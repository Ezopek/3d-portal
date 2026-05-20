#!/usr/bin/env bash
# Execute the Epic 9 audit baseline (Story 9.1) — install-already + run-now
# wrapper around bandit + semgrep + pip-audit + npm audit + OWASP ZAP.
#
# Produces five raw outputs + tool-versions.txt + reproducers.sh in
# `_bmad-output/implementation-artifacts/audit-raw/${AUDIT_DATE}/`
# (default `${AUDIT_DATE}` is today's UTC date). Re-running on the same date
# overwrites; passing a new date creates a fresh dated slot. The directory
# is gitignored (parent `_bmad-output/` is in .gitignore).
#
# Acceptance thresholds (Story 9.4 gate inputs):
#   bandit     — zero High-severity findings
#   semgrep    — zero severity:ERROR findings
#   pip-audit  — zero HIGH/CRITICAL severity vulnerabilities
#   npm audit  — zero high/critical severity vulnerabilities
#   ZAP        — zero riskcode>=3 (High/Critical) alerts
#
# This script DOES NOT enforce those thresholds (Story 9.4's gate decision
# is the enforcement surface). It only produces the artifacts.
#
# Required tools (pre-flight; the script aborts if any are missing):
#   - bandit    via apps/api/.venv (uv run bandit) — added in Story 9.1 T2
#   - semgrep   pipx install semgrep>=1.95
#   - pip-audit pipx install pip-audit>=2.7
#   - npm + node (standard on dev box)
#   - docker (for ghcr.io/zaproxy/zaproxy:stable; ~2.3GB image)
#   - uv (for uv export + uv run)
#   - jq (for severity-count predicates if you want to spot-check after run)
#
# Optional env:
#   AUDIT_DATE       override the dated subdir (default: $(date -u +%F))
#   PORTAL_URL       ZAP scan target (default: https://3d.ezop.ddns.net)
#   ZAP_MAX_MINUTES  ZAP -m flag (default: 5)
#   SKIP_<TOOL>=1    skip individual tools; e.g. SKIP_ZAP=1 audit-baseline.sh
#                    Tools: BANDIT, SEMGREP, PIP_AUDIT, NPM_AUDIT, ZAP
#
# Flags:
#   --help     print this header + tool checklist; exit 3
#
# Exit codes:
#   0  all selected tools produced output files
#   1  one or more tools failed to produce an output file
#   2  prerequisite check failed (missing tool, .190 unreachable, etc.)
#   3  --help invoked
#
# Example:
#   bash infra/scripts/audit-baseline.sh                # today
#   AUDIT_DATE=2026-05-21 bash infra/scripts/audit-baseline.sh
#   SKIP_ZAP=1 bash infra/scripts/audit-baseline.sh     # offline subset
#
set -Eeuo pipefail

#-----------------------------------------------------------------------------
# Path setup
#-----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

AUDIT_DATE="${AUDIT_DATE:-$(date -u +%F)}"
AUDIT_DIR="$REPO_DIR/_bmad-output/implementation-artifacts/audit-raw/$AUDIT_DATE"
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
ZAP_MAX_MINUTES="${ZAP_MAX_MINUTES:-5}"

#-----------------------------------------------------------------------------
# --help
#-----------------------------------------------------------------------------
if [[ "${1:-}" == "--help" ]]; then
  sed -n '1,55p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 3
fi

#-----------------------------------------------------------------------------
# Pre-flight tool checks
#-----------------------------------------------------------------------------
log() { printf '[audit-baseline] %s\n' "$*" >&2; }
fail() { log "ERROR: $*"; exit 2; }

require() {
  local name="$1" cmd="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "missing tool: $name (cmd: $cmd)"
  fi
}

require "uv"        uv
require "semgrep"   semgrep
require "pip-audit" pip-audit
require "npm"       npm
require "docker"    docker
require "jq"        jq

# Bandit lives inside the apps/api venv (uv-installed dev dep).
if ! (cd "$REPO_DIR/apps/api" && uv run --no-sync bandit --version >/dev/null 2>&1); then
  fail "bandit not available in apps/api/.venv — run 'uv sync --extra dev' first"
fi

mkdir -p "$AUDIT_DIR"
log "audit dir: $AUDIT_DIR"

FAILED_TOOLS=()

#-----------------------------------------------------------------------------
# AC3 — bandit (apps/api + workers/render)
#-----------------------------------------------------------------------------
run_bandit() {
  log "bandit — apps/api"
  (cd "$REPO_DIR/apps/api" && \
    uv run bandit -r app -f txt -o "$AUDIT_DIR/bandit-apps-api.txt") || true
  log "bandit — workers/render"
  (cd "$REPO_DIR/workers/render" && \
    uv run bandit -r render -f txt -o "$AUDIT_DIR/bandit-workers-render.txt") || true
  [[ -s "$AUDIT_DIR/bandit-apps-api.txt" ]] || FAILED_TOOLS+=(bandit-apps-api)
  [[ -s "$AUDIT_DIR/bandit-workers-render.txt" ]] || FAILED_TOOLS+=(bandit-workers-render)
}

#-----------------------------------------------------------------------------
# AC4 — semgrep (apps/api + apps/web + workers/render)
#-----------------------------------------------------------------------------
run_semgrep() {
  log "semgrep — apps/api + apps/web + workers/render"
  (cd "$REPO_DIR" && \
    semgrep --config auto --config p/owasp-top-ten --exclude node_modules \
      --json --output "$AUDIT_DIR/semgrep.json" \
      apps/api apps/web workers/render) || true
  [[ -s "$AUDIT_DIR/semgrep.json" ]] || FAILED_TOOLS+=(semgrep)
}

#-----------------------------------------------------------------------------
# AC5 — pip-audit (apps/api + workers/render production deps only)
#-----------------------------------------------------------------------------
run_pip_audit() {
  log "pip-audit — apps/api (prod deps)"
  (cd "$REPO_DIR/apps/api" && \
    pip-audit --requirement <(uv export --no-dev --no-hashes 2>/dev/null) \
      -o "$AUDIT_DIR/pip-audit-apps-api.txt") || true
  log "pip-audit — workers/render (prod deps)"
  (cd "$REPO_DIR/workers/render" && \
    pip-audit --requirement <(uv export --no-dev --no-hashes 2>/dev/null) \
      -o "$AUDIT_DIR/pip-audit-workers-render.txt") || true
  [[ -s "$AUDIT_DIR/pip-audit-apps-api.txt" ]] || FAILED_TOOLS+=(pip-audit-apps-api)
  [[ -s "$AUDIT_DIR/pip-audit-workers-render.txt" ]] || FAILED_TOOLS+=(pip-audit-workers-render)
}

#-----------------------------------------------------------------------------
# AC6 — npm audit (apps/web)
#-----------------------------------------------------------------------------
run_npm_audit() {
  log "npm audit — apps/web"
  (cd "$REPO_DIR/apps/web" && \
    npm audit --audit-level=moderate --json > "$AUDIT_DIR/npm-audit.json") \
    || true  # npm audit exits non-zero when findings exist
  [[ -s "$AUDIT_DIR/npm-audit.json" ]] || FAILED_TOOLS+=(npm-audit)
}

#-----------------------------------------------------------------------------
# AC7 — OWASP ZAP baseline (passive + light-active)
#-----------------------------------------------------------------------------
run_zap() {
  log "ZAP baseline — $PORTAL_URL (max ${ZAP_MAX_MINUTES} min)"
  docker run --rm \
    -v "$AUDIT_DIR:/zap/wrk:rw" \
    --user "$(id -u):$(id -g)" \
    ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
    -t "$PORTAL_URL" \
    -r zap-baseline.html \
    -J zap-baseline.json \
    -m "$ZAP_MAX_MINUTES" || true  # zap-baseline.py exits 2 on WARNs
  [[ -s "$AUDIT_DIR/zap-baseline.html" ]] || FAILED_TOOLS+=(zap-html)
  [[ -s "$AUDIT_DIR/zap-baseline.json" ]] || FAILED_TOOLS+=(zap-json)
}

#-----------------------------------------------------------------------------
# AC8 — tool versions
#-----------------------------------------------------------------------------
write_tool_versions() {
  {
    echo "bandit: $(cd "$REPO_DIR/apps/api" && uv run bandit --version 2>/dev/null | head -1)"
    echo "semgrep: $(semgrep --version 2>&1)"
    echo "pip-audit: $(pip-audit --version 2>&1)"
    echo "npm: $(npm --version 2>&1) / node: $(node --version 2>&1)"
    echo "zaproxy: $(docker run --rm ghcr.io/zaproxy/zaproxy:stable zap.sh -version 2>&1 | tail -1)"
    echo "docker: $(docker --version 2>&1)"
    echo "uv: $(uv --version 2>&1)"
    echo "pipx: $(pipx --version 2>&1 || echo 'not installed')"
    echo "git HEAD: $(cd "$REPO_DIR" && git rev-parse HEAD)"
    echo "git branch: $(cd "$REPO_DIR" && git rev-parse --abbrev-ref HEAD)"
    echo "scan date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$AUDIT_DIR/tool-versions.txt"
}

#-----------------------------------------------------------------------------
# AC10 — reproducers.sh (copy from infra/scripts template — kept in lockstep)
#-----------------------------------------------------------------------------
write_reproducers() {
  cat > "$AUDIT_DIR/reproducers.sh" <<'REPRO'
#!/usr/bin/env bash
# Single-tool reproducer commands — re-runs one tool against the same source
# tree. Generated by infra/scripts/audit-baseline.sh; mirrors AC3-AC7.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
run_bandit() {
  (cd "$REPO_DIR/apps/api" && uv run bandit -r app -f txt -o "$SCRIPT_DIR/bandit-apps-api.txt") || true
  (cd "$REPO_DIR/workers/render" && uv run bandit -r render -f txt -o "$SCRIPT_DIR/bandit-workers-render.txt") || true
}
run_semgrep() {
  (cd "$REPO_DIR" && semgrep --config auto --config p/owasp-top-ten --exclude node_modules \
    --json --output "$SCRIPT_DIR/semgrep.json" apps/api apps/web workers/render)
}
run_pip_audit() {
  (cd "$REPO_DIR/apps/api" && pip-audit --requirement <(uv export --no-dev --no-hashes 2>/dev/null) \
    -o "$SCRIPT_DIR/pip-audit-apps-api.txt") || true
  (cd "$REPO_DIR/workers/render" && pip-audit --requirement <(uv export --no-dev --no-hashes 2>/dev/null) \
    -o "$SCRIPT_DIR/pip-audit-workers-render.txt") || true
}
run_npm_audit() {
  (cd "$REPO_DIR/apps/web" && npm audit --audit-level=moderate --json > "$SCRIPT_DIR/npm-audit.json") || true
}
run_zap() {
  docker run --rm -v "$SCRIPT_DIR:/zap/wrk:rw" --user "$(id -u):$(id -g)" \
    ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
    -t https://3d.ezop.ddns.net -r zap-baseline.html -J zap-baseline.json -m 5 || true
}
case "${1:-all}" in
  bandit) run_bandit ;;
  semgrep) run_semgrep ;;
  pip-audit) run_pip_audit ;;
  npm-audit) run_npm_audit ;;
  zap) run_zap ;;
  all) run_bandit; run_semgrep; run_pip_audit; run_npm_audit; run_zap ;;
  *) echo "unknown tool: $1 (bandit|semgrep|pip-audit|npm-audit|zap|all)" >&2; exit 2 ;;
esac
REPRO
  chmod +x "$AUDIT_DIR/reproducers.sh"
}

#-----------------------------------------------------------------------------
# Run selected tools (SKIP_<TOOL>=1 overrides)
#-----------------------------------------------------------------------------
[[ "${SKIP_BANDIT:-}"    == "1" ]] && log "SKIP bandit"    || run_bandit
[[ "${SKIP_SEMGREP:-}"   == "1" ]] && log "SKIP semgrep"   || run_semgrep
[[ "${SKIP_PIP_AUDIT:-}" == "1" ]] && log "SKIP pip-audit" || run_pip_audit
[[ "${SKIP_NPM_AUDIT:-}" == "1" ]] && log "SKIP npm-audit" || run_npm_audit
[[ "${SKIP_ZAP:-}"       == "1" ]] && log "SKIP zap"       || run_zap

write_tool_versions
write_reproducers

#-----------------------------------------------------------------------------
# Summary
#-----------------------------------------------------------------------------
log "outputs in: $AUDIT_DIR"
ls -1 "$AUDIT_DIR" | sed 's/^/  /' >&2

if (( ${#FAILED_TOOLS[@]} > 0 )); then
  log "FAILED tools: ${FAILED_TOOLS[*]}"
  exit 1
fi

log "all selected tools produced output files."
exit 0
