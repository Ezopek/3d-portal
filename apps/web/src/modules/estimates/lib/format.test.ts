import { describe, expect, it } from "vitest";

import {
  EM_DASH,
  formatCost,
  formatDuration,
  formatLength,
  formatMass,
  formatVolume,
} from "./format";

// The finite-number guard (AC-4, load-bearing): every formatter treats null, undefined,
// NaN, Infinity and -Infinity identically to a missing value (em-dash). A non-finite
// numeric must NEVER render as a digit string.
const NON_FINITE = [null, undefined, NaN, Infinity, -Infinity] as const;

describe("formatDuration", () => {
  it.each(NON_FINITE)("renders %s as em dash", (v) => {
    expect(formatDuration(v)).toBe(EM_DASH);
  });

  it("renders Xh Ym for durations over an hour", () => {
    // 12947s = 215m 47s ≈ 216m = 3h 36m
    expect(formatDuration(12947)).toBe("3h 36m");
    expect(formatDuration(3600)).toBe("1h 0m");
  });

  it("renders Ym for sub-hour durations", () => {
    expect(formatDuration(1500)).toBe("25m");
  });

  it("renders a negative duration as em dash (nonsense value, never -Xm)", () => {
    expect(formatDuration(-60)).toBe(EM_DASH);
  });
});

describe("formatMass", () => {
  it.each(NON_FINITE)("renders %s as em dash", (v) => {
    expect(formatMass(v)).toBe(EM_DASH);
  });

  it("renders grams below 1 kg and kg at/above 1 kg", () => {
    expect(formatMass(76.76)).toBe("77 g");
    expect(formatMass(1000)).toBe("1.00 kg");
    expect(formatMass(1234.5)).toBe("1.23 kg");
  });
});

describe("formatLength", () => {
  it.each(NON_FINITE)("renders %s as em dash", (v) => {
    expect(formatLength(v)).toBe(EM_DASH);
  });

  it("renders mm below 1 m and m at/above 1 m", () => {
    expect(formatLength(850)).toBe("850 mm");
    expect(formatLength(25735.79)).toBe("25.74 m");
  });
});

describe("formatVolume", () => {
  it.each(NON_FINITE)("renders %s as em dash", (v) => {
    expect(formatVolume(v)).toBe(EM_DASH);
  });

  it("renders cm³ with two decimals", () => {
    expect(formatVolume(61.9)).toBe("61.90 cm³");
  });
});

describe("formatCost", () => {
  it.each(NON_FINITE)("renders %s as em dash regardless of currency", (v) => {
    expect(formatCost(v, "PLN")).toBe(EM_DASH);
    expect(formatCost(v, null)).toBe(EM_DASH);
  });

  it("renders an informational amount with a currency when present", () => {
    expect(formatCost(4.6, "PLN")).toBe("4.60 PLN");
  });

  it("renders a bare amount when no currency is known", () => {
    expect(formatCost(4.6, null)).toBe("4.60");
  });
});

describe("no formatter ever renders NaN or Infinity", () => {
  it("returns em dash for every non-finite input across every formatter", () => {
    const formatters = [
      formatDuration,
      formatMass,
      formatLength,
      formatVolume,
    ] as const;
    for (const fmt of formatters) {
      for (const v of NON_FINITE) {
        const out = fmt(v);
        expect(out).toBe(EM_DASH);
        expect(out).not.toMatch(/NaN|Infinity/);
      }
    }
    for (const v of NON_FINITE) {
      const out = formatCost(v, "PLN");
      expect(out).toBe(EM_DASH);
      expect(out).not.toMatch(/NaN|Infinity/);
    }
  });
});
