from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from homeprep_server.core.backup import backup_due, create_backup, prune_backups

BackupSettingsProvider = Callable[[], tuple[str, int]]


def run_backup_scheduler(
    stop_event: threading.Event,
    *,
    data_dir: Path,
    settings_provider: BackupSettingsProvider,
    check_interval_seconds: float = 3600,
) -> None:
    """Run scheduled HomePrep backups until the supplied stop event is set."""
    backup_dir = data_dir / "backups"
    while not stop_event.is_set():
        schedule, retention = settings_provider()
        try:
            if backup_due(schedule, backup_dir):
                create_backup(backup_dir)
                prune_backups(retention, backup_dir)
        except Exception:
            # Backup failures must not crash the HomePrep Server process. Status
            # reporting/logging will be expanded with the backup administration UI.
            pass

        stop_event.wait(check_interval_seconds)
