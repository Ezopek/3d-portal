# Story 1.2: `apps/web/src/release.ts` — Single-Source RELEASE Constant

Status: review

> **Story role:** First consumer of the `__GIT_COMMIT__` + `__PKG_VERSION__` ambient constants shipped by Story 1.3 (commit `946fb52`). Pins AR1: `RELEASE = "${package.version}+${git_short_sha}"`. After this story, `instrument.ts` reports the new `RELEASE` to GlitchTip; the legacy `VITE_PORTAL_VERSION` env-var path is gone from `apps/web/src/`. **Infra-side `VITE_PORTAL_VERSION` (Dockerfile, docker-compose, deploy.sh, package.json) STAYS unchanged** — only the in-code TypeScript expression is replaced.

## Story

As any code that needs the release tag (this story's `instrument.ts`; future Story 2.2 dynamic tags; future Story 2.5 `glitchtip-triage.sh` parsing release-SHA from events; Story 1.6 CLI fallback parity),
I want one single TypeScript-typed `RELEASE` constant assembled from `package.json#version` + `git_short_sha` via Vite-injected ambient constants,
so that build-time and runtime release identity cannot drift — drift produces a TypeScript compile error or test failure, not a runtime mystery.

## Acceptance Criteria

1. **AC1 — `apps/web/src/release.ts` exists, exports `RELEASE: string`.** New file at exact path. Body:

   ```typescript
   /**
    * Single-source release identity for this build.
    *
    * Format: `<pkg.version>+<git_short_sha>` (e.g., `"0.1.0+946fb52"`).
    *
    * The two halves are injected at build time by Vite `define` (see
    * `apps/web/vite.config.ts`). Both `vite serve` (dev) and `vite build`
    * (prod) resolve the values; `__GIT_COMMIT__` falls back to `"unknown"`
    * if no git context is available (off-LAN CI, etc.).
    *
    * Drift between this expression and any other place that reports a
    * release tag = TypeScript compile error or `release.test.ts` failure.
    */
   export const RELEASE: string = `${__PKG_VERSION__}+${__GIT_COMMIT__}`;
   ```

   The file is small by design — no imports, no helpers, no factories. The expression IS the contract.

2. **AC2 — Importable as `@/release`.** From any TypeScript file under `apps/web/src/`, `import { RELEASE } from "@/release";` succeeds (path alias `@` → `apps/web/src/`, baseline tsconfig).

3. **AC3 — Format matches `^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$`.** A vitest unit test asserts the format. For the current package.json (`"version": "0.1.0"`) and the host's `git rev-parse --short HEAD` resolving to a 7-char hex SHA, `RELEASE` matches `^0\.1\.0\+[0-9a-f]{7,}$`. The test uses a relaxed regex covering the documented format space (numeric semver + plus-sign + hex-or-unknown).

4. **AC4 — Vitest can resolve the ambient constants.** `apps/web/vitest.config.ts` is updated to include a `define` block identical in shape to `apps/web/vite.config.ts`'s `define` block. Constants resolve at test time with the same fallback chain (env-var → host git rev-parse → `"unknown"`). The shared compute logic (`tryGitShortSha`, env-var read, package.json read) is duplicated cleanly between the two config files (small, throwaway code; do NOT introduce a shared helper module — keeps each config self-contained).

5. **AC5 — `instrument.ts` consumes `RELEASE` instead of `VITE_PORTAL_VERSION`.** `apps/web/src/instrument.ts` is modified:
   - Add: `import { RELEASE } from "@/release";` after the `@sentry/react` import.
   - Replace: `release: import.meta.env.VITE_PORTAL_VERSION ?? "0.1.0",` → `release: RELEASE,`.
   - Existing `dsn`, `environment`, `sampleRate`, `tracesSampleRate`, `Sentry.setTag("service", "web")` lines stay unchanged.
   - The `if (typeof dsn === "string" && dsn !== "")` gate stays — DSN-empty no-op path unchanged.

6. **AC6 — `instrument.test.ts` is updated to match the new contract.** `apps/web/src/instrument.test.ts`:
   - Remove the line `vi.stubEnv("VITE_PORTAL_VERSION", "1.2.3");` (env var is no longer consumed).
   - Replace the assertion `expect(call.release).toBe("1.2.3");` with `expect(call.release).toMatch(/^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$/);` — same regex as Story 1.2's `release.test.ts`. The exact `RELEASE` value is non-deterministic at test time (depends on host git SHA), so the test asserts FORMAT, not value.
   - Other existing assertions (DSN, environment, setTag) stay intact.

7. **AC7 — `vite-env.d.ts` no longer declares `VITE_PORTAL_VERSION`.** `apps/web/src/vite-env.d.ts` removes `readonly VITE_PORTAL_VERSION?: string;` from `interface ImportMetaEnv`. The other two readonly fields (`VITE_SENTRY_DSN`, `VITE_ENVIRONMENT`) stay. `interface ImportMeta` block stays. The 3 `declare const __GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__` lines (added by Story 1.3) stay.

8. **AC8 — Repository-wide grep for `VITE_PORTAL_VERSION` in `apps/web/src/` returns zero matches.** Verifiable via `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/`. Currently 3 matches: `vite-env.d.ts:5`, `instrument.ts:9`, `instrument.test.ts:30`. After this story: 0 matches. The env var continues to flow through baseline infra (Dockerfile ARG, docker-compose build args, deploy.sh export from `infra/.env`) but is no longer read by any TypeScript code in `src/`.

9. **AC9 — `npm run lint` and `npm run typecheck` (via `npm run build`) both pass.** No new ESLint warnings (`--max-warnings=0` floor preserved), no TypeScript errors. The cast-less expression-template syntax (`\`${__PKG_VERSION__}+${__GIT_COMMIT__}\``) infers as `string` automatically; no `as` cast needed.

10. **AC10 — `npm run test` (vitest) passes.** All existing 70 test files pass — including the 3 pre-existing flake failures in `src/ui/custom/CardCarousel.test.tsx` (NOT introduced by this story; documented in Story 1.3 completion notes). The new `release.test.ts` PASSES. The updated `instrument.test.ts` PASSES with the regex assertion.

11. **AC11 — Auto-deploy after merge succeeds + GlitchTip events on prod report new RELEASE format.** Per memory `feedback_auto_deploy_dev`, `bash infra/scripts/deploy.sh` runs immediately after the commit. Deploy chain: build → ship → restart → alembic → `/api/health` 200. Smoke verification: trigger any prod event (e.g., `POST /api/admin/sentry-test`) and confirm via REST that the event's `release` field matches the new format `0.1.0+<git_sha>` (NOT plain `0.1.0`).

## Tasks / Subtasks

- [x] **Task 1: Pre-flight** (clean baseline)
  - [x] Subtask 1.1: From `apps/web/`, run `npm run lint`, `npm run build` (covers tsc + vite build), `npm run test` — record baseline: lint clean, build OK, vitest 3 fail / 276 pass (the 3 are pre-existing CardCarousel jsdom flake; do NOT attempt to fix them in this story).
  - [x] Subtask 1.2: Confirm `git status` clean. From repo root: `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/` returns 3 matches (instrument.ts:9, instrument.test.ts:30, vite-env.d.ts:5). This is the "before" state.

- [x] **Task 2: TDD red phase — write `release.test.ts` first** (AC3)
  - [x] Subtask 2.1: Create `apps/web/src/release.test.ts`:

    ```typescript
    import { describe, expect, it } from "vitest";

    import { RELEASE } from "./release";

    describe("RELEASE", () => {
      it("matches the documented format `<semver>+<sha-or-unknown>`", () => {
        expect(RELEASE).toMatch(/^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$/);
      });

      it("contains the package.json version as the prefix", async () => {
        const pkg = (await import("../package.json")).default;
        expect(RELEASE.startsWith(`${pkg.version}+`)).toBe(true);
      });

      it("does not embed a literal `__PKG_VERSION__` token (define must substitute)", () => {
        expect(RELEASE).not.toContain("__PKG_VERSION__");
        expect(RELEASE).not.toContain("__GIT_COMMIT__");
      });
    });
    ```

  - [x] Subtask 2.2: Run `npm run test -- release` from `apps/web/` — expect FAIL (release.ts doesn't exist yet → ImportError). This is the red phase.

- [x] **Task 3: TDD green phase — create `release.ts`** (AC1, AC2)
  - [x] Subtask 3.1: Create `apps/web/src/release.ts` with the documented body (see AC1).
  - [x] Subtask 3.2: Run `npm run test -- release` again — expect a NEW failure: `ReferenceError: __PKG_VERSION__ is not defined` (vitest doesn't have the `define` yet). Still red, but different reason — confirms the file is now reached.

- [x] **Task 4: Wire vitest `define`** (AC4)
  - [x] Subtask 4.1: Modify `apps/web/vitest.config.ts` to add the same `define` block as `vite.config.ts`. Cleanest implementation: copy the `tryGitShortSha`, env-var read, and `JSON.parse(readFileSync('./package.json', 'utf-8')).version as string` lines verbatim from `vite.config.ts`. Add the matching `import { execSync } from "node:child_process"; import { readFileSync } from "node:fs";` at the top. Wire `define: { __GIT_COMMIT__: ..., __BUILD_TIME__: ..., __PKG_VERSION__: ... }` inside `defineConfig({ ... })`.
  - [x] Subtask 4.2: Run `npm run test -- release` — expect PASS (3 tests in `release.test.ts` green). This is the green phase.
  - [x] Subtask 4.3: Refactor consideration (optional): the duplication between `vite.config.ts` and `vitest.config.ts` is ~10 lines. **Do NOT extract to a shared helper module yet.** Keeping each config self-contained avoids the "config-of-configs" complexity surface; the duplication is small, the contract is small, the change frequency is low. Future story can revisit if a third config (e.g., a Storybook or Vitest-browser config) materializes.

- [x] **Task 5: Replace `VITE_PORTAL_VERSION` consumer in `instrument.ts`** (AC5)
  - [x] Subtask 5.1: Modify `apps/web/src/instrument.ts`:
    - Add import: `import { RELEASE } from "@/release";` after the `import * as Sentry from "@sentry/react";` line (preserve import order: external → `@/`-aliased → relative).
    - Replace `release: import.meta.env.VITE_PORTAL_VERSION ?? "0.1.0",` → `release: RELEASE,`.
  - [x] Subtask 5.2: Run `npm run typecheck` (or `npx tsc -b --noEmit` from `apps/web/`) — expect PASS (RELEASE is `string`, satisfies Sentry's `release` option).

- [x] **Task 6: Update `instrument.test.ts`** (AC6)
  - [x] Subtask 6.1: Modify `apps/web/src/instrument.test.ts`:
    - Remove the line `vi.stubEnv("VITE_PORTAL_VERSION", "1.2.3");` from the first test's setup.
    - Replace `expect(call.release).toBe("1.2.3");` with `expect(call.release).toMatch(/^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$/);`.
  - [x] Subtask 6.2: Run `npm run test -- instrument` — expect both tests in instrument.test.ts to PASS.

- [x] **Task 7: Remove `VITE_PORTAL_VERSION` from `vite-env.d.ts`** (AC7, AC8)
  - [x] Subtask 7.1: Modify `apps/web/src/vite-env.d.ts`: delete the line `readonly VITE_PORTAL_VERSION?: string;`. Keep the other 2 readonly fields (`VITE_SENTRY_DSN`, `VITE_ENVIRONMENT`) and the `interface ImportMeta` block + ambient `__GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__` lines.
  - [x] Subtask 7.2: Verify `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/` returns ZERO matches.
  - [x] Subtask 7.3: Run `npm run typecheck` again — expect PASS (no consumer in src/ references the removed declaration).

- [x] **Task 8: Full smoke test** (AC9, AC10)
  - [x] Subtask 8.1: From `apps/web/`, run `npm run lint` — expect silent success.
  - [x] Subtask 8.2: Run `npm run build` — expect `✓ built in <N>s`.
  - [x] Subtask 8.3: Run `npm run test` — expect 70 test files run, 3 fail (CardCarousel pre-existing flake), 276+1 pass (276 baseline + 3 new in release.test.ts; the +3 comes from release.test.ts having 3 it() blocks). The PRE-EXISTING fail count must be exactly 3 — if any test other than CardCarousel × 3 fails, this story has introduced a regression and must fix it before commit.

- [x] **Task 9: Commit + auto-deploy** (AC11)
  - [x] Subtask 9.1: Stage 6 files: `apps/web/src/release.ts` (NEW), `apps/web/src/release.test.ts` (NEW), `apps/web/vitest.config.ts`, `apps/web/src/instrument.ts`, `apps/web/src/instrument.test.ts`, `apps/web/src/vite-env.d.ts`. If `apps/web/src/routeTree.gen.ts` got regenerated by `npm run build`, also stage it (same handling as Story 1.3 — legitimate build by-product).
  - [x] Subtask 9.2: Commit with conventional message:

    ```
    feat(web): single-source RELEASE constant

    Adds apps/web/src/release.ts exporting `RELEASE = ${PKG_VERSION}+${GIT_COMMIT}`,
    consuming the ambient constants wired up in commit 946fb52 (Story 1.3).
    instrument.ts now reports `release: RELEASE` instead of reading the legacy
    `VITE_PORTAL_VERSION` env var directly. The env var still flows through
    baseline infra (Dockerfile, docker-compose, deploy.sh) for backwards
    compatibility but is no longer referenced from any TypeScript file under
    apps/web/src/ — verifiable via `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/`
    returning zero matches.

    Vitest config picks up the same `define` block as vite.config.ts so the
    new `release.test.ts` (and any future tests) can resolve `__PKG_VERSION__`
    and `__GIT_COMMIT__` at test time. Each config keeps its own copy of the
    ~10-line compute block — a shared helper module would be premature
    factoring for a 2-config surface.

    Co-Authored-By: ...
    ```

  - [x] Subtask 9.3: Run `bash infra/scripts/deploy.sh` (auto-deploy per memory). Confirm the existing `release identity:` echo line prints, the build + ship + restart + alembic chain succeeds, and `/api/health` returns 200.
  - [x] Subtask 9.4: Production smoke: trigger a Sentry test event (e.g., `curl -X POST -H "X-Portal-Client: web" -b "<auth-cookie>" https://3d.ezop.ddns.net/api/admin/sentry-test` if the auth cookie is available, OR open the production page in a browser and trigger any error). Then via REST: `curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" 'http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/issues/?statsPeriod=10m&limit=1' | jq '.[0].lastSeen, .[0].title, .[0].metadata'`. Expect at least one event tagged with the new release format. (The event's `release` field check is the smoke; if no event is easy to trigger, AC11 falls back to the deploy stdout `release identity:` line + `/api/health` 200 as sufficient evidence.)

- [x] **Task 10: Update sprint-status + finalize story file**
  - [x] Subtask 10.1: After successful deploy + smoke, edit `_bmad-output/implementation-artifacts/sprint-status.yaml`: `1-2-release-ts-single-source-release-constant: in-progress → review`. Update `last_updated`.
  - [x] Subtask 10.2: Update this story file: Status → review, fill File List + Completion Notes + Change Log per Story 1.3 pattern.

## Dev Notes

### Why this story doesn't touch infra-side `VITE_PORTAL_VERSION`

The infra layer (Dockerfile ARG, docker-compose build arg, deploy.sh export from `infra/.env`, `infra/.env` itself) keeps `VITE_PORTAL_VERSION` because:

- The env var is harmless when unused; removing it from infra would invite "what was that var?" archaeology in 6 months.
- `deploy.sh` reads it via `read_env_var` and re-exports as `PORTAL_VERSION` (already used as image tag, compose service version field, alembic migration target). Removing it would cascade.
- Architecture's deferred Phase 2 work (backend Sentry polish) might want a parallel `release` value for the FastAPI side; keeping the infra plumbing means future stories can re-introduce the consumer without re-doing the wiring.

The grep AC8 is intentionally scoped to `apps/web/src/` — TypeScript source files only. **Do not delete the env var from `infra/.env`, Dockerfile, docker-compose.yml, or deploy.sh in this story.**

### TDD red→green→refactor sequence

Project-context says TDD applies (resumed from Story 1.2 onward). For this story the canonical sequence:

1. **Red 1:** Write `release.test.ts`, run vitest → ImportError (release.ts missing).
2. **Red 2:** Create `release.ts` → ReferenceError (`__PKG_VERSION__` not defined in vitest).
3. **Green:** Update `vitest.config.ts` with matching `define` block → tests pass.
4. **Refactor:** Replace consumer in `instrument.ts`, update its test, remove dead declaration in `vite-env.d.ts`. Tests stay green throughout.

Each red→green transition is a verifiable signal — don't skip them. Skipping wastes the discipline's primary value (catching test-vs-impl inversions where the test is wrong).

### Why duplicate the `define` compute logic between `vite.config.ts` and `vitest.config.ts` instead of factoring out

The 10-ish lines (`tryGitShortSha` function + 3 const declarations + the JSON.parse-package.json read) are about as boilerplate as TypeScript permits. Pulling them into a shared module (e.g., `apps/web/build-constants.ts`) would:

- Add a 4th file to maintain alongside `vite.config.ts`, `vitest.config.ts`, `release.ts`.
- Introduce import-resolution edge cases when this helper itself is being loaded by a Vite config that's itself loaded by ts-node / esbuild internally.
- Not actually reduce churn surface — both configs need the exact same shape, and any change is mirror-trivial.

The duplication is acknowledged and acceptable. If a third config (Storybook, Vitest browser-mode, etc.) ever lands, that's the time to revisit.

### Files being touched — current state and what changes

**`apps/web/src/release.ts`** (NEW) — single export. ~10 lines including JSDoc.

**`apps/web/src/release.test.ts`** (NEW) — vitest unit test, 3 it() blocks (format regex, prefix matches package.json, no literal define-tokens leaked).

**`apps/web/vitest.config.ts`** (UPDATE)
- *Current state:* imports from `vitest/config`, defines `resolve.alias`, `test.environment: "jsdom"`, `test.globals: false`, `test.exclude: [..., "**/tests/visual/**"]`. ~13 lines.
- *Changes:* add `import { execSync } from "node:child_process"; import { readFileSync } from "node:fs";` at top. Compute 3 consts (mirrors `vite.config.ts`). Add `define: { ... }` to the config object next to `resolve` / `test`.
- *Preserved:* the `test.environment`, `test.globals`, `test.exclude` blocks; the `resolve.alias`.

**`apps/web/src/instrument.ts`** (UPDATE)
- *Current state:* imports `@sentry/react`, gates `Sentry.init` on `VITE_SENTRY_DSN`, hardcodes `release: import.meta.env.VITE_PORTAL_VERSION ?? "0.1.0"`, sets `service` tag, exports `Sentry`.
- *Changes:* add `import { RELEASE } from "@/release";`. Replace the `release:` line.
- *Preserved:* DSN gate, environment, sampleRate, tracesSampleRate, setTag, the `export { Sentry }`. **Story 2.2 will significantly modify this file later** (additional setTag calls for static identity tags); do NOT pre-emptively land Story 2.2's work here — keep the diff minimal.

**`apps/web/src/instrument.test.ts`** (UPDATE)
- *Current state:* mocks `@sentry/react` init + setTag, has 2 tests: "calls Sentry.init with the DSN" + "no-ops when VITE_SENTRY_DSN is empty". The first test stubs `VITE_PORTAL_VERSION` and asserts `call.release === "1.2.3"`.
- *Changes:* remove the `VITE_PORTAL_VERSION` stubEnv line; replace the assertion with regex match.
- *Preserved:* DSN, environment, setTag assertions; the no-op test; the mock setup; `vi.resetModules()` and `vi.unstubAllEnvs()` lifecycle hooks.

**`apps/web/src/vite-env.d.ts`** (UPDATE)
- *Current state:* Story 1.3 added 3 `declare const` lines for ambient constants. `interface ImportMetaEnv` has 3 readonly fields including `VITE_PORTAL_VERSION`.
- *Changes:* delete the `VITE_PORTAL_VERSION` line from the interface.
- *Preserved:* `/// <reference types="vite/client" />` directive, `VITE_SENTRY_DSN` + `VITE_ENVIRONMENT` readonly fields, `interface ImportMeta`, the 3 `declare const` lines.

### Project Structure Notes

This story stays inside `apps/web/src/` (frontend module) for the consumer-side change + adds 2 NEW files at the same level as `instrument.ts` (top-level src/). The new test colocates next to the source under test (project convention: vitest tests colocated with `*.test.ts` infix). No file moves, no deletes, no path-alias changes.

### Test plan

- `release.test.ts` covers: format regex (AC3), prefix-matches-package.json (AC2 indirectly + ensures the SHA didn't accidentally swap with the version), and the no-literal-token check (catches a regression where vitest config drops the `define` and the test starts comparing against the string `__PKG_VERSION__+__GIT_COMMIT__`).
- `instrument.test.ts` regression-protected: the 2 baseline tests stay; the assertion is loosened to a format match instead of an exact-value match.
- No visual regression needed — no UI changes.

### References

- `_bmad-output/planning-artifacts/epics.md#story-1-2-apps-web-src-release-ts-single-source-release-constant` — story authoritative ACs.
- `_bmad-output/planning-artifacts/architecture.md` AR1 (RELEASE expression pinned), Decision G (single-source release).
- `_bmad-output/planning-artifacts/prd.md` FR3 (single-shared-expression invariant).
- `_bmad-output/implementation-artifacts/1-3-vite-define-build-time-constants.md` — previous story; intelligence on Node 24 nvm pattern, vitest separate config (this story owns the merge), pre-existing CardCarousel flake (don't fix).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `1-3 = review`, `epic-1 = in-progress`.
- Commit `946fb52` (Story 1.3) — added `__GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__` define + ambient declarations + Dockerfile/compose/deploy.sh wiring.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Opus 4.7, 1M context).

### Debug Log References

- Pre-flight: `npm run lint` silent ✓; `npm run build` ✓ built in 5.06s; vitest 3 fail (CardCarousel pre-existing) / 276 pass; `grep VITE_PORTAL_VERSION` in src/ = 3 matches (instrument.ts:9, instrument.test.ts:30, vite-env.d.ts:5).
- Red 1: `npm test -- src/release` → ImportError (release.ts missing). Confirms test reaches missing-file failure mode.
- Red 2: After creating release.ts → `ReferenceError: __PKG_VERSION__ is not defined` (vitest config has no define yet). Confirms file is loaded but symbol missing.
- Green: After updating vitest.config.ts with define block → 3/3 release tests pass in 5ms.
- Final smoke: lint silent ✓, build ✓ built in 5.22s, vitest 279 pass / 3 fail (276 baseline + 3 new release.test.ts; 3 fail = pre-existing CardCarousel × 3, no regression). `grep VITE_PORTAL_VERSION` in src/ = 0 matches (AC8 ✓).
- Auto-deploy (`bash infra/scripts/deploy.sh`): full chain success. Key log line: `release identity: 0.1.0+381fc8a, built at 2026-05-09T11:44:39Z`. `/api/health` → HTTP 200.
- Production smoke: `curl https://3d.ezop.ddns.net/assets/index-Cxk_ZpYx.js | grep -oE '"0\.1\.0\+[0-9a-f]+"'` returned `"0.1.0+381fc8a"` — the RELEASE constant is end-to-end visible in the deployed bundle. This was the verification AC6 of Story 1.3 deferred to Story 1.2 (no consumer existed at 1.3 time).

### Completion Notes List

- All 11 ACs satisfied. TDD red→red→green→refactor sequence executed cleanly with both red phases producing distinct, verifiable failure modes (ImportError → ReferenceError → green).
- The architecture's pinned RELEASE expression `${package.version}+${git_short_sha}` lands as `\`${__PKG_VERSION__}+${__GIT_COMMIT__}\`` template literal in release.ts — TypeScript infers `string` automatically, no `as` cast needed.
- `vitest.config.ts` and `vite.config.ts` now duplicate the ~10-line compute block (`tryGitShortSha` + 3 const declarations + define). This duplication is intentional per Dev Notes — extraction to a shared helper is premature factoring for a 2-config surface.
- `instrument.test.ts` regex assertion is loosened from exact-match (`"1.2.3"`) to format-match (`/^\d+\.\d+\.\d+(\+[0-9a-f]+|\+unknown)$/`) because the test-time RELEASE value is host-dependent (host's git short SHA, which is the test runner's HEAD).
- `vite-env.d.ts` no longer declares `VITE_PORTAL_VERSION` — verifiable via `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/` returning zero matches. The env var continues to flow through baseline infra (Dockerfile, docker-compose, deploy.sh, infra/.env) for backwards compatibility but no TypeScript file in src/ references it.
- Production deployment commit `381fc8a` is the SECOND deploy in this session (first was `946fb52` for Story 1.3). End-to-end RELEASE chain now visible in production: Vite define injects → release.ts exports `RELEASE` → instrument.ts passes to Sentry SDK → bundled into `dist/assets/index-Cxk_ZpYx.js` → served via `https://3d.ezop.ddns.net/assets/index-Cxk_ZpYx.js`. Future events emitted to GlitchTip will carry `release: "0.1.0+381fc8a"`.
- Pre-existing CardCarousel × 3 jsdom flake confirmed unchanged (count exact: 3 fail same files); no regression introduced by this story.
- `routeTree.gen.ts` was NOT regenerated by build this round (no new routes in src/routes/) — clean diff.
- Visual regression matrix unaffected — no UI changes; `npm run test:visual` not required per spec.

### File List

**New (permanent, on `main` — committed in `381fc8a`):**
- `apps/web/src/release.ts`
- `apps/web/src/release.test.ts`

**Modified (permanent, on `main` — committed in `381fc8a`):**
- `apps/web/vitest.config.ts` (added 11 lines: 2 imports + 3 const + 5-line define block, mirroring vite.config.ts)
- `apps/web/src/instrument.ts` (added `import { RELEASE } from "@/release";`; replaced `release` field value with `RELEASE`)
- `apps/web/src/instrument.test.ts` (removed `vi.stubEnv("VITE_PORTAL_VERSION", ...)` line; loosened assertion to regex format match)
- `apps/web/src/vite-env.d.ts` (removed `readonly VITE_PORTAL_VERSION?: string;` from `interface ImportMetaEnv`)

**Modified (permanent, in `_bmad-output/` — gitignored, not in git history):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (`1-2 → in-progress → review`)
- `_bmad-output/implementation-artifacts/1-2-release-ts-single-source-release-constant.md` (this file)

**No file moves or deletes.**

### Change Log

- 2026-05-09: Story implemented end-to-end. Commit `381fc8a`. Auto-deploy success. Production bundle carries literal `"0.1.0+381fc8a"`. Status → review.
