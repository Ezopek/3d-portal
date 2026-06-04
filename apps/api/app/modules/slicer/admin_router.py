"""Story 33.1 (PROFILE-ADMIN-1) — read-only admin profile inventory.

A single **admin-gated** ``GET /api/admin/profiles?printer_ref=<ref>`` endpoint that
enumerates every ``(material_class, quality_tier)`` slot over the named
``MATERIAL_CLASS_ORDER x QUALITY_TIER_ORDER`` grid and projects, per slot, whether it is
imported / resolvable / compatible, the single primary status by a fixed precedence, a
structured reason, and leak-fenced provenance (Decision AK).

Scope fence (AC-10 — read-only / deploy-clean): this router + the ``schemas.py`` DTOs +
``compatibility.py`` are the only new surfaces. It introduces NO write/upload/multipart
surface, NO on-disk write, NO ``config.py`` slot, NO Alembic migration, NO slicer-worker
change. ``resolvable`` REUSES the same ``resolve_preset`` seam that backs
``GET /api/estimates/quality-tiers`` (AC-5/AC-6 parity) — it does NOT re-derive resolution.

The route carries ``current_admin`` (a default-value ``Depends``), so the Init 6 / Story
11.4 route-enforcement gate recognises it WITHOUT any ``_PUBLIC_ROUTES`` edit (AC-2).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Protocol, runtime_checkable

from fastapi import APIRouter, Depends, Query, Request

from app.core.auth.dependencies import current_admin
from app.core.config import get_settings
from app.modules.slicer.compatibility import INCOMPATIBLE_REASON, is_compatible
from app.modules.slicer.estimate_read import (
    EstimateResolver,
    PresetResolveError,
    SettingsEstimateResolver,
)
from app.modules.slicer.models import MaterialClass, PrintIntentPreset, QualityTier
from app.modules.slicer.router import QUALITY_TIER_ORDER
from app.modules.slicer.schemas import (
    AdminProfileInventoryResponse,
    AdminProfileProvenance,
    AdminProfileSlot,
    AdminProfileStatus,
)

router = APIRouter(prefix="/api/admin", tags=["admin-profiles"])

# Inventory grid material axis, in resolver/UX order (PLA, PETG, PCTG, TPU). The companion
# tier axis is QUALITY_TIER_ORDER (reused from the estimates router so the two surfaces
# share one tier-order SoT). Together they are the named FE↔BE grid the FE mirrors.
MATERIAL_CLASS_ORDER: tuple[MaterialClass, ...] = ("PLA", "PETG", "PCTG", "TPU")

# Structured reason CATEGORIES for the two non-compatibility non-offerable statuses (the
# FE localizes them). `profile_not_imported` is byte-identical to the string
# `GET /api/estimates/quality-tiers` already emits, keeping the member/admin reason
# vocabulary aligned. `incompatible_for_material` lives in compatibility.py (the compat SoT).
NOT_IMPORTED_REASON = "profile_not_imported"
NOT_RESOLVABLE_REASON = "not_resolvable"


@runtime_checkable
class ProfileInventorySource(Protocol):
    """The read-only source seam the inventory depends on (overridable in tests).

    Satisfied by ``VendoredProfileSource``; a test fake can drive ``has_intent`` /
    ``system_tree_hash`` directly so the four statuses can be exercised without a real
    vendored tree on disk.
    """

    def has_intent(self, intent: PrintIntentPreset) -> bool: ...

    def system_tree_hash(self) -> str: ...


# === pure projection (shared SoT — unit-testable without HTTP) ================


def derive_status_and_reason(
    *, compatible: bool, imported: bool, resolvable: bool
) -> tuple[AdminProfileStatus, str | None]:
    """Map the three booleans to the single primary status + structured reason (AC-4).

    Fixed precedence (top wins): Incompatible → Not imported → Not resolvable → Offerable.
    ``compatible`` is evaluated FIRST and INDEPENDENTLY of import/resolve, so a
    resolvable-but-incompatible slot reads ``incompatible`` (never "available"). Every
    non-offerable status carries a non-null category whose name matches the status.
    """
    if not compatible:
        return "incompatible", INCOMPATIBLE_REASON
    if not imported:
        return "not_imported", NOT_IMPORTED_REASON
    if not resolvable:
        return "not_resolvable", NOT_RESOLVABLE_REASON
    return "offerable", None


def build_slot(
    material_class: MaterialClass,
    quality_tier: QualityTier,
    *,
    imported: bool,
    resolvable: bool,
    provenance: AdminProfileProvenance,
) -> AdminProfileSlot:
    """Build one inventory slot from the per-dimension facts (the shared per-slot SoT).

    ``compatible`` comes from the compatibility SoT (``compatibility.py``); ``offerable``
    is the load-bearing conjunction; status/reason follow the AC-4 precedence.
    ``portal_label`` is reserved for the Story 33.3 operator label store (``None`` here).
    Both the admin grid and the member-selector projection derive from THIS function, so a
    single test can assert neither surface offers an incompatible slot (AC-8).
    """
    compatible = is_compatible(material_class, quality_tier)
    offerable = imported and resolvable and compatible
    status, reason = derive_status_and_reason(
        compatible=compatible, imported=imported, resolvable=resolvable
    )
    return AdminProfileSlot(
        material_class=material_class,
        quality_tier=quality_tier,
        imported=imported,
        resolvable=resolvable,
        compatible=compatible,
        offerable=offerable,
        status=status,
        reason=reason,
        portal_label=None,
        provenance=provenance,
    )


def member_selector_tiers(
    slots: list[AdminProfileSlot],
) -> dict[MaterialClass, list[dict[str, object]]]:
    """Project the inventory onto the member-selector availability (AC-8, the shared SoT).

    Mirrors the FE hybrid: **incompatible** tiers are HIDDEN (omitted entirely — never
    teased); **compatible** tiers are surfaced with an ``available`` flag (``available ==
    offerable``) so the FE can disable-with-explanation the compatible-but-unavailable ones.
    The shared test asserts this projection NEVER surfaces an incompatible
    ``(material_class, quality_tier)`` — the structural guard against the admin grid and
    the member selector drifting (FR21-COMPAT-1 verifiable clause, NFR21-NO-422-1).
    """
    projection: dict[MaterialClass, list[dict[str, object]]] = {}
    for slot in slots:
        if not slot.compatible:
            continue  # incompatible → hidden from the member surface
        projection.setdefault(slot.material_class, []).append(
            {"quality_tier": slot.quality_tier, "available": slot.offerable}
        )
    return projection


# === DI seams (overridable in tests) =========================================


def get_admin_profile_resolver(request: Request) -> EstimateResolver:
    """The production preset → resolvability resolver (the SAME seam as the estimates read).

    Reuses ``SettingsEstimateResolver`` so ``resolvable`` is computed by the identical
    ``resolve_preset`` path that backs ``GET /api/estimates/quality-tiers`` (AC-5/AC-6
    parity). The inventory intents pin no Spoolman filament, so the Redis factory is
    unused on this path; it is wired through only to match the estimates seam. Overridable
    in tests via ``app.dependency_overrides``.
    """
    redis_factory = getattr(request.app.state, "redis", None)
    return SettingsEstimateResolver(redis_factory=redis_factory)


def get_profile_inventory_source() -> ProfileInventorySource:
    """The vendored profile source (intent-file presence + system-tree provenance hash).

    Read-only: ``has_intent`` is a pure existence check (backs ``imported``) and
    ``system_tree_hash`` is a content hash of the vendored system tree (backs provenance).
    Overridable in tests.
    """
    settings = get_settings()
    from app.modules.slicer.resolver import VendoredProfileSource

    return VendoredProfileSource(settings.slicer_vendored_profiles_dir)


@router.get(
    "/profiles",
    response_model=AdminProfileInventoryResponse,
    summary="Read-only admin inventory of Orca process profiles per slot (admin only)",
    description=(
        "Story 33.1 (FR21-PROFILE-INVENTORY-1 + FR21-COMPAT-1 read-only). Enumerates every "
        "(material_class, quality_tier) slot for one printer and projects whether it is "
        "imported / resolvable / compatible, the single primary status by precedence "
        "(Incompatible → Not imported → Not resolvable → Offerable), a structured reason, "
        "and leak-fenced provenance. A read-only superset projection over the resolver — it "
        "never writes, slices, or imports. Admin-gated; not public; no Orca internals leak."
    ),
)
async def read_admin_profile_inventory(
    printer_ref: Annotated[str, Query(description="Portal printer identity (resolve input)")],
    resolver: Annotated[EstimateResolver, Depends(get_admin_profile_resolver)],
    source: Annotated[ProfileInventorySource, Depends(get_profile_inventory_source)],
    _user_id: uuid.UUID = current_admin,
) -> AdminProfileInventoryResponse:
    settings = get_settings()
    orca_version = settings.orca_version
    # Provenance tree hash is a property of the whole vendored system tree — constant
    # across slots, so compute it once rather than per slot.
    tree_hash = source.system_tree_hash()

    slots: list[AdminProfileSlot] = []
    for material_class in MATERIAL_CLASS_ORDER:
        for quality_tier in QUALITY_TIER_ORDER:
            intent = PrintIntentPreset(
                name=f"{material_class} {quality_tier}",
                material_class=material_class,
                quality_tier=quality_tier,
                printer_ref=printer_ref,
                spoolman_filament_ref=None,
            )
            imported = source.has_intent(intent)
            try:
                # REUSE the estimates resolve seam verbatim (AC-6 parity) — resolvability is
                # exactly "resolve_preset did not raise", for every slot including the
                # incompatible ones (so the parity with quality-tiers is total).
                await resolver.resolve_preset(intent)
            except PresetResolveError:
                resolvable = False
            else:
                resolvable = True
            # Provenance only when the profile actually resolved (no resolved profile ⇒ no
            # provenance). Leak-fenced: tree hash + orca_version only.
            provenance = (
                AdminProfileProvenance(source_system_tree_hash=tree_hash, orca_version=orca_version)
                if resolvable
                else AdminProfileProvenance()
            )
            slots.append(
                build_slot(
                    material_class,
                    quality_tier,
                    imported=imported,
                    resolvable=resolvable,
                    provenance=provenance,
                )
            )

    return AdminProfileInventoryResponse(printer_ref=printer_ref, slots=slots)
