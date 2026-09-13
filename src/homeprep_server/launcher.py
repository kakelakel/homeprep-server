import argparse
import os
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

from homeprep_server.standalone_config import default_data_dir, load_standalone_config


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def _configure_frozen_stdio() -> None:
    """Provide valid stdio streams for windowed PyInstaller builds."""
    if not getattr(sys, "frozen", False):
        return

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


def _configure_runtime_paths() -> None:
    if "HOMEPREP_DATA_DIR" not in os.environ:
        os.environ["HOMEPREP_DATA_DIR"] = str(default_data_dir())

    data_dir = Path(os.environ["HOMEPREP_DATA_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)

    # Native standalone installs keep normal settings in config.json. Explicit
    # environment variables still win for Docker and advanced deployments.
    standalone = load_standalone_config(data_dir)
    os.environ.setdefault("HOMEPREP_HOST", str(standalone["host"]))
    os.environ.setdefault("HOMEPREP_PORT", str(standalone["port"]))

    if getattr(sys, "frozen", False) and "HOMEPREP_WEB_DIR" not in os.environ:
        os.environ["HOMEPREP_WEB_DIR"] = str(_bundle_root() / "web" / "dist")


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    root = _bundle_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")


def _backup_settings() -> tuple[str, int]:
    data_dir = Path(os.environ["HOMEPREP_DATA_DIR"])
    config = load_standalone_config(data_dir)
    return str(config["backup_schedule"]), int(config["backup_retention"])


def _start_backup_scheduler(stop_event: threading.Event) -> threading.Thread:
    from homeprep_server.core.backup_scheduler import run_backup_scheduler

    data_dir = Path(os.environ["HOMEPREP_DATA_DIR"])
    thread = threading.Thread(
        target=run_backup_scheduler,
        kwargs={
            "stop_event": stop_event,
            "data_dir": data_dir,
            "settings_provider": _backup_settings,
        },
        name="homeprep-backup-scheduler",
        daemon=True,
    )
    thread.start()
    return thread


def _open_browser_later(url: str) -> None:
    def worker() -> None:
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


def _run_foreground(*, open_browser: bool) -> None:
    _run_migrations()

    import uvicorn

    from homeprep_server.core.config import settings
    from homeprep_server.main import app

    if open_browser:
        _open_browser_later(f"http://127.0.0.1:{settings.port}")

    stop_event = threading.Event()
    scheduler_thread = _start_backup_scheduler(stop_event)
    try:
        uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
    finally:
        stop_event.set()
        scheduler_thread.join(timeout=2)


def _run_service_workload(
    stop_event: threading.Event,
    mark_running: Callable[[], None],
) -> None:
    """Run Uvicorn until the Windows Service Control Manager asks us to stop."""
    _run_migrations()

    import uvicorn

    from homeprep_server.core.config import settings
    from homeprep_server.main import app

    scheduler_thread = _start_backup_scheduler(stop_event)
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="homeprep-uvicorn")
    server_thread.start()

    deadline = time.monotonic() + 30
    while server_thread.is_alive() and not server.started and not stop_event.is_set():
        if time.monotonic() >= deadline:
            server.should_exit = True
            server_thread.join(timeout=10)
            raise RuntimeError("HomePrep Server did not become ready in time")
        time.sleep(0.1)

    if not server_thread.is_alive():
        raise RuntimeError("HomePrep Server stopped during service startup")

    mark_running()
    stop_event.wait()
    server.should_exit = True
    server_thread.join(timeout=20)
    scheduler_thread.join(timeout=2)
    if server_thread.is_alive():
        server.force_exit = True
        server_thread.join(timeout=5)


def _validate_backup(path: str) -> int:
    from homeprep_server.core.backup import validate_backup

    result = validate_backup(Path(path))
    if not result.valid:
        print(result.error or "Backup validation failed", file=sys.stderr)
        return 1
    print(
        f"Valid HomePrep backup: format {result.format_version}, "
        f"created {result.created_at}, household {result.household_name or 'not configured'}"
    )
    return 0


def _restore_backup(path: str) -> int:
    from homeprep_server.core.backup import restore_backup

    result = restore_backup(Path(path), safety_backup=True)
    print(
        f"Restored HomePrep backup from {result.created_at}; "
        "a pre-restore safety backup was created when existing data was present."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="HomePrep Server")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--validate-backup", metavar="PATH")
    parser.add_argument("--restore-backup", metavar="PATH")
    parser.add_argument("--service", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--install-service", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--start-service", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stop-service", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--remove-service", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    _configure_frozen_stdio()
    _configure_runtime_paths()

    if args.validate_backup:
        raise SystemExit(_validate_backup(args.validate_backup))
    if args.restore_backup:
        raise SystemExit(_restore_backup(args.restore_backup))

    service_action = any(
        (
            args.service,
            args.install_service,
            args.start_service,
            args.stop_service,
            args.remove_service,
        )
    )
    if service_action and os.name != "nt":
        parser.error("Windows service commands are only available on Windows")

    if args.install_service:
        from homeprep_server.windows_service import install_windows_service

        install_windows_service(sys.executable)
        return
    if args.start_service:
        from homeprep_server.windows_service import start_windows_service

        start_windows_service()
        return
    if args.stop_service:
        from homeprep_server.windows_service import stop_windows_service

        stop_windows_service()
        return
    if args.remove_service:
        from homeprep_server.windows_service import remove_windows_service

        remove_windows_service()
        return
    if args.service:
        from homeprep_server.windows_service import run_windows_service

        run_windows_service(_run_service_workload)
        return

    _run_foreground(open_browser=args.open_browser)


if __name__ == "__main__":
    main()
