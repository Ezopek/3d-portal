import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useModel } from "./useModel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useModel", () => {
  it("calls GET /api/models/{uuid}", async () => {
    const id = "11111111-1111-1111-1111-111111111111";
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id, slug: "x" }), { status: 200 }),
    );
    renderHook(() => useModel(id), { wrapper: wrap() });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`/api/models/${id}`);
  });

  it("uses different cache keys for different ids", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    const wrapper = wrap();
    renderHook(() => useModel("a"), { wrapper });
    renderHook(() => useModel("b"), { wrapper });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });
});
