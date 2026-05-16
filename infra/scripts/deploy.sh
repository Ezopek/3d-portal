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

# --- Deploy skip-gate (AGENTS.md § Deploy gate) ---------------------------
# Range-based: skip the deploy only when EVERY commit in
# <last-deploy-sha>..HEAD is skip-prefixed (docs:/chore:/wip:). Any single
# non-skip commit in range forces a deploy. State file is updated on
# deploy-success only — skipped runs leave it unchanged, so consecutive
# skip pushes accumulate in the next non-skip push's range. Failure modes
# (missing/empty/unresolved state) degrade to WARN+deploy; never trust
# HEAD-only as a fallback (that flaw is why a previous HEAD-only design
# was reverted on 2026-05-16; see AGENTS.md § Deploy gate for context).
SKIP_PREFIXES=("docs:" "chore:" "wip:")
last_deploy_path="$REPO_DIR/infra/.last-deploy-sha"
head_short="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"

if [[ ! -f "$last_deploy_path" ]]; then
  echo "[deploy-skip-gate] WARN: $last_deploy_path missing — first run, proceeding with deploy" >&2
else
  last_deploy_sha="$(tr -d '[:space:]' < "$last_deploy_path")"
  # Validate the stripped content is a full 40-char hex SHA BEFORE handing it
  # to `rev-parse --verify`. Without this guard, an empty string would let
  # `rev-parse --verify "^{commit}"` succeed (git peels HEAD by default), and
  # a value containing `^N` could resolve to an unintended ancestor — both
  # would bypass the WARN+deploy path the spec promises for invalid state.
  if [[ ! "$last_deploy_sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "[deploy-skip-gate] WARN: $last_deploy_path content '${last_deploy_sha:0:40}' is not a valid 40-char hex SHA, proceeding with deploy" >&2
  elif ! git -C "$REPO_DIR" rev-parse --verify "${last_deploy_sha}^{commit}" >/dev/null 2>&1; then
    echo "[deploy-skip-gate] WARN: last-deploy-sha '$last_deploy_sha' unresolved (rebased or GC'd), proceeding with deploy" >&2
  else
    range="${last_deploy_sha}..HEAD"
    last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha")"
    short_range="${last_short}..${head_short}"
    subjects="$(git -C "$REPO_DIR" log --format=%s "$range" 2>/dev/null || true)"
    if [[ -z "$subjects" ]]; then
      echo "[deploy-skip] no new commits since last deploy ($short_range), skipping"
      exit 0
    fi
    commit_count="$(git -C "$REPO_DIR" rev-list --count "$range" 2>/dev/null || echo 0)"
    all_skip=true
    while IFS= read -r subject; do
      [[ -z "$subject" ]] && continue
      matched=false
      for prefix in "${SKIP_PREFIXES[@]}"; do
        [[ "$subject" == "$prefix"* ]] && { matched=true; break; }
      done
      if ! $matched; then
        all_skip=false
        break
      fi
    done <<< "$subjects"
    if $all_skip; then
      echo "[deploy-skip] all $commit_count commits in $short_range are skip-prefixed, skipping deploy"
      exit 0
    fi
  fi
fi

# Captured before `docker compose build` so verify-symbolication.sh (TB-005)
# can compare against the resulting web image's `.Created` timestamp: a
# cached web image (API-only / doc-only deploys) leaves it older than this
# value, which the verify script treats as a skip condition (release-tag
# mismatch is structural, not a real symbolication regression). Exported
# alongside PORTAL_VERSION so the child script can resolve the image tag.
DEPLOY_START_TS=$(date +%s)
export DEPLOY_START_TS
export PORTAL_VERSION="$VERSION"

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
  5) printf '\033[33m→ verify SKIPPED: web image cached (no rebuild → release-tag mismatch unavoidable, not a real regression)\033[0m\n' ;;
  *) printf '\033[31m⚠ verify FAILED: unexpected exit %s\033[0m\n' "$verify_exit" >&2 ;;
esac

# --- Post-deploy verify: agent runbook fingerprint (Story 4.2; Decision D) -
# Non-fatal: deploy success is decoupled from verify outcome. Same three-
# signal model as verify-symbolication.sh: stderr warning + state marker
# + (future) synthetic GlitchTip event on mismatch. Fingerprint extraction
# chain is BINDING (matches Story 4.1 Completion Notes); any drift here
# vs the chain that produced infra/.runbook-fingerprint will yield a
# spurious mismatch on a runbook that hasn't actually changed.
#
# IMPORTANT: under `set -euo pipefail` (top of this script), every step
# below MUST tolerate non-zero exit codes from curl/sha256sum/awk via
# explicit `|| true` or `if ! ...; then`. Otherwise a transient prod
# blip kills the deploy script before it writes the FAILED marker.
echo "→ Verify post-deploy agent runbook fingerprint"
runbook_url="${PORTAL_RUNBOOK_URL:-https://3d.ezop.ddns.net/agent-runbook}"
last_runbook_path="$REPO_DIR/infra/.last-verify-runbook"
expected_fp="$(cat "$REPO_DIR/infra/.runbook-fingerprint" 2>/dev/null || echo "<missing>")"

runbook_body=""
runbook_ctype=""
curl_exit=0
# `-w` extracts the live Content-Type so we can sanity-check NFR7 — a
# successful 200 with a wrong content-type would still match the
# fingerprint and silently pass otherwise.
curl_out="$(curl -fsS -w $'\n--CTYPE--\n%{content_type}' \
  "$runbook_url" 2>/dev/null)" || curl_exit=$?
if [[ $curl_exit -eq 0 ]]; then
  runbook_body="${curl_out%$'\n--CTYPE--\n'*}"
  runbook_ctype="${curl_out##*--CTYPE--$'\n'}"
fi
actual_fp=""
if [[ -n "$runbook_body" ]]; then
  actual_fp="$(printf '%s' "$runbook_body" \
    | awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' \
    | sha256sum | awk '{print $1}')" || actual_fp=""
fi

if [[ "$expected_fp" = "<missing>" ]]; then
  printf '\033[33m⚠ runbook verify SKIPPED: infra/.runbook-fingerprint not present\033[0m\n' >&2
  echo "SKIPPED $(date -Iseconds) reason=baseline-missing" > "$last_runbook_path"
elif [[ $curl_exit -ne 0 || -z "$runbook_body" ]]; then
  printf '\033[31m⚠ runbook verify FAILED: %s unreachable (curl exit %s)\033[0m\n' "$runbook_url" "$curl_exit" >&2
  echo "FAILED $(date -Iseconds) reason=unreachable url=$runbook_url curl_exit=$curl_exit" > "$last_runbook_path"
elif [[ "$runbook_ctype" != text/markdown* ]]; then
  printf '\033[31m⚠ runbook verify FAILED: wrong Content-Type %s (expected text/markdown)\033[0m\n' "$runbook_ctype" >&2
  echo "FAILED $(date -Iseconds) reason=content-type ctype=$runbook_ctype" > "$last_runbook_path"
elif [[ -z "$actual_fp" ]]; then
  printf '\033[31m⚠ runbook verify FAILED: fingerprint extraction returned empty (intro paragraph missing or awk chain broken)\033[0m\n' >&2
  echo "FAILED $(date -Iseconds) reason=fingerprint-empty" > "$last_runbook_path"
elif [[ "$expected_fp" = "$actual_fp" ]]; then
  echo "✓ runbook fingerprint OK ($actual_fp)"
  echo "OK $(date -Iseconds) $actual_fp" > "$last_runbook_path"
else
  printf '\033[31m⚠ runbook fingerprint MISMATCH: expected %s, got %s\033[0m\n' "$expected_fp" "$actual_fp" >&2
  echo "FAILED $(date -Iseconds) expected=$expected_fp actual=$actual_fp" > "$last_runbook_path"
fi

# Defensive: clean up TB-005 exports so an operator who runs verify by hand
# in the same shell (e.g. after `source` rather than `bash` invocation) does
# not silently inherit the gate and SKIP unexpectedly.
unset DEPLOY_START_TS PORTAL_VERSION || true

# --- Record successful deploy SHA for next run's skip-gate ----------------
# Best-effort: a write failure here must NOT fail the deploy (it's already
# done). The state file is local-only (gitignored) — host-specific
# runtime tracking, never committed. Skipped runs do not advance this
# pointer; only completed deploys do.
deploy_sha_full="$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || true)"
if [[ -n "$deploy_sha_full" ]]; then
  echo "$deploy_sha_full" > "$last_deploy_path" 2>/dev/null || \
    echo "[deploy-skip-gate] WARN: failed to update $last_deploy_path (non-fatal)" >&2
fi

echo "Done."
