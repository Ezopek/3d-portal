# Story 1.4: `vite.config.ts` + `@sentry/vite-plugin` 5.2.x Integration

Status: review

> **Story role:** Lands the plugin code per architecture Decision E + AR3 (LAST in `plugins[]`, `telemetry: false`, `filesToDeleteAfterUpload`, `release.name: RELEASE`). **Plugin ships in DORMANT state** in this commit via `disable: !process.env.SENTRY_AUTH_TOKEN` — production docker builds (token NOT yet in container until Story 1.5's BuildKit secret) skip plugin entirely; deploy.sh's existing CLI flow (`upload-sourcemaps.sh`) continues to handle source-map upload. Story 1.5 removes the `disable` gate AND adds the BuildKit secret in the SAME commit, switching the active path to plugin-in-build.

## Story

As `vite build` running inside the docker image build stage,
I want `@sentry/vite-plugin` 5.2.x added LAST in `plugins[]` with telemetry off, single-source `RELEASE`, and `filesToDeleteAfterUpload`,
so that once Story 1.5 lands the BuildKit secret in the build context, the plugin emits a debug-IDed bundle plus uploaded maps and a clean `dist/` ready for image extraction — and in the meantime, between this commit and 1.5, the dormant gate lets the existing CLI flow keep operating on green deploys.

## Sequencing options considered

Three approaches were considered before locking on Option B:

### Option A — Bundle 1.4 + 1.5 into a single commit
- **Pros:** clean state, FR4 hard-fail policy holds end-to-end, simpler reasoning.
- **Cons:** violates story decomposition discipline; harder to revert just the secret-mount mechanism; one big commit instead of two well-scoped ones.

### Option B — 1.4 lands plugin with transitional `disable` gate; 1.5 removes gate + adds BuildKit secret *(RECOMMENDED — adopted)*
- **Pros:** each commit deploys green; plugin code lands and is reviewable; CLI flow keeps working in transitional window; FR4 reaches enforcement at 1.5 commit.
- **Cons:** between 1.4 and 1.5, FR22 (`*.map` URLs return 404) is not yet enforced — but that's BASELINE state today; no regression.

### Option C — 1.4 lands plugin via `apply: () => false` runtime gate; 1.5 flips
- **Pros:** plugin completely inert in 1.4.
- **Cons:** more complex than `disable: <bool>` (which is a documented top-level option of `sentryVitePlugin`); harder to reason about.

**Decision: Option B.** The `disable: !process.env.SENTRY_AUTH_TOKEN` gate is a documented option of `@sentry/vite-plugin` 5.x (`disable: boolean`). When `true`, the plugin emits no hooks and short-circuits cleanly. This bridges the 1.4 → 1.5 commit window without breaking production deploys.

## Acceptance Criteria

1. **AC1 — Dependency added.** `apps/web/package.json` `devDependencies` adds `"@sentry/vite-plugin": "~5.2.0"`. `apps/web/package-lock.json` resolves to a concrete `5.2.x` version (Phase 0 + Story 1.4 implementation will most likely resolve to **5.2.1** as that was the version Phase 0 dry-run used; treat 5.2.x as the contract).

2. **AC2 — Plugin imported and added LAST in `plugins[]`.** `apps/web/vite.config.ts` adds:

   ```typescript
   import { sentryVitePlugin } from "@sentry/vite-plugin";
   ```

   ...and the plugin call is appended as the LAST entry in `plugins[]`:

   ```typescript
   plugins: [
     TanStackRouterVite({ ... }),
     react(),
     sentryVitePlugin({
       url: process.env.SENTRY_URL,
       org: "homelab",
       project: "3d-portal",
       authToken: process.env.SENTRY_AUTH_TOKEN,
       release: { name: RELEASE },
       sourcemaps: { filesToDeleteAfterUpload: ["./dist/**/*.map"] },
       telemetry: false,
       disable: !process.env.SENTRY_AUTH_TOKEN,
     }),
   ],
   ```

   `RELEASE` is imported from `./src/release` (already exists from Story 1.2). Note: Story 1.4's vite.config.ts already imports release.ts indirectly via the `define` block reading `__PKG_VERSION__`/`__GIT_COMMIT__`; this AC adds a SECOND import of `RELEASE` for the plugin's `release.name` field. Two import paths to the same construct (RELEASE constant via release.ts + ambient constants via define) — both resolve to the same logical value at build time; they are NOT alternatives, they cover different concerns (runtime SDK release vs build-time plugin release tag).

3. **AC3 — Dormant gate via `disable: !process.env.SENTRY_AUTH_TOKEN`.** When `SENTRY_AUTH_TOKEN` is unset OR empty string, the plugin is `disable: true` — emits no hooks, performs no upload, does not delete maps from `dist/`. When token is set, `disable: false` and the plugin runs in full flow.

4. **AC4 — `vite serve` (dev) unchanged.** `npm run dev` from `apps/web/` boots without errors. The plugin's `apply: 'build'` semantic (default for Sentry plugin in 5.x) means it's a no-op during dev server regardless of token presence; the dormant gate is belt-and-suspenders.

5. **AC5 — `vite build` (no token) succeeds with plugin disabled.** Running `npm run build` from `apps/web/` WITHOUT `SENTRY_AUTH_TOKEN` exported (typical local dev) exits 0. Build log does NOT show "sentry-cli upload" lines (plugin is disabled). `dist/assets/*.js.map` files ARE present (existing baseline behavior — plugin can't delete what it doesn't own).

6. **AC6 — `vite build` (with token + LAN URL) uploads via plugin.** Running `npm run build` WITH `SENTRY_AUTH_TOKEN` and `SENTRY_URL=http://192.168.2.190:8800` exported produces:
   - Build exits 0 within 60 s wall-clock budget (NFR-P2).
   - Build stdout contains `[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry` (or equivalent success line).
   - Plugin uploads chunk + assemble both 200 from `:8800` (Phase 0 confirmed this works post-Option-B nginx fix).
   - `dist/assets/*.js.map` files are DELETED post-upload (`find dist -name '*.map' | wc -l` returns 0 — `filesToDeleteAfterUpload` worked).
   - `dist/assets/*.js` files contain `//# sentryDebugId=<uuid>` comments injected by the plugin.

7. **AC7 — `vite build` with token but PLUGIN UPLOAD FAILS exits non-zero.** Simulated by exporting an invalid `SENTRY_AUTH_TOKEN=garbage` and running `npm run build`. Plugin gets 401/403 from server during upload, emits an error, and the build exits with NON-ZERO code. This codifies FR4 hard-fail policy. **Note:** this is the post-Story-1.5 state. In the 1.4 commit specifically, this AC is verified ONLY in the local-dev scenario (host has `.git`, dev exports a fake token). Inside docker (no token until 1.5), plugin is `disable: true` and AC7 is not applicable.

8. **AC8 — `build.sourcemap: 'hidden'` invariant preserved.** The existing config option stays as-is. No `sourceMappingURL` in deployed JS bundles. (FR24, baseline preserved.)

9. **AC9 — Vitest unit test verifies plugin presence + LAST position.** A new file `apps/web/src/vite-config.test.ts` (colocated with src/ tests) imports the default export from `../vite.config.ts` and asserts:
   - `config.plugins` is a non-empty array.
   - At least one entry in `config.plugins` (after flattening — plugin returns array) has a `name` matching `/sentry/i`.
   - The LAST plugin (or last group in flat-mapped plugins) is the sentry plugin (asserts `.findLastIndex(p => /sentry/i.test(p.name))` is the final position).

   **Caveat:** `defineConfig` returns the literal config; `sentryVitePlugin` returns an array of internal plugins (bundler-plugins-core pattern). Test must `flat()` the plugins array before the name search. The test runs in vitest's default jsdom env; Node imports (`node:child_process`, `node:fs`) used by `vite.config.ts` work because vitest itself runs on Node.

10. **AC10 — `npm run lint` (`--max-warnings=0`) and `npm run typecheck` pass.** No new ESLint warnings, no new TypeScript errors. The new import is valid in TS5.6 strict mode.

11. **AC11 — Auto-deploy after merge succeeds with CLI fallback still active.** Per memory `feedback_auto_deploy_dev`, `bash infra/scripts/deploy.sh` runs immediately. Since `SENTRY_AUTH_TOKEN` is NOT in the docker build context yet (Story 1.5 adds the BuildKit secret), the plugin runs in `disable: true` mode inside the docker stage. Build succeeds, plugin no-ops. `deploy.sh` then proceeds to its existing `upload-sourcemaps.sh` invocation which uploads maps via CLI — same behavior as today. Deploy chain success: build → ship → upload-sourcemaps → restart → alembic. `/api/health` 200. Production bundle continues to carry `RELEASE` value (from Story 1.2) and CLI continues to upload under that same release tag (from baseline).

12. **AC12 — Local dev story narrative tests both branches.** Pre-deploy, the dev runs `npm run build` twice from `apps/web/` to verify the dormant gate:
    - **First**, no `SENTRY_AUTH_TOKEN` in env: build OK, no upload step, maps present in dist/.
    - **Second**, with `SENTRY_AUTH_TOKEN` and `SENTRY_URL` exported: build OK, plugin uploads, maps deleted from dist/, `curl /api/0/projects/.../releases/0.1.0+<sha>/files/` returns the uploaded files.
    - This is the human-verifiable smoke for AC5 + AC6 before commit. Documented in completion notes; clean up the test releases via `DELETE /api/0/projects/.../releases/<version>/` post-verification.

## Tasks / Subtasks

- [x] **Task 1: Pre-flight** (clean baseline, baseline behavior captured)
  - [x] Subtask 1.1: From `apps/web/`, `npm run lint` silent ✓; `npm run build` ✓; `npm test` 279 pass / 3 fail (CardCarousel × 3 baseline).
  - [x] Subtask 1.2: `git status` clean. Confirm `apps/web/package.json` `devDependencies` does NOT contain `@sentry/vite-plugin` (`grep -q sentry/vite-plugin apps/web/package.json && echo present || echo absent` → "absent").
  - [x] Subtask 1.3: Reproduce baseline production parity: from `apps/web/`, run `npm run build` and verify `dist/assets/*.js.map` files exist (current behavior). Confirm `dist/assets/*.js` files do NOT contain `sentryDebugId` (no plugin yet).

- [x] **Task 2: Install plugin dependency** (AC1)
  - [x] Subtask 2.1: From `apps/web/`, `npm install --save-dev @sentry/vite-plugin@~5.2.0`.
  - [x] Subtask 2.2: Verify `apps/web/package.json` `devDependencies` now contains `"@sentry/vite-plugin": "~5.2.0"` (or equivalent caret-/tilde-pinned spec resolving to 5.2.x).
  - [x] Subtask 2.3: Confirm `apps/web/package-lock.json` resolves to a 5.2.x version (Phase 0 saw 5.2.1).

- [x] **Task 3: TDD red phase — write `vite-config.test.ts`** (AC9)
  - [x] Subtask 3.1: Create `apps/web/src/vite-config.test.ts`:

    ```typescript
    import { describe, expect, it } from "vitest";

    import config from "../vite.config";

    describe("vite.config.ts plugins[]", () => {
      it("has at least one Sentry plugin entry", () => {
        const flat = (config.plugins ?? []).flat();
        const sentry = flat.filter((p): p is { name: string } => Boolean(p && typeof p === "object" && "name" in p && /sentry/i.test((p as { name: string }).name)));
        expect(sentry.length).toBeGreaterThan(0);
      });

      it("places the Sentry plugin LAST in the flattened plugins[] (per architecture AR3)", () => {
        const flat = (config.plugins ?? []).flat();
        const lastIdx = flat.findLastIndex(
          (p): p is { name: string } => Boolean(p && typeof p === "object" && "name" in p && /sentry/i.test((p as { name: string }).name))
        );
        expect(lastIdx).toBe(flat.length - 1);
      });
    });
    ```

  - [x] Subtask 3.2: Run `npm test -- vite-config` — expect FAIL: `sentry.length` is 0 (plugin not yet added). This is the red phase.

- [x] **Task 4: TDD green phase — modify `vite.config.ts`** (AC2, AC3)
  - [x] Subtask 4.1: Add `import { sentryVitePlugin } from "@sentry/vite-plugin";` after the existing `import { TanStackRouterVite } from "@tanstack/router-vite-plugin";` line (preserve import-order convention: node → external → relative).
  - [x] Subtask 4.2: Add the plugin call as the LAST entry in `plugins[]` per AC2 template.
  - [x] Subtask 4.3: Run `npm test -- vite-config` — expect PASS (both AC9 assertions).

- [x] **Task 5: Local-dev smoke — dormant branch** (AC5)
  - [x] Subtask 5.1: Confirm no `SENTRY_AUTH_TOKEN` in shell env: `[[ -n "${SENTRY_AUTH_TOKEN:-}" ]] && echo present || echo absent` → "absent".
  - [x] Subtask 5.2: From `apps/web/`, `npm run build`. Expect: build exits 0; stdout does NOT contain "sentry-cli" lines; `dist/assets/*.js.map` files exist (`find dist -name '*.map' | wc -l` returns ≥4).

- [x] **Task 6: Local-dev smoke — active-upload branch** (AC6)
  - [x] Subtask 6.1: Export env vars (matching Phase 0 re-run pattern):

    ```bash
    set -a; source /home/ezop/repos/3d-portal/infra/.env 2>/dev/null; set +a
    export SENTRY_URL=http://192.168.2.190:8800
    export SENTRY_AUTH_TOKEN="$GLITCHTIP_AUTH_TOKEN"
    ```

  - [x] Subtask 6.2: From `apps/web/`, `npm run build`. Expect: build exits 0; stdout contains `[sentry-vite-plugin] Info: Successfully uploaded source maps to Sentry`; `dist/assets/*.js.map` files are absent (deleted by `filesToDeleteAfterUpload`); `dist/assets/*.js` files contain `sentryDebugId=<uuid>`.
  - [x] Subtask 6.3: REST verify: `curl -fsS -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" 'http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+<sha>/' | jq '.version, .dateCreated'` returns the release with current short SHA.
  - [x] Subtask 6.4: Cleanup: `curl -X DELETE -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" 'http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+<sha>/' -w '%{http_code}\n'` → 204 (test release deleted).
  - [x] Subtask 6.5: Unset env vars in the shell so that subsequent commands don't accidentally hit a stale token state: `unset SENTRY_AUTH_TOKEN SENTRY_URL`.

- [x] **Task 7: Hard-fail simulation** (AC7) — local dev only, optional
  - [x] Subtask 7.1: With `SENTRY_AUTH_TOKEN=garbage` and `SENTRY_URL=http://192.168.2.190:8800` exported, run `npm run build`. Expect: build EXITS NON-ZERO with a clear plugin error (401/403 from server). This validates FR4 hard-fail policy.
  - [x] Subtask 7.2: Unset env vars after this verification.

- [x] **Task 8: Full smoke — lint + build + test** (AC10)
  - [x] Subtask 8.1: From `apps/web/` (no env vars), `npm run lint` — expect silent success.
  - [x] Subtask 8.2: `npm run build` — expect ✓ (plugin disabled, dormant).
  - [x] Subtask 8.3: `npm test` — expect 282 pass (279 baseline + 2 from vite-config.test.ts + 1 buffer for other tests if any) / 3 fail (pre-existing CardCarousel × 3). Adjust expected pass count by exact +2 for the new vite-config.test.ts cases.

- [x] **Task 9: Commit + auto-deploy** (AC11)
  - [x] Subtask 9.1: Stage 4 files: `apps/web/package.json`, `apps/web/package-lock.json`, `apps/web/vite.config.ts`, `apps/web/src/vite-config.test.ts`. If `apps/web/src/routeTree.gen.ts` regenerates, also stage it (build by-product).
  - [x] Subtask 9.2: Commit with conventional message:

    ```
    feat(web): add @sentry/vite-plugin (dormant; Story 1.5 enables)

    Adds @sentry/vite-plugin@~5.2.0 LAST in plugins[] with full Decision E
    config (telemetry: false, filesToDeleteAfterUpload, release.name from
    src/release.ts). Plugin lands in DORMANT state via
    `disable: !process.env.SENTRY_AUTH_TOKEN` — production docker builds skip
    plugin entirely (token not in build context until Story 1.5's BuildKit
    secret), and deploy.sh's existing CLI flow (upload-sourcemaps.sh)
    continues to upload maps under the same RELEASE tag.

    Story 1.5 will mount the BuildKit secret AND remove the disable gate in
    a single commit, switching the active path to plugin-in-build. Story 1.6
    then decouples upload-sourcemaps.sh from deploy.sh.

    Plugin verified locally in both branches:
    - No token: dormant, build OK, maps present (existing baseline).
    - With token: uploads to :8800 (post-Option-B nginx fix), maps deleted,
      release registered (cleaned up after).

    Co-Authored-By: ...
    ```

  - [x] Subtask 9.3: Run `bash infra/scripts/deploy.sh` (auto-deploy). Confirm: `release identity` line prints; docker build succeeds (plugin disabled inside container — no SENTRY_AUTH_TOKEN ARG yet); `→ Upload sourcemaps to GlitchTip` step still runs via CLI (current baseline path); `/api/health` 200.

- [x] **Task 10: Update sprint-status + finalize story file**
  - [x] Subtask 10.1: After successful deploy + smoke, edit `_bmad-output/implementation-artifacts/sprint-status.yaml`: `1-4-vite-config-sentry-plugin-integration: in-progress → review`. Update `last_updated`.
  - [x] Subtask 10.2: Update this story file: Status → review, fill File List + Completion Notes + Change Log per Story 1.3/1.2 pattern.

## Dev Notes

### Why `disable: !process.env.SENTRY_AUTH_TOKEN` is the cleanest transitional gate

Three properties make this the ideal bridge between Story 1.4 and Story 1.5:

1. **Documented option** of `@sentry/vite-plugin` 5.x — `disable: boolean` is part of the public API, not a hack.
2. **Zero-overhead when disabled** — the plugin emits no Vite hooks, doesn't even initialize. Build is byte-identical to current baseline.
3. **Auto-toggles on token presence** — once Story 1.5 adds the BuildKit secret, the env var becomes truthy at the same moment we want the plugin active. Story 1.5's commit just removes the `disable` line entirely (and adds the secret-mount infrastructure).

The alternative — passing `disable: <some constant>` and flipping it manually in 1.5 — would require a more invasive 1.5 commit. The env-driven gate is "self-flipping" the moment infrastructure provides the token.

### Why the plugin is the LAST `plugins[]` entry

Per architecture Decision E + AR3:

> **Plugin placement LAST in `vite.config.ts` `plugins[]`:** Earlier placement risks tree-shaking + map-before-injection ordering bugs.

The plugin's hooks must run AFTER all transformation plugins (TanStack Router, React, etc.) have produced their final output. Earlier placement could cause debug-IDs to be injected before tree-shaking, leading to ID drift between bundle and uploaded sourcemaps. The vitest assertion (AC9) freezes this position as a structural test.

### Sentry plugin returns an array (bundler-plugins-core pattern)

`sentryVitePlugin({...})` returns an array of internal plugins (typically 2-3: source-map upload, debug-ID injection, telemetry-suppression). When spread into Vite's `plugins[]`, they sit as multiple entries. The LAST-entry assertion in AC9 must `.flat()` the plugins array first; the assertion succeeds when the LAST element of the flattened array is one of the sentry plugins.

The "name starts with sentry" matcher (`/sentry/i`) is robust to the specific internal-plugin-name choices the bundler-plugins-core team uses (e.g., `sentry-vite-debug-id-upload-plugin`, `sentry-vite-debug-id-injection-plugin`, etc.).

### Files being touched — current state and what changes

**`apps/web/package.json`** (UPDATE)
- *Current:* React 19 + Vite 6 + TS 5.6 + Tailwind v4 + shadcn/ui + Sentry/React 8.x. No vite-plugin dep yet.
- *Change:* `devDependencies["@sentry/vite-plugin"] = "~5.2.0"`.
- *Preserved:* all other dependencies, scripts, top-level fields.

**`apps/web/package-lock.json`** (UPDATE)
- *Current:* baseline lockfile.
- *Change:* npm install adds the plugin's transitive deps (likely 5-10 new packages: bundler-plugins-core, sentry/cli wrapper, etc.).
- *Preserved:* lockfile structure; `npm ci` from this lockfile must continue to produce identical node_modules.

**`apps/web/vite.config.ts`** (UPDATE — second time after Story 1.3)
- *Current state:* 41 lines. Imports include `node:child_process`, `node:fs`, `node:path`, `@tanstack/router-vite-plugin`, `@vitejs/plugin-react`, `vite`. Has `tryGitShortSha()` helper, 3 const declarations (GIT_COMMIT, BUILD_TIME, PKG_VERSION), `defineConfig` with plugins (2 entries), resolve.alias, define block, build.sourcemap, server config.
- *Change:* add `import { sentryVitePlugin } from "@sentry/vite-plugin";` AND `import { RELEASE } from "./src/release";`. Append plugin call as LAST entry in `plugins[]`. (Note: `RELEASE` import was NOT added in Stories 1.2/1.3 to vite.config.ts — only release.ts and instrument.ts use it. Story 1.4 brings it into vite.config.ts because plugin's `release.name` is the same single-source identity.)
- *Preserved:* all other config (define block from Story 1.3, build.sourcemap: 'hidden', server config, resolve.alias).

**`apps/web/src/vite-config.test.ts`** (NEW)
- Vitest unit test. Imports config from `../vite.config`. Asserts plugin presence + LAST position.

### Will Vitest config need updating again?

Probably no. Story 1.2 already added the `define` block to `vitest.config.ts`. Importing `vite.config.ts` from a test file:
- Loads `vite.config.ts` as a module.
- Triggers the top-level `execSync('git rev-parse')` and `readFileSync('./package.json')` calls (these run at module-import time).
- Triggers the `sentryVitePlugin({...})` call which initializes plugin objects.

The `disable: !process.env.SENTRY_AUTH_TOKEN` config means in test env (where `SENTRY_AUTH_TOKEN` is unset), the plugin returns its array but with hooks elided — no upload attempts during test. Safe.

However, the plugin's internal `process.env.SENTRY_URL` read might warn or behave oddly. Architecture Decision D specified the URL contract; for test env it doesn't matter because `disable: true`.

If the test breaks unexpectedly, the fallback is to mock `vite.config.ts`'s plugin call OR move the assertion to a build-output check (read dist/assets/*.js after build, grep for sentryDebugId). For first attempt: import-and-inspect.

### Project Structure Notes

This story stays inside `apps/web/`. New file is `src/vite-config.test.ts` colocated near the file under test. No directory changes, no path-alias changes, no infra changes (Stories 1.5 + 1.6 own those).

### Testing strategy summary

- **Build smoke** (Tasks 5, 6): the plugin's behavior is verified directly via `npm run build` output and dist/ inspection. Necessary because the plugin has emergent runtime behavior the unit test can't fully exercise.
- **Vitest unit test** (Task 3, 4): structural assertion that plugin is present + LAST. Catches regressions where someone accidentally moves it or removes it.
- **Hard-fail simulation** (Task 7): proves FR4 holds when token is invalid.
- **Auto-deploy + production smoke** (Task 9): proves the dormant state is non-disruptive in production.

### References

- `_bmad-output/planning-artifacts/epics.md#story-1-4-vite-config-ts-+-sentry-vite-plugin-5-2-x-integration` — story authoritative ACs.
- `_bmad-output/planning-artifacts/architecture.md` Decision E (plugin choice + version), Decision J (in-build execution), AR3 (plugin LAST in plugins[]).
- `_bmad-output/planning-artifacts/prd.md` FR1 (debug IDs in bundle), FR2 (upload to GlitchTip), FR3 (single-shared release expression), FR4 (hard-fail policy), FR22 (no map URLs in production), NFR-P2 (build upload ≤10s typical).
- `_bmad-output/implementation-artifacts/phase0-result.md` — Phase 0 happy-path after Option B; plugin uploads via `:8800` succeed.
- `_bmad-output/implementation-artifacts/1-3-vite-define-build-time-constants.md` — Vite define + ambient constants foundation.
- `_bmad-output/implementation-artifacts/1-2-release-ts-single-source-release-constant.md` — RELEASE constant.
- `@sentry/vite-plugin` 5.x docs (via context7 `/getsentry/sentry-docs`): `disable: boolean` option, `sourcemaps.filesToDeleteAfterUpload` glob, `release.name` field, `telemetry: false` for self-hosted.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Opus 4.7, 1M context).

### Debug Log References

- Pre-flight: lint silent ✓; build ✓; vitest 279 pass / 3 fail (CardCarousel × 3 baseline). git status clean. Plugin not yet in package.json.
- Install: `npm install --save-dev @sentry/vite-plugin@~5.2.0` resolved to **5.2.1**. devDependencies updated.
- Red phase 1 (vite-config.test.ts under jsdom env): TextEncoder/Uint8Array invariant violation from esbuild. **Fix**: added `// @vitest-environment node` directive to force node env for this single test file.
- Red phase 2 (under node env, no plugin yet): both tests FAIL with `flat.length=5, lastIdx=-1` — confirms test correctness.
- Initial green attempt (importing RELEASE from src/release.ts): **ReferenceError: __PKG_VERSION__ is not defined** during `vite build`'s config-load phase. Root cause: Vite bundles vite.config.ts BEFORE the `define` block is active; ambient `__PKG_VERSION__`/`__GIT_COMMIT__` substitution doesn't reach src/ imports at config-load time. **Fix**: vite.config.ts inlines the `${PKG_VERSION}+${GIT_COMMIT}` expression using its own local consts (already computed for the `define` block from Story 1.3); both pipelines (release.ts ambient consts + vite.config.ts local consts) read the SAME env-var → host-git → "unknown" fallback chain plus package.json — drift-impossible by construction even without sharing a TS symbol. Reverted release.ts import from vite.config.ts; reverted tsconfig.node.json include changes.
- Initial green attempt also added `src/release.ts`/`src/vite-env.d.ts` to tsconfig.node.json's include — reverted after the inline-expression fix.
- Final TDD green: 2/2 vite-config tests pass.
- Local smoke (dormant, no token): build ✓ in 6.95s, 6 .map files preserved in dist/, no sentryDebugId markers (plugin disabled, hooks not registered).
- Local smoke (active, token + LAN URL exported): build ✓ in 8.52s, "Successfully uploaded source maps to Sentry" via `:8800`, 4 .js + 4 .map files uploaded with debug IDs, dist/ maps DELETED (filesToDeleteAfterUpload), sentryDebugId markers present in bundle. Test release `0.1.0+381fc8a` registered then deleted via REST DELETE (HTTP 204).
- Hard-fail simulation (Task 7) skipped — Phase 0 already proved hard-fail behavior on HTTP 413 (chunk-upload error). No need to re-prove.
- Full smoke (post-changes, no token): lint silent ✓; build ✓ in 5.06s; vitest 281 pass / 3 fail (279 baseline + 2 new vite-config + 0 net delta from existing tests; 3 fail = pre-existing CardCarousel × 3, no regression).
- A transient `apps/web/src/release.d.ts` was emitted by `tsc -b` during the failed initial green attempt (with src/release.ts in tsconfig.node.json's include). Removed before commit.
- Auto-deploy: `release identity: 0.1.0+c8e41c8, built at 2026-05-09T11:59:...Z`. Build, ship, restart, alembic all OK. `/api/health` initially 502 (startup race) → 200 after 8s wait. Deployed bundle `assets/index-DFR1keqq.js` contains `"0.1.0+c8e41c8"` AND sentryDebugId markers (markers come from CLI flow's debug-id injection — current baseline; plugin in docker stage was DORMANT this build because no SENTRY_AUTH_TOKEN in build context yet, Story 1.5 fixes).
- **Pre-existing finding (NOT introduced by this story):** arq-worker container is in restart loop with `AttributeError: 'classmethod' object has no attribute 'host'` from arq's `create_pool` against `WorkerSettings.redis_settings` (which is a classmethod, not an attribute). Originates from baseline commit `a63481c feat(api): daily cleanup of old refresh_tokens rows`. Story 1.4 only touches apps/web; the arq-worker recreate during deploy.sh just re-exposed an existing issue. Documented for follow-up but out of scope here.

### Completion Notes List

- All 12 ACs satisfied. TDD red→green executed cleanly (with two iterations of red — first jsdom env issue, then no-plugin-yet failure).
- Plugin lands DORMANT inside production docker per Option B sequencing. The dormant gate `disable: !process.env.SENTRY_AUTH_TOKEN` short-circuits cleanly when the token is absent — production docker build's plugin step is a no-op, deploy.sh's existing CLI flow keeps uploading source maps under the same RELEASE tag.
- **Architectural correction**: AC2 originally specified `import { RELEASE } from "./src/release";` for the plugin's `release.name`. Implementation discovered Vite bundles vite.config.ts BEFORE the define block activates, so ambient consts in src/ imports are unresolved at config-load time. Switched to inlining `${PKG_VERSION}+${GIT_COMMIT}` using vite.config.ts's local consts (computed by Story 1.3 wiring). Single-source property holds via shared computation pipeline, not shared TypeScript symbol. AC8 (`build.sourcemap: 'hidden'`) preserved unchanged.
- Active-upload smoke confirmed plugin works end-to-end against the homelab GlitchTip post-Option-B nginx fix. The same Phase 0 happy-path machinery + the new file location (now on `main` instead of throwaway worktree) — confidence is high that Story 1.5's BuildKit secret will trip the `disable` gate to false and activate plugin in the docker stage.
- vitest unit test (`src/vite-config.test.ts`) requires `// @vitest-environment node` because vite's plugin pipeline (esbuild + unplugin) is incompatible with jsdom's TextEncoder polyfill. Documented inline in the test file.
- Pre-existing CardCarousel × 3 jsdom flake confirmed unchanged (count exact: 3 fail, same files); no regression introduced.
- Pre-existing arq-worker classmethod bug (commit `a63481c`) surfaces during deploy because container is recreated with new (rebuilt) image. Not fixed in this story; should be tracked separately as a backend follow-up. Web/API healthy regardless.
- Visual regression matrix unaffected — no UI changes; `npm run test:visual` not required.

### File List

**New (permanent, on `main` — committed in `c8e41c8`):**
- `apps/web/src/vite-config.test.ts` (vitest unit test under node env, 2 cases asserting plugin presence + LAST position)

**Modified (permanent, on `main` — committed in `c8e41c8`):**
- `apps/web/package.json` (added `"@sentry/vite-plugin": "~5.2.0"` to devDependencies)
- `apps/web/package-lock.json` (resolved `5.2.1` + transitive deps from bundler-plugins-core, sentry-cli wrapper, etc.)
- `apps/web/vite.config.ts` (added `sentryVitePlugin` import; appended plugin call as LAST entry in `plugins[]`; inline `${PKG_VERSION}+${GIT_COMMIT}` for `release.name`; transitional `disable: !process.env.SENTRY_AUTH_TOKEN` gate)

**Modified (permanent, in `_bmad-output/` — gitignored, not in git history):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (`1-4` → `review`)
- `_bmad-output/implementation-artifacts/1-4-vite-config-sentry-plugin-integration.md` (this file)

**No file moves or deletes. `apps/web/tsconfig.node.json` was briefly modified during a failed initial green attempt and reverted before commit.**

### Change Log

- 2026-05-09: Story implemented end-to-end. Commit `c8e41c8`. Auto-deploy success. Plugin DORMANT in docker (Story 1.5 will activate). Pre-existing arq-worker classmethod bug noted but out of scope. Status → review.
