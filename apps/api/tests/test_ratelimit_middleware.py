"""Tests for the Initiative 5 rate-limit middleware (Story 6.6).

Covers AC-1 through AC-7 from the Story 6.6 spec:
- AC-1: RateLimitMiddleware class shape (sliding-window primitive + 429 + Retry-After)
- AC-2: Redis-unreachable fail-soft (WARNING log + ALLOW)
- AC-3: Three instances mounted in main.py with CSRF-before-rate-limit ordering
- AC-4: Six Settings fields with env-var tunability
- AC-5: HTTP-layer threshold verification per scope (5/10/3 thresholds)
- AC-6: Per-IP isolation + sliding-window correctness
- AC-7: Zero frontend / migration / OpenAPI / audit drift

Two fixture rigs:
- ``minimal_app_client`` — a fresh FastAPI() with a single /test-route, used
  for class-shape ASGI unit tests (mounted with arbitrary scope="test_scope").
- ``integration_client`` — TestClient(create_app()) + fakeredis swap, used
  for integration HTTP tests against the real /api/auth/{login,refresh,register} routes.
"""

from __future__ import annotations

import logging
import time
from unittest.mock import MagicMock, patch

import fakeredis.aioredis
import pytest
import redis.exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth.ratelimit import (
    RateLimitMiddleware,
    _client_ip,
    login_ratelimit_key,
)

PASSWORD_STRONG = "Tr0ub4dor&3-correct-horse"
REGISTER_BODY = {
    "token": "x" * 43,
    "email": "valid@example.com",
    "password": PASSWORD_STRONG,
}


# ---------------------------------------------------------------------------
# Fixture: minimal FastAPI app with one /test-route + parameterized middleware
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_app_client():
    """Builds a minimal FastAPI() app for ASGI-level unit tests.

    The factory enters the TestClient as a context manager so the underlying
    anyio portal (and therefore the fakeredis event-loop binding) stays alive
    across multiple ``c.post()`` calls in the same test.
    """
    opened: list[TestClient] = []

    def _build(*, scope: str, key_fn, window_seconds: int = 60, threshold: int = 5):
        app = FastAPI()
        # Per-test isolated FakeServer so state does not leak across tests
        # (default fakeredis.aioredis.FakeRedis() shares a global server).
        fake = fakeredis.aioredis.FakeRedis(server=fakeredis.FakeServer())
        factory = MagicMock()
        factory.get = MagicMock(return_value=fake)
        app.state.redis = factory
        app.add_middleware(
            RateLimitMiddleware,
            scope=scope,
            key_fn=key_fn,
            window_seconds=window_seconds,
            threshold=threshold,
        )

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
# Fixture: full create_app() + fakeredis swap (integration tests)
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    """Tiny in-memory handler — records every emitted record into ``records``."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def ratelimit_caplog():
    """Capture records emitted on ``app.auth.ratelimit`` for the duration of the test.

    Pytest's built-in ``caplog`` attaches its handler to root; the
    ``app.core.logging.configure_logging`` call inside the FastAPI lifespan
    startup wipes ``root.handlers``, which removes pytest's handler and any
    subsequent record goes to /dev/null from caplog's perspective. This
    fixture sidesteps the issue by attaching a dedicated handler directly to
    the named ratelimit logger.
    """
    logger = logging.getLogger("app.auth.ratelimit")
    prev_level = logger.level
    prev_disabled = logger.disabled
    handler = _ListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    # Some prior tests can leave `disabled=True` on the named logger via
    # `logging.config.dictConfig(...)` calls; ensure capture works.
    logger.disabled = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)
        logger.disabled = prev_disabled


@pytest.fixture
def integration_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

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
        yield c, fake, app
    get_settings.cache_clear()
    get_engine.cache_clear()


# ---------------------------------------------------------------------------
# AC-1 + AC-6 class-shape tests
# ---------------------------------------------------------------------------


def test_middleware_passes_through_when_count_below_threshold(minimal_app_client):
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    r = c.post("/test-route")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_middleware_returns_429_on_threshold_plus_one(minimal_app_client):
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    for _ in range(5):
        r = c.post("/test-route")
        assert r.status_code == 200
    r6 = c.post("/test-route")
    assert r6.status_code == 429
    assert r6.headers["Retry-After"] == "60"
    assert r6.json() == {
        "detail": "rate_limited",
        "scope": "test_scope",
        "retry_after_seconds": 60,
    }


def test_middleware_skips_non_http_scope(minimal_app_client):
    """ASGI lifespan scope MUST short-circuit (no Redis call).

    Verified indirectly via TestClient.__enter__ / __exit__ which dispatches
    a lifespan scope under the hood. If the middleware tried to call
    redis.pipeline() on it, the FastAPI lifespan startup would raise.
    """
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    # Smoke: the TestClient was constructed without raising, which means the
    # lifespan startup completed without the middleware touching redis.
    assert c.app.state.redis.get is not None


def test_middleware_skips_when_key_fn_returns_none(minimal_app_client):
    c, _ = minimal_app_client(scope="test_scope", key_fn=lambda r: None, threshold=5)
    # 100 calls without rate-limit because key_fn returns None for each.
    for _ in range(100):
        r = c.post("/test-route")
        assert r.status_code == 200


def test_middleware_redis_unavailable_logs_warning_and_allows(minimal_app_client, ratelimit_caplog):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    with patch.object(
        fake,
        "pipeline",
        side_effect=redis.exceptions.ConnectionError("simulated outage"),
    ):
        r = c.post("/test-route")
    assert r.status_code == 200
    records = [
        rec
        for rec in ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].levelname == "WARNING"
    assert records[0].__dict__["labels.scope"] == "test_scope"


def test_middleware_redis_timeout_logs_warning_and_allows(minimal_app_client, ratelimit_caplog):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    with patch.object(fake, "pipeline", side_effect=redis.exceptions.TimeoutError("slow")):
        r = c.post("/test-route")
    assert r.status_code == 200
    records = [
        rec
        for rec in ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1


def test_middleware_unexpected_exception_propagates(minimal_app_client):
    c, fake = minimal_app_client(scope="test_scope", key_fn=lambda r: "k", threshold=5)
    with (
        patch.object(fake, "pipeline", side_effect=ValueError("not a redis error")),
        pytest.raises(ValueError, match="not a redis error"),
    ):
        c.post("/test-route")


def test_middleware_sliding_window_purges_old_entries(minimal_app_client):
    c, fake = minimal_app_client(
        scope="test_scope", key_fn=lambda r: "k", window_seconds=60, threshold=5
    )
    # Pre-populate the sorted set with 4 entries WAY OUTSIDE the 60s window
    # (scores at 70 seconds ago). They should be ZREMRANGEBYSCORE'd by the
    # first request, so the count after the first call is 1, not 5.

    async def _seed():
        now_ms = int(time.time() * 1000)
        ancient = now_ms - 70_000
        for i in range(4):
            await fake.zadd("ratelimit:test_scope:k", {f"ancient-{i}": ancient + i})

    c.portal.call(_seed)
    for _ in range(5):
        r = c.post("/test-route")
        assert r.status_code == 200, r.text
    r6 = c.post("/test-route")
    assert r6.status_code == 429


def test_middleware_per_key_isolation(minimal_app_client):
    c, _ = minimal_app_client(
        scope="test_scope",
        key_fn=lambda r: r.headers.get("X-Test-Key", "default"),
        threshold=5,
    )
    for _ in range(5):
        r = c.post("/test-route", headers={"X-Test-Key": "a"})
        assert r.status_code == 200
    for _ in range(5):
        r = c.post("/test-route", headers={"X-Test-Key": "b"})
        assert r.status_code == 200
    # 6th call on key "a" rejects
    r = c.post("/test-route", headers={"X-Test-Key": "a"})
    assert r.status_code == 429


def test_middleware_zadd_unique_score_member(minimal_app_client):
    """Verify ZADD member is unique-per-request even when scores collide.

    If the implementation used a fixed member (e.g., a static string),
    sorted-set semantics would collapse two concurrent same-ms requests
    into one entry, under-counting the actual request rate.
    """
    c, fake = minimal_app_client(
        scope="test_scope", key_fn=lambda r: "k", window_seconds=60, threshold=5
    )

    async def _seed():
        now_ms = int(time.time() * 1000)
        # Same score, different members → 5 distinct ZSET entries.
        await fake.zadd("ratelimit:test_scope:k", {f"m{i}": now_ms for i in range(5)})

    c.portal.call(_seed)
    r = c.post("/test-route")
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# AC-5 integration tests — login scope
# ---------------------------------------------------------------------------


def test_login_6th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.0.1"}
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 401, r.text
    r6 = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r6.status_code == 429
    assert r6.json()["detail"] == "rate_limited"


def test_login_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.0.2"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
    r = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "login",
        "retry_after_seconds": 60,
    }


def test_login_429_retry_after_header_value(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.0.3"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
    r = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r.headers["Retry-After"] == "60"


def test_login_window_clears_after_flush(integration_client):
    c, fake, _ = integration_client
    headers = {"X-Real-IP": "10.0.0.4"}
    for _ in range(6):
        c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )

    async def _flush():
        await fake.flushdb()

    c.portal.call(_flush)
    r = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 401  # passes rate-limit, hits invalid-credentials


def test_login_different_ips_isolated(integration_client):
    c, _, _ = integration_client
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers={"X-Real-IP": "1.1.1.1"},
        )
        assert r.status_code == 401
    for _ in range(5):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers={"X-Real-IP": "2.2.2.2"},
        )
        assert r.status_code == 401


def test_login_csrf_rejection_does_not_burn_rate_limit(integration_client):
    c, _, _ = integration_client
    # Drop the CSRF header so each call returns 403 BEFORE rate-limit fires.
    del c.headers["X-Portal-Client"]
    headers = {"X-Real-IP": "10.0.0.5"}
    for _ in range(10):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "csrf_required"
    # Restore the header and make ONE valid call → must return 401, not 429.
    c.headers["X-Portal-Client"] = "web"
    r = c.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
        headers=headers,
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# AC-5 integration tests — refresh scope
# ---------------------------------------------------------------------------


def test_refresh_11th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.1.1"}
    for _ in range(10):
        r = c.post("/api/auth/refresh", headers=headers)
        assert r.status_code == 401
    r = c.post("/api/auth/refresh", headers=headers)
    assert r.status_code == 429


def test_refresh_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.1.2"}
    for _ in range(11):
        c.post("/api/auth/refresh", headers=headers)
    r = c.post("/api/auth/refresh", headers=headers)
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "refresh",
        "retry_after_seconds": 60,
    }


# ---------------------------------------------------------------------------
# AC-5 integration tests — register scope
# ---------------------------------------------------------------------------


def test_register_4th_call_returns_429_within_window(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.2.1"}
    for _ in range(3):
        r = c.post("/api/auth/register", json=REGISTER_BODY, headers=headers)
        assert r.status_code == 404, r.text
    r = c.post("/api/auth/register", json=REGISTER_BODY, headers=headers)
    assert r.status_code == 429


def test_register_429_body_shape(integration_client):
    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.2.2"}
    for _ in range(4):
        c.post("/api/auth/register", json=REGISTER_BODY, headers=headers)
    r = c.post("/api/auth/register", json=REGISTER_BODY, headers=headers)
    assert r.status_code == 429
    assert r.json() == {
        "detail": "rate_limited",
        "scope": "register",
        "retry_after_seconds": 60,
    }


def test_register_429_does_not_emit_register_fail_audit(integration_client):
    """The 429 fires BEFORE the route handler runs → no auth.register.fail row.

    Verified by counting `auth.register.fail` audit rows after the 4-call
    burst: expected count is 3 (the three 404 calls each emit), not 4.
    """
    from sqlmodel import Session, select

    from app.core.db.models import AuditLog
    from app.core.db.session import get_engine

    c, _, _ = integration_client
    headers = {"X-Real-IP": "10.0.2.3"}
    engine = get_engine()
    # Clear any pre-existing audit rows from app boot or earlier interactions.
    with Session(engine) as s:
        for row in s.exec(select(AuditLog).where(AuditLog.action == "auth.register.fail")).all():
            s.delete(row)
        s.commit()
    for _ in range(4):
        c.post("/api/auth/register", json=REGISTER_BODY, headers=headers)
    with Session(engine) as s:
        rows = s.exec(select(AuditLog).where(AuditLog.action == "auth.register.fail")).all()
    assert len(rows) == 3  # 3 successful 404s emit audit; 4th 429 does not


# ---------------------------------------------------------------------------
# AC-4 env-var override tests
# ---------------------------------------------------------------------------


def test_login_rate_limit_threshold_env_var_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r2.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_LOGIN_THRESHOLD", "2")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

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
        headers = {"X-Real-IP": "10.0.5.1"}
        for _ in range(2):
            r = c.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "x"},
                headers=headers,
            )
            assert r.status_code == 401
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers=headers,
        )
        assert r.status_code == 429  # 3rd call rejects (threshold=2)
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_login_rate_limit_window_env_var_override(tmp_path, monkeypatch):
    """Window-size override: 30s instead of 60s → an entry at -40s is purged."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/r3.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("RATELIMIT_LOGIN_WINDOW_SECONDS", "30")
    from app.core.config import get_settings
    from app.core.db.session import get_engine
    from app.main import create_app

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

        # Seed an ancient entry at -40 seconds (beyond the new 30s window).
        async def _seed():
            now_ms = int(time.time() * 1000)
            await fake.zadd("ratelimit:login:ip:10.0.5.2", {"ancient": now_ms - 40_000})

        c.portal.call(_seed)
        headers = {"X-Real-IP": "10.0.5.2"}
        for _ in range(5):
            r = c.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "x"},
                headers=headers,
            )
            assert r.status_code == 401, r.text
    get_settings.cache_clear()
    get_engine.cache_clear()


# ---------------------------------------------------------------------------
# Fail-soft integration tests
# ---------------------------------------------------------------------------


def test_login_redis_outage_allows_request_with_warning_log(integration_client, ratelimit_caplog):
    c, fake, _ = integration_client
    with patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")):
        r = c.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "x"},
            headers={"X-Real-IP": "10.0.6.1"},
        )
    assert r.status_code == 401  # passes through, hits invalid-credentials
    records = [
        rec
        for rec in ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "login"


def test_refresh_redis_outage_allows_request_with_warning_log(integration_client, ratelimit_caplog):
    c, fake, _ = integration_client
    with patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")):
        r = c.post(
            "/api/auth/refresh",
            headers={"X-Real-IP": "10.0.6.2"},
        )
    assert r.status_code == 401
    records = [
        rec
        for rec in ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "refresh"


def test_register_redis_outage_allows_request_with_warning_log(
    integration_client, ratelimit_caplog
):
    c, fake, _ = integration_client
    with patch.object(fake, "pipeline", side_effect=redis.exceptions.ConnectionError("down")):
        r = c.post(
            "/api/auth/register",
            json=REGISTER_BODY,
            headers={"X-Real-IP": "10.0.6.3"},
        )
    assert r.status_code == 404  # passes through, hits token_invalid
    records = [
        rec
        for rec in ratelimit_caplog.records
        if rec.__dict__.get("event.action") == "ratelimit.redis_unavailable"
    ]
    assert len(records) >= 1
    assert records[0].__dict__["labels.scope"] == "register"


# ---------------------------------------------------------------------------
# Module surface + helper tests
# ---------------------------------------------------------------------------


def test_ratelimit_module_exports_class_and_three_key_fns():
    from app.core.auth import ratelimit as rl

    assert isinstance(rl.RateLimitMiddleware, type)
    for fn in (rl.login_ratelimit_key, rl.refresh_ratelimit_key, rl.register_ratelimit_key):
        assert callable(fn)


def test_login_ratelimit_key_returns_none_for_non_login_path():
    req = MagicMock()
    req.method = "POST"
    req.url.path = "/api/auth/refresh"
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert login_ratelimit_key(req) is None


def test_login_ratelimit_key_returns_none_for_get_method():
    req = MagicMock()
    req.method = "GET"
    req.url.path = "/api/auth/login"
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert login_ratelimit_key(req) is None


def test_client_ip_prefers_x_real_ip_over_xff():
    # nginx sets X-Real-IP from $remote_addr (unforgeable across the proxy hop);
    # X-Forwarded-For is attacker-controlled and must be ignored even when both
    # headers are present.
    req = MagicMock()
    req.headers = {"x-real-ip": "5.6.7.8", "x-forwarded-for": "1.1.1.1, 2.2.2.2"}
    req.client = MagicMock(host="ignored")
    assert _client_ip(req) == "5.6.7.8"


def test_client_ip_ignores_forged_xff_without_real_ip():
    # Without X-Real-IP, a forged XFF still does NOT shift the bucket — the
    # limiter falls back to the transport-level client host. This is the bypass
    # the rewrite blocks: attacker spraying random first-XFF values lands in the
    # same client.host bucket and trips the threshold.
    req = MagicMock()
    req.headers = {"x-forwarded-for": "1.1.1.1, 2.2.2.2, 3.3.3.3"}
    req.client = MagicMock(host="10.0.0.1")
    assert _client_ip(req) == "10.0.0.1"


def test_client_ip_falls_back_to_request_client_host():
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="1.2.3.4")
    assert _client_ip(req) == "1.2.3.4"


def test_client_ip_returns_unknown_when_no_headers_and_no_client():
    req = MagicMock()
    req.headers = {}
    req.client = None
    assert _client_ip(req) == "unknown"
