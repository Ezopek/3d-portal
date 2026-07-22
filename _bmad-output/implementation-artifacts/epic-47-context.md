# Epic 47 Context: i18n + theming + visual regression + runbook/docs cutover + terminal category retirement

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic 47 is the terminal epic of Initiative 25 (Facet Tag Taxonomy + Category Retirement), closing out the catalog rebuild that replaces a single mandatory `Category` per model with admin-managed, facet-grouped tags. It finishes the cutover left open by earlier epics: swap i18n keys from category-based to facet-based copy, enforce the dark-mode token-only rule on the new facet surfaces, add pl-PL Playwright visual baselines for those surfaces, update agent-runbook/docs that reference categories, and — uniquely in this epic — perform the actual destructive retirement of the `Category` API/ORM/schema surface, which every prior epic (E41–E46) deliberately built additively alongside so `main` stayed green. Until 47.4/47.5 land, the live category API is a zero-code compatibility bridge; this epic is what finally removes it.

## Stories

- Story 47.1: i18n key swap (remove category keys, add facet/tag-group/admin keys, en+pl parity)
- Story 47.2: pl-PL Playwright visual baselines for facet surfaces + dark-mode token AC
- Story 47.3: Agent add-model runbook + docs cutover (drop category pre-flight)
- Story 47.4: Category API-surface retirement + FE category-tree type/hook cleanup (reversible by code revert)
- Story 47.5: Category ORM + DTO + migration `0019` atomic cutover (destructive, forward-only)

## Requirements & Constraints

- i18n: remove `catalog.filters.category` / `openCategories` / `a11y.allCategories`; add `facets` / `matchAll` / `matchAny` / `untagged` / `noTags` / `tags.groupless` and admin merge/rename/newGroup/duplicate keys — both locales must stay in parity (no key present in one language file only).
- Dark mode is a hard acceptance criterion for every new facet surface (sidebar, ribbon, grouped detail, admin screen, untagged states): token-only styling, no hardcoded color literals, correct in both light and dark.
- New Playwright visual specs must render in pl-PL locale (project-wide visual-test convention); consolidate any overlapping `/api/*` route mocks used by these specs into a single handler rather than duplicating per-spec mocks.
- Agent add-model runbook and any category-referencing docs must drop the `GET /api/categories` pre-flight step and the requirement that model create supply a `category_id` (tagging is optional at create).
- 47.4 (API-surface retirement) and 47.5 (ORM+DTO+migration `0019`) may only proceed once every consumer of `GET /api/categories` / `category_id` is gone: the E43–E45 frontend and the 47.3 runbook/hydrate-script updates. This is a hard ordering constraint, not a suggestion — the app auto-deploys `main` HEAD, so removing a still-consumed surface produces a live outage, not just a failing test.
- 47.5 is destructive and forward-only (its migration's `downgrade()` raises) and must land as a single atomic commit together with the 45.3 admin create-form category-selector removal (same deploy HEAD). It requires an explicit operator destructive-go recorded before dev-go/deploy — do not treat this file or the epic sketch as that authorization.
- 47.4 is destructive to an API surface but reversible by plain code revert, so it follows the standard review/gate path (not the full destructive-migration gate that 47.5 requires).

## Technical Decisions

- The `Category` entity, `Model.category_id`, and all category routes/schemas/service functions are removed only in this epic; `CategorySummary` specifically survives 47.4 (still embedded in the retained `ModelDetail`/`ShareModelView`) and is only dropped in 47.5, together with `ModelCreate/Patch/Summary.category_id`, `ModelDetail.category`, and `ShareModelView.category`.
- 47.4 additionally owns the frontend-side symmetry: deleting the FE `CategoryNode`/`CategoryTree` types and the `useCategoriesTree` hook once their last consumers (from E44/E45) are migrated. FE `CategorySummary` and the `ModelSummary.category_id`/`ModelDetail.category` fields stay alive until 47.5.
- The destructive migration `0019_drop_category` is `down_revision = "0018_facet_tags"`, forward-only; drops the `model.category_id` column/index via `batch_alter_table` (no `drop_constraint` — the FK is an unnamed inline) then drops the `category` table.
- The design source of truth for visual/dark-mode rules is `docs/design/HANDOFF-tagi-fasetowe.md` (§7 token/dark-mode rule); it exists in this worktree's `docs/design/` directory (outside the planning-artifacts folder) but was not otherwise duplicated into this context.
- Determinism requirement applies across all Initiative 25 epics: 3 consecutive identical pytest + vitest pass counts required before merging any story in this epic.

## Cross-Story Dependencies

- 47.1–47.3 depend on E44–E46 UI having landed (visual specs need real surfaces to baseline against).
- 47.4 depends on 44.3 + 45.x (no remaining FE category read) and on 47.3 (runbook/hydrate cutover) having landed first.
- 47.5 depends on 47.4 and on 45.3's create-form category-selector removal, which must deploy in the same commit/HEAD as 47.5.
- 47.5's destructive-go is a separate, deferred operator decision not granted by any planning artifact — it must be obtained explicitly at 47.5's dev-go.
