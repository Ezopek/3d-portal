import { Vector3 } from "three";

import type { WeldedMesh } from "../lib/welder";

const BOUNDARY = 0xffffffff;

export function triangleNormal(welded: WeldedMesh, t: number): Vector3 {
  const i0 = welded.indices[3 * t]!;
  const i1 = welded.indices[3 * t + 1]!;
  const i2 = welded.indices[3 * t + 2]!;
  const ax = welded.positions[3 * i0]!;
  const ay = welded.positions[3 * i0 + 1]!;
  const az = welded.positions[3 * i0 + 2]!;
  const bx = welded.positions[3 * i1]!;
  const by = welded.positions[3 * i1 + 1]!;
  const bz = welded.positions[3 * i1 + 2]!;
  const cx = welded.positions[3 * i2]!;
  const cy = welded.positions[3 * i2 + 1]!;
  const cz = welded.positions[3 * i2 + 2]!;
  const e1 = new Vector3(bx - ax, by - ay, bz - az);
  const e2 = new Vector3(cx - ax, cy - ay, cz - az);
  return e1.cross(e2).normalize();
}

/**
 * BFS over edge-adjacency. Accepts a candidate triangle iff
 * `acos(|n_candidate · n_seed|) <= toleranceDeg`. Seed-comparison
 * eliminates curvature creep — this is intentional (spec §6.2, P2-5).
 */
export function floodFill(
  welded: WeldedMesh,
  seedTriangleId: number,
  toleranceDeg: number,
): Set<number> {
  const cluster = new Set<number>([seedTriangleId]);
  const seedNormal = triangleNormal(welded, seedTriangleId);
  const cosThreshold = Math.cos((toleranceDeg * Math.PI) / 180);
  const queue: number[] = [seedTriangleId];

  while (queue.length > 0) {
    const t = queue.shift()!;
    for (let slot = 0; slot < 3; slot += 1) {
      const neighbour = welded.adjacency[3 * t + slot]!;
      if (neighbour === BOUNDARY || cluster.has(neighbour)) continue;
      const n = triangleNormal(welded, neighbour);
      const dot = Math.abs(n.dot(seedNormal));
      if (dot >= cosThreshold) {
        cluster.add(neighbour);
        queue.push(neighbour);
      }
    }
  }

  return cluster;
}
