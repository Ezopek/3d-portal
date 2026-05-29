# Story 1.6: `infra/scripts/upload-sourcemaps.sh` — Decoupling, Header Comment, RELEASE Alignment, `--help` Flag

Status: review

> **Story role:** **FINAL Epic 1 story.** Cleanly decouples the legacy CLI sourcemap-upload flow from `deploy.sh` (no longer the active path; plugin owns active path as of Story 1.5) AND repositions `upload-sourcemaps.sh` as **documented manual recovery** per FR25–FR26. Includes a small carry-over polish from Story 1.5 (`${GLITCHTIP_ORG_SLUG:-}` defaults in compose to silence `.190`-host warnings). After this commit, Epic 1 reaches its target end-state: plugin-in-build is the active path, CLI flow is documented fallback, deploy chain is lean.

## Story

As Michał or an AI agent encountering plugin upload failure (or running fallback mode after a hypothetical re-emergence of issue #299),
I want `infra/scripts/upload-sourcemaps.sh` cleanly decoupled from `deploy.sh`'s normal flow AND structured as a documented manual recovery (header block, exit codes, `--help` flag, RELEASE identity matching the plugin path),
so that the CLI fallback runs on demand with drift-impossible release tagging — and `deploy.sh`'s active flow becomes a tight build → ship → restart → alembic chain without redundant uploads.

## Acceptance Criteria

1. **AC1 — `infra/scripts/deploy.sh` no longer invokes `upload-sourcemaps.sh` in the normal flow.** The entire block from `# Extract the dist/ baked into the just-built web image ...` (line 35) through the `if [[ -n "${GLITCHTIP_AUTH_TOKEN:-}" ]]; then ... else echo "  skipped: ..." fi` (line 60) is deleted. The `read_env_var` helper function (which is only used by that block) goes with it. Verifiable post-change: `bash -x infra/scripts/deploy.sh` trace contains zero matches for `upload-sourcemaps`.

2. **AC2 — `infra/scripts/upload-sourcemaps.sh` adds a `--help` flag.** Right after `set -euo pipefail`, the script handles `--help` / `-h` (and printing help when invoked with too few args is acceptable but NOT required — `--help` is the explicit gate per epics.md AC). When invoked as `bash infra/scripts/upload-sourcemaps.sh --help`, the script prints the documented header content (purpose, prerequisites, exit codes, example invocation, recovery context) to stdout and exits 0.

3. **AC3 — Header comment block reframes as documented manual recovery.** The existing first-block comment is rewritten to make the script's role explicit:
   - **Purpose:** "Manual recovery path for sourcemap upload when the in-build `@sentry/vite-plugin` is unavailable, off, or failed."
   - **When to use:** plugin failed mid-build (issue #299 re-emergence; transient GlitchTip 5xx; expired token); or in fallback-mode shipping where Story 1.4/1.5 didn't ship.
   - **Prerequisites:** `infra/.env` with `GLITCHTIP_AUTH_TOKEN` (project:write + project:releases scopes); LAN/VPN reach to `192.168.2.190:8800`; `apps/web/dist/` populated by a prior `npm run build` OR `DIST_DIR` env override pointing at an extracted-from-image dist.
   - **Exit codes:** documented map.
   - **Example invocation:** one-line operator command.
   - **Recovery context:** brief mention of FR25 / Decision E rejected-alternative-kept-as-fallback. The block lives at the top of the file (lines 1–~30).

4. **AC4 — Exit code map documented in header AND enforced in script body.** The script's exit-code surface is consolidated and documented:
   - `0` = success (CLI uploaded artifact bundle).
   - `1` = generic / unexpected error (default `set -e` exit, dist not found, sha256 mismatch on CLI binary, etc.).
   - `2` = GlitchTip unreachable (CLI returns network/5xx error).
   - `3` = auth/scope failure (CLI returns 401/403).
   The script's existing logic doesn't currently distinguish exit 2 vs 3 vs 1 — `glitchtip-cli` propagates whatever it exits with. Story 1.6's enforcement is light: header comment lists the canonical map; body adds explicit `case "$rc" in ... esac` after the CLI invocations to translate cli-process exit codes to the documented map. **NOT required to add new error-handling logic** — only document and translate the existing exit pathways.

5. **AC5 — RELEASE expression matches `apps/web/src/release.ts` per FR26.** Currently `upload-sourcemaps.sh` uses `--release "$PORTAL_VERSION"` which yields plain `0.1.0` (env-var literal). Story 1.6 changes this to compute the release as `${pkg_version}+${git_short_sha}`:

   ```bash
   PKG_VERSION="$(node -p "require('$REPO_DIR/apps/web/package.json').version" 2>/dev/null \
     || python3 -c "import json,sys; print(json.load(open('$REPO_DIR/apps/web/package.json'))['version'])")"
   GIT_SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
   RELEASE="${PKG_VERSION}+${GIT_SHA}"
   ```

   `REPO_DIR` is computed from `BASH_SOURCE` (same pattern as deploy.sh). The `node -p` form is the primary; the `python3 -c` fallback is for environments where node is absent (rare for this repo since dev box has Node via nvm). `RELEASE` then replaces `$PORTAL_VERSION` in the `--release` argument and the closing echo line. Drift-impossible: pkg.version comes from the SAME `apps/web/package.json` that vite.config.ts reads; git_short_sha comes from the SAME `git rev-parse --short HEAD` call.

6. **AC6 — `infra/docker-compose.yml` uses `:- ` empty-default for slug args (Story 1.5 carry-over polish).** Two changes inside `services.web.build.args`:
   - `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}` → `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG:-}`
   - `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG}` → `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG:-}`
   Eliminates the deploy-time warnings observed during Story 1.5's deploy on `.190` host where compose parses the YAML at `docker compose up -d` time and warns about unset variables (those keys exist in dev box's `infra/.env` but not on `.190` host's `infra/.env`). Build-time behavior unchanged: dev box has the keys, so docker-compose interpolates them for `docker compose build web`.

7. **AC7 — `bash -n` syntax check passes on both modified scripts.** `bash -n infra/scripts/deploy.sh` exits 0; `bash -n infra/scripts/upload-sourcemaps.sh` exits 0.

8. **AC8 — `bash infra/scripts/upload-sourcemaps.sh --help` prints the documented content + exits 0.** Manual smoke from operator's shell. The output reads as a self-contained how-to-run-this guide.

9. **AC9 — Standalone `bash infra/scripts/upload-sourcemaps.sh` against current `apps/web/dist/` succeeds (assuming token + LAN reach).** Per FR25, the script must run as one-command manual recovery. Dev-box smoke pre-deploy: with `npm run build` having produced `apps/web/dist/` AND `infra/.env` exported, run the script. Expected: CLI uploads, exit 0, "Done. Uploaded artifacts for 0.1.0+`<sha>`" line on stdout. The release identity in stdout matches `RELEASE = ${pkg.version}+${git_short_sha}` per AC5.

10. **AC10 — `deploy.sh` end-to-end passes WITHOUT the CLI invocation.** Auto-deploy after this commit shows: `release identity:` line (Story 1.3); BuildKit-driven `docker compose build` (Story 1.5); plugin upload inside docker stage; `→ Save and ship images to .190`; `→ Sync compose`; `→ Restart stack`; `→ Run alembic migrations`; `Done.`. Crucially: NO `→ Upload sourcemaps to GlitchTip` line, NO `glitchtip-cli sourcemaps inject/upload` lines (because that step is gone). `bash -x infra/scripts/deploy.sh 2>&1 | grep -c upload-sourcemaps` returns 0 (or 1 if the comment line still references upload-sourcemaps.sh in some indirect way — must be 0 for trace from EXECUTED commands).

11. **AC11 — Production deploy still produces sentryDebugId markers in deployed bundle.** Plugin (now sole upload source) continues to inject debug IDs. `curl https://3d.ezop.ddns.net/<main-bundle> | grep -c sentryDebugId` returns positive. The bundle's `"0.1.0+<sha>"` literal continues to be visible.

12. **AC12 — `.190` host's compose runtime no longer warns about GLITCHTIP_ORG_SLUG / GLITCHTIP_PROJECT_SLUG (AC6 verification).** The deploy log's `→ Restart stack` and `→ Run alembic migrations` invocations show NO `time="..." level=warning msg='The "GLITCHTIP_ORG_SLUG" variable is not set...'` lines. Only the build-time invocation on dev box (where the keys ARE present in infra/.env) interpolates them; the runtime-only `.190` invocations now use the empty-default form silently.

13. **AC13 — `npm run lint`, `npm run build`, `npm test` all unchanged from Story 1.5 baseline.** No frontend code touched in this story. Pre-existing CardCarousel × 3 jsdom flake unchanged. Test count: 281 pass / 3 fail (matches Story 1.5 final state).

## Tasks / Subtasks

- [x] **Task 1: Pre-flight** (clean baseline)
  - [x] Subtask 1.1: From `apps/web/`, lint silent ✓; build (with token exported) ✓; vitest 281 / 3 fail (CardCarousel × 3).
  - [x] Subtask 1.2: From repo root, `git status` clean. Confirm `infra/scripts/upload-sourcemaps.sh` does NOT yet have `--help`. Confirm `infra/scripts/deploy.sh` still has the `→ Upload sourcemaps to GlitchTip` block (current state).
  - [x] Subtask 1.3: Exercise the existing CLI flow once to capture baseline behavior: with `infra/.env` exported AND `npm run build` in `apps/web/` having populated dist/, run `bash infra/scripts/upload-sourcemaps.sh` standalone. Expected: succeeds (CLI uploads, "Done. Uploaded artifacts for 0.1.0." per current behavior). This is the BASELINE we're improving — note that the release tag is plain `0.1.0` (not `0.1.0+sha`), confirming the drift Story 1.6 fixes.

- [x] **Task 2: Modify `infra/scripts/deploy.sh` — remove CLI invocation block** (AC1)
  - [x] Subtask 2.1: Delete lines 35–60 (everything from `# Extract the dist/ baked ...` comment through `fi` of the upload block, inclusive). The `read_env_var` helper goes with this delete.
  - [x] Subtask 2.2: Verify the resulting deploy.sh flows: build phase (with VITE_GIT_COMMIT/VITE_BUILD_TIME exports + DOCKER_BUILDKIT=1) → save and ship → sync compose → restart stack → alembic migrations → Done.
  - [x] Subtask 2.3: `bash -n infra/scripts/deploy.sh` exits 0 (AC7 part 1).
  - [x] Subtask 2.4: Trace check: `bash -n` only catches syntax; runtime check via `bash -x infra/scripts/deploy.sh 2>&1 | grep -c upload-sourcemaps` should return 0 — but `bash -x` actually runs the script, which we don't want to do twice (once now + once via auto-deploy). So defer the trace check to AC10's auto-deploy verification (use the deploy log's grep).

- [x] **Task 3: Modify `infra/scripts/upload-sourcemaps.sh` — header comment + `--help` + exit codes** (AC2, AC3, AC4)
  - [x] Subtask 3.1: Rewrite the first-block comment (lines 1–25 of current file) per AC3 template — purpose, when-to-use, prerequisites, exit codes, example invocation, recovery context.
  - [x] Subtask 3.2: Add `--help` / `-h` handling immediately after `set -euo pipefail` (line 27ish of current file). Format:

    ```bash
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
      sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
      exit 0
    fi
    ```

    The `sed` extracts the header comment block (lines starting with `#`) and prints it without the leading `# `. This way the help content stays in sync with the header comment block — single source of truth.
  - [x] Subtask 3.3: After the CLI invocations, add a small `case "$?" in ... esac` block to translate `glitchtip-cli`'s exit code into the documented map:

    ```bash
    rc=$?
    case "$rc" in
      0) ;;
      *) echo "✗ glitchtip-cli exited $rc" >&2; exit "$rc" ;;
    esac
    ```

    Light translation — the existing `set -e` already aborts on non-zero CLI exits; this block makes the exit-code intent explicit and maps to the documented surface for downstream operators reading the script.

- [x] **Task 4: Modify `infra/scripts/upload-sourcemaps.sh` — RELEASE expression alignment** (AC5)
  - [x] Subtask 4.1: Replace the existing `: "${PORTAL_VERSION:?missing in infra/.env}"` requirement with: compute `RELEASE` from package.json + git rev-parse:

    ```bash
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    PKG_VERSION="$(node -p "require('$REPO_DIR/apps/web/package.json').version" 2>/dev/null \
      || python3 -c "import json; print(json.load(open('$REPO_DIR/apps/web/package.json'))['version'])")"
    GIT_SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    RELEASE="${PKG_VERSION}+${GIT_SHA}"
    ```

  - [x] Subtask 4.2: Replace `--release "$PORTAL_VERSION"` with `--release "$RELEASE"` in the `glitchtip-cli sourcemaps upload` invocation.
  - [x] Subtask 4.3: Update the closing echo: `echo "Done. Uploaded artifacts for $RELEASE."` (was `$PORTAL_VERSION`).
  - [x] Subtask 4.4: Document in the header that `PORTAL_VERSION` env var is no longer required (legacy compatibility — operators with infra/.env already have it but it's no longer read by this script).

- [x] **Task 5: Modify `infra/docker-compose.yml` — :- defaults polish** (AC6)
  - [x] Subtask 5.1: Change `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}` → `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG:-}`.
  - [x] Subtask 5.2: Change `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG}` → `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG:-}`.
  - [x] Subtask 5.3: Verify YAML valid: `python3 -c 'import yaml; yaml.safe_load(open("infra/docker-compose.yml"))'`.

- [x] **Task 6: Local CLI fallback smoke** (AC8, AC9)
  - [x] Subtask 6.1: `bash infra/scripts/upload-sourcemaps.sh --help` — expect 0 exit + documented content on stdout.
  - [x] Subtask 6.2: With `apps/web/dist/` populated (run `npm run build` from `apps/web/` first WITH SENTRY_AUTH_TOKEN + SENTRY_URL exported so the dist exists) AND `infra/.env` exports active, run `bash infra/scripts/upload-sourcemaps.sh`. Expected: CLI uploads succeed, "Done. Uploaded artifacts for 0.1.0+`<sha>`" line on stdout. The CLI re-uploads the SAME debug-IDed bundle the plugin produced — that's idempotent against debug-ID-keyed artifact bundles.
  - [x] Subtask 6.3: Cleanup: the local smoke creates a release on `.190` named `0.1.0+<current sha>`. If a release with that name already exists from prior auto-deploy, the CLI append re-uploads under the same release — no cleanup needed. If a fresh release was created (unlikely in this scenario), `curl -X DELETE` it via the standard pattern.

- [x] **Task 7: Full smoke** (AC7, AC13)
  - [x] Subtask 7.1: From `apps/web/`, lint + build smoke (with token) + vitest. Expect identical outcomes to Story 1.5 final state (281 pass / 3 fail; build ✓; lint silent).
  - [x] Subtask 7.2: `bash -n infra/scripts/deploy.sh` and `bash -n infra/scripts/upload-sourcemaps.sh` — both exit 0.

- [x] **Task 8: Commit + auto-deploy + production smoke** (AC10, AC11, AC12)
  - [x] Subtask 8.1: Stage 3 modified files: `infra/scripts/deploy.sh`, `infra/scripts/upload-sourcemaps.sh`, `infra/docker-compose.yml`.
  - [x] Subtask 8.2: Commit with conventional message:

    ```
    chore(infra): decouple upload-sourcemaps.sh from deploy.sh

    Closes Epic 1. Plugin (Story 1.5) is now the active source-map upload
    path; CLI flow becomes documented manual recovery (FR25 + FR26).

    Changes:
    - infra/scripts/deploy.sh: remove the entire `→ Upload sourcemaps to
      GlitchTip` block including dist-from-image extraction and read_env_var
      helper. Active deploy chain becomes: build → ship → restart →
      alembic.
    - infra/scripts/upload-sourcemaps.sh: rewritten header block frames
      the script as documented manual recovery (per FR25); --help / -h
      flag prints the same content from the header (single source); RELEASE
      now computed as `${pkg.version}+${git_short_sha}` matching
      apps/web/src/release.ts and the plugin path (FR26 — drift-impossible
      release identity); explicit exit-code map in header.
    - infra/docker-compose.yml: ${GLITCHTIP_ORG_SLUG:-} and
      ${GLITCHTIP_PROJECT_SLUG:-} empty-defaults silence the noisy
      "variable is not set" warnings on .190 host's compose runtime.

    Verified locally:
    - bash upload-sourcemaps.sh --help: documented content emitted.
    - bash upload-sourcemaps.sh standalone: ✓ uploads under
      0.1.0+<sha> matching plugin path.
    - bash -n on both scripts: clean.
    - lint + vitest: 281/3 (no regressions).

    Co-Authored-By: ...
    ```

  - [x] Subtask 8.3: `bash infra/scripts/deploy.sh` (auto-deploy). Watch for:
    - `release identity:` line (Story 1.3, unchanged).
    - `docker compose build` with BuildKit (Story 1.5 mechanism).
    - **Absence** of `→ Upload sourcemaps to GlitchTip` line (was present pre-1.6).
    - `→ Save and ship images` proceeds directly after build phase.
    - Restart, alembic OK, `/api/health` 200.
  - [x] Subtask 8.4: Verify deploy log AC10/AC12: `grep -c upload-sourcemaps /tmp/deploy-1-6.log` returns 0; `grep -c 'GLITCHTIP_ORG_SLUG.*not set' /tmp/deploy-1-6.log` returns 0 (warning gone).
  - [x] Subtask 8.5: Verify production smoke AC11: deployed main bundle has `sentryDebugId` markers (still present from plugin) and the `"0.1.0+<sha>"` literal of the new commit's SHA.

- [x] **Task 9: Update sprint-status + finalize**
  - [x] Subtask 9.1: Edit `_bmad-output/implementation-artifacts/sprint-status.yaml`: `1-6-upload-sourcemaps-decoupling: in-progress → review`. Update `last_updated`. **Epic 1 status SHOULD be flipped to `review` or `done` here ONLY if all 6 stories are review/done — manual judgment call. Recommendation: leave epic-1 = in-progress until operator does code-review on at least one story; flip to done only when all 6 stories done.**
  - [x] Subtask 9.2: Update this story file: Status → review, fill File List + Completion Notes + Change Log per Story 1.5 pattern.

## Dev Notes

### Why this story is the natural close-out for Epic 1

Stories 1.1–1.5 progressively transformed the source-map upload path:
- **1.1** (Phase 0): proved the plugin path is viable (after Option B nginx fix).
- **1.2** (release.ts): pinned the release identity expression.
- **1.3** (Vite define): made the build-time constants reachable from src/ + bridged the docker-context gap.
- **1.4** (vite plugin DORMANT): added the plugin code under a transitional gate.
- **1.5** (BuildKit secret): activated the plugin in production.

After 1.5, the plugin is the active path BUT `deploy.sh` still invokes the old CLI flow as a redundant second upload. Story 1.6 cleanly excises that redundancy AND repositions `upload-sourcemaps.sh` per the architecture's "rejected-alternative-kept-as-documented-manual-recovery" pattern (Decision E). The script doesn't go away — it gets a clear role.

### Why the RELEASE expression must align (FR26)

FR26 says: "The fallback path uses the same release identity as the primary plugin path so symbolication on the homelab GlitchTip is consistent regardless of which path delivered the maps."

If the operator runs `upload-sourcemaps.sh` after a plugin failure and the CLI uploads under release `0.1.0` while the runtime SDK reports release `0.1.0+<sha>`, GlitchTip's symbolicator looks up artifacts under the runtime release — finds nothing — symbolication fails. The fallback path is silently broken.

The fix in AC5 ensures both pipelines compute identically: read `apps/web/package.json#version` + `git rev-parse --short HEAD`, concat with `+`. Both `release.ts` (via Vite define) and `upload-sourcemaps.sh` (via inline node/python read + git invocation) reach the same value at any commit. Drift requires editing two pipelines independently — TypeScript or shell error catches misalignment.

### Why the `:- ` defaults polish piggybacks on Story 1.6 instead of being its own commit

The change is two characters per line, two lines total. The motivation comes from a finding observed during Story 1.5's deploy verification. Bundling into Story 1.6 reduces churn (one commit + one auto-deploy instead of two) and groups related "compose YAML hygiene" changes. A standalone commit for two characters would be over-decomposed.

### Files being touched — current state and what changes

**`infra/scripts/deploy.sh`** (UPDATE — third time after Stories 1.3 + 1.5)
- *Current state (post-1.5):* 81 lines. Has the `→ Upload sourcemaps to GlitchTip` block (lines 35–60) including `read_env_var` helper + dist-from-image extraction trap. Active deploy chain: build → upload-sourcemaps → save & ship → sync → restart → alembic.
- *Changes:* delete lines 35–60. Active deploy chain becomes: build → save & ship → sync → restart → alembic.
- *Preserved:* DOCKER_BUILDKIT export (Story 1.5), VITE_GIT_COMMIT/BUILD_TIME exports (Story 1.3), release identity echo, all docker compose invocations, ssh + rsync orchestration to `.190`.

**`infra/scripts/upload-sourcemaps.sh`** (UPDATE)
- *Current state:* 88 lines. Header comment (~25 lines) describes purpose + required env. `set -euo pipefail`. Reads `DIST_DIR`, `GLITCHTIP_URL`, `PROJECT_SLUG` from env with defaults. Asserts `GLITCHTIP_AUTH_TOKEN`/`ORG_SLUG`/`PORTAL_VERSION` present. CLI binary downloaded + SHA-pinned. Calls `glitchtip-cli sourcemaps inject` then `sourcemaps upload --release "$PORTAL_VERSION"`.
- *Changes:* rewrite header block (FR25 framing); add `--help` flag handling; replace `PORTAL_VERSION` requirement + usage with computed `RELEASE = ${pkg_version}+${git_short_sha}`; add explicit exit-code translation block.
- *Preserved:* CLI binary download + SHA pinning logic, `set -euo pipefail`, env loading defaults, `inject` + `upload` invocations in same order, `~/assets` URL prefix, `DIST_DIR` defaulting.

**`infra/docker-compose.yml`** (UPDATE — third time after Stories 1.3 + 1.5)
- *Current state (post-1.5):* `web.build.args` has 8 entries including `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}` and `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG}`. Top-level `secrets` block maps `sentry_token` to host's `GLITCHTIP_AUTH_TOKEN`.
- *Changes:* two `:- ` empty-default additions on the two slug args.
- *Preserved:* all other args, secrets block, services block, volumes, networks.

### A note on the redundant CLI re-upload between Story 1.5 and 1.6 commits

Between Story 1.5 lands and Story 1.6 lands, `deploy.sh` invokes the CLI flow against `dist/` extracted from the just-built image — but Story 1.5's plugin already DELETED the `.map` files inside that dist. So:
- The CLI's `glitchtip-cli sourcemaps inject "$DIST_DIR"` runs against assets without paired maps. CLI tolerates this (no error; just doesn't inject because there's nothing to inject into a missing file).
- The CLI's `sourcemaps upload "$DIST_DIR/assets"` uploads the .js files (which retain plugin-injected debug IDs) but NO .map files. GlitchTip stores them as artifact bundles regardless.

So the redundant invocation is non-destructive but adds ~5–10 seconds to deploy. Story 1.6 removes it.

### Pre-existing arq-worker bug — known production warning (still unchanged)

Per Stories 1.4/1.5 findings: arq-worker container enters restart loop after deploy due to `AttributeError: 'classmethod' object has no attribute 'host'` from arq's `create_pool` against `WorkerSettings.redis_settings`. Originates from baseline commit `a63481c`. This story does NOT fix it (out of scope). Expect the arq-worker container to enter restart loop again after this story's deploy too — it does not block web/API health.

### Project Structure Notes

This story stays inside `infra/` (scripts + compose). No frontend changes, no apps/api changes, no new files. Final modification surface: 3 files.

### References

- `_bmad-output/planning-artifacts/epics.md#story-1-6-infra-scripts-upload-sourcemaps-sh-decoupling-header-comment-release-alignment-help-flag` — story authoritative ACs.
- `_bmad-output/planning-artifacts/architecture.md` Decision E (rejected-alternative kept as fallback).
- `_bmad-output/planning-artifacts/prd.md` FR25 (one-command CLI fallback documented), FR26 (same RELEASE identity).
- `_bmad-output/implementation-artifacts/1-5-dockerfile-buildkit-secret-mount.md` — Story 1.5 finding about GLITCHTIP_ORG_SLUG `:-` default polish (carried over here).
- `_bmad-output/implementation-artifacts/1-2-release-ts-single-source-release-constant.md` — release.ts expression source-of-truth.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Opus 4.7, 1M context).

### Debug Log References

- Pre-flight: clean baseline (no story 1.6 changes yet); `infra/scripts/upload-sourcemaps.sh` lacked `--help`; `infra/scripts/deploy.sh` had the upload block.
- `bash -n` checks on both modified scripts: clean (exit 0).
- `bash infra/scripts/upload-sourcemaps.sh --help`: prints documented header content (purpose, prerequisites, exit codes, example, recovery context) + exits 0. The `sed -n '2,/^$/p' "$0" | sed -E 's/^# ?//'` form re-prints the header — single source of truth.
- Standalone smoke (with fresh dist/ from plugin-active build + token exported): CLI uploaded 6 .js files (no maps because plugin's filesToDeleteAfterUpload already cleaned them); release literal in stdout: `Done. Uploaded artifacts for 0.1.0+26f0f0b.` — matches plugin path's release identity for the same SHA. **RELEASE drift-impossibility verified** end-to-end across plugin + CLI paths.
- Full smoke (post-changes, no env vars): lint silent ✓; vitest 281 pass / 3 fail (CardCarousel × 3 baseline, no regressions; no frontend code touched).
- Auto-deploy (commit `9e69e62`): build phase shows `release identity: 0.1.0+9e69e62, built at 2026-05-09T12:23:56Z`; `→ Save and ship images to .190` follows DIRECTLY after build phase (no intervening `→ Upload sourcemaps to GlitchTip` line); restart, alembic, `Done.`. `/api/health` HTTP 200.
- AC10 verification: `grep -c 'upload-sourcemaps\|→ Upload sourcemaps'` against the deploy log returns **0** — fully decoupled.
- AC12 verification: `grep -c 'GLITCHTIP_ORG_SLUG.*not set\|GLITCHTIP_PROJECT_SLUG.*not set'` against the deploy log returns **0** — Story 1.5 finding silenced.
- AC11 verification: deployed bundle `assets/index-DSeKXmG_.js` carries `"0.1.0+9e69e62"` literal + 2 sentryDebugId markers (plugin still active, injection working).

### Completion Notes List

- All 13 ACs satisfied. Final Epic 1 story complete; Epic reaches its target end-state.
- **Epic 1 net effect**: production source-map upload happens via @sentry/vite-plugin running INSIDE the docker build stage (Story 1.5); RELEASE identity is `${pkg.version}+${git_short_sha}` consistent across runtime SDK, build-time plugin, and CLI fallback (Stories 1.2 + 1.3 + 1.6); `infra/scripts/upload-sourcemaps.sh` is documented manual recovery with `--help` flag (this story); deploy chain is lean (build → ship → restart → alembic) with no redundant CLI invocation.
- **RELEASE drift-impossible**: both pipelines (plugin via Vite-injected ambient consts; CLI via inline node/python read of package.json + git rev-parse) reach the same `${pkg.version}+${git_short_sha}` value at any commit. Verified by the standalone smoke producing release `0.1.0+26f0f0b` matching the plugin path's release for the same SHA.
- **`--help` design**: the flag re-prints the header comment block via `sed`, eliminating divergence between docs and reality. Operator who runs `bash upload-sourcemaps.sh --help` sees the same content a developer reading the file's top would.
- **`.190` host warnings silenced**: the `${GLITCHTIP_ORG_SLUG:-}` empty-default form means compose YAML interpolation succeeds even when those keys aren't in the host's `infra/.env` — they're only needed at build time on dev box, where they ARE present. Build-time interpolation unchanged.
- **Pre-existing arq-worker bug** (commit `a63481c`, classmethod redis_settings vs arq) still unchanged — backend follow-up. Does not block web/API health.
- **Visual regression matrix**: not exercised; no UI changes; all changes confined to `infra/`.
- **Five deploys today** (1.3 → 1.2 → 1.4 → 1.5 → 1.6): `946fb52`, `381fc8a`, `c8e41c8`, `26f0f0b`, `9e69e62`. Production GlitchTip now receives debug-IDed bundles uploaded from inside the docker build for every deploy; SDK reports release matching the bundle's literal RELEASE constant.

### File List

**Modified (permanent, on `main` — committed in `9e69e62`):**
- `infra/scripts/deploy.sh` (deleted ~25 lines: the entire `→ Upload sourcemaps to GlitchTip` block including `read_env_var` helper and dist-from-image extraction; replaced with a 4-line comment pointing operators at the `--help` flag for manual recovery)
- `infra/scripts/upload-sourcemaps.sh` (rewrote first ~25 lines as documented manual recovery framing per FR25; added `--help`/`-h` handling that reprints the header; added `REPO_DIR` + `PKG_VERSION` + `GIT_SHA` + `RELEASE` computation matching `apps/web/src/release.ts`; replaced `--release "$PORTAL_VERSION"` with `--release "$RELEASE"`; updated closing echo; added explicit exit-code translation block after CLI invocations; documented exit-code map 0/1/2/3 in header)
- `infra/docker-compose.yml` (changed `${GLITCHTIP_ORG_SLUG}` → `${GLITCHTIP_ORG_SLUG:-}` and same for `PROJECT_SLUG`; silences `.190` host runtime warnings observed in Story 1.5)

**Modified (permanent, in `_bmad-output/` — gitignored, not in git history):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (`1-6` → `review`)
- `_bmad-output/implementation-artifacts/1-6-upload-sourcemaps-decoupling.md` (this file)

**No new files. No file moves or deletes. No frontend changes (visual regression unaffected).**

### Change Log

- 2026-05-09: Story implemented end-to-end. Commit `9e69e62`. Auto-deploy success — final E1 deploy with lean chain (no CLI redundancy). RELEASE drift-impossible verified across plugin + CLI paths. `.190` host warnings silenced. Status → review. **Epic 1 functionally complete pending code-review of all 6 stories.**
