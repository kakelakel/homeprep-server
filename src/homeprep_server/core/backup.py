from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from homeprep_server import __version__
from homeprep_server.core.config import settings
from homeprep_server.core.identity import get_server_id
from homeprep_server.database import get_engine

BACKUP_FORMAT_VERSION = 1


@dataclass(frozen=True)
class BackupResult:
    filename: str
    path: str
    created_at: str
    size_bytes: int
    format_version: int


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _migration_version() -> str | None:
    with get_engine().connect() as connection:
        try:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        except Exception:
            return None


def _household_metadata() -> dict[str, str] | None:
    with get_engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, name FROM households "
                "WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            )
        ).mappings().first()
    if row is None:
        return None
    return {"id": str(row["id"]), "name": str(row["name"])}


def _snapshot_sqlite(destination: Path) -> None:
    engine = get_engine()
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Native backup currently supports SQLite installations only")

    raw_connection = engine.raw_connection()
    try:
        source = raw_connection.driver_connection
        if not isinstance(source, sqlite3.Connection):
            raise RuntimeError("Unable to access the SQLite connection for backup")
        with sqlite3.connect(destination) as target:
            source.backup(target)
    finally:
        raw_connection.close()


def create_backup(destination_dir: Path | None = None) -> BackupResult:
    """Create a consistent portable HomePrep backup archive."""
    created_at = _utc_now()
    backup_dir = destination_dir or (Path(settings.data_dir) / "backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    filename = f"homeprep-backup-{timestamp}.zip"
    archive_path = backup_dir / filename

    manifest = {
        "backup_format_version": BACKUP_FORMAT_VERSION,
        "product": "HomePrep Server",
        "server_version": __version__,
        "server_id": str(get_server_id()),
        "created_at": created_at.isoformat(),
        "database": {
            "engine": "sqlite",
            "migration_version": _migration_version(),
        },
        "household": _household_metadata(),
        "components": ["database"],
    }

    with tempfile.TemporaryDirectory(prefix="homeprep-backup-") as temp_dir:
        snapshot_path = Path(temp_dir) / "homeprep.db"
        _snapshot_sqlite(snapshot_path)
        manifest_path = Path(temp_dir) / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(manifest_path, "manifest.json")
            archive.write(snapshot_path, "homeprep.db")

    result = BackupResult(
        filename=filename,
        path=str(archive_path.resolve()),
        created_at=created_at.isoformat(),
        size_bytes=archive_path.stat().st_size,
        format_version=BACKUP_FORMAT_VERSION,
    )
    return result


def list_backups(destination_dir: Path | None = None) -> list[BackupResult]:
    backup_dir = destination_dir or (Path(settings.data_dir) / "backups")
    if not backup_dir.exists():
        return []

    results: list[BackupResult] = []
    for archive_path in sorted(backup_dir.glob("homeprep-backup-*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                manifest = json.loads(archive.read("manifest.json"))
            results.append(
                BackupResult(
                    filename=archive_path.name,
                    path=str(archive_path.resolve()),
                    created_at=str(manifest["created_at"]),
                    size_bytes=archive_path.stat().st_size,
                    format_version=int(manifest["backup_format_version"]),
                )
            )
        except (KeyError, ValueError, OSError, zipfile.BadZipFile, json.JSONDecodeError):
            continue
    return results


def backup_result_dict(result: BackupResult) -> dict[str, str | int]:
    return asdict(result)
