import { Vector3 } from "three";

import type { Measurement } from "../types";

/** Returns a deterministic unit vector perpendicular to `axis`.
 *  Picks the world axis least parallel to `axis` and crosses with it.
 *  Camera-aware hysteresis (spec §2.3) is deferred to v1.2.x. */
export function pickTangent(axis: Vector3): { x: number; y: number; z: number } {
  const ax = Math.abs(axis.x), ay = Math.abs(axis.y), az = Math.abs(axis.z);
  const reference =
    ax < ay && ax < az
      ? new Vector3(1, 0, 0)
      : ay < az
        ? new Vector3(0, 1, 0)
        : new Vector3(0, 0, 1);
  const t = reference.clone().cross(axis).normalize();
  return { x: t.x, y: t.y, z: t.z };
}

/** 1-based display index of `m` within `all`. */
export function displayIndex(m: Measurement, all: readonly Measurement[]): number {
  return all.findIndex((x) => x.id === m.id) + 1;
}
