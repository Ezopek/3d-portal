import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useUploadFile } from "./useUploadFile";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => fetchMock.mockReset());

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useUploadFile", () => {
  it("POSTs FormData to admin files endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "f1" }), { status: 200 }),
    );
    const { result } = renderHook(() => useUploadFile("m1"), { wrapper: wrap() });
    const file = new File(["x"], "x.png", { type: "image/png" });
    result.current.mutate({ file, kind: "image" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/files");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("retries upload once after refreshing token on 401 access_expired", async () => {
    // 1st call: upload → 401 access_expired
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }),
    );
    // 2nd call: /auth/refresh → 200 (token refreshed)
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 200 }));
    // 3rd call: upload retry → 200 with file data
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "f2" }), { status: 200 }),
    );

    const { result } = renderHook(() => useUploadFile("m1"), { wrapper: wrap() });
    const file = new File(["x"], "x.png", { type: "image/png" });
    result.current.mutate({ file, kind: "image" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // fetch called 3 times: upload, refresh, upload-retry
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/models/m1/files");
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/auth/refresh");
    expect(fetchMock.mock.calls[2]?.[0]).toBe("/api/admin/models/m1/files");
  });

  it("retries upload once after refreshing token on 401 missing_access", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "missing_access" }), { status: 401 }),
    );
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 200 }));
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "f3" }), { status: 200 }),
    );

    const { result } = renderHook(() => useUploadFile("m1"), { wrapper: wrap() });
    result.current.mutate({ file: new File(["y"], "y.stl"), kind: "stl" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("does not retry on 401 with unrelated detail (e.g. admin_required)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "admin_required" }), { status: 401 }),
    );

    const { result } = renderHook(() => useUploadFile("m1"), { wrapper: wrap() });
    result.current.mutate({ file: new File(["z"], "z.png"), kind: "image" });
    await waitFor(() => expect(result.current.isError).toBe(true));

    // Only the original upload call — no refresh, no retry
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current.error?.message).toMatch(/upload failed: 401/);
  });

  it("does not retry when refresh itself fails", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }),
    );
    // refresh returns 401 (e.g. refresh token also expired)
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 }));

    const { result } = renderHook(() => useUploadFile("m1"), { wrapper: wrap() });
    result.current.mutate({ file: new File(["z"], "z.png"), kind: "image" });
    await waitFor(() => expect(result.current.isError).toBe(true));

    // upload + failed refresh — no second upload attempt
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.current.error?.message).toMatch(/upload failed: 401/);
  });
});
