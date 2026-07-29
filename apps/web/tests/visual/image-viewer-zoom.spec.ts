// Story 53.2 (E53 / FR26-VIEW-1, NFR26-A11Y-1, NFR26-VISUAL-1) — TARGETED
// coverage of the mature viewer's always-mounted zoom toolbar.
//
// Deliberately narrow (story D-10). This spec owns exactly two captured states
// plus the assertions jsdom cannot make honestly:
//
//   1. the viewer open AT REST (scale 1.0) with the toolbar mounted
//   2. the viewer ZOOMED with the tap-to-hide chrome HIDDEN — mockup
//      `key-viewer-chrome.html` state C, "the load-bearing state"
//
// The FULL contract — Pixel 5 portrait AND landscape, panorama 4:1 and 8:1,
// portrait 1:4, small source, rotation refit, repeated open-close, error and
// slow-load, and the PHYSICAL Android Chrome smoke — belongs to Story 53.3
// (`epics.md:4579`) and is NOT pre-empted here.
//
// `tests/visual/image-viewer-containment.spec.ts` is a STANDING suite
// (`architecture.md:3376`) and is not touched by this story; it must stay green
// unmodified.
//
// playwright.config.ts forces `pl-PL`, so every matcher below is the literal
// pl.json string (`Powiększ` / `Pomniejsz` / `Dopasuj`). Per the Epic 45/46
// test-authoring rule, every `toHaveScreenshot` is preceded by an explicit
// `toBeVisible()` on the concrete state being captured.

import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

// `{spacing.target-fullscreen-close}` — DESIGN.md:180, :287; EXPERIENCE.md:302;
// WCAG 2.2 SC 2.5.8.
const CLOSE_TARGET_MIN_PX = 44;
// `{components.lightbox-zoom-control}` — DESIGN.md:176.
const ZOOM_CONTROL_MIN_PX = 40;
// Sub-pixel tolerance for device-scale-factor rounding on the Pixel 5 projects.
const EPSILON_PX = 0.5;

async function openViewer(page: Page) {
  // Two images, so the capture exercises the toolbar coexisting with the FULL
  // chrome layer (counter + chevrons) and the thumb strip — the three-layer
  // structure this story introduced. With the single-image default there would
  // be no strip and no counter to layer against.
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  // Layout only reflects the real intrinsic size once the source is decoded,
  // and the toolbar stays DISABLED until it resolves (D-6) — so waiting here is
  // what makes both the screenshots and the geometry assertions meaningful
  // rather than capturing a 0x0 placeholder behind a dimmed toolbar.
  await expect
    .poll(() =>
      page
        .getByTestId("image-viewer-frame")
        .locator("img")
        .evaluate((el: HTMLImageElement) => el.naturalWidth),
    )
    .toBeGreaterThan(0);
  await expect(zoomIn(page)).toBeEnabled();
  await waitForReady(page);
}

// The toolbar is scoped explicitly on every lookup. `catalog.image_viewer
// .zoom_in` is "Powiększ" in Polish and so is the SHIPPED
// `catalog.image_viewer.trigger_label` on the gallery trigger (story D-8's
// recorded terminology collision). 53.2 keeps the UX spine's viewer labels
// verbatim and does NOT rename the shipped trigger — that is raised for Story
// 54.1's cross-surface terminology audit. Scoping here is how this spec stays
// unambiguous in the meantime.
const toolbar = (page: Page) => page.getByTestId("image-viewer-toolbar");
const zoomIn = (page: Page) => toolbar(page).getByRole("button", { name: "Powiększ" });
const zoomOut = (page: Page) => toolbar(page).getByRole("button", { name: "Pomniejsz" });
const zoomReset = (page: Page) => toolbar(page).getByRole("button", { name: "Dopasuj" });

test("image viewer toolbar at rest matches baseline", async ({ page }) => {
  await openViewer(page);
  await expect(toolbar(page)).toBeVisible();
  await expect(zoomIn(page)).toBeVisible();
  await expect(zoomOut(page)).toBeVisible();
  await expect(zoomReset(page)).toBeVisible();
  // Mockup state A: at 1.0 the Zoom Out and Reset controls are
  // disabled-and-announced, not hidden.
  await expect(zoomOut(page)).toBeDisabled();
  await expect(zoomReset(page)).toBeDisabled();
  await expect(page).toHaveScreenshot("image-viewer-toolbar-rest.png");
});

test("image viewer toolbar stays visible when zoomed with chrome hidden", async ({ page }) => {
  await openViewer(page);
  await zoomIn(page).click();
  await zoomIn(page).click();

  // Tap the image to hide the chrome layer. This is the shipped
  // tap-to-toggle-chrome gesture; dispatching real touch events keeps it on
  // the same code path a phone takes.
  const frame = page.getByTestId("image-viewer-frame");
  const box = await frame.boundingBox();
  expect(box).not.toBeNull();
  const cx = (box?.x ?? 0) + (box?.width ?? 0) / 2;
  const cy = (box?.y ?? 0) + (box?.height ?? 0) / 2;
  // `TouchEvent`'s `touches` / `changedTouches` accept ONLY real `Touch`
  // instances — Chromium rejects plain object literals outright ("Failed to
  // convert value to 'Touch'"). `new Touch({...})` additionally requires
  // `identifier` and `target`. Constructing them properly is what keeps this on
  // the same code path a phone takes, instead of reaching past the shipped
  // gesture handler and calling React state directly.
  await page.evaluate(
    ([x, y]) => {
      const root = document.querySelector('[data-testid="image-viewer-root"]');
      if (root === null) return;
      const touch = new Touch({
        identifier: 1,
        target: root,
        clientX: x as number,
        clientY: y as number,
      });
      root.dispatchEvent(
        new TouchEvent("touchstart", {
          bubbles: true,
          touches: [touch],
          targetTouches: [touch],
          changedTouches: [touch],
        }),
      );
      root.dispatchEvent(
        new TouchEvent("touchend", {
          bubbles: true,
          touches: [],
          targetTouches: [],
          changedTouches: [touch],
        }),
      );
    },
    [cx, cy],
  );

  // Mockup state C — chrome hidden AND still zoomed, zoom controls still there.
  await expect(page.getByTestId("image-viewer-strip")).toHaveAttribute("aria-hidden", "true");
  await expect(toolbar(page)).toBeVisible();
  await expect(zoomOut(page)).toBeEnabled();
  await expect(zoomReset(page)).toBeEnabled();
  // The toolbar is never inside an aria-hidden subtree.
  expect(
    await toolbar(page).evaluate((el) => el.closest('[aria-hidden="true"]') !== null),
  ).toBe(false);
  await expect(page).toHaveScreenshot("image-viewer-toolbar-zoomed-chrome-hidden.png");
});

test("focus stays inside the toolbar when a control disables itself", async ({ page }) => {
  await openViewer(page);
  await zoomIn(page).focus();
  // Drive Zoom In to the ceiling from the keyboard. Chromium blurs a control
  // the instant it becomes `disabled`, and Base UI's focus manager does NOT
  // recover it (measured: `document.activeElement` became `<body>`), which
  // strands a keyboard / switch user outside the toolbar inside a focus-trapped
  // dialog. jsdom does not model that blur at all, so this is the only place the
  // repair can be honestly asserted.
  for (let i = 0; i < 20; i += 1) {
    if (await zoomIn(page).isDisabled()) break;
    await zoomIn(page).press("Enter");
  }
  await expect(zoomIn(page)).toBeDisabled();

  const active = await page.evaluate(
    () => document.activeElement?.getAttribute("data-testid") ?? "body",
  );
  expect(active).toBe("image-viewer-zoom-out");
});

test("close and zoom controls meet their target-size floors", async ({ page }) => {
  await openViewer(page);
  // jsdom has no layout, so this is the only place the 44x44 floor (AC-4) and
  // the 40px zoom-control size can actually be MEASURED.
  const close = await page.getByTestId("image-viewer-close").boundingBox();
  expect(close).not.toBeNull();
  expect(close?.width ?? 0).toBeGreaterThanOrEqual(CLOSE_TARGET_MIN_PX - EPSILON_PX);
  expect(close?.height ?? 0).toBeGreaterThanOrEqual(CLOSE_TARGET_MIN_PX - EPSILON_PX);

  for (const control of [zoomIn(page), zoomOut(page), zoomReset(page)]) {
    const box = await control.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(ZOOM_CONTROL_MIN_PX - EPSILON_PX);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(ZOOM_CONTROL_MIN_PX - EPSILON_PX);
  }
});

test("toolbar geometry is invariant across zoom levels (outside the transform layer)", async ({
  page,
}) => {
  await openViewer(page);
  const before = await toolbar(page).boundingBox();
  const closeBefore = await page.getByTestId("image-viewer-close").boundingBox();

  await zoomIn(page).click();
  await zoomIn(page).click();
  // The image really did scale...
  expect(
    await page
      .getByTestId("image-viewer-transform")
      .evaluate((el) => getComputedStyle(el).transform),
  ).not.toBe("none");

  // ...and the toolbar and close button did not move or resize by a pixel,
  // because they live outside the transform layer (AC-1, DESIGN.md § Elevation).
  const after = await toolbar(page).boundingBox();
  const closeAfter = await page.getByTestId("image-viewer-close").boundingBox();
  expect(after?.width).toBeCloseTo(before?.width ?? -1, 1);
  expect(after?.height).toBeCloseTo(before?.height ?? -1, 1);
  expect(after?.x).toBeCloseTo(before?.x ?? -1, 1);
  expect(after?.y).toBeCloseTo(before?.y ?? -1, 1);
  expect(closeAfter?.x).toBeCloseTo(closeBefore?.x ?? -1, 1);
  expect(closeAfter?.y).toBeCloseTo(closeBefore?.y ?? -1, 1);
});

// AC-6. Deliberately ELEMENT-AGNOSTIC. Story V-2 warns that Base UI's
// `useScrollLock` targets `<html>` OR `<body>` depending on which is the
// overflow element and on whether the platform uses overlay scrollbars — and
// measurement confirms it: in this Chromium it locks `<body>` (`overflow:
// hidden`) and leaves `<html>` untouched. Asserting one specific element would
// encode a platform detail and would make this test lie the moment the
// scrollbar mode changes. What is asserted instead is the contract
// `EXPERIENCE.md:234` actually states: scrolling is prevented while open, and
// the document is exactly as it was afterwards.
//
// `window.scrollTo` is NOT a valid probe here: `overflow: hidden` suppresses
// USER scrolling but still permits PROGRAMMATIC scrolling (only `overflow:
// clip` forbids it). A real wheel gesture is the honest test, so that is what
// runs below.

/** The overflow the viewport actually gets: `<html>` wins unless it is
 *  `visible`, in which case `<body>`'s value propagates to the viewport. */
async function effectiveViewportOverflow(page: Page): Promise<string> {
  return page.evaluate(() => {
    const html = getComputedStyle(document.documentElement).overflowY;
    return html === "visible" ? getComputedStyle(document.body).overflowY : html;
  });
}

/** Inline overflow overrides on both candidate elements, both axes. */
async function inlineOverflowState(page: Page) {
  return page.evaluate(() => ({
    htmlOverflow: document.documentElement.style.overflow,
    htmlOverflowY: document.documentElement.style.overflowY,
    bodyOverflow: document.body.style.overflow,
    bodyOverflowY: document.body.style.overflowY,
  }));
}

/** Scroll with a REAL wheel gesture and report where the page ended up. */
async function wheelAndReadScrollY(page: Page): Promise<number> {
  await page.mouse.move(200, 400);
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(200);
  return page.evaluate(() => window.scrollY);
}

test("body scroll is locked on open and fully restored on close", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // AC-6's stated pre-check: Base UI's `ScrollLocker.lock` bails out with a
  // NO-OP restore when the document is ALREADY overflow hidden/clip, which
  // would make every assertion below vacuously true. Prove that is not our
  // state.
  const overflowBefore = await effectiveViewportOverflow(page);
  expect(["hidden", "clip"]).not.toContain(overflowBefore);

  const inlineBefore = await inlineOverflowState(page);

  // Second no-op guard: prove the page is genuinely scrollable to begin with,
  // otherwise "scrolling was prevented" would prove nothing.
  expect(await wheelAndReadScrollY(page)).toBeGreaterThan(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });

  // Locked while open. This is Base UI's `Dialog.Root modal` default (V-2) —
  // Story 53.2 adds NO second lock; this test proves the SHIPPED one actually
  // engages on this surface, rather than covering a reimplementation.
  await expect.poll(() => effectiveViewportOverflow(page)).toBe("hidden");
  // ...and it is real prevention, not just a style: the same wheel gesture that
  // moved the page a moment ago now moves nothing.
  expect(await wheelAndReadScrollY(page)).toBe(0);

  await page.getByTestId("image-viewer-close").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "detached" });

  // Restored. The inline overflow overrides are byte-identical to the pre-open
  // state on BOTH candidate elements. The lock leaves an empty `style=""`
  // attribute behind on <body>; that is cosmetic residue and not an overflow
  // override, so comparing the overflow VALUES is simultaneously stricter about
  // what matters and immune to that.
  await expect.poll(() => inlineOverflowState(page)).toEqual(inlineBefore);
  expect(await effectiveViewportOverflow(page)).toBe(overflowBefore);
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  // ...and scrolling works again.
  expect(await wheelAndReadScrollY(page)).toBeGreaterThan(0);
});
