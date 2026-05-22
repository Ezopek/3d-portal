#!/usr/bin/env bash
# Story 13.2 / Decision P — operator-supervised WebP-thumbnail backfill.
#
# Inventories every image/print ModelFile in the live deployment, checks the
# sibling `<storage_path>.thumb.webp` on disk, and either enqueues a
# `generate_thumbnail` arq job (default — fast, distributes work to the
# worker) or runs the Pillow pipeline inline (slower, deterministic).
#
# Idempotent: ModelFiles whose `.thumb.webp` sibling already exists are
# skipped without enqueueing anything. Safe to re-run.
#
# NOT auto-fired by infra/scripts/deploy.sh — operator runs once post-Story
# 13.2 deploy to populate variants for pre-pipeline uploads. The variant
# endpoint silently falls back to the original blob in the meantime, so
# delaying the backfill does NOT break the user-facing flow.
#
# Usage:
#   bash infra/scripts/backfill-thumbnails.sh                  # enqueue mode (default)
#   bash infra/scripts/backfill-thumbnails.sh --inline         # synchronous render
#   bash infra/scripts/backfill-thumbnails.sh --dry-run        # inventory only
#   bash infra/scripts/backfill-thumbnails.sh -- --verbose     # forward to Python
#
# Env (overrideable):
#   COMPOSE_FILE      default infra/docker-compose.yml
#   API_SERVICE       default api
#   SSH_TARGET        when set, run via SSH on the named host
#                     (e.g. ezope@192.168.2.190) — useful for one-shot remote
#                     execution from the operator workstation.
#
# Exit codes:
#   0  success (possibly with skipped files)
#   1  prerequisite or runtime error
#   2  invalid invocation

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.yml}"
API_SERVICE="${API_SERVICE:-api}"
SSH_TARGET="${SSH_TARGET:-}"

PASS_ARGS=()
while (($#)); do
  case "$1" in
    --inline | --dry-run | -v | --verbose)
      PASS_ARGS+=("$1")
      shift
      ;;
    --)
      shift
      PASS_ARGS+=("$@")
      break
      ;;
    -h | --help)
      sed -n '2,/^$/p' "$0"
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      echo "usage: $0 [--inline] [--dry-run] [--verbose]" >&2
      exit 2
      ;;
  esac
done

REMOTE_CMD=(docker compose -f "$COMPOSE_FILE" exec -T "$API_SERVICE"
  python -m scripts.enqueue_thumbnail_backfill "${PASS_ARGS[@]}")

if [[ -n "$SSH_TARGET" ]]; then
  echo "==> remote: ssh $SSH_TARGET ${REMOTE_CMD[*]}"
  ssh "$SSH_TARGET" "cd /home/ezope/3d-portal && ${REMOTE_CMD[*]}"
else
  echo "==> local: ${REMOTE_CMD[*]}"
  "${REMOTE_CMD[@]}"
fi
