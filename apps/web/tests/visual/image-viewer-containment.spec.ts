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

async function openViewerWith(
  page: Page,
  full: Buffer,
  opts: { overflow?: boolean; scrollX?: number } = {},
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
