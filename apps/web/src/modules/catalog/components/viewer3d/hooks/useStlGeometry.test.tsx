import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { BufferGeometry } from "three";

import { useStlGeometry } from "./useStlGeometry";
import { _resetStlCacheForTests, stlCache } from "../lib/stlCache";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const m = "11111111-1111-1111-1111-111111111111";
const f = "22222222-2222-2222-2222-222222222222";
const url = `/api/models/${m}/files/${f}/content`;

beforeEach(() => {
  fetchMock.mockReset();
  _resetStlCacheForTests();
});

afterEach(() => {
  _resetStlCacheForTests();
});

// Minimal valid binary STL: 80-byte header + uint32 triangle count = 1 + 50 bytes per triangle.
function makeStlBuffer(): ArrayBuffer {
  const buf = new ArrayBuffer(80 + 4 + 50);
  const view = new DataView(buf);
  view.setUint32(80, 1, true);
  return buf;
}

describe("useStlGeometry", () => {
  it("returns null while loading and resolves to BufferGeometry on fetch", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(makeStlBuffer(), {
        status: 200,
        headers: { "Content-Type": "model/stl" },
      }),
    );
    const { result } = renderHook(() => useStlGeometry({ modelId: m, fileId: f }));
    expect(result.current.geometry).toBeNull();
    await waitFor(() => expect(result.current.geometry).not.toBeNull());
    expect(result.current.geometry).toBeInstanceOf(BufferGeometry);
    expect(result.current.error).toBeNull();
  });

  it("uses the cache on the second render with the same key", async () => {
    fetchMock.mockResolvedValueOnce(new Response(makeStlBuffer(), { status: 200 }));
    const first = renderHook(() => useStlGeometry({ modelId: m, fileId: f }));
    await waitFor(() => expect(first.result.current.geometry).not.toBeNull());
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const second = renderHook(() => useStlGeometry({ modelId: m, fileId: f }));
    await waitFor(() => expect(second.result.current.geometry).not.toBeNull());
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("sets error on HTTP failure", async () => {
    fetchMock.mockResolvedValueOnce(new Response("not found", { status: 404 }));
    const { result } = renderHook(() => useStlGeometry({ modelId: m, fileId: f }));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.geometry).toBeNull();
  });

  it("skips network fetch when modelId or fileId is empty", async () => {
    const { result } = renderHook(() =>
      useStlGeometry({ modelId: "", fileId: f }),
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.geometry).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("releases the cache subscription on unmount", async () => {
    fetchMock.mockResolvedValueOnce(new Response(makeStlBuffer(), { status: 200 }));
    const { result, unmount } = renderHook(() =>
      useStlGeometry({ modelId: m, fileId: f }),
    );
    await waitFor(() => expect(result.current.geometry).not.toBeNull());
    unmount();
    expect(stlCache.peek(url)).toBeInstanceOf(BufferGeometry);
  });
});
