# Story 31.4: Frontend landing low-stock card

Status: done

Spec status: review → done after Round-1 review applied 1 [Important] patch (threshold-boundary comment + test case) and ratified 1 [Important] as already operator-sanctioned by the SCP B5 demoable-signal directive.

## Story

As an **authenticated portal user** opening the portal at `/`,
I want **a real landing dashboard that prominently surfaces a "Low stock" card listing every spool whose `remaining_weight` is below the operator-set threshold (default 200 g), so the two real low-stock spools at session start (PLA Speed Matt White 138.9 g + PCTG Army Green 163.2 g per brainstorm B5) appear on first visit**,
so that **the demoable B5 signal lands without leaving the portal, and the previous `/` → `/catalog` redirect (deferred-by-design until a second module shipped) graduates to a real dashboard now that `/spools` is live**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-29-spoolman.md` § §4.3 (Story 31.4 row) + § Success criteria L541.
Architectural anchor: Decision **AD** (shared canonical query key with Story 31.3).
Realizes **FR19-LOWSTOCK-1** + **NFR19-VISUAL-VERIFICATION-1** (partial) + **NFR19-I18N-PARITY-1** (partial — final sweep is Story 31.5).
**Codex tag:** `gpt-5.4-mini` — pure FE work; no auth boundary change; no NFR-SECURITY adjacency.

## Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

1. **Files reused (already shipped):**
   - `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts` — Story 31.3 hook. Story 31.4 imports it directly; same `queryKey: ["spools", "summary"]`; no observer-level override (cache-topology table in Story 31.3 confirmed agreement).
   - `apps/web/src/modules/spools/lib/format.ts` — `formatWeight` + `formatTimeOfDay` + `minutesSince`. Reused verbatim.
   - `apps/web/src/lib/api-types.ts` — `SpoolsSummaryResponse`, `SpoolView`, `FilamentView` (Story 31.2).
   - `apps/web/src/ui/card.tsx` — shadcn Card / CardHeader / CardTitle / CardContent.
   - `apps/web/src/ui/custom/EmptyState.tsx` — soft-fail rendering.
   - `apps/web/tests/visual/_test.ts` + `helpers.ts` — admin-auth fixture + `waitForReady`.
2. **New files:**
   - `apps/web/src/modules/spools/components/LowStockCard.tsx` — the card.
   - `apps/web/src/modules/landing/LandingPage.tsx` — the dashboard. Inline a small hero with two quick-link tiles (Catalog + Spools) so the LowStockCard does not appear orphaned on an otherwise-empty page.
   - `apps/web/tests/visual/landing-low-stock.spec.ts` — 1 happy test × 4 projects = 4 PNGs.
   - `apps/web/tests/visual/landing-low-stock-softfail.spec.ts` — 1 soft-fail test × 4 projects = 4 PNGs.
   - `apps/web/src/modules/spools/components/LowStockCard.test.tsx` — vitest cases for the filter + sort logic.
3. **Modified files:**
   - `apps/web/src/routes/index.tsx` — swap the `beforeLoad: redirect → /catalog` shape for `component: LandingPage`. The original deferral comment ("V1 ships with one working module" — confusing-first-impression rationale) NO LONGER APPLIES now that `/spools` ships; spec calls this out explicitly so the upgrade is intentional, not accidental.
   - `apps/web/src/routes/index.test.tsx` — rewrite (the existing test asserts the redirect throws to `/catalog`; this is exactly what Story 31.4 is removing). Replace with a smoke test that asserts `Route.options.component === LandingPage` and the redirect descriptor is no longer present.
   - `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` — append 6 new `modules.spools.lowstock.*` + `landing.*` keys per AC-5.
4. **Test fixtures reused:**
   - `test` + `expect` from `_test.ts`.
   - `waitForReady(page)` from `helpers.ts`.
   - `page.route("**/api/spools/summary", ...)` per-test stubs.
5. **Contracts already enforced (mechanisms named):**
   - **AuthGate at the shell level** — the landing page is auth-protected via `AppShell.tsx` (Decision O). Anonymous visits to `/` already redirect to `/login` via the shell, so the new LandingPage does not need its own auth gate.
   - **i18n parity** — every new key MUST exist in both locale files. Story 31.5's final sweep audits the full `modules.spools.*` + `landing.*` namespace.
   - **Backend route auth gate** — `/api/spools/summary` is `Depends(current_user)` per Story 31.2 AC-2; the LowStockCard's data request inherits the same gate.
   - **TanStack Query single-cache invariant** — Stories 31.3 + 31.4 use the SAME `queryKey: ["spools","summary"]`. A second observer on the same key shares the cached snapshot; no extra network call when navigating between `/` and `/spools`.
6. **Defensive policies not reversed by this story:** none. Pure additive FE — the redirect-on-`/` deferral was provisional and explicitly conditioned on "second module ships".

## Cache-topology enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

Same table as Story 31.3 (only the consumer surface changes; the key + budget contract is identical). Re-asserting the agreement:

| Concern | Story 31.3 (`/spools`) | Story 31.4 (`/` LowStockCard) |
|---|---|---|
| Query key | `["spools","summary"]` | `["spools","summary"]` — same hook, same key |
| `staleTime` | `60_000` (FR19-CACHE-1 freshness budget) | same |
| `gcTime` | `5 * 60_000` (cross-route survival) | same |
| Retry | TanStack default | same |
| Mutation propagation | n/a (read-only mirror) | n/a |
| Eviction on route exit | none | none |
| Seeding on route enter | none | none |

Cache contract holds — `useSpoolsSummary` imported with zero per-observer overrides.

## Acceptance Criteria

### AC-1 — Low-stock threshold constant + magic-constant contract

`apps/web/src/modules/spools/components/LowStockCard.tsx` defines:

```ts
// because "operator UX preference at MVP-A — ≤200g treated as 'low' on a
// standard 1 kg spool; Story 31.5 documents the constant in operations.md
// addendum (no env override in MVP-A — a hardcoded number is the smallest
// surface; promote to env in a follow-up if operator wants runtime tuning)"
export const LOW_STOCK_THRESHOLD_G = 200;
```

The constant is module-level; pure functions in the same file consume it. No env wiring in MVP-A — `SPOOLMAN_LOW_STOCK_THRESHOLD_G` env slot is documented in Story 31.5's operations.md addendum as the upgrade path, NOT shipped here. Justification: operator can flip the number in one file + redeploy; runtime env adds wiring overhead without UX benefit at MVP-A.

### AC-2 — `LowStockCard` renders the four UX states

| Hook state | UI render |
|---|---|
| `isLoading` (no cached data) | Card with `t("modules.spools.lowstock.title")` header + skeleton-equivalent label (`t("modules.spools.lowstock.loading")`) |
| `isError` | Card with title + `EmptyState messageKey="modules.spools.lowstock.error" tone="error"` + Retry action |
| `data.spools` non-empty AND at least one spool has `remaining_weight < LOW_STOCK_THRESHOLD_G AND !archived` | Card title + list of low-stock rows (compact: color swatch + filament.name + `formatWeight(remaining_weight)`) + last-updated indicator (composed via same i18n keys as Story 31.3 — `last_updated` / `last_updated_with_ago`) |
| `data.spools` non-empty BUT no spool below threshold | Card title + `EmptyState messageKey="modules.spools.lowstock.all_ok" tone="muted"` + last-updated indicator |
| `data.spools` empty AND `last_success_ts === null` (cold-cache + Spoolman down) | Card title + `EmptyState messageKey="modules.spools.lowstock.unavailable" tone="error"` (no Retry — cache repopulates via arq) |
| `data.spools` empty AND `last_success_ts !== null` | Card title + same "no low-stock" empty state as the non-empty-but-all-OK case (operator emptied Spoolman; treat as "all good") |

Archived spools are EXCLUDED from the low-stock list (operator already moved them out of rotation; surfacing them as "low" is noise). The filter operates on `!archived && remaining_weight !== null && remaining_weight < LOW_STOCK_THRESHOLD_G`.

### AC-3 — Low-stock row compact format

Each low-stock row renders as a single line (no progress bar; the card is a quick-glance summary):

- Color swatch (12×12) using `filament.color_hex` if present; neutral grey fallback.
- `filament.name` — primary text.
- Right-aligned `formatWeight(spool.remaining_weight)` — bold or accent color.

Sort: ascending `remaining_weight` (lowest first — most-urgent spool at the top). The card lists up to 5 spools; if more exist, append a footer line `t("modules.spools.lowstock.more_count", { n: extra })` where `extra = totalLowStock - 5`. The `+N` overflow indicator is shipped behind a constant in the file (also documented inline with the magic-constant contract pointer):

```ts
// because "operator UX preference — keep the card compact; a 5-spool list
// fits the dashboard hero without a scroll bar at the desktop breakpoint."
const LOW_STOCK_LIST_CAP = 5;
```

### AC-4 — `LandingPage` hosts the LowStockCard prominently

`apps/web/src/modules/landing/LandingPage.tsx`:

- Page wrapper: `<div className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-10">`.
- Hero block: `<h1>{t("landing.title")}</h1>` + `<p className="text-sm text-muted-foreground">{t("landing.subtitle")}</p>`.
- Quick-link tile grid: two `<Link>` cards — one to `/catalog`, one to `/spools`. Each renders its module name + a 1-line teaser (`t("landing.tile.catalog.label")` + `.description`, same shape for `.tile.spools`). Tile shape: shadcn `Card` with `CardHeader` + `CardContent`. Grid `grid-cols-1 md:grid-cols-2 gap-4`.
- Low-stock card mounted below the tile grid: `<LowStockCard />`.

The hero + tiles use the same Card primitives as the rest of the project, so no new UI primitives ship in this story.

### AC-5 — i18n keys land in BOTH `en.json` + `pl.json`

Exactly 9 new keys (with Polish translations):

| Key | en | pl |
|---|---|---|
| `landing.title` | `Dashboard` | `Pulpit` |
| `landing.subtitle` | `Welcome back. Pick a module to dive in.` | `Witaj. Wybierz moduł, by zacząć.` |
| `landing.tile.catalog.label` | `Catalog` | `Katalog` |
| `landing.tile.catalog.description` | `Browse models, filters, and detail pages.` | `Przeglądaj modele, filtry i strony szczegółów.` |
| `landing.tile.spools.label` | `Spools` | `Szpule` |
| `landing.tile.spools.description` | `Live filament inventory mirrored from Spoolman.` | `Aktualny stan filamentów z Spoolman.` |
| `modules.spools.lowstock.title` | `Low stock` | `Mało filamentu` |
| `modules.spools.lowstock.loading` | `Checking spool levels…` | `Sprawdzanie stanu szpul…` |
| `modules.spools.lowstock.error` | `Could not load low-stock list.` | `Nie udało się załadować listy.` |
| `modules.spools.lowstock.all_ok` | `Every spool is above the threshold.` | `Każda szpula jest powyżej progu.` |
| `modules.spools.lowstock.unavailable` | `Spoolman is unreachable.` | `Spoolman jest nieosiągalny.` |
| `modules.spools.lowstock.more_count` | `and {{n}} more` | `i jeszcze {{n}}` |

Reused (already shipped): `common.retry`, `modules.spools.index.last_updated`, `modules.spools.index.last_updated_with_ago`.

Total new keys: **12** (3 `landing.*` + 6 `landing.tile.*` + actually let me recount). Re-counting the table above: 6 `landing.*` + 6 `modules.spools.lowstock.*` = **12 keys × 2 locales = 24 entries**.

### AC-6 — Route swap: `/` renders `LandingPage`

`apps/web/src/routes/index.tsx`:

```tsx
import { createFileRoute } from "@tanstack/react-router";

import { LandingPage } from "@/modules/landing/LandingPage";

export const Route = createFileRoute("/")({
  component: LandingPage,
});
```

Rewrite `apps/web/src/routes/index.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";

import { Route as IndexRoute } from "./index";
import { LandingPage } from "@/modules/landing/LandingPage";

describe("/ (landing)", () => {
  it("renders the landing page component (no redirect)", () => {
    expect(IndexRoute.options.component).toBe(LandingPage);
    expect(IndexRoute.options.beforeLoad).toBeUndefined();
  });
});
```

The old assertion ("beforeLoad redirects to /catalog") is removed; the new assertion documents that the redirect deferral has ended.

### AC-7 — Playwright visual baselines

Two NEW spec files:

**`apps/web/tests/visual/landing-low-stock.spec.ts`** — single happy-path test (4 projects = 4 baselines). The fixture mirrors the brainstorm B5 signal: 4 spools total, 2 of them low-stock (`remaining_weight` 138.9 g and 163.2 g, matching the real session-start state), 2 above threshold. The test:

- Pins `page.clock.install({ time: FIXED_NOW_ISO })` for stable timestamp.
- Stubs `/api/spools/summary` with a fixed payload (`last_success_ts` 1 minute behind FIXED_NOW).
- Goes to `/`.
- `await expect(page).toHaveScreenshot("landing-low-stock-happy.png", { fullPage: true })`.

**`apps/web/tests/visual/landing-low-stock-softfail.spec.ts`** — single soft-fail test (4 projects = 4 baselines):

- Stubs `/api/spools/summary` to return `{spools: [], filaments: [], vendors: [], fetched_at: null, last_success_ts: null}`.
- Goes to `/`.
- `await expect(page).toHaveScreenshot("landing-low-stock-softfail.png", { fullPage: true })`.

**Existing baseline regen risk:** the `/catalog` redirect was the implicit landing for some existing test specs (e.g. `accessibility-axe.spec.ts`, anything that uses `page.goto("/")` then asserts URL). Story 31.4 changes the / behavior. Audit all existing specs for `page.goto("/")` and either (a) update them to `goto("/catalog")` if they intended the catalog OR (b) accept that the landing now renders a different page and regen affected baselines. Story 31.5 owns the "regen any existing baselines that drift" sweep — but THIS story owns the audit + obvious updates.

### AC-8 — Vitest unit tests

New file `apps/web/src/modules/spools/components/LowStockCard.test.tsx`:

- `it("filters spools by threshold (200g default)")` — fixture with 4 spools (2 below, 2 above) → component renders 2 low-stock rows.
- `it("excludes archived spools from low-stock list")` — fixture with an archived spool whose `remaining_weight=10g` → row is hidden.
- `it("sorts low-stock rows by remaining_weight ascending")` — fixture with 138.9 + 163.2 → asserts 138.9 renders before 163.2 in the DOM.
- `it("renders 'all OK' empty state when nothing is below threshold")` — fixture with all spools above 200g → assert the `lowstock.all_ok` message text appears.
- `it("renders 'unavailable' empty state on cold-cache + soft-fail")` — fixture with empty arrays + null last_success_ts → assert `lowstock.unavailable` text.

The existing `format.test.ts` already covers the helpers; no duplicate cases.

### AC-9 — Gate execution

- `npm run lint --max-warnings=0` PASS (1 pre-existing react-version warning unchanged).
- `npm run typecheck` PASS.
- `npm run test` PASS (full vitest; baseline + 5 new cases + the rewritten landing test).
- `npm run test:visual` PASS (full Playwright; baseline + 8 new + any regen of `/`-touching specs).

### AC-10 — Grep invariants

- `git diff main -- apps/api/` shows zero diff (Story 31.4 is FE-only).
- `git diff main -- apps/web/src/lib/api.ts apps/web/src/lib/api-types.ts` shows zero diff (types from 31.2; api wrapper unchanged).
- No `fetch(` literal added under `apps/web/src/modules/spools/` or `apps/web/src/modules/landing/` — every backend call routes through `api()` (via the shared `useSpoolsSummary` hook).
- All 12 new i18n keys appear in BOTH `en.json` AND `pl.json` (`grep -c "lowstock\\|^  \"landing\\."` on both files returns equal counts).

## Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

| Literal | Location | Contract pointed to |
|---|---|---|
| `200` (low-stock threshold, grams) | `LowStockCard.tsx` `LOW_STOCK_THRESHOLD_G` | because **"operator UX preference at MVP-A — 200g treated as 'low' on a standard 1 kg spool; Story 31.5 documents the value in operations.md addendum (no env override in MVP-A by design; promote to env if operator wants runtime tuning)"** |
| `5` (max rows in card list) | `LowStockCard.tsx` `LOW_STOCK_LIST_CAP` | because **"operator UX preference — keep the card compact; a 5-spool list fits the dashboard hero without a scroll bar at the desktop breakpoint"** |

All previously-pinned literals from Stories 31.1 + 31.2 + 31.3 remain owned by their original files with their original contract pointers.

## Tasks / Subtasks

- [ ] **T1** (AC-1 + AC-2 + AC-3) — Author `LowStockCard.tsx`.
- [ ] **T2** (AC-4) — Author `apps/web/src/modules/landing/LandingPage.tsx`.
- [ ] **T3** (AC-5) — Append 12 keys × 2 locales = 24 entries.
- [ ] **T4** (AC-6) — Swap `/` route component + rewrite the index test.
- [ ] **T5** (AC-7) — Author Playwright specs + generate baselines.
- [ ] **T6** (AC-7 carry-over) — Audit existing specs for `page.goto("/")`; update intent or accept regen.
- [ ] **T7** (AC-8) — Author `LowStockCard.test.tsx`.
- [ ] **T8** (AC-9) — Run gates.
- [ ] **T9** (AC-10) — Verify grep invariants + i18n parity.
- [ ] **T10** (close-out) — Commit subject `feat(web): landing dashboard + low-stock card (Story 31.4, Init 19)`; ff-merge; push.

## Dev Agent Record

### Code-side gates (filled by dev-story execution)

- npm run lint: PASS (eslint + stylelint; 1 pre-existing react-version warning unchanged; mid-dev fix-up split `LOW_STOCK_THRESHOLD_G` + `selectLowStockRows` into sibling `LowStockCard.lib.ts` to satisfy `react-refresh/only-export-components` after initial run flagged a Fast-Refresh violation).
- npm run typecheck: PASS (`tsc -b` clean).
- npm run test (vitest narrow): `src/modules/spools` + `src/routes/index` → 3 files / 14 tests passed (6 format + 7 selectLowStockRows + 1 route).
- npm run test (vitest full): 101 files / 451 tests passed (baseline 444 + 7 new on LowStockCard selector logic).
- npm run test:visual (full): 364 passed / 24 skipped (baseline 356 + 8 new landing baselines; 0 regen on existing baselines — the anon-login-only test 1 change is a non-baseline assertion update only).

### Grep invariants (filled by dev-story execution)

- `apps/api/` byte-diff against `origin/main`: zero diff (Story 31.4 is FE-only).
- `apps/web/src/lib/api.ts` + `apps/web/src/lib/api-types.ts` byte-diff: zero diff.
- No `fetch(` literal under `apps/web/src/modules/spools/` or `apps/web/src/modules/landing/`: confirmed via grep.
- i18n parity: 12 keys × 2 locales = 24 entries added symmetrically (en.json + pl.json).
- `page.goto("/")` audit: 3 occurrences across 2 spec files. (a) `agents-info-dialog.spec.ts` (2 tests) scope screenshots to popup/dialog selectors — unaffected by landing-page change. (b) `anon-login-only.spec.ts` test 1 asserted `waitForURL(/login?next=%2Fcatalog/)` because the pre-31.4 `/` redirect chained through `/catalog` before AuthGate captured the next param. Updated to `waitForURL(/login?next=%2F/)` matching the new direct `/` capture; behavior change documented inline. The remaining tests in anon-login-only.spec.ts visit explicit `/catalog`, `/admin/users`, `/login`, `/register`, `/reset-password` — unaffected.

**In-flight refactor mid-dev:** initial LowStockCard implementation co-located `LOW_STOCK_THRESHOLD_G` + `selectLowStockRows` + `LowStockRow` interface in the component file. `eslint-plugin-react-refresh` flagged the mixed export shape as a Fast-Refresh hazard. Split into sibling `LowStockCard.lib.ts` (constants + pure selector); component file re-imports them. Same external behavior; cleaner refresh semantics.

### Review Findings (filled by code-review execution)

**Reviewer routing deviation:** native Codex CLI hung on MCP transport after a 120s bounded timeout — same failure mode as Stories 31.1 / 31.2 / 31.3. Per AGENTS.md § Autonomous development mode, Story 31.4 disclaims NFR-SECURITY adjacency (pure FE; no backend change; no auth boundary touched). Labeled fallback: Claude Sonnet 4.6 delegate via `feature-dev:code-reviewer` sub-agent (labeled honestly).

**Round-1 verdict:** APPROVED-WITH-NITS — 0 Critical, 2 Important, 0 Minor findings.

Findings resolution:

1. **[Important]** `LowStockCard.lib.ts:25` — threshold boundary semantics (`remaining_weight < LOW_STOCK_THRESHOLD_G` is strict less-than) undocumented and untested. Reviewer flagged the future-risk of an operator-visible miss when a spool degrades to exactly 200g. **Patched in fix-up commit:** (a) added an inline comment on the filter explaining the strict-`<` choice is intentional + flagging the coupling between comparator and test if the operator ever changes the semantic; (b) added a regression test case (`excludes a spool sitting exactly on the threshold (boundary is strict <)`) that asserts a spool at 200.0g is excluded and a spool at 199.9g is included. Test count: 8 (was 7).

2. **[Important]** `anon-login-only.spec.ts` test 1 — post-login redirect destination shifts from `/catalog` to `/` (the LandingPage). Reviewer flagged this as a deliberate UX shift that needs operator ratification rather than a code change. **Resolution:** the shift is already operator-sanctioned by the SCP § Success criteria L541 ("fresh `git pull` + visit to landing as an authenticated member shows the real low-stock spools card with the two spools at session start — `[[feedback_b5_demoable_signal]]`") — i.e., the SCP explicitly assigns the demoable value to the landing page, so post-login returning to `/` IS the intended UX, not a regression. The original `/` → `/catalog` redirect was a stop-gap conditioned on "second module ships" (verbatim from the pre-31.4 file comment); Story 31.4 ends that deferral. No code change needed.

Gates re-run post-patch: `npm run test src/modules/spools` 14 passed (8 LowStockCard + 6 format); `npm run typecheck` PASS; visual unaffected by lib-only change.

Triage: 0 decision-needed, 1 patched, 0 deferred, 1 ratified-as-intended (Important #2 — SCP § Success criteria already cover the UX shift). Status flipped review → done.

## Out of scope

- `SPOOLMAN_LOW_STOCK_THRESHOLD_G` runtime env slot — explicitly deferred to a future follow-up if operator wants runtime tuning. MVP-A ships a hardcoded module constant; the spec calls this out in AC-1.
- Final i18n parity grep sweep — Story 31.5.
- ops doc addendum — Story 31.5.
- Per-spool detail page navigation from the card — out of MVP-A scope (no per-spool detail page exists).
- Threshold customization UI — out of scope.
- Multi-instance Spoolman support — out of scope per SCP.
