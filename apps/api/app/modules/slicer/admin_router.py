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

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Protocol, runtime_checkable

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlmodel import Session

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.config import get_settings
from app.core.db.session import get_engine, get_session
from app.modules.slicer import profile_library, profile_offer, profile_publish
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.compatibility import INCOMPATIBLE_REASON, is_compatible
from app.modules.slicer.estimate_read import (
    EstimateResolver,
    PresetResolveError,
    SettingsEstimateResolver,
)
from app.modules.slicer.import_service import (
    build_manifest,
    is_safe_printer_ref,
    is_valid_triple_shape,
    is_within_intents_root,
    publish_intent,
    restore_published_intent,
    sanitize_original_filename,
    snapshot_published_intent,
    validate_import,
)
from app.modules.slicer.models import (
    MaterialClass,
    PrintIntentPreset,
    QualityTier,
    ResolveFailure,
)
from app.modules.slicer.overrides import spoolman_filament_ref as _spoolman_filament_ref
from app.modules.slicer.profile_policy import (
    FilamentOverride,
    MaterialDefault,
    ProfilePolicy,
    ProfilePolicyStore,
    normalize_material,
    unknown_profile_refs,
)
from app.modules.slicer.resolver import VendoredProfileSource
from app.modules.slicer.router import QUALITY_TIER_ORDER
from app.modules.slicer.schemas import (
    AdminProfileInventoryResponse,
    AdminProfileProvenance,
    AdminProfileSlot,
    AdminProfileStatus,
    DefaultMatrixBackfillRequest,
    DefaultMatrixBackfillResponse,
    FilamentOverrideDeleteRequest,
    FilamentOverrideUpsert,
    MaterialDefaultUpsert,
    OfferPublishRequest,
    OfferPublishResult,
    OfferVisibility,
    PolicyAdminView,
    PrintProfileOffer,
    PrintProfileOfferCreate,
    PrintProfileOfferListResponse,
    PrintProfileOfferUpdate,
    ProfileChainRef,
    ProfileImportRejection,
    ProfileLibraryBlock,
    ProfileLibraryListResponse,
    ProfileLibraryType,
    SpoolmanFilamentPolicyInfo,
    SpoolmanMaterialInfo,
)
from app.modules.slicer.stl_cache import StlCache
from app.modules.slicer.validation import NullCliValidator
from app.modules.spools.models import SpoolmanSnapshot
from app.modules.spools.service import SpoolsService

# Upload cap for an imported intent triple (AC-4). An intent triple is a small JSON object
# ({machine, process, filament} merged Orca key/values) — orders of magnitude below the
# 500 MB STL cap (sot ``_MAX_FILE_BYTES``). This is an explicit safety bound against a
# non-profile payload, NOT a reuse of the STL cap; arbitrary-but-bounded — revisit only if a
# legitimate vendored triple is shown to exceed it.
_MAX_PROFILE_BYTES = 1 * 1024 * 1024  # 1 MiB

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

    def manifest_label(self, intent: PrintIntentPreset) -> str | None: ...


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
    portal_label: str | None = None,
) -> AdminProfileSlot:
    """Build one inventory slot from the per-dimension facts (the shared per-slot SoT).

    ``compatible`` comes from the compatibility SoT (``compatibility.py``); ``offerable``
    is the load-bearing conjunction; status/reason follow the AC-4 precedence.
    ``portal_label`` is the operator label surfaced from the Story 33.2 sidecar manifest
    (``None`` when no manifest exists — the unchanged 33.1 default); it does NOT replace any
    live field (AC-10/AC-14). Both the admin grid and the member-selector projection derive
    from THIS function, so a single test can assert neither surface offers an incompatible
    slot (AC-8).
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
        portal_label=portal_label,
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

    return VendoredProfileSource(settings.slicer_vendored_profiles_dir)


def get_import_profile_source() -> VendoredProfileSource:
    """The concrete vendored source the IMPORT write path targets (Story 33.2).

    Returns the same ``VendoredProfileSource`` rooted at ``slicer_vendored_profiles_dir`` as
    the inventory read, but typed as the concrete class because the import path needs
    ``intent_path`` / ``system_tree`` / ``root`` (not just the read-only inventory Protocol).
    Overridable in tests via ``app.dependency_overrides``.
    """
    settings = get_settings()
    return VendoredProfileSource(settings.slicer_vendored_profiles_dir)


def get_publish_bundle_store() -> BundleStore:
    settings = get_settings()
    return BundleStore(settings.slicer_bundle_store_dir)


def get_publish_stl_cache() -> StlCache:
    settings = get_settings()
    return StlCache(settings.slicer_stl_cache_dir)


def get_publish_arq_pool(request: Request) -> Any:
    arq_pool = getattr(request.app.state, "arq", None)
    if arq_pool is None:
        raise HTTPException(status_code=503, detail="slicer queue unavailable")
    return arq_pool


def _reject(status_code: int, reason_category: str, message: str) -> HTTPException:
    """Build a structured-detail rejection (AC-5/6/7, AC-18) — no Orca internals leaked."""
    return HTTPException(
        status_code,
        detail=ProfileImportRejection(
            reason_category=reason_category, message=message
        ).model_dump(),
    )


def _slot_id(printer_ref: str, material_class: str, quality_tier: str) -> uuid.UUID:
    """Deterministic audit entity_id for a slot (stable across re-imports, AC-12)."""
    return uuid.uuid5(
        uuid.NAMESPACE_URL, f"slicer_profile:{printer_ref}/{material_class}/{quality_tier}"
    )


@router.post(
    "/profiles/import",
    response_model=AdminProfileSlot,
    status_code=status.HTTP_201_CREATED,
    summary="Validated import + publish of an Orca intent triple into a slot (admin only)",
    description=(
        "Story 33.2 (FR21-PROFILE-IMPORT-1 + FR21-COMPAT-1 enforce). Accepts a multipart "
        "upload of an intent-triple JSON for the form-specified (printer_ref, material_class, "
        "quality_tier) slot and publishes it ONLY when it is BOTH structurally resolvable "
        "(reusing resolve() verbatim against the real system tree) AND compatible for the "
        "material class (compatibility.py SoT). Gate order: size (413) → shape (422 "
        "invalid_partial) → compatibility (422 incompatible_for_material) → structural "
        "resolve (422 classified) → atomic publish → sidecar manifest → audit → 201. Admin-"
        "gated; not public; CSRF enforced by middleware; no re-slice enqueued (OD-6 deferred)."
    ),
    responses={
        201: {"description": "Profile imported + published"},
        413: {"description": "Upload exceeds the profile size cap"},
        422: {"description": "Rejected: malformed / incompatible / not resolvable"},
    },
)
async def import_admin_profile(
    request: Request,
    file: Annotated[UploadFile, File(description="The intent-triple JSON (partials only)")],
    printer_ref: Annotated[str, Form()],
    material_class: Annotated[MaterialClass, Form()],
    quality_tier: Annotated[QualityTier, Form()],
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    portal_label: Annotated[str | None, Form()] = None,
    _user_id: uuid.UUID = current_admin,
) -> AdminProfileSlot:
    settings = get_settings()

    # (1) size cap (413) — read with an explicit ceiling so a non-profile payload cannot
    # exhaust memory. The target slot is taken from the form fields, NEVER inferred from the
    # file content (the uploaded JSON is the partials only — AC-3).
    data = b""
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        data += chunk
        if len(data) > _MAX_PROFILE_BYTES:
            raise _reject(
                413,
                "too_large",
                f"profile upload exceeds the {_MAX_PROFILE_BYTES}-byte cap",
            )

    # (2) parse + shape gate (422 invalid_partial) — the SAME {machine,process,filament} dict
    # shape the resolver applies, mirrored on the UPLOAD before any compatibility/resolve work.
    try:
        partials = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise _reject(
            422,
            "invalid_partial",
            "uploaded profile is not valid JSON",
        ) from None
    if not is_valid_triple_shape(partials):
        raise _reject(
            422,
            "invalid_partial",
            "expected an object carrying dict machine/process/filament entries",
        )

    # (2b) printer_ref path-safety gate (422) — printer_ref is the only attacker-controlled
    # component joined into the on-disk intent_path (material_class/quality_tier are Literal
    # enums). Reject traversal/separator/absolute values BEFORE any write so a malicious
    # printer_ref can never escape <root>/intents (fallback-review Critical fix).
    if not is_safe_printer_ref(printer_ref):
        raise _reject(
            422,
            "invalid_printer_ref",
            "printer_ref must be a single safe identifier (no path separators or traversal)",
        )

    # (3) compatibility gate (422) — cheap, no I/O, BEFORE any disk write or resolve (OD-7).
    # resolvable ∧ ¬compatible is still NOT offerable: an incompatible slot is never published.
    if not is_compatible(material_class, quality_tier):
        raise _reject(
            422,
            INCOMPATIBLE_REASON,
            f"slot {material_class}/{quality_tier} is not compatible for this material class",
        )

    intent = PrintIntentPreset(
        name=f"{material_class} {quality_tier}",
        material_class=material_class,
        quality_tier=quality_tier,
        printer_ref=printer_ref,
        spoolman_filament_ref=None,
    )

    # (4) structural resolvability gate (422 classified) — reuse resolve() VERBATIM via a
    # staged source; NOTHING is written until this passes (validate-before-publish, AC-7).
    outcome = validate_import(
        partials, intent, real_root=source.root, orca_version=settings.orca_version
    )
    if isinstance(outcome, ResolveFailure):
        raise _reject(422, outcome.reason.value, outcome.message)

    # (4b) belt-and-braces containment — the resolved publish target MUST stay below
    # <root>/intents even if the syntactic gate were bypassed (defense-in-depth, AC-23).
    intent_path = source.intent_path(intent)
    if not is_within_intents_root(source.root, intent_path):
        raise _reject(
            422,
            "invalid_printer_ref",
            "resolved profile path escapes the vendored intents tree",
        )

    # (5) atomic publish + (6) sidecar manifest — the validated triple is written in place.
    # Snapshot the prior pair so a later required side-effect failure (audit) can roll the disk
    # state back; a request must not return 500 while leaving an unaudited profile live.
    tree_hash = source.system_tree_hash()
    original_filename = sanitize_original_filename(file.filename)
    previous_intent, previous_manifest = snapshot_published_intent(intent_path)
    manifest = build_manifest(
        portal_label=portal_label,
        imported_by=_user_id,
        imported_at=datetime.now(UTC).isoformat(),
        original_filename=original_filename,
        compatible=True,
        compat_reason=None,
        source_system_tree_hash=tree_hash,
        orca_version=settings.orca_version,
    )
    publish_intent(partials, intent_path=intent_path, manifest=manifest)

    # (7) audit (NFR21-OBS-1) — leak-fenced: NO Orca profile body, NO g-code in the payload.
    # If the audit write fails after publish, restore the prior intent+manifest pair before
    # re-raising so an unaudited import never remains live on disk.
    try:
        record_event(
            get_engine(),
            action="slicer_profile.import",
            entity_type="slicer_profile",
            entity_id=_slot_id(printer_ref, material_class, quality_tier),
            actor_user_id=_user_id,
            after={
                "printer_ref": printer_ref,
                "material_class": material_class,
                "quality_tier": quality_tier,
                "portal_label": portal_label,
                "source_system_tree_hash": tree_hash,
                "original_filename": original_filename,
            },
            request_id=request.headers.get("x-request-id"),
        )
    except BaseException:
        restore_published_intent(intent_path, previous_intent, previous_manifest)
        raise

    # (8) 201 + the freshly-offerable slot (imported ∧ resolvable ∧ compatible all hold now).
    provenance = AdminProfileProvenance(
        source_system_tree_hash=tree_hash, orca_version=settings.orca_version
    )
    return build_slot(
        material_class,
        quality_tier,
        imported=True,
        resolvable=True,
        provenance=provenance,
        portal_label=portal_label,
    )


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
            # AC-14: surface the operator label from the sidecar manifest (when present).
            # All other slot fields stay computed exactly as in 33.1 — the manifest never
            # replaces imported/resolvable/compatible/status/offerable/provenance (AC-10).
            portal_label = source.manifest_label(intent) if imported else None
            slots.append(
                build_slot(
                    material_class,
                    quality_tier,
                    imported=imported,
                    resolvable=resolvable,
                    provenance=provenance,
                    portal_label=portal_label,
                )
            )

    return AdminProfileInventoryResponse(printer_ref=printer_ref, slots=slots)


# === PROFILE-LIB-1 (Decision AM) — separate-block profile library CRUD =========
#
# Four additive admin-gated routes on the SAME router object — the operator inventory of
# SEPARATE Orca profile blocks (machine / process / filament). Purely additive: they do NOT
# touch resolve(), the intents/ grid, the 33.1 inventory read, the 33.2 grid import, the
# append-only bundle/snapshot store, bundle_hash, or compatibility.py (AC-1/AC-21). Writes
# reuse the 33.2 atomic-publish + metadata-preservation foundations via profile_library
# (which delegates to import_service.publish_pair) — no re-implemented unsafe writes (AC-8).


def _block_dto(manifest: dict) -> ProfileLibraryBlock:
    """Project a curated library manifest onto the leak-fenced ``ProfileLibraryBlock`` DTO.

    Selects ONLY the DTO fields (drops the internal ``manifest_version`` / ``original_filename``
    sidecar bookkeeping) so ``extra="forbid"`` holds and no raw Orca key can cross the wire.
    """
    return ProfileLibraryBlock(
        block_id=manifest["block_id"],
        profile_type=manifest["profile_type"],
        name=manifest["name"],
        source=manifest.get("source"),
        is_system=manifest.get("is_system", False),
        inherit=manifest.get("inherit"),
        inherit_chain=manifest.get("inherit_chain", []),
        settings_id=manifest.get("settings_id"),
        material_type=manifest.get("material_type"),
        compatible_printers=manifest.get("compatible_printers", []),
        validation_state=manifest["validation_state"],
        reasons=manifest.get("reasons", []),
        portal_label=manifest.get("portal_label"),
        imported_at=manifest["imported_at"],
        imported_by=manifest["imported_by"],
    )


@router.post(
    "/profiles/library",
    response_model=ProfileLibraryBlock,
    status_code=status.HTTP_201_CREATED,
    summary="Import/upload a single Orca profile BLOCK into the library (admin only)",
    description=(
        "PROFILE-LIB-1 (Decision AM). Accepts a multipart upload of ONE Orca profile-block "
        "JSON (process / filament / machine; no slot fields — the target tree is derived from "
        "the classified type). Gate order: size (413 too_large) → parse (422 invalid_json) → "
        "classify (422 unsupported_profile when ambiguous) → extract curated metadata → derive "
        "validation state (requires_attention does NOT block storage) → atomic store (body + "
        "curated manifest sidecar) → audit → 201 with the curated block DTO. Admin-gated; not "
        "public; CSRF enforced by middleware. The curated surface never exposes raw Orca JSON."
    ),
    responses={
        201: {"description": "Block imported (usable or requires_attention)"},
        413: {"description": "Upload exceeds the profile size cap"},
        422: {"description": "Rejected: invalid JSON / unsupported (unclassifiable) profile"},
    },
)
async def import_profile_block(
    request: Request,
    file: Annotated[UploadFile, File(description="A single Orca profile-block JSON")],
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    portal_label: Annotated[str | None, Form()] = None,
    _user_id: uuid.UUID = current_admin,
) -> ProfileLibraryBlock:
    # (1) size cap (413) — bounded read so a non-profile payload cannot exhaust memory. A single
    # Orca block is a small JSON object (same 1 MiB contract as the 33.2 intent triple).
    data = b""
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        data += chunk
        if len(data) > _MAX_PROFILE_BYTES:
            raise _reject(
                413, "too_large", f"profile upload exceeds the {_MAX_PROFILE_BYTES}-byte cap"
            )

    # (2) parse (422 invalid_json).
    try:
        body = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise _reject(422, "invalid_json", "uploaded profile is not valid JSON") from None

    # (3) classify (422 unsupported_profile) — an ambiguous/unclassifiable block is the AC-2
    # error path: rejected, NOTHING stored. A nameless block cannot mint a stable block_id, so
    # it is unsupported too.
    profile_type = profile_library.classify_profile(body)
    if profile_type is None:
        raise _reject(
            422, "unsupported_profile", "could not classify the uploaded Orca profile block"
        )
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise _reject(
            422, "unsupported_profile", "the uploaded Orca profile block has no usable name"
        )

    # (4) extract curated metadata + derive validation state (requires_attention is stored).
    system_tree = source.system_tree()
    curated = profile_library.extract_curated_metadata(
        body, profile_type=profile_type, system_tree=system_tree
    )
    validation_state, reasons = profile_library.derive_validation_state(
        curated, system_tree=system_tree
    )

    # (5) atomic store (body + curated manifest sidecar). block_id is server-derived + path-safe.
    block_id = profile_library.derive_block_id(profile_type, curated.name)
    original_filename = profile_library.sanitize_original_filename(file.filename)
    imported_at = datetime.now(UTC).isoformat()
    manifest = profile_library.build_block_manifest(
        curated,
        block_id=block_id,
        validation_state=validation_state,
        reasons=reasons,
        portal_label=portal_label,
        imported_by=_user_id,
        imported_at=imported_at,
        original_filename=original_filename,
    )
    prev_body, prev_manifest = profile_library.snapshot_block(source.root, profile_type, block_id)
    profile_library.store_block(
        source.root, profile_type=profile_type, block_id=block_id, body=body, manifest=manifest
    )

    # (6) audit (NFR21-OBS-1) — leak-fenced: NO Orca body / g-code / path in the payload. If the
    # audit write fails after the store, roll the block back to its prior state before re-raising.
    try:
        record_event(
            get_engine(),
            action="slicer_profile.library_import",
            entity_type="slicer_profile",
            entity_id=uuid.UUID(block_id),
            actor_user_id=_user_id,
            after={
                "profile_type": profile_type,
                "name": curated.name,
                "source": curated.source,
                "settings_id": curated.settings_id,
                "material_type": curated.material_type,
                "validation_state": validation_state,
                "portal_label": portal_label,
                "original_filename": original_filename,
            },
            request_id=request.headers.get("x-request-id"),
        )
    except BaseException:
        profile_library.restore_block(source.root, profile_type, block_id, prev_body, prev_manifest)
        raise

    stale = profile_offer.offers_referencing_block(source.root, block_id)
    stale_offers = [
        {
            "offer_id": s.get("offer_id"),
            "label": s.get("label"),
            "publish_state": s.get("publish_state"),
        }
        for s in stale
        if s.get("publish_state") == "published"
    ]
    block_data = _block_dto(manifest).model_dump()
    block_data["stale_offers"] = stale_offers
    return ProfileLibraryBlock(**block_data)


@router.get(
    "/profiles/library",
    response_model=ProfileLibraryListResponse,
    summary="List imported Orca profile blocks (curated metadata only, admin only)",
    description=(
        "PROFILE-LIB-1 (AC-10). Lists every imported block's curated metadata (read from the "
        "on-disk manifest sidecars, never the raw bodies), optionally filtered by profile_type "
        "(?profile_type=process etc.). Deterministically ordered (process first, then name). A "
        "missing/empty library tree returns an empty list. Admin-gated; no Orca internals leak."
    ),
)
async def list_profile_blocks(
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    profile_type: Annotated[ProfileLibraryType | None, Query()] = None,
    _user_id: uuid.UUID = current_admin,
) -> ProfileLibraryListResponse:
    manifests = profile_library.list_blocks(source.root, profile_type=profile_type)
    return ProfileLibraryListResponse(blocks=[_block_dto(m) for m in manifests])


@router.get(
    "/profiles/library/{block_id}",
    response_model=ProfileLibraryBlock,
    summary="Get one imported block's curated detail (admin only)",
    description=(
        "PROFILE-LIB-1 (AC-11). Returns the curated metadata + validation state for one block "
        "(404 not_found when absent). It returns curated metadata ONLY — there is NO raw Orca "
        "JSON preview/detail in this story. The block_id path param is validated as 32-char hex."
    ),
    responses={404: {"description": "No block with that id"}},
)
async def get_profile_block(
    block_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> ProfileLibraryBlock:
    if not profile_library.is_valid_block_id(block_id):
        raise _reject(404, "not_found", "no such profile block")
    manifest = profile_library.read_block(source.root, block_id)
    if manifest is None:
        raise _reject(404, "not_found", "no such profile block")
    return _block_dto(manifest)


@router.delete(
    "/profiles/library/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an imported block (audited, admin only)",
    description=(
        "PROFILE-LIB-1 (AC-12). Removes a block's body + curated manifest (manifest first so a "
        "torn delete never leaves a manifest pointing at a gone body), 404 not_found when "
        "absent, 204 on success, audited. Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        204: {"description": "Block deleted"},
        404: {"description": "No block with that id"},
        409: {"description": "Block in use by one or more offers"},
    },
)
async def delete_profile_block(
    request: Request,
    block_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> None:
    if not profile_library.is_valid_block_id(block_id):
        raise _reject(404, "not_found", "no such profile block")
    referencing = profile_offer.offers_referencing_block(source.root, block_id)
    if referencing:
        raise HTTPException(
            status_code=409,
            detail={
                "reason_category": "profile_block_in_use",
                "message": f"block is referenced by {len(referencing)} offer(s)",
                "offers": [
                    {
                        "offer_id": s.get("offer_id"),
                        "label": s.get("label"),
                        "publish_state": s.get("publish_state"),
                    }
                    for s in referencing
                ],
            },
        )
    removed = profile_library.delete_block(source.root, block_id)
    if not removed:
        raise _reject(404, "not_found", "no such profile block")
    record_event(
        get_engine(),
        action="slicer_profile.library_delete",
        entity_type="slicer_profile",
        entity_id=uuid.UUID(block_id),
        actor_user_id=_user_id,
        after={"block_id": block_id},
        request_id=request.headers.get("x-request-id"),
    )


# === PROFILE-OFFER-1 (Decision AN) — PrintProfileOffer / ProfileChain CRUD =====
#
# Five additive admin-gated routes on the SAME router object — the offer/chain layer that
# CONSUMES the PROFILE-LIB-1 block library. Purely additive (AC-1): they do NOT call resolve(),
# read raw Orca bodies, write the intents/ grid, touch the append-only bundle/snapshot store,
# bundle_hash, compatibility.py, or the library WRITE path. Each write reuses the shared atomic
# single-file publish + ezop:ezop-664 metadata preservation via profile_offer (which delegates
# to import_service.publish_single). Real resolver publication / live slicing is OUT of scope
# (G-PUBLISH, deferred). The offer routes carry current_admin, so the route-enforcement gate
# recognises them WITHOUT any _PUBLIC_ROUTES edit (AC-15).


def _offer_dto(resolved: profile_offer.ResolvedOffer) -> PrintProfileOffer:
    """Project a stored offer sidecar + its read-time validation onto the leak-fenced DTO.

    ``validation_state`` / ``reasons`` come from the READ-TIME recomputation (AC-10), never the
    stored snapshot; ``chain_blocks`` echoes the referenced blocks' curated metadata (reusing
    ``_block_dto`` — the same leak-fenced projection the library list/get use), omitting any
    missing referenced block.
    """
    sidecar = resolved.sidecar
    chain = sidecar.get("chain") or {}
    publish_state = profile_publish.publish_state_of(sidecar)
    sync_state = profile_offer.derive_sync_state(
        sidecar,
        chain_block_manifests=resolved.chain_block_manifests,
        resolved_state=resolved.state,
    )
    return PrintProfileOffer(
        offer_id=sidecar["offer_id"],
        label=sidecar["label"],
        description=sidecar.get("description"),
        chain=ProfileChainRef(
            machine_block_id=chain["machine_block_id"],
            process_block_id=chain["process_block_id"],
            filament_block_id=chain["filament_block_id"],
        ),
        visibility=sidecar["visibility"],
        is_default=sidecar.get("is_default", False),
        compatible_material_categories=sidecar.get("compatible_material_categories", []),
        validation_state=resolved.state,
        reasons=resolved.reasons,
        chain_blocks=[_block_dto(m) for m in resolved.chain_block_manifests],
        created_at=sidecar["created_at"],
        created_by=sidecar["created_by"],
        updated_at=sidecar["updated_at"],
        publish_state=publish_state.publish_state,
        published_bundle_hash=publish_state.published_bundle_hash,
        published_at=publish_state.published_at,
        published_by=publish_state.published_by,
        source_snapshot_ref=publish_state.source_snapshot_ref,
        published_stl_hash=publish_state.published_stl_hash,
        sync_state=sync_state,
    )


def _gate_material_categories(categories: list[str]) -> None:
    """AC-9 material-category gate: an out-of-table category ⇒ 422 unsupported_material_category."""
    for category in categories:
        if category not in profile_offer.OFFER_MATERIAL_CATEGORIES:
            raise _reject(
                422,
                "unsupported_material_category",
                f"material category {category!r} is not in the supported set",
            )


async def _read_json_body(request: Request) -> object:
    """Read + size-cap (413) + JSON-parse (422 invalid_json) a request body (AC-9 gate order)."""
    raw = await request.body()
    if len(raw) > _MAX_PROFILE_BYTES:
        raise _reject(413, "too_large", f"offer body exceeds the {_MAX_PROFILE_BYTES}-byte cap")
    try:
        return json.loads(raw.decode("utf-8")) if raw else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise _reject(422, "invalid_json", "offer body is not valid JSON") from None


def _offer_audit_payload(record: dict) -> dict:
    """The leak-fenced audit ``after`` payload for an offer mutation (AC-14)."""
    chain = record.get("chain") or {}
    return {
        "label": record.get("label"),
        "visibility": record.get("visibility"),
        "is_default": record.get("is_default"),
        "compatible_material_categories": record.get("compatible_material_categories"),
        "machine_block_id": chain.get("machine_block_id"),
        "process_block_id": chain.get("process_block_id"),
        "filament_block_id": chain.get("filament_block_id"),
        "validation_state": record.get("validation_state"),
    }


@router.post(
    "/profiles/offers",
    response_model=PrintProfileOffer,
    status_code=status.HTTP_201_CREATED,
    summary="Compose + validate a PrintProfileOffer over the block library (admin only)",
    description=(
        "PROFILE-OFFER-1 (Decision AN). Accepts a JSON body selecting one machine + one process "
        "+ one filament library block (an embedded ProfileChain) plus label/visibility/default/"
        "compatible-material-categories, validates the chain by reading ONLY the referenced "
        "blocks' curated manifests (NO resolve(), NO slicing), and stores the offer as an "
        "on-disk sidecar. Gate order: size (413) → parse/shape (422 invalid_json / invalid_offer) "
        "→ material category (422 unsupported_material_category) → hard chain gate (422 "
        "invalid_chain for a structural reason — nothing stored) → derive validation "
        "(requires_attention does NOT block) → atomic store → audit → 201. Admin-gated; not "
        "public; CSRF enforced by middleware. No raw Orca JSON crosses the wire; no publish/slice."
    ),
    responses={
        201: {"description": "Offer created (usable or requires_attention)"},
        413: {"description": "Body exceeds the size cap"},
        422: {"description": "Rejected: malformed / unsupported category / invalid chain"},
    },
)
async def create_profile_offer(
    request: Request,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> PrintProfileOffer:
    # (1) size (413) + (2a) parse (422 invalid_json).
    parsed = await _read_json_body(request)
    # (2b) shape (422 invalid_offer) — extra="forbid" + the hex block_id field validators.
    try:
        body = PrintProfileOfferCreate.model_validate(parsed)
    except ValidationError:
        raise _reject(422, "invalid_offer", "offer body failed validation") from None

    # (3) material category gate (422 unsupported_material_category).
    _gate_material_categories(body.compatible_material_categories)

    # (4) hard chain gate (422 invalid_chain) — a structural invalid (unknown_block /
    # wrong_block_type / block_unusable) is rejected, NOTHING stored.
    chain = profile_offer.ProfileChain(
        machine_block_id=body.chain.machine_block_id,
        process_block_id=body.chain.process_block_id,
        filament_block_id=body.chain.filament_block_id,
    )
    if profile_offer.validate_chain(chain, root=source.root).state == "invalid":
        raise _reject(422, "invalid_chain", "the selected blocks do not form a valid chain")

    # (5) derive validation across the existing offer set + this offer, then atomic store.
    offer_id = profile_offer.mint_offer_id()
    now = datetime.now(UTC).isoformat()
    peers = profile_offer.list_offers(source.root)
    record = profile_offer.build_offer_record(
        offer_id=offer_id,
        label=body.label,
        description=body.description,
        chain=chain,
        visibility=body.visibility,
        is_default=body.is_default,
        compatible_material_categories=body.compatible_material_categories,
        validation_state="usable",
        reasons=[],
        created_at=now,
        created_by=_user_id,
        updated_at=now,
    )
    resolved = profile_offer.revalidate_offer(source.root, record, peers=peers)
    record["validation_state"] = resolved.state
    record["reasons"] = resolved.reasons

    prev = profile_offer.snapshot_offer(source.root, offer_id)
    profile_offer.store_offer(source.root, record)

    # (6) audit (NFR21-OBS-1) — leak-fenced. Roll the store back if the audit write fails.
    try:
        record_event(
            get_engine(),
            action="slicer_profile.offer_create",
            entity_type="slicer_profile",
            entity_id=uuid.UUID(offer_id),
            actor_user_id=_user_id,
            after=_offer_audit_payload(record),
            request_id=request.headers.get("x-request-id"),
        )
    except BaseException:
        profile_offer.restore_offer(source.root, offer_id, prev)
        raise

    return _offer_dto(resolved)


@router.get(
    "/profiles/offers",
    response_model=PrintProfileOfferListResponse,
    summary="List PrintProfileOffers with read-time revalidation (admin only)",
    description=(
        "PROFILE-OFFER-1 (AC-10). Lists every offer's curated DTO (read from the on-disk "
        "sidecars), optionally filtered by ?material_category= and/or ?visibility=. Each offer's "
        "validation_state + reasons are RECOMPUTED at read time against the current library, so a "
        "stale 'usable' is never served after a referenced block was deleted (it surfaces as "
        "invalid unknown_block; the offer remains, flagged — no eager cross-deletion). "
        "Deterministically ordered (created_at then offer_id). Admin-gated; no raw Orca JSON."
    ),
)
async def list_profile_offers(
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    material_category: Annotated[str | None, Query()] = None,
    visibility: Annotated[OfferVisibility | None, Query()] = None,
    _user_id: uuid.UUID = current_admin,
) -> PrintProfileOfferListResponse:
    sidecars = profile_offer.list_offers(source.root)
    offers: list[PrintProfileOffer] = []
    for resolved in profile_offer.revalidate_offers(source.root, sidecars):
        sidecar = resolved.sidecar
        if material_category is not None and material_category not in (
            sidecar.get("compatible_material_categories") or []
        ):
            continue
        if visibility is not None and sidecar.get("visibility") != visibility:
            continue
        offers.append(_offer_dto(resolved))
    return PrintProfileOfferListResponse(offers=offers)


@router.get(
    "/profiles/offers/{offer_id}",
    response_model=PrintProfileOffer,
    summary="Get one PrintProfileOffer's curated detail (admin only)",
    description=(
        "PROFILE-OFFER-1 (AC-11). Returns the single offer DTO with read-time revalidation + the "
        "chain_blocks echo (404 not_found when absent). Curated metadata + validation state ONLY "
        "— NO raw Orca JSON body. The offer_id path param is validated as 32-char hex."
    ),
    responses={404: {"description": "No offer with that id"}},
)
async def get_profile_offer(
    offer_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> PrintProfileOffer:
    if not profile_offer.is_valid_offer_id(offer_id):
        raise _reject(404, "not_found", "no such profile offer")
    sidecar = profile_offer.read_offer(source.root, offer_id)
    if sidecar is None:
        raise _reject(404, "not_found", "no such profile offer")
    peers = profile_offer.list_offers(source.root)
    resolved = profile_offer.revalidate_offer(source.root, sidecar, peers=peers)
    return _offer_dto(resolved)


@router.patch(
    "/profiles/offers/{offer_id}",
    response_model=PrintProfileOffer,
    summary="Edit a PrintProfileOffer's label/visibility/default/categories (audited, admin only)",
    description=(
        "PROFILE-OFFER-1 (AC-12). Partial update of label/description/visibility/is_default/"
        "compatible_material_categories ONLY — the chain (block refs) is IMMUTABLE on PATCH "
        "(changing blocks = delete + recreate). Re-runs the material-category gate (422 "
        "unsupported_material_category), re-derives validation, atomic re-write, bumps "
        "updated_at, audits. 404 not_found when absent. Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        404: {"description": "No offer with that id"},
        422: {"description": "Rejected: malformed body / unsupported category"},
    },
)
async def update_profile_offer(
    request: Request,
    offer_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> PrintProfileOffer:
    if not profile_offer.is_valid_offer_id(offer_id):
        raise _reject(404, "not_found", "no such profile offer")

    parsed = await _read_json_body(request)
    try:
        body = PrintProfileOfferUpdate.model_validate(parsed)
    except ValidationError:
        raise _reject(422, "invalid_offer", "offer body failed validation") from None

    sidecar = profile_offer.read_offer(source.root, offer_id)
    if sidecar is None:
        raise _reject(404, "not_found", "no such profile offer")

    # Apply only the fields actually provided (partial PATCH) — exclude_unset distinguishes
    # "set to null" from "absent". The chain key is never in this body (forbidden on the DTO).
    changes = body.model_dump(exclude_unset=True)
    if "compatible_material_categories" in changes:
        _gate_material_categories(changes["compatible_material_categories"] or [])

    updated = dict(sidecar)
    updated.update(changes)
    updated["updated_at"] = datetime.now(UTC).isoformat()

    # Re-derive validation across the OTHER offers + this updated offer.
    peers = [s for s in profile_offer.list_offers(source.root) if s.get("offer_id") != offer_id]
    resolved = profile_offer.revalidate_offer(source.root, updated, peers=peers)
    updated["validation_state"] = resolved.state
    updated["reasons"] = resolved.reasons

    prev = profile_offer.snapshot_offer(source.root, offer_id)
    profile_offer.store_offer(source.root, updated)
    try:
        record_event(
            get_engine(),
            action="slicer_profile.offer_update",
            entity_type="slicer_profile",
            entity_id=uuid.UUID(offer_id),
            actor_user_id=_user_id,
            after=_offer_audit_payload(updated),
            request_id=request.headers.get("x-request-id"),
        )
    except BaseException:
        profile_offer.restore_offer(source.root, offer_id, prev)
        raise

    return _offer_dto(resolved)


@router.delete(
    "/profiles/offers/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a PrintProfileOffer (audited, admin only)",
    description=(
        "PROFILE-OFFER-1 (AC-13). Removes the offer sidecar (404 not_found when absent, 204 on "
        "success, audited). Deleting an offer does NOT touch the referenced library blocks "
        "(offers reference, they do not own). Re-deleting an absent offer is an idempotent-safe "
        "404, not a 500. Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        204: {"description": "Offer deleted"},
        404: {"description": "No offer with that id"},
    },
)
async def delete_profile_offer(
    request: Request,
    offer_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> None:
    if not profile_offer.is_valid_offer_id(offer_id):
        raise _reject(404, "not_found", "no such profile offer")
    if not profile_offer.delete_offer(source.root, offer_id):
        raise _reject(404, "not_found", "no such profile offer")
    record_event(
        get_engine(),
        action="slicer_profile.offer_delete",
        entity_type="slicer_profile",
        entity_id=uuid.UUID(offer_id),
        actor_user_id=_user_id,
        after={"offer_id": offer_id},
        request_id=request.headers.get("x-request-id"),
    )


# === PROFILE-PUBLISH-1 (Decision AR) — offer chain publish / rollback =========
#
# Two additive admin-gated POST routes. They are the first E33 routes that legitimately
# touch the resolve/bundle/slice path: publish resolves the offer's chain directly from
# library block bodies, persists the bundle append-only, enqueues one slicer job, and records
# v2 publish state on the offer sidecar. Unpublish flips only that marker; it never deletes
# append-only bundles/snapshots/estimates.


@router.post(
    "/profiles/offers/{offer_id}/publish",
    response_model=OfferPublishResult,
    summary="Publish a usable PrintProfileOffer chain to a real resolver bundle (admin only)",
    description=(
        "PROFILE-PUBLISH-1 (Decision AR option b). Re-validates the offer at publish time, "
        "resolves its ProfileChain directly from library block bodies through the shared "
        "resolver tail, persists the content-addressed bundle/snapshot append-only, enqueues "
        "one slicer estimate for the requested or operator-selected catalog STL hash, writes "
        "additive v2 publish-state on the offer sidecar, and audits. It never reads/writes the "
        "grid intents/system trees and does not change the member selector."
    ),
    responses={
        200: {"description": "Offer published and one estimate slice enqueued"},
        404: {"description": "No offer with that id"},
        409: {"description": "Offer is not usable or requires attention"},
        422: {"description": "Publish rejected: STL hash/resolve failure"},
    },
)
async def publish_profile_offer(
    request: Request,
    offer_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    bundle_store: Annotated[BundleStore, Depends(get_publish_bundle_store)],
    stl_cache: Annotated[StlCache, Depends(get_publish_stl_cache)],
    db_session: Annotated[Session, Depends(get_session)],
    arq_pool: Annotated[Any, Depends(get_publish_arq_pool)],
    _user_id: uuid.UUID = current_admin,
) -> OfferPublishResult:
    parsed = await _read_json_body(request)
    try:
        body = OfferPublishRequest.model_validate(parsed or {})
    except ValidationError:
        raise _reject(422, "invalid_publish_request", "publish body failed validation") from None

    settings = get_settings()
    try:
        outcome = await profile_publish.publish_offer(
            offer_id=offer_id,
            root=source.root,
            source=source,
            bundle_store=bundle_store,
            validator=NullCliValidator(),
            orca_version=settings.orca_version,
            stl_hash=body.stl_hash,
            content_dir=settings.portal_content_dir,
            stl_cache=stl_cache,
            db_session=db_session,
            arq_pool=arq_pool,
            actor_user_id=_user_id,
            engine=get_engine(),
            request_id=request.headers.get("x-request-id"),
        )
    except profile_publish.PublishError as exc:
        raise _reject(exc.status_code, exc.reason_category, exc.message) from exc

    # Story 35.6 — offer-publish matrix hook (AC-9).
    # Enqueue estimates for all catalog STLs x this offer's compatible material defaults.
    # Never re-raises: a backfill failure must NOT roll back the publish.
    try:
        from app.modules.slicer.matrix_backfill import enumerate_matrix_cells, resolve_matrix_cells

        _settings = get_settings()
        _sidecar = profile_offer.read_offer(source.root, offer_id)
        if _sidecar is not None:
            _policy = ProfilePolicyStore(_settings.slicer_profile_policy_dir).load()
            _cells = enumerate_matrix_cells([_sidecar], _policy)
            if _cells:
                _resolved = resolve_matrix_cells(
                    _cells,
                    source=source,
                    store=bundle_store,
                    orca_version=_settings.orca_version,
                    validator=NullCliValidator(),
                )
                from sqlmodel import Session as _Session

                from app.modules.slicer.estimate_store import EstimateStore
                from app.modules.slicer.matrix_backfill import enqueue_matrix_for_all_stls

                _counters: dict[str, int] = {}
                with _Session(get_engine()) as _sess:
                    _counters = await enqueue_matrix_for_all_stls(
                        _resolved,
                        arq_pool=arq_pool,
                        stl_cache=stl_cache,
                        estimate_store=EstimateStore(_settings.slicer_estimate_store_dir),
                        content_dir=_settings.portal_content_dir.resolve(),
                        db_session=_sess,
                    )
                _LOG.info(
                    "slicer.offer_publish_matrix_hook",
                    extra={
                        "labels.offer_id": offer_id,
                        "labels.cells_count": len(_cells),
                        "labels.enqueued": _counters.get("enqueued", 0),
                        "labels.already_fresh": _counters.get("already_fresh", 0),
                    },
                )
    except Exception:
        _LOG.exception(
            "slicer.offer_publish_matrix_hook.error",
            extra={"labels.offer_id": offer_id},
        )

    return OfferPublishResult(
        offer_id=outcome.offer_id,
        published_bundle_hash=outcome.published_bundle_hash,
        publish_state=profile_publish.PUBLISH_STATE_PUBLISHED,
        published_at=outcome.published_at,
        estimate_job_id=outcome.estimate_job_id,
        estimate=None,
    )


@router.post(
    "/profiles/offers/{offer_id}/unpublish",
    response_model=PrintProfileOffer,
    summary="Mark a PrintProfileOffer unpublished without deleting append-only artifacts",
    description=(
        "PROFILE-PUBLISH-1 rollback primitive. Flips the offer sidecar publish_state to "
        "unpublished, clears active publish refs, and audits. The persisted bundle/snapshot/"
        "estimate artifacts are append-only and are never deleted."
    ),
    responses={
        200: {"description": "Offer is unpublished (idempotent)"},
        404: {"description": "No offer with that id"},
    },
)
async def unpublish_profile_offer(
    request: Request,
    offer_id: str,
    source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> PrintProfileOffer:
    try:
        updated = profile_publish.unpublish_offer(
            offer_id=offer_id,
            root=source.root,
            actor_user_id=_user_id,
            engine=get_engine(),
            request_id=request.headers.get("x-request-id"),
        )
    except profile_publish.PublishError as exc:
        raise _reject(exc.status_code, exc.reason_category, exc.message) from exc
    peers = profile_offer.list_offers(source.root)
    resolved = profile_offer.revalidate_offer(source.root, updated, peers=peers)
    return _offer_dto(resolved)


# === POLICY-ADMIN-1 (FR23-ADMIN-1) — filament-profile-selection policy admin ===
#
# Five additive admin-gated routes on the SAME router object (prefix="/api/admin").
# Read + write surface for the portal's filament-profile-selection policy. Purely
# additive: does NOT touch resolve(), the intents/grid, the library, the offer layer,
# or the bundle/snapshot/estimate stores.
#
# All write routes carry ``current_admin`` (default-value Depends) so the Init 6
# route-enforcement gate recognises them WITHOUT any _PUBLIC_ROUTES edit (AC-3).

_POLICY_LOG = logging.getLogger("app.slicer.policy_admin")
_LOG = logging.getLogger("app.modules.slicer.admin_router")


# --- DI seams (overridable in tests) ----------------------------------------


def get_policy_store() -> ProfilePolicyStore:
    """The filesystem-backed policy store, rooted at the configured policy dir."""
    settings = get_settings()
    return ProfilePolicyStore(settings.slicer_profile_policy_dir)


async def get_snapshot(request: Request) -> SpoolmanSnapshot | None:
    """The live Spoolman snapshot; soft-fails to None when unavailable (AC-2)."""
    redis_factory = getattr(request.app.state, "redis", None)
    service = SpoolsService(redis_factory=redis_factory, client=None)
    try:
        return await service.get_summary()
    except Exception:
        _POLICY_LOG.warning(
            "Spoolman snapshot unavailable for policy admin read",
            extra={"labels": {"reason": "snapshot_unavailable"}},
        )
        return None


def get_policy_profile_source() -> VendoredProfileSource:
    """The vendored profile source for filament name enumeration (AC-10)."""
    settings = get_settings()
    return VendoredProfileSource(settings.slicer_vendored_profiles_dir)


# --- pure helpers -----------------------------------------------------------


def _known_filament_profile_refs(source: VendoredProfileSource) -> set[str]:
    """Vendored filament-type system profile names (AC-10 known_refs set).

    Computed fresh per request — the system tree can change on deploy. NOT cached
    across requests (AC-10 explicit prohibition).
    """
    return {
        name
        for name, body in source.system_tree().items()
        if profile_library.classify_profile(body) == "filament"
    }


def _build_policy_admin_view(
    policy: ProfilePolicy,
    snapshot: SpoolmanSnapshot | None,
    source: VendoredProfileSource,
) -> PolicyAdminView:
    """Project policy + snapshot + system_tree onto PolicyAdminView (AC-1/AC-2)."""
    system_tree = source.system_tree()
    orca_names = sorted(
        name
        for name, body in system_tree.items()
        if profile_library.classify_profile(body) == "filament"
    )

    materials_info: list[SpoolmanMaterialInfo] = []
    filaments_info: list[SpoolmanFilamentPolicyInfo] = []

    if snapshot is not None:
        seen: set[str] = set()
        for f in snapshot.filaments:
            norm = normalize_material(f.material)
            if norm is None or norm in seen:
                continue
            seen.add(norm)
            default = policy.material_defaults.get(norm)
            materials_info.append(
                SpoolmanMaterialInfo(
                    material=norm,
                    configured=default is not None and default.enabled,
                    enabled=default.enabled if default is not None else None,
                    orca_filament_profile_ref=(
                        default.orca_filament_profile_ref if default else None
                    ),
                )
            )

        for f in snapshot.filaments:
            ref = _spoolman_filament_ref(f)
            override = policy.filament_overrides.get(ref)
            filaments_info.append(
                SpoolmanFilamentPolicyInfo(
                    ref=ref,
                    name=f.name,
                    vendor_name=f.vendor_name,
                    material=normalize_material(f.material),
                    has_override=override is not None,
                    override=override,
                )
            )

    return PolicyAdminView(
        policy=policy,
        spoolman_materials=materials_info,
        spoolman_filaments=filaments_info,
        orca_filament_profile_names=orca_names,
    )


def _policy_entity_id(discriminator: str) -> uuid.UUID:
    """Deterministic audit entity_id for a policy mutation (stable across re-saves)."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"slicer_policy:{discriminator}")


async def _run_default_matrix_backfill(
    *,
    body: DefaultMatrixBackfillRequest,
    request: Request,
    store: ProfilePolicyStore,
    source: VendoredProfileSource,
) -> DefaultMatrixBackfillResponse:
    """Preview or enqueue the published-offer x material-default estimate matrix."""
    if body.include_overrides:
        raise _reject(
            422,
            "include_overrides_not_supported",
            "HTTP backfill is limited to material defaults; filament overrides stay opt-in-only",
        )

    material_filter = None
    if body.material is not None:
        material_filter = normalize_material(body.material)
        if not material_filter:
            raise _reject(422, "invalid_material", "material filter must be non-blank")

    from sqlmodel import select

    from app.core.db.models import ModelFile, ModelFileKind
    from app.modules.slicer.estimate_store import EstimateStore
    from app.modules.slicer.matrix_backfill import (
        enqueue_matrix_for_all_stls,
        enumerate_matrix_cells,
        resolve_matrix_cells,
    )
    from app.modules.slicer.models import EstimateStatus
    from app.modules.slicer.profile_offer import list_offers
    from app.modules.slicer.stl_cache import StlCache, is_content_hash
    from app.modules.slicer.validation import NullCliValidator

    settings = get_settings()
    policy = store.load()
    sidecars = list_offers(source.root)
    if body.offer_id:
        sidecars = [s for s in sidecars if s.get("offer_id") == body.offer_id]
    offers_map = {s.get("offer_id", ""): s for s in sidecars if s.get("offer_id")}
    cells = enumerate_matrix_cells(sidecars, policy, material_filter=material_filter)
    resolved = resolve_matrix_cells(
        cells,
        source=source,
        store=BundleStore(settings.slicer_bundle_store_dir),
        orca_version=settings.orca_version,
        validator=NullCliValidator(),
        offers_map=offers_map,
    )
    active_cells = [rc for rc in resolved if rc.bundle_hash is not None]

    response = DefaultMatrixBackfillResponse(
        dry_run=body.dry_run,
        cells_total=len(resolved),
        cells_resolved=len(active_cells),
        cells_resolve_failed=sum(1 for rc in resolved if rc.resolve_failed),
    )

    estimate_store = EstimateStore(settings.slicer_estimate_store_dir)
    content_root = settings.portal_content_dir.resolve()
    with Session(get_engine()) as session:
        rows = session.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()
        response.inspected = len(rows)

        # No resolvable cells (empty policy, all resolve-failed, or filtered to nothing) means
        # there is nothing to enqueue: skip the STL scan and never touch the queue. This keeps a
        # real (non-dry) run with an empty policy from failing on the arq availability check.
        if not active_cells:
            return response

        if body.dry_run:
            for row in rows:
                abs_path = (content_root / row.storage_path).resolve()
                try:
                    abs_path.relative_to(content_root)
                except ValueError:
                    response.errors += len(active_cells)
                    continue
                if not abs_path.is_file():
                    response.missing_stl += len(active_cells)
                    continue
                candidate_stl_hash = row.sha256
                if not is_content_hash(candidate_stl_hash):
                    response.errors += len(active_cells)
                    continue
                for rc in active_cells:
                    existing = estimate_store.read(candidate_stl_hash, rc.bundle_hash)
                    if existing is not None and existing.status == EstimateStatus.fresh:
                        response.already_fresh += 1
                    else:
                        response.would_enqueue += 1
            return response

        arq_pool = getattr(request.app.state, "arq", None)
        if arq_pool is None:
            raise HTTPException(status_code=503, detail="slicer queue unavailable")
        counters = await enqueue_matrix_for_all_stls(
            resolved,
            arq_pool=arq_pool,
            stl_cache=StlCache(settings.slicer_stl_cache_dir),
            estimate_store=estimate_store,
            content_dir=content_root,
            db_session=session,
        )
        response.enqueued = counters.get("enqueued", 0)
        response.already_fresh = counters.get("already_fresh", 0)
        response.missing_stl = counters.get("missing_stl", 0)
        response.errors = counters.get("errors", 0)
        return response


# --- GET /api/admin/policy ---------------------------------------------------


@router.get(
    "/policy",
    response_model=PolicyAdminView,
    summary="Read the full filament-profile-selection policy + Spoolman context (admin only)",
    description=(
        "POLICY-ADMIN-1 (FR23-ADMIN-1, AC-1/AC-2/AC-3). Returns the current "
        "ProfilePolicy plus Spoolman material/filament projections and the sorted list "
        "of vendored filament-type profile names. When the Spoolman snapshot is "
        "unavailable (cold Redis / service down), returns 200 with empty material and "
        "filament lists — never 500. Admin-gated; no Orca internals leak."
    ),
)
async def read_policy(
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    snapshot: Annotated[SpoolmanSnapshot | None, Depends(get_snapshot)],
    source: Annotated[VendoredProfileSource, Depends(get_policy_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> PolicyAdminView:
    # get_snapshot() already logs when it soft-fails on an exception (AC-2 single warning).
    policy = store.load()
    return _build_policy_admin_view(policy, snapshot, source)


@router.post(
    "/policy/default-matrix-backfill",
    response_model=DefaultMatrixBackfillResponse,
    summary="Preview or enqueue the published-offer x material-default estimate matrix",
    description=(
        "Admin-gated explicit control for default-matrix estimate backfill. Defaults to "
        "dry-run preview, excludes filament overrides, filters optionally by material or "
        "offer_id, and returns classified counters without exposing raw Orca bodies, gcode, "
        "bundle hashes, STL paths, or queue internals."
    ),
)
async def default_matrix_backfill(
    body: DefaultMatrixBackfillRequest,
    request: Request,
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    source: Annotated[VendoredProfileSource, Depends(get_policy_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> DefaultMatrixBackfillResponse:
    return await _run_default_matrix_backfill(
        body=body,
        request=request,
        store=store,
        source=source,
    )


# --- PUT /api/admin/policy/material-defaults/{material} ----------------------


@router.put(
    "/policy/material-defaults/{material}",
    response_model=PolicyAdminView,
    summary="Upsert a material-default entry in the policy (admin only)",
    description=(
        "POLICY-ADMIN-1 (AC-4/AC-6/AC-9/AC-10/AC-11/AC-12). Normalises the path "
        "param, validates the orca_filament_profile_ref against the vendored filament "
        "profile names (fresh per request — AC-10), saves atomically, and returns the "
        "updated PolicyAdminView. 422 invalid_material on blank normalised key; "
        "422 unknown_profile_ref when the ref is absent from the vendored tree. "
        "No partial save on 422 (AC-9). Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        200: {"description": "Material default upserted"},
        422: {"description": "Rejected: blank material or unknown profile ref"},
    },
)
async def upsert_material_default(
    material: str,
    body: MaterialDefaultUpsert,
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    snapshot: Annotated[SpoolmanSnapshot | None, Depends(get_snapshot)],
    source: Annotated[VendoredProfileSource, Depends(get_policy_profile_source)],
    request: Request,
    _user_id: uuid.UUID = current_admin,
) -> PolicyAdminView:
    norm = normalize_material(material)
    if not norm:
        raise _reject(422, "invalid_material", "material key must be non-blank after normalisation")

    policy = store.load()
    candidate = ProfilePolicy(
        material_defaults={
            **policy.material_defaults,
            norm: MaterialDefault(
                orca_filament_profile_ref=body.orca_filament_profile_ref,
                enabled=body.enabled,
            ),
        },
        filament_overrides=policy.filament_overrides,
    )

    known_refs = _known_filament_profile_refs(source)
    unknown = unknown_profile_refs(candidate, known_refs)
    if unknown:
        raise _reject(
            422,
            "unknown_profile_ref",
            f"profile ref(s) not in vendored system tree: {sorted(unknown)}",
        )

    store.save(candidate)
    record_event(
        get_engine(),
        action="slicer_policy.material_default_upsert",
        entity_type="slicer_profile",
        entity_id=_policy_entity_id(f"material_default:{norm}"),
        actor_user_id=_user_id,
        after={
            "material_or_ref": norm,
            "orca_filament_profile_ref": body.orca_filament_profile_ref,
            "enabled": body.enabled,
        },
        request_id=request.headers.get("x-request-id"),
    )

    # Story 35.6 — material-default change matrix hook (AC-10).
    # Re-enqueues all STLs for offers compatible with `norm` when the profile ref changes.
    # Only fires when the ref changes (or a brand-new enabled default is added).
    # Never re-raises: a backfill failure MUST NOT roll back the policy save.
    old_default = policy.material_defaults.get(norm)
    new_default = candidate.material_defaults.get(norm)
    _profile_ref_changed = (
        new_default is not None
        and new_default.enabled
        and (
            old_default is None
            or old_default.orca_filament_profile_ref != new_default.orca_filament_profile_ref
        )
    )
    if _profile_ref_changed:
        try:
            from sqlmodel import Session as _Session

            from app.modules.slicer.bundle_store import BundleStore
            from app.modules.slicer.estimate_store import EstimateStore
            from app.modules.slicer.matrix_backfill import (
                enqueue_matrix_for_all_stls,
                enumerate_matrix_cells,
                resolve_matrix_cells,
            )
            from app.modules.slicer.profile_offer import list_offers
            from app.modules.slicer.stl_cache import StlCache
            from app.modules.slicer.validation import NullCliValidator

            _settings = get_settings()
            _arq_pool = getattr(request.app.state, "arq", None)
            if _arq_pool is not None:
                _all_sidecars = list_offers(source.root)
                _compatible_sidecars = [
                    s
                    for s in _all_sidecars
                    if norm in (s.get("compatible_material_categories") or [])
                ]
                _cells = enumerate_matrix_cells(
                    _compatible_sidecars, candidate, material_filter=norm
                )
                if _cells:
                    _resolved = resolve_matrix_cells(
                        _cells,
                        source=source,
                        store=BundleStore(_settings.slicer_bundle_store_dir),
                        orca_version=_settings.orca_version,
                        validator=NullCliValidator(),
                    )
                    _counters: dict[str, int] = {}
                    with _Session(get_engine()) as _sess:
                        _counters = await enqueue_matrix_for_all_stls(
                            _resolved,
                            arq_pool=_arq_pool,
                            stl_cache=StlCache(_settings.slicer_stl_cache_dir),
                            estimate_store=EstimateStore(_settings.slicer_estimate_store_dir),
                            content_dir=_settings.portal_content_dir.resolve(),
                            db_session=_sess,
                        )
                    _LOG.info(
                        "slicer.policy_material_default_matrix_hook",
                        extra={
                            "labels.material": norm,
                            "labels.cells_count": len(_cells),
                            "labels.enqueued": _counters.get("enqueued", 0),
                            "labels.already_fresh": _counters.get("already_fresh", 0),
                        },
                    )
        except Exception:
            _LOG.exception(
                "slicer.policy_material_default_matrix_hook.error",
                extra={"labels.material": norm},
            )

    return _build_policy_admin_view(store.load(), snapshot, source)


# --- DELETE /api/admin/policy/material-defaults/{material} -------------------


@router.delete(
    "/policy/material-defaults/{material}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a material-default entry from the policy (admin only)",
    description=(
        "POLICY-ADMIN-1 (AC-5/AC-12). Normalises the path param (PLA == pla), removes "
        "the entry, and returns 204. 404 not_found when the normalised key was absent. "
        "Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        204: {"description": "Material default removed"},
        404: {"description": "Material key not found in policy"},
    },
)
async def delete_material_default(
    material: str,
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    request: Request,
    _user_id: uuid.UUID = current_admin,
) -> None:
    norm = normalize_material(material)
    policy = store.load()

    if norm is None or norm not in policy.material_defaults:
        raise _reject(404, "not_found", f"material default {material!r} not found in policy")

    updated = ProfilePolicy(
        material_defaults={k: v for k, v in policy.material_defaults.items() if k != norm},
        filament_overrides=policy.filament_overrides,
    )
    store.save(updated)
    record_event(
        get_engine(),
        action="slicer_policy.material_default_delete",
        entity_type="slicer_profile",
        entity_id=_policy_entity_id(f"material_default:{norm}"),
        actor_user_id=_user_id,
        after={"material_or_ref": norm, "orca_filament_profile_ref": None, "enabled": None},
        request_id=request.headers.get("x-request-id"),
    )


# --- POST /api/admin/policy/filament-overrides --------------------------------


@router.post(
    "/policy/filament-overrides",
    response_model=PolicyAdminView,
    summary="Upsert a per-filament override entry in the policy (admin only)",
    description=(
        "POLICY-ADMIN-1 (AC-7/AC-9/AC-10/AC-11/AC-12). Ref is in the body (not a path "
        "param) because it contains the unit-separator (U+001F) that would need "
        "percent-encoding in URLs. Validates orca_filament_profile_ref against vendored "
        "filament profiles (fresh per request — AC-10); 422 unknown_profile_ref when "
        "absent. No partial save on 422 (AC-9). Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        200: {"description": "Filament override upserted"},
        422: {"description": "Rejected: unknown profile ref"},
    },
)
async def upsert_filament_override(
    body: FilamentOverrideUpsert,
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    snapshot: Annotated[SpoolmanSnapshot | None, Depends(get_snapshot)],
    source: Annotated[VendoredProfileSource, Depends(get_policy_profile_source)],
    request: Request,
    _user_id: uuid.UUID = current_admin,
) -> PolicyAdminView:
    policy = store.load()
    candidate = ProfilePolicy(
        material_defaults=policy.material_defaults,
        filament_overrides={
            **policy.filament_overrides,
            body.spoolman_filament_ref: FilamentOverride(
                orca_filament_profile_ref=body.orca_filament_profile_ref,
                enabled=body.enabled,
            ),
        },
    )

    known_refs = _known_filament_profile_refs(source)
    unknown = unknown_profile_refs(candidate, known_refs)
    if unknown:
        raise _reject(
            422,
            "unknown_profile_ref",
            f"profile ref(s) not in vendored system tree: {sorted(unknown)}",
        )

    store.save(candidate)
    record_event(
        get_engine(),
        action="slicer_policy.filament_override_upsert",
        entity_type="slicer_profile",
        entity_id=_policy_entity_id(f"filament_override:{body.spoolman_filament_ref}"),
        actor_user_id=_user_id,
        after={
            "material_or_ref": body.spoolman_filament_ref,
            "orca_filament_profile_ref": body.orca_filament_profile_ref,
            "enabled": body.enabled,
        },
        request_id=request.headers.get("x-request-id"),
    )
    return _build_policy_admin_view(store.load(), snapshot, source)


# --- DELETE /api/admin/policy/filament-overrides ------------------------------


@router.delete(
    "/policy/filament-overrides",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a per-filament override entry from the policy (admin only)",
    description=(
        "POLICY-ADMIN-1 (AC-8/AC-12). Body carries the spoolman_filament_ref (contains "
        "U+001F — not suitable as path param). 204 on success; 404 not_found when the "
        "ref was absent. Admin-gated; CSRF enforced by middleware."
    ),
    responses={
        204: {"description": "Filament override removed"},
        404: {"description": "Filament override ref not found in policy"},
    },
)
async def delete_filament_override(
    body: FilamentOverrideDeleteRequest,
    store: Annotated[ProfilePolicyStore, Depends(get_policy_store)],
    request: Request,
    _user_id: uuid.UUID = current_admin,
) -> None:
    policy = store.load()

    if body.spoolman_filament_ref not in policy.filament_overrides:
        raise _reject(
            404,
            "not_found",
            f"filament override {body.spoolman_filament_ref!r} not found in policy",
        )

    updated = ProfilePolicy(
        material_defaults=policy.material_defaults,
        filament_overrides={
            k: v for k, v in policy.filament_overrides.items() if k != body.spoolman_filament_ref
        },
    )
    store.save(updated)
    record_event(
        get_engine(),
        action="slicer_policy.filament_override_delete",
        entity_type="slicer_profile",
        entity_id=_policy_entity_id(f"filament_override:{body.spoolman_filament_ref}"),
        actor_user_id=_user_id,
        after={
            "material_or_ref": body.spoolman_filament_ref,
            "orca_filament_profile_ref": None,
            "enabled": None,
        },
        request_id=request.headers.get("x-request-id"),
    )
