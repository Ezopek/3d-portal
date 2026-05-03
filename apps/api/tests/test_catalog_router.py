from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/c.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_list_models_returns_all(client):
    r = client.get("/api/catalog/models")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["models"]) == 3


def test_get_model_returns_detail(client):
    r = client.get("/api/catalog/models/002")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "002"
    assert body["name_pl"] == "Wazon"


def test_get_model_404_for_missing(client):
    r = client.get("/api/catalog/models/999")
    assert r.status_code == 404


def test_list_files_for_model(client):
    r = client.get("/api/catalog/models/002/files")
    assert r.status_code == 200
    files = r.json()["files"]
    assert "Vase.stl" in files


def test_get_model_returns_thumbnail_url(client):
    resp = client.get("/api/catalog/models/001")
    assert resp.status_code == 200
    body = resp.json()
    # Same chain logic as the list — Dragon has images/Dragon.png.
    assert body["thumbnail_url"] == "/api/files/001/images/Dragon.png"


def test_list_files_default_kind_is_all(client):
    """Backward compat: default response includes non-STL files (README, images)."""
    r = client.get("/api/catalog/models/002/files")
    assert r.status_code == 200
    files = r.json()["files"]
    assert "Vase.stl" in files
    assert "README.txt" in files


def test_list_files_printable_returns_only_stl(client):
    r = client.get("/api/catalog/models/002/files?kind=printable")
    assert r.status_code == 200
    files = r.json()["files"]
    assert all(f.lower().endswith(".stl") for f in files)
    assert "README.txt" not in files
    assert "Vase.stl" in files


def test_list_files_printable_is_case_insensitive(client):
    r = client.get("/api/catalog/models/002/files?kind=printable")
    files = r.json()["files"]
    # files/Upper.STL has uppercase extension — must appear in printable list.
    assert "files/Upper.STL" in files
