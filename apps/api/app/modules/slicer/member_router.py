"""Story 36.1 — member-accessible published print profile offer list.

``GET /api/profiles/offers/published`` — authenticated-member (``current_user``) access.
Returns the safe :class:`~app.modules.slicer.schemas.MemberPublishedOfferView` DTO for
each published offer. No admin capability; no admin offer API change; no DB/worker change.

Publish state is read from the on-disk offer sidecar (the ``publish_state`` field written
by PROFILE-PUBLISH-1). Only offers with ``publish_state == "published"`` are surfaced.

``quality_tier`` is derived from the process block's name (keyword match against
"aesthetic" / "standard" / "strong") and is ``null`` when the process block is unavailable.
``printer_name`` is read from the machine block manifest's ``name`` field and is ``null``
when the block is unavailable. Both nullable fields are documented in the Story 36.1
Dev Agent Record completion notes.

Source planning artifacts: architecture.md § Initiative 24 / Decision AT;
epics.md § Initiative 24 / Epic E36; Story 36.1.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.auth.dependencies import current_user
from app.core.config import get_settings
from app.modules.slicer.profile_library import read_block
from app.modules.slicer.profile_offer import list_offers
from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED
from app.modules.slicer.schemas import MemberPublishedOfferListResponse, MemberPublishedOfferView

router = APIRouter(prefix="/api/profiles/offers", tags=["profiles", "member"])

# Quality-tier keywords to match against process block names. Order is significant:
# checked left-to-right; first match wins. Lowercase comparison applied at match time.
_QUALITY_TIER_KEYWORDS: tuple[str, ...] = ("aesthetic", "standard", "strong")


def _normalize_material(raw: str | None) -> str | None:
    if raw is None:
        return None
    trimmed = raw.strip()
    return trimmed.upper() if trimmed else None


def _derive_quality_tier(process_manifest: dict | None) -> str | None:
    """Derive quality tier from the process block's portal_label or name, or None.

    The process block manifest carries no explicit ``quality_tier`` field (PROFILE-LIB-1
    design); the tier is inferred from the block's human name by keyword match. When the
    block is unavailable or the name contains no recognizable tier keyword, returns None.
    """
    if process_manifest is None:
        return None
    # Prefer portal_label (operator-assigned display label) over the raw block name.
    name = (process_manifest.get("portal_label") or process_manifest.get("name") or "").lower()
    for tier in _QUALITY_TIER_KEYWORDS:
        if tier in name:
            return tier
    return None


def _printer_name(machine_manifest: dict | None) -> str | None:
    """Read the printer name from the machine block manifest, or None."""
    if machine_manifest is None:
        return None
    name = machine_manifest.get("name")
    return name if isinstance(name, str) and name else None


@router.get(
    "/published",
    response_model=MemberPublishedOfferListResponse,
    summary="List published print profile offers (member view)",
    description=(
        "Story 36.1 — returns the safe member DTO for every published print profile offer. "
        "Only offers with publish_state=published and visibility=visible are included. "
        "Optional ?material=<key> filter (case-insensitive) restricts results by "
        "compatible_material_categories. "
        "Requires authentication (any role); anonymous requests return 401. "
        "Not in _PUBLIC_ROUTES; covered by the Story 11.4 route-enforcement gate."
    ),
)
async def list_published_offers(
    material: Annotated[
        str | None,
        Query(description="Filter by compatible material category (e.g. PLA). Case-insensitive."),
    ] = None,
    _user_id: uuid.UUID = current_user,
) -> MemberPublishedOfferListResponse:
    settings = get_settings()
    root = settings.slicer_vendored_profiles_dir

    all_sidecars = list_offers(root)

    # Filter to member-visible published offers only. Hidden published offers are
    # admin/internal and must not reach the member catalog surface.
    published = [
        s
        for s in all_sidecars
        if s.get("publish_state") == PUBLISH_STATE_PUBLISHED and s.get("visibility") == "visible"
    ]

    # Optional material filter — normalize to uppercase to match stored categories (AC-8).
    if material is not None:
        normalized = _normalize_material(material)
        if normalized is None:
            published = []
        else:
            published = [
                s
                for s in published
                if normalized in (s.get("compatible_material_categories") or [])
            ]

    items: list[MemberPublishedOfferView] = []
    for sidecar in published:
        chain = sidecar.get("chain") or {}
        machine_block_id = chain.get("machine_block_id")
        process_block_id = chain.get("process_block_id")

        # Read library blocks to derive safe display fields. Missing blocks produce None
        # (an offer stays listed once published; chain invalidity does not de-list it here).
        machine_manifest = (
            read_block(root, machine_block_id)
            if isinstance(machine_block_id, str) and machine_block_id
            else None
        )
        process_manifest = (
            read_block(root, process_block_id)
            if isinstance(process_block_id, str) and process_block_id
            else None
        )

        items.append(
            MemberPublishedOfferView(
                offer_id=sidecar["offer_id"],
                # Sidecar field is "label"; member DTO exposes it as "portal_label" (Story 36.1).
                portal_label=sidecar.get("label", ""),
                quality_tier=_derive_quality_tier(process_manifest),
                compatible_material_categories=list(
                    sidecar.get("compatible_material_categories") or []
                ),
                printer_name=_printer_name(machine_manifest),
                is_default=bool(sidecar.get("is_default", False)),
            )
        )

    return MemberPublishedOfferListResponse(offers=items)
