import { describe, it, expect } from "vitest";
import { Vector3 } from "three";

import { initialMeasureState, measureReducer } from "./measureReducer";
import type { MeasureState, Plane, Rim } from "../types";

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
          { kind: "p2p", id: "x", colorIndex: 0, a: new Vector3(), b: new Vector3(1, 0, 0), distanceMm: 1 },
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
        { kind: "p2p" as const, id: "x", colorIndex: 0, a: new Vector3(), b: new Vector3(), distanceMm: 1 },
      ],
    };
    const s1 = measureReducer(s0, { type: "clear" });
    expect(s1.active).toEqual({ stage: "empty" });
    expect(s1.completed).toHaveLength(0);
    expect(s1.mode).toBe("plane-to-plane");
    expect(s1.toleranceDeg).toBe(7);
  });

  it("patch-last-pl2pl updates the most recent pl2pl measurement", () => {
    const planeA = fakePlane(1, [1, 2]);
    const planeB = fakePlane(5, [5, 6]);
    let s = measureReducer(
      { ...initialMeasureState, mode: "plane-to-plane" },
      { type: "click-plane", plane: planeA },
    );
    s = measureReducer(s, { type: "click-plane", plane: planeB });
    s = measureReducer(s, {
      type: "patch-last-pl2pl",
      distanceMm: 12.4,
      angleDeg: 47,
      pl2plKind: "closest",
      approximate: false,
    });
    const last = s.completed[s.completed.length - 1];
    expect(last?.kind).toBe("pl2pl");
    if (last?.kind === "pl2pl") {
      expect(last.distanceMm).toBeCloseTo(12.4);
      expect(last.angleDeg).toBeCloseTo(47);
      expect(last.pl2plKind).toBe("closest");
    }
  });

  it("patch-last-p2pl updates the most recent p2pl measurement", () => {
    const plane = fakePlane(1, [1, 2]);
    let s = measureReducer(
      { ...initialMeasureState, mode: "point-to-plane" },
      { type: "click-plane", plane },
    );
    s = measureReducer(s, { type: "click-mesh", point: new Vector3(0, 0, 5) });
    s = measureReducer(s, { type: "patch-last-p2pl", distanceMm: 12.4 });
    const last = s.completed[s.completed.length - 1];
    expect(last?.kind).toBe("p2pl");
    if (last?.kind === "p2pl") expect(last.distanceMm).toBeCloseTo(12.4);
  });

  it("patch actions no-op when last completed has wrong kind", () => {
    const s0 = {
      ...initialMeasureState,
      completed: [
        {
          kind: "p2p" as const,
          id: "x",
          colorIndex: 0,
          a: new Vector3(),
          b: new Vector3(),
          distanceMm: 1,
        },
      ],
    };
    const s1 = measureReducer(s0, {
      type: "patch-last-pl2pl",
      distanceMm: 5,
      angleDeg: 0,
      pl2plKind: "parallel",
      approximate: false,
    });
    expect(s1).toBe(s0); // exact reference equality (returned unchanged state)
    const s2 = measureReducer(s0, { type: "patch-last-p2pl", distanceMm: 5 });
    expect(s2).toBe(s0); // exact reference equality
  });
});

function fakeRim(): Rim {
  return {
    center: new Vector3(0, 0, 0),
    axis: new Vector3(0, 0, 1),
    radius: 5,
    loopPoints: [],
    weak: false,
  };
}

describe("measureReducer — click-rim", () => {
  it("appends a kind:'diameter' measurement with colorIndex 0 in fresh state", () => {
    const state = { ...initialMeasureState, mode: "diameter" as const };
    const next = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    expect(next.completed).toHaveLength(1);
    const m = next.completed[0]!;
    expect(m.kind).toBe("diameter");
    expect(m.colorIndex).toBe(0);
    if (m.kind === "diameter") {
      expect(m.diameterMm).toBe(10);
    }
  });

  it("ignores click-rim when mode is not diameter", () => {
    const state = { ...initialMeasureState, mode: "point-to-point" as const };
    const next = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    expect(next.completed).toHaveLength(0);
  });
});

describe("measureReducer — colorIndex stability", () => {
  it("delete middle measurement does not recolor others", () => {
    let state: MeasureState = { ...initialMeasureState, mode: "diameter" };
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    const id1 = state.completed[1]!.id;
    const indicesBefore = state.completed.map((m) => m.colorIndex);
    state = measureReducer(state, { type: "delete-measurement", id: id1 });
    const indicesAfter = state.completed.map((m) => m.colorIndex);
    expect(indicesAfter).toEqual([indicesBefore[0], indicesBefore[2]]);
  });

  it("reuses freed colorIndex on next allocation", () => {
    let state: MeasureState = { ...initialMeasureState, mode: "diameter" };
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() }); // 0
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() }); // 1
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() }); // 2
    const id1 = state.completed[1]!.id;
    state = measureReducer(state, { type: "delete-measurement", id: id1 });
    state = measureReducer(state, { type: "click-rim", rim: fakeRim() });
    expect(state.completed.map((m) => m.colorIndex).sort()).toEqual([0, 1, 2]);
  });
});
