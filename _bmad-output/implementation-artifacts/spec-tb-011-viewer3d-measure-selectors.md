---
title: 'TB-011 — Tighten viewer3d-measure selectors for PL locale (close visual-regression suite)'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
final_commit: 'c0daf7a'
note: 'Rolled into consolidated TB-010+011+012 commit c0daf7a after autonomous mode authorized scope merging. Selector swaps applied verbatim per this spec; additionally measure-pp regex updated for post-34125a4 layout. See TB-010 Spec Change Log entry 2026-05-12-B for full close-out narrative.'
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** TB-010 partial (commit `10bc3de`) closed 10 of 26 viewer3d failures (snapshot drift). 16 remain on `viewer3d-measure-pp` (4) and `viewer3d-measure-plane` (12) — NOT snapshot drift, real test-logic failures hidden under the rot:

1. `viewer3d-measure-pp.spec.ts:32` uses `getByRole("button", { name: /pomiar|measure/i })` — under PL locale the regex matches **at least 4 buttons**: `viewer3d.tooltip.measure` ("Pomiar (punkt do punktu)") + 4 mode buttons (`measure.mode.p2p` / `p2pl` / `pl2pl` / `diameter` — all PL labels begin with "Pomiar"). Strict-mode violation: 3+ resolved elements.
2. `viewer3d-measure-plane.spec.ts:34/45/62` uses `getByRole("button", { name: /point.to.plane|p2pl/i })` — pre-i18n EN-only regex; PL label is "Pomiar punkt-do-płaszczyzny" which contains neither `point.to.plane` nor `p2pl`. `locator.click` times out; cascade-blocks all 3 sub-tests.

Tooltipy/labels added in `7fe96bd` (diameter mode) and refactored in `8a02101` (design-token cleanup) — these expanded the button population without test selector updates.

**Approach:** Two pure test-side selector tightenings (zero component edits — labels are correct PL i18n via `viewer3d.tooltip.measure` and `viewer3d.measure.mode.p2pl`):

(a) `viewer3d-measure-pp.spec.ts:32` — replace `/pomiar|measure/i` with `^pomiar \(punkt do punktu\)/i` (exact match for toolbar measure button — `viewer3d.tooltip.measure` PL = "Pomiar (punkt do punktu)").

(b) `viewer3d-measure-plane.spec.ts:34, 45, 62` — replace `/point.to.plane|p2pl/i` with `/punkt-do-płaszczyzny/i` (matches PL `viewer3d.measure.mode.p2pl` = "Pomiar punkt-do-płaszczyzny"; substring also works for any future EN/PL drift).

After selector fixes resolve, regenerate ~16 viewer3d-measure-* snapshots after diff inspection. **This closes the entire visual-regression suite** (sessions + 8 catalog/dev + viewer3d-modal-* + viewer3d-mobile + viewer3d-inline-loaded from TB-009/010 + viewer3d-measure-* from TB-011 = ALL GREEN on 4 projects).

## Boundaries & Constraints

**Always:**
- Selectors locale-aware (PL match or PL+EN regex when PL label is non-trivial).
- Snapshot regen only AFTER selector fixes resolve (else stale capture).
- Diff inspection of ≥4 representative snapshots (1 per project) before `--update-snapshots=all`.
- ESLint `--max-warnings=0` clean; `npx tsc --noEmit` clean; locale parity preserved (no locale changes).
- ALL 4 projects GREEN at end (closes the suite — no remaining viewer3d failures).

**Ask First:**
- Any change to `apps/web/src/modules/catalog/components/viewer3d/**` source.
- Any selector that requires a component aria-label addition.
- Any i18n key edit.

**Never:**
- `test.skip` / `test.fixme`.
- Touch component source — selectors are correct PL i18n already.
- Edit i18n keys.
- `--update-snapshots` blindly without ≥4-diff inspection.
- Regen snapshots before selectors are GREEN.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error Handling |
|----------|---------------|----------|----------------|
| measure-pp toolbar button under PL | locale=pl-PL, dialog open | Selector matches exactly 1 button (`Pomiar (punkt do punktu)` toolbar tooltip) | If still ambiguous → tighten regex anchor or scope to toolbar role |
| measure-plane p2pl mode under PL | locale=pl-PL, dialog open | Selector matches exactly 1 button (`Pomiar punkt-do-płaszczyzny` mode) | If matches multiple modes → anchor on full mode name |
| Snapshot post-fix | All measure-* tests run | Each test reaches `toHaveScreenshot`, snapshot captured + matches OR is regenerated | Drift beyond locale text → HALT |
| Tolerance popover (downstream) | After p2pl button works | `/tolerance|tolerancja/i` regex matches (already correct, just needed p2pl to pass first) | If still fails → separate selector issue |
| Cascade unblock check | All 3 measure-plane sub-tests pass after p2pl fix | Verified via full `viewer3d-measure-plane.spec.ts` run | If sub-tests pass independently but not together → `beforeEach` issue |

</frozen-after-approval>

## Code Map

- `apps/web/tests/visual/viewer3d-measure-pp.spec.ts:32` — single line: `name: /pomiar|measure/i` → `name: /^pomiar \(punkt do punktu\)/i`.
- `apps/web/tests/visual/viewer3d-measure-plane.spec.ts:34, 45, 62` — three identical lines: `name: /point.to.plane|p2pl/i` → `name: /punkt-do-płaszczyzny/i`.
- `apps/web/tests/visual/__snapshots__/viewer3d-measure-pp.spec.ts/` — 4 PNGs regenerated.
- `apps/web/tests/visual/__snapshots__/viewer3d-measure-plane.spec.ts/` — 12 PNGs regenerated (3 sub-tests × 4 projects).

Out of scope (must NOT touch): all `apps/web/src/**`, locales, other spec files, playwright config.

## Tasks & Acceptance

**Execution** (strict order):

- [ ] `viewer3d-measure-pp.spec.ts:32` — selector swap to PL exact-match.
- [ ] `viewer3d-measure-plane.spec.ts:34, 45, 62` — selector swap to PL substring (3 occurrences).
- [ ] Lint + tsc clean: `cd apps/web && npm run lint && npx tsc --noEmit`.
- [ ] Run measure specs WITHOUT regen: `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts viewer3d-measure-pp.spec.ts viewer3d-measure-plane.spec.ts --reporter=list 2>&1 | tee /tmp/tb011-pre-regen.log`. Expected: failures only on `toHaveScreenshot` (selectors green now). Grep log for `Error:` lines — should be zero `strict mode violation` and zero `locator.click ... timeout`.
- [ ] Inspect ≥4 representative diffs from the failing snapshots (1 per project). Confirm = palette/icons/MeasureSummary deltas + correct PL flow only. STOP if drift beyond expected.
- [ ] Targeted regen: same command + `--update-snapshots=all`.
- [ ] Full re-run `npm run test:visual` from `apps/web/` — **ALL 4 projects GREEN, 0 failures, 14 pre-existing skips unchanged**. Closes the suite.
- [ ] Sanity: `git diff --name-only c35b5dc HEAD -- apps/web/src/` — empty (TB-011 is test-only).
- [ ] `grep -nE "test\.(skip|fixme|only)" apps/web/tests/visual/*.spec.ts` — no new entries.

**Acceptance Criteria:**
- Given the merge commit, `npm run test:visual` returns **0 failures** across all 4 projects (closes the suite — full visual regression GREEN).
- 14 pre-existing skips unchanged.
- Merge diff filtered to `apps/web/src/` is empty.
- No `name` regex matches an EN-only literal in any modified spec.
- Selector pattern documented in commit message: PL-string match strategy chosen because labels are non-ambiguous PL i18n.

## Spec Change Log

<!-- Empty until first bad_spec loopback. -->

## Design Notes

**Why exact PL match (not role-only):** measure-pp toolbar shares a parent with 4 mode buttons all named "Pomiar X" — role-only is hopelessly ambiguous. Anchored regex on full PL toolbar tooltip is the surgical fix. Sister tests (`viewer3d-modal-*`) work because they target dialog-level controls without this populated-toolbar context.

**Why PL substring for p2pl (not anchored):** "Pomiar punkt-do-płaszczyzny" is unambiguous (only one button has "punkt-do-płaszczyzny" in name). Substring is robust to future label tweaks while staying locale-pinned. Could also retrofit `|punkt.do.płaszczyzny` to keep the EN-or-PL pattern, but EN no longer renders so it's dead code.

**Why no component aria-label additions:** The PL i18n labels ARE the canonical accessible names. Tests should respect that, not impose test-only synthetic labels.

**Closes the loop:** TB-009 → TB-010 → TB-011 chain restores the full visual-regression baseline (~66 → 0 failures) corrupted by `212c025` UI-review batch. After this ships, future UI PRs can rely on visual regression as a real gate.

## Verification

**Commands** (from `apps/web/`):
- `npm run lint` — 0 warnings.
- `npx tsc --noEmit` — 0 errors.
- `npx playwright test --config=tests/visual/playwright.config.ts viewer3d-measure-pp.spec.ts viewer3d-measure-plane.spec.ts` — gate (selectors green, only snapshot fails).
- After inspection: same + `--update-snapshots=all`.
- `npm run test:visual` — full suite, **0 failures, all 4 projects GREEN**, 14 skips unchanged.
- From repo root: `git diff --name-only HEAD~ HEAD -- apps/web/src/` — empty.

**Manual checks:**
- Open Playwright HTML report; spot-check 4 diffs (one per project).
- Final: `npm run test:visual` final-state grep for `failed` should yield only zeroes.
