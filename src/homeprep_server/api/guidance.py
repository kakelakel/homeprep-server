from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.guidance import GuidanceService
from homeprep_server.schemas import TargetRead
from homeprep_server.services import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/guidance", tags=["guidance"])
SessionDep = Annotated[Session, Depends(get_session)]


class GuidanceAdoptRequest(BaseModel):
    household_id: UUID
    recommendation_id: str = Field(min_length=1, max_length=120)
    profile_id: str | None = Field(default=None, max_length=120)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.get("/profiles")
def list_guidance_profiles(
    session: SessionDep,
    principal: PrincipalDep,
) -> list[dict]:
    del principal
    return GuidanceService(session).list_profiles()


@router.get("/{household_id}")
def resolved_guidance(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
    profile_id: str | None = Query(default=None, max_length=120),
) -> dict:
    del principal
    try:
        return GuidanceService(session).resolved(household_id, profile_id)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("/adopt", response_model=TargetRead)
def adopt_guidance(
    payload: GuidanceAdoptRequest,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TargetRead:
    del principal
    try:
        return GuidanceService(session).adopt(
            payload.household_id,
            payload.recommendation_id,
            payload.profile_id,
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
