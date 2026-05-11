"""Read-side response schemas for the SoT entity tables.

These Pydantic models shape the JSON responses for /api/categories,
/api/tags, /api/models[/{id}[/files]]. They use `from_attributes=True`
so they can be built directly from SQLModel rows.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategorySummary(_OrmBase):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    slug: str
    name_en: str
    name_pl: str | None


class CategoryNode(CategorySummary):
    children: list["CategoryNode"]
    model_count: int = 0


class CategoryTree(BaseModel):
    roots: list[CategoryNode]


class TagRead(_OrmBase):
    id: uuid.UUID
    slug: str
    name_en: str
    name_pl: str | None


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
    category_id: uuid.UUID
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

    category: CategorySummary
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
