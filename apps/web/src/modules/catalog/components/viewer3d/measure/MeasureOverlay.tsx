import { Html, Line } from "@react-three/drei";
import { useTranslation } from "react-i18next";

import type { Measurement } from "../types";
import { formatMm, midpoint } from "./geometry";

type Props = {
  measurements: readonly Measurement[];
  partialPoint?: { x: number; y: number; z: number } | null;
  showAssumed?: boolean;
};

export function MeasureOverlay({ measurements, partialPoint, showAssumed }: Props) {
  const { t } = useTranslation();
  return (
    <>
      {measurements.map((m, i) => {
        const mp = midpoint(m.a, m.b);
        const label =
          showAssumed === true && i === 0
            ? t("viewer3d.measure.assumed", { value: m.distanceMm.toFixed(1) })
            : formatMm(m.distanceMm);
        return (
          <group key={m.id}>
            <Line
              points={[m.a.toArray(), m.b.toArray()]}
              color="#3b82f6"
              lineWidth={2}
            />
            <Html position={[mp.x, mp.y, mp.z]} center>
              <span className="rounded bg-primary px-2 py-0.5 text-xs text-primary-foreground shadow">
                {label}
              </span>
            </Html>
          </group>
        );
      })}
      {partialPoint && (
        <mesh position={[partialPoint.x, partialPoint.y, partialPoint.z]}>
          <sphereGeometry args={[0.5, 12, 12]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
      )}
    </>
  );
}
