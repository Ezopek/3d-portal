from pathlib import Path
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.auth.jwt import encode_token
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/p.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis()
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose

    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        app.state.redis = factory
        token = encode_token(subject="1", role="admin", secret="test", ttl_minutes=30)
        yield c, token
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_resolve_unknown_token_returns_404(client):
    c, _ = client
    r = c.get("/api/share/nope")
    assert r.status_code == 404


def test_resolve_returns_subset_projection(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    created = c.post(
        "/api/admin/share",
        json={"model_id": "002", "expires_in_hours": 1},
        headers=headers,
    ).json()
    r = c.get(f"/api/share/{created['token']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "002"
    assert body["name_pl"] == "Wazon"
    assert "rating" not in body  # subset, not full Model
    assert "source_url" not in body
    assert isinstance(body["images"], list)


def test_resolve_returns_stl_url_when_stl_present(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    created = c.post(
        "/api/admin/share",
        json={"model_id": "001", "expires_in_hours": 1},
        headers=headers,
    ).json()
    body = c.get(f"/api/share/{created['token']}").json()
    assert body["stl_url"] == "/api/files/001/Dragon.stl"
