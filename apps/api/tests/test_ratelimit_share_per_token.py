"""Tests for Initiative 16 Story 23.3 — per-token share-view DDoS cap.

Realizes FR16-RATELIMIT-PER-TOKEN-1 (60 req/min per token, IP-INDEPENDENT, on
``/api/share/{token}/*``). Layered defense on top of Init 12 Story 19.1
per-(token, IP) middleware: a botnet wielding a single leaked share token
across many IPs defeats the per-IP cap; the per-token cap catches it.
Closes TB-026 sub#6 per-token addition (operator-decision 2026-05-24).

Three test classes:
1. share_anon_per_token_ratelimit_key behavior (URL parsing + key shape)
2. Middleware cap enforcement against the live share router (single + multi IP)
3. Composability with the existing per-(token, IP) middleware

Mirrors the dedicated ``_ListHandler`` pattern Story 18.4 codified
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
    share_anon_per_token_ratelimit_key,
    share_anon_per_token_retry_after_seconds,
)
from app.main import create_app

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Fixture: full app with anon-share router (per-token middleware mounted)
# ---------------------------------------------------------------------------


@pytest.fixture
def share_anon_client(monkeypatch, tmp_path):
    """TestClient(create_app()) + fakeredis swap. Anonymous (no cookies).

    Mirrors test_ratelimit_share_anon.py:share_anon_client. Per-(token, IP)
    and per-token middlewares both fire under this fixture — set thresholds
    via monkeypatch.setenv BEFORE this fixture is called.
    """
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


@pytest.fixture
def share_anon_client_low_per_token(monkeypatch, tmp_path):
    """share_anon_client variant: per-token cap LOW (5), per-(token, IP) cap HIGH (100).

    Used by tests that need to prove per-token middleware fires BEFORE the
    per-(token, IP) one when caps are configured asymmetrically. Mirrors the
    composability proof from Story 23.3 spec AC5.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    # Per-token cap LOW so it fires first.
    monkeypatch.setenv("RATELIMIT_SHARE_PER_TOKEN_THRESHOLD", "5")
    # Per-(token, IP) cap HIGH so it would not fire under the same volume.
    monkeypatch.setenv("RATELIMIT_SHARE_ANON_THRESHOLD", "100")
    # Disable per-(token, IP) soft-alert noise so caplog assertions stay clean.
    monkeypatch.setenv("RATELIMIT_SHARE_ANON_SOFT_ALERT_THRESHOLD", "100")

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
    """Capture records on ``app.share.ratelimit`` for the test duration.

    RateLimitMiddleware emits soft-alert WARNINGS on ``app.share.ratelimit``
    (see apps/api/app/core/auth/ratelimit.py:_SHARE_LOG). configure_logging
    wipes pytest's root caplog handler during lifespan startup; attaching
    here sidesteps the wipe. Mirrors test_ratelimit_share_anon.py:share_anon_caplog.
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


def test_per_token_key_extracts_only_token_no_ip():
    """Per-token key MUST NOT include IP — that's the whole point of the layer."""
    req = _make_request("/api/share/abc123def/files", ip="10.0.0.1")
    key = share_anon_per_token_ratelimit_key(req)
    assert key is not None
    assert key.startswith("token:")
    # IP suffix MUST NOT be present (distinguishes from share_anon_ratelimit_key)
    assert ":ip:" not in key
    assert "10.0.0.1" not in key
    expected_hash = hashlib.sha256(b"abc123def").hexdigest()[:16]
    assert key == f"token:{expected_hash}"


def test_per_token_key_identical_across_different_ips():
    """SAME token from DIFFERENT IPs → SAME key (the defining property)."""
    req1 = _make_request("/api/share/sametoken/files", ip="10.0.0.1")
    req2 = _make_request("/api/share/sametoken/files", ip="192.168.1.1")
    req3 = _make_request("/api/share/sametoken/files", ip="203.0.113.42")
    assert share_anon_per_token_ratelimit_key(req1) == share_anon_per_token_ratelimit_key(req2)
    assert share_anon_per_token_ratelimit_key(req2) == share_anon_per_token_ratelimit_key(req3)


def test_per_token_key_differs_across_tokens():
    """Different tokens → different keys (token isolation)."""
    req_a = _make_request("/api/share/tokenA/files", ip="10.0.0.1")
    req_b = _make_request("/api/share/tokenB/files", ip="10.0.0.1")
    assert share_anon_per_token_ratelimit_key(req_a) != share_anon_per_token_ratelimit_key(req_b)


def test_per_token_key_returns_none_for_non_share_path():
    assert share_anon_per_token_ratelimit_key(_make_request("/api/auth/login")) is None
    assert share_anon_per_token_ratelimit_key(_make_request("/api/admin/share")) is None
    assert share_anon_per_token_ratelimit_key(_make_request("/api/health")) is None
    assert share_anon_per_token_ratelimit_key(_make_request("/api/share/")) is None  # no token


def test_per_token_key_returns_none_for_empty_token():
    # /api/share//files — token segment is empty
    assert share_anon_per_token_ratelimit_key(_make_request("/api/share//files")) is None


def test_per_token_key_handles_token_only_path():
    """GET /api/share/<token> (resolve endpoint) — no trailing segment."""
    req = _make_request("/api/share/abc123def")
    key = share_anon_per_token_ratelimit_key(req)
    assert key is not None
    expected_hash = hashlib.sha256(b"abc123def").hexdigest()[:16]
    assert key == f"token:{expected_hash}"


def test_per_token_key_does_not_leak_token_cleartext():
    """Security invariant: the raw token MUST NOT appear in the Redis key.

    Same rationale as Story 19.1: Redis logs key patterns under DEBUG,
    snapshots can be dumped, monitoring pipelines surface key names.
    Hashing keeps the secret material safe.
    """
    secret_token = "this-is-a-very-secret-share-token-xyz"
    req = _make_request(f"/api/share/{secret_token}/files")
    key = share_anon_per_token_ratelimit_key(req)
    assert key is not None
    assert secret_token not in key


def test_per_token_retry_after_is_window_duration():
    """Sliding-window Retry-After = window duration (60s default), NOT seconds-to-midnight."""
    assert share_anon_per_token_retry_after_seconds() == 60


def test_per_token_retry_after_picks_up_settings_override(monkeypatch):
    """Verifies call-time settings read — operator-tuned window propagates."""
    monkeypatch.setenv("RATELIMIT_SHARE_PER_TOKEN_WINDOW_SECONDS", "120")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert share_anon_per_token_retry_after_seconds() == 120
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 2. Middleware cap enforcement (Redis-backed) — default config (60/60)
# ---------------------------------------------------------------------------


def test_per_token_cap_60_requests_pass_61st_returns_429(share_anon_client):
    """Single IP: 60 requests under cap pass, 61st returns 429.

    Note: with default config, BOTH per-token (60) AND per-(token, IP) (60)
    have the same threshold. The 61st request triggers ONE of the two; the
    Starlette LIFO ordering makes per-(token, IP) the outer layer so it
    is the one returning 429 in this default config. The point of this test
    is the cap fires at 60 — composability tests below prove which.
    """
    c = share_anon_client
    for i in range(60):
        r = c.get("/api/share/abc/files")
        assert r.status_code != 429, f"request {i + 1} unexpectedly hit cap: {r.text}"
    r = c.get("/api/share/abc/files")
    assert r.status_code == 429, f"expected 429 on 61st, got {r.status_code}: {r.text}"
    assert r.headers.get("retry-after") == "60"


def test_per_token_cap_is_per_token(share_anon_client):
    """Different tokens get independent per-token buckets."""
    c = share_anon_client
    # Saturate token A
    for _ in range(60):
        c.get("/api/share/tokenA/files")
    assert c.get("/api/share/tokenA/files").status_code == 429
    # Token B is a separate bucket — 1st request passes
    r = c.get("/api/share/tokenB/files")
    assert r.status_code != 429, f"token B was cross-polluted: {r.text}"


def test_non_share_paths_bypass_per_token_cap(share_anon_client):
    """Hitting /api/health 100x must NOT count against any share-anon-per-token bucket."""
    c = share_anon_client
    for _ in range(100):
        r = c.get("/api/health")
        assert r.status_code == 200
    # Now a share request still has full per-token budget — first request passes
    r = c.get("/api/share/some-token/files")
    assert r.status_code != 429


# ---------------------------------------------------------------------------
# 3. Per-token-distinct-from-per-(token, IP) — distributed IP attack
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ips",
    [
        ["10.0.0.1", "10.0.0.2"],
        ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
        ["192.168.1.10", "203.0.113.5", "172.16.0.99"],
    ],
)
def test_per_token_cap_catches_multi_ip_attack(share_anon_client_low_per_token, ips):
    """Botnet simulation: per-token cap LOW (5), per-(token, IP) cap HIGH (100).

    Distribute 6 requests for the SAME token across N IPs. The per-(token, IP)
    cap would NEVER fire (max 6/N < 100). The per-token cap WILL fire at the
    6th request (threshold=5).

    AC5 from spec: 'Per-token overage from distributed IPs (mock multiple
    X-Forwarded-For values): 429 surfaces from NEW Story 23.3 middleware.'
    """
    c = share_anon_client_low_per_token
    # Round-robin 6 requests across the IP set — total volume exceeds per-token
    # cap of 5 regardless of any single IP's contribution.
    statuses: list[int] = []
    for i in range(6):
        ip = ips[i % len(ips)]
        r = c.get("/api/share/leaked-token/files", headers={"X-Real-IP": ip})
        statuses.append(r.status_code)
    # First 5 must NOT 429 (per-token cap not yet exceeded)
    assert all(s != 429 for s in statuses[:5]), f"premature 429 in first 5: {statuses}"
    # 6th must 429 — and the scope MUST be share_anon_per_token (NOT share_anon)
    assert statuses[5] == 429, f"6th request should 429 (per-token cap 5): {statuses}"
    # Verify the 429 came from the per-token middleware, not the per-(token, IP) one
    r = c.get("/api/share/leaked-token/files", headers={"X-Real-IP": ips[0]})
    assert r.status_code == 429
    body = r.json()
    assert body["scope"] == "share_anon_per_token", (
        f"expected 429 from share_anon_per_token scope (per-token middleware); got: {body}"
    )


def test_per_token_cap_fires_from_single_ip_when_per_token_lower(
    share_anon_client_low_per_token,
):
    """Even with single IP, per-token cap (5) catches before per-(token, IP) cap (100).

    AC5 composability: per-token cap distinct from per-(token, IP) cap.
    """
    c = share_anon_client_low_per_token
    for i in range(5):
        r = c.get("/api/share/token-x/files", headers={"X-Real-IP": "10.0.0.1"})
        assert r.status_code != 429, f"premature 429 at request {i + 1}: {r.text}"
    # 6th request — per-token cap exceeded (per-(token, IP) cap of 100 still has room)
    r = c.get("/api/share/token-x/files", headers={"X-Real-IP": "10.0.0.1"})
    assert r.status_code == 429
    body = r.json()
    assert body["scope"] == "share_anon_per_token", (
        f"expected 429 from share_anon_per_token middleware; got: {body}"
    )


# ---------------------------------------------------------------------------
# 4. Composability — both layers coexist, EITHER overage triggers 429
# ---------------------------------------------------------------------------


def test_both_middlewares_clean_passes(share_anon_client):
    """Normal traffic under BOTH caps: 200 (or 404 from router) response."""
    c = share_anon_client
    # 10 requests well under both default 60-caps
    for i in range(10):
        r = c.get("/api/share/normal-token/files")
        assert r.status_code != 429, f"clean request {i + 1} unexpectedly 429: {r.text}"


def test_per_token_cap_independent_of_per_ip_cap_scopes(share_anon_client_low_per_token):
    """When per-token fires, response scope identifies which middleware.

    Crucial for operator triage: the 429 response body's ``scope`` field
    tells which layer caught the overage (share_anon vs share_anon_per_token).
    """
    c = share_anon_client_low_per_token
    # Saturate per-token bucket from one IP (5 requests, well under per-IP cap of 100)
    for _ in range(5):
        c.get("/api/share/tok-z/files", headers={"X-Real-IP": "10.0.0.1"})
    r = c.get("/api/share/tok-z/files", headers={"X-Real-IP": "10.0.0.1"})
    assert r.status_code == 429
    assert r.json()["scope"] == "share_anon_per_token"
    # Different token from same IP → fresh bucket on per-token AND per-(token, IP) caps
    r2 = c.get("/api/share/different-tok/files", headers={"X-Real-IP": "10.0.0.1"})
    assert r2.status_code != 429


# ---------------------------------------------------------------------------
# 5. Retry-After header alignment with window_seconds
# ---------------------------------------------------------------------------


def test_per_token_retry_after_header_matches_window(share_anon_client_low_per_token):
    """Retry-After header value MUST equal ratelimit_share_per_token_window_seconds."""
    c = share_anon_client_low_per_token
    for _ in range(5):
        c.get("/api/share/header-test-tok/files")
    r = c.get("/api/share/header-test-tok/files")
    assert r.status_code == 429
    # Default window is 60s
    assert r.headers["Retry-After"] == "60"
    assert r.json()["retry_after_seconds"] == 60


# ---------------------------------------------------------------------------
# 6. Soft-alert threshold log emission
# ---------------------------------------------------------------------------


@pytest.fixture
def share_anon_client_soft_alert(monkeypatch, tmp_path):
    """Variant with per-token soft-alert threshold set to 3 (cap=5).

    Used to assert the WARNING log emission at exact-crossing — mirrors
    test_ratelimit_share_cap.py:test_member_10th_share_emits_soft_alert_log.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")
    monkeypatch.setenv("TOTP_FERNET_KEY", "ZmFrZS10ZXN0LWtleS0zMi1ieXRlcy1mb3ItdGVzdHM=")
    monkeypatch.setenv("RATELIMIT_SHARE_PER_TOKEN_THRESHOLD", "5")
    monkeypatch.setenv("RATELIMIT_SHARE_PER_TOKEN_SOFT_ALERT_THRESHOLD", "3")
    # Keep per-(token, IP) caps high so they don't interfere.
    monkeypatch.setenv("RATELIMIT_SHARE_ANON_THRESHOLD", "100")
    monkeypatch.setenv("RATELIMIT_SHARE_ANON_SOFT_ALERT_THRESHOLD", "100")

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


def test_per_token_soft_alert_emits_at_exact_threshold(
    share_anon_client_soft_alert, share_anon_caplog
):
    """3rd request triggers WARNING; 1st and 2nd do not."""
    c = share_anon_client_soft_alert
    for i in range(3):
        r = c.get("/api/share/alert-tok/files")
        assert r.status_code != 429, f"premature 429 at request {i + 1}"
    soft_records = [
        rec
        for rec in share_anon_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
        and rec.__dict__.get("labels.scope") == "share_anon_per_token"
    ]
    assert len(soft_records) == 1, (
        f"expected exactly 1 soft-alert record at count=3 from share_anon_per_token scope; "
        f"got {len(soft_records)}: {[r.__dict__ for r in soft_records]}"
    )
    rec = soft_records[0]
    assert rec.__dict__["labels.count"] == 3
    assert rec.__dict__["labels.threshold"] == 5
    assert rec.__dict__["labels.soft_alert_threshold"] == 3


def test_per_token_soft_alert_disabled_by_default(share_anon_client, share_anon_caplog):
    """Default config has soft_alert=None → ZERO records on app.share.ratelimit
    from the per-token middleware scope, even after 30 requests."""
    c = share_anon_client
    for _ in range(30):
        c.get("/api/share/default-tok/files")
    soft_records = [
        rec
        for rec in share_anon_caplog.records
        if rec.__dict__.get("event.action") == "share.ratelimit.soft_alert"
        and rec.__dict__.get("labels.scope") == "share_anon_per_token"
    ]
    assert soft_records == [], (
        f"per-token soft-alert should be disabled by default; got: {soft_records}"
    )


# ---------------------------------------------------------------------------
# 7. Module surface — exports stay backward-compatible
# ---------------------------------------------------------------------------


def test_ratelimit_module_exports_per_token_callables():
    """Per-token callables are exported alongside Story 19.1 callables."""
    from app.core.auth import ratelimit as rl

    assert callable(rl.share_anon_per_token_ratelimit_key)
    assert callable(rl.share_anon_per_token_retry_after_seconds)
    # Backward-compat: Story 19.1 callables still exported
    assert callable(rl.share_anon_ratelimit_key)
    assert callable(rl.share_anon_retry_after_seconds)
