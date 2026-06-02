"""Story 32.6 (AC-1, AC-5) — the estimate read service: resolve a ``PrintIntentPreset``
to its ``bundle_hash``, read the persisted ``EstimateRecord`` by content key, and
project it onto the UI-safe DTO — exposing ONLY what the UI needs.

This module is CALLED by ``router.py``; it CALLS the Story 32.1 ``resolve`` +
Story 32.3 ``EstimateStore.read`` + Story 32.5 ``map_filament_extra`` / Spoolman
override provider. It does NOT re-implement hashing (the bundle_hash derivation is
``resolver.resolve``, the SAME path Story 32.5's dispatch uses) and it edits NONE of
the engine modules (AC-9).

The projection + override-context builders are PURE (no clock, no I/O), so they are
unit-testable directly; the production resolver (``SettingsEstimateResolver``) is the
only impure part (it reads vendored profiles + the Redis-cached Spoolman snapshot,
exactly as ``spoolman_invalidation`` / the spools router do).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.models import (
    EstimateRecord,
    PrintIntentPreset,
    ResolveSuccess,
    SlicerProfileBundle,
    SourceProfileSnapshot,
)
from app.modules.slicer.overrides import (
    NoopOverrideProvider,
    SpoolmanOverrideProvider,
    map_filament_extra,
    spoolman_filament_ref,
)
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.schemas import (
    EstimateView,
    OverrideContextView,
    WarningView,
)
from app.modules.slicer.validation import NullCliValidator
from app.modules.spools.models import SpoolmanFilament

# The stable warning category the FE keys an icon/label off — because "FR20-FAILURE-1
# warnings are non-blocking Orca slice warnings; the internal SliceWarning carries only
# free Orca text (the message), so the UI code is a single constant category, not a
# per-warning taxonomy the backend does not have". A real taxonomy would be a backend
# change, not a UI guess.
SLICE_WARNING_CODE = "slice_warning"

# The informational cost currency. ``None`` because "no portal currency SoT exists yet
# — ``filament_cost`` is INFORMATIONAL (AC-9, never a quote); the DTO carries a
# ``currency`` slot for the future Phase-D cost UX, but this story has no currency
# source to fill it honestly, so it is left absent rather than guessed". NOT an
# arbitrary default — an explicit, contract-pointed absence.
ESTIMATE_CURRENCY: str | None = None

# The Spoolman ``filament.extra`` key carrying the purchase link Story 32.5 carries
# "along for the ride" (the JSON-encoded URL string). Story 32.6 surfaces it (AC-5).
_PURCHASE_URL_EXTRA_KEY = "url"
# URL schemes safe to render as an external ``<a href>`` — because "AC-5 surfaces the
# link as a plain external link, NOT parsed/validated beyond URL-safety; gating to
# http/https blocks javascript:/data: link-injection without parsing the URL further".
_SAFE_URL_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class ResolvedPreset:
    """The resolver port's result: the content key + the pinned filament (if any).

    ``bundle_hash`` is the Story 32.1 ``resolve`` output (the estimate-store read key);
    ``pinned_filament`` is the Spoolman filament the preset pins (``None`` when the
    preset has no pin), surfaced for the override-context panel (AC-5).
    """

    bundle_hash: str
    pinned_filament: SpoolmanFilament | None = None


class PresetResolveError(Exception):
    """The preset could not be resolved to a bundle (a classified resolve failure).

    Carries the machine-readable ``ResolveReason`` so the router can map it to a 422
    without leaking resolver internals.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"preset not resolvable: {reason}")
        self.reason = reason


@runtime_checkable
class EstimateResolver(Protocol):
    """The seam the router depends on (overridable in tests)."""

    async def resolve_preset(self, intent: PrintIntentPreset) -> ResolvedPreset: ...


# === pure projection =========================================================


def safe_purchase_url(extra: dict[str, str]) -> str | None:
    """Extract a URL-safe purchase link from ``filament.extra`` (AC-5), or ``None``.

    Spoolman serializes ``extra`` values as JSON-encoded strings. The value is parsed,
    required to be a ``str`` with an http/https scheme; anything else (absent key,
    malformed JSON, non-string, ``javascript:``/``data:`` scheme) ⇒ ``None`` — never a
    link the operator could be phished by.
    """
    raw = extra.get(_PURCHASE_URL_EXTRA_KEY)
    if raw is None:
        return None
    try:
        decoded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Tolerate a plain (non-JSON-encoded) string too — Spoolman extras are
        # JSON-encoded by contract, but a bare string must not crash the read.
        decoded = raw
    if not isinstance(decoded, str):
        return None
    scheme = urlsplit(decoded).scheme.lower()
    if scheme not in _SAFE_URL_SCHEMES:
        return None
    return decoded


def build_override_context(
    intent: PrintIntentPreset, pinned_filament: SpoolmanFilament | None
) -> OverrideContextView:
    """Build the UI-safe override-context block from the preset + the pinned filament.

    Always carries the material class + quality tier (known from the preset). When a
    filament is pinned, adds its human name, the FACT that custom overrides are applied
    (``map_filament_extra`` yields ≥1 set field), and the URL-safe purchase link — but
    NEVER the override VALUES (AC-5).
    """
    if pinned_filament is None:
        return OverrideContextView(
            material_class=intent.material_class,
            quality_tier=intent.quality_tier,
        )
    overrides = map_filament_extra(pinned_filament.extra)
    custom_applied = bool(overrides.model_dump(exclude_none=True))
    return OverrideContextView(
        material_class=intent.material_class,
        quality_tier=intent.quality_tier,
        pinned_filament_name=pinned_filament.name,
        custom_overrides_applied=custom_applied,
        purchase_url=safe_purchase_url(pinned_filament.extra),
    )


def project_estimate(
    record: EstimateRecord | None,
    *,
    override_context: OverrideContextView,
    currency: str | None = ESTIMATE_CURRENCY,
) -> EstimateView:
    """Project an ``EstimateRecord`` (or its absence) onto the UI-safe ``EstimateView``.

    A miss (``record is None``) ⇒ ``status="absent"`` with every numeric ``None`` — a
    first-class UI empty state, not a 404. A present record projects its status +
    numerics + warnings + ``failure_reason``; the ``settings_ids`` / ``bundle_hash`` /
    Orca-key fields are simply not read (they have no DTO slot). For a ``failed`` record
    the numerics are already ``None`` by the model invariant — they project as ``None``,
    never ``0``.
    """
    if record is None:
        return EstimateView(
            status="absent",
            override_context=override_context,
            currency=currency,
        )
    return EstimateView(
        status=record.status.value,
        time_seconds=record.time_seconds,
        filament_g=record.filament_g,
        filament_mm=record.filament_mm,
        filament_cm3=record.filament_cm3,
        filament_cost=record.filament_cost,
        currency=currency,
        computed_at=record.computed_at,
        warnings=[WarningView(code=SLICE_WARNING_CODE, message=w.message) for w in record.warnings],
        failure_reason=record.reason,
        override_context=override_context,
    )


# === production resolver (impure — vendored profiles + Spoolman snapshot) =====


class _ReadOnlyBundleStore(BundleStore):
    """A ``BundleStore`` whose two persistence methods are no-ops — the read path is
    NON-MUTATING with respect to the real bundle-store artifacts (review blocker #1).

    ``GET /api/estimates`` is documented + intended read-only ("never enqueues, slices,
    or writes an estimate record"), but Story 32.1 ``resolve`` persists a freshly built
    bundle + provenance snapshot on a content MISS (its own provenance-cache write,
    ``write_snapshot`` / ``write_bundle``). On the read path that write must NOT happen:
    the endpoint only needs the computed ``bundle_hash`` to key the estimate-store read,
    and an absent estimate is a first-class empty state — not a reason to mutate the
    content volume from a GET.

    Overriding ONLY the two write methods to no-ops keeps the resolve precedence + the
    ``bundle_hash`` derivation byte-identical (``load_bundle`` still serves a content HIT
    from disk; the hash is computed the same way on a miss). ``resolve`` still returns a
    ``ResolveSuccess`` carrying the correct in-memory bundle, so the read path is
    unaffected beyond suppressing the side-effecting writes. The real (writing)
    ``BundleStore`` continues to back every OTHER caller (Story 32.5 dispatch, the
    worker, ``resolve_intent``) — this adapter is local to the read seam only.
    """

    def write_bundle(self, bundle: SlicerProfileBundle) -> Path:
        # No write — return the path the real store WOULD use, without touching disk.
        return self.bundle_path(bundle.bundle_hash)

    def write_snapshot(self, snapshot: SourceProfileSnapshot) -> Path:
        return self.snapshot_path(snapshot.snapshot_hash)


class SettingsEstimateResolver:
    """The production ``EstimateResolver``: resolve a preset to its bundle_hash.

    Builds the resolver dependencies from ``get_settings()`` (the vendored profile
    source + a READ-ONLY bundle store) and, when the preset pins a Spoolman filament,
    the real ``SpoolmanOverrideProvider`` from the Init 19 Redis-cached snapshot
    (read-only, via ``SpoolsService.get_summary`` — the SAME read the spools router +
    ``build_spoolman_override_provider`` use; NO second poll). It then CALLS Story 32.1
    ``resolve`` (the bundle_hash derivation is NOT re-implemented).

    The ``resolve`` call may, on a content miss, build a fresh bundle, but the store is a
    ``_ReadOnlyBundleStore`` whose ``write_bundle`` / ``write_snapshot`` are no-ops — so
    this read endpoint NEVER mutates the real bundle-store artifacts (review blocker #1).
    A content HIT is still served from disk; a miss just computes the ``bundle_hash``
    in-memory without persisting it. The endpoint also never writes an ``EstimateRecord``.
    """

    def __init__(self, *, redis_factory: object | None) -> None:
        self._redis_factory = redis_factory

    async def resolve_preset(self, intent: PrintIntentPreset) -> ResolvedPreset:
        settings = get_settings()
        source = VendoredProfileSource(settings.slicer_vendored_profiles_dir)
        # Read-only: a content miss must not append a bundle/snapshot from a GET.
        bundle_store = _ReadOnlyBundleStore(settings.slicer_bundle_store_dir)

        pinned_filament: SpoolmanFilament | None = None
        if intent.spoolman_filament_ref is not None:
            filaments_by_ref = await self._filaments_by_ref()
            pinned_filament = filaments_by_ref.get(intent.spoolman_filament_ref)
            provider: NoopOverrideProvider | SpoolmanOverrideProvider = SpoolmanOverrideProvider(
                filaments_by_ref
            )
        else:
            provider = NoopOverrideProvider()

        outcome = resolve(
            intent,
            source=source,
            store=bundle_store,
            override_provider=provider,
            validator=NullCliValidator(),
            orca_version=settings.orca_version,
        )
        if not isinstance(outcome, ResolveSuccess):
            raise PresetResolveError(outcome.reason.value)
        return ResolvedPreset(
            bundle_hash=outcome.bundle.bundle_hash,
            pinned_filament=pinned_filament,
        )

    async def _filaments_by_ref(self) -> dict[str, SpoolmanFilament]:
        """Read the Redis-cached Spoolman snapshot, keyed by the churn-stable ref.

        Read-only reuse of the Init 19 ``SpoolsService`` (Story 31.1 client + cache +
        circuit breaker), mirroring the spools router's ``async with SpoolmanClient``
        pattern. On cold-cache + Spoolman-down ``get_summary`` returns ``None``
        (FR19-FAILURE-1); we then key over an empty map (no pin resolves, the resolve
        degrades to the material-class-default bundle — never a hard failure).
        """
        if self._redis_factory is None:
            return {}
        # Imported lazily so the read path does not pull httpx/Redis at module import.
        from app.modules.spools.client import SpoolmanClient
        from app.modules.spools.service import SpoolsService

        settings = get_settings()
        async with SpoolmanClient(
            base_url=settings.spoolman_url,
            auth_token=settings.spoolman_auth_token,
        ) as client:
            service = SpoolsService(redis_factory=self._redis_factory, client=client)
            snapshot = await service.get_summary()
        if snapshot is None:
            return {}
        return {spoolman_filament_ref(f): f for f in snapshot.filaments}
