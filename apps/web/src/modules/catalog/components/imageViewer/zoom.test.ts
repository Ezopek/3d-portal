// Story 53.2 (E53 / FR26-VIEW-1) — unit coverage for the viewer's zoom + pan
// math. This module exists specifically so the clamp arithmetic is testable:
// jsdom has no layout engine, so `getBoundingClientRect()` returns all-zero
// rects and a clamp test written against the mounted component would pass
// trivially and prove nothing (story Dev Notes, "jsdom has no layout"). Here
// the geometry is injected as plain numbers, so the assertions are real.

import { describe, expect, it } from "vitest";

import {
  BASE_MAX_SCALE,
  DOUBLE_TAP_SCALE,
  MIN_SCALE,
  ZOOM_STEP,
  clampPan,
  clampScale,
  doubleTapTarget,
  panForScaleAbout,
  resolveMaxScale,
  zoomIn,
  zoomOut,
} from "./zoom";

describe("zoom constants", () => {
  it("uses the story D-4 limits", () => {
    expect(MIN_SCALE).toBe(1);
    expect(BASE_MAX_SCALE).toBe(4);
    expect(ZOOM_STEP).toBe(1.5);
  });

  it("puts the double-tap target on the button ladder", () => {
    // D-4: "every state it reaches must also be reachable by the buttons".
    // 2.25 === two Zoom In presses from 1.0, so double-tap introduces no
    // scale the three visible controls cannot produce.
    expect(DOUBLE_TAP_SCALE).toBeCloseTo(ZOOM_STEP * ZOOM_STEP, 10);
  });
});

describe("resolveMaxScale", () => {
  it("falls back to the base cap when the geometry is unmeasurable", () => {
    // jsdom / pre-decode: natural or rendered width is 0.
    expect(resolveMaxScale(0, 0)).toBe(BASE_MAX_SCALE);
    expect(resolveMaxScale(4000, 0)).toBe(BASE_MAX_SCALE);
    expect(resolveMaxScale(0, 400)).toBe(BASE_MAX_SCALE);
  });

  it("keeps the base cap when the source cannot support more", () => {
    // A source displayed near 1:1 still gets the default 4x envelope.
    expect(resolveMaxScale(400, 400)).toBe(BASE_MAX_SCALE);
    expect(resolveMaxScale(800, 400)).toBe(BASE_MAX_SCALE);
  });

  it("raises the cap to the native-pixel ratio for a downscaled panorama", () => {
    // An 8:1 panorama letterboxed into a phone frame: 8000 native px shown
    // across 400 CSS px supports 20x before a single pixel is upsampled.
    expect(resolveMaxScale(8000, 400)).toBe(20);
  });
});

describe("clampScale", () => {
  it("never goes below 1.0", () => {
    expect(clampScale(0.2, 4)).toBe(MIN_SCALE);
    expect(clampScale(-3, 4)).toBe(MIN_SCALE);
  });

  it("never exceeds the supplied max", () => {
    expect(clampScale(9, 4)).toBe(4);
    expect(clampScale(2.5, 4)).toBe(2.5);
  });

  it("treats a non-finite scale as the floor", () => {
    expect(clampScale(Number.NaN, 4)).toBe(MIN_SCALE);
    expect(clampScale(Number.POSITIVE_INFINITY, 4)).toBe(4);
  });
});

describe("zoomIn / zoomOut", () => {
  it("steps by 1.5x and stops at the cap", () => {
    expect(zoomIn(1, 4)).toBe(1.5);
    expect(zoomIn(1.5, 4)).toBe(2.25);
    expect(zoomIn(3, 4)).toBe(4);
    expect(zoomIn(4, 4)).toBe(4);
  });

  it("steps back down by 1.5x and stops at 1.0", () => {
    expect(zoomOut(2.25, 4)).toBe(1.5);
    expect(zoomOut(1.5, 4)).toBe(1);
    expect(zoomOut(1, 4)).toBe(1);
  });

  it("is symmetric — a Zoom In followed by a Zoom Out returns to the origin", () => {
    expect(zoomOut(zoomIn(1, 4), 4)).toBeCloseTo(1, 10);
    expect(zoomOut(zoomIn(1.5, 4), 4)).toBeCloseTo(1.5, 10);
  });
});

describe("doubleTapTarget", () => {
  it("toggles 1.0 <-> the fixed step", () => {
    expect(doubleTapTarget(1, 4)).toBe(DOUBLE_TAP_SCALE);
    expect(doubleTapTarget(DOUBLE_TAP_SCALE, 4)).toBe(1);
  });

  it("returns to 1.0 from any zoomed state, not only from the step", () => {
    expect(doubleTapTarget(1.5, 4)).toBe(1);
    expect(doubleTapTarget(3.9, 4)).toBe(1);
  });

  it("respects a max below the fixed step", () => {
    expect(doubleTapTarget(1, 1.8)).toBe(1.8);
  });
});

describe("clampPan", () => {
  const frame = { width: 400, height: 800 };
  const base = { width: 400, height: 300 };

  it("pins pan to zero at scale 1.0 in both axes", () => {
    expect(clampPan({ x: 120, y: -60 }, 1, base, frame)).toEqual({ x: 0, y: 0 });
  });

  it("allows pan only along the axis that actually overflows", () => {
    // At 2x the image is 800x600: it overflows the 400px width by 400
    // (=> +/-200 of travel) but is still shorter than the 800px frame.
    expect(clampPan({ x: 500, y: 500 }, 2, base, frame)).toEqual({ x: 200, y: 0 });
    expect(clampPan({ x: -500, y: -500 }, 2, base, frame)).toEqual({ x: -200, y: 0 });
  });

  it("leaves an in-range pan untouched", () => {
    expect(clampPan({ x: 40, y: 0 }, 2, base, frame)).toEqual({ x: 40, y: 0 });
  });

  it("never lets an image edge move inside the frame edge", () => {
    // Tall frame, tall image: 400x300 at 4x = 1600x1200, overflowing 400x800
    // by 1200 and 400 => +/-600 and +/-200 of travel.
    expect(clampPan({ x: 9999, y: 9999 }, 4, base, frame)).toEqual({ x: 600, y: 200 });
  });

  it("re-clamps after a zoom-out so the image cannot stay detached", () => {
    // Panned to the 4x limit, then zoomed back to 2x: the old offset is now
    // out of range and must be pulled back to the 2x limit.
    const at4x = clampPan({ x: 9999, y: 9999 }, 4, base, frame);
    expect(clampPan(at4x, 2, base, frame)).toEqual({ x: 200, y: 0 });
  });

  it("degenerates safely when the geometry is unmeasurable (jsdom)", () => {
    // jsdom reports every layout box as 0, so both operands vanish together
    // and there is no travel to permit.
    expect(clampPan({ x: 50, y: 50 }, 3, { width: 0, height: 0 }, frame)).toEqual({
      x: 0,
      y: 0,
    });
    expect(
      clampPan({ x: 50, y: 50 }, 3, { width: 0, height: 0 }, { width: 0, height: 0 }),
    ).toEqual({ x: 0, y: 0 });
  });

  it("coerces a non-finite pan to zero without disturbing the other axis", () => {
    // At 4x the image is 1600x1200, so the Y axis has +/-200 of real travel:
    // y = 100 must survive while the NaN on X collapses to 0.
    expect(clampPan({ x: Number.NaN, y: 100 }, 4, base, frame)).toEqual({ x: 0, y: 100 });
  });
});

describe("panForScaleAbout", () => {
  it("is a no-op when the scale does not change", () => {
    expect(panForScaleAbout({ x: 30, y: 10 }, 2, 2, { x: 50, y: 50 })).toEqual({
      x: 30,
      y: 10,
    });
  });

  it("keeps the frame centre fixed when the focus is the centre", () => {
    expect(panForScaleAbout({ x: 0, y: 0 }, 1, 2, { x: 0, y: 0 })).toEqual({ x: 0, y: 0 });
  });

  it("keeps the focused content point under the fingers", () => {
    // Content point c sits at screen offset p = pan + s*c. Doubling the
    // scale about p must leave p resolving to the same c.
    const pan = { x: 10, y: -20 };
    const from = 2;
    const to = 3;
    const focus = { x: 60, y: 40 };
    const c = { x: (focus.x - pan.x) / from, y: (focus.y - pan.y) / from };
    const next = panForScaleAbout(pan, from, to, focus);
    expect(next.x + to * c.x).toBeCloseTo(focus.x, 10);
    expect(next.y + to * c.y).toBeCloseTo(focus.y, 10);
  });

  it("degenerates safely on a zero source scale", () => {
    expect(panForScaleAbout({ x: 5, y: 5 }, 0, 2, { x: 1, y: 1 })).toEqual({ x: 5, y: 5 });
  });
});
