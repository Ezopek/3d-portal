import { describe, expect, it } from "vitest";
import { Vector3 } from "three";
import { weld } from "../lib/welder";
import { closestSharpEdge } from "./closestSharpEdge";
import { buildClosedSphere } from "../../../../../../tests/visual/fixtures/build-closed-sphere";

function buildAxisAlignedCubeSoup(): Float32Array {
  const v = [
    [-1, -1, -1], [+1, -1, -1], [+1, +1, -1], [-1, +1, -1],
    [-1, -1, +1], [+1, -1, +1], [+1, +1, +1], [-1, +1, +1],
  ];
  const tri = (a: number, b: number, c: number) => [...v[a]!, ...v[b]!, ...v[c]!];
  return new Float32Array([
    ...tri(0, 1, 2), ...tri(0, 2, 3),
    ...tri(4, 6, 5), ...tri(4, 7, 6),
    ...tri(0, 3, 7), ...tri(0, 7, 4),
    ...tri(1, 5, 6), ...tri(1, 6, 2),
    ...tri(0, 4, 5), ...tri(0, 5, 1),
    ...tri(3, 2, 6), ...tri(3, 6, 7),
  ]);
}

function expandIndexedToSoup(positions: Float32Array, indices: Uint32Array): Float32Array {
  const out = new Float32Array(indices.length * 3);
  for (let i = 0; i < indices.length; i++) {
    const v = indices[i]!;
    out[i * 3] = positions[v * 3]!;
    out[i * 3 + 1] = positions[v * 3 + 1]!;
    out[i * 3 + 2] = positions[v * 3 + 2]!;
  }
  return out;
}

describe("closestSharpEdge — cube", () => {
  it("returns a sharp edge id when the hit point is near a cube edge", () => {
    const positions = buildAxisAlignedCubeSoup();
    const welded = weld(positions, 4);
    const hit = new Vector3(0, -1, -1);
    const result = closestSharpEdge(welded, welded.graph, 0, hit);
    expect(result).not.toBeNull();
  });
});

describe("closestSharpEdge — no sharp edges available", () => {
  it("returns null on a smooth closed sphere (no sharp edges in 3-tri radius)", () => {
    const sphere = buildClosedSphere(1, 64, 32);
    // SphereGeometry produces an indexed mesh; weld() takes triangle soup.
    const soup = expandIndexedToSoup(sphere.positions, sphere.indices);
    const welded = weld(soup, 2);
    const hit = new Vector3(0, 1, 0); // top of sphere
    expect(closestSharpEdge(welded, welded.graph, 0, hit)).toBeNull();
  });
});
