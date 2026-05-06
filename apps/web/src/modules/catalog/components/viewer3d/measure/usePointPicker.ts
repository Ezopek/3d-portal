import { useCallback } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { Vector3 } from "three";

export type Pick = { point: Vector3; faceIndex: number | null };

export function usePointPicker(
  onPick: (p: Pick) => void,
): (e: ThreeEvent<MouseEvent>) => void {
  return useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      onPick({
        point: e.point.clone(),
        faceIndex: e.faceIndex ?? null,
      });
    },
    [onPick],
  );
}
