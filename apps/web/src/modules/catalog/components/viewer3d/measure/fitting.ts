import { Vector3 } from "three";

import type { Plane } from "../types";
import type { WeldedMesh } from "../lib/welder";
import { triangleNormal } from "./floodFill";

function triangleArea(welded: WeldedMesh, t: number): number {
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
  const e1x = bx - ax, e1y = by - ay, e1z = bz - az;
  const e2x = cx - ax, e2y = cy - ay, e2z = cz - az;
  const nx = e1y * e2z - e1z * e2y;
  const ny = e1z * e2x - e1x * e2z;
  const nz = e1x * e2y - e1y * e2x;
  return Math.sqrt(nx * nx + ny * ny + nz * nz) * 0.5;
}

function triangleCentroid(welded: WeldedMesh, t: number): Vector3 {
  const i0 = welded.indices[3 * t]!;
  const i1 = welded.indices[3 * t + 1]!;
  const i2 = welded.indices[3 * t + 2]!;
  const x = (welded.positions[3 * i0]! + welded.positions[3 * i1]! + welded.positions[3 * i2]!) / 3;
  const y = (welded.positions[3 * i0 + 1]! + welded.positions[3 * i1 + 1]! + welded.positions[3 * i2 + 1]!) / 3;
  const z = (welded.positions[3 * i0 + 2]! + welded.positions[3 * i1 + 2]! + welded.positions[3 * i2 + 2]!) / 3;
  return new Vector3(x, y, z);
}

export function fitPlane(
  welded: WeldedMesh,
  triangleIds: readonly number[],
  seedTriangleId: number,
): Plane {
  if (triangleIds.length === 0) {
    throw new Error("fitPlane: empty cluster");
  }

  let totalArea = 0;
  const accNormal = new Vector3();
  const accCentroid = new Vector3();

  for (const t of triangleIds) {
    const area = triangleArea(welded, t);
    if (area < 1e-12) continue;
    totalArea += area;
    accNormal.addScaledVector(triangleNormal(welded, t), area);
    accCentroid.addScaledVector(triangleCentroid(welded, t), area);
  }

  if (totalArea < 1e-12) {
    return {
      centroid: triangleCentroid(welded, seedTriangleId),
      normal: triangleNormal(welded, seedTriangleId),
      triangleIds: [...triangleIds],
      seedTriangleId,
      weak: triangleIds.length === 1,
    };
  }

  return {
    centroid: accCentroid.divideScalar(totalArea),
    normal: accNormal.divideScalar(totalArea).normalize(),
    triangleIds: [...triangleIds],
    seedTriangleId,
    weak: triangleIds.length === 1,
  };
}
