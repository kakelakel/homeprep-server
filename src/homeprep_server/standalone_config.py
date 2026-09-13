from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def default_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("PROGRAMDATA", Path.home()))
        return base / "HomePrep"
    return Path("data").resolve()


def config_path(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / "config.json"


def load_standalone_config(data_dir: Path | None = None) -> dict[str, Any]:
    path = config_path(data_dir)
    if not path.exists():
        return {"host": DEFAULT_HOST, "port": DEFAULT_PORT}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"host": DEFAULT_HOST, "port": DEFAULT_PORT}

    host = str(raw.get("host", DEFAULT_HOST))
    port_raw = raw.get("port", DEFAULT_PORT)
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = DEFAULT_PORT

    if not 1 <= port <= 65535:
        port = DEFAULT_PORT

    if host not in {"127.0.0.1", "0.0.0.0"}:
        host = DEFAULT_HOST

    return {"host": host, "port": port}


def save_standalone_config(host: str, port: int, data_dir: Path | None = None) -> Path:
    if host not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError("Unsupported bind address")
    if not 1 <= int(port) <= 65535:
        raise ValueError("Port must be between 1 and 65535")

    path = config_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"host": host, "port": int(port)}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
