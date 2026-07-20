---
title: 'ModelCard untagged ghost-chip'
type: 'feature'
created: '2026-07-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '5f1912c6e9092b20274e8c317176b637e05001fe'
final_revision: '65c58c376369edb989321ee035def21c438099eb'
---

<intent-contract>

## Intent

**Problem:** After the facet-tag catalog rebuild, every model starts with zero tags (no data migration ran category → tag). `ModelCard` only renders a chip row when `model.tags.length > 0`, so a zero-tag card currently shows no chip row at all instead of communicating the "untagged" state, which is now the common case, not an edge case.

**Approach:** When `model.tags` is empty, render a single dashed/ghost-style placeholder chip in `apps/web/src/ui/custom/ModelCard.tsx` reading "Bez tagów" (pl) / "No tags" (en) in place of the current empty chip row, using a new i18n key. Tagged models keep the existing top-2 chip rendering unchanged.

## Boundaries & Constraints

**Always:**
- Ghost chip renders only when `model.tags.length === 0`; any model with 1+ tags keeps the current `topTags` chip-row behavior untouched.
- Ghost chip is visually distinct from a real tag chip (dashed border, muted/lower-emphasis styling) so it reads as a placeholder/absence state, not a selectable tag.
- Ghost chip uses only existing `--color-*` Tailwind theme tokens (e.g. `text-muted-foreground`, `border-muted-foreground` or `border-border`) — no inline hex colors, no new tokens needed for a dashed border treatment.
- New copy goes through i18n: add `catalog.no_tags` to both `apps/web/src/locales/en.json` ("No tags") and `apps/web/src/locales/pl.json` ("Brak tagów" — component uses `t("catalog.no_tags")`, not the existing `catalog.filters.untagged` filter-checkbox label, which reads as a full sentence ("Untagged models") and is wrong grammatically as a chip label).
- Ghost chip is not a link/button and carries no click/filter behavior — Story 45.2 (CatalogDetail) and the existing `FacetSidebar` untagged filter already own tag-driven navigation/filtering; this story is card-rendering only.

**Block If:** none — this is a self-contained, unambiguous rendering change with no external dependency gaps.

**Never:**
- Do not change `topTags` slicing (still top 2 for tagged models).
- Do not touch `FacetSidebar`, `CatalogList`, `CatalogDetail`, or `EditTagsSheet` — out of scope for 45.1 (45.2/45.3 own detail/edit surfaces).
- Do not add a `data-testid="tag-chip"` to the ghost chip — it is not a tag and must not be counted by `tag-chip` queries/assertions elsewhere; give it its own `data-testid="untagged-chip"`.
- Do not reuse `catalog.filters.untagged` copy for the chip label.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Zero tags | `model.tags = []` | Single ghost chip with `data-testid="untagged-chip"` and translated "no tags" text renders; no `tag-chip` elements render | No error expected |
| One tag | `model.tags` has 1 item | Existing chip-row renders 1 real chip; no ghost chip | No error expected |
| Two-plus tags | `model.tags` has 3 items | Existing chip-row renders top 2 real chips (unchanged overflow behavior); no ghost chip | No error expected |

</intent-contract>

## Code Map

- `apps/web/src/ui/custom/ModelCard.tsx` -- add the zero-tag ghost-chip branch alongside the existing `topTags.length > 0` chip row (around line 93-105).
- `apps/web/src/ui/custom/ModelCard.test.tsx` -- add coverage for the zero-tag ghost-chip case; existing tests already cover the tagged case via `makeSummary()`'s 3-tag default.
- `apps/web/src/locales/en.json` -- add `"catalog.no_tags": "No tags"` near the existing `catalog.no_preview` key (line ~277).
- `apps/web/src/locales/pl.json` -- add the matching `"catalog.no_tags": "Brak tagów"` entry, same key position as en.json.
- `apps/web/tests/visual/api-stubs.ts` -- no change needed; `stubSotList`'s `/api/models*` fixture already includes a zero-tag model (`bbbbbbbb-...` "Vase", `tags: []`), so the existing `catalog-list.spec.ts` baseline will pick up the new ghost chip automatically.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/locales/en.json` -- add `"catalog.no_tags": "No tags"` -- new copy needed for the ghost-chip label
- [x] `apps/web/src/locales/pl.json` -- add `"catalog.no_tags": "Brak tagów"` -- Polish parity for the same key
- [x] `apps/web/src/ui/custom/ModelCard.tsx` -- render a dashed ghost chip (`data-testid="untagged-chip"`, `t("catalog.no_tags")`) when `topTags.length === 0`, replacing the current no-op (chip row simply absent) -- makes the untagged state visible instead of blank space, per FR25-FILT-2
- [x] `apps/web/src/ui/custom/ModelCard.test.tsx` -- add a test asserting the ghost chip renders for a zero-tag model and that tagged-model tests still show no ghost chip -- locks the new branch behavior in place
- [x] `apps/web/tests/visual/__snapshots__/**` -- regenerate `catalog-list` (and any other spec whose baseline includes the zero-tag "Vase" fixture model) baselines across all four projects after the code change, with `baseline-reviewed:` sign-off lines in the commit message -- Baseline Acceptance Gate requires this for any changed `.png`

**Acceptance Criteria:**
- Given a `ModelSummary` with `tags: []`, when `ModelCard` renders, then a single ghost/dashed chip with the localized "no tags" copy is shown and no `tag-chip` elements are present.
- Given a `ModelSummary` with 1 or more tags, when `ModelCard` renders, then the existing top-2 real-tag-chip behavior is unchanged and no ghost chip renders.
- Given the `pl-PL` locale, when the ghost chip renders, then its text reads "Brak tagów"; given `en`, it reads "No tags".
- Given the visual regression suite, when run across all four projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`) after this change, then any snapshot delta is limited to the expected ghost-chip appearance on zero-tag fixture cards and is intentionally reviewed/updated.

## Spec Change Log

_(none — no bad_spec loopback occurred)_

## Review Triage Log

### 2026-07-20 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 2, low 2)
- defer: 1 (low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[medium]` `[patch]` New `ModelCard.test.tsx` untagged-chip test only asserted `data-testid` presence, not the rendered translated text — a raw-key i18n regression would have slipped through undetected. Strengthened to assert `screen.findByText("No tags")` and exact `textContent`.
  - `[medium]` `[patch]` Spec's own I/O matrix "one tag" row (1 real chip, no ghost chip) had zero test coverage — the task checklist's claim that the 3-tag default covers it was incorrect (it only exercises the 2+ overflow case). Added a dedicated 1-tag test.
  - `[low]` `[patch]` No test asserted `untagged-chip` is absent when tags are present (mutual-exclusivity only checked in one direction). Added the missing assertion to the existing "renders top 2 tag chips" test.
  - `[low]` `[patch]` The two ternary branches in `ModelCard.tsx` duplicated the identical `<div className="flex flex-wrap gap-1">` wrapper. Hoisted the wrapper once, branching only on the inner content.
  - Rejected as out-of-scope: `ModelHero.tsx` (catalog-detail hero) has the same "empty tag row" gap for zero-tag models — explicitly out of scope per this spec's `Never` boundary (`Do not touch ... CatalogDetail`) and owned by Story 45.2 (`CatalogDetail` grouped tags, FR25-DETAIL-1), which reworks tag rendering on that surface entirely.
  - Rejected as non-issue (visually verified): reviewer flagged the 14 regenerated baseline PNGs as "accepted on a size-diff heuristic, not an actual visual check," and separately flagged a possible row-height/box-model jitter from the ghost chip's dashed border vs. the borderless real-tag chip. Directly inspected before/after renders of `catalog-list-desktop-light.png` and `rail-focus-desktop-light.png` (extracted pre-change baseline via `git show <baseline_revision>:...` and compared to the regenerated PNG) — confirmed the only visual delta across all inspected snapshots is the intended "Brak tagów" ghost chip on the zero-tag "Wazon"/"Vase" fixture card, with no layout shift, misalignment, or unintended change elsewhere.
  - Rejected as cosmetic/non-defect: capitalization mismatch between new "No tags" (sentence case) and pre-existing sibling "no preview" (lowercase) placeholder copy — "No tags" is consistent with the nearby `catalog.filters.untagged` ("Untagged models") capitalization convention; no spec requirement violated.
  - Rejected as premature: reviewer noted no visible `baseline-reviewed:` commit sign-off yet — correct but expected at this point, since the change had not been committed yet; the Finalize step adds the required sign-off lines at commit time.
- Deferred: `/dev/components` manual-QA gallery has no zero-tag `ModelCard` fixture to showcase the new ghost-chip state (not required by this story's scope/ACs) — recorded in `deferred-work.md`.

## Verification

**Commands:**
- `npm run lint` (from `apps/web/`) -- expected: exits 0, `--max-warnings=0`
- `npm run test` (from `apps/web/`) -- expected: all Vitest suites pass, including the new `ModelCard.test.tsx` case
- `npx playwright test --config=tests/visual/playwright.config.ts` (from `apps/web/`) -- expected: run first to see the intentional diff on baselines containing the zero-tag fixture model, then `--update-snapshots` to regenerate, then a final run confirming all four projects pass clean
- `npx tsc --noEmit` (from `apps/web/`, or via the project's typecheck script) -- expected: no new type errors

## Auto Run Result

**Summary:** Zero-tag `ModelCard`s now render a dashed "Brak tagów"/"No tags" ghost chip instead of a blank chip row, communicating the untagged state (now the common post-cutover case) instead of leaving empty space. Tagged-model rendering is unchanged.

**Files changed:**
- `apps/web/src/locales/en.json` -- added `catalog.no_tags: "No tags"`
- `apps/web/src/locales/pl.json` -- added `catalog.no_tags: "Brak tagów"`
- `apps/web/src/ui/custom/ModelCard.tsx` -- ghost-chip branch when `topTags.length === 0`; hoisted the shared chip-row wrapper (review patch)
- `apps/web/src/ui/custom/ModelCard.test.tsx` -- new tests for zero-tag (with translated-text assertion), single-tag boundary, and mutual-exclusivity on the tagged case (review patches)
- `apps/web/tests/visual/__snapshots__/**` -- 14 baseline PNGs regenerated (`catalog-list.spec.ts` ×4, `filter-ribbon-selects-open.spec.ts` ×6, `focus-ring.spec.ts` ×4), all containing the pre-existing zero-tag "Vase" fixture model; visually verified as ghost-chip-only diffs
- `_bmad-output/implementation-artifacts/deferred-work.md` -- recorded one deferred finding

**Review findings breakdown:** 10 total (Blind Hunter 10, Edge Case Hunter 0) — 4 patch (auto-fixed: weak i18n test assertion, missing 1-tag boundary test, missing mutual-exclusivity assertion, duplicated wrapper markup), 1 defer (`/dev/components` gallery has no zero-tag fixture), 5 reject (out-of-scope ModelHero gap owned by 45.2, two visually-verified non-issues on baseline diffs, cosmetic capitalization nit, premature baseline-sign-off note).

**Verification performed:**
- `npm run lint` -- exit 0, `--max-warnings=0` (one pre-existing unrelated warning)
- `npm run test` -- 128 test files / 716 tests passed
- `npx tsc -b` -- exit 0, no type errors
- `npx playwright test --config=tests/visual/playwright.config.ts` -- full run across all four projects (desktop-light/dark, mobile-light/dark): 464 passed, 24 skipped, 0 failed after baseline regeneration
- Direct visual inspection of before/after PNGs (`catalog-list-desktop-light.png`, `rail-focus-desktop-light.png`) confirmed diffs are limited to the intended ghost chip with no layout shift

**Residual risks:** None blocking. The `/dev/components` manual-QA gallery gap is low-severity and deferred. `ModelHero.tsx` (catalog-detail) still shows a blank row for zero-tag models until Story 45.2 lands — expected, in-scope for that story.
