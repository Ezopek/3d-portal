import { describe, expect, it } from "vitest";
import { weld } from "../lib/welder";
import { walkEdgeLoop, LOOP_MAX_VERTICES } from "./loopWalk";

function buildAxisAlignedCube(): { positions: Float32Array } {
  const v = [
    [-1, -1, -1], [+1, -1, -1], [+1, +1, -1], [-1, +1, -1],
    [-1, -1, +1], [+1, -1, +1], [+1, +1, +1], [-1, +1, +1],
  ];
  const tri = (a: number, b: number, c: number) => [...v[a]!, ...v[b]!, ...v[c]!];
  return {
    positions: new Float32Array([
      ...tri(0, 1, 2), ...tri(0, 2, 3),
      ...tri(4, 6, 5), ...tri(4, 7, 6),
      ...tri(0, 3, 7), ...tri(0, 7, 4),
      ...tri(1, 5, 6), ...tri(1, 6, 2),
      ...tri(0, 4, 5), ...tri(0, 5, 1),
      ...tri(3, 2, 6), ...tri(3, 6, 7),
    ]),
  };
}

describe("walkEdgeLoop — cube", () => {
  it("returns a 4-vertex square loop when starting on a cube edge", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(cube.positions, 4);
    // Pick any sharp edge (graph.edges[0..2]).
    const startEdge = 0;
    const loop = walkEdgeLoop(welded, welded.graph, startEdge);
    expect(loop).not.toBeNull();
    expect(loop!.length).toBe(4);
  });

  it("returns null for an invalid start edge id", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(cube.positions, 4);
    expect(walkEdgeLoop(welded, welded.graph, -1 as never)).toBeNull();
  });
});

// Plate-with-hole tests come in Task 8 (detectRim) once the fixture exists.
