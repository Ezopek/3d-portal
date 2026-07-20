---
title: 'EditTagsSheet grouped picker + create-form cutover'
type: 'feature'
created: '2026-07-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'PLACEHOLDER_UPDATED_BY_COMMIT'
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

### 2026-07-20 — Review pass (dev-repair)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 2, low 0)
- defer: 2 (low 2)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` The new "renders candidates spanning 2 groups…" test asserted section ordering via `document.body.textContent.indexOf(...)`, a substring search over the *entire* rendered document rather than scoped to the sheet — would false-pass if the same literal strings ever appeared elsewhere on the page. Scoped the check to `screen.getByRole("dialog").textContent` instead.
  - `[medium]` `[patch]` The "never shows or triggers the create-tag affordance for a non-admin" test's readiness gate (`await waitFor(() => expect(fetchMock).toHaveBeenCalled())`) was satisfied by the sheet's own mount-time fetch, so it could resolve before the query triggered by the typed "brandnew" text actually completed, undermining the "never" claim. Changed the wait to assert `fetchMock` was called with a URL containing `q=brandnew` specifically.
  - Deferred to `deferred-work.md`: `labelOf`'s locale-fallback guards empty `name_pl` but not empty `name_en` — confirmed identical, pre-existing, already-duplicated verbatim in `FacetSidebar`/`TagGroupsSection` (45.1/45.2), not introduced by this story.
  - Deferred to `deferred-work.md`: grouped candidate sections have no within-section ordering (`TagRead.group_position` unused) — confirmed via repo-wide grep that no sibling component reads it either; pre-existing architectural gap surfaced incidentally, not caused by this diff.
  - Rejected as a false negative in the *external* verification gate, not a code defect: the triggering "deterministic verification failure" (`aider-review-gate.py` rc=3, "no explicit final verdict") was traced to a regex bug in that shared script (outside this worktree, on `main`) that fails to match a verdict written as `**Verdict:** APPROVE` (bold wraps only the label, not the word). The actual reviewer output was a clean APPROVE with 0 critical/0 important/0 minor findings. An independent audit subagent in this pass re-confirmed the code fully satisfies the spec with no changes needed (lint/tsc/735 tests green) before this review pass ran.
  - Rejected as a duplicate of an already-addressed finding from the prior review pass (deliberate, spec-directed decision, not a gap): `isAdmin`-gated code paths (the create-affordance branch and `createAndSelect`'s `if (!isAdmin) return;` guard) remain unreachable in production today since `ModelHero.tsx`'s single call site still mounts `<EditTagsSheet>` inside its pre-existing, unchanged `isAdmin &&` gate.
  - Rejected as consistent with an already-addressed, already-reviewed sibling pattern: plain-`<span>` group headers with no `role="group"`/`aria-labelledby` wiring — identical convention to `TagGroupsSection` (45.2, already reviewed and accepted).
  - Rejected as mathematically consistent with the spec's own orphan-folding rule, not a bug: when `useTagGroups()` resolves with `groups: []` (zero known groups, as opposed to pending/error), every candidate correctly folds into "Ungrouped" per the spec's literal rule ("references a group absent from the current response" folds in) — there is no known-groups set for anything to belong to, so this is the expected/correct result, not a fallback-list gap.
  - Rejected as currently unreachable in production, same precedent as the `isAdmin`-gate finding above: a non-admin's zero-candidate search now renders no affordance/message at all (vs. the pre-diff single flat list, which showed "+ Create" to every viewer as implicit "no results" feedback) — this branch has zero live traffic today since only admins can open the sheet at all.
  - Rejected as matching the spec's explicit Code Map instruction, not an unintended gap: `ModelHero.test.tsx`'s path-aware `fetchMock` default resolves any unmatched URL to a generic `200 []`, which the spec's Code Map directly specified ("make the default... path-aware").
  - Rejected as meta-commentary confirming correct prior handling, not a new actionable finding: two of the three `deferred-work.md` entries recorded in the prior review pass describe pre-existing gaps in code paths this diff also touches (the create-affordance's fetch-in-flight flash, the whitespace-only-query no-op) — already correctly deferred per the prior pass's triage, not left unaddressed.
  - Rejected as a low-value cosmetic naming concern: `sprint-status.yaml` marking `45-3-edittagssheet-grouped-picker-create-form-cutover: done` could be misread as the full "create-form cutover" (the `AddModelForm`/`routes/admin/models/new.tsx` half, explicitly deferred to ship with 47.5) having shipped — the spec's Approach section already documents this split explicitly; the combined story-title convention across two stories is an established process pattern, not a defect in this diff.

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

**Summary:** `EditTagsSheet`'s candidate-tag list is grouped by facet (mirroring `TagGroupsSection`/`FacetSidebar`'s conventions) instead of one flat search list, with orphaned/groupless candidates folding into a trailing "Ungrouped" section and a graceful flat-list fallback while `useTagGroups()` hasn't resolved. The sheet also gained a required `isAdmin` prop that hides the "create new tag" affordance (and never invokes `useCreateTag`) for non-admins, at the component level rather than relying solely on the caller. The admin create-form category-selector cutover (the other half of this story's title) remains explicitly deferred to ship alongside story 47.5, per the recorded 45.3↔47.5 handshake in `epic-45-context.md`.

This pass was a **dev-repair resume**: the previous session's implementation (commit `8b9e234`) had already reached `done` and passed this skill's own review cycle, but the orchestrator's external `aider-review-gate.py` check reported a failure. Root cause: that shared script (outside this worktree, on `main`) has a verdict-detection regex that fails to match a verdict written as `**Verdict:** APPROVE` (bold wraps only the label, not the word) — the actual reviewer output was a clean APPROVE with 0 critical/0 important/0 minor findings. An implementation-audit subagent independently re-confirmed the existing code fully satisfies the spec's intent-contract, boundaries, and I/O matrix with zero changes needed before this pass's review ran.

**Files changed this pass:**
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` -- two test-robustness patches from this pass's review (see Review Triage Log): scoped the group-ordering assertion to the dialog root instead of `document.body`; fixed a `waitFor` gate that could resolve before the query triggered by typed text actually completed.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- appended 2 new pre-existing-gap entries surfaced incidentally by this pass's review.
- `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md` -- this spec.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- restored `45-3-edittagssheet-grouped-picker-create-form-cutover: done`.

No changes to `EditTagsSheet.tsx`, `ModelHero.tsx`, or `ModelHero.test.tsx` this pass — the prior pass's implementation of those files was re-verified, not re-derived.

**Review findings breakdown (this pass):** 12 total (Blind Hunter 10, Edge Case Hunter 2) -- 2 patch (auto-fixed: brittle document-wide ordering assertion, weak `waitFor` readiness gate), 2 defer (pre-existing `labelOf` empty-`name_en` gap already duplicated in shipped siblings; unused `TagRead.group_position` — no sibling component orders within a section either), 8 reject (external gate's own regex bug is not a code defect; `isAdmin`-gate-unreachable-in-production and non-admin-empty-search-feedback both duplicate/extend the already-rejected unreachable-branch precedent; aria wiring and zero-known-groups-folds-to-Ungrouped both consistent with already-accepted sibling behavior or the spec's own literal fold rule; `ModelHero.test.tsx`'s fetchMock default matches the spec's explicit Code Map instruction; deferred-work meta-commentary and sprint-status naming concerns are non-issues), 0 intent_gap, 0 bad_spec.

**Verification performed:**
- `npm run lint` -- exit 0, `--max-warnings=0` (one pre-existing unrelated informational warning: React version not specified)
- `npm run test` -- 129 test files / 735 tests passed
- `npx tsc -b` -- exit 0, no type errors

**Residual risks:** None blocking. The two newly-deferred findings are pre-existing gaps in already-shipped, already-reviewed sibling conventions (`labelOf`, unused `group_position`), logged for later focused attention. The external `aider-review-gate.py` regex bug is unresolved (out of this worktree's scope — it lives in shared `.bmad-loop/scripts/` on `main`) and may cause the same false-negative on re-verification if the reviewer model again formats its verdict as `**Verdict:** APPROVE`; recommend fixing that script's regex separately since no in-scope code change can affect its parsing.

### 2026-07-20 — Visual-coverage repair pass

**Finding:** `apps/web/tests/visual/destructive-dialogs-edit-sheets-open.spec.ts`'s "EditTagsSheet open" case opened the sheet against `stubSotDetail`'s fixture, whose only tags (`t1`/`t2`) were already selected. `EditTagsSheet` mounts unconditionally under `ModelHero`'s `isAdmin &&` block (not lazily on sheet-open), so `useTags("")` fires on page load; with no `/api/tags` stub registered for this spec, the request 404'd via `_test.ts`'s default catch-all, leaving `candidates = []`. The four `edit-tags-sheet-open-*.png` baselines therefore showed the chip row + empty search box only — no group headers, no candidate rows — so the suite passed without ever visually exercising this story's core deliverable (the grouped candidate picker).

**Repair:** Added a test-local `stubTagCandidates(page)` route override for `**/api/tags*` inside the spec file (not folded into shared `stubSotDetail`, so the other three tests in this file — which never open `EditTagsSheet` — keep their existing baselines byte-identical). It returns 5 tags: the 2 already-selected ones (`t1` dragon/`tg-theme`, `t2` articulated/groupless — filtered out client-side by the component's own `!selected.includes(id)` logic) plus 3 new unselected candidates spanning `stubSotDetail`'s existing `/api/tag-groups` fixture's two known groups (`t3` fire → `tg-theme`/"Motyw", `t4` resin → `tg-material`/"Materiał") and one groupless orphan (`t5` orphan-decor → `group_id: null` → "Bez grupy"). Added explicit `expect(...).toBeVisible()` assertions for both pl-PL group headers, the "Bez grupy" trailing section, and all three candidate rows, scoped to the sheet locator, before each `toHaveScreenshot` call — so a future regression that silently empties the picker fails the assertion, not just a pixel diff a reviewer might rubber-stamp.

No production code changes — `EditTagsSheet.tsx` already implements the grouped picker correctly per the 2026-07-20 review passes above; this pass was purely a test-fixture/visual-proof gap.

**Files changed this pass:**
- `apps/web/tests/visual/destructive-dialogs-edit-sheets-open.spec.ts` — added `stubTagCandidates()` local route stub + pre-screenshot visibility assertions for the "EditTagsSheet open" test only.
- `apps/web/tests/visual/__snapshots__/destructive-dialogs-edit-sheets-open.spec.ts/edit-tags-sheet-open-{desktop,mobile}-{light,dark}.png` — regenerated; now show 3 grouped sections ("Motyw" + fire, "Materiał" + resin, "Bez grupy" + orphan-decor) instead of an empty candidate list.
- This spec (`final_revision` placeholder pending this pass's commit SHA).

**Verification performed:**
- `npx playwright test --config=tests/visual/playwright.config.ts destructive-dialogs-edit-sheets-open.spec.ts` (targeted, all 4 projects, pre-regen) — 12/16 passed, the 4 `EditTagsSheet open` cases failed only on `toHaveScreenshot` pixel diff (expected — old baselines showed the empty-picker bug); all new `toBeVisible()` assertions passed on every project, confirming the grouped picker renders correctly before the screenshot step.
- `npx playwright test --config=tests/visual/playwright.config.ts destructive-dialogs-edit-sheets-open.spec.ts -g "EditTagsSheet open" --update-snapshots` — regenerated exactly the 4 targeted baselines.
- `npx playwright test --config=tests/visual/playwright.config.ts` (full suite) — 468 passed, 0 failed, 24 skipped. `git status --porcelain` confirmed only the 4 intended PNGs + the spec file changed — no other baseline rippled.
- `git diff --check` — clean, no whitespace errors.
- `npx eslint tests/visual/destructive-dialogs-edit-sheets-open.spec.ts --max-warnings=0` — no issues.
- `npx tsc -b` — 1 pre-existing, unrelated error (`TS5101`, deprecated `baseUrl` compiler option in `tsconfig.json`, itself untouched by this pass — confirmed via `git diff --stat -- apps/web/tsconfig.json` showing no diff); no new type errors from the changed test file.
- Visually inspected all 4 regenerated baselines (Read tool, rendered PNGs): grouped sections render correctly in the expected `position` order (Motyw → Materiał → Bez grupy), no clipping, no unwanted scrollbar, correct light/dark contrast, and correct desktop/mobile layout in all four.

**Residual risks:** None. This pass only closed a visual-proof gap in test fixtures/assertions; it does not touch `EditTagsSheet.tsx`, `ModelHero.tsx`, `AddModelForm.tsx`, `routes/admin/models/new.tsx`, category-selector behavior, API types, or backend. Epic 45 closeout ownership remains with Laura/controller.

