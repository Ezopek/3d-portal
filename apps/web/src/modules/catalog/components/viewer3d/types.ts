import type { Vector3 } from "three";

export type StlFile = {
  id: string;
  modelId: string;
  name: string;
  size: number;
};

export type MeasureMode =
  | "off"
  | "point-to-point"
  | "point-to-plane"
  | "plane-to-plane";

export type Plane = {
  centroid: Vector3;
  normal: Vector3;
  triangleIds: number[];
  seedTriangleId: number;
  weak: boolean;
};

export type Pl2plKind = "parallel" | "closest";

export type Measurement =
  | { kind: "p2p"; id: string; a: Vector3; b: Vector3; distanceMm: number }
  | {
      kind: "p2pl";
      id: string;
      point: Vector3;
      plane: Plane;
      distanceMm: number;
      weakA: boolean;
    }
  | {
      kind: "pl2pl";
      id: string;
      planeA: Plane;
      planeB: Plane;
      distanceMm: number;
      angleDeg: number;
      pl2plKind: Pl2plKind;
      approximate: boolean;
      weakA: boolean;
      weakB: boolean;
    };

export type MeasureActiveStage =
  | { stage: "empty" }
  | { stage: "have-point"; point: Vector3 }
  | { stage: "have-plane"; plane: Plane };

export type MeasureState = {
  mode: MeasureMode;
  toleranceDeg: number;
  active: MeasureActiveStage;
  completed: Measurement[];
};

export type Viewer3DProps = {
  files: readonly StlFile[];
  initialFileId?: string;
  onClose?: () => void;
};
