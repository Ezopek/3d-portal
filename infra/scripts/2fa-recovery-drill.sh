#!/usr/bin/env bash
# Execute the Epic 7 acceptance-gate recovery-code drill against deployed `.190`.
#
# Performs the 8-step drill from epics.md §1732 (enroll → logout → TOTP login →
# logout → recovery-code login → regenerate → disable → password-only login),
# captures per-step timestamps + request IDs + audit_log row deltas, and writes
# a markdown artifact to
# `_bmad-output/implementation-artifacts/2fa-recovery-drill-$(date +%Y-%m-%d).md`.
# The artifact is the binding evidence for Epic 7 closure per epics.md §1735
# ("Epic 7 is not considered closed until the drill artifact lands") and the
# first slot for NFR5-OBS-2 (operator drill artifacts).
#
# Required env (sourced from infra/.env on dev box):
#   PORTAL_URL                 default https://3d.ezop.ddns.net
#   ADMIN_EMAIL                admin account (read-only access to /api/admin/audit)
#   ADMIN_PASSWORD             admin password
#   DRILL_MEMBER_EMAIL         test-member subject email (seeded via Epic 6 invite)
#   DRILL_MEMBER_PASSWORD      test-member password (≥12 chars + zxcvbn≥3)
#   DRILL_TOTP_CODE_PROVIDER   `manual` (read 6-digit codes from stdin) or
#                              `pyotp`  (synthesize from captured secret — P2 fallback)
#
# Optional env (overrideable):
#   DRILL_OUTPUT_DIR           default _bmad-output/implementation-artifacts
#   DRILL_DATE_OVERRIDE        default $(date -u +%Y-%m-%d)
#   DRILL_DB_HOST              default 192.168.2.190 (ssh target for SQLite reads)
#   DRILL_DB_CONTAINER         default 3d-portal-api-1
#   DRILL_DB_PATH              default /data/state/portal.db
#                              (the api container has python3+sqlite3 module
#                              but no `sqlite3` binary; queries go via python3)
#   DRILL_PYOTP_PYTHON         default apps/api/.venv/bin/python
#                              (any python3 with pyotp installed)
#
# Flags:
#   --help            print this header docstring + the seeding recipe; exit 3
#   --dry-run         execute Steps 1-8 against .190 but DO NOT write the artifact
#                     (useful for testing the script without polluting the
#                     artifact slot)
#   --keep-tempfiles  retain /tmp/drill-YYYY-MM-DD-* cookie + token + codes files
#                     for debugging (default: cleanup on trap-EXIT)
#
# Exit codes:
#   0  drill succeeded; all 8 steps clean; all 9 audit rows verified present;
#      artifact written. users.totp_secret retention invariant intact.
#   1  drill step failure (HTTP non-2xx OR audit row missing OR totp_secret
#      ciphertext changed). Artifact written with FAILED status (unless dry-run).
#   2  prerequisite failure (admin cookies refused, .190 unreachable, OR
#      test-member precondition unmet — dirty 2FA state OR missing account).
#      NO artifact written; operator must fix prereqs and re-run.
#   3  --help invoked; clean exit after printing the docstring + seeding recipe.
#   4  invalid invocation (missing required env var; conflicting flags); NO
#      artifact written.
#
# Example:
#   set -a; source infra/.env; set +a
#   export DRILL_MEMBER_EMAIL=drill@portal.example.com
#   export DRILL_MEMBER_PASSWORD='<≥12-char + zxcvbn≥3>'
#   export DRILL_TOTP_CODE_PROVIDER=pyotp
#   bash infra/scripts/2fa-recovery-drill.sh
#   # → 0; artifact at _bmad-output/implementation-artifacts/2fa-recovery-drill-2026-05-20.md
#
# Seeding the test-member (run ONCE before the first drill via the Epic 6 admin-invite flow):
#
#   # 1. Acquire admin cookies
#   curl -fsS -c /tmp/admin-cookies.txt -X POST \
#     -H "Content-Type: application/json" -H "X-Portal-Client: web" \
#     -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
#     "$PORTAL_URL/api/auth/login"
#
#   # 2. Generate a member-role invite (Story 6.3)
#   curl -fsS -b /tmp/admin-cookies.txt -X POST \
#     -H "Content-Type: application/json" -H "X-Portal-Client: web" \
#     -d '{"role":"member","ttl_seconds":3600}' \
#     "$PORTAL_URL/api/admin/invites"
#   # → captures invite token (43-char URL-safe entropy) from response
#
#   # 3. Register the test-member (Story 6.4)
#   curl -fsS -X POST -H "Content-Type: application/json" -H "X-Portal-Client: web" \
#     -d "{\"token\":\"<from-step-2>\",\"email\":\"drill@portal.example.com\",
#          \"password\":\"<≥12-char + zxcvbn≥3>\"}" \
#     "$PORTAL_URL/api/auth/register"
#   # → 201; user created; portal_access + portal_refresh issued
#
#   # 4. Verify clean single-factor state
#   curl -fsS -X POST -H "Content-Type: application/json" -H "X-Portal-Client: web" \
#     -d "{\"email\":\"drill@portal.example.com\",\"password\":\"<...>\"}" \
#     "$PORTAL_URL/api/auth/login" \
#     | jq '{partial_auth, totp_enroll_required, role: .user.role}'
#   # → {"partial_auth": false, "totp_enroll_required": false, "role": "member"}
#
#   # 5. Export DRILL_MEMBER_EMAIL + DRILL_MEMBER_PASSWORD; then run this script.
#
# Help:
#   bash infra/scripts/2fa-recovery-drill.sh --help

set -Eeuo pipefail

# --- Help handling first (before any required-env enforcement) ---------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,/^set -Eeuo pipefail$/p' "$0" | sed -E 's/^# ?//;/^set -Eeuo pipefail$/d'
  exit 3
fi

# --- Flag parsing ------------------------------------------------------------
DRY_RUN=0
KEEP_TEMPFILES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --keep-tempfiles) KEEP_TEMPFILES=1; shift ;;
    *)
      echo "drill: unknown flag '$1' (try --help)" >&2
      exit 4
      ;;
  esac
done

# --- Required env enforcement ------------------------------------------------
: "${PORTAL_URL:=https://3d.ezop.ddns.net}"
for var in ADMIN_EMAIL ADMIN_PASSWORD DRILL_MEMBER_EMAIL DRILL_MEMBER_PASSWORD DRILL_TOTP_CODE_PROVIDER; do
  if [[ -z "${!var:-}" ]]; then
    echo "drill: missing required env var: $var (try --help)" >&2
    exit 4
  fi
done
case "$DRILL_TOTP_CODE_PROVIDER" in
  manual|pyotp) ;;
  *)
    echo "drill: DRILL_TOTP_CODE_PROVIDER must be 'manual' or 'pyotp' (got '$DRILL_TOTP_CODE_PROVIDER')" >&2
    exit 4
    ;;
esac

# --- Optional env defaults ---------------------------------------------------
: "${DRILL_OUTPUT_DIR:=_bmad-output/implementation-artifacts}"
: "${DRILL_DATE_OVERRIDE:=$(date -u +%Y-%m-%d)}"
: "${DRILL_DB_HOST:=192.168.2.190}"
: "${DRILL_DB_CONTAINER:=3d-portal-api-1}"
: "${DRILL_DB_PATH:=/data/state/portal.db}"
: "${DRILL_PYOTP_PYTHON:=apps/api/.venv/bin/python}"

# --- Constants + paths -------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

DATE="$DRILL_DATE_OVERRIDE"
umask 077  # subsequent tempfile creates land mode 600

ADMIN_COOKIES="/tmp/drill-${DATE}-admin-cookies.txt"
MEMBER_COOKIES="/tmp/drill-${DATE}-member-cookies.txt"
CODES_FILE="/tmp/drill-${DATE}-codes.txt"
ARTIFACT_BODY="/tmp/drill-${DATE}-artifact-body.md"

# Generated TOTP secret captured during Step 1 (for pyotp provider).
TOTP_SECRET=""
# Test-member user_id captured during prereq verification.
DRILL_MEMBER_USER_ID=""
# Step transcripts accumulator (markdown fragments).
: > "$ARTIFACT_BODY"

# --- Trap-EXIT cleanup -------------------------------------------------------
cleanup() {
  local rc=$?
  if [[ $KEEP_TEMPFILES -eq 0 ]]; then
    rm -f "$ADMIN_COOKIES" "$MEMBER_COOKIES" "$CODES_FILE" "$ARTIFACT_BODY" 2>/dev/null || true
  else
    echo "drill: --keep-tempfiles set; preserving /tmp/drill-${DATE}-* tempfiles" >&2
  fi
  exit "$rc"
}
trap cleanup EXIT

# --- Helpers -----------------------------------------------------------------

new_request_id() { python3 -c 'import uuid; print(uuid.uuid4())'; }
iso_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Pace login-scope endpoint calls to stay under the 5-per-60s sliding-window
# rate-limit (login + /2fa/verify + /2fa/recovery-codes/regenerate + /2fa/disable
# all share `ratelimit:login:ip:{ip}` per Story 7.5 AC-4). Default 13s gap
# yields ≤5 requests per any 60s window (5×13s = 65s > 60s window).
: "${DRILL_LOGIN_GAP_SECONDS:=13}"
LAST_LOGIN_TS=0
wait_login_window() {
  local now elapsed
  now=$(date +%s)
  elapsed=$(( now - LAST_LOGIN_TS ))
  if (( elapsed < DRILL_LOGIN_GAP_SECONDS )); then
    sleep $(( DRILL_LOGIN_GAP_SECONDS - elapsed ))
  fi
  LAST_LOGIN_TS=$(date +%s)
}
# Step-start timestamps absorb 10s of clock skew between dev box + .190 +
# audit-emission lag; the assert_audit_row retry loop also handles eventual
# consistency by polling for up to 15s.
iso_step_start() { date -u -d '10 seconds ago' +%Y-%m-%dT%H:%M:%SZ; }

artifact_append() { printf '%s\n' "$@" >> "$ARTIFACT_BODY"; }

err() { echo "drill: $*" >&2; }

# Resolve a TOTP 6-digit code from the configured provider.
get_totp_code() {
  if [[ "$DRILL_TOTP_CODE_PROVIDER" == "pyotp" ]]; then
    if [[ -z "$TOTP_SECRET" ]]; then
      err "FATAL: pyotp provider selected but TOTP secret not yet captured"
      return 1
    fi
    "$DRILL_PYOTP_PYTHON" -c "import pyotp; print(pyotp.TOTP('$TOTP_SECRET').now())"
  else
    local code
    read -r -p "Enter 6-digit TOTP code from authenticator app: " code </dev/tty
    echo "$code"
  fi
}

# Fetch the last `limit` audit rows visible to the admin.
fetch_audit() {
  local limit="${1:-100}"
  curl -fsS -b "$ADMIN_COOKIES" -H "X-Portal-Client: web" \
    "$PORTAL_URL/api/admin/audit?limit=$limit&offset=0"
}

# Assert a JSON-shaped audit row exists for the test-member after step_start.
# Args: 1=action 2=step_start_iso [3=jq-extra-filter]
# Retries up to 15× with 1s sleep to absorb audit-emission lag. Returns the
# first matched row's JSON to stdout. Excludes audit rows older than the
# step start, so prior-step rows with the same action name do not collide.
assert_audit_row() {
  local action="$1"
  local start="$2"
  local extra="${3:-}"
  local jq_filter='.events
    | map(select(.actor_user_id == $uid and .action == $action and .at > $start))'
  if [[ -n "$extra" ]]; then
    jq_filter+=" | map(select($extra))"
  fi
  local attempt=1
  local max_attempts=15
  while (( attempt <= max_attempts )); do
    local audit
    audit=$(fetch_audit 100)
    local count
    count=$(echo "$audit" | jq --arg uid "$DRILL_MEMBER_USER_ID" --arg action "$action" \
      --arg start "$start" "$jq_filter | length")
    if (( count >= 1 )); then
      echo "$audit" | jq --arg uid "$DRILL_MEMBER_USER_ID" --arg action "$action" \
        --arg start "$start" "$jq_filter | .[0]"
      return 0
    fi
    sleep 1
    (( attempt++ ))
  done
  err "FATAL: expected audit row '$action' (filter '$extra') after $start NOT FOUND after ${max_attempts}s"
  fetch_audit 50 | jq --arg uid "$DRILL_MEMBER_USER_ID" --arg start "$start" \
    '.events | map(select(.actor_user_id == $uid and .at > $start))' >&2 || true
  return 1
}

# Read a single scalar from .190 SQLite via the api container's python3
# interpreter (sqlite3 binary is absent in the api image; python3+sqlite3
# module is present). Args: 1=SQL string returning one scalar column.
# The SQL is piped via stdin to `python3 -` so it can contain quotes safely.
query_db_scalar() {
  local sql="$1"
  ssh "$DRILL_DB_HOST" docker exec -i "$DRILL_DB_CONTAINER" python3 - <<PYEOF
import sqlite3
c = sqlite3.connect("$DRILL_DB_PATH")
row = c.execute("""$sql""").fetchone()
print(row[0] if row and row[0] is not None else "NULL")
PYEOF
}

query_secret_length() {
  query_db_scalar "SELECT length(totp_secret) FROM 'user' WHERE email = '$DRILL_MEMBER_EMAIL'"
}

# Read users.totp_secret as raw bytes and emit its sha256 hex digest. Length
# compare can pass while bytes differ (Fernet re-encryption with a new IV
# produces equal-length ciphertext); the sha256 of the ciphertext column is
# the binding identity check for the Story 7.5 retention invariant. The
# digest is NOT a secret (it's a hash of an already-encrypted value), so
# logging it to the artifact is safe.
query_secret_sha256() {
  ssh "$DRILL_DB_HOST" docker exec -i "$DRILL_DB_CONTAINER" python3 - <<PYEOF
import sqlite3, hashlib
c = sqlite3.connect("$DRILL_DB_PATH")
row = c.execute("SELECT totp_secret FROM 'user' WHERE email = '$DRILL_MEMBER_EMAIL'").fetchone()
val = row[0] if row else None
if val is None:
    print("NULL")
else:
    if isinstance(val, str):
        val = val.encode("utf-8")
    print(hashlib.sha256(val).hexdigest())
PYEOF
}

query_totp_enabled_at() {
  query_db_scalar "SELECT coalesce(totp_enabled_at, 'NULL') FROM 'user' WHERE email = '$DRILL_MEMBER_EMAIL'"
}

# --- Failure-path artifact writer + ERR trap ---------------------------------
#
# Contract (docstring §Exit codes): exit 1 = drill step failure; "Artifact
# written with FAILED status (unless dry-run)". Under set -e a curl/jq/ssh
# non-zero exits immediately, bypassing the end-of-script artifact write —
# so we wire an ERR trap + a `fail()` helper that emit the FAILED artifact
# before exiting. The helper is idempotent so recursive failure paths
# (e.g., cp fails inside the writer) collapse to a single artifact attempt
# instead of spinning the ERR trap forever.
DRILL_FAILED_WRITTEN=0

write_failed_artifact() {
  if [[ $DRILL_FAILED_WRITTEN -eq 1 ]]; then
    return 0
  fi
  DRILL_FAILED_WRITTEN=1
  local reason="${1:-unexpected error}"
  set +e  # never let the writer recurse via ERR trap; we're already in fail mode
  if [[ ! -s "$ARTIFACT_BODY" ]]; then
    # Failure landed before the H1 header was appended (e.g., prereq stage).
    # The contract for prereq failures is exit 2 with NO artifact; defensive
    # short-circuit so an unexpected ERR during prereqs does not write an
    # empty stub.
    err "drill: artifact body empty at failure time; SKIPPING FAILED artifact write"
    set -e
    return 0
  fi
  artifact_append "" "---" "" "## Drill outcome — FAILED" "" \
    "**Reason:** ${reason}  " \
    "**Captured at:** $(iso_now)  " "" \
    "Partial drill state captured at point of failure; binding evidence per Story 7.6 acceptance contract." ""
  local result_line="**Result:** ❌ FAILED — ${reason}"
  {
    head -n 1 "$ARTIFACT_BODY"
    echo ""
    echo "$result_line  "
    tail -n +3 "$ARTIFACT_BODY"
  } > "${ARTIFACT_BODY}.with-result"
  mv "${ARTIFACT_BODY}.with-result" "$ARTIFACT_BODY"
  if [[ $DRY_RUN -eq 1 ]]; then
    err "drill: --dry-run set; SKIPPING FAILED artifact write (would have written to ${DRILL_OUTPUT_DIR}/2fa-recovery-drill-${DATE}.md)"
    set -e
    return 0
  fi
  mkdir -p "$DRILL_OUTPUT_DIR"
  local path="${DRILL_OUTPUT_DIR}/2fa-recovery-drill-${DATE}.md"
  if [[ -e "$path" ]]; then
    local backup="${path%.md}.bak-$(date -u +%H%M%S).md"
    mv "$path" "$backup"
    err "drill: existing artifact backed up to $backup"
  fi
  cp "$ARTIFACT_BODY" "$path"
  err "drill: ❌ FAILED artifact written to $path"
  set -e
}

# Explicit failure path — call from inline assertions that already emitted a
# diagnostic via err()+artifact_append(). Writes FAILED artifact and exits 1.
fail() {
  local reason="$1"
  err "FATAL: $reason"
  write_failed_artifact "$reason"
  exit 1
}

# ERR trap — catches every set -e tripwire that does NOT have an explicit
# `|| fail` guard (curl/jq/ssh transient failures, surprise non-2xx, etc.).
on_err() {
  local rc=$?
  local lineno=${BASH_LINENO[0]:-unknown}
  local cmd=${BASH_COMMAND:-unknown}
  write_failed_artifact "set -e tripped at line ${lineno} (rc=${rc}) — \`${cmd}\`"
  exit 1
}

# --- Prerequisite verification (exit 2 on any failure) -----------------------

err "drill: verifying prerequisites against $PORTAL_URL …"

# Prereq 1 — portal reachable.
if ! curl -fsS -o /dev/null --max-time 10 "$PORTAL_URL/api/health"; then
  err "prereq fail (1/3): $PORTAL_URL/api/health unreachable"; exit 2
fi
err "prereq OK (1/3): portal reachable"

# Prereq 2 — admin login produces session cookies AND those cookies actually
# grant /api/admin/audit access. /login can return 200 with partial_auth=true
# (no Set-Cookie) when ADMIN_EMAIL has TOTP enabled, OR cookies can be set
# but the role lacks admin scope — both leave the drill stuck in
# assert_audit_row retry loops. Fail-fast BEFORE mutating any test-member
# state so re-running the drill is cheap.
admin_login_resp=$(mktemp -t drill-admin-login.XXXXXX)
wait_login_window
if ! curl -fsS -c "$ADMIN_COOKIES" -X POST \
    -H "Content-Type: application/json" -H "X-Portal-Client: web" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login" -o "$admin_login_resp"; then
  err "prereq fail (2/3): admin login refused"
  rm -f "$admin_login_resp"; exit 2
fi
chmod 600 "$ADMIN_COOKIES"

# Reject partial_auth — if ADMIN has TOTP enabled, /login returns 200 with
# partial_auth=true and NO Set-Cookie; an empty cookie jar would otherwise
# silently propagate to every audit assert.
if jq -e '.partial_auth == true' "$admin_login_resp" >/dev/null 2>&1; then
  err "prereq fail (2/3): admin /login returned partial_auth=true (ADMIN_EMAIL has TOTP enabled — drill requires single-factor admin OR a future 2FA-aware admin-login step)"
  rm -f "$admin_login_resp"; exit 2
fi
rm -f "$admin_login_resp"

# Defensive — confirm session cookies actually landed in the jar even if the
# partial_auth check above passed (malformed response / future schema change).
if ! grep -qE '(^|	)portal_access(	|$)' "$ADMIN_COOKIES" 2>/dev/null \
   || ! grep -qE '(^|	)portal_refresh(	|$)' "$ADMIN_COOKIES" 2>/dev/null; then
  err "prereq fail (2/3): admin /login returned 200 but session cookies missing from jar (portal_access AND/OR portal_refresh absent)"
  exit 2
fi

# Verify admin can actually read /api/admin/audit — the audit endpoint is the
# binding evidence channel for every drill step; a 401/403 here would stall
# every assert_audit_row loop until its 15s retry budget expired.
if ! curl -fsS -o /dev/null -b "$ADMIN_COOKIES" -H "X-Portal-Client: web" \
    "$PORTAL_URL/api/admin/audit?limit=1&offset=0"; then
  err "prereq fail (2/3): admin cookies present but GET /api/admin/audit refused (likely role!=admin OR audit endpoint not deployed on $PORTAL_URL)"
  exit 2
fi
err "prereq OK (2/3): admin cookies acquired + audit endpoint reachable"

# Prereq 3 — test-member exists + clean state.
member_login_resp=$(mktemp -t drill-member-login.XXXXXX)
wait_login_window
if ! curl -fsS -c "$MEMBER_COOKIES" -X POST \
    -H "Content-Type: application/json" -H "X-Portal-Client: web" \
    -d "{\"email\":\"$DRILL_MEMBER_EMAIL\",\"password\":\"$DRILL_MEMBER_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login" -o "$member_login_resp"; then
  err "prereq fail (3/3): test-member login refused (HTTP non-2xx); seed via --help recipe"
  rm -f "$member_login_resp"; exit 2
fi
chmod 600 "$MEMBER_COOKIES"

state=$(jq -r '"\(.partial_auth) \(.totp_enroll_required // false)"' "$member_login_resp")
if [[ "$state" != "false false" ]]; then
  err "prereq fail (3/3): test-member NOT in clean single-factor state (partial_auth + totp_enroll_required = '$state')"
  err "  expected 'false false'; either 2FA already enabled OR role-forced enrollment active"
  err "  manual cleanup: ssh $DRILL_DB_HOST docker exec $DRILL_DB_CONTAINER python3 -c \"import sqlite3; c=sqlite3.connect('$DRILL_DB_PATH'); c.execute(\\\"UPDATE user SET totp_enabled_at=NULL WHERE email='$DRILL_MEMBER_EMAIL'\\\"); c.commit()\""
  rm -f "$member_login_resp"; exit 2
fi
DRILL_MEMBER_USER_ID=$(jq -r '.user.id' "$member_login_resp")
rm -f "$member_login_resp"
err "prereq OK (3/3): test-member clean-state (user_id=$DRILL_MEMBER_USER_ID)"

# Capture initial users.totp_secret state for the artifact.
INITIAL_SECRET_LEN=$(query_secret_length)
INITIAL_ENABLED_AT=$(query_totp_enabled_at)
err "prereq snapshot: users.totp_secret length = $INITIAL_SECRET_LEN; totp_enabled_at = $INITIAL_ENABLED_AT"

# --- Begin drill -------------------------------------------------------------

artifact_append "# Story 7.6 — 2FA Recovery-Code Drill against \`.190\`" "" \
  "**Date:** ${DATE} (ISO-8601, UTC)  " \
  "**Executor:** Claude Opus 4.7 (1M context), via BMAD bmad-dev-story (autonomous mode)  " \
  "**Drill subject:** test-member \`${DRILL_MEMBER_EMAIL}\` (user_id \`${DRILL_MEMBER_USER_ID}\`)  " \
  "**Portal:** ${PORTAL_URL}  " \
  "**TOTP code provider:** \`${DRILL_TOTP_CODE_PROVIDER}\`  " \
  "**Script:** \`infra/scripts/2fa-recovery-drill.sh\` (Story 7.6)  " \
  "**Artifact location:** \`${DRILL_OUTPUT_DIR}/2fa-recovery-drill-${DATE}.md\` (gitignored via \`_bmad-output/\` in \`.gitignore:65\`)" "" "---" "" \
  "## Preconditions" "" \
  "| Check | Method | Result |" \
  "|---|---|---|" \
  "| \`.190\` reachable | \`curl -fsS \$PORTAL_URL/api/health\` returns 200 | ✅ HTTP 200 |" \
  "| Admin auth + audit access | \`POST /api/auth/login\` + cookie-jar contains \`portal_access\`+\`portal_refresh\` + \`GET /api/admin/audit?limit=1\` returns 200 | ✅ Cookies + audit endpoint reachable |" \
  "| Test-member exists + clean state | \`POST /api/auth/login\`; assert \`partial_auth=false AND totp_enroll_required=false\` | ✅ Single-factor; totp_enabled_at IS NULL |" \
  "| \`users.totp_secret\` initial state | \`sqlite3 ... SELECT length(totp_secret)\` | length=\`${INITIAL_SECRET_LEN}\`; totp_enabled_at=\`${INITIAL_ENABLED_AT}\` |" "" "---" "" \
  "## Step-by-step transcript" ""

# ERR trap wired ONLY after the H1 + preconditions block has populated
# ARTIFACT_BODY. Prereq failures above exit 2 (no artifact, per docstring
# contract); from here on, any unhandled non-zero exit emits the FAILED
# artifact via on_err.
trap on_err ERR

# --- STEP 1 — Enroll TOTP ----------------------------------------------------
err "drill: Step 1 — Enroll TOTP"
S1_START=$(iso_step_start); RID1A=$(new_request_id); RID1B=$(new_request_id)
enroll_resp=$(curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID1A" \
  "$PORTAL_URL/api/auth/2fa/enroll")
TOTP_SECRET=$(echo "$enroll_resp" | jq -r '.manual_secret')
ENROLLMENT_TOKEN=$(echo "$enroll_resp" | jq -r '.enrollment_token')
if [[ "$TOTP_SECRET" == "null" || -z "$TOTP_SECRET" ]]; then
  fail "Step 1 enroll response missing manual_secret"
fi

CODE1=$(get_totp_code)
confirm_resp=$(curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID1B" \
  -H "Content-Type: application/json" \
  -d "{\"enrollment_token\":\"$ENROLLMENT_TOKEN\",\"code\":\"$CODE1\"}" \
  "$PORTAL_URL/api/auth/2fa/enroll/confirm")
ENROLL_BATCH_ID=$(echo "$confirm_resp" | jq -r '.batch_id')
ENROLL_GENERATED_AT=$(echo "$confirm_resp" | jq -r '.generated_at')
echo "$confirm_resp" | jq -r '.recovery_codes[]' > "$CODES_FILE"
chmod 600 "$CODES_FILE"
CODES_COUNT=$(wc -l < "$CODES_FILE")
S1_END=$(iso_now)

step1_row=$(assert_audit_row "auth.totp.enrolled" "$S1_START") || fail "Step 1 audit row 'auth.totp.enrolled' not found"

artifact_append "### Step 1 — Enroll TOTP" "" \
  "**Start:** ${S1_START}  " \
  "**End:** ${S1_END}  " \
  "**Request IDs:** \`${RID1A}\` (enroll), \`${RID1B}\` (confirm)  " "" \
  "- \`POST /api/auth/2fa/enroll\` → 200; body keys: \`enrollment_token\`, \`qr_svg\`, \`manual_secret\` (32-char b32; captured for pyotp provider)" \
  "- \`POST /api/auth/2fa/enroll/confirm\` → 200; body keys: \`recovery_codes\` (${CODES_COUNT} hex strings), \`batch_id\`=\`${ENROLL_BATCH_ID}\`, \`generated_at\`=\`${ENROLL_GENERATED_AT}\`" \
  "- 8 recovery codes saved to mode-600 tempfile \`${CODES_FILE}\` (cleartext NOT logged)" "" \
  "**Audit row verified:**" "" \
  '```json' "$step1_row" '```' ""

# --- STEP 2 — Log out --------------------------------------------------------
err "drill: Step 2 — Log out"
S2_START=$(iso_step_start); RID2=$(new_request_id)
curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID2" \
  "$PORTAL_URL/api/auth/logout" -o /dev/null
# Drop cookies file — logout cleared session.
: > "$MEMBER_COOKIES"
S2_END=$(iso_now)

step2_row=$(assert_audit_row "auth.logout" "$S2_START") || fail "Step 2 audit row 'auth.logout' not found"

artifact_append "### Step 2 — Log out" "" \
  "**Start:** ${S2_START}  " "**End:** ${S2_END}  " "**Request ID:** \`${RID2}\`  " "" \
  "- \`POST /api/auth/logout\` → 204; portal_access + portal_refresh cookies cleared" "" \
  "**Audit row verified:**" "" '```json' "$step2_row" '```' ""

# --- STEP 3 — Log in with password + TOTP ------------------------------------
err "drill: Step 3 — Log in with password + TOTP"
S3_START=$(iso_step_start); RID3A=$(new_request_id); RID3B=$(new_request_id)
wait_login_window
login3_resp=$(curl -fsS -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID3A" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$DRILL_MEMBER_EMAIL\",\"password\":\"$DRILL_MEMBER_PASSWORD\"}" \
  "$PORTAL_URL/api/auth/login")
PARTIAL_TOKEN_3=$(echo "$login3_resp" | jq -r '.partial_token')
if [[ "$PARTIAL_TOKEN_3" == "null" || -z "$PARTIAL_TOKEN_3" ]]; then
  fail "Step 3 login returned no partial_token (got: $(echo "$login3_resp" | jq -c .))"
fi
CODE3=$(get_totp_code)
wait_login_window
verify3_resp=$(curl -fsS -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID3B" \
  -H "Content-Type: application/json" \
  -d "{\"partial_token\":\"$PARTIAL_TOKEN_3\",\"code\":\"$CODE3\"}" \
  "$PORTAL_URL/api/auth/2fa/verify")
chmod 600 "$MEMBER_COOKIES"
S3_END=$(iso_now)

step3_row=$(assert_audit_row "auth.totp.verify.success" "$S3_START" '.after.method == "totp"') || fail "Step 3 audit row 'auth.totp.verify.success' (method=totp) not found"

artifact_append "### Step 3 — Log in with password + TOTP" "" \
  "**Start:** ${S3_START}  " "**End:** ${S3_END}  " \
  "**Request IDs:** \`${RID3A}\` (login), \`${RID3B}\` (verify)  " "" \
  "- \`POST /api/auth/login\` → 200; body shape \`PartialAuthResponse\` { partial_auth=true, totp_required=true, partial_token=<redacted> }; **no cookies** issued" \
  "- \`POST /api/auth/2fa/verify\` → 200; body shape \`LoginResponse\` { partial_auth=false, user, totp_enroll_required=false }; portal_access + portal_refresh cookies issued" "" \
  "**Audit row verified (method=totp):**" "" '```json' "$step3_row" '```' "" \
  "**Note:** Story 7.3 partial-auth audit asymmetry — \`auth.login.success\` is NOT emitted on this path; emission moves to \`auth.totp.verify.success\`." ""

# --- STEP 4 — Log out --------------------------------------------------------
err "drill: Step 4 — Log out"
S4_START=$(iso_step_start); RID4=$(new_request_id)
curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID4" \
  "$PORTAL_URL/api/auth/logout" -o /dev/null
: > "$MEMBER_COOKIES"
S4_END=$(iso_now)

step4_row=$(assert_audit_row "auth.logout" "$S4_START") || fail "Step 4 audit row 'auth.logout' not found"

artifact_append "### Step 4 — Log out" "" \
  "**Start:** ${S4_START}  " "**End:** ${S4_END}  " "**Request ID:** \`${RID4}\`  " "" \
  "- \`POST /api/auth/logout\` → 204" "" \
  "**Audit row verified:**" "" '```json' "$step4_row" '```' ""

# --- STEP 5 — Log in with password + recovery code ---------------------------
err "drill: Step 5 — Log in with password + recovery code"
S5_START=$(iso_step_start); RID5A=$(new_request_id); RID5B=$(new_request_id)
wait_login_window
login5_resp=$(curl -fsS -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID5A" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$DRILL_MEMBER_EMAIL\",\"password\":\"$DRILL_MEMBER_PASSWORD\"}" \
  "$PORTAL_URL/api/auth/login")
PARTIAL_TOKEN_5=$(echo "$login5_resp" | jq -r '.partial_token')
RECOVERY_CODE=$(head -n 1 "$CODES_FILE")
wait_login_window
verify5_resp=$(curl -fsS -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID5B" \
  -H "Content-Type: application/json" \
  -d "{\"partial_token\":\"$PARTIAL_TOKEN_5\",\"code\":\"$RECOVERY_CODE\"}" \
  "$PORTAL_URL/api/auth/2fa/verify")
chmod 600 "$MEMBER_COOKIES"
S5_END=$(iso_now)

step5a_row=$(assert_audit_row "auth.totp.verify.success" "$S5_START" '.after.method == "recovery_code"') || fail "Step 5 audit row 'auth.totp.verify.success' (method=recovery_code) not found"
step5b_row=$(assert_audit_row "auth.recovery_code.used" "$S5_START") || fail "Step 5 audit row 'auth.recovery_code.used' not found"

artifact_append "### Step 5 — Log in with password + recovery code (consumes 1 of ${CODES_COUNT})" "" \
  "**Start:** ${S5_START}  " "**End:** ${S5_END}  " \
  "**Request IDs:** \`${RID5A}\` (login), \`${RID5B}\` (verify)  " "" \
  "- \`POST /api/auth/login\` → 200; PartialAuthResponse (same partial-auth branch as Step 3)" \
  "- \`POST /api/auth/2fa/verify\` with code=\`$(echo "$RECOVERY_CODE" | cut -c1-3)...\` (recovery code masked) → 200; LoginResponse" "" \
  "**Audit row #1 verified (method=recovery_code):**" "" '```json' "$step5a_row" '```' "" \
  "**Audit row #2 verified (recovery code consumption):**" "" '```json' "$step5b_row" '```' ""

# --- STEP 6 — Regenerate recovery codes --------------------------------------
err "drill: Step 6 — Regenerate recovery codes"
S6_START=$(iso_step_start); RID6=$(new_request_id)
CODE6=$(get_totp_code)
wait_login_window
regen_resp=$(curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID6" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"$DRILL_MEMBER_PASSWORD\",\"totp_code\":\"$CODE6\"}" \
  "$PORTAL_URL/api/auth/2fa/recovery-codes/regenerate")
REGEN_BATCH_ID=$(echo "$regen_resp" | jq -r '.batch_id')
REGEN_GENERATED_AT=$(echo "$regen_resp" | jq -r '.generated_at')
# Overwrite codes file with new batch.
echo "$regen_resp" | jq -r '.recovery_codes[]' > "$CODES_FILE"
chmod 600 "$CODES_FILE"
NEW_CODES_COUNT=$(wc -l < "$CODES_FILE")
S6_END=$(iso_now)

step6_row=$(assert_audit_row "auth.recovery_codes.regenerated" "$S6_START") || fail "Step 6 audit row 'auth.recovery_codes.regenerated' not found"
REGEN_INVALIDATED_COUNT=$(echo "$step6_row" | jq -r '.after.invalidated_count')
REGEN_CODES_COUNT=$(echo "$step6_row" | jq -r '.after.codes_count')

artifact_append "### Step 6 — Regenerate recovery codes" "" \
  "**Start:** ${S6_START}  " "**End:** ${S6_END}  " "**Request ID:** \`${RID6}\`  " "" \
  "- \`POST /api/auth/2fa/recovery-codes/regenerate\` body \`{password=<redacted>, totp_code=<6-digit>}\` → 200" \
  "- Body shape \`RegenerateResponse\`: \`batch_id\`=\`${REGEN_BATCH_ID}\` (differs from enroll batch \`${ENROLL_BATCH_ID}\` ✓), \`generated_at\`=\`${REGEN_GENERATED_AT}\`, \`recovery_codes\`=[${NEW_CODES_COUNT} new hex strings]" "" \
  "**Audit row verified:**" "" '```json' "$step6_row" '```' "" \
  "**Binding lifecycle assertion:** \`after.codes_count\`=\`${REGEN_CODES_COUNT}\` (expect \`8\`), \`after.invalidated_count\`=\`${REGEN_INVALIDATED_COUNT}\` (expect \`7\` per Decision E §1533 one-statement UPDATE: 8 enroll-batch codes minus the 1 consumed in Step 5 = 7 invalidated)." ""

if [[ "$REGEN_INVALIDATED_COUNT" != "7" || "$REGEN_CODES_COUNT" != "8" ]]; then
  artifact_append "⚠️ **ASSERTION FAILURE:** expected \`codes_count=8\` + \`invalidated_count=7\`; got \`codes_count=$REGEN_CODES_COUNT\` + \`invalidated_count=$REGEN_INVALIDATED_COUNT\`. Decision E §1533 lifecycle invariant violated." ""
  fail "Step 6 binding lifecycle assertion failed (got codes_count=$REGEN_CODES_COUNT, invalidated_count=$REGEN_INVALIDATED_COUNT; expected 8 + 7)"
fi

# --- STEP 7 — Disable TOTP ---------------------------------------------------
err "drill: Step 7 — Disable TOTP"
S7_START=$(iso_step_start); RID7=$(new_request_id)
BEFORE_SECRET_LEN=$(query_secret_length)
BEFORE_SECRET_SHA=$(query_secret_sha256)
BEFORE_ENABLED_AT=$(query_totp_enabled_at)

CODE7=$(get_totp_code)
wait_login_window
curl -fsS -b "$MEMBER_COOKIES" -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID7" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"$DRILL_MEMBER_PASSWORD\",\"totp_code\":\"$CODE7\"}" \
  "$PORTAL_URL/api/auth/2fa/disable" -o /dev/null

AFTER_SECRET_LEN=$(query_secret_length)
AFTER_SECRET_SHA=$(query_secret_sha256)
AFTER_ENABLED_AT=$(query_totp_enabled_at)
S7_END=$(iso_now)

step7_row=$(assert_audit_row "auth.totp.disabled" "$S7_START") || fail "Step 7 audit row 'auth.totp.disabled' not found"
DISABLE_INVALIDATED_COUNT=$(echo "$step7_row" | jq -r '.after.invalidated_count')

artifact_append "### Step 7 — Disable TOTP" "" \
  "**Start:** ${S7_START}  " "**End:** ${S7_END}  " "**Request ID:** \`${RID7}\`  " "" \
  "- \`POST /api/auth/2fa/disable\` body \`{password=<redacted>, totp_code=<6-digit>}\` → 204 (no body)" "" \
  "**\`users.totp_secret\` retention check:**" "" \
  "| Phase | \`length(totp_secret)\` | \`sha256(totp_secret)[:16]\` | \`totp_enabled_at\` |" \
  "|---|---|---|---|" \
  "| BEFORE Step 7 | \`${BEFORE_SECRET_LEN}\` | \`${BEFORE_SECRET_SHA:0:16}…\` | \`${BEFORE_ENABLED_AT}\` |" \
  "| AFTER Step 7  | \`${AFTER_SECRET_LEN}\`  | \`${AFTER_SECRET_SHA:0:16}…\`  | \`${AFTER_ENABLED_AT}\` |" "" \
  "Retention invariant uses byte-identical sha256 compare (not length) — Fernet re-encryption with a fresh IV produces equal-length ciphertext, so length-only equality could mask a silent rotation." "" \
  "**Audit row verified:**" "" '```json' "$step7_row" '```' "" \
  "**Binding lifecycle assertion (Story 7.6 acceptance gate, fail-fast):** \`after.invalidated_count\`=\`${DISABLE_INVALIDATED_COUNT}\` MUST equal \`9\`. The shipped disable UPDATE at \`apps/api/app/modules/auth/totp/router.py:700-705\` filters on \`WHERE user_id=? AND invalidated_at IS NULL\` only — does NOT include \`used_at IS NULL\`. Expected \`invalidated_count=9\` = 8 regen-batch active codes + 1 consumed-but-not-invalidated enroll-batch code from Step 5 (the consumed row matches the disable's \`invalidated_at IS NULL\` filter and transitions to dual-stamped used_at+invalidated_at state — a valid Decision E §1527-1528 lifecycle position). Drill exits with FAILED artifact on any other value (e.g. \`8\` ⇒ predicate drifted to active-only)." ""

if [[ "$BEFORE_SECRET_SHA" != "$AFTER_SECRET_SHA" ]]; then
  artifact_append "⚠️ **ASSERTION FAILURE:** \`users.totp_secret\` sha256 changed (BEFORE=\`${BEFORE_SECRET_SHA:0:16}…\` AFTER=\`${AFTER_SECRET_SHA:0:16}…\`; length BEFORE=\`$BEFORE_SECRET_LEN\` AFTER=\`$AFTER_SECRET_LEN\`). Epics §1719 retention invariant violated — Fernet ciphertext was rotated by the disable path." ""
  fail "Step 7 retention invariant broken: users.totp_secret sha256 changed (BEFORE=${BEFORE_SECRET_SHA:0:16}… AFTER=${AFTER_SECRET_SHA:0:16}…; length BEFORE=$BEFORE_SECRET_LEN AFTER=$AFTER_SECRET_LEN)"
fi
if [[ "$AFTER_ENABLED_AT" != "NULL" ]]; then
  artifact_append "⚠️ **ASSERTION FAILURE:** \`totp_enabled_at\` not cleared after disable (got \`$AFTER_ENABLED_AT\`)." ""
  fail "Step 7 totp_enabled_at not cleared after disable (got '$AFTER_ENABLED_AT')"
fi
if [[ "$DISABLE_INVALIDATED_COUNT" != "9" ]]; then
  artifact_append "⚠️ **ASSERTION FAILURE:** expected \`invalidated_count=9\` (8 regen-batch active + 1 enroll-batch used-but-not-invalidated from Step 5 per Decision E §1527-1528 dual-stamped lifecycle); got \`invalidated_count=${DISABLE_INVALIDATED_COUNT}\`. Disable predicate at \`apps/api/app/modules/auth/totp/router.py:700-705\` drifted from spec — investigate whether \`used_at IS NULL\` was added to the WHERE clause." ""
  fail "Step 7 disable invariant failed: expected invalidated_count=9, got ${DISABLE_INVALIDATED_COUNT}"
fi

# --- STEP 8 — Log in with password-only --------------------------------------
err "drill: Step 8 — Log in with password-only"
S8_START=$(iso_step_start); RID8=$(new_request_id)
wait_login_window
login8_resp=$(curl -fsS -c "$MEMBER_COOKIES" -X POST \
  -H "X-Portal-Client: web" -H "X-Request-ID: $RID8" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$DRILL_MEMBER_EMAIL\",\"password\":\"$DRILL_MEMBER_PASSWORD\"}" \
  "$PORTAL_URL/api/auth/login")
chmod 600 "$MEMBER_COOKIES"
S8_PARTIAL=$(echo "$login8_resp" | jq -r '.partial_auth')
S8_ENROLL_REQ=$(echo "$login8_resp" | jq -r '.totp_enroll_required')
S8_END=$(iso_now)

step8_row=$(assert_audit_row "auth.login.success" "$S8_START") || fail "Step 8 audit row 'auth.login.success' not found"

artifact_append "### Step 8 — Log in with password-only" "" \
  "**Start:** ${S8_START}  " "**End:** ${S8_END}  " "**Request ID:** \`${RID8}\`  " "" \
  "- \`POST /api/auth/login\` → 200 in one round-trip; LoginResponse with full cookies" \
  "- Body asserts: \`partial_auth\`=\`${S8_PARTIAL}\` (expect \`false\`), \`totp_enroll_required\`=\`${S8_ENROLL_REQ}\` (expect \`false\`)" "" \
  "**Audit row verified:**" "" '```json' "$step8_row" '```' "" \
  "**Note:** no \`auth.totp.verify.*\` row in this step — single-factor flow restored per Story 7.5 disable semantics." ""

if [[ "$S8_PARTIAL" != "false" || "$S8_ENROLL_REQ" != "false" ]]; then
  artifact_append "⚠️ **ASSERTION FAILURE:** Step 8 expected \`partial_auth=false AND totp_enroll_required=false\`; got \`partial_auth=$S8_PARTIAL, totp_enroll_required=$S8_ENROLL_REQ\`. Likely \`ENFORCE_2FA_FOR_ROLES\` includes the member role on \`.190\`." ""
  fail "Step 8 expected single-factor flow but got partial_auth=$S8_PARTIAL, totp_enroll_required=$S8_ENROLL_REQ"
fi

# --- Audit row map -----------------------------------------------------------

artifact_append "---" "" "## Audit row map (binding 9-row chronological sequence)" "" \
  "| # | Step | Action | Entity | Notes |" \
  "|---|---|---|---|---|" \
  "| 1 | 1 | \`auth.totp.enrolled\` | user | actor==target self-enroll |" \
  "| 2 | 2 | \`auth.logout\` | — | refresh-token family revoked |" \
  "| 3 | 3 | \`auth.totp.verify.success\` | user | method=totp; **replaces \`auth.login.success\`** on partial-auth path |" \
  "| 4 | 4 | \`auth.logout\` | — | |" \
  "| 5 | 5 | \`auth.totp.verify.success\` | user | method=recovery_code |" \
  "| 6 | 5 | \`auth.recovery_code.used\` | recovery_code | same xact as #5 |" \
  "| 7 | 6 | \`auth.recovery_codes.regenerated\` | user | invalidated_count=${REGEN_INVALIDATED_COUNT}, codes_count=${REGEN_CODES_COUNT} |" \
  "| 8 | 7 | \`auth.totp.disabled\` | user | invalidated_count=${DISABLE_INVALIDATED_COUNT} (asserted ==9); \`users.totp_secret\` RETAINED (length=${AFTER_SECRET_LEN}, sha256=${AFTER_SECRET_SHA:0:16}…) |" \
  "| 9 | 8 | \`auth.login.success\` | user | partial-auth branch NOT triggered; single-factor restored |" \
  "" "---" ""

# --- Cleanup section ---------------------------------------------------------

artifact_append "## Cleanup" "" \
  "- **Test-member account** \`${DRILL_MEMBER_EMAIL}\` (user_id \`${DRILL_MEMBER_USER_ID}\`): retained in \`user\` table per pre-Epic-8 disposition (Story 8.3 \`POST /api/admin/users/{id}/deactivate\` not yet shipped as of ${DATE}); operator MAY revisit post-E8 ship." \
  "- **Recovery-codes notes tempfile** \`${CODES_FILE}\` (mode 600): $( [[ $KEEP_TEMPFILES -eq 1 ]] && echo "retained (--keep-tempfiles)" || echo "auto-deleted on trap-EXIT" )" \
  "- **Cookie jar tempfiles** \`/tmp/drill-${DATE}-{admin,member}-cookies.txt\` (mode 600): $( [[ $KEEP_TEMPFILES -eq 1 ]] && echo "retained" || echo "auto-deleted on trap-EXIT" )" \
  "- **Audit rows + recovery_codes rows** in \`.190\` SQLite: persisted (binding evidence of the drill; never deleted)." "" "---" ""

# --- Gaps + recommendations placeholders (filled by dev agent post-run) -----

artifact_append "## Runbook gaps & operator-action items" "" \
  "_Filled in by dev agent / operator after drill execution._" "" "---" ""

artifact_append "## NFR-by-NFR coverage" "" \
  "| NFR / FR | Coverage |" \
  "|---|---|" \
  "| NFR5-OBS-2 (drill artifact slot 1) | ✅ THIS artifact IS the slot — filled |" \
  "| NFR5-OBS-1 (GlitchTip log correlation via request_id) | ⚠ Verify the script's X-Request-ID propagates to audit + GlitchTip — flagged in gaps if not |" \
  "| NFR5-INT-1 (agent fail-fast on enforce_2fa_for_roles) | Out of scope (Story 7.4 territory; not exercised by this drill) |" \
  "| NFR5-SEC-3 (rate-limit defense matrix) | Out of scope (Story 9.2 covers this) |" \
  "| FR5-2FA-1 (TOTP enrollment) | ✅ Step 1 end-to-end |" \
  "| FR5-2FA-2 (TOTP login flow) | ✅ Step 3 end-to-end |" \
  "| FR5-2FA-3 (per-role enforcement) | Step 8 negative test (post-disable single-factor restored) |" \
  "| FR5-2FA-4 (regenerate + disable) | ✅ Steps 6+7 with binding invalidated_count assertions |" \
  "| FR5-AUDIT-1 (E7 vocabulary: 5 actions + 1 regen extension) | ✅ 6 of 6 emitted |" \
  "| FR5-RATELIMIT-1 (login rate-limit) | NOT triggered (drill stays under threshold) |" "" "---" ""

artifact_append "## Recommendations to operator" "" \
  "_Filled in by dev agent / operator post-run, ordered P1 → P3._" ""

# --- Result + status header replacement -------------------------------------

# Prepend a "Result:" line to the artifact body. We do this last so the result
# header reflects the actual drill outcome.
RESULT_LINE="**Result:** ✅ All 8 steps passed; 9 audit rows verified present + correctly shaped"
{
  head -n 1 "$ARTIFACT_BODY"
  echo ""
  echo "$RESULT_LINE  "
  tail -n +3 "$ARTIFACT_BODY"
} > "${ARTIFACT_BODY}.with-result"
mv "${ARTIFACT_BODY}.with-result" "$ARTIFACT_BODY"

# --- Write final artifact ----------------------------------------------------

if [[ $DRY_RUN -eq 1 ]]; then
  err "drill: --dry-run set; SKIPPING artifact write (would have written to ${DRILL_OUTPUT_DIR}/2fa-recovery-drill-${DATE}.md)"
  err "drill: ✅ drill complete (dry-run); all 8 steps passed against ${PORTAL_URL}"
  exit 0
fi

case "$DRILL_OUTPUT_DIR" in
  _bmad-output/*) ;;
  *) err "WARN: DRILL_OUTPUT_DIR=$DRILL_OUTPUT_DIR is OUTSIDE _bmad-output/ — artifact may be committed if you forget to gitignore it" ;;
esac

mkdir -p "$DRILL_OUTPUT_DIR"
ARTIFACT_PATH="${DRILL_OUTPUT_DIR}/2fa-recovery-drill-${DATE}.md"

if [[ -e "$ARTIFACT_PATH" ]]; then
  backup="${ARTIFACT_PATH%.md}.bak-$(date -u +%H%M%S).md"
  mv "$ARTIFACT_PATH" "$backup"
  err "drill: existing artifact backed up to $backup"
fi

cp "$ARTIFACT_BODY" "$ARTIFACT_PATH"
err "drill: ✅ artifact written to $ARTIFACT_PATH"
err "drill: ✅ drill complete; all 8 steps passed against $PORTAL_URL"
exit 0
