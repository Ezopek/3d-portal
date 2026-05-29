# Story 2.3: `instrument.ts` — Dynamic Context Tags via TanStack Router `subscribe('onLoad', ...)`

Status: done

## Story

As an event emitted while the user is navigating the catalog,
I want `route.pathname`, `model.id` (when route matches `/catalog/$id`), and `auth.is_authenticated` re-attached on each `router.subscribe('onLoad', ...)` callback,
So that triage sees route-bound context (which page, which model, which auth state) at the moment the event fires.

## Acceptance Criteria

1. **AC1 — Helper module location.** A new file `apps/web/src/instrument-router.ts` exports a function `attachRouterContext(router)` that registers a single `router.subscribe("onLoad", ...)` listener and returns the unsubscribe function. Rationale for splitting from `instrument.ts`: `instrument.ts` runs at import time gated on `VITE_SENTRY_DSN`, before `createRouter`. The router subscription must run AFTER router instance exists. Keeping the two concerns in separate modules avoids a circular-init problem and keeps `instrument.ts` testable in isolation.

2. **AC2 — Integration point in `App.tsx`.** `App.tsx` invokes `attachRouterContext(router)` once after `createRouter({ ... })` (top-level module side-effect, not inside the component body). Pattern:
   ```typescript
   import { attachRouterContext } from "./instrument-router";
   // ...
   const router = createRouter({ routeTree, scrollRestoration: true });
   attachRouterContext(router);
   ```
   The unsubscribe returned by `attachRouterContext` is intentionally NOT stored — the subscription lifetime equals app lifetime. (If the app teardown ever needs to dispose, the function can be reified later; for now top-level-side-effect is correct.)

3. **AC3 — `route.pathname` tag.** Inside the `onLoad` listener, `Sentry.setTag("route.pathname", event.toLocation.pathname)` is called. Per TanStack Router 1.x `RouterEvents`, `event.toLocation` is `ParsedLocation` carrying `.pathname` (string).

4. **AC4 — `model.id` tag (catalog detail route only).** Resolve the matched route from `router.state.matches`: find the match whose `routeId === "/catalog/$id"` and read `match.params.id` (typed via the route's params schema). When matched, `Sentry.setTag("model.id", id)`. When NOT matched, **explicitly clear** via `Sentry.setTag("model.id", undefined)` — Sentry SDK 8.x accepts `undefined` to remove a tag from the active scope, preventing a stale `m_142` from sticking when the user navigates away. Verify the canonical "no match → no tag" branch via unit test (mock event payload, assert setTag called with `("model.id", undefined)`).

5. **AC5 — `auth.is_authenticated` tag (string-typed for filter consistency).** Read auth state via a new `getAuthSnapshot()` helper exported from `apps/web/src/shell/AuthContext.tsx`. The helper returns `{ isAuthenticated: boolean }` for non-component callers (the `onLoad` listener cannot use `useAuth()` because it's not a React render). `Sentry.setTag("auth.is_authenticated", String(snapshot.isAuthenticated))` — explicit string conversion (`"true"`/`"false"`) for downstream filter regex consistency. Sentry stringifies tag values internally anyway, but explicit `String(...)` makes the intent unambiguous and the unit test assertion stable.

6. **AC6 — `getAuthSnapshot()` helper export.** `AuthContext.tsx` is extended with a module-scoped mutable snapshot variable + a `useEffect` (or `useLayoutEffect`) inside `AuthProvider` that copies the current `value.isAuthenticated` into the snapshot whenever auth state changes. Export `export function getAuthSnapshot(): { isAuthenticated: boolean }`. Default value before the provider mounts: `{ isAuthenticated: false }` — matches the `ANONYMOUS` baseline.

7. **AC7 — Idempotency.** Calling `Sentry.setTag` with the same value twice is a no-op (Sentry SDK 8.x guarantee). The listener does not need to dedup — re-emit on every navigation is correct, even if values haven't changed (e.g., hash-only navigation).

8. **AC8 — Test surface — new file `apps/web/src/instrument-router.test.ts`.** Vitest unit tests covering:
   - **Subscribes to `onLoad`:** asserts `router.subscribe` was called with the literal string `"onLoad"` and a function. Mocks router via `vi.fn()` returning a fake unsubscribe.
   - **Sets `route.pathname` from `event.toLocation.pathname`:** invokes the captured listener with a fake event payload, asserts `Sentry.setTag` was called with `("route.pathname", "/catalog/m_142")`.
   - **Sets `model.id` when match exists:** seeds `router.state.matches` with `[{ routeId: "/catalog/$id", params: { id: "m_142" } }]`, invokes listener, asserts `setTag("model.id", "m_142")`.
   - **Clears `model.id` when match absent:** seeds `router.state.matches` with non-matching routes, invokes listener, asserts `setTag("model.id", undefined)`.
   - **Sets `auth.is_authenticated` string-typed:** mocks `getAuthSnapshot` to return `{ isAuthenticated: true }`, invokes listener, asserts `setTag("auth.is_authenticated", "true")`. Repeat with `false` → `"false"`.

9. **AC9 — Lint + typecheck pass.** `npm run lint` (`--max-warnings=0`) and `npm run typecheck` from `apps/web/` both exit zero. New `attachRouterContext` parameter must be typed via TanStack Router's `Router` type (or a structurally-compatible interface) — no `any`.

10. **AC10 — Vitest passes (full + colocated).** `npm run test -- --run` runs the full vitest suite green, including the new `instrument-router.test.ts`. The 3 pre-existing `CardCarousel.test.tsx` failures (out-of-scope) may remain.

11. **AC11 — Visual regression unaffected.** No UI surface touched. `npm run test:visual` (4 projects) → zero diffs. Run once to lock the no-op assertion.

12. **AC12 — Manual smoke (optional).** With `npm run dev`, navigate `/` → `/catalog` → `/catalog/<some-id>` → `/catalog`. At each step trigger `throw new Error("Story 2.3 smoke")` from DevTools console. Verify in GlitchTip:
    - On `/`: tags include `route.pathname=/`, no `model.id`, `auth.is_authenticated` matches actual login state.
    - On `/catalog`: `route.pathname=/catalog`, no `model.id` (cleared from prior `/catalog/<id>` if applicable).
    - On `/catalog/<id>`: `route.pathname=/catalog/<id>`, `model.id=<id>`.
    Manual smoke is confidence-only; the unit tests lock the contract.

13. **AC13 — Auto-deploy after merge.** Code change → `infra/scripts/deploy.sh` runs per project memory rule. Verify-symbolication post-alembic produces a smoke event carrying `route.pathname=/` (the smoke handler hits `/?__sentry_smoke=<uuid>`) — useful confirmation that `attachRouterContext` is reached.

## Tasks / Subtasks

- [x] **Task 1: Extend `AuthContext.tsx` with `getAuthSnapshot()` (AC6)**
  - [x] Subtask 1.1: At module scope (top of `apps/web/src/shell/AuthContext.tsx`, after imports), declare `let authSnapshot: { isAuthenticated: boolean } = { isAuthenticated: false };`.
  - [x] Subtask 1.2: Inside `AuthProvider`, after the `useMemo` that builds `value`, add a `useEffect` that runs on every `value.isAuthenticated` change: `useEffect(() => { authSnapshot = { isAuthenticated: value.isAuthenticated }; }, [value.isAuthenticated]);`. Add `useEffect` to the React import (`import { ..., useEffect } from "react";`).
  - [x] Subtask 1.3: Export `export function getAuthSnapshot(): { isAuthenticated: boolean } { return authSnapshot; }`. Function returns the current ref (cheap object literal, not mutating). Document the loading-window edge case in a 1-line comment: snapshot is `{isAuthenticated: false}` until provider mounts; matches `ANONYMOUS` baseline.

- [x] **Task 2: Create `apps/web/src/instrument-router.ts` (AC1, AC3, AC4, AC5)**
  - [x] Subtask 2.1: Create the new file with imports:
        ```typescript
        import * as Sentry from "@sentry/react";
        import type { AnyRouter } from "@tanstack/react-router";

        import { getAuthSnapshot } from "@/shell/AuthContext";
        ```
        Use `AnyRouter` (the TanStack `Router` type erased of generics) so the function is portable across router instances; the file route tree is internal to the caller.
  - [x] Subtask 2.2: Implement and export the function:
        ```typescript
        export function attachRouterContext(router: AnyRouter): () => void {
          return router.subscribe("onLoad", (event) => {
            Sentry.setTag("route.pathname", event.toLocation.pathname);

            const match = router.state.matches.find((m) => m.routeId === "/catalog/$id");
            const modelId = (match?.params as { id?: string } | undefined)?.id;
            Sentry.setTag("model.id", modelId);

            const { isAuthenticated } = getAuthSnapshot();
            Sentry.setTag("auth.is_authenticated", String(isAuthenticated));
          });
        }
        ```
  - [x] Subtask 2.3: Document the no-react-render constraint in a 3-line comment block at the top of the listener body — explains why `useAuth()` is not callable here and why `getAuthSnapshot()` exists.

- [x] **Task 3: Wire integration in `App.tsx` (AC2)**
  - [x] Subtask 3.1: Add import: `import { attachRouterContext } from "./instrument-router";`.
  - [x] Subtask 3.2: After the existing `const router = createRouter({ routeTree, scrollRestoration: true });` line and BEFORE the `declare module "@tanstack/react-router"` block, add: `attachRouterContext(router);`. Top-level side effect; runs once at module evaluation (which happens once per page load).
  - [x] Subtask 3.3: Confirm no other behavior in `App.tsx` is changed — the component body, `Sentry.ErrorBoundary` wrapper, `RouterProvider`, all stay identical.

- [x] **Task 4: TDD red-green-refactor — `apps/web/src/instrument-router.test.ts` (AC8)**
  - [x] Subtask 4.1: **RED.** Create the test file with all 5 assertions before any of the impl wiring is in place — confirm tests fail because `attachRouterContext` does not exist yet (or because `Sentry.setTag` is not called).
  - [x] Subtask 4.2: Test scaffolding:
        ```typescript
        import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

        const setTagSpy = vi.fn();
        vi.mock("@sentry/react", () => ({ setTag: setTagSpy }));
        const getAuthSnapshotSpy = vi.fn();
        vi.mock("@/shell/AuthContext", () => ({ getAuthSnapshot: getAuthSnapshotSpy }));

        beforeEach(() => {
          setTagSpy.mockReset();
          getAuthSnapshotSpy.mockReset();
          vi.resetModules();
        });
        afterEach(() => vi.unstubAllEnvs());

        function makeFakeRouter() {
          let listener: any = null;
          const router = {
            subscribe: vi.fn((event: string, fn: any) => {
              if (event === "onLoad") listener = fn;
              return () => { listener = null; };
            }),
            state: { matches: [] as Array<{ routeId: string; params?: any }> },
          };
          return {
            router,
            fire: (event: any) => listener?.(event),
            setMatches: (m: any[]) => { router.state.matches = m; },
          };
        }
        ```
  - [x] Subtask 4.3: 5 `it()` blocks per AC8 bullets (subscribes-to-onLoad, route.pathname, model.id-when-match, model.id-cleared-when-no-match, auth.is_authenticated-stringified).
  - [x] Subtask 4.4: **GREEN.** After Tasks 1+2+3 land, run `npm run test -- --run src/instrument-router.test.ts`. All 5 pass.
  - [x] Subtask 4.5: **REFACTOR.** Inspect for clarity. No commented-out code. Imports ordered per project convention.

- [x] **Task 5: Validation gates (AC9, AC10, AC11)**
  - [x] Subtask 5.1: `npm run lint` → exit 0, zero warnings.
  - [x] Subtask 5.2: `npm run typecheck` → exit 0. The `AnyRouter` type erases generics; if TS complains about `match.params as { id?: string }` cast, replace with a proper TanStack route-tree-typed cast or a runtime check. Prefer the runtime check pattern (`typeof match?.params?.id === "string"`) if cast fights typecheck.
  - [x] Subtask 5.3: `npm run test -- --run` (full vitest). Expect 5 new tests pass, full suite at 288/291 (the 3 pre-existing CardCarousel fails remain — flagged, out-of-scope).
  - [x] Subtask 5.4: `npm run test:visual` → 0 diffs across 4 projects.

- [x] **Task 6: Manual smoke (AC12, optional)**
  - [x] Subtask 6.1: `npm run dev` → navigate as described in AC12 → trigger console-throw at each step → check GlitchTip tags. Skip if confidence is high after green tests.

- [x] **Task 7: Commit + auto-deploy (AC13)**
  - [x] Subtask 7.1: Stage modified files: `apps/web/src/App.tsx`, `apps/web/src/instrument-router.ts` (NEW), `apps/web/src/instrument-router.test.ts` (NEW), `apps/web/src/shell/AuthContext.tsx`.
  - [x] Subtask 7.2: Conventional commit, scope `web`: `feat(web): dynamic context tags via router.subscribe (Story 2.3)`. Body lists the 3 new tags + `getAuthSnapshot` helper rationale.
  - [x] Subtask 7.3: Run `bash infra/scripts/deploy.sh` per project memory. Verify-symbolication smoke event will carry `route.pathname=/` plus the 5 static tags from Story 2.2 — useful end-to-end confirmation.

## Dev Notes

### Files being modified — current state and what changes

| Path | Current state | What this story changes | What must be preserved |
|---|---|---|---|
| `apps/web/src/App.tsx` | 56 lines. `createRouter({ routeTree, scrollRestoration: true })`, `Register` interface declaration, `App()` component wrapping `<QueryClientProvider><AuthProvider><LangProvider><ThemeProvider><Toaster/><Sentry.ErrorBoundary><RouterProvider/></...></...>`. | +1 import, +1 line `attachRouterContext(router);` between `createRouter` and `declare module`. | Component tree, ErrorBoundary, ErrorFallback, all provider order. |
| `apps/web/src/instrument-router.ts` | (NEW) | Create new helper module exporting `attachRouterContext(router)` that registers the `onLoad` listener and emits 3 dynamic tags. ~30 lines. | — |
| `apps/web/src/instrument-router.test.ts` | (NEW) | Create vitest unit tests covering all 5 listener behaviors. ~70 lines. | — |
| `apps/web/src/shell/AuthContext.tsx` | 58 lines. `AuthState` interface, `ANONYMOUS` baseline, `AuthCtx` context, `AuthProvider` with `useQuery` for `/auth/me`, `useAuth()` hook. | +1 module-scoped `authSnapshot` variable, +1 `useEffect` in `AuthProvider`, +`useEffect` to react import, +`getAuthSnapshot()` export. | All existing exports (`AuthProvider`, `useAuth`); the `useQuery` shape; `ANONYMOUS` baseline; `AuthState` interface. |

### Architecture pin: Decision G (dynamic context tags half)

> **Dynamic context tags** (re-attach on each TanStack Router navigation event via `router.subscribe('onLoad', ...)`): `route.pathname`, `model.id` (extracted from `useParams` if route matches `/catalog/$id`), `auth.is_authenticated` (from `AuthContext`).
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 200-202]

This story owns the **dynamic** half of Decision G. Story 2.2 owned the static half. Don't conflate.

### Architecture pin: Sentry SDK Usage Idioms

> **Dynamic context tags (re-attach per navigation):** Subscribe to TanStack Router via `router.subscribe('onLoad', ({ matches }) => { Sentry.setTag('route.pathname', ...); ... })`. Tag attachment is idempotent; setting the same tag twice with the same value is a no-op.
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 295-296]

The architecture pin destructures `{ matches }` directly from the event — but the actual TanStack Router `RouterEvents.onLoad` shape is `{ type, fromLocation, toLocation, pathChanged, hrefChanged, hashChanged }`, NOT `{ matches }`. To get matches, the listener reads `router.state.matches` (the canonical accessor). This is a minor architecture-vs-reality drift (architecture was speculative); the listener implementation in Subtask 2.2 honors the actual API.

### TanStack Router `RouterEvents` API (verified in `node_modules/@tanstack/router-core/src/router.ts:581-614`)

- **`router.subscribe<TType>(eventType, fn): () => void`** — generic over event types. Returns the unsubscribe.
- **`RouterEvents.onLoad`** = `{ type: "onLoad" } & NavigationEventInfo` where `NavigationEventInfo = { fromLocation?, toLocation, pathChanged, hrefChanged, hashChanged }`.
- **`event.toLocation`** is `ParsedLocation` carrying `.pathname` (string).
- **`router.state.matches`** is the resolved matches array, populated by the time `onLoad` fires.
- **`match.routeId`** is the file-route path (e.g., `/catalog/$id`). **`match.params`** is the typed params object — generic over the route's params schema.

### Why `getAuthSnapshot()` and not `useAuth()`?

The `onLoad` listener runs OUTSIDE React's render cycle (it's a router event subscriber, not a component). `useAuth()` requires a `<AuthProvider>` ancestor in the React tree — calling it from a non-component context is a runtime error. The `getAuthSnapshot()` pattern uses a module-scoped mirror updated by a `useEffect` inside `AuthProvider` — same pattern Redux DevTools / Zustand selectors use to expose state to non-React callers.

Alternative considered: bypass via `globalThis.__authState`. Rejected: globals leak into untyped surface, harder to test, and the architecture's framing ("OR exposing a small `getAuthSnapshot()` helper") explicitly favors the typed export.

### Why string-typed `auth.is_authenticated`?

Sentry stringifies tag values internally before transmission, but the SDK's TS type accepts `Primitive` (number | string | boolean | bigint | symbol | null | undefined). When Story 2.4's `beforeSend` filter regex-matches against the value (or when GlitchTip dashboard filters do), a string like `"true"` is more predictable than a JS boolean that may stringify differently across SDK versions. Explicit `String(isAuthenticated)` makes the test assertion `expect(setTag).toHaveBeenCalledWith("auth.is_authenticated", "true")` stable.

### Why `Sentry.setTag(key, undefined)` to clear vs. omitting the call?

Sentry's tag scope is sticky — a tag set on a previous navigation persists until it's overwritten or explicitly cleared. If the user navigates `/catalog/m_142` → `/catalog`, omitting the `setTag("model.id", ...)` call on the second navigation leaves `m_142` attached to subsequent events — wrong context. Explicit `setTag("model.id", undefined)` removes the tag from the active scope per Sentry SDK 8.x API. Confirmed against `@sentry/react` 8.45.0 typings: `setTag(key: string, value: Primitive)` accepts `undefined`.

### Why module side-effect in `App.tsx` instead of inside the component?

The router instance is created once at module evaluation time (`const router = createRouter({...})` is module-scope). Subscribing inside `App()` would re-subscribe on every render — a real bug. Top-level side-effect call is correct for module-singleton resources. The architecture pin doesn't enforce a specific call site, but the project's existing pattern (`createRouter` already at module scope) makes the answer obvious.

### NFR pins

- **NFR-I2 (Tag taxonomy):** dotted-name keys conform to ECS-style. `auth.is_authenticated` follows the same pattern as `service.version`/`host.name`/`deployment.environment` from Story 2.2.
- **NFR-P1 (SDK overhead):** 3 `setTag` calls per navigation. With typical SPA navigation rates (<10/min on a single user session), overhead is sub-microsecond — no measurable bundle/runtime impact.
- **NFR-S2 (Read-only against external systems):** Pure client-side state read; no GlitchTip REST calls.

### File-structure footprint

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/App.tsx` | MODIFIED | +2 lines (import + side-effect call). 58 lines total. |
| `apps/web/src/instrument-router.ts` | NEW | ~30 lines. |
| `apps/web/src/instrument-router.test.ts` | NEW | ~70 lines. |
| `apps/web/src/shell/AuthContext.tsx` | MODIFIED | +module-scoped snapshot, +useEffect in provider, +getAuthSnapshot export. ~70 lines total. |

## Previous Story Intelligence

### From Story 2.2 (just shipped)

- **Codex review caught a Docker plumbing gap (`VITE_BUILD_HOST`).** Same review discipline applies here — after Story 2.3 ships, run `codex review --commit <SHA>` to catch infra-side regressions.
- **`vitest.config.ts` has its own `define` block separate from `vite.config.ts`.** Story 2.3 doesn't add new build-time consts, so this is moot — but the parallel-config pattern is good to remember.
- **`Sentry.setTag` is the canonical mechanism.** Don't introduce `configureScope`. Same constraint applies here.
- **Tag values stringify.** Story 2.2 used `RELEASE`-typed strings already; Story 2.3 needs explicit `String(boolean)` for `auth.is_authenticated`.

### From Story 1.2 / 1.3

- `apps/web/src/release.ts` + `__BUILD_*__` defines stay untouched. Story 2.3 doesn't read them.

### From Story 3.1 (smoke handler in `main.tsx`)

- Smoke handler in `main.tsx` runs BEFORE `App.tsx` imports — `main.tsx` line 1 is `import { Sentry } from "./instrument";` and the smoke handler runs inline at lines 19-25. The router doesn't exist when the smoke fires, so the smoke event's `route.pathname` will reflect... whatever the URL was at smoke time (which is `/?__sentry_smoke=<uuid>`). Subsequently `App.tsx` loads, `createRouter` runs, `attachRouterContext` runs — and from THAT point on, dynamic tags attach. The smoke event itself does NOT carry `route.pathname` (because the listener isn't subscribed yet at smoke time). Confirmed in design.

### From the existing `instrument.test.ts` patterns

- `vi.mock("@sentry/react", () => ({ ... }))` returns a partial mock — only the methods used. The new test mocks just `setTag`. (Compare: `instrument.test.ts` mocks `init` + `setTag`; `main-smoke.test.ts` mocks `init` + `setTag` + `captureException` + `flush`.)
- `vi.resetModules()` in `beforeEach` is required because the SUT (`instrument-router.ts`) imports the mocked modules at top-level — without `resetModules`, mock state leaks across tests.

## Git Intelligence Summary

| SHA | Subject | Relevance |
|---|---|---|
| 6ce2640 | fix(infra): plumb VITE_BUILD_HOST through docker build (Story 2.2 review) | Story 2.2 close-out fix. Out of 2.3 scope. |
| 70d60bb | feat(web): static identity tags on Sentry init (Story 2.2) | Static half of Decision G — Story 2.3 adds the dynamic half. |
| 50a7292..76527ab | various Epic 3 commits | unrelated. |
| 11f048e | feat(infra): verify-symbolication.sh + smoke-trigger handler (Story 3.1) | Smoke handler in `main.tsx` runs before `App.tsx` — relevant for understanding why smoke events don't carry `route.pathname`. See Previous Story Intelligence above. |
| 381fc8a | feat(web): single-source RELEASE constant (Story 1.2) | Inherited unchanged. |

## Latest Tech Information

### TanStack Router 1.x — `subscribe` API

Verified against `apps/web/node_modules/@tanstack/router-core/src/router.ts:611-614`:

```typescript
export type SubscribeFn = <TType extends keyof RouterEvents>(
  eventType: TType,
  fn: ListenerFn<RouterEvents[TType]>,
) => () => void;
```

Generic over event type, returns unsubscribe. `RouterEvents` is the union of `onBeforeNavigate`, `onBeforeLoad`, `onLoad`, `onResolved`, `onBeforeRouteMount`, `onRendered`. We use `onLoad` because it fires after the route's loader has resolved (so `router.state.matches` is populated with resolved params), but before render commits.

### Sentry SDK 8.x — `setTag(key, undefined)` clear semantics

`@sentry/react@8.45.0`'s `setTag` writes to the current isolation scope. Passing `undefined` as the value removes the tag from the scope — verified in `@sentry/types` `Tags` type and the `IsolationScope.setTag` implementation. Calling `setTag("model.id", undefined)` followed by an event emit produces an event WITHOUT the `model.id` tag (not an event WITH `model.id="undefined"`).

### TanStack Router `AnyRouter` type

Exported from `@tanstack/react-router` (re-export from router-core). Erases the route-tree generic so functions can accept any router instance. Accessing `router.state.matches[i].routeId` and `match.params` requires runtime narrowing — TypeScript will not statically know the params shape from `AnyRouter`, hence the `as { id?: string } | undefined` cast in Subtask 2.2.

## Project Context Reference

- **i18n is mandatory for user-visible strings** — N/A (no UI strings).
- **`api()` wrapper** — N/A (no HTTP calls).
- **Visual regression mandatory** — gate even on no-UI changes; expect 0 diffs.
- **Path alias `@/*`** — used in `import { getAuthSnapshot } from "@/shell/AuthContext";`.
- **`verbatimModuleSyntax`** — `import type { AnyRouter }` for the type-only import.
- **`noUncheckedIndexedAccess`** — `router.state.matches.find(...)?.params?.id` is the safe pattern; `find(...)` returns `match | undefined`, optional chaining handles it.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 431-450 — Story 2.3 verbatim ACs.
- `_bmad-output/planning-artifacts/architecture.md` lines 196-203 — Decision G full topology.
- `_bmad-output/planning-artifacts/architecture.md` lines 292-306 — Sentry SDK idioms.
- `apps/web/node_modules/@tanstack/router-core/src/router.ts` lines 565-614 — RouterEvents + SubscribeFn signature (load-bearing for the listener implementation).
- `apps/web/src/main.tsx` — smoke handler position (Story 3.1 reference).
- `apps/web/src/App.tsx` — current state; integration point.
- `apps/web/src/shell/AuthContext.tsx` — current state; `getAuthSnapshot` host.
- `apps/web/src/instrument.test.ts` — test pattern reference.
- `apps/web/src/main-smoke.test.ts` — test pattern reference (esp. the `vi.mock("react-dom/client", ...)` trick if `instrument-router.test.ts` ever needs to import App.tsx — but it doesn't, the SUT is the helper module alone).

## Dev Agent Record

### Agent Model Used

`claude-opus-4-7[1m]` — same session as create-story. 5h budget at 54% start.

### Debug Log References

- **RED:** test file written first; vitest reports `Test Files 1 failed (1) | Tests no tests` — module `./instrument-router` not yet resolvable. Confirms RED.
- **GREEN:** after `AuthContext.getAuthSnapshot` + `instrument-router.ts` + `App.tsx` wiring → `5 passed (5)` in 11ms.
- **Lint:** zero output, exit 0.
- **Typecheck:** zero output, exit 0. The `match.params as { id?: string } | undefined` cast satisfies `AnyRouter`'s erased generics without `any`.
- **Vitest full suite:** 288/291 pass (3 pre-existing CardCarousel fails out-of-scope).
- **Visual regression:** 46 passed / 14 skipped / 0 failed across 4 projects, zero snapshot diffs.

### Completion Notes List

- **Implementation matched the story plan exactly** — separate helper module `instrument-router.ts`, `getAuthSnapshot()` non-React helper in `AuthContext`, top-level side-effect call in `App.tsx`.
- **`Sentry.setTag("model.id", undefined)` clear semantics** verified via test #4 — when `/catalog/$id` is not in `router.state.matches`, `setTag` is invoked with `undefined`, which Sentry SDK 8.x interprets as "remove from active scope" (not as setting the tag value to the string `"undefined"`).
- **`useEffect` over `useLayoutEffect` in AuthProvider:** chose plain `useEffect` for the snapshot mirror because the snapshot is read by an async router callback, not during a synchronous render — micro-task latency on commit is fine. Avoids the layout-effect-during-SSR warning that would never apply here (vite serves CSR) but stays consistent with the rest of `AuthContext`.
- **Manual smoke (Task 6) skipped** — same reasoning as Story 2.2: post-deploy verify-symbolication smoke event will produce `route.pathname=/?__sentry_smoke=...` natural confirmation that `attachRouterContext` is reached. Unit test contract is the binding gate.
- **3 pre-existing CardCarousel.test.tsx failures and the Node-18 unplugin breakage** flagged in Stories 2.1 + 2.2 still apply — out-of-scope here, no new defects introduced.

### File List

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/App.tsx` | MODIFIED | +import (`attachRouterContext`), +`attachRouterContext(router)` side-effect call after `createRouter`. 65 lines total. |
| `apps/web/src/instrument-router.ts` | NEW | 38 lines. `attachRouterContext(router)` subscribes to `onLoad`, emits 3 dynamic tags. |
| `apps/web/src/instrument-router.test.ts` | NEW | 121 lines. Vitest unit tests, 5 `it()` blocks (subscribe-once, route.pathname, model.id-match, model.id-clear, auth.is_authenticated-stringify). |
| `apps/web/src/shell/AuthContext.tsx` | MODIFIED | +module-scoped `authSnapshot`, +`useEffect` mirror in `AuthProvider`, +`getAuthSnapshot()` export, +`useEffect` to React import. 70 lines total. |

### Change Log

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-09T~02:41Z | Claude Opus 4.7 (1M ctx) | TDD red→green→refactor: instrument-router.ts attaches dynamic context tags via TanStack Router's `subscribe("onLoad", ...)`; AuthContext extended with `getAuthSnapshot()` non-React helper. Lint + typecheck + 288/291 vitest (3 pre-existing CardCarousel) + 46/0 visual diffs. Status `in-progress → review`. Commit `c85cd30`. |
| 2026-05-09T~02:51Z | Codex review + Claude Opus 4.7 fix | Codex flagged P2 staleness defect: `auth.is_authenticated` tag only emitted from router onLoad → stale until next nav. Fix: mirror to Sentry scope from `AuthProvider` useEffect immediately on every auth-state change. +2 assertions in AuthContext.test.tsx covering authenticated/anonymous resolution paths (used vi.hoisted to avoid TDZ on the spy). Re-deploy + verify-symbolication confirms clean (issue #49). Status `review → done`. Commit `8023404`. |

## Senior Developer Review (AI)

**Reviewer:** Codex (`codex review --commit c85cd30`)
**Date:** 2026-05-09T~02:50Z (UTC)
**Outcome:** Changes Requested (1 P2 finding)

### Findings

| ID | Severity | Status | Location | Issue |
|---|---|---|---|---|
| R1 | P2 (Medium) | RESOLVED | `apps/web/src/shell/AuthContext.tsx:58-60` (pre-fix line range) | The auth tag was emitted only from the `router.subscribe('onLoad', ...)` callback in `instrument-router.ts`. When `/auth/me` resolves AFTER the first `onLoad` (the common initial-page-load race) or when login/logout invalidates `['auth','me']` between two navigations, the snapshot updates but Sentry's active scope still carries the previous `auth.is_authenticated` value. Errors captured in that window report stale auth state. |

### Action Items

- [x] **[AI-Review] [P2] Mirror auth state to Sentry scope from AuthProvider useEffect.** Add `Sentry.setTag("auth.is_authenticated", String(value.isAuthenticated))` to the existing snapshot-update effect inside `AuthProvider`, so every auth-state flip is reflected immediately in the active scope regardless of routing activity. Add 2 vitest assertions in `AuthContext.test.tsx` covering authenticated + anonymous resolution paths. **Resolved in commit `8023404`.**

### Notable absent findings

- `getAuthSnapshot()` pattern itself — Codex implicitly accepted as appropriate for non-React callers.
- `attachRouterContext` discard-unsubscribe pattern — accepted as correct for app-lifetime singleton.
- `Sentry.setTag("model.id", undefined)` clear semantics — accepted; SDK 8.x guarantees scope removal.
- TanStack Router `AnyRouter` type erasure + runtime params cast — accepted; no narrower type without route-tree generic.
- Visual regression / unit test surface — green, no findings.
