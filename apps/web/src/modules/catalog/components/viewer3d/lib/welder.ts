export type WeldedMesh = {
  positions: Float32Array;
  indices: Uint32Array;
  /** triangleCount * 3; each slot stores the neighbour triangle id across the
   * edge (i, (i+1)%3), or 0xFFFFFFFF for boundary edges. */
  adjacency: Uint32Array;
  /** sourceToWelded[sourceFace] = weldedTriangle */
  sourceToWelded: Uint32Array;
  /** weldedToSourceStart[i]..weldedToSourceStart[i+1] indexes weldedToSource */
  weldedToSourceStart: Uint32Array;
  weldedToSource: Uint32Array;
};

const MIN_GRANULARITY_MM = 1e-5;
const BOUNDARY = 0xffffffff;

export function weld(
  positions: Float32Array,
  bboxDiagonal: number,
): WeldedMesh {
  const granularity = Math.max(bboxDiagonal * 1e-6, MIN_GRANULARITY_MM);
  const sourceTriangleCount = positions.length / 9;

  // 1. Quantize and dedupe vertices.
  const vertexMap = new Map<string, number>();
  const dedupedPositions: number[] = [];
  const sourceVertexToWelded = new Uint32Array(positions.length / 3);

  for (let v = 0; v < positions.length / 3; v += 1) {
    const x = positions[3 * v]!;
    const y = positions[3 * v + 1]!;
    const z = positions[3 * v + 2]!;
    const qx = Math.round(x / granularity);
    const qy = Math.round(y / granularity);
    const qz = Math.round(z / granularity);
    const key = `${qx},${qy},${qz}`;
    let id = vertexMap.get(key);
    if (id === undefined) {
      id = dedupedPositions.length / 3;
      vertexMap.set(key, id);
      dedupedPositions.push(x, y, z);
    }
    sourceVertexToWelded[v] = id;
  }

  const dedupedPositionsArr = new Float32Array(dedupedPositions);

  // 2. Build indices and dedupe degenerate / duplicate triangles.
  const triangleKey = (a: number, b: number, c: number) => {
    const sorted = [a, b, c].sort((x, y) => x - y);
    return `${sorted[0]}-${sorted[1]}-${sorted[2]}`;
  };
  const triangleMap = new Map<string, number>();
  const indices: number[] = [];
  const sourceToWelded = new Uint32Array(sourceTriangleCount);
  const sourceLists: number[][] = [];

  for (let t = 0; t < sourceTriangleCount; t += 1) {
    const a = sourceVertexToWelded[3 * t]!;
    const b = sourceVertexToWelded[3 * t + 1]!;
    const c = sourceVertexToWelded[3 * t + 2]!;
    if (a === b || b === c || a === c) {
      // Degenerate: still record a mapping so downstream raycasts don't crash;
      // point at the first welded triangle (or 0 if none yet) — defensive only.
      sourceToWelded[t] = 0;
      continue;
    }
    const key = triangleKey(a, b, c);
    let weldedId = triangleMap.get(key);
    if (weldedId === undefined) {
      weldedId = indices.length / 3;
      triangleMap.set(key, weldedId);
      indices.push(a, b, c);
      sourceLists.push([t]);
    } else {
      sourceLists[weldedId]!.push(t);
    }
    sourceToWelded[t] = weldedId;
  }

  const indicesArr = new Uint32Array(indices);
  const triangleCount = indicesArr.length / 3;

  // 3. Build edge adjacency.
  const adjacency = new Uint32Array(triangleCount * 3);
  adjacency.fill(BOUNDARY);
  const edgeMap = new Map<string, { tri: number; slot: number }>();
  for (let t = 0; t < triangleCount; t += 1) {
    const i0 = indicesArr[3 * t]!;
    const i1 = indicesArr[3 * t + 1]!;
    const i2 = indicesArr[3 * t + 2]!;
    const edges: Array<[number, number, number]> = [
      [i0, i1, 0],
      [i1, i2, 1],
      [i2, i0, 2],
    ];
    for (const [a, b, slot] of edges) {
      const key = a < b ? `${a}-${b}` : `${b}-${a}`;
      const other = edgeMap.get(key);
      if (other === undefined) {
        edgeMap.set(key, { tri: t, slot });
      } else {
        adjacency[3 * t + slot] = other.tri;
        adjacency[3 * other.tri + other.slot] = t;
        edgeMap.delete(key);
      }
    }
  }

  // 4. Flatten weldedToSource with CSR offsets.
  const weldedToSourceStart = new Uint32Array(triangleCount + 1);
  let offset = 0;
  for (let t = 0; t < triangleCount; t += 1) {
    weldedToSourceStart[t] = offset;
    offset += sourceLists[t]?.length ?? 0;
  }
  weldedToSourceStart[triangleCount] = offset;

  const weldedToSource = new Uint32Array(offset);
  for (let t = 0; t < triangleCount; t += 1) {
    const list = sourceLists[t] ?? [];
    const base = weldedToSourceStart[t]!;
    for (let i = 0; i < list.length; i += 1) {
      weldedToSource[base + i] = list[i]!;
    }
  }

  return {
    positions: dedupedPositionsArr,
    indices: indicesArr,
    adjacency,
    sourceToWelded,
    weldedToSourceStart,
    weldedToSource,
  };
}
