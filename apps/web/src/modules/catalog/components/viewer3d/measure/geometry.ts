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
