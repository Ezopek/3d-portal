import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ShareToken(BaseModel):
    token: str
    model_id: uuid.UUID
    expires_at: datetime
    created_by: uuid.UUID
    created_at: datetime


class CreateShareRequest(BaseModel):
    model_id: uuid.UUID
    # Initiative 10 Story 16.3 — hard-cap TTL at 7 days per operator decision.
    # Pre-Init-10 cap was 30 days (24 * 30); narrowed to 7 days (24 * 7 = 168)
    # to limit anonymous-link lifetime per share-link-amplification security
    # posture. The frontend dialog exposes only 1d/3d/7d presets; this
    # backend constraint backstops any client that bypasses the dropdown.
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 7)


class CreateShareResponse(BaseModel):
    token: str
    url: str
    expires_at: datetime


class ShareModelView(BaseModel):
    """Subset projection returned to anonymous share visitors."""

    id: uuid.UUID
    name_en: str
    name_pl: str | None
    category: str
    tags: list[str]
    thumbnail_url: str | None
    has_3d: bool
    images: list[str]  # API-relative URLs for the gallery
    notes_en: str
    notes_pl: str
    stl_url: str | None = None
