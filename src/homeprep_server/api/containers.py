from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.schemas import ContainerCreate, ContainerRead, ContainerUpdate
from homeprep_server.services import ConflictError, ContainerService, NotFoundError

router = APIRouter(prefix="/api/v1/containers", tags=["containers"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=ContainerRead, status_code=status.HTTP_201_CREATED)
def create_container(
    payload: ContainerCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ContainerRead:
    del principal
    try:
        return ContainerService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[ContainerRead])
def list_containers(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[ContainerRead]:
    del principal
    try:
        return list(ContainerService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{container_id}", response_model=ContainerRead)
def get_container(
    container_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> ContainerRead:
    del principal
    try:
        return ContainerService(session).get(container_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{container_id}", response_model=ContainerRead)
def update_container(
    container_id: UUID,
    payload: ContainerUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ContainerRead:
    del principal
    try:
        return ContainerService(session).update(container_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{container_id}", response_model=ContainerRead)
def delete_container(
    container_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ContainerRead:
    del principal
    try:
        return ContainerService(session).delete(container_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
