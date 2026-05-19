"""User table.

The portal's authentication identity. UUID PK since Slice 1B; the legacy
int-id User was dropped at the 0005 migration. TOTP 2FA columns added
by Story 7.1 (migration 0013) — both NULL on the existing admin +
agent rows so the schema change is null-op for the service account
(NFR5-INT-1).
"""

import datetime
import uuid

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from ._enums import UserRole
from ._helpers import UTCDateTime, _now_utc


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str
    totp_secret: str | None = Field(default=None, max_length=255)
    totp_enabled_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UTCDateTime, nullable=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    last_login_at: datetime.datetime | None = None
