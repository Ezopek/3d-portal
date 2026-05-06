import { describe, it, expect } from "vitest";
import { Vector3 } from "three";

import { initialMeasureState, measureReducer } from "./measureReducer";
import type { MeasureState } from "../types";

describe("measureReducer", () => {
  it("sets mode and resets active points", () => {
    const s = measureReducer(
      { ...initialMeasureState, active: { points: [new Vector3()] } },
      { type: "set-mode", mode: "point-to-point" },
    );
    expect(s.mode).toBe("point-to-point");
    expect(s.active.points).toHaveLength(0);
  });

  it("collects first click as a partial measurement", () => {
    const s = measureReducer(
      { ...initialMeasureState, mode: "point-to-point" },
      { type: "click-mesh", point: new Vector3(1, 0, 0) },
    );
    expect(s.active.points).toHaveLength(1);
    expect(s.completed).toHaveLength(0);
  });

  it("completes a measurement on second click", () => {
    const s0: MeasureState = { ...initialMeasureState, mode: "point-to-point" };
    const s1 = measureReducer(s0, { type: "click-mesh", point: new Vector3(0, 0, 0) });
    const s2 = measureReducer(s1, { type: "click-mesh", point: new Vector3(3, 4, 0) });
    expect(s2.active.points).toHaveLength(0);
    expect(s2.completed).toHaveLength(1);
    expect(s2.completed[0]?.distanceMm).toBeCloseTo(5, 5);
  });

  it("ignores clicks when mode is off", () => {
    const s = measureReducer(initialMeasureState, {
      type: "click-mesh",
      point: new Vector3(),
    });
    expect(s).toBe(initialMeasureState);
  });

  it("clear empties active and completed", () => {
    const s = measureReducer(
      {
        mode: "point-to-point",
        active: { points: [new Vector3(1, 0, 0)] },
        completed: [
          { id: "x", a: new Vector3(), b: new Vector3(1, 0, 0), distanceMm: 1 },
        ],
      },
      { type: "clear" },
    );
    expect(s.active.points).toHaveLength(0);
    expect(s.completed).toHaveLength(0);
  });
});
