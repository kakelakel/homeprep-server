from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.planning_services import PlanService
from homeprep_server.schemas import PlanCreate, PlanRead, PlanUpdate
from homeprep_server.services import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[PlanRead])
def list_plans(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[PlanRead]:
    del principal
    try:
        return list(PlanService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(
    plan_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).get(plan_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: UUID,
    payload: PlanUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).update(plan_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{plan_id}", response_model=PlanRead)
def delete_plan(
    plan_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).delete(plan_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
