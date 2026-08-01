// E48.1 (TB-044 follow-up) — fullscreen image viewer containment regression.
//
// Measured root cause (NOT the source image's intrinsic width — that
// hypothesis was tested and disproved; see the spec's Design Notes): the
// Dialog inherits `left: 50%` + `translate: -50%` from `ui/dialog.tsx` while
// this viewer sizes itself in `vw`. `left: 50%` resolves against the
// fixed-position containing block, which mobile Chrome widens to the
// document's scroll width as soon as the page overflows horizontally, while
// `vw` keeps resolving against the visual viewport. Once the two diverge the
// whole dialog — close button included — is displaced past the right edge of
// what the user can see.
//
// The suite still drives genuinely large intrinsic sizes, because the
// neighbouring invariant this file also locks (`max-h-[calc(95dvh-5rem)]`,
// Story 26.1 / TB-044) only means anything against a real 4k/8k source. The
// shared stub in `api-stubs.ts` serves a 1x1 PNG, which cannot express it.
//
// Geometry assertions only — no new snapshot baselines. Runs across the
// standard 4-project matrix, so `mobile-light` / `mobile-dark` cover the
// reported Pixel 5 trap.

import { deflateSync } from "node:zlib";

import type { Locator, Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

// Sub-pixel slack. The fractional offsets come from `vw` arithmetic
// (`1vw` of 393 = 3.93px), not from device pixel ratio. Kept at 1px because
// a genuine failure of this class is off by tens to hundreds of pixels.
const EPSILON_PX = 1;

// Table-free CRC-32. `zlib.crc32` would be the obvious choice but it only
// exists from Node 20.15 / 22.2, while `package.json` declares
// `engines.node >= 20.11`. A lookup table would need an unchecked index read,
// which this repo bans; there is no reason to pay for either, because PNG
// checksums only ever cover the chunk headers and the ALREADY-DEFLATED image
// data (a few KB), never the multi-MB raw scanlines.
function crc32(buf: Buffer): number {
  let c = 0xffffffff;
  for (const byte of buf) {
    c ^= byte;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type: string, data: Buffer): Buffer {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const typed = Buffer.concat([Buffer.from(type, "latin1"), data]);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(typed));
  return Buffer.concat([length, typed, checksum]);
}

/**
 * Minimal 8-bit greyscale PNG encoder. All-zero pixel data deflates to a
 * couple of KB even at 6000x1200, which keeps the fixture cheap while giving
 * the browser a genuine raster image with the requested intrinsic size.
 */
function solidPng(width: number, height: number): Buffer {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 0; // colour type: greyscale
  // Bytes 10-12 stay 0: deflate compression, adaptive filtering, no interlace.
  // One leading filter byte (0 = None) per scanline, then `width` pixel bytes.
  const raw = Buffer.alloc((width + 1) * height);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", deflateSync(raw)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

const EXTREME_WIDE = solidPng(6000, 1200);
const EXTREME_TALL = solidPng(1200, 6000);
const THUMB = solidPng(128, 128);

// Story 53.3 D-4 — the source-geometry matrix `epics.md:4579` names. Each
// size is pinned to the contract it serves rather than to a round number
// (`project-context.md` § "Magic constants ... contract-pointing").
/** 4:1. Wide enough that a Pixel-5-class frame downscales it hard, so
 *  `resolveMaxScale` returns the native-pixel ratio instead of
 *  `BASE_MAX_SCALE` — the branch `zoom.test.ts` covers algebraically, here
 *  exercised through real layout. */
const PANORAMA_4_1 = solidPng(4000, 1000);
/** 8:1 — the inspectability case `FR26-VIEW-1` exists for, and the widest
 *  thing the `max-h-[calc(95dvh-5rem)]` cap must survive in LANDSCAPE, where
 *  the vertical budget is scarcest. */
const PANORAMA_8_1 = solidPng(8000, 1000);
/** 1:4 — the complementary axis: the HEIGHT cap, not the width cap, is what
 *  must contain this one. Kept distinct from `EXTREME_TALL` (1200x6000 = 1:5)
 *  rather than reusing it, because the epic names 1:4 literally and an
 *  all-zero greyscale fixture deflates to a few KB. */
const PORTRAIT_1_4 = solidPng(1000, 4000);
/** Smaller than the rendered frame in every project. Proves `resolveMaxScale`
 *  falls back to `BASE_MAX_SCALE` rather than to a sub-1 ratio, so the three
 *  zoom controls are not dead — the case 53.2's `max(4, ratio)` reading was
 *  chosen to protect. */
const SMALL_SOURCE = solidPng(120, 90);

/** `zoom.ts`'s `BASE_MAX_SCALE`. Restated rather than imported: this is a
 *  Playwright spec asserting the SHIPPED envelope, and importing the constant
 *  would make a test that silently follows the value it is meant to pin. */
const BASE_MAX_SCALE = 4;

// `{spacing.target-fullscreen-close}` — `DESIGN.md:180, :287`;
// `EXPERIENCE.md:302`; WCAG 2.2 SC 2.5.8.
const CLOSE_TARGET_MIN_PX = 44;
// Device-scale-factor rounding on the Pixel 5 projects.
const TARGET_EPSILON_PX = 0.5;

// Mobile Chrome expands the *layout* viewport (the containing block for
// `position: fixed`) to the document's scroll width as soon as the page
// overflows horizontally, while `vw` units keep resolving against the
// *visual* viewport. Any page-level overflow therefore de-centers a dialog
// positioned with `left: 50%` + `translate: -50%` + a `vw` width. This
// injects that state deterministically instead of depending on whichever
// element happens to overflow the real catalog page at a given width.
async function forceHorizontalPageOverflow(page: Page) {
  await page.addStyleTag({
    content:
      "body::after { content: ''; display: block; width: calc(100vw + 200px); height: 1px; }",
  });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      ),
    )
    .toBe(true);
}

// ── Story 53.3 (E53 / FR26-VIEW-1, NFR26-A11Y-1, NFR26-VISUAL-1) ──────────
// AC-2 / AC-3 / AC-4 extend this suite ADDITIVELY. Story D-3 puts the
// source-geometry x orientation matrix HERE rather than in a new spec file
// because every helper above (`solidPng`, `openViewerWith`, `boxOf`,
// `assertContained`, `assertDismissible`, ...) is file-local and unexported:
// a new file would have to duplicate ~130 lines of PNG encoder plus geometry
// assertions, which is the exact wheel-reinvention this story exists to
// prevent. The four tests below the helpers keep their bodies byte-identical,
// `openViewerWith` gained one OPTIONAL parameter defaulting to today's
// behaviour, and the suite still produces NO snapshots.

/**
 * Landscape by AXIS SWAP of the project's own viewport (D-2). Deliberately no
 * literal dimensions: a landscape Pixel 5 is defined by Playwright's own
 * `devices["Pixel 5"]` descriptor, which is Playwright's to change on any
 * upgrade, so a hard-coded `851 x 393` would rot silently. The same helper
 * therefore expresses both "opened in landscape" and "rotated while open".
 *
 * `setViewportSize` fires `resize`; it does NOT fire `orientationchange`
 * (story V-5). The viewer registers BOTH listeners; the second one is covered
 * in `ImageFullscreenViewer.test.tsx`, because synthesising an
 * `orientationchange` here would prove the listener is wired, not that a
 * rotation refits.
 */
async function rotate(page: Page) {
  const vp = page.viewportSize();
  if (vp === null) throw new Error("no viewport to rotate");
  await page.setViewportSize({ width: vp.height, height: vp.width });
  // `setViewportSize` resolves before the page has necessarily re-laid-out and
  // run the viewer's own `resize` handler, and every geometry assertion after a
  // rotation depends on that having happened.
  await expect.poll(() => page.evaluate(() => window.innerWidth)).toBe(vp.height);
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve(null))),
      ),
  );
}

async function openViewerWith(
  page: Page,
  full: Buffer,
  opts: { overflow?: boolean; scrollX?: number; landscape?: boolean } = {},
) {
  // Two images are intentional: they make the h-20 thumbnail strip, counter,
  // chevrons and the `95dvh - 5rem` main-frame budget part of every assertion.
  await stubSotDetail(page, { imageCount: 2 });
  // Registered AFTER `stubSotDetail` so it wins: Playwright matches route
  // handlers in reverse registration order.
  await page.route("**/api/models/**/files/**/content**", (route: Route) => {
    const variant = new URL(route.request().url()).searchParams.get("variant");
    return route.fulfill({
      status: 200,
      contentType: "image/png",
      body: variant === "full" ? full : THUMB,
    });
  });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  // Story 53.3 D-2 — opt-in landscape. Defaults to today's behaviour, so the
  // three call sites above are untouched (AC-9).
  if (opts.landscape === true) await rotate(page);
  if (opts.overflow === true) await forceHorizontalPageOverflow(page);
  if ((opts.scrollX ?? 0) > 0) {
    await page.evaluate((x) => window.scrollTo({ left: x, behavior: "instant" }), opts.scrollX);
    await expect.poll(() => page.evaluate(() => window.scrollX)).toBeGreaterThan(0);
  }
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  // Layout only reflects the real intrinsic size once the source is decoded;
  // before that the <img> is a 0x0 placeholder and would pass trivially.
  await expect
    .poll(() =>
      page
        .getByTestId("image-viewer-frame")
        .locator("img")
        .evaluate((el: HTMLImageElement) => el.naturalWidth),
    )
    .toBeGreaterThan(0);
}

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Read the rect in-page rather than via `locator.boundingBox()`: the latter
// reports page-relative coordinates, which drift from `clientWidth` once the
// page is scrollable or scaled. Containment must be judged in one coordinate
// space — the same one the viewport dimensions are read in.
async function boxOf(page: Page, selector: string): Promise<Box> {
  const box = await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (el === null) return null;
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, width: r.width, height: r.height };
  }, selector);
  expect(box, `${selector} has no bounding box`).not.toBeNull();
  return box as Box;
}

// Story 53.4 D-4: `expectWithinViewport` (a 0-origin box test against
// `clientWidth`/`clientHeight`) was removed rather than left standing. Its two
// call sites now use `expectWithinVisibleRegion`, which takes the visible
// region's ORIGIN as well as its size — `visualViewport.offsetLeft/offsetTop`
// are non-zero whenever the user has panned a zoomed page, so a 0-origin test
// cannot express containment in that state at all.

function expectContainedBy(label: string, inner: Box, outer: Box) {
  expect(inner.x, `${label} left edge`).toBeGreaterThanOrEqual(outer.x - EPSILON_PX);
  expect(inner.y, `${label} top edge`).toBeGreaterThanOrEqual(outer.y - EPSILON_PX);
  expect(inner.x + inner.width, `${label} right edge`).toBeLessThanOrEqual(
    outer.x + outer.width + EPSILON_PX,
  );
  expect(inner.y + inner.height, `${label} bottom edge`).toBeLessThanOrEqual(
    outer.y + outer.height + EPSILON_PX,
  );
}

const TOOLBAR_SELECTOR = '[data-testid="image-viewer-toolbar"]';

/**
 * The region the user can actually see, in the same coordinate space
 * `getBoundingClientRect()` reports.
 *
 * `window.visualViewport` is the ONLY API that reports it. Everything else in
 * this file used to assume otherwise; Story 53.4 measured the assumption and
 * it is false. On `mobile-light` with the page scale factor at 2:
 *
 *   visualViewport.width = 196.5
 *   documentElement.clientWidth = innerWidth = used `100vw` = fixed `100%` = 393
 *
 * All four of the non-`visualViewport` metrics report the LAYOUT viewport, and
 * the layout viewport is the very box the dialog is sized from — so measuring
 * the dialog against it can never fail, whatever the page scale. See the
 * contract correction at `assertContained`.
 */
async function visibleRegion(page: Page): Promise<Box> {
  return page.evaluate(() => {
    const vv = window.visualViewport;
    if (vv === null || vv === undefined) {
      // No `visualViewport` (older engines): the layout viewport is then the
      // best available answer AND the two cannot diverge, so this is exact.
      return {
        x: 0,
        y: 0,
        width: document.documentElement.clientWidth,
        height: document.documentElement.clientHeight,
      };
    }
    return { x: vv.offsetLeft, y: vv.offsetTop, width: vv.width, height: vv.height };
  });
}

/** THE CONTRACT, stated once: no part of the named box may extend beyond the
 *  region the user can see. Deliberately not "the right edge equals X" — the
 *  numbers are the environment's, the containment is the promise (D-3). */
function expectWithinVisibleRegion(label: string, box: Box, region: Box) {
  expect(box.x, `${label} left edge is inside what the user can see`).toBeGreaterThanOrEqual(
    region.x - EPSILON_PX,
  );
  expect(box.y, `${label} top edge is inside what the user can see`).toBeGreaterThanOrEqual(
    region.y - EPSILON_PX,
  );
  expect(
    box.x + box.width,
    `${label} right edge is inside what the user can see`,
  ).toBeLessThanOrEqual(region.x + region.width + EPSILON_PX);
  expect(
    box.y + box.height,
    `${label} bottom edge is inside what the user can see`,
  ).toBeLessThanOrEqual(region.y + region.height + EPSILON_PX);
}

async function assertContained(page: Page, opts: { overflow?: boolean } = {}) {
  // ── Story 53.4 D-4 CONTRACT CORRECTION (measured, not assumed) ──────────
  // This helper used to read the reference box from
  // `document.documentElement.clientWidth/Height`, on the premise — stated in
  // the comment that stood here — that "`clientWidth` tracks the VISUAL
  // viewport; `innerWidth` tracks the layout viewport". BOTH halves are false,
  // measured on `mobile-light` this run:
  //
  //   page scale 2:      visualViewport.width 196.5 | clientWidth 393 | innerWidth 393
  //   page overflow:     visualViewport.width 393   | clientWidth 393 | innerWidth 593
  //
  // `clientWidth` never reported the visual viewport, and `innerWidth` is
  // neither metric reliably. Because `vw` also resolves against the layout
  // viewport, asserting the viewer's `98vw`-sized box against `clientWidth`
  // compared it to the box it was derived from — vacuously true at every page
  // scale, which is mechanically why this suite stayed green through the
  // shipped defect (AC-3). The reference box is now the visible region.
  const region = await visibleRegion(page);
  const { scrollWidth, layoutWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    layoutWidth: document.documentElement.clientWidth,
  }));

  const dialog = await boxOf(page, '[data-slot="dialog-content"]');
  const root = await boxOf(page, '[data-testid="image-viewer-root"]');
  const frame = await boxOf(page, '[data-testid="image-viewer-frame"]');
  const image = await boxOf(page, '[data-testid="image-viewer-frame"] img');
  const close = await boxOf(page, '[data-testid="image-viewer-close"]');

  expectWithinVisibleRegion("dialog", dialog, region);
  expect(dialog.width, "dialog preserves fullscreen coverage").toBeGreaterThanOrEqual(
    region.width * 0.9,
  );
  expectWithinVisibleRegion("viewer root", root, region);
  expectWithinVisibleRegion("close button", close, region);
  expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);
  expectContainedBy("image", image, frame);
  await expect(page.getByTestId("image-viewer-strip")).toBeVisible();
  await expect(page.getByTestId("image-viewer-counter")).toBeVisible();
  await expect(page.getByTestId("image-viewer-prev")).toBeVisible();
  await expect(page.getByTestId("image-viewer-next")).toBeVisible();
  await expect(page.getByTestId("image-viewer-thumb")).toHaveCount(2);
  // The viewer must not itself add a horizontal scroll region. `scrollWidth` is
  // a LAYOUT-viewport-space quantity, so this one keeps `clientWidth` as its
  // reference — that pairing was always correct and is not part of the D-4
  // correction above. Skipped when a test deliberately injected page overflow —
  // there the overflow is the input.
  if (opts.overflow !== true) expect(scrollWidth).toBeLessThanOrEqual(layoutWidth + EPSILON_PX);
}

async function assertDismissible(page: Page) {
  // The close control must not merely be geometrically inside the viewport:
  // it must be hittable and actually dismiss the viewer.
  await expect(page.getByTestId("image-viewer-close")).toBeVisible();
  await page.getByTestId("image-viewer-close").click();
  await expect(page.getByTestId("image-viewer-root")).toHaveCount(0);
}

test("fullscreen viewer contains an extreme-wide source and keeps close in viewport", async ({
  page,
}) => {
  await openViewerWith(page, EXTREME_WIDE);
  await assertContained(page);
  await assertDismissible(page);
});

test("fullscreen viewer contains an extreme-portrait source and keeps close in viewport", async ({
  page,
}) => {
  await openViewerWith(page, EXTREME_TALL);
  await assertContained(page);
  await assertDismissible(page);
});

// The reported trap: a horizontally overflowing page widens the layout
// viewport, the dialog's percentage-based centering resolves against it while
// its width resolves against the visual viewport, and the whole viewer — close
// button included — is displaced past the right edge of what the user can see.
test("fullscreen viewer stays reachable when the page overflows horizontally", async ({
  page,
}) => {
  await openViewerWith(page, EXTREME_WIDE, { overflow: true });
  await assertContained(page, { overflow: true });
  await assertDismissible(page);
});

test("fullscreen viewer remains reachable from a horizontally scrolled page", async ({ page }, testInfo) => {
  // Pixel 5 emulation exposes a wider layout viewport but clamps root scrollX
  // to zero (matching mobile Chrome). Desktop Chromium permits an actual root
  // horizontal scroll, so it owns this complementary geometry check.
  test.skip(testInfo.project.name.startsWith("mobile-"), "mobile root scrollX is clamped to zero");

  await openViewerWith(page, EXTREME_WIDE, { overflow: true, scrollX: 100 });
  await assertContained(page, { overflow: true });

  const secondThumb = page.getByTestId("image-viewer-thumb").nth(1);
  await page.getByTestId("image-viewer-next").click();
  await expect(secondThumb).toHaveAttribute("aria-current", "true");
  await assertDismissible(page);
});

// ══ Story 53.3 — AC-2 / AC-3 / AC-4 ═══════════════════════════════════════
// Everything below is NEW. Nothing above this line changed except
// `openViewerWith`'s optional `landscape` parameter (AC-9).

// The toolbar is scoped on every lookup: `playwright.config.ts` forces
// `pl-PL`, so the matchers below are the literal pl.json strings, and
// `catalog.image_viewer.zoom_in` is "Powiększ". The gallery trigger's
// `catalog.image_viewer.trigger_label` used to be "Powiększ" too (53.2 D-8's
// recorded collision); Story 54.1 closed it by changing that key's Polish
// value to "Otwórz na pełnym ekranie", so the scoping no longer separates
// those two. It stays because these assertions are about the TOOLBAR's
// controls, and another same-name surface already exists today
// (`viewer3d.tooltip.expand`), so an unscoped name lookup would silently widen
// the assertion.
const toolbar = (page: Page) => page.getByTestId("image-viewer-toolbar");
const zoomInControl = (page: Page) => toolbar(page).getByRole("button", { name: "Powiększ" });
const zoomOutControl = (page: Page) => toolbar(page).getByRole("button", { name: "Pomniejsz" });
const zoomResetControl = (page: Page) => toolbar(page).getByRole("button", { name: "Dopasuj" });

/** Wait until the image has actually resolved, which is what arms the three
 *  zoom controls. `openViewerWith` already polls `naturalWidth`, but that is
 *  the browser's view; this is React's. */
async function waitForZoomable(page: Page) {
  await expect(zoomInControl(page)).toBeEnabled();
}

/** The transform layer's live matrix. `scale` is the uniform scale factor and
 *  `x`/`y` the committed pan, read in the same coordinate space the clamp
 *  arithmetic works in. `translate3d(...)` computes to a `matrix3d`, which
 *  `DOMMatrixReadOnly` normalises for us. */
async function transformOf(page: Page): Promise<{ scale: number; x: number; y: number }> {
  return page.evaluate(() => {
    const el = document.querySelector('[data-testid="image-viewer-transform"]');
    if (el === null) throw new Error("no transform layer");
    const m = new DOMMatrixReadOnly(getComputedStyle(el).transform);
    return { scale: m.a, x: m.e, y: m.f };
  });
}

/**
 * A single-finger drag on the viewer root — the shipped pan gesture, driven
 * through the same handler a phone reaches. `TouchEvent`'s touch lists accept
 * ONLY real `Touch` instances; Chromium rejects plain object literals outright
 * ("Failed to convert value to 'Touch'"), and `new Touch({...})` additionally
 * requires `identifier` and `target` (53.2 D-9).
 */
async function panBy(page: Page, dx: number, dy: number) {
  const frame = await boxOf(page, '[data-testid="image-viewer-frame"]');
  await page.evaluate(
    ({ sx, sy, ex, ey }) => {
      const root = document.querySelector('[data-testid="image-viewer-root"]');
      if (root === null) throw new Error("no viewer root");
      const at = (x: number, y: number) =>
        new Touch({ identifier: 1, target: root, clientX: x, clientY: y });
      const fire = (type: string, touch: Touch, remaining: Touch[]) =>
        root.dispatchEvent(
          new TouchEvent(type, {
            bubbles: true,
            touches: remaining,
            targetTouches: remaining,
            changedTouches: [touch],
          }),
        );
      const start = at(sx, sy);
      fire("touchstart", start, [start]);
      // Two moves, so the drag passes TAP_MOVE_TOLERANCE_PX and is committed
      // as a pan rather than being released as a tap.
      const mid = at((sx + ex) / 2, (sy + ey) / 2);
      fire("touchmove", mid, [mid]);
      const end = at(ex, ey);
      fire("touchmove", end, [end]);
      fire("touchend", end, []);
    },
    {
      sx: frame.x + frame.width / 2,
      sy: frame.y + frame.height / 2,
      ex: frame.x + frame.width / 2 + dx,
      ey: frame.y + frame.height / 2 + dy,
    },
  );
}

/**
 * `clampPan`'s postcondition expressed in MEASURED pixels (AC-4). On each
 * axis: either the scaled image is smaller than the frame, in which case the
 * pan is pinned to 0, or it is larger, in which case it must fully COVER the
 * frame — no image edge may ever sit inside the corresponding frame edge.
 *
 * This is the half `zoom.test.ts` cannot do. That suite constrains the same
 * algebra against INJECTED geometry (V-11); what only a real browser can show
 * is that the component feeds it real measurements.
 */
async function assertPanClamped(page: Page) {
  const frame = await boxOf(page, '[data-testid="image-viewer-frame"]');
  const image = await boxOf(page, '[data-testid="image-viewer-frame"] img');
  const pan = await transformOf(page);

  if (image.width >= frame.width - EPSILON_PX) {
    expect(image.x, "image left edge must not detach from the frame").toBeLessThanOrEqual(
      frame.x + EPSILON_PX,
    );
    expect(
      image.x + image.width,
      "image right edge must not detach from the frame",
    ).toBeGreaterThanOrEqual(frame.x + frame.width - EPSILON_PX);
  } else {
    expect(pan.x, "pan is pinned on an axis the image does not overflow").toBeCloseTo(0, 1);
  }

  if (image.height >= frame.height - EPSILON_PX) {
    expect(image.y, "image top edge must not detach from the frame").toBeLessThanOrEqual(
      frame.y + EPSILON_PX,
    );
    expect(
      image.y + image.height,
      "image bottom edge must not detach from the frame",
    ).toBeGreaterThanOrEqual(frame.y + frame.height - EPSILON_PX);
  } else {
    expect(pan.y, "pan is pinned on an axis the image does not overflow").toBeCloseTo(0, 1);
  }
}

/**
 * Containment while the image is deliberately ZOOMED.
 *
 * `assertContained` additionally asserts the image sits inside its frame,
 * which is only true at fit scale: a zoomed image legitimately overflows the
 * frame and is clipped by the frame's own `overflow-hidden`. What must hold at
 * EVERY zoom level is the other half — the viewer's own boxes stay inside the
 * visual viewport and the viewer adds no document overflow.
 */
async function assertChromeContained(page: Page) {
  // Same Story 53.4 D-4 contract correction as `assertContained`: the
  // reference box is the region the user can see, not the layout viewport the
  // geometry is derived from.
  const region = await visibleRegion(page);
  const { scrollWidth, layoutWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    layoutWidth: document.documentElement.clientWidth,
  }));

  expectWithinVisibleRegion("dialog", await boxOf(page, '[data-slot="dialog-content"]'), region);
  expectWithinVisibleRegion(
    "viewer root",
    await boxOf(page, '[data-testid="image-viewer-root"]'),
    region,
  );
  expectWithinVisibleRegion(
    "frame",
    await boxOf(page, '[data-testid="image-viewer-frame"]'),
    region,
  );
  expectWithinVisibleRegion(
    "close button",
    await boxOf(page, '[data-testid="image-viewer-close"]'),
    region,
  );
  expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);
  await expect(page.getByTestId("image-viewer-strip")).toBeVisible();
  await expect(page.getByTestId("image-viewer-counter")).toBeVisible();
  await expect(page.getByTestId("image-viewer-prev")).toBeVisible();
  await expect(page.getByTestId("image-viewer-next")).toBeVisible();
  await expect(page.getByTestId("image-viewer-toolbar")).toBeVisible();
  expect(scrollWidth, "the viewer adds no horizontal document overflow").toBeLessThanOrEqual(
    layoutWidth + EPSILON_PX,
  );
}

/** The close control must not merely be inside the viewport (which
 *  `assertContained` already proves) — it must be big enough to hit. */
async function assertCloseTargetFloor(page: Page) {
  const close = await boxOf(page, '[data-testid="image-viewer-close"]');
  expect(close.width, "close target width").toBeGreaterThanOrEqual(
    CLOSE_TARGET_MIN_PX - TARGET_EPSILON_PX,
  );
  expect(close.height, "close target height").toBeGreaterThanOrEqual(
    CLOSE_TARGET_MIN_PX - TARGET_EPSILON_PX,
  );
}

/** Press Zoom In until it disables itself, and report the scale it stopped at. */
async function driveToCeiling(page: Page): Promise<number> {
  for (let i = 0; i < 25; i += 1) {
    if (await zoomInControl(page).isDisabled()) break;
    await zoomInControl(page).click();
  }
  await expect(zoomInControl(page)).toBeDisabled();
  return (await transformOf(page)).scale;
}

// ── AC-2: the source-geometry matrix, both orientations ───────────────────
// Placement in `tests/visual/` is what discharges `epics.md:4579`'s "light
// AND dark" and "Pixel 5" for free: the 4-project matrix is fixed
// (`project-context.md:110`) and every spec here runs on all four unless it
// self-skips. There is deliberately NO colour-scheme loop and NO fifth
// project (V-3).

const GEOMETRY_MATRIX = [
  { label: "panorama 4:1", png: PANORAMA_4_1 },
  { label: "panorama 8:1", png: PANORAMA_8_1 },
  { label: "portrait 1:4", png: PORTRAIT_1_4 },
  { label: "small source", png: SMALL_SOURCE },
] as const;

for (const { label, png } of GEOMETRY_MATRIX) {
  test(`viewer contains a ${label} source in portrait`, async ({ page }) => {
    await openViewerWith(page, png);
    await assertContained(page);
    await assertCloseTargetFloor(page);
    await assertDismissible(page);
  });

  test(`viewer contains a ${label} source in landscape`, async ({ page }, testInfo) => {
    // D-2: rotating a DESKTOP Chrome window is not a phone rotation and would
    // assert nothing about `epics.md:4579`'s "Pixel 5 landscape". Same skip
    // idiom as the horizontally-scrolled test above.
    test.skip(
      !testInfo.project.name.startsWith("mobile-"),
      "landscape is a phone-only case (D-2)",
    );

    await openViewerWith(page, png, { landscape: true });
    await assertContained(page);
    await assertCloseTargetFloor(page);
    await assertDismissible(page);
  });
}

// ── AC-3: rotation refit ──────────────────────────────────────────────────

test("rotation refits without clipping and preserves the user's zoom", async ({
  page,
}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith("mobile-"), "rotation is a phone-only case (D-2)");

  await openViewerWith(page, PANORAMA_8_1);
  await waitForZoomable(page);

  // Zoom above 1.0 AND pan off-centre, so the refit has something to preserve
  // and something to re-clamp. A rotation test at pan {0,0} would pass against
  // a refit that silently drops the pan.
  await zoomInControl(page).click();
  await zoomInControl(page).click();
  // Wait for the zoom to be COMMITTED before dragging. A drag at scale 1.0 is
  // a deliberate no-op (`onTouchMove` bails on `scaleRef.current <=
  // MIN_SCALE`), so panning against an uncommitted zoom silently yields a zero
  // pan and makes the whole rotation assertion vacuous — measured as exactly
  // that, intermittently, under `fullyParallel` load.
  await expect
    .poll(async () => (await transformOf(page)).scale, {
      message: "zoom committed before panning",
    })
    .toBeGreaterThan(1);
  // The gesture is inside the poll on purpose: each drag is relative to the
  // pan it starts from, so a retry converges on the clamp rather than
  // fighting it, and the precondition is OBSERVED rather than assumed.
  await expect
    .poll(
      async () => {
        await panBy(page, -200, 0);
        return Math.abs((await transformOf(page)).x);
      },
      { message: "panned off-centre before rotating" },
    )
    .toBeGreaterThan(0);
  const portrait = await transformOf(page);
  expect(portrait.scale, "zoomed above 1.0 before rotating").toBeGreaterThan(1);

  await rotate(page);

  // `EXPERIENCE.md:262` — the zoom LEVEL survives the rotation...
  const landscape = await transformOf(page);
  expect(landscape.scale, "zoom level preserved across rotation").toBeCloseTo(portrait.scale, 2);
  // ...the pan is re-clamped against the new geometry...
  await assertPanClamped(page);
  // ...and every control stays inside the visual viewport with no document
  // overflow. `assertChromeContained`, not `assertContained`: the image is
  // deliberately zoomed here, so it SHOULD overflow its frame and be clipped.
  await assertChromeContained(page);
  await assertCloseTargetFloor(page);

  // The return trip is the failure this actually pins: a one-way refit that
  // strands the image when the phone rotates back is still a broken refit.
  await rotate(page);
  const backToPortrait = await transformOf(page);
  expect(backToPortrait.scale, "zoom level preserved on the return trip").toBeCloseTo(
    portrait.scale,
    2,
  );
  await assertPanClamped(page);
  await assertChromeContained(page);
  // The 44x44 floor is re-measured after the RETURN rotation too, not only
  // after the outbound one: a refit that survives one axis swap and shrinks
  // the close target on the way back is still a broken refit (AC-2's floor
  // applies at every geometry this test visits).
  await assertCloseTargetFloor(page);

  // Back at fit scale the STRICTER containment applies again, which is what
  // proves the two rotations left no residue in the layout.
  await zoomResetControl(page).click();
  await assertContained(page);
  await assertDismissible(page);
});

// ── AC-4: clamp and reset, measured at real layout ────────────────────────

test("pan is pinned at 1.0, clamped when zoomed, and reset returns to exactly 1.0", async ({
  page,
}) => {
  await openViewerWith(page, PANORAMA_4_1);
  await waitForZoomable(page);

  // At 1.0 the image fits the frame on both axes, so no drag may move it.
  //
  // What this pins EXACTLY: `onTouchMove` returns before setting
  // `gestureMovedRef` while `scale <= MIN_SCALE` (`ImageFullscreenViewer.tsx`),
  // so the release is classified by `touchend` alone — and with |dy| = 200 well
  // past `SWIPE_VERTICAL_TOLERANCE_PX` (60) it takes the vertical-scroll bail.
  // So this is the "a drag at fit scale moves nothing and navigates nothing"
  // contract, NOT a `clampPan` assertion; the clamp arithmetic is pinned by the
  // zoomed cases below. The counter check is what keeps the second half honest:
  // without it a regression that navigated instead of no-op'ing would still see
  // a zeroed transform on the newly-selected image and pass.
  const counter = page.getByTestId("image-viewer-counter");
  const counterBefore = await counter.textContent();
  await panBy(page, -300, -200);
  const rest = await transformOf(page);
  expect(rest.scale, "still at fit scale").toBe(1);
  expect(rest.x, "pan pinned at scale 1.0").toBe(0);
  expect(rest.y, "pan pinned at scale 1.0").toBe(0);
  expect(await counter.textContent(), "a drag at fit scale navigated nothing").toBe(counterBefore);

  await zoomInControl(page).click();
  await zoomInControl(page).click();
  // Same reason as the rotation test: a drag at scale 1.0 is a no-op, so the
  // zoom has to be observed as committed or the clamp assertions below become
  // assertions about an unzoomed image.
  await expect
    .poll(async () => (await transformOf(page)).scale, {
      message: "zoom committed before panning",
    })
    .toBeGreaterThan(1);

  // Drag far past anything the clamp can allow, in both directions.
  for (const [dx, dy] of [
    [-4000, -4000],
    [4000, 4000],
  ] as const) {
    await panBy(page, dx, dy);
    await assertPanClamped(page);
  }

  // A zoom-OUT must re-clamp: the envelope shrinks under a pan that was legal
  // a moment ago, and the image may not stay detached from an edge.
  await zoomOutControl(page).click();
  await assertPanClamped(page);

  // Reset returns to EXACTLY 1.0 with pan {0,0} — not "approximately".
  await zoomResetControl(page).click();
  const afterReset = await transformOf(page);
  expect(afterReset.scale, "Reset returns to exactly 1.0").toBe(1);
  expect(afterReset.x, "Reset drops the pan").toBe(0);
  expect(afterReset.y, "Reset drops the pan").toBe(0);
  await expect(zoomOutControl(page)).toBeDisabled();
  await expect(zoomResetControl(page)).toBeDisabled();
  await assertContained(page);
});

test("the zoom ceiling is measured from the source, not fixed at the default envelope", async ({
  page,
}) => {
  // `resolveMaxScale` = `max(BASE_MAX_SCALE, naturalWidth / renderedWidth)`.
  // `zoom.test.ts` constrains that algebra against INJECTED numbers; what only
  // a real browser can show is that the component feeds it REAL measurements,
  // i.e. that a panorama and a postage stamp end up with DIFFERENT ceilings.
  await openViewerWith(page, PANORAMA_8_1);
  await waitForZoomable(page);
  const panoramaCeiling = await driveToCeiling(page);
  const expectedPanorama = await page.evaluate(() => {
    const img = document.querySelector('[data-testid="image-viewer-frame"] img');
    if (!(img instanceof HTMLImageElement)) throw new Error("no rendered image");
    return Math.max(4, img.naturalWidth / img.offsetWidth);
  });
  expect(panoramaCeiling).toBeCloseTo(expectedPanorama, 2);
  expect(panoramaCeiling, "a panorama earns more than the default envelope").toBeGreaterThan(
    BASE_MAX_SCALE,
  );
  await assertPanClamped(page);

  // The small source is the complementary half: below one image-pixel per
  // CSS-pixel the ceiling must NOT fall below the default envelope, or the
  // three controls would be dead on a small photo.
  await openViewerWith(page, SMALL_SOURCE);
  await waitForZoomable(page);
  expect(await driveToCeiling(page), "small source keeps the default envelope").toBeCloseTo(
    BASE_MAX_SCALE,
    5,
  );
});

// ══ Story 53.4 — AC-1 / AC-2 / AC-3 ═══════════════════════════════════════
// The shipped Android/Brave fit-to-frame defect, pinned.
//
// THE CONDITION, measured rather than guessed (AC-1). The viewer's geometry is
// expressed entirely in viewport-relative CSS — `w-[98vw]`, `left-[1vw]`,
// `max-w-[calc(100%-2vw)]`, `h-[95dvh]`, `top-[2.5dvh]` — and `position:
// fixed` lays the dialog out in the same box those units resolve against: the
// LAYOUT viewport. Whenever the VISUAL viewport is narrower than the layout
// viewport, the dialog is therefore sized and anchored to a box the user
// cannot see all of, and its right-hand part — photo AND centred toolbar — is
// off-screen. Measured on `mobile-light` at page scale 2, before the repair:
//
//   visualViewport.width 196.5 | clientWidth 393 | innerWidth 393 | 100vw 393
//   dialog  3.92 -> 389.05   (overflows what the user can see by 192.55px)
//   toolbar 124.48 -> 268.48 (centre 196.48; the cut at 196.5 lands inside the
//                             `-` button, which is exactly what the operator's
//                             device screenshot shows)
//
// WHY THE PAGE SCALE FACTOR IS THE RIGHT STAND-IN. A real phone reaches this
// state by pinch-zooming the page — which `EXPERIENCE.md:291` /
// `architecture.md:3374` REQUIRE to stay available, since `user-scalable=no`
// is banned. Playwright cannot pinch, but the visual-viewport-narrower-than-
// layout-viewport relation IS the defect condition, and CDP's page scale
// factor produces exactly that relation deterministically. The repair is
// anchored to the relation, not to any one cause of it.
//
// WHY THE STANDING SUITE COULD NOT SEE THIS (AC-3) — three separate reasons,
// each measured this run, none of them "we were missing an overflow test":
//   1. The horizontal-overflow case above ALREADY exists and is green. It
//      grows `innerWidth`/`scrollWidth` to 593 and leaves clientWidth,
//      visualViewport.width and `100vw` all at 393 — it never produces a
//      visual-viewport divergence at all, so it cannot express this class.
//   2. Every containment assertion measured against
//      `documentElement.clientWidth`, which reports the LAYOUT viewport — the
//      same box `98vw` is a percentage of. `1vw + 98vw <= clientWidth` is true
//      by construction at every page scale. The assertion was vacuous, not
//      absent (D-4 contract correction applied above).
//   3. Nothing in the repo consulted `window.visualViewport`, and it is the
//      only API that reports the visible region — so the contract was not
//      expressible in the terms the suite was written in.
/** The viewer re-reads the visible region from a `visualViewport` event; give
 *  the committed layout a frame to settle before measuring it. */
async function settleTwoFrames(page: Page) {
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve(null))),
      ),
  );
}

async function setPageScale(page: Page, factor: number) {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Emulation.setPageScaleFactor", { pageScaleFactor: factor });
  await expect
    .poll(() => page.evaluate(() => window.visualViewport?.scale ?? 1), {
      message: "page scale factor applied",
    })
    .toBeCloseTo(factor, 1);
  await settleTwoFrames(page);
}

// PANNING the scaled page — the other half of the condition, and the half the
// two tests above cannot reach. At page scale alone the visible region's ORIGIN
// stays at `0,0`, so `visualViewport.offsetLeft`/`.offsetTop` — the terms the
// viewer adds to `--viewer-left`/`--viewer-top` — are multiplied by nothing and
// a 0-origin implementation would pass. A pinched phone is panned constantly,
// which moves the visible region WITHOUT resizing it; this is the state the
// removed `expectWithinViewport` helper could not express at all (D-4).
//
// Same caveat class as the page-scale factor itself, stated rather than
// glossed: Playwright cannot pan by touch — the touch gesture is consumed by
// the page — so the pan is synthesized as a WHEEL gesture. With the viewer open
// the document cannot scroll (body scroll is locked), so the scroll chains to
// the visual viewport, which is exactly the state a device pan produces. The
// equivalence claimed is GEOMETRIC, not behavioural.
const PAN_ORIGIN_PX = 100;
/** Fast enough that the gesture completes well inside a test, slow enough that
 *  Chromium does not coalesce it into a fling with momentum after the command
 *  returns — the measurement must be taken against a settled origin. */
const PAN_SPEED_PX_PER_S = 8000;

async function panVisibleRegion(page: Page, dx: number, dy: number) {
  const cdp = await page.context().newCDPSession(page);
  // Negative distance scrolls the content the other way, i.e. moves the visible
  // region towards positive `offsetLeft`/`offsetTop`.
  await cdp.send("Input.synthesizeScrollGesture", {
    x: PAN_ORIGIN_PX,
    y: PAN_ORIGIN_PX,
    xDistance: -dx,
    yDistance: -dy,
    gestureSourceType: "mouse",
    speed: PAN_SPEED_PX_PER_S,
  });
  // BOTH axes, not their sum (2026-08-01, `bmad-code-review` re-run #2 NB-2):
  // the test below hard-asserts `region.x > 0` AND `region.y > 0` with no retry,
  // so a poll on `offsetLeft + offsetTop` would let the gesture settle on one
  // axis and race the other. `Math.min` is the same one-line shape and gates on
  // the slower of the two.
  await expect
    .poll(
      () =>
        page.evaluate(() =>
          Math.min(window.visualViewport?.offsetLeft ?? 0, window.visualViewport?.offsetTop ?? 0),
        ),
      { message: "visible region panned away from the layout viewport's origin on BOTH axes" },
    )
    .toBeGreaterThan(0);
  await settleTwoFrames(page);
}

for (const factor of [1.5, 2] as const) {
  test(`the viewer fits the region the user can see when the visual viewport is ${factor}x narrower than the layout viewport`, async ({
    page,
  }) => {
    await openViewerWith(page, PANORAMA_8_1);
    await setPageScale(page, factor);

    // Reset / minimum scale, before any zoom — the state the defect report is
    // about. Asserted, not assumed (SCP 2.1 could not read it off a photo).
    expect((await transformOf(page)).scale, "still at the fit floor").toBe(1);

    const region = await visibleRegion(page);
    expect(
      region.width,
      "precondition: the visible region really is narrower than the layout viewport",
    ).toBeLessThan(await page.evaluate(() => document.documentElement.clientWidth));

    // THE CONTRACT: no part of the viewer box extends beyond the region the
    // user can see, at reset scale. Not "the right edge equals X" — these are
    // the boxes the operator could not reach on the device.
    expectWithinVisibleRegion("dialog", await boxOf(page, '[data-slot="dialog-content"]'), region);
    expectWithinVisibleRegion(
      "viewer root",
      await boxOf(page, '[data-testid="image-viewer-root"]'),
      region,
    );
    expectWithinVisibleRegion(
      "photo",
      await boxOf(page, '[data-testid="image-viewer-frame"] img'),
      region,
    );
    expectWithinVisibleRegion(
      "close button",
      await boxOf(page, '[data-testid="image-viewer-close"]'),
      region,
    );
    expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);

    // ── `--viewer-img-max-h` is LOAD-BEARING, proved by deletion ───────────
    // 2026-08-01, `bmad-code-review` re-run #2 NB-1: the "delete the term and
    // watch a test fail" proof had been applied to `--viewer-left`/`--viewer-top`
    // but NOT to the property that governs the photo's vertical fit. Nothing
    // failed if the write at `ImageFullscreenViewer.tsx` was removed — the three
    // page-scale tests all use `PANORAMA_8_1`, which is ~48px tall at fit scale,
    // so the cap never binds, and the sources that WOULD bind it only run at
    // page scale 1, where the measured value and the `calc(95dvh-5rem)` fallback
    // are the same number.
    //
    // Here they are NOT the same number, because the visual viewport is
    // `factor` times shorter than the layout viewport `dvh` resolves against.
    // Asserting the USED value therefore pins which of the two was applied.
    const imgMaxHeight = await page.evaluate(() => {
      const img = document.querySelector('[data-testid="image-viewer-frame"] img');
      if (!(img instanceof HTMLImageElement)) return null;
      return {
        used: Number.parseFloat(window.getComputedStyle(img).maxHeight),
        // What the component publishes: `0.95 * visualViewport.height - 5rem`.
        measured: (window.visualViewport?.height ?? 0) * 0.95 - 80,
        // What `calc(95dvh-5rem)` resolves to — `dvh` is the LAYOUT viewport.
        fallback: document.documentElement.clientHeight * 0.95 - 80,
      };
    });
    expect(imgMaxHeight, "the photo has a computed max-height").not.toBeNull();
    const maxH = imgMaxHeight as { used: number; measured: number; fallback: number };
    expect(
      maxH.fallback - maxH.measured,
      "precondition: the fallback and the measured cap are genuinely different numbers here",
    ).toBeGreaterThan(50);
    expect(
      maxH.used,
      "the photo's max-height came from the MEASURED visible region, not the `dvh` fallback",
    ).toBeCloseTo(maxH.measured, 0);

    // Reachable, not merely inside: the toolbar is the control the device
    // evidence shows sliced, so hit-test it rather than only measuring it.
    await expect(zoomInControl(page)).toBeEnabled();
    await zoomInControl(page).click();
    await expect.poll(async () => (await transformOf(page)).scale).toBeGreaterThan(1);
    await zoomResetControl(page).click();
    await expect.poll(async () => (await transformOf(page)).scale).toBe(1);
    await assertDismissible(page);
  });
}

// The ORIGIN half of the condition — added 2026-08-01 after the native
// `bmad-code-review` observed that page scale alone leaves the visible region
// at `0,0`, so `visualViewport.offsetLeft`/`.offsetTop` (`ImageFullscreenViewer
// .tsx`, `--viewer-left`/`--viewer-top`) and the `scroll` listener that keeps
// them current had zero coverage. Deleting both terms would have left the two
// tests above green.
const PAN_X_PX = 120;
const PAN_Y_PX = 80;

/**
 * "Reachable" expressed as a HIT TEST rather than as a click (2026-08-01,
 * BLOCKING-3 of the `bmad-code-review` re-run).
 *
 * The panned test below cannot drive Playwright's `click()`: Playwright derives
 * the click point from `getBoundingClientRect()` — LAYOUT-viewport space — while
 * CDP's `Input.dispatchMouseEvent` interprets it in VISUAL-viewport space. Once
 * the visible region's origin is non-zero the two spaces differ by exactly
 * `offsetLeft`/`offsetTop`, so the synthetic pointer lands on the photo, the
 * thumbnail strip or the overlay instead of the button. That is an artefact of
 * the harness, not a defect in the product: the same click is stable in the two
 * page-scale tests above, where the origin stays at `0,0`, and those two keep
 * the real interaction coverage (zoom in, reset, dismiss).
 *
 * `document.elementFromPoint` has no such split — it takes the same client
 * coordinates `getBoundingClientRect()` reports — so it answers the question
 * that actually matters here ("is this control the topmost thing at its own
 * centre, or is something covering it?") in one coordinate space, deterministically.
 *
 * ⚠️ CORRECTED 2026-08-01 (`bmad-code-review` re-run #2, BLOCKING-7). This
 * helper used to claim "reachable, not merely inside" on the strength of
 * `elementFromPoint` alone, and that claim was FALSE: `elementFromPoint` is not
 * clipped to the visible region, so under the 0-origin regression this test
 * exists to kill — the whole dialog laid out above and to the left of what the
 * user can see — the button is still unoccluded and the occlusion check still
 * passes. All the regression power lived in the `expectWithinVisibleRegion`
 * calls at the call site. The `region` argument is what makes the claim true:
 * the point actually hit-tested must ALSO lie inside the region the user can
 * see, so the helper now fails on a 0-origin implementation by itself. The two
 * halves are complementary and both are asserted — inside the region, and
 * topmost at that point.
 */
async function expectHittable(locator: Locator, label: string, region: Box) {
  await expect(locator, `${label} is visible`).toBeVisible();
  const { topmostIsTarget, hitX, hitY } = await locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    const hit = document.elementFromPoint(x, y);
    return { topmostIsTarget: hit === el || el.contains(hit), hitX: x, hitY: y };
  });
  // The hit POINT — not the box — because that is the coordinate the occlusion
  // answer is about; a control half inside the region would otherwise report
  // "topmost" from a centre the user cannot reach.
  expect(hitX, `${label}: the hit-tested point is inside what the user can see (left)`)
    .toBeGreaterThanOrEqual(region.x - EPSILON_PX);
  expect(hitX, `${label}: the hit-tested point is inside what the user can see (right)`)
    .toBeLessThanOrEqual(region.x + region.width + EPSILON_PX);
  expect(hitY, `${label}: the hit-tested point is inside what the user can see (top)`)
    .toBeGreaterThanOrEqual(region.y - EPSILON_PX);
  expect(hitY, `${label}: the hit-tested point is inside what the user can see (bottom)`)
    .toBeLessThanOrEqual(region.y + region.height + EPSILON_PX);
  expect(topmostIsTarget, `${label} is the topmost element at its own centre`).toBe(true);
}

test("the viewer follows the visible region when the user pans a zoomed page", async ({ page }) => {
  await openViewerWith(page, PANORAMA_8_1);
  await setPageScale(page, 2);
  // Panned AFTER the viewer is open, so the geometry can only be right if the
  // `visualViewport` `scroll` listener re-published it — an open-time-only sync
  // fails here.
  await panVisibleRegion(page, PAN_X_PX, PAN_Y_PX);

  const region = await visibleRegion(page);
  expect(
    region.x,
    "precondition: the visible region's origin really moved along X",
  ).toBeGreaterThan(0);
  expect(
    region.y,
    "precondition: the visible region's origin really moved along Y",
  ).toBeGreaterThan(0);

  // THE CONTRACT, unchanged from the two tests above — only the region's origin
  // differs. A 0-origin implementation puts the whole dialog above and to the
  // left of what the user can see, and every one of these fails.
  expectWithinVisibleRegion("dialog", await boxOf(page, '[data-slot="dialog-content"]'), region);
  expectWithinVisibleRegion(
    "viewer root",
    await boxOf(page, '[data-testid="image-viewer-root"]'),
    region,
  );
  expectWithinVisibleRegion(
    "photo",
    await boxOf(page, '[data-testid="image-viewer-frame"] img'),
    region,
  );
  expectWithinVisibleRegion(
    "close button",
    await boxOf(page, '[data-testid="image-viewer-close"]'),
    region,
  );
  expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);

  // Reachable in the panned state too, not merely inside it — as a hit test,
  // not as a click. See `expectHittable`: driving a synthetic pointer here
  // measures the harness's two coordinate spaces, not the viewer. The
  // click-through interaction (zoom in, reset, dismiss) stays where it is
  // deterministic — the two origin-`0,0` page-scale tests above. "Reachable"
  // here means BOTH halves, and `region` is what carries the first:
  // hit-tested inside what the user can see, AND topmost at that point.
  await expect(zoomInControl(page)).toBeEnabled();
  // Zoom-in and close only: both are ENABLED in this state, so a hit test on
  // them is unambiguous. Reset is legitimately disabled at the fit floor, and
  // "can a disabled control be hit" is not a contract this story owns.
  await expectHittable(zoomInControl(page), "zoom-in control in the panned region", region);
  await expectHittable(
    page.getByTestId("image-viewer-close"),
    "close control in the panned region",
    region,
  );
});


// ── THE UPPER END OF THE PAGE-SCALE RANGE ─────────────────────────────────
// Added 2026-08-01 after `bmad-code-review` re-run #2 (BLOCKING-6) observed
// that the tests above stop at page scale 2 while `apps/web/index.html:5`
// carries `width=device-width, initial-scale=1.0` and NO `maximum-scale`, so
// Chromium lets the user pinch the page to 5x. The contract AC-2 states is
// unqualified, and "a green suite that stopped short of the defect" is the
// exact thesis of AC-3 — so the range had to be measured, not assumed.
//
// MEASURED on `mobile-light` (393px layout viewport) BEFORE the repair below,
// with the visible region's origin at 0,0. The review's estimate was ~2.7x; the
// measurement puts the first failure lower, at ~2.45x, and finds a SECOND cause
// it had not named — the close button, not just the toolbar:
//
//   scale  region.w  dialog.w  toolbar right  close right   verdict
//    2      196.50    192.56      170.23        182.52      contained
//    2.5    157.20    154.05      152.56        147.56      root 159.56 -> OUT
//    3      131.00    128.38      152.30 -> OUT 147.30 -> OUT
//    4       98.25     96.28      152.00 -> OUT 147.00 -> OUT
//    5       78.60     77.02      152.00 -> OUT 147.00 -> OUT
//
// Two independent causes, both repaired at the source rather than tested
// around (see the two BLOCKING-6 comment blocks in `ImageFullscreenViewer.tsx`):
//   1. the root is a GRID ITEM of `DialogContent`, so its `min-width: auto`
//      floored it at the thumb strip's 158px min-content and the close button
//      rode that floor straight out of the visible region — `min-w-0`;
//   2. the toolbar's max-content is 144px and it neither wrapped nor shrank —
//      `flex-wrap` + `justify-center`, with `shrink-0` on the three buttons so
//      the re-flow cannot buy containment by squeezing the targets.
//
// ⚠️ THE BOUND IS RAISED, NOT REMOVED — and the range below is the range that
// was MEASURED GREEN, not an unlimited claim. AFTER the repair, toolbar top
// slack against the visible region (`mobile-light`, portrait):
//
//   scale  region.h  frame.h  toolbar rows x h   top slack
//    3      242.33    150.20     2 x 40 = 96      +44.25   contained
//    3.5    207.71    117.33     2 x 40 = 96      +10.52   contained
//    4      181.75     92.66     2 x 40 = 96      -14.81   OUT (vertical)
//    4.5    161.56     73.47     3 x 40 = 144     -82.50   OUT (vertical)
//    5      145.40     58.13     3 x 40 = 144     -98.25   OUT (vertical)
//
// Above ~3.5x on a 393px-wide phone the binding constraint stops being the
// toolbar's width and becomes the VERTICAL budget: the `h-20` thumb strip is a
// fixed 80px of a dialog that is only 172px tall at 4x, leaving a 92.66px frame
// that a 96px wrapped toolbar cannot sit inside.
//
// And a TIGHTER limit sits below that one, found by running this test at 3.5
// and reading the failure rather than by predicting it: the wrapped toolbar
// grows UPWARDS from its bottom anchor, and above ~3.06x it covers the close
// button's centre. Measured onset (`mobile-light`, toolbar top vs close centre):
//
//   scale  toolbar top  close centre  slack   topmost at close's centre
//    3        44.25        40.05      +4.20   the close button
//    3.05     40.39        39.95      +0.44   the close button
//    3.1      36.64        39.86      -3.22   the TOOLBAR
//    3.2      29.50        39.67     -10.17   the zoom-out button
//
// Both limits need the same repair — changing what the viewer RENDERS at tiny
// heights (dropping, shrinking or re-anchoring the strip and the toolbar) —
// which is the viewer redesign this repair story is scoped out of. They are
// ledgered as owed rather than claimed: `deferred-work.md` DW-53.4-C. AC-2 is
// therefore satisfied over a MEASURED range, ~1x-3x, not unlimited.
//
// On the two DESKTOP projects (1280x720) Chromium refuses the emulation above
// 4x — `Emulation.setPageScaleFactor(4.5)` and `(5)` both leave
// `visualViewport.scale` at 4 — and the viewer is contained at 3, 3.5 and 4
// there (toolbar top slack +90.00 / +56.56 / +31.50), because 144px of toolbar
// still fits one row in a 320px-wide region. The phone projects are the tight
// ones, and they are the ones the defect was reported from.
//
// 3 alone, not a range: it is the first integer scale past the measured ~2.45
// break, it is green on all four projects, and the +4.20px of close-button
// slack it carries is deliberately the LAST safe step — this test is the
// tripwire that fires if anything grows the toolbar or the strip.
const HIGH_PAGE_SCALES = [3] as const;

/** The SHIPPED toolbar control size (`h-10 w-10`). Asserted as a
 *  non-regression floor, not as the accessibility minimum — WCAG 2.2 SC 2.5.8
 *  asks 24px and `CLOSE_TARGET_MIN_PX` carries the 44px design token. The
 *  point is that the fit repair must not buy containment by shrinking
 *  controls, which is what an unguarded `flex-shrink` would have done. */
const TOOLBAR_TARGET_MIN_PX = 40;

for (const factor of HIGH_PAGE_SCALES) {
  test(`the viewer stays inside the visible region and keeps its target sizes at page scale ${factor}`, async ({
    page,
  }) => {
    await openViewerWith(page, PANORAMA_8_1);
    await setPageScale(page, factor);

    const region = await visibleRegion(page);
    expect(
      region.width,
      "precondition: the visible region really is narrower than the layout viewport",
    ).toBeLessThan(await page.evaluate(() => document.documentElement.clientWidth));

    // THE CONTRACT — identical to the 1.5x/2x tests above. `viewer root` and
    // `close button` are the two that failed here before the repair, and the
    // toolbar is the control the operator's device screenshot showed sliced.
    expectWithinVisibleRegion("dialog", await boxOf(page, '[data-slot="dialog-content"]'), region);
    expectWithinVisibleRegion(
      "viewer root",
      await boxOf(page, '[data-testid="image-viewer-root"]'),
      region,
    );
    expectWithinVisibleRegion(
      "photo",
      await boxOf(page, '[data-testid="image-viewer-frame"] img'),
      region,
    );
    expectWithinVisibleRegion(
      "close button",
      await boxOf(page, '[data-testid="image-viewer-close"]'),
      region,
    );
    expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);

    // ...WITHOUT paying for it in target size. Containment is trivially
    // satisfiable by letting the controls collapse; that is the failure mode
    // this half exists to catch.
    const controls = await page.evaluate((sel) => {
      const bar = document.querySelector(sel);
      if (bar === null) return null;
      return Array.from(bar.querySelectorAll("button")).map((b) => {
        const r = b.getBoundingClientRect();
        return { width: r.width, height: r.height };
      });
    }, TOOLBAR_SELECTOR);
    expect(controls, "the toolbar is present").not.toBeNull();
    expect(controls, "all three zoom controls survive the narrow region").toHaveLength(3);
    for (const [i, c] of (controls as { width: number; height: number }[]).entries()) {
      expect(c.width, `zoom control ${i} keeps its target width`).toBeGreaterThanOrEqual(
        TOOLBAR_TARGET_MIN_PX - TARGET_EPSILON_PX,
      );
      expect(c.height, `zoom control ${i} keeps its target height`).toBeGreaterThanOrEqual(
        TOOLBAR_TARGET_MIN_PX - TARGET_EPSILON_PX,
      );
    }
    const closeBox = await boxOf(page, '[data-testid="image-viewer-close"]');
    expect(closeBox.width, "close keeps its 44px target width").toBeGreaterThanOrEqual(
      CLOSE_TARGET_MIN_PX - TARGET_EPSILON_PX,
    );
    expect(closeBox.height, "close keeps its 44px target height").toBeGreaterThanOrEqual(
      CLOSE_TARGET_MIN_PX - TARGET_EPSILON_PX,
    );

    // Still reachable, not merely contained — same two halves as the panned
    // test: hit-tested inside the visible region AND topmost at that point.
    await expectHittable(zoomInControl(page), `zoom-in control at page scale ${factor}`, region);
    await expectHittable(
      page.getByTestId("image-viewer-close"),
      `close control at page scale ${factor}`,
      region,
    );
  });
}

// ── A `visualViewport` RESIZE RE-RUNS THE ZOOM/PAN REFIT ──────────────────
// Added 2026-08-01 for `bmad-code-review` re-run #2 BLOCKING-5. All three
// tests above assert at `scale === 1`, so none of them can see the coupling
// this story INTRODUCED: `--viewer-w`/`--viewer-h` now size the dialog, so
// `frame.clientWidth/Height` — the box `clampPan` measures the legal travel
// against — became a function of `visualViewport`. A page pinch fires
// `visualViewport.resize` and NOT `window.resize`, so with the listeners split
// across two effects the frame halved while `panRef` kept the travel it earned
// against the OLD frame: dead background dragged into view, and a stale zoom
// ceiling with it.
test("a visual-viewport resize re-clamps an existing zoom and pan", async ({ page }) => {
  await openViewerWith(page, PANORAMA_8_1);
  await waitForZoomable(page);

  // Zoom IN and pan to the edge FIRST, at page scale 1 — the state the two
  // page-scale tests cannot reach, and the only state in which the missing
  // refit is observable at all.
  // Two steps then a drag far past anything the clamp can allow — the same
  // recipe as the clamp test above, which is the one shape proven to commit a
  // pan on all four projects (a single step leaves too little travel on the
  // desktop frame, and a short drag is classified as a swipe).
  await zoomInControl(page).click();
  await zoomInControl(page).click();
  await expect
    .poll(async () => (await transformOf(page)).scale, { message: "zoomed above the fit floor" })
    .toBeGreaterThan(1);

  // The drag is RETRIED until it commits, and this is a precondition, not the
  // contract. MEASURED: firing the synthetic touch sequence immediately after
  // the zoom poll commits the pan on the phone projects every time but only
  // ~50% of the time on `desktop-light`/`desktop-dark` (10 runs, 5 red, all on
  // `|pan| > 0`); inserting round-trips before the gesture made it 4/4. The
  // suite's own `settleTwoFrames` is that wait, stated once. The retry is what
  // makes it robust rather than merely likelier: `panBy` is ABSOLUTE (it
  // recomputes from `start.panX + dx` each time, and 4000px is past every
  // clamp), so a repeat drag is idempotent and lands on the same clamped edge.
  // If the pan can never commit the poll times out and the test fails loudly —
  // it cannot degrade into a silent pass.
  await settleTwoFrames(page);
  await expect
    .poll(
      async () => {
        await panBy(page, -4000, -4000);
        const t = await transformOf(page);
        return Math.abs(t.x) + Math.abs(t.y);
      },
      { message: "precondition: the drag committed a pan away from centre" },
    )
    .toBeGreaterThan(0);
  const zoomed = await transformOf(page);
  expect(zoomed.scale, "zoomed above the fit floor before the viewport change").toBeGreaterThan(1);
  const frameBefore = await boxOf(page, '[data-testid="image-viewer-frame"]');

  // THE EVENT: a page pinch. `Emulation.setPageScaleFactor` fires
  // `visualViewport.resize` and leaves `window.resize` alone — which is
  // precisely the gap. The frame must actually shrink, or the assertion below
  // would be vacuous.
  await setPageScale(page, 3);
  const frameAfter = await boxOf(page, '[data-testid="image-viewer-frame"]');
  expect(
    frameAfter.width,
    "precondition: the pinch really did shrink the frame the clamp measures against",
  ).toBeLessThan(frameBefore.width);

  // THE CONTRACT: the pan is re-clamped against the NEW frame. `assertPanClamped`
  // states it exactly once for the whole suite — per axis, either the scaled
  // image no longer overflows the frame (pan pinned to 0) or the image edge is
  // not dragged inside the frame edge.
  await expect
    .poll(
      async () => {
        const t = await transformOf(page);
        return Math.abs(t.x) + Math.abs(t.y);
      },
      { message: "the refit ran after the visual-viewport resize" },
    )
    .toBeLessThanOrEqual(Math.abs(zoomed.x) + Math.abs(zoomed.y) + EPSILON_PX);
  await assertPanClamped(page);

  // ...and the zoom level itself is PRESERVED, not silently reset — the same
  // promise the rotation test makes (`EXPERIENCE.md:262`).
  expect((await transformOf(page)).scale, "the refit preserved the zoom level").toBeCloseTo(
    zoomed.scale,
    2,
  );

  // The whole point of re-clamping: nothing the user can see is outside the
  // region, in the zoomed state too.
  const region = await visibleRegion(page);
  expectWithinVisibleRegion("dialog", await boxOf(page, '[data-slot="dialog-content"]'), region);
  expectWithinVisibleRegion(
    "viewer root",
    await boxOf(page, '[data-testid="image-viewer-root"]'),
    region,
  );
  expectWithinVisibleRegion("zoom toolbar", await boxOf(page, TOOLBAR_SELECTOR), region);
});
