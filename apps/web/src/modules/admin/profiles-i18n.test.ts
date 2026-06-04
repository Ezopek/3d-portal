import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 33.1 (AC-22) — i18n parity for the new admin-profiles + member-selector keys. Both
// locales must carry the SAME key set; Polish must use real diacritics; material names
// PLA/PETG/PCTG/TPU stay UNtranslated (rendered raw from MATERIAL_CLASSES, never an i18n key).
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIXES = [
  "admin.tabs.profiles",
  "modules.admin.profiles.",
  "modules.estimates.selector.reason_",
];

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj)
    .filter((k) => STORY_PREFIXES.some((p) => k === p || k.startsWith(p)))
    .sort();
}

describe("Story 33.1 i18n parity (AC-22)", () => {
  it("en and pl carry the identical Story 33.1 key set", () => {
    expect(storyKeys(plKeys)).toEqual(storyKeys(enKeys));
  });

  it("every Story 33.1 key is non-empty in both locales", () => {
    for (const k of storyKeys(enKeys)) {
      expect(enKeys[k], `en missing ${k}`).toBeTruthy();
      expect(plKeys[k], `pl missing ${k}`).toBeTruthy();
    }
  });

  it("the Polish strings use diacritics (a real translation, not an en copy)", () => {
    const plText = storyKeys(plKeys)
      .map((k) => plKeys[k])
      .join(" ");
    expect(/[ąćęłńóśźż]/i.test(plText)).toBe(true);
  });

  it("does NOT translate material names (no per-material i18n key)", () => {
    for (const material of ["PLA", "PETG", "PCTG", "TPU"]) {
      expect(`modules.admin.profiles.material.${material}` in enKeys).toBe(false);
    }
  });
});
