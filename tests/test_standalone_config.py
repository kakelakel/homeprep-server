from homeprep_server.standalone_config import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    load_standalone_config,
    save_standalone_config,
)


def test_standalone_config_defaults(tmp_path) -> None:
    assert load_standalone_config(tmp_path) == {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
    }


def test_standalone_config_round_trip(tmp_path) -> None:
    path = save_standalone_config("0.0.0.0", 9090, tmp_path)
    assert path.exists()
    assert load_standalone_config(tmp_path) == {"host": "0.0.0.0", "port": 9090}


def test_standalone_config_rejects_invalid_port(tmp_path) -> None:
    try:
        save_standalone_config("127.0.0.1", 70000, tmp_path)
    except ValueError as exc:
        assert "Port" in str(exc)
    else:
        raise AssertionError("Expected invalid port to be rejected")
