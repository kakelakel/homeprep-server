from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class ClientType(StrEnum):
    HOME_ASSISTANT = "home_assistant"
    ANDROID = "android"
    WEB = "web"
    OTHER = "other"


class ClientAccessRole(StrEnum):
    FULL_ACCESS = "full_access"
    READ_ONLY = "read_only"


class ContainerType(StrEnum):
    BAG = "bag"
    BOX_CRATE = "box_crate"
    WATER_CONTAINER = "water_container"
    CABINET_STORAGE = "cabinet_storage"
    VEHICLE_STORAGE = "vehicle_storage"
    OTHER = "other"


class AssetType(StrEnum):
    WATER_SHUTOFF = "water_shutoff"
    ISOLATION_VALVE = "isolation_valve"
    FLOOR_DRAIN = "floor_drain"
    LEAK_SENSOR = "leak_sensor"
    BACKFLOW_VALVE = "backflow_valve"
    SUMP_PUMP = "sump_pump"
    SMOKE_ALARM = "smoke_alarm"
    FIRE_EXTINGUISHER = "fire_extinguisher"
    ELECTRICAL_PANEL = "electrical_panel"
    GENERATOR = "generator"
    OTHER = "other"


class TaskKind(StrEnum):
    GENERAL = "general"
    INSPECTION = "inspection"
    CONTAINER_INSPECTION = "container_inspection"
    ASSET_INSPECTION = "asset_inspection"


class RecurrenceType(StrEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class RescheduleMode(StrEnum):
    COMPLETION = "completion"
    SCHEDULED = "scheduled"


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
    disabled_at: datetime | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)
    disabled: bool | None = None


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


class ClientContextPrincipal(BaseModel):
    kind: str
    id: UUID
    name: str
    role: str


class ClientContextHousehold(BaseModel):
    id: UUID
    name: str


class ClientContext(BaseModel):
    server_id: UUID
    server_version: str
    api_version: str
    principal: ClientContextPrincipal
    household: ClientContextHousehold | None


class BackupRead(BaseModel):
    filename: str
    path: str
    created_at: datetime
    size_bytes: int
    format_version: int


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


class ContainerCreate(BaseModel):
    household_id: UUID
    name: str = Field(min_length=1, max_length=120)
    container_type: ContainerType = ContainerType.OTHER
    location: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ContainerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    container_type: ContainerType | None = None
    location: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    expected_revision: int = Field(ge=1)


class ContainerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    name: str
    container_type: str
    location: str | None
    description: str | None
    last_checked_at: datetime | None
    next_check_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int
    deleted_at: datetime | None


class AssetCreate(BaseModel):
    household_id: UUID
    name: str = Field(min_length=1, max_length=120)
    asset_type: AssetType = AssetType.OTHER
    location: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    instructions: str | None = Field(default=None, max_length=8000)
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    image_id: str | None = Field(default=None, max_length=120)
    image_token: str | None = Field(default=None, max_length=255)
    image_content_type: str | None = Field(default=None, max_length=120)
    image_filename: str | None = Field(default=None, max_length=255)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    asset_type: AssetType | None = None
    location: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    instructions: str | None = Field(default=None, max_length=8000)
    last_checked_at: datetime | None = None
    next_check_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    image_id: str | None = Field(default=None, max_length=120)
    image_token: str | None = Field(default=None, max_length=255)
    image_content_type: str | None = Field(default=None, max_length=120)
    image_filename: str | None = Field(default=None, max_length=255)
    expected_revision: int = Field(ge=1)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    name: str
    asset_type: str
    location: str | None
    description: str | None
    instructions: str | None
    last_checked_at: datetime | None
    next_check_at: datetime | None
    notes: str | None
    image_id: str | None
    image_token: str | None
    image_content_type: str | None
    image_filename: str | None
    created_at: datetime
    updated_at: datetime
    revision: int
    schema_version: int
    deleted_at: datetime | None


class TaskCreate(BaseModel):
    household_id: UUID
    name: str = Field(min_length=1, max_length=120)
    task_kind: TaskKind = TaskKind.GENERAL
    category: str | None = Field(default=None, max_length=64)
    linked_item_id: UUID | None = None
    linked_container_id: UUID | None = None
    linked_asset_id: UUID | None = None
    recurrence_type: RecurrenceType = RecurrenceType.MONTHS
    recurrence_interval: int = Field(default=1, ge=1, le=1000)
    reschedule_mode: RescheduleMode = RescheduleMode.COMPLETION
    last_completed_at: datetime | None = None
    next_due_at: date | None = None
    reminder_before_days: int = Field(default=0, ge=0, le=3650)
    enabled: bool = True
    notes: str | None = Field(default=None, max_length=4000)
    completion_count: int = Field(default=0, ge=0)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    task_kind: TaskKind | None = None
    category: str | None = Field(default=None, max_length=64)
    linked_item_id: UUID | None = None
    linked_container_id: UUID | None = None
    linked_asset_id: UUID | None = None
    recurrence_type: RecurrenceType | None = None
    recurrence_interval: int | None = Field(default=None, ge=1, le=1000)
    reschedule_mode: RescheduleMode | None = None
    last_completed_at: datetime | None = None
    next_due_at: date | None = None
    reminder_before_days: int | None = Field(default=None, ge=0, le=3650)
    enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)
    completion_count: int | None = Field(default=None, ge=0)
    expected_revision: int = Field(ge=1)


class TaskComplete(BaseModel):
    expected_revision: int = Field(ge=1)
    completed_on: date | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    name: str
    task_kind: str
    category: str | None
    linked_item_id: UUID | None
    linked_container_id: UUID | None
    linked_asset_id: UUID | None
    recurrence_type: str
    recurrence_interval: int
    reschedule_mode: str
    last_completed_at: datetime | None
    next_due_at: date | None
    reminder_before_days: int
    enabled: bool
    notes: str | None
    completion_count: int
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
