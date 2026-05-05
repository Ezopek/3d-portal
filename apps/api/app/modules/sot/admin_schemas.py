"""Request schemas for SoT admin write endpoints.

Kept separate from read-side schemas.py for symmetry — this module owns
everything the admin router accepts as input (body payloads).
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.db.models import ExternalSource, ModelFileKind, ModelSource, ModelStatus, NoteKind


class ModelCreate(BaseModel):
    name_en: str = Field(min_length=1)
    name_pl: str | None = None
    category_id: uuid.UUID
    source: ModelSource = ModelSource.unknown
    status: ModelStatus = ModelStatus.not_printed
    rating: float | None = Field(default=None, ge=1.0, le=5.0)
    slug: str | None = None


class ModelPatch(BaseModel):
    """All fields optional.  Extra keys rejected to catch caller typos."""

    model_config = ConfigDict(extra="forbid")

    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None
    category_id: uuid.UUID | None = None
    source: ModelSource | None = None
    status: ModelStatus | None = None
    rating: float | None = Field(default=None, ge=1.0, le=5.0)
    slug: str | None = None


class ThumbnailSet(BaseModel):
    file_id: uuid.UUID


class PhotoReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID]


class RenderRequest(BaseModel):
    """Optional STL selection for the render job. Empty = worker picks the first STL."""

    selected_stl_file_ids: list[uuid.UUID] = Field(default_factory=list)


class ModelFilePatch(BaseModel):
    """Updateable fields for a ModelFile.  Content-tied fields (storage_path,
    sha256, size_bytes, mime_type) are intentionally excluded — replace the
    binary via DELETE + POST upload instead."""

    model_config = ConfigDict(extra="forbid")

    kind: ModelFileKind | None = None
    original_name: str | None = Field(default=None, min_length=1)


# ---------------------------------------------------------------------------
# Tags M2M
# ---------------------------------------------------------------------------


class TagsReplace(BaseModel):
    tag_ids: list[uuid.UUID]


class TagAdd(BaseModel):
    tag_id: uuid.UUID


# ---------------------------------------------------------------------------
# Tags global
# ---------------------------------------------------------------------------


class TagCreate(BaseModel):
    slug: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    name_pl: str | None = None


class TagPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str | None = Field(default=None, min_length=1)
    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None


class TagMerge(BaseModel):
    from_id: uuid.UUID
    to_id: uuid.UUID


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    parent_id: uuid.UUID | None = None
    slug: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    name_pl: str | None = None


class CategoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: uuid.UUID | None = None
    slug: str | None = Field(default=None, min_length=1)
    name_en: str | None = Field(default=None, min_length=1)
    name_pl: str | None = None


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class NoteCreate(BaseModel):
    kind: NoteKind
    body: str = Field(min_length=1)


class NotePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: NoteKind | None = None
    body: str | None = Field(default=None, min_length=1)


# ---------------------------------------------------------------------------
# Prints
# ---------------------------------------------------------------------------


class PrintCreate(BaseModel):
    printed_at: datetime.date | None = None
    note: str | None = None
    photo_file_id: uuid.UUID | None = None


class PrintPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    printed_at: datetime.date | None = None
    note: str | None = None
    photo_file_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------


class ExternalLinkCreate(BaseModel):
    source: ExternalSource
    external_id: str | None = None
    url: str = Field(min_length=1)


class ExternalLinkPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: ExternalSource | None = None
    external_id: str | None = None
    url: str | None = Field(default=None, min_length=1)
