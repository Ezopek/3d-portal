"""Orca command builder + subprocess invoke layer (Story 32.2, AC-3/AC-7, Decision AI).

This is the real invocation contract Story 32.1 only *specified* as
``ORCA_SMOKE_COMMAND_TEMPLATE`` / ``build_orca_smoke_command``:

* a cheap ``--info`` manifold pre-check argv over the STL,
* a headless slice argv built by EXTENDING the Story 32.1
  :func:`validation.build_orca_load_flags` shape (single source of truth — no
  divergent argv re-implementation),
* a timeout-bounded subprocess runner that terminates the whole process group on
  wall-time expiry (AC-7).

The Orca entrypoint is read from a settings slot (``slicer_orca_bin``), NEVER a
literal (NFR20-CONTAINER-1). Real Orca is NOT executed in CI — the runner is an
injectable seam (:class:`SubprocessRunner` in production, a fake in the unit suite).
Classification of the outcome into a ``SliceOutcome`` lives in ``worker_job.py``
(AC-6); this module only builds argv, runs, and parses Orca output.
"""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.modules.slicer.validation import build_orca_load_flags

# --info flag: the cheap pre-check pass that reports mesh stats — because "the proven
# bench `--info` output reports manifold yes/no + facet count + volume, gating the
# fast-fail before a full slice (Decision AI § Failure classification)".
_INFO_FLAG = "--info"

# Headless slice flags. ``--slice 0`` slices all plates; g-code is emitted under
# ``--outputdir``. The EXACT slice flag set is verified out-of-band on the configs-
# side container (AC-12 R3 spike) — because "CI has no AppImage; the argv shape
# extends the Story 32.1 build_orca_load_flags single source, the real flag set is
# bench-confirmed on the slicer-worker container".
_SLICE_FLAG = "--slice"
_SLICE_ALL_PLATES = "0"
_OUTPUTDIR_FLAG = "--outputdir"

# Orca `--info` manifold field parse — because "the proven bench `--info` output
# field gating the fast-fail before a full slice — Decision AI § Failure
# classification; brainstorm § 'Validation pre-check'" (AC-10). Tolerates
# ``manifold: yes`` / ``manifold = no`` / ``manifold yes`` shapes case-insensitively.
_MANIFOLD_RE = re.compile(r"manifold\s*[:=]?\s*(yes|no|true|false|1|0)\b", re.IGNORECASE)
_MANIFOLD_TRUE = frozenset({"yes", "true", "1"})

# A slice stdout/stderr line carrying this token is a non-blocking Orca warning
# (e.g. floating cantilever) — the g-code is still valid (AC-6 warning path).
_WARNING_MARKER = "warning"

# Stderr signatures that mean Orca rejected the resolved triple at LOAD time, vs a
# generic non-zero slice exit — because "cli_rejected_profile should already be
# caught at Story 32.1 resolve-time validation (Decision AH § 5); re-classified here
# as defense-in-depth" (AC-6).
#
# NOTE (review fix #5): the broad ``"invalid"`` / ``"reject"`` markers can in theory
# over-match a non-load-time slice error whose stderr happens to contain those words;
# narrowing them safely needs the REAL Orca load-rejection stderr signatures, which CI
# cannot observe (no AppImage). Deferred to the AC-12 configs-side Orca-in-container
# smoke (ORCA_SMOKE_TEST) to capture the real markers before tightening. The
# mis-classification blast radius is bounded: either way the outcome is a typed
# ``failed`` (cli_rejected_profile vs non_zero_exit), never a silent zero.
_PROFILE_REJECT_MARKERS = (
    "failed to load",
    "could not parse",
    "load-settings",
    "load-filaments",
    "invalid",
    "reject",
)


@dataclass(frozen=True)
class RunnerResult:
    """What a runner returns for a completed (non-timed-out) invocation."""

    returncode: int
    stdout: str
    stderr: str


# A runner takes (argv, wall_time_seconds) and returns a RunnerResult, or raises
# ``subprocess.TimeoutExpired`` if the wall-time budget is exceeded (AC-7).
Runner = Callable[[list[str], float], RunnerResult]


@dataclass(frozen=True)
class InfoResult:
    """Parsed outcome of the ``--info`` pre-check."""

    manifold: bool | None
    returncode: int
    raw: str


@dataclass(frozen=True)
class SliceRun:
    """Raw outcome of a completed slice invocation (classified by worker_job)."""

    returncode: int
    stdout: str
    stderr: str


class SubprocessRunner:
    """Default production runner: a real subprocess bounded by a wall-time timeout.

    The child is started in its OWN session/process group (``start_new_session``)
    so that on timeout the ENTIRE group is killed — Orca may fork helper processes,
    and killing only the parent would leak them and defeat the wall-time bound
    (AC-7 / NFR20-RESOURCE-1). On timeout ``subprocess.TimeoutExpired`` propagates so
    the worker classifies the outcome ``timeout``.
    """

    def __call__(self, argv: list[str], timeout_s: float) -> RunnerResult:
        # argv is fixed flags + content-addressed paths (no user-interpolated input).
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            with contextlib.suppress(Exception):
                proc.communicate(timeout=5)
            raise
        return RunnerResult(returncode=proc.returncode, stdout=stdout or "", stderr=stderr or "")


def build_info_command(orca_bin: str, stl: Path) -> list[str]:
    """The cheap ``--info`` manifold pre-check argv over the STL (AC-3)."""
    return [orca_bin, _INFO_FLAG, str(stl)]


def build_slice_command(
    orca_bin: str, machine: Path, process: Path, filament: Path, stl: Path, outdir: Path
) -> list[str]:
    """The headless slice argv (AC-3), reusing the Story 32.1 load-flag shape.

    ``orca_bin`` is the settings-sourced entrypoint (never a literal). The
    ``--load-*`` segment is :func:`validation.build_orca_load_flags` verbatim so the
    profile-loading shape stays single-source with the 32.1 smoke command.
    """
    return [
        orca_bin,
        *build_orca_load_flags(machine, process, filament),
        _SLICE_FLAG,
        _SLICE_ALL_PLATES,
        _OUTPUTDIR_FLAG,
        str(outdir),
        str(stl),
    ]


def parse_info_manifold(text: str) -> bool | None:
    """Parse the ``--info`` output for the manifold verdict.

    Returns ``True``/``False`` when the field is present, ``None`` when absent (an
    unparseable ``--info`` is NOT treated as manifold — the worker proceeds to the
    slice, which will fail-loud if the mesh is bad rather than fast-failing on a
    parse gap).
    """
    match = _MANIFOLD_RE.search(text or "")
    if match is None:
        return None
    return match.group(1).lower() in _MANIFOLD_TRUE


def parse_slice_warnings(stdout: str, stderr: str) -> list[str]:
    """Collect non-blocking Orca warning lines from the slice output (AC-6)."""
    warnings: list[str] = []
    for stream in (stdout, stderr):
        for line in (stream or "").splitlines():
            if _WARNING_MARKER in line.lower():
                warnings.append(line.strip())
    return warnings


def is_profile_rejection(stderr: str) -> bool:
    """True if the slice stderr looks like an Orca profile-LOAD rejection (AC-6)."""
    low = (stderr or "").lower()
    return any(marker in low for marker in _PROFILE_REJECT_MARKERS)


class OrcaCli:
    """Settings-wired Orca invoker: ``--info`` pre-check + headless slice."""

    def __init__(
        self,
        *,
        orca_bin: str,
        runner: Runner,
        info_timeout_s: float,
        slice_timeout_s: float,
    ) -> None:
        self.orca_bin = orca_bin
        self._runner = runner
        self.info_timeout_s = info_timeout_s
        self.slice_timeout_s = slice_timeout_s

    @classmethod
    def from_settings(cls, settings, runner: Runner | None = None) -> OrcaCli:
        """Build from ``Settings`` — the entrypoint + both timeouts come from slots."""
        return cls(
            orca_bin=settings.slicer_orca_bin,
            runner=runner or SubprocessRunner(),
            info_timeout_s=settings.slicer_info_timeout_seconds,
            slice_timeout_s=settings.slicer_slice_timeout_seconds,
        )

    def info_precheck(self, stl: Path) -> InfoResult:
        """Run the cheap ``--info`` pass; raises ``subprocess.TimeoutExpired`` on overrun."""
        argv = build_info_command(self.orca_bin, stl)
        result = self._runner(argv, self.info_timeout_s)
        manifold = parse_info_manifold(f"{result.stdout}\n{result.stderr}")
        return InfoResult(manifold=manifold, returncode=result.returncode, raw=result.stdout)

    def run_slice(
        self, *, machine: Path, process: Path, filament: Path, stl: Path, outdir: Path
    ) -> SliceRun:
        """Run the headless slice; raises ``subprocess.TimeoutExpired`` on overrun."""
        argv = build_slice_command(self.orca_bin, machine, process, filament, stl, outdir)
        result = self._runner(argv, self.slice_timeout_s)
        return SliceRun(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
