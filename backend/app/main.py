from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent, health, jobs, studies
from app.config import Settings, get_settings
from app.startup import run_startup_checks
from app.storage.repository import close_repository


def configure_logging(level: str = "INFO") -> None:
    """Initialize predictable console logging for the process."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application; this also makes isolated tests straightforward."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.startup_checks = run_startup_checks(settings)
        logger.info("%s started in %s mode", settings.app_name, settings.environment)
        try:
            yield
        finally:
            close_repository()
            logger.info("%s stopped", settings.app_name)

    application = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = "/api/v1"
    application.include_router(health.router, prefix=api_prefix)
    application.include_router(studies.router, prefix=api_prefix)
    application.include_router(jobs.router, prefix=api_prefix)
    application.include_router(agent.router, prefix=api_prefix)

    @application.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {"name": settings.app_name, "version": settings.app_version, "docs": "/docs"}

    return application


app = create_app()
