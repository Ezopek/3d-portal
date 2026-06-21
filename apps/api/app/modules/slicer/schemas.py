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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.slicer.models import EstimateFailureReason, MaterialClass, QualityTier

# The UI estimate status = the Decision AJ ``EstimateStatus`` lifecycle
# ``{fresh, stale, queued, failed}`` PLUS ``absent`` — a 200 store miss the read
# endpoint adds as a FIRST-CLASS UI empty state (AC-1/AC-3), distinct from a transport
# error and from ``failed``. ``loading`` is a query/transport state the FE owns; it is
# never a DTO value (the server never reports "loading").
UIEstimateStatus = Literal["fresh", "stale", "queued", "failed", "absent", "not_computed"]


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


class RecomputeRequest(BaseModel):
    """The guarded recompute POST body (EST-RECOMPUTE-1) — the SAME preset-resolution
    inputs the ``GET /api/estimates`` read endpoint takes, as a validated JSON body.

    ``extra="forbid"`` so an unexpected field is a 422, not a silently-ignored input. The
    ``stl_hash`` shape (64 lowercase hex) is re-validated in the handler via
    ``validate_content_hash`` BEFORE it is woven into any resolve/store/queue path — this DTO
    only carries it, it does not own the path-safety gate.
    """

    model_config = ConfigDict(extra="forbid")
    stl_hash: str
    material_class: MaterialClass
    quality_tier: QualityTier
    printer_ref: str
    spoolman_filament_ref: str | None = None


class QualityTierAvailability(BaseModel):
    """A UI-safe availability projection for one portal quality tier.

    EST-TIERS-1 uses this bridge contract so the frontend can render only tiers whose
    process profile is currently resolvable for ``(printer_ref, material_class)`` without
    probing ``GET /api/estimates`` and turning missing vendored profiles into a user-facing
    422. ``reason`` is intentionally short and generic — it carries no filesystem path or
    Orca internals.
    """

    model_config = ConfigDict(extra="forbid")
    quality_tier: QualityTier
    available: bool
    reason: str | None = None


class QualityTierAvailabilityResponse(BaseModel):
    """Resolvable quality-tier set for one printer/material pair (EST-TIERS-1)."""

    model_config = ConfigDict(extra="forbid")
    printer_ref: str
    material_class: MaterialClass
    tiers: list[QualityTierAvailability]


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
    offer_id: str | None = None


# --- Story 33.1 (Decision AK, OD-7) — read-only admin profile inventory DTOs --------
#
# The admin-facing per-slot projection over the resolver. Like every DTO in this module
# it is ``extra="forbid"`` and carries ONLY the projected fields — no Orca-internal keys,
# no filesystem paths, no g-code, no raw profile bodies (the AC-9 no-leak fence, mirrored
# by the negative-assertion test). It is a SUPERSET projection: ``resolvable`` reuses the
# same resolve seam as ``GET /api/estimates/quality-tiers`` (AC-6 parity); ``imported`` +
# ``compatible`` + ``provenance`` are added on top.

# The single primary status per slot, by the AC-4 precedence
# (Incompatible → Not imported → Not resolvable → Offerable).
AdminProfileStatus = Literal["offerable", "not_imported", "not_resolvable", "incompatible"]


class AdminProfileProvenance(BaseModel):
    """The leak-fenced provenance of a resolved profile (AC-9).

    Exposes ONLY the snapshot tree hash (content identity of the vendored system tree, may
    be truncated for display by the FE) and the Orca version. Both are ``None`` for a slot
    that does not resolve (no resolved profile ⇒ no provenance). NO Orca-internal profile
    keys, NO filesystem paths, NO g-code — the same FR20-PRESET-1 fence as ``EstimateView``.
    """

    model_config = ConfigDict(extra="forbid")
    source_system_tree_hash: str | None = None
    orca_version: str | None = None


class AdminProfileSlot(BaseModel):
    """One ``(material_class, quality_tier)`` slot in the admin inventory (AC-3).

    ``offerable === (imported and resolvable and compatible)``; ``status`` is the single
    primary status by the AC-4 precedence; ``reason`` is the structured category (the FE
    localizes it) and is non-null for every non-offerable slot. ``portal_label`` is the
    operator-assigned display label — reserved for the Story 33.3 label store, so ``None``
    in this read-only slice (the FE falls back to the localized tier label).
    """

    model_config = ConfigDict(extra="forbid")
    material_class: MaterialClass
    quality_tier: QualityTier
    imported: bool
    resolvable: bool
    compatible: bool
    offerable: bool
    status: AdminProfileStatus
    reason: str | None = None
    portal_label: str | None = None
    provenance: AdminProfileProvenance


class ProfileImportRejection(BaseModel):
    """Story 33.2 (AC-5/6/7, AC-18) — the structured rejection detail an import returns.

    Carried as the ``detail`` of the 413/422 ``HTTPException`` so the admin panel can localize
    *why* an import was rejected (admin fails closed/visible). ``reason_category`` is the
    machine-readable category the FE keys an i18n string off — one of ``too_large`` (413),
    ``invalid_partial`` / ``incompatible_for_material`` / ``unsupported_material_class`` /
    ``missing_system_profile`` / ``cli_validation_failed`` (422). ``message`` is a short,
    non-leaking diagnostic (no Orca-internal profile body, no filesystem path, no g-code).
    """

    model_config = ConfigDict(extra="forbid")
    reason_category: str
    message: str


# --- PROFILE-LIB-1 (Decision AM) — separate-block profile library DTOs --------
#
# The operator-facing curated projection over ONE imported Orca profile BLOCK (machine /
# process / filament). Like every DTO in this module it is ``extra="forbid"`` and carries
# ONLY curated metadata + validation state — NO raw Orca key body, NO filesystem path, NO
# g-code (the AC-13 leak fence, mirrored by a negative-assertion test). It coexists with the
# 33.1/33.2 grid DTOs (the compiled-intent projection) and never replaces them.

# The classified block type (SCP § 3 separate-block model).
ProfileLibraryType = Literal["machine", "process", "filament"]

# The per-block validation state (AC-4): classified+stored is at worst ``requires_attention``;
# ``error`` is the AC-2 unclassifiable reject path (never stored, surfaced only as a rejection).
ProfileLibraryValidationState = Literal["usable", "requires_attention", "error"]


class ProfileLibraryBlock(BaseModel):
    """One imported Orca profile block's curated metadata (AC-13).

    The single shape the list/get endpoints return, read from the on-disk curated manifest
    sidecar — NEVER from the raw Orca body (there is no raw-body read path in this story).
    ``reasons`` carries machine-readable categories the FE localizes (no display text from the
    backend). Carries no raw layer-height / temps / volumetric-speed / density / g-code / full
    Orca key set (FR20-PRESET-1 / NFR21-OBS-1 fence).
    """

    model_config = ConfigDict(extra="forbid")
    block_id: str
    profile_type: ProfileLibraryType
    name: str
    source: str | None = None
    is_system: bool = False
    inherit: str | None = None
    inherit_chain: list[str] = Field(default_factory=list)
    settings_id: str | None = None
    material_type: str | None = None
    compatible_printers: list[str] = Field(default_factory=list)
    validation_state: ProfileLibraryValidationState
    reasons: list[str] = Field(default_factory=list)
    portal_label: str | None = None
    imported_at: str
    imported_by: str
    stale_offers: list[dict] = Field(default_factory=list)
    # added 38.1: populated by import endpoint only; empty list for all other callers


class ProfileLibraryListResponse(BaseModel):
    """The imported-block inventory (PROFILE-LIB-1, AC-10).

    Deterministically ordered (process first, then name). A missing/empty ``library/`` tree ⇒
    an empty ``blocks`` list — the empty state IS an empty inventory.
    """

    model_config = ConfigDict(extra="forbid")
    blocks: list[ProfileLibraryBlock]


# --- PROFILE-OFFER-1 (Decision AN) — PrintProfileOffer / ProfileChain DTOs ----
#
# The curated offer/chain projection over the separate-block library. Like every DTO in this
# module it is ``extra="forbid"`` and carries ONLY curated offer config + the embedded chain
# refs + validation state + a leak-fenced ``chain_blocks`` echo of the referenced blocks'
# curated metadata — NO raw Orca key body, NO filesystem path, NO g-code (the AC-8 leak fence,
# mirrored by a negative-assertion test). It coexists with the 33.1/33.2 grid DTOs and the
# PROFILE-LIB-1 library DTOs and never replaces them.

OfferVisibility = Literal["hidden", "visible"]
OfferPublishState = Literal["published", "unpublished"]

# The per-offer validation state (AC-4): a stored offer is at worst ``invalid`` (a referenced
# block went missing / wrong-typed); ``requires_attention`` is stored + listed + flagged.
OfferValidationState = Literal["usable", "requires_attention", "invalid"]

# Added 38.1: sync state indicates whether the published offer still reflects current blocks.
OfferSyncState = Literal["current", "stale", "unknown"]


class ProfileChainRef(BaseModel):
    """The embedded triple of library block references (AC-2, AC-8).

    Each id is validated as a 32-char lowercase hex ``block_id`` (the same structural
    path-safe property the library mints) so a malformed ref is a 422 ``invalid_offer`` before
    it ever reaches the storage path. Carries no raw Orca body — only the three refs.
    """

    model_config = ConfigDict(extra="forbid")
    machine_block_id: str
    process_block_id: str
    filament_block_id: str

    @field_validator("machine_block_id", "process_block_id", "filament_block_id")
    @classmethod
    def _hex_block_id(cls, value: str) -> str:
        from app.modules.slicer.profile_library import is_valid_block_id

        if not is_valid_block_id(value):
            raise ValueError("block_id must be a 32-char lowercase hex string")
        return value


class PrintProfileOffer(BaseModel):
    """One ``PrintProfileOffer`` with its embedded chain + read-time validation (AC-8).

    The single shape the offer list/get/create/patch endpoints return. ``validation_state`` +
    ``reasons`` are RECOMPUTED at read time against the current library (AC-10) — a stale
    ``usable`` is never served after a referenced block changes. ``chain_blocks`` echoes the
    referenced blocks' curated metadata (reusing :class:`ProfileLibraryBlock`) so the FE can
    render the selected blocks WITHOUT a second round-trip and WITHOUT any raw Orca body; a
    missing referenced block is omitted from the echo (surfaced via the ``unknown_block``
    reason). ``label`` / block names / material types render as DATA (untranslated).
    """

    model_config = ConfigDict(extra="forbid")
    offer_id: str
    label: str
    description: str | None = None
    chain: ProfileChainRef
    visibility: OfferVisibility
    is_default: bool
    compatible_material_categories: list[str] = Field(default_factory=list)
    validation_state: OfferValidationState
    reasons: list[str] = Field(default_factory=list)
    chain_blocks: list[ProfileLibraryBlock] = Field(default_factory=list)
    created_at: str
    created_by: str
    updated_at: str
    publish_state: OfferPublishState = "unpublished"
    published_bundle_hash: str | None = None
    published_at: str | None = None
    published_by: str | None = None
    source_snapshot_ref: str | None = None
    published_stl_hash: str | None = None
    sync_state: OfferSyncState = "unknown"


class PrintProfileOfferListResponse(BaseModel):
    """The offer inventory (PROFILE-OFFER-1, AC-10).

    Deterministically ordered (by ``created_at`` then ``offer_id``). A missing/empty
    ``offers/`` tree ⇒ an empty ``offers`` list.
    """

    model_config = ConfigDict(extra="forbid")
    offers: list[PrintProfileOffer]


# --- Story 36.1 — safe member DTO for published print profile offers ----------
#
# Purposefully narrow: only the five fields the member picker needs. ``extra="forbid"``
# ensures any accidental extra field is caught at construction time. Every sensitive
# internal (bundle_hash, chain block IDs, sidecar paths, publish-state internals, raw
# Orca refs) is deliberately absent — the negative leak-fence test asserts their absence.


class MemberPublishedOfferView(BaseModel):
    """Safe member projection of one published print profile offer (Story 36.1, AC-10/11).

    Exposes ONLY the safe fields needed by the member picker. ``quality_tier`` and
    ``printer_name`` are nullable because they are derived from library block manifests
    that may be unavailable (chain validation failure does not block the member surface
    — the offer was already published). Fields absent from this DTO: bundle_hash,
    chain block IDs, sidecar paths/internals, publish-state internals, raw Orca refs.
    """

    model_config = ConfigDict(extra="forbid")
    offer_id: str
    portal_label: str
    quality_tier: str | None = None
    compatible_material_categories: list[str] = Field(default_factory=list)
    printer_name: str | None = None
    is_default: bool = False


class MemberPublishedOfferListResponse(BaseModel):
    """Published offer list for authenticated members (Story 36.1)."""

    model_config = ConfigDict(extra="forbid")
    offers: list[MemberPublishedOfferView]


class PrintProfileOfferCreate(BaseModel):
    """The create-offer request body (AC-9).

    ``visibility`` defaults ``hidden`` and ``is_default`` defaults ``false`` (a new offer is
    not published by default). ``compatible_material_categories`` is a plain ``list[str]`` here
    (NOT a ``Literal``) so an out-of-table category yields the structured
    ``422 unsupported_material_category`` from the handler's material gate rather than an opaque
    Pydantic enum error. ``extra="forbid"`` so an unexpected field is a 422 ``invalid_offer``.
    """

    model_config = ConfigDict(extra="forbid")
    label: str
    description: str | None = None
    chain: ProfileChainRef
    visibility: OfferVisibility = "hidden"
    is_default: bool = False
    compatible_material_categories: list[str] = Field(default_factory=list)


class PrintProfileOfferUpdate(BaseModel):
    """The patch-offer request body (AC-12) — label/visibility/default/categories ONLY.

    The chain (block refs) is IMMUTABLE on PATCH: changing the selected blocks means deleting
    the offer and creating a new one (keeps ``offer_id`` ↔ chain identity simple; chain
    mutation/versioning is deferred, SCP § 9). Every field is optional (partial update);
    ``extra="forbid"`` so an attempt to PATCH ``chain`` (or any unknown field) is a 422.
    """

    model_config = ConfigDict(extra="forbid")
    label: str | None = None
    description: str | None = None
    visibility: OfferVisibility | None = None
    is_default: bool | None = None
    compatible_material_categories: list[str] | None = None


class OfferPublishRequest(BaseModel):
    """PROFILE-PUBLISH-1 publish request.

    ``stl_hash`` is optional; absent means the operator-selected G-DATA default for this
    slice. It is validated at the service boundary before any path is built.
    """

    model_config = ConfigDict(extra="forbid")
    stl_hash: str | None = None


class OfferPublishResult(BaseModel):
    """The curated result of publishing one offer chain to a real bundle.

    Carries the bundle hash + queue job id needed by the admin surface, and never carries
    raw Orca body, filesystem path, queue payload internals beyond the deterministic job id,
    or g-code.
    """

    model_config = ConfigDict(extra="forbid")
    offer_id: str
    published_bundle_hash: str
    publish_state: OfferPublishState
    published_at: str
    estimate_job_id: str
    estimate: EstimateView | None = None


class AdminProfileInventoryResponse(BaseModel):
    """The full per-slot inventory for one printer (Story 33.1, FR21-PROFILE-INVENTORY-1).

    Enumerates EVERY slot over the named ``MATERIAL_CLASSES x QUALITY_TIER_ORDER`` grid —
    including structurally-incompatible and not-imported slots — so the admin grid renders
    the complete matrix (no blank cells; the empty state IS the all-not-imported grid).
    """

    model_config = ConfigDict(extra="forbid")
    printer_ref: str
    slots: list[AdminProfileSlot]


class RecomputeResponse(BaseModel):
    """The guarded recompute POST response (EST-RECOMPUTE-1).

    Carries the FACT that a re-slice was enqueued ON THIS CALL (``enqueued``) plus the honest
    projected estimate state (``estimate`` — the SAME UI-safe ``EstimateView`` the read
    endpoint returns). ``enqueued`` is ``False`` only when the record is already ``queued`` (a
    recompute is in flight, so the call is an idempotent no-op — the R1 self-DoS guard); it is
    ``True`` for the ``fresh``/``stale``/``failed``/``absent`` enqueue paths.

    No ``bundle_hash`` / ``job_id`` / queue-name / settings_ids / g-code crosses the wire — the
    same FR20-PRESET-1 no-internal-leak contract as ``EstimateView`` (``enqueued`` is the only
    addition, a plain boolean carrying no slicer internals).
    """

    model_config = ConfigDict(extra="forbid")
    enqueued: bool
    estimate: EstimateView


class OfferRecomputeRequest(BaseModel):
    """Body for POST /api/admin/profiles/offers/recompute-estimates."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    visible_only: bool = True
    offer_id: str | None = None
    max_cells: int | None = None


class OfferEstimateRecomputeResponse(BaseModel):
    """Classified counters for offer-driven estimate recompute preview/enqueue."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool
    inspected: int = 0
    cells_total: int = 0
    cells_resolved: int = 0
    cells_resolve_failed: int = 0
    enqueued: int = 0
    already_fresh: int = 0
    missing_stl: int = 0
    errors: int = 0
    would_enqueue: int = 0
