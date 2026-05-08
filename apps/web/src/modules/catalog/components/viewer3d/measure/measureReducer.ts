import type { Vector3 } from "three";

import { distance } from "./geometry";
import { allocateColorIndex } from "../lib/palette";
import type {
  Measurement,
  MeasureState,
  Plane,
  Rim,
} from "../types";

export type MeasureAction =
  | { type: "set-mode"; mode: MeasureState["mode"] }
  | { type: "click-mesh"; point: Vector3 }
  | { type: "click-plane"; plane: Plane }
  | { type: "click-rim"; rim: Rim }
  | { type: "set-tolerance"; value: number }
  | { type: "replace-active-plane"; plane: Plane }
  | { type: "clear" }
  | { type: "cancel-active" }
  | { type: "delete-measurement"; id: string }
  | {
      type: "patch-last-pl2pl";
      distanceMm: number;
      angleDeg: number;
      pl2plKind: "parallel" | "closest";
      approximate: boolean;
    }
  | { type: "patch-last-p2pl"; distanceMm: number };

export const initialMeasureState: MeasureState = {
  mode: "off",
  toleranceDeg: 1,
  active: { stage: "empty" },
  completed: [],
};

function clampTolerance(value: number): number {
  if (Number.isNaN(value)) return 1;
  return Math.min(15, Math.max(0.5, value));
}

function newId(prefix: string, completed: Measurement[]): string {
  return `${prefix}-${completed.length + 1}-${Date.now()}`;
}

function pl2plPlaceholder(planeA: Plane, planeB: Plane, completed: Measurement[]): Measurement {
  // Distance + angle math lands in Task 6. For now Task 1 only needs the
  // reducer to *create* a Measurement of kind "pl2pl"; values are filled by
  // the canvas integration once geometry helpers exist.
  return {
    kind: "pl2pl",
    id: newId("pl2pl", completed),
    colorIndex: allocateColorIndex(completed),
    planeA,
    planeB,
    distanceMm: 0,
    angleDeg: 0,
    pl2plKind: "parallel",
    approximate: false,
    weakA: planeA.weak,
    weakB: planeB.weak,
  };
}

export function measureReducer(
  state: MeasureState,
  action: MeasureAction,
): MeasureState {
  switch (action.type) {
    case "set-mode":
      return { ...state, mode: action.mode, active: { stage: "empty" } };

    case "click-mesh": {
      if (state.mode === "off") return state;
      if (state.mode === "point-to-point") {
        if (state.active.stage !== "have-point") {
          return {
            ...state,
            active: { stage: "have-point", point: action.point.clone() },
          };
        }
        const a = state.active.point;
        const b = action.point.clone();
        const colorIndex = allocateColorIndex(state.completed);
        const m: Measurement = {
          kind: "p2p",
          id: newId("p2p", state.completed),
          colorIndex,
          a,
          b,
          distanceMm: distance(a, b),
        };
        return {
          ...state,
          active: { stage: "empty" },
          completed: [...state.completed, m],
        };
      }
      if (state.mode === "point-to-plane") {
        if (state.active.stage !== "have-plane") return state;
        const m: Measurement = {
          kind: "p2pl",
          id: newId("p2pl", state.completed),
          colorIndex: allocateColorIndex(state.completed),
          point: action.point.clone(),
          plane: state.active.plane,
          distanceMm: 0, // filled by canvas integration in Task 13 with geometry helpers from Task 6
          weakA: state.active.plane.weak,
        };
        return {
          ...state,
          active: { stage: "empty" },
          completed: [...state.completed, m],
        };
      }
      return state;
    }

    case "click-plane": {
      if (state.mode === "off" || state.mode === "point-to-point") return state;
      if (state.active.stage === "empty") {
        return {
          ...state,
          active: { stage: "have-plane", plane: action.plane },
        };
      }
      if (
        state.mode === "plane-to-plane" &&
        state.active.stage === "have-plane"
      ) {
        const m = pl2plPlaceholder(state.active.plane, action.plane, state.completed);
        return {
          ...state,
          active: { stage: "empty" },
          completed: [...state.completed, m],
        };
      }
      return state;
    }

    case "set-tolerance":
      return { ...state, toleranceDeg: clampTolerance(action.value) };

    case "replace-active-plane":
      if (state.active.stage !== "have-plane") return state;
      return { ...state, active: { stage: "have-plane", plane: action.plane } };

    case "clear":
      return { ...state, active: { stage: "empty" }, completed: [] };

    case "cancel-active":
      return { ...state, active: { stage: "empty" } };

    case "delete-measurement": {
      const idx = state.completed.findIndex((m) => m.id === action.id);
      if (idx === -1) return state;
      return {
        ...state,
        completed: [
          ...state.completed.slice(0, idx),
          ...state.completed.slice(idx + 1),
        ],
      };
    }

    case "patch-last-pl2pl": {
      const last = state.completed[state.completed.length - 1];
      if (last === undefined || last.kind !== "pl2pl") return state;
      const patched: Measurement = {
        ...last,
        distanceMm: action.distanceMm,
        angleDeg: action.angleDeg,
        pl2plKind: action.pl2plKind,
        approximate: action.approximate,
      };
      return {
        ...state,
        completed: [...state.completed.slice(0, -1), patched],
      };
    }

    case "patch-last-p2pl": {
      const last = state.completed[state.completed.length - 1];
      if (last === undefined || last.kind !== "p2pl") return state;
      const patched: Measurement = { ...last, distanceMm: action.distanceMm };
      return { ...state, completed: [...state.completed.slice(0, -1), patched] };
    }

    case "click-rim": {
      if (state.mode !== "diameter") return state;
      const colorIndex = allocateColorIndex(state.completed);
      const m: Measurement = {
        kind: "diameter",
        id: newId("diameter", state.completed),
        colorIndex,
        rim: action.rim,
        diameterMm: action.rim.radius * 2,
        weak: action.rim.weak,
      };
      return { ...state, completed: [...state.completed, m] };
    }

    default: {
      const _exhaustive: never = action;
      void _exhaustive;
      return state;
    }
  }
}
