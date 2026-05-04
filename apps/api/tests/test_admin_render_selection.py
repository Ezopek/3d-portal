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

# A fixed UUID used for non-admin "wrong role" token tests (never looked up in DB).
_NON_ADMIN_UUID = "00000000-0000-0000-0000-000000000042"


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
        # Retrieve the seeded admin user UUID for token.
        from sqlmodel import Session, select

        from app.core.db.models import User

        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
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
    user_token = encode_token(subject=_NON_ADMIN_UUID, role="user", secret="test", ttl_minutes=30)
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


def test_put_requires_admin(client):
    c, *_ = client
    r = c.put("/api/admin/models/001/render-selection", json={"paths": []})
    assert r.status_code == 401


def test_put_403_for_non_admin(client):
    c, *_ = client
    user_token = encode_token(subject=_NON_ADMIN_UUID, role="user", secret="test", ttl_minutes=30)
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": []},
        headers=_hdrs(user_token),
    )
    assert r.status_code == 403


def test_put_404_for_unknown_model(client):
    c, token, _ = client
    r = c.put(
        "/api/admin/models/999/render-selection",
        json={"paths": []},
        headers=_hdrs(token),
    )
    assert r.status_code == 404


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escape.stl",
        "/etc/passwd.stl",
        "files/x.exe",
        "files//double.stl",
        ".hidden.stl",
        "files/.hidden.stl",
    ],
)
def test_put_400_for_invalid_path(client, bad_path):
    c, token, _ = client
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": [bad_path]},
        headers=_hdrs(token),
    )
    assert r.status_code == 400


def test_put_400_when_path_does_not_exist(client):
    c, token, _ = client
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": ["files/nonexistent.stl"]},
        headers=_hdrs(token),
    )
    assert r.status_code == 400


def test_put_400_when_more_than_16_paths(client):
    c, token, _ = client
    paths = [f"files/p{i}.stl" for i in range(17)]
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": paths},
        headers=_hdrs(token),
    )
    assert r.status_code == 400


def test_put_with_valid_paths_persists_and_enqueues(client):
    """Use Dragon.stl which exists in tests/fixtures/catalog/decorum/dragon/."""
    c, token, arq = client
    valid_paths = ["Dragon.stl"]
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": valid_paths},
        headers=_hdrs(token),
    )
    assert r.status_code == 204
    arq.enqueue_job.assert_awaited_once_with("render_model", "001", selected_paths=valid_paths)


def test_put_empty_paths_clears_and_enqueues_with_none(client):
    c, token, arq = client
    # Seed a non-empty state first so the empty PUT is a state change.
    c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": ["Dragon.stl"]},
        headers=_hdrs(token),
    )
    arq.enqueue_job.reset_mock()
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": []},
        headers=_hdrs(token),
    )
    assert r.status_code == 204
    arq.enqueue_job.assert_awaited_once_with("render_model", "001", selected_paths=None)


def test_put_identical_set_does_not_enqueue(client):
    c, token, arq = client
    valid_paths = ["Dragon.stl"]
    c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": valid_paths},
        headers=_hdrs(token),
    )
    arq.enqueue_job.reset_mock()
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": valid_paths},
        headers=_hdrs(token),
    )
    assert r.status_code == 204
    arq.enqueue_job.assert_not_awaited()


def test_put_empty_when_already_empty_is_noop(client):
    c, token, arq = client
    r = c.put(
        "/api/admin/models/001/render-selection",
        json={"paths": []},
        headers=_hdrs(token),
    )
    assert r.status_code == 204
    arq.enqueue_job.assert_not_awaited()
