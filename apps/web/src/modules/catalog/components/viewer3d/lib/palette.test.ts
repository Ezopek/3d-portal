import { describe, expect, it } from "vitest";
import {
  allocateColorIndex,
  paletteCss,
  paletteFor,
  oklchToLinearSrgb,
} from "./palette";
import type { Measurement } from "../types";

const CANVAS_BG = [0x0d / 255, 0x14 / 255, 0x22 / 255] as const; // #0d1422 sRGB

function relativeLuminance([r, g, b]: readonly [number, number, number]): number {
  const lin = (c: number) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function linearToDisplaySrgb(c: number): number {
  // Inverse of the sRGB→linear gamma. Standard formula.
  return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

function contrastRatio(a: readonly [number, number, number], b: readonly [number, number, number]): number {
  const lum1 = relativeLuminance(a);
  const lum2 = relativeLuminance(b);
  const [hi, lo] = lum1 > lum2 ? [lum1, lum2] : [lum2, lum1];
  return (hi + 0.05) / (lo + 0.05);
}

describe("paletteFor", () => {
  it("is deterministic for a given (index, slot)", () => {
    const a = paletteFor(0, "sel1").toArray();
    const b = paletteFor(0, "sel1").toArray();
    expect(a).toEqual(b);
  });

  it("produces visibly different colors for sel1 vs sel2 at the same index", () => {
    const sel1 = paletteFor(0, "sel1").toArray();
    const sel2 = paletteFor(0, "sel2").toArray();
    const maxDelta = Math.max(...sel1.map((v, i) => Math.abs(v - sel2[i]!)));
    expect(maxDelta).toBeGreaterThan(0.1);
  });

  it("rotates hue between consecutive indices (golden angle)", () => {
    const a = paletteFor(0, "sel1").toArray();
    const b = paletteFor(1, "sel1").toArray();
    const maxDelta = Math.max(...a.map((v, i) => Math.abs(v - b[i]!)));
    expect(maxDelta).toBeGreaterThan(0.15);
  });

  it("WCAG: every (index, slot) achieves >= 3:1 contrast vs canvas #0d1422 for index 0..15", () => {
    const failures: string[] = [];
    for (let i = 0; i < 16; i++) {
      for (const slot of ["sel1", "sel2"] as const) {
        const linear = paletteFor(i, slot).toArray() as [number, number, number];
        const display = linear.map(linearToDisplaySrgb) as [number, number, number];
        const ratio = contrastRatio(display, CANVAS_BG);
        if (ratio < 3.0) {
          failures.push(`idx=${i} slot=${slot} ratio=${ratio.toFixed(2)}`);
        }
      }
    }
    expect(failures, failures.join("\n")).toEqual([]);
  });
});

describe("paletteCss", () => {
  it("returns a valid oklch() css string", () => {
    const css = paletteCss(0, "sel1");
    expect(css).toMatch(/^oklch\(\d+(\.\d+)?% 0\.\d+ \d+(\.\d+)?\)$/);
  });
});

describe("oklchToLinearSrgb", () => {
  it("clamps to [0,1] for any input", () => {
    const [r, g, b] = oklchToLinearSrgb(1.5, 0.5, 0);
    expect(r).toBeGreaterThanOrEqual(0);
    expect(r).toBeLessThanOrEqual(1);
    expect(g).toBeGreaterThanOrEqual(0);
    expect(g).toBeLessThanOrEqual(1);
    expect(b).toBeGreaterThanOrEqual(0);
    expect(b).toBeLessThanOrEqual(1);
  });
});

describe("allocateColorIndex", () => {
  function fakeMeasurements(indices: number[]): Measurement[] {
    return indices.map((i) => ({
      kind: "p2p",
      id: `m${i}`,
      colorIndex: i,
      a: { x: 0, y: 0, z: 0 } as never,
      b: { x: 0, y: 0, z: 0 } as never,
      distanceMm: 0,
    }));
  }

  it("returns 0 for an empty list", () => {
    expect(allocateColorIndex([])).toBe(0);
  });

  it("returns N for a contiguous [0..N-1] list", () => {
    expect(allocateColorIndex(fakeMeasurements([0, 1, 2]))).toBe(3);
  });

  it("fills the smallest gap", () => {
    expect(allocateColorIndex(fakeMeasurements([0, 2]))).toBe(1);
    expect(allocateColorIndex(fakeMeasurements([1, 2]))).toBe(0);
    expect(allocateColorIndex(fakeMeasurements([0, 1, 3]))).toBe(2);
  });
});
