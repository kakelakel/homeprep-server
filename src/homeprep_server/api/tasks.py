from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.schemas import TaskComplete, TaskCreate, TaskRead, TaskUpdate
from homeprep_server.services import ConflictError, NotFoundError, TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TaskRead:
    del principal
    try:
        return TaskService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[TaskRead])
def list_tasks(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[TaskRead]:
    del principal
    try:
        return list(TaskService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> TaskRead:
    del principal
    try:
        return TaskService(session).get(task_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TaskRead:
    del principal
    try:
        return TaskService(session).update(task_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: UUID,
    payload: TaskComplete,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TaskRead:
    del principal
    try:
        return TaskService(session).complete(task_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{task_id}", response_model=TaskRead)
def delete_task(
    task_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> TaskRead:
    del principal
    try:
        return TaskService(session).delete(task_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
