"""Tests for SPOOL-PREQ-1 — the Spoolman filament reverse index / intent attribution.

Three surfaces, all pure app-side (real on-disk stores in ``tmp_path``; no Redis / no
Orca / no httpx):

- ``AttributionStore`` — the append-only ref-hash-fanout sidecar that persists, at
  resolve time, which ``PrintIntentPreset`` (and the ``bundle_hash`` it resolved to)
  pinned a given Spoolman ``spoolman_filament_ref``.
- ``resolve()`` DI seam — an OPTIONAL ``attribution_sink``: a pinned ref records one
  entry; a ``None`` ref or no/Noop sink is a byte-identical no-op (the Story 32.1
  override-seam discipline mirrored).
- ``lookup_affected_keys`` — the deterministic join (index ⋈ ``EstimateStore``) that
  returns, per pinning intent, the affected ``(stl_hash, bundle_hash)`` estimate keys —
  exactly the inputs SPOOL-EVT-1 feeds into ``apply_spoolman_filament_change``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.modules.slicer.attribution_store import (
    AttributionSink,
    AttributionStore,
    NoopAttributionSink,
    lookup_affected_keys,
)
from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import EstimateRecord, EstimateStatus, PrintIntentPreset
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve, resolve_intent
from app.modules.slicer.validation import NullCliValidator

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

# A churn-stable profile-style ref carries a \x1f separator + arbitrary vendor text —
# NOT path-safe, so the store must hash it for the on-disk filename.
PLA_REF = "Polymaker\x1fPLA\x1fPolyTerra"
OTHER_REF = "Prusa\x1fPETG\x1fPrusament"

PLA_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)
PLA_INTENT_PINNED = PLA_INTENT.model_copy(update={"spoolman_filament_ref": PLA_REF})
PLA_INTENT_PINNED_AESTHETIC = PLA_INTENT.model_copy(
    update={"quality_tier": "aesthetic", "spoolman_filament_ref": PLA_REF}
)

# 64-lowercase-hex content hashes (the EstimateStore path gate requires this shape).
STL_A = "1" * 64
STL_B = "2" * 64
BUNDLE_1 = "a" * 64
BUNDLE_2 = "b" * 64


def _resolve_pinned(intent, store, *, sink=None, orca="2.3.2"):
    return resolve(
        intent,
        source=VendoredProfileSource(FIXTURES),
        store=store,
        override_provider=NoopOverrideProvider(),
        validator=NullCliValidator(),
        orca_version=orca,
        attribution_sink=sink,
    )


def _fresh(stl_hash: str, bundle_hash: str, *, orca: str = "2.3.2") -> EstimateRecord:
    return EstimateRecord(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        orca_version=orca,
        time_seconds=120,
        filament_g=1.5,
        filament_mm=2.0,
        filament_cm3=3.0,
        status=EstimateStatus.fresh,
        computed_at="2026-06-03T00:00:00+00:00",
    )


# === AttributionStore persist semantics =======================================


def test_record_is_keyed_by_ref_hash_not_raw_ref_and_round_trips(tmp_path):
    store = AttributionStore(tmp_path)
    store.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)

    ref_hash = hashlib.sha256(PLA_REF.encode("utf-8")).hexdigest()
    expected = tmp_path / "attribution" / ref_hash[:2] / f"{ref_hash}.json"
    assert expected.exists()
    # The raw ref (with its \x1f separator) NEVER reaches the filesystem path.
    for p in tmp_path.rglob("*"):
        assert "\x1f" not in p.name
    # ...but it round-trips verbatim inside the record.
    record = store.load(PLA_REF)
    assert record is not None
    assert record.spoolman_filament_ref == PLA_REF
    assert len(record.entries) == 1
    assert record.entries[0].intent == PLA_INTENT_PINNED
    assert record.entries[0].bundle_hash == BUNDLE_1


def test_record_path_traversal_shaped_ref_stays_under_root(tmp_path):
    store = AttributionStore(tmp_path)
    nasty = "ev\x1f../../etc\x1fpasswd"
    store.record(nasty, PLA_INTENT_PINNED, BUNDLE_1)
    root = tmp_path.resolve()
    # The traversal-shaped ref is hashed away — every persisted file stays under root.
    written = list(tmp_path.rglob("*.json"))
    assert written
    for p in written:
        assert root in p.resolve().parents
    assert store.load(nasty) is not None


def test_record_idempotent_add_is_byte_stable_noop(tmp_path):
    store = AttributionStore(tmp_path)
    store.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    ref_hash = hashlib.sha256(PLA_REF.encode("utf-8")).hexdigest()
    path = tmp_path / "attribution" / ref_hash[:2] / f"{ref_hash}.json"
    before = path.read_bytes()
    store.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)  # exact duplicate
    after = path.read_bytes()
    assert before == after  # prior file untouched (append-only, no churn)
    record = store.load(PLA_REF)
    assert record is not None
    assert len(record.entries) == 1


def test_record_appends_additional_entries_without_mutating_prior(tmp_path):
    store = AttributionStore(tmp_path)
    store.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    store.record(PLA_REF, PLA_INTENT_PINNED_AESTHETIC, BUNDLE_2)
    record = store.load(PLA_REF)
    assert record is not None
    pairs = {(e.intent.quality_tier, e.bundle_hash) for e in record.entries}
    assert pairs == {("standard", BUNDLE_1), ("aesthetic", BUNDLE_2)}


def test_record_dedups_by_bundle_hash_ignoring_ui_only_fields(tmp_path):
    # Two pins with the SAME ref + SAME bundle_hash that differ only in resolve-irrelevant
    # UI-ish fields (notes / is_default) must collapse to a single entry — those fields do
    # not change the resolve, so they must not bloat the index (the first intent wins).
    store = AttributionStore(tmp_path)
    a = PLA_INTENT_PINNED.model_copy(update={"notes": "draft for Bob"})
    b = PLA_INTENT_PINNED.model_copy(update={"notes": "draft for Alice", "is_default": True})
    store.record(PLA_REF, a, BUNDLE_1)
    ref_hash = hashlib.sha256(PLA_REF.encode("utf-8")).hexdigest()
    path = tmp_path / "attribution" / ref_hash[:2] / f"{ref_hash}.json"
    before = path.read_bytes()
    store.record(PLA_REF, b, BUNDLE_1)  # same bundle, different notes/is_default
    after = path.read_bytes()
    assert before == after  # no-op, prior file untouched
    record = store.load(PLA_REF)
    assert record is not None
    assert len(record.entries) == 1
    assert record.entries[0].intent == a  # first intent for the bundle wins


def test_record_entries_are_deterministically_ordered(tmp_path):
    # Insertion order must NOT leak into the persisted order (reproducible records).
    a = AttributionStore(tmp_path / "a")
    a.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    a.record(PLA_REF, PLA_INTENT_PINNED_AESTHETIC, BUNDLE_2)
    b = AttributionStore(tmp_path / "b")
    b.record(PLA_REF, PLA_INTENT_PINNED_AESTHETIC, BUNDLE_2)
    b.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    ra, rb = a.load(PLA_REF), b.load(PLA_REF)
    assert ra is not None and rb is not None
    assert ra.entries == rb.entries


def test_load_unknown_ref_returns_none(tmp_path):
    store = AttributionStore(tmp_path)
    assert store.load(PLA_REF) is None


# === resolver DI seam =========================================================


def test_resolve_with_sink_records_attribution_when_ref_pinned(tmp_path):
    bundles = BundleStore(tmp_path / "bundles")
    sink = AttributionStore(tmp_path / "attrib")
    out = _resolve_pinned(PLA_INTENT_PINNED, bundles, sink=sink)
    record = sink.load(PLA_REF)
    assert record is not None
    assert len(record.entries) == 1
    assert record.entries[0].bundle_hash == out.bundle.bundle_hash
    assert record.entries[0].intent == PLA_INTENT_PINNED


def test_resolve_with_ref_none_writes_no_attribution(tmp_path):
    bundles = BundleStore(tmp_path / "bundles")
    sink = AttributionStore(tmp_path / "attrib")
    _resolve_pinned(PLA_INTENT, bundles, sink=sink)  # ref is None
    assert not (tmp_path / "attrib" / "attribution").exists()


def test_resolve_with_empty_string_ref_writes_no_attribution(tmp_path):
    # spoolman_filament_ref is `str | None` with no non-blank validator, so "" is a valid
    # construction. An empty ref is not a usable pin — the seam must treat it like None and
    # write nothing (no degenerate index bucket).
    bundles = BundleStore(tmp_path / "bundles")
    sink = AttributionStore(tmp_path / "attrib")
    empty_pin = PLA_INTENT.model_copy(update={"spoolman_filament_ref": ""})
    _resolve_pinned(empty_pin, bundles, sink=sink)
    assert not (tmp_path / "attrib" / "attribution").exists()


def test_resolve_without_sink_is_noop_even_when_ref_pinned(tmp_path):
    bundles = BundleStore(tmp_path / "bundles")
    out = _resolve_pinned(PLA_INTENT_PINNED, bundles, sink=None)
    # Resolve succeeds and persists ONLY the bundle/snapshot — no attribution subtree.
    assert out.bundle.bundle_hash
    assert list((tmp_path / "bundles").rglob("attribution")) == []


def test_resolve_cache_hit_still_records_attribution(tmp_path):
    bundles = BundleStore(tmp_path / "bundles")
    sink = AttributionStore(tmp_path / "attrib")
    first = _resolve_pinned(PLA_INTENT_PINNED, bundles, sink=sink)
    second = _resolve_pinned(PLA_INTENT_PINNED, bundles, sink=sink)
    assert second.from_cache is True
    assert second.bundle.bundle_hash == first.bundle.bundle_hash
    record = sink.load(PLA_REF)
    assert record is not None
    assert len(record.entries) == 1  # idempotent across the cache-hit path


def test_resolve_with_noop_sink_writes_nothing(tmp_path):
    bundles = BundleStore(tmp_path / "bundles")
    _resolve_pinned(PLA_INTENT_PINNED, bundles, sink=NoopAttributionSink())
    assert list(tmp_path.rglob("attribution")) == []


def test_resolve_intent_wires_a_real_attribution_store_from_settings(tmp_path, monkeypatch):
    from app.core import config as config_mod

    monkeypatch.setenv("SLICER_VENDORED_PROFILES_DIR", str(FIXTURES))
    monkeypatch.setenv("SLICER_BUNDLE_STORE_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("ORCA_VERSION", "2.3.2")
    config_mod.get_settings.cache_clear()
    try:
        out = resolve_intent(PLA_INTENT_PINNED)
        store = AttributionStore(tmp_path / "store")
        record = store.load(PLA_REF)
        assert record is not None
        assert record.entries[0].bundle_hash == out.bundle.bundle_hash
    finally:
        config_mod.get_settings.cache_clear()


# === lookup semantics =========================================================


def test_lookup_returns_affected_keys_for_known_ref(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    attrib.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    estimates = EstimateStore(tmp_path / "est")
    estimates.write(_fresh(STL_A, BUNDLE_1))
    estimates.write(_fresh(STL_B, BUNDLE_1))
    estimates.write(_fresh(STL_A, BUNDLE_2))  # different bundle, must NOT be picked

    groups = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    assert len(groups) == 1
    assert groups[0].intent == PLA_INTENT_PINNED
    assert groups[0].bundle_hash == BUNDLE_1
    assert groups[0].affected_keys == [(STL_A, BUNDLE_1), (STL_B, BUNDLE_1)]


def test_lookup_groups_by_intent_for_a_shared_ref(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    attrib.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    attrib.record(PLA_REF, PLA_INTENT_PINNED_AESTHETIC, BUNDLE_2)
    estimates = EstimateStore(tmp_path / "est")
    estimates.write(_fresh(STL_A, BUNDLE_1))
    estimates.write(_fresh(STL_B, BUNDLE_2))

    groups = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    by_bundle = {g.bundle_hash: g for g in groups}
    assert set(by_bundle) == {BUNDLE_1, BUNDLE_2}
    assert by_bundle[BUNDLE_1].affected_keys == [(STL_A, BUNDLE_1)]
    assert by_bundle[BUNDLE_2].affected_keys == [(STL_B, BUNDLE_2)]
    assert by_bundle[BUNDLE_1].intent == PLA_INTENT_PINNED
    assert by_bundle[BUNDLE_2].intent == PLA_INTENT_PINNED_AESTHETIC


def test_lookup_unknown_ref_is_empty(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    estimates = EstimateStore(tmp_path / "est")
    assert lookup_affected_keys(OTHER_REF, attribution_store=attrib, estimate_store=estimates) == []


def test_lookup_bundle_with_no_estimates_yields_empty_keys(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    attrib.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    estimates = EstimateStore(tmp_path / "est")  # empty store
    groups = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    assert len(groups) == 1
    assert groups[0].bundle_hash == BUNDLE_1
    assert groups[0].affected_keys == []


def test_lookup_is_deterministic_across_calls(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    attrib.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    attrib.record(PLA_REF, PLA_INTENT_PINNED_AESTHETIC, BUNDLE_2)
    estimates = EstimateStore(tmp_path / "est")
    estimates.write(_fresh(STL_B, BUNDLE_1))
    estimates.write(_fresh(STL_A, BUNDLE_1))
    estimates.write(_fresh(STL_A, BUNDLE_2))
    first = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    second = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    assert first == second
    # keys within a group are sorted (STL_A < STL_B) regardless of write order.
    g1 = next(g for g in first if g.bundle_hash == BUNDLE_1)
    assert g1.affected_keys == [(STL_A, BUNDLE_1), (STL_B, BUNDLE_1)]


def test_lookup_missing_estimate_store_dir_does_not_raise(tmp_path):
    attrib = AttributionStore(tmp_path / "attrib")
    attrib.record(PLA_REF, PLA_INTENT_PINNED, BUNDLE_1)
    estimates = EstimateStore(tmp_path / "does-not-exist")
    groups = lookup_affected_keys(PLA_REF, attribution_store=attrib, estimate_store=estimates)
    assert groups[0].affected_keys == []


# === Protocol conformance =====================================================


def test_attribution_store_satisfies_sink_protocol(tmp_path):
    assert isinstance(AttributionStore(tmp_path), AttributionSink)


def test_noop_sink_satisfies_protocol():
    assert isinstance(NoopAttributionSink(), AttributionSink)
