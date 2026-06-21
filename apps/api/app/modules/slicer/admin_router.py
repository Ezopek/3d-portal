"""Admin router for slicer profile library and offer management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

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
from app.modules.slicer.resolver import VendoredProfileSource
from app.modules.slicer.schemas import (
    OfferEstimateRecomputeResponse,
    OfferPublishRequest,
    OfferPublishResult,
    OfferRecomputeRequest,
    OfferVisibility,
    PrintProfileOffer,
    PrintProfileOfferCreate,
    PrintProfileOfferListResponse,
    PrintProfileOfferUpdate,
    ProfileChainRef,
    ProfileImportRejection,
    ProfileLibraryBlock,
    ProfileLibraryListResponse,
    ProfileLibraryType,
)
from app.modules.slicer.stl_cache import StlCache
from app.modules.slicer.validation import NullCliValidator

# Upload cap for an imported intent triple (AC-4). An intent triple is a small JSON object
# ({machine, process, filament} merged Orca key/values) — orders of magnitude below the
# 500 MB STL cap (sot ``_MAX_FILE_BYTES``). This is an explicit safety bound against a
# non-profile payload, NOT a reuse of the STL cap; arbitrary-but-bounded — revisit only if a
# legitimate vendored triple is shown to exceed it.
_MAX_PROFILE_BYTES = 1 * 1024 * 1024  # 1 MiB

_LOG = logging.getLogger("app.modules.slicer.admin_router")

router = APIRouter(prefix="/api/admin", tags=["admin-profiles"])


# === DI seams (overridable in tests) =========================================


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

    # Story 40.1 — offer-publish offer-SoT hook.
    # Enqueue estimates for all catalog STLs x this offer's published bundle hash.
    # Never re-raises: a backfill failure must NOT roll back the publish.
    try:
        from sqlmodel import Session as _Session

        from app.modules.slicer.estimate_store import EstimateStore
        from app.modules.slicer.matrix_backfill import (
            enqueue_matrix_for_all_stls,
            enumerate_offer_cells,
        )

        _settings = get_settings()
        _sidecar = profile_offer.read_offer(source.root, offer_id)
        if _sidecar is not None:
            _resolved = enumerate_offer_cells([_sidecar], visible_only=False, offer_id=offer_id)
            if _resolved:
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
                        "labels.cells_count": len(_resolved),
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


def get_policy_profile_source() -> VendoredProfileSource:
    """The vendored profile source for filament name enumeration (AC-10)."""
    settings = get_settings()
    return VendoredProfileSource(settings.slicer_vendored_profiles_dir)


def _offer_recompute_noneligible_reason(sidecar: dict, *, visible_only: bool) -> str | None:
    if sidecar.get("publish_state") != profile_publish.PUBLISH_STATE_PUBLISHED:
        return "offer_unpublished"
    publish_state = profile_publish.publish_state_of(sidecar)
    if not publish_state.published_bundle_hash:
        return "missing_published_bundle_hash"
    if sidecar.get("validation_state") == "invalid":
        return "offer_invalid"
    if visible_only and sidecar.get("visibility") != "visible":
        return "offer_hidden"
    return None


async def _dry_run_offer_cells(
    response: OfferEstimateRecomputeResponse,
    *,
    rows: list[Any],
    active_cells: list[Any],
    estimate_store: Any,
    content_root: Any,
) -> OfferEstimateRecomputeResponse:
    from app.modules.slicer.models import EstimateStatus
    from app.modules.slicer.stl_cache import is_content_hash

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


async def _run_offer_recompute(
    *,
    body: OfferRecomputeRequest,
    request: Request,
    source: VendoredProfileSource,
) -> OfferEstimateRecomputeResponse:
    """Preview or enqueue offer-SoT estimates for all catalog STLs."""
    from sqlmodel import select

    from app.core.db.models import ModelFile, ModelFileKind
    from app.modules.slicer.estimate_store import EstimateStore
    from app.modules.slicer.matrix_backfill import (
        enqueue_matrix_for_all_stls,
        enumerate_offer_cells,
    )
    from app.modules.slicer.stl_cache import StlCache

    if body.offer_id is not None and not profile_offer.is_valid_offer_id(body.offer_id):
        raise _reject(422, "invalid_offer_id", "offer_id must be a 32-char lowercase hex string")

    settings = get_settings()
    sidecars = profile_offer.list_offers(source.root)
    if body.offer_id is not None:
        sidecar = profile_offer.read_offer(source.root, body.offer_id)
        if sidecar is None:
            raise _reject(404, "offer_not_found", "no such profile offer")
        reason = _offer_recompute_noneligible_reason(sidecar, visible_only=body.visible_only)
        if reason is not None:
            raise _reject(422, reason, "profile offer is not eligible for estimate recompute")
        sidecars = [sidecar]

    resolved = enumerate_offer_cells(
        sidecars, visible_only=body.visible_only, offer_id=body.offer_id
    )
    active_cells = [rc for rc in resolved if rc.bundle_hash is not None]
    response = OfferEstimateRecomputeResponse(
        dry_run=body.dry_run,
        cells_total=len(resolved),
        cells_resolved=len(active_cells),
        cells_resolve_failed=0,
    )

    estimate_store = EstimateStore(settings.slicer_estimate_store_dir)
    content_root = settings.portal_content_dir.resolve()
    with Session(get_engine()) as session:
        rows = session.exec(select(ModelFile).where(ModelFile.kind == ModelFileKind.stl)).all()
        response.inspected = len(rows)
        if (
            body.max_cells is not None
            and response.cells_total * response.inspected > body.max_cells
        ):
            raise _reject(422, "max_cells_exceeded", "requested recompute exceeds max_cells")
        if not active_cells:
            return response
        if body.dry_run:
            return await _dry_run_offer_cells(
                response,
                rows=rows,
                active_cells=active_cells,
                estimate_store=estimate_store,
                content_root=content_root,
            )

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


@router.post(
    "/profiles/offers/recompute-estimates",
    response_model=OfferEstimateRecomputeResponse,
    summary="Preview or enqueue offer-driven estimate recompute for all catalog STLs",
    description=(
        "Admin-gated offer-SoT recompute. Defaults to dry-run preview, filters optionally by "
        "offer_id and visible_only, and returns classified counters without reading any "
        "removed profile-policy state."
    ),
)
async def offer_recompute_estimates(
    body: OfferRecomputeRequest,
    request: Request,
    source: Annotated[VendoredProfileSource, Depends(get_policy_profile_source)],
    _user_id: uuid.UUID = current_admin,
) -> OfferEstimateRecomputeResponse:
    return await _run_offer_recompute(body=body, request=request, source=source)
