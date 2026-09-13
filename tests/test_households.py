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


def test_server_allows_only_one_active_household(client: TestClient) -> None:
    first = client.post(
        "/api/v1/households",
        json={"name": "Primary household"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/households",
        json={"name": "Second household"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "This HomePrep Server already has a household"

    households = client.get("/api/v1/households")
    assert households.status_code == 200
    assert [household["name"] for household in households.json()] == ["Primary household"]
