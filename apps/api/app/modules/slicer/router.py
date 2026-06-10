"""Story 32.6 (AC-1) — the narrow, read-first estimate API seam.

The slicer estimate stack had NO HTTP surface before this story (the slicer module
mounted zero routes). This adds the MINIMUM the frontend needs: a single
**authenticated** ``GET /api/estimates`` read endpoint that resolves a
``PrintIntentPreset`` (built from the request's selector fields) to its
``bundle_hash`` (Story 32.1 ``resolve``), reads the persisted ``EstimateRecord``
(Story 32.3 ``EstimateStore.read``) by content key, and projects it onto the UI-safe
DTO (``schemas.py``). A store miss ⇒ ``status="absent"`` (a 200, not a 404).

Scope fence (AC-9): this router + ``schemas.py`` + ``estimate_read.py`` are the ONLY
new backend files; the engine modules are CALLED, not edited. The route is
authenticated (``Depends(current_user)``, recognized by the Story 11.4 route-
enforcement gate) and is NOT added to ``main.py:_PUBLIC_ROUTES``.

AC-1b (a guarded recompute-enqueue endpoint) is DEFERRED to ``deferred-work.md`` —
the read-only seam is sufficient for the 32.6 display MVP, and deferring keeps the
slicer-worker overlay out of the deploy path (SW-DEPLOY-1).
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth.dependencies import current_user
from app.core.config import get_settings
from app.modules.slicer.estimate_read import (
    EstimateResolver,
    PresetResolveError,
    SettingsEstimateResolver,
    UnavailableProfileError,
    build_override_context,
    build_profile_selection_context,
    project_estimate,
)
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import EstimateStatus, MaterialClass, PrintIntentPreset, QualityTier
from app.modules.slicer.recompute import enqueue_recompute
from app.modules.slicer.schemas import (
    EstimateView,
    QualityTierAvailability,
    QualityTierAvailabilityResponse,
    RecomputeRequest,
    RecomputeResponse,
)
from app.modules.slicer.stl_cache import validate_content_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/estimates", tags=["estimates"])

QUALITY_TIER_ORDER: tuple[QualityTier, ...] = ("aesthetic", "standard", "strong")


def get_estimate_store() -> EstimateStore:
    """The append-only estimate store rooted at the settings slot (Story 32.3).

    Overridable in tests via ``app.dependency_overrides`` so the read path can be
    exercised against a ``tmp_path`` store without touching the production volume.
    """
    settings = get_settings()
    return EstimateStore(settings.slicer_estimate_store_dir)


def get_estimate_resolver(request: Request) -> EstimateResolver:
    """The production preset → ``bundle_hash`` resolver (vendored profiles + Spoolman).

    Carries the app's Redis factory so the Spoolman override provider can read the
    Init 19 cache when a filament is pinned. Overridable in tests.
    """
    redis_factory = getattr(request.app.state, "redis", None)
    return SettingsEstimateResolver(redis_factory=redis_factory)


def get_recompute_resolver(request: Request) -> EstimateResolver:
    """The preset → ``bundle_hash`` resolver for the ENQUEUE path (EST-RECOMPUTE-1).

    Same resolver seam + same ``bundle_hash`` derivation as ``get_estimate_resolver``, but
    constructed with ``persist_bundle=True`` so a content-miss bundle is written through the
    real ``BundleStore`` — otherwise a by-hash re-slice enqueued for a never-yet-resolved
    bundle would classify a typed ``missing_bundle`` failure on the worker (the deliberate
    read-vs-enqueue divergence the deferral called out). Overridable in tests via
    ``app.dependency_overrides`` (the same ``_FakeResolver`` the read tests inject).
    """
    redis_factory = getattr(request.app.state, "redis", None)
    return SettingsEstimateResolver(redis_factory=redis_factory, persist_bundle=True)


def get_arq_pool(request: Request) -> Any:
    """The arq pool the recompute enqueue rides (``request.app.state.arq``), as an injectable
    dependency seam so tests can fake the queue (assert the deterministic Story 32.4 enqueue
    kwargs) without a live Redis. A missing pool ⇒ 503 (the queue is genuinely unavailable —
    a classified, no-internal-leak transport error, never a silent drop of the recompute).
    """
    arq_pool = getattr(request.app.state, "arq", None)
    if arq_pool is None:
        raise HTTPException(status_code=503, detail="recompute queue unavailable")
    return arq_pool


@router.get(
    "/quality-tiers",
    response_model=QualityTierAvailabilityResponse,
    summary="List resolvable estimate quality tiers for one printer/material pair",
    description=(
        "EST-TIERS-1 bridge contract. Resolves each portal quality tier for the given "
        "(printer_ref, material_class) and reports which tiers are actually available. "
        "This lets the Files/STL selector disable missing profiles before a member can "
        "send an estimate read/recompute request that would otherwise 422."
    ),
)
async def read_quality_tier_availability(
    material_class: Annotated[MaterialClass, Query()],
    printer_ref: Annotated[str, Query(description="Portal printer identity (resolve input)")],
    resolver: Annotated[EstimateResolver, Depends(get_estimate_resolver)],
    _user_id: uuid.UUID = current_user,
) -> QualityTierAvailabilityResponse:
    tiers: list[QualityTierAvailability] = []
    for quality_tier in QUALITY_TIER_ORDER:
        intent = PrintIntentPreset(
            name=f"{material_class} {quality_tier}",
            material_class=material_class,
            quality_tier=quality_tier,
            printer_ref=printer_ref,
            spoolman_filament_ref=None,
        )
        try:
            await resolver.resolve_preset(intent)
        except PresetResolveError:
            tiers.append(
                QualityTierAvailability(
                    quality_tier=quality_tier,
                    available=False,
                    reason="profile_not_imported",
                )
            )
        else:
            tiers.append(QualityTierAvailability(quality_tier=quality_tier, available=True))

    return QualityTierAvailabilityResponse(
        printer_ref=printer_ref,
        material_class=material_class,
        tiers=tiers,
    )


@router.get(
    "",
    response_model=EstimateView,
    summary="Resolve a print-intent preset to its persisted estimate (members + admin)",
    description=(
        "Story 32.6 (FR20-PRESET-1 + FR20-FAILURE-1 FE half). Resolves the preset "
        "(material class + quality tier + optional pinned Spoolman filament) to its "
        "content-addressed bundle, reads the persisted estimate for "
        "(stl_hash, bundle_hash), and projects it onto the UI-safe DTO. A miss returns "
        "200 with status=absent (a first-class empty state, NOT a 404). Read-only: "
        "never enqueues, slices, or writes an estimate record."
    ),
)
async def read_estimate(
    request: Request,
    stl_hash: Annotated[str, Query(description="Content hash (64 lowercase hex) of the STL")],
    material_class: Annotated[MaterialClass, Query()],
    quality_tier: Annotated[QualityTier, Query()],
    printer_ref: Annotated[str, Query(description="Portal printer identity (resolve input)")],
    store: Annotated[EstimateStore, Depends(get_estimate_store)],
    resolver: Annotated[EstimateResolver, Depends(get_estimate_resolver)],
    spoolman_filament_ref: Annotated[str | None, Query()] = None,
    _user_id: uuid.UUID = current_user,
) -> EstimateView:
    # Path-safety gate (AC-1): reject a malformed/traversal-shaped stl_hash BEFORE any
    # resolve/store read — no work on garbage, no untrusted hash woven into a path.
    try:
        validate_content_hash(stl_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="malformed stl_hash") from exc

    intent = PrintIntentPreset(
        name=f"{material_class} {quality_tier}",
        material_class=material_class,
        quality_tier=quality_tier,
        printer_ref=printer_ref,
        spoolman_filament_ref=spoolman_filament_ref,
    )
    # override_context for the unavailable path uses no pinned filament (profile absent).
    override_context_no_filament = build_override_context(intent, None)

    try:
        resolved = await resolver.resolve_preset(intent)
    except UnavailableProfileError as exc:
        # Story 35.3 (AC-4): no profile configured → 200 absent, NOT 422.
        # The order/request path stays open (NFR23-NO-BLOCK-1).
        # AC-14: log source label only — no filament names, no bodies.
        logger.info(
            "slicer.estimate.unavailable_profile",
            extra={
                "labels.estimate_profile_source": exc.profile_selection.source.value,
                "labels.reason": "unconfigured",
            },
        )
        ctx = build_profile_selection_context(exc.profile_selection, exc.selected_filament_name)
        return project_estimate(
            None, override_context=override_context_no_filament, profile_selection_context=ctx
        )
    except PresetResolveError as exc:
        # The preset does not resolve to a bundle (e.g. a vendored profile is absent for
        # this printer/class/tier). A classified, no-internal-leak 422.
        raise HTTPException(status_code=422, detail="preset not resolvable") from exc

    record = store.read(stl_hash, resolved.bundle_hash)
    override_context = build_override_context(intent, resolved.pinned_filament)
    return project_estimate(
        record,
        override_context=override_context,
        profile_selection_context=build_profile_selection_context(
            resolved.profile_selection, resolved.selected_filament_name
        ),
    )


@router.post(
    "/recompute",
    response_model=RecomputeResponse,
    summary="Enqueue a guarded re-slice for a preset's estimate (members + admin)",
    description=(
        "EST-RECOMPUTE-1 (Story 32.6 AC-1b, promoted). Resolves the preset to its "
        "content-addressed bundle and enqueues an idempotent by-hash re-slice via the Story "
        "32.4 enqueue helper, so the UI can (re)queue an estimate that is absent/stale/failed. "
        "Guarded against self-DoS: a record already 'queued' is an idempotent no-op (no second "
        "enqueue). Never fabricates numbers — an absent/failed key is returned in its honest "
        "current state with enqueued=true. Authenticated + CSRF-gated; not public; enqueues by "
        "hash only (no source-file hashing, no new job helper, no bulk/unbounded route)."
    ),
)
async def recompute_estimate(
    body: RecomputeRequest,
    store: Annotated[EstimateStore, Depends(get_estimate_store)],
    resolver: Annotated[EstimateResolver, Depends(get_recompute_resolver)],
    arq_pool: Annotated[Any, Depends(get_arq_pool)],
    _user_id: uuid.UUID = current_user,
) -> RecomputeResponse:
    # Path-safety gate (mirrors GET): reject a malformed/traversal-shaped stl_hash BEFORE any
    # resolve/store/queue work — no work on garbage, no untrusted hash woven into a path/_job_id.
    try:
        validate_content_hash(body.stl_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="malformed stl_hash") from exc

    intent = PrintIntentPreset(
        name=f"{body.material_class} {body.quality_tier}",
        material_class=body.material_class,
        quality_tier=body.quality_tier,
        printer_ref=body.printer_ref,
        spoolman_filament_ref=body.spoolman_filament_ref,
    )
    override_context_no_filament = build_override_context(intent, None)

    try:
        resolved = await resolver.resolve_preset(intent)
    except UnavailableProfileError as exc:
        # Story 35.3 (AC-5): no profile configured → 200, enqueued=False, no job (NFR23-NO-BLOCK-1).
        # AC-14: log source label only — no filament names, no bodies.
        logger.info(
            "slicer.estimate.unavailable_profile",
            extra={
                "labels.estimate_profile_source": exc.profile_selection.source.value,
                "labels.reason": "unconfigured",
            },
        )
        ctx = build_profile_selection_context(exc.profile_selection, exc.selected_filament_name)
        return RecomputeResponse(
            enqueued=False,
            estimate=project_estimate(
                None, override_context=override_context_no_filament, profile_selection_context=ctx
            ),
        )
    except PresetResolveError as exc:
        # Same classified, no-internal-leak 422 the read endpoint returns for an unresolvable
        # preset — and the enqueue is short-circuited (no job for a preset that has no bundle).
        raise HTTPException(status_code=422, detail="preset not resolvable") from exc

    override_context = build_override_context(intent, resolved.pinned_filament)
    profile_selection_context = build_profile_selection_context(
        resolved.profile_selection, resolved.selected_filament_name
    )
    record = store.read(body.stl_hash, resolved.bundle_hash)

    # Idempotency / self-DoS guard (R1): a recompute already in flight ('queued') must NOT
    # re-enqueue — return its still-servable projected estimate untouched. The Story 32.4
    # _job_id dedupe would drop a duplicate job anyway; short-circuiting here also avoids a
    # redundant queue round-trip and keeps enqueued=false honest.
    if record is not None and record.status == EstimateStatus.queued:
        return RecomputeResponse(
            enqueued=False,
            estimate=project_estimate(
                record,
                override_context=override_context,
                profile_selection_context=profile_selection_context,
            ),
        )

    # fresh / stale / failed / absent ⇒ enqueue an idempotent by-hash re-slice. Reuse the Story
    # 32.4 helper BYTE-IDENTICALLY (its own validate_content_hash + slice_job_id + queue name);
    # do NOT re-derive the job-id/queue constants or hash a source file here.
    await enqueue_recompute(arq_pool, stl_hash=body.stl_hash, bundle_hash=resolved.bundle_hash)

    # fresh / stale ⇒ mark queued (still SERVABLE: last numbers + a "recomputing" banner).
    # failed ⇒ mark_queued is a no-op (returns the failed record unchanged — never "queued over"
    # a failure); absent (miss) ⇒ mark_queued returns None (never fabricate a record). In both
    # cases the honest current state is what we project — no fabricated numbers.
    queued = store.mark_queued(body.stl_hash, resolved.bundle_hash)
    result_record = queued if queued is not None else record
    return RecomputeResponse(
        enqueued=True,
        estimate=project_estimate(
            result_record,
            override_context=override_context,
            profile_selection_context=profile_selection_context,
        ),
    )
