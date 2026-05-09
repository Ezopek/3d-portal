#!/usr/bin/env bash
# Manual recovery path for source-map upload to the homelab GlitchTip.
#
# As of Story 1.5 (commit 26f0f0b), the active source-map upload runs via
# `@sentry/vite-plugin` INSIDE the docker build stage. This script is the
# documented FALLBACK (FR25, FR26) — a one-command recovery for cases where
# the in-build plugin is unavailable, off, or failed mid-build:
#   - GlitchTip backend issue #299 re-emerges (artifactbundle/assemble 404).
#   - Transient GlitchTip 5xx during a deploy.
#   - Auth token expired between rotation cycles.
#   - Operator deliberately runs a fallback-mode build (Story 1.5 reverted).
#
# The script uses the official `glitchtip-cli` (Rust) which talks the
# chunk-upload protocol GlitchTip expects. Stores artifacts as debug-id-keyed
# bundles via /api/0/organizations/{org}/chunk-upload/, resolved by the
# symbolicator at event time.
#
# The CLI binary is downloaded once into ~/.cache/glitchtip-cli/ and pinned
# by SHA-256 — no system install needed, no surprises across versions.
#
# RELEASE identity (FR26): computed as `${pkg.version}+${git_short_sha}` —
# matches `apps/web/src/release.ts` and the in-build plugin's release.name.
# Drift-impossible by construction: both pipelines read the SAME
# apps/web/package.json#version + `git rev-parse --short HEAD`.
#
# Required env (read from infra/.env on dev box):
#   GLITCHTIP_AUTH_TOKEN  - long-lived token, project:write + project:releases scopes
#   GLITCHTIP_ORG_SLUG    - org slug in GlitchTip (default: homelab)
#
# Optional:
#   GLITCHTIP_PROJECT_SLUG - project slug (default: 3d-portal)
#   GLITCHTIP_URL          - GlitchTip base URL (default: http://192.168.2.190:8800
#                             — internal LAN, avoids the public nginx proxy's
#                             body-size limits on multi-MB sourcemaps)
#   DIST_DIR               - dist directory to upload (default: apps/web/dist)
#
# Exit codes:
#   0 - success (CLI uploaded artifact bundle; release registered)
#   1 - generic / unexpected error (default `set -e`; dist not found;
#       sha256 mismatch on CLI binary; git/node/python lookup failure)
#   2 - GlitchTip unreachable (CLI returned network/5xx error)
#   3 - auth/scope failure (CLI returned 401/403; check token + scopes)
#
# Example invocation (from repo root, with infra/.env exported):
#
#   set -a; source infra/.env; set +a
#   cd apps/web && npm run build && cd ../..
#   bash infra/scripts/upload-sourcemaps.sh
#
# Help:
#   bash infra/scripts/upload-sourcemaps.sh --help
#
# Recovery context (FR25, architecture Decision E rejected-alternative):
#   "Every replacement keeps its predecessor as documented manual recovery
#   for one release cycle." This script IS that documented manual recovery.

set -euo pipefail

# --- Help flag --------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  # Reprint the header comment block (everything from line 2 up to the first
  # blank line after `# Help:` block) without the leading `# `. Single source
  # of truth — the script's docstring IS its help text.
  sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'
  exit 0
fi

# --- Compute paths and RELEASE expression ----------------------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST_DIR="${DIST_DIR:-$REPO_DIR/apps/web/dist}"
GLITCHTIP_URL="${GLITCHTIP_URL:-http://192.168.2.190:8800}"
PROJECT_SLUG="${GLITCHTIP_PROJECT_SLUG:-3d-portal}"

: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"
: "${GLITCHTIP_ORG_SLUG:?missing in infra/.env}"

# RELEASE identity = `${pkg.version}+${git_short_sha}` — same expression as
# apps/web/src/release.ts (which goes through Vite `define` to the runtime
# SDK and the in-build plugin's release.name). Reading directly from
# package.json + git on the host keeps both pipelines drift-impossible.
PKG_VERSION="$(node -p "require('$REPO_DIR/apps/web/package.json').version" 2>/dev/null \
  || python3 -c "import json; print(json.load(open('$REPO_DIR/apps/web/package.json'))['version'])")"
GIT_SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
RELEASE="${PKG_VERSION}+${GIT_SHA}"

if [[ ! -d "$DIST_DIR/assets" ]]; then
  echo "✗ $DIST_DIR/assets not found — did 'npm run build' run?" >&2
  exit 1
fi

# --- Resolve CLI binary -----------------------------------------------------
CLI_VERSION="v0.1.0"
CLI_SHA256="aa98c98de1a95e1840afbb14f0b11889feb2fbf9d71b278e19e034a30b4623b7"
CLI_URL="https://gitlab.com/glitchtip/glitchtip-cli/-/jobs/artifacts/${CLI_VERSION}/raw/artifacts/glitchtip-cli-linux-x86_64?job=build-linux-x86_64"
CLI_CACHE_DIR="${HOME}/.cache/glitchtip-cli"
CLI_BIN="${CLI_CACHE_DIR}/glitchtip-cli-${CLI_VERSION}"

ensure_cli() {
  if [[ -x "$CLI_BIN" ]] && sha256sum "$CLI_BIN" 2>/dev/null | grep -q "^${CLI_SHA256}"; then
    return 0
  fi
  echo "→ Downloading glitchtip-cli ${CLI_VERSION}"
  mkdir -p "$CLI_CACHE_DIR"
  curl -fsSL "$CLI_URL" -o "${CLI_BIN}.tmp"
  local actual
  actual=$(sha256sum "${CLI_BIN}.tmp" | awk '{print $1}')
  if [[ "$actual" != "$CLI_SHA256" ]]; then
    rm -f "${CLI_BIN}.tmp"
    echo "✗ glitchtip-cli sha256 mismatch: got $actual, expected $CLI_SHA256" >&2
    exit 1
  fi
  chmod +x "${CLI_BIN}.tmp"
  mv "${CLI_BIN}.tmp" "$CLI_BIN"
}

ensure_cli

# --- Run upload --------------------------------------------------------------
# Inject debug IDs into .js + .js.map so symbolicator can match by ID, then
# upload as an artifact bundle. URL prefix `~/assets` matches the deployed
# bundle path (http://.../assets/index-XXX.js) for legacy by-name fallback.

export SENTRY_URL="$GLITCHTIP_URL"
export SENTRY_AUTH_TOKEN="$GLITCHTIP_AUTH_TOKEN"
export SENTRY_ORG="$GLITCHTIP_ORG_SLUG"

echo "→ Inject debug IDs into $DIST_DIR"
"$CLI_BIN" sourcemaps inject "$DIST_DIR"
inject_rc=$?

echo "→ Upload sourcemaps to GlitchTip (release: $RELEASE)"
"$CLI_BIN" -p "$PROJECT_SLUG" sourcemaps upload \
  --release "$RELEASE" \
  --url-prefix '~/assets' \
  "$DIST_DIR/assets"
upload_rc=$?

# Exit-code translation: glitchtip-cli's exit code is propagated as-is, but
# `set -e` would have aborted before reaching here on non-zero. Re-check
# explicitly so the documented exit-code map (0/1/2/3) is enforced even when
# `set +e` callers run this script.
if [[ "$inject_rc" -ne 0 ]]; then
  echo "✗ glitchtip-cli sourcemaps inject exited $inject_rc" >&2
  exit "$inject_rc"
fi
if [[ "$upload_rc" -ne 0 ]]; then
  echo "✗ glitchtip-cli sourcemaps upload exited $upload_rc" >&2
  exit "$upload_rc"
fi

echo "Done. Uploaded artifacts for $RELEASE."
