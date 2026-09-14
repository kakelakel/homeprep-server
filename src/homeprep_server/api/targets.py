from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.planning_services import TargetService
from homeprep_server.schemas import TargetCreate, TargetRead, TargetUpdate
from homeprep_server.services import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def create_target(
    payload: TargetCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TargetRead:
    del principal
    try:
        return TargetService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[TargetRead])
def list_targets(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[TargetRead]:
    del principal
    try:
        return list(TargetService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{target_id}", response_model=TargetRead)
def get_target(
    target_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> TargetRead:
    del principal
    try:
        return TargetService(session).get(target_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{target_id}", response_model=TargetRead)
def update_target(
    target_id: UUID,
    payload: TargetUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TargetRead:
    del principal
    try:
        return TargetService(session).update(target_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{target_id}", response_model=TargetRead)
def delete_target(
    target_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TargetRead:
    del principal
    try:
        return TargetService(session).delete(target_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
