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
