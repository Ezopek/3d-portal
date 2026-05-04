"""Pre-Slice-1A legacy tables.

User has been migrated to UUID PK as part of Slice 1B. AuditEvent and the
ThumbnailOverride/RenderSelection set_by_user_id FKs follow the same UUID
convention. AuditEvent will be replaced by AuditLog in a follow-up task.
"""

import datetime
import uuid

from sqlmodel import Field, SQLModel

from ._enums import UserRole
from ._helpers import _now_utc, uuid_fk


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    kind: str = Field(index=True)
    payload: str


class ThumbnailOverride(SQLModel, table=True):
    __tablename__ = "thumbnailoverride"

    model_id: str = Field(primary_key=True)
    relative_path: str
    set_by_user_id: uuid.UUID = Field(
        sa_column=uuid_fk("user.id", ondelete="RESTRICT", nullable=False),
    )
    set_at: datetime.datetime = Field(default_factory=_now_utc)


class RenderSelection(SQLModel, table=True):
    __tablename__ = "renderselection"

    model_id: str = Field(primary_key=True)
    selected_paths: str  # JSON-encoded list[str], paths relative to model folder
    set_by_user_id: uuid.UUID = Field(
        sa_column=uuid_fk("user.id", ondelete="RESTRICT", nullable=False),
    )
    set_at: datetime.datetime = Field(default_factory=_now_utc)
