#!/usr/bin/env bash
# Build images, push to .190, restart compose stack.
# Run from `~/repos/3d-portal/`.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_DIR="${PORTAL_COMPOSE_DIR:-/mnt/raid/docker-compose/3d-portal}"
TARGET_HOST="${PORTAL_HOST:-ezop@192.168.2.190}"
SSH_PORT="${PORTAL_SSH_PORT:-30022}"
VERSION="${PORTAL_VERSION:-0.1.0}"
LOCAL_ENV="$REPO_DIR/infra/.env"

# Local docker compose build still needs all ${VAR} references resolved
# (volumes, image tags, build args). Pull the canonical .env from .190 if
# we don't already have a local copy.
if [[ ! -f "$LOCAL_ENV" ]]; then
  echo "→ infra/.env absent locally, fetching from $TARGET_HOST"
  scp -P "$SSH_PORT" "$TARGET_HOST:$COMPOSE_DIR/.env" "$LOCAL_ENV"
  chmod 600 "$LOCAL_ENV"
fi

echo "→ Build images locally (tag: $VERSION)"
cd "$REPO_DIR"
docker compose --env-file "$LOCAL_ENV" -f infra/docker-compose.yml build

echo "→ Save and ship images to $TARGET_HOST"
docker save \
  "portal-api:$VERSION" \
  "portal-render:$VERSION" \
  "portal-web:$VERSION" \
  | ssh -p "$SSH_PORT" "$TARGET_HOST" "docker load"

echo "→ Sync compose"
ssh -p "$SSH_PORT" "$TARGET_HOST" "mkdir -p $COMPOSE_DIR"
scp -P "$SSH_PORT" infra/docker-compose.yml "$TARGET_HOST:$COMPOSE_DIR/docker-compose.yml"
# .env must already exist on the host; never push it from here.

echo "→ Restart stack"
ssh -p "$SSH_PORT" "$TARGET_HOST" "cd $COMPOSE_DIR && docker compose --env-file .env up -d"

echo "→ Run alembic migrations"
ssh -p "$SSH_PORT" "$TARGET_HOST" "cd $COMPOSE_DIR && docker compose run --rm api alembic upgrade head"

echo "Done."
