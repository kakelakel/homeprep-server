from calendar import monthrange
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.orm import Session

from homeprep_server.models import (
    AssetModel,
    ContainerModel,
    HouseholdModel,
    InventoryItemModel,
    TaskModel,
)
from homeprep_server.repositories import (
    AssetRepository,
    ContainerRepository,
    HouseholdRepository,
    InventoryRepository,
    TaskRepository,
)
from homeprep_server.schemas import (
    AssetCreate,
    AssetUpdate,
    ContainerCreate,
    ContainerUpdate,
    HouseholdCreate,
    InventoryCreate,
    InventoryUpdate,
    TaskComplete,
    TaskCreate,
    TaskUpdate,
)


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(value: date, years: int) -> date:
    year = value.year + years
    day = min(value.day, monthrange(year, value.month)[1])
    return date(year, value.month, day)


def calculate_next_due(task: TaskModel, completed_on: date) -> date:
    base = completed_on
    if task.reschedule_mode == "scheduled" and task.next_due_at is not None:
        base = task.next_due_at

    def advance(value: date) -> date:
        if task.recurrence_type == "days":
            return value + timedelta(days=task.recurrence_interval)
        if task.recurrence_type == "weeks":
            return value + timedelta(weeks=task.recurrence_interval)
        if task.recurrence_type == "months":
            return _add_months(value, task.recurrence_interval)
        if task.recurrence_type == "years":
            return _add_years(value, task.recurrence_interval)
        raise ValueError(f"Unsupported recurrence type: {task.recurrence_type}")

    next_due = advance(base)
    if task.reschedule_mode == "scheduled":
        while next_due <= completed_on:
            next_due = advance(next_due)
    return next_due


class HouseholdService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = HouseholdRepository(session)

    def create(self, payload: HouseholdCreate) -> HouseholdModel:
        if self.repository.list_all():
            raise ConflictError("This HomePrep Server already has a household")
        household = HouseholdModel(id=str(uuid4()), name=payload.name)
        self.repository.add(household)
        self.session.commit()
        self.session.refresh(household)
        return household

    def get(self, household_id: UUID) -> HouseholdModel:
        household = self.repository.get(str(household_id))
        if household is None:
            raise NotFoundError("Household not found")
        return household

    def list_all(self) -> Sequence[HouseholdModel]:
        return self.repository.list_all()


class ContainerService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ContainerRepository(session)
        self.households = HouseholdRepository(session)

    def create(self, payload: ContainerCreate) -> ContainerModel:
        if self.households.get(str(payload.household_id)) is None:
            raise NotFoundError("Household not found")
        container = ContainerModel(
            id=str(uuid4()),
            household_id=str(payload.household_id),
            name=payload.name,
            container_type=payload.container_type.value,
            location=payload.location,
            description=payload.description,
            last_checked_at=payload.last_checked_at,
            next_check_at=payload.next_check_at,
            notes=payload.notes,
        )
        self.repository.add(container)
        self.session.commit()
        self.session.refresh(container)
        return container

    def get(self, container_id: UUID) -> ContainerModel:
        container = self.repository.get(str(container_id))
        if container is None:
            raise NotFoundError("Container not found")
        return container

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, container_id: UUID, payload: ContainerUpdate) -> ContainerModel:
        container = self.get(container_id)
        if container.revision != payload.expected_revision:
            message = (
                "Revision mismatch: expected "
                f"{payload.expected_revision}, current {container.revision}"
            )
            raise ConflictError(message)
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "container_type" in changes and changes["container_type"] is not None:
            changes["container_type"] = changes["container_type"].value
        for field, value in changes.items():
            setattr(container, field, value)
        container.revision += 1
        container.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(container)
        return container

    def delete(self, container_id: UUID, expected_revision: int) -> ContainerModel:
        container = self.get(container_id)
        if container.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {container.revision}"
            )
        now = utc_now()
        container.deleted_at = now
        container.updated_at = now
        container.revision += 1
        self.session.execute(
            sqlalchemy_update(InventoryItemModel)
            .where(
                InventoryItemModel.container_id == str(container_id),
                InventoryItemModel.deleted_at.is_(None),
            )
            .values(
                container_id=None,
                updated_at=now,
                revision=InventoryItemModel.revision + 1,
            )
        )
        self.session.commit()
        self.session.refresh(container)
        return container


class AssetService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = AssetRepository(session)
        self.households = HouseholdRepository(session)

    def create(self, payload: AssetCreate) -> AssetModel:
        if self.households.get(str(payload.household_id)) is None:
            raise NotFoundError("Household not found")
        asset = AssetModel(
            id=str(uuid4()),
            household_id=str(payload.household_id),
            name=payload.name,
            asset_type=payload.asset_type.value,
            location=payload.location,
            description=payload.description,
            instructions=payload.instructions,
            last_checked_at=payload.last_checked_at,
            next_check_at=payload.next_check_at,
            notes=payload.notes,
            image_id=payload.image_id,
            image_token=payload.image_token,
            image_content_type=payload.image_content_type,
            image_filename=payload.image_filename,
        )
        self.repository.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: UUID) -> AssetModel:
        asset = self.repository.get(str(asset_id))
        if asset is None:
            raise NotFoundError("Asset not found")
        return asset

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, asset_id: UUID, payload: AssetUpdate) -> AssetModel:
        asset = self.get(asset_id)
        if asset.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {asset.revision}"
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "asset_type" in changes and changes["asset_type"] is not None:
            changes["asset_type"] = changes["asset_type"].value
        for field, value in changes.items():
            setattr(asset, field, value)
        asset.revision += 1
        asset.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def delete(self, asset_id: UUID, expected_revision: int) -> AssetModel:
        asset = self.get(asset_id)
        if asset.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {asset.revision}"
            )
        now = utc_now()
        asset.deleted_at = now
        asset.updated_at = now
        asset.revision += 1
        self.session.commit()
        self.session.refresh(asset)
        return asset


class TaskService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = TaskRepository(session)
        self.households = HouseholdRepository(session)
        self.inventory = InventoryRepository(session)
        self.containers = ContainerRepository(session)
        self.assets = AssetRepository(session)

    def _validate_link(self, household_id: str, repository, linked_id: UUID | None, label: str):
        if linked_id is None:
            return None
        linked = repository.get(str(linked_id))
        if linked is None or linked.household_id != household_id:
            raise NotFoundError(f"{label} not found in this household")
        return linked.id

    def _sync_linked_resource(self, task: TaskModel) -> None:
        next_due = task.next_due_at if task.enabled else None
        checked_at = task.last_completed_at
        now = utc_now()
        if task.task_kind == "inspection" and task.linked_item_id:
            item = self.inventory.get(task.linked_item_id)
            if item is not None:
                item.next_check_at = next_due
                if checked_at is not None:
                    item.last_checked = checked_at.date()
                item.updated_at = now
                item.revision += 1
        elif task.task_kind == "container_inspection" and task.linked_container_id:
            container = self.containers.get(task.linked_container_id)
            if container is not None:
                container.next_check_at = (
                    datetime.combine(next_due, datetime.min.time(), tzinfo=UTC)
                    if next_due is not None
                    else None
                )
                if checked_at is not None:
                    container.last_checked_at = checked_at
                container.updated_at = now
                container.revision += 1
        elif task.task_kind == "asset_inspection" and task.linked_asset_id:
            asset = self.assets.get(task.linked_asset_id)
            if asset is not None:
                asset.next_check_at = (
                    datetime.combine(next_due, datetime.min.time(), tzinfo=UTC)
                    if next_due is not None
                    else None
                )
                if checked_at is not None:
                    asset.last_checked_at = checked_at
                asset.updated_at = now
                asset.revision += 1

    def create(self, payload: TaskCreate) -> TaskModel:
        household_id = str(payload.household_id)
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")
        task = TaskModel(
            id=str(uuid4()),
            household_id=household_id,
            name=payload.name,
            task_kind=payload.task_kind.value,
            category=payload.category,
            linked_item_id=self._validate_link(
                household_id, self.inventory, payload.linked_item_id, "Inventory item"
            ),
            linked_container_id=self._validate_link(
                household_id, self.containers, payload.linked_container_id, "Container"
            ),
            linked_asset_id=self._validate_link(
                household_id, self.assets, payload.linked_asset_id, "Asset"
            ),
            recurrence_type=payload.recurrence_type.value,
            recurrence_interval=payload.recurrence_interval,
            reschedule_mode=payload.reschedule_mode.value,
            last_completed_at=payload.last_completed_at,
            next_due_at=payload.next_due_at,
            reminder_before_days=payload.reminder_before_days,
            enabled=payload.enabled,
            notes=payload.notes,
            completion_count=payload.completion_count,
        )
        self.repository.add(task)
        self._sync_linked_resource(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get(self, task_id: UUID) -> TaskModel:
        task = self.repository.get(str(task_id))
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, task_id: UUID, payload: TaskUpdate) -> TaskModel:
        task = self.get(task_id)
        if task.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {task.revision}"
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        enum_fields = {"task_kind", "recurrence_type", "reschedule_mode"}
        link_fields = {
            "linked_item_id": (self.inventory, "Inventory item"),
            "linked_container_id": (self.containers, "Container"),
            "linked_asset_id": (self.assets, "Asset"),
        }
        for field in enum_fields:
            if field in changes and changes[field] is not None:
                changes[field] = changes[field].value
        for field, (repository, label) in link_fields.items():
            if field in changes:
                changes[field] = self._validate_link(
                    task.household_id, repository, changes[field], label
                )
        for field, value in changes.items():
            setattr(task, field, value)
        task.revision += 1
        task.updated_at = utc_now()
        self._sync_linked_resource(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def complete(self, task_id: UUID, payload: TaskComplete) -> TaskModel:
        task = self.get(task_id)
        if task.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {task.revision}"
            )
        completed_on = payload.completed_on or date.today()
        task.last_completed_at = datetime.combine(
            completed_on, datetime.min.time(), tzinfo=UTC
        )
        task.next_due_at = calculate_next_due(task, completed_on)
        task.completion_count += 1
        task.revision += 1
        task.updated_at = utc_now()
        self._sync_linked_resource(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: UUID, expected_revision: int) -> TaskModel:
        task = self.get(task_id)
        if task.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {task.revision}"
            )
        task.enabled = False
        self._sync_linked_resource(task)
        now = utc_now()
        task.deleted_at = now
        task.updated_at = now
        task.revision += 1
        self.session.commit()
        self.session.refresh(task)
        return task


class InventoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = InventoryRepository(session)
        self.households = HouseholdRepository(session)
        self.containers = ContainerRepository(session)

    def _validate_container(
        self,
        household_id: str,
        container_id: UUID | None,
    ) -> str | None:
        if container_id is None:
            return None
        container = self.containers.get(str(container_id))
        if container is None or container.household_id != household_id:
            raise NotFoundError("Container not found in this household")
        return container.id

    def create(self, payload: InventoryCreate) -> InventoryItemModel:
        household_id = str(payload.household_id)
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")
        item = InventoryItemModel(
            id=str(uuid4()),
            household_id=household_id,
            name=payload.name,
            category=payload.category,
            item_type=payload.item_type,
            quantity=payload.quantity,
            unit=payload.unit,
            expires_at=payload.expires_at,
            last_checked=payload.last_checked,
            next_check_at=payload.next_check_at,
            notes=payload.notes,
            container_id=self._validate_container(household_id, payload.container_id),
        )
        self.repository.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get(self, item_id: UUID) -> InventoryItemModel:
        item = self.repository.get(str(item_id))
        if item is None:
            raise NotFoundError("Inventory item not found")
        return item

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, item_id: UUID, payload: InventoryUpdate) -> InventoryItemModel:
        item = self.get(item_id)
        if item.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {item.revision}"
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "container_id" in changes:
            changes["container_id"] = self._validate_container(
                item.household_id,
                changes["container_id"],
            )
        for field, value in changes.items():
            setattr(item, field, value)
        item.revision += 1
        item.updated_at = utc_now()
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item_id: UUID, expected_revision: int) -> InventoryItemModel:
        item = self.get(item_id)
        if item.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {item.revision}"
            )
        now = utc_now()
        item.deleted_at = now
        item.updated_at = now
        item.revision += 1
        self.session.commit()
        self.session.refresh(item)
        return item
