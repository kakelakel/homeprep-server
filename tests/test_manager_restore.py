from pathlib import Path

from homeprep_server import manager_entry


def test_restore_restarts_service_after_restore_failure(monkeypatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        manager_entry.manager,
        "_restore_invocation",
        lambda archive: f"RESTORE {archive}",
    )

    def fake_run(script: str) -> int:
        captured["script"] = script
        return 10

    monkeypatch.setattr(manager_entry.manager, "_run_elevated_powershell_code", fake_run)

    result = manager_entry.restore_local_backup(Path("backup.zip"), restart_service=True)

    assert result == "restore_failed"
    script = captured["script"]
    assert "Stop-Service" in script
    assert "RESTORE backup.zip" in script
    assert "$restoreExit=$LASTEXITCODE" in script
    assert "Start-Service" in script
    assert script.index("Start-Service") < script.index("if ($restoreExit -ne 0)")


def test_restore_reports_restart_failure(monkeypatch) -> None:
    monkeypatch.setattr(manager_entry.manager, "_restore_invocation", lambda archive: "RESTORE")
    monkeypatch.setattr(manager_entry.manager, "_run_elevated_powershell_code", lambda script: 20)

    result = manager_entry.restore_local_backup(Path("backup.zip"), restart_service=True)

    assert result == "restart_failed"


def test_restore_without_running_service_does_not_touch_service(monkeypatch) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(manager_entry.manager, "_restore_invocation", lambda archive: "RESTORE")

    def fake_run(script: str) -> int:
        captured["script"] = script
        return 0

    monkeypatch.setattr(manager_entry.manager, "_run_elevated_powershell_code", fake_run)

    result = manager_entry.restore_local_backup(Path("backup.zip"), restart_service=False)

    assert result == "success"
    assert "Stop-Service" not in captured["script"]
    assert "Start-Service" not in captured["script"]
