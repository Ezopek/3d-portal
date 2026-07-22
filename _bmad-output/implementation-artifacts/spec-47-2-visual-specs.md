---
title: 'Story 47.2 — Facet-surface Playwright visual specs (sidebar, ribbon, AND-too-narrow empty state)'
type: 'chore'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'b1fe7393818bb315db066713b1d61d7b28f42b0f'
final_revision: '716cd2b809bfb31b617bddfb541070723dec5760'
---

<intent-contract>

## Intent

**Problem:** The facet-tag catalog rebuild (E41-E46) shipped `FacetSidebar`, `FilterRibbon`'s tag chips/match-mode toggle/tag-picker, and the AND-too-narrow empty state, but no Playwright visual spec exercises their groupless/untagged/collapsed/match-mode-toggle states. `catalog-list.spec.ts` only renders a 1-group, no-groupless, no-untagged fixture; `filter-ribbon-selects-open.spec.ts` covers only the non-tag Selects. `TagGroupsSection` (grouped detail) and the admin governance screen already have adequate dedicated coverage (`catalog-detail.spec.ts`, `admin-tag-groups.spec.ts`) and are out of scope here.

**Approach:** Add one new spec, `facet-filtering.spec.ts`, covering: FacetSidebar's default-expanded/collapsed/groupless/untagged-checkbox states; FilterRibbon's tag-picker popover and UI-driven (not URL-preset) two-tag selection that reveals the match-mode toggle — closing the `deferred-work.md` "FilterRibbon-UI-driven >=2 gate" item; and the AND-too-narrow `EmptyState`. Consolidate the mocks these tests need into the existing shared `stubSotList` helper via an optional fixture-override param, rather than registering a fourth duplicate `/api/tags`/`/api/tag-groups` handler.

## Boundaries & Constraints

**Always:** Every new screenshot is preceded by a `toBeVisible()`/visible-text assertion on the concrete rendered state (Epic 45/46 test-authoring rule; explicitly reinforced for this story by the E47 47.2 action item). All new text matchers use the actual pl-PL strings in `pl.json` (harness forces `pl-PL`). Reuse `stubSotList`'s new optional override rather than a duplicate route handler. Sidebar-only tests (desktop element is `hidden` below `lg`) use the established `skipOnMobile` pattern from `filter-ribbon-selects-open.spec.ts`.

**Block If:** If giving `stubSotList` an optional `opts` param cannot be made byte-for-byte behavior-preserving for its 18 existing zero-arg call sites, HALT with status `blocked`, blocking condition `stubSotList consolidation changes existing spec behavior`.

**Never:** Do not modify `Model`/`Tag`/`TagGroup` ORM, routes, or services — test-only story. Do not add new i18n keys (47.1 already closed that scope); if a needed pl-PL string is missing, HALT rather than inventing one. Do not retrofit `toBeVisible()` into pre-existing specs lacking it (`catalog-list.spec.ts`, `catalog-detail.spec.ts`) — out of this story's boundary. Do not touch `admin-tag-groups.spec.ts`, `catalog-detail.spec.ts`, or `destructive-dialogs-edit-sheets-open.spec.ts`'s intentionally-local `stubTagCandidates` — already adequate / a deliberate prior decision, not this story's to revisit.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sidebar default | 3 groups + groupless, no persisted collapse state | First 2 groups (by `position`) expanded with tag rows; 3rd group + groupless section collapsed (chevron-right) | N/A |
| Sidebar group toggle | Click collapsed group's header | Group expands, its tag row becomes visible | N/A |
| Sidebar untagged | `/catalog?untagged=true` | "Modele bez tagów" checkbox renders checked | N/A |
| Ribbon tag-picker | 0 tags selected, click "+ tag" | `role="dialog"` picker opens listing all fixture tags | N/A |
| Ribbon match-mode reveal | Pick 2 tags one-by-one through the picker UI | 2 `tag-chip` elements render; match-mode toggle group becomes visible | N/A |
| AND-too-narrow | 2 `tag_ids` selected, `/api/models*` returns `total: 0` | `EmptyState` renders "Przełącz na dowolne" + "Wyczyść filtry" | N/A |

</intent-contract>

## Code Map

- `apps/web/tests/visual/api-stubs.ts` -- `stubSotList` currently hardcodes its `/api/tags*` and `/api/tag-groups*` fixtures inline (lines ~158, ~177); extract to module-level `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS` constants and add an optional `opts: { tags?: TagListItem[]; tagGroups?: TagGroupsResponse }` param (default = the extracted constants) so new specs can supply richer fixtures through the same handler.
- `apps/web/src/modules/catalog/components/FacetSidebar.tsx` -- read-only reference: `DEFAULT_EXPANDED_GROUP_COUNT=2`, `GROUPLESS_ID` sentinel, untagged checkbox (line ~176-190), `a11y.expand`/`a11y.collapse` aria-labels on group headers.
- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` -- read-only reference: tag chips (`data-testid="tag-chip"`, line 81), "+ tag" button opening `TagPicker` (`role="dialog"`, aria-label `catalog.tags.pickerTitle`), match-mode `role="group"` toggle shown only at `tag_ids.length >= 2` (line 114).
- `apps/web/src/routes/catalog/index.tsx` -- read-only reference: `UUID_RE` — URL `tag_ids` must be canonical UUIDs or `validateSearch` silently drops them; fixture tag ids for URL-driven tests must be UUID-shaped.
- `apps/web/tests/visual/facet-filtering.spec.ts` -- new file; the six-test suite described in Design Notes.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- the "Deferred from: story 44.2 dev repair review" entry's `status:` line lists two STILL-OPEN sub-items (FilterRibbon-UI-driven `>=2` gate, pl-PL visual baselines) that this story closes; append a resolution note.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/tests/visual/api-stubs.ts` -- extract existing `/api/tags*`/`/api/tag-groups*` fixtures to `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS`, add optional `opts` param to `stubSotList` -- lets the new spec supply a 3-group+groupless+UUID-id fixture without a duplicate handler (NFR25-VISUAL-1 consolidation clause), zero behavior change for existing call sites
- [x] `apps/web/tests/visual/facet-filtering.spec.ts` -- new file, six tests: sidebar default (2 expanded/1 collapsed/groupless collapsed), sidebar group-expand click, sidebar untagged-checkbox via `?untagged=true`, tag-picker open (0 tags), UI-driven 2-tag selection revealing match-mode toggle, AND-too-narrow empty state -- closes the sidebar/ribbon/untagged-state gap `catalog-list.spec.ts` and `filter-ribbon-selects-open.spec.ts` leave open
- [x] Generate + visually review baselines: `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts facet-filtering.spec.ts --update-snapshots` -- new spec has no prior baseline
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- append a resolution note to the story-44.2-dev-repair-review entry recording that `facet-filtering.spec.ts` closes both STILL-OPEN sub-items -- keeps the ledger truthful (spec-47-1's repair pass set this precedent)

**Acceptance Criteria:**
- Given `/catalog` stubbed with the 3-group+groupless fixture, when the page loads, then groups 1-2 (by `position`) render expanded with tag rows and group 3 renders collapsed, before any screenshot.
- Given the collapsed 3rd group, when its header is clicked, then it expands and its tag row is `toBeVisible()` before the screenshot.
- Given `/catalog?untagged=true`, when the page loads, then the untagged checkbox is checked before the screenshot.
- Given `/catalog` with 0 tags selected, when "+ tag" is clicked, then the `TagPicker` dialog is visible with all fixture tags listed before the screenshot.
- Given the picker open, when 2 tags are selected one-by-one through the UI, then 2 `tag-chip` elements and the match-mode toggle group are `toBeVisible()` before the screenshot.
- Given 2 `tag_ids` selected and `/api/models*` overridden to `total: 0`, when the page loads, then both EmptyState action buttons are `toBeVisible()` before the screenshot.
- Given `npx playwright test --config=tests/visual/playwright.config.ts facet-filtering.spec.ts`, when run, then every test passes on the projects it targets (sidebar tests: desktop-light/desktop-dark only, mobile skipped via `skipOnMobile`; ribbon/empty-state tests: all 4 projects).
- Given `stubSotList(page)` called with no `opts` (all 18 existing call sites), when its routes fulfill, then the JSON bodies are byte-for-byte identical to the pre-change hardcoded fixtures.

## Spec Change Log

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 1, low 3)
- defer: 5: (high 0, medium 2, low 3)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, deduplicated) found the "default state" sidebar test's own stated third claimed state — the groupless section rendering collapsed — was asserted nowhere before `facet-sidebar-default.png`, violating this spec's own "Always" boundary (every screenshot preceded by a visibility assertion on the concrete state captured). Added assertions for the groupless section's collapsed header (`"Rozwiń Bez grupy"` visible) and absent tag text (`"Różne"` count 0) before the screenshot; re-ran, still 18/18 green with unchanged baselines.
  - `[low]` `[patch]` Blind Hunter found `RICH_TAGS` and `RICH_FIXTURE` hand-duplicated the same 5 tags' data in two independent literals — ironic given this story's own `stubSotList`-consolidation goal, and a drift risk if one is edited without the other. Changed `RICH_TAGS` to derive from `RICH_FIXTURE.groups.flatMap(...)` + `.groupless` instead of a second hand-authored literal; re-ran, unchanged baselines confirm the derivation is equivalent.
  - `[low]` `[patch]` Blind Hunter found the "default state" test's correctness silently depends on `FacetSidebar`'s `localStorage["catalog:facet-collapse"]` starting unset (true today only because Playwright isolates browser contexts per test), undocumented. Added a comment on the `describe` block naming the assumption and the condition under which it would need re-verifying.
  - `[low]` `[patch]` Blind Hunter found the two `describe` blocks that run on all 4 projects (no `skipOnMobile`) had no comment explaining the asymmetry with the sidebar tests' desktop-only gating. Added a one-comment explanation (FilterRibbon chrome isn't viewport-gated, unlike FacetSidebar's `hidden lg:flex` `<aside>`).
  - Deferred to `deferred-work.md` (5, not this story's problem — pre-existing or genuinely future-scoped, see entries under "Deferred from: story 47.2 dev review"): `[medium]` unannotated `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS` fixture-type drift risk (pre-dates 47.2's extraction); `[medium]` `TagPicker` missing `aria-modal`/focus-trap (pre-existing since 44.2, first exercised by clicks here); `[low]` `skipOnMobile` now triplicated across 3 spec files (fixing requires touching sibling specs, out of this story's boundary); `[low]` the story-44.2 deferred-work.md entry's `status:` line growing as one unbroken paragraph across repeated amendments (pre-existing file-wide convention); `[low]` `stubSotList`'s new `opts.tags`/`opts.tagGroups` independently-optional params have no guard against a future partial-override caller producing an inconsistent fixture (not triggered by this story's own only caller).
  - Rejected as noise (3, with reasoning): the spec doc's I/O matrix "N/A" Error Handling column for every row is a template-formality nitpick with no actual behavior gap — this story is pure-rendering visual assertion, not error-handling implementation; a dedicated unit test asserting `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS` byte-for-byte preservation is over-engineering given the full 522-test visual suite already provides strong incidental protection (any edit would very likely break some existing baseline); the "group-expand" test not re-asserting groups 1-2 remain expanded / groupless remains collapsed after clicking group 3 is redundant with the "default state" test already covering that exact same fixture/URL combination — the pixel diff on `facet-sidebar-group-expanded.png` would catch a regression there too.

## Design Notes

Fixture tag ids must be canonical UUIDs (`UUID_RE` in `routes/catalog/index.tsx`), unlike existing fixtures' `"tag-1"`/`"t1"` ids, so URL-driven states (`?untagged=true` needs no ids, but a future URL-preset variant would) survive `validateSearch`. Tests 4-5 deliberately drive the 2-tag selection through actual `TagPicker` clicks rather than a `?tag_ids=...` URL preset: `deferred-work.md`'s "story 44.2 dev repair review" entry flags the `FilterRibbon`-UI-driven `setFilters` `>=2` gate as the one remaining uncovered path after `CatalogList.test.tsx`'s router-level tests (which exercise the empty-state/sidebar paths, not a ribbon-originated toggle) — this spec is the first coverage of that exact path. The 3-group fixture's group count (2 expanded, 1 collapsed by default) is a direct consequence of `FacetSidebar`'s `DEFAULT_EXPANDED_GROUP_COUNT=2` — reusing that same fixture also gives the groupless section a real collapsed-by-default row for free.

## Verification

**Commands:**
- `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts facet-filtering.spec.ts` -- expected: all tests pass across their targeted projects (no `--update-snapshots`, i.e. baselines match)
- `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` -- expected: full suite green, no regressions from the `stubSotList` signature change (18 existing call sites unaffected)
- `cd apps/web && npx vitest run` -- expected: unaffected, all pass (no application source code touched)
- `cd apps/web && npm run lint` -- expected: 0 warnings

## Auto Run Result

Status: done

**Summary:** Added `apps/web/tests/visual/facet-filtering.spec.ts`, a new 6-test Playwright visual-regression spec covering the facet-tag catalog rebuild's (E41-E46) previously-untested UI states: `FacetSidebar`'s default-expanded/collapsed-group/groupless-section/untagged-checkbox states, `FilterRibbon`'s tag-picker popover and a UI-driven (real clicks, not a URL preset) two-tag selection that reveals the match-mode toggle, and the AND-too-narrow `EmptyState`. The UI-driven match-mode test specifically closes a `deferred-work.md` item from story 44.2's dev-repair review that named this as the one remaining uncovered `FilterRibbon`-originated path. `stubSotList` in `api-stubs.ts` was extended with an optional fixture-override param (byte-for-byte behavior-preserving for its 18 existing call sites) so the new spec's richer 3-group+groupless+UUID-id fixture reuses the shared route handler instead of registering a fourth duplicate mock, satisfying NFR25-VISUAL-1's consolidation clause. `TagGroupsSection` (grouped detail) and the admin governance screen already had adequate dedicated coverage (`catalog-detail.spec.ts`, `admin-tag-groups.spec.ts`) and were left untouched per the epic's own coordination note.

**Files changed:**
- `apps/web/tests/visual/api-stubs.ts` -- `stubSotList` gained an optional `opts: { tags?: TagListItem[]; tagGroups?: TagGroupsResponse }` param; existing hardcoded fixtures extracted to `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS` module constants as the default
- `apps/web/tests/visual/facet-filtering.spec.ts` (new) -- 6 tests, 18 new baseline PNGs under `__snapshots__/facet-filtering.spec.ts/`
- `_bmad-output/implementation-artifacts/deferred-work.md` -- resolved the story-44.2 dev-repair-review entry's two STILL-OPEN sub-items; appended 5 new deferred entries from this story's own review pass (fixture-type-drift risk, `TagPicker` a11y gap, `skipOnMobile` triplication, ledger-entry growth, `stubSotList` partial-override footgun)
- `_bmad-output/implementation-artifacts/spec-47-2-visual-specs.md` (new) -- this spec

**Review findings breakdown:** 4 patch (1 medium — the "default state" test's own claimed groupless-section state was unasserted before its screenshot, violating the story's own test-authoring rule; 3 low — `RICH_TAGS`/`RICH_FIXTURE` duplicate-literal drift risk fixed by deriving one from the other, two documentation comments added), 5 deferred (2 medium — unannotated fixture-type drift risk pre-dating this story's extraction, `TagPicker`'s pre-existing missing `aria-modal`/focus-trap now first exercised by real clicks; 3 low — `skipOnMobile` now triplicated across 3 spec files, `deferred-work.md`'s per-entry single-line growth convention, `stubSotList`'s new opts params being independently optional), 3 rejected as noise (I/O matrix "N/A" Error Handling formality, redundant fixture-preservation unit-test suggestion given the full suite's incidental protection, a redundant re-assertion suggestion already covered by an existing test + the pixel diff).

**Verification performed:** All 18 new baseline PNGs visually inspected directly (not just pixel-diffed) across both light/dark and desktop/mobile variants — confirmed sidebar group-expand/collapse, untagged-checkbox, tag-picker option list, match-mode toggle, and AND-too-narrow empty-state actions all render as designed in both themes. Ran and confirmed green: `facet-filtering.spec.ts` alone (18 passed, 6 correctly skipped on mobile, stable without `--update-snapshots`), the full visual suite (522 passed, 30 skipped, 0 failed), `npx vitest run` (788 passed, 136 files), `npx tsc -b` (clean), `npm run lint` (0 warnings). Re-ran the full visual suite a second time after applying the 4 review patches to confirm no regression.

**Residual risks:** None blocking. The 5 deferred items are either pre-existing (fixture-type-drift, `TagPicker` a11y gap, `deferred-work.md` line-growth convention) or latent/untriggered (`skipOnMobile` triplication, `stubSotList`'s partial-override footgun) — none affect this story's own correctness.
