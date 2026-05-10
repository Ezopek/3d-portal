#!/usr/bin/env bash
# Render a GlitchTip issue as a markdown story stub paste-ready into BMAD
# planning skills (`bmad-quick-dev`, `bmad-create-story`).
#
# AI agents triaging an issue should run this script instead of opening the
# GlitchTip web UI — the markdown stub is the entire interface, and its
# schema is verifiable against tests/golden/triage-schema.txt so downstream
# BMAD parsers cannot break silently.
#
# Required env (sourced from infra/.env on dev box):
#   GLITCHTIP_AUTH_TOKEN     long-lived token; org:read + project:read
#                            scopes are sufficient for this script
#                            (read-only triage path, no write ops).
#
# Optional env (overrideable):
#   GLITCHTIP_URL      GlitchTip API base. Default
#                      http://192.168.2.190:8800 (LAN HTTP — fastest from
#                      dev box). For off-LAN dev boxes, set
#                      https://glitchtip.ezop.ddns.net before invoking.
#
# Exit codes:
#   0 - success: markdown stub printed to stdout, OR --schema/--help
#       served and exited cleanly.
#   1 - missing dependency (jq/curl absent) OR unexpected REST response
#       (non-2xx, non-401, non-403, non-5xx).
#   2 - missing/invalid argument (no issue_id provided), OR GlitchTip
#       unreachable (REST 5xx).
#   3 - GlitchTip auth/scope failure (REST 401/403).
#
# Examples:
#   set -a; source infra/.env; set +a
#   bash infra/scripts/glitchtip-triage.sh 51         # render real issue
#   bash infra/scripts/glitchtip-triage.sh --schema   # bare template
#   bash infra/scripts/glitchtip-triage.sh --help     # this header
#
# The --schema flag prints the bare template (placeholder tokens, no REST
# call) and exits 0. Used for golden-file diff verification:
#   bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -
# Diff failure means the schema drifted — reconcile to the PRD's Decision F
# contract via a follow-up edit, not a silent absorption (NFR-I3).

set -euo pipefail

# --- Help flag ---------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'
  exit 0
fi

# --- Dependency check (AR12) -------------------------------------------------
command -v jq >/dev/null || { echo "missing: jq" >&2; exit 1; }
command -v curl >/dev/null || { echo "missing: curl" >&2; exit 1; }

# --- Schema rendering function (single source of truth) ----------------------
# Called with no args (or all empties) for the --schema bare template; called
# with extracted values to render the populated stub. Both paths emit the same
# bytes minus placeholder substitutions, guaranteeing schema parity.
render_stub() {
  # `${var-default}` (no colon) substitutes default only when UNSET, not when
  # empty. Important for `model_id_segment`: a populated render passes an
  # empty string when the event has no model.id tag (segment is suppressed);
  # a `--schema` call (no args) gets the placeholder.
  local issue_id="${1-<issue_id>}"
  local title="${2-<title>}"
  local filename="${3-<filename>}"
  local lineno="${4-<line>}"
  local fingerprint="${5-<fingerprint>}"
  local route_pathname="${6-<route.pathname>}"
  local model_id_segment="${7-(model.id=<id>)}"
  local release="${8-<release>}"
  local git_commit="${9-<git.commit>}"
  local last5_block="${10-1. \`<timestamp>\` — \`<message preview>\`
  2. \`<timestamp>\` — \`<message preview>\`
  3. \`<timestamp>\` — \`<message preview>\`
  4. \`<timestamp>\` — \`<message preview>\`
  5. \`<timestamp>\` — \`<message preview>\`}"
  local permalink="${11-<permalink>}"

  cat <<EOF
# Issue #${issue_id}: ${title}

- **Top frame:** \`${filename}:${lineno}\`
- **Fingerprint:** \`${fingerprint}\`
- **Route:** \`${route_pathname}\` ${model_id_segment}
- **Release:** \`${release}\` (commit \`${git_commit}\`)
- **Last 5 events:**
  ${last5_block}
- **Suggested file to edit:** \`${filename}\` (top-frame source)

GlitchTip link: ${permalink}
EOF
}

# --- Schema flag (no REST call) ---------------------------------------------
if [[ "${1:-}" == "--schema" ]]; then
  render_stub
  exit 0
fi

# --- Argument validation -----------------------------------------------------
ISSUE_ID="${1:-}"
if [[ -z "$ISSUE_ID" ]]; then
  printf 'usage: %s <issue_id> | --schema | --help\n\n' "$(basename "$0")" >&2
  sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//' >&2
  exit 2
fi

# --- Bootstrap (env) ---------------------------------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -f "${REPO_DIR}/infra/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "${REPO_DIR}/infra/.env"; set +a
fi
: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"
GLITCHTIP_URL="${GLITCHTIP_URL:-http://192.168.2.190:8800}"

# --- REST: fetch latest event for the issue (AR13 idiom) ---------------------
LATEST_BODY="/tmp/gt-triage-${ISSUE_ID}-$$-latest.json"
EVENTS_BODY="/tmp/gt-triage-${ISSUE_ID}-$$-events.json"
trap 'rm -f "${LATEST_BODY}" "${EVENTS_BODY}"' EXIT

# Wrap the primary curl in an if-guard so transport failures (DNS error,
# connect refused, timeout) map to the documented exit code 2 instead of
# letting `set -e` bail with curl's raw exit code (e.g. 7, 28). Mirrors
# the pattern in verify-symbolication.sh.
if ! http_code=$(curl -sS -o "${LATEST_BODY}" -w '%{http_code}' \
  --max-time 10 \
  -H "Authorization: Bearer ${GLITCHTIP_AUTH_TOKEN}" \
  "${GLITCHTIP_URL}/api/0/issues/${ISSUE_ID}/events/latest/"); then
  echo "GlitchTip unreachable (curl transport failure) on /api/0/issues/${ISSUE_ID}/events/latest/" >&2
  exit 2
fi

case "${http_code}" in
  20*) ;;
  401|403)
    echo "auth/scope failure (${http_code}) on /api/0/issues/${ISSUE_ID}/events/latest/" >&2
    exit 3
    ;;
  5*)
    echo "GlitchTip unreachable (${http_code}) on /api/0/issues/${ISSUE_ID}/events/latest/" >&2
    exit 2
    ;;
  *)
    echo "unexpected response (${http_code}) on /api/0/issues/${ISSUE_ID}/events/latest/:" >&2
    cat "${LATEST_BODY}" >&2
    echo >&2
    exit 1
    ;;
esac

# --- REST: fetch last 5 events (graceful fallback on failure) ----------------
# Transport failures here are non-fatal (latest event already extracted);
# the `|| echo "000"` swallows curl's non-zero exit so set -e doesn't kill
# the script before we can degrade gracefully to a "—" last-5 block.
events_http=$(curl -sS -o "${EVENTS_BODY}" -w '%{http_code}' \
  --max-time 10 \
  -H "Authorization: Bearer ${GLITCHTIP_AUTH_TOKEN}" \
  "${GLITCHTIP_URL}/api/0/issues/${ISSUE_ID}/events/?limit=5" 2>/dev/null || echo "000")

# --- jq extraction (latest event = camelCase shape) --------------------------
TITLE=$(jq -r '.title // "—"' < "${LATEST_BODY}")
FINGERPRINT=$(jq -r '.groupID // "—"' < "${LATEST_BODY}")
PERMALINK=$(jq -r '.permalink // ""' < "${LATEST_BODY}")
RELEASE=$(jq -r '.release // (.tags[]? | select(.key=="service.version") | .value) // "—"' < "${LATEST_BODY}")
GIT_COMMIT=$(jq -r '(.tags[]? | select(.key=="git.commit") | .value) // "—"' < "${LATEST_BODY}")
ROUTE_PATHNAME=$(jq -r '(.tags[]? | select(.key=="route.pathname") | .value) // "—"' < "${LATEST_BODY}")
MODEL_ID=$(jq -r '(.tags[]? | select(.key=="model.id") | .value) // ""' < "${LATEST_BODY}")

# Stack trace: last frame of the first exception is the top of the call stack
# (Sentry frames are call-order, not stack-order — innermost = last index).
TOP_FRAME_FILE=$(jq -r '
  (.entries // [])
  | map(select(.type=="exception"))
  | .[0].data.values[0].stacktrace.frames // []
  | (.[-1].filename // "—")
' < "${LATEST_BODY}")
TOP_FRAME_LINE=$(jq -r '
  (.entries // [])
  | map(select(.type=="exception"))
  | .[0].data.values[0].stacktrace.frames // []
  | (.[-1].lineno // "—" | tostring)
' < "${LATEST_BODY}")

# Conditional `(model.id=...)` segment: present only when the tag exists.
if [[ -n "${MODEL_ID}" && "${MODEL_ID}" != "null" ]]; then
  MODEL_SEGMENT="(model.id=${MODEL_ID})"
else
  MODEL_SEGMENT=""
fi

# Permalink fallback: derive from URL when the field is missing/empty.
if [[ -z "${PERMALINK}" || "${PERMALINK}" == "null" ]]; then
  PERMALINK="${GLITCHTIP_URL}/-/issues/${ISSUE_ID}/"
fi

# Last 5 events block: snake_case at the events list endpoint.
# GlitchTip 6.1.x returns either a plain array (single page) OR the
# documented paginated shape `{"items":[...], "next":...}` for larger
# result sets. Normalize via `if type == "array" then . else .items end`
# so both shapes render correctly. Codex review of ed48ab2 caught the
# paginated case as a P1 — the script would jq-error and exit non-zero.
if [[ "${events_http}" == 20* ]]; then
  LAST5_BLOCK=$(jq -r '
    (if type == "array" then . else (.items // []) end)
    | to_entries
    | map("\(.key+1). `\(.value.date_created // "—")` — `\(.value.message // .value.title // "—")`")
    | .[]
  ' < "${EVENTS_BODY}" 2>/dev/null | sed 's/^/  /' | sed -E '1s/^  //' || true)
  if [[ -z "${LAST5_BLOCK}" ]]; then
    LAST5_BLOCK="—"
  fi
else
  LAST5_BLOCK="—"
fi

# --- Render populated stub ---------------------------------------------------
render_stub \
  "${ISSUE_ID}" \
  "${TITLE}" \
  "${TOP_FRAME_FILE}" \
  "${TOP_FRAME_LINE}" \
  "${FINGERPRINT}" \
  "${ROUTE_PATHNAME}" \
  "${MODEL_SEGMENT}" \
  "${RELEASE}" \
  "${GIT_COMMIT}" \
  "${LAST5_BLOCK}" \
  "${PERMALINK}"
