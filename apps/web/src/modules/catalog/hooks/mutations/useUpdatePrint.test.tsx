import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUpdatePrint } from "./useUpdatePrint";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useUpdatePrint", () => {
  it("PATCHes the admin prints endpoint with the patch body", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "p1" }), { status: 200 }),
    );
    const { result } = renderHook(() => useUpdatePrint("m1", "p1"), {
      wrapper: wrap(),
    });
    result.current.mutate({ note: "updated" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/prints/p1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ note: "updated" }));
  });
});
