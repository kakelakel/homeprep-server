from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from homeprep_server import __version__
from homeprep_server.standalone_config import (
    DEFAULT_BACKUP_RETENTION,
    DEFAULT_BACKUP_SCHEDULE,
    DEFAULT_PORT,
    default_data_dir,
    load_standalone_config,
    save_standalone_config,
)

SERVICE_NAME = "HomePrepServer"
RELEASE_API = "https://api.github.com/repos/kakelakel/homeprep-server/releases/latest"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run_sc(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sc.exe", *args],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )


def _service_state() -> str:
    result = _run_sc("query", SERVICE_NAME)
    text = f"{result.stdout}\n{result.stderr}".upper()
    if "RUNNING" in text:
        return "Running"
    if "STOPPED" in text:
        return "Stopped"
    if result.returncode != 0:
        return "Not installed"
    return "Starting / stopping"


def _run_elevated_powershell_code(script: str) -> int:
    escaped = script.replace("'", "''")
    command = (
        "$p=Start-Process powershell.exe -Verb RunAs -Wait -PassThru "
        f"-ArgumentList '-NoProfile -WindowStyle Hidden -Command \"{escaped}\"'; "
        "exit $p.ExitCode"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", command],
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return result.returncode


def _run_elevated_powershell(script: str) -> bool:
    return _run_elevated_powershell_code(script) == 0


def _service_action(action: str) -> bool:
    if action == "start":
        script = f"Start-Service -Name '{SERVICE_NAME}' -ErrorAction Stop"
    elif action == "stop":
        script = f"Stop-Service -Name '{SERVICE_NAME}' -ErrorAction Stop"
    elif action == "restart":
        script = f"Restart-Service -Name '{SERVICE_NAME}' -Force -ErrorAction Stop"
    else:
        raise ValueError(f"Unsupported service action: {action}")
    return _run_elevated_powershell(script)


def _server_reachable(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/readyz",
            timeout=1.2,
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(path)  # type: ignore[attr-defined]


def _configured_port() -> int:
    return int(load_standalone_config(default_data_dir()).get("port", DEFAULT_PORT))


def _latest_backup_name(data_dir: Path) -> str:
    backup_dir = data_dir / "backups"
    backups = sorted(backup_dir.glob("homeprep-backup-*.zip"), reverse=True)
    return backups[0].name if backups else "No backups yet"


def _create_local_backup(data_dir: Path) -> Path:
    from homeprep_server.core.backup import create_backup
    from homeprep_server.core.config import settings
    from homeprep_server.database import reset_database_state

    settings.data_dir = data_dir
    settings.database_url = None
    reset_database_state()
    try:
        result = create_backup(data_dir / "backups")
        return Path(result.path)
    finally:
        reset_database_state()


def _validate_local_backup(path: Path):
    from homeprep_server.core.backup import validate_backup

    return validate_backup(path)


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _restore_invocation(archive_path: Path) -> str:
    if getattr(sys, "frozen", False):
        server_executable = Path(sys.executable).with_name("HomePrepServer.exe")
        return f"& {_ps_quote(server_executable)} --restore-backup {_ps_quote(archive_path)}"
    return (
        f"& {_ps_quote(sys.executable)} -m homeprep_server.launcher "
        f"--restore-backup {_ps_quote(archive_path)}"
    )


def _restore_local_backup(archive_path: Path, *, restart_service: bool) -> str:
    restore_command = _restore_invocation(archive_path)
    steps = ["$ErrorActionPreference='Stop'"]
    if restart_service:
        steps.append(f"Stop-Service -Name '{SERVICE_NAME}' -Force -ErrorAction Stop")
    steps.extend(
        [
            restore_command,
            "if ($LASTEXITCODE -ne 0) { exit 10 }",
        ]
    )
    if restart_service:
        steps.append(
            f"try {{ Start-Service -Name '{SERVICE_NAME}' -ErrorAction Stop }} "
            "catch { exit 20 }"
        )
    steps.append("exit 0")
    exit_code = _run_elevated_powershell_code("; ".join(steps))
    if exit_code == 0:
        return "success"
    if exit_code == 20:
        return "restart_failed"
    return "restore_failed"


def _version_key(version: str) -> tuple[int, int, int, int]:
    clean = version.casefold().lstrip("v")
    numbers = [int(part) for part in re.findall(r"\d+", clean)[:3]]
    numbers.extend([0] * (3 - len(numbers)))
    stable = 0 if any(marker in clean for marker in ("dev", "alpha", "beta", "rc")) else 1
    return numbers[0], numbers[1], numbers[2], stable


def _latest_release() -> tuple[str, str] | None:
    request = urllib.request.Request(
        RELEASE_API,
        headers={"User-Agent": f"HomePrepServerManager/{__version__}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return str(payload["tag_name"]), str(payload["html_url"])


def open_homeprep_from_config() -> None:
    webbrowser.open(f"http://127.0.0.1:{_configured_port()}")


class ManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("HomePrep Server Manager")
        self.geometry("700x750")
        self.minsize(640, 680)
        self.data_dir = default_data_dir()
        self.config_data = load_standalone_config(self.data_dir)

        self.status_var = tk.StringVar(value="Checking…")
        self.reachable_var = tk.StringVar(value="Checking…")
        self.backup_var = tk.StringVar(value=_latest_backup_name(self.data_dir))
        self.port_var = tk.StringVar(value=str(self.config_data.get("port", DEFAULT_PORT)))
        self.access_var = tk.StringVar(
            value="LAN" if self.config_data.get("host") == "0.0.0.0" else "Local only"
        )
        self.backup_schedule_var = tk.StringVar(
            value=str(self.config_data.get("backup_schedule", DEFAULT_BACKUP_SCHEDULE)).title()
        )
        self.backup_retention_var = tk.StringVar(
            value=str(self.config_data.get("backup_retention", DEFAULT_BACKUP_RETENTION))
        )

        self._build_ui()
        self.after(150, self.refresh_status)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="HomePrep Server Manager", font=("Segoe UI", 18, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            root,
            text="Manage the local HomePrep Server service and standalone settings.",
        ).pack(anchor="w", pady=(4, 18))

        status = ttk.LabelFrame(root, text="Server", padding=14)
        status.pack(fill="x")
        grid = ttk.Frame(status)
        grid.pack(fill="x")
        ttk.Label(grid, text="Service status:").grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", pady=4
        )
        ttk.Label(grid, text="Web/API:").grid(row=1, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, textvariable=self.reachable_var).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(grid, text="Version:").grid(row=2, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, text=__version__).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(grid, text="Data folder:").grid(row=3, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, text=str(self.data_dir)).grid(row=3, column=1, sticky="w", pady=4)

        buttons = ttk.Frame(status)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Open HomePrep", command=self.open_homeprep).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Start", command=lambda: self.do_service_action("start")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Stop", command=lambda: self.do_service_action("stop")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Restart", command=lambda: self.do_service_action("restart")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Refresh", command=self.refresh_status).pack(side="right")

        settings = ttk.LabelFrame(root, text="Network settings", padding=14)
        settings.pack(fill="x", pady=(16, 0))
        form = ttk.Frame(settings)
        form.pack(fill="x")
        ttk.Label(form, text="Port").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Entry(form, textvariable=self.port_var, width=12).grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(form, text="Access").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Combobox(
            form,
            textvariable=self.access_var,
            values=("Local only", "LAN"),
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(
            form,
            text="LAN exposes HomePrep on this computer's network interfaces. Authentication still applies.",
            wraplength=480,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 8))

        backups = ttk.LabelFrame(root, text="Backups", padding=14)
        backups.pack(fill="x", pady=(16, 0))
        backup_form = ttk.Frame(backups)
        backup_form.pack(fill="x")
        ttk.Label(backup_form, text="Latest:").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=4)
        ttk.Label(backup_form, textvariable=self.backup_var).grid(row=0, column=1, columnspan=2, sticky="w", pady=4)
        ttk.Label(backup_form, text="Schedule:").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=4)
        ttk.Combobox(
            backup_form,
            textvariable=self.backup_schedule_var,
            values=("Off", "Daily", "Weekly"),
            state="readonly",
            width=14,
        ).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(backup_form, text="Keep backups:").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=4)
        ttk.Entry(backup_form, textvariable=self.backup_retention_var, width=8).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(backup_form, text="files").grid(row=2, column=2, sticky="w", pady=4)

        backup_buttons = ttk.Frame(backups)
        backup_buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(backup_buttons, text="Back up now", command=self.backup_now).pack(side="left")
        ttk.Button(backup_buttons, text="Restore backup…", command=self.restore_backup).pack(side="left", padx=8)
        ttk.Button(
            backup_buttons,
            text="Open backup folder",
            command=lambda: _open_folder(self.data_dir / "backups"),
        ).pack(side="left")

        ttk.Button(root, text="Save settings and restart", command=self.save_settings).pack(
            anchor="w", pady=(16, 0)
        )

        tools = ttk.Frame(root)
        tools.pack(fill="x", pady=(16, 0))
        ttk.Button(tools, text="Check for updates", command=self.check_for_updates).pack(side="left")
        ttk.Button(tools, text="Open data folder", command=lambda: _open_folder(self.data_dir)).pack(side="left", padx=8)
        ttk.Button(tools, text="Open Windows Services", command=self.open_services).pack(side="left")

    def current_port(self) -> int:
        try:
            return int(self.port_var.get())
        except ValueError:
            return DEFAULT_PORT

    def refresh_status(self) -> None:
        state = _service_state()
        port = self.current_port()
        self.status_var.set(state)
        self.reachable_var.set(
            f"Online at http://127.0.0.1:{port}" if _server_reachable(port) else "Not reachable"
        )
        self.backup_var.set(_latest_backup_name(self.data_dir))

    def open_homeprep(self) -> None:
        webbrowser.open(f"http://127.0.0.1:{self.current_port()}")

    def do_service_action(self, action: str) -> None:
        if not _service_action(action):
            messagebox.showerror(
                "HomePrep",
                f"Could not {action} HomePrep Server. Administrator permission may have been cancelled.",
            )
            return
        self.after(900, self.refresh_status)

    def backup_now(self) -> None:
        try:
            archive_path = _create_local_backup(self.data_dir)
        except Exception as exc:
            messagebox.showerror("Backup failed", f"HomePrep could not create a backup.\n\n{exc}")
            return
        self.backup_var.set(archive_path.name)
        messagebox.showinfo("Backup complete", f"Backup created successfully:\n\n{archive_path}")

    def restore_backup(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select HomePrep backup",
            initialdir=self.data_dir / "backups",
            filetypes=(("HomePrep backup", "*.zip"), ("All files", "*.*")),
        )
        if not selected:
            return

        archive_path = Path(selected)
        validation = _validate_local_backup(archive_path)
        if not validation.valid:
            messagebox.showerror("Invalid backup", f"This backup cannot be restored.\n\n{validation.error}")
            return

        household = validation.household_name or "No household configured"
        if not messagebox.askyesno(
            "Restore HomePrep backup",
            (
                "This will replace the current HomePrep database.\n\n"
                f"Backup: {archive_path.name}\n"
                f"Created: {validation.created_at}\n"
                f"Household: {household}\n\n"
                "HomePrep will create a safety backup of the current database first. Continue?"
            ),
        ):
            return

        was_running = _service_state() == "Running"
        result = _restore_local_backup(archive_path, restart_service=was_running)
        self.after(900, self.refresh_status)
        self.backup_var.set(_latest_backup_name(self.data_dir))

        if result == "restore_failed":
            messagebox.showerror(
                "Restore failed",
                "HomePrep could not restore the selected backup. The current database was left intact whenever possible.",
            )
            return
        if result == "restart_failed":
            messagebox.showwarning(
                "Restore complete — server not started",
                (
                    "The backup was restored successfully, but HomePrep Server could not be restarted automatically. "
                    "Start the service from Server Manager or Windows Services."
                ),
            )
            return
        messagebox.showinfo("Restore complete", "The backup was restored successfully. HomePrep is ready to use.")

    def check_for_updates(self) -> None:
        try:
            release = _latest_release()
        except (OSError, urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Update check failed", f"HomePrep could not check for updates.\n\n{exc}")
            return

        if release is None:
            messagebox.showinfo("HomePrep updates", "No published HomePrep Server release is available yet.")
            return

        latest_version, release_url = release
        if _version_key(latest_version) > _version_key(__version__):
            if messagebox.askyesno(
                "Update available",
                (
                    f"Installed: {__version__}\n"
                    f"Latest: {latest_version}\n\n"
                    "A newer HomePrep Server release is available. Open the release page?"
                ),
            ):
                webbrowser.open(release_url)
            return

        messagebox.showinfo("HomePrep updates", f"HomePrep Server {__version__} is up to date.")

    def save_settings(self) -> None:
        try:
            port = int(self.port_var.get())
            retention = int(self.backup_retention_var.get())
            host = "0.0.0.0" if self.access_var.get() == "LAN" else "127.0.0.1"
            save_standalone_config(
                host,
                port,
                self.data_dir,
                backup_schedule=self.backup_schedule_var.get().casefold(),
                backup_retention=retention,
            )
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Unable to save", str(exc))
            return

        if not _service_action("restart"):
            messagebox.showwarning(
                "Settings saved",
                "Settings were saved, but the server could not be restarted. Restart it from the manager when ready.",
            )
            return
        self.after(900, self.refresh_status)
        messagebox.showinfo("HomePrep", "Settings saved and HomePrep Server restarted.")

    def open_services(self) -> None:
        try:
            subprocess.Popen(["mmc.exe", "services.msc"])
        except OSError as exc:
            messagebox.showerror("HomePrep", f"Could not open Windows Services.\n\n{exc}")


def main() -> None:
    if os.name != "nt":
        raise SystemExit("HomePrep Server Manager currently requires Windows")

    parser = argparse.ArgumentParser(description="HomePrep Server Manager")
    parser.add_argument("--open-homeprep", action="store_true")
    args = parser.parse_args()
    if args.open_homeprep:
        open_homeprep_from_config()
        return

    ManagerApp().mainloop()


if __name__ == "__main__":
    main()
