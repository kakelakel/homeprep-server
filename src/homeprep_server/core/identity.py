from pathlib import Path
from uuid import UUID, uuid4

from homeprep_server.core.config import settings

SERVER_ID_FILENAME = "server-id"


def get_server_id() -> UUID:
    """Return the stable identity of this HomePrep Server data directory."""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    identity_path = data_dir / SERVER_ID_FILENAME

    if identity_path.exists():
        return UUID(identity_path.read_text(encoding="utf-8").strip())

    server_id = uuid4()
    identity_path.write_text(f"{server_id}\n", encoding="utf-8")
    return server_id
