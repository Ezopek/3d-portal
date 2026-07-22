"""Read-side response schemas for the SoT entity tables.

These Pydantic models shape the JSON responses for /api/tags,
/api/models[/{id}[/files]]. They use `from_attributes=True`
so they can be built directly from SQLModel rows.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, model_serializer


class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TagRead(_OrmBase):
    id: uuid.UUID
    slug: str
    name_en: str
    name_pl: str | None
    # Initiative 25 (Story 42.2) — facet membership, read straight off the Tag
    # ORM columns (zero query cost via from_attributes). Additive: existing
    # consumers ignore the new keys, and because ModelSummary/ModelDetail embed
    # TagRead these two fields also appear on every model response (intended,
    # FR25-DETAIL-1). The human group label/slug is NOT embedded here — it is
    # delivered authoritatively by GET /api/tag-groups (D-SHAPE-1).
    group_id: uuid.UUID | None
    group_position: int


class TagListItem(TagRead):
    """Standalone GET /api/tags item — TagRead plus an OPT-IN model_count.

    Story 42.2 D-RESPONSEMODEL-1: model_count is present only when the caller
    passes ?with_counts=true. The wrap serializer drops the key when it is
    None so the count-free shape carries no model_count key, while genuine
    null fields (group_id / name_pl) are preserved. Declared with a concrete
    optional-int field (not response_model=None) so OpenAPI advertises an
    honest named component.
    """

    model_count: int | None = None

    @model_serializer(mode="wrap")
    def _drop_none_count(self, handler):
        data = handler(self)
        if data.get("model_count") is None:
            data.pop("model_count", None)
        return data


class TagReadWithCount(TagRead):
    """TagRead with a REQUIRED model_count — used by GET /api/tag-groups where
    the count is always computed (distinct from TagListItem's optional count)."""

    model_count: int


class TagGroupRead(_OrmBase):
    id: uuid.UUID
    slug: str
    name_en: str
    name_pl: str | None
    position: int
    tags: list[TagReadWithCount]


class TagGroupsResponse(BaseModel):
    groups: list[TagGroupRead]
    groupless: list[TagReadWithCount]


class TagGroupSummary(_OrmBase):
    """Flat write-response for the admin tag-group governance endpoints
    (Story 42.4). Does NOT embed `tags[]` — that is the read-side
    `TagGroupRead`'s job (GET /api/tag-groups)."""

    id: uuid.UUID
    slug: str
    name_en: str
    name_pl: str | None
    position: int


class ModelFileRead(_OrmBase):
    id: uuid.UUID
    model_id: uuid.UUID
    kind: str
    original_name: str
    storage_path: str
    sha256: str
    size_bytes: int
    mime_type: str
    position: int | None
    selected_for_render: bool
    created_at: datetime.datetime


class ExternalLinkRead(_OrmBase):
    id: uuid.UUID
    model_id: uuid.UUID
    source: str
    external_id: str | None
    url: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class NoteRead(_OrmBase):
    id: uuid.UUID
    model_id: uuid.UUID
    kind: str
    body: str
    # Initiative 10 Story 16.1 (Decision L) — bilingual description fields.
    # Null on non-description notes and on legacy description rows whose
    # backfill hasn't run; frontend falls back to `body` in either case.
    body_pl: str | None = None
    body_en: str | None = None
    author_id: uuid.UUID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class PrintRead(_OrmBase):
    id: uuid.UUID
    model_id: uuid.UUID
    photo_file_id: uuid.UUID | None
    printed_at: datetime.date | None
    note: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ModelSummary(_OrmBase):
    """Used in list responses; tags eagerly loaded, no other embeds."""

    id: uuid.UUID
    slug: str
    name_en: str
    name_pl: str | None
    source: str
    status: str
    rating: float | None
    thumbnail_file_id: uuid.UUID | None
    date_added: datetime.date
    deleted_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tags: list[TagRead]
    # Top up to 4 image/print files, ordered by (position NULLS LAST, created_at).
    gallery_file_ids: list[uuid.UUID]
    # Total image+print files for this model.
    image_count: int


class ModelDetail(ModelSummary):
    """Used in single-model GET; full embed of related entities."""

    files: list[ModelFileRead]
    prints: list[PrintRead]
    notes: list[NoteRead]
    external_links: list[ExternalLinkRead]


class ModelListResponse(BaseModel):
    items: list[ModelSummary]
    total: int
    offset: int
    limit: int


class FileListResponse(BaseModel):
    items: list[ModelFileRead]
