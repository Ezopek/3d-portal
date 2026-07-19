# Epic 44 Context: Catalog browse UI

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Replace the legacy single-category tree browse experience with the facet-tag browse UI in the catalog module. This is the frontend surface of the facet-tag initiative: a faceted sidebar (collapsible groups, multi-select checkboxes, per-tag counts, client-side search), an active-filter ribbon with an AND/OR match toggle, and a catalog list whose filters, empty-result recovery, and untagged surfacing are all driven by facet tags instead of `category_id`. It matters because a single hard category forced a lossy "pick one" per model; models legitimately span multiple axes (type, room, system, material, creator), and this epic is where users first browse the catalog along those axes.

## Stories

- Story 44.1: `FacetSidebar` (replaces `CategoryTreeSidebar`)
- Story 44.2: `FilterRibbon` (active chips + AND/OR toggle)
- Story 44.3: `CatalogList` states (facet URL wiring, empty-state CTA, untagged)

## Requirements & Constraints

- Facet filtering replaces category filtering. The catalog list must filter by `tag_ids` plus a `tag_match` mode (`all` = AND, default; `any` = OR) plus an `untagged` boolean, all carried in URL state. Default backend semantics are AND between groups / OR within a group; `tag_match` is the user-visible override. The old `category_id` / `useCategoriesTree` path is dropped.
- Untagged is a valid state, not an error. Every model with zero tags remains a catalog member (matches no facet filter); `untagged=true` surfaces exactly those models for triage. This matters immediately after cutover because all models start untagged.
- The facet sidebar shows collapsible groups with multi-select checkboxes and per-tag model counts. It has a top search that does client-side substring matching over `name_pl`/`name_en` on the already-fetched group data — no new endpoint, no fuzzy matching.
- Default-expanded state: the first 2 groups by `position` are expanded, plus any group that currently has an active filter; the rest collapsed. The "how many expanded" number should be a named constant so it can be tuned without logic changes.
- Collapse state is persisted per user in `localStorage`.
- An "untagged" pseudo-facet is pinned (per handoff, at the bottom of the sidebar).
- Empty result (AND too narrow) shows an EmptyState with recovery actions: "Switch to OR" and "Clear filters".
- Dark-mode hard AC: all new facet surfaces are token-only styled and must pass both light and dark themes. Use Tailwind classes bound to theme tokens (`bg-card`, `text-muted-foreground`, `border-border`, etc.) — zero inline hex / color literals (the existing ESLint/Stylelint color-literal ban applies). Tokens are already theme-aware via `.dark`, so correct token usage makes dark mode work automatically.
- The visual mockup (`docs/design/HANDOFF-tagi-fasetowe.md` + its HTML) is the source of truth for appearance; relevant mockups are 02/03 (sidebar), 04 (AND/OR toggle), 08B/08D (untagged + empty-result states).
- Playwright visual baselines for these surfaces are authored later (Epic 47) in pl-PL locale — not in this epic, but build the surfaces to be testable that way.

## Technical Decisions

- Work lives in `apps/web/src/modules/catalog`. Concrete file map: `components/CategoryTreeSidebar.tsx` → new `FacetSidebar`; `components/FilterRibbon.tsx` gains the active-chip bar + AND/OR toggle (existing Status/Source/Sort controls unchanged); `routes/CatalogList.tsx` drops `useCategoriesTree`/`expandCategoryIds`/`category_id` and wires the facet URL state (pagination/empty-state scaffolding stays).
- Data comes from a single facet round-trip: a `GET /api/tag-groups`-style call surfaced through a `useTagGroups()` hook returning groups + their tags + per-tag counts. There is no server search endpoint; the sidebar filters the fetched data client-side. `useTags` (now carrying each tag's `group`/`group_id`) remains available.
- The frontend Tag type carries `group`/`group_id` (+ group position); `ModelSummary`/`ModelDetail` no longer carry `category_id`/`category`.
- AND/OR combination is a user-facing switch (`tag_match`), defaulting to AND (`all`).
- The `useCategoriesTree` hook and the frontend `CategoryNode`/`CategoryTree` types are NOT deleted in this epic — their removal is deferred to Epic 47 (story 47.4), gated on this epic (44.3) plus 45.x being the last FE consumers gone. Do not remove them here; just stop consuming them.

## UX & Interaction Patterns

- Sidebar (mockups 02/03): grouped facets replace the category tree. Groups collapse/expand; each tag row has a checkbox and a count. Top-of-sidebar search filters visible tags live. "Untagged" pinned as a pseudo-facet.
- Filter ribbon (mockups 03/04): removable chips for each active filter, plus the AND/OR toggle. The sidebar is the primary tag-selection surface; the ribbon reflects and lets users remove active selections.
- Empty state (mockup 08D): when an AND intersection yields nothing, offer "Switch to OR" and "Clear filters" as the recovery path rather than a dead end.
- Untagged surfacing (mockup 08B): the `untagged=true` filter lets an operator triage the models that have no tags yet.

## Cross-Story Dependencies

- Depends on Epic 43 (landed on `main`): the FE data layer this epic consumes — api-types with the grouped Tag shape, the `useTagGroups` hook, and the `tag_ids`/`tag_match`/`untagged` URL-state helpers — was delivered there (stories 43.1 api-types, 43.2 hooks, 43.3 URL state). This epic builds the UI on top of that layer; it should not re-add category reads.
- Within the epic: 44.1 (`FacetSidebar`) and 44.2 (`FilterRibbon`) produce the selection surfaces whose state 44.3 (`CatalogList`) wires into URL params and the models query; the untagged pseudo-facet spans the sidebar (44.1) and the list/empty-state (44.3).
- The backend facet API (`GET /api/models` with `tag_ids`/`tag_match`/`untagged`, `GET /api/tags?with_counts`, `GET /api/tag-groups`) is provided by Epic 42; the live `GET /api/categories` endpoint remains as a zero-code compatibility bridge until Epic 47 — so this epic must simply stop calling it.
- Downstream: Epic 45 (card/detail/edit) reuses shared components/patterns from this epic; Epic 47's category-tree type/hook cleanup and pl-PL visual baselines are gated on this epic's surfaces landing.
- G-UXGATE: the HANDOFF mockup is the visual SoT; whether a `bmad-ux` refinement item is required before FE work is an operator decision at sprint planning.
