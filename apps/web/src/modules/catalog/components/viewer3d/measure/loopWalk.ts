import type { WeldedMesh } from "../lib/welder";
import type { SharpEdgeGraph, SharpEdgeId } from "../lib/sharpEdgeGraph";

export const LOOP_MAX_VERTICES = 512;

const TURN_REJECT_RAD = (90 * Math.PI) / 180;

/** Walk a closed loop of sharp edges starting at `startEdge`.
 *  Returns welded vertex indices in loop order, or null on:
 *    - loop > LOOP_MAX_VERTICES
 *    - ambiguous junction (>= 3 sharp edges incident to a vertex)
 *    - two consecutive >90° turns
 *    - open path (loop did not close) */
export function walkEdgeLoop(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  startEdge: SharpEdgeId,
): number[] | null {
  if (startEdge < 0 || startEdge * 2 + 1 >= graph.edges.length) return null;
  const startV = graph.edges[startEdge * 2]!;
  const nextV = graph.edges[startEdge * 2 + 1]!;
  const visited = new Set<SharpEdgeId>([startEdge]);
  const order: number[] = [startV, nextV];

  let prev = startV;
  let current = nextV;
  let prevDir = subVec(welded, current, prev);
  normalize(prevDir);
  let lastTurnExceededLimit = false;

  while (order.length <= LOOP_MAX_VERTICES) {
    // Look up incident sharp edges at `current`.
    const start = graph.vertexEdgesStart[current]!;
    const end = graph.vertexEdgesStart[current + 1]!;
    const candidates: SharpEdgeId[] = [];
    for (let i = start; i < end; i++) {
      const eid = graph.vertexEdges[i]!;
      if (!visited.has(eid)) candidates.push(eid);
    }

    if (candidates.length === 0) return null; // dead end
    if (candidates.length >= 3) return null; // ambiguous junction

    let bestEdge: SharpEdgeId;
    if (candidates.length === 1) {
      bestEdge = candidates[0]!;
    } else {
      // Two candidates — pick the one minimizing turn (max dot with prevDir).
      let bestDot = -Infinity;
      bestEdge = candidates[0]!;
      for (const eid of candidates) {
        const other = otherEndpoint(graph, eid, current);
        const dir = subVec(welded, other, current);
        normalize(dir);
        const d = dir[0] * prevDir[0] + dir[1] * prevDir[1] + dir[2] * prevDir[2];
        if (d > bestDot) {
          bestDot = d;
          bestEdge = eid;
        }
      }
    }

    visited.add(bestEdge);
    const nextVertex = otherEndpoint(graph, bestEdge, current);
    const dir = subVec(welded, nextVertex, current);
    normalize(dir);
    const turnDot = dir[0] * prevDir[0] + dir[1] * prevDir[1] + dir[2] * prevDir[2];
    const turnRad = Math.acos(Math.max(-1, Math.min(1, turnDot)));
    if (turnRad > TURN_REJECT_RAD) {
      if (lastTurnExceededLimit) return null;
      lastTurnExceededLimit = true;
    } else {
      lastTurnExceededLimit = false;
    }

    if (nextVertex === startV) {
      // Closed.
      return order;
    }

    order.push(nextVertex);
    prev = current;
    current = nextVertex;
    prevDir = dir;
  }

  return null; // exceeded LOOP_MAX_VERTICES
}

function otherEndpoint(graph: SharpEdgeGraph, edgeId: SharpEdgeId, vertex: number): number {
  const v0 = graph.edges[edgeId * 2]!;
  const v1 = graph.edges[edgeId * 2 + 1]!;
  return v0 === vertex ? v1 : v0;
}

function subVec(welded: WeldedMesh, a: number, b: number): [number, number, number] {
  return [
    welded.positions[a * 3]! - welded.positions[b * 3]!,
    welded.positions[a * 3 + 1]! - welded.positions[b * 3 + 1]!,
    welded.positions[a * 3 + 2]! - welded.positions[b * 3 + 2]!,
  ];
}

function normalize(v: [number, number, number]): void {
  const len = Math.hypot(v[0], v[1], v[2]) || 1;
  v[0] /= len;
  v[1] /= len;
  v[2] /= len;
}
