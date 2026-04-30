#!/usr/bin/env bash
# Run nightly on .190 via cron. Backs up SQLite portal.db with 30-day retention.

set -euo pipefail

SRC="/mnt/raid/3d-portal-state/portal.db"
DEST_DIR="/mnt/raid/3d-portal-state/backups"
RETENTION_DAYS=30

mkdir -p "$DEST_DIR"
DATE=$(date +%F)
sqlite3 "$SRC" ".backup '$DEST_DIR/portal-$DATE.db'"
find "$DEST_DIR" -type f -name 'portal-*.db' -mtime "+$RETENTION_DAYS" -delete
