#!/usr/bin/env bash
# Operator-run pre-flight before triggering Story 10.3's atomic edge cutover.
# Story 10.1 AC5.
#
# Verifies the three Story 10.1 fixtures are live and the smoke script
# self-tests cleanly against `.190`:
#
#   Check 1 — test-member account     POST /api/auth/login as test-member → 200
#   Check 2 — share-token URL         GET  /share/<token>                 → 200
#   Check 3 — smoke script self-test  bash cutover-smoke.sh               → 0
#
# Run this on the dev box (which is on the LAN that nginx-180 still
# IP-allowlists) WITHIN the 24h pre-cutover window so any fixture-rot is
# caught BEFORE the cutover commit lands. The smoke self-test alone proves
# checks 1 + 2 pass (smoke Scenario 3 covers test-member login, Scenario 1
# covers share-token URL), but we run them explicitly first so a fixture
# regression yields a precise diagnostic instead of a generic "smoke FAIL".
#
# Required env (sourced from infra/.env):
#   ADMIN_EMAIL                   admin (Michał) — used only for diagnostics
#   ADMIN_PASSWORD
#   AGENT_EMAIL                   agent role
#   AGENT_PASSWORD
#   CUTOVER_TEST_MEMBER_EMAIL     test-member account
#   CUTOVER_TEST_MEMBER_PASSWORD
#   CUTOVER_TEST_SHARE_TOKEN      kept fresh by cutover-share-token-refresh.sh
#   CUTOVER_TEST_MODEL_ID         test-member-owned model
#
# Optional env:
#   PORTAL_URL                    default https://3d.ezop.ddns.net
#
# Flags:
#   --help        print this header docstring; exit 3
#   --skip-smoke  run only the fixture checks; skip the smoke self-test
#                 (useful when you've already run the smoke separately)
#
# Exit codes:
#   0  all 3 checks PASS; cutover prerequisites are green
#   1  ≥1 check FAIL; fix the fixture / regenerate the share token / re-seed
#      the test-member before triggering Story 10.3
#   2  prerequisite failure (env var missing, portal unreachable)
#   3  --help invoked
#
# Example:
#   set -a; source infra/.env; set +a
#   bash infra/scripts/cutover-preflight.sh
#   # → 0; ✅ all 3 checks PASS; proceed to Story 10.3
#
# Help:
#   bash infra/scripts/cutover-preflight.sh --help

set -Eeuo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,/^set -Eeuo pipefail$/p' "$0" | sed -E 's/^# ?//;/^set -Eeuo pipefail$/d'
  exit 3
fi

SKIP_SMOKE=0
if [[ "${1:-}" == "--skip-smoke" ]]; then
  SKIP_SMOKE=1
  shift
fi
if [[ $# -gt 0 ]]; then
  echo "cutover-preflight: unknown argument '$1' (try --help)" >&2
  exit 2
fi

command -v jq >/dev/null || { echo "cutover-preflight: missing dependency: jq" >&2; exit 2; }
command -v curl >/dev/null || { echo "cutover-preflight: missing dependency: curl" >&2; exit 2; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if [[ -f "$REPO_DIR/infra/.env" ]]; then
  set -a; source "$REPO_DIR/infra/.env"; set +a
fi

_missing_env=()
for v in CUTOVER_TEST_MEMBER_EMAIL CUTOVER_TEST_MEMBER_PASSWORD \
         CUTOVER_TEST_SHARE_TOKEN CUTOVER_TEST_MODEL_ID; do
  if [[ -z "${!v:-}" ]]; then
    _missing_env+=("$v")
  fi
done
if (( ${#_missing_env[@]} > 0 )); then
  echo "cutover-preflight: missing required env in infra/.env: ${_missing_env[*]}" >&2
  exit 2
fi

: "${PORTAL_URL:=https://3d.ezop.ddns.net}"

if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_RED=""; C_GREEN=""; C_BOLD=""; C_RESET=""
fi

umask 077
TMPDIR_RUN=$(mktemp -d /tmp/cutover-preflight.XXXXXX)
trap 'rm -rf "$TMPDIR_RUN" 2>/dev/null || true' EXIT

FAIL_COUNT=0

echo "${C_BOLD}cutover-preflight: ${PORTAL_URL}${C_RESET}"

# --- Check 1 — test-member account ------------------------------------------
LOGIN_RESP="$TMPDIR_RUN/member-login.json"
HTTP_TIMEOUT=10
if member_code=$(curl --max-time "$HTTP_TIMEOUT" -sS -o "$LOGIN_RESP" -w "%{http_code}" \
    -X POST -H "Content-Type: application/json" -H "X-Portal-Client: web" \
    -d "{\"email\":\"$CUTOVER_TEST_MEMBER_EMAIL\",\"password\":\"$CUTOVER_TEST_MEMBER_PASSWORD\"}" \
    "$PORTAL_URL/api/auth/login") \
   && [[ "$member_code" == "200" ]] \
   && ! jq -e '.partial_auth == true' "$LOGIN_RESP" >/dev/null 2>&1; then
  echo "  ${C_GREEN}PASS${C_RESET} 1 test-member account     login OK ($CUTOVER_TEST_MEMBER_EMAIL)"
else
  echo "  ${C_RED}FAIL${C_RESET} 1 test-member account     login returned HTTP=${member_code:-???}; re-seed via Story 10.1 T4"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# --- Check 2 — share-token URL ----------------------------------------------
if share_code=$(curl --max-time "$HTTP_TIMEOUT" -sS -o /dev/null -w "%{http_code}" \
    "$PORTAL_URL/share/$CUTOVER_TEST_SHARE_TOKEN") \
   && [[ "$share_code" == "200" ]]; then
  echo "  ${C_GREEN}PASS${C_RESET} 2 share-token URL         GET /share/<token> → 200"
else
  echo "  ${C_RED}FAIL${C_RESET} 2 share-token URL         GET /share/<token> returned HTTP=${share_code:-???}; run cutover-share-token-refresh.sh"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# --- Check 3 — smoke script self-test ---------------------------------------
if (( SKIP_SMOKE == 1 )); then
  echo "  SKIP 3 smoke self-test         --skip-smoke flag passed"
else
  SMOKE_LOG="$TMPDIR_RUN/smoke.log"
  if bash "$REPO_DIR/infra/scripts/cutover-smoke.sh" > "$SMOKE_LOG" 2>&1; then
    echo "  ${C_GREEN}PASS${C_RESET} 3 smoke self-test         4/4 scenarios PASS"
  else
    smoke_rc=$?
    echo "  ${C_RED}FAIL${C_RESET} 3 smoke self-test         exit=$smoke_rc; transcript follows:"
    sed 's/^/    /' "$SMOKE_LOG"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

echo ""
if (( FAIL_COUNT == 0 )); then
  echo "${C_BOLD}${C_GREEN}cutover-preflight: ✅ all checks PASS — cutover prerequisites green${C_RESET}"
  exit 0
fi

echo "${C_BOLD}${C_RED}cutover-preflight: ❌ ${FAIL_COUNT} check(s) FAIL — fix before triggering Story 10.3${C_RESET}"
exit 1
