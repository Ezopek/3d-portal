#!/usr/bin/env bash
# Explicit FULL closeout/merge gate (the repo's local CI-equivalent — there is
# no hosted CI). Runs every per-story quality gate listed in AGENTS.md against
# the working tree and exits 0 only when ALL gates are green. Intended for:
#   - The required gate before a story-branch ff-merge to `main` / deploy
#   - One-shot baseline audits after long autonomous batches
#   - Tee-loggable evidence runs:
#       mkdir -p .hermes/run-logs && infra/scripts/check-all.sh 2>&1 | tee .hermes/run-logs/check-all-$(date +%Y%m%d_%H%M%S).log
#
# This is NO LONGER the default `.githooks/pre-push` hook. That hook is now a
# lean, low-output transport gate (ruff/typecheck/lint/cheap-drift only); the
# heavy stages below (production build, vitest, pytest, visual regression) run
# here, not on every push. See AGENTS.md § "Pre-push hook policy & gate
# evidence". Do not re-point pre-push at this aggregate — its multi-megabyte
# stdout is what produced the SIGPIPE/exit-141-after-success pushes.
#
# Order is fast-to-slow so failures surface early. The script does NOT spawn
# Vite for `test:visual`; that step starts its own dev server via Playwright's
# `webServer` config. Skip individual stages with `SKIP_<NAME>=1`, e.g.
# `SKIP_VISUAL=1 infra/scripts/check-all.sh` for quick iteration.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

FAILED=()
PASSED=()
SKIPPED=()

run_stage() {
  local name="$1" skipvar="$2" wd="$3"
  shift 3
  if [[ "${!skipvar:-}" == "1" ]]; then
    SKIPPED+=("$name")
    echo "[skip] $name (${skipvar}=1)"
    return 0
  fi
  echo
  echo "==> $name"
  echo "    (cwd: $wd)"
  echo "    $*"
  if (cd "$wd" && "$@"); then
    PASSED+=("$name")
    return 0
  else
    FAILED+=("$name")
    return 1
  fi
}

API_VENV="$ROOT/apps/api/.venv/bin"
WORKER_VENV="$ROOT/workers/render/.venv/bin"

run_stage "apps/api ruff format" SKIP_RUFF_FORMAT "$ROOT/apps/api" \
  "$API_VENV/ruff" format --check .

run_stage "apps/api ruff check" SKIP_RUFF_CHECK "$ROOT/apps/api" \
  "$API_VENV/ruff" check .

run_stage "workers/render ruff format" SKIP_RUFF_FORMAT "$ROOT/workers/render" \
  "$WORKER_VENV/ruff" format --check .

run_stage "workers/render ruff check" SKIP_RUFF_CHECK "$ROOT/workers/render" \
  "$WORKER_VENV/ruff" check .

run_stage "apps/web typecheck" SKIP_TYPECHECK "$ROOT/apps/web" \
  npm run typecheck

# Story 9.1 (Epic 8 retro §A11) — apps/web production build stage. `tsc -b`
# (the typecheck stage above) does NOT catch missing-export errors that the
# full Vite production build surfaces. Story 8.6 TS2305 lesson: api-types.ts
# shipped without an exported symbol that other modules imported; typecheck
# passed because the tsc composite incremental did not re-evaluate the
# downstream file. `pnpm build` (== `tsc -b && vite build`) re-evaluates
# everything and fails fast. Cost: ~30-60s on a clean tree. Skip via
# SKIP_BUILD=1 for fast iteration.
run_stage "apps/web production build" SKIP_BUILD "$ROOT/apps/web" \
  npm run build

run_stage "apps/web lint (eslint + stylelint)" SKIP_LINT "$ROOT/apps/web" \
  npm run lint -- --max-warnings=0

run_stage "apps/web vitest" SKIP_VITEST "$ROOT/apps/web" \
  npm run test

run_stage "apps/api pytest" SKIP_PYTEST "$ROOT/apps/api" \
  "$API_VENV/pytest" -q

run_stage "workers/render pytest" SKIP_PYTEST "$ROOT/workers/render" \
  "$WORKER_VENV/pytest" -q

# SW-DEPLOY-1 — infra/scripts unit tests (slicer-worker overlay detect +
# DRY_RUN shell-command generation). Stdlib + pytest, no Docker/SSH. Run with
# the apps/api venv pytest since it is the one provisioned on the dev box.
run_stage "infra/scripts pytest" SKIP_INFRA_TESTS "$ROOT" \
  "$API_VENV/pytest" -q "$ROOT/infra/scripts/tests/test_slicer_worker_overlay.py"

run_stage "apps/web visual regression" SKIP_VISUAL "$ROOT/apps/web" \
  npm run test:visual

# Story 8.1 (Epic 7 retro §1) — tri-directional Settings ↔ env.example ↔
# docker-compose.yml diff. Catches the Story 6.4/6.6/6.7/7.1 dropped-on-the-
# floor env-var wiring regression class. Cheap (<1s).
run_stage "settings-env-compose-diff" SKIP_SETTINGS_ENV "$ROOT" \
  "$API_VENV/python" "$ROOT/infra/scripts/check-settings-env-compose.py"

# Story 8.1 (Epic 7 retro §2) — uv lockfile staleness gate. Catches the
# Story 7.1 stale-lockfile class (a pyproject.toml change shipped without
# `uv lock` regen).
run_stage "uv-lock-check (apps/api)" SKIP_UV_LOCK "$ROOT/apps/api" \
  uv lock --check
run_stage "uv-lock-check (workers/render)" SKIP_UV_LOCK "$ROOT/workers/render" \
  uv lock --check

# Story 8.1 (Epic 7 retro §1) — LOCAL infra/.env secret-provisioning check.
# Scans env.example for ^[A-Z_]+=$ empty slots (intended for operator-supplied
# secrets) and asserts the same name is non-empty in the local infra/.env.
# Skips gracefully if infra/.env is absent (fresh checkout, no local dev yet).
run_stage "local-env-secrets" SKIP_LOCAL_ENV_SECRETS "$ROOT" \
  bash "$ROOT/infra/scripts/check-local-env-secrets.sh"

echo
echo "================ check-all summary ================"
printf "passed:  %d\n" "${#PASSED[@]}"
for n in "${PASSED[@]}"; do printf "         ✓ %s\n" "$n"; done
if (( ${#SKIPPED[@]} > 0 )); then
  printf "skipped: %d\n" "${#SKIPPED[@]}"
  for n in "${SKIPPED[@]}"; do printf "         - %s\n" "$n"; done
fi
if (( ${#FAILED[@]} > 0 )); then
  printf "failed:  %d\n" "${#FAILED[@]}"
  for n in "${FAILED[@]}"; do printf "         ✗ %s\n" "$n"; done
  exit 1
fi
echo "all green."
