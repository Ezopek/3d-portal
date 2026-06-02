"""Initiative 19 Story 31.2 (Decision AF) — public ``/api/spools/*`` read-only
routes that project the Redis-cached Spoolman snapshot through the public
DTOs at ``apps/api/app/modules/spools/schemas.py``.

All three routes carry ``Depends(current_user)`` per operator decision 2 —
members + admin visible; NOT admin-only. The route-enforcement gate
(``apps/api/tests/test_route_enforcement_gate.py``) recognizes the auth
parameter; ``_PUBLIC_ROUTES`` stays UNTOUCHED.

Cold-cache + Spoolman-down behavior: returns HTTP 200 with empty arrays and
``last_success_ts: null`` rather than a 5xx. FR19-FAILURE-1 contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Request

from app.core.auth.dependencies import current_user
from app.core.config import get_settings
from app.modules.spools.client import SpoolmanClient
from app.modules.spools.models import SpoolmanSnapshot
from app.modules.spools.schemas import (
    FilamentView,
    SpoolsSummaryResponse,
    SpoolView,
    VendorView,
)
from app.modules.spools.service import SpoolsService

router = APIRouter(prefix="/api/spools", tags=["spools"])


async def _read_snapshot(
    request: Request,
) -> tuple[SpoolmanSnapshot | None, datetime | None]:
    settings = get_settings()
    async with SpoolmanClient(
        base_url=settings.spoolman_url,
        auth_token=settings.spoolman_auth_token,
    ) as client:
        service = SpoolsService(redis_factory=request.app.state.redis, client=client)
        snapshot = await service.get_summary()
        last_success = await service.get_last_success_ts()
    return snapshot, last_success


def _project_summary(
    snapshot: SpoolmanSnapshot | None, last_success: datetime | None
) -> SpoolsSummaryResponse:
    if snapshot is None:
        return SpoolsSummaryResponse(
            spools=[],
            filaments=[],
            vendors=[],
            fetched_at=None,
            last_success_ts=last_success,
        )
    return SpoolsSummaryResponse(
        spools=[SpoolView.model_validate(s.model_dump()) for s in snapshot.spools],
        filaments=[
            # ``extra`` is the internal Spoolman ``filament.extra`` map (Story 32.5 AC-1);
            # it is consumed by the slicer override layer and MUST NOT flow to the public
            # ``extra="forbid"`` FilamentView — exclude it from the projection (AC-9).
            FilamentView.model_validate(f.model_dump(exclude={"extra"}))
            for f in snapshot.filaments
        ],
        vendors=[VendorView.model_validate(v.model_dump()) for v in snapshot.vendors],
        fetched_at=snapshot.fetched_at,
        last_success_ts=last_success,
    )


@router.get(
    "/summary",
    response_model=SpoolsSummaryResponse,
    summary="Cached Spoolman inventory snapshot (members + admin)",
    description=(
        "Initiative 19 Story 31.2 (FR19-SPOOLS-VIEW-1 + FR19-DATA-CARRY-1). "
        "Returns the full Spoolman snapshot (spools + filaments + vendors) "
        "projected through public DTOs carrying every Decision AF cost-"
        "relevant field. Reads the canonical Redis key written by the arq "
        "poll job (Story 31.1); cold-cache miss falls through to a single "
        "lock-protected live fetch. Cold-cache + Spoolman-down returns HTTP "
        "200 with empty arrays + last_success_ts=null per FR19-FAILURE-1."
    ),
)
async def get_spools_summary(
    request: Request,
    _user_id: uuid.UUID = current_user,
) -> SpoolsSummaryResponse:
    snapshot, last_success = await _read_snapshot(request)
    return _project_summary(snapshot, last_success)


@router.get(
    "/spools",
    response_model=list[SpoolView],
    summary="Cached spool list slice (members + admin)",
    description=(
        "Slice projection of the same canonical snapshot returned by "
        "/api/spools/summary. Cache-coherent by construction — both "
        "endpoints ride the same Redis key (spools:summary:v1)."
    ),
)
async def get_spools_list(
    request: Request,
    _user_id: uuid.UUID = current_user,
) -> list[SpoolView]:
    snapshot, _ = await _read_snapshot(request)
    if snapshot is None:
        return []
    return [SpoolView.model_validate(s.model_dump()) for s in snapshot.spools]


@router.get(
    "/filaments",
    response_model=list[FilamentView],
    summary="Cached filament list slice (members + admin)",
    description=(
        "Slice projection of the same canonical snapshot returned by "
        "/api/spools/summary. Cache-coherent by construction — both "
        "endpoints ride the same Redis key (spools:summary:v1)."
    ),
)
async def get_filaments_list(
    request: Request,
    _user_id: uuid.UUID = current_user,
) -> list[FilamentView]:
    snapshot, _ = await _read_snapshot(request)
    if snapshot is None:
        return []
    # Exclude the internal ``extra`` map (Story 32.5 AC-1) — it never flows to the public DTO.
    return [
        FilamentView.model_validate(f.model_dump(exclude={"extra"})) for f in snapshot.filaments
    ]
