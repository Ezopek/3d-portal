import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import { fetchApiBlob } from "./api-blob";

const IMG = "/api/models/m1/files/f7/content?variant=full";

function unauthorized(detail: string): Response {
  return new Response(JSON.stringify({ detail }), { status: 401 });
}

function image(): Response {
  return new Response(new Blob(["binary"], { type: "image/jpeg" }), {
    status: 200,
    headers: { "Content-Type": "image/jpeg" },
  });
}

/** URLs of the CONTENT requests only — `/api/auth/refresh` is filtered out so a
 *  count assertion means "how many times did we ask for the photo". */
function contentCalls(mock: { mock: { calls: unknown[][] } }): string[] {
  return mock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => !u.includes("/api/auth/refresh"));
}

function refreshCalls(mock: { mock: { calls: unknown[][] } }): string[] {
  return mock.mock.calls
    .map((c) => String(c[0]))
    .filter((u) => u.includes("/api/auth/refresh"));
}

describe("fetchApiBlob", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let fetchMock: any;

  beforeEach(() => {
    fetchMock = vi.spyOn(globalThis, "fetch");
  });
  afterEach(() => {
    fetchMock.mockRestore();
  });

  it("sends the credentialed, CSRF-stamped request and returns the blob", async () => {
    fetchMock.mockResolvedValueOnce(image());
    const blob = await fetchApiBlob(IMG);
    expect(blob).toBeInstanceOf(Blob);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(IMG);
    // The authenticated catalog surface is the OPPOSITE of `/share`'s
    // `credentials: "omit"` contract — cookies must attach here.
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("X-Portal-Client")).toBe("web");
  });

  it("refreshes once and retries the SAME url once on 401 access_expired", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 })) // /api/auth/refresh
      .mockResolvedValueOnce(image());
    const blob = await fetchApiBlob(IMG);
    expect(blob).toBeInstanceOf(Blob);
    expect(contentCalls(fetchMock)).toEqual([IMG, IMG]);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });

  it("treats missing_access the same way", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("missing_access"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());
    await expect(fetchApiBlob(IMG)).resolves.toBeInstanceOf(Blob);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });

  it("stops after a failed refresh — no retry, no storm", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(unauthorized("refresh_invalid")); // /api/auth/refresh
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
    expect(contentCalls(fetchMock)).toEqual([IMG]);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });

  it("does not loop when the retry is also 401", async () => {
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(unauthorized("access_expired"));
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
    expect(contentCalls(fetchMock)).toEqual([IMG, IMG]);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });

  it("never refreshes on a non-refreshable failure", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "not_found" }), { status: 404 }));
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
    expect(refreshCalls(fetchMock)).toHaveLength(0);
    expect(contentCalls(fetchMock)).toEqual([IMG]);
  });

  it("never refreshes on a 401 whose detail is not a refresh candidate", async () => {
    // Widening the retry surface past the two `detail` values is a deliberate
    // auth decision (`project-context.md` § Auth & sessions), not a default.
    fetchMock.mockResolvedValueOnce(unauthorized("account_disabled"));
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
    expect(refreshCalls(fetchMock)).toHaveLength(0);
  });

  it("surfaces a transport throw as an ApiError rather than a raw TypeError", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
  });

  it("surfaces a body read that fails after a 200 header as an ApiError", async () => {
    // A dropped connection mid-transfer on a multi-MB original: the headers
    // already said 200.
    const torn = new Response(null, { status: 200 });
    Object.defineProperty(torn, "blob", {
      value: () => Promise.reject(new TypeError("network error")),
    });
    fetchMock.mockResolvedValueOnce(torn);
    await expect(fetchApiBlob(IMG)).rejects.toBeInstanceOf(ApiError);
  });

  it("carries the parsed error body so ApiError.body.detail survives", async () => {
    // `instrument-filters.ts` suppresses GlitchTip noise by reading
    // `ApiError.body.detail`; a null body would silently defeat it.
    fetchMock.mockResolvedValueOnce(unauthorized("account_disabled"));
    await expect(fetchApiBlob(IMG)).rejects.toMatchObject({
      status: 401,
      body: { detail: "account_disabled" },
    });
  });

  it("refuses to send credentials off the /api prefix or at a share asset", async () => {
    // NFR10-SHARE-SECURITY-1 made structural: `/share` assets are fetched
    // `credentials: "omit"` through `shareBlobCache`, and this helper must be
    // impossible to point at one.
    await expect(fetchApiBlob("/api/share/tok/files/f1/content")).rejects.toBeInstanceOf(ApiError);
    await expect(fetchApiBlob("https://evil.example/api/x")).rejects.toBeInstanceOf(ApiError);
    await expect(fetchApiBlob("/static/logo.png")).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("passes an abort signal down to both the probe and the retry", async () => {
    const controller = new AbortController();
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(image());
    await fetchApiBlob(IMG, controller.signal);
    const contentInits = fetchMock.mock.calls
      .filter((c: unknown[]) => !String(c[0]).includes("/api/auth/refresh"))
      .map((c: unknown[]) => c[1] as RequestInit);
    expect(contentInits).toHaveLength(2);
    for (const init of contentInits) expect(init.signal).toBe(controller.signal);
  });

  it("shares ONE refresh across concurrent expired image loads", async () => {
    // Two photos expiring together must not rotate the refresh token twice —
    // reuse of an already-rotated token triggers family invalidation.
    fetchMock
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(unauthorized("access_expired"))
      .mockResolvedValueOnce(new Response("{}", { status: 200 })) // single refresh
      .mockResolvedValueOnce(image())
      .mockResolvedValueOnce(image());
    const [a, b] = await Promise.all([fetchApiBlob(IMG), fetchApiBlob(`${IMG}&x=2`)]);
    expect(a).toBeInstanceOf(Blob);
    expect(b).toBeInstanceOf(Blob);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });
});
