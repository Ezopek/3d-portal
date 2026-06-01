"""Tests for the Orca CLI invoke layer (Story 32.2, AC-3/AC-7).

``cli.py`` builds the ``--info`` pre-check argv + the headless slice argv and runs
them through an injectable subprocess-shaped runner seam. Real Orca is NEVER run in
CI (no AppImage); the unit suite injects a fake runner so every happy/warning/
failure path is exercised deterministically. The single real-Orca path is the
env-gated ``ORCA_SMOKE_TEST=1`` bench bridge at the bottom of this file.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from app.core.config import Settings
from app.modules.slicer.cli import (
    OrcaCli,
    RunnerResult,
    SubprocessRunner,
    build_info_command,
    build_slice_command,
    is_profile_rejection,
    parse_info_manifold,
    parse_slice_warnings,
)
from app.modules.slicer.validation import build_orca_load_flags, build_orca_smoke_command


def _contains_subsequence(haystack: list[str], needle: list[str]) -> bool:
    """True if ``needle`` appears as a contiguous run inside ``haystack``."""
    if not needle:
        return True
    for i in range(len(haystack) - len(needle) + 1):
        if haystack[i : i + len(needle)] == needle:
            return True
    return False


# --- argv builders -------------------------------------------------------------


def test_info_command_uses_settings_entrypoint_and_info_flag(tmp_path):
    stl = tmp_path / "mesh.stl"
    argv = build_info_command("/opt/orca/orca", stl)
    assert argv[0] == "/opt/orca/orca"  # entrypoint, never a literal
    assert "--info" in argv
    assert str(stl) in argv


def test_slice_argv_reuses_validation_command_shape(tmp_path):
    # AC-3 — the slice argv is built by EXTENDING the Story 32.1 load-flag shape
    # (single source of truth, no divergent re-implementation).
    m, p, f = tmp_path / "m.json", tmp_path / "p.json", tmp_path / "f.json"
    stl, outdir = tmp_path / "x.stl", tmp_path / "out"
    argv = build_slice_command("/opt/orca/orca", m, p, f, stl, outdir)
    load_flags = build_orca_load_flags(m, p, f)
    assert argv[0] == "/opt/orca/orca"
    assert _contains_subsequence(argv, load_flags)
    assert str(stl) in argv
    # The slice does an actual slice, not the cheap --info smoke.
    assert "--info" not in argv


def test_smoke_and_slice_share_the_same_load_flag_shape(tmp_path):
    # Single-source proof: both commands embed the identical build_orca_load_flags run.
    m, p, f = tmp_path / "m.json", tmp_path / "p.json", tmp_path / "f.json"
    stl, outdir = tmp_path / "x.stl", tmp_path / "out"
    load_flags = build_orca_load_flags(m, p, f)
    assert _contains_subsequence(build_orca_smoke_command(m, p, f, stl), load_flags)
    assert _contains_subsequence(build_slice_command("orca", m, p, f, stl, outdir), load_flags)


def test_orca_entrypoint_read_from_settings_not_hardcoded(monkeypatch):
    # AC-3/AC-9 — the OrcaCli entrypoint comes from settings (ORCA_BIN), never a
    # hard-coded path; the built argv carries exactly that entrypoint.
    monkeypatch.delenv("SLICER_ORCA_BIN", raising=False)
    monkeypatch.setenv("ORCA_BIN", "/opt/orca/squashfs-root/AppRun")
    cli = OrcaCli.from_settings(Settings(), runner=lambda argv, t: RunnerResult(0, "", ""))
    assert cli.orca_bin == "/opt/orca/squashfs-root/AppRun"
    argv = build_info_command(cli.orca_bin, Path("mesh.stl"))
    assert argv[0] == "/opt/orca/squashfs-root/AppRun"


def test_orca_cli_timeouts_read_from_settings(monkeypatch):
    # AC-7 — both the slice wall-time and the --info ceiling come from settings.
    monkeypatch.setenv("SLICER_SLICE_TIMEOUT_SECONDS", "123")
    monkeypatch.setenv("SLICER_INFO_TIMEOUT_SECONDS", "7")
    cli = OrcaCli.from_settings(Settings(), runner=lambda argv, t: RunnerResult(0, "", ""))
    assert cli.slice_timeout_s == 123
    assert cli.info_timeout_s == 7


# --- output parsing ------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("facets: 1200\nmanifold: yes\nvolume: 42", True),
        ("manifold: no", False),
        ("Manifold = NO", False),
        ("manifold yes", True),
        ("facets: 1200\nvolume: 42", None),  # field absent ⇒ unknown
    ],
)
def test_parse_info_manifold_yes_no_none(text, expected):
    assert parse_info_manifold(text) is expected


def test_parse_slice_warnings_extracts_warning_lines():
    stdout = "Slicing plate 1\nWarning: floating cantilever detected\nDone"
    stderr = "warning: thin wall near base"
    warnings = parse_slice_warnings(stdout, stderr)
    assert any("cantilever" in w for w in warnings)
    assert any("thin wall" in w for w in warnings)
    assert parse_slice_warnings("Slicing\nDone", "") == []


def test_is_profile_rejection_detects_load_rejection():
    assert is_profile_rejection("error: failed to load filament profile") is True
    assert is_profile_rejection("invalid value for nozzle_temperature") is True
    assert is_profile_rejection("Segmentation fault (core dumped)") is False


# --- the real subprocess runner: wall-time terminate (AC-7) --------------------


def test_subprocess_runner_raises_timeout_and_terminates_process_group():
    # AC-7 — a slice that overruns the wall-time budget is terminated (process
    # group killed) and surfaces as subprocess.TimeoutExpired for the worker to
    # classify ``timeout``. Uses a real ``sleep`` child (NOT Orca).
    runner = SubprocessRunner()
    with pytest.raises(subprocess.TimeoutExpired):
        runner(["sleep", "5"], 0.3)


def test_subprocess_runner_captures_returncode_and_streams():
    runner = SubprocessRunner()
    result = runner(["sh", "-c", "printf out; printf err 1>&2; exit 3"], 10)
    assert result.returncode == 3
    assert result.stdout == "out"
    assert result.stderr == "err"


# --- env-gated real-Orca bench bridge (AC-3/AC-12) -----------------------------


@pytest.mark.skipif(
    os.environ.get("ORCA_SMOKE_TEST") != "1",
    reason="bench-only: requires the real Orca AppImage in the slicer-worker container",
)
def test_real_orca_slice_smoke(tmp_path):  # pragma: no cover
    # Bench bridge: runs a real headless slice end-to-end. Verified out-of-band on
    # the configs-side slicer-worker container (AC-12); CI has no AppImage so this
    # is skipped by default. Mirrors Story 32.1's ORCA_SMOKE_TEST pattern.
    from app.core.config import get_settings

    settings = get_settings()
    machine = tmp_path / "machine.json"
    process = tmp_path / "process.json"
    filament = tmp_path / "filament.json"
    for path in (machine, process, filament):
        path.write_text("{}")
    stl = tmp_path / "probe.stl"
    stl.write_bytes(b"solid x\nendsolid x\n")
    cli = OrcaCli.from_settings(settings)
    info = cli.info_precheck(stl)
    assert info.manifold is not None
    run = cli.run_slice(
        machine=machine, process=process, filament=filament, stl=stl, outdir=tmp_path
    )
    assert run.returncode == 0
