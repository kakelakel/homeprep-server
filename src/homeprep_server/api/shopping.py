from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.services import ConflictError, NotFoundError
from homeprep_server.shopping_contract import ShoppingContractModel, ShoppingContractService

router = APIRouter(prefix="/api/v1/shopping", tags=["shopping"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]
ShoppingStatus = Literal["pending", "purchased", "ignored"]
ShoppingSource = Literal[
    "manual",
    "inventory_expired",
    "target_shortage",
    "plan_requirement",
    "container_requirement",
    "asset_maintenance",
]


class ShoppingCreate(BaseModel):
    household_id: UUID
    name: str = Field(min_length=1, max_length=160)
    quantity: float = Field(default=1.0, ge=0)
    unit: str = Field(default="piece", min_length=1, max_length=32)
    category: str = Field(default="other", min_length=1, max_length=64)
    container_id: UUID | None = None
    source_type: ShoppingSource = "manual"
    source_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=4000)
    status: ShoppingStatus = "pending"
    notes: str | None = Field(default=None, max_length=4000)


class ShoppingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    container_id: UUID | None = None
    source_type: ShoppingSource | None = None
    source_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=4000)
    status: ShoppingStatus | None = None
    notes: str | None = Field(default=None, max_length=4000)
    expected_revision: int = Field(ge=1)


class ShoppingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    name: str
    quantity: float
    unit: str
    category: str
    container_id: UUID | None
    source_type: str
    source_id: UUID | None
    reason: str | None
    status: str
    notes: str | None
    purchased_at: datetime | None
    ignored_at: datetime | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int
    deleted_at: datetime | None


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


@router.get("", response_model=list[ShoppingRead])
def list_shopping(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[ShoppingRead]:
    del principal
    try:
        return list(ShoppingContractService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.post("", response_model=ShoppingRead, status_code=status.HTTP_201_CREATED)
def create_shopping(
    payload: ShoppingCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ShoppingContractModel:
    del principal
    try:
        return ShoppingContractService(session).create(
            household_id=payload.household_id,
            name=payload.name,
            quantity=payload.quantity,
            unit=payload.unit,
            category=payload.category,
            container_id=payload.container_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            reason=payload.reason,
            status=payload.status,
            notes=payload.notes,
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.patch("/{item_id}", response_model=ShoppingRead)
def update_shopping(
    item_id: UUID,
    payload: ShoppingUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ShoppingContractModel:
    del principal
    try:
        return ShoppingContractService(session).update(
            item_id,
            expected_revision=payload.expected_revision,
            changes=payload.model_dump(exclude_unset=True, exclude={"expected_revision"}),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{item_id}", response_model=ShoppingRead)
def delete_shopping(
    item_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> ShoppingContractModel:
    del principal
    try:
        return ShoppingContractService(session).delete(item_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
