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

# --- Stale-verify tripwire (Story 3.2; FR16) -----------------------------
# Warn loud + non-fatal at the START if the previous deploy did NOT record
# a successful verify. Reads `infra/.last-verify` mtime vs the current
# HEAD's commit timestamp (chosen per epics.md:559 — simplest mechanism, no
# new state file needed; HEAD time is monotonically tied to "the deploy
# being performed now"). Older mtime → previous deploy's verify never
# landed (or wasn't recent) → operator sees yellow warning.
last_verify_path="$REPO_DIR/infra/.last-verify"
if [[ -f "$last_verify_path" ]]; then
  last_verify_mtime=$(stat -c %Y "$last_verify_path")
  head_timestamp=$(git -C "$REPO_DIR" log -1 --format=%ct HEAD 2>/dev/null || echo 0)
  if (( last_verify_mtime < head_timestamp )); then
    printf '\033[33m⚠ stale verify: previous deploy did not record a successful verification (last verify: %s; last commit: %s)\033[0m\n' \
      "$(date -u -d "@$last_verify_mtime" +%Y-%m-%dT%H:%M:%SZ)" \
      "$(date -u -d "@$head_timestamp" +%Y-%m-%dT%H:%M:%SZ)" >&2
  fi
else
  printf '\033[34m→ verify history not yet established (no infra/.last-verify); first run after this deploy will populate it\033[0m\n'
fi

echo "→ Build images locally (tag: $VERSION)"
cd "$REPO_DIR"
VITE_GIT_COMMIT="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
VITE_BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Resolve build host on the dev box BEFORE the docker build container
# inherits the env. Without this the inner BuildKit container would supply
# its own ephemeral hostname (e.g. `buildkitsandbox`), defeating the
# `host.name` static identity tag (Story 2.2 / architecture Decision G).
# Honor an operator-set VITE_BUILD_HOST if already exported, else fall
# back to `hostname`.
VITE_BUILD_HOST="${VITE_BUILD_HOST:-$(hostname 2>/dev/null || echo unknown)}"
export VITE_GIT_COMMIT VITE_BUILD_TIME VITE_BUILD_HOST
# BuildKit is required for the --mount=type=secret syntax used in
# apps/web/Dockerfile (mounts SENTRY_AUTH_TOKEN for the Sentry vite-plugin
# without persisting it in any image layer).
export DOCKER_BUILDKIT=1
echo "  release identity: ${PORTAL_VERSION:-$VERSION}+${VITE_GIT_COMMIT}, built at ${VITE_BUILD_TIME}"
docker compose --env-file "$LOCAL_ENV" -f infra/docker-compose.yml build

# Source-map upload now happens via @sentry/vite-plugin INSIDE the docker
# build stage (see apps/web/vite.config.ts + apps/web/Dockerfile's
# `--mount=type=secret,id=sentry_token` line). For documented manual
# recovery (FR25), use `bash infra/scripts/upload-sourcemaps.sh --help`.

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

# --- Post-deploy verify (Story 3.2; FR15) --------------------------------
# Non-fatal gate: deploy success is decoupled from verify outcome
# (NFR-R3). Capture the FR12 exit code (0/1/2/3/4) and print an exit-code-
# mapped warning. Deploy exits 0 regardless of verify_exit; the verify
# signal lands in (a) the printed warning here, (b) infra/.last-verify
# (Story 3.1 fail_verify writes FAILED on every non-zero exit), and
# (c) a synthetic GlitchTip event for codes 1/3 (Story 3.1 emit_alarm).
echo "→ Verify post-deploy symbolication"
verify_exit=0
bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || verify_exit=$?
case "$verify_exit" in
  0) echo "✓ verify OK" ;;
  1) printf '\033[31m⚠ verify FAILED: symbolication broken (top frame regex mismatch)\033[0m\n' >&2 ;;
  2) printf '\033[31m⚠ verify FAILED: GlitchTip unreachable\033[0m\n' >&2 ;;
  3) printf '\033[31m⚠ verify FAILED: auth/scope failure — token rotation needed?\033[0m\n' >&2 ;;
  4) printf '\033[31m⚠ verify FAILED: timeout (no matching event within 30s)\033[0m\n' >&2 ;;
  *) printf '\033[31m⚠ verify FAILED: unexpected exit %s\033[0m\n' "$verify_exit" >&2 ;;
esac

echo "Done."
