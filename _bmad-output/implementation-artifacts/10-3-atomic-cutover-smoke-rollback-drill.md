# Story 10.3: Atomic cutover execution + 4-scenario smoke run + rollback drill

Status: ready-for-dev

> **Story role:** THIRD Epic 10 story — **executes the production cutover atomically**: push sibling nginx commit → ssh .180 + git pull + nginx -t + nginx -s reload → smoke (4 scenarios per Decision J) → rollback drill (revert + reload + smoke + revert-the-revert + reload + smoke). Total cutover budget ≤5 minutes per NFR5-PERF-2; rollback ≤30s end-to-end per Decision K. Highest-risk story in Init 5 (live edge-config change to production). Depends on Story 10.2 (commit ready) + Story 10.1 (smoke ready). Story 10.4 is the closing commit AFTER this lands cleanly.

## Story

As the ITCM executing the atomic edge cutover with the audit gate already cleared,
I want **the cutover commit pushed + nginx reloaded on `.180` + the 4-scenario smoke verified PASS + the rollback drill verified PASS — all within ≤5 minutes wall-clock**,
so that **the portal transitions from LAN-only IP-allowlist gating to public-internet authenticated access (cookie+JWT + share-token + agent-runbook bypass preserved at app level), with a verified rollback path that can revert the change in ≤30s if any smoke scenario regresses**.

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §507-523 + Decision J + Decision K.

### AC1 — Cutover sequence (sequential, total ≤5 minutes per NFR5-PERF-2)

Execute in order:

1. **Sibling repo push.** `cd ~/repos/configs && git push origin main`. (Story 10.2 produced the commit locally.) Push completes; capture push timestamp T0.
2. **.180 git pull + nginx test + reload.** `ssh ezop@192.168.2.180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'`. (`~/configs` is the .180 deploy path of the sibling repo; verify before running.) `nginx -t` MUST PASS on the freshly-pulled commit (re-verifies syntax post-pull); `nginx -s reload` executes atomically (no traffic disruption). Capture reload timestamp T1.
3. **Smoke run.** `bash infra/scripts/cutover-smoke.sh` against `https://3d.ezop.ddns.net`. All 4 Decision J scenarios MUST PASS within ≤30s wall-clock. Capture smoke completion timestamp T2.
4. **Verdict.** If 4/4 PASS: proceed to AC2 rollback drill. If ANY FAIL: trigger AC3 immediate rollback (do NOT proceed to drill).

### AC2 — Rollback drill (verifies the revert path before close-out)

ONLY runs if AC1 step 4 verdict is PASS. Sequence:

1. **First revert.** `cd ~/repos/configs && git revert <cutover-sha> --no-edit && git push origin main`. (`--no-edit` per memory: `--no-edit` not valid for rebase, but valid for revert.)
2. **Reload + smoke.** `ssh ezop@192.168.2.180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'` → `bash infra/scripts/cutover-smoke.sh`. All 4 MUST PASS (this verifies the rollback works under the pre-cutover state — same as the pre-cutover baseline from Story 10.1 T7).
3. **Revert the revert (re-apply cutover).** `cd ~/repos/configs && git revert <revert-sha> --no-edit && git push origin main`.
4. **Reload + smoke.** Same as step 2. All 4 MUST PASS (this verifies the re-apply works — proves both directions are mechanical).

Total drill wall-clock budget: ≤30s end-to-end (Decision K). Drill timestamps captured.

### AC3 — Immediate rollback on AC1 step 3 FAIL

If ANY smoke scenario fails at AC1 step 3 (post-reload verification):

1. `cd ~/repos/configs && git revert <cutover-sha> --no-edit && git push origin main` IMMEDIATELY.
2. `ssh ezop@192.168.2.180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'`.
3. Re-run smoke; confirm 4/4 PASS post-rollback (proves we're back to pre-cutover state).
4. STOP — escalate to operator. The cutover is BLOCKED until the failing scenario is root-caused + fixed. Audit re-runs after fix sprint.

Drill steps in AC2 are SKIPPED on AC3 path (rollback is the recovery, not a drill).

### AC4 — Cutover-smoke artifact

`_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` (gitignored, NFR5-OBS-2 second-slot per memory). Format mirrors `2fa-recovery-drill-2026-05-20.md` (Story 7.6 NFR5-OBS-2 first slot). Sections:

1. **Title + Date + Operator** — `# Cutover smoke — 3d-portal edge cutover — YYYY-MM-DD` + `**Operator:** Ezop (autonomous ITCM mode)`.
2. **Sequence timeline** — T0 push / T1 reload / T2 smoke / T3 drill-end timestamps with deltas.
3. **Pre-cutover state** — pre-cutover smoke baseline (from Story 10.1 T7) + last-deploy SHA + git status of both repos.
4. **Cutover smoke** — Decision J table populated with per-scenario expected/actual/status/timestamp/request_id/audit-row-delta.
5. **Rollback drill** — drill scenarios 1-4 PASS lines + revert-the-revert verification + total drill window.
6. **Post-cutover state** — final SHA of both repos + verify `https://3d.ezop.ddns.net` reachable from an external (non-LAN) probe (e.g., `curl --resolve` from a non-LAN host, OR document why this verification step was deferred).
7. **Verdict line** — verbatim: `**E10 cutover complete** — sibling commit <sha> on configs/main; .180 nginx reloaded; smoke 4/4 PASS; rollback drill 4/4 + 4/4 PASS; cutover wall-clock <MM:SS> / drill wall-clock <SS>s.` (mirror epics §521 verbatim convention).

### AC5 — External-IP verification (the cutover's primary effect)

The smoke runs from the LAN — pre and post-cutover from LAN look identical (allowlist would have allowed either way). The CUTOVER'S primary effect is that **external IPs can now reach the portal**. AC4 §6 documents this:

- **If verified externally:** include the external-probe curl output (HTTP 200 + portal HTML body excerpt) in AC4 §6.
- **If deferred:** document the deferral reason (e.g., "external-IP probe deferred to operator post-merge — autonomous mode lacks NON-LAN probe capability without VPN tunneling out") + the verification operator runs.

### AC6 — Cutover-smoke artifact NOT committed

Per epics §522 verbatim ("Artifact committed to local `_bmad-output/` only (gitignored)"), the cutover-smoke artifact stays at `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md`. The sprint-status update IS committed (sprint-status is the persistent index).

## Files

### Created

- `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` — AC4 (gitignored).

### Modified

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flip `10-3-atomic-cutover-smoke-rollback-drill: ready-for-dev` → `done` with the cutover SHA + rollback drill PASS notes + cutover wall-clock measurement.

### Untouched

- Everything else in 3d-portal. No code changes. No alembic. No frontend. The sibling repo changes happen via `git push` of Story 10.2's pre-prepared commit + post-drill revert pair (both already authored).

## Tasks

### T1 — Pre-cutover checklist (operator-confirmable)

1. `cd ~/repos/configs && git log origin/main..HEAD` shows EXACTLY 1 pending commit (the Story 10.2 cutover commit).
2. `cd ~/repos/3d-portal && bash infra/scripts/cutover-smoke.sh` → 4/4 PASS (current pre-cutover state).
3. `ssh ezop@192.168.2.180 'cat ~/configs/nginx/3d.ezop.ddns.net.conf | head -25'` → confirm .180 is on the pre-cutover SHA.
4. Capture pre-cutover state to artifact AC4 §3.

**Done-When:** all four checks pass; artifact §3 written.

### T2 — Execute AC1 cutover sequence

1. `cd ~/repos/configs && git push origin main`. Capture T0.
2. `ssh ezop@192.168.2.180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'`. Capture T1.
3. `bash infra/scripts/cutover-smoke.sh`. Capture T2 + 4-scenario verdicts.
4. If 4/4 PASS → T3 drill. If any FAIL → T4 immediate rollback.

### T3 — Execute AC2 rollback drill (ONLY if T2 PASS)

1. `cd ~/repos/configs && git revert HEAD --no-edit && git push origin main`. Capture revert-sha.
2. SSH `.180` + git pull + nginx -t + nginx -s reload + smoke. Capture drill-T1.
3. `cd ~/repos/configs && git revert HEAD --no-edit && git push origin main`. Capture revert-the-revert-sha.
4. SSH `.180` + git pull + nginx -t + nginx -s reload + smoke. Capture drill-T2.
5. Confirm 4/4 PASS on both drill smokes; capture drill wall-clock budget (target ≤30s end-to-end).

**Done-When:** drill complete; artifact §5 written.

### T4 — Immediate rollback (ONLY if T2 FAIL)

1. `cd ~/repos/configs && git revert HEAD --no-edit && git push origin main`.
2. SSH `.180` + git pull + nginx -t + nginx -s reload + smoke.
3. Confirm 4/4 PASS post-rollback (proves pre-cutover state restored).
4. STOP — escalate. Artifact §4 + §5 document the FAIL + rollback evidence.

### T5 — Write cutover-smoke artifact

Per AC4 sections 1-7. File at `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md`.

### T6 — 3d-portal close-out commit

`chore(infra): record E10 cutover smoke + rollback drill PASS (Story 10.3)`. Sprint-status update only. Push to origin/main. Deploy-skip-gate range check WILL skip (no app code changed).

**Done-When:** 3d-portal main has the close-out commit; cutover artifact lives in _bmad-output/; sibling repo HEAD is at the re-applied cutover SHA (NOT the revert SHA — Story 10.3 closes with cutover IN EFFECT).

## Test Plan

The story IS the test. Pass criteria:
- AC1 PASS verdict: 4/4 smoke scenarios PASS post-reload.
- AC2 PASS verdict: 4/4 + 4/4 drill smokes PASS.
- AC4 artifact exists + contains the verdict line verbatim.
- Total cutover wall-clock <5 minutes per NFR5-PERF-2.
- Total drill wall-clock <30s per Decision K.

## Dev Notes

### What changes post-cutover (live behavior)

Pre-cutover: `curl https://3d.ezop.ddns.net/` from PUBLIC IP → 403 Forbidden (deny all).
Post-cutover: same call → 200 (proxies to .190:8090 → portal HTML / login redirect).

The smoke runs from LAN — pre/post identical from LAN. The external-IP behavior change is the real effect; AC5 documents how to verify.

### What stays the same post-cutover

- App-level auth gates: still required for `/api/*` writes; still required for `/admin/*`.
- Share tokens: route `/share/<token>` works post-cutover for external IPs (allowing the operator's friends-and-family to access share links).
- Agent-runbook bypass: route `/agent-runbook` works post-cutover (the agent already has cookie auth; the change is that it can authenticate from non-LAN IPs if needed — likely irrelevant since agent runs on .190 LAN, but the route is structurally open).

### Rollback drill rationale

Per Decision K verbatim: "verified rollback drill (≤30s end-to-end) before cutover considered closed". The drill PROVES both directions work mechanically — not just that we can revert, but that we can revert-the-revert to re-apply. Operator confidence in the cutover is higher when both paths are exercise-verified.

### Why revert order matters

Revert ordering ALWAYS: revert latest cutover sha first → smoke → revert THAT revert (which re-applies the cutover) → smoke. Reversing the order would leave the working tree in an unexpected state.

### Cross-repo coordination

This story touches BOTH repos:
- `~/repos/configs/`: 3 pushes (cutover + revert + revert-the-revert) + 2 reloads on .180.
- `~/repos/3d-portal/`: 1 commit (sprint-status + artifact reference).

The atomic-cutover sequence interleaves both. Operator-confirmable checkpoints are T0/T1/T2 + drill-T1/drill-T2 captured in the artifact.

### Convention cross-references

- Artifact format mirrors `2fa-recovery-drill-2026-05-20.md` (Story 7.6 — NFR5-OBS-2 first slot precedent).
- Cross-repo coordination per `feedback_auto_deploy_dev.md` (deploy invariant — Story 10.4 fires `deploy.sh`).
- Memory `feedback_codex_review_invocation.md` for any post-cutover codex review of script changes (Story 10.3 likely runs codex on Story 10.1+10.2 fix-ups if any).
