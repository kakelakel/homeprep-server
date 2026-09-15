from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from homeprep_server.core.config import settings
from homeprep_server.database import get_engine, reset_database_state
from homeprep_server.main import app
from homeprep_server.models import Base


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    original_database_url = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-plan-checklist.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())
    with TestClient(app) as test_client:
        setup = test_client.post(
            "/api/v1/auth/setup",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert setup.status_code == 201
        yield test_client
    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def _household(client: TestClient) -> str:
    response = client.post("/api/v1/households", json={"name": "Checklist home"})
    assert response.status_code == 201
    return response.json()["id"]


def test_plan_checklist_crud_preserves_links_and_revision(client: TestClient) -> None:
    household_id = _household(client)
    inventory = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Go bag radio",
            "category": "communication",
            "quantity": 1,
            "unit": "piece",
        },
    )
    assert inventory.status_code == 201
    container = client.post(
        "/api/v1/containers",
        json={
            "household_id": household_id,
            "name": "Go bag",
            "container_type": "bag",
        },
    )
    assert container.status_code == 201
    asset = client.post(
        "/api/v1/assets",
        json={
            "household_id": household_id,
            "name": "Main shutoff",
            "asset_type": "water_shutoff",
        },
    )
    assert asset.status_code == 201

    plan = client.post(
        "/api/v1/plans",
        json={
            "household_id": household_id,
            "name": "Evacuation",
            "plan_type": "evacuation",
        },
    )
    assert plan.status_code == 201
    plan_body = plan.json()

    added = client.post(
        f"/api/v1/plans/{plan_body['id']}/checklist",
        json={
            "expected_revision": plan_body["revision"],
            "label": "Bring the critical kit",
            "description": "Verify radio, bag and shutoff before leaving.",
            "linked_inventory_item_ids": [inventory.json()["id"]],
            "linked_container_ids": [container.json()["id"]],
            "linked_asset_ids": [asset.json()["id"]],
        },
    )
    assert added.status_code == 200
    added_body = added.json()
    assert added_body["revision"] == plan_body["revision"] + 1
    assert len(added_body["checklist"]) == 1
    check = added_body["checklist"][0]
    assert check["label"] == "Bring the critical kit"
    assert check["linked_inventory_item_ids"] == [inventory.json()["id"]]
    assert check["linked_container_ids"] == [container.json()["id"]]
    assert check["linked_asset_ids"] == [asset.json()["id"]]

    edited = client.patch(
        f"/api/v1/plans/{plan_body['id']}/checklist/{check['id']}",
        json={
            "expected_revision": added_body["revision"],
            "label": "Bring the checked critical kit",
            "description": "Updated instructions.",
        },
    )
    assert edited.status_code == 200
    edited_body = edited.json()
    edited_check = edited_body["checklist"][0]
    assert edited_check["label"] == "Bring the checked critical kit"
    assert edited_check["description"] == "Updated instructions."
    assert edited_check["linked_inventory_item_ids"] == [inventory.json()["id"]]

    toggled = client.post(
        f"/api/v1/plans/{plan_body['id']}/checklist/{check['id']}/toggle",
        json={"expected_revision": edited_body["revision"], "completed": True},
    )
    assert toggled.status_code == 200
    toggled_body = toggled.json()
    assert toggled_body["checklist"][0]["completed"] is True
    assert toggled_body["checklist"][0]["last_confirmed_at"] is not None

    stale_delete = client.delete(
        f"/api/v1/plans/{plan_body['id']}/checklist/{check['id']}",
        params={"expected_revision": edited_body["revision"]},
    )
    assert stale_delete.status_code == 409

    deleted = client.delete(
        f"/api/v1/plans/{plan_body['id']}/checklist/{check['id']}",
        params={"expected_revision": toggled_body["revision"]},
    )
    assert deleted.status_code == 200
    assert deleted.json()["checklist"] == []


def test_plan_checklist_rejects_cross_household_links(client: TestClient) -> None:
    household_a = _household(client)
    household_b_response = client.post(
        "/api/v1/households", json={"name": "Other home"}
    )
    assert household_b_response.status_code == 201
    household_b = household_b_response.json()["id"]

    foreign_item = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_b,
            "name": "Foreign item",
            "category": "other",
            "quantity": 1,
            "unit": "piece",
        },
    )
    assert foreign_item.status_code == 201

    plan = client.post(
        "/api/v1/plans",
        json={"household_id": household_a, "name": "Home A plan"},
    )
    assert plan.status_code == 201

    response = client.post(
        f"/api/v1/plans/{plan.json()['id']}/checklist",
        json={
            "expected_revision": plan.json()["revision"],
            "label": "Invalid linked item",
            "linked_inventory_item_ids": [foreign_item.json()["id"]],
        },
    )
    assert response.status_code == 404
