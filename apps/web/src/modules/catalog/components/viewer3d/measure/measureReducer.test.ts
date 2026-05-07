import { describe, it, expect } from "vitest";
import { Vector3 } from "three";

import { initialMeasureState, measureReducer } from "./measureReducer";
import type { MeasureState, Plane } from "../types";

describe("measureReducer", () => {
  it("sets mode and resets active stage", () => {
    const s = measureReducer(
      {
        ...initialMeasureState,
        active: { stage: "have-point", point: new Vector3() },
      },
      { type: "set-mode", mode: "point-to-point" },
    );
    expect(s.mode).toBe("point-to-point");
    expect(s.active).toEqual({ stage: "empty" });
  });

  it("collects first click as a partial measurement", () => {
    const s = measureReducer(
      { ...initialMeasureState, mode: "point-to-point" },
      { type: "click-mesh", point: new Vector3(1, 0, 0) },
    );
    expect(s.active).toEqual({
      stage: "have-point",
      point: expect.any(Vector3),
    });
    expect(s.completed).toHaveLength(0);
  });

  it("completes a measurement on second click", () => {
    const s0: MeasureState = { ...initialMeasureState, mode: "point-to-point" };
    const s1 = measureReducer(s0, { type: "click-mesh", point: new Vector3(0, 0, 0) });
    const s2 = measureReducer(s1, { type: "click-mesh", point: new Vector3(3, 4, 0) });
    expect(s2.active).toEqual({ stage: "empty" });
    expect(s2.completed).toHaveLength(1);
    const m = s2.completed[0];
    expect(m?.kind).toBe("p2p");
    if (m?.kind === "p2p") {
      expect(m.distanceMm).toBeCloseTo(5, 5);
    }
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
        toleranceDeg: 1,
        active: { stage: "have-point", point: new Vector3(1, 0, 0) },
        completed: [
          { kind: "p2p", id: "x", a: new Vector3(), b: new Vector3(1, 0, 0), distanceMm: 1 },
        ],
      },
      { type: "clear" },
    );
    expect(s.active).toEqual({ stage: "empty" });
    expect(s.completed).toHaveLength(0);
  });
});

function fakePlane(seed: number, triangleIds: number[]): Plane {
  return {
    centroid: new Vector3(0, 0, 0),
    normal: new Vector3(0, 0, 1),
    triangleIds,
    seedTriangleId: seed,
    weak: triangleIds.length === 1,
  };
}

describe("measureReducer — plane modes", () => {
  it("set-mode resets active stage to empty", () => {
    const s0 = {
      ...initialMeasureState,
      mode: "point-to-plane" as const,
      active: { stage: "have-plane" as const, plane: fakePlane(7, [7, 8]) },
    };
    const s1 = measureReducer(s0, { type: "set-mode", mode: "off" });
    expect(s1.mode).toBe("off");
    expect(s1.active).toEqual({ stage: "empty" });
  });

  it("click-plane in p2pl moves to have-plane", () => {
    const s0 = { ...initialMeasureState, mode: "point-to-plane" as const };
    const s1 = measureReducer(s0, {
      type: "click-plane",
      plane: fakePlane(3, [3, 4]),
    });
    expect(s1.active).toEqual({
      stage: "have-plane",
      plane: expect.objectContaining({ seedTriangleId: 3 }),
    });
    expect(s1.completed).toHaveLength(0);
  });

  it("click-plane in pl2pl with have-plane completes a measurement", () => {
    const planeA = fakePlane(1, [1, 2]);
    const planeB = fakePlane(5, [5, 6]);
    const s0 = {
      ...initialMeasureState,
      mode: "plane-to-plane" as const,
      active: { stage: "have-plane" as const, plane: planeA },
    };
    const s1 = measureReducer(s0, { type: "click-plane", plane: planeB });
    expect(s1.active).toEqual({ stage: "empty" });
    expect(s1.completed).toHaveLength(1);
    expect(s1.completed[0]?.kind).toBe("pl2pl");
  });

  it("pl2pl ids increment per measurement", () => {
    const planeA = fakePlane(1, [1, 2]);
    const planeB = fakePlane(5, [5, 6]);
    let s: MeasureState = { ...initialMeasureState, mode: "plane-to-plane" as const };
    s = measureReducer(s, { type: "click-plane", plane: planeA });
    s = measureReducer(s, { type: "click-plane", plane: planeB });
    s = measureReducer(s, { type: "click-plane", plane: planeA });
    s = measureReducer(s, { type: "click-plane", plane: planeB });
    expect(s.completed).toHaveLength(2);
    const id1 = s.completed[0]?.id;
    const id2 = s.completed[1]?.id;
    expect(id1).not.toBe(id2);
    expect(id1).toMatch(/^pl2pl-1-/);
    expect(id2).toMatch(/^pl2pl-2-/);
  });

  it("set-tolerance clamps below 0.5", () => {
    const s = measureReducer(initialMeasureState, {
      type: "set-tolerance",
      value: 0.1,
    });
    expect(s.toleranceDeg).toBe(0.5);
  });

  it("set-tolerance clamps above 15", () => {
    const s = measureReducer(initialMeasureState, {
      type: "set-tolerance",
      value: 99,
    });
    expect(s.toleranceDeg).toBe(15);
  });

  it("replace-active-plane keeps stage and updates plane", () => {
    const planeA = fakePlane(2, [2]);
    const planeB = fakePlane(2, [2, 3, 4]);
    const s0 = {
      ...initialMeasureState,
      mode: "point-to-plane" as const,
      active: { stage: "have-plane" as const, plane: planeA },
    };
    const s1 = measureReducer(s0, { type: "replace-active-plane", plane: planeB });
    expect(s1.active).toEqual({ stage: "have-plane", plane: planeB });
  });

  it("clear empties active and completed but preserves toleranceDeg and mode", () => {
    const s0 = {
      ...initialMeasureState,
      toleranceDeg: 7,
      mode: "plane-to-plane" as const,
      active: { stage: "have-plane" as const, plane: fakePlane(1, [1]) },
      completed: [
        { kind: "p2p" as const, id: "x", a: new Vector3(), b: new Vector3(), distanceMm: 1 },
      ],
    };
    const s1 = measureReducer(s0, { type: "clear" });
    expect(s1.active).toEqual({ stage: "empty" });
    expect(s1.completed).toHaveLength(0);
    expect(s1.mode).toBe("plane-to-plane");
    expect(s1.toleranceDeg).toBe(7);
  });
});
