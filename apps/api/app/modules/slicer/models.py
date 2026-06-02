"""Internal Pydantic shapes + typed resolver result/failure model (Story 32.1).

These are the data-model surfaces of Decision AH (architecture.md § Initiative
20). None of them is exposed over HTTP in this story — ``PrintIntentPreset`` is
user-facing in a *later* story; ``SlicerProfileBundle`` / ``SourceProfileSnapshot``
are internal provenance/reproducibility records and are never sent to the client.

[Source: architecture.md § Decision AH — data-model surfaces]
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    # Optional pin to a specific Spoolman filament record, linked by a stable PROFILE-STYLE
    # reference (Story 32.5 AC-5 / Init 19 B2) — NOT the churning integer ``SpoolmanFilament.id``.
    # ``None`` (the default) keeps every existing construction + ``frozen=True`` non-breaking
    # and resolves exactly as today (the no-override path). Story 32.6's selector writes it.
    spoolman_filament_ref: str | None = None


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


# --- Story 32.3 (Decision AJ) — typed estimate + parse-failure taxonomy ---------
#
# The g-code-metadata parse half of FR20-ESTIMATE-1: a typed ``EstimateRecord`` keyed
# on the complete ``(stl_hash, bundle_hash)`` reproducibility tuple, plus the parse
# failure taxonomy. The taxonomy is placed HERE on the estimate record — NOT bolted
# onto ``SliceFailureReason`` — so the slice-INVOCATION axis (Story 32.2) stays
# byte-unreshaped; parse failures and invocation failures are two orthogonal axes.


class EstimateStatus(StrEnum):
    """Lifecycle state of a persisted estimate (Decision AJ, AC-1).

    Story 32.3 writes only ``fresh`` (a clean parse) and ``failed`` (a classified parse
    failure). The ``stale``/``queued`` values exist now so Story 32.4 (invalidation /
    recompute) EXTENDS behavior, not shape — 32.3 never SETS them.
    """

    fresh = "fresh"
    stale = "stale"
    queued = "queued"
    failed = "failed"


class EstimateFailureReason(StrEnum):
    """Machine-readable g-code-metadata parse-failure reasons (AC-1, AC-4).

    This realizes the ``parse_failure`` reason the Story 32.2 ``SliceFailureReason``
    docstring reserved — on the ESTIMATE record, never on ``SliceOutcome``. The granular
    reasons let Story 32.6 render "couldn't estimate, here's why" precisely.
    """

    parse_failure = "parse_failure"
    missing_metadata_line = "missing_metadata_line"
    unparseable_time = "unparseable_time"
    unparseable_numeric = "unparseable_numeric"


class EstimateRecord(BaseModel):
    """Typed per-STL estimate keyed ``(stl_hash, bundle_hash)`` (Decision AJ, AC-1).

    Identity IS the ``(stl_hash, bundle_hash)`` tuple — the complete reproducibility key
    (``bundle_hash`` already folds ``orca_version`` + the Spoolman-override set per Story
    32.1). ``computed_at`` is provenance metadata, EXCLUDED from any content-identity /
    dedup comparison (AC-6) and from determinism assertions (AC-12), mirroring the Story
    32.1 ``created_at``-excluded-from-hash discipline.

    On a ``failed`` record the numeric fields are ``None`` — NEVER ``0``. A zero is a
    plausible-but-wrong value a caller could spend/print against; ``None`` + ``reason`` is
    the no-silent-zero contract (FR20-ESTIMATE-1 / FR20-FAILURE-1 parse half).
    """

    stl_hash: str
    bundle_hash: str
    orca_version: str
    time_seconds: int | None = None
    filament_g: float | None = None
    filament_mm: float | None = None
    filament_cm3: float | None = None
    # filament_cost: INFORMATIONAL owner-side cost from the slice's own cost line; carried
    # so Story 32.4 can recompute it arithmetically (cost = mass x price/gram) WITHOUT
    # re-slicing (OD-7, NFR20-REPRODUCIBLE-1). Never a quote/checkout price.
    filament_cost: float | None = None
    # settings_ids: the {filament,print,printer}_settings_id g-code lines naming which
    # resolved profile produced this estimate (NFR20-ATTRIBUTION-1). Absent ids degrade
    # attribution but do not fail the record (AC-4).
    settings_ids: dict[str, str] = Field(default_factory=dict)
    warnings: list[SliceWarning] = Field(default_factory=list)
    status: EstimateStatus
    reason: EstimateFailureReason | None = None
    computed_at: str

    # The required numerics a successful (``fresh``) record must carry — the FR20-ESTIMATE-1
    # load-bearing fields (``filament_cost`` stays optional even on a fresh record).
    _FRESH_REQUIRED_NUMERICS: ClassVar[tuple[str, ...]] = (
        "time_seconds",
        "filament_g",
        "filament_mm",
        "filament_cm3",
    )
    # Every nullable numeric field — defense-in-depth non-finite gate (no nan/inf persisted).
    _NUMERIC_FIELDS: ClassVar[tuple[str, ...]] = (
        "time_seconds",
        "filament_g",
        "filament_mm",
        "filament_cm3",
        "filament_cost",
    )

    @field_validator("filament_g", "filament_mm", "filament_cm3", "filament_cost")
    @classmethod
    def _reject_non_finite(cls, value: float | None) -> float | None:
        # Defense-in-depth: a nan/inf that slipped past the parser must never be persisted
        # as an estimate number — nan poisons arithmetic, inf is a plausible-but-wrong
        # forever-print (mirrors the gcode_parse.py review-fix #1 gate at the model edge).
        if value is not None and not math.isfinite(value):
            raise ValueError("estimate numeric fields must be finite (never nan/inf)")
        return value

    @model_validator(mode="after")
    def _enforce_status_invariants(self) -> EstimateRecord:
        # A ``failed`` record is a no-silent-zero placeholder: it carries a classifying
        # reason and NO numbers (a number behind a failure status is exactly the
        # plausible-but-wrong value the contract forbids). A ``fresh`` record is the
        # inverse: every load-bearing numeric present + finite, and no failure reason.
        # ``stale``/``queued`` are Story 32.4-owned transitions — left unconstrained here
        # beyond the non-finite gate above.
        if self.status == EstimateStatus.failed:
            if self.reason is None:
                raise ValueError("a failed estimate record must carry a reason")
            present = [n for n in self._NUMERIC_FIELDS if getattr(self, n) is not None]
            if present:
                raise ValueError(
                    f"a failed estimate record must not carry numerics, got: {present}"
                )
        elif self.status == EstimateStatus.fresh:
            if self.reason is not None:
                raise ValueError("a fresh estimate record must not carry a failure reason")
            missing = [n for n in self._FRESH_REQUIRED_NUMERICS if getattr(self, n) is None]
            if missing:
                raise ValueError(
                    f"a fresh estimate record must carry every required numeric, missing: {missing}"
                )
        return self
