from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from homeprep_server.models import Base, utc_now
from homeprep_server.repositories import HouseholdRepository, InventoryRepository, TaskRepository
from homeprep_server.services import ConflictError, NotFoundError
from homeprep_server.shopping_contract import ShoppingContractModel

# Keep the operations service compatibility layer on the canonical shopping
# mapper. Defining a second mapper for the same shopping_items table made
# SQLAlchemy metadata accumulate duplicate implicit indexes during bootstrap.
ShoppingItemModel = ShoppingContractModel


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    household_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("households.id"), index=True, nullable=False
    )
    event_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="attention"
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ShoppingRepository:
    """Compatibility repository over the canonical shopping mapper.

    New API code uses ``ShoppingContractService`` directly. This repository is
    retained for internal notification/legacy callers until those call sites
    are fully removed, but it deliberately shares the canonical table mapper.
    """

    def __init__(self, session: Session):
        self.session = session

    def add(self, item: ShoppingItemModel) -> ShoppingItemModel:
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def get(self, item_id: str) -> ShoppingItemModel | None:
        return self.session.scalar(
            select(ShoppingItemModel).where(
                ShoppingItemModel.id == item_id,
                ShoppingItemModel.deleted_at.is_(None),
            )
        )

    def list_for_household(self, household_id: str) -> Sequence[ShoppingItemModel]:
        return self.session.scalars(
            select(ShoppingItemModel)
            .where(
                ShoppingItemModel.household_id == household_id,
                ShoppingItemModel.deleted_at.is_(None),
            )
            .order_by(
                (ShoppingItemModel.status != "pending").asc(),
                ShoppingItemModel.created_at.desc(),
                ShoppingItemModel.id.asc(),
            )
        ).all()

    def source_exists(self, household_id: str, inventory_item_id: str) -> bool:
        return (
            self.session.scalar(
                select(ShoppingItemModel.id).where(
                    ShoppingItemModel.household_id == household_id,
                    ShoppingItemModel.source_type == "inventory_expired",
                    ShoppingItemModel.source_id == inventory_item_id,
                    ShoppingItemModel.deleted_at.is_(None),
                )
            )
            is not None
        )


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, notification_id: str) -> NotificationModel | None:
        return self.session.get(NotificationModel, notification_id)

    def by_event_key(self, event_key: str) -> NotificationModel | None:
        return self.session.scalar(
            select(NotificationModel).where(NotificationModel.event_key == event_key)
        )

    def list_for_household(self, household_id: str) -> Sequence[NotificationModel]:
        return self.session.scalars(
            select(NotificationModel)
            .where(
                NotificationModel.household_id == household_id,
                NotificationModel.dismissed_at.is_(None),
            )
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.asc())
        ).all()


class ShoppingService:
    """Legacy compatibility facade.

    The public shopping API uses ``ShoppingContractService``. Keep this facade
    coherent with schema v1 for older internal callers while avoiding a second
    SQLAlchemy model for the same table.
    """

    def __init__(self, session: Session):
        self.session = session
        self.repository = ShoppingRepository(session)
        self.households = HouseholdRepository(session)
        self.inventory = InventoryRepository(session)

    def _require_household(self, household_id: str) -> None:
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")

    def sync_expired(self, household_id: UUID) -> int:
        key = str(household_id)
        self._require_household(key)
        today = date.today()
        created = 0
        for inventory_item in self.inventory.list_for_household(key):
            if inventory_item.expires_at is None or inventory_item.expires_at >= today:
                continue
            if self.repository.source_exists(key, inventory_item.id):
                continue
            reason = f"Automatically added · Expired {inventory_item.expires_at.isoformat()}"
            self.repository.add(
                ShoppingItemModel(
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
            )
            created += 1
        if created:
            self.session.commit()
        return created

    def list_for_household(self, household_id: UUID):
        self.sync_expired(household_id)
        return self.repository.list_for_household(str(household_id))

    def create_manual(
        self,
        household_id: UUID,
        *,
        name: str,
        quantity: float,
        unit: str,
        category: str,
        notes: str | None,
    ) -> ShoppingItemModel:
        key = str(household_id)
        self._require_household(key)
        item = ShoppingItemModel(
            id=str(uuid4()),
            household_id=key,
            name=name,
            quantity=quantity,
            unit=unit,
            category=category,
            source_type="manual",
            status="pending",
            source="manual",
            completed=False,
            notes=notes,
        )
        self.repository.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get(self, item_id: UUID) -> ShoppingItemModel:
        item = self.repository.get(str(item_id))
        if item is None:
            raise NotFoundError("Shopping item not found")
        return item

    def update(
        self,
        item_id: UUID,
        *,
        expected_revision: int,
        changes: dict,
    ) -> ShoppingItemModel:
        item = self.get(item_id)
        if item.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {item.revision}"
            )
        if "completed" in changes:
            item.completed_at = utc_now() if changes["completed"] else None
        for field, value in changes.items():
            setattr(item, field, value)
        item.updated_at = utc_now()
        item.revision += 1
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item_id: UUID, expected_revision: int) -> ShoppingItemModel:
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


class NotificationService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = NotificationRepository(session)
        self.households = HouseholdRepository(session)
        self.inventory = InventoryRepository(session)
        self.tasks = TaskRepository(session)

    def _upsert_event(
        self,
        household_id: str,
        *,
        event_key: str,
        kind: str,
        severity: str,
        title: str,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        if self.repository.by_event_key(event_key) is not None:
            return
        self.session.add(
            NotificationModel(
                id=str(uuid4()),
                household_id=household_id,
                event_key=event_key,
                kind=kind,
                severity=severity,
                title=title,
                message=message,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    def sync_household(self, household_id: UUID) -> int:
        key = str(household_id)
        if self.households.get(key) is None:
            raise NotFoundError("Household not found")
        before = self.session.scalar(select(func.count()).select_from(NotificationModel)) or 0
        today = date.today()
        soon = today + timedelta(days=30)
        for item in self.inventory.list_for_household(key):
            if item.expires_at is None:
                continue
            if item.expires_at < today:
                self._upsert_event(
                    key,
                    event_key=f"inventory-expired:{item.id}:{item.expires_at.isoformat()}",
                    kind="inventory_expired",
                    severity="critical",
                    title=f"{item.name} has expired",
                    message=(
                        f"Expired on {item.expires_at}. Replace or review this inventory item."
                    ),
                    resource_type="inventory",
                    resource_id=item.id,
                )
            elif item.expires_at <= soon:
                self._upsert_event(
                    key,
                    event_key=f"inventory-expiring:{item.id}:{item.expires_at.isoformat()}",
                    kind="inventory_expiring",
                    severity="attention",
                    title=f"{item.name} expires soon",
                    message=f"Expiry date: {item.expires_at}.",
                    resource_type="inventory",
                    resource_id=item.id,
                )
        for task in self.tasks.list_for_household(key):
            if not task.enabled or task.next_due_at is None:
                continue
            if task.next_due_at < today:
                severity, kind, wording = "critical", "task_overdue", "is overdue"
            elif task.next_due_at == today:
                severity, kind, wording = "attention", "task_due", "is due today"
            elif task.reminder_before_days and today >= task.next_due_at - timedelta(
                days=task.reminder_before_days
            ):
                severity, kind, wording = "attention", "task_reminder", "is coming up"
            else:
                continue
            self._upsert_event(
                key,
                event_key=f"{kind}:{task.id}:{task.next_due_at.isoformat()}",
                kind=kind,
                severity=severity,
                title=f"{task.name} {wording}",
                message=f"Next due date: {task.next_due_at}.",
                resource_type="task",
                resource_id=task.id,
            )
        self.session.commit()
        after = self.session.scalar(select(func.count()).select_from(NotificationModel)) or 0
        return max(0, after - before)

    def list_for_household(self, household_id: UUID):
        self.sync_household(household_id)
        return self.repository.list_for_household(str(household_id))

    def mark_read(self, notification_id: UUID) -> NotificationModel:
        notification = self.repository.get(str(notification_id))
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.read_at is None:
            notification.read_at = utc_now()
            self.session.commit()
            self.session.refresh(notification)
        return notification

    def dismiss(self, notification_id: UUID) -> NotificationModel:
        notification = self.repository.get(str(notification_id))
        if notification is None:
            raise NotFoundError("Notification not found")
        notification.dismissed_at = utc_now()
        self.session.commit()
        self.session.refresh(notification)
        return notification
