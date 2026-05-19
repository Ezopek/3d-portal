"""Dual-backed (Redis + SQLite) invite-token service for Initiative 5.

Mirrors the Init 0 share-token shape in ``apps/api/app/modules/share/service.py``
with one structural addition: a DB row is the authoritative audit history,
Redis is the authoritative consumable-state cache. The two backings never
disagree because the consumption flow is validate-in-Redis -> DB UPDATE with
state predicate -> DEL Redis key, in that order.

Decision references (architecture.md § Initiative 5):
  - Decision A: dual-backed storage rationale + failure mode.
  - Decision B: token shape (32-byte entropy, Redis key, DB schema, TTL bounds).
  - Decision F: agent role is operator-bootstrapped only; invites must reject it.

Caller contract: audit emission (``auth.invite.generated`` / ``.used`` /
``.revoked``) is the caller's responsibility, mirroring the share-router
precedent in ``apps/api/app/modules/share/admin_router.py``.
"""

from __future__ import annotations

import datetime
import json
import secrets
import uuid

from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis
from sqlalchemy.engine import Engine
from sqlmodel import Session, update

from app.core.db.models._enums import UserRole
from app.modules.invite.models import InviteToken, hash_token

_KEY_PREFIX = "invite:token:"
_TTL_MIN_SECONDS = 60
_TTL_MAX_SECONDS = 7776000  # 90 days


class InviteServiceError(Exception):
    """Base class for all InviteService failures."""


class InviteNotFound(InviteServiceError):
    """Admin operation referenced an invite_id that does not exist."""


class InviteAlreadyResolved(InviteServiceError):
    """Admin revoke against an already-used or already-revoked invite."""


class InviteConsumed(InviteServiceError):
    """Public-facing: token is unusable.

    Covers consumed, revoked, expired, and never-existed states deliberately
    -- the consume path MUST surface these uniformly to prevent token-status
    enumeration attacks (FR5-INVITE-4 / Decision G brute-force margin).
    """


class GenerateInviteResult(BaseModel):
    """Return value of ``generate_invite()``.

    The ``token`` field is the cleartext URL-safe string and is the ONLY place
    cleartext ever leaves the service. Callers must surface it exactly once
    (admin-panel one-time generation response) and never persist or re-emit it.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    token: str
    invite: InviteToken


class ActiveInvite(BaseModel):
    """Lightweight view of a Redis-backed active invite.

    Reconstructed from the Redis JSON payload, never re-read from the DB --
    that is the AC-2 Redis-only guarantee.
    """

    model_config = ConfigDict(frozen=True)
    invite_id: uuid.UUID
    role: UserRole
    generated_by_user_id: uuid.UUID | None
    generated_at: datetime.datetime


class InviteService:
    """Dual-backed invite-token service. Constructor takes BOTH Redis + Engine."""

    def __init__(self, *, redis: Redis, engine: Engine) -> None:
        self._redis = redis
        self._engine = engine

    async def generate_invite(
        self,
        *,
        role: UserRole,
        ttl_seconds: int,
        generated_by_user_id: uuid.UUID | None,
    ) -> GenerateInviteResult:
        """Mint a new invite. DB INSERT first, then Redis SET.

        Caller is responsible for emitting the ``auth.invite.generated``
        audit event after this returns.

        If the Redis SET raises, the DB row stays as authoritative audit
        history -- the admin can revoke it from the panel. No compensating
        DB delete: a failing compensation could itself partially-fail.
        """
        if ttl_seconds < _TTL_MIN_SECONDS:
            raise ValueError(f"ttl_seconds must be >= {_TTL_MIN_SECONDS}")
        if ttl_seconds > _TTL_MAX_SECONDS:
            raise ValueError(f"ttl_seconds must be <= {_TTL_MAX_SECONDS}")
        if role not in (UserRole.member, UserRole.admin):
            raise ValueError("role must be member or admin")

        token = secrets.token_urlsafe(32)
        now = datetime.datetime.now(datetime.UTC)
        row = InviteToken(
            token_hash=hash_token(token),
            role=role.value,
            generated_by_user_id=generated_by_user_id,
            generated_at=now,
            ttl_seconds=ttl_seconds,
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

        payload = json.dumps(
            {
                "invite_id": str(row.id),
                "token_hash": row.token_hash,
                "role": row.role,
                "generated_by_user_id": (
                    str(row.generated_by_user_id) if row.generated_by_user_id else None
                ),
                "generated_at": row.generated_at.isoformat(),
            }
        )
        await self._redis.set(f"{_KEY_PREFIX}{token}", payload, ex=ttl_seconds)
        return GenerateInviteResult(token=token, invite=row)

    async def validate_active(self, token: str) -> ActiveInvite | None:
        """Redis-only O(1) lookup. NEVER touches the DB."""
        raw = await self._redis.get(f"{_KEY_PREFIX}{token}")
        if raw is None:
            return None
        payload = json.loads(raw)
        return ActiveInvite(
            invite_id=uuid.UUID(payload["invite_id"]),
            role=UserRole(payload["role"]),
            generated_by_user_id=(
                uuid.UUID(payload["generated_by_user_id"])
                if payload.get("generated_by_user_id")
                else None
            ),
            generated_at=datetime.datetime.fromisoformat(payload["generated_at"]),
        )

    async def consume(
        self,
        token: str,
        *,
        used_by_user_id: uuid.UUID,
        used_from_ip: str,
    ) -> InviteToken:
        """Single-use consumption with DB-side replay protection.

        Flow: validate_active (Redis GET) -> DB UPDATE with WHERE used_at IS NULL
        AND revoked_at IS NULL -> DEL Redis key. The DB row's predicate is the
        atomic guard; Redis is the hot-path cache, not the source of truth.

        Raises :class:`InviteConsumed` uniformly for never-existed / consumed /
        revoked / expired tokens (token-status enumeration protection).

        Caller is responsible for emitting the ``auth.invite.used`` audit event
        after this returns.
        """
        active = await self.validate_active(token)
        if active is None:
            raise InviteConsumed
        now = datetime.datetime.now(datetime.UTC)
        with Session(self._engine) as session:
            stmt = (
                update(InviteToken)
                .where(
                    InviteToken.id == active.invite_id,
                    InviteToken.used_at.is_(None),
                    InviteToken.revoked_at.is_(None),
                )
                .values(
                    used_by_user_id=used_by_user_id,
                    used_at=now,
                    used_from_ip=used_from_ip,
                )
            )
            result = session.exec(stmt)
            if result.rowcount == 0:
                # Redis said active, DB said no -- DB wins.
                raise InviteConsumed
            session.commit()
            updated = session.get(InviteToken, active.invite_id)
        await self._redis.delete(f"{_KEY_PREFIX}{token}")
        return updated

    async def revoke(self, invite_id: uuid.UUID) -> InviteToken:
        """Admin-initiated revocation by row id.

        DB UPDATE first (state authority), then Redis key DEL via SCAN+JSON
        match. An already-expired Redis key is benign.

        Caller is responsible for emitting the ``auth.invite.revoked`` audit
        event after this returns.
        """
        with Session(self._engine) as session:
            row = session.get(InviteToken, invite_id)
            if row is None:
                raise InviteNotFound
            if row.used_at is not None or row.revoked_at is not None:
                raise InviteAlreadyResolved
            row.revoked_at = datetime.datetime.now(datetime.UTC)
            session.add(row)
            session.commit()
            session.refresh(row)

        redis_key = await self._find_redis_key_for_invite(invite_id)
        if redis_key is not None:
            await self._redis.delete(redis_key)
        return row

    async def _find_redis_key_for_invite(self, invite_id: uuid.UUID) -> str | None:
        target = str(invite_id)
        async for key in self._redis.scan_iter(match=f"{_KEY_PREFIX}*"):
            raw = await self._redis.get(key)
            if raw is None:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if payload.get("invite_id") == target:
                return key.decode() if isinstance(key, bytes) else key
        return None
