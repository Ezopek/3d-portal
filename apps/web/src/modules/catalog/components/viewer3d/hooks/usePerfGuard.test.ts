import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { BufferAttribute, BufferGeometry } from "three";

import { usePerfGuard, LARGE_FILE_BYTES, LARGE_MESH_TRIANGLES } from "./usePerfGuard";

function geomWithTriangles(n: number): BufferGeometry {
  const g = new BufferGeometry();
  // 3 vertices per triangle, 3 floats per vertex.
  const positions = new Float32Array(n * 9);
  g.setAttribute("position", new BufferAttribute(positions, 3));
  return g;
}

describe("usePerfGuard", () => {
  it("flags files above LARGE_FILE_BYTES (50 MB)", () => {
    const { result } = renderHook(() => usePerfGuard());
    expect(result.current.needsConfirmForSize(LARGE_FILE_BYTES)).toBe(false);
    expect(result.current.needsConfirmForSize(LARGE_FILE_BYTES + 1)).toBe(true);
    expect(result.current.needsConfirmForSize(undefined)).toBe(false);
  });

  it("counts triangles from a BufferGeometry's position attribute", () => {
    const { result } = renderHook(() => usePerfGuard());
    expect(result.current.triangleCount(null)).toBe(0);
    expect(result.current.triangleCount(geomWithTriangles(0))).toBe(0);
    expect(result.current.triangleCount(geomWithTriangles(12))).toBe(12);
  });

  it("flags meshes with more than 1M triangles", () => {
    const { result } = renderHook(() => usePerfGuard());
    expect(result.current.isLargeMesh(geomWithTriangles(LARGE_MESH_TRIANGLES))).toBe(false);
    expect(result.current.isLargeMesh(geomWithTriangles(LARGE_MESH_TRIANGLES + 1))).toBe(true);
    expect(result.current.isLargeMesh(null)).toBe(false);
  });
});
