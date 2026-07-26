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


class TagGroup(SQLModel, table=True):
    __tablename__ = "tag_group"
    __table_args__ = (
        # Explicit index name so the ORM name matches the alembic migration
        # 41.2 will create (op.create_index("uq_tag_group_slug", ...)) —
        # Field(index=True) would auto-name it ix_tag_group_slug and drift.
        Index("uq_tag_group_slug", "slug", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str
    name_en: str
    name_pl: str | None = None
    position: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name_en: str
    name_pl: str | None = None
    group_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("tag_group.id", ondelete="SET NULL", nullable=True),
    )
    group_position: int = Field(default=0)
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


class BrowseCategory(SQLModel, table=True):
    """Initiative 26 browse category — a NEW entity, independent of the retired
    Initiative 25 single-category taxonomy (dropped by 0019_drop_category).

    Flat MVP with an optional ``parent_id``; the product depth-2 ceiling and
    self-cycle rejection are SERVICE-layer rules (Story 49.5), deliberately not
    expressed in DDL.
    """

    __tablename__ = "browse_category"
    __table_args__ = (
        # Explicit index name so the ORM name matches 0020_browse_categories
        # (op.create_index("uq_browse_category_slug", ...)). The reason is the
        # NAME, not the object count: Field(unique=True, index=True) — the
        # Tag.slug pattern above — folds into exactly ONE unique index and no
        # separate UNIQUE constraint (probed on SQLModel 0.0.38: Tag emits only
        # ix_tag_slug), but it auto-names that index ix_browse_category_slug and
        # so drifts against the migration. Follow TagGroup here, never Tag.
        Index("uq_browse_category_slug", "slug", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str
    name_en: str
    name_pl: str | None = None
    description_en: str | None = None
    description_pl: str | None = None
    inclusion_criterion: str | None = None
    position: int = Field(default=0)
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("browse_category.id", ondelete="RESTRICT", nullable=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelBrowseCategory(SQLModel, table=True):
    """M:N join between Model and BrowseCategory — the ModelTag shape verbatim.

    A Model may have ZERO categories and is fully valid (and public) in that
    state; nothing here makes a category mandatory.
    """

    __tablename__ = "model_browse_category"
    __table_args__ = (Index("ix_model_browse_category_cat_model", "category_id", "model_id"),)

    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", primary_key=True),
    )
    category_id: uuid.UUID = Field(
        sa_column=uuid_fk("browse_category.id", ondelete="RESTRICT", primary_key=True),
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
        # TB-008: backs the TB-004 `?external_url=<url>` filter on
        # GET /api/models. Without this index the subquery is a full
        # table scan — tolerable for low-thousands of rows, but not
        # under any bulk-import sweep. Non-unique because a given URL
        # can appear on multiple sources/models in pathological edge
        # cases (e.g. two distinct models pointing at the same source URL,
        # exercised by `test_list_models_external_url_combines_with_other_filters`).
        Index(
            "ix_model_external_link_url",
            "url",
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
    # Initiative 10 Story 16.1 (Decision L) — description-kind notes use
    # body_pl + body_en for bilingual content. body remains as the legacy
    # column for non-description note kinds (print_settings etc.) and as a
    # backward-compat mirror on description rows (frontend prefers
    # body_pl/body_en, falls back to body when both are null).
    body: str
    body_pl: str | None = Field(default=None)
    body_en: str | None = Field(default=None)
    author_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("user.id", ondelete="SET NULL", nullable=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)
