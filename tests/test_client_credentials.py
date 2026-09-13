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
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-client-auth-test.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())

    with TestClient(app) as test_client:
        yield test_client

    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def _setup_owner_and_household(client: TestClient) -> str:
    setup = client.post(
        "/api/v1/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert setup.status_code == 201
    household = client.post("/api/v1/households", json={"name": "Test household"})
    assert household.status_code == 201
    return household.json()["id"]


def test_full_access_client_can_use_inventory_and_be_revoked(client: TestClient) -> None:
    household_id = _setup_owner_and_household(client)

    created = client.post(
        "/api/v1/clients",
        json={
            "name": "Home Assistant",
            "client_type": "home_assistant",
            "access_role": "full_access",
        },
    )
    assert created.status_code == 201
    body = created.json()
    token = body["token"]
    client_id = body["id"]
    assert token
    assert body["client_type"] == "home_assistant"
    assert body["access_role"] == "full_access"

    client.post("/api/v1/auth/logout")
    headers = {"Authorization": f"Bearer {token}"}

    households = client.get("/api/v1/households", headers=headers)
    assert households.status_code == 200
    assert households.json()[0]["id"] == household_id

    inventory = client.post(
        "/api/v1/inventory",
        headers=headers,
        json={
            "household_id": household_id,
            "name": "Water",
            "category": "water",
            "quantity": 10,
            "unit": "l",
        },
    )
    assert inventory.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    revoked = client.post(f"/api/v1/clients/{client_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None

    client.post("/api/v1/auth/logout")
    denied = client.get("/api/v1/households", headers=headers)
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "authentication_required"


def test_read_only_client_cannot_write(client: TestClient) -> None:
    household_id = _setup_owner_and_household(client)

    created = client.post(
        "/api/v1/clients",
        json={
            "name": "Read-only phone",
            "client_type": "android",
            "access_role": "read_only",
        },
    )
    assert created.status_code == 201
    token = created.json()["token"]

    client.post("/api/v1/auth/logout")
    headers = {"Authorization": f"Bearer {token}"}

    listing = client.get(f"/api/v1/inventory?household_id={household_id}", headers=headers)
    assert listing.status_code == 200

    denied = client.post(
        "/api/v1/inventory",
        headers=headers,
        json={
            "household_id": household_id,
            "name": "Should fail",
            "quantity": 1,
            "unit": "pcs",
        },
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "write_access_required"
