from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from homeprep_server.api.client_auth import PrincipalDep, WritePrincipalDep
from homeprep_server.database import get_session
from homeprep_server.planning_services import PlanService
from homeprep_server.schemas import PlanCreate, PlanRead, PlanUpdate
from homeprep_server.services import ConflictError, NotFoundError

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])
SessionDep = Annotated[Session, Depends(get_session)]
ExpectedRevision = Annotated[int, Query(ge=1)]

PLAN_TEMPLATES: dict[str, dict] = {
    "fire": {
        "name": "Fire safety plan",
        "plan_type": "fire",
        "description": (
            "Household fire preparedness, evacuation and equipment readiness."
        ),
        "review_interval_months": 6,
        "checklist": [
            {"label": "A household meeting point outside the home has been agreed"},
            {"label": "Everyone knows the primary evacuation route"},
            {"label": "Alternative escape routes have been considered"},
            {"label": "Smoke alarms are installed in suitable locations"},
            {"label": "Smoke alarms have been tested recently"},
            {
                "label": (
                    "Fire extinguisher or other suitable extinguishing equipment "
                    "is available"
                )
            },
            {"label": "Fire blanket is available where appropriate"},
            {"label": "Children know what to do if the alarm sounds"},
        ],
    },
    "flood": {
        "name": "Flood and water damage plan",
        "plan_type": "flood",
        "description": "Reduce the impact of leaks, flooding and water-related damage.",
        "review_interval_months": 6,
        "checklist": [
            {"label": "The main water shutoff is known and accessible"},
            {"label": "Household members know how to shut off the water"},
            {"label": "Leak sensors are installed in relevant areas"},
            {"label": "Leak sensors have been tested recently"},
            {"label": "Floor drains and drainage routes are accessible and clear"},
            {"label": "Washing-machine and dishwasher hoses have been inspected"},
            {
                "label": (
                    "Important documents and vulnerable valuables are stored above "
                    "likely flood level"
                )
            },
            {"label": "Any sump pump or drainage pump has been tested"},
        ],
    },
    "evacuation": {
        "name": "Rapid evacuation plan",
        "plan_type": "evacuation",
        "description": (
            "Be ready to leave the home quickly with the people and essentials that "
            "matter most."
        ),
        "review_interval_months": 6,
        "checklist": [
            {"label": "Primary exit routes are known"},
            {"label": "A household meeting point has been agreed"},
            {"label": "Go bag or evacuation kit is ready"},
            {"label": "Essential medicines can be taken quickly"},
            {"label": "Important documents or copies are accessible"},
            {"label": "Children and dependants have a clear evacuation routine"},
            {"label": "Pet transport and essential pet supplies are planned"},
            {
                "label": (
                    "A contact outside the household knows the emergency plan"
                )
            },
        ],
    },
}


class PlanTemplateCreate(BaseModel):
    household_id: UUID
    template_id: str = Field(min_length=1, max_length=64)


class PlanReview(BaseModel):
    expected_revision: int = Field(ge=1)
    reviewed_on: date | None = None


class ChecklistToggle(BaseModel):
    expected_revision: int = Field(ge=1)
    completed: bool | None = None


class ChecklistCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    linked_inventory_item_ids: list[UUID] = Field(default_factory=list)
    linked_container_ids: list[UUID] = Field(default_factory=list)
    linked_asset_ids: list[UUID] = Field(default_factory=list)


class ChecklistUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    linked_inventory_item_ids: list[UUID] | None = None
    linked_container_ids: list[UUID] | None = None
    linked_asset_ids: list[UUID] | None = None


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error")


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _require_revision(plan, expected_revision: int) -> None:
    if plan.revision != expected_revision:
        raise ConflictError(
            f"Revision mismatch: expected {expected_revision}, current {plan.revision}"
        )


def _checklist_copy(plan) -> list[dict]:
    return [dict(item) for item in plan.checklist]


@router.get("/templates")
def list_plan_templates(principal: PrincipalDep) -> list[dict]:
    del principal
    return [
        {
            "id": key,
            "name": value["name"],
            "plan_type": value["plan_type"],
            "description": value["description"],
        }
        for key, value in PLAN_TEMPLATES.items()
    ]


@router.post(
    "/from-template",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_plan_from_template(
    payload: PlanTemplateCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    template = PLAN_TEMPLATES.get(payload.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Plan template not found")
    try:
        return PlanService(session).create(
            PlanCreate(household_id=payload.household_id, **template)
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).create(payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[PlanRead])
def list_plans(
    household_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[PlanRead]:
    del principal
    try:
        return list(PlanService(session).list_for_household(household_id))
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(
    plan_id: UUID,
    session: SessionDep,
    principal: PrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).get(plan_id)
    except NotFoundError as exc:
        raise _translate_error(exc) from exc


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: UUID,
    payload: PlanUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).update(plan_id, payload)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{plan_id}/review", response_model=PlanRead)
def mark_plan_reviewed(
    plan_id: UUID,
    payload: PlanReview,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    service = PlanService(session)
    try:
        plan = service.get(plan_id)
        _require_revision(plan, payload.expected_revision)
        reviewed = payload.reviewed_on or date.today()
        next_review = (
            _add_months(reviewed, plan.review_interval_months)
            if plan.review_interval_months
            else None
        )
        return service.update(
            plan_id,
            PlanUpdate(
                expected_revision=plan.revision,
                last_reviewed_at=datetime.combine(reviewed, datetime.min.time()),
                next_review_at=next_review,
            ),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{plan_id}/checklist", response_model=PlanRead)
def add_plan_checklist_item(
    plan_id: UUID,
    payload: ChecklistCreate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    service = PlanService(session)
    try:
        plan = service.get(plan_id)
        _require_revision(plan, payload.expected_revision)
        checklist = _checklist_copy(plan)
        checklist.append(
            {
                "label": payload.label,
                "description": payload.description,
                "completed": False,
                "linked_inventory_item_ids": payload.linked_inventory_item_ids,
                "linked_container_ids": payload.linked_container_ids,
                "linked_asset_ids": payload.linked_asset_ids,
            }
        )
        return service.update(
            plan_id,
            PlanUpdate(expected_revision=plan.revision, checklist=checklist),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.patch("/{plan_id}/checklist/{item_id}", response_model=PlanRead)
def update_plan_checklist_item(
    plan_id: UUID,
    item_id: str,
    payload: ChecklistUpdate,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    service = PlanService(session)
    try:
        plan = service.get(plan_id)
        _require_revision(plan, payload.expected_revision)
        checklist = _checklist_copy(plan)
        changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        found = False
        for item in checklist:
            if item.get("id") != item_id:
                continue
            for key, value in changes.items():
                item[key] = value
            found = True
            break
        if not found:
            raise NotFoundError("Checklist item not found")
        return service.update(
            plan_id,
            PlanUpdate(expected_revision=plan.revision, checklist=checklist),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{plan_id}/checklist/{item_id}", response_model=PlanRead)
def delete_plan_checklist_item(
    plan_id: UUID,
    item_id: str,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    service = PlanService(session)
    try:
        plan = service.get(plan_id)
        _require_revision(plan, expected_revision)
        checklist = [item for item in _checklist_copy(plan) if item.get("id") != item_id]
        if len(checklist) == len(plan.checklist):
            raise NotFoundError("Checklist item not found")
        return service.update(
            plan_id,
            PlanUpdate(expected_revision=plan.revision, checklist=checklist),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{plan_id}/checklist/{item_id}/toggle", response_model=PlanRead)
def toggle_plan_checklist_item(
    plan_id: UUID,
    item_id: str,
    payload: ChecklistToggle,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    service = PlanService(session)
    try:
        plan = service.get(plan_id)
        _require_revision(plan, payload.expected_revision)
        checklist = _checklist_copy(plan)
        found = False
        for item in checklist:
            if item.get("id") != item_id:
                continue
            completed = (
                not bool(item.get("completed"))
                if payload.completed is None
                else payload.completed
            )
            item["completed"] = completed
            item["last_confirmed_at"] = (
                datetime.now().isoformat() if completed else None
            )
            found = True
            break
        if not found:
            raise NotFoundError("Checklist item not found")
        return service.update(
            plan_id,
            PlanUpdate(expected_revision=plan.revision, checklist=checklist),
        )
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{plan_id}", response_model=PlanRead)
def delete_plan(
    plan_id: UUID,
    expected_revision: ExpectedRevision,
    session: SessionDep,
    principal: WritePrincipalDep,
) -> PlanRead:
    del principal
    try:
        return PlanService(session).delete(plan_id, expected_revision)
    except (NotFoundError, ConflictError) as exc:
        raise _translate_error(exc) from exc
