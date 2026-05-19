"""Recovery-code table for Initiative 5 / Epic 7 TOTP 2FA.

Architecture Decision E (architecture.md §1515-1533): eight single-use
recovery codes generated as a batch at TOTP enrollment, stored as
bcrypt hashes (defense-in-depth on DB compromise — 32-bit code entropy
times bcrypt cost 12 yields >=10^9 years average crack time per code), with
per-code lifecycle columns so the audit history can answer "which
code did Anna consume on 2026-06-12?" and the regenerate-flow (Story
7.5) can invalidate a whole batch via one UPDATE.

Story 7.1 ships the schema + model only. Subsequent stories add:

* ``apps/api/app/modules/auth/totp/service.py`` — batch generation +
  Fernet encrypt helpers (Story 7.2).
* ``apps/api/app/modules/auth/totp/router.py`` — ``/api/auth/2fa/enroll``
  + ``/api/auth/2fa/enroll/confirm`` + ``/api/auth/2fa/verify`` endpoints
  (Stories 7.2 + 7.3).
* ``apps/api/app/modules/auth/totp/regenerate_router.py`` — ``/api/auth/
  2fa/recovery-codes/regenerate`` + ``/api/auth/2fa/disable`` (Story 7.5).

The cleartext code never lives in this table — only its bcrypt digest
in ``code_hash``. ``batch_id`` is a UUID generated at enrollment time
and shared across the 8 codes of one generation cycle. The schema
matches migration 0013_users_2fa_columns 1:1; column-shape changes
must land in both files in lock-step (same Story 6.1 invite_tokens
precedent).
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Column, Index
from sqlmodel import Field, SQLModel

from ._helpers import UTCDateTime, _now_utc, uuid_fk


class RecoveryCode(SQLModel, table=True):
    """One single-use TOTP recovery code, bcrypt-hashed at rest."""

    __tablename__ = "recovery_codes"
    __table_args__ = (
        Index("ix_recovery_codes_user_id", "user_id"),
        Index("ix_recovery_codes_batch_id", "batch_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=uuid_fk("user.id", ondelete="CASCADE", nullable=False),
    )
    code_hash: str = Field(max_length=60)
    batch_id: uuid.UUID
    generated_at: datetime.datetime = Field(
        default_factory=_now_utc,
        sa_column=Column(UTCDateTime, nullable=False),
    )
    used_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UTCDateTime, nullable=True),
    )
    invalidated_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UTCDateTime, nullable=True),
    )
