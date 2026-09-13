from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from homeprep_server.api.auth import require_user
from homeprep_server.api.client_auth import PrincipalDep
from homeprep_server.database import get_session
from homeprep_server.schemas import HouseholdCreate, HouseholdRead
from homeprep_server.services import ConflictError, HouseholdService, NotFoundError

router = APIRouter(prefix="/api/v1/households", tags=["households"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=HouseholdRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_user)],
)
def create_household(
    payload: HouseholdCreate,
    session: SessionDep,
) -> HouseholdRead:
    try:
        return HouseholdService(session).create(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=list[HouseholdRead])
def list_households(
    session: SessionDep,
    principal: PrincipalDep,
) -> list[HouseholdRead]:
    del principal
    return list(HouseholdService(session).list_all())


@router.get("/{household_id}", response_model=HouseholdRead)
def get_household(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> HouseholdRead:
    del principal
    try:
        return HouseholdService(session).get(household_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
