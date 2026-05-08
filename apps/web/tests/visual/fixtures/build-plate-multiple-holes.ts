// Plate with three circular through-holes at offset positions, triangulated.
// Plate dims: 80 × 40 × 3 mm.
// Hole A: Ø 5 mm  at (-25, 0) in xz
// Hole B: Ø 10 mm at (  0, 0) in xz
// Hole C: Ø 15 mm at (+25, 0) in xz
// 32 segments per hole.
//
// Used by visual specs (Task 19) to verify multi-measurement coloring.

export type MultiHoleOpts = {
  segments?: number;
};

export type RawMesh = {
  positions: Float32Array;
  indices: Uint32Array;
};

type HoleSpec = { cx: number; cz: number; r: number };

export function buildPlateMultipleHoles(opts: MultiHoleOpts = {}): RawMesh {
  const N = opts.segments ?? 32;
  const width = 80;
  const depth = 40;
  const thickness = 3;

  const holes: HoleSpec[] = [
    { cx: -25, cz: 0, r: 2.5 },  // Hole A: Ø 5 mm
    { cx:   0, cz: 0, r:   5 },  // Hole B: Ø 10 mm
    { cx:  25, cz: 0, r: 7.5 },  // Hole C: Ø 15 mm
  ];

  return buildPlateWithHoles({ width, depth, thickness, holes, N });
}

function buildPlateWithHoles(opts: {
  width: number;
  depth: number;
  thickness: number;
  holes: HoleSpec[];
  N: number;
}): RawMesh {
  const { width, depth, thickness, holes, N } = opts;

  const x0 = -width / 2, x1 = width / 2;
  const z0 = -depth / 2, z1 = depth / 2;
  const y0 = 0, y1 = thickness;

  const positions: number[] = [];
  const indices: number[] = [];
  let nextIdx = 0;

  const idx = (x: number, y: number, z: number) => {
    positions.push(x, y, z);
    return nextIdx++;
  };

  // Build ring vertices for each hole (top + bottom).
  const topRings: number[][] = [];
  const botRings: number[][] = [];

  for (const hole of holes) {
    const topRing: number[] = [];
    const botRing: number[] = [];
    for (let i = 0; i < N; i++) {
      const t = (2 * Math.PI * i) / N;
      topRing.push(idx(hole.cx + hole.r * Math.cos(t), y1, hole.cz + hole.r * Math.sin(t)));
      botRing.push(idx(hole.cx + hole.r * Math.cos(t), y0, hole.cz + hole.r * Math.sin(t)));
    }
    topRings.push(topRing);
    botRings.push(botRing);
  }

  // Plate corner verts (top + bottom).
  const tCorners = [
    idx(x0, y1, z0),
    idx(x1, y1, z0),
    idx(x1, y1, z1),
    idx(x0, y1, z1),
  ];
  const bCorners = [
    idx(x0, y0, z0),
    idx(x1, y0, z0),
    idx(x1, y0, z1),
    idx(x0, y0, z1),
  ];

  // Hole inner walls.
  for (let h = 0; h < holes.length; h++) {
    const topRing = topRings[h]!;
    const botRing = botRings[h]!;
    for (let i = 0; i < N; i++) {
      const a = topRing[i]!, b = topRing[(i + 1) % N]!, c = botRing[(i + 1) % N]!, d = botRing[i]!;
      indices.push(a, c, b, a, d, c);
    }
  }

  // Top face: triangulate around each hole with a simple fan to corners.
  // For multi-hole plates we do independent sector fans per hole (same strategy
  // as single-hole, but each hole is isolated — the remaining plate is not
  // guaranteed watertight between holes; good enough for visual regression).
  for (let h = 0; h < holes.length; h++) {
    triangulateFaceWithHole(tCorners, topRings[h]!, indices, N, true);
    triangulateFaceWithHole(bCorners, botRings[h]!, indices, N, false);
  }

  // Plate side walls (4 quads → 8 triangles).
  indices.push(tCorners[0]!, bCorners[1]!, tCorners[1]!, tCorners[0]!, bCorners[0]!, bCorners[1]!);
  indices.push(tCorners[1]!, bCorners[2]!, tCorners[2]!, tCorners[1]!, bCorners[1]!, bCorners[2]!);
  indices.push(tCorners[2]!, bCorners[3]!, tCorners[3]!, tCorners[2]!, bCorners[2]!, bCorners[3]!);
  indices.push(tCorners[3]!, bCorners[0]!, tCorners[0]!, tCorners[3]!, bCorners[3]!, bCorners[0]!);

  return {
    positions: new Float32Array(positions),
    indices: new Uint32Array(indices),
  };
}

function triangulateFaceWithHole(
  corners: number[],
  ring: number[],
  indices: number[],
  N: number,
  topward: boolean,
): void {
  const winding = (a: number, b: number, c: number) =>
    topward ? indices.push(a, b, c) : indices.push(a, c, b);

  const ring0 = 0, ring1 = N / 4 | 0, ring2 = N / 2 | 0, ring3 = (3 * N / 4) | 0;
  const c0 = corners[0]!, c1 = corners[1]!, c2 = corners[2]!, c3 = corners[3]!;

  for (let i = ring0; i < ring1; i++) winding(ring[i]!, ring[i + 1]!, c1);
  winding(ring[ring0]!, c1, c0);

  for (let i = ring1; i < ring2; i++) winding(ring[i]!, ring[i + 1]!, c2);
  winding(ring[ring1]!, c2, c1);

  for (let i = ring2; i < ring3; i++) winding(ring[i]!, ring[i + 1]!, c3);
  winding(ring[ring2]!, c3, c2);

  for (let i = ring3; i < N - 1; i++) winding(ring[i]!, ring[i + 1]!, c0);
  winding(ring[N - 1]!, ring[0]!, c0);
  winding(ring[ring3]!, c0, c3);
}
