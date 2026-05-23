"""Story 8.1 — backend tests for LastActiveMiddleware throttle invariant.

Covers AC-4 verbatim. 6 named tests T1-T6 — the names are binding cross-
references for the dev-story task list.

Pattern: per-test isolated DB + fakeredis via the new conftest fixture
``isolated_client`` (the promoted Story 8.1 fixture per AC-7). SQL
statement capture for the throttle invariant uses SQLAlchemy
``before_cursor_execute`` event listener attached at test scope and
removed via finalizer.
"""

from __future__ import annotations

import logging
import uuid
from unittest.mock import MagicMock

import pytest
import redis.exceptions
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.config import get_settings
from app.core.db.models import User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine

# Use the currently-effective settings.jwt_secret rather than a hardcoded
# value. Other tests in the suite call monkeypatch.setenv("JWT_SECRET", ...)
# but do not clear the LRU cache on get_settings(), so a hardcoded constant
# here can disagree with whichever secret the middleware actually decodes
# against in full-suite context (TB-021 Failure A: cross-file pollution).

_UPDATE_LAST_ACTIVE_RE = "UPDATE user SET last_active_at"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_user(role: UserRole = UserRole.member, email_prefix: str = "u") -> User:
    """Commit a fresh user row to the per-test DB and return it (refreshed)."""
    engine = get_engine()
    with Session(engine) as s:
        u = User(
            email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@test.local",
            display_name=email_prefix,
            role=role,
            password_hash="x",
        )
        s.add(u)
        s.commit()
        s.refresh(u)
    # Guard the AC-4 fixture assertion: the user row MUST be visible to
    # the throttle's UPDATE statement before the request runs.
    with Session(engine) as s:
        seen = s.exec(select(User).where(User.id == u.id)).first()
        assert seen is not None, "seeded user row must be committed pre-request"
    return u


def _login_as(c: TestClient, user: User) -> None:
    token = encode_token(
        subject=str(user.id),
        role=user.role.value,
        secret=get_settings().jwt_secret,
        ttl_minutes=30,
    )
    c.cookies.set("portal_access", token, path="/api")


def _user_last_active(user_id: uuid.UUID):
    engine = get_engine()
    with Session(engine) as s:
        u = s.exec(select(User).where(User.id == user_id)).first()
        return u.last_active_at if u is not None else None


def _redis_get(c: TestClient, fake, key: str):
    async def _do():
        return await fake.get(key)

    return c.portal.call(_do)


def _redis_ttl(c: TestClient, fake, key: str):
    async def _do():
        return await fake.ttl(key)

    return c.portal.call(_do)


def _redis_delete(c: TestClient, fake, key: str):
    async def _do():
        return await fake.delete(key)

    return c.portal.call(_do)


def _redis_keys(c: TestClient, fake, pattern: str):
    async def _do():
        return await fake.keys(pattern)

    return c.portal.call(_do)


class _UpdateCounter:
    """SQLAlchemy event listener that counts UPDATE last_active_at calls.

    Registered at test scope on the per-test engine; removed via the
    pytest fixture teardown. The match is a substring check on the SQL
    text emitted by ``before_cursor_execute`` — robust to whitespace and
    parameter binding differences across SQLAlchemy versions.
    """

    def __init__(self) -> None:
        self.count = 0
        self._engine = get_engine()
        self._handler = self._on_execute
        sa.event.listen(self._engine, "before_cursor_execute", self._handler)

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany) -> None:
        if _UPDATE_LAST_ACTIVE_RE in statement:
            self.count += 1

    def remove(self) -> None:
        sa.event.remove(self._engine, "before_cursor_execute", self._handler)


@pytest.fixture
def counter(isolated_client):
    """SQL update counter scoped to the per-test isolated engine."""
    c = _UpdateCounter()
    yield c
    c.remove()


# ---------------------------------------------------------------------------
# T1 — authenticated request writes last_active on first hit
# ---------------------------------------------------------------------------


def test_authenticated_request_writes_last_active_on_first_hit(isolated_client, counter):
    c, fake = isolated_client
    user = _seed_user(role=UserRole.member)
    _login_as(c, user)

    r = c.get("/api/auth/me")
    assert r.status_code == 200, r.text

    last_active = _user_last_active(user.id)
    assert last_active is not None, "last_active_at should be populated"

    redis_key = f"last_active:{user.id}"
    stored = _redis_get(c, fake, redis_key)
    assert stored is not None, "Redis throttle key should be present"
    ttl = _redis_ttl(c, fake, redis_key)
    assert 0 < ttl <= 300, f"TTL should be ≤ 300s, got {ttl}"
    assert counter.count == 1


# ---------------------------------------------------------------------------
# T2 — throttle skips DB write within window
# ---------------------------------------------------------------------------


def test_throttle_skips_db_write_within_window(isolated_client, counter):
    c, _fake = isolated_client
    user = _seed_user(role=UserRole.member)
    _login_as(c, user)

    for _ in range(50):
        r = c.get("/api/auth/me")
        assert r.status_code == 200

    assert counter.count == 1, f"expected EXACTLY 1 UPDATE in throttle window, got {counter.count}"


# ---------------------------------------------------------------------------
# T3 — second write allowed after TTL expiry
# ---------------------------------------------------------------------------


def test_throttle_allows_second_write_after_ttl_expiry(isolated_client, counter):
    c, fake = isolated_client
    user = _seed_user(role=UserRole.member)
    _login_as(c, user)

    for _ in range(10):
        r = c.get("/api/auth/me")
        assert r.status_code == 200
    assert counter.count == 1

    # Simulate TTL expiry by dropping the Redis throttle key directly.
    # fakeredis honors real time and waiting 300s in CI is not viable;
    # deleting the key is functionally equivalent to the SET NX EX 300
    # window having elapsed (the SET NX check is per-key existence,
    # not wall-clock based on the producer side).
    redis_key = f"last_active:{user.id}"
    deleted = _redis_delete(c, fake, redis_key)
    assert deleted == 1

    for _ in range(10):
        r = c.get("/api/auth/me")
        assert r.status_code == 200
    assert counter.count == 2, (
        f"expected EXACTLY 2 UPDATEs across both batches, got {counter.count}"
    )


# ---------------------------------------------------------------------------
# T4 — anonymous requests produce no update
# ---------------------------------------------------------------------------


def test_anonymous_requests_produce_no_update(isolated_client, counter):
    c, fake = isolated_client
    # No cookie set; the /me endpoint will return 401, but the middleware
    # still wraps the request; the assertion is that the throttle does NOT
    # fire on the anonymous path.
    for _ in range(20):
        r = c.get("/api/auth/me")
        assert r.status_code == 401

    assert counter.count == 0
    keys = _redis_keys(c, fake, "last_active:*")
    assert keys == [], f"no Redis last_active keys expected, got {keys}"


# ---------------------------------------------------------------------------
# T5 — agent role produces no update
# ---------------------------------------------------------------------------


def test_agent_role_produces_no_update(isolated_client, counter):
    c, fake = isolated_client
    user = _seed_user(role=UserRole.agent, email_prefix="agent")
    _login_as(c, user)

    # /me requires the user to exist; the agent IS seeded, so this should
    # succeed at the handler level. The throttle MUST be a no-op anyway.
    for _ in range(10):
        r = c.get("/api/auth/me")
        assert r.status_code == 200

    assert counter.count == 0
    keys = _redis_keys(c, fake, f"last_active:{user.id}")
    assert keys == [], f"agent role must not register a Redis key, got {keys}"
    last_active = _user_last_active(user.id)
    assert last_active is None


# ---------------------------------------------------------------------------
# T6 — Redis-down passes through with warning
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_client_redis_down(isolated_client):
    """Variant: Redis client's .set() raises ConnectionError.

    Yields the patched client + restores the original redis factory in
    teardown so subsequent tests (which share the TestClient via the
    isolated_client base fixture chain) don't inherit the broken
    Redis stub — that was causing full-suite hangs when ratelimit /
    share / 2FA tests ran after this one.
    """
    c, _real_fake = isolated_client
    broken = MagicMock()

    async def _set(*args, **kwargs):
        raise redis.exceptions.ConnectionError("simulated outage")

    broken.set = _set
    original_get = c.app.state.redis.get
    c.app.state.redis.get = MagicMock(return_value=broken)
    try:
        yield c
    finally:
        c.app.state.redis.get = original_get


class _ListHandler(logging.Handler):
    """Capture records on a named logger without going through root.

    pytest's built-in caplog attaches to root, but
    ``app.core.logging.configure_logging`` does ``root.handlers[:] = ...``
    during FastAPI lifespan startup, removing pytest's handler. Attaching a
    dedicated handler to ``app.auth.last_active`` sidesteps the wipe.
    Mirrors the share_caplog / auth_ratelimit_caplog pattern from
    test_ratelimit_share_cap.py. Closes TB-021 Failure A.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def last_active_caplog():
    logger = logging.getLogger("app.auth.last_active")
    prev_level = logger.level
    prev_disabled = logger.disabled
    handler = _ListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.disabled = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)
        logger.disabled = prev_disabled


def test_redis_down_passes_through_with_warning(
    isolated_client_redis_down, counter, last_active_caplog
):
    c = isolated_client_redis_down
    user = _seed_user(role=UserRole.member)
    _login_as(c, user)

    r = c.get("/api/auth/me")
    assert r.status_code == 200, r.text

    warnings = [
        rec
        for rec in last_active_caplog.records
        if rec.name == "app.auth.last_active"
        and getattr(rec, "event.action", None) == "last_active.redis_unavailable"
    ]
    assert len(warnings) == 1, (
        f"expected exactly one redis_unavailable warning, got {len(warnings)}"
    )
    assert counter.count == 0
    last_active = _user_last_active(user.id)
    assert last_active is None
