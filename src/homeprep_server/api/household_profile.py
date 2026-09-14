from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.planning_services import HouseholdProfileService
from homeprep_server.schemas import HouseholdProfileRead, HouseholdProfileUpsert
from homeprep_server.services import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/household-profile", tags=["household-profile"])
SessionDep = Annotated[Session, Depends(get_session)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.get("/{household_id}", response_model=HouseholdProfileRead)
def get_household_profile(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> HouseholdProfileRead:
    del principal
    try:
        return HouseholdProfileService(session).get(household_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.put("/{household_id}", response_model=HouseholdProfileRead)
def upsert_household_profile(
    household_id: UUID,
    payload: HouseholdProfileUpsert,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> HouseholdProfileRead:
    del principal
    try:
        return HouseholdProfileService(session).upsert(household_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
