from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from homeprep_server import __version__
from homeprep_server.core.config import settings
from homeprep_server.core.identity import get_server_id
from homeprep_server.database import get_engine, reset_database_state

BACKUP_FORMAT_VERSION = 1


@dataclass(frozen=True)
class BackupResult:
    filename: str
    path: str
    created_at: str
    size_bytes: int
    format_version: int


@dataclass(frozen=True)
class BackupValidation:
    valid: bool
    format_version: int | None
    server_version: str | None
    created_at: str | None
    household_id: str | None
    household_name: str | None
    migration_version: str | None
    error: str | None = None


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
    target: sqlite3.Connection | None = None
    try:
        source = raw_connection.driver_connection
        if not isinstance(source, sqlite3.Connection):
            raise RuntimeError("Unable to access the SQLite connection for backup")
        target = sqlite3.connect(destination)
        source.backup(target)
    finally:
        if target is not None:
            target.close()
        raw_connection.close()


def _configured_sqlite_path() -> Path:
    url = make_url(settings.resolved_database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        raise RuntimeError("Restore currently supports file-based SQLite installations only")
    database_path = Path(url.database)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    return database_path.resolve()


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

    return BackupResult(
        filename=filename,
        path=str(archive_path.resolve()),
        created_at=created_at.isoformat(),
        size_bytes=archive_path.stat().st_size,
        format_version=BACKUP_FORMAT_VERSION,
    )


def validate_backup(archive_path: Path) -> BackupValidation:
    """Validate backup structure, manifest compatibility and SQLite integrity."""
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = set(archive.namelist())
            required = {"manifest.json", "homeprep.db"}
            if not required.issubset(names):
                raise ValueError("Backup archive is missing required components")

            manifest = json.loads(archive.read("manifest.json"))
            format_version = int(manifest["backup_format_version"])
            if format_version != BACKUP_FORMAT_VERSION:
                raise ValueError(
                    f"Unsupported backup format version {format_version}; "
                    f"expected {BACKUP_FORMAT_VERSION}"
                )
            if manifest.get("product") != "HomePrep Server":
                raise ValueError("Backup archive is not a HomePrep Server backup")
            if manifest.get("database", {}).get("engine") != "sqlite":
                raise ValueError("Backup database engine is not supported")

            household = manifest.get("household") or {}
            with tempfile.TemporaryDirectory(prefix="homeprep-validate-") as temp_dir:
                database_path = Path(temp_dir) / "homeprep.db"
                database_path.write_bytes(archive.read("homeprep.db"))
                connection = sqlite3.connect(database_path)
                try:
                    integrity = connection.execute("PRAGMA integrity_check").fetchone()
                finally:
                    connection.close()
                if integrity != ("ok",):
                    raise ValueError("SQLite integrity check failed")

            return BackupValidation(
                valid=True,
                format_version=format_version,
                server_version=str(manifest.get("server_version")),
                created_at=str(manifest.get("created_at")),
                household_id=str(household.get("id")) if household.get("id") else None,
                household_name=(
                    str(household.get("name")) if household.get("name") else None
                ),
                migration_version=(
                    str(manifest.get("database", {}).get("migration_version"))
                    if manifest.get("database", {}).get("migration_version")
                    else None
                ),
            )
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        return BackupValidation(
            valid=False,
            format_version=None,
            server_version=None,
            created_at=None,
            household_id=None,
            household_name=None,
            migration_version=None,
            error=str(exc),
        )


def restore_backup(archive_path: Path, *, safety_backup: bool = True) -> BackupValidation:
    """Restore a validated backup while the normal server process is offline."""
    validation = validate_backup(archive_path)
    if not validation.valid:
        raise RuntimeError(validation.error or "Backup validation failed")

    database_path = _configured_sqlite_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if safety_backup and database_path.exists():
        create_backup(Path(settings.data_dir) / "backups" / "pre-restore")

    with tempfile.TemporaryDirectory(prefix="homeprep-restore-") as temp_dir:
        candidate_path = Path(temp_dir) / "homeprep.db"
        with zipfile.ZipFile(archive_path, "r") as archive:
            candidate_path.write_bytes(archive.read("homeprep.db"))

        reset_database_state()
        replacement_path = database_path.with_suffix(database_path.suffix + ".restore-new")
        shutil.copy2(candidate_path, replacement_path)
        replacement_path.replace(database_path)

    reset_database_state()
    return validation


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


def backup_due(schedule: str, destination_dir: Path | None = None) -> bool:
    """Return whether a daily/weekly backup is due based on the latest archive."""
    schedule = schedule.casefold()
    if schedule == "off":
        return False
    interval = timedelta(days=1 if schedule == "daily" else 7)
    backups = list_backups(destination_dir)
    if not backups:
        return True
    try:
        latest = datetime.fromisoformat(backups[0].created_at)
    except ValueError:
        return True
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return _utc_now() - latest >= interval


def prune_backups(retention: int, destination_dir: Path | None = None) -> int:
    """Delete oldest normal backup archives beyond the configured retention count."""
    if retention < 1:
        raise ValueError("Backup retention must be at least 1")
    backup_dir = destination_dir or (Path(settings.data_dir) / "backups")
    archives = sorted(backup_dir.glob("homeprep-backup-*.zip"), reverse=True)
    removed = 0
    for archive_path in archives[retention:]:
        archive_path.unlink(missing_ok=True)
        removed += 1
    return removed


def backup_result_dict(result: BackupResult) -> dict[str, str | int]:
    return asdict(result)
