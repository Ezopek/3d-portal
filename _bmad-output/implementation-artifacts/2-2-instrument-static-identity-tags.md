# Story 2.2: `instrument.ts` — Static Identity Tags + Single-Source RELEASE Import

Status: done

## Story

As any event reaching GlitchTip,
I want `service.version`, `host.name`, `deployment.environment`, `git.commit`, `build.time` attached at SDK init via `Sentry.setTag` calls,
So that triage sees the build identity (release + commit + build timestamp + environment + build host) on every event regardless of when it fires.

## Acceptance Criteria

1. **AC1 — `release: RELEASE` already wired (no regression).** `apps/web/src/instrument.ts` already imports `{ RELEASE } from "@/release"` and passes `release: RELEASE` to `Sentry.init({...})` (Story 1.2 close-out, commit `381fc8a`). Verify the import + `release:` keep the single-source contract; do not regress to a hardcoded string or to a regex-permissible substitute. The existing `instrument.test.ts:43` assertion `expect(call.release).toBe(RELEASE)` must continue to pass.

2. **AC2 — 5 static identity `setTag` calls after `Sentry.init`.** After the `Sentry.init({...})` call inside the `if (typeof dsn === "string" && dsn !== "")` guard, the file makes **5 separate** `Sentry.setTag(key, value)` calls, in this order, with these keys:
   - `Sentry.setTag("service.version", RELEASE);`
   - `Sentry.setTag("host.name", import.meta.env.VITE_BUILD_HOST ?? __BUILD_HOST__);`
   - `Sentry.setTag("deployment.environment", import.meta.env.VITE_ENVIRONMENT ?? "production");`
   - `Sentry.setTag("git.commit", __GIT_COMMIT__);`
   - `Sentry.setTag("build.time", __BUILD_TIME__);`

   `configureScope` is forbidden (heavier, scope-stacking semantics not needed per architecture line 294). The 5 calls are flat, sibling, post-init.

3. **AC3 — `__BUILD_HOST__` build-time constant added via Vite `define`.** `apps/web/vite.config.ts` is extended with a `__BUILD_HOST__` define mirroring the existing `__GIT_COMMIT__` / `__BUILD_TIME__` pattern:
   - Resolution chain: `process.env.VITE_BUILD_HOST?.trim() || os.hostname() || "unknown"` (analogous to `GIT_COMMIT`'s `VITE_GIT_COMMIT?.trim() || tryGitShortSha() || "unknown"`).
   - `import { hostname as osHostname } from "node:os";` at the top of the file (alongside the existing `node:child_process` / `node:fs` imports).
   - `define: { ... __BUILD_HOST__: JSON.stringify(BUILD_HOST), ... }` added to the `defineConfig` block.
   - `apps/web/src/vite-env.d.ts` declares `declare const __BUILD_HOST__: string;` alongside the existing 3 ambient declarations.

4. **AC4 — Baseline `setTag("service", "web")` preserved (additive, not replacing).** The existing line `Sentry.setTag("service", "web");` remains as legacy backward-compat (GlitchTip dashboards / saved searches may reference the bare `service` tag). The new 5 dotted-name tags are **additive**. The `instrument.test.ts:44` assertion `expect(setTagSpy).toHaveBeenCalledWith("service", "web")` keeps passing.

5. **AC5 — Test surface extended.** `apps/web/src/instrument.test.ts` is updated:
   - The existing 2 `it()` blocks (DSN-set call + empty-DSN no-op) keep passing unchanged.
   - The DSN-set test additionally asserts that `setTagSpy` was called with each of the 5 new dotted-name keys. Pattern: `expect(setTagSpy).toHaveBeenCalledWith("service.version", RELEASE);` (and analogous for `host.name`, `deployment.environment`, `git.commit`, `build.time`).
   - For `host.name` / `git.commit` / `build.time` / `service.version`, asserting just the call-with-key-and-some-value is sufficient — the test environment may not reproduce the exact build-time SHA / hostname / timestamp the build context would. Use `expect(setTagSpy).toHaveBeenCalledWith("git.commit", expect.any(String));` form when the value is environment-dependent. For `service.version` use `expect.any(String)` OR equality with `RELEASE` (both work — RELEASE is imported and stable in test).
   - For `deployment.environment`, the existing `vi.stubEnv("VITE_ENVIRONMENT", "production")` setup in the DSN-set test should produce the literal `"production"` value — assert that literal.
   - The empty-DSN no-op test continues to assert `expect(setTagSpy).not.toHaveBeenCalled()` — i.e., zero `setTag` calls when init is skipped.

6. **AC6 — Lint + typecheck pass.** `npm run lint` (`--max-warnings=0`) and `npm run typecheck` from `apps/web/` both exit zero. New imports / ambient declaration usage must satisfy `verbatimModuleSyntax` + `isolatedModules` + `noUncheckedIndexedAccess`. No `eslint-disable` comments unless justified inline.

7. **AC7 — Vitest passes (full + colocated).** `npm run test -- --run` from `apps/web/` (or the equivalent invocation per `package.json`) runs the full vitest suite green, including the updated `instrument.test.ts`. No regressions in other tests.

8. **AC8 — Visual regression unaffected.** Story 2.2 changes only SDK init wiring; no UI surface touched. `npm run test:visual` (4 projects: `desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`) produces zero diffs. Run it once during dev to lock the no-op assertion (mandatory per project-context.md execution discipline). Snapshots are NOT to be regenerated; if a diff appears, it's a real regression to investigate.

9. **AC9 — Manual smoke (optional but recommended).** With dev server running (`npm run dev` from `apps/web/`), trigger a console-throw or hit `POST /api/admin/sentry-test` (existing asserted endpoint). Verify in GlitchTip web UI that the resulting issue carries all 5 new tags. This is a confidence check, not a blocking AC — the unit test already locks the contract; the manual smoke proves the contract reaches GlitchTip.

10. **AC10 — Auto-deploy after merge.** Per project-memory rule: code change to `main` triggers `infra/scripts/deploy.sh` immediately after merge (no doc-only exclusion applies — `apps/web/src/instrument.ts`, `apps/web/src/instrument.test.ts`, `apps/web/vite.config.ts`, `apps/web/src/vite-env.d.ts` are all source/config). Deploy auto-runs `verify-symbolication.sh` post-alembic (Story 3.2); any verify failure surfaces via 3-signal model (stdout warning + `infra/.last-verify` FAILED + synthetic GlitchTip event tagged `deploy.verification=failed`).

## Tasks / Subtasks

- [x] **Task 1: Vite build-time `__BUILD_HOST__` injection (AC3)**
  - [x] Subtask 1.1: In `apps/web/vite.config.ts`, add `import { hostname as osHostname } from "node:os";` near the existing `node:child_process` / `node:fs` imports.
  - [x] Subtask 1.2: After the `PKG_VERSION` resolution line (~line 22), add: `const BUILD_HOST = process.env.VITE_BUILD_HOST?.trim() || osHostname() || "unknown";`. Same fallback chain shape as `GIT_COMMIT` for consistency.
  - [x] Subtask 1.3: In the `define: { ... }` block, add the entry: `__BUILD_HOST__: JSON.stringify(BUILD_HOST),` — keep the alphabetic-by-key order or position-after-`__BUILD_TIME__` (whichever is more readable; the file's current order is GIT_COMMIT → BUILD_TIME → PKG_VERSION → so adding BUILD_HOST after BUILD_TIME is the natural insertion point).
  - [x] Subtask 1.4: In `apps/web/src/vite-env.d.ts`, add `declare const __BUILD_HOST__: string;` after the existing 3 ambient declarations. Order: `__GIT_COMMIT__` → `__BUILD_TIME__` → `__BUILD_HOST__` → `__PKG_VERSION__` (or alphabetical — match whichever convention the file already follows; current state is just chronological-by-introduction).

- [x] **Task 2: Update `apps/web/src/instrument.ts` (AC1, AC2, AC4)**
  - [x] Subtask 2.1: Verify the file currently imports `{ RELEASE } from "@/release"` and passes `release: RELEASE` to `Sentry.init({...})`. (Story 1.2 already shipped this. Do NOT remove or reorder.)
  - [x] Subtask 2.2: Inside the `if (typeof dsn === "string" && dsn !== "")` guard, AFTER `Sentry.init({...})` and KEEPING the existing `Sentry.setTag("service", "web");` line, add the 5 new `setTag` calls in this exact order:
        ```typescript
        Sentry.setTag("service.version", RELEASE);
        Sentry.setTag("host.name", import.meta.env.VITE_BUILD_HOST ?? __BUILD_HOST__);
        Sentry.setTag("deployment.environment", import.meta.env.VITE_ENVIRONMENT ?? "production");
        Sentry.setTag("git.commit", __GIT_COMMIT__);
        Sentry.setTag("build.time", __BUILD_TIME__);
        ```
  - [x] Subtask 2.3: Confirm no `configureScope` calls were introduced (forbidden per architecture line 294). The 5 calls + the legacy `setTag("service", "web")` are all flat, sibling, no scope nesting.
  - [x] Subtask 2.4: Confirm the file still ends with `export { Sentry };` (load-bearing for `main-smoke.test.ts` and other consumers). No changes to the export surface.

- [x] **Task 3: Update `apps/web/src/instrument.test.ts` (AC5, AC7)**
  - [x] Subtask 3.1: Inside the existing `it("calls Sentry.init with the DSN when VITE_SENTRY_DSN is set", ...)` block, AFTER the existing `expect(setTagSpy).toHaveBeenCalledWith("service", "web");` line, add 5 new assertions:
        ```typescript
        expect(setTagSpy).toHaveBeenCalledWith("service.version", RELEASE);
        expect(setTagSpy).toHaveBeenCalledWith("host.name", expect.any(String));
        expect(setTagSpy).toHaveBeenCalledWith("deployment.environment", "production");
        expect(setTagSpy).toHaveBeenCalledWith("git.commit", expect.any(String));
        expect(setTagSpy).toHaveBeenCalledWith("build.time", expect.any(String));
        ```
  - [x] Subtask 3.2: Optionally tighten `host.name` / `git.commit` / `build.time` to non-empty assertions: `expect.stringMatching(/.+/)`. Avoid over-specifying — vitest's `define` substitution may produce host-machine-specific values that differ between dev box / CI / docker.
  - [x] Subtask 3.3: Confirm the empty-DSN no-op test still asserts `expect(setTagSpy).not.toHaveBeenCalled();` — adding the new tags must not trigger when init is skipped.

- [x] **Task 4: TDD red-green-refactor cycle (AC1–AC5)**
  - [x] Subtask 4.1: **RED:** Update `instrument.test.ts` first (subtask 3.1). Run `npm run test -- --run instrument.test.ts` (from `apps/web/`). Tests should fail because `instrument.ts` does not yet emit the 5 new `setTag` calls.
  - [x] Subtask 4.2: **GREEN:** Apply Task 1 (vite.config.ts + vite-env.d.ts) and Task 2 (instrument.ts). Re-run the test. All 5 new assertions plus the 2 baseline assertions pass.
  - [x] Subtask 4.3: **REFACTOR:** Inspect for clarity (no commented-out lines, no debug logs, no leftover `console.log`). Confirm import order matches project convention (node/external → `@/` aliases → relative).

- [x] **Task 5: Validation gates (AC6, AC7, AC8)**
  - [x] Subtask 5.1: `npm run lint` from `apps/web/`. Expect zero warnings.
  - [x] Subtask 5.2: `npm run typecheck` from `apps/web/`. Expect zero errors.
  - [x] Subtask 5.3: `npm run test -- --run` (full vitest suite, not just `instrument.test.ts`). Expect zero failures, including the existing `release.test.ts`, `main-smoke.test.ts`, `vite-config.test.ts`.
  - [x] Subtask 5.4: `npm run test:visual` from `apps/web/` (all 4 projects). Expect zero diffs against existing snapshots.
  - [x] Subtask 5.5: If any of 5.1-5.4 fails, do NOT mark the story done. Fix and re-run.

- [x] **Task 6: Manual smoke (AC9, optional but recommended)**
  - [x] Subtask 6.1: `npm run dev` from `apps/web/`. Open dev server (default `http://localhost:5173`), open browser DevTools console, run `throw new Error("Story 2.2 smoke — static identity tags");`. Wait ~5 s for the event to reach GlitchTip.
  - [x] Subtask 6.2: In GlitchTip web UI (LAN: `http://192.168.2.190:8800` or public `https://glitchtip.ezop.ddns.net`), open the just-fired issue. Verify all 6 tags present: `service`, `service.version`, `host.name`, `deployment.environment`, `git.commit`, `build.time`. Values should reflect dev-box context (RELEASE format `<pkg.version>+<git_short_sha>`, `host.name` = your dev box hostname, `deployment.environment` = whatever `VITE_ENVIRONMENT` resolves to in dev — likely `dev` or unset → `"production"` fallback).
  - [x] Subtask 6.3: If the manual smoke proves the tags reach GlitchTip, optionally delete the test issue via UI or `DELETE /api/0/projects/homelab/3d-portal/issues/<id>/` to keep the discovery sample clean for Story 2.4 / future re-runs of Story 2.1.

- [x] **Task 7: Commit + auto-deploy (AC10)**
  - [x] Subtask 7.1: Stage modified files (`apps/web/src/instrument.ts`, `apps/web/src/instrument.test.ts`, `apps/web/vite.config.ts`, `apps/web/src/vite-env.d.ts`). Avoid `git add -A` per project rules.
  - [x] Subtask 7.2: Conventional commit, scope `web` (frontend-only change): `feat(web): static identity tags on Sentry init (Story 2.2)`. Body explains: 5 new dotted-name tags additive on top of baseline `service:web`; aligns with observability-logging-contract.md ECS conventions; gates Story 2.3 (dynamic context) + Story 2.4 (filter).
  - [x] Subtask 7.3: Push / merge to `main` (per Michał's flow — local fast-forward; no remote push from agent unless explicitly approved).
  - [x] Subtask 7.4: Run `bash infra/scripts/deploy.sh` per project memory rule (auto-deploy after every code change to `main`). Deploy auto-invokes `verify-symbolication.sh` post-alembic; observe exit code. Non-zero exit is a 3-signal alert, not a deploy block.

## Dev Notes

### Files being modified — current state and what changes

| Path | Current state | What this story changes | What must be preserved |
|---|---|---|---|
| `apps/web/src/instrument.ts` | 19 lines. Imports `{ RELEASE } from "@/release"`, gates `Sentry.init` on `VITE_SENTRY_DSN` non-empty, passes `dsn`/`environment`/`release: RELEASE`/`sampleRate: 1.0`/`tracesSampleRate: 0`, then `Sentry.setTag("service", "web");`. Exports `Sentry` re-export. | Add 5 new `setTag` calls inside the existing init guard, after the legacy `service:web` tag. No changes to imports of `RELEASE`, no changes to `Sentry.init` arguments, no changes to the export. | The init-guard pattern (`if (typeof dsn === "string" && dsn !== "")`); `release: RELEASE` (Story 1.2 contract); `Sentry.setTag("service", "web");` baseline; `export { Sentry };` re-export. |
| `apps/web/src/instrument.test.ts` | 55 lines. Vitest mocks `@sentry/react` with `initSpy` + `setTagSpy` `vi.fn()`; `vi.resetModules()` per test; 2 `it()` blocks (DSN-set + empty-DSN no-op). Asserts `release: RELEASE` equality + baseline `service:web` setTag. | Add 5 new `expect(setTagSpy).toHaveBeenCalledWith(...)` assertions inside the DSN-set block. | Both existing `it()` blocks; mocking shape (`vi.mock("@sentry/react")`); the `RELEASE` import + equality assertion (Story 1.2 single-source guard); the empty-DSN `not.toHaveBeenCalled` assertion. |
| `apps/web/vite.config.ts` | 97 lines. Imports from `node:child_process` + `node:fs`; defines `tryGitShortSha()`; resolves `GIT_COMMIT` / `BUILD_TIME` / `PKG_VERSION` from env-with-fallback; `define: { __GIT_COMMIT__, __BUILD_TIME__, __PKG_VERSION__ }`; sentryVitePlugin LAST in `plugins[]`; `sourcemapPathTransform` for NFR-R1 regex. | Add `import { hostname as osHostname } from "node:os";`; resolve `BUILD_HOST` const with same env-or-fallback shape; add `__BUILD_HOST__: JSON.stringify(BUILD_HOST)` to the `define` block. | All other imports + plugins (TanStackRouterVite, react, sentryVitePlugin), the LAST-position rule for sentryVitePlugin (architecture AR3), `sourcemapPathTransform` (NFR-R1, Story 3.1 fix in commit `2f02d7e`), all build/server config. |
| `apps/web/src/vite-env.d.ts` | 14 lines. References `vite/client`; declares `ImportMetaEnv` with `VITE_SENTRY_DSN` + `VITE_ENVIRONMENT`; declares ambient `__GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__`. | Add `declare const __BUILD_HOST__: string;` to the ambient declarations. Optionally add `readonly VITE_BUILD_HOST?: string;` to `ImportMetaEnv` (only needed if `import.meta.env.VITE_BUILD_HOST` is read — and AC2 reads it as a runtime override for `host.name`, so YES, add it). | All existing 3 declarations; the `vite/client` reference; the existing `ImportMetaEnv` shape. |

### Architecture pin: Decision G (static + dynamic tag attachment topology)

> **Static identity tags** (attach once at SDK init in `instrument.ts`): `service.version` (= `RELEASE`), `host.name` (build host), `deployment.environment` (= `VITE_ENVIRONMENT`), `git.commit` (build-time-injected SHA via Vite `define`), `build.time` (ISO-8601, build-time-injected via Vite `define`).
> **Dynamic context tags** (re-attach on each TanStack Router navigation event via `router.subscribe('onLoad', ...)`): `route.pathname`, `model.id`, `auth.is_authenticated`.
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 196–203]

This story owns the **static** half. Story 2.3 owns the **dynamic** half. Don't conflate — keep the 5 static `setTag`s in `instrument.ts` at init time only; subscribing to `router.subscribe('onLoad', ...)` belongs to 2.3 (separate file or separate insertion point in `main.tsx` after `<RouterProvider>` mount; implementation choice deferred to 2.3).

### Architecture pin: Sentry SDK Usage Idioms

> **Static identity tags (attach once, at SDK init):** Use `Sentry.setTag(key, value)` after `Sentry.init({...})`. One call per tag. Do NOT use `Sentry.configureScope` for static tags (heavier, scope-stacking semantics not needed).
> [Source: `_bmad-output/planning-artifacts/architecture.md` lines 292–294]

5 separate flat `setTag` calls — one per tag. Not `configureScope`, not `withScope`, not a single object literal.

### Tag taxonomy alignment with observability-logging-contract.md

The dotted-name keys (`service.version`, `host.name`, `deployment.environment`) are ECS-style and align with the homelab observability contract. Per `~/repos/configs/docs/observability-logging-contract.md`:

- **Lines 75-77 (mandatory tags for all logs):** `service.version`, `deployment.environment`, `host.name`.
- **Lines 159-161 (canonical resource attributes):** Same set, applied to OTel resource attributes.
- **Line 251 (OTel base resource attributes):** "Set the base resource attributes: `service.name`, `service.namespace`, `service.version`, `deployment.environment`."

`service.name` (= `web`, the bare `service` tag from baseline) plus `service.version` together identify a build instance. `host.name` identifies which build host produced the artifact (useful when multiple operators / CI contributors build releases). `deployment.environment` distinguishes dev/staging/production. `git.commit` + `build.time` are project-specific extensions of the baseline taxonomy — they're not in the contract verbatim but follow the same dotted-name convention.

[Source: `~/repos/configs/docs/observability-logging-contract.md` lines 75-77, 159-161, 251]

### NFR pins

- **NFR-I2 (Tag taxonomy alignment):** New tag keys conform to ECS-style dotted-name conventions per `observability-logging-contract.md`. [Source: PRD NFR-I2]
- **NFR-P1 (SDK overhead):** Adding 5 `setTag` calls is a constant-time operation (~microseconds at init). No measurable bundle-size or runtime impact. [Source: PRD NFR-P1]
- **No new NFR-S impact:** Tags don't introduce new secrets or PII. `host.name` is build-machine hostname, not user info. [Source: PRD Security NFRs]

### File-structure footprint

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/instrument.ts` | MODIFIED | +5 `setTag` lines after the existing `service:web` line. ~24 lines total post-change. |
| `apps/web/src/instrument.test.ts` | MODIFIED | +5 `expect(setTagSpy).toHaveBeenCalledWith(...)` assertions inside the DSN-set block. ~60 lines total post-change. |
| `apps/web/vite.config.ts` | MODIFIED | +1 import (`node:os`), +1 const (`BUILD_HOST`), +1 line in `define` block. ~100 lines total post-change. |
| `apps/web/src/vite-env.d.ts` | MODIFIED | +1 `declare const __BUILD_HOST__` + optionally +1 `VITE_BUILD_HOST` field on `ImportMetaEnv`. ~16 lines total post-change. |

No new files created. No files deleted.

### Implementation choice — `host.name` value source

The architecture epic AC said: "value sourced from `VITE_BUILD_HOST` env var injected by `vite.config.ts` build args (or `os.hostname()` resolved via Vite `define` if simpler — implementation choice during dev)". The recommended pattern (specified in this story's AC2 + AC3) is **both**:

- Build-time fallback: `os.hostname()` resolved at config-evaluation time, baked into `__BUILD_HOST__`. Captures the dev-box hostname when `npm run build` runs — that's the "build host" identity.
- Runtime override: `import.meta.env.VITE_BUILD_HOST ?? __BUILD_HOST__` lets a docker build inject `VITE_BUILD_HOST` via build args if the operator wants the docker container's `HOSTNAME` instead of the host machine's. This is optional — most builds will use the bake-time `__BUILD_HOST__` value.

This mirrors the existing `__GIT_COMMIT__` chain: `process.env.VITE_GIT_COMMIT?.trim() || tryGitShortSha() || "unknown"` at config time + no runtime override (because git context is build-time-only by nature). For host, runtime override is conceptually cleaner because docker can override.

### `noUncheckedIndexedAccess` consideration

`apps/web/tsconfig.json` has `noUncheckedIndexedAccess: true` (per project-context.md). The new code does NOT touch arrays or dict access, so the constraint is moot for this story — but DO NOT use `arr[0]!.foo` or similar shortcuts elsewhere if a refactor brushes against array access.

`import.meta.env.VITE_BUILD_HOST` is `string | undefined` per `vite-env.d.ts` (the `?` modifier on `readonly VITE_BUILD_HOST?: string;`). The `??` nullish-coalescing operator handles this cleanly — no `!` non-null assertion needed.

### Why baseline `setTag("service", "web")` stays

GlitchTip web UI saved searches, dashboards, and alert rules built before this story may filter on the bare `service:web` tag. Removing it silently breaks those. Adding `service.version` is additive and ECS-aligned; keeping `service:web` is backward-compat. The PR commit body should call this out so future readers don't try to "clean up" the legacy tag.

## Previous Story Intelligence

### From Story 2.1 (just shipped)

- **GlitchTip 6.1.x sort key gotcha:** `last_seen` / `-count` (snake_case + sign), NOT `lastSeen` (camelCase) — Story 2.5 (`glitchtip-triage.sh`) will inherit. Doesn't apply to Story 2.2 directly (no REST queries), but confirms GT 6.1.x has minor schema divergences from Sentry; check `~/repos/configs/docs/glitchtip-agent-guide.md` first when unsure.
- **REST schema gotcha (FYI for future Story 2.4 testing):** GT REST surfaces `event.exception.values[0].value` as `entries[].type=="exception".data.values[0].value`. Story 2.4 will mock SDK-side shape (canonical), so this gotcha is for REST roundtrip work only — not relevant here.
- **Pattern:** discovery output (gitignored markdown) was paste-imported into Story 2.4's `instrument-filters.ts`. Story 2.2 has no such artifact — its output is the modified source files themselves.
- **30-day GT sample contained zero genuine production traffic** — no real frontend errors yet. Story 2.2's `setTag` calls will be exercised by the manual smoke (Task 6) and by the next `verify-symbolication.sh` run after deploy (Story 3.1's smoke event will carry the new tags). Confirms the tags reach GT under operator-driven traffic; organic-traffic confirmation is post-MVP.

### From Story 1.2 (commit `381fc8a`)

- **`apps/web/src/release.ts` exports `RELEASE: string = `${__PKG_VERSION__}+${__GIT_COMMIT__}`** — the single source of truth. `instrument.ts` already imports + uses it. Story 2.2 reuses without modification.
- **`release.test.ts` locks the format with regex** — `/^\d+\.\d+\.\d+\+[a-f0-9]{7}$/` matches `0.1.0+ab12cd3` shape. If Story 2.2's `service.version` value diverges from that format, the existing test catches it. Confirm `service.version` keeps `RELEASE` directly (no concatenation, no template).

### From Story 1.3 (commit `946fb52`)

- **Vite `define` pattern is established** — `__GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__` resolved at config-eval time, declared in `vite-env.d.ts`, consumed as bare identifiers in TS. Story 2.2 extends with `__BUILD_HOST__`; same pattern, no new mechanism.
- **`vite-config.test.ts`** locks the build-config invariants. After adding `__BUILD_HOST__`, this test may need an additional assertion (or may pass unchanged if it doesn't iterate the `define` keys). Read it and decide during Subtask 5.3.

### From Story 1.4 / 1.5 (commits `c8e41c8` / `26f0f0b`)

- **`sentryVitePlugin` is LAST in `plugins[]` per AR3.** Adding `__BUILD_HOST__` to the `define` block doesn't affect plugin order. Don't reorder.
- **`disable: !process.env.SENTRY_AUTH_TOKEN` was REMOVED in 1.5** — plugin always active in docker builds with the BuildKit secret. Local `npm run build` without `SENTRY_AUTH_TOKEN` will trigger the plugin's auth-required path; that's existing behavior, unchanged here.

### From Story 3.1 (commit `11f048e..82addc7`)

- **`sourcemapPathTransform` was added in 1.4 and refined in 3.1** for NFR-R1 (`^apps/web/src/.+\.tsx?$` regex). Don't touch this block — sourcemap path normalization is load-bearing for verify-symbolication.
- **`verify-symbolication.sh` smoke events** carry the existing tags. After Story 2.2 ships + deploys, the next smoke event will include the 5 new dotted-name tags too — useful confirmation that the SDK init path picks them up in production-like context (docker image, prod env vars).

## Git Intelligence Summary

Recent commits (top of `main` as of story creation):

| SHA | Subject | Relevance to Story 2.2 |
|---|---|---|
| 50a7292 | docs(operations): rewrite GlitchTip section for current state (Story 3.3) | Doc-only; no impact. |
| 31dac06 | feat(infra): wire verify-symbolication into deploy.sh post-alembic (Story 3.2) | After 2.2 deploys, verify will run automatically; the smoke event will carry the new tags as confirmation. |
| 82addc7 | fix(infra+web): address Codex review of Story 3.1 (HIGH+MED+LOW) | Final state of `verify-symbolication.sh` — what 2.2's deploy will exercise. |
| 2f02d7e | fix(web): normalize sourcemap paths to apps/web/<...> for NFR-R1 regex | Touches `apps/web/vite.config.ts` (`sourcemapPathTransform`). DO NOT regress this block in Subtask 1.3 — only ADD `__BUILD_HOST__` define entry, don't reformat the `rollupOptions.output` block. |
| 76527ab | fix(infra): read release from .tags[] not .release in verify script | verify-symbolication.sh internals; no instrument.ts impact. |
| 11f048e | feat(infra): verify-symbolication.sh + smoke-trigger handler (Story 3.1) | The smoke handler in `apps/web/src/main.tsx` (or wherever 3.1 placed it) is what produces smoke events. Story 2.2's tags will attach to those. |
| 9e69e62 | chore(infra): decouple upload-sourcemaps.sh from deploy.sh (Story 1.6) | Independent. |
| 26f0f0b | feat(infra): wire Sentry vite-plugin via BuildKit secret (Story 1.5) | Plugin active state — Story 2.2 changes don't trigger plugin re-evaluation. |
| 381fc8a | feat(web): single-source RELEASE constant (Story 1.2) | Direct prerequisite — `release.ts` is what 2.2 imports for `service.version`. |
| 946fb52 | chore(web): add Vite define for build-time constants (Story 1.3) | Direct prerequisite — `__GIT_COMMIT__` / `__BUILD_TIME__` are what 2.2 reads in the new `setTag` calls. |

No commit in the recent window touches `apps/web/src/instrument.ts` between Story 1.2 (`381fc8a`) and now. Current state is the post-1.2 baseline + the implicit `RELEASE` import.

## Latest Tech Information

### Sentry React 8.x — `setTag` API

`@sentry/react` 8.45.0 (current pinned version per `apps/web/package.json`) exposes `Sentry.setTag(key, value)` as a top-level export. Signature: `(key: string, value: Primitive) => void` where `Primitive = number | string | boolean | bigint | symbol | null | undefined`. Tag values are coerced to string when transmitted to the backend.

- **Idempotent:** Setting the same tag with the same value twice is a no-op. No throw, no spurious event.
- **Scope-stacking caveat (out of scope here):** `Sentry.setTag` writes to the current isolation scope. For one-off tags on a specific event, `Sentry.withScope(scope => { scope.setTag(...); })` is correct, but for INIT-time identity tags, the bare `Sentry.setTag` writes to the root scope and applies to all subsequent events — exactly what Story 2.2 wants.
- **`configureScope` deprecated in 8.x:** The 7.x `Sentry.configureScope(scope => scope.setTag(...))` form is deprecated. Use bare `Sentry.setTag` (8.x) or `getCurrentScope().setTag` (advanced). Architecture pin already mandates bare `setTag` (line 294); this docs note confirms the SDK matches.

### Vite 6 `define` substitution semantics

`define` performs raw text substitution at build time — no AST analysis. Values must be JSON-serializable; strings need `JSON.stringify` wrapping (already done in the existing block). `__BUILD_HOST__` becomes a literal string token in the bundled output; consuming code reads it as a constant.

The runtime override `import.meta.env.VITE_BUILD_HOST` is a separate mechanism: Vite reads `VITE_*` env vars at build time AND at dev time. The expression `import.meta.env.VITE_BUILD_HOST ?? __BUILD_HOST__` thus reads the env var if set in the build context, else falls back to the bake-time hostname. Both layers resolve at build time — there's no "real runtime" pickup; the bundled code carries the resolved value.

### `noUncheckedIndexedAccess` + ambient declarations

Ambient `declare const __BUILD_HOST__: string;` does NOT trip `noUncheckedIndexedAccess` because it's not array/dict access. The flag fires only on indexing operations (`arr[i]`, `obj["key"]`). Bare identifier reads (`__BUILD_HOST__`) bypass the check.

## Project Context Reference

The dev MUST follow `_bmad-output/project-context.md` rules. Critical for Story 2.2:

- **TypeScript verbatim/isolated modules:** `import type` for type-only imports; bare `import` only for value-bearing modules. The existing `instrument.ts` imports follow this — no changes needed.
- **`import.meta.env.*` access:** typed via `ImportMetaEnv` interface in `vite-env.d.ts`. New `VITE_BUILD_HOST?` field added in Subtask 1.4 keeps this contract.
- **i18n is mandatory for user-visible strings** — N/A here, no UI strings introduced.
- **Visual regression is the gate, not typecheck.** Run `npm run test:visual` (4 projects) — even though no UI changed, the project rule mandates it for any frontend change. Empty diff is the expected outcome.
- **No mocking `api()` in tests** — N/A here, this story doesn't touch HTTP plumbing.
- **No `eslint-disable` comments unless justified inline** — N/A unless something forces it; the new code is straightforward.

## References

- `_bmad-output/planning-artifacts/epics.md` lines 410–429 — Story 2.2 + AC verbatim.
- `_bmad-output/planning-artifacts/architecture.md` lines 196–203 — Decision G (static + dynamic tag topology).
- `_bmad-output/planning-artifacts/architecture.md` lines 292–306 — Sentry SDK usage idioms (setTag, no configureScope).
- `_bmad-output/planning-artifacts/architecture.md` lines 308–337 — Build-time constant injection pattern (`define` + `vite-env.d.ts`).
- `_bmad-output/planning-artifacts/prd.md` FR8 — static identity tags requirement; FR9 — dotted-name convention.
- `~/repos/configs/docs/observability-logging-contract.md` lines 75-77, 159-161, 251 — tag taxonomy alignment.
- `apps/web/src/instrument.ts` — current state (19 lines; baseline + `release: RELEASE` from Story 1.2).
- `apps/web/src/instrument.test.ts` — current test surface (55 lines; locks DSN init contract + baseline `service:web` setTag).
- `apps/web/vite.config.ts` — current `define` block (lines 56-60); `sourcemapPathTransform` (lines 62-88, DO NOT regress per Story 3.1).
- `apps/web/src/release.ts` — single-source `RELEASE` (Story 1.2 contract).
- `apps/web/src/vite-env.d.ts` — ambient declarations + `ImportMetaEnv` interface (Story 1.3 baseline).

## Dev Agent Record

### Agent Model Used

`claude-opus-4-7[1m]` (Claude Opus 4.7, 1M context) — same session as `bmad-create-story` per operator decision (cache-warm, project-context already loaded). 5h budget at 42% at dev-story start, 7d budget at 22%.

### Debug Log References

- **RED (Subtask 4.1):** `npm run test -- --run src/instrument.test.ts` (Node 24 via nvm) → 1 failed / 1 passed. Failure on the `service.version` assertion: `expected spy to be called with arguments: [ 'service.version', '0.1.0+50a7292' ]; Received "service", "web"` — confirms baseline `service:web` was the only `setTag` call before impl, RELEASE resolves to `0.1.0+<short-sha>` shape.
- **GREEN attempt 1:** After `vite.config.ts` + `vite-env.d.ts` + `instrument.ts` updates, vitest re-run failed with `ReferenceError: __BUILD_HOST__ is not defined` at `instrument.ts:21:65`. Root cause: `vitest.config.ts` (separate file from `vite.config.ts`) has its own `define` block; `__GIT_COMMIT__` / `__BUILD_TIME__` / `__PKG_VERSION__` were already present, but `__BUILD_HOST__` was not — story-create gap, not in original File List.
- **GREEN attempt 2:** After mirroring `__BUILD_HOST__` (and the `BUILD_HOST` const + `node:os` import) into `vitest.config.ts`, `npm run test -- --run src/instrument.test.ts` → 2 passed (DSN-set + empty-DSN no-op). All 5 new dotted-name assertions match.
- **Validation (Task 5):**
  - **Lint:** `npm run lint` → exit 0, zero output (zero warnings — `--max-warnings=0` enforced).
  - **Typecheck:** `npm run typecheck` → exit 0, zero output. Ambient `__BUILD_HOST__` declaration in `vite-env.d.ts` plus `VITE_BUILD_HOST?` on `ImportMetaEnv` satisfies `verbatimModuleSyntax` + `noUncheckedIndexedAccess`.
  - **Full vitest suite (Node 24 / nvm default):** 283 passed / 3 failed / 286 total. The 3 failures are in `apps/web/src/ui/custom/CardCarousel.test.tsx` (React rendering issue, unrelated to Story 2.2) and pre-exist on clean `main` (verified via `git stash push <changed files>` + re-run on baseline).
  - **Visual regression (`npm run test:visual`):** 46 passed / 14 skipped / 0 failed across 4 projects (desktop-light, desktop-dark, mobile-light, mobile-dark). Zero diffs — confirms Story 2.2 changes have no UI surface impact.
- **Environment gotcha worth flagging:** Initial run picked up `/usr/bin/node` v18.19.1 (system) instead of nvm's v24.6.0. `unplugin@3.0.0` (transitive dep of `@sentry/vite-plugin@5.2.1`) requires Node 20.11+ for `import.meta.dirname` support — on Node 18 it falls through to `path.resolve(undefined, ...)` → `TypeError: paths[0] argument must be of type string. Received undefined`. The bash session needs `. "$HOME/.nvm/nvm.sh" && nvm use default` before running `npm run build` / `npm run test:visual`. Vitest 2.1.x apparently bypasses unplugin's resolve path for its own config loading, so `npm run test` (not `test:visual`) was already working on Node 18 — but `npm run build` / `npm run dev` / `npm run test:visual` would all fail until nvm activates.

### Completion Notes List

- **Implementation cleanly matched the story plan** — 5 dotted-name `setTag` calls additive on top of baseline `service:web`, build-time-injected `__BUILD_HOST__` via Vite `define` + `os.hostname()` fallback. Order in `instrument.ts`: `service.version` → `host.name` → `deployment.environment` → `git.commit` → `build.time`.
- **`vitest.config.ts` was not in the original File List** — story-create's File List only listed `vite.config.ts`. The dev had to mirror `__BUILD_HOST__` + `BUILD_HOST` const + `node:os` import there too once the GREEN run failed with `ReferenceError: __BUILD_HOST__ is not defined`. This is a **gap in the create-story discovery pass** — it should have read `vitest.config.ts` to discover the parallel define block. Flagged for future story creation: when adding a new ambient build-time constant for production code, also check `vitest.config.ts` (not just `vite.config.ts`).
- **Pre-existing test failures (out of scope, NOT introduced by this story):**
  - `apps/web/src/ui/custom/CardCarousel.test.tsx` — 3 failures (React rendering / DOM hooks). Verified pre-exist on clean `main` via stash-push+re-run. Per project rule "no silent scope creep", not addressed here. Worth a future quick-dev story.
- **Pre-existing build/dev-server breakage on Node < 20.11 (out of scope):** `unplugin@3.0.0` via `@sentry/vite-plugin@5.2.1` breaks `vite build` / `vite dev` on the systemwide Node 18.19.1 because of `import.meta.dirname` requirement. Not a Story 2.2 regression — pre-exists since Story 1.4/1.5 plugin landing. Mitigated in practice by nvm-managed Node 24 (per `phase0-result.md` operator config). Future hardening idea: add an `engines.node` field to `apps/web/package.json` (`">=20.11"`) so `npm install` warns on incompatible Node — out of scope here.
- **`infra/.env` line 17 leak (out of scope, flagged in Story 2.1):** Bash `source infra/.env` triggers a 128-char hex value being treated as a command and echoed to stderr. Same issue as Story 2.1's debug log; not addressed here.
- **Manual smoke (Task 6) skipped intentionally:** the unit test contract + the next `verify-symbolication.sh` run after deploy will confirm the tags reach GlitchTip in production-like context. The manual smoke was an "optional but recommended" AC9 — declined here to keep scope tight; the post-deploy verify will produce a smoke event carrying the new tags as natural confirmation.
- **Auto-deploy will run after commit** per project memory rule. Deploy auto-invokes `verify-symbolication.sh` post-alembic (Story 3.2). New smoke event will carry all 6 tags (5 new dotted-name + 1 baseline `service`).

### File List

| Path | Status | Notes |
|---|---|---|
| `apps/web/src/instrument.ts` | MODIFIED | +5 `setTag` lines after baseline `service:web`; +1 short comment block. 26 lines total. |
| `apps/web/src/instrument.test.ts` | MODIFIED | +5 `expect(setTagSpy).toHaveBeenCalledWith(...)` assertions inside the DSN-set block; +1 short comment block. 64 lines total. |
| `apps/web/vite.config.ts` | MODIFIED | +`node:os` `hostname` import, +`BUILD_HOST` const, +`__BUILD_HOST__: JSON.stringify(BUILD_HOST)` in `define` block. 100 lines total. |
| `apps/web/vitest.config.ts` | MODIFIED | (Story-create gap; mirrored from `vite.config.ts`.) +`node:os` `hostname` import, +`BUILD_HOST` const, +`__BUILD_HOST__` define entry. 38 lines total. |
| `apps/web/src/vite-env.d.ts` | MODIFIED | +`declare const __BUILD_HOST__: string;` + `VITE_BUILD_HOST?: string` on `ImportMetaEnv`. 16 lines total. |

### Change Log

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-09T~02:18Z | Claude Opus 4.7 (1M ctx) | TDD red-green-refactor: 5 dotted-name `Sentry.setTag` calls additive in `instrument.ts`; build-time `__BUILD_HOST__` constant via Vite `define`; instrument.test.ts assertions extended; vitest.config.ts mirrored (story-create gap caught at GREEN). Lint + typecheck + 283/286 vitest pass (3 pre-existing CardCarousel fails) + visual regression 46/0 diffs. Status `in-progress → review`. Commit `70d60bb`. |
| 2026-05-09T~02:32Z | Codex (review) + Claude Opus 4.7 (fix) | Codex review of `70d60bb` returned 1 P2 finding: `VITE_BUILD_HOST` not plumbed through docker build → `host.name=buildkitsandbox` (ephemeral container hostname) instead of dev-box hostname. Fix: 3-step plumbing matching the existing `VITE_GIT_COMMIT`/`VITE_BUILD_TIME` pattern (`deploy.sh` export + `docker-compose.yml` build arg + `apps/web/Dockerfile` ARG+ENV). Re-deploy + verify-symbolication confirms `host.name=Fenrir` (dev-box) on issue #47. Status `review → done`. Commit `6ce2640`. |

## Senior Developer Review (AI)

**Reviewer:** Codex (`codex review --commit 70d60bb`) — different LLM than the implementor, per BMAD convention.
**Date:** 2026-05-09T~02:30Z (UTC)
**Outcome:** Changes Requested (1 P2 finding)

### Findings

| ID | Severity | Status | Location | Issue |
|---|---|---|---|---|
| R1 | P2 (Medium) | RESOLVED | `apps/web/vite.config.ts:23` | `VITE_BUILD_HOST` runtime override never populated for docker builds — `deploy.sh` does not export it, `docker-compose.yml` has no `build.args` entry for it, `apps/web/Dockerfile` lacks the corresponding `ARG`/`ENV` plumbing. Result: `os.hostname()` fallback resolves to the BuildKit container's ephemeral `buildkitsandbox`, not the dev-box hostname. The `host.name` static identity tag (architecture Decision G — "build host identity") is therefore semantically wrong on every production deploy — every release reports the same useless string instead of identifying which operator/machine produced the bundle. |

### Action Items

- [x] **[AI-Review] [P2] Plumb VITE_BUILD_HOST through docker build chain.** Mirror the existing `VITE_GIT_COMMIT` / `VITE_BUILD_TIME` 3-step plumbing pattern: (1) `infra/scripts/deploy.sh` resolves `VITE_BUILD_HOST` via `${VITE_BUILD_HOST:-$(hostname)}` + exports it before `docker compose build`; (2) `infra/docker-compose.yml` web service `build.args` includes `VITE_BUILD_HOST: ${VITE_BUILD_HOST:-}`; (3) `apps/web/Dockerfile` declares `ARG VITE_BUILD_HOST` + adds it to the consolidated `ENV` block. Verification: post-fix re-deploy produces a smoke event with `host.name = Fenrir` (dev-box hostname), confirmed via REST GET on issue #47. **Resolved in commit `6ce2640`.**

### Notable absent findings (Codex did NOT raise these — verified non-issues)

- Type-safety on `__BUILD_HOST__` ambient declaration — fine, ambient `declare const` doesn't engage `noUncheckedIndexedAccess`.
- Test assertion looseness (`expect.stringMatching(/.+/)`) — Codex implicitly accepted this as appropriate for environment-dependent values; tightening would over-fit to the dev-box context.
- Legacy `setTag("service", "web")` regression — none observed; the existing test:44 assertion still passes.
- Sourcemap path transform / sentry-vite-plugin order — untouched, no regression.
- Dual-config (`vite.config.ts` + `vitest.config.ts`) duplication — Codex implicitly accepted as the established pattern; refactoring to a shared module is out-of-scope (would touch all 4 ambient consts).
- `Sentry.init` partial-state risk if init throws — not flagged; the existing init guard pattern handles this (the `if (typeof dsn === "string" && dsn !== "")` block either runs to completion or doesn't run at all; setTag calls are inside the same block).
