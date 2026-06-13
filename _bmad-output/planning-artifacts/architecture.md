---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter (N/A — brownfield delta; starter-level decisions frozen at baseline)
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
status: complete
completedAt: '2026-05-09'
lastStep: 8
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip-distillate.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
  - _bmad-output/project-context.md
  - docs/operations.md
  - docs/plans/2026-04-30-glitchtip-integration-design.md
  - docs/plans/2026-04-30-glitchtip-integration-plan.md
  - "~/repos/configs/docs/glitchtip-agent-guide.md"
  - "~/repos/configs/docs/observability-logging-contract.md"
documentCounts:
  prd: 1
  brief: 2
  ux: 0
  research: 0
  projectDocs: 4
  projectContext: 1
workflowType: 'architecture'
project_name: '3d-portal'
user_name: 'Ezop'
date: '2026-05-09'
projectMode: 'brownfield'
classification:
  projectType: web_app
  domain: general
  complexity: low
  projectContext: brownfield
initiatives:
  - id: 0
    name: 'Product Foundation — Home 3D-Printing Catalog'
    status: 'shipped_retrospective'
    completed: '2026-04 (v1 cutover)'
    documented: '2026-05-15'
    sections: 'see "Initiative 0" H2 below — minimal pointer section; the full v1 architectural baseline lives in docs/architecture.md and docs/design/2026-04-29-portal-design.md'
  - id: 1
    name: 'Useful GlitchTip Delta'
    status: 'shipped'
    completed: '2026-05-10'
    sections: 'see "Initiative 1" H2 below'
  - id: 2
    name: 'Agent Runbook + Legacy SoT Triage'
    status: 'shipped'
    started: '2026-05-10'
    completed: '2026-05-11'
    sections: 'see "Initiative 2" H2 below'
  - id: 3
    name: 'UI Theme Compliance & Visual Regression Hardening'
    status: 'shipped'
    started: '2026-05-13'
    completed: '2026-05-13'
    sections: 'see "Initiative 3" H2 below'
  - id: 5
    name: 'Public Registration & User Account Management'
    status: 'planning'
    started: '2026-05-18'
    sections: 'see "Initiative 5" H2 below — Decisions A–K in-scope, L–N deferred'
  - id: 19
    name: 'Spoolman Read-Only Inventory (MVP-A)'
    status: 'planning'
    started: '2026-05-29'
    sections: 'see "Initiative 19" H2 below — Decisions AD (cache topology + poll cadence + leader-election + observability), AE (network transport — internal docker network with configs-side coordination + P4a fallback), AF (data-model carry-through for future cost-calc UX)'
  - id: 21
    name: 'Admin-Managed Orca Process Profiles + User-Facing Selector Options'
    status: 'planning'
    started: '2026-06-04'
    sections: 'see "Initiative 21" H2 below — Decisions AK (admin-managed profile inventory read over the resolver + compatibility-map representation/enforcement, offerable = imported ∧ resolvable ∧ compatible), AL (import write posture — in-place vendored-tree write + on-disk sidecar manifest + audit, no DB)'
  - id: 22
    name: 'Admin Operational Observability (Worker/Job Console)'
    status: 'planning'
    started: '2026-06-06'
    sections: 'see "Initiative 22" H2 below — Decisions AO (admin queue-console read model: raw-arq live snapshot over app.state arq/Redis + business-keyed status-key context reuse + console lives in admin area not the member /queue slot + durable ledger deferred), AP (worker-liveness tri-state from the coarse <queue>:health-check key, coarse ~1h liveness accepted for MVP, interval-lowering deferred), AQ (leak fence / read-only privacy contract — field-allowlist DTO, never raw pickled args/kwargs/result, curated error_class/context, admin-only GET-only)'
---

# Architecture Decision Document — 3d-portal

**Maintainer:** Ezop
**Created:** 2026-05-09 (Initiative 1)
**Last updated:** 2026-06-06 (Initiative 22 Admin Operational Observability — Worker/Job Console for ARQ queues — planning extension via sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md, status `proposed` 2026-06-06 — Decisions AO + AP + AQ appended after Initiative 21 H2. Read-only admin MVP; implementation BLOCKED until bmad-create-story + dev-go. Prior: 2026-06-04 Initiative 21 Decisions AK + AL.)

This is the living project architecture document for **3d-portal**. It grows over time, one **Initiative** at a time, mirroring the `prd.md` initiatives index. Each initiative documents its own context analysis, starter evaluation, core decisions, patterns, structure, and validation. New initiatives extend this file — do **not** fork (`architecture-v2.md`, `architecture-glitchtip.md`).

Source-of-truth for capability contracts: `prd.md`. Source-of-truth for technical bounds of the v1 portal foundation: `product-brief-3d-portal.md` + `docs/project-overview.md`. Source-of-truth for Initiative 1 (GlitchTip) technical bounds: `product-brief-3d-portal-glitchtip-distillate.md`.

## Initiatives Index

| # | Name | Status | Shipped | Notes |
|---|---|---|---|---|
| 0 | Product Foundation — Home 3D-Printing Catalog | ✅ shipped (retro) | 2026-04 v1 | Pointer-only section. The v1 architectural baseline (component topology, data plane, integration points, deployment) lives authoritatively in `docs/architecture.md` + `docs/design/2026-04-29-portal-design.md`. This file's E1+ decisions are deltas layered ON TOP of that baseline. See section "Initiative 0" below for the pointer mapping. |
| 1 | Useful GlitchTip Delta | ✅ shipped | 2026-05-10 | 12 architectural decisions (A–L) covering symbolication, filter chain, verify ritual, triage script. See section "Initiative 1" below. |
| 2 | Agent Runbook + Legacy SoT Triage | ✅ shipped | 2026-05-11 | 8 architectural decisions (A–H) covering runbook delivery, layered auto-discovery (runbook + OpenAPI), self-serving endpoint, source-detection strategy, decision-doc-first pattern for legacy folder triage. See section "Initiative 2" below. |
| 3 | UI Theme Compliance & Visual Regression Hardening | ✅ shipped | 2026-05-13 | 10 architectural decisions (A–J in-scope) + 3 deferred (K–M, re-eval 2026-06-13) covering token taxonomy additions, token-file split for Stylelint compatibility, layered lint enforcement (in-repo first-line + optional plugin), git-hook-enforced baseline acceptance gate, axe contrast scan integration, Codex review prompt enrichment. See section "Initiative 3" below. |
| 5 | Public Registration & User Account Management | ✅ shipped | 2026-05-20 | 11 architectural decisions (A–K in-scope) + 3 deferred (L–N). Five epics E6–E10 shipped. Closing commit `7e5aea0`. See section "Initiative 5" below. |
| 6 | Post-Cutover Default-Deny Auth Posture | ✅ shipped | 2026-05-21 | 3 architectural decisions (M, N, O). Default-deny `/api/*` mechanism (pytest enumeration + `_PUBLIC_ROUTES` allowlist), share-scoped asset endpoint (Codex peer-grilled), frontend shell-level AuthGate. Single epic E11 (7 stories 11.1-11.7). Closing commit `2641b6c`. See section "Initiative 6" below. |
| 7 | Account & Admin UX Polish | 🚧 planning | — | 1 architectural decision (Q — settings hub topology: flat list-of-cards at `/settings`, no shared layout wrapper, sibling routes for Profile/2FA/Sessions). Light-touch — most stories are component-level. Single epic E12 (5 stories 12.1-12.5). See section "Initiative 7" below. |
| 8 | Catalog Mobile & Image Performance | 🚧 planning | — | 1 architectural decision (P — on-upload thumbnail pipeline + WebP @ q80 800px longest side + query-param variant endpoint + on-disk `.thumb.webp` co-location + arq task in existing API worker + idempotent backfill script). Cross-cutting backend+frontend. Single epic E13 (2 stories 13.1-13.2). See section "Initiative 8" below. |
| 9 | Test Isolation Cleanup | 🚧 planning | — | **No architectural decisions** — test-infrastructure-only work. Pointer-only section listed for index completeness. Single epic E14 (3 stories 14.1-14.3). See section "Initiative 9" below. |
| 10 | Operator Polish Batch | 🚧 planning | — | 3 architectural decisions (L — ModelNote bilingual schema migration forward-only Alembic; M — anonymous share-link frontend route shell; N — admin manual-add model + file upload write surface). Three epics E15+E16+E17. Source SCP: `sprint-change-proposal-2026-05-22-init10.md`. See section "Initiative 10" below. |
| 19 | Spoolman Read-Only Inventory (MVP-A) | 🚧 planning | — | 3 architectural decisions (AD — cache topology Redis 30s TTL + arq 60s poll + SETNX leader-election + observability with `external_service=spoolman` tag + 3-row cache-coherence table for `["spools", "summary"]` query-key; AE — network transport via internal docker network with configs-side coordination PR + P4a host-network fallback; AF — data-model carry-through surfacing ALL Spoolman cost-relevant fields end-to-end in DTOs + cache for future Phase D cost-calc UX). Single epic E31 (5 stories 31.1-31.5). All stories `gpt-5.4-mini` Codex routing (no NFR-SECURITY adjacency). Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md`. See section "Initiative 19" below. |
| 20 | STL Slicer Estimates (Per-Part MVP) | 🚧 planning | — | 3 architectural decisions (AH — resolver: recursive Orca system+user inheritance merge + `type` injection + instantiation drop + Spoolman override layer + real-slice validation + canonicalized `bundle_hash` over machine ∥ process ∥ filament ∥ `orca_version` + append-only bundles + `SourceProfileSnapshot` provenance; AI — dedicated containerized headless OrcaSlicer 2.3.2 slicer-worker + `(stl_ref, bundle_ref)` job contract + `<root>/stl/<hash[:2]>/<hash>.stl` cache + g-code parse-and-discard + configs-side compose ownership; AJ — `EstimateRecord` keyed `(stl_hash, bundle_hash)` + exhaustive recompute-trigger table + cost-only-arithmetic-recompute rule preventing re-slice storms). Resolver precedence: exact bundle > custom override > material default > unsupported. Single epic E32 (6 stories 32.1-32.6). Per-STL only; no whole-plate slicing; not e-commerce; Spoolman = inventory SoT; Fenrir = bench-only. Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md`. See section "Initiative 20" below. |
| 21 | Admin-Managed Orca Process Profiles + User-Facing Selector Options | 🚧 planning | — | 2 architectural decisions (AK — admin-managed profile **inventory read** projected over the existing resolver (`resolve_preset` resolvability + `VendoredProfileSource` provenance, no new resolve logic) **+ the OD-7 compatibility map** as a first-class explicit declaration extending the named FE↔BE `QualityTier`/`MaterialClass` contract, backend = SoT, FE mirrors + parity-tested, `offerable = imported ∧ resolvable ∧ compatible`; AL — import **write posture**: validated triple (structural `resolve()` ∧ compatibility) written **in-place** into `SLICER_VENDORED_PROFILES_DIR/intents/...` (provenance-snapshot-safe) + **on-disk sidecar manifest** for admin metadata + per-slot compatibility status/reason + existing audit log, **no Alembic migration in v1**, configs-side portal-content RW mount is a write-slice-only HC2 item). Read-only inventory first (zero write/deploy risk). Single epic E33 (3 stories 33.1-33.3). Process/intent profiles only; NOT Spoolman inventory/cost. Preserves Init 20 `bundle_hash` + `source_system_tree_hash` + append-only invariants. Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md`. See section "Initiative 21" below. |
| 22 | Admin Operational Observability (Worker/Job Console) | 🚧 planning | — | 3 architectural decisions (AO — admin queue-console **read model**: a read-only raw-arq **live snapshot** computed per-request over the lifespan-owned `app.state` arq pool + raw Redis (`apps/api/app/main.py:64-94`) — per-pool `zcard` queued (exact) + bounded `SCAN arq:in-progress:*` + bounded hard-capped `SCAN arq:result:*` (**never** the unbounded `KEYS` of `all_job_results()`) — no new table, no worker change; reuses the existing business-keyed status keys (`render:status:{model_id}`, slicer `EstimateStatus`) as the job-context layer; **console lives in the admin area `/admin/queues`, NOT the member `/queue` slot**; durable job-activity ledger **deferred** (G-LEDGER). AP — **worker-liveness tri-state** from the coarse `<queue>:health-check` key (presence + age; `health_check_interval` 3600s today, surfaced verbatim) — coarse ~1h liveness **accepted for MVP** (running/queued stay exact), interval-lowering deferred (G-LIVENESS). AQ — **leak fence / read-only privacy contract**: field-allowlist DTO, never raw pickled `args`/`kwargs`/`result`, curated `error_class`/`context`, `current_admin`-gated, `GET`-only, no `_PUBLIC_ROUTES` edit). Endpoint `GET /api/admin/queues` in a new `apps/api/app/modules/queue/` package (OD-4); FE `/admin/queues` admin tab. Single epic E34 (1 read-only MVP story, ADMIN-JOBS-1). API-read-only + FE → SW-DEPLOY-1 NOT triggered. Sequenced BEFORE G-PUBLISH (Init 21 PROFILE-OFFER-1). Discovery: `spec-admin-jobs-console.md` (commit dcb9df8). Source SCP: `sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md`. See section "Initiative 22" below. |

## Initiative 0 — Product Foundation: Home 3D-Printing Catalog

**Status:** shipped retrospective (v1 cutover 2026-04; documented 2026-05-15). **Framing:** the foundation's architectural decisions were made and shipped before BMAD adoption — they are not re-litigated here. This section is a **pointer to authoritative documents** so downstream initiatives can extend a documented baseline rather than implicit context.

### Authoritative architectural sources for v1

| Concern | Authoritative source |
|---|---|
| Component topology (web / api / worker / redis / nginx-180 edge) | [`docs/architecture.md`](../../docs/architecture.md) — condensed view |
| Full v1 design specification | [`docs/design/2026-04-29-portal-design.md`](../../docs/design/2026-04-29-portal-design.md) |
| v1 implementation plan (12 phases) | [`docs/plans/2026-04-29-portal-v1-implementation.md`](../../docs/plans/2026-04-29-portal-v1-implementation.md) |
| Project capabilities + user personas + deployment | [`docs/project-overview.md`](../../docs/project-overview.md) (generated 2026-05-15) |
| Annotated source tree | [`docs/source-tree-analysis.md`](../../docs/source-tree-analysis.md) (generated 2026-05-15) |
| Implementation rules (136 must-respect items) | [`_bmad-output/project-context.md`](../project-context.md) |
| Operations runbook | [`docs/operations.md`](../../docs/operations.md) |
| Data plane (11 migrations) | `apps/api/migrations/versions/0001_initial.py` through `0011_index_ext_link_url.py` |

### Why no decision matrix here

The architectural decisions for v1 (SQLite vs Postgres, SQLModel vs raw SQLAlchemy, FastAPI vs Django, React + TanStack vs Next.js, arq vs Celery, three.js for the STL viewer, etc.) were taken in the 2026-04-29 design spec. **Re-listing them as A–H entries in this file would duplicate the spec without adding decision provenance.** Initiative 1+ (this file's existing content) layers deltas ON the v1 baseline; the baseline itself is owned by `docs/design/2026-04-29-portal-design.md`.

If a future initiative needs to **revisit** a v1 architectural choice (e.g., flip SQLite → Postgres), that initiative gets its own H2 section with its own decision matrix referencing the v1 baseline being changed.

### Cross-references

- **PRD section:** `prd.md` § Initiative 0 — Product Foundation: Home 3D-Printing Catalog.
- **Epics section:** `epics.md` § Initiative 0 — E0.1 through E0.9 retrospective foundation epics.
- **Brief:** `_bmad-output/planning-artifacts/product-brief-3d-portal.md` + distillate sibling (created 2026-05-15).

---

## Initiative 1 — Useful GlitchTip Delta

**Status:** shipped 2026-05-10. Project mode: brownfield — observability infrastructure delta layered on the existing 2026-04-30 Sentry/glitchtip-cli baseline. Built through step-by-step BMAD architecture-skill discovery.

### Project Context Analysis

#### Requirements Overview

**Functional Requirements (30 FRs across 7 capability areas):**

- **A. Production Frontend Symbolication (FR1–4)** — emit debug IDs, upload to GlitchTip, single-source release expression, hard-fail policy on upload error.
- **B. Event Noise Filtering & Tagging (FR5–9)** — denyUrls / ignoreErrors / `beforeSend` filters; static identity tags + dynamic context tags re-attached on TanStack Router navigation.
- **C. Post-Deploy Verification (FR10–16)** — `verify-symbolication.sh` smoke + 30s poll + fingerprint match + tripwire timestamp + synthetic alarm event + `deploy.sh` integration.
- **D. GlitchTip-to-BMAD Triage Bridge (FR17–20)** — `glitchtip-triage.sh <issue_id>` returns markdown story stub, fixed-order schema, read-only.
- **E. Build-Time Security & Determinism (FR21–24)** — token never in image layers, no map URL exposure, in-image build, `sourcemap: 'hidden'` invariant.
- **F. Operational Continuity & Recovery (FR25–28)** — CLI fallback path, same-release identity, token rotation procedure, scope minimization.
- **G. Documentation & Execution Discipline (FR29–30)** — `operations.md` rewrite + 3 new project-context.md execution-discipline rules.

**Non-Functional Requirements (17 NFRs):**

- **Performance (P1–P4):** SDK overhead ≤2 KB/event, build upload ≤10 s, verify ≤30 s, triage ≤5 s.
- **Security (S1–S5):** Token-at-rest scoping, quarterly rotation, scope minimization, network exposure exactly 2 hosts, no map leakage cadence.
- **Reliability (R1–R4):** Verify false-positive ≤1/100, CLI fallback verified per release cycle, three-signal failure detection (NFR-R3 codifies FR4 + FR14 + FR16), decay window ≤1 deploy cycle.
- **Integration (I1–I4):** GlitchTip 6.1.x API versioned dependency, ECS-style tag taxonomy alignment, stable triage-script schema (golden-file diff), configs-repo cross-reference integrity.

#### Scale & Complexity

- **Primary domain:** web_app (frontend build pipeline + SDK config + operational scripts)
- **Complexity level:** **Low** — ~5–7 files modified in `apps/web/`, 2 new bash scripts in `infra/scripts/`, 1 baseline plan decoupling, 1 runbook section rewrite, 3 project-context rule additions.
- **Estimated architectural components touched:** 5 — Vite config, SDK init, Dockerfile, deploy.sh, 2 new ops scripts. Plus 2 docs.
- **Brownfield delta size:** Slim. The baseline (2026-04-30 5-phase plan) shipped Sentry SDK + CLI upload + ErrorBoundary; this delta replaces ONE component (CLI → vite-plugin) and adds TWO new operational surfaces (verify + triage scripts) plus filter-ruleset polish on existing instrument.ts.

#### Technical Constraints & Dependencies

**Hard constraints (non-negotiable, from PRD + project-context.md):**

- **Bundle-hash determinism:** Plugin upload runs INSIDE the docker build stage. Local `pnpm build` is forbidden (project-context.md rule). Hashes derive from in-image build only.
- **LAN HTTP `:8800` for chunk upload:** Public HTTPS proxy has 1MB body limit; multi-MB chunks force LAN. Build host requires LAN/VPN reach to `.190`.
- **BuildKit secret for `SENTRY_AUTH_TOKEN`:** Plain `ARG` persists in `docker history` — security boundary forbids it. Mount via `--mount=type=secret,id=sentry_token`.
- **GlitchTip 6.1.x API surface:** Chunk-upload protocol + artifact-bundle assemble endpoint. Phase 0 dry-run gate verifies issue #299 doesn't fire on this specific instance before plugin migration commits.
- **Single-source `RELEASE` expression:** `apps/web/src/release.ts` exports `RELEASE` (`${__PKG_VERSION__}+${__GIT_COMMIT__}`), consumed by `instrument.ts` (runtime SDK) and `infra/scripts/upload-sourcemaps.sh` (CLI fallback, via inline `node -p` + `git rev-parse`). `vite.config.ts` cannot `import` from `src/release.ts` because Vite bundles the config BEFORE its `define` block activates (Story 1.4 discovery), so the plugin's `release.name` inlines the SAME `${PKG_VERSION}+${GIT_COMMIT}` template using vite.config.ts's own local consts that read from the SAME env-var → host-git → `"unknown"` fallback chain plus package.json. Drift-impossible by **shared compute pipeline**, not by shared TypeScript symbol. Add a new compute pipeline (e.g., a third config or build-time runner) and you must mirror the same fallback chain or break the invariant.
- **`build.sourcemap: 'hidden'`:** Stays as-is; deployed bundle has no `sourceMappingURL`. Plugin's `filesToDeleteAfterUpload` removes maps from `dist/` before image extraction.
- **Plugin placement LAST in `vite.config.ts` `plugins[]`:** Earlier placement risks tree-shaking + map-before-injection ordering bugs.

**Brownfield dependencies (existing baseline this delta builds on):**

- `@sentry/react` 8.x already initialized in `apps/web/src/instrument.ts` with `release: VITE_PORTAL_VERSION`, `setTag('service', 'web')`, `tracesSampleRate: 0`.
- `<Sentry.ErrorBoundary>` already wraps `<RouterProvider>` in `apps/web/src/main.tsx` (Phase 3 of baseline plan).
- `infra/scripts/upload-sourcemaps.sh` already runs `glitchtip-cli` v0.1.0 (SHA-pinned) — decoupled from `deploy.sh` in this delta but kept as documented manual recovery (FR25).
- `infra/scripts/deploy.sh` orchestrates build + ship + restart + alembic migrate. This delta adds verify-call + last-verify-tripwire (FR15, FR16).

**Cross-repo dependencies:**

- `~/repos/configs/docs/glitchtip-agent-guide.md` — auth flow, REST recipes (load-bearing for triage script + verify script implementation).
- `~/repos/configs/docs/observability-logging-contract.md` — ECS-style tag taxonomy alignment (NFR-I2).
- `~/repos/configs/nginx/3d-portal.conf` — edge proxy NOT touched by this delta; `:8800` bypasses edge entirely.

#### Cross-Cutting Concerns Identified

1. **Build-time vs runtime release identity coherence.** Single shared expression in `release.ts`; affects plugin + SDK + verify-script + CLI fallback. Spans 4 components.
2. **Secret handling boundary at build time.** `SENTRY_AUTH_TOKEN` flows: dev-box `infra/.env` → BuildKit secret mount → plugin upload → never persisted in image. Spans Dockerfile, deploy.sh, plugin config.
3. **Verification + alarm channel reuse.** `verify-symbolication.sh` writes `infra/.last-verify` (consumed by deploy.sh), emits synthetic GlitchTip event on failure (alarm without new infra), and records exit codes consumed by deploy.sh stale-check. Spans 3 surfaces: filesystem, GlitchTip ingest, deploy script.
4. **GlitchTip API surface as load-bearing dependency.** All three new/modified scripts (verify, triage, decoupled CLI fallback) hit GlitchTip REST. Versioned at 6.1.x; upgrade requires re-validation per NFR-I1.
5. **BMAD pipeline integration as output.** `glitchtip-triage.sh` formats markdown stub paste-ready for `bmad-quick-dev`/`bmad-create-story`. Schema is a stable contract (NFR-I3, golden-file diff verifiable). Spans script implementation + project-context.md execution-discipline rule.
6. **Decay protection across boundaries.** Manual rituals decay; instrumented rituals don't. `deploy.sh` reads `infra/.last-verify` and warns on stale state; `verify-symbolication.sh` writes the timestamp; failed verify emits synthetic GlitchTip event. Three independent components in a tripwire loop (NFR-R3).
7. **Brownfield baseline preservation.** The 2026-04-30 plan's existing components (instrument.ts setTag wiring, ErrorBoundary, hidden sourcemaps, glitchtip-cli script) all remain functional. Delta is additive (verify + triage) plus one substitution (CLI → plugin in active path).

### Starter Template Evaluation

**Status:** N/A — brownfield delta.

This PRD modifies an existing React 19 + Vite 6 + TypeScript 5.6 + Tailwind v4 + shadcn/ui project (`3d-portal`, host project initialized 2026-04-29). All starter-level decisions (language, framework, build tool, styling, testing, project structure) are **frozen at baseline** per PRD's "Frozen Baseline" table — this delta touches none of them.

The pre-existing `@sentry/react ^8.45.0` SDK + `<Sentry.ErrorBoundary>` integration + multi-stage Dockerfile + Vite/TypeScript configs constitute the inherited foundation. Architectural decisions for this delta therefore start from "what's already there" rather than "what to choose" — the actual decision space is the 5 architectural surfaces enumerated in Project Context Analysis (Vite plugin config, SDK config polish, Dockerfile secret-mount changes, deploy.sh integration, two new operational scripts).

**Implication for downstream steps:** Step 4 (Architectural Decisions) starts directly from the brownfield baseline; no starter-bootstrap stories required.

### Core Architectural Decisions

#### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

1. Plugin choice + version pinning (`@sentry/vite-plugin` 5.2.x)
2. Secret transport mechanism (BuildKit secret mount, NOT plain `ARG`)
3. Failure policy on plugin upload error (hard-fail + documented CLI fallback)
4. Verification fingerprint scheme (`smoke.run_id=<uuid>` per run)

**Important Decisions (Shape Architecture):**

5. Triage script output schema (fixed-order markdown stub + golden-file diff)
6. Tag taxonomy alignment with `observability-logging-contract.md` (ECS-style dotted)
7. Decay protection topology (`infra/.last-verify` + synthetic GlitchTip event on failure)

**Deferred Decisions (Post-MVP, gated):**

- Backend SDK polish (gated: ≥3 BMAD-triaged issues in 30 days)
- Alerting webhook (gated: pull-only proves insufficient in measurable cases)
- CI auto-verify (gated: 3d-portal acquires CI runner)

#### Data Architecture

**Status:** N/A for this delta. SQLite `portal.db` (catalog SoT) + `portal-content` volume + Redis queue all stay frozen at baseline. No schema migrations required by FR1–30.

#### Authentication & Security

**Decision A: `SENTRY_AUTH_TOKEN` transport via BuildKit secret mount.**

- **Choice:** `--mount=type=secret,id=sentry_token` in `apps/web/Dockerfile`'s build stage.
- **Alternatives rejected:** Plain `ARG SENTRY_AUTH_TOKEN` (persists in `docker history` — security boundary violation per NFR-S1); env-file copied into image (same persistence problem); password-grant API call at build time (GlitchTip doesn't expose `/auth/login/`, agent-guide explicit).
- **Rationale:** BuildKit secrets are mounted at build time, never written to image layers. `docker history` post-build shows no token trace. Aligns with NFR-S1 token-at-rest scoping.
- **Cascading implications:** `deploy.sh` must export `DOCKER_BUILDKIT=1` before `docker compose build`. Token source remains `infra/.env` on dev box (mode 600, not pushed to `.190`). Token rotation procedure (FR27, Journey 4) updates `infra/.env` only, no image rebuild semantics change.

**Decision B: Token scope minimization.**

- **Choice:** Required scopes for the build/triage token = `org:read`, `project:read`, `project:write`, `project:releases`, `event:write`. NOT `org:write`, NOT `org:admin`.
- **Rationale:** NFR-S3 + glitchtip-agent-guide.md scope spec. Read+release+upload sufficient for plugin upload; `event:write` covers synthetic alarm event in failed verify (FR14). Anything broader is unnecessary attack surface.
- **Cascading:** `operations.md` rotation runbook lists exact scope set so re-mint is replicable (FR28).

**Decision C: Cookie auth and CSRF unchanged.**

- **Status:** Inherited from baseline. `portal_access` JWT (10min) + `portal_refresh` (30d) + `X-Portal-Client: web` CSRF header remain as-is. This delta does NOT touch auth flow.

#### API & Communication Patterns

**Decision D: GlitchTip API surface — split endpoints, versioned dependency.**

- **Choice:** SDK ingestion via `https://glitchtip.ezop.ddns.net/api/<id>/envelope/` (public). Source-map upload via `http://192.168.2.190:8800` (LAN HTTP, mandatory for >1 MB chunks). REST triage via either endpoint (sub-MB GETs).
- **Alternatives rejected:** Public HTTPS for upload (1 MB nginx body limit blocks chunks); legacy `/api/0/.../files/` REST (returns 405 on GlitchTip 6.1.x — agent-guide confirms); zero-upload + name-based resolution ("works most of the time" per operations.md, not bulletproof).
- **Rationale:** Split endpoint constraint is hard, sourced from glitchtip-agent-guide.md and operations.md. Build host must have LAN/VPN reach to `.190`.
- **Cascading:** NFR-S4 enforces "exactly two hosts" at build time. NFR-I1 versions the API surface dependency at GlitchTip 6.1.x; upgrade requires re-validation per `operations.md` upgrade checklist.

**Decision E: Plugin choice — `@sentry/vite-plugin` 5.2.x.**

- **Choice:** Official Sentry-maintained Vite plugin, version 5.2.x. Configured with `url: process.env.SENTRY_URL`, `org: 'homelab'`, `project: '3d-portal'`, `release.name: RELEASE` (from `apps/web/src/release.ts`), `sourcemaps.filesToDeleteAfterUpload: ['./dist/**/*.map']`, `telemetry: false`. Plugin placement LAST in `vite.config.ts` `plugins[]`.
- **Alternatives rejected:** `glitchtip-cli` (current baseline; kept as fallback per FR25 but not active path — single in-build step beats post-build CLI invocation, drift-proof release tagging); `ikenfin/vite-plugin-sentry` (community, slower to track sentry-cli changes, lacks debug-ID-first flow); `sentry-cli` direct invocation in CI (decouples sourcemap upload from build → release drift risk).
- **Rationale:** Plugin is Sentry-maintained, stable on Node 18+, suppresses telemetry for self-hosted, debug-ID-first flow (recommended since sentry-cli 2.17.0 / bundler-plugins 2.0.0). GlitchTip 6.1.6 supports the protocol (4.2 inflection point passed).
- **Cascading:** Phase 0 dry-run gate verifies issue #299 doesn't fire BEFORE merge (PRD scope MVP item). If #299 fires: abort plugin migration, retain CLI flow + ship SDK polish + scripts only — explicit pivot, not implicit fallback.

**Decision F: Triage script output schema — fixed-order markdown stub + golden-file diff verification.**

- **Choice:** `glitchtip-triage.sh <issue_id>` outputs a markdown stub with fields in fixed order: top frame `(filename:line)`, fingerprint, route context, `model.id` (when present), release SHA, last 5 events, suggested file. Schema verifiable via `./infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returning zero diff.
- **Alternatives rejected:** JSON output (downstream BMAD invocations parse markdown more naturally, paste-direct UX); free-form prose (breaks NFR-I3 stable-contract requirement); per-call schema metadata (cost outweighs benefit for a small homelab tool).
- **Rationale:** Markdown stub paste-ready into `bmad-quick-dev` / `bmad-create-story` (FR19); `--schema` flag + golden file enables drift detection without runtime cost. Field order is the contract (NFR-I3).
- **Cascading:** Story-creation step (CE) will produce a story for the script, plus a story for `tests/golden/triage-schema.txt` golden file. CI auto-verify (Phase 2 gated) will run the diff.

#### Frontend Architecture

**Decision G: SDK init enrichment — static + dynamic tag attachment topology.**

- **Choice:**
  - **Static identity tags** (attach once at SDK init in `instrument.ts`): `service.version` (= `RELEASE`), `host.name` (build host), `deployment.environment` (= `VITE_ENVIRONMENT`), `git.commit` (build-time-injected SHA via Vite `define`), `build.time` (ISO-8601, build-time-injected via Vite `define`).
  - **Dynamic context tags** (re-attach on each TanStack Router navigation event via `router.subscribe('onLoad', ...)`): `route.pathname`, `model.id` (extracted from `useParams` if route matches `/catalog/$id`), `auth.is_authenticated` (from `AuthContext`).
- **Alternatives rejected:** All-static (loses dynamic context — every event tagged with init-time route, useless for triage); all-dynamic (re-attach overhead per event); custom Sentry integration class (over-engineering for 3 dynamic tags).
- **Rationale:** Static-once + dynamic-on-navigation is the minimal correct topology. TanStack Router's `subscribe('onLoad')` fires after navigation completes — captures the route the user is ON when an event fires. Tag taxonomy aligns with `~/repos/configs/docs/observability-logging-contract.md` ECS-style dotted naming (NFR-I2).
- **Cascading:** `apps/web/src/release.ts` exports `RELEASE` constant. Vite `define` injects `__GIT_COMMIT__` + `__BUILD_TIME__` at build time. Stories must enumerate these injection points.

**Decision H: `beforeSend` filter contract.**

- **Choice:** Filter executes in fixed order: (1) `denyUrls` regex match (cheapest exit); (2) `ignoreErrors` title match (empirical + anticipated); (3) `!navigator.onLine` check; (4) `ApiError.detail === "access_expired"` check. Returns `null` to drop, modified event to send.
- **Alternatives rejected:** Single conditional pile (harder to reason about); deny-list-only without `beforeSend` (cannot inspect runtime state like `navigator.onLine`); Sentry built-in `defaultIntegrations` only (lacks app-specific 401 / offline knowledge).
- **Rationale:** Empirical ruleset (FR6, derived from Phase 0 Discovery 30-day sample) is the floor; anticipated patterns (extensions, ResizeObserver loop) are easy quick wins; runtime-state filters (offline, refresh-flow 401) require `beforeSend` access.
- **Cascading:** Phase 0 Discovery output → empirical pattern list → instrument.ts implementation. Story for filter implementation depends on Discovery story.

**Decision I: State management + routing + bundle config — frozen at baseline.**

- **Status:** Inherited. TanStack Router 1.x (file-style routes), TanStack Query 5.x, Tailwind v4 + shadcn/ui, Vite 6 build (`build.sourcemap: 'hidden'`), nginx 1.27-alpine serving `dist/`. This delta does NOT touch any of these.

#### Infrastructure & Deployment

**Decision J: Plugin-in-build vs CLI-post-build — in-build, deterministic.**

- **Choice:** Plugin executes during `vite build` INSIDE the docker image build context. Source maps generated, debug IDs injected, upload to `:8800`, `filesToDeleteAfterUpload` removes `.map` files — all before docker build extracts `dist/`.
- **Alternatives rejected:** Local `pnpm build` + plugin upload + then docker build (violates project-context.md bundle-hash determinism rule); CLI post-build outside docker (current baseline; upload-deploy timing window can leave first error of new release unmapped if maps land late).
- **Rationale:** Determinism-preserving (extract-from-image rule holds), upload-then-deploy ordering guaranteed (no first-error race), single pipeline step.
- **Cascading:** Dockerfile build stage requires `DOCKER_BUILDKIT=1` env (BuildKit secret) + LAN reach from build host to `:8800`. `deploy.sh` exports the env var; off-LAN dev box → deploy fails by design.

**Decision K: `deploy.sh` integration — non-fatal verify + tripwire.**

- **Choice:** `deploy.sh` invokes `verify-symbolication.sh` AFTER successful `docker compose up -d` + `alembic upgrade head`. Verify exit code does NOT fail the deploy script (exit 0 propagates regardless), but loud red warning prints on non-zero. Tripwire: `deploy.sh` checks `infra/.last-verify` mtime at start; warns if older than previous deploy mtime.
- **Alternatives rejected:** Fail-on-verify-error (rolls back deploys when GlitchTip is the broken party — wrong blame); silent verify (decay risk); separate cron-based verify (over-engineering for solo-dev).
- **Rationale:** Deploy success is decoupled from observability post-condition (NFR-R3 three-signal model). Operator-visible signal in three places: stdout warning, `infra/.last-verify` FAILED marker, synthetic GlitchTip event tagged `deploy.verification=failed`. Decay protection via timestamp tripwire (FR16, NFR-R4).
- **Cascading:** `verify-symbolication.sh` exit codes (FR12 contract: 0/1/2/3/4) consumed by `deploy.sh` for warning text. Failed-verify synthetic event hits same DSN as runtime errors → same triage path.

**Decision L: CI/CD strategy — `deploy.sh` IS the CI for now; CI auto-verify gated to Phase 2.**

- **Choice:** No GitHub Actions / GitLab CI in scope. `deploy.sh` orchestrates build + verify locally on dev box. Future CI auto-verify gated on 3d-portal acquiring a CI runner reachable from `.190` LAN.
- **Rationale:** Solo-dev project, low deploy frequency, LAN-only `:8800` dependency makes hosted-CI tricky. Phase 2 brief addresses CI when measurable case justifies.

#### Decision Impact Analysis

**Implementation Sequence (informs CE story ordering):**

1. **Phase 0 dry-run gate** — one-shot local plugin smoke against `:8800`. If issue #299 fires, abort Decisions E/J, re-scope brief.
2. **Discovery story** — sample 30-day GlitchTip issues → derive empirical filter ruleset (Decision H).
3. **Foundation: `apps/web/src/release.ts`** — single-source `RELEASE` constant. Imported by `instrument.ts` (runtime SDK). Compile-time check on instrument-side drift.
4. **Plugin wiring: `vite.config.ts`** — Decision E + Decision J. Last in `plugins[]`. Inlines `${PKG_VERSION}+${GIT_COMMIT}` using its own local consts (Story 1.4 discovery: cannot `import` `release.ts` because config bundles before `define` activates). Both `vite.config.ts` and `release.ts` read the same env-var → host-git → `"unknown"` fallback chain plus package.json — shared compute pipeline, not shared symbol.
5. **Dockerfile + compose: BuildKit secret** — Decision A + B. `infra/.env` source, mount-type=secret.
6. **`instrument.ts` polish** — Decision G + H. Tag attachment topology + filter contract. Depends on (3) for `RELEASE` import.
7. **Operational scripts** — `verify-symbolication.sh` (FR10–16) + `glitchtip-triage.sh` (FR17–20, Decision F). Independent of (4)–(6); can parallelize.
8. **`deploy.sh` integration** — Decision K. Depends on (7) for verify script.
9. **`upload-sourcemaps.sh` decoupling** — header comment + remove from deploy.sh. Independent of (4)–(8).
10. **Documentation** — `operations.md` rewrite + `_bmad-output/project-context.md` execution-discipline rules. After all code lands.

**Cross-Component Dependencies:**

- `release.ts` (3) is load-bearing for plugin (4), SDK config (6), CLI fallback (still imports same release tag), verify-symbolication.sh (smoke event needs release context for matching).
- BuildKit secret mechanism (5) gates plugin upload (4) end-to-end test capability.
- Discovery output (2) gates filter ruleset story (6).
- `verify-symbolication.sh` exit-code contract (FR12) gates `deploy.sh` integration (8).
- Issue #299 outcome of Phase 0 (1) gates Decisions E and J — pivot path documented in PRD Risk Mitigation table.

### Implementation Patterns & Consistency Rules

#### Pattern Categories Defined

Most baseline patterns (file naming, TypeScript imports, FastAPI Annotated DI, ruff config, ESLint rules, Tailwind theme tokens) are inherited from `_bmad-output/project-context.md` and `AGENTS.md` and remain unchanged. This section pins patterns SPECIFIC to the observability delta where AI agents implementing FR1–30 could otherwise make divergent choices.

#### Bash Script Conventions (`infra/scripts/`)

The two new scripts (`verify-symbolication.sh`, `glitchtip-triage.sh`) plus the modified `deploy.sh` and `upload-sourcemaps.sh` (kept) follow a single conventions set.

**MANDATORY:**

- **Strict mode:** Every script starts with `set -euo pipefail`. No `|| true` on critical operations.
- **Dependency check:** Scripts depending on `jq` / `curl` start with `command -v <tool> >/dev/null || { echo "missing: <tool>" >&2; exit 1; }`.
- **Env loading:** Scripts source `infra/.env` exactly once at start: `set -a; source infra/.env; set +a`. Never read from random paths.
- **Required env validation:** `: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"` syntax for hard requirements. No silent defaults.
- **Stdout vs stderr:** Operator-readable narrative on stdout (progress, status). Errors and warnings on stderr. Tools like `jq` outputs go to stdout for piping.
- **Exit codes:** 0 = success; non-zero = specific failure mode. Each script's exit code map is documented in its header comment block.
- **Header comment block:** First 10–20 lines of every script explain: purpose, required env, exit codes, when to run, recovery path. Format consistent across the four scripts.

**Exit-code spec for `verify-symbolication.sh` (FR12):**

| Code | Meaning |
|---|---|
| 0 | Success — smoke event symbolicated to `^apps/web/src/.+\.tsx?$` |
| 1 | Symbolication broken — event found but top frame regex mismatch |
| 2 | GlitchTip unreachable — REST 5xx or network error |
| 3 | Auth/scope failure — REST 401/403 |
| 4 | Timeout — no matching event within 30 s budget |

`deploy.sh` reads this code and produces matching warning text.

#### Sentry SDK Usage Idioms (`apps/web/src/instrument.ts`)

**Static identity tags (attach once, at SDK init):** Use `Sentry.setTag(key, value)` after `Sentry.init({...})`. One call per tag. Do NOT use `Sentry.configureScope` for static tags (heavier, scope-stacking semantics not needed).

**Dynamic context tags (re-attach per navigation):** Subscribe to TanStack Router via `router.subscribe('onLoad', ({ matches }) => { Sentry.setTag('route.pathname', ...); ... })`. Tag attachment is idempotent; setting the same tag twice with the same value is a no-op.

**Filter ordering:** `beforeSend(event, hint)` returns `null` to drop, modified event to send. Order is fixed (cheapest exit first):

1. `denyUrls` regex match against `event.request?.url`
2. `ignoreErrors` title match against `event.exception?.values?.[0]?.value`
3. `!navigator.onLine` → drop
4. `hint.originalException instanceof ApiError && hint.originalException.body?.detail === "access_expired"` → drop
5. Return event unchanged

Each filter step is a separate `if` with early `return null` — readable, testable per branch.

#### Build-Time Constant Injection (`vite.config.ts`)

Vite's `define` is the canonical mechanism for `__GIT_COMMIT__`, `__BUILD_TIME__`, and any other build-time values consumed by `instrument.ts`.

**Pattern:**

```typescript
import { execSync } from 'node:child_process';
import { RELEASE } from './src/release';

const GIT_COMMIT = execSync('git rev-parse --short HEAD').toString().trim();
const BUILD_TIME = new Date().toISOString();

export default defineConfig({
  define: {
    __GIT_COMMIT__: JSON.stringify(GIT_COMMIT),
    __BUILD_TIME__: JSON.stringify(BUILD_TIME),
  },
  // ... other config ...
});
```

**Type declaration:** Add to `apps/web/src/vite-env.d.ts`:

```typescript
declare const __GIT_COMMIT__: string;
declare const __BUILD_TIME__: string;
```

`instrument.ts` consumes them as plain identifiers. Drift = TypeScript compile error (because declarations are explicit).

#### `infra/.last-verify` File Format

Single-purpose tripwire file. Format:

```
<ISO-8601 timestamp>\t<STATUS>\t<deploy_version>
```

- One line, tab-separated, plain ASCII.
- `STATUS` ∈ {`OK`, `FAILED`}.
- `deploy_version` matches `RELEASE` (e.g., `0.1.0+ab12cd3`).

Example: `2026-05-09T14:22:15Z	OK	0.1.0+ab12cd3`.

`deploy.sh` reads this file with `cut -f1 infra/.last-verify` for timestamp comparison; full line for warning text.

#### Synthetic GlitchTip Event Structure (failed verify)

When `verify-symbolication.sh` fails, it POSTs a synthetic event to GlitchTip's envelope endpoint with:

- `tags`: `{ "deploy.verification": "failed", "smoke.run_id": "<uuid>", "service.version": "<RELEASE>", "deployment.environment": "production" }`
- `level`: `"warning"` (NOT `error` — this is a meta-failure, not an app exception)
- `message`: `"deploy verification failed: <exit_code_meaning>"`
- `extra`: `{ "exit_code": <0..4>, "expected_top_frame_regex": "^apps/web/src/.+\\.tsx?$", "actual_top_frame": "<frame>" }`

Same DSN as runtime errors → same triage path. Tag `deploy.verification` is the filter key for distinguishing from real errors.

#### Markdown Stub Format (`glitchtip-triage.sh`)

Output is plain markdown, fields in fixed order (NFR-I3 contract). Template:

```
# Issue #<issue_id>: <title>

- **Top frame:** `<filename>:<line>`
- **Fingerprint:** `<fingerprint>`
- **Route:** `<route.pathname>` <model.id if present: `(model.id=<id>)`>
- **Release:** `<release>` (commit `<git.commit>`)
- **Last 5 events:**
  1. `<timestamp>` — `<message preview>`
  ...
- **Suggested file to edit:** `<filename>` (top-frame source)

GlitchTip link: <permalink>
```

`./infra/scripts/glitchtip-triage.sh --schema` prints the bare template (no values). Golden file `tests/golden/triage-schema.txt` is exactly that template; `diff -u` against it returns zero on stable contract.

#### Curl + jq Idioms

Standard pattern across the four scripts:

```bash
http_code=$(curl -sS -o /tmp/gt-response.json -w '%{http_code}' \
  -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" \
  "$GLITCHTIP_URL/api/0/...")

case "$http_code" in
  20*) ;;  # success, fall through
  401|403) echo "auth/scope failure ($http_code)" >&2; exit 3 ;;
  5*)  echo "GlitchTip unreachable ($http_code)" >&2; exit 2 ;;
  *)   echo "unexpected response ($http_code): $(cat /tmp/gt-response.json)" >&2; exit 1 ;;
esac

# Extract field with jq:
title=$(jq -r '.title' < /tmp/gt-response.json)
```

Consistent across all GlitchTip REST calls in this delta.

#### Project-Context Patterns Inherited (Not Re-Specified Here)

The following patterns are pinned in `_bmad-output/project-context.md` and apply unchanged:

- **Frontend:** TypeScript path alias `@/*`, no inline hex colors, `api()` wrapper for HTTP, ESLint `--max-warnings=0`, components `PascalCase.tsx`, Tailwind theme tokens via CSS variables.
- **Backend:** ruff config, FastAPI `Annotated[Session, Depends(get_session)]`, SQLModel `Session.exec(select(...))`, soft-delete `Model.deleted_at.is_(None)`, structured JSON logs.
- **Git:** trunk-only `main`, ff-merge only, conventional commits with scope, no `--no-verify`.
- **Deploy:** auto-deploy after every code/infra commit (doc-only skips).

#### Enforcement Guidelines

**All AI Agents MUST:**

- Use `set -euo pipefail` in every new bash script. Exit codes from the contract above for `verify-symbolication.sh`.
- Import `RELEASE` from `apps/web/src/release.ts` in any new code that needs the release tag — never duplicate the expression.
- Use `Sentry.setTag` for static tags, `router.subscribe('onLoad', ...)` for dynamic tags. Filter ordering in `beforeSend` is fixed.
- Format markdown stub output identically to the golden file in `tests/golden/triage-schema.txt`.
- Use the standard curl+jq error-handling pattern for any GlitchTip REST call.

**Pattern Enforcement:**

- Schema drift detected by `glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` (post-deploy or CI).
- Visual regression matrix unchanged (this delta touches no UI; any diff signals unintended regression).
- TypeScript compile error on `RELEASE` import-path drift.

#### Pattern Examples

**Good — single-source release import:**

```typescript
// apps/web/src/instrument.ts
import { RELEASE } from "@/release";
Sentry.init({ release: RELEASE, /* ... */ });

// apps/web/vite.config.ts
import { RELEASE } from './src/release';
sentryVitePlugin({ release: { name: RELEASE } });
```

**Anti-pattern — release tag drift:**

```typescript
// apps/web/src/instrument.ts
Sentry.init({ release: import.meta.env.VITE_PORTAL_VERSION ?? "0.1.0", /* ... */ });

// apps/web/vite.config.ts
sentryVitePlugin({ release: { name: process.env.PORTAL_VERSION || "unknown" } });
```

Two separate expressions; nothing prevents drift if one env var is renamed. Forbidden.

**Good — exit-code-driven warning in `deploy.sh`:**

```bash
verify_exit=0
bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || verify_exit=$?

case "$verify_exit" in
  0) ;; # silent success
  1) echo "⚠ verify FAILED: symbolication broken (top frame regex mismatch)" ;;
  2) echo "⚠ verify FAILED: GlitchTip unreachable" ;;
  3) echo "⚠ verify FAILED: auth/scope failure — token rotation needed?" ;;
  4) echo "⚠ verify FAILED: timeout (no matching event within 30s)" ;;
esac
```

**Anti-pattern — silent verify in deploy.sh:**

```bash
bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || true
```

Loses the failure signal. Forbidden by Decision K.

### Project Structure & Boundaries

#### Delta Footprint (NEW + MODIFIED files)

The full 3d-portal repository tree is canonical in `AGENTS.md`. This section enumerates only files this delta TOUCHES.

**NEW files:**

```
apps/web/src/release.ts                   # Single-source RELEASE constant
apps/web/src/vite-env.d.ts                # Add __GIT_COMMIT__, __BUILD_TIME__ declarations
infra/scripts/verify-symbolication.sh     # Smoke + 30s poll + tripwire + alarm event
infra/scripts/glitchtip-triage.sh         # Issue → markdown story stub
infra/.last-verify                        # Generated at runtime; gitignored
tests/golden/triage-schema.txt            # Golden file for triage-script schema diff
```

**MODIFIED files:**

```
apps/web/vite.config.ts                   # + @sentry/vite-plugin (LAST in plugins[]); + define for git/build
apps/web/src/instrument.ts                # Tag attachment + beforeSend filter; import RELEASE
apps/web/Dockerfile                       # BuildKit secret mount for SENTRY_AUTH_TOKEN
infra/docker-compose.yml                  # SENTRY_ORG, SENTRY_PROJECT, SENTRY_URL build args
infra/scripts/deploy.sh                   # DOCKER_BUILDKIT=1, post-deploy verify call, last-verify tripwire
infra/scripts/upload-sourcemaps.sh        # Header comment update; decoupled from deploy.sh
apps/web/package.json                     # + @sentry/vite-plugin dep
docs/operations.md                        # Section rewrite: ritual + recovery + rotation + triage
_bmad-output/project-context.md           # +3 execution-discipline rules
```

**UNTOUCHED (frozen baseline) — explicit non-list:**

- `apps/api/**` (no backend changes — Phase 2 gated)
- `workers/render/**` (no worker changes)
- `apps/web/src/main.tsx` (ErrorBoundary wiring already shipped 2026-04-30)
- `apps/web/src/{shell,modules,ui,lib,locales,routes}/**` (no UI changes)
- `infra/nginx-180/**` (edge proxy in `~/repos/configs/`, not touched)

#### FR → File Mapping

| FR(s) | File(s) |
|---|---|
| FR1, FR3 | `apps/web/src/release.ts`, `apps/web/vite.config.ts`, `apps/web/src/instrument.ts` |
| FR2, FR4, FR21–24 | `apps/web/vite.config.ts`, `apps/web/Dockerfile`, `infra/docker-compose.yml` |
| FR5–9 | `apps/web/src/instrument.ts`, `apps/web/src/vite-env.d.ts` |
| FR10–14 | `infra/scripts/verify-symbolication.sh` |
| FR15, FR16 | `infra/scripts/deploy.sh`, `infra/.last-verify` |
| FR17–20 | `infra/scripts/glitchtip-triage.sh`, `tests/golden/triage-schema.txt` |
| FR25, FR26 | `infra/scripts/upload-sourcemaps.sh`, `infra/scripts/deploy.sh` |
| FR27, FR28 | `docs/operations.md`, `infra/.env` (token rotation procedure) |
| FR29 | `docs/operations.md` |
| FR30 | `_bmad-output/project-context.md` |

#### Architectural Boundaries

**Build-time boundary (`apps/web/Dockerfile` `node:22-alpine` stage):**

- IN: source code, `infra/.env` (BuildKit secret mount), package.json deps
- OUT: `dist/` artifacts (via image extract in deploy.sh), source maps uploaded to `:8800`
- TOKEN HANDLING: `SENTRY_AUTH_TOKEN` enters via `--mount=type=secret,id=sentry_token`, exits via plugin upload, never persists in image layer.

**Runtime boundary (`apps/web` nginx serve, browser-side):**

- IN: bundled `dist/` (no maps), env-injected DSN
- OUT: events to `https://glitchtip.ezop.ddns.net/api/<id>/envelope/` (public)
- DOES NOT HAVE: source map files, auth token, build-time secrets

**Operational boundary (`infra/scripts/`):**

- `verify-symbolication.sh` IN: env from `infra/.env`, prod URL; OUT: GlitchTip REST queries (read), synthetic event POST on failure (write), `infra/.last-verify` (write).
- `glitchtip-triage.sh` IN: issue ID arg, env from `infra/.env`; OUT: markdown stub on stdout; READ-ONLY against GlitchTip.
- `deploy.sh` IN: code/infra commit on `main`; OUT: image push to `.190`, restart compose, alembic migrate, post-deploy verify call.

#### Integration Points

**Internal Communication (within this delta):**

- `release.ts` → `vite.config.ts` (via TS import) and `instrument.ts` (via TS import). Compile-time bound.
- `vite.config.ts` (plugin) → GlitchTip `:8800` chunk-upload endpoint. Build-time HTTP.
- `instrument.ts` (runtime SDK) → GlitchTip `https://.../envelope/`. Browser-side HTTPS.
- `verify-symbolication.sh` → prod URL (smoke event injection) + GlitchTip REST (poll) + `infra/.last-verify` (write) + GlitchTip envelope (synthetic alarm event on failure).
- `glitchtip-triage.sh` → GlitchTip REST (read-only).
- `deploy.sh` → calls `verify-symbolication.sh` and reads `infra/.last-verify`.

**External Integrations:**

- GlitchTip 6.1.x REST API (versioned dependency, NFR-I1).
- GlitchTip 6.1.x chunk-upload protocol.
- BuildKit (Docker BuildKit secret mounts).
- Vite 6 plugin lifecycle (build hook).
- TanStack Router event subscription (`router.subscribe('onLoad', ...)`).

**Data Flow (per deploy cycle):**

1. Operator runs `bash infra/scripts/deploy.sh`.
2. `deploy.sh` checks `infra/.last-verify` mtime; warns if older than previous deploy.
3. `deploy.sh` exports `DOCKER_BUILDKIT=1`, runs `docker compose build` with `--secret id=sentry_token`.
4. Inside Dockerfile build stage: `vite build` runs → plugin injects debug IDs, uploads maps to `:8800`, deletes `.map` files. Build fails hard on plugin upload error.
5. `deploy.sh` extracts `dist/` from image, ships image to `.190`, restarts compose.
6. `deploy.sh` calls `verify-symbolication.sh`. Verify fires smoke event with unique `smoke.run_id`, polls REST 30s, asserts top frame regex.
7. Verify writes `infra/.last-verify` (OK or FAILED) and emits synthetic GlitchTip event on FAILED.
8. `deploy.sh` prints exit-code-mapped warning if non-zero. Deploy success propagates regardless.
9. Real production error fires later → SDK reports event with full tag set → operator/agent uses `glitchtip-triage.sh <issue_id>` → markdown stub → `bmad-quick-dev` → fix → next deploy.

#### File Organization Patterns

**Configuration files:**

- Plugin config inline in `vite.config.ts` (not separate file — small, version-pinned, project-scoped).
- BuildKit secret mount declared in Dockerfile RUN line; `infra/docker-compose.yml` provides build args.
- Token at rest: `infra/.env` only (mode 600, gitignored, dev-box only).

**Source organization:**

- `apps/web/src/release.ts` — small file, exports just `RELEASE`. Sits alongside `instrument.ts` and `main.tsx` (top-level src/).
- `apps/web/src/vite-env.d.ts` — Vite's standard ambient-declarations file; extended with `__GIT_COMMIT__` / `__BUILD_TIME__`.
- Operational scripts in `infra/scripts/` — bash, executable, header-commented.
- Test fixtures in `tests/golden/` — text files for diff-based contract verification.

**Asset organization:**

- No new assets. `tests/golden/triage-schema.txt` is text, not asset.

#### Development Workflow Integration

**Development server:**

- `vite serve` does NOT trigger plugin upload. Dev workflow unchanged.
- Sentry SDK still initializes in dev (DSN + environment="dev"); events sample to GlitchTip but flagged with `deployment.environment=dev`.

**Build process:**

- Plugin executes during `vite build` ONLY, inside docker image build stage.
- Local `pnpm build` (developer machine, outside docker) is forbidden by project-context.md determinism rule. The plugin would still execute but uploaded artifacts would have non-deterministic hashes — this is the "don't build dist locally" anti-pattern.

**Deployment:**

- `deploy.sh` orchestrates the full chain. Operator never invokes individual scripts during normal deploy.
- Manual recovery (CLI fallback, manual verify): operator invokes `infra/scripts/upload-sourcemaps.sh` or `infra/scripts/verify-symbolication.sh` standalone.

**Testing (in scope for stories during CE):**

- Visual regression unchanged (no UI changes).
- Bash script smoke tests can be added to verify exit code semantics (out of scope for this PRD; gated to Phase 2 CI brief).
- Golden-file diff for triage-script schema (post-implementation, runs at deploy time per FR / NFR-I3).

### Architecture Validation Results

#### Coherence Validation ✅

**Decision Compatibility:**

All 12 substantive decisions (A–L) are mutually consistent. Cross-checked:

- Decision E (`@sentry/vite-plugin` 5.2.x, Node 18+) compatible with Vite 6 + TS 5.6 baseline.
- Decision A (BuildKit secret) requires `DOCKER_BUILDKIT=1` enforced in Decision J (deploy.sh).
- Decision G (single-source `RELEASE` from `release.ts`) is consumed by Decision E (plugin config) and Decision K (verify-script smoke event tagging).
- Decision F (markdown stub schema) coheres with NFR-I3 testable verification via golden-file diff.
- Decision E hard-fail (FR4) coheres with Decision K non-fatal verify (FR15) — different layers, different policies, no contradiction (build vs post-deploy).
- CLI fallback (Decision E rejected-alternative kept as recovery) compatible with Decision G — both paths use the same `RELEASE`, drift-impossible.

**Pattern Consistency:**

- Bash conventions (set -euo pipefail, exit codes, env loading) consistent across all 4 scripts.
- Sentry SDK idioms (`setTag` for static, `router.subscribe` for dynamic) consistent with Decision G topology.
- Curl + jq + http_code + case-statement pattern uniform across all GlitchTip REST integrations.
- Naming: dotted ECS-style for tags (`route.pathname`, `service.version`); kebab-case for scripts; snake_case for status markers.

**Structure Alignment:**

- 6 NEW files + 9 MODIFIED files cover all FR1–30 and NFR-P/S/R/I.
- File-level FR→location mapping table (Step 6) shows no orphan FRs and no orphan files.
- Boundaries (build-time / runtime / operational) explicitly separate token handling, secret persistence, and external network reach.

#### Requirements Coverage Validation ✅

**Functional Requirements Coverage (30/30):**

| FR group | Architectural support |
|---|---|
| FR1–4 (symbolication) | Decision E (plugin), Decision J (in-build), Decision G (single-source release) |
| FR5–9 (filtering + tagging) | Decision G (tag topology), Decision H (filter ordering) |
| FR10–16 (verification) | Decision K (deploy.sh integration) + verify-symbolication.sh + Decision G + script patterns |
| FR17–20 (triage bridge) | Decision F (schema contract) + glitchtip-triage.sh + golden-file pattern |
| FR21–24 (security/determinism) | Decision A (BuildKit), Decision J (in-image build), Boundaries section |
| FR25–28 (continuity/recovery) | Decision E rejected-alternatives kept as fallback, token rotation procedure |
| FR29–30 (documentation) | Structure section enumerates docs/operations.md + project-context.md modifications |

**Non-Functional Requirements Coverage (17/17):**

| NFR | Architectural support |
|---|---|
| NFR-P1–P4 (performance bounds) | Quantified via Decision E (plugin overhead), FR12 contract (verify ≤30s), Decision F (triage ≤5s) |
| NFR-S1–S5 (security) | Decision A (BuildKit secret = no token in layers), Decision B (scope minimization), Decision D (network exposure split), Boundaries section codifies "exactly two hosts" |
| NFR-R1–R4 (reliability) | Decision K (three-signal failure model), `infra/.last-verify` tripwire, FR12 regex contract for false-positive prevention |
| NFR-I1–I4 (integration) | Decision D (versioned API surface), Decision F (golden-file diff for schema), tag taxonomy alignment with observability-logging-contract.md |

#### Implementation Readiness Validation ✅

**Decision Completeness:** All 12 decisions documented with explicit choice + alternatives rejected + rationale + cascading implications. Versions pinned where applicable (Vite 6, @sentry/vite-plugin 5.2.x, GlitchTip 6.1.x, Node 18+).

**Structure Completeness:** Delta footprint enumerated 6 new + 9 modified files. FR→file mapping table covers all 30 FRs. Boundaries diagram defines build/runtime/operational separation. Data flow described in 9-step deploy cycle.

**Pattern Completeness:** 8 pattern categories cover all delta-specific surfaces. Each category has concrete code/bash example + good vs anti-pattern. Project-context inheritance explicitly listed (not re-specified).

#### Gap Analysis Results

**Critical Gaps:** **0** — no blockers for implementation.

**Important Gaps:** **2** — to address during CE (story creation), not blocking architecture sign-off.

1. **`RELEASE` constant computation not pinned.** `apps/web/src/release.ts` is named as the single-source location, but the EXACT expression (e.g., `${package.version}+${git_short_sha}` vs `${VITE_PORTAL_VERSION}+${__GIT_COMMIT__}`) is not committed. Story-level decision during CE; should pin against PRD's Tech SC#3.
2. **Phase 0 outcome branches story creation.** Architecture documents both paths (plugin happy-path + CLI-only pivot if issue #299 fires). CE must produce stories for the happy-path baseline and a Phase 0 abort/pivot story; the abort branch may produce different epics. Suggest CE produce two branched epic sets gated on Phase 0 verify-result.

**Nice-to-Have Gaps:** **1** — non-blocking polish.

3. Could add a tiny "version compatibility matrix" table (Vite 6.0+ × @sentry/vite-plugin 5.2.x × Node 18+ × GlitchTip 6.1.x) for quick reference. Current Decisions section disperses these across A/E/J. Not load-bearing; minor doc-readability improvement.

#### Validation Issues Addressed

None blocking. The 2 Important gaps above are deliberately deferred to the next BMAD step (CE) because they are story-level concerns: (1) the exact RELEASE expression is implementation detail that fits naturally into the foundation story; (2) Phase 0 branching is a story-set conditional that CE handles directly.

#### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed (Step 2; 7 cross-cutting concerns + technical constraints + brownfield dependencies enumerated)
- [x] Scale and complexity assessed (Low; 5 components touched; 2-3 person-day budget; brownfield delta size: slim)
- [x] Technical constraints identified (7 hard constraints; 3 cross-repo dependencies; brownfield baseline preserved)
- [x] Cross-cutting concerns mapped (7 concerns spanning 3+ components each)

**Architectural Decisions**

- [x] Critical decisions documented with versions (Decisions A–L; Vite 6 / @sentry/vite-plugin 5.2.x / Node 18+ / GlitchTip 6.1.x)
- [x] Technology stack fully specified (frozen baseline + delta-specific tools enumerated)
- [x] Integration patterns defined (Decision D split endpoints; Decision K verify integration; Decision F triage schema)
- [x] Performance considerations addressed (NFR-P1–P4 → Decision E plugin / FR12 verify timeout / Decision F triage budget)

**Implementation Patterns**

- [x] Naming conventions established (ECS-style dotted tags; kebab-case scripts; standard project-context conventions inherited)
- [x] Structure patterns defined (Step 6 file organization + delta footprint)
- [x] Communication patterns specified (Decision D split endpoints; Decision K signal topology; curl+jq idiom)
- [x] Process patterns documented (bash conventions; SDK idioms; filter ordering; build-time injection)

**Project Structure**

- [x] Complete directory structure defined (delta footprint enumerates 6 new + 9 modified; baseline tree canonical in AGENTS.md)
- [x] Component boundaries established (build / runtime / operational sections in Boundaries)
- [x] Integration points mapped (internal communication + external integrations + 9-step data flow)
- [x] Requirements to structure mapping complete (FR→file table covers all 30 FRs)

**Score: 16/16** — all checklist items confirmed.

#### Architecture Readiness Assessment

**Overall Status:** **READY FOR IMPLEMENTATION**

(Justification: 16/16 checklist items `[x]`; 0 Critical Gaps; 2 Important Gaps both deliberately deferred to CE story-level scope; 1 Nice-to-Have gap is doc-polish only.)

**Confidence Level:** **High**

- Architecture is grounded in a 5/5 Excellent PRD with 100% traceability and 100% coverage validation.
- Brownfield baseline (2026-04-30 plan) is preserved end-to-end; risk surface is small.
- Phase 0 dry-run gate prevents wrong-direction execution if issue #299 fires.
- All 12 decisions document alternatives rejected — future maintainer can audit reasoning.

**Key Strengths:**

- **Brownfield-baseline preservation as first-class concern.** Architecture explicitly enumerates UNTOUCHED components and routes around them.
- **Single-source `RELEASE` expression** as compile-time-enforced drift prevention (Decision G).
- **Three-signal failure model** (Decision K + NFR-R3) makes "silent observability decay" structurally impossible.
- **Phase 0 dry-run gate** with explicit pivot path means we don't bet the brief on an unverified primary path.
- **CLI fallback retained as documented manual recovery** (FR25–26 + Decision E rejected-alternative) — issue #299 has a known one-command escape hatch.
- **Tag taxonomy aligned with observability-logging-contract.md** — this delta strengthens cross-repo standard rather than diverging.
- **`glitchtip-triage.sh` schema as stable contract** with golden-file diff verification — closes the BMAD-input loop testably.

**Areas for Future Enhancement (non-blocking):**

- Backend Sentry init polish brief (gated: ≥3 BMAD-triaged issues in 30d post-rollout)
- Alerting webhook brief (gated: pull-only proves insufficient)
- CI auto-verify brief (gated: 3d-portal acquires CI runner reachable from `.190` LAN)
- Multi-project pattern reuse — promote env-var contract + BuildKit secret pattern + release.ts pattern to `~/repos/configs/docs/observability-logging-contract.md`

#### Implementation Handoff

**AI Agent Guidelines:**

- Read this architecture document + PRD + product-brief-distillate before implementing any FR.
- Follow Decisions A–L exactly. Alternatives are documented for context, not for re-evaluation at story time.
- Use Implementation Patterns section as the consistency contract — bash conventions, Sentry SDK idioms, curl+jq pattern, schema format are all pinned.
- Story execution order MUST respect Step 4's "Implementation Sequence" (1→10) — Phase 0 first, then Discovery, then foundation `release.ts`, then plugin wiring, etc.
- When a decision branches (e.g., Phase 0 pivot to CLI-only), refer to PRD Risk Mitigation table for the alternate path.

**First Implementation Priority:**

**Phase 0 dry-run gate** — one-shot local `vite build` against `.190` GlitchTip with `@sentry/vite-plugin` 5.2.x enabled, fire smoke error, verify symbolication via REST. Outcome gates the rest of the brief:

- Green → proceed with full MVP scope (Decisions E and J active path).
- #299 fires → pivot to "tighten existing CLI flow + ship SDK polish + scripts only" — abort Decision E, retain Decision G (still useful for CLI flow), retain Decisions K, F, A, B (independent of plugin).

## Initiative 2 — Agent Runbook + Legacy SoT Triage

**Status:** ✅ shipped 2026-05-11 (started 2026-05-10). Project mode: brownfield — tooling+docs extension to the SoT-migrated portal (Slices 2A–2D + 3A–3F, completed 2026-05-06 + 2026-05-10). Source-of-truth for capability contract: `prd.md` § "Initiative 2" (11 FRs, 8 NFRs). Decisions A–H below; numbering is initiative-local (Initiative 1's A–L do not conflict).

### Project Context Analysis

**Requirements Overview (Initiative 2):**

- **A. Runbook Content & Curation (FR1–FR4)** — single canonical markdown source covering principles, source-detection table, Printables GraphQL recipe, 3MF conversion procedure. No endpoint signatures (deferred to OpenAPI by NFR8).
- **B. Self-Serving Endpoint & OpenAPI Discovery (FR10, FR11)** — `GET /agent-runbook` serves the markdown; OpenAPI surface enriched with summaries/descriptions/tags/examples on admin+sot routes.
- **C. Auth & Security (FR5)** — agent service-account password at `~/.config/3d-portal/agent.password`, login-then-cookie pattern (POST `/api/auth/login` → ride `portal_access` cookie + CSRF header on mutations).
- **D. Operational Invariants (FR6)** — pre-flight checklist enforced by agent before `POST /api/admin/models`.
- **E. Legacy Folder Triage (FR7)** — written decision in `docs/migration-reports/` re: drop `Model.legacy_id` + 4 migration scripts vs. freeze with marker.
- **F. Acceptance Contract (FR8)** — end-to-end smoke-test by fresh-session agent against real Printables URL.
- **G. Optional CLI (FR9)** — `infra/scripts/add-model-from-url.py` (Growth scope; defer-able).

**Non-Functional Posture:**

- Pull-only ergonomics (NFR1) — inherits Initiative 1's design discipline.
- Credentials-at-rest scope (NFR2) — `~/.config/3d-portal/agent.password` mode 600, never echoed; cookie jar inherits the same discipline.
- Verification gates completion (NFR3) — runbook adoption is "done" only when FR8 transcript exists.
- Deploy-time runbook verification (NFR7) — `deploy.sh` sha256-checks `/agent-runbook` response.
- Decision documentation discipline (NFR4) — written rationale precedes execution of irreversible cleanup.
- Agent-portable (NFR5) — Claude AND Codex executable.
- Idempotent URL re-import (NFR6) — dedup via `ExternalLink` pre-flight check.
- Auto-discovery principle (NFR8) — runbook documents behavior; OpenAPI documents endpoints. Zero duplication.

**Existing Surfaces Reused (no rewrite required):**

- `POST /api/admin/models` + `POST /api/admin/models/{id}/files` — `apps/api/app/modules/sot/admin_router.py` (already shipped; agent role permitted per Slice 2D).
- `infra/scripts/migrate_catalog_3mf.py` — 3MF→STL converter (shipped 2026-05-02, see `docs/migration-reports/2026-05-02-3mf-to-stl-migration.md`).
- `agent-browser` CLI installed system-wide (see `~/.claude/CLAUDE.md` § "Browser automation").
- `FastAPI` OpenAPI generator (`/api/openapi.json` already exists at baseline).
- `agent` role provisioned as a regular `User` row via `python -m scripts.bootstrap_agent --email agent@portal.local` on `.190` (script in `apps/api/scripts/bootstrap_agent.py`); the generated password is captured once and stored on the agent host at `~/.config/3d-portal/agent.password` (mode 600). Auth flow uses the standard cookie-based login (`POST /api/auth/login` → `portal_access` cookie, ~30 min TTL; refresh via `POST /api/auth/refresh`); admin/agent routes read the principal via `Cookie(alias=ACCESS_COOKIE)` (see `apps/api/app/modules/sot/admin_router.py` `_current_admin_or_agent_dep`). No long-lived bearer token surface exists. (Per `docs/operations.md` § "Agent service account".)

### Starter Template Evaluation

**Status:** N/A. Brownfield extension; all new code paths layer on existing modules (`apps/api/app/modules/`) and existing scripts (`infra/scripts/`). No template, no scaffolding step.

### Core Architectural Decisions

#### Decision Priority Analysis (Initiative 2)

**Critical Decisions (Block Implementation):**

1. Runbook delivery mechanism (FastAPI route + Docker COPY, not nginx static — Decision A)
2. Public access for `/agent-runbook` (no auth — Decision B)
3. Layered documentation contract (runbook narrative + OpenAPI signatures — Decision C, codifies NFR8)
4. Fingerprint discipline (sha256 of intro section, single-source `infra/.runbook-fingerprint` — Decision D)

**Important Decisions (Shape Architecture):**

5. OpenAPI enrichment via FastAPI decorators + Pydantic `json_schema_extra` (no external spec — Decision E)
6. Source-detection strategy (GraphQL for Printables, `agent-browser` for the four browser-only sources — Decision F)
7. CLI as thin shim over runbook content (FR9 Growth scope — Decision G)
8. Decision-doc-first pattern for legacy folder triage (rationale BEFORE execution — Decision H)

**Deferred Decisions (Post-MVP, gated):**

- Auto-categorization from model metadata (gated: smoke-test reveals manual category-pick is the dominant remaining friction).
- Multi-source ingestion in one command (gated: ≥3 batch imports done manually in 30 days post-rollout).
- Browser-only source replacement with REST APIs (gated: Thangs/Thingiverse/MakerWorld/Creality Cloud expose public REST in the future).

#### Data Architecture

**Status:** Mostly N/A for this initiative. One column-level decision pending under Decision H (whether `Model.legacy_id` retires or stays). No other schema migrations required by FR1–FR11. The OpenAPI surface enrichment (FR11) does not alter the schema — it adds metadata that Pydantic emits into OpenAPI.

#### Runbook Delivery & Discovery

**Decision A: Runbook delivered by FastAPI route, not nginx static.**

- **Choice:** New module `apps/api/app/modules/runbook/router.py` exposing `GET /agent-runbook` as `PlainTextResponse` reading from `/app/static/agent-runbook.md`. Docker `COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md` in `apps/api/Dockerfile`. Edge proxy (`~/repos/configs/nginx/3d-portal.conf`) adds a `location /agent-runbook { proxy_pass http://api; }` rule.
- **Alternatives rejected:**
  - **nginx static file directly**: simple but loses ability to add response headers / conditional logic / version-detection / OpenAPI cross-linking later. Locks the path to a content-type that nginx infers; harder to evolve.
  - **Embedded in Python string**: zero filesystem dependency, but couples markdown edits to Python deploys and balloons module size.
  - **Read from `docs/agents-add-model-runbook.md` at request time (no COPY)**: requires bind-mounting `docs/` into the API container, which conflates source tree with runtime tree. Bad isolation.
- **Rationale:** FastAPI is the consistent surface for everything else under the portal hostname. Static file COPIED into the image guarantees the runbook version-locks with the API deploy — drift between "runbook on disk" and "API endpoints" is impossible by deploy mechanism. Modest cost (~10 lines Python + 1 Dockerfile COPY + 1 nginx pass).
- **Consequence:** When the runbook content updates, the API image must rebuild and redeploy. Acceptable since runbook edits are infrequent compared to API endpoint additions (which Decision E auto-discovers via OpenAPI).

**Decision B: `/agent-runbook` is public read, no auth.**

- **Choice:** No `Depends(current_user)` / `Depends(current_admin)` on the route. Edge proxy passes `/agent-runbook` through without basic-auth challenge (same pattern as `/api/share/*` per `nginx-180/3d-portal.conf`).
- **Alternatives rejected:**
  - **Require admin/agent JWT to read runbook**: paradoxical — the runbook documents how to authenticate. Forcing auth on the doc that teaches auth creates a chicken-and-egg.
  - **Basic auth at nginx layer with shared "household" password**: marginal security gain (sources of leak are the markdown content and the operator giving someone the URL, not network sniffing on LAN) at the cost of extra setup steps in every onboarding.
- **Rationale:** Runbook content reveals: agent token PATH (local filesystem location), endpoint NAMES (already in `/api/openapi.json`), example Printables GraphQL query (Printables-public API). None of these are secrets. The token itself is never in the runbook — it lives on the operator's machine and the runbook tells the agent to read it. Public access matches the runbook's purpose (zero-context bootstrap) and inherits the same trust model as `/api/docs` (Swagger UI is also unauthenticated on this portal).
- **Consequence:** Anyone who knows the portal hostname can see the runbook. Acceptable for a homelab single-tenant deployment; if a future multi-tenant evolution requires tenant-scoped runbooks, this decision is reviewable. Logged as a future trigger.

#### Layered Auto-Discovery Contract

**Decision C: Runbook + OpenAPI are layered, not duplicated.**

- **Choice:** Markdown runbook (`docs/agents-add-model-runbook.md`) carries narrative + behavioral side-effects + external-API recipes only. Endpoint catalog + request/response schemas + status codes live in `/api/openapi.json`, auto-generated by FastAPI from `@router.post/get/...` route signatures and Pydantic models. Cross-link is one explicit pointer at the top of the runbook (`"For endpoint signatures + schemas, fetch /api/openapi.json"`).
- **Alternatives rejected:**
  - **Single comprehensive runbook with every endpoint inline**: drift-prone (every new endpoint requires a markdown edit; markdown lies, OpenAPI tells truth) and grows unboundedly as the API surface expands.
  - **OpenAPI-only (drop runbook entirely)**: OpenAPI cannot express behavioral side-effects (e.g., "first STL upload auto-enqueues render"), agent-execution rules (e.g., "read token inline, never export"), or external-API recipes (Printables GraphQL is not part of the portal's OpenAPI). Agents would have to discover these rules empirically, costing tokens and retries.
- **Rationale:** Native FastAPI + Pydantic auto-generation makes OpenAPI authoritative by construction — drift detection becomes "does the OpenAPI response shape match the actual API behavior", which is enforced by Pydantic validation at request time. Markdown carries only what auto-discovery cannot express. The Initiative-1 retro lesson "every replacement keeps its predecessor as documented manual recovery" generalizes here: OpenAPI is the active mechanism, runbook is the curated context that surrounds it.
- **Consequence:** Codified as NFR8. Smoke-test (FR8) grep-asserts the runbook contains zero occurrences of HTTP-method-uppercase preceding `/api/` paths (catches accidental endpoint duplication). Adding a new endpoint requires zero runbook edit; adding a behavioral rule requires a runbook edit + fingerprint update.

#### Verification & Drift Protection

**Decision D: Runbook fingerprint discipline.**

- **Choice:** Single-source sha256 fingerprint of a stable intro paragraph from the runbook, stored at `infra/.runbook-fingerprint` (single-line, committed). `deploy.sh` (Initiative-1-style verify chain) computes the live `/agent-runbook` response sha256 and compares — mismatch yields a non-fatal stderr warning + `infra/.last-verify-runbook` FAILED marker (same three-signal model as Initiative 1 NFR-R3).
- **Alternatives rejected:**
  - **Full-file sha256**: every minor edit (typo, formatting) invalidates the fingerprint, forcing a "no-op" deploy bump. Noise > signal.
  - **No fingerprint, trust deploy mechanism**: the `COPY` in Dockerfile is robust, but operator-side edits (`docker exec` patches, image overrides) could desync without detection. Belt-and-suspenders matters for an agent-trust contract.
- **Rationale:** Stable intro paragraph is content the runbook never restructures (e.g., the principles section's opening sentence). Editing that paragraph IS a "the runbook contract changed" event, which legitimately requires a fingerprint bump in the same commit. Drift detection cost: one `sha256sum` call in `deploy.sh`. Drift detection benefit: agent never reads a stale runbook against a current API.
- **Consequence:** Runbook edits to the fingerprinted section MUST update `infra/.runbook-fingerprint` in the same commit. Pre-commit hook discipline (not enforced via git hook in MVP; manual discipline; revisit if drift incidents occur).

#### OpenAPI Enrichment

**Decision E: OpenAPI enrichment via FastAPI decorators + Pydantic `json_schema_extra`.**

- **Choice:** Each `@router.post/get/put/patch/delete` in `apps/api/app/modules/{admin,sot}/` adds explicit `summary="..."` (one-line) and `description="..."` (multi-line, includes behavioral side-effects). Endpoints callable by the `agent` role tagged via `tags=["agent-write"]`. Key Pydantic request models (`ModelCreate`, `ModelFilePatch`, `ModelPatch`, etc.) add `model_config = ConfigDict(json_schema_extra={"examples": [...]})` with at least one realistic example.
- **Alternatives rejected:**
  - **External OpenAPI YAML/JSON spec** (e.g., `apps/api/openapi.yaml`): drift-prone (spec lags route implementation); contradicts FastAPI's native auto-generation strength.
  - **Plugin-generated examples** (e.g., dynamic random examples via `polyfactory`): noisy and non-deterministic; agents prefer pinned realistic examples.
  - **Generate examples from existing test fixtures**: clever but couples test data shape to OpenAPI shape; fragile under test refactors.
- **Rationale:** FastAPI's native OpenAPI generator is the source of truth by construction. Pinning examples in `json_schema_extra` is a one-time edit per request model, never goes stale (Pydantic validation enforces shape match with the route handler), and renders directly in Swagger UI + OpenAPI JSON.
- **Consequence:** New route MUST add `summary` + `description` (Pytest in `apps/api/tests/test_openapi_agent_surface.py` enforces). New agent-writable request model MUST add at least one `examples` entry (same Pytest enforces). One mechanical edit per new endpoint; pays back permanently in agent UX.

#### Source-Detection Strategy

**Decision F: Layered source-detection (REST API where exists, browser CLI elsewhere).**

- **Choice:** Per-source recipe documented in runbook source-detection table.
  - `printables.com`: GraphQL `getDownloadLink(id, printId, fileType: stl, source: model_detail)` against `https://api.printables.com/graphql/`. No auth required for public models.
  - `thangs.com`, `thingiverse.com`, `makerworld.com`, `crealitycloud.com`: `agent-browser` CLI against the operator's logged-in Windows-host Chrome (mirrored networking + CDP per `~/.claude/CLAUDE.md` § "Browser automation"). Navigate to URL → click Download → file lands in `D:\` → PowerShell move into a temporary working dir → upload via runbook's existing flow.
- **Alternatives rejected:**
  - **Browser-only for all sources** (uniform path): wastes the existing Printables REST capability; ~10× slower per import.
  - **Implement portal-side scrapers** for the four browser-only sources: enormous scope expansion (each source has captcha + login flow). Defer indefinitely.
  - **Defer non-Printables sources to Vision scope**: too restrictive; Thangs in particular is the operator's secondary source.
- **Rationale:** Printables has a free, undocumented but stable GraphQL surface (used by the legacy `AGENTS.md` runbook for >6 months without breaking). For other sources, the operator already maintains a logged-in browser session on the Windows host for personal use; `agent-browser` leverages that without duplicating credentials or running headless logins.
- **Consequence:** Runbook documents both paths with one worked example each. CLI script (FR9 Growth) can implement Printables natively in Python; browser-source ingestion via CLI is deferred (Growth + Vision; encoding browser-CLI invocation is fragile).

#### CLI Script Architecture (Growth)

**Decision G: CLI is a thin shim over runbook content, not a duplicated source-of-truth.**

- **Choice:** `infra/scripts/add-model-from-url.py` (FR9, Growth) implements the Printables path natively in Python (~150 lines). For source-detection logic (URL host → recipe), the script fetches `/agent-runbook` at startup and parses the source-detection table for the strategy — does NOT hardcode the table. A `--verify-against-runbook` mode computes the script's known table sha256 vs. the runbook's table sha256 to detect drift.
- **Alternatives rejected:**
  - **Hardcoded source-detection table in script**: duplicates runbook content; drift-prone (table edit in markdown won't update script).
  - **Single Python file that both renders the runbook and executes it** (generate markdown from Python data structures): elegant but couples markdown-edit ergonomics to Python-edit ergonomics, friction for human + agent editors.
  - **Skip CLI entirely** (defer to Vision): viable, but the script captures one valuable property — encoded retries, structured progress logging, idempotence check — that ad-hoc runbook execution doesn't enforce. Worth keeping in Growth scope.
- **Rationale:** Script is a Growth-scope convenience, not a substitute for the runbook. Runbook stays primary source; script reuses it for the parts it can encode. Drift between script logic and runbook table is detectable at script startup, not at run-time-failure.
- **Consequence:** Script depends on `/agent-runbook` being reachable; if portal is down, script fails clean with "runbook unreachable" rather than running on stale embedded data. Acceptable trade-off — agent can fall back to manual runbook execution.

#### Legacy Folder Triage

**Decision H: Decision-doc-first pattern for legacy SoT folder triage.**

- **Choice:** FR7 (legacy folder triage) produces a written rationale in `docs/migration-reports/2026-05-XX-legacy-sot-folder-decision.md` BEFORE any executing action (Alembic migration to drop `Model.legacy_id`, or README marker creation freezing scripts). The document captures three required inputs to the decision: (a) last observed `legacy_id` use date (queried from `audit_log`), (b) schema compatibility check of the 4 migration scripts against the current schema (post-Alembic-0008), (c) backup strategy if scripts retire. Decision space is binary: **drop everything** or **freeze with marker**. The doc states which option, why, and what follow-up action is required.
- **Alternatives rejected:**
  - **Execute first, document after**: violates project memory rule `feedback_default_to_bmad_workflow.md` (decisions are durable; ephemeral execution captures lose the "why"). Also matches Initiative 1's retro lesson on documentation discipline.
  - **Single binary decision without input data** ("just drop it / just keep it"): no audit trail; future operator can't reconstruct why the call was made.
  - **Defer the decision indefinitely** (status quo): the gap stays open as the folder accumulates cruft; existing scripts grow stale against schema migrations they never see.
- **Rationale:** This decision is irreversible (Alembic migration dropping a column cannot be cleanly rolled back if a future restore is needed). The rationale document costs ~30 minutes and pays back permanently in audit clarity. Future agents grep'ing migration scripts find the "why" immediately.
- **Consequence:** Codified as NFR4. Execution (Alembic migration OR README marker creation) is a follow-up story gated on the rationale being merged.

### Implementation Patterns & Consistency Rules

**Runbook content guidelines:**

- One H1 (the runbook title), H2 for top-level sections (Principles, Auth, Source Detection, etc.), H3 for sub-sections, code blocks for commands with `bash` language tag (rendering in Swagger UI / markdown viewers).
- Every command example uses the cookie-jar pattern: a one-time `POST /api/auth/login` with the password read inline (`pw=$(cat ~/.config/3d-portal/agent.password); curl -c /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' -d '{"email":"agent@portal.local","password":"'"$pw"'"}' https://3d.ezop.ddns.net/api/auth/login`) followed by `-b /tmp/portal-cookies.txt` on subsequent calls. **Mutations also need `-H 'X-Portal-Client: web'`** (CSRF). NEVER `export PASSWORD=$(...)` (persists in shell history); inline `$(cat ...)` keeps it out of env. NEVER `Authorization: Bearer ...` — admin/agent routes read JWT from the `portal_access` cookie, not from the `Authorization` header.
- Every endpoint reference is `METHOD /api/path` (uppercase method, full path). Cross-link to OpenAPI: `"See \`paths.\"/api/admin/models\".post\` in /api/openapi.json"`.
- External-API recipes (Printables GraphQL) include one worked example with a real public model ID. Examples are pinned to specific models that exist long-term on the source platform.

**FastAPI route conventions (Initiative 2):**

- `@router.post(path, summary="X", description="Multi-line including behavioral side-effects.", tags=["agent-write" if applicable])`.
- Pydantic request models: `model_config = ConfigDict(json_schema_extra={"examples": [{...realistic example...}]})`.
- No schema duplication between OpenAPI and runbook markdown (per Decision C / NFR8).

**Runbook fingerprint workflow:**

- Choose stable intro paragraph (typically: "This runbook teaches an AI agent..." or similar opening). Compute sha256: `sha256sum <(grep -A 5 -F "<stable-marker>" docs/agents-add-model-runbook.md | head -5)`. Store in `infra/.runbook-fingerprint` (single line).
- `deploy.sh` post-deploy chain: `curl https://3d.ezop.ddns.net/agent-runbook | sha256-check vs $(cat infra/.runbook-fingerprint)`. Mismatch → stderr warning (non-fatal) + `infra/.last-verify-runbook` FAILED marker.
- Runbook edit to the fingerprinted paragraph MUST update `infra/.runbook-fingerprint` in the same commit. Failure to do so triggers the verify warning at next deploy.

**Credentials-handling boilerplate (encoded in runbook + CLI):**

- Password path: `~/.config/3d-portal/agent.password` (mode 600, owner `ezop`).
- Default email for the service account: `agent@portal.local` (or whatever email was used at first `bootstrap_agent` run; runbook documents the default and notes that the operator may have customized).
- Login pattern: `pw=$(cat ~/.config/3d-portal/agent.password)` then `POST /api/auth/login` with `{"email":"agent@portal.local","password":"$pw"}` and `X-Portal-Client: web` header, capturing cookies into `/tmp/portal-cookies.txt` (or any out-of-tracked-path location) via `-c`. Subsequent calls reuse via `-b`. CSRF header `X-Portal-Client: web` repeated on every mutation.
- Cookie surfaces: `portal_access` (`Path=/api`, ~30 min TTL, JWT) for admin calls; `portal_refresh` (`Path=/api/auth`, 30-day TTL) for re-issuing access. Long sessions either cron a daily relogin OR `POST /api/auth/refresh` before the access cookie expires (cheaper, no password re-read).
- Never to env var unless in an ephemeral subshell; never echoed; cookie jar inherits the same don't-leak discipline.
- Rotation: `python -m scripts.bootstrap_agent --email agent@portal.local --rotate` on `.190` prints a fresh password to stdout once — capture it, replace the file contents (`chmod 600` preserved). No service restart needed; existing cookies remain valid until their JWT TTL expires.

### Project Structure & Boundaries

**New files / surfaces introduced by Initiative 2:**

| Path | Role | Owner |
|---|---|---|
| `docs/agents-add-model-runbook.md` | Curated agent runbook (narrative + behavioral + external-API recipes) | `docs/` |
| `apps/api/app/modules/runbook/__init__.py` + `router.py` | FastAPI route exposing `/agent-runbook` | `apps/api/` |
| `apps/api/Dockerfile` (modified) | `COPY` runbook markdown into `/app/static/agent-runbook.md` | `apps/api/` |
| `~/repos/configs/nginx/3d-portal.conf` (modified, external repo) | `location /agent-runbook` proxy_pass rule | `~/repos/configs/` |
| `infra/.runbook-fingerprint` | Single-line sha256 of stable intro paragraph | `infra/` |
| `infra/scripts/deploy.sh` (modified) | Append runbook-endpoint verify to verify chain | `infra/scripts/` |
| `apps/api/tests/test_openapi_agent_surface.py` | Pytest enforcing FR11 (summary/description/examples on admin+sot routes) | `apps/api/tests/` |
| `apps/api/app/modules/{admin,sot}/` (modified) | Add `summary` + `description` + `tags` to existing routes; `json_schema_extra` examples on request models | `apps/api/` |
| `docs/migration-reports/2026-05-XX-legacy-sot-folder-decision.md` | Written rationale for FR7 | `docs/` |
| `infra/scripts/add-model-from-url.py` (FR9 Growth, deferable) | Optional CLI shim over runbook | `infra/scripts/` |

**No changes to:**

- `apps/web/` (no UI surface change in Initiative 2).
- `workers/render/` (render trigger unchanged; auto-enqueue-on-first-STL already shipped per Slice 2).
- `apps/api/app/core/` (no auth/db/observability plumbing changes).
- Alembic migrations (no schema change UNLESS Decision H execution chooses "drop `Model.legacy_id`"; that migration would be a follow-up story).

### Architecture Validation Results

**Validation Checklist (Initiative 2):**

| Check | Status |
|---|---|
| Every FR mapped to at least one architectural decision | ✅ (FR1–4 → A,C,D; FR5 → token boilerplate; FR6 → patterns; FR7 → H; FR8 → D + Pytest; FR9 → G; FR10 → A,B; FR11 → E) |
| Every NFR has an enforcing mechanism | ✅ (NFR1 → pull-only design; NFR2 → token-handling boilerplate; NFR3 → FR8 gate; NFR4 → H; NFR5 → runbook lints; NFR6 → FR6.4 dedup; NFR7 → D; NFR8 → C + smoke-test grep) |
| Decisions are independent OR explicitly dependent | ✅ (A,B independent; C depends on E; D depends on A; F independent; G depends on A + C; H independent) |
| No silent assumption about Initiative 1 surfaces | ✅ (explicit reuse list under "Project Context Analysis"; Initiative 1's `verify-symbolication.sh` and `glitchtip-triage.sh` are NOT in Initiative 2 scope) |
| Decisions don't violate project-context rules | ✅ (no `os.environ` direct reads, no `Depends()` default-arg style, no nginx config in this repo without sync to `~/repos/configs/`) |

### Implementation Handoff

**AI Agent Guidelines (Initiative 2):**

- Read `prd.md` § "Initiative 2" + this section (architecture § "Initiative 2") + product-brief-distillate before implementing any FR.
- Follow Decisions A–H exactly. Alternatives are documented for context, not for re-evaluation at story time.
- Use Implementation Patterns (Initiative 2 subsection) as the consistency contract — runbook style, FastAPI decorators, fingerprint workflow, token-handling.
- Story execution order: foundation first (runbook content + endpoint + Dockerfile + nginx — Decisions A + B), then OpenAPI enrichment (Decision E), then fingerprint + deploy verify (Decision D), then pre-flight checklist + idempotence (FR6 + NFR6), then legacy folder triage (FR7 + Decision H), then end-to-end smoke-test acceptance (FR8). CLI script (FR9) is Growth — deferable.

**First Implementation Priority:**

Runbook content (`docs/agents-add-model-runbook.md`) — port from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` § "Adding a New Model" + § "Downloading from Printables" + § "3MF Conversion Workflow", reframe for DB-era endpoints, add agent-token + pre-flight checklist. Once content exists, Decision A delivery (FastAPI route + Dockerfile COPY + nginx rule) and Decision D fingerprint are mechanical.

## Initiative 3 — UI Theme Compliance & Visual Regression Hardening

**Status:** ✅ shipped 2026-05-13 (started 2026-05-13, single-session autonomous). Project mode: brownfield — frontend remediation+prevention layered on the 2026-05-12 post-TB-012 baseline (visual-regression 90 passed / 0 failed / 14 skips). Source-of-truth for capability contract: `prd.md` § "Initiative 3" (17 FRs, 9 NFRs). Decisions A–J below in-scope (numbering is initiative-local; Initiative 1's A–L and Initiative 2's A–H do not conflict). Decisions K–M were explicitly deferred at Epic 5 retro — all leave-deferred (re-eval 2026-06-13 per retro action item).

### Project Context Analysis

**Requirements Overview (Initiative 3):**

- **A. Audit (FR1–FR3)** — three read-only inventories: color-literal sweep + token-reader inventory, baseline integrity audit + 14-skip disposition, interactive-surface coverage matrix.
- **B. Tooling-early (FR4–FR6)** — in-repo ESLint `no-restricted-syntax` rule banning color literals, token-file split + Stylelint with per-file overrides, `@axe-core/playwright` contrast scan scoped to `runOnly: ['color-contrast']`.
- **C. Remediation (FR7–FR12)** — dialog/overlay tokenization with new `--color-overlay` token, viewer-overlay tokenization with new `--color-viewer-tooltip` token, dark-mode override completeness, bulk fix, baseline regeneration with operator sign-off, open-state spec expansion sub-split per primitive.
- **D. Prevention (FR13–FR17)** — git pre-commit hook for baseline acceptance, visual coverage contract enforcement, two new project-context.md rules, Codex review prompt enrichment, axe scan promotion to fail level.

**Non-Functional Posture:**

- Lint-green-build merge contract (NFR1) — `npm run lint --max-warnings=0` chains ESLint + Stylelint.
- Stylelint scoped per-file overrides (NFR2) — preserves the intentional mixed-notation design between `theme.css` (modern HSL for browser) and `viewer-tokens.css` (legacy HSL for three.js).
- Convention-only enforcement explicitly rejected (NFR3) — every Phase-D rule paired with a tooling defense.
- Operator eye-review time budget acknowledged in workflow (NFR4) — ≤20 PNGs / ≤2 sessions per day; sampling fallback documented.
- No SaaS adoption (NFR5) — local Playwright + git hook + operator sign-off; no Chromatic/Percy/Argos.
- No Storybook adoption (NFR6) — numerical LOC comparison documented.
- English in committed file content (NFR7) — Polish conversational only.
- `_bmad-output/` stays gitignored (NFR8) — all initiative artifacts operator-local.
- Single-operator workflow constraint (NFR9) — all gates observable on operator's machine.

**Existing Surfaces Reused (no rewrite required):**

- `apps/web/src/styles/theme.css` — `@theme {}` block stays in place; 4 viewer tokens move out to a sibling file (Decision B), 19 base tokens stay; `.dark {}` block gains 3 overrides for success/warning/destructive (FR9).
- `apps/web/eslint.config.js` — existing ESLint 9 flat config extended with one new `no-restricted-syntax` rule entry (Decision C); existing structure (`tseslint.configs.recommended` + `react.configs.flat.recommended` + the existing `/api/files|catalog/` ban) preserved.
- `apps/web/tests/visual/playwright.config.ts` — existing 4-project matrix (desktop/mobile × light/dark) reused; axe scan added as a sibling spec (Decision H).
- `infra/scripts/deploy.sh` — auto-deploy chain unchanged; lint failures already block via existing pre-deploy `npm run lint` step.
- `_bmad-output/project-context.md` — extended with 2 new rules (FR15), `rule_count` 134 → 136; rule format unchanged.
- `.codex/` directory — created if absent; review-prompt artifact lives there per Decision J.

### Starter Template Evaluation

**Status:** N/A. Brownfield remediation; all new code paths layer on existing modules. No template, no scaffolding step.

### Core Architectural Decisions

#### Decision Priority Analysis (Initiative 3)

**Critical Decisions (Block Implementation):**

1. Overlay token surface — new `--color-overlay` + `--color-overlay-foreground` tokens (Decision A; drives FR7)
2. Token-file split for Stylelint compatibility — `viewer-tokens.css` extracted (Decision B; drives FR5)
3. Primary lint enforcement layer — in-repo ESLint `no-restricted-syntax` is critical path, `@poupe` plugin is optional enhancement (Decision C; drives FR4)
4. Stylelint integration in `npm run lint` script chain (Decision D; drives FR5 + NFR1)
5. Baseline acceptance enforcement via git pre-commit hook, not convention (Decision E; drives FR13)

**Important Decisions (Shape Architecture):**

6. Hook tooling choice — `husky` ≥9 (Decision F; drives FR13/FR14 implementation pattern)
7. Visual Coverage Contract enforcement (FR14) — extend the FR13 hook (single shell script, two checks) rather than add a parallel ESLint custom rule (Decision G)
8. Axe scan invocation pattern — dedicated `tests/visual/accessibility-axe.spec.ts` running per project, not per-page-spec axe call (Decision H)
9. Axe per-test escape hatches — `disableRules('color-contrast')` opt-out for known-noisy nodes (Decision I)
10. Codex prompt enrichment delivery — single artifact at `.codex/review-prompts/ui-theme-checks.md` + wrapper script `.codex/bin/review-ui-commit` that detects UI commits via path-pattern heuristic (Decision J)

**Deferred Decisions (Post-Epic-5, gated):**

- **K.** Move three.js consumers off CSSOM parsing to build-time generated `viewer-tokens.ts` TS constants — most-robust path against the CSS-parser-mismatch incident class. Gated: Epic 5 retro decision; revisit if another parser-mismatch incident occurs within 90 days post-Epic-5 close OR if `viewer-tokens.css` accumulates ≥3 additional `--color-viewer-*` tokens.
- **L.** Recurring monthly baseline audit codified as a scheduled BMAD chore — informal first; gated on whether the FR13 first-pass enforcement test (≥3 commits with `baseline-reviewed:` in 30 days) is exceeded by an order of magnitude (would indicate higher baseline churn requiring scheduled audit).
- **M.** Selector-policy lint rule (PL-locale enforcement on `tests/visual/*.spec.ts` `getByRole({name:...})` regexes) — gated on Phase A coverage matrix output revealing ≥3 EN-only-regex violations beyond what TB-009's selector-fix policy already addressed.

#### Token Taxonomy

**Decision A: New `--color-overlay` + `--color-overlay-foreground` tokens.**

- **Choice:** Add `--color-overlay: hsl(222 47% 11% / 0.5)` (light mode — modern HSL with alpha) and `--color-overlay-foreground: hsl(210 40% 98%)` to `@theme {}` in `theme.css`. `.dark` overrides `--color-overlay: hsl(0 0% 0% / 0.5)` (darker theme already has dark backdrops). `DialogContent` and `SheetContent` consume via `bg-overlay text-overlay-foreground`; `DialogOverlay` and `SheetOverlay` use `bg-overlay/40` opacity modifier or a separate `--color-overlay-backdrop` token (decided during FR7 implementation — both options validated).
- **Alternatives rejected:**
  - **Reuse `bg-background/N` opacity modifier** (token-reuse, no new token): viable for `DialogContent` (where overlay = bg-color with transparency) but semantically wrong — `--color-background` is the page surface; reusing it for translucent overlays couples two unrelated concerns. First semantic drift incident in the design system.
  - **No new token; harden via documented-but-uncodified pattern of `bg-popover/N`**: `--color-popover` is the popover surface (consumed by `dropdown-menu` + `select`); semantically wrong for dialogs and sheets. The whole point of Initiative 3 is to stop semantic drift.
- **Rationale:** Overlay is a distinct semantic surface (translucent layer above content). It deserves its own token. The token cost is minimal (1 light + 1 dark declaration, plus the foreground sibling). Adding it now prevents the next agent from reaching for `bg-background/N` or another mis-fit token when adding the next dialog-like primitive.
- **Consequence:** `theme.css` gains 2 tokens; `.dark {}` gains 2 overrides. Tailwind class surface gains `bg-overlay`, `text-overlay-foreground`, `bg-overlay/<modifier>` for opacity tweaks. FR7 implementation pattern: `bg-overlay text-overlay-foreground` on `DialogContent`/`SheetContent`; `bg-overlay/40` on the corresponding overlay backdrop.

**Decision B: Token-file split — `viewer-tokens.css` extracted from `theme.css`.**

- **Choice:** Create `apps/web/src/styles/viewer-tokens.css` containing the 4 `--color-viewer-*` declarations (`viewer-mesh-paint`, `viewer-mesh-edge`, `viewer-grid`, `viewer-measure`) + their `.dark` overrides + the 7-line three.js-parse-constraint comment block (currently lines 27–33 of `theme.css`). `theme.css` imports it via `@import "./viewer-tokens.css";` after the tailwindcss + tw-animate-css imports. A new `--color-viewer-tooltip` token (introduced by FR8) also lives in this file.
- **Alternatives rejected:**
  - **Keep tokens together in `theme.css`** + custom Stylelint rule targeting only `--color-viewer-*` declarations: more complex Stylelint config, no off-the-shelf rule supports per-declaration notation pinning. The file split is the simpler mechanism with zero custom rule maintenance.
  - **Compile-time generation of `viewer-tokens.css` from a JSON/TS source**: over-engineered for 4–5 tokens. Revisit in Decision K (TS constants) if motivation shifts.
  - **Single CSS file with `stylelint-disable-next-line` annotations on viewer tokens**: theatre — operator silences the rule instead of authoring it. Same anti-pattern Initiative 3 is built to eliminate.
- **Rationale:** Stylelint's `color-function-notation` rule is file-wide. The intentional mixed-notation design (modern for browser tokens, legacy comma-form for three.js Color compatibility per `feedback_threejs_hsl_parsing.md`) cannot be expressed via in-file overrides. File split is the simplest mechanism. `viewer-tokens.css` becomes the contract surface for "any token consumed by a non-browser CSS parser"; future additions to that file inherit the comma-form pin automatically.
- **Consequence:** Two CSS source files; Stylelint config has per-file `color-function-notation` overrides (`theme.css` → `'modern'`, `viewer-tokens.css` → `'legacy'`). `palette.ts:10` and `readMeshTokens.ts` reader paths unchanged — `getComputedStyle().getPropertyValue('--color-viewer-*')` still returns the same value; only the source-file location changed.

#### Lint Enforcement

**Decision C: In-repo ESLint `no-restricted-syntax` is the critical path; `@poupe` plugin is optional enhancement.**

- **Choice:** Add a new entry to the existing `no-restricted-syntax` rule in `apps/web/eslint.config.js` (currently bans `/api/files|catalog/` literals). The new pattern matches color literals in JSX `className` attributes:
  ```js
  {
    selector: "JSXAttribute[name.name='className'] Literal[value=/(?:^|\\s)(?:bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\\[(?:#|rgb|hsl|oklch|color\\()/]",
    message: "Color literals in className are forbidden — use a theme token (bg-card, text-foreground, etc.) or add a new --color-* token in theme.css. See _bmad-output/project-context.md § Theme system."
  }
  ```
  Tiered via `overrides` block: `error` for files matching `apps/web/src/ui/**/*.tsx`, `warn` for the rest of `apps/web/src/**/*.tsx`. Plus a similar pattern banning raw palette utilities (`bg-zinc-N`, `bg-red-N`, `text-white`, etc.) — also tiered.
  Optional layer at `warn` for `apps/web/src/**`: `@poupe/eslint-plugin-tailwindcss` with `prefer-theme-tokens` + `no-arbitrary-value-overuse` rules. Wired via `package.json` devDep + `eslint.config.js` plugin import.
- **Alternatives rejected:**
  - **`oxlint-tailwindcss` as second linter** (alongside ESLint): faster, but dual-toolchain. Violates single-linter discipline established by the rest of the project's `lint` script.
  - **`francoismassart/eslint-plugin-tailwindcss`**: only partial Tailwind v4 support (beta channel). `@poupe` is v4-first.
  - **Custom ESLint plugin in a separate package**: over-engineered for one rule. `no-restricted-syntax` is the right primitive.
  - **`@poupe` as critical path**: pre-1.0 (v0.3.1, 2026-04-07), single-maintainer. If it goes silent the build breaks. In-repo rule first, plugin as enhancement.
- **Rationale:** In-repo rule is zero-dependency, deterministic, and survives plugin abandonment. Carries ≥80% of the value: the lint catches `bg-[rgba(...)`, `bg-[#abc]`, `text-[hsl(...)]`, raw palette utilities. The `@poupe` plugin's `prefer-theme-tokens` adds semantic awareness (knows which tokens exist, not just regex matching), worth keeping as an additive `warn` layer for the rest of the codebase.
- **Consequence:** Build (`npm run lint --max-warnings=0`) fails on any new color literal in `apps/web/src/ui/**`. Existing `_bmad-output/project-context.md` rule "No inline hex colors anywhere in .tsx/.ts" gets a tooling counterpart (was convention-only before).

**Decision D: Stylelint integration via `npm run lint` script chain.**

- **Choice:** `apps/web/package.json` `lint` script: `"lint": "eslint . --max-warnings=0 && stylelint \"src/styles/*.css\""`. New devDep: `stylelint` ≥16 + `stylelint-config-standard` + `stylelint-color-no-non-variables`. Config file `apps/web/.stylelintrc.json`:
  ```json
  {
    "extends": ["stylelint-config-standard"],
    "plugins": ["stylelint-color-no-non-variables"],
    "rules": {
      "color-no-hex": true,
      "color-no-non-variables/color-no-non-variables": [true, { "ignore": ["named"] }]
    },
    "overrides": [
      { "files": ["**/theme.css"], "rules": { "color-function-notation": "modern" } },
      { "files": ["**/viewer-tokens.css"], "rules": { "color-function-notation": "legacy" } }
    ]
  }
  ```
- **Alternatives rejected:**
  - **Single ESLint plugin orchestrating Stylelint** (e.g., `eslint-plugin-stylelint`): adds AST-level integration cost for marginal ergonomic win. Two CLIs chained is the simpler default.
  - **Pre-commit-only Stylelint** (via husky, not in `lint` script): bypasses CI / agent-driven verification. `lint` script is the contract — must include both linters.
  - **File-wide `color-function-notation` pin on the entire project**: would force comma form on browser tokens or modern form on viewer tokens — the exact problem Decision B avoids.
- **Rationale:** Two CLIs chained via `&&` is universally understood and matches how `lint` is already structured in solo-operator JS repos. Per-file overrides via Stylelint native config are first-class — no plugin gymnastics. Failure of either step fails the merge contract.
- **Consequence:** `npm run lint` runs both linters in sequence. CI/auto-deploy chain (`infra/scripts/deploy.sh` step that runs `npm run lint`) inherits this without change. New devDep + config file; minimal footprint.

#### Visual Quality Gates

**Decision E: Baseline acceptance via git pre-commit hook (NOT commit-message convention).**

- **Choice:** New file `apps/web/.husky/pre-commit` (per Decision F) runs a Node/bash script that:
  1. Collects staged file paths matching `apps/web/tests/visual/__snapshots__/**/*.png` via `git diff --cached --name-only --diff-filter=AM`.
  2. If zero matches: exit 0 (commit allowed; no baseline change).
  3. If matches present: read the in-flight commit message from `.git/COMMIT_EDITMSG`. For each changed PNG basename, require a line matching `^baseline-reviewed: <basename>, <reviewer>, \d{4}-\d{2}-\d{2}$` in the message. Reject otherwise with a clear error pointing at the missing basename(s).
- **Alternatives rejected:**
  - **Commit-message convention without hook enforcement**: the original v1 brief proposal. Rejected during adversarial review — the 2026-05-10 UI-review retro documented that conventions get bypassed. Tooling-enforced or it doesn't count.
  - **Server-side `pre-receive` hook** (would catch even bypass of local hooks): no remote server in scope; portal repo lives on `.190` with no shared bare repo. Local pre-commit is the right layer.
  - **GitHub Actions check** (cloud CI): no GitHub Actions on this homelab repo today; adopting CI is out of Initiative 3 scope (NFR9).
- **Rationale:** The whole problem class is "conventions bypassed under load". A pre-commit hook is the lightest mechanism that turns the convention into a contract. Cost: ~30 lines of shell or 20 lines of Node. Bypass requires `--no-verify`, which is documented and observable in `git reflog`.
- **Consequence:** Every commit touching `apps/web/tests/visual/__snapshots__/**` requires a `baseline-reviewed:` line per changed PNG. Workflow: operator runs `npx playwright test --update-snapshots --grep <spec>`, opens the Playwright HTML report at 100% zoom, verifies each new PNG is intentional, writes the commit message with one `baseline-reviewed:` line per PNG, commits. The hook validates and either accepts or rejects.

**Decision F: Hook tooling — `husky` ≥9.**

- **Choice:** Adopt `husky` ≥9 as devDep. `npx husky init` creates `.husky/` directory and registers the prepare script. `apps/web/.husky/pre-commit` is a shell script that delegates to a Node helper `apps/web/.husky/_check-baseline-review.mjs` for the parsing logic.
- **Alternatives rejected:**
  - **Hand-rolled `.git/hooks/pre-commit` shell script (no devDep)**: lighter, but `.git/hooks/` is not committed to the repo by default — every clone needs manual setup. Husky's whole value-prop is "hook config that ships with the repo".
  - **`pre-commit` framework** (Python-based): adds Python toolchain dependency to a JS-only frontend directory. Husky is JS-native.
  - **`lefthook`**: viable Go alternative; minor ergonomic differences. Husky is the JS-ecosystem default with widest tutorial / debugging coverage.
- **Rationale:** Husky 9 is the JS-frontend standard. Operator already uses npm scripts and devDeps extensively (Vitest, Playwright, ESLint, Prettier). Adding husky is one devDep + one `prepare` script. Zero novel cognitive load.
- **Consequence:** `apps/web/package.json` gains `husky` ≥9 devDep + `"prepare": "husky"` script. `.husky/` directory committed. First `npm install` post-merge wires the hooks. Operator workflow inherits hook checks transparently.

**Decision G: Visual Coverage Contract enforcement (FR14) — extend the FR13 hook.**

- **Choice:** Same `apps/web/.husky/pre-commit` script gains a second check: collect staged new files matching `apps/web/src/ui/*.tsx` via `git diff --cached --name-only --diff-filter=A` (added-only). For each new file (basename without `.tsx`), require a matching staged test file at `apps/web/tests/visual/<basename>.spec.ts` or `apps/web/tests/visual/<basename>-*.spec.ts`. Reject otherwise.
- **Alternatives rejected:**
  - **Separate ESLint custom rule** ("when a new file is added under `apps/web/src/ui/`, require a matching spec"): ESLint doesn't naturally see "what files are staged in this commit" — it operates on the file under lint, not on the commit's file-set. Hook is the right level.
  - **Parallel pre-commit hook script**: two scripts, twice the orchestration. One script with two checks is simpler.
  - **Defer enforcement to manual code review**: same convention-vs-tooling problem Decision E is built to solve.
- **Rationale:** Both FR13 and FR14 are commit-shape checks. Putting both in the same hook keeps the developer-feedback loop in one place: one error message at commit time covers both contracts.
- **Consequence:** Pre-commit hook has two responsibilities; documented in its header comment. Test: adding `apps/web/src/ui/new-primitive.tsx` to a commit without a matching spec is rejected.

#### Axe Contrast Scan

**Decision H: Dedicated axe spec — `tests/visual/accessibility-axe.spec.ts`.**

- **Choice:** New spec file `apps/web/tests/visual/accessibility-axe.spec.ts` runs once per Playwright project (desktop-light, desktop-dark, mobile-light, mobile-dark). For each project: navigate to a curated set of representative pages (`/`, `/catalog`, `/admin/models`, `/admin/tags`, `/admin/categories`, plus one model-detail page), run `await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()`, assert `violations.length === 0` (post-FR17 promotion) or just log violations (pre-promotion, FR6 state).
- **Alternatives rejected:**
  - **Per-existing-spec axe call** (every visual spec also runs axe at the end): scattered config; harder to evolve; couples a11y concerns to visual-regression concerns at the test level.
  - **Dedicated separate project** in `playwright.config.ts`: viable, but adds a `npm run test:a11y` script. The dedicated-spec-in-existing-projects pattern reuses the existing 4-project matrix unchanged.
  - **Standalone CI step outside Playwright**: viable for pa11y / Lighthouse-CI but adds a new toolchain. Reusing Playwright keeps the matrix coherent.
- **Rationale:** One file, one concern, one set of curated pages. Easy to evolve (add a page = one line). Runs in parallel with existing visual specs under the same 4-project sharding.
- **Consequence:** `tests/visual/accessibility-axe.spec.ts` added; `@axe-core/playwright` added as devDep. `npm run test:visual` runs axe automatically as part of the existing matrix.

**Decision I: Per-test escape hatches via `disableRules('color-contrast')`.**

- **Choice:** Known-noisy nodes (overlapping z-index, disabled controls, custom-tooltip combos) opt out via `await new AxeBuilder({ page }).withRules(['color-contrast']).exclude('.viewer3d-overlay-stack').analyze()` or similar. The exclude-list is documented in the spec file header and grows only via Phase B / Phase C-prevention work where a real exclusion is justified.
- **Alternatives rejected:**
  - **Globally `disableRules('color-contrast')` per-spec**: defeats the purpose.
  - **No escape hatch at all**: forces every false-positive to be remediated, which is fine in theory but generates remediation work outside Initiative 3 scope. Pragmatic exclude-list is the right balance for solo-operator throughput.
- **Rationale:** Axe color-contrast has documented false-positive modes (overlapping nodes, disabled controls). An exclude-list with explicit justification per entry is the standard mitigation.
- **Consequence:** Spec header documents the exclude policy; FR17 promotion gates on the exclude-list being short and justified, not zero.

#### Codex Review Prompt Enrichment

**Decision J: Single artifact `.codex/review-prompts/ui-theme-checks.md` + wrapper script for UI-commit detection.**

- **Choice:** Create `.codex/review-prompts/ui-theme-checks.md` (committed; explicitly NOT under `_bmad-output/`) — a prompt fragment instructing Codex to check (a) color literals in `apps/web/src/ui/**`, (b) `.dark {}` override completeness for any new `--color-*`, (c) open-state visual spec coverage for any new `apps/web/src/ui/*.tsx`, (d) selector locale-awareness in any new `apps/web/tests/visual/*.spec.ts`. Wrapper script `.codex/bin/review-ui-commit` (executable shell) detects UI commits via `git diff --name-only HEAD~1..HEAD | grep -E "^apps/web/(src/(ui|styles|modules/.*/components)|tests/visual)/" -q`; if matched, runs `cat .codex/review-prompts/ui-theme-checks.md .codex/review-prompts/_tail.md | codex exec -`; if not matched, runs bare `codex review --commit <SHA>`.
- **Alternatives rejected:**
  - **Inline the prompt in a memory file**: harder to version, harder to test against historical commits.
  - **Always use the enriched prompt for every commit**: floods non-UI reviews with irrelevant checks; degrades signal.
  - **Manual operator invocation choice**: removes the automation that's the whole point of Initiative 3's prevention layer.
- **Rationale:** Concrete file path + concrete invocation pattern. Acceptance test (replay against commit `10bc3de`) is mechanical, not aspirational. Detection heuristic is conservative — false positives (running enriched prompt on a non-UI commit) cost a few tokens; false negatives (missing a UI commit) miss the value.
- **Consequence:** `.codex/` directory committed (creates if absent); two new files (prompt + wrapper); no existing Codex workflow changes (bare `codex review` still works for direct invocation). Operator's existing `codex review` muscle memory unchanged; the wrapper is invoked when the operator switches to the enriched mode (or wires it into a per-commit reflex post-Epic-5).

### Implementation Patterns & Consistency Rules

**Token authoring discipline:**

- Every new `--color-*` token added to `@theme {}` in `theme.css` MUST have a matching `.dark` override declared in the same commit. Failure logged as a violation candidate for project-context.md rule extension (currently captured in NFR3 enforcement; mechanical lint rule deferred to architecture follow-up).
- Tokens consumed by non-browser CSS parsers (currently: three.js Color via `readMeshTokens.ts`/`palette.ts`) MUST live in `viewer-tokens.css` (legacy comma-form HSL). Tokens consumed only by the browser MUST live in `theme.css` (modern syntax). Mixing within either file is forbidden by Stylelint per-file overrides (Decision D).
- Opacity modifiers on token classes (`bg-overlay/40`) are preferred over hardcoded translucency (`bg-[rgba(...)]`). Test before introducing a new token-with-alpha vs token + opacity modifier — the latter is more reusable.

**Lint rule extension pattern:**

- New `no-restricted-syntax` patterns extend the existing entry in `apps/web/eslint.config.js` rather than introducing parallel rules. Tiered (error in `ui/**`, warn elsewhere) via `overrides`.
- Stylelint rule changes go in `apps/web/.stylelintrc.json` with per-file overrides where the rule conflicts with intentional design (Decision B).

**Hook script discipline:**

- `apps/web/.husky/pre-commit` is a shell wrapper that delegates to Node helpers under `apps/web/.husky/_*.mjs` (underscore prefix marks them as private). Husky 9 best-practice is shell-thin + Node-heavy for any parsing logic.
- Hook scripts MUST run in <1s on the operator's machine. PNG-list collection is O(staged-files); commit-message parsing is O(message-length). Both well under budget.
- Hook scripts MUST exit non-zero with a single clear error line on failure; never silent.

**Axe scan discipline:**

- `withRules(['color-contrast'])` is the minimal scope. Broader axe rule packs are out of Initiative 3 scope (NFR8 — broader a11y is a separate future initiative).
- Exclude-list entries (`exclude('.selector')`) MUST carry a one-line comment in the spec file justifying the exclusion.
- FR17 promotion gates on the exclude-list being short and justified, not zero.

**Codex prompt artifact discipline:**

- `.codex/review-prompts/ui-theme-checks.md` is committed and visible. Updates to the prompt are commit-reviewable.
- The wrapper script `.codex/bin/review-ui-commit` is the single invocation entry point; bare `codex review` remains available for direct use.
- Acceptance criterion for any prompt change: replay against commit `10bc3de` MUST still surface at least one of the two TB-010 defects (black-mesh OR overlap).

### Project Structure & Boundaries

**New files / surfaces introduced by Initiative 3:**

| Path | Role | Owner |
|---|---|---|
| `apps/web/src/styles/viewer-tokens.css` | Three.js-compatible legacy-HSL token declarations (extracted from `theme.css`) | `apps/web/src/styles/` |
| `apps/web/src/styles/theme.css` (modified) | Imports `viewer-tokens.css`; adds `--color-overlay` + `--color-overlay-foreground` + `.dark` overrides; adds missing `.dark` overrides for success/warning/destructive | `apps/web/src/styles/` |
| `apps/web/src/ui/dialog.tsx` (modified) | Replace hardcoded RGBA at :34 + :56 with `bg-overlay`/`bg-overlay/40` token classes | `apps/web/src/ui/` |
| `apps/web/src/ui/sheet.tsx` (modified) | Replace hardcoded RGBA at :29 with `bg-overlay/40` token class | `apps/web/src/ui/` |
| `apps/web/src/modules/catalog/components/viewer3d/measure/{RimOverlay,MeasureOverlay}.tsx` (modified) | Replace raw palette utilities with new `bg-viewer-tooltip` token classes | `apps/web/src/modules/catalog/` |
| `apps/web/eslint.config.js` (modified) | Extended `no-restricted-syntax` rule banning color literals + raw palette utilities, tiered error/warn via overrides | `apps/web/` |
| `apps/web/.stylelintrc.json` | New Stylelint config with per-file `color-function-notation` overrides | `apps/web/` |
| `apps/web/package.json` (modified) | `lint` script chains ESLint + Stylelint; new devDeps: `stylelint`, `stylelint-config-standard`, `stylelint-color-no-non-variables`, `husky`, `@axe-core/playwright`, optional `@poupe/eslint-plugin-tailwindcss` | `apps/web/` |
| `apps/web/.husky/pre-commit` | Shell wrapper delegating to Node helpers for FR13 + FR14 checks | `apps/web/.husky/` |
| `apps/web/.husky/_check-baseline-review.mjs` | Node helper parsing staged PNGs vs commit-message `baseline-reviewed:` lines | `apps/web/.husky/` |
| `apps/web/.husky/_check-visual-coverage.mjs` | Node helper enforcing FR14 (new `ui/*.tsx` requires matching spec) | `apps/web/.husky/` |
| `apps/web/tests/visual/accessibility-axe.spec.ts` | Dedicated axe `color-contrast` scan spec across the 4-project matrix | `apps/web/tests/visual/` |
| `apps/web/tests/visual/<8 new spec files>` (per FR12 sub-split) | Open-state Playwright specs for Select, ConfirmDialog/EditSheets, Tooltip+UserMenu, RenderSheet/AddPrintSheet/AddNoteSheet/FilterRibbon | `apps/web/tests/visual/` |
| `apps/web/tests/visual/__snapshots__/<~32 new PNGs>` | Open-state baselines × 4 projects, each with `baseline-reviewed:` sign-off | `apps/web/tests/visual/__snapshots__/` |
| `.codex/review-prompts/ui-theme-checks.md` | Codex prompt fragment for UI commits | `.codex/` |
| `.codex/review-prompts/_tail.md` | Shared trailing context for Codex `exec -` invocations | `.codex/` |
| `.codex/bin/review-ui-commit` | Wrapper script detecting UI commits + invoking enriched Codex prompt | `.codex/bin/` |
| `_bmad-output/project-context.md` (modified) | Add 2 rules (Baseline Acceptance Gate + Visual Coverage Contract); rule_count 134 → 136 | `_bmad-output/` |
| `_bmad-output/implementation-artifacts/theme-token-violations-2026-05-XX.md` | FR1 output (Phase A audit) | `_bmad-output/implementation-artifacts/` |
| `_bmad-output/implementation-artifacts/token-reader-inventory-2026-05-XX.md` | FR1 output (Phase A audit) | `_bmad-output/implementation-artifacts/` |
| `_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-XX.md` | FR2 output (Phase A audit + 14-skip disposition) | `_bmad-output/implementation-artifacts/` |
| `_bmad-output/implementation-artifacts/interactive-surface-coverage-matrix-2026-05-XX.md` | FR3 output (Phase A audit) | `_bmad-output/implementation-artifacts/` |

**No changes to:**

- `apps/api/` (backend untouched; Initiative 3 is frontend-only per scope).
- `workers/render/` (worker untouched).
- `infra/scripts/deploy.sh` (auto-deploy unchanged; existing `npm run lint` pre-deploy step inherits the new chained linters automatically).
- `infra/scripts/verify-symbolication.sh` (unchanged; visual-regression has its own gate path).
- Alembic migrations (no DB schema change).
- `apps/web/vite.config.ts` / `vitest.config.ts` / `tsconfig.json` (no build-config changes; lint and test changes are config-additive within their existing files).

### Architecture Validation Results

**Validation Checklist (Initiative 3):**

| Check | Status |
|---|---|
| Every FR mapped to at least one architectural decision | ✅ (FR1–FR3 → audit ops, no decision needed; FR4 → C; FR5 → B + D; FR6 → H + I; FR7 → A; FR8 → A + B; FR9 → token authoring discipline; FR10 → C; FR11 → E + F; FR12 → H + G; FR13 → E + F; FR14 → F + G; FR15 → no decision (operator-authored); FR16 → J; FR17 → H + I) |
| Every NFR has an enforcing mechanism | ✅ (NFR1 → D `lint` script chain; NFR2 → B + D per-file overrides; NFR3 → E/F/G hook + C/D lint; NFR4 → FR2 batching encoded in story acceptance; NFR5 → "no SaaS" embedded in J + H; NFR6 → no Storybook adoption surface; NFR7 → operator discipline; NFR8 → gitignore inherited; NFR9 → all decisions stay local-machine-observable) |
| Decisions are independent OR explicitly dependent | ✅ (A independent; B independent; C independent; D depends on B + Stylelint adoption; E independent; F is enabling tech for E + G; G depends on F; H independent; I depends on H; J independent) |
| No silent assumption about Initiative 1 + 2 surfaces | ✅ (frontend-only; no overlap with Initiative 1 verify-symbolication / triage-script or Initiative 2 runbook/OpenAPI/agent-token surfaces) |
| Decisions don't violate project-context rules | ✅ (no new colors in `.tsx`; new tokens via `@theme {}`; ESLint must pass `--max-warnings=0`; vitest globals=false + setup file pattern preserved; no `vi.mock("@/lib/api")` — visual specs use fetch-level stubs per existing pattern) |

### Implementation Handoff

**AI Agent Guidelines (Initiative 3):**

- Read `prd.md` § "Initiative 3" + this section (architecture § "Initiative 3") + both product-brief artifacts before implementing any FR.
- Follow Decisions A–J exactly. Alternatives are documented for context, not for re-evaluation at story time. Decisions K–M are explicitly deferred — do not re-litigate during Epic 5; surface at Epic 5 retro.
- Use Implementation Patterns (Initiative 3 subsection) as the consistency contract — token authoring, lint extension, hook discipline, axe scope, Codex prompt artifact.
- Story execution order (enforced by Epic 5 dependency graph in `epics.md`):
  1. **Phase A audit (5.1, 5.2, 5.3)** — parallel; produces three reports in `_bmad-output/implementation-artifacts/`. No source changes.
  2. **Phase C-early tooling (5.4, 5.5, 5.6)** — ESLint rule + token split + Stylelint + axe-warn. Lands BEFORE remediation so violations show up in CI during the fix work.
  3. **Phase C-prevention hook (5.13)** — must land BEFORE baseline regen (5.11) so regen commits pass through the gate. Husky setup + check scripts.
  4. **Phase B remediation source changes (5.7, 5.8, 5.9, 5.10)** — token-class swaps validated by the now-live lint rule.
  5. **Phase B baseline regen (5.11)** — every regenerated PNG goes through the FR13 hook.
  6. **Phase B coverage expansion (5.12)** — open-state specs + new baselines, also through the hook.
  7. **Phase C-prevention finalization (5.14, 5.15, 5.16, 5.17)** — coverage contract enforcement, project-context rules, Codex prompt, axe promotion. 5.17 is the closing story.

**First Implementation Priority:**

Story 5.1 (color-literal sweep + token-reader inventory) — pure read-only audit, produces two markdown reports. No code changes. Output gates Phase B story granularity (5.7, 5.8, 5.10 scopes are determined by what 5.1 surfaces). Can run in parallel with Stories 5.2 + 5.3.

## Initiative 5 — Public Registration & User Account Management

**Status:** 🚧 planning (started 2026-05-18). Project mode: brownfield — auth-surface expansion layered on Init 0 cookie+JWT foundation (`portal_access` 10min + `portal_refresh` 30d family rotation), Init 0 share-token Redis pattern, Init 0 audit-log `record_event()` helper. Source-of-truth for capability contract: `prd.md` § "Initiative 5" (24 FRs across 8 prefix groups + 12 NFRs across 6 categories). Source brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (v2, 213 lines, adversarial-review applied: P0×2 + P1×3 + P2×1 fixed) + distillate sibling. Source CC proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Decisions A–K below in-scope (numbering is initiative-local; Initiative 1's A–L, Initiative 2's A–H, and Initiative 3's A–J do not conflict). Decisions L–N deferred (see "Decisions Deferred" subsection — each has documented deferral motivation + future-initiative pointer).

### Overview

**Current state.** The portal admits two principals: `admin` (Michał) and `agent` (the AI service account). Catalog browse is gated at the nginx edge via IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`); there is no per-person login path for friends-and-family. The `member` role is already enumerated in `apps/api/app/core/db/models/_enums.py` (Init 0 baseline) but is unreachable — no registration flow, no admin UI for invite issuance, no 2FA infrastructure, and the network perimeter is still load-bearing for trust.

**Scope.** Five sequenced epics close the gap: **E6** (Member role + invite-based registration) wires the core flow against the existing auth stack; **E7** (TOTP 2FA + recovery codes) adds optional second-factor; **E8** (Admin panel: users + invites) ships two tabs in the existing admin UI; **E9** (Security audit — HARD GATE blocking E10) executes the pre-cutover audit per the gate condition in NFR5-SEC-1; **E10** (Edge cutover) atomically drops `auth_basic` + IP allowlist in the sibling nginx config repo. The cutover is the smallest change in the initiative — the bulk of the work is the audit that lets the portal trust the cutover, not the cutover itself.

**Brief working-label mapping.** The source brief uses dotted notation `5.1`–`5.5` as working labels. These map 1:1 onto project-global epic IDs per CC §3.4 (vanilla BMAD `epics-template.md` `{{N}}` unique-in-file constraint preserved via global numbering): brief `5.1` → **E6**, `5.2` → **E7**, `5.3` → **E8**, `5.4` → **E9**, `5.5` → **E10**. Story IDs follow `<global-epic-id>.<local-story-num>` (e.g., `Story 6.1`, `7.3`, `10.2`).

**Init 0 + Init 2 are unchanged.** Initiative 5 is purely additive on the brownfield base. The cookie+JWT auth stack stays exactly as Init 0 ships it. The share-token Redis pattern stays as the template for invite tokens — Decision A's dual-backed storage mirrors `apps/api/app/modules/share/service.py` deliberately. The audit-log surface gains 16 new actions (enumerated in FR5-AUDIT-1) but no contract changes — same `record_event()` helper, same `KNOWN_ENTITY_TYPES` registry, same `/api/admin/audit` query path. The `agent` service account is preserved exactly: cookie+password flow unchanged (Init 2), no 2FA forced ever (FR5-2FA-3 fail-fast startup check), `/agent-runbook` nginx bypass preserved across the Epic 10 cutover (NFR5-INT-1). The `admin` role is preserved exactly — `current_admin` dependency stays admin-only; no admin-tier expansion.

**Relationship to Init 0 anchors.** Decisions A and B extend the Init 0 share-token pattern (`apps/api/app/modules/share/`) with one new module (`apps/api/app/modules/invite/`) — identical Redis-primary + DB-audit shape, different key namespace (`invite:token:{token}` vs `share:token:{token}`) and different consumption semantics (single-use vs TTL-bounded reuse). Decision C extends the auth dependency family in `apps/api/app/core/auth/dependencies.py` with one new variant (`current_member_or_admin`) — `current_admin` stays admin-only. Decision F is a Pydantic Settings addition in `apps/api/app/core/config.py` with a fail-fast startup validation in `apps/api/app/main.py` lifespan-startup. Decisions D + E + I are three additive Alembic migrations (`0012`, `0013`, `0014`) — no rewrites of existing columns, no data backfill that touches `admin` or `agent` rows.

### Decisions In-Scope (A–K)

#### Decision A — Invite-token dual-backed storage (Redis primary + DB row audit history)

- **Realizes:** FR5-INVITE-1, FR5-INVITE-2.
- **Choice:** Active state lives in Redis at key `invite:token:{token}` (TTL-bounded, supports immediate revoke via `DEL`). Audit history lives in a new `invite_tokens` DB table (one row per generated invite, written at generation time, updated at consumption + revoke). The DB row outlives the Redis TTL — used and expired invites remain visible in the admin panel forever; Redis only carries the active set.
- **Alternatives rejected:** Redis-only (loses audit history on natural TTL expiry — operator cannot answer "did Anna ever consume the invite I sent her last month?"); DB-only (every `/register?token=` request hits SQLite, and TTL enforcement requires a manual sweep job — both anti-patterns versus Init 0's proven share-token shape); Redis-primary with separate audit-log row instead of dedicated table (audit-log payload schema is heterogenous-by-action and not optimized for filter-by-status pagination — see FR5-INVITE-2 Invites-tab filter requirement).
- **Rationale:** Mirrors the Init 0 share-token pattern (`apps/api/app/modules/share/service.py`) deliberately. Redis O(1) lookup + automatic TTL expiry covers the happy path. DB row captures `generated_by` / `generated_at` / `used_by` / `used_at` / `used_from_ip` for ops visibility and indefinite retention. The two backings are NOT a consistency hazard — Redis is authoritative for "is this token currently consumable", DB is authoritative for "what happened with this token", and the two never disagree (consumption flow is: validate-in-Redis → atomic-DB-update → DEL-Redis-key).
- **Cascading:** Decision B specifies the concrete Redis-value + DB-table shape. New module `apps/api/app/modules/invite/{service.py,router.py,admin_router.py}` follows the share-module file layout. Alembic migration `0012` adds `invite_tokens` table (Decision B). Failure mode is safe-degrade: if Redis is unreachable mid-consumption, the Redis-validate step returns 503 and the user is asked to retry — the DB row is NEVER updated without a successful Redis DEL (matches Init 0 share-token failure semantics).

#### Decision B — Invite-token shape (32-byte entropy + Redis key + DB schema + TTL preset enum)

- **Realizes:** FR5-INVITE-1, FR5-INVITE-4.
- **Choice:**
  - **Token generation:** `secrets.token_urlsafe(32)` → 43-character URL-safe string, 256 bits entropy. Single call site in `apps/api/app/modules/invite/service.py:generate_invite()`.
  - **Redis key:** `invite:token:{token}`. Value = JSON `{"role": "member", "generated_by_user_id": 1, "generated_at": "2026-MM-DDTHH:MM:SSZ", "invite_id": 42}`. TTL set via `EXPIRE` at write time, value matches `invite_tokens.ttl_seconds`.
  - **DB table `invite_tokens`** (Alembic `0012_invite_tokens.py`):
    | Column | Type | Notes |
    |---|---|---|
    | `id` | `UUID PK` | `uuid.uuid4()` default; matches Init 0 UUID-PK convention (`apps/api/app/core/db/models/_user.py:17`) |
    | `token_hash` | `VARCHAR(64) NOT NULL UNIQUE` | SHA-256 of token (token-at-rest is hashed; Redis holds cleartext during active TTL only) |
    | `role` | `VARCHAR(16) NOT NULL` | matches `UserRole(StrEnum)` |
    | `generated_by_user_id` | `UUID NULL FK user.id ondelete=SET NULL` | nullable per Decision A "DB row outlives Redis TTL" — the originating admin's deletion must not cascade-delete invite audit |
    | `generated_at` | `DATETIME NOT NULL` | |
    | `ttl_seconds` | `INTEGER NOT NULL` | redundant with Redis EXPIRE; preserved for audit |
    | `used_by_user_id` | `UUID NULL FK user.id ondelete=SET NULL` | set on consumption; nullable for same audit-survives-user-delete reason |
    | `used_at` | `DATETIME NULL` | |
    | `used_from_ip` | `VARCHAR(45) NULL` | IPv6-capable |
    | `revoked_at` | `DATETIME NULL` | set on FR5-INVITE-3 revoke |
  - **Indexes:** `UNIQUE(token_hash)`, `INDEX(generated_at DESC)` for admin-panel pagination, `INDEX(used_by_user_id)` for per-user invite history.
  - **TTL preset enum** in `apps/api/app/modules/invite/models.py`:
    ```python
    class InviteTTLPreset(IntEnum):
        ONE_DAY = 86400
        THREE_DAYS = 259200
        SEVEN_DAYS = 604800
        THIRTY_DAYS = 2592000
    ```
    Plus a `custom_ttl_seconds: int | None` field accepted from the admin panel for non-preset values (validated `60 ≤ custom ≤ 7776000` — 1 minute to 90 days).
- **Alternatives rejected:** 16-byte token (insufficient brute-force margin against NFR5-SEC-3 ≥10⁶-attempts requirement); raw cleartext token stored in DB (replay-protection requires hash-at-rest like password); UUID4 (122 effective bits — below the 256-bit margin target); HMAC-with-server-key tokens (unnecessary complexity — random opaque tokens with rate-limit are the simpler and equally-strong primitive); `secrets.token_hex(32)` (64-char hex vs 43-char URL-safe — same entropy, longer URL).
- **Rationale:** 256-bit entropy combined with the rate-limit middleware (Decision G) yields ≥10⁶ brute-force margin per NFR5-SEC-3. Token-at-rest hashing (SHA-256 not bcrypt — SHA-256 is sufficient because the search space is 256 bits, far beyond any offline brute-force budget; bcrypt is the right primitive for human-chosen passwords with low entropy, not for high-entropy opaque tokens). TTL preset enum keeps the admin panel form a finite radio-button choice + one custom-input fallback (matches brief working assumption).
- **Cascading:** Token never logged in cleartext (logger filter in `apps/api/app/core/logging.py` redacts query-string `token=*` and POST-body `token` fields). Cleartext token appears in two places: (1) generated-invite response to admin (one-time display), (2) `/register?token=` query string during consumption flow (TLS-terminated at nginx). Token is never returned in any list-invites response — admin panel shows DB row metadata only.

#### Decision C — Member permission scope diff (`current_member_or_admin` dependency family; share-router auth expansion; per-route allowlist table)

- **Realizes:** FR5-MEMBER-1, FR5-MEMBER-2.
- **Choice:**
  - **New dependency** in `apps/api/app/core/auth/dependencies.py`:
    ```python
    # As-shipped per Story 6.5 (commit a58c4b6) — adapted from initial pseudocode to match Init 0 idioms:
    # - JWT-only oracle (no DB lookup); returns uuid.UUID, not User ORM, mirroring _resolve_admin precedent
    # - Bare Depends(...) single-instance export (not Annotated[X, Depends(...)]) — matches existing dependency-injection convention
    # - snake_case detail string aligns with FastAPI/Pydantic error envelope convention used across the auth surface
    async def _resolve_member_or_admin(user_id: uuid.UUID = Depends(_resolve_current_user_id)) -> uuid.UUID:
        # role check via JWT claim — no DB I/O on the auth boundary
        if claims.role not in (UserUserRole.member, UserUserRole.admin):
            raise HTTPException(status_code=403, detail="member_or_admin_required")
        return user_id

    current_member_or_admin = Depends(_resolve_member_or_admin)
    ```
  - **Applied ONLY** to `POST /api/admin/share` in `apps/api/app/modules/share/admin_router.py`. `current_admin` dependency stays admin-only on every other admin route group.
  - **Per-route allowlist (binding contract):**

    | Route | Before (Init 0) | After (Init 5) | Reason |
    |---|---|---|---|
    | `POST /api/admin/share` | `current_admin` | `current_member_or_admin` | FR5-MEMBER-1 — member share-link generation is the only permission expansion |
    | `GET /api/share/{token}` | anonymous | anonymous (no change) | Init 0 — share consumption is public by design |
    | `DELETE /api/admin/share/{token}` | `current_admin` | `current_admin` (no change) | Revoke remains admin-only; member-initiated bulk revoke is out-of-scope |
    <!-- NOTE: pre-2026-05-19 plan listed `POST /api/admin/share/{id}/revoke` separately — that endpoint does not exist in code; the DELETE row above is the single revoke path. -->

    | All `/api/admin/*` | `current_admin` | `current_admin` (no change) | FR5-MEMBER-2 |
    | `/api/audit/*` (read) | `current_admin` | `current_admin` (no change) | FR5-MEMBER-2 |
    | `/agent-runbook` | nginx-bypass | nginx-bypass (no change) | NFR5-INT-1 + Decision K nginx config preservation |
    | `GET /api/catalog/*` | `current_user` | `current_user` (no change) | Catalog browse already gated to any authenticated user |
    | `GET /api/sot/*` | `current_user` | `current_user` (no change) | Same |
- **Alternatives rejected:** Add `member` to `current_admin` allowlist (semantic drift — `current_admin` becomes a misnomer for "member-or-admin"; future readers cannot trust the dependency name); generic role-based RBAC (`@requires(UserRole.member | UserRole.admin)`) (over-engineering for one route expansion; current dependency-injection pattern is the Init 0 idiom); reuse `current_user` on `POST /api/admin/share` (drops role-gating entirely — every authenticated user including future role additions could mint share tokens, breaks the "permission expansion is one bit" property).
- **Rationale:** Distinct dependency name encodes the expanded permission scope explicitly (brief's "permission expansion is one bit" framing is preserved). Existing `current_admin` semantics stay identical — no downstream test invalidation. Per-route table is the binding contract for the FR5-MEMBER-2 denial verifier (a member-authenticated `GET /api/admin/users` returns 403).
- **Cascading (as-shipped per Story 6.5 commit `a58c4b6`):** Per-file `client` fixture in `apps/api/tests/test_share_member_permission.py` mints both admin and member cookies inline (the `admin_user_cookies` conftest fixture referenced in pre-2026-05-19 planning text does NOT exist; per-file fixtures are the actual project convention through Init 0–5). Tests live flat at `apps/api/tests/test_share_member_permission.py` (the `apps/api/tests/integration/` directory referenced in pre-2026-05-19 text does NOT exist). Coverage: happy-path (`member` POST `/api/admin/share` returns 201) + denial-path (`member` GET `/api/admin/users` returns 403). FR5-MEMBER-3 per-member share cap (Decision H) layers on TOP of this dependency. **Action item carried into Epic 6 retro:** promote per-file `client` fixture to conftest once ≥3 test files need it (threshold reached at 4 files: 6.3 invite_admin, 6.4 invite_register, 6.5 share_member_permission, 6.7 ratelimit_share_cap).

<!-- Initiative 6 clarification 2026-05-20 — added by sprint-change-proposal-2026-05-20-post-cutover-auth.md §4.2.1 -->

**Initiative 6 clarification:** The per-route table above is **default-deny + explicit anonymous-allow allowlist**, NOT "per-route allow-with-named-dependency". Read it as: every `/api/*` route requires an explicit `current_*` Depends UNLESS the route appears in the table with `anonymous` in the "After" column. This property was implicit in the original Init 5 Decision C wording and was the proximate root cause of supplemental finding High-002 (post-cutover audit miss 2026-05-20): the implementation in `apps/api/app/modules/sot/router.py` shipped without the `current_user` Depends that this table specified, and the nginx perimeter masked the drift on the live deploy.

Initiative 6 adds:

- **Decision M (Init 6):** Mechanical route enforcement test (`apps/api/tests/test_route_enforcement_gate.py`) iterating the FastAPI route table and asserting each `/api/*` route either has an auth Depends OR appears in `_PUBLIC_ROUTES` allowlist constant. This is the structural fix for the drift class.
- **Decision N (Init 6):** Share-scoped asset endpoint `GET /api/share/{token}/files/{file_id}/content` replacing the implicit anonymous bypass via nginx for `/api/models/{m}/files/{f}/content` URLs that share-resolve emitted. Hardened-(a) design per Codex peer-grill 2026-05-20 (kind filter, no-store cache, audit token-hash, path-token redaction).
- **Decision O (Init 6):** Frontend shell-level AuthGate in `AppShell.tsx` replacing per-route `<AuthGate>` wrappers; anonymous user surface is the login screen only.

See § Initiative 6 (below) for the full Decisions M–O text.

#### Decision D — 2FA column shape on `users` table (Fernet-encrypted `totp_secret` + nullable `totp_enabled_at`)

- **Realizes:** FR5-2FA-1, FR5-2FA-2, NFR5-INT-1.
- **Choice:**
  - **New columns on `users`** (Alembic `0013_users_2fa_columns.py`):
    | Column | Type | Default | Notes |
    |---|---|---|---|
    | `totp_secret` | `VARCHAR(255) NULL` | `NULL` | Fernet ciphertext (`cryptography.fernet`); NULL = no TOTP configured |
    | `totp_enabled_at` | `DATETIME NULL` | `NULL` | NULL = 2FA inactive; `IS NOT NULL` = login flow extends with second factor |
  - **Encryption key** in `apps/api/app/core/config.py`:
    ```python
    TOTP_FERNET_KEY: str  # 32 url-safe base64 bytes; sourced from infra/.env mode 600
    ```
    Loaded at app startup via Pydantic Settings; absence raises `RuntimeError` (fail-fast) so an unconfigured deployment cannot accidentally store plaintext secrets.
  - **Encryption boundary:** cleartext `totp_secret` exists in process memory ONLY inside `apps/api/app/modules/auth/totp/service.py:_decrypt_secret()` for the duration of one TOTP verify call. Stored column value is always Fernet ciphertext. Encryption helper has no logging of cleartext; serialization helpers in `apps/api/app/core/db/serializers.py` explicitly omit `totp_secret` from any `users` row response.
  - **Migration semantics:** Both columns NULL-default; existing `admin` (Michał) and `agent` rows are unaffected (NFR5-INT-1 null-op).
- **Alternatives rejected:** Plaintext `totp_secret` (BAD per OWASP ASVS V2.8.5 — TOTP shared secrets are credential-equivalent and must be encrypted at rest); separate `user_totp` table (one-to-one with `users` doesn't justify the JOIN cost on every 2FA-required login; no recurring multi-row use case); AES-GCM raw (Fernet is AES-128-CBC + HMAC-SHA256 + versioned tokens — same security envelope, less footgun-prone API for app code).
- **Rationale:** Per-column Fernet encryption isolates the cleartext surface to one service module + one decryption call per verify. `totp_enabled_at` nullable timestamp doubles as enrollment audit (avoids a separate `users.has_2fa` bool that could drift out of sync with secret presence — single source of truth: `totp_enabled_at IS NOT NULL`). Fernet's versioned-token format gives the future key rotation path without a separate `key_version` column.
- **Cascading:** `TOTP_FERNET_KEY` added to `infra/.env` template (mode 600; rotation procedure deferred until first member-account ages 12+ months — explicit Out-of-scope for E7 per brief Vision section). Test fixture `apps/api/tests/conftest.py:TOTP_FERNET_KEY` overrides for tests. Recovery codes (Decision E) live in a separate table — they are NOT stored as additional `totp_secret` rows.

#### Decision E — Recovery codes schema (bcrypt-at-rest, batch grouping, lifecycle columns)

- **Realizes:** FR5-2FA-1, FR5-2FA-2, FR5-2FA-4.
- **Choice:**
  - **New table `recovery_codes`** (Alembic `0013_users_2fa_columns.py` — combined with Decision D in one migration since both target the same 2FA enrollment milestone):
    | Column | Type | Notes |
    |---|---|---|
    | `id` | `UUID PK` | `uuid.uuid4()` default; matches Init 0 UUID-PK convention |
    | `user_id` | `UUID NOT NULL FK user.id ondelete=CASCADE` | recovery codes cascade-delete with their owning user (no audit-survives-delete requirement here) |
    | `code_hash` | `VARCHAR(60) NOT NULL` | bcrypt hash (cost 12, matches existing password hashing config) |
    | `batch_id` | `UUID NOT NULL` | groups the 8 codes generated together; uuid4 |
    | `generated_at` | `DATETIME NOT NULL` | |
    | `used_at` | `DATETIME NULL` | set on consumption — row stays for audit |
    | `invalidated_at` | `DATETIME NULL` | set when batch is invalidated by regen (FR5-2FA-4) or by `auth.totp.disabled` |
  - **Indexes:** `INDEX(user_id, invalidated_at)` for "fetch active batch for this user" queries; `INDEX(user_id, used_at)` for audit queries.
  - **Code shape:** `secrets.token_hex(4)` → 8-character hex string (32 bits entropy per code). 8 codes per batch. Displayed cleartext ONCE at enrollment / regeneration; subsequent panel loads return only batch metadata (`{batch_id, generated_at, codes_remaining}`).
  - **Consumption check:** at second-factor verify, iterate active batch (where `invalidated_at IS NULL`) calling `bcrypt.checkpw(submitted_code, row.code_hash)`. Bcrypt cost 12 means ~250ms per check; 8 codes × 250ms = 2s worst-case is acceptable for a recovery flow. First match sets `used_at` and emits `auth.recovery_code.used`.
- **Alternatives rejected:** Plaintext codes in DB (loses defense-in-depth on DB compromise — DB leak = instant 2FA bypass for every user); SHA-256 hash (32-bit code space + fast SHA-256 = 4-billion-attempt rainbow table fits in ~200GB, brute-forceable offline); single `users.recovery_codes_json` column (loses per-code lifecycle audit; cannot answer "which code did Anna consume on 2026-06-12?"); per-user single random "master recovery secret" instead of 8 codes (loses brief's verbatim "8 single-use codes" + drill artifact NFR5-OBS-2 step).
- **Rationale:** bcrypt-at-rest mirrors password hashing — DB compromise leaks a slow-search artifact (32-bit entropy × bcrypt cost 12 yields ≥10⁹ years average crack time per code). Batch grouping preserves the audit history (which generation cycle did the consumed code come from). Regeneration (FR5-2FA-4) is a one-statement `UPDATE recovery_codes SET invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL` followed by an INSERT of the new 8-code batch.
- **Cascading:** UI displays cleartext codes via download-as-txt + clipboard-copy buttons (no "view again" path — once dismissed, codes are unrecoverable from the panel). Recovery-code drill artifact (`_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-MM-DD.md` per NFR5-OBS-2) executes one consumption to verify the flow; consumed code is logged in the artifact with timestamp + AuditLog row reference.

#### Decision F — 2FA enforcement config flag (`enforce_2fa_for_roles` + fail-fast startup validation)

- **Realizes:** FR5-2FA-3, NFR5-INT-1.
- **Choice:**
  - **Config flag** in `apps/api/app/core/config.py`:
    ```python
    enforce_2fa_for_roles: list[Role] = Field(default_factory=list)
    ```
  - **Startup validation** in `apps/api/app/main.py` lifespan-startup, runs BEFORE Redis connection and BEFORE any route is mounted:
    ```python
    if UserRole.agent in settings.enforce_2fa_for_roles:
        raise RuntimeError(
            "agent role MUST NEVER appear in enforce_2fa_for_roles "
            "(it is a service account; forcing 2FA would brick AI ingestion). "
            "Edit apps/api/app/core/config.py or infra/.env to remove it."
        )
    ```
  - **Per-user override:** admin force-enrollment (FR5-ADMIN-2 `force-2FA-enrollment` action) sets `users.totp_enabled_at` directly regardless of role — independent of config flag, no startup dependency. The flag governs MANDATORY enrollment-on-next-login for a whole role; per-user force is a one-off action.
  - **Enforcement check** in `apps/api/app/core/auth/middleware.py` (post-login, pre-cookie-issue): if `user.role in settings.enforce_2fa_for_roles and user.totp_enabled_at IS NULL`, return partial-auth response that forces the frontend to land on `/settings/2fa` enrollment screen before any other route works.
- **Alternatives rejected:** Boolean global flag (loses per-role granularity; "enforce 2FA for everyone" doesn't fit the operator's banking-IT instinct of "members only, agent never"); allow-list with no startup validation (a typo in `infra/.env` could brick the agent flow silently); DB-stored config (mismatch with all other rate-limit/CSRF/cookie settings in Pydantic Settings; introduces a config-drift surface between DB and `core/config.py`); env-var-only boolean per role (`ENFORCE_2FA_FOR_MEMBER=true`) (less type-safe than a `list[Role]` field validated by Pydantic).
- **Rationale:** Fail-fast on startup catches operator misconfiguration before any request reaches the wire — the agent ingestion flow is the single most-load-bearing dependency in Init 2 and a 2FA-enforced agent would silently break overnight ingestion runs. Per-role granularity matches the brief's working assumption verbatim ("`enforce_2fa_for_roles: list[Role]`").
- **Cascading:** Test `apps/api/tests/test_config.py::test_agent_role_in_enforce_2fa_raises` verifies the startup-fail path (instantiating `TestClient` with `enforce_2fa_for_roles=[UserRole.agent]` raises `RuntimeError`). Lifespan startup ordering: validation runs FIRST (no resource waste on misconfigured boot). Operator runbook documents the flag in `_bmad-output/project-context.md` post-E10 (deferred per CC §2.2). **Enforcement check placement:** inline in `apps/api/app/modules/auth/router.py::login()` (after password verify, before `set_session_cookies`) — NOT in `app/core/auth/middleware.py` (that module does not exist; per-request middleware would re-decode JWT on every request, violating Init 0 perf budget).

#### Decision G — Rate-limit middleware (Redis sliding-window, key shape, threshold config, middleware placement)

- **Realizes:** FR5-RATELIMIT-1, FR5-RATELIMIT-2, NFR5-SEC-3.
- **Choice:**
  - **Algorithm:** Redis-backed **sliding window over sorted set**. Per-request operations:
    ```
    now_ms = epoch milliseconds
    member = f"{now_ms}-{uuid.uuid4().hex}"   # unique member shape to avoid sub-millisecond burst collapse
    ZREMRANGEBYSCORE ratelimit:{scope}:{key} -inf (now_ms - window_ms)
    ZADD ratelimit:{scope}:{key} now_ms member
    EXPIRE ratelimit:{scope}:{key} ceil(window_seconds + 1)
    ZCARD ratelimit:{scope}:{key} → current count
    ```
    Pipelined into one Redis round-trip via `MULTI/EXEC`. Count > threshold → reject with HTTP 429. **Member shape note (Story 6.6 ship correction):** pre-2026-05-19 pseudocode used `ZADD ... now now` (score AND member both `now_ms`); under sub-millisecond bursts ZADD with identical (score, member) pairs is a no-op, collapsing 6 in-millisecond requests into 1 ZSET entry and under-counting the actual rate. The shipped code uses `f"{now_ms}-{uuid.uuid4().hex}"` as the member to keep each request distinct while preserving sliding-window math on the score.
  - **Module:** new `apps/api/app/core/auth/ratelimit.py` exporting `RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold, soft_alert_threshold=None, retry_after_seconds_fn=None)`. As-shipped shape is **raw-ASGI** (`async def __call__(self, scope, receive, send)`) not `BaseHTTPMiddleware` (`call_next`); the pre-2026-05-19 pseudocode used `BaseHTTPMiddleware.dispatch(request, call_next)` shorthand — semantically equivalent but the shipped form runs sooner in the request lifecycle and avoids a `Request` instantiation per call.
  - **Key shapes (binding):**
    | Scope | Key | Window | Threshold | Realizes |
    |---|---|---|---|---|
    | `login` | `ratelimit:login:ip:{ip}` | 60s | 5 failures | FR5-RATELIMIT-1, SC#6 |
    | `refresh` | `ratelimit:refresh:ip:{ip}` | 60s | 10 attempts | FR5-RATELIMIT-1 |
    | `register` | `ratelimit:register:ip:{ip}` | 60s | 3 attempts | FR5-RATELIMIT-1, NFR5-SEC-3 |
    | `share` | `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` | 86400s | 20 creations | FR5-RATELIMIT-2, FR5-MEMBER-3, Decision H |
  - **Thresholds** sourced from `apps/api/app/core/config.py` (Pydantic Settings); all four scopes have tunable `*_window_seconds` + `*_threshold` config keys.
  - **Middleware placement** in `apps/api/app/main.py` factory (as-shipped per Story 6.6 commit `68fa766`, validated end-to-end on `.190`): rate-limit middlewares are added FIRST via `app.add_middleware(...)`, then `install_csrf_middleware(app)` is called LAST. Starlette's `add_middleware` always prepends to `app.user_middleware`, so the LAST-added middleware wraps OUTERMOST in the request flow. Outcome: CSRF wraps outermost, rate-limit fires AFTER the CSRF check but BEFORE auth dependency resolution. Rationale: a 403 `csrf_required` rejection MUST NOT burn rate-limit budget (test_login_csrf_rejection_does_not_burn_rate_limit invariant); brute-force POST attempts against `/api/auth/login` must be rate-limited by IP BEFORE the password-hash check absorbs the cost the limiter was meant to prevent. **Pre-2026-05-19 wording** said "AFTER CORS, AFTER CSRF check, BEFORE auth dependency resolution" and implied install-order was source-order — that wording is empirically inverted vs Starlette LIFO behavior. `@app.middleware("http")` decorator and `app.add_middleware(MiddlewareClass)` form behave identically (both prepend to `user_middleware`); the dev-time Dev Notes claim that decorator-form wraps outermost is incorrect.
  - **Failure mode:** if Redis is unreachable, middleware logs `WARNING app.auth.ratelimit redis_unavailable scope={scope}` and ALLOWS the request (matches Init 0 share-token fail-soft semantics — Redis outage degrades to "no rate-limit" not "no auth"). GlitchTip captures the warning per NFR5-OBS-1.
- **Alternatives rejected:** Token bucket (per-key lazy-reset state means single-Redis-call atomicity is harder; sliding-window with ZREMRANGEBYSCORE + ZADD + ZCARD is one round-trip and stateless server-side); leaky bucket (same Redis complexity as sliding-window with no perceptible UX advantage); in-process counters (loses cross-worker accuracy — uvicorn workers fan out the per-key state); third-party `slowapi` / `fastapi-limiter` (extra dependency for ~80 LOC of bespoke logic; key-shape control matters for the 4-scope contract).
- **Rationale:** Sliding-window over Redis sorted set is the industry-standard distributed rate-limit primitive (same approach used by Cloudflare, GitHub API). Single pipelined round-trip per request. Fail-soft on Redis outage is the right trade-off for a homelab — losing rate-limit briefly is better than losing the entire authentication surface (the LAN+VPN allowlist still protects the portal during the cutover window; post-cutover the audit gate ensures no Critical/High brute-force exposure exists).
- **Cascading:** Middleware order documented in `_bmad-output/project-context.md` post-E10 (per CC §2.2 — deferred to post-cutover rule addition). E9 audit (NFR5-SEC-3) verifies all four scopes — invite-token brute force (must reject before 256-bit entropy depletion by ≥10⁶ margin, satisfied trivially by 3 attempts / 60s on the register scope), `/api/auth/login` SC#6 verification, `/api/auth/refresh` family-rotation interaction, `/api/share/` per-member cap (Decision H). Test fixture installs `fakeredis` for unit tests; integration tests against `.190` exercise the real Redis instance.

#### Decision H — Per-member share cap (cap key shape, soft/hard thresholds, admin exemption)

- **Realizes:** FR5-MEMBER-3, FR5-RATELIMIT-2.
- **Choice:**
  - **Cap key:** `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` (reuses Decision G middleware with `share` scope). Day boundary is UTC (deterministic, no timezone math).
  - **Hard threshold:** 20 share creations per 24h window → HTTP 429 `Too Many Requests` with `Retry-After: <seconds-until-UTC-midnight>` header. Matches brief working-assumption floor verbatim.
  - **Soft threshold (alert):** 10 creations per 24h (50% of hard threshold). Middleware emits a structured WARNING-level log on logger `app.share.ratelimit` (distinct from `app.auth.ratelimit` used for `redis_unavailable`) with `event.action="share.ratelimit.soft_alert"` and `labels.{scope, key, count, threshold, soft_alert_threshold}` extras — visible in GlitchTip per NFR5-OBS-1, queryable for operator review. Pre-2026-05-19 wording phrased the log target as a single name `app.share.ratelimit.soft_alert` — as-shipped per Story 6.7 commit `12ba359`, the name decomposes as `logger.name=app.share.ratelimit` + `event.action=share.ratelimit.soft_alert`. Fires once per crossing per key per process (strict equality `count == soft_alert_threshold` after incrementing).
  - **Admin exemption:** if `request.state.user.role == UserRole.admin`, middleware skips both threshold checks for the `share` scope. Rationale: admin share creation is operator-direct catalog curation work; rate-limiting Michał would be operator-self-DoS. The exemption is scoped to the `share` rate-limit ONLY — admin is still bound by the `/api/auth/refresh` rate-limit (no exemption from auth-surface protections).
  - **Scope:** cap applies ONLY to `POST /api/admin/share`. `DELETE /api/admin/share/{token}` is admin-only (per Decision C) and not rate-limited. `GET /api/share/{token}` is anonymous consumption — no per-creator cap applies.
- **Alternatives rejected:** Per-hour throttle (loses brief's "20/day" verbatim; per-hour creates a burst-resistant pattern that doesn't match operator's mental model of "20 share links a day is a lot"); per-week cap (loses today/yesterday signal — operator wants to see "Anna is at 18/20 today" not "Anna is at 95/140 this week"); per-IP cap (defeats the entire "member identity matters" property of the design — a member behind CGNAT would inherit shared-IP throttle); no admin exemption (operator self-DoS during catalog curation).
- **Rationale:** Cap is per-user, per-day, soft-alert at 50% — matches brief working assumption verbatim. Admin exemption keeps the operator unrestricted during catalog work. UTC day boundary keeps the cap key deterministic and avoids DST edge cases. The soft-alert log enables the compromised-member detection pattern: correlate `app.share.ratelimit.soft_alert` with `auth.refresh.reuse_detected` for the same `user_id` (brief working assumption "Member share-link generation is a deliberate amplification surface").
- **Cascading:** Audit smoke (NFR5-SEC-3 share-token-abuse scenario) verifies both the soft-alert log emission at the 10th creation AND the hard-fail HTTP 429 at the 21st. The exemption check is a single `if user.role == UserRole.admin: return await call_next(request)` line in `apps/api/app/core/auth/ratelimit.py` — no separate admin-rate-limit middleware. Per-member counter survives uvicorn worker restarts (Redis-backed).

#### Decision I — Soft-delete + `last_active_at` throttling (`is_active` column + Redis SET NX EX last-write throttle)

- **Realizes:** NFR5-PERF-1, FR5-ADMIN-2, FR5-ADMIN-3.
- **Choice:**
  - **New columns on `users`** (Alembic `0014_users_is_active_last_active.py`):
    | Column | Type | Default | Notes |
    |---|---|---|---|
    | `is_active` | `BOOLEAN NOT NULL` | `TRUE` | existing rows backfill to TRUE |
    | `last_active_at` | `DATETIME NULL` | `NULL` | populated by middleware throttle |
  - **Throttle implementation** in `apps/api/app/core/auth/middleware.py` (`LastActiveMiddleware`, runs after auth dependency resolution on authenticated requests):
    ```python
    last_write_key = f"user:last_active:{user.id}"
    acquired = await redis.set(last_write_key, now_iso, nx=True, ex=300)
    if acquired:
        await db.execute(
            update(User).where(User.id == user.id).values(last_active_at=now)
        )
    ```
    `SET NX EX 300` is a single atomic Redis call: writes only if key doesn't exist, sets 5-minute TTL. The `if acquired` branch fires at most once per user per 300 seconds. ≤1 DB write per user per 5 minutes regardless of request rate (matches NFR5-PERF-1 verbatim).
  - **Soft-delete behavior:** `is_active = FALSE` users:
    - **JWT-based requests:** existing `portal_access` cookies remain valid until natural 10-minute expiry (no proactive token revocation — matches existing session-revoke semantics in `apps/api/app/modules/auth/sessions/`).
    - **Refresh-token rotation:** `POST /api/auth/refresh` checks `user.is_active`; if FALSE, returns HTTP 401 + emits `auth.login.fail` reason `account_deactivated`, AND invalidates the entire refresh-token family (matches existing reuse-detection invalidation pattern). After ≤10 minutes the access token expires and the user is fully logged out.
    - **Login attempts:** `POST /api/auth/login` checks `user.is_active`; FALSE → HTTP 401 with the same reason.
  - **Admin actions** (FR5-ADMIN-2):
    - `deactivate` → `UPDATE users SET is_active = FALSE` + `record_event('user.deactivated', actor_user_id=admin.id, target_user_id=user.id)`.
    - `reactivate` → `UPDATE users SET is_active = TRUE` + `record_event('user.reactivated', ...)`.
    - `force logout-all-sessions` → invalidate all refresh-token families for the user (existing `apps/api/app/modules/auth/sessions/service.py` revoke-all helper) + `record_event('user.force_logout', ...)`. Independent of `is_active` — applies to active users too.
- **Alternatives rejected:** Hard-delete on deactivate (FK integrity damage on `audit_log.actor_user_id` and `refresh_tokens.user_id`; loses audit history — "who issued this invite a year ago?" returns NULL); in-memory throttle (loses cross-worker accuracy — every uvicorn worker would independently throttle); ZADD-based heatmap structure (over-engineering for a single timestamp column — `SET NX EX` is the minimum primitive); cron-based batch update of `last_active_at` from access logs (defers signal by minutes — admin panel wants live-ish data); proactive JWT revocation on deactivate (requires JWT blacklist infrastructure — out-of-scope; 10-minute access-token window is short enough to accept).
- **Rationale:** `SET NX EX` is a one-call atomic throttle primitive — no locking, no race, no per-worker drift. The 5-minute throttle window matches brief assumption verbatim and reduces SQLite write churn from request-frequency to per-user-per-5-min (3+ orders of magnitude). Soft-delete keeps full audit history intact (brief working assumption: hard-delete reserved for GDPR right-to-be-forgotten, DB-direct only — not exposed in the panel).
- **Cascading:** `AuthGate` frontend pattern is unchanged (deactivation surfaces as 401 just like expired session — existing refresh-then-retry flow handles the redirect to login). Admin panel `is_active` toggle is a single PATCH endpoint at `/api/admin/users/{id}` (FR5-ADMIN-2). Bulk deactivation explicitly NOT in panel UI (FR5-ADMIN-4) — DB-direct only.

#### Decision J — Cross-repo cutover smoke matrix (4-scenario test definition + artifact format)

- **Realizes:** FR5-CUTOVER-2, NFR5-OBS-2.
- **Choice:**
  - **Smoke script:** `infra/scripts/cutover-smoke.sh` in `3d-portal`, authored as part of Story 10.x pre-cutover. Bash + `curl` + `jq` — same toolchain as the existing `verify-symbolication.sh` (Init 1 Decision K convention). `set -euo pipefail` + dependency check + stdout-narrative + stderr-errors per Init 1 § "Bash Script Conventions".
  - **Four scenarios** (executed sequentially against `https://3d.ezop.ddns.net`, total ≤30 seconds wall time):

    | # | Scenario | Setup fixture | Request | Expected | Failure mode |
    |---|---|---|---|---|---|
    | 1 | **Share bypass** | cron-refreshed share token, valid 24h | `curl -fsS -o /dev/null -w "%{http_code}" https://3d.ezop.ddns.net/share/<test-token>` | `200` | nginx share-location rule regressed; immediate rollback |
    | 2 | **Agent ingestion** | `agent` cookie-jar from `/api/auth/login` | `POST /api/admin/models` with minimal STL fixture | `201` | agent role broke; immediate rollback (NFR5-INT-1 violation) |
    | 3 | **Member login** | seeded test-member from panel-issued invite ≥24h before | `POST /api/auth/login` username+password | `200` + `portal_access` cookie set | new auth path broken; immediate rollback |
    | 4 | **Admin login** | `admin` (Michał) credentials | `POST /api/auth/login` then `GET /api/admin/users` | `200` (login) + `200` (admin scope verified) | admin scope regressed; immediate rollback |
  - **Artifact** at `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` (matches NFR5-OBS-2 second-drill-artifact slot):

    ```markdown
    | # | Scenario | Expected | Actual | Status | Timestamp (UTC) | Request ID | Audit row delta |
    |---|---|---|---|---|---|---|---|
    | 1 | Share bypass | 200 | 200 | ✅ PASS | 2026-MM-DDTHH:MM:SSZ | req_abc123 | (no auth event — anonymous bypass) |
    | 2 | Agent ingestion | 201 | 201 | ✅ PASS | ... | req_def456 | `auth.login.success` (actor=agent), `model.created` |
    | 3 | Member login | 200 + cookie | 200 + cookie | ✅ PASS | ... | req_ghi789 | `auth.login.success` (actor=test-member) |
    | 4 | Admin login | 200 + admin scope | 200 + admin scope | ✅ PASS | ... | req_jkl012 | `auth.login.success` (actor=admin) |

    **Rollback drill:** `git revert <sha>` + `nginx -s reload` + re-run scenarios 1-4 → all PASS → `git revert <revert-sha>` + `nginx -s reload` + re-run → all PASS. Total drill window: HH:MM:SS.
    ```
  - **Any FAIL row** → immediate rollback execution per Decision K. Pre-cutover checklist (Story 10.x) verifies all three setup fixtures (test-member, test-share-token, test-STL) ahead of the cutover commit.
- **Alternatives rejected:** pytest-based smoke (requires Python venv on `.180`; over-engineering for 4 curl calls; doesn't run from operator's local shell during cutover); Playwright smoke (DOM-render path doesn't exercise the auth/share boundary directly — the boundary is HTTP-status-shaped); single curl multi-scenario one-liner (loses per-scenario timing + request IDs); REST-Client-style `.http` files (no CLI executor available on `.180`).
- **Rationale:** Bash + curl is the lowest-friction execution path on `.180` (already required for `nginx -s reload`). Per-scenario timestamps + request IDs enable post-cutover correlation against GlitchTip logs (NFR5-OBS-1 + NFR5-OBS-2 second-drill-artifact). The artifact format mirrors the Init 1 verify-symbolication artifact shape (operator pattern familiarity).
- **Cascading:** Test fixtures pre-seeded by Story 10.x: one test-member account (registered via panel-issued invite 24h before cutover), one share token kept fresh by hourly cron-refresh (preserved through cutover), one minimal STL fixture for agent POST. Smoke script lives in `3d-portal/infra/scripts/` — NOT in the sibling configs repo (operator runs it from the `3d-portal` working tree against the deployed `.190` instance).

#### Decision K — Nginx config diff + rollback (concrete diff, single-commit atomic edit, ≤30s rollback)

- **Realizes:** FR5-CUTOVER-1, FR5-CUTOVER-3, NFR5-PERF-2, NFR5-CROSS-REPO-1, NFR5-CROSS-REPO-2, NFR5-INT-2.
- **Choice:**
  - **Concrete diff** against current `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (sibling repo, deployed to `.180`):

    ```diff
     server {
       listen 443 ssl;
       server_name 3d.ezop.ddns.net;
       ssl_certificate /etc/letsencrypt/live/3d.ezop.ddns.net/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/3d.ezop.ddns.net/privkey.pem;
    -
    -  # Edge-gate (Init 0): drop atomically in cutover commit
    -  auth_basic           "3d-portal";
    -  auth_basic_user_file /etc/nginx/.htpasswd-portal;
    -  allow 192.168.2.0/24;
    -  allow 10.8.0.0/24;
    -  deny  all;

       location /share/ {
    -    auth_basic off;
    -    allow all;
         proxy_pass http://192.168.2.190:8090;
         proxy_set_header Host              $host;
         proxy_set_header X-Real-IP         $remote_addr;
         proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /agent-runbook {
    -    auth_basic off;
    -    allow all;
         proxy_pass http://192.168.2.190:8090;
         proxy_set_header Host              $host;
         proxy_set_header X-Real-IP         $remote_addr;
         proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
       }

       location / {
         proxy_pass http://192.168.2.190:8090;
         proxy_set_header Host              $host;
         proxy_set_header X-Real-IP         $remote_addr;
         proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
       }
     }
    ```

    Key property: removing the server-level `auth_basic` + `allow`/`deny` block makes the per-location `auth_basic off;` + `allow all;` overrides redundant — they are removed in the same commit for cleanliness, but the share + agent-runbook bypass behavior is preserved (no `auth_basic` parent directive to disable, all locations are bypass-by-default).
  - **Commit message convention** (sibling repo `~/repos/configs/`):
    ```
    feat(nginx): drop auth_basic + IP allowlist for 3d-portal cutover
    ```
    Conventional-commit `feat(nginx)` matches sibling repo's existing commit style. Body references `3d-portal` PR + cutover artifact path.
  - **Rollback sequence** (any smoke scenario regresses; ≤30 seconds end-to-end per FR5-CUTOVER-3 + NFR5-PERF-2):
    ```bash
    # On dev box:
    cd ~/repos/configs
    git revert <cutover-sha> --no-edit
    git push origin main

    # On .180:
    ssh .180 "cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload"

    # Verification:
    bash infra/scripts/cutover-smoke.sh  # re-run Decision J — all 4 PASS confirms rollback success
    ```
  - **Pre-flight gate:** `sudo nginx -t` (config syntax check) MUST pass on `.180` before reload — verified in Story 10.x pre-cutover checklist. If `nginx -t` fails, the cutover is aborted before reload (no traffic disruption).
  - **Cutover bypasses `3d-portal` `deploy.sh` skip-gate** (NFR5-CROSS-REPO-1): the edit lives in the sibling repo and has no equivalent of `infra/.last-deploy-sha`. Closing commit in `3d-portal` (`docs/operations.md` cutover-date update with non-skip-prefixed message such as `feat(infra): record edge cutover date 2026-MM-DD`) records the cutover within `3d-portal`'s deploy history per `feedback_auto_deploy_dev.md`.
- **Alternatives rejected:** Move `auth_basic` off in a separate commit before allowlist drop (creates a window where portal trusts itself with no IP fence — wrong order; widens attack surface during the gap); separate staging nginx (no staging exists in homelab; cutover IS the test); blue-green nginx with two configs (over-engineering for a 5-minute atomic change); keep `auth_basic` as fallback with disabled `allow`/`deny` (BAD — `.htpasswd-portal` shared credential becomes load-bearing in an unintended way; cleaner to drop both directives in one commit and let the portal own the auth boundary entirely).
- **Rationale:** Single-commit atomic cutover preserves the rollback property — one SHA reverts both directive drops AND the per-location bypass cleanups in lockstep. Location-block bypass preservation is the load-bearing detail — `/share/*` and `/agent-runbook` must remain anonymous-accessible after the cutover (NFR5-INT-2 + brief working assumption verbatim). Pre-flight `nginx -t` gate eliminates the "broken config + reload" failure mode entirely.
- **Cascading:** Sibling repo commit SHA cited in Story 10.x acceptance criterion. Rollback story spans both repos per NFR5-CROSS-REPO-2 — story tasks reference two working trees (configs + 3d-portal). The closing `docs/operations.md` update commit in `3d-portal` is the explicit deploy-history record (the deploy gate skips infrastructure-only commits — but the operations.md edit is code-level + has no skip-prefix, so it correctly fires `deploy.sh` and records the cutover SHA in `infra/.last-deploy-sha`).

### Decisions Deferred (L–N)

These decisions are explicitly out-of-scope for Initiative 5 and documented here to prevent future agents from inferring missing capabilities as Init 5 gaps. Each has a documented deferral motivation + future-initiative pointer per brief Out-of-scope section.

#### Decision L — Self-service mail-based password reset (deferred)

- **Reason:** Depends on self-hosted mail server initiative (separate future work, no current commitment). V1 uses admin-issued password-reset link (FR5-ADMIN-3) — functionally identical to invite token shape (Decision B), delivered out-of-band by the operator (SMS / Messenger / personal mail). Every reset is a manual operator action until the mail server lands.
- **Where it goes:** Self-hosted mail server initiative (vision-tier per brief §"Vision" +12 months). When the mail server arrives, this path becomes self-service via `POST /api/auth/password-reset` with email lookup → mail delivery of single-use Redis-fronted token (same shape as Decision B). No schema change required at that time — only a new public route + mail-server integration.
- **Cross-reference:** brief working assumption "Admin-issued password reset link is delivered out-of-band by the operator"; PRD FR5-ADMIN-3.

#### Decision M — OIDC/SSO federation (Authentik in homelab) (deferred)

- **Reason:** Explicitly Out-of-scope per brief Q5 + PRD § "Out". V1 uses native cookie+JWT accounts only — Initiative 5's audience (~10-20 friends-and-family) doesn't justify the federation surface, and the brownfield base will have `member` role + cookie+JWT auth in production after Init 5 ships, making federation purely additive.
- **Where it goes:** `member-print-requests` initiative may revisit if it surfaces multi-role-per-user requirements (e.g., a member who is also a printer-owner across multiple homelab services). At that point, OIDC/Authentik can layer on top of the existing role enum without schema migration of `users`.
- **Cross-reference:** brief Q5 (operator-confirmed non-goal); PRD § "Out".

#### Decision N — Per-model ACL (`member X sees subset of catalog`) (deferred)

- **Reason:** V1 all-or-nothing access for `member` role per brief Q5. Catalog-wide reads are the "simplicity is the moat" property — adding per-model ACL would multiply the permission surface (~hundreds of models × per-member grants) and create the very complexity that the friends-and-family scope explicitly avoids.
- **Where it goes:** Future initiative if and when the friend-circle outgrows the trust model (e.g., curated subgroups by interest area). Implementation would add a `model_access_grants` table with `(user_id, model_id, granted_by, granted_at)`; the catalog query gains a `LEFT JOIN` filter. No `users` or `models` schema changes required at that time.
- **Cross-reference:** brief Q5 (operator-confirmed non-goal); PRD § "Out"; brief §"What We Are NOT Solving".

### Cross-references

- **PRD Initiative 5 section** — `prd.md` § "Initiative 5 — Public Registration & User Account Management" (lines 1065-1258). Each Decision A–K above realizes one or more concrete FR5-* / NFR5-* requirement IDs — see the `**Realizes:**` line in each Decision header. Forward references from PRD to this section: FR5-RATELIMIT-1 → Decision G; FR5-CUTOVER-1 → Decision K.
- **Brief v2** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines; adversarial-review applied: P0×2 + P1×3 + P2×1 fixed). Binding content source. Decisions A, B, D, E, F, G, H, K each cite a specific brief working assumption verbatim.
- **Brief distillate** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5688 tokens, LLM-optimized).
- **Sprint Change Proposal** — `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Document-shape (single-file H2-append per CC §3.3) + decision scope (A–K in, L–N deferred per §4.2 2B) + epic numbering (global E6–E10 per §3.4) are locked here.
- **Init 0 baseline anchors:**
  - **Auth stack** — `docs/architecture.md` § "Auth module" + `apps/api/app/core/auth/` (cookies, csrf, jwt, refresh, dependencies, sessions). Decision C extends `dependencies.py`; Decision D extends `core/db/models/_user.py`; Decision F extends `core/config.py` + `main.py` lifespan; Decision G adds `core/auth/ratelimit.py`; Decision I adds `core/auth/middleware.py:LastActiveMiddleware`.
  - **Share-token Redis pattern** — `apps/api/app/modules/share/{service.py,models.py,admin_router.py}` (Init 0 baseline). Decision A's dual-backed storage mirrors this pattern; Decision C extends the share-router auth dependency; Decision H caps share creation per-member.
  - **Audit log** — `apps/api/app/core/audit/{service.py,models.py}` + `KNOWN_ENTITY_TYPES` registry (Init 0 baseline). FR5-AUDIT-1 adds 16 new action names without contract changes.
  - **Role enum** — `apps/api/app/core/db/models/_enums.py:10-13` (Init 0 baseline). `member` is already enumerated; no enum change required by Init 5.
- **Forward references:**
  - **`epics.md` § Initiative 5** — to be authored in Session D (manual edit per CC §4.2 2C; ~600-800 lines; Epic 6-10 H4 + Stories 6.x-10.x H5). Each Story will cite one or more Decision letters from this section as its architectural anchor.
  - **`sprint-status.yaml`** — to be extended in Session F via `bmad-sprint-planning` with `epic-6` … `epic-10` keys + per-story entries (status `backlog`).
  - **Audit artifacts** — `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md` (E9 close, NFR5-SEC-1), `2fa-recovery-drill-2026-MM-DD.md` (E7 close, NFR5-OBS-2), `cutover-smoke-2026-MM-DD.md` (E10 close, Decision J + NFR5-OBS-2).
- **Memory entries informing decisions:** `feedback_default_to_bmad_workflow.md` (E9 as epic-not-story discipline), `feedback_auto_deploy_dev.md` (Decision K cross-repo cutover commit + `docs/operations.md` deploy-history closing), `feedback_vanilla_bmad_first.md` v2 (monolithic H2-append pattern justification for this manual edit), `feedback_invoke_codex_directly.md` (NFR5-SEC-2 `codex review` countersignature mechanism).

## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Brownfield bug-fix-scope-expansion on Init 0/5 auth surface. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20). Source PRD section: `prd.md` § "Initiative 6" (FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + 7 NFRs). Single Epic E11 with 7 stories.

### Overview

Initiative 5 shipped a default-deny posture in Architecture (Decision C per-route allowlist table specified `current_user` for read-side endpoints) but implementation in `apps/api/app/modules/sot/router.py` shipped without that dependency. Pre-cutover nginx IP allowlist masked the drift. Story 10.3 cutover (sibling configs `5a95b23`) removed the allowlist, exposing the drift externally. Hot-fix `64447ff` was reverted at `be43b92` after Codex P1×2 review caught share-recipient + agent regressions.

Initiative 6 fixes the gap with mechanical enforcement: a pytest enumeration test prevents the drift class from recurring; a share-scoped asset endpoint replaces the implicit `/api/models/{m}/files/{f}/content` anonymous bypass; the frontend shell-level AuthGate makes the auth posture explicit in topology. The bulk of the technical work is enforcement and topology — the auth contract itself is already correctly specified in Init 5 Decision C.

### Decisions In-Scope (M–O)

#### Decision M — Default-deny route enforcement mechanism

- **Realizes:** FR6-AUTH-1, FR6-AUTH-2.
- **Choice:** pytest enumeration test at `apps/api/tests/test_route_enforcement_gate.py` iterates `app.routes` (FastAPI's exposed route table), filters routes with path starting `/api/`, asserts each route's endpoint callable has at least one parameter with a `Depends(current_user | current_member_or_admin | current_admin | ...)` default value OR the route path matches an entry in `_PUBLIC_ROUTES` allowlist. Allowlist is a tuple-of-strings constant in `apps/api/app/main.py` enumerated explicitly:

```python
# apps/api/app/main.py — Initiative 6 Decision M
_PUBLIC_ROUTES: tuple[str, ...] = (
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/register",
    "/api/auth/totp/verify",  # partial-auth step for users mid-2FA-login
    "/api/auth/password-reset/consume",
    "/api/share/{token}",  # resolve
    "/api/share/{token}/files/{file_id}/content",  # share-scoped asset (Decision N)
    "/api/csrf-token",  # if exists, TBD Story 11.1
)
```

The test fails CI on drift with a message like:
```
FAILED: route /api/categories has no auth Depends and is not in _PUBLIC_ROUTES
```
- **Alternatives rejected:** mypy plugin (over-engineering; route table is runtime-introspectable); FastAPI middleware introspecting Depends on first request (delays drift detection to runtime; CI doesn't catch); nginx-level route prefix list (couples app-level auth contract to edge config — exactly the failure mode of Init 5).
- **Rationale:** mechanical, runs in <1s, drift becomes a CI fail not a production privacy regression. The allowlist itself is a single source of truth for "what is anonymous".
- **Cascading:** allowlist updates require a Sprint Change Proposal (FR6-AUTH-2) — this is the procedural gate that catches "let's just add one more public route" creep.

#### Decision N — Share-scoped asset endpoint (hardened per Codex peer-grill 2026-05-20)

- **Realizes:** FR6-SHARE-1, NFR6-OBS-1.
- **Choice:** new endpoint at `GET /api/share/{token}/files/{file_id}/content` in `apps/api/app/modules/share/router.py`. Implementation contract (all six guarantees binding for Story 11.2 — Codex peer-grill 2026-05-20 surfaced and hardened each one; see SCP §3.4.2 + §4.2.2 for the verbatim verdict):

```python
# apps/api/app/modules/share/router.py — Initiative 6 Story 11.2
import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.db.models import Model, ModelFile, ModelFileKind
from app.core.db.session import get_session
from app.modules.share.service import ShareService


@router.get("/{token}/files/{file_id}/content")
async def get_share_asset(
    token: str,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
) -> Response:
    # 1. Token resolve (Redis primary). Uniform 404 on miss — do NOT distinguish
    #    "invalid token" / "expired" / "revoked" externally (timing-distinguishable
    #    responses leak token-state oracle).
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share asset not found")

    # 2. Scope-check BEFORE ETag handling. Scope query MUST include the kind
    #    filter — without it, share for model A would expose `source` (raw .blend)
    #    + `archive_3mf` files that share-resolve NEVER surfaced. Soft-deleted
    #    models return 404 (no leak via Model.deleted_at IS NOT NULL).
    file_row = session.exec(
        select(ModelFile)
        .join(Model, Model.id == ModelFile.model_id)
        .where(
            ModelFile.id == file_id,
            ModelFile.model_id == record.model_id,
            ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print, ModelFileKind.stl]),
            Model.deleted_at.is_(None),
        )
    ).first()
    if file_row is None:
        # Uniform 404 — wrong model / wrong kind / missing file / soft-deleted model
        # all produce the same response shape (no IDOR enumeration leak).
        raise HTTPException(404, "Share asset not found")

    # 3. Audit emission BEFORE serving. Captures access intent regardless of disk
    #    outcome. token_hash = sha256(token), NEVER clear token.
    record_event(
        session,
        action="share.asset.fetched",
        actor_user_id=None,
        target_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        target_model_id=record.model_id,
        target_file_id=file_id,
        target_file_kind=file_row.kind.value,
        ip=request.client.host if request.client else None,
    )

    # 4. Serve content with Cache-Control: no-store (override default
    #    "private, max-age=300" from sot/router.py:212; prevents revoked tokens
    #    from serving cached content for up to 300s post-revoke).
    return _serve_file_content(
        file_row,
        download=download,
        cache_control="no-store",
    )
```

`share-router.py` refactor — share-resolve handler emits share-scoped URLs:
- Line 55: `images = [f"/api/share/{token}/files/{fid}/content" for fid in image_files]`
- Line 59: `thumbnail_url = f"/api/share/{token}/files/{model.thumbnail_file_id}/content"`
- Line 70: `stl_url = f"/api/share/{token}/files/{stl_row}/content?download=1"`

`apps/api/app/core/logging.py` MUST extend token redaction regex — current pattern `_TOKEN_URL_REGEX = re.compile(r"\btoken=[^&\s\"']+")` (line 14) matches only query-string tokens; share-asset endpoint exposes token in URL path, so add a second pattern matching `/share/<bearer>/...` (token segment between two slashes after `/share/` or `/api/share/`). Negative-test in Story 11.2: a log record containing `/api/share/abc123/files/.../content` emits with `/api/share/<redacted>/files/.../content`.

- **Alternatives rejected:** see SCP §3.4.2 — (b) query-param `share_token=` on existing `/api/models/...` — recreates dual-mode endpoint that caused 64447ff; (c) HMAC-signed URLs — still hangs anonymous access off `/api/models/.../content`; (d) per-asset Redis signature — less self-explanatory than `/api/share/{token}/files/...`. All Codex-verdicted REJECTED with verbatim rationale in SCP §3.4.2.
- **Rationale:** mirrors `/api/share/{token}` resolve namespace (single anonymous-allowed prefix); scope check + kind filter + soft-delete filter in one DB join; revoke semantics inherit from share-token Redis DEL (no orphan signed URLs to track separately); audit emission uses token hash not clear token; Cache-Control `no-store` prevents post-revoke cached serving; ETag NOT applied to share-asset response (premature ETag-match short-circuit would bypass scope check).
- **Cascading:** `/api/models/{m}/files/{f}/content` endpoint becomes `current_user`-gated via Story 11.1 (no more anonymous access via that path). Share recipients are routed exclusively through `/api/share/...` prefix. Logging redaction extension is a shared-codebase change; pre-merge codex review (NFR6-SEC-3) verifies the regex doesn't over-redact legitimate `/share-something-else/` URL substrings.

#### Decision O — Frontend shell-level AuthGate topology

- **Realizes:** FR6-SHELL-1, FR6-SHELL-2.
- **Choice:** `apps/web/src/shell/AppShell.tsx` evaluates authentication state at mount time. Shape:

```tsx
const _PUBLIC_PATHS = new Set([
  "/login", "/register", "/reset-password", // anonymous routes from Init 5
  // /share/* handled separately because share path is dynamic
]);

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const { pathname, searchStr } = useLocation();

  // 1. Share path bypass (anonymous, already existed Init 0; preserved)
  if (pathname.startsWith("/share/")) {
    return <>{children}</>;
  }

  // 2. Public path bypass (login / register / reset-password — anonymous-allowed)
  if (_PUBLIC_PATHS.has(pathname)) {
    return <>{children}</>;
  }

  // 3. Auth loading state
  if (auth.isLoading) {
    return <LoadingScreen />;  // spinner; no shell chrome
  }

  // 4. Unauthenticated → redirect to login
  if (!auth.isAuthenticated) {
    const next = encodeURIComponent(pathname + searchStr);
    void router.navigate({ to: "/login", search: { next }, replace: true });
    return null;  // brief blank during navigation
  }

  // 5. Authenticated → full shell
  return (
    <div className="flex min-h-screen">
      <ModuleRail />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 pb-16 lg:pb-0">{children}</main>
      </div>
    </div>
  );
}
```

Per-route `<AuthGate>` wrappers (`apps/web/src/routes/catalog/*.tsx` if any exist from Init 5 admin panel) are removed — single source of auth state in shell.

- **Alternatives rejected:** keep per-route `<AuthGate>` (every new module reinvents auth check; multiplies surfaces for the kind of bug 64447ff P2 introduced); TanStack Router `beforeLoad` route guard (couples auth state to TanStack lifecycle in a way that's harder to test); React Suspense-based gating (over-engineering for boolean auth check).
- **Rationale:** single source of truth for auth-vs-anonymous decision; explicit public-path allowlist mirrors backend `_PUBLIC_ROUTES`; ModuleRail + TopBar absent from DOM for anonymous users (operator-aligned UX requirement D-LOCK-5); the `searchStr` fix (P2 from 64447ff codex review) is local to this implementation.
- **Cascading:** AuthGate.tsx remains as a thin wrapper component for legacy callers (if any), but its impl uses `searchStr` not `search`. The component may eventually be deleted in a future cleanup pass once all callers route through shell-level gating.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20).
- PRD section: `prd.md` § Initiative 6 (FR6-* + NFR6-*).
- Epics section: `epics.md` § Initiative 6 (Epic E11 + Stories 11.1–11.7).
- Init 5 Decision C clarifying note (above, after line 1493).
- Memory entries informing decisions: [[invoke-codex-directly]] (Codex peer-grilling for share-asset trade-off Decision N), [[itcm-autonomous-mode]] (frame-shift before drafting), [[auth-boundary-contract-audit]] (explicit enumeration phase for auth-boundary commits + SCP recommendations), [[vanilla-bmad-first]] (monolithic H2-append for this section).

## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Brownfield UX polish on Init 5 admin + account self-service surfaces and Init 0 registration. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 7" (FR7-* + NFR7-*). Single Epic E12 with 5 stories.

### Overview

Initiative 7 stories are primarily component-level changes on shipped frontend surfaces. The only architectural decision is the topology of the new settings hub (Decision Q) — does it become a route-layout wrapper, a flat list-of-cards landing, or a tab-style navigator? Decision below selects the flat list-of-cards landing for minimum coupling to Init 5/6 admin substrate.

### Decisions In-Scope (Q)

#### Decision Q — Settings hub topology

- **Realizes:** FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2.
- **Choice:** flat list-of-cards landing page at `/settings`. Each card links to a sibling route (`/settings/profile`, `/settings/2fa`, `/settings/sessions`). No shared layout component between `/settings` and its children (so `/settings/2fa` continues to render `Settings2faPage` as a full-page component, not as a tab body). User-menu in `TopBar.tsx` gains a "Settings" link routing to `/settings`.
- **Alternatives rejected:**
  - Route-layout wrapper (`/settings/_layout.tsx` with persistent sidebar nav) — over-engineering for three sections; couples sibling layouts that have distinct content needs (2FA enrollment flow has wizard-style steps; sessions has table; profile has form).
  - Tab-style navigator (one route, three tab panels) — breaks deep-link semantics; current direct URL `/settings/2fa` would either need a query-param shim or break existing 2FA enrollment links from notifications/emails.
- **Rationale:** simplest topology that solves discoverability. Cards-on-landing is consistent with the existing `/admin` admin landing pattern (Init 5 E8). Three sections is the project's complete settings surface for the near term; future additions (notification preferences, API tokens, etc.) follow the same card-add pattern.
- **Cascading:** none. No new shared components, no schema changes, no new backend endpoints required for the hub itself (children's endpoints already exist).

## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Brownfield additive — thumbnail pipeline on Init 0 catalog read-surface. Source SCP: `sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 8" (FR8-* + NFR8-*). Single Epic E13 with 2 stories.

### Overview

Initiative 8 introduces an image transformation layer between the existing `portal-content` volume binary storage and the `/api/models/.../content` read endpoint. The pipeline is on-upload (deterministic, cacheable, no per-request CPU spike) rather than on-the-fly. The variant is served via query param on the existing endpoint (no new route prefix, no nginx changes). Decision P below documents the pipeline shape, format/quality choice, and backfill posture.

### Decisions In-Scope (P)

#### Decision P — On-upload thumbnail pipeline, WebP @ q80, 800px longest side, query-param variant

- **Realizes:** FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1.
- **Choice:** thumbnail generation triggered as an arq task enqueued from the admin model-file create endpoint when the uploaded file's kind is `image`. Task runs in the existing `apps/api/app/workers/__init__.py` `WorkerSettings` (NOT the dedicated render worker — thumbnails are I/O-light Pillow CPU and don't warrant the matplotlib-heavy render-worker isolation). Output filename convention: `<original-filename>.thumb.webp` co-located with original in `portal-content`. The asset content endpoint `GET /api/models/{model_id}/files/{file_id}/content` accepts an optional `variant=thumb` query param; when present and the thumbnail file exists, serves the WebP variant; when absent, serves original. Frontend catalog cards request via `srcSet` with `?variant=thumb`. Detail view continues to request full-res original (no srcSet).
- **Backfill:** one-shot script `infra/scripts/backfill-thumbnails.sh` walks `ModelFile` rows of `kind=image` AND missing thumbnail, enqueues the same arq task per row. Operator-supervised (not part of `deploy.sh` automation). Idempotent (skip if thumbnail already exists).
- **Alternatives rejected:**
  - On-the-fly thumbnail generation (resize per request) — per-request CPU spike, harder to cache, defeats the latency-budget benefit.
  - New dedicated `workers/thumbnail/` sibling worker — over-engineering for a thin Pillow task; the existing arq worker has spare cycles.
  - JPEG @ q85 instead of WebP @ q80 — WebP gives 25-35% smaller files at equivalent visual quality; JPEG fallback unnecessary for the project's user base per NFR8-COMPAT-1.
  - Separate thumbnail endpoint `/api/models/.../thumb` — query-param variant keeps the existing route shape and avoids nginx config touches.
- **Rationale:** simplest pipeline that hits NFR8-PERF-1's 50 KB payload budget for typical phone-photo inputs. On-upload is deterministic and cache-friendly. Query-param variant rides existing route + middleware + auth posture (no new public route, no `_PUBLIC_ROUTES` allowlist change — preserves Init 6 default-deny).
- **Cascading:** Pillow ≥11 must be in `apps/api/pyproject.toml` (verify during Story 13.2 spec; per project-context.md L24 it's confirmed in worker but not necessarily API). Backfill script must be run once post-Story-13.2-deploy by operator. No nginx, no auth, no schema changes.

## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Brownfield test-infrastructure cleanup. Source SCP: `sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 9" (FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1). Single Epic E14 with 3 stories.

### Overview

Initiative 9 is test-infrastructure-only work. **No new architectural decisions, no product-architecture changes, no schema changes, no auth contract changes.** Init 0–6 product architecture is load-bearing for the fixes; Initiative 9 does not modify it.

The three stories operate within existing test-infrastructure contracts:

- **Story 14.1** operates within the vitest + @testing-library/react contract documented at `apps/web/vitest.setup.ts` (global `afterEach(cleanup)`) and `apps/web/vitest.config.ts` (jsdom env, `globals: false`). No contract changes.
- **Story 14.2** operates within the pytest + SQLModel + fakeredis contract documented at `apps/api/tests/conftest.py` (`_isolated_db`, `_patch_arq_pool`). Story 14.2 may tighten fixture scoping or add explicit teardowns, but does NOT modify the broader test isolation architecture.
- **Story 14.3** operates within the husky + playwright + check-all.sh contract documented at `apps/web/.husky/_check-baseline-review.mjs` + `_check-visual-coverage.mjs` and the visual-regression Playwright config at `apps/web/tests/visual/playwright.config.ts`. Story 14.3 may add instrumentation logging or fix a port/SHA/cache divergence, but does NOT modify the baseline-acceptance gate or visual-coverage contract.

This section is listed in the architecture document for Initiatives Index completeness; there are no design decisions to record.

## Initiative 10 — Operator Polish Batch

**Status:** 🚧 planning (started 2026-05-22). Source PRD: `prd.md` § "Initiative 10" (FR10-* + NFR10-*). Source SCP: `sprint-change-proposal-2026-05-22-init10.md`. Three epics E15+E16+E17 with ~13 stories.

### Overview

Initiative 10 introduces **3 architectural decisions** (L, M, N) on top of the Init 0–6 baseline. None of the existing architectural decisions (Init 1–6 A–O) is invalidated. Epic 15 (Test Health) has NO architectural decisions — test-infrastructure-only per NFR10-SCOPE-1 (carries Init 9 NFR9-SCOPE-1 precedent with explicit boundary-carve for the Story 15.1 prod-side race possibility — see PRD NFR10-SCOPE-1). Epic 17 (UX + TB Sweep) has NO architectural decisions — CSS-only + doc commits.

The three decisions all reside in Epic 16:

- **Decision L** — ModelNote bilingual schema migration (Story 16.1)
- **Decision M** — Anonymous share-link frontend route shell (Story 16.3)
- **Decision N** — Admin manual-add model + file upload write surface (Stories 16.4 + 16.5)

### Decision L — ModelNote bilingual schema migration (forward-only Alembic)

**Context.** ModelNote currently stores descriptions as a single `body: str NOT NULL` column with `kind: NoteKind` discriminator (`apps/api/app/core/db/models/_entities.py:196-211`). The portal serves a bilingual PL/EN UI (i18next + react-i18next 15), but the description field has no language split — operators landing models from EN-language sources (Printables, Thingiverse) write English content; Polish UI users see English fallback. Operator decision §1.1: migrate to `body_pl: str | None` + `body_en: str | None` schema. Backfill existing rows to `body_en` (English source-dominant per current catalog state).

**Decision.** Forward-only Alembic migration:

1. Add `body_pl: str | None` column (nullable).
2. Add `body_en: str | None` column (nullable).
3. Backfill `UPDATE model_note SET body_en = body WHERE kind = 'description'` (other note kinds — `print_settings`, etc. — retain `body` until separate scope).
4. Drop legacy `body NOT NULL` constraint on `kind='description'` rows. Initial implementation: keep `body` column non-null for non-description notes; alternative: split into two tables.

**Implementation shape (story-level fidelity in epics.md):**

- **Schema:** `ModelNote` gains `body_pl: str | None` + `body_en: str | None` SQLModel fields. The existing `body: str` field is retained for backward-compat on non-description notes (`kind='print_settings'` etc.) — a future Init can decide whether to bilingual-split other note kinds too. Description-kind rows after migration must have `body_pl OR body_en NOT NULL`; database-level CHECK constraint optional, deferred to runtime validation in Pydantic layer.
- **Backfill:** Inside the Alembic up() migration as part of the atomic schema change — not a separate post-deploy script. Pattern: `op.execute("UPDATE model_note SET body_en = body WHERE kind = 'description' AND body_en IS NULL")`. After backfill, leave `body` column populated for non-description rows.
- **API surface:** `app.modules.sot.admin_schemas` adds `body_pl` + `body_en` to NoteRead/NoteCreate/NoteUpdate. `ModelNoteUpdate` request accepts either field; legacy `body` field for description kind is rejected with 400 (deprecation enforced).
- **Frontend rendering:** `DescriptionPanel.tsx` resolves to `body_pl` if `i18n.language === 'pl'` AND `body_pl IS NOT NULL`, fallback to `body_en`, else empty-state. Editor UI in admin shows tabbed PL / EN editor.

**Rollback path.** Down-migration: drop `body_pl` + `body_en` columns; restore description rows to legacy `body` (use whichever bilingual field had content, prefer `body_en` for null-vs-not-null determinism). Acceptable data loss: `body_pl` content written between forward migration and rollback is lost. Rollback is not online-safe — requires <2-min downtime.

**Cascading.** Backfill script in migration up() must complete in <60s for current catalog size (<200 models); larger catalogs may need batching. No nginx config impact (route shape unchanged). No auth contract impact (admin/owner auth on PUT unchanged). No worker impact.

### Decision M — Anonymous share-link frontend route shell

**Context.** Init 6 Decision N shipped the `/api/share/<token>/*` share-scoped asset endpoint (`apps/api/app/modules/share/router.py:70-89`). Backend asset paths exist + work anonymously (`/api/share/<token>/files/<fid>/content`, `/api/share/<token>` GET model detail). But no frontend route consumes them — `apps/web/src/routes/` has no `share/` subdirectory. Members can mint share-tokens via `POST /api/admin/share` (Init 5 FR5-MEMBER-1) but the recipient has no UI to view the model. Feature is half-shipped.

**Decision.** Add a TanStack Router file-route `apps/web/src/routes/share/$token.tsx` that:

1. **Renders WITHOUT `AuthGate`.** Anonymous visitors must reach the route directly; no auth-state consultation. Route component renders `AnonymousShareView` directly, no fallback.
2. **Has NO ModuleRail** — operator decision: anonymous viewer doesn't see left nav. Layout uses a custom slim chrome (logo TopBar only) instead of the standard `<AppShell>`.
3. **Reuses existing model-detail components** — `Viewer3DInline`, `DescriptionPanel`, `FilesTab` (filtered to download-only — no upload affordances visible). Data fetched via `useQuery` calls to `/api/share/<token>/*` endpoints with NO cookies sent (route MUST NOT call `api()` since `api()` attaches `X-Portal-Client: web` CSRF header which is intended for authenticated flows; instead use `fetch` directly with `credentials: "omit"`).
4. **Member-side UI** lives at: (a) model-detail page — share-link generation dialog with TTL dropdown (1d / 3d / 7d) visible to `current_member_or_admin`; (b) `apps/web/src/routes/settings/share-links.tsx` — list of member-minted tokens + revoke CTA. Both consume existing `/api/admin/share/*` endpoints.

**Implementation shape:**

- **Anonymous-route component:** `apps/web/src/modules/catalog/components/AnonymousShareView.tsx`. Receives `token` from route params. Renders `<div className="min-h-screen flex flex-col">` → minimal logo TopBar + centered content layout. `<AuthGate>` NOT present in route tree.
- **API client:** dedicated `shareApi.ts` module in `apps/web/src/lib/` using bare `fetch` (NOT `api()`). Wraps `/api/share/<token>/*` endpoints. Returns same shapes as existing `ShareModelView` from backend.
- **Member share-gen UI:** dialog component `apps/web/src/modules/catalog/components/ShareLinkDialog.tsx`. Form: TTL select (1d/3d/7d enum; not free-form), description (optional). On submit: `POST /api/admin/share` → returns `{url, token, expires_at}` → show generated link with copy-to-clipboard button.
- **My share links page:** route `apps/web/src/routes/settings/share-links.tsx`. Table listing all member's active share-tokens (model name link, created_at, expires_at, revoke button). DELETE `/api/admin/share/{token}` on revoke. Pagination if >20 (matches Init 7 settings-hub pagination pattern).

**Auth posture (CRITICAL).** Anonymous share-link route MUST NOT:

- Call `/api/auth/me` (would attempt to set anonymous user as the share-token's actor).
- Mount within the `<AuthGate>` provider tree (would force authentication).
- Send any cookies to `/api/share/*` endpoints (would risk auth-leak — although backend already public per Init 6 Decision N, defense-in-depth).
- Expose any admin-mutating UI elements (`<UploadFile>`, `<EditModel>`, etc. components must be conditionally rendered behind a `if (currentUser?.role === 'admin')` guard — which evaluates false on anonymous routes).

Story 16.3 acceptance includes Codex auth-boundary contract audit per memory [[auth-boundary-contract-audit]].

**Cascading.** No new backend endpoints (Init 6 Decision N already shipped). Nginx config unchanged (Init 5 `_PUBLIC_ROUTES` allowlist already covers `/share/*` + `/api/share/*` per E10 cutover). Frontend route alone.

### Decision N — Admin manual-add model + file upload write surface

**Context.** Today, model creation flows through `POST /api/sot/models/import-from-source` (agent flow — accepts source URL + auto-derives fields). No admin UI for manual model creation; operator-Ezop relies on the agent flow even for self-curated models. Operator decision §1.1: add admin-only manual-add UI for: (a) creating new models from scratch with bilingual fields + uploaded files; (b) uploading additional files to existing models (STL revision, additional images, thumbnail replacement).

**Decision.** Two new admin-only endpoints, both `multipart/form-data`:

1. **`POST /api/admin/models`** — create new model. Manifest as JSON in `form.manifest` field; files as `form.thumbnail`, `form.images` (multiple), `form.files` (multiple).
2. **`POST /api/admin/models/{id}/files`** — append/replace files on existing model. Single file per request with `form.kind` + `form.file`. Replace semantics for primary STL/STEP/F3D; append for images.

**Implementation shape:**

- **Router:** new file `apps/api/app/modules/sot/admin_router_create.py` mounted under existing `apps/api/app/modules/sot/admin_router.py` prefix `/api/sot/admin`. Two endpoint functions:

  ```python
  @router.post("/models", status_code=201)
  async def create_model_manual(
      manifest: ModelManualCreate = Form(...),  # JSON-as-form-field
      thumbnail: UploadFile | None = File(None),
      images: list[UploadFile] = File(default=[]),
      files: list[UploadFile] = File(default=[]),
      current: Annotated[User, Depends(current_admin)],
      session: Annotated[Session, Depends(get_session)],
  ) -> ModelDetail: ...

  @router.post("/models/{model_id}/files", status_code=201)
  async def upload_model_file(
      model_id: uuid.UUID,
      kind: FileKind = Form(...),
      file: UploadFile = File(...),
      current: Annotated[User, Depends(current_admin)],
      session: Annotated[Session, Depends(get_session)],
  ) -> ModelFileRead: ...
  ```

- **Pydantic schemas:** `ModelManualCreate` mirrors `ModelCreate` (existing agent-flow shape) with bilingual fields explicit (`name_pl`, `name_en`, `description_pl`, `description_en`); `FileKind` enum new (`stl`, `step`, `f3d`, `image`, `thumbnail`).
- **Existing patterns reused:** thumbnail-render arq job enqueue (`enqueue_thumbnail_render(model_id, file_id)`); audit-log via `record_event(action='sot.model.create_manual', ...)`; soft-delete unchanged; slug generation reuses existing helper.
- **Frontend:**
  - `apps/web/src/routes/admin/models/new.tsx` — form page with multi-step UI (manifest fields → file uploads → submit).
  - `apps/web/src/modules/catalog/components/FileUploadDialog.tsx` — dropzone dialog (visible to admin only on model-detail page) for individual file upload.
  - Reuse existing `@uploadthing/react` or native HTML5 file inputs (verify what's in repo; if neither, add minimal native input + form data construction).
- **Auth:** `current_admin` on both endpoints. Member role does NOT get these (operator decision §1.1).
- **Member fall-through:** existing agent flow (`/api/sot/models/import-from-source`) stays as the member path. No member-side UI for manual add.

**Cascading.** No new tables. No new env vars. Soft-delete unchanged. Thumbnail-render arq worker unchanged. `verify-symbolication.sh` deploy chain unchanged. Audit-log adds 2 new action names (`sot.model.create_manual`, `sot.model.upload_file`) to `KNOWN_ENTITY_TYPES` — extends the existing registry, doesn't replace it. Per FR10-MANUAL-ADD-1 + FR10-MANUAL-ADD-2 NFR validation: file size limits (max 100MB per file STL/STEP/F3D; max 10MB per image) enforced at FastAPI layer via `UploadFile.size` check; rejection with 413 Payload Too Large.

### Cross-references

- PRD: `prd.md` § Initiative 10 (FR10-DESC-1, FR10-SHARE-ANON-1+2, FR10-MANUAL-ADD-1+2 link to Decisions L+M+N respectively).
- Epics: `epics.md` § Initiative 10 (Epic 16 stories 16.1, 16.3, 16.4+16.5 implement these decisions).
- SCP: `sprint-change-proposal-2026-05-22-init10.md`.
- Memory entries informing decisions: [[feedback_auth_boundary_contract_audit]] (Decision M frontend auth posture), [[feedback_frontend_visual_verification]] (all UI stories under these decisions carry the gate).

## Initiative 11 — Triage Quick Wins Bundle

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11. Single epic E18 with 5 stories.

### Overview

No architectural decisions in this initiative — Epic 18 is pure quick-fix triage (TB-025, TB-028, TB-014, TB-021, TB-016 closures). Per-story details in source SCP. No new architectural surface; all stories patch existing systems.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11.
- PRD: `prd.md` § Initiative 11 (FR11-* + NFR11-*).
- Epics: `epics.md` § Initiative 11 (Epic 18 stories 18.1-18.5).

## Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening

Init 10 Story 16.3 shipped the minimum-viable anonymous share viewer (static "Download STL" button only). Operator-aligned 2026-05-23: bring the surface to **member-view-scoped parity** (carousel, file list, description, STL preview renders, 3D viewer — all read-only, no member-only actions like print-request which reserve for future capabilities). At the same time, the public anonymous endpoint is now a real DDoS attack surface; ship security hardening (rate-limit + throughput cap + threat model doc) BEFORE expanding the UX surface.

Carousel framing: "the catalog detail page a logged-in member would see for this one shared item, minus member-only actions reserved for future capabilities" — NOT "admin view minus admin actions". Admin will become a strict superset of member with extra capabilities (analytics, system config, force actions); anonymous share recipients see only the catalog-detail surface scoped to the shared item.

### Decision Q — Anonymous share request-rate middleware (Story 19.1)

**Decision:** FastAPI middleware on `/api/share/{token}/*` capping requests at **60 per 60 seconds per (token, IP) tuple**. Soft-alert log at 30 (half-cap). Redis-backed sorted-set sliding window (existing `RateLimitMiddleware` class from Story 6.6 reused).

**Why FastAPI middleware (not Nginx):**
- Can hash the token + log structured events with `event.action=share.ratelimit.soft_alert` at `app.share.ratelimit` logger.
- Per-`(token_hash, ip)` keying needs URL path parsing to extract the token; Nginx `limit_req_zone` keys are usually just `$binary_remote_addr` or `$request_uri`. Doing the keying app-side is cleaner.
- Stays in lockstep with the four existing rate-limit middlewares (login/refresh/register/share) — single class, four call sites.

**Why per-(token, IP) tuple keying:**
- Token-only: too coarse for "one operator, many recipients" — would starve concurrent legitimate viewers if one recipient gets DOS-ed.
- IP-only: too narrow for "single recipient legitimate use" of multiple shared links — would mix legit recipients sharing a NAT/VPN gateway.
- Tuple: every (token, IP) pair gets its own bucket. Legitimate viewer browses carousel + STL + file list under the cap; rogue IP scraping the token gets stopped at 60/min.

**Why hash the token in the Redis key:**
- The share token IS the credential. Redis logs key patterns under DEBUG, snapshots can be dumped, monitoring/observability pipelines surface key names. Storing the raw token cleartext is a leak vector.
- 16-byte sha256 prefix (64 bits) gives collision-free bucketing with no leak.

**Threshold rationale (operator-calibrated 2026-05-23):**
- 60 req/min = 1 req/sec rolling. Legit viewer: ~5-15 requests per minute (carousel + STL init + file list + maybe a download click). Cap is ~4× legit headroom.
- Soft-alert at 30 (half-cap): logs `share.ratelimit.soft_alert` for observability — operator monitors whether real traffic creeps toward the cap.
- Window 60s: short enough that a temporary spike (tab restore loading carousel + viewer concurrently) doesn't persistently lock out a legit recipient.

**Key formula:** `ratelimit:share_anon:token:{sha256_prefix_16}:ip:{client_ip}` (scope prefix `share_anon`).

**Endpoints affected:** all paths matching `^/api/share/.+` (regex extracts the token from path segment 3). Path `/api/share/` itself (no token) returns None from key_fn and bypasses the middleware.

**Response shape on cap:** HTTP 429 + `Retry-After: 60` header. Standard sliding-window — retry-after = window duration, NOT seconds-to-midnight (contrast with Decision H share-creation cap, which uses UTC-day rollover).

### Decision R — Edge Nginx throughput cap (Story 19.2)

**Decision:** `location ~ ^/api/share/[^/]+/files/` block in `~/repos/configs/nginx/3d.ezop.ddns.net.conf` carrying `limit_rate 2m;` (2 MB/s per stream) + `limit_conn share_anon_conn 5;` (5 concurrent per IP). Zone defined in `~/repos/configs/nginx.conf` http context: `limit_conn_zone $binary_remote_addr zone=share_anon_conn:10m;`.

**Why Nginx edge (not app-level streaming throttle):**
- Nginx is byte-stream-cap-efficient at edge; app-level throttle would slow every download for every share recipient even when no contention exists.
- Per-IP concurrent-connection cap is Nginx-native (`limit_conn_zone` + `limit_conn`) and cheap.
- Edge cap defends the outbound pipe BEFORE the app even sees the bytes — relevant for raw-stream attack class (range-request flooding).

**Why per-stream 2 MB/s + per-IP 5 concurrent (operator-calibrated 2026-05-23):**
- 2 MB/s per stream: large STL (~50 MB) downloads in ~25s — acceptable UX. Faster would let single recipient burn pipe; slower would annoy legitimate downloads.
- 5 concurrent per IP: covers carousel image loads (parallel) + STL viewer (1 stream) + 2-3 file downloads. Power-user pattern. Above 5, returns HTTP 503.
- Together: max 10 MB/s outbound per IP — bounded blast radius for compromised tokens.

**Coverage:** ONLY `/api/share/{token}/files/...` paths (file content downloads). Carousel image / STL preview render fetches use the same path pattern (via Decision T file-list endpoint) so they ALSO cap to 2 MB/s + 5 concurrent. The resolve `GET /api/share/{token}` returning JSON metadata, and the file-list `GET /api/share/{token}/files` returning paginated list — NOT under throughput cap (only Decision Q request-rate).

**Coordination with Decision Q:** Decision Q (app) gates request count; Decision R (edge) gates byte stream and concurrent connections. Layered: simple scrape loop stopped by Q at 60 req/min; single-stream pipe-flood stopped by R at 2 MB/s. Together: max sustainable damage from compromised token = 2 MB/s × 5 streams = ~10 MB/s — manageable on residential uplink.

**Deploy:** changes in two configs-repo files (sync.sh deploys both to edge proxy). Operator-manual step per [[feedback_collaboration_division]]; not autonomous infra deploy. Pre-deploy: `nginx -t` syntax check + graceful reload (`nginx -s reload`).

### Decision S — STL preview render pipeline (Story 19.6)

**Decision:** New arq task `render_stl_previews(model_file_id)` in `workers/render/` consuming a `ModelFile` of kind `stl` and producing 4 image previews (iso / front / side / top views) stored as new `ModelFile` rows with `image_kind = "stl_preview"`. Alembic migration 0019 extends the `ModelFileKind` enum.

**Why 4 fixed views (iso/front/side/top):**
- iso: 3/4-perspective for "shape at a glance".
- front/side/top: orthographic, mirror the manufacturing-drawing convention.
- Standard set lets recipients quickly grok the model without 3D viewer dependency (good for share-view-without-3D-viewer-yet during Story 19.5 ship before 19.7).

**Why pre-render (not on-the-fly):**
- Trimesh + matplotlib render is ~5-30s for medium meshes. Anonymous recipient shouldn't wait.
- Pre-rendered images stream from disk at edge-capped throughput.

**Trigger pattern:** lazy on first `GET /api/share/{token}/files` if STL exists but previews missing. Idempotency guard: `(model_id, image_kind=stl_preview, position)` uniqueness check before insert.

**Storage:** existing `ModelFile` storage (`portal-content` volume). Filename pattern: `<stl_basename>_iso.png`, `_front.png`, `_side.png`, `_top.png`. PNG format (better than JPEG for STL line-art renders — no edge artifacts).

**Render parameters:**
- Matplotlib camera positions: iso = (elev=45°, azim=45°), front = (0°, 0°), side = (0°, 90°), top = (90°, 0°).
- Lighting: single directional light at 45° elevation, ambient ~30% (mirror existing thumbnail-render pipeline).
- Output size: 1024×1024 px (consistent with thumbnail variants).

**Worker integration:** new arq function in `workers/render/`, dispatched via `request.app.state.arq.enqueue_job("render_stl_previews", model_file_id)` from share file-list endpoint. Idempotent (existing renders skipped on re-enqueue).

### Decision T — Share view file list endpoint (Story 19.4)

**Decision:** `GET /api/share/{token}/files` returning `PaginatedFileList[ShareFileListEntry]` — share-scoped URLs per Init 6 Decision N pattern. Anonymous (no auth beyond the valid share token resolving the model).

**Endpoint signature:**
```
GET /api/share/{token}/files?page=1&page_size=50
Response: 200 {
    items: [{
        id, kind, original_name, mime_type, size_bytes, position,
        content_url: "/api/share/{token}/files/{file_id}/content",
        created_at,
    }, ...],
    total, page, page_size,
}
```

**Why share-scoped URLs in response (Init 6 Decision N pattern):**
- Recipients have NO access to `/api/models/{id}/files/{file_id}/content` (Init 6 default-deny). Share-scoped `/api/share/{token}/files/{file_id}/content` is the only path that resolves anonymous.
- File-list response embeds the right URL shape directly so the FE doesn't need to construct it.

**Why admin auth NOT consulted:**
- Share token IS the auth. Decision M (Init 6) carved `/api/share/*` out of the `_PUBLIC_ROUTES` allowlist precisely so anonymous recipients can use these endpoints.
- Adding `Depends(current_user)` would break the public bypass — caught by Init 6 NFR6-SEC-1 hard gate.

**Pagination:** standard 50/page default with 1-200 range. STL files + images + prints + stl_previews — most models have <50 files but pagination is available.

**Coverage:** all files attached to the shared model, regardless of `image_kind`. Includes `stl_preview` files (Decision S output) so the anonymous viewer renders iso/front/side/top thumbnails alongside the carousel.

### § Threat vectors enumerated (Story 19.3 per [[feedback_security_vector_enumeration]])

The anonymous `/api/share/{token}/*` surface MUST defend against the following vectors. Each story under Init 12 MUST be reviewed against this list before merge; each subsequent share-related story (future Init 13+) MUST re-validate that no new vector slipped in.

**1. Cookie-sending vectors on `/api/share/{token}/*` browser fetches.**

`<img src>`, `<a href download>`, `<link rel="preload">`, `<script src>`, `<source srcset>` — all send same-origin cookies by default. If a logged-in admin opens a share link in the same tab, the browser attaches `portal_access` + `portal_refresh` cookies to every asset fetch. The share endpoint MUST NOT trust those cookies (Init 6 NFR6-SEC-1), but mere transmission to the server creates log noise + potential leak vectors via referer / error responses.

Mitigations:
- Init 10 Story 16.3 migrated `<img>` to `fetch → blob → object URL` anchors — verified credentialless.
- STL viewer assets (Story 19.7) MUST inherit the same fetch-blob pattern via Init 13 Story 20.3 `Viewer3DInline.srcOverride`.
- New file-list endpoint (Decision T) response URLs are share-scoped; FE consumes via `fetch(url, { credentials: "omit" })` NOT via direct `<img src>` attribute.
- TB-023 (Init 14 Story 21.2) pytest `anonymous_client` fixture + Playwright `assertCredentialless` helper assert maszynowo: no `Set-Cookie` in response, no `Cookie` in outgoing request for every `/api/share/<token>/*` exercise.

**2. Auth-state-consultation points (AuthProvider `/api/auth/me`).**

The SPA's `AuthContext` polls `/api/auth/me` on mount + route changes to determine `currentUser`. On the anonymous share route, this poll triggers an authenticated request even though the route is supposed to be credentialless.

Mitigations:
- Init 10 Story 16.3: AuthProvider explicitly skips `/auth/me` when route starts with `/share/`. Reactive via monkey-patched `history.pushState` + custom `routechange` event so SPA-nav into /share/ ALSO detects the route change.
- Init 12 Stories 19.5/19.7 MUST verify the skip still fires when the share route mounts heavier components (Viewer3DInline, ModelGallery).
- Tests: TB-023 fixture asserts NO `/auth/me` request fires on `/share/*` page load.

**3. Browser-default-credentials behaviors (resource-element vs `fetch`).**

`<a download>` clicks default to `credentials: "include"` (same-origin). `fetch()` defaults to `credentials: "same-origin"` (also includes cookies). Explicit credentialless on same-origin requires:
- For fetch: `fetch(url, { credentials: "omit" })`.
- For `<img>`: NO native way; use fetch-blob workaround.
- For `<a download>`: NO native way; either fetch-blob+anchor pattern OR accept cookies-included request.

Mitigations:
- All share-view binary fetches go through `fetch(url, { credentials: "omit" })` then convert to blob + object URL.
- Anchor `<a download>` for STL keeps `credentials: "include"` because no native escape — but backend `/api/share/{token}/files/{file_id}/content` tolerates cookies (Init 6 Decision M short-circuit allows).

**4. SPA reactivity gotchas.**

TanStack Router navigates without full reload. If AuthProvider polled `/auth/me` once at initial mount, it has stale data when user navigates TO `/share/` from a logged-in catalog detail. SPA-aware auth-state consult must re-evaluate on navigation.

Mitigations:
- Init 10 Story 16.3 monkey-patched `history.pushState` to dispatch a custom `routechange` event AuthProvider listens to.
- Init 12 Stories 19.5/19.7 MUST verify AuthProvider skip still fires on SPA-nav (not just full reload).

**5. Rate-limit bypass attempts.**

Attacker controlling token + multiple IPs (proxy/botnet) can bypass per-IP rate limits. X-Forwarded-For spoofing: client supplies `X-Forwarded-For: 1.2.3.4` and Nginx propagates it as `X-Real-IP` → key_fn sees the spoofed IP not the real one.

Mitigations:
- Nginx `set_real_ip_from 192.168.2.180` (Init 6 Story 6.6 hardening): ONLY web nginx trusted to set X-Real-IP. Direct caller's XFF discarded; `$remote_addr` (actual TCP-layer peer) propagated.
- Botnet / multi-IP attack: out of scope for app-layer rate limit. Decision R per-stream throughput cap bounds damage even of multi-IP attack (each connection still capped at 2 MB/s × 5 streams per IP = max 10 MB/s per IP × N IPs).
- Token rotation: if a token is observed under attack, operator can revoke via existing share-link management UI (Init 10 Story 16.3 member surface).

**6. Token leak vectors via logs / referrers / outbound resources.**

- Log lines containing `path=/api/share/<token>/files/<file_id>/content` leak token to log aggregators.
- HTTP `Referer` header on outbound third-party requests leaks token via referer.
- Token in `<a href>` visible on copy-link from browser context menu.

Mitigations:
- Logging: existing `TokenRedactionFilter` redacts `token=<value>` patterns; Story 19.3 acceptance: extend to catch URL-path tokens (`/share/<token>/`).
- Outbound third-party resources: share view MUST NOT load external scripts/styles (current state: no externals on /share/<token> page — keep invariant).
- Browser-context-leak: token in URL unavoidable for link-share UX. Mitigation: short TTL (Init 10 Story 16.3 cap = 7 days max) bounds the leak window.
- Recipient-driven leak (recipient shares the link in another channel): operator-acknowledged risk; out of code-side scope.

### Cross-references

- PRD: `prd.md` § Initiative 12 (drafted during Story 19.1 spec; NFR12-DDOS-RATE-1 / NFR12-DDOS-THROUGHPUT-1 / NFR12-THREAT-MODEL-1 / FR12-SHARE-* link to Decisions Q/R/S/T respectively).
- Epics: `epics.md` § Initiative 12 (Epic 19 stories 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7 implement these decisions).
- SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 12; operator-calibration captured 2026-05-23 via AskUserQuestion (security-first priority, 60 req/min cap, 2 MB/s + 5 concurrent per IP, carousel = member-view-scoped).
- Memory entries informing decisions: [[feedback_security_vector_enumeration]] (§ Threat vectors enumeration mandatory), [[feedback_auth_boundary_contract_audit]] (Decision M frontend auth posture carry-forward), [[feedback_codex_model_routing]] (gpt-5.5 heavy/security class for 19.1+19.2+19.3+19.7 reviews), [[feedback_voice_heavy_dedicated_grilling]] (Init 12 4-question grilling preceded story drafts), [[reference_external_test_source]] (Story 19.2 parallel-stream verification via ezop-kbk).

## Initiative 13 — Catalog UX Uplift

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13.

### Decision U — Add Model CTA modal-over-route shape (Epic 20 / Story 20.2)

**Decision:** Admin Add Model CTA renders as toolbar button in `/catalog` page top-right (admin-only via AuthGate); clicks open a shadcn Dialog wrapping the existing `/admin/models/new` form (extracted to reusable `AddModelForm` component with `compact` prop). Modal-over-route chosen over inline-form OR navigate-to-route per operator AskUserQuestion 2026-05-23: modal preserves catalog context (back-button doesn't dump to a different surface) AND the form is heavy enough that an inline expanded panel would dominate the toolbar visually.

**Shape:**
- `AddModelForm.tsx` — reusable form component (renamed from previous inline form; `compact` prop tunes spacing).
- `AddModelModal.tsx` — Dialog wrapper consuming AddModelForm; close-on-success + state-reset-on-close (Story 20.2 round-2 fix-up).
- `AddModelButton.tsx` — admin-gated CTA button; opens modal.
- `/admin/models/new` route refactored to consume the same AddModelForm (single source of truth).

### Decision V — srcSet retina drop (Epic 20 / Story 20.1)

**Decision:** Remove `${thumbUrl} 1x, ${fullUrl} 2x` srcSet candidate from ModelCard + CardCarousel. Retina users were burning bandwidth loading full-resolution originals as the 2x candidate. Trade-off: post-Story-20.1, retina catalog cards may appear slightly less crisp because browser scales the 1x WebP thumb up. Operator accepted the trade-off (catalog list LOAD time matters more than retina-card-crispness).

Init 16 TB-037 gallery tier (Decision W) ULTIMATELY supersedes this — the gallery middle-tier covers retina detail-page main-frame needs at appropriate bandwidth.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13.
- PRD: `prd.md` § Initiative 13 (FR13-CATALOG-* link to Decisions U + V).
- Epics: `epics.md` § Initiative 13 (Epic 20 stories implement these decisions).

## Initiative 14 — Test Infrastructure Hardening

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14.

### Overview

No new architectural decisions — Init 14 is test-infrastructure hardening only. Story 21.2 (credentialless test fixture) adds maszynowo enforcement of the existing NFR10-SHARE-SECURITY-1 contract via the new `make_anonymous_client` helper + `assert_no_set_cookie_in_response` assertion. Composition layer (helper-not-fixture) explained in source SCP.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14.
- PRD: `prd.md` § Initiative 14 (FR14-TEST-CREDENTIALLESS-1).
- Epics: `epics.md` § Initiative 14 (Epic 21 stories 21.1-21.2).

## Initiative 15 — Meta + Deferred

**Status:** ✅ shipped 2026-05-23 (doc-only). Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15. NOT an epic.

### Overview

No architectural decisions — Init 15 is meta/skill-file work (TB-024 BMAD template updates) + deferred TB-017 (TOTP rotation runbook, trigger 2027-05-20). No code-level architectural surface.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15.
- Epics: `epics.md` § Initiative 15.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § init-15-meta.

## Initiative 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)

**Status:** 🚧 planning (started 2026-05-24). Source SCP: `sprint-change-proposal-2026-05-24-init16.md`. Three new decisions covering Epic 22 gallery tier pipeline + Epic 23 share-view security hardening.

**Note on H2 backfill debt:** Initiatives 13, 14, 15 decision sections (if any) NOT yet present in this architecture doc. Init 11 has no architecture-level decisions. Tracked as TB-039.

### Decision W — Gallery tier variant pipeline shape (Epic 22 / FR16-TIER-1)

**Decision:** Extend the existing `generate_thumbnail` worker pipeline (Decision P, Initiative 8) to produce TWO variants per upload: `<basename>.thumb.webp` (existing, ~10-50 KB, 128px longest-edge) AND `<basename>.gallery.webp` (NEW, ~150-500 KB target, designer-tuned default 1920px longest-edge). Variant routing extended at `apps/api/app/modules/sot/router.py:variant routing block` with `?variant=gallery` branch — silently falls back to original blob when sibling missing (mirror existing thumb fallback pattern from Decision P).

**Storage shape:** Sibling-file pattern (matches existing thumb storage). No Alembic migration needed. No new entity types. Filename suffix `.gallery.webp` complements existing `.thumb.webp`.

**Backfill:** `apps/api/scripts/enqueue_thumbnail_backfill.py` + `infra/scripts/backfill-thumbnails.sh` extended to also generate gallery tier for existing files. Same `--inline` pattern as current thumb backfill ran on 2026-05-23. Expected output shape: `inspected=N already_present=A enqueued=E rendered=R missing_original=0 errors=0`.

**Consumer surfaces (Story 22.2 + 22.3):**
- Catalog ModelCard + CardCarousel card-grid: stays `?variant=thumb` (Story 20.1 baseline).
- CardCarousel main frame: switches to `?variant=gallery` (NEW per FR16-CAROUSEL-TIER-1).
- ShareCarousel main frame: switches to `?variant=gallery` (NEW per FR16-CAROUSEL-TIER-1); thumb strip stays `?variant=thumb`.
- NEW symmetric fullscreen viewer (Story 22.3): fullscreen frame fetches `?variant=full` (= original blob); thumb strip uses `?variant=thumb`.
- Admin photo-order page: explicit `?variant=full` to ensure operator sees authoritative source quality.

**Designer tuning surface:** gallery longest-edge dimension is the primary designer-tunable parameter. Default 1920px assumes typical desktop fullscreen viewport. Designer UX session output (Story 22.3 spec) may override to 1280px / 1600px / 2560px based on viewport math — final value locked into Story 22.1 spec AC.

**Why this shape (rationale):**
- **Boring-tech consistency** with Decision P (Initiative 8 thumb pipeline). No new storage mechanism, no new endpoint shape, no new test fixture class.
- **Fallback preserves backward compatibility.** Pre-tier files automatically continue serving original blob until backfill catches up — no transitional state to manage.
- **Three-tier semantics** (thumb / gallery / full) explicitly maps to operator's mental model: thumb=catalog cards, gallery=preview frame, full=download / fullscreen / admin authority.
- **Bandwidth math:** with gallery tier ~10× smaller than full (4-5 MB → ~150-500 KB), Init 12 Story 19.2 nginx caps (`limit_rate 2m` + `limit_conn share_anon_conn 5`) no longer fire on legitimate carousel use (TB-036 503 root cause goes away naturally).

### Decision X — Blob cache hardening (Epic 23 / FR16-BLOB-CACHE-1 + FR16-STL-PREVIEW-LOCK-1)

**Decision:** Two complementary hardening patterns applied to share-view client + server concurrency surfaces:

**Decision X.1 — StrictMode-safe refcount + revocation invalidation (Story 23.1):**

`apps/web/src/routes/share/$token.tsx` module-level `_shareBlobCache` + `_shareBlobInflight` (Init 12 Story 19.5 round-2 a28cdde) extended with `_pending: Map<string, number>` count map. `acquireShareBlob` increments `_pending[src]` before fetch starts; resolve handler reads `_pending[src]` as initial refCount and decrements after consuming. If refCount drops to 0 during inflight resolution (all consumers unmounted before resolve), the resolve handler revokes the blob URL + skips cache entry creation. This closes TB-033 P2#1 (StrictMode double-mount / cancelled-load orphaned refcount inc).

**Cache invalidation policy: A — page-mount-scoped clear.** Both `_shareBlobCache` and `_shareBlobInflight` cleared in a useEffect cleanup when `/share/$token` route unmounts. Closes TB-033 P2#2 (revocation invalidation for open tabs — recipient gets fresh fetch + 404/403 on revoked token reopen). Chosen over alternatives B (TTL probabilistic) and C (server ETag round-trips) for simplicity + deterministic semantics; loses cross-token-nav cache benefit (acceptable trade-off given share-view UX terminus per [[feedback_share_view_scope_boundary]] — anonymous recipients rarely navigate between tokens).

**Decision X.2 — STL preview source-tracking + single-flight lock (Story 23.2):**

`workers/render/render/worker.py:render_stl_previews` (Init 12 Story 19.6 fef96f7) hardened with two complementary protections:

**Source tracking by STL sha256 (boring-tech choice over FK column):** `ModelFile.original_name = f"<view>-{stl_sha256[:8]}.png"`. Worker's idempotency check (skip-if-existing-count>=4) now counts only previews matching CURRENT primary STL's sha256. Stale previews from prior STLs survive as orphan rows visible to admin but not consumed by share view (separate cleanup task out-of-scope for Story 23.2). Chosen over Option B (FK ON DELETE CASCADE) for boring-tech reasons: no new column, no Alembic migration, sha256 already computed during upload.

**Single-flight dispatch lock:** Redis SETNX lock at `apps/api/app/modules/share/router.py:dispatch_render_previews` (function inferred from Story 19.6 lazy dispatch glue). Pattern: `lock_key = f"share:stl_preview_lock:{stl_for_preview}"`; `acquired = await redis.set(lock_key, "1", nx=True, ex=300)`. Only ONE worker job dispatched per STL even under concurrent share-view requests. Lock TTL 300s covers worst-case render time + safety margin; worker explicitly releases lock on completion / failure.

**Why this combined Decision X (rationale):**
- **Both hardening surfaces share the "concurrency + state-correctness in share-view subsystem" job-family** — bundling under one decision keeps the trail coherent for future hardening work.
- **Policy A (page-mount-scoped invalidation)** matches the share-view terminus reality: recipients are unlikely to navigate between multiple share tokens; the cache benefit traded away is theoretical.
- **sha256 source-tracking** is forward-compatible with future STL-replace workflows (preview-rotate triggered by sha256 mismatch); FK approach would require additional schema work later.
- **Single-flight via Redis SETNX** mirrors Story 19.1 per-IP rate-limit Redis pattern (familiar shape, no new infrastructure dependency).

### Decision Y — Per-token rate-limit middleware (Epic 23 / FR16-RATELIMIT-PER-TOKEN-1)

**Decision:** NEW per-share-token request-count rate-limit middleware OR extension of existing `share_anon_ratelimit_*` from Init 12 Story 19.1 (commit 2232b77). Per-token sliding window via Redis ZADD timestamps to sorted set keyed `share_token_ratelimit:<token>`; ZREMRANGEBYSCORE prunes old timestamps; ZCARD counts vs cap. Configurable via `apps/api/app/core/config.py` Settings fields:

```
SHARE_PER_TOKEN_RATELIMIT_PER_MINUTE      default=60      ge=1, le=10000
SHARE_PER_TOKEN_RATELIMIT_WINDOW_SECONDS  default=60      ge=10, le=3600
```

Operator-decided defaults per 2026-05-24 AskUserQuestion ("Dodać app-level per-token request-count cap np. 60 req/min/token"). Misconfig (negative / out-of-range) raises ValidationError at startup-config-load (matches Init 7 Settings precedent).

**429 response shape:** matches Story 19.1 per-IP middleware (composable):
```
HTTP/1.1 429 Too Many Requests
Retry-After: <N>
Content-Type: application/json

{"detail": "rate_limited", "scope": "share_token", "retry_after_seconds": <N>}
```

Retry-After header is the remaining window before the oldest timestamp in the sorted set ages out below the cap (computed via ZSCORE of the oldest in-window timestamp + `SHARE_PER_TOKEN_RATELIMIT_WINDOW_SECONDS`).

**Composition with Story 19.1 per-IP middleware:** BOTH middlewares fire on `/api/share/<token>/*` requests; EITHER overage returns 429. Test fixture exercises both legs independently (per-IP overage vs per-token overage vs both clean). Middleware ordering: per-IP fires FIRST (cheaper Redis key, more common abuse vector); per-token fires SECOND (token-specific defense-in-depth).

**Threat-vector enumeration (NFR16-SECURITY-1 in spec):**
- **Share-token leak vectors:** referrer header on linked content, screenshot share, copy-paste-then-redistribute, log leakage. Token rotation defense remains operator-controlled (existing `DELETE /api/admin/share/{token}` endpoint).
- **IP-pool attacker scenarios:** botnet defeats per-IP cap by distributing requests across IPs; per-token cap catches THIS specific attack vector — 60 req/min/token means even a million-IP botnet maxes out at 60 req/min total per scraped token.
- **Retry-After backoff exploitation:** attacker that respects Retry-After still bounded by the window cap; attacker that ignores Retry-After hits 429 storm (no resource consumption beyond Redis ZADD).
- **Share-scoped DDoS multiplier:** without per-token cap, attacker with M IP-pool and N scraped tokens can hit M×60 req/min×N tokens; per-token cap reduces to N×60 req/min independent of pool size.

**Pen-test source (operator-blessed):** `ezop-kbk.ddns.net` per [[reference_external_test_source]] for post-deploy verification — separate LAN + public-internet egress = real anonymous surface.

**Why this shape (rationale):**
- **Defense-in-depth over single-layer per-IP** — operator's 2026-05-24 explicit choice. Per-IP catches casual abuse; per-token catches sophisticated multi-IP scraping.
- **Redis ZSET sliding window** mirrors Story 19.1 RateLimitMiddleware pattern (familiar shape, deterministic O(log N) ops, no new infrastructure).
- **Composable with existing middleware** keeps blast radius small — Story 19.1 stays untouched; new middleware is additive.
- **Configurable via env** lets operator tune in production without code redeploy if 60 req/min proves too tight / too loose.

### Cross-references

- PRD: `prd.md` § Initiative 16 (FR16-* + NFR16-* link to Decisions W/X/Y respectively).
- Epics: `epics.md` § Initiative 16 (Epic 22 stories 22.1-22.4 implement Decision W; Epic 23 stories 23.1+23.2 implement Decision X; Story 23.3 implements Decision Y).
- SCP: `sprint-change-proposal-2026-05-24-init16.md` (operator-approved 2026-05-24 with voice-heavy AskUserQuestion answers locked into Decision W default tier-dim + Decision Y default thresholds).
- Memory entries informing decisions: [[feedback_security_vector_enumeration]] (§ Threat vectors enumeration mandatory for Decision Y), [[feedback_shared_cache_in_react]] (Decision X.1 informed by prior cache hardening guidance — refcount correctness + invalidation + memory cap), [[feedback_worker_single_flight]] (Decision X.2 informed by prior worker single-flight guidance — Redis SETNX atomic claim), [[feedback_codex_model_routing]] (Decisions X+Y reviewed on gpt-5.5 security class), [[feedback_voice_heavy_dedicated_grilling]] (Init 16 3-question grilling 2026-05-24 preceded SCP draft; designer engagement gates Decision W tuning), [[feedback_share_view_scope_boundary]] (Decision W fullscreen viewer is image-quality exception, NOT UX enrichment — terminus carve-out), [[feedback_collaboration_division]] (Story 19.2 nginx throughput cap remains operator infra-side dep; Decision Y composes on top of nginx layer without overriding).

## Initiative 17 — Post-Init-16 Operator Hands-On Findings + Housekeeping Sweep

**Status:** 🚧 planning (started 2026-05-24, same session as Init 16 close-out). Source SCP: `sprint-change-proposal-2026-05-24-init17.md`. One new architectural decision (Decision Z — share-view concurrency semaphore); rest of Init 17 stories are CSS / URL-extension / doc-only without architectural surface.

### Decision Z — Share-view fetch concurrency semaphore (Epic 27 / FR17-SHARE-CONCURRENCY-1)

**Decision:** Add a module-level concurrency semaphore to `apps/web/src/routes/share/shareBlobCache.ts` that caps concurrent in-flight share-asset fetches at **4**. Overflow requests queue via a promise-chain release mechanism — they wait on the next slot to free up. The semaphore wraps the cold-fetch path; the existing generation guard (Story 23.1 round-2) and the `_pending` refcount discipline (Story 23.1 round-1) remain unchanged.

**Shape:**

```typescript
// shareBlobCache.ts — module-level state
const MAX_CONCURRENT_FETCHES = 4;
let _concurrentFetches = 0;
const _queue: Array<() => void> = [];

async function _acquireFetchSlot(): Promise<void> {
  if (_concurrentFetches < MAX_CONCURRENT_FETCHES) {
    _concurrentFetches += 1;
    return;
  }
  return new Promise<void>((resolve) => {
    _queue.push(() => {
      _concurrentFetches += 1;
      resolve();
    });
  });
}

function _releaseFetchSlot(): void {
  _concurrentFetches -= 1;
  const next = _queue.shift();
  if (next !== undefined) next();
}

// acquireShareBlob — cold-fetch branch (existing code remains)
const promise: Promise<string> = (async () => {
  await _acquireFetchSlot();
  try {
    const r = await fetch(src, { credentials: "omit" });
    // ... existing resolve + cache logic ...
  } finally {
    _releaseFetchSlot();
  }
})();
```

**Why cap=4 (one below nginx limit):**

Story 19.2 nginx `limit_conn share_anon_conn 5` is the hard cap at the network layer. Setting client-side semaphore = 4 leaves a 1-slot safety margin: if a stale connection lingers in nginx's count or a parallel browser tab opens, the client doesn't push to the absolute edge. Tighter than 4 sacrifices throughput on initial paint; looser than 4 brings back the 503 risk (HAR-confirmed 3× 503 + wait=0ms in `tmp/share_gallery.har` operator capture 2026-05-24).

**Why semaphore wraps fetch, not generation check:**

Generation guard (Story 23.1 round-2) handles the route-unmount-mid-flight case: an OLD fetch's resolve handler must not pollute the NEW cache state after `clearShareBlobCache()` runs. The semaphore is orthogonal — it caps concurrency regardless of generation. Order of operations in cold-fetch branch:
1. Increment `_pending[src]` (Story 23.1 round-1 — counts subscribers).
2. Acquire semaphore slot (Story 27.1 — caps concurrency).
3. Capture `fetchGeneration` (Story 23.1 round-2 — detects clear).
4. Fetch; on resolve, generation check + cache set.
5. Finally: release semaphore + shift queue.

**Queue overflow semantics:**

When all 4 slots are in-use, new `acquireShareBlob` callers don't dispatch a fetch — they wait on a release-callback in `_queue`. As each in-flight fetch completes (success OR failure), one queued callback fires, incrementing `_concurrentFetches` and resolving the awaiting promise. Net effect: under burst of N=8+ AnonymousImage mounts, the first 4 fetch concurrently, remaining 4+ wait for the first 4 to complete, then dispatch sequentially in groups of 4. No 503s, no client-side rejection, just gentle pacing under the nginx cap.

**Memory implications:**

`_queue` could grow unboundedly under pathological load (e.g. 1000-image carousel mount with all eager mounts). For current operator catalog (~5-15 photos per share), max queue depth is bounded by carousel size. If pathological case surfaces, follow-up consideration: cap `_queue.length` and reject overflow with explicit error. Out of scope for Story 27.1.

**Why this shape (rationale):**

- **Boring-tech**: module-level state + promise-chain queue is standard JS concurrency primitive. No new dependencies. No race conditions (JS single-threaded; queue mutations atomic per microtask).
- **Composable with existing cache layers**: doesn't touch Story 19.5/23.1's cache map + pending counter + generation guard. Pure additive layer between "want to fetch" and "actually fetch".
- **Deterministic for tests**: vitest can spawn N concurrent `acquireShareBlob` calls + assert `_concurrentFetches === 4` at peak + verify FIFO queue ordering.
- **TB-036 fully closed**: original Init 12 share-anon 503 issue (carousel mount burst exceeding nginx cap) is now resolved at the client layer — no need to relax the nginx security cap.

### Cross-references

- PRD: `prd.md` § Initiative 17 (FR17-SHARE-CONCURRENCY-1 links to Decision Z).
- Epics: `epics.md` § Initiative 17 (Epic 27 Story 27.1 implements Decision Z).
- SCP: `sprint-change-proposal-2026-05-24-init17.md` § §4.2.
- Memory entries informing decisions: [[feedback_shared_cache_in_react]] (semaphore composes with cache layers), [[feedback_codex_model_routing]] (gpt-5.4-mini sufficient for FE concurrency primitive), [[feedback_share_view_scope_boundary]] (semaphore is bug-fix per terminus carve-out for security-class).


## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Source SCP: `sprint-change-proposal-2026-05-25-init18.md` (status `approved` 2026-05-25). Init 18 introduces three architectural decisions on the share-flow recipient-state routing.

### Decision AA — Authenticated share-resolve endpoint placement

**Decision:** the new authenticated branch lives at `GET /api/me/share-links/<token>/resolve`, NOT `GET /api/share/<token>/resolve`.

**Implementation:** add the endpoint to existing `apps/api/app/modules/share/member_router.py` (router prefix `/api/me/share-links` per Init 6 Story 6.5 precedent). The endpoint uses standard `Depends(current_user)` auth dep; no anonymous bypass.

**Why this prefix (not `/api/share/<token>/...`):**

- [[feedback_share_view_scope_boundary]] amended carve-out 2026-05-25 preserves NFR10 credentialless contract on existing `/api/share/<token>/*` family. Adding ANY auth-bearing endpoint under that prefix risks future maintainers reflexively adding `Depends(current_user)` to a public route (Init 6 / Init 12 lessons: the public-bypass pattern is fragile under contributor pressure).
- `member_router.py` at `/api/me/share-links` already establishes the "authenticated operations adjacent to share-tokens" pattern. Extending it to host `<token>/resolve` is the natural placement.
- Frontend pairing is clean: `MemberShareView` calls `api("/api/me/share-links/<token>/resolve")`; anonymous render continues calling existing `/api/share/<token>` endpoints. Two URL families = two clearly-separated trust zones.

**Token-status-enumeration protection** (NFR18-TOKEN-ENUMERATION-1): the new endpoint returns uniform 404 for invalid / expired / revoked tokens (same convention as Init 6 Story 6.4 invite-token validation). The resolve endpoint does NOT distinguish "token never existed" from "token existed but expired/revoked" in the response — uniform 404 prevents a brute-force enumeration probe from extracting token-state. For tokens that DO resolve, the endpoint returns `{model_id: UUID, access: "granted"}` — `access` field is forward-compat for B7 (`"granted"` / `"request_needed"`).

### Decision AB — `/share/*` AppShell chrome bypass policy

**Decision:** `AppShell.tsx` `isSharePath` bypass becomes conditional:

- **Anonymous OR auth-loading** → bypass (existing behavior; minimal share-view header rendered by route component itself).
- **Authenticated** → render full AppShell (TopBar + ModuleRail), enabling Variant γ enrich-in-place at `/share/<token>`.

**Implementation sketch** (Story 30.2):

```tsx
// AppShell.tsx
const isSharePath = pathname.startsWith("/share/");

// Decision AB: bypass share path ONLY when the caller is anonymous.
// Authenticated callers on /share/<token> get full chrome (Variant γ
// enrich-in-place) per Init 18 FR18-MEMBER-SHARE-VIEW-1.
const shouldBypassForShare = isSharePath && !auth.isAuthenticated;

if (shouldBypassForShare) {
  return <>{children}</>;
}
```

The auth-loading state (`auth.isLoading === true`) continues to render the spinner per existing behavior (line 73-79 of AppShell.tsx); the bypass evaluation runs after loading resolves, preventing a chrome flash during the brief auth fetch.

**Why conditional bypass (not unconditional):**

- Variant γ enrich-in-place (operator + Sally decision) requires the full member chrome to render around the catalog detail content. An unconditional bypass would force `MemberShareView` to re-implement TopBar + ModuleRail inside the route component, which is fragile (chrome drift, prop duplication, dark-mode token drift).
- Anonymous render continues to bypass (zero regression for B1/B2/B3/B4/B6 recipients).

### Decision AC — Info-bar dismissal persistence

**Decision:** `sessionStorage` key pattern `share-context-dismissed:<modelId>`. Per-model + per-session granularity. Next session re-shows (assumes user may have forgotten context).

**Implementation:** `ShareMemberContextInfoBar.tsx` component reads `sessionStorage.getItem("share-context-dismissed:" + modelId)` on mount; if present (any truthy value), suppresses render. Close button sets `sessionStorage.setItem("share-context-dismissed:" + modelId, "1")`.

**Why sessionStorage (not localStorage):**

- Sally pick + operator-approved 2026-05-25 (Sally UX rec Decision 3).
- Re-showing per session is less surprising than "forever dismissed" — recipient may genuinely forget the share-link context after a multi-day gap.
- Per-modelId scoping prevents one dismiss from silencing the info-bar for unrelated share links the same recipient receives later.
- Operator may downgrade to localStorage in a future iteration if telemetry shows recipients dismissing repeatedly within a session.

**Edge case — sessionStorage unavailable** (private browsing strict mode, embedded WebView, etc.): the info-bar renders on every mount (fail-open, never silently swallows the affordance). The dismiss button still works in-memory for the lifetime of the component instance.

### Cross-references

- PRD: `prd.md` § Initiative 18 (FR18-* + NFR18-* link back to Decisions AA + AB + AC).
- Epics: `epics.md` § Initiative 18 (Epic E30 Story 30.1 implements Decision AA; Story 30.2 implements Decisions AB + AC; Story 30.3 implements chrome additions independent of the three decisions).
- SCP: `sprint-change-proposal-2026-05-25-init18.md` § §4.
- Memory entries informing decisions: [[feedback_share_view_scope_boundary]] (amended carve-out language drove Decision AA's prefix separation), [[feedback_auth_boundary_contract_audit]] (Decision AA prefix separation is the canonical audit-mandated boundary-preservation shape), [[feedback_security_vector_enumeration]] (Story 30.1 § Threat vectors enumerated MUST list: token-enumeration probe via resolve endpoint, double-resolve via stale session, CSRF on resolve endpoint (read-only GET — not applicable, but document the reasoning), cross-tenant access via stale member access).


## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)

**Status:** 🚧 planning (started 2026-05-29). Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md` (status `approved` 2026-05-29). Init 19 introduces three architectural decisions on the read-only Spoolman inventory integration. First portal-side outbound HTTP to a non-observability service.

### Decision AD — Cache topology + poll cadence + leader-election + observability

**Decision:** Redis 30s TTL on the single canonical `spools:summary:v1` key (JSON-encoded snapshot of all active spools + filaments + vendors) + arq cron job `poll_spoolman_summary` every 60s + Redis SETNX `spools:poll-lock` (90s expiry) acquired before refresh (brainstorm anti-pattern 11 leader-election; prevents thundering herd when multiple API workers run) + `external_service=spoolman` structured-log tag on every Spoolman client call (per `~/repos/configs/docs/observability-logging-contract.md`).

**Implementation sketch:**

- Backend `apps/api/app/modules/spools/client.py` wraps `httpx.AsyncClient` with explicit 5s timeout + circuit breaker (3 consecutive failures → 30s open).
- `apps/api/app/modules/spools/service.py` owns the cache topology: `get_summary()` reads `spools:summary:v1` from Redis; cache miss falls through to a single live fetch + lock-protected SET. `refresh_summary()` runs from the arq cron, acquires SETNX `spools:poll-lock` (90s expiry covering worst-case Spoolman latency), fetches `/api/v1/spool` + `/api/v1/filament` + `/api/v1/vendor`, writes the JSON snapshot to `spools:summary:v1` (30s TTL) + sibling key `spools:summary:last-success-ts` (unbounded TTL, drives the "Last updated HH:MM" indicator).
- arq cron registration lives in `apps/api/app/workers/__init__.py` `WorkerSettings.cron_jobs` (the API-image arq worker per AGENTS.md § Worker depends on `portal-api` editable — NOT the render worker).
- Frontend `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts` wraps `useQuery` with `queryKey: ["spools", "summary"]`, `staleTime: 60_000`, `gcTime: 5 * 60_000`. No mutation observers (read-only mirror).

**Cache-coherence table** (per [[feedback_scp_pre_enumeration_phase]] § B discipline + Init 18 round-7 lesson):

| Query key | Staleness budget | Retry | Mutation propagation | Eviction on route exit | Seeding on route enter |
|---|---|---|---|---|---|
| `["spools", "summary"]` | 60s acceptable | n/a (read-only mirror; staleness IS the contract) | n/a (no portal-side mutations in MVP-A) | none (cache survives navigation; stays warm for landing-card revisit) | none (poll job seeds; UI just reads) |

**Magic-constant contract pointing** (per [[feedback_scp_pre_enumeration_phase]] § C rule):

- `staleTime: 60_000` because **"low-stock landing card freshness budget is 60s per FR19-CACHE-1; matches arq poll cadence"** (the contract is the poll cadence, NOT the AuthContext meQuery staleTime — Init 18 round-1 P1 lesson).
- `gcTime: 5 * 60_000` because **"keep the snapshot in-memory across landing card / `/spools` route transitions so revisits skip the network round-trip; 5min upper bound is arbitrary product default, revisit if memory pressure surfaces"**.
- Redis TTL `30s` because **"upper bound on stale snapshot served from Redis; poll runs every 60s but a fresh request within the 30-60s gap still gets cache hit serving the slightly-staler value rather than triggering a synchronous fetch in request path"**.
- arq cron cadence `60s` because **"low-stock signal updates rarely (operator/Laura adds or measures a spool maybe once per print job, plus background `last_used` ticks); 60s freshness is acceptable per operator decision implicit in MVP-A scope; sub-minute polling would burn LAN-only egress with no UX gain"**.
- Spoolman client timeout `5s` because **"LAN-only host on `.190`, typical response ~50ms; 5s upper bound flags genuine outage rather than transient latency. Arbitrary value within typical homelab outbound timeout band"**.
- Circuit breaker thresholds `3 failures` / `30s open` because **"3 consecutive errors signal real outage rather than transient blip; 30s open window matches Redis TTL so a fresh probe naturally retries when cache would expire anyway. Arbitrary defaults within typical resilience-pattern bands"**.
- SETNX lock `90s expiry` because **"worst-case Spoolman refresh latency is ~5s × 3 entity types + serialization headroom; 90s comfortably covers stuck-poll scenarios without holding the lock past the next poll interval"**.

**Failure semantics:**

- Spoolman unreachable → frontend reads last cached `spools:summary:v1` value + reads sibling `spools:summary:last-success-ts` for the "Last updated HH:MM (Xm ago)" indicator (FR19-FAILURE-1).
- Cold-start + Spoolman down (cache empty) → `/spools` and the landing card render an explicit "Spoolman unavailable" empty state — NOT 500.
- Circuit-breaker open → cache reads still serve the last successful snapshot; the open window prevents request-path retries.

**Observability:**

- Every httpx call instrumented with structured-log fields `external_service=spoolman` + `endpoint=GET /api/v1/spool` (or `/filament`, `/vendor`) + `duration_ms` + `status_code` + `lock_acquired` (true/false on the poll path).
- OTel span name `spoolman.client.<endpoint>` wrapping the httpx call.
- Sentry/GlitchTip breadcrumb category `spoolman.client`.
- Response bodies summarized as entity counts only — NEVER logged in full at INFO (brainstorm anti-pattern 8).

### Decision AE — Network transport (internal docker network + configs-side coordination)

**Decision:** primary topology P4b — portal-api container resolves `http://spoolman:8000/api/v1/*` over a shared docker compose network. Requires the configs-side Spoolman compose to join a docker network the portal compose stack also joins (e.g. `portal-network`).

**Implementation:**

- **Configs-side PR (NOT a 3d-portal commit):** scope ~10 LOC in `~/repos/configs/docker-compose-recipes/spoolman.yml` — add `networks: [portal-network]` to the Spoolman service block and declare the external network. Deploy via `~/repos/configs/sync.sh`. HC2 trip-wire honored (portal repo never edits configs files).
- **Portal-side wiring** (deferred to Story 31.1): add `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` env slots to `apps/api/app/core/config.py` Pydantic `Settings`. Default `SPOOLMAN_URL=http://spoolman:8000`. `infra/docker-compose.yml` joins the same `portal-network` external network. `infra/docker-compose.dev.yml` may keep the host-network fallback if local dev doesn't co-locate the Spoolman container.

**Fallback topology P4a:** if the configs-side PR is not yet in place when Story 31.1 begins, portal-api runs on the docker host network and calls `http://localhost:7912/api/v1/*`. One-line transitional posture; same `SPOOLMAN_URL` env var wraps both shapes (just point it at `http://localhost:7912` instead of `http://spoolman:8000`). No Init 19 schedule slip.

**Rejected alternatives:**

- **P4c (nginx-fronted Spoolman through `nginx-180` edge)** — adds latency + complexity for zero security gain in a LAN-only deployment. Reconsider only if Spoolman ever exposes externally (would also require P3d Spoolman auth).
- **P4e (sidecar service in `apps/api/app/modules/spools/`)** — that IS the *organizational* shape (the httpx wrapper lives there), but it is NOT a transport choice. Transport is still P4b or P4a.

**Future swap-out cost:** isolated httpx client in `apps/api/app/modules/spools/client.py` means swapping P4b → P4a → future P3d-with-auth is a one-file change. Brainstorm anti-pattern 7 honored: `SPOOLMAN_URL` env-driven, NOT hardcoded.

**Configs-side precondition** (OD8 close-out + Story 31.1 § Pre-merge precondition): before Story 31.1 ships, the configs-side compose MUST be verified to bind Spoolman on a non-routable host interface (NOT `0.0.0.0` exposed via the router). Documented as Story 31.1 § Pre-merge precondition — NOT a 3d-portal commit.

### Decision AF — Data-model carry-through for future cost-calc UX

**Decision:** backend DTOs (`apps/api/app/modules/spools/models.py`) for `SpoolView` and `FilamentView` surface ALL cost-relevant Spoolman fields end-to-end — even though MVP-A's UX does NOT compute cost. Operator decision 5: Spoolman native `price` + `weight` fields are the canonical cost-data source, verified by live OpenAPI inspection (Filament has `price` + `weight` + `spool_weight`; Spool has `price` + `spool_weight` + `remaining_weight` + `initial_weight` + `used_weight`).

**DTO surfaces:**

- **`FilamentView`**: `id`, `name`, `vendor_id`, `vendor_name`, `material`, `color_hex`, `price` (currency-tagged float, nullable), `weight` (grams, the full-spool weight), `spool_weight` (grams, empty-cardboard weight).
- **`SpoolView`**: `id`, `filament_id`, `price` (override, nullable), `remaining_weight` (grams), `initial_weight` (grams), `used_weight` (grams), `spool_weight` (grams), `first_used` (ISO8601 nullable), `last_used` (ISO8601 nullable), `archived` (bool), `lot_nr` (str nullable).

**Mirroring:** frontend `apps/web/src/lib/api-types.gen.ts` mirrors these fields automatically via the OpenAPI generation pipeline (no manual TypeScript typing — Story 31.2 regenerates `api-types.gen.ts` after the new routes land).

**MVP-A UX subset:** uses ONLY `id`, `name`, `vendor_name`, `material`, `color_hex`, `remaining_weight`, `initial_weight` (for the % remaining bar). The broader fields are CARRIED in the cache and DTOs.

**Forward-design note (Phase D, NOT in MVP-A):** future per-print cost arithmetic = `remaining_value = remaining_weight × (filament.price / filament.weight)` (or `spool.price` override if set). Documented here so the data shape decision today serves the future feature; the UX itself is parked with explicit precondition trigger per § Out of scope (Phase D triggers on operator request for per-print cost rollup).

**Why carry-through now, not later:**

- Schema additions are cheap (rename + add fields in DTO + cache JSON). Schema BACKFILL (after MVP-A ships without these fields) would require touching the cache key format, the OpenAPI surface, and every consumer — operator decision 5 explicitly preempts that backfill cost.
- Brainstorm Reverse anti-pattern 18 reinforces: faithfully mirror Spoolman's filament-as-SKU vs spool-as-physical-instance distinction (OD9 close-out — collapsing to spool-only would silently break when a second spool of an existing filament SKU arrives).
- The data flow is mechanical (Spoolman → Pydantic → JSON → Redis → JSON → React Query → TypeScript) — no design degrees of freedom were sacrificed by including the broader field set.

### Cross-references

- PRD: `prd.md` § Initiative 19 (FR19-* + NFR19-* link back to Decisions AD + AE + AF).
- Epics: `epics.md` § Initiative 19 (Story 31.1 implements Decisions AD + AE; Story 31.2 implements Decision AF DTOs; Stories 31.3 + 31.4 + 31.5 are pure FE / i18n / docs).
- Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md` § §3 + §4.2.
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md` (15-parameter morphological grid + OD1-OD10 register).
- Memory entries informing decisions: [[feedback_scp_pre_enumeration_phase]] (cache-coherence table format from § B + magic-constant contract pointing from § C applied to Decision AD), [[feedback_codex_model_routing]] (gpt-5.4-mini routing locked for all Init 19 stories — no NFR-SECURITY adjacency).

## Initiative 20 — STL Slicer Estimates (Per-Part MVP)

**Status:** 🚧 planning (started 2026-05-31). Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` (status `approved` 2026-05-31 — approval scoped to planning-artifact appends, NOT code implementation). Init 20 introduces three architectural decisions for trustworthy, reproducible **per-STL** slicer estimates produced by a real headless OrcaSlicer slice. The decisions are grounded in **proven** CLI feasibility (PLA + TPU slices on the Fenrir bench, g-code metadata confirmed, resolver script proved end-to-end), not blue-sky. This is the phase-3 (solutioning) graduation of the architecture content sketched in the brainstorm discovery artifact (§ 2 data model, § 3 resolver, § 4 slicer-worker, § 5 invalidation). All app-layer code is portal-owned; the container/network topology is configs-side (HC2 boundary).

### Decision AH — Resolver architecture (system + user inheritance merge + override layer + hashing)

**Decision:** A first-class **profile resolver** subsystem (NOT a convenience script) is mandatory, because raw Orca user-profile JSONs are **partial** — they `inherit` from system profiles and lack a top-level `type`, so the Orca CLI rejects them directly via `--load-settings` / `--load-filaments` and `--datadir` does not fix it (verified). The temporary `/home/ezop/tmp/orca_resolve_profiles.py` proved the resolve path end-to-end for both PLA and TPU.

**Resolver responsibilities (production shape):**

1. **Import boundary (read):** read the Orca system profile tree + the user partials as **vendored/exported artifacts** (one-way snapshot from the Fenrir bench), never a live read of Fenrir's `/mnt/c/...` in production.
2. **Inheritance merge:** recursively resolve `inherit` chains (system → user partial), deep-merging keys; **user partial wins on conflict.**
3. **Normalize:** inject the top-level `type` (machine/process/filament); drop the instantiation field that breaks the CLI.
4. **Override layer:** apply the Spoolman-mapped custom overrides (Decision AJ § Spoolman linkage) onto the filament JSON.
5. **Validate:** confirm the merged JSON is CLI-acceptable **before** it becomes a bundle — a dry `--info` / minimal-slice smoke check + a schema assertion that required keys (e.g. `filament_max_volumetric_speed` for TPU) are present and sane.
6. **Hash & version:** compute `bundle_hash`, stamp `orca_version`, write `SlicerProfileBundle` + `SourceProfileSnapshot`.
7. **Export boundary (write):** the resolved triple is the portable artifact; bundle import/export across environments is by these full JSONs + their hash, never by re-reading live Orca/Windows state.

**Resolver precedence (load-bearing contract):** `exact bundle > custom override > material-class default > unsupported`. A request that resolves to "unsupported" is an explicit classified failure surfaced to the owner — never a silent fallback to a wrong default. **The Orca resolver is first-class precisely because raw user profiles are partial** — the merge IS the load-bearing complexity that the naive `--load-settings` path fails on.

**Hashing / versioning:**

- `bundle_hash = H(machine_json ∥ process_json ∥ filament_json ∥ orca_version)`, canonicalized (sorted keys, normalized floats) so cosmetic JSON churn does not churn the hash.
- **`orca_version` is folded into the hash on purpose:** a different Orca build can produce different estimates from identical settings (slicing-engine changes), so an Orca upgrade becomes a clean bulk-invalidation event (Decision AJ) rather than a silent estimate drift.
- Bundles are **append-only / versioned** — a re-tune creates a new bundle + hash; old estimates stay attributable to the old hash until recomputed.

**Data-model surfaces (sketch — PRD/story phase confirms field names):**

- **`PrintIntentPreset`** (portal-owned, user-facing): `name`, `material_class` ∈ {PLA, PETG, PCTG, TPU}, `quality_tier` (OD-1), `printer_ref`, `notes`, `is_default`. MUST NOT leak Orca internals (no raw layer-height floats, no `filament_max_volumetric_speed` in the UI).
- **`SlicerProfileBundle`** (internal): `intent_preset_ref`, `machine_json_ref` / `process_json_ref` / `filament_json_ref`, `orca_version`, `bundle_hash`, `source_snapshot_ref`, `spoolman_overrides_ref?`, `created_at` / `superseded_at`.
- **`SourceProfileSnapshot`** (provenance): the raw user partials + system-profile refs + resolver-script version used, so a bundle can be re-resolved and diffed if Orca's system tree changes upstream. Append-only.

**Ownership topology:** Spoolman owns inventory + `filament.extra.url` (Init 19 SoT); the Orca system+user profile tree owns the *resolution recipe*; the portal owns the *resolved* bundle + the source snapshot + the estimate. The portal snapshots inputs so a resolve is reproducible even if upstream profiles change.

### Decision AI — Slicer-worker container (runtime boundary, job IO, STL cache)

**Decision:** Production runs OrcaSlicer **headless in a dedicated containerized `slicer-worker` service** bundling the Linux OrcaSlicer **2.3.2** AppImage + the verified dep set (`libopengl0`, `libglu1-mesa`, `libgtk-3-0`, `libwebkit2gtk-4.1-0`, `libsecret-1-0`, `libgstreamer-plugins-base1.0-0`, `libmspack0`). **No Fenrir, no Windows exe, no Orca GUI in production.**

**OD-2 (dedicated vs extend `workers/render/`) — leaning dedicated:** Orca's GUI/GL deps bloat the render image and have a different failure profile (a slice takes minutes; a render is sub-second), so co-tenancy would couple two very different resource + timeout regimes. The repo already runs an arq worker for renders, so the queue/runtime shape is proven; the slicer worker reuses that pattern in its own service. **AppImage-in-container:** `--appimage-extract` (run the squashfs contents directly, avoids FUSE in the container) is the assumed container-friendly path — flag for a spike (risk R3).

**Job contract:**

- **Input (job payload):** the `(stl_ref/stl_hash, bundle_ref/bundle_hash)` 2-tuple — nothing else. The worker pulls the STL from the cache and the resolved triple JSONs from the bundle store.
- **Process:** Orca `--info` cheap manifold/facet/volume pre-check (fail fast on bad meshes) → headless CLI slice with the three resolved JSONs + STL → g-code to a temp path.
- **Output:** parsed `EstimateRecord` fields from the confirmed-present g-code metadata lines (`; estimated printing time (normal mode)`, `; filament used [g]` / `; total filament used [g]`, `; filament used [mm]`, `; filament used [cm3]`, `; total filament cost`, `; {filament,print,printer}_settings_id`) + classified warnings. **G-code is parse-and-discard** (OD-5 leaning) — large, derivable, not retained beyond the parse.

**STL cache:** content-hashed; layout `<cache_root>/stl/<hash[:2]>/<hash>.stl` (fan-out by hash prefix, same shape the render worker uses for thumbnails). The API/catalog populates the cache; the worker reads the `.190`-mirrored catalog copy (OD-8), never Windows directly.

**Failure & warning classification:**

- **Warnings** (slice succeeded, estimate valid): e.g. *floating cantilever* — captured in `EstimateRecord.warnings`, surfaced to the owner, **non-blocking**.
- **Failures** (no usable estimate): non-manifold mesh, Orca non-zero exit, CLI-rejected profile (should be caught at resolve-time validation, Decision AH § 5), parse failure, timeout → `status: failed` + reason; the record exists so the UI shows "couldn't estimate, here's why" rather than vanishing.

**Concurrency & queue:** arq job per non-`fresh` `(stl_hash, bundle_hash)`, deduped on the key; **small bounded concurrency** (likely 1-2 on `.190`, OD-6) to avoid starving the API/render workers; recompute is idempotent.

**Configs/app boundary (HC2):** any docker-network / compose change to add the `slicer-worker` service or reach Spoolman is a `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` PR — **NOT a 3d-portal commit**. The portal initiative owns app-layer worker code; the container topology is configs-side. `infra/.env.example` gains `ORCA_VERSION` + `FENRIR_EXPORT_PATH` slots (bench-only export path documented as NOT a production runtime path).

**OD-9 (module placement):** new `apps/api/app/modules/slicer/` (resolver, worker client, cache logic, estimate models) + `apps/web/src/modules/estimates/` (display, `PrintIntentPreset` selector, soft-fail UI) — vs folding into a `requests` v2 slot. Architecture-phase leaning is a dedicated module; story specs confirm.

### Decision AJ — Cache / invalidation / cost arithmetic

**Decision:** `EstimateRecord` is keyed `(stl_hash, bundle_hash)`; because `bundle_hash` folds in `orca_version` and the Spoolman-override set, that 2-tuple is the **complete** reproducibility key. An estimate goes **stale** (→ `queued` → recompute) when any input to its key changes.

**Recompute-trigger table** (exhaustive-by-design — closes risk R9 "cache key incomplete → stale served as fresh"):

| Trigger | Mechanism | Effect |
|---|---|---|
| STL content changes | `stl_hash` changes | new key ⇒ new estimate; old key orphaned (GC later) |
| Resolved bundle re-tuned | new `SlicerProfileBundle` + new `bundle_hash` | estimates on the old hash marked `stale`, requeued against the new bundle |
| Orca version upgrade | `orca_version` ∈ `bundle_hash` ⇒ hash changes | all estimates effectively stale; bulk recompute |
| Spoolman mapped-override change (volumetric speed, temp, density) | folded into `bundle_hash` via `spoolman_overrides_ref` | affected bundles re-hash ⇒ dependent estimates stale |
| Spoolman cost-only change (`spool.price`; density unchanged) | **OD-7 — cost is derived, not a slice input** | recompute the cost field **arithmetically without re-slicing** (cheap path) |

**Cost-only-arithmetic rule (OD-7, load-bearing efficiency decision):** anything that changes *slicer output* invalidates via the hash; anything that is pure post-slice arithmetic (`cost = mass × price/gram`, or `spool.price` override if set) is recomputed **without re-slicing**. Re-slicing for a price change wastes minutes of CPU — the Pre-Mortem flagged "re-slicing on every Spoolman price tick" as the top self-inflicted-DoS risk (R1). Target: a cost-only Spoolman change recomputes in <1s, not minutes.

**Spoolman linkage & custom overrides:** a `PrintIntentPreset` (or per-request line) MAY pin a specific Spoolman filament record, linked by **profile-style reference** (Init 19 B2 insight — link by profile, not by churning entity id, to isolate from Spoolman entity churn). Custom filament/process overrides — especially `filament_max_volumetric_speed`, nozzle/bed temps, density for TPU and unusual filaments — are mapped from the Spoolman `filament.extra` fields onto the resolved filament JSON, captured in `spoolman_overrides_ref`, and folded into `bundle_hash` so a Spoolman-side change to a mapped field correctly invalidates downstream estimates.

**Staleness is explicit, never silent:** a stale estimate is **served with a `stale` flag** (UI: "estimate may be out of date, recomputing") rather than hidden — matching the Init 19 soft-fail / `stale since HH:MM` pattern. Soft-fail when the worker is down serves the last cached estimate with a "Last estimated HH:MM (Xm ago)" indicator.

**Observability:** every slicer-worker job + any outbound Spoolman read is instrumented per `~/repos/configs/docs/observability-logging-contract.md` (structured-log tags + OTel span + GlitchTip breadcrumb); g-code bodies are NOT logged in full.

### Gated capability (explicitly OUT of scope, architecture-relevant)

**Adaptive / variable layer height — GATED** on a proven negative (`adaptive_layer_height=1` did NOT change the layer-Z schedule or estimates vs fixed 0.20 mm for Qstool). The data model must **not** bake in "estimates assume uniform layer height" in a way that blocks a later variable-height bundle, but no MVP work goes here. **Spike exit criterion:** demonstrate a CLI-only path produces a *different, correct* layer schedule + estimate for a known part.

### Cross-references

- PRD: `prd.md` § Initiative 20 (FR20-* + NFR20-* link back to Decisions AH + AI + AJ).
- Epics: `epics.md` § Initiative 20 (Story 32.1 implements Decision AH; Story 32.2 implements Decision AI; Stories 32.3 + 32.4 implement Decision AJ; Story 32.5 implements the Spoolman override mapping; Story 32.6 is the frontend preset + estimate display).
- Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2.
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md` (§ 2 data model + ownership topology, § 3 resolver, § 4 slicer-worker, § 5 invalidation rules, § 7 security/ops, § 8 risk register, § 9 OD register).
- Configs-side coordination: `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` PR per Decision AI — **NOT a 3d-portal commit**; HC2 trip-wire honored.
- Inventory SoT: Initiative 19 (Spoolman) — the slicer initiative consumes Spoolman filament records + `filament.extra.url`, does not own or duplicate inventory.
- Memory entries informing decisions: [[feedback_scp_pre_enumeration_phase]] (cache-topology enumeration § B + magic-constant contract pointing § C apply to the resolver hash constants, the `(stl_hash, bundle_hash)` cache key, the slice-concurrency cap, and the Orca/timeout literals in every Init 20 story spec).

## Initiative 21 — Admin-Managed Orca Process Profiles + User-Facing Selector Options

**Status:** 🚧 in-progress (started 2026-06-04). Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` (status `approved-but-corrected` — operator go; approval scoped to planning-artifact appends, NOT code implementation). Init 21 introduces two architectural decisions for an **admin-managed Orca process-profile surface** that drives **admin-approved + material-compatible** user-facing estimate options. The decisions are grounded in shipped Init 20 code — the resolver, its fixed vendored layout, the EST-TIERS-1 availability seam, the admin auth/router/upload patterns — not blue-sky; this is the phase-3 graduation of the SCP's pre-enumeration save (§ 2). All app-layer code is portal-owned; the only configs-side item (portal-content RW mount) is isolated to the write slice (HC2 boundary).

> ⚠️ **DOMAIN-MODEL CORRECTION (2026-06-06).** Decisions AK + AL below model the admin/profile surface around the **fixed `printer_ref × material_class × quality_tier` slot grid + fused intent triple**. Per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md`, that grid is **NOT the canonical domain model** — it is a **transitional compiled-intent / resolver projection** (kept as MVP compatibility for the existing resolver/worker, not deprecated). The **canonical model is separate Orca-like building blocks** — `MachineProfile` (required for valid Orca slicing; real current Orca machine; later machine-capability material restrictions), `ProcessProfile` (**primary portal-facing block** — drives grams/material estimates, print strategy, quality choice), `FilamentProfile` (Orca-required; max volumetric speed, compatibility, time estimates, Spoolman material-type bridge) — plus `ProfileChain` (the compiled intent these Decisions already produce) and `PrintProfileOffer` (member/admin offer). **Decisions AK/AL therefore stand as the architecture of the *compiled projection*, not of the canonical profile model.** The OD-7 "compatibility map over the grid" is reclassified as an **interim expression of block/chain compatibility** (filament `material_type`/`compatible_printers`, machine capability, process↔filament validity will carry it natively in the block model), kept as the live gate behind the projection. Future profile/admin architecture (separate-block inventory; offer/chain layer) is authored when the re-pointed next slice (PROFILE-LIB-1 → PROFILE-OFFER-1) is sequenced; it **compiles into the same resolver intent path** so `bundle_hash` / append-only stores / provenance snapshots (NFR21-PROVENANCE-1) remain invariants — no forced migration.

### Pre-enumeration save (reuse + extend, never parallel-implement)

| Concern | Existing artifact (reuse/extend) | Posture |
|---|---|---|
| Resolver read contract | `apps/api/app/modules/slicer/resolver.py:114-123` `VendoredProfileSource` — `<root>/system/*.json` + `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json`; missing intent ⇒ classified `unsupported_material_class` (`:226`), never silent fallback | An imported profile IS, in resolver terms, an intent triple file in that path. The panel manages the *inputs* of this read. |
| Availability seam | `GET /api/estimates/quality-tiers` (`router.py:101-131`) resolves each `QUALITY_TIER_ORDER` (`:51`) tier and reports `{quality_tier, available, reason}` | Admin-ify, don't re-derive. Inventory read returns a **superset** (add provenance + import + compatibility metadata); the two must agree on resolvability (parity test). |
| Named FE↔BE grid contract | backend `QualityTier`/`MaterialClass` literals ↔ FE `QUALITY_TIERS` (`apps/web/src/modules/estimates/lib/preset.ts:25`) + `MaterialClass` mirror (`preset.ts:4,9`) | The compatibility map extends this contract (per-material allowed-tier table), backend SoT + FE mirror, parity-tested — same shape as `QUALITY_TIER_ORDER`↔`QUALITY_TIERS`. |
| Admin auth + router | `current_admin` / `admin_required` 403 (`apps/api/app/core/auth/dependencies.py`); admin router `prefix="/api/admin"` (`apps/api/app/modules/admin/router.py:29`) | Mount the profiles route here; reuse the guard; keep it out of `_PUBLIC_ROUTES` (Init 6 route-enforcement gate). |
| Multipart upload + audit | `apps/api/app/modules/sot/admin_router.py` `admin_upload_file` + `record_event` audit | Write slice mirrors this shape (JSON payloads, far smaller than STL). |
| FE admin surface | `apps/web/src/modules/admin/AdminTabs.tsx:6` (`ActiveTab = "users" \| "invites"`) + `routes/admin/`; `useAuth().isAdmin` gate | Extend `ActiveTab` with `"profiles"` + add `routes/admin/profiles.tsx`, mirroring `users.tsx`/`invites.tsx`. |
| Provenance / hash invariants | `bundle_hash` byte-pinned input order (`resolver.py`); `source_system_tree_hash` snapshot built for in-place edits (`resolver.py:300-309`); append-only stores, no slicer Alembic schema by design | Preserved, not edited (NFR21-PROVENANCE-1). An in-place system-tree write yields a new snapshot identity automatically — provenance safety is structural. |
| Read-only-at-runtime posture | vendored dir documented read-only at runtime (`config.py`) | A write path **reverses** this posture — a named decision (Decision AL / OD-2), contained to the write slice, not the read-only first slice. |

### Decision AK — Admin-managed profile inventory read + compatibility-map representation & enforcement

**Decision:** The admin profile inventory is a **read-only superset projection over the existing resolver**, NOT a new resolution path. For each `(printer_ref, material_class, quality_tier)` slot it returns `{imported, resolvable, compatible, reason, portal_label, provenance: {source_system_tree_hash, orca_version}}`, computed by:

1. **`resolvable`** — reuse the EST-TIERS-1 `resolve_preset` seam (the same logic behind `GET /api/estimates/quality-tiers`). The inventory and the public availability endpoint MUST agree on resolvability for the same slot (one source of truth, asserted by a shared parity test).
2. **`imported`** — file presence of the intent triple in `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` (the resolver's own input).
3. **`compatible`** — evaluated against the **compatibility map** (below).
4. **`provenance`** — projected from the resolved bundle's snapshot; **no Orca-internal keys, no file paths, no g-code** leak into the DTO (mirrors the existing no-internal-leak fence).

**Compatibility map (OD-7) — the load-bearing representation choice:** the map is a **first-class, explicit declaration**, NOT implied by mere file presence or by resolvability. Resolvability is **necessary but not sufficient** — a slot is offerable only when it is BOTH structurally resolvable AND declared compatible for its material class:

> **`offerable = imported ∧ resolvable ∧ compatible`**

- **Representation:** extend the existing named FE↔BE grid contract with a **per-material allowed-tier / compatibility table** (which `quality_tier` process slots are valid for each `material_class`). The **backend is the source of truth**; the FE mirrors it and a parity test asserts they agree — exactly the proven `QUALITY_TIER_ORDER` ↔ `QUALITY_TIERS` mirroring pattern (`router.py:51` ↔ `preset.ts:25`). No new free-text taxonomy.
- **Enforcement (read slice, Story 33.1):** the inventory **never marks an incompatible `(material_class, quality_tier)` slot as offerable**; a resolvable-but-incompatible slot (e.g. a PLA-class process profile sitting in a TPU slot) is reported as **not offerable** with a structured incompatibility `reason`. The projection that feeds the user selector excludes incompatible slots — asserted by a shared test so neither the admin grid nor the user selector can surface a TPU-incompatible process choice for TPU (nor vice-versa).
- **User-facing contract preserved:** `GET /api/estimates/quality-tiers` keeps its `{quality_tier, available, reason}` shape; the compatibility dimension folds into `available` (false when incompatible) and `reason` (carries the incompatibility cause). The DTO does not change shape.
- **Concrete data deferred:** the exact per-material compatible-slot set (e.g. which slots are TPU-compatible) is an **admin-data question** confirmed at the PRD/data phase, not a code constant baked here. The magic-constant discipline ([[feedback_scp_pre_enumeration_phase]] § C) applies: any concrete allowed-slot set in a story spec must point to the operator-confirmed material-compatibility contract, not to "what happens to resolve."

**Why a projection, not a new endpoint family:** re-deriving availability in an admin path would create a second source of truth that could drift from the member-facing endpoint — the precise failure class the parity test exists to prevent. The admin read is strictly a *superset* of the public read.

**Boundary:** Decision AK covers the **read** + the compatibility-map *representation and consumption*. **Authoring/editing** the map and **writing** profiles is Decision AL. Story 33.1 consumes the map read-only.

### Decision AL — Profile import write posture + on-disk metadata (no DB)

**Decision:** A validated import writes the intent triple **directly, in-place** into `SLICER_VENDORED_PROFILES_DIR/intents/<printer_ref>/<material_class>/<quality_tier>.json` (OD-2), with admin metadata in an **on-disk sidecar manifest** and who/when in the **existing admin audit log** — **no Alembic migration, no slicer DB schema** (OD-4). This is the write slice (Story 33.2) and owns the only novel risk in the initiative.

**Import validation (two gates, both required before publish):**

1. **Structural resolvability (OD-3):** run the existing `resolve()` merge/normalize/required-keys path (default `NullCliValidator`) — availability == resolvability is the live contract; this is exactly what determines the user-facing 422/availability today. Real-Orca CLI slice-validation (worker-only) is an optional async follow-up, NOT in v1.
2. **Compatibility (OD-7 / Decision AK):** the target slot must be declared compatible for its material class. An import targeting an incompatible slot (e.g. a non-TPU process profile into a TPU slot) is **rejected with a clear structured reason** and is NOT published/exposed — `resolvable ∧ ¬compatible` is still not offerable. The rejection reason surfaces in the admin panel.

**Write posture (named reversal):** the vendored dir is documented as **read-only at runtime** (Init 20 / `config.py` — "exported artifacts, never a live read at resolve time"). An admin write reverses that posture. Per the repo's NFR-carve-out-reversal discipline, this is a **deliberate, named decision** contained to the write slice — the read-only first slice (Story 33.1) does not touch it. The write reuses the `sot/admin_router.py` multipart + `_write_atomic` + `record_event` shape (JSON payloads are far smaller than the STL uploads that pattern already handles).

**Provenance safety is structural (NFR21-PROVENANCE-1):** the `source_system_tree_hash` snapshot (`resolver.py:300-309`) was deliberately built for in-place edits of vendored profiles, so an admin write that mutates the system tree yields a **new snapshot identity automatically** — the panel does not re-invent provenance. Importing a profile MUST NOT perturb the `bundle_hash` of an unrelated already-persisted bundle (byte-pinned input order is preserved); the append-only bundle/estimate stores are not edited.

**On-disk sidecar manifest (OD-4):** admin metadata — portal label, importer, timestamp, original filename, status, and **per-slot compatibility status + reason** — lives in a sidecar manifest in the vendored tree, consistent with the slicer subsystem's no-DB / append-only posture. The PROFILE-ADMIN-1 inventory read (Decision AK) reflects this manifest as the single source of truth for the compatibility decision per imported slot. A DB-table alternative was considered and **not** recommended for v1 (would introduce the slicer subsystem's first Alembic schema, against its documented Boundaries).

**Configs/app boundary (HC2, write slice only):** if the import writes to the portal-content volume from the api container, the portal-content volume RW mount is a `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` (+ api compose) coordination item — **NOT a 3d-portal commit**. **Deploy-safety:** vendored profiles are *data* on the shared `portal-content` volume, not code in the worker image, so an admin write is visible to the slicer-worker overlay **without an image rebuild** — this initiative does **not** trip the SW-DEPLOY-1 overlay-rebuild gate (no new slicer module). The read-only first slice is a pure API+web change on the standard deploy path.

**OD-6 (re-slice on import):** NOT in the read slice; optional in the write slice and **gated on EST-PARSE-1** (the estimate parser/backfill pipeline being healthy). Reuse the existing EST-RECOMPUTE-1 `POST /api/estimates/recompute` per (stl_hash, preset) rather than a new bulk-enqueue surface.

### Decision AM — Separate-block Orca profile library (additive inventory; PROFILE-LIB-1)

> Added 2026-06-06 by Story PROFILE-LIB-1, per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 3–§ 6. Decisions AK/AL above are the architecture of the **compiled-intent projection** (the fixed grid); Decision AM is the FIRST architecture of the **canonical separate-block model**.

**Decision:** the operator manages separate Orca profile **blocks** (`machine` / `process` / `filament`) in a small **additive** inventory, **disjoint from and coexisting with** the AK/AL grid. Imported blocks live in a new subtree under the SAME `SLICER_VENDORED_PROFILES_DIR` root: `<root>/library/<profile_type>/<block_id>.json` (the verbatim Orca block body) + `<root>/library/<profile_type>/<block_id>.manifest.json` (a curated-metadata sidecar v1 — a NEW schema, distinct from the AL intent-manifest). This is **inventory CRUD only** (import / list / get-curated-detail / delete), ahead of the offer/chain layer (Decision AN / PROFILE-OFFER-1).

**Block identity (path-safe by construction):** `block_id = uuid5(NAMESPACE_URL, "<profile_type>:<orca name>").hex` — derived **server-side**, never from the upload, so it is a 32-char hex string (no attacker-controlled path segment) and is **stable on re-import** of the same `(type, name)` (an UPSERT). This **structurally eliminates** the path-traversal class the AL `printer_ref` write path had to gate (`is_safe_printer_ref`/`is_within_intents_root`); a `<root>/library` containment assert is still applied (defense-in-depth), and the `{block_id}` route param is hex-validated.

**Classify → extract → validate (curated-metadata-only):** the backend (`slicer/profile_library.py`) **classifies** a block (explicit Orca `type` field preferred, structural-key heuristics as fallback, ambiguous ⇒ `unsupported` reject); **extracts MINIMIZED curated metadata** (`name`, `profile_type`, `inherit`+resolved chain, `settings_id`, filament `material_type`/`compatible_printers`, `source`/`is_system`) with the SAME leak fence as the AK/AL DTOs — **no raw Orca key body, no g-code, no path** crosses the wire or the audit; and **derives** `usable` / `requires_attention` / `error`. The Fenrir governance rule (a user **process** block must inherit a **system** process profile — Orca silently drops an invalid user-process inheritance) is surfaced as a `requires_attention` flag, not silently repeated. **There is no raw-Orca-JSON viewer** (SCP § 6).

**Reuses the AL safety foundations verbatim:** atomic two-phase publish (body+manifest, rollback-safe), `ezop:ezop 664` owner/mode preservation on the operator-managed bind mount (the `31bcf0c` fix), `sanitize_original_filename`, the leak fence, and the audit log (`slicer_profile.library_import` / `.library_delete`, reusing the `slicer_profile` entity_type — no Alembic, no DB; SCP § 4 no-DB posture).

**Coexistence + invariants:** Decision AM adds the library **alongside** the AK/AL grid with **no data migration** — it never touches `resolve()`, `compatibility.py`, the `intents/`/`system/` trees, `bundle_hash`, or the append-only bundle/snapshot/estimate stores, so NFR21-PROVENANCE-1 holds trivially (the library never enters the resolve/bundle path). The library engine runs **api-side** and blocks are **data** on the shared volume → **SW-DEPLOY-1 not triggered**. The offer/chain layer that *compiles* selected blocks into the existing resolver intent path is **Decision AN / PROFILE-OFFER-1** (the next slice).

### Decision AN — PrintProfileOffer / ProfileChain layer (additive offer surface; PROFILE-OFFER-1)

> Anchored 2026-06-06 by Story PROFILE-OFFER-1, per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 3.4–3.5, § 6 ("THEN" step), and § 8 (UX gate). Decision AM is the architecture of the separate-block **library**; Decision AN is the FIRST architecture of the **offer/chain** surface that consumes it. Decisions AK/AL (the fixed grid) remain the **transitional compiled-intent projection** feeding the member selector — untouched.

**Decision:** the operator composes a **`PrintProfileOffer`** by selecting **exactly one** `machine` + **one** `process` + **one** `filament` block from the Decision AM library — an embedded **`ProfileChain`** value object `{machine_block_id, process_block_id, filament_block_id}` — plus a member/admin `label`, `visibility ∈ {hidden, visible}`, an `is_default` flag, and `compatible_material_categories` (the small generic `{PLA, PETG, PCTG, TPU}` bridge — SCP § 3.6). Offers live in a NEW subtree under the SAME `SLICER_VENDORED_PROFILES_DIR` root, **disjoint from** `system/`, `intents/` (grid), and `library/` (blocks): `<root>/offers/<offer_id>.json` (a curated offer sidecar v1 — a NEW schema, no raw Orca body because an offer carries only curated refs). This is **offer data-model + admin CRUD + dry validation only**; it does **NOT** compile a chain into the resolver intent path or slice (that bridge is the explicitly-gated **G-PUBLISH** step — a later slice).

**Offer identity (path-safe, stable across edits):** `offer_id = uuid4().hex` — minted **server-side** at create time, never from the request, so it is a 32-char hex string (no attacker-controlled path segment) and is **immutable across `label`/`visibility`/`is_default`/`category` edits**. This deliberately **differs** from the AM `block_id = uuid5(type:name)` (derived from a block's *immutable* `(type, name)` to make re-import an UPSERT): an offer has no immutable natural key (every offer field except identity is mutable), so a minted token is the correct identity, and a `<root>/offers` containment assert + hex-validated `{offer_id}` route param close the traversal class.

**Dry chain-validation (NO resolve, NO slice):** the backend (`slicer/profile_offer.py`) validates a chain by **reading the referenced blocks' curated manifests only** (`profile_library.read_block`) — it does **NOT** call `resolve()`, read raw Orca bodies, write `intents/`, or slice. It derives `usable` / `requires_attention` / `invalid` (`invalid` for a missing block / wrong block type / unusable block — a hard `422 invalid_chain` reject on create; `requires_attention` for a flagged block, a filament↔machine `compatible_printers` mismatch, a material-category mismatch, a hidden-default, or a duplicate default across visible offers). Validation is **recomputed at read time** on list/get so a deleted referenced block surfaces as `invalid unknown_block` rather than a stale `usable`. The same leak fence as the AK/AL/AM DTOs holds — **no raw Orca key body, g-code, or path** crosses the wire or the audit (a `chain_blocks` echo reuses the AM `ProfileLibraryBlock` curated DTO). Deeper Orca process↔filament *slice-time* validity is deferred to G-PUBLISH (it needs the resolver path).

**Reuses the AM/AL safety foundations verbatim:** atomic publish (`import_service.publish_pair`), `ezop:ezop 664` owner/mode preservation on the operator-managed bind mount (incl. the `221bbe1` fresh-directory metadata-inheritance fix), the leak fence, the `<root>` containment assert, and the audit log (`slicer_profile.offer_create` / `.offer_update` / `.offer_delete`, reusing the `slicer_profile` entity_type — **no Alembic, no DB**; SCP § 4 no-DB posture).

**Coexistence + invariants:** Decision AN adds the offer surface **alongside** the AK/AL grid and the AM library with **no data migration** and **no resolver publication in this slice** — it never touches `resolve()`, `compatibility.py`, the `intents/`/`system/` trees, `bundle_hash`, the append-only stores, or the AM library *write* path (offers only **read** the library), so NFR21-PROVENANCE-1 holds trivially. The engine runs **api-side** and offers are **data** on the shared volume → **SW-DEPLOY-1 not triggered**. The FE offer-composition UI is **gated on a UX checkpoint** (G-UXGATE; SCP § 8 — offer composition is relationship UI), and **real resolver publication / live slicing is G-PUBLISH** (a later slice); until then the member selector keeps consuming the AK/AL grid projection unchanged.

### Decision AR — offer-chain publish bridge: chain-addressed resolve → real bundle_hash → one live slice (PROFILE-PUBLISH-1; G-PUBLISH backend half)

> **Accepted** 2026-06-06 by G-ARCH for Story PROFILE-PUBLISH-1 (status `draft`), per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 3.4/§ 6/§ 7/§ 10 and Decision AN (which named real resolver publication / live slicing as the later **G-PUBLISH** slice, provisionally "PROFILE-OFFER-2"). **G-ARCH satisfied** — Gemini architecture review APPROVE (`.hermes/run-logs/g-publish-gemini-architect-20260606_210937.log`) confirmed option (b) as the mechanism before dev-story; this records (b) as accepted. Decision AR consumes Decision AM (library bodies) + Decision AN (offer/chain); Decisions AK/AL (the grid projection feeding the member selector) remain **untouched**.

**Mechanism fork resolved by G-ARCH (load-bearing):**
- **Option (a) — intent-coordinate publish (REJECTED as default):** publishing writes/overlays an `intents/<printer>/<material>/<tier>.json` triple derived from the chain's three blocks. Rejected because an offer has **no** grid coordinate, so this forces a *synthetic* `(printer, material, tier)` and writing into the grid `intents/` tree risks colliding with / overwriting the **transitional grid projection that still feeds the member selector** — a direct violation of SCP § 4 (grid KEPT, coexist, no forced migration) and the OFFER-1/LIB-1 fence (never touch the `intents/`/`system/` trees).
- **Option (b) — chain-addressed resolve-tail (RECOMMENDED):** a new resolver entry resolves a `ProfileChain` **directly from its three library block bodies**, reusing the existing `resolve()` tail **verbatim** (inheritance-merge → `normalize_for_cli` → required-key schema check → CLI smoke validation → `compute_bundle_hash` → persist `SlicerProfileBundle` + `SourceProfileSnapshot` append-only) **without** reading or writing the `intents/`/`system/` (grid) trees and **without** minting a synthetic grid coordinate. Faithful to SCP § 3.4/§ 6/§ 10 — "the existing resolver intent **path**" means the resolve→bundle→slice **machinery** (single SoT), not the grid **directory**; `bundle_hash` and the append-only stores are preserved exactly; the offer publish stays **disjoint** from the grid intents tree (consistent with the offer sidecar being disjoint from `system/`/`intents/`/`library/`).

**Decision (accepted by G-ARCH):** option (b). A new `slicer/profile_publish.py` orchestrates the bridge — chain-addressed resolve (reusing the `resolve()` primitives, no second resolution path; SCP § 7), append-only persistence via the existing `BundleStore`/`EstimateStore` + `enqueue_slice_estimate`, an **additive** publish-state block on the existing `<root>/offers/<offer_id>.json` sidecar (`published_bundle_hash`/`published_at`/`published_by`/`publish_state`/`source_snapshot_ref`; sidecar `offer_manifest_version` bumps to `"2"`, v1 reads forward as `unpublished`) written via the shared atomic `import_service.publish_single` + `ezop:ezop 664` owner/mode preservation, and exactly **one** live slice/estimate over one operator-designated catalog STL. The publish step is the **first legitimate reader of the raw library block body** (`<root>/library/<type>/<block_id>.json`; OFFER-1 read only the `.manifest.json`).

**Coexistence + invariants:** Decision AR preserves the Init 20 `bundle_hash` input order (`machine ∥ process ∥ filament ∥ orca_version [∥ overrides_ref]`, `overrides_ref=None` for an offer with no concrete override — backward-compatible, hash unchanged) and the append-only store **layout** — publishing is additive, re-publishing the same chain is byte-stable/idempotent (`os.link` first-write-wins), and an unrelated bundle is byte-unchanged (NFR21-PROVENANCE-1). NFR21-NO-422-1 holds trivially (no new member-reachable resolve — the member selector is unchanged). **Escalation:** this is the **first E33 slice to touch the resolve/bundle/slice path** and the worker consumes the published bundle → **SW-DEPLOY-1 IS triggered** (overlay rebuild + worker smoke, fatal-on-fail), unlike the deploy-clean AM/AN slices. The **member-facing** offer surface (offer-as-member-choice) stays deferred to **PROFILE-PUBLISH-2**.

### Cross-references

- PRD: `prd.md` § Initiative 21 (FR21-PROFILE-INVENTORY-1 + FR21-COMPAT-1 + FR21-PROFILE-IMPORT-1 + FR21-SELECTOR-1 + NFR21-* link back to Decisions AK + AL).
- Epics: `epics.md` § Initiative 21 (Story 33.1 implements Decision AK read + compatibility consumption; Story 33.2 implements Decision AL write + compatibility enforcement; Story 33.3 is the optional manage/lifecycle slice).
- Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` § 2 (pre-enumeration) + § 5 (open decisions) + § 6 (stories).
- Predecessor / superseded: Initiative 20 (resolver + EST-TIERS-1 availability seam); EST-TIERS-1 (`deferred-work.md`) — the disk-presence availability gate this initiative makes admin-managed.
- Inventory SoT: Initiative 19 (Spoolman) — process/intent profiles only; Spoolman is NOT touched.
- UX work item: **UX-PROFILE-1** (`bmad-ux`) — designs the *surfacing* of the AK compatibility map (admin grid + user selector), NOT the underlying rules. Blocks FE story ACs (NFR21-UX-1).
- Configs-side coordination: portal-content RW mount per Decision AL — **NOT a 3d-portal commit**; HC2 boundary honored; write slice only.
- Memory entries informing decisions: [[feedback_scp_pre_enumeration_phase]] (the pre-enumeration save above follows § A; the magic-constant contract § C applies to the per-material compatible-slot set + any import validation/size constants in every Init 21 story spec).

## Initiative 22 — Admin Operational Observability (Worker/Job Console)

**Status:** 🚧 planning (started 2026-06-06). Source SCP: `sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md` (status `proposed` 2026-06-06 — approval scoped to planning-artifact appends, NOT code implementation). Discovery + architecture/UX design: `_bmad-output/implementation-artifacts/spec-admin-jobs-console.md` (ADMIN-JOBS-1, commit `dcb9df8`). Init 22 introduces three architectural decisions for a **read-only, admin-only worker/job console** over the three live ARQ pools (API `arq:api`, Render `arq:queue`, Slicer `arq:slicer`). The decisions are grounded in shipped code (the FastAPI-lifespan-owned arq pool + raw Redis on `app.state`, the admin router/auth patterns, the existing business-keyed status keys) and the installed `arq==0.28.0` source — not blue-sky. All code is app-layer + read-only; **no worker image change → the SW-DEPLOY-1 overlay-rebuild gate is NOT tripped**, and there is no configs-side coordination.

### Pre-enumeration save (reuse + extend, never parallel-implement)

| Concern | Existing artifact (reuse/extend) | Posture |
|---|---|---|
| arq pool + raw Redis | `app.state.arq = await create_pool(...)` + `app.state.redis = RedisFactory(...)` created once in the FastAPI lifespan (`apps/api/app/main.py:64-94`), closed on shutdown | The console reads via `request.app.state.arq` / `.redis` — **never** an ad-hoc connection (project-context backend rule). |
| arq read surface | `ArqRedis.queued_jobs()` (`arq/connections.py:210`), `all_job_results()` (`:192`), `Job.status()`/`Job.info()` (`arq/jobs.py`), per-queue `<queue>:health-check` key + counters (`arq/worker.py:255-259,773-785`); key prefixes fixed in `arq/constants.py` | REUSE, do not invent. **Replace `all_job_results()`'s `KEYS arq:result:*` with a bounded `SCAN`**; use `zcard` for depth; avoid `queued_jobs()` (it deserializes args). |
| Business-keyed status keys | render worker `render:status:{model_id}` / `render:stl_preview:{model_file_id}` (60-min TTL); slicer `EstimateStatus` keyed `(stl_hash, bundle_hash)` | REUSE as the `context` layer ("what was this job about") instead of building a new ledger. |
| Admin router + auth | per-module `admin_router.py` mounted in `apps/api/app/router.py`; `current_admin` default-value dep (`apps/api/app/core/auth/dependencies.py:76`); route-enforcement gate (`apps/api/app/main.py:50` + `apps/api/tests/test_route_enforcement_gate.py`) | Mount the console route here; `current_admin`-gated route passes the gate with **no** `_PUBLIC_ROUTES` edit. |
| Admin FE chrome | `apps/web/src/modules/admin/AdminTabs.tsx` (Users/Invites/Profiles/…) + `routes/admin/*.tsx`; shell `AuthGate` discipline | EXTEND with one `"queues"` tab + `routes/admin/queues.tsx`, mirroring `profiles.tsx`. Adding a TanStack route ripples `routeTree.gen.ts` + AdminTabs visual baselines ([[reference_web_routetree_regen]]). |
| Member `/queue` slot | `apps/web/src/routes/queue/index.tsx` + `ModuleRail.tsx:10` — the **member-facing future print queue** (AGENTS.md v2 module), a "Coming soon" stub | **NOT this feature.** The console is operator/infra observability — it lives in the admin area, not the member slot (Decision AO location clause). |

### Decision AO — Admin queue-console read model + location + ledger-deferred

**Decision:** the console is a **read-only raw-arq live snapshot** computed **per-request** over the lifespan-owned `app.state` arq pool + raw Redis — **no new table, no worker instrumentation, no Alembic migration**. For each pool it computes:

1. **`queued`** = `redis.zcard(queue_name)` — exact, O(1), no scan.
2. **`worker`** = parse the `<queue>:health-check` string (counters `j_complete/j_failed/j_retried/j_ongoing/queued` + heartbeat timestamp) and compute age (Decision AP).
3. **`running_jobs`** = bounded `SCAN MATCH arq:in-progress:* COUNT <small>`; for each id, `Job(id).info()` for the function name (only) + curated context; attribute to queue. Cardinality ≤ total concurrency (≈ 1 api + 2 render + N slicer) so the SCAN is tiny.
4. **`recent`** = bounded `SCAN MATCH arq:result:* COUNT <small>` with a **hard cap**, each key `deserialize_result` → project to **allowlisted** fields only (Decision AQ), grouped by `JobResult.queue_name`. Results expire with arq's `keep_result` (~1h) so this list is ephemeral and **labelled Redis-resident** (NFR22-RETENTION-HONESTY-1).
5. **`context`** = derived from the **existing** business-keyed status keys (`render:status:{model_id}`, slicer `EstimateStatus`) and/or the job id (slicer's deterministic `slice:<stl_hash>:<bundle_hash>` yields a stl-hash prefix) — **never** from raw `args`/`kwargs`/`result`.

**Hard finding (drives the design):** arq's `all_job_results()` uses Redis `KEYS arq:result:*` (`arq/connections.py:192-208`), which blocks Redis — the "broad key scan" the controller warned against. The MVP **must** use a bounded `SCAN` with a hard cap, **never** an unbounded `KEYS` in a request path (NFR22-REDIS-LOAD-1).

**Data-model tradeoff (the controller-asked justification):** Option A (raw-arq snapshot only) is shipped for the MVP; Option C (hybrid raw-arq live layer + durable ledger for context-rich failure history) is the design target with the **ledger as an explicit deferred slice (G-LEDGER)**. Rationale: UC1/UC2 need only live state, answered exactly + cheaply by raw arq; UC3 needs failures legible past Redis TTL, which the MVP closes *cheaply* by reusing the existing business-keyed status keys instead of building a table that would touch every enqueue site + worker function + add an Alembic migration. Visibility-first: prove the surface with (A)+reuse before paying (B)'s cost.

**Location clause:** the console lives in the **admin area** (`GET /api/admin/queues` backend in a new `apps/api/app/modules/queue/` package per OD-4; FE `/admin/queues` admin tab), **NOT** the member-facing `/queue` print-queue module slot — conflating them would mis-scope a member module and put infra internals on a member route.

**Boundary:** Decision AO covers the read model, data-model tradeoff, and location. Liveness derivation is Decision AP; the privacy fence is Decision AQ.

### Decision AP — Worker-liveness tri-state from the coarse health key

**Decision:** worker liveness is a **tri-state derived from the `<queue>:health-check` key's presence + age**, honestly labelled — `alive` (present, age < interval), `idle/stale` (present, age ≥ interval), `unknown/down` (absent). The raw counters, heartbeat timestamp, and the **actual `interval_s`** (read from the worker's `health_check_interval`, not a chosen constant) are surfaced verbatim.

**Hard finding:** arq's `health_check_interval` defaults to **3600 s (1 hour)** and **none of the three pools override it** (discovery § 3/§ 6). So the health key is refreshed at most ~once/hour and "is this worker alive *right now*?" is **not** answerable at useful resolution from the health key alone. **Ruling: accept coarse (~1h) liveness for the MVP** — the *running/queued* signals UC1/UC2 actually need are exact regardless of health-key granularity. The console is honest about the coarseness (it shows the interval + heartbeat age). Lowering `health_check_interval` to ~30-60 s on each `WorkerSettings` (`apps/api/app/workers/__init__.py`, `workers/render/render/worker.py`, `apps/api/app/modules/slicer/worker.py`) would give near-real-time liveness but is a **worker-config change → worker image rebuild/redeploy**, out of this read-only API-only MVP — **deferred (G-LIVENESS)**.

### Decision AQ — Leak fence / read-only privacy contract (load-bearing)

**Decision:** the console **must never serialize raw arq payloads.** arq stores **pickled `args`, `kwargs`, and `result`** on every queued job and every result (`arq/jobs.py:58-64`); these can embed absolute paths, model internals, Spoolman data, or token material. The fence (each clause → an AC + negative test in the create-story spec):

1. **Admin-only** — `current_admin`; non-admin → 403, anonymous → 401; route-enforcement gate green with **no `_PUBLIC_ROUTES` edit**.
2. **Field allowlist, not denylist** — the DTO carries only `queue_name`, friendly `role`, `function`, `job_id`, counts, timings/ages, `success/outcome`, liveness, and a curated `context`. A test asserts the serialized response matches the allowlist and contains **no** `args`/`kwargs`/`result` keys (mirrors the 33.1 AC-9 provenance fence).
3. **No raw paths / no raw error bodies** — `error_class` is a curated category (exception type name at most), never a traceback/message; `context.ref` is an id / hash-prefix, never a filesystem path. Negative test asserts no path-like substrings (`/`, drive letters, `..`).
4. **No `args`/`kwargs` deserialization leak** — avoid `queued_jobs()` (it deserializes args); use `zcard` for depth + `Job.info()` (function name only) for the bounded in-progress set.
5. **No secrets, ever** (project-context cross-cutting rule); **No destructive surface** — `GET` only, no enqueue/abort/purge (NFR22-READONLY-1).

**Logging/observability:** namespaced logger `app.queue.admin`; structured JSON per `~/repos/configs/docs/observability-logging-contract.md`; **no payloads logged**.

### Deploy / cross-repo boundary

- **Deploy-safety:** the MVP is **API-read-only + FE**. No worker image change ⇒ the SW-DEPLOY-1 overlay-rebuild gate is **not** tripped; this is a pure standard-deploy-path API+web change (cf. 33.1's deploy-clean reasoning). The only deferred decision that would change this is OD-2's worker-interval lowering (G-LIVENESS) — it would add a worker redeploy + heartbeat-freshness smoke.
- **No configs-side coordination** — the console reads Redis already owned by the api process; no new mount, no new container, no nginx change.

### Cross-references

- PRD: `prd.md` § Initiative 22 (FR22-QUEUE-SNAPSHOT-1 + FR22-LIVENESS-1 + FR22-CONSOLE-UI-1 + NFR22-* link back to Decisions AO + AP + AQ).
- Epics: `epics.md` § Initiative 22 (Story 34.1 implements Decisions AO + AP + AQ as the single read-only MVP slice).
- Discovery: `_bmad-output/implementation-artifacts/spec-admin-jobs-console.md` (ADMIN-JOBS-1, commit `dcb9df8`) — grounds every seam cited above.
- Predecessor / sequencing: Initiative 21 (Epic E33) — the slice/recompute queues this console observes; **sequenced BEFORE G-PUBLISH** (Init 21 PROFILE-OFFER-1 real-resolver publication) so queue effects are observable before publishing begins.
- arq 0.28.0 grounding: `arq/constants.py` (key prefixes), `arq/jobs.py:25-64,152-169` (JobStatus + JobResult), `arq/connections.py:183-220` (`queued_jobs`, `all_job_results` = `KEYS`), `arq/worker.py:187-259,773-785` (health-check key + interval + counters).
- Memory entries informing decisions: [[feedback_scp_pre_enumeration_phase]] (the pre-enumeration save above follows § A; the magic-constant contract § C applies to the polling interval + `recent[]` SCAN cap in the Init 22 story spec), [[reference_web_routetree_regen]] (routeTree regen + AdminTabs baseline ripple from the new tab).

## Initiative 23 — Spoolman Filament Profile Estimates (Material-Default + Exact-Override Policy)

**Status:** 🚧 in-progress (started 2026-06-07). Source SCP: `sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md` (status `approved`). Single epic **E35**. Predecessors grounded in shipped code: Init 20 (Epic E32 — the `resolve()` → merge → normalize → override → hash → persist pipeline + the `(stl_hash, bundle_hash)` cache this builds on) and Init 19 (Epic E31 — the Redis-cached Spoolman snapshot + `spoolman_filament_ref()` reused, **no second live read**). Init 23 makes print estimates pick the Orca **filament** profile from a portal-owned **profile-selection policy** instead of the single material-class default the Init 20 resolver hard-wires today, classifying each estimate's profile provenance honestly. All code is app-layer; the 35.2 resolver integration adds **no** Alembic migration and **no** worker image change (the resolver module is shared by the api + slicer-worker images but the on-disk contract is unchanged) → the **SW-DEPLOY-1 overlay-rebuild gate is NOT tripped**. Distinct from Init 21 (Epic E33 — admin-managed Orca **process** profiles + offer/chain): this initiative owns the **filament**-profile selection policy keyed by Spoolman generic material.

### Pre-enumeration save (reuse + extend, never parallel-implement)

| Concern | Existing artifact (reuse/extend) | Posture |
|---|---|---|
| Profile-selection policy + store | `apps/api/app/modules/slicer/profile_policy.py` (Story 35.1 — `EstimateProfileSource`, `normalize_material`, `MaterialDefault`/`FilamentOverride`/`ProfilePolicy`, `ProfilePolicy.resolve_selection`, `ProfilePolicyStore`, `unknown_profile_refs`, `load_profile_policy`) | REUSE as the policy SoT. The precedence resolver is pure + shipped; 35.2 only **consumes** its `ProfileSelection`, it does not re-implement precedence. |
| Filament profile addressing | `intents/<printer_ref>/<material_class>/<quality_tier>.json` filament partial is `{"inherit": "<system filament profile name>"}`; `merge.resolve_inheritance` looks the parent up **by name** in `system_tree` (`merge.py` parent lookup) | An `orca_filament_profile_ref` **IS a system filament profile name**. The policy selection re-targets the filament partial's `inherit` to that name before inheritance resolution — REUSE the name-keyed merge, do **not** invent a second filament-addressing scheme. |
| bundle_hash identity | `resolver.compute_bundle_hash(machine, process, filament, orca_version, overrides_ref)` over `machine ∥ process ∥ filament ∥ orca_version ∥ overrides_ref` (Decision AH) | UNCHANGED hashing contract (NFR23-CACHE-INVARIANT-1). A different selected profile changes the resolved **filament** JSON, so the existing hash naturally separates exact/default/variant bundles; no new hash input. |
| Spoolman snapshot → material/ref | `SpoolsService.get_summary()` → `SpoolmanSnapshot.filaments`; `overrides.spoolman_filament_ref(f)` (vendor∥material∥name); the `build_spoolman_override_provider` snapshot→`filaments_by_ref` idiom (`overrides.py`) | REUSE the cached snapshot + the one ref function; **no** second live read. Soft-fail when the snapshot is cold/`None` (mirror `build_spoolman_override_provider`). |
| Override numeric layer | `overrides.apply_filament_overrides` + `overrides_fingerprint` (`filament.extra` → Orca keys) applied onto the filament **after** inheritance merge | UNCHANGED + correctly ordered: the policy chooses the **base** filament profile first; the `filament.extra` numeric layer applies **after** (SCP Task 4 step 4), so an override on top of a policy-selected base still re-hashes via `overrides_ref`. |
| Classified no-estimate | `ResolveReason` StrEnum + `ResolveFailure`; ingest's `if not isinstance(outcome, ResolveSuccess): … no enqueue` (`ingest.py`) | EXTEND `ResolveReason` with `unavailable_no_profile` (additive StrEnum value); the existing ingest/enqueue path treats any non-`ResolveSuccess` as "no enqueue, no silent wrong default" — so an unavailable selection **cannot** slice a fallback. |

### Decision AS — Portal-owned filament-profile-selection policy + classified `EstimateProfileSource` + opt-in resolver integration

**Decision.** Spoolman stays the source of truth for filament inventory and the **generic** material type (`PLA`, `PETG`, `PCTG`, `TPU`, `ABS`, …); the **portal** owns the mapping from that material — and optionally from a specific Spoolman filament — to a concrete Orca `FilamentProfile`. The mapping is a portal-owned **profile-selection policy** (Story 35.1, shipped): material-type default Orca filament profiles + optional per-Spoolman-filament exact overrides, with a pure precedence resolver and a file-backed `ProfilePolicyStore`. Every estimate carries a classified **`EstimateProfileSource`** (`exact_filament_mapping` / `default_material_profile` / `unavailable_no_profile`) so a fallback is never presented as exact and a missing profile is an explicit, non-blocking absence.

**Precedence (load-bearing contract).** `exact filament override > material-type default > unavailable`. A selected `spoolman_filament_ref` present + `enabled` in `filament_overrides` ⇒ `exact_filament_mapping`; else a normalized material present + `enabled` in `material_defaults` ⇒ `default_material_profile`; else `unavailable_no_profile` (profile ref `None`). A disabled entry falls through to the next level. Overrides are keyed by the churn-stable `spoolman_filament_ref()` (vendor∥material∥name), **never** the Spoolman integer id (NFR23-STABLE-KEY-1).

**Resolver integration (Story 35.2).** The Orca filament profile is chosen by policy **before bundle materialization**, folded into the resolve through the filament partial's `inherit`:

1. **Opt-in seam (backward compatibility).** `resolve()` gains an optional `profile_selection: ProfileSelection | None = None`. When `None` (every existing caller's default), the resolve is **byte-identical** to the Init 20 material-class-default path — same partials, same merge, same `bundle_hash` (NFR23-CACHE-INVARIANT-1). The policy only engages when a selection is supplied.
2. **Profile substitution.** For an `exact_filament_mapping` / `default_material_profile` selection, the resolver re-targets the filament partial's `inherit` to the selection's `orca_filament_profile_ref` (a system filament profile **name**) before `resolve_inheritance` runs. The chosen system profile materializes into the resolved filament JSON, so the **existing** `compute_bundle_hash` separates variants with no new hash input. Two generic PLA colors that resolve to the **same** default profile and carry no numeric extras produce a **byte-identical** filament ⇒ the **same** `bundle_hash` (one shared estimate bundle); a PLA Matt exact override re-targets to a **different** profile ⇒ a **different** `bundle_hash`.
3. **Classified absence — no wrong fallback.** An `unavailable_no_profile` selection returns `ResolveFailure(reason=ResolveReason.unavailable_no_profile)` **without** writing a bundle/snapshot. The ingest/enqueue path's `not isinstance(outcome, ResolveSuccess)` branch already declines to enqueue, so a missing profile yields an explicit, classified no-estimate state and **never** slices a guessed fallback (NFR23-NO-BLOCK-1's resolver half; the order/request path stays open — that absence is surfaced honestly by the 35.3 estimate API/UI).
4. **Override ordering.** The `filament.extra` numeric override layer (`apply_filament_overrides`) applies **after** the policy-selected base profile is materialized, so a numeric override on top of a policy base still re-hashes via `overrides_ref` (SCP Task 4 step 4). An exact/default selection with no numeric extras leaves `overrides_ref` absent, preserving the byte-identical-shared-bundle property.
5. **Selection sourcing (FR23-SNAPSHOT-MAP-1).** The `(material, spoolman_filament_ref)` fed to `ProfilePolicy.resolve_selection` is derived from the Init 19 **cached** snapshot (`SpoolsService.get_summary()` → `{spoolman_filament_ref(f): f}`) — **no** second live Spoolman read. When a selected ref is present its generic `material` is read from the snapshot map; when the snapshot is cold/`None` the resolver **soft-fails** to a caller-supplied fallback material (or `unavailable_no_profile`), never a hard error and never a guessed material (mirrors `build_spoolman_override_provider`'s degraded path).
6. **Result metadata.** `ResolveSuccess` carries the `ProfileSelection` (additive, default `None`) so the 35.3 estimate read API can surface `estimate_profile_source` + the selected material/ref + the Orca profile name without re-resolving. The bundle itself stays content-addressed and metadata-free.

**Observability (NFR23-OBS-1).** Selection/soft-fail logs carry the profile-source label + counts/reason categories only (filament count, `degraded` reason) — **never** full filament bodies (mirrors Init 20 NFR20-OBS-1).

**Validation seam (Story 35.4).** `unknown_profile_refs(policy, known_refs)` (shipped 35.1, pure) lets the admin save path reject a policy whose refs are not among the available/vendored Orca filament profile names **before** a deferred RC -17-style resolve failure. The "available filament profile names" set is the caller's input (the vendored `system_tree` filament profiles) — no concrete Orca ref is hard-coded in the model/tests.

**Deploy / cross-repo boundary.** 35.1 + 35.2 are app-layer: a new policy module + a resolver parameter + a small selection helper. No Alembic migration, no on-disk worker contract change ⇒ **SW-DEPLOY-1 NOT tripped**; standard deploy path. No configs-side coordination. Changing a material default changes **future** bundle hashes (old estimates remain as orphaned cache; active reads use the newly resolved key) — the bounded-backfill ergonomics of that invalidation are Story 35.6 (G-BACKFILL-OPT-IN: concrete per-filament overrides are operator-opt-in only, never part of the default matrix).

### Cross-references

- PRD/Epics: `epics.md` § Initiative 23 / Epic E35 (FR23-POLICY-1 + FR23-PRECEDENCE-1 → 35.1; FR23-RESOLVER-1 + FR23-SNAPSHOT-MAP-1 → 35.2; FR23-ESTIMATE-API-1 → 35.3; FR23-ADMIN-1 → 35.4; FR23-UI-LABEL-1 → 35.5; FR23-BACKFILL-1 → 35.6; NFR23-* link back to this Decision AS).
- SCP: `sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md` (§ Accepted product decision, § Data model target, § Implementation tasks 1–4).
- Shipped grounding: `apps/api/app/modules/slicer/profile_policy.py` (35.1); `resolver.py` (`resolve`, `_resolve_partials`, `compute_bundle_hash`); `merge.py` (`resolve_inheritance` name lookup); `overrides.py` (`spoolman_filament_ref`, `apply_filament_overrides`, `build_spoolman_override_provider`); `spools/models.py` (`SpoolmanSnapshot.filaments`); `ingest.py` (the `not isinstance(_, ResolveSuccess)` no-enqueue branch).
- Decision lineage: extends Decision AH (Init 20 — content-addressed `(stl_hash, bundle_hash)` resolve/cache) + Decision AJ (Init 20 — typed estimate record / override fingerprint); reuses Init 19 Decision AF (Spoolman snapshot mirror).
- Gates: **G-ARCH** (this section — appended before the 35.2 resolver integration); **G-DEVGO** (35.2–35.6 per-story `bmad-create-story` + dev-go; 35.2 delegated in this run); **G-UXGATE** (`bmad-ux` before/with 35.4 + 35.5 FE); **G-BACKFILL-OPT-IN** (35.6).

## Initiative 24 — Member-Facing Published Profile Offer Surface (PROFILE-PUBLISH-2)

**Status:** 🚧 planning (started 2026-06-13). Source SCP: `sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md` (status `proposed`). Single epic E36. Realizes the named PROFILE-PUBLISH-2 follow-on deferred by Decision AR (PROFILE-PUBLISH-1, AC-16).

### Overview

Init 24 bridges the published offer/chain layer (Decision AR — `bundle_hash` in append-only store, proven by PROFILE-PUBLISH-1) to the member-facing estimate surface, reusing E35's `EstimateProfileSource` metadata. The design goal is **read-only over already-published bundles**: no new slicer worker path, no Alembic/DB change, no SW-DEPLOY-1 trigger. The admin offer API is preserved unchanged; a separate member-accessible endpoint provides a hard DTO safety fence.

### Decision AT — Member-facing published-offer surface: separate safe DTO endpoint + estimate-by-offer read-only resolution

**Accepted (proposed)** 2026-06-13 for Initiative 24, per `sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md` § 4 and § 3 (scope boundary). Pending operator OD-1/OD-2/OD-3 confirmation before 36.2 dev-story.

**The three load-bearing choices:**

**Choice 1 — Separate member endpoint vs. extending the admin endpoint.**
The admin `GET /api/admin/profiles/offers/` returns the full sidecar DTO (including internal fields needed by admin). Extending it to be member-accessible would require hiding fields at the serializer layer and risks future leakage as the admin DTO grows. **Decision: a new, separate `GET /api/profiles/offers/published` endpoint** with a purpose-built `MemberPublishedOfferView` DTO that includes only: `offer_id`, `portal_label`, `quality_tier`, `compatible_material_categories`, `printer_name`. Explicitly **excluded** from this DTO: `bundle_hash`, raw Orca profile ref names, chain block bodies, `sidecar` internals, `profile_chain`, `publish_state` (implied by the endpoint — only published offers are returned). NFR24-LEAKFENCE-1 is verified by a negative DTO test that asserts none of the excluded field names appear in the serialized response.

**Choice 2 — Estimate-by-offer resolution: read-only over existing published bundles.**
PROFILE-PUBLISH-1 proved that a published offer has a real `bundle_hash` in the append-only bundle store and at least one estimate in `EstimateStore`. Init 24's estimate-by-offer path **reads** that existing estimate rather than triggering a new resolve/slice. The resolution is: `offer_id` → sidecar read → `publish_state.bundle_hash` → `EstimateStore.read(stl_hash, bundle_hash)` → `EstimateView` (with E35 `estimate_profile_source` metadata passthrough). If the estimate does not exist yet (not yet computed for this STL): return `{status: "not_computed", offer_id: ...}` — **no on-demand enqueue in this slice** (SW-DEPLOY-1 NOT triggered; future G-ENQUEUE gate named). If the offer is not published or not found: 404. NFR24-NO-422-1: the resolve path has no branch that can produce a 422 (no live Orca call, no `resolve()` call).
**OD-1 (endpoint shape):** Proposed default: extend existing `GET /api/estimates` with an optional `offer_id` query param (backward-compatible; callers without `offer_id` use the existing resolve path unchanged). Alternative: new `GET /api/estimates/by-offer`. **To be confirmed by operator before 36.2 dev-story.**
**OD-2 (filament context):** An optional `spoolman_filament_ref` query param; when absent, the E35 policy resolver uses material-default only. This lets the frontend pass the member's currently selected spool ref to disambiguate exact vs default resolution. **To be confirmed by operator before 36.2 dev-story.**

**Choice 3 — G-UXGATE for 36.3 FE (consistent with Init 21 PROFILE-OFFER-1 precedent).**
The member offer picker is a new member-facing UI surface. Consistent with Init 21's `UX-PROFILE-OFFER-1` gate before the FE composition UI, **G-UXGATE is required before Story 36.3 dev-story** — a `ux-profile-publish-2-member-offer-picker` `bmad-ux` work item must produce a UX spec (layout, selection mechanic, honesty label placement, unavailability states) before 36.3 FE implementation begins. 36.1 + 36.2 backend stories may proceed in parallel with the UX work item.
**OD-3:** Does the operator want to schedule the UX gate now (parallel with backend) or defer 36.3 until after 36.2 is on `main`? **Proposed default: G-UXGATE required; schedule as parallel work item.**

**AuthGate discipline (NFR24-AUTHGATE-1, carry-forward from Init 10):** the offer picker component must NOT redirect when auth state is unknown or anonymous. Defer to shell `AuthGate` for the unauthenticated case; only block for `authenticated-but-unauthorized` (which is impossible here since offer picker is member-accessible, so only anonymous → `AuthGate` handles). Pattern: same as Init 12 / share-view components.

**Invariants preserved:**
- Admin offers API (`/api/admin/profiles/offers/*`) — unchanged, no new param, no new auth shape.
- 33.1/33.2 fixed-grid projection — unchanged; members who do not interact with the offer picker continue to see the existing estimate display.
- `bundle_hash` input order + append-only store layout — not touched (read-only consumption).
- E35 `EstimateProfileSource` — consumed from existing `EstimateView` DTO; no modification.
- `compatibility.py` grid — not touched.
- Alembic / DB — no migration.
- SW-DEPLOY-1 — NOT triggered (all new code is read-only over the existing offer sidecars + bundle store + estimate store; no new slicer worker path).

**Named deferred gate:**
- **G-ENQUEUE**: member-triggered on-demand estimate enqueue (when `not_computed`). Deferred to a follow-on story. Naming it here prevents it from silently bleeding into 36.2's scope.

### Cross-references

- PRD/Epics: `prd.md` § Initiative 24; `epics.md` § Initiative 24 / Epic E36 (FR24-* → 36.1–36.3; NFR24-* link back to this Decision AT).
- SCP: `sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md` (§ 3 scope, § 4 architecture, § 5–6 FR/NFR, § 7 story breakdown).
- Decision lineage: consumes Decision AR (PROFILE-PUBLISH-1 — published bundle_hash in append-only store) + Decision AS (E35 `EstimateProfileSource` metadata); reuses Decision AK (compatibility map, not modified) + Decision AJ (estimate store + `EstimateView` shape).
- Gates: **G-DEVGO** (36.1 implementation BLOCKED until create-story + dev-go); **G-UXGATE** (`ux-profile-publish-2-member-offer-picker` required before 36.3 FE); **G-ENQUEUE** (on-demand member-triggered enqueue — named deferred, not in this slice); **OD-1/OD-2/OD-3** (operator confirmation before 36.2 dev-story).
