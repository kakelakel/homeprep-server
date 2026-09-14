"""Contract tests for Home Assistant ↔ Server domain-language parity.

The HA standalone integration is the canonical HomePrep domain contract. These tests
make accidental field loss visible before sync work can ship.
"""

# ruff: noqa: I001

from homeprep_server.models import (
    AssetModel,
    ContainerModel,
    InventoryItemModel,
    PlanModel,
    TargetModel,
    TaskModel,
)
from homeprep_server.schemas import (
    AssetRead,
    ContainerRead,
    InventoryRead,
    PlanRead,
    TargetRead,
    TaskRead,
)


HA_INVENTORY_FIELDS = {
    "id",
    "household_id",
    "name",
    "category",
    "item_type",
    "quantity",
    "unit",
    "container_id",
    "expires_at",
    "last_checked",
    "next_check_at",
    "notes",
    "image_id",
    "image_token",
    "image_content_type",
    "image_filename",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}
HA_CONTAINER_FIELDS = {
    "id",
    "household_id",
    "name",
    "container_type",
    "location",
    "description",
    "last_checked_at",
    "next_check_at",
    "notes",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}
HA_ASSET_FIELDS = {
    "id",
    "household_id",
    "name",
    "asset_type",
    "location",
    "description",
    "instructions",
    "last_checked_at",
    "next_check_at",
    "notes",
    "image_id",
    "image_token",
    "image_content_type",
    "image_filename",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}
HA_TASK_FIELDS = {
    "id",
    "household_id",
    "name",
    "task_kind",
    "category",
    "linked_item_id",
    "linked_container_id",
    "linked_asset_id",
    "recurrence_type",
    "recurrence_interval",
    "reschedule_mode",
    "last_completed_at",
    "next_due_at",
    "reminder_before_days",
    "enabled",
    "notes",
    "completion_count",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}
HA_PLAN_FIELDS = {
    "id",
    "household_id",
    "name",
    "plan_type",
    "description",
    "meeting_point",
    "enabled",
    "checklist",
    "review_interval_months",
    "last_reviewed_at",
    "next_review_at",
    "notes",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}
HA_TARGET_FIELDS = {
    "id",
    "household_id",
    "name",
    "category",
    "target_type",
    "matcher",
    "unit",
    "minimum_value",
    "target_value",
    "current_value",
    "requirements",
    "completed_requirement_ids",
    "priority",
    "enabled",
    "notes",
    "origin",
    "source_profile_id",
    "source_recommendation_id",
    "source_profile_version",
    "created_at",
    "updated_at",
    "deleted_at",
    "revision",
    "schema_version",
}


def model_columns(model) -> set[str]:
    return {column.name for column in model.__table__.columns}


def schema_fields(schema) -> set[str]:
    return set(schema.model_fields)


def test_inventory_contract_matches_ha_schema_v4() -> None:
    assert model_columns(InventoryItemModel) == HA_INVENTORY_FIELDS
    assert schema_fields(InventoryRead) == HA_INVENTORY_FIELDS
    assert InventoryItemModel.__table__.c.schema_version.default.arg == 4


def test_container_contract_matches_ha_schema_v2() -> None:
    assert model_columns(ContainerModel) == HA_CONTAINER_FIELDS
    assert schema_fields(ContainerRead) == HA_CONTAINER_FIELDS
    assert ContainerModel.__table__.c.schema_version.default.arg == 2


def test_asset_contract_matches_ha_schema_v2() -> None:
    assert model_columns(AssetModel) == HA_ASSET_FIELDS
    assert schema_fields(AssetRead) == HA_ASSET_FIELDS
    assert AssetModel.__table__.c.schema_version.default.arg == 2


def test_task_contract_matches_ha_schema_v5() -> None:
    assert model_columns(TaskModel) == HA_TASK_FIELDS
    assert schema_fields(TaskRead) == HA_TASK_FIELDS
    assert TaskModel.__table__.c.schema_version.default.arg == 5


def test_plan_contract_matches_ha_schema_v3() -> None:
    assert model_columns(PlanModel) == HA_PLAN_FIELDS
    assert schema_fields(PlanRead) == HA_PLAN_FIELDS
    assert PlanModel.__table__.c.schema_version.default.arg == 3


def test_target_contract_matches_ha_schema_v4() -> None:
    assert model_columns(TargetModel) == HA_TARGET_FIELDS
    assert schema_fields(TargetRead) == HA_TARGET_FIELDS
    assert TargetModel.__table__.c.schema_version.default.arg == 4
