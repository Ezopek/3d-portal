import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 50.3 — i18n parity for the new SearchSuggest combobox, mirroring
// admin/tag-groups-i18n.test.ts's key-set-diff shape.
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIX = "catalog.suggestions.";

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj).filter((k) => k.startsWith(STORY_PREFIX));
}

describe("catalog.suggestions i18n parity (Story 50.3)", () => {
  it("en and pl carry the same key set", () => {
    expect(storyKeys(plKeys).sort()).toEqual(storyKeys(enKeys).sort());
    expect(storyKeys(enKeys).length).toBeGreaterThan(0);
  });

  it("every suggestions key is non-empty in both locales", () => {
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

  it("the pl tagOption string matches the UX doc contract verbatim", () => {
    expect(plKeys["catalog.suggestions.tagOption"]).toBe(
      "Dodaj filtr: {{name}}, grupa {{group}}",
    );
  });
});
