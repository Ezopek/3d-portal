"""Pre-Slice-1A legacy tables.

User has been migrated to UUID PK as part of Slice 1B. AuditEvent has been
replaced by AuditLog (rich schema) in Slice 1B Task 3.
"""

import datetime
import uuid

from sqlalchemy import Column, Index
from sqlmodel import Field, SQLModel

from ._enums import UserRole
from ._helpers import _now_utc, sa_uuid_type, uuid_fk


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    last_login_at: datetime.datetime | None = None


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id", "at"),
        Index("ix_audit_log_actor", "actor_user_id", "at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    action: str = Field(index=True)
    entity_type: str
    entity_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(sa_uuid_type(), nullable=True),
    )
    before_json: str | None = None
    after_json: str | None = None
    request_id: str | None = None
    at: datetime.datetime = Field(default_factory=_now_utc, index=True)


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
