from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthSetup(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)


class AuthLogin(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    role: str
    created_at: datetime


class AuthStatus(BaseModel):
    setup_required: bool
    authenticated: bool
    user: UserRead | None = None


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class HouseholdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int
    deleted_at: datetime | None


class InventoryCreate(BaseModel):
    household_id: UUID
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="other", min_length=1, max_length=64)
    item_type: str = Field(default="consumable", min_length=1, max_length=32)
    quantity: float = Field(default=1.0, ge=0)
    unit: str = Field(default="pcs", min_length=1, max_length=32)
    expires_at: date | None = None
    last_checked: date | None = None
    next_check_at: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    container_id: UUID | None = None


class InventoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    item_type: str | None = Field(default=None, min_length=1, max_length=32)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    expires_at: date | None = None
    last_checked: date | None = None
    next_check_at: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    container_id: UUID | None = None
    expected_revision: int = Field(ge=1)


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    name: str
    category: str
    item_type: str
    quantity: float
    unit: str
    expires_at: date | None
    last_checked: date | None
    next_check_at: date | None
    notes: str | None
    container_id: UUID | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int
    deleted_at: datetime | None
