"""Tests for the Story 32.5 Spoolman-mapped filament-override layer (Decision AH §
override layer + Decision AJ § Spoolman linkage).

Pure app-side surface, no real Spoolman / no real Orca / no Redis / no httpx:

- ``map_filament_extra`` — the pure ``filament.extra`` (JSON-encoded strings) →
  ``FilamentOverrides`` mapper, with the no-silent-garbage guard (AC-2).
- ``spoolman_filament_ref`` + ``SpoolmanOverrideProvider`` — the sync, snapshot-backed
  provider + the churn-stable profile-style reference link (AC-3 / AC-5).
- ``build_spoolman_override_provider`` — the single async, instrumented Spoolman touch,
  soft-failing to an empty provider on a down/absent Spoolman (AC-4 / AC-8).
- ``filament_price_per_gram`` / ``classify_spoolman_delta`` / ``apply_spoolman_filament_change``
  — the cost-vs-mapped classification + the dispatch into the Story 32.4 engine (AC-6).

The Story 32.4 ``recompute`` engine is CALLED with injected fakes (a fake ``arq_pool`` +
a real on-disk ``EstimateStore``); the new-``bundle_hash`` derivation uses a real
in-process ``resolver.resolve`` over the checked-in fixtures (AC-6). ``computed_at`` is
the only non-deterministic field and is excluded from every assertion (AC-12).
"""

from __future__ import annotations

import json
import logging
import math

import pytest
from pydantic import ValidationError

from app.modules.slicer.models import FilamentOverrides
from app.modules.slicer.overrides import map_filament_extra

# === structured-log capture surface ==========================================
#
# The AC-8 observability assertions need a capture surface that survives the
# suite-wide ``configure_logging()`` reset: the API lifespan does
# ``root.handlers[:] = [handler]`` (app/core/logging.py), which evicts pytest's
# ``caplog`` root handler for the rest of the session, so a ``caplog``-based
# assertion silently sees zero records once any app-touching test has run. We
# attach a handler DIRECTLY to the module logger instead (mirrors the
# established pattern in tests/test_spools.py::_CaptureHandler). The repo's
# structured-log convention is dotted ``labels.*`` keys passed via ``extra=``,
# surfaced as record ``__dict__`` attributes — asserted here verbatim.


class _CaptureHandler(logging.Handler):
    """Per-test handler attached directly to a named logger (survives the reset)."""

    def __init__(self, logger_name: str, level: int) -> None:
        super().__init__(level=level)
        self.records: list[logging.LogRecord] = []
        self._logger = logging.getLogger(logger_name)
        self._prior_level = self._logger.level
        self._prior_disabled = self._logger.disabled
        # Full-suite logging-config paths can leave named loggers disabled;
        # force an enabled state for the assertion, restored in ``detach()``.
        self._logger.disabled = False
        self._logger.setLevel(level)
        self._logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def detach(self) -> None:
        self._logger.removeHandler(self)
        self._logger.setLevel(self._prior_level)
        self._logger.disabled = self._prior_disabled


def _attach_capture(logger_name: str, *, level: int = logging.INFO) -> _CaptureHandler:
    return _CaptureHandler(logger_name, level)


# === AC-2: pure filament.extra → FilamentOverrides mapper =====================


def test_map_filament_extra_reads_volumetric_speed_temps_density():
    extra = {
        "filament_max_volumetric_speed": "8.0",
        "nozzle_temperature": "230",
        "hot_plate_temp": "60",
        "filament_density": "1.24",
    }
    out = map_filament_extra(extra)
    assert isinstance(out, FilamentOverrides)
    assert out.filament_max_volumetric_speed == pytest.approx(8.0)
    assert out.nozzle_temperature == 230
    assert out.hot_plate_temp == 60
    assert out.filament_density == pytest.approx(1.24)


def test_map_filament_extra_parses_json_encoded_string_values():
    # Spoolman's contract: each ``extra`` value is a JSON-encoded string, NOT a raw
    # scalar — so a bare ``"8.0"`` decodes to the float 8.0 via json.loads.
    extra = {"filament_max_volumetric_speed": "8.0", "nozzle_temperature": "230"}
    out = map_filament_extra(extra)
    assert out.filament_max_volumetric_speed == pytest.approx(8.0)
    assert isinstance(out.nozzle_temperature, int)
    assert out.nozzle_temperature == 230


@pytest.mark.parametrize(
    "bad_value",
    [
        "abc",  # not valid JSON at all
        "NaN",  # JSON-decodes to float nan
        "Infinity",  # JSON-decodes to float inf
        "-Infinity",
        '"8.0"',  # wrong type: a JSON string, not a number
        "true",  # wrong type: a JSON bool (an int subclass — must NOT coerce to 1)
        "[1, 2]",  # wrong type: a JSON array
        "{}",  # wrong type: a JSON object
        "null",  # wrong type: JSON null
    ],
)
def test_map_filament_extra_malformed_value_is_dropped_with_warning_not_garbage(bad_value):
    extra = {"filament_max_volumetric_speed": bad_value}
    captured = _attach_capture("app.modules.slicer.overrides", level=logging.WARNING)
    try:
        out = map_filament_extra(extra)
    finally:
        captured.detach()
    # The bad value is DROPPED (left None) — never a silent garbage/zero/nan override.
    assert out.filament_max_volumetric_speed is None
    # A structured warning was emitted naming the dropped key.
    assert any(
        r.__dict__.get("labels.extra_key") == "filament_max_volumetric_speed"
        for r in captured.records
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("nozzle_temperature", "-5"),  # negative temp
        ("hot_plate_temp", "0"),  # zero bed temp (no-silent-zero)
        ("filament_max_volumetric_speed", "-1.0"),  # negative speed
        ("filament_max_volumetric_speed", "0"),  # zero speed (no-silent-zero)
        ("filament_density", "-1.24"),  # negative density
        ("filament_density", "0.0"),  # zero density (no-silent-zero)
        ("nozzle_temperature", "230.5"),  # non-integral value for an int temp field
    ],
)
def test_map_filament_extra_negative_or_out_of_domain_value_dropped(key, value):
    out = map_filament_extra({key: value})
    # Every out-of-domain value leaves its field None — never applied to the filament JSON.
    assert getattr(out, key) is None


def test_map_filament_extra_absent_key_is_none():
    out = map_filament_extra({"nozzle_temperature": "230"})
    # Only the present, valid key is set; the rest stay None (excluded downstream).
    assert out.nozzle_temperature == 230
    assert out.filament_max_volumetric_speed is None
    assert out.hot_plate_temp is None
    assert out.filament_density is None


def test_map_filament_extra_no_mapped_keys_yields_all_none():
    # An extra carrying only non-mapped keys (e.g. the purchase url) ⇒ all-None overrides.
    out = map_filament_extra({"url": '"https://example.test"', "lot_nr": '"LOT-1"'})
    assert out == FilamentOverrides()
    assert out.model_dump(exclude_none=True) == {}


def test_map_filament_extra_empty_is_all_none():
    assert map_filament_extra({}) == FilamentOverrides()


def test_map_filament_extra_is_deterministic():
    extra = {"filament_max_volumetric_speed": "8.0", "nozzle_temperature": "230"}
    results = {map_filament_extra(extra).model_dump_json() for _ in range(50)}
    assert len(results) == 1


def test_map_filament_extra_unknown_extra_key_cannot_leak():
    # FilamentOverrides is extra="forbid"; an unmapped Spoolman key is simply not mapped,
    # it can never become a stray override field.
    out = map_filament_extra({"some_future_spoolman_field": "1.0"})
    assert out.model_dump(exclude_none=True) == {}


def test_spoolman_extra_to_override_map_covers_the_mapped_field_set():
    from app.modules.slicer.overrides import _SPOOLMAN_EXTRA_TO_OVERRIDE

    # The named FR20-SPOOLMAN-MAP-1 mapped-field set — identity-named portal↔Spoolman keys.
    assert set(_SPOOLMAN_EXTRA_TO_OVERRIDE) == {
        "filament_max_volumetric_speed",
        "nozzle_temperature",
        "hot_plate_temp",
        "filament_density",
    }


def test_map_filament_extra_is_pure_no_clock_no_external_read():
    # Defense-in-depth: the mapper module function reads only its argument — no Spoolman
    # read, no clock — so the same extra in always yields the same overrides out.
    extra = {"filament_density": "1.24"}
    first = map_filament_extra(dict(extra))
    second = map_filament_extra(dict(extra))
    assert first == second


# === AC-3 / AC-5: SpoolmanOverrideProvider + the profile-style reference link =====

from pathlib import Path  # noqa: E402

from app.modules.slicer.bundle_store import BundleStore  # noqa: E402
from app.modules.slicer.models import PrintIntentPreset  # noqa: E402
from app.modules.slicer.overrides import (  # noqa: E402
    NoopOverrideProvider,
    SpoolmanOverrideProvider,
    spoolman_filament_ref,
)
from app.modules.slicer.resolver import VendoredProfileSource, resolve  # noqa: E402
from app.modules.slicer.validation import NullCliValidator  # noqa: E402
from app.modules.spools.models import SpoolmanFilament  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

_PLA_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)


def _filament(ref_id: int = 1, *, extra: dict[str, str] | None = None, **kw) -> SpoolmanFilament:
    base = dict(
        id=ref_id,
        name=f"Rosa3D PLA Starter {ref_id}",
        vendor_name="Rosa3D",
        material="PLA",
        price=20.0,
        weight=1000.0,
        extra=extra or {},
    )
    base.update(kw)
    return SpoolmanFilament.model_validate(base)


def _pinned(
    filament: SpoolmanFilament, intent: PrintIntentPreset = _PLA_INTENT
) -> PrintIntentPreset:
    return intent.model_copy(update={"spoolman_filament_ref": spoolman_filament_ref(filament)})


def _provider_for(*filaments: SpoolmanFilament) -> SpoolmanOverrideProvider:
    return SpoolmanOverrideProvider({spoolman_filament_ref(f): f for f in filaments})


def _resolve(intent, store, *, provider):
    return resolve(
        intent,
        source=VendoredProfileSource(FIXTURES),
        store=store,
        override_provider=provider,
        validator=NullCliValidator(),
        orca_version="2.3.2",
    )


def test_provider_maps_pinned_filament_extra_into_overrides():
    filament = _filament(
        extra={"filament_max_volumetric_speed": "8.0", "nozzle_temperature": "230"}
    )
    provider = _provider_for(filament)
    out = provider.overrides_for(_pinned(filament))
    assert out is not None
    assert out.filament_max_volumetric_speed == pytest.approx(8.0)
    assert out.nozzle_temperature == 230


def test_provider_no_pin_returns_none():
    filament = _filament(extra={"nozzle_temperature": "230"})
    provider = _provider_for(filament)
    # _PLA_INTENT has spoolman_filament_ref=None (no pin) ⇒ no override.
    assert provider.overrides_for(_PLA_INTENT) is None


def test_provider_ref_absent_from_map_returns_none():
    filament = _filament(extra={"nozzle_temperature": "230"})
    provider = SpoolmanOverrideProvider({})  # empty map
    assert provider.overrides_for(_pinned(filament)) is None


def test_provider_all_none_mapping_returns_none_byte_identical_to_noop(tmp_path):
    # A pinned filament whose extra maps to all-None ⇒ provider returns None, and the
    # resolve is byte-identical to the NoopOverrideProvider path (same bundle_hash, no ref).
    filament = _filament(extra={"url": '"https://example.test"'})  # no mapped keys
    provider = _provider_for(filament)
    assert provider.overrides_for(_pinned(filament)) is None

    noop_out = _resolve(
        _pinned(filament), BundleStore(tmp_path / "a"), provider=NoopOverrideProvider()
    )
    prov_out = _resolve(_pinned(filament), BundleStore(tmp_path / "b"), provider=provider)
    assert noop_out.bundle.bundle_hash == prov_out.bundle.bundle_hash
    assert prov_out.bundle.spoolman_overrides_ref is None


def test_print_intent_preset_pin_defaults_none_non_breaking():
    # Existing constructions are unaffected (no pin) and the model stays frozen.
    assert _PLA_INTENT.spoolman_filament_ref is None
    with pytest.raises(ValidationError):
        _PLA_INTENT.material_class = "TPU"  # frozen=True intact


def test_spoolman_filament_ref_is_stable_not_entity_id():
    # The ref must NOT key on the churning integer id — two filaments with the same
    # descriptive identity but different ids derive the SAME ref (id is irrelevant).
    a = SpoolmanFilament.model_validate(
        {"id": 70707, "name": "Galaxy Black", "vendor_name": "Rosa3D", "material": "PLA"}
    )
    b = a.model_copy(update={"id": 999})  # same descriptive fields, churned id
    assert spoolman_filament_ref(a) == spoolman_filament_ref(b)
    assert "70707" not in spoolman_filament_ref(a)  # the entity id does not appear in the ref


def test_build_and_lookup_use_same_ref_function():
    # A filament built into the map under ref R is found by an intent pinning R — guards
    # the build/lookup key divergence (a divergence would silently never-match).
    filament = _filament(extra={"filament_density": "1.24"})
    provider = _provider_for(filament)
    intent = _pinned(filament)
    assert intent.spoolman_filament_ref == spoolman_filament_ref(filament)
    out = provider.overrides_for(intent)
    assert out is not None and out.filament_density == pytest.approx(1.24)


def test_resolve_with_pinned_ref_applies_that_filaments_overrides(tmp_path):
    filament = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    provider = _provider_for(filament)
    out = _resolve(_pinned(filament), BundleStore(tmp_path), provider=provider)
    assert out.triple.filament["filament_max_volumetric_speed"] == ["8.0"]
    assert out.bundle.spoolman_overrides_ref is not None


def test_resolve_with_spoolman_override_is_deterministic_same_values_same_hash(tmp_path):
    filament = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    provider = _provider_for(filament)
    first = _resolve(_pinned(filament), BundleStore(tmp_path / "a"), provider=provider)
    second = _resolve(_pinned(filament), BundleStore(tmp_path / "b"), provider=provider)
    assert first.bundle.bundle_hash == second.bundle.bundle_hash


def test_resolve_with_changed_mapped_value_yields_different_bundle_hash(tmp_path):
    f1 = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    f2 = _filament(extra={"filament_max_volumetric_speed": "12.0"})  # same ref, changed value
    assert spoolman_filament_ref(f1) == spoolman_filament_ref(f2)
    out1 = _resolve(_pinned(f1), BundleStore(tmp_path / "a"), provider=_provider_for(f1))
    out2 = _resolve(_pinned(f2), BundleStore(tmp_path / "b"), provider=_provider_for(f2))
    # The re-hash AC-6 turns into a spoolman_mapped_override invalidation.
    assert out1.bundle.bundle_hash != out2.bundle.bundle_hash


def test_provider_implements_override_provider_protocol():
    from app.modules.slicer.overrides import OverrideProvider

    assert isinstance(_provider_for(_filament()), OverrideProvider)


# === AC-4 / AC-8: async builder — the single instrumented Spoolman touch, soft-fail ===

import asyncio  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

from app.modules.slicer.overrides import build_spoolman_override_provider  # noqa: E402
from app.modules.spools.models import SpoolmanSnapshot  # noqa: E402


def _snapshot(*filaments: SpoolmanFilament) -> SpoolmanSnapshot:
    return SpoolmanSnapshot(
        spools=[],
        filaments=list(filaments),
        vendors=[],
        fetched_at=datetime(2026, 6, 2, tzinfo=UTC),
    )


class _BoomClient:
    """A client whose every read raises — proves the builder routes through SpoolsService."""

    async def list_filaments(self, *a, **k):  # pragma: no cover
        raise AssertionError("builder must not call SpoolmanClient directly")

    list_spools = list_vendors = list_filaments


class _FakeSpoolsService:
    def __init__(self, snapshot: SpoolmanSnapshot | None) -> None:
        self._snapshot = snapshot
        self.get_summary_calls = 0
        self._client = _BoomClient()

    async def get_summary(self) -> SpoolmanSnapshot | None:
        self.get_summary_calls += 1
        return self._snapshot


def test_builder_reads_summary_via_spools_service():
    filament = _filament(extra={"nozzle_temperature": "230"})
    service = _FakeSpoolsService(_snapshot(filament))
    provider = asyncio.run(build_spoolman_override_provider(service))
    assert service.get_summary_calls == 1
    # The built provider carries the snapshot's filaments keyed by the shared ref fn.
    assert provider.overrides_for(_pinned(filament)) is not None


def test_builder_soft_fails_to_empty_provider_when_spoolman_down():
    service = _FakeSpoolsService(None)  # cold cache + Spoolman down ⇒ get_summary None
    provider = asyncio.run(build_spoolman_override_provider(service))
    # Empty provider ⇒ every overrides_for is None (class-default resolve, not a hard fail).
    filament = _filament(extra={"nozzle_temperature": "230"})
    assert provider.overrides_for(_pinned(filament)) is None


def test_builder_does_not_call_spoolman_client_directly():
    # The builder takes a SpoolsService (reusing the Init 19 cache) — not base_url/token —
    # and never touches a fresh SpoolmanClient (whose reads raise in the fake).
    import inspect

    params = inspect.signature(build_spoolman_override_provider).parameters
    assert "service" in params
    assert "base_url" not in params and "auth_token" not in params
    service = _FakeSpoolsService(_snapshot(_filament()))
    asyncio.run(build_spoolman_override_provider(service))  # _BoomClient never invoked


def test_builder_emits_degraded_tag_when_spoolman_down():
    service = _FakeSpoolsService(None)
    captured = _attach_capture("app.modules.slicer.overrides", level=logging.WARNING)
    try:
        asyncio.run(build_spoolman_override_provider(service))
    finally:
        captured.detach()
    degraded = [
        r for r in captured.records if r.__dict__.get("labels.override_layer") == "degraded"
    ]
    assert degraded
    rec = degraded[-1]
    assert rec.__dict__["labels.external_service"] == "spoolman"
    assert rec.__dict__["labels.filament_count"] == 0


def test_builder_emits_obs_tag_no_body():
    # The ok line carries external_service=spoolman + the filament COUNT — never bodies.
    f1 = _filament(1, extra={"nozzle_temperature": "230"})
    f2 = _filament(2, extra={"filament_density": "1.24"})
    service = _FakeSpoolsService(_snapshot(f1, f2))
    captured = _attach_capture("app.modules.slicer.overrides", level=logging.INFO)
    try:
        asyncio.run(build_spoolman_override_provider(service))
    finally:
        captured.detach()
    ok = [r for r in captured.records if r.__dict__.get("labels.override_layer") == "ok"]
    assert ok
    rec = ok[-1]
    assert rec.__dict__["labels.external_service"] == "spoolman"
    assert rec.__dict__["labels.filament_count"] == 2
    # No filament bodies in the line (no extra values, no price, no names).
    for record in captured.records:
        blob = record.getMessage() + json.dumps(
            {k: str(v) for k, v in record.__dict__.items() if k.startswith("labels.")}
        )
        assert "230" not in blob
        assert "Rosa3D" not in blob
        assert "1.24" not in blob


# === AC-6 / AC-8: price_per_gram + classify + dispatch into the Story 32.4 engine =====

from types import SimpleNamespace  # noqa: E402

from app.modules.slicer.estimate_store import EstimateStore  # noqa: E402
from app.modules.slicer.models import EstimateRecord, EstimateStatus  # noqa: E402
from app.modules.slicer.recompute import RecomputeTrigger  # noqa: E402
from app.modules.slicer.spoolman_invalidation import (  # noqa: E402
    apply_spoolman_filament_change,
    classify_spoolman_delta,
    filament_price_per_gram,
)
from app.modules.slicer.worker_job import SLICE_JOB_NAME  # noqa: E402

_STL_HASH = "a" * 64


class _FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


def _fresh_estimate(stl_hash: str, bundle_hash: str) -> EstimateRecord:
    return EstimateRecord(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        filament_cost=4.60,
        status=EstimateStatus.fresh,
        computed_at="2026-06-01T00:00:00+00:00",
    )


def _resolved_hash(filament: SpoolmanFilament, store: BundleStore) -> str:
    out = _resolve(_pinned(filament), store, provider=_provider_for(filament))
    return out.bundle.bundle_hash


# --- filament_price_per_gram (the no-silent-zero/nan/negative guard) ---


def test_price_per_gram_divides_price_by_weight():
    f = _filament(price=24.0, weight=1000.0)
    assert filament_price_per_gram(f) == pytest.approx(0.024)


def test_price_per_gram_spool_price_override_takes_precedence():
    f = _filament(price=24.0, weight=1000.0)
    # spool.price overrides the filament price per the architecture row.
    assert filament_price_per_gram(f, spool_price=30.0) == pytest.approx(0.030)


@pytest.mark.parametrize("bad_weight", [0.0, -1.0, None])
def test_price_per_gram_rejects_zero_or_negative_weight_returns_none(bad_weight):
    f = _filament(price=24.0, weight=bad_weight)
    assert filament_price_per_gram(f) is None


@pytest.mark.parametrize("bad_price", [-0.01, math.nan, math.inf, None])
def test_price_per_gram_rejects_non_finite_or_negative_price_returns_none(bad_price):
    f = _filament(price=bad_price, weight=1000.0)
    assert filament_price_per_gram(f) is None


def test_price_per_gram_zero_price_is_allowed_returns_zero():
    # A free spool (price 0) is a valid non-negative finite rate — 32.4 accepts cost 0.
    f = _filament(price=0.0, weight=1000.0)
    assert filament_price_per_gram(f) == pytest.approx(0.0)


# --- classify_spoolman_delta (the cheap-vs-expensive decision) ---


def test_classify_mapped_field_change_is_mapped_override():
    old = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    assert classify_spoolman_delta(old, new) == RecomputeTrigger.spoolman_mapped_override


def test_classify_price_only_change_is_cost_only():
    old = _filament(price=24.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    new = _filament(price=30.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    assert classify_spoolman_delta(old, new) == RecomputeTrigger.spoolman_cost_only


def test_classify_density_change_is_mapped_not_cost_only():
    # Density is a MAPPED field (re-hash ⇒ re-slice), NOT a cost field — the architecture row.
    old = _filament(extra={"filament_density": "1.24"})
    new = _filament(extra={"filament_density": "1.21"})
    assert classify_spoolman_delta(old, new) == RecomputeTrigger.spoolman_mapped_override


def test_classify_mapped_wins_when_both_mapped_and_price_change():
    # A simultaneous price change rides along in the re-slice's fresh estimate — mapped wins.
    old = _filament(price=24.0, extra={"nozzle_temperature": "230"})
    new = _filament(price=30.0, extra={"nozzle_temperature": "240"})
    assert classify_spoolman_delta(old, new) == RecomputeTrigger.spoolman_mapped_override


def test_classify_irrelevant_field_change_is_none():
    # An irrelevant filament field (color) is neither mapped nor price/weight ⇒ no invalidation.
    old = _filament(color_hex="AABBCC", extra={"nozzle_temperature": "230"})
    new = _filament(color_hex="DDEEFF", extra={"nozzle_temperature": "230"})
    assert classify_spoolman_delta(old, new) is None


def test_classify_no_change_is_none():
    f = _filament(extra={"nozzle_temperature": "230"})
    assert classify_spoolman_delta(f, f.model_copy()) is None


# --- apply_spoolman_filament_change (dispatch into 32.4) ---


def test_dispatch_mapped_override_invalidates_with_old_and_new_bundle_hash(tmp_path):
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new_f = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch_old"))
    new_hash = _resolved_hash(new_f, BundleStore(tmp_path / "scratch_new"))
    assert old_hash != new_hash

    store = EstimateStore(tmp_path / "est")
    store.write(_fresh_estimate(_STL_HASH, old_hash))  # the OLD (stl, old_bundle) record
    pool = _FakePool()

    asyncio.run(
        apply_spoolman_filament_change(
            store,
            pool,
            intent=_pinned(new_f),
            old=old_f,
            new=new_f,
            source=VendoredProfileSource(FIXTURES),
            bundle_store=bundle_store,
            orca_version="2.3.2",
            affected_keys=[(_STL_HASH, old_hash)],
        )
    )
    # OLD record marked stale (kept servable, never served as fresh — R9).
    assert store.read(_STL_HASH, old_hash).status == EstimateStatus.stale
    # The re-slice was enqueued for the NEW bundle hash (computed by re-resolve here).
    assert len(pool.calls) == 1
    args, _ = pool.calls[0]
    assert args == (SLICE_JOB_NAME, _STL_HASH, new_hash)
    # The NEW key is a natural cache miss (32.4 fabricates no record) — the worker fills it
    # fresh; the re-slice is enqueued against it.
    assert store.read(_STL_HASH, new_hash) is None


def test_dispatch_cost_only_recomputes_arithmetically_no_enqueue(tmp_path):
    # THE single most important test in the story (R1 self-DoS guard): a price tick recomputes
    # cost arithmetically in place and the fake arq_pool is NEVER called.
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(price=24.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    new_f = _filament(price=50.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    bundle_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))

    store = EstimateStore(tmp_path / "est")
    store.write(_fresh_estimate(_STL_HASH, bundle_hash))
    pool = _FakePool()

    asyncio.run(
        apply_spoolman_filament_change(
            store,
            pool,
            intent=_pinned(new_f),
            old=old_f,
            new=new_f,
            source=VendoredProfileSource(FIXTURES),
            bundle_store=bundle_store,
            orca_version="2.3.2",
            affected_keys=[(_STL_HASH, bundle_hash)],
        )
    )
    assert pool.calls == []  # NEVER reaches the slicer queue
    updated = store.read(_STL_HASH, bundle_hash)
    assert updated.status == EstimateStatus.fresh  # cost-only never invalidates slice output
    assert updated.filament_cost == pytest.approx(76.76 * (50.0 / 1000.0))


def test_dispatch_none_trigger_is_noop(tmp_path):
    bundle_store = BundleStore(tmp_path / "bundles")
    f = _filament(color_hex="AABBCC", extra={"nozzle_temperature": "230"})
    new = _filament(color_hex="DDEEFF", extra={"nozzle_temperature": "230"})
    store = EstimateStore(tmp_path / "est")
    bundle_hash = _resolved_hash(f, BundleStore(tmp_path / "scratch"))
    store.write(_fresh_estimate(_STL_HASH, bundle_hash))
    pool = _FakePool()
    asyncio.run(
        apply_spoolman_filament_change(
            store,
            pool,
            intent=_pinned(new),
            old=f,
            new=new,
            source=VendoredProfileSource(FIXTURES),
            bundle_store=bundle_store,
            orca_version="2.3.2",
            affected_keys=[(_STL_HASH, bundle_hash)],
        )
    )
    # No store write, no enqueue — the record is untouched.
    assert pool.calls == []
    assert store.read(_STL_HASH, bundle_hash).status == EstimateStatus.fresh


def test_dispatch_mapped_override_bulk_fans_out_over_affected_keys(tmp_path):
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new_f = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch_old"))
    new_hash = _resolved_hash(new_f, BundleStore(tmp_path / "scratch_new"))

    store = EstimateStore(tmp_path / "est")
    stls = ["a" * 64, "b" * 64, "c" * 64]
    for stl in stls:
        store.write(_fresh_estimate(stl, old_hash))
    pool = _FakePool()
    asyncio.run(
        apply_spoolman_filament_change(
            store,
            pool,
            intent=_pinned(new_f),
            old=old_f,
            new=new_f,
            source=VendoredProfileSource(FIXTURES),
            bundle_store=bundle_store,
            orca_version="2.3.2",
            affected_keys=[(stl, old_hash) for stl in stls],
        )
    )
    # One deduped enqueue per affected key, each targeting the new bundle.
    assert len(pool.calls) == 3
    for stl in stls:
        assert store.read(stl, old_hash).status == EstimateStatus.stale
    enqueued = {args for args, _ in pool.calls}
    assert enqueued == {(SLICE_JOB_NAME, stl, new_hash) for stl in stls}


def test_dispatch_cost_only_skips_when_price_per_gram_unguarded(tmp_path):
    # A new filament whose price_per_gram cannot be derived (weight 0) ⇒ NO poisoned value
    # handed to the 32.4 arithmetic; the cost recompute is skipped, nothing enqueued.
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(price=24.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    new_f = _filament(price=50.0, weight=0.0, extra={"nozzle_temperature": "230"})
    bundle_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    store = EstimateStore(tmp_path / "est")
    store.write(_fresh_estimate(_STL_HASH, bundle_hash))
    pool = _FakePool()
    asyncio.run(
        apply_spoolman_filament_change(
            store,
            pool,
            intent=_pinned(new_f),
            old=old_f,
            new=new_f,
            source=VendoredProfileSource(FIXTURES),
            bundle_store=bundle_store,
            orca_version="2.3.2",
            affected_keys=[(_STL_HASH, bundle_hash)],
        )
    )
    assert pool.calls == []
    # Cost untouched (no 0/nan written) — the original 4.60 survives.
    assert store.read(_STL_HASH, bundle_hash).filament_cost == pytest.approx(4.60)


# --- AC-8 observability ---


def test_classify_emits_trigger_tag(tmp_path):
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(price=24.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    new_f = _filament(price=50.0, weight=1000.0, extra={"nozzle_temperature": "230"})
    bundle_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch"))
    store = EstimateStore(tmp_path / "est")
    store.write(_fresh_estimate(_STL_HASH, bundle_hash))
    pool = _FakePool()
    captured = _attach_capture("app.modules.slicer.spoolman_invalidation", level=logging.INFO)
    try:
        asyncio.run(
            apply_spoolman_filament_change(
                store,
                pool,
                intent=_pinned(new_f),
                old=old_f,
                new=new_f,
                source=VendoredProfileSource(FIXTURES),
                bundle_store=bundle_store,
                orca_version="2.3.2",
                affected_keys=[(_STL_HASH, bundle_hash)],
            )
        )
    finally:
        captured.detach()
    tagged = [r for r in captured.records if r.__dict__.get("labels.trigger") is not None]
    assert tagged
    assert tagged[-1].__dict__["labels.trigger"] == "spoolman_cost_only"
    # No Spoolman price/extra VALUES in the classification line.
    for r in tagged:
        blob = json.dumps({k: str(v) for k, v in r.__dict__.items() if k.startswith("labels.")})
        assert "50.0" not in blob and "24.0" not in blob


def test_dispatch_does_not_double_log_invalidate(tmp_path):
    # The per-invalidation line comes from the 32.4 recompute module, NOT re-emitted here.
    bundle_store = BundleStore(tmp_path / "bundles")
    old_f = _filament(extra={"filament_max_volumetric_speed": "8.0"})
    new_f = _filament(extra={"filament_max_volumetric_speed": "12.0"})
    old_hash = _resolved_hash(old_f, BundleStore(tmp_path / "scratch_old"))
    store = EstimateStore(tmp_path / "est")
    store.write(_fresh_estimate(_STL_HASH, old_hash))
    pool = _FakePool()
    captured = _attach_capture("app.modules.slicer.spoolman_invalidation", level=logging.INFO)
    try:
        asyncio.run(
            apply_spoolman_filament_change(
                store,
                pool,
                intent=_pinned(new_f),
                old=old_f,
                new=new_f,
                source=VendoredProfileSource(FIXTURES),
                bundle_store=bundle_store,
                orca_version="2.3.2",
                affected_keys=[(_STL_HASH, old_hash)],
            )
        )
    finally:
        captured.detach()
    # The spoolman_invalidation logger emits the CLASSIFICATION line(s) only — not the
    # "slicer.invalidate complete" per-key line (that is the recompute module's logger).
    own = [r for r in captured.records if r.name == "app.modules.slicer.spoolman_invalidation"]
    assert all("slicer.invalidate complete" not in r.getMessage() for r in own)


# === AC-7: Spoolman stays inventory SoT — read-only, no write, no duplication =====

import re  # noqa: E402

from app.modules.slicer.models import SlicerProfileBundle  # noqa: E402
from app.modules.slicer.overrides import overrides_fingerprint  # noqa: E402
from app.modules.spools.client import SpoolmanClient  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OVERRIDES_SRC = _REPO_ROOT / "apps/api/app/modules/slicer/overrides.py"
_INVALIDATION_SRC = _REPO_ROOT / "apps/api/app/modules/slicer/spoolman_invalidation.py"


def test_no_spoolman_write_method_invoked():
    # The SpoolmanClient exposes only ``list_*`` reads (Init 19 contract) — a write is
    # structurally impossible without adding one, and Story 32.5 adds none.
    public = [m for m in dir(SpoolmanClient) if not m.startswith("_")]
    write_verbs = ("post", "put", "patch", "delete", "create", "update", "write", "mutate")
    offenders = [m for m in public if any(v in m.lower() for v in write_verbs)]
    assert offenders == [], f"Spoolman write surface leaked: {offenders}"
    # The new Story 32.5 source never references an HTTP write verb against Spoolman.
    for src in (_OVERRIDES_SRC, _INVALIDATION_SRC):
        text = src.read_text(encoding="utf-8").lower()
        assert ".post(" not in text and ".put(" not in text
        assert ".patch(" not in text and ".delete(" not in text


def test_only_overrides_ref_persisted_not_raw_spoolman_fields(tmp_path):
    filament = _filament(price=24.0, weight=1000.0, extra={"filament_max_volumetric_speed": "8.0"})
    out = _resolve(_pinned(filament), BundleStore(tmp_path), provider=_provider_for(filament))
    # Only the DERIVED fingerprint (a sha256) persists, not raw Spoolman price/extra.
    assert re.fullmatch(r"[0-9a-f]{64}", out.bundle.spoolman_overrides_ref)
    # The persisted bundle model has no raw-Spoolman fields.
    fields = set(SlicerProfileBundle.model_fields)
    assert "price" not in fields and "extra" not in fields and "spool_price" not in fields
    # The raw spool price (24.0) is nowhere in the persisted bundle JSON.
    assert "24.0" not in out.bundle.model_dump_json()


def test_no_new_inventory_table_or_cache_key():
    # Story 32.5 reads the Init 19 cache via SpoolsService — it defines NO new Redis key
    # namespace and opens NO redis connection of its own (no inventory duplication).
    for src in (_OVERRIDES_SRC, _INVALIDATION_SRC):
        text = src.read_text(encoding="utf-8")
        assert "spools:summary" not in text  # no new/duplicated cache key
        # No DIRECT redis access — the snapshot is read via the injected SpoolsService only.
        assert "import redis" not in text
        assert "RedisFactory" not in text
        assert "app.core.redis" not in text
    # No new Alembic migration is added by this story.
    versions = _REPO_ROOT / "apps/api/migrations/versions"
    pre_story = {
        p.name for p in versions.glob("*.py")
    }  # presence check only — the diff gate (AC-9) enforces zero-add
    assert pre_story  # sanity: the migrations dir exists and is non-empty


def test_overrides_ref_matches_fingerprint(tmp_path):
    filament = _filament(extra={"nozzle_temperature": "230"})
    provider = _provider_for(filament)
    overrides = provider.overrides_for(_pinned(filament))
    out = _resolve(_pinned(filament), BundleStore(tmp_path), provider=provider)
    assert out.bundle.spoolman_overrides_ref == overrides_fingerprint(overrides)


# === AC-10: NFR20-CONTAINER-1 grep invariant over the new slicer files ============


def test_no_bench_or_windows_path_literal_in_new_slicer_files():
    pattern = re.compile(r"/mnt/c|fenrir|\.exe|[Ww]indows")
    for src in (_OVERRIDES_SRC, _INVALIDATION_SRC):
        assert not pattern.search(src.read_text(encoding="utf-8")), f"path/exe literal in {src}"


# === AC-9: overrides_for stays SYNC (no resolver reshape) =========================


def test_overrides_for_is_synchronous_not_async():
    import inspect

    # Making the Protocol async would reshape the Story 32.1 resolver (AC-9 forbids it).
    assert not inspect.iscoroutinefunction(SpoolmanOverrideProvider.overrides_for)
    # The async Spoolman read is hoisted to the builder.
    assert inspect.iscoroutinefunction(build_spoolman_override_provider)
