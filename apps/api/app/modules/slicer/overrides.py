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
from typing import Protocol, runtime_checkable

from app.modules.slicer.models import FilamentOverrides, PrintIntentPreset

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
