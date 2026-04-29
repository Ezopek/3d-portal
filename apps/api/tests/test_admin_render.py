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

    # Use a shared FakeServer so that the sync seed client and the async
    # endpoint client share the same in-memory state without event-loop conflicts.
    fake_server = fakeredis.FakeServer()
    fake_sync = fakeredis.FakeStrictRedis(server=fake_server)
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
        yield c, token, fake_sync, arq_pool
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_render_requires_admin(client):
    c, *_ = client
    r = c.post("/api/admin/render/001")
    assert r.status_code == 401


def test_render_enqueues_job_and_returns_id(client):
    c, token, _fake, arq = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/admin/render/001", headers=headers)
    assert r.status_code == 202
    assert r.json()["job_id"] == "job-001"
    arq.enqueue_job.assert_awaited_once_with("render_model", "001")


def test_render_unknown_model_404(client):
    c, token, *_ = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/admin/render/999", headers=headers)
    assert r.status_code == 404


def test_status_returns_running_when_set(client):
    c, token, fake_sync, _ = client
    # fake_sync is a sync FakeStrictRedis sharing the same FakeServer as the async client
    fake_sync.set("render:status:001", b"running", ex=60)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/admin/jobs/001", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_status_returns_unknown_when_absent(client):
    c, token, *_ = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/admin/jobs/999", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "unknown"
