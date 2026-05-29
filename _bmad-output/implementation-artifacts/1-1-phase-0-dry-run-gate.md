# Story 1.1: Phase 0 Dry-Run Gate

Status: done (with caveat — see Completion Notes below; outcome documented in phase0-result.md is a THIRD category not anticipated by ACs; operator decision A/B/C required before Stories 1.4 and 1.5 can be scheduled)

> **Note:** This story is **NOT a permanent code change**. It is a one-shot experiment in a throwaway git worktree to verify whether GlitchTip backend issue [#299](https://github.com/glitchtip/glitchtip-backend/issues/299) fires on the homelab instance BEFORE committing the `@sentry/vite-plugin` migration. Outcome decides whether Stories 1.4 and 1.5 ship at all (happy-path) or are closed as won't-ship (fallback-path). The temporary worktree is discarded after recording the result.

## Story

As **Michał** (or an AI agent acting on his behalf running this dry-run autonomously),
I want a one-shot local `vite build` against the homelab GlitchTip instance with `@sentry/vite-plugin` 5.2.x enabled,
so that we know empirically whether issue #299 fires on this specific instance before committing the plugin migration to the repo.

## Acceptance Criteria

1. **AC1 — Worktree isolation.** A temporary git worktree is created from `main` (e.g., `git worktree add ../3d-portal-phase0 main`). All experimental file modifications happen there. The main repo working tree stays clean throughout. The worktree is removed after recording the outcome.

2. **AC2 — Plugin install + minimal vite.config.ts modification.** Inside the worktree: `npm install --save-dev @sentry/vite-plugin@~5.2.0` (in `apps/web/`); a stub `apps/web/src/release.ts` is created exporting `RELEASE = "0.1.0+phase0"`; `apps/web/vite.config.ts` is modified to import `RELEASE` from `./src/release` and to add `sentryVitePlugin({ url: process.env.SENTRY_URL, org: 'homelab', project: '3d-portal', authToken: process.env.SENTRY_AUTH_TOKEN, release: { name: RELEASE }, sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] }, telemetry: false })` as the **LAST** entry in `plugins[]`. `build.sourcemap` stays `"hidden"`.

3. **AC3 — Plugin upload returns 200 + assemble returns 200 (happy-path indicator).** From the worktree, with `SENTRY_URL=http://192.168.2.190:8800`, `SENTRY_AUTH_TOKEN=$(grep '^GLITCHTIP_AUTH_TOKEN=' infra/.env | cut -d= -f2-)` exported, and LAN/VPN reach to `192.168.2.190:8800` confirmed, run `cd apps/web && npm run build`. The build runs to completion within 60 s wall-clock for the upload phase. The plugin's stdout shows the chunk-upload step returning 200 from `:8800` AND the artifact-bundle `assemble` call returning 200 (NOT 404). If `assemble` returns 404, this is the issue #299 signal — fallback-path.

4. **AC4 — Files endpoint lists uploaded artifacts.** After a happy-path build, `curl -fsS -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+phase0/files/"` returns a non-empty JSON array listing the uploaded files (each entry has `id`, `name`, `headers`, etc.). Empty array OR 404 = fallback-path.

5. **AC5 — Outcome artifact written.** A new file `_bmad-output/implementation-artifacts/phase0-result.md` records the outcome with this structure (one of the two checkboxes ticked, exit reason filled in):
   ```markdown
   # Phase 0 Dry-Run Gate Result

   - **Date:** YYYY-MM-DDTHH:MM:SSZ (ISO-8601, UTC)
   - **Operator:** <Michał | autonomous AI agent / model name>
   - **Plugin version tested:** @sentry/vite-plugin@~5.2.0 (installed: <resolved version>)
   - **GlitchTip endpoint:** http://192.168.2.190:8800
   - **Release tag used:** 0.1.0+phase0
   - **Outcome:**
     - [ ] **happy-path** — chunk upload 200, assemble 200, files endpoint listed N artifacts. Stories 1.4 and 1.5 PROCEED.
     - [ ] **fallback-path** — `<reason>` (e.g., assemble 404 = issue #299, 401 = auth, 5xx = GlitchTip unreachable). Stories 1.4 and 1.5 CLOSE as won't-ship; CLI flow remains active path.
   - **Build log excerpt:**
     ```
     <last ~30 lines of vite build output covering the plugin steps>
     ```
   - **Decision:**
     - <one sentence rationale linking the observed signals to the chosen path>
   ```

6. **AC6 — Worktree teardown.** After AC5 is written, the temporary worktree is removed: `git worktree remove ../3d-portal-phase0 --force`. The main repo working tree is verified clean (`git status` returns clean tree on `main`). No commits land on `main` from this story.

7. **AC7 — Sprint-status synchronization (manual or via bmad-dev-story epilogue).** After AC5 is written:
   - `1-1-phase-0-dry-run-gate` status in `_bmad-output/implementation-artifacts/sprint-status.yaml` moves from `ready-for-dev` → `done`.
   - **If happy-path:** `1-4-vite-config-sentry-plugin-integration` and `1-5-dockerfile-buildkit-secret-mount` remain at `backlog` in sprint-status (will be picked up by subsequent `bmad-create-story` invocations).
   - **If fallback-path:** `1-4-...` and `1-5-...` get a `done` status with a sprint-status comment line above each entry: `# closed: phase 0 fallback-path; see phase0-result.md`. `epics.md` Epic 1's "Phase 0 branching" note may be updated to reflect the chosen path (optional polish; not blocking).

8. **AC8 — `_bmad-output/` is gitignored — outcome stays local.** `phase0-result.md` lands in `_bmad-output/implementation-artifacts/` which is gitignored (per memory note `feedback_local_only_docs`). The result is mirrored into the eventual Phase 0 PR description when one is opened (manual step at PR-open time, not part of this story's automation).

## Tasks / Subtasks

- [ ] **Task 1: Pre-flight checks (AC1, AC3 prerequisites)**
  - [ ] Subtask 1.1: Confirm `git status` on `main` is clean (no uncommitted work to lose).
  - [ ] Subtask 1.2: Confirm `infra/.env` exists and contains `GLITCHTIP_AUTH_TOKEN=<non-empty>`. Do NOT echo the token to logs or stdout.
  - [ ] Subtask 1.3: Confirm LAN/VPN reach to `:8800`: `curl -fsS -o /dev/null -w '%{http_code}\n' --max-time 5 http://192.168.2.190:8800/api/0/` should return a non-network-error HTTP code (200 or any 4xx is acceptable; the goal is "TCP+HTTP works"). If `curl` exits non-zero with a connection-refused or timeout error → **STOP and surface the gap**; the dry-run cannot proceed off-LAN.
  - [ ] Subtask 1.4: Confirm Node 22 / npm match the existing `apps/web/Dockerfile` baseline (`node --version` should report v22.x; `cd apps/web && npm --version` should match the lockfile expectation). Mismatched Node version is OK for dry-run; document in phase0-result.md if so.

- [ ] **Task 2: Create temporary worktree (AC1)**
  - [ ] Subtask 2.1: `git worktree add ../3d-portal-phase0 main` (or a sibling path that does not collide with the host filesystem). Operate from the new worktree path for all subsequent steps.
  - [ ] Subtask 2.2: `cd ../3d-portal-phase0` and verify `git status` clean, on a detached HEAD or temporary branch.

- [ ] **Task 3: Install plugin + create release.ts stub (AC2)**
  - [ ] Subtask 3.1: From the worktree's `apps/web/`, run `npm install --save-dev @sentry/vite-plugin@~5.2.0`. Lockfile change is local to the worktree only — never lands on `main` from this story.
  - [ ] Subtask 3.2: Create `apps/web/src/release.ts` with content:
    ```typescript
    export const RELEASE = "0.1.0+phase0";
    ```
  - [ ] Subtask 3.3: Modify `apps/web/vite.config.ts` to:
    - Add at top: `import { sentryVitePlugin } from "@sentry/vite-plugin";`
    - Add at top: `import { RELEASE } from "./src/release";`
    - Add as the **LAST** entry in `plugins[]`:
      ```typescript
      sentryVitePlugin({
        url: process.env.SENTRY_URL,
        org: "homelab",
        project: "3d-portal",
        authToken: process.env.SENTRY_AUTH_TOKEN,
        release: { name: RELEASE },
        sourcemaps: { filesToDeleteAfterUpload: ["./dist/**/*.map"] },
        telemetry: false,
      })
      ```
    - Keep `build.sourcemap: "hidden"` unchanged.

- [ ] **Task 4: Run build with the right env (AC3)**
  - [ ] Subtask 4.1: Export the env vars in the same shell that runs `npm run build`:
    ```bash
    set -a
    source <REPO_ROOT>/infra/.env
    set +a
    export SENTRY_URL=http://192.168.2.190:8800
    export SENTRY_AUTH_TOKEN="$GLITCHTIP_AUTH_TOKEN"
    ```
    The `set -a` / `set +a` pattern auto-exports keys read from `.env`.
  - [ ] Subtask 4.2: From the worktree's `apps/web/`, run `npm run build 2>&1 | tee /tmp/phase0-build.log`. Capture the FULL log — both happy-path and fallback-path require it as evidence in AC5.
  - [ ] Subtask 4.3: Inspect the log:
    - Happy-path signals: lines like `Successfully uploaded source maps`, `assemble` step returning 200 / "ready", debug-IDs injected, `dist/` ends with no `.map` files.
    - Fallback-path signals: `assemble` returning 404 (issue #299), 401/403 (auth), 5xx (GlitchTip side broken), or any non-zero `vite build` exit.
    - Document the actual signals seen.

- [ ] **Task 5: Verify uploaded files via REST (AC4 — happy-path branch only)**
  - [ ] Subtask 5.1: If Task 4 produced a happy-path build, run:
    ```bash
    curl -fsS \
      -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
      "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+phase0/files/" \
      | jq '. | length'
    ```
    Expected: a positive integer (count of uploaded files).
  - [ ] Subtask 5.2: If Task 4 produced a fallback-path outcome, skip Subtask 5.1 — the release likely does not exist (404 on the files endpoint is consistent with #299 / auth / network failure modes).

- [ ] **Task 6: Write phase0-result.md (AC5)**
  - [ ] Subtask 6.1: From the **main repo** (not the worktree), create `_bmad-output/implementation-artifacts/phase0-result.md` per AC5 template. Tick the matching outcome box. Paste the last ~30 lines of `/tmp/phase0-build.log` into the build-log excerpt block.
  - [ ] Subtask 6.2: In the Decision sentence, name the observed signals and the chosen path explicitly (e.g., "Assemble returned 200 + files endpoint listed 7 artifacts → happy-path; Stories 1.4 and 1.5 proceed.").

- [ ] **Task 7: Discard worktree (AC6)**
  - [ ] Subtask 7.1: Return to the main repo: `cd <REPO_ROOT>`.
  - [ ] Subtask 7.2: `git worktree remove ../3d-portal-phase0 --force` (the `--force` is acceptable here because the worktree is intentionally throwaway; lockfile changes were never meant to land).
  - [ ] Subtask 7.3: Verify `git status` returns a clean tree on `main`. No staged changes, no untracked files (other than the new `phase0-result.md` in the gitignored `_bmad-output/`).

- [ ] **Task 8: Sync sprint-status (AC7)**
  - [ ] Subtask 8.1: Update `_bmad-output/implementation-artifacts/sprint-status.yaml`:
    - `1-1-phase-0-dry-run-gate: ready-for-dev` → `done`.
    - **If fallback-path:** also set `1-4-vite-config-sentry-plugin-integration: done` and `1-5-dockerfile-buildkit-secret-mount: done` with a comment line above each: `# closed: phase 0 fallback-path; see phase0-result.md`.
    - Update `last_updated` field to today's date.
  - [ ] Subtask 8.2: **If fallback-path:** edit `epics.md` Epic 1's "Phase 0 branching" note to record the actual outcome with a date stamp (one-line addition; not a full rewrite).

## Dev Notes

### Story type — exception to standard TDD/visual-regression discipline

This story is **a one-shot experiment**, not a feature implementation. The standard `_bmad-output/project-context.md` rules around **TDD red→green→refactor** and **mandatory `npm run test:visual`** do **not apply** here because:

- No production code lands on `main`.
- No UI changes (visual regression baseline is unaffected — `dist/` from the worktree never reaches the deployed bundle).
- The "test" is the dry-run itself; success = AC3 + AC4 happy-path signals OR a clean fallback-path determination.

These rules **resume in full force from Story 1.2 onwards** (where `release.ts` lands on `main` permanently).

### Worktree isolation rationale

`git worktree` is the cleanest mechanism for "I want to apply temporary file changes that I will throw away" without polluting the active workspace. Alternatives considered and rejected:

- **Stash + reset:** harder to script reliably; lockfile churn from `npm install` is annoying to unwind in a single stash; risk of forgetting and committing a partial state.
- **Branch + reset --hard:** destructive on the active branch; slow; risks the user's other in-flight work.
- **Docker container:** full repo copy + npm install inside the container is heavyweight for a single dry-run; also obscures the actual `vite build` flow we want to test.

Worktree is the standard `~/.claude/CLAUDE.md` discipline ("Worktree isolation for feature work that will take multiple commits or risks polluting the active workspace") applied even here, because the cost of a 30-second `git worktree add` is far smaller than the cost of accidentally leaving plugin install changes on `main`.

### Token handling

`GLITCHTIP_AUTH_TOKEN` is in `infra/.env` (mode 600 on dev box, gitignored). It is exported into the build-shell's environment as `SENTRY_AUTH_TOKEN` for the plugin. **Never echo it.** Never paste it into `phase0-result.md` build-log excerpts (sed-redact if it appears in `vite build` output before pasting). The token's presence is verified by checking the env var is non-empty (`[[ -n "$SENTRY_AUTH_TOKEN" ]]`), not by printing its value.

### Required token scopes (per `architecture.md` Decision B)

For Phase 0, the token needs `org:read`, `project:read`, `project:write`, `project:releases`, and `event:write`. If `assemble` returns 403 instead of 404, that is an **auth/scope** signal, not a #299 signal — the token lacks `project:write` or `project:releases`. Document this distinction in `phase0-result.md`'s Decision sentence so the operator knows to re-mint with the correct scopes rather than declaring fallback-path.

### Reading the build log (signal → meaning)

| Log line / outcome | Meaning | Path |
|---|---|---|
| `[sentry-cli] INFO Successfully uploaded source maps` (and similar 200-from-`:8800` lines) followed by `[sentry-cli] INFO Released ...` | Happy-path | proceed with 1.4 + 1.5 |
| `assemble` step returning HTTP 404 (or "release not found" semantics) | issue #299 fired | fallback-path |
| HTTP 401 / 403 from `:8800` | auth/scope problem (NOT #299) | fix token, re-run; do NOT prematurely call fallback-path |
| HTTP 5xx / connection refused / timeout | GlitchTip-side broken or `:8800` unreachable | retry later; if persistent → fallback-path with `<reason: unreachable>` |
| `Cannot find module '@sentry/vite-plugin'` or similar | install step failed (npm registry / network) | fix install env; retry |
| `vite build` succeeds but no upload step ran | plugin not registered (likely placement bug or `apply` filter) | re-check plugin position in `plugins[]` |

### `npm install` in the worktree

The worktree shares the parent repo's git history but has its OWN working tree, including a separate `node_modules/`. So `npm install --save-dev @sentry/vite-plugin@~5.2.0` from the worktree's `apps/web/` will create a local `node_modules/` and update the worktree's `package.json` + `package-lock.json` — none of this lands on `main` because we never `git add` / `git commit` from the worktree. After `git worktree remove --force`, the entire `node_modules/` is removed alongside.

If npm complains about an existing `node_modules/` symlink or a peer-dep conflict, run `rm -rf apps/web/node_modules apps/web/package-lock.json` inside the worktree first, then `npm install` to bootstrap fresh from `apps/web/package.json` (without phase 0 plugin yet), then re-run with the plugin install. This is throwaway work — speed over elegance.

### Project Structure Notes

This story does not introduce any permanent files into the canonical project structure (per `architecture.md` Step 6 "Project Structure & Boundaries"). The only new file in the main repo working tree is `_bmad-output/implementation-artifacts/phase0-result.md`, which lives entirely in the gitignored BMAD output directory and never enters the canonical tree.

The worktree's `apps/web/src/release.ts` and modified `apps/web/vite.config.ts` are **DRAFTS** — they are NOT the final form. Story 1.2 will introduce a permanent `release.ts` with the proper expression `${package.version}+${git_short_sha}` (per `architecture.md` Decision G + AR1). Story 1.4 will introduce the permanent `vite.config.ts` plugin integration (gated on this story's outcome). Do not copy the dry-run code into Story 1.2 or Story 1.4 verbatim — re-derive against the production-grade ACs in `epics.md`.

### References

- `_bmad-output/planning-artifacts/epics.md#story-1-1-phase-0-dry-run-gate` — story authoritative ACs (this file is a context-rich spec; the epic file is the single source of truth for the AC contract).
- `_bmad-output/planning-artifacts/architecture.md` Decisions A, B, E, J, AR10 — token transport, scope minimization, plugin choice, in-build execution, Phase 0 gate rationale.
- `_bmad-output/planning-artifacts/prd.md` FR4 (hard-fail policy), NFR-S1 (token at-rest scope), Risk Mitigation table row "Technical: GlitchTip backend issue #299 fires" (Phase 0 mitigation rationale).
- `~/repos/configs/docs/glitchtip-agent-guide.md` — REST recipes, including releases/files endpoint shape (consulted by Subtask 5.1).
- `_bmad-output/project-context.md` — TDD discipline (note: explicitly does NOT apply to this experimental story; resumes in 1.2+).
- Sentry vite-plugin docs (latest, via context7 `/getsentry/sentry-docs`): plugin LAST in `plugins[]`, `authToken` from env, `sourcemaps.filesToDeleteAfterUpload` glob pattern, `build.sourcemap: 'hidden'`. Self-hosted `url` parameter is the GlitchTip-equivalent endpoint base (here `http://192.168.2.190:8800`).
- GlitchTip backend issue #299 — the specific failure mode this gate detects: `artifactbundle/assemble` returning 404 against an otherwise-healthy chunk-upload flow on certain GlitchTip 6.1.x deployments.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Opus 4.7, 1M context) — running this story autonomously while operator is asleep.

### Debug Log References

- `/tmp/phase0-build.log` — captured during `vite build` from the throwaway worktree (HTTP 413 stack at lines ~30–45).
- Inline curl outputs against `http://192.168.2.190:8800/api/0/...` are reproduced verbatim in `phase0-result.md` (chunk-upload server config + releases list + files endpoint).

### Completion Notes List

- **Pre-flight:** All passed except Node version. `nvm use default` (Node 24.6.0) bridged the gap; `import.meta.dirname` from unplugin (transitive of `@sentry/vite-plugin`) requires Node 20.11+, system Node was 18.19.1. Documented as a non-blocking variance (Dockerfile uses Node 22 in production; both 22 and 24 satisfy unplugin's runtime requirement).
- **Worktree:** `git worktree add --detach ../3d-portal-phase0 HEAD` (initial `main` checkout failed because `main` was already checked out in the active worktree — used `--detach` instead).
- **TS error fix:** `tsconfig.node.json` did not include `src/release.ts`; added `"src/release.ts"` to its `include` array within the worktree only. Production version of this fix is part of Story 1.2 (proper release.ts integration).
- **Plugin install:** `npm install --save-dev @sentry/vite-plugin@~5.2.0` resolved 5.2.1; 853 packages added on first install with Node 18, 975 on Node 24 reinstall. Both runs succeeded.
- **Build:** `vite build` itself completed in 6.84 s (`✓ built in 6.84s`), then upload step failed with HTTP 413.
- **Outcome category:** THIRD — neither happy-path nor fallback-path (issue #299). The 413 happens upstream of `assemble`; #299 cannot be evaluated against this homelab instance until the chunk-upload phase completes. Documented exhaustively in `phase0-result.md`.
- **Direct sentry-cli sanity check:** Same artifacts uploaded successfully via `sentry-cli --url http://192.168.2.190:8800 sourcemaps upload` (HTTP 200). Confirms the LAN endpoint accepts large bodies; the 413 is specific to the plugin's chunk-upload protocol, where GlitchTip's server response forces traffic to the public HTTPS URL (which has a 1 MB nginx body cap).
- **Worktree teardown:** `git worktree remove ../3d-portal-phase0 --force` succeeded; main repo on `main`, working tree clean, only worktree listed is the active one.
- **Sprint-status:** `1-1-phase-0-dry-run-gate` → `done`. Epic 1 status remains `in-progress`. `1-4-vite-config-sentry-plugin-integration` and `1-5-dockerfile-buildkit-secret-mount` LEFT at `backlog` with inline comments — they are GATED on operator decision A/B/C documented in `phase0-result.md`. `epics.md` Phase 0 branching note NOT updated yet — same gating reason.
- **Decision required of operator (in the morning):** Pick A (fix GlitchTip server config to return LAN URL), B (raise nginx body limit on public proxy), or C (accept fallback-path: close 1.4 + 1.5, keep CLI flow active). Recommendation in `phase0-result.md`: A first, C if A is too costly this cycle.

### File List

**Created (permanent, in `_bmad-output/` — gitignored, never reaches `main` history):**
- `_bmad-output/implementation-artifacts/1-1-phase-0-dry-run-gate.md` (this file)
- `_bmad-output/implementation-artifacts/phase0-result.md`

**Modified (permanent, in `_bmad-output/` — gitignored):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `1-1` → `done`; comments added to `1-4` and `1-5` referencing the operator gate.
- `_bmad-output/planning-artifacts/epics.md` — UNCHANGED for now (Phase 0 branching note will be updated after operator decision).

**Created/modified in worktree (THROWAWAY — discarded by `git worktree remove --force`):**
- `apps/web/src/release.ts` (stub `RELEASE = "0.1.0+phase0"`)
- `apps/web/vite.config.ts` (plugin LAST in `plugins[]` with full Decision E/J config)
- `apps/web/tsconfig.node.json` (added `src/release.ts` to `include`)
- `apps/web/package.json` + `apps/web/package-lock.json` (devDep `@sentry/vite-plugin@~5.2.0` resolved 5.2.1)
- `apps/web/node_modules/` (regenerated for Node 24)
- `apps/web/dist/` (build artifacts)

**Side artifacts on the GlitchTip server (`.190`) — non-destructive, can be cleaned by operator if desired:**
- Release `0.1.0+phase0` (created by plugin attempt; no files associated due to upload failure).
- Artifact bundle from direct sentry-cli test (debug-ID-keyed; no per-release listing).
