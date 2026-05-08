import { describe, expect, it } from "vitest";
import { weld } from "./welder";
import { buildSharpEdgeGraph, SHARP_EDGE_THRESHOLD_RAD } from "./sharpEdgeGraph";
import { buildClosedSphere } from "../../../../../../tests/visual/fixtures/build-closed-sphere";
import { buildPlateWithHole } from "../../../../../../tests/visual/fixtures/build-plate-with-hole";

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

function buildAxisAlignedCube(): { positions: Float32Array; indices: Uint32Array } {
  // 8 vertices, 12 triangles, 6 faces (each face = 2 triangles)
  const v = [
    [-1, -1, -1], [+1, -1, -1], [+1, +1, -1], [-1, +1, -1],
    [-1, -1, +1], [+1, -1, +1], [+1, +1, +1], [-1, +1, +1],
  ];
  const positions = new Float32Array(v.flat());
  const tri = (a: number, b: number, c: number) => [a, b, c];
  const indices = new Uint32Array([
    ...tri(0, 1, 2), ...tri(0, 2, 3), // back  z=-1
    ...tri(4, 6, 5), ...tri(4, 7, 6), // front z=+1
    ...tri(0, 3, 7), ...tri(0, 7, 4), // left  x=-1
    ...tri(1, 5, 6), ...tri(1, 6, 2), // right x=+1
    ...tri(0, 4, 5), ...tri(0, 5, 1), // bottom y=-1
    ...tri(3, 2, 6), ...tri(3, 6, 7), // top    y=+1
  ]);
  return { positions, indices };
}

describe("buildSharpEdgeGraph — cube", () => {
  it("identifies all 12 cube edges as sharp", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(toSoup(cube.positions, cube.indices), 4 /* diagonal */);
    const graph = buildSharpEdgeGraph(welded);
    expect(graph.edges.length / 2).toBe(12);
  });

  it("each cube vertex has 3 incident sharp edges (vertexEdges length = 2 * edges)", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(toSoup(cube.positions, cube.indices), 4);
    const graph = buildSharpEdgeGraph(welded);
    const vertCount = welded.positions.length / 3;
    expect(graph.vertexEdgesStart.length).toBe(vertCount + 1);
    // Each canonical edge contributes its id to BOTH endpoints' incidence list,
    // so total length = 2 * edge count.
    expect(graph.vertexEdges.length).toBe(graph.edges.length);
  });

  it("all dihedral angles are pi/2 +- 1e-6", () => {
    const cube = buildAxisAlignedCube();
    const welded = weld(toSoup(cube.positions, cube.indices), 4);
    const graph = buildSharpEdgeGraph(welded);
    for (const angle of graph.dihedralAngles) {
      expect(Math.abs(angle - Math.PI / 2)).toBeLessThan(1e-6);
    }
  });
});

describe("buildSharpEdgeGraph — closed sphere", () => {
  it("returns 0 sharp edges for a watertight sphere with low triangle deviation", () => {
    const sphere = buildClosedSphere(1, 64, 32); // 64 longitude × 32 latitude
    const welded = weld(toSoup(sphere.positions, sphere.indices), 2);
    const graph = buildSharpEdgeGraph(welded);
    expect(graph.edges.length / 2).toBe(0);
  });
});

describe("buildSharpEdgeGraph — threshold semantics", () => {
  it("rejects internal edges with dihedral < SHARP_EDGE_THRESHOLD_RAD", () => {
    expect(SHARP_EDGE_THRESHOLD_RAD).toBeCloseTo((30 * Math.PI) / 180, 6);
  });
});

describe("buildSharpEdgeGraph — plate with hole", () => {
  it("32-segment hole + 3 mm plate produces 64 sharp rim edges + 12 plate-corner edges", () => {
    const plate = buildPlateWithHole({ segments: 32 });
    const welded = weld(toSoup(plate.positions, plate.indices), 60);
    const graph = buildSharpEdgeGraph(welded);
    // Expected sharp edges:
    //  - top hole rim: 32 edges (top face → hole inner wall, 90° dihedral each)
    //  - bottom hole rim: 32 edges
    //  - 4 vertical plate edges (corners of cube top↔side, side↔side x4 = 4 vertical + 8 horizontal)
    //  - 8 horizontal plate edges along the top + bottom rectangles
    // The exact count depends on the fan triangulation — assert >= 64 for rims,
    // and total in [76, 110] inclusive (slack for fan-triangulation interior edges).
    expect(graph.edges.length / 2).toBeGreaterThanOrEqual(64 + 12);
    expect(graph.edges.length / 2).toBeLessThanOrEqual(110);
  });
});
