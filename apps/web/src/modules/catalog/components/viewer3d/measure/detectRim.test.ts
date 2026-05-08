import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { weld } from "../lib/welder";
import { buildAxisAlignedCube } from "../lib/__tests__/cubeFixture";
import { buildPlateWithHole } from "../../../../../../tests/visual/fixtures/build-plate-with-hole";
import { detectRim } from "./detectRim";

/** Expand an indexed mesh to triangle soup so weld() can process it. */
function toSoup(positions: Float32Array, indices: Uint32Array): Float32Array {
  const soup = new Float32Array(indices.length * 3);
  for (let i = 0; i < indices.length; i++) {
    const vi = indices[i]! * 3;
    soup[i * 3] = positions[vi]!;
    soup[i * 3 + 1] = positions[vi + 1]!;
    soup[i * 3 + 2] = positions[vi + 2]!;
  }
  return soup;
}

describe("detectRim — false-positives", () => {
  it("cube edge → null (square loop, fitCircle rejects)", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(cube.positions, 4);
    // Hit triangle 0 near the edge between (-1,-1,-1) and (+1,-1,-1).
    const hit = new Vector3(0, -1, -1);
    expect(detectRim(0, hit, welded, welded.graph)).toBeNull();
  });

  it("flat-quad triangle, no sharp edges anywhere → null", () => {
    const positions = new Float32Array([
      0, 0, 0, 1, 0, 0, 1, 1, 0,
      0, 0, 0, 1, 1, 0, 0, 1, 0,
    ]);
    const welded = weld(positions, 2);
    expect(detectRim(0, new Vector3(0.5, 0.5, 0), welded, welded.graph)).toBeNull();
  });
});

describe("detectRim — plate-with-hole e2e", () => {
  it("hit on a top-hole-rim triangle returns Rim with r ≈ 5", () => {
    const plate = buildPlateWithHole({ segments: 32, holeRadius: 5 });
    const welded = weld(toSoup(plate.positions, plate.indices), 60);
    // Find a triangle on the top face adjacent to the hole rim.
    // Strategy: pick the first triangle that has all three vertices near y = 3 (top)
    // and at least one vertex near radius 5 from origin in xz-plane.
    let targetTri = -1;
    const indices = welded.indices;
    for (let t = 0; t < indices.length / 3; t++) {
      let onTop = true, hasRimVert = false;
      for (let e = 0; e < 3; e++) {
        const v = indices[t * 3 + e]!;
        const y = welded.positions[v * 3 + 1]!;
        const rx = welded.positions[v * 3]!;
        const rz = welded.positions[v * 3 + 2]!;
        const rr = Math.hypot(rx, rz);
        if (Math.abs(y - 3) > 0.1) onTop = false;
        if (Math.abs(rr - 5) < 0.1) hasRimVert = true;
      }
      if (onTop && hasRimVert) {
        targetTri = t;
        break;
      }
    }
    expect(targetTri).toBeGreaterThan(-1);
    // Hit point: a rim vertex
    const v = indices[targetTri * 3]!;
    const hit = new Vector3(welded.positions[v * 3]!, welded.positions[v * 3 + 1]!, welded.positions[v * 3 + 2]!);
    const rim = detectRim(targetTri, hit, welded, welded.graph);
    expect(rim).not.toBeNull();
    expect(rim!.radius).toBeCloseTo(5, 2);
  });
});
