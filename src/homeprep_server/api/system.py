from fastapi import APIRouter

from homeprep_server import __version__
from homeprep_server.core.config import settings

router = APIRouter()


@router.get("/healthz", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", tags=["system"])
def readiness() -> dict[str, str]:
    # Database readiness will be added when persistence is initialized.
    return {"status": "ready"}


@router.get("/api/v1/system/info", tags=["system"])
def system_info() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "api_version": "v1",
    }
