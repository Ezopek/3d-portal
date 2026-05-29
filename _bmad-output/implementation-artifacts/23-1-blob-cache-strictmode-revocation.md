---
title: 'Story 23.1 — Share-view blob cache hardening (StrictMode refcount + revocation invalidation, TB-033)'
type: 'hardening'
status: 'ready-for-dev'
story_id: '23.1'
epic: 'E23 — Share-View Security Hardening'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-033'
fr_ref: 'FR16-BLOB-CACHE-1'
architectural_anchor: 'Decision X.1'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.5 per [[feedback_codex_model_routing]] concurrency/security class)'
estimated_effort: '1-2 h refactor + StrictMode-safe test + agent-browser verify'
created: '2026-05-24'
---

# Story 23.1 — Share-view blob cache hardening (StrictMode refcount + revocation invalidation, TB-033)

Status: ready-for-dev

## Story

As an anonymous share recipient with /share/$token open across StrictMode dev re-renders OR keeping the tab open after the model owner revokes the share token,
I want the blob cache to stay correct under cancelled-inflight scenarios AND to release cached blob URLs on route unmount,
so that orphaned object URLs don't leak under React.StrictMode AND cached photos don't survive past share-token revocation (closes TB-033 P2#1 + P2#2 from Story 19.5 round-2 a28cdde Codex review).

## Acceptance Criteria

1. **AC1 — StrictMode-safe refcount via `_pending` map.** NEW `_pending: Map<string, number>` module-level state in `apps/web/src/routes/share/$token.tsx` tracks inflight subscribers separately from cached refs. `acquireShareBlob(src)`:
   - On cache hit (existing `_shareBlobCache.get(src)` defined): `cached.refCount += 1` → return `cached.url` (existing behavior preserved).
   - On cold-or-inflight path (cache miss): `_pending.set(src, (_pending.get(src) ?? 0) + 1)` BEFORE returning piggy-back-or-fetch promise.
   - Cold fetch resolve handler reads `_pending.get(src)` as initial refCount. If `pendingCount > 0`: `_shareBlobCache.set(src, { url, refCount: pendingCount })`. If `pendingCount === 0` (all consumers unmounted before resolve): `URL.revokeObjectURL(url)` + skip cache entry + reject piggy-backers (silent catch in `AnonymousImage`).
   - Piggy-back path no longer mutates `refCount` in its `.then()` — the cold fetch's resolve handles all pending consumers' refcount via the `_pending` counter.

2. **AC2 — `releaseShareBlob(src)` decrements correct counter.** If `_shareBlobCache.get(src)` defined: decrement `entry.refCount`; on 0 → revoke + delete (existing behavior preserved). If cache entry NOT yet materialized (still inflight): decrement `_pending[src]`. The cleanup function in `AnonymousImage` useEffect MUST call `releaseShareBlob(src)` regardless of whether the fetch has resolved (existing behavior preserved — change is INSIDE `releaseShareBlob`, not in its callers).

3. **AC3 — Page-mount-scoped cache invalidation (Decision X.1 policy A).** Add a useEffect in the `/share/$token` route component (`Share$tokenComponent` or whatever the route default-export is) with empty deps `[]` and a cleanup that:
   - Iterates `_shareBlobCache.values()` calling `URL.revokeObjectURL(entry.url)` on each.
   - Calls `_shareBlobCache.clear()` + `_shareBlobInflight.clear()` + `_pending.clear()`.
   This fires once on route unmount. Effect: re-navigating to `/share/$token` (same or different token) starts with a clean cache. Token revocation while tab open + close-tab-and-reopen → fresh fetch attempts → revoked token returns 404/403 from `acquireShareBlob`'s fetch path → silent fail surface (existing behavior).

4. **AC4 — Deterministic StrictMode mounting test.** NEW vitest test in `apps/web/src/routes/share/$token.test.tsx` (or sibling test file — verify naming convention against existing tests) that:
   - Mounts `<AnonymousImage src="test-url" />` inside `<StrictMode>...<StrictMode>` (or uses `renderHook` with StrictMode wrapper).
   - Mocks `fetch` with a deferrable promise (test controls when it resolves).
   - Asserts that after StrictMode double-mount + double-unmount BEFORE fetch resolves, then resolve fires: `_pending.has("test-url") === false` (counter cleared) AND `_shareBlobCache.has("test-url") === false` (no orphan cache entry) AND `URL.revokeObjectURL` called exactly once on the blob URL.
   - Assert no console.error / no React warnings during the run.

5. **AC5 — Revocation invalidation manual test.** Inline manual test note in spec (operator can re-verify if needed):
   - Open `/share/<valid-token>` in browser; observe N photos load.
   - Admin: `DELETE /api/admin/share/<token>` (or revoke from My Share Links UI).
   - Recipient navigates AWAY from `/share/...` (e.g. to `/`) — route unmounts → cleanup fires → blob URLs revoked.
   - Recipient navigates BACK to `/share/<token>` — `useShareModel` query re-fires → 404/403 from now-revoked token → existing error UI surfaces.
   - Before this story: recipient stays on `/share/...` keeps seeing cached photos until they manually refresh. After: full re-render on route unmount.

6. **AC6 — Full vitest no-regression.** `cd apps/web && npx vitest run` exit 0. All existing AnonymousImage / share-related tests PASS (count preserved or grown by the new StrictMode test).

7. **AC7 — Typecheck + lint clean.** `cd apps/web && npm run typecheck && npm run lint` exit 0.

8. **AC8 — Codex review CLEAN (gpt-5.5 concurrency/security class).** Per [[feedback_codex_model_routing]] heavy class. Round-2 fix-up acceptable if P1/P2 surface (expected since this is concurrency hardening). Round-3+ surfaces as new TB candidate.

## Tasks / Subtasks

- [ ] **T1 — Add `_pending` map + refactor `acquireShareBlob`** (AC: #1)
  - [ ] T1.1 — Add `const _pending = new Map<string, number>();` at module top (after `_shareBlobInflight`).
  - [ ] T1.2 — Refactor `acquireShareBlob`:
    - Cache-hit path unchanged.
    - Cache-miss branches (both piggy-back and cold fetch) increment `_pending[src]` BEFORE returning the promise.
    - Cold fetch resolve handler: read `_pending.get(src) ?? 0`, set `_pending.delete(src)`, if > 0 create cache entry with `refCount: pendingCount`, else revoke URL + reject.
    - Piggy-back `.then()` no longer mutates `_shareBlobCache` — just returns `url`.
  - [ ] T1.3 — Update inline comment block at lines 85-90 to reflect the new `_pending` discipline.

- [ ] **T2 — Refactor `releaseShareBlob`** (AC: #2)
  - [ ] T2.1 — Branch on `_shareBlobCache.get(src)`:
    - Defined: existing refCount-decrement + revoke-on-0 path (unchanged).
    - Undefined: decrement `_pending[src]` (or `_pending.delete(src)` if it would drop to 0).

- [ ] **T3 — Page-mount-scoped invalidation** (AC: #3)
  - [ ] T3.1 — Identify the route component (likely `Share$token` or `RouteComponent` default-export at end of `$token.tsx`).
  - [ ] T3.2 — Add useEffect with empty deps and cleanup that iterates `_shareBlobCache.values()` → `URL.revokeObjectURL(entry.url)`, then `.clear()` on all three maps.
  - [ ] T3.3 — Inline comment citing TB-033 P2#2 + Decision X.1 policy A.

- [ ] **T4 — StrictMode deterministic test** (AC: #4)
  - [ ] T4.1 — Create test file (check existing structure: `apps/web/src/routes/share/$token.test.tsx` or `apps/web/src/routes/share/AnonymousImage.test.tsx` — pick whichever fits existing pattern).
  - [ ] T4.2 — Test: StrictMode double-mount + double-unmount BEFORE fetch resolves, then resolve. Assert no orphan in caches, `URL.revokeObjectURL` called once.
  - [ ] T4.3 — Mock `URL.createObjectURL` + `URL.revokeObjectURL` + `fetch` per existing vitest setup conventions.

- [ ] **T5 — Pre-merge gates** (AC: #6, #7)
  - [ ] T5.1 — `cd apps/web && npm run typecheck` exit 0.
  - [ ] T5.2 — `cd apps/web && npm run lint` exit 0.
  - [ ] T5.3 — `cd apps/web && npx vitest run` exit 0 (all tests, including the new StrictMode test).
  - [ ] T5.4 — `cd apps/web && npm run build` exit 0 (per [[feedback_pre_merge_gate_checklist]] — catches code-split warnings if any).

- [ ] **T6 — Commit + Codex review + auto-deploy** (AC: #8)
  - [ ] T6.1 — Commit message: `fix(share): blob cache StrictMode refcount + revocation invalidation (Story 23.1, TB-033)`.
  - [ ] T6.2 — ff-merge to main.
  - [ ] T6.3 — `codex review --commit <SHA>` (default gpt-5.5 since no `-c review_model` override = security/concurrency class).
  - [ ] T6.4 — If P1/P2: round-2 fix-up + re-review.
  - [ ] T6.5 — On CLEAN: auto-deploy via `infra/scripts/deploy.sh` per [[feedback_auto_deploy_dev]].
  - [ ] T6.6 — Sprint-status flip + TB-033 status → done.

## Dev Notes

### Current code state (lines 91-133 of `apps/web/src/routes/share/$token.tsx`)

```typescript
const _shareBlobCache = new Map<string, { url: string; refCount: number }>();
const _shareBlobInflight = new Map<string, Promise<string>>();

function acquireShareBlob(src: string): Promise<string> {
  const cached = _shareBlobCache.get(src);
  if (cached !== undefined) {
    cached.refCount += 1;
    return Promise.resolve(cached.url);
  }
  const inflight = _shareBlobInflight.get(src);
  if (inflight !== undefined) {
    return inflight.then((url) => {
      const entry = _shareBlobCache.get(src);
      if (entry !== undefined) entry.refCount += 1;  // BUG: race if entry created with refCount=1 already counting this caller
      return url;
    });
  }
  const promise = fetch(src, { credentials: "omit" })
    .then((r) => (r.ok ? r.blob() : Promise.reject(new Error(`img_${r.status}`))))
    .then((blob) => {
      const objUrl = URL.createObjectURL(blob);
      _shareBlobCache.set(src, { url: objUrl, refCount: 1 });  // BUG: hard-coded 1; ignores any unmounted-but-was-pending consumers
      return objUrl;
    })
    .finally(() => {
      _shareBlobInflight.delete(src);
    });
  _shareBlobInflight.set(src, promise);
  return promise;
}

function releaseShareBlob(src: string): void {
  const entry = _shareBlobCache.get(src);
  if (entry === undefined) return;  // BUG: silently drops pending releases that fired before fetch resolved
  entry.refCount -= 1;
  if (entry.refCount <= 0) {
    URL.revokeObjectURL(entry.url);
    _shareBlobCache.delete(src);
  }
}
```

### Bug shapes (TB-033)

**P2#1 — StrictMode refcount leak on cancelled inflight loads:**
React.StrictMode (active in `apps/web/src/main.tsx`) double-mounts effects in dev/tests. Fast carousel prev/next stepping triggers the same shape. The piggy-back path's `.then()` increments `refCount` AFTER the cache entry exists. If all consumers unmount BEFORE the fetch resolves:
1. Each consumer's cleanup runs `releaseShareBlob(src)` — `_shareBlobCache.get(src)` returns `undefined` (entry not created yet) — `releaseShareBlob` no-ops.
2. Fetch resolves → entry created with hard-coded `refCount: 1`.
3. Each piggy-back `.then()` reads the entry and increments `refCount` → orphaned refs never decremented.
4. The single primary consumer's `refCount: 1` initial value already accounts for it; but the cancelled ones contribute orphan refs.

**P2#2 — Cache bypasses share-token revocation for open tabs:**
Cache is keyed only by URL. Once fetched, URL stays in cache for tab lifetime. If model owner revokes share token while recipient keeps tab open, `acquireShareBlob` returns the cached object URL forever — recipient continues seeing already-loaded photos. The "revoking a link immediately disconnects anonymous viewers" contract weakens.

### Fix sketch (paste-ready proposed shape)

```typescript
const _shareBlobCache = new Map<string, { url: string; refCount: number }>();
const _shareBlobInflight = new Map<string, Promise<string>>();
const _pending = new Map<string, number>();  // NEW: tracks consumers in the inflight window

function acquireShareBlob(src: string): Promise<string> {
  const cached = _shareBlobCache.get(src);
  if (cached !== undefined) {
    cached.refCount += 1;
    return Promise.resolve(cached.url);
  }
  // No cache hit — register this consumer as pending
  _pending.set(src, (_pending.get(src) ?? 0) + 1);

  const inflight = _shareBlobInflight.get(src);
  if (inflight !== undefined) return inflight;

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
      // All consumers unmounted before fetch resolved — clean up
      URL.revokeObjectURL(objUrl);
      throw new Error("all_consumers_unmounted");
    })
    .finally(() => {
      _shareBlobInflight.delete(src);
    });
  _shareBlobInflight.set(src, promise);
  return promise;
}

function releaseShareBlob(src: string): void {
  const entry = _shareBlobCache.get(src);
  if (entry !== undefined) {
    entry.refCount -= 1;
    if (entry.refCount <= 0) {
      URL.revokeObjectURL(entry.url);
      _shareBlobCache.delete(src);
    }
    return;
  }
  // Not in cache (still inflight) — decrement pending counter
  const pendingCount = _pending.get(src) ?? 0;
  if (pendingCount > 1) {
    _pending.set(src, pendingCount - 1);
  } else {
    _pending.delete(src);
  }
}
```

Page-mount-scoped invalidation hook (added INSIDE the route component, NOT in AnonymousImage):

```tsx
function ShareRouteComponent() {
  // ... existing route code ...
  useEffect(() => {
    return () => {
      // Decision X.1 policy A: page-mount-scoped invalidation per TB-033 P2#2.
      // On route unmount, revoke all cached blob URLs + clear all maps so a
      // subsequent re-mount starts fresh — token-revocation contract preserved.
      for (const entry of _shareBlobCache.values()) {
        URL.revokeObjectURL(entry.url);
      }
      _shareBlobCache.clear();
      _shareBlobInflight.clear();
      _pending.clear();
    };
  }, []);
  // ... rest of component ...
}
```

### AnonymousImage already handles silent catch correctly

`AnonymousImage` useEffect at lines 144-167 already has a silent `.catch(() => {})` on `acquireShareBlob`. The new `throw new Error("all_consumers_unmounted")` from cold-fetch-with-zero-pending will be caught silently — no UI surface change.

The `cancelled` ref guard at lines 150 + 153 prevents `setObjectUrl` after unmount — still works correctly.

### Why policy A (page-mount-scoped) over B (TTL) or C (server-driven ETag)

- **A (mount-scoped):** simplest, deterministic. Drops cache on unmount. Recipient re-navigating same token = fresh fetch = revoked token surfaces correctly via 404/403. Cache benefit preserved within single route mount.
- **B (TTL):** probabilistic, lag up to TTL. More implementation complexity.
- **C (ETag/HEAD round-trip):** most accurate but adds round-trips per blob fetch — undoes the rate-limit-savings reason the cache exists.

Per [[feedback_share_view_scope_boundary]] terminus: simplicity wins for /share/ surface; cross-token-nav cache benefit traded away is theoretical (anonymous recipients rarely navigate between multiple share tokens).

### StrictMode test scaffolding

Existing tests in `apps/web/src/routes/share/` directory: check if there's a test file already. If not, create `$token.test.tsx` mirroring existing per-route test conventions (`apps/web/src/routes/<other>.test.tsx` if any exist).

Mock pattern:
```typescript
// Mock URL.createObjectURL + revokeObjectURL globally (matches existing patterns
// in apps/web/src/test-utils/* if such a util exists; otherwise inline).
const mockRevoke = vi.spyOn(URL, "revokeObjectURL");

// Deferrable fetch
let resolveFetch: (response: Response) => void;
const mockFetch = vi.spyOn(global, "fetch").mockImplementation(() => {
  return new Promise((resolve) => {
    resolveFetch = resolve;
  });
});

// Mount + unmount inside StrictMode
const { rerender, unmount } = render(<StrictMode><AnonymousImage src="test-url" alt="" /></StrictMode>);
// StrictMode double-mounts in dev — each cycle runs effect twice
unmount();

// Now resolve fetch
resolveFetch(new Response(new Blob(["fake"]), { status: 200 }));

await waitFor(() => {
  expect(mockRevoke).toHaveBeenCalledTimes(1);  // single revoke for the orphaned blob
});

// Verify internal state — import the module-level maps (might require named-export or test-only access)
// Or assert behaviorally: subsequent mount of same URL re-fetches (fetch called twice).
```

NOTE: testing module-level state directly may require exporting the maps OR refactoring into a closure / class. Behavioral assertion (re-fetch on next mount) is preferred per Init 11-15 testing precedent.

### Files NOT touched

- `apps/web/src/main.tsx` — StrictMode wrap stays.
- `apps/web/src/modules/share/*` — module organization unchanged.
- Backend `apps/api/app/modules/share/router.py` — no API contract change.

## File List

**MODIFIED (1):**
- `apps/web/src/routes/share/$token.tsx` — `_pending` map added; `acquireShareBlob` + `releaseShareBlob` refactored; route component gets page-mount-scoped invalidation effect.

**NEW (1):**
- `apps/web/src/routes/share/$token.test.tsx` (or equivalent path per existing convention) — StrictMode-safe refcount test + behavioral re-fetch test.

**Diff stats expected:**
- ~20-30 LOC modified in `$token.tsx` (refactor + new useEffect)
- ~80-150 LOC new test file
- Net: ~+100-180 LOC

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Typecheck | `cd apps/web && npm run typecheck` | Exit 0 |
| Lint | `cd apps/web && npm run lint` | Exit 0 |
| Vitest full | `cd apps/web && npx vitest run` | All tests PASS including new StrictMode test |
| Build | `cd apps/web && npm run build` | Exit 0, no code-split warnings on `/share/` route |
| Pytest no-regression | `cd apps/api && timeout 600 uv run pytest -q tests/` | Exit 0 (no backend change but verify deterministic) |
| Manual revocation verify | (operator, post-deploy) | Documented in commit body |
| Codex review | `codex review --commit <SHA>` (default gpt-5.5 security class) | CLEAN OR P1/P2 → fix-up cycle |

## References

- [Init 16 SCP §4.2](sprint-change-proposal-2026-05-24-init16.md#42-epic-e23--share-view-security-hardening) — Story 23.1 originating scope.
- [epics.md § Initiative 16 § Epic E23 § Story 23.1](../planning-artifacts/epics.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Story description.
- [prd.md § FR16-BLOB-CACHE-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Verifiable requirement.
- [architecture.md § Decision X.1](../planning-artifacts/architecture.md#decision-x--blob-cache-hardening-epic-23--fr16-blob-cache-1--fr16-stl-preview-lock-1) — Architectural anchor (StrictMode refcount + invalidation policy A).
- [triage-backlog.md § TB-033](../triage-backlog.md) — Original Codex Story 19.5 round-2 P2 findings.
- Story 19.5 round-2 commit a28cdde — module-level blob cache origin.
- Memory entries:
  - [[feedback_shared_cache_in_react]] — module-level React cache hardening guidance.
  - [[feedback_codex_model_routing]] — gpt-5.5 for security/concurrency class.
  - [[feedback_pre_merge_gate_checklist]] — typed pre-Codex gates.
  - [[feedback_share_view_scope_boundary]] — share view terminus; policy A justified.
  - [[feedback_auto_deploy_dev]] — auto-deploy on commit.

## Dev Agent Record

### Agent Model Used

(Filled in by dev-story execution)

### Debug Log References

(Filled in during dev-story phase)

### Completion Notes List

(Filled in during dev-story phase)

### File List

(Filled in during dev-story phase — expected match to File List above)
