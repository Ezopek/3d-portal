---
title: 'Story 47.1 — i18n cutover: remove dead category-filter keys'
type: 'chore'
created: '2026-07-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '693c7af3ddc000992a70e52eee3c3dae9bba05a8'
final_revision: '4d7f2348ecbfeabdd67c97840f72f7aea0192145'
---

<intent-contract>

## Intent

**Problem:** The locale files still carry two category-filter i18n keys (`catalog.filters.category`, `a11y.allCategories`) whose only consumer is `CategoryTreeSidebar`, a component orphaned since the facet-tag catalog rebuild (E41–E46): it is not imported anywhere except its own test file, and `CatalogList` renders `FacetSidebar` exclusively in production. Investigation confirmed the epic's other proposed i18n additions (`facets.*`, `matchAll`, `matchAny`, `untagged`, `noTags`, `tags.groupless`) and the admin tag-group keys were already shipped with genuine en+pl parity in E43/E44/E46; `openCategories` never existed under that name. The only real remaining work is deleting the two dead keys and the dead code that solely depended on them.

**Approach:** Delete `CategoryTreeSidebar.tsx` and `CategoryTreeSidebar.test.tsx` (dead code, zero production importers), then remove the two now-unused keys from both `apps/web/src/locales/en.json` and `apps/web/src/locales/pl.json`, preserving exact 1:1 key parity between the two files.

## Boundaries & Constraints

**Always:** Keep `en.json` and `pl.json` at identical key sets after the edit (verify count: 918 → 916 in both files). Delete the component and its test together in the same change — do not leave a broken test referencing a deleted component or removed keys.

**Block If:** A production route or component (outside the two files identified) is found to still import `CategoryTreeSidebar` at execution time — re-verify with a fresh grep before deleting; if found, HALT with status `blocked` and blocking condition `CategoryTreeSidebar has a live consumer`.

**Never:** Do not touch `Category` ORM entities, `Model.category_id`, backend category routes/services, or any other FE `Category*` type/hook (`useCategoriesTree`, `CategoryNode`, `CategoryTree` type) — all of that is explicitly owned by stories 47.4/47.5, not this one. Do not add the `facets.*`/`noTags`/`tags.groupless` keys the epic sketch mentions — they are not needed since the equivalent keys (`catalog.filters.untagged`, `catalog.no_tags`, `catalog.filters.ungrouped`) already ship with correct en+pl content. Do not touch `modules.admin.tagGroups.*` keys (E46-complete). Do not modify `catalog.filters.tags` (orphaned key, out of this story's boundary, not blocking).

</intent-contract>

## Code Map

- `apps/web/src/modules/catalog/components/CategoryTreeSidebar.tsx` -- dead component (167 lines), only consumer of the two keys being removed; delete.
- `apps/web/src/modules/catalog/components/CategoryTreeSidebar.test.tsx` -- test for the dead component; delete alongside it.
- `apps/web/src/locales/en.json` -- remove `"a11y.allCategories"` (line 28), `"catalog.filters.category"` (line 277), and `"common.all"` (line 16, orphaned by the same deletion — patched during review).
- `apps/web/src/locales/pl.json` -- remove `"a11y.allCategories"` (line 28), `"catalog.filters.category"` (line 277), and `"common.all"` (line 16, orphaned by the same deletion — patched during review).

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/components/CategoryTreeSidebar.tsx` -- delete file -- dead code, sole reason the two locale keys still exist
- [x] `apps/web/src/modules/catalog/components/CategoryTreeSidebar.test.tsx` -- delete file -- test-only consumer of the deleted component; leaving it would fail once the component/keys are gone
- [x] `apps/web/src/locales/en.json` -- remove the `"a11y.allCategories"` and `"catalog.filters.category"` entries -- keys have zero remaining consumers after the component deletion
- [x] `apps/web/src/locales/pl.json` -- remove the `"a11y.allCategories"` and `"catalog.filters.category"` entries -- mirrors the en.json removal to preserve parity

**Acceptance Criteria:**
- Given the repo after this change, when grepping `apps/web/src` for `CategoryTreeSidebar`, then there are zero matches.
- Given the repo after this change, when grepping `apps/web/src` for `catalog.filters.category` or `a11y.allCategories`, then there are zero matches in any `.ts`/`.tsx`/`.json` file.
- Given `en.json` and `pl.json` after this change, when comparing their top-level key sets, then they are identical (same key count, no key present in one file only).
- Given the existing Vitest suite, when run after this change, then it passes with no new failures (the deleted test's cases are removed, not left failing).

## Spec Change Log

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 1, low 0)
- defer: 2: (high 0, medium 0, low 2)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter found `common.all` (en.json/pl.json line 16) orphaned by the same `CategoryTreeSidebar` deletion this story performs — its sole consumer was that component. Verified zero remaining consumers repo-wide and removed the key from both locale files; parity re-verified at 915/915; full Vitest suite (788 tests) re-run green.

### 2026-07-22 — Repair pass (external Aider verify gate returned rc=3, no code change required)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found `sprint-status.yaml` (line 333) and this spec's own frontmatter disagreed on completion state (`done` vs `in-progress`/`in-review`) — an artifact of the prior pass's status having been reverted by the orchestrator after the external verify gate's parse failure, without the tracker being reverted to match. Reconciled by carrying this repair pass through to a consistent `done` close (both files) below.
  - `[low]` `[patch]` Blind Hunter found the `sprint-status.yaml` `done` entry for this story lacked the commit/test/gate-outcome annotation every neighboring entry carries. Added an annotation recording the final commit, review-pass tallies, and the external gate's actual (approving) verdict text.
  - `[low]` `[patch]` Blind Hunter found the `deferred-work.md` stale-doc entry claimed to have "confirmed both docs" referencing the deleted `CategoryTreeSidebar`, but a third file (`docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md`, a historical UI-rewrite proposal, not live docs) also names it. Reworded the entry to note the third reference and flag it for 47.3 to triage rather than assert an exhaustive count.
  - Not addressed (rejected as noise, with reasoning): the intent-contract's `catalog.filters.tags` boundary already documents and justifies leaving that orphaned key alone, so the "inconsistent treatment vs `common.all`" finding is not a defect; this repo's specs universally snapshot verification commands/counts at closure time rather than maintaining them as living checks, so the "hardcoded line numbers/counts will go stale" finding describes standard practice, not a gap; an unattributed `followup_review_recommended: false` is the norm across sibling specs (only stories that went through an explicit repair/re-review loop annotate it, per `spec-46-3`) so no gap exists; the deleted component's orphaned `sessionStorage` key (`catalog:tree-expand`) is inert client-side data with no consumer, no security/privacy impact, and no code path left to clear it retroactively.

**Note on this repair pass's trigger:** the prior pass's commit (`eceb4bc`) was already independently reviewed by the required external Aider gate and received an explicit `**Verdict:** APPROVE` (content: dead-code + orphaned-key removal correct and complete, one non-blocking documentation-discrepancy note). The gate's regex-based verdict parser did not recognize that bold-formatting variant of the verdict line and exited `rc=3` ("no explicit final verdict found"), which the orchestrator treated as a verification failure and reverted this spec's `status` for a repair pass. No code or locale-key change was needed or made in this pass; the diff since `baseline_revision` is unchanged from what Aider already approved, aside from the process/doc patches above.

## Verification

**Commands:**
- `grep -rn "CategoryTreeSidebar\|catalog\.filters\.category\|a11y\.allCategories" apps/web/src` -- expected: no output
- `cd apps/web && npx vitest run` -- expected: all pass, no failures, no leftover reference to the deleted test file
- `python3 -c "import json; a=set(json.load(open('apps/web/src/locales/en.json'))); b=set(json.load(open('apps/web/src/locales/pl.json'))); print(len(a), len(b), a==b)"` -- expected: `915 915 True` (916/916 before the review-pass `common.all` patch; 915/915 after)

## Auto Run Result

Status: done

**Summary:** Removed the two locale keys (`catalog.filters.category`, `a11y.allCategories`) whose sole consumer was `CategoryTreeSidebar` — a component orphaned since the facet-tag catalog rebuild (E41-E46 moved the live catalog UI to `FacetSidebar`) — and deleted the component and its test. Investigation showed every other i18n addition the epic sketch called for was already shipped with real en+pl parity in prior stories, so this story's real scope was the dead-key/dead-code removal only. This repair pass made no code or locale changes: the external Aider verify gate had returned `rc=3` against the already-committed, already-approved diff because its verdict-parsing regex didn't recognize the model's `**Verdict:** APPROVE` bold-formatting variant — a gate tooling gap, not a content rejection. This pass ran a fresh independent review (Blind Hunter + Edge Case Hunter) over the unchanged diff and patched three process/documentation inconsistencies surfaced by it.

**Files changed (this repair pass):**
- `_bmad-output/implementation-artifacts/spec-47-1-i18n.md` -- status reconciled to `done`, repair-pass Review Triage Log entry added, this Auto Run Result
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `done` entry annotated with final commit + review/gate evidence
- `_bmad-output/implementation-artifacts/deferred-work.md` -- corrected an overclaiming stale-doc entry (a third historical reference exists) and added one new deferred entry (epic-context determinism-rule scope is ambiguous for non-destructive stories)
- Removed two stray untracked `apps/web/vitest.config.d.ts` / `vitest.setup.d.ts` build artifacts left over from a prior local `tsc -b` run (not part of any commit, unrelated to this story)

No `apps/web/src` code or locale file was touched in this pass — the implementation from the prior pass (commit `eceb4bc`) was independently re-verified byte-for-byte against the spec's Tasks & Acceptance and found complete.

**Review findings breakdown (this repair pass):** 3 patch (1 medium — tracker/spec status contradiction, resolved by this pass's close-out; 2 low — missing gate-evidence annotation, deferred-work overclaim), 1 defer (epic-context determinism-rule wording ambiguous for non-migration stories), 4 rejected as noise (the `catalog.filters.tags` asymmetry is already justified by the frozen intent-contract's own boundary note; hardcoded verification counts are this repo's standard closure-snapshot convention; unattributed `followup_review_recommended: false` is the sibling-spec norm, not a gap; the deleted component's orphaned `sessionStorage` key is inert with no consumer and no accessible fix path).

**Verification performed:** Independently re-ran and confirmed all three of this spec's Verification commands (zero grep matches for the deleted component/keys, `915 915 True` locale parity, full Vitest suite 136 files / 788 tests passing). Re-confirmed via a whole-repo grep (not just `apps/web/src`) that no code, barrel re-export, dynamic import, or Storybook story references the deleted component; remaining matches are historical docs/specs only.

**Residual risks:** None for this story's own scope. The one new deferred item (epic-context determinism-rule scope) is informational and non-blocking — it affects how future E47 stories interpret a cached planning-context note, not this story's correctness.

