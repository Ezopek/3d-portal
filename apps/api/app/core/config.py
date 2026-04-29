from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "3d-portal-api"
    app_version: str = "0.1.0"
    environment: str = Field(default="dev")  # "dev" | "production"

    # Volumes (paths inside container)
    catalog_data_dir: Path = Path("/data/catalog")
    renders_dir: Path = Path("/data/renders")
    state_dir: Path = Path("/data/state")

    # DB
    database_url: str = "sqlite:////data/state/portal.db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 30
    admin_email: str = "admin@local"
    admin_password: str = "change-me"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None  # e.g. "authorization=Bearer <token>"

    @property
    def sqlite_path(self) -> Path | None:
        # SQLite URLs use 3 slashes for relative paths (sqlite:///portal.db -> portal.db)
        # and 4 for absolute (sqlite:////data/state/portal.db -> /data/state/portal.db).
        # Stripping a 3-slash prefix preserves the leading `/` of absolute paths.
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.removeprefix("sqlite:///"))
        return None

    @model_validator(mode="after")
    def _block_default_secrets_in_prod(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret == "change-me-in-production":
                raise ValueError(
                    "jwt_secret must be set to a real value in production; "
                    "the default placeholder is not allowed."
                )
            if self.admin_password == "change-me":
                raise ValueError(
                    "admin_password must be set to a real value in production; "
                    "the default placeholder is not allowed."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
