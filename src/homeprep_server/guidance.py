from __future__ import annotations

import json
from copy import deepcopy
from importlib.resources import files
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from homeprep_server.planning_services import HouseholdProfileService, TargetService
from homeprep_server.schemas import TargetCreate, TargetOrigin, TargetRequirement, TargetType
from homeprep_server.services import ConflictError, NotFoundError


class RecommendationCatalog:
    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}
        package_root = files("homeprep_server.recommendations")
        for resource in package_root.iterdir():
            if not resource.name.endswith(".json"):
                continue
            with resource.open("r", encoding="utf-8") as handle:
                profile = json.load(handle)
            self._profiles[str(profile["id"])] = profile

    @property
    def profiles(self) -> list[dict[str, Any]]:
        return list(self._profiles.values())

    def get(self, profile_id: str) -> dict[str, Any] | None:
        return self._profiles.get(profile_id)

    def metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "id": profile["id"],
                "country_code": profile["country_code"],
                "authority": profile["authority"],
                "authority_url": profile["authority_url"],
                "title": profile["title"],
                "version": profile["version"],
                "reviewed_at": profile["reviewed_at"],
                "default_duration_days": profile.get("default_duration_days"),
                "unofficial": bool(profile.get("unofficial", False)),
                "disclaimer": profile.get("disclaimer"),
            }
            for profile in self.profiles
        ]

    def for_country(self, country_code: str | None) -> dict[str, Any]:
        wanted = (country_code or "OTHER").upper()
        for profile in self.profiles:
            if str(profile.get("country_code", "")).upper() == wanted:
                return profile
        fallback = next(
            (
                profile
                for profile in self.profiles
                if str(profile.get("country_code", "")).upper() == "OTHER"
            ),
            None,
        )
        if fallback is None:
            raise NotFoundError("No guidance profile is available")
        return fallback


def calculate_recommendation(
    recommendation: dict[str, Any],
    household: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    result = deepcopy(recommendation)
    rule = recommendation.get("rule") or {}
    kind = rule.get("kind")
    days = int(
        household.get("preparedness_days")
        or profile.get("default_duration_days")
        or 7
    )
    adults = int(household.get("adults") or 0)
    children = int(household.get("children") or 0)
    pets = int(household.get("pets") or 0)
    people = adults + children
    notes: list[str] = []
    result["calculated"] = {
        "preparedness_days": days,
        "people": people,
        "adults": adults,
        "children": children,
        "pets": pets,
        "calculation_notes": notes,
    }

    if kind == "quantity_per_person_per_day":
        minimum_rate = float(rule["minimum"])
        target_rate = float(rule.get("target", minimum_rate))
        result["calculated"].update(
            {
                "minimum_value": minimum_rate * people * days,
                "target_value": target_rate * people * days,
                "unit": rule["unit"],
                "rate_basis": "person_per_day",
                "minimum_rate": minimum_rate,
                "target_rate": target_rate,
            }
        )
        notes.append(f"Calculated for {people} people over {days} days.")
    elif kind == "quantity_per_adult_per_day":
        minimum_rate = float(rule["minimum"])
        target_rate = float(rule.get("maximum", rule.get("target", minimum_rate)))
        result["calculated"].update(
            {
                "minimum_value": minimum_rate * adults * days,
                "target_value": target_rate * adults * days,
                "unit": rule["unit"],
                "rate_basis": "adult_per_day",
            }
        )
        notes.append(f"Quantified source rate applies to {adults} adults over {days} days.")
        if children:
            notes.append(
                f"{children} children are present but are not included in this numeric rule."
            )
    elif kind == "quantity_per_person_total":
        per_person = float(rule["value"])
        result["calculated"].update(
            {
                "minimum_value": per_person * people,
                "target_value": per_person * people,
                "unit": rule["unit"],
                "rate_basis": "person_total",
            }
        )
        notes.append(f"Calculated for {people} people.")
    elif kind == "coverage_days":
        value = int(rule.get("days") or days)
        result["calculated"].update(
            {
                "minimum_value": value,
                "target_value": value,
                "unit": "day",
                "rate_basis": "coverage_days",
            }
        )
    elif kind in {"presence", "capability", "checklist"}:
        requirements = list(recommendation.get("requirements") or [])
        result["calculated"].update(
            {
                "requirements": requirements,
                "requirement_count": len(
                    [item for item in requirements if item.get("required", True)]
                ),
                "rate_basis": "readiness_requirements",
            }
        )
    else:
        result["calculated"]["advisory_only"] = True
        notes.append("This recommendation is advisory only and has no numeric conversion.")

    if pets and recommendation.get("pet_adjustment_note"):
        notes.append(recommendation["pet_adjustment_note"])
    if recommendation.get("household_adjustment_note"):
        notes.append(recommendation["household_adjustment_note"])
    result["applicable"] = not (
        recommendation.get("id") == "pet_supplies" and pets == 0
    )
    return result


class GuidanceService:
    def __init__(self, session: Session):
        self.session = session
        self.catalog = RecommendationCatalog()
        self.profiles = HouseholdProfileService(session)
        self.targets = TargetService(session)

    def list_profiles(self) -> list[dict[str, Any]]:
        return self.catalog.metadata()

    def resolved(
        self,
        household_id: UUID,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        household_profile = self.profiles.get(household_id)
        household = {
            "country_code": household_profile.country_code,
            "adults": household_profile.adults,
            "children": household_profile.children,
            "pets": household_profile.pets,
            "preparedness_days": household_profile.preparedness_days,
        }
        profile = (
            self.catalog.get(profile_id)
            if profile_id is not None
            else self.catalog.for_country(household_profile.country_code)
        )
        if profile is None:
            raise NotFoundError("Guidance profile not found")
        return {
            "profile": profile,
            "household": household,
            "recommendations": [
                calculate_recommendation(recommendation, household, profile)
                for recommendation in profile.get("recommendations", [])
            ],
        }

    def adopt(
        self,
        household_id: UUID,
        recommendation_id: str,
        profile_id: str | None = None,
    ):
        resolved = self.resolved(household_id, profile_id)
        profile = resolved["profile"]
        recommendation = next(
            (
                item
                for item in resolved["recommendations"]
                if item.get("id") == recommendation_id
            ),
            None,
        )
        if recommendation is None:
            raise NotFoundError("Recommendation not found")
        for existing in self.targets.list_for_household(household_id):
            if (
                existing.origin == "recommendation"
                and existing.source_profile_id == profile["id"]
                and existing.source_recommendation_id == recommendation_id
            ):
                raise ConflictError("This recommendation is already adopted")

        calculated = recommendation.get("calculated") or {}
        notes: list[str] = []
        if recommendation.get("advisory_note"):
            notes.append(recommendation["advisory_note"])
        notes.extend(calculated.get("calculation_notes") or [])
        requirements = [
            TargetRequirement(**item)
            for item in (
                calculated.get("requirements")
                or recommendation.get("requirements")
                or []
            )
        ]
        target = TargetCreate(
            household_id=household_id,
            name=recommendation["title"],
            category=recommendation.get("category"),
            target_type=TargetType(recommendation["target_type"]),
            matcher=recommendation.get("matcher") or {},
            unit=calculated.get("unit"),
            minimum_value=calculated.get("minimum_value"),
            target_value=calculated.get("target_value"),
            requirements=requirements,
            priority=recommendation.get("priority", "normal"),
            notes="\n".join(notes) if notes else None,
            origin=TargetOrigin.RECOMMENDATION,
            source_profile_id=profile["id"],
            source_recommendation_id=recommendation_id,
            source_profile_version=profile["version"],
        )
        return self.targets.create(target)
