import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 51.1 — i18n parity for the desktop browse rail, mirroring
// suggestions-i18n.test.ts's key-set-diff shape (Story 50.3).
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIX = "catalog.browse.";

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj).filter((k) => k.startsWith(STORY_PREFIX));
}

describe("catalog.browse i18n parity (Story 51.1)", () => {
  it("en and pl carry the same key set", () => {
    expect(storyKeys(plKeys).sort()).toEqual(storyKeys(enKeys).sort());
    expect(storyKeys(enKeys)).toHaveLength(7);
  });

  it("every browse key is non-empty in both locales", () => {
    for (const k of storyKeys(enKeys)) {
      expect(enKeys[k], `en missing ${k}`).toBeTruthy();
    }
    for (const k of storyKeys(plKeys)) {
      expect(plKeys[k], `pl missing ${k}`).toBeTruthy();
    }
  });

  it("every pl value is a real translation, not a copy of the en value", () => {
    for (const k of storyKeys(plKeys)) {
      if (k in enKeys) {
        expect(plKeys[k], `pl.${k} is identical to en.${k}`).not.toBe(enKeys[k]);
      }
    }
  });

  // EXPERIENCE.md:202 fixes the browse vocabulary: "Przeglądaj"/"Browse".
  // "Odkrywaj" and "Eksploruj" are explicitly rejected — this is a private
  // tool, not a storefront. Guarding it here keeps Story 54.1's cross-surface
  // terminology audit from finding a drift this story could have prevented.
  it("uses the ratified pl browse vocabulary and rejects the storefront synonyms", () => {
    const rail = plKeys["catalog.browse.railLabel"] ?? "";
    expect(rail).toContain("Przeglądaj");
    expect(rail).not.toMatch(/Odkrywaj|Eksploruj/);
  });

  it("keeps both interpolation placeholders in every row accessible-name key", () => {
    for (const locale of [enKeys, plKeys]) {
      for (const key of storyKeys(locale).filter((k) => k.startsWith("catalog.browse.categoryWithCount"))) {
        const value = locale[key] ?? "";
        expect(value).toContain("{{name}}");
        expect(value).toContain("{{count}}");
      }
    }
  });
});
