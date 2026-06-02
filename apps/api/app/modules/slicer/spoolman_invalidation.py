"""Spoolman change → estimate-recompute classification + dispatch (Story 32.5 AC-6).

This is the *wiring* Story 32.4 AC-7 explicitly deferred to Story 32.5: it supplies the
inputs the Story 32.4 ``recompute`` engine takes as caller-supplied (the derived
``price_per_gram`` and the old→new ``bundle_hash`` mapping), classifies a single filament's
old→new state into the cheap-vs-expensive recompute path, and dispatches into 32.4. It
CALLS the 32.4 engine — it does NOT edit ``recompute.py`` (AC-9).

Two paths, the load-bearing OD-7 distinction (the R1 self-DoS guard, now *wired*):

- **mapped-field change** (a delta in ``map_filament_extra`` — volumetric speed / nozzle
  temp / bed temp / **density**) ⇒ the slicer OUTPUT changes ⇒ re-hash ⇒
  ``invalidate(trigger=spoolman_mapped_override, …, new_bundle_hash=<new>)`` (mark the old
  record stale + enqueue the new key). The new ``bundle_hash`` is computed HERE by
  re-resolving the intent with the NEW override (Story 32.1 ``resolve``).
- **price/weight-only change** (mapped overrides identical, the derived ``price_per_gram``
  differs) ⇒ ``invalidate(trigger=spoolman_cost_only, …, price_per_gram=<new>)`` — pure
  post-slice arithmetic, NO re-slice, NO enqueue. A Spoolman price tick can NEVER trigger a
  re-slice storm.

``affected_keys`` is caller-supplied (the same boundary 32.4 drew): this module proves the
dispatch correct; the live poll-diff + reverse-index event source that enumerates which
estimate keys depend on a given filament is explicitly DEFERRED (recorded in
``deferred-work.md``). Spoolman is consumed READ-ONLY — this module never writes to Spoolman
and never imports a write surface (there is none).

[Source: architecture.md § Decision AJ — recompute-trigger table rows "Spoolman mapped-
override change" + "Spoolman cost-only change (spool.price; density unchanged) — OD-7"]
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

from app.modules.slicer import recompute
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import EstimateRecord, PrintIntentPreset, ResolveSuccess
from app.modules.slicer.overrides import (
    SpoolmanOverrideProvider,
    map_filament_extra,
    spoolman_filament_ref,
)
from app.modules.slicer.recompute import RecomputeTrigger
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.validation import NullCliValidator
from app.modules.spools.models import SpoolmanFilament

logger = logging.getLogger(__name__)


def filament_price_per_gram(
    filament: SpoolmanFilament, *, spool_price: float | None = None
) -> float | None:
    """Derive ``price_per_gram = price / weight`` with the no-silent-zero/nan guard (AC-6).

    because "OD-7 / Decision AJ cost-only-arithmetic rule — cost is post-slice arithmetic
    ``mass x price/gram``; deriving the per-gram rate from the Spoolman spool price / net
    filament weight is the price source 32.4 AC-7 deferred to this story; ``weight > 0`` +
    finite + non-negative is the no-silent-zero/nan guard". Units contract: *grams x
    (currency per gram) = currency* (mirrors 32.4 AC-7).

    ``price`` = per-spool currency (a ``spool.price`` override takes precedence when given);
    ``weight`` = filament net grams. ``price`` and ``weight`` MUST be finite and non-negative
    and ``weight > 0``; ANY violation ⇒ ``None`` (the caller skips the cost recompute rather
    than feeding ``0``/``nan``/``inf``/negative into the 32.4 arithmetic).
    """
    price = spool_price if spool_price is not None else filament.price
    weight = filament.weight
    if price is None or weight is None:
        return None
    if not (math.isfinite(price) and math.isfinite(weight)):
        return None
    if price < 0 or weight <= 0:
        return None
    return price / weight


def classify_spoolman_delta(
    old: SpoolmanFilament, new: SpoolmanFilament
) -> RecomputeTrigger | None:
    """Classify a single filament's old→new state into a recompute trigger (the chokepoint).

    The cheap-vs-expensive decision (AC-6):

    - any **mapped-field** change (a delta in ``map_filament_extra(old.extra)`` vs
      ``map_filament_extra(new.extra)`` — volumetric speed / temps / **density**) ⇒
      ``spoolman_mapped_override`` (slicer output changes ⇒ re-hash ⇒ re-slice). A
      simultaneous price change rides along in the re-slice's fresh estimate — mapped wins.
    - else a **price/weight-only** change (the derived ``price_per_gram`` differs, mapped
      overrides identical) ⇒ ``spoolman_cost_only`` (OD-7 arithmetic, density unchanged).
    - else (no relevant change — an irrelevant field like color) ⇒ ``None`` (no-op).

    Spool-level fields such as ``lot_nr`` / ``last_used`` live on ``SpoolmanSpool`` and never
    reach this filament-level classifier, so they can never trigger an invalidation.
    """
    if map_filament_extra(old.extra) != map_filament_extra(new.extra):
        return RecomputeTrigger.spoolman_mapped_override
    if filament_price_per_gram(old) != filament_price_per_gram(new):
        return RecomputeTrigger.spoolman_cost_only
    return None


def _new_bundle_hash(
    intent: PrintIntentPreset,
    new: SpoolmanFilament,
    *,
    source: VendoredProfileSource,
    bundle_store: BundleStore,
    orca_version: str,
) -> str | None:
    """Compute the NEW ``bundle_hash`` by re-resolving the intent with the NEW override.

    The old→new bundle mapping 32.4 AC-7 said "is computed by Story 32.5 linkage and passed
    in". The intent is pinned to ``new``'s ref so the new override is applied; a classified
    resolve failure ⇒ ``None`` (the caller skips that dispatch rather than invalidate against
    a bogus hash).
    """
    pinned = intent.model_copy(update={"spoolman_filament_ref": spoolman_filament_ref(new)})
    provider = SpoolmanOverrideProvider({spoolman_filament_ref(new): new})
    outcome = resolve(
        pinned,
        source=source,
        store=bundle_store,
        override_provider=provider,
        validator=NullCliValidator(),
        orca_version=orca_version,
    )
    if isinstance(outcome, ResolveSuccess):
        return outcome.bundle.bundle_hash
    return None


async def apply_spoolman_filament_change(
    store: EstimateStore,
    arq_pool: Any,
    *,
    intent: PrintIntentPreset,
    old: SpoolmanFilament,
    new: SpoolmanFilament,
    source: VendoredProfileSource,
    bundle_store: BundleStore,
    orca_version: str,
    affected_keys: Sequence[tuple[str, str]],
) -> list[EstimateRecord | None]:
    """Classify the old→new filament change and dispatch into the Story 32.4 engine (AC-6).

    - ``spoolman_mapped_override`` → re-resolve to the NEW ``bundle_hash`` then
      ``invalidate_bulk`` over ``(stl_hash, old_bundle_hash, new_bundle_hash)`` triples (32.4
      marks each OLD record stale + enqueues + marks the NEW key queued — the old/new path).
    - ``spoolman_cost_only`` → derive the guarded ``price_per_gram`` then ``invalidate_bulk``
      over ``(stl_hash, bundle_hash)`` pairs (32.4 recomputes cost in place — NO enqueue, NO
      re-slice; the R1 self-DoS guard). A non-derivable ``price_per_gram`` ⇒ skip (never feed
      a poisoned value to 32.4).
    - ``None`` ⇒ no dispatch (no store write, no enqueue).

    ``affected_keys`` is caller-supplied (the live event source is deferred). Emits ONE
    classification line (AC-8); the per-invalidation lines come from the 32.4 engine, not
    re-emitted here.
    """
    trigger = classify_spoolman_delta(old, new)
    ref = spoolman_filament_ref(new)

    if trigger is None:
        _emit_classification(ref, trigger=None, key_count=len(affected_keys))
        return []

    if trigger == RecomputeTrigger.spoolman_mapped_override:
        new_hash = _new_bundle_hash(
            intent, new, source=source, bundle_store=bundle_store, orca_version=orca_version
        )
        if new_hash is None:
            # The intent no longer resolves with the new override (a classified failure) —
            # skip rather than invalidate against a bogus hash. Surfaced, not silent.
            _emit_classification(
                ref, trigger=trigger, key_count=0, note="reslice_target_unresolved"
            )
            return []
        _emit_classification(ref, trigger=trigger, key_count=len(affected_keys))
        keys = [(stl_hash, old_bundle, new_hash) for stl_hash, old_bundle in affected_keys]
        return await recompute.invalidate_bulk(store, arq_pool, trigger=trigger, keys=keys)

    # spoolman_cost_only — the cheap arithmetic path (NO enqueue, NO re-slice).
    price_per_gram = filament_price_per_gram(new)
    if price_per_gram is None:
        # No silently-poisoned cost handed to 32.4 — skip the recompute, log the reason.
        _emit_classification(ref, trigger=trigger, key_count=0, note="price_per_gram_unguarded")
        return []
    _emit_classification(ref, trigger=trigger, key_count=len(affected_keys))
    return recompute.recompute_cost_only_bulk(
        store, list(affected_keys), price_per_gram=price_per_gram
    )


def _emit_classification(
    ref: str,
    *,
    trigger: RecomputeTrigger | None,
    key_count: int,
    note: str | None = None,
) -> None:
    # One structured line per classification decision so a dashboard can confirm price ticks
    # never hit the slicer queue (the R1 guard is observable). Carries the ref + the resulting
    # trigger kind + the affected-key count — NEVER the Spoolman price/extra VALUES (AC-8).
    extra: dict[str, Any] = {
        "labels.spoolman_filament_ref": ref,
        "labels.trigger": trigger.value if trigger is not None else "none",
        "labels.affected_key_count": key_count,
    }
    if note is not None:
        extra["labels.note"] = note
    logger.info("slicer.spoolman_classification", extra=extra)
