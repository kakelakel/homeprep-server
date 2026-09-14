from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep
from homeprep_server.database import get_session
from homeprep_server.readiness import ReadinessService
from homeprep_server.services import NotFoundError

router = APIRouter(prefix="/api/v1/readiness", tags=["readiness"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/{household_id}")
def get_readiness(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict:
    del principal
    try:
        return ReadinessService(session).summary(household_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
