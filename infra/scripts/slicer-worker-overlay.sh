#!/usr/bin/env bash
# SW-DEPLOY-1 — slicer-worker overlay deploy/rebuild + in-container smoke.
#
# WHY THIS EXISTS
# ----------------
# infra/scripts/deploy.sh rebuilds/restarts only the BASE stack
# (portal-api / portal-web / portal-render). The slicer-worker is a
# configs-side OVERLAY: image `portal-slicer-worker:<ver>` built
# `FROM portal-api:<ver>` from a recipe that lives in the configs repo on
# the target host, NOT in this repo. So any deploy that bumps the
# portal-api base image (every apps/api/** change — the slicer modules are
# a subset) ships "green" while the running slicer-worker keeps the OLD
# image and silently executes stale `app.modules.slicer.*` code. That skew
# only surfaces when a slice/estimate job runs — well after deploy is
# reported done. This hit Story 32.3 and is the open runtime gate for
# 32.4/32.5 (see _bmad-output/implementation-artifacts/deferred-work.md
# SW-DEPLOY-1 and epic-32-retro-2026-06-02.md §4/§5).
#
# BOUNDARY (HC2 repo<->configs)
# ------------------------------
# The overlay RECIPE (Dockerfile + compose file) is owned by the configs
# repo and lives at $SLICER_OVERLAY_RECIPE_DIR on the target host. This
# script NEVER vendors or reproduces it — it only references those paths
# over SSH. If the recipe paths move, change the env-var defaults below;
# do not copy the recipe into this repo.
#
# SUBCOMMANDS
#   detect [RANGE]   exit 0 = overlay rebuild needed, exit 10 = not needed.
#   rebuild          ssh: docker build the overlay image + compose up the service.
#   smoke            ssh: docker compose exec -T <service> python - <in-container smoke>.
#   deploy [RANGE]   detect -> (needed) rebuild + smoke ; (not needed) skip.
#
# KEY ENV (all overridable; defaults mirror deploy.sh + deferred-work.md):
#   PORTAL_HOST/PORTAL_SSH_PORT/PORTAL_VERSION/PORTAL_COMPOSE_DIR
#   SLICER_OVERLAY_RECIPE_DIR / SLICER_OVERLAY_COMPOSE_FILE / SLICER_OVERLAY_DOCKERFILE
#   SLICER_WORKER_IMAGE / SLICER_WORKER_SERVICE / SLICER_WORKER_PROFILE
#   SLICER_TRIGGER_GLOBS  (space-separated path prefixes; default "apps/api/")
#   FORCE_SLICER_WORKER_REBUILD=1   force "needed" (manual 32.4/32.5 gate closure)
#   SKIP_SLICER_WORKER=1            hard opt-out (deploy exits 0, does nothing)
#   DRY_RUN=1                       print fully-resolved commands, run no ssh/docker
#   SLICER_REPO_DIR                 override repo root (tests; default = this repo)

set -euo pipefail

# --- Configuration (env-driven; defaults match deploy.sh + deferred-work.md) ---
REPO_DIR="${SLICER_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
TARGET_HOST="${PORTAL_HOST:-ezop@192.168.2.190}"
SSH_PORT="${PORTAL_SSH_PORT:-30022}"
VERSION="${PORTAL_VERSION:-0.1.0}"
COMPOSE_DIR="${PORTAL_COMPOSE_DIR:-/mnt/raid/docker-compose/3d-portal}"

# Configs-side recipe paths on the target host — referenced, never vendored.
RECIPE_DIR="${SLICER_OVERLAY_RECIPE_DIR:-/mnt/raid/configs/docker-compose-recipes/workers}"
OVERLAY_FILE="${SLICER_OVERLAY_COMPOSE_FILE:-$RECIPE_DIR/slicer-worker.yml}"
DOCKERFILE="${SLICER_OVERLAY_DOCKERFILE:-$RECIPE_DIR/slicer-worker.Dockerfile}"
IMAGE="${SLICER_WORKER_IMAGE:-portal-slicer-worker:$VERSION}"
SERVICE="${SLICER_WORKER_SERVICE:-slicer-worker}"
PROFILE="${SLICER_WORKER_PROFILE:-slicer-worker}"

# Detection contract: the overlay layers `FROM portal-api:<ver>`, so ANY change
# that rebuilds the portal-api image (every apps/api/** edit) requires the
# overlay to rebuild on the fresh base. The default points to THAT contract,
# not to a peer usage (magic-constant contract-pointing rule).
TRIGGER_GLOBS="${SLICER_TRIGGER_GLOBS:-apps/api/}"

# Exit code the "not needed" path contracts on (tests + deploy.sh rely on it).
readonly NOT_NEEDED=10

# In-container smoke payload (Story 32.3/32.4/32.5 skew surface). Single-quoted
# heredoc — NOT interpolated here; it runs inside the slicer-worker container.
read -r -d '' SMOKE_PY <<'PYEOF' || true
import importlib
import os
import subprocess
import sys

REQUIRED_MODULES = [
    "app.modules.slicer.gcode_parse",        # Story 32.3
    "app.modules.slicer.estimate_store",     # Story 32.3
    "app.modules.slicer.recompute",          # Story 32.4
    "app.modules.slicer.overrides",          # Story 32.5
    "app.modules.slicer.spoolman_invalidation",  # Story 32.5
]


def fail(msg: str) -> None:
    print("SLICER_WORKER_SMOKE_FAIL " + msg, file=sys.stderr)
    raise SystemExit(1)


# (a) importlib presence — the exact 32.3/32.4/32.5 skew surface.
for _m in REQUIRED_MODULES:
    try:
        importlib.import_module(_m)
    except Exception as exc:  # noqa: BLE001
        fail("import %s: %r" % (_m, exc))

# (b) Settings resolve non-empty via the cached app config.
from app.core.config import get_settings

_s = get_settings()
if not str(getattr(_s, "slicer_estimate_store_dir", "")).strip():
    fail("slicer_estimate_store_dir empty")
if not str(getattr(_s, "slicer_orca_bin", "")).strip():
    fail("slicer_orca_bin empty")

# (c) Orca binary smoke — present + executable + responds to --help. NO real
# slice is run (just prove the binary is reachable). A non-zero --help exit is
# acceptable; only not-found / timeout fail.
_orca = str(_s.slicer_orca_bin)
if not (os.path.isfile(_orca) and os.access(_orca, os.X_OK)):
    fail("orca bin not executable: %s" % _orca)
try:
    subprocess.run([_orca, "--help"], capture_output=True, timeout=30)
except FileNotFoundError:
    fail("orca bin not found at runtime: %s" % _orca)
except subprocess.TimeoutExpired:
    fail("orca --help timed out")

# (d) functional smoke — the modules import AND honour the current contract
# (catches a build that imports but is stale / signature-drifted).
from app.modules.slicer.gcode_parse import parse_gcode_metadata
from app.modules.slicer.overrides import map_filament_extra

if parse_gcode_metadata("; slicer-worker smoke\n") is None:
    fail("parse_gcode_metadata returned None")
if map_filament_extra({}) is None:
    fail("map_filament_extra returned None")

print(
    "SLICER_WORKER_SMOKE_OK modules=%d orca=%s estimate_store_dir=%s"
    % (len(REQUIRED_MODULES), _orca, _s.slicer_estimate_store_dir)
)
PYEOF

usage() {
  cat >&2 <<EOF
usage: slicer-worker-overlay.sh <detect|rebuild|smoke|deploy> [RANGE]
  detect [RANGE]   exit 0 if overlay rebuild needed, $NOT_NEEDED if not
  rebuild          rebuild + restart the overlay on \$PORTAL_HOST
  smoke            run the in-container import/Orca/parser smoke
  deploy [RANGE]   detect -> rebuild + smoke (or skip)
See the header of this file for env vars.
EOF
}

# Resolve the default deploy range from infra/.last-deploy-sha. Echoes
# "<sha>..HEAD" on success; non-zero (caller treats as unresolved -> needed).
resolve_default_range() {
  local state="$REPO_DIR/infra/.last-deploy-sha" sha
  [[ -f "$state" ]] || return 1
  sha="$(tr -d '[:space:]' < "$state")"
  [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || return 1
  git -C "$REPO_DIR" rev-parse --verify "${sha}^{commit}" >/dev/null 2>&1 || return 1
  printf '%s..HEAD' "$sha"
}

cmd_detect() {
  local range="${1:-}" changed f g

  if [[ -n "${FORCE_SLICER_WORKER_REBUILD:-}" ]]; then
    echo "[slicer-worker] FORCE_SLICER_WORKER_REBUILD set — overlay rebuild needed"
    return 0
  fi

  if [[ -z "$range" ]]; then
    range="$(resolve_default_range)" || range=""
  fi
  if [[ -z "$range" ]]; then
    echo "[slicer-worker] deploy range unresolved/empty — assuming overlay rebuild needed (safe direction)" >&2
    return 0
  fi

  if ! changed="$(git -C "$REPO_DIR" diff --name-only "$range" 2>/dev/null)"; then
    echo "[slicer-worker] could not diff '$range' — assuming overlay rebuild needed (safe direction)" >&2
    return 0
  fi

  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    # shellcheck disable=SC2086  # TRIGGER_GLOBS is intentionally space-split into prefixes
    for g in $TRIGGER_GLOBS; do
      if [[ "$f" == "$g"* ]]; then
        echo "[slicer-worker] '$f' matches trigger '$g' — overlay rebuild needed (portal-api base changed)"
        return 0
      fi
    done
  done <<< "$changed"

  echo "[slicer-worker] no portal-api/slicer-adjacent change in '$range' — overlay rebuild not needed"
  return "$NOT_NEEDED"
}

cmd_rebuild() {
  local build_cmd compose_cmd
  # Path vars are double-quoted in the REMOTE command (they may, in principle,
  # carry spaces if an operator overrides them); IMAGE/SERVICE/PROFILE are
  # docker identifiers (constrained charset, no spaces) so they stay bare —
  # which also keeps the DRY_RUN assertions (`-t <image>`, `--profile <p>`,
  # `up -d <svc>`) readable.
  build_cmd="docker build -f \"$DOCKERFILE\" -t $IMAGE \"$RECIPE_DIR\""
  compose_cmd="cd \"$COMPOSE_DIR\" && docker compose --env-file .env -f docker-compose.yml -f \"$OVERLAY_FILE\" --profile $PROFILE up -d $SERVICE"

  if [[ -n "${DRY_RUN:-}" ]]; then
    echo "[slicer-worker][dry-run] ssh -p $SSH_PORT $TARGET_HOST \"$build_cmd\""
    echo "[slicer-worker][dry-run] ssh -p $SSH_PORT $TARGET_HOST \"$compose_cmd\""
    return 0
  fi

  # FATAL on failure: a build/restart error must propagate (the caller runs
  # this directly under `set -e`, no `if !` wrapper). If `docker build` fails
  # and we swallowed it, `docker compose up` would restart the OLD image and
  # the presence-based smoke would pass against stale-but-present modules —
  # the exact silent skew this script exists to prevent.
  echo "→ [slicer-worker] rebuild $IMAGE on $TARGET_HOST from $DOCKERFILE"
  ssh -p "$SSH_PORT" "$TARGET_HOST" "$build_cmd"
  echo "→ [slicer-worker] (re)start overlay service '$SERVICE' (profile '$PROFILE')"
  ssh -p "$SSH_PORT" "$TARGET_HOST" "$compose_cmd"
  # Best-effort image-digest log for the deploy audit trail — the ONLY
  # intentionally non-fatal step (it must not mask a successful rebuild).
  ssh -p "$SSH_PORT" "$TARGET_HOST" \
    "docker image inspect $IMAGE --format 'slicer-worker image: {{.Id}}'" || true
}

cmd_smoke() {
  local exec_cmd
  exec_cmd="cd \"$COMPOSE_DIR\" && docker compose --env-file .env -f docker-compose.yml -f \"$OVERLAY_FILE\" --profile $PROFILE exec -T $SERVICE python -"

  if [[ -n "${DRY_RUN:-}" ]]; then
    echo "[slicer-worker][dry-run] ssh -p $SSH_PORT $TARGET_HOST \"$exec_cmd\" <<'PY'"
    printf '%s\n' "$SMOKE_PY"
    echo "PY"
    return 0
  fi

  echo "→ [slicer-worker] in-container smoke on '$SERVICE'"
  printf '%s\n' "$SMOKE_PY" | ssh -p "$SSH_PORT" "$TARGET_HOST" "$exec_cmd"
}

cmd_deploy() {
  local range="${1:-}" d

  if [[ -n "${SKIP_SLICER_WORKER:-}" ]]; then
    echo "[slicer-worker] SKIP_SLICER_WORKER set — skipping overlay rebuild + smoke"
    return 0
  fi

  set +e
  cmd_detect "$range"
  d=$?
  set -e

  if [[ "$d" -eq "$NOT_NEEDED" ]]; then
    echo "[slicer-worker] overlay rebuild not needed for this deploy — skipping"
    return 0
  elif [[ "$d" -ne 0 ]]; then
    echo "[slicer-worker] detect returned unexpected code $d — assuming rebuild needed (safe direction)" >&2
  fi

  # Needed. BOTH steps are fatal (run directly under `set -e`): a failed
  # rebuild must abort the deploy rather than silently leave the old image
  # running (a build failure that kept stale-but-present modules would still
  # pass the presence-based smoke — the precise silent skew this exists to
  # prevent), and a smoke failure means the worker is genuinely stale/broken.
  # The escape hatch for "the overlay isn't deployed on this host" is
  # SKIP_SLICER_WORKER=1, not a swallowed rebuild error.
  cmd_rebuild
  cmd_smoke
}

main() {
  local sub="${1:-}"
  [[ $# -gt 0 ]] && shift
  case "$sub" in
    detect)  cmd_detect "$@" ;;
    rebuild) cmd_rebuild "$@" ;;
    smoke)   cmd_smoke "$@" ;;
    deploy)  cmd_deploy "$@" ;;
    -h|--help|help) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
