from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_BACKUP_SCHEDULE = "off"
DEFAULT_BACKUP_RETENTION = 14
BACKUP_SCHEDULES = {"off", "daily", "weekly"}


def default_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("PROGRAMDATA", Path.home()))
        return base / "HomePrep"
    return Path("data").resolve()


def config_path(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / "config.json"


def _defaults() -> dict[str, Any]:
    return {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "backup_schedule": DEFAULT_BACKUP_SCHEDULE,
        "backup_retention": DEFAULT_BACKUP_RETENTION,
    }


def load_standalone_config(data_dir: Path | None = None) -> dict[str, Any]:
    path = config_path(data_dir)
    if not path.exists():
        return _defaults()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _defaults()

    host = str(raw.get("host", DEFAULT_HOST))
    port_raw = raw.get("port", DEFAULT_PORT)
    backup_schedule = str(raw.get("backup_schedule", DEFAULT_BACKUP_SCHEDULE)).casefold()
    retention_raw = raw.get("backup_retention", DEFAULT_BACKUP_RETENTION)

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    try:
        backup_retention = int(retention_raw)
    except (TypeError, ValueError):
        backup_retention = DEFAULT_BACKUP_RETENTION

    if not 1 <= port <= 65535:
        port = DEFAULT_PORT
    if host not in {"127.0.0.1", "0.0.0.0"}:
        host = DEFAULT_HOST
    if backup_schedule not in BACKUP_SCHEDULES:
        backup_schedule = DEFAULT_BACKUP_SCHEDULE
    if not 1 <= backup_retention <= 365:
        backup_retention = DEFAULT_BACKUP_RETENTION

    return {
        "host": host,
        "port": port,
        "backup_schedule": backup_schedule,
        "backup_retention": backup_retention,
    }


def save_standalone_config(
    host: str,
    port: int,
    data_dir: Path | None = None,
    *,
    backup_schedule: str | None = None,
    backup_retention: int | None = None,
) -> Path:
    if host not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError("Unsupported bind address")
    if not 1 <= int(port) <= 65535:
        raise ValueError("Port must be between 1 and 65535")

    current = load_standalone_config(data_dir)
    schedule = backup_schedule or str(current["backup_schedule"])
    retention = int(
        backup_retention if backup_retention is not None else current["backup_retention"]
    )
    schedule = schedule.casefold()
    if schedule not in BACKUP_SCHEDULES:
        raise ValueError("Backup schedule must be off, daily or weekly")
    if not 1 <= retention <= 365:
        raise ValueError("Backup retention must be between 1 and 365 backups")

    path = config_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": host,
        "port": int(port),
        "backup_schedule": schedule,
        "backup_retention": retention,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
