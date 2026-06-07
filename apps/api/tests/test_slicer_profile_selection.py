"""Tests for Story 35.2 — resolve the Orca filament profile by policy before bundle
materialization (Init 23 / Epic E35, architecture.md § Decision AS).

Two surfaces, both backend-only:

1. the pure selection-sourcing helpers (:func:`build_filaments_by_ref`,
   :func:`select_profile`) that map the Init 19 cached Spoolman snapshot → a
   churn-stable ``ref → filament`` map and derive a :class:`ProfileSelection`
   (snapshot material wins, soft-fail to a caller fallback) — AC-9..AC-13;
2. the resolver integration (the opt-in ``profile_selection`` seam, the filament
   ``inherit`` substitution, the shared/distinct bundle identities, the override
   ordering, the classified ``unavailable_no_profile`` absence, the result
   metadata, and the byte-identical legacy path) — AC-1..AC-8, AC-14.

The resolver core stays pure + offline: the override + CLI-validator layers are
injected fakes (no real Orca, no real Spoolman), mirroring test_slicer_resolver.py.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.models import (
    FilamentOverrides,
    PrintIntentPreset,
    ResolveFailure,
    ResolveReason,
    ResolveSuccess,
)
from app.modules.slicer.overrides import (
    NoopOverrideProvider,
    spoolman_filament_ref,
)
from app.modules.slicer.profile_policy import (
    EstimateProfileSource,
    FilamentOverride,
    MaterialDefault,
    ProfilePolicy,
    ProfileSelection,
)
from app.modules.slicer.profile_selection import build_filaments_by_ref, select_profile
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.validation import NullCliValidator
from app.modules.spools.models import SpoolmanFilament, SpoolmanSnapshot

PRINTER = "creality-k1-max-microswiss-hf"

# A policy with one material default (PLA → "Generic PLA") and two exact overrides:
# an exact override that ALSO points at "Generic PLA" (to prove the cache branch
# carries the supplied selection) and the PLA Matt exact override.
POLICY = ProfilePolicy(
    material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")},
    filament_overrides={
        "exact-generic": FilamentOverride(orca_filament_profile_ref="Generic PLA"),
        "matt-ref": FilamentOverride(orca_filament_profile_ref="PLA Matt"),
    },
)


# --- Spoolman snapshot fixtures -------------------------------------------------


def _filament(fid: int, name: str, vendor: str, material: str, **extra: str) -> SpoolmanFilament:
    return SpoolmanFilament(
        id=fid, name=name, vendor_name=vendor, material=material, extra=dict(extra)
    )


def _snapshot(*filaments: SpoolmanFilament) -> SpoolmanSnapshot:
    return SpoolmanSnapshot(
        spools=[], filaments=list(filaments), vendors=[], fetched_at=datetime.now(UTC)
    )


# --- AC-9: build_filaments_by_ref (snapshot → churn-stable ref map, soft-fail) ---


def test_build_filaments_by_ref_keys_by_spoolman_filament_ref():
    f1 = _filament(1, "Galaxy Black", "Rosa3D", "PLA")
    f2 = _filament(2, "Matt White", "Fiberlogy", "PLA")
    by_ref = build_filaments_by_ref(_snapshot(f1, f2))
    assert by_ref == {spoolman_filament_ref(f1): f1, spoolman_filament_ref(f2): f2}


def test_build_filaments_by_ref_none_snapshot_is_empty_map_soft_fail():
    # Cold cache / Spoolman down ⇒ empty map, never an exception (mirrors
    # build_spoolman_override_provider's degraded path).
    assert build_filaments_by_ref(None) == {}


# --- AC-13: NFR23-OBS-1 — counts/reason only, never filament bodies --------------


def test_build_filaments_by_ref_logs_counts_only_not_bodies(caplog):
    f1 = _filament(1, "Galaxy Black", "Rosa3D", "PLA")
    with caplog.at_level(logging.INFO, logger="app.modules.slicer.profile_selection"):
        build_filaments_by_ref(_snapshot(f1))
    record = next(r for r in caplog.records if r.name == "app.modules.slicer.profile_selection")
    assert getattr(record, "labels.filament_count", None) == 1
    # The filament's descriptive fields must never appear in the log payload.
    assert "Galaxy Black" not in caplog.text
    assert "Rosa3D" not in caplog.text


def test_build_filaments_by_ref_none_logs_degraded_reason(caplog):
    with caplog.at_level(logging.WARNING, logger="app.modules.slicer.profile_selection"):
        build_filaments_by_ref(None)
    record = next(r for r in caplog.records if r.name == "app.modules.slicer.profile_selection")
    assert getattr(record, "labels.reason", None) == "spoolman_unavailable"
    assert getattr(record, "labels.filament_count", None) == 0


# --- AC-10 / AC-11: select_profile precedence, snapshot material, soft-fail ------


def test_select_profile_exact_override_wins():
    sel = select_profile(
        policy=POLICY,
        spoolman_filament_ref="matt-ref",
        fallback_material="PLA",
        filaments_by_ref={},
    )
    assert sel.source is EstimateProfileSource.exact_filament_mapping
    assert sel.orca_filament_profile_ref == "PLA Matt"
    assert sel.selected_spoolman_filament_ref == "matt-ref"


def test_select_profile_material_default_via_snapshot_material():
    f = _filament(1, "Galaxy Black", "Rosa3D", "PLA")
    ref = spoolman_filament_ref(f)
    sel = select_profile(
        policy=POLICY,
        spoolman_filament_ref=ref,
        fallback_material=None,
        filaments_by_ref={ref: f},
    )
    assert sel.source is EstimateProfileSource.default_material_profile
    assert sel.orca_filament_profile_ref == "Generic PLA"
    assert sel.selected_material == "PLA"


def test_select_profile_snapshot_material_wins_over_fallback():
    # The snapshot says PETG; the caller's fallback says PLA. The snapshot material
    # is authoritative for a found ref ⇒ no PETG default ⇒ unavailable, NOT a wrong
    # PLA-default estimate.
    f = _filament(1, "CF PETG", "Fiberlogy", "PETG")
    ref = spoolman_filament_ref(f)
    sel = select_profile(
        policy=POLICY,
        spoolman_filament_ref=ref,
        fallback_material="PLA",
        filaments_by_ref={ref: f},
    )
    assert sel.selected_material == "PETG"
    assert sel.source is EstimateProfileSource.unavailable_no_profile


def test_select_profile_ref_absent_from_map_uses_fallback_material():
    sel = select_profile(
        policy=POLICY,
        spoolman_filament_ref="not-in-snapshot",
        fallback_material="PLA",
        filaments_by_ref={},
    )
    assert sel.source is EstimateProfileSource.default_material_profile
    assert sel.orca_filament_profile_ref == "Generic PLA"
    assert sel.selected_material == "PLA"


def test_select_profile_cold_snapshot_soft_fails_to_unavailable_without_fallback():
    sel = select_profile(
        policy=POLICY,
        spoolman_filament_ref="anything",
        fallback_material=None,
        filaments_by_ref=None,
    )
    assert sel.source is EstimateProfileSource.unavailable_no_profile
    assert sel.orca_filament_profile_ref is None


def test_select_profile_is_pure_and_deterministic():
    f = _filament(1, "Galaxy Black", "Rosa3D", "PLA")
    ref = spoolman_filament_ref(f)
    kwargs = dict(
        policy=POLICY,
        spoolman_filament_ref=ref,
        fallback_material="PLA",
        filaments_by_ref={ref: f},
    )
    assert select_profile(**kwargs) == select_profile(**kwargs)


# --- Resolver integration fixtures ---------------------------------------------


def _intent(material_class: str = "PLA", ref: str | None = None) -> PrintIntentPreset:
    return PrintIntentPreset(
        name=f"{material_class} standard",
        material_class=material_class,  # type: ignore[arg-type]
        quality_tier="standard",
        printer_ref=PRINTER,
        spoolman_filament_ref=ref,
    )


def _write_policy_tree(root: Path, *, filament_inherit: str = "Generic PLA") -> Path:
    """A vendored tree with two distinct named PLA filament system profiles.

    ``Generic PLA`` and ``PLA Matt`` differ (nozzle temp) so a profile re-target
    produces a materially different resolved filament JSON ⇒ a different bundle_hash.
    The PLA intent's filament partial inherits ``filament_inherit`` by default.
    """
    sysd = root / "system"
    sysd.mkdir(parents=True, exist_ok=True)
    (sysd / "common.json").write_text(
        json.dumps(
            {
                "name": "fdm_filament_common",
                "from": "system",
                "instantiation": "false",
                "filament_flow_ratio": ["0.98"],
            }
        )
    )
    (sysd / "m.json").write_text(
        json.dumps({"name": "M", "from": "system", "instantiation": "true"})
    )
    (sysd / "p.json").write_text(
        json.dumps({"name": "P", "from": "system", "instantiation": "true", "layer_height": "0.2"})
    )
    (sysd / "generic_pla.json").write_text(
        json.dumps(
            {
                "name": "Generic PLA",
                "inherit": "fdm_filament_common",
                "from": "system",
                "instantiation": "true",
                "filament_type": ["PLA"],
                "nozzle_temperature": ["210"],
            }
        )
    )
    (sysd / "pla_matt.json").write_text(
        json.dumps(
            {
                "name": "PLA Matt",
                "inherit": "fdm_filament_common",
                "from": "system",
                "instantiation": "true",
                "filament_type": ["PLA"],
                "nozzle_temperature": ["215"],
            }
        )
    )
    intentd = root / "intents" / PRINTER / "PLA"
    intentd.mkdir(parents=True, exist_ok=True)
    (intentd / "standard.json").write_text(
        json.dumps(
            {
                "machine": {"inherit": "M"},
                "process": {"inherit": "P"},
                "filament": {"inherit": filament_inherit},
            }
        )
    )
    return root


def _resolve(intent, source, store, *, selection=None, overrides=None):
    return resolve(
        intent,
        source=source,
        store=store,
        override_provider=_FixedOverrideProvider(overrides),
        validator=NullCliValidator(),
        orca_version="2.3.2",
        profile_selection=selection,
    )


class _FixedOverrideProvider:
    def __init__(self, overrides: FilamentOverrides | None) -> None:
        self._overrides = overrides

    def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None:
        return self._overrides


def _default_sel(ref: str) -> ProfileSelection:
    return POLICY.resolve_selection(material="PLA", spoolman_filament_ref=ref)


# --- AC-1 / AC-14: opt-in seam — byte-identical legacy path ---------------------


def test_resolve_without_selection_is_byte_identical_legacy(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    legacy = resolve(
        _intent(),
        source=src,
        store=BundleStore(tmp_path / "a"),
        override_provider=NoopOverrideProvider(),
        validator=NullCliValidator(),
        orca_version="2.3.2",
    )
    explicit_none = _resolve(_intent(), src, BundleStore(tmp_path / "b"), selection=None)
    assert isinstance(legacy, ResolveSuccess)
    assert isinstance(explicit_none, ResolveSuccess)
    assert explicit_none.bundle.bundle_hash == legacy.bundle.bundle_hash
    assert explicit_none.triple == legacy.triple
    assert explicit_none.profile_selection is None


def test_default_selection_to_same_profile_does_not_change_hash(tmp_path):
    # AC-14 / NFR23-CACHE-INVARIANT-1: a selection that re-targets to the SAME
    # profile the intent already inherits yields the SAME bundle_hash as the
    # no-selection legacy resolve — the selection metadata is NOT a hash input.
    src = VendoredProfileSource(
        _write_policy_tree(tmp_path / "vend", filament_inherit="Generic PLA")
    )
    legacy = _resolve(_intent(), src, BundleStore(tmp_path / "a"))
    selected = _resolve(
        _intent(ref="c"), src, BundleStore(tmp_path / "b"), selection=_default_sel("c")
    )
    assert isinstance(legacy, ResolveSuccess) and isinstance(selected, ResolveSuccess)
    assert selected.bundle.bundle_hash == legacy.bundle.bundle_hash


# --- AC-3: profile substitution — chosen profile materializes --------------------


def test_selection_retargets_filament_inherit(tmp_path):
    # The intent file inherits "PLA Matt", but a Generic-PLA default selection must
    # re-target the filament to "Generic PLA" before the merge.
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend", filament_inherit="PLA Matt"))
    out = _resolve(_intent(ref="c"), src, BundleStore(tmp_path / "s"), selection=_default_sel("c"))
    assert isinstance(out, ResolveSuccess)
    assert out.triple.filament["name"] == "Generic PLA"
    assert out.triple.filament["nozzle_temperature"] == ["210"]


def test_selection_non_dict_filament_partial_still_classifies_invalid(tmp_path):
    root = tmp_path / "vend"
    _write_policy_tree(root)
    # Corrupt the intent filament partial to a non-dict; the substitution must not
    # raise — _resolve_partials' shape gate classifies it as invalid_partial.
    intent_file = root / "intents" / PRINTER / "PLA" / "standard.json"
    intent_file.write_text(
        json.dumps({"machine": {"inherit": "M"}, "process": {"inherit": "P"}, "filament": []})
    )
    out = _resolve(
        _intent(ref="c"),
        VendoredProfileSource(root),
        BundleStore(tmp_path / "s"),
        selection=_default_sel("c"),
    )
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.invalid_partial


# --- AC-4: two generic-PLA colors share one bundle ------------------------------


def test_two_pla_colors_same_default_share_bundle(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    store = BundleStore(tmp_path / "s")
    a = _resolve(_intent(ref="colorA"), src, store, selection=_default_sel("colorA"))
    b = _resolve(_intent(ref="colorB"), src, store, selection=_default_sel("colorB"))
    assert isinstance(a, ResolveSuccess) and isinstance(b, ResolveSuccess)
    assert a.from_cache is False
    assert b.from_cache is True  # shared bundle — second resolve is a cache hit
    assert a.bundle.bundle_hash == b.bundle.bundle_hash
    assert a.bundle.filament == b.bundle.filament  # byte-identical filament JSON


# --- AC-2: ResolveSuccess carries the supplied selection (fresh + cache) --------


def test_resolve_success_carries_selection_on_fresh_and_cache(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    store = BundleStore(tmp_path / "s")
    fresh = _resolve(_intent(ref="colorA"), src, store, selection=_default_sel("colorA"))
    assert isinstance(fresh, ResolveSuccess)
    assert fresh.profile_selection == _default_sel("colorA")
    # An exact override pointing at the SAME profile ("Generic PLA") ⇒ same bundle
    # ⇒ cache hit ⇒ the supplied (exact) selection is attached, distinguishable
    # from the first (default) selection by its source.
    exact = POLICY.resolve_selection(material="PLA", spoolman_filament_ref="exact-generic")
    cached = _resolve(_intent(ref="exact-generic"), src, store, selection=exact)
    assert isinstance(cached, ResolveSuccess)
    assert cached.from_cache is True
    assert cached.profile_selection is not None
    assert cached.profile_selection.source is EstimateProfileSource.exact_filament_mapping


# --- AC-5: PLA Matt exact override resolves to a distinct bundle -----------------


def test_pla_matt_exact_override_distinct_bundle(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    store = BundleStore(tmp_path / "s")
    default = _resolve(_intent(ref="colorA"), src, store, selection=_default_sel("colorA"))
    matt_sel = POLICY.resolve_selection(material="PLA", spoolman_filament_ref="matt-ref")
    matt = _resolve(_intent(ref="matt-ref"), src, store, selection=matt_sel)
    assert isinstance(default, ResolveSuccess) and isinstance(matt, ResolveSuccess)
    assert matt.bundle.bundle_hash != default.bundle.bundle_hash
    assert matt.triple.filament["name"] == "PLA Matt"


# --- AC-6: override numeric layer applies AFTER policy base selection ------------


def test_numeric_override_applies_after_base_selection(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    store = BundleStore(tmp_path / "s")
    plain = _resolve(_intent(ref="colorA"), src, store, selection=_default_sel("colorA"))
    overridden = _resolve(
        _intent(ref="colorA"),
        src,
        store,
        selection=_default_sel("colorA"),
        overrides=FilamentOverrides(nozzle_temperature=250),
    )
    assert isinstance(plain, ResolveSuccess) and isinstance(overridden, ResolveSuccess)
    # No-extras default leaves overrides_ref absent (the AC-4 shared property holds).
    assert plain.bundle.spoolman_overrides_ref is None
    # A numeric override re-hashes via overrides_ref to a distinct bundle.
    assert overridden.bundle.bundle_hash != plain.bundle.bundle_hash
    assert overridden.bundle.spoolman_overrides_ref is not None
    # The base profile is still the policy-selected one; the override applied on top.
    assert overridden.triple.filament["name"] == "Generic PLA"
    assert overridden.triple.filament["nozzle_temperature"] == ["250"]


# --- AC-7 / AC-8: unavailable ⇒ classified absence, no write, no enqueue ---------


def test_unavailable_selection_yields_classified_failure_no_write(tmp_path):
    src = VendoredProfileSource(_write_policy_tree(tmp_path / "vend"))
    store_dir = tmp_path / "s"
    store = BundleStore(store_dir)
    unavailable = POLICY.resolve_selection(material="ABS", spoolman_filament_ref="x")
    assert unavailable.source is EstimateProfileSource.unavailable_no_profile
    out = _resolve(_intent(material_class="PLA", ref="x"), src, store, selection=unavailable)
    # AC-7: classified failure, no bundle/snapshot persisted.
    assert isinstance(out, ResolveFailure)
    assert out.reason == ResolveReason.unavailable_no_profile
    assert list(store_dir.rglob("*.json")) == []
    # AC-8: the ingest no-enqueue branch keys on `not isinstance(_, ResolveSuccess)`,
    # so this outcome cannot enqueue a wrong fallback slice.
    assert not isinstance(out, ResolveSuccess)
