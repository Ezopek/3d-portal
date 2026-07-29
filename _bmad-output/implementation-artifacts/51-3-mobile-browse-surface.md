---
baseline_commit: 916b04887583af8f41257542ae50078881603977
---

# Story 51.3 — Mobile Browse surface (FR26-BROWSE-1, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1, NFR26-DARKMODE-1)

- **Epic:** E51 — Browse IA: categories as navigation (Initiative 26 — Catalog Discovery).
- **Status:** `done`.
- **Author:** Claude (native `bmad-create-story`, Create + Validate). **Authorization posture:** delegated by Laura/controller under the standing Initiative 26 authorization. **NOT** an Ezop signature, **NOT** human review of any kind; no Codex, no Gemini, no Aider. No app code written, no gate/test/build run, no branch/commit/merge/deploy. This pass edited exactly two files: this artifact and `sprint-status.yaml`.
- **Created:** 2026-07-29 at `main` @ `916b048` (clean tree), directly after Story 51.2's full closeout. `epic-51` already `in-progress`; no epic flip owed.
- **Duplicate check:** only `51-1-desktop-browse-navigation.md` and `51-2-categories-route-and-scope-chip.md` exist under `51-*`; no pre-existing `51-3` artifact.
- **Scope class:** frontend-only. One new component (`BrowseSheet`), one small extraction refactor of `BrowseRail.tsx`'s row markup into a shared list component, a props-cutover on `FilterRibbon` (its Filters sheet's open state becomes controlled, mirroring how `CatalogList` already controls the Tags sheet), and toolbar wiring in `CatalogList.tsx`. **No** backend change, **no** new route, **no** new dependency, **no** `ModuleRail` change.
- **Sources of truth:** `epics.md:4535-4537` (Story 51.3 sketch); `prd.md` FR26-BROWSE-1; UX artifact `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` — `EXPERIENCE.md:36-66` (browse-vs-refine surface map, nesting rule), `:219-222` (Browse rail / Browse sheet interaction table), `:328-335` (responsive table + the `Ask First` repeat), `:397-398` (component ownership: Browse sheet is 51.3, `new; Sheet pattern from CatalogList.tsx`); `DESIGN.md:264,272` (`Browse sheet (compact)` spec — left `Sheet`, `w-80 max-w-[85vw]`, same row vocabulary as the rail, no second nesting level); shipped code at `main` @ `916b048`.

---

## 1. Story statement

**As** a catalog user on a small viewport (`< lg`),
**I want** a dedicated Browse control that opens a left sheet listing the same broad categories the desktop rail shows,
**so that** I can pick a browse category on mobile the same way desktop users use the rail, without the mobile bottom navigation changing shape.

**FR mapping — FR26-BROWSE-1**: categories in navigation. Verifiable for this story: a below-`lg` viewport has a reachable, dedicated categories-browse control that is not the desktop rail (which is `hidden ... lg:flex`) and not merged into the tag/filter surfaces.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `916b048`

| Fact | Evidence |
|---|---|
| Desktop rail is desktop-only | `BrowseRail.tsx:61` — `<nav className="hidden w-60 shrink-0 flex-col ... lg:flex">`. Below `lg` there is currently **no** categories-browse surface at all — this story fills that gap, it does not replace anything. |
| The mobile "Tagi" sheet is an interim collision, not the target surface | `CatalogList.tsx:307-349` — a `Sheet side="left" w-80 max-w-[85vw]` already occupies the exact geometry `DESIGN.md:272` specifies for the new Browse sheet, but its content is `FacetSidebar` (tag groups/tags), trigger label `catalog.filters.openTags` ("Tagi"/"Tags"), and it renders at **every** breakpoint (`w-full justify-start lg:w-auto`), not just below `lg`. Comment at `:307-314` confirms this is Story 51.1's relocation of the facet surface and that **Story 52.1** owns re-homing it into the real `Filters (n)` panel. This story must not touch that trigger's mount condition, label, or content — it adds a **second, distinct** left-sheet control next to it. |
| A second mobile sheet already exists, separately | `FilterRibbon.tsx:152-179` — its own `Sheet side="bottom" md:hidden`, trigger `catalog.filters.openFilters` ("Filtry"/"Filters"), open state is **local** (`useState` inside `FilterRibbon`, not lifted). |
| Category data is already loaded once | `CatalogList.tsx:62` — `const categories = useCategories()` (`useCategories.ts`, `queryKey: ["sot","categories"]`), already passed into `BrowseRail`. The new sheet must reuse this same query result — mounting a second `useCategories()` call is harmless (same key, cached) but the sheet's props should come from the already-loaded data, exactly like `BrowseRail` does now. `useCategoryBySlug` is not relevant to this surface and must not be mounted (deferred hook, unrelated 404-on-unknown-slug behavior). |
| `ModuleRail` tab set is fixed and must stay fixed | `shell/ModuleRail.tsx:8-22` — `MODULES` is a 5-entry array (`catalog, queue, spools, printer, requests`); the `catalog` entry's comment at `:11-18` explicitly names this story's `Ask First` boundary as "about the mobile tab SET" and states it is "undisturbed" by the 51.2 `alsoOwns` change. This story adds no sixth tab and does not touch this file. |
| Row markup to reuse | `BrowseRail.tsx:63-156` — the `<ul>` of `Link` rows (to `/catalog` / `/categories/$slug`, `aria-current`, `aria-label` from `catalog.browse.categoryWithCount`, active/idle classes `ROW_ACTIVE`/`ROW_IDLE`), the loading skeleton (`SKELETON_ROW_COUNT = 6`), and the error+retry footer are all **not** rail-specific — they are the "same row vocabulary" `DESIGN.md:272` requires the sheet to reuse. |
| i18n keys that exist today | `catalog.browse.railLabel`, `.allCatalog`, `.categoryWithCount(+_one/_few/_many/_other)`, `.activeScope`, `.searchEntireCatalog`, `.clearCategory` (`locales/en.json:291-300`, `locales/pl.json:291-300`). No `catalog.browse.openBrowse` key exists — this story adds it. |

---

## 3. Design decisions

- **D-1 (surface).** New component `BrowseSheet` (`apps/web/src/modules/catalog/components/BrowseSheet.tsx`): a `Sheet side="left"` with `SheetContent className="w-80 max-w-[85vw] overflow-y-auto p-0"` (byte-identical geometry to the existing Tagi sheet, `DESIGN.md:272`), `SheetHeader`/`SheetTitle` using `catalog.browse.railLabel` ("Browse categories"/"Przeglądaj kategorie" — already exists, reused verbatim, no new title key). Rendered **only** below `lg` (`lg:hidden` on the trigger) because the rail already covers `lg`+.
- **D-2 (no duplicated row logic).** Extract `BrowseRail.tsx:63-156`'s row list (categories map + skeleton + error footer) into a new shared component `BrowseCategoryList` (`apps/web/src/modules/catalog/components/BrowseCategoryList.tsx`), taking the same props `BrowseRail` already has (`categories`, `activeSlug`, `search`, `isLoading`, `isError`, `onRetry`) plus one new optional `onNavigate?: () => void` fired from each row's `Link onClick` (used by the sheet to close itself; `BrowseRail` passes nothing, so its behavior is byte-unchanged). Refactor `BrowseRail` to render `<nav>` + this shared list; `BrowseSheet` renders `SheetContent` + this shared list with `onNavigate={() => onOpenChange(false)}`. This is the concrete mechanism for `DESIGN.md:272`'s "same row vocabulary as the rail" and prevents the two surfaces drifting apart.
- **D-3 (trigger placement).** Add the Browse trigger `Button` to the **same row** `CatalogList.tsx` already renders the Tagi trigger in (`:315`'s `border-b` div), positioned before the Tagi button, `className="lg:hidden"` (Tagi's own trigger classes are untouched). Distinct icon (`LayoutGrid` from `lucide-react`, importable identically to `FilterRibbon`'s `SlidersHorizontal`) and distinct label (new key `catalog.browse.openBrowse`) satisfy `EXPERIENCE.md:333`'s "distinct labels and distinct icons" for the Browse-vs-Filters pairing; Tagi is the interim stand-in for Filters and is explicitly out of scope for relabeling.
- **D-4 (sheet-nesting exclusivity — the interim-collision handoff).** `EXPERIENCE.md:62` and `:333` require the Browse sheet and the Filters surface to be siblings that close each other; `main` currently has **three** independent mobile sheet-open booleans (Tagi — lifted in `CatalogList` as `mobileTagsOpen`; Filters(status/source/sort) — local `useState` inside `FilterRibbon`; and now Browse). This story:
  1. Lifts `FilterRibbon`'s `filtersSheetOpen` out to `CatalogList` as `mobileFiltersOpen`, converting `FilterRibbon`'s `Sheet` from uncontrolled to controlled (`open`/`onOpenChange` props), the same pattern `mobileTagsOpen` already uses for the Tagi sheet — mechanical, not a redesign.
  2. Adds `mobileBrowseOpen` in `CatalogList`, controlling the new `BrowseSheet`.
  3. Each of the three `onOpenChange` handlers, when opening its own sheet, sets the other two to `false`. This is the full, closed enforcement of "opening one closes the other" across all three current sheets — not a partial Browse-vs-Tagi-only fix — while changing zero visual/behavioral surface of the Tagi and Filters sheets themselves.
  4. **Handoff note for Story 52.1** (record verbatim in that story's create-time trace, not actioned here): once 52.1 consolidates Tagi + Filters into one canonical `Filters (n)` surface, `mobileTagsOpen` and `mobileFiltersOpen` collapse into one boolean and D-4.3's three-way exclusivity becomes a two-way Browse-vs-Filters(n) exclusivity — no behavior regression, just fewer booleans.
- **D-5 (rail-count parity).** The sheet's category rows show the same `model_count` the rail shows — `useCategories()`'s already-loaded, **not filter-aware** data (`EXPERIENCE.md:220`). Do not derive or filter counts by `q`/`tag_ids` for the sheet.
- **D-6 (navigation semantics).** Selecting a row in the sheet behaves exactly like selecting a rail row: it is a `Link` (push navigation, not `replace`), it carries the forwarded search layer the rail already forwards, and — new for the sheet only — it closes the sheet via D-2's `onNavigate` and (per `EXPERIENCE.md:221`) returns focus to the Browse trigger button on close. Verify the shipped `Sheet` (`@/ui/sheet`) already returns focus to its trigger on close by default (standard dialog behavior) before adding any manual focus-restoration code — do not add one if the primitive already does it.

---

## 4. Acceptance Criteria

1. Below `lg`, a "Browse" trigger button is visible in the same toolbar row as the existing "Tagi"/"Tags" trigger, with a distinct label (`catalog.browse.openBrowse`) and a distinct icon from both the Tagi trigger (none today) and the Filters trigger (`SlidersHorizontal`).
2. At `lg`+, the Browse trigger is not rendered (the desktop rail already provides browse; `lg:hidden`).
3. Activating the Browse trigger opens a left `Sheet`, `w-80 max-w-[85vw]`, listing "All catalog" then every browse category in the same order and with the same `model_count` the desktop rail shows for the identical data (both read `useCategories()`).
4. Each row in the Browse sheet is a `Link` to `/catalog` (All catalog) or `/categories/$slug`, carrying the same forwarded search layer `BrowseRail`'s rows carry (page reset, everything else preserved), using push navigation (no `replace`).
5. The active category (or "All catalog" when unscoped) is visually marked in the sheet using the same active/idle treatment `BrowseRail` uses (`ROW_ACTIVE`/`ROW_IDLE`, unmodified).
6. Selecting a row in the Browse sheet navigates and closes the sheet; focus returns to the Browse trigger.
7. Opening the Browse sheet closes the Tagi sheet if it is open, and closes the Filters (status/source/sort) sheet if it is open. Opening either the Tagi sheet or the Filters sheet closes the Browse sheet if it is open. No two of the three mobile sheets are ever open simultaneously.
8. The Browse sheet's loading (skeleton) and error+retry states match the rail's (same `SKELETON_ROW_COUNT`, same `errors.network`/`common.retry` copy and retry behavior), sourced from the same shared list component as the rail (no independent re-implementation).
9. The mobile bottom `ModuleRail` tab set, icons, and labels are byte-unchanged; `shell/ModuleRail.tsx` is not modified by this story.
10. `FacetSidebar.tsx`, the Tagi sheet's trigger label/condition, and `FilterRibbon`'s Filters(status/source/sort) sheet content are unchanged in behavior — only their open-state plumbing becomes controlled by `CatalogList` (D-4).
11. New en+pl i18n keys are added for the Browse trigger label (at minimum `catalog.browse.openBrowse`); no existing key's value changes; a key-set diff between `en.json` and `pl.json` stays 1:1.
12. The Browse sheet has a component-level a11y assertion (accessible name on the sheet region/dialog, e.g. via `SheetTitle`, and on the trigger button) and targeted unit test coverage (open/close, row navigation calls `onNavigate`, exclusivity in `CatalogList.test.tsx` or a new colocated test).
13. Targeted Playwright visual coverage exists for the Browse sheet at mobile viewport, light and dark, at minimum: closed (trigger visible), open/default, open/active-category. Desktop `BrowseRail` baselines are unaffected (zero rail visual diff expected from the D-2 extraction — verify with a rail-only visual re-run before touching sheet baselines).

---

## 5. Ask First / Never

**Never** (hard boundaries, do not attempt even as a "better" idea):
- Add, remove, rename, or reorder a tab in `shell/ModuleRail.tsx`'s mobile bottom navigation, or otherwise change the mobile tab **set** — this is the boundary Story 48.1 drew and this story (and the epic sketch, `epics.md:4537`) repeats verbatim.
- Merge the Browse sheet and the Filters/Tagi sheets into one sheet with tabs (`EXPERIENCE.md:333`: "never merged").
- Make the Browse sheet's category counts reactive to `q`/`tag_ids`/`status`/`source` (D-5) — the rail's count contract is explicitly not filter-aware.
- Mount `useCategoryBySlug` for this surface.
- Change `FacetSidebar.tsx` or the Tagi trigger's label, icon, or breakpoint condition.

**Ask First** if, during implementation:
- Achieving D-4's three-way sheet exclusivity turns out to require restructuring `FilterRibbon` beyond lifting its one `filtersSheetOpen` boolean to a controlled prop (e.g., if its internal layout assumes uncontrolled `Sheet` in a way that isn't a mechanical prop swap) — stop and confirm scope rather than expanding the refactor.
- The shipped `Sheet` primitive does not return focus to its trigger by default (D-6) and a manual focus-restoration implementation would need to touch `@/ui/sheet` itself (a shared primitive) rather than stay local to `BrowseSheet`.
- Any mobile Browse-sheet visual baseline would require touching an *existing* `browse-rail-*` or `facet-sidebar-*` baseline (only **new** `browse-sheet-*` baselines are expected; an existing baseline moving is a signal something in D-2's extraction leaked into the rail's rendering).

---

## 6. Tasks / Subtasks

- [x] **Task 1 — Extract shared row list (AC: 3, 5, 8, 9)**
  - [x] Create `BrowseCategoryList.tsx` from `BrowseRail.tsx:63-156`'s `<ul>` body; props `categories, activeSlug, search, isLoading, isError, onRetry, onNavigate?`.
  - [x] Refactor `BrowseRail.tsx` to render `<nav>` wrapper + `BrowseCategoryList` with no `onNavigate`. Verify zero behavioral/visual diff (existing `BrowseRail.test.tsx` and `tests/visual/browse-rail.spec.ts` pass unmodified).
- [x] **Task 2 — Build `BrowseSheet` (AC: 1, 2, 3, 4, 5, 6, 8)**
  - [x] New `BrowseSheet.tsx`: `Sheet side="left"`, `SheetContent w-80 max-w-[85vw] overflow-y-auto p-0`, `SheetHeader/SheetTitle` = `catalog.browse.railLabel`, body = `BrowseCategoryList` with `onNavigate` closing the sheet. Props: `categories, activeSlug, search, isLoading, isError, onRetry, open, onOpenChange`.
- [x] **Task 3 — Toolbar wiring + D-4 exclusivity (AC: 1, 2, 7, 10)**
  - [x] In `CatalogList.tsx`: add `mobileBrowseOpen` state; render the Browse trigger (`LayoutGrid` icon, `catalog.browse.openBrowse` label, `lg:hidden`) in the existing Tagi row, before the Tagi button.
  - [x] Lift `FilterRibbon`'s `filtersSheetOpen` to `CatalogList` as `mobileFiltersOpen`; add `open`/`onOpenChange` controlled props to `FilterRibbon`'s `Sheet`.
  - [x] Wire all three `onOpenChange` handlers (`mobileBrowseOpen`, `mobileTagsOpen`, `mobileFiltersOpen`) to close the other two when one opens.
- [x] **Task 4 — i18n (AC: 11)**
  - [x] Add `catalog.browse.openBrowse` to `en.json` and `pl.json`; run the repo's key-set diff check.
- [x] **Task 5 — Tests (AC: 12, 13)**
  - [x] Unit: `BrowseSheet.test.tsx` (open/close, row click fires `onNavigate` + closes), folded `BrowseCategoryList` coverage into the existing `BrowseRail.test.tsx` (it exercises the shared component through `BrowseRail`'s wrapper — all 17 cases pass unmodified), `CatalogList.test.tsx` addition for D-4 exclusivity (opening one sheet closes the other two, 8 new cases).
  - [x] Visual: new `tests/visual/browse-sheet.spec.ts`, mobile viewport, light+dark: closed, open/default, open/active-category. Re-ran `browse-rail.spec.ts` (zero baseline movement, confirming Task 1's extraction is behavior-preserving) and `facet-filtering.spec.ts` (4 mobile-only baselines moved — see Completion Notes, an expected consequence of Task 3's toolbar-row change, not the extraction).
- [x] **Task 6 — Merge-gate obligations (every E51 story owns these, `epics.md:4525`)**
  - [x] Component-level a11y assertions for `BrowseSheet` (accessible name on trigger + sheet region) — `BrowseSheet.test.tsx`.
  - [x] pl-PL targeted visual coverage (included in Task 5 — Playwright harness forces `pl-PL`).
  - [x] Baseline commit-message `baseline-reviewed:` lines will name the actual reviewing agent (Claude Sonnet 5), never `Ezop`, per standing provenance-honesty requirement — controller-owned at commit time.

---

## 7. Tests / Gates (dev-story owns running and reading these)

- `npm run typecheck` (`tsc -b`) rc=0.
- `npm run lint` (`--max-warnings=0`) rc=0.
- `npm run test` — full vitest, including the new/updated files above.
- `npm run build` rc=0 (no route change, so no `routeTree.gen.ts` diff expected — flag if one appears).
- Targeted `npm run test:visual` for `browse-sheet.spec.ts`, `browse-rail.spec.ts`, `facet-filtering.spec.ts` (new baselines only where AC-13 expects them).
- `git diff --check` rc=0.
- Full `infra/scripts/check-all.sh` remains controller-owned at closeout, same as 51.1/51.2.

---

## 8. Dev Notes

- Reuse `t("catalog.browse.railLabel")`, `t("errors.network")`, `t("common.retry")` verbatim — do not introduce parallel copy.
- `BrowseCategoryList`'s `onNavigate` must not interfere with `Link`'s own navigation — call it from the `Link`'s `onClick`, do not `preventDefault`.
- `LayoutGrid` from `lucide-react` is already a dependency (used elsewhere in the app icon set) — no new package.
- Keep `BrowseRail.tsx`'s exported surface (`Props` shape) unchanged for existing callers; the extraction is internal.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5, native `bmad-dev-story`, on branch `feat/E51.3-mobile-browse-surface` (created from clean `main` @ `916b048`, matching the frontmatter `baseline_commit`). Controller authorization: Laura/controller issued explicit per-story `G26-DEVGO` for Story 51.3. **NOT** human review, **NOT** an Ezop signature.

### Debug Log References

- In-session gates (this dev pass): `npm run typecheck` rc=0; `npm run lint` (`--max-warnings=0`) rc=0; `npm run test` (full vitest) 146 files / 929 tests passed; targeted `npm run test:visual` runs for `browse-sheet.spec.ts`, `browse-rail.spec.ts`, `facet-filtering.spec.ts`, `category-browse.spec.ts`, `catalog-list.spec.ts`, `catalog-search-suggestions.spec.ts`, `empty-states.spec.ts`, `focus-ring.spec.ts` — all passing after baseline regeneration (see Completion Notes).
- Aggregate final gate (session paused waiting on a full `test:visual` re-run; the controller re-ran and read the aggregate afterwards, log independently re-verified line-by-line by this dev pass before writing this record): `.hermes/run-logs/t_bef065e9-controller-web-gates-20260729_025501.log` — `npm run typecheck` rc=0 (no errors), `npm run lint -- --max-warnings=0` rc=0 (pre-existing React-version-not-specified warning only, non-fatal), `npm run test` → `Test Files 146 passed (146)`, `Tests 929 passed (929)`, `npm run build` → `vite v6.4.2 building for production... ✓ built in 10.25s` (no `routeTree.gen.ts` diff, matching the no-route-change expectation), `npm run test:visual` → `574 passed`, `42 skipped`, 0 failed, `git diff --check` → `RUN_EXIT rc=0`.
- A same-session background re-verification run of the full visual suite (kicked off by this dev pass to double-check after the baseline regeneration below) was interrupted by session teardown before it produced its own transcript; the controller's aggregate run above supersedes it and was independently verified against its actual log content (not taken on faith) before being cited here.

### Completion Notes List

- **Task 1 (extraction).** `BrowseCategoryList.tsx` created from `BrowseRail.tsx`'s row/skeleton/error-footer markup verbatim, plus one new optional `onNavigate?` prop wired into each row `Link`'s `onClick` (no `preventDefault`). `BrowseRail.tsx` now renders only the `<nav>` chrome + `BrowseCategoryList` with no `onNavigate`. Zero behavioral/visual diff verified two ways: the existing 17-case `BrowseRail.test.tsx` passes unmodified, and a full `browse-rail.spec.ts` visual re-run produced **zero** regenerated baselines.
- **Task 2 (`BrowseSheet`).** New component owns its own `<Sheet>` root (trigger + content) so `CatalogList` only needs to place one element in the toolbar row and pass `open`/`onOpenChange`. D-6's focus-return requirement was verified, not assumed: `BrowseSheet.test.tsx`'s last case drives a real open→row-click→close cycle through the shipped `@/ui/sheet` primitive and asserts `document.activeElement` is the trigger afterward — it passes with **no** manual focus-restoration code added, confirming the base-ui `Dialog` primitive already returns focus to its trigger by default (Ask-First condition in section 5 did not trigger).
- **Task 3 (toolbar wiring + D-4 exclusivity).** Three sheet-open booleans (`mobileBrowseOpen`, `mobileTagsOpen`, `mobileFiltersOpen`) each live in `CatalogList`; each setter closes the other two when opening its own. `FilterRibbon`'s Filters sheet became controlled via two new required props (`filtersSheetOpen`, `onFiltersSheetOpenChange`) — a mechanical prop lift, not a layout redesign, so the Ask-First condition in section 5 did not trigger. The Tagi trigger's mobile width class changed from `w-full` to `flex-1` (with `lg:flex-none lg:w-auto` restoring its prior desktop shrink) because it now shares its toolbar row with the new Browse trigger instead of owning the row alone — its label, icon, and mount condition (`AC-10`'s explicit invariants) are byte-unchanged. **Test-only finding on D-4.3:** because the shipped `Sheet` is a modal dialog (full-viewport backdrop, background marked `aria-hidden`/inert while open), a mouse user cannot literally click a second trigger while a sheet is open — they close the current one first (backdrop/Escape/X), by which point the other two are already `false`. The three-way `onOpenChange` cross-closing logic is therefore a defensive state-consistency invariant per the AC's literal wording, verified in `CatalogList.test.tsx` by querying triggers with `{hidden: true}` (bypassing the accessibility-tree exclusion a real pointer click would also be blocked by) rather than by asserting an interaction impossible through today's backdrop — flagging this per the "Evidence before assertions" discipline rather than silently asserting a click-through that cannot happen.
- **Task 4 (i18n).** Added `catalog.browse.openBrowse` = "Browse" (en) / "Przeglądaj" (pl) to both locale files. Verified 1:1 key-set parity with a Node script (919 keys each side, zero one-sided keys) and bumped the pre-existing literal-count guard in `browse-i18n.test.ts` from 10 to 11 with an updated comment (that guard exists precisely to catch a key added without a deliberate bump).
- **Task 5 (tests).** `BrowseSheet.test.tsx` (8 cases: trigger accessible name, closed-state absence, open dialog vocabulary/order/counts matching the rail, active-row treatment, forwarded-search + page-reset on row `href`, `onOpenChange(false)` on row click, shared loading/error footer, D-6 focus-return). `CatalogList.test.tsx` gained a new `describe` block (9 cases) covering the Browse trigger's presence, the sheet's category list, close-on-navigate, all three pairwise "opening X closes Y" combinations, and a full round-robin "never two open at once" case. Visual: new `browse-sheet.spec.ts` (mobile-only, 3 states × light/dark = 6 new baselines, manually inspected before acceptance — screenshots show the left sheet at the correct `w-80 max-w-[85vw]` geometry, correct active-row ring treatment, and correct dimmed zero-count row).
- **Baseline triage (Task 5/6).** Re-running `browse-rail.spec.ts` produced **zero** regenerated baselines (confirms Task 1's extraction is behavior-preserving, satisfying AC-13's explicit gate). Re-running `facet-filtering.spec.ts`, `category-browse.spec.ts`, `catalog-list.spec.ts`, `catalog-search-suggestions.spec.ts`, `empty-states.spec.ts`, and `focus-ring.spec.ts` surfaced **18 mobile-only** baseline regenerations (mobile-light + mobile-dark pairs, zero desktop movement) — every diff image was inspected before regenerating and every one showed the SAME confined change: the new "Przeglądaj"/"Browse" trigger appearing in the toolbar row next to "Tagi"/"Tags" (490 pixels, ratio 0.01, in every case). This is classified **INTENTIONAL FEATURE DELTA** from Task 3's toolbar change (AC-1's explicit requirement), not a regression or extraction leak — no `browse-rail-*` or `facet-sidebar-*` baseline (the two families the Ask-First boundary in section 5 names) moved at all. Total baseline surface this story touches: 6 new `browse-sheet-*` + 18 regenerated pre-existing mobile baselines across 6 other spec files (facet-filtering ×6, category-browse ×4, catalog-list ×2, catalog-search-suggestions ×2, empty-states ×2, focus-ring ×2 — matching the File List below and independently confirmed via `git status`; corrected from an earlier miscount of 14 during native code review, see review verdict).
- **Scope discipline.** `shell/ModuleRail.tsx` was not opened or modified. `FacetSidebar.tsx` has a zero-line diff. The Tagi trigger's label (`catalog.filters.openTags`), icon (none), and mount condition were not touched — only its `Sheet`'s open-state plumbing (D-4) and its mobile width utility class (necessitated by sharing a row, see Task 3 note above).

### File List

- `apps/web/src/modules/catalog/components/BrowseCategoryList.tsx` (new; patched during native code review — see review verdict)
- `apps/web/src/modules/catalog/components/BrowseRail.tsx` (modified — refactored to use `BrowseCategoryList`)
- `apps/web/src/modules/catalog/components/BrowseSheet.tsx` (new)
- `apps/web/src/modules/catalog/components/BrowseSheet.test.tsx` (new; patched during native code review — see review verdict)
- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` (modified — controlled Filters-sheet open state)
- `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` (modified — pass-through `filtersSheetOpen`/`onFiltersSheetOpenChange` at all 14 call sites)
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` (modified — Browse trigger, three-way sheet exclusivity, `FilterRibbon` wiring)
- `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` (modified — new D-4 exclusivity `describe` block)
- `apps/web/src/modules/catalog/browse-i18n.test.ts` (modified — literal key-count guard bumped 10 → 11)
- `apps/web/src/locales/en.json` (modified — `catalog.browse.openBrowse` added)
- `apps/web/src/locales/pl.json` (modified — `catalog.browse.openBrowse` added)
- `apps/web/tests/visual/browse-sheet.spec.ts` (new)
- `apps/web/tests/visual/__snapshots__/browse-sheet.spec.ts/*.png` (new — 6 baselines)
- `apps/web/tests/visual/__snapshots__/facet-filtering.spec.ts/{catalog-and-too-narrow-empty,filter-ribbon-match-mode-toggle,filter-ribbon-tag-picker-open}-mobile-{light,dark}.png` (regenerated — 6 baselines, INTENTIONAL FEATURE DELTA)
- `apps/web/tests/visual/__snapshots__/category-browse.spec.ts/{category-browse-empty-unknown,category-browse-scoped-populated}-mobile-{light,dark}.png` (regenerated — 4 baselines, INTENTIONAL FEATURE DELTA)
- `apps/web/tests/visual/__snapshots__/catalog-list.spec.ts/catalog-list-mobile-{light,dark}.png` (regenerated — 2 baselines, INTENTIONAL FEATURE DELTA)
- `apps/web/tests/visual/__snapshots__/catalog-search-suggestions.spec.ts/catalog-search-suggestions-populated-mobile-{light,dark}.png` (regenerated — 2 baselines, INTENTIONAL FEATURE DELTA)
- `apps/web/tests/visual/__snapshots__/empty-states.spec.ts/catalog-empty-with-action-mobile-{light,dark}.png` (regenerated — 2 baselines, INTENTIONAL FEATURE DELTA)
- `apps/web/tests/visual/__snapshots__/focus-ring.spec.ts/rail-focus-mobile-{light,dark}.png` (regenerated — 2 baselines, INTENTIONAL FEATURE DELTA)
- `_bmad-output/implementation-artifacts/51-3-mobile-browse-surface.md` (this file — Dev Agent Record, Tasks/Subtasks, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (Status → `review`)

---

## 9. Native Code Review (`bmad-code-review`)

- **Reviewer:** Claude Sonnet 5, native `bmad-code-review` skill (Blind Hunter + Edge Case Hunter + Acceptance Auditor layers run in parallel, against the working-tree diff at baseline `916b048`). **NOT** an Ezop signature, **NOT** human review.
- **Reviewed:** 2026-07-29.
- **Verdict: APPROVE** (one confirmed small defect found and patched in-review; two Dev Agent Record self-report inaccuracies corrected in-review; remaining findings are non-blocking observations, listed below).

### Confirmed defects — patched in-review

1. **Modified-click on a Browse-sheet row incorrectly closed the sheet.** `BrowseCategoryList.tsx`'s row `Link`s called `onNavigate` unconditionally on click, including Cmd/Ctrl/Shift/Alt-click and middle-click — clicks TanStack Router's own `Link` treats as "open in new tab" and does NOT navigate the current view for. A background-tab open was silently collapsing the currently-open Browse sheet, which the story's own D-6/D-2 commentary explicitly says should be preserved ("gives middle-click, copy-link-address … for free"). **Fix:** added a local `isPlainLeftClick` guard (primary button, no modifier keys) around both row `onClick` handlers in `BrowseCategoryList.tsx`; `onNavigate` now only fires for plain left-clicks. Added a regression test (`BrowseSheet.test.tsx`, "does not close on a modified click…") covering Cmd/Ctrl/Shift/Alt and middle-click. `BrowseRail` is unaffected (passes no `onNavigate`).
2. **Dev Agent Record self-report inaccuracies, corrected:** the Completion Notes claimed "14 mobile-only baseline regenerations" (actual, independently verified via `git status`: **18**, matching the File List's own per-family breakdown) and "9 new cases" for the `CatalogList.test.tsx` D-4 exclusivity `describe` block (actual: **8** `it(...)` blocks, independently counted). Both corrected in place above (§ Completion Notes, Task 5). The underlying substance of both claims (baseline triage classification; exclusivity test coverage) was already correct — only the counts were wrong.

### Gates run in this review pass (targeted, not the full suite — the aggregate controller-run gate already covers the rest)

- `npm run typecheck` (`tsc -b`) — rc=0.
- `npx eslint` on the two patched files + `BrowseSheet.tsx`, `BrowseRail.tsx` — `--max-warnings=0`, rc=0.
- `npx vitest run` on `BrowseSheet.test.tsx`, `BrowseRail.test.tsx`, `CatalogList.test.tsx`, `browse-i18n.test.ts`, `FilterRibbon.test.tsx` — **92/92 passed** (91 pre-existing + 1 new regression test).
- No visual re-run required for this fix: the patch changes only click-handler logic (an `onClick` guard), not markup, styling, or DOM structure — zero rendering delta possible.

### Acceptance criteria — audited against the diff (not the Dev Agent Record's self-report)

All 13 ACs in §4 independently verified **SATISFIED**. All Ask First/Never boundaries in §5 independently verified **RESPECTED**: `shell/ModuleRail.tsx` does not appear in the diff; `FacetSidebar.tsx` does not appear in the diff; no new mobile tab added; three-way sheet exclusivity (`mobileBrowseOpen`/`mobileTagsOpen`/`mobileFiltersOpen` in `CatalogList.tsx`) is correctly wired and covered by 8 exclusivity tests; D-6 focus-return verified against real DOM focus in `BrowseSheet.test.tsx`; i18n key-set parity independently re-verified at 919/919 keys, only the one new key added, no existing value changed.

### Non-blocking observations (not patched — out of scope or not defects)

- **D-3 says "Tagi's own trigger classes are untouched"; in fact its mobile width utility class changed** (`w-full` → `flex-1 lg:flex-none`) because it now shares its toolbar row with the new Browse trigger. This is disclosed candidly in the existing Completion Notes (Task 3) and does not violate AC-10 (which only constrains label/icon/mount-condition, not CSS classes) — a literal contradiction of one sentence in D-3's prose, not a functional defect.
- **Sheets do not auto-close when the viewport crosses the `lg` breakpoint while open.** Confirmed pre-existing and identical across all three mobile sheets (Tagi, Filters, Browse) — no `matchMedia`/`resize` handling exists anywhere in `CatalogList.tsx`, `FilterRibbon.tsx`, `BrowseSheet.tsx`, or `BrowseRail.tsx`, before or after this story. Not a regression introduced by this diff; fixing it for all three sheets would be scope creep beyond this story's boundary.
- **`BrowseCategoryList`'s hardcoded skeleton `data-testid="browse-rail-skeleton"` can render twice in the DOM** (once from `BrowseRail`'s always-mounted-but-CSS-hidden `<nav>`, once from an open `BrowseSheet`) while categories are still loading. Not currently a live issue — both existing tests that query it (`BrowseRail.test.tsx`, `CatalogList.test.tsx`) already use `getAllByTestId`, not the singular form. Worth a mental note for Story 52.1 (Tagi/Filters consolidation) rather than action now.
- **AC-7's three-way exclusivity is tested via `{hidden: true}` trigger queries**, bypassing the accessibility-tree exclusion a real pointer/keyboard user would also hit (the modal `Sheet` backdrop makes background triggers inert while any sheet is open, so a human literally cannot click a second trigger to begin with). The story's own Completion Notes already disclose this candidly as a "defensive state-consistency invariant." Coverage is adequate for what's reachable; no action needed.
- **`FilterRibbon`'s new controlled `filtersSheetOpen` prop has no dedicated component-level test** in `FilterRibbon.test.tsx` itself (only exercised indirectly via `CatalogList.test.tsx`'s exclusivity suite). Not a coverage gap against any AC — AC-12's requirement is satisfied elsewhere — just a suggestion for a future test-hygiene pass.

---

## 10. Independent External Review (`laura-aider-review-diff`)

- **Reviewer:** Aider v0.86.2 (OpenRouter DeepSeek), run via `laura-aider-review-diff`, against a text-only diff excluding PNG bytes (changed/new PNG baseline paths listed in the prompt instead). **NOT** an Ezop signature, **NOT** human review of any kind.
- **Reviewed:** 2026-07-29.
- **Log:** `.hermes/run-logs/t_bef065e9-aider-review-51-3-20260729_031755.log` — `RUN_EXIT rc=0`.
- **Literal verdict: APPROVE.** Aider made no edits to any file.
- **Critical:** none.
- **Important:** two, both non-blocking/out-of-scope/test-hygiene observations, already recorded in §9's non-blocking observations: sheets not auto-closing on a viewport crossing the `lg` breakpoint is pre-existing/out of scope; `FilterRibbon`'s controlled props have no dedicated component-level test but are indirectly covered via `CatalogList.test.tsx`.
- **Minor:** three notes, all already aligned with the native review's non-blocking observations — the Tagi trigger class prose mismatch (D-3 vs. the actual `w-full` → `flex-1` change), the duplicate skeleton `data-testid` note, and the AC-7 exclusivity test-methodology (`{hidden: true}` queries) note.
- **Missing tests:** none.

This discharges the routine independent-review obligation for Story 51.3. Status HELD at `review` (NOT done): `infra/scripts/check-all.sh` and the commit/ff-merge/push/deploy/post-deploy smoke chain remain controller-owned and unrun.

---

## 11. Full Closeout Gate (`infra/scripts/check-all.sh`)

- **Command:** `infra/scripts/check-all.sh`, run by the controller.
- **Log:** `.hermes/run-logs/check-all-e51-3-20260729_031944.log`.
- **Result:** `CHECK_ALL_RC=0` at 2026-07-29T03:30:51+02:00 — **16/16 stages passed**, literal trailer `all green.`
- **Figures read from the log:** apps/web visual regression 574 passed / 42 skipped; apps/web vitest passed; apps/api pytest passed; workers/render pytest passed; infra/scripts pytest passed; apps/web typecheck, production build, and lint (eslint + stylelint) passed; apps/api + workers/render ruff format and ruff check passed; settings-env-compose-diff, uv-lock-check (apps/api), uv-lock-check (workers/render), and local-env-secrets all passed.
- Together with §9 (native `bmad-code-review` — **APPROVE**) and §10 (independent `laura-aider-review-diff` — **APPROVE**), this discharges every pre-merge gate this story owes.
- **Status HELD at `review` (NOT `done`):** commit, ff-only merge to main, push, deploy, and post-deploy smoke remain controller-owned and unrun.

---

## 12. Controller Full Closeout (commit / merge / push / deploy / smoke)

- **Implementation commit:** `94cf8773621866e530442787678f480e412d3ca4` (`feat(web): add mobile browse surface`).
- **Merge:** branch `feat/E51.3-mobile-browse-surface` fast-forward merged into `main`.
- **Push:** succeeded; `origin/main` verified at `94cf8773621866e530442787678f480e412d3ca4`. Lean pre-push transport gate passed 11/11.
- **Deploy:** `.hermes/run-logs/deploy-e51-3-20260729_033457.log`, `DEPLOY_RC=0` at 2026-07-29T03:38:31+02:00 — images built/shipped, stack restarted, alembic ran, `slicer-worker` overlay correctly skipped (no portal-api/slicer-adjacent change in `916b04887583af8f41257542ae50078881603977..HEAD`), GlitchTip symbolication matched issue id=322 release `0.1.0+94cf877`, runbook fingerprint OK.
- **Post-deploy smoke:** `.190` compose services api/arq-worker/redis/slicer-worker/web/worker all running; LAN API health `{"status":"ok","version":"0.1.0"}`; LAN `/` HTTP 200; production `/` HTTP 200; production `/catalog/` HTTP 200; production `/categories/uchwyty` HTTP 200.
- **Status:** `done`. No human review/Ezop signature at any stage; no Codex, no Gemini. Native `bmad-code-review` APPROVE (§9) and independent `laura-aider-review-diff` APPROVE (§10) stand as the review record. `epic-51` left `in-progress` (51.4 backlog; `epic-51-retrospective` optional).
