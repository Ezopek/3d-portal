import { describe, it, expect } from "vitest";

import { floodFill } from "./floodFill";
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

describe("floodFill", () => {
  it("cube face seed yields a 2-triangle cluster", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const cluster = floodFill(welded, 0, 1);
    expect(cluster.size).toBe(2);
    expect(cluster.has(0)).toBe(true);
  });

  it("single-triangle (boundary) seed yields a 1-triangle cluster", () => {
    const positions = new Float32Array([
      0, 0, 0,
      1, 0, 0,
      0, 1, 0,
    ]);
    const welded = weld(positions, Math.sqrt(2));
    const cluster = floodFill(welded, 0, 1);
    expect(cluster.size).toBe(1);
  });

  it("does NOT creep across gentle curvature (seed-comparison rule)", () => {
    // Build a tessellated dome strip: 16 triangles arranged so each adjacent
    // pair differs by 0.8°, but the whole strip curves through ~12°.
    // At tolerance 1.5°, neighbour-comparison would walk the entire strip;
    // seed-comparison should stop after only triangles within 1.5° of seed.
    const positions: number[] = [];
    const segments = 16;
    const radius = 100;
    const heightStep = 0.5;
    for (let i = 0; i < segments; i += 1) {
      const angle1 = (i * 0.8 * Math.PI) / 180;
      const angle2 = ((i + 1) * 0.8 * Math.PI) / 180;
      const x1 = radius * Math.sin(angle1);
      const z1 = radius * Math.cos(angle1);
      const x2 = radius * Math.sin(angle2);
      const z2 = radius * Math.cos(angle2);
      const y = i * heightStep;
      positions.push(x1, y, z1, x2, y, z2, x1, y + 1, z1);
    }
    const welded = weld(new Float32Array(positions), 200);
    const seed = Math.floor(welded.indices.length / 3 / 2);
    const cluster = floodFill(welded, seed, 1.5);
    // With seed-comparison, only tris within ±1.5° of seed normal pass.
    expect(cluster.size).toBeLessThan(welded.indices.length / 3);
  });
});
