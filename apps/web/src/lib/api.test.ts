import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

describe("api wrapper", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let fetchMock: any;

  beforeEach(() => {
    fetchMock = vi.spyOn(globalThis, "fetch");
  });
  afterEach(() => {
    fetchMock.mockRestore();
  });

  it("includes credentials and X-Portal-Client", async () => {
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 200 }));
    await api("/test");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-Portal-Client")).toBe("web");
  });

  it("retries once on 401 access_expired", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))    // /auth/refresh
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }));   // retry
    const out = await api<{ ok: boolean }>("/me");
    expect(out.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("retries once on 401 missing_access", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "missing_access" }), { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }));
    const out = await api<{ ok: boolean }>("/me");
    expect(out.ok).toBe(true);
  });

  it("does not retry on other 4xx codes", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "admin_required" }), { status: 403 }),
    );
    await expect(api("/admin")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not loop after second 401", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))   // /auth/refresh
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "access_expired" }), { status: 401 }));
    await expect(api("/me")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(3);  // not 5
  });
});
