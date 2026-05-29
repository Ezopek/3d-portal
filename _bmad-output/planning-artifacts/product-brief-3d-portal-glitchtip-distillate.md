---
title: "Product Brief Distillate: 3d-portal — Useful GlitchTip"
type: llm-distillate
source: "product-brief-3d-portal-glitchtip.md"
created: "2026-05-09"
purpose: "Token-efficient context for downstream PRD creation"
---

# Distillate — Useful GlitchTip for 3d-portal

Reference detail captured during discovery, elicitation, and review that did not fit the executive brief but is load-bearing for PRD-level decisions.

---

## Frozen technical facts

- **GlitchTip instance:** version 6.1.6 (well past 4.2 inflection point that introduced artifact-bundle / debug-ID flow). Org slug `homelab`, project slug `3d-portal`, project ID `4`. Single shared DSN across web/api/worker; service distinguished by `setTag('service', '...')` (`web`, `api`, `render`).
- **Endpoint split (mandatory):**
  - SDK event ingestion: `https://glitchtip.ezop.ddns.net` (works from anywhere).
  - Source-map / artifact-bundle upload: `http://192.168.2.190:8800` (LAN HTTP). The public HTTPS proxy has a 1MB body-size limit that breaks multi-MB chunk uploads.
  - REST API for triage (issues, events): either endpoint; HTTPS is fine for sub-MB GETs.
- **Auth token:** GlitchTip personal token, 64-char lowercase hex. Created via UI Profile → Auth Tokens (no `/auth/login` password-grant API exists). Required scopes for plugin: `project:write`, `project:releases`, `org:read`. Same scopes as the existing `GLITCHTIP_AUTH_TOKEN` used by `infra/scripts/upload-sourcemaps.sh`.
- **Plugin:** `@sentry/vite-plugin` 5.2.x (Node 18+, uses Rolldown for its own build, suppresses telemetry when `url` ≠ sentry.io). Speaks the same Sentry chunk-upload + debug-ID protocol GlitchTip's own CLI uses.
- **Existing CLI:** `glitchtip-cli` v0.1.0, SHA256 `aa98c98de1a95e1840afbb14f0b11889feb2fbf9d71b278e19e034a30b4623b7`, fetched from gitlab.com/glitchtip/glitchtip-cli. Flow: `glitchtip-cli sourcemaps inject ./dist` → `glitchtip-cli sourcemaps upload ./dist --release $PORTAL_VERSION --url-prefix '~/assets'`.
- **SDK state at start of brief (already wired):** `@sentry/react ^8.45.0` in `apps/web/src/instrument.ts`. Init reads `VITE_SENTRY_DSN`, `VITE_PORTAL_VERSION`, `VITE_ENVIRONMENT` from build args. Currently sets `release: VITE_PORTAL_VERSION`, `setTag('service','web')`, `sampleRate: 1`, `tracesSampleRate: 0`. Already emits `debug_meta.images[].debug_id` at runtime (browser SDK 8.x default).
- **Existing sourcemap config:** `apps/web/vite.config.ts` has `build.sourcemap = 'hidden'` — bundle has no `sourceMappingURL` comment, browsers do not fetch maps. Keep as-is; plugin assumes hidden.
- **Release tag:** currently `0.1.0` from `PORTAL_VERSION` env var; used identically in SDK runtime, CLI upload, and Docker image tag.

## Constraints — non-negotiable

- **Bundle-hash determinism:** `infra/scripts/deploy.sh` extracts `dist/` from the just-built docker image (NOT from a local build). Reason: local node/pnpm versions diverge from image; hash drift breaks symbolication. Plugin uploads must therefore happen INSIDE the docker build context, not from a separate local step. (Source: project-context.md infra rule.)
- **`SENTRY_AUTH_TOKEN` must NOT enter image layers.** Plain `ARG` persists in `docker history`. Use BuildKit `--mount=type=secret,id=sentry_token` with `DOCKER_BUILDKIT=1`. Verify with `docker history apps_web:<tag>` after build.
- **`:8800` LAN-only requirement** means the build must run on a host with LAN/VPN access to `.190`. Currently dev box only. Future portability concern: any CI runner needs LAN reach or a tunnel.
- **`/api/share/*` is the public bypass** in 3d-portal — never add auth there. Not directly load-bearing for this brief but worth knowing if Sentry breadcrumbs touch HTTP.
- **English in committed content** (code, docs, commit messages); Polish stays conversational.
- **Auto-deploy after every code/infra commit to `main`** — adding the plugin will trigger this loop. Doc-only commits skip deploy.

## Rejected approaches (do not re-propose)

- **Legacy REST `POST /api/0/organizations/{org}/releases/{version}/files/` upload.** Returns 405 on GlitchTip 6.1.x. Documented in `operations.md` and inside `upload-sourcemaps.sh` comments. Replaced by chunk-upload protocol.
- **Public HTTPS upload at `https://glitchtip.ezop.ddns.net`.** 1MB nginx body limit blocks multi-MB sourcemap chunks. Forces LAN HTTP `:8800`.
- **Local pnpm/npm build before docker build, then upload local `dist/`.** Violates bundle-hash determinism rule (project-context.md). Local node/pnpm version ≠ image's; hashes diverge.
- **URL-prefix `~/assets` matching only (legacy by-name resolution).** Operations.md admits "only works most of the time" for live-browser errors that carry SDK `debug_meta`. Debug-ID is the bulletproof path.
- **`ikenfin/vite-plugin-sentry`** (community plugin). Older mental model, release-only flow, no first-class debug-ID injection, slower to track sentry-cli changes. Use the official `@sentry/vite-plugin` instead.
- **No upload at all + GlitchTip name-based JS resolution** (let GlitchTip fetch maps by URL at event-processing time). Either exposes maps publicly or requires GlitchTip to reach an internal URL; no debug-ID guarantee; stale CDN means unmapped frames forever.
- **Removing `glitchtip-cli` and `infra/scripts/upload-sourcemaps.sh` from the repo.** Kept as fallback against issue #299. Repeatable principle: every replacement keeps its predecessor as documented manual recovery for one release cycle.
- **Plugin in `vite serve` / dev mode.** Plugin only runs on `vite build`. Trying to wire it into dev is wasted effort.
- **Backend FE-style sourcemap upload.** Python tracebacks are already source-line-resolved. No symbolication need; out of scope here.

## Anti-patterns named (avoid in implementation)

- **Release-name mismatch** (#1 churn cause). SDK runtime `release` and plugin upload `release.name` must come from the same expression. Mitigation: `apps/web/src/release.ts` exports `RELEASE`, imported by both.
- **Upload-after-deploy timing trap.** If maps upload AFTER the new bundle is served, the first user error of that release stays unmapped forever (Sentry/GlitchTip do not retro-symbolicate). Plugin runs during `vite build` → uploads happen before image is even pushed → safe by construction.
- **Plugin placed before other Vite plugins.** Tree-shaking strips Sentry instrumentation and/or maps generate before injection. **Plugin must be LAST in `plugins[]`.**
- **Auth-token-warn-and-continue.** Common deploy script anti-pattern: upload step warns on 401/403 and continues. Brief mandates hard fail with documented CLI fallback.
- **Public sourcemaps via `sourcemap: true`.** Leaks source. Use `'hidden'` + `filesToDeleteAfterUpload: ['./dist/**/*.map']`.
- **Re-injecting debug IDs after CLI already injected them.** Risk if vite-plugin runs alongside `upload-sourcemaps.sh`. Decision in this brief: plugin replaces CLI; CLI script is decoupled from `deploy.sh` to prevent dual-injection.
- **GlitchTip backend issue #299** (`artifactbundle/assemble` 404, status: open as of 2026-Q2). Plugin upload returns 200 but symbolication still fails with "release not found". Brief gates Phase 0 on smoke-testing this against the homelab GlitchTip 6.1.6.
- **GlitchTip issue #96** (`sentry-cli releases finalize` partially-implemented). Release timeline / commit-association on GlitchTip is mostly cosmetic. Don't depend on commit-tracking UI features.

## Existing infrastructure state

- `infra/scripts/upload-sourcemaps.sh` — current source-map upload pipeline, glitchtip-cli-based. Works. Decoupled from `deploy.sh` after this brief lands; kept on disk as documented manual-recovery path.
- `infra/scripts/deploy.sh` — builds locally → ships images via SSH → restarts compose stack on `.190` → runs `alembic upgrade head`. Pulls canonical `infra/.env` from `.190` if missing. Reads `PORTAL_HOST` (`ezop@192.168.2.190`), `PORTAL_SSH_PORT` (`30022`), `PORTAL_VERSION` (`0.1.0`).
- `apps/web/Dockerfile` — multi-stage `node:22-alpine` → `nginx:1.27-alpine`. Build args from compose: `VITE_SENTRY_DSN`, `VITE_PORTAL_VERSION`, `VITE_ENVIRONMENT`. Plugin requires additional build-time inputs: `SENTRY_AUTH_TOKEN` (BuildKit secret), `SENTRY_ORG=homelab`, `SENTRY_PROJECT=3d-portal`, `SENTRY_URL=http://192.168.2.190:8800`.
- `apps/api/app/modules/admin/router.py` — has `POST /api/admin/sentry-test` (deliberately raises). Backend smoke endpoint; do NOT "fix". Frontend equivalent is the `?__sentry_smoke=<uuid>` query param introduced by this brief.
- `docs/operations.md` — flagged source-map symbolication explicitly as out-of-scope follow-up (line 144). Brief replaces that note with the new ritual.
- Existing planning docs (gitignored): `docs/plans/2026-04-30-glitchtip-integration-design.md`, `docs/plans/2026-04-30-glitchtip-integration-plan.md` — original 5-phase rollout that landed Sentry SDK + CLI upload pipeline. Baseline this brief builds on.

## Open questions for PRD

- **`GLITCHTIP_AUTH_TOKEN` provenance.** Does an auth token already exist in `infra/.env` on the dev box? Or do we mint a fresh one with the required scopes? PRD must specify.
- **Token-at-rest storage on dev box.** `infra/.env` (current pattern for other secrets)? Separate `infra/.env.sentry-build`? `1Password` / system keychain? Brief does not pin this.
- **Token rotation policy.** Cyclic (e.g., quarterly) or on-incident-only? Who owns the rotation calendar? Currently undefined.
- **BuildKit secret mechanism specifics.** Pass via file (`echo $TOKEN > /tmp/sentry_token; --secret id=sentry_token,src=/tmp/sentry_token`) or via env (`--secret id=sentry_token,env=SENTRY_AUTH_TOKEN`)? PRD picks one.
- **Final `denyUrls` / `ignoreErrors` ruleset.** Depends on Phase-0 Discovery output. Brief commits to deriving from observed 30-day noise; PRD records actual list once Discovery runs.
- **Tag cardinality budget.** `route.pathname` + `model.id` + `git.commit` + `build.time` are unbounded-ish. GlitchTip event payload size and indexing cost not measured. Light concern but PRD should note a guardrail.
- **`glitchtip-triage.sh` output format.** Markdown stub structure not finalized — what fields, what order, how it renders inside a BMAD `bmad-quick-dev` invocation. PRD nails the contract; the script becomes one of its first stories.
- **Dependency on `jq`.** Triage script will likely shell-pipe `curl ... | jq ...`. Confirm `jq` is installed on dev box (it usually is); pin if not.

## User scenarios (richer than exec brief)

- **Scenario — model-specific catalog crash.** User opens `/catalog/m_42`; component throws because of malformed `external_links` array. GlitchTip event arrives with: top frame `apps/web/src/modules/catalog/components/ExternalLinksPanel.tsx:73`, tags `route.pathname=/catalog/$id`, `model.id=m_42`, `auth.is_authenticated=true`, `git.commit=ab12cd3`, `build.time=2026-05-09T14:22:00Z`, `release=0.1.0`. AI agent runs `./infra/scripts/glitchtip-triage.sh 142` → markdown stub → paste into `bmad-quick-dev` → Amelia (dev agent) writes failing test in `ExternalLinksPanel.test.tsx`, fixes the parsing, ships.
- **Scenario — refresh-token race.** User triggers a mutation while access cookie just expired; `apiFetch` retries via refresh, but the underlying mutation receives a non-`access_expired` 401 from elsewhere. Without `beforeSend` filter: noise. With brief's filter (drop on `ApiError.detail === 'access_expired'`): only the real 401 lands. Tags include `auth.is_authenticated=true` and `route.pathname` so the false-positive auth state mismatch surfaces.
- **Scenario — post-deploy symbolication regression.** Deploy completes; `verify-symbolication.sh` fires smoke event with `smoke.run_id=<uuid>`; polls 30s; matches by tag; finds top frame is still `app-XYZ.js:13`. Script writes `infra/.last-verify` with FAILED marker AND emits a synthetic GlitchTip event tagged `deploy.verification=failed`. Next deploy: `deploy.sh` reads `.last-verify`, sees the failure, prints loud warning + reminds operator to investigate before next ship.
- **Scenario — issue #299 fires post-rollout.** Plugin upload returns 200, but events arriving after that show "release not found" / unsymbolicated stacks. `verify-symbolication.sh` catches it. Operator runs `bash infra/scripts/upload-sourcemaps.sh` (CLI fallback) for the current release; opens new BMAD story to either pin plugin to a working version or document permanent CLI use.

## Cross-repo touchpoints

- `~/repos/configs/docs/glitchtip-agent-guide.md` — authoritative for: GlitchTip auth flow, REST endpoints (`/api/0/projects/homelab/3d-portal/issues/?statsPeriod=24h`, `/issues/<id>/events/latest/`), token creation UX, project conventions. Brief consumes this; `glitchtip-triage.sh` should align with the guide's documented endpoints rather than invent new ones.
- `~/repos/configs/docs/observability-logging-contract.md` — canonical log/trace tag fields. New tags introduced by this brief (`git.commit`, `deploy.host`, `build.time`) should align with this contract's naming. If the contract uses dotted names already (e.g. `deployment.commit`), match it; otherwise this brief sets the precedent and feeds back into the contract.
- `~/repos/configs/nginx/3d-portal.conf` — nginx-180 edge proxy config (lives in configs repo, NOT in 3d-portal). Brief does not touch it. Worth knowing because port `:8800` access bypasses the edge entirely; no nginx config change required.
- `~/repos/orca-profiles/AGENTS.md` — git workflow Michał uses across repos (trunk-only main, ff merges, conventional commits with scope). Brief commits will follow `feat(observability):`, `chore(infra):` etc.

## Scope signals

- **In MVP (this brief):**
  - Phase 0 dry-run gate (issue #299 smoke).
  - Discovery (sample 30-day noise).
  - `vite.config.ts` plugin wiring.
  - `instrument.ts` filter + tag overhaul.
  - `release.ts` single-source.
  - Dockerfile BuildKit secret + build args.
  - `verify-symbolication.sh` (smoke + tripwire + failed-verify GlitchTip event).
  - `glitchtip-triage.sh` (issue → BMAD stub).
  - `deploy.sh` integration (calls verify as non-fatal warning, checks last-verify timestamp).
  - `upload-sourcemaps.sh` decoupling + header comment.
  - `operations.md` rewrite of the symbolication section.
  - `project-context.md` adds 3 execution-discipline rules.

- **Out of MVP:**
  - Backend Sentry init polish (gated on ≥3 issues triaged via GlitchTip in 30d).
  - Alerting (gated on pull-only model proving insufficient).
  - CI auto-verify (gated on 3d-portal having a CI runner).
  - Backend sourcemap upload.
  - Removing CLI fallback.
  - Notification webhook (Slack-like, email).

- **Maybe / future briefs:**
  - Generalizing `verify-symbolication.sh` into a multi-check post-deploy smoke harness reusable across services.
  - Promoting the env-var contract (`SENTRY_*`) into `~/repos/configs/docs/observability-logging-contract.md` so the next homelab project starts at this brief's end-state.
  - Token rotation runbook + dependabot-style monitoring of `@sentry/vite-plugin` and `glitchtip-cli` for drift.
