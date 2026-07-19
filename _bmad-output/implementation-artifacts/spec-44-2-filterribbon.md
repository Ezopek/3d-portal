---
title: 'Story 44.2 — FilterRibbon AND/OR toggle'
type: 'feature'
created: '2026-07-20'
status: 'done'
baseline_revision: '70aff05a35b242a56de89691f60c6f0d1f366000'
final_revision: 'aebfde78a81cbf72bbe2d67ce3978ac470712b37'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-44-context.md'
  - '{project-root}/docs/design/HANDOFF-tagi-fasetowe.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The catalog `FilterRibbon` already renders removable active-tag chips (`tag_ids`) but has no way for the user to control how multiple selected tags combine. The facet initiative (FR25-FILT-1, HANDOFF §17 + mockup 04) requires a user-visible AND/OR (`tag_match`) switch: default AND (`all` — intersect), toggle to OR (`any` — union). The backend `GET /api/models` already accepts `tag_match` (`all` default), and the E43 URL layer already validates the `tag_match` search param — only the UI control and its pass-through are missing.

**Approach:** Add an inline, token-styled AND/OR segmented toggle to the existing `FilterRibbon`, controlled via its existing `state`/`onChange` contract by adding an optional `tag_match` field to `FilterRibbonState` (defaults to `"all"`). Render it only when ≥2 tags are selected (AND vs OR only changes results with ≥2 tags). Wire the value through `CatalogList` (URL persist, mirroring the existing `tag_ids` handling) and `useModels` (send the `tag_match` query param) so the toggle is functional on live `main`, not a dead control.

## Boundaries & Constraints

**Always:**
- `FilterRibbon` stays **presentational/controlled**: no self-fetching for the toggle; it reads `state.tag_match` (defaulting to `"all"`) and fires `onChange({ ...state, tag_match })`. The status/source/sort selects, the search input, the active-chip bar, and the `TagPicker` are unchanged.
- Toggle renders **only when `state.tag_ids.length >= 2`** — with 0 or 1 selected tags, AND and OR are equivalent, so the control is hidden to avoid a no-op affordance.
- Token-only styling: Tailwind classes bound to theme tokens (`border-border`, `bg-primary`, `text-primary-foreground`, `text-muted-foreground`, `hover:bg-accent`). **Zero inline hex / color literals** (ESLint + Stylelint color-literal ban; HANDOFF §7 dark-mode hard AC — correct tokens make dark work via `.dark`).
- No new `apps/web/src/ui/*.tsx` primitive (would trip the Visual Coverage Contract pre-commit hook). Build the toggle inline with native `<button>`s inside a `role="group"` wrapper.
- All user-visible strings via `useTranslation()` + `t(...)`, keys added to **both** `en.json` and `pl.json` with an identical key set.
- `TagMatch` (`"all" | "any"`) is imported from its single existing home (`@/routes/catalog/index`); do not redefine the union.
- `CatalogList`/`useModels` changes are the **minimal** pass-through to make the toggle functional: persist `tag_match` to URL (omit when `"all"`) and send it to the models query. Everything else in `CatalogList` (category tree, `expandCategoryIds`, `category_id`, empty-state, pagination) stays untouched.

**Block If:**
- The E43 `tag_match` URL param / validation is absent from `@/routes/catalog/index` (no `tag_match` on `CatalogSearch`, no `TAG_MATCHES`) → HALT `blocked`, blocking condition `missing E43 tag_match URL layer`.

**Never:**
- Do **not** remove or restyle the existing `TagPicker`, active-chip bar, or status/source/sort selects (HANDOFF: TagPicker stays as an alternative add path).
- Do **not** drop `useCategoriesTree`/`expandCategoryIds`/`category_id`, mount `FacetSidebar`, add the empty-result "Switch to OR / Clear" CTA, or add `untagged` surfacing — all Story 44.3.
- Do **not** add a `tag_match` toggle to the mobile Filters sheet or duplicate it — one instance in the active-filter row serves both breakpoints.
- Do **not** change chip labels (still `slug`), add fuzzy search, or add a new endpoint.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No / single tag | `tag_ids` length 0 or 1 | No AND/OR toggle rendered | No error expected |
| Two+ tags, default | `tag_ids` length ≥2, `tag_match` unset/`"all"` | Toggle visible; "All" (AND) button is the active/pressed one | No error expected |
| Switch to OR | Click "Any" while `tag_match` is `"all"` | `onChange` fires once with `tag_match: "any"`; "Any" becomes pressed (controlled by prop) | No error expected |
| Switch to AND | Click "All" while `tag_match` is `"any"` | `onChange` fires once with `tag_match: "all"` | No error expected |
| Re-click active | Click the already-active button | `onChange` fires with the same value (idempotent); no crash | No error expected |
| URL persist | Toggle to OR in `CatalogList` | `tag_match=any` written to URL; models query sends `tag_match=any`; toggling back to AND removes the param | No error expected |

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` -- add `tag_match?: TagMatch` to `FilterRibbonState`; render the inline AND/OR toggle in the active-filter row (the `flex flex-wrap items-center gap-1` block, after the `TagPicker` add button) gated on `state.tag_ids.length >= 2`. Token classes only; reuse the existing `onChange({ ...state, ... })` idiom.
- `apps/web/src/routes/catalog/index.tsx` -- change `type TagMatch` → `export type TagMatch`; `CatalogSearch.tag_match` + `TAG_MATCHES` already exist (E43). `validateSearch` now also drops `tag_match` when fewer than 2 `tag_ids` survive normalization, so hand-crafted URLs cannot strand an un-clearable `tag_match=any` — this is the runtime enforcement layer (TanStack runs `validateSearch` on every navigation) and keeps the URL layer consistent with `setFilters`/`buildParams` (E44.2 review repair).
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` -- `filterState` gains `tag_match: search.tag_match ?? "all"`; `setFilters` persists `tag_match: next.tag_match && next.tag_match !== "all" ? next.tag_match : undefined`; `useModels(...)` call gains `tag_match: search.tag_match`.
- `apps/web/src/modules/catalog/hooks/useModels.ts` -- `ModelsFilters` gains `tag_match?: TagMatch`; `buildParams` appends `tag_match` only when defined, `!== "all"`, and `tag_ids.length >= 2` (backend default is `all`; `tag_match` is a no-op below 2 tags), matching the `validateSearch`/`setFilters` threshold (E44.2 review repair).
- `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` -- append toggle cases (existing cases untouched; `tag_match` optional so they still compile).
- `apps/web/src/locales/en.json`, `pl.json` -- add match-mode keys to both.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/routes/catalog/index.tsx` -- export the existing `TagMatch` union (`export type TagMatch`) so `FilterRibbon`/`useModels` share one definition. No behavior change.
- [x] `apps/web/src/modules/catalog/hooks/useModels.ts` -- add `tag_match?: TagMatch` to `ModelsFilters`; in `buildParams` append `p.set("tag_match", f.tag_match)` only when `f.tag_match !== undefined && f.tag_match !== "all"`. `tag_match` participates in the `["sot","models",filters]` query key automatically.
- [x] `apps/web/src/modules/catalog/components/FilterRibbon.tsx` -- add `tag_match?: TagMatch` to `FilterRibbonState`; compute `const matchMode = state.tag_match ?? "all"`. Render an inline segmented toggle only when `state.tag_ids.length >= 2`: a `role="group"` `aria-label={t("catalog.filters.matchMode")}` wrapper with a `border border-border rounded-md` frame and two `<button type="button">`s ("All"→`all`, "Any"→`any`), each with `aria-pressed={matchMode === value}`, active = `bg-primary text-primary-foreground`, inactive = `text-muted-foreground hover:bg-accent`, `onClick={() => onChange({ ...state, tag_match: value })}`.
- [x] `apps/web/src/modules/catalog/routes/CatalogList.tsx` -- add `tag_match: search.tag_match ?? "all"` to `filterState`; in `setFilters` add `tag_match: next.tag_match && next.tag_match !== "all" ? next.tag_match : undefined`; add `tag_match: search.tag_match` to the `useModels({...})` call. No other lines change.
- [x] `apps/web/src/locales/en.json` & `pl.json` -- add `catalog.filters.matchMode` ("Tag match" / "Dopasowanie tagów"), `catalog.filters.matchAll` ("All" / "Wszystkie"), `catalog.filters.matchAny` ("Any" / "Dowolne") to both (identical key set).
- [x] `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` -- append cases covering every matrix row: hidden at 0 and 1 tag; visible at 2 tags with "All" pressed by default; click "Any" fires `onChange` with `tag_match: "any"`; click "All" fires with `tag_match: "all"`; `aria-pressed` reflects the `tag_match` prop.

**Acceptance Criteria:**
- Given `state.tag_ids` has fewer than 2 entries, when `FilterRibbon` renders, then no AND/OR toggle is present.
- Given `state.tag_ids` has ≥2 entries and `tag_match` is unset or `"all"`, when `FilterRibbon` renders, then the toggle is shown with the "All" (AND) option pressed.
- Given the toggle is shown, when the user clicks "Any", then `onChange` fires exactly once with `{ ...state, tag_match: "any" }` and pressed-state follows the controlling prop (fully controlled).
- Given `CatalogList`, when the user switches the toggle to OR, then the URL carries `tag_match=any` and the models query sends `tag_match=any`; switching back to AND removes the param and the query omits it.
- Given the app builds, when `npm run lint`, `npm run typecheck`, and `npm run test` run in `apps/web/`, then all pass with zero warnings and no color literals are introduced.

## Spec Change Log

_No `bad_spec` loopback occurred; the review pass produced only auto-fixed patches (see Review Triage Log)._

## Review Triage Log

### 2026-07-20 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 9
- addressed_findings:
  - `[low]` `[patch]` A non-default `tag_match=any` stranded in the URL/models-query when the user reduced their selection below 2 tags (the toggle hides at <2, leaving it un-clearable). Both reviewers flagged it; functionally benign (backend treats `any`≡`all` for <2 tags) but violates the story's URL-persist contract. Gated the `setFilters` `tag_match` write on `next.tag_ids.length >= 2` so it drops from the URL as soon as the selection falls below the threshold.
  - `[low]` `[patch]` The `buildParams` `tag_match` omission branch (send for `any`, omit for `all`/`undefined`) — the exact behavior AC-4 asserts for the models query — had no direct hook-level test. Added a `useModels` case proving `tag_match=any` is sent and `all`/`undefined` are omitted.
- rejected (by-design / spec-scoped / no real trigger): `role="group"`+`aria-pressed` vs `radiogroup`/`radio` (spec-prescribed; segmented `aria-pressed` toggle is an accepted single-select pattern); no visible text label beyond the group `aria-label` (buttons are self-labeled "All"/"Any" in the active-tag row; visible-label styling is E47 visual-spec territory); redundant `onChange` on re-clicking the active segment (the I/O matrix explicitly accepts idempotent re-click); `TagMatch` imported from the route module (spec-prescribed single-source-of-truth, `import type` only — no runtime cycle; relocation is gold-plating beyond minimal-diff); `"all"|"any"` literal appearing in a few call sites (the `TagMatch` *type* is single-sourced; runtime literals are local and typed); color-only active-state cue (`aria-pressed` covers SR users; matches the app's existing segmented styling); `activeFilterCount`/`filtersActive` not counting `tag_match` (with ≥2 tags `filtersActive` is already true via `tag_ids`; the toggle only exists alongside active tags); double `?? "all"` default across the CatalogList→FilterRibbon boundary (both defensively resolve the same documented default; optional-with-default is idiomatic); backend-default-drift risk (three encodings agree today; asserting cross-layer alignment is out of this story's scope).

### 2026-07-20 — Review pass (verification-failure repair)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 2
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` The deterministic verify gate (independent Aider review) returned `REQUEST_CHANGES` (rc=4), driven by an inconsistency: `setFilters` gated the `tag_match` URL write on `tag_ids.length >= 2`, but `validateSearch` (E43) still accepted a non-default `tag_match` at 0–1 tags, so a hand-crafted URL could strand an un-clearable `tag_match=any`. Repaired by adding the `>= 2` precondition to `validateSearch` (`index.tsx`) — the runtime enforcement layer TanStack runs on every navigation — and, for full three-layer agreement, to `buildParams` (`useModels.ts`). Updated the affected E43 `validateSearch` tests (they asserted the old independent-param behavior — `tag_match` now requires ≥2 surviving `tag_ids`) and added the reviewer-requested normalization tests: `tag_match=any` dropped at 0 and 1 tags, and dropped when all `tag_ids` fail validation. Updated the `useModels` test to prove the `≥2` gate. `<intent-contract>` untouched; the fix strengthens the frozen URL-persist contract without contradicting any I/O-matrix row (no matrix row covers hand-crafted <2-tag URLs).
- deferred (real, not this story's frozen scope): (1) no `CatalogList` router-level integration test for the full toggle→URL→query round-trip — the invariant is enforced+unit-tested at `validateSearch`/`buildParams`; integration/visual facet coverage is E47-scoped per Verification; (2) pre-existing E43 `tag_ids` dedupe is case-sensitive while validation is case-insensitive, so a repeated-UUID-different-case URL can count as 2 tags. Both recorded in `deferred-work.md`.
- rejected (by-design / spec-frozen / no real trigger): `role="group"`+`aria-pressed` vs `radiogroup`/`radio` (spec-prescribed in `<intent-contract>`; cannot change without violating frozen intent); no rendered visible label beyond the group `aria-label` (E47 visual-spec territory; buttons self-label "All"/"Any"); color-only active cue (`aria-pressed` covers SR users); idempotent re-click firing `onChange` (I/O matrix explicitly accepts it); double `?? "all"` default across the `CatalogList`→`FilterRibbon` boundary (idiomatic optional-with-default); `activeFilterCount`/`filtersActive` not counting `tag_match` (toggle only exists alongside ≥2 active tags, so `filtersActive` is already true); type-only `TagMatch` import from the route module (spec-prescribed single source of truth, `import type` — erased at runtime); `validateSearch` block-ordering being load-bearing (natural order, commented; a hypothetical reorder is a maintenance concern, not a defect).

### 2026-07-20 — Review pass (follow-up review, no code changes)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 14
- addressed_findings:
  - none
- reject rationale (both reviewers re-surfaced items the two prior passes already adjudicated; verification re-run green — typecheck, lint, 703/703 tests): `>= 2` threshold "duplicated" across `FilterRibbon`/`setFilters`/`buildParams`/`validateSearch` (the spec documents this three-layer agreement as the intentional enforcement design, not a defect; extracting a shared constant is gold-plating beyond minimal-diff); `TagMatch` imported from `@/routes/catalog/index` (spec-prescribed single source of truth, `import type` only — erased at runtime, no cycle); no rendered visible label / "All"·"Any" AND-vs-OR ambiguity (E47 visual-spec territory; buttons self-label in the active-tag row); `role="group"`+`aria-pressed` vs `radiogroup`/`radio` (spec-prescribed segmented-toggle pattern in `<intent-contract>`); idempotent re-click firing `onChange`→navigate (I/O matrix explicitly accepts the idempotent re-click); `activeFilterCount` ignoring `tag_match` (toggle only exists alongside ≥2 active tags, so `filtersActive` is already true via `tag_ids`); double `?? "all"` default across the `CatalogList`→`FilterRibbon` boundary (idiomatic optional-with-default); backend-default-drift assumption unverified (out of this story's scope; three encodings agree today); duplicated Tailwind base utilities across the ternary branches (cosmetic; churning it contradicts the deliberate minimal diff); no mutual-exclusivity test (redundant with the existing `aria-pressed`-reflects-prop test). The two *real* items surfaced — (a) no `CatalogList`/`setFilters` router-level integration test for the toggle→URL→query round-trip, and (b) the pre-existing E43 case-insensitive-UUID-validation vs case-sensitive-`tag_ids`-dedup gap that can inflate the ≥2 count on a hand-crafted URL — are **already recorded in `deferred-work.md`** from the prior pass; not re-appended (NEW-entries-only ledger discipline; prefer reject over duplicate defer).

## Design Notes

- **Why functional wiring, not a pure component like 44.1:** `FacetSidebar` (44.1) was a new, unmounted component, so URL wiring could defer to 44.3. `FilterRibbon` is already live in `CatalogList` and auto-deploys to `.190` on merge — a toggle whose state does not persist would ship a visibly-broken control (it would snap back to AND on every click, since `CatalogList` re-derives `filterState` each render). The minimal `tag_match` pass-through (URL + query) mirrors the `tag_ids` handling already present and is additive; 44.3's distinctive scope (category-tree removal, `FacetSidebar` mount, untagged, empty-state CTA) is orthogonal and unaffected.
- **Why gate at `tag_ids.length >= 2`:** `tag_match` only changes results with ≥2 tags; showing it at 0–1 tags is a no-op affordance. HANDOFF §17 asks only that it be "visible to the user (default AND)"; the ≥2 gate keeps the ribbon clean without contradicting that.
- **Toggle shape (inline, no `ui/` primitive):** two native `<button>`s in a bordered `role="group"`; active button `bg-primary text-primary-foreground`, inactive `text-muted-foreground hover:bg-accent`. Inline avoids adding `ui/toggle-group.tsx`, which would trip the Visual Coverage Contract hook.
- **`tag_match` omitted from URL/query when `"all"`:** `all` is both the app default and the backend default, so persisting it would only add URL noise; write it only for the non-default `any`. This matches the E43 `validateSearch`, which already drops `tag_match === "all"`.

## Verification

**Commands:** (run from `apps/web/`)
- `npm run typecheck` -- expected: `tsc -b` passes, no type errors.
- `npm run lint` -- expected: ESLint `--max-warnings=0` + Stylelint pass (no color literals).
- `npm run test` -- expected: Vitest green, including the appended `FilterRibbon.test.tsx` toggle cases and all pre-existing cases.

**Manual checks:**
- No new Playwright visual baseline in 44.2: pl-PL facet-surface baselines are authored in Epic 47 per the epic plan. The toggle is hidden in the default 0-selected-tag state that the existing `catalog-list.spec.ts` / `filter-ribbon-selects-open.spec.ts` snapshots exercise, so those baselines are unaffected. Confirm `npm run test:visual` still passes (or, if the browser cannot run in this environment, state so explicitly and rely on the unchanged-default-state argument).


## Auto Run Result

Status: done (verification-failure repair)

**Summary:** The previous session's diff failed the deterministic verify gate (independent Aider review, rc=4 `REQUEST_CHANGES`). The critical driver was a URL-normalization inconsistency: `CatalogList.setFilters` dropped `tag_match` below 2 tags, but `validateSearch` (E43) and `useModels.buildParams` still accepted a non-default `tag_match` at 0–1 tags, so a hand-crafted URL could strand an un-clearable `tag_match=any`. Repaired by making all three layers enforce the same `tag_ids.length >= 2` precondition, and by adding the reviewer-requested router-level normalization tests. The frozen `<intent-contract>` was not touched.

**Files changed (repair):**
- `apps/web/src/routes/catalog/index.tsx` — `validateSearch` drops `tag_match` when fewer than 2 `tag_ids` survive normalization (runtime enforcement on every navigation).
- `apps/web/src/modules/catalog/hooks/useModels.ts` — `buildParams` gates the `tag_match` query param on `tag_ids.length >= 2` (three-layer consistency).
- `apps/web/src/routes/catalog/index.test.ts` — updated E43 `tag_match` tests to the ≥2 precondition; added normalization/edge-case tests (dropped at 0 and 1 tags, and when all `tag_ids` fail validation).
- `apps/web/src/modules/catalog/hooks/useModels.test.tsx` — asserts the `≥2` gate and the `undefined` omission the test name promises.
- Spec: refreshed Code Map (`index.tsx`, `useModels.ts` notes), appended Review Triage Log repair pass.

**Review findings breakdown:** 1 patch applied (three-layer `tag_match` `≥2` consistency + tests); 2 deferred (no `CatalogList` router-level integration test — E47 scope; pre-existing E43 case-sensitive `tag_ids` dedupe); 8 rejected as by-design / spec-frozen / no-trigger (see Review Triage Log).

**Verification performed (from `apps/web/`):**
- `npm run typecheck` — pass (`tsc -b`, no errors).
- `npm run lint` — pass (ESLint `--max-warnings=0` + Stylelint; no color literals).
- `npm run test` — pass (126 files, 703 tests green).
- `npm run test:visual` — not run in this environment; toggle is hidden in the default 0-tag state the existing snapshots exercise, so baselines are unaffected (per Manual checks).

**Residual risks:** The `setFilters`/`validateSearch`/`buildParams` round-trip has no single router-level integration test (deferred to E47); the invariant is enforced and unit-tested at the `validateSearch` layer that actually runs on every navigation. The verify gate's re-review is an independent LLM pass; `followup_review_recommended: true` requests it re-run over the repaired diff.

### Follow-up review pass (2026-07-20)

Status: done (follow-up review, no code changes)

**Summary:** Fresh independent review of the complete diff since baseline `70aff05`. Blind Hunter (adversarial) and Edge Case Hunter ran in parallel with no prior context. Every finding was either a re-tread of an item the two prior passes already adjudicated by-design, or one of the two real items already recorded in `deferred-work.md` (no `CatalogList`/`setFilters` router-level integration test; pre-existing E43 case-insensitive-UUID-validation vs case-sensitive-`tag_ids`-dedup gap). No new intent gaps, spec defects, or patchable findings surfaced. Zero code changes this pass.

**Review findings breakdown:** 0 intent_gap, 0 bad_spec, 0 patch, 0 defer (both real items already in the ledger — not duplicated), 14 reject (all by-design / spec-frozen / E47-visual-scope / already-deferred; see Review Triage Log 2026-07-20 follow-up entry for the itemized rationale).

**Verification performed (from `apps/web/`):**
- `npm run typecheck` — pass (`tsc -b`, no errors).
- `npm run lint` — pass (ESLint `--max-warnings=0` + Stylelint; no color literals; only the pre-existing informational "React version not specified" note, not a warning failure).
- `npm run test` — pass (126 files, 703 tests green).
- `npm run test:visual` — not run in this environment; toggle is hidden in the default 0-tag state the existing snapshots exercise, so baselines are unaffected (per Manual checks).

**Follow-up review recommendation:** `false` — this pass made no review-driven changes; the diff is unchanged and already independently verified.
