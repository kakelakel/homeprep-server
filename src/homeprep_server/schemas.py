from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientType(StrEnum):
    HOME_ASSISTANT = "home_assistant"
    ANDROID = "android"
    WEB = "web"
    OTHER = "other"


class ClientAccessRole(StrEnum):
    FULL_ACCESS = "full_access"
    READ_ONLY = "read_only"


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


class ClientCredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    client_type: ClientType = ClientType.OTHER
    access_role: ClientAccessRole = ClientAccessRole.FULL_ACCESS


class ClientCredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    client_type: str
    access_role: str
    created_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None


class ClientCredentialCreated(ClientCredentialRead):
    token: str


class ClientPairingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    client_type: ClientType = ClientType.OTHER
    access_role: ClientAccessRole = ClientAccessRole.FULL_ACCESS


class ClientPairingCreated(BaseModel):
    id: UUID
    name: str
    client_type: str
    access_role: str
    pairing_token: str
    expires_at: datetime


class ClientPairingExchange(BaseModel):
    pairing_token: str = Field(min_length=16, max_length=256)


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
