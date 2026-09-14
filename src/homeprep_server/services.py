from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.orm import Session

from homeprep_server.models import ContainerModel, HouseholdModel, InventoryItemModel
from homeprep_server.repositories import (
    ContainerRepository,
    HouseholdRepository,
    InventoryRepository,
)
from homeprep_server.schemas import (
    ContainerCreate,
    ContainerUpdate,
    HouseholdCreate,
    InventoryCreate,
    InventoryUpdate,
)


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


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
