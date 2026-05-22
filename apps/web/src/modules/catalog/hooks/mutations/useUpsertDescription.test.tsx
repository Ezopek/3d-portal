import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useUpsertDescription } from "./useUpsertDescription";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useUpsertDescription", () => {
  it("POSTs a new description note when no existingId is provided", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "n1" }), { status: 201 }),
    );
    const { result } = renderHook(() => useUpsertDescription(), { wrapper: wrap() });
    result.current.mutate({
      modelId: "m1",
      existingId: null,
      body_pl: "",
      body_en: "hello",
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/notes");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        kind: "description",
        body: "hello",
        body_pl: null,
        body_en: "hello",
      }),
    );
  });

  it("PATCHes an existing note with bilingual body fields", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "n9" }), { status: 200 }),
    );
    const { result } = renderHook(() => useUpsertDescription(), { wrapper: wrap() });
    result.current.mutate({
      modelId: "m1",
      existingId: "n9",
      body_pl: "polski",
      body_en: "english",
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/notes/n9");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({ body: "english", body_pl: "polski", body_en: "english" }),
    );
  });
});
