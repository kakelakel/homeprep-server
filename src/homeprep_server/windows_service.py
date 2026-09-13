"""Minimal native Windows Service host for HomePrep Server.

This module deliberately uses the Windows Service Control Manager API through
ctypes so the packaged HomePrep executable does not need an additional service
wrapper or pywin32 runtime dependency.
"""

from __future__ import annotations

import ctypes
import os
import threading
from collections.abc import Callable
from ctypes import wintypes

SERVICE_NAME = "HomePrepServer"
SERVICE_DISPLAY_NAME = "HomePrep Server"

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
