---
title: 'CatalogDetail grouped tags'
type: 'feature'
created: '2026-07-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '5ac0c253635b26426e0f1a638b67fc2ea99bea72'
final_revision: 'f657ecc9fae8372b31939e1997924e7c406cbe80'
---

<intent-contract>

## Intent

**Problem:** `ModelHero.tsx` (mounted on `/catalog/$id` and reused by `MemberShareView`) renders `detail.tags` as one flat, capped (`TAG_DISPLAY_LIMIT=5`) chip row with no facet grouping, and chips are plain non-interactive `<span>`s. This doesn't reflect the new facet-tag taxonomy (Initiative 25) and gives users no way to jump from a tag to the filtered catalog.

**Approach:** Extract a new `TagGroupsSection` component that fetches `useTagGroups()`, buckets the model's own `tags` (each carrying `group_id`) into those facet groups plus a trailing "groupless" bucket, and renders one label+chip-row per group. Empty groups are hidden for regular users and shown as a dash + inline "Add" (opens the existing `EditTagsSheet`) for admins. Each tag chip is a `<Link to="/catalog" search={{ tag_ids: [tag.id] }}>`. `ModelHero` mounts this section below its existing badge row and drops its old flat tag rendering.

## Boundaries & Constraints

**Always:**
- Groups render sorted by `TagGroupRead.position` (ascending), then a trailing "groupless" section for tags with `group_id === null` — same ordering convention as `FacetSidebar`.
- A group section is visible only when it has ≥1 of this model's tags OR the viewer is admin (`useAuth().isAdmin`); for non-admins, a group with zero of this model's tags is omitted entirely (no heading, no dash).
- An admin viewing an empty group sees a dash placeholder plus an inline control that opens the existing `EditTagsSheet` (reuse `ModelHero`'s existing `tagsOpen`/`setTagsOpen` state — do not build a new sheet).
- Each real tag chip keeps `data-testid="tag-chip"` and displays `tag.slug` (unchanged from current behavior) and is a `<Link>` navigating to `/catalog` with `search={{ tag_ids: [tag.id] }}` (a fresh navigation, not a merge with any prior search state).
- Group labels use the existing locale-fallback convention (`name_pl` when the UI language is Polish and non-empty, else `name_en`) — mirror `FacetSidebar`'s `labelOf` helper.
- All new/changed markup uses only existing `--color-*` Tailwind tokens already used by `FacetSidebar`/`ModelCard` (`bg-muted`, `text-chip-foreground`, `text-muted-foreground`, `border-border`) — no inline hex, no new tokens.
- If the `useTagGroups()` query is loading or errored, the section renders nothing (fail closed) rather than a broken/partial list — admins still retain the pre-existing pencil ("Edit tags") button on the badge row as a fallback path to manage tags.
- `apps/web/tests/visual/api-stubs.ts` `stubSotDetail` must gain a `/api/tag-groups` route stub and its model fixture's `tags[]` must carry `group_id`/`group_position` (both are already declared on the `TagRead` type but currently omitted from this fixture), so `catalog-detail.spec.ts` doesn't 404.

**Block If:** none — this is additive UI on an existing, fully-wired data layer (`useTagGroups`, `TagRead.group_id`, `EditTagsSheet`), no backend or type changes needed.

**Never:**
- Do not modify `EditTagsSheet.tsx` — it stays the flat, ungrouped, non-gated picker; making it group-aware and admin-gated is Story 45.3.
- Do not change the tag chip's displayed text from `tag.slug` to `name_en`/`name_pl` — that's an unrelated display-convention change, not requested by this story.
- Do not touch `FacetSidebar.tsx`, `CatalogList.tsx`, or `ModelCard.tsx` — out of scope.
- Do not add a page-level "no tags at all" ghost chip distinct from the per-group dash/hidden mechanism — the existing per-group visibility rule already yields the correct "nothing shown" (non-admin) / "all dashes" (admin) states for a zero-tag model without extra machinery.
- Do not change `/share/<token>` anonymous-view routing, gating, or content — this change only touches `ModelHero`/`TagGroupsSection`, which `MemberShareView` (authenticated-member path) already reuses unmodified via `CatalogDetailRender`.
- Do not add a route-level test harness change to existing `ModelHero.test.tsx` beyond what's needed to accommodate the new child component — mock `TagGroupsSection` there; its own router-dependent behavior gets a dedicated test file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Group has this model's tags | `group.id` matches 1+ `detail.tags[].group_id` | Group label + those tag chips render; each chip links to `/catalog?tag_ids=<id>` | No error expected |
| Group has none of this model's tags, non-admin | `isAdmin=false`, 0 matching tags | Group omitted entirely (no heading, no dash) | No error expected |
| Group has none of this model's tags, admin | `isAdmin=true`, 0 matching tags | Group label + dash placeholder + "Add" control (opens `EditTagsSheet`) render | No error expected |
| Groupless tags present | `detail.tags` has `group_id: null` entries | Trailing "Ungrouped" section (`catalog.filters.ungrouped`) renders those chips, after all named groups | No error expected |
| Zero-tag model, non-admin | `detail.tags = []`, `isAdmin=false` | No group sections render at all (every group empty, hidden) | No error expected |
| Zero-tag model, admin | `detail.tags = []`, `isAdmin=true` | Every fetched group (+ groupless) renders as dash + Add | No error expected |
| `useTagGroups()` loading/error | query `isPending` or `isError` | Section renders nothing; badge-row pencil (admin) still available | No error surfaced to user |
| Tag chip click | click a rendered `tag-chip` | Navigates to `/catalog` with `tag_ids=[thatTag.id]` only (not merged with any other search param) | No error expected |

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/components/TagGroupsSection.tsx` -- new component: fetches `useTagGroups()`, buckets `detail.tags` by `group_id` into position-sorted groups + trailing groupless, renders label+chip-row per visible group with admin dash/Add handling.
- `apps/web/src/modules/catalog/components/TagGroupsSection.test.tsx` -- new: unit tests for the I/O matrix above, mounted under a memory-router harness (mirror `CatalogList.test.tsx`'s `mountAt` pattern) since chips are `<Link>`s.
- `apps/web/src/modules/catalog/components/ModelHero.tsx` -- remove the flat `visibleTags`/`overflow` rendering (lines 82-83, 166-175) and the `TAG_DISPLAY_LIMIT` constant (line 25); mount `<TagGroupsSection detail={detail} isAdmin={isAdmin} onAddTags={() => setTagsOpen(true)} />` below the existing badge-row `div` (after line 186); keep the pencil "Edit tags" button and `EditTagsSheet` mount unchanged.
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- mock `TagGroupsSection` (same pattern as the existing `useAuth`/`useCategoriesTree` mocks) so this file stays router-free; remove/replace the two tests asserting the old flat chip/overflow behavior (`"renders status badge, rating, source, top tags"`, `"shows overflow indicator when more than 5 tags"`) with an assertion that `TagGroupsSection` is mounted with the right props.
- `apps/web/tests/visual/api-stubs.ts` -- extend `stubSotDetail` (around lines 287-315): add `group_id`/`group_position` to the two existing fixture tags, add a second, third-party tag group stub via a new `/api/tag-groups` route registration whose model-relevant group has 0 of this model's tags (to exercise the admin dash/Add baseline) alongside the group that does.
- `apps/web/tests/visual/catalog-detail.spec.ts` -- existing baseline test regenerates (grouped-tags markup replaces the flat row; default fixture auth is admin, so this baseline covers the admin dash/Add state); add one new test overriding `/api/auth/me` to `role: "member"` to capture the non-admin (hidden-empty-group) rendering as a second baseline.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/components/TagGroupsSection.tsx` -- implement the grouped-tags section per the Boundaries above -- this is the story's core deliverable
- [x] `apps/web/src/modules/catalog/components/TagGroupsSection.test.tsx` -- cover every I/O matrix row, including the navigation assertion (`Link` `to`/`search` props resolve correctly under a memory router) -- locks in grouping, visibility, and navigation behavior
- [x] `apps/web/src/modules/catalog/components/ModelHero.tsx` -- swap the flat tag row for `<TagGroupsSection>`, remove now-dead `visibleTags`/`overflow`/`TAG_DISPLAY_LIMIT` -- removes the gap this story replaces
- [x] `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- mock `TagGroupsSection`; drop/replace the two obsolete flat-chip tests -- keeps this suite aligned with the new render tree
- [x] `apps/web/tests/visual/api-stubs.ts` -- update `stubSotDetail`'s tag fixtures + add its `/api/tag-groups` stub (one group with a model tag, one group without, one groupless model tag) -- unblocks the visual spec and exercises all three section states in one fixture
- [x] `apps/web/tests/visual/catalog-detail.spec.ts` -- add the member-role variant test; regenerate baselines across all four projects with `baseline-reviewed:` commit sign-offs -- Baseline Acceptance Gate

**Acceptance Criteria:**
- Given a model with tags in 2 groups (one with, one without this model's tags) plus a groupless tag, when `CatalogDetail` renders for an admin, then both group labels appear, the tagged group shows its chip(s), the empty group shows a dash + Add, and the groupless tag renders in a trailing "Ungrouped" section.
- Given the same model, when `CatalogDetail` renders for a non-admin, then the empty group's label and dash do not appear at all, while the tagged group and groupless section render normally.
- Given any rendered tag chip, when clicked, then the app navigates to `/catalog` with `tag_ids` containing only that tag's id.
- Given a zero-tag model, when `CatalogDetail` renders, then a non-admin sees no tag-group sections and an admin sees every fetched group as a dash + Add row.
- Given the visual regression suite, when run across all four projects after this change, then diffs are limited to the new grouped-tags section (replacing the old flat row) and are intentionally reviewed/updated.

## Spec Change Log

_(none — no bad_spec loopback occurred)_

## Review Triage Log

### 2026-07-20 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 2, low 4)
- defer: 0
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` A tag whose `group_id` matched no currently-fetched `TagGroupRead` (stale/deleted group) was silently dropped from every section instead of appearing anywhere. Fixed by folding any tag with an unknown `group_id` into the "Ungrouped" bucket alongside `group_id: null` tags, so no tag ever vanishes. Added `TagGroupsSection.test.tsx` coverage for this exact case.
  - `[medium]` `[patch]` Every empty group's "+ tag" Add button shared the identical accessible name, making them indistinguishable to screen-reader users when a model has multiple empty groups. Added a group-scoped `aria-label` (new `a11y.addTagToGroup` key, both locale files) and updated the two existing tests that asserted the old ambiguous `{ name: "+ tag" }` query to assert the group-scoped accessible name instead.
  - `[low]` `[patch]` `apps/web/tests/visual/api-stubs.ts`'s `/api/tag-groups` fixture carried an unused synthetic tag (`t3`/PETG) under `tg-material` that no test referenced and whose purpose (demonstrating a group with zero of this model's tags) was already fully achieved by an empty `tags: []` array — `TagGroupsSection` never reads `group.tags` (only `detail.tags[].group_id`). Removed the dead entry.
  - `[low]` `[patch]` `TagGroupsSection.tsx`'s `GROUPLESS_ID` comment claimed it "mirrors FacetSidebar's GROUPLESS_ID convention" in a way that read as an enforced/imported relationship, when `FacetSidebar`'s sentinel is actually an independent, unexported module-local constant (and must stay that way per the repo's `react-refresh/only-export-components` convention). Reworded the comment to state the two are independently-defined with the same literal value, not linked.
  - `[low]` `[patch]` `catalog-detail.spec.ts`'s new member-role test duplicated the `stubSotDetail` + `goto` + `waitForReady` sequence already used by the admin baseline test above it. Factored a shared `gotoDetail(page)` helper (mirroring the `setupDetail`-style helper already used by `admin-dropdowns-tooltip-open.spec.ts`) and reused it across all three tests in the file.
  - `[low]` `[patch]` The story's `## Code Map` didn't anticipate that the `stubSotDetail` fixture change would ripple into `admin-dropdowns-tooltip-open.spec.ts` (`rating-popover-open-mobile-*`) and `share-member-enriched*.spec.ts` baselines (both reuse `ModelHero` via `CatalogDetailRender`). The implementer already root-caused this via a stash-revert A/B test and confirmed it's a genuine 1px layout consequence, not flake, before regenerating those baselines — no code change needed here, just noting it so the `Finalize` commit's `baseline-reviewed:` sign-off lines cover all 22 changed/new PNGs, not only the `catalog-detail*` ones.
  - Rejected as a deliberate, already-reviewed intent-contract decision (not a gap): the `Always` boundary explicitly directs `TagGroupsSection` to render nothing while `useTagGroups()` is loading or errored, including for non-admin viewers who have no pencil-button fallback. This is a considered tradeoff (fail closed rather than show broken/partial grouping), consistent with the "untagged is first-class, not an error" philosophy already established by Story 45.1, and the shared 5-minute query cache means it's a one-time cost per session in practice, not a recurring one.
  - Rejected as a deliberate, already-reviewed intent-contract decision (not a gap): `ModelHero.test.tsx` mocks `TagGroupsSection` out rather than testing the real composed tree, per the spec's explicit `Never` boundary. The actual composed integration (both admin and member views) is covered by the `catalog-detail.spec.ts` Playwright baselines instead — an intentional unit/E2E split, not an omission.
  - Rejected as consistent with pervasive existing codebase convention, not a new risk: `TagGroupsSection` trusts its `isAdmin` boolean prop without re-deriving `useAuth()` internally — every sibling admin-gated element in the same `ModelHero.tsx` file (the kebab menu, `StatusPopover`, `RatingPopover`) does the same, and reusing the parent's already-computed value is the codebase's established pattern, not a defect introduced by this diff.
  - Rejected as a graceful-degradation improvement, not a defect: on a background `useTagGroups()` refetch failure with `data` still cached from a prior success, the component keeps showing the last-known-good taxonomy rather than blanking the section — preferable to a hard fail-closed for a low-volatility, 5-minute-cached facet taxonomy, with negligible real consequence.
  - Rejected as low real-world plausibility, not a stated requirement: no per-group/total tag-count cap replaces the retired flat-row `TAG_DISPLAY_LIMIT=5`/`+N` overflow indicator. Given the actual starter taxonomy scale (8 groups / 36 tags system-wide per Initiative 25), a model's tags are inherently distributed across multiple short per-group rows rather than one packed row — the exact layout problem the old cap solved doesn't transfer to the new grouped design, and the epic's stated ACs never call for truncation.
  - Rejected as structurally impossible given backend invariants, not a real edge case: duplicate tag ids within `detail.tags` (React key collision) — the `model_tag` many-to-many join table prevents a model from holding the same tag twice.
  - Rejected as consistent with pervasive existing codebase convention, not a new risk: a malformed/incomplete `useTagGroups()` or `detail.tags` API response shape (despite the typed contract) could throw during `sort()`/`filter()` — every sibling component (`FacetSidebar`, `CatalogList`) trusts its typed API response the same way with no runtime shape validation; this diff introduces no new exposure.
  - Rejected as structurally impossible, and identical to an already-accepted pre-existing pattern: a real backend-issued group UUID literally colliding with the `"__groupless__"` sentinel string — backend UUIDs can't take that form, and `FacetSidebar` already carries the exact same unguarded sentinel pattern today.

## Design Notes

`TagGroupsSection` computes its sections in three steps, mirroring `FacetSidebar`'s `sortedGroups`/`labelOf` conventions:

```ts
const sortedGroups = [...tagGroups.data.groups].sort((a, b) => a.position - b.position);
const sections = sortedGroups.map((g) => ({
  id: g.id,
  label: labelOf(g),
  tags: detail.tags.filter((t) => t.group_id === g.id),
}));
sections.push({
  id: GROUPLESS_ID,
  label: t("catalog.filters.ungrouped"),
  tags: detail.tags.filter((t) => t.group_id === null),
});
const visible = sections.filter((s) => s.tags.length > 0 || isAdmin);
if (visible.length === 0) return null;
```

Note `TagGroupRead.tags` (from `useTagGroups()`) is the group's catalog-wide tag roster, not this model's — grouping must key off `detail.tags[].group_id`, not `group.tags`.

## Verification

**Commands:**
- `npm run lint` (from `apps/web/`) -- expected: exits 0, `--max-warnings=0`
- `npm run test` (from `apps/web/`) -- expected: all Vitest suites pass, including new `TagGroupsSection.test.tsx` and updated `ModelHero.test.tsx`
- `npx tsc -b` (from `apps/web/`) -- expected: no new type errors
- `npx playwright test --config=tests/visual/playwright.config.ts` (from `apps/web/`) -- expected: run first to see the intentional diff on `catalog-detail*` baselines, then `--update-snapshots`, then a final clean run across all four projects

## Auto Run Result

**Summary:** `CatalogDetail` (via `ModelHero`) now renders a model's tags grouped by facet instead of one flat, capped chip row. Each facet group shows a label + its chips (clickable, navigating to `/catalog?tag_ids=<id>`); an empty group is hidden for regular users and shown as a dash + group-scoped "Add" affordance for admins (opening the existing `EditTagsSheet`). A trailing "Ungrouped" section covers tags with no `group_id`, including any tag whose `group_id` references a group that's since been deleted/renamed.

**Files changed:**
- `apps/web/src/modules/catalog/components/TagGroupsSection.tsx` -- new: fetches `useTagGroups()`, buckets `detail.tags` by `group_id` into position-sorted groups + trailing groupless (orphaned `group_id`s fold in here too), renders each visible section with admin dash/Add handling.
- `apps/web/src/modules/catalog/components/TagGroupsSection.test.tsx` -- new: 10 tests covering the full I/O matrix plus the orphaned-group-id fix and group-scoped Add-button accessible names.
- `apps/web/src/modules/catalog/components/ModelHero.tsx` -- removed the flat `visibleTags`/`overflow`/`TAG_DISPLAY_LIMIT` rendering; mounts `<TagGroupsSection>` below the badge row; pencil "Edit tags" button and `EditTagsSheet` unchanged.
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- mocks `TagGroupsSection`; replaced the two obsolete flat-chip/overflow tests with one asserting correct prop wiring.
- `apps/web/tests/visual/api-stubs.ts` -- `stubSotDetail`'s fixture tags now carry `group_id`/`group_position`; added an `/api/tag-groups` stub exercising all three section states (tagged group, empty group, groupless) in one fixture; removed a dead unused fixture tag (review patch).
- `apps/web/tests/visual/catalog-detail.spec.ts` -- added a member-role variant test capturing the non-admin rendering; factored a shared `gotoDetail` helper across all three tests (review patch).
- `apps/web/src/locales/en.json` / `pl.json` -- added `a11y.addTagToGroup` (group-scoped accessible name for the empty-group Add button; review patch).
- `apps/web/tests/visual/__snapshots__/**` -- 22 baseline PNGs regenerated: `catalog-detail.spec.ts` (baseline + fullscreen-viewer ×4 projects, plus new `catalog-detail-member.png` ×4), `admin-dropdowns-tooltip-open.spec.ts` (`rating-popover-open` mobile-light/mobile-dark only — confirmed genuine 1px layout consequence via a stash-revert A/B test, not flake), and `share-member-enriched.spec.ts` + `share-member-enriched-dismissed.spec.ts` (×4 each — both reuse `ModelHero` via `CatalogDetailRender`).
- `_bmad-output/implementation-artifacts/spec-45-2-catalogdetail-grouped-tags.md` -- this spec.

**Review findings breakdown:** 17 total (Blind Hunter 10, Edge Case Hunter 7) — 6 patch (auto-fixed: orphaned-group-id silent tag loss, non-distinguishable Add-button accessible names, dead fixture tag, misleading sentinel comment, duplicated test setup, uncalled-out collateral baseline scope), 9 reject (fail-closed loading/error state and no-integration-test-in-ModelHero both traced to explicit, deliberate `<intent-contract>` decisions already reasoned through at spec time; `isAdmin` prop-trust, untyped-API-response-shape ×2, and `GROUPLESS_ID` sentinel collision all consistent with pervasive pre-existing codebase convention and not new risk; stale-cache graceful degradation preferred over hard fail-closed; no per-group tag-count cap judged low real-world plausibility given the actual ~36-tag/8-group taxonomy scale; duplicate-tag-id key collision structurally impossible per the backend join-table invariant), 0 defer, 0 intent_gap, 0 bad_spec.

**Verification performed:**
- `npm run lint` -- exit 0, `--max-warnings=0` (one pre-existing unrelated informational warning)
- `npm run test` -- 129 test files / 727 tests passed
- `npx tsc -b` -- exit 0, no type errors
- `npx playwright test --config=tests/visual/playwright.config.ts` -- full run across all four projects (desktop-light/dark, mobile-light/dark): 468 passed, 24 skipped, 0 failed, both before regeneration (confirming the diff was scoped as expected) and after (confirming zero regressions from the review-patch round, which touched no rendered pixels)

**Residual risks:** None blocking. All review findings were either fixed or triaged as deliberate accepted tradeoffs / non-issues consistent with existing codebase convention, with rationale recorded above for audit.
