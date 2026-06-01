"""Internal Pydantic shapes + typed resolver result/failure model (Story 32.1).

These are the data-model surfaces of Decision AH (architecture.md § Initiative
20). None of them is exposed over HTTP in this story — ``PrintIntentPreset`` is
user-facing in a *later* story; ``SlicerProfileBundle`` / ``SourceProfileSnapshot``
are internal provenance/reproducibility records and are never sent to the client.

[Source: architecture.md § Decision AH — data-model surfaces]
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Material classes the resolver knows about (PRD § Initiative 20). An intent
# outside this set has no material-class default and resolves to a classified
# ``unsupported_material_class`` failure (AC-7), never a silent wrong default.
MaterialClass = Literal["PLA", "PETG", "PCTG", "TPU"]

# Print-intent quality presets (OD-1, resolved 2026-05-31).
QualityTier = Literal["aesthetic", "standard", "strong"]

# Profile kinds in an Orca resolve triple.
ProfileKind = Literal["machine", "process", "filament"]


class PrintIntentPreset(BaseModel):
    """User-facing print intent (portal-owned). MUST NOT leak Orca internals.

    Carries no raw layer-height floats / no ``filament_max_volumetric_speed`` —
    those live only in the resolved (internal) bundle. This story exposes it via
    NO route; it is the resolver's input key for ``(material_class, quality_tier,
    printer_ref)``.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    material_class: MaterialClass
    quality_tier: QualityTier
    printer_ref: str
    notes: str | None = None
    is_default: bool = False


class FilamentOverrides(BaseModel):
    """Spoolman-mapped custom overrides applied onto the filament JSON (AC-8).

    Mirrors the ``filament.extra`` fields Story 32.5 will pull from Spoolman.
    Every field is optional; only set fields are applied. ``None`` fields are
    excluded from the override fingerprint so they do not perturb the hash.
    """

    model_config = ConfigDict(extra="forbid")

    filament_max_volumetric_speed: float | None = None
    nozzle_temperature: int | None = None
    hot_plate_temp: int | None = None
    filament_density: float | None = None


class ResolvedTriple(BaseModel):
    """The three normalized, CLI-acceptable profile JSONs (the portable artifact).

    Stored as full dicts (not flattened) so a later variable/adaptive layer-height
    process profile remains representable (AC-11 forward-compat invariant).
    """

    machine: dict
    process: dict
    filament: dict


class SourceProfileSnapshot(BaseModel):
    """Append-only provenance record so a resolve is reproducible/diffable (AC-6).

    ``source_system_tree_hash`` is the content identity of the vendored system
    profile tree (NOT merely its root path): the vendored artifacts are edited in
    place, so an in-place system-profile change must yield a new snapshot identity
    rather than silently aliasing an old snapshot (review fix #3).

    ``created_at`` is provenance metadata and is deliberately EXCLUDED from
    ``snapshot_hash`` (and from ``bundle_hash``) so it never perturbs the
    content-addressed identity.
    """

    source_system_tree_ref: str
    source_system_tree_hash: str
    source_user_partial_hash: str
    orca_version: str
    resolver_version: str
    snapshot_hash: str
    created_at: str


class SlicerProfileBundle(BaseModel):
    """Internal, content-addressed resolved bundle (append-only; AC-6).

    Identity IS ``bundle_hash``. ``spoolman_overrides_ref`` is absent when no
    override layer was applied (the no-op provider path). The full resolved triple
    is inlined (the resolved JSON is the portable artifact per Decision AH § 7).
    """

    bundle_hash: str
    orca_version: str
    machine: dict
    process: dict
    filament: dict
    source_snapshot_ref: str
    spoolman_overrides_ref: str | None = None
    created_at: str


class ResolveReason(StrEnum):
    """Machine-readable classified-failure reason codes (AC-7).

    A resolve never returns a bare ``None`` (which a caller might misread as
    "fresh") and never silently falls back to a wrong default.
    """

    unsupported_material_class = "unsupported_material_class"
    missing_system_profile = "missing_system_profile"
    cli_validation_failed = "cli_validation_failed"
    invalid_partial = "invalid_partial"


class ResolveFailure(BaseModel):
    """Typed classified failure — the no-silent-fallback contract (AC-7)."""

    reason: ResolveReason
    message: str


class ResolveSuccess(BaseModel):
    """A successful resolve: the persisted bundle + the resolved triple.

    ``from_cache`` is True when an exact pre-resolved bundle already existed for
    this content (the exact-bundle precedence branch short-circuited).
    """

    bundle: SlicerProfileBundle
    triple: ResolvedTriple
    from_cache: bool = Field(default=False)


# A resolve outcome is exactly one of success or classified failure.
ResolveOutcome = ResolveSuccess | ResolveFailure
