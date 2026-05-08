// Plate with a single circular through-hole, triangulated and STL-encoded.
// Plate dims: 50 × 30 × 3 mm. Hole: Ø 10 mm at center. 32 segments.

export type PlateOpts = {
  width?: number;
  depth?: number;
  thickness?: number;
  holeRadius?: number;
  segments?: number;
};

export type RawMesh = {
  positions: Float32Array;
  indices: Uint32Array;
};

export function buildPlateWithHole(opts: PlateOpts = {}): RawMesh {
  const width = opts.width ?? 50;
  const depth = opts.depth ?? 30;
  const thickness = opts.thickness ?? 3;
  const r = opts.holeRadius ?? 5; // Ø 10 mm
  const N = opts.segments ?? 32;

  const x0 = -width / 2, x1 = width / 2;
  const z0 = -depth / 2, z1 = depth / 2;
  const y0 = 0, y1 = thickness;

  const positions: number[] = [];
  const indices: number[] = [];
  const idx = (x: number, y: number, z: number) => {
    positions.push(x, y, z);
    return positions.length / 3 - 1;
  };

  // Hole center at origin, vertices on circle (top + bottom).
  const topRing: number[] = [];
  const botRing: number[] = [];
  for (let i = 0; i < N; i++) {
    const t = (2 * Math.PI * i) / N;
    topRing.push(idx(r * Math.cos(t), y1, r * Math.sin(t)));
    botRing.push(idx(r * Math.cos(t), y0, r * Math.sin(t)));
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

  // Hole inner wall (cylinder between topRing and botRing).
  for (let i = 0; i < N; i++) {
    const a = topRing[i]!, b = topRing[(i + 1) % N]!, c = botRing[(i + 1) % N]!, d = botRing[i]!;
    indices.push(a, c, b, a, d, c); // CCW from outside (inward-facing wall normal)
  }

  // Top + bottom faces of the plate, with the circular hole carved out.
  // Triangulate as a fan from each ring vertex to the nearest plate corners.
  // For simplicity: split into 4 trapezoid sectors (one per plate edge).
  // Each sector: connects ring quadrant to one plate edge via fan triangles.
  // (Detailed triangulation below.)
  triangulateFaceWithHole(tCorners, topRing, indices, N, /* topward */ true);
  triangulateFaceWithHole(bCorners, botRing, indices, N, /* topward */ false);

  // Plate side walls (4 quads → 8 triangles).
  // Front (z = z0): tCorners[0]→[1] / bCorners[0]→[1]
  indices.push(tCorners[0]!, bCorners[1]!, tCorners[1]!, tCorners[0]!, bCorners[0]!, bCorners[1]!);
  // Right (x = x1): tCorners[1]→[2] / bCorners[1]→[2]
  indices.push(tCorners[1]!, bCorners[2]!, tCorners[2]!, tCorners[1]!, bCorners[1]!, bCorners[2]!);
  // Back (z = z1): tCorners[2]→[3] / bCorners[2]→[3]
  indices.push(tCorners[2]!, bCorners[3]!, tCorners[3]!, tCorners[2]!, bCorners[2]!, bCorners[3]!);
  // Left (x = x0): tCorners[3]→[0] / bCorners[3]→[0]
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
  // Quartile-based fan: split ring into 4 quadrants matching plate corners.
  // For each plate edge, fan from that edge's two corners to the corresponding ring quadrant.
  // Ring vertex i has angle 2πi/N. Quadrants: 0..N/4, N/4..N/2, N/2..3N/4, 3N/4..N.
  const winding = (a: number, b: number, c: number) => topward ? indices.push(a, b, c) : indices.push(a, c, b);

  // Map quadrant → corner pair.
  // Plate corners 0..3 in CCW (top view): 0=(x0,z0), 1=(x1,z0), 2=(x1,z1), 3=(x0,z1).
  // Pick a ring vertex closest to each corner direction; for simplicity, use ring index N*k/4 for k=0..3.
  const ring0 = 0, ring1 = N / 4 | 0, ring2 = N / 2 | 0, ring3 = (3 * N / 4) | 0;
  const c0 = corners[0]!, c1 = corners[1]!, c2 = corners[2]!, c3 = corners[3]!;

  // Sector 0: ring[ring0..ring1] + corner c1 + c0
  for (let i = ring0; i < ring1; i++) {
    winding(ring[i]!, ring[i + 1]!, c1);
  }
  winding(ring[ring0]!, c1, c0);

  for (let i = ring1; i < ring2; i++) {
    winding(ring[i]!, ring[i + 1]!, c2);
  }
  winding(ring[ring1]!, c2, c1);

  for (let i = ring2; i < ring3; i++) {
    winding(ring[i]!, ring[i + 1]!, c3);
  }
  winding(ring[ring2]!, c3, c2);

  for (let i = ring3; i < N - 1; i++) {
    winding(ring[i]!, ring[i + 1]!, c0);
  }
  // Wrap: ring[N-1] → ring[0]
  winding(ring[N - 1]!, ring[0]!, c0);
  winding(ring[ring3]!, c0, c3);
}
