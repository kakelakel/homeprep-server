from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from homeprep_server.models import Base, utc_now
from homeprep_server.repositories import (
    ContainerRepository,
    HouseholdRepository,
    InventoryRepository,
)
from homeprep_server.services import ConflictError, NotFoundError

SHOPPING_STATUSES = {"pending", "purchased", "ignored"}
SHOPPING_SOURCES = {
    "manual",
    "inventory_expired",
    "target_shortage",
    "plan_requirement",
    "container_requirement",
    "asset_maintenance",
}


class ShoppingContractModel(Base):
    """Canonical shopping mapper matching Home Assistant schema v1."""

    __tablename__ = "shopping_items"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="piece")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="other")
    container_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ignored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Legacy fields stay coherent during the upgrade window.
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_inventory_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ShoppingContractService:
    def __init__(self, session: Session):
        self.session = session
        self.households = HouseholdRepository(session)
        self.containers = ContainerRepository(session)
        self.inventory = InventoryRepository(session)

    def _require_household(self, household_id: str) -> None:
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")

    def _validate_container(self, household_id: str, container_id: UUID | None) -> str | None:
        if container_id is None:
            return None
        container = self.containers.get(str(container_id))
        if container is None or container.household_id != household_id:
            raise NotFoundError("Container not found in this household")
        return container.id

    def _source_exists(self, household_id: str, source_type: str, source_id: str) -> bool:
        return (
            self.session.scalar(
                select(ShoppingContractModel.id).where(
                    ShoppingContractModel.household_id == household_id,
                    ShoppingContractModel.source_type == source_type,
                    ShoppingContractModel.source_id == source_id,
                    ShoppingContractModel.deleted_at.is_(None),
                )
            )
            is not None
        )

    def sync_expired_inventory(self, household_id: UUID) -> int:
        key = str(household_id)
        self._require_household(key)
        today = date.today()
        created = 0
        for inventory_item in self.inventory.list_for_household(key):
            if inventory_item.expires_at is None or inventory_item.expires_at >= today:
                continue
            if self._source_exists(key, "inventory_expired", inventory_item.id):
                continue
            reason = f"Automatically added · Expired {inventory_item.expires_at.isoformat()}"
            item = ShoppingContractModel(
                id=str(uuid4()),
                household_id=key,
                name=inventory_item.name,
                quantity=inventory_item.quantity,
                unit=inventory_item.unit,
                category=inventory_item.category,
                container_id=inventory_item.container_id,
                source_type="inventory_expired",
                source_id=inventory_item.id,
                reason=reason,
                status="pending",
                notes=None,
                source="expired_inventory",
                source_inventory_item_id=inventory_item.id,
                completed=False,
            )
            self.session.add(item)
            created += 1
        if created:
            self.session.commit()
        return created

    def list_for_household(self, household_id: UUID) -> Sequence[ShoppingContractModel]:
        key = str(household_id)
        self._require_household(key)
        self.sync_expired_inventory(household_id)
        return self.session.scalars(
            select(ShoppingContractModel)
            .where(
                ShoppingContractModel.household_id == key,
                ShoppingContractModel.deleted_at.is_(None),
            )
            .order_by(
                (ShoppingContractModel.status != "pending").asc(),
                ShoppingContractModel.created_at.desc(),
                ShoppingContractModel.id.asc(),
            )
        ).all()

    def get(self, item_id: UUID) -> ShoppingContractModel:
        item = self.session.scalar(
            select(ShoppingContractModel).where(
                ShoppingContractModel.id == str(item_id),
                ShoppingContractModel.deleted_at.is_(None),
            )
        )
        if item is None:
            raise NotFoundError("Shopping item not found")
        return item

    def create(
        self,
        *,
        household_id: UUID,
        name: str,
        quantity: float,
        unit: str,
        category: str,
        container_id: UUID | None,
        source_type: str,
        source_id: UUID | None,
        reason: str | None,
        status: str,
        notes: str | None,
    ) -> ShoppingContractModel:
        key = str(household_id)
        self._require_household(key)
        if source_type not in SHOPPING_SOURCES:
            raise ConflictError(f"Unsupported shopping source: {source_type}")
        if status not in SHOPPING_STATUSES:
            raise ConflictError(f"Unsupported shopping status: {status}")
        container_key = self._validate_container(key, container_id)
        now = utc_now()
        item = ShoppingContractModel(
            id=str(uuid4()),
            household_id=key,
            name=name.strip(),
            quantity=max(0.0, quantity),
            unit=unit or "piece",
            category=category or "other",
            container_id=container_key,
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            reason=reason,
            status=status,
            notes=notes,
            purchased_at=now if status == "purchased" else None,
            ignored_at=now if status == "ignored" else None,
            source="expired_inventory" if source_type == "inventory_expired" else source_type,
            source_inventory_item_id=(
                str(source_id) if source_type == "inventory_expired" and source_id else None
            ),
            completed=status == "purchased",
            completed_at=now if status == "purchased" else None,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update(
        self,
        item_id: UUID,
        *,
        expected_revision: int,
        changes: dict,
    ) -> ShoppingContractModel:
        item = self.get(item_id)
        if item.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {item.revision}"
            )
        if "container_id" in changes:
            raw_container = changes["container_id"]
            changes["container_id"] = self._validate_container(
                item.household_id, UUID(str(raw_container)) if raw_container else None
            )
        if "source_type" in changes and changes["source_type"] not in SHOPPING_SOURCES:
            raise ConflictError(f"Unsupported shopping source: {changes['source_type']}")
        if "status" in changes:
            shopping_status = changes["status"]
            if shopping_status not in SHOPPING_STATUSES:
                raise ConflictError(f"Unsupported shopping status: {shopping_status}")
            now = utc_now()
            changes["purchased_at"] = now if shopping_status == "purchased" else None
            changes["ignored_at"] = now if shopping_status == "ignored" else None
            item.completed = shopping_status == "purchased"
            item.completed_at = now if shopping_status == "purchased" else None
        if "source_type" in changes:
            item.source = (
                "expired_inventory"
                if changes["source_type"] == "inventory_expired"
                else changes["source_type"]
            )
        if "source_id" in changes:
            item.source_inventory_item_id = (
                str(changes["source_id"])
                if changes.get("source_type", item.source_type) == "inventory_expired"
                and changes["source_id"]
                else None
            )
            changes["source_id"] = str(changes["source_id"]) if changes["source_id"] else None
        for field, value in changes.items():
            setattr(item, field, value)
        item.updated_at = utc_now()
        item.revision += 1
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item_id: UUID, expected_revision: int) -> ShoppingContractModel:
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
