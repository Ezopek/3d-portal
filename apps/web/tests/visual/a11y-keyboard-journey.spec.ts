/*
 * Story 54.2 / AC-3 (T6) — the cross-surface keyboard-only journey, in real
 * Chromium, on all four Playwright projects.
 *
 * `epics.md:4595` charters this story for "keyboard-only and screen-reader
 * traversal BETWEEN surfaces, which no single component test covers". This is
 * that clause made executable. Every per-story spec in this suite proves its
 * own surface; none of them walks from one to the next, which is exactly where
 * the residue lives.
 *
 * WHAT THIS ASSERTS, AND WHAT IT DELIBERATELY DOES NOT (VS-3)
 * ----------------------------------------------------------
 * AC-3 is REACHABILITY plus FOCUS RETURN:
 *   - every hop on the § 1 journey is reachable with the keyboard alone —
 *     no pointer, no `.click()`, no `.focus()` shortcut. `Tab` and `Enter`
 *     only;
 *   - dismissing an overlay returns focus to the control that opened it.
 * The focus TRAP is AC-4's and lives in `a11y-overlay-traversal.spec.ts`. The
 * split is deliberate: AC-3 was originally written to assert "focus is where
 * the contract says" at the lightbox hop, which conflated the two and made this
 * spec depend on DN-1.
 *
 * ⚠️ SCOPE OF THE CLAIM (story § 0.1). Headless-Chromium evidence. The
 * `mobile-*` projects are EMULATION — a desktop Chromium with a Pixel 5
 * viewport, DPR and touch flag — never "Android". No physical device, no
 * screen reader.
 *
 * playwright.config.ts forces `pl-PL`, so every name matcher is the literal
 * pl.json string.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail, stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
/** Enough to cross a full catalog grid; a real journey needs far fewer. */
const MAX_TAB_PRESSES = 120;

interface Focused {
  testid: string | null;
  label: string;
  tag: string;
  href: string | null;
}

async function focused(page: Page): Promise<Focused> {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    return {
      testid: el?.getAttribute("data-testid") ?? null,
      label:
        el?.getAttribute("aria-label") ?? (el?.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 48),
      tag: el?.tagName ?? "none",
      href: el?.getAttribute("href") ?? null,
    };
  });
}

/**
 * Tab forward until `match` accepts the focused element. Keyboard only — this
 * helper never calls `.focus()` or `.click()`, because a journey that needs a
 * pointer to reach its next hop is precisely the failure AC-3 looks for.
 */
async function tabUntil(page: Page, what: string, match: (f: Focused) => boolean) {
  const trail: Focused[] = [];
  for (let i = 0; i < MAX_TAB_PRESSES; i += 1) {
    await page.keyboard.press("Tab");
    const f = await focused(page);
    trail.push(f);
    if (match(f)) return f;
  }
  throw new Error(
    `keyboard-only traversal never reached ${what} in ${MAX_TAB_PRESSES} Tab presses.` +
      ` Trail: ${JSON.stringify(trail.map((t) => t.testid ?? t.label))}`,
  );
}

function isMobile(testInfo: { project: { name: string } }) {
  return testInfo.project.name.startsWith("mobile-");
}

test("keyboard-only: /catalog -> scope -> Filters open/close -> detail -> lightbox open/close", async ({
  page,
}, testInfo) => {
  // The list fixture is registered FIRST and the detail fixture SECOND, so the
  // detail route's exact handler wins for `/api/models/<id>` while the list
  // handler still serves `/api/models?...` (Playwright resolves handlers in
  // reverse registration order — `_test.ts:10-19`).
  await stubSotList(page);
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto("/catalog");
  await waitForReady(page);

  // ---- HOP 1: the Filters trigger is reachable, opens, and returns focus ----
  // catalog.filters.openFilters = "Filtry".
  await tabUntil(page, 'the "Filtry" trigger', (f) => f.label === "Filtry");
  await page.keyboard.press("Enter");
  const panel = page.locator('[data-slot="sheet-content"]');
  await expect(panel).toBeVisible();

  // Opening moved focus INTO the panel — otherwise a keyboard user would have
  // to tab the whole page again to reach what they just opened.
  expect(
    await page.evaluate(
      () =>
        document
          .querySelector('[data-slot="sheet-content"]')
          ?.contains(document.activeElement) ?? false,
    ),
    "opening the Filters panel must move focus into it",
  ).toBe(true);

  await page.keyboard.press("Escape");
  await expect(panel).not.toBeVisible();
  expect(
    (await focused(page)).label,
    "dismissing the Filters panel must return focus to the trigger that opened it",
  ).toBe("Filtry");

  // ---- HOP 2: browse to a category, keyboard only ----
  // Desktop uses BrowseRail (`hidden lg:flex`); below `lg` the same vocabulary
  // lives behind the BrowseSheet trigger. Both are walked with Tab + Enter.
  if (isMobile(testInfo)) {
    // catalog.browse.openBrowse = "Przeglądaj".
    await tabUntil(page, 'the "Przeglądaj" trigger', (f) => f.label === "Przeglądaj");
    await page.keyboard.press("Enter");
    const sheet = page.locator('[data-slot="sheet-content"]');
    await expect(sheet).toBeVisible();
  }
  await tabUntil(page, "a browse category link", (f) =>
    /Uchwyty i mocowania/.test(f.label),
  );
  await page.keyboard.press("Enter");
  await page.waitForURL("**/categories/uchwyty");
  await waitForReady(page);

  // ---- HOP 3: the scope chip's escape is reachable from the top ----
  // catalog.browse.clearCategory / searchEntireCatalog — the chip renders ONE
  // navigation with two possible labels (ScopeChip.tsx:41-43).
  await tabUntil(page, "the scope-chip escape link", (f) =>
    /Wyczyść kategorię|Szukaj w całym katalogu/.test(f.label),
  );

  // ---- HOP 4: into model detail ----
  await tabUntil(
    page,
    "a model-card link",
    (f) => f.tag === "A" && (f.href ?? "").includes("/catalog/"),
  );
  await page.keyboard.press("Enter");
  await page.waitForURL(`**/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // ---- HOP 5: gallery -> lightbox, and back ----
  const trigger = await tabUntil(
    page,
    "the gallery fullscreen trigger",
    (f) => f.testid === "gallery-fullscreen-trigger",
  );
  expect(trigger.testid).toBe("gallery-fullscreen-trigger");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();

  expect(
    await page.evaluate(
      () => document.querySelector('[role="dialog"]')?.contains(document.activeElement) ?? false,
    ),
    "opening the lightbox must move focus into it",
  ).toBe(true);

  await page.keyboard.press("Escape");
  await expect(page.getByTestId("image-viewer-root")).not.toBeVisible();
  expect(
    (await focused(page)).testid,
    "dismissing the lightbox must return focus to the gallery trigger that opened it",
  ).toBe("gallery-fullscreen-trigger");
});
