"""apps/api/app/core/auth/ratelimit.py — sliding-window rate-limit middleware.

Redis-backed sliding window over a sorted set, one pipelined ``MULTI/EXEC``
round-trip per request. Used by ``apps/api/app/main.py:create_app()`` to mount
three middleware instances for ``login``, ``refresh``, and ``register`` scopes
(Initiative 5, Story 6.6; the fourth ``share`` scope is deferred to Story 6.7).

Decision references (architecture.md § Initiative 5):
  - Decision G: algorithm + module location + key shapes + threshold sourcing
    + middleware placement + Redis-down fail-soft semantics.

Caller contract: the middleware does NOT emit audit-log rows. The 429
response is the only side-effect on the rate-limit path; the
``ratelimit.redis_unavailable`` warning log is the only side-effect on the
fail-soft path. GlitchTip ingests the warning per NFR5-OBS-1.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import redis.exceptions
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import TokenError, decode_token
from app.core.config import get_settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

_LOG = logging.getLogger("app.auth.ratelimit")
_SHARE_LOG = logging.getLogger("app.share.ratelimit")


def _client_ip(request: Request) -> str:
    """Return the trusted client IP for per-IP rate-limit bucketing.

    Trust chain (production): browser → edge nginx → web nginx → API.
      - Edge nginx (``configs/nginx/3d.ezop.ddns.net.conf``) sets
        ``X-Real-IP $remote_addr`` from the TLS-terminating socket, which the
        attacker cannot forge across the proxy hop.
      - Web nginx (``apps/web/nginx.conf``) enforces the trust boundary via
        ``set_real_ip_from 192.168.2.180`` + ``real_ip_header X-Real-IP``
        (Story 6.6 codex fix-up #3). Only X-Real-IP from the edge nginx is
        trusted; direct callers reaching the exposed ``:8090`` port (operator
        curls on the LAN, dev tests) have their caller-supplied X-Real-IP
        discarded and ``$remote_addr`` used instead. The ``/api/`` block then
        propagates the now-sanitized ``$remote_addr`` as ``X-Real-IP`` to
        the API, so this helper sees a header it can trust at face value.

    Resolution order:
      1. ``X-Real-IP`` — trusted across the chain because nginx is the trust
         boundary upstream.
      2. Left-most entry of ``X-Forwarded-For`` — fallback for dev fixtures
         or proxy misconfigurations where X-Real-IP is absent. Direct-attacker
         traffic from outside cannot reach the API (web nginx is the only
         exposed surface), so the left-most-XFF assumption is safe.
      3. ``request.client.host`` — dev / direct-access path with no proxy.
    """
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        leftmost = xff.split(",", 1)[0].strip()
        if leftmost:
            return leftmost
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def login_ratelimit_key(request: Request) -> str | None:
    """Per-IP rate-limit key for the shared login / 2FA-verify /
    re-auth-gated endpoints (Story 7.3 + Story 7.5).

    All four paths share the same ``ratelimit:login:ip:{ip}`` 5-failures-
    per-60s budget per epics §1694 — second-factor failures and re-auth
    failures count against the same scope key as the password-login
    surface, so an attacker cannot spend their login budget then move to
    verify / regenerate / disable for fresh attempts.
    """
    if request.method == "POST" and request.url.path in {
        "/api/auth/login",
        "/api/auth/2fa/verify",
        "/api/auth/2fa/recovery-codes/regenerate",
        "/api/auth/2fa/disable",
    }:
        return f"ip:{_client_ip(request)}"
    return None


def refresh_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/refresh":
        return f"ip:{_client_ip(request)}"
    return None


def register_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path in {
        "/api/auth/register",
        "/api/auth/password-reset",
    }:
        return f"ip:{_client_ip(request)}"
    return None


def share_ratelimit_key(request: Request) -> str | None:
    """Per-member daily share-creation key + admin exemption (Decision H).

    Returns ``None`` for any non-POST / non-``/api/admin/share`` request,
    missing or invalid JWT, admin role (Decision H operator-self-DoS
    exemption), or non-member/non-admin roles (the auth dependency rejects
    those with 403). Returns ``user:{user_id}:day:{YYYY-MM-DD}`` (UTC day
    boundary — no DST math) for valid member requests, so the middleware's
    final Redis key is ``ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}``.

    The architecture's "single ``if user.role == Role.admin`` line" lives
    here, not inside ``RateLimitMiddleware.__call__`` — keeps the middleware
    class scope-agnostic and lets the key_fn short-circuit the Redis
    pipeline before the count is incremented.

    ``get_settings()`` is invoked at call time (not module import) so the
    ``monkeypatch.setenv + get_settings.cache_clear()`` test pattern picks
    up per-test overrides.
    """
    if request.method != "POST" or request.url.path != "/api/admin/share":
        return None
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        claims = decode_token(token, secret=get_settings().jwt_secret)
    except TokenError:
        return None
    role = claims.get("role")
    if role == "admin":
        return None
    if role != "member":
        return None
    user_id = claims.get("sub")
    if not user_id:
        return None
    today_utc = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"user:{user_id}:day:{today_utc}"


def share_retry_after_seconds() -> int:
    """Seconds remaining until the next UTC midnight (next day boundary).

    Clamps to a minimum of 1 to keep ``Retry-After: 0`` (which HTTP clients
    interpret as "retry immediately") out of the response — a microsecond
    race against the rollover would otherwise give us a non-positive value.
    """
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()), 1)


class RateLimitMiddleware:
    """Sliding-window rate-limit middleware (one Redis pipeline per request)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        scope: str,
        key_fn: Callable[[Request], str | None],
        window_seconds: int,
        threshold: int,
        soft_alert_threshold: int | None = None,
        retry_after_seconds_fn: Callable[[], int] | None = None,
    ) -> None:
        self.app = app
        self.scope_name = scope
        self.key_fn = key_fn
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.soft_alert_threshold = soft_alert_threshold
        self.retry_after_seconds_fn = retry_after_seconds_fn

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        key_suffix = self.key_fn(request)
        if key_suffix is None:
            await self.app(scope, receive, send)
            return

        redis_key = f"ratelimit:{self.scope_name}:{key_suffix}"
        now_ms = int(time.time() * 1000)
        window_ms = self.window_seconds * 1000

        try:
            redis_client = request.app.state.redis.get()
            # Member must be unique per request — multiple requests landing in
            # the same millisecond would otherwise be collapsed into one ZSET
            # entry (same score AND same member is a no-op ZADD), under-counting
            # the actual request rate. The score stays at now_ms for sliding-
            # window math; uuid suffix provides member uniqueness.
            member = f"{now_ms}-{uuid.uuid4().hex}"
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(redis_key, "-inf", now_ms - window_ms)
                pipe.zadd(redis_key, {member: now_ms})
                pipe.expire(redis_key, self.window_seconds + 1)
                pipe.zcard(redis_key)
                _, _, _, count = await pipe.execute()
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError) as exc:
            _LOG.warning(
                "ratelimit.redis_unavailable",
                extra={
                    "event.action": "ratelimit.redis_unavailable",
                    "labels.scope": self.scope_name,
                    "labels.key": redis_key,
                    "error.message": str(exc),
                },
            )
            await self.app(scope, receive, send)
            return

        if self.soft_alert_threshold is not None and count == self.soft_alert_threshold:
            _SHARE_LOG.warning(
                "share.ratelimit.soft_alert",
                extra={
                    "event.action": "share.ratelimit.soft_alert",
                    "labels.scope": self.scope_name,
                    "labels.key": redis_key,
                    "labels.count": count,
                    "labels.threshold": self.threshold,
                    "labels.soft_alert_threshold": self.soft_alert_threshold,
                },
            )

        if count > self.threshold:
            retry_after_seconds = (
                self.retry_after_seconds_fn()
                if self.retry_after_seconds_fn is not None
                else self.window_seconds
            )
            response = JSONResponse(
                {
                    "detail": "rate_limited",
                    "scope": self.scope_name,
                    "retry_after_seconds": retry_after_seconds,
                },
                status_code=429,
                headers={"Retry-After": str(retry_after_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
