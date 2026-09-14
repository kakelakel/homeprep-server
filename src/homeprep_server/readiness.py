from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from homeprep_server.repositories import (
    HouseholdRepository,
    InventoryRepository,
    TargetRepository,
    TaskRepository,
)
from homeprep_server.services import NotFoundError

UNIT_DIMENSIONS: dict[str, tuple[str, float]] = {
    "milliliter": ("volume", 0.001),
    "centiliter": ("volume", 0.01),
    "deciliter": ("volume", 0.1),
    "liter": ("volume", 1.0),
    "l": ("volume", 1.0),
    "cubic_meter": ("volume", 1000.0),
    "fluid_ounce_us": ("volume", 0.0295735295625),
    "cup_us": ("volume", 0.2365882365),
    "pint_us": ("volume", 0.473176473),
    "quart_us": ("volume", 0.946352946),
    "gallon_us": ("volume", 3.785411784),
    "fluid_ounce_imperial": ("volume", 0.0284130625),
    "pint_imperial": ("volume", 0.56826125),
    "quart_imperial": ("volume", 1.1365225),
    "gallon_imperial": ("volume", 4.54609),
    "milligram": ("mass", 0.000001),
    "gram": ("mass", 0.001),
    "kilogram": ("mass", 1.0),
    "kg": ("mass", 1.0),
    "ounce": ("mass", 0.028349523125),
    "pound": ("mass", 0.45359237),
    "stone": ("mass", 6.35029318),
    "watt_hour": ("energy", 1.0),
    "kilowatt_hour": ("energy", 1000.0),
    "piece": ("count", 1.0),
    "pcs": ("count", 1.0),
    "pair": ("count", 2.0),
    "dozen": ("count", 12.0),
}


def convert_value(value: float | int, from_unit: str, to_unit: str) -> float | None:
    if from_unit == to_unit:
        return float(value)
    source = UNIT_DIMENSIONS.get(from_unit)
    target = UNIT_DIMENSIONS.get(to_unit)
    if not source or not target or source[0] != target[0]:
        return None
    return float(value) * source[1] / target[1]


def item_matches(item: dict[str, Any], matcher: dict[str, Any]) -> bool:
    if "item_id" in matcher and item.get("id") != matcher["item_id"]:
        return False
    if "category" in matcher and item.get("category") != matcher["category"]:
        return False
    if "item_type" in matcher and item.get("item_type") != matcher["item_type"]:
        return False
    name_contains = matcher.get("name_contains")
    if name_contains and str(name_contains).lower() not in str(item.get("name", "")).lower():
        return False
    return True


def _result(
    target: dict[str, Any],
    *,
    current_value: Any,
    minimum_value: Any,
    target_value: Any,
    status: str,
    matching_count: int,
    incompatible_count: int,
    requirements: list[dict[str, Any]] | None = None,
    progress_label: str | None = None,
) -> dict[str, Any]:
    return {
        "target_id": target["id"],
        "name": target["name"],
        "target_type": target.get("target_type"),
        "status": status,
        "current_value": current_value,
        "minimum_value": minimum_value,
        "target_value": target_value,
        "unit": target.get("unit"),
        "matching_count": matching_count,
        "incompatible_count": incompatible_count,
        "requirements": requirements or [],
        "progress_label": progress_label,
    }


def _numeric_result(
    target: dict[str, Any],
    current: float,
    matching_count: int,
    incompatible_count: int,
) -> dict[str, Any]:
    minimum = target.get("minimum_value")
    desired = target.get("target_value")
    if minimum is not None and current < float(minimum):
        status = "below_minimum"
    elif desired is not None and current < float(desired):
        status = "below_target"
    else:
        status = "met"
    display = int(current) if current.is_integer() else current
    unit = target.get("unit") or ""
    return _result(
        target,
        current_value=current,
        minimum_value=minimum,
        target_value=desired,
        status=status,
        matching_count=matching_count,
        incompatible_count=incompatible_count,
        progress_label=f"{display} {unit}".strip(),
    )


def evaluate_target(target: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    target_type = target["target_type"]
    requirements = list(target.get("requirements") or [])
    if target_type in {"presence", "capability", "checklist"} and requirements:
        confirmed = set(target.get("completed_requirement_ids") or [])
        evaluated: list[dict[str, Any]] = []
        completed_required = 0
        required_count = 0
        for requirement in requirements:
            matcher = dict(requirement.get("matcher") or {})
            matched_items = [item for item in inventory if matcher and item_matches(item, matcher)]
            complete = requirement["id"] in confirmed or bool(matched_items)
            required = bool(requirement.get("required", True))
            if required:
                required_count += 1
                if complete:
                    completed_required += 1
            evaluated.append(
                {
                    **requirement,
                    "complete": complete,
                    "completion_source": (
                        "inventory" if matched_items else "manual" if complete else None
                    ),
                    "matching_count": len(matched_items),
                }
            )
        if required_count == 0 or completed_required == required_count:
            status = "met"
        elif completed_required > 0:
            status = "below_target"
        else:
            status = "below_minimum"
        return _result(
            target,
            current_value=completed_required,
            minimum_value=required_count,
            target_value=required_count,
            status=status,
            matching_count=sum(item["matching_count"] for item in evaluated),
            incompatible_count=0,
            requirements=evaluated,
            progress_label=(
                "Ready" if status == "met" else f"{completed_required} of {required_count} ready"
            ),
        )

    matching = [item for item in inventory if item_matches(item, target.get("matcher") or {})]
    if target_type in {"presence", "capability"}:
        current = bool(matching)
        return _result(
            target,
            current_value=1 if current else 0,
            minimum_value=1,
            target_value=1,
            status="met" if current else "below_minimum",
            matching_count=len(matching),
            incompatible_count=0,
            progress_label="Ready" if current else "Not ready",
        )
    if target_type == "count":
        current = sum(float(item.get("quantity") or 0) for item in matching)
        return _numeric_result(target, current, len(matching), 0)
    if target_type == "coverage":
        current = target.get("current_value")
        if current is None:
            return _result(
                target,
                current_value=None,
                minimum_value=target.get("minimum_value"),
                target_value=target.get("target_value"),
                status="unknown",
                matching_count=len(matching),
                incompatible_count=0,
                progress_label="Not assessed",
            )
        result = _numeric_result(target, float(current), len(matching), 0)
        result["progress_label"] = f"{current:g} {target.get('unit') or ''}".strip()
        return result

    target_unit = target.get("unit")
    if not target_unit:
        return _result(
            target,
            current_value=None,
            minimum_value=target.get("minimum_value"),
            target_value=target.get("target_value"),
            status="unknown",
            matching_count=len(matching),
            incompatible_count=len(matching),
            progress_label="Not measurable",
        )
    current = 0.0
    incompatible = 0
    for item in matching:
        converted = convert_value(
            float(item.get("quantity") or 0),
            str(item.get("unit") or ""),
            target_unit,
        )
        if converted is None:
            incompatible += 1
        else:
            current += converted
    return _numeric_result(target, current, len(matching), incompatible)


def task_status(task, today: date | None = None) -> str:
    if not task.enabled:
        return "disabled"
    if task.next_due_at is None:
        return "unscheduled"
    today = today or date.today()
    if task.next_due_at < today:
        return "overdue"
    if task.next_due_at == today:
        return "due"
    if task.reminder_before_days and today >= task.next_due_at - timedelta(
        days=task.reminder_before_days
    ):
        return "upcoming"
    return "ok"


class ReadinessService:
    def __init__(self, session: Session):
        self.households = HouseholdRepository(session)
        self.inventory = InventoryRepository(session)
        self.targets = TargetRepository(session)
        self.tasks = TaskRepository(session)

    def summary(self, household_id: UUID) -> dict[str, Any]:
        household_key = str(household_id)
        if self.households.get(household_key) is None:
            raise NotFoundError("Household not found")
        inventory_models = self.inventory.list_for_household(household_key)
        inventory = [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "item_type": item.item_type,
                "quantity": item.quantity,
                "unit": item.unit,
            }
            for item in inventory_models
        ]
        target_models = [
            target
            for target in self.targets.list_for_household(household_key)
            if target.enabled
        ]
        evaluations = [
            evaluate_target(
                {
                    "id": target.id,
                    "name": target.name,
                    "target_type": target.target_type,
                    "matcher": target.matcher,
                    "unit": target.unit,
                    "minimum_value": target.minimum_value,
                    "target_value": target.target_value,
                    "current_value": target.current_value,
                    "requirements": target.requirements,
                    "completed_requirement_ids": target.completed_requirement_ids,
                },
                inventory,
            )
            for target in target_models
        ]
        target_counts = {"met": 0, "below_target": 0, "below_minimum": 0, "unknown": 0}
        for evaluation in evaluations:
            target_counts[evaluation["status"]] = target_counts.get(evaluation["status"], 0) + 1
        if target_counts["below_minimum"]:
            target_status = "critical"
        elif target_counts["below_target"] or target_counts["unknown"]:
            target_status = "attention"
        else:
            target_status = "ok"

        task_counts = {
            "overdue": 0,
            "due": 0,
            "upcoming": 0,
            "ok": 0,
            "unscheduled": 0,
            "disabled": 0,
        }
        task_rows = []
        for task in self.tasks.list_for_household(household_key):
            status = task_status(task)
            task_counts[status] += 1
            task_rows.append(
                {
                    "id": task.id,
                    "name": task.name,
                    "status": status,
                    "next_due_at": task.next_due_at,
                    "task_kind": task.task_kind,
                }
            )
        if task_counts["overdue"]:
            task_overall = "critical"
        elif task_counts["due"] or task_counts["upcoming"] or task_counts["unscheduled"]:
            task_overall = "attention"
        else:
            task_overall = "ok"

        total_targets = len(evaluations)
        score = round(100 * target_counts["met"] / total_targets) if total_targets else None
        overall = "critical" if "critical" in {target_status, task_overall} else (
            "attention" if "attention" in {target_status, task_overall} else "ok"
        )
        return {
            "status": overall,
            "score": score,
            "inventory_items": len(inventory_models),
            "targets": {"status": target_status, "total": total_targets, **target_counts},
            "target_evaluations": evaluations,
            "tasks": {"status": task_overall, "total": len(task_rows), **task_counts},
            "task_rows": task_rows,
        }
