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
        user_b_id = _seed_user(
            s, email=f"u-{uuid.uuid4().hex[:6]}@test.local", role=UserRole.member
        )
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
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 168})
    assert r.status_code == 201

    # 169h+ rejected by Pydantic constraint.
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 169})
    assert r.status_code == 422


# ─── Initiative 18 Story 30.1 — share-resolve endpoint coverage ───
# AC-1..AC-11 (resolve_my_share_link). Reuses existing `client` +
# `seed_two_users_and_model` fixtures. No new fixtures introduced.

_INVALID_404_BODY = '{"detail":"Share token not found or expired"}'


def test_resolve_my_share_link_happy_path_returns_200_with_model_id(
    client, seed_two_users_and_model
):
    """RESOLVE-1: AC-1 + AC-2 + AC-11.

    user_a (admin) creates a token; user_b (member) resolves it; gets 200
    with EXACTLY {model_id, access} keys (AC-11 enumeration-protection).
    """
    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    assert r.status_code == 201, r.text
    token = r.json()["token"]

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"model_id", "access"}, (
        f"AC-11 enumeration-protection: extra keys leak token-state. body={body}"
    )
    assert body["model_id"] == str(model_id)
    assert body["access"] == "granted"


def test_resolve_my_share_link_requires_authentication(client, seed_two_users_and_model):
    """RESOLVE-2: AC-3 — anonymous gets 401."""
    user_a, _user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    client.cookies.delete(ACCESS_COOKIE)
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 401
    assert r.json()["detail"] in {"missing_access", "access_expired", "invalid_access"}


def test_resolve_my_share_link_invalid_token_returns_uniform_404(client, seed_two_users_and_model):
    """RESOLVE-3: AC-4 — random-string token returns canonical 404."""
    user_a, _user_b, _mid = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.get(f"/api/me/share-links/{uuid.uuid4().hex}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_resolve_my_share_link_expired_token_uniform_404(isolated_client, seed_two_users_and_model):
    """RESOLVE-4: AC-4 — Redis TTL elapse returns byte-identical 404 to RESOLVE-3."""
    c, fake = isolated_client
    user_a, user_b, model_id = seed_two_users_and_model
    c.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = c.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    # Simulate Redis TTL elapse: delete the share-token key directly via
    # the fakeredis instance bound to app.state.redis. Use c.portal.call
    # to bridge sync→async (same pattern as test_admin_password_reset_mint).
    async def _delete():
        await fake.delete(f"share:token:{token}")

    c.portal.call(_delete)

    c.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = c.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY  # byte-identical AC-4 enforcement


def test_resolve_my_share_link_revoked_token_uniform_404(client, seed_two_users_and_model):
    """RESOLVE-5: AC-4 — explicitly revoked token returns byte-identical 404."""
    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    r = client.delete(f"/api/me/share-links/{token}")
    assert r.status_code == 204

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_resolve_my_share_link_soft_deleted_model_uniform_404(client, seed_two_users_and_model):
    """RESOLVE-6: AC-5 — soft-deleted model returns byte-identical 404."""
    from datetime import UTC, datetime

    from app.core.db.models import Model

    user_a, user_b, model_id = seed_two_users_and_model
    client.cookies.set(ACCESS_COOKIE, _token(user_a, "admin"))
    r = client.post("/api/admin/share", json={"model_id": str(model_id), "expires_in_hours": 24})
    token = r.json()["token"]

    with Session(get_engine()) as s:
        m = s.exec(select(Model).where(Model.id == model_id)).one()
        m.deleted_at = datetime.now(UTC)
        s.add(m)
        s.commit()

    client.cookies.set(ACCESS_COOKIE, _token(user_b))
    r = client.get(f"/api/me/share-links/{token}/resolve")
    assert r.status_code == 404
    assert r.text == _INVALID_404_BODY


def test_share_public_router_carries_no_auth_depends_after_init_18():
    """CONTRACT-1: AC-6 NFR10 grep invariant.

    The public /api/share/<token>/* family MUST stay credentialless.
    Pattern-matches the two code-meaningful shapes for an auth Depends:

      1. ``= current_user`` / ``= current_admin`` / ... (handler signature
         default-arg pattern, e.g. ``_user_id: uuid.UUID = current_admin``)
      2. ``Depends(current_user)`` / ``Depends(_current_user_dep)`` / ...
         (explicit Depends wrap with the dep callable name)

    Comments mentioning ``current_user`` historically (e.g. Init 6
    Decision N rationale at line ~184 of router.py) are NOT violations —
    code-level introspection only. Story 30.1's authenticated branch
    lives in member_router.py under /api/me/share-links per Decision AA.
    """
    import inspect
    import re

    from app.modules.share import router as share_router

    src = inspect.getsource(share_router)
    # Strip line comments to ignore rationale references like the Init 6
    # Decision N comment block — they explain the contract, they don't
    # violate it.
    src_no_comments = "\n".join(line.split("#", 1)[0] for line in src.splitlines())

    forbidden_names = (
        "current_user",
        "current_admin",
        "current_member_or_admin",
        "current_admin_or_agent",
    )
    patterns: list[str] = []
    for name in forbidden_names:
        # Assignment-style: ``= <name>`` at the end of a parameter declaration.
        patterns.append(rf"=\s*{re.escape(name)}\b")
        # Explicit Depends wrap; ``_?`` allows ``Depends(_current_user_dep)``
        # in addition to the typical ``Depends(current_user)`` shape.
        patterns.append(rf"Depends\(\s*_?{re.escape(name)}_?")

    hits: list[str] = [pat for pat in patterns if re.search(pat, src_no_comments)]

    assert hits == [], (
        "NFR18-SHARE-ANON-CONTRACT-1 violated: apps/api/app/modules/share/router.py "
        f"contains auth-dep code patterns {hits}. Move auth-required endpoints "
        "to member_router.py (Decision AA) — see Story 30.1 spec."
    )
