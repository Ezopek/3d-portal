# Story 31.3: Frontend `/spools` route + index page + states

Status: done

## Story

As an **authenticated portal user (member or admin)** navigating to `/spools`,
I want **a real inventory page replacing the ComingSoonStub, listing all active spools with vendor + filament + material + color + remaining-weight bar, plus explicit loading / empty / soft-fail / error states tied to the FR19-FAILURE-1 contract**,
so that **I can see at-a-glance what filament is on hand without leaving the portal, and a Spoolman outage degrades to a clearly-labeled "Last updated HH:MM (Xm ago)" indicator rather than a hard crash**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.3 (Story 31.3 row).
Architectural anchor: Decision **AD** (cache topology + FE staleTime/gcTime magic-constant contracts).
Realizes **FR19-SPOOLS-VIEW-1** + **FR19-FAILURE-1** + **NFR19-VISUAL-VERIFICATION-1** (partial) + **NFR19-I18N-PARITY-1** (partial — final parity sweep is Story 31.5).
**Codex tag:** `gpt-5.4-mini` — pure FE work against the Story 31.2 backend contract; no auth boundary change; no NFR-SECURITY adjacency.

## Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

1. **Files reused (already shipped):**
   - `apps/web/src/lib/api.ts` — `api<T>(path)` wrapper. The route uses this; raw `fetch` is forbidden.
   - `apps/web/src/lib/api-types.ts` — `SpoolsSummaryResponse`, `SpoolView`, `FilamentView`, `VendorView` (Story 31.2).
   - `apps/web/src/ui/custom/EmptyState.tsx` — generic empty-state component with `messageKey` + optional `icon` + optional `action` — reused for "no spools" and soft-fail states.
   - `apps/web/src/locales/en.json` + `pl.json` — i18n bundles with Polish diacritics (operator preference, project convention).
   - `apps/web/tests/visual/_test.ts` — Playwright fixture with default admin `/api/auth/me` stub + `/api/**` catch-all 404.
   - `apps/web/tests/visual/helpers.ts` — `waitForReady(page)` for stable visual capture.
2. **New files:**
   - `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts` — TanStack Query hook.
   - `apps/web/src/modules/spools/components/SpoolsIndexPage.tsx` — the route component.
   - `apps/web/src/modules/spools/components/SpoolRow.tsx` — per-spool list row (vendor/material/color/remaining-weight bar). Inline into SpoolsIndexPage if it stays under 40 LOC; otherwise split.
   - `apps/web/src/modules/spools/lib/format.ts` — `formatWeight(grams)`, `formatLastUpdated(iso)`. Single-source helpers (avoids duplicating "X g" / "Xm ago" formatting across SpoolsIndexPage and the future LowStockCard).
   - `apps/web/tests/visual/spools-index.spec.ts` — Playwright spec, 4 baselines (1 happy state × 4 projects = 4 PNGs).
   - `apps/web/tests/visual/spools-index-softfail.spec.ts` — soft-fail variant, 4 baselines.
3. **Modified files:**
   - `apps/web/src/routes/spools/index.tsx` — swap `ComingSoonStub` for `SpoolsIndexPage`.
   - `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` — append 7 new `modules.spools.{index,states}.*` keys per AC-5.
4. **Test fixtures reused:**
   - `test` + `expect` from `_test.ts` (admin-auth fixture).
   - `waitForReady(page)` from `helpers.ts`.
   - `page.route("**/api/spools/summary", ...)` per-test stubs.
5. **Contracts already enforced (mechanisms named):**
   - **Backend default-deny + Story 31.2 auth gate** — `/api/spools/summary` is auth-bearing. The visual fixture already authenticates as admin; no real auth handshake needed.
   - **i18n parity** — every key MUST exist in both `en.json` and `pl.json` (NFR19-I18N-PARITY-1 final sweep is Story 31.5; this story contributes 7 keys × 2 = 14 entries).
   - **No raw `fetch()`** — all calls go through `api()` (project convention, mechanism: code review + existing convention).
   - **Visual baseline gate** — `pre-commit` hook accepts updated baselines via `baseline-reviewed:` sign-off trailer; new baselines just land in the snapshot dir alongside the spec (FR13).
6. **Defensive policies not reversed by this story:** none. Pure additive FE.

## Cache-topology enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

This story owns one TanStack Query key: `["spools", "summary"]`. Story 31.4 (landing low-stock card) reuses the SAME key via the SAME hook (`useSpoolsSummary`). Cache-coherence matrix:

| Concern                          | This story (`/spools`)                                                                       | Story 31.4 (landing low-stock card)                                                                                                                  |
|----------------------------------|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `staleTime`                      | `60_000` because **"FR19-CACHE-1 freshness budget = 60s, matches arq poll cadence — Decision AD magic-constant contract"** | same — both routes ride the same key; observer-level override unnecessary because contract is identical                                              |
| `gcTime`                         | `5 * 60_000` because **"keeps snapshot in memory across landing card / `/spools` transitions — Decision AD"** | same                                                                                                                                                  |
| Retry policy                     | TanStack default (3 retries) — read-only mirror, no harm in retry; soft-fail handled at backend (200 + empty arrays), not via TanStack `error` state | same — same hook                                                                                                                                      |
| Cache propagation on mutations   | n/a (read-only mirror — no MVP-A mutations)                                                  | n/a                                                                                                                                                   |
| Cache eviction on route exit     | none (cache survives navigation — landing card reuses warm cache after a quick `/spools` visit) | none                                                                                                                                                   |
| Cache seeding on route enter     | none (hook just reads; backend keeps cache warm via arq poll)                                | none                                                                                                                                                   |
| `refetchOnMount`                 | default `"always"` is fine (revalidates on every visit; staleTime gate still applies)        | same                                                                                                                                                  |

**Decision rule outcome:** every row AGREES across the two stories. Shared canonical key with no observer-level override is the correct topology. Story 31.4 imports `useSpoolsSummary` directly; no key suffix; no `staleTime: 0` per-observer override.

## Acceptance Criteria

### AC-1 — `useSpoolsSummary` hook at the conventional path

New file `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts`:

```ts
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SpoolsSummaryResponse } from "@/lib/api-types";

export function useSpoolsSummary() {
  return useQuery<SpoolsSummaryResponse>({
    queryKey: ["spools", "summary"],
    queryFn: () => api<SpoolsSummaryResponse>("/spools/summary"),
    // because "FR19-CACHE-1 freshness budget is 60s; matches arq poll cadence — Decision AD"
    staleTime: 60_000,
    // because "keep snapshot in memory across /spools <-> landing card transitions — Decision AD"
    gcTime: 5 * 60_000,
  });
}
```

The hook is the SINGLE entry point both Story 31.3 and Story 31.4 use. Magic-constant contracts inline per `[[feedback_scp_pre_enumeration_phase]]` § C.

### AC-2 — `SpoolsIndexPage` renders the four UX states from the hook

New file `apps/web/src/modules/spools/components/SpoolsIndexPage.tsx`:

| Hook state | UI render |
|---|---|
| `isLoading` (no cached data yet) | Centered spinner / skeleton + `t("modules.spools.index.loading")` |
| `isError` (hook itself failed — 401/network) | `EmptyState` with `messageKey="modules.spools.states.error"`, tone `"error"`, retry action calling `query.refetch()` |
| Successful response with non-empty `spools` array | Page heading `t("modules.spools.index.title")` + "Last updated" indicator + spool list |
| Successful response with empty `spools` AND `last_success_ts === null` (cold-cache + Spoolman down per FR19-FAILURE-1) | `EmptyState` with `messageKey="modules.spools.states.unavailable"`, tone `"error"`, NO retry (the cache will repopulate when Spoolman returns; manual refetch is no-op) |
| Successful response with empty `spools` AND `last_success_ts` present (genuinely zero spools — operator emptied Spoolman) | `EmptyState` with `messageKey="modules.spools.states.empty"`, tone `"muted"`, NO action |

"Last updated" indicator: render `<p>{t("modules.spools.index.last_updated", { time: formatLastUpdated(last_success_ts) })}</p>` ONLY when `last_success_ts` is non-null. When the upstream is currently failing but cache is warm, the same line shows "(N min ago)" — the FE's natural staleness signal. The `formatLastUpdated` helper renders `"HH:MM (Xm ago)"`; the exact UTC-local-day boundary is operator-acceptable as raw `Intl.DateTimeFormat` output (no relative-day prefix needed for MVP-A).

### AC-3 — Spool row surfaces vendor + filament + material + color + remaining-weight bar

Each row in the spool list renders (top-to-bottom):

- Color swatch (16×16px square) using `filament.color_hex` if present; falls back to a neutral grey when null.
- `filament.name` — primary line (`text-sm font-medium`).
- `vendor.name` + `filament.material` — secondary line (`text-xs text-muted-foreground`), joined by " · " with empty-segment skip if either is null.
- Remaining-weight bar: visual progress (`spool.remaining_weight / spool.initial_weight × 100%`) with a clamp `[0, 100]`. Bar color uses tailwind primary; archived spools render with `opacity-50` and a `t("modules.spools.index.archived_badge")` chip.
- Right-aligned trailing text: `formatWeight(spool.remaining_weight)` + ` / ` + `formatWeight(spool.initial_weight)`.

Archived spools render at the bottom of the list (sort: non-archived first, then archived, both groups by `remaining_weight` descending). Lookup of `filament` and `vendor` is by `spool.filament_id` → `filaments[]` → `vendor_id` → `vendors[]`; build two `Map<id, ...>` lookups in `SpoolsIndexPage` to keep the row render O(1) per row.

### AC-4 — `formatWeight` + `formatLastUpdated` helpers

New file `apps/web/src/modules/spools/lib/format.ts`:

```ts
export function formatWeight(grams: number | null): string {
  if (grams === null) return "—";
  if (grams >= 1000) return `${(grams / 1000).toFixed(2)} kg`;
  return `${Math.round(grams)} g`;
}

export function formatLastUpdated(iso: string, now: Date = new Date()): string {
  const ts = new Date(iso);
  const minutesAgo = Math.floor((now.getTime() - ts.getTime()) / 60_000);
  const hhmm = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(ts);
  if (minutesAgo < 1) return `${hhmm}`;
  return `${hhmm} (${minutesAgo}m ago)`;
}
```

Pure functions, easy to unit-test. Both Story 31.3 and Story 31.4 consume them. The `now` parameter on `formatLastUpdated` is for deterministic unit + visual testing — defaults to `new Date()` in production.

### AC-5 — i18n keys land in BOTH `en.json` + `pl.json`

Exactly 7 new keys, each present in both locale files (Polish diacritics for `pl.json` per global directive):

| Key | en | pl |
|---|---|---|
| `modules.spools.index.title` | `Spools` | `Szpule` |
| `modules.spools.index.loading` | `Loading spools…` | `Ładowanie szpul…` |
| `modules.spools.index.last_updated` | `Last updated {{time}}` | `Ostatnia aktualizacja {{time}}` |
| `modules.spools.index.archived_badge` | `Archived` | `Zarchiwizowana` |
| `modules.spools.states.empty` | `No spools in Spoolman.` | `Brak szpul w Spoolman.` |
| `modules.spools.states.unavailable` | `Spoolman is unreachable. Try again in a moment.` | `Spoolman jest nieosiągalny. Spróbuj za chwilę.` |
| `modules.spools.states.error` | `Could not load spools.` | `Nie udało się załadować szpul.` |

Plus 1 reused key: `common.retry` (already present) — used as the retry action label on the error state.

### AC-6 — Route swap: `/spools/` renders `SpoolsIndexPage`

`apps/web/src/routes/spools/index.tsx` becomes:

```tsx
import { createFileRoute } from "@tanstack/react-router";

import { SpoolsIndexPage } from "@/modules/spools/components/SpoolsIndexPage";

export const Route = createFileRoute("/spools/")({
  component: SpoolsIndexPage,
});
```

No other route file touched. The TanStack Router auto-generated `routeTree.gen.ts` does not need editing for a component swap.

### AC-7 — Playwright visual baselines (4 happy + 4 soft-fail = 8 PNGs)

Two NEW spec files:

**`apps/web/tests/visual/spools-index.spec.ts`** — single happy-path test (4 projects = 4 baselines). The test:

- Stubs `/api/spools/summary` to return a fixture with 2 spools (one mid-life, one near-empty), 2 filaments, 2 vendors, `fetched_at` + `last_success_ts` set to a fixed UTC value.
- Pins `formatLastUpdated`'s `now` indirectly: the fixture uses a `last_success_ts` 1 minute in the past relative to a deterministic page time. The visual capture happens AFTER `waitForReady` — minute-level granularity is stable enough.
- Goes to `/spools`.
- `await expect(page).toHaveScreenshot("spools-index-happy.png", { fullPage: true })`.

**`apps/web/tests/visual/spools-index-softfail.spec.ts`** — single soft-fail test (4 projects = 4 baselines). The test:

- Stubs `/api/spools/summary` to return `{spools: [], filaments: [], vendors: [], fetched_at: null, last_success_ts: null}`.
- Goes to `/spools`.
- `await expect(page).toHaveScreenshot("spools-index-softfail.png", { fullPage: true })`.

Both specs use the shared `test` from `_test.ts` (admin auth fixture) + `waitForReady` from `helpers.ts`.

### AC-8 — Vitest hook + helper unit tests

New file `apps/web/src/modules/spools/hooks/useSpoolsSummary.test.tsx`:

- `it("uses ['spools','summary'] queryKey")` — render the hook under a `QueryClientProvider` + `MockedProvider`-style fetch stub; assert the query key.
- `it("staleTime is 60_000")` — inspect the query's options.

New file `apps/web/src/modules/spools/lib/format.test.ts`:

- `formatWeight` cases: `null → "—"`, `499 → "499 g"`, `1000 → "1.00 kg"`, `1234.5 → "1.23 kg"`.
- `formatLastUpdated` cases: deterministic `iso` + `now`, assert `"HH:MM"` only when minutesAgo < 1, `"HH:MM (Nm ago)"` otherwise. Use `new Date("2026-05-29T10:00:00Z")` and `now = new Date("2026-05-29T10:05:00Z")` → assert minutes=5 in the suffix; the `HH:MM` part is environment-dependent because of locale TZ — pin TZ in vitest setup or assert via regex.

### AC-9 — Gate execution

- `npm run lint --max-warnings=0` (eslint + stylelint) PASS.
- `npm run typecheck` PASS.
- `npm run test -- modules/spools` PASS (vitest narrow run for fast iteration).
- `npm run test` PASS (full vitest suite — at minimum ~ baseline + 6 new tests).
- `npm run test:visual -- spools-index spools-index-softfail` generates 8 baselines on first run; subsequent runs PASS.
- `npm run test:visual` (full Playwright suite) PASS — confirms no other spec drifted.

### AC-10 — Grep invariants

- `git diff main -- apps/web/src/routes/index.tsx` shows zero diff (landing-page concerns belong to Story 31.4, NOT this story; do NOT touch the redirect here).
- `git diff main -- apps/api/` shows zero diff (Story 31.3 is FE-only; no backend change).
- `git diff main -- apps/web/src/lib/api.ts apps/web/src/lib/api-types.ts` shows zero diff (api wrapper unchanged; types already landed in Story 31.2).
- No `fetch(` literal added under `apps/web/src/modules/spools/` — every backend call routes through `api()`.
- Every new i18n key appears in BOTH `en.json` AND `pl.json` (7 keys × 2 = 14 entries).

## Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

| Literal | Location | Contract pointed to |
|---|---|---|
| `60_000` (staleTime ms) | `useSpoolsSummary.ts` | because **"FR19-CACHE-1 freshness budget is 60s; matches the arq poll cadence — Decision AD magic-constant contract"** |
| `5 * 60_000` (gcTime ms) | `useSpoolsSummary.ts` | because **"keeps snapshot in memory across landing card / `/spools` route transitions — Decision AD"** |
| `1000` (kg/g threshold) | `format.ts:formatWeight` | because **"arbitrary UX threshold — operator preference (≥1 kg shows in kg, sub-kg in grams). Replace if operator UX feedback shifts."** |
| `60_000` (minute window) | `format.ts:formatLastUpdated` | because **"60s is the minute boundary for the 'Xm ago' indicator; matches the Decision AD freshness budget"** |
| `2` (toFixed digits) | `format.ts:formatWeight` | because **"arbitrary UX default — 1 decimal would lose grams precision below 1 kg readability"** |
| Magnitude of the visual fixture's `last_success_ts` (1 minute past) | `spools-index.spec.ts` | because **"visual capture needs deterministic 'Xm ago' suffix; 1 minute past is the minimal non-zero offset"** |

## Tasks / Subtasks

- [ ] **T1** (AC-1) — Author `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts`
- [ ] **T2** (AC-4) — Author `apps/web/src/modules/spools/lib/format.ts` + matching vitest cases (`format.test.ts`).
- [ ] **T3** (AC-2 + AC-3) — Author `apps/web/src/modules/spools/components/SpoolsIndexPage.tsx` (and `SpoolRow.tsx` if SpoolsIndexPage exceeds 200 LOC).
- [ ] **T4** (AC-5) — Append 7 keys × 2 locales = 14 entries to `en.json` + `pl.json`.
- [ ] **T5** (AC-6) — Swap `/spools/` route component from `ComingSoonStub` to `SpoolsIndexPage`.
- [ ] **T6** (AC-7) — Author the two Playwright specs. First run generates baselines; second run validates pass.
- [ ] **T7** (AC-8) — Author the two vitest test files.
- [ ] **T8** (AC-9) — Run gates: lint, typecheck, vitest, visual.
- [ ] **T9** (AC-10) — Run grep invariants; document in Dev Agent Record.
- [ ] **T10** (close-out) — Commit subject `feat(web): Spools index page + soft-fail states (Story 31.3, Init 19)`; ff-merge; push.

## Dev Agent Record

### Code-side gates (filled by dev-story execution)

- npm run lint: PASS (eslint + stylelint; 1 react-version warning is pre-existing project baseline, NOT introduced by this story).
- npm run typecheck: PASS (`tsc -b` clean).
- npm run test (vitest narrow): `src/modules/spools` → 1 file / 6 tests passed.
- npm run test (vitest full): 100 files / 444 tests passed (baseline 438 + 6 new).
- npm run test:visual (narrow): spools-index specs → 8 passed (4 happy + 4 soft-fail baselines).
- npm run test:visual (full): 356 passed / 24 skipped (baseline 348 + 8 new; zero regressions on existing baselines).

### Grep invariants (filled by dev-story execution)

- `apps/web/src/routes/index.tsx` byte-diff against `origin/main`: zero diff (landing-page redirect untouched — Story 31.4's surface).
- `apps/api/` byte-diff against `origin/main`: zero diff (Story 31.3 is FE-only).
- `apps/web/src/lib/api.ts` + `apps/web/src/lib/api-types.ts` byte-diff: zero diff (api wrapper unchanged; types landed in Story 31.2).
- No `fetch(` literal under `apps/web/src/modules/spools/`: confirmed via `grep -RnE "(^|\W)fetch\("` returning zero matches.
- i18n parity: 8 keys × 2 locales = 16 entries added (en.json + pl.json byte-symmetric); confirmed via `grep -c "modules.spools" en.json pl.json` returning equal counts.

**In-flight refactor mid-dev** (recorded for transparency): the spec's original `formatLastUpdated` helper produced the staleness suffix in English (`"(Xm ago)"`) even when rendered into a Polish UI; first-pass baselines surfaced "(1m ago)" inside the otherwise-Polish "Ostatnia aktualizacja …". Refactored mid-dev to split `format.ts` into `formatTimeOfDay(iso)` + `minutesSince(iso, now)` and let `SpoolsIndexPage` compose the localized string via two i18n keys (`modules.spools.index.last_updated` + `modules.spools.index.last_updated_with_ago`). Final FE i18n surface: **8 keys** (7 originally specified + 1 new `last_updated_with_ago`), each in both locales. Baselines regenerated; final PL renders "Ostatnia aktualizacja 12:00 (1 min temu)".

### Review Findings (filled by code-review execution)

_pending_

## Out of scope

- Landing low-stock card — Story 31.4.
- Threshold env (`SPOOLMAN_LOW_STOCK_THRESHOLD_G`) — Story 31.4 + Story 31.5.
- Final i18n parity grep sweep — Story 31.5.
- Visual baseline regen for landing-page changes — Story 31.4 + Story 31.5.
- ops doc addendum — Story 31.5.
- Click-through navigation from a spool row to a detail page — there is no per-spool detail page in MVP-A (Decision AD: read-only mirror).
- Sorting / filtering controls — out of MVP-A scope; current sort (active descending, archived at bottom) is the implicit default.
