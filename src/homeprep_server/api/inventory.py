from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from homeprep_server.api.auth import require_user
from homeprep_server.database import get_session
from homeprep_server.schemas import InventoryCreate, InventoryRead, InventoryUpdate
from homeprep_server.services import ConflictError, InventoryService, NotFoundError

router = APIRouter(
    prefix="/api/v1/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_user)],
)
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.post("", response_model=InventoryRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryCreate,
    session: SessionDep,
) -> InventoryRead:
    try:
        return InventoryService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    household_id: UUID,
    session: SessionDep,
) -> list[InventoryRead]:
    try:
        return list(InventoryService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{item_id}", response_model=InventoryRead)
def get_inventory_item(
    item_id: UUID,
    session: SessionDep,
) -> InventoryRead:
    try:
        return InventoryService(session).get(item_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{item_id}", response_model=InventoryRead)
def update_inventory_item(
    item_id: UUID,
    payload: InventoryUpdate,
    session: SessionDep,
) -> InventoryRead:
    try:
        return InventoryService(session).update(item_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{item_id}", response_model=InventoryRead)
def delete_inventory_item(
    item_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
) -> InventoryRead:
    try:
        return InventoryService(session).delete(item_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
