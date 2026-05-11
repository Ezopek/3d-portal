"""Slice 1A entity tables: catalog model and its relations.

These are the new SoT tables for the 3D model catalog. UUID PKs throughout,
soft delete on Model, audit_log integration deferred to Slice 1B.
"""

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Index,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from ._enums import (
    ExternalSource,
    ModelFileKind,
    ModelSource,
    ModelStatus,
    NoteKind,
)
from ._helpers import _now_utc, uuid_fk


class Category(SQLModel, table=True):
    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),
        # NULL != NULL in SQL, so the composite constraint above won't catch two
        # root categories (parent_id IS NULL) with the same slug.  A partial
        # unique index on slug WHERE parent_id IS NULL covers that case on both
        # SQLite (3.9+) and Postgres.
        Index(
            "uq_category_root_slug",
            "slug",
            unique=True,
            sqlite_where=Column("parent_id").is_(None),
            postgresql_where=Column("parent_id").is_(None),
        ),
        # Named to match the alembic migration (ix_category_parent), which
        # differs from the SQLModel auto-generated name (ix_category_parent_id).
        Index("ix_category_parent", "parent_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=True),
    )
    slug: str = Field(index=True)
    name_en: str
    name_pl: str | None = None
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name_en: str
    name_pl: str | None = None
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class Model(SQLModel, table=True):
    __tablename__ = "model"
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1.0 AND 5.0)",
            name="ck_model_rating_range",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name_en: str
    name_pl: str | None = None
    category_id: uuid.UUID = Field(
        sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=False, index=True),
    )
    source: ModelSource = Field(default=ModelSource.unknown)
    status: ModelStatus = Field(default=ModelStatus.not_printed, index=True)
    rating: float | None = None
    date_added: datetime.date = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).date()
    )
    deleted_at: datetime.datetime | None = Field(default=None, index=True)
    thumbnail_file_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("model_file.id", ondelete="SET NULL", nullable=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelFile(SQLModel, table=True):
    __tablename__ = "model_file"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "sha256",
            "kind",
            name="uq_model_file_model_sha_kind",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", nullable=False, index=True),
    )
    kind: ModelFileKind
    original_name: str
    storage_path: str = Field(unique=True)
    sha256: str = Field(index=True)
    size_bytes: int = Field(sa_column=Column(BigInteger(), nullable=False))
    mime_type: str
    position: int | None = Field(default=None, nullable=True, index=False)
    selected_for_render: bool = Field(default=False, nullable=False)
    created_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelTag(SQLModel, table=True):
    __tablename__ = "model_tag"
    __table_args__ = (Index("ix_model_tag_tag_model", "tag_id", "model_id"),)

    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", primary_key=True),
    )
    tag_id: uuid.UUID = Field(
        sa_column=uuid_fk("tag.id", ondelete="RESTRICT", primary_key=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelPrint(SQLModel, table=True):
    __tablename__ = "model_print"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", nullable=False, index=True),
    )
    photo_file_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("model_file.id", ondelete="SET NULL", nullable=True),
    )
    printed_at: datetime.date | None = None
    note: str | None = None
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelExternalLink(SQLModel, table=True):
    __tablename__ = "model_external_link"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "source",
            name="uq_model_external_link_model_source",
        ),
        Index(
            "ix_model_external_lookup",
            "source",
            "external_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", nullable=False),
    )
    source: ExternalSource
    external_id: str | None = None
    url: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelNote(SQLModel, table=True):
    __tablename__ = "model_note"
    __table_args__ = (Index("ix_model_note_model_kind", "model_id", "kind"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", nullable=False),
    )
    kind: NoteKind
    body: str
    author_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)
