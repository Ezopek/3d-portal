import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreateTag } from "./useCreateTag";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useCreateTag", () => {
  it("POSTs to admin tags endpoint with the input body", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "t1" }), { status: 201 }),
    );
    const { result } = renderHook(() => useCreateTag(), { wrapper: wrap() });
    result.current.mutate({ slug: "new-tag", name_en: "New tag" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/tags");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ slug: "new-tag", name_en: "New tag" }));
  });
});
