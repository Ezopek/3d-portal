import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// TAG-GROUPS-1 (Story 46.1) — i18n parity for the new tag-groups admin screen, mirroring
// profile-library-i18n.test.ts. `model_count` is a CLDR plural-keyed i18next key
// (`_one`/`_other` in en, `_one`/`_few`/`_many`/`_other` in pl) — the two locales
// legitimately need a different number of plural-form keys, so parity is checked on the
// base key (suffix stripped), not on the raw key set.
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIXES = ["admin.tabs.tagGroups", "modules.admin.tagGroups."];
const PLURAL_SUFFIXES = ["_zero", "_one", "_two", "_few", "_many", "_other"];

function baseKey(key: string): string {
  const suffix = PLURAL_SUFFIXES.find((s) => key.endsWith(s));
  return suffix ? key.slice(0, -suffix.length) : key;
}

function storyKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj).filter((k) => STORY_PREFIXES.some((p) => k === p || k.startsWith(p)));
}

function storyBaseKeys(obj: Record<string, string>): string[] {
  return [...new Set(storyKeys(obj).map(baseKey))].sort();
}

describe("tag-groups i18n parity (Story 46.1)", () => {
  it("en and pl carry the same base key set (plural-form key count may legitimately differ)", () => {
    expect(storyBaseKeys(plKeys)).toEqual(storyBaseKeys(enKeys));
    expect(storyBaseKeys(enKeys).length).toBeGreaterThan(0);
  });

  it("every tag-groups key is non-empty in both locales", () => {
    for (const k of storyKeys(enKeys)) {
      expect(enKeys[k], `en missing ${k}`).toBeTruthy();
    }
    for (const k of storyKeys(plKeys)) {
      expect(plKeys[k], `pl missing ${k}`).toBeTruthy();
    }
  });

  it("every pl value is a real translation, not a copy of the en value", () => {
    // "model" is a loanword spelled identically in en and pl singular nominative —
    // a legitimate coincidence, not an untranslated copy.
    const COINCIDENTAL_MATCHES = new Set(["modules.admin.tagGroups.model_count_one"]);
    for (const k of storyKeys(plKeys)) {
      if (k in enKeys && !COINCIDENTAL_MATCHES.has(k)) {
        expect(plKeys[k], `pl.${k} is identical to en.${k}`).not.toBe(enKeys[k]);
      }
    }
  });
});
