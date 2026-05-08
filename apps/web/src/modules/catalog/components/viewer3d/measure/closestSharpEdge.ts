import { Vector3 } from "three";

import { BOUNDARY, type WeldedMesh } from "../lib/welder";
import type { SharpEdgeGraph, SharpEdgeId } from "../lib/sharpEdgeGraph";

const NO_SHARP = 0xffffffff;
const BFS_DEPTH = 3;

/** Find the welded sharp edge id closest to `hitPoint` starting from `hitTriangle`.
 *  First tries the 3 edges of the hit triangle; if none are sharp, BFS up to depth 3
 *  via welded.adjacency. Returns the SharpEdgeId of the closest sharp edge, or null.
 *  Boundary edges (open mesh) are treated as sharp per spec §4.1 — a hole rim on a
 *  non-watertight STL still produces a closed loop along the mesh boundary. */
export function closestSharpEdge(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  hitTriangle: number,
  hitPoint: Vector3,
): SharpEdgeId | null {
  if (hitTriangle === BOUNDARY) return null;
  const direct = pickClosestSharpEdgeOnTriangle(welded, graph, hitTriangle, hitPoint);
  if (direct !== null) return direct;
  return bfsFindSharpEdge(welded, graph, hitTriangle, hitPoint, BFS_DEPTH);
}

function pickClosestSharpEdgeOnTriangle(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  triangleId: number,
  hitPoint: Vector3,
): SharpEdgeId | null {
  let best: { id: SharpEdgeId; dist: number } | null = null;
  for (let e = 0; e < 3; e++) {
    const id = graph.triangleEdgeIds[triangleId * 3 + e]!;
    if (id === NO_SHARP) continue;
    const dist = pointToWeldedEdgeDistance(welded, graph, id, hitPoint);
    if (best === null || dist < best.dist) best = { id, dist };
  }
  return best?.id ?? null;
}

function bfsFindSharpEdge(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  startTri: number,
  hitPoint: Vector3,
  maxDepth: number,
): SharpEdgeId | null {
  const visited = new Set<number>([startTri]);
  let frontier: number[] = [startTri];
  let best: { id: SharpEdgeId; dist: number } | null = null;
  for (let depth = 0; depth < maxDepth; depth++) {
    const nextFrontier: number[] = [];
    for (const t of frontier) {
      for (let e = 0; e < 3; e++) {
        const neighbor = welded.adjacency[t * 3 + e]!;
        if (neighbor === BOUNDARY || visited.has(neighbor)) continue;
        visited.add(neighbor);
        nextFrontier.push(neighbor);
        const candidate = pickClosestSharpEdgeOnTriangle(welded, graph, neighbor, hitPoint);
        if (candidate !== null) {
          const dist = pointToWeldedEdgeDistance(welded, graph, candidate, hitPoint);
          if (best === null || dist < best.dist) best = { id: candidate, dist };
        }
      }
    }
    if (best !== null) return best.id;
    frontier = nextFrontier;
    if (frontier.length === 0) break;
  }
  return null;
}

/** Perpendicular distance from `hitPoint` to the welded edge identified by `edgeId`. */
function pointToWeldedEdgeDistance(
  welded: WeldedMesh,
  graph: SharpEdgeGraph,
  edgeId: SharpEdgeId,
  hitPoint: Vector3,
): number {
  const v0Id = graph.edges[edgeId * 2]!;
  const v1Id = graph.edges[edgeId * 2 + 1]!;
  const ax = welded.positions[v0Id * 3]!;
  const ay = welded.positions[v0Id * 3 + 1]!;
  const az = welded.positions[v0Id * 3 + 2]!;
  const bx = welded.positions[v1Id * 3]!;
  const by = welded.positions[v1Id * 3 + 1]!;
  const bz = welded.positions[v1Id * 3 + 2]!;
  const dx = bx - ax;
  const dy = by - ay;
  const dz = bz - az;
  const lenSq = dx * dx + dy * dy + dz * dz;
  if (lenSq === 0) {
    return Math.hypot(hitPoint.x - ax, hitPoint.y - ay, hitPoint.z - az);
  }
  let t = ((hitPoint.x - ax) * dx + (hitPoint.y - ay) * dy + (hitPoint.z - az) * dz) / lenSq;
  t = Math.max(0, Math.min(1, t));
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  const cz = az + t * dz;
  return Math.hypot(hitPoint.x - cx, hitPoint.y - cy, hitPoint.z - cz);
}
