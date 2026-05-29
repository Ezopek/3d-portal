---
title: 'TB-013 close-out + orphan baseline cleanup'
type: 'chore'
created: '2026-05-17'
status: 'done'
commit: 'eb3ee4b'
review_verdict: 'clean (3 BMAD subagents + Codex independent — no actionable findings; 1 P1 patch applied at commit-message level pre-commit)'
baseline_commit: '7787d5229d28c6e801057e8d434d8faf7b75e28c'
context:
  - '{project-root}/_bmad-output/triage-backlog.md'
  - '{project-root}/_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-13.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** TB-013 (api-stubs.ts gap for list-page background fetches) was raised on 2026-05-13 when visual-test runs spammed `ECONNREFUSED 127.0.0.1:8000` for `/api/auth/me`, `/api/categories`, `/api/tags?limit=50`. On 2026-05-17 (today, 21:10 +0200) commit `d949d85` solved the underlying symptom more broadly by adding a Playwright fixture (`apps/web/tests/visual/_test.ts`) with a catch-all `**/api/**` → 404 stub plus an explicit `**/api/auth/me` → 401 stub. TB-013 is therefore obsolete-as-specified. The Epic 5 retrospective also surfaced 12 orphan PNG baselines on `describe.skip` specs (`files-tab-admin.spec.ts` × 8, `catalog-detail-admin.spec.ts` × 4) dating 2026-05-03; those PNGs sit unconsulted on disk and bloat the snapshot inventory.

**Approach:** One bookkeeping + cleanup commit: (1) delete the 12 orphan PNGs, (2) mark TB-013 as `done` in `_bmad-output/triage-backlog.md` with a citation to `d949d85`, (3) add a one-line tracking entry in `sprint-status.yaml`. No source-tree changes. No `apps/web/src/` touched. No `apps/web/tests/visual/*.ts` (specs/stubs) touched.

## Boundaries & Constraints

**Always:**
- Test-only commit: limited to deletions under `apps/web/tests/visual/__snapshots__/` and edits to two `_bmad-output/` files.
- Use `git rm` for the PNGs so the deletion is tracked by git (not just filesystem `rm`).
- Commit message format: `chore(web): orphan baseline cleanup + TB-013 close-out`.
- Skip `infra/scripts/deploy.sh` per `feedback_auto_deploy_dev.md` (test-only + tracking files; nothing ships to runtime).

**Ask First:**
- If `npm run test:visual` exit code is non-zero or the post-delete diff shows any newly-failing test, HALT and surface — the orphan-classification was wrong.

**Never:**
- Do NOT touch the `agents-info-dialog` / `viewer3d-*` / `sessions` baselines. They are live, exercised by un-skipped specs.
- Do NOT modify `apps/web/tests/visual/_test.ts` or any `api-stubs.ts` helper — d949d85 already shipped the proxy fix.
- Do NOT re-enable the `describe.skip` blocks in the two specs — those are scaffolds for Slices 3D/3E.
- Do NOT delete the spec files themselves; they preserve filenames for future reactivation.

</frozen-after-approval>

## Code Map

- `apps/web/tests/visual/__snapshots__/files-tab-admin.spec.ts/` — 8 orphan PNGs (default × 4 projects + pending × 4 projects), `describe.skip` parent spec
- `apps/web/tests/visual/__snapshots__/catalog-detail-admin.spec.ts/` — 4 orphan PNGs (× 4 projects), `describe.skip` parent spec
- `apps/web/tests/visual/files-tab-admin.spec.ts:5` — `test.describe.skip("files tab admin (deferred to Slice 3E)", …)`
- `apps/web/tests/visual/catalog-detail-admin.spec.ts:6` — `test.describe.skip("catalog detail admin (deferred to Slice 3E)", …)`
- `_bmad-output/triage-backlog.md` — TB-013 entry moves from "Active candidates" to "Declined / done" with d949d85 citation
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — append a `tb-013-closeout-orphan-baselines: done` entry under the TB-cleanup section
- `_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-13.md` — Part 2 tables for files-tab-admin + catalog-detail-admin (regen-action column flips to `deleted (tb-013 close-out 2026-05-17)`)

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/tests/visual/__snapshots__/files-tab-admin.spec.ts/` -- `git rm` all 8 PNGs -- orphan baselines for `describe.skip` spec
- [x] `apps/web/tests/visual/__snapshots__/catalog-detail-admin.spec.ts/` -- `git rm` all 4 PNGs -- orphan baselines for `describe.skip` spec
- [x] `_bmad-output/triage-backlog.md` -- move TB-013 entry from "Active candidates" to "Declined / done"; cite d949d85 as the resolution + this spec for the bookkeeping commit -- close-out
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- append `tb-013-closeout-orphan-baselines: done` entry with commit reference -- audit trail
- [x] `_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-13.md` -- update files-tab-admin (8 rows) + catalog-detail-admin (4 rows) regen-action cells -- audit consistency

**Acceptance Criteria:**
- Given the 12 PNGs are deleted, when `npm run test:visual` runs, then exit code is 0 and the run reports the same pass count as pre-delete (the deleted baselines belong to skipped tests, so the regression suite shouldn't notice).
- Given `git status` after deletion, when inspecting staged paths, then ONLY paths under `apps/web/tests/visual/__snapshots__/{files-tab-admin,catalog-detail-admin}.spec.ts/` and `_bmad-output/` appear; no `apps/web/src/`, no `apps/api/`, no `infra/`.
- Given `_bmad-output/triage-backlog.md` post-edit, when grepping for `TB-013`, then the entry sits under `## Declined / done` with `**Status:** done` and a citation line to commit `d949d85`.

## Verification

**Commands:**
- `git -C apps/web/tests/visual/__snapshots__ ls-files | grep -E 'files-tab-admin|catalog-detail-admin'` -- expected: empty after `git rm`
- `cd apps/web && npm run test:visual -- --reporter=line 2>&1 | tail -20` -- expected: `passed` count unchanged from pre-delete (164 passed baseline per d949d85 commit message)
- `git status --short` -- expected: only deletions under `apps/web/tests/visual/__snapshots__/{files-tab-admin,catalog-detail-admin}.spec.ts/` and modifications to `_bmad-output/triage-backlog.md`, `_bmad-output/implementation-artifacts/{sprint-status.yaml,baseline-integrity-audit-2026-05-13.md}`

## Design Notes

The `_bmad-output/` directory is gitignored on this repo (per `feedback_local_only_docs.md` — Michał keeps plans off the remote). So the triage-backlog + sprint-status edits don't go through CI/PR review; they're operator-local bookkeeping that travels with the dev box. Only the 12 PNG deletions land in the shipped git history. The commit message therefore emphasizes the PNG cleanup as the primary `chore(web)` payload, with TB-013 close-out mentioned in the body for audit-trail continuity.

Per the baseline-integrity-audit (Part 4 Surprises/follow-ups #2): "Operator should decide whether to delete now... Recommend deletion at the same time Story 5.11 commits its baseline regen." Story 5.11 already shipped (commit `017cd87`) without bundling the orphan cleanup; this spec catches up on that recommendation.

## Suggested Review Order

**Orphan justification**

- Confirm both parent specs are still skipped placeholders, not active tests.
  [`files-tab-admin.spec.ts:5`](../../apps/web/tests/visual/files-tab-admin.spec.ts#L5)

- Same check for the other deleted-baseline parent spec.
  [`catalog-detail-admin.spec.ts:6`](../../apps/web/tests/visual/catalog-detail-admin.spec.ts#L6)

**Audit trail**

- Inspect the 12 deleted rows — verdict flipped from "tbd (likely delete)" to "deleted 2026-05-17".
  [`baseline-integrity-audit-2026-05-13.md:79`](./baseline-integrity-audit-2026-05-13.md#L79)

- Files-tab-admin (×8) variant block.
  [`baseline-integrity-audit-2026-05-13.md:128`](./baseline-integrity-audit-2026-05-13.md#L128)

**TB-013 close-out narrative**

- New "## Declined / done" entry with d949d85 citation explaining the broader fix.
  [`triage-backlog.md:48`](../triage-backlog.md#L48)

- One-line sprint-status entry under "Post-Epic 5 TB cleanup".
  [`sprint-status.yaml:130`](./sprint-status.yaml#L130)

**Empirical evidence (already verified pre-commit)**

- `npm run test:visual` post-delete: 164 passed / 0 failed / 24 skipped / 0 ECONNREFUSED lines (~43s). Same pass count as d949d85's commit message ("164 passed"). No re-run needed — fold this number into the commit's audit trail.

