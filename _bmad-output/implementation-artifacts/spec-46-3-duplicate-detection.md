---
title: 'Admin tag-groups screen — duplicate detection (Story 46.3)'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '907745e59b80a36b7d254edea535e09bcc7ca162'
final_revision: 'cf9c9702db8e2906b4dce4a8e04b9a0a7106a70b'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The `/admin/tag-groups` screen (46.1 read + 46.2 write) has no way to spot near-duplicate tags (e.g. "Bracket"/"Brackets", "3D Printer"/"3d printer") that admins created by accident across groups. Every such duplicate silently splits a model's counts across two tags until an admin happens to notice and manually merges them one pair at a time via the existing per-tag "Merge into…" action.

**Approach:** Compute duplicate clusters client-side from the already-loaded `useTagGroups()` data using normalized-text similarity (no new endpoint), surface them as a dismissable-by-absence "Possible duplicates" panel above the group list, and let an admin pick a survivor and merge an entire cluster in one confirm — implemented as sequential calls to the existing `POST /admin/tags/merge` endpoint (reused unchanged from 46.2).

## Boundaries & Constraints

**Always:**
- Compute clusters purely client-side over `allTags(data)` (already defined in `TagGroupsPage.tsx`) — no new endpoint, no extra fetch, recomputed via `useMemo` on every `data` change.
- Normalize `name_en`/`name_pl` before comparing: NFD-decompose + strip combining diacritics, map `ł`/`Ł` → `l`/`L` (no NFD decomposition exists for those), lowercase, trim, collapse internal whitespace.
- Two tags belong to the same cluster if, for either language field independently (en-vs-en, pl-vs-pl; only compare when both sides are non-empty), the normalized strings are exactly equal OR their Levenshtein distance is within a length-scaled threshold: `0` for normalized length ≤ 4, `1` for length ≤ 8, `2` otherwise. This catches case/typo/plural-s variants; it deliberately does NOT attempt cross-language matching (an `en` field is never compared against a `pl` field) — that needs semantic/translation knowledge this codebase doesn't have.
- Clustering is transitive (union-find over matching pairs): if A~B and B~C, all three land in one cluster even if A and C aren't directly similar.
- Reuse `useMergeTags()` unchanged. A cluster merge is N-1 sequential `mutateAsync` calls (never `Promise.all`) — each non-survivor tag merged into the chosen survivor, one at a time, so a mid-sequence failure leaves only already-committed merges applied (no corruption, unlike the 46.2 reorder case there is nothing to roll back — each completed merge is already the desired end state).
- Default survivor pre-selection = the cluster tag with the highest `model_count` (tie-break: alphabetical by normalized `name_en`); the admin can pick a different survivor before confirming.
- The merge-duplicates dialog re-derives its live option list from currently-loaded tags by id every render (same pattern as `MoveTagDialog`/`MergeTagDialog`'s existing options-refresh fix) — if a cluster member disappears (merged elsewhere) while the dialog is open, it drops out; submit disables when fewer than 2 candidates remain.
- New copy lives under `modules.admin.tagGroups.duplicates.*` in `en.json`/`pl.json` with real (non-identical) Polish; the existing `tag-groups-i18n.test.ts` prefix sweep (`modules.admin.tagGroups.`) auto-covers it.
- Token-only styling reusing the existing `--color-warning` family (`border-warning/40 bg-warning/10 text-warning`), matching the established warning-banner precedent in `ProfileLibraryPage.tsx`.
- Every new rendered state (duplicates panel populated, merge-duplicates dialog open) gets a Playwright visual assertion (`toBeVisible()` immediately before `toHaveScreenshot`) across all 4 projects.

**Block If:**
- `POST /admin/tags/merge` no longer accepts `{ from_id, to_id }` — HALT rather than guess a new contract (same live-contract check as 46.2).

**Never:**
- Do not add a new backend endpoint, a persisted duplicate-detection table, or any server-side similarity computation — detection is a pure client-side derivation of already-fetched data.
- Do not attempt cross-language/semantic duplicate matching (e.g. treating an English name and a Polish name as the same concept) — out of scope; the heuristic is literal per-language-field text similarity only.
- Do not auto-merge anything without an explicit admin confirmation per cluster.
- Do not add rename/move affordances to the duplicates panel — it only surfaces clusters and triggers the merge-into-one flow; existing per-tag rename/move/merge actions (46.2) are unchanged.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Case-insensitive EN duplicate | Tags with `name_en` "3D Printer" / "3d printer" | Clustered together | n/a |
| Near-typo EN duplicate | Tags "Bracket" / "Brackets" (distance 1, len 8) | Clustered together | n/a |
| Exact PL duplicate | Two tags share the same non-empty `name_pl` after normalization | Clustered together | n/a |
| Distinct short tags | "PLA" / "ABS" (len 3, distance 3, threshold 0) | NOT clustered | n/a |
| Cross-group cluster | Similar tags in different groups, or one groupless | Clustered regardless of `group_id` | n/a |
| Transitive 3-tag cluster | A~B and B~C, A/C not directly similar | One 3-tag cluster, not two 2-tag clusters | n/a |
| No duplicates | All tags textually distinct | Duplicates panel not rendered | n/a |
| Merge cluster, happy path | Admin opens a cluster's "Merge into one", keeps the default survivor, confirms | Sequential `POST /admin/tags/merge` for every other cluster tag → survivor; list refreshes; one success toast | n/a |
| Merge cluster, partial failure | 2nd of 3 sequential merge calls fails (e.g. 409) | 1st merge already committed and stays; remaining calls stop; dialog closes; error toast reports partial completion | Non-2xx mid-sequence → stop + partial-failure toast, no in-dialog retry |
| Cluster shrinks mid-dialog | A cluster member gets merged away by a concurrent action while the dialog is open | Survivor options re-derive live from currently loaded tags; submit disables if fewer than 2 remain | n/a |
| Non-admin | Authenticated non-admin at `/admin/tag-groups` | Redirected to `/` (unchanged 46.1 behavior); no duplicate UI reachable | n/a |

</intent-contract>

## Code Map

- `apps/web/src/modules/admin/duplicateTags.ts` -- NEW: `normalizeTagText`, `levenshtein`, `findDuplicateClusters(tags: TagReadWithCount[]): TagReadWithCount[][]` (union-find over pairwise matches per the Boundaries rule).
- `apps/web/src/modules/admin/duplicateTags.test.ts` -- NEW: unit coverage for every I/O Matrix clustering row.
- `apps/web/src/modules/admin/DuplicateTagsPanel.tsx` -- NEW: presentational warning-styled list of clusters (joined localized names + "N similar" badge + "Merge into one" button per cluster); renders `null` when `clusters.length === 0`.
- `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.tsx` -- NEW: survivor radio-group (default = highest `model_count`) + destructive-warning copy + confirm; `onSubmit(survivorId)`.
- `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.test.tsx` -- NEW: default survivor selection, live option re-derivation on prop change, submit-disabled below 2 options.
- `apps/web/src/modules/admin/TagGroupsPage.tsx` -- extend: `useMemo` cluster computation over `allTags(data)`; render `<DuplicateTagsPanel>` above the group list; new `DialogState` variant `{ kind: "merge-duplicates"; tagIds: string[] }`; `submitMergeDuplicates` sequential-merge handler using `mergeTags.mutateAsync`.
- `apps/web/src/modules/admin/TagGroupsPage.test.tsx` -- extend: panel renders/hides, sequential `POST /admin/tags/merge` call order + bodies on confirm, partial-failure toast path.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` -- add `modules.admin.tagGroups.duplicates.*` keys (title, count badge, merge action, dialog title/description/survivor label/warning/submit, toasts), real pl translations.
- `apps/web/tests/visual/admin-tag-groups.spec.ts` -- extend: add one near-duplicate tag pair to the `POPULATED` fixture; add a populated-with-duplicates-panel baseline + a merge-duplicates dialog-open baseline, `toBeVisible()` before each, across all 4 projects.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/admin/duplicateTags.ts` -- normalize/levenshtein/union-find clustering -- powers detection.
- [x] `apps/web/src/modules/admin/duplicateTags.test.ts` -- unit tests for every I/O Matrix clustering scenario -- correctness gate for the algorithm.
- [x] `apps/web/src/modules/admin/DuplicateTagsPanel.tsx` -- cluster list UI -- surfaces detection results.
- [x] `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.tsx` -- survivor picker + confirm -- backs the merge-cluster action.
- [x] `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.test.tsx` -- default survivor, live re-derivation, submit-disabled guard -- correctness gate.
- [x] `apps/web/src/modules/admin/TagGroupsPage.tsx` -- wire cluster computation, panel, dialog state, sequential-merge handler -- integrates the feature into the screen.
- [x] `apps/web/src/modules/admin/TagGroupsPage.test.tsx` -- panel + sequential-merge + partial-failure coverage -- correctness gate.
- [x] `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` -- `modules.admin.tagGroups.duplicates.*` keys, real pl translations -- i18n parity.
- [x] `apps/web/tests/visual/admin-tag-groups.spec.ts` -- fixture near-duplicate pair + 2 new baselines, 4 projects -- visual gate.

**Acceptance Criteria:**
- Given an admin on `/admin/tag-groups` with at least one detected duplicate cluster, when the page loads, then a "possible duplicates" panel renders above the group list listing each cluster with a similar-count badge and a "Merge into one" action; the panel is absent entirely when no clusters are detected.
- Given an admin confirms a cluster merge with the (possibly overridden) survivor, when every sequential merge call succeeds, then every other cluster tag is gone after refresh and one success toast fires.
- Given a non-admin navigates to the route, then they are redirected to `/` and no duplicate-detection UI or data is reachable (46.1 behavior preserved).
- Given the visual suite runs, then the duplicates-panel baseline and the merge-duplicates dialog baseline pass in all 4 projects (light/dark × desktop/mobile).

## Spec Change Log

_No bad_spec loopback occurred; empty._

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 1, medium 2, low 0)
- defer: 3 (high 0, medium 1, low 2)
- reject: 4 (high 0, medium 1, low 3)
- addressed_findings:
  - `[high]` `[patch]` `submitMergeDuplicates` (`TagGroupsPage.tsx`) was invoked with the raw `dialog.tagIds` snapshot frozen at dialog-open time instead of the live candidate ids used for display — if a cluster member disappeared (merged elsewhere) while the dialog stayed open, the loop still attempted a merge against the now-gone tag, producing a spurious partial-failure toast for a case that should self-heal silently. Fixed: the `onSubmit` wiring now re-derives ids from `mergeDuplicatesCandidates(dialog.tagIds)` at the moment of submit. Added `TagGroupsPage.test.tsx` "uses live candidate ids at submit time, skipping a tag that disappeared…" (mutates the query cache mid-dialog via the newly-exposed `mount()` `qc` handle, asserts only the still-live tag is merged).
  - `[medium]` `[patch]` `MergeDuplicatesDialog`'s survivor radios used `candidate.label` as the sole `aria-label`, with no disambiguator — two cluster members sharing the exact same localized text (the most common real duplicate: a tag typed twice) produced identical accessible names, making the choice unreachable via screen reader even though the visible `model_count` column still distinguished them for sighted users. Fixed: added `disambiguatedLabel()`, appending `(1)`/`(2)`/… to the accessible name only when a genuine label collision exists in the candidate list, leaving the common non-colliding case unchanged. Added two `MergeDuplicatesDialog.test.tsx` cases (collision → disambiguated; no collision → plain label).
  - `[medium]` `[patch]` The partial-failure toast copy ("Some duplicate tags couldn't be merged. Already-merged tags were kept.") was shown even when the very *first* sequential merge call failed, i.e. when zero merges actually committed — implying partial progress that didn't happen. Fixed: `submitMergeDuplicates` now tracks `succeededCount` and uses a distinct `duplicates.toast.merge_failed` message ("Couldn't merge the duplicate tags.") when nothing succeeded, keeping the "kept" wording only for genuine partial completion. New en/pl i18n key added (auto-covered by `tag-groups-i18n.test.ts`'s prefix sweep). Added `TagGroupsPage.test.tsx` "first call fails outright — distinct 'nothing merged' toast…".
  - Deferred: Escape/backdrop-click bypasses the disabled-Cancel signal during an in-flight cluster merge (pre-existing across all 46.2 dialogs too, worse consequence here since it's several sequential requests, not one — needs a shared dialog-state-level fix, not a single-dialog patch); an empty-but-still-warning dialog state when a concurrent action drains all candidates (spec's own "submit disables below 2" requirement is met; low-consequence polish only); unbounded O(n²) clustering recompute with no size guard (consistent with this epic's established admin-scale-is-fine convention, no practical concern at current catalog scale). All three logged to `deferred-work.md`.
  - Rejected: the per-language OR-match semantics can false-positive-cluster tags whose other-language field clearly disagrees — this is the spec's deliberate, explicitly-documented design (an explicit admin confirmation exists precisely to catch heuristic false positives; AND-semantics would break the common case where only one language field is populated). Rejected: cluster labels don't show group context despite cross-group clustering being a named scenario — matches the pre-existing 46.2 `MergeTagDialog`/`mergeOptions` precedent, which also never surfaces group context for merges; not a new gap. Rejected: no cap/virtualization on the duplicates panel for a hypothetically large cluster count — matches the existing no-virtualization pattern across this admin screen's group list; no real catalog is at that scale. Rejected: union-find assumes tag ids are unique with no guard against a duplicate-id input — requires an unreachable backend PK-corruption precondition (SQLite primary keys are unique by construction); defensive-programming overkill for a state this app cannot produce.

## Design Notes

Levenshtein threshold table (on normalized-string length):

| Normalized length | Max edit distance to cluster |
|---|---|
| ≤ 4 | 0 (exact only — avoids false positives like "PLA"/"ABS") |
| ≤ 8 | 1 |
| > 8 | 2 |

Clustering (per cluster candidate set = `allTags(data)`, i.e. every tag across all groups + groupless, mirroring the existing `mergeOptions`/`moveOptions` cross-group pattern already in `TagGroupsPage.tsx`):

```ts
const parent = new Map<string, string>(tags.map((t) => [t.id, t.id]));
function find(id: string): string { /* path-compressed */ }
function union(a: string, b: string) { parent.set(find(a), find(b)); }
for (const [a, b] of allPairs(tags)) if (similar(a, b)) union(a.id, b.id);
// group tags by find(id); keep only groups with length >= 2, sorted by
// (descending size, then representative normalized name_en) for deterministic output.
```

`DuplicateTagsPanel` joins each cluster's localized names with " · " for the row label (mirrors the design mockup's cluster preview string), shows a `{{count}} similar` badge, and a "Merge into one" button that opens `MergeDuplicatesDialog` with that cluster's tag ids.

`MergeDuplicatesDialog` renders a radio per candidate (label + model_count), defaulting to the highest-`model_count` id; on submit the page's `submitMergeDuplicates` loop does:
```ts
for (const tag of cluster) {
  if (tag.id === survivorId) continue;
  await mergeTags.mutateAsync({ from_id: tag.id, to_id: survivorId }); // sequential, not Promise.all
}
```
stopping and toasting a partial-failure message on the first rejection, exactly mirroring the sequential-with-stop-on-failure shape already established by 46.2's group-reorder repair (`aider-review-gate.py` critical finding, resolved on `2e5f2eb`).

## Verification

**Commands:**
- `pnpm --filter web test -- duplicateTags TagGroupsPage MergeDuplicatesDialog tag-groups-i18n` -- expected: all pass.
- `pnpm --filter web typecheck` -- expected: no new type errors.
- `pnpm --filter web lint` -- expected: no new lint warnings (`--max-warnings=0`).
- `npx playwright test --config=tests/visual/playwright.config.ts admin-tag-groups` (from `apps/web/`) -- expected: all 4 projects pass; regenerate baselines intentionally with `--update-snapshots` and review the diff (only the added duplicates panel + dialog state).

**Manual checks (if no CLI):**
- Confirm the duplicates panel and merge-duplicates dialog render correctly in light and dark themes with token-only (`--color-warning`) styling.

## Auto Run Result

Status: done

### Summary

Implemented Story 46.3 duplicate-tag detection on the existing `/admin/tag-groups` screen: a pure client-side clustering algorithm (normalize + Levenshtein, length-scaled threshold, union-find) surfaces textually-similar tags in a warning-styled "Possible duplicates" panel above the group list; an admin picks a survivor and merges an entire cluster in one confirm, implemented as sequential calls to the existing `POST /admin/tags/merge` endpoint (no backend changes). A dev-repair pass fixed 3 patchable findings from the independent review (stale-snapshot merge loop, missing accessible-name disambiguation, misleading toast wording) before closing.

### Files changed

- `apps/web/src/modules/admin/duplicateTags.ts` — NEW: `normalizeTagText`, `levenshtein`, `findDuplicateClusters` (union-find clustering).
- `apps/web/src/modules/admin/duplicateTags.test.ts` — NEW: unit coverage for every I/O Matrix clustering scenario.
- `apps/web/src/modules/admin/DuplicateTagsPanel.tsx` — NEW: presentational duplicates panel.
- `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.tsx` — NEW: survivor picker + confirm; dev-repair added `disambiguatedLabel()` for accessible-name collisions.
- `apps/web/src/modules/admin/dialogs/MergeDuplicatesDialog.test.tsx` — NEW: default survivor, tie-break, live re-derivation, submit-disabled guard; dev-repair added label-collision coverage.
- `apps/web/src/modules/admin/TagGroupsPage.tsx` — extended: cluster computation, panel wiring, `merge-duplicates` dialog state, sequential-merge handler; dev-repair fixed the submit path to re-derive live candidate ids and to distinguish a zero-success failure from a partial one.
- `apps/web/src/modules/admin/TagGroupsPage.test.tsx` — extended: panel render/hide, sequential-merge call order, partial-failure toast; dev-repair added the live-ids regression test (using a newly-exposed `qc` handle from `mount()`) and the first-call-fails toast-wording test.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — `modules.admin.tagGroups.duplicates.*` keys, real pl translations; dev-repair added `toast.merge_failed`.
- `apps/web/tests/visual/admin-tag-groups.spec.ts` — added a Bracket/Brackets near-duplicate pair to the `POPULATED` fixture; 2 new baseline tests (duplicates panel, merge-duplicates dialog).

### Review findings breakdown

- Independent review (Blind Hunter + Edge Case Hunter, run in parallel over the diff since baseline): 10 unique findings after dedup.
- patch: 3 (high 1, medium 2, low 0) — all auto-fixed and re-verified:
  - stale `dialog.tagIds` snapshot used in the merge loop instead of live-derived candidates (high) — fixed by re-deriving at submit time.
  - survivor radio `aria-label` collision when two candidates share an identical label (medium) — fixed with a collision-only disambiguator.
  - misleading partial-failure toast when the *first* merge call fails with zero successes (medium) — fixed with a distinct `merge_failed` message.
- defer: 3 (medium 1, low 2), logged to `deferred-work.md`: Escape/backdrop-click bypasses the disabled-Cancel signal during an in-flight cluster merge (pre-existing across all 46.2 dialogs, needs a shared fix); empty-but-still-warning dialog chrome when a concurrent action drains all candidates (spec's own boundary already met); unbounded O(n²) clustering recompute with no size ceiling (consistent with this epic's established admin-scale convention).
- reject: 4 (medium 1, low 3): OR-across-language false-positive clustering (deliberate, spec-documented, explicit-confirm-required design); missing group context in cluster labels (matches pre-existing 46.2 merge-dialog precedent); no cap/virtualization on the panel (matches existing no-virtualization pattern, hypothetical scale); union-find's unique-id assumption (requires an unreachable backend PK-corruption precondition).

### Verification performed

- `npx vitest run duplicateTags TagGroupsPage MergeDuplicatesDialog tag-groups-i18n` — 50/50 pass (46 original + 4 dev-repair regression tests).
- `npm test` (full suite) — 794/794 pass.
- `npm run typecheck` (`tsc -b`) — clean.
- `npm run lint` (`--max-warnings=0`) — clean.
- `npx playwright test --config=tests/visual/playwright.config.ts admin-tag-groups` — 36/36 pass across all 4 projects (desktop/mobile × light/dark), run both before and after the dev-repair patches (no visual delta from the patches, since the aria-label fix only changes markup for a collision case absent from the visual fixture).
- All 28 changed/new baseline PNGs (20 changed by the fixture reflow, 8 new) visually inspected directly by Claude (this agent) before sign-off — confirmed correct in both themes and both viewports; none show a broken or unintended render.

### Residual risks

- Group reorder's known non-atomic-at-the-transport-layer residual (pre-existing, from 46.2) is unrelated to and unaffected by this story.
- The three deferred items above (dismiss-during-pending bypass, empty-cluster dialog chrome, unbounded clustering cost) remain open in `deferred-work.md` for future focused attention; none block this story's acceptance criteria.
