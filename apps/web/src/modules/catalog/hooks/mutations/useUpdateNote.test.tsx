import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUpdateNote } from "./useUpdateNote";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useUpdateNote", () => {
  it("PATCHes the admin notes endpoint with the patch body", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "n1" }), { status: 200 }),
    );
    const { result } = renderHook(() => useUpdateNote("m1", "n1"), { wrapper: wrap() });
    result.current.mutate({ body: "updated" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes/n1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ body: "updated" }));
  });
});
