#!/usr/bin/env bash
# Verify post-deploy symbolication is alive on the homelab GlitchTip.
#
# Triggers a deterministic frontend smoke event via `?__sentry_smoke=<uuid>`,
# polls GlitchTip REST for the matching event (≤30 s wall-clock budget),
# asserts the top stack frame resolves to a real `apps/web/src/<...>.tsx`
# path, and writes a single-line tripwire marker at `infra/.last-verify`.
# On failure also POSTs a synthetic envelope event tagged
# `deploy.verification=failed` so the alarm channel is in-band with the
# rest of GlitchTip triage.
#
# Required env (sourced from infra/.env on dev box):
#   GLITCHTIP_AUTH_TOKEN     long-lived token; org:read + project:read +
#                            event:write (write needed for synthetic alarm).
#   GLITCHTIP_ORG_SLUG       org slug (default-fixture: homelab).
#   GLITCHTIP_PROJECT_SLUG   project slug (default-fixture: 3d-portal).
#   VITE_SENTRY_DSN          DSN — public key + project_id parsed for the
#                            envelope POST URL + auth header.
#
# Optional env (overrideable):
#   GLITCHTIP_URL      GlitchTip API base (default http://192.168.2.190:8800
#                      — LAN HTTP, fastest from dev box; works for sub-MB
#                      GETs and the synthetic envelope POST).
#   PORTAL_PUBLIC_URL  Production SPA URL where the smoke handler runs
#                      (default https://3d.ezop.ddns.net).
#
# Exit codes (FR12 contract — `deploy.sh` consumes these in Story 3.2):
#   0 - success; smoke event symbolicated, top frame matches
#       `^apps/web/src/.+\.tsx?$`. infra/.last-verify carries OK.
#   1 - symbolication broken; event found but top-frame regex MISMATCH
#       (or event had no exception stacktrace, or unexpected REST shape).
#       infra/.last-verify carries FAILED. Synthetic alarm POSTed.
#   2 - GlitchTip unreachable (REST 5xx, network/DNS error, smoke-page 4xx/5xx).
#       infra/.last-verify carries FAILED. No alarm (GlitchTip is broken party).
#   3 - GlitchTip auth/scope failure (REST 401/403). infra/.last-verify
#       carries FAILED. Alarm best-effort (envelope auth differs from REST
#       auth — uses DSN public key, may still succeed).
#   4 - timeout; no matching event within 30s budget (NFR-P3).
#       infra/.last-verify carries FAILED. No alarm (cause unknown).
#
# Example:
#   set -a; source infra/.env; set +a
#   bash infra/scripts/verify-symbolication.sh
#   # → ✓ verify OK — top frame: apps/web/src/main.tsx, release: 0.1.0+ab12cd3
#
# Help:
#   bash infra/scripts/verify-symbolication.sh --help

set -euo pipefail

# --- Help flag --------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  # Reprint the header comment block (lines 2..first blank) with leading
  # `# ` stripped. Single source of truth — the docstring IS the help text.
  sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'
  exit 0
fi

# --- Bootstrap --------------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

command -v jq >/dev/null    || { echo "✗ missing required tool: jq" >&2; exit 1; }
command -v curl >/dev/null  || { echo "✗ missing required tool: curl" >&2; exit 1; }
command -v uuidgen >/dev/null || { echo "✗ missing required tool: uuidgen" >&2; exit 1; }
command -v timeout >/dev/null || { echo "✗ missing required tool: timeout (coreutils)" >&2; exit 1; }

# Headless browser is mandatory: the smoke event fires inside the SPA's JS
# (`apps/web/src/main.tsx`), so a plain curl GET cannot trigger it — only a
# real browser executing the bundle. Auto-detect the first available chrome
# binary; the operator can pin a specific one via HEADLESS_BROWSER env.
HEADLESS_BROWSER="${HEADLESS_BROWSER:-}"
if [[ -z "$HEADLESS_BROWSER" ]]; then
  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null; then
      HEADLESS_BROWSER="$c"
      break
    fi
  done
fi
[[ -z "$HEADLESS_BROWSER" ]] && {
  echo "✗ no headless browser found (need google-chrome or chromium)" >&2
  echo "  set HEADLESS_BROWSER=<binary> in env to override" >&2
  exit 1
}

set -a
# shellcheck disable=SC1090,SC1091
source "$REPO_DIR/infra/.env"
set +a

: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"
: "${GLITCHTIP_ORG_SLUG:?missing in infra/.env}"
: "${GLITCHTIP_PROJECT_SLUG:?missing in infra/.env}"
: "${VITE_SENTRY_DSN:?missing in infra/.env}"

GLITCHTIP_URL="${GLITCHTIP_URL:-http://192.168.2.190:8800}"
PORTAL_PUBLIC_URL="${PORTAL_PUBLIC_URL:-https://3d.ezop.ddns.net}"

# Parse the DSN once — needed for the envelope endpoint URL + auth header.
# Format: https://<public_key>@<host>/<project_id>
dsn_key=$(sed -E 's|.*//([^@]+)@.*|\1|' <<<"$VITE_SENTRY_DSN")
project_id=$(sed -E 's|.*/||' <<<"$VITE_SENTRY_DSN")
envelope_url="${GLITCHTIP_URL}/api/${project_id}/envelope/"

# 30s wall-clock deadline — applies from script start, not just the poll
# loop. NFR-P3 codifies this as an SLO consumed by Story 3.2's deploy chain.
deadline=$(( $(date +%s) + 30 ))
smoke_run_id="$(uuidgen)"

# --- Helpers ----------------------------------------------------------------

# Seconds left until the 30s deadline, clamped to [1, max]. Used to cap each
# curl `--max-time` and sleep so the wall-clock budget stays hard.
budget_left() {
  local max="$1" now remaining
  now=$(date +%s)
  remaining=$((deadline - now))
  if (( remaining < 1 )); then
    echo 1
  elif (( remaining < max )); then
    echo "$remaining"
  else
    echo "$max"
  fi
}

# Persist the .last-verify tripwire line. Single line, tab-separated, plain
# ASCII (AR8). Always overwrites — idempotent on re-runs (AC12).
write_last_verify() {
  local status="$1" rel="${2:-unknown}"
  printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$status" "$rel" \
    > "$REPO_DIR/infra/.last-verify"
}

# Synthetic alarm event (AR9) — POST envelope to GlitchTip when verify fails
# with code 1 (regex mismatch / unexpected event shape) or code 3 (auth — best
# effort: envelope POST uses DSN public key, may still ingest even if Bearer
# is rejected). Codes 2 and 4 skip the alarm: code 2 means GlitchTip itself
# is unreachable, code 4 means cause unknown.
emit_alarm() {
  local exit_code="$1" actual_frame="$2" rel="$3" run_id="$4"
  local event_id unix_ts envelope_file http_code iso_now
  event_id=$(uuidgen | tr -d -)
  unix_ts=$(date +%s)
  iso_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  envelope_file=/tmp/gt-envelope.json
  {
    printf '{"event_id":"%s","sent_at":"%s"}\n' "$event_id" "$iso_now"
    printf '{"type":"event"}\n'
    jq -nc \
      --arg eid "$event_id" \
      --argjson uts "$unix_ts" \
      --arg msg "deploy verification failed: symbolication broken (top frame regex mismatch)" \
      --arg rid "$run_id" \
      --arg rel "$rel" \
      --argjson exit "$exit_code" \
      --arg actual "$actual_frame" \
      '{event_id:$eid, timestamp:$uts, level:"warning", platform:"other",
        message:{formatted:$msg},
        tags:{"deploy.verification":"failed","smoke.run_id":$rid,"service.version":$rel,"deployment.environment":"production"},
        extra:{exit_code:$exit, expected_top_frame_regex:"^apps/web/src/.+\\.tsx?$", actual_top_frame:$actual}}'
  } > "$envelope_file"
  if ! http_code=$(curl -sS --max-time 5 -o /tmp/gt-envelope-response.json -w '%{http_code}' \
      -X POST \
      -H "Content-Type: application/x-sentry-envelope" \
      -H "X-Sentry-Auth: Sentry sentry_version=7, sentry_key=${dsn_key}, sentry_client=verify-symbolication.sh/1.0" \
      --data-binary "@${envelope_file}" \
      "$envelope_url"); then
    echo "⚠ alarm POST failed (network error; alarm event NOT ingested)" >&2
    return
  fi
  case "$http_code" in
    20*) echo "→ alarm event posted (event_id=$event_id)" ;;
    *)   echo "⚠ alarm POST returned $http_code (alarm event may not have been ingested)" >&2 ;;
  esac
}

# Single failure exit point — writes FAILED tripwire, optionally fires the
# synthetic alarm event, exits with the FR12 code. Caller passes the code,
# the (best-effort) release tag, the actual top frame (if known), and a
# stderr message describing the failure mode.
fail_verify() {
  local code="$1" rel="${2:-unknown}" frame="${3:-}" msg="$4"
  write_last_verify "FAILED" "$rel"
  printf '\033[31m✗ verify FAILED: %s\033[0m\n' "$msg" >&2
  case "$code" in
    1|3) emit_alarm "$code" "$frame" "$rel" "$smoke_run_id" || true ;;
  esac
  exit "$code"
}

# AR13 GlitchTip REST GET — case-statement maps HTTP code to FR12 exit code.
# Network/DNS failures hit the `if !`-branch (curl exits non-zero before
# emitting %{http_code}); REST 5xx returns a `5xx` http_code with the body
# in $out. stderr: errors via fail_verify; stdout: nothing on success.
gt_get() {
  local url="$1" out="$2"
  local http_code max_time
  max_time=$(budget_left 10)
  if ! http_code=$(curl -sS --max-time "$max_time" -o "$out" -w '%{http_code}' \
      -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "$url"); then
    fail_verify 2 "" "" "GlitchTip unreachable (network error)"
  fi
  case "$http_code" in
    20*)     return 0 ;;
    401|403) fail_verify 3 "" "" "GlitchTip auth/scope failure ($http_code)" ;;
    5*)      fail_verify 2 "" "" "GlitchTip unreachable ($http_code)" ;;
    *)       fail_verify 1 "" "" "unexpected response ($http_code) from $url" ;;
  esac
}

# --- Smoke trigger ----------------------------------------------------------
echo "→ Triggering smoke event: smoke.run_id=$smoke_run_id"
smoke_url="${PORTAL_PUBLIC_URL%/}/?__sentry_smoke=${smoke_run_id}"

# Precheck: production page must be reachable. curl can't fire the smoke
# (no JS execution), but a 200 here means the SPA shell is up before we
# spin chrome.
if ! curl -fsS -o /dev/null --max-time "$(budget_left 10)" "$smoke_url"; then
  fail_verify 2 "" "" "production page unreachable at $smoke_url"
fi

# Headless chrome loads the SPA, executes the smoke handler in main.tsx,
# and Sentry.flush(2000) drains the transport queue. virtual-time-budget
# advances JS timers so the flush completes; timeout caps wallclock so a
# hung browser never eats the full 30s budget.
chrome_user_dir="$(mktemp -d -t verify-chrome-XXXXXX)"
trap 'rm -rf "$chrome_user_dir"' EXIT
timeout "$(budget_left 8)" "$HEADLESS_BROWSER" \
  --headless=new --disable-gpu --no-sandbox \
  --user-data-dir="$chrome_user_dir" \
  --hide-scrollbars \
  --virtual-time-budget=5000 \
  --dump-dom "$smoke_url" >/dev/null 2>&1 || true

echo "→ Polling GlitchTip REST for matching event (budget: 30s)"
issues_url="${GLITCHTIP_URL}/api/0/projects/${GLITCHTIP_ORG_SLUG}/${GLITCHTIP_PROJECT_SLUG}/issues/?statsPeriod=5m&query=smoke.run_id:${smoke_run_id}"

# --- Poll loop --------------------------------------------------------------
issue_id=""
while [[ $(date +%s) -lt $deadline ]]; do
  gt_get "$issues_url" /tmp/gt-issues.json
  issue_id=$(jq -r '.[0].id // empty' < /tmp/gt-issues.json)
  [[ -n "$issue_id" ]] && break
  # Clamp the poll cadence to the remaining budget so the last sleep can't
  # blow the deadline.
  sleep "$(budget_left 2)"
done

if [[ -z "$issue_id" ]]; then
  fail_verify 4 "" "" "no matching GlitchTip event for smoke.run_id=$smoke_run_id within 30s"
fi

echo "→ Matched issue id=$issue_id; fetching latest event"

# --- Fetch latest event + extract top frame --------------------------------
event_url="${GLITCHTIP_URL}/api/0/issues/${issue_id}/events/latest/"
gt_get "$event_url" /tmp/gt-event.json

top_frame=$(jq -r \
  '.entries[]? | select(.type=="exception") | .data.values[0].stacktrace.frames[-1].filename // empty' \
  < /tmp/gt-event.json | head -n1)
# GlitchTip surfaces the SDK's `release` field as a tag, not as a top-level
# event field. Read from .tags[] for compatibility with the 6.1.x API.
release=$(jq -r '.tags[]? | select(.key=="release") | .value // empty' < /tmp/gt-event.json | head -n1)
if [[ -z "$release" ]]; then
  echo "⚠ event missing release tag — falling back to 'unknown'" >&2
  release="unknown"
fi
if [[ -z "$top_frame" ]]; then
  fail_verify 1 "$release" "" "event has no exception stacktrace; top frame unavailable"
fi

# --- Regex assertion --------------------------------------------------------
if [[ "$top_frame" =~ ^apps/web/src/.+\.tsx?$ ]]; then
  write_last_verify "OK" "$release"
  echo "✓ verify OK — top frame: $top_frame, release: $release"
  exit 0
fi

# Failure path: regex mismatch (FR12 exit 1).
fail_verify 1 "$release" "$top_frame" "top frame regex mismatch (got: $top_frame)"
