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
#   1 - symbolication broken; event found but top-frame regex MISMATCH.
#       infra/.last-verify carries FAILED. Synthetic alarm POSTed.
#   2 - GlitchTip unreachable (REST 5xx OR network/DNS error). No alarm
#       (GlitchTip itself is the broken party).
#   3 - GlitchTip auth/scope failure (REST 401/403). Alarm best-effort.
#   4 - timeout; no matching event within 30s budget (NFR-P3). No alarm
#       (cause unknown — could be SDK, ingest lag, search).
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
# `infra/.env` carries an OTEL_EXPORTER_OTLP_HEADERS line whose value
# `authorization=Bearer <token>` contains an unquoted space; bash parses the
# token as a command and sets exit 127. Suspend `set -e` for the source so
# that quirk doesn't abort us. The vars we actually read (GLITCHTIP_*,
# VITE_SENTRY_DSN, GLITCHTIP_URL, PORTAL_PUBLIC_URL) export normally.
set +e
# shellcheck disable=SC1090,SC1091
source "$REPO_DIR/infra/.env" 2>/dev/null
set -e
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
iso_start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- Helpers ----------------------------------------------------------------

# AR13 GlitchTip REST GET — case-statement maps HTTP code to FR12 exit code.
# stdout: response body file path (caller reads it). stderr: errors.
gt_get() {
  local url="$1" out="$2"
  local http_code
  http_code=$(curl -sS --max-time 10 -o "$out" -w '%{http_code}' \
    -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
    "$url" || echo "000")
  case "$http_code" in
    20*)     return 0 ;;
    401|403) echo "✗ verify FAILED: GlitchTip auth/scope failure ($http_code)" >&2; exit 3 ;;
    5*)      echo "✗ verify FAILED: GlitchTip unreachable ($http_code)" >&2; exit 2 ;;
    000)     echo "✗ verify FAILED: GlitchTip unreachable (network error)" >&2; exit 2 ;;
    *)       echo "✗ unexpected response ($http_code) from $url: $(cat "$out" 2>/dev/null)" >&2; exit 1 ;;
  esac
}

# Synthetic alarm event (AR9) — POST envelope to GlitchTip when the verify
# concludes with exit code 1 (regex mismatch). NOT called for exit 2 (can't
# reach GlitchTip) or exit 4 (cause unknown). Best-effort: failure to POST
# is non-fatal because the primary signals (`infra/.last-verify` + stderr
# + non-zero exit) are already loud.
emit_alarm() {
  local exit_code="$1" actual_frame="$2" rel="$3" run_id="$4" iso="$5"
  local event_id unix_ts envelope_file http_code
  event_id=$(uuidgen | tr -d -)
  unix_ts=$(date +%s)
  envelope_file=/tmp/gt-envelope.json
  {
    printf '{"event_id":"%s","sent_at":"%s"}\n' "$event_id" "$iso"
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
  http_code=$(curl -sS --max-time 5 -o /tmp/gt-envelope-response.json -w '%{http_code}' \
    -X POST \
    -H "Content-Type: application/x-sentry-envelope" \
    -H "X-Sentry-Auth: Sentry sentry_version=7, sentry_key=${dsn_key}, sentry_client=verify-symbolication.sh/1.0" \
    --data-binary "@${envelope_file}" \
    "$envelope_url" || echo "000")
  case "$http_code" in
    20*) echo "→ alarm event posted (event_id=$event_id)" ;;
    *)   echo "⚠ alarm POST returned $http_code (alarm event may not have been ingested)" >&2 ;;
  esac
}

# --- Smoke trigger ----------------------------------------------------------
echo "→ Triggering smoke event: smoke.run_id=$smoke_run_id"
smoke_url="${PORTAL_PUBLIC_URL%/}/?__sentry_smoke=${smoke_run_id}"

# Precheck: production page must be reachable. curl can't fire the smoke
# (no JS execution), but a 200 here means the SPA shell is up before we
# spin chrome.
if ! curl -fsS -o /dev/null --max-time 10 "$smoke_url"; then
  echo "✗ smoke trigger failed: production page unreachable at $smoke_url" >&2
  exit 2
fi

# Headless chrome loads the SPA, executes the smoke handler in main.tsx,
# and Sentry.flush(2000) drains the transport queue. virtual-time-budget
# advances JS timers so the flush completes; timeout caps wallclock so a
# hung browser never eats the full 30s budget.
chrome_user_dir="$(mktemp -d -t verify-chrome-XXXXXX)"
trap 'rm -rf "$chrome_user_dir"' EXIT
timeout 8 "$HEADLESS_BROWSER" \
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
  sleep 2
done

if [[ -z "$issue_id" ]]; then
  echo "✗ verify FAILED: no matching GlitchTip event for smoke.run_id=$smoke_run_id within 30s" >&2
  exit 4
fi

echo "→ Matched issue id=$issue_id; fetching latest event"

# --- Fetch latest event + extract top frame --------------------------------
event_url="${GLITCHTIP_URL}/api/0/issues/${issue_id}/events/latest/"
gt_get "$event_url" /tmp/gt-event.json

top_frame=$(jq -r \
  '.entries[]? | select(.type=="exception") | .data.values[0].stacktrace.frames[-1].filename // empty' \
  < /tmp/gt-event.json | head -n1)
release=$(jq -r '.release // empty' < /tmp/gt-event.json)
if [[ -z "$release" ]]; then
  echo "⚠ event missing release field — falling back to 'unknown'" >&2
  release="unknown"
fi
if [[ -z "$top_frame" ]]; then
  echo "✗ event has no exception stacktrace; top frame unavailable" >&2
  exit 1
fi

iso_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# --- Regex assertion --------------------------------------------------------
if [[ "$top_frame" =~ ^apps/web/src/.+\.tsx?$ ]]; then
  printf '%s\t%s\t%s\n' "$iso_now" "OK" "$release" > "$REPO_DIR/infra/.last-verify"
  echo "✓ verify OK — top frame: $top_frame, release: $release"
  exit 0
fi

# Failure path: regex mismatch (FR12 exit 1).
printf '%s\t%s\t%s\n' "$iso_now" "FAILED" "$release" > "$REPO_DIR/infra/.last-verify"
printf '\033[31m✗ verify FAILED: top frame regex mismatch (got: %s)\033[0m\n' "$top_frame" >&2
emit_alarm 1 "$top_frame" "$release" "$smoke_run_id" "$iso_now" || true
exit 1
