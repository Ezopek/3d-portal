"""Story 32.6 (AC-1) — UI-safe estimate DTOs the ``/api/estimates`` read endpoint
projects from the internal ``EstimateRecord`` (``models.py``).

This file is the public ⟂ internal split, mirroring ``spools/schemas.py`` ⟂
``spools/models.py``: every DTO is ``ConfigDict(extra="forbid")`` and exposes ONLY
the fields the frontend renders. It deliberately carries NO ``settings_ids`` (the
resolved-profile attribution — internal), NO ``bundle_hash`` / ``stl_hash`` (the
content-addressed reproducibility key — internal), NO raw layer-height /
``filament_max_volumetric_speed`` / temps / density / g-code / Orca key, and NOT the
``SlicerProfileBundle`` itself. That is FR20-PRESET-1 ("the preset never leaks Orca
internals") enforced at the API boundary (the render layer re-enforces it — defense
in depth, AC-5).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.slicer.models import EstimateFailureReason, MaterialClass, QualityTier

# The UI estimate status = the Decision AJ ``EstimateStatus`` lifecycle
# ``{fresh, stale, queued, failed}`` PLUS ``absent`` — a 200 store miss the read
# endpoint adds as a FIRST-CLASS UI empty state (AC-1/AC-3), distinct from a transport
# error and from ``failed``. ``loading`` is a query/transport state the FE owns; it is
# never a DTO value (the server never reports "loading").
UIEstimateStatus = Literal["fresh", "stale", "queued", "failed", "absent"]


class WarningView(BaseModel):
    """A single non-blocking Orca slice warning, projected for the UI.

    ``message`` is the Orca warning TEXT (rendered as data, like a filament name — not
    UI copy). ``code`` is a stable category the FE can key an icon/label off; the
    internal ``SliceWarning`` carries only the message, so the code is the constant
    ``"slice_warning"`` category (see ``estimate_read.SLICE_WARNING_CODE``).
    """

    model_config = ConfigDict(extra="forbid")
    code: str
    message: str


class OverrideContextView(BaseModel):
    """Material / Spoolman provenance the operator needs, at the right altitude (AC-5).

    Carries the FACT that custom overrides are applied + safe display metadata (the
    material class, the quality tier, the pinned filament's human name, the carried
    ``filament.extra.url`` purchase link) — NEVER the override VALUES (no volumetric
    speed / temp / density / layer height number), NO ``settings_ids``, NO g-code, NO
    Orca key. FR20-PRESET-1 at the display boundary.
    """

    model_config = ConfigDict(extra="forbid")
    material_class: MaterialClass
    quality_tier: QualityTier
    # The pinned Spoolman filament's human display name (NOT the churning integer id).
    pinned_filament_name: str | None = None
    # The FACT that a custom Spoolman override profile is applied — a boolean badge,
    # never the values behind it.
    custom_overrides_applied: bool = False
    # The carried ``filament.extra.url`` purchase link (Story 32.5), surfaced as a plain
    # external link — URL-safety-gated (http/https only), never parsed beyond that.
    purchase_url: str | None = None


class EstimateView(BaseModel):
    """The UI-safe estimate the read endpoint returns (AC-1).

    A miss ⇒ ``status="absent"`` with every numeric ``None``. A ``failed`` record ⇒
    ``status="failed"`` + ``failure_reason`` + every numeric ``None`` (NEVER ``0`` — the
    no-silent-zero contract carries through to the wire). ``filament_cost`` is
    INFORMATIONAL only (AC-9 — no quote/checkout).
    """

    model_config = ConfigDict(extra="forbid")
    status: UIEstimateStatus
    time_seconds: int | None = None
    filament_g: float | None = None
    filament_mm: float | None = None
    filament_cm3: float | None = None
    filament_cost: float | None = None
    currency: str | None = None
    computed_at: str | None = None
    warnings: list[WarningView] = Field(default_factory=list)
    failure_reason: EstimateFailureReason | None = None
    override_context: OverrideContextView
