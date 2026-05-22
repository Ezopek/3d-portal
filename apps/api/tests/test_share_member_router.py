"""Tests for /api/me/share-links — Initiative 10 Story 16.3.

Member-scoped list + revoke of own share tokens. Mirrors the admin
endpoints' behavior with strict ownership filter (created_by == current
user only).
"""

import uuid

import bcrypt
import pytest
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import encode_token
from app.core.db.models import Category, Model, User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine


@pytest.fixture
def client(isolated_client):
    """Initiative 10 Story 16.3 — share tests need a fakeredis swap so the
    Redis-backed ShareService doesn't try to reach a real Redis. Delegate to
    conftest.isolated_client; ignore the FakeRedis second element since we
    interact via the HTTP layer only."""
    c, _ = isolated_client
    yield c


def _seed_user(session: Session, *, email: str, role: UserRole = UserRole.member) -> uuid.UUID:
    pwd_hash = bcrypt.hashpw(b"pw", bcrypt.gensalt(rounds=4)).decode()
    u = User(email=email, display_name=email.split("@")[0], role=role, password_hash=pwd_hash)
    session.add(u)
    session.commit()
    session.refresh(u)
    return u.id


def _token(user_id: uuid.UUID, role: str = "member") -> str:
    return encode_token(
        subject=str(user_id),
        role=role,
        secret="test-secret-not-real",
        ttl_minutes=30,
    )


def _seed_model(session, slug: str = "share-me") -> uuid.UUID:
    cat = Category(slug=f"cat-share-me-{slug}", name_en="X")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    m = Model(slug=slug, name_en=slug, category_id=cat.id)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m.id


@pytest.fixture
def seed_two_users_and_model():
    with Session(get_engine()) as s:
        # Reuse admin if already present (idempotent across tests within session).
        admin_email = "admin@localhost.localdomain"
        admin = s.exec(select(User).where(User.email == admin_email)).first()
        if admin is None:
            user_a_id = _seed_user(s, email=admin_email, role=UserRole.admin)
        else:
            user_a_id = admin.id
        user_b_id = _seed_user(s, email=f"u-{uuid.uuid4().hex[:6]}@test.local", role=UserRole.member)
        mid = _seed_model(s, slug=f"sm-{uuid.uuid4().hex[:6]}")
    return user_a_id, user_b_id, mid


def test_my_share_links_lists_only_my_tokens(client, seed_two_users_and_model):
    user_a, user_b, model_id = seed_two_users_and_model

    # User A creates a share token.
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    assert r.status_code == 201, r.text
    token_a = r.json()["token"]

    # User B creates a different share token.
    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    assert r.status_code == 201
    token_b = r.json()["token"]

    # User A lists — should see ONLY their own token.
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.get("/api/me/share-links")
    assert r.status_code == 200
    tokens = r.json()["tokens"]
    assert len(tokens) == 1
    assert tokens[0]["token"] == token_a
    assert tokens[0]["created_by"] == str(user_a)
    assert token_b not in {t["token"] for t in tokens}


def test_my_share_links_revoke_own_token(client, seed_two_users_and_model):
    user_a, _user_b, model_id = seed_two_users_and_model

    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    r = client.delete(f"/api/me/share-links/{token}")
    assert r.status_code == 204

    # Listing now empty.
    r = client.get("/api/me/share-links")
    assert r.status_code == 200
    assert r.json()["tokens"] == []


def test_my_share_links_revoke_other_users_token_returns_403(client, seed_two_users_and_model):
    user_a, user_b, model_id = seed_two_users_and_model

    # User A creates a token.
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token_a = r.json()["token"]

    # User B tries to revoke User A's token.
    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.delete(f"/api/me/share-links/{token_a}")
    assert r.status_code == 403

    # Token still active.
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.get("/api/me/share-links")
    assert len(r.json()["tokens"]) == 1


def test_my_share_links_revoke_unknown_token_returns_404(client, seed_two_users_and_model):
    user_a, _user_b, _mid = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.delete(f"/api/me/share-links/{uuid.uuid4().hex}")
    assert r.status_code == 404


def test_my_share_links_requires_authentication(client):
    """Initiative 6 default-deny — anonymous request gets 401."""
    client.cookies.delete(ACCESS_COOKIE)
    r = client.get("/api/me/share-links")
    assert r.status_code == 401


def test_create_share_ttl_capped_at_7_days(client, seed_two_users_and_model):
    """Initiative 10 Story 16.3 — hard-cap TTL at 7 days (168 hours)."""
    user_a, _user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))

    # 168h is the max allowed.
    r = client.post(
        "/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 168}
    )
    assert r.status_code == 201

    # 169h+ rejected by Pydantic constraint.
    r = client.post(
        "/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 169}
    )
    assert r.status_code == 422
