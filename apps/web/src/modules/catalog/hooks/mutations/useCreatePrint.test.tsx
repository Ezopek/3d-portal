import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreatePrint } from "./useCreatePrint";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useCreatePrint", () => {
  it("POSTs the print input to admin prints endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "p1" }), { status: 201 }),
    );
    const { result } = renderHook(() => useCreatePrint("m1"), { wrapper: wrap() });
    result.current.mutate({ model_id: "m1", printed_at: "2026-05-04", note: "ok" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/prints");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({ model_id: "m1", printed_at: "2026-05-04", note: "ok" }),
    );
  });
});
