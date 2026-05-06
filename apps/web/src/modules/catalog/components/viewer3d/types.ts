import type { Vector3 } from "three";

export type StlFile = {
  id: string;
  modelId: string;
  name: string;
  size: number;
};

export type MeasureMode = "off" | "point-to-point";

export type ToolMode = "orbit" | "pan";

export type Measurement = {
  id: string;
  a: Vector3;
  b: Vector3;
  distanceMm: number;
};

export type MeasureState = {
  mode: MeasureMode;
  active: { points: Vector3[] };
  completed: Measurement[];
};

export type Viewer3DProps = {
  files: readonly StlFile[];
  initialFileId?: string;
  thumbnailUrl?: string;
  onClose?: () => void;
};
