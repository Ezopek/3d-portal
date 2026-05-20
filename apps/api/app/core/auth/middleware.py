"""apps/api/app/core/auth/middleware.py — last-active throttled write middleware.

Redis-throttled writer for ``user.last_active_at`` that gates DB updates to
at most one per user per 5-minute window regardless of authenticated request
rate (NFR5-PERF-1 verbatim). Used by ``apps/api/app/main.py:create_app()``,
mounted LIFO-after the rate-limit + CSRF middleware install block so the
execution order is (outermost-to-innermost) CSRF → rate-limit trio →
last-active → handler.

Decision references (architecture.md § Initiative 5):
  - Decision I: column shape on ``user`` + ``SET NX EX 300`` throttle
    primitive + middleware module path. See architecture.md §1601-1630.

Caller contract: the middleware does NOT emit audit-log rows (the
``last_active_at`` column is a signal column, not a mutation tracked by
``audit.py``). The single side-effect on the happy path is the
``UPDATE user SET last_active_at = :now WHERE id = :user_id`` statement
when the per-user Redis throttle key is acquired; the single side-effect
on the Redis-down fail-soft path is the ``last_active.redis_unavailable``
warning log (GlitchTip ingests per NFR5-OBS-1). Request handling never
5xxs because of this middleware — every failure mode passes the request
through unchanged.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import TYPE_CHECKING

import redis.exceptions
import sqlalchemy as sa
from fastapi import Request

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.auth.jwt import TokenError, decode_token
from app.core.config import get_settings
from app.core.db.models._helpers import sa_uuid_type
from app.core.db.session import get_engine

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

_LOG = logging.getLogger("app.auth.last_active")

# matches Decision I + NFR5-PERF-1 verbatim (≤1 DB write per user per 5min,
# regardless of authenticated request rate). Hardcoded with no Settings knob —
# the throttle is a property of the audit/signal contract, not an operator
# tuning lever.
_LAST_ACTIVE_THROTTLE_SECONDS = 300

_REDIS_KEY_PREFIX = "last_active:"

# Roles that DO get the throttled last-active write. The ``agent`` role is a
# service account that posts ingestion every few minutes; if it shared the
# throttle namespace, its Redis key would always be present, but the DB
# column would still update once per 5min — that's correct but pollutes the
# per-user Redis namespace for no operator value (no admin panel surface
# shows agent last_active_at). Skipping ``agent`` is the minimum-surface
# choice per story §AC-3 step 3.
_TRACKED_ROLES: frozenset[str] = frozenset({"admin", "member"})


class LastActiveMiddleware:
    """ASGI middleware that throttles ``user.last_active_at`` updates.

    Behavior summary:
      1. Non-HTTP scope (websocket / lifespan) → pass through.
      2. Missing or invalid ``portal_access`` cookie → pass through.
      3. ``agent`` role (or any non-admin/member role) → pass through.
      4. ``app.state.redis`` missing (very-early startup window) → pass through.
      5. Redis ``SET NX EX 300`` returns True (key acquired) → execute the
         ``UPDATE user SET last_active_at = :now WHERE id = :user_id``
         statement after the response is yielded. Wrap in try/except + log;
         never let a write failure escape and 5xx the request.
      6. Redis ``SET NX EX 300`` returns False (another request already
         wrote within this window) → no DB call.
      7. Redis ``ConnectionError`` / ``TimeoutError`` / ``OSError`` →
         log ``last_active.redis_unavailable`` warning and pass through.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        token = request.cookies.get(ACCESS_COOKIE)
        if not token:
            await self.app(scope, receive, send)
            return

        try:
            claims = decode_token(token, secret=get_settings().jwt_secret)
        except TokenError:
            await self.app(scope, receive, send)
            return

        role = claims.get("role")
        if role not in _TRACKED_ROLES:
            await self.app(scope, receive, send)
            return

        try:
            user_id = uuid.UUID(str(claims["sub"]))
        except (KeyError, ValueError):
            await self.app(scope, receive, send)
            return

        # Defensive against the very-early startup window before ``lifespan()``
        # populates ``app.state.redis = RedisFactory(...)``. Pass through with
        # no log line — this is the legitimate dev / pytest startup window,
        # NOT a Redis outage.
        redis_factory = getattr(request.app.state, "redis", None)
        if redis_factory is None:
            await self.app(scope, receive, send)
            return

        redis_key = f"{_REDIS_KEY_PREFIX}{user_id}"
        now = datetime.datetime.now(datetime.UTC)
        acquired = False
        try:
            redis_client = redis_factory.get()
            acquired = bool(
                await redis_client.set(
                    redis_key,
                    now.isoformat().encode(),
                    nx=True,
                    ex=_LAST_ACTIVE_THROTTLE_SECONDS,
                )
            )
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, OSError) as exc:
            _LOG.warning(
                "last_active.redis_unavailable",
                extra={
                    "event.action": "last_active.redis_unavailable",
                    "labels.key": redis_key,
                    "error.message": str(exc),
                },
            )
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)

        if not acquired:
            return

        # Fire-and-forget DB write AFTER the response is yielded. The throttle
        # column is best-effort signal, not transactional state — wrap in
        # try/except + log a single warning so a DB hiccup never leaks back
        # as a 5xx (the response has already been sent to the client by now).
        try:
            engine = get_engine()
            stmt = sa.text("UPDATE user SET last_active_at = :now WHERE id = :user_id").bindparams(
                sa.bindparam("user_id", type_=sa_uuid_type())
            )
            with engine.begin() as conn:
                conn.execute(stmt, {"now": now, "user_id": user_id})
        except Exception as exc:
            _LOG.warning(
                "last_active.db_write_failed",
                extra={
                    "event.action": "last_active.db_write_failed",
                    "labels.key": redis_key,
                    "error.message": str(exc),
                },
            )
