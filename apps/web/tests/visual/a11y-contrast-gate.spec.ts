/*
 * Story 54.2 / AC-7 + T10 (Decision D-5) — a COLOUR gate that actually fires.
 *
 * WHY THIS EXISTS
 * ---------------
 * The visual suite is a LAYOUT gate, not a colour gate. Story 53.3's DN-3
 * repair moved the viewer error chip's backdrop from `bg-gallery-control/40` to
 * `/60`, taking the composite behind its white copy from rgb(151,151,151) to
 * rgb(102,102,102) — a 2.92:1 -> 5.74:1 contrast change, plainly visible to a
 * human — and ALL FOUR `image-viewer-error-<project>.png` baselines still
 * PASSED. Playwright's `toHaveScreenshot` defaults to `threshold: 0.2`
 * (per-pixel YIQ distance) and pixelmatch's normalised delta for a 49-level
 * grey shift is ~0.034, well inside it. A gate that cannot see a 2.92:1 text
 * contrast is not a contrast gate.
 *
 * MECHANISM CHOSEN, AND WHY (AC-7 lets dev pick; the choice is recorded here)
 * --------------------------------------------------------------------------
 * A COMPUTED-CONTRAST PROBE, not a tightened `threshold`/`maxDiffPixelRatio`.
 *   - A tightened threshold is a repo-wide `playwright.config.ts` change, which
 *     is `Ask First` (story § 5) precisely because the 53.3 review measured
 *     "real flake risk across four projects". It would also be an INDIRECT
 *     detector: it fires on any pixel drift, not on a contrast failure, so it
 *     answers a different question than the one NFR26-DARKMODE-1 asks.
 *   - Axe's `color-contrast` rule is the other candidate and IS extended, in
 *     `accessibility-axe.spec.ts`, to the Initiative 26 surfaces. But axe
 *     cannot rule on the V-6 case at all: it reports `incomplete`, not
 *     `violation`, whenever the text sits on a translucent layer whose backdrop
 *     it cannot resolve — which is every `bg-gallery-control/<alpha>` overlay in
 *     this app. An `incomplete` fails nothing.
 *   - The probe below composites the ACTUAL rendered alpha stack in Chromium
 *     and asserts a WCAG ratio directly. It fires on the thing the criterion is
 *     about, on all four projects, with no suite-wide flake surface.
 *
 * DEMONSTRATED FAILING (D-5: "a gate that has never been seen to fire is not a
 * gate"). Recorded in the story's § 14 Dev Agent Record: reverting the DN-3
 * repair (`/60` -> `/40` on the error chip) makes
 * `viewer error chip clears WCAG AA for body text` FAIL on the two light
 * projects with the measured ratio in the message. The regression was then
 * reverted.
 *
 * ⚠️ WHAT THIS GATE DELIBERATELY DOES NOT CLAIM
 * ---------------------------------------------
 * Only composites whose backdrop is DOM-DETERMINABLE are measured. A control
 * painted over a PHOTO (the `ModelGallery` prev/next/fullscreen chrome, the
 * `/share` carousel chrome, and the viewer's own prev/next while an image is
 * showing) has a per-pixel backdrop that no DOM walk can resolve and that a
 * photograph makes unbounded in principle. Those call sites are ROUTED, not
 * silently passed — see `deferred-work.md` under Story 54.2. The viewer error
 * chip IS measurable and is the one that matters most, because the error state
 * means no image is painted: the backdrop is the dialog's own solid layer.
 *
 * ⚠️ SCOPE OF THE CLAIM (story § 0.1). Headless-Chromium evidence. The
 * `mobile-*` projects are EMULATION, never "Android". No physical device.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

/** WCAG 2.2 SC 1.4.3 Contrast (Minimum), body text below 18.66px/24px bold. */
const AA_BODY_TEXT = 4.5;

interface ContrastReading {
  ratio: number;
  foreground: string;
  background: string;
  /** True when the walk hit an opaque layer, so the composite is complete. */
  resolved: boolean;
}

/**
 * Composite the element's alpha stack in the page and return the WCAG contrast
 * ratio between its text colour and its effective background.
 *
 * The walk goes element -> ancestors, accumulating every non-transparent
 * `background-color` layer, and stops at the first fully-opaque one. Layers are
 * then composited back-to-front with the standard source-over formula, which is
 * what the compositor itself does. `resolved` says whether an opaque layer was
 * ever reached — an unresolved stack is reported, never quietly passed.
 */
async function readContrast(page: Page, selector: string): Promise<ContrastReading> {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (el === null) throw new Error(`contrast probe: no element matches ${sel}`);

    interface Rgba {
      r: number;
      g: number;
      b: number;
      a: number;
    }

    // Colour parsing goes through a canvas, NOT a regex.
    //
    // This project is on Tailwind v4, whose colour tokens resolve to `oklab(…)`
    // / `color(srgb …)` rather than `rgb()`, and a translucent utility such as
    // `bg-gallery-control/60` comes back from `getComputedStyle` in that
    // syntax. A regex that only understands `rgba?()` silently drops those
    // layers, and the probe then reports white-on-white at 1:1 — measuring
    // nothing while looking like it measured something. Letting the browser
    // rasterise the declaration is exact for every colour syntax it supports,
    // now and after the next Tailwind bump.
    const probe = document.createElement("canvas");
    probe.width = 1;
    probe.height = 1;
    const ctx = probe.getContext("2d", { willReadFrequently: true });

    const parse = (value: string): Rgba | null => {
      if (ctx === null || value === "" || value === "none") return null;
      // `fillStyle` silently ignores an unparseable value, so a sentinel is the
      // only way to tell "transparent" from "the browser rejected this".
      ctx.fillStyle = "#000000";
      ctx.fillStyle = value;
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillRect(0, 0, 1, 1);
      const d = ctx.getImageData(0, 0, 1, 1).data;
      const a = (d[3] ?? 0) / 255;
      if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
      return { r: d[0] ?? 0, g: d[1] ?? 0, b: d[2] ?? 0, a };
    };

    /** Source-over: `front` (possibly translucent) painted onto opaque `back`. */
    const over = (front: Rgba, back: Rgba): Rgba => ({
      r: front.r * front.a + back.r * (1 - front.a),
      g: front.g * front.a + back.g * (1 - front.a),
      b: front.b * front.a + back.b * (1 - front.a),
      a: 1,
    });

    const layers: Rgba[] = [];
    let resolved = false;
    for (let n: Element | null = el; n !== null; n = n.parentElement) {
      const bg = parse(getComputedStyle(n).backgroundColor);
      if (bg === null || bg.a === 0) continue;
      layers.push(bg);
      if (bg.a === 1) {
        resolved = true;
        break;
      }
    }
    // The canvas beneath everything. `html`'s used background is what the
    // browser paints there, and it is opaque in both themes.
    if (!resolved) {
      const canvas = parse(getComputedStyle(document.documentElement).backgroundColor);
      if (canvas !== null && canvas.a === 1) {
        layers.push(canvas);
        resolved = true;
      }
    }

    // Composite back-to-front. Without a resolved opaque layer the stack has no
    // defined bottom; white is assumed only so a number exists to report, and
    // `resolved: false` is what the caller must act on.
    let background: Rgba = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i -= 1) {
      const layer = layers[i];
      if (layer === undefined) continue;
      background = over(layer, background);
    }

    const fgRaw = parse(getComputedStyle(el).color) ?? { r: 0, g: 0, b: 0, a: 1 };
    const foreground = fgRaw.a === 1 ? fgRaw : over(fgRaw, background);

    const luminance = (c: Rgba) => {
      const lin = [c.r, c.g, c.b].map((channel) => {
        const s = channel / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * (lin[0] ?? 0) + 0.7152 * (lin[1] ?? 0) + 0.0722 * (lin[2] ?? 0);
    };
    const l1 = luminance(foreground);
    const l2 = luminance(background);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

    const fmt = (c: Rgba) => `rgb(${Math.round(c.r)},${Math.round(c.g)},${Math.round(c.b)})`;
    return {
      ratio: Math.round(ratio * 100) / 100,
      foreground: fmt(foreground),
      background: fmt(background),
      resolved,
    };
  }, selector);
}

// ---------------------------------------------------------------------------
// The V-6 site itself. The error state means the image did NOT paint, so the
// chip's backdrop is the dialog's own solid layer and the composite is fully
// DOM-determinable — this is a real, complete measurement, not an estimate.
// ---------------------------------------------------------------------------
test("viewer error chip clears WCAG AA for body text (AC-7 / V-6)", async ({ page }) => {
  await stubSotDetail(page, { imageCount: 1 });
  // Drive the viewer into its error branch. The status must stay 200: the
  // viewer fetches the bytes into a blob and it is the `<img>` element's own
  // `error` event that flips `imageStatus`, so a non-2xx would stall the fetch
  // layer instead. Serving a valid 200 whose body is not a decodable image
  // makes the decode fail, which is the path the jsdom contract test models
  // with `fireEvent.error(rendered-img)`. Registered AFTER `stubSotDetail`, so
  // Playwright's reverse-registration order lets it win over that fixture's own
  // 1x1-PNG content stub (`api-stubs.ts:485`).
  await page.route("**/api/models/**/files/**/content**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from("not-a-decodable-image"),
    }),
  );

  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();

  const chip = page.getByTestId("image-viewer-error").locator("span").first();
  await expect(chip).toBeVisible();

  const reading = await readContrast(page, '[data-testid="image-viewer-error"] span');

  // Non-vacuity: an unresolved stack means the probe never reached an opaque
  // layer, so its number is a guess. That is a failure of the GATE, and it must
  // say so rather than report a ratio nobody can trust.
  expect(reading.resolved, `contrast probe never resolved an opaque backdrop: ${JSON.stringify(reading)}`).toBe(true);

  expect(
    reading.ratio,
    `viewer error copy measured ${reading.ratio}:1 (${reading.foreground} on ${reading.background}).` +
      ` WCAG 2.2 SC 1.4.3 requires >= ${AA_BODY_TEXT}:1 for body text. This is the DN-3 site:` +
      ` at bg-gallery-control/40 it measured 2.92:1 and every PNG baseline still passed.`,
  ).toBeGreaterThanOrEqual(AA_BODY_TEXT);
});

// ---------------------------------------------------------------------------
// Non-vacuity of the PROBE, not of the app. If `readContrast` cannot tell a
// failing composite from a passing one, the test above is decoration. This
// injects a known-bad composite into the live page and requires the probe to
// report it below the floor — which is the D-5 "demonstrated failing" property
// pinned as an assertion rather than left as a one-off manual run.
// ---------------------------------------------------------------------------
test("the contrast probe reports a deliberately-bad composite as failing (D-5)", async ({
  page,
}) => {
  await stubSotDetail(page, { imageCount: 1 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  await page.evaluate(() => {
    const host = document.createElement("div");
    host.id = "contrast-probe-selftest";
    // Opaque mid-grey backdrop with white copy on top: ~2.85:1, the same order
    // as the DN-3 regression this gate exists to catch.
    host.style.cssText = "position:fixed;inset:auto 0 0 auto;background:rgb(151,151,151)";
    const text = document.createElement("span");
    text.style.color = "rgb(255,255,255)";
    text.textContent = "probe";
    host.appendChild(text);
    document.body.appendChild(host);
  });

  const bad = await readContrast(page, "#contrast-probe-selftest span");
  expect(bad.resolved).toBe(true);
  expect(
    bad.ratio,
    `probe scored a known-bad composite at ${bad.ratio}:1 — it cannot detect a contrast regression`,
  ).toBeLessThan(AA_BODY_TEXT);
});
