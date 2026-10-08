from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import get_settings
from app.imaging.pipeline import SuperResolutionPipeline
from app.schemas.job import Job, JobCreate
from app.storage.repository import get_repository

router = APIRouter(tags=["jobs"])


def _repo():
    return get_repository()


def _process(job: Job, source: Path) -> None:
    repo = _repo()
    try:
        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        repo.save("jobs", job.id, job.model_dump())
        output = get_settings().processed_dir / f"{job.id}{source.suffix}"
        SuperResolutionPipeline().run(source, output, job.scale, job.method)
        job.status, job.output_path = "completed", str(output)
    except Exception as exc:  # keep failure visible through the job API
        job.status, job.error = "failed", str(exc)
    job.updated_at = datetime.now(timezone.utc)
    repo.save("jobs", job.id, job.model_dump())


@router.post("/studies/{study_id}/super-resolution", response_model=Job, status_code=202)
def create_job(study_id: str, payload: JobCreate, background_tasks: BackgroundTasks) -> Job:
    settings = get_settings()
    metadata = _repo().get("studies", study_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="研究不存在")
    matches = list(settings.upload_dir.glob(f"{study_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="研究文件不存在")
    now = datetime.now(timezone.utc)
    job = Job(id=uuid4().hex, study_id=study_id, status="queued", scale=payload.scale, method=payload.method, created_at=now, updated_at=now)
    _repo().save("jobs", job.id, job.model_dump())
    background_tasks.add_task(_process, job, matches[0])
    return job


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    value = _repo().get("jobs", job_id)
    if not value:
        raise HTTPException(status_code=404, detail="任务不存在")
    return Job.model_validate(value)
