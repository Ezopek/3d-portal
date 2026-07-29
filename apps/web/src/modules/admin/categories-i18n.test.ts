import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 52.2 — i18n parity for the admin browse-category screen, mirroring
// `tag-groups-i18n.test.ts`. Several keys here are CLDR plural-keyed
// (`model_count`, `queue.title`, `editor.advisory`, `delete.in_use_title`):
// runtime lookup needs locale-specific suffixes, while the repo's global i18n
// parity guard keeps raw key sets identical. This story-level guard therefore
// also checks the base key (suffix stripped), making the plural contract explicit
// without duplicating the global raw-key check.
const enKeys = en as Record<string, string>;
const plKeys = pl as Record<string, string>;

const STORY_PREFIXES = ["admin.tabs.categories", "modules.admin.categories."];
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

describe("admin categories i18n parity (Story 52.2)", () => {
  it("en and pl carry the same base key set (plural-form key count may legitimately differ)", () => {
    expect(storyBaseKeys(plKeys)).toEqual(storyBaseKeys(enKeys));
    expect(storyBaseKeys(enKeys).length).toBeGreaterThan(0);
  });

  it("every categories key is non-empty in both locales", () => {
    for (const k of storyKeys(enKeys)) {
      expect(enKeys[k], `en missing ${k}`).toBeTruthy();
    }
    for (const k of storyKeys(plKeys)) {
      expect(plKeys[k], `pl missing ${k}`).toBeTruthy();
    }
  });

  it("every pl value is a real translation, not a copy of the en value", () => {
    // "model" is a loanword spelled identically in en and pl singular nominative —
    // the same coincidence `tag-groups-i18n.test.ts` already records.
    const COINCIDENTAL_MATCHES = new Set(["modules.admin.categories.model_count_one"]);
    for (const k of storyKeys(plKeys)) {
      if (k in enKeys && !COINCIDENTAL_MATCHES.has(k)) {
        expect(plKeys[k], `pl.${k} is identical to en.${k}`).not.toBe(enKeys[k]);
      }
    }
  });

  it("the save control never says 'save changes' — it replaces a whole set", () => {
    // EXPERIENCE.md Voice and Tone, and the story's D-3: under the accepted
    // last-writer-wins posture a concurrent edit is silently discarded, so the
    // verb must state what the API does. "Save changes" would imply a merge the
    // contract does not perform. Asserted on the shipped strings, not on prose.
    expect(enKeys["modules.admin.categories.editor.submit"]).toBe("Replace categories");
    expect(plKeys["modules.admin.categories.editor.submit"]).toBe("Zastąp kategorie");
    for (const [locale, keys] of [
      ["en", enKeys],
      ["pl", plKeys],
    ] as const) {
      for (const k of storyKeys(keys)) {
        const value = keys[k]?.toLowerCase() ?? "";
        expect(value, `${locale}.${k} uses forbidden save-changes wording`).not.toContain(
          "save changes",
        );
        expect(value, `${locale}.${k} uses forbidden save-changes wording`).not.toContain(
          "zapisz zmiany",
        );
      }
    }
  });

  it("the advisory copy states that saving is not blocked", () => {
    // FR26-CAT-3 is a WARNING-level norm. The copy must not read as an error or
    // a limit; if this string ever loses the "not blocked" clause the screen
    // starts implying an enforcement the API does not have.
    expect(enKeys["modules.admin.categories.editor.advisory_other"]).toContain("not blocked");
    expect(plKeys["modules.admin.categories.editor.advisory_many"]).toContain("nie jest blokowany");
  });

  it("the curation queue copy calls a zero-category model valid, not broken", () => {
    // FR26-CAT-2 / EXPERIENCE.md: a zero-category model is normal and stays
    // public. The queue is curation work, never a defect report.
    expect(enKeys["modules.admin.categories.queue.description"]).toContain("valid state");
    expect(plKeys["modules.admin.categories.queue.description"]).toContain("poprawny stan");
  });
});
