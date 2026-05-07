import { Html, Line } from "@react-three/drei";
import type { Color } from "three";
import { Vector3 } from "three";
import { useTranslation } from "react-i18next";

import type { Measurement } from "../types";
import { formatMm, midpoint } from "./geometry";

type Props = {
  measurements: readonly Measurement[];
  partialPoint?: { x: number; y: number; z: number } | null;
  showAssumed?: boolean;
  color: Color;
};

function projectPointToPlane(
  point: Vector3,
  centroid: Vector3,
  normal: Vector3,
): Vector3 {
  const dx = point.x - centroid.x;
  const dy = point.y - centroid.y;
  const dz = point.z - centroid.z;
  const t = dx * normal.x + dy * normal.y + dz * normal.z;
  return new Vector3(
    point.x - t * normal.x,
    point.y - t * normal.y,
    point.z - t * normal.z,
  );
}

export function MeasureOverlay({
  measurements,
  partialPoint,
  showAssumed,
  color,
}: Props) {
  const { t } = useTranslation();
  return (
    <>
      {measurements.map((m, i) => {
        if (m.kind === "p2p") {
          const mp = midpoint(m.a, m.b);
          const label =
            showAssumed === true && i === 0
              ? t("viewer3d.measure.assumed", { value: m.distanceMm.toFixed(1) })
              : formatMm(m.distanceMm);
          return (
            <group key={m.id}>
              <Line points={[m.a.toArray(), m.b.toArray()]} color={color} lineWidth={2} />
              <Html position={[mp.x, mp.y, mp.z]} center>
                <span className="rounded bg-primary px-2 py-0.5 text-xs text-primary-foreground shadow">
                  {label}
                </span>
              </Html>
            </group>
          );
        }
        if (m.kind === "p2pl") {
          const foot = projectPointToPlane(m.point, m.plane.centroid, m.plane.normal);
          const mp = midpoint(m.point, foot);
          return (
            <group key={m.id}>
              <Line points={[m.point.toArray(), foot.toArray()]} color={color} lineWidth={2} />
              <Html position={[mp.x, mp.y, mp.z]} center>
                <span className="rounded bg-primary px-2 py-0.5 text-xs text-primary-foreground shadow">
                  {formatMm(m.distanceMm)}
                </span>
              </Html>
            </group>
          );
        }
        // pl2pl: line between centroids as a visual reference
        const a = m.planeA.centroid;
        const b = m.planeB.centroid;
        const mp = midpoint(a, b);
        const angle = m.angleDeg.toFixed(1);
        return (
          <group key={m.id}>
            <Line points={[a.toArray(), b.toArray()]} color={color} lineWidth={2} />
            <Html position={[mp.x, mp.y, mp.z]} center>
              <span className="rounded bg-primary px-2 py-0.5 text-xs text-primary-foreground shadow">
                {`${m.distanceMm.toFixed(1)} mm @ ${angle}°`}
              </span>
            </Html>
          </group>
        );
      })}
      {partialPoint && (
        <mesh position={[partialPoint.x, partialPoint.y, partialPoint.z]}>
          <sphereGeometry args={[0.5, 12, 12]} />
          <meshBasicMaterial color={color} />
        </mesh>
      )}
    </>
  );
}
