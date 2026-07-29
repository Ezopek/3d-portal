import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 52.1 — i18n parity for the consolidated `Filters (n)` surface,
// mirroring browse-i18n.test.ts / suggestions-i18n.test.ts's key-set-diff
// shape. The locale files are flat dotted-key JSON, so a prefix filter is the
// whole of the "namespace".
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIX = "catalog.filters.";

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj).filter((k) => k.startsWith(STORY_PREFIX));
}

// `Status` is a genuine en/pl cognate — the Polish word IS "Status". It is the
// only `catalog.filters.*` key whose two locale values legitimately coincide,
// so it is allow-listed by name rather than by weakening the guard below.
const IDENTICAL_BY_LANGUAGE = new Set(["catalog.filters.status"]);

describe("catalog.filters i18n parity (Story 52.1)", () => {
  it("en and pl carry the same key set", () => {
    expect(storyKeys(plKeys).sort()).toEqual(storyKeys(enKeys).sort());
    // 14 shipped before this story, and 14 after: Story 52.1 removes
    // `openTags` (the retired Tagi trigger) and adds `openFiltersWithCount`
    // (D-10's counted accessible name). The literal is the point: a key added
    // without a deliberate bump here is a key added without a pl value.
    expect(storyKeys(enKeys)).toHaveLength(14);
  });

  it("every filters key is non-empty in both locales", () => {
    for (const k of storyKeys(enKeys)) {
      expect(enKeys[k], `en missing ${k}`).toBeTruthy();
    }
    for (const k of storyKeys(plKeys)) {
      expect(plKeys[k], `pl missing ${k}`).toBeTruthy();
    }
  });

  it("every pl value is a real translation, not a copy of the en value", () => {
    for (const k of storyKeys(plKeys)) {
      if (!(k in enKeys) || IDENTICAL_BY_LANGUAGE.has(k)) continue;
      expect(plKeys[k], `pl.${k} is identical to en.${k}`).not.toBe(enKeys[k]);
    }
  });

  // D-10 / AC-20 — the trigger's counted accessible name. EXPERIENCE.md:204's
  // own examples ("Filters (3)" / "Filtry (3)") are the literal contract, and a
  // parenthesised numeral is grammatically invariant in both locales, so this
  // key deliberately ships WITHOUT `_one`/`_few`/`_many` plural forms.
  it("carries the counted trigger name with its {{count}} placeholder in both locales", () => {
    for (const locale of [enKeys, plKeys]) {
      const value = locale["catalog.filters.openFiltersWithCount"] ?? "";
      expect(value).toContain("{{count}}");
      expect(value).toContain("(");
      expect(value).toContain(")");
    }
    expect(enKeys["catalog.filters.openFiltersWithCount"]).toBe(
      "Filters ({{count}})",
    );
    expect(plKeys["catalog.filters.openFiltersWithCount"]).toBe(
      "Filtry ({{count}})",
    );
    for (const suffix of ["_one", "_few", "_many", "_other"]) {
      expect(
        `catalog.filters.openFiltersWithCount${suffix}` in enKeys,
        `unexpected plural form ${suffix}`,
      ).toBe(false);
    }
  });

  // AC-22 — exactly two keys are retired, and the three look-alikes that still
  // have call sites are NOT. `catalog.actions.addTag` survives on
  // `TagGroupsSection.tsx` (model detail); `catalog.tags.searchPlaceholder` and
  // `catalog.tags.noMatches` survive inside `FacetSidebar`.
  it("retires exactly the two orphaned keys and keeps the three with surviving call sites", () => {
    for (const locale of [enKeys, plKeys]) {
      expect("catalog.filters.openTags" in locale).toBe(false);
      expect("catalog.tags.pickerTitle" in locale).toBe(false);
      expect(locale["catalog.actions.addTag"]).toBeTruthy();
      expect(locale["catalog.tags.searchPlaceholder"]).toBeTruthy();
      expect(locale["catalog.tags.noMatches"]).toBeTruthy();
    }
  });

  // AC-21 — the 50.3 overflow note pointed at the `+ tag` control this story
  // deletes. Only its VALUE changes; the key name and its call site's
  // attributes are untouched (EXPERIENCE.md:226).
  it("points the suggestion overflow note at the Filters surface, not at + tag", () => {
    expect(enKeys["catalog.suggestions.overflowNote"]).toContain("Filters");
    expect(plKeys["catalog.suggestions.overflowNote"]).toContain("Filtry");
    for (const locale of [enKeys, plKeys]) {
      expect(locale["catalog.suggestions.overflowNote"] ?? "").not.toMatch(
        /\+\s*tag/i,
      );
    }
  });

  it("keeps the whole en/pl key set 1:1 after the change", () => {
    expect(Object.keys(plKeys).sort()).toEqual(Object.keys(enKeys).sort());
  });
});
