"""Legacy tables — string `model_id` referencing the file-based catalog.

`ThumbnailOverride` and `RenderSelection` reference models by their legacy
3-digit string ID (`"001"`, `"002"`, ...) drawn from the file-based
`_index/index.json` catalog. They will be migrated to UUID FKs into the
new `model` table at the cutover slice; until then they live here as
"genuinely legacy" surfaces.

User and AuditLog used to live in this module too — Slice 1B's polish
moved them to dedicated modules (`_user.py`, `_audit.py`).
"""

import datetime
import uuid

from sqlmodel import Field, SQLModel

from ._helpers import _now_utc, uuid_fk


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
