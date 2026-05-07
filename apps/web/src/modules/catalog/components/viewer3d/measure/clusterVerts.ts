import { Vector3 } from "three";

import type { WeldedMesh } from "../lib/welder";

export function uniqueClusterVerts(
  welded: WeldedMesh,
  triangleIds: readonly number[],
): Vector3[] {
  const seen = new Set<number>();
  const out: Vector3[] = [];
  for (const t of triangleIds) {
    for (let s = 0; s < 3; s += 1) {
      const v = welded.indices[3 * t + s]!;
      if (seen.has(v)) continue;
      seen.add(v);
      out.push(
        new Vector3(
          welded.positions[3 * v]!,
          welded.positions[3 * v + 1]!,
          welded.positions[3 * v + 2]!,
        ),
      );
    }
  }
  return out;
}
