from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class RenderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    catalog_data_dir: Path = Path("/data/catalog")
    renders_dir: Path = Path("/data/renders")
    redis_url: str = "redis://redis:6379/0"
    image_size: int = 768
    service_name: str = "3d-portal-worker"
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_headers: str | None = None


@lru_cache
def get_settings() -> RenderSettings:
    return RenderSettings()
