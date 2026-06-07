"""Selection sourcing for the profile policy (Story 35.2, Init 23, Decision AS).

The bridge between the Init 19 cached Spoolman snapshot and the Story 35.1
profile-selection policy:

- :func:`build_filaments_by_ref` maps a cached snapshot → a churn-stable
  ``spoolman_filament_ref → SpoolmanFilament`` map (reusing the ONE
  :func:`~app.modules.slicer.overrides.spoolman_filament_ref` function), soft-failing
  to an empty map when the snapshot is cold/unavailable;
- :func:`select_profile` derives a :class:`~app.modules.slicer.profile_policy.ProfileSelection`
  from a selected filament ref + that map, reading the filament's generic material from
  the snapshot (snapshot material wins over the caller fallback) and delegating precedence
  to the shipped, pure ``ProfilePolicy.resolve_selection`` — it re-implements NO precedence.

There is NO live Spoolman read here: the map is PRE-FETCHED by the caller (mirroring
``SpoolmanOverrideProvider`` / ``build_spoolman_override_provider``), so the resolve path
stays synchronous + deterministic. The resolver consumes the resulting ``ProfileSelection``
via its opt-in ``profile_selection`` seam (resolver.py).

Observability (NFR23-OBS-1): the snapshot-boundary log carries the filament COUNT + a
reason category only — never filament names/bodies (mirrors Init 20 NFR20-OBS-1 / the
``build_spoolman_override_provider`` log shape).

[Source: architecture.md § Initiative 23 Decision AS clause 5; SCP 2026-06-07 § Task 3]
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.slicer.overrides import spoolman_filament_ref
from app.modules.slicer.profile_policy import ProfilePolicy, ProfileSelection

if TYPE_CHECKING:
    from app.modules.spools.models import SpoolmanFilament, SpoolmanSnapshot

logger = logging.getLogger(__name__)


def build_filaments_by_ref(
    snapshot: SpoolmanSnapshot | None,
) -> dict[str, SpoolmanFilament]:
    """Map a cached Spoolman snapshot → ``{spoolman_filament_ref(f): f}`` (AC-9).

    Reuses the single churn-stable ref function so build-side and lookup-side keys cannot
    diverge. **Soft-fail:** a ``None`` snapshot (cold cache / Spoolman down per
    FR19-FAILURE-1) returns an EMPTY map and logs a ``degraded`` reason — an explicit,
    logged absence, never an exception and never a guessed map (mirrors
    ``build_spoolman_override_provider``). Logs counts/reason only (NFR23-OBS-1).
    """
    if snapshot is None:
        logger.warning(
            "slicer.profile_selection.snapshot",
            extra={
                "labels.external_service": "spoolman",
                "labels.snapshot": "degraded",
                "labels.reason": "spoolman_unavailable",
                "labels.filament_count": 0,
            },
        )
        return {}
    by_ref = {spoolman_filament_ref(f): f for f in snapshot.filaments}
    logger.info(
        "slicer.profile_selection.snapshot",
        extra={
            "labels.external_service": "spoolman",
            "labels.snapshot": "ok",
            "labels.filament_count": len(by_ref),
        },
    )
    return by_ref


def select_profile(
    *,
    policy: ProfilePolicy,
    spoolman_filament_ref: str | None,
    fallback_material: str | None = None,
    filaments_by_ref: dict[str, SpoolmanFilament] | None = None,
) -> ProfileSelection:
    """Resolve a :class:`ProfileSelection` for a selected filament (AC-10, AC-11).

    The generic material fed to the policy is read from the snapshot map for a present,
    found ref (the snapshot material is authoritative — it WINS over ``fallback_material``);
    when the ref is absent / the map is empty / the snapshot was cold, the caller-supplied
    ``fallback_material`` is used (e.g. the intent's material class). Precedence
    (exact override > material default > unavailable) is delegated to the pure, shipped
    ``ProfilePolicy.resolve_selection`` — this helper adds NO precedence logic. Pure +
    deterministic: same inputs ⇒ same selection, no clock, no live read.
    """
    material = fallback_material
    if spoolman_filament_ref and filaments_by_ref:
        filament = filaments_by_ref.get(spoolman_filament_ref)
        if filament is not None and filament.material:
            material = filament.material
    return policy.resolve_selection(material=material, spoolman_filament_ref=spoolman_filament_ref)
