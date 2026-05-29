# Story 10.4: Closing `docs/operations.md` cutover-date commit in `3d-portal`

Status: ready-for-dev

> **Story role:** FOURTH and FINAL Epic 10 story + FINAL Initiative 5 deliverable. Records the cutover date in `docs/operations.md` + bypasses the `deploy.sh` skip-gate (non-skip-prefix commit) so the deploy step fires + `infra/.last-deploy-sha` advances to the cutover SHA. Initiative 5 is considered COMPLETE at this commit's merge. Depends on Story 10.3 (cutover landed + stable + verified).

## Story

As the ITCM closing Initiative 5,
I want **a commit to `3d-portal` updating `docs/operations.md` with the post-cutover portal-self-auth posture documentation + cross-references to all three NFR5-OBS-2 artifacts (recovery-drill + audit + cutover-smoke) + bypass of the deploy.sh skip-gate (so the deploy fires + advances `infra/.last-deploy-sha`)**,
so that **the cutover is recorded within `3d-portal` deploy history (NFR5-CROSS-REPO-1), future deploy-gate behavior anchors at the post-cutover SHA, and Initiative 5 is structurally closed for the retrospective handoff**.

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §524-536.

### AC1 — `docs/operations.md` post-cutover posture section

Append a new section to `docs/operations.md` (after the existing content). Title: `## Post-cutover portal-self-auth posture (2026-MM-DD)` (use actual cutover date). Body covers:

- nginx is now a thin TLS terminator + share-bypass + agent-runbook bypass + proxy layer (no longer an auth gate via IP allowlist).
- Portal authenticates itself via cookie+JWT — `portal_access` 10min + `portal_refresh` 30d family rotation; CSRF via `X-Portal-Client: web` header.
- `member` role is invite-only — admin generates single-use invites via `/admin/invites` panel; recipient lands on `/register?token=` flow (Story 6.4 + Story 8.6 surfaces).
- 2FA enforcement is per-role config-flag-driven (`enforce_2fa_for_roles: list[Role]`) with `Role.agent` permanently excluded via fail-fast startup `RuntimeError` (Story 7.4 binding).
- Rate-limit middleware (Redis sliding-window) protects `/api/auth/login` (5/60s), `/api/auth/refresh` (10/60s), `/api/auth/register?token=` (3/60s), and per-member `/api/share/` creation (20/day hard + 50% soft-alert per Decision G + H).
- Cross-references (verbatim paths):
  - `_bmad-output/implementation-artifacts/security-audit-2026-05-20.md` — Story 9.4 audit signoff (NFR5-SEC-1 gate PASS).
  - `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-05-20.md` — Story 7.6 NFR5-OBS-2 first artifact slot.
  - `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` — Story 10.3 NFR5-OBS-2 second artifact slot.

### AC2 — Commit message conforms to non-skip-prefix per `bf919c2`/`0745209` skip-gate

Commit message subject: `feat(infra): record edge cutover date 2026-MM-DD`. Conventional Commits `feat(infra)` is a NON-skip prefix per the deploy-skip-gate convention; the prefix selection IS the gate-bypass mechanism per memory `feedback_deploy_skip_gate_design.md`. Body references:

- Sibling cutover commit SHA (from Story 10.3 final state).
- All three NFR5-OBS-2 artifact paths (per AC1).
- Initiative 5 close-out anchor (this commit closes Init 5).

### AC3 — Auto-deploy fires per `feedback_auto_deploy_dev.md`

After the commit lands on main: `infra/scripts/deploy.sh` is invoked per the auto-deploy convention. The deploy is a null-op for application code (no code changed — only docs/), but it:
- Advances `infra/.last-deploy-sha` to this commit's SHA → future deploy-gate range-check anchors here.
- Re-runs verify-symbolication (sanity check).
- Records the cutover SHA in deploy history.

**Critical:** the deploy MUST actually fire (deploy-skip-gate must NOT skip this commit). Verify by inspecting `infra/.last-deploy-sha` post-deploy — it MUST match this commit's SHA.

### AC4 — Initiative 5 considered COMPLETE at this commit's merge

The merge of the AC2 commit IS the structural Initiative 5 close-out marker. Sprint-status `epic-10: in-progress → done` AND `10-4-closing-operations-md-cutover-date: ready-for-dev → done` flip in the same commit (or a follow-up sprint-status edit if separated). NO further code/infra changes for Init 5 after this commit.

### AC5 — Init 5 retrospective scheduled (NOT executed here)

Per epics §536: "Retrospective (`bmad-retrospective`) scheduled as the next session per CC §5.2 handoff plan." Story 10.4 ships the close-out commit; the retrospective is the SEPARATE follow-up that this story does NOT execute. Sprint-status notes the retro as `epic-10-retrospective: optional` OR `pending` per the operator's choice (retros for Epic 9 + Epic 10 + Init 5 final are typically bundled in the autonomous ITCM mode close-out).

## Files

### Created

None.

### Modified

- `docs/operations.md` — append AC1 section (~30-50 lines of new content).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flip `epic-10` + `10-4-closing-operations-md-cutover-date` to `done`.

### Untouched

- No apps/ changes. No alembic. No infra/scripts changes. No frontend.

## Tasks

### T1 — Pre-conditions

1. Verify Story 10.3 cutover landed + artifact exists: `ls -la _bmad-output/implementation-artifacts/cutover-smoke-2026-*.md`.
2. Verify sibling repo HEAD: `cd ~/repos/configs && git log origin/main..HEAD` empty (Story 10.3 left pushed state).
3. Sprint-status check: `10-3-atomic-cutover-smoke-rollback-drill: done` AND `epic-10: in-progress`.

### T2 — Edit `docs/operations.md`

Append AC1 section. Preserve existing content + heading structure.

### T3 — Sprint-status update

Flip:
- `epic-10: in-progress` → `done`.
- `10-4-closing-operations-md-cutover-date: ready-for-dev` → `done` with the cutover-date + sibling SHA + cutover-smoke artifact path.

### T4 — Commit (non-skip prefix)

1. `git add docs/operations.md _bmad-output/implementation-artifacts/sprint-status.yaml`.
2. `git commit -m "$(cat <<'EOF'`-style heredoc with AC2 subject + body.
3. `git push --no-verify origin main`.

### T5 — Auto-deploy fires

1. `infra/scripts/deploy.sh` invoked.
2. Verify deploy actually ran (skip-gate did NOT skip): `cat infra/.last-deploy-sha` matches HEAD.
3. Verify-symbolication PASS.
4. Initiative 5 structurally COMPLETE at this point.

### T6 — Handoff signal

Update orchestration state doc (`_bmad-output/story-automator/orchestration-init-5-*.md`):
- `status: COMPLETED`.
- `lastUpdated: 2026-MM-DDTHH:MM:SSZ`.
- Log entry: "Initiative 5 closed at <sha> per Story 10.4 commit on YYYY-MM-DD."

## Test Plan

- T2 edit: `docs/operations.md` has the new section + cross-references resolve to existing artifact paths.
- T4: commit on main + pushed + deploy fired.
- T5: `infra/.last-deploy-sha` advanced to the close-out commit SHA.

## Dev Notes

### Why "feat(infra):" not "chore(infra):"

The deploy-skip-gate (per `bf919c2`/`0745209` from memory) skips commits whose subject starts with `chore:`/`docs:`/etc. `feat(infra):` is in the NON-skip list. The prefix choice IS the gate-bypass mechanism — this commit MUST be non-skip so the deploy fires + the marker advances.

### What "Initiative 5 complete" structurally means

After this commit:
- All 27 stories DONE (sprint-status structural marker).
- All 5 epics DONE (E6-E10).
- All FRs (24/24) + NFRs (12/12) realized per the brief.
- The HARD GATE (NFR5-SEC-1) PASSED + the cutover (FR5-CUTOVER-1..3) EXECUTED + the rollback drill (FR5-CUTOVER-3) VERIFIED.
- Initiative-5-retrospective is the only remaining deliverable (typically batched into operator handoff).

### Why no separate Init 5 retro story

Epic retrospectives are SKILLs (`bmad-retrospective`), not stories. The Init 5 retrospective is invoked as a SEPARATE post-close-out session — not as a Story 10.5. Per autonomous mode + memory, the parent (ITCM) typically runs the retro inline after Story 10.4 lands; the retro artifact lives at `_bmad-output/implementation-artifacts/initiative-5-retro-YYYY-MM-DD.md`.

### Convention cross-references

- Non-skip-prefix per `feedback_deploy_skip_gate_design.md` (memory) — `feat(infra):` triggers `deploy.sh`.
- Auto-deploy per `feedback_auto_deploy_dev.md` — every code/infra merge to main runs `deploy.sh`.
- Closing-commit pattern per CC §5.2 handoff plan (epics.md §536).
- NFR5-OBS-2 second slot per `_bmad-output/implementation-artifacts/cutover-smoke-2026-05-20.md` (Story 10.3 artifact, gitignored).
