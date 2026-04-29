from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
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


def test_download_stl(client):
    r = client.get("/api/files/001/Dragon.stl")
    assert r.status_code == 200
    assert "ETag" in r.headers


def test_etag_round_trip_returns_304(client):
    r1 = client.get("/api/files/001/Dragon.stl")
    etag = r1.headers["ETag"]
    r2 = client.get("/api/files/001/Dragon.stl", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_path_traversal_rejected(client):
    r = client.get("/api/files/001/..%2F..%2Fetc/passwd")
    assert r.status_code in {400, 404}


def test_unknown_model_returns_404(client):
    r = client.get("/api/files/999/anything")
    assert r.status_code == 404
