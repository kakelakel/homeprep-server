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
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-test.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())

    with TestClient(app) as test_client:
        setup_response = test_client.post(
            "/api/v1/auth/setup",
            json={"username": "test-owner", "password": "correct horse battery staple"},
        )
        assert setup_response.status_code == 201
        yield test_client

    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def _create_household(client: TestClient) -> str:
    household_response = client.post(
        "/api/v1/households",
        json={"name": "Test household"},
    )
    assert household_response.status_code == 201
    return household_response.json()["id"]


def test_inventory_crud_and_revision_conflict(client: TestClient) -> None:
    household_id = _create_household(client)

    create_response = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Drinking water",
            "category": "water",
            "item_type": "consumable",
            "quantity": 20,
            "unit": "l",
        },
    )
    assert create_response.status_code == 201
    item = create_response.json()
    item_id = item["id"]
    assert item["revision"] == 1
    assert item["quantity"] == 20
    assert item["schema_version"] == 4

    list_response = client.get(
        "/api/v1/inventory",
        params={"household_id": household_id},
    )
    assert list_response.status_code == 200
    assert [row["id"] for row in list_response.json()] == [item_id]

    update_response = client.patch(
        f"/api/v1/inventory/{item_id}",
        json={"quantity": 24, "expected_revision": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity"] == 24
    assert update_response.json()["revision"] == 2

    stale_update = client.patch(
        f"/api/v1/inventory/{item_id}",
        json={"quantity": 30, "expected_revision": 1},
    )
    assert stale_update.status_code == 409

    delete_response = client.delete(
        f"/api/v1/inventory/{item_id}",
        params={"expected_revision": 2},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["revision"] == 3
    assert delete_response.json()["deleted_at"] is not None

    missing_response = client.get(f"/api/v1/inventory/{item_id}")
    assert missing_response.status_code == 404

    empty_list = client.get(
        "/api/v1/inventory",
        params={"household_id": household_id},
    )
    assert empty_list.status_code == 200
    assert empty_list.json() == []


def test_inventory_preserves_home_assistant_schema_v4_fields(client: TestClient) -> None:
    """HA inventory metadata must survive a Server API/database round trip."""
    household_id = _create_household(client)

    container_response = client.post(
        "/api/v1/containers",
        json={
            "household_id": household_id,
            "name": "Bathroom preparedness box",
            "container_type": "box_crate",
            "location": "Bathroom cabinet",
        },
    )
    assert container_response.status_code == 201
    container_id = container_response.json()["id"]

    ha_payload = {
        "household_id": household_id,
        "name": "Toothbrush",
        "category": "hygiene",
        "item_type": "equipment",
        "quantity": 4,
        "unit": "piece",
        "container_id": container_id,
        "expires_at": "2028-09-01",
        "last_checked": "2026-09-14",
        "next_check_at": "2027-03-14",
        "notes": "Family reserve toothbrushes",
        "image_id": "img-toothbrush-01",
        "image_token": "opaque-local-media-token",
        "image_content_type": "image/jpeg",
        "image_filename": "toothbrush.jpg",
    }

    created = client.post("/api/v1/inventory", json=ha_payload)
    assert created.status_code == 201
    created_item = created.json()
    assert created_item["schema_version"] == 4

    fetched = client.get(f"/api/v1/inventory/{created_item['id']}")
    assert fetched.status_code == 200
    item = fetched.json()

    for field, expected in ha_payload.items():
        assert item[field] == expected

    updated = client.patch(
        f"/api/v1/inventory/{created_item['id']}",
        json={
            "image_filename": "toothbrush-new.jpg",
            "notes": "Rotated reserve toothbrushes",
            "expected_revision": created_item["revision"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["image_filename"] == "toothbrush-new.jpg"
    assert updated.json()["notes"] == "Rotated reserve toothbrushes"
    assert updated.json()["schema_version"] == 4
