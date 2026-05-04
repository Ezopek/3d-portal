"""Pre-Slice-1A legacy tables.

User, AuditEvent, ThumbnailOverride, RenderSelection were defined before the
catalog refactor. They are kept here untouched until Slice 1B migrates User
to UUID and replaces AuditEvent with the rich audit_log.
"""

import datetime

from sqlmodel import Field, SQLModel

from ._enums import UserRole
from ._helpers import _now_utc


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    last_login_at: datetime.datetime | None = None


class AuditEvent(SQLModel, table=True):
    __tablename__ = "auditevent"

    id: int | None = Field(default=None, primary_key=True)
    at: datetime.datetime = Field(default_factory=_now_utc, index=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id")
    kind: str = Field(index=True)
    payload: str


class ThumbnailOverride(SQLModel, table=True):
    __tablename__ = "thumbnailoverride"

    model_id: str = Field(primary_key=True)
    relative_path: str
    set_by_user_id: int = Field(foreign_key="user.id")
    set_at: datetime.datetime = Field(default_factory=_now_utc)


class RenderSelection(SQLModel, table=True):
    __tablename__ = "renderselection"

    model_id: str = Field(primary_key=True)
    selected_paths: str  # JSON-encoded list[str], paths relative to model folder
    set_by_user_id: int = Field(foreign_key="user.id")
    set_at: datetime.datetime = Field(default_factory=_now_utc)
