#!/usr/bin/env bash
# Upload built sourcemaps + their paired .js files from apps/web/dist/ to
# GlitchTip for the current release. Run AFTER `pnpm build` (so dist/ exists)
# and BEFORE shipping the docker image.
#
# Uses the official `glitchtip-cli` (Rust) which talks the chunk-upload
# protocol GlitchTip expects. The legacy `releases/{version}/files/` POST
# endpoint is not implemented on this GlitchTip version (returns 405); the
# CLI stores artifacts as debug-id-keyed bundles via /api/0/organizations/
# {org}/chunk-upload/ which the symbolicator resolves at event time.
#
# The CLI binary is downloaded once into ~/.cache/glitchtip-cli/ and pinned
# by SHA-256 — no system install needed, no surprises across versions.
#
# Required env (read from infra/.env by deploy.sh):
#   GLITCHTIP_AUTH_TOKEN  - long-lived token, project:write + project:releases scopes
#   GLITCHTIP_ORG_SLUG    - org slug in GlitchTip
#   PORTAL_VERSION        - release version (matches Sentry SDK release tag)
#
# Optional:
#   GLITCHTIP_PROJECT_SLUG - defaults to 3d-portal
#   GLITCHTIP_URL          - defaults to http://192.168.2.190:8800 (internal,
#                            avoids the public nginx proxy's 1MB body limit
#                            on multi-MB sourcemaps)
#   DIST_DIR               - defaults to apps/web/dist

set -euo pipefail

DIST_DIR="${DIST_DIR:-apps/web/dist}"
GLITCHTIP_URL="${GLITCHTIP_URL:-http://192.168.2.190:8800}"
PROJECT_SLUG="${GLITCHTIP_PROJECT_SLUG:-3d-portal}"

: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"
: "${GLITCHTIP_ORG_SLUG:?missing in infra/.env}"
: "${PORTAL_VERSION:?missing in infra/.env}"

if [[ ! -d "$DIST_DIR/assets" ]]; then
  echo "✗ $DIST_DIR/assets not found — did pnpm build run?" >&2
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

echo "→ Upload sourcemaps to GlitchTip (release: $PORTAL_VERSION)"
"$CLI_BIN" -p "$PROJECT_SLUG" sourcemaps upload \
  --release "$PORTAL_VERSION" \
  --url-prefix '~/assets' \
  "$DIST_DIR/assets"

echo "Done. Uploaded artifacts for $PORTAL_VERSION."
