import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreateNote } from "./useCreateNote";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useCreateNote", () => {
  it("POSTs the note input to admin notes endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "n1" }), { status: 201 }),
    );
    const { result } = renderHook(() => useCreateNote("m1"), { wrapper: wrap() });
    result.current.mutate({ model_id: "m1", kind: "operational", body: "hello" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({ model_id: "m1", kind: "operational", body: "hello" }),
    );
  });
});
