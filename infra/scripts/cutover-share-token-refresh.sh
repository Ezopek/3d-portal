#!/usr/bin/env bash
# Hourly cron: rotate CUTOVER_TEST_SHARE_TOKEN in infra/.env so Scenario 1
# of `cutover-smoke.sh` (share bypass) keeps PASSing through the cutover
# window. Story 10.1 AC4.
#
# Why this script exists: share tokens expire (default 72h via Story 6.x);
# we cannot rely on a single token to survive the multi-day pre-cutover
# fixture-seeding window + cutover-day window + post-cutover review window.
# A cheap hourly cron keeps a fresh token at all times. The smoke script
# re-sources infra/.env on every invocation, so the next smoke run picks
# up the new token transparently.
#
# Refresh strategy:
#   1. Login as the test-member (CUTOVER_TEST_MEMBER_EMAIL).
#   2. POST /api/admin/share with model_id=CUTOVER_TEST_MODEL_ID → new token
#      (member can create — admin_router uses current_member_or_admin guard).
#   3. Atomic rewrite of infra/.env via a sibling tempfile + mv (preserves
#      file mode + survives concurrent reads from cutover-smoke.sh).
#   4. Old token is left to age out naturally — DELETE /api/admin/share/{token}
#      requires admin scope, which the test-member does NOT have. Tokens
#      auto-expire per `expires_in_hours` so leakage is bounded.
#
# Required env (sourced from infra/.env):
#   CUTOVER_TEST_MEMBER_EMAIL     test-member account
#   CUTOVER_TEST_MEMBER_PASSWORD  test-member password
#   CUTOVER_TEST_MODEL_ID         model UUID owned by test-member (Story 10.1 T5)
#
# Optional env (overrideable):
#   PORTAL_URL                  default https://3d.ezop.ddns.net
#   CUTOVER_SHARE_TTL_HOURS     default 24 (cron runs hourly → 24h gives 24×
#                               redundancy; tradeoff: larger leaked-token
#                               blast radius vs. resilience to cron skip)
#   CUTOVER_REFRESH_LOG_FILE    default /var/log/3d-portal-cutover-share-refresh.log
#                               (falls back to stderr if not writable)
#
# Exit codes:
#   0  fresh token written to infra/.env (or `--dry-run` invoked)
#   1  login refused / API non-2xx / .env rewrite failed
#   2  missing required env / missing infra/.env
#   3  --help invoked
#
# Cron entry (hourly at :00, runs from repo root, stdout+stderr appended
# to a tmpfs log to survive log-rotation):
#
#   0 * * * * cd ~/repos/3d-portal && bash infra/scripts/cutover-share-token-refresh.sh >> /tmp/cutover-share-refresh.log 2>&1
#
# Flags:
#   --help     print this header docstring; exit 3
#   --dry-run  obtain a new token but do NOT mutate infra/.env (smoke test the
#              path without touching state)
#
# Example:
#   set -a; source infra/.env; set +a
#   bash infra/scripts/cutover-share-token-refresh.sh
#   bash infra/scripts/cutover-share-token-refresh.sh --dry-run
#
# Help:
#   bash infra/scripts/cutover-share-token-refresh.sh --help

set -Eeuo pipefail

# --- Help handling first -----------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,/^set -Eeuo pipefail$/p' "$0" | sed -E 's/^# ?//;/^set -Eeuo pipefail$/d'
  exit 3
fi

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi
if [[ $# -gt 0 ]]; then
  echo "cutover-share-refresh: unknown argument '$1' (try --help)" >&2
  exit 2
fi

# --- Dependency check --------------------------------------------------------
command -v jq >/dev/null || { echo "cutover-share-refresh: missing dependency: jq" >&2; exit 2; }
command -v curl >/dev/null || { echo "cutover-share-refresh: missing dependency: curl" >&2; exit 2; }

# --- Repo + env loading ------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

ENV_FILE="$REPO_DIR/infra/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "cutover-share-refresh: $ENV_FILE not found" >&2
  exit 2
fi
set -a; source "$ENV_FILE"; set +a

_missing_env=()
for v in CUTOVER_TEST_MEMBER_EMAIL CUTOVER_TEST_MEMBER_PASSWORD CUTOVER_TEST_MODEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    _missing_env+=("$v")
  fi
done
if (( ${#_missing_env[@]} > 0 )); then
  echo "cutover-share-refresh: missing required env in infra/.env: ${_missing_env[*]}" >&2
  exit 2
fi

: "${PORTAL_URL:=https://3d.ezop.ddns.net}"
: "${CUTOVER_SHARE_TTL_HOURS:=24}"
: "${CUTOVER_REFRESH_LOG_FILE:=/var/log/3d-portal-cutover-share-refresh.log}"

# --- Logging plumbing --------------------------------------------------------
# Try to redirect stderr to the requested log file; fall back to inherited
# stderr (cron's caller) on permission failure. We log to stderr so the
# cron-wrapping `>> /tmp/...log 2>&1` still works for ops who don't have
# write to /var/log.
log() { printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$" "$*" >&2; }

if [[ -w "$(dirname "$CUTOVER_REFRESH_LOG_FILE")" || -w "$CUTOVER_REFRESH_LOG_FILE" ]] 2>/dev/null; then
  if ! exec 2>>"$CUTOVER_REFRESH_LOG_FILE"; then
    log "WARN: could not redirect stderr to $CUTOVER_REFRESH_LOG_FILE; using inherited stderr"
  fi
fi

log "cutover-share-refresh: start (portal=$PORTAL_URL, ttl=${CUTOVER_SHARE_TTL_HOURS}h, dry_run=$DRY_RUN)"

# --- Tempfiles + cleanup -----------------------------------------------------
umask 077
TMPDIR_RUN=$(mktemp -d /tmp/cutover-share-refresh.XXXXXX)
COOKIES="$TMPDIR_RUN/member-cookies.txt"
LOGIN_RESP="$TMPDIR_RUN/login.json"
SHARE_RESP="$TMPDIR_RUN/share.json"
cleanup() { rm -rf "$TMPDIR_RUN" 2>/dev/null || true; }
trap cleanup EXIT

# --- Login as test-member ----------------------------------------------------
HTTP_TIMEOUT=10
log "logging in as $CUTOVER_TEST_MEMBER_EMAIL"
if ! login_code=$(curl --max-time "$HTTP_TIMEOUT" -sS -o "$LOGIN_RESP" -w "%{http_code}" \
    -c "$COOKIES" -X POST \
    -H "Content-Type: application/json" -H "X-Portal-Client: web" \
    -d "{\"email\":\"$CUTOVER_TEST_MEMBER_EMAIL\",\"password\":\"$CUTOVER_TEST_MEMBER_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login"); then
  log "FATAL: curl to /api/auth/login failed (network error)"
  exit 1
fi
if [[ "$login_code" != "200" ]]; then
  log "FATAL: /api/auth/login returned HTTP $login_code (test-member credentials wrong, or partial_auth path)"
  exit 1
fi
chmod 600 "$COOKIES"

if jq -e '.partial_auth == true' "$LOGIN_RESP" >/dev/null 2>&1; then
  log "FATAL: test-member /api/auth/login returned partial_auth=true (2FA enabled). Disable 2FA on test-member or pre-cutover fixture is unusable."
  exit 1
fi

# --- Create new share token --------------------------------------------------
log "POST /api/admin/share model_id=$CUTOVER_TEST_MODEL_ID expires_in_hours=$CUTOVER_SHARE_TTL_HOURS"
if ! share_code=$(curl --max-time "$HTTP_TIMEOUT" -sS -o "$SHARE_RESP" -w "%{http_code}" \
    -b "$COOKIES" -X POST \
    -H "Content-Type: application/json" -H "X-Portal-Client: web" \
    -d "{\"model_id\":\"$CUTOVER_TEST_MODEL_ID\",\"expires_in_hours\":$CUTOVER_SHARE_TTL_HOURS}" \
    "$PORTAL_URL/api/admin/share"); then
  log "FATAL: curl to /api/admin/share failed (network error)"
  exit 1
fi
if [[ "$share_code" != "201" ]]; then
  log "FATAL: POST /api/admin/share returned HTTP $share_code; body=$(cat "$SHARE_RESP" 2>/dev/null | head -c 500)"
  exit 1
fi

NEW_TOKEN=$(jq -r '.token' "$SHARE_RESP")
EXPIRES_AT=$(jq -r '.expires_at' "$SHARE_RESP")
if [[ -z "$NEW_TOKEN" || "$NEW_TOKEN" == "null" ]]; then
  log "FATAL: /api/admin/share response missing .token (body=$(cat "$SHARE_RESP" | head -c 500))"
  exit 1
fi

log "new share token issued (expires_at=$EXPIRES_AT, prefix=$(echo "$NEW_TOKEN" | cut -c1-6)...)"

if (( DRY_RUN == 1 )); then
  log "--dry-run: NOT mutating $ENV_FILE; would have written CUTOVER_TEST_SHARE_TOKEN=<new>"
  exit 0
fi

# --- Atomic .env rewrite -----------------------------------------------------
# Read current .env, replace the CUTOVER_TEST_SHARE_TOKEN line (or append if
# absent), write to a sibling tempfile in the same directory, then mv. The
# sibling-tempfile + mv pattern is atomic on the same filesystem; readers
# (cutover-smoke.sh) either see the old file in full or the new file in full.
ENV_TMP=$(mktemp "$ENV_FILE.tmp.XXXXXX")
# Preserve original mode (typically 600) on the replacement.
ORIG_MODE=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo 600)
chmod "$ORIG_MODE" "$ENV_TMP"

if grep -qE '^CUTOVER_TEST_SHARE_TOKEN=' "$ENV_FILE"; then
  # Use awk for in-place line replacement (sed -i on a tempfile is awkward
  # with special chars in the token). Token is URL-safe-base64 — no shell
  # metachars — but awk is safer regardless.
  awk -v tok="$NEW_TOKEN" '
    /^CUTOVER_TEST_SHARE_TOKEN=/ { print "CUTOVER_TEST_SHARE_TOKEN=" tok; next }
    { print }
  ' "$ENV_FILE" > "$ENV_TMP"
else
  # First-time write — append at end with a section comment.
  cat "$ENV_FILE" > "$ENV_TMP"
  printf '\n# Cutover smoke fixture (rotated hourly by cutover-share-token-refresh.sh)\nCUTOVER_TEST_SHARE_TOKEN=%s\n' "$NEW_TOKEN" >> "$ENV_TMP"
fi

# Validate the rewrite contains the new token before swapping.
if ! grep -qE "^CUTOVER_TEST_SHARE_TOKEN=${NEW_TOKEN}\$" "$ENV_TMP"; then
  log "FATAL: rewrite verification failed — new token NOT present in $ENV_TMP; aborting mv"
  rm -f "$ENV_TMP"
  exit 1
fi

mv -f "$ENV_TMP" "$ENV_FILE"
log "✅ $ENV_FILE updated; cutover-smoke.sh will pick up new token on next run"
exit 0
