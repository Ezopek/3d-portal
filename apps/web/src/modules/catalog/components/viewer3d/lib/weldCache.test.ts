import { describe, it, expect, beforeEach } from "vitest";

import { _resetWeldCacheForTests, weldCache } from "./weldCache";
import type { WeldedMesh } from "./welder";

function fakeWelded(): WeldedMesh {
  return {
    positions: new Float32Array(0),
    indices: new Uint32Array(0),
    adjacency: new Uint32Array(0),
    sourceToWelded: new Uint32Array(0),
    weldedToSourceStart: new Uint32Array(1),
    weldedToSource: new Uint32Array(0),
    graph: {
      edges: new Uint32Array(0),
      triangles: new Uint32Array(0),
      dihedralAngles: new Float32Array(0),
      vertexEdges: new Uint32Array(0),
      vertexEdgesStart: new Uint32Array(1),
      triangleEdgeIds: new Uint32Array(0),
    },
  };
}

describe("weldCache", () => {
  beforeEach(() => {
    _resetWeldCacheForTests();
  });

  it("acquire returns undefined for missing keys", () => {
    expect(weldCache.acquire("nope")).toBeUndefined();
  });

  it("put + acquire returns the welded mesh", () => {
    const w = fakeWelded();
    weldCache.put("k1", w);
    expect(weldCache.acquire("k1")).toBe(w);
  });

  it("release decrements refcount", () => {
    const w = fakeWelded();
    weldCache.put("k1", w);
    expect(weldCache.acquire("k1")).toBe(w); // ref=1
    expect(weldCache.acquire("k1")).toBe(w); // ref=2
    weldCache.release("k1"); // ref=1
    weldCache.release("k1"); // ref=0
    // Still retrievable because not evicted yet.
    expect(weldCache.acquire("k1")).toBe(w);
  });
});

describe("weldCache — LRU + detached lifecycle", () => {
  beforeEach(() => {
    _resetWeldCacheForTests();
  });

  it("evicts oldest entry past capacity", () => {
    weldCache.setCapacityForTests(1);
    weldCache.put("k1", fakeWelded());
    weldCache.put("k2", fakeWelded());
    expect(weldCache.has("k1")).toBe(false);
    expect(weldCache.has("k2")).toBe(true);
  });

  it("evicted entry with active refcount survives in detached", () => {
    weldCache.setCapacityForTests(1);
    const w1 = fakeWelded();
    weldCache.put("k1", w1);
    expect(weldCache.acquire("k1")).toBe(w1); // ref=1
    weldCache.put("k2", fakeWelded()); // evicts k1 from live
    // k1 still retrievable while ref-held
    expect(weldCache.has("k1")).toBe(true);
    weldCache.release("k1"); // ref=0 → detached cleanup
    expect(weldCache.has("k1")).toBe(false);
  });

  it("put over an acquired key keeps old entry in detached for active holders", () => {
    const w1 = fakeWelded();
    weldCache.put("k1", w1);
    const acquired = weldCache.acquire("k1");
    expect(acquired).toBe(w1);
    weldCache.put("k1", fakeWelded()); // new data
    // The previously-acquired ref is still release-able without throwing
    expect(() => weldCache.release("k1")).not.toThrow();
  });
});
