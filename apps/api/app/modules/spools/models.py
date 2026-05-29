"""Initiative 19 Story 31.1 (Decision AF) — internal Pydantic mirror of
Spoolman's response shape. Carries ALL cost-relevant fields end-to-end so
Story 31.2's public DTOs + future Phase D cost-calc UX land without a
portal-side schema backfill. Models tolerate Spoolman schema drift via
``extra="ignore"``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class SpoolmanVendor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str


class SpoolmanFilament(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str
    vendor_id: int | None = None
    vendor_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten_vendor(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("vendor"), dict):
            vendor = data["vendor"]
            data = dict(data)
            if data.get("vendor_id") is None:
                data["vendor_id"] = vendor.get("id")
            if data.get("vendor_name") is None:
                data["vendor_name"] = vendor.get("name")
        return data

    material: str | None = None
    color_hex: str | None = None
    price: float | None = None
    weight: float | None = None
    spool_weight: float | None = None


class SpoolmanSpool(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    filament_id: int

    @model_validator(mode="before")
    @classmethod
    def _flatten_filament(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("filament"), dict):
            filament = data["filament"]
            data = dict(data)
            if data.get("filament_id") is None:
                data["filament_id"] = filament.get("id")
            if data.get("spool_weight") is None:
                data["spool_weight"] = filament.get("spool_weight")
        return data

    price: float | None = None
    remaining_weight: float | None = None
    initial_weight: float | None = None
    used_weight: float | None = None
    spool_weight: float | None = None
    first_used: datetime | None = None
    last_used: datetime | None = None
    archived: bool = False
    lot_nr: str | None = None


class SpoolmanSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spools: list[SpoolmanSpool]
    filaments: list[SpoolmanFilament]
    vendors: list[SpoolmanVendor]
    fetched_at: datetime
