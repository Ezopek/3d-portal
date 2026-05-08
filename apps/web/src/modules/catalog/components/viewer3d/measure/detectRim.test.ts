import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { weld } from "../lib/welder";
import { buildAxisAlignedCube } from "../lib/__tests__/cubeFixture";
import { detectRim } from "./detectRim";

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
