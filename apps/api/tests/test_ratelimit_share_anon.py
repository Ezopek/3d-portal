"""Tests for Initiative 12 Story 19.1 — anonymous share view DDoS cap.

Realizes NFR12-DDOS-RATE-1 (60 req/min per (token, IP) tuple on
``/api/share/{token}/*``). Operator-calibrated 2026-05-23 AskUserQuestion.

Three test classes:
1. share_anon_ratelimit_key behavior (URL parsing + key shape)
2. Middleware cap enforcement against the live share router
3. Per-IP and per-token isolation

Uses the same dedicated ``_ListHandler`` pattern Story 18.4 codified
(``app.share.ratelimit`` logger wiped by configure_logging at lifespan
startup; attaching to the named logger sidesteps it).
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.auth.ratelimit import (
    share_anon_ratelimit_key,
    share_anon_retry_after_seconds,
)
from app.main import create_app

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Fixture: full app with anon-share router (and the middleware mounted)
# ---------------------------------------------------------------------------


@pytest.fixture
def share_anon_client(monkeypatch, tmp_path):
    """TestClient(create_app()) + fakeredis swap. Anonymous (no cookies)."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        app = create_app()
        fake = fakeredis.aioredis.FakeRedis()
        factory = MagicMock()
        factory.get = MagicMock(return_value=fake)

        async def _aclose():
            return None

        factory.aclose = _aclose
        with TestClient(app) as c:
            c.headers.update({"X-Portal-Client": "web"})
            app.state.redis = factory
            yield c
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()


# ---------------------------------------------------------------------------
# Fixture: dedicated logger handler (Story 18.4 lesson)
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def share_anon_caplog():
    """Capture records on ``app.auth.ratelimit`` for the test duration.

    RateLimitMiddleware logs soft-alert at ``app.auth.ratelimit`` (see
    apps/api/app/core/auth/ratelimit.py:_LOG). configure_logging wipes
    pytest's root caplog handler during lifespan startup; attaching here
    sidesteps the wipe. Mirrors test_ratelimit_share_cap.py:share_caplog.
    """
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
# 1. Key-function unit tests (no Redis)
# ---------------------------------------------------------------------------


def _make_request(path: str, ip: str = "10.0.0.1") -> Request:
    """Synthesize a Starlette Request with a given URL path + X-Real-IP."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"x-real-ip", ip.encode())],
        "query_string": b"",
        "client": ("127.0.0.1", 0),
    }
    return Request(scope)


def test_share_anon_key_extracts_token_and_ip():
    req = _make_request("/api/share/abc123def/files")
    key = share_anon_ratelimit_key(req)
    assert key is not None
    assert key.startswith("token:")
    assert ":ip:10.0.0.1" in key
    # Hash prefix is 16 chars (64 bits)
    expected_hash = hashlib.sha256(b"abc123def").hexdigest()[:16]
    assert key == f"token:{expected_hash}:ip:10.0.0.1"


def test_share_anon_key_returns_none_for_non_share_path():
    assert share_anon_ratelimit_key(_make_request("/api/auth/login")) is None
    assert share_anon_ratelimit_key(_make_request("/api/admin/share")) is None
    assert share_anon_ratelimit_key(_make_request("/api/health")) is None
    assert share_anon_ratelimit_key(_make_request("/api/share/")) is None  # no token


def test_share_anon_key_returns_none_for_empty_token():
    # /api/share//files — token segment is empty
    assert share_anon_ratelimit_key(_make_request("/api/share//files")) is None


def test_share_anon_key_handles_token_only_path():
    """GET /api/share/<token> (resolve endpoint) — no trailing segment."""
    req = _make_request("/api/share/abc123def")
    key = share_anon_ratelimit_key(req)
    assert key is not None
    expected_hash = hashlib.sha256(b"abc123def").hexdigest()[:16]
    assert key == f"token:{expected_hash}:ip:10.0.0.1"


def test_share_anon_key_does_not_leak_token_cleartext():
    """Security invariant: the raw token MUST NOT appear in the Redis key.

    Storing tokens cleartext in Redis is a leak vector — Redis logs key
    patterns under DEBUG, snapshots can be dumped, monitoring/observability
    pipelines surface key names. Hashing keeps the secret material safe.
    """
    secret_token = "this-is-a-very-secret-share-token-xyz"
    req = _make_request(f"/api/share/{secret_token}/files")
    key = share_anon_ratelimit_key(req)
    assert key is not None
    assert secret_token not in key


def test_share_anon_retry_after_is_window_duration():
    """Sliding-window Retry-After = window duration (60s), NOT seconds-to-midnight."""
    assert share_anon_retry_after_seconds() == 60


# ---------------------------------------------------------------------------
# 2. Middleware cap enforcement (Redis-backed)
# ---------------------------------------------------------------------------


def test_anon_cap_60_requests_pass_61st_returns_429(share_anon_client):
    """The 60th request under the cap PASSES (404 from share router because
    no token registered, but middleware lets it through). The 61st gets 429.
    """
    c = share_anon_client
    # All 60 requests share the same (token, IP) bucket
    for i in range(60):
        r = c.get("/api/share/abc/files")
        assert r.status_code != 429, f"request {i+1} unexpectedly hit cap: {r.text}"
    # 61st must be rate-limited
    r = c.get("/api/share/abc/files")
    assert r.status_code == 429, f"expected 429 on 61st, got {r.status_code}: {r.text}"
    # Retry-After header set by share_anon_retry_after_seconds()
    assert r.headers.get("retry-after") == "60"


def test_anon_cap_is_per_token(share_anon_client):
    """Different tokens get independent buckets even from the same IP."""
    c = share_anon_client
    # Saturate bucket for token A
    for _ in range(60):
        c.get("/api/share/tokenA/files")
    # 61st on token A returns 429
    assert c.get("/api/share/tokenA/files").status_code == 429
    # token B is a separate bucket — 1st request passes
    r = c.get("/api/share/tokenB/files")
    assert r.status_code != 429, f"token B was cross-polluted: {r.text}"


def test_anon_cap_is_per_ip(share_anon_client):
    """Same token but different IPs get independent buckets."""
    c = share_anon_client
    # Saturate token X from IP 1
    for _ in range(60):
        c.get("/api/share/tokenX/files", headers={"X-Real-IP": "10.0.0.1"})
    assert (
        c.get("/api/share/tokenX/files", headers={"X-Real-IP": "10.0.0.1"}).status_code
        == 429
    )
    # Same token from a different IP — fresh bucket
    r = c.get("/api/share/tokenX/files", headers={"X-Real-IP": "10.0.0.2"})
    assert r.status_code != 429, f"IP isolation broken: {r.text}"


def test_non_share_paths_bypass_anon_cap(share_anon_client):
    """Hitting /api/health 100× must NOT count against any share-anon bucket."""
    c = share_anon_client
    for _ in range(100):
        r = c.get("/api/health")
        assert r.status_code == 200
    # Now a share request still has full budget available — first request passes
    r = c.get("/api/share/some-token/files")
    assert r.status_code != 429
