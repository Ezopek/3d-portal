"""Test-only helpers. Do not import outside tests."""
from pathlib import Path

from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.catalog.service import CatalogService


def override_catalog_paths(app: FastAPI, *, index_path: Path) -> None:
    """Replace the catalog service with one pointing at a custom index.

    Call this AFTER entering the TestClient context manager — the lifespan
    must run first so that we then overwrite the service it created.
    Reads `catalog_data_dir` from settings (env-driven in tests) so it does
    not depend on prior `app.state` content.
    """
    settings = get_settings()
    app.state.catalog_service = CatalogService(
        catalog_dir=settings.catalog_data_dir,
        index_path=index_path,
    )
