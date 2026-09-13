from homeprep_server.standalone_config import (
    DEFAULT_BACKUP_RETENTION,
    DEFAULT_BACKUP_SCHEDULE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_standalone_config,
    save_standalone_config,
)


def test_standalone_config_defaults(tmp_path) -> None:
    assert load_standalone_config(tmp_path) == {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "backup_schedule": DEFAULT_BACKUP_SCHEDULE,
        "backup_retention": DEFAULT_BACKUP_RETENTION,
    }


def test_standalone_config_round_trip(tmp_path) -> None:
    path = save_standalone_config(
        "0.0.0.0",
        9090,
        tmp_path,
        backup_schedule="daily",
        backup_retention=21,
    )
    assert path.exists()
    assert load_standalone_config(tmp_path) == {
        "host": "0.0.0.0",
        "port": 9090,
        "backup_schedule": "daily",
        "backup_retention": 21,
    }


def test_standalone_config_rejects_invalid_port(tmp_path) -> None:
    try:
        save_standalone_config("127.0.0.1", 70000, tmp_path)
    except ValueError as exc:
        assert "Port" in str(exc)
    else:
        raise AssertionError("Expected invalid port to be rejected")


def test_standalone_config_rejects_invalid_backup_settings(tmp_path) -> None:
    try:
        save_standalone_config(
            "127.0.0.1",
            8080,
            tmp_path,
            backup_schedule="hourly",
        )
    except ValueError as exc:
        assert "Backup schedule" in str(exc)
    else:
        raise AssertionError("Expected invalid backup schedule to be rejected")
