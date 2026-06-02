"""Spoolman override-layer seam (Story 32.1, AC-8).

Designed now so Story 32.5 (the real Spoolman-backed provider, reusing the Init
19 ``spools`` client) slots in WITHOUT reshaping the resolver. This story ships
only the interface + a no-op default + the pure application/fingerprint helpers,
and proves the seam is DI-clean (an injected override lands in the filament JSON
and changes ``bundle_hash``).

Out of scope here: the live Spoolman read + the real ``filament.extra`` mapping
(Story 32.5).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.modules.slicer.models import FilamentOverrides, PrintIntentPreset
from app.modules.spools.models import SpoolmanFilament

if TYPE_CHECKING:
    # Type-only import — kept out of runtime so the resolve path (incl. the slicer worker)
    # never pulls Redis/httpx in just to import this module. The builder receives a live
    # ``SpoolsService`` instance from the caller; it never constructs one.
    from app.modules.spools.service import SpoolsService

logger = logging.getLogger(__name__)

# Map of FilamentOverrides field → Orca filament JSON key. Orca stores these as
# single-element string arrays (e.g. ``["12"]``), so applied values are wrapped
# to match the resolved-profile shape. Identity-named for now (Story 32.5 owns
# the real Spoolman ``filament.extra`` → Orca-key mapping logic).
_OVERRIDE_TO_ORCA_KEY = {
    "filament_max_volumetric_speed": "filament_max_volumetric_speed",
    "nozzle_temperature": "nozzle_temperature",
    "hot_plate_temp": "hot_plate_temp",
    "filament_density": "filament_density",
}


@runtime_checkable
class OverrideProvider(Protocol):
    """The override-layer interface the resolver consumes."""

    def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None:
        """Return the override set pinning a spool for ``intent``, or ``None``."""
        ...


class NoopOverrideProvider:
    """Default provider returning ``None`` — the MVP path until Story 32.5.

    With this provider the resolved filament is override-free and
    ``spoolman_overrides_ref`` is absent, so the hash is identical to a plain
    no-override resolve.
    """

    def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None:
        return None


def apply_filament_overrides(filament: dict, overrides: FilamentOverrides) -> dict:
    """Apply set override fields onto the filament JSON (AC-8). New dict; no mutation.

    Only fields that are set (non-``None``) are applied; each is written as a
    single-element string array to match Orca's resolved-filament shape.
    """
    out = dict(filament)
    payload = overrides.model_dump(exclude_none=True)
    for field, value in payload.items():
        orca_key = _OVERRIDE_TO_ORCA_KEY[field]
        out[orca_key] = [str(value)]
    return out


def overrides_fingerprint(overrides: FilamentOverrides) -> str:
    """Stable content id of the applied override set → ``spoolman_overrides_ref``.

    Folded into the bundle so a later mapped-field change re-hashes (the trigger
    Story 32.4 invalidation consumes). Canonical JSON (sorted keys) over the set
    fields only, sha256-hashed.
    """
    payload = overrides.model_dump(exclude_none=True)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- Story 32.5 (Decision AJ) — the real filament.extra → FilamentOverrides mapping --
#
# Spoolman → FilamentOverrides field map. because "the FR20-SPOOLMAN-MAP-1 mapped-field
# set — the exact slicer-output-affecting fields Spoolman pins (volumetric speed / nozzle
# temp / bed temp / density for TPU & unusual filaments); the key names ARE the
# portal↔Spoolman naming convention, a Spoolman-side rename is a coordinated change not a
# silent drift". The default convention is identity-named: ``extra["nozzle_temperature"]``
# → ``FilamentOverrides.nozzle_temperature``. Each entry pairs the override field with its
# coercion target (``float`` for speed/density, ``int`` for the integral temps).
_SPOOLMAN_EXTRA_TO_OVERRIDE: dict[str, tuple[str, type]] = {
    "filament_max_volumetric_speed": ("filament_max_volumetric_speed", float),
    "nozzle_temperature": ("nozzle_temperature", int),
    "hot_plate_temp": ("hot_plate_temp", int),
    "filament_density": ("filament_density", float),
}


def _coerce_override_value(decoded: object, target: type) -> int | float | None:
    """Coerce a json.loads'd ``extra`` value to ``target``, or ``None`` if out-of-domain.

    The data-integrity guard (AC-2): never apply a garbage/zero/nan/negative override. A
    bool (a JSON ``true``/``false`` — an ``int`` subclass that must NOT silently become 1),
    a non-number, a non-finite (``nan``/``inf``), a non-positive value (the no-silent-zero
    rule — a zero/negative speed/temp/density is physically meaningless), or a non-integral
    value for an integer temp field all yield ``None`` (the field is left unset).
    """
    if isinstance(decoded, bool) or not isinstance(decoded, (int, float)):
        return None
    number = float(decoded)
    if not math.isfinite(number) or number <= 0:
        return None
    if target is int:
        if number != int(number):
            return None
        return int(number)
    return number


def map_filament_extra(extra: dict[str, str]) -> FilamentOverrides:
    """Pure ``filament.extra`` → ``FilamentOverrides`` mapper (Story 32.5 AC-2).

    Reads the mapped override keys (``_SPOOLMAN_EXTRA_TO_OVERRIDE``) from ``extra`` —
    Spoolman serializes each value as a JSON-encoded string, so each is ``json.loads``'d
    then coerced + domain-guarded. A malformed / non-finite / wrong-type / out-of-domain
    value is DROPPED (its field stays ``None``) and a structured warning is logged
    (NFR20-OBS-1) — never a silent garbage override applied to the filament JSON. An absent
    key stays ``None``; an ``extra`` with no mapped keys yields an all-``None`` overrides
    (the provider treats that as "no override"). Pure + deterministic: same ``extra`` in ⇒
    same ``FilamentOverrides`` out, no clock, no external read.
    """
    fields: dict[str, int | float] = {}
    for extra_key, (field_name, target) in _SPOOLMAN_EXTRA_TO_OVERRIDE.items():
        if extra_key not in extra:
            continue
        try:
            decoded = json.loads(extra[extra_key])
        except (json.JSONDecodeError, TypeError):
            _warn_dropped_extra(extra_key, "malformed_json")
            continue
        coerced = _coerce_override_value(decoded, target)
        if coerced is None:
            _warn_dropped_extra(extra_key, "non_finite_or_out_of_domain")
            continue
        fields[field_name] = coerced
    return FilamentOverrides(**fields)


def _warn_dropped_extra(extra_key: str, reason: str) -> None:
    # Structured warning carrying ONLY the dropped key + a reason category — never the value
    # nor the whole ``extra`` map (AC-8: no Spoolman bodies in logs).
    logger.warning(
        "slicer.override_mapping dropped a malformed filament.extra value",
        extra={"labels.extra_key": extra_key, "labels.reason": reason},
    )


# --- Story 32.5 (AC-5) — the churn-stable profile-style reference link ----------------
#
# Unit-separator delimiter: an unambiguous join char that does not appear in Spoolman's
# descriptive fields, so the composite cannot be confused with a single field value.
_REF_DELIMITER = "\x1f"


def spoolman_filament_ref(filament: SpoolmanFilament) -> str:
    """Derive the churn-stable profile-style reference for a Spoolman filament (AC-5).

    because "Init 19 B2 profile-style-reference insight — link by a churn-stable profile
    ref, not the Spoolman integer entity id which re-keys on inventory edits; ONE function
    derives both the build-side map key and the lookup-side intent key so they cannot
    silently diverge". The ref is a ``vendor∥material∥name`` composite over the filament's
    stable descriptive fields — NEVER ``filament.id`` (the integer churns when inventory is
    re-keyed). A portal pin stores this exact string in
    ``PrintIntentPreset.spoolman_filament_ref``; the AC-4 builder keys its map by the same
    function, so build-side and lookup-side keys cannot diverge.
    """
    return _REF_DELIMITER.join((filament.vendor_name or "", filament.material or "", filament.name))


class SpoolmanOverrideProvider:
    """The real Spoolman-backed ``OverrideProvider`` — sync + pure (Story 32.5 AC-3).

    Constructed from a PRE-FETCHED, in-memory ``filaments_by_ref`` map (the async Spoolman
    read is hoisted to :func:`build_spoolman_override_provider`, AC-4), so ``overrides_for``
    stays synchronous + deterministic — it performs NO live external read at resolve time,
    mirroring ``VendoredProfileSource``'s snapshot discipline and keeping the Story 32.1
    resolver's sync ``override_provider`` contract unreshaped (AC-9).

    ``overrides_for`` returns the mapped overrides only when the intent pins a ref present in
    the map AND at least one field is set; otherwise ``None`` (the no-override path —
    byte-identical to ``NoopOverrideProvider``, no ``spoolman_overrides_ref``).
    """

    def __init__(self, filaments_by_ref: dict[str, SpoolmanFilament]) -> None:
        self._filaments_by_ref = filaments_by_ref

    def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None:
        ref = intent.spoolman_filament_ref
        if ref is None:
            return None
        filament = self._filaments_by_ref.get(ref)
        if filament is None:
            return None
        overrides = map_filament_extra(filament.extra)
        # An all-None mapping is "no override" — return None so the resolve stays
        # byte-identical to the no-op path (no spurious spoolman_overrides_ref).
        if not overrides.model_dump(exclude_none=True):
            return None
        return overrides


async def build_spoolman_override_provider(
    service: SpoolsService,
) -> SpoolmanOverrideProvider:
    """Build the provider from the Init 19 Redis-cached Spoolman snapshot (Story 32.5 AC-4).

    The SINGLE outbound-Spoolman touch in this story: it reads via the existing
    ``SpoolsService.get_summary()`` (read-only — reusing the Story 31.1 client + cache +
    circuit-breaker + leader-election; NO second poll, NO cache bypass, NO direct
    ``SpoolmanClient``). The instrumented read lives inside the Init 19 client; the builder
    adds one ``override_layer_resolved`` line (ok / degraded) tagged ``external_service=
    spoolman`` + the filament count — never filament bodies (NFR20-OBS-1 / AC-8).

    **Soft-fail (the external-boundary contract):** ``get_summary()`` returns ``None`` on
    cold-cache + Spoolman-down (FR19-FAILURE-1). The builder then returns a provider over an
    EMPTY map (every ``overrides_for`` ⇒ ``None`` ⇒ the downstream resolve produces the
    material-class-default bundle) and emits a ``degraded`` warning — an explicit, logged
    absence of the override, NOT a hard resolve failure and NOT a silent substitution that
    masquerades as the override bundle.
    """
    snapshot = await service.get_summary()
    if snapshot is None:
        logger.warning(
            "slicer.override_layer_resolved",
            extra={
                "labels.external_service": "spoolman",
                "labels.override_layer": "degraded",
                "labels.reason": "spoolman_unavailable",
                "labels.filament_count": 0,
            },
        )
        return SpoolmanOverrideProvider({})

    filaments_by_ref = {spoolman_filament_ref(f): f for f in snapshot.filaments}
    logger.info(
        "slicer.override_layer_resolved",
        extra={
            "labels.external_service": "spoolman",
            "labels.override_layer": "ok",
            "labels.filament_count": len(filaments_by_ref),
        },
    )
    return SpoolmanOverrideProvider(filaments_by_ref)
