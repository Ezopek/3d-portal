# Story 10.2: Sibling nginx commit authoring + pre-flight `nginx -t` gate

Status: ready-for-dev

> **Story role:** SECOND Epic 10 story — authors the cross-repo nginx commit in `~/repos/configs/` that drops the IP allowlist gating `https://3d.ezop.ddns.net`. **Produces commit locally + verifies syntax; does NOT push (Story 10.3 handles atomic push+reload+smoke+rollback drill).** Depends on Story 10.1 (smoke script ready to verify reload).

## Story

As the ITCM executing the atomic edge cutover,
I want **the sibling nginx config edit landed as a single local commit in `~/repos/configs/` with `nginx -t` syntax verification PASSING before Story 10.3 pushes**,
so that **the cross-repo atomic-cutover sequence in Story 10.3 starts from a known-syntactically-valid state — eliminating the risk of a `nginx -s reload` failing on `.180` mid-cutover**.

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §494-505. Architecture Decision K (concrete diff). The architecture.md diff describes `auth_basic` + per-location bypasses that DO NOT exist in the current `~/repos/configs/nginx/3d.ezop.ddns.net.conf` — see Dev Notes "Architecture diff drift" for the reality-vs-aspiration reconciliation.

### AC1 — Concrete edit to sibling config file

The file `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (NOT in `3d-portal` working tree — sibling repo) has the following lines DROPPED from the `server { listen 443 ssl; ... }` block:

```diff
   ssl_session_cache shared:SSL:10m;
 
-  # LAN + VPN only — portal hosts the operator's private 3D model collection.
-  allow 192.168.2.0/24;
-  allow 10.8.0.0/24;
-  deny all;
-
   # Catalog data (STL files, thumbnails, prints) can be 50+ MB for STL and
```

The four lines DROPPED are: comment line + `allow 192.168.2.0/24;` + `allow 10.8.0.0/24;` + `deny all;` plus the trailing blank line. The `client_max_body_size 100m;` line and everything below stays exactly as-is. **No auth_basic directives exist in the current file** (the architecture.md Decision K diff describes a baseline that drifted from reality — this story handles the actual current state).

### AC2 — Sibling repo commit (local only — NO push)

In `~/repos/configs/`:
- Commit message subject: `feat(nginx): drop IP allowlist for 3d-portal cutover`. (Architecture.md spec said `drop auth_basic + IP allowlist`; tightened to reality.)
- Conventional Commits `feat(nginx)` matches sibling repo style.
- Body references:
  - The corresponding `3d-portal` cutover artifact path (`_bmad-output/implementation-artifacts/security-audit-2026-05-20.md` — the E9 audit that unblocked this).
  - Decision K cross-reference (`_bmad-output/planning-artifacts/architecture.md` §1662).
  - Story 9.2 reproducibility note (the audit was rerunnable via `bash audit-raw/2026-05-20/reproducers.sh all`).
  - Rollback note: revert via `git revert <sha>` + nginx reload re-establishes IP allowlist; verified via Story 10.3 drill.
- **Critical:** the commit is NOT pushed to origin. Story 10.3 owns push + reload + smoke atomically.

### AC3 — Pre-flight `nginx -t` PASS on sibling commit content

Before the commit lands (or immediately after with `git reset --soft` if needed), the edited config is syntax-checked:
- Method A (preferred — if nginx installed locally): `nginx -t -c <(cat ~/repos/configs/nginx/3d.ezop.ddns.net.conf)` — runs against the edited content.
- Method B (fallback — copy to `.180`): `scp ~/repos/configs/nginx/3d.ezop.ddns.net.conf ezop@192.168.2.180:/tmp/3d-portal-cutover-test.conf && ssh ezop@192.168.2.180 'sudo nginx -t -c /etc/nginx/nginx.conf'` (copy to the include directory first, OR perform an out-of-tree syntax test).

The syntax check MUST PASS. If it fails: revert the edit, escalate to operator (NFR5-PERF-2 cutover-≤5min budget is conditional on `nginx -t` passing on first attempt).

### AC4 — No 3d-portal-side changes

This story does NOT modify any file in the `3d-portal` working tree. Sprint-status update is the ONLY 3d-portal-tracked artifact this story produces (per Story 10.2 acceptance gate).

### AC5 — Story commit in 3d-portal documents the sibling commit SHA

In 3d-portal, a one-line commit `chore(infra): note sibling nginx commit <sha> for E10 cutover (Story 10.2)` updates sprint-status.yaml ONLY. The commit body references the sibling SHA + the sibling repo path. This is the ONLY 3d-portal commit produced by Story 10.2.

## Files

### Created

None.

### Modified

- `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (SIBLING REPO — not in `3d-portal` working tree). 4 lines dropped (server-block IP allowlist).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (3d-portal — note the sibling SHA in the 10.2 status line).

### Untouched

- Everything else in 3d-portal. No nginx changes to apps/api or workers/render. No alembic. No frontend.

## Tasks

### T1 — Verify pre-conditions

1. `cd ~/repos/configs && git status` → working tree clean.
2. `git log --oneline -5` → confirm sibling repo HEAD is current (no uncommitted ad-hoc edits from operator).
3. `cd ~/repos/3d-portal && cat _bmad-output/implementation-artifacts/security-audit-2026-05-20.md | grep -F "E10 cleared to proceed"` → confirm gate PASS line present.
4. `bash infra/scripts/cutover-smoke.sh` → 4/4 PASS against current (pre-cutover) `.190` state.

**Done-When:** all four pre-conditions hold.

### T2 — Edit sibling nginx config

1. `cd ~/repos/configs/`.
2. Open `nginx/3d.ezop.ddns.net.conf`; delete the 4 lines per AC1.
3. Diff-review: `git diff nginx/3d.ezop.ddns.net.conf` shows ONLY the 4-line deletion + no whitespace artifacts.

### T3 — Syntax-check via `nginx -t`

Try Method A first; fall back to Method B (SSH .180) if local nginx not installed. Either way, MUST observe `nginx: configuration file ... test is successful` output.

**Done-When:** syntax check passes; document method used.

### T4 — Sibling repo commit (NO push)

1. `cd ~/repos/configs/`.
2. `git add nginx/3d.ezop.ddns.net.conf`.
3. `git commit -m "$(cat <<'EOF'`-style heredoc with the AC2 message body.
4. `git log -1 --stat` → confirm exactly 1 file, 0 insertions, 4 deletions.

**Done-When:** commit lives locally on the current branch (typically `main`); `git log origin/main..HEAD` shows the new commit pending push.

### T5 — 3d-portal close-out commit

1. `cd ~/repos/3d-portal/`.
2. Edit `_bmad-output/implementation-artifacts/sprint-status.yaml` 10.2 line: flip `ready-for-dev` → `done` + add sibling SHA + nginx -t method used.
3. Commit: `chore(infra): note sibling nginx commit <sibling-sha> for E10 cutover (Story 10.2)`.
4. Push to 3d-portal origin/main.
5. Deploy-skip-gate range check WILL skip the deploy step (sprint-status.yaml is doc-only — pre-existing skip pattern).

**Done-When:** 3d-portal main has the close-out commit; sibling repo has the cutover commit locally (NOT pushed).

## Test Plan

- T3 nginx -t PASS is the only mechanical verification.
- T4 git log shows the commit + diff shape matches AC1 exactly.
- T5 3d-portal commit visible on origin/main.

## Dev Notes

### Architecture diff drift (reality vs aspiration)

The `architecture.md` Decision K diff (§1662) describes a baseline with:
- `auth_basic "3d-portal";`
- `auth_basic_user_file /etc/nginx/.htpasswd-portal;`
- `location /share/ { auth_basic off; allow all; ... }`
- `location /agent-runbook { auth_basic off; allow all; ... }`

NONE of these exist in the current `~/repos/configs/nginx/3d.ezop.ddns.net.conf`. The current file has ONLY:
- Server-level `allow 192.168.2.0/24;` + `allow 10.8.0.0/24;` + `deny all;` (no auth_basic).
- Single `location /` block (no per-location bypasses).

This is a planning-phase architectural drift. The cutover-as-shipped is simpler than the architecture.md spec. Acknowledge in the sibling commit message + flag for Init 5 retrospective doc-drift batch.

**Implication for smoke script (Story 10.1) and rollback drill (Story 10.3):**

- Scenario 1 (share bypass) and Scenario 2 (agent ingestion) currently work via app-level routing through the single `location /` block — there's no nginx-level bypass to preserve.
- The smoke runs from the LAN (dev box → .180), which passes the IP allowlist either way (pre or post-cutover from LAN looks identical).
- Smoke does NOT detect the cutover's primary effect (external-IP reachability). True post-cutover validation requires testing from a public IP — out of smoke scope.

The smoke validates app-level auth + routing post-reload, not network-level reachability change. This is intentional + documented in Story 10.1 spec.

### Why NO push in this story

Story 10.3 owns the atomic cross-repo sequence: push sibling + ssh .180 + git pull + nginx -t + nginx -s reload + smoke + (rollback drill). If 10.2 pushed independently, the cutover state would be live BEFORE the smoke verifies — a 30+ minute window where a regression could go unnoticed. Keeping push as an atomic 10.3 step minimizes the production-state-change window.

### Convention cross-references

- Cross-repo coordination per `~/repos/configs/docs/observability-logging-contract.md` precedent (sibling repo containing infra-specific docs).
- Conventional Commits `feat(nginx):` matches existing sibling repo style.
- Pre-flight gate per Decision K verbatim: `ssh .180 'sudo nginx -t'` MUST PASS BEFORE push.
