import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";

import { useFileIndex } from "./useFileIndex";
import type { StlFile } from "../types";

const m = "11111111-1111-1111-1111-111111111111";

const mk = (id: string, name: string): StlFile => ({
  id,
  modelId: m,
  name,
  size: 1000,
});

describe("useFileIndex", () => {
  it("returns alphabetical sort with 1..N positions", () => {
    const files = [mk("a", "zebra.stl"), mk("b", "apple.stl"), mk("c", "mango.stl")];
    const { result } = renderHook(() => useFileIndex(files));
    expect(result.current.sorted.map((f) => f.name)).toEqual([
      "apple.stl",
      "mango.stl",
      "zebra.stl",
    ]);
    expect(result.current.positionOf("b")).toBe(1);
    expect(result.current.positionOf("c")).toBe(2);
    expect(result.current.positionOf("a")).toBe(3);
  });

  it("sort is case-insensitive but stable on ties", () => {
    const files = [mk("a", "Body.stl"), mk("b", "body.stl"), mk("c", "Apple.stl")];
    const { result } = renderHook(() => useFileIndex(files));
    expect(result.current.sorted.map((f) => f.id)).toEqual(["c", "a", "b"]);
  });

  it("returns 0 when id is unknown", () => {
    const { result } = renderHook(() => useFileIndex([mk("a", "x.stl")]));
    expect(result.current.positionOf("nonexistent")).toBe(0);
  });

  it("renumbers when a file is removed (1..N stays sequential)", () => {
    const initial = [mk("a", "a.stl"), mk("b", "b.stl"), mk("c", "c.stl")];
    const { result, rerender } = renderHook(({ files }) => useFileIndex(files), {
      initialProps: { files: initial },
    });
    expect(result.current.positionOf("c")).toBe(3);
    rerender({ files: [mk("a", "a.stl"), mk("c", "c.stl")] });
    expect(result.current.positionOf("c")).toBe(2);
  });
});
