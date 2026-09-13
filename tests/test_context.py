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
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-context-test.db'}"
    reset_database_state()
    Base.metadata.create_all(get_engine())

    with TestClient(app) as test_client:
        yield test_client

    reset_database_state()
    settings.database_url = original_database_url
    reset_database_state()


def test_paired_client_can_read_context(client: TestClient) -> None:
    setup = client.post(
        "/api/v1/auth/setup",
        json={"username": "owner", "password": "correct horse battery staple"},
    )
    assert setup.status_code == 201

    household = client.post("/api/v1/households", json={"name": "Context household"})
    assert household.status_code == 201

    pairing = client.post(
        "/api/v1/pairing",
        json={
            "name": "Home Assistant",
            "client_type": "home_assistant",
            "access_role": "full_access",
        },
    )
    assert pairing.status_code == 201

    client.post("/api/v1/auth/logout")
    exchange = client.post(
        "/api/v1/pairing/exchange",
        json={"pairing_token": pairing.json()["pairing_token"]},
    )
    assert exchange.status_code == 201
    token = exchange.json()["token"]

    context = client.get(
        "/api/v1/context",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert context.status_code == 200
    body = context.json()
    assert body["api_version"] == "v1"
    assert body["server_id"]
    assert body["server_version"]
    assert body["principal"]["kind"] == "client"
    assert body["principal"]["name"] == "Home Assistant"
    assert body["principal"]["role"] == "full_access"
    assert body["household"]["id"] == household.json()["id"]
    assert body["household"]["name"] == "Context household"


def test_context_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/context")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
