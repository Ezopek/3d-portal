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
// Story 23.1 round-2 (Codex P2 fix-up): generation counter wycina stale
// in-flight fetches whose `clearShareBlobCache()` ran between their dispatch
// and their resolve. Without this guard, an OLD fetch resolving AFTER a
// route unmount + remount could pollute the NEW cache state by consuming
// the new `_pending[src]` counter and stamping the OLD blob URL into the
// fresh cache — leaving the remounted image stuck on a pre-revocation blob.
let _generation = 0;

// Story 27.1 (Init 17 / TB-047 / Decision Z): concurrency semaphore caps
// simultaneous in-flight `/api/share/<token>/files/*` fetches at 4 — one
// below the nginx `limit_conn share_anon_conn 5` hard cap (Story 19.2).
// Operator HAR capture 2026-05-24 (`tmp/share_gallery.har`) showed 8
// fetches launched within 1ms on share-view mount → 5 prześliznęły się
// przez limit_conn → 3 instant 503s. Story 22.2 round-2 LazyAnonymousImage
// reduced the eager-strip-mount window but didn't deterministically cap
// the burst count. This semaphore does — overflow callers wait for a
// release rather than fire-and-fail at the nginx layer.
const MAX_CONCURRENT_FETCHES = 4;
let _concurrentFetches = 0;
const _fetchQueue: Array<() => void> = [];

// Sync-when-available: returns `undefined` when a slot is immediately
// granted (so the caller can chain fetch synchronously and existing
// tests + microtask timing assumptions stay intact); returns a Promise
// only when the request must queue. Story 27.1 semaphore composition
// with Story 23.1's promise-chain shape works cleanly either way.
function _acquireFetchSlot(): Promise<void> | undefined {
  if (_concurrentFetches < MAX_CONCURRENT_FETCHES) {
    _concurrentFetches += 1;
    return undefined;
  }
  return new Promise<void>((resolve) => {
    _fetchQueue.push(() => {
      _concurrentFetches += 1;
      resolve();
    });
  });
}

function _releaseFetchSlot(): void {
  _concurrentFetches -= 1;
  const next = _fetchQueue.shift();
  if (next !== undefined) next();
}

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
  // Capture the generation at fetch dispatch time. If
  // `clearShareBlobCache()` bumps `_generation` before this fetch resolves,
  // both the resolve handler and the finally cleanup will see the mismatch
  // and refuse to mutate the (now-newer) cache state.
  const fetchGeneration = _generation;
  // Story 27.1 — semaphore wraps the fetch dispatch. Slot is acquired
  // synchronously when available (preserves existing tests' microtask
  // assumptions) OR via promise chain when queued. Slot released in the
  // `.finally()` block below. The `_pending` and generation disciplines
  // remain orthogonal: even if a consumer's slot wait races with
  // `clearShareBlobCache()`, the generation check on resolve still
  // rejects the (now-stale) result and the slot is released via the
  // same finally.
  //
  // Story 27.1 round-2 (Codex P3): wrap the fetch-init construction in
  // try/catch so a SYNC throw (e.g. malformed URL, `URL` constructor
  // throwing on bad input) releases the just-acquired slot. Without this,
  // a sync-throw on bad input would leak `_concurrentFetches += 1` forever
  // until page reload. Production rarely hits sync `fetch()` throws but
  // the leak permanence makes the defensive path worth the 3 LOC.
  const slotWait = _acquireFetchSlot();
  let fetchInit: Promise<Response>;
  try {
    fetchInit = slotWait === undefined
      ? fetch(src, { credentials: "omit" })
      : slotWait.then(() => fetch(src, { credentials: "omit" }));
  } catch (syncErr) {
    if (slotWait === undefined) {
      // Slot was acquired synchronously and now leaked — release it.
      _releaseFetchSlot();
    }
    // Story 27.1 round-3 (Codex round-2 P2): return a REJECTED promise
    // rather than re-throwing. acquireShareBlob's caller is
    // AnonymousImage which uses `.then().catch()` — a sync throw would
    // bypass its catch handler and leak the `_pending` increment from
    // the top of this function. Returning rejected promise lets the
    // standard catch handle the error AND keeps the signature
    // consistent ("acquireShareBlob always returns Promise<string>").
    // Also explicitly decrement _pending here since the cold-fetch
    // resolve never gets to clean it up.
    const pendingCount = _pending.get(src) ?? 0;
    if (pendingCount > 1) {
      _pending.set(src, pendingCount - 1);
    } else {
      _pending.delete(src);
    }
    return Promise.reject(syncErr);
  }
  const promise: Promise<string> = fetchInit
    .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`img_${r.status}`))))
    .then((blob) => {
      const objUrl = URL.createObjectURL(blob);
      if (fetchGeneration !== _generation) {
        // The cache was cleared mid-flight (route unmount → remount). This
        // fetch's response is for the PREVIOUS page-life; drop it without
        // touching the current `_pending` / `_shareBlobCache` so the new
        // fetch dispatched by the remount can resolve cleanly.
        URL.revokeObjectURL(objUrl);
        throw new Error("share_blob_stale_generation");
      }
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
      // Promise-identity guard: if `clearShareBlobCache()` already wiped
      // the inflight map and a NEW fetch took this slot, do NOT delete the
      // NEW promise. Only remove the entry if it still points at THIS
      // promise. This pairs with the generation guard above so neither the
      // resolve handler nor the cleanup can stomp on fresh state.
      if (_shareBlobInflight.get(src) === promise) {
        _shareBlobInflight.delete(src);
      }
      // Story 27.1 — release semaphore slot AFTER the fetch settles (success
      // OR failure OR stale-generation reject). The next queued caller (if
      // any) acquires the freed slot via its push'd callback.
      _releaseFetchSlot();
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
  // Bump generation FIRST so any in-flight fetch dispatched before this
  // clear (still hanging onto a now-stale `fetchGeneration`) will see the
  // mismatch in its resolve handler and refuse to pollute the fresh cache.
  // Story 23.1 round-2 (Codex P2 fix-up).
  _generation += 1;
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
   *  between cases without invoking React unmount. Also force-resets the
   *  Story 27.1 semaphore (which `clearShareBlobCache` doesn't touch in
   *  production — see Decision Z rationale on slot accounting under
   *  in-flight-during-unmount). */
  reset: (): void => {
    clearShareBlobCache();
    _concurrentFetches = 0;
    _fetchQueue.length = 0;
  },
  /** Story 27.1 (Init 17 / TB-047) — semaphore introspection for vitest. */
  semaphore: {
    get concurrentFetches() {
      return _concurrentFetches;
    },
    get queueLength() {
      return _fetchQueue.length;
    },
    maxConcurrent: MAX_CONCURRENT_FETCHES,
  },
};
