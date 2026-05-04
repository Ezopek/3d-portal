"""Pre-migration Data Quality Report (DQR).

Scans `_index/index.json` and prints a markdown report grouped into:
  * Informational — fields commonly empty for legitimate reasons (no
    `source`, no `notes`, no own images, no rating). Listed for awareness;
    no action expected.
  * Actionable — likely data hygiene issues:
      - models with `name_en` but no `name_pl`, or vice versa
      - tags appearing exactly once (likely typos or merge candidates)
      - tags that look Polish (contain ąćęłńóśźż) but are absent from
        `tag_translations.PL_EN`

The DQR does NOT block migration. Operators read it and decide whether
to clean items by hand (or via the agent in the old workflow) before
cutover, or to import as-is and clean up later through the new API.

Usage:
    python -m scripts.data_quality_report --index <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.tag_translations import PL_EN

_PL_ONLY_LETTERS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def _looks_polish(tag: str) -> bool:
    return any(ch in _PL_ONLY_LETTERS for ch in tag)


def build_report(records: list[dict[str, Any]]) -> str:
    """Build the markdown DQR report for the given index.json records."""
    n = len(records)
    if n == 0:
        return "# Data Quality Report\n\n_No records in index.json._\n"

    # ---------- Informational counters ----------
    no_source = sum(1 for r in records if not r.get("source") or r["source"] == "unknown")
    no_notes = sum(1 for r in records if not (r.get("notes") or "").strip())
    no_source_url = sum(1 for r in records if not r.get("source_url"))
    no_rating = sum(1 for r in records if r.get("rating") is None)
    no_thumbnail = sum(1 for r in records if not r.get("thumbnail"))
    no_prints = sum(1 for r in records if not r.get("prints"))

    # ---------- Actionable: name-language mismatch ----------
    name_only_en: list[str] = []
    name_only_pl: list[str] = []
    for r in records:
        en = (r.get("name_en") or "").strip()
        pl = (r.get("name_pl") or "").strip()
        rid = r.get("id", "?")
        if en and not pl:
            name_only_en.append(f"{rid}: {en!r}")
        elif pl and not en:
            name_only_pl.append(f"{rid}: {pl!r}")

    # ---------- Actionable: rare tags (used exactly once) ----------
    tag_counts: dict[str, int] = {}
    for r in records:
        for t in r.get("tags", []) or []:
            tag_counts[t.lower()] = tag_counts.get(t.lower(), 0) + 1
    rare_tags = sorted([t for t, c in tag_counts.items() if c == 1])

    # ---------- Actionable: PL-looking tags missing from PL_EN ----------
    pl_unmapped = sorted(t for t in tag_counts if _looks_polish(t) and t not in PL_EN)

    out: list[str] = []
    out.append("# Data Quality Report\n")
    out.append(f"**Total models:** {n}\n")

    out.append("## Informational")
    out.append("Fields commonly empty for legitimate reasons. No action required.\n")
    out.append(f"- {no_source}/{n} models without `source` (or `source=unknown`)")
    out.append(f"- {no_source_url}/{n} models without `source_url`")
    out.append(f"- {no_notes}/{n} models without `notes`")
    out.append(f"- {no_rating}/{n} models without `rating`")
    out.append(f"- {no_thumbnail}/{n} models without explicit `thumbnail`")
    out.append(f"- {no_prints}/{n} models with empty `prints[]`")
    out.append("")

    out.append("## Actionable")
    out.append("Items worth a manual review before migration.\n")

    out.append(f"### Models with `name_en` but no `name_pl` ({len(name_only_en)})")
    if name_only_en:
        for line in name_only_en:
            out.append(f"- {line}")
    else:
        out.append("_None._")
    out.append("")

    out.append(f"### Models with `name_pl` but no `name_en` ({len(name_only_pl)})")
    if name_only_pl:
        for line in name_only_pl:
            out.append(f"- {line}")
    else:
        out.append("_None._")
    out.append("")

    out.append(f"### Tags used exactly once ({len(rare_tags)})")
    out.append("These are typo / merge candidates. If they're real concepts, ignore.\n")
    if rare_tags:
        for t in rare_tags:
            out.append(f"- `{t}`")
    else:
        out.append("_None._")
    out.append("")

    out.append(f"### Polish-looking tags not in `PL_EN` map ({len(pl_unmapped)})")
    out.append(
        "Extend `scripts/tag_translations.py` to dedupe these into "
        "their EN counterparts during migration.\n"
    )
    if pl_unmapped:
        for t in pl_unmapped:
            out.append(f"- `{t}`")
    else:
        out.append("_None._")
    out.append("")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--index",
        type=Path,
        required=True,
        help="Path to _index/index.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output markdown path (default: stdout)",
    )
    args = p.parse_args(argv)

    if not args.index.is_file():
        print(f"index.json not found: {args.index}", file=sys.stderr)
        return 2

    records = json.loads(args.index.read_text(encoding="utf-8"))
    report = build_report(records)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
