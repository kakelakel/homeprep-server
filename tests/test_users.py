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
    original_data_dir = settings.data_dir
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-users-test.db'}"
    settings.data_dir = tmp_path
    reset_database_state()
    Base.metadata.create_all(get_engine())

    with TestClient(app) as test_client:
        yield test_client

    reset_database_state()
    settings.database_url = original_database_url
    settings.data_dir = original_data_dir
    reset_database_state()


def _login(client: TestClient, username: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def test_owner_editor_viewer_rbac(client: TestClient) -> None:
    owner_password = "correct horse battery staple"
    editor_password = "editor secure password"
    viewer_password = "viewer secure password"

    setup = client.post(
        "/api/v1/auth/setup",
        json={"username": "owner", "password": owner_password},
    )
    assert setup.status_code == 201
    owner_id = setup.json()["id"]

    household = client.post("/api/v1/households", json={"name": "RBAC household"})
    assert household.status_code == 201
    household_id = household.json()["id"]

    editor = client.post(
        "/api/v1/users",
        json={"username": "editor", "password": editor_password, "role": "editor"},
    )
    assert editor.status_code == 201
    viewer = client.post(
        "/api/v1/users",
        json={"username": "viewer", "password": viewer_password, "role": "viewer"},
    )
    assert viewer.status_code == 201
    viewer_id = viewer.json()["id"]

    users = client.get("/api/v1/users")
    assert users.status_code == 200
    assert {user["role"] for user in users.json()} == {"owner", "editor", "viewer"}

    last_owner_demote = client.patch(f"/api/v1/users/{owner_id}", json={"role": "editor"})
    assert last_owner_demote.status_code == 409
    assert last_owner_demote.json()["error"]["code"] == "last_owner_required"

    assert client.post("/api/v1/auth/logout").status_code == 204
    _login(client, "editor", editor_password)

    editor_item = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Editor item",
            "quantity": 2,
            "unit": "pcs",
        },
    )
    assert editor_item.status_code == 201
    assert client.get("/api/v1/inventory", params={"household_id": household_id}).status_code == 200
    assert client.get("/api/v1/users").status_code == 403
    assert client.get("/api/v1/backups").status_code == 403
    assert client.get("/api/v1/clients").status_code == 403
    assert client.post(
        "/api/v1/pairing",
        json={"name": "Forbidden pairing", "client_type": "home_assistant"},
    ).status_code == 403

    assert client.post("/api/v1/auth/logout").status_code == 204
    _login(client, "viewer", viewer_password)

    inventory = client.get("/api/v1/inventory", params={"household_id": household_id})
    assert inventory.status_code == 200
    viewer_write = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Viewer item",
            "quantity": 1,
            "unit": "pcs",
        },
    )
    assert viewer_write.status_code == 403
    assert viewer_write.json()["error"]["code"] == "write_access_required"

    assert client.post("/api/v1/auth/logout").status_code == 204
    _login(client, "owner", owner_password)
    disable = client.patch(f"/api/v1/users/{viewer_id}", json={"disabled": True})
    assert disable.status_code == 200
    assert disable.json()["disabled_at"] is not None

    assert client.post("/api/v1/auth/logout").status_code == 204
    denied = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": viewer_password},
    )
    assert denied.status_code == 401
