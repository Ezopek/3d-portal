import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useFiles } from "./useFiles";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
  fetchMock.mockReset();
});

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("useFiles", () => {
  it("calls /files with kind=all by default (backward compat)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ files: ["a.stl"] }), { status: 200 }),
    );
    const { result } = renderHook(() => useFiles("001"), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/catalog/models/001/files?kind=all",
      expect.any(Object),
    );
  });

  it("calls /files with kind=printable when requested", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ files: ["a.stl"] }), { status: 200 }),
    );
    const { result } = renderHook(() => useFiles("001", { kind: "printable" }), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/catalog/models/001/files?kind=printable",
      expect.any(Object),
    );
  });

  it("uses different cache keys for different kinds", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ files: [] }), { status: 200 }));
    const wrapper = wrap();
    renderHook(() => useFiles("001", { kind: "all" }), { wrapper });
    renderHook(() => useFiles("001", { kind: "printable" }), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
