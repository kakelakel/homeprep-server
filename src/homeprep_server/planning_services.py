from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from homeprep_server.models import HouseholdProfileModel, PlanModel, TargetModel
from homeprep_server.repositories import (
    AssetRepository,
    ContainerRepository,
    HouseholdProfileRepository,
    HouseholdRepository,
    InventoryRepository,
    PlanRepository,
    TargetRepository,
)
from homeprep_server.schemas import (
    HouseholdProfileUpsert,
    PlanChecklistItem,
    PlanCreate,
    PlanUpdate,
    TargetCreate,
    TargetUpdate,
)
from homeprep_server.services import ConflictError, NotFoundError


def utc_now() -> datetime:
    return datetime.now(UTC)


class HouseholdProfileService:
    def __init__(self, session: Session):
        self.session = session
        self.households = HouseholdRepository(session)
        self.repository = HouseholdProfileRepository(session)

    def get(self, household_id: UUID) -> HouseholdProfileModel:
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        profile = self.repository.get(str(household_id))
        if profile is None:
            raise NotFoundError("Household profile not configured")
        return profile

    def upsert(
        self,
        household_id: UUID,
        payload: HouseholdProfileUpsert,
    ) -> HouseholdProfileModel:
        household_key = str(household_id)
        if self.households.get(household_key) is None:
            raise NotFoundError("Household not found")
        profile = self.repository.get(household_key)
        if profile is None:
            if payload.expected_revision is not None:
                raise ConflictError("Household profile does not exist yet")
            profile = HouseholdProfileModel(household_id=household_key)
            self.repository.add(profile)
        elif payload.expected_revision is not None and profile.revision != payload.expected_revision:
            raise ConflictError(
                "Revision mismatch: expected "
                f"{payload.expected_revision}, current {profile.revision}"
            )
        changes = payload.model_dump(exclude={"expected_revision"})
        country_code = changes.get("country_code")
        changes["country_code"] = country_code.upper() if country_code else None
        for field, value in changes.items():
            setattr(profile, field, value)
        if profile.created_at is None:
            profile.created_at = utc_now()
        profile.updated_at = utc_now()
        if payload.expected_revision is not None:
            profile.revision += 1
        self.session.commit()
        self.session.refresh(profile)
        return profile


class TargetService:
    def __init__(self, session: Session):
        self.session = session
        self.households = HouseholdRepository(session)
        self.repository = TargetRepository(session)

    def _normalize_requirements(self, requirements) -> list[dict]:
        return [requirement.model_dump(mode="json") for requirement in requirements]

    def _validate_numeric_target(self, target_type: str, matcher: dict) -> None:
        if target_type in {"quantity", "count"} and not matcher:
            raise ConflictError("A numeric target requires a matcher")

    def create(self, payload: TargetCreate) -> TargetModel:
        household_id = str(payload.household_id)
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")
        target_type = payload.target_type.value
        self._validate_numeric_target(target_type, payload.matcher)
        requirements = self._normalize_requirements(payload.requirements)
        valid_ids = {item["id"] for item in requirements}
        completed_ids = [
            value for value in payload.completed_requirement_ids if value in valid_ids
        ]
        target = TargetModel(
            id=str(uuid4()),
            household_id=household_id,
            name=payload.name,
            category=payload.category,
            target_type=target_type,
            matcher=payload.matcher,
            unit=payload.unit,
            minimum_value=payload.minimum_value,
            target_value=payload.target_value,
            current_value=payload.current_value,
            requirements=requirements,
            completed_requirement_ids=completed_ids,
            priority=payload.priority,
            enabled=payload.enabled,
            notes=payload.notes,
            origin=payload.origin.value,
            source_profile_id=payload.source_profile_id,
            source_recommendation_id=payload.source_recommendation_id,
            source_profile_version=payload.source_profile_version,
        )
        self.repository.add(target)
        self.session.commit()
        self.session.refresh(target)
        return target

    def get(self, target_id: UUID) -> TargetModel:
        target = self.repository.get(str(target_id))
        if target is None:
            raise NotFoundError("Target not found")
        return target

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, target_id: UUID, payload: TargetUpdate) -> TargetModel:
        target = self.get(target_id)
        if target.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {target.revision}"
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "target_type" in changes and changes["target_type"] is not None:
            changes["target_type"] = changes["target_type"].value
        if "requirements" in changes and changes["requirements"] is not None:
            changes["requirements"] = self._normalize_requirements(changes["requirements"])
        target_type = changes.get("target_type", target.target_type)
        matcher = changes.get("matcher", target.matcher)
        self._validate_numeric_target(target_type, matcher)
        requirements = changes.get("requirements", target.requirements)
        valid_ids = {item["id"] for item in requirements}
        if "completed_requirement_ids" in changes:
            changes["completed_requirement_ids"] = [
                value for value in changes["completed_requirement_ids"] if value in valid_ids
            ]
        for field, value in changes.items():
            setattr(target, field, value)
        target.updated_at = utc_now()
        target.revision += 1
        self.session.commit()
        self.session.refresh(target)
        return target

    def delete(self, target_id: UUID, expected_revision: int) -> TargetModel:
        target = self.get(target_id)
        if target.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {target.revision}"
            )
        now = utc_now()
        target.deleted_at = now
        target.updated_at = now
        target.revision += 1
        self.session.commit()
        self.session.refresh(target)
        return target


class PlanService:
    def __init__(self, session: Session):
        self.session = session
        self.households = HouseholdRepository(session)
        self.repository = PlanRepository(session)
        self.inventory = InventoryRepository(session)
        self.containers = ContainerRepository(session)
        self.assets = AssetRepository(session)

    def _validate_link(self, household_id: str, repository, raw_id: UUID, label: str) -> str:
        linked = repository.get(str(raw_id))
        if linked is None or linked.household_id != household_id:
            raise NotFoundError(f"{label} not found in this household")
        return linked.id

    def _normalize_checklist(
        self,
        household_id: str,
        checklist: list[PlanChecklistItem],
    ) -> list[dict]:
        result: list[dict] = []
        for item in checklist:
            result.append(
                {
                    "id": item.id or str(uuid4()),
                    "label": item.label,
                    "description": item.description,
                    "completed": item.completed,
                    "last_confirmed_at": (
                        item.last_confirmed_at.isoformat()
                        if item.last_confirmed_at is not None
                        else None
                    ),
                    "linked_inventory_item_ids": [
                        self._validate_link(household_id, self.inventory, value, "Inventory item")
                        for value in item.linked_inventory_item_ids
                    ],
                    "linked_container_ids": [
                        self._validate_link(household_id, self.containers, value, "Container")
                        for value in item.linked_container_ids
                    ],
                    "linked_asset_ids": [
                        self._validate_link(household_id, self.assets, value, "Asset")
                        for value in item.linked_asset_ids
                    ],
                }
            )
        return result

    def create(self, payload: PlanCreate) -> PlanModel:
        household_id = str(payload.household_id)
        if self.households.get(household_id) is None:
            raise NotFoundError("Household not found")
        plan = PlanModel(
            id=str(uuid4()),
            household_id=household_id,
            name=payload.name,
            plan_type=payload.plan_type.value,
            description=payload.description,
            meeting_point=payload.meeting_point,
            enabled=payload.enabled,
            checklist=self._normalize_checklist(household_id, payload.checklist),
            review_interval_months=payload.review_interval_months,
            last_reviewed_at=payload.last_reviewed_at,
            next_review_at=payload.next_review_at,
            notes=payload.notes,
        )
        self.repository.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def get(self, plan_id: UUID) -> PlanModel:
        plan = self.repository.get(str(plan_id))
        if plan is None:
            raise NotFoundError("Plan not found")
        return plan

    def list_for_household(self, household_id: UUID):
        if self.households.get(str(household_id)) is None:
            raise NotFoundError("Household not found")
        return self.repository.list_for_household(str(household_id))

    def update(self, plan_id: UUID, payload: PlanUpdate) -> PlanModel:
        plan = self.get(plan_id)
        if plan.revision != payload.expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {payload.expected_revision}, current {plan.revision}"
            )
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "plan_type" in changes and changes["plan_type"] is not None:
            changes["plan_type"] = changes["plan_type"].value
        if "checklist" in changes and changes["checklist"] is not None:
            changes["checklist"] = self._normalize_checklist(
                plan.household_id, changes["checklist"]
            )
        for field, value in changes.items():
            setattr(plan, field, value)
        plan.updated_at = utc_now()
        plan.revision += 1
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def delete(self, plan_id: UUID, expected_revision: int) -> PlanModel:
        plan = self.get(plan_id)
        if plan.revision != expected_revision:
            raise ConflictError(
                f"Revision mismatch: expected {expected_revision}, current {plan.revision}"
            )
        now = utc_now()
        plan.deleted_at = now
        plan.updated_at = now
        plan.revision += 1
        self.session.commit()
        self.session.refresh(plan)
        return plan
