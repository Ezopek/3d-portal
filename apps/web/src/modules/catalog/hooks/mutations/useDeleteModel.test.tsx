import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDeleteModel } from "./useDeleteModel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useDeleteModel", () => {
  it("DELETEs the admin model endpoint (soft delete by default)", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const { result } = renderHook(() => useDeleteModel("m1"), { wrapper: wrap() });
    result.current.mutate({});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("DELETE");
  });
});
