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
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
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
        # Swap the lifespan-created factory for the fakeredis one.
        app.state.redis = factory
        token = encode_token(subject="1", role="admin", secret="test", ttl_minutes=30)
        yield c, token
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_create_share_requires_admin(client):
    c, _ = client
    r = c.post("/api/admin/share", json={"model_id": "001", "expires_in_hours": 24})
    assert r.status_code == 401


def test_create_share_returns_token_and_url(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post(
        "/api/admin/share", json={"model_id": "001", "expires_in_hours": 24}, headers=headers
    )
    assert r.status_code == 201
    body = r.json()
    assert body["url"].startswith("/share/")
    assert body["token"]


def test_list_share_returns_active_tokens(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    c.post("/api/admin/share", json={"model_id": "001", "expires_in_hours": 24}, headers=headers)
    c.post("/api/admin/share", json={"model_id": "002", "expires_in_hours": 24}, headers=headers)
    r = c.get("/api/admin/share", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["tokens"]) == 2


def test_revoke_share_removes_it(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    created = c.post(
        "/api/admin/share", json={"model_id": "001", "expires_in_hours": 1}, headers=headers
    ).json()
    r = c.delete(f"/api/admin/share/{created['token']}", headers=headers)
    assert r.status_code == 204
    after = c.get("/api/admin/share", headers=headers).json()
    assert all(t["token"] != created["token"] for t in after["tokens"])


def test_create_for_unknown_model_returns_404(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/admin/share", json={"model_id": "999", "expires_in_hours": 1}, headers=headers)
    assert r.status_code == 404
