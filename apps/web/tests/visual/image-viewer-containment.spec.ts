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

import type { Page, Route } from "@playwright/test";

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

function expectWithinViewport(label: string, box: Box, vw: number, vh: number) {
  expect(box.x, `${label} left edge`).toBeGreaterThanOrEqual(-EPSILON_PX);
  expect(box.y, `${label} top edge`).toBeGreaterThanOrEqual(-EPSILON_PX);
  expect(box.x + box.width, `${label} right edge`).toBeLessThanOrEqual(vw + EPSILON_PX);
  expect(box.y + box.height, `${label} bottom edge`).toBeLessThanOrEqual(vh + EPSILON_PX);
}

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

async function assertContained(page: Page, opts: { overflow?: boolean } = {}) {
  // `documentElement.clientWidth` tracks the VISUAL viewport; `innerWidth`
  // tracks the layout viewport and is exactly the value that diverges here.
  // Containment is only meaningful against the visual viewport — that is what
  // the user can actually see and reach.
  const { vw, vh, scrollWidth } = await page.evaluate(() => ({
    vw: document.documentElement.clientWidth,
    vh: document.documentElement.clientHeight,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  const dialog = await boxOf(page, '[data-slot="dialog-content"]');
  const root = await boxOf(page, '[data-testid="image-viewer-root"]');
  const frame = await boxOf(page, '[data-testid="image-viewer-frame"]');
  const image = await boxOf(page, '[data-testid="image-viewer-frame"] img');
  const close = await boxOf(page, '[data-testid="image-viewer-close"]');

  expectWithinViewport("dialog", dialog, vw, vh);
  expect(dialog.width, "dialog preserves fullscreen coverage").toBeGreaterThanOrEqual(vw * 0.9);
  expectWithinViewport("viewer root", root, vw, vh);
  expectWithinViewport("close button", close, vw, vh);
  expectContainedBy("image", image, frame);
  await expect(page.getByTestId("image-viewer-strip")).toBeVisible();
  await expect(page.getByTestId("image-viewer-counter")).toBeVisible();
  await expect(page.getByTestId("image-viewer-prev")).toBeVisible();
  await expect(page.getByTestId("image-viewer-next")).toBeVisible();
  await expect(page.getByTestId("image-viewer-thumb")).toHaveCount(2);
  // The viewer must not itself add a horizontal scroll region. Skipped when a
  // test deliberately injected page overflow — there the overflow is the input.
  if (opts.overflow !== true) expect(scrollWidth).toBeLessThanOrEqual(vw + EPSILON_PX);

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
// `pl-PL` and `catalog.image_viewer.zoom_in` is "Powiększ" in Polish — and so
// is the SHIPPED `catalog.image_viewer.trigger_label` on the gallery trigger
// (53.2 D-8's recorded terminology collision, raised for Story 54.1). Scoping
// is how these lookups stay unambiguous without renaming anything (V-17).
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
  const { vw, vh, scrollWidth } = await page.evaluate(() => ({
    vw: document.documentElement.clientWidth,
    vh: document.documentElement.clientHeight,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  expectWithinViewport("dialog", await boxOf(page, '[data-slot="dialog-content"]'), vw, vh);
  expectWithinViewport(
    "viewer root",
    await boxOf(page, '[data-testid="image-viewer-root"]'),
    vw,
    vh,
  );
  expectWithinViewport("frame", await boxOf(page, '[data-testid="image-viewer-frame"]'), vw, vh);
  expectWithinViewport(
    "close button",
    await boxOf(page, '[data-testid="image-viewer-close"]'),
    vw,
    vh,
  );
  await expect(page.getByTestId("image-viewer-strip")).toBeVisible();
  await expect(page.getByTestId("image-viewer-counter")).toBeVisible();
  await expect(page.getByTestId("image-viewer-prev")).toBeVisible();
  await expect(page.getByTestId("image-viewer-next")).toBeVisible();
  await expect(page.getByTestId("image-viewer-toolbar")).toBeVisible();
  expect(scrollWidth, "the viewer adds no horizontal document overflow").toBeLessThanOrEqual(
    vw + EPSILON_PX,
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
