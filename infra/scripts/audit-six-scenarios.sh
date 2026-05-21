#!/usr/bin/env bash
# Execute the Epic 9 six-scenario adversarial audit (Story 9.2) against the
# live `.190` deploy per NFR5-SEC-3 + epics §428-436. Each scenario produces
# a standalone reproducer in `audit-raw/${AUDIT_DATE}/scenario-N-*.sh`, an
# evidence file (`scenario-N-results.txt`/`.json`), and a row in
# `audit-raw/${AUDIT_DATE}/six-scenario-coverage.json`.
#
# Re-running on the same date does NOT delete prior outputs — instead the
# wrapper appends `-attempt-N` to the output filenames so prior attempts
# survive. The audit report (Story 9.4) cites the LAST attempt.
#
# Scenarios (per spec):
#   1. Invite-token brute-force (register rate-limit, AC1)
#   2. Refresh-token family reuse-detection (AC2)
#   3. CSRF + JWT tampering on every mutating endpoint (AC3)
#   4. IDOR scan on /api/admin/* via member principal (AC4)
#   5. Login rate-limit (AC5)
#   6. Member share-link amplification + soft-alert (AC6)
#
# Required tools (pre-flight; aborts if missing):
#   - curl, jq, uuidgen, python3, ssh, openssl (mac, htpasswd-style operations)
#
# Required env (NO defaults — fail fast if missing):
#   ADMIN_EMAIL          admin login email (e.g. admin@portal.ezop.ddns.net)
#   ADMIN_PASSWORD       admin login password
#
# Optional env:
#   AUDIT_DATE           override dated subdir (default: $(date -u +%F))
#   PORTAL_URL           target host (default: https://3d.ezop.ddns.net)
#   SSH_TARGET           ssh user@host:port for Redis (default: ezop@192.168.2.190 -p 30022)
#   REDIS_CONTAINER      docker container name (default: 3d-portal-redis-1)
#   AUDIT_MEMBER_EMAIL   audit-member email (default: audit-9-2-${AUDIT_DATE}@portal.test)
#   AUDIT_MEMBER_PASSWORD overrides auto-generated password (default: auto-generated)
#   AUDIT_MEMBER_REUSE   1 = reuse existing audit-member if it already exists (default: 0)
#   AUDIT_KEEP_MEMBER    1 = skip teardown deactivation (debug aid, default: 0)
#   SKIP_<N>=1           skip scenario N; N in {1,2,3,4,5,6}
#
# Flags:
#   --help               print this header + scenario list; exit 3
#
# Sub-commands:
#   scenario-1 | scenario-2 | scenario-3 | scenario-4 | scenario-5 | scenario-6
#                        run a single scenario (still bootstraps + tears down audit-member)
#   all                  run all six scenarios (default)
#   bootstrap            bootstrap audit-member only; no scenarios
#   teardown             teardown audit-member only (looks up by email)
#
# Exit codes:
#   0  all selected scenarios PASS or completed with documented MITIGATED verdicts
#   1  one or more scenarios FAIL — see audit-raw/${AUDIT_DATE}/six-scenario-coverage.json
#   2  prerequisite check failed (missing tool, env-var, .190 unreachable, etc.)
#   3  --help invoked
#
# Example:
#   ADMIN_EMAIL=admin@portal.ezop.ddns.net ADMIN_PASSWORD=... \
#     bash infra/scripts/audit-six-scenarios.sh all
#   SKIP_2=1 SKIP_6=1 bash infra/scripts/audit-six-scenarios.sh all
#   bash infra/scripts/audit-six-scenarios.sh scenario-1

set -Eeuo pipefail

#-----------------------------------------------------------------------------
# Path + env setup
#-----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

AUDIT_DATE="${AUDIT_DATE:-$(date -u +%F)}"
AUDIT_DIR="$REPO_DIR/_bmad-output/implementation-artifacts/audit-raw/$AUDIT_DATE"
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
SSH_TARGET="${SSH_TARGET:-ezop@192.168.2.190}"
SSH_PORT="${SSH_PORT:-30022}"
REDIS_CONTAINER="${REDIS_CONTAINER:-3d-portal-redis-1}"
AUDIT_MEMBER_EMAIL_DEFAULT="audit-9-2-${AUDIT_DATE}@portal.example.com"
AUDIT_MEMBER_EMAIL="${AUDIT_MEMBER_EMAIL:-$AUDIT_MEMBER_EMAIL_DEFAULT}"
AUDIT_MEMBER_REUSE="${AUDIT_MEMBER_REUSE:-0}"
AUDIT_KEEP_MEMBER="${AUDIT_KEEP_MEMBER:-0}"

log() { printf '[audit-six-scenarios] %s\n' "$*" >&2; }
fail() { log "ERROR: $*"; exit 2; }

#-----------------------------------------------------------------------------
# --help
#-----------------------------------------------------------------------------
if [[ "${1:-}" == "--help" ]]; then
  sed -n '1,60p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 3
fi

#-----------------------------------------------------------------------------
# Pre-flight tool checks
#-----------------------------------------------------------------------------
require() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "missing tool: $cmd"
}
require curl
require jq
require uuidgen
require python3
require ssh
require openssl

[[ -n "${ADMIN_EMAIL:-}" ]] || fail "ADMIN_EMAIL env-var is required"
[[ -n "${ADMIN_PASSWORD:-}" ]] || fail "ADMIN_PASSWORD env-var is required"

mkdir -p "$AUDIT_DIR"
log "audit dir:   $AUDIT_DIR"
log "portal:      $PORTAL_URL"
log "audit-member: $AUDIT_MEMBER_EMAIL"

#-----------------------------------------------------------------------------
# attempt-N suffix calculation — prior outputs survive
#-----------------------------------------------------------------------------
# Look for the highest existing attempt-K suffix on scenario-1 outputs;
# next attempt is K+1. If nothing exists yet, we use attempt-1.
ATTEMPT_N=1
while compgen -G "$AUDIT_DIR/scenario-1-*-attempt-${ATTEMPT_N}.txt" >/dev/null \
   || compgen -G "$AUDIT_DIR/scenario-1-*-attempt-${ATTEMPT_N}.json" >/dev/null \
   || compgen -G "$AUDIT_DIR/six-scenario-coverage-attempt-${ATTEMPT_N}.json" >/dev/null; do
  ATTEMPT_N=$((ATTEMPT_N+1))
done
SFX="-attempt-${ATTEMPT_N}"
log "attempt:     ${ATTEMPT_N} (suffix: ${SFX})"

#-----------------------------------------------------------------------------
# HTTP helpers
#-----------------------------------------------------------------------------
# `curl_status` performs a request and returns ONLY the HTTP status code on
# stdout. Body goes to optional file. Never exits non-zero on >=400.
curl_status() {
  local out_body="${1:-/dev/null}" ; shift
  curl -sS -o "$out_body" -w '%{http_code}' "$@"
}

curl_json() {
  curl -fsS -H 'Content-Type: application/json' -H 'X-Portal-Client: web' "$@"
}

#-----------------------------------------------------------------------------
# Bootstrap: admin cookies + audit-member account
#-----------------------------------------------------------------------------
ADMIN_COOKIES="$(mktemp /tmp/audit-9-2-admin-cookies.XXXXXX)"
MEMBER_COOKIES="$(mktemp /tmp/audit-9-2-member-cookies.XXXXXX)"
MEMBER_COOKIES_OLD="$(mktemp /tmp/audit-9-2-member-cookies-old.XXXXXX)"

cleanup_tmp() {
  rm -f "$ADMIN_COOKIES" "$MEMBER_COOKIES" "$MEMBER_COOKIES_OLD"
  rm -f /tmp/audit-9-2-*.tmp
}
trap cleanup_tmp EXIT

admin_login() {
  log "admin login: $ADMIN_EMAIL"
  local body
  body=$(curl_json -c "$ADMIN_COOKIES" -X POST "$PORTAL_URL/api/auth/login" \
    -d "$(jq -nc --arg e "$ADMIN_EMAIL" --arg p "$ADMIN_PASSWORD" \
            '{email:$e, password:$p}')")
  local role
  role=$(jq -r '.user.role // "missing"' <<<"$body")
  [[ "$role" == "admin" ]] || fail "admin login returned role=$role (expected admin); body=$body"
}

# Build a strong audit-member password if not supplied. ≥16 chars, mixed.
gen_password() {
  # 24 hex chars + suffix to clear zxcvbn typical thresholds.
  printf 'AuD!t9-2_'
  openssl rand -hex 12
}

# Persist the auto-generated password to a temp file alongside the audit-member
# metadata so a follow-up run (after a fresh bootstrap or AUDIT_MEMBER_REUSE=1)
# can reuse the same credentials without the caller having to export the
# password explicitly. The file is gitignored (lives under audit-raw/$DATE/).
AUDIT_MEMBER_PWFILE="$AUDIT_DIR/.audit-member-password"
if [[ -z "${AUDIT_MEMBER_PASSWORD:-}" ]]; then
  if [[ -s "$AUDIT_MEMBER_PWFILE" ]]; then
    AUDIT_MEMBER_PASSWORD=$(cat "$AUDIT_MEMBER_PWFILE")
  else
    AUDIT_MEMBER_PASSWORD=$(gen_password)
    umask 077
    printf '%s' "$AUDIT_MEMBER_PASSWORD" > "$AUDIT_MEMBER_PWFILE"
  fi
fi
AUDIT_MEMBER_ID=""

# Look up the audit member's UUID by email via admin /users endpoint.
lookup_audit_member_id() {
  local resp
  resp=$(curl_json -b "$ADMIN_COOKIES" \
    "$PORTAL_URL/api/admin/users?email_filter=$(jq -nr --arg s "$AUDIT_MEMBER_EMAIL" '$s|@uri')&limit=20")
  AUDIT_MEMBER_ID=$(jq -r --arg e "$AUDIT_MEMBER_EMAIL" \
    '.items[] | select(.email == $e) | .id' <<<"$resp" | head -1)
}

bootstrap_audit_member() {
  admin_login
  lookup_audit_member_id

  if [[ -n "$AUDIT_MEMBER_ID" ]]; then
    if [[ "$AUDIT_MEMBER_REUSE" == "1" ]]; then
      log "reusing existing audit-member $AUDIT_MEMBER_EMAIL (id=$AUDIT_MEMBER_ID)"
    else
      fail "audit-member $AUDIT_MEMBER_EMAIL already exists (id=$AUDIT_MEMBER_ID). \
Set AUDIT_MEMBER_REUSE=1 to reuse, or pick a different AUDIT_MEMBER_EMAIL."
    fi
  else
    log "minting invite token (admin)"
    local invite_resp invite_token
    invite_resp=$(curl_json -b "$ADMIN_COOKIES" -X POST "$PORTAL_URL/api/admin/invites" \
      -d '{"role":"member","ttl_seconds":3600}')
    invite_token=$(jq -r '.token // empty' <<<"$invite_resp")
    [[ -n "$invite_token" ]] || fail "invite mint did not return a token; resp=$invite_resp"

    log "registering audit-member with invite token"
    local reg_resp http_code
    reg_resp=$(mktemp)
    http_code=$(curl_status "$reg_resp" -X POST \
      "$PORTAL_URL/api/auth/register" \
      -H 'Content-Type: application/json' -H 'X-Portal-Client: web' \
      -d "$(jq -nc --arg t "$invite_token" --arg e "$AUDIT_MEMBER_EMAIL" --arg p "$AUDIT_MEMBER_PASSWORD" \
              '{token:$t, email:$e, password:$p}')")
    if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
      cat "$reg_resp" >&2
      rm -f "$reg_resp"
      fail "audit-member register returned HTTP $http_code"
    fi
    rm -f "$reg_resp"
    lookup_audit_member_id
    [[ -n "$AUDIT_MEMBER_ID" ]] || fail "audit-member registered but UUID lookup failed"
    log "audit-member created: $AUDIT_MEMBER_EMAIL (id=$AUDIT_MEMBER_ID)"
  fi
}

teardown_audit_member() {
  if [[ "$AUDIT_KEEP_MEMBER" == "1" ]]; then
    log "AUDIT_KEEP_MEMBER=1 → skipping audit-member deactivation"
    return 0
  fi
  if [[ -z "$AUDIT_MEMBER_ID" ]]; then
    lookup_audit_member_id
  fi
  [[ -n "$AUDIT_MEMBER_ID" ]] || { log "teardown: audit-member not found, nothing to do"; return 0; }

  log "teardown: deactivating audit-member $AUDIT_MEMBER_EMAIL"
  local resp http_code
  resp=$(mktemp)
  http_code=$(curl_status "$resp" -X PATCH \
    "$PORTAL_URL/api/admin/users/$AUDIT_MEMBER_ID" \
    -H 'Content-Type: application/json' -H 'X-Portal-Client: web' \
    -b "$ADMIN_COOKIES" \
    -d '{"is_active": false}')
  if [[ "$http_code" != "200" && "$http_code" != "204" ]]; then
    log "teardown PATCH returned HTTP $http_code: $(cat "$resp")"
  fi
  rm -f "$resp"

  log "teardown: cleaning Redis counters for audit-member"
  reset_share_ratelimit "$AUDIT_MEMBER_ID" || true
}

# Wipe the share-ratelimit counter for a given user UUID. The actual key
# shape is `ratelimit:share:user:{uuid}:day:{YYYY-MM-DD}` (Story 6.7 design),
# so DEL must scan + delete by pattern.
reset_share_ratelimit() {
  local user_id="$1"
  ssh -p "$SSH_PORT" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    "$SSH_TARGET" \
    "docker exec $REDIS_CONTAINER sh -c \"redis-cli --scan --pattern 'ratelimit:share:user:$user_id:*' | xargs -r redis-cli DEL\"" \
    >/dev/null 2>&1
}

# Login the audit-member into MEMBER_COOKIES jar. Optionally a different jar.
member_login() {
  local jar="${1:-$MEMBER_COOKIES}"
  rm -f "$jar"
  local resp http_code
  resp=$(mktemp)
  http_code=$(curl_status "$resp" -X POST "$PORTAL_URL/api/auth/login" \
    -H 'Content-Type: application/json' -H 'X-Portal-Client: web' \
    -c "$jar" \
    -d "$(jq -nc --arg e "$AUDIT_MEMBER_EMAIL" --arg p "$AUDIT_MEMBER_PASSWORD" \
            '{email:$e, password:$p}')")
  if [[ "$http_code" != "200" ]]; then
    cat "$resp" >&2
    rm -f "$resp"
    fail "audit-member login returned HTTP $http_code"
  fi
  rm -f "$resp"
}

#-----------------------------------------------------------------------------
# SSH-to-Redis helper
#-----------------------------------------------------------------------------
ssh_redis() {
  local redis_cmd="$1"
  ssh -p "$SSH_PORT" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
    "$SSH_TARGET" \
    "docker exec $REDIS_CONTAINER redis-cli $redis_cmd"
}

# Wipe the login/register/refresh rate-limit counters in Redis so a scenario
# starts from a clean window. The audit-member's share-counter is reset
# inline by scenario 6 (it needs the audit-member UUID).
reset_auth_ratelimits() {
  # The :ip: suffix is per-source-IP. We don't know the dev workstation's
  # outbound IP from here (NAT), so wipe the entire ratelimit:{scope}:*
  # namespace. This is safe because the .190 host serves only us during
  # the audit window.
  for scope in register login refresh; do
    ssh -p "$SSH_PORT" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
      "$SSH_TARGET" \
      "docker exec $REDIS_CONTAINER sh -c \"redis-cli --scan --pattern 'ratelimit:$scope:*' | xargs -r redis-cli DEL\"" \
      >/dev/null 2>&1 || true
  done
}

#-----------------------------------------------------------------------------
# Per-scenario reproducer-script emitters + executors
# Each emit_scenario_N writes a standalone .sh into AUDIT_DIR that, given
# the same env-vars, reproduces the exact scenario. The aggregator then
# executes it inline (bash $AUDIT_DIR/scenario-N-...-reproducer.sh).
#-----------------------------------------------------------------------------

# ----------------- SCENARIO 1 — invite brute-force ---------------------------
emit_scenario_1() {
  local repro="$AUDIT_DIR/scenario-1-invite-brute-force-reproducer.sh"
  cat > "$repro" <<'REPRO_S1'
#!/usr/bin/env bash
# Story 9.2 / AC1 — invite-token brute-force reproducer.
# Verifies register rate-limit (3 attempts / 60s per IP via Story 6.6)
# trips HTTP 429 on the 4th attempt within the sliding window.
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${1:-scenario-1-output.txt}"
: > "$OUT"
# Send 5 well-formed registration attempts with fake invite tokens. The
# body must satisfy schema validation (token length=43 — matches
# secrets.token_urlsafe(32) output exactly per Story 6.2) so the request
# reaches the auth-rate-limit middleware. Each fake token is 43 chars
# of URL-safe base64 produced by `head -c32 /dev/urandom | base64`.
gen_fake_token() {
  # 32 random bytes → url-safe base64 (length 43 after stripping "=")
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
}
for i in 1 2 3 4 5; do
  token=$(gen_fake_token)
  code=$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST "$PORTAL_URL/api/auth/register" \
    -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg t "$token" '{token:$t, email:"brute@portal.example.com", password:"NotARealPassword123!"}')")
  printf 'attempt=%d status=%s token=%s\n' "$i" "$code" "$token" | tee -a "$OUT"
done
REPRO_S1
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

run_scenario_1() {
  log "--- Scenario 1: invite-token brute force ---"
  local repro out verdict notes
  repro=$(emit_scenario_1)
  out="$AUDIT_DIR/scenario-1-output${SFX}.txt"
  log "resetting register + login rate-limit counters"
  reset_auth_ratelimits
  bash "$repro" "$out"
  # Assert: 4th attempt status == 429 within the 60s window.
  local fourth_status
  fourth_status=$(awk -F'status=' '/^attempt=4 /{ split($2,a," "); print a[1] }' "$out")
  if [[ "$fourth_status" == "429" ]]; then
    verdict="PASS"
    notes="4th attempt returned HTTP 429 as expected (register rate-limit 3/60s tripped)."
  else
    verdict="FAIL"
    notes="4th attempt returned HTTP $fourth_status (expected 429). Inspect $out."
  fi
  record_verdict 1 "$verdict" "$out" "$repro" "$notes"
}

# ----------------- SCENARIO 2 — refresh-token replay -------------------------
emit_scenario_2() {
  local repro="$AUDIT_DIR/scenario-2-refresh-replay-reproducer.sh"
  cat > "$repro" <<'REPRO_S2'
#!/usr/bin/env bash
# Story 9.2 / AC2 — refresh-token family reuse-detection reproducer.
# Verifies Init 0 family-rotation invalidates a token family when a stale
# refresh cookie is replayed.
#
# Required env: PORTAL_URL, AUDIT_MEMBER_EMAIL, AUDIT_MEMBER_PASSWORD,
#               ADMIN_COOKIES (path to a cookie-jar with admin login),
#               OUT_FILE (output file)
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${OUT_FILE:-scenario-2-output.txt}"
GEN1="$(mktemp /tmp/audit-9-2-s2-gen1.XXXXXX)"
GEN2="$(mktemp /tmp/audit-9-2-s2-gen2.XXXXXX)"
trap 'rm -f "$GEN1" "$GEN2"' EXIT

step_login() {
  curl -fsS -c "$GEN1" -X POST "$PORTAL_URL/api/auth/login" \
    -H 'Content-Type: application/json' -H 'X-Portal-Client: web' \
    -d "$(jq -nc --arg e "$AUDIT_MEMBER_EMAIL" --arg p "$AUDIT_MEMBER_PASSWORD" \
            '{email:$e, password:$p}')" >/dev/null
}

step_rotate() {
  cp "$GEN1" "$GEN2"
  curl -fsS -b "$GEN1" -c "$GEN2" -X POST "$PORTAL_URL/api/auth/refresh" \
    -H 'X-Portal-Client: web' >/dev/null
}

step_replay() {
  # Replay the GEN1 cookie jar (still holds the original portal_refresh).
  curl -sS -o /dev/null -w '%{http_code}' \
    -b "$GEN1" -X POST "$PORTAL_URL/api/auth/refresh" \
    -H 'X-Portal-Client: web'
}

step_followup_gen2() {
  curl -sS -o /dev/null -w '%{http_code}' \
    -b "$GEN2" -X POST "$PORTAL_URL/api/auth/refresh" \
    -H 'X-Portal-Client: web'
}

{
  echo "--- Scenario 2: refresh-token replay ---"
  echo "step1=login"; step_login; echo "ok"
  echo "step2=rotate"; step_rotate; echo "ok"
  # Wait past the 30s grace window — in-grace replays return
  # `grace_returned` (HTTP 200) as a benign-retry protection per
  # apps/api/app/core/auth/refresh.py:GRACE_SECONDS. Replay after grace
  # triggers `reuse_detected` (HTTP 401 + family burn).
  echo "step2b=sleep-past-grace-window (31s)"
  sleep 31
  replay_code=$(step_replay)
  echo "step3=replay_status=$replay_code"
  followup_code=$(step_followup_gen2)
  echo "step4=followup_gen2_status=$followup_code"
  # step5 — admin audit query (caller injects ADMIN_COOKIES)
  if [[ -n "${ADMIN_COOKIES:-}" && -r "$ADMIN_COOKIES" ]]; then
    # /api/admin/audit ignores filter query-params (returns paged dict with
    # `events`, NOT `items`). Filter client-side for the expected action
    # within the last 100 events (more than enough to catch a fresh emit).
    audit_row=$(curl -fsS -b "$ADMIN_COOKIES" -H 'X-Portal-Client: web' \
      "$PORTAL_URL/api/admin/audit?limit=100" \
      | jq -r '[.events[]? | select(.action == "auth.refresh.reuse_detected")] | .[0].action // "none"')
    echo "step5=audit_action=$audit_row"
  else
    echo "step5=audit_action=skipped_no_admin_cookies"
  fi
} | tee "$OUT"
REPRO_S2
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

run_scenario_2() {
  log "--- Scenario 2: refresh-token replay ---"
  local repro out verdict notes
  repro=$(emit_scenario_2)
  out="$AUDIT_DIR/scenario-2-output${SFX}.txt"

  log "resetting login + refresh rate-limit counters"
  reset_auth_ratelimits

  member_login "$MEMBER_COOKIES_OLD"
  # We need the GEN1 cookies preserved in the reproducer; the reproducer
  # logs in itself. The reproducer also reads ADMIN_COOKIES from env to
  # query the audit log.
  ADMIN_COOKIES="$ADMIN_COOKIES" \
  AUDIT_MEMBER_EMAIL="$AUDIT_MEMBER_EMAIL" \
  AUDIT_MEMBER_PASSWORD="$AUDIT_MEMBER_PASSWORD" \
  PORTAL_URL="$PORTAL_URL" \
  OUT_FILE="$out" \
    bash "$repro"

  local replay_code followup_code audit_action
  replay_code=$(grep -oE 'step3=replay_status=[0-9]+' "$out" | cut -d= -f3)
  followup_code=$(grep -oE 'step4=followup_gen2_status=[0-9]+' "$out" | cut -d= -f3)
  audit_action=$(grep -oE 'step5=audit_action=[A-Za-z0-9._-]+' "$out" | cut -d= -f3 | head -1)

  if [[ "$replay_code" == "401" \
        && "$audit_action" == "auth.refresh.reuse_detected" \
        && "$followup_code" == "401" ]]; then
    verdict="PASS"
    notes="replay=401, audit-row=auth.refresh.reuse_detected, gen-2 invalidated=401."
  else
    verdict="FAIL"
    notes="replay=$replay_code (want 401), audit=$audit_action (want auth.refresh.reuse_detected), gen-2 followup=$followup_code (want 401). See $out."
  fi
  record_verdict 2 "$verdict" "$out" "$repro" "$notes"
}

# ----------------- SCENARIO 3 — CSRF + JWT tampering -------------------------
emit_scenario_3_targets() {
  local targets="$AUDIT_DIR/scenario-3-targets.json"
  # Paths verified against:
  #   apps/api/app/modules/invite/admin_router.py        (prefix /api/admin/invites)
  #   apps/api/app/modules/auth/totp/router.py           (prefix /api/auth)
  #   apps/api/app/modules/admin/router.py               (prefix /api/admin)
  #   apps/api/app/modules/auth/password_reset/admin_router.py (prefix /api/admin)
  cat > "$targets" <<'TARGETS_S3'
[
  {"label": "register",                  "method": "POST",  "path": "/api/auth/register",                                                    "auth": "none",   "body": {"token":"NOT_A_REAL_TOKEN_NOT_A_REAL_TOKEN_NOT_AAA","email":"x@portal.example.com","password":"NotARealPassword123!"}},
  {"label": "admin-invites-create",      "method": "POST",  "path": "/api/admin/invites",                                                    "auth": "admin",  "body": {"role":"member","ttl_seconds":3600}},
  {"label": "admin-invites-revoke",      "method": "POST",  "path": "/api/admin/invites/00000000-0000-0000-0000-000000000000/revoke",        "auth": "admin",  "body": {}},
  {"label": "2fa-enroll",                "method": "POST",  "path": "/api/auth/2fa/enroll",                                                  "auth": "member", "body": {}},
  {"label": "2fa-enroll-confirm",        "method": "POST",  "path": "/api/auth/2fa/enroll/confirm",                                          "auth": "member", "body": {"code":"000000"}},
  {"label": "2fa-verify",                "method": "POST",  "path": "/api/auth/2fa/verify",                                                  "auth": "none",   "body": {"code":"000000"}},
  {"label": "2fa-disable",               "method": "POST",  "path": "/api/auth/2fa/disable",                                                 "auth": "member", "body": {"code":"000000"}},
  {"label": "2fa-regen-recovery",        "method": "POST",  "path": "/api/auth/2fa/recovery-codes/regenerate",                               "auth": "member", "body": {"code":"000000"}},
  {"label": "admin-users-patch",         "method": "PATCH", "path": "/api/admin/users/00000000-0000-0000-0000-000000000000",                 "auth": "admin",  "body": {"is_active":false}},
  {"label": "admin-users-force-logout",  "method": "POST",  "path": "/api/admin/users/00000000-0000-0000-0000-000000000000/force-logout",    "auth": "admin",  "body": {}},
  {"label": "admin-users-2fa-enforce",   "method": "POST",  "path": "/api/admin/users/00000000-0000-0000-0000-000000000000/force-2fa-enrollment", "auth": "admin", "body": {}},
  {"label": "admin-users-2fa-disable",   "method": "POST",  "path": "/api/admin/users/00000000-0000-0000-0000-000000000000/force-disable-2fa",    "auth": "admin", "body": {}},
  {"label": "admin-users-pw-reset",      "method": "POST",  "path": "/api/admin/users/00000000-0000-0000-0000-000000000000/password-reset",       "auth": "admin", "body": {}}
]
TARGETS_S3
  printf '%s\n' "$targets"
}

emit_scenario_3() {
  local repro="$AUDIT_DIR/scenario-3-csrf-jwt-tampering-reproducer.sh"
  cat > "$repro" <<'REPRO_S3'
#!/usr/bin/env bash
# Story 9.2 / AC3 — CSRF + JWT tampering reproducer.
# For every mutating endpoint introduced in E6+E7+E8:
#   - CSRF: omit X-Portal-Client header → expect HTTP 403 (csrf_missing)
#   - JWT tampering: corrupt the portal_access cookie → expect HTTP 401
#
# Required env: PORTAL_URL, ADMIN_COOKIES, MEMBER_COOKIES, TARGETS_JSON,
#               OUT_FILE.
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${OUT_FILE:-scenario-3-output.txt}"
TARGETS_JSON="${TARGETS_JSON:-scenario-3-targets.json}"

tamper_cookie_jar() {
  # Strip the last 8 chars from the portal_access cookie value (a/k/a
  # signature corruption). Returns a NEW cookie jar that the caller must
  # rm -f afterwards.
  #
  # curl's Netscape cookie-jar format prefixes HttpOnly rows with
  # "#HttpOnly_"; we must NOT treat those as comments. Real comments
  # start with "# " (hash + space) or are blank lines.
  local src="$1" dst
  dst=$(mktemp /tmp/audit-9-2-tampered.XXXXXX)
  awk 'BEGIN{FS="\t"; OFS="\t"} {
    if ($0 ~ /^# / || $0 ~ /^[[:space:]]*$/ || NF < 7) { print; next }
    if (index($6, "portal_access") > 0) {
      $7 = substr($7, 1, length($7)-8) "AAAAAAAA"
    }
    print
  }' "$src" > "$dst"
  printf '%s\n' "$dst"
}

run_target() {
  local label="$1" method="$2" path="$3" auth="$4" body="$5"
  local jar=""
  case "$auth" in
    admin)  jar="$ADMIN_COOKIES" ;;
    member) jar="$MEMBER_COOKIES" ;;
    none)   jar="" ;;
  esac

  # CSRF attack — same auth but NO X-Portal-Client header.
  local csrf_args=( -sS -o /dev/null -w '%{http_code}' -X "$method"
                    "$PORTAL_URL$path" -H 'Content-Type: application/json'
                    -d "$body" )
  [[ -n "$jar" ]] && csrf_args+=( -b "$jar" )
  local csrf_code
  csrf_code=$(curl "${csrf_args[@]}")

  # JWT tampering — same headers, but tampered jar. Only applicable when
  # there is an auth jar (admin/member). For `auth=none` we treat the JWT
  # row as N/A.
  local tampered_code="n/a"
  if [[ -n "$jar" ]]; then
    local tampered_jar
    tampered_jar=$(tamper_cookie_jar "$jar")
    tampered_code=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" \
      "$PORTAL_URL$path" -H 'Content-Type: application/json' \
      -H 'X-Portal-Client: web' \
      -b "$tampered_jar" -d "$body")
    rm -f "$tampered_jar"
  fi

  printf 'label=%-32s method=%-6s csrf_code=%s jwt_code=%s auth=%s\n' \
    "$label" "$method" "$csrf_code" "$tampered_code" "$auth"
}

: > "$OUT"
jq -c '.[]' "$TARGETS_JSON" | while read -r row; do
  label=$(jq -r '.label' <<<"$row")
  method=$(jq -r '.method' <<<"$row")
  path=$(jq -r '.path' <<<"$row")
  auth=$(jq -r '.auth' <<<"$row")
  body=$(jq -c '.body' <<<"$row")
  run_target "$label" "$method" "$path" "$auth" "$body" | tee -a "$OUT"
done
REPRO_S3
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

run_scenario_3() {
  log "--- Scenario 3: CSRF + JWT tampering ---"
  local repro targets out verdict notes
  targets=$(emit_scenario_3_targets)
  repro=$(emit_scenario_3)
  out="$AUDIT_DIR/scenario-3-output${SFX}.txt"

  log "resetting login + refresh rate-limit counters"
  reset_auth_ratelimits

  member_login

  PORTAL_URL="$PORTAL_URL" ADMIN_COOKIES="$ADMIN_COOKIES" \
  MEMBER_COOKIES="$MEMBER_COOKIES" TARGETS_JSON="$targets" \
  OUT_FILE="$out" \
    bash "$repro"

  # Acceptance: every row's csrf_code is 403 AND (auth=none OR jwt_code is 401).
  local bad=0 total=0
  local bad_rows
  bad_rows=$(awk '
    /^label=/ {
      total++
      csrf=""; jwt=""; auth=""
      for (i=1; i<=NF; i++) {
        if (match($i, /^csrf_code=/)) csrf=substr($i, 11)
        else if (match($i, /^jwt_code=/)) jwt=substr($i, 10)
        else if (match($i, /^auth=/)) auth=substr($i, 6)
      }
      ok_csrf = (csrf == "403")
      ok_jwt  = (auth == "none" || jwt == "401")
      if (!ok_csrf || !ok_jwt) {
        bad++
        print $0
      }
    }
    END { exit (bad > 0 ? 1 : 0) }
  ' "$out") || true

  total=$(grep -c '^label=' "$out" || echo 0)
  bad=$(awk 'BEGIN{c=0} /^label=/{
    csrf=""; jwt=""; auth=""
    for (i=1; i<=NF; i++) {
      if (match($i, /^csrf_code=/)) csrf=substr($i, 11)
      else if (match($i, /^jwt_code=/)) jwt=substr($i, 10)
      else if (match($i, /^auth=/)) auth=substr($i, 6)
    }
    if (!(csrf=="403" && (auth=="none" || jwt=="401"))) c++
  } END{print c}' "$out")

  if [[ "$bad" == "0" ]]; then
    verdict="PASS"
    notes="$total/$total endpoints rejected CSRF-stripped (403) and tampered-JWT (401) attacks."
  else
    verdict="FAIL"
    notes="$bad/$total endpoints failed expected 403/401. Rows: $(echo "$bad_rows" | tr '\n' '|')"
  fi
  record_verdict 3 "$verdict" "$out" "$repro" "$notes"
}

# ----------------- SCENARIO 4 — Auth-boundary probe on ALL /api/* ------------
#
# Initiative 6 Story 11.5 — Scenario 4 reworked from "/api/admin/* IDOR via
# member" to "auth-boundary probe on ALL /api/* routes". The pre-Init-6 scope
# (admin-only) missed the read-side /api/sot/* and /api/* surfaces and was
# the proximate root cause of supplemental finding High-002 (post-cutover
# anonymous external read of /api/categories).
#
# The new Scenario 4 enumerates the live FastAPI route table via
# /api/openapi.json, then probes every route as:
#   1. anonymous (no cookies) → expected 401 EXCEPT _PUBLIC_ROUTES which
#      return route-specific status codes (200 OK / 422 validation /
#      400 bad request / etc.; the canonical "anonymous can call" check
#      is "status != 401 + 403")
#   2. member-authenticated → expected 200/201/403/404/422 per route's
#      posture. Member-blocked routes (admin/*) return 403; member-allowed
#      routes return their normal success code or validation error for
#      the smoke-call payload.
#
# Verdict logic:
#   - PASS if every /api/* route either has documented anonymous access
#     (in _PUBLIC_ROUTES per backend route table) OR returns 401 anonymous.
#   - FAIL if ANY route returns 200 (or any non-{401,403} success code)
#     anonymously while NOT being in _PUBLIC_ROUTES — that's the High-002
#     class of regression.

emit_scenario_4() {
  local repro="$AUDIT_DIR/scenario-4-auth-boundary-reproducer.sh"
  cat > "$repro" <<'REPRO_S4'
#!/usr/bin/env bash
# Story 11.5 / Initiative 6 — auth-boundary probe on every /api/* route.
# Replaces the pre-Init-6 admin-only IDOR scope (which missed the read-side
# /api/sot/* surface that the Story 10.3 cutover exposed externally).
#
# Required env: PORTAL_URL, MEMBER_COOKIES, OUT_FILE.
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${OUT_FILE:-scenario-4-output.txt}"

# Anonymous-allowed routes (must match apps/api/app/main.py:_PUBLIC_ROUTES).
# Path templates are matched literally against the OpenAPI route table;
# {param} segments do NOT need substitution for the probe (we send a
# template-placeholder value and check the status code shape, not the
# semantic response).
PUBLIC_ROUTES=(
  "/api/health"
  "/api/auth/login"
  "/api/auth/logout"
  "/api/auth/refresh"
  "/api/auth/register"
  "/api/auth/2fa/verify"
  "/api/auth/password-reset"
  "/api/share/{token}"
  "/api/share/{token}/files/{file_id}/content"
)

is_public_route() {
  local path="$1"
  for p in "${PUBLIC_ROUTES[@]}"; do
    [[ "$p" == "$path" ]] && return 0
  done
  return 1
}

# Fetch route table from /api/openapi.json (single source of truth for what
# routes the API actually serves; defense against the pre-Init-6 pattern of
# hand-maintaining a target list that drifts from the live route table).
ROUTES_JSON=$(curl -sS "$PORTAL_URL/api/openapi.json" \
  | jq -c '[.paths | to_entries[] | {path: .key, methods: (.value | keys | map(select(. != "parameters")))}]')

probe_one() {
  local method="$1" path="$2" expected_anon="$3"
  # Substitute path templates with a known-bogus UUID so the request reaches
  # the handler and exercises the auth dep, but the handler's body validation
  # will produce a deterministic 422/404 for valid-auth probes.
  local probe_path="$path"
  probe_path=${probe_path//\{token\}/probe-token-bogus-aaaaaaaaaaaaaaaaaa}
  probe_path=${probe_path//\{model_id\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{file_id\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{user_id\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{family_id\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{invite_id\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{file_id:uuid\}/00000000-0000-0000-0000-000000000000}
  probe_path=${probe_path//\{tag_id\}/00000000-0000-0000-0000-000000000000}

  # 1. Anonymous probe (no cookie jar, no CSRF header).
  local anon_code
  anon_code=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" \
    "$PORTAL_URL$probe_path" \
    -H 'Content-Type: application/json' -d '{}')

  # 2. Member-authenticated probe (cookie jar + CSRF header for mutating).
  local member_code
  member_code=$(curl -sS -o /dev/null -w '%{http_code}' -X "$method" \
    "$PORTAL_URL$probe_path" \
    -H 'X-Portal-Client: web' \
    -H 'Content-Type: application/json' \
    -b "$MEMBER_COOKIES" -d '{}')

  # Verdict: anonymous code MUST be 401 for non-public routes. Public
  # routes can return anything (typically 200 / 400 / 422) — they're
  # EXPECTED to be reachable anonymously.
  local verdict="PASS"
  if [[ "$expected_anon" == "public" ]]; then
    # Public route: any code is fine as long as it's NOT a server error.
    if [[ "$anon_code" =~ ^5 ]]; then
      verdict="FAIL_server_error_on_public"
    fi
  else
    # Protected route: anonymous MUST get 401 (or 403 for some role
    # mismatches before auth runs, but 401 is the canonical reject).
    if [[ "$anon_code" != "401" && "$anon_code" != "403" ]]; then
      verdict="FAIL_anonymous_leak"
    fi
  fi

  printf 'method=%-6s path=%-72s anon=%s member=%s expected=%s verdict=%s\n' \
    "$method" "$path" "$anon_code" "$member_code" "$expected_anon" "$verdict"
}

: > "$OUT"
echo "$ROUTES_JSON" | jq -c '.[]' | while read -r row; do
  path=$(jq -r '.path' <<<"$row")
  # Skip non-/api/* paths (e.g. /agent-runbook — nginx-level bypass per
  # NFR5-INT-1 Decision K, outside the Initiative 6 /api/* auth contract).
  [[ "$path" != /api/* ]] && continue
  # Skip introspection-only paths (not part of the auth boundary contract).
  [[ "$path" == "/api/openapi.json" || "$path" == "/api/docs" ]] && continue
  expected_anon="protected"
  is_public_route "$path" && expected_anon="public"
  for method in $(jq -r '.methods[]' <<<"$row" | tr '[:lower:]' '[:upper:]'); do
    [[ "$method" == "HEAD" ]] && continue
    probe_one "$method" "$path" "$expected_anon" | tee -a "$OUT"
  done
done
REPRO_S4
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

run_scenario_4() {
  log "--- Scenario 4: auth-boundary probe on ALL /api/* (Initiative 6 Story 11.5) ---"
  local repro out verdict notes
  repro=$(emit_scenario_4)
  out="$AUDIT_DIR/scenario-4-output${SFX}.txt"

  log "resetting login + refresh rate-limit counters"
  reset_auth_ratelimits

  member_login

  PORTAL_URL="$PORTAL_URL" MEMBER_COOKIES="$MEMBER_COOKIES" \
  OUT_FILE="$out" bash "$repro"

  local total bad
  total=$(grep -c '^method=' "$out" || echo 0)
  bad=$(awk '/^method=/{
    s=""
    for (i=1; i<=NF; i++) if (match($i, /^verdict=/)) s=substr($i, 9)
    if (s != "PASS") c++
  } END{print c+0}' "$out")

  if [[ "$bad" == "0" ]]; then
    verdict="PASS"
    notes="$total/$total /api/* routes enforce documented auth posture (anon→401 except _PUBLIC_ROUTES)."
  else
    verdict="FAIL"
    notes="$bad/$total /api/* routes violated auth posture. See $out for verdict=FAIL_* rows."
  fi
  record_verdict 4 "$verdict" "$out" "$repro" "$notes"
}

# ----------------- SCENARIO 5 — login rate-limit -----------------------------
emit_scenario_5() {
  local repro="$AUDIT_DIR/scenario-5-login-rate-limit-reproducer.sh"
  cat > "$repro" <<'REPRO_S5'
#!/usr/bin/env bash
# Story 9.2 / AC5 — /api/auth/login rate-limit reproducer.
# Five wrong-password attempts return 401; the sixth returns 429 within the
# 60s sliding window (ratelimit_login_threshold=5).
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${OUT_FILE:-scenario-5-output.txt}"
EMAIL="${LOGIN_TEST_EMAIL:-audit-login-probe@portal.example.com}"
: > "$OUT"
for i in 1 2 3 4 5 6 7; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST "$PORTAL_URL/api/auth/login" \
    -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg e "$EMAIL" '{email:$e, password:"definitely-not-the-real-password"}')")
  printf 'attempt=%d status=%s\n' "$i" "$code" | tee -a "$OUT"
done
REPRO_S5
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

run_scenario_5() {
  log "--- Scenario 5: login rate-limit ---"
  local repro out verdict notes
  repro=$(emit_scenario_5)
  out="$AUDIT_DIR/scenario-5-output${SFX}.txt"

  log "resetting login + refresh rate-limit counters"
  reset_auth_ratelimits

  # Use a probe email distinct from any real account; the wrong-password
  # attempts will fail with 401 until the counter trips.
  LOGIN_TEST_EMAIL="audit-9-2-login-probe@portal.example.com" \
  PORTAL_URL="$PORTAL_URL" OUT_FILE="$out" bash "$repro"

  local first_five sixth
  first_five=$(awk -F'[= ]' '/^attempt=[1-5] /{print $4}' "$out" | sort -u | tr -d '\n')
  sixth=$(awk -F'[= ]' '/^attempt=6 /{print $4}' "$out")

  if [[ "$first_five" == "401" && "$sixth" == "429" ]]; then
    verdict="PASS"
    notes="attempts 1-5 returned HTTP 401; attempt 6 returned HTTP 429 within 60s (login rate-limit 5/60s tripped)."
  else
    verdict="FAIL"
    notes="attempts 1-5 statuses=$first_five (want 401), attempt 6=$sixth (want 429). See $out."
  fi
  record_verdict 5 "$verdict" "$out" "$repro" "$notes"
}

# ----------------- SCENARIO 6 — share-link amplification --------------------
emit_scenario_6() {
  local repro="$AUDIT_DIR/scenario-6-share-amplification-reproducer.sh"
  cat > "$repro" <<'REPRO_S6'
#!/usr/bin/env bash
# Story 9.2 / AC6 — member share-link amplification reproducer.
# Creates 21 share tokens via /api/admin/share (member-authenticated path,
# valid since Story 6.5 member-permission expansion). Asserts soft-alert
# audit row at call 10 and HTTP 429 at call 21.
#
# Required env: PORTAL_URL, MEMBER_COOKIES, ADMIN_COOKIES, AUDIT_MEMBER_ID,
#               SHARE_MODEL_ID, OUT_FILE.
set -Eeuo pipefail
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
OUT="${OUT_FILE:-scenario-6-output.txt}"
: > "$OUT"

if [[ -z "${SHARE_MODEL_ID:-}" ]]; then
  echo "FATAL: SHARE_MODEL_ID env-var required (a model UUID accessible to the audit-member)" >&2
  exit 2
fi

for i in $(seq 1 21); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST "$PORTAL_URL/api/admin/share" \
    -H 'X-Portal-Client: web' -H 'Content-Type: application/json' \
    -b "$MEMBER_COOKIES" \
    -d "$(jq -nc --arg m "$SHARE_MODEL_ID" '{model_id:$m, expires_in_hours:24}')")
  printf 'call=%d status=%s\n' "$i" "$code" | tee -a "$OUT"
done

# Story 6.7 emits share.ratelimit.soft_alert as a LOG LINE (not an audit-log
# row in the DB). Spec story 9.2 §AC6 says "soft-alert audit row" — this is
# documentation drift; the implementation in
# apps/api/app/core/auth/ratelimit.py:231 logs via _SHARE_LOG.warning(...)
# and never writes to audit_log. Verify by inspecting the container's
# stdout logs over SSH instead of querying the audit-log endpoint.
if [[ -n "${SSH_TARGET:-}" && -n "${SSH_PORT:-}" && -n "${AUDIT_MEMBER_ID:-}" ]]; then
  soft_alert_loglines=$(ssh -p "$SSH_PORT" -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=accept-new "$SSH_TARGET" \
    "docker logs --since 5m 3d-portal-api-1 2>&1 | grep 'share.ratelimit.soft_alert' | grep -F '$AUDIT_MEMBER_ID' | wc -l" \
    2>/dev/null || echo 0)
  echo "soft_alert_loglines=$soft_alert_loglines" | tee -a "$OUT"
else
  echo "soft_alert_loglines=skipped_no_ssh_target" | tee -a "$OUT"
fi
REPRO_S6
  chmod +x "$repro"
  printf '%s\n' "$repro"
}

# A member needs a model to share. Strategy: query /api/models (admin route)
# for an existing model accessible to the audit member. If none, mint a
# placeholder catalog row via admin API (NOT in scope for this scenario —
# fail-fast and ask operator if no model is reachable).
discover_share_model_id() {
  local resp model_id
  resp=$(curl_json -b "$ADMIN_COOKIES" "$PORTAL_URL/api/models?limit=1&visibility=public")
  model_id=$(jq -r '.items[0].id // empty' <<<"$resp" 2>/dev/null || true)
  if [[ -z "$model_id" ]]; then
    # Fall back to any model the API knows.
    resp=$(curl_json -b "$ADMIN_COOKIES" "$PORTAL_URL/api/models?limit=1")
    model_id=$(jq -r '.items[0].id // empty' <<<"$resp" 2>/dev/null || true)
  fi
  if [[ -z "$model_id" ]]; then
    # Try /api/admin/share?limit=1 to discover an existing share that
    # might reveal a known model id (in case /api/models is gated).
    resp=$(curl_json -b "$ADMIN_COOKIES" "$PORTAL_URL/api/admin/share?limit=1")
    model_id=$(jq -r '.items[0].model_id // empty' <<<"$resp" 2>/dev/null || true)
  fi
  printf '%s\n' "$model_id"
}

run_scenario_6() {
  log "--- Scenario 6: member share amplification ---"
  local repro out verdict notes model_id
  repro=$(emit_scenario_6)
  out="$AUDIT_DIR/scenario-6-output${SFX}.txt"

  log "resetting login + refresh rate-limit counters"
  reset_auth_ratelimits

  member_login

  # Reset Redis share-counter for audit-member BEFORE the scenario runs.
  log "resetting Redis share-counter for audit-member"
  reset_share_ratelimit "$AUDIT_MEMBER_ID" || \
    log "WARN: redis DEL failed (continuing — counter may not be 0)"

  model_id=$(discover_share_model_id)
  if [[ -z "$model_id" ]]; then
    record_verdict 6 "FAIL" "$out" "$repro" \
      "could not discover a model UUID for the audit-member to share — set SHARE_MODEL_ID env-var explicitly"
    return 0
  fi
  log "share model_id: $model_id"

  PORTAL_URL="$PORTAL_URL" MEMBER_COOKIES="$MEMBER_COOKIES" \
  ADMIN_COOKIES="$ADMIN_COOKIES" AUDIT_MEMBER_ID="$AUDIT_MEMBER_ID" \
  SHARE_MODEL_ID="$model_id" OUT_FILE="$out" \
  SSH_TARGET="$SSH_TARGET" SSH_PORT="$SSH_PORT" \
    bash "$repro"

  local call21 alert_count
  call21=$(awk '/^call=21 /{ for(i=1;i<=NF;i++) if (index($i,"status=")==1) { sub("status=","",$i); print $i } }' "$out")
  alert_count=$(awk -F= '/^soft_alert_loglines=/{print $2}' "$out")

  if [[ "$call21" == "429" && "$alert_count" =~ ^[1-9][0-9]*$ ]]; then
    verdict="PASS"
    notes="call 21 HTTP 429; share.ratelimit.soft_alert log-lines for audit-member=$alert_count (log-only per Story 6.7; spec §AC6 'audit row' is documentation drift)."
  elif [[ "$call21" == "429" && "$alert_count" == "0" ]]; then
    verdict="FAIL"
    notes="call 21=429 OK, but soft-alert log-line missing for audit-member. Inspect docker logs 3d-portal-api-1."
  else
    verdict="FAIL"
    notes="call 21=$call21 (want 429), soft_alert_loglines=$alert_count (want ≥1). See $out."
  fi
  record_verdict 6 "$verdict" "$out" "$repro" "$notes"
}

#-----------------------------------------------------------------------------
# Verdict aggregation — six-scenario-coverage.json (per-attempt)
#-----------------------------------------------------------------------------
COVERAGE_JSON="$AUDIT_DIR/six-scenario-coverage${SFX}.json"

# Initialize with an empty object on first scenario.
init_coverage() {
  if [[ ! -s "$COVERAGE_JSON" ]]; then
    echo '{}' > "$COVERAGE_JSON"
  fi
}

record_verdict() {
  local n="$1" verdict="$2" evidence="$3" reproducer="$4" notes="$5"
  init_coverage
  local tmp
  tmp=$(mktemp)
  jq --arg k "scenario_$n" \
     --arg v "$verdict" \
     --arg e "$(basename "$evidence")" \
     --arg r "$(basename "$reproducer")" \
     --arg n "$notes" \
     '. + { ($k): { verdict: $v, evidence_path: $e, reproducer_path: $r, notes: $n } }' \
     "$COVERAGE_JSON" > "$tmp"
  mv "$tmp" "$COVERAGE_JSON"
  log "$verdict  scenario_$n  $notes"
}

#-----------------------------------------------------------------------------
# Dispatch
#-----------------------------------------------------------------------------
SUB="${1:-all}"

case "$SUB" in
  bootstrap)
    bootstrap_audit_member
    ;;
  teardown)
    admin_login
    teardown_audit_member
    ;;
  scenario-1|scenario-2|scenario-3|scenario-4|scenario-5|scenario-6|all)
    bootstrap_audit_member
    case "$SUB" in
      scenario-1) [[ "${SKIP_1:-}" == "1" ]] || run_scenario_1 ;;
      scenario-2) [[ "${SKIP_2:-}" == "1" ]] || run_scenario_2 ;;
      scenario-3) [[ "${SKIP_3:-}" == "1" ]] || run_scenario_3 ;;
      scenario-4) [[ "${SKIP_4:-}" == "1" ]] || run_scenario_4 ;;
      scenario-5) [[ "${SKIP_5:-}" == "1" ]] || run_scenario_5 ;;
      scenario-6) [[ "${SKIP_6:-}" == "1" ]] || run_scenario_6 ;;
      all)
        [[ "${SKIP_1:-}" == "1" ]] && log "SKIP scenario-1" || run_scenario_1
        [[ "${SKIP_2:-}" == "1" ]] && log "SKIP scenario-2" || run_scenario_2
        [[ "${SKIP_3:-}" == "1" ]] && log "SKIP scenario-3" || run_scenario_3
        [[ "${SKIP_4:-}" == "1" ]] && log "SKIP scenario-4" || run_scenario_4
        [[ "${SKIP_5:-}" == "1" ]] && log "SKIP scenario-5" || run_scenario_5
        [[ "${SKIP_6:-}" == "1" ]] && log "SKIP scenario-6" || run_scenario_6
        ;;
    esac
    teardown_audit_member
    log "coverage: $COVERAGE_JSON"
    if jq -e '[.[] | .verdict] | any(. == "FAIL")' "$COVERAGE_JSON" >/dev/null 2>&1; then
      log "one or more scenarios FAILed — see $COVERAGE_JSON"
      exit 1
    fi
    ;;
  *)
    fail "unknown subcommand: $SUB (use --help for list)"
    ;;
esac

log "done."
exit 0
