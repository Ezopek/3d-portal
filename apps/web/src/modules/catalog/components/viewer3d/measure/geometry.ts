import { Vector3 } from "three";

export function distance(a: Vector3, b: Vector3): number {
  return a.distanceTo(b);
}

export function midpoint(a: Vector3, b: Vector3): Vector3 {
  return new Vector3((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2);
}

export function formatMm(value: number, opts?: { qualifier?: string }): string {
  const base = `${value.toFixed(1)} mm`;
  return opts?.qualifier === undefined ? base : `${base} (${opts.qualifier})`;
}

export function distancePointToPlane(
  point: Vector3,
  centroid: Vector3,
  normal: Vector3,
): number {
  const dx = point.x - centroid.x;
  const dy = point.y - centroid.y;
  const dz = point.z - centroid.z;
  return Math.abs(dx * normal.x + dy * normal.y + dz * normal.z);
}

export function anglePlanes(nA: Vector3, nB: Vector3): number {
  const dot = Math.min(1, Math.max(-1, Math.abs(nA.dot(nB))));
  return (Math.acos(dot) * 180) / Math.PI;
}

/**
 * Wall thickness for parallel-ish planes.
 *
 * IMPORTANT: projects onto nA only. Anti-parallel normals (e.g. opposite
 * cube faces) classify as parallel via `acos(|nA·nB|)` but
 * `(nA + nB).normalize()` would collapse to NaN. See spec §6.4.
 */
export function perpendicularPlaneDistance(
  centroidA: Vector3,
  nA: Vector3,
  centroidB: Vector3,
): number {
  const dx = centroidA.x - centroidB.x;
  const dy = centroidA.y - centroidB.y;
  const dz = centroidA.z - centroidB.z;
  return Math.abs(dx * nA.x + dy * nA.y + dz * nA.z);
}

export function minVertexPairDistance(
  A: readonly Vector3[],
  B: readonly Vector3[],
): number {
  let best = Infinity;
  for (const a of A) {
    for (const b of B) {
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dz = a.z - b.z;
      const d2 = dx * dx + dy * dy + dz * dz;
      if (d2 < best) best = d2;
    }
  }
  return Math.sqrt(best);
}
