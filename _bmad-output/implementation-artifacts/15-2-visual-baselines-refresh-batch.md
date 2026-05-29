---
title: 'Story 15.2 — Visual-regression baseline batch refresh (86 deterministic failures)'
type: 'bugfix'
status: 'ready-for-dev'
created: '2026-05-22'
epic: 15
initiative: 10
story_id: '15.2'
story_key: '15-2-visual-baselines-refresh-batch'
predecessor_scp: '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-22-init10.md (Initiative 10 Epic 15 Story 15.2; SCP §4 + §C.3 + Appendix A Story 15.2)'
realizes:
  - 'FR10-TEST-DETERMINISM-PLAYWRIGHT-1 (full)'
  - 'NFR10-DETERMINISM-1'
  - 'NFR10-SCOPE-1'
predecessor_commits:
  - 'd3831e9 — Story 15.1 primary fix (pytest threading deadlock close)'
  - '352507f — Story 15.1 Codex P2 fix-up (sequential assertion tightening)'
context:
  - 'apps/web/tests/visual/ — playwright visual-regression test suite'
  - 'apps/web/tests/visual/__snapshots__/ — baseline PNGs (4 projects × N specs)'
  - 'apps/web/tests/visual/anon-login-only.spec.ts — 8 deterministic page.waitForURL timeouts (separate class from stale-baseline)'
auto_approval_directive: 'Operator standing approval per SCP execution_directive "lecisz do końca samemu" (2026-05-22); ITCM autonomous mode per memory [[feedback_itcm_autonomous_mode]]. Inline-authored sibling story within Epic 15 per autonomous chain efficiency (entry story 15.1 used full bmad-create-story; sibling stories drive inline per ITCM ownership).'
---

## Story 15.2 — Visual-regression baseline batch refresh (86 deterministic failures)

**As an** ITCM owning the autonomous Init 10 chain,
**I want** the 86 deterministic playwright visual-regression failures classified and resolved — stale baselines regenerated (post-Init 5/6/7/8 UI evolution) and the 8 `page.waitForURL` timeouts in `anon-login-only.spec.ts` fixed,
**so that** Epic 15's acceptance gate is met (full visual suite passes deterministically 3× consecutive both standalone and via check-all.sh hook context) and downstream Init 10 epics develop on reliable visual signal.

### Story Requirements

Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 10 § Epic 15 § Story 15.2. Audit subagent recon 2026-05-22: 86 deterministic-FAIL (variance=0) + 234 PASS + 24 skipped / 344 total. Zero true non-determinism. 78 stale-baseline drift + 8 anon-login-only `page.waitForURL` timeouts.

#### Acceptance Criteria

**AC-1 (FR10-TEST-DETERMINISM-PLAYWRIGHT-1):** `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` returns exit 0 in <120s wall-clock, **3 consecutive invocations**. All baselines pass, all specs green.

**AC-2 (FR10-TEST-DETERMINISM-PLAYWRIGHT-1 — hook context):** `infra/scripts/check-all.sh visual` (or the project's standard CI-equivalent visual invocation) returns exit 0, **3 consecutive invocations**. Hook context and standalone context produce identical pass/fail verdict (per Story 14.3 precedent — both contexts at equal scope).

**AC-3 (Phase 1 — Classification triage, no fix yet):** Capture the 86 failures into a 3-category triage in Dev Agent Record:

- **Stale baseline (UI evolved legally):** regen via `--update-snapshots`; sign-off per Baseline Acceptance Gate (`baseline-reviewed: <basename>, Claude/Ezop, 2026-05-22` per project-context.md UI Quality Gates).
- **Real UX regression:** STOP and surface to operator. Do NOT regen a snapshot that masks a real bug. If >5 regressions discovered, HALT and surface as Init-10-amending discovery (SCP §A Story 15.2 boundary).
- **`anon-login-only` timeouts (8 expected):** spec-level fix — `page.waitForURL` assertion timing changed post-Init 5/6 cutover (auth flow timing or URL pattern). Inspect spec, verify current portal behavior at `https://3d.ezop.ddns.net`, update spec assertion.

The triage matrix goes verbatim into Dev Agent Record under "Phase 1 classification" with one row per failing spec/baseline.

**AC-4 (Phase 2 — Stale baseline regen):** Apply `--update-snapshots` only to the classified stale-baseline set (78 of 86 expected). For each regenerated PNG, commit-message trailer line: `baseline-reviewed: <basename>, Claude, 2026-05-22`. The `_check-baseline-review.mjs` pre-commit hook enforces this gate.

**AC-5 (Phase 3 — anon-login-only spec fix):** Update `apps/web/tests/visual/anon-login-only.spec.ts` for the 8 failing `page.waitForURL` timeouts. Investigation steps:
1. Read current spec to understand what URL pattern + timeout it expects.
2. Reproduce manually (or via agent-browser) — what URL does anonymous login actually land on post-cutover (Init 6 default-deny shipped)?
3. Update spec assertion to match current behavior. Likely shapes: (a) shorter wait (auth fires faster); (b) different URL pattern (route changed); (c) different state-detection mechanism (URL → DOM element).

**AC-6 (Phase 4 — Verify per NFR10-DETERMINISM-1):**
- `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` → exit 0, 3× consecutive (standalone)
- `infra/scripts/check-all.sh visual` → exit 0, 3× consecutive (hook context)
- Standalone + hook context produce identical pass/fail verdict
- Logged in Dev Agent Record with timestamps + wall-clock + pass-count per run

**AC-7 (Vitest no-regression):** `cd apps/web && timeout 300 npm run test` returns exit 0 with 94 files / 408 tests pass (matches Story 15.1 baseline).

**AC-8 (No production-code changes per NFR10-SCOPE-1):** Story 15.2 touches `apps/web/tests/visual/__snapshots__/**/*.png` (baseline regen) + `apps/web/tests/visual/anon-login-only.spec.ts` (spec fix). NOT touched: any `apps/web/src/**` production code. If Phase 1 reveals real UX regressions (>5), HALT per AC-3.

**AC-9 (Codex review):** Pre-merge `codex review --commit <SHA>` PASS. Either CLEAN or all P0/P1 findings closed via fix-up commits before merge.

**AC-10 (NFR10-VISUAL-VERIFICATION-1 — N/A):** Test-infrastructure-only; no production UI surface added/modified.

### Developer Context

#### Failure inventory (audit subagent 2026-05-22)

**78 stale-baseline failures across 12 specs:**

- `agents-info-dialog.spec.ts`
- `anon-login-only.spec.ts` (some specs in this file are stale-baseline, others are timeout — disambiguate in Phase 1)
- `catalog-detail.spec.ts`
- `catalog-list.spec.ts`
- `dev.spec.ts`
- `empty-states.spec.ts`
- `focus-ring.spec.ts`
- `login-2fa-verify.spec.ts`
- `register.spec.ts`
- `reset-password.spec.ts`
- `v2-placeholders.spec.ts`
- `viewer3d-mobile.spec.ts`

Root cause class: Initiative 5/6/7/8 closed substantial UI changes (admin invites unblock, settings hub, sessions UX, display-name registration, mobile carousel arrows, thumbnail pipeline srcSet). These cascade through every spec that screenshots a shared component (TopBar, UserMenu, AppShell, catalog cards, model gallery). Baselines were not refreshed at Init 7/8/9 close because the hook-context flake (Story 14.3) masked the cascade.

**8 deterministic timeouts in `anon-login-only.spec.ts`:** `page.waitForURL` timing or URL-pattern mismatch post-Init-6 default-deny cutover. Spec-level fix required, not baseline regen.

#### Constraints from project-context.md

- **Visual regression matrix is fixed (4 projects):** `desktop-light`, `desktop-dark`, `mobile-light` (Pixel 5), `mobile-dark`. Locale `pl-PL`, timezone `Europe/Warsaw`.
- **API is stubbed for visual tests** via `apps/web/tests/visual/api-stubs.ts` (+ default routes in `apps/web/tests/visual/_test.ts`). Do not modify the stub layer unless investigation reveals it's the bug source.
- **Snapshot updates:** `npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots`. Inspect `__snapshots__/` diffs intentionally per project-context.md L112.
- **Baseline Acceptance Gate** (project-context.md L245): any commit touching `apps/web/tests/visual/__snapshots__/**/*.png` MUST include `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` trailer per changed PNG. Enforced by pre-commit hook.
- **Failure-mode triage before regen** per memory [[feedback_visual_failure_mode_triage]]: grep failure log for snapshot-diff vs timeout vs strict-mode-violation breakdown BEFORE deciding to `--update-snapshots`. Different failure classes have different fixes.

#### Files in scope

**Phase 2 — stale baseline regen:**
- `apps/web/tests/visual/__snapshots__/**/*.png` (78 PNGs across 12 specs × 4 projects, possibly more)

**Phase 3 — spec fix:**
- `apps/web/tests/visual/anon-login-only.spec.ts` (8 `page.waitForURL` assertions)

**Files NOT in scope:**
- Any `apps/web/src/**` production code (no UX-regression masking)
- `apps/web/tests/visual/_test.ts` (fixture layer; do not touch unless investigation reveals it's the bug source)
- `apps/web/tests/visual/api-stubs.ts` (stub layer; same)

#### Verification command sheet

```bash
# Phase 1 — capture failure log for classification
cd /home/ezop/repos/3d-portal/apps/web
npx playwright test --config=tests/visual/playwright.config.ts --reporter=list 2>&1 | tee /tmp/visual-triage.log

# Phase 1 — classify failures
grep -E "FAIL|✘|TimeoutError" /tmp/visual-triage.log | sort -u

# Phase 2 — regen stale baselines (after classification)
cd /home/ezop/repos/3d-portal/apps/web
npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots

# Phase 3 — spec fix for anon-login-only (manual edits)
# inspect: apps/web/tests/visual/anon-login-only.spec.ts
# reproduce: navigate https://3d.ezop.ddns.net manually + agent-browser CDP
# update spec timing/URL assertion

# Phase 4 — verification (standalone)
cd /home/ezop/repos/3d-portal/apps/web
for i in 1 2 3; do
  echo "=== Run $i ==="
  time npx playwright test --config=tests/visual/playwright.config.ts
  [ $? -ne 0 ] && { echo "FAIL"; break; }
done

# Phase 4 — verification (hook context)
cd /home/ezop/repos/3d-portal
for i in 1 2 3; do
  echo "=== Run $i ==="
  time infra/scripts/check-all.sh visual
  [ $? -ne 0 ] && { echo "FAIL"; break; }
done

# AC-7 — vitest no-regression
cd /home/ezop/repos/3d-portal/apps/web
timeout 300 npm run test
```

### References

- Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-22-init10.md` § Appendix A Story 15.2 + § Appendix C.3.
- Source epics.md: `_bmad-output/planning-artifacts/epics.md` § Initiative 10 § Epic 15 § Story 15.2.
- Recon subagent (test-flake landscape audit) 2026-05-22: 86 deterministic-FAIL split 78 stale + 8 anon-login-only timeouts; zero true flake.
- Story 14.3 precedent: hook-context vs standalone scope-disambiguation (commit `313dd33`); identical-scope produces identical-verdict; stale-baseline-only outcome.
- Memory entries:
  - [[feedback_visual_failure_mode_triage]] — Phase 1 classification before regen.
  - [[feedback_frontend_visual_verification]] — visual-verification gate forward contract (does NOT apply to Story 15.2 — test-infra only).
  - [[feedback_itcm_autonomous_mode]] — ITCM ownership pattern.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) + ITCM autonomous mode 2026-05-22.

### Phase 1 Classification

To be filled during dev.

### Phase 2 Stale Baseline Regen

To be filled during dev.

### Phase 3 anon-login-only Spec Fix

To be filled during dev.

### Phase 4 Verification

To be filled during dev — AC-1 (3× standalone) + AC-2 (3× hook context) + AC-7 (vitest) results.

### Codex Review

To be filled post-commit.

### Debug Log References

To be filled during dev.

### Completion Notes List

To be filled during dev.

### File List

To be filled during dev.
