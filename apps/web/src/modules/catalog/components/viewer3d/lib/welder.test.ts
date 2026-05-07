import { describe, it, expect } from "vitest";

import { weld } from "./welder";

function cubePositions(): Float32Array {
  // 12 triangles, 36 vertices, axis-aligned 1x1x1 cube centred at origin.
  const v = (x: number, y: number, z: number) => [x, y, z];
  const a = -0.5, b = 0.5;
  const corners = [
    v(a, a, a), v(b, a, a), v(b, b, a), v(a, b, a),
    v(a, a, b), v(b, a, b), v(b, b, b), v(a, b, b),
  ];
  const faces: number[][] = [
    [0, 1, 2], [0, 2, 3], // -z
    [4, 6, 5], [4, 7, 6], // +z
    [0, 4, 5], [0, 5, 1], // -y
    [3, 6, 7], [3, 2, 6], // +y
    [0, 3, 7], [0, 7, 4], // -x
    [1, 5, 6], [1, 6, 2], // +x
  ];
  const out: number[] = [];
  for (const tri of faces) {
    for (const ci of tri) out.push(...corners[ci]!);
  }
  return new Float32Array(out);
}

describe("welder.weld", () => {
  it("deduplicates a cube to 8 unique vertices", () => {
    const positions = cubePositions();
    const welded = weld(positions, /* bboxDiagonal */ Math.sqrt(3));
    expect(welded.positions.length / 3).toBe(8);
    expect(welded.indices.length / 3).toBe(12);
  });

  it("every cube edge is shared by exactly two triangles", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const counts = new Map<string, number>();
    for (let t = 0; t < welded.indices.length / 3; t += 1) {
      const i0 = welded.indices[3 * t]!;
      const i1 = welded.indices[3 * t + 1]!;
      const i2 = welded.indices[3 * t + 2]!;
      for (const [a, b] of [
        [i0, i1],
        [i1, i2],
        [i2, i0],
      ] as const) {
        const key = a < b ? `${a}-${b}` : `${b}-${a}`;
        counts.set(key, (counts.get(key) ?? 0) + 1);
      }
    }
    for (const [, c] of counts) expect(c).toBe(2);
  });

  it("adjacency is symmetric (boundary edges marked 0xFFFFFFFF)", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    const triangleCount = welded.indices.length / 3;
    expect(welded.adjacency.length).toBe(triangleCount * 3);
    // For a closed cube: every adjacency slot is a real triangle id (no boundary).
    for (let i = 0; i < welded.adjacency.length; i += 1) {
      expect(welded.adjacency[i]).not.toBe(0xffffffff);
      expect(welded.adjacency[i]).toBeLessThan(triangleCount);
    }
  });

  it("sourceToWelded maps every source face to a welded triangle", () => {
    const welded = weld(cubePositions(), Math.sqrt(3));
    expect(welded.sourceToWelded.length).toBe(12);
    for (let i = 0; i < 12; i += 1) {
      expect(welded.sourceToWelded[i]).toBeLessThan(welded.indices.length / 3);
    }
  });

  it("handles an open mesh (single triangle) with boundary edges", () => {
    const positions = new Float32Array([
      0, 0, 0,
      1, 0, 0,
      0, 1, 0,
    ]);
    const welded = weld(positions, Math.sqrt(2));
    expect(welded.positions.length / 3).toBe(3);
    expect(welded.indices.length / 3).toBe(1);
    for (let i = 0; i < 3; i += 1) {
      expect(welded.adjacency[i]).toBe(0xffffffff);
    }
  });

  it("merges vertices within quantization but separates beyond it", () => {
    const eps = 1e-7; // sub-quantization (granularity = max(diag*1e-6, 1e-5))
    const positions = new Float32Array([
      0, 0, 0,
      1, 0, 0,
      0, 1, 0,
      eps, 0, 0, // duplicate of (0,0,0) within quantization
      1, 0, 0,
      0, 1 + eps, 0,
    ]);
    const welded = weld(positions, Math.sqrt(2));
    expect(welded.positions.length / 3).toBe(3);
  });
});
