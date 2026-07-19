---
title: 'Story 44.3 — CatalogList facet states'
type: 'feature'
created: '2026-07-20'
status: 'done'
baseline_revision: '8c5f345ff34c595f4b08b163f97ab62a557779e3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-44-context.md'
  - '{project-root}/docs/design/HANDOFF-tagi-fasetowe.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `CatalogList` still browses via the legacy category tree (`useCategoriesTree` / `category_id` / `CategoryTreeSidebar`) and never mounts the facet browse surfaces built in 44.1/44.2. `FacetSidebar` is unmounted, the `untagged` filter is not wired into the models query, and an AND-too-narrow empty result offers only "Clear filters" — not the "Switch to OR" recovery the facet UX (HANDOFF mockup 08D) requires.

**Approach:** Replace the category sidebar with `FacetSidebar` sourced from `useTagGroups()`, wire `tag_ids` / `tag_match` / `untagged` URL state into the sidebar and the models query, drop the `category_id` URL param and category-tree consumption (leaving the E47-deferred hook/types intact), and give the empty result a two-action recovery (Switch to OR + Clear filters). Purely frontend — the backend already accepts `tag_ids` / `tag_match` / `untagged` (E42) and `useTagGroups` / URL helpers exist (E43).

## Boundaries & Constraints

**Always:** Token-only styling, zero color literals (ESLint/Stylelint ban). Route all network through existing `api()`-backed hooks (`useTagGroups`, `useModels`, `useTags`). Preserve the E44.2 three-layer invariant that a non-default `tag_match` only survives with ≥2 `tag_ids` — rely on `validateSearch` normalization (runs on every navigation) to drop a stranded `tag_match` when tag toggling drops below 2. `untagged=true` OR-unions with the tag predicate at the backend (a model is never both), so treat the sidebar untagged checkbox as an independent toggle, not mutually exclusive with tags. Every navigation that changes a filter resets `page`. i18n keys added to both `en.json` and `pl.json` (identical key set).

**Block If:** The backend `GET /api/tag-groups` shape or the `GET /api/models` `untagged` / `tag_match` params are found absent or changed from the E42/E43 contract — do not invent an endpoint or a param; HALT.

**Never:** Do NOT delete the `useCategoriesTree` hook or the `CategoryNode` / `CategoryTree` types — their removal is E47 (story 47.4), gated on the last consumer gone. Do NOT touch the `FilterRibbon` AND/OR toggle contract (44.2 frozen) or add untagged chips to the ribbon. Do NOT add a new backend endpoint or a separate query just to compute an untagged count. No pl-PL visual baselines (authored in E47).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Toggle a facet tag on | Click an unchecked sidebar tag | Tag id appended to `tag_ids` URL param; `page` reset; models query refetches | No error expected |
| Toggle a facet tag off below 2 | Remove a tag leaving 1, with `tag_match=any` set | `tag_ids` shrinks; `tag_match` dropped by `validateSearch` normalization (no stranded `any`) | No error expected |
| Toggle untagged | Click the untagged checkbox | `untagged=true` written to URL; models query sends `untagged=true`; clicking again removes the param and the query omits it | No error expected |
| AND too narrow | `tag_ids` length ≥2, `tag_match` unset/`"all"`, models total 0 | EmptyState shows "Switch to OR" (primary) + "Clear filters" (secondary); Switch to OR sets `tag_match=any` | No error expected |
| Empty, non-recoverable | 0 results, not a ≥2-AND case, some filter active | EmptyState shows "Clear filters" only | No error expected |
| Empty, no filters | 0 results, no active filter | EmptyState message only, no action button | No error expected |
| tag-groups load error | `useTagGroups` isError or `useModels` isError | Error-tone EmptyState with a retry action that refetches both | Retry refetches groups + models |
| Legacy category URL | `/catalog?category_id=x` | `category_id` stripped by `validateSearch`; no category filter applied; catalog renders normally | No error expected |

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/routes/CatalogList.tsx` -- primary rewrite. Drop `useCategoriesTree`, `CategoryTreeSidebar`, `expandCategoryIds`, `findNode`, `setCategoryId`, and the `CategoryNode`/`CategoryTree` imports. Add `useTagGroups()`; render `FacetSidebar` (desktop unconditional after the loading guard, plus the mobile Sheet variant with `mobile`). Add `toggleTag(id)` and `toggleUntagged()` navigate handlers (both `replace`, both reset `page`). Change the `useModels(...)` call: drop `category_ids`, add `untagged: search.untagged`. Rebase the loading/error early-returns on `tagGroups` instead of `tree`. `filtersActive` counts `tag_ids`/`status`/`source`/`q`/`untagged`. Add the AND-too-narrow "Switch to OR" + "Clear filters" empty-state recovery.
- `apps/web/src/modules/catalog/hooks/useModels.ts` -- add `untagged?: boolean` to `ModelsFilters`; in `buildParams` `p.set("untagged", "true")` only when `f.untagged` is truthy. Participates in the `["sot","models",filters]` key automatically. Leave category params untouched (backend-live; E47 scope).
- `apps/web/src/routes/catalog/index.tsx` -- remove `category_id` from `CatalogSearch` and from `validateSearch` (`CatalogList`, its only consumer, migrates here — E43 preserved it "until CatalogList migrates in 44.3"). Keep `tag_ids`/`tag_match`/`untagged` validation as-is.
- `apps/web/src/ui/custom/EmptyState.tsx` -- add optional `secondaryAction?: { labelKey: string; onClick: () => void }`, rendered as a second outline button beside the primary. Additive — the 10 existing single-`action` callers are unaffected.
- `apps/web/src/modules/catalog/hooks/useModels.test.tsx` -- add cases: `untagged=true` emitted when set; omitted when `false`/`undefined`.
- `apps/web/src/routes/catalog/index.test.ts` -- update the "coexistence with category_id (AC #6)" describe: `category_id` is now stripped, not preserved (drop it from the "full" expectation; a `category_id`-only URL normalizes to `{}`).
- `apps/web/src/locales/en.json`, `pl.json` -- add `catalog.actions.switch_to_or` ("Switch to OR" / "Przełącz na dowolne") and `catalog.filters.openTags` ("Tags" / "Tagi", mobile sidebar sheet label). Remove the now-orphaned `catalog.filters.openCategories`. Keep both files' key sets identical.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/hooks/useModels.ts` -- add `untagged?: boolean` to `ModelsFilters`; `buildParams` appends `untagged=true` only when truthy.
- [x] `apps/web/src/routes/catalog/index.tsx` -- remove `category_id` from `CatalogSearch` interface and its `validateSearch` block.
- [x] `apps/web/src/ui/custom/EmptyState.tsx` -- add the optional `secondaryAction` prop and render it as a second outline button when present.
- [x] `apps/web/src/modules/catalog/routes/CatalogList.tsx` -- swap the category sidebar for `FacetSidebar` (desktop + mobile Sheet) fed by `useTagGroups()`; add `toggleTag`/`toggleUntagged`; pass `untagged` (drop `category_ids`) to `useModels`; rebase guards + `filtersActive`; add the AND-too-narrow recovery (Switch to OR + Clear filters).
- [x] `apps/web/src/locales/en.json` & `pl.json` -- add `catalog.actions.switch_to_or` and `catalog.filters.openTags`; remove `catalog.filters.openCategories`; keep key sets identical.
- [x] `apps/web/src/modules/catalog/hooks/useModels.test.tsx` -- add the `untagged` param cases (matrix row 3).
- [x] `apps/web/src/routes/catalog/index.test.ts` -- update the category_id AC #6 describe to assert stripping (matrix row 8).

**Acceptance Criteria:**
- Given the catalog list renders with tag groups loaded, when the user checks a sidebar facet tag, then its id is added to the `tag_ids` URL param, `page` resets, and the models query includes that tag.
- Given the untagged checkbox is toggled on, when `CatalogList` requests models, then the query carries `untagged=true`; toggling off removes both the URL param and the query param.
- Given `tag_ids` has ≥2 entries with an effective AND (`tag_match` unset or `"all"`) and the result is empty, when the EmptyState renders, then it offers "Switch to OR" (which sets `tag_match=any`) and "Clear filters".
- Given a `/catalog?category_id=x` URL, when the route validates search, then `category_id` is stripped and no category filter is applied, and `CatalogList` compiles without any `useCategoriesTree`/`CategoryTreeSidebar`/`category_id` reference.
- Given the app builds, when `npm run typecheck`, `npm run lint`, and `npm run test` run in `apps/web/`, then all pass with zero warnings and no color literals are introduced.

## Spec Change Log

_No `bad_spec` loopback occurred; the single review pass produced one auto-fixed patch (see Review Triage Log)._

## Review Triage Log

### 2026-07-20 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 2
- reject: 5
- addressed_findings:
  - `[low]` `[patch]` `andTooNarrow` keyed on `items.length === 0`, so a stale `?page=2` URL whose filtered set still has matches on page 1 (`total > 0`, current page empty) was misdiagnosed as an AND-too-narrow result and falsely offered "Switch to OR". Tightened the guard to `total === 0` (the whole filtered set is empty, not just this page) so page-overshoot falls through to the Clear-filters branch instead. `CatalogList.tsx`; verified by typecheck + lint + full suite (705/705).
- deferred (real, pre-existing — recorded in `deferred-work.md`): (1) `useTags()` error/loading is unguarded, so a tags-query failure strips FilterRibbon chip labels and the retry never refetches `tags` (unchanged since 44.2); (2) a stale `/catalog?page=2` with no filters and one page of results is a no-recovery dead-end (structurally-unchanged `filtersActive ? clear : undefined` branch).
- rejected (by-design / no trigger / out-of-scope): generic empty-state copy + "Switch to OR"/"Przełącz na dowolne" wording (buttons self-label; consistent with the OR="Dowolne" toggle vocab; dedicated empty-copy refinement is E47 UX/visual scope); `andTooNarrow` not diagnosing the exact narrowing culprit when status/source/q are also active (by-design — the empty state offers BOTH "Switch to OR" primary and "Clear filters" secondary, and broadening tags is a legitimate first recovery step that gracefully falls through); mobile Sheet not closing after a tag/untagged toggle (by-design — the facet sidebar is multi-select, so auto-closing per toggle would break selecting multiple tags; the old single-select category tree closed on select, the new one correctly does not); two `FacetSidebar` instances sharing one `localStorage` collapse key with independent state (cosmetic collapse-state divergence that self-heals on reload; inherent to the 44.1 component + the standard desktop-hidden/mobile-Sheet dual-mount); `EmptyState` `secondaryAction` rendered only inside the `action` block (no current caller passes a secondary without a primary — `andTooNarrow` always passes both).

## Design Notes

- **`EmptyState.secondaryAction` (additive) over a bespoke block:** the AND-too-narrow case needs two recovery buttons; extending the shared primitive with an optional second action keeps the centered layout consistent and reusable, and — being optional — leaves all existing single-action callers and the (absent) test untouched. Modifying an existing `ui/` primitive does not trip the Visual Coverage Contract (that gates file *additions*).
- **`untaggedCount` left `undefined`:** `TagGroupsResponse` carries no untagged count and `FacetSidebar` renders no count when the prop is `undefined`. A dedicated `useModels({untagged:true})` count query would be a wasted round-trip for a nicety — out of scope; the checkbox works without a badge.
- **`tag_match` stranding handled by `validateSearch`, so `toggleTag` stays minimal:** `toggleTag` only rewrites `tag_ids` and spreads the rest; TanStack runs `validateSearch` on the resulting navigation, which drops a non-default `tag_match` below 2 tags (the E44.2 enforcement layer). No need to re-derive the gate inline.
- **`category_id` URL removal is the planned 44.3 handoff:** E43 (43.3) deliberately preserved the `category_id` param "until CatalogList migrates in 44.3". This story is that migration; `search.category_id` has no other consumer (`AddModelForm`/`useUpdateModel` use their own `category_id`), so removing it from the route is self-contained. The `useCategoriesTree` hook and `CategoryNode`/`CategoryTree` types stay (E47).

## Verification

**Commands:** (run from `apps/web/`)
- `npm run typecheck` -- expected: `tsc -b` passes, no type errors.
- `npm run lint` -- expected: ESLint `--max-warnings=0` + Stylelint pass (no color literals).
- `npm run test` -- expected: Vitest green, including the new `useModels` untagged cases and the updated `index.test.ts` category_id assertions; all pre-existing cases still pass.

**Manual checks:**
- No new Playwright visual baseline in 44.3: pl-PL facet-surface baselines are authored in Epic 47 per the epic plan. A full `CatalogList` render/integration test needs router-hook mocking with no in-repo precedent and was explicitly deferred to E47 by 44.2 (already in `deferred-work.md`) — this story's new logic is covered at the hook (`useModels`) and URL (`validateSearch`) layers plus typecheck/lint. Confirm `npm run test:visual` still passes, or, if the browser cannot run in this environment, state so and rely on the fact that the desktop catalog snapshot's default 0-filter state renders the same facet sidebar shape.

## Auto Run Result

Status: done

**Summary:** Migrated `CatalogList` from the legacy category-tree browse to the facet-tag browse surface. Mounted `FacetSidebar` (desktop + mobile Sheet) fed by `useTagGroups()`, wired `tag_ids` / `tag_match` / `untagged` URL state into the models query and the sidebar, dropped the `category_id` URL param and all category-tree consumption (the `useCategoriesTree` hook + `CategoryNode`/`CategoryTree` types stay — E47), and gave the AND-too-narrow empty result a two-action recovery ("Switch to OR" + "Clear filters") via a new optional `EmptyState.secondaryAction`. Purely frontend; the backend already accepts these params (E42) and the FE data layer exists (E43). The frozen `<intent-contract>` was not modified.

**Files changed:**
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` — swapped category sidebar → `FacetSidebar`; added `toggleTag`/`toggleUntagged`; passed `untagged` (dropped `category_ids`) to `useModels`; rebased guards + `filtersActive` onto `tagGroups`/`untagged`; added the `andTooNarrow` (keyed on `total === 0`) empty-state recovery; removed the dead `expandCategoryIds`/`findNode` helpers.
- `apps/web/src/modules/catalog/hooks/useModels.ts` — `ModelsFilters.untagged?: boolean`; `buildParams` emits `untagged=true` when truthy.
- `apps/web/src/routes/catalog/index.tsx` — removed `category_id` from `CatalogSearch` + `validateSearch` (its only consumer migrated here).
- `apps/web/src/ui/custom/EmptyState.tsx` — added optional `secondaryAction` (additive; existing single-action callers unaffected).
- `apps/web/src/locales/en.json`, `pl.json` — added `catalog.actions.switch_to_or` + `catalog.filters.openTags`; removed orphaned `catalog.filters.openCategories`; key sets stay identical.
- `apps/web/src/modules/catalog/hooks/useModels.test.tsx` — added `untagged` param cases.
- `apps/web/src/routes/catalog/index.test.ts` — updated the AC#6 describe to assert `category_id` is now stripped.

**Review findings breakdown:** 1 patch applied (tighten `andTooNarrow` to `total === 0` so a stale `?page=2` overshoot with page-1 matches no longer false-offers "Switch to OR"); 2 deferred to `deferred-work.md` (unguarded `useTags()` chip-label degradation — pre-existing since 44.2; no-filter page-overshoot dead-end — pre-existing branch); 5 rejected as by-design / no-trigger / E47-scope (see Review Triage Log).

**Verification performed (from `apps/web/`):**
- `npm run typecheck` — pass (`tsc -b`, no errors).
- `npm run lint` — pass (ESLint `--max-warnings=0` + Stylelint; no color literals; only the pre-existing benign "React version not specified" notice, exit 0).
- `npm run test` — pass (126 files, 705 tests green), including the new `useModels` untagged cases (12) and the updated `index.test.ts` category_id assertions (21).
- `npm run test:visual` — not run (no browser in this environment); pl-PL facet-surface baselines are Epic 47 scope.

**Residual risks:** No router-level `CatalogList` integration/visual test (E47 scope; new logic covered at the `useModels`/`validateSearch` layers). Two low-consequence pre-existing edges recorded in `deferred-work.md`. `untaggedCount` is intentionally omitted (no cheap source; the sidebar renders the checkbox without a count badge).
