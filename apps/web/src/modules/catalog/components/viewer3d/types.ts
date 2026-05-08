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
  | "plane-to-plane"
  | "diameter";

export type Plane = {
  centroid: Vector3;
  normal: Vector3;
  triangleIds: number[];
  seedTriangleId: number;
  weak: boolean;
};

export type Rim = {
  /** Center of the fitted circle in mesh-local frame. */
  center: Vector3;
  /** Plane normal (unit). */
  axis: Vector3;
  /** mm. */
  radius: number;
  /** Absolute coordinates of loop vertices, snapshotted from welded.positions
   *  at fit time. After commit the rim does not depend on the welded mesh. */
  loopPoints: Vector3[];
  /** Any of weakV / weakM / weakA / weakN signals (see circleFit.ts). */
  weak: boolean;
};

export type Pl2plKind = "parallel" | "closest";

export type Measurement =
  | {
      kind: "p2p";
      id: string;
      colorIndex: number;
      a: Vector3;
      b: Vector3;
      distanceMm: number;
    }
  | {
      kind: "p2pl";
      id: string;
      colorIndex: number;
      point: Vector3;
      plane: Plane;
      distanceMm: number;
      weakA: boolean;
    }
  | {
      kind: "pl2pl";
      id: string;
      colorIndex: number;
      planeA: Plane;
      planeB: Plane;
      distanceMm: number;
      angleDeg: number;
      pl2plKind: Pl2plKind;
      approximate: boolean;
      weakA: boolean;
      weakB: boolean;
    }
  | {
      kind: "diameter";
      id: string;
      colorIndex: number;
      rim: Rim;
      diameterMm: number;
      weak: boolean;
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
