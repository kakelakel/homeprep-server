from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from homeprep_server.core.config import settings
from homeprep_server.database import get_engine, reset_database_state
from homeprep_server.main import app
from homeprep_server.models import Base


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    original_database_url = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-domains.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/setup",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert response.status_code == 201
        yield test_client
    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def create_household(client: TestClient) -> str:
    response = client.post("/api/v1/households", json={"name": "Prepared household"})
    assert response.status_code == 201
    return response.json()["id"]


def test_profile_guidance_targets_and_readiness(client: TestClient) -> None:
    household_id = create_household(client)
    profile = client.put(
        f"/api/v1/household-profile/{household_id}",
        json={
            "country_code": "SE",
            "adults": 2,
            "children": 1,
            "pets": 1,
            "preparedness_days": 7,
        },
    )
    assert profile.status_code == 200
    assert profile.json()["id"] == household_id
    assert profile.json()["household_id"] == household_id
    assert profile.json()["country_code"] == "SE"
    assert profile.json()["schema_version"] == 2

    guidance = client.get(f"/api/v1/guidance/{household_id}")
    assert guidance.status_code == 200
    assert guidance.json()["profile"]["id"] == "se-msb-2026-v1"
    water = next(row for row in guidance.json()["recommendations"] if row["id"] == "water")
    assert water["calculated"]["target_value"] == 63

    adopted = client.post(
        "/api/v1/guidance/adopt",
        json={"household_id": household_id, "recommendation_id": "water"},
    )
    assert adopted.status_code == 200
    assert adopted.json()["origin"] == "recommendation"

    inventory = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Stored water",
            "category": "water",
            "quantity": 70,
            "unit": "liter",
        },
    )
    assert inventory.status_code == 201

    readiness = client.get(f"/api/v1/readiness/{household_id}")
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["targets"]["met"] == 1
    assert body["score"] == 100


def test_container_asset_task_plan_flow(client: TestClient) -> None:
    household_id = create_household(client)
    container = client.post(
        "/api/v1/containers",
        json={
            "household_id": household_id,
            "name": "Go bag",
            "container_type": "bag",
            "location": "Hall",
        },
    )
    assert container.status_code == 201
    container_id = container.json()["id"]

    item = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Torch",
            "category": "lighting",
            "quantity": 1,
            "unit": "pcs",
            "container_id": container_id,
        },
    )
    assert item.status_code == 201
    assert item.json()["container_id"] == container_id

    asset = client.post(
        "/api/v1/assets",
        json={
            "household_id": household_id,
            "name": "Main water shutoff",
            "asset_type": "water_shutoff",
            "location": "Basement",
        },
    )
    assert asset.status_code == 201
    asset_id = asset.json()["id"]

    task = client.post(
        "/api/v1/tasks",
        json={
            "household_id": household_id,
            "name": "Check shutoff",
            "task_kind": "asset_inspection",
            "linked_asset_id": asset_id,
            "recurrence_type": "months",
            "recurrence_interval": 6,
            "next_due_at": date.today().isoformat(),
            "reminder_before_days": 7,
        },
    )
    assert task.status_code == 201
    task_body = task.json()

    completed = client.post(
        f"/api/v1/tasks/{task_body['id']}/complete",
        json={"expected_revision": task_body["revision"]},
    )
    assert completed.status_code == 200
    assert completed.json()["completion_count"] == 1
    assert completed.json()["next_due_at"] != date.today().isoformat()

    refreshed_asset = client.get(f"/api/v1/assets/{asset_id}")
    assert refreshed_asset.status_code == 200
    assert refreshed_asset.json()["last_checked_at"] is not None

    plan = client.post(
        "/api/v1/plans",
        json={
            "household_id": household_id,
            "name": "Evacuation plan",
            "plan_type": "evacuation",
            "meeting_point": "Mailbox",
            "checklist": [
                {
                    "label": "Take go bag",
                    "linked_container_ids": [container_id],
                }
            ],
        },
    )
    assert plan.status_code == 201
    assert plan.json()["checklist"][0]["label"] == "Take go bag"

    deleted_container = client.delete(
        f"/api/v1/containers/{container_id}",
        params={"expected_revision": container.json()["revision"]},
    )
    assert deleted_container.status_code == 200
    refreshed_item = client.get(f"/api/v1/inventory/{item.json()['id']}")
    assert refreshed_item.status_code == 200
    assert refreshed_item.json()["container_id"] is None
