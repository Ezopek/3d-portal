import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// PROFILE-OFFER-1 (AC-19) — i18n parity for the new profile-offers keys. Both locales must
// carry the SAME key set; Polish must use real diacritics; offer labels + block names +
// material_types render as DATA (untranslated — no per-material/per-name i18n key).
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIXES = ["admin.tabs.profileOffers", "modules.admin.profileOffers."];

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj)
    .filter((k) => STORY_PREFIXES.some((p) => k === p || k.startsWith(p)))
    .sort();
}

describe("PROFILE-OFFER-1 i18n parity (AC-19)", () => {
  it("en and pl carry the identical profile-offers key set", () => {
    expect(storyKeys(plKeys)).toEqual(storyKeys(enKeys));
  });

  it("every profile-offers key is non-empty in both locales", () => {
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
      expect(`modules.admin.profileOffers.material.${material}` in enKeys).toBe(false);
    }
  });
});
