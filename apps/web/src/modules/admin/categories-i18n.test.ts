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

// ---------------------------------------------------------------------------
// Story 52.3 — the curation-QA panel's copy contract
// ---------------------------------------------------------------------------

const QA_PREFIX = "modules.admin.categories.qa.";

function qaKeys(obj: Record<string, string>): string[] {
  return Object.keys(obj)
    .filter((k) => k.startsWith(QA_PREFIX))
    .sort();
}

describe("admin curation QA i18n parity (Story 52.3)", () => {
  it("carries the IDENTICAL raw key set in both locales, CLDR suffixes included", () => {
    // The repo-wide guard (tests/i18n.test.ts) compares RAW keys, so a Polish
    // `_few`/`_many` without an English counterpart fails it. That is exactly
    // what broke Story 52.2's first full gate; this story-level check makes the
    // failure local and legible instead of repo-wide and cryptic.
    expect(qaKeys(plKeys)).toEqual(qaKeys(enKeys));
    expect(qaKeys(enKeys).length).toBeGreaterThan(0);
  });

  it("ships the complete CLDR set for every counted key in both locales", () => {
    const COUNTED_BASES = [
      `${QA_PREFIX}title`,
      `${QA_PREFIX}overflow`,
      `${QA_PREFIX}tiny_category.finding`,
      `${QA_PREFIX}over_categorized.finding`,
      `${QA_PREFIX}uncategorized_models.finding`,
      `${QA_PREFIX}ungrouped_tags.finding`,
    ];
    for (const base of COUNTED_BASES) {
      for (const suffix of ["_one", "_few", "_many", "_other"]) {
        expect(enKeys[`${base}${suffix}`], `en missing ${base}${suffix}`).toBeTruthy();
        expect(plKeys[`${base}${suffix}`], `pl missing ${base}${suffix}`).toBeTruthy();
      }
    }
  });

  it("never calls a flagged state an error, a failure or broken (AC-23)", () => {
    // EXPERIENCE.md: nothing in curation QA is an error. The ONE permitted use
    // of the word is the explicit negation the mockup itself carries
    // ("To ostrzeżenie, nie błąd."), so it is stripped before the check rather
    // than whitelisted by key.
    // `qa.partial` is excluded: it describes a READ that did not complete, not
    // a curation finding, and saying so is the honesty D-6 requires.
    const FORBIDDEN_EN = ["error", "failure", "failed", "broken", "invalid", "defect"];
    const FORBIDDEN_PL = ["błąd", "błęd", "awaria", "zepsut", "uszkodz", "nieprawidłow"];
    for (const [locale, keys, forbidden, negations] of [
      ["en", enKeys, FORBIDDEN_EN, ["not an error"]],
      ["pl", plKeys, FORBIDDEN_PL, ["nie błąd"]],
    ] as const) {
      for (const k of qaKeys(keys)) {
        if (k === `${QA_PREFIX}partial`) continue;
        let value = keys[k]?.toLowerCase() ?? "";
        for (const negation of negations) value = value.split(negation).join("");
        for (const word of forbidden) {
          expect(value, `${locale}.${k} calls a curation finding "${word}"`).not.toContain(word);
        }
      }
    }
  });

  it("states in both locales that nothing is auto-applied and no category comes from tags (AC-23)", () => {
    // FR26-ADMIN-2 / EXPERIENCE.md:290. The panel must say the negative out
    // loud; a surface that merely omits an auto-apply button does not.
    expect(enKeys[`${QA_PREFIX}description`]).toContain("never inferred from a model's tags");
    expect(plKeys[`${QA_PREFIX}description`]).toContain("nigdy nie wynika z tagów modelu");
  });

  it("keeps the over-categorized copy a warning about a suggestion, not a limit", () => {
    // FR26-CAT-3 is advisory. The row must not imply the write was or would be
    // blocked — the panel performs no write at all.
    expect(enKeys[`${QA_PREFIX}over_categorized.sub`]).toContain("suggested norm is 1–3");
    expect(plKeys[`${QA_PREFIX}over_categorized.sub`]).toContain("Sugerowana norma to 1–3");
  });

  it("calls a zero-category model a valid state, exactly as the shipped queue does", () => {
    expect(enKeys[`${QA_PREFIX}uncategorized_models.sub`]).toContain("valid state");
    expect(plKeys[`${QA_PREFIX}uncategorized_models.sub`]).toContain("poprawny stan");
  });

  it("reuses the shipped empty-state copy — not an error, not a celebration", () => {
    // EXPERIENCE.md:252. Deliberately the SAME sentence the curation queue
    // already ships, because it is the same promise.
    expect(enKeys[`${QA_PREFIX}empty`]).toBe(enKeys["modules.admin.categories.queue.empty"]);
    expect(plKeys[`${QA_PREFIX}empty`]).toBe(plKeys["modules.admin.categories.queue.empty"]);
  });
});
