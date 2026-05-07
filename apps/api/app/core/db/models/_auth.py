"""apps/api/app/core/db/models/_auth.py"""
import datetime
import uuid

from sqlmodel import Field, SQLModel

from ._helpers import uuid_fk


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=uuid_fk("user.id", ondelete="CASCADE", nullable=False),
    )
    family_id: uuid.UUID = Field(index=True)
    family_issued_at: datetime.datetime
    token_hash: str = Field(unique=True)
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    replaced_at: datetime.datetime | None = None
    replaced_by_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("refresh_tokens.id", ondelete="SET NULL", nullable=True),
    )
    revoked_at: datetime.datetime | None = None
    revoke_reason: str | None = None
    last_used_at: datetime.datetime | None = None
    ip: str | None = None
    user_agent: str | None = None
