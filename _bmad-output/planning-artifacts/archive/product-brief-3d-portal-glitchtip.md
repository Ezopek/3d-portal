---
title: "Product Brief: Useful GlitchTip — production frontend symbolication and ergonomics for 3d-portal"
status: "complete"
created: "2026-05-09"
updated: "2026-05-09"
inputs:
  - docs/operations.md
  - docs/plans/2026-04-30-glitchtip-integration-design.md
  - docs/plans/2026-04-30-glitchtip-integration-plan.md
  - "~/repos/configs/docs/glitchtip-agent-guide.md"
  - _bmad-output/project-context.md
  - apps/web/vite.config.ts
  - apps/web/src/instrument.ts
  - infra/scripts/upload-sourcemaps.sh
---

# Product Brief: Useful GlitchTip for 3d-portal

## Executive Summary

3d-portal already ships errors to GlitchTip from the React frontend, the FastAPI backend, and the arq render worker. The plumbing works — events arrive, releases tag, environments separate. What does **not** work in practice is *using* it: when a frontend exception fires in production, the GlitchTip event surfaces a stack frame at `app-DhGq2.js:13` instead of `apps/web/src/modules/catalog/.../X.tsx:42`. The result is the predictable failure mode of a homelab observability tool — installed, never opened. The infrastructure cost is sunk (Postgres, RAM, container lifecycle on `.190`) whether we use it or not.

This brief reframes GlitchTip's role from "event store" to **structured input for the BMAD planning pipeline and AI-agent debugging loop**. In 3d-portal, BMAD owns the workflow and AI agents are half the user base — production errors should land in `bmad-quick-dev` / `bmad-create-story` as ready-to-implement bug stubs, not in a UI someone has to remember to open. To deliver that, we replace the standalone `glitchtip-cli` upload with `@sentry/vite-plugin` integrated into the production build (debug-ID symbolication, drift-proof release tagging), tighten the SDK config so the issue list is signal not noise, and add two scripts: `verify-symbolication.sh` (smoke check after every deploy) and `glitchtip-triage.sh` (issue-id → markdown story stub). Backend and worker polish are out of scope here, gated on frontend rollout demonstrating measurable triage value.

## The Problem

Source maps are uploaded today by `infra/scripts/upload-sourcemaps.sh` (glitchtip-cli, SHA-pinned 0.1.0). The script works, but the workflow has three latent failures that conspire to turn GlitchTip into shelfware:

- **Symbolication is name-based, not debug-ID-based.** GlitchTip 6.1.6 supports the modern artifact-bundle / debug-ID flow (added in 4.2, Nov 2024), but the existing CLI path leans on legacy `--url-prefix '~/assets'` matching that `operations.md` itself admits "only works most of the time".
- **Release tagging can drift.** The browser SDK reports `release: VITE_PORTAL_VERSION` at runtime; the CLI script uploads under `--release $PORTAL_VERSION` from outside the build. Nothing enforces that they match — a deploy where one of those env vars resolves differently silently strands events with unmapped frames, and the only signal is "the next time someone opens the issue".
- **No verification ritual.** There is no cheap, repeatable way to confirm post-deploy that a real frontend error resolves to a real source line. The first signal that symbolication is dead is "I clicked an issue and the stack is gibberish" — which is exactly when you stop bothering.

On top of symbolication, the SDK currently captures everything: browser-extension errors, `ResizeObserver loop` warnings, transient offline network failures, and normal `access_expired` refresh-flow 401s. Unfiltered, the issue list becomes noise the first time someone opens it — and that one bad first impression is the whole adoption problem.

## The Solution

**Wire `@sentry/vite-plugin` (5.2.x) into `apps/web/vite.config.ts`.** The plugin runs during `vite build`, injects debug IDs into the bundle, uploads the (hidden) source maps to GlitchTip's chunk-upload endpoint at `http://192.168.2.190:8800`, and finalizes the release in one step. Both the plugin's `release.name` and the runtime SDK's `release` import a single `RELEASE` constant from `apps/web/src/release.ts` — drift becomes a TypeScript error, not a runtime mystery. **Failure policy:** if the upload step fails (transient GlitchTip outage, expired auth token, GlitchTip backend issue #299 `artifactbundle/assemble` 404), the `vite build` fails hard, the deploy aborts, and `bash infra/scripts/upload-sourcemaps.sh` is the documented one-command recovery path that ships the maps via the legacy CLI flow.

**Polish the SDK init in `apps/web/src/instrument.ts`** with deny rules for browser-extension URLs, ignore rules for known noise (`ResizeObserver loop limit exceeded`, non-Error promise rejections), and a `beforeSend` filter that drops events when the user is offline or when an `ApiError` represents a normal `access_expired` refresh round-trip. Attach useful tags — current route pathname, `model_id` when on `/catalog/$id`, auth status, plus build-derived `git.commit` SHA, `deploy.host`, and `build.time` — so triaging an event takes 30 seconds and "which deploy broke this?" is one glance, not archaeology.

**Add a verification step to the deploy ritual.** A new `infra/scripts/verify-symbolication.sh` triggers a deterministic frontend error via a `?__sentry_smoke=<uuid>` query param that throws with a unique tag `smoke.run_id=<uuid>` per run, polls GlitchTip's REST `/issues/?statsPeriod=5m` endpoint for up to 30 seconds, matches by fingerprint, and asserts the returned event's top stack frame `filename` is a real `.tsx`, not a minified bundle. Manual run for now, documented in `operations.md`, automatable later. The execution-discipline section of `_bmad-output/project-context.md` picks up two new rules: "after `deploy.sh`, run `verify-symbolication.sh` until CI takes over" and "every replacement keeps its predecessor as documented manual recovery for one release cycle".

## What Makes This The Right Call

- **One source of release truth.** Plugin reads the same version expression the runtime SDK does. SDK and uploads stay in lockstep by construction.
- **Modern flow, settled tooling.** GlitchTip 4.2+ accepts debug-ID artifact bundles; `@sentry/vite-plugin` 5.2.x is stable, suppresses telemetry for self-hosted targets, and speaks the protocol GlitchTip's own CLI uses. No bleeding edge.
- **Determinism preserved.** Plugin uploads happen inside the docker image build, so `deploy.sh`'s "extract dist from image" rule (project-context.md) still holds — no bundle-hash drift. The Dockerfile spec is the single most load-bearing implementation contract: which stage runs the upload, where the BuildKit secret enters and exits, and why the runtime image stays clean. Lock it down at design time.
- **CLI fallback is one command away.** Issue #299 is real and open. If it fires, `bash infra/scripts/upload-sourcemaps.sh` recovers without writing recovery code under pressure. This becomes a repeatable principle: every replacement keeps its predecessor as documented manual recovery for one release cycle.
- **Closes the planning loop.** `glitchtip-triage.sh` converts a GlitchTip issue into a markdown stub ready for `bmad-quick-dev` or `bmad-create-story`. Production error → triage script → BMAD story → fix is a single chain instead of three context switches.
- **Pull-only as a deliberate stance, not a deferral.** Solo dev + AI agents poll on cadence and pull on suspicion. Push notifications would be noise. Skipping alerting in v1 is the design, not the omission — the alerting follow-up brief ships only if pull is measurably failing.

## Who This Serves

**Primary surface: AI agents reading GlitchTip via REST + the BMAD planning pipeline they feed.**

- The dominant debugging persona is an AI agent (Claude Code, Codex, Gemini) executing `glitchtip-agent-guide.md` recipes — `curl /api/0/projects/homelab/3d-portal/issues/?statsPeriod=24h`, then `/issues/<id>/events/latest/`. Resolved stack frames + structured tags (`route.pathname`, `model.id`, `auth.is_authenticated`, `git.commit`, `deploy.host`, `build.time`) are what makes that loop work. UI ergonomics are secondary — clickability of an issue is not the success criterion; **agent-readable triage is**.
- `glitchtip-triage.sh <issue_id>` is the bridge from this surface into BMAD: top frame, fingerprint, route context, release SHA, suggested files-to-edit — formatted as a markdown stub ready to feed `bmad-quick-dev` or `bmad-create-story`. Production error becomes structured planning input automatically.

**Secondary surface: Michał, when an agent escalates or when triaging in person.**

- Solo developer, single-tenant household catalog, no per-user error context needed.
- "Aha moment": running `verify-symbolication.sh` after a deploy and watching the smoke event come back symbolicated to `apps/web/src/...:42` in under 30 seconds. Or: pasting `./infra/scripts/glitchtip-triage.sh 142` into a BMAD session and getting a usable bug story stub back. From either of those, GlitchTip becomes a tool the loop relies on, not a dashboard nobody opens.

## Success Criteria

The brief succeeds when, simultaneously:

1. **Real symbolication.** Any uncaught frontend exception in the production build produces a GlitchTip event whose top stack frame resolves to `apps/web/src/<...>.tsx:<line>` — confirmed by `verify-symbolication.sh` after every deploy until CI takes over.
2. **Quiet by default.** The first 25 issues sorted by `lastSeen desc`, measured 7 days post-rollout, contain zero matches against the deny list (browser extensions, `ResizeObserver` loops, transient offline-network errors, `access_expired` refresh-flow noise). If they do, the filter ruleset is wrong, not the ceiling.
3. **One source of release truth.** Build-time and runtime `release` values are derived from the same expression. The build log shows the upload step exiting non-zero on auth-token failure, not warning-and-continuing.
4. **Pull-only ergonomics that work.** Existing `glitchtip-agent-guide.md` REST recipes return resolved stack frames from a fresh deploy without manual sourcemap fiddling. `glitchtip-triage.sh <issue_id>` returns a markdown story stub usable as direct input to `bmad-quick-dev` or `bmad-create-story`. No alerting required for v1.
5. **Retired but recoverable.** `infra/scripts/upload-sourcemaps.sh` is unreferenced from `deploy.sh` but lives in the repo with a header comment marking it as the manual-recovery path for issue #299 fallout.
6. **Instrumented ritual, not honor system.** `infra/.last-verify` timestamp is updated by every successful `verify-symbolication.sh` run; `deploy.sh` warns at next invocation if the previous deploy did not record a verify. Failed verifies emit a synthetic GlitchTip event tagged `deploy.verification=failed` — the alarm channel exists without adding new infrastructure.

## Scope

**Phase 0 — pre-flight gate (before any code lands):**

- Run a one-shot local `vite build` against `.190` GlitchTip with `@sentry/vite-plugin` 5.2.x enabled. Fire a smoke error in the resulting `dist/`, confirm via REST that the event symbolicates to a real `.tsx` frame.
- **If GlitchTip backend issue #299 (`artifactbundle/assemble` 404) fires** despite GlitchTip 6.1.6 being current: abort this brief. Switch to a much smaller scope: tighten the existing CLI flow + add the SDK polish + add the verification + triage scripts, and skip the plugin migration entirely.
- **If the smoke comes back green:** proceed to the rest of the scope below.

**Discovery — sample real noise (before writing the filter ruleset):**

- Pull 30 days of existing issues from the homelab GlitchTip:
  `curl -H "Authorization: Bearer $TOKEN" 'http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/issues/?statsPeriod=30d&limit=100'`.
- Sort by `count` desc; the top 10–20 noise patterns are the empirical basis for `denyUrls` / `ignoreErrors` / `beforeSend`. The anticipated list (`ResizeObserver`, browser-extension URLs, offline) is the floor — actual noise on `.190` may be different and dominates the rollout impression.

**In scope — code + config:**

- `apps/web/vite.config.ts` — `@sentry/vite-plugin` 5.2.x config, placed after all other plugins; debug IDs + chunk upload to `:8800`; `filesToDeleteAfterUpload` to keep `.map` files off the served bundle.
- `apps/web/src/instrument.ts` — `denyUrls`, `ignoreErrors` (derived from Discovery), `beforeSend` filter, scope-tag wiring (TanStack Router-aware: tag bound on each navigation, not once at init).
- `apps/web/src/release.ts` — single exported `RELEASE` constant imported by both `vite.config.ts` (plugin) and `instrument.ts` (SDK init) so build-time and runtime release values cannot drift.
- `apps/web/Dockerfile` + `infra/docker-compose.yml` — surface `SENTRY_ORG=homelab`, `SENTRY_PROJECT=3d-portal`, `SENTRY_URL=http://192.168.2.190:8800` as build args. `SENTRY_AUTH_TOKEN` is mounted as a BuildKit secret (`--mount=type=secret,id=sentry_token`), NOT a plain `ARG` — `ARG` would persist in `docker history` layers. The runtime image stays token-free; verify with `docker history` in the verification ritual.

**In scope — scripts + integration:**

- `infra/scripts/verify-symbolication.sh` — new smoke script. Triggers a deterministic frontend error via `?__sentry_smoke=<uuid>` query param, polls `/issues/?statsPeriod=5m` for up to 30s, matches by `smoke.run_id=<uuid>` tag, asserts top frame `filename` is a real `.tsx`. On success: writes timestamp to `infra/.last-verify`. On failure: emits a synthetic GlitchTip event tagged `deploy.verification=failed` so the same tool the brief is making useful is also the alarm channel for its own breakage.
- `infra/scripts/glitchtip-triage.sh <issue_id>` — new triage helper. Pulls `/issues/<id>/events/latest/` from GlitchTip, extracts top frame (filename:line), fingerprint, route, model_id, release SHA, last 5 events; formats as markdown story stub paste-ready for `bmad-quick-dev` / `bmad-create-story`.
- `infra/scripts/deploy.sh` — at end of run, calls `verify-symbolication.sh` as **non-fatal warning** (deploy doesn't block on it, but stdout is loud). Before the build step, warns if `infra/.last-verify` timestamp is older than the previous deploy timestamp (instrumented manual ritual — decay becomes visible).
- `infra/scripts/upload-sourcemaps.sh` — header comment marking it as the manual-recovery path for issue #299, decoupled from `deploy.sh`, still runnable on demand.

**In scope — docs:**

- `docs/operations.md` — replace the existing "out of scope follow-up" note with the new deploy ritual; document the manual-recovery path; document how to use `glitchtip-triage.sh`.
- `_bmad-output/project-context.md` — add to AI agent execution discipline:
  1. "After `deploy.sh`, run `verify-symbolication.sh` until CI takes over."
  2. "When a production GlitchTip issue needs a fix, run `glitchtip-triage.sh <issue_id>` first to get the structured story stub."
  3. "Every replacement keeps its predecessor as documented manual recovery for one release cycle."

**Out of scope (explicit):**

- Backend Sentry init polish (`apps/api/app/core/sentry.py`, worker `instrument`) — staged as a follow-up brief, conditional on the frontend round demonstrating real triage value.
- Alerting / notifications (webhook to Slack-like, email). Pull-only suffices for solo-dev MTTR; revisit only if measurable cases prove otherwise.
- CI-side automation of `verify-symbolication.sh`. Manual run is acceptable until 3d-portal has a CI runner; tracked as future work, not blocking.
- Backend sourcemap upload — Python tracebacks are already source-line-resolved.
- Removing `glitchtip-cli` from the repo — kept as fallback, not deleted.

## Vision (12-24 months)

GlitchTip becomes the default first-stop for "production frontend feels weird" — a tool the team (Michał + AI agents) actually opens. Three concrete extensions, each its own brief:

- **Backend ergonomics round.** Structured tags from FastAPI handlers (operation, auth role, `audit.event_id`), `beforeSend` filter for known-benign Pydantic 422s, optional artifact-bundle pattern for backend if it adds triage value. Concrete gate: ≥3 production issues opened from a GlitchTip event (referencing `<issue_id>`) within 30 days post-rollout.
- **Alerting.** GlitchTip → webhook on first occurrence of a new issue in the last 24h. Only added if the pull-only flow proves insufficient in measurable cases.
- **CI-grade verification.** `verify-symbolication.sh` running automatically post-deploy via a BMAD `tea` CI pipeline; gate the deploy on its exit code.

The end-state is GlitchTip as a load-bearing piece of the operational loop — not a bullet point on the architecture diagram.
