---
title: 'Story 44.1 — FacetSidebar'
type: 'feature'
created: '2026-07-19'
status: 'in-review'
baseline_revision: '903795fd798a5bc1298379b158f7556f84a4f30f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-44-context.md'
  - '{project-root}/docs/design/HANDOFF-tagi-fasetowe.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The catalog browses along a single hard category (`CategoryTreeSidebar` + `category_id`), which forces a lossy "pick one" per model. The facet-tag initiative needs a sidebar that lets users select tags across multiple facet groups (type, room, system, material) with counts, search, and an untagged-triage affordance.

**Approach:** Add a new controlled, presentational `FacetSidebar` component that renders facet groups (from the E43 `useTagGroups` data shape) as collapsible sections with multi-select checkboxes + per-tag counts, a client-side substring search over tag names, `localStorage`-persisted collapse state, and a pinned "untagged" pseudo-facet. Selection is driven by props/callbacks; URL wiring and route mounting are Story 44.3's job.

## Boundaries & Constraints

**Always:**
- Component is **presentational/controlled**: selection state (`selectedTagIds`, `untaggedActive`) arrives via props; the component only renders state and fires callbacks. It owns its own internal UI state (search query, collapse state) only.
- Token-only styling: Tailwind classes bound to theme tokens (`bg-card`, `border-border`, `text-muted-foreground`, `text-foreground`, `bg-primary`, `text-primary-foreground`, `hover:bg-accent`). **Zero inline hex / color literals** (ESLint + Stylelint color-literal ban applies; hard AC per HANDOFF §7 — dark mode then works automatically via `.dark`).
- All user-visible strings via `useTranslation()` + `t(...)`, keys added to **both** `en.json` and `pl.json` with an identical key set. Group/tag labels come from data: prefer `name_pl` when `i18n.language.startsWith("pl")` and `name_pl` is non-null, else `name_en` (mirror `CategoryTreeSidebar`'s `preferPl` pattern).
- Default-expanded rule (first render, no persisted state): the first `DEFAULT_EXPANDED_GROUP_COUNT` groups by `position` **plus** any group containing a currently-selected tag; all others collapsed. `DEFAULT_EXPANDED_GROUP_COUNT` is a module-local named constant (=2), tunable without logic change.
- Collapse state persists per user in `localStorage` under key `catalog:facet-collapse`; reads are guarded (try/catch + shape validation) and fall back to the default rule on any failure — never throw.
- Untagged pseudo-facet is a single checkbox row pinned at the sidebar bottom, always visible (search does not filter it); it fires `onToggleUntagged` and reflects `untaggedActive`.

**Block If:**
- The E43 data layer this consumes is absent (no `TagGroupRead`/`TagReadWithCount`/`TagGroupsResponse` in `@/lib/api-types`, or no `useTagGroups` hook) → HALT `blocked`, blocking condition `missing E43 data layer`.

**Never:**
- Do **not** wire URL search params, mount into `CatalogList.tsx`, replace the `CategoryTreeSidebar` usage, or touch the models query — all owned by Story 44.3.
- Do **not** remove `CategoryTreeSidebar`, `useCategoriesTree`, `CategoryNode`/`CategoryTree`, or any category surface (removal is Epic 47 / story 47.4).
- Do **not** add a shared `apps/web/src/ui/*.tsx` primitive (would trip the Visual Coverage Contract hook); render the checkbox/collapse inline within the component using a native `<input type="checkbox">` + token styling.
- Do **not** add the intra-group AND/OR match badge or an in-sidebar "Clear filters" affordance — those belong to the FilterRibbon (Story 44.2) / EmptyState (44.3).
- No new backend endpoint, no fuzzy search, no server-side tag search.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default render | `groups` (each with `tags` + `model_count`), no selection, empty `localStorage` | Search input at top; first 2 groups by `position` expanded, rest collapsed; each visible tag row = checkbox + localized name + count; untagged row pinned at bottom | No error expected |
| Toggle tag | Click an unchecked tag row | `onToggleTag(tag.id)` fires exactly once; checkbox checked-state is derived from `selectedTagIds` (controlled) | No error expected |
| Toggle untagged | Click untagged row | `onToggleUntagged()` fires exactly once | No error expected |
| Client search | Type substring in search input | Only tags whose `name_pl` OR `name_en` contains the query (case-insensitive) render; groups with ≥1 match render expanded (collapse ignored while searching); groups with 0 matches hidden; untagged row still pinned | No error expected |
| Search no matches | Query matches no tag | Group-list area shows `t("catalog.tags.noMatches")`; untagged row still pinned | No error expected |
| Collapse persistence | User collapses a group, component remounts | That group stays collapsed (restored from `catalog:facet-collapse`) | Malformed/unavailable storage → default expansion, no throw |
| Active-filter default expand | `selectedTagIds` contains a tag in a group beyond the first 2, no persisted state | That group is expanded on initial render | No error expected |
| Groupless tags | `groupless` non-empty | Rendered in a trailing collapsible group labeled `t("catalog.filters.ungrouped")`, above the untagged row | Empty `groupless` → section omitted |

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/components/CategoryTreeSidebar.tsx` -- pattern reference (props/controlled shape, `preferPl` label, chevron + `a11y.expand`/`a11y.collapse`, storage guard `loadExpanded()`, token classes, `mobile` prop). Do NOT modify.
- `apps/web/src/lib/api-types.ts` -- source of `TagGroupRead` (`{id, slug, name_en, name_pl, position, tags: TagReadWithCount[]}`), `TagReadWithCount` (`TagRead & {model_count: number}`), `TagGroupsResponse` (`{groups, groupless}`). Import types from here.
- `apps/web/src/modules/catalog/hooks/useTagGroups.ts` -- the E43 hook (`["sot","tag-groups"]`) the parent (44.3) will call to supply this component's data. Not called here.
- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` -- token-class idiom reference; also confirms `tag_match`/`untagged` are not yet consumed (44.3).
- `apps/web/src/shell/ThemeProvider.tsx` -- `localStorage` lazy-init + `useEffect`-persist reference pattern.
- `apps/web/src/locales/en.json`, `pl.json` -- flat dotted keys; add facet keys, reuse `catalog.tags.searchPlaceholder`, `catalog.tags.noMatches`, `a11y.expand`, `a11y.collapse`.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/components/FacetSidebar.tsx` -- new named export `FacetSidebar`. Props: `{ groups: TagGroupRead[]; groupless: TagReadWithCount[]; selectedTagIds: string[]; onToggleTag: (id: string) => void; untaggedActive: boolean; onToggleUntagged: () => void; untaggedCount?: number; mobile?: boolean }`. Implement: search input (reuse `@/ui/input`), collapsible group headers (inline `useState`-driven toggle + chevron from `lucide-react`, `aria-expanded`, `aria-label` via `a11y.expand`/`a11y.collapse`), tag rows as `<label>` wrapping a native `<input type="checkbox">` + localized name + `model_count`, trailing groupless group when non-empty, pinned untagged footer row. Internal state: `query`, `expandedGroupIds: Set<string>` (module-local `DEFAULT_EXPANDED_GROUP_COUNT = 2`; lazy-init from `localStorage["catalog:facet-collapse"]` with guarded parse, else default rule; `useEffect` persists on change). Token-only classes; desktop `hidden ... lg:block` vs `mobile` `w-full` container à la `CategoryTreeSidebar`.
- [x] `apps/web/src/modules/catalog/components/FacetSidebar.test.tsx` -- Vitest (Testing Library, `fireEvent`, `localStorage.clear()` in `afterEach`; no QueryClient needed — presentational). Cover every I/O & Edge-Case Matrix row: default-expand (first 2 + active-filter group), tag toggle callback, untagged toggle callback, search filter + expand-on-search, no-matches state, collapse persistence round-trip, groupless rendering, malformed-`localStorage` fallback.
- [x] `apps/web/src/locales/en.json` & `apps/web/src/locales/pl.json` -- add `catalog.filters.untagged` ("Untagged models" / "Modele bez tagów") and `catalog.filters.ungrouped` ("Ungrouped" / "Bez grupy") to both files (identical key set).

**Acceptance Criteria:**
- Given groups with tags, no selection, and empty `localStorage`, when the sidebar renders, then exactly the first 2 groups by `position` are expanded and every visible tag row shows a checkbox, its localized name, and its `model_count`.
- Given a group beyond the first 2 that contains a selected tag and no persisted collapse state, when the sidebar first renders, then that group is expanded.
- Given a rendered sidebar, when a tag checkbox is clicked, then `onToggleTag` fires once with that tag's `id` and the checked state follows the `selectedTagIds` prop (fully controlled).
- Given a rendered sidebar, when the untagged row is clicked, then `onToggleUntagged` fires once and the row reflects `untaggedActive`.
- Given a search query, when it is typed, then only tags whose `name_pl` or `name_en` contains it (case-insensitive) are shown, matching groups are expanded, non-matching groups are hidden, the untagged row stays pinned, and a query with no matches shows `catalog.tags.noMatches`.
- Given a user collapses a group, when the component remounts, then that group is restored collapsed from `catalog:facet-collapse`; and given malformed/unavailable storage, the default expansion is used without throwing.
- Given the app builds, when `npm run lint`, `npm run typecheck`, and `npm run test` run in `apps/web/`, then all pass with zero warnings and no color literals are introduced.

## Spec Change Log

_No `bad_spec` loopback occurred; the review pass produced only auto-fixed patches (see Review Triage Log)._

## Review Triage Log

### 2026-07-19 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `labelOf` rendered a blank label for a valid empty-string `name_pl` in the pl locale (guard was `!== null`); changed to a truthy check so it falls back to `name_en`, matching the sibling `ModelHero` convention; added a pl-locale regression test.
  - `[low]` `[patch]` A group header toggle during an active search silently mutated and persisted hidden collapse state; guarded `onClick` to no-op while searching; added a regression test proving the in-search click no longer collapses-and-persists.
  - `[low]` `[patch]` The search `Input` exposed only a `placeholder` (not an accessible name); added an `aria-label`.
- rejected (by-design / spec-scoped / no real trigger): persisted-set governing over the active-filter reveal on return visits (spec-accepted; FilterRibbon in 44.2 is the always-visible active-filter surface; component not yet route-wired); default-expand "breaks if groups arrive later" (parent guards loading, mirrors `CategoryTreeSidebar`); first-mount persist (matches `CategoryTreeSidebar`); stale-id accumulation (dead ids in a Set are inert); search matching tag names only (spec scope: substring, no fuzzy, tag names); `__groupless__` id collision (ids are UUIDs); diacritic-insensitive search (spec: no fuzzy); per-render `includes` scan (facet sets are tiny).

## Design Notes

- **Why controlled + prop-fed data (not self-fetching):** mirrors `CategoryTreeSidebar` (parent passes `tree`, owns loading/empty/error). Keeps 44.1 pure-presentational and unit-testable without query mocking; 44.3 calls `useTagGroups`, destructures `{groups, groupless}`, supplies `untaggedCount`, and owns selection→URL wiring.
- **Collapse persistence model:** persist the resolved expanded-id set as a JSON array. Per group, expanded = persisted membership if a persisted set exists, else the default rule. New groups absent from persisted state fall to the default rule. Guard reads exactly like `CategoryTreeSidebar.loadExpanded()` (try/catch + `Array.isArray` + string-element check → `new Set()` on failure), swapping `sessionStorage` → `localStorage`, key `catalog:facet-collapse`.
- **Checkbox inline, not a `ui/` primitive:** native `<input type="checkbox" className="peer sr-only">` (or token-styled input) inside a `<label>` avoids adding `ui/checkbox.tsx`, which would trigger the Visual Coverage Contract pre-commit hook. Keep `DEFAULT_EXPANDED_GROUP_COUNT` module-local (unexported) so the file exports only the component — otherwise `react-refresh/only-export-components` fails `--max-warnings=0`.
- **Groupless completeness:** the HANDOFF mockups only show grouped tags, but `TagGroupsResponse.groupless` can be non-empty; rendering it in a trailing section keeps every tag reachable. It is intentionally beyond the mockup — a correctness guard, not decoration.
- **No mutual-exclusivity logic** between untagged and tag selections here — that is filter semantics for 44.3; the sidebar stays a dumb renderer.

## Verification

**Commands:** (run from `apps/web/`)
- `npm run typecheck` -- expected: `tsc -b` passes, no type errors.
- `npm run lint` -- expected: ESLint `--max-warnings=0` + Stylelint pass (no color literals).
- `npm run test` -- expected: Vitest green, including the new `FacetSidebar.test.tsx` covering all matrix rows.

**Manual checks:**
- No new Playwright visual baseline in 44.1: `FacetSidebar` is not yet route-mounted (mounting is 44.3), so there is no rendered route surface to snapshot; pl-PL visual baselines for these surfaces are authored in Epic 47 per the epic plan. Confirm `npm run test:visual` is unaffected (component not imported by any route).

## Auto Run Result

Status: done

**Implemented change:** Added `FacetSidebar` — a controlled, presentational faceted-tag browse sidebar for the catalog module (Story 44.1). Renders `useTagGroups`-shaped data as collapsible facet groups with multi-select checkboxes + per-tag counts, a client-side substring search over `name_pl`/`name_en`, `localStorage`-persisted collapse state (key `catalog:facet-collapse`, default = first 2 groups by `position` ∪ groups with an active selection), a trailing groupless section, and a pinned "untagged" pseudo-facet. Selection is driven by props/callbacks; URL wiring + route mounting remain Story 44.3.

**Files changed:**
- `apps/web/src/modules/catalog/components/FacetSidebar.tsx` (new) — the component.
- `apps/web/src/modules/catalog/components/FacetSidebar.test.tsx` (new) — 13 Vitest cases covering every I/O matrix row plus the two review-patch regressions.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — added `catalog.filters.untagged` and `catalog.filters.ungrouped` (identical key sets).

**Review findings breakdown:** 3 patches applied (1 medium: empty-string `name_pl` blank-label fallback; 2 low: in-search header-toggle no-op guard, search-input `aria-label`), 0 deferred, 8 rejected as by-design / spec-scoped / no-real-trigger. No `intent_gap`, no `bad_spec`, no loopback.

**Follow-up review recommended:** false — the three fixes are localized to a single new, not-yet-route-wired component, carry no behavior/API/security/data-flow impact, and each is locked by a regression test.

**Verification performed (independently re-run after patches):**
- `npm run typecheck` (`tsc -b`) → exit 0, no type errors.
- `npm run lint` (`eslint --max-warnings=0` + stylelint) → exit 0 (only the pre-existing informational "React version not specified" note); no color literals introduced.
- `npm run test` (vitest) → 126 files, **694 tests passed** (incl. `FacetSidebar.test.tsx` 13/13).
- No new Playwright baseline: component is not yet route-mounted (44.3); `test:visual` surface unaffected.

**Residual risks:** On return visits the persisted collapse set governs, so a group holding an active tag filter is not force-re-expanded — accepted by design; the always-visible FilterRibbon (Story 44.2) is the canonical active-filter surface, and full selection→URL behavior only becomes user-facing once Story 44.3 wires and mounts the component. `untaggedCount` is an optional prop the parent (44.3) must supply.
