from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RenderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    catalog_data_dir: Path = Path("/data/catalog")
    renders_dir: Path = Path("/data/renders")
    database_url: str = "sqlite:////data/state/portal.db"
    content_dir: Path = Path("/data/content")
    redis_url: str = "redis://redis:6379/0"
    image_size: int = 768
    service_name: str = "3d-portal-worker"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None
    sentry_dsn: str | None = None
    portal_version: str = "0.1.0"
    environment: str = "production"


@lru_cache
def get_settings() -> RenderSettings:
    return RenderSettings()
