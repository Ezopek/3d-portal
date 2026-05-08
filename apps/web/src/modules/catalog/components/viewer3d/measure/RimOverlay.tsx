import { Html, Line } from "@react-three/drei";
import type { Color } from "three";

import type { Rim } from "./circleFit";
import { cn } from "@/lib/utils";

const LABEL_CLASS =
  "whitespace-nowrap rounded bg-zinc-900/95 px-2 py-0.5 text-xs font-medium text-white shadow-md ring-1 ring-white/15";

type Props = {
  rim: Rim;
  color: Color;
  /** Optional label text (e.g. `#3 Ø 12.5 mm`). When undefined, only the rim
   *  geometry renders — used for hover preview. */
  label?: string;
  /** Tangent unit vector perpendicular to rim.axis used to position the label.
   *  Required when `label` is set. */
  labelTangent?: { x: number; y: number; z: number };
};

export function RimOverlay({ rim, color, label, labelTangent }: Props) {
  // Close the loop by appending the first point — drei <Line> has no `closed` prop.
  const points = [...rim.loopPoints.map((p) => p.toArray() as [number, number, number])];
  if (rim.loopPoints.length > 0) {
    const first = rim.loopPoints[0]!;
    points.push([first.x, first.y, first.z]);
  }
  const dotR = Math.max(0.5, rim.radius * 0.04);

  // Label position: rim.center + tangent * (radius + 4mm). 4mm offset chosen by feel.
  let labelPos: [number, number, number] | null = null;
  if (label !== undefined && labelTangent !== undefined) {
    const offset = rim.radius + 4;
    labelPos = [
      rim.center.x + labelTangent.x * offset,
      rim.center.y + labelTangent.y * offset,
      rim.center.z + labelTangent.z * offset,
    ];
  }

  return (
    <group>
      <Line
        points={points}
        color={color}
        lineWidth={2}
        depthTest={false}
        depthWrite={false}
        renderOrder={1}
      />
      <mesh position={[rim.center.x, rim.center.y, rim.center.z]}>
        <sphereGeometry args={[dotR, 12, 12]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {labelPos !== null && (
        <Html position={labelPos} center>
          <span className={cn(LABEL_CLASS)}>{label}</span>
        </Html>
      )}
    </group>
  );
}
