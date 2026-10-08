from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request = None) -> dict:
    """Return liveness plus dependency statuses gathered at startup."""
    checks = getattr(request.app.state, "startup_checks", {}) if request else {}
    return {"status": "ok", "service": "mri-agent", "checks": checks}


@router.get("/ready")
def ready(request: Request) -> dict:
    """Return whether startup checks completed and the service can receive work."""
    checks = getattr(request.app.state, "startup_checks", {})
    required = ("storage", "mongodb", "chroma", "model")
    complete = bool(checks) and all(name in checks for name in required)
    unavailable = [
        name for name, value in checks.items() if value.get("status") == "unavailable"
    ]
    return {
        "status": "ready" if complete and not unavailable else "degraded",
        "service": "mri-agent",
        "checks": checks,
    }
