"""Request schemas for SoT admin write endpoints.

Kept separate from read-side schemas.py for symmetry — this module owns
everything the admin router accepts as input (body payloads).
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.db.models import ModelSource, ModelStatus


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
