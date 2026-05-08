"""apps/api/app/core/db/models/_auth.py"""
import datetime
import uuid

from sqlalchemy import Column, Index, text
from sqlmodel import Field, SQLModel

from ._helpers import UTCDateTime, uuid_fk


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        # Partial unique index: at most one active (non-revoked) token per family.
        # Prevents concurrent rotations from inserting two active rows for the same family.
        # The sqlite_where clause makes this a partial index on SQLite; on PostgreSQL
        # add postgresql_where=text("revoked_at IS NULL") when migrating.
        Index(
            "ux_refresh_tokens_family_active",
            "family_id",
            unique=True,
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=uuid_fk("user.id", ondelete="CASCADE", nullable=False),
    )
    family_id: uuid.UUID = Field(index=True)
    family_issued_at: datetime.datetime = Field(sa_column=Column(UTCDateTime, nullable=False))
    token_hash: str = Field(unique=True)
    issued_at: datetime.datetime = Field(sa_column=Column(UTCDateTime, nullable=False))
    expires_at: datetime.datetime = Field(sa_column=Column(UTCDateTime, nullable=False))
    replaced_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))
    replaced_by_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("refresh_tokens.id", ondelete="SET NULL", nullable=True),
    )
    revoked_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))
    revoke_reason: str | None = None
    last_used_at: datetime.datetime | None = Field(default=None, sa_column=Column(UTCDateTime, nullable=True))
    ip: str | None = None
    user_agent: str | None = None
