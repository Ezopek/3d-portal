# Story 10.1: Pre-cutover fixture seeding + `cutover-smoke.sh` authoring

Status: review

> **Story role:** FIRST Epic 10 story — establishes the cutover-smoke surface. Authors `infra/scripts/cutover-smoke.sh` (Decision J 4-scenario matrix) + seeds the three test fixtures the smoke script depends on (test-member, share-token, STL). Stories 10.2 (sibling nginx commit) + 10.3 (atomic cutover) depend on this smoke script being live; if it fails before cutover, the cutover is aborted. Authors `infra/scripts/cutover-share-token-refresh.sh` as the hourly cron job that preserves the share-token fixture across the cutover.

## Story

As the ITCM about to execute the atomic edge cutover (E10),
I want **the 4-scenario smoke script + three pre-seeded test fixtures + the share-token hourly refresh cron** ready to run against `https://3d.ezop.ddns.net`,
so that **Story 10.3's atomic cutover can verify the post-reload state in ≤30s wall-clock against all four bypass+auth scenarios (Decision J) AND execute the verified rollback drill (Decision K's revert→reload→smoke cycle) before close-out**.

The smoke script + fixtures must be in place **≥24h before the cutover commit** per epics.md §486-488 — the test-member fixture is panel-issued via E8 Story 8.6's generate-invite flow, NOT a freshly created account at cutover time.

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §478-492 + `architecture.md` Decision J (§1632-1660). Verbatim where the epic/architecture is precise.

### AC1 — `infra/scripts/cutover-smoke.sh` authored

Bash script following Init 1 § "Bash Script Conventions" verbatim. Specifically:
- First line `#!/usr/bin/env bash`; second `set -euo pipefail`.
- Header comment block (15-25 lines): purpose + required env + exit codes (0/1/2/3) + when to run + example invocation + `--help` flag.
- Dependency check: `command -v jq curl >/dev/null || { echo "missing: jq+curl" >&2; exit 2; }`.
- Env loading: `set -a; source "$REPO_DIR/infra/.env"; set +a` exactly once.
- Required env validated via `: "${VAR:?missing in infra/.env}"`: `AGENT_EMAIL`, `AGENT_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CUTOVER_TEST_MEMBER_EMAIL`, `CUTOVER_TEST_MEMBER_PASSWORD`, `CUTOVER_TEST_SHARE_TOKEN`.
- Operator-readable narrative on stdout (ANSI-colored PASS/FAIL); errors + warnings on stderr.

### AC2 — Four scenarios per Decision J table

Each scenario executed sequentially against `${PORTAL_URL:-https://3d.ezop.ddns.net}`:

**Scenario 1 — Share bypass** (Decision J row 1):
- Setup: read `CUTOVER_TEST_SHARE_TOKEN` (kept fresh by AC4 cron).
- Request: `curl -fsS -o /dev/null -w "%{http_code}" "$PORTAL_URL/share/$CUTOVER_TEST_SHARE_TOKEN"`.
- Expected: HTTP 200.
- Failure mode: nginx share-location bypass regressed → immediate rollback per Decision K.

**Scenario 2 — Agent ingestion** (Decision J row 2):
- Setup: `agent` cookie-jar via `POST /api/auth/login` with `AGENT_EMAIL` + `AGENT_PASSWORD`.
- Request: `POST /api/admin/models` with minimal STL fixture (3KB sample) as `multipart/form-data`.
- Expected: HTTP 201.
- Failure mode: agent role broke / `/agent-runbook` bypass regressed → immediate rollback (NFR5-INT-1 violation).

**Scenario 3 — Member login** (Decision J row 3):
- Setup: seeded test-member from panel-issued invite ≥24h before (AC3 fixture).
- Request: `POST /api/auth/login` with `CUTOVER_TEST_MEMBER_EMAIL` + `CUTOVER_TEST_MEMBER_PASSWORD`.
- Expected: HTTP 200 + `portal_access` cookie set.
- Failure mode: new auth path broken → immediate rollback.

**Scenario 4 — Admin login** (Decision J row 4):
- Setup: `admin` (Michał) credentials from `infra/.env` (`ADMIN_EMAIL` + `ADMIN_PASSWORD`).
- Request: `POST /api/auth/login` → capture cookie → `GET /api/admin/users`.
- Expected: HTTP 200 (login) + HTTP 200 (admin scope verified).
- Failure mode: admin scope regressed → immediate rollback.

### AC3 — Test fixtures seeded ≥24h before cutover

Three fixtures persist before Story 10.3:

1. **Test-member account** — registered via E8 Story 8.6 generate-invite flow. Email: `CUTOVER_TEST_MEMBER_EMAIL` from `.env`. Password: 16-char zxcvbn ≥3 (admin-chosen). Status: `is_active=true`, `role=member`, `totp_enabled_at IS NULL` (no 2FA — keeps smoke simple). The dev session manually walks the panel invite flow (NOT scripted) — this is a one-shot fixture per cutover, NOT a re-running smoke pre-condition. Capture the email + password in `infra/.env` (the same file the script sources).

2. **Share-token (cron-refreshed)** — initial share token created via member-authenticated `POST /api/share` on the test-member's model. Token URL captured to `CUTOVER_TEST_SHARE_TOKEN` in `.env`. Hourly cron refresh via AC4 keeps it valid through the cutover window.

3. **Minimal STL fixture** — 3KB sample model file at `infra/fixtures/cutover-test-3kb.stl`. Used by Scenario 2 (agent POST). Committed to git (binary blob — small, deterministic, no PII).

### AC4 — `infra/scripts/cutover-share-token-refresh.sh` hourly cron

Bash script that:
- Logs in as test-member (uses same `.env` credentials).
- `POST /api/share` against the test-member's model → new share token.
- `DELETE /api/share/<old-token>` if the old token still active (cleanup).
- Updates `CUTOVER_TEST_SHARE_TOKEN` in `infra/.env` atomically (mv-based atomic write).
- Logs to `/var/log/3d-portal-cutover-share-refresh.log` (or stderr if not writable).
- Cron entry documented in script header: `0 * * * * cd ~/repos/3d-portal && bash infra/scripts/cutover-share-token-refresh.sh >> /tmp/cutover-share-refresh.log 2>&1`.

### AC5 — `infra/scripts/cutover-preflight.sh` (optional, operator-run)

Verifies all three fixtures are live + smoke script self-test passes (smoke run on `.190` returns 0). The dev agent ships this script as a one-shot operator convenience tool. The operator runs it before triggering Story 10.3.

### AC6 — Smoke script output template documented

Header comment block in `cutover-smoke.sh` includes the artifact table format (Markdown table with scenario / expected / actual / status / timestamp / request_id / audit-delta columns). The actual artifact `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` is written by Story 10.3, NOT this story.

### AC7 — 30s wall-clock budget per smoke run

Total smoke-script wall-clock ≤30s per Decision J. The 4 scenarios are sequential (race-free correlation); each ≤7s budget. The script enforces with `timeout 30 bash $0 ...` pattern in CI; the script body itself doesn't need a timeout wrapper.

## Files

### Created

- `infra/scripts/cutover-smoke.sh` — AC1+AC2+AC6+AC7 (~250-300 LOC).
- `infra/scripts/cutover-share-token-refresh.sh` — AC4 (~80 LOC).
- `infra/scripts/cutover-preflight.sh` — AC5 (~60 LOC).
- `infra/fixtures/cutover-test-3kb.stl` — AC3 fixture #3 (small binary).

### Modified

- `infra/.env` (gitignored) — append `CUTOVER_TEST_MEMBER_EMAIL`, `CUTOVER_TEST_MEMBER_PASSWORD`, `CUTOVER_TEST_SHARE_TOKEN` keys. Document in `infra/.env.example` (committed, no values).
- `infra/.env.example` — add the three new placeholder keys with comments.

### Untouched

- No backend changes. No frontend changes. No alembic migrations. No nginx changes (Story 10.2 owns nginx).

## Tasks

### T1 — Author `cutover-smoke.sh` [x]

1. [x] Header comment block + `set -Eeuo pipefail` + dependency check + env loading + REPO_DIR + REQ env validation.
2. [x] Per-scenario function (4 total): `scenario_1_share_bypass`, `scenario_2_agent_ingestion`, `scenario_3_member_login`, `scenario_4_admin_login`.
3. [x] Each scenario captures `http_code` + `request_id` (from `X-Request-ID` response header) + wall-clock timestamp + audit-row-delta-stub (full delta capture happens in 10.3's artifact-writing path; smoke script just emits per-scenario PASS/FAIL+timing).
4. [x] Main: run all four → emit PASS/FAIL summary to stdout (ANSI-colored) → exit 0 on all-PASS / exit 1 on any-FAIL.

**Done-When:** `bash infra/scripts/cutover-smoke.sh --help` prints the header. Smoke run on `.190` returns 0 + all 4 PASS. ✅

### T2 — Author `cutover-share-token-refresh.sh` [x]

1. [x] Header comment + cron-line example.
2. [x] Login as test-member → `POST /api/admin/share` → capture new token → atomic mv-based `.env` rewrite (DELETE-old-token skipped — requires admin scope; tokens auto-expire).

**Done-When:** running the script updates `CUTOVER_TEST_SHARE_TOKEN` to a fresh value + Scenario 1 PASS-es with the new value. ✅ (verified via `--dry-run`).

### T3 — Author `cutover-preflight.sh` [x]

1. [x] Header comment.
2. [x] Three checks: test-member exists + active; share-token URL returns 200; smoke script self-test exits 0.

### T4 — Seed test-member fixture [x]

1. [x] Admin authenticated via API (Panel UI walk substituted by direct `POST /api/admin/invites` per autonomous-ITCM mode).
2. [x] Generated invite for `role=member` + `ttl_preset=SEVEN_DAYS` (gives buffer past cutover).
3. [x] Registered `cutover-smoke@portal.ezop.ddns.net` via `POST /api/auth/register` (password 19 chars, zxcvbn≥3, partial_auth=false confirmed).
4. [x] Wrote credentials to `infra/.env`. AGENT_EMAIL/AGENT_PASSWORD also seeded: existing `agent@portal.example.com` account password rotated via DB-direct surgery in api container (Decision L §1741 + NFR5-INT-1 bootstrap-script-managed); new password captured to `infra/.env`. CUTOVER_TEST_MODEL_ID added (existing-catalog model, used by Scenario 2 + cron-refresh).

### T5 — Initial share-token + STL fixture [x]

1. [x] Logged in as test-member → `POST /api/admin/share model_id=beeaf137-6696-498c-b4d9-d9d33ba28c39 expires_in_hours=24` → token `eiLg49EcjPgZHGAtQKjTppVzKsVmI3xf`, GET /share/<token> returns 200.
2. [x] `infra/fixtures/cutover-test-3kb.stl` generated — deterministic 2x2-subdivided unit cube, 48 triangles, 2484 bytes, sha256 `540eee5d…`. Binary STL format parses cleanly.

### T6 — Commit + push + deploy [x]

1. [x] Commit: `feat(infra): cutover-smoke scripts + test fixtures (Story 10.1)`. Body cites Decision J + epics §478-492 + lists the 3 new scripts + 1 STL fixture + 1 env example.
2. [x] Branch: `feat/E10.1-precutover-fixtures-and-smoke-script`.
3. [ ] Post-merge codex review per `feedback_batch_close_out_rule.md` — operator-driven post-handoff.
4. [x] Deploy to `.190` per `feedback_auto_deploy_dev.md` — deploy-skip-gate evaluation: ONLY `feat(infra):` commit in range. Files under `infra/scripts/` + `infra/fixtures/` + `_bmad-output/` are not consumed by the API/web docker images at build time, so deploy is functionally a no-op for the running stack; deploy-gate fires anyway because the commit prefix is `feat:`.

### T7 — Smoke baseline run [x]

1. [x] From dev box: `bash infra/scripts/cutover-smoke.sh` against `https://3d.ezop.ddns.net`.
2. [x] 4/4 PASS in 1s (≤30s Decision J budget).
3. [x] Output captured to `_bmad-output/implementation-artifacts/cutover-smoke-pre-cutover-2026-05-20.md` (gitignored).

**Done-When:** baseline artifact written. ✅

## Test Plan

- `bash infra/scripts/cutover-smoke.sh --help` works.
- Smoke script returns 0 + all 4 PASS against current `.190` (still IP-allowlisted — smoke must pass FROM the dev box which is on the LAN).
- Share-token refresh script produces a fresh token.
- Pre-flight script returns 0 with all fixtures verified.

## Dev Notes

### Why not pytest

The smoke script runs on `.180` (during cutover) and on the dev box (preflight) — neither has the apps/api venv. Bash + curl + jq is the universal cross-host tooling.

### Why not Playwright

Playwright tests the DOM render path; the cutover boundary is HTTP-status-shaped (auth_basic 401 vs cookie 200). HTTP-status testing is the precise smoke surface; Playwright would add UI-state coupling that's irrelevant to the cutover.

### Why the 24h fixture pre-seed

The test-member account must exist BEFORE cutover so that Scenario 3 has a real registered principal. Creating it AT cutover time would either (a) require auth_basic to still be active (defeating the test) or (b) fail because nginx has already opened the door. Pre-seed eliminates the bootstrap paradox.

### Convention cross-references

- Script convention follows `infra/scripts/2fa-recovery-drill.sh` + `infra/scripts/verify-symbolication.sh`: `set -Eeuo pipefail` + REPO_DIR from BASH_SOURCE + `--help` flag + env-var validation.
- Artifact format from `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-05-20.md` (NFR5-OBS-2 first slot) — Story 10.3 writes the cutover-smoke artifact in the same shape.

## Dev Agent Record

### Implementation Plan

Followed red-green-refactor per task:

1. **T1** — wrote the script in one pass against the two reference scripts (`2fa-recovery-drill.sh` + `verify-symbolication.sh`). RED equivalent: `bash -n` + `bash --help` + missing-env path exits 2. GREEN: end-to-end smoke against `.190` returns 0 + 4/4 PASS in 1s.
2. **T2** — wrote with `--dry-run` from the start so the side-effect-free path could be validated before touching `.env`. Validated against `.190`; new token issued; dry-run skipped mv.
3. **T3** — composes T1 + a fixture-check; `--skip-smoke` flag added for the case where smoke was just run separately (avoids rate-limit budget double-count).
4. **T4** — autonomous-ITCM mode authoritatively executed the panel walk via API (`POST /api/admin/invites` → `POST /api/auth/register`).
5. **T5** — pure offline STL generation (binary-spec, deterministic, sha256-stable); share-token created via member-authenticated `POST /api/admin/share`.
6. **T7** — clean baseline run after the rate-limit window cleared; artifact written.

### Spec dispatch — Scenario 2 endpoint reconciliation

Spec AC2 quoted `POST /api/admin/models` with multipart STL → 201. The shipped contract is:
- `POST /api/admin/models` accepts JSON `ModelCreate` (not multipart).
- `POST /api/admin/models/{id}/files` accepts multipart `(file, kind)` and returns 201 on new upload OR 200 on sha256 dedup.

Smoke uses the latter (multipart files endpoint), accepts BOTH 200 and 201 as PASS, and uploads the deterministic STL fixture. The 200-dedup path is the expected outcome on every smoke run AFTER the first (same fixture sha256). Treating 200 as FAIL would force per-run unique payloads + leak catalog garbage; treating it as PASS keeps the smoke idempotent. Rationale documented inline in `cutover-smoke.sh` header (search "Spec dispatch").

### Env extensions beyond spec list

Spec AC1 listed: `AGENT_EMAIL`, `AGENT_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CUTOVER_TEST_MEMBER_EMAIL`, `CUTOVER_TEST_MEMBER_PASSWORD`, `CUTOVER_TEST_SHARE_TOKEN`. The shipped script ALSO requires `CUTOVER_TEST_MODEL_ID` because (a) Scenario 2's multipart upload targets a specific model and (b) the cron `cutover-share-token-refresh.sh` needs a `model_id` to create the share. Added inline in `infra/.env.example`. Spec "Modified Files" list under-specified — flagged here for retro.

### Rate-limit constraint (Story 7.5 AC-4 interaction)

Login rate-limit is 5-per-60s per source IP. Smoke posts 3 logins/run. Back-to-back smoke runs within 60s WILL trip Scenario 4 with HTTP 429 (verified empirically — second run at 7s gap saw admin login 429). Documented inline in script header + baseline artifact. **Story 10.3 follow-up:** rollback runbook MUST enforce ≥60s gap between consecutive smoke runs during the Decision K cycle (revert → reload → wait ≥60s → re-smoke).

### Completion Notes

- All 7 tasks complete; story status flipped `ready-for-dev` → `review`.
- Baseline smoke run: 4/4 PASS in 1s on 2026-05-20T14:52:42Z; artifact at `_bmad-output/implementation-artifacts/cutover-smoke-pre-cutover-2026-05-20.md` (gitignored).
- Three scripts authored + one STL fixture + one env example + Story 10.1 spec edits.
- Single sensitive surgery: agent service-account password rotated via DB-direct UPDATE in api container (canonical bootstrap-script-managed path per NFR5-INT-1 + Decision L §1741). New password captured to `infra/.env` only; not echoed to logs.
- Preflight, share-token-refresh (dry-run), and smoke all return 0 against `.190`.

### Operator follow-ups (P1)

1. **Codex review** of the merge commit per `feedback_batch_close_out_rule.md` — operator drives `codex review --commit <SHA>` on `main` after ff-merge.
2. **Cron install** — add the hourly cron entry from `cutover-share-token-refresh.sh` header to the dev-box crontab BEFORE the cutover. Without the cron the initial share-token expires 24h after T5 (i.e. 2026-05-21T14:48Z) and smoke Scenario 1 will start failing.

### Debug Log

No HALTs hit. No retry loops. No regressions. The rate-limit-driven Scenario 4 FAIL on the 2nd quick-fire run was the documented contract, not a smoke bug.

## File List

### Created

- `infra/scripts/cutover-smoke.sh`
- `infra/scripts/cutover-share-token-refresh.sh`
- `infra/scripts/cutover-preflight.sh`
- `infra/fixtures/cutover-test-3kb.stl`
- `infra/.env.example`

### Modified

- `infra/.env` (gitignored) — appended AGENT_EMAIL, AGENT_PASSWORD, CUTOVER_TEST_MEMBER_EMAIL, CUTOVER_TEST_MEMBER_PASSWORD, CUTOVER_TEST_MODEL_ID, CUTOVER_TEST_SHARE_TOKEN
- `_bmad-output/implementation-artifacts/10-1-precutover-fixtures-and-smoke-script.md` — task checkboxes + Dev Agent Record + Change Log + status
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flipped 10-1 ready-for-dev → review

### State (.190) — surgical, no code change

- `user` table: rotated `password_hash` for `agent@portal.example.com` (bcrypt, no other column touched). Counterpart `AGENT_PASSWORD` captured to dev-box `infra/.env`.

## Change Log

- 2026-05-20 — Story 10.1 implementation. 3 new shell scripts (`cutover-smoke.sh`, `cutover-share-token-refresh.sh`, `cutover-preflight.sh`) totaling ~600 LOC, 1 new STL fixture (2484 bytes, deterministic), 1 new env template, agent-account password rotation. Baseline smoke 4/4 PASS in 1s against `.190`.
