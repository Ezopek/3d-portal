import { act, render, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { __test_AnonymousImage as AnonymousImage } from "./$token";
import { __test_share_blob_state as shareBlobState } from "./shareBlobCache";

// Story 23.1 (TB-033) — StrictMode refcount + revocation invalidation tests.
//
// These tests assert the hardened blob-cache contract on the share view:
//   AC4 STRICTMODE — under React.StrictMode's double-mount-then-unmount of
//     effects, the module-level `_pending` / `_shareBlobCache` maps must not
//     accumulate orphan entries when consumers unmount before the fetch
//     resolves.
//   AC3 REVOCATION — the route component's unmount cleanup must revoke every
//     cached object URL and clear all three maps, so subsequent re-mounts
//     re-fetch (and therefore see a now-revoked share token's 404/403).
//
// Mocks: `URL.createObjectURL` / `URL.revokeObjectURL` aren't installed by
// jsdom. We stub them inline with deterministic stream IDs so each call's
// return value is uniquely identifiable. `fetch` is stubbed per-test with a
// deferrable promise that the test controls.

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};

function defer<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

let createObjectURLSpy: ReturnType<typeof vi.fn>;
let revokeObjectURLSpy: ReturnType<typeof vi.fn>;
let objectUrlCounter: number;

beforeEach(() => {
  // Reset module-level state from any prior leak. The `reset()` helper
  // mirrors the route-component cleanup so the test starts clean even when
  // the previous test forgot (or intentionally skipped) unmount.
  shareBlobState.reset();
  objectUrlCounter = 0;
  createObjectURLSpy = vi.fn(() => `blob:fake/${++objectUrlCounter}`);
  revokeObjectURLSpy = vi.fn();
  // jsdom does NOT provide URL.createObjectURL / revokeObjectURL — install
  // shims on the URL global. `vi.stubGlobal` would replace the entire URL
  // object; we want to keep the constructor and only override the static
  // methods, so we assign directly and restore in afterEach.
  Object.defineProperty(URL, "createObjectURL", {
    value: createObjectURLSpy,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    value: revokeObjectURLSpy,
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  shareBlobState.reset();
  vi.restoreAllMocks();
});

describe("share blob cache — StrictMode refcount hardening (TB-033 P2#1)", () => {
  it("STRICTMODE-1: strict-mount-unmount-resolve leaves no orphan + revokes the URL exactly once", async () => {
    // Deferrable fetch: the test controls when (and whether) the cold fetch
    // resolves. The Response body is a tiny blob so the .then(r => r.blob())
    // chain in `acquireShareBlob` completes synchronously after resolve.
    const fetchDeferred = defer<Response>();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => fetchDeferred.promise);

    // StrictMode double-mounts the effect: mount → cleanup → mount. Then we
    // unmount the entire tree, which runs cleanup once more. Net effect:
    // every consumer that ran `acquireShareBlob` also ran `releaseShareBlob`.
    const { unmount } = render(
      <StrictMode>
        <AnonymousImage src="https://example.test/asset.jpg" alt="" />
      </StrictMode>,
    );

    // Before resolve: `_pending` should have a counter for this src AND it
    // must net to zero across StrictMode's double-effect pairs. The inflight
    // promise is registered until fetch resolves.
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(shareBlobState.inflight.has("https://example.test/asset.jpg")).toBe(true);
    // StrictMode pairs each acquire with its matching release on the
    // synthetic unmount, so by the time render() returns the net pending
    // count is 1 (only the live consumer remains, not the strict-shadow).
    expect(shareBlobState.pending.get("https://example.test/asset.jpg")).toBe(1);

    // Unmount the live consumer BEFORE fetch resolves. After this all
    // subscribers are gone, `_pending` should be empty.
    unmount();
    expect(shareBlobState.pending.has("https://example.test/asset.jpg")).toBe(false);

    // Resolve the fetch. The cold-fetch resolve handler reads `_pending`
    // (now 0), revokes the freshly-created object URL, and rejects the
    // promise (silently caught by AnonymousImage's `.catch(() => {})`).
    await act(async () => {
      fetchDeferred.resolve(new Response(new Blob(["fake"]), { status: 200 }));
      // Yield two microtask ticks so the .then chain (r => r.blob, then the
      // create-or-revoke handler) completes before we assert.
      await Promise.resolve();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1);
    });

    // Final state: no orphan anywhere. The single object URL that got
    // created was revoked, never cached.
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:fake/1");
    expect(shareBlobState.cache.has("https://example.test/asset.jpg")).toBe(false);
    expect(shareBlobState.pending.has("https://example.test/asset.jpg")).toBe(false);
    expect(shareBlobState.inflight.has("https://example.test/asset.jpg")).toBe(false);
  });

  it("STRICTMODE-2: sequential mounts of the same URL share one fetch + one object URL", async () => {
    // Two independent consumers mount the same URL. The second should
    // piggy-back the first's inflight fetch (NFR12-DDOS-RATE-1 contract
    // preserved). When both stay mounted long enough for the fetch to
    // resolve, the cache entry's refCount must be 2 — not 1, and not 3.
    const fetchDeferred = defer<Response>();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => fetchDeferred.promise);

    const a = render(<AnonymousImage src="https://example.test/shared.jpg" alt="a" />);
    const b = render(<AnonymousImage src="https://example.test/shared.jpg" alt="b" />);

    // One fetch covers both consumers — the rate-limit reason the cache
    // exists in the first place.
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    // Two consumers in the inflight window → pending = 2.
    expect(shareBlobState.pending.get("https://example.test/shared.jpg")).toBe(2);

    await act(async () => {
      fetchDeferred.resolve(new Response(new Blob(["fake"]), { status: 200 }));
      await Promise.resolve();
      await Promise.resolve();
    });

    await waitFor(() => {
      const entry = shareBlobState.cache.get("https://example.test/shared.jpg");
      expect(entry).toBeDefined();
      expect(entry?.refCount).toBe(2);
    });

    // Only one object URL created across the two consumers — cache shared.
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);

    // Unmount one consumer — refCount drops to 1, URL not yet revoked.
    a.unmount();
    expect(shareBlobState.cache.get("https://example.test/shared.jpg")?.refCount).toBe(1);
    expect(revokeObjectURLSpy).not.toHaveBeenCalled();

    // Unmount the second — refCount hits 0, URL revoked + entry removed.
    b.unmount();
    expect(shareBlobState.cache.has("https://example.test/shared.jpg")).toBe(false);
    expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1);
  });
});

describe("share blob cache — page-mount-scoped invalidation (TB-033 P2#2)", () => {
  it("REVOCATION-1: route-component unmount revokes cached URLs + clears all maps", async () => {
    // Behavioral simulation: directly invoke the reset helper (which mirrors
    // the route's useEffect cleanup) and assert all module-level state is
    // dropped. This sidesteps the need to wire up TanStack Router in the
    // test — the cleanup logic itself is what matters for the contract.
    //
    // First, prime the cache with a resolved entry.
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(new Blob(["fake"]), { status: 200 }));

    render(<AnonymousImage src="https://example.test/cached.jpg" alt="" />);
    await waitFor(() => {
      expect(shareBlobState.cache.has("https://example.test/cached.jpg")).toBe(true);
    });
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);

    // Route cleanup fires (recipient navigates away from /share/<token>).
    shareBlobState.reset();

    // Every cached URL revoked, every map empty.
    expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1);
    expect(shareBlobState.cache.size).toBe(0);
    expect(shareBlobState.inflight.size).toBe(0);
    expect(shareBlobState.pending.size).toBe(0);

    // Subsequent acquire of the same URL must re-fetch — proves the cache
    // didn't survive cleanup. Token-revocation contract preserved.
    fetchSpy.mockClear();
    render(<AnonymousImage src="https://example.test/cached.jpg" alt="" />);
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
  });
});
