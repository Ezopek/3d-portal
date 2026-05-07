import { describe, it, expect } from "vitest";
import { Box3, Vector3 } from "three";

import { framingDistance, viewPresets } from "./camera";

describe("framingDistance", () => {
  it("returns a distance proportional to the bounding sphere + margin", () => {
    const box = new Box3(new Vector3(-10, -10, -10), new Vector3(10, 10, 10));
    const d = framingDistance(box, { fovDeg: 50, margin: 1.15 });
    // Bounding sphere radius = sqrt(3) * 10 ≈ 17.3, distance ≈ 17.3 / tan(25°) * 1.15 ≈ 42.7.
    expect(d).toBeGreaterThan(35);
    expect(d).toBeLessThan(50);
  });

  it("scales with extent", () => {
    const small = framingDistance(
      new Box3(new Vector3(-1, -1, -1), new Vector3(1, 1, 1)),
      { fovDeg: 50, margin: 1.15 },
    );
    const big = framingDistance(
      new Box3(new Vector3(-100, -100, -100), new Vector3(100, 100, 100)),
      { fovDeg: 50, margin: 1.15 },
    );
    expect(big).toBeCloseTo(small * 100, 5);
  });
});

describe("viewPresets", () => {
  it("returns four named presets with unit-vector directions", () => {
    expect(Object.keys(viewPresets)).toEqual(["front", "side", "top", "iso"]);
    for (const v of Object.values(viewPresets)) {
      expect(v.length()).toBeCloseTo(1, 5);
    }
  });

  it("front looks down -z; top looks down -y; iso has positive components", () => {
    expect(viewPresets.front.z).toBeCloseTo(1, 5);
    expect(viewPresets.top.y).toBeCloseTo(1, 5);
    expect(viewPresets.iso.x).toBeGreaterThan(0);
    expect(viewPresets.iso.y).toBeGreaterThan(0);
    expect(viewPresets.iso.z).toBeGreaterThan(0);
  });
});
