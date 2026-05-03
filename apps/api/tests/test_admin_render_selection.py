from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.core.auth.jwt import encode_token
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()

    fake_server = fakeredis.FakeServer()
    fake_async = fakeredis.aioredis.FakeRedis(server=fake_server)
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake_async)

    async def _aclose():
        return None

    factory.aclose = _aclose

    arq_pool = MagicMock()
    arq_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job-001"))

    async def _arq_close():
        return None

    arq_pool.aclose = _arq_close

    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        app.state.redis = factory
        app.state.arq = arq_pool
        token = encode_token(subject="1", role="admin", secret="test", ttl_minutes=30)
        yield c, token, arq_pool
    get_settings.cache_clear()
    get_engine.cache_clear()


def _hdrs(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_requires_admin(client):
    c, *_ = client
    r = c.get("/api/admin/models/001/render-selection")
    assert r.status_code == 401


def test_get_403_for_non_admin(client):
    c, *_ = client
    user_token = encode_token(subject="42", role="user", secret="test", ttl_minutes=30)
    r = c.get("/api/admin/models/001/render-selection", headers=_hdrs(user_token))
    assert r.status_code == 403


def test_get_404_for_unknown_model(client):
    c, token, _ = client
    r = c.get("/api/admin/models/999/render-selection", headers=_hdrs(token))
    assert r.status_code == 404


def test_get_returns_empty_paths_and_available_stls(client):
    c, token, _ = client
    r = c.get("/api/admin/models/001/render-selection", headers=_hdrs(token))
    assert r.status_code == 200
    body = r.json()
    assert body["paths"] == []
    assert isinstance(body["available_stls"], list)
    assert all(p.lower().endswith(".stl") for p in body["available_stls"])
    assert "Dragon.stl" in body["available_stls"]
