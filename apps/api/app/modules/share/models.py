import uuid
from datetime import datetime
from typing import Literal

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


class ShareResolveResponse(BaseModel):
    """Initiative 18 Story 30.1 (Decision AA) — minimal projection for the
    authenticated share-resolve endpoint at GET /api/me/share-links/{token}/resolve.

    Exactly two fields. NO token-state fields (expires_at / revoked_at /
    created_by / token) per AC-11 enumeration-protection contract: the
    response is consumed by any authenticated user (not just the token's
    creator), so leaking creation/expiry metadata would enable a brute-force
    probe to infer token state from non-404 responses.

    The ``access`` field is forward-compat for B7 (future granular sharing):
    today it is always ``"granted"``; when granular sharing lands, B7
    callers without model access will receive ``access="request_needed"``
    plus a distinct response body shape that surfaces a request-access
    affordance. The literal type today blocks accidental introduction of
    other values without a deliberate schema change.
    """

    model_id: uuid.UUID
    access: Literal["granted"]


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
