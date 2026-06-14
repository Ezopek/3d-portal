"""PROFILE-PUBLISH-1 (Decision AR) — offer-chain publish bridge.

This module is the backend bridge from a usable ``PrintProfileOffer`` to the real
resolver/bundle/slice path. It implements Decision AR option (b): resolve a chain from
library block bodies, never from the grid ``intents/`` tree, then persist the existing
append-only bundle and enqueue one real slice over an operator-designated catalog STL.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.db.models import ModelFile, ModelFileKind
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.enqueue import enqueue_slice_estimate, slice_job_id
from app.modules.slicer.models import MaterialClass, ResolveFailure, ResolveSuccess
from app.modules.slicer.profile_offer import (
    OFFER_MATERIAL_CATEGORIES,
    chain_of,
    is_valid_offer_id,
    list_offers,
    read_offer,
    restore_offer,
    revalidate_offer,
    snapshot_offer,
    store_offer,
)
from app.modules.slicer.resolver import VendoredProfileSource, resolve_chain
from app.modules.slicer.stl_cache import StlCache, validate_content_hash
from app.modules.slicer.validation import CliValidator

PublishState = Literal["published", "unpublished"]
PUBLISH_STATE_PUBLISHED: PublishState = "published"
PUBLISH_STATE_UNPUBLISHED: PublishState = "unpublished"

# Operator-selected G-DATA default for this slice. It is a content hash only; the actual
# source file is resolved through the catalog ModelFile row at publish time.
DEFAULT_PUBLISH_STL_HASH = "282d26c1660c41b30d15b293b5c92bfe494ab62d76350009ceba55e714774b7f"

_OFFER_MANIFEST_VERSION_V2 = "2"
_PUBLISH_HASH_KEYS = (
    "published_bundle_hash",
    "source_snapshot_ref",
    "published_stl_hash",
    "published_chain_fingerprint",
)


@dataclass(frozen=True)
class OfferPublishMetadata:
    publish_state: PublishState
    published_bundle_hash: str | None = None
    published_at: str | None = None
    published_by: str | None = None
    source_snapshot_ref: str | None = None
    published_stl_hash: str | None = None
    published_chain_fingerprint: str | None = None


@dataclass(frozen=True)
class PublishOutcome:
    offer_id: str
    published_bundle_hash: str
    published_at: str
    estimate_job_id: str
    sidecar: dict


class PublishError(Exception):
    """Structured publish rejection that routes can map to HTTP detail."""

    def __init__(self, status_code: int, reason_category: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reason_category = reason_category
        self.message = message


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def publish_state_of(sidecar: dict) -> OfferPublishMetadata:
    """Read v2 publish metadata; v1 sidecars read forward as unpublished."""
    if sidecar.get("publish_state") != PUBLISH_STATE_PUBLISHED:
        return OfferPublishMetadata(publish_state=PUBLISH_STATE_UNPUBLISHED)
    bundle_hash = sidecar.get("published_bundle_hash")
    published_at = sidecar.get("published_at")
    published_by = sidecar.get("published_by")
    source_snapshot_ref = sidecar.get("source_snapshot_ref")
    published_stl_hash = sidecar.get("published_stl_hash")
    if not all(isinstance(value, str) and value for value in (bundle_hash, published_at)):
        return OfferPublishMetadata(publish_state=PUBLISH_STATE_UNPUBLISHED)
    chain_fingerprint = sidecar.get("published_chain_fingerprint")
    return OfferPublishMetadata(
        publish_state=PUBLISH_STATE_PUBLISHED,
        published_bundle_hash=bundle_hash,
        published_at=published_at,
        published_by=published_by if isinstance(published_by, str) else None,
        source_snapshot_ref=source_snapshot_ref if isinstance(source_snapshot_ref, str) else None,
        published_stl_hash=published_stl_hash if isinstance(published_stl_hash, str) else None,
        published_chain_fingerprint=chain_fingerprint
        if isinstance(chain_fingerprint, str)
        else None,
    )


def apply_published_state(
    sidecar: dict,
    *,
    bundle_hash: str,
    published_at: str,
    published_by: uuid.UUID,
    source_snapshot_ref: str,
    stl_hash: str,
    chain_fingerprint: str | None = None,
) -> dict:
    """Return a v2 sidecar with additive active publish metadata."""
    validate_content_hash(bundle_hash)
    validate_content_hash(source_snapshot_ref)
    validate_content_hash(stl_hash)
    updated = dict(sidecar)
    updated["offer_manifest_version"] = _OFFER_MANIFEST_VERSION_V2
    updated["publish_state"] = PUBLISH_STATE_PUBLISHED
    updated["published_bundle_hash"] = bundle_hash
    updated["published_at"] = published_at
    updated["published_by"] = str(published_by)
    updated["source_snapshot_ref"] = source_snapshot_ref
    updated["published_stl_hash"] = stl_hash
    updated["published_chain_fingerprint"] = chain_fingerprint
    return updated


def apply_unpublished_state(sidecar: dict) -> dict:
    """Return a v2 sidecar with no active publish refs."""
    updated = dict(sidecar)
    updated["offer_manifest_version"] = _OFFER_MANIFEST_VERSION_V2
    updated["publish_state"] = PUBLISH_STATE_UNPUBLISHED
    for key in _PUBLISH_HASH_KEYS:
        updated[key] = None
    updated["published_at"] = None
    updated["published_by"] = None
    return updated


def store_publish_state(root: Path | str, sidecar: dict) -> Path:
    """Persist a publish-state sidecar through the shared atomic offer store."""
    return store_offer(root, sidecar)


def _material_class_for_offer(resolved_offer) -> MaterialClass:
    filament = next(
        (
            block
            for block in resolved_offer.chain_block_manifests
            if block.get("profile_type") == "filament"
        ),
        None,
    )
    if filament is not None:
        material_type = filament.get("material_type")
        if material_type in OFFER_MATERIAL_CATEGORIES:
            return cast(MaterialClass, material_type)
    for category in resolved_offer.sidecar.get("compatible_material_categories") or []:
        if category in OFFER_MATERIAL_CATEGORIES:
            return cast(MaterialClass, category)
    raise PublishError(
        409,
        "offer_not_usable",
        "offer has no supported material category for publish",
    )


def _source_stl_for_hash(session: Session, *, content_dir: Path, stl_hash: str) -> Path:
    try:
        validate_content_hash(stl_hash)
    except ValueError as exc:
        raise PublishError(422, "invalid_stl_hash", "stl_hash must be a sha256 hex digest") from exc
    row = session.scalars(
        select(ModelFile)
        .where(ModelFile.kind == ModelFileKind.stl)
        .where(ModelFile.sha256 == stl_hash)
        .order_by(ModelFile.created_at.asc())
    ).first()
    if row is None:
        raise PublishError(422, "stl_not_found", "no catalog STL exists for the requested hash")
    base = content_dir.resolve()
    candidate = (content_dir / row.storage_path).resolve()
    if not (candidate == base or base in candidate.parents):
        raise PublishError(422, "stl_not_found", "catalog STL path is invalid")
    if not candidate.exists():
        raise PublishError(422, "stl_not_found", "catalog STL bytes are not available")
    return candidate


def _offer_or_404(root: Path | str, offer_id: str) -> dict:
    if not is_valid_offer_id(offer_id):
        raise PublishError(404, "not_found", "no such profile offer")
    sidecar = read_offer(root, offer_id)
    if sidecar is None:
        raise PublishError(404, "not_found", "no such profile offer")
    return sidecar


async def publish_offer(
    *,
    offer_id: str,
    root: Path,
    source: VendoredProfileSource,
    bundle_store: BundleStore,
    validator: CliValidator,
    orca_version: str,
    stl_hash: str | None,
    content_dir: Path,
    stl_cache: StlCache,
    db_session: Session,
    arq_pool: Any,
    actor_user_id: uuid.UUID,
    engine: Engine,
    request_id: str | None,
) -> PublishOutcome:
    """Publish a usable offer and enqueue exactly one estimate slice."""
    sidecar = _offer_or_404(root, offer_id)
    peers = list_offers(root)
    resolved = revalidate_offer(root, sidecar, peers=peers)
    if resolved.state == "invalid":
        raise PublishError(409, "offer_not_usable", "offer validation_state is invalid")
    if resolved.state == "requires_attention":
        raise PublishError(
            409, "offer_requires_attention", "offer requires operator attention before publish"
        )

    selected_stl_hash = stl_hash or DEFAULT_PUBLISH_STL_HASH
    source_stl = _source_stl_for_hash(
        db_session, content_dir=content_dir, stl_hash=selected_stl_hash
    )
    material_class = _material_class_for_offer(resolved)
    outcome = resolve_chain(
        chain_of(sidecar),
        source=source,
        store=bundle_store,
        validator=validator,
        orca_version=orca_version,
        material_class=material_class,
    )
    if isinstance(outcome, ResolveFailure):
        raise PublishError(
            422,
            "chain_resolve_failed",
            f"{outcome.reason.value}: {outcome.message}",
        )
    assert isinstance(outcome, ResolveSuccess)

    cached_stl_hash = stl_cache.populate_from_source(source_stl)
    if cached_stl_hash != selected_stl_hash:
        raise PublishError(
            422,
            "stl_hash_mismatch",
            "catalog STL bytes do not match the requested hash",
        )

    from app.modules.slicer.profile_offer import derive_chain_fingerprint

    chain_fingerprint = derive_chain_fingerprint(chain_of(sidecar), root=root)
    if chain_fingerprint is None:
        raise PublishError(
            409,
            "offer_not_usable",
            "cannot derive chain fingerprint: missing or invalid imported_at in block manifest",
        )

    estimate_job_id = slice_job_id(cached_stl_hash, outcome.bundle.bundle_hash)
    published_at = _now_iso()
    updated = apply_published_state(
        sidecar,
        bundle_hash=outcome.bundle.bundle_hash,
        published_at=published_at,
        published_by=actor_user_id,
        source_snapshot_ref=outcome.bundle.source_snapshot_ref,
        stl_hash=cached_stl_hash,
        chain_fingerprint=chain_fingerprint,
    )
    previous = snapshot_offer(root, offer_id)
    store_publish_state(root, updated)
    try:
        enqueue_result = await enqueue_slice_estimate(
            arq_pool,
            source_stl=source_stl,
            bundle_hash=outcome.bundle.bundle_hash,
            stl_cache=stl_cache,
        )
        if enqueue_result.job_id != estimate_job_id:
            raise RuntimeError("slice enqueue returned an unexpected job id")
        chain = updated.get("chain") or {}
        record_event(
            engine,
            action="slicer_profile.offer_publish",
            entity_type="slicer_profile",
            entity_id=uuid.UUID(offer_id),
            actor_user_id=actor_user_id,
            after={
                "published_bundle_hash": outcome.bundle.bundle_hash,
                "machine_block_id": chain.get("machine_block_id"),
                "process_block_id": chain.get("process_block_id"),
                "filament_block_id": chain.get("filament_block_id"),
                "designated_stl_hash": cached_stl_hash,
                "estimate_job_id": estimate_job_id,
            },
            request_id=request_id,
        )
    except BaseException:
        restore_offer(root, offer_id, previous)
        raise
    return PublishOutcome(
        offer_id=offer_id,
        published_bundle_hash=outcome.bundle.bundle_hash,
        published_at=published_at,
        estimate_job_id=estimate_job_id,
        sidecar=updated,
    )


def unpublish_offer(
    *,
    offer_id: str,
    root: Path,
    actor_user_id: uuid.UUID,
    engine: Engine,
    request_id: str | None,
) -> dict:
    """Mark an offer unpublished without deleting append-only bundle/estimate artifacts."""
    sidecar = _offer_or_404(root, offer_id)
    previous_state = publish_state_of(sidecar)
    updated = apply_unpublished_state(sidecar)
    previous = snapshot_offer(root, offer_id)
    store_publish_state(root, updated)
    try:
        record_event(
            engine,
            action="slicer_profile.offer_unpublish",
            entity_type="slicer_profile",
            entity_id=uuid.UUID(offer_id),
            actor_user_id=actor_user_id,
            after={
                "publish_state": PUBLISH_STATE_UNPUBLISHED,
                "previous_bundle_hash": previous_state.published_bundle_hash,
            },
            request_id=request_id,
        )
    except BaseException:
        restore_offer(root, offer_id, previous)
        raise
    return updated
