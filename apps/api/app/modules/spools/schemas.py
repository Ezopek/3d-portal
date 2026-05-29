"""Initiative 19 Story 31.2 (Decision AF) — public response DTOs that the
``/api/spools/*`` routes project from the internal Spoolman mirror at
``apps/api/app/modules/spools/models.py``.

Every Decision AF cost-relevant field is carried end-to-end so the future
Phase D cost-calc UX lights up without a portal-side schema backfill. The
strict ``extra="forbid"`` posture means schema drift is a code change, not
an implicit accept.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VendorView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    name: str


class FilamentView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    name: str
    vendor_id: int | None = None
    vendor_name: str | None = None
    material: str | None = None
    color_hex: str | None = None
    price: float | None = None
    weight: float | None = None
    spool_weight: float | None = None


class SpoolView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    filament_id: int
    price: float | None = None
    remaining_weight: float | None = None
    initial_weight: float | None = None
    used_weight: float | None = None
    spool_weight: float | None = None
    first_used: datetime | None = None
    last_used: datetime | None = None
    archived: bool = False
    lot_nr: str | None = None


class SpoolsSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spools: list[SpoolView]
    filaments: list[FilamentView]
    vendors: list[VendorView]
    fetched_at: datetime | None = None
    last_success_ts: datetime | None = None
