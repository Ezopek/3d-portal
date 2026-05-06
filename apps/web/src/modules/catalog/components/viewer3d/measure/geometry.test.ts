import { describe, it, expect } from "vitest";
import { Vector3 } from "three";

import { distance, midpoint, formatMm } from "./geometry";

describe("distance", () => {
  it("returns Euclidean distance between two points", () => {
    expect(distance(new Vector3(0, 0, 0), new Vector3(3, 4, 0))).toBeCloseTo(5, 6);
  });

  it("returns 0 for identical points", () => {
    expect(distance(new Vector3(1, 2, 3), new Vector3(1, 2, 3))).toBe(0);
  });

  it("handles negative coordinates", () => {
    expect(distance(new Vector3(-1, -1, -1), new Vector3(1, 1, 1))).toBeCloseTo(
      Math.sqrt(12),
      6,
    );
  });
});

describe("midpoint", () => {
  it("returns the midpoint of two points", () => {
    const m = midpoint(new Vector3(0, 0, 0), new Vector3(2, 4, 6));
    expect(m.x).toBe(1);
    expect(m.y).toBe(2);
    expect(m.z).toBe(3);
  });
});

describe("formatMm", () => {
  it("formats with one decimal mm by default", () => {
    expect(formatMm(42.04)).toBe("42.0 mm");
  });

  it("includes qualifier when provided", () => {
    expect(formatMm(42, { qualifier: "assumed" })).toBe("42.0 mm (assumed)");
  });

  it("clamps to one decimal even for whole numbers", () => {
    expect(formatMm(7)).toBe("7.0 mm");
  });
});
