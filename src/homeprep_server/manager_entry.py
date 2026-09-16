"""Windows Server Manager entry point.

Keeps restore recovery conservative: if the Manager stopped a running HomePrep
service before restore, it always attempts to start that service again, even when
the restore command itself fails. This avoids leaving a previously healthy Server
silently stopped after a failed recovery attempt.
"""

from __future__ import annotations

from pathlib import Path

from homeprep_server import manager
from homeprep_server import updater


def restore_local_backup(archive_path: Path, *, restart_service: bool) -> str:
    restore_command = manager._restore_invocation(archive_path)
    steps = ["$ErrorActionPreference='Stop'"]

    if restart_service:
        steps.append(f"Stop-Service -Name '{manager.SERVICE_NAME}' -Force -ErrorAction Stop")

    # Capture the restore result rather than exiting immediately. A service that
    # was running before restore should be restarted regardless of restore success.
    steps.extend(
        [
            "$restoreExit=0",
            restore_command,
            "$restoreExit=$LASTEXITCODE",
        ]
    )

    if restart_service:
        steps.append(
            f"try {{ Start-Service -Name '{manager.SERVICE_NAME}' -ErrorAction Stop }} "
            "catch { if ($restoreExit -eq 0) { exit 20 } else { exit 30 } }"
        )

    steps.extend(
        [
            "if ($restoreExit -ne 0) { exit 10 }",
            "exit 0",
        ]
    )

    exit_code = manager._run_elevated_powershell_code("; ".join(steps))
    if exit_code == 0:
        return "success"
    if exit_code == 20:
        return "restart_failed"
    return "restore_failed"


def check_for_updates(app: manager.ManagerApp) -> None:
    updater.check_for_updates(
        app,
        release_api=manager.RELEASE_API,
        installed_version=manager.__version__,
    )


def main() -> None:
    manager._restore_local_backup = restore_local_backup
    manager.ManagerApp.check_for_updates = check_for_updates
    manager.main()


if __name__ == "__main__":
    main()
