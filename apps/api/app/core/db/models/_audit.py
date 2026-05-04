"""Audit log table.

Records every mutation in the portal: who (actor_user_id) did what
(action) to which entity (entity_type + entity_id), with optional
before/after snapshots and a request_id for tracing.

`action` is free `text` in Slice 1B; will be tightened to a strict
enum in Slice 2 once the API mutation catalog is final. `entity_id`
is nullable because not every event ties to a specific entity (login
failures, catalog refresh, share-token operations on legacy string
model_ids).
"""

import datetime
import uuid

from sqlalchemy import Column, Index
from sqlmodel import Field, SQLModel

from ._helpers import _now_utc, sa_uuid_type, uuid_fk


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
