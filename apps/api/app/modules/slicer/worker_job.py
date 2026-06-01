"""Slice job orchestration + outcome classification (Story 32.2, Decision AI).

The ``slice_estimate`` arq task orchestrates one idempotent ``(stl_hash, bundle_hash)``
slice:

    load bundle → locate STL → ``--info`` manifold pre-check → headless slice →
    classify → hand temp g-code to the (Story 32.3) parser sink → discard temp g-code

Every outcome is a typed :class:`SliceOutcome` (FR20-FAILURE-1, AC-6) — never a bare
``None``/0 a caller could misread as a valid estimate. g-code is written to a
context-managed scratch dir and DELETED at job end on success OR failure (OD-5
parse-and-discard, AC-5); no g-code survives in any durable store, log, or volume.

[Source: architecture.md § Decision AI; consumed by Story 32.3 (g-code + SliceOutcome)]
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sentry_sdk
from opentelemetry import trace

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.cli import OrcaCli, is_profile_rejection, parse_slice_warnings
from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.gcode_parse import EstimateParseFailure, ParsedEstimate, ParsingGcodeSink
from app.modules.slicer.models import (
    EstimateRecord,
    EstimateStatus,
    SliceFailureReason,
    SliceOutcome,
    SliceStatus,
    SliceWarning,
)
from app.modules.slicer.stl_cache import StlCache, is_content_hash

#: arq task name — the function name the dedicated slicer queue dispatches (AC-2).
SLICE_JOB_NAME = "slice_estimate"

# The g-code Orca emits under --outputdir. parse-and-discard means we only ever
# discover it for the in-job parser hand-off (Story 32.3), never retain it.
_GCODE_GLOB = "*.gcode"

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)

# A g-code sink consumes the temp g-code path within the job (the Story 32.3 parser
# hand-off seam). Default is a no-op discard so 32.3 slots in without reshaping this
# module (AC-5).
GcodeSink = Callable[[Path], None]


def discard_sink(gcode_path: Path) -> None:
    """Default no-op g-code sink — parse-and-discard (OD-5). Story 32.3 replaces it."""
    return None


def _materialize_triple(bundle, scratch: Path) -> tuple[Path, Path, Path]:
    """Write the resolved triple JSONs to temp files for ``--load-*`` (AC-3)."""
    machine = scratch / "machine.json"
    process = scratch / "process.json"
    filament = scratch / "filament.json"
    machine.write_text(json.dumps(bundle.machine))
    process.write_text(json.dumps(bundle.process))
    filament.write_text(json.dumps(bundle.filament))
    return machine, process, filament


def _find_gcode(outdir: Path) -> Path | None:
    matches = sorted(outdir.glob(_GCODE_GLOB))
    return matches[0] if matches else None


def _classify(
    *,
    stl_hash: str,
    bundle_hash: str,
    stl_cache: StlCache,
    bundle_store: BundleStore,
    cli: OrcaCli,
    sink: GcodeSink,
) -> SliceOutcome:
    """Run the slice pipeline and return the classified outcome (no timing/identity)."""
    # (1) bundle — a miss is an integrity fault (the resolver should have persisted
    # it), never a silent default (AC-4). Guard the bundle_hash BEFORE it reaches
    # bundle_store path construction so a malformed/traversal hash cannot escape the
    # store root (review fix #2); a malformed hash is, from the worker's view, an
    # unaddressable bundle ⇒ missing_bundle.
    if not is_content_hash(bundle_hash):
        return SliceOutcome(status=SliceStatus.failed, reason=SliceFailureReason.missing_bundle)
    bundle = bundle_store.load_bundle(bundle_hash)
    if bundle is None:
        return SliceOutcome(status=SliceStatus.failed, reason=SliceFailureReason.missing_bundle)

    # (2) STL from the content-hash cache — a miss ⇒ missing_stl (AC-4). read_path
    # itself rejects a malformed stl_hash (returns None WITHOUT building a path), so a
    # genuine miss AND a traversal-shaped hash both classify missing_stl (review fix #2).
    stl_path = stl_cache.read_path(stl_hash)
    if stl_path is None:
        return SliceOutcome(status=SliceStatus.failed, reason=SliceFailureReason.missing_stl)

    # (3) --info manifold pre-check BEFORE the slice (AC-3). manifold:no ⇒ fast-fail
    # WITHOUT attempting the minutes-long slice on a known-bad mesh.
    try:
        info = cli.info_precheck(stl_path)
    except subprocess.TimeoutExpired:
        return SliceOutcome(status=SliceStatus.failed, reason=SliceFailureReason.timeout)
    except OSError:
        # Orca itself could not be launched (bad entrypoint / perms) — classify a
        # typed launch_error rather than letting it surface as an uncaught arq
        # exception (review fix #3). No slice is attempted.
        return SliceOutcome(status=SliceStatus.failed, reason=SliceFailureReason.launch_error)
    # A non-zero --info exit means its manifold verdict is unreliable; do NOT run the
    # full slice on its say-so (review fix #4). Checked before the manifold verdict so
    # a failed precheck is never silently read as "manifold: <whatever>".
    if info.returncode != 0:
        return SliceOutcome(
            status=SliceStatus.failed,
            reason=SliceFailureReason.info_precheck_failed,
            manifold=info.manifold,
        )
    if info.manifold is False:
        return SliceOutcome(
            status=SliceStatus.failed, reason=SliceFailureReason.non_manifold, manifold=False
        )

    # (4) slice into a context-managed scratch dir; g-code discarded on block exit
    # (AC-5 parse-and-discard) regardless of success/failure.
    with tempfile.TemporaryDirectory(prefix="portal-slice-") as scratch:
        scratch_dir = Path(scratch)
        machine, process, filament = _materialize_triple(bundle, scratch_dir)
        try:
            run = cli.run_slice(
                machine=machine,
                process=process,
                filament=filament,
                stl=stl_path,
                outdir=scratch_dir,
            )
        except subprocess.TimeoutExpired:
            return SliceOutcome(
                status=SliceStatus.failed,
                reason=SliceFailureReason.timeout,
                manifold=info.manifold,
            )
        except OSError:
            # Orca could not be launched for the slice pass (review fix #3).
            return SliceOutcome(
                status=SliceStatus.failed,
                reason=SliceFailureReason.launch_error,
                manifold=info.manifold,
            )

        if run.returncode != 0:
            # cli_rejected_profile is defense-in-depth (should be caught at 32.1
            # resolve-time validation); everything else is a generic non_zero_exit.
            reason = (
                SliceFailureReason.cli_rejected_profile
                if is_profile_rejection(run.stderr)
                else SliceFailureReason.non_zero_exit
            )
            return SliceOutcome(status=SliceStatus.failed, reason=reason, manifold=info.manifold)

        # exit 0 but NO g-code ⇒ there is no parser input. Returning ok/warning here
        # would be a plausible-but-wrong silent zero downstream (FR20-FAILURE-1) — so
        # classify a typed missing_gcode failure instead (review fix #1, BLOCKER). The
        # scratch dir (and any partial g-code) is still discarded at block exit (AC-5).
        gcode = _find_gcode(scratch_dir)
        if gcode is None:
            return SliceOutcome(
                status=SliceStatus.failed,
                reason=SliceFailureReason.missing_gcode,
                manifold=info.manifold,
            )

        # success: hand the temp g-code to the parser sink (Story 32.3), then discard.
        sink(gcode)
        warnings = [SliceWarning(message=m) for m in parse_slice_warnings(run.stdout, run.stderr)]
        status = SliceStatus.warning if warnings else SliceStatus.ok
        return SliceOutcome(
            status=status,
            warnings=warnings,
            manifold=info.manifold,
            gcode_temp_ref=str(gcode),
        )


def run_slice_job(
    *,
    stl_hash: str,
    bundle_hash: str,
    stl_cache: StlCache,
    bundle_store: BundleStore,
    cli: OrcaCli,
    orca_version: str,
    gcode_sink: GcodeSink | None = None,
) -> SliceOutcome:
    """Run one slice job and return the classified, instrumented :class:`SliceOutcome`.

    Pure under the injected mock runner (no clock/random in the classification path),
    so the determinism gate (AC-11) holds; ``slice_wall_ms`` is the only non-pure
    field and is observability-only (excluded from assertions).
    """
    sink = gcode_sink or discard_sink
    logger.info(
        "slicer.slice start",
        extra={
            "labels.stl_hash": stl_hash,
            "labels.bundle_hash": bundle_hash,
            "labels.orca_version": orca_version,
        },
    )
    start = time.perf_counter()
    with _tracer.start_as_current_span("slicer.slice") as span:
        span.set_attribute("slicer.stl_hash", stl_hash)
        span.set_attribute("slicer.bundle_hash", bundle_hash)
        span.set_attribute("slicer.orca_version", orca_version)

        outcome = _classify(
            stl_hash=stl_hash,
            bundle_hash=bundle_hash,
            stl_cache=stl_cache,
            bundle_store=bundle_store,
            cli=cli,
            sink=sink,
        )
        outcome = outcome.model_copy(
            update={
                "slice_wall_ms": int((time.perf_counter() - start) * 1000),
                "stl_hash": stl_hash,
                "bundle_hash": bundle_hash,
                "orca_version": orca_version,
            }
        )

        span.set_attribute("slicer.status", outcome.status.value)
        span.set_attribute("slicer.warning_count", len(outcome.warnings))
        if outcome.manifold is not None:
            span.set_attribute("slicer.manifold", outcome.manifold)
        if outcome.reason is not None:
            span.set_attribute("slicer.failure_reason", outcome.reason.value)

        _emit_completion(outcome)
        if outcome.status == SliceStatus.failed:
            sentry_sdk.add_breadcrumb(
                category="slicer",
                level="error",
                message="slice failed",
                data={
                    "stl_hash": outcome.stl_hash,
                    "bundle_hash": outcome.bundle_hash,
                    "failure_reason": outcome.reason.value if outcome.reason else None,
                },
            )
    return outcome


def _emit_completion(outcome: SliceOutcome) -> None:
    """One structured completion line per job (NFR20-OBS-1, AC-8).

    Carries the contract tags; g-code is parse-and-discard and is NEVER logged in
    full (it is large + derivable) — only the warning COUNT and the hashes appear.
    """
    extra: dict[str, Any] = {
        "labels.stl_hash": outcome.stl_hash,
        "labels.bundle_hash": outcome.bundle_hash,
        "labels.status": outcome.status.value,
        "labels.orca_version": outcome.orca_version,
        "labels.slice_wall_ms": outcome.slice_wall_ms,
        "labels.warning_count": len(outcome.warnings),
    }
    if outcome.manifold is not None:
        extra["labels.manifold"] = outcome.manifold
    if outcome.reason is not None:
        extra["labels.failure_reason"] = outcome.reason.value
    logger.info("slicer.slice complete", extra=extra)


def _assemble_estimate_record(
    outcome: SliceOutcome,
    parse_result: ParsedEstimate | EstimateParseFailure | None,
) -> EstimateRecord | None:
    """Map a (SliceOutcome, parse result) pair to the EstimateRecord to persist (AC-8).

    - slice-INVOCATION failure (``status == failed``) ⇒ ``None``: the failure is fully
      described by ``SliceOutcome``; persisting an invocation-failure estimate is Story
      32.4's recompute-state concern, NOT 32.3's parse half (the explicit boundary);
    - a clean parse (``ParsedEstimate``) ⇒ a ``fresh`` record carrying the numerics +
      cost-carry + attribution + the warnings verbatim from the outcome;
    - a classified parse failure (``EstimateParseFailure``) ⇒ a ``failed`` record with
      ``reason`` and numeric fields left ``None`` (never a silent zero, AC-4).
    """
    if outcome.status == SliceStatus.failed:
        return None
    key = dict(
        stl_hash=outcome.stl_hash,
        bundle_hash=outcome.bundle_hash,
        orca_version=outcome.orca_version,
        warnings=outcome.warnings,
        computed_at=_now_iso(),
    )
    if isinstance(parse_result, ParsedEstimate):
        return EstimateRecord(
            status=EstimateStatus.fresh,
            time_seconds=parse_result.time_seconds,
            filament_mm=parse_result.filament_mm,
            filament_cm3=parse_result.filament_cm3,
            filament_g=parse_result.filament_g,
            filament_cost=parse_result.filament_cost,
            settings_ids=parse_result.settings_ids,
            **key,
        )
    if isinstance(parse_result, EstimateParseFailure):
        return EstimateRecord(status=EstimateStatus.failed, reason=parse_result.reason, **key)
    return None


def _now_iso() -> str:
    """ISO-8601 UTC provenance stamp for ``computed_at`` — the ONLY non-deterministic field.

    Excluded from content-identity / dedup (AC-6) and from determinism assertions (AC-12).
    """
    return datetime.now(UTC).isoformat()


def _emit_estimate_persist(record: EstimateRecord) -> None:
    """One structured line per estimate persist (NFR20-OBS-1, AC-10).

    g-code is parse-and-discard and is NEVER logged in full — only the hashes, status,
    orca_version and (on failure) the reason cross into logs. A parse ``failed`` also drops
    a GlitchTip breadcrumb (no g-code body).
    """
    extra: dict[str, Any] = {
        "labels.stl_hash": record.stl_hash,
        "labels.bundle_hash": record.bundle_hash,
        "labels.estimate_status": record.status.value,
        "labels.orca_version": record.orca_version,
    }
    if record.reason is not None:
        extra["labels.estimate_failure_reason"] = record.reason.value
    logger.info("slicer.estimate persist", extra=extra)
    if record.status == EstimateStatus.failed:
        sentry_sdk.add_breadcrumb(
            category="slicer",
            level="error",
            message="estimate parse failed",
            data={
                "stl_hash": record.stl_hash,
                "bundle_hash": record.bundle_hash,
                "reason": record.reason.value if record.reason else None,
            },
        )


async def slice_estimate(ctx: dict[str, Any], stl_hash: str, bundle_hash: str) -> dict[str, Any]:
    """arq task entry point (AC-1/AC-8). Pulls injected deps from ``ctx`` (startup-wired).

    The 2-tuple ``(stl_hash, bundle_hash)`` is the ENTIRE payload (AC-2): the worker
    pulls the STL from the cache and the resolved triple from the bundle store; no
    profile JSON, STL bytes, or file paths travel in the payload.

    Story 32.3 slots the parser sink into the Story 32.2 seam WITHOUT reshaping the slice
    orchestration: a fresh per-job :class:`ParsingGcodeSink` parses the temp g-code in-job,
    then — AFTER ``run_slice_job`` returns — the parsed result is assembled into a typed
    ``EstimateRecord`` and persisted (subject to the AC-6 dedup). ``_classify`` and
    ``run_slice_job`` are untouched.
    """
    sink = ParsingGcodeSink()
    outcome = run_slice_job(
        stl_hash=stl_hash,
        bundle_hash=bundle_hash,
        stl_cache=ctx["stl_cache"],
        bundle_store=ctx["bundle_store"],
        cli=ctx["cli"],
        orca_version=ctx["orca_version"],
        gcode_sink=sink,
    )
    estimate_store: EstimateStore | None = ctx.get("estimate_store")
    if estimate_store is not None:
        record = _assemble_estimate_record(outcome, sink.result)
        if record is not None:
            # The persist runs AFTER run_slice_job's slice span has closed, so it carries
            # its own span — completing the AC-10 "structured-log + OTel span + breadcrumb"
            # triad (mirroring run_slice_job's slicer.slice span). g-code body never crosses
            # into a span attribute (parse-and-discard) — only hashes/status/reason.
            with _tracer.start_as_current_span("slicer.estimate") as span:
                span.set_attribute("slicer.stl_hash", record.stl_hash)
                span.set_attribute("slicer.bundle_hash", record.bundle_hash)
                span.set_attribute("slicer.orca_version", record.orca_version)
                span.set_attribute("slicer.estimate_status", record.status.value)
                if record.reason is not None:
                    span.set_attribute("slicer.estimate_failure_reason", record.reason.value)
                estimate_store.write(record)
                _emit_estimate_persist(record)
    return outcome.model_dump(mode="json")
