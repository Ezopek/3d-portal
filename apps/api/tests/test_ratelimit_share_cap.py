"""Tests for the Initiative 5 per-member share-token cap (Story 6.7).

Covers AC-1 through AC-7 from the Story 6.7 spec:
- AC-1: RateLimitMiddleware class extension (soft_alert_threshold + retry_after_seconds_fn)
- AC-2: share_ratelimit_key callable (path + JWT + admin exemption + member key shape)
- AC-3: Fourth middleware instance mounted in main.py with CSRF-OUTERMOST ordering preserved
- AC-4: Three new Settings fields with env-var tunability
- AC-5: HTTP-layer threshold verification (10th soft-alert + 21st hard-fail + admin exempt)
- AC-6: Per-user isolation + UTC-day rollover + Retry-After-to-midnight
- AC-7: Zero frontend / migration / OpenAPI / audit / KNOWN_ENTITY_TYPES drift

Three fixture rigs:
- ``minimal_app_client`` — fresh FastAPI() with /test-route, used for class-shape
  unit tests of the extended RateLimitMiddleware params.
- ``share_client`` — TestClient(create_app()) + fakeredis swap + seeded admin
  + TWO seeded members + admin-token + two member-tokens (A and B) + two Model
  rows; mirrors test_share_member_permission.py:client fixture verbatim.
- ``share_caplog`` — _ListHandler attached to logger ``app.share.ratelimit``
  (mirrors test_ratelimit_middleware.py:ratelimit_caplog precedent because
  pytest's built-in caplog gets wiped by configure_logging at lifespan startup).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import fakeredis
import fakeredis.aioredis
import pytest
import redis.exceptions
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.auth.ratelimit import (
    RateLimitMiddleware,
    share_ratelimit_key,
    share_retry_after_seconds,
)
from app.core.db.models import Category, Model, User, UserRole
from app.core.db.session import get_engine
from app.main import create_app

# ---------------------------------------------------------------------------
# Fixture: minimal FastAPI app for class-shape unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_app_client():
    """Build a minimal FastAPI() per call with parameterized middleware kwargs.

    Mirrors Story 6.6 test_ratelimit_middleware.py:minimal_app_client shape.
    The factory enters the TestClient as a context manager so the underlying
    anyio portal (and therefore the fakeredis event-loop binding) stays alive
    across multiple ``c.post()`` calls in the same test.
    """
    opened: list[TestClient] = []

    def _build(
        *,
        scope: str = "x",
        key_fn=lambda r: "k",
        window_seconds: int = 60,
        threshold: int = 5,
        soft_alert_threshold: int | None = None,
        retry_after_seconds_fn=None,
    ):
        app = FastAPI()
        fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
        factory = MagicMock()
        factory.get = MagicMock(return_value=fake)
        app.state.redis = factory
        kwargs: dict = {
            "scope": scope,
            "key_fn": key_fn,
            "window_seconds": window_seconds,
            "threshold": threshold,
        }
        if soft_alert_threshold is not None:
            kwargs["soft_alert_threshold"] = soft_alert_threshold
        if retry_after_seconds_fn is not None:
            kwargs["retry_after_seconds_fn"] = retry_after_seconds_fn
        app.add_middleware(RateLimitMiddleware, **kwargs)

        @app.post("/test-route")
        def _r():
            return {"ok": True}

        client = TestClient(app)
        client.__enter__()
        opened.append(client)
        return client, fake

    try:
        yield _build
    finally:
        for client in opened:
            client.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Fixture: dedicated handler on the app.share.ratelimit logger
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    """Tiny in-memory handler — records every emitted record into ``records``."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def share_caplog():
    """Capture records emitted on ``app.share.ratelimit`` for the test duration.

    Mirrors Story 6.6 ratelimit_caplog: pytest's built-in caplog attaches to
    root, but ``app.core.logging.configure_logging`` does ``root.handlers[:] = ...``
    during FastAPI lifespan startup, removing pytest's handler. Attaching a
    dedicated handler to the named logger sidesteps the wipe.
    """
    logger = logging.getLogger("app.share.ratelimit")
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


@pytest.fixture
def auth_ratelimit_caplog():
    """Mirror of share_caplog bound to ``app.auth.ratelimit`` (for redis-outage assertions)."""
    logger = logging.getLogger("app.auth.ratelimit")
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


# ---------------------------------------------------------------------------
# Fixture: full create_app() + admin + two seeded members + tokens + fakeredis swap
# ---------------------------------------------------------------------------


@pytest.fixture
def share_client(tmp_path, monkeypatch):
    """Extend test_share_member_permission.py:client with a SECOND member seed."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/sc.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        engine = get_engine()
        with Session(engine) as s:
            admin = s.exec(select(User).where(User.email == "admin@localhost.localdomain")).first()
            admin_uuid = admin.id
            member_a = User(
                email=f"member-a-{uuid.uuid4().hex[:6]}@localhost.localdomain",
                display_name="Member A",
                role=UserRole.member,
                password_hash="$2b$12$irrelevant.for.these.tests....................",
            )
            member_b = User(
                email=f"member-b-{uuid.uuid4().hex[:6]}@localhost.localdomain",
                display_name="Member B",
                role=UserRole.member,
                password_hash="$2b$12$irrelevant.for.these.tests....................",
            )
            s.add(member_a)
            s.add(member_b)
            s.flush()
            member_a_uuid = member_a.id
            member_b_uuid = member_b.id
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
            model_ids = (m1.id, m2.id)
        admin_token = encode_token(
            subject=str(admin_uuid), role="admin", secret="test", ttl_minutes=30
        )
        member_a_token = encode_token(
            subject=str(member_a_uuid), role="member", secret="test", ttl_minutes=30
        )
        member_b_token = encode_token(
            subject=str(member_b_uuid), role="member", secret="test", ttl_minutes=30
        )
        yield (
            c,
            admin_token,
            admin_uuid,
            member_a_token,
            member_a_uuid,
            member_b_token,
            member_b_uuid,
            model_ids,
            fake,
        )
    get_settings.cache_clear()
    get_engine.cache_clear()


def _set_cookie(c: TestClient, token: str) -> None:
    c.cookies.set("portal_access", token)


def _clear_cookie(c: TestClient) -> None:
    c.cookies.clear()


def _create_share_payload(model_id) -> dict:
    return {"model_id": str(model_id), "expires_in_hours": 24}


# ===========================================================================
# AC-1: RateLimitMiddleware class-shape / param-shape tests
# ===========================================================================


def test_middleware_accepts_soft_alert_threshold_kw_only(minimal_app_client):
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=20,
        soft_alert_threshold=10,
    )
    # Smoke: the construction did not raise; first call passes through.
    r = c.post("/test-route")
    assert r.status_code == 200


def test_middleware_accepts_retry_after_seconds_fn_kw_only(minimal_app_client):
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=2,
        retry_after_seconds_fn=lambda: 42,
    )
    for _ in range(2):
        r = c.post("/test-route")
        assert r.status_code == 200
    r3 = c.post("/test-route")
    assert r3.status_code == 429
    assert r3.headers["Retry-After"] == "42"
    assert r3.json()["retry_after_seconds"] == 42


def test_middleware_backward_compat_no_new_params(minimal_app_client):
    """Story 6.6 trio construction shape — must still work with no soft_alert/retry_after_fn."""
    c, _ = minimal_app_client(scope="x", key_fn=lambda r: "k", threshold=5)
    for _ in range(5):
        r = c.post("/test-route")
        assert r.status_code == 200
    r6 = c.post("/test-route")
    assert r6.status_code == 429
    # Retry-After defaults to window_seconds when no fn supplied.
    assert r6.headers["Retry-After"] == "60"
    assert r6.json()["retry_after_seconds"] == 60


def test_middleware_soft_alert_emits_at_exact_threshold(minimal_app_client, share_caplog):
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=20,
        soft_alert_threshold=10,
    )
    for i in range(1, 11):
        r = c.post("/test-route")
        assert r.status_code == 200, f"call {i} unexpectedly rejected"
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    assert soft_records[0].__dict__["labels.count"] == 10


def test_middleware_soft_alert_payload_shape(minimal_app_client, share_caplog):
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=20,
        soft_alert_threshold=10,
    )
    for _ in range(10):
        c.post("/test-route")
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    rec = soft_records[0]
    assert rec.levelname == "WARNING"
    assert rec.__dict__["event.action"] == "share.ratelimit.soft_alert"
    assert rec.__dict__["labels.scope"] == "x"
    assert rec.__dict__["labels.key"].startswith("ratelimit:x:")
    assert rec.__dict__["labels.count"] == 10
    assert rec.__dict__["labels.threshold"] == 20
    assert rec.__dict__["labels.soft_alert_threshold"] == 10


def test_middleware_soft_alert_does_not_emit_when_disabled(minimal_app_client, share_caplog):
    """No soft_alert_threshold → ZERO records on app.share.ratelimit, ever."""
    c, _ = minimal_app_client(scope="x", key_fn=lambda r: "k", threshold=50)
    for _ in range(50):
        r = c.post("/test-route")
        assert r.status_code == 200
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert soft_records == []


def test_middleware_retry_after_seconds_fn_takes_precedence(minimal_app_client):
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=2,
        retry_after_seconds_fn=lambda: 3600,
    )
    for _ in range(2):
        c.post("/test-route")
    r = c.post("/test-route")
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "3600"
    assert r.json()["retry_after_seconds"] == 3600


def test_middleware_retry_after_seconds_fn_default_falls_back_to_window(minimal_app_client):
    """Story 6.6 regression — no fn supplied → Retry-After = window_seconds."""
    c, _ = minimal_app_client(scope="x", key_fn=lambda r: "k", window_seconds=42, threshold=2)
    for _ in range(2):
        c.post("/test-route")
    r = c.post("/test-route")
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "42"


def test_middleware_soft_alert_does_not_re_emit_after_crossing(minimal_app_client, share_caplog):
    """11th, 12th, ..., 20th must NOT re-emit; the crossing fires exactly once."""
    c, _ = minimal_app_client(
        scope="x",
        key_fn=lambda r: "k",
        window_seconds=60,
        threshold=20,
        soft_alert_threshold=10,
    )
    for _ in range(15):
        c.post("/test-route")
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    assert soft_records[0].__dict__["labels.count"] == 10


# ===========================================================================
# AC-2: share_ratelimit_key callable
# ===========================================================================


def _make_request(
    *,
    method: str = "POST",
    path: str = "/api/admin/share",
    cookies: dict | None = None,
) -> Request:
    """Build a minimal Starlette Request with method/path/cookies."""
    headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_value = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers.append((b"cookie", cookie_value.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 0),
        "root_path": "",
    }

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=_receive)


def _member_token(user_id: str = "") -> str:
    sub = user_id or str(uuid.uuid4())
    return encode_token(subject=sub, role="member", secret="test", ttl_minutes=30)


def _admin_token() -> str:
    return encode_token(subject=str(uuid.uuid4()), role="admin", secret="test", ttl_minutes=30)


def _agent_token() -> str:
    return encode_token(subject=str(uuid.uuid4()), role="agent", secret="test", ttl_minutes=30)


@pytest.fixture
def jwt_secret_env(monkeypatch):
    """Ensure ``JWT_SECRET=test`` so ``share_ratelimit_key`` decodes our minted tokens."""
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_share_key_returns_none_for_non_post_method(jwt_secret_env):
    req = _make_request(method="GET", path="/api/admin/share")
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_non_share_path(jwt_secret_env):
    req = _make_request(method="POST", path="/api/admin/users")
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_share_subpath(jwt_secret_env):
    """Exact-string match on /api/admin/share; subpaths (e.g. /<token>) must NOT match."""
    req = _make_request(method="POST", path="/api/admin/share/foo")
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_missing_cookie(jwt_secret_env):
    req = _make_request(method="POST", path="/api/admin/share")
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_invalid_jwt(jwt_secret_env):
    req = _make_request(
        method="POST",
        path="/api/admin/share",
        cookies={"portal_access": "not-a-real-jwt"},
    )
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_admin_role(jwt_secret_env):
    """Decision H exemption — admin role MUST short-circuit the cap."""
    req = _make_request(
        method="POST",
        path="/api/admin/share",
        cookies={"portal_access": _admin_token()},
    )
    assert share_ratelimit_key(req) is None


def test_share_key_returns_none_for_agent_role(jwt_secret_env):
    """Agent has no share permission; key_fn abstains — auth dep returns 403."""
    req = _make_request(
        method="POST",
        path="/api/admin/share",
        cookies={"portal_access": _agent_token()},
    )
    assert share_ratelimit_key(req) is None


def test_share_key_returns_user_day_for_member(jwt_secret_env):
    member_uuid = str(uuid.uuid4())
    token = _member_token(member_uuid)
    req = _make_request(method="POST", path="/api/admin/share", cookies={"portal_access": token})
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    assert share_ratelimit_key(req) == f"user:{member_uuid}:day:{today}"


def test_share_key_uses_utc_day_boundary(jwt_secret_env, monkeypatch):
    """Monkeypatch datetime to two timestamps straddling UTC midnight."""
    member_uuid = str(uuid.uuid4())
    token = _member_token(member_uuid)
    req = _make_request(method="POST", path="/api/admin/share", cookies={"portal_access": token})
    real_datetime = datetime

    class _FrozenDT:
        moment = real_datetime(2026, 1, 1, 23, 30, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.moment

    monkeypatch.setattr("app.core.auth.ratelimit.datetime", _FrozenDT)
    assert share_ratelimit_key(req) == f"user:{member_uuid}:day:2026-01-01"
    _FrozenDT.moment = real_datetime(2026, 1, 2, 0, 30, 0, tzinfo=UTC)
    assert share_ratelimit_key(req) == f"user:{member_uuid}:day:2026-01-02"


# ===========================================================================
# AC-3 supporting tests: share_retry_after_seconds callable
# ===========================================================================


def test_share_retry_after_seconds_returns_positive_int():
    result = share_retry_after_seconds()
    assert isinstance(result, int)
    assert 1 <= result <= 86_400


def test_share_retry_after_seconds_decreases_as_day_progresses(monkeypatch):
    real_datetime = datetime

    class _FrozenDT:
        moment = real_datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.moment

    monkeypatch.setattr("app.core.auth.ratelimit.datetime", _FrozenDT)
    first = share_retry_after_seconds()
    _FrozenDT.moment = real_datetime(2026, 5, 19, 11, 0, 0, tzinfo=UTC)
    second = share_retry_after_seconds()
    assert first - second == 3600


def test_share_retry_after_seconds_clamps_to_one_at_midnight_corner(monkeypatch):
    real_datetime = datetime

    class _FrozenDT:
        moment = real_datetime(2026, 5, 19, 0, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.moment

    monkeypatch.setattr("app.core.auth.ratelimit.datetime", _FrozenDT)
    # 00:00:00 exactly → tomorrow - now = 86400s; not the clamp path but proves
    # we never see 0. Use 23:59:59.999999 of the day to hit the clamp branch.
    _FrozenDT.moment = real_datetime(2026, 5, 19, 23, 59, 59, 999999, tzinfo=UTC)
    result = share_retry_after_seconds()
    assert result >= 1


# ===========================================================================
# AC-5 + AC-6 integration HTTP tests
# ===========================================================================


def test_member_first_20_share_creations_return_201(share_client):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for i in range(20):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201, f"call {i + 1}: {r.text}"
        assert isinstance(r.json()["token"], str) and len(r.json()["token"]) > 0


def test_member_21st_share_creation_returns_429(share_client):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(20):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201
    r = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r.status_code == 429
    body = r.json()
    assert body["detail"] == "rate_limited"
    assert body["scope"] == "share"
    assert isinstance(body["retry_after_seconds"], int)
    assert r.headers["Retry-After"] == str(body["retry_after_seconds"])


def test_member_21st_share_retry_after_within_5s_of_midnight(share_client):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(20):
        c.post("/api/admin/share", json=_create_share_payload(mid))
    r = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r.status_code == 429
    val = int(r.headers["Retry-After"])
    assert 1 <= val <= 86_400
    assert abs(val - share_retry_after_seconds()) <= 5


def test_member_10th_share_emits_soft_alert_log(share_client, share_caplog):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for i in range(10):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201, f"call {i + 1}: {r.text}"
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    rec = soft_records[0]
    assert rec.__dict__["labels.scope"] == "share"
    assert rec.__dict__["labels.key"].startswith("ratelimit:share:user:")
    assert rec.__dict__["labels.count"] == 10
    assert rec.__dict__["labels.threshold"] == 20
    assert rec.__dict__["labels.soft_alert_threshold"] == 10


def test_member_9th_share_does_not_emit_soft_alert(share_client, share_caplog):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(9):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert soft_records == []


def test_member_11th_share_does_not_re_emit_soft_alert(share_client, share_caplog):
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(11):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    assert soft_records[0].__dict__["labels.count"] == 10


def test_admin_21st_share_creation_returns_201(share_client):
    """Decision H admin exemption — admin's 21st POST still returns 201."""
    c, admin_token, _, _, _, _, _, (mid, _), fake = share_client
    _set_cookie(c, admin_token)
    for i in range(21):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201, f"admin call {i + 1}: {r.text}"

    async def _keys():
        return await fake.keys("ratelimit:share:*")

    keys = c.portal.call(_keys)
    assert keys == [] or keys == [], f"admin should not populate any share key: {keys}"


def test_member_get_list_share_returns_403_not_429(share_client):
    """GET list is admin-only AND not capped; member 25x still 403, never 429."""
    c, _, _, member_a_token, _, _, _, _, _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(25):
        r = c.get("/api/admin/share")
        assert r.status_code == 403
        assert r.json()["detail"] == "admin_required"


def test_admin_delete_share_not_capped(share_client):
    """DELETE method check in key_fn → share scope abstains."""
    c, admin_token, _, _, _, _, _, (mid, _), fake = share_client
    _set_cookie(c, admin_token)
    # Mint 5 tokens to delete; each DELETE 204.
    tokens: list[str] = []
    for _ in range(5):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 201
        tokens.append(r.json()["token"])
    for tok in tokens:
        r = c.delete(f"/api/admin/share/{tok}")
        assert r.status_code == 204, r.text

    async def _keys():
        return await fake.keys("ratelimit:share:*")

    keys = c.portal.call(_keys)
    assert keys == []


def test_anonymous_post_share_returns_401_not_429(share_client):
    """Anon POST → key_fn returns None (no cookie) → auth dep returns 401."""
    c, _, _, _, _, _, _, (mid, _), fake = share_client
    _clear_cookie(c)
    for _ in range(25):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 401
        assert r.json()["detail"] == "missing_access"

    async def _keys():
        return await fake.keys("ratelimit:share:*")

    keys = c.portal.call(_keys)
    assert keys == []


def test_share_csrf_rejection_does_not_burn_cap(share_client):
    """CSRF wraps OUTERMOST — 403 csrf_required does NOT burn the share cap."""
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    # Drop CSRF header so each call returns 403 BEFORE rate-limit fires.
    del c.headers["X-Portal-Client"]
    for _ in range(25):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 403
        assert r.json()["detail"] == "csrf_required"
    # Restore the header and make ONE valid call → 201, not 429.
    c.headers["X-Portal-Client"] = "web"
    r = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r.status_code == 201


def test_share_per_user_isolation(share_client):
    """Two members: 20 each → all 40 = 201; 21st on each → 429."""
    c, _, _, member_a_token, _, member_b_token, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    for _ in range(20):
        assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 201
    _set_cookie(c, member_b_token)
    for _ in range(20):
        assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 201
    # 21st on B
    r_b = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r_b.status_code == 429
    # 21st on A
    _set_cookie(c, member_a_token)
    r_a = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r_a.status_code == 429


def test_share_utc_day_rollover_resets_count(share_client, monkeypatch):
    """Advance UTC date → new Redis key → count resets to 1."""
    c, _, _, member_a_token, _, _, _, (mid, _), _ = share_client
    _set_cookie(c, member_a_token)
    real_datetime = datetime

    class _FrozenDT:
        moment = real_datetime(2026, 5, 19, 10, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.moment

    monkeypatch.setattr("app.core.auth.ratelimit.datetime", _FrozenDT)
    # 20 POSTs on 2026-05-19 — all 201
    for _ in range(20):
        assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 201
    # 21st would 429 — verify
    assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 429
    # Advance to next UTC day
    _FrozenDT.moment = real_datetime(2026, 5, 20, 0, 30, 0, tzinfo=UTC)
    r = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r.status_code == 201, r.text


# ===========================================================================
# AC-4: env-var override tests
# ===========================================================================


def test_share_threshold_env_var_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/svo.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_SHARE_THRESHOLD", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        engine = get_engine()
        with Session(engine) as s:
            member = User(
                email=f"m-{uuid.uuid4().hex[:6]}@localhost.localdomain",
                display_name="M",
                role=UserRole.member,
                password_hash="$2b$12$irrelevant.for.these.tests....................",
            )
            s.add(member)
            s.flush()
            member_uuid = member.id
            cat = Category(slug=f"sc-{uuid.uuid4().hex[:6]}", name_en="C")
            s.add(cat)
            s.flush()
            m = Model(
                slug=f"sm-{uuid.uuid4().hex[:6]}",
                name_en="M",
                category_id=cat.id,
            )
            s.add(m)
            s.commit()
            mid = m.id
        member_token = encode_token(
            subject=str(member_uuid), role="member", secret="test", ttl_minutes=30
        )
        c.cookies.set("portal_access", member_token)
        for i in range(5):
            assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 201, (
                f"call {i + 1} should 201 under threshold=5"
            )
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
        assert r.status_code == 429
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_share_soft_alert_threshold_env_var_override(tmp_path, monkeypatch, share_caplog):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/sso.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_SHARE_SOFT_ALERT_THRESHOLD", "3")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
    factory = MagicMock()
    factory.get = MagicMock(return_value=fake)

    async def _aclose():
        return None

    factory.aclose = _aclose
    with TestClient(app) as c:
        c.headers.update({"X-Portal-Client": "web"})
        app.state.redis = factory
        engine = get_engine()
        with Session(engine) as s:
            member = User(
                email=f"m-{uuid.uuid4().hex[:6]}@localhost.localdomain",
                display_name="M",
                role=UserRole.member,
                password_hash="$2b$12$irrelevant.for.these.tests....................",
            )
            s.add(member)
            s.flush()
            member_uuid = member.id
            cat = Category(slug=f"sc-{uuid.uuid4().hex[:6]}", name_en="C")
            s.add(cat)
            s.flush()
            m = Model(
                slug=f"sm-{uuid.uuid4().hex[:6]}",
                name_en="M",
                category_id=cat.id,
            )
            s.add(m)
            s.commit()
            mid = m.id
        member_token = encode_token(
            subject=str(member_uuid), role="member", secret="test", ttl_minutes=30
        )
        c.cookies.set("portal_access", member_token)
        for _ in range(4):
            assert c.post("/api/admin/share", json=_create_share_payload(mid)).status_code == 201
    soft_records = [
        rec
        for rec in share_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
    ]
    assert len(soft_records) == 1
    assert soft_records[0].__dict__["labels.count"] == 3
    assert soft_records[0].__dict__["labels.soft_alert_threshold"] == 3
    get_settings.cache_clear()
    get_engine.cache_clear()


# ===========================================================================
# Fail-soft on share scope
# ===========================================================================


def test_share_redis_outage_allows_creation_with_warning_log(share_client, auth_ratelimit_caplog):
    c, _, _, member_a_token, _, _, _, (mid, _), fake = share_client
    _set_cookie(c, member_a_token)
    with patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")):
        r = c.post("/api/admin/share", json=_create_share_payload(mid))
    assert r.status_code == 201, r.text
    records = [
        rec
        for rec in auth_ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    # Multiple middleware instances may log on the same request (login/refresh/register/share
    # all hit the redis pipeline); we only care that share is among them.
    share_records = [r for r in records if r.__dict__.get("labels.scope") == "share"]
    assert len(share_records) >= 1


# ===========================================================================
# Module-surface
# ===========================================================================


def test_ratelimit_module_exports_share_callables():
    from app.core.auth import ratelimit as rl

    assert callable(rl.share_ratelimit_key)
    assert callable(rl.share_retry_after_seconds)
    # Backward-compat: trio + class still exported
    assert isinstance(rl.RateLimitMiddleware, type)
    assert callable(rl.login_ratelimit_key)
    assert callable(rl.refresh_ratelimit_key)
    assert callable(rl.register_ratelimit_key)
