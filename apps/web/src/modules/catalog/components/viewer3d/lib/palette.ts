import { Color, LinearSRGBColorSpace } from "three";

import type { Measurement } from "../types";

export type PaletteSlot = "sel1" | "sel2";

const BASE_HUE_DEG = 200;
const GOLDEN_ANGLE_DEG = 137.50776;
const PAIR_LIGHTNESS_BRIGHT = 0.78; // sel1
const PAIR_LIGHTNESS_DARK = 0.55;   // sel2 — calibrated for ≥3:1 contrast vs #0d1422
const PAIR_CHROMA = 0.18;

/** Three.js Color in linear-sRGB (R3F's working color space). */
export function paletteFor(colorIndex: number, slot: PaletteSlot): Color {
  const [r, g, b] = oklchToLinearSrgb(...oklchOf(colorIndex, slot));
  return new Color().setRGB(r, g, b, LinearSRGBColorSpace);
}

/** CSS color string in display-sRGB; the browser handles OKLCH → display sRGB. */
export function paletteCss(colorIndex: number, slot: PaletteSlot): string {
  const [L, C, h] = oklchOf(colorIndex, slot);
  return `oklch(${(L * 100).toFixed(1)}% ${C.toFixed(3)} ${h.toFixed(1)})`;
}

function oklchOf(colorIndex: number, slot: PaletteSlot): [number, number, number] {
  const hue = ((BASE_HUE_DEG + colorIndex * GOLDEN_ANGLE_DEG) % 360 + 360) % 360;
  const L = slot === "sel1" ? PAIR_LIGHTNESS_BRIGHT : PAIR_LIGHTNESS_DARK;
  return [L, PAIR_CHROMA, hue];
}

/** OKLCH → linear sRGB (Björn Ottosson's published matrix), clamped to [0, 1]. */
export function oklchToLinearSrgb(L: number, C: number, hueDeg: number): [number, number, number] {
  const h = (hueDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l3 = l_ ** 3;
  const m3 = m_ ** 3;
  const s3 = s_ ** 3;
  const r =  4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3;
  const g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3;
  const bl = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3;
  return [
    Math.max(0, Math.min(1, r)),
    Math.max(0, Math.min(1, g)),
    Math.max(0, Math.min(1, bl)),
  ];
}

/** Smallest non-negative integer not already used as colorIndex. */
export function allocateColorIndex(completed: readonly Measurement[]): number {
  const used = new Set<number>();
  for (const m of completed) used.add(m.colorIndex);
  for (let i = 0; ; i++) if (!used.has(i)) return i;
}
