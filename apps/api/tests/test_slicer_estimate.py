"""Tests for the Story 32.3 g-code metadata parser + EstimateRecord cache (Decision AJ).

Pure app-side surface (FR20-ESTIMATE-1 parse half + FR20-CACHE-1 + NFR20-ATTRIBUTION-1):

- ``gcode_parse.parse_gcode_metadata`` / ``parse_duration_to_seconds`` — pure text→struct
  (no file I/O, no clock, no subprocess); a missing/garbled required line classifies a
  typed ``EstimateParseFailure``, never a silent zero.
- ``estimate_store.EstimateStore`` — append-only content-addressed ``(stl_hash, bundle_hash)``
  cache mirroring the Story 32.1 ``bundle_store`` atomic-write pattern; a ``fresh`` re-write
  is an idempotent no-op, a ``failed`` record is replaced by a clean retry.
- ``ParsingGcodeSink`` + the ``slice_estimate`` persist path — slots into the Story 32.2
  ``GcodeSink`` seam WITHOUT reshaping ``_classify`` / ``run_slice_job``.

No subprocess, no real Orca, no clock in any assertion (``computed_at`` is the only
non-deterministic field and is excluded — AC-12).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
import re
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.slicer import worker_job as worker_job_module
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.gcode_parse import (
    EstimateParseFailure,
    ParsedEstimate,
    ParsingGcodeSink,
    parse_duration_to_seconds,
    parse_gcode_metadata,
)
from app.modules.slicer.models import (
    EstimateFailureReason,
    EstimateRecord,
    EstimateStatus,
    SliceFailureReason,
    SliceOutcome,
    SliceStatus,
    SliceWarning,
)
from app.modules.slicer.worker_job import slice_estimate

REPO_ROOT = Path(__file__).resolve().parents[3]
GCODE_FIXTURES = Path(__file__).parent / "fixtures" / "slicer" / "gcode"

# Two well-formed 64-lowercase-hex content hashes for the cache key.
STL_HASH = "a" * 64
BUNDLE_HASH = "b" * 64


def _fixture(name: str) -> str:
    return (GCODE_FIXTURES / name).read_text(encoding="utf-8")


# === AC-1: models ============================================================


def test_estimate_status_enum_values():
    assert {s.value for s in EstimateStatus} == {"fresh", "stale", "queued", "failed"}


def test_estimate_failure_reason_extends_not_reshapes_sliceoutcome():
    # The parse taxonomy lives on the ESTIMATE record, never bolted onto the slice
    # INVOCATION taxonomy. EstimateFailureReason carries the parse reasons...
    assert {r.value for r in EstimateFailureReason} >= {
        "parse_failure",
        "missing_metadata_line",
        "unparseable_time",
        "unparseable_numeric",
    }
    # ...and SliceOutcome / SliceFailureReason stay byte-unreshaped (Story 32.2 AC-6).
    assert {r.value for r in SliceFailureReason} == {
        "non_manifold",
        "info_precheck_failed",
        "non_zero_exit",
        "cli_rejected_profile",
        "launch_error",
        "missing_gcode",
        "missing_stl",
        "missing_bundle",
        "timeout",
    }
    assert set(SliceOutcome.model_fields) == {
        "status",
        "reason",
        "warnings",
        "gcode_temp_ref",
        "manifold",
        "slice_wall_ms",
        "stl_hash",
        "bundle_hash",
        "orca_version",
    }


def test_estimate_record_failed_has_none_numerics_not_zero():
    rec = EstimateRecord(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.failed,
        reason=EstimateFailureReason.missing_metadata_line,
        computed_at="2026-06-01T00:00:00+00:00",
    )
    # No silent zero — a failed record carries None, never 0 (FR20-ESTIMATE-1).
    assert rec.time_seconds is None
    assert rec.filament_g is None
    assert rec.filament_mm is None
    assert rec.filament_cm3 is None
    assert rec.filament_cost is None
    assert rec.reason == EstimateFailureReason.missing_metadata_line


def test_estimate_record_reuses_slicewarning_model():
    rec = EstimateRecord(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.fresh,
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        warnings=[SliceWarning(message="floating cantilever")],
        computed_at="2026-06-01T00:00:00+00:00",
    )
    assert rec.warnings[0].__class__ is SliceWarning
    assert rec.warnings[0].message == "floating cantilever"


# === AC-2: pure g-code metadata parser =======================================


def test_parses_all_metadata_fields_pla():
    parsed = parse_gcode_metadata(_fixture("pla_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    assert parsed.time_seconds == 3 * 3600 + 35 * 60 + 47  # 3h35m47s
    assert parsed.filament_mm == pytest.approx(25735.79)
    assert parsed.filament_cm3 == pytest.approx(61.90)
    assert parsed.filament_g == pytest.approx(76.76)
    assert parsed.filament_cost == pytest.approx(4.60)


def test_parses_tpu_metadata():
    parsed = parse_gcode_metadata(_fixture("tpu_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    assert parsed.filament_g == pytest.approx(77.25)
    assert parsed.time_seconds == 8 * 3600 + 6 * 60 + 5  # 8h06m05s


def test_settings_ids_extracted_and_dequoted():
    parsed = parse_gcode_metadata(_fixture("pla_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    assert parsed.settings_ids == {
        "filament_settings_id": "AI Rosa3D PLA Starter",
        "printer_settings_id": "Creality K1 Max (0.4 nozzle)",
        "print_settings_id": "AI 0.20mm (0.4 nozzle) - MicroSwiss HF",
    }


def test_parse_is_order_independent():
    # Shuffle the metadata footer lines — the key-anchored parser must not depend on
    # ordering or on g-code body content (only the comment keys).
    lines = _fixture("pla_standard.gcode").splitlines()
    shuffled = "\n".join(reversed(lines))
    parsed = parse_gcode_metadata(shuffled)
    assert isinstance(parsed, ParsedEstimate)
    assert parsed.filament_g == pytest.approx(76.76)
    assert parsed.time_seconds == 3 * 3600 + 35 * 60 + 47


def test_parser_is_pure_no_io(monkeypatch):
    # A pure text→struct function must touch NO filesystem and NO clock. Load the text
    # FIRST, then forbid all I/O before calling the parser.
    text = _fixture("pla_standard.gcode")

    def _boom(*args, **kwargs):  # pragma: no cover - only fires on a purity breach
        raise AssertionError("parser performed I/O")

    monkeypatch.setattr("builtins.open", _boom)
    monkeypatch.setattr(Path, "read_text", _boom)
    monkeypatch.setattr(Path, "open", _boom)
    parsed = parse_gcode_metadata(text)
    assert isinstance(parsed, ParsedEstimate)
    # ParsedEstimate carries no timestamp — the clock-stamped computed_at is the
    # caller's job (AC-2), keeping the parser deterministic.
    assert "computed_at" not in ParsedEstimate.model_fields


# === AC-3: time-string normalization =========================================


def test_duration_h_m_s():
    assert parse_duration_to_seconds("3h35m47s") == 3 * 3600 + 35 * 60 + 47


def test_duration_m_s_only():
    assert parse_duration_to_seconds("35m47s") == 35 * 60 + 47


def test_duration_s_only():
    assert parse_duration_to_seconds("47s") == 47


def test_duration_with_days():
    assert parse_duration_to_seconds("1d2h3m4s") == 86400 + 2 * 3600 + 3 * 60 + 4


def test_duration_garbled_returns_none():
    assert parse_duration_to_seconds("3x5") is None
    assert parse_duration_to_seconds("abc") is None
    assert parse_duration_to_seconds("3600") is None  # bare number has no d/h/m/s unit


def test_duration_empty_returns_none():
    assert parse_duration_to_seconds("") is None
    assert parse_duration_to_seconds("   ") is None


# === AC-4: classified parse failure, never a silent zero =====================


def test_missing_time_line_classifies_missing_metadata_line():
    failure = parse_gcode_metadata(_fixture("missing_time.gcode"))
    assert isinstance(failure, EstimateParseFailure)
    assert failure.reason == EstimateFailureReason.missing_metadata_line
    assert "time" in failure.detail.lower()


def test_missing_filament_g_classifies_missing_metadata_line():
    text = "\n".join(
        line
        for line in _fixture("pla_standard.gcode").splitlines()
        if "filament used [g]" not in line
    )
    failure = parse_gcode_metadata(text)
    assert isinstance(failure, EstimateParseFailure)
    assert failure.reason == EstimateFailureReason.missing_metadata_line


def test_non_numeric_mass_classifies_unparseable_numeric():
    failure = parse_gcode_metadata(_fixture("garbled.gcode"))
    assert isinstance(failure, EstimateParseFailure)
    assert failure.reason == EstimateFailureReason.unparseable_numeric


def test_unparseable_time_classifies_unparseable_time():
    text = _fixture("pla_standard.gcode").replace("3h35m47s", "soon-ish")
    failure = parse_gcode_metadata(text)
    assert isinstance(failure, EstimateParseFailure)
    assert failure.reason == EstimateFailureReason.unparseable_time


def test_missing_cost_is_non_fatal():
    text = "\n".join(
        line
        for line in _fixture("pla_standard.gcode").splitlines()
        if "total filament cost" not in line
    )
    parsed = parse_gcode_metadata(text)
    assert isinstance(parsed, ParsedEstimate)  # cost is informational — absence is OK
    assert parsed.filament_cost is None
    assert parsed.filament_g == pytest.approx(76.76)


def test_missing_settings_ids_is_non_fatal_attribution_degrades():
    text = "\n".join(
        line for line in _fixture("pla_standard.gcode").splitlines() if "settings_id" not in line
    )
    parsed = parse_gcode_metadata(text)
    assert isinstance(parsed, ParsedEstimate)  # attribution degrades, numbers stay valid
    assert parsed.settings_ids == {}
    assert parsed.time_seconds is not None


def test_parse_failure_never_returns_silent_zero():
    # Every failure path returns a typed failure, NEVER a ParsedEstimate with 0s.
    for text in (
        _fixture("missing_time.gcode"),
        _fixture("garbled.gcode"),
        "; no metadata here at all\nG1 X0 Y0\n",
        "",
    ):
        result = parse_gcode_metadata(text)
        assert isinstance(result, EstimateParseFailure)


# === AC-5 + AC-6: append-only store + dedup ==================================


def _record(status=EstimateStatus.fresh, *, computed_at="2026-06-01T00:00:00+00:00", **kw):
    base = dict(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        time_seconds=12947,
        filament_g=76.76,
        filament_mm=25735.79,
        filament_cm3=61.90,
        filament_cost=4.60,
        settings_ids={"filament_settings_id": "AI Rosa3D PLA Starter"},
        status=status,
        computed_at=computed_at,
    )
    base.update(kw)
    return EstimateRecord(**base)


def _failed_record(
    *,
    reason=EstimateFailureReason.parse_failure,
    computed_at="2026-06-01T00:00:00+00:00",
    **kw,
):
    # A failed record carries NO numerics (the no-silent-zero invariant) + a reason.
    base = dict(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.failed,
        reason=reason,
        computed_at=computed_at,
    )
    base.update(kw)
    return EstimateRecord(**base)


def test_estimate_store_write_then_read_roundtrip(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_record())
    got = store.read(STL_HASH, BUNDLE_HASH)
    assert got is not None
    assert got.stl_hash == STL_HASH
    assert got.bundle_hash == BUNDLE_HASH
    assert got.filament_g == pytest.approx(76.76)
    assert got.status == EstimateStatus.fresh


def test_estimate_store_layout_is_stl_then_bundle_fanout(tmp_path):
    store = EstimateStore(tmp_path)
    path = store.write(_record())
    expected = tmp_path / "estimates" / STL_HASH[:2] / STL_HASH / f"{BUNDLE_HASH}.json"
    assert path == expected
    assert path.exists()


def test_estimate_store_rejects_malformed_stl_hash(tmp_path):
    store = EstimateStore(tmp_path)
    with pytest.raises(ValueError, match="content hash"):
        store.write(_record(stl_hash="../../etc/passwd"))


def test_estimate_store_rejects_malformed_bundle_hash(tmp_path):
    store = EstimateStore(tmp_path)
    with pytest.raises(ValueError, match="content hash"):
        store.write(_record(bundle_hash="../../etc/passwd"))


def test_estimate_store_read_miss_returns_none(tmp_path):
    store = EstimateStore(tmp_path)
    assert store.read(STL_HASH, BUNDLE_HASH) is None  # never a fabricated default
    # A malformed hash is a miss, not a path build.
    assert store.read("../../etc", BUNDLE_HASH) is None


def test_estimate_store_atomic_write_no_partial_on_concurrent_read(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_record())
    path = store.write(_failed_record())  # replace path exists
    # The published file is always complete + valid JSON (atomic publish).
    EstimateRecord.model_validate_json(path.read_text(encoding="utf-8"))


def test_fresh_rewrite_is_idempotent_noop(tmp_path):
    store = EstimateStore(tmp_path)
    p1 = store.write(_record(filament_g=76.76))
    content1 = p1.read_text(encoding="utf-8")
    # A second fresh write for the same key — even with different numbers — is a no-op.
    p2 = store.write(_record(filament_g=999.99, computed_at="2099-01-01T00:00:00+00:00"))
    assert p1 == p2
    assert p2.read_text(encoding="utf-8") == content1  # first fresh wins, untouched


def test_rewrite_over_failed_replaces(tmp_path):
    store = EstimateStore(tmp_path)
    store.write(_failed_record(reason=EstimateFailureReason.parse_failure))
    # A retry that now parses cleanly MUST win over the failed placeholder.
    store.write(_record(status=EstimateStatus.fresh, filament_g=76.76))
    got = store.read(STL_HASH, BUNDLE_HASH)
    assert got is not None
    assert got.status == EstimateStatus.fresh
    assert got.filament_g == pytest.approx(76.76)


def test_computed_at_difference_alone_is_not_a_change(tmp_path):
    store = EstimateStore(tmp_path)
    p1 = store.write(_record(computed_at="2026-06-01T00:00:00+00:00"))
    content1 = p1.read_text(encoding="utf-8")
    p2 = store.write(_record(computed_at="2026-12-31T23:59:59+00:00"))
    # Only computed_at differs ⇒ no change ⇒ the first record is preserved verbatim.
    assert p2.read_text(encoding="utf-8") == content1


# === AC-7: cost-carry + attribution ==========================================


def test_record_carries_filament_g_and_cost_for_arithmetic_recompute():
    parsed = parse_gcode_metadata(_fixture("pla_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    # Both mass AND cost carried so Story 32.4 recomputes cost = mass x price/gram
    # WITHOUT re-slicing (OD-7 / NFR20-REPRODUCIBLE-1 — the R1 self-DoS guard).
    assert parsed.filament_g is not None
    assert parsed.filament_cost is not None


def test_settings_ids_attribution_present_on_success():
    parsed = parse_gcode_metadata(_fixture("pla_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    assert "filament_settings_id" in parsed.settings_ids
    assert "print_settings_id" in parsed.settings_ids
    assert "printer_settings_id" in parsed.settings_ids


def test_attribution_invariant_record_names_its_profile():
    # NFR20-ATTRIBUTION-1 — a successful estimate always names which resolved profile
    # produced it (so a bad estimate is at least traceable).
    parsed = parse_gcode_metadata(_fixture("pla_standard.gcode"))
    assert isinstance(parsed, ParsedEstimate)
    rec = EstimateRecord(
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
        status=EstimateStatus.fresh,
        time_seconds=parsed.time_seconds,
        filament_g=parsed.filament_g,
        filament_mm=parsed.filament_mm,
        filament_cm3=parsed.filament_cm3,
        settings_ids=parsed.settings_ids,
        computed_at="2026-06-01T00:00:00+00:00",
    )
    assert rec.settings_ids != {}


# === AC-8: parser-sink + persist integration =================================


def test_parsing_sink_stashes_parsed_result(tmp_path):
    gcode = tmp_path / "part.gcode"
    gcode.write_text(_fixture("pla_standard.gcode"), encoding="utf-8")
    sink = ParsingGcodeSink()
    sink(gcode)
    assert isinstance(sink.result, ParsedEstimate)
    assert sink.result.filament_g == pytest.approx(76.76)


def test_parsing_sink_does_not_retain_gcode_after_job(tmp_path):
    gcode = tmp_path / "part.gcode"
    gcode.write_text(_fixture("pla_standard.gcode"), encoding="utf-8")
    sink = ParsingGcodeSink()
    sink(gcode)
    gcode.unlink()  # the 32.2 scratch-dir context manager deletes the temp g-code
    # The sink kept only the typed parse result, NOT the path or raw g-code text.
    assert isinstance(sink.result, ParsedEstimate)
    assert not gcode.exists()


class _StubStore:
    """In-memory EstimateStore stand-in honoring the fresh⇒no-op / non-fresh⇒replace rule."""

    def __init__(self) -> None:
        self.records: dict[tuple[str, str], EstimateRecord] = {}

    def write(self, record: EstimateRecord):
        key = (record.stl_hash, record.bundle_hash)
        existing = self.records.get(key)
        if existing is not None and existing.status == EstimateStatus.fresh:
            return None
        self.records[key] = record
        return None


def _ok_outcome(status=SliceStatus.ok, warnings=None):
    return SliceOutcome(
        status=status,
        warnings=warnings or [],
        manifold=True,
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
    )


def _run_slice_estimate(monkeypatch, *, outcome, gcode_text):
    """Drive slice_estimate with run_slice_job stubbed to fire the sink + return outcome."""
    store = _StubStore()

    def fake_run_slice_job(*, gcode_sink, **kwargs):
        if outcome.status in (SliceStatus.ok, SliceStatus.warning) and gcode_text is not None:
            gcode_sink(_FakeGcode(gcode_text))
        return outcome

    monkeypatch.setattr(worker_job_module, "run_slice_job", fake_run_slice_job)
    ctx = {
        "stl_cache": object(),
        "bundle_store": object(),
        "cli": object(),
        "orca_version": "2.3.2",
        "estimate_store": store,
    }
    asyncio.run(slice_estimate(ctx, STL_HASH, BUNDLE_HASH))
    return store


class _FakeGcode:
    """A path-like the ParsingGcodeSink can read without a real file."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.suffix = ".gcode"

    def read_text(self, *args, **kwargs) -> str:
        return self._text


def test_slice_estimate_persists_fresh_record_on_ok(monkeypatch):
    store = _run_slice_estimate(
        monkeypatch, outcome=_ok_outcome(), gcode_text=_fixture("pla_standard.gcode")
    )
    rec = store.records[(STL_HASH, BUNDLE_HASH)]
    assert rec.status == EstimateStatus.fresh
    assert rec.filament_g == pytest.approx(76.76)
    assert rec.time_seconds == 3 * 3600 + 35 * 60 + 47


def test_slice_estimate_persists_failed_record_on_parse_failure(monkeypatch):
    store = _run_slice_estimate(
        monkeypatch, outcome=_ok_outcome(), gcode_text=_fixture("garbled.gcode")
    )
    rec = store.records[(STL_HASH, BUNDLE_HASH)]
    assert rec.status == EstimateStatus.failed
    assert rec.reason == EstimateFailureReason.unparseable_numeric
    assert rec.filament_g is None  # never a silent zero


def test_slice_estimate_writes_no_record_on_invocation_failure(monkeypatch):
    failed = SliceOutcome(
        status=SliceStatus.failed,
        reason=SliceFailureReason.non_manifold,
        stl_hash=STL_HASH,
        bundle_hash=BUNDLE_HASH,
        orca_version="2.3.2",
    )
    store = _run_slice_estimate(monkeypatch, outcome=failed, gcode_text=None)
    # A slice-INVOCATION failure is fully described by SliceOutcome — 32.3 writes nothing.
    assert store.records == {}


def test_classify_and_run_slice_job_orchestration_unreshaped():
    # AC-8 — the Story 32.2 orchestration is byte-unreshaped: signatures + the sink
    # call site inside _classify are untouched.
    classify_sig = inspect.signature(worker_job_module._classify)
    assert list(classify_sig.parameters) == [
        "stl_hash",
        "bundle_hash",
        "stl_cache",
        "bundle_store",
        "cli",
        "sink",
    ]
    run_sig = inspect.signature(worker_job_module.run_slice_job)
    assert list(run_sig.parameters) == [
        "stl_hash",
        "bundle_hash",
        "stl_cache",
        "bundle_store",
        "cli",
        "orca_version",
        "gcode_sink",
    ]
    source = inspect.getsource(worker_job_module._classify)
    assert "sink(gcode)" in source  # the 32.2 sink hand-off call site is intact


# === AC-9: settings slot + grep invariant ====================================


def test_slicer_estimate_store_dir_default(monkeypatch):
    from app.core.config import Settings

    monkeypatch.delenv("SLICER_ESTIMATE_STORE_DIR", raising=False)
    s = Settings()
    # Store ROOT (EstimateStore adds the internal estimates/ child) — container-internal,
    # never a bench/Windows path.
    assert str(s.slicer_estimate_store_dir) == "/data/content/slicer"


def test_no_bench_or_windows_path_literal_in_new_slicer_files():
    # AC-9 / NFR20-CONTAINER-1 — the new parser/store files carry no path/exe literal.
    full = re.compile(r"/mnt/c|fenrir|\.exe|[Ww]indows", re.IGNORECASE)
    for name in ("gcode_parse.py", "estimate_store.py"):
        path = REPO_ROOT / "apps/api/app/modules/slicer" / name
        assert not full.search(path.read_text(encoding="utf-8")), f"path/exe literal in {name}"


# === AC-10: observability ====================================================


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def estimate_log():
    logger = logging.getLogger("app.modules.slicer.worker_job")
    prev_level, prev_disabled = logger.level, logger.disabled
    handler = _ListHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.disabled = False
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)
        logger.disabled = prev_disabled


def test_estimate_persist_emits_structured_tags(monkeypatch, estimate_log):
    _run_slice_estimate(
        monkeypatch, outcome=_ok_outcome(), gcode_text=_fixture("pla_standard.gcode")
    )
    persist = [r for r in estimate_log.records if "estimate" in r.getMessage()]
    assert persist, "expected an estimate-persist log line"
    rec = persist[-1].__dict__
    for key in (
        "labels.stl_hash",
        "labels.bundle_hash",
        "labels.estimate_status",
        "labels.orca_version",
    ):
        assert key in rec, f"missing structured tag {key}"
    assert rec["labels.estimate_status"] == "fresh"


def test_parse_failure_emits_failure_reason_and_breadcrumb(monkeypatch, estimate_log):
    breadcrumbs: list[dict] = []
    monkeypatch.setattr(
        worker_job_module.sentry_sdk,
        "add_breadcrumb",
        lambda **kw: breadcrumbs.append(kw),
    )
    _run_slice_estimate(monkeypatch, outcome=_ok_outcome(), gcode_text=_fixture("garbled.gcode"))
    persist = [r for r in estimate_log.records if "estimate" in r.getMessage()]
    assert persist
    assert persist[-1].__dict__["labels.estimate_failure_reason"] == "unparseable_numeric"
    assert any(b.get("category") == "slicer" and b.get("level") == "error" for b in breadcrumbs)


def test_full_gcode_never_appears_in_logs(monkeypatch, estimate_log):
    marker = "G1 X20 Y10 E2.0"  # a g-code body line present in the PLA fixture
    _run_slice_estimate(
        monkeypatch, outcome=_ok_outcome(), gcode_text=_fixture("pla_standard.gcode")
    )
    assert estimate_log.records, "expected estimate persist to emit a log line"
    for record in estimate_log.records:
        assert marker not in record.getMessage()
        for value in record.__dict__.values():
            assert not (isinstance(value, str) and marker in value)


# === AC-12: determinism ======================================================


def test_parse_is_deterministic_across_repeated_calls():
    text = _fixture("pla_standard.gcode")
    first = parse_gcode_metadata(text)
    for _ in range(5):
        again = parse_gcode_metadata(text)
        assert isinstance(first, ParsedEstimate)
        assert isinstance(again, ParsedEstimate)
        assert again.model_dump() == first.model_dump()  # no clock/random in the parser


# === Review-fix #1: non-finite numeric metadata is never a successful estimate =====
#
# float("nan")/float("inf")/float("-inf") all parse without ValueError — so a required
# numeric of "nan"/"inf" would otherwise slip through as a ParsedEstimate (and persist
# as a fresh, plausible-but-wrong estimate). Required non-finite ⇒ unparseable_numeric;
# optional cost non-finite ⇒ degrade to None (consistent with the optional-field rule).


def _replace_metadata(text: str, key: str, new_value: str) -> str:
    return "\n".join(
        f"; {key} = {new_value}" if line.strip().startswith(f"; {key}") else line
        for line in text.splitlines()
    )


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "Infinity", "NaN"])
@pytest.mark.parametrize("key", ["filament used [mm]", "filament used [cm3]", "filament used [g]"])
def test_non_finite_required_numeric_classifies_unparseable_numeric(key, bad):
    text = _replace_metadata(_fixture("pla_standard.gcode"), key, bad)
    result = parse_gcode_metadata(text)
    assert isinstance(result, EstimateParseFailure)  # never a ParsedEstimate
    assert result.reason == EstimateFailureReason.unparseable_numeric


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_non_finite_cost_degrades_to_none_non_fatal(bad):
    text = _replace_metadata(_fixture("pla_standard.gcode"), "total filament cost", bad)
    parsed = parse_gcode_metadata(text)
    # Cost is informational/optional — a non-finite cost degrades to absent, the
    # load-bearing numerics stay valid (mirrors the missing-cost non-fatal rule).
    assert isinstance(parsed, ParsedEstimate)
    assert parsed.filament_cost is None
    assert parsed.filament_g == pytest.approx(76.76)


# === Review-fix #2: EstimateRecord enforces failed/fresh invariants =================


def test_failed_record_with_numerics_is_rejected():
    # A failed record must not carry numbers — that would be a silent number behind a
    # failure status (defense-in-depth on the no-silent-zero contract).
    with pytest.raises(ValidationError):
        EstimateRecord(
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            status=EstimateStatus.failed,
            reason=EstimateFailureReason.unparseable_numeric,
            filament_g=76.76,
            computed_at="2026-06-01T00:00:00+00:00",
        )


def test_failed_record_without_reason_is_rejected():
    with pytest.raises(ValidationError):
        EstimateRecord(
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            status=EstimateStatus.failed,
            computed_at="2026-06-01T00:00:00+00:00",
        )


def test_fresh_record_missing_required_numeric_is_rejected():
    # A fresh record must carry every load-bearing numeric — a None here would be a
    # fresh estimate with a hole a caller could misread.
    with pytest.raises(ValidationError):
        EstimateRecord(
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            status=EstimateStatus.fresh,
            time_seconds=12947,
            filament_mm=25735.79,
            filament_cm3=61.90,
            # filament_g omitted ⇒ None ⇒ invalid fresh record
            computed_at="2026-06-01T00:00:00+00:00",
        )


def test_fresh_record_with_failure_reason_is_rejected():
    with pytest.raises(ValidationError):
        EstimateRecord(
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            status=EstimateStatus.fresh,
            time_seconds=12947,
            filament_g=76.76,
            filament_mm=25735.79,
            filament_cm3=61.90,
            reason=EstimateFailureReason.parse_failure,  # a fresh record has no reason
            computed_at="2026-06-01T00:00:00+00:00",
        )


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_fresh_record_rejects_non_finite_float(bad):
    # Defense-in-depth: even if a non-finite value reached the record builder, the model
    # rejects it rather than persisting nan/inf as a fresh number.
    with pytest.raises(ValidationError):
        EstimateRecord(
            stl_hash=STL_HASH,
            bundle_hash=BUNDLE_HASH,
            orca_version="2.3.2",
            status=EstimateStatus.fresh,
            time_seconds=12947,
            filament_g=bad,
            filament_mm=25735.79,
            filament_cm3=61.90,
            computed_at="2026-06-01T00:00:00+00:00",
        )


def test_valid_fresh_and_failed_records_still_accepted():
    # The invariants must not reject legitimately-shaped records.
    fresh = _record()
    assert fresh.status == EstimateStatus.fresh
    failed = _failed_record()
    assert failed.status == EstimateStatus.failed
    assert failed.time_seconds is None


# === Review-fix #3: fresh-record write is race-safe (no TOCTOU overwrite) ===========


def test_concurrent_fresh_write_does_not_overwrite_existing_fresh(tmp_path, monkeypatch):
    """Two writers race for the same (empty) key; the first fresh record must win and its
    ``computed_at`` must be preserved. The check-then-publish window is serialized per
    record, so the second writer observes the first's fresh record and no-ops (it never
    clobbers it) — the AC-6 idempotent-no-op holds under concurrency, not just serially.
    """
    store = EstimateStore(tmp_path)
    publish_started = threading.Event()
    release_publish = threading.Event()
    orig_publish = EstimateStore._atomic_publish

    def slow_publish(path, content):
        # Hold the critical section open so the second writer is forced to contend on the
        # per-record lock before the first writer has published.
        publish_started.set()
        assert release_publish.wait(timeout=5)
        return orig_publish(path, content)

    monkeypatch.setattr(EstimateStore, "_atomic_publish", staticmethod(slow_publish))

    first = _record(filament_g=11.11, computed_at="2026-01-01T00:00:00+00:00")
    second = _record(filament_g=22.22, computed_at="2026-12-31T00:00:00+00:00")

    t1 = threading.Thread(target=store.write, args=(first,))
    t1.start()
    assert publish_started.wait(timeout=5)  # writer #1 holds the lock, mid-publish
    t2 = threading.Thread(target=store.write, args=(second,))
    t2.start()
    release_publish.set()  # let writer #1 finish; writer #2 will see a fresh record
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive()

    got = store.read(STL_HASH, BUNDLE_HASH)
    assert got is not None
    assert got.status == EstimateStatus.fresh
    assert got.computed_at == "2026-01-01T00:00:00+00:00"  # first fresh preserved
    assert got.filament_g == pytest.approx(11.11)  # never the second writer's number
