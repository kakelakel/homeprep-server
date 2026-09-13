from __future__ import annotations

import ctypes
import os
import subprocess
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from homeprep_server import __version__
from homeprep_server.standalone_config import (
    DEFAULT_PORT,
    default_data_dir,
    load_standalone_config,
    save_standalone_config,
)

SERVICE_NAME = "HomePrepServer"
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


def _run_elevated_service_action(action: str) -> bool:
    params = f'{action} "{SERVICE_NAME}"'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "sc.exe", params, None, 0)
    return rc > 32


def _server_reachable(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=1.2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(path)  # type: ignore[attr-defined]


class ManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("HomePrep Server Manager")
        self.geometry("610x470")
        self.minsize(560, 430)
        self.data_dir = default_data_dir()
        self.config_data = load_standalone_config(self.data_dir)

        self.status_var = tk.StringVar(value="Checking…")
        self.reachable_var = tk.StringVar(value="Checking…")
        self.port_var = tk.StringVar(value=str(self.config_data.get("port", DEFAULT_PORT)))
        self.access_var = tk.StringVar(
            value="LAN" if self.config_data.get("host") == "0.0.0.0" else "Local only"
        )

        self._build_ui()
        self.after(150, self.refresh_status)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="HomePrep Server Manager", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Manage the local HomePrep Server service and standalone settings.",
        ).pack(anchor="w", pady=(4, 18))

        status = ttk.LabelFrame(root, text="Server", padding=14)
        status.pack(fill="x")
        grid = ttk.Frame(status)
        grid.pack(fill="x")
        ttk.Label(grid, text="Service status:").grid(row=0, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(grid, text="Web/API:").grid(row=1, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, textvariable=self.reachable_var).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(grid, text="Version:").grid(row=2, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, text=__version__).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(grid, text="Data folder:").grid(row=3, column=0, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(grid, text=str(self.data_dir)).grid(row=3, column=1, sticky="w", pady=4)

        buttons = ttk.Frame(status)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Open HomePrep", command=self.open_homeprep).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Start", command=lambda: self.service_action("start")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Stop", command=lambda: self.service_action("stop")).pack(side="left", padx=4)
        ttk.Button(buttons, text="Restart", command=self.restart_service).pack(side="left", padx=4)
        ttk.Button(buttons, text="Refresh", command=self.refresh_status).pack(side="right")

        settings = ttk.LabelFrame(root, text="Network settings", padding=14)
        settings.pack(fill="x", pady=(16, 0))
        form = ttk.Frame(settings)
        form.pack(fill="x")
        ttk.Label(form, text="Port").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Entry(form, textvariable=self.port_var, width=12).grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(form, text="Access").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=6)
        access = ttk.Combobox(
            form,
            textvariable=self.access_var,
            values=("Local only", "LAN"),
            state="readonly",
            width=18,
        )
        access.grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(
            form,
            text="LAN exposes HomePrep on this computer's network interfaces. Authentication still applies.",
            wraplength=390,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 8))
        ttk.Button(settings, text="Save settings and restart", command=self.save_settings).pack(anchor="w")

        tools = ttk.Frame(root)
        tools.pack(fill="x", pady=(16, 0))
        ttk.Button(tools, text="Open data folder", command=lambda: _open_folder(self.data_dir)).pack(side="left")
        ttk.Button(tools, text="Open Windows Services", command=self.open_services).pack(side="left", padx=8)

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

    def open_homeprep(self) -> None:
        webbrowser.open(f"http://127.0.0.1:{self.current_port()}")

    def service_action(self, action: str) -> None:
        if not _run_elevated_service_action(action):
            messagebox.showerror("HomePrep", f"Could not request permission to {action} the service.")
            return
        self.after(1600, self.refresh_status)

    def restart_service(self) -> None:
        if _service_state() == "Running":
            if not _run_elevated_service_action("stop"):
                return
            self.after(1800, lambda: self._finish_restart())
        else:
            self.service_action("start")

    def _finish_restart(self) -> None:
        _run_elevated_service_action("start")
        self.after(1800, self.refresh_status)

    def save_settings(self) -> None:
        try:
            port = int(self.port_var.get())
            host = "0.0.0.0" if self.access_var.get() == "LAN" else "127.0.0.1"
            save_standalone_config(host, port, self.data_dir)
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Unable to save", str(exc))
            return

        messagebox.showinfo(
            "HomePrep",
            "Settings saved. HomePrep Server will now be restarted.",
        )
        self.restart_service()

    def open_services(self) -> None:
        subprocess.Popen(["services.msc"], creationflags=CREATE_NO_WINDOW)


def main() -> None:
    if os.name != "nt":
        raise SystemExit("HomePrep Server Manager currently requires Windows")
    ManagerApp().mainloop()


if __name__ == "__main__":
    main()
