from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from homeprep_server.database import get_session
from homeprep_server.schemas import HouseholdCreate, HouseholdRead
from homeprep_server.services import HouseholdService, NotFoundError

router = APIRouter(prefix="/api/v1/households", tags=["households"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=HouseholdRead, status_code=status.HTTP_201_CREATED)
def create_household(
    payload: HouseholdCreate,
    session: SessionDep,
) -> HouseholdRead:
    return HouseholdService(session).create(payload)


@router.get("/{household_id}", response_model=HouseholdRead)
def get_household(
    household_id: UUID,
    session: SessionDep,
) -> HouseholdRead:
    try:
        return HouseholdService(session).get(household_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
