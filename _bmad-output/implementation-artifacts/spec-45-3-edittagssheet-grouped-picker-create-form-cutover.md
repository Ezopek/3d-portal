---
title: 'EditTagsSheet grouped picker + create-form cutover'
type: 'feature'
created: '2026-07-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'bfab5fae01b8da9335d11b7c95208b01897f6c8a'
context: []
warnings: ['oversized']
baseline_revision: '195a8e47d47d4b63abc47774f5a42a842cd01d1f'
---

<intent-contract>

## Intent

**Problem:** `EditTagsSheet.tsx` renders its candidate-tag list as one flat, ungrouped search result and lets any viewer create a new tag inline — it predates the facet-tag taxonomy (Initiative 25) and doesn't gate tag creation to admins at the component level.

**Approach:** Group the sheet's search candidates by facet (fetch `useTagGroups()`, bucket by `TagListItem.group_id`, sorted by `TagGroupRead.position` + trailing "Ungrouped"), mirroring `FacetSidebar`/`TagGroupsSection`'s established grouping convention. Add an `isAdmin` prop (parent-computed, passed through like `TagGroupsSection` already does) and hide the "create new tag" affordance — and skip calling `useCreateTag` — whenever it's false. The admin create-form category-selector removal (the other half of this story's title) is deferred per the 45.3↔47.5 handshake recorded in `epic-45-context.md` and is explicitly out of scope for this pass.

## Boundaries & Constraints

**Always:**
- Candidate tags (from `useTags(query)`, filtered to exclude already-selected ids — unchanged) render bucketed into sections: one per `TagGroupRead` (sorted by `position` ascending) whose bucket is non-empty, then a trailing "Ungrouped" section (`t("catalog.filters.ungrouped")`) for candidates whose `group_id` is `null` or references a group absent from the current `useTagGroups()` response (orphaned) — mirror `TagGroupsSection`'s orphan-folding behavior so no candidate silently disappears. A section with zero candidates is omitted (this is a picker, not a taxonomy browser — no admin-only empty-section display here, unlike `TagGroupsSection`).
- Section labels use the existing locale-fallback convention (`name_pl` when the UI language is Polish and non-empty, else `name_en`), mirroring `FacetSidebar`'s `labelOf` helper.
- If `useTagGroups()` has no data yet (`isPending` or `isError`), candidates render as the current flat, header-less list instead of hiding them — the sheet's core select/save flow must keep working even if facet metadata fails to load (this differs deliberately from `TagGroupsSection`'s fail-closed convention, which has a fallback pencil button; this sheet, once open, has none).
- Accept a new required `isAdmin: boolean` prop. The "create new tag" button/affordance (currently shown when `candidates.length === 0 && query.length > 0`) additionally requires `isAdmin`; when `isAdmin` is false, that branch never renders and `createAndSelect`/`useCreateTag` are never invoked, regardless of search state.
- Selected-tag chips (top-of-sheet row, remove-`×` buttons, `save()`/Cancel footer) are unchanged by this story.
- All new/changed markup uses only existing `--color-*` Tailwind tokens already used elsewhere in this file/`FacetSidebar` (`text-muted-foreground`, etc.) — no inline hex, no new tokens.

**Block If:** none — this is additive UI on an existing, fully-wired data layer (`useTagGroups`, `TagListItem.group_id`), no backend or type changes needed.

**Never:**
- Do not touch `routes/admin/models/new.tsx` or `AddModelForm.tsx` (the category-selector removal) — deferred to ship in the same `main` HEAD as story 47.5 per the recorded 45.3↔47.5 handshake; out of scope for this pass.
- Do not change `ModelHero.tsx`'s existing `isAdmin &&` gate around mounting `<EditTagsSheet>` or the pencil button that opens it — only add the new `isAdmin={isAdmin}` prop to the existing mount. Widening who can *open* the sheet is not requested.
- Do not modify `FilterRibbon.tsx`'s own `TagPicker` (the filter-ribbon "+ tag" flat picker) — unrelated component, out of scope.
- Do not add new i18n keys — group headers use `TagGroupRead.name_en`/`name_pl` directly plus the already-existing `catalog.filters.ungrouped` key; leave this file's other pre-existing hardcoded English strings (title, placeholder, buttons) untouched.
- Do not change `useTags`, `useTagGroups`, `useCreateTag`, or `useReplaceTags` — consume them as-is.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Candidates span 2 groups | search results have tags with 2 distinct known `group_id`s | Two group sections render, each with its label + matching chips, ordered by group `position` | No error expected |
| Candidate with `group_id: null` | 1+ candidate has `group_id === null` | Trailing "Ungrouped" section renders those candidates | No error expected |
| Candidate with orphaned `group_id` | candidate's `group_id` doesn't match any group in `useTagGroups()` data | Candidate folds into the "Ungrouped" section, not dropped | No error expected |
| `useTagGroups()` loading/error | query `isPending` or `isError` | Candidates render as today's flat, header-less list | No error surfaced to user |
| Admin, no candidates + query typed | `isAdmin=true`, `candidates.length===0`, `query!==""` | "+ Create" button renders; clicking it calls `useCreateTag` | No error expected |
| Non-admin, no candidates + query typed | `isAdmin=false`, `candidates.length===0`, `query!==""` | No "+ Create" affordance renders at all; `useCreateTag` never invoked | No error expected |
| Non-admin, candidates present | `isAdmin=false` | Grouped candidate sections render and remain selectable identically to admin | No error expected |

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.tsx` -- add `isAdmin` prop; fetch `useTagGroups()`; bucket `candidates` into position-sorted group sections + trailing "Ungrouped" (falling back to the current flat list when tag-groups data isn't loaded); gate the "+ Create" button/`createAndSelect`/`useCreateTag` call behind `isAdmin`.
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` -- this story's `EditTagsSheet` now fires `useTagGroups()` concurrently with the existing `useTags()` query on every mount, so the two existing `"calls useReplaceTags..."` tests (which assert on `fetchMock.mock.calls[0]`/`[1]` by call *index*, expecting exactly one query fetch before the Save click) will break — switch `fetchMock`'s implementation to dispatch by requested path/URL (e.g. `fetchMock.mockImplementation((url) => ...)` keyed on whether `url` contains `/tags`, `/tag-groups`, or `/admin/models/`) instead of positional `mockResolvedValueOnce` calls, then reassert the Save-click PUT request by matching its path rather than by array index. Add coverage for the I/O matrix above (grouped rendering, orphan folding, loading fallback, admin vs non-admin create-affordance gating) on top of that.
- `apps/web/src/modules/catalog/components/ModelHero.tsx` -- pass `isAdmin={isAdmin}` to the existing `<EditTagsSheet>` mount (line ~177); no other change.
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- this file's `beforeEach` default (`fetchMock.mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }))`) returns a bare `[]` for every unmatched request; that's array-shaped (fine for `/tags`) but not a valid `TagGroupsResponse` (`{groups, groupless}`), and the two tests that mount the real `EditTagsSheet` (`"mounts TagGroupsSection..."`'s `onAddTags` click, and `"renders the edit-tags pencil..."`) will now also trigger its `useTagGroups()` call. Make the default (or a targeted override in those two tests) path-aware so `/tag-groups` resolves to `{ groups: [], groupless: [] }` instead of `[]`.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.tsx` -- implement grouped candidate sections + `isAdmin`-gated create affordance per the Boundaries above -- this is the story's core deliverable
- [x] `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` -- cover every I/O matrix row -- locks in grouping, orphan-folding, loading fallback, and admin-gating behavior
- [x] `apps/web/src/modules/catalog/components/ModelHero.tsx` -- wire `isAdmin` prop through to `<EditTagsSheet>` -- keeps the component's new required prop satisfied at its only call site
- [x] `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- make the default `fetchMock` resolution path-aware so `/tag-groups` resolves to `{ groups: [], groupless: [] }` instead of the current bare `[]` -- prevents the real (unmocked) `EditTagsSheet`'s new `useTagGroups()` call from receiving a malformed response in the two tests that mount it

**Acceptance Criteria:**
- Given a model's tag search returns candidates spanning 2 known groups plus one groupless candidate, when `EditTagsSheet` is open, then each group's label and matching chips render in `position` order, followed by an "Ungrouped" section for the groupless one.
- Given `useTagGroups()` has not yet resolved data, when `EditTagsSheet` is open, then candidates still render as a flat list (current behavior), so selection and save remain usable.
- Given `isAdmin=false`, when a search query matches zero existing candidates, then no "create new tag" affordance appears anywhere in the sheet.
- Given `isAdmin=true`, when a search query matches zero existing candidates, then the existing "+ Create" flow still works unchanged.

## Review Triage Log

### 2026-07-20 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 1, low 1)
- defer: 3
- reject: 10
- addressed_findings:
  - `[medium]` `[patch]` The new pl-locale test (`EditTagsSheet.test.tsx`) switched the shared `i18n` singleton to `"pl"` and only restored `"en"` via a trailing statement with no `try/finally`/`afterEach`, so a thrown assertion above it would leave every subsequent test running in Polish. Fixed by moving the reset into the file's `afterEach` (runs unconditionally after every test, success or failure) and dropping the now-redundant manual reset line.
  - `[low]` `[patch]` `EditTagsSheet`'s new `const { t, i18n } = useTranslation()` shadowed the pre-existing local `t` used as a tag/loop variable in three places in the same file (`detail.tags.map((t) => ...)`, `for (const t of detail.tags)`, `const t = selectedLookup.get(id)`) — currently safe by scoping but a landmine for a future edit inside those blocks. Renamed the destructured translator to `translate` (its only call site, `translate("catalog.filters.ungrouped")`), leaving the pre-existing loop variables untouched.
  - Rejected as a deliberate, spec-directed decision (not a gap): `EditTagsSheet`'s new `isAdmin`-gated create-affordance code is only reachable via the component's own `Harness`-driven unit tests today, since `ModelHero.tsx`'s single call site still mounts `<EditTagsSheet>` inside its pre-existing `{isAdmin && ...}` block (unchanged, per the spec's explicit `Never` boundary against widening who can open the sheet). This is intentional component-level defense-in-depth matching FR25-TAX-2's literal wording ("EditTagsSheet drops non-admin create affordance") and the established precedent from `TagGroupsSection` (45.2) accepting a parent-trusted `isAdmin` prop — not a gap introduced by this diff.
  - Rejected as consistent with an established, already-reviewed sibling pattern, not a new risk: the `labelOf`/sorted-groups bucketing logic and the `GROUPLESS_ID = "__groupless__"` sentinel are now independently re-implemented a third time (after `FacetSidebar` and `TagGroupsSection`). The spec's Design Notes explicitly directed mirroring `TagGroupsSection`'s inline shape, and 45.2's own review already accepted this exact duplication convention (independently-defined, same-literal-value sentinels; module-local `labelOf` per file) as intentional, not a defect to fix here.
  - Rejected as consistent with `TagGroupsSection`'s identical, already-reviewed structure, not a regression: the new group-section headers are non-interactive `<span>` labels with no `role="group"`/`aria-labelledby` wiring to their tag buttons, unlike `FacetSidebar`'s collapsible `<button>` headers — but `FacetSidebar`'s interactivity is for expand/collapse, a feature this non-collapsible picker list doesn't have, and `TagGroupsSection` (45.2, already reviewed) uses the identical plain-`<span>` convention for the same reason.
  - Rejected as a deliberate, already-reasoned intent-contract decision (not a gap): only the new "Ungrouped" section label is translated via `t()`/`translate()`; every other string in the sheet (title, placeholder, Save/Cancel, "No tags") stays hardcoded English, per the spec's explicit `Never` boundary ("do not add new i18n keys... leave this file's other pre-existing hardcoded English strings... untouched").
  - Rejected as low real-world impact given actual data scale, consistent with 45.2's identical precedent: `candidates`/`selectedLookup`/`sections` are recomputed on every keystroke with no `useMemo`, but at the taxonomy's actual ~36-tag/8-group scale this is negligible — the same rationale 45.2's review used to reject a per-group tag-count cap.
  - Rejected as cosmetic and pre-existing, not introduced by this diff: `ModelHero.tsx`'s `<EditTagsSheet ... isAdmin={isAdmin} />` mount is a single long line while sibling sheets use one-prop-per-line — but the line was already single-line (with 3 props) before this diff; this change only added a 4th prop to an existing style, it didn't introduce the inconsistency.
  - Rejected as consistent with `TagGroupsSection`/`FacetSidebar`'s identical, already-reviewed behavior, not a new risk: `sortedGroups`'s `position`-based sort has no tiebreaker for equal positions, so ties fall back to API response array order — the same sort expression used unmodified by both sibling components.
  - Rejected as structurally implausible, consistent with an already-accepted sibling pattern: `sections.map` keys on raw backend-issued group `id`s with no dedup guard against a hypothetical duplicate id in the `/tag-groups` response — group id uniqueness is a backend/DB invariant that `TagGroupsSection` and `FacetSidebar` trust identically today.
  - Rejected as structurally impossible given this codebase's actual fetch usage: a hypothetical `fetchMock.mockImplementation((url: string) => ...)` failure if `fetch`'s first argument were ever a `Request`/`URL` instance rather than a string — `apps/web/src/lib/api.ts`'s `api()` wrapper (the app's only fetch call site) always calls `fetch(\`${BASE}${path}\`, ...)` with a plain template-string URL; no code path in this app constructs a `Request`/`URL` object.

## Design Notes

Candidate sectioning mirrors `TagGroupsSection`'s three-step shape, but keyed off `useTags(query)`'s flat results (`candidates`) rather than `detail.tags`, and with sections filtered to non-empty (no admin-only empty-section display, since this is a picker not a taxonomy browser):

```ts
const candidates = (tags.data ?? []).filter((t) => !selected.includes(t.id));
let sections: { id: string; label: string | null; tags: TagListItem[] }[];
if (tagGroups.data === undefined) {
  sections = candidates.length > 0 ? [{ id: FLAT_ID, label: null, tags: candidates }] : [];
} else {
  const sortedGroups = [...tagGroups.data.groups].sort((a, b) => a.position - b.position);
  const knownIds = new Set(sortedGroups.map((g) => g.id));
  sections = sortedGroups
    .map((g) => ({ id: g.id, label: labelOf(g), tags: candidates.filter((t) => t.group_id === g.id) }))
    .filter((s) => s.tags.length > 0);
  const groupless = candidates.filter((t) => t.group_id === null || !knownIds.has(t.group_id));
  if (groupless.length > 0) sections.push({ id: GROUPLESS_ID, label: t("catalog.filters.ungrouped"), tags: groupless });
}
```

A `null` section `label` (the loading/error flat-fallback case) renders no header — just the existing plain button list.

## Verification

**Commands:**
- `npm run lint` (from `apps/web/`) -- expected: exits 0, `--max-warnings=0`
- `npm run test` (from `apps/web/`) -- expected: all Vitest suites pass, including updated `EditTagsSheet.test.tsx` and `ModelHero.test.tsx`
- `npx tsc -b` (from `apps/web/`) -- expected: no new type errors

## Auto Run Result

**Summary:** `EditTagsSheet`'s candidate-tag list is now grouped by facet (mirroring `TagGroupsSection`/`FacetSidebar`'s conventions) instead of one flat search list, with orphaned/groupless candidates folding into a trailing "Ungrouped" section and a graceful flat-list fallback while `useTagGroups()` hasn't resolved. The sheet also gained a required `isAdmin` prop that hides the "create new tag" affordance (and never invokes `useCreateTag`) for non-admins, at the component level rather than relying solely on the caller. The admin create-form category-selector cutover (the other half of this story's title) remains explicitly deferred to ship alongside story 47.5, per the recorded 45.3↔47.5 handshake in `epic-45-context.md`.

**Files changed:**
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.tsx` -- added `isAdmin` prop; fetches `useTagGroups()` alongside the existing `useTags(query)`; buckets candidates into position-sorted group sections + trailing "Ungrouped" (orphaned `group_id`s fold in too), falling back to the original flat list when tag-groups data isn't loaded; gated the "+ Create" button/`createAndSelect`/`useCreateTag` behind `isAdmin`.
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` -- rewrote `fetchMock` to dispatch by URL/method (`setupFetch` helper) instead of positional `mockResolvedValueOnce` calls; added 9 new tests covering the full I/O matrix (2-group + groupless ordering, orphan-folding, pending/error flat-list fallback, admin create-flow, non-admin create-suppression, non-admin grouped-section usability, pl-locale label fallback); moved the pl-locale reset into `afterEach` (review patch).
- `apps/web/src/modules/catalog/components/ModelHero.tsx` -- passes `isAdmin={isAdmin}` to the existing `<EditTagsSheet>` mount; no other change.
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` -- made the default `fetchMock` implementation path-aware so `/tag-groups` resolves `{ groups: [], groupless: [] }` (was a bare `[]`), since the real `EditTagsSheet` now fires that query too in the two tests that mount it.
- `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md` -- this spec.

**Review findings breakdown:** 15 total (Blind Hunter 11, Edge Case Hunter 5, with the i18n-locale-leak finding raised independently by both and counted once) -- 2 patch (auto-fixed: pl-locale test leaving the shared i18n singleton stuck on Polish if an earlier assertion threw; a new `t`/`useTranslation` shadowing a pre-existing loop variable of the same name), 10 reject (isAdmin-gate-currently-unreachable-in-prod and empty-section aria-wiring both traced to explicit `TagGroupsSection`/45.2-established conventions or explicit spec `Never` boundaries; triple-duplicated `labelOf`/sentinel logic and no-`useMemo` perf concern both consistent with 45.2's identical, already-accepted precedent; cosmetic `ModelHero.tsx` single-line formatting predates this diff; sort-tiebreaker and duplicate-group-id-key findings consistent with identical unmodified sibling-component behavior; fetch-arg-type assumption structurally impossible given the app's actual fetch call convention), 3 defer (all pre-existing, unmodified-by-this-diff UX gaps in the create-flow and stale-selected-chip-label path — logged to `deferred-work.md`), 0 intent_gap, 0 bad_spec.

**Verification performed:**
- `npm run lint` -- exit 0, `--max-warnings=0` (one pre-existing unrelated informational warning: React version not specified)
- `npm run test` -- 129 test files / 735 tests passed (re-run after the two review patches)
- `npx tsc -b` -- exit 0, no type errors

**Residual risks:** None blocking. The three deferred findings are all pre-existing gaps in code this story didn't modify (the create-flow's loading/whitespace-query edge cases and the stale-selected-chip-label fallback), logged for later focused attention rather than fixed here, per the triage rules for pre-existing issues surfaced incidentally.
