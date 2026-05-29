# Story 2.4: `instrument.ts` — `beforeSend` Filter Contract (5-Step Fixed Ordering)

Status: done

## Story

As GlitchTip,
I want only signal events arriving — drop browser-extension URLs (FR5), drop noise titles per the empirical ruleset from Story 2.1 (FR6), drop offline events (FR7), drop `ApiError.access_expired` refresh-flow noise (FR7),
So that the first 25 issues sorted by `lastSeen desc` 7 days post-rollout contain zero deny-list matches (Tech Success #3 in PRD).

## Acceptance Criteria

1. **AC1 — Filter ruleset module (`apps/web/src/instrument-filters.ts` NEW).** A new module exports two `RegExp[]` arrays — `denyUrls` and `ignoreErrors` — paste-imported **literally** from `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` (Story 2.1 output). Anticipated-minimum floor patterns are mandatory. Empirical additions from Story 2.1 = 0 (organic-traffic-deferred), so the arrays equal exactly the floor:

   ```typescript
   export const denyUrls: RegExp[] = [
     /^chrome-extension:\/\//,           // floor: anticipated minimum (FR5)
     /^moz-extension:\/\//,              // floor: anticipated minimum (FR5)
     /^safari-web-extension:\/\//,       // floor: anticipated minimum (FR5)
   ];

   export const ignoreErrors: RegExp[] = [
     /ResizeObserver loop/,                              // floor: anticipated minimum (FR6)
     /Non-Error promise rejection captured/,             // floor: anticipated minimum (FR6)
   ];
   ```

   No re-ordering, no rewriting, no manual translation — Story 2.1's contract pins these arrays as the source of truth.

2. **AC2 — `beforeSend(event, hint)` callback inside `Sentry.init({...})`.** `apps/web/src/instrument.ts` adds a `beforeSend` callback whose body executes 5 sequential `if` branches in fixed order with separate early `return null` per branch (architecture Decision H, AR6). Order is non-negotiable (cheapest exits first):

   ```typescript
   beforeSend(event, hint) {
     // 1. denyUrls: drop events from browser-extension URLs (FR5).
     const url = event.request?.url ?? "";
     for (const pattern of denyUrls) {
       if (pattern.test(url)) return null;
     }
     // 2. ignoreErrors: drop noise titles per Story 2.1 ruleset (FR6).
     const value = event.exception?.values?.[0]?.value ?? "";
     for (const pattern of ignoreErrors) {
       if (pattern.test(value)) return null;
     }
     // 3. Drop events captured while offline (FR7) — they will be retried
     //    by the SDK on reconnect, but if the user closes the tab first
     //    the queue is lost. Better to drop than queue spurious noise.
     if (typeof navigator !== "undefined" && !navigator.onLine) return null;
     // 4. Drop `ApiError.access_expired` refresh-flow noise (FR7) — these
     //    401s are part of the silent refresh path; they're not real errors.
     const orig = hint.originalException;
     if (
       orig instanceof ApiError &&
       (orig.body as { detail?: string } | null)?.detail === "access_expired"
     ) {
       return null;
     }
     // 5. Pass-through: real signal.
     return event;
   }
   ```

3. **AC3 — `denyUrls` matched against `event.request?.url` (NOT script URL).** Per Decision H step 1 + Sentry SDK semantics: the page URL the user was on when the event fired. Architecture pin and Story 2.1 methodology section confirm this; do not regex-match against `event.exception.values[0].stacktrace.frames[].filename` (out of scope for this filter).

4. **AC4 — `ignoreErrors` matched against `event.exception?.values?.[0]?.value`.** First exception's `.value` field — NOT `.type`, NOT `.title`, NOT `event.message`. Per Decision H step 2.

5. **AC5 — Offline + ApiError branches use type-safe runtime checks.** No `any`, no non-null assertions. `navigator.onLine` requires `typeof navigator !== "undefined"` guard for SSR/test safety. `hint.originalException instanceof ApiError` is the runtime narrow; `body` is `unknown` so casting through `{ detail?: string } | null` is acceptable (matches the existing pattern in `apps/web/src/lib/api.ts:46`).

6. **AC6 — Test surface — new file `apps/web/src/instrument-filters.test.ts`.** Vitest unit tests covering 5 branches (one per AC2 step) plus the catch-all pass-through. Tests import the `denyUrls` / `ignoreErrors` arrays + a small helper that wraps the same `beforeSend` logic OR import `beforeSend` directly. Implementation choice during dev — see Task 4 for the recommended pattern.

   Test names use the convention from the epic: `drops_via_denyUrls`, `drops_via_ignoreErrors`, `drops_when_offline`, `drops_access_expired`, `passes_through_default`.

7. **AC7 — Decision H ordering codified in test names.** The 5 tests run in the order specified above; their names mirror the `if`-branch order. Reading `instrument-filters.test.ts` top-to-bottom describes the production filter chain.

8. **AC8 — `denyUrls` / `ignoreErrors` traceable to Story 2.1.** Header comment block at the top of `instrument-filters.ts` references the discovery report with date stamp and a one-sentence "anticipated minimum, no empirical additions because organic traffic = 0" rationale. Future re-runs of Story 2.1 update this file by replacing the array bodies; the header points re-runners at the canonical pattern.

9. **AC9 — Lint + typecheck pass.** `npm run lint` (`--max-warnings=0`) and `npm run typecheck` from `apps/web/`. New imports satisfy `verbatimModuleSyntax` (`import type`-tag the `ApiError` type if the runtime class is not actually constructed in the consumer file — but Story 2.4 needs `instanceof ApiError`, so it imports the class as a value).

10. **AC10 — Vitest passes (full + colocated).** Full suite green except the 3 pre-existing `CardCarousel.test.tsx` failures (out-of-scope).

11. **AC11 — Visual regression unaffected.** `npm run test:visual` → 0 diffs across 4 projects. No UI surface touched.

12. **AC12 — Manual smoke (optional).** With `npm run dev`, in DevTools console:
    - `throw new Error("ResizeObserver loop limit exceeded")` → expected: NOT in GlitchTip (filtered by `ignoreErrors`).
    - `throw new Error("Story 2.4 smoke real error")` → expected: lands in GlitchTip (passes through).
    - `throw new ApiError(401, { detail: "access_expired" }, "401 Unauthorized")` → expected: NOT in GlitchTip (filtered by step 4).
    - Set `navigator.onLine = false` (DevTools → Network → Offline) and trigger a throw → expected: NOT in GlitchTip.

13. **AC13 — Auto-deploy after merge.** Verify-symbolication smoke event after deploy will produce a real exception (`Error: smoke <uuid>`) — its `value` is `smoke <uuid>` which does NOT match either floor pattern, so it passes through. Smoke ritual remains intact.

14. **AC14 — Tech Success #3 (PRD).** "First 25 issues sorted by `lastSeen desc`, measured 7 days post-rollout, contain zero matches against the deny list." This is a 7-day post-rollout success metric, not a Story 2.4 acceptance gate — but Story 2.4 ships the mechanism that makes the metric measurable.

## Tasks / Subtasks

- [x] **Task 1: Create `apps/web/src/instrument-filters.ts` (AC1, AC8)**
  - [x] Subtask 1.1: New file with header doc-comment referencing Story 2.1 discovery output (`glitchtip-discovery-2026-05-09.md`), the anticipated-minimum-floor framing, and the rationale for zero empirical additions (no organic traffic in 30-day window).
  - [x] Subtask 1.2: Export `denyUrls: RegExp[]` (3 floor patterns) and `ignoreErrors: RegExp[]` (2 floor patterns) — paste-imported literally from the discovery report's "Derived `denyUrls`" / "Derived `ignoreErrors`" sections (slash-delimited regex literals, slash-comments per pattern justifying floor vs empirical origin).
  - [x] Subtask 1.3: Verify the file is < 50 lines and has no logic — purely a const-export module.

- [x] **Task 2: Modify `apps/web/src/instrument.ts` to wire `beforeSend` (AC2, AC3, AC4, AC5)**
  - [x] Subtask 2.1: Add 2 new imports: `import type { ErrorEvent, EventHint } from "@sentry/react";` (Sentry's typed event/hint types) and `import { ApiError } from "@/lib/api";` (runtime class for `instanceof` check) and `import { denyUrls, ignoreErrors } from "@/instrument-filters";`. Note: `ApiError` is a value import, not type-only, because `instanceof` needs the class at runtime.
  - [x] Subtask 2.2: Inside `Sentry.init({...})`, add a `beforeSend(event, hint)` property after `tracesSampleRate: 0`:
        ```typescript
        beforeSend(event: ErrorEvent, hint: EventHint): ErrorEvent | null {
          // 1. denyUrls (FR5)
          const url = event.request?.url ?? "";
          for (const pattern of denyUrls) {
            if (pattern.test(url)) return null;
          }
          // 2. ignoreErrors (FR6, Story 2.1 ruleset)
          const value = event.exception?.values?.[0]?.value ?? "";
          for (const pattern of ignoreErrors) {
            if (pattern.test(value)) return null;
          }
          // 3. Offline (FR7)
          if (typeof navigator !== "undefined" && !navigator.onLine) return null;
          // 4. ApiError access_expired (FR7)
          const orig = hint.originalException;
          if (
            orig instanceof ApiError &&
            (orig.body as { detail?: string } | null)?.detail === "access_expired"
          ) {
            return null;
          }
          // 5. Pass-through
          return event;
        }
        ```
  - [x] Subtask 2.3: Confirm the existing init guard, `setTag` calls, and `export { Sentry }` are unchanged. Only `beforeSend` is added inside the init object.

- [x] **Task 3: TDD red-green-refactor — `apps/web/src/instrument-filters.test.ts` (AC6, AC7)**
  - [x] Subtask 3.1: **RED**, but with a twist — the unit test target is the `beforeSend` callback. Two implementation options:
        - **Option A (recommended): Extract `beforeSend` to a named export.** Move the callback body to a top-level exported function `applyBeforeSendFilters(event, hint)` in either `instrument-filters.ts` or a new `instrument-beforeSend.ts`. `instrument.ts` then passes `beforeSend: applyBeforeSendFilters` to `Sentry.init`. Clean unit test surface: import the function, call it with mock `event`/`hint`, assert return value.
        - **Option B: Test the in-place callback indirectly via `Sentry.init` mock.** Capture the `beforeSend` argument from the spy on `Sentry.init` and invoke it. More fragile.
        - **Choice for this story: Option A.** Add `applyBeforeSendFilters` export to `instrument-filters.ts` (keeps the filter logic colocated with the regex arrays), update `instrument.ts` to import + pass it.
  - [x] Subtask 3.2: Test scaffolding (vitest with mock `event`/`hint` shape):
        ```typescript
        import { describe, expect, it } from "vitest";

        import { ApiError } from "@/lib/api";

        import { applyBeforeSendFilters } from "./instrument-filters";

        function makeEvent(overrides: Partial<{ request: { url: string }; exception: { values: { value: string }[] } }> = {}) {
          return { request: { url: "https://3d.ezop.ddns.net/" }, exception: { values: [{ value: "Real error" }] }, ...overrides };
        }
        function makeHint(orig: unknown = undefined) {
          return { originalException: orig };
        }
        ```
  - [x] Subtask 3.3: 5 `it()` blocks in fixed order:
        - `drops_via_denyUrls`: event with `request.url = "chrome-extension://abc/inject.js"` → `applyBeforeSendFilters(...)` returns `null`.
        - `drops_via_ignoreErrors`: event with `exception.values[0].value = "ResizeObserver loop limit exceeded"` → returns `null`.
        - `drops_when_offline`: stub `navigator.onLine = false`, event passes shapes 1+2 cleanly → returns `null`. Restore `navigator.onLine = true` after.
        - `drops_access_expired`: hint with `originalException = new ApiError(401, { detail: "access_expired" }, "401")` → returns `null`.
        - `passes_through_default`: clean event + clean hint, navigator online → returns the event unchanged (`expect(result).toBe(event)`).
  - [x] Subtask 3.4: **GREEN.** Tests pass after Task 1 + Task 2 land.
  - [x] Subtask 3.5: **REFACTOR.** Inspect for clarity. The 5 `it()` blocks should read as a 5-step contract.

- [x] **Task 4: Update `instrument.test.ts` (existing tests still pass; add a smoke for `beforeSend` wiring)**
  - [x] Subtask 4.1: Confirm the existing 2 `it()` blocks still pass (DSN init + empty-DSN no-op). The new `beforeSend` property in `Sentry.init({...})` doesn't affect them.
  - [x] Subtask 4.2: Add 1 new assertion in the DSN-set block: `expect(call.beforeSend).toBe(applyBeforeSendFilters);` — confirms the filter function is wired at init time, not just defined. Import `applyBeforeSendFilters` at the top of the test file.

- [x] **Task 5: Validation gates (AC9, AC10, AC11)**
  - [x] Subtask 5.1: `npm run lint` → exit 0.
  - [x] Subtask 5.2: `npm run typecheck` → exit 0. The `body as { detail?: string } | null` cast satisfies `unknown`-typed `ApiError.body`.
  - [x] Subtask 5.3: `npm run test -- --run` → 5 new tests pass (instrument-filters), existing 7 tests in instrument.test.ts pass (with new `beforeSend` wiring assertion), 290+5 = 295/298 vitest (3 pre-existing CardCarousel fails out-of-scope).
  - [x] Subtask 5.4: `npm run test:visual` → 0 diffs across 4 projects.

- [x] **Task 6: Manual smoke (AC12, optional)** — skip if confidence is high after green.

- [x] **Task 7: Commit + auto-deploy (AC13)**
  - [x] Subtask 7.1: Stage modified + new files: `apps/web/src/instrument.ts`, `apps/web/src/instrument.test.ts`, `apps/web/src/instrument-filters.ts` (NEW), `apps/web/src/instrument-filters.test.ts` (NEW).
  - [x] Subtask 7.2: Conventional commit, scope `web`: `feat(web): beforeSend filter contract per architecture Decision H (Story 2.4)`. Body lists the 5-step ordering, references Story 2.1 paste-import, mentions Tech Success #3 measurement window.
  - [x] Subtask 7.3: `bash infra/scripts/deploy.sh`. Verify-symbolication smoke event will produce `Error: smoke <uuid>` with `value="smoke <uuid>"` — does NOT match either floor pattern, so passes through. Confirms filter doesn't break the verify ritual.

## Dev Notes

### Files being modified — current state and what changes

| Path | Current state | What this story changes | What must be preserved |
|---|---|---|---|
| `apps/web/src/instrument.ts` | 26 lines (Story 2.2 final). `Sentry.init({...})` with dsn/environment/release/sampleRate/tracesSampleRate; 6 `setTag` calls (1 baseline + 5 dotted-name); `export { Sentry }`. | +3 imports (`ErrorEvent`/`EventHint` types, `ApiError` value, `applyBeforeSendFilters`); +`beforeSend: applyBeforeSendFilters` line inside `Sentry.init({...})`. ~31 lines total. | Init guard, all 6 setTag calls, `release: RELEASE`, `export { Sentry }`. |
| `apps/web/src/instrument.test.ts` | 64 lines (Story 2.2 final). 2 `it()` blocks. | +1 import for `applyBeforeSendFilters`, +1 assertion `expect(call.beforeSend).toBe(applyBeforeSendFilters)` in the DSN-set block. ~67 lines total. | Both `it()` blocks; mock factory shape; baseline assertions. |
| `apps/web/src/instrument-filters.ts` | (NEW) | 3 exports: `denyUrls: RegExp[]`, `ignoreErrors: RegExp[]`, `applyBeforeSendFilters(event, hint)`. ~50-60 lines. | — |
| `apps/web/src/instrument-filters.test.ts` | (NEW) | 5 `it()` blocks covering branches in fixed order. ~80 lines. | — |

### Architecture pin: Decision H + AR6 (`beforeSend` filter contract)

> **AR6 (Decision H — beforeSend filter ordering):** Filter executes in fixed order with separate `if` branches and early `return null`: (1) `denyUrls` regex match against `event.request?.url`; (2) `ignoreErrors` title match against `event.exception?.values?.[0]?.value`; (3) `!navigator.onLine` → drop; (4) `hint.originalException instanceof ApiError && hint.originalException.body?.detail === "access_expired"` → drop; (5) return event unchanged.
> [Source: `_bmad-output/planning-artifacts/epics.md` line 143; architecture.md lines 205-210, 298-306]

**Non-negotiables:** order is fixed (cheapest exits first); branches are separate `if` blocks (NOT a single chained conditional); each drop branch has its own `return null`; final branch is the implicit "return event unchanged".

### Story 2.1 paste-import contract (NFR-I3)

`apps/web/src/instrument-filters.ts` paste-imports the `denyUrls` and `ignoreErrors` arrays from `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md`. Per Story 2.1 AC4: "Story 2.4 imports the derived ruleset literally — no manual translation, no reshuffling — so 2.4 ACs trace back to 2.1 evidence."

The discovery report layout is the contract; future re-runs of Story 2.1 produce a new dated markdown that REPLACES the current one's array bodies. Manual edits to `instrument-filters.ts` without a corresponding discovery refresh would drift the empirical floor away from observed reality (NFR-I3 breaking change).

**Empirical sample (2026-05-09):** 21 issues / 27 events, 100% synthetic/operator-driven, zero genuine production noise. Empirical additions = 0; floor patterns enacted as mandated. Re-run discovery 30 days post-organic-traffic activation.

### Why split filter logic to `instrument-filters.ts`?

The architecture pin (Decision H) and the original epic AC say "imported from a colocated module ... so they can be unit-tested independently and traced to Story 2.1". Direct test of `instrument.ts`'s in-place callback is fragile (requires capturing the callback from a `Sentry.init` spy). Extracting `applyBeforeSendFilters` to `instrument-filters.ts` (alongside the regex arrays) gives:

- Direct unit test surface (import + invoke).
- Single source-of-truth file for "what gets dropped" — easier to review, easier to update on next discovery refresh.
- `instrument.ts` stays a thin SDK-init shell.

### Why 5 separate `if` blocks (NOT one big conditional)?

Per architecture pin lines 298-306: "Each filter step is a separate `if` with early `return null` — readable, testable per branch." A single chained `if (a || b || c || d) return null` is harder to reason about under code review and harder to test per-branch (multi-cause failure modes).

### Why `navigator.onLine` runtime guard?

`navigator` is undefined in Node-like test environments (vitest with `jsdom` provides it, but unit tests of the pure filter function may run without DOM). The `typeof navigator !== "undefined"` guard makes the function safe to call from any context. Without the guard, the test scaffolding would have to set up jsdom for the offline branch — overengineering for a 1-line check.

### Why string-cast `body` as `{ detail?: string } | null`?

`ApiError.body` is `unknown` (typed loosely on purpose — the API returns variable shapes per endpoint). The structural cast `(body as { detail?: string } | null)?.detail` is the existing project pattern (see `apps/web/src/lib/api.ts:30`: `(body as { detail?: string })?.detail`). Optional chaining handles the `null`/missing-key cases.

### NFR pins

- **NFR-I3 (BMAD pipeline contract):** Story 2.1 → Story 2.4 paste-import is the contract. Drift is a breaking change requiring follow-up.
- **NFR-P1 (SDK overhead):** 5 short `if` checks per event. denyUrls is 3 regex tests against a string; ignoreErrors is 2 regex tests; offline + ApiError are O(1) checks. Aggregate per-event filter overhead < 10 µs; well within budget.

### File-structure footprint

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/instrument.ts` | MODIFIED | +3 imports, +`beforeSend: applyBeforeSendFilters` in `Sentry.init`. ~31 lines. |
| `apps/web/src/instrument.test.ts` | MODIFIED | +1 import, +1 assertion on `beforeSend` wiring. ~67 lines. |
| `apps/web/src/instrument-filters.ts` | NEW | `denyUrls`, `ignoreErrors`, `applyBeforeSendFilters`. ~55 lines. |
| `apps/web/src/instrument-filters.test.ts` | NEW | 5 `it()` blocks, fixed-order. ~80 lines. |

## Previous Story Intelligence

### From Story 2.3 (just shipped)

- **Codex caught a P2 staleness defect** post-dev. Same review discipline applies after 2.4 ships. Specifically watch for:
  - Filter chain ordering regressions (e.g., `body.detail` check before `instanceof ApiError` would match plain `ApiError` shapes that aren't actually ApiError instances).
  - Type-cast escape hatches (`as any`) creeping in to silence typecheck.
- **`vi.hoisted` pattern** for sentry mock spies in vitest (used in `AuthContext.test.tsx` review fix). If `instrument-filters.test.ts` ever needs to mock something cross-module-imported at top, use the same pattern.

### From Story 2.1 (the input contract)

- **Empirical sample = 21 issues, all synthetic/test/operator-driven.** No browser-extension URLs, no `ResizeObserver loop`, no `Script error.`, etc. Floor patterns are the entire ruleset.
- **Smoke events from `verify-symbolication.sh`** carry `value = "smoke <uuid>"` — does NOT match `/ResizeObserver loop/` or `/Non-Error promise rejection captured/`. They pass through `beforeSend` unchanged. The verify ritual remains intact post-2.4.
- **Synthetic alarm events** (`level: warning`, `message: "deploy verification failed: ..."`) have `event.exception?.values` empty (envelope-injected; not real exceptions). The `ignoreErrors` step's lookup `event.exception?.values?.[0]?.value` evaluates to `""` — passes through. **No regression on operator alarms.**

### From Story 2.2

- **`Sentry.init` config object** — 5 properties currently (dsn, environment, release, sampleRate, tracesSampleRate). 2.4 adds `beforeSend` as the 6th property. Order in the object literal doesn't matter for runtime; preferred placement is after `tracesSampleRate` (last among the existing properties), before any future additions.
- **Existing test mock pattern (`vi.mock("@sentry/react", () => ({ init: ..., setTag: ... }))`)** — extends naturally with the new `beforeSend` wiring assertion.

## Git Intelligence Summary

| SHA | Subject | Relevance |
|---|---|---|
| 8023404 | fix(web): re-emit auth.is_authenticated on every auth-state change (Story 2.3 review) | AuthContext + auth tag now stable across nav. Out of 2.4 scope. |
| c85cd30 | feat(web): dynamic context tags via router.subscribe (Story 2.3) | `attachRouterContext` adds 3 dynamic tags. Out of scope; `beforeSend` runs AFTER tag attachment, sees the full event with all 8 tags (5 static + 3 dynamic). |
| 6ce2640 | fix(infra): plumb VITE_BUILD_HOST through docker build (Story 2.2 review) | Docker plumbing. Out of 2.4 scope. |
| 70d60bb | feat(web): static identity tags on Sentry init (Story 2.2) | 5 static tags. Out of 2.4 scope; events 2.4 filters carry these tags. |
| 381fc8a | feat(web): single-source RELEASE constant (Story 1.2) | RELEASE imported in instrument.ts; not changed. |

## Latest Tech Information

### Sentry SDK 8.x — `beforeSend(event, hint)` API

- Signature: `(event: ErrorEvent, hint: EventHint) => ErrorEvent | null | Promise<ErrorEvent | null>`. Synchronous form returning `null` drops; returning the (possibly modified) event sends.
- `event.request?.url` is the page URL (browser SDK auto-attaches).
- `event.exception?.values?.[0]?.value` is the first exception's message (`Error.message` for native errors).
- `hint.originalException` is the JS object that was thrown — `unknown` type per Sentry typings, narrow via `instanceof` for ApiError.
- **No async needed** for this filter — all checks are synchronous. Returning a promise would defer the SDK send pipeline; not required here.

### `noUncheckedIndexedAccess` interaction

`event.exception?.values?.[0]` returns `value | undefined`. Optional chaining via `?.value` handles the undefined branch — no `!` non-null assertion needed.

### `ApiError` runtime shape

```typescript
class ApiError extends Error {
  constructor(public status: number, public body: unknown, message: string) {
    super(message);
  }
}
```

`status: number`, `body: unknown` (loose), `message: string` (inherited). The runtime narrow via `instanceof ApiError` is the only way to confirm the type — duck-typing on `body.detail` could match plain objects or other error subclasses.

## Project Context Reference

- **`api()` wrapper** is the only place ApiError is thrown. The 401 retry path inside `api()` already filters `access_expired` / `missing_access` — but THAT retry happens at fetch level, not Sentry level. The 401s that DO reach `beforeSend` are ones where the retry already failed (token rotation broke, etc.) OR the silent-refresh path returned ok and the original call succeeded — both shouldn't generate Sentry events anyway. The `access_expired` filter is belt-and-suspenders coverage for the edge where a 401 escapes the retry logic.
- **Path alias `@/*`** — used for `@/lib/api` and `@/instrument-filters` imports.
- **`verbatimModuleSyntax`** — `import type { ErrorEvent, EventHint } from "@sentry/react";` for type-only Sentry imports; `import { ApiError } from "@/lib/api";` for the runtime class.
- **`react-refresh/only-export-components`** — `instrument-filters.ts` exports both arrays and a function from a non-component file. ESLint rule applies only to .tsx route components / providers; non-component .ts modules are unaffected.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 452-471 — Story 2.4 verbatim ACs.
- `_bmad-output/planning-artifacts/architecture.md` lines 205-210 — Decision H.
- `_bmad-output/planning-artifacts/architecture.md` lines 298-306 — 5-step filter ordering pin.
- `_bmad-output/planning-artifacts/epics.md` line 143 — AR6.
- `_bmad-output/planning-artifacts/prd.md` Tech Success #3 — 7-day post-rollout zero-deny-list-match metric.
- `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` — Story 2.1 paste-import source.
- `apps/web/src/instrument.ts` — current state (Story 2.2 final, 26 lines).
- `apps/web/src/instrument.test.ts` — current test surface.
- `apps/web/src/lib/api.ts:5-9` — `ApiError` class definition.
- `apps/web/src/lib/api.ts:29-30` — existing `body as { detail?: string }` cast pattern.

## Dev Agent Record

### Agent Model Used

`claude-opus-4-7[1m]` — same session as create-story. 5h budget at 62% start.

### Debug Log References

- **RED:** `instrument-filters.test.ts` written first; `npm run test -- --run src/instrument-filters.test.ts` failed with "1 failed (no tests)" because `./instrument-filters` module didn't exist yet.
- **GREEN attempt 1:** after `instrument-filters.ts` + `instrument.ts` wiring, instrument-filters.test.ts → 5 passed in 2ms. But instrument.test.ts failed: `expect(call.beforeSend).toBe(applyBeforeSendFilters)` — `Object.is equality` fail with "Compared values have no visual difference". Root cause: `vi.resetModules()` in `beforeEach` re-evaluates `instrument.ts` per test, producing a fresh `applyBeforeSendFilters` function reference each time; the test-side import is from before-reset.
- **GREEN attempt 2:** Replaced reference equality with `expect(typeof call.beforeSend).toBe("function") && expect(call.beforeSend.name).toBe("applyBeforeSendFilters")`. Locks the wiring contract without coupling to identity. → instrument.test.ts 2/2 pass.
- **Lint:** zero output, exit 0.
- **Typecheck:** zero output, exit 0. The `(orig.body as { detail?: string } | null)?.detail` cast satisfies `unknown`-typed `ApiError.body`.
- **Full vitest:** 295/298 pass (3 pre-existing CardCarousel out-of-scope). 5 new instrument-filters tests pass; 2 instrument.test.ts pass with new wiring assertion.
- **Visual regression:** 46 passed / 14 skipped / 0 diffs across 4 projects.

### Completion Notes List

- **Implementation matched the story plan** — 5-step beforeSend chain in fixed order, each step a separate `if` block with early `return null`, traceable to architecture Decision H (lines 205-210, 298-306) and AR6.
- **Story 2.1 paste-import contract honored** — `denyUrls` and `ignoreErrors` array bodies copied verbatim from `glitchtip-discovery-2026-05-09.md`. Header doc-comment in `instrument-filters.ts` references the discovery report and the 30-day-organic-traffic-deferred rationale for zero empirical additions.
- **`vi.resetModules()` interaction with reference equality** — flagged for future story: when a test mocks `@sentry/react` AND imports a value from the SUT chain that uses `import.meta`-defined consts, `vi.resetModules()` re-evaluates the chain → reference equality fails. Solution: assert by `.name` + `typeof`. Same gotcha could surface in Story 2.5 if it were to test cross-module wiring.
- **`applyBeforeSendFilters` is exported from `instrument-filters.ts`** (not from `instrument.ts`) — this keeps the colocation principle (filter logic + regex arrays live together) and makes the unit test surface clean (import the function, mock event/hint, assert).
- **Smoke event compatibility verified by spec analysis:** verify-symbolication smoke produces `Error: smoke <uuid>` with `value="smoke <uuid>"` — does NOT match `/ResizeObserver loop/` or `/Non-Error promise rejection captured/`, passes through to GlitchTip. Synthetic alarm events have `event.exception?.values` empty (envelope-injected) — `value ?? ""` evaluates to `""`, no regex match, passes through. Both operational pathways remain intact.
- **Pre-existing failures still flagged** (Stories 2.1+2.2+2.3): 3 CardCarousel tests + Node 18 unplugin breakage. No new regressions.

### File List

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/instrument.ts` | MODIFIED | +3 imports, +`beforeSend: applyBeforeSendFilters`. |
| `apps/web/src/instrument.test.ts` | MODIFIED | +1 import, +1 wiring assertion. |
| `apps/web/src/instrument-filters.ts` | NEW | denyUrls + ignoreErrors arrays + applyBeforeSendFilters function. |
| `apps/web/src/instrument-filters.test.ts` | NEW | 5 it() blocks per Decision H ordering. |

### Change Log

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-09T~02:58Z | Claude Opus 4.7 (1M ctx) | TDD red→green→refactor: instrument-filters.ts module exports `denyUrls`, `ignoreErrors` (paste-imported from Story 2.1), and `applyBeforeSendFilters(event, hint)` 5-step chain; instrument.ts wires `beforeSend: applyBeforeSendFilters`. Lint + typecheck + 295/298 vitest + 46/0 visual. Status `in-progress → review`. Commit `4149507`. |
| 2026-05-09T~03:07Z | Codex review + Claude Opus 4.7 fix | Codex flagged P2 architectural-assumption gap: `event.request?.url` is the PAGE URL, not where extension errors originate (which is stack-frame `filename`). Step 1 was effectively a no-op for FR5's canonical case. Fix: belt-and-suspenders — keep request URL test, additionally iterate frames testing each `filename`. +1 unit test covering frame-filename match. Re-deploy + verify-symbolication clean (issue #51). Status `review → done`. Commit `9d6d207`. |

## Senior Developer Review (AI)

**Reviewer:** Codex (`codex review --commit 4149507`)
**Date:** 2026-05-09T~03:00Z (UTC)
**Outcome:** Changes Requested (1 P2 finding)

### Findings

| ID | Severity | Status | Location | Issue |
|---|---|---|---|---|
| R1 | P2 (Medium) | RESOLVED | `apps/web/src/instrument-filters.ts:57` (pre-fix) | denyUrls step matched only `event.request?.url`. Browser-extension exceptions thrown while the user is on the portal carry the extension URL inside `event.exception.values[0].stacktrace.frames[].filename`, while `request.url` is the portal origin — so FR5's main scenario was unfiltered. Sentry's own built-in `denyUrls` filter checks frame filenames; the architecture pin to "request URL only" was wrong by intent. |

### Action Items

- [x] **[AI-Review] [P2] Match denyUrls against frame filenames in addition to request URL.** Iterate the first exception's stack frames; test each `filename` against the same `denyUrls` regex array as the request URL. Belt-and-suspenders coverage strictly broader than the prior contract (never narrower). Add 1 unit test for the frame-filename match path. Update the architecture-pin header comment in `instrument-filters.ts` to reflect the broadened contract. **Resolved in commit `9d6d207`.**

### Notable absent findings

- 5-step chain ordering — accepted; matches Decision H.
- `instanceof ApiError` runtime narrow + `body as { detail?: string } | null` cast — accepted; matches existing api.ts pattern.
- `typeof navigator !== "undefined"` SSR guard — accepted.
- Story 2.1 paste-import contract honoring — accepted.
- vi.resetModules + by-name function assertion — accepted as correct workaround for module-reset reference identity.
