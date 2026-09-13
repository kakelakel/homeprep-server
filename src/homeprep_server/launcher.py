import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _configure_runtime_paths() -> None:
    if "HOMEPREP_DATA_DIR" not in os.environ:
        if os.name == "nt":
            base = Path(os.environ.get("PROGRAMDATA", Path.home()))
            os.environ["HOMEPREP_DATA_DIR"] = str(base / "HomePrep")
        else:
            os.environ["HOMEPREP_DATA_DIR"] = str(Path("data").resolve())

    # Alembic connects directly to SQLite before the FastAPI lifespan or
    # database helper gets a chance to create the persistent data directory.
    # Ensure it exists before migrations run, especially for native Windows.
    Path(os.environ["HOMEPREP_DATA_DIR"]).mkdir(parents=True, exist_ok=True)

    if os.name == "nt" and "HOMEPREP_HOST" not in os.environ:
        os.environ["HOMEPREP_HOST"] = "127.0.0.1"

    if getattr(sys, "frozen", False) and "HOMEPREP_WEB_DIR" not in os.environ:
        os.environ["HOMEPREP_WEB_DIR"] = str(_bundle_root() / "web" / "dist")


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    root = _bundle_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")


def _open_browser_later(url: str) -> None:
    def worker() -> None:
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="HomePrep Server")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()

    _configure_runtime_paths()
    _run_migrations()

    import uvicorn

    from homeprep_server.core.config import settings
    from homeprep_server.main import app

    if args.open_browser:
        _open_browser_later(f"http://127.0.0.1:{settings.port}")

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
