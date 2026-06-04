"""Tests for the slicer worker job, enqueue, queue/settings + observability.

Story 32.2 (Decision AI). The arq invocation + real Orca are mocked: a fake
subprocess runner exercises every happy/warning/failure branch deterministically
(real Orca is bench/container-gated, AC-3/AC-12). Covers AC-2 (idempotent 2-tuple
job + dedicated queue), AC-4 (bundle-store + STL cache reads + miss classification),
AC-5 (temp g-code parse-and-discard + 32.3 sink seam), AC-6 (failure/warning
classification, never a silent zero), AC-7 (bounded concurrency + timeout classify),
AC-8 (structured tags, no full g-code logged), AC-9 (grep invariant), AC-13 (no
router mounted).
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.cli import OrcaCli, RunnerResult
from app.modules.slicer.enqueue import enqueue_slice_estimate, slice_job_id
from app.modules.slicer.models import (
    SliceFailureReason,
    SliceOutcome,
    SlicerProfileBundle,
    SliceStatus,
    SliceWarning,
)
from app.modules.slicer.stl_cache import StlCache, compute_stl_hash
from app.modules.slicer.worker import SLICER_QUEUE_NAME, SlicerWorkerSettings
from app.modules.slicer.worker_job import SLICE_JOB_NAME, discard_sink, run_slice_job

REPO_ROOT = Path(__file__).resolve().parents[3]
GCODE_BODY_MARKER = "; UNIQUE_GCODE_BODY_MARKER estimated printing time = 3h35m"


class FakeRunner:
    """Subprocess-shaped runner seam (AC-3): records call order + captured outdir.

    Distinguishes the ``--info`` pre-check from the slice by the argv. On a
    successful slice it writes a g-code file into the ``--outputdir`` so the worker's
    discover-and-discard path is exercised.
    """

    def __init__(
        self,
        *,
        manifold: str = "yes",
        info_returncode: int = 0,
        slice_returncode: int = 0,
        slice_stdout: str = "",
        slice_stderr: str = "",
        write_gcode: bool = True,
        info_timeout: bool = False,
        slice_timeout: bool = False,
        info_oserror: BaseException | None = None,
        slice_oserror: BaseException | None = None,
    ) -> None:
        self.manifold = manifold
        self._manifold_values = list(manifold) if isinstance(manifold, list) else None
        self.info_returncode = info_returncode
        self.slice_returncode = slice_returncode
        self._slice_returncodes = (
            list(slice_returncode) if isinstance(slice_returncode, list) else None
        )
        self.slice_stdout = slice_stdout
        self.slice_stderr = slice_stderr
        self.write_gcode = write_gcode
        self.info_timeout = info_timeout
        self.slice_timeout = slice_timeout
        self.info_oserror = info_oserror
        self.slice_oserror = slice_oserror
        self.calls: list[str] = []
        self.captured_outdir: Path | None = None
        self.captured_machine: str | None = None
        self.info_paths: list[Path] = []
        self.slice_stl: Path | None = None

    def __call__(self, argv: list[str], timeout_s: float) -> RunnerResult:
        if "--info" in argv:
            self.calls.append("info")
            self.info_paths.append(Path(argv[-1]))
            if self.info_oserror is not None:
                raise self.info_oserror
            if self.info_timeout:
                raise subprocess.TimeoutExpired(argv, timeout_s)
            manifold = self._manifold_values.pop(0) if self._manifold_values else self.manifold
            return RunnerResult(
                self.info_returncode, f"facets: 1200\nmanifold: {manifold}\nvolume: 42", ""
            )
        # slice
        self.calls.append("slice")
        if self.slice_oserror is not None:
            raise self.slice_oserror
        load_idx = argv.index("--load-settings")
        machine_path = Path(argv[load_idx + 1].split(";")[0])
        self.captured_machine = machine_path.read_text()
        outdir = Path(argv[argv.index("--outputdir") + 1])
        self.captured_outdir = outdir
        self.slice_stl = Path(argv[-1])
        if self.slice_timeout:
            raise subprocess.TimeoutExpired(argv, timeout_s)
        if self.write_gcode:
            (outdir / "part.gcode").write_text(f"{GCODE_BODY_MARKER}\nG1 X0 Y0\n")
        slice_returncode = (
            self._slice_returncodes.pop(0) if self._slice_returncodes else self.slice_returncode
        )
        return RunnerResult(slice_returncode, self.slice_stdout, self.slice_stderr)


def _make_bundle(bundle_hash: str, *, machine: dict | None = None) -> SlicerProfileBundle:
    return SlicerProfileBundle(
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        machine=machine or {"m": "MACHINE_DISTINCT"},
        process={"p": 1},
        filament={"f": 1},
        source_snapshot_ref="snap-ref",
        created_at="2026-06-01T00:00:00+00:00",
    )


@pytest.fixture
def slice_env(tmp_path):
    """A bundle store + STL cache + a present bundle + a present STL."""
    store = BundleStore(tmp_path / "store")
    cache = StlCache(tmp_path / "cache")
    bundle_hash = "bb" + "1" * 62
    store.write_bundle(_make_bundle(bundle_hash))
    src = tmp_path / "catalog.stl"
    src.write_bytes(b"solid mesh\nendsolid mesh\n")
    stl_hash = cache.populate_from_source(src)
    return {
        "store": store,
        "cache": cache,
        "bundle_hash": bundle_hash,
        "stl_hash": stl_hash,
        "tmp_path": tmp_path,
    }


class FakeMeshRepairer:
    def __init__(self, *, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.calls: list[tuple[Path, Path]] = []
        self.written_bytes: bytes | None = None

    def repair(self, source: Path, target: Path) -> bool:
        self.calls.append((source, target))
        if not self.succeeds:
            return False
        self.written_bytes = source.read_bytes() + b"\nrepaired-copy\n"
        target.write_bytes(self.written_bytes)
        return True


def _run(slice_env, runner: FakeRunner, *, gcode_sink=None, mesh_repairer=None) -> SliceOutcome:
    cli = OrcaCli(orca_bin="/opt/orca/orca", runner=runner, info_timeout_s=60, slice_timeout_s=900)
    return run_slice_job(
        stl_hash=slice_env["stl_hash"],
        bundle_hash=slice_env["bundle_hash"],
        stl_cache=slice_env["cache"],
        bundle_store=slice_env["store"],
        cli=cli,
        orca_version="2.3.2",
        gcode_sink=gcode_sink,
        mesh_repairer=mesh_repairer,
    )


# --- models (T1.2) -------------------------------------------------------------


def test_slice_enums_and_outcome_shape():
    assert {s.value for s in SliceStatus} == {"ok", "warning", "failed"}
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
    out = SliceOutcome(status=SliceStatus.ok)
    assert out.reason is None
    assert out.warnings == []
    assert out.gcode_temp_ref is None
    assert SliceWarning(message="x").message == "x"


# --- AC-2: idempotent 2-tuple job + dedicated queue ----------------------------


def test_enqueue_uses_stl_bundle_tuple_job_id_for_dedupe(tmp_path):
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "a.stl"
    src.write_bytes(b"abc")
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))
    bundle_hash = "bb" + "0" * 62
    import asyncio

    asyncio.run(
        enqueue_slice_estimate(pool, source_stl=src, bundle_hash=bundle_hash, stl_cache=cache)
    )
    stl_hash = compute_stl_hash(src)
    _, kwargs = pool.enqueue_job.call_args
    assert kwargs["_job_id"] == f"slice:{stl_hash}:{bundle_hash}"
    assert kwargs["_job_id"] == slice_job_id(stl_hash, bundle_hash)


def test_enqueue_targets_dedicated_slicer_queue(tmp_path):
    assert SLICER_QUEUE_NAME == "arq:slicer"
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "a.stl"
    src.write_bytes(b"abc")
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))
    import asyncio

    asyncio.run(enqueue_slice_estimate(pool, source_stl=src, bundle_hash="b" * 64, stl_cache=cache))
    _, kwargs = pool.enqueue_job.call_args
    assert kwargs["_queue_name"] == SLICER_QUEUE_NAME


def test_job_payload_carries_only_the_two_hashes(tmp_path):
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "a.stl"
    src.write_bytes(b"abc")
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))
    import asyncio

    bundle_hash = "b" * 64
    asyncio.run(
        enqueue_slice_estimate(pool, source_stl=src, bundle_hash=bundle_hash, stl_cache=cache)
    )
    args, _ = pool.enqueue_job.call_args
    stl_hash = compute_stl_hash(src)
    assert args == (SLICE_JOB_NAME, stl_hash, bundle_hash)  # name + 2 hashes ONLY


def test_enqueue_populates_cache_from_mirrored_catalog_copy(tmp_path):
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "catalog.stl"
    data = b"mirrored-catalog-bytes"
    src.write_bytes(data)
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))
    import asyncio

    result = asyncio.run(
        enqueue_slice_estimate(pool, source_stl=src, bundle_hash="b" * 64, stl_cache=cache)
    )
    cached = cache.read_path(result.stl_hash)
    assert cached is not None
    assert cached.read_bytes() == data


def test_enqueue_rejects_malformed_bundle_hash(tmp_path):
    # review fix #2 — a caller-supplied bundle_hash is validated BEFORE it is woven
    # into the _job_id / path lookups; a traversal-shaped hash never reaches the queue.
    cache = StlCache(tmp_path / "cache")
    src = tmp_path / "a.stl"
    src.write_bytes(b"abc")
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job"))
    import asyncio

    with pytest.raises(ValueError, match="content hash"):
        asyncio.run(
            enqueue_slice_estimate(
                pool, source_stl=src, bundle_hash="../../etc/passwd", stl_cache=cache
            )
        )
    pool.enqueue_job.assert_not_called()  # nothing enqueued on a malformed key


# --- AC-4: bundle store + STL cache reads + miss classification ----------------


def test_loads_resolved_triple_from_bundle_store_by_hash(slice_env):
    runner = FakeRunner()
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.ok
    # The slice was fed the triple loaded FROM the bundle store (distinct marker).
    assert json.loads(runner.captured_machine) == {"m": "MACHINE_DISTINCT"}


def test_missing_bundle_classifies_missing_bundle(slice_env):
    slice_env["bundle_hash"] = "no" + "0" * 62  # not in the store
    out = _run(slice_env, FakeRunner())
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_bundle


def test_cache_miss_classifies_missing_stl(slice_env):
    slice_env["stl_hash"] = "no" + "0" * 62  # not in the cache
    out = _run(slice_env, FakeRunner())
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_stl


# --- AC-3: --info pre-check before slice; non-manifold fast-fail ---------------


def test_info_precheck_runs_before_slice(slice_env):
    runner = FakeRunner()
    _run(slice_env, runner)
    assert runner.calls == ["info", "slice"]  # info STRICTLY before slice


def test_admesh_repairer_decodes_non_utf8_tool_output_defensively(monkeypatch, tmp_path):
    from app.modules.slicer import worker_job as worker_job_module

    source = tmp_path / "source.stl"
    target = tmp_path / "target.stl"
    source.write_bytes(b"solid mesh\nendsolid mesh\n")

    def fake_run(argv, **kwargs):
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        assert "--nearby" in argv
        assert "--fill-holes" in argv
        assert "--normal-directions" in argv
        assert "--normal-values" in argv
        target.write_bytes(b"solid repaired\nendsolid repaired\n")
        return subprocess.CompletedProcess(argv, 0, stdout="bad byte: \ufffd", stderr="")

    monkeypatch.setattr(worker_job_module.subprocess, "run", fake_run)

    assert worker_job_module.AdmeshRepairer().repair(source, target) is True


def test_non_manifold_info_fast_fails_without_slicing_when_repair_unavailable(slice_env):
    runner = FakeRunner(manifold="no")
    out = _run(slice_env, runner, mesh_repairer=None)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.non_manifold
    assert out.manifold is False
    assert "slice" not in runner.calls  # without repair seam, known-bad mesh is not sliced


def test_non_zero_exit_repairs_then_slices_repaired_temp_path(slice_env):
    runner = FakeRunner(manifold=["yes", "yes"], slice_returncode=[1, 0], write_gcode=True)
    repairer = FakeMeshRepairer()
    outcome = _run(slice_env, runner=runner, mesh_repairer=repairer)

    assert outcome.status == SliceStatus.warning
    assert outcome.used_repaired_mesh is True
    assert [p.name for p in runner.info_paths] == [
        slice_env["cache"].read_path(slice_env["stl_hash"]).name,
        "repaired.stl",
    ]
    assert runner.slice_stl is not None
    assert runner.slice_stl.name == "repaired.stl"
    assert repairer.calls[0][0] == slice_env["cache"].read_path(slice_env["stl_hash"])


def test_non_manifold_info_repairs_then_slices_repaired_temp_path(slice_env):
    runner = FakeRunner(manifold=["no", "yes"])
    repairer = FakeMeshRepairer()
    original = slice_env["cache"].read_path(slice_env["stl_hash"])

    out = _run(slice_env, runner, mesh_repairer=repairer)

    assert out.status != SliceStatus.failed
    assert out.used_repaired_mesh is True
    assert runner.calls == ["info", "info", "slice"]
    assert repairer.calls[0][0] == original
    assert repairer.calls[0][1].name == "repaired.stl"
    assert runner.info_paths == [original, repairer.calls[0][1]]
    assert runner.slice_stl == repairer.calls[0][1]


def test_failed_non_manifold_repair_keeps_non_manifold_failure(slice_env):
    runner = FakeRunner(manifold="no")
    repairer = FakeMeshRepairer(succeeds=False)

    out = _run(slice_env, runner, mesh_repairer=repairer)

    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.non_manifold
    assert out.used_repaired_mesh is False
    assert runner.calls == ["info"]


def test_non_manifold_repair_does_not_overwrite_original_stl(slice_env):
    runner = FakeRunner(manifold=["no", "yes"])
    repairer = FakeMeshRepairer()
    original = slice_env["cache"].read_path(slice_env["stl_hash"])
    before = original.read_bytes()

    out = _run(slice_env, runner, mesh_repairer=repairer)

    assert out.status != SliceStatus.failed
    assert original.read_bytes() == before
    assert repairer.written_bytes != before


# --- AC-5: temp g-code emit + parse-and-discard + 32.3 sink seam ---------------


def test_gcode_written_to_temp_path(slice_env):
    seen: dict[str, object] = {}

    def sink(path: Path) -> None:
        seen["path"] = path
        seen["existed"] = path.exists()

    out = _run(slice_env, FakeRunner(), gcode_sink=sink)
    assert out.status == SliceStatus.ok
    assert seen["existed"] is True  # g-code present in-job for the parser hand-off
    assert str(seen["path"]).endswith(".gcode")
    assert out.gcode_temp_ref is not None and out.gcode_temp_ref.endswith(".gcode")


def test_temp_gcode_discarded_on_success(slice_env):
    runner = FakeRunner()
    _run(slice_env, runner)
    assert runner.captured_outdir is not None
    assert not runner.captured_outdir.exists()  # scratch dir + g-code gone at job end


def test_temp_gcode_discarded_on_failure(slice_env):
    runner = FakeRunner(slice_returncode=1, slice_stderr="boom")
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert runner.captured_outdir is not None
    assert not runner.captured_outdir.exists()  # discarded even on failure


def test_no_gcode_retained_in_durable_store_or_log(slice_env):
    runner = FakeRunner()
    _run(slice_env, runner)
    # No g-code under the bundle store or STL cache roots (durable volumes).
    store_root = slice_env["tmp_path"] / "store"
    cache_root = slice_env["tmp_path"] / "cache"
    assert list(store_root.rglob("*.gcode")) == []
    assert list(cache_root.rglob("*.gcode")) == []


def test_parser_sink_is_injected_default_noop(slice_env):
    # Default sink discards (no-op); a custom 32.3 sink receives the g-code path.
    out = _run(slice_env, FakeRunner())  # default sink path — must not raise
    assert out.status == SliceStatus.ok
    assert discard_sink(Path("anything.gcode")) is None

    received: list[Path] = []
    _run(slice_env, FakeRunner(), gcode_sink=received.append)
    assert len(received) == 1
    assert received[0].suffix == ".gcode"


# --- AC-6: failure + warning classification, never a silent zero ---------------


def test_warning_slice_is_non_blocking_warning_status(slice_env):
    runner = FakeRunner(slice_stdout="Slicing\nWarning: floating cantilever\nDone")
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.warning
    assert out.reason is None  # warning is NON-blocking — the estimate is still valid
    assert any("cantilever" in w.message for w in out.warnings)


def test_non_zero_exit_classifies_non_zero_exit(slice_env):
    runner = FakeRunner(slice_returncode=139, slice_stderr="Segmentation fault")
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.non_zero_exit


def test_cli_rejected_profile_classifies_cli_rejected_profile(slice_env):
    runner = FakeRunner(slice_returncode=1, slice_stderr="error: failed to load filament profile")
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.cli_rejected_profile


def test_timeout_classifies_timeout(slice_env):
    runner = FakeRunner(slice_timeout=True)
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.timeout


def test_info_timeout_classifies_timeout(slice_env):
    runner = FakeRunner(info_timeout=True)
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.timeout


# --- review fix #1 (BLOCKER): exit 0 but NO g-code is a typed failure -----------


def test_zero_exit_but_no_gcode_classifies_missing_gcode(slice_env):
    # Orca returns 0 yet emits no *.gcode → there is NO parser input. A silent
    # ok/warning here would be a plausible-but-wrong zero downstream (FR20-FAILURE-1).
    runner = FakeRunner(slice_returncode=0, write_gcode=False)
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_gcode
    assert out.gcode_temp_ref is None  # never a transient ref to a file that doesn't exist


def test_missing_gcode_sink_not_called_and_scratch_discarded(slice_env):
    received: list[Path] = []
    runner = FakeRunner(write_gcode=False)
    out = _run(slice_env, runner, gcode_sink=received.append)
    assert out.reason == SliceFailureReason.missing_gcode
    assert received == []  # the parser sink is NEVER handed a non-existent g-code path
    assert runner.captured_outdir is not None
    assert not runner.captured_outdir.exists()  # scratch dir still discarded (AC-5)


# --- review fix #3: Orca launch errors classify launch_error, not uncaught ------


def test_info_launch_error_classifies_launch_error_without_slicing(slice_env):
    runner = FakeRunner(info_oserror=FileNotFoundError("no such orca"))
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.launch_error
    assert "slice" not in runner.calls  # never reaches the slice when --info can't launch


def test_slice_launch_error_classifies_launch_error(slice_env):
    runner = FakeRunner(slice_oserror=PermissionError("orca not executable"))
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.launch_error


def test_generic_oserror_on_launch_classifies_launch_error(slice_env):
    runner = FakeRunner(info_oserror=OSError("exec format error"))
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.launch_error


# --- review fix #4: non-zero --info return code is NOT ignored ------------------


def test_info_nonzero_returncode_classifies_info_precheck_failed(slice_env):
    runner = FakeRunner(info_returncode=2)
    out = _run(slice_env, runner)
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.info_precheck_failed


def test_info_nonzero_returncode_does_not_run_the_full_slice(slice_env):
    # A failed precheck must short-circuit BEFORE the minutes-long slice (AC-3 intent):
    # the slice runner is never invoked.
    runner = FakeRunner(info_returncode=2, manifold="yes")
    _run(slice_env, runner)
    assert runner.calls == ["info"]  # info ran, slice NEVER did
    assert "slice" not in runner.calls


# --- review fix #2: malformed hashes are rejected before any path is built ------


def test_malformed_bundle_hash_classifies_missing_bundle(slice_env):
    # A traversal-shaped bundle_hash must be rejected BEFORE bundle-store path use.
    slice_env["bundle_hash"] = "../../etc/passwd"
    out = _run(slice_env, FakeRunner())
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_bundle


def test_malformed_stl_hash_classifies_missing_stl(slice_env):
    slice_env["stl_hash"] = "../../../etc/shadow"
    out = _run(slice_env, FakeRunner())
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_stl


def test_uppercase_hash_is_rejected_as_malformed(slice_env):
    # Project style mints lowercase sha256 hexdigests; an uppercase hash is malformed.
    slice_env["stl_hash"] = "A" * 64
    out = _run(slice_env, FakeRunner())
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.missing_stl


@pytest.mark.parametrize(
    "runner_kwargs,override",
    [
        ({"manifold": "no"}, {"mesh_repairer": None}),
        ({"info_returncode": 2}, {}),
        ({"slice_returncode": 1, "slice_stderr": "boom"}, {}),
        ({"slice_returncode": 1, "slice_stderr": "failed to load"}, {}),
        ({"slice_timeout": True}, {}),
        ({"info_oserror": FileNotFoundError("x")}, {}),
        ({"slice_oserror": PermissionError("x")}, {}),
        ({"write_gcode": False}, {}),
        ({}, {"bundle_hash": "no" + "0" * 62}),
        ({}, {"stl_hash": "no" + "0" * 62}),
        ({}, {"bundle_hash": "../../etc/passwd"}),
    ],
)
def test_failure_never_returns_silent_zero(slice_env, runner_kwargs, override):
    mesh_repairer = override.pop("mesh_repairer", object())
    slice_env.update(override)
    out = _run(slice_env, FakeRunner(**runner_kwargs), mesh_repairer=mesh_repairer)
    assert isinstance(out, SliceOutcome)
    assert out.status == SliceStatus.failed
    assert out.reason is not None  # a machine-readable reason ALWAYS accompanies failure


# --- AC-7: bounded concurrency cap ---------------------------------------------


def test_slicer_worker_settings_concurrency_cap_default_is_bounded():
    from app.core.config import get_settings

    assert SlicerWorkerSettings.queue_name == SLICER_QUEUE_NAME
    assert SlicerWorkerSettings.max_jobs == get_settings().slicer_max_concurrency
    assert SlicerWorkerSettings.max_jobs <= 2  # bounded so a slice can't starve others
    assert SlicerWorkerSettings.max_jobs == 1  # default


def test_slice_timeout_terminates_and_classifies_timeout(slice_env):
    # Worker-side classification half of AC-7 (the process-group terminate is proven
    # in test_slicer_cli.test_subprocess_runner_raises_timeout_and_terminates...).
    out = _run(slice_env, FakeRunner(slice_timeout=True))
    assert out.status == SliceStatus.failed
    assert out.reason == SliceFailureReason.timeout


# --- AC-8: observability tags; g-code never logged in full ---------------------


class _ListHandler(logging.Handler):
    """Tiny in-memory handler — records every emitted record into ``records``."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def slice_log():
    """Capture ``app.modules.slicer.worker_job`` records via a dedicated handler.

    pytest's built-in ``caplog`` attaches to root, but
    ``app.core.logging.configure_logging`` does ``root.handlers[:] = ...`` during
    FastAPI lifespan startup (run by other tests in the suite), removing pytest's
    handler — so ``caplog`` captures nothing once any client/lifespan test has run.
    Attaching a dedicated handler to the named logger sidesteps the wipe (the
    repo-wide pattern from test_ratelimit_share_cap.py / test_spools.py).
    """
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


def test_job_emits_structured_tags_on_completion(slice_env, slice_log):
    _run(slice_env, FakeRunner())
    completion = [r for r in slice_log.records if "complete" in r.getMessage()]
    assert completion, "expected a completion log line"
    rec = completion[-1].__dict__
    for key in (
        "labels.stl_hash",
        "labels.bundle_hash",
        "labels.status",
        "labels.orca_version",
        "labels.slice_wall_ms",
        "labels.warning_count",
        "labels.manifold",
    ):
        assert key in rec, f"missing structured tag {key}"
    assert rec["labels.status"] == "ok"


def test_failure_emits_failure_reason_tag(slice_env, slice_log):
    _run(slice_env, FakeRunner(slice_returncode=1, slice_stderr="boom"))
    completion = [r for r in slice_log.records if "complete" in r.getMessage()]
    assert completion
    rec = completion[-1].__dict__
    assert rec["labels.failure_reason"] == "non_zero_exit"


def test_full_gcode_never_appears_in_logs(slice_env, slice_log):
    _run(slice_env, FakeRunner())
    assert slice_log.records, "expected slice job to emit log lines"
    for record in slice_log.records:
        assert GCODE_BODY_MARKER not in record.getMessage()
        for value in record.__dict__.values():
            assert not (isinstance(value, str) and GCODE_BODY_MARKER in value)


# --- AC-9: NFR20-CONTAINER-1 grep invariant ------------------------------------


def test_no_bench_or_windows_path_literal_in_slicer_module():
    # AC-9 / NFR20-CONTAINER-1. Per the AC clarification ("the test targets path/exe
    # literals, not the prose"): the slicer MODULE (this story's authored surface)
    # must be free of the FULL pattern — no /mnt/c, fenrir, .exe, or windows token
    # anywhere, comments included. config.py is shared with Story 32.1 provenance
    # prose that legitimately names the external boundary (".../external bench/Windows
    # host...", "FENRIR_EXPORT_PATH"), so it is checked for PATH/EXE LITERALS only.
    module = REPO_ROOT / "apps/api/app/modules/slicer"
    full = re.compile(r"/mnt/c|fenrir|\.exe|[Ww]indows", re.IGNORECASE)
    literal = re.compile(r"/mnt/c|\.exe", re.IGNORECASE)
    offenders: list[str] = []
    for path in sorted(module.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if full.search(path.read_text(encoding="utf-8", errors="ignore")):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    config = REPO_ROOT / "apps/api/app/core/config.py"
    if literal.search(config.read_text(encoding="utf-8")):
        offenders.append("apps/api/app/core/config.py")
    assert offenders == [], f"bench/Windows path/exe literal leaked into: {offenders}"


# --- AC-13 / Story 32.6: scope fence — narrow read-only router only -------------


def test_slicer_module_mounts_only_narrow_estimates_read_router():
    module = REPO_ROOT / "apps/api/app/modules/slicer"
    router_path = module / "router.py"
    assert router_path.exists()
    router_text = router_path.read_text(encoding="utf-8")

    # Story 32.6 added the first slicer HTTP surface (a single authenticated GET read seam);
    # EST-RECOMPUTE-1 added a guarded authenticated POST /recompute; EST-TIERS-1 adds exactly ONE
    # more narrow authenticated GET (/quality-tiers — the tier-availability bridge read that lets
    # the selector disable unresolvable profiles before a member can 422 an estimate read). Preserve
    # the scope-fence intent: a NARROW surface — exactly TWO GETs (quality-tier availability +
    # estimate read) and ONE POST (guarded recompute). The POST reuses the Story 32.4 enqueue
    # plumbing BYTE-IDENTICALLY (no duplicated job-id/queue constants, no source-file hashing),
    # never writes an estimate record from the API, and mounts no bulk / unbounded write route.
    assert 'APIRouter(prefix="/api/estimates"' in router_text
    assert router_text.count("@router.get") == 2
    # The added GET is the narrow tier-availability read (no bulk/unbounded variant).
    assert '"/quality-tiers"' in router_text
    # Exactly one POST, and it is the narrow /recompute path (no bulk/unbounded variant).
    assert router_text.count("@router.post") == 1
    assert '"/recompute"' in router_text
    # No bulk / unbounded fan-out surface: the Story 32.4 bulk helpers + the store's
    # whole-subtree iterator must NOT be reachable from the API router.
    assert "invalidate_bulk" not in router_text
    assert "recompute_cost_only_bulk" not in router_text
    assert "iter_all_estimates" not in router_text
    # The POST REUSES Story 32.4 enqueue_recompute (not a re-implemented enqueue): the helper is
    # imported + called, and the router does NOT re-derive the job-id / queue-name plumbing nor
    # call arq directly, nor hash a source file.
    assert "from app.modules.slicer.recompute import enqueue_recompute" in router_text
    assert "enqueue_recompute(" in router_text
    assert "def slice_job_id" not in router_text
    assert "slice_job_id(" not in router_text
    assert ".enqueue_job(" not in router_text
    assert "populate_from_source" not in router_text
    # The API never writes an estimate record (the worker owns the fresh terminus); status
    # transitions go through the store's guarded mark_queued, never a direct write().
    assert "store.write" not in router_text

    api_router = re.compile(r"\bAPIRouter\b")
    offenders = []
    for path in module.glob("*.py"):
        if path.name == "router.py":
            continue
        if api_router.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert offenders == []
