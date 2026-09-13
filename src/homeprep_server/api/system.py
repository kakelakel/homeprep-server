from fastapi import APIRouter, HTTPException

from homeprep_server import __version__
from homeprep_server.core.config import settings
from homeprep_server.core.identity import get_server_id
from homeprep_server.database import database_is_ready

router = APIRouter()


@router.get("/healthz", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", tags=["system"])
def readiness() -> dict[str, str]:
    if not database_is_ready():
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ready"}


@router.get("/api/v1/system/info", tags=["system"])
def system_info() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "api_version": "v1",
        "server_id": str(get_server_id()),
    }
