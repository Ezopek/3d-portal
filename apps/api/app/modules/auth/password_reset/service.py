"""Redis-only single-use opaque-token service for admin-issued password resets.

Story 8.5: implements the Redis-side primitive consumed by the new
``apps/api/app/modules/auth/password_reset/`` admin-mint + public-consume
endpoints. Mirrors the Story 6.2 invite-token shape (Decision A + B) but
WITHOUT the dual DB-row backing — Redis is the SOLE state surface per
epics §1814 verbatim ("NO DB-row audit history is needed at the
password-reset-link tier — ``auth.password.reset.initiated`` audit row
captures issuance; ``auth.password.reset.completed`` captures consumption").

Token shape (matches invite-token primitive verbatim):
  - 256-bit URL-safe entropy via ``secrets.token_urlsafe(32)`` (43 chars).
  - Redis key ``invite:reset:{token}`` — the shared ``invite:`` namespace is
    deliberate (epics §1814 verbatim "stores at Redis key
    ``invite:reset:{token}``") and keeps the auth-token-namespace
    conceptually unified with invite-token + partial-auth-token primitives.
  - JSON payload ``{user_id, generated_by_user_id, generated_at}``.

Atomicity contract:
  ``claim()`` issues ``GETDEL`` (Redis 6.2+) — a single indivisible op under
  Redis's single-threaded model. Mirrors ``auth/totp/router.py:369`` verbatim;
  two concurrent ``claim(token)`` calls with the same token can never both
  succeed because at most one observes a non-None value.

Caller contract: audit emission (``auth.password.reset.initiated`` /
``auth.password.reset.completed``) is the caller's responsibility, mirroring
the invite/service.py convention.
"""

from __future__ import annotations

import datetime
import json
import secrets
import uuid

from redis.asyncio import Redis

_KEY_PREFIX = "invite:reset:"
_TTL_MIN_SECONDS = 60
_TTL_MAX_SECONDS = 86400  # 24h ceiling (Settings.password_reset_ttl_seconds.le)


class PasswordResetService:
    """Redis-only single-use opaque-token service."""

    def __init__(self, *, redis: Redis) -> None:
        self._redis = redis

    async def generate(
        self,
        *,
        user_id: uuid.UUID,
        generated_by_user_id: uuid.UUID,
        ttl_seconds: int,
    ) -> str:
        """Mint a fresh single-use reset token and stash it in Redis with TTL.

        The cleartext token returned here is the ONLY place cleartext leaves
        the service. Callers must surface it exactly once (admin-panel
        one-time mint response) and never persist or re-emit it.
        """
        if ttl_seconds < _TTL_MIN_SECONDS:
            raise ValueError(f"ttl_seconds must be >= {_TTL_MIN_SECONDS}")
        if ttl_seconds > _TTL_MAX_SECONDS:
            raise ValueError(f"ttl_seconds must be <= {_TTL_MAX_SECONDS}")

        token = secrets.token_urlsafe(32)
        payload = json.dumps(
            {
                "user_id": str(user_id),
                "generated_by_user_id": str(generated_by_user_id),
                "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
        )
        await self._redis.set(f"{_KEY_PREFIX}{token}", payload, ex=ttl_seconds)
        return token

    async def claim(self, token: str) -> uuid.UUID | None:
        """Atomic single-use claim via ``GETDEL``.

        Returns the bound ``user_id`` on hit. Returns ``None`` uniformly for
        never-existed / expired / already-claimed tokens — the Redis-only
        state surface cannot distinguish them post-GETDEL, which is the
        deliberate token-status-enumeration protection per the Story 6.4
        ``invite/service.py:54-57`` verbatim convention.
        """
        key = f"{_KEY_PREFIX}{token}"
        raw = await self._redis.execute_command("GETDEL", key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        payload = json.loads(raw)
        return uuid.UUID(payload["user_id"])
