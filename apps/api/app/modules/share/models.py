import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ShareToken(BaseModel):
    token: str
    model_id: str
    expires_at: datetime
    created_by: uuid.UUID
    created_at: datetime


class CreateShareRequest(BaseModel):
    model_id: str
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class CreateShareResponse(BaseModel):
    token: str
    url: str
    expires_at: datetime


class ShareModelView(BaseModel):
    """Subset projection returned to anonymous share visitors."""

    id: str
    name_en: str
    name_pl: str
    category: str
    tags: list[str]
    thumbnail_url: str | None
    has_3d: bool
    images: list[str]  # API-relative URLs for the gallery
    notes_en: str
    notes_pl: str
    stl_url: str | None = None
