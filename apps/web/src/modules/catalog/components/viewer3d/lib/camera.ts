import { Box3, Vector3 } from "three";

export type ViewPreset = "front" | "side" | "top" | "iso";

export const viewPresets: Record<ViewPreset, Vector3> = {
  front: new Vector3(0, 0, 1),
  side: new Vector3(1, 0, 0),
  top: new Vector3(0, 1, 0),
  iso: new Vector3(1, 1, 1).normalize(),
};

export type FramingOpts = { fovDeg: number; margin: number };

export function framingDistance(box: Box3, opts: FramingOpts): number {
  const size = new Vector3();
  box.getSize(size);
  const radius = Math.max(size.x, size.y, size.z) * 0.5;
  const halfFov = (opts.fovDeg * Math.PI) / 360;
  return (radius / Math.tan(halfFov)) * opts.margin;
}
