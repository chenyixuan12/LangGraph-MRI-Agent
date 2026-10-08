"""Infrastructure-only checks executed when the API starts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


def _check_chroma(path: Path) -> dict[str, Any]:
    """Check local ChromaDB configuration without making it mandatory yet."""

    path.mkdir(parents=True, exist_ok=True)
    try:
        import chromadb  # type: ignore
    except ImportError:
        return {"status": "not_configured", "path": str(path), "detail": "chromadb is not installed"}

    try:
        chromadb.PersistentClient(path=str(path))
    except Exception as exc:  # pragma: no cover - depends on optional package
        logger.exception("ChromaDB startup check failed")
        return {"status": "unavailable", "path": str(path), "detail": str(exc)}
    return {"status": "ready", "path": str(path)}


def _check_model_dir(path: Path) -> dict[str, Any]:
    """Report model files without loading a model into memory."""

    if not path.exists():
        return {"status": "not_configured", "path": str(path), "detail": "directory does not exist"}
    if not path.is_dir():
        return {"status": "unavailable", "path": str(path), "detail": "path is not a directory"}
    files = sum(1 for item in path.rglob("*") if item.is_file())
    return {"status": "ready" if files else "empty", "path": str(path), "files": files}


def _check_mongodb(settings: Settings) -> dict[str, Any]:
    """Check MongoDB connectivity without making an unavailable DB crash startup."""
    try:
        from pymongo import MongoClient

        client = MongoClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )
        try:
            client.admin.command("ping")
        finally:
            client.close()
    except Exception as exc:
        logger.warning("MongoDB startup check failed: %s", exc)
        return {"status": "unavailable", "database": settings.mongodb_database, "detail": str(exc)}
    return {"status": "ready", "database": settings.mongodb_database}


def run_startup_checks(settings: Settings) -> dict[str, dict[str, Any]]:
    """Prepare storage and return dependency statuses for health checks."""

    for directory in (settings.data_dir, settings.upload_dir, settings.processed_dir):
        directory.mkdir(parents=True, exist_ok=True)

    checks = {
        "storage": {"status": "ready", "path": str(settings.data_dir)},
        "mongodb": _check_mongodb(settings),
        "chroma": _check_chroma(settings.chroma_dir),
        "model": _check_model_dir(settings.model_dir),
    }
    for name, result in checks.items():
        logger.info("startup check %-7s: %s", name, result["status"])
    return checks
