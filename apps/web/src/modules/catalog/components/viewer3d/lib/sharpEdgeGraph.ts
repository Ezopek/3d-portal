import { BOUNDARY } from "./welder";

export const SHARP_EDGE_THRESHOLD_RAD = (30 * Math.PI) / 180;

/** A canonical undirected edge id. */
export type SharpEdgeId = number;

export type SharpEdgeGraph = {
  /** edges[2*i], edges[2*i+1] = the two welded vertex ids (sorted ascending). */
  edges: Uint32Array;
  /** triangles[2*i], triangles[2*i+1] = the two adjacent welded triangle ids
   *  (or BOUNDARY for the second slot if the edge is a mesh boundary). */
  triangles: Uint32Array;
  /** dihedralAngles[i] in radians; π for boundary edges (treated as sharp). */
  dihedralAngles: Float32Array;
  /** CSR vertex → incident sharp edge ids:
   *  vertexEdges[vertexEdgesStart[v] .. vertexEdgesStart[v+1]) */
  vertexEdges: Uint32Array;
  vertexEdgesStart: Uint32Array;
  /** Reverse lookup: given (welded triangle, local edge 0|1|2) → SharpEdgeId or 0xffffffff. */
  triangleEdgeIds: Uint32Array; // length = welded.indices.length
};

type GraphInput = {
  positions: Float32Array;
  indices: Uint32Array;
  adjacency: Uint32Array;
};

const NO_SHARP = 0xffffffff;

export function buildSharpEdgeGraph(welded: GraphInput): SharpEdgeGraph {
  const triCount = welded.indices.length / 3;
  const vertCount = welded.positions.length / 3;

  // Step 1+2: collect canonical edges with adjacency.
  type EdgeRecord = { v0: number; v1: number; tris: number[] };
  const edgeMap = new Map<bigint, number>();
  const edgesAll: EdgeRecord[] = [];

  const N = BigInt(vertCount);
  for (let t = 0; t < triCount; t++) {
    const i0 = welded.indices[t * 3]!;
    const i1 = welded.indices[t * 3 + 1]!;
    const i2 = welded.indices[t * 3 + 2]!;
    const tri = [i0, i1, i2];
    for (let e = 0; e < 3; e++) {
      const a = tri[e]!;
      const b = tri[(e + 1) % 3]!;
      const v0 = a < b ? a : b;
      const v1 = a < b ? b : a;
      const key = BigInt(v0) * N + BigInt(v1);
      let idx = edgeMap.get(key);
      if (idx === undefined) {
        idx = edgesAll.length;
        edgeMap.set(key, idx);
        edgesAll.push({ v0, v1, tris: [] });
      }
      edgesAll[idx]!.tris.push(t);
    }
  }

  // Step 3+4: compute face normals + dihedral per edge.
  const faceNormals = computeFaceNormals(welded);
  const dihedrals: number[] = new Array(edgesAll.length);
  const adjTris: [number, number][] = new Array(edgesAll.length);
  for (let i = 0; i < edgesAll.length; i++) {
    const rec = edgesAll[i]!;
    if (rec.tris.length === 1) {
      dihedrals[i] = Math.PI;
      adjTris[i] = [rec.tris[0]!, BOUNDARY];
    } else if (rec.tris.length === 2) {
      const t1 = rec.tris[0]!;
      const t2 = rec.tris[1]!;
      const dot =
        faceNormals[t1 * 3]! * faceNormals[t2 * 3]! +
        faceNormals[t1 * 3 + 1]! * faceNormals[t2 * 3 + 1]! +
        faceNormals[t1 * 3 + 2]! * faceNormals[t2 * 3 + 2]!;
      const clamped = Math.max(-1, Math.min(1, dot));
      dihedrals[i] = Math.acos(clamped);
      adjTris[i] = [t1, t2];
    } else {
      // Non-manifold (>= 3 incident triangles). Treat as boundary, skip.
      dihedrals[i] = Math.PI;
      adjTris[i] = [rec.tris[0]!, BOUNDARY];
    }
  }

  // Step 5: keep only sharp / boundary edges.
  const keptEdgeIds: number[] = [];
  for (let i = 0; i < edgesAll.length; i++) {
    if (dihedrals[i]! >= SHARP_EDGE_THRESHOLD_RAD || adjTris[i]![1] === BOUNDARY) {
      keptEdgeIds.push(i);
    }
  }

  const E = keptEdgeIds.length;
  const edgesOut = new Uint32Array(E * 2);
  const trianglesOut = new Uint32Array(E * 2);
  const dihedralsOut = new Float32Array(E);

  for (let k = 0; k < E; k++) {
    const orig = keptEdgeIds[k]!;
    const rec = edgesAll[orig]!;
    edgesOut[k * 2] = rec.v0;
    edgesOut[k * 2 + 1] = rec.v1;
    trianglesOut[k * 2] = adjTris[orig]![0];
    trianglesOut[k * 2 + 1] = adjTris[orig]![1];
    dihedralsOut[k] = dihedrals[orig]!;
  }

  // Step 6: CSR vertex → incident sharp edges.
  const vertexCounts = new Uint32Array(vertCount);
  for (let k = 0; k < E; k++) {
    vertexCounts[edgesOut[k * 2]!]!++;
    vertexCounts[edgesOut[k * 2 + 1]!]!++;
  }
  const vertexEdgesStart = new Uint32Array(vertCount + 1);
  for (let v = 0; v < vertCount; v++) {
    vertexEdgesStart[v + 1] = vertexEdgesStart[v]! + vertexCounts[v]!;
  }
  const vertexEdges = new Uint32Array(vertexEdgesStart[vertCount]!);
  const cursor = new Uint32Array(vertCount);
  for (let k = 0; k < E; k++) {
    const v0 = edgesOut[k * 2]!;
    const v1 = edgesOut[k * 2 + 1]!;
    vertexEdges[vertexEdgesStart[v0]! + cursor[v0]!++] = k;
    vertexEdges[vertexEdgesStart[v1]! + cursor[v1]!++] = k;
  }

  // Step 7: triangleEdgeIds reverse lookup.
  const triangleEdgeIds = new Uint32Array(welded.indices.length).fill(NO_SHARP);
  for (let k = 0; k < E; k++) {
    const v0 = edgesOut[k * 2]!;
    const v1 = edgesOut[k * 2 + 1]!;
    for (const t of [trianglesOut[k * 2]!, trianglesOut[k * 2 + 1]!]) {
      if (t === BOUNDARY) continue;
      const ia = welded.indices[t * 3]!;
      const ib = welded.indices[t * 3 + 1]!;
      const ic = welded.indices[t * 3 + 2]!;
      let local = -1;
      if ((ia === v0 && ib === v1) || (ia === v1 && ib === v0)) local = 0;
      else if ((ib === v0 && ic === v1) || (ib === v1 && ic === v0)) local = 1;
      else if ((ic === v0 && ia === v1) || (ic === v1 && ia === v0)) local = 2;
      if (local >= 0) triangleEdgeIds[t * 3 + local] = k;
    }
  }

  return {
    edges: edgesOut,
    triangles: trianglesOut,
    dihedralAngles: dihedralsOut,
    vertexEdges,
    vertexEdgesStart,
    triangleEdgeIds,
  };
}

function computeFaceNormals(welded: GraphInput): Float32Array {
  const triCount = welded.indices.length / 3;
  const out = new Float32Array(triCount * 3);
  for (let t = 0; t < triCount; t++) {
    const i0 = welded.indices[t * 3]! * 3;
    const i1 = welded.indices[t * 3 + 1]! * 3;
    const i2 = welded.indices[t * 3 + 2]! * 3;
    const ax = welded.positions[i1]! - welded.positions[i0]!;
    const ay = welded.positions[i1 + 1]! - welded.positions[i0 + 1]!;
    const az = welded.positions[i1 + 2]! - welded.positions[i0 + 2]!;
    const bx = welded.positions[i2]! - welded.positions[i0]!;
    const by = welded.positions[i2 + 1]! - welded.positions[i0 + 1]!;
    const bz = welded.positions[i2 + 2]! - welded.positions[i0 + 2]!;
    let nx = ay * bz - az * by;
    let ny = az * bx - ax * bz;
    let nz = ax * by - ay * bx;
    const len = Math.hypot(nx, ny, nz) || 1;
    nx /= len;
    ny /= len;
    nz /= len;
    out[t * 3] = nx;
    out[t * 3 + 1] = ny;
    out[t * 3 + 2] = nz;
  }
  return out;
}
