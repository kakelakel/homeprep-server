from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from homeprep_server.models import HouseholdModel, InventoryItemModel
from homeprep_server.repositories import HouseholdRepository, InventoryRepository
from homeprep_server.schemas import HouseholdCreate, InventoryCreate, InventoryUpdate


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


class InventoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = InventoryRepository(session)
        self.households = HouseholdRepository(session)

    def create(self, payload: InventoryCreate) -> InventoryItemModel:
        if self.households.get(str(payload.household_id)) is None:
            raise NotFoundError("Household not found")

        item = InventoryItemModel(
            id=str(uuid4()),
            household_id=str(payload.household_id),
            name=payload.name,
            category=payload.category,
            item_type=payload.item_type,
            quantity=payload.quantity,
            unit=payload.unit,
            expires_at=payload.expires_at,
            last_checked=payload.last_checked,
            next_check_at=payload.next_check_at,
            notes=payload.notes,
            container_id=str(payload.container_id) if payload.container_id else None,
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
            container_id = changes["container_id"]
            changes["container_id"] = str(container_id) if container_id else None

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
