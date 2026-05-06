import { useMemo } from "react";
import type { BufferGeometry } from "three";

export const LARGE_FILE_BYTES = 50 * 1024 * 1024;
export const LARGE_MESH_TRIANGLES = 1_000_000;

export type PerfGuard = {
  /** True if the file's STL is large enough to ask the user for confirmation. */
  needsConfirmForSize: (sizeBytes: number | undefined) => boolean;
  /** Triangle count derived from a parsed BufferGeometry, or 0 if unknown. */
  triangleCount: (geometry: BufferGeometry | null) => number;
  /** True when the mesh is dense enough to warn + drop OrbitControls damping. */
  isLargeMesh: (geometry: BufferGeometry | null) => boolean;
};

export function usePerfGuard(): PerfGuard {
  return useMemo(
    () => ({
      needsConfirmForSize: (size) =>
        typeof size === "number" && size > LARGE_FILE_BYTES,
      triangleCount: (g) => {
        if (g === null) return 0;
        const pos = g.getAttribute("position");
        if (pos === undefined) return 0;
        return Math.floor(pos.count / 3);
      },
      isLargeMesh: (g) => {
        if (g === null) return false;
        const pos = g.getAttribute("position");
        if (pos === undefined) return false;
        return Math.floor(pos.count / 3) > LARGE_MESH_TRIANGLES;
      },
    }),
    [],
  );
}
