"""Native Windows Service support for HomePrep Server.

The service host uses the Windows Service Control Manager API through ctypes so
HomePrep does not require an additional wrapper or pywin32 dependency. Small
management helpers use the built-in sc.exe tool for install/update/start/stop.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

SERVICE_NAME = "HomePrepServer"
SERVICE_DISPLAY_NAME = "HomePrep Server"
SERVICE_DESCRIPTION = "Self-hosted HomePrep preparedness server"

SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_START_PENDING = 0x00000002
SERVICE_STOP_PENDING = 0x00000003
SERVICE_RUNNING = 0x00000004
SERVICE_STOPPED = 0x00000001
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_ACCEPT_SHUTDOWN = 0x00000004
SERVICE_CONTROL_STOP = 0x00000001
SERVICE_CONTROL_SHUTDOWN = 0x00000005
NO_ERROR = 0


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", wintypes.DWORD),
        ("dwCurrentState", wintypes.DWORD),
        ("dwControlsAccepted", wintypes.DWORD),
        ("dwWin32ExitCode", wintypes.DWORD),
        ("dwServiceSpecificExitCode", wintypes.DWORD),
        ("dwCheckPoint", wintypes.DWORD),
        ("dwWaitHint", wintypes.DWORD),
    ]


LPHANDLER_FUNCTION_EX = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.LPVOID,
)
LPSERVICE_MAIN_FUNCTION = ctypes.WINFUNCTYPE(
    None,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.LPWSTR),
)


class SERVICE_TABLE_ENTRY(ctypes.Structure):
    _fields_ = [
        ("lpServiceName", wintypes.LPWSTR),
        ("lpServiceProc", LPSERVICE_MAIN_FUNCTION),
    ]


ServiceWorkload = Callable[[threading.Event, Callable[[], None]], None]


def _run_sc(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    if os.name != "nt":
        raise RuntimeError("Windows service management is only available on Windows")
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        ["sc.exe", *args],
        check=check,
        capture_output=True,
        text=True,
        creationflags=creationflags,
    )


def service_exists() -> bool:
    return _run_sc("query", SERVICE_NAME, check=False).returncode == 0


def _wait_for_service_registration(timeout_seconds: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if service_exists():
            return
        time.sleep(0.1)
    raise RuntimeError("HomePrep service was not registered by Windows in time")


def install_windows_service(executable: str | Path) -> None:
    """Create or update the HomePrep Windows service."""
    executable_path = str(Path(executable).resolve())
    binary_path = f'"{executable_path}" --service'
    common = [
        SERVICE_NAME,
        "binPath=",
        binary_path,
        "start=",
        "delayed-auto",
        "DisplayName=",
        SERVICE_DISPLAY_NAME,
    ]
    if service_exists():
        _run_sc("stop", SERVICE_NAME, check=False)
        _run_sc("config", *common)
    else:
        _run_sc("create", *common)
        _wait_for_service_registration()
    _run_sc("description", SERVICE_NAME, SERVICE_DESCRIPTION)


def start_windows_service() -> None:
    _wait_for_service_registration()
    result = _run_sc("start", SERVICE_NAME, check=False)
    # 1056 means the service is already running.
    if result.returncode != 0 and "1056" not in (result.stdout + result.stderr):
        raise RuntimeError(result.stdout or result.stderr or "Unable to start HomePrep service")


def stop_windows_service() -> None:
    _run_sc("stop", SERVICE_NAME, check=False)


def remove_windows_service() -> None:
    stop_windows_service()
    _run_sc("delete", SERVICE_NAME, check=False)


class WindowsServiceHost:
    def __init__(self, workload: ServiceWorkload) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows service mode is only available on Windows")

        self.workload = workload
        self.stop_event = threading.Event()
        self.status_handle: wintypes.HANDLE | None = None
        self.status = SERVICE_STATUS()
        self._handler_callback = LPHANDLER_FUNCTION_EX(self._control_handler)
        self._service_main_callback = LPSERVICE_MAIN_FUNCTION(self._service_main)

        self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self.advapi32.RegisterServiceCtrlHandlerExW.argtypes = [
            wintypes.LPCWSTR,
            LPHANDLER_FUNCTION_EX,
            wintypes.LPVOID,
        ]
        self.advapi32.RegisterServiceCtrlHandlerExW.restype = wintypes.HANDLE
        self.advapi32.SetServiceStatus.argtypes = [wintypes.HANDLE, ctypes.POINTER(SERVICE_STATUS)]
        self.advapi32.SetServiceStatus.restype = wintypes.BOOL
        self.advapi32.StartServiceCtrlDispatcherW.argtypes = [
            ctypes.POINTER(SERVICE_TABLE_ENTRY)
        ]
        self.advapi32.StartServiceCtrlDispatcherW.restype = wintypes.BOOL

    def _set_status(
        self,
        state: int,
        *,
        controls: int = 0,
        exit_code: int = NO_ERROR,
        wait_hint: int = 0,
    ) -> None:
        if self.status_handle is None:
            return
        self.status.dwServiceType = SERVICE_WIN32_OWN_PROCESS
        self.status.dwCurrentState = state
        self.status.dwControlsAccepted = controls
        self.status.dwWin32ExitCode = exit_code
        self.status.dwServiceSpecificExitCode = 0
        self.status.dwCheckPoint = 0
        self.status.dwWaitHint = wait_hint
        if not self.advapi32.SetServiceStatus(self.status_handle, ctypes.byref(self.status)):
            raise ctypes.WinError(ctypes.get_last_error())

    def _mark_running(self) -> None:
        self._set_status(
            SERVICE_RUNNING,
            controls=SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN,
        )

    def _control_handler(
        self,
        control: int,
        _event_type: int,
        _event_data: wintypes.LPVOID,
        _context: wintypes.LPVOID,
    ) -> int:
        if control in (SERVICE_CONTROL_STOP, SERVICE_CONTROL_SHUTDOWN):
            self._set_status(SERVICE_STOP_PENDING, wait_hint=15_000)
            self.stop_event.set()
        return NO_ERROR

    def _service_main(
        self,
        _argc: int,
        _argv: ctypes.POINTER(wintypes.LPWSTR),
    ) -> None:
        self.status_handle = self.advapi32.RegisterServiceCtrlHandlerExW(
            SERVICE_NAME,
            self._handler_callback,
            None,
        )
        if not self.status_handle:
            return

        self._set_status(SERVICE_START_PENDING, wait_hint=30_000)
        exit_code = NO_ERROR
        try:
            self.workload(self.stop_event, self._mark_running)
        except Exception:
            exit_code = 1
        finally:
            self._set_status(SERVICE_STOPPED, exit_code=exit_code)

    def run(self) -> None:
        table = (SERVICE_TABLE_ENTRY * 2)()
        table[0].lpServiceName = SERVICE_NAME
        table[0].lpServiceProc = self._service_main_callback
        table[1].lpServiceName = None
        table[1].lpServiceProc = LPSERVICE_MAIN_FUNCTION()

        if not self.advapi32.StartServiceCtrlDispatcherW(table):
            raise ctypes.WinError(ctypes.get_last_error())


def run_windows_service(workload: ServiceWorkload) -> None:
    """Connect the current process to the Windows Service Control Manager."""
    WindowsServiceHost(workload).run()
