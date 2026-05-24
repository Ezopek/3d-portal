// Module-level shared blob cache for /share/<token>/* fetches.
// Keyed by URL, refcounted across AnonymousImage instances. When a thumbnail
// strip + main carousel frame both render the same URL, only ONE fetch hits
// the share-anon rate limit (NFR12-DDOS-RATE-1 cap = 60 req/min). Without
// this cache, a carousel of ~60+ photos would self-429 by issuing 60+ thumb
// fetches + duplicate main-frame fetch on mount (Codex 19.5 round-2 P2).
//
// Story 23.1 (TB-033) — Hardening:
//   - `_pending` tracks subscribers in the inflight window separately from
//     the materialized cache. Each `acquireShareBlob` call on a cold/inflight
//     URL increments `_pending[src]`; each `releaseShareBlob` decrements it.
//     The cold fetch's resolve handler uses the current `_pending` count as
//     the initial `refCount`, so consumers that mounted and unmounted while
//     the fetch was in flight (StrictMode double-effect, fast carousel prev/
//     next) don't leave orphaned refs behind. P2#1.
//   - `clearShareBlobCache()` is invoked from the route component's unmount
//     cleanup so token revocation propagates the next time the recipient
//     navigates back to /share/<token>. P2#2.
//
// Extracted from $token.tsx into a sibling module (Story 23.1) so the route
// file can stay focused on JSX/components and the cache module can carry the
// test-only state-inspection exports without tripping
// react-refresh/only-export-components.

const _shareBlobCache = new Map<string, { url: string; refCount: number }>();
const _shareBlobInflight = new Map<string, Promise<string>>();
const _pending = new Map<string, number>();

export function acquireShareBlob(src: string): Promise<string> {
  const cached = _shareBlobCache.get(src);
  if (cached !== undefined) {
    cached.refCount += 1;
    return Promise.resolve(cached.url);
  }
  // Cold or inflight — register this consumer in `_pending` BEFORE
  // returning the promise so the cold fetch's resolve handler can read the
  // correct subscriber count (Story 23.1 / TB-033 P2#1). Note: every code
  // path through `acquireShareBlob` is paired with a `releaseShareBlob`
  // call from the `AnonymousImage` useEffect cleanup, even when the
  // consumer unmounts before the fetch resolves.
  _pending.set(src, (_pending.get(src) ?? 0) + 1);

  const inflight = _shareBlobInflight.get(src);
  if (inflight !== undefined) {
    // Piggy-back: the cold fetch's resolve handler will materialize the
    // cache entry with the final `_pending` count as its refCount. We just
    // return the same URL when it lands. No refCount mutation here.
    return inflight;
  }
  const promise = fetch(src, { credentials: "omit" })
    .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`img_${r.status}`))))
    .then((blob) => {
      const objUrl = URL.createObjectURL(blob);
      const pendingCount = _pending.get(src) ?? 0;
      _pending.delete(src);
      if (pendingCount > 0) {
        _shareBlobCache.set(src, { url: objUrl, refCount: pendingCount });
        return objUrl;
      }
      // All consumers unmounted before the fetch resolved — drop the URL
      // and reject so piggy-back `.catch(() => {})` handlers stay silent.
      URL.revokeObjectURL(objUrl);
      throw new Error("share_blob_all_consumers_unmounted");
    })
    .finally(() => {
      _shareBlobInflight.delete(src);
    });
  _shareBlobInflight.set(src, promise);
  return promise;
}

export function releaseShareBlob(src: string): void {
  const entry = _shareBlobCache.get(src);
  if (entry !== undefined) {
    entry.refCount -= 1;
    if (entry.refCount <= 0) {
      URL.revokeObjectURL(entry.url);
      _shareBlobCache.delete(src);
    }
    return;
  }
  // Cache entry not yet materialized — decrement the inflight counter.
  // Story 23.1 / TB-033 P2#1: without this branch, consumers that unmount
  // before the fetch resolves would leak into the future cache entry's
  // initial refCount (the old code hard-coded `refCount: 1` on resolve
  // and silently discarded pending releases).
  const pendingCount = _pending.get(src) ?? 0;
  if (pendingCount > 1) {
    _pending.set(src, pendingCount - 1);
  } else {
    _pending.delete(src);
  }
}

/**
 * Revoke every cached object URL and clear all three maps. Invoked from the
 * route component's unmount cleanup (Story 23.1 / TB-033 P2#2, Decision X.1
 * policy A) so a subsequent re-mount of /share/<token> (same or different
 * token) starts from a clean slate. Without this, a recipient who keeps the
 * tab open across a model-owner share revocation would continue seeing
 * cached photos until manual refresh.
 *
 * Policy A chosen over B (TTL) or C (server ETag round-trip) because:
 *   - A is deterministic, lowest implementation cost, drops cache exactly
 *     once per page-life.
 *   - The share view is the terminus surface (per scope-boundary memo) so
 *     cross-token-nav cache benefit traded away is theoretical.
 */
export function clearShareBlobCache(): void {
  for (const entry of _shareBlobCache.values()) {
    URL.revokeObjectURL(entry.url);
  }
  _shareBlobCache.clear();
  _shareBlobInflight.clear();
  _pending.clear();
}

// Test-only handle for asserting the internal cache shape from vitest.
// Production callers MUST NOT reach into this — the maps are deliberately
// module-private. Exposed for Story 23.1 StrictMode + revocation tests
// (TB-033 AC4).
export const __test_share_blob_state = {
  cache: _shareBlobCache,
  inflight: _shareBlobInflight,
  pending: _pending,
  acquire: acquireShareBlob,
  release: releaseShareBlob,
  /** Mirrors the route-component cleanup so tests can reset module state
   *  between cases without invoking React unmount. */
  reset: clearShareBlobCache,
};
