import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.db.models._enums import ModelFileKind


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
    # Initiative 12 Story 19.7 round-2 (Codex P2) — byte size of the STL
    # surfaced via stl_url. Anonymous viewer uses it to fire the >50 MB
    # large-mesh confirm dialog before parsing. None when no STL exists or
    # when the backend can't determine the size — the gate then skips.
    stl_size_bytes: int | None = None


# Initiative 12 Story 19.4 (Decision T) — anonymous share file list endpoint.


class ShareFileListEntry(BaseModel):
    """One file row in the anonymous share view file list response.

    Mirrors the admin SoT ModelFile shape but with a pre-formatted
    share-scoped ``content_url`` (Init 6 Decision N pattern) so the
    anonymous SPA does not need to construct the URL itself. Only kinds
    in ``_SHARE_ALLOWED_KINDS`` ({image, print, stl}; plus stl_preview
    after Story 19.6) are surfaced; source / archive_3mf are filtered out
    server-side.
    """

    id: str
    kind: ModelFileKind
    original_name: str
    mime_type: str
    size_bytes: int
    position: int | None
    content_url: str  # share-scoped: /api/share/{token}/files/{file_id}/content
    created_at: datetime


class PaginatedShareFileList(BaseModel):
    items: list[ShareFileListEntry]
    total: int
    page: int
    page_size: int
