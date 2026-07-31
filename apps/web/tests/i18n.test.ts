import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

function flat(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const full = prefix ? `${prefix}.${k}` : k;
    return typeof v === "object" && v !== null
      ? flat(v as Record<string, unknown>, full)
      : [full];
  });
}

describe("i18n key parity", () => {
  it("en and pl have identical key sets", () => {
    const enKeys = new Set(flat(en));
    const plKeys = new Set(flat(pl));
    expect([...enKeys].filter((k) => !plKeys.has(k))).toEqual([]);
    expect([...plKeys].filter((k) => !enKeys.has(k))).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Story 54.1 — Initiative 26 cross-surface i18n audit (NFR26-I18N-1)
//
// The parity check above is repo-wide and predates this story. What it cannot
// see is content: a key can exist in both files and still carry untranslated
// English, a placeholder, or a broken interpolation. The checks below close
// that gap for the Initiative 26 key space and ONLY for it. Scoping is
// deliberate (D-2): extending them repo-wide would assert an audit of all 1048
// keys that nobody performed. The key space is § 3 of
// `_bmad-output/implementation-artifacts/54-1-i18n-parity-audit.md`.
// ---------------------------------------------------------------------------

const enValues = en as Record<string, string>;
const plValues = pl as Record<string, string>;

// Exact keys whose prefix would otherwise drag out-of-scope siblings in.
const INITIATIVE_26_KEYS = [
  "catalog.emptyCategory",
  "catalog.emptyInCategory",
  "admin.tabs.categories",
  // Story 52.1 (commit 3202b7c) shipped this key. Its two `catalog.filters.*`
  // neighbours `openFilters` and `title` came from 47e8407 (2026-05-10), two
  // months before Initiative 26, and stay out of scope.
  "catalog.filters.openFiltersWithCount",
];

const INITIATIVE_26_PREFIXES = [
  "catalog.browse.",
  "catalog.suggestions.",
  "catalog.image_viewer.",
  "modules.admin.categories.",
];

function inScope(key: string): boolean {
  return INITIATIVE_26_KEYS.includes(key) || INITIATIVE_26_PREFIXES.some((p) => key.startsWith(p));
}

const scopedKeys = Object.keys(enValues).filter(inScope).sort();

/** `{{name}}` placeholders, in source order. */
function placeholders(value: string): string[] {
  return value.match(/\{\{.*?\}\}/g) ?? [];
}

/** The value with every interpolation removed — what a reader is left to read. */
function prose(value: string): string {
  return value.replace(/\{\{.*?\}\}/g, "");
}

const HAS_LETTER = /\p{L}/u;

// A bare "pl must differ from en" rule is a false-positive generator: some
// pairs are legitimately identical, and a gate that cries wolf gets disabled by
// the next person who trips it. Every entry needs a reason, and the reason has
// to be about the string — not about the inconvenience of fixing it.
//
// Seeded from § 2 V-4 of the story. V-4 lists five shipped identical pairs; the
// other three (`modules.admin.tagGroups.model_count_one`,
// `catalog.filters.status`, `catalog.sort.status`) sit outside the § 3 key
// space, so listing them here would be inert and would overstate what this
// check covers.
const IDENTICAL_BY_DESIGN = new Map([
  ["catalog.image_viewer.counter", "interpolation and a separator; there is no prose to translate"],
  [
    "modules.admin.categories.model_count_one",
    "'model' is a loanword whose pl nominative singular is spelled exactly as the en singular",
  ],
  [
    // Added by this story, not inherited: aligning the pl plural family onto the
    // "{{count}} <noun>" shape the rest of the family and both admin counters
    // already use (§ 13 ruling c) lands the singular on the same loanword
    // coincidence the admin counter above already records.
    "catalog.browse.categoryWithCount_one",
    "'model' is a loanword whose pl nominative singular is spelled exactly as the en singular",
  ],
]);

describe("Initiative 26 i18n content audit (Story 54.1)", () => {
  it("covers exactly the 157 keys the audit enumerated", () => {
    // A literal, like `browse-i18n.test.ts` uses. A key added to one of these
    // families without bumping this number is a key that entered the audited
    // surface without being audited.
    expect(scopedKeys).toHaveLength(157);
  });

  it("has no in-scope pl value that is still the English string", () => {
    for (const key of scopedKeys) {
      if (IDENTICAL_BY_DESIGN.has(key)) continue;
      expect(plValues[key], `pl.${key} is byte-identical to en.${key}`).not.toBe(enValues[key]);
    }
  });

  it("keeps the identical-by-design allowlist honest", () => {
    // An allowlist entry that no longer describes an identical pair is a stale
    // exemption hiding a future regression.
    for (const [key, reason] of IDENTICAL_BY_DESIGN) {
      expect(scopedKeys, `${key} is allowlisted but out of scope`).toContain(key);
      expect(plValues[key], `${key} is allowlisted but no longer identical`).toBe(enValues[key]);
      expect(reason.length, `${key} needs a reason`).toBeGreaterThan(0);
    }
  });

  it("has no placeholder or untranslated-marker pl value", () => {
    for (const key of scopedKeys) {
      const plValue = plValues[key] ?? "";
      expect(plValue.trim(), `pl.${key} is empty`).not.toBe("");
      expect(plValue, `pl.${key} carries an untranslated marker`).not.toMatch(
        /\b(todo|tbd|fixme|xxx)\b/i,
      );
      // Interpolation-and-punctuation only on the pl side while en carries
      // prose means the sentence around the value was never translated.
      if (HAS_LETTER.test(prose(enValues[key] ?? ""))) {
        expect(
          HAS_LETTER.test(prose(plValue)),
          `pl.${key} is interpolation-only while en.${key} carries prose`,
        ).toBe(true);
      }
    }
  });

  it("keeps the same interpolation placeholders in both locales", () => {
    for (const key of scopedKeys) {
      expect(
        placeholders(plValues[key] ?? "").sort(),
        `pl.${key} placeholders diverge from en.${key}`,
      ).toEqual(placeholders(enValues[key] ?? "").sort());
    }
  });

  it("gives every viewer control its own Polish accessible name", () => {
    // AC-7 regression guard. `trigger_label` and `zoom_in` both rendered as
    // "Powiększ" until this story, so a screen-reader user heard one name for
    // two different controls (NFR26-A11Y-1: distinguishable by accessible
    // name, not by appearance alone). The two viewer specs scope every lookup
    // to `image-viewer-toolbar` because of it; this check is what stops the
    // collision coming back once that scoping stops being load-bearing.
    const seen = new Map<string, string>();
    for (const key of scopedKeys.filter((k) => k.startsWith("catalog.image_viewer."))) {
      const value = plValues[key] ?? "";
      const collidesWith = seen.get(value);
      expect(collidesWith, `pl.${key} and pl.${collidesWith} are both "${value}"`).toBeUndefined();
      seen.set(value, key);
    }
  });
});
