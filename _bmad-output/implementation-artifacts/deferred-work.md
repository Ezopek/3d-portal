# Deferred Work

## Deferred from: code review of 41-1-taggroup-entity-tag-membership-category-removal (2026-07-18)

- No ORM↔migration drift guard — the inline comment claims migration 0018 (story 41.2) will create index `uq_tag_group_slug`, but nothing in the test suite verifies ORM metadata against migrations (no `compare_metadata`/autogenerate diff test). If 41.2 names the index differently or omits it, no test fails. 41.2 owns the migration and should add a schema-parity test (`test_migration_0018`).
- `Tag.group_id` FK is unindexed — intentional for 41.1 (AC #2 matches the 0018 sketch: add column + FK, no index) and consistent with the ORM. Group-scoped tag queries ("tags in group X ordered by group_position") don't exist yet; when E42 introduces them, evaluate adding an index on `tag.group_id`.

## Deferred from: story 41.2 create-story (2026-07-18)

- **Destructive category-retirement DDL is owed by the E42 backend cut-over.** Migration `0018_facet_tags` (this story) is **additive-only** — it creates `tag_group` and adds `tag.group_id`/`group_position`, with a reversible `downgrade`. The destructive half of the original `0018` sketch — `op.batch_alter_table("model").drop_index("ix_model_category_id")` + `drop_column("category_id")` and `op.drop_table("category")`, forward-only (`downgrade` raises `NotImplementedError`) — was pulled out and must land in the **same commit/migration as the ORM removal** of `class Category` + `Model.category_id` from `_entities.py` (E42 stories 42.1/42.3/42.5; likely 42.5 or a dedicated cut-over story). Suggested revision id: `0019_drop_category` (`down_revision = "0018_facet_tags"`). Reason for the split: prod applies `alembic upgrade head` against the HEAD-built image on any deploy (`docs/operations.md:234`); a forward-only destructive migration on `main` before the ORM/app `Category` references are gone irrecoverably bricks prod catalog/share (re-deploying the prior image can't recover a dropped table + a raising `downgrade`). Keeps "main deployable at every commit" + ORM↔migration parity throughout E41→E47. **Operator confirmation requested** (41.2 Story Creation Question #1).
- **Full ORM↔migration drift guard still open (carried from 41-1).** `test_migration_0018` pins the `uq_tag_group_slug` name + `group_id`/`group_position` shape, but there is still no `compare_metadata`/autogenerate diff test asserting the whole ORM metadata matches the migration head. Revisit when the E42 cut-over migration lands (good moment to add a single autogenerate-diff parity test covering the finished facet schema).

## Deferred from: story 41.2 dev (2026-07-18)

- **Confirmed landed as additive-only.** Migration `0018_facet_tags` shipped exactly as scoped: `upgrade()` creates `tag_group` + `uq_tag_group_slug` and adds `tag.group_id` (nullable) / `tag.group_position` (NOT NULL, `server_default="0"`) with FK `fk_tag_group_id` → `tag_group.id` `ON DELETE SET NULL`; `downgrade()` is fully reversible. `model`, `model.category_id`, and `category` are untouched (asserted by `test_migration_0018` as the deferral guard). Alembic has a single head (`0018_facet_tags`).
- **Destructive category-retirement DDL remains owed by the E42 backend cut-over** (as detailed in the create-story note above): a new migration — suggested `0019_drop_category` (`down_revision = "0018_facet_tags"`) — doing `op.drop_index("ix_model_category_id")` + `op.batch_alter_table("model").drop_column("category_id")` + `op.drop_table("category")`, forward-only (`downgrade` raises), must land in the SAME commit/migration as the ORM removal of `class Category` + `Model.category_id` from `_entities.py` (E42 stories 42.1/42.3/42.5; likely 42.5 or a dedicated cut-over story). Never place the forward-only drop on `main` ahead of the ORM/app `Category` removal — it bricks prod on any `alembic upgrade head` deploy and is unrecoverable.

## Deferred from: story 44.2 dev repair review (2026-07-20)

- source_spec: `_bmad-output/implementation-artifacts/spec-44-2-filterribbon.md`
  summary: No `CatalogList` integration test covers the full toggle→URL→models-query round-trip (including the `setFilters` `>=2` gate that drops a stranded `tag_match`).
  evidence: There is no `CatalogList.test.tsx` in the tree; the `setFilters` gate at `apps/web/src/modules/catalog/routes/CatalogList.tsx:77` is only reasoned about in a comment. The user-facing invariant ("no stranded `tag_match` below 2 tags") is enforced and now unit-tested at the `validateSearch` layer (TanStack runs it on every navigation) and at `useModels.buildParams`, so the behavior is covered where it actually runs; the missing piece is a router-level integration test. The spec's Verification section defers integration/visual coverage of the facet surface to Epic 47, so add this router-level test when E47 authors the facet-surface integration/visual suite.
  status: PARTIALLY RESOLVED in the 44.3 dev-repair pass (2026-07-20). `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` now mounts the route (real `createMemoryHistory` router + `QueryClientProvider`, stubbed `fetch`) and covers the `andTooNarrow` → Switch-to-OR (`tag_match=any`) round-trip, the single-filter vs. no-filter empty branches, and `untagged` wiring. STILL OPEN: the `setFilters` `>=2` gate specifically driven through the `FilterRibbon` UI (my test exercises the empty-state + sidebar paths, not a FilterRibbon-originated tag toggle), plus pl-PL visual baselines. Fold the remaining FilterRibbon round-trip into the E47 facet-surface suite.
- source_spec: `_bmad-output/implementation-artifacts/spec-44-2-filterribbon.md`
  summary: `validateSearch` dedupes `tag_ids` case-sensitively while validating them case-insensitively, so a hand-crafted URL repeating one UUID in two letter-cases counts as 2 tags and lets `tag_match=any` persist for a single logical tag.
  evidence: In `apps/web/src/routes/catalog/index.tsx`, `UUID_RE.test` is case-insensitive but the dedupe `seen` set keys on the exact trimmed string. `[uuid, UUID]` (same id, different case) survives as two entries. Pre-existing E43 normalization behavior surfaced incidentally by 44.2's new `>=2` gate; functionally benign (backend treats `any`≡`all` for one logical tag, and canonical DB UUIDs are lowercase). Revisit alongside E43/E47 tag-id normalization hardening (case-fold the dedupe key).

## Deferred from: story 44.3 dev review (2026-07-20)

_(The page-overshoot dead-end originally recorded here was RESOLVED in the 44.3 dev-repair pass — see the spec's Review Triage Log. `CatalogList` now renders a "Back to first page" recovery action whenever `items.length === 0 && total > 0` (page past the end of a non-empty result set), covered by `CatalogList.test.tsx`. No open 44.3-specific deferrals remain.)_

## Deferred from: story 45.1 dev review (2026-07-20)

- source_spec: `_bmad-output/implementation-artifacts/spec-45-1-modelcard-untagged-chip.md`
  summary: The `/dev/components` manual-QA gallery (`apps/web/src/routes/dev/components.tsx`) has no zero-tag `ModelCard` fixture, so the new "Brak tagów"/"No tags" ghost-chip state has no dedicated lightweight inspection surface even though the sibling "no preview" placeholder state is exercised there via `thumbnail_file_id: null` on the existing fixtures.
  evidence: Both `FAKE_MODEL` and `FAKE_MODEL_2` in `apps/web/src/routes/dev/components.tsx` carry non-empty `tags` arrays; `dev.spec.ts`'s visual baseline never renders the new branch. Not required by the 45.1 spec's scope or ACs, but worth adding alongside a future dev-page touch (e.g. when 45.2/45.3 also add new card/detail states).

## Deferred from: story 45.3 dev review (2026-07-20)

- source_spec: `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md`
  summary: `EditTagsSheet`'s "+ Create" button visibility (`candidates.length === 0 && query.length > 0`) conflates "search still loading" with "genuinely zero results," so it can flash briefly while `useTags(query)` is still refetching for a query that does have matches.
  evidence: `candidates = (tags.data ?? []).filter(...)` — while `tags.isFetching` is true for a new `query` and `tags.data` still holds the previous (possibly empty) result set, the create button can render even though the in-flight request may return real matches a moment later. Pre-existing behavior, unchanged by 45.3 (only the surrounding `isAdmin &&` guard was added); not part of this story's scope.
- source_spec: `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md`
  summary: A whitespace-only search query lets the "+ Create" button render (`query.length > 0`) but `createAndSelect()` silently no-ops once the trimmed slug is empty, with no user-facing feedback that nothing happened.
  evidence: `EditTagsSheet.tsx`'s `createAndSelect()`: `const slug = query.trim()...; if (slug === "") return;` — pre-existing logic, unchanged by 45.3. A user who types only spaces and clicks "+ Create" sees no toast, no error, and no created tag.
- source_spec: `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md`
  summary: A selected tag's chip label falls back to `id.slice(0, 6)` instead of its slug if the tag was selected while matching one search query, then the search text changes to something that no longer returns that tag AND it isn't present in `detail.tags` (i.e., a newly created/selected tag not yet saved).
  evidence: `selectedLookup` is rebuilt each render from `tags.data ?? []` (the *current* query's results) plus `detail.tags`; a selected id present in neither collection has no name to display. Pre-existing `selectedLookup` construction, unchanged by 45.3.

## Deferred from: story 45.3 dev-repair review (2026-07-20)

- source_spec: `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md`
  summary: `labelOf`'s locale-fallback helper guards against an empty `name_pl` (falls back to `name_en`) but has no equivalent guard for an empty `name_en`, so a group/tag with `name_en === ""` renders a blank section/label with no fallback text.
  evidence: Identical `labelOf` expression (`preferPl && item.name_pl ? item.name_pl : item.name_en`) is independently duplicated verbatim in `FacetSidebar.tsx`, `TagGroupsSection.tsx`, and now `EditTagsSheet.tsx` — pre-existing gap in an already-shipped (45.1/45.2), already-reviewed convention, not introduced or worsened by this story. `name_en` is presumed non-empty by the same backend/DB invariant those sibling components already trust.
- source_spec: `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md`
  summary: Grouped candidate sections have no defined ordering within a section — `TagRead.group_position` ("order within the group," per its own doc comment in `api-types.ts`) is never read by the sort/filter logic, so tags within a section render in whatever order `useTags(query)` returned them.
  evidence: Confirmed via repo-wide grep that no sibling component (`FacetSidebar`, `TagGroupsSection`) reads `group_position` either — it's only ever set in test fixtures. Pre-existing architectural gap surfaced incidentally by this story (the first place a bold group header visually implies curated ordering, making it more noticeable), not caused by this diff's logic.

## Deferred from: story 46.1 dev review (2026-07-22)

- source_spec: `_bmad-output/implementation-artifacts/spec-46-1-group-list-counts.md`
  summary: `AdminTabs`'s `<nav role="tablist" aria-label={t("admin.tabs.users")}>` hardcodes the tablist's accessible name to the "Users" tab label regardless of which tab is actually active, and Story 46.1 adds a 6th tab without fixing it.
  evidence: `apps/web/src/modules/admin/AdminTabs.tsx:20` — `aria-label` is a static `t("admin.tabs.users")` call, unconditional on `activeTab`. Pre-existing since the tab component's introduction; 46.1 only appends a new `<Link>`, it doesn't touch the `aria-label` line.
- source_spec: `_bmad-output/implementation-artifacts/spec-46-1-group-list-counts.md`
  summary: `routes/admin/tag-groups.tsx`'s auth-gate branches (`isLoading` → null, `!isAuthenticated` → null, `!isAdmin` → redirect to `/`) have no automated test coverage — `TagGroupsPage.test.tsx` only mounts the bare page component, never the route wrapper.
  evidence: Same gap exists for the sibling `routes/admin/queues.tsx` (no dedicated route-level auth test either), so this is an inherited convention gap, not a novel regression — but it means the 46.1 acceptance criterion "non-admin is redirected to `/`" is only verified by manual/structural inspection, not a test.
- source_spec: `_bmad-output/implementation-artifacts/spec-46-1-group-list-counts.md`
  summary: `TagGroupsPage` has no ARIA live-region or `aria-busy` signal on loading→data or loading→error transitions, so a screen-reader user gets no announcement that content changed after the initial render.
  evidence: The skeleton is correctly `aria-hidden="true"`, but nothing else in the component tree uses `aria-live`/`aria-busy`; `QueuesPage` has the identical gap, so this is a pre-existing app-wide convention gap surfaced incidentally by this new screen, not introduced by it.
