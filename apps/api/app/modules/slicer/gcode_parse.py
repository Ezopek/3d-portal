"""Pure g-code metadata parser + duration normalization + parser sink (Story 32.3).

The FR20-ESTIMATE-1 "small unit-testable pure function" half of Decision AJ:
``parse_gcode_metadata`` is a pure ``str -> ParsedEstimate | EstimateParseFailure``
function — no file I/O, no clock, no subprocess. The file read + record assembly +
persistence live in the sink/store/worker (AC-2, AC-5, AC-8), keeping this module
maximally testable and deterministic (AC-12).

A missing/garbled REQUIRED metadata line classifies a typed :class:`EstimateParseFailure`
(``missing_metadata_line`` / ``unparseable_time`` / ``unparseable_numeric``), NEVER a
silent zero (FR20-ESTIMATE-1 / FR20-FAILURE-1 parse half, AC-4).

[Source: architecture.md § Decision AJ; consumes the Story 32.2 temp g-code via the
``GcodeSink`` seam; feeds the Story 32.4 / 32.6 ``EstimateRecord``]
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

from pydantic import BaseModel

from app.modules.slicer.models import EstimateFailureReason

logger = logging.getLogger(__name__)

# Time-unit multipliers for the d/h/m/s grammar of Orca's `estimated printing time`
# line, because "they are the time-format contract of that line — 1d=86400, 1h=3600,
# 1m=60, 1s=1 seconds — not arbitrary" (AC-11).
_SECONDS_PER_DAY = 86400
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_MINUTE = 60
_SECONDS_PER_SECOND = 1

# OrcaSlicer duration grammar: optional d/h/m/s tokens, each a run of digits followed by
# its unit (e.g. `3h35m47s`, `6h 54m 23s`, `35m47s`, `47s`, `1d2h3m4s`). Real Orca
# 2.3.2 inserts spaces between tokens in production g-code, while older synthetic
# fixtures used the compact form; both are the same duration contract. Every token is
# optional, so an all-empty match (or any leftover chars) is rejected as garbled below.
_DURATION_RE = re.compile(r"^(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?$")


def parse_duration_to_seconds(value: str) -> int | None:
    """Normalize an Orca duration string (``3h35m47s``) to whole seconds (AC-3).

    Returns ``None`` for an empty / token-less / garbled value so the caller classifies a
    typed ``unparseable_time`` (AC-4), never a plausible-but-wrong zero-second print.
    """
    value = value.strip()
    if not value:
        return None
    match = _DURATION_RE.fullmatch(value)
    if match is None:
        return None
    days, hours, minutes, seconds = match.groups()
    if days is None and hours is None and minutes is None and seconds is None:
        # Matched only because every token is optional (e.g. a bare number) — not a duration.
        return None
    return (
        int(days or 0) * _SECONDS_PER_DAY
        + int(hours or 0) * _SECONDS_PER_HOUR
        + int(minutes or 0) * _SECONDS_PER_MINUTE
        + int(seconds or 0) * _SECONDS_PER_SECOND
    )


# Each metadata key token below is "the proven OrcaSlicer 2.3.2 g-code metadata footer
# field name (PRD § Init 20 feasibility); the parser's contract IS the real Orca output,
# confirmed against the Story 32.2 in-container PLA/TPU slice g-code" (AC-11). Matching is
# key-anchored to a comment line (`^\s*;\s*<key>\s*=\s*<value>`) + separator-tolerant, so
# it does not depend on line ordering or on g-code body content (only the comment footer).
def _value_re(key_pattern: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*;\s*{key_pattern}\s*=\s*([^\n]*?)\s*$", re.MULTILINE)


# Print time — prefer the `(normal mode)` line; never the `(silent mode)` sibling. The
# bare fallback only matches when `=` follows the key directly, so it can never grab the
# silent-mode line (its `(silent mode)` breaks the `time =` adjacency).
_TIME_NORMAL_RE = _value_re(r"estimated printing time \(normal mode\)")
_TIME_BARE_RE = _value_re(r"estimated printing time")
_FILAMENT_MM_RE = _value_re(r"filament used \[mm\]")
_FILAMENT_CM3_RE = _value_re(r"filament used \[cm3\]")
_FILAMENT_G_RE = _value_re(r"filament used \[g\]")
_FILAMENT_COST_RE = _value_re(r"total filament cost")

# The three attribution lines (NFR20-ATTRIBUTION-1). `print_settings_id` cannot collide
# with `printer_settings_id`: "printer" diverges from "print_" at the 6th char, and the
# value regex anchors on `<key>\s*=`, so each key matches only its own line.
_SETTINGS_ID_KEYS = ("filament_settings_id", "print_settings_id", "printer_settings_id")
_SETTINGS_ID_RES = {key: _value_re(key) for key in _SETTINGS_ID_KEYS}


class ParsedEstimate(BaseModel):
    """The numeric + attribution fields a clean parse yields (AC-2).

    Carries NO key context (``stl_hash``/``bundle_hash``/``orca_version``) and NO
    timestamp — the caller adds the key, status, warnings and clock-stamped
    ``computed_at`` when it assembles the ``EstimateRecord`` (AC-8). That keeps the parser
    a pure text→struct function (AC-12).
    """

    time_seconds: int
    filament_mm: float
    filament_cm3: float
    filament_g: float
    # cost is informational + may be absent without a configured spool price (AC-4/AC-11).
    filament_cost: float | None = None
    settings_ids: dict[str, str]


class EstimateParseFailure(BaseModel):
    """A classified g-code-metadata parse failure (AC-4) — never a silent zero."""

    reason: EstimateFailureReason
    detail: str


def _search(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match is not None else None


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_gcode_metadata(gcode_text: str) -> ParsedEstimate | EstimateParseFailure:
    """Parse the Orca metadata footer to typed fields, or a classified failure (AC-2/AC-4).

    Required-vs-optional split (AC-4/AC-11): time + filament mm/cm3/g are FATAL when
    absent (they are the FR20-ESTIMATE-1 load-bearing numerics); ``total filament cost``
    and the ``settings_ids`` are NON-FATAL — cost is informational and may be absent
    without a spool price, and missing attribution degrades traceability but leaves the
    numbers valid. So absence of an optional field records it as absent, never fails.
    """
    # --- print time (required) ------------------------------------------------------
    raw_time = _search(gcode_text, _TIME_NORMAL_RE)
    if raw_time is None:
        raw_time = _search(gcode_text, _TIME_BARE_RE)
    if raw_time is None:
        return EstimateParseFailure(
            reason=EstimateFailureReason.missing_metadata_line,
            detail="estimated printing time",
        )
    time_seconds = parse_duration_to_seconds(raw_time)
    if time_seconds is None:
        return EstimateParseFailure(
            reason=EstimateFailureReason.unparseable_time,
            detail=f"estimated printing time = {raw_time!r}",
        )

    # --- filament usage (required, numeric) -----------------------------------------
    numerics: dict[str, float] = {}
    for label, pattern in (
        ("filament used [mm]", _FILAMENT_MM_RE),
        ("filament used [cm3]", _FILAMENT_CM3_RE),
        ("filament used [g]", _FILAMENT_G_RE),
    ):
        raw = _search(gcode_text, pattern)
        if raw is None:
            return EstimateParseFailure(
                reason=EstimateFailureReason.missing_metadata_line, detail=label
            )
        try:
            value = float(raw)
        except ValueError:
            return EstimateParseFailure(
                reason=EstimateFailureReason.unparseable_numeric,
                detail=f"{label} = {raw!r}",
            )
        # ``float()`` happily parses 'nan'/'inf'/'-inf' — but a non-finite required
        # numeric is a plausible-but-wrong estimate (nan poisons arithmetic, inf prints
        # forever), so it is classified unparseable_numeric, never a fresh number
        # (review-fix #1 — same no-silent-zero contract as a non-numeric value).
        if not math.isfinite(value):
            return EstimateParseFailure(
                reason=EstimateFailureReason.unparseable_numeric,
                detail=f"{label} = {raw!r}",
            )
        numerics[label] = value

    # --- cost (optional, informational) ---------------------------------------------
    raw_cost = _search(gcode_text, _FILAMENT_COST_RE)
    filament_cost: float | None = None
    if raw_cost is not None:
        try:
            parsed_cost = float(raw_cost)
        except ValueError:
            # Cost is non-fatal — an unparseable cost degrades to absent, the numbers
            # (which ARE load-bearing) stay valid (AC-4).
            parsed_cost = None
        else:
            # A non-finite cost is "present but garbage" — degrade it to absent (the same
            # optional-field rule as a missing cost line), never persist nan/inf as a
            # fresh cost (review-fix #1). The load-bearing numerics are unaffected.
            if not math.isfinite(parsed_cost):
                logger.warning(
                    "slicer.gcode_parse: non-finite filament cost degraded to None",
                    extra={"labels.estimate_cost_raw": repr(raw_cost)},
                )
                parsed_cost = None
        filament_cost = parsed_cost

    # --- attribution (optional, degrades) -------------------------------------------
    settings_ids: dict[str, str] = {}
    for key, pattern in _SETTINGS_ID_RES.items():
        raw = _search(gcode_text, pattern)
        if raw is not None:
            settings_ids[key] = _strip_quotes(raw)

    return ParsedEstimate(
        time_seconds=time_seconds,
        filament_mm=numerics["filament used [mm]"],
        filament_cm3=numerics["filament used [cm3]"],
        filament_g=numerics["filament used [g]"],
        filament_cost=filament_cost,
        settings_ids=settings_ids,
    )


class ParsingGcodeSink:
    """Per-job, stateful ``GcodeSink`` that parses the temp g-code IN-job (AC-8).

    Honors the Story 32.2 seam (``GcodeSink = Callable[[Path], None]``): ``__call__`` reads
    the temp g-code WHILE it is still alive (the 32.2 scratch-dir context manager deletes
    it at block exit — OD-5 parse-and-discard, zero durable retention) and stashes ONLY
    the typed parse result. It keeps neither the path nor the raw g-code text, so nothing
    g-code-shaped crosses the job boundary — only ``self.result``.
    """

    def __init__(self) -> None:
        self.result: ParsedEstimate | EstimateParseFailure | None = None

    def __call__(self, gcode_path: Path) -> None:
        text = gcode_path.read_text(encoding="utf-8", errors="ignore")
        self.result = parse_gcode_metadata(text)
