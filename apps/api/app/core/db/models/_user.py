"""User table.

The portal's authentication identity. UUID PK since Slice 1B; the legacy
int-id User was dropped at the 0005 migration.
"""

import datetime
import uuid

from sqlmodel import Field, SQLModel

from ._enums import UserRole
from ._helpers import _now_utc


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    last_login_at: datetime.datetime | None = None
