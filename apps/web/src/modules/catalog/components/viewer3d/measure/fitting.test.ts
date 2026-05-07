import { describe, it, expect } from "vitest";

import { fitPlane } from "./fitting";
import { weld } from "../lib/welder";

function cubePositions(): Float32Array {
  const v = (x: number, y: number, z: number) => [x, y, z];
  const a = -0.5, b = 0.5;
  const corners = [
    v(a, a, a), v(b, a, a), v(b, b, a), v(a, b, a),
    v(a, a, b), v(b, a, b), v(b, b, b), v(a, b, b),
  ];
  const faces: number[][] = [
    [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
    [0, 4, 5], [0, 5, 1], [3, 6, 7], [3, 2, 6],
    [0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2],
  ];
  const out: number[] = [];
  for (const tri of faces) for (const ci of tri) out.push(...corners[ci]!);
  return new Float32Array(out);
}

describe("fitPlane", () => {
  it("cube -z face: normal aligned with z axis, weak=false", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const plane = fitPlane(welded, [0, 1], 0);
    expect(Math.abs(plane.normal.z)).toBeGreaterThan(0.999);
    expect(Math.abs(plane.normal.x)).toBeLessThan(0.001);
    expect(Math.abs(plane.normal.y)).toBeLessThan(0.001);
    expect(plane.weak).toBe(false);
    expect(plane.seedTriangleId).toBe(0);
  });

  it("single triangle cluster sets weak=true", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const plane = fitPlane(welded, [0], 0);
    expect(plane.weak).toBe(true);
  });

  it("centroid is at the cube face midpoint", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const plane = fitPlane(welded, [0, 1], 0);
    expect(Math.abs(plane.centroid.x)).toBeLessThan(0.01);
    expect(Math.abs(plane.centroid.y)).toBeLessThan(0.01);
    expect(plane.centroid.z).toBeCloseTo(-0.5, 2);
  });
});
