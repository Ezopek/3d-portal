"""SQLModel primitives for the Initiative 5 invite-token flow.

Story 6.1 ships the schema and helpers only. Subsequent stories add:

* ``service.py``      — dual-backed Redis SET + DB INSERT/consume flow (6.2).
* ``router.py``       — public ``/register?token=...`` consumer (6.4).
* ``admin_router.py`` — admin generate / list / revoke endpoints (6.3).

Decision A (architecture.md § Initiative 5) mirrors the Init 0 share-token
shape: Redis is the O(1) hot path, the DB row outlives the Redis TTL so
used + expired + revoked invites stay visible to the admin audit panel.
The schema matches migration 0012_invite_tokens 1:1; column-shape changes
must land in both files in lock-step.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from enum import IntEnum

from sqlalchemy import Column, Index
from sqlmodel import Field, SQLModel

from app.core.db.models._helpers import UTCDateTime, _now_utc, uuid_fk


class InviteTTLPreset(IntEnum):
    """Allowed TTL choices for admin-issued invites (Decision B)."""

    ONE_DAY = 86400
    THREE_DAYS = 259200
    SEVEN_DAYS = 604800
    THIRTY_DAYS = 2592000


class InviteToken(SQLModel, table=True):
    """Persistent row backing a Redis-cached invite token.

    The cleartext token never lives in this table — only its SHA-256 digest
    in ``token_hash``. ``role`` is a string mirror of ``UserRole`` (stored
    as text because ``UserRole`` is a ``StrEnum`` and SQLite carries it as
    a plain VARCHAR column already).
    """

    __tablename__ = "invite_tokens"
    __table_args__ = (
        Index("ux_invite_tokens_token_hash", "token_hash", unique=True),
        Index("ix_invite_tokens_generated_at", "generated_at"),
        Index("ix_invite_tokens_used_by_user_id", "used_by_user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    token_hash: str = Field(max_length=64)
    role: str = Field(max_length=16)
    generated_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    generated_at: datetime.datetime = Field(
        default_factory=_now_utc,
        sa_column=Column(UTCDateTime, nullable=False),
    )
    ttl_seconds: int
    used_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    used_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UTCDateTime, nullable=True),
    )
    used_from_ip: str | None = Field(default=None, max_length=45)
    revoked_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UTCDateTime, nullable=True),
    )


def hash_token(token: str) -> str:
    """Return the 64-char lowercase hex SHA-256 digest of ``token``.

    Decision B explicitly chose SHA-256 (not bcrypt) for invite tokens.
    The 256-bit entropy from ``secrets.token_urlsafe(32)`` combined with
    the rate-limit middleware in Decision G keeps the brute-force margin
    well inside NFR5-SEC-3 even with a fast hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
