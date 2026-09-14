from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from homeprep_server.models import (
    AssetModel,
    ContainerModel,
    HouseholdModel,
    InventoryItemModel,
    TaskModel,
)


class HouseholdRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, household: HouseholdModel) -> HouseholdModel:
        self.session.add(household)
        self.session.flush()
        self.session.refresh(household)
        return household

    def get(self, household_id: str) -> HouseholdModel | None:
        statement = select(HouseholdModel).where(
            HouseholdModel.id == household_id,
            HouseholdModel.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_all(self) -> Sequence[HouseholdModel]:
        statement = (
            select(HouseholdModel)
            .where(HouseholdModel.deleted_at.is_(None))
            .order_by(HouseholdModel.name.asc(), HouseholdModel.id.asc())
        )
        return self.session.scalars(statement).all()


class ContainerRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, container: ContainerModel) -> ContainerModel:
        self.session.add(container)
        self.session.flush()
        self.session.refresh(container)
        return container

    def get(self, container_id: str) -> ContainerModel | None:
        statement = select(ContainerModel).where(
            ContainerModel.id == container_id,
            ContainerModel.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_for_household(self, household_id: str) -> Sequence[ContainerModel]:
        statement = (
            select(ContainerModel)
            .where(
                ContainerModel.household_id == household_id,
                ContainerModel.deleted_at.is_(None),
            )
            .order_by(ContainerModel.name.asc(), ContainerModel.id.asc())
        )
        return self.session.scalars(statement).all()


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, asset: AssetModel) -> AssetModel:
        self.session.add(asset)
        self.session.flush()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: str) -> AssetModel | None:
        statement = select(AssetModel).where(
            AssetModel.id == asset_id,
            AssetModel.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_for_household(self, household_id: str) -> Sequence[AssetModel]:
        statement = (
            select(AssetModel)
            .where(
                AssetModel.household_id == household_id,
                AssetModel.deleted_at.is_(None),
            )
            .order_by(AssetModel.name.asc(), AssetModel.id.asc())
        )
        return self.session.scalars(statement).all()


class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def get(self, task_id: str) -> TaskModel | None:
        statement = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_for_household(self, household_id: str) -> Sequence[TaskModel]:
        statement = (
            select(TaskModel)
            .where(
                TaskModel.household_id == household_id,
                TaskModel.deleted_at.is_(None),
            )
            .order_by(TaskModel.next_due_at.asc(), TaskModel.name.asc(), TaskModel.id.asc())
        )
        return self.session.scalars(statement).all()


class InventoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, item: InventoryItemModel) -> InventoryItemModel:
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def get(self, item_id: str) -> InventoryItemModel | None:
        statement = select(InventoryItemModel).where(
            InventoryItemModel.id == item_id,
            InventoryItemModel.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_for_household(self, household_id: str) -> Sequence[InventoryItemModel]:
        statement = (
            select(InventoryItemModel)
            .where(
                InventoryItemModel.household_id == household_id,
                InventoryItemModel.deleted_at.is_(None),
            )
            .order_by(InventoryItemModel.name.asc(), InventoryItemModel.id.asc())
        )
        return self.session.scalars(statement).all()
