from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from homeprep_server.core.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""
    global _engine
    if _engine is None:
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
        connect_args = (
            {"check_same_thread": False}
            if settings.resolved_database_url.startswith("sqlite")
            else {}
        )
        _engine = create_engine(
            settings.resolved_database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    return _engine


def database_is_ready() -> bool:
    """Verify that the configured database can execute a trivial query."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
