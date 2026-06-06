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
import uuid
from datetime import UTC, datetime
from typing import Annotated, Protocol, runtime_checkable

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

from app.core.audit import record_event
from app.core.auth.dependencies import current_admin
from app.core.config import get_settings
from app.core.db.session import get_engine
from app.modules.slicer import profile_library
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
from app.modules.slicer.resolver import VendoredProfileSource
from app.modules.slicer.router import QUALITY_TIER_ORDER
from app.modules.slicer.schemas import (
    AdminProfileInventoryResponse,
    AdminProfileProvenance,
    AdminProfileSlot,
    AdminProfileStatus,
    ProfileImportRejection,
    ProfileLibraryBlock,
    ProfileLibraryListResponse,
    ProfileLibraryType,
)

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

    return _block_dto(manifest)


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
