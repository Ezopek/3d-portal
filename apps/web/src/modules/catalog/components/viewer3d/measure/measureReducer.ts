import type { Vector3 } from "three";

import { distance } from "./geometry";
import type { Measurement, MeasureMode, MeasureState } from "../types";

export type MeasureAction =
  | { type: "set-mode"; mode: MeasureMode }
  | { type: "click-mesh"; point: Vector3 }
  | { type: "clear" }
  | { type: "cancel-active" };

export const initialMeasureState: MeasureState = {
  mode: "off",
  active: { points: [] },
  completed: [],
};

export function measureReducer(
  state: MeasureState,
  action: MeasureAction,
): MeasureState {
  switch (action.type) {
    case "set-mode":
      return { ...state, mode: action.mode, active: { points: [] } };
    case "click-mesh": {
      if (state.mode !== "point-to-point") return state;
      const next = [...state.active.points, action.point];
      if (next.length < 2) return { ...state, active: { points: next } };
      const [a, b] = next as [Vector3, Vector3];
      const m: Measurement = {
        id: `m-${state.completed.length + 1}-${Date.now()}`,
        a,
        b,
        distanceMm: distance(a, b),
      };
      return {
        ...state,
        active: { points: [] },
        completed: [...state.completed, m],
      };
    }
    case "clear":
      return { ...state, active: { points: [] }, completed: [] };
    case "cancel-active":
      return { ...state, active: { points: [] } };
    default:
      return state;
  }
}
