/*
 * Story 54.2 / AC-4 (T7) — accessibility-TREE traversal for every overlay on
 * the Initiative 26 journey, in real Chromium, on all four Playwright projects.
 *
 * ⚠️ SCOPE OF THE CLAIM (story § 0.1). Everything below is an
 * ACCESSIBILITY-TREE claim measured through the DOM — roles, names,
 * `aria-hidden`/`inert`, focus position. **No screen reader was run.** No
 * physical Android device was used: `mobile-light`/`mobile-dark` are a desktop
 * Chromium with an emulated Pixel 5 viewport, DPR and touch flag. Say
 * "emulation", never "Android".
 *
 * WHAT THIS SPEC PROVES, PER OVERLAY
 * ----------------------------------
 *   (a) focus cannot leave the overlay in EITHER Tab direction, and
 *   (b) the background is hidden from assistive technology.
 *
 * DN-1 — WHY (a) LOOKED FALSE AND IS NOT (Story 54.2 / T8, measured 2026-07-31)
 * ---------------------------------------------------------------------------
 * `deferred-work.md` carried "the modal focus trap does not hold in real
 * Chromium" as `status: OPEN`, `Owner: Story 54.2`, measured by Story 53.3 on
 * all four projects in both directions. **It does not reproduce.** The trap
 * holds. Two separate measurement artefacts produced the original reading:
 *
 *   1. `@base-ui/react`'s `FloatingFocusManager` renders two `FocusGuard`
 *      `<span tabindex=0>` elements as SIBLINGS of the popup inside the portal
 *      — deliberately outside `[role="dialog"]`. Tabbing off either end of the
 *      dialog lands on a guard for one tick, and the guard's `onFocus` then
 *      bounces focus back to the other end. The bounce is QUEUED, not
 *      synchronous. A probe that reads `document.activeElement` immediately
 *      after `keyboard.press` therefore samples the guard and records
 *      "focus left the dialog" on the one tick where the trap is doing its
 *      job. Every read below settles across two animation frames first, and
 *      the guards are treated as part of the overlay's focus scope because
 *      that is what they are.
 *   2. `#root` genuinely carries neither `inert` nor `aria-hidden` — but the
 *      background IS hidden. `markOthers.js` builds its keep-set from
 *      `body.querySelectorAll('[aria-live]')` and walks INTO any ancestor of a
 *      live region instead of hiding it, so a live region mounted under
 *      `#root` (here: Sonner's toaster `<section aria-live>`, mounted in
 *      `App.tsx:34`) makes `#root` un-markable BY DESIGN — a live region must
 *      stay announceable while a modal is open. base-ui hides `#root`'s other
 *      children individually instead, and it does: the whole app shell carries
 *      `aria-hidden="true"`. The old probe asserted the wrong node.
 *      Separately, base-ui never sets `inert` at this version — it passes only
 *      `ariaHidden` to `markOthers` — so an `inert` assertion asserts something
 *      the library does not do.
 *
 * Consequence: `apps/web/src/ui/dialog.tsx` is NOT modified by this story. The
 * bounded `Ask First` grant on it (story § 11 Q-4) was deliberately NOT
 * exercised — there is no defect there to repair.
 *
 * playwright.config.ts forces `pl-PL`, so every matcher is the literal pl.json
 * string or a locale-independent role/testid.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail, stubSotList } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

/** Every open overlay in this app is one of these two shadcn slots. */
const OVERLAY_SLOTS = '[data-slot="dialog-content"], [data-slot="sheet-content"]';

interface FocusSample {
  tag: string;
  testid: string | null;
  label: string;
  /** Inside the open overlay popup itself. */
  inOverlay: boolean;
  /** On one of base-ui's focus guards — part of the overlay's focus scope. */
  onGuard: boolean;
  /** Inside the page behind the overlay — this is what must never happen. */
  inBackground: boolean;
}

/**
 * Press `key` `presses` times, sampling focus after the queued guard bounce has
 * landed. Two `requestAnimationFrame`s is the settle point: `enqueueFocus`
 * defers, so a same-tick read samples the guard rather than the bounce target.
 */
async function tabTrail(page: Page, key: "Tab" | "Shift+Tab", presses: number) {
  const trail: FocusSample[] = [];
  for (let i = 0; i < presses; i += 1) {
    await page.keyboard.press(key);
    await page.evaluate(
      () =>
        new Promise((resolve) => {
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        }),
    );
    trail.push(
      await page.evaluate((slots) => {
        const el = document.activeElement as HTMLElement | null;
        const overlay = document.querySelector(slots);
        const shell = document.querySelector("#root > div");
        return {
          tag: el?.tagName ?? "none",
          testid: el?.getAttribute("data-testid") ?? null,
          label:
            el?.getAttribute("aria-label") ?? (el?.textContent ?? "").trim().slice(0, 32),
          inOverlay: overlay?.contains(el) ?? false,
          onGuard: el?.hasAttribute("data-base-ui-focus-guard") ?? false,
          inBackground: shell?.contains(el) ?? false,
        };
      }, OVERLAY_SLOTS),
    );
  }
  return trail;
}

/** Assert the settled focus position never leaves the overlay's focus scope. */
async function expectFocusTrapped(page: Page, presses: number) {
  for (const key of ["Shift+Tab", "Tab"] as const) {
    const trail = await tabTrail(page, key, presses);
    const escapes = trail
      .map((s, i) => ({ ...s, press: i + 1 }))
      .filter((s) => !s.inOverlay && !s.onGuard);
    expect(
      escapes,
      `focus left the overlay on ${key}: ${JSON.stringify(escapes)}`,
    ).toEqual([]);
    // Stronger than "not outside": it must be positively inside the page-behind
    // never, so a focus that fell to <body> is also a failure.
    expect(
      trail.filter((s) => s.inBackground),
      `focus reached the page behind on ${key}`,
    ).toEqual([]);
  }
}

/**
 * Assert the background is hidden from assistive technology.
 *
 * The unit is deliberately NOT "does `#root` carry the attribute" — that is the
 * assertion DN-1 got wrong (see the header note). What the criterion actually
 * means is that no background CONTROL is reachable by a virtual cursor, so that
 * is what is measured: every focusable element under `#root` must have an
 * `aria-hidden="true"` / `inert` ancestor-or-self. Where base-ui chooses to put
 * the attribute — on `#root`, or on individual children when a live region
 * forces it to keep walking — is an implementation detail this assertion is
 * correctly blind to.
 */
async function expectBackgroundHiddenFromAt(page: Page) {
  const exposed = await page.evaluate(() => {
    const root = document.getElementById("root");
    const focusables = Array.from(
      root?.querySelectorAll(
        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    );
    const hidden = (el: Element) => {
      for (let n: Element | null = el; n !== null; n = n.parentElement) {
        if (n.getAttribute("aria-hidden") === "true" || n.hasAttribute("inert")) return true;
      }
      return false;
    };
    return {
      total: focusables.length,
      exposed: focusables
        .filter((el) => !hidden(el))
        .slice(0, 8)
        .map((el) => ({
          tag: el.tagName,
          testid: el.getAttribute("data-testid"),
          label: el.getAttribute("aria-label") ?? (el.textContent ?? "").trim().slice(0, 32),
        })),
      exposedCount: focusables.filter((el) => !hidden(el)).length,
    };
  });

  // Non-vacuity: a page with no background controls proves nothing.
  expect(exposed.total, "#root has background controls to hide").toBeGreaterThan(0);
  expect(
    exposed.exposedCount,
    `${exposed.exposedCount} background control(s) still reachable by a virtual cursor` +
      ` while the overlay is open; first few: ${JSON.stringify(exposed.exposed)}`,
  ).toBe(0);
}

function skipOnDesktop(testInfo: { project: { name: string } }) {
  test.skip(
    !testInfo.project.name.startsWith("mobile-"),
    "BrowseSheet's trigger is lg:hidden; the desktop browse surface is the rail.",
  );
}

// ---------------------------------------------------------------------------
// 1. The photo lightbox — `ImageFullscreenViewer`, a `DialogContent` consumer.
// ---------------------------------------------------------------------------
test("lightbox: focus is trapped in both directions and the background is hidden from AT", async ({
  page,
}) => {
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();

  await page.getByTestId("image-viewer-close").focus();
  // More presses than the viewer has controls, so the cycle has to wrap: a trap
  // that only holds for the first pass is not a trap.
  await expectFocusTrapped(page, 10);
  await expectBackgroundHiddenFromAt(page);
});

// ---------------------------------------------------------------------------
// 2. A NON-viewer `ui/dialog.tsx` consumer (AC-5's verification bar). The
//    lightbox overrides `DialogContent`'s geometry classes wholesale, so a
//    plain consumer is the one that proves the shared layer, not the override.
// ---------------------------------------------------------------------------
test("DeleteModelDialog: focus is trapped in both directions and the background is hidden from AT", async ({
  page,
}) => {
  await loginAsAdmin(page);
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // catalog.actions.modelActions = "Akcje modelu"; catalog.actions.delete = "Usuń".
  await page.getByRole("button", { name: /^Akcje modelu$/i }).click();
  await page.getByRole("menuitem", { name: /^Usuń$/i }).click();
  const dialog = page.locator('[data-slot="dialog-content"]');
  await expect(dialog).toBeVisible();

  await expectFocusTrapped(page, 8);
  await expectBackgroundHiddenFromAt(page);
});

// ---------------------------------------------------------------------------
// 3. The Filters panel — a `SheetContent` consumer. Right panel at `lg`+,
//    bottom sheet below; both regimes run, one per project family.
// ---------------------------------------------------------------------------
test("Filters panel: focus is trapped in both directions and the background is hidden from AT", async ({
  page,
}) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);

  // catalog.filters.openFilters = "Filtry".
  await page.getByRole("button", { name: "Filtry", exact: true }).click();
  const sheet = page.locator('[data-slot="sheet-content"]');
  await expect(sheet).toBeVisible();

  await expectFocusTrapped(page, 12);
  await expectBackgroundHiddenFromAt(page);
});

// ---------------------------------------------------------------------------
// 4. The mobile Browse sheet — the other `SheetContent` consumer on the
//    journey. Mobile-only by construction (`lg:hidden` trigger).
// ---------------------------------------------------------------------------
test("Browse sheet: focus is trapped in both directions and the background is hidden from AT", async ({
  page,
}, testInfo) => {
  skipOnDesktop(testInfo);
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);

  // catalog.browse.trigger = "Przeglądaj".
  await page.getByRole("button", { name: "Przeglądaj" }).click();
  const sheet = page.locator('[data-slot="sheet-content"]');
  await expect(sheet).toBeVisible();

  await expectFocusTrapped(page, 10);
  await expectBackgroundHiddenFromAt(page);
});
