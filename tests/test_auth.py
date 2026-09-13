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
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-auth-test.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())

    with TestClient(app) as test_client:
        yield test_client

    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def test_first_run_setup_login_logout_and_protection(client: TestClient) -> None:
    status_response = client.get("/api/v1/auth/status")
    assert status_response.status_code == 200
    assert status_response.json()["setup_required"] is True
    assert status_response.json()["authenticated"] is False

    protected_response = client.get("/api/v1/households")
    assert protected_response.status_code == 401

    setup_response = client.post(
        "/api/v1/auth/setup",
        json={"username": "Owner", "password": "correct horse battery staple"},
    )
    assert setup_response.status_code == 201
    assert setup_response.json()["username"] == "owner"
    assert setup_response.json()["role"] == "owner"

    status_after_setup = client.get("/api/v1/auth/status")
    assert status_after_setup.status_code == 200
    assert status_after_setup.json()["setup_required"] is False
    assert status_after_setup.json()["authenticated"] is True

    second_setup = client.post(
        "/api/v1/auth/setup",
        json={"username": "other", "password": "another secure password"},
    )
    assert second_setup.status_code == 409

    household_response = client.post(
        "/api/v1/households",
        json={"name": "Protected household"},
    )
    assert household_response.status_code == 201

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204
    assert client.get("/api/v1/households").status_code == 401

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": "wrong password"},
    )
    assert invalid_login.status_code == 401

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "OWNER", "password": "correct horse battery staple"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["username"] == "owner"

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "owner"

    assert client.get("/api/v1/households").status_code == 200
