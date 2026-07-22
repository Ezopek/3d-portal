# Epic 47 Context: i18n + theming + visual regression + runbook/docs cutover + terminal category retirement

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic 47 is the terminal epic of Initiative 25 (Facet Tag Taxonomy + Category Retirement), closing out the catalog rebuild that replaces a single mandatory `Category` per model with admin-managed, facet-grouped tags. It finishes the cutover left open by earlier epics: swap i18n keys from category-based to facet-based copy, enforce the dark-mode token-only rule on the new facet surfaces, add pl-PL Playwright visual baselines for those surfaces, update agent-runbook/docs that reference categories, and — uniquely in this epic — perform the actual destructive retirement of the `Category` API/ORM/schema surface, which every prior epic (E41–E46) deliberately built additively alongside so `main` stayed green. Until the absorbed 47.5 cutover lands (47.4 was absorbed into 47.5 on 2026-07-22), the live category API is a zero-code compatibility bridge; this epic is what finally removes it.

## Stories

- Story 47.1: i18n key swap (remove category keys, add facet/tag-group/admin keys, en+pl parity)
- Story 47.2: pl-PL Playwright visual baselines for facet surfaces + dark-mode token AC
- Story 47.3: Agent add-model runbook + docs cutover (drop category pre-flight)
- Story 47.4: Category API-surface retirement + FE category-tree type/hook cleanup (absorbed into 47.5, 2026-07-22 — SCP `sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md`; do not build standalone)
- Story 47.5: Category API-surface + ORM + DTO + migration `0019` atomic cutover (destructive, forward-only; absorbs 47.4 and additionally migrates the last two live FE consumers — `AddModelForm` category selector removal, `ModelHero` category-ancestry breadcrumb removal with no replacement)

## Requirements & Constraints

- i18n: remove `catalog.filters.category` / `openCategories` / `a11y.allCategories`; add `facets` / `matchAll` / `matchAny` / `untagged` / `noTags` / `tags.groupless` and admin merge/rename/newGroup/duplicate keys — both locales must stay in parity (no key present in one language file only).
- Dark mode is a hard acceptance criterion for every new facet surface (sidebar, ribbon, grouped detail, admin screen, untagged states): token-only styling, no hardcoded color literals, correct in both light and dark.
- New Playwright visual specs must render in pl-PL locale (project-wide visual-test convention); consolidate any overlapping `/api/*` route mocks used by these specs into a single handler rather than duplicating per-spec mocks.
- Agent add-model runbook and any category-referencing docs must drop the `GET /api/categories` pre-flight step and the requirement that model create supply a `category_id` (tagging is optional at create).
- (Corrected 2026-07-22, `bmad-correct-course`.) The earlier "every consumer of `GET /api/categories` / `category_id` is gone after 44.3 + 45.x" precondition was **stale against shipped code**: two live `useCategoriesTree` consumers remained — `AddModelForm.tsx` (documented, operator-approved 45.3↔47.5 handshake deferral) and `ModelHero.tsx`'s category-ancestry breadcrumb (undocumented dependency; 45.2 scoped itself to the tag-chip row only). Resolution: 47.4 is absorbed into 47.5, and the absorbed cutover migrates both consumers itself as its first internal phase (a), before retiring the hook/types (b), the backend API surface (c), and the ORM/DTO/migration (d) — required order (a)→(b)→(c)→(d) inside one commit (FE stops reading before BE stops serving, before the ORM stops existing). The hard constraint stands: the app auto-deploys `main` HEAD, so no phase may ship in a separate deploy.
- The absorbed 47.5 is destructive and forward-only (its migration's `downgrade()` raises) and must land as a **single atomic commit / single deploy HEAD** covering all four phases (a)-(d), including the 45.3 admin create-form category-selector removal (handshake preserved). Operator destructive-go was **recorded 2026-07-22** (exact phrase `GO E47 ATOMIC CUTOVER`, Michał/Ezop via controller session), covering deployment of `0019_drop_category` with acceptance of losing 43 category rows + 130 model-category assignments. A **fresh verified pre-`0019` backup under the deploy lock (`/tmp/3d-portal-deploy.lock`), with demonstrated restore-readiness, remains mandatory immediately before deploy** — the pre-GO checkpoint backup does not substitute for it. No partial/hidden/internal category API bridge at any phase.

## Technical Decisions

- (Rewritten 2026-07-22 — 47.4 and 47.5 are no longer two stories; both are sub-phases of the one absorbed 47.5 cutover.) The `Category` entity, `Model.category_id`, and all category routes/schemas/service functions are removed only in this epic, all inside the absorbed 47.5's single commit: phase (b) deletes the FE `CategoryNode`/`CategoryTree` types + `useCategoriesTree` hook (ex-47.4 FE half); phase (c) deletes the backend routes/service fns/route-only schemas (ex-47.4 backend half); phase (d) drops `CategorySummary` together with `ModelCreate/Patch/Summary.category_id`, `ModelDetail.category`, `ShareModelView.category`, the `Category` ORM entity, and ships `0019_drop_category`. `CategorySummary` (BE + FE) survives phases (a)-(c) — it is embedded in the retained `ModelDetail`/`ShareModelView` until (d).
- The destructive migration `0019_drop_category` is `down_revision = "0018_facet_tags"`, forward-only; drops the `model.category_id` column/index via `batch_alter_table` (no `drop_constraint` — the FK is an unnamed inline) then drops the `category` table.
- The design source of truth for visual/dark-mode rules is `docs/design/HANDOFF-tagi-fasetowe.md` (§7 token/dark-mode rule); it exists in this worktree's `docs/design/` directory (outside the planning-artifacts folder) but was not otherwise duplicated into this context.
- Determinism requirement applies across all Initiative 25 epics: 3 consecutive identical pytest + vitest pass counts required before merging any story in this epic.

## Cross-Story Dependencies

- 47.1–47.3 depend on E44–E46 UI having landed (visual specs need real surfaces to baseline against). All three are done.
- The absorbed 47.5 depends on 47.3 (runbook/hydrate cutover — done) and on 45.3's create-form category-selector removal, which it performs itself in phase (a) of the same commit/HEAD (the 45.3↔47.5 handshake, preserved). The former "47.5 depends on 47.4" cross-story dependency is dissolved — ex-47.4 scope is the same story's internal phases (b)-(c).
- 47.5's destructive-go was recorded 2026-07-22 (`GO E47 ATOMIC CUTOVER`, Michał/Ezop, controller session); the fresh pre-deploy verified backup with demonstrated restore-readiness under the deploy lock remains a separate mandatory pre-deploy gate item.
