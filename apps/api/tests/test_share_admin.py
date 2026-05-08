import uuid
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.auth.jwt import encode_token
from app.core.db.models import Category, Model
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
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
        # Swap the lifespan-created factory for the fakeredis one.
        app.state.redis = factory
        # Retrieve the seeded admin user UUID for the token.
        from sqlmodel import select

        from app.core.db.models import User

        engine = get_engine()
        with Session(engine) as s:
            user = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            user_id = user.id
            cat = Category(slug=f"share-cat-{uuid.uuid4().hex[:6]}", name_en="Cat")
            s.add(cat)
            s.flush()
            m1 = Model(
                slug=f"share-m1-{uuid.uuid4().hex[:6]}",
                name_en="M1",
                category_id=cat.id,
            )
            m2 = Model(
                slug=f"share-m2-{uuid.uuid4().hex[:6]}",
                name_en="M2",
                category_id=cat.id,
            )
            s.add(m1)
            s.add(m2)
            s.commit()
            ids = (m1.id, m2.id)
        token = encode_token(subject=str(user_id), role="admin", secret="test", ttl_minutes=30)
        yield c, token, ids
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_create_share_requires_admin(client):
    c, _, (mid, _) = client
    r = c.post("/api/admin/share", json={"model_id": str(mid), "expires_in_hours": 24})
    assert r.status_code == 401


def test_create_share_returns_token_and_url(client):
    c, token, (mid, _) = client
    c.cookies.set("portal_access", token)
    r = c.post(
        "/api/admin/share",
        json={"model_id": str(mid), "expires_in_hours": 24},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["url"].startswith("/share/")
    assert body["token"]


def test_list_share_returns_active_tokens(client):
    c, token, (mid1, mid2) = client
    c.cookies.set("portal_access", token)
    c.post(
        "/api/admin/share",
        json={"model_id": str(mid1), "expires_in_hours": 24},
    )
    c.post(
        "/api/admin/share",
        json={"model_id": str(mid2), "expires_in_hours": 24},
    )
    r = c.get("/api/admin/share")
    assert r.status_code == 200
    assert len(r.json()["tokens"]) == 2


def test_revoke_share_removes_it(client):
    c, token, (mid, _) = client
    c.cookies.set("portal_access", token)
    created = c.post(
        "/api/admin/share",
        json={"model_id": str(mid), "expires_in_hours": 1},
    ).json()
    r = c.delete(f"/api/admin/share/{created['token']}")
    assert r.status_code == 204
    after = c.get("/api/admin/share").json()
    assert all(t["token"] != created["token"] for t in after["tokens"])


def test_create_for_unknown_model_returns_404(client):
    c, token, _ = client
    c.cookies.set("portal_access", token)
    r = c.post(
        "/api/admin/share",
        json={"model_id": str(uuid.uuid4()), "expires_in_hours": 1},
    )
    assert r.status_code == 404
