"""Tests for the pre-migration Data Quality Report script."""

from scripts.data_quality_report import build_report


def test_empty_records_message():
    out = build_report([])
    assert "_No records in index.json._" in out


def test_informational_counters():
    records = [
        {"id": "001", "name_en": "A", "source": "unknown"},
        {"id": "002", "name_en": "B", "source": "printables", "notes": "hello"},
    ]
    out = build_report(records)
    assert "**Total models:** 2" in out
    # Both lack source_url; both lack rating; second has notes; first has none
    assert "## Informational" in out
    assert "1/2 models without `notes`" in out
    assert "1/2 models without `source` (or `source=unknown`)" in out


def test_name_language_mismatch_section():
    records = [
        {"id": "001", "name_en": "Dragon"},  # missing name_pl
        {"id": "002", "name_pl": "Smok"},  # missing name_en
        {"id": "003", "name_en": "Crab", "name_pl": "Krab"},  # both present
    ]
    out = build_report(records)
    assert "Models with `name_en` but no `name_pl` (1)" in out
    assert "001:" in out
    assert "Models with `name_pl` but no `name_en` (1)" in out
    assert "002:" in out


def test_rare_tags_listed():
    records = [
        {"id": "001", "tags": ["dragon", "rare1"]},
        {"id": "002", "tags": ["dragon", "rare2"]},
        {"id": "003", "tags": ["dragon"]},  # dragon used 3x — not rare
    ]
    out = build_report(records)
    assert "Tags used exactly once (2)" in out
    assert "`rare1`" in out
    assert "`rare2`" in out
    # dragon used 3 times — must NOT be in the rare list
    rare_section_start = out.index("Tags used exactly once")
    rare_section_end = out.index("Polish-looking tags")
    assert "`dragon`" not in out[rare_section_start:rare_section_end]


def test_polish_unmapped_tags_detected():
    records = [
        # PL letters present but tag IS in PL_EN map (smok → dragon) — must NOT be flagged
        {"id": "001", "tags": ["smok"]},
        # PL letters present and NOT in PL_EN map — must be flagged
        {"id": "002", "tags": ["nieistniejący-pl-tag"]},
        # No PL letters — never flagged
        {"id": "003", "tags": ["regular-en-tag"]},
    ]
    out = build_report(records)
    assert "Polish-looking tags not in `PL_EN` map (1)" in out
    assert "`nieistniejący-pl-tag`" in out
    assert "`smok`" not in out.split("Polish-looking")[1]
    assert "`regular-en-tag`" not in out.split("Polish-looking")[1]


def test_full_report_runs_on_realistic_corpus():
    records = [
        {
            "id": "001",
            "name_en": "Dragon",
            "name_pl": "Smok",
            "tags": ["dragon", "smok", "articulated"],
            "source": "printables",
            "source_url": "https://example.com/123",
            "notes": "good print",
            "rating": 4,
            "thumbnail": "iso.png",
            "prints": [{"path": "p1.jpg", "date": "2026-01-01"}],
        },
        {
            "id": "002",
            "name_en": "Crab",
            "tags": ["dragon", "crab"],
            "source": "unknown",
        },
    ]
    out = build_report(records)
    assert out.startswith("# Data Quality Report")
    assert "**Total models:** 2" in out
    assert "## Informational" in out
    assert "## Actionable" in out
