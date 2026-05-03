#!/usr/bin/env bash
# Sync catalog from Windows / WSL → .190 portal data volume, then refresh
# the portal's in-memory index.
# Run from WSL after a catalog change.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$REPO_DIR/infra/.env"

SOURCE="${PORTAL_CATALOG_SRC:-/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/}"
DEST="${PORTAL_CATALOG_DEST:-ezop@192.168.2.190:/mnt/raid/3d-portal-data/}"
SSH_PORT="${PORTAL_SSH_PORT:-30022}"
# Default to LAN URL — works without VPN, no TLS dance, and parallels
# the rsync target on the same box.
PORTAL_URL="${PORTAL_URL:-http://192.168.2.190:8090}"

echo "→ rsync $SOURCE → $DEST (ssh port $SSH_PORT)"
RSYNC_ARGS=(
  -avz --delete -e "ssh -p $SSH_PORT"
  --exclude='.git/' --exclude='.claude/' --exclude='.codex/'
  --exclude='.playwright-mcp/' --exclude='.superpowers/'
  --exclude='docs/' --exclude='AGENTS.md' --exclude='CLAUDE.md'
  --exclude='_archive/'
  --include='*/'
  --include='_index/index.json'
  --include='**/*.[sS][tT][lL]' --include='**/*.[3][mM][fF]'
  --include='**/*.[sS][tT][eE][pP]'
  --include='**/images/**' --include='**/prints/**'
  --exclude='*'
)
# Auto-retry on exit 23 (partial transfer). On WSL/Nextcloud this is
# almost always a Cloud Files API placeholder: a freshly-modified
# directory hasn't been hydrated yet, so readdir() returns EINVAL. The
# failed listing itself triggers Windows-side hydration, so the next
# attempt usually succeeds.
attempt=1
max_attempts=3
while true; do
  if rsync "${RSYNC_ARGS[@]}" "$SOURCE" "$DEST"; then
    break
  fi
  rc=$?
  if [[ $rc -ne 23 || $attempt -ge $max_attempts ]]; then
    exit "$rc"
  fi
  attempt=$((attempt + 1))
  echo "→ rsync exit 23 (Nextcloud placeholder?), retry $attempt/$max_attempts"
done

read_env_var() {
  # Cherry-pick a single variable from infra/.env without sourcing the file.
  # `source` would choke on values containing unquoted spaces (e.g. OTLP
  # headers like "authorization=Bearer <token>").
  [[ -f "$ENV_FILE" ]] || return
  grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-
}

ADMIN_EMAIL="${ADMIN_EMAIL:-$(read_env_var ADMIN_EMAIL)}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(read_env_var ADMIN_PASSWORD)}"

if [[ -z "$ADMIN_EMAIL" || -z "$ADMIN_PASSWORD" ]]; then
  echo "→ Skipped refresh-catalog: ADMIN_EMAIL / ADMIN_PASSWORD not set" \
       "(env vars or $ENV_FILE)"
  exit 0
fi

echo "→ Authenticating against $PORTAL_URL/api/auth/login"
LOGIN_PAYLOAD="$(jq -nc --arg e "$ADMIN_EMAIL" --arg p "$ADMIN_PASSWORD" \
                 '{email:$e, password:$p}')"
TOKEN="$(curl -fsS -H "Content-Type: application/json" \
              -d "$LOGIN_PAYLOAD" \
              "$PORTAL_URL/api/auth/login" \
         | jq -r '.access_token')"

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "→ Login failed; skipping refresh-catalog" >&2
  exit 1
fi

echo "→ POST $PORTAL_URL/api/admin/refresh-catalog"
curl -fsS -H "Authorization: Bearer $TOKEN" \
     -X POST "$PORTAL_URL/api/admin/refresh-catalog"
echo
