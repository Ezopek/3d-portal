import { useEffect, useMemo } from "react";
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  MeshBasicMaterial,
} from "three";

import type { WeldedMesh } from "../lib/welder";

type Props = {
  welded: WeldedMesh;
  triangleIds: readonly number[];
  color: Color;
  opacity: number;
};

export function ClusterOverlay({ welded, triangleIds, color, opacity }: Props) {
  const geometry = useMemo(() => {
    const g = new BufferGeometry();
    const positionsArr = new Float32Array(triangleIds.length * 9);
    for (let i = 0; i < triangleIds.length; i += 1) {
      const t = triangleIds[i]!;
      const i0 = welded.indices[3 * t]!;
      const i1 = welded.indices[3 * t + 1]!;
      const i2 = welded.indices[3 * t + 2]!;
      const dst = i * 9;
      positionsArr[dst] = welded.positions[3 * i0]!;
      positionsArr[dst + 1] = welded.positions[3 * i0 + 1]!;
      positionsArr[dst + 2] = welded.positions[3 * i0 + 2]!;
      positionsArr[dst + 3] = welded.positions[3 * i1]!;
      positionsArr[dst + 4] = welded.positions[3 * i1 + 1]!;
      positionsArr[dst + 5] = welded.positions[3 * i1 + 2]!;
      positionsArr[dst + 6] = welded.positions[3 * i2]!;
      positionsArr[dst + 7] = welded.positions[3 * i2 + 1]!;
      positionsArr[dst + 8] = welded.positions[3 * i2 + 2]!;
    }
    g.setAttribute("position", new BufferAttribute(positionsArr, 3));
    g.computeVertexNormals();
    return g;
  }, [welded, triangleIds]);

  const material = useMemo(
    () =>
      new MeshBasicMaterial({
        color,
        transparent: true,
        opacity,
        depthTest: true,
        polygonOffset: true,
        polygonOffsetFactor: -1,
        polygonOffsetUnits: -1,
      }),
    [color, opacity],
  );

  useEffect(() => {
    return () => geometry.dispose();
  }, [geometry]);

  useEffect(() => {
    return () => material.dispose();
  }, [material]);

  return <mesh geometry={geometry} material={material} />;
}
