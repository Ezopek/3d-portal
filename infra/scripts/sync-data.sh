#!/usr/bin/env bash
# Sync catalog from Windows / WSL → .190 portal data volume.
# Run from WSL after a catalog change.

set -euo pipefail

SOURCE="${PORTAL_CATALOG_SRC:-/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/}"
DEST="${PORTAL_CATALOG_DEST:-ezop@192.168.2.190:/mnt/raid/3d-portal-data/}"
SSH_PORT="${PORTAL_SSH_PORT:-30022}"
PORTAL_URL="${PORTAL_URL:-https://3d.ezop.ddns.net}"
PORTAL_AUTH="${PORTAL_AUTH:-}"
PORTAL_ADMIN_TOKEN="${PORTAL_ADMIN_TOKEN:-}"

echo "→ rsync $SOURCE → $DEST (ssh port $SSH_PORT)"
rsync -avz --delete -e "ssh -p $SSH_PORT" \
  --exclude='.git/' --exclude='.claude/' --exclude='.codex/' \
  --exclude='.playwright-mcp/' --exclude='.superpowers/' \
  --exclude='docs/' --exclude='AGENTS.md' --exclude='CLAUDE.md' \
  --include='*/' \
  --include='_index/index.json' \
  --include='**/*.stl' --include='**/*.3mf' --include='**/*.step' \
  --include='**/images/**' --include='**/prints/**' \
  --exclude='*' \
  "$SOURCE" "$DEST"

if [[ -n "$PORTAL_ADMIN_TOKEN" ]]; then
  echo "→ POST $PORTAL_URL/api/admin/refresh-catalog"
  curl -fsS -u "${PORTAL_AUTH}" \
    -H "Authorization: Bearer ${PORTAL_ADMIN_TOKEN}" \
    -X POST "$PORTAL_URL/api/admin/refresh-catalog" || true
else
  echo "→ Skipped refresh-catalog: PORTAL_ADMIN_TOKEN not set"
fi
