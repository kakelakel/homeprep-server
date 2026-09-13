import json
import sqlite3
import zipfile
from collections.abc import Generator
from pathlib import Path

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
    settings.data_dir = tmp_path
    settings.database_url = f"sqlite:///{tmp_path / 'homeprep-backup-test.db'}"
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
    settings.data_dir = original_data_dir
    reset_database_state()


def test_backup_contains_manifest_and_consistent_database(client: TestClient, tmp_path) -> None:
    household = client.post("/api/v1/households", json={"name": "Backup household"})
    assert household.status_code == 201
    household_id = household.json()["id"]

    inventory = client.post(
        "/api/v1/inventory",
        json={
            "household_id": household_id,
            "name": "Emergency water",
            "category": "water",
            "quantity": 30,
            "unit": "l",
        },
    )
    assert inventory.status_code == 201

    created = client.post("/api/v1/backups")
    assert created.status_code == 201
    backup = created.json()
    assert backup["format_version"] == 1
    assert backup["size_bytes"] > 0

    archive_path = Path(backup["path"])
    assert archive_path.exists()
    assert archive_path.parent == tmp_path / "backups"

    extracted_db = tmp_path / "restored-check.db"
    with zipfile.ZipFile(archive_path, "r") as archive:
        assert set(archive.namelist()) == {"manifest.json", "homeprep.db"}
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["backup_format_version"] == 1
        assert manifest["household"]["id"] == household_id
        assert manifest["household"]["name"] == "Backup household"
        extracted_db.write_bytes(archive.read("homeprep.db"))

    with sqlite3.connect(extracted_db) as connection:
        row = connection.execute(
            "SELECT name, quantity, unit FROM inventory_items WHERE deleted_at IS NULL"
        ).fetchone()
    assert row == ("Emergency water", 30.0, "l")

    listing = client.get("/api/v1/backups")
    assert listing.status_code == 200
    assert listing.json()[0]["filename"] == backup["filename"]
