import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useGallery } from "./useGallery";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const baseModel = {
  id: "001",
  path: "decorum/dragon",
  prints: [],
};

describe("useGallery", () => {
  it("does not fetch on mount (lazy)", () => {
    const { result } = renderHook(() => useGallery(baseModel), { wrapper });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.images).toBeUndefined();
  });

  it("fetches once activate() flips the gate, resolves to candidates", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ files: ["images/a.png", "Dragon.stl"] }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const { result } = renderHook(() => useGallery(baseModel), { wrapper });
    act(() => result.current.activate());

    await waitFor(() => expect(result.current.images).toBeDefined());
    expect(result.current.images?.[0]).toEqual({
      url: "/api/files/001/images/a.png",
      path: "images/a.png",
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not refetch on subsequent activate() calls within staleTime", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ files: [] }), { status: 200 }),
    );
    const { result } = renderHook(() => useGallery(baseModel), { wrapper });

    act(() => result.current.activate());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    act(() => result.current.activate());
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
