import { describe, it, expect, beforeEach } from "vitest";
import { BufferGeometry } from "three";

import { stlCache, _resetStlCacheForTests } from "./stlCache";

function makeGeom(id: string): BufferGeometry {
  const g = new BufferGeometry();
  g.userData.id = id;
  g.userData.disposed = false;
  const orig = g.dispose.bind(g);
  g.dispose = () => {
    g.userData.disposed = true;
    orig();
  };
  return g;
}

describe("stlCache", () => {
  beforeEach(() => {
    _resetStlCacheForTests();
  });

  it("inserts and retrieves a geometry by url", () => {
    const g = makeGeom("a");
    stlCache.put("/a", g);
    expect(stlCache.peek("/a")).toBe(g);
  });

  it("evicts the least-recently-used entry when over capacity", () => {
    stlCache.setCapacityForTests(2);
    const a = makeGeom("a");
    const b = makeGeom("b");
    const c = makeGeom("c");
    stlCache.put("/a", a);
    stlCache.put("/b", b);
    expect(stlCache.peek("/a")).toBe(a); // touches /a
    stlCache.put("/c", c);
    expect(stlCache.peek("/b")).toBe(undefined);
    expect(b.userData.disposed).toBe(true);
    expect(stlCache.peek("/a")).toBe(a);
    expect(stlCache.peek("/c")).toBe(c);
  });

  it("does NOT dispose an evicted entry that still has subscribers", () => {
    stlCache.setCapacityForTests(1);
    const a = makeGeom("a");
    const b = makeGeom("b");
    stlCache.put("/a", a);
    stlCache.acquire("/a");
    stlCache.put("/b", b);
    expect(stlCache.peek("/a")).toBe(undefined);
    expect(a.userData.disposed).toBe(false);
    stlCache.release("/a");
    expect(a.userData.disposed).toBe(true);
  });

  it("release on a still-cached entry does not dispose", () => {
    const a = makeGeom("a");
    stlCache.put("/a", a);
    stlCache.acquire("/a");
    stlCache.release("/a");
    expect(a.userData.disposed).toBe(false);
  });

  it("acquire returns the same geometry as put", () => {
    const a = makeGeom("a");
    stlCache.put("/a", a);
    expect(stlCache.acquire("/a")).toBe(a);
  });

  it("acquire on missing key returns undefined", () => {
    expect(stlCache.acquire("/nope")).toBe(undefined);
  });

  it("clear disposes everything regardless of refcount", () => {
    const a = makeGeom("a");
    const b = makeGeom("b");
    stlCache.put("/a", a);
    stlCache.put("/b", b);
    stlCache.acquire("/a");
    stlCache.clear();
    expect(a.userData.disposed).toBe(true);
    expect(b.userData.disposed).toBe(true);
    expect(stlCache.peek("/a")).toBe(undefined);
  });
});
