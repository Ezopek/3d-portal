#!/usr/bin/env bash
# 4-scenario cutover smoke against `https://3d.ezop.ddns.net` (Decision J).
#
# Verifies the post-reload state of the atomic edge cutover (Story 10.3) by
# exercising the four bypass + auth surfaces that the cutover crosses:
#
#   Scenario 1 — Share bypass            GET  /share/<CUTOVER_TEST_SHARE_TOKEN>
#   Scenario 2 — Agent ingestion         POST /api/admin/models/<id>/files
#   Scenario 3 — Member login            POST /api/auth/login (member)
#   Scenario 4 — Admin login             POST /api/auth/login (admin) + scope
#
# Each scenario captures HTTP code, X-Request-ID, wall-clock timestamp, and
# emits a PASS/FAIL line (ANSI-colored on stdout). On any FAIL the script
# exits 1 — Decision K then says: revert nginx → reload → re-smoke. The
# audit-row delta capture lives in Story 10.3's artifact writer; this script
# only emits per-scenario PASS/FAIL with timings + request ids.
#
# Wall-clock budget: ≤30s total per Decision J. Each scenario uses a 7s
# `curl --max-time` cap so a hung scenario cannot exhaust the budget.
# Operators wrap the whole run in `timeout 30 bash $0` in CI; the script
# body itself does NOT enforce the outer wrap.
#
# Login rate-limit caveat (Story 7.5 AC-4): the API enforces a 5-failures-
# per-60s sliding window keyed by client IP, scoped to /api/auth/login +
# /api/auth/2fa/verify + /api/auth/2fa/recovery-codes/regenerate +
# /api/auth/2fa/disable. Every smoke run posts 3 logins (agent + member +
# admin). Back-to-back runs from the SAME source IP within 60s will hit
# the 6th login and FAIL Scenario 4 with HTTP 429. The Decision K rollback
# drill therefore REQUIRES ≥60s gap between consecutive smoke runs from
# the same caller (typical cadence: pre-reload → reload (~5-15s) → wait
# ≥45s → post-reload smoke → if FAIL: revert → reload → wait ≥60s →
# post-revert smoke). A 429 on Scenario 4 during a hot cutover is NOT a
# rollback signal by itself — re-check against rate-limit budget before
# acting.
#
# Spec dispatch — Scenario 2 endpoint reconciliation:
#   Story 10.1 spec quotes "POST /api/admin/models with minimal STL fixture
#   as multipart/form-data → 201". The actual contract on .190 is:
#       POST /api/admin/models           — JSON ModelCreate         → 201
#       POST /api/admin/models/{id}/files — multipart (file+kind)   → 201
#                                                                   → 200 on
#                                                                     sha256 dedup
#   This script uses the multipart files endpoint against a pre-existing test
#   model (CUTOVER_TEST_MODEL_ID), accepts BOTH 200 and 201 as PASS, and
#   uploads the deterministic 3KB STL fixture at infra/fixtures/cutover-test-3kb.stl.
#   200 (dedup) is functionally identical to 201 — same agent-write code path,
#   same admin-router decorator. The dedup-200 path is the expected outcome on
#   every smoke run AFTER the first (same fixture sha256). Treating 200 as FAIL
#   would force per-run unique payloads + leak catalog garbage; treating it as
#   PASS keeps the smoke idempotent.
#
# Required env (sourced from infra/.env on the dev box / `.180` host):
#   AGENT_EMAIL                agent role account (write access via /agent-runbook bypass)
#   AGENT_PASSWORD             agent password
#   ADMIN_EMAIL                admin (Michał) account
#   ADMIN_PASSWORD             admin password
#   CUTOVER_TEST_MEMBER_EMAIL  test-member seeded via E8 generate-invite (Story 10.1 T4)
#   CUTOVER_TEST_MEMBER_PASSWORD  ≥12-char zxcvbn≥3
#   CUTOVER_TEST_SHARE_TOKEN   share token kept fresh by hourly cron (cutover-share-token-refresh.sh)
#   CUTOVER_TEST_MODEL_ID      pre-seeded model UUID owned by test-member (Story 10.1 T5);
#                              target of Scenario 2's multipart upload
#
# Optional env (overrideable):
#   PORTAL_URL          default https://3d.ezop.ddns.net
#   CUTOVER_STL_FIXTURE default infra/fixtures/cutover-test-3kb.stl
#   CUTOVER_HTTP_TIMEOUT default 7 (seconds per individual request)
#
# Flags:
#   --help  print this header docstring; exit 3
#
# Exit codes:
#   0  all 4 scenarios PASS; safe to proceed past cutover
#   1  ≥1 scenario FAIL; trigger rollback per Decision K
#   2  prerequisite failure (env var missing, fixture missing, portal unreachable);
#      no rollback decision encoded — operator investigates
#   3  --help invoked
#
# Example:
#   set -a; source infra/.env; set +a
#   bash infra/scripts/cutover-smoke.sh
#   # → 0; ✅ all 4 scenarios PASS in <30s
#
# Artifact output template (consumed by Story 10.3's artifact writer; this
# script does NOT write the artifact, only emits the per-scenario lines):
#
#   | # | Scenario              | Expected | Actual | Status | Timestamp (UTC)        | Request ID                              | Audit delta |
#   |---|-----------------------|----------|--------|--------|------------------------|-----------------------------------------|-------------|
#   | 1 | share bypass          | 200      | 200    | PASS   | 2026-05-20T20:13:14Z   | 0b1a2c3d-...                            | (10.3 fills) |
#   | 2 | agent ingestion       | 201|200  | 201    | PASS   | 2026-05-20T20:13:15Z   | 1c2b3d4e-...                            | (10.3 fills) |
#   | 3 | member login          | 200      | 200    | PASS   | 2026-05-20T20:13:16Z   | 2d3c4e5f-...                            | (10.3 fills) |
#   | 4 | admin login + scope   | 200,200  | 200,200| PASS   | 2026-05-20T20:13:17Z   | 3e4d5f6g-...,4f5e6g7h-...               | (10.3 fills) |
#
# Help:
#   bash infra/scripts/cutover-smoke.sh --help

set -Eeuo pipefail

# --- Help handling first (no env required) -----------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,/^set -Eeuo pipefail$/p' "$0" | sed -E 's/^# ?//;/^set -Eeuo pipefail$/d'
  exit 3
fi

if [[ $# -gt 0 ]]; then
  echo "cutover-smoke: unknown argument '$1' (try --help)" >&2
  exit 2
fi

# --- Dependency check --------------------------------------------------------
command -v jq >/dev/null || { echo "cutover-smoke: missing dependency: jq" >&2; exit 2; }
command -v curl >/dev/null || { echo "cutover-smoke: missing dependency: curl" >&2; exit 2; }

# --- Repo root + env loading -------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if [[ -f "$REPO_DIR/infra/.env" ]]; then
  set -a; source "$REPO_DIR/infra/.env"; set +a
fi

# --- Required env enforcement (exit 2 per docstring contract) ---------------
# Bash `:?` exits with status 1 — we want exit 2 ("prerequisite failure") for
# missing env, so we walk the list explicitly and accumulate misses for a
# single fail-fast message.
_missing_env=()
for v in AGENT_EMAIL AGENT_PASSWORD ADMIN_EMAIL ADMIN_PASSWORD \
         CUTOVER_TEST_MEMBER_EMAIL CUTOVER_TEST_MEMBER_PASSWORD \
         CUTOVER_TEST_SHARE_TOKEN CUTOVER_TEST_MODEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    _missing_env+=("$v")
  fi
done
if (( ${#_missing_env[@]} > 0 )); then
  echo "cutover-smoke: missing required env in infra/.env: ${_missing_env[*]}" >&2
  exit 2
fi

: "${PORTAL_URL:=https://3d.ezop.ddns.net}"
: "${CUTOVER_STL_FIXTURE:=$REPO_DIR/infra/fixtures/cutover-test-3kb.stl}"
: "${CUTOVER_HTTP_TIMEOUT:=7}"

if [[ ! -f "$CUTOVER_STL_FIXTURE" ]]; then
  echo "cutover-smoke: STL fixture missing: $CUTOVER_STL_FIXTURE" >&2
  exit 2
fi

# --- ANSI colors (auto-disable when stdout is not a tty) ---------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_RED=""; C_GREEN=""; C_YELLOW=""; C_BOLD=""; C_RESET=""
fi

# --- Helpers -----------------------------------------------------------------
new_request_id() { python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null \
  || cat /proc/sys/kernel/random/uuid; }
iso_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

umask 077
TMPDIR_RUN=$(mktemp -d /tmp/cutover-smoke.XXXXXX)
cleanup() {
  rm -rf "$TMPDIR_RUN" 2>/dev/null || true
}
trap cleanup EXIT

# Per-scenario row accumulator (markdown table fragments for stdout summary).
RESULTS_FILE="$TMPDIR_RUN/results.tsv"
: > "$RESULTS_FILE"

# Record a row: scenario_num \t name \t expected \t actual \t status \t ts \t request_id
record_result() {
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$@" >> "$RESULTS_FILE"
}

# Curl wrapper that emits "<http_code>\t<request_id>" to stdout. Body is
# discarded unless BODY_OUT is set in the caller. Auto-captures the inbound
# X-Request-ID echo from the response header. Honors CUTOVER_HTTP_TIMEOUT.
# Args: passed through to curl.
curl_smoke() {
  local rid headers_file
  rid=$(new_request_id)
  headers_file="$TMPDIR_RUN/headers.$$.$RANDOM"
  local body_out="${BODY_OUT:-/dev/null}"
  local http_code
  http_code=$(curl --max-time "$CUTOVER_HTTP_TIMEOUT" \
    -sS -o "$body_out" -w "%{http_code}" \
    -D "$headers_file" \
    -H "X-Request-ID: $rid" \
    -H "X-Portal-Client: web" \
    "$@" || echo "000")
  # The API echoes the request_id back via x-request-id header (case-insensitive
  # match). If absent, fall back to the one we generated.
  local echoed
  echoed=$(grep -i '^x-request-id:' "$headers_file" 2>/dev/null \
    | tail -n1 | awk '{print $2}' | tr -d '\r' || true)
  rm -f "$headers_file"
  printf '%s\t%s\n' "$http_code" "${echoed:-$rid}"
}

# --- Pre-flight: portal reachable -------------------------------------------
PRECHECK_RID=$(new_request_id)
if ! curl --max-time "$CUTOVER_HTTP_TIMEOUT" -fsS -o /dev/null \
    -H "X-Request-ID: $PRECHECK_RID" \
    "$PORTAL_URL/api/health"; then
  echo "${C_RED}cutover-smoke: portal /api/health unreachable (${PORTAL_URL})${C_RESET}" >&2
  exit 2
fi

echo "${C_BOLD}cutover-smoke: ${PORTAL_URL}${C_RESET}"
echo "started: $(iso_now); pid=$$; fixture=$CUTOVER_STL_FIXTURE"
echo ""

# --- Scenario 1 — Share bypass ----------------------------------------------
scenario_1_share_bypass() {
  local ts code rid out
  ts=$(iso_now)
  out=$(curl_smoke "$PORTAL_URL/share/$CUTOVER_TEST_SHARE_TOKEN")
  code=$(echo "$out" | cut -f1)
  rid=$(echo "$out" | cut -f2)
  if [[ "$code" == "200" ]]; then
    printf '  %s%s 1 share bypass%s         expected=200 actual=%s ts=%s rid=%s\n' \
      "$C_GREEN" "PASS" "$C_RESET" "$code" "$ts" "$rid"
    record_result 1 "share bypass" "200" "$code" PASS "$ts" "$rid"
    return 0
  fi
  printf '  %s%s 1 share bypass%s         expected=200 actual=%s ts=%s rid=%s\n' \
    "$C_RED" "FAIL" "$C_RESET" "$code" "$ts" "$rid"
  record_result 1 "share bypass" "200" "$code" FAIL "$ts" "$rid"
  return 1
}

# --- Scenario 2 — Agent ingestion (multipart STL upload) --------------------
scenario_2_agent_ingestion() {
  local ts code rid out cookies login_resp
  ts=$(iso_now)
  cookies="$TMPDIR_RUN/agent-cookies.txt"
  login_resp="$TMPDIR_RUN/agent-login.json"

  # Login as agent → cookie jar
  BODY_OUT="$login_resp" out=$(curl_smoke -c "$cookies" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$AGENT_EMAIL\",\"password\":\"$AGENT_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login")
  code=$(echo "$out" | cut -f1)
  if [[ "$code" != "200" ]]; then
    rid=$(echo "$out" | cut -f2)
    printf '  %s%s 2 agent ingestion%s      expected=200 actual=%s ts=%s rid=%s (login)\n' \
      "$C_RED" "FAIL" "$C_RESET" "$code" "$ts" "$rid"
    record_result 2 "agent ingestion" "201|200" "login=$code" FAIL "$ts" "$rid"
    return 1
  fi
  chmod 600 "$cookies"

  # Reject partial_auth — agent role with 2FA enrollment would land in
  # PartialAuthResponse and the cookie jar would be empty.
  if jq -e '.partial_auth == true' "$login_resp" >/dev/null 2>&1; then
    rid=$(echo "$out" | cut -f2)
    printf '  %s%s 2 agent ingestion%s      expected=full-auth actual=partial ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$ts" "$rid"
    record_result 2 "agent ingestion" "201|200" "partial_auth=true" FAIL "$ts" "$rid"
    return 1
  fi

  # Multipart STL upload
  ts=$(iso_now)
  out=$(curl_smoke -b "$cookies" -X POST \
    -F "file=@${CUTOVER_STL_FIXTURE};type=model/stl" \
    -F "kind=stl" \
    "$PORTAL_URL/api/admin/models/$CUTOVER_TEST_MODEL_ID/files")
  code=$(echo "$out" | cut -f1)
  rid=$(echo "$out" | cut -f2)
  # 201 = new upload; 200 = sha256 dedup (idempotent success per spec dispatch)
  if [[ "$code" == "201" || "$code" == "200" ]]; then
    printf '  %s%s 2 agent ingestion%s      expected=201|200 actual=%s ts=%s rid=%s\n' \
      "$C_GREEN" "PASS" "$C_RESET" "$code" "$ts" "$rid"
    record_result 2 "agent ingestion" "201|200" "$code" PASS "$ts" "$rid"
    return 0
  fi
  printf '  %s%s 2 agent ingestion%s      expected=201|200 actual=%s ts=%s rid=%s\n' \
    "$C_RED" "FAIL" "$C_RESET" "$code" "$ts" "$rid"
  record_result 2 "agent ingestion" "201|200" "$code" FAIL "$ts" "$rid"
  return 1
}

# --- Scenario 3 — Member login -----------------------------------------------
scenario_3_member_login() {
  local ts code rid out cookies login_resp
  ts=$(iso_now)
  cookies="$TMPDIR_RUN/member-cookies.txt"
  login_resp="$TMPDIR_RUN/member-login.json"

  BODY_OUT="$login_resp" out=$(curl_smoke -c "$cookies" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$CUTOVER_TEST_MEMBER_EMAIL\",\"password\":\"$CUTOVER_TEST_MEMBER_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login")
  code=$(echo "$out" | cut -f1)
  rid=$(echo "$out" | cut -f2)
  if [[ "$code" != "200" ]]; then
    printf '  %s%s 3 member login%s         expected=200 actual=%s ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$code" "$ts" "$rid"
    record_result 3 "member login" "200" "$code" FAIL "$ts" "$rid"
    return 1
  fi
  chmod 600 "$cookies"

  # Per AC: expect portal_access cookie set. Reject partial_auth (2FA-enrolled
  # test-member would silently break the smoke).
  if jq -e '.partial_auth == true' "$login_resp" >/dev/null 2>&1; then
    printf '  %s%s 3 member login%s         expected=full-auth actual=partial ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$ts" "$rid"
    record_result 3 "member login" "200" "partial_auth=true" FAIL "$ts" "$rid"
    return 1
  fi
  if ! grep -qE '(^|	)portal_access(	|$)' "$cookies"; then
    printf '  %s%s 3 member login%s         expected=portal_access-cookie actual=missing ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$ts" "$rid"
    record_result 3 "member login" "200+cookie" "no-cookie" FAIL "$ts" "$rid"
    return 1
  fi
  printf '  %s%s 3 member login%s         expected=200+cookie actual=%s ts=%s rid=%s\n' \
    "$C_GREEN" "PASS" "$C_RESET" "$code" "$ts" "$rid"
  record_result 3 "member login" "200+cookie" "$code" PASS "$ts" "$rid"
  return 0
}

# --- Scenario 4 — Admin login + scope verification ---------------------------
scenario_4_admin_login() {
  local ts code rid out cookies login_resp scope_code scope_rid
  ts=$(iso_now)
  cookies="$TMPDIR_RUN/admin-cookies.txt"
  login_resp="$TMPDIR_RUN/admin-login.json"

  BODY_OUT="$login_resp" out=$(curl_smoke -c "$cookies" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login")
  code=$(echo "$out" | cut -f1)
  rid=$(echo "$out" | cut -f2)
  if [[ "$code" != "200" ]]; then
    printf '  %s%s 4 admin login%s          expected=200 actual=%s ts=%s rid=%s (login)\n' \
      "$C_RED" "FAIL" "$C_RESET" "$code" "$ts" "$rid"
    record_result 4 "admin login + scope" "200,200" "login=$code" FAIL "$ts" "$rid"
    return 1
  fi
  chmod 600 "$cookies"

  if jq -e '.partial_auth == true' "$login_resp" >/dev/null 2>&1; then
    printf '  %s%s 4 admin login%s          expected=full-auth actual=partial ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$ts" "$rid"
    record_result 4 "admin login + scope" "200,200" "partial_auth=true" FAIL "$ts" "$rid"
    return 1
  fi

  # Verify admin scope via /api/admin/users (admin-only)
  out=$(curl_smoke -b "$cookies" "$PORTAL_URL/api/admin/users")
  scope_code=$(echo "$out" | cut -f1)
  scope_rid=$(echo "$out" | cut -f2)
  if [[ "$scope_code" != "200" ]]; then
    printf '  %s%s 4 admin login%s          expected=200,200 actual=%s,%s ts=%s rid=%s\n' \
      "$C_RED" "FAIL" "$C_RESET" "$code" "$scope_code" "$ts" "$scope_rid"
    record_result 4 "admin login + scope" "200,200" "$code,$scope_code" FAIL "$ts" "${rid},${scope_rid}"
    return 1
  fi
  printf '  %s%s 4 admin login%s          expected=200,200 actual=%s,%s ts=%s rid=%s\n' \
    "$C_GREEN" "PASS" "$C_RESET" "$code" "$scope_code" "$ts" "$scope_rid"
  record_result 4 "admin login + scope" "200,200" "$code,$scope_code" PASS "$ts" "${rid},${scope_rid}"
  return 0
}

# --- Main: run all scenarios sequentially (race-free correlation) ------------
FAIL_COUNT=0
START_TS=$(date +%s)

scenario_1_share_bypass     || FAIL_COUNT=$((FAIL_COUNT + 1))
scenario_2_agent_ingestion  || FAIL_COUNT=$((FAIL_COUNT + 1))
scenario_3_member_login     || FAIL_COUNT=$((FAIL_COUNT + 1))
scenario_4_admin_login      || FAIL_COUNT=$((FAIL_COUNT + 1))

END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))

echo ""
if (( FAIL_COUNT == 0 )); then
  echo "${C_BOLD}${C_GREEN}cutover-smoke: ✅ 4/4 PASS in ${ELAPSED}s${C_RESET}"
  if (( ELAPSED > 30 )); then
    echo "${C_YELLOW}warning: ${ELAPSED}s exceeds Decision J 30s budget — investigate latency before rollback${C_RESET}" >&2
  fi
  exit 0
fi

echo "${C_BOLD}${C_RED}cutover-smoke: ❌ ${FAIL_COUNT}/4 FAIL in ${ELAPSED}s — trigger rollback per Decision K${C_RESET}"
exit 1
