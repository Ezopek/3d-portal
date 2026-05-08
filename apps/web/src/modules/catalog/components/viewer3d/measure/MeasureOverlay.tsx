import { Html, Line } from "@react-three/drei";
import { Vector3 } from "three";
import { useTranslation } from "react-i18next";

import { paletteFor } from "../lib/palette";
import type { Measurement } from "../types";
import { formatMm, midpoint } from "./geometry";

type Props = {
  measurements: readonly Measurement[];
  partialPoint?: { x: number; y: number; z: number } | null;
  showAssumed?: boolean;
};

const LABEL_CLASS =
  "whitespace-nowrap rounded bg-zinc-900/95 px-2 py-0.5 text-xs font-medium text-white shadow-md ring-1 ring-white/15";

function projectPointToPlane(point: Vector3, centroid: Vector3, normal: Vector3): Vector3 {
  const dx = point.x - centroid.x;
  const dy = point.y - centroid.y;
  const dz = point.z - centroid.z;
  const t = dx * normal.x + dy * normal.y + dz * normal.z;
  return new Vector3(point.x - t * normal.x, point.y - t * normal.y, point.z - t * normal.z);
}

export function MeasureOverlay({ measurements, partialPoint, showAssumed }: Props) {
  const { t } = useTranslation();
  return (
    <>
      {measurements.map((m, i) => {
        const num = `#${i + 1}`;
        const sel1 = paletteFor(m.colorIndex, "sel1");
        const sel2 = paletteFor(m.colorIndex, "sel2");
        if (m.kind === "p2p") {
          const mp = midpoint(m.a, m.b);
          const value =
            showAssumed === true && i === 0
              ? t("viewer3d.measure.assumed", { value: m.distanceMm.toFixed(1) })
              : formatMm(m.distanceMm);
          return (
            <group key={m.id}>
              <Line points={[m.a.toArray(), m.b.toArray()]} color={sel1} lineWidth={2} />
              <mesh position={[m.a.x, m.a.y, m.a.z]}>
                <sphereGeometry args={[0.6, 12, 12]} />
                <meshBasicMaterial color={sel1} />
              </mesh>
              <mesh position={[m.b.x, m.b.y, m.b.z]}>
                <sphereGeometry args={[0.6, 12, 12]} />
                <meshBasicMaterial color={sel2} />
              </mesh>
              <Html position={[mp.x, mp.y, mp.z]} center>
                <span className={LABEL_CLASS}>
                  {num} {value}
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
              <Line points={[m.point.toArray(), foot.toArray()]} color={sel1} lineWidth={2} />
              <mesh position={[m.point.x, m.point.y, m.point.z]}>
                <sphereGeometry args={[0.6, 12, 12]} />
                <meshBasicMaterial color={sel2} />
              </mesh>
              <Html position={[mp.x, mp.y, mp.z]} center>
                <span className={LABEL_CLASS}>
                  {num} {formatMm(m.distanceMm)}
                </span>
              </Html>
            </group>
          );
        }
        if (m.kind === "pl2pl") {
          // Diagonal line for closest, perpendicular for parallel.
          const angle = m.angleDeg.toFixed(1);
          let a: Vector3;
          let b: Vector3;
          if (m.pl2plKind === "parallel") {
            const cA = m.planeA.centroid;
            const cB = m.planeB.centroid;
            const nA = m.planeA.normal;
            const signed = (cB.x - cA.x) * nA.x + (cB.y - cA.y) * nA.y + (cB.z - cA.z) * nA.z;
            a = cA;
            b = new Vector3(cA.x + nA.x * signed, cA.y + nA.y * signed, cA.z + nA.z * signed);
          } else {
            a = m.planeA.centroid;
            b = m.planeB.centroid;
          }
          const mp = midpoint(a, b);
          return (
            <group key={m.id}>
              <Line points={[a.toArray(), b.toArray()]} color={sel1} lineWidth={2} />
              <Html position={[mp.x, mp.y, mp.z]} center>
                <span className={LABEL_CLASS}>
                  {num} {`${formatMm(m.distanceMm)} @ ${angle}°`}
                </span>
              </Html>
            </group>
          );
        }
        return null; // diameter rendered by RimOverlay in Modal/Inline directly
      })}
      {partialPoint && (
        <mesh position={[partialPoint.x, partialPoint.y, partialPoint.z]}>
          <sphereGeometry args={[0.5, 12, 12]} />
          <meshBasicMaterial color="white" />
        </mesh>
      )}
    </>
  );
}
