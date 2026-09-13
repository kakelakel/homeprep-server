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


def test_inventory_crud_and_revision_conflict(client: TestClient) -> None:
    household_response = client.post(
        "/api/v1/households",
        json={"name": "Test household"},
    )
    assert household_response.status_code == 201
    household_id = household_response.json()["id"]

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
