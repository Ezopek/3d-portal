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
from typing import TYPE_CHECKING

import redis.exceptions
from fastapi import Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

_LOG = logging.getLogger("app.auth.ratelimit")


def _client_ip(request: Request) -> str:
    """Return the trusted client IP for per-IP rate-limit bucketing.

    Trust chain (production): browser → edge nginx → web nginx → API.
      - Edge nginx (``configs/nginx/3d.ezop.ddns.net.conf``) sets
        ``X-Real-IP $remote_addr`` from the TLS-terminating socket, which the
        attacker cannot forge across the proxy hop.
      - Web nginx (``apps/web/nginx.conf`` ``/api/`` block) forwards the value
        verbatim via ``X-Real-IP $http_x_real_ip`` (Story 6.6 codex fix-up #2 —
        the earlier ``$remote_addr`` form here overwrote the edge-set value with
        the docker-network IP and collapsed every HTTPS client into one bucket).

    Resolution order:
      1. ``X-Real-IP`` — trusted across the chain when both proxies cooperate.
      2. Left-most entry of ``X-Forwarded-For`` — canonical original-client
         position. Safe under the trust assumption that the proxy chain
         *appends* to the list (nginx ``$proxy_add_x_forwarded_for`` does so)
         and that direct attacker traffic cannot reach the API: the edge nginx
         is the only public-facing surface, internal Docker networking shields
         everything else. This branch is exercised only when X-Real-IP is
         absent (dev fixtures, debugging, or a proxy misconfiguration).
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
    if request.method == "POST" and request.url.path == "/api/auth/login":
        return f"ip:{_client_ip(request)}"
    return None


def refresh_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/refresh":
        return f"ip:{_client_ip(request)}"
    return None


def register_ratelimit_key(request: Request) -> str | None:
    if request.method == "POST" and request.url.path == "/api/auth/register":
        return f"ip:{_client_ip(request)}"
    return None


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
    ) -> None:
        self.app = app
        self.scope_name = scope
        self.key_fn = key_fn
        self.window_seconds = window_seconds
        self.threshold = threshold

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

        if count > self.threshold:
            response = JSONResponse(
                {
                    "detail": "rate_limited",
                    "scope": self.scope_name,
                    "retry_after_seconds": self.window_seconds,
                },
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
