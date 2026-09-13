from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for HomePrep Server."""

    model_config = SettingsConfigDict(
        env_prefix="HOMEPREP_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "HomePrep Server"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    data_dir: Path = Path("/data")
    web_dir: Path = Path("web/dist")
    database_url: str | None = None

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        database_path = self.data_dir / "homeprep.db"
        return f"sqlite:///{database_path}"


settings = Settings()
