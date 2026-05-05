import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useFiles } from "./useFiles";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

const ID = "11111111-1111-1111-1111-111111111111";

describe("useFiles", () => {
  it("defaults to kind=stl", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    renderHook(() => useFiles(ID), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/models/${ID}/files?kind=stl`);
  });

  it("accepts an explicit kind", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    renderHook(() => useFiles(ID, { kind: "image" }), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/models/${ID}/files?kind=image`);
  });

  it("omits kind param when kind is null", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    renderHook(() => useFiles(ID, { kind: null }), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/models/${ID}/files`);
  });

  it("uses different cache keys per kind", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    const wrapper = wrap();
    renderHook(() => useFiles(ID, { kind: "stl" }), { wrapper });
    renderHook(() => useFiles(ID, { kind: "image" }), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
