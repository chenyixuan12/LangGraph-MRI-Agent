"""Upload and lifecycle management for MRI study files."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.config import Settings, get_settings
from app.schemas.study import Study, StudyList
from app.storage.repository import get_repository

router = APIRouter(prefix="/studies", tags=["studies"])

ALLOWED_CONTENT_TYPES = {
    "application/dicom",
    "application/x-dicom",
    "application/gzip",
    "application/nii",
    "application/octet-stream",
    "application/x-gzip",
    "application/x-nifti",
    "image/bmp",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


def _extension(filename: str) -> str:
    """Extract a supported extension, including the compound NIfTI suffix."""
    lowered = filename.lower()
    if lowered.endswith(".nii.gz"):
        return ".nii.gz"
    return Path(lowered).suffix


def _safe_filename(filename: str | None) -> str:
    """Keep a display name while removing path and control-character tricks."""
    raw = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    raw = unicodedata.normalize("NFKC", raw)
    raw = re.sub(r"[\x00-\x1f\x7f]", "_", raw)
    raw = re.sub(r"[^\w.() -]+", "_", raw, flags=re.UNICODE).strip(" .")
    if not raw:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return raw[:255]


def _stored_path(settings: Settings, study_id: str, metadata: dict) -> Path:
    """Resolve a stored file inside the upload directory only."""
    storage_name = metadata.get("storage_name")
    if storage_name:
        candidate = (settings.upload_dir / str(storage_name)).resolve()
        upload_root = settings.upload_dir.resolve()
        if candidate.parent != upload_root or candidate.name != str(storage_name):
            raise HTTPException(status_code=500, detail="研究文件存储路径无效")
        if candidate.is_file():
            return candidate
        raise HTTPException(status_code=404, detail="研究文件不存在")

    # Compatibility for records created before storage_name was added.
    matches = [path for path in settings.upload_dir.glob(f"{study_id}.*") if path.is_file()]
    if not matches:
        raise HTTPException(status_code=404, detail="研究文件不存在")
    return matches[0]


def _get_study(study_id: str) -> tuple[dict, Path]:
    metadata = get_repository().get("studies", study_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="研究不存在")
    return metadata, _stored_path(get_settings(), study_id, metadata)


@router.post("", response_model=Study, status_code=status.HTTP_201_CREATED)
async def upload_study(file: UploadFile = File(...)) -> Study:
    settings = get_settings()
    safe_name = _safe_filename(file.filename)
    suffix = _extension(safe_name)
    if suffix not in settings.allowed_extensions:
        raise HTTPException(status_code=415, detail=f"不支持的文件类型：{suffix or '无扩展名'}")
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"不支持的文件 MIME 类型：{file.content_type}")

    study_id = uuid4().hex
    storage_name = f"{study_id}{suffix}"
    target = settings.upload_dir / storage_name
    temporary = settings.upload_dir / f".{study_id}.uploading"
    total = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    try:
        with temporary.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail="文件超过大小限制")
                stream.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="不能上传空文件")
        temporary.replace(target)
        study = Study(
            id=study_id,
            filename=safe_name,
            content_type=file.content_type,
            size_bytes=total,
            created_at=datetime.now(timezone.utc),
        )
        record = study.model_dump()
        record["storage_name"] = storage_name
        get_repository().save("studies", study_id, record)
        return study
    except HTTPException:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="文件保存失败，请稍后重试")
    finally:
        await file.close()


@router.get("", response_model=StudyList)
def list_studies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StudyList:
    repo = get_repository()
    records = repo.list("studies", limit=limit, offset=offset)
    return StudyList(
        items=[Study.model_validate(record) for record in records],
        total=repo.count("studies"),
        limit=limit,
        offset=offset,
    )


@router.get("/{study_id}", response_model=Study)
def get_study(study_id: str) -> Study:
    metadata = get_repository().get("studies", study_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="研究不存在")
    return Study.model_validate(metadata)


@router.get("/{study_id}/file")
def download_study(study_id: str) -> FileResponse:
    metadata, path = _get_study(study_id)
    return FileResponse(
        path,
        media_type=metadata.get("content_type") or "application/octet-stream",
        filename=metadata.get("filename") or path.name,
    )


@router.delete("/{study_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_study(study_id: str) -> None:
    repo = get_repository()
    metadata = repo.get("studies", study_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="研究不存在")
    try:
        path = _stored_path(get_settings(), study_id, metadata)
    except HTTPException as exc:
        # A missing binary is already gone; still remove its orphaned metadata.
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
    else:
        path.unlink(missing_ok=True)
    repo.delete("studies", study_id)
