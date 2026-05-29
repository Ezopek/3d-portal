# Story 1.5: Dockerfile BuildKit Secret Mount + Compose Build Args + Remove Plugin Dormant Gate

Status: review

> **Story role:** ACTIVATES the `@sentry/vite-plugin` inside the production docker build. Story 1.4 landed the plugin DORMANT (`disable: !process.env.SENTRY_AUTH_TOKEN`); this story mounts `SENTRY_AUTH_TOKEN` as a BuildKit secret in the build stage AND removes the dormant gate. After this commit lands, source-map upload happens via the plugin running INSIDE `vite build` inside the docker stage — bundle-hash determinism preserved (architecture FR23). Story 1.6 then decouples `upload-sourcemaps.sh` from `deploy.sh` (until then the CLI flow continues to run as a redundant-but-harmless second upload).

## Story

As the docker image build process,
I want `SENTRY_AUTH_TOKEN` mounted as a BuildKit secret (`--mount=type=secret,id=sentry_token`) AND `SENTRY_ORG` / `SENTRY_PROJECT` / `SENTRY_URL` passed as plain build args, AND the dormant gate removed from `vite.config.ts`,
so that the auth token never persists in image layers (verifiable via `docker history`) AND the Sentry vite-plugin actively uploads source maps + injects debug IDs during `vite build` inside the docker stage on every production deploy.

## Acceptance Criteria

1. **AC1 — Dockerfile syntax directive + new ARGs.** `apps/web/Dockerfile` adds `# syntax=docker/dockerfile:1` as the very first line (ensures BuildKit-secret syntax recognition across docker daemon versions). Adds three new ARGs after the existing `ARG VITE_BUILD_TIME`:

   ```dockerfile
   ARG SENTRY_ORG
   ARG SENTRY_PROJECT
   ARG SENTRY_URL
   ```

   Plus matching ENV exports continuing the existing backslash-newline pattern:

   ```dockerfile
   ENV ... \
       SENTRY_ORG=$SENTRY_ORG \
       SENTRY_PROJECT=$SENTRY_PROJECT \
       SENTRY_URL=$SENTRY_URL
   ```

   These three are passed as plain build args (NOT secrets) — they are not sensitive (org slug, project slug, LAN URL) and need to be visible to the plugin via `process.env`.

2. **AC2 — Dockerfile RUN line uses BuildKit secret.** The existing `RUN npm run build` line is replaced with:

   ```dockerfile
   RUN --mount=type=secret,id=sentry_token \
       SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" \
       npm run build
   ```

   The single-line env-var prefix is preferred over `sh -c '...'` for readability. The token is read from the BuildKit-mounted file inline and exported into the npm run build subprocess. After the RUN step, the secret is unmounted; nothing persists in the layer.

3. **AC3 — `infra/docker-compose.yml` adds 3 build args + secret reference.** The `web.build` block becomes:

   ```yaml
   web:
     image: portal-web:${PORTAL_VERSION}
     build:
       context: ../apps/web
       args:
         VITE_SENTRY_DSN: ${VITE_SENTRY_DSN}
         VITE_PORTAL_VERSION: ${PORTAL_VERSION}
         VITE_ENVIRONMENT: ${ENVIRONMENT}
         VITE_GIT_COMMIT: ${VITE_GIT_COMMIT:-}
         VITE_BUILD_TIME: ${VITE_BUILD_TIME:-}
         SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}
         SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG}
         SENTRY_URL: http://192.168.2.190:8800
       secrets:
         - sentry_token
     # ...rest of web service unchanged...
   ```

   And a new top-level `secrets:` block at the same indentation level as `services:` and `volumes:`:

   ```yaml
   secrets:
     sentry_token:
       environment: GLITCHTIP_AUTH_TOKEN
   ```

   The `environment: GLITCHTIP_AUTH_TOKEN` form tells docker-compose to read the secret value from the host environment variable `GLITCHTIP_AUTH_TOKEN` at build time — which deploy.sh already exports via `read_env_var GLITCHTIP_AUTH_TOKEN`. **NO code changes to `infra/.env`** — the existing `GLITCHTIP_AUTH_TOKEN` / `GLITCHTIP_ORG_SLUG` / `GLITCHTIP_PROJECT_SLUG` keys are reused via remapping; `SENTRY_URL` is hardcoded in compose YAML (`http://192.168.2.190:8800` is architecturally pinned per Decision D + NFR-S4 "exactly two hosts at build time").

4. **AC4 — `infra/scripts/deploy.sh` exports `DOCKER_BUILDKIT=1`.** Inserted near the existing build-phase exports (just above the `docker compose ... build` line, alongside the `VITE_GIT_COMMIT` / `VITE_BUILD_TIME` exports added in Story 1.3):

   ```bash
   export DOCKER_BUILDKIT=1
   ```

   This is a single line. No other deploy.sh changes are required for this story (Story 1.6 owns removing the `upload-sourcemaps.sh` invocation later).

5. **AC5 — `apps/web/vite.config.ts` removes the dormant gate.** The `disable: !process.env.SENTRY_AUTH_TOKEN,` line is deleted from the `sentryVitePlugin({...})` call. All other plugin options (url, org, project, authToken, release.name, sourcemaps, telemetry: false) stay unchanged. Plugin from this commit forward ALWAYS runs in `vite build` mode; absent token now produces a hard failure (FR4) rather than silent no-op.

6. **AC6 — Local `docker compose build web` succeeds with BuildKit secret.** From the repo root with `GLITCHTIP_AUTH_TOKEN`, `GLITCHTIP_ORG_SLUG`, `GLITCHTIP_PROJECT_SLUG` exported (as deploy.sh does) and `DOCKER_BUILDKIT=1` set, run:

   ```bash
   docker compose --env-file infra/.env -f infra/docker-compose.yml build web 2>&1 | tee /tmp/buildkit-build.log
   ```

   Expected: build exits 0; build log contains `[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry` (plugin ran inside docker stage and uploaded).

7. **AC7 — `docker history` proves token never lands in image layers (FR21, NFR-S1).**

   ```bash
   docker history --no-trunc portal-web:0.1.0 | grep -i 'sentry_auth_token\|GLITCHTIP_AUTH_TOKEN' || echo "(0 matches — clean)"
   docker history --no-trunc portal-web:0.1.0 | grep -i "$(echo $GLITCHTIP_AUTH_TOKEN | head -c 8)" || echo "(token prefix not in any layer)"
   ```

   Both grep commands MUST return zero matches (or the literal "(0 matches — clean)" / "(token prefix not in any layer)" message). The `--no-trunc` flag is critical — without it, only first ~50 chars per layer command shows.

8. **AC8 — Build WITHOUT BuildKit fails with a clear error.** Manual smoke (optional, for documentation only): with `unset DOCKER_BUILDKIT`, run `docker compose build web`. Expected: build fails because `--mount=type=secret` syntax requires BuildKit. The error message references the `--mount` flag. This validates that the BuildKit gate is real, and operators on machines without BuildKit will see an actionable error — they then export `DOCKER_BUILDKIT=1` and retry. Modern Docker (20.10+) defaults to BuildKit, so on most boxes this is a non-issue; the explicit export is belt-and-suspenders.

9. **AC9 — Plugin uploads via `:8800` succeed and bundle has `sentryDebugId` markers.** After AC6's build:

   ```bash
   docker create --name probe portal-web:0.1.0 >/dev/null
   docker cp probe:/usr/share/nginx/html /tmp/portal-dist
   docker rm probe >/dev/null
   ls /tmp/portal-dist/assets/*.map | wc -l   # expect 0 (filesToDeleteAfterUpload worked)
   grep -ho 'sentryDebugId' /tmp/portal-dist/assets/*.js | head -3   # expect "sentryDebugId" lines
   rm -rf /tmp/portal-dist
   ```

   The `:8800` upload is verified by checking the GlitchTip release endpoint:

   ```bash
   set -a; source infra/.env; set +a
   curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
     "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+$(git rev-parse --short HEAD)/" \
     | jq '.version, .dateCreated'
   ```

   Expected: returns the just-deployed release version.

10. **AC10 — Auto-deploy after merge succeeds end-to-end.** Per memory `feedback_auto_deploy_dev`, `bash infra/scripts/deploy.sh` runs immediately after the commit. Deploy chain:
    - `release identity: 0.1.0+<sha>, built at <ts>` printed (Story 1.3 line, unchanged).
    - `docker compose build web` runs WITH BuildKit; plugin uploads inside the build stage; build exits 0.
    - `→ Upload sourcemaps to GlitchTip` step still runs via CLI (Story 1.6 removes it). The CLI upload runs against the plugin-extracted `dist/` which has NO `.map` files — CLI either uploads 0 files (idempotent, harmless) or warns about no maps. Treat any non-zero exit from upload-sourcemaps.sh in this transitional state as worth investigating but not blocking.
    - `Save and ship images to .190` proceeds.
    - Restart compose, alembic, `/api/health` 200.

11. **AC11 — Dist files served from production carry plugin-injected debug IDs.**

    ```bash
    INDEX_HTML=$(curl -fsS https://3d.ezop.ddns.net/)
    MAIN_JS=$(echo "$INDEX_HTML" | grep -oE 'assets/index-[^"]*\.js' | head -1)
    curl -fsS "https://3d.ezop.ddns.net/$MAIN_JS" | grep -c 'sentryDebugId'
    ```

    Expected: positive integer (at least 1 occurrence of `sentryDebugId`). The deployed bundle ALSO carries the literal RELEASE string `"0.1.0+<sha>"` from Story 1.2.

12. **AC12 — Vitest unit test still passes (regression check).** `npm test -- src/vite-config` from `apps/web/` continues to pass (2 tests). Removing the `disable` line doesn't affect plugin presence/position assertions.

13. **AC13 — `npm run lint` and full vitest suite still green.** Lint silent. Vitest 281 pass / 3 fail (CardCarousel × 3 pre-existing baseline; no new regressions).

## Tasks / Subtasks

- [x] **Task 1: Pre-flight** (clean baseline, BuildKit availability)
  - [x] Subtask 1.1: From `apps/web/`, lint silent ✓; build ✓ (plugin disabled in dormant mode); vitest 281/3 (matches Story 1.4 final state).
  - [x] Subtask 1.2: From repo root, `git status` clean. `docker --version` shows ≥20.10 (BuildKit-stable). `docker buildx version` shows ≥0.10 (modern secret mount).
  - [x] Subtask 1.3: Confirm `infra/.env` has `GLITCHTIP_AUTH_TOKEN`, `GLITCHTIP_ORG_SLUG=homelab`, `GLITCHTIP_PROJECT_SLUG=3d-portal`. The first is sensitive (token); the other two are slugs to remap as build args.

- [x] **Task 2: Modify `apps/web/Dockerfile`** (AC1, AC2)
  - [x] Subtask 2.1: Add `# syntax=docker/dockerfile:1` as the FIRST line of the file (before the `FROM`).
  - [x] Subtask 2.2: Add three new `ARG` declarations after the existing `ARG VITE_BUILD_TIME`: `ARG SENTRY_ORG` / `ARG SENTRY_PROJECT` / `ARG SENTRY_URL`.
  - [x] Subtask 2.3: Extend the existing `ENV` block with the three new keys via the backslash-newline pattern.
  - [x] Subtask 2.4: Replace `RUN npm run build` with the BuildKit-secret form: `RUN --mount=type=secret,id=sentry_token SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" npm run build`.

- [x] **Task 3: Modify `infra/docker-compose.yml`** (AC3)
  - [x] Subtask 3.1: Inside `services.web.build.args`, add three lines: `SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}`, `SENTRY_PROJECT: ${GLITCHTIP_PROJECT_SLUG}`, `SENTRY_URL: http://192.168.2.190:8800`.
  - [x] Subtask 3.2: Inside `services.web.build`, add a `secrets:` block (sibling of `args:`) with one entry: `- sentry_token`.
  - [x] Subtask 3.3: Add a top-level `secrets:` block at the end of the file (after `volumes:` if present, else after `services:` block ends): `secrets: { sentry_token: { environment: GLITCHTIP_AUTH_TOKEN } }`.
  - [x] Subtask 3.4: Verify YAML parses cleanly: `python3 -c 'import yaml; yaml.safe_load(open("infra/docker-compose.yml"))'`.

- [x] **Task 4: Modify `infra/scripts/deploy.sh`** (AC4)
  - [x] Subtask 4.1: Insert `export DOCKER_BUILDKIT=1` immediately after the `cd "$REPO_DIR"` line (before the `VITE_GIT_COMMIT` export from Story 1.3, OR alongside it — either order works because all three exports happen before the `docker compose build` invocation).
  - [x] Subtask 4.2: Run `bash -n infra/scripts/deploy.sh` for syntax check — expect exit 0.

- [x] **Task 5: Remove dormant gate from `apps/web/vite.config.ts`** (AC5)
  - [x] Subtask 5.1: Delete the line `disable: !process.env.SENTRY_AUTH_TOKEN,` from the `sentryVitePlugin({...})` call.
  - [x] Subtask 5.2: Run `npm run lint` and `npm run typecheck` from `apps/web/` — expect both PASS.
  - [x] Subtask 5.3: Run `npm test -- src/vite-config` — expect 2 PASS (plugin still present + still LAST).

- [x] **Task 6: Local docker build smoke** (AC6, AC7, AC9)
  - [x] Subtask 6.1: From repo root: `set -a; source infra/.env; set +a; export DOCKER_BUILDKIT=1`. Verify `[[ -n "$GLITCHTIP_AUTH_TOKEN" ]] && echo present || echo missing` → "present".
  - [x] Subtask 6.2: `docker compose --env-file infra/.env -f infra/docker-compose.yml build web 2>&1 | tee /tmp/buildkit-build.log`.
  - [x] Subtask 6.3: Verify upload happened: `grep -E 'sentry-vite-plugin.*Successfully uploaded|Successfully uploaded source maps' /tmp/buildkit-build.log`.
  - [x] Subtask 6.4: Token-leak check: `docker history --no-trunc portal-web:0.1.0 | grep -i 'sentry_auth_token\|GLITCHTIP_AUTH_TOKEN'` → expect ZERO matches. Token-prefix check: `docker history --no-trunc portal-web:0.1.0 | grep -c "$(echo $GLITCHTIP_AUTH_TOKEN | head -c 8)"` → expect 0.
  - [x] Subtask 6.5: Image-content check: `docker create --name probe portal-web:0.1.0 >/dev/null; docker cp probe:/usr/share/nginx/html /tmp/portal-dist; docker rm probe >/dev/null; find /tmp/portal-dist -name '*.map' | wc -l` → expect 0. `grep -lho 'sentryDebugId' /tmp/portal-dist/assets/*.js | head -3` → expect non-empty (sentryDebugId markers present). Cleanup: `rm -rf /tmp/portal-dist`.
  - [x] Subtask 6.6: REST verify release on .190: `curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+$(git rev-parse --short HEAD)/" | jq -r '.version'` → expect `0.1.0+<sha>` matching current HEAD.

- [x] **Task 7: Cleanup pre-deploy test release** (AC9 sanitation)
  - [x] Subtask 7.1: Delete the test release that the local build registered: `curl -fsS -X DELETE -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+$(git rev-parse --short HEAD)/" -w 'cleanup: %{http_code}\n' -o /dev/null` → expect 204.

- [x] **Task 8: Full smoke** (AC12, AC13)
  - [x] Subtask 8.1: From `apps/web/`, `npm run lint` silent ✓; `npm run build` (with NO env vars, plugin will hard-fail per FR4 — this is EXPECTED to fail now without the dormant gate). **Skip** AC13's "plain `npm run build` exits 0" check; the test expectation has shifted.
  - [x] Subtask 8.2: Re-run with token: from `apps/web/`, `set -a; source ../../infra/.env; set +a; export SENTRY_URL=http://192.168.2.190:8800; export SENTRY_AUTH_TOKEN="$GLITCHTIP_AUTH_TOKEN"; export VITE_GIT_COMMIT=$(git -C ../.. rev-parse --short HEAD); npm run build` → expect ✓ + upload step. Cleanup the second test release post-build.
  - [x] Subtask 8.3: Run `npm test` (full suite) → expect 281 pass / 3 fail (same as Story 1.4 final state — no regressions).

- [x] **Task 9: Commit + auto-deploy** (AC10, AC11)
  - [x] Subtask 9.1: Stage 4 modified files: `apps/web/Dockerfile`, `apps/web/vite.config.ts`, `infra/docker-compose.yml`, `infra/scripts/deploy.sh`.
  - [x] Subtask 9.2: Commit with conventional message:

    ```
    feat(infra): wire Sentry vite-plugin via BuildKit secret

    Activates the dormant @sentry/vite-plugin (Story 1.4) by mounting
    SENTRY_AUTH_TOKEN as a BuildKit secret in the docker build stage and
    removing the disable gate from vite.config.ts.

    Changes:
    - apps/web/Dockerfile: # syntax=docker/dockerfile:1; ARG SENTRY_ORG/
      SENTRY_PROJECT/SENTRY_URL + ENV exports; RUN line uses
      --mount=type=secret,id=sentry_token to read the token without it
      ever landing in an image layer (FR21, NFR-S1).
    - infra/docker-compose.yml: 3 new build args + secrets stanza on web
      service + top-level secrets block mapping sentry_token to host's
      GLITCHTIP_AUTH_TOKEN env var.
    - infra/scripts/deploy.sh: export DOCKER_BUILDKIT=1 before
      docker compose build so the secret syntax is recognized.
    - apps/web/vite.config.ts: removed `disable: !process.env...` —
      plugin now ALWAYS runs in vite build (FR4 hard-fail policy
      enforced from this commit forward).

    Verified locally:
    - docker compose build web with BuildKit: ✓, plugin uploaded
      source maps to :8800, dist/ in image has no .map files,
      sentryDebugId markers present in JS bundles.
    - docker history --no-trunc | grep -i sentry_auth_token: 0 matches.
    - REST: release 0.1.0+<sha> registered on homelab GlitchTip.

    Story 1.6 will decouple infra/scripts/upload-sourcemaps.sh from
    deploy.sh; until then it runs as a redundant-but-harmless second
    upload against the plugin-extracted dist/ (which has no maps).

    Co-Authored-By: ...
    ```

  - [x] Subtask 9.3: Run `bash infra/scripts/deploy.sh`. Watch for: `release identity:` line (existing); `docker compose build` triggers BuildKit; plugin upload step inside docker shows "Successfully uploaded"; `Save and ship images to .190` proceeds; restart succeeds; alembic OK; `/api/health` 200 (allow up to 8s startup race per Story 1.4 finding).
  - [x] Subtask 9.4: Production smoke per AC11: fetch the deployed main bundle, confirm `sentryDebugId` markers present (from PLUGIN's injection — distinct from CLI's previous injection because plugin and CLI use different debug-ID schemes; both produce `sentryDebugId` markers but with different bundle IDs).
  - [x] Subtask 9.5: Cleanup any test release artifacts on .190 if the deploy created intermediate ones beyond the auto-published one.

- [x] **Task 10: Update sprint-status + finalize story file**
  - [x] Subtask 10.1: After successful deploy + smoke, edit `_bmad-output/implementation-artifacts/sprint-status.yaml`: `1-5-dockerfile-buildkit-secret-mount: in-progress → review`. Update `last_updated`.
  - [x] Subtask 10.2: Update this story file: Status → review, fill File List + Completion Notes + Change Log per Story 1.4 pattern.

## Dev Notes

### Why a single commit covers AC1–AC5 instead of multiple commits

Each of the five surface changes is too small to warrant its own commit AND they are interdependent: removing the dormant gate without mounting the secret would break production deploys (plugin would hard-fail with no token); mounting the secret without removing the gate would silently keep the plugin in dormant mode. They MUST land together. The Story-1.4-as-Option-B sequencing was the trade-off: Story 1.4 alone is safely deployable BECAUSE 1.5 is bundled. Story 1.5 is "the activation commit" — atomic, all-or-nothing.

### BuildKit secret mount mechanics

When the Dockerfile contains `RUN --mount=type=secret,id=sentry_token ...`, BuildKit:

1. Reads the secret value from the source declared in `docker-compose.yml`'s `secrets.sentry_token.environment: GLITCHTIP_AUTH_TOKEN` — i.e., the host environment variable named `GLITCHTIP_AUTH_TOKEN`.
2. Mounts it as a temporary **tmpfs file** at `/run/secrets/sentry_token` inside the build container, but ONLY for the duration of the RUN step.
3. The mount is destroyed when the RUN step completes — the file does not exist in any subsequent layer.
4. `docker history` shows the RUN command but redacts the mount source. The actual file content NEVER reaches the layer commit.

This is qualitatively different from `ARG SENTRY_AUTH_TOKEN` + `ENV SENTRY_AUTH_TOKEN=...` which DO persist in the image's metadata. The architecture's NFR-S1 specifically forbids the ARG/ENV pattern for tokens.

The single-line shell prefix form `SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" npm run build` is intentional:

- The exported `SENTRY_AUTH_TOKEN` env var lives only in the `npm run build` subprocess; no parent shell holds it.
- `process.env.SENTRY_AUTH_TOKEN` inside the npm child is populated.
- After `npm run build` exits, the env var is gone with the subprocess.

### Why hardcode `SENTRY_URL` in `infra/docker-compose.yml`

Architecture Decision D + NFR-S4 pin `SENTRY_URL=http://192.168.2.190:8800` as one of the architecturally permitted "exactly two hosts" the build process talks to. The LAN URL is not sensitive (no auth, well-known IP), and committing it to the repo:

- Eliminates "operator forgot to set SENTRY_URL" failure modes.
- Documents the architectural choice in code (anyone reading docker-compose.yml sees the LAN-only invariant).
- Survives `infra/.env` rebuilds without re-derivation.

The token, by contrast, IS sensitive and stays in `infra/.env` (mode 600, gitignored, dev box only).

### Why remap `GLITCHTIP_ORG_SLUG` / `GLITCHTIP_PROJECT_SLUG` instead of adding new `SENTRY_*` env vars

Two reasons:

1. **No infra/.env changes needed.** The existing keys are already present + correctly populated on the dev box. Story 1.5 stays code-only; operator does NOT have to touch `infra/.env` on either dev box or `.190`.
2. **Consistency with existing patterns.** The CLI flow (`upload-sourcemaps.sh`) already reads `GLITCHTIP_ORG_SLUG` / `GLITCHTIP_PROJECT_SLUG` directly. The Sentry plugin reads `process.env.SENTRY_ORG` / `SENTRY_PROJECT`. Mapping at the docker-compose layer (`SENTRY_ORG: ${GLITCHTIP_ORG_SLUG}`) lets each consumer use its preferred name without forcing the operator to maintain duplicate keys.

If a future change ever splits the CLI flow's project from the plugin's project (unlikely), the mapping in compose can be re-pointed without touching `infra/.env`.

### Files being touched — current state and what changes

**`apps/web/Dockerfile`** (UPDATE — third time in this delta after Stories 1.3 + 1.4)
- *Current state:* 22 lines after Story 1.3. `node:22-alpine` build stage with `npm ci` + `COPY . .` + 5 ARG/ENV pairs (VITE_SENTRY_DSN, VITE_PORTAL_VERSION, VITE_ENVIRONMENT, VITE_GIT_COMMIT, VITE_BUILD_TIME) + `RUN npm run build`. nginx:1.27-alpine runtime stage.
- *Changes:* prepend `# syntax=docker/dockerfile:1`; add 3 ARGs (SENTRY_ORG, SENTRY_PROJECT, SENTRY_URL); extend ENV block; rewrite RUN line with `--mount=type=secret`.
- *Preserved:* image base versions, COPY/install order (BuildKit caching reasons), nginx runtime stage.

**`apps/web/vite.config.ts`** (UPDATE — third time)
- *Current state:* Story 1.4 added the `sentryVitePlugin({...})` call LAST in `plugins[]` with `disable: !process.env.SENTRY_AUTH_TOKEN`.
- *Change:* delete the `disable: !process.env.SENTRY_AUTH_TOKEN,` line.
- *Preserved:* all other plugin options (url, org, project, authToken, release.name, sourcemaps, telemetry: false), all other config blocks.

**`infra/docker-compose.yml`** (UPDATE — second time after Story 1.3)
- *Current state:* Story 1.3 added 2 build args (`VITE_GIT_COMMIT`, `VITE_BUILD_TIME`). Web service has 5 build args.
- *Changes:* add 3 build args (SENTRY_ORG, SENTRY_PROJECT, SENTRY_URL); add `web.build.secrets: [sentry_token]`; add top-level `secrets:` block.
- *Preserved:* all existing services (api, redis, arq-worker, render-worker), networks, volumes, service-level env blocks.

**`infra/scripts/deploy.sh`** (UPDATE — second time after Story 1.3)
- *Current state:* Story 1.3 added VITE_GIT_COMMIT/VITE_BUILD_TIME exports + release-identity echo line.
- *Change:* add `export DOCKER_BUILDKIT=1`.
- *Preserved:* all existing deploy logic including upload-sourcemaps.sh invocation (Story 1.6 removes that).

### Pre-existing arq-worker bug — known production warning

Per Story 1.4 finding: arq-worker container enters a restart loop after deploy due to `AttributeError: 'classmethod' object has no attribute 'host'` from arq's `create_pool` against `WorkerSettings.redis_settings` (which is a classmethod, not a property). Originates from baseline commit `a63481c` ("daily cleanup of old refresh_tokens rows"). This story does NOT fix it (out of scope; backend-only follow-up). Expect the arq-worker container to enter restart loop again after this story's deploy too — it does not block web/API health.

### Why don't we worry about the redundant CLI upload (between 1.5 and 1.6 commits)

`infra/scripts/upload-sourcemaps.sh` (the CLI flow) runs AFTER docker build, against `dist/` extracted from the just-built image. Story 1.5 makes the plugin delete `*.map` files from dist post-upload (`filesToDeleteAfterUpload`). So the CLI's subsequent run sees an empty map set and either:
- Uploads zero files (idempotent; no harm).
- Skips with "no files to upload" message (graceful no-op).
- Fails with "expected files but found none" (treat as warning; Story 1.6 removes the invocation entirely so this becomes moot).

In any of these cases, the deploy chain continues. No production harm. Story 1.6 is the proper cleanup.

### Project Structure Notes

This story stays within the canonical infra surface (`apps/web/Dockerfile`, `infra/docker-compose.yml`, `infra/scripts/deploy.sh`) plus one frontend file (`apps/web/vite.config.ts`). No new files, no path changes.

### References

- `_bmad-output/planning-artifacts/epics.md#story-1-5-dockerfile-buildkit-secret-mount` — story authoritative ACs.
- `_bmad-output/planning-artifacts/architecture.md` Decision A (BuildKit secret transport), Decision B (token scope minimization), Decision E (plugin choice 5.2.x), Decision J (in-build execution + DOCKER_BUILDKIT=1).
- `_bmad-output/planning-artifacts/prd.md` FR21 (token never in image layers), FR4 (hard-fail policy), NFR-S1 (token at-rest scope), NFR-S4 (build-time exposure exactly 2 hosts).
- `_bmad-output/implementation-artifacts/1-4-vite-config-sentry-plugin-integration.md` — previous story; plugin ships dormant; this story removes the gate.
- `_bmad-output/implementation-artifacts/1-3-vite-define-build-time-constants.md` — deploy.sh export pattern (single-export-covers-multiple-stories) + arq-worker pre-existing finding context.
- `_bmad-output/implementation-artifacts/phase0-result.md` — Phase 0 happy-path post Option B; plugin uploads via `:8800` succeed.
- Docker BuildKit docs (`docs.docker.com/build/buildkit/secrets/`): mount syntax, environment-source mapping, no-layer-persistence guarantees.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Opus 4.7, 1M context).

### Debug Log References

- Pre-flight: git status clean, Docker 29.3.1, buildx 0.31.1 (BuildKit modern OK).
- Local docker compose build (with DOCKER_BUILDKIT=1): ✓ build complete; plugin upload step inside docker showed `[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry`; `Image portal-web:0.1.0 Built` in 15.0s. `infra/.env` parse warning ("command not found" on hex value continuation line) is pre-existing noise and harmless.
- Token-leak check: `docker history --no-trunc portal-web:0.1.0 | grep -i 'sentry_auth_token\|GLITCHTIP_AUTH_TOKEN'` → 0 matches. Token-prefix grep (`025cf013...`) across all layers → 0 matches. **FR21 satisfied.**
- Image-content check: `docker create + docker cp /usr/share/nginx/html` → 0 .map files (filesToDeleteAfterUpload worked); 3+ sentryDebugId markers across JS bundles; release literal `"0.1.0+c8e41c8"` (HEAD pre-commit) embedded.
- REST: `0.1.0+c8e41c8` release exists on `.190` GlitchTip with current dateCreated (uploaded by local docker build's plugin path, distinct from earlier Story 1.4 deploy's CLI upload).
- Full smoke (post-changes, no-token build): vitest 281 pass / 3 fail (CardCarousel × 3 baseline). Lint silent. Build with token: ✓ in 6.93s, plugin upload OK.
- Auto-deploy (commit 26f0f0b): docker compose build w/ BuildKit; build log shows `RUN --mount=type=secret,id=sentry_token SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" npm run build` line + plugin upload success. Image shipped, restart, alembic, `/api/health` HTTP 200. Deployed bundle (`assets/index-MSRVApBZ.js`) carries `"0.1.0+26f0f0b"` + 2 sentryDebugId markers — **FIRST production deployment with plugin upload happening from INSIDE the docker build context**.

### Completion Notes List

- All 13 ACs satisfied. Atomic activation commit landed cleanly: BuildKit secret + 3 build args + DOCKER_BUILDKIT=1 + remove dormant gate. Production source-map upload now happens via the plugin running inside `vite build` inside the docker stage; CLI flow (Story 1.6 will decouple) ran as redundant second upload but didn't break anything.
- **FR21 verified end-to-end**: `docker history --no-trunc | grep` for the token + token-prefix returns zero matches across all layers. The `--mount=type=secret` mechanism keeps the value on a tmpfs that exists ONLY during the RUN step; after that step's commit, no trace remains.
- **NFR-S1 token-at-rest scope preserved**: token lives in `infra/.env` mode 600 on dev box only. Compose's `secrets.sentry_token.environment: GLITCHTIP_AUTH_TOKEN` reads the host's exported env var — deploy.sh's existing `read_env_var GLITCHTIP_AUTH_TOKEN` + export covers this.
- **Decision E + Decision J active**: plugin in vite.config.ts always runs in production (no longer dormant), and the upload happens INSIDE the docker image build context (not after). Bundle-hash determinism preserved because `vite build` runs inside the same image stage that produces `dist/`.
- **Re-mapping at compose layer worked cleanly**: SENTRY_ORG comes from GLITCHTIP_ORG_SLUG, SENTRY_PROJECT from GLITCHTIP_PROJECT_SLUG. Operator did NOT need to add new keys to `infra/.env` on either dev box or .190.
- **Minor finding (non-blocking, follow-up candidate)**: Deploy log shows `time="..." level=warning msg='The "GLITCHTIP_ORG_SLUG" variable is not set. Defaulting to a blank string.'` (and same for PROJECT_SLUG) from the SECOND `docker compose up -d` invocation that happens on `.190` after image push. The .190 host's `infra/.env` doesn't have these keys (they're only on dev box), and even though the build args are not used at runtime on .190, compose still parses the YAML and warns. Workaround for cleaner logs: change `${GLITCHTIP_ORG_SLUG}` → `${GLITCHTIP_ORG_SLUG:-}` in `infra/docker-compose.yml`. Non-blocking; warnings don't affect deploy success. Should land in Story 1.6 or as a small follow-up commit.
- **Pre-existing arq-worker bug** (commit `a63481c`, classmethod redis_settings vs arq) unchanged. Container enters restart loop after deploy; web/API are unaffected.
- Visual regression matrix unaffected — no UI changes.
- Three significant deployments today: 1.3 (`946fb52`) → 1.2 (`381fc8a`) → 1.4 (`c8e41c8`) → 1.5 (`26f0f0b`). End-to-end Decision E + J active in production.

### File List

**Modified (permanent, on `main` — committed in `26f0f0b`):**
- `apps/web/Dockerfile` (added `# syntax=docker/dockerfile:1`; added 3 ARGs SENTRY_ORG/PROJECT/URL; extended ENV block; rewrote `RUN npm run build` as `RUN --mount=type=secret,id=sentry_token SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" npm run build`)
- `apps/web/vite.config.ts` (deleted `disable: !process.env.SENTRY_AUTH_TOKEN,` line — plugin always runs in `vite build` from this commit)
- `infra/docker-compose.yml` (added 3 build args under `web.build.args`; added `web.build.secrets: [sentry_token]`; added top-level `secrets:` block mapping `sentry_token` to host's `GLITCHTIP_AUTH_TOKEN` env var)
- `infra/scripts/deploy.sh` (added `export DOCKER_BUILDKIT=1` before `docker compose build` invocation)

**Modified (permanent, in `_bmad-output/` — gitignored, not in git history):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (`1-5` → `review`)
- `_bmad-output/implementation-artifacts/1-5-dockerfile-buildkit-secret-mount.md` (this file)

**No new files. No file moves or deletes.**

### Change Log

- 2026-05-09: Story implemented end-to-end. Commit `26f0f0b`. Auto-deploy success — plugin upload now happens from INSIDE the docker build context. Token leak check across all image layers: zero matches. Status → review.
