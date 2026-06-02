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

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth.dependencies import current_user
from app.core.config import get_settings
from app.modules.slicer.estimate_read import (
    EstimateResolver,
    PresetResolveError,
    SettingsEstimateResolver,
    build_override_context,
    project_estimate,
)
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import MaterialClass, PrintIntentPreset, QualityTier
from app.modules.slicer.schemas import EstimateView
from app.modules.slicer.stl_cache import validate_content_hash

router = APIRouter(prefix="/api/estimates", tags=["estimates"])


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

    try:
        resolved = await resolver.resolve_preset(intent)
    except PresetResolveError as exc:
        # The preset does not resolve to a bundle (e.g. a vendored profile is absent for
        # this printer/class/tier). A classified, no-internal-leak 422.
        raise HTTPException(status_code=422, detail="preset not resolvable") from exc

    record = store.read(stl_hash, resolved.bundle_hash)
    override_context = build_override_context(intent, resolved.pinned_filament)
    return project_estimate(record, override_context=override_context)
