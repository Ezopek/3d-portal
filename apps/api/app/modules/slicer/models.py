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


# --- Story 32.2 (Decision AI) — slice invocation result/failure model ----------
#
# The worker classifies EVERY outcome into a typed ``SliceOutcome`` — never a bare
# ``None``/0 a caller could misread as a valid estimate (FR20-FAILURE-1, AC-6). The
# taxonomy is designed to EXTEND, not reshape: Story 32.3 adds a ``parse_failure``
# reason for g-code-metadata parse errors without changing ``SliceOutcome``'s shape.


class SliceStatus(StrEnum):
    """Top-level slice outcome (AC-6).

    ``ok`` and ``warning`` both mean the slice produced valid g-code; ``warning``
    additionally carries non-blocking Orca warnings (surfaced non-blocking by Story
    32.6). ``failed`` always carries a machine-readable ``SliceFailureReason``.
    """

    ok = "ok"
    warning = "warning"
    failed = "failed"


class SliceFailureReason(StrEnum):
    """Machine-readable slice-INVOCATION failure reasons (AC-6).

    Scope: invocation outcomes only. g-code metadata-parse failure is classified by
    the Story 32.3 parser (a future ``parse_failure`` reason), NOT here.

    The taxonomy EXTENDS without reshaping ``SliceOutcome``: ``info_precheck_failed``,
    ``launch_error`` and ``missing_gcode`` were added as Story 32.2 review fixes to
    keep the no-silent-zero contract total — a non-zero ``--info`` precheck, an Orca
    process that fails to launch, and an exit-0 slice that emits no g-code were each
    previously able to leak past classification.
    """

    non_manifold = "non_manifold"
    # --info precheck exited non-zero — its manifold verdict is unreliable, so the
    # full slice MUST NOT run on its say-so (review fix #4).
    info_precheck_failed = "info_precheck_failed"
    non_zero_exit = "non_zero_exit"
    cli_rejected_profile = "cli_rejected_profile"
    # Orca could not be launched at all (FileNotFoundError/PermissionError/OSError
    # from the runner) — a bad entrypoint/perms, never an uncaught arq exception
    # (review fix #3).
    launch_error = "launch_error"
    # Orca exited 0 but produced no g-code — there is NO parser input, so an ``ok``
    # here would be a plausible-but-wrong silent zero downstream (review fix #1).
    missing_gcode = "missing_gcode"
    missing_stl = "missing_stl"
    missing_bundle = "missing_bundle"
    timeout = "timeout"


class SliceWarning(BaseModel):
    """A single non-blocking Orca slice warning (e.g. floating cantilever)."""

    message: str


class SliceOutcome(BaseModel):
    """Typed classified result of one slice job — the no-silent-zero contract (AC-6).

    A failed/timed-out slice NEVER returns success-with-zero: ``status`` is
    ``failed`` with a ``reason`` so Story 32.6 can render "couldn't estimate, here's
    why". ``gcode_temp_ref`` is a TRANSIENT reference to the in-job temp g-code (the
    Story 32.3 parser-sink hand-off); the file itself is discarded at job end (OD-5
    parse-and-discard, AC-5), so the ref points at an already-deleted path once the
    job returns. Timing/identity fields are observability metadata (AC-8) and are
    excluded from determinism assertions (AC-11).
    """

    status: SliceStatus
    reason: SliceFailureReason | None = None
    warnings: list[SliceWarning] = Field(default_factory=list)
    gcode_temp_ref: str | None = None
    manifold: bool | None = None
    slice_wall_ms: int | None = None
    stl_hash: str | None = None
    bundle_hash: str | None = None
    orca_version: str | None = None
