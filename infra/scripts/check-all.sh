#!/usr/bin/env bash
# Run every per-story quality gate listed in AGENTS.md against the working
# tree. Exits 0 only when ALL gates are green. Intended for:
#   - Manual `infra/scripts/check-all.sh` before pushing a story branch
#   - The `.githooks/pre-push` hook (opt-in via `git config core.hooksPath .githooks`)
#   - One-shot baseline audits after long autonomous batches
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

run_stage "apps/web lint (eslint + stylelint)" SKIP_LINT "$ROOT/apps/web" \
  npm run lint -- --max-warnings=0

run_stage "apps/web vitest" SKIP_VITEST "$ROOT/apps/web" \
  npm run test

run_stage "apps/api pytest" SKIP_PYTEST "$ROOT/apps/api" \
  "$API_VENV/pytest" -q

run_stage "workers/render pytest" SKIP_PYTEST "$ROOT/workers/render" \
  "$WORKER_VENV/pytest" -q

run_stage "apps/web visual regression" SKIP_VISUAL "$ROOT/apps/web" \
  npm run test:visual

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
