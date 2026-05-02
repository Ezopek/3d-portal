"""Tests for render_report."""
from datetime import datetime, timezone

from migrate_catalog_3mf import (
    render_report,
    ExecutionResult,
    Plan,
    WrapInFolder,
    Convert3mf,
)


def _now():
    return datetime(2026, 5, 2, 3, 0, 0, tzinfo=timezone.utc)


def test_report_includes_summary_and_counts(tmp_path):
    actions = [
        WrapInFolder(
            file=tmp_path / "decorum" / "x.stl",
            folder=tmp_path / "decorum" / "x",
        )
    ]
    plan = Plan(actions=actions, index_after=[], validations=[])
    result = ExecutionResult(completed=actions, failed=[], skipped=[])
    md = render_report(result, plan, _now(), _now())
    assert "## Summary" in md
    assert "1 action" in md
    assert "0 failed" in md
    assert "Exit code:" in md


def test_report_lists_failed_actions(tmp_path):
    a = Convert3mf(src=tmp_path / "decorum" / "y" / "y.3mf")
    plan = Plan(actions=[a], index_after=[], validations=[])
    result = ExecutionResult(
        completed=[],
        failed=[(a, "ConversionError: bad data")],
        skipped=[],
    )
    md = render_report(result, plan, _now(), _now())
    assert "## Conversions (failed — manual review)" in md
    assert "ConversionError: bad data" in md


def test_report_dry_run_shows_skipped(tmp_path):
    a = WrapInFolder(
        file=tmp_path / "decorum" / "x.stl",
        folder=tmp_path / "decorum" / "x",
    )
    plan = Plan(actions=[a], index_after=[], validations=[])
    result = ExecutionResult(completed=[], failed=[], skipped=[a])
    md = render_report(result, plan, _now(), _now())
    assert "DRY RUN" in md or "skipped" in md.lower()
