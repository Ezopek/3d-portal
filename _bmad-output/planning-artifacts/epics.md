---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip-distillate.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
  - _bmad-output/planning-artifacts/architecture.md
persistentFacts:
  - _bmad-output/project-context.md
project_name: '3d-portal'
user_name: 'Ezop'
date: '2026-05-09'
last_updated: '2026-05-21'
last_update_note: 'Initiative 5 planning chain extension (Session D of 5-session handoff B-F per sprint-change-proposal-2026-05-18-init5.md, status approved). Appended ## Initiative 5 H2 section: Overview + Requirements Inventory (FR↔Epic + NFR↔Epic matrices) + Epic List + Epic 6-10 (#### H4) + Stories 6.1-6.7 / 7.1-7.6 / 8.1-8.6 / 9.1-9.4 / 10.1-10.4 (##### H5) + Cross-references. Each Story cites realized FR5-*/NFR5-* IDs + architectural anchor (Decision A-K letter from architecture.md § Initiative 5). Project-global epic numbering E6-E10 + story IDs <epic>.<local-num> per CC §3.4 vanilla-alignment correction. E9 flagged as HARD GATE prominently; E10 blocked-by E9 PASS (zero open Critical/High; ≤3 accepted-rationale Mediums per NFR5-SEC-1). Initiatives Index table + frontmatter initiatives array updated with Init 5 entry (status planning). Init 0/1/2/3 sections unchanged. Manual edit per CC §4.3 — no bmad-edit-epics skill exists; monolithic H2-append pattern is canonical workaround per AGENTS.md vanilla-first subsection v2 (2026-05-18). 2026-05-19 fixes applied per Codex bmad-check-implementation-readiness review (implementation-readiness-report-2026-05-19.md, status needs_work_before_implementation, 0 critical / 5 major / 3 minor): M4 — Story 8.4 expanded from force-enrollment-only to "Admin 2FA overrides (force-enroll + force-disable)" with explicit `POST /api/admin/users/{id}/force-disable-2fa` endpoint anchoring the lost-2FA recovery flow; Story 8.5 ambiguous "planned admin-disable path" phrasing replaced with explicit two-step recovery flow (8.4 force-disable → 8.5 reset). m1 — Story 8.2 gained negative AC bullet (FR5-ADMIN-4 enforcement: Playwright asserts absence of bulk-select / bulk-action selectors). FR5-ADMIN-4 matrix row updated with 8.2 anchor. M1/M2/M3/M5/m2/m3 acknowledged as by-design (per CC §3.3 hard rule #4 deferring granular Given/When/Then to bmad-create-story) or forward guidance for Sesja G+. Next session: F (bmad-sprint-planning, fresh context, gated by Codex IR PASS-for-sprint-planning verdict).'
projectMode: 'brownfield'
classification:
  projectType: web_app
  domain: general
  complexity: low
  projectContext: brownfield
releaseMode: phased
status: 'complete'
completedAt: '2026-05-09'
totalEpics: 3
totalStories: 15
storiesByEpic:
  E1: 6
  E2: 5
  E3: 4
conditionalStories:
  - E1.1.4 (HAPPY-PATH only — gated on E1.1.1 outcome)
  - E1.1.5 (HAPPY-PATH only — gated on E1.1.1 outcome)
initiatives:
  - id: 0
    name: 'Product Foundation — Home 3D-Printing Catalog'
    status: 'shipped_retrospective'
    completed: '2026-04 (v1 cutover)'
    documented: '2026-05-15'
    epics: 'E0 (Foundation epics shipped retroactively — catalog / auth / share / admin / sot / runbook / render / infra)'
  - id: 1
    name: 'Useful GlitchTip Delta'
    status: 'shipped'
    completed: '2026-05-10'
    epics: 'E1-E3 (Production-Readable Stack Traces / Triage-Ready Events / Verify Ritual)'
  - id: 2
    name: 'Agent Runbook + Legacy SoT Triage'
    status: 'shipped'
    started: '2026-05-10'
    completed: '2026-05-11'
    epics: 'E4 (Self-Serving Agent Runbook + Legacy SoT Triage) — 5 MVP stories DONE + 4-4-followup DONE + retro DONE; 4.6 deferred Growth'
  - id: 3
    name: 'UI Theme Compliance & Visual Regression Hardening'
    status: 'shipped'
    started: '2026-05-13'
    completed: '2026-05-13'
    epics: 'E5 (UI Theme Compliance & Visual Regression Hardening) — 17 stories DONE + retro DONE single-session autonomous'
  - id: 5
    name: 'Public Registration & User Account Management'
    status: 'shipped'
    started: '2026-05-18'
    completed: '2026-05-20'
    epics: 'E6 (Member role + invite-based registration) → E7 (TOTP 2FA + recovery codes) → E8 (Admin panel: users + invites) → E9 (Security audit — HARD GATE blocking E10) → E10 (Edge cutover — atomic). Closing commits: 7e5aea0 (cutover) + 2429157 (retro). All 27 stories shipped.'
  - id: 6
    name: 'Post-Cutover Default-Deny Auth Posture'
    status: 'shipped'
    started: '2026-05-20'
    completed: '2026-05-21'
    epics: 'E11 (Post-cutover default-deny auth posture) with 7 stories (11.1-11.7). NFR6-SEC-1 HARD GATE PASS (69/69 auth-boundary probe + 3/3 route enforcement test). Closing commit 2641b6c. External verification post-close via ezop-kbk.ddns.net 2026-05-21T15:07Z: cutover-smoke 5/5 PASS, pen-test 28 PASS / 4 FAIL-triaged-to-FP.'
  - id: 7
    name: 'Account & Admin UX Polish'
    status: 'planning'
    started: '2026-05-21'
    epics: 'E12 (Account & Admin UX Polish) with 5 stories (12.1-12.5): admin invites unblock + i18n + layout, admin users inactive-filter, display name on registration + self-service edit, settings hub + 2FA discoverability + user-menu link, sessions UX (pagination/sort/UA-filter). Each story carries NFR7-UX-1 mandatory pre-CR agent-browser visual-verification gate.'
  - id: 8
    name: 'Catalog Mobile & Image Performance'
    status: 'planning'
    started: '2026-05-21'
    epics: 'E13 (Catalog Mobile & Image Performance) with 2 stories (13.1-13.2): mobile carousel arrows at ≤sm breakpoint, thumbnail pipeline (Pillow on-upload + 800px WebP @ q80 + query-param variant endpoint + backfill script).'
  - id: 9
    name: 'Test Isolation Cleanup'
    status: 'planning'
    started: '2026-05-21'
    epics: 'E14 (Test Isolation Cleanup) with 3 stories (14.1-14.3): vitest admin module finder fixes (18→0 failures), pytest hydrate DB-pollution close, visual-regression hook-context flake fix. Test-infrastructure only per NFR9-SCOPE-1. Promoted from TB-018 via operator scope-pull. Scheduled FIRST in SCP execution chain.'
  - id: 10
    name: 'Operator Polish Batch'
    status: 'planning'
    started: '2026-05-22'
    epics: '3 epics: E15 (Test Health & Determinism, 3 stories 15.1-15.3 — pytest threading deadlock + visual baselines refresh + per-file client fixture refactor); E16 (Catalog Power-User Features, 6 stories 16.1-16.6 — ModelNote bilingual schema + on-demand Generate description + anonymous share-link viewer + admin manual model-add + admin file-upload + bulk STL download ZIP restore); E17 (Operator UX & Backlog Sweep, 4 stories 17.1-17.4 — admin tables fluid full-width + TB-016 runbook doc-honesty + DOC-DRIFT-2 close + baseline regen).'
  - id: 19
    name: 'Spoolman Read-Only Inventory (MVP-A)'
    status: 'planning'
    started: '2026-05-29'
    epics: 'E31 (Spoolman Read-Only Inventory, 5 stories 31.1-31.5 — backend httpx client + Redis cache + arq poll job + env config (31.1); backend `/api/spools/*` routes + DTOs with cost-data carry-through (31.2); frontend `/spools` route + index page + states (31.3); frontend landing low-stock card (31.4); i18n + ops doc + visual baseline regen (31.5)). All stories `gpt-5.4-mini` Codex routing (no NFR-SECURITY adjacency). Source SCP: sprint-change-proposal-2026-05-29-spoolman.md.'
  - id: 21
    name: 'Admin-Managed Orca Process Profiles + User-Facing Selector Options'
    status: 'planning'
    started: '2026-06-04'
    epics: 'E33 (Admin-Managed Orca Process Profiles, 3 stories 33.1-33.3, read-only first — read-only admin profile inventory over the resolver + compatibility map consumption (33.1, PROFILE-ADMIN-1); validated import/publish write path (in-place vendored-tree write + sidecar manifest + compatibility enforcement) (33.2, PROFILE-ADMIN-2); optional manage/lifecycle — rename label / disable / delete (33.3, PROFILE-ADMIN-3)). offerable = imported ∧ resolvable ∧ compatible. UX-PROFILE-1 (bmad-ux) required before/with FE work. Process/intent profiles only; NOT Spoolman inventory/cost. Source SCP: sprint-change-proposal-2026-06-04-profile-admin.md.'
  - id: 22
    name: 'Admin Operational Observability (Worker/Job Console)'
    status: 'planning'
    started: '2026-06-06'
    epics: 'E34 (Admin Worker/Job Queue Console, 1 read-only MVP story 34.1 ADMIN-JOBS-1 — admin-only read-only console over the 3 live ARQ pools: backend GET /api/admin/queues snapshot (per-pool zcard queued + bounded SCAN in-progress + bounded hard-capped SCAN recent results, never KEYS) + FE /admin/queues admin tab (per-queue cards + running strip + recent ~1h list with retention label, fails-closed). Raw-arq live snapshot + reuse of business-keyed status keys as context; durable ledger DEFERRED (G-LEDGER); coarse health-key liveness accepted for MVP (G-LIVENESS); read-only, NO retry/kill/purge/pause/resume (G-ACTIONS). Decisions AO/AP/AQ. Sequenced BEFORE G-PUBLISH (Init 21 PROFILE-OFFER-1). Implementation BLOCKED until bmad-create-story + dev-go (G-DEVGO). Discovery: spec-admin-jobs-console.md (commit dcb9df8). Source SCP: sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md.'
---

# 3d-portal — Epic Breakdown

This is the living project epics ledger for **3d-portal**. Epics are numbered project-globally (E1, E2, E3, ...) — numbering does **not** restart per initiative. Each initiative groups its own epics under an H2 section below, mirroring the `prd.md` / `architecture.md` initiatives index.

BMAD does not currently ship a dedicated `bmad-edit-epics` skill. New initiatives extend this file via manual append following the existing structure (Initiative wrapper + Requirements Inventory + Epic List + per-Epic detail). Do **not** fork (`epics-v2.md`, `epics-glitchtip.md`).

## Initiatives Index

| # | Name | Status | Shipped | Epics | Stories |
|---|---|---|---|---|---|
| 0 | Product Foundation — Home 3D-Printing Catalog | ✅ shipped (retro) | 2026-04 v1 | E0 | Foundation epics shipped retroactively (catalog / auth / share / admin / sot / runbook / render / infra). Stories not recreated — implementation source of truth is `docs/design/2026-04-29-portal-design.md` + `docs/plans/2026-04-29-portal-v1-implementation.md` + the running code. |
| 1 | Useful GlitchTip Delta | ✅ shipped | 2026-05-10 | E1-E3 | 15 total (E1: 6, E2: 5, E3: 4) |
| 2 | Agent Runbook + Legacy SoT Triage | ✅ shipped | 2026-05-11 | E4 | 6 total — 5 MVP DONE + 4-4-followup DONE + retro DONE; 4.6 Growth explicitly deferred |
| 3 | UI Theme Compliance & Visual Regression Hardening | ✅ shipped | 2026-05-13 | E5 | 17 total — all DONE single-session autonomous + retro DONE |
| 5 | Public Registration & User Account Management | ✅ shipped | 2026-05-20 | E6-E10 | 27 stories shipped. Closing commits 7e5aea0 (cutover) + 2429157 (retro). |
| 6 | Post-Cutover Default-Deny Auth Posture | ✅ shipped | 2026-05-21 | E11 | 7 stories shipped (11.1-11.7). NFR6-SEC-1 HARD GATE PASS. Closing commit 2641b6c. |
| 7 | Account & Admin UX Polish | 🚧 planning | started 2026-05-21 | E12 | 5 stories (12.1-12.5): admin invites unblock, admin users inactive-filter, display name on registration, settings hub + 2FA discoverability, sessions UX. NFR7-UX-1 visual-verification gate on every UI story. |
| 8 | Catalog Mobile & Image Performance | 🚧 planning | started 2026-05-21 | E13 | 2 stories (13.1-13.2): mobile carousel arrows, thumbnail pipeline (Pillow + WebP + backfill). |
| 9 | Test Isolation Cleanup | 🚧 planning | started 2026-05-21 | E14 | 3 stories (14.1-14.3): vitest admin finders, pytest hydrate pollution, visual-regression hook flake. TB-018 promotion via operator scope-pull. Scheduled FIRST in SCP execution chain (unblocks Init 7 + 8 test surfaces). |
| 10 | Operator Polish Batch | 🚧 planning | started 2026-05-22 | E15-E17 | ~13 stories (E15 = 3, E16 = 6, E17 = 4). E15 Test Health (pytest deadlock + visual baselines + fixture refactor) → E16 + E17 parallel after E15. NFR10-DETERMINISM-1 + NFR10-VISUAL-VERIFICATION-1 gates. |
| 11 | Triage Quick Wins Bundle | ✅ shipped | 2026-05-23 | E18 | 5 stories (18.1-18.5) + 3 fix-ups; all Codex CLEAN; 846/846 pytest deterministic. |
| 12 | Anonymous Share View Enrichment + DDoS Hardening | 🚧 planning | started 2026-05-23 | E19 | 7 stories (19.1-19.7); security-first sequencing (rate-limit + throughput BEFORE UX uplift); operator-calibrated thresholds (60 req/min per token+IP; 2 MB/s + 5 concurrent per IP); carousel = member-view-scoped-to-shared-item. Story 19.7 (3D viewer) depends on Init 13 TB-022. |
| 19 | Spoolman Read-Only Inventory (MVP-A) | 🚧 planning | started 2026-05-29 | E31 | 5 stories (31.1-31.5): 31.1 backend httpx client + Redis 30s TTL + arq 60s poll + SETNX leader-election + env config; 31.2 backend `/api/spools/*` routes + DTOs with cost-data carry-through; 31.3 frontend `/spools` index page + states; 31.4 frontend landing low-stock card; 31.5 i18n + ops doc + visual baseline regen. All stories `gpt-5.4-mini` Codex routing (no NFR-SECURITY adjacency — read-only outbound HTTP to LAN-only Spoolman). Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md`. |
| 20 | STL Slicer Estimates (Per-Part MVP) | 🚧 planning | started 2026-05-31 | E32 | 6 stories (32.1-32.6): 32.1 profile resolver (Orca system+user inheritance merge + normalize + validate + hash + provenance snapshot); 32.2 containerized headless OrcaSlicer slicer-worker (AppImage + job shape + CLI invoke); 32.3 g-code metadata parse + `(stl_hash, bundle_hash)` cache schema + cost-carry fields; 32.4 invalidation rules + recompute queue + cost-only arithmetic recompute; 32.5 Spoolman-mapped custom filament overrides (volumetric speed / temps / density); 32.6 frontend `PrintIntentPreset` selector + estimate display + soft-fail/warning/failure states. Per-STL only; request totals are linear sums (no whole-plate slicing); not e-commerce; Spoolman = inventory SoT; Fenrir = research/export bench only. Three architecture Decisions (AH resolver, AI slicer-worker container, AJ cache/invalidation). Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md`. |
| 21 | Admin-Managed Orca Process Profiles + User-Facing Selector Options | 🚧 planning | started 2026-06-04 | E33 | 3 stories (33.1-33.3, read-only first): 33.1 read-only admin profile inventory over the resolver — per `(printer_ref, material_class, quality_tier)` slot `{imported, resolvable, compatible, reason, portal_label, provenance}`, `/api/admin/profiles` admin-gated, + `"profiles"` admin tab grid (PROFILE-ADMIN-1); 33.2 validated import/publish write path — structural `resolve()` ∧ compatibility gates → in-place vendored-tree write + on-disk sidecar manifest + audit, reject incompatible-slot imports (PROFILE-ADMIN-2); 33.3 optional manage/lifecycle — rename label / disable / delete (PROFILE-ADMIN-3). offerable = imported ∧ resolvable ∧ compatible (TPU only offers TPU-compatible process profiles). Two architecture Decisions (AK inventory read + compatibility-map representation/enforcement, AL import write posture + sidecar metadata, no DB). UX-PROFILE-1 (`bmad-ux`) required before/with FE work. Process/intent profiles only; NOT Spoolman inventory/cost; preserves Init 20 `bundle_hash`/provenance invariants. Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md`. Kanban `t_ce1927cf`. |
| 22 | Admin Operational Observability (Worker/Job Console) | 🚧 planning | started 2026-06-06 | E34 | 1 read-only MVP story (34.1 ADMIN-JOBS-1): admin-only worker/job **console** over the 3 live ARQ pools (API `arq:api`, Render `arq:queue`, Slicer `arq:slicer`) — backend `GET /api/admin/queues` snapshot (per-pool `zcard` queued exact + bounded `SCAN arq:in-progress:*` + bounded hard-capped `SCAN arq:result:*`, **never** unbounded `KEYS`; all via the lifespan-owned `app.state` arq/Redis) + FE `/admin/queues` admin tab (per-queue cards with queued/running headline + tri-state liveness chip + raw counters; "running now" strip; "recent ~1h" list **labelled Redis-resident**; loading/empty/error **fails-closed**; focus-gated polling, no WebSocket/SSE). Answers UC1 "did my change wake the backend?" / UC2 "is something running ahead?" / UC3 "what are these red jobs?". **Read-only, admin-only — NO retry/kill/purge/pause/resume.** MVP = raw-arq live snapshot + reuse of existing business-keyed status keys (`render:status:{model_id}`, slicer `EstimateStatus`) as context. **Durable job-activity ledger DEFERRED** (G-LEDGER); coarse ~1h health-key liveness accepted for MVP, interval-lowering deferred (G-LIVENESS); operator-action controls deferred (G-ACTIONS). Load-bearing **leak fence** (field-allowlist DTO, never raw pickled `args`/`kwargs`/`result`). Three architecture Decisions (AO read-model+location+ledger-deferred, AP coarse-health-key liveness, AQ leak fence/read-only privacy). API-read-only + FE → SW-DEPLOY-1 NOT triggered. **Sequenced BEFORE G-PUBLISH** (Init 21 PROFILE-OFFER-1). Implementation BLOCKED until bmad-create-story + dev-go. Discovery: `spec-admin-jobs-console.md` (commit dcb9df8). Source SCP: `sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md`. |

## Initiative 0 — Product Foundation: Home 3D-Printing Catalog

**Status:** shipped retrospective (v1 cutover 2026-04; documented 2026-05-15). **Framing:** the foundation's epics shipped before BMAD adoption — they are listed here as a retroactive ledger so the project-global epic numbering is sound (E0 → E1 → E2 → … rather than starting at E1). **No stories** are recreated; the implementation source of truth is `docs/design/2026-04-29-portal-design.md` + `docs/plans/2026-04-29-portal-v1-implementation.md` + the running code under `apps/` + `workers/` + `infra/`.

### Overview

The retrospective foundation decomposes into nine logical epics (E0.1–E0.9), mirroring the v1 implementation plan's 12 phases. Phases are collapsed where the architectural boundary is the same. **All nine ship in this single retroactive entry; none correspond to new work.**

**⚠️ Important — Initiative 0 intentionally relaxes normal epic-quality standards.** Several E0 epics (E0.1 Repo + Monorepo Bootstrap, E0.2 Data Plane + Migrations, E0.9 Infra + Deploy + Observability Baseline) are technical-by-nature and do NOT deliver direct user value in the way a forward-looking epic should. **This is acceptable here because E0 is a retroactive ledger of pre-BMAD work, not a work queue.** Do NOT pattern-copy E0's epic structure for future initiatives — Initiatives 1+ must follow normal "epics deliver user value" standards (see Codex implementation-readiness review 2026-05-15 § Major 4 + Forward-Applicable Principles § 6 at end of this document).

### Epic List (retroactive)

| Epic | Name | Status | Scope |
|---|---|---|---|
| E0.1 | Repo + Monorepo Bootstrap | ✅ shipped | Project structure: `apps/web`, `apps/api`, `workers/render`, `infra`. Tooling: pnpm/npm, uv, ruff, vitest, playwright. CLAUDE.md / AGENTS.md baseline. |
| E0.2 | Data Plane + Migrations | ✅ shipped | SQLite at `/data/state/portal.db`, SQLModel entities (`User`, `Model`, `ModelFile`, `Tag`, `Category`, `Print`, `ExternalLink`, `AuditLog`, `RefreshToken`), 11 Alembic migrations through `0011_index_ext_link_url`. Postgres-ready via `DATABASE_URL` flip. |
| E0.3 | Auth + CSRF | ✅ shipped | JWT login via `/api/auth/login` (bcrypt), refresh-token rotation (`0009_refresh_tokens`), CSRF middleware requiring `X-Portal-Client: web`, `current_user` / `current_admin` dependencies. Cookie + password agent flow per `bootstrap_agent.py` (2026-05-10 correction authoritative). |
| E0.4 | Catalog Read Surface | ✅ shipped | `apps/api/app/modules/sot/router.py` public reads, `apps/web/src/modules/catalog/` list + grid + search + filter + detail page + 3D STL viewer (three.js + react-three-fiber + drei, theme-token materials). Mobile + dark theme verified. |
| E0.5 | Admin + Audit Log | ✅ shipped | `apps/api/app/modules/admin/router.py` CRUD over all catalog entities, audit log row per write (migration `0005`). Frontend admin UI behind `<AuthGate>`. |
| E0.6 | Share Link Lifecycle | ✅ shipped | `apps/api/app/modules/share/{router,admin_router}.py`, Redis-backed token TTL, nginx-180 location-rule bypass for `/share/*` + `/api/share/*`. Admin list + revoke. |
| E0.7 | Render Pipeline | ✅ shipped | `workers/render/` arq worker, `trimesh` + `matplotlib` 4-view STL renderer, output as `ModelFile` rows. Trigger via admin API; bulk via `infra/scripts/render-all.sh`. Job status TTL 1h. |
| E0.8 | Agent Surface (foundation) | ✅ shipped | `/agent-runbook` Markdown endpoint (`apps/api/app/modules/runbook/router.py`). OpenAPI exposed at `/openapi.json` (Initiative 2 adds enrichment with operation IDs). Sot ingestion via cookie + password agent flow. |
| E0.9 | Infra + Deploy + Observability Baseline | ✅ shipped | Docker Compose on `.190`, nginx edge on `.180`, BuildKit-secret-mounted production secrets, `bash infra/scripts/deploy.sh` one-command deploy with Alembic migration. GlitchTip + OTel distro 0.50b0 + structured JSON logs (Initiative 1 layers debug-ID symbolication on top). SQLite nightly backup with 30-day retention. |

### Requirements Inventory

The functional requirements live in `prd.md` § Initiative 0 (FR0-CAT-*, FR0-ADM-*, FR0-SHARE-*, FR0-AUTH-*, FR0-SOT-*, FR0-RUN-*, FR0-RND-*). The non-functional bounds live in the same section (NFR0-PERF-*, NFR0-SEC-*, NFR0-REL-*, NFR0-INT-*, NFR0-OBS-*, NFR0-MAINT-*).

These FRs/NFRs are not gated by acceptance-criteria tables here because their acceptance was the v1 cutover itself. The running code at `https://3d.ezop.ddns.net` is the source of truth.

### Cross-references

- **PRD section:** `prd.md` § Initiative 0 — Product Foundation: Home 3D-Printing Catalog.
- **Architecture section:** `architecture.md` § Initiative 0 (pointer-only — v1 architectural baseline lives in `docs/architecture.md` + `docs/design/2026-04-29-portal-design.md`; Initiative 1+ in `architecture.md` are deltas layered on top).
- **Brief:** `_bmad-output/planning-artifacts/product-brief-3d-portal.md` + `product-brief-3d-portal-distillate.md` (created 2026-05-15).
- **v1 design spec:** `docs/design/2026-04-29-portal-design.md`.
- **v1 implementation plan:** `docs/plans/2026-04-29-portal-v1-implementation.md`.
- **Project overview (generated 2026-05-15):** `docs/project-overview.md`, `docs/source-tree-analysis.md`, `docs/index.md`.

### Out of scope for E0 (deferred to future initiatives)

- Print queue backend (`apps/api/app/modules/queue/` slot — web placeholder live, backend pending).
- Moonraker integration (`apps/web/src/modules/printer/` slot).
- Spoolman integration (`apps/web/src/modules/spools/` slot).
- Member-print-requests + per-user auth model (OIDC vs. native — `apps/web/src/modules/requests/` slot).
- Mobile photo upload (admin endpoint exists; volume + reverse-rsync flow pending).
- OpenSearch full-text backend (cluster available at homelab `https://192.168.2.190:9200`).
- Postgres migration (`DATABASE_URL` flip when SQLite hits a ceiling).
- HA / multi-host deployment.
- CI runner for this repo (currently no CI; manual pre-deploy checks).

Each of these becomes its own initiative when work starts. The corresponding code slots are already scaffolded so no big-bang restructure is required.

---

## Initiative 1 — Useful GlitchTip Delta

**Status:** shipped 2026-05-10. Brownfield delta layered on the 2026-04-30 Sentry/glitchtip-cli baseline. Scope: ~5–7 files in `apps/web/`, 2 new bash scripts in `infra/scripts/`, 1 deploy.sh integration, 1 runbook section rewrite, 3 project-context.md execution-discipline rules. Budget: 2–3 person-days.

### Overview

This initiative decomposes the requirements from `prd.md` § Initiative 1 (30 FRs + 17 NFRs) and `architecture.md` § Initiative 1 (12 decisions A–L) into implementable stories E1.1–E3.4.

**No UX document** — this delta did not touch UI; visual-regression matrix preserved no-regression invariant.

### Requirements Inventory

#### Functional Requirements

##### A. Production Frontend Symbolication

- **FR1:** Production `vite build` emits unique debug IDs into the served JavaScript bundle and emits matching source maps to a non-public artifact location (not the deployed bundle).
- **FR2:** The build uploads source maps + debug IDs to the homelab GlitchTip instance such that GlitchTip can resolve a runtime stack frame to its original `.tsx:line` source location.
- **FR3:** The runtime SDK reports a `release` value identical to the `release` used at upload time, derived from a single shared expression in the codebase (drift-impossible by construction).
- **FR4:** When the upload step fails for any reason (auth, network, GlitchTip-side bug), the production build fails hard with a non-zero exit and the deploy aborts before any image is shipped. There is no warn-and-continue path.

##### B. Event Noise Filtering & Tagging

- **FR5:** The runtime SDK drops events originating from browser-extension URLs (`chrome-extension://`, `moz-extension://`, `safari-web-extension://`).
- **FR6:** The runtime SDK drops events matching well-known noise titles (e.g., `ResizeObserver loop limit exceeded`, `Non-Error promise rejection captured`) plus an empirically-derived deny-list determined from a 30-day sample of real events on the homelab GlitchTip instance.
- **FR7:** The runtime SDK drops events when the user is offline (`!navigator.onLine`) or when an `ApiError` represents a normal `access_expired` refresh-flow round-trip.
- **FR8:** Every emitted event carries static identity tags: `service.version`, `host.name` (build host), `deployment.environment`, `git.commit`, `build.time`. These attach once at SDK init.
- **FR9:** Every emitted event carries dynamic context tags: `route.pathname`, `model.id` (when present in the current route), `auth.is_authenticated`. These re-attach on each TanStack Router navigation event.

##### C. Post-Deploy Verification

- **FR10:** Operators (human or automated) can run a single command that triggers a deterministic frontend smoke event in production, polls GlitchTip for that event, and asserts the top stack frame resolves to a real source file path.
- **FR11:** The verification process uses a unique per-run fingerprint (`smoke.run_id=<uuid>`) so concurrent or accidental matching events cannot produce false positives.
- **FR12:** The verification process has a bounded time budget (≤30 seconds total wall-clock) and exits non-zero if it cannot match a successfully-symbolicated event within that window. **Exit code contract:** `0` = success; `1` = symbolication broken (top-frame regex mismatch); `2` = GlitchTip unreachable (REST 5xx / network error); `3` = auth/scope failure (401/403); `4` = timeout (no matching event within 30 s budget). Stable contract — `deploy.sh` and downstream automation depend on these specific codes.
- **FR13:** A successful verification persists a timestamp + status marker that subsequent `deploy.sh` invocations can read.
- **FR14:** A failed verification persists a `FAILED` marker and emits a synthetic GlitchTip event tagged `deploy.verification=failed`, providing an in-band alarm channel without external infrastructure.
- **FR15:** `deploy.sh` invokes the verification step at the end of every deploy as a non-fatal warning (deploy success is decoupled from verification result, but operator output makes the result loud).
- **FR16:** `deploy.sh` warns on its NEXT invocation if the previous deploy did not record a successful verification (instrumented decay protection).

##### D. GlitchTip-to-BMAD Triage Bridge

- **FR17:** Operators can run a single command (`<script> <issue_id>`) to convert a GlitchTip issue into a structured markdown story stub.
- **FR18:** The story stub contains a stable, documented set of fields: top stack frame `(filename:line)`, fingerprint, route context, `model.id` when present, release SHA, last 5 events with timestamps, and at least one suggested file to edit.
- **FR19:** The story stub conforms to a documented schema with fields in fixed order (per FR18) and is parsed unmodified by `bmad-quick-dev` or `bmad-create-story` invocations — no manual reformatting, no preprocessing, no field reshuffling required.
- **FR20:** The triage command is read-only against GlitchTip — running it does not modify any issue state.

##### E. Build-Time Security & Determinism

- **FR21:** The GlitchTip authentication token used for source-map upload never appears in the final docker image's layer history (verifiable via `docker history`).
- **FR22:** The deployed bundle does not expose source map files publicly (`*.js.map` URLs return 404 from production).
- **FR23:** The build executes inside the same docker image stage that produces the deployed `dist/` artifacts — bundle hashes derive from the in-image build only, regardless of which dev box invoked the deploy.
- **FR24:** Production `build.sourcemap` setting remains `'hidden'` so the deployed bundle has no `sourceMappingURL` directive — browsers do not fetch maps in any context.

##### F. Operational Continuity & Recovery

- **FR25:** A documented one-command CLI fallback path exists for source-map upload that does not depend on the in-build plugin succeeding.
- **FR26:** The fallback path uses the same release identity as the primary plugin path so symbolication on the homelab GlitchTip is consistent regardless of which path delivered the maps.
- **FR27:** Operators can rotate `GLITCHTIP_AUTH_TOKEN` in a single same-day operation: re-mint via UI, update `infra/.env`, run a normal deploy. The procedure is documented in the operations runbook.
- **FR28:** Required token scopes (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`) are explicitly listed in the runbook so an operator can replicate without trial and error.

##### G. Documentation & Execution Discipline

- **FR29:** The operations runbook (`docs/operations.md`) replaces its current "Sentry vite-plugin out-of-scope follow-up" note with the new ritual: deploy + verify; manual recovery procedure; token rotation procedure; triage script usage.
- **FR30:** The project context file (`_bmad-output/project-context.md`) carries three new execution-discipline rules: run verify-symbolication after every deploy until CI lands; use the triage script before manual triage of a GlitchTip-reported bug; "every replacement keeps its predecessor as documented manual recovery for one release cycle".

#### NonFunctional Requirements

##### Performance

- **NFR-P1:** SDK runtime overhead is bounded — ≤2 KB additional payload per emitted event; SDK init is non-blocking via deferred module bundle (zero user-perceived page-load impact).
- **NFR-P2:** Build-time plugin upload latency ≤10 seconds added to docker build wall-clock for current bundle size (~2 MB minified, ~6 MB maps). Hard timeout at 60 s with clear error.
- **NFR-P3:** `verify-symbolication.sh` total budget ≤30 seconds (codifies FR12 as an SLO).
- **NFR-P4:** `glitchtip-triage.sh` returns within 5 seconds for typical issue lookup (10 s ceiling for large events). No retry loop on transient 5xx — fail clean.

##### Security

- **NFR-S1:** `GLITCHTIP_AUTH_TOKEN` exists ONLY in `infra/.env` on dev box (mode 600). Never on `.190`. Never in image layers. Never in commit history. Never in BMAD planning artifacts.
- **NFR-S2:** Quarterly rotation cadence baseline; ad-hoc rotation triggered by perceived risk events. Same-day operation per FR27.
- **NFR-S3:** Token scope minimization — exactly `org:read`, `project:read`, `project:write`, `project:releases`, `event:write`. NOT `org:write`/`org:admin`.
- **NFR-S4:** Build-time network exposure minimized — exactly two hosts: `192.168.2.190:8800` (chunk upload) + npm registry mirrors. `telemetry: false` for self-hosted plugin target.
- **NFR-S5:** No source-code leakage post-deploy — verified at every deploy via `verify-symbolication.sh` extension or documented manual `curl` returning 404 for `*.js.map`.

##### Reliability

- **NFR-R1:** `verify-symbolication.sh` false-positive rate ≤1 per 100 deploys. Top-frame regex MUST match `^apps/web/src/.+\.tsx?$` — permissive globs forbidden.
- **NFR-R2:** CLI fallback path verified at least once per release cycle. Codified as a project-context.md execution-discipline rule.
- **NFR-R3:** Deploy never ships in observability-broken state without operator-visible signal. Three-signal failure model: stdout warning + `infra/.last-verify` FAILED marker + synthetic GlitchTip event tagged `deploy.verification=failed`.
- **NFR-R4:** Manual ritual decay detection window ≤1 deploy cycle (codifies FR16 as SLO).

##### Integration

- **NFR-I1:** GlitchTip REST API dependency versioned at 6.1.x (`/api/0/projects/...`, `/api/0/issues/...`, chunk-upload protocol). Upgrade requires re-validation per `operations.md` upgrade checklist.
- **NFR-I2:** Tag taxonomy alignment with `~/repos/configs/docs/observability-logging-contract.md` — ECS-style dotted naming for static identity tags + 3d-portal-specific extensions preserve dotted convention.
- **NFR-I3:** BMAD pipeline contract for `glitchtip-triage.sh` output — fixed field order: top frame `(filename:line)`, fingerprint, route context, `model.id` (when present), release SHA, last 5 events, suggested file. **Verifiable:** `./infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returns zero changes.
- **NFR-I4:** configs repo cross-reference integrity — revisions to `glitchtip-agent-guide.md` / `observability-logging-contract.md` affecting this PRD's scope require reconciliation, not silent absorption.

#### Additional Requirements

These are architectural requirements pinned by the Architecture document (Decisions A–L) that are load-bearing for story decomposition but not stated explicitly as PRD FRs.

- **AR1 (Decision G — single-source RELEASE):** `apps/web/src/release.ts` exports `RELEASE: string`. Imported by both `vite.config.ts` (build-time plugin) and `instrument.ts` (runtime SDK). **Pinned expression:** `${package.version}+${git_short_sha}`, where `package.version` is read from `apps/web/package.json` at build time and `git_short_sha` = `git rev-parse --short HEAD`. Drift = TypeScript compile error.
- **AR2 (Decision A — BuildKit secret transport):** `SENTRY_AUTH_TOKEN` flows via `--mount=type=secret,id=sentry_token` in `apps/web/Dockerfile` build stage. `deploy.sh` exports `DOCKER_BUILDKIT=1`. Token source remains `infra/.env` on dev box (mode 600).
- **AR3 (Decision E + J — plugin placement & in-build execution):** `@sentry/vite-plugin` 5.2.x configured with `url: process.env.SENTRY_URL`, `org: 'homelab'`, `project: '3d-portal'`, `release.name: RELEASE`, `sourcemaps.filesToDeleteAfterUpload: ['./dist/**/*.map']`, `telemetry: false`. **Plugin placement: LAST in `vite.config.ts` `plugins[]`.** Executes during `vite build` ONLY, INSIDE docker image build context.
- **AR4 (Decision G — build-time constant injection):** Vite `define` injects `__GIT_COMMIT__` (= `git rev-parse --short HEAD`) and `__BUILD_TIME__` (= `new Date().toISOString()`). Type declarations in `apps/web/src/vite-env.d.ts` (`declare const __GIT_COMMIT__: string;` etc.).
- **AR5 (Decision G — dynamic tag attachment):** TanStack Router `router.subscribe('onLoad', ({ matches }) => ...)` re-attaches dynamic tags on each navigation: `route.pathname`, `model.id` (extracted from `useParams` when route matches `/catalog/$id`), `auth.is_authenticated` (from `AuthContext`).
- **AR6 (Decision H — beforeSend filter ordering):** Filter executes in fixed order with separate `if` branches and early `return null`: (1) `denyUrls` regex match against `event.request?.url`; (2) `ignoreErrors` title match against `event.exception?.values?.[0]?.value`; (3) `!navigator.onLine` → drop; (4) `hint.originalException instanceof ApiError && hint.originalException.body?.detail === "access_expired"` → drop; (5) return event unchanged.
- **AR7 (Decision F — schema-flag + golden-file diff):** `glitchtip-triage.sh --schema` prints the bare template (no values). Golden file `tests/golden/triage-schema.txt` is exactly that template; `diff -u` against it returns zero on stable contract.
- **AR8 (Decision K — `infra/.last-verify` format):** Single line, tab-separated, plain ASCII: `<ISO-8601 timestamp>\t<STATUS>\t<deploy_version>` where `STATUS ∈ {OK, FAILED}` and `deploy_version` matches `RELEASE`. Example: `2026-05-09T14:22:15Z\tOK\t0.1.0+ab12cd3`. `deploy.sh` reads via `cut -f1` for timestamp comparison; full line for warning text.
- **AR9 (Decision K — synthetic alarm event structure):** Failed verify POSTs envelope event to GlitchTip with `tags: { deploy.verification: failed, smoke.run_id: <uuid>, service.version: <RELEASE>, deployment.environment: production }`, `level: warning` (NOT `error` — meta-failure, not app exception), `message: "deploy verification failed: <exit_code_meaning>"`, `extra: { exit_code, expected_top_frame_regex, actual_top_frame }`.
- **AR10 (Phase 0 dry-run gate — FIRST story, branches epic set):** One-shot `vite build` against homelab GlitchTip (`http://192.168.2.190:8800`) with `@sentry/vite-plugin` 5.2.x BEFORE plugin migration commits. **Outcome branches the epic set:**
  - **Happy-path:** Decisions E + J active → full MVP scope per Implementation Sequence (Phase 0 → Discovery → release.ts → vite.config plugin → Dockerfile BuildKit → instrument.ts polish → ops scripts → deploy.sh → upload-sourcemaps.sh decoupling → docs).
  - **Fallback-path:** Issue #299 fires → abort Decisions E and J. Retain Decisions G (release.ts still useful for CLI flow), F (triage), A and B (token scoping for any GlitchTip API call), K (verify integration). Ship SDK polish + ops scripts only; CLI flow stays as active path.
- **AR11 (Discovery story — empirical filter ruleset):** Sample 30-day GlitchTip issues from homelab instance → derive empirical `denyUrls` / `ignoreErrors` patterns. Anticipated minimums (browser-extension URLs, `ResizeObserver loop`) are a floor, not a ceiling. Output gates AR6 / FR6 implementation.
- **AR12 (Bash script conventions — uniform across 4 scripts):** Every script (`verify-symbolication.sh`, `glitchtip-triage.sh`, modified `deploy.sh`, kept `upload-sourcemaps.sh`):
  - Strict mode: `set -euo pipefail`. No `|| true` on critical operations.
  - Dependency check: `command -v jq curl >/dev/null || { echo "missing: <tool>" >&2; exit 1; }`.
  - Env loading: `set -a; source infra/.env; set +a` exactly once at start.
  - Required env validation: `: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"`. No silent defaults.
  - Stdout vs stderr split: narrative on stdout, errors/warnings on stderr.
  - Exit-code map documented in 10–20 line header comment block.
- **AR13 (Curl + jq idiom — uniform across all GlitchTip REST calls):** `http_code=$(curl -sS -o /tmp/gt-response.json -w '%{http_code}' -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "$GLITCHTIP_URL/api/0/...")` then `case "$http_code" in 20*) ;; 401|403) exit 3 ;; 5*) exit 2 ;; *) exit 1 ;; esac`. Field extraction via `jq -r`.

#### UX Design Requirements

**N/A.** This delta does not include a UX Design document. The brief explicitly freezes UI baseline:

- No UI changes in any story. `npm run test:visual` produces zero diffs across all 4 projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`). Any diff = unintended regression = stop signal.
- Routing / SPA chrome / browser support / SEO / real-time / accessibility all frozen at baseline (PRD "Frozen Baseline" table).

#### FR Coverage Map

Each requirement maps to exactly one epic. AR10 (Phase 0) lives entirely inside Epic 1 as Story 1.1, branching subsequent E1 stories — it does not produce a separate epic set; instead, conditional stories within E1 carry explicit happy-path / fallback-path scope notes.

| Requirement | Epic | Brief description |
|---|---|---|
| FR1 | Epic 1 | Vite build emits unique debug IDs into bundle + matching maps to non-public location |
| FR2 | Epic 1 | Build uploads maps + debug IDs to homelab GlitchTip for `.tsx:line` resolution |
| FR3 | Epic 1 | Runtime + upload-time `release` derive from single shared expression (drift-impossible) |
| FR4 | Epic 1 | Upload failure = hard build fail = deploy aborts before image ship (no warn-and-continue) |
| FR5 | Epic 2 | Drop browser-extension URLs (`chrome-extension://`, `moz-extension://`, `safari-web-extension://`) |
| FR6 | Epic 2 | Drop well-known noise titles + empirical 30-day-derived deny-list |
| FR7 | Epic 2 | Drop offline events + `ApiError.access_expired` refresh-flow noise |
| FR8 | Epic 2 | Static identity tags attach once at SDK init |
| FR9 | Epic 2 | Dynamic context tags re-attach on TanStack Router `onLoad` navigation |
| FR10 | Epic 3 | Single-command verify triggers smoke event + polls + asserts top-frame source resolution |
| FR11 | Epic 3 | Per-run `smoke.run_id=<uuid>` fingerprint prevents false matches |
| FR12 | Epic 3 | Verify ≤30 s budget + stable exit-code contract (0/1/2/3/4) |
| FR13 | Epic 3 | Successful verify persists timestamp + status marker |
| FR14 | Epic 3 | Failed verify persists FAILED marker + emits synthetic `deploy.verification=failed` event |
| FR15 | Epic 3 | `deploy.sh` invokes verify post-deploy as non-fatal warning (loud output) |
| FR16 | Epic 3 | `deploy.sh` warns next invocation if previous deploy lacks successful verify (decay protection) |
| FR17 | Epic 2 | Single-command `<script> <issue_id>` produces structured markdown story stub |
| FR18 | Epic 2 | Stub fields fixed: top frame, fingerprint, route, model.id, release SHA, last 5 events, suggested file |
| FR19 | Epic 2 | Stub schema fixed-order, parsed unmodified by `bmad-quick-dev` / `bmad-create-story` |
| FR20 | Epic 2 | Triage command read-only against GlitchTip (no state mutation) |
| FR21 | Epic 1 | Token never appears in `docker history` (BuildKit secret mount) |
| FR22 | Epic 1 | Production `*.js.map` URLs return 404 (no source-map exposure) |
| FR23 | Epic 1 | Build runs INSIDE docker image stage producing `dist/` (bundle-hash determinism) |
| FR24 | Epic 1 | `build.sourcemap: 'hidden'` invariant preserved (no `sourceMappingURL` in deployed bundle) |
| FR25 | Epic 1 | One-command CLI fallback path exists and runs without plugin (`upload-sourcemaps.sh`) |
| FR26 | Epic 1 | Fallback path uses same `RELEASE` identity as primary path (consistent symbolication) |
| FR27 | Epic 3 | Token rotation = same-day operation: re-mint UI → update `infra/.env` → run deploy |
| FR28 | Epic 3 | Required scopes (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`) listed in runbook |
| FR29 | Epic 3 | `docs/operations.md` rewrites symbolication section (ritual + recovery + rotation + triage) |
| FR30 | Epic 3 | `_bmad-output/project-context.md` carries 3 new execution-discipline rules |
| NFR-P1 | Epic 2 | SDK runtime overhead ≤2 KB/event, init non-blocking |
| NFR-P2 | Epic 1 | Build-time plugin upload ≤10 s typical, hard fail at 60 s |
| NFR-P3 | Epic 3 | Verify total budget ≤30 s |
| NFR-P4 | Epic 2 | Triage script ≤5 s typical, ≤10 s ceiling |
| NFR-S1 | Epic 1 | Token at-rest scope = `infra/.env` only (mode 600, dev box, gitignored) |
| NFR-S2 | Epic 3 | Quarterly rotation cadence baseline + ad-hoc on risk events |
| NFR-S3 | Epic 1 | Token scope minimization (5 specific scopes, no `org:write`/`org:admin`) |
| NFR-S4 | Epic 1 | Build-time exposure = exactly 2 hosts + `telemetry: false` |
| NFR-S5 | Epic 1 | No source-code leakage post-deploy verified at every deploy |
| NFR-R1 | Epic 3 | Verify false-positive rate ≤1/100 (regex `^apps/web/src/.+\.tsx?$`) |
| NFR-R2 | Epic 1 | CLI fallback verified at least once per release cycle |
| NFR-R3 | Epic 3 | Three-signal failure model (stdout warn + FAILED marker + synthetic event) |
| NFR-R4 | Epic 3 | Decay window ≤1 deploy cycle |
| NFR-I1 | Epic 1 | GlitchTip 6.1.x API surface versioned dependency |
| NFR-I2 | Epic 2 | Tag taxonomy ECS-style alignment with `observability-logging-contract.md` |
| NFR-I3 | Epic 2 | Triage schema golden-file diff verifiable |
| NFR-I4 | Epic 3 | configs-repo cross-reference integrity |
| AR1 | Epic 1 | `release.ts` exports `RELEASE = ${package.version}+${git_short_sha}` |
| AR2 | Epic 1 | BuildKit secret mount transport for `SENTRY_AUTH_TOKEN` |
| AR3 | Epic 1 | `@sentry/vite-plugin` 5.2.x LAST in `plugins[]`, in-build only |
| AR4 | Epic 1 | Vite `define` injects `__GIT_COMMIT__` + `__BUILD_TIME__` + ambient declarations |
| AR5 | Epic 2 | TanStack Router `subscribe('onLoad', ...)` attaches dynamic tags |
| AR6 | Epic 2 | `beforeSend` filter ordering fixed (denyUrls → ignoreErrors → offline → ApiError → return) |
| AR7 | Epic 2 | `--schema` flag + `tests/golden/triage-schema.txt` golden file |
| AR8 | Epic 3 | `infra/.last-verify` format = ISO8601\\tSTATUS\\tRELEASE single-line tab-separated |
| AR9 | Epic 3 | Synthetic alarm event structure (tags + `level: warning` + extra) |
| AR10 | Epic 1 | Phase 0 dry-run gate as Story 1.1; outcome branches E1 stories 1.2–1.7 |
| AR11 | Epic 2 | Discovery story samples 30-day GlitchTip issues → empirical filter ruleset |
| AR12 | Epic 3 | Bash script conventions enforced (`set -euo pipefail`, env loading, exit-code header) |
| AR13 | Epic 2, 3 | curl + jq + http_code + case-statement idiom (E2: triage script; E3: verify script) |

**Coverage:** 30/30 FRs + 17/17 NFRs + 13/13 ARs mapped. AR12 enforced cross-cuttingly in scripts shipped by E2 and E3; AR13 applies wherever GlitchTip REST is hit (E2 triage script + E3 verify script).

### Epic List

The MVP scope ships as 3 epics organized by user value (not technical layers). Each epic stands alone — Epic 2 and Epic 3 build upon Epic 1's symbolication round but each delivers complete functionality for its domain. Phase 0 dry-run gate is Story 1.1 of Epic 1; its outcome branches Stories 1.2–1.7 (happy-path: full plugin migration; fallback-path: skip plugin stories, retain CLI flow as active path with `release.ts` + `upload-sourcemaps.sh` polish).

#### Epic 1: Production-Readable Stack Traces

**User outcome:** AI agents and Michał looking at any new GlitchTip issue from production see a top stack frame resolved to `apps/web/src/<...>.tsx:<line>` instead of `index-DhGq2.js:13`. Bundle hashes are deterministic (build runs inside the docker image), `SENTRY_AUTH_TOKEN` never appears in image layers, source maps do not leak publicly. The CLI fallback path (`upload-sourcemaps.sh`) is decoupled from `deploy.sh` but remains documented manual recovery.

**FRs covered:** FR1, FR2, FR3, FR4, FR21, FR22, FR23, FR24, FR25, FR26
**NFRs touched:** NFR-P2, NFR-S1, NFR-S3, NFR-S4, NFR-S5, NFR-R2, NFR-I1
**ARs touched:** AR1, AR2, AR3, AR4, AR10
**Phase 0 branching:** Story 1.1 (Phase 0 dry-run gate) outcome decides whether stories 1.4–1.7 ship the plugin migration (happy-path) or skip plugin migration entirely while retaining release.ts + upload-sourcemaps decoupling (fallback-path on issue #299).

#### Epic 2: Triage-Ready Events & BMAD Triage Bridge

**User outcome:** Every event emitted to GlitchTip carries the static identity tags (`service.version`, `host.name`, `deployment.environment`, `git.commit`, `build.time`) and re-attaches dynamic context (`route.pathname`, `model.id`, `auth.is_authenticated`) on each TanStack Router navigation. The runtime SDK drops empirically-derived noise (extensions, ResizeObserver loops, offline, refresh-flow 401). AI agents convert any GlitchTip issue into a paste-ready BMAD story stub with one command (`glitchtip-triage.sh <issue_id>`), schema verifiable via golden-file diff.

**FRs covered:** FR5, FR6, FR7, FR8, FR9, FR17, FR18, FR19, FR20
**NFRs touched:** NFR-P1, NFR-P4, NFR-I2, NFR-I3
**ARs touched:** AR5, AR6, AR7, AR11, AR13

#### Epic 3: Verify Ritual, Decay Protection & Operational Continuity

**User outcome:** Every deploy proves observability is alive: `deploy.sh` invokes `verify-symbolication.sh` post-deploy, happy-path writes timestamped `infra/.last-verify`, failure-path produces three independent signals (loud red stdout warning + FAILED marker + synthetic GlitchTip event tagged `deploy.verification=failed`). The next deploy reads the last-verify state and warns on stale state (decay protection). Operator has documented same-day token rotation procedure, exact required scopes, and three new execution-discipline rules in `_bmad-output/project-context.md`.

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR27, FR28, FR29, FR30
**NFRs touched:** NFR-P3, NFR-S2, NFR-R1, NFR-R3, NFR-R4, NFR-I4
**ARs touched:** AR8, AR9, AR12, AR13

---

### Epic 1: Production-Readable Stack Traces

**Goal:** AI agents and Michał looking at any new GlitchTip issue from production see a top stack frame resolved to `apps/web/src/<...>.tsx:<line>` instead of `index-DhGq2.js:13`. Bundle hashes are deterministic (build runs inside the docker image), `SENTRY_AUTH_TOKEN` never appears in image layers, source maps do not leak publicly. The CLI fallback path remains documented manual recovery with the same `RELEASE` identity.

**Phase 0 branching:** Story 1.1 outcome decides whether stories 1.4–1.5 ship the plugin migration (happy-path) or are closed as `won't ship` (fallback-path on issue #299). Stories 1.2, 1.3, 1.6 are unconditional.

> **Phase 0 outcome (2026-05-09):** Initial dry-run hit a third category — HTTP 413 from public proxy (not issue #299). Operator chose Option B: a 50 MB regex-scoped `client_max_body_size` block was added in `~/repos/configs/nginx/glitchtip.ezop.ddns.net.conf` for `^/api/0/organizations/[^/]+/chunk-upload`. Re-run #2 = **HAPPY-PATH** (`✓ built in 7.24s`, "Successfully uploaded source maps to Sentry"). **Stories 1.4 and 1.5 PROCEED.** Full transcript: `_bmad-output/implementation-artifacts/phase0-result.md`.

#### Story 1.1: Phase 0 Dry-Run Gate

As Michał (or an AI agent acting as Michał),
I want a one-shot local `vite build` against the homelab GlitchTip instance with `@sentry/vite-plugin` 5.2.x enabled,
So that we know empirically whether GlitchTip backend issue #299 fires on this specific instance before committing the plugin migration to the repo.

**Acceptance Criteria:**

**Given** `infra/.env` carries `GLITCHTIP_AUTH_TOKEN` with the required scopes (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`) and the dev box has LAN/VPN reach to `192.168.2.190:8800`,
**When** a temporary git worktree adds `@sentry/vite-plugin@~5.2.0` as devDependency, a stub `apps/web/src/release.ts` exporting `RELEASE = "0.1.0+phase0"`, and a minimal `vite.config.ts` modification appending `sentryVitePlugin({ url: process.env.SENTRY_URL, org: 'homelab', project: '3d-portal', release: { name: RELEASE }, sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] }, telemetry: false })` LAST in `plugins[]`,
**Then** `vite build` runs to completion and the plugin's chunk-upload step returns 200 from `:8800` and the artifact-bundle `assemble` call returns 200 (NOT 404) within 60 s wall-clock.
**And** an immediately-following `curl -fsS -H "Authorization: Bearer $GLITCHTIP_AUTH_TOKEN" "http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/releases/0.1.0+phase0/files/"` returns a non-empty JSON array listing the uploaded files.
**And** the outcome is recorded in `_bmad-output/implementation-artifacts/phase0-result.md` as either `[x] happy-path: assemble 200 — proceed with stories 1.4 + 1.5` OR `[x] fallback-path: assemble returned 404 (#299 fires) — close 1.4 + 1.5 as won't ship, retain CLI flow as active path`. The same checklist line is later mirrored into the Phase 0 PR description when one opens.
**And** the temporary worktree is discarded after recording — no permanent code changes land from Story 1.1; the actual plugin integration ships via Story 1.4 only on happy-path.

#### Story 1.2: `apps/web/src/release.ts` — Single-Source RELEASE Constant

As any code that needs the release tag (`instrument.ts` runtime, `vite.config.ts` plugin in happy-path, `upload-sourcemaps.sh` CLI fallback in either path),
I want one single TypeScript-typed `RELEASE` constant assembled from `package.version` + `git_short_sha`,
So that build-time and runtime release identity cannot drift — drift produces a TypeScript compile error.

**Acceptance Criteria:**

**Given** `apps/web/package.json` carries `"version": "X.Y.Z"`,
**When** the file `apps/web/src/release.ts` is created exporting `RELEASE: string` whose value at build time equals `${package.version}+${git_short_sha}` — implementation: read `package.json` version (via Vite `define` of a build-time constant `__PKG_VERSION__` derived from `JSON.parse(readFileSync('package.json'))`) and the git short SHA (via Vite `define` of `__GIT_COMMIT__` per Story 1.3), then `release.ts` exports a const `RELEASE = \`${__PKG_VERSION__}+${__GIT_COMMIT__}\``,
**Then** `import { RELEASE } from "@/release"` succeeds in any TypeScript file under `apps/web/src/`.
**And** changing `apps/web/package.json` version + rebuilding produces a new `RELEASE` value matching the new version.
**And** rebuilding on a different short-SHA produces a different `RELEASE` value (no caching across commits).
**And** repository-wide `grep -RIn 'VITE_PORTAL_VERSION' apps/web/src/` returns zero matches in TypeScript files (legacy expression replaced).
**And** `npm run lint` (ESLint --max-warnings=0) and `npm run typecheck` (or `tsc --noEmit`) both pass with the new file in place.

#### Story 1.3: Vite `define` for `__GIT_COMMIT__`, `__BUILD_TIME__`, and `__PKG_VERSION__`

As `apps/web/src/release.ts` (Story 1.2 consumer) and `apps/web/src/instrument.ts` (Epic 2 consumer),
I want `__GIT_COMMIT__`, `__BUILD_TIME__`, and `__PKG_VERSION__` injected as ambient string constants via Vite `define`,
So that release identity + static identity tags carry git short SHA, ISO-8601 build timestamp, and package version without runtime probing.

**Acceptance Criteria:**

**Given** `vite.config.ts`,
**When** the config adds (at module top) `import { execSync } from 'node:child_process';` `import { readFileSync } from 'node:fs';` plus computes `const GIT_COMMIT = execSync('git rev-parse --short HEAD').toString().trim();` `const BUILD_TIME = new Date().toISOString();` `const PKG_VERSION = JSON.parse(readFileSync('./package.json', 'utf-8')).version;` and adds `define: { __GIT_COMMIT__: JSON.stringify(GIT_COMMIT), __BUILD_TIME__: JSON.stringify(BUILD_TIME), __PKG_VERSION__: JSON.stringify(PKG_VERSION) }`,
**And** `apps/web/src/vite-env.d.ts` adds `declare const __GIT_COMMIT__: string; declare const __BUILD_TIME__: string; declare const __PKG_VERSION__: string;`,
**Then** any TypeScript file under `apps/web/src/` can reference the three constants as plain identifiers without import.
**And** `npm run build` produces a bundle where the constants are replaced with the actual short SHA, ISO-8601 timestamp, and package version (verifiable via `grep` in `dist/assets/*.js`).
**And** `npm run dev` (vite serve) also resolves these values at server startup; values may be stale-on-watch by Vite design — explicitly acceptable for dev convenience.
**And** `npm run lint` and `npm run typecheck` both pass.
**And** the values do NOT leak into `_bmad-output/` planning artifacts (no echo, no log line).

#### Story 1.4: `vite.config.ts` + `@sentry/vite-plugin` 5.2.x Integration

**Conditional:** ships only if Story 1.1 records happy-path outcome.

As `vite build` running inside the docker image build stage,
I want `@sentry/vite-plugin` 5.2.x added LAST in `plugins[]` with telemetry off, single-source `RELEASE`, and `filesToDeleteAfterUpload`,
So that the build emits a debug-IDed bundle plus uploaded maps and a clean `dist/` ready for image extraction.

**Acceptance Criteria:**

**Given** `apps/web/package.json` adds `@sentry/vite-plugin@~5.2.0` as `devDependencies`,
**When** `vite.config.ts` imports `RELEASE` from `./src/release` and adds `sentryVitePlugin({ url: process.env.SENTRY_URL, org: 'homelab', project: '3d-portal', release: { name: RELEASE }, sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] }, telemetry: false })` as the LAST entry in `plugins[]`,
**Then** `npm run dev` (vite serve) runs unchanged — the plugin executes only in `vite build` per its `apply: 'build'` semantics, dev workflow unaffected.
**And** `npm run build` with `SENTRY_URL=http://192.168.2.190:8800`, `SENTRY_AUTH_TOKEN` exported, and LAN reach to `.190` produces a `dist/` directory containing zero `.map` files (`find dist -name '*.map' | wc -l` returns 0 — deleted by `filesToDeleteAfterUpload`).
**And** the build stdout names the `sentry-cli` upload step and records 200 responses from `:8800` for chunk upload + assemble.
**And** the bundle's emitted `.js` files contain a `//# sentryDebugId=<uuid>` comment per chunk (debug ID injection — verifiable via `grep sentryDebugId dist/assets/*.js`).
**And** absence of `SENTRY_AUTH_TOKEN` env (or 401/403 response from `:8800`) makes `vite build` exit non-zero — covers FR4 hard-fail policy.
**And** `build.sourcemap: 'hidden'` invariant remains in `vite.config.ts` (FR24 baseline preservation).

#### Story 1.5: Dockerfile BuildKit Secret Mount + Compose Build Args

**Conditional:** ships only if Story 1.1 records happy-path outcome.

As the docker image build process,
I want `SENTRY_AUTH_TOKEN` mounted as a BuildKit secret (`--mount=type=secret,id=sentry_token`) and `SENTRY_ORG` / `SENTRY_PROJECT` / `SENTRY_URL` passed as plain build args,
So that the auth token never persists in image layers (verifiable via `docker history`) while the non-secret config is reproducible.

**Acceptance Criteria:**

**Given** `infra/.env` carries `GLITCHTIP_AUTH_TOKEN` (mode 600 on dev box),
**When** `apps/web/Dockerfile`'s build stage RUN line for `npm run build` is rewritten as `RUN --mount=type=secret,id=sentry_token,target=/run/secrets/sentry_token sh -c 'export SENTRY_AUTH_TOKEN=$(cat /run/secrets/sentry_token) && npm run build'`,
**And** `apps/web/Dockerfile` adds `ARG SENTRY_ORG`, `ARG SENTRY_PROJECT`, `ARG SENTRY_URL` and corresponding `ENV` exports in the build stage,
**And** `infra/docker-compose.yml`'s `web` service `build` block declares `args: { SENTRY_ORG: homelab, SENTRY_PROJECT: 3d-portal, SENTRY_URL: http://192.168.2.190:8800 }` and `secrets: [sentry_token]` plus a top-level `secrets: { sentry_token: { environment: GLITCHTIP_AUTH_TOKEN } }`,
**And** `infra/scripts/deploy.sh` exports `DOCKER_BUILDKIT=1` before `docker compose build` (this `DOCKER_BUILDKIT=1` export also satisfies Story 3.2 — single export covers both stories),
**Then** `docker compose build web` succeeds and the resulting image's `docker history apps_web:<tag>` (and `docker history --no-trunc`) shows zero matches for `grep -i sentry_auth_token` and zero matches for the actual token value.
**And** the plugin upload step inside the build stage receives the token via the env var and uploads succeed (chunk upload + assemble both 200).
**And** running `docker compose build web` WITHOUT `DOCKER_BUILDKIT=1` (e.g., dev box where the export is removed) exits non-zero with a clear message — BuildKit secret syntax requires it.
**And** `infra/.env` remains gitignored and never enters the image filesystem (verifiable: `docker run --rm apps_web:<tag> ls /run/secrets/` returns nothing because the mount is build-time only).

#### Story 1.6: `infra/scripts/upload-sourcemaps.sh` — Decoupling, Header Comment, RELEASE Alignment, `--help` Flag

**Conditional:** always (happy-path: documented manual recovery; fallback-path: active path with the new `RELEASE` expression).

As Michał or an AI agent encountering plugin upload failure (or running fallback-path),
I want `infra/scripts/upload-sourcemaps.sh` decoupled from `deploy.sh` (no longer auto-invoked) and clearly documented as manual recovery via a header comment, with the same `RELEASE` identity as the plugin path,
So that the CLI fallback runs on demand with drift-impossible release tagging — and `--help` makes the contract discoverable without reading source.

**Acceptance Criteria:**

**Given** `infra/scripts/upload-sourcemaps.sh` currently exists and is invoked from `deploy.sh`,
**When** the script's first 10–20 lines are replaced with a documented header block stating: purpose ("Manual recovery path for sourcemap upload when in-build plugin is unavailable, off, or failed."), prerequisites (`infra/.env` with `GLITCHTIP_AUTH_TOKEN`, LAN reach to `:8800`, completed `npm run build` with maps present in `apps/web/dist/`), exit codes (0 success / 1 generic / 2 GlitchTip unreachable / 3 auth/scope), example invocation, recovery context (cite FR25 + Decision E rejected-alternative-kept-as-fallback),
**And** `deploy.sh`'s reference to `upload-sourcemaps.sh` in the active deploy chain is removed (the line is deleted, not commented out),
**And** the script computes `RELEASE` by reading `apps/web/package.json` version + running `git rev-parse --short HEAD` and concatenating as `${pkg_version}+${git_short_sha}` — identical expression to `apps/web/src/release.ts` per Story 1.2 — assigning to a `RELEASE` shell variable used in all subsequent `glitchtip-cli` invocations,
**And** the script supports a `--help` flag (and prints help when invoked with no arguments) that outputs the same content as the header comment block,
**Then** `bash infra/scripts/upload-sourcemaps.sh --help` prints purpose, prerequisites, exit codes, and example invocation to stdout and exits 0.
**And** `bash infra/scripts/upload-sourcemaps.sh` standalone (after a fresh `npm run build`) produces a successful chunk upload to `:8800` and the resulting GlitchTip release tag matches what runtime SDK emits when an event fires.
**And** running `bash infra/scripts/deploy.sh` end-to-end no longer invokes `upload-sourcemaps.sh` (verifiable: `bash -x infra/scripts/deploy.sh` trace contains zero matches for `upload-sourcemaps`).
**And** the script follows AR12 bash conventions: `set -euo pipefail`, dependency check for `glitchtip-cli` + `jq`, `set -a; source infra/.env; set +a` once, required env validated via `: "${GLITCHTIP_AUTH_TOKEN:?missing in infra/.env}"`, stdout vs stderr split, exit-code map in header.

---

### Epic 2: Triage-Ready Events & BMAD Triage Bridge

**Goal:** Every event emitted to GlitchTip carries the static identity tags (`service.version`, `host.name`, `deployment.environment`, `git.commit`, `build.time`) and re-attaches dynamic context (`route.pathname`, `model.id`, `auth.is_authenticated`) on each TanStack Router navigation. The runtime SDK drops empirically-derived noise (extensions, ResizeObserver loops, offline events, refresh-flow 401s). AI agents convert any GlitchTip issue into a paste-ready BMAD story stub with one command (`glitchtip-triage.sh <issue_id>`), schema verifiable via golden-file diff.

**Prerequisite:** Epic 1 stories 1.2 + 1.3 (single-source `RELEASE` + Vite `define` constants) must land first — Stories 2.2–2.4 import `RELEASE` and reference `__GIT_COMMIT__` / `__BUILD_TIME__`. Story 2.5 (triage script) is independent and can run in parallel with 2.1–2.4.

#### Story 2.1: 30-Day GlitchTip Issue Discovery + Empirical Filter Ruleset

As the SDK-config author drafting `instrument.ts` filter logic,
I want a documented sample of the last 30 days of GlitchTip issues from the homelab instance (sorted by frequency) and a derived filter ruleset (`denyUrls` regex patterns + `ignoreErrors` title patterns),
So that the in-code filter is empirically grounded — anticipated patterns (extensions, ResizeObserver) are a floor, not a ceiling, per FR6 and architecture Decision H.

**Acceptance Criteria:**

**Given** `infra/.env` carries `GLITCHTIP_AUTH_TOKEN` with `org:read` + `project:read` scopes,
**When** an ad-hoc shell script (or one-off command sequence) queries `GET http://192.168.2.190:8800/api/0/projects/homelab/3d-portal/issues/?statsPeriod=30d&limit=100&sort=lastSeen` and groups events by `title`, `culprit`, and any URL pattern visible in `request.url`,
**Then** the output is saved as `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` (date stamp = day Story 2.1 ships, ISO-8601),
**And** the document contains:
  - Total issue count for the period.
  - A frequency-ranked table of the top 25 issue titles + their `culprit` / `request.url` if present.
  - A derived `denyUrls` array of regex patterns (anticipated minimums: `/^chrome-extension:\/\//`, `/^moz-extension:\/\//`, `/^safari-web-extension:\/\//`; plus any empirically-noisy URL patterns observed).
  - A derived `ignoreErrors` array of title patterns (anticipated minimums: `/ResizeObserver loop/`, `/Non-Error promise rejection captured/`; plus any empirically-noisy title patterns observed).
  - For each empirical addition, a one-line justification with frequency count.
**And** the file is committed only to local `_bmad-output/` (gitignored per memory; never pushed to remote).
**And** Story 2.4 imports the derived ruleset literally — no manual translation, no reshuffling — so 2.4 ACs trace back to 2.1 evidence.

#### Story 2.2: `instrument.ts` — Static Identity Tags + Single-Source RELEASE Import

As any event reaching GlitchTip,
I want `service.version`, `host.name`, `deployment.environment`, `git.commit`, `build.time` attached at SDK init via `Sentry.setTag` calls,
So that triage sees the build identity (release + commit + build timestamp + environment + build host) on every event regardless of when it fires.

**Acceptance Criteria:**

**Given** Stories 1.2 (`release.ts`) and 1.3 (Vite `define`) are complete,
**When** `apps/web/src/instrument.ts` imports `{ RELEASE } from "@/release"` and replaces the existing `release: VITE_PORTAL_VERSION` (or equivalent) in `Sentry.init({...})` with `release: RELEASE`,
**And** after `Sentry.init({...})` the file makes 5 separate `Sentry.setTag(key, value)` calls (NOT `configureScope`):
  - `setTag('service.version', RELEASE)`
  - `setTag('host.name', __BUILD_TIME__.length ? import.meta.env.VITE_BUILD_HOST ?? 'unknown' : 'unknown')` — value sourced from `VITE_BUILD_HOST` env var injected by `vite.config.ts` build args (or `os.hostname()` resolved via Vite `define` if simpler — implementation choice during dev)
  - `setTag('deployment.environment', import.meta.env.VITE_ENVIRONMENT ?? 'production')`
  - `setTag('git.commit', __GIT_COMMIT__)`
  - `setTag('build.time', __BUILD_TIME__)`
**Then** an event emitted in dev (e.g., manually triggered via the existing `/api/admin/sentry-test` flow or a temporary console-throw) lands in GlitchTip with all 5 tags present and values matching the build's actual `RELEASE` / git short SHA / ISO-8601 build timestamp / `dev` (or whatever `VITE_ENVIRONMENT` resolves to in dev).
**And** the existing `Sentry.setTag('service', 'web')` call from baseline either remains (legacy) or is replaced — explicit choice in the PR — but the new dotted-name `service.version` is mandatory and additive.
**And** `npm run lint` and `npm run typecheck` both pass with the new imports.
**And** unit smoke: a colocated `apps/web/src/instrument.test.ts` (or extension to existing test) imports the module and asserts that `Sentry.setTag` mock was called with the 5 expected keys (test runs `init` against a mocked Sentry SDK).

#### Story 2.3: `instrument.ts` — Dynamic Context Tags via TanStack Router `subscribe('onLoad', ...)`

As an event emitted while the user is navigating the catalog,
I want `route.pathname`, `model.id` (when route matches `/catalog/$id`), and `auth.is_authenticated` re-attached on each `router.subscribe('onLoad', ...)` callback,
So that triage sees route-bound context (which page, which model, which auth state) at the moment the event fires.

**Acceptance Criteria:**

**Given** Story 2.2 is complete and `Sentry.init` has run,
**When** `apps/web/src/instrument.ts` (or a small helper module imported into `apps/web/src/main.tsx` after `<RouterProvider>` mount, whichever is cleaner — implementation choice during dev) registers `router.subscribe('onLoad', ({ matches }) => { ... })`,
**And** inside the callback the code:
  - Sets `route.pathname` to the current `router.state.location.pathname` (or the resolved match's `pathname`).
  - Sets `model.id` from `useParams`-equivalent extraction when route matches `/catalog/$id` — uses `matches.find(m => m.routeId === '/catalog/$id')?.params?.id` or equivalent; clears the tag (sets to `undefined` or omits) when no match.
  - Sets `auth.is_authenticated` from `AuthContext` via a context-bypass read pattern — accessing `auth_state` via `globalThis.__authState` (set by `AuthContext`) OR exposing a small `getAuthSnapshot()` helper from `apps/web/src/shell/AuthContext.tsx` that returns `{ isAuthenticated: boolean }` for non-component callers.
**Then** navigating between routes (e.g., `/login` → `/catalog` → `/catalog/m_142` → `/catalog`) and triggering a test event at each step produces GlitchTip events whose `route.pathname` matches the current URL at the moment of emit.
**And** an event triggered on `/catalog/m_142` carries `model.id = "m_142"`; an event on `/catalog` (no id) does not carry a stale `m_142` tag.
**And** an event triggered before login carries `auth.is_authenticated = "false"`; after login carries `auth.is_authenticated = "true"`.
**And** setting the same tag twice with the same value is a no-op (idempotent — no error, no spurious event).
**And** the visual-regression matrix is unaffected (no UI changes; `npm run test:visual` produces zero diffs across all 4 projects).
**And** `npm run lint` and `npm run typecheck` both pass.

#### Story 2.4: `instrument.ts` — `beforeSend` Filter Contract (5-Step Fixed Ordering)

As GlitchTip,
I want only signal events arriving — drop browser-extension URLs (FR5), drop noise titles per the empirical ruleset from Story 2.1 (FR6), drop offline events (FR7), drop `ApiError.access_expired` refresh-flow noise (FR7),
So that the first 25 issues sorted by `lastSeen desc` 7 days post-rollout contain zero deny-list matches (Tech Success #3 in PRD).

**Acceptance Criteria:**

**Given** Story 2.1 has produced `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md` with the derived `denyUrls` and `ignoreErrors` arrays,
**When** `apps/web/src/instrument.ts` adds inside `Sentry.init({...})` a `beforeSend(event, hint)` callback whose body executes 5 sequential `if` branches in fixed order with separate early `return null` per branch:
  1. `denyUrls`: iterate the imported regex array, test each against `event.request?.url ?? ''`, return `null` on any match.
  2. `ignoreErrors`: iterate the imported regex array, test each against `event.exception?.values?.[0]?.value ?? ''`, return `null` on any match.
  3. `!navigator.onLine` → return `null`.
  4. `hint.originalException instanceof ApiError && hint.originalException.body?.detail === 'access_expired'` → return `null`. (`ApiError` is the existing class from `apps/web/src/lib/api.ts`.)
  5. Return `event` unchanged.
**And** the `denyUrls` and `ignoreErrors` arrays are imported from a colocated module (e.g., `apps/web/src/instrument-filters.ts`) so they can be unit-tested independently and traced to Story 2.1,
**Then** colocated vitest unit tests `apps/web/src/instrument.test.ts` (or `instrument-filters.test.ts`) cover each of the 4 drop branches with a passing assertion (mock `event` / `hint`, call `beforeSend` directly, expect `null`) plus one passing assertion for the catch-all return-event path.
**And** in dev: triggering a test event from a known browser-extension URL pattern is dropped (does not appear in GlitchTip); triggering with `navigator.onLine = false` is dropped; triggering an `ApiError` with `body.detail === 'access_expired'` is dropped; triggering a normal `ReferenceError` is sent.
**And** `npm run lint` (`--max-warnings=0`) and `npm run typecheck` both pass.
**And** the filter ordering matches Decision H exactly — branch order codified in the test file's test-name suffixes (`drops_via_denyUrls`, `drops_via_ignoreErrors`, `drops_when_offline`, `drops_access_expired`, `passes_through_default`).

#### Story 2.5: `glitchtip-triage.sh <issue_id>` + Golden-File Schema

As an AI agent triaging a GlitchTip issue (Journey 1 in PRD),
I want one command that returns a markdown stub paste-ready into `bmad-quick-dev` / `bmad-create-story`,
So that I never need to open the GlitchTip UI — the stub is the entire interface, and its schema is verifiable so downstream BMAD parsers cannot break silently.

**Acceptance Criteria:**

**Given** `infra/.env` carries `GLITCHTIP_AUTH_TOKEN` (with `org:read` + `project:read`) and `GLITCHTIP_URL` (resolves to `http://192.168.2.190:8800` on LAN OR `https://glitchtip.ezop.ddns.net` for sub-MB GETs from off-LAN — script picks one source-of-truth env var; document the choice in the header),
**When** `bash infra/scripts/glitchtip-triage.sh <issue_id>` runs against an existing GlitchTip issue,
**Then** the script:
  1. Sources `infra/.env` once via `set -a; source infra/.env; set +a`.
  2. Validates required env via `: "${GLITCHTIP_AUTH_TOKEN:?missing}"` / `: "${GLITCHTIP_URL:?missing}"`.
  3. Validates `<issue_id>` arg present (else prints `--help`-equivalent and exits non-zero).
  4. Checks `command -v jq curl >/dev/null` (exits 1 with stderr message on missing).
  5. Calls `GET $GLITCHTIP_URL/api/0/issues/<issue_id>/events/latest/` using the curl+jq idiom from AR13 — captures `http_code` via `-w '%{http_code}'`, case-statement maps 401/403 → exit 3, 5xx → exit 2, non-2xx → exit 1.
  6. Optionally calls `GET $GLITCHTIP_URL/api/0/issues/<issue_id>/events/?limit=5` for the "last 5 events" field (or extracts from the latest-event response if it includes recent siblings — implementation choice).
  7. Extracts via `jq -r` and prints to stdout in fixed order per architecture Decision F template:
     ```
     # Issue #<issue_id>: <title>

     - **Top frame:** `<filename>:<line>`
     - **Fingerprint:** `<fingerprint>`
     - **Route:** `<route.pathname>` `(model.id=<id>)` (the `(model.id=...)` segment present only when `model.id` tag exists on the event)
     - **Release:** `<release>` (commit `<git.commit>`)
     - **Last 5 events:**
       1. `<timestamp>` — `<message preview>`
       ...
     - **Suggested file to edit:** `<filename>` (top-frame source)

     GlitchTip link: <permalink>
     ```
**And** the script supports a `--schema` flag that prints the bare template with placeholder tokens (`<title>`, `<filename>`, etc.) and exits 0 — used for golden-file diff verification.
**And** `tests/golden/triage-schema.txt` is created containing exactly the `--schema` output.
**And** running `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returns zero diff and exit 0 — covers NFR-I3 verifiable contract.
**And** the script is read-only against GlitchTip (only `GET` requests; no `PUT` / `POST` / `DELETE`) — covers FR20.
**And** typical-issue lookup completes within 5 s wall-clock (NFR-P4); 10 s ceiling for a large-event response; no retry loop on transient 5xx (fail clean per NFR-P4).
**And** the script follows AR12 bash conventions: `set -euo pipefail`, dependency check, env loading once, required-env validation, stdout (markdown) vs stderr (errors/warnings) split, header comment block (10–20 lines: purpose, prerequisites, exit codes, example, `--schema` flag explanation).
**And** a `--help` flag prints the same content as the header comment block.

---

### Epic 3: Verify Ritual, Decay Protection & Operational Continuity

**Goal:** Every deploy proves observability is alive: `deploy.sh` invokes `verify-symbolication.sh` post-deploy, happy-path writes a timestamped `infra/.last-verify`, failure-path produces three independent signals (loud red stdout warning + FAILED marker + synthetic GlitchTip event tagged `deploy.verification=failed`). The next deploy reads last-verify state and warns on stale state (decay protection). The operator has a documented same-day token rotation procedure with exact required scopes, and `_bmad-output/project-context.md` carries three new execution-discipline rules anchoring the loop for future BMAD agents.

**Prerequisite:** Epic 1 stories 1.2 (`release.ts`) and 1.3 (Vite `define`) must land first — Story 3.1's smoke event needs the `RELEASE` value to match the deployed bundle. Stories 3.3 + 3.4 are doc-only (do not block on E1/E2 code) but should land in the same release cycle as the runtime changes for runbook coherence.

#### Story 3.1: `verify-symbolication.sh` — Smoke Event + 30 s Poll + Tripwire + Synthetic Alarm

As `deploy.sh` (or Michał running it standalone),
I want one command that triggers a deterministic frontend smoke event in production, polls GlitchTip REST for that specific event, asserts the top stack frame regex matches a real source file path, writes a timestamped `infra/.last-verify` marker, and on failure emits a synthetic GlitchTip event tagged `deploy.verification=failed`,
So that observability has a tripwire — silent decay is structurally impossible (NFR-R3 three-signal failure model).

**Acceptance Criteria:**

**Given** `infra/.env` carries `GLITCHTIP_AUTH_TOKEN` (with `org:read` + `project:read` + `event:write`) and `GLITCHTIP_URL`, and the production page at `https://3d.ezop.ddns.net` exposes a smoke-event mechanism (e.g., a `?__sentry_smoke=<uuid>` query param that triggers a deliberate JS error with the UUID in the stack — exact mechanism designed during dev: simplest implementation is a 5-line `apps/web/src/main.tsx` block that on `URLSearchParams.get('__sentry_smoke')` calls `Sentry.captureException(new Error(\`smoke ${uuid}\`))` and tags the event with `smoke.run_id=<uuid>`),
**When** `bash infra/scripts/verify-symbolication.sh` runs,
**Then** the script:
  1. Sources `infra/.env`; validates env via AR12 conventions; checks `command -v jq curl >/dev/null`.
  2. Generates `smoke_run_id=$(uuidgen)` (or `cat /proc/sys/kernel/random/uuid`).
  3. Triggers the smoke by making a `curl -s -o /dev/null https://3d.ezop.ddns.net/?__sentry_smoke=$smoke_run_id` request; the SPA loads, the smoke handler fires, the SDK emits an event with the UUID tag.
  4. Polls `GET $GLITCHTIP_URL/api/0/projects/homelab/3d-portal/issues/?statsPeriod=5m&query=smoke.run_id:$smoke_run_id` (or equivalent fingerprint search) every 2 s up to a 30 s wall-clock budget.
  5. On match: extracts the top frame `filename`, asserts regex match `^apps/web/src/.+\.tsx?$` (NFR-R1 strict regex), writes `infra/.last-verify` with format `<ISO-8601>\t<STATUS>\t<deploy_version>` (single line, tab-separated, plain ASCII; STATUS=`OK`; deploy_version = the `RELEASE` extracted from the event's `release` field), exits 0.
  6. On no-match within budget: exits 4.
  7. On regex mismatch: writes `infra/.last-verify` with `STATUS=FAILED`, emits a synthetic GlitchTip envelope event with tags `{ deploy.verification: 'failed', smoke.run_id: '$smoke_run_id', service.version: '$release', deployment.environment: 'production' }`, level `warning`, message `"deploy verification failed: symbolication broken (top frame regex mismatch)"`, extra `{ exit_code: 1, expected_top_frame_regex: '^apps/web/src/.+\\.tsx?$', actual_top_frame: '<frame>' }`, exits 1.
  8. On REST 5xx / network error: exits 2 (no synthetic event — GlitchTip is the broken party, can't reach it).
  9. On REST 401/403: exits 3 (synthetic event optional — if auth works for the alarm POST it goes; if not, log only).
  10. Total wall-clock budget ≤30 s (codifies FR12 + NFR-P3); script exits 4 on timeout.
**And** the script is idempotent — re-running it with a fresh UUID produces a fresh `infra/.last-verify` line (no stale collision).
**And** the script follows AR12 bash conventions and AR13 curl+jq idiom (header comment block: purpose, prerequisites, exit-code map 0/1/2/3/4, example, `--help` flag).
**And** a manually-broken bundle (e.g., temporarily renaming a `dist/*.js.map` so symbolication fails) makes a follow-up `verify-symbolication.sh` exit 1 and the corresponding synthetic alarm event appears in GlitchTip with the expected tags within 30 s.
**And** `infra/.last-verify` is added to root `.gitignore` (or to `infra/.gitignore` if one exists) — never committed.
**And** `tests/golden/last-verify-format.txt` exists with one example line documenting the exact format (single-line tab-separated `<ISO-8601>\t<STATUS>\t<release>`); Story 3.2 references this format.

#### Story 3.2: `deploy.sh` Integration — `DOCKER_BUILDKIT=1` + Verify Call + Last-Verify Tripwire + Exit-Code-Mapped Warning

As Michał running `deploy.sh`,
I want `deploy.sh` to export `DOCKER_BUILDKIT=1` (covering both Story 1.5's BuildKit secret prerequisite and the post-deploy verify call), invoke `verify-symbolication.sh` post-deploy as non-fatal, print exit-code-mapped warning text, and on next invocation warn if `infra/.last-verify` is stale,
So that deploy success is decoupled from observability post-condition (NFR-R3) while three-signal failure detection holds (FR15, FR16).

**Acceptance Criteria:**

**Given** Story 3.1 is complete (`verify-symbolication.sh` exists with stable exit codes 0/1/2/3/4),
**When** `infra/scripts/deploy.sh` is modified to:
  1. Export `DOCKER_BUILDKIT=1` near the top of the script (before `docker compose build`) — single export covers Story 1.5's prerequisite. If the export already exists from Story 1.5 land, this story is a no-op for that line; otherwise this story owns it.
  2. At the START of `deploy.sh` (before the build phase), read `infra/.last-verify` and the timestamp of the previous deploy (e.g., `git log -1 --format=%ct main` or `infra/.last-deploy` if such a file is introduced — pick simplest mechanism documented in the inline comment) — if `infra/.last-verify` mtime is older than the previous deploy timestamp, print a yellow `⚠ stale verify: previous deploy did not record a successful verification` warning to stderr, do NOT abort.
  3. After `docker compose up -d` + `alembic upgrade head` complete, invoke `bash "$REPO_DIR/infra/scripts/verify-symbolication.sh"` capturing exit code into `verify_exit` (`|| verify_exit=$?` syntax, NOT `|| true`).
  4. Map `verify_exit` to a printed warning per Decision K example:
     ```
     case "$verify_exit" in
       0) echo "✓ verify OK" ;;
       1) echo -e "\033[31m⚠ verify FAILED: symbolication broken (top frame regex mismatch)\033[0m" >&2 ;;
       2) echo -e "\033[31m⚠ verify FAILED: GlitchTip unreachable\033[0m" >&2 ;;
       3) echo -e "\033[31m⚠ verify FAILED: auth/scope failure — token rotation needed?\033[0m" >&2 ;;
       4) echo -e "\033[31m⚠ verify FAILED: timeout (no matching event within 30s)\033[0m" >&2 ;;
       *) echo -e "\033[31m⚠ verify FAILED: unexpected exit $verify_exit\033[0m" >&2 ;;
     esac
     ```
  5. Deploy exit code remains independent of `verify_exit` — `deploy.sh` exits 0 if all build/ship/restart phases succeed regardless of verify outcome (FR15 non-fatal contract).
**Then** running `bash infra/scripts/deploy.sh` end-to-end on a healthy `.190` produces successful deploy + `verify-symbolication.sh` exit 0 + `infra/.last-verify` updated with `OK` line + `✓ verify OK` printed to stdout.
**And** running with verify deliberately broken (e.g., temporarily rename `verify-symbolication.sh` to fail) produces successful deploy + the corresponding red warning printed to stderr + `infra/.last-verify` carrying `FAILED` (or absent if script crashed before write — acceptable, the next invocation will warn on stale state per FR16).
**And** running `bash infra/scripts/deploy.sh` immediately after a previous run that ended in `FAILED` produces the stale-verify warning at the START (yellow `⚠ stale verify: ...`) — codifies FR16.
**And** `bash -x infra/scripts/deploy.sh` trace contains the `verify-symbolication.sh` invocation and zero matches for the legacy `upload-sourcemaps.sh` invocation (cross-checks Story 1.6 decoupling).

#### Story 3.3: `docs/operations.md` — Symbolication Section Rewrite (Ritual + Recovery + Rotation + Triage + Scopes)

As an operator (human Michał or an AI agent landing cold in the repo),
I want the runbook section on observability rewritten to current state: the deploy + verify ritual, the manual recovery flow (CLI fallback), the same-day token rotation procedure, the exact required token scopes, and the triage script usage,
So that no one has to reverse-engineer the workflow from code or PR history.

**Acceptance Criteria:**

**Given** `docs/operations.md` currently contains a "Sentry vite-plugin out-of-scope follow-up" note (or equivalent baseline section),
**When** the section is rewritten as a new "GlitchTip observability — operator runbook" section containing the following subsections (titles may adjust during dev for prose flow but each topic must be present):
  1. **Deploy ritual:** `bash infra/scripts/deploy.sh` runs build + ship + restart + alembic + `verify-symbolication.sh`. Verify is non-fatal but loud. Three-signal failure model (stdout warn + `infra/.last-verify` FAILED + synthetic GlitchTip event tagged `deploy.verification=failed`).
  2. **Manual recovery — CLI fallback:** when plugin upload fails (issue #299, transient 5xx, expired token mid-build), run `bash infra/scripts/upload-sourcemaps.sh` standalone after a fresh `npm run build` — this uploads source maps using the same `RELEASE` identity as the plugin path. Re-run `bash infra/scripts/verify-symbolication.sh` to confirm.
  3. **Token rotation procedure (same-day):** open GlitchTip web UI on LAN/VPN → Profile → Auth Tokens → create new token with the exact scopes listed in the next subsection → update `infra/.env`'s `GLITCHTIP_AUTH_TOKEN` value → run `bash infra/scripts/deploy.sh` to validate via plugin upload → revoke old token → record rotation date in this runbook (or `_bmad-output/project-context.md` as evergreen log).
  4. **Required token scopes (exact list):** `org:read`, `project:read`, `project:write`, `project:releases`, `event:write`. NOT `org:write`, NOT `org:admin`. (FR28 + NFR-S3.)
  5. **Triage script usage:** `bash infra/scripts/glitchtip-triage.sh <issue_id>` returns a markdown stub paste-ready into `bmad-quick-dev` / `bmad-create-story`. Output schema fixed; verifiable via `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -`. Read-only against GlitchTip.
  6. **Cross-references:** link to `~/repos/configs/docs/glitchtip-agent-guide.md` for REST recipes; link to `~/repos/configs/docs/observability-logging-contract.md` for tag taxonomy.
  7. **GlitchTip 6.1.x version pin:** note that scripts depend on the 6.1.x REST API surface; an upgrade requires re-validation per NFR-I1 (cite the upgrade-checklist subsection by reference).
**Then** `docs/operations.md` opens with the rewritten section in a sensible position (not buried) — TOC or section order updated.
**And** the legacy "Sentry vite-plugin out-of-scope follow-up" note is removed (not commented out).
**And** the section is internally consistent with the actual scripts shipped in E1/E2/E3 (no dangling references to renamed flags or non-existent paths).
**And** the doc-only commit follows project memory: skips auto-deploy (per `feedback_auto_deploy_dev`) — commit scope `docs(infra)` or `docs(operations)`.

#### Story 3.4: `_bmad-output/project-context.md` — Three New Execution-Discipline Rules

As any future BMAD agent (Claude Code / Codex / Gemini) working in this repo,
I want three new execution-discipline rules pinned in `_bmad-output/project-context.md`,
So that agents arriving cold do not have to re-derive operational discipline from PRs or commit history.

**Acceptance Criteria:**

**Given** `_bmad-output/project-context.md` currently exists with `rule_count: 125` and a status of `complete`,
**When** the file is updated to add three new rules under an appropriate existing section (likely "Critical Don't-Miss Rules" → "Infra & deploy" or a sibling "Observability" subsection — implementation choice during dev for cohesion):
  1. **"Run `verify-symbolication.sh` after every deploy until CI auto-verify lands."** Rationale: NFR-R3 three-signal failure model only holds when humans/agents actually invoke the verify script. `deploy.sh` calls it automatically as of E3 Story 3.2; this rule applies if/when an agent runs a partial deploy or skips `deploy.sh`.
  2. **"Use `glitchtip-triage.sh <issue_id>` before manual triage of a GlitchTip-reported bug."** Rationale: Journey 1 in PRD — the markdown stub IS the triage interface for AI agents; opening the GlitchTip UI is the slow path. Pull-only ergonomics is design, not degraded mode.
  3. **"Every replacement keeps its predecessor as documented manual recovery for one release cycle."** Rationale: codifies the brief's principle (CLI fallback retained alongside plugin migration; FR25–26 + Decision E rejected-alternative). Promoted from this delta's local pragmatism into a repo-wide principle for future replacements.
**And** the frontmatter `rule_count` is incremented from `125` to `128`.
**And** the frontmatter `date` and `Last Updated` lines are updated to the day Story 3.4 ships.
**And** the doc-only commit skips auto-deploy — commit scope `docs(bmad)` or `chore(bmad)`.
**And** running `grep -c '^- \*\*' _bmad-output/project-context.md` (or the equivalent rule-counting heuristic the file uses) returns a value consistent with the new `rule_count: 128`.

## Initiative 2 — Agent Runbook + Legacy SoT Triage

**Status:** ✅ shipped 2026-05-11 (started 2026-05-10). This initiative decomposes the requirements from `prd.md` § Initiative 2 (11 FRs + 8 NFRs) and `architecture.md` § Initiative 2 (8 decisions A–H) into implementable stories E4.1–E4.6.

**No product brief in `_bmad-output/planning-artifacts/`.** Init 2 was planned + executed via the autonomous chain (Session 2, 2026-05-10) without a separate `bmad-product-brief` stage; scope was small enough (~1–2 person-days, single-epic decomposition) that brief + distillate were folded into the PRD extension directly. Acknowledged hygiene gap per `feedback_docs_hygiene` (no retro-brief planned; gap is explicit and not silent).

### Overview

Brownfield extension to the SoT-migrated portal. Scope: ~1 markdown doc (`docs/agents-add-model-runbook.md`), ~10 lines of FastAPI route, Dockerfile COPY + nginx pass-through rule, ~6 admin/sot router enrichment edits (OpenAPI summary/description/tags + Pydantic examples), 1 migration-report decision doc, 1 acceptance-smoke-test transcript, optional CLI script. Budget: 1–2 person-days of agent execution time.

**No UX document** — this initiative does not touch UI; visual-regression matrix preserves no-regression invariant. Frontend changes: zero.

### Requirements Inventory

Pointer rather than duplication. Functional requirements: see `prd.md` § Initiative 2 § "Functional Requirements" (FR1–FR11, grouped A–G). Non-functional requirements: see `prd.md` § Initiative 2 § "Non-Functional Requirements" (NFR1–NFR8). Architectural decisions: see `architecture.md` § Initiative 2 § "Core Architectural Decisions" (A–H).

**Coverage:** 11/11 FRs + 8/8 NFRs + 8/8 Decisions mapped across the 6 stories below.

### Epic List

The MVP scope ships as 1 epic (Epic 4), 5 MVP stories + 1 Growth story. Single-epic structure reflects Initiative 2's smaller surface area (~1–2 person-days) vs Initiative 1's 3-epic decomposition (~2–3 person-days). No conditional branching — each story is independent or has a documented dependency below.

#### Epic 4: Self-Serving Agent Runbook + Legacy SoT Triage

**User outcome:** An AI agent (Claude, Codex, future LLM) given a Printables / Thangs / Thingiverse / MakerWorld / Creality Cloud URL + the path to `~/.config/3d-portal/agent.password` (agent service-account password file, mode 600) can create a model in the portal from a fresh session, without reading any file in `~/repos/3d-portal/`. Auth is cookie-based (login → ride `portal_access` cookie + `X-Portal-Client: web` CSRF header), NOT a long-lived bearer token. The runbook is served by the portal itself (`/agent-runbook`), endpoint catalog is auto-discovered via `/api/openapi.json`, drift between markdown and API surface is impossible by construction. Legacy SoT folder (`/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`) triage decision is recorded with written rationale.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9 (Growth), FR10, FR11
**NFRs touched:** NFR1, NFR2, NFR3, NFR4, NFR5, NFR6, NFR7, NFR8
**Decisions touched:** A (route delivery), B (public access), C (layered docs), D (fingerprint), E (OpenAPI enrichment), F (source detection), G (CLI thin shim), H (decision-doc-first)
**Dependencies:** Story 4.5 (acceptance smoke-test) requires stories 4.1–4.3 done. Story 4.6 (Growth CLI) requires story 4.1 (runbook content) done.

---

### Epic 4: Self-Serving Agent Runbook + Legacy SoT Triage

**Goal:** Restate of user outcome above. AI agent boots from one URL + one token path; portal documents itself via the runbook endpoint + auto-generated OpenAPI; legacy folder gap closed with a written decision.

**Implementation Status (refreshed 2026-05-15 per Codex implementation-readiness review M2/M3):**

| Story | Status | Commit(s) | Execution divergence from plan |
|---|---|---|---|
| 4.1 — Author `docs/agents-add-model-runbook.md` | ✅ done 2026-05-11 | `b382fee` + `ec27222` (Codex fix-up: 1 P1 + 5 P2 + 1 P3) | None — clean ship; Printables mutation signature P2 deferred to Story 4.5 smoke-test |
| 4.2 — `/agent-runbook` FastAPI route + deploy verify | ✅ done 2026-05-11 | `9ac52f6` + `565b347` (Codex fix-up: 1 P1 + 1 P2 + 2 P3) | **In-repo `infra/nginx-180/3d-portal.conf` archived during execution** — discovered the live edge proxy at `~/repos/configs/nginx/3d.ezop.ddns.net.conf` is a simpler IP-allowlist catch-all and needs no edge sync for `/agent-runbook`. In-repo config moved to `infra/nginx-180/.archived/3d-portal.conf.pre-IP-allowlist` per TB-003 (commit `6e680be`). **Story 4.2 plan text below references the original (pre-archive) path for historical fidelity; Codex M3 (absent nginx path) is resolved by this reality note.** |
| 4.3 — OpenAPI surface enrichment for agent consumption | ✅ done 2026-05-11 | `369e3f6` + `7ac5e61` (Codex fix-up: 8 P2 + 2 P3 — all desc-vs-impl drift) | Tightened test from sanity-count to strict route-set membership |
| 4.4 — Legacy SoT folder triage decision | ✅ done 2026-05-11 | `3acb698` + `d1586f0` (Codex fix-up: 0 P1 + 3 P2 + 3 P3) | Decision: DROP recommended; 4.4-followup (Alembic 0010 drop legacy_id) shipped same day in `89da8e4` |
| 4.5 — End-to-end smoke-test acceptance | ✅ done 2026-05-11 | smoke-test transcript at `_bmad-output/implementation-artifacts/agent-runbook-smoke-2026-05-11.md` (operator-local) | R-1/R-2/R-3 runbook gaps fixed in `691e4f0`; R-4/R-5 deferred. NFR5 cross-LLM (Codex execution) deferred to optional follow-up |
| 4.6 — `infra/scripts/add-model-from-url.py` CLI | 📋 backlog (Growth — explicitly deferred) | — | Per Story 4.6 AC: defer-able after 4.5 acceptance review |
| **4-4-followup-drop-legacy-id** | ✅ done 2026-05-11 | `89da8e4` (Path B / accept-risk per homelab single-tenant scope) | Alembic 0010 ran on prod; 4 migrations + 3 test files retired; ~1611 LOC net. Snapshot at `docs/migration-reports/2026-05-11-legacy-id-snapshot.json` |
| epic-4-retrospective | ✅ done 2026-05-11 | `_bmad-output/implementation-artifacts/epic-4-retro-2026-05-11.md` (operator-local) | First fully-autonomous epic in the repo |

**Codex implementation-readiness M2 (E4 stale vs worktree) — resolved by this status table.** Story plan text below retained for historical fidelity to the planning chain. Future agents reading Epic 4 should treat the Implementation Status table above as authoritative for shipped status, and the story sections below as historical context for HOW each story was scoped before execution.

#### Story 4.1: Author `docs/agents-add-model-runbook.md`

As an AI agent (Claude, Codex, or future LLM) tasked with adding a model to 3d-portal from a URL,
I want a single curated markdown file that teaches me principles, auth model, source detection, behavioral rules, and operational invariants,
So that I can execute the full URL-to-portal flow without reading any source code or any other file in the repository.

**Acceptance Criteria:**

**Given** `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` exists with un-migrated runbook knowledge (§ "Workflow: Adding a New Model", § "Downloading from Printables (GraphQL)", § "3MF Conversion Workflow") and `docs/agents-add-model-runbook.md` does NOT yet exist,
**When** the agent ports the relevant content and reframes it for the post-SoT-migration DB-era (portal.db on .190 + `POST /api/admin/models` + `POST /api/admin/models/{id}/files` instead of folder layout + `_index/index.json`):
  - **Principles section** — pull-only ergonomics, REST + token, idempotence (FR10 + NFR1 + NFR6 captured as principles).
  - **Auth section** — agent service account is a regular `User` row with `role=agent`; credentials are a **password** (NOT a long-lived bearer token) at `~/.config/3d-portal/agent.password` (mode 600). Login flow documented end-to-end: read password inline `pw=$(cat ~/.config/3d-portal/agent.password)`, then `curl -c /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' -d '{"email":"agent@portal.local","password":"'"$pw"'"}' https://3d.ezop.ddns.net/api/auth/login` → server sets `portal_access` (`Path=/api`, ~30 min JWT TTL) + `portal_refresh` (`Path=/api/auth`, 30-day TTL) cookies. All subsequent admin/sot calls reuse via `-b /tmp/portal-cookies.txt`; mutations also need `-H 'X-Portal-Client: web'` (CSRF gate). Never `export PASSWORD=...` (persists in shell history); never `Authorization: Bearer ...` — admin routes read JWT from the cookie, not from the header. Long-running agent sessions either cron a daily relogin OR call `POST /api/auth/refresh` (with the refresh cookie) before access expires. Rotation procedure references `python -m scripts.bootstrap_agent --email agent@portal.local --rotate` on .190 — prints a new password to stdout once, capture and replace the file content (chmod 600 preserved); no service restart. (FR5 + NFR2.)
  - **Source-detection table** — URL host → fetch strategy: `printables.com` → GraphQL `getDownloadLink`, `thangs.com` / `thingiverse.com` / `makerworld.com` / `crealitycloud.com` → `agent-browser` CLI. (FR2.)
  - **Printables GraphQL recipe** — endpoint `https://api.printables.com/graphql/`, mutation signature `getDownloadLink(id, printId, fileType: stl, source: model_detail)`, one worked example with a real model ID, JSON response shape + file-fetch step. (FR3.)
  - **3MF conversion procedure** — every `.3mf` MUST be converted via `infra/scripts/migrate_catalog_3mf.py --convert <file.3mf>`; original archived to `_archive/3mf-originals/` on .190. Runbook references the script, does NOT duplicate its logic. (FR4.)
  - **Pre-flight checklist** — 5 items: (1) category slug exists (verify via `GET /api/categories`), (2) name sanitized (no diacritics, no whitespace, no extension), (3) STL present after any conversion, (4) duplicate-check (existing model with same source URL), (5) all source files in expected formats. (FR6.)
  - **Endpoint pointer** — one cross-link "For endpoint signatures, request/response schemas, status codes: `curl https://3d.ezop.ddns.net/api/openapi.json | jq` — see `paths.\"/api/admin/models\".post` etc." NO endpoint paths or method names duplicated inline. (Decision C + NFR8.)
**And** the runbook contains zero occurrences of HTTP-method-uppercase preceding `/api/` paths inside body text (smoke-test grep heuristic; cross-link sentence is the only allowed reference and uses backticks to avoid the heuristic).
**And** the runbook is < 600 lines (target: ~400) — dense, agent-readable, zero fluff.
**And** sha256 of a stable intro paragraph is captured into `infra/.runbook-fingerprint` (single line, committed) — establishes Decision D's fingerprint baseline (Story 4.2 consumes it).
**And** the doc-only commit skips auto-deploy — commit scope `docs(agents)`.

**Dev notes:**
- Source: `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` carries the legacy runbook content. Read it first; the content port is ~70% rewrite (DB-era endpoints, agent-token model, OpenAPI cross-link) and ~30% verbatim (GraphQL recipe, 3MF workflow).
- Use bash code-fence with language tag `bash` for command examples; agent parsers detect this.
- Stable intro paragraph candidate: the first paragraph under H1 (project description, before any operational content). Keep it ~3 sentences; edits to this paragraph are rare and intentional.

#### Story 4.2: `/agent-runbook` FastAPI route + deploy verify

As a fresh-session AI agent invoked with no prior repo knowledge,
I want `GET https://3d.ezop.ddns.net/agent-runbook` to return the canonical runbook content as `text/markdown`,
So that one URL bootstrap suffices to learn the portal's operational surface, without needing repo access.

**Acceptance Criteria:**

**Given** `docs/agents-add-model-runbook.md` exists and `infra/.runbook-fingerprint` contains a sha256 line (Story 4.1 done),
**When** Story 4.2 ships:
  - **New FastAPI module** `apps/api/app/modules/runbook/__init__.py` + `apps/api/app/modules/runbook/router.py` exposing `GET /agent-runbook` as `PlainTextResponse` reading from `/app/static/agent-runbook.md`. (Decision A.)
  - **Router mounted** in `apps/api/app/router.py` with no auth dependencies — public read. (Decision B.)
  - **Dockerfile updated** — `apps/api/Dockerfile` (or whichever shared image owns the API) adds `COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md` in the build stage. Static file lives at deterministic image path.
  - **nginx config updated** — `infra/nginx-180/3d-portal.conf` adds `location /agent-runbook { proxy_pass http://api; }` (or equivalent — matching the existing `location /api/` pattern). nginx config copied to `~/repos/configs/nginx/3d-portal.conf` and deployed via that repo's `sync.sh` per project convention.
  - **Response contract** — `200 OK` with `Content-Type: text/markdown; charset=utf-8`. `503` if the file is missing from the image (deploy bug — fail loud, not silent 404).
  - **Deploy verify extension** — `infra/scripts/deploy.sh` (post-`alembic upgrade head`, before exit) computes `curl https://3d.ezop.ddns.net/agent-runbook | sha256-check vs $(cat infra/.runbook-fingerprint)`. Mismatch → stderr warning (non-fatal) + `infra/.last-verify-runbook` FAILED marker. Same three-signal model as Initiative 1's `verify-symbolication.sh` per NFR-R3 (Initiative 1) / NFR7 (Initiative 2). (Decision D.)
**And** smoke test on local dev: `curl http://192.168.2.190:8090/agent-runbook` returns 200 + markdown body during `docker compose up` (LAN HTTP path; `https://` requires .180 edge proxy reload).
**And** smoke test on production after deploy: `curl https://3d.ezop.ddns.net/agent-runbook | wc -l` returns ≥100 lines (runbook is non-empty).
**And** auto-deploy fires for this commit (code + infra change) per project memory `feedback_auto_deploy_dev.md`.

**Dev notes:**
- The `/api/` prefix is intentionally NOT used for `/agent-runbook` — the runbook is conceptually a top-level discovery resource, not an API. nginx routes `/agent-runbook` to the API container directly. If a future contract demands `/api/agent-runbook`, that's a redirect away.
- Match existing module style: `apps/api/app/modules/admin/router.py` and `apps/api/app/modules/share/router.py` are good shape references.

#### Story 4.3: OpenAPI surface enrichment for agent consumption

As an AI agent consuming `/api/openapi.json` to discover endpoint signatures,
I want each agent-callable endpoint under `admin/` and `sot/` to carry a `summary`, `description` (including behavioral side-effects), a relevant tag, and at least one request-body example on its Pydantic input model,
So that I can read the OpenAPI surface and execute the agent flow without spelunking the FastAPI source.

**Acceptance Criteria:**

**Given** `apps/api/app/modules/sot/admin_router.py` and `apps/api/app/modules/admin/router.py` currently define routes with default (or missing) `summary` / `description` and most Pydantic request models lack `json_schema_extra` examples,
**When** Story 4.3 ships:
  - **Every `@router.post / @router.put / @router.patch / @router.delete` decorator** in `apps/api/app/modules/{admin,sot}/` carries an explicit `summary="One-line capability description"` and `description="Multi-line including behavioral side-effects (e.g., 'first STL upload auto-enqueues render')."` (Decision E; FR11.)
  - **Endpoints callable by the `agent` role** carry `tags=["agent-write"]` (additive — existing tag conventions preserved).
  - **Key Pydantic request models** — `ModelCreate`, `ModelPatch`, `ModelFilePatch`, `RenderRequest`, `PhotoReorderRequest`, `ThumbnailSet`, plus tag/category/note/print/external_link create/patch payloads — carry `model_config = ConfigDict(json_schema_extra={"examples": [{...realistic example...}]})` with at least one realistic example payload.
  - **New Pytest** `apps/api/tests/test_openapi_agent_surface.py` asserts: (a) every route in `app/modules/{admin,sot}/*.py` has non-empty `summary` in OpenAPI, (b) every route has non-empty `description`, (c) every agent-writable request model has at least one `examples` entry. Test FAILS if a future route is added without these.
  - **Spot check** — `curl https://3d.ezop.ddns.net/api/openapi.json | jq '.paths."/api/admin/models".post.summary'` returns a non-empty string.
**And** `npm run lint` (apps/web) is irrelevant — no frontend touched. `ruff check apps/api` passes. `pytest apps/api/tests/test_openapi_agent_surface.py` passes.

**Dev notes:**
- The `agent` role is already part of the auth system (Slice 2D). The `agent-write` tag is purely OpenAPI metadata, NOT a runtime authorization filter. Filtering happens via existing `Depends(current_user)` + role check.
- `json_schema_extra.examples` is the Pydantic v2 idiom (NOT `Config.schema_extra` v1 style).

#### Story 4.4: Legacy SoT folder triage decision

As an operator maintaining the 3d-portal codebase,
I want a written decision documenting whether to retire `Model.legacy_id` + the 4 migration scripts (`migrate_from_index_json.py`, `backfill_legacy_renders.py`, `backfill_iso_thumbnail.py`, `fix_legacy_render_names.py`) entirely OR freeze them as a "do-not-touch-unless-restore" artifact,
So that a future agent grep'ing those scripts finds the rationale immediately without reconstructing it from git history or guess.

**Acceptance Criteria:**

**Given** the legacy SoT folder at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` currently serves as restore-snapshot for the 4 migration scripts in `apps/api/scripts/`, and `Model.legacy_id` exists as a nullable unique column on the `model` SQLModel entity,
**When** Story 4.4 ships:
  - **Audit inputs gathered:**
    1. Query `audit_log` for any READ/WRITE referencing `legacy_id` since 2026-05-06 (the SoT migration cutover). Record date + caller of last use (or "never used post-cutover" if zero hits).
    2. Verify schema compatibility — would the 4 migration scripts run against the current schema (post-Alembic-0008) without code changes? Attempt a dry-run of one script (e.g., `migrate_from_index_json.py --dry-run` if such flag exists, or wrap in a transaction that always rolls back) and record outcome.
    3. Backup strategy if scripts retire — export `Model.legacy_id` column to a frozen JSON (one-time, ~89 rows ~5 KB) committed to `docs/migration-reports/` as a permanent artifact.
  - **Decision document** `docs/migration-reports/2026-05-XX-legacy-sot-folder-decision.md` captures all three inputs above + the chosen option + the reasoning. Decision space: **drop** (retire `Model.legacy_id` + 4 migration scripts, schedule follow-up Alembic migration) OR **freeze** (keep column + scripts + folder, add `apps/api/scripts/README.md` marker with "do not modify; restore-only artifact"). The doc states which option and why.
  - **Follow-up story noted** — if "drop": follow-up is "E4.4-followup-drop-legacy-id-alembic" (separate Alembic migration story, gated on this decision being merged). If "freeze": follow-up is "E4.4-followup-freeze-scripts-readme" (trivial README marker creation; can be appended to this same commit if scope-compatible, OR split as separate doc-only commit).
**And** the decision is recorded BEFORE any executing action (irreversibility discipline per Decision H + NFR4).
**And** the doc-only commit skips auto-deploy — commit scope `docs(migration-reports)`.

**Dev notes:**
- The `audit_log` query is straightforward: `SELECT * FROM auditlog WHERE old_values LIKE '%legacy_id%' OR new_values LIKE '%legacy_id%' OR entity_type='model' AND created_at > '2026-05-06'`. If `audit_log` doesn't track column-level reads (it tracks mutations), the question shifts to "any script invocation since 2026-05-06" — query script execution times via shell history or commit history.
- Schema-compat check: simplest is `import` the script in a python REPL with the current models — if imports resolve, models match. Run-time call is not strictly needed.
- The frozen JSON backup is small enough to commit. Don't bother with object storage.

#### Story 4.5: End-to-end smoke-test acceptance

As Ezop validating Initiative 2 is "done" rather than just "written",
I want a fresh-session AI agent (Claude or Codex) to execute the full URL-to-portal flow against one real Printables URL using only the runbook endpoint + the agent token,
So that the runbook is proven agent-executable end-to-end, not just plausibly-readable.

**Acceptance Criteria:**

**Given** Stories 4.1, 4.2, 4.3 are done (runbook content + `/agent-runbook` endpoint + OpenAPI enrichment all live on .190 / 3d.ezop.ddns.net),
**When** an AI agent invoked in a fresh session (no prior repo context) is given:
  1. Portal URL: `https://3d.ezop.ddns.net`
  2. Bootstrap instruction: "fetch `/agent-runbook` for principles; fetch `/api/openapi.json` for endpoint catalog"
  3. Password file path: `~/.config/3d-portal/agent.password` (mode 600); default email `agent@portal.local`
  4. One real Printables URL chosen by Ezop (e.g., a Cali Cat or similar small printable that doesn't already exist in the catalog)
  5. Target category slug (or "agent picks via `GET /api/categories`")
**Then** the agent executes the flow autonomously and produces:
  - **A model row in the catalog** — visible at `https://3d.ezop.ddns.net/` with the chosen URL's metadata (name, source link, at least one STL file, at least one render after auto-enqueue completes).
  - **A full transcript** committed as `_bmad-output/implementation-artifacts/agent-runbook-smoke-2026-05-XX.md` — every shell command run (with token redacted), every HTTP request + response status + body excerpt, every file uploaded, the resulting model UUID, the render-completion confirmation timing.
  - **Smoke-test self-verification** within the transcript:
    - (a) `curl /agent-runbook` returned valid markdown of length ≥ a threshold AND sha256 of intro paragraph matches `infra/.runbook-fingerprint`.
    - (b) `curl /api/openapi.json` returned valid OpenAPI 3.x JSON with `paths."/api/admin/models".post` AND `paths."/api/admin/models/{model_id}/files".post` defined.
    - (c) `POST /api/admin/models` returned 201 with a UUID; `POST /api/admin/models/{id}/files` (multipart STL) returned 201; `GET /api/models/{id}` thumbnail field became non-null within 60 s (auto-render landed).
    - (d) The model is visible at the catalog page.
  - **NFR8 drift-check** within the transcript: a grep against the runbook for HTTP-method-uppercase preceding `/api/` paths returns zero matches outside the explicit cross-link sentence (auto-discovery principle holds — runbook didn't duplicate endpoint signatures).
**And** the transcript-creation commit scope is `docs(bmad)` (in `_bmad-output/implementation-artifacts/`, which is gitignored per project memory `feedback_local_only_docs.md` — so the artifact lives on the operator's dev box only, mirroring the constraint).
**And** the transcript captures any deviations from the runbook (sources of friction, agent confusion, missing context) as a "Runbook gaps" section. These feed Story 4.6 OR a follow-up runbook edit, depending on scope.

**Dev notes:**
- Smoke-test execution can happen via Claude (this session, after auto-deploy of stories 4.1–4.3 completes), Codex, or a third party. Cross-agent execution is the strongest acceptance signal but logistically Claude or Codex is faster.
- Credentials redaction: smoke-test transcripts should redact (a) the raw password (`-d '{"email":"agent@portal.local","password":"<REDACTED>"}'`), (b) the cookie-jar contents (`Cookie: portal_access=<REDACTED>; portal_refresh=<REDACTED>`), and (c) the `Set-Cookie` response headers from `/api/auth/login`. Inline `$(cat ...)` pattern in commands keeps the password out of tool-output anyway, but explicit redaction across these three surfaces is a belt-and-suspenders safeguard.

#### Story 4.6: `infra/scripts/add-model-from-url.py` CLI (Growth, deferable)

As an operator who wants one-command model creation from a Printables URL (without invoking an LLM agent for each model),
I want a Python CLI script that encodes the runbook flow as executable code with structured progress logs and idempotence checks,
So that batch imports + scripted re-runs are cheap, while drift detection guarantees the script stays consistent with the canonical runbook.

**Acceptance Criteria (Growth scope — deferable):**

**Given** Story 4.1 (runbook content) is done and `/agent-runbook` is reachable,
**When** Story 4.6 ships:
  - **New CLI** `infra/scripts/add-model-from-url.py` (≤200 lines, single-file Python).
  - **Positional arg:** source URL.
  - **Optional flags:** `--category <slug>` (default: prompt-on-stdout-and-stderr if missing), `--password-file <path>` (default `~/.config/3d-portal/agent.password`), `--email <addr>` (default `agent@portal.local`), `--portal <base-url>` (default `https://3d.ezop.ddns.net`), `--dry-run` (validate flow without `POST`s), `--verify-against-runbook` (fetch `/agent-runbook`, compare source-detection table sha256 vs hardcoded, exit non-zero on mismatch). Login is performed internally via `POST /api/auth/login` and the cookie jar is held in-memory (not written to disk).
  - **Source coverage:** Printables only (MVP for CLI). Other sources output "not yet implemented in CLI; use the runbook manually" and exit non-zero. (Decision F + G.)
  - **Progress logs** to stdout as JSON-lines (`{"step": "fetch_metadata", "status": "ok", "duration_ms": 234}`) — mirrors observability contract.
  - **Exit code:** `0` + model UUID on stdout on success. Non-zero with one-line JSON error payload (`{"error": "category_not_found", "detail": "slug 'foo' does not exist"}`).
  - **Idempotence:** dedup check via `GET /api/models?source_url=<url>` (or equivalent search) before `POST /api/admin/models` — if exists, return the existing UUID and exit 0 with a `"created": false` flag.
  - **Drift detection:** `--verify-against-runbook` mode fetches `/agent-runbook`, parses the source-detection table, computes its sha256, compares against a hardcoded constant in the script. Mismatch → exit non-zero with `{"error": "runbook_drift", "detail": "..."}`.
**And** `ruff check` passes; `python3 infra/scripts/add-model-from-url.py --help` prints usage.
**And** the script is referenced from the runbook (FR1) as "an optional convenience — `infra/scripts/add-model-from-url.py <url> --category <slug>` encodes the Printables path; for other sources or for one-off imports, follow the runbook flow directly".

**Dev notes:**
- This story is **Growth scope** — defer if runbook + endpoint MVP delivers enough value on its own. Decision point: after Story 4.5 acceptance, review the smoke-test "Runbook gaps" section. If gaps are mostly "agent had to retry / agent didn't know X" → CLI is high value. If gaps are minimal → CLI is nice-to-have, defer to Vision.
- The script's GraphQL recipe should be a near-direct port of the runbook's `printables.com` row. Drift detection guards against the two diverging.

## Initiative 3 — UI Theme Compliance & Visual Regression Hardening

**Status:** ✅ shipped 2026-05-13 (started + completed 2026-05-13, single-session autonomous). This initiative decomposes the requirements from `prd.md` § Initiative 3 (17 FRs + 9 NFRs) and `architecture.md` § Initiative 3 (10 decisions A–J in-scope; K–M deferred — re-eval 2026-06-13) into implementable stories E5.1–E5.17.

### Overview

Brownfield remediation+prevention initiative layered on the 2026-05-12 post-TB-012 baseline. Scope: ~6 modified `apps/web/src/ui/` + viewer overlay files (Dialog, Sheet, RimOverlay, MeasureOverlay, plus any Phase-A surfaces), 1 extracted CSS file (`viewer-tokens.css`), 1 modified `theme.css` (3 new `.dark` overrides + 2 new overlay tokens), 1 modified ESLint config, 1 new Stylelint config, 1 new husky pre-commit hook + 2 Node helpers, 1 new axe spec, ~8 new open-state Playwright specs + ~32 new PNG baselines, 1 modified `package.json` (devDeps + lint chain), 1 new Codex prompt artifact + wrapper script, 1 modified `project-context.md` (2 new rules). Budget: 2–3 sprint-equivalent units of agent execution.

**No UX document** — visual changes are constrained to fixing existing surfaces (Dialog/Sheet/viewer overlays); no new UI primitives ship in Initiative 3.

### Requirements Inventory

Pointer rather than duplication. Functional requirements: see `prd.md` § Initiative 3 § "Functional Requirements" (FR1–FR17, grouped A–D). Non-functional requirements: see `prd.md` § Initiative 3 § "Non-Functional Requirements" (NFR1–NFR9). Architectural decisions: see `architecture.md` § Initiative 3 § "Core Architectural Decisions" (A–J in-scope; K–M deferred).

**Coverage:** 17/17 FRs + 9/9 NFRs + 10/10 in-scope Decisions mapped 1:1 to the 17 stories below. Story numbering aligns with FR numbering (Story E5.N implements FR-N).

### Epic List

The MVP scope ships as 1 epic (Epic 5), 17 stories spanning four phases:

- **Phase A — Audit (read-only):** E5.1, E5.2, E5.3. Parallelizable, no code changes.
- **Phase C-early — Tooling adoption:** E5.4, E5.5, E5.6. Lands BEFORE Phase B remediation so violations show up in CI during the fix work.
- **Phase C-prevention hook (out-of-band sequencing):** E5.13. Must land BEFORE Phase B baseline regen (E5.11) so regen commits pass through the gate.
- **Phase B — Remediation source changes:** E5.7, E5.8, E5.9, E5.10. Token-class swaps validated by the now-live lint rule.
- **Phase B — Baseline regen + coverage expansion:** E5.11, E5.12. Every PNG goes through the FR13 hook.
- **Phase C-prevention finalization:** E5.14, E5.15, E5.16, E5.17. E5.17 is the closing story (axe `warn` → `fail` promotion).

#### Epic 5: UI Theme Compliance & Visual Regression Hardening

**User outcome:** The operator stops finding light/dark theme defects post-deploy. The visual-regression suite becomes a real quality gate: baselines reviewed by human eye through an enforced sign-off mechanism (git pre-commit hook), color literals banned in UI primitives at lint time, axe contrast violations break the build at Epic close, every new interactive UI primitive ships with open-state coverage in all four projects (desktop/mobile × light/dark) before merge. AI agents (Claude/Codex/Gemini) producing UI commits inherit the same gates automatically — no convention left as the only enforcement layer.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17
**NFRs touched:** NFR1, NFR2, NFR3, NFR4, NFR5, NFR6, NFR7, NFR8, NFR9
**Decisions touched:** A (overlay tokens), B (token-file split), C (in-repo lint first-line + optional plugin), D (Stylelint chain), E (hook-not-convention), F (husky), G (extend hook for coverage contract), H (dedicated axe spec), I (per-test escape hatches), J (Codex prompt artifact + wrapper)
**Dependencies:** E5.4–E5.6 require E5.1; E5.7–E5.10 require E5.4 + E5.5; E5.11 requires E5.13 (hook live) + E5.7–E5.10 (source changes); E5.12 requires E5.3 + E5.13; E5.14 requires E5.13 (extends same hook); E5.17 requires E5.6 + E5.11 + E5.12 (axe baseline must be zero before promotion).

---

### Epic 5: UI Theme Compliance & Visual Regression Hardening

**Goal:** Restate of user outcome above. Three documented incidents (`c35b5dc` light-theme polish, TB-010 viewer3D HSL, AgentsOnboardingDialog 2026-05-13) extinguished by a single BMAD-formal epic; visual-regression process hardened from "passes if it matches the (possibly corrupted) baseline" to "passes the hook + the lint + the axe scan, with every new baseline carrying a human sign-off line in commit history".

**Implementation Status (refreshed 2026-05-15 per Codex implementation-readiness review C1/C2/C3/M1):**

| Story | Status | Commit(s) | Execution divergence from plan |
|---|---|---|---|
| 5.1 — Static color-literal sweep | ✅ done 2026-05-13 | Phase A audit — reports at `_bmad-output/implementation-artifacts/theme-token-violations-2026-05-13.md` + `token-reader-inventory-2026-05-13.md` | Found 11 violations (5 brief-seeded + 3 CardCarousel + 3 ModelGallery NEW); brief assumption (only `readMeshTokens.ts` as non-browser reader) CONFIRMED |
| 5.2 — Baseline integrity audit + skip disposition | ✅ done 2026-05-13 | Phase A audit — report at `baseline-integrity-audit-2026-05-13.md` | 82 PNGs catalogued; 14 baseline-skip count is matrix-expanded from 4 source skip statements (12 of 14 are describe.skip placeholders for unimplemented Slices 3D/3E); 54 of 82 unverified-defer-to-operator per NFR4 batching |
| 5.3 — Interactive-surface coverage matrix | ✅ done 2026-05-13 | Phase A audit — report at `interactive-surface-coverage-matrix-2026-05-13.md` | 25 Radix instances enumerated; 4/25 covered (16%) pre-Epic 5; brief 10-gap list REFUTED-WITH-DIFF (UserMenu already covered; Tooltip misattributed) |
| 5.4 — In-repo ESLint `no-restricted-syntax` rule | ✅ done 2026-05-13 | `5a84f7c` | Shipped at warn level with `--max-warnings=10` accommodating 10 known Phase A violations during Phase B; @poupe plugin enhancement deferred. **Codex M1 (warn-mode-first promotion) resolved by execution path:** lint promoted warn→error in 5.10 closing commit (`4339cfc`) after remediation. |
| 5.5 — Token-file split + Stylelint integration | ✅ done 2026-05-13 | `39eaac3` | viewer-tokens.css extracted; per-file Stylelint color-function-notation overrides (modern for theme.css, legacy for viewer-tokens.css) |
| 5.6 — `@axe-core/playwright` contrast scan at warn | ✅ done 2026-05-13 | `0ce5ac8` | 5 pages × 4 projects = 20 axe scans with `runOnly:['color-contrast']`; per-test exclude policy header with empty exclude-list at MVP |
| 5.7 — Dialog/Overlay tokenization | ✅ done 2026-05-13 | `46bb499` | DialogContent moved to `bg-card text-card-foreground` (semantically correct card surface); plus `.husky/**` added to ESLint ignore. **Codex C1 (red-state-until-5.11) mitigated by execution timeline:** stories 5.7-5.10 + 5.11 all shipped within same autonomous session (~3h elapsed); red-state window minutes, not days. |
| 5.8 — Viewer-overlay tokenization | ✅ done 2026-05-13 | `788223a` | RimOverlay + MeasureOverlay tokenized via new `--color-viewer-tooltip`; Decision A "DOM-rendered exception" — drei `<Html>` is browser-side, so tokens live in theme.css with modern HSL, not viewer-tokens.css |
| 5.9 — Dark-mode override completeness | ✅ done 2026-05-13 | `10821cc` | `.dark` overrides for success/warning/destructive (lightness bumps 45%→55%, 50%→60%, 60%→70%); token-authoring-discipline comment block added |
| 5.10 — Bulk fix remaining Phase A offenders | ✅ done 2026-05-13 | `4339cfc` | New `--color-gallery-control` tokens; CardCarousel × 4 + ModelGallery × 3 violations remediated; lint promotion `--max-warnings=10` → 0 |
| 5.11 — Baseline regeneration with operator sign-off | ✅ done 2026-05-13 | `017cd87` + `fc79d77` (fix-up) | 14 PNGs regenerated (light-mode variants of dialog/sheet/viewer3d-measure-*/viewer3d-modal-*). **Codex C3 (pre-commit can't read COMMIT_EDITMSG) discovered during execution and resolved in same session** — sprint-status verbatim: *"First exercise of FR13 hook — caught real design flaw (pre-commit fires before .git/COMMIT_EDITMSG is current); fix-up in same session made pre-commit warning-only, commit-msg strict."* This split is exactly Codex C3's recommendation. **AUTONOMOUS SIGN-OFF** — operator eye-review of 14 regen + 54 new (Story 5.12) PNGs pending. |
| 5.12 — Open-state spec expansion | ✅ done 2026-05-13 | `1b38bab` (5.12a Selects) + `1477c28` (5.12b destructive dialogs + EditSheets) + `bac71e0` (5.12c admin DropdownMenus + Tooltip) + `e596d97` (5.12d remaining Sheets) | 4 sub-stories per architecture Decision G subdivision pattern; 54 new PNG baselines via subagent execution; RenderSheet success branch deferred (requires mutation-state mocking) |
| 5.13 — Baseline acceptance git hooks | ✅ done 2026-05-13 | `fb8155a` + `13a442d` (fix-up) | Implemented as pre-commit (staged-file checks + warning-only baseline check) + commit-msg (strict `baseline-reviewed:` validation), per Codex C3 split discovered during 5.11 execution. Husky 9 + `git config core.hooksPath apps/web/.husky` (monorepo gotcha) + Docker prepare-script compatibility fix-up |
| 5.14 — Visual Coverage Contract enforcement | ✅ done 2026-05-13 | `fb8155a` (same commit as 5.13) | `_check-visual-coverage.mjs` rejects commits adding `apps/web/src/ui/*.tsx` without matching `apps/web/tests/visual/<basename>.spec.ts` in staged set |
| 5.15 — project-context.md rule additions | ✅ done 2026-05-13 | Operator-local edit (gitignored `_bmad-output/`) | Added "UI quality gates (Initiative 3 / Epic 5)" section; rule_count 134 → 136 |
| 5.16 — Codex review prompt enrichment | ✅ done 2026-05-13 | `a5a83b8` | `.codex/review-prompts/ui-theme-checks.md` + `_tail.md` + `.codex/bin/review-ui-commit`; `.gitignore` updated with negation rules; acceptance test (replay against `10bc3de`) deferred-to-operator |
| 5.17 — Axe contrast scan promotion to `fail` (CLOSING GATE) | ✅ done 2026-05-13 | `a8494b8` | Modified `accessibility-axe.spec.ts` assertion `console.warn` → `expect(violations).toHaveLength(0)`; **zero violations across 20 scans = 5 pages × 4 projects** |
| epic-5-retrospective | ✅ done 2026-05-13 | `_bmad-output/implementation-artifacts/epic-5-retro-2026-05-13.md` (operator-local) | Single-session autonomous execution (~3h elapsed); 15 commits + 4 deploys + 1 fix-up; deferred Decisions K/L/M re-evaluated at retro (all leave-deferred, re-eval 2026-06-13) |

**Codex implementation-readiness Critical findings — all resolved during execution:**

- **C1 (intermediate red visual-regression states):** mitigated by execution timeline. Stories 5.7-5.10 + 5.11 all shipped within ~3h autonomous session; the theoretical multi-day red-state window the plan text allowed never materialized. Lesson codified in Forward-Applicable Principles § 3 below.
- **C2 (forward dependency 5.11/5.12 → 5.13):** mitigated by autonomous executor running stories in dependency order, not numeric order. 5.13 shipped before 5.11/5.12. **Plan text retained for historical fidelity to the planning chain (Phase A → Phase C-early → Phase B → Phase C-prevention).** Lesson codified in Forward-Applicable Principles § 1 below — future initiatives MUST renumber stories to match execution order.
- **C3 (pre-commit + COMMIT_EDITMSG):** discovered + resolved during 5.11 execution. Shipped split implementation (pre-commit warning-only + commit-msg strict) exactly matches Codex's recommendation. Lesson codified in Forward-Applicable Principles § 4 below.

**Codex Major M1 (Story 5.4 warn-mode-first):** resolved in execution path — 5.4 shipped at warn with `--max-warnings=10`, promoted to error in 5.10 closing commit `4339cfc`. Lesson codified in Forward-Applicable Principles § 2 below.

**For future agents reading Epic 5:** treat the Implementation Status table above as authoritative for shipped status, and the story sections below as historical context for HOW each story was scoped before execution.

#### Story 5.1: Static color-literal sweep + token-reader inventory

As an operator scoping Phase B remediation effort,
I want a comprehensive inventory of every hardcoded color literal in `apps/web/src/**` plus every non-browser `--color-*` token reader in the repo,
So that Phase B story granularity (which files get touched, which need new tokens) is data-driven, not guessed.

**Acceptance Criteria:**

**Given** `apps/web/src/` currently contains 5 known violations (`dialog.tsx:34`, `dialog.tsx:56`, `sheet.tsx:29`, `RimOverlay.tsx:8`, `MeasureOverlay.tsx:16`) and the brief's working assumption is `readMeshTokens.ts` + `palette.ts:10` are the only non-browser token readers,
**When** Story 5.1 ships:
- **Output 1: `_bmad-output/implementation-artifacts/theme-token-violations-2026-05-XX.md`** — table with columns `file:line`, `pattern matched`, `current literal value`, `suggested token replacement (if known)`, `severity (P0/P1/P2)`. Grep heuristic: `grep -rEn "(bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\[(#|rgb|hsl|oklch|color\()" apps/web/src/ + grep -rEn "(bg|text|border)-(red|blue|green|zinc|gray|...)-(50|100|200|300|400|500|600|700|800|900|950)" apps/web/src/` (full prefix list per architecture Decision C). Severity P0 = `apps/web/src/ui/**`, P1 = `apps/web/src/modules/**/components/`, P2 = elsewhere.
- **Output 2: `_bmad-output/implementation-artifacts/token-reader-inventory-2026-05-XX.md`** — table with columns `file:line`, `reader pattern`, `tokens consumed`, `parser engine (browser | three.js | other)`. Grep heuristic: `grep -rEn "getPropertyValue\(['\\\"]--color-" apps/web/src/ + grep -rEn "getComputedStyle\(" apps/web/src/ + grep -rEn "new (THREE\\.)?Color\(" apps/web/src/`. The brief's assumption (only `readMeshTokens.ts` + `palette.ts:10`) is verified or refuted in the report's conclusions section.
- **No source changes.** Pure audit story.
**And** both artifacts live in `_bmad-output/implementation-artifacts/` (gitignored per project memory).
**And** the doc-only "commit" is conceptual — `_bmad-output/` is gitignored; the audit reports are operator-local artifacts.

**Dev notes:**
- Run greps from `apps/web/` root for path consistency. `apps/web/src/**` is the scope; `apps/web/tests/` is excluded.
- The prefix list for color-literal grep must match the ESLint rule in Story 5.4 verbatim. Establish the canonical regex here.
- The non-browser-token-reader inventory is the load-bearing assumption check for Decision K (deferred). If 5.1 surfaces ≥1 unexpected reader (e.g., a chart library, an SVG-export pipeline), Decision K's gating condition activates earlier.

#### Story 5.2: Baseline integrity audit + skip disposition

As the operator absorbing the QA load,
I want every existing PNG baseline in `apps/web/tests/visual/__snapshots__/` reviewed at 100% zoom against the human eye, plus a disposition decision for each of the 14 currently-skipped specs,
So that Phase B baseline-regen scope is bounded (only buggy baselines regenerate) and the 14-skip silent hole is closed.

**Acceptance Criteria:**

**Given** `apps/web/tests/visual/__snapshots__/` contains ~82 PNG baselines across 18 spec files × 4 projects (post-`c0daf7a` state: 90 passed / 0 failed / 14 skips), and the brief documents a baseline (`agents-dialog-desktop-light.png`) that visually carries a bug despite the test being green,
**When** Story 5.2 ships:
- **Reviewer-fatigue countermeasure encoded:** operator reviews baselines in batches of ≤20 PNGs per session, ≤2 sessions per day. Total ~82 PNGs ⇒ ~5 sessions over ~3 days. Each session captures its review log inline in the artifact.
- **Output: `_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-XX.md`** — table with columns `baseline relative path`, `project (desktop-light/dark, mobile-light/dark)`, `verdict (OK / buggy / uncertain)`, `defect note (if buggy/uncertain)`, `regen action required (yes/no)`. Plus a section listing each of the 14 currently-skipped specs with disposition `skip→unskip` (and what's needed to make it pass) OR `skip→delete` (and why the spec is no longer relevant). Each entry signed `reviewed: Ezop, <YYYY-MM-DD>`.
- **The known-buggy `agents-dialog-desktop-light.png`** (and its 3 sibling project variants) MUST appear in the "buggy" set; serves as a sanity check that the audit caught at least the documented case.
- **No source changes.** Pure audit story. Regen happens in Story 5.11.
**And** the artifact lives in `_bmad-output/implementation-artifacts/` (gitignored).

**Dev notes:**
- The Playwright HTML report (`npx playwright show-report`) is the recommended viewer; supports 100%-zoom inspection. Alternative: open PNGs directly in the OS image viewer.
- "Uncertain" verdict is allowed when the operator cannot decide without seeing the rendered surface live — escalate to "live check" via `npm run dev` + manual interaction. The artifact records the escalation outcome.
- The 14 skips: read each spec's `.skip(` or `.fixme(` reason; some may be legitimate (e.g., requires backend state) and some may be drift artifacts.

#### Story 5.3: Interactive-surface coverage matrix

As an operator scoping Phase B coverage expansion (Story 5.12),
I want a table cross-referencing every Radix/base-ui interactive primitive instance in the app against the open-state visual-regression specs,
So that the new-spec inventory (which primitives need open-state coverage) is data-driven.

**Acceptance Criteria:**

**Given** ~7 of 18 existing visual specs exercise open interactive surfaces (sessions, catalog-card-carousel, agents-info-dialog, files-tab-admin, viewer3d-measure-plane/pp, viewer3d-modal-open, viewer3d-inline-loaded, viewer3d-mobile) and the brief documents 10 surfaces with zero open-state baseline,
**When** Story 5.3 ships:
- **Output: `_bmad-output/implementation-artifacts/interactive-surface-coverage-matrix-2026-05-XX.md`** — table with rows enumerating every interactive primitive instance in the app (Dialog: AgentsOnboardingDialog, ConfirmDialog, model-detail dialogs; Sheet: EditTagsSheet, EditDescriptionSheet, RenderSheet, AddPrintSheet, AddNoteSheet, mobile filter sheet; Popover/Select: model-form selects, tag picker; Dropdown: UserMenu, model-card admin menu, FilterRibbon; Tooltip: catalog hover tooltips, viewer3d hover tooltips). Columns: `surface`, `open-state spec exists? (yes/no)`, `covered projects (desktop-light/dark, mobile-light/dark)`, `gap notes`.
- **Spec-coverage scoring:** each surface gets a row even if zero specs cover it; gap cells (no spec exists) flagged with `[GAP]` marker. The aggregate "coverage matrix at 100%" criterion in `prd.md` § Initiative 3 § "Success Criteria" reads this artifact at Epic 5 close.
- **Story 5.12 sub-split derivation:** the matrix groups gap surfaces into ~4 bundles (Select dropdowns / ConfirmDialog+EditSheets / Tooltip+UserMenu / RenderSheet+AddPrintSheet+AddNoteSheet+FilterRibbon) for sub-story sequencing.
- **No source changes.** Pure audit story.
**And** the artifact lives in `_bmad-output/implementation-artifacts/` (gitignored).

**Dev notes:**
- Enumerate primitive instances via grep: `grep -rEn "<(Dialog|Sheet|Popover|Select|Dropdown|Tooltip)" apps/web/src/` filtered for the import path (`@/ui/*`) to distinguish project primitives from incidental matches.
- Use the visual specs' filenames as the cross-reference key — primitive name in component matches spec name (`AgentsOnboardingDialog` ↔ `agents-info-dialog.spec.ts`).

#### Story 5.4: In-repo ESLint `no-restricted-syntax` rule

As an agent committing to `apps/web/src/ui/`,
I want `npm run lint --max-warnings=0` to fail when I introduce a hardcoded color literal or a raw Tailwind palette utility,
So that the convention "no inline hex colors anywhere in `.tsx`/`.ts`" (project-context.md) becomes a tooling gate, not a soft norm.

**Acceptance Criteria:**

**Given** `apps/web/eslint.config.js` currently bans `/api/files|catalog/` literals via `no-restricted-syntax` and has no color/theme-token rule,
**When** Story 5.4 ships:
- **New `no-restricted-syntax` entries** in `apps/web/eslint.config.js` per architecture Decision C: pattern (1) matches JSX `className` attribute `Literal` or `TemplateElement` values containing `(bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\\[(#|rgb|hsl|oklch|color\\()` — i.e., color literals in arbitrary brackets; pattern (2) matches raw palette utilities `(bg|text|border)-(red|blue|green|zinc|gray|slate|stone|neutral|amber|yellow|orange|emerald|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)-(50|100|200|300|400|500|600|700|800|900|950)` plus `text-white`, `text-black`, `bg-white`, `bg-black`.
- **Tiered enforcement via `overrides`:** error level on files matching `apps/web/src/ui/**/*.tsx`, warn level on `apps/web/src/**/*.tsx`.
- **Error message** for each pattern points operator at `apps/web/src/styles/theme.css` § `@theme {}` block and at `_bmad-output/project-context.md` § Theme system rule.
- **Optional enhancement layer:** if Phase A's audit (Story 5.1) finds the inventory clean enough to land `@poupe/eslint-plugin-tailwindcss` at `warn` without false-positive flood, add it as a second devDep + a `warn`-level config. Skip if the plugin would generate noise that drowns the actionable signal.
- **Test commit:** deliberately introduce `bg-[rgba(0,0,0,0.5)]` in `apps/web/src/ui/dialog.tsx` (temporary), confirm `npm run lint --max-warnings=0` fails with the expected error message, revert the test commit.
**And** `npm run lint --max-warnings=0` passes on `main` HEAD at the time of Story 5.4 commit (note: the 5 known violations from Phase A are at `error` level under `ui/**` → lint will FAIL until Stories 5.7–5.10 land. Sequence: ship 5.4 with the rule defined but tier-set to `warn` for `ui/**` first; promote to `error` as part of Story 5.10 closing commit. Alternative: ship 5.4 + 5.7 + 5.8 in a coordinated paczka. Decide at sprint planning).
**And** auto-deploy fires (lint-config change is `code`-tier per `feedback_auto_deploy_dev.md`).

**Dev notes:**
- Regex authoring: test the patterns in `eslint-doc-rule-tester` or via `npx eslint --rulesdir` against fixture files BEFORE landing. False positives in `className` (e.g., `bg-[image-url]`) must not fire.
- The optional `@poupe` enhancement layer can ship as a separate follow-up story if its config tuning needs its own focused effort. Story 5.4 scope is bounded by the in-repo rule.

#### Story 5.5: Token-file split + Stylelint integration

As an operator preserving the intentional mixed-notation design between `theme.css` (modern HSL, browser tokens) and three.js-consumed `--color-viewer-*` (legacy comma HSL),
I want the `--color-viewer-*` tokens extracted into `apps/web/src/styles/viewer-tokens.css` and a Stylelint config with per-file `color-function-notation` overrides,
So that the HSL-syntax-mismatch incident class (root cause of TB-010 black-mesh) becomes tooling-defended.

**Acceptance Criteria:**

**Given** `apps/web/src/styles/theme.css` lines 27–37 contain the 4 `--color-viewer-*` tokens (legacy comma HSL) + the 7-line three.js parse-constraint comment block; the file mixes modern HSL (lines 8–26) and legacy HSL (lines 34–37), and no Stylelint is installed,
**When** Story 5.5 ships:
- **Create `apps/web/src/styles/viewer-tokens.css`** containing the 4 `--color-viewer-*` declarations (light theme inside `:root` or `@theme {}`, dark inside `.dark`) + the 7-line comment block. Format: legacy comma HSL throughout.
- **Modify `apps/web/src/styles/theme.css`**: remove the 4 viewer declarations (light + dark); add `@import "./viewer-tokens.css";` after the existing tw-animate-css import. The comment block also moves to `viewer-tokens.css`.
- **New devDeps:** `stylelint@>=16`, `stylelint-config-standard`, `stylelint-color-no-non-variables`.
- **New config `apps/web/.stylelintrc.json`** per architecture Decision D: extends `stylelint-config-standard`; plugin `stylelint-color-no-non-variables`; rules `color-no-hex: true`, `color-no-non-variables/color-no-non-variables: [true, { "ignore": ["named"] }]`; per-file overrides — `theme.css` pins `color-function-notation: "modern"`, `viewer-tokens.css` pins `color-function-notation: "legacy"`.
- **Modify `apps/web/package.json` `lint` script** to `"lint": "eslint . --max-warnings=0 && stylelint \"src/styles/*.css\""`.
- **Smoke test:** introduce `color: #abc` in `viewer-tokens.css` (temporary) → `npm run lint` fails on the Stylelint step. Introduce `hsl(220 9% 60%)` (modern syntax) in `viewer-tokens.css` (temporary) → fails. Revert.
- **Three.js parse compatibility preserved:** `npm run test:visual -- viewer3d` returns clean (mesh still renders correctly with the moved tokens).
**And** auto-deploy fires; `verify-symbolication.sh` still clean.

**Dev notes:**
- The `@import` URL is relative — `./viewer-tokens.css`. Tailwind v4 PostCSS pipeline handles it.
- `palette.ts:10` and `readMeshTokens.ts` are unchanged — `getComputedStyle().getPropertyValue('--color-viewer-mesh-paint')` returns the same value regardless of which CSS file defines it.
- The Stylelint `ignore: ["named"]` exception allows `currentColor`, `transparent`, etc. — these are not the failure mode Initiative 3 targets.

#### Story 5.6: `@axe-core/playwright` contrast scan integration

As an operator and AI agent producing UI changes,
I want a `color-contrast`-only axe scan running across the 4-project Playwright matrix at `warn` level during Phase B,
So that contrast violations surface during remediation work and can be fixed before Story 5.17 promotes the scan to `fail`.

**Acceptance Criteria:**

**Given** `apps/web/tests/visual/playwright.config.ts` runs 4 projects (desktop-light/dark + mobile-light/dark) and no axe integration exists,
**When** Story 5.6 ships:
- **New devDep:** `@axe-core/playwright`.
- **New spec `apps/web/tests/visual/accessibility-axe.spec.ts`** per architecture Decision H: for each of the 4 projects, navigate to a curated page set (`/`, `/catalog`, `/admin/models`, `/admin/tags`, `/admin/categories`, one model-detail page from the seed catalog), run `await new AxeBuilder({ page }).withRules(['color-contrast']).exclude('<known-noisy-selectors>').analyze()`, and at `warn` level: `if (violations.length > 0) { console.warn(violations); }` (do NOT fail the test yet — promotion happens in Story 5.17).
- **Per-test exclude policy header** in the spec file documents the architecture Decision I escape hatch: every `.exclude()` entry MUST have a one-line comment justifying it. Initial exclude-list bounded — only the surfaces the operator KNOWS will false-positive (e.g., disabled controls overlapping z-index in the viewer3d toolbar).
- **Spec runs as part of `npm run test:visual`** alongside existing visual specs (no separate test script needed; existing 4-project sharding picks it up).
- **Smoke test:** run `npm run test:visual -- accessibility-axe` → completes without failure; console output shows the current violation count (the Phase B baseline).
**And** auto-deploy fires; `verify-symbolication.sh` still clean.

**Dev notes:**
- AxeBuilder is project-aware — uses the page's current viewport, locale, and theme automatically. Don't re-set those in the axe call.
- The curated page set should cover both authenticated and public routes; the `accessibility-axe.spec.ts` can use the same auth fixture as other specs (cookie-jar login).
- Expect non-trivial violation count at first run. That's the input for Phase B prioritization, NOT a reason to defer the story.

#### Story 5.7: Dialog/Overlay tokenization + `--color-overlay` token

As the operator who watched `AgentsOnboardingDialog` render as unreadable in light mode,
I want `apps/web/src/ui/dialog.tsx` lines 34 and 56 (DialogOverlay + DialogContent) plus `apps/web/src/ui/sheet.tsx` line 29 (SheetOverlay) tokenized to consume new `--color-overlay` / `--color-overlay-foreground` tokens,
So that every dialog and sheet in the app inherits a working light-mode appearance from `theme.css`.

**Acceptance Criteria:**

**Given** `apps/web/src/ui/dialog.tsx:34` carries `bg-[rgba(0,0,0,0.15)]` (DialogOverlay), `:56` carries `bg-[rgba(8,12,20,0.5)] ... text-foreground` (DialogContent), and `apps/web/src/ui/sheet.tsx:29` carries `bg-[rgba(0,0,0,0.15)]` (SheetOverlay),
**When** Story 5.7 ships:
- **Add 2 new tokens to `apps/web/src/styles/theme.css`** (inside `@theme {}` light + matching `.dark` overrides) per architecture Decision A: `--color-overlay: hsl(222 47% 11% / 0.5);` (light) → `.dark: hsl(0 0% 0% / 0.5);` and `--color-overlay-foreground: hsl(210 40% 98%);` (light) → `.dark: hsl(210 40% 98%);` (essentially same — overlay foreground is bright in both themes). Token values may be tuned post-implementation if visual review (Story 5.11 regen sign-off) reveals a need.
- **Modify `apps/web/src/ui/dialog.tsx:34`** (DialogOverlay): replace `bg-[rgba(0,0,0,0.15)]` with `bg-overlay/30` (light dialog gets bg-overlay-color at 30% opacity for the backdrop layer). Test value during implementation — `/30`, `/40`, `/20` all candidates; pick visually clean.
- **Modify `apps/web/src/ui/dialog.tsx:56`** (DialogContent): replace `bg-[rgba(8,12,20,0.5)] ... text-foreground` with `bg-card text-card-foreground` (the dialog content surface is a card-level surface — `bg-card` is semantically correct; the translucency at 50% in the original is wrong for light mode anyway). Verify visually that DialogContent against the now-properly-translucent DialogOverlay reads correctly in both themes.
- **Modify `apps/web/src/ui/sheet.tsx:29`** (SheetOverlay): replace `bg-[rgba(0,0,0,0.15)]` with `bg-overlay/30` (same as DialogOverlay — symmetric fix).
- **ESLint rule from Story 5.4 reports zero violations on these three files** post-change.
- **Baseline regen for affected snapshots** is OUT of scope for this story (Story 5.11 handles it). The visual-regression suite will FAIL on `agents-info-dialog.spec.ts` and any other dialog/sheet specs until 5.11 regenerates; that's expected.
**And** auto-deploy fires; `verify-symbolication.sh` still clean.

**Dev notes:**
- The token-value tuning is the visually-tricky part. Use the Playwright HTML report's full-page screenshot to compare light vs dark; the goal is "dialog content reads clearly in both themes against the backdrop".
- `bg-card text-card-foreground` was the v1-brief's first instinct for DialogContent; if visual tuning reveals a card surface is too high-contrast, fall back to `bg-overlay text-overlay-foreground` (then the overlay token is the content surface, and a separate `bg-overlay-backdrop` for the OverlayBackdrop layer — but that's a 3-token spread, prefer the 2-token solution if possible).

#### Story 5.8: Viewer-overlay tokenization + `--color-viewer-tooltip` token

As the operator preserving viewer3D contrast,
I want `RimOverlay.tsx:8` and `MeasureOverlay.tsx:16` tokenized to consume a new `--color-viewer-tooltip` token (legacy HSL, in `viewer-tokens.css`),
So that over-canvas tooltips inherit theme-correct contrast.

**Acceptance Criteria:**

**Given** `apps/web/src/modules/catalog/components/viewer3d/measure/RimOverlay.tsx:8` and `MeasureOverlay.tsx:16` both use `bg-zinc-900/95 text-white ring-white/15` raw palette utilities,
**When** Story 5.8 ships:
- **Add 1 new token to `apps/web/src/styles/viewer-tokens.css`** per architecture Decision A (in viewer file because the overlays render over the WebGL canvas; though they're not consumed by three.js Color, locating viewer-surface tokens together is a coherence argument; if Phase A audit reveals these are browser-rendered DOM and have no three.js consumer, they may instead live in `theme.css` as `--color-viewer-tooltip` — decide during implementation, default to viewer-tokens.css). Token: `--color-viewer-tooltip: hsl(222, 47%, 9%);` (light → readable on bright canvas) → `.dark: hsl(220, 14%, 16%);` (still dark — viewer3D canvas is dark in both themes per design). Plus a foreground variant if contrast requires.
- **Modify both files** to use token classes instead of raw palette: `bg-zinc-900/95 text-white ring-white/15` → `bg-viewer-tooltip/95 text-viewer-tooltip-foreground ring-viewer-tooltip-foreground/15` (or simpler combination if foreground variant not needed — choose minimal token surface).
- **ESLint rule from Story 5.4 reports zero violations on these two files** post-change.
- **Stylelint passes** on `viewer-tokens.css` with the new token in legacy comma HSL (`hsl(H, S%, L%)`).
- **Visual regression on viewer3d specs** is expected to FAIL until Story 5.11 regenerates (over-canvas tooltips appear in `viewer3d-measure-pp.spec.ts` and `viewer3d-measure-plane.spec.ts`).
**And** auto-deploy fires; `verify-symbolication.sh` still clean.

**Dev notes:**
- The "where does this token live" decision (Decision A vs Decision B) hinges on whether `RimOverlay` / `MeasureOverlay` are pure DOM (in which case `theme.css`) or three.js-attached (in which case `viewer-tokens.css`). Read the component source: if they render via `<div>` in React, theme.css; if via `<Html>` from drei or three.js sprite, viewer-tokens.css. Default to viewer-tokens.css for coherence with the surrounding viewer surface.

#### Story 5.9: Dark-mode override completeness

As an operator preventing latent dark-mode contrast risk,
I want `.dark {}` overrides added to `theme.css` for the 3 tokens currently inheriting their light values (`--color-success`, `--color-warning`, `--color-destructive`) plus any other gaps surfaced by Phase A audit (Story 5.1),
So that every `--color-*` token has a deliberate value in both themes.

**Acceptance Criteria:**

**Given** `apps/web/src/styles/theme.css` `.dark {}` block currently overrides 16 of 19 base tokens — missing `--color-success`, `--color-warning`, `--color-destructive` (and possibly others surfaced by 5.1 audit),
**When** Story 5.9 ships:
- **Add `.dark` overrides** for each missing token. Initial values: `--color-success: hsl(142 71% 55%);` (slightly brighter green for dark bg readability), `--color-warning: hsl(38 92% 55%);`, `--color-destructive: hsl(0 84% 65%);`. Tune to satisfy WCAG AA contrast against `--color-background` dark value.
- **Add a `theme.css` block comment** noting that every `--color-*` in `@theme {}` MUST have a matching `.dark` declaration; future violations are caught at code review (no mechanical lint rule for this; deferred).
- **Verify visually** by toggling theme on a page that uses these tokens (admin/models for status badges, model-card for destructive-action buttons, etc.).
**And** auto-deploy fires; visual-regression may show changes on dark-theme baselines that exercise success/warning/destructive — Story 5.11 handles regen.

**Dev notes:**
- Use the existing axe contrast scan from Story 5.6 (now live at `warn` level) to verify new dark-mode values: re-run the scan post-change and confirm no new contrast violations appear on the affected surfaces.
- The Phase A audit (5.1) may surface additional `.dark` gaps if any `--color-*` token has been added since the brief was written — sweep includes a check.

#### Story 5.10: Bulk fix remaining Phase A offenders

As an operator ensuring zero hardcoded color literals in `apps/web/src/ui/**`,
I want every file flagged P0 (in `ui/**`) and P1 (in `modules/**/components/`) by Story 5.1 audit tokenized,
So that the ESLint rule from Story 5.4 can be promoted from `warn` to `error` for `apps/web/src/**` (not just `ui/**`).

**Acceptance Criteria:**

**Given** Story 5.1 produced a severity-ranked offender list, and Stories 5.7 + 5.8 addressed the P0+P1 violations on dialog/sheet/viewer-overlays,
**When** Story 5.10 ships:
- **Iterate the P1 list from Story 5.1.** For each file: replace hardcoded color literal with the suggested token (from 5.1 column) OR add a new `--color-*` token to `theme.css` if no suitable existing token covers the semantic. New tokens follow Decision A pattern (light + dark declarations together).
- **For P2 entries (outside `ui/` and `modules/**/components/`):** the lint rule stays at `warn` post-Epic-5; remediation is opt-in via follow-up. Phase A 5.1 documents per-entry whether the P2 entry is worth touching now (incremental fix bundled here) or deferred.
- **ESLint rule from Story 5.4 promoted to `error` for `apps/web/src/**` (full src tree).** This is the closing commit of remediation: `npm run lint --max-warnings=0` passes on all of `apps/web/src/`.
- **Stylelint passes** on all theme + viewer-token files.
**And** auto-deploy fires; visual-regression on the touched specs may FAIL pending Story 5.11 regen.

**Dev notes:**
- This story's effort is proportional to what 5.1 surfaces. Brief's working assumption is ~5 sites total (3 in `ui/` + 2 in viewer-overlays). If 5.1 surfaces 10+ additional, sprint planner may split 5.10 into per-bundle sub-stories.
- Avoid scope-creep into non-flagged files. The point of 5.1 is to bound this scope.

#### Story 5.11: Baseline regeneration with operator sign-off

As the operator restoring the visual-regression suite to a known-good state,
I want every PNG affected by Stories 5.7–5.10 regenerated via `--update-snapshots` AND each regenerated PNG sign-off recorded in the commit message,
So that Phase B closes with a clean baseline set + auditable sign-off trail.

**Acceptance Criteria:**

**Given** Story 5.13 has shipped the FR13 git pre-commit hook BEFORE this story runs, and Stories 5.7–5.10 have landed source changes that invalidate some existing baselines,
**When** Story 5.11 ships:
- **Identify affected baselines:** run `npm run test:visual` post-Stories-5.7–5.10; collect every test that FAILS with `Screenshot does not match` (these are the baselines invalidated by source changes).
- **For each failing spec, regenerate** via `npx playwright test --update-snapshots --grep <spec-name>`. Run per-project regen separately if needed to control sign-off batching.
- **Visual review of every regenerated PNG** at 100% zoom in the Playwright HTML report. Reviewer-fatigue countermeasure: ≤20 PNGs per session, ≤2 sessions per day (same protocol as Story 5.2).
- **Commit message format per FR13 hook:**
  ```
  fix(web): regenerate baselines post-overlay-tokenization (E5.11)

  baseline-reviewed: agents-dialog-desktop-light.png, Ezop, 2026-05-XX
  baseline-reviewed: agents-dialog-desktop-dark.png, Ezop, 2026-05-XX
  baseline-reviewed: agents-dialog-mobile-light.png, Ezop, 2026-05-XX
  baseline-reviewed: agents-dialog-mobile-dark.png, Ezop, 2026-05-XX
  baseline-reviewed: sheet-overlay-...  (continued for every PNG)
  ```
- **Pre-commit hook validates** that every changed PNG basename has a matching `baseline-reviewed:` line. Hook rejects if any are missing.
- **Post-commit:** `npm run test:visual` returns clean (90 → updated total passed / 0 failed / 14 skips OR fewer skips per Story 5.2's disposition decisions).
**And** auto-deploy fires; `verify-symbolication.sh` still clean.

**Dev notes:**
- The PNG count is bounded by Stories 5.7–5.10 surface. Brief estimate: ~20–30 PNGs across the affected specs × 4 projects.
- If a regen produces a visually wrong PNG (e.g., the dialog still looks broken because the token value picked in 5.7 was wrong), the workflow is: revert the regen commit, fix the token value via a Story-5.7-amendment commit, re-run regen, re-review.
- The first time a `baseline-reviewed:` line appears in `git log --grep='baseline-reviewed:'` is here — this story is also the first-pass test of the FR13 hook.

#### Story 5.12: Open-state spec expansion

As an agent producing UI changes,
I want open-state Playwright specs for every interactive primitive currently uncovered by visual-regression,
So that the next defect class to hit the surface gets caught BEFORE production-equivalent.

**Acceptance Criteria:**

**Given** Story 5.3 produced an interactive-surface coverage matrix with ~10 surfaces flagged `[GAP]` and Story 5.13 (hook) is live,
**When** Story 5.12 ships:
- **Sub-split per primitive bundle** (per architecture Decision G and brief's effort-balloon countermeasure):
  - **5.12a Select dropdowns:** open-state spec for the model-form select + tag picker.
  - **5.12b ConfirmDialog + EditTagsSheet + EditDescriptionSheet:** triggered open via fixture interactions.
  - **5.12c Tooltip + UserMenu:** UserMenu open-state covers the admin-onboarding dialog trigger; Tooltip on catalog cards covers the hover state.
  - **5.12d Remaining: RenderSheet, AddPrintSheet, AddNoteSheet, FilterRibbon TagPicker (mobile sheet).**
- **Each sub-story:** writes a new `apps/web/tests/visual/<primitive>-open.spec.ts` (or extends an existing related spec); triggers the open state via Playwright fixture interactions; runs across all 4 projects (the existing project sharding picks it up automatically); captures the PNG baselines; goes through the FR13 hook sign-off process.
- **Selectors are PL-locale-aware** per the TB-009 selector-fix policy (commented in spec headers; one-line locale-dependency note). EN-only regex selectors caught here — sprint planner may surface a follow-up if Phase A 5.3 finds ≥3 such cases worth a lint rule (architecture Decision M gating condition).
- **Aggregate effect:** the FR3 coverage matrix re-runs at 100% green after all 4 sub-stories complete.
**And** auto-deploy fires per sub-story.

**Dev notes:**
- The 4 sub-stories are NOT a hard split — sprint planner may merge them if scope under-runs OR further-split if scope over-runs. They are independently shippable.
- Fixture pattern: use the existing `apps/web/tests/visual/helpers.ts` for common open-state interaction patterns; extend it as new interactions emerge.

#### Story 5.13: Baseline acceptance git pre-commit hook

As an operator preventing convention-only enforcement (per architecture Decision E),
I want a git pre-commit hook that parses commit messages and rejects baseline-touching commits without `baseline-reviewed:` lines,
So that the Baseline Acceptance Gate is a contract, not a soft norm.

**Acceptance Criteria:**

**Given** `apps/web/` has no husky / lint-staged / pre-commit hook configured today,
**When** Story 5.13 ships:
- **Adopt husky ≥9** per architecture Decision F: new devDep, `npx husky init` (or equivalent flat config); `package.json` `prepare` script set to `"prepare": "husky"`.
- **New `apps/web/.husky/pre-commit`** shell wrapper that runs the FR13 + FR14 checks (FR14 lands in Story 5.14):
  ```sh
  #!/bin/sh
  node "${0%/*}/_check-baseline-review.mjs" || exit 1
  # FR14 invocation slot — added by Story 5.14
  ```
- **New `apps/web/.husky/_check-baseline-review.mjs`** Node helper per architecture Decision E: collects staged PNGs via `git diff --cached --name-only --diff-filter=AM | grep "apps/web/tests/visual/__snapshots__/.*\.png$"`; if zero matches, exit 0; if matches present, read `.git/COMMIT_EDITMSG`; for each PNG basename, require a line `^baseline-reviewed: <basename>, .+, \d{4}-\d{2}-\d{2}$`; reject with a clear error pointing at the missing basename(s).
- **`prepare` script wires hooks on first `npm install`.** Run `npm install` post-Story-5.13 ship to install the hook locally.
- **Test:** stage a fake `apps/web/tests/visual/__snapshots__/test.png` (touch+stage), commit without sign-off line → hook rejects. Commit with sign-off → hook accepts. Revert the test.
**And** auto-deploy fires; the husky `prepare` script runs on the production deploy host's `npm install` (post-PR-merge build), wiring the hook there too — but the dev-host `.190` deploy doesn't run `git commit`, so the hook is operator-local-machine-only by execution surface.

**Dev notes:**
- Husky 9's flat-config flow is `npx husky init` → creates `.husky/pre-commit` placeholder → operator edits the script. The legacy `husky add` style is deprecated.
- The Node helper runs sync via `node` (top-level await OK in modern Node). Keep it dependency-free (no devDeps imported); only `node:fs`, `node:child_process`.

#### Story 5.14: Visual Coverage Contract enforcement (FR14)

As an operator enforcing the "every new interactive primitive ships with open-state coverage" rule,
I want the FR13 hook extended to reject commits adding new `apps/web/src/ui/*.tsx` without a matching visual spec,
So that the Visual Coverage Contract is a commit-time gate.

**Acceptance Criteria:**

**Given** Story 5.13 has shipped the hook and its Node helpers slot,
**When** Story 5.14 ships:
- **New `apps/web/.husky/_check-visual-coverage.mjs`** Node helper per architecture Decision G: collects staged ADDED (`-diff-filter=A`) files matching `apps/web/src/ui/*.tsx`; for each `<basename>.tsx`, require a corresponding staged file matching `apps/web/tests/visual/<basename>.spec.ts` OR `apps/web/tests/visual/<basename>-*.spec.ts`; reject with a clear error otherwise.
- **`apps/web/.husky/pre-commit`** wraps the second helper invocation:
  ```sh
  node "${0%/*}/_check-baseline-review.mjs" || exit 1
  node "${0%/*}/_check-visual-coverage.mjs" || exit 1
  ```
- **Test:** stage a fake `apps/web/src/ui/new-primitive.tsx`, commit → hook rejects with "missing visual spec". Add `apps/web/tests/visual/new-primitive.spec.ts` to the staged set, commit → hook accepts. Revert.
**And** auto-deploy fires.

**Dev notes:**
- The "matching spec" check is filename-pattern-based, not content-based. If a future need emerges to verify the spec actually opens the primitive (not just shares a name), that's a follow-up.
- Edge case: if a primitive is added but spec already exists in main (pre-existing), the staged set will lack the spec. Decide: either require the spec to be in the staged set (strictest, may force re-touching the spec to bump a timestamp) OR check both staged + working-tree (more ergonomic, weaker contract). Default to working-tree-aware check; tighten if bypass incidents occur.

#### Story 5.15: `project-context.md` rule additions

As an operator codifying the two new procedural contracts,
I want `_bmad-output/project-context.md` extended with "Baseline Acceptance Gate" and "Visual Coverage Contract" rules,
So that future agents reading the project-context find the rules + their tooling counterparts together.

**Acceptance Criteria:**

**Given** `_bmad-output/project-context.md` frontmatter `rule_count: 134`,
**When** Story 5.15 ships:
- **Add 2 new rules** under a new or existing relevant section (Observability or new "UI Quality Gates"):
  - **Rule N (Baseline Acceptance Gate):** "Any commit touching `apps/web/tests/visual/__snapshots__/**/*.png` MUST include a `baseline-reviewed: <basename>, <reviewer>, <YYYY-MM-DD>` line per changed PNG. Enforced by `apps/web/.husky/pre-commit` via `_check-baseline-review.mjs` (FR13 / Story 5.13). The hook rejects commits missing any line. Convention without tooling is rejected — see Initiative 3 retrospective + 2026-05-10 UI-review retro."
  - **Rule N+1 (Visual Coverage Contract):** "Any commit adding a new `apps/web/src/ui/*.tsx` MUST also stage a matching `apps/web/tests/visual/<basename>.spec.ts` (or `<basename>-*.spec.ts`) exercising the open state. Enforced by `apps/web/.husky/pre-commit` via `_check-visual-coverage.mjs` (FR14 / Story 5.14)."
- **Update frontmatter `rule_count: 134` → `136`.**
- **Update `last_updated: <today>`.**
- **Doc-only commit** — auto-deploy skipped per `feedback_auto_deploy_dev.md`.

**Dev notes:**
- Rule numbering follows the existing format in the file (look at existing rules for the pattern; typically inline narrative, not numeric-indexed).
- Keep prose tight — match the existing rule density. The rules are pointers to the tooling, not the tooling-mechanism description (that lives in architecture).

#### Story 5.16: Codex review prompt enrichment

As an operator wanting Codex to catch UI-class defects at PR review time,
I want a concrete prompt artifact at `.codex/review-prompts/ui-theme-checks.md` plus a wrapper script invoking it for UI commits,
So that the cross-LLM review surface includes theme/visual checks deterministically.

**Acceptance Criteria:**

**Given** Codex review is invoked today as `codex review --commit <SHA>` with no pluggable prompt template,
**When** Story 5.16 ships:
- **Create `.codex/review-prompts/ui-theme-checks.md`** per architecture Decision J — a prompt fragment instructing Codex to check:
  - (a) Color literals in `apps/web/src/ui/**` per the regex used in Story 5.4's ESLint rule.
  - (b) `.dark {}` override completeness — any new `--color-*` in `@theme {}` must have matching `.dark` declaration.
  - (c) Open-state visual spec coverage — any new `apps/web/src/ui/*.tsx` must have matching `apps/web/tests/visual/<basename>.spec.ts`.
  - (d) Selector locale-awareness — any new `apps/web/tests/visual/*.spec.ts` `getByRole({ name: ... })` regex must match PL strings (the locale forced by `playwright.config.ts`).
- **Create `.codex/review-prompts/_tail.md`** — shared trailing context: pointers to `_bmad-output/project-context.md`, `prd.md` § Initiative 3, instructions to surface findings as P0/P1/P2/P3 per existing project convention.
- **Create `.codex/bin/review-ui-commit`** executable shell wrapper per architecture Decision J: detects UI commits via `git diff --name-only HEAD~1..HEAD | grep -E "^apps/web/(src/(ui|styles|modules/.*/components)|tests/visual)/" -q`; if matched, runs `cat .codex/review-prompts/ui-theme-checks.md .codex/review-prompts/_tail.md | codex exec -`; if not matched, runs bare `codex review --commit "$1"`.
- **Acceptance test:** replay against historical commit `10bc3de` (TB-010 partial — baked black-mesh + summary-overlap into 14 baselines). The enriched prompt MUST surface at least one of those defects. Capture the Codex output transcript inline in the story or as `_bmad-output/implementation-artifacts/codex-prompt-validation-2026-05-XX.md`.
**And** the commit is `code`-tier — auto-deploy fires (lint/test/build unaffected, but the `.codex/` directory is shipped to the repo).

**Dev notes:**
- The wrapper script does not need to be perfect — false positives (running enriched prompt on a non-UI commit) cost ~1k Codex tokens; false negatives (missing a UI commit) miss the value but don't break anything.
- The acceptance test (replay against `10bc3de`) is the proof-point. If the enriched prompt does NOT surface a TB-010 defect, the prompt needs strengthening — iterate before considering the story done.

#### Story 5.17: Axe contrast scan promotion to `fail`

As the closing story of Epic 5,
I want the `@axe-core/playwright` scan from Story 5.6 promoted from `warn` to `fail` level,
So that contrast violations block CI / auto-deploy going forward — the Visual Regression suite is now a real quality gate.

**Acceptance Criteria:**

**Given** Stories 5.6 (axe at warn) + 5.7–5.10 (remediation) + 5.11 (regen) + 5.12 (coverage expansion) all shipped, and the current axe-scan output shows zero `color-contrast` violations across all 4 projects (verify by running `npm run test:visual -- accessibility-axe` and inspecting the console output),
**When** Story 5.17 ships:
- **Modify `apps/web/tests/visual/accessibility-axe.spec.ts`** — change the assertion from `console.warn` to `expect(violations).toHaveLength(0)`.
- **Acceptance gate:** `npm run test:visual -- accessibility-axe` returns clean across all 4 projects. If any violation surfaces, the story does NOT close — instead, the violation is either remediated (one more remediation story) OR added to the per-test exclude-list (architecture Decision I) with a one-line justification.
- **Smoke test:** deliberately introduce a low-contrast element (e.g., `<div className="text-muted-foreground" style={{ background: 'rgba(0,0,0,0.5)' }}>test</div>`) somewhere on `/admin/models`, run `npm run test:visual -- accessibility-axe` → test FAILS. Revert.
- **Epic 5 close gate:** with this story shipped, Epic 5 is complete. Trigger Epic 5 retrospective story `epic-5-retrospective`.
**And** auto-deploy fires; the promoted gate is now part of the `npm run test:visual` contract on every UI commit going forward.

**Dev notes:**
- The exclude-list discipline (per architecture Decision I) is what prevents this story from being unable-to-close. Pragmatic exclude-list with explicit justification per entry is the right balance for solo-operator throughput; "zero violations and zero excludes" is the aspirational goal but not a hard close criterion.
- Post-Epic-5 retro should re-evaluate the exclude-list for any entries that can be remediated rather than kept excluded.

---

## Forward-Applicable Principles (from Codex implementation-readiness 2026-05-15)

This section captures lessons surfaced by the 2026-05-15 Codex review that future initiatives MUST apply. Distinct from per-epic Implementation Status tables above (which describe how E4/E5 navigated specific findings in execution), these are project-wide standards that apply to ALL future initiatives planned in this ledger.

### Principle 1 — Story numbering MUST match execution order (no forward dependencies)

When designing a new initiative's story breakdown: if Story X depends on Story Y, Y MUST have a lower number than X. A future agent executing strictly by story number cannot hit a blocked prerequisite.

**Counter-example to avoid:** E5 originally had Story 5.11 depending on Story 5.13 (hook before regen). The autonomous executor navigated this by ordering stories by dependency, but a less-context-aware agent would have stalled at 5.11. Plan text retained for historical fidelity to the planning chain (Phase A → C-early → B → C-prevention); **new initiatives must renumber to avoid the same trap**.

**Practical guidance:** during `bmad-create-epics-and-stories`, sequence numbering AFTER drawing the dependency graph, not before. If phase-based naming (Phase A / B / C) helps organize the plan, keep it in section headers but flatten the numeric order to be execution-safe.

### Principle 2 — Lint-rule introductions are warn-mode-first

Introducing a new ESLint/Stylelint/etc. rule requires the rule to land at `warn` level first, NOT `error`. The promotion to `error` is scheduled as a closing story AFTER all known violations are remediated.

This avoids the contradictory-AC trap: "rule catches current violations" + "lint passes on main" cannot both be true at error level until remediation lands.

**Pattern:** Story N introduces rule at warn (or `--max-warnings=<known-count>`); Stories N+1..N+k remediate; Story N+m promotes warn → error (or `--max-warnings=0`).

**Reference implementation:** E5 lint rule sequence (5.4 warn at `--max-warnings=10` → 5.10 promote at closing commit `4339cfc`).

### Principle 3 — UI changes ship with own baseline updates, not deferred regen

Stories that change UI source MUST regenerate own affected visual-regression baselines in the same story (same commit if possible, or back-to-back commits in same autonomous session). Deferring baseline regen to a separate "final regen" story creates a window where `main` carries a known-red visual-regression state.

**Acceptable execution patterns:**

- (a) Each remediation story regenerates own baselines in its own commit (preferred for new initiatives).
- (b) Remediation chain + baseline regen execute end-to-end within a single autonomous session, keeping the red-state window to minutes (E5's actual execution pattern; acceptable for autonomous-only sessions).

**Unacceptable:** human-paced multi-day execution with red-state baselines on main between remediation and regen.

**Note:** this overlaps with project-context.md rule "UI changes require visual-regression verification before completion". This Principle is the planning-document corollary — it constrains how UI initiatives are STRUCTURED, not just executed.

### Principle 4 — Commit-message validation lives in `commit-msg`, not `pre-commit`

Git `pre-commit` runs BEFORE the commit message is finalized; `.git/COMMIT_EDITMSG` may not contain the user's message yet. Commit-message validation (e.g., required `baseline-reviewed:` lines, conventional-commit format) MUST run in `commit-msg`.

`pre-commit` is correctly used for staged-file checks (lint, format, file-presence rules).

**Reference implementation:** E5 hook split (`apps/web/.husky/pre-commit` for staged-file checks + warning-only baseline check; `apps/web/.husky/commit-msg` for strict `baseline-reviewed:` validation). Discovered during 5.11 execution + shipped in `13a442d` fix-up.

### Principle 5 — Brownfield initiatives MUST refresh planning artifacts after execution

When an initiative ships end-to-end (especially autonomously), the planning artifacts (`epics.md` story descriptions) MUST be updated to reflect shipped reality:

- Per-story `**Status:** ✅ shipped (commit `<sha>`, <date>)` lines, OR an "Implementation Status (refreshed <date>)" table at top of the Epic section (the pattern adopted for E4/E5 in the 2026-05-15 refresh).
- Execution-divergence notes where implementation departed from plan (e.g., E5.11's hook design discovery, E4.2's nginx config archival).
- Cross-references to retrospective if one exists.

Without this, future agents reading `epics.md` cannot tell forward-looking work from historical record, and reviewers like Codex flag shipped work as "not ready" (see the 2026-05-15 Codex review as the canonical example — 3 critical + 4 major findings, of which all but M4 were artifacts of plan-vs-reality drift, not real defects).

**Practical guidance:** add this refresh as a step in the epic retrospective workflow. Sprint-status.yaml carries the per-story status as machine-readable data; epics.md needs the same data in narrative form for human + AI-agent readers who don't cross-reference YAML.

### Principle 6 — E0 (retrospective foundation) intentionally relaxes epic-quality standards; do NOT pattern-copy

E0.1 Repo Bootstrap, E0.2 Data Plane, E0.9 Infra are technical-by-nature and acceptable only as a retroactive ledger of pre-BMAD work. **Forward-looking initiatives MUST follow normal "epics deliver user value" standards.** See § Initiative 0 § Overview for the explicit annotation that surfaces this constraint at the source.

**Anti-pattern to watch for:** a new initiative epic titled "Repo refactor", "Migration cleanup", "Data plane evolution" without clear user value framing. Such epics ARE valid for technical debt or infrastructure work, but their AC and Goal sections must articulate the downstream user value the technical work unblocks. E0's epics intentionally lack this framing because they are retroactive, not because technical-debt-without-user-framing is a green-field-acceptable pattern.

---

## Initiative 5 — Public Registration & User Account Management

**Status:** 🚧 planning (started 2026-05-18). Maintainer: Ezop. Source brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (v2, 213 lines, adversarial review applied: P0×2 + P1×3 + P2×1 fixed) + distillate sibling (~5688 tokens, LLM-optimized). Source CC proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Source PRD section: `prd.md` § "Initiative 5" (lines 1065-1258 — 24 FRs across 8 prefix groups + 12 NFRs across 6 categories). Source architecture section: `architecture.md` § "Initiative 5" (lines 1399-1767 — Decisions A–K in-scope; L–N deferred). Sequenced into five epics: **E6** (Member role + invite-based registration) → **E7** (TOTP 2FA + recovery codes) → **E8** (Admin panel: users + invites) → **E9** (Security audit — **HARD GATE** blocking E10) → **E10** (Edge cutover — atomic).

**Brief working-label mapping.** The source brief uses dotted notation `5.1`–`5.5` as working labels. These map 1:1 onto project-global epic IDs per CC §3.4 vanilla-alignment correction (vanilla `epics-template.md` `{{N}}` unique-in-file constraint preserved via project-global numbering, continuing E1–E3 / E4 / E5 from Init 1/2/3): brief `5.1` → **E6**, `5.2` → **E7**, `5.3` → **E8**, `5.4` → **E9**, `5.5` → **E10**. Story IDs follow `<global-epic-id>.<local-story-num>` (e.g. `Story 6.1`, `7.3`, `10.2`). The dotted brief labels are PRD-time historical artifacts; from this section forward only the global IDs are used.

**Init 0 + Init 2 are unchanged.** Initiative 5 is purely additive on the brownfield base. The Init 0 cookie+JWT auth stack stays exactly as it ships (`portal_access` 10min + `portal_refresh` 30d family rotation, CSRF via `X-Portal-Client: web`). The Init 0 share-token Redis pattern stays as the template for invite tokens (Decision A mirrors `apps/api/app/modules/share/service.py` deliberately). The Init 0 audit-log surface gains 16 new action names (enumerated in FR5-AUDIT-1) but no contract changes — same `record_event()` helper, same `KNOWN_ENTITY_TYPES` registry, same `/api/admin/audit` query path. The `agent` service account (Init 2) is preserved exactly: cookie+password flow unchanged, no 2FA forced ever (FR5-2FA-3 fail-fast startup check on `Role.agent in enforce_2fa_for_roles`), `/agent-runbook` nginx bypass preserved across the Epic 10 cutover (NFR5-INT-1 + Decision K). The `admin` role is preserved exactly — `current_admin` stays admin-only.

**Header levels** per CC §3.4 (deeper nesting than Init 1/2/3 to encapsulate five epics under a single initiative): `## Initiative 5` (H2) → `### Overview / Requirements Inventory / Epic List / Cross-references` (H3) → `#### Epic N` (H4) → `##### Story N.M` (H5).

### Overview

3d-portal today admits exactly two principals: `admin` (Michał) and `agent` (the AI service account). Catalog browse is gated at the nginx edge via IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`, covering homelab LAN + VPN); there is no per-person login path for friends-and-family. The `member` role is already enumerated in `apps/api/app/core/db/models/_enums.py` (Init 0 baseline) but is unreachable — no registration flow, no admin UI for invite issuance, no 2FA infrastructure, and the network perimeter is still load-bearing for trust.

Initiative 5 closes that gap in five sequenced epics. **E6** wires the core flow: admin generates a single-use invite link with operator-chosen TTL and pre-bound role, recipient lands on `/register?token=<token>`, supplies email + password (zxcvbn ≥3 ≥12-char gate), and the resulting `member` account gains catalog browse + 3D viewer + share-link generation via the share-router auth expansion. E6 also ships the cross-cutting rate-limit middleware (Redis sliding-window over sorted set) for `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`, and the per-member share-token cap. **E7** adds optional second-factor TOTP with mandatory eight single-use recovery codes; enforcement is per-role via `enforce_2fa_for_roles: list[Role]` with the `agent` role explicitly excluded by fail-fast startup validation. E7 closes with an end-to-end recovery-code drill against `.190` captured as `2fa-recovery-drill-YYYY-MM-DD.md`. **E8** ships two new admin tabs (`/admin/users`, `/admin/invites`) on the existing admin module, soft-delete + `last_active_at` infrastructure with Redis `SET NX EX 300` write throttle, per-user actions (change role, deactivate / reactivate, force logout-all-sessions, force-2FA-enrollment, issue password reset), and the invite list/revoke surface. **E9** is the **HARD GATE** before E10 — formal pre-cutover audit with `bandit` + `semgrep` + `pip-audit` + `npm audit`/`osv-scanner` + OWASP ZAP active scan + `codex review` countersignature for each Medium disposition. Gate condition (NFR5-SEC-1): zero open Critical/High findings; at most three "accepted-with-rationale" Medium findings (the fourth forces auto-fail and triggers a fix sprint). **E10** is the atomic single-commit nginx edit in the sibling configs repo dropping both `auth_basic` and the IP allowlist, plus a four-scenario post-reload smoke matrix and a verified rollback drill before close-out.

The work is bounded. The cutover itself is the smallest change in the initiative — drop two nginx directives. The bulk of the effort is the audit that lets the portal trust the cutover, not the cutover itself. Each Story below cites one or more concrete FR5-* / NFR5-* requirement IDs from `prd.md` § Initiative 5 and one or more architecture Decision letters (A–K) from `architecture.md` § Initiative 5 as the binding architectural anchor. Granular per-step acceptance criteria (Given/When/Then prose) are deferred to `bmad-create-story` skill at story-execution time (Sesja G+ per CC §4.3); this section's acceptance bullets are the high-level capability checks per story, sufficient for sprint-planning intake.

**Out-of-scope reminders carried from brief Q5 + PRD § "Out" + architecture Decisions L–N (deferred):** no social login, no OIDC/SSO federation, no per-model ACL, no team/group accounts, no user-to-user messaging, no public read-only browse mode, no self-service mail-based password reset (blocked on self-hosted mail server initiative), no email deliverability verification (RFC format only), no webhook push to external systems, no multi-tenant. Admin-issued password reset link (FR5-ADMIN-3) is the only reset path in v1; delivery is out-of-band by the operator. FR5-ADMIN-4 (bulk user operations in panel UI) is a deliberate exclusion documented in architecture.md Decision-adjacent narrative — single-user actions only; bulk needs go through DB-direct scripts.

### Requirements Inventory

#### FR↔Epic coverage matrix

Each functional requirement from `prd.md` § "Initiative 5" Functional Requirements maps to one or more epics here. The "Architectural anchor" column cites the Decision letter(s) from `architecture.md` § "Initiative 5" that the realizing Story bases its implementation on.

| Requirement | Brief description | Realizing Epic(s) | Architectural anchor |
|---|---|---|---|
| FR5-INVITE-1 | Admin generates single-use 256-bit invite tokens with TTL preset + custom; dual-backed Redis + DB | E6 (6.1, 6.2, 6.3) | Decisions A, B |
| FR5-INVITE-2 | Admin lists active + historical invites with per-row metadata + status filter | E6 (6.3), E8 (8.6) | Decisions A, B |
| FR5-INVITE-3 | Admin revokes active invite; revoked-but-listed token MUST be unconsumable (HTTP 410) | E6 (6.2, 6.3), E8 (8.6) | Decisions A, B |
| FR5-INVITE-4 | Single-use semantics; replay attempts fail closed with HTTP 410 + `auth.register.fail` reason `token_consumed` | E6 (6.2) | Decisions A, B |
| FR5-REGISTER-1 | Public `/register?token=` accepts valid unused token; invalid → HTTP 404 + audit `auth.register.fail` reason `token_invalid` | E6 (6.4) | Decisions A, B |
| FR5-REGISTER-2 | Form captures email (RFC syntax) + password (zxcvbn ≥3, length ≥12); failure HTTP 422 with failing-rule body | E6 (6.4) | Decisions A, B |
| FR5-REGISTER-3 | Successful registration creates user with invite-bound role; issues `portal_access` + `portal_refresh` cookies; audit `auth.register.success` | E6 (6.4) | Decisions A, B, C |
| FR5-MEMBER-1 | `member` role grants browse + viewer + `POST /api/admin/share`; share-router expands to `current_member_or_admin` | E6 (6.5) | Decision C |
| FR5-MEMBER-2 | `member` denied all `/api/admin/*` + `/api/audit/*`; `current_admin` stays admin-only | E6 (6.5) | Decision C |
| FR5-MEMBER-3 | Per-member share-token rate-limit + daily cap (≤20/day hard, 50% soft-alert) | E6 (6.7), E9 (9.2 audit verify) | Decisions G, H |
| FR5-2FA-1 | TOTP enrollment with QR + manual secret; 8 single-use recovery codes generated once + stored hashed | E7 (7.1, 7.2) | Decisions D, E |
| FR5-2FA-2 | Login flow extends with second-factor step for users with `totp_enabled_at IS NOT NULL`; accepts TOTP or recovery code | E7 (7.3) | Decisions D, E |
| FR5-2FA-3 | `enforce_2fa_for_roles: list[Role]` config; `Role.agent` triggers fail-fast startup `RuntimeError` | E7 (7.4) | Decision F |
| FR5-2FA-4 | Regenerate recovery codes (invalidates prior batch) + disable TOTP (clears `totp_enabled_at` + invalidates unused codes); both require re-auth | E7 (7.5) | Decision E |
| FR5-ADMIN-1 | Two admin tabs `/admin/users` + `/admin/invites` with paginated lists and documented column sets | E8 (8.2, 8.6) | Decisions I (users tab columns), A (invites tab columns) |
| FR5-ADMIN-2 | Per-user actions: change role, force 2FA, deactivate, reactivate, force logout-all-sessions; each emits matching audit row | E8 (8.3, 8.4) | Decisions I (soft-delete + force-logout), F (force-2FA per-user override) |
| FR5-ADMIN-3 | Admin-issued password-reset link mirrors invite-token shape; Redis `invite:reset:{token}`; out-of-band delivery | E8 (8.5) | Decisions A, B (token shape reuse) |
| FR5-ADMIN-4 | Bulk user ops deliberately NOT in v1 panel UI (single-user only); DB-direct scripts for bulk | Negative AC enforced in E8 (8.2 Users tab — Playwright snapshot test asserts absence of bulk-select / bulk-action selectors); deliberate exclusion also documented in architecture.md narrative | none (architectural decision; negative AC anchored in 8.2) |
| FR5-AUDIT-1 | 16 new audit-log actions emitted via existing `record_event()` — actions are free-form `action=` strings, NOT entries in `KNOWN_ENTITY_TYPES` (which is the entity-type registry); Story 6.1 adds `invite_token` to KNOWN_ENTITY_TYPES, E7 may add `recovery_code` | E6 (6.1, 6.3, 6.4) + E7 (7.2, 7.3, 7.5) + E8 (8.3, 8.4, 8.5) | cross-cuts; uses Init 0 audit-log baseline contract |
| FR5-RATELIMIT-1 | Rate-limit middleware on `/api/auth/login` + `/api/auth/refresh` + `/api/auth/register?token=`; Redis sliding-window | E6 (6.6), E9 (9.2 audit verify) | Decision G |
| FR5-RATELIMIT-2 | Per-member share-token creation cap; soft-alert log at 50%, hard-fail HTTP 429 at 100% | E6 (6.7), E9 (9.2 audit verify) | Decisions G, H |
| FR5-CUTOVER-1 | Atomic single-commit nginx edit dropping `auth_basic` + IP allowlist; preserves share + agent-runbook bypasses | E10 (10.2, 10.3) | Decision K |
| FR5-CUTOVER-2 | Four-scenario post-reload smoke matrix executed against `.190`; per-scenario timestamps + request IDs + audit deltas | E10 (10.1, 10.3) | Decision J |
| FR5-CUTOVER-3 | Verified rollback drill (≤30s end-to-end) before cutover considered closed; any smoke regression triggers immediate rollback | E10 (10.3) | Decision K |

**Coverage:** 24/24 FRs mapped. FR5-ADMIN-4 (bulk-ops deliberate exclusion) and FR5-AUDIT-1 (cross-cutting audit registration) are not single-story-anchored by design — see column notes.

#### NFR↔Epic coverage matrix

| Requirement | Brief description | Realizing Epic(s) | Architectural anchor |
|---|---|---|---|
| NFR5-SEC-1 | E9 audit HARD GATE: zero open Critical/High; ≤3 accepted-rationale Mediums; 4th forces auto-fail + fix sprint | E9 (9.1, 9.2, 9.4) | Decisions G, H (verification surface); audit report shape per FR5-CUTOVER-2 artifact format precedent |
| NFR5-SEC-2 | Per-Medium disposition requires `codex review --commit <SHA>` countersignature in audit report | E9 (9.3) | none (process control) |
| NFR5-SEC-3 | Six-scenario audit coverage matrix: invite brute, refresh replay, CSRF/JWT, IDOR, rate-limit verify, member share amplification | E9 (9.2) | Decisions G, H |
| NFR5-PERF-1 | `last_active_at` write throttled ≤1/5min/user via Redis `SET NX EX 300` | E8 (8.1) | Decision I |
| NFR5-PERF-2 | Edge cutover window ≤5 minutes including smoke + rollback drill; rollback path ≤30 seconds | E10 (10.3) | Decision K |
| NFR5-AUDIT-1 | Every Init 5 audit action emitted via `record_event()` — no parallel logging surface | cross-cuts E6/E7/E8 (every audit-row-emitting story) | Init 0 audit baseline contract |
| NFR5-CROSS-REPO-1 | Epic 10 nginx edit bypasses `3d-portal` `deploy.sh` skip-gate (sibling repo has no `.last-deploy-sha`); closing `docs/operations.md` cutover-date commit records cutover in `3d-portal` deploy history | E10 (10.4) | Decision K |
| NFR5-CROSS-REPO-2 | Rollback story spans both repos (`git revert` in sibling + `nginx -s reload` on `.180` + smoke re-run + revert-the-revert + reload + smoke re-run); sprint plan reflects cross-repo tasks | E10 (10.3) | Decision K |
| NFR5-INT-1 | `agent` role preserved exactly: cookie+password flow unchanged; `Role.agent` MUST NEVER appear in `enforce_2fa_for_roles`; `/agent-runbook` bypass preserved across cutover | E7 (7.4, startup check) + E10 (10.3, smoke scenario 2 + nginx bypass preservation) | Decisions F, K |
| NFR5-INT-2 | `/share/*` location bypass preserved across cutover; share-token TTL + revoke semantics unchanged from Init 0 | E10 (10.3, smoke scenario 1 + nginx bypass preservation) | Decision K |
| NFR5-OBS-1 | All new auth events produce GlitchTip-visible structured log entries via `JsonFormatter` with namespaced loggers (`app.auth.invite`, `app.auth.totp`, `app.auth.register`, `app.admin.users`); counter-shaped events for `*.fail` queryable in dashboard | cross-cuts E6/E7/E8/E9/E10 (every audit-row-emitting story; rate-limit soft-alert log) | Init 1 GlitchTip baseline + Decisions G, H |
| NFR5-OBS-2 | Two named drill artifacts under `_bmad-output/implementation-artifacts/`: `2fa-recovery-drill-YYYY-MM-DD.md` (E7 close) + `cutover-smoke-YYYY-MM-DD.md` (E10 close) | E7 (7.6), E10 (10.3) | Decisions E, J, K |

**Coverage:** 12/12 NFRs mapped. NFR5-AUDIT-1 and NFR5-OBS-1 are cross-cutting and have no single-story anchor by design — the property is preserved by every audit-row-emitting story routing through `record_event()` and the existing namespaced-logger pattern.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E6 | Member role + invite-based registration | 7 (6.1–6.7) | Medium | Medium | FR5-INVITE-1..4, FR5-REGISTER-1..3, FR5-MEMBER-1..3, FR5-RATELIMIT-1..2 (foundation), FR5-AUDIT-1 (E6 subset: 4 actions) | none (entry epic) |
| E7 | TOTP 2FA + recovery codes | 6 (7.1–7.6) | Medium | Medium | FR5-2FA-1..4, NFR5-INT-1 (agent fail-fast), NFR5-OBS-2 (2fa-recovery-drill artifact), FR5-AUDIT-1 (E7 subset: 5 actions) | E6 complete |
| E8 | Admin panel: users + invites | 6 (8.1–8.6) | Medium | Low | FR5-ADMIN-1..3, NFR5-PERF-1, FR5-AUDIT-1 (E8 subset: 7 actions including admin reuse of E6 invite revoke) | E6 + E7 complete |
| E9 | Security audit — **HARD GATE** blocking E10 | 4 (9.1–9.4) | High | **High** | NFR5-SEC-1..3, audit verification of FR5-RATELIMIT-1..2 + FR5-MEMBER-3 | E6 + E7 + E8 complete |
| E10 | Edge cutover (atomic) | 4 (10.1–10.4) | Low | **High** | FR5-CUTOVER-1..3, NFR5-PERF-2, NFR5-CROSS-REPO-1..2, NFR5-INT-1..2, NFR5-OBS-2 (cutover-smoke artifact) | **E9 audit PASS (NFR5-SEC-1 gate condition: zero open Critical/High, ≤3 accepted-rationale Mediums)** |

**Total:** 27 stories planned (within CC §4.4 estimate floor 25, ceiling 35). Effort total estimated at 4–6 weeks back-to-back per brief Vision section.

**Sequencing:** E6 → E7 → E8 → **E9 (HARD GATE)** → E10. E10 is contractually blocked on E9 audit PASS — no "yolo cutover" override path is documented anywhere. If E9 audit produces a 4th Medium or any open Critical/High, E10 is parked and a fix sprint is triaged before the cutover unlocks. The HARD GATE is structural, not procedural — there is no `--force` flag in any cutover script.

#### Epic 6 — Member role + invite-based registration

**Goal.** Wire the end-to-end core flow from "admin generates invite link" → "operator delivers link out-of-band" → "recipient lands on `/register?token=...`" → "server validates token + email + password strength + creates user with invite-bound role + issues cookie pair" → "member can browse catalog and mint share tokens". Also ship the cross-cutting rate-limit middleware (Redis sliding-window) that the E9 audit will verify and the per-member share-token cap that closes the share-link-amplification surface flagged in brief Q3.

**Acceptance gate.** End-to-end happy path drilled on `.190`: invite generated by admin via Story 6.3 endpoint → consumed via Story 6.4 register flow → resulting member-cookie-authenticated `POST /api/admin/share` returns 201 (Story 6.5 permission expansion) → rate-limit middleware (Story 6.6) rejects 6th failed login from one IP within 60s with HTTP 429 → per-member share cap (Story 6.7) returns HTTP 429 on the 21st share creation in a UTC day. All E6 audit actions (`auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`) visible via `/api/admin/audit` with correct actor + target.

**FRs realized:** FR5-INVITE-1, FR5-INVITE-2 (admin endpoints subset; Invites tab UI is E8.6), FR5-INVITE-3, FR5-INVITE-4, FR5-REGISTER-1..3, FR5-MEMBER-1..3, FR5-RATELIMIT-1..2, FR5-AUDIT-1 (E6 subset: 5 actions).

**Architectural anchors:** Decisions A (invite-token dual-backed storage), B (invite-token shape + Alembic 0012), C (member permission scope diff + `current_member_or_admin` dependency), G (rate-limit middleware), H (per-member share cap).

**Blocked by:** none. Entry epic for Initiative 5.

##### Story 6.1 — Alembic migration `0012_invite_tokens` + invite-token primitives

**Realizes:** FR5-INVITE-1, FR5-INVITE-4, FR5-AUDIT-1 (`auth.invite.*` action names emitted via `record_event()`; new entity_type `invite_token` added to `KNOWN_ENTITY_TYPES`).
**Architectural anchor:** Decisions A, B (table schema per Decision B column table + indexes + TTL preset enum).
**Depends on:** none (E6 entry story).

Acceptance check shape:

- `apps/api/migrations/versions/0012_invite_tokens.py` exists with the column set + indexes specified in `architecture.md` § Initiative 5 Decision B; `alembic upgrade head` and `alembic downgrade -1` both succeed on a fresh SQLite test DB. (Path was `alembic/versions/` in pre-2026-05-19 planning text; corrected to live `migrations/versions/` per `alembic.ini:8` `script_location = %(here)s/migrations`.)
- `apps/api/app/modules/invite/models.py` exports `InviteTTLPreset(IntEnum)` (1d / 3d / 7d / 30d values) + `InviteToken` SQLModel + a `hash_token(token: str) -> str` SHA-256 helper.
- 4 new audit action names emitted via `record_event()`: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success` (the 5th E6 audit action `auth.register.fail` is added in 6.4 with the public route). NEW entity_type `invite_token` added to `KNOWN_ENTITY_TYPES` (the entity-type registry at `apps/api/app/core/audit.py:28-44`). Action names are convention; entity_types are the registry.
- Logger filter in `apps/api/app/core/logging.py` redacts query-string `token=` values and POST-body `token` fields from JSON log records (verifiable: a manually-constructed log record containing `token=abc` emits with `token=<redacted>`).

##### Story 6.2 — `apps/api/app/modules/invite/service.py` dual-backed write/read/revoke/consume

**Realizes:** FR5-INVITE-1 (entropy at write), FR5-INVITE-3 (immediate revoke), FR5-INVITE-4 (single-use consume + replay-fails-closed).
**Architectural anchor:** Decisions A, B.
**Depends on:** 6.1 (table + helpers).

Acceptance check shape:

- `generate_invite(role, ttl_seconds, generated_by_user_id) -> tuple[token_cleartext, InviteToken]` writes the DB row first, then Redis key (`invite:token:{token}` with `EXPIRE` matching `ttl_seconds`); failure mid-sequence does not leave a dangling Redis key without a DB row.
- `validate_active(token) -> InviteToken | None` checks Redis first (O(1)), returns `None` on miss without touching the DB.
- `consume(token, used_by_user_id, used_from_ip) -> InviteToken` is atomic: validate-in-Redis → DB update with `used_by_user_id` + `used_at` + `used_from_ip` → DEL Redis key. Failure between DB update and DEL is the rare edge case — Redis TTL still expires naturally; the DB row reflects authoritative "used" state.
- `revoke(invite_id) -> None` deletes the Redis key (`DEL`) and sets `revoked_at` on the DB row in one transaction.
- Replay path: second `consume()` on the same token returns `None` from `validate_active()` after the first consume completed (Redis key gone); caller raises HTTP 410 with reason `token_consumed`.

##### Story 6.3 — Admin endpoints: generate / list / revoke

**Realizes:** FR5-INVITE-1, FR5-INVITE-2 (server endpoint with status filter), FR5-INVITE-3, FR5-AUDIT-1 (`auth.invite.generated`, `auth.invite.revoked`).
**Architectural anchor:** Decisions A, B.
**Depends on:** 6.2 (service layer).

Acceptance check shape:

- `POST /api/admin/invites` accepts `{role, ttl_seconds | ttl_preset, custom_ttl_seconds?}` from admin-authenticated request; returns `{invite_id, token, registration_url, role, ttl_seconds, expires_at}` (cleartext token surfaces ONCE in this response only). Audit `auth.invite.generated` emitted with `actor_user_id`, `target_user_id=null`, `request_id`.
- `GET /api/admin/invites?status=active|used|expired|revoked&page=N&page_size=M` returns paginated rows with per-row metadata (`generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`); never includes cleartext token.
- `POST /api/admin/invites/{id}/revoke` calls service `revoke()`; subsequent `GET /register?token=<that-token>` returns HTTP 410 Gone. Audit `auth.invite.revoked` emitted.
- All three endpoints require `current_admin` dependency; member-authenticated requests return 403.
- Endpoints follow Init 0 admin-router conventions (filename layout, error envelope, X-Portal-Client CSRF check).

##### Story 6.4 — Public `/api/auth/register?token=` + `/register` UI

**Realizes:** FR5-REGISTER-1, FR5-REGISTER-2, FR5-REGISTER-3, FR5-AUDIT-1 (`auth.register.success`, `auth.register.fail` reasons `token_invalid` / `token_consumed` / `weak_password`).
**Architectural anchor:** Decisions A, B (token consumption flow), C (cookie issuance reuses Init 0 auth contract).
**Depends on:** 6.2 (consume flow).

Acceptance check shape:

- `POST /api/auth/register` accepts `{token, email, password}`; runs the validation chain: token Redis lookup (miss → HTTP 404 + `auth.register.fail` reason `token_invalid`); email RFC syntax (no DNS/MX); password zxcvbn score ≥3 AND length ≥12 (fail → HTTP 422 + body identifies failing rule + `auth.register.fail` reason `weak_password`); existing user with that email → HTTP 409 + `auth.register.fail` reason `email_taken`.
- On all-checks-pass: create user with `role` from invite + hashed password (existing bcrypt path) → consume invite (6.2 atomic flow) → issue `portal_access` (10min) + `portal_refresh` (30d) cookies via existing Init 0 `auth/cookies.py` helpers → emit `auth.register.success`.
- `apps/web/src/modules/auth/RegisterPage.tsx` React route at `/register` reads `?token=` query param, posts the form, redirects to `/catalog` on 201, surfaces the 422 failing-rule body inline below the password field on validation failure, surfaces 404 + 410 as full-page error states (invalid / consumed token).
- Public route is rate-limited via Story 6.6 middleware (`register` scope, 3 attempts / 60s per IP).
- Visual-regression baselines for `/register` page added in same commit (matches `feedback_docs_hygiene.md` no-red-state rule from Init 3 Principle 3).

##### Story 6.5 — Member permission expansion: `current_member_or_admin` dependency + share-router auth diff

**Realizes:** FR5-MEMBER-1, FR5-MEMBER-2.
**Architectural anchor:** Decision C (binding per-route allowlist table).
**Depends on:** 6.4 (member accounts exist).

Acceptance check shape:

- `apps/api/app/core/auth/dependencies.py` exports `current_member_or_admin` (raises 403 for `Role.agent` and any other non-listed role).
- `apps/api/app/modules/share/admin_router.py` route `POST /api/admin/share` decorator switches from `current_admin` to `current_member_or_admin` (one-line dependency swap); every other share-router route + every `/api/admin/*` route + `/api/audit/*` read endpoint stays on `current_admin`.
- `apps/api/tests/conftest.py` adds `member_user_cookies` fixture analogous to existing `admin_user_cookies`.
- Integration tests cover both directions: member POST `/api/share/` → 201 with fresh share token; member GET `/api/admin/users` → 403; admin POST `/api/share/` → 201 (unchanged); anonymous POST `/api/share/` → 401 (unchanged).

##### Story 6.6 — Rate-limit middleware `apps/api/app/core/auth/ratelimit.py` for login / refresh / register

**Realizes:** FR5-RATELIMIT-1 (3 scopes), NFR5-SEC-3 (foundation for E9 audit scenario coverage of these 3 scopes).
**Architectural anchor:** Decision G (sliding-window over Redis sorted set + middleware-placement contract + key shapes + tunable thresholds).
**Depends on:** 6.4 (register endpoint to rate-limit).

Acceptance check shape:

- New file `apps/api/app/core/auth/ratelimit.py` exporting `RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold)` per Decision G one-pipelined-call shape (`ZREMRANGEBYSCORE` + `ZADD` + `EXPIRE` + `ZCARD` via `MULTI/EXEC`).
- Three middleware instances mounted in `apps/api/app/main.py` factory **AFTER CORS, AFTER CSRF check, BEFORE auth dependency resolution** (placement matters — see Decision G rationale).
- Default thresholds from `apps/api/app/core/config.py`: `login` 5 failures / 60s per IP; `refresh` 10 attempts / 60s per IP; `register` 3 attempts / 60s per IP. All four `*_window_seconds` + `*_threshold` Pydantic Settings keys tunable.
- Failure mode: Redis unreachable → middleware logs `WARNING app.auth.ratelimit redis_unavailable scope=<scope>` and ALLOWS the request (matches Init 0 share-token fail-soft semantics; GlitchTip captures the warning per NFR5-OBS-1).
- Unit tests use `fakeredis`; integration test against `.190` Redis verifies 6th call from one IP returns HTTP 429 with `Retry-After` header.

##### Story 6.7 — Per-member share-token cap (extension of 6.6 middleware to `share` scope + soft-alert)

**Realizes:** FR5-MEMBER-3, FR5-RATELIMIT-2.
**Architectural anchor:** Decisions G (middleware reuse with `share` scope), H (cap key + soft/hard thresholds + admin exemption + scope binding to `POST /api/admin/share` only).
**Depends on:** 6.5 (member role expansion to `POST /api/admin/share`), 6.6 (middleware base).

Acceptance check shape:

- Fourth middleware instance mounted with scope `share`, key `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` (UTC), window `86400s`, threshold `20` creations.
- Soft-alert at 10 creations (50% threshold) emits structured log `app.share.ratelimit.soft_alert {user_id, role, count, threshold, window_end}` visible in GlitchTip per NFR5-OBS-1.
- Hard-fail at 21st creation returns HTTP 429 with `Retry-After: <seconds-until-UTC-midnight>` header.
- Admin exemption: `if request.state.user.role == Role.admin: return await call_next(request)` short-circuit at top of `share` middleware. Verified by scripted test: admin 21st share returns 201; member 21st share returns 429.
- Cap applies ONLY to `POST /api/admin/share`. `DELETE /api/admin/share/{token}` (admin-only) and `GET /api/share/{token}` (anonymous consumption) untouched.
- E9 audit scenario coverage (Story 9.2 scenario 6) verifies both soft-alert log emission AND hard-fail behavior on the same member account.

#### Epic 7 — TOTP 2FA + recovery codes

**Goal.** Add optional second-factor authentication with eight mandatory single-use recovery codes generated once at enrollment; allow per-role enforcement via a config flag with the `agent` role explicitly excluded by fail-fast startup validation; close with a documented end-to-end recovery-code drill against `.190` capturing AuditLog row deltas.

**Acceptance gate.** Test user enrolls TOTP via Story 7.2 panel → logs out → logs back in via Story 7.3 partial-auth path with a fresh TOTP code → logs out → logs back in consuming a recovery code → regenerates recovery codes via Story 7.5 → disables TOTP via Story 7.5 → logs back in with password-only → drill artifact `2fa-recovery-drill-YYYY-MM-DD.md` (NFR5-OBS-2 first slot) committed under `_bmad-output/implementation-artifacts/` with per-step timestamps + request IDs + audit row references. Startup-fail test for `Role.agent in enforce_2fa_for_roles` passes (Story 7.4).

**FRs realized:** FR5-2FA-1..4, NFR5-INT-1 (agent fail-fast startup), NFR5-OBS-2 first artifact, FR5-AUDIT-1 (E7 subset: `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`).

**Architectural anchors:** Decisions D (`users.totp_secret` Fernet + `totp_enabled_at`), E (`recovery_codes` table + bcrypt-at-rest + batch grouping), F (`enforce_2fa_for_roles` config flag + lifespan-startup fail-fast).

**Blocked by:** E6 complete (member accounts exist as 2FA-enrolling subjects).

##### Story 7.1 — Alembic migration `0013_users_2fa_columns` + recovery-codes table + Fernet key plumbing

**Realizes:** FR5-2FA-1 (table foundation), FR5-AUDIT-1 (5 E7 action names emitted via `record_event()`; entity_type decision — `recovery_code` new or reuse `user` — encoded at Story 7.1 spec creation).
**Architectural anchor:** Decisions D (users column additions + Fernet key), E (recovery_codes table + indexes).
**Depends on:** 6.1 (Alembic chain continuity).

Acceptance check shape:

- `apps/api/migrations/versions/0013_users_2fa_columns.py` adds `user.totp_secret VARCHAR(255) NULL` + `user.totp_enabled_at DATETIME NULL` + `recovery_codes` table per Decision E column spec + 2 indexes; existing `admin` + `agent` rows verified NULL-default (NFR5-INT-1 null-op migration semantics). Table name `user` singular (Init 0 convention).
- `TOTP_FERNET_KEY: str` added to `apps/api/app/core/config.py` Pydantic Settings; absence raises `RuntimeError` at startup (fail-fast — no unconfigured deployment can accidentally store plaintext secrets).
- `infra/env.example` adds `TOTP_FERNET_KEY=<generate-with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">` documentation line.
- `apps/api/tests/conftest.py` adds `TOTP_FERNET_KEY` test override (deterministic test key).
- 5 new audit action names emitted via `record_event()`: `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`. Entity_type decision at spec-creation time: either (a) add `recovery_code` to `KNOWN_ENTITY_TYPES`, or (b) reuse existing `user` entity_type (precedent: `auth.login.*` already emits with `entity_type="user"`).

##### Story 7.2 — TOTP enrollment endpoint + UI (`POST /api/auth/2fa/enroll` + confirm + `/settings/2fa`)

**Realizes:** FR5-2FA-1.
**Architectural anchor:** Decisions D (Fernet encryption boundary + serializer omit of `totp_secret`), E (8 recovery codes batch generation).
**Depends on:** 7.1 (migration + Fernet key).

Acceptance check shape:

- `POST /api/auth/2fa/enroll` (authenticated, any role except agent) generates a pyotp secret + provisioning URI; returns `{qr_svg, manual_secret, enrollment_token}` (enrollment_token Redis-stashed 10min to bridge enroll → confirm).
- `POST /api/auth/2fa/enroll/confirm {enrollment_token, code}` verifies the 6-digit code, persists `totp_secret` Fernet-encrypted in `users.totp_secret`, sets `totp_enabled_at = NOW()`, generates 8 fresh recovery codes (`secrets.token_hex(4)`, 32 bits each) with shared `batch_id`, stores them bcrypt-hashed in `recovery_codes`, returns the 8 cleartext codes ONCE in the response body. Audit `auth.totp.enrolled` emitted with `actor_user_id == target_user_id`.
- `apps/web/src/modules/auth/Settings2faPage.tsx` React route at `/settings/2fa` walks the enroll flow: QR scan / manual entry → confirm code → display cleartext recovery codes with download-as-txt + clipboard-copy buttons + "I have saved these" confirmation modal that gates the page from advancing.
- Subsequent `GET /settings/2fa` page loads return only batch metadata (`{batch_id, generated_at, codes_remaining}`) — cleartext codes are unrecoverable per Decision E "display ONCE" property.
- `apps/api/app/core/db/serializers.py` explicitly omits `totp_secret` from any `users` row serialization (verified by scripted test against `/api/auth/me` response shape).

##### Story 7.3 — Login flow extension: partial-auth + TOTP / recovery-code verify step

**Realizes:** FR5-2FA-2.
**Architectural anchor:** Decisions D (decrypt-on-verify boundary), E (recovery code consumption iteration + bcrypt check).
**Depends on:** 7.2 (users can enroll).

Acceptance check shape:

- `POST /api/auth/login` for users with `totp_enabled_at IS NOT NULL` returns HTTP 200 + body `{partial_auth: true, totp_required: true, partial_token}` (NO `portal_access` cookie set); `partial_token` Redis-stashed 5min.
- `POST /api/auth/2fa/verify {partial_token, code}` accepts either a current 6-digit TOTP code OR an 8-char recovery code: validate-via-Fernet-decrypt for TOTP; iterate active batch (where `invalidated_at IS NULL`) calling `bcrypt.checkpw()` for recovery codes — first match sets `used_at` and emits `auth.recovery_code.used`. Success: issues `portal_access` + `portal_refresh` cookies + emits `auth.totp.verify.success`. Failure: HTTP 401 + `auth.totp.verify.fail`.
- Frontend `AuthGate` + `LoginPage` extended to detect `partial_auth` response and prompt for second-factor input; UI flow accepts either input type without an explicit switch (regex-distinguish TOTP `^\d{6}$` vs recovery code `^[0-9a-f]{8}$`).
- Story 6.6 login rate-limit (5 failures / 60s per IP) is unaffected — second-factor failures count against the same `login` scope key (defense in depth: brute-forcing the second factor still trips the IP rate-limit).
- Visual-regression baselines for the second-factor prompt screen added in same commit.

##### Story 7.4 — `enforce_2fa_for_roles` config + lifespan-startup fail-fast + middleware enforcement

**Realizes:** FR5-2FA-3, NFR5-INT-1 (agent fail-fast).
**Architectural anchor:** Decision F.
**Depends on:** 7.3 (login flow has 2FA path to enforce).

Acceptance check shape:

- `apps/api/app/core/config.py` adds `enforce_2fa_for_roles: list[Role] = Field(default_factory=list)`.
- `apps/api/app/main.py` lifespan-startup runs BEFORE Redis connection + BEFORE any route mount: `if Role.agent in settings.enforce_2fa_for_roles: raise RuntimeError(...)` with the verbatim error message from Decision F. Verified by `apps/api/tests/test_config.py::test_agent_role_in_enforce_2fa_raises`.
- `apps/api/app/core/auth/middleware.py` adds post-login pre-cookie-issue check: `if user.role in settings.enforce_2fa_for_roles and user.totp_enabled_at is None: return partial_auth_response_forcing_enrollment(user)` — frontend lands on `/settings/2fa` enrollment screen before any other route works for that user.
- Per-user override path (Decision F cascading) — admin force-enrollment endpoint (E8 Story 8.4) sets `totp_enabled_at` directly independent of config flag.
- `infra/env.example` documents `ENFORCE_2FA_FOR_ROLES=` (empty default; comma-separated role names; agent forbidden).

##### Story 7.5 — Regenerate recovery codes + disable TOTP from `/settings/2fa`

**Realizes:** FR5-2FA-4.
**Architectural anchor:** Decision E (batch invalidation + audit lifecycle columns).
**Depends on:** 7.2 (enrollment exists), 7.3 (verify path for re-auth).

Acceptance check shape:

- `POST /api/auth/2fa/recovery-codes/regenerate` requires re-auth body `{password, totp_code}` (verified against Story 7.3 verify primitives) before action; UPDATEs prior batch `invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL` → INSERTs 8 fresh codes with new `batch_id` → returns cleartext codes ONCE in response body.
- `POST /api/auth/2fa/disable` requires re-auth body `{password, totp_code}`; clears `users.totp_enabled_at = NULL`, invalidates all `recovery_codes` rows for the user (`invalidated_at = NOW() WHERE invalidated_at IS NULL`), emits `auth.totp.disabled` with `actor == target`. Note: `users.totp_secret` is intentionally retained as Fernet ciphertext — disable does not delete the secret column, only clears the timestamp; rationale: enables future "I re-enrolled with the same authenticator app" path without secret rotation (low-priority optimization).
- Post-disable login flow returns to single-factor (Story 7.3 partial-auth path no longer triggers since `totp_enabled_at IS NULL`).
- UI panel at `/settings/2fa` exposes both actions behind a re-auth modal (password + current TOTP).

##### Story 7.6 — End-to-end recovery-code drill against `.190` + artifact authoring

**Realizes:** NFR5-OBS-2 first artifact slot.
**Architectural anchor:** Decision E (recovery codes lifecycle as drill subject).
**Depends on:** 7.2 + 7.3 + 7.5 (full 2FA lifecycle in place).

Acceptance check shape:

- Drill executed against deployed `.190` (NOT against CI fixtures or local dev — per brief Success Criterion #5 verbatim). Test-member account used as drill subject (seeded out-of-band ahead of drill).
- Drill steps captured with timestamps + request IDs + AuditLog row references: (1) enroll test user via `/settings/2fa` → confirm cleartext recovery codes saved out-of-band; (2) log out; (3) log in supplying password + TOTP from authenticator app → verify `auth.totp.verify.success` row; (4) log out; (5) log in supplying password + recovery code (1 of 8) → verify `auth.recovery_code.used` row + `auth.totp.verify.success` row; (6) regenerate recovery codes from `/settings/2fa` → verify prior batch `invalidated_at` populated, new batch displayed once; (7) disable TOTP → verify `auth.totp.disabled` row + `totp_enabled_at IS NULL`; (8) log in with password-only → verify normal single-factor flow restored.
- Artifact written to `_bmad-output/implementation-artifacts/2fa-recovery-drill-YYYY-MM-DD.md` (gitignored per `feedback_local_only_docs.md`); committed locally only.
- Artifact format mirrors the Init 1 verify-symbolication artifact shape (operator pattern familiarity from Init 1 Decision K precedent).
- Artifact serves as Epic 7 acceptance gate evidence — Epic 7 is not considered closed until the drill artifact lands.

#### Epic 8 — Admin panel: users + invites

**Goal.** Ship two new admin tabs (`/admin/users`, `/admin/invites`) on the existing admin module, soft-delete + `last_active_at` infrastructure (Redis `SET NX EX 300` throttle so SQLite writes stay at ≤1/5min/user), and the per-user action surface (change role, deactivate / reactivate, force logout-all-sessions, force-2FA-enrollment, issue password reset). Operator daily-driver path: zero panel-triggered operations require SQL inspection (brief Success Criterion #2).

**Acceptance gate.** All four brief-defined routine operator actions exercised via the panel UI on `.190`: generate invite (via E6 Story 6.3 endpoint surfaced via Invites tab in 8.6), revoke invite (via 8.6 panel button), change user role (via 8.3), reset user password (via 8.5). Plus the soft-delete + reactivate cycle (8.3), force-logout-all-sessions (8.3), force-2FA-enrollment (8.4) all panel-driven. Audit row visible for every panel action with correct `actor_user_id` / `target_user_id` pair.

**FRs realized:** FR5-ADMIN-1..3 (FR5-ADMIN-4 is the deliberate exclusion — no story), NFR5-PERF-1, FR5-AUDIT-1 (E8 subset: 7 action names — `user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`, `auth.totp.enrolled` actor!=target, `auth.password.reset.initiated`, `auth.password.reset.completed`).

**Architectural anchors:** Decisions A + B (admin-issued password-reset link reuses invite-token shape), F (force-2FA per-user override surface), I (soft-delete + `last_active_at` throttle).

**Blocked by:** E6 complete (member accounts exist as panel subjects), E7 complete (force-2FA action needs 2FA enrollment infrastructure).

##### Story 8.1 — Alembic migration `0014_users_is_active_last_active` + `LastActiveMiddleware`

**Realizes:** NFR5-PERF-1, FR5-AUDIT-1 (E8 action names registered).
**Architectural anchor:** Decision I.
**Depends on:** 7.1 (Alembic chain continuity).

Acceptance check shape:

- `apps/api/migrations/versions/0014_users_is_active_last_active.py` adds `user.is_active BOOLEAN NOT NULL DEFAULT TRUE` (backfill existing rows TRUE) + `user.last_active_at DATETIME NULL`; verified that Init 0 + Init 2 existing `admin` + `agent` rows backfill to `is_active = TRUE`. Table name `user` singular (Init 0 convention).
- `apps/api/app/core/auth/middleware.py` adds `LastActiveMiddleware` per Decision I implementation: `SET NX EX 300` atomic Redis call gates DB write to ≤1/5min/user; runs after auth dependency resolution on authenticated requests only.
- 7 E8 audit action names emitted via `record_event()`: `user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`, `auth.password.reset.initiated`, `auth.password.reset.completed` (the 7th, `auth.totp.enrolled` with actor!=target, was already in use from 7.1; 8.4 emits it with new actor/target pivot). All these actions emit with existing `user` entity_type; no new entries needed in `KNOWN_ENTITY_TYPES`.
- Scripted test: 50 authenticated requests from one user within 1 minute produce exactly 1 `UPDATE users SET last_active_at` (verified via `apps/api/tests/integration/test_last_active_throttle.py` against fakeredis).

##### Story 8.2 — Admin Users tab (`/admin/users` route + `GET /api/admin/users` paginated list)

**Realizes:** FR5-ADMIN-1.
**Architectural anchor:** Decision I (`is_active` + `last_active_at` are panel-visible columns).
**Depends on:** 8.1 (columns exist to display).

Acceptance check shape:

- `GET /api/admin/users?page=N&page_size=M&search=<email-substring>` returns paginated rows with columns `{id, email, role, created_at, last_active_at, totp_enabled (derived: totp_enabled_at IS NOT NULL), is_active}`; requires `current_admin`.
- `apps/web/src/modules/admin/UsersPage.tsx` React route at `/admin/users` renders the paginated table with column sort (email, role, created_at, last_active_at) + search input + page-size selector.
- Pagination defaults match existing admin-list defaults (Init 0 pattern: 25 rows per page).
- Visual-regression baselines for `/admin/users` empty / one-row / many-row states added in same commit.
- **Negative AC (FR5-ADMIN-4 enforcement):** the Users tab UI exposes NO `select all` checkbox column header, NO row-level multi-select checkboxes, NO bulk-action menu (`Bulk role change`, `Bulk disable`, etc.); the per-row action menu shipped in Story 8.3 is the ONLY action surface. Verifiable: a Playwright snapshot test asserts the absence of bulk-select / bulk-action selectors. The deliberate exclusion is recorded so future agents (UI redesigns, panel-v2 considerations) do not infer missing bulk CRUD as a defect.

##### Story 8.3 — Per-user actions: change role, deactivate / reactivate, force logout-all-sessions

**Realizes:** FR5-ADMIN-2 (subset), FR5-AUDIT-1 (`user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`).
**Architectural anchor:** Decision I (soft-delete + force-logout via existing refresh-token family invalidation).
**Depends on:** 8.2 (users tab UI), 8.1 (`is_active` column).

Acceptance check shape:

- `PATCH /api/admin/users/{id}` accepts `{role?, is_active?}` mutations; per-mutation emits one audit row (`user.role_changed` if role changed; `user.deactivated` if `is_active false`; `user.reactivated` if `is_active true→true-after-false` — verified by reading prior value). All emit with `actor_user_id == admin.id`, `target_user_id == path-id`.
- `POST /api/admin/users/{id}/force-logout` invokes existing `apps/api/app/modules/auth/sessions/service.py` revoke-all helper to invalidate every refresh-token family for the target user → emits `user.force_logout`. After ≤10 minutes the target's access token expires and they are fully logged out (per Decision I "JWT-based requests stay valid until natural expiry").
- Deactivation behavior verified end-to-end: target user with `is_active = FALSE` attempting `POST /api/auth/refresh` returns HTTP 401 + emits `auth.login.fail` reason `account_deactivated` + invalidates the refresh-token family (matches Init 0 reuse-detection invalidation pattern).
- UI on Users tab: per-row action menu with "Change role" / "Deactivate" / "Reactivate" / "Force logout all sessions"; each gated by a confirmation modal.

##### Story 8.4 — Admin 2FA overrides per-user: force-enrollment + force-disable (lockout recovery)

**Realizes:** FR5-ADMIN-2 (subset — both force-enrollment and force-disable per `actor != target` audit shape), FR5-AUDIT-1 (`auth.totp.enrolled` with `actor != target` + `auth.totp.disabled` with `actor != target`).
**Architectural anchor:** Decision F (per-user override path independent of `enforce_2fa_for_roles` config flag — applies to BOTH directions: force-enroll and force-disable).
**Depends on:** 7.4 (config-flag enforcement path exists; per-user override wired into same middleware check), 7.5 (user-side disable-TOTP endpoint exists; this Story adds the admin-side mirror with different auth contract — admin actor instead of user actor, no user-password+TOTP re-auth requirement since the lockout-recovery scenario implies the user CANNOT supply those).
**Depended on by:** 8.5 (admin-issued password-reset link references this Story's force-disable-2FA endpoint as Step 1 of the lost-2FA-AND-lost-recovery-codes recovery flow).

Acceptance check shape:

- **Force-2FA-enrollment endpoint:** `POST /api/admin/users/{id}/force-2fa-enrollment` flags the target user for mandatory-enrollment-on-next-login (implementation: set a `users.force_2fa_enrollment BOOLEAN` flag — added in this story as a minor column addition reusing the 0014 migration or a new tiny 0015 migration per implementer's call; or alternatively reuse Decision F middleware path by checking the target's user record at login and routing to `/settings/2fa`). Audit `auth.totp.enrolled` with `actor_user_id == admin.id`, `target_user_id != actor_user_id`, plus a `force_enrolled: true` extra field in the audit payload. On next login, target lands on `/settings/2fa` enrollment screen before any other route works (same path as Decision F config-flag enforcement). After target completes enrollment, the flag is cleared automatically (one-shot).
- **Force-disable-2FA endpoint (lockout recovery):** `POST /api/admin/users/{id}/force-disable-2fa` clears `users.totp_enabled_at = NULL` for the target user, invalidates all `recovery_codes` rows for that user (`invalidated_at = NOW() WHERE invalidated_at IS NULL`), emits `auth.totp.disabled` with `actor_user_id == admin.id`, `target_user_id != actor_user_id`, plus an `admin_override: true` extra field in the audit payload. Requires `current_admin` only — does NOT require the target user's password + current TOTP (the user-side 7.5 disable endpoint requires those for self-disable; this admin-side endpoint is the lockout-recovery mirror that bypasses re-auth precisely because the user is presumed locked out). `users.totp_secret` Fernet ciphertext is retained (matches Story 7.5 retention policy).
- **UI on Users tab:** two per-row action menu entries:
  - "Force 2FA enrollment" — enabled only when target's `totp_enabled = false`.
  - "Force-disable 2FA (lockout recovery)" — enabled only when target's `totp_enabled = true`; gated by a confirmation modal explaining the recovery context + recommending immediate password-reset issuance (Story 8.5) as the typical follow-up step.
- **Force-disable endpoint is NOT rate-limited beyond standard admin rate-limit budget** — it is an operator-triggered low-frequency action, not a public surface.
- **Audit traceability:** both endpoints emit audit rows queryable via `/api/admin/audit?action=auth.totp.enrolled&force_enrolled=true` (force-enrollment view) and `/api/admin/audit?action=auth.totp.disabled&admin_override=true` (force-disable view).

##### Story 8.5 — Admin-issued password-reset link

**Realizes:** FR5-ADMIN-3, FR5-AUDIT-1 (`auth.password.reset.initiated`, `auth.password.reset.completed`).
**Architectural anchor:** Decisions A + B (token shape reuse — Redis-fronted single-use opaque token), I (lost-2FA-AND-lost-recovery-codes recovery path: admin force-disables 2FA via Story 8.4 endpoint first, then issues reset via this Story).
**Depends on:** 6.2 (invite-token service primitives generalize to reset tokens), 8.3 (admin user-actions UI), 8.4 (force-disable-2FA endpoint exists as Step 1 of lost-2FA recovery flow — concrete endpoint, not "planned").

Acceptance check shape:

- `POST /api/admin/users/{id}/password-reset` mints a single-use 256-bit opaque token; stores at Redis key `invite:reset:{token}` (TTL default 1h configurable via `PASSWORD_RESET_TTL_SECONDS` Pydantic Settings field) with value `{user_id, generated_by, generated_at}`. NO DB-row audit history is needed at the password-reset-link tier — `auth.password.reset.initiated` audit row captures issuance; `auth.password.reset.completed` captures consumption. Returns `{reset_url}` to admin (one-time display, mirrors invite-token UX).
- Public `POST /api/auth/password-reset?token=<token>` consumption endpoint accepts `{token, new_password}`; runs zxcvbn ≥3 ≥12-char check (same gate as registration); on success updates `users.password_hash` + emits `auth.password.reset.completed` + DELs Redis key (single-use semantics).
- `apps/web/src/modules/auth/ResetPasswordPage.tsx` React route at `/reset-password` mirrors `/register` form's password-strength gates.
- **Lost-2FA-AND-lost-recovery-codes recovery flow (two explicit steps):** Step 1 — operator invokes Story 8.4 `POST /api/admin/users/{id}/force-disable-2fa` endpoint, audit `auth.totp.disabled` with `actor != target` + `admin_override: true`. Step 2 — operator invokes this Story's `POST /api/admin/users/{id}/password-reset` endpoint, audit `auth.password.reset.initiated`. The two-step flow is documented in `docs/operations.md` (operator runbook section authored in Story 10.4 closing commit) with explicit endpoint references rather than the previously-ambiguous "via existing 7.5 / planned admin-disable" phrasing.
- Endpoint rate-limited via Story 6.6 middleware (`register` scope shared — 3 attempts / 60s per IP; reset and register share the public-write rate-limit budget by design).

##### Story 8.6 — Admin Invites tab (`/admin/invites` route + status filter UI)

**Realizes:** FR5-ADMIN-1, FR5-INVITE-2 (UI surface on top of 6.3 endpoint), FR5-INVITE-3 (panel revoke button calls 6.3 revoke endpoint).
**Architectural anchor:** Decisions A + B (DB row metadata surfaced in UI).
**Depends on:** 6.3 (admin invite endpoints).

Acceptance check shape:

- `apps/web/src/modules/admin/InvitesPage.tsx` React route at `/admin/invites` calls `GET /api/admin/invites?status=...` from 6.3; renders paginated table with `status` filter dropdown (active / used / expired / revoked / all) + per-row metadata columns (`generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`).
- "Generate invite" button opens a modal collecting `{role, ttl_preset | custom_ttl_seconds}` → calls 6.3 `POST /api/admin/invites` → displays the cleartext token + `registration_url` in a copy-friendly one-time modal (matches Decision B "cleartext token surfaces ONCE" property).
- Per-row "Revoke" button (active invites only) calls 6.3 `POST /api/admin/invites/{id}/revoke` → row transitions to `revoked` state.
- Visual-regression baselines for empty / mixed-status / generate-modal / revoke-confirm states added in same commit.

#### Epic 9 — Security audit (HARD GATE — blocks E10)

**Goal.** Pre-cutover audit using `bandit` + `semgrep` + `pip-audit` + `npm audit` / `osv-scanner` + OWASP ZAP active scan against `.190` + `codex review` countersignature for each Medium disposition. Produce a signed-off audit report at `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` meeting the NFR5-SEC-1 gate condition: zero open Critical/High findings; at most three "accepted-with-rationale" Medium findings; the fourth forces auto-fail and triggers a fix sprint.

**Acceptance gate.** **HARD GATE for E10.** Audit report signed off with explicit gate-condition decision line: either "E10 cleared to proceed" (PASS) or "E10 blocked, fix sprint required" with the list of triaging issues. There is NO bypass flag, NO override path, NO `--force` flag in any cutover script. If the audit fails, the cutover is parked and the failing findings triage into a fix sprint before the audit reruns and the gate re-evaluates. Critical and High findings have NO "accepted" disposition path — fixed-or-bust. Mediums get max-3 cap; the 4th is auto-fail.

**FRs / NFRs realized:** NFR5-SEC-1, NFR5-SEC-2, NFR5-SEC-3 (six-scenario coverage matrix); audit verification of FR5-RATELIMIT-1 + FR5-RATELIMIT-2 + FR5-MEMBER-3 (Story 6.6 / 6.7 / 8.x outputs are verified-under-load here, not first-implemented).

**Architectural anchors:** Decisions G + H provide the rate-limit middleware and per-member share cap as the audit subjects under NFR5-SEC-3 scenarios 5 + 6; the rest of the audit scope (scenarios 1–4) covers the cookie+JWT + CSRF + admin/IDOR surfaces from Init 0 baseline, with the auth-surface additions from E6 + E7 + E8 layered on top.

**Blocked by:** E6 + E7 + E8 complete (audit subjects exist).

**Critical property (encoded in this section as a load-bearing structural reminder for future agents):** E9 is an epic, NOT a story tacked onto the cutover. Multi-PR security batches from review docs are epics in disguise (per `feedback_default_to_bmad_workflow.md`). The sequencing — pay the audit cost before the LAN whitelist drops, not after — is the operator's banking-IT instinct encoded as a planning structure (brief §"What Makes This Special" property #2).

##### Story 9.1 — Audit tooling install + run baseline

**Realizes:** NFR5-SEC-1 (tooling foundation).
**Architectural anchor:** none (process / tooling).
**Depends on:** E6 + E7 + E8 complete.

Acceptance check shape:

- `bandit -r apps/api workers/render` runs clean (zero Critical / zero High; Medium-or-below allowed pending Story 9.3 disposition). Output saved as `_bmad-output/implementation-artifacts/audit-raw/bandit-YYYY-MM-DD.txt` (gitignored).
- `semgrep --config auto --config p/owasp-top-ten apps/api apps/web workers/render` runs; output saved as `audit-raw/semgrep-YYYY-MM-DD.json`.
- `pip-audit` (against `apps/api/pyproject.toml` + `workers/render/pyproject.toml`) + `npm audit --audit-level=moderate` (against `apps/web/package.json`) — outputs saved.
- OWASP ZAP active scan against `https://3d.ezop.ddns.net` post-deploy (with seeded test-member account + admin account credentials provided via authenticated-scan policy file). Output: `audit-raw/zap-YYYY-MM-DD.html`.
- All raw outputs aggregated into a single "Tools run summary" table in the audit report skeleton (created in Story 9.4).

##### Story 9.2 — Six-scenario audit coverage execution

**Realizes:** NFR5-SEC-3, audit verification of FR5-RATELIMIT-1 + FR5-RATELIMIT-2 + FR5-MEMBER-3.
**Architectural anchor:** Decisions G (rate-limit verification target), H (per-member share cap verification target).
**Depends on:** 9.1 (tooling installed).

Acceptance check shape — six scenarios per NFR5-SEC-3 + brief working assumptions, each producing a PASS / FAIL / MITIGATED row in the audit report with reproducer command preserved:

1. **Invite-token brute force:** scripted ≥10⁶-attempt loop against `POST /api/auth/register?token=<varying>` — Story 6.6 `register` rate-limit (3 attempts / 60s per IP) MUST reject before 256-bit entropy depletion by ≥10⁶ margin (trivially satisfied: 3 attempts × 60s per IP × 1 IP = 3 attempts per minute = ~4.3 attempts/day ≪ 256-bit search space). PASS criterion: HTTP 429 returned on 4th attempt within 60s.
2. **Refresh-token replay:** scripted replay of a recently-rotated `portal_refresh` against `POST /api/auth/refresh` — Init 0 family-rotation reuse-detection MUST trigger `auth.refresh.reuse_detected` and invalidate the entire family. PASS criterion: audit row emitted + subsequent refresh attempts on any token in the family return HTTP 401.
3. **CSRF / JWT tampering:** for each mutating endpoint introduced in E6 + E7 + E8, verify CSRF middleware rejects requests without `X-Portal-Client: web` header (HTTP 403 reason `csrf_missing`); for each cookie-issuing endpoint, verify a tampered JWT (re-signed or expired) returns HTTP 401. PASS criterion: 0 mutating endpoints accept a tampered/CSRF-stripped request.
4. **IDOR scan on `/api/admin/*`:** for each admin endpoint introduced in E6 + E8 (invite gen/list/revoke, user PATCH, user force-logout, force-2fa, password-reset), verify a member-authenticated request returns HTTP 403 (matches Decision C per-route allowlist). PASS criterion: 0 admin endpoints reachable by a member-role principal.
5. **Rate-limit verification on `/api/auth/login`:** `siege`/`hey` benchmark from one IP at 6+ failures/60s MUST trip HTTP 429 (matches Success Criterion #6 verbatim). PASS criterion: HTTP 429 returned on 6th call.
6. **Member share-link amplification (FR5-MEMBER-3):** scripted 21-share-creation burst from one member account — soft-alert log MUST emit at the 10th creation; hard-fail HTTP 429 MUST return on the 21st creation. PASS criterion: both signals observed.

Each scenario emits a reproducer command preserved as `audit-raw/scenario-N-reproducer.sh` so any subsequent audit can re-run the same verification.

##### Story 9.3 — Codex review countersignature per Medium disposition

**Realizes:** NFR5-SEC-2.
**Architectural anchor:** none (process control on top of `feedback_invoke_codex_directly.md`).
**Depends on:** 9.1 + 9.2 produced a Medium-findings list.

Acceptance check shape:

- For each Medium finding from 9.1 + 9.2, the disposition (`fixed` / `mitigated` / `accepted-with-rationale`) is documented in the audit report draft with the relevant patch SHA + a `codex review --commit <SHA>` invocation against that patch.
- The `codex review` output is captured (per `feedback_codex_review_invocation.md` — mode flag standalone OR `cat prompt.md | codex exec --sandbox read-only -`) and a one-line summary cited in the disposition row.
- "Accepted-with-rationale" Medium findings specifically get an explicit countersignature line in the audit report: `countersigned: codex review SHA=<commit>, date=<YYYY-MM-DD>` per NFR5-SEC-2 verbatim.
- Self-attestation mitigation rationale (operator is both auditor and gate-keeper) is documented in the audit report Methodology section as the compensating control alongside the max-3-Mediums cap.

##### Story 9.4 — Audit report authoring + gate-condition sign-off

**Realizes:** NFR5-SEC-1 (gate sign-off), FR5-AUDIT-1 (no new audit actions — the audit report itself is the artifact, not a `record_event` row).
**Architectural anchor:** none (output artifact); format mirrors Init 1 verify-symbolication / 2fa-recovery-drill artifact precedents for operator familiarity.
**Depends on:** 9.1 + 9.2 + 9.3 complete.

Acceptance check shape:

- `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` authored with: Title + Date + Auditor + Methodology section (citing tooling stack from 9.1, scenario coverage from 9.2, codex countersignature pattern from 9.3, single-operator self-attestation mitigation from NFR5-SEC-2) + Tools run summary table + Six-scenario coverage table (PASS / FAIL / MITIGATED per scenario) + Findings disposition table (one row per finding: severity / source / disposition / patch SHA / codex countersignature SHA where applicable) + Explicit Gate-condition decision line.
- Gate-condition decision line is one of: (a) `**E10 cleared to proceed** — gate condition PASS: zero open Critical/High findings; N accepted-rationale Mediums (N ≤ 3); audit complete on YYYY-MM-DD`, OR (b) `**E10 blocked, fix sprint required** — gate condition FAIL: <reason: M open Criticals OR P open Highs OR Q accepted-rationale Mediums (Q ≥ 4)>; triaging the following findings: <list>; audit reruns after fix sprint`.
- On PASS: E10 stories unblock per sequencing.
- On FAIL: the failing findings are triaged into a fix sprint (likely new E9.x or carry-over E9.x stories created via CC re-invocation per AGENTS.md vanilla-first subsection — NOT a procedural drift; CC is canonical for post-ship scope change including "this audit failed, what now"); audit reruns AFTER fix sprint closes; this Story is not considered closed until a PASS decision is signed off.
- Artifact committed to local `_bmad-output/` only (gitignored per `feedback_local_only_docs.md`).

#### Epic 10 — Edge cutover (atomic)

**Goal.** Atomic single-commit edit in the sibling nginx config repo (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`) dropping both `auth_basic` and the IP allowlist; preserve share + agent-runbook bypasses; execute a four-scenario post-reload smoke matrix against `.190`; execute a verified rollback drill (≤30s end-to-end) before the cutover is considered closed; close with a non-skip-prefixed commit in `3d-portal` (`docs/operations.md` cutover-date update) recording the cutover within `3d-portal` deploy history.

**Acceptance gate.** All four smoke scenarios PASS post-reload; rollback drill PASS (revert + reload + smoke re-run all-PASS, revert-the-revert + reload + smoke re-run all-PASS); closing commit landed; Initiative 5 considered complete here. **Strictly blocked by E9 audit PASS (NFR5-SEC-1 gate condition).** If at any point during execution a smoke scenario regresses post-reload, the rollback sequence executes immediately per Decision K (≤30s end-to-end).

**FRs / NFRs realized:** FR5-CUTOVER-1..3, NFR5-PERF-2, NFR5-CROSS-REPO-1..2, NFR5-INT-1..2 (verified through smoke scenarios + nginx-bypass preservation), NFR5-OBS-2 second artifact slot (`cutover-smoke-YYYY-MM-DD.md`).

**Architectural anchors:** Decisions J (smoke matrix definition + 4 scenarios + artifact format), K (nginx config diff + atomic single-commit + rollback sequence + pre-flight `nginx -t` gate + commit-message conventions + cross-repo skip-gate cascade).

**Blocked by:** **E9 audit PASS (NFR5-SEC-1 gate condition).** No bypass.

##### Story 10.1 — Pre-cutover fixture seeding + `cutover-smoke.sh` authoring

**Realizes:** FR5-CUTOVER-2 (smoke script foundation), NFR5-OBS-2 (artifact format).
**Architectural anchor:** Decision J (4-scenario table + artifact shape).
**Depends on:** E6 + E7 + E8 complete (test fixtures depend on member registration + invite generation surfaces); E9 audit PASS confirmed before this story starts.

Acceptance check shape:

- Three test fixtures seeded ≥24h before the cutover commit:
  - test-member account registered via panel-issued invite (E8 Story 8.6 generate-invite flow).
  - hourly cron-refreshed share-token (preserves through cutover; cron in `infra/scripts/cutover-share-token-refresh.sh` runs hourly on dev box; share token URL recorded for scenario 1).
  - minimal STL fixture (3KB sample model) added to fixture storage for agent POST scenario 2.
- `infra/scripts/cutover-smoke.sh` authored with: `set -euo pipefail` + dependency check (`jq curl`) + 4 sequential scenarios per Decision J table + per-scenario `http_code` + `request_id` + audit-row-delta capture + ANSI-colored PASS / FAIL output to stdout + stderr-narrative for errors + 30s wall-clock total budget + `--help` flag printing usage. Bash conventions match Init 1 § AR12.
- Smoke output template documents the artifact format (Markdown table with scenario / expected / actual / status / timestamp / request_id / audit delta columns) + Rollback drill timing block.
- Pre-flight script `infra/scripts/cutover-preflight.sh` (optional, operator-run before cutover) verifies all three fixtures are live and the smoke script self-test passes.

##### Story 10.2 — Sibling nginx commit authoring + pre-flight `nginx -t` gate

**Realizes:** FR5-CUTOVER-1.
**Architectural anchor:** Decision K (concrete diff + commit-message convention + pre-flight gate).
**Depends on:** 10.1 (smoke script ready to verify the cutover).

Acceptance check shape:

- Edit to `~/repos/configs/nginx/3d.ezop.ddns.net.conf` matches the Decision K concrete diff exactly: drop server-level `auth_basic "3d-portal"` + `auth_basic_user_file /etc/nginx/.htpasswd-portal` + `allow 192.168.2.0/24` + `allow 10.8.0.0/24` + `deny all`; drop per-location `auth_basic off;` + `allow all;` in both `location /share/` and `location /agent-runbook` (they become redundant once the server-level block is gone). The `proxy_pass` + `proxy_set_header` lines in every location block stay untouched.
- Sibling repo commit message: `feat(nginx): drop auth_basic + IP allowlist for 3d-portal cutover`. Conventional-commit `feat(nginx)` matches sibling repo style. Body references `3d-portal` issue + cutover artifact path + Decision K cross-reference.
- Pre-flight gate: `ssh .180 'sudo nginx -t'` MUST PASS BEFORE `git push origin main` in sibling repo. If `nginx -t` fails, the cutover is aborted before reload — no traffic disruption.
- The commit is NOT pushed in this story — Story 10.2 produces the commit locally + verifies syntax; Story 10.3 pushes + reloads + smokes atomically.

##### Story 10.3 — Atomic cutover execution + 4-scenario smoke run + rollback drill

**Realizes:** FR5-CUTOVER-2, FR5-CUTOVER-3, NFR5-PERF-2, NFR5-INT-1 (smoke scenario 2 verifies agent ingestion unchanged + nginx bypass preserved), NFR5-INT-2 (smoke scenario 1 verifies share bypass preserved), NFR5-CROSS-REPO-2 (rollback drill spans both repos), NFR5-OBS-2 (cutover-smoke artifact written).
**Architectural anchor:** Decisions J, K (executable rollback sequence).
**Depends on:** 10.2 (commit ready + nginx -t passing locally on .180), 10.1 (smoke script + fixtures ready).

Acceptance check shape:

- Cutover sequence (sequential, total ≤5 minutes per NFR5-PERF-2):
  1. `git push origin main` in sibling repo (`~/repos/configs/`).
  2. `ssh .180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'` — `nginx -t` MUST PASS again on the freshly-pulled commit; reload executes atomically.
  3. `bash infra/scripts/cutover-smoke.sh` against `https://3d.ezop.ddns.net` — all 4 Decision J scenarios MUST PASS within ≤30s total wall-clock.
  4. Rollback drill: `cd ~/repos/configs && git revert <cutover-sha> --no-edit && git push origin main` → `ssh .180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'` → re-run smoke script → all 4 PASS confirms rollback works → `git revert <revert-sha> --no-edit && git push origin main` → `ssh .180` reload → re-run smoke script → all 4 PASS confirms re-apply works.
- Any FAIL in step 3 triggers immediate rollback per the same Decision K sequence (≤30s end-to-end) without proceeding to step 4 drill.
- Cutover-smoke artifact `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` (NFR5-OBS-2 second slot) captures: per-scenario timestamps + request IDs + audit-row deltas (from scenarios 2, 3, 4 audit emissions) + rollback drill timing block (revert-reload-smoke-revert-reload-smoke total wall-clock) + cutover commit SHA + revert commit SHA + revert-the-revert commit SHA.
- Artifact committed to local `_bmad-output/` only (gitignored).

##### Story 10.4 — Closing `docs/operations.md` cutover-date commit in `3d-portal`

**Realizes:** NFR5-CROSS-REPO-1 (records cutover in `3d-portal` deploy history; bypasses `deploy.sh` skip-gate via non-skip prefix).
**Architectural anchor:** Decision K (cascading note on deploy-history closing commit).
**Depends on:** 10.3 (cutover landed and stable).

Acceptance check shape:

- Edit to `docs/operations.md` adds a new section describing the post-cutover portal-self-auth posture: nginx is now a thin TLS terminator + share-bypass rewrite layer; portal authenticates itself via cookie+JWT; `member` role is invite-only via admin panel; 2FA enforcement is per-role config-flag-driven with `agent` role permanently excluded; rate-limit middleware protects the login / refresh / register / share surfaces; cross-references to `security-audit-YYYY-MM-DD.md` + `cutover-smoke-YYYY-MM-DD.md` + `2fa-recovery-drill-YYYY-MM-DD.md`.
- Commit message: `feat(infra): record edge cutover date 2026-MM-DD` (Conventional Commits `feat(infra)` — NON-skip-prefix per `bf919c2`/`0745209` skip-gate; the commit fires `deploy.sh` and records the cutover SHA in `infra/.last-deploy-sha`, surfacing the cutover within `3d-portal` deploy history per Decision K cascading note + `feedback_auto_deploy_dev.md` deploy invariant).
- Commit body references the sibling cutover commit SHA + the cutover-smoke + security-audit artifact paths.
- Auto-deploy fires per `feedback_auto_deploy_dev.md`; deploy is null-op for application code (no code changed) but updates `infra/.last-deploy-sha` to anchor future deploy-gate behavior at the post-cutover SHA.
- Initiative 5 considered complete at the merge of this commit. Retrospective (`bmad-retrospective`) scheduled as the next session per CC §5.2 handoff plan.

### Cross-references

- **Brief v2** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines; adversarial-review applied: P0×2 + P1×3 + P2×1 fixed). Binding content source for FR / NFR shape + working assumptions + Success Criteria + Vision trajectory.
- **Brief distillate** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5688 tokens, LLM-optimized).
- **Sprint Change Proposal** — `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Doc-shape (single-file H2-append per §3.3 + §4.1), epic numbering (global E6-E10 per §3.4), per-artifact content outline (§4.2 2C governs this section), per-epic effort + risk estimates (§4.4), hard rules carried forward (§5.6).
- **PRD § Initiative 5** — `prd.md` lines 1065-1258 (24 FRs across 8 prefix groups + 12 NFRs across 6 categories). Each Story above cites one or more FR5-* / NFR5-* IDs the Story realizes. Forward reference from PRD: FR5-RATELIMIT-1 → Decision G → Story 6.6; FR5-CUTOVER-1 → Decision K → Stories 10.2 + 10.3.
- **Architecture § Initiative 5** — `architecture.md` lines 1399-1767 (Decisions A–K in-scope; L–N deferred). Each Story above cites one or more Decision letters as its architectural anchor. Forward references in architecture.md to this section: each Decision's "Cascading" note points to the realizing epic / story scope.
- **Sprint status** — `_bmad-output/implementation-artifacts/sprint-status.yaml` — to be extended in Session F via `bmad-sprint-planning` with `epic-6` ... `epic-10` keys + 27 per-story entries (status `backlog` on creation; status transitions per Init 0/1/2/3 precedent).
- **Implementation Readiness check** — to be authored in Session E via `bmad-check-implementation-readiness` (gates Session F sprint-planning); covers PRD ↔ UX ↔ Architecture ↔ Epics alignment across all five initiatives (Init 0/1/2/3 + Init 5; Init 4 reverted per `bf919c2`).
- **Init 0 baseline anchors:** auth stack (Init 0 § Auth module + `apps/api/app/core/auth/`), share-token Redis pattern (Init 0 § Share module + `apps/api/app/modules/share/`), audit log (Init 0 § Admin module + `apps/api/app/core/audit/` + `KNOWN_ENTITY_TYPES` registry), role enum (`apps/api/app/core/db/models/_enums.py:10-13` — `member` already enumerated). Init 5 is purely additive on these anchors; no Init 0 contract changes.
- **Init 1 baseline anchors:** GlitchTip plumbing (`apps/web/src/instrument.ts` + `JsonFormatter`) — NFR5-OBS-1 reuses this surface for all Init 5 namespaced loggers (`app.auth.invite`, `app.auth.totp`, `app.auth.register`, `app.admin.users`, `app.share.ratelimit.soft_alert`); bash script conventions (Init 1 § AR12) — Stories 7.6, 9.x, 10.1, 10.3 cutover-smoke + drill scripts follow this pattern.
- **Init 2 baseline anchors:** `agent` service account contract — NFR5-INT-1 preserves this exactly (Stories 7.4 startup fail-fast + 10.3 smoke scenario 2 + 10.3 nginx-bypass preservation).
- **Init 3 baseline anchors:** visual-regression matrix (4 projects: desktop-light / desktop-dark / mobile-light / mobile-dark) + Init 3 Principle 3 (UI changes ship with own baseline updates in same commit) — Stories 6.4, 7.2, 7.3, 8.2, 8.3, 8.4, 8.5, 8.6 each note "visual-regression baselines added in same commit"; axe-contrast scans active per Init 3 ESLint + Stylelint integration extend automatically to new admin pages + register / 2FA / reset-password screens.
- **Memory entries informing decisions:** `feedback_default_to_bmad_workflow.md` (E9 as epic-not-story discipline; multi-PR security batches are epics in disguise), `feedback_auto_deploy_dev.md` (Story 10.4 closing commit deploy invariant), `feedback_vanilla_bmad_first.md` v2 (monolithic H2-append pattern justification for this manual edit per `bmad-edit-epics` no-skill path), `feedback_bmad_skill_discovery_checklist.md` (session-start `bmad-help` confirmed manual edit canonical), `feedback_invoke_codex_directly.md` (Story 9.3 codex review countersignature mechanism), `feedback_local_only_docs.md` (drill + smoke + audit artifacts gitignored per `_bmad-output/` convention), `feedback_collaboration_division.md` (operator-driven content decisions encoded as locked Brief + PRD + Architecture inputs to this section; agent does NOT re-elicit closed decisions).
- **Out-of-scope reminders (Decisions L–N deferred + brief Q5 + PRD § "Out"):** self-service mail-based password reset (Decision L; blocked on self-hosted mail server initiative), OIDC/SSO federation (Decision M; brief Q5 confirmed non-goal), per-model ACL (Decision N; brief Q5 confirmed non-goal), social login, team accounts, user-to-user messaging, public read-only browse, email deliverability verification, webhook push, multi-tenant. Future initiatives may revisit (see Decision-letter "Where it goes" pointers in architecture.md).

## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20). Source PRD section: `prd.md` § "Initiative 6" (FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + 7 NFRs). Source architecture section: `architecture.md` § "Initiative 6" (Decisions M, N, O). Single Epic E11 with 7 stories.

**Init 5 unchanged.** Initiative 6 is purely additive — drift correction + endpoint redesign for share + frontend topology shift. No Init 5 epic retro-modification; Init 5 retro stays closed at `2429157`. Initiative 6's relationship to Init 5 is `bug-fix-scope-expansion`, not `supersession`.

### Overview

Single epic E11. Sequence: 11.1 (backend default-deny gating + agent contract) → 11.2 (share-scoped asset endpoint + share-router refactor) → 11.3 (frontend shell-level AuthGate + P2 `searchStr` fix) → 11.4 (route enforcement gate — pytest enumeration + `_PUBLIC_ROUTES` allowlist constant) → 11.5 (audit re-run with Scenario 4 extended to ALL `/api/*`) → 11.6 (cutover-smoke automation: external-host probe) → 11.7 (sibling nginx allowlist rollback + `docs/operations.md` cutover-date update). Stories 11.5 + 11.6 are GATE before Story 11.7 — audit + drill must PASS before the sibling allowlist comes off.

**Audit gate condition (NFR6-SEC-1):** identical to Init 5 NFR5-SEC-1 — zero open Critical/High; ≤3 accepted-rationale Mediums; 4th forces auto-fail + fix sprint. **Pre-merge codex review (NFR6-SEC-3) for Stories 11.1, 11.2, 11.3** — auth-boundary contracts get peer review BEFORE merge to catch the cognitive pattern that produced hot-fix 64447ff.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E11 | Post-cutover default-deny auth posture | 7 (11.1–11.7) | Medium | **High** (security boundary; pre-merge codex review on 11.1, 11.2, 11.3) | FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + NFR6-SEC-1..3, NFR6-PERF-1, NFR6-INT-1, NFR6-CROSS-REPO-1, NFR6-OBS-1 | none (entry epic) |

**Total: 7 stories** planned. Effort: 3–5 days back-to-back autonomous execution (mirrors Init 5 Story 10.x rate at ~1 story/4-8h with codex review intercept).

### Epic 11 — Post-cutover default-deny auth posture

**Goal.** Implement what Init 5 Decision C already specified (default-deny `/api/*` with explicit anonymous allowlist), add mechanical enforcement so the drift class cannot recur, redesign share-asset URL contract to make anonymous bypass explicit at the URL prefix level, hoist frontend AuthGate to shell level so anonymous users see only the login surface, re-run audit with Scenario 4 covering ALL `/api/*` (not just `/api/admin/*`), automate the external-host probe that Story 10.3 deferred to operator manual verification, and roll back the temporary sibling nginx allowlist (`70cb5ba`) once audit + drill PASS.

**Acceptance gate.** End-to-end drill on `.190`:
1. `curl https://3d.ezop.ddns.net/api/categories` from non-LAN host → 401 (was 200 pre-Init-6).
2. `curl https://3d.ezop.ddns.net/api/share/{valid-token}/files/{valid-file-id}/content` from non-LAN host → 200 with file body.
3. Agent service-account `hydrate_local_tree.py` runbook end-to-end completes without 403 on any pre-flight call.
4. Anonymous user navigating to `https://3d.ezop.ddns.net/` is redirected to `/login?next=%2F` (no module rail, no top bar).
5. Story 11.5 audit produces fresh `security-audit-2026-MM-DD.md` with Scenario 4 covering enumerated routes, gate-condition PASS.
6. Story 11.7 sibling configs revert deployed, `nginx -s reload` smoke verified — external anonymous still 401 (now via portal auth, not nginx allowlist).

**Pre-merge codex review (NFR6-SEC-3):** Stories 11.1, 11.2, 11.3 cannot merge until `codex review --commit <SHA>` returns no P1 findings or P1 findings are addressed in follow-up commits. Story 11.4, 11.5, 11.6, 11.7 follow standard post-merge codex review pattern.

**FRs realized:** FR6-AUTH-1, FR6-AUTH-2, FR6-SHARE-1, FR6-SHELL-1, FR6-SHELL-2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1.

**Architectural anchors:** Decisions M, N, O. Init 5 Decision C clarifying note (architecture.md ~line 1494) is the bridge between Init 5 intent and Init 6 enforcement.

**Blocked by:** none. Operator-confirmed business intent + non-negotiable D-LOCKs (D-LOCK-1..5 per SCP §3.3).

##### Story 11.1 — Backend default-deny gating on SoT + agent contract preserved

**Realizes:** FR6-AUTH-1 (partial; gating clauses), FR6-AGENT-1, NFR6-INT-1.
**Architectural anchor:** Decision M (partial — non-test side of gating); Init 5 Decision C verbatim (implement what's specified).
**Depends on:** none (E11 entry story).
**Pre-merge codex review:** REQUIRED (NFR6-SEC-3).

Acceptance check shape:

- `apps/api/app/modules/sot/router.py`: all 6 GET endpoints get `_user_id: uuid.UUID = current_user` (NOT `current_member_or_admin` — that was the hot-fix 64447ff bug). Endpoint description text updated to "Requires authenticated user (any role). Initiative 6 default-deny posture; see architecture.md § Initiative 6 Decision M for `_PUBLIC_ROUTES` allowlist."
- `apps/api/tests/test_sot_*.py`: scenarios added for anonymous → 401, member → 200, admin → 200, **agent → 200** (NFR6-INT-1 verification). The agent-200 case is the explicit regression test for hot-fix 64447ff's P1-2.
- `apps/api/tests/test_hydrate_local_tree.py`: pre-set cookie auth on TestClient before `run_hydrate()` invocation (mirrors the test-fix attempted in 64447ff, but with `current_user` semantics → agent cookie path works without role-blocking).
- `infra/scripts/audit-six-scenarios.sh` Scenario 2 (agent ingestion): reproduces post-fix that agent cookie reaches `/api/categories` returning 200. No P1-2 regression.

##### Story 11.2 — Share-scoped asset endpoint + share-router refactor (hardened per Codex peer-grill)

**Realizes:** FR6-SHARE-1, NFR6-OBS-1, NFR6-INT-1 (share bypass preservation).
**Architectural anchor:** Decision N (hardened — see SCP §3.4.2 + §4.2.2 for the six Codex hardenings; this story honors all six).
**Depends on:** 11.1 (default-deny lays the ground; share-scoped asset endpoint is the explicit anonymous bypass).
**Pre-merge codex review:** REQUIRED (NFR6-SEC-3).

Acceptance check shape:

**Implementation:**

- New route `GET /api/share/{token}/files/{file_id}/content` in `apps/api/app/modules/share/router.py` per Decision N implementation block (verbatim or near-verbatim, all 6 hardenings honored).
- `share-router.py` resolve handler refactored: lines 55, 59, 70 emit `/api/share/{token}/files/{fid}/content` URLs instead of `/api/models/{m}/files/{f}/content`.
- New audit event `share.asset.fetched` emitted on successful fetch with `target_token_hash` (sha256 hex), `target_model_id`, `target_file_id`, `target_file_kind`, `ip` fields. **Token-hash, NEVER clear token.**
- `apps/api/app/core/logging.py`: token-redaction regex extended to match `/api/share/<token>/...` path segments. Negative test: log record containing `/api/share/abc123/files/x/content` emits with `/api/share/<redacted>/files/x/content`.
- `_serve_file_content` helper extended with `cache_control` parameter (or new sibling helper); share-asset response uses `Cache-Control: no-store`.

**Test coverage — share-asset IDOR matrix (Codex-required, verbatim):**

1. `test_anon_valid_token_valid_file_returns_200` — token A + file A (kind=image) returns 200 with file body
2. `test_anon_valid_token_wrong_model_file_returns_404` — token A + file B (file from model B, different from token-bound model A) returns 404 (NOT 403 — uniform error shape)
3. `test_anon_valid_token_non_shareable_kind_returns_404` — token A + file C (file from model A, but kind=`source` or `archive_3mf`) returns 404
4. `test_anon_revoked_token_returns_404` — token revoked via existing revoke flow; subsequent fetch returns 404
5. `test_anon_expired_token_returns_404` — token past Redis TTL; subsequent fetch returns 404
6. `test_anon_soft_deleted_model_returns_404` — model.deleted_at IS NOT NULL; subsequent fetch returns 404
7. `test_anon_garbage_token_returns_404` — request with non-existent token returns 404 (no timing oracle vs valid-token-wrong-file)
8. `test_audit_row_present_on_success` — successful fetch emits `share.asset.fetched` with `target_token_hash = sha256(token).hexdigest()`, clear token absent from audit payload
9. `test_audit_row_present_on_fail` — failed fetch (any of #2-#7) emits `share.asset.fail` with reason field (audit row has fail-reason but NO clear-token disclosure)
10. `test_cache_control_no_store` — successful response includes `Cache-Control: no-store` header
11. `test_etag_not_used_for_share_asset` — share-asset endpoint does NOT emit ETag header (would short-circuit scope check on 304 path)
12. `test_logging_redaction_path_token` — log record containing path-with-token emits with token segment replaced by `<redacted>`

**Cross-validation tests (against Story 11.1 default-deny posture):**

- `test_authenticated_member_models_files_content_returns_200` — proves `/api/models/{m}/files/{f}/content` still works for authenticated principal (Story 11.1's scope; verified here to ensure cross-flow consistency)
- `test_anon_models_files_content_returns_401` — proves `/api/models/...` is 401 anonymous post-Initiative 6 (no leak through legacy URL)
- `test_share_resolve_emits_share_scoped_urls` — calls `GET /api/share/{valid-token}` and asserts each `images`, `thumbnail_url`, `stl_url` returned URL starts with `/api/share/`, NOT `/api/models/`. **This is the test that would have caught hot-fix 64447ff at code-review time** had it existed (Codex's cognitive-pattern-property check, SCP §3.4.2).

**Frontend changes:**

- `apps/web/src/modules/share/...` (TBD module-name during Story 11.2; possibly `apps/web/src/routes/share/$token.tsx`): consumes new share-scoped URLs returned by share-resolve API. No URL-shape assumption in frontend — relies on backend-returned strings.
- Visual regression test: anonymous share-recipient view at `/share/{token}` renders thumbnail + 3D viewer correctly with new URLs (4-project matrix per project-context.md).

##### Story 11.3 — Frontend shell-level AuthGate + P2 `searchStr` fix

**Realizes:** FR6-SHELL-1, FR6-SHELL-2.
**Architectural anchor:** Decision O.
**Depends on:** 11.1 (backend default-deny in place; frontend redirect on 401 is the UX surface).
**Pre-merge codex review:** REQUIRED (NFR6-SEC-3).

Acceptance check shape:

- `apps/web/src/shell/AppShell.tsx` implements the Decision O code block (verbatim or near-verbatim).
- `apps/web/src/shell/AuthGate.tsx`: `searchStr` (not `search`) used when constructing `next` URL. Component may remain as a thin wrapper for legacy callers OR be deleted if no caller remains post-refactor.
- Per-route `<AuthGate>` wrappers removed from `apps/web/src/routes/*.tsx` (audit grep confirms no remaining usage after refactor).
- Anonymous user visiting `https://3d.ezop.ddns.net/catalog?category_id=xyz` is redirected to `https://3d.ezop.ddns.net/login?next=%2Fcatalog%3Fcategory_id%3Dxyz` — URL-encoded, no `[object Object]` artifacts.
- `apps/web/tests/visual/anon-login-only.spec.ts`: visual regression test — anonymous user at `/`, `/catalog`, `/admin/users`, `/profile` all render the login page only (no ModuleRail, no TopBar). 4-project matrix (desktop-light/dark, mobile-light/dark) per project-context.md UI testing rules.
- `apps/web/src/locales/{en,pl}.json`: any new i18n keys for the login surface added to both.

##### Story 11.4 — Route enforcement gate (pytest enumeration + `_PUBLIC_ROUTES` allowlist)

**Realizes:** FR6-AUTH-1, FR6-AUTH-2, NFR6-PERF-1.
**Architectural anchor:** Decision M.
**Depends on:** 11.1, 11.2 (the routes whose auth posture the test asserts are in place).

Acceptance check shape:

- `apps/api/app/main.py` (or `apps/api/app/core/auth/dependencies.py`): `_PUBLIC_ROUTES` constant defined per Decision M code block.
- `apps/api/tests/test_route_enforcement_gate.py`: iterates `app.routes`, filters `/api/`-prefixed routes, asserts each route's endpoint signature contains at least one parameter with `Depends(current_*)` default OR matches `_PUBLIC_ROUTES`. Test runs in <1s (NFR6-PERF-1). Test failure message names the offending route specifically.
- Add deliberate negative-test story-internal verification: temporarily remove `current_user` from one SoT GET handler → run pytest → assert the enforcement test fails with the expected message. Then restore.
- `docs/operations.md` documents the test in the testing checklist section.

##### Story 11.5 — Audit re-run with Scenario 4 extended to ALL `/api/*`

**Realizes:** FR6-AUDIT-RERUN-1, NFR6-SEC-1, NFR6-SEC-2.
**Architectural anchor:** none (audit tooling — re-execution of Init 5 NFR5-SEC-1 process).
**Depends on:** 11.1, 11.2, 11.3, 11.4 (the auth contract that the audit asserts has shipped; the enforcement test must exist for cross-validation).

Acceptance check shape:

- `infra/scripts/audit-six-scenarios.sh` Scenario 4 reworked: enumerates `/api/openapi.json` route table (or equivalent), iterates each route as anonymous (expected: 401 except `_PUBLIC_ROUTES` → 200/400/422 per route shape) + as `member`-authenticated (expected: 200/201/403 per route's posture). Scenario 4 output is a per-route status table.
- Audit re-run produces `security-audit-2026-MM-DD.md` (new date — likely 2026-05-22 or later) with gate-condition section verbatim mirroring Init 5 NFR5-SEC-1 shape: zero open Critical/High, ≤3 accepted-rationale Mediums, 4th forces auto-fail.
- Per-Medium codex review countersignature per NFR6-SEC-2 (mirrors NFR5-SEC-2). Stories 11.1, 11.2, 11.3 commits cited in the audit's "Patch SHA" column (these are the new commits the audit covers).
- Gate condition PASS → unlocks 11.6 + 11.7.

##### Story 11.6 — Cutover-smoke automation: external-host probe

**Realizes:** FR6-CUTOVER-PROBE-1.
**Architectural anchor:** none (smoke script extension; mirrors Init 5 Decision J).
**Depends on:** 11.5 (audit-passed deployed state to probe).

Acceptance check shape:

- `infra/scripts/cutover-smoke.sh` extends with Scenario 5: `curl -fsS -o /dev/null -w "%{http_code}" https://3d.ezop.ddns.net/api/categories` from a non-LAN source. Source TBD: CI runner (if GitHub Actions ever lands), public VPS (operator already has one for monitoring), or mobile-data network on operator's laptop tether (one-shot verification).
- Scenario 5 expected: 401. Fails the smoke run if external host returns 200.
- Updated `cutover-smoke-YYYY-MM-DD.md` artifact format includes Scenario 5 row.
- Story documents the choice of external-host source in `docs/operations.md`.

##### Story 11.7 — Sibling nginx allowlist rollback + closing cutover-date update

**Realizes:** NFR6-CROSS-REPO-1, completes Initiative 6.
**Architectural anchor:** Init 5 Decision K rollback shape (this story is the analogue revert).
**Depends on:** 11.5 (audit PASS), 11.6 (external-host probe PASS).

Acceptance check shape:

- `~/repos/configs/` sibling repo: revert commit `70cb5ba` (temporary IP allowlist) via `git revert 70cb5ba`. Verify pre-deploy with `sudo nginx -t` on `.180`. Deploy via sibling repo's `sync.sh` (or equivalent — same mechanism as Init 5 Story 10.3 cutover sibling deploy).
- `nginx -s reload` on `.180`.
- Re-execute `infra/scripts/cutover-smoke.sh` (now including Scenario 5 from 11.6). All 5 scenarios PASS.
- `docs/operations.md`: cutover-date paragraph updates from `2026-05-20` (Init 5 cutover) to also reference `2026-MM-DD` (Initiative 6 final cutover). Non-skip-prefixed commit message (`feat(infra): record Initiative 6 cutover date 2026-MM-DD`) to fire `deploy.sh` and advance `infra/.last-deploy-sha`. This is the Init 5 NFR5-CROSS-REPO-1 mirror for Initiative 6.
- Update Sprint Change Proposal status: `approved` → `done` in YAML frontmatter; `Initiative 6 COMPLETE` line appended.
- Retrospective story spawned in fresh context (`bmad-retrospective` skill) for Initiative 6 close-out.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20).
- PRD section: `prd.md` § Initiative 6.
- Architecture section: `architecture.md` § Initiative 6 (Decisions M, N, O).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via `bmad-sprint-planning` (epic-11 + 11.1–11.7 status `backlog`).
- Predecessor: Initiative 5 (Public Registration & User Account Management) — closed 2026-05-20 `7e5aea0` + retro `2429157`.
- Codex peer-grilling pattern: see [[invoke-codex-directly]] + Init 5 NFR5-SEC-2 (mandatory for security-boundary stories per NFR6-SEC-3).
- Memory entries informing this initiative: [[itcm-autonomous-mode]] (frame-shift before drafting 2026-05-20 addition), [[auth-boundary-contract-audit]] (NEW 2026-05-20 — explicit enumeration phase for auth-boundary commits + SCP recommendations), [[invoke-codex-directly]] (Codex peer-grilling for Decision N share-asset trade-off), [[vanilla-bmad-first]] v2 (monolithic H2-append pattern for this section).
- Production state checkpoints: SCP §1.4 production state table.

## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 7" (FR7-ADMIN-INVITES-1..3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1..2, FR7-SESSIONS-1..2 + NFR7-UX-1, NFR7-A11Y-1, NFR7-COMPAT-1). Source architecture section: `architecture.md` § "Initiative 7" (Decision Q). Single Epic E12 with 5 stories.

**Init 5 + 6 unchanged.** Initiative 7 is purely additive polish on shipped surfaces. No Init 5/6 epic retro-modification.

### Overview

Single epic E12 with 5 stories. Sequence: 12.1 (Admin Invites unblock — nav tab + translations + table layout) → 12.2 (Admin Users inactive-filter) → 12.3 (Display name on registration + self-service edit) → 12.4 (Settings hub + 2FA discoverability + user-menu link) → 12.5 (Sessions UX — pagination + sort + UA-filter). Stories 12.3 and 12.4 share the new `/settings/profile` route surface (12.3 creates it, 12.4 wires the hub link); 12.3 → 12.4 sequencing is recommended but not strict.

Each story carries NFR7-UX-1 (pre-CR visual verification gate) as a mandatory non-functional acceptance criterion.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E12 | Account & Admin UX Polish | 5 (12.1–12.5) | Medium | Low (no security boundary, no schema risk; mostly component-level changes on shipped surfaces) | FR7-ADMIN-INVITES-1..3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1..2, FR7-SESSIONS-1..2 + NFR7-UX-1, NFR7-A11Y-1, NFR7-COMPAT-1 | depends on Initiative 9 (E14) completion — E14 unblocks admin test surfaces for Stories 12.1, 12.2 (and 12.3, 12.5 indirectly) |

**Total: 5 stories.** Effort estimate: 2–3 days back-to-back autonomous execution (~½–1 day per story, faster than Init 6 auth-boundary stories due to lower risk profile).

### Epic 12 — Account & Admin UX Polish

**Goal.** Raise five user-facing surfaces (admin invites, admin users, registration, settings discoverability, active sessions) from minimum-viable to operator-acceptable UX. Bake in the new pre-CR visual-verification gate as a procedural fix for the Init 6 admin-invites shipping incident class.

**Acceptance gate.**

1. `/admin/invites` nav tab is enabled for admin role; clicking it routes to the existing page; page renders complete pl/en translations; table fits viewport at desktop default and mobile-light.
2. `/admin/users` defaults to `is_active=true` rows; "Pokaż nieaktywne konta" checkbox toggle shows all rows.
3. Registration form has optional display-name field with auto-suggest from email prefix; backend accepts display_name; `/settings/profile` allows self-service edit.
4. `/settings` hub exists with three section entries (Profile, 2FA, Sessions); user-menu in TopBar has "Settings" link.
5. `/settings/sessions` paginates at default 20/page, sorts by `last_used_at DESC` default, has "Pokaż API/non-browser sesje" checkbox toggle (default OFF — filters curl/non-browser UA patterns).
6. Each story (12.1–12.5) has agent-browser snapshots at desktop-default + mobile-light viewports attached to Dev Agent Record.

**FRs realized:** FR7-ADMIN-INVITES-1, FR7-ADMIN-INVITES-2, FR7-ADMIN-INVITES-3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2, FR7-SESSIONS-1, FR7-SESSIONS-2.

**Architectural anchors:** Decision Q (Initiative 7 — settings hub topology).

**Blocked by:** Initiative 9 (E14) — closes admin test surfaces before E12 stories begin. Operator-confirmed business intent (display name option A; default-OFF inactive filter; default-OFF API/non-browser session filter). Other technical choices ITCM-delegated.

##### Story 12.1 — Admin Invites unblock (nav tab + translations + table layout)

**Realizes:** FR7-ADMIN-INVITES-1, FR7-ADMIN-INVITES-2, FR7-ADMIN-INVITES-3, NFR7-UX-1.
**Architectural anchor:** none (component-level).
**Depends on:** Story 14.1 (admin vitest finder fixes) + Story 14.3 (visual-regression hook flake) — both unblock the admin module test signal.

Acceptance check shape:

- `apps/web/src/modules/admin/AdminTabs.tsx`: invites entry changes from `<span aria-disabled="true" cursor-not-allowed opacity-50>` to a `<Link to="/admin/invites">` with the same styling as other admin tabs.
- `apps/web/src/locales/pl.json` + `apps/web/src/locales/en.json`: full key set for admin invites page added (key list enumerated during spec phase by reading the existing `InvitesPage.tsx` + child components and pulling every `t("admin.invites.*")` call). Parity between pl and en.
- Admin invites table layout: max-width on container, left-margin compressed to match other admin pages, horizontal scroll if needed for mobile viewport.
- Visual smoke per NFR7-UX-1: agent-browser snapshot at desktop-default + mobile-light. Verify nav-tab enabled, no raw i18n keys, table fits.

##### Story 12.2 — Admin Users inactive-filter (default-hide + checkbox toggle)

**Realizes:** FR7-ADMIN-USERS-1, NFR7-A11Y-1 (checkbox keyboard reach).
**Architectural anchor:** none.
**Depends on:** Story 14.1 (admin vitest finder fixes) + Story 14.3 (visual-regression hook flake on admin-users baseline).

Acceptance check shape:

- `apps/web/src/modules/admin/UsersPage.tsx`: add `is_active` filter state, default `true`. Add checkbox below page header: "Pokaż nieaktywne konta" / "Show inactive accounts", default unchecked. Checked → query without `is_active` filter (returns all). Unchecked → query with `is_active=true`.
- Backend: verify `apps/api/app/modules/admin/router.py` users-list endpoint accepts `is_active` query param. If not, extend (small change — likely adds `is_active: bool | None = None` to existing query).
- Inactive rows when shown: muted visual style (e.g. text-muted-foreground theme token).
- Visual smoke per NFR7-UX-1.

##### Story 12.3 — Display name on registration + self-service edit

**Realizes:** FR7-REG-DISPLAY-1, NFR7-A11Y-1.
**Architectural anchor:** none (the new `/settings/profile` route is component-level under Decision Q's hub topology).
**Depends on:** Story 14.2 (pytest hydrate isolation — User model touch surfaces share test infrastructure).

Acceptance check shape:

- Registration form (path TBD during spec — likely `apps/web/src/routes/auth/register.tsx`): add optional `display_name` text field below email. On email blur, populate display-name field with email prefix if empty.
- Backend `POST /api/auth/register`: accept optional `display_name` in request body; if absent, fall back to email prefix server-side.
- New route `apps/web/src/routes/settings/profile.tsx`: form to edit display_name. PATCH (or PUT) to a new endpoint `PATCH /api/auth/me/display-name` (or extend existing self-service user endpoint if exists). Auth: `current_user`.
- Verify `User.display_name` field already exists in `apps/api/app/core/db/models.py`. If not, add Alembic migration.
- Visual smoke per NFR7-UX-1.

##### Story 12.4 — Settings hub + 2FA discoverability + user-menu link

**Realizes:** FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2, NFR7-A11Y-1.
**Architectural anchor:** Decision Q.
**Depends on:** 12.3 (sequential — 12.3 creates `/settings/profile`, 12.4 wires the hub link to it). If 12.3 not yet shipped, 12.4 can ship the hub with only 2FA + Sessions entries and add Profile entry in a follow-up.

Acceptance check shape:

- New route `apps/web/src/routes/settings/index.tsx`: hub landing with three cards (Profile, 2FA, Sessions). Each card has i18n title + brief description (i18n key set added to pl/en).
- `apps/web/src/shell/TopBar.tsx` (or wherever user-menu lives): add "Settings" entry to user-menu dropdown, routing to `/settings`. i18n key added.
- Anonymous user redirect: `/settings` is shell-AuthGate protected per Init 6 FR6-SHELL-1 (no change needed in this story — already covered).
- Visual smoke per NFR7-UX-1 — emphasis on user-menu visibility and hub landing render.

##### Story 12.5 — Sessions UX (pagination + sort + UA-filter)

**Realizes:** FR7-SESSIONS-1, FR7-SESSIONS-2, NFR7-A11Y-1.
**Architectural anchor:** none.
**Depends on:** Story 14.2 (pytest hydrate isolation — Session endpoint test surface shares conftest).

Acceptance check shape:

- `apps/web/src/routes/settings/sessions.tsx`: wire `offset` + `limit` query params to existing `/api/auth/sessions` endpoint (backend already accepts them). Page-size selector (default 20, options 10/20/50). Prev/next page controls. Total-count indicator.
- Sort: default `last_used_at DESC`. Backend may already do this; verify during spec.
- UA-filter checkbox "Pokaż API/non-browser sesje" / "Show API/non-browser sessions". Default OFF. Filter pattern: TBD during spec — likely a list of substrings (e.g. `curl/`, `python-requests/`, `httpie/`, `wget/`, `Go-http-client/`, plus check for absence of common browser markers like `Mozilla/`, `Chrome/`, `Safari/`). Filter applied client-side OR server-side — TBD during spec.
- Visual smoke per NFR7-UX-1.

### Cross-references

- PRD: `prd.md` § Initiative 7.
- Architecture: `architecture.md` § Initiative 7 (Decision Q).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-12.

## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 8" (FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1..3 + NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1). Source architecture section: `architecture.md` § "Initiative 8" (Decision P). Single Epic E13 with 2 stories.

**Init 0 + 5 + 6 unchanged.** Initiative 8 is purely additive — catalog read-surface UX polish + new thumbnail pipeline layer.

### Overview

Single epic E13 with 2 stories. Sequence: 13.1 (Mobile carousel arrows — small CSS fix) → 13.2 (Thumbnail pipeline — backend pipeline + endpoint + frontend srcSet + backfill script). 13.1 is faster ship-day-1; 13.2 is the bigger cross-cutting story.

Each story carries NFR8-UX-1 (pre-CR visual verification gate). Story 13.2 also has NFR8-PERF-1 backend payload-size budget.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E13 | Catalog Mobile & Image Performance | 2 (13.1, 13.2) | Medium-Low | Low (no security boundary; Pillow is well-trodden) | FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1 | depends on Initiative 9 (E14) — Story 13.2 ModelFile test surface shares pytest conftest with Story 14.2 |

**Total: 2 stories.** Effort estimate: 1–2 days back-to-back autonomous execution (13.1 is hours; 13.2 is ~1 day with backend + frontend + backfill + tests).

### Epic 13 — Catalog Mobile & Image Performance

**Goal.** Make catalog list-page usable on mobile (visible carousel arrows) and bandwidth-friendly (thumbnail variants instead of full-res 8K photos). Establish the thumbnail pipeline as future-extensible (variant param can grow to cover other size targets if needed).

**Acceptance gate.**

1. Catalog list page on mobile (≤sm breakpoint) shows prev/next arrow buttons on each card carousel; desktop hover behavior preserved.
2. Image-kind file upload generates `.thumb.webp` variant within 30s; thumbnail file size ≤50 KB for typical phone photos.
3. `GET /api/models/{model_id}/files/{file_id}/content?variant=thumb` returns thumbnail; same request without variant returns original.
4. Catalog cards request thumbnails via srcSet; detail view requests full-res.
5. Backfill script processes existing image-kind files without thumbnail, skips files that already have one (idempotent).
6. Each story has agent-browser snapshots at desktop + mobile viewports.

**FRs realized:** FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3.

**Architectural anchors:** Decision P (Initiative 8 — thumbnail pipeline shape).

**Blocked by:** Initiative 9 Story 14.2 (pytest hydrate isolation — Story 13.2 ModelFile test surface shares conftest). ITCM technical decisions ratified by operator delegation 2026-05-21.

##### Story 13.1 — Mobile carousel arrows always-visible at ≤sm breakpoint

**Realizes:** FR8-CAROUSEL-MOBILE-1, NFR8-UX-1.
**Architectural anchor:** none (CSS-only change).
**Depends on:** none (technically independent; can ship before 13.2 or in parallel).

Acceptance check shape:

- `apps/web/src/ui/custom/CardCarousel.tsx`: arrow button classes change from `opacity-0 group-hover:opacity-100 ...` to `sm:opacity-0 sm:group-hover:opacity-100 ...` (Tailwind v4 `sm:` prefix applies above sm-breakpoint; below sm-breakpoint = mobile = always visible).
- `apps/web/src/modules/catalog/components/ModelGallery.tsx`: same pattern applied to its arrow buttons.
- Verify the existing CardCarousel.test.tsx tests still pass (5/5 per QD-3 close-out 2026-05-10) — likely no test changes needed since the change is purely CSS.
- Playwright visual-regression baselines update for catalog list at mobile-light + mobile-dark (per project-context.md L110 4-project matrix). Baseline-reviewed lines per pre-commit hook contract.
- Visual smoke per NFR8-UX-1 — emphasis on mobile-light (the new visible-arrows behavior).

##### Story 13.2 — Thumbnail pipeline (on-upload + variant endpoint + srcSet + backfill)

**Realizes:** FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1.
**Architectural anchor:** Decision P.
**Depends on:** Initiative 9 Story 14.2 (test isolation for ModelFile pytest surface). Recommended ship-after-13.1 ordering keeps the smaller visual change separate from the bigger backend change.

Acceptance check shape:

**Backend (Pillow integration):**

- `apps/api/pyproject.toml`: verify Pillow ≥11 present; if not, add (worker already has it per project-context.md L24).
- `apps/api/app/workers/__init__.py`: new arq task `generate_thumbnail(model_file_id: int)` that loads the original file, generates 800px-longest-side WebP @ q80 via Pillow, saves as sibling `<original-filename>.thumb.webp` in `portal-content`.
- `apps/api/app/modules/admin/router.py` model-file create endpoint (image kind): on successful file save, enqueue `generate_thumbnail(file.id)`. Verify by integration test that thumbnail file appears on disk after task runs.
- `apps/api/app/modules/sot/router.py` GET content endpoint: accept `variant: str | None = Query(None)` query param; when `variant == "thumb"` and thumbnail file exists, serve thumbnail (Content-Type: image/webp); when thumbnail missing OR variant absent, serve original.
- `apps/api/tests/test_thumbnail_pipeline.py` (NEW): unit tests for thumbnail generation (size budget per NFR8-PERF-1), integration tests for upload → enqueue → thumbnail file presence, endpoint tests for variant routing.

**Frontend (srcSet):**

- `apps/web/src/modules/catalog/components/ModelGallery.tsx` (and any catalog-card image-srcing site): render `<img>` with both `src` (thumbnail URL with `?variant=thumb`) and `srcSet` for retina (`?variant=thumb` @ 1x, full URL @ 2x — OR adjust based on what the spec phase determines is the right multiplier strategy).
- Catalog-detail page (model-page large image): continues to use full-resolution original, no srcSet.

**Backfill:**

- `infra/scripts/backfill-thumbnails.sh`: bash script that connects to API (using existing agent credentials or admin token from `.env`), queries `/api/models?include_files=true` (or equivalent listing endpoint), filters to image-kind files without thumbnails, enqueues `generate_thumbnail` for each via admin endpoint OR direct arq enqueue.
- Idempotent: re-running the script skips files that already have thumbnails.
- Run once post-deploy by operator (not automated in `deploy.sh`).

**Visual smoke per NFR8-UX-1:** catalog list page at desktop + mobile, model-detail at desktop + mobile. Verify catalog cards render quickly with thumbnail-sized payloads; detail view still uses full-res.

### Cross-references

- PRD: `prd.md` § Initiative 8.
- Architecture: `architecture.md` § Initiative 8 (Decision P).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-13.

## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 9" (FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1). Source architecture section: `architecture.md` § "Initiative 9" (pointer-only — no architectural decisions). Single Epic E14 with 3 stories.

**Init 5 + 6 + product architecture unchanged.** Initiative 9 is test-infrastructure-only work.

### Overview

Single epic E14 with 3 stories. Sequence: 14.1 (vitest admin finders) → 14.2 (pytest hydrate pollution) → 14.3 (visual-regression hook flake). 14.1 + 14.2 can also run in parallel since they touch distinct frameworks; sequencing them gives cleaner Codex review boundaries. 14.3 begins with an instrumentation pass before fixing.

Each story carries NFR9-DETERMINISM-1 (≥3 consecutive successful runs of the affected test suite). NFR7-UX-1 / NFR8-UX-1 visual-verification gate does NOT apply (no rendered UI surface in any of these stories).

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E14 | Test Isolation Cleanup | 3 (14.1, 14.2, 14.3) | Low-Medium | Low (test-only; no production-code touches per NFR9-SCOPE-1) | FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1 | none (entry epic for Init 9; scheduled FIRST in this SCP's execution chain) |

**Total: 3 stories.** Effort estimate: ~½–1 day back-to-back autonomous execution. 14.1 + 14.2 are bounded (hours each — known surfaces, known fix shapes). 14.3 has investigation-time variance (instrumentation pass → root cause → fix → verify) — pessimistic estimate ~4-8h.

### Epic 14 — Test Isolation Cleanup

**Goal.** Close three test-infrastructure isolation gaps that pre-date Init 5+6 and would interfere with Init 7+8 story development. Establish NFR9-DETERMINISM-1 as the test-infrastructure analog of the UI visual-verification gate.

**Acceptance gate.**

1. `npm run test apps/web/src/modules/admin/` returns 0 failures across all 5 affected files; verified by 3 consecutive runs.
2. `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` returns PASS deterministically across 10 consecutive invocations (in this exact order).
3. `infra/scripts/check-all.sh` visual stage and standalone `npx playwright test --config=tests/visual/playwright.config.ts` produce identical pass/fail verdict across the full baseline set, 3 consecutive runs in each context.
4. Each story's Dev Agent Record logs the 3-consecutive-run verification per NFR9-DETERMINISM-1.

**FRs realized:** FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1.

**Architectural anchors:** none (test-infrastructure only).

**Blocked by:** none. Operator scope-pull 2026-05-21 promoted these from triage.

##### Story 14.1 — Vitest admin module finder fixes (18 failures → 0)

**Realizes:** FR9-VITEST-ADMIN-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (entry story).

Acceptance check shape:

- Identify the 18 failing tests across `apps/web/src/modules/admin/InvitesPage.test.tsx`, `GenerateInviteModal.test.tsx`, `InviteTokenDisplayModal.test.tsx`, `ResetLinkDisplayModal.test.tsx`, `UsersPage.test.tsx`. Capture failure log per test (text mismatch, role mismatch, label mismatch, missing element, etc.).
- For each failure: regenerate the finder against current i18n + DOM shape. Test-only change. If a finder reveals what looks like a real component bug (e.g. accessible-name regression in the component itself), STOP and surface to operator per NFR9-SCOPE-1.
- Verify: `npm run test apps/web/src/modules/admin/` returns 0 failures, 3 consecutive runs.
- Per-file afterEach(cleanup) audit per memory [[feedback_vitest_manual_cleanup]] — note: since commit a026e97 (global `vitest.setup.ts`), per-file afterEach is redundant; if any of the 5 affected files still has per-file boilerplate, leave it (harmless), don't introduce new ones.

##### Story 14.2 — Pytest hydrate DB-pollution isolation close

**Realizes:** FR9-PYTEST-HYDRATE-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 14.1).

Acceptance check shape:

- Reproduce: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in this order fails on `test_hydrate_creates_local_tree`; running `test_hydrate_creates_local_tree` alone passes. Confirm via 3 consecutive reproductions.
- Investigate `apps/api/tests/conftest.py`: `_isolated_db` is session-scoped per L96-97 in project-context.md. Check whether FAKE_STL_PAYLOAD_AAA is committed via a fixture that should be function-scoped, OR whether the test commits explicitly without rollback, OR whether the `/api/models` listing in hydrate scans the DB without filtering by something the FAKE seed lacks (e.g. soft-delete marker).
- Fix: tighten isolation. Probable shapes:
  - Convert offending fixture to function-scoped + add explicit teardown.
  - Add explicit DB rollback at test exit in the offending test.
  - Add explicit filter in `/api/models` listing or in `test_hydrate_creates_local_tree`'s expectations.
- Verify: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in order returns PASS deterministically, 10 consecutive runs (per FR9-PYTEST-HYDRATE-1 verification clause).
- Always wrap pytest in `timeout 600` per memory [[feedback_pytest_timeout]] — investigation runs should not become zombie-pytest sessions.

##### Story 14.3 — Visual-regression hook-context flake (admin-invites + admin-users baselines)

**Realizes:** FR9-VISUAL-HOOK-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 14.1, 14.2).

Acceptance check shape:

**Phase 1 — Instrumentation pass (no fix yet):**

- Add temporary logging to `infra/scripts/check-all.sh` (or wherever the visual stage entry is) capturing: the actual port the Playwright dev-server binds to, the build SHA being tested, the working directory at visual-stage entry, the env vars present (filtered to relevant ones — `PORT`, `VITE_*`, `NODE_ENV`, etc.).
- Reproduce hook-context failure on admin-invites + admin-users baselines. Capture the log output.
- Reproduce standalone-context pass on same baselines. Capture the standalone log output.
- Diff the two logs. Pin the divergence (port collision, SHA drift, env-var leak, etc.).

**Phase 2 — Fix (informed by Phase 1):**

- Apply the targeted fix at the divergence point. Could be one of: explicit port allocation in `check-all.sh` to avoid collision; explicit build artifact directory for visual stage; explicit env-var unset/set in the hook chain; or a Playwright config tweak.
- Per [[feedback_visual_failure_mode_triage]]: grep the failure log for snapshot vs timeout vs strict-mode-violation breakdown BEFORE deciding on `--update-snapshots`. Hook flake is likely NOT a baseline-snapshot issue; do not regen baselines as the fix.

**Phase 3 — Verify per NFR9-DETERMINISM-1:**

- 3 consecutive `infra/scripts/check-all.sh` runs → identical pass/fail verdict across full baseline set.
- 3 consecutive standalone Playwright runs → identical pass/fail verdict across full baseline set.
- Hook-context and standalone-context verdicts match.

**Phase 4 — Remove instrumentation logging** added in Phase 1 (or convert to permanent diagnostic log gated behind `DEBUG=1` env var per project-context.md L59 logging contract).

### Cross-references

- PRD: `prd.md` § Initiative 9.
- Architecture: `architecture.md` § Initiative 9 (pointer-only).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-14.
- Memory entries informing this epic: [[feedback_preexisting_issue_threshold]], [[feedback_vitest_manual_cleanup]], [[feedback_pytest_timeout]], [[feedback_visual_failure_mode_triage]].

## Initiative 10 — Operator Polish Batch

**Status:** 🚧 planning (started 2026-05-22). Source SCP: `sprint-change-proposal-2026-05-22-init10.md` (status `approved` 2026-05-22). Predecessor Initiative 9 closed 2026-05-22 chained batch. Three epics E15+E16+E17 with ~13 stories total. Execution: **E15 first** (test health is precondition for downstream feature work); **E16 + E17 parallel** after E15 close (disjoint surfaces — catalog + admin write vs admin read tables + triage docs).

### Overview

Operator surfaced 10 stakeholder items in 2026-05-22 batch report. 8 land in Init 10 epics; 2 are RECONCLUDED OUT-OF-SCOPE (item #6 OTEL infra-side, item #7 401-scan SSH-blocked) per SCP §B operator-action-items.

### Requirements Inventory

| Type | ID | Epic | Stories | Title |
|---|---|---|---|---|
| FR | FR10-TEST-DETERMINISM-PYTEST-1 | E15 | 15.1 | Pytest suite completes deterministically (close threading deadlock in `test_concurrent_refresh_one_wins`) |
| FR | FR10-TEST-DETERMINISM-PLAYWRIGHT-1 | E15 | 15.2 | Playwright visual suite at 0 unhandled failures (78 stale baselines + 8 anon-login-only timeouts) |
| FR | FR10-TEST-FIXTURE-CLEANUP-1 | E15 | 15.3 | Centralize per-file `client` fixture into conftest.py (Epic 8 retro item §10) |
| FR | FR10-DESC-1 | E16 | 16.1 | ModelNote bilingual schema migration (body → body_pl + body_en) |
| FR | FR10-DESC-2 | E16 | 16.2 | On-demand "Generate description" admin button + AI pipeline |
| FR | FR10-SHARE-ANON-1 | E16 | 16.3 | Anonymous share-link frontend route `/share/<token>` |
| FR | FR10-SHARE-ANON-2 | E16 | 16.3 | Member-side share-gen dialog + "My share links" settings page |
| FR | FR10-MANUAL-ADD-1 | E16 | 16.4 | Admin manual model add (admin-only `POST /api/admin/models`) |
| FR | FR10-MANUAL-ADD-2 | E16 | 16.5 | Admin file upload to existing model (`POST /api/admin/models/{id}/files`) |
| FR | FR10-DOWNLOAD-1 | E16 | 16.6 | Bulk STL download (ZIP) restoration |
| FR | FR10-UX-TABLES-1 | E17 | 17.1 | Admin tables fluid full-width (designer-confirmed) |
| FR | FR10-TRIAGE-1 | E17 | 17.3 | TB-016 agent runbook doc-honesty (3 findings) |
| FR | FR10-TRIAGE-2 | E17 | 17.4 | DOC-DRIFT-2 close (4 remaining drifts) |
| NFR | NFR10-DETERMINISM-1 | E15 (all) + forward | — | Cross-framework test-suite determinism (3 consecutive runs); forward contract for Init 11+ |
| NFR | NFR10-SCOPE-1 | E15 (15.1 boundary-carve) | — | Test-only changes by default; Story 15.1 prod-side carve if root cause reveals real race |
| NFR | NFR10-SCHEMA-MIGRATION-1 | E16 (16.1) | — | ModelNote migration forward-only; <2-min downtime acceptable; backfill in up() |
| NFR | NFR10-VISUAL-VERIFICATION-1 | E16 + E17 (UI stories) | 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 17.1 | Mandatory pre-CR agent-browser visual-verification (Init 7+8+9 precedent) |
| NFR | NFR10-SHARE-SECURITY-1 | E16 (16.3) | — | Anonymous share route MUST NOT expose admin endpoints / `current_user` state / cookies; Codex auth-boundary contract audit |

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered |
|---|---|---|---|---|---|
| E15 | Test Health & Determinism | 3 (15.1, 15.2, 15.3) | Med-High (highest variance — depends on Story 15.1 outcome) | Low (test-only per NFR10-SCOPE-1) | FR10-TEST-DETERMINISM-PYTEST-1, FR10-TEST-DETERMINISM-PLAYWRIGHT-1, FR10-TEST-FIXTURE-CLEANUP-1 + NFR10-DETERMINISM-1 |
| E16 | Catalog Power-User Features | 6 (16.1, 16.2, 16.3, 16.4, 16.5, 16.6) | Med-High | Med (schema migration + multipart upload + new admin UI + anonymous frontend route) | FR10-DESC-1/2, FR10-SHARE-ANON-1/2, FR10-MANUAL-ADD-1/2, FR10-DOWNLOAD-1 + NFR10-SCHEMA-MIGRATION-1 + NFR10-VISUAL-VERIFICATION-1 + NFR10-SHARE-SECURITY-1 |
| E17 | Operator UX & Backlog Sweep | 4 (17.1, 17.2, 17.3, 17.4) | Low | Low (CSS + doc) | FR10-UX-TABLES-1, FR10-TRIAGE-1/2 + NFR10-VISUAL-VERIFICATION-1 |

**Total: ~13 stories.** Optimistic 2-3 days, realistic 3-5 days autonomous chain. E15 + E16 carry highest investment; E17 is small-surface hygiene.

### Epic 15 — Test Health & Determinism

**Goal.** Close 1 pytest threading deadlock + 86 deterministic visual-regression failures (78 stale-baseline drift + 8 anon-login-only timeouts) + ~16-file per-file `client` fixture refactor. Establish NFR10-DETERMINISM-1 forward contract (no `retry: 3`, no skip-tag, no per-story flake-investigation cycles in downstream epics).

**Audit findings (recon subagent 2026-05-22):** vitest at flake-zero (0 work needed); pytest 1 hang-class deadlock in `test_concurrent_refresh_one_wins` (`apps/api/tests/test_auth_refresh.py:164-194`) likely caused by non-thread-safe `_patch_arq_pool` autouse fixture; playwright 86 deterministic-FAIL = stale baselines (post-Init 5/6/7/8 UI evolved) + 8× `page.waitForURL` timeout in `anon-login-only.spec.ts`. Zero true non-determinism (variance=0).

**Acceptance gate.** `cd apps/api && timeout 600 uv run pytest tests/` 3× consecutive PASS deterministic AND `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` 3× consecutive PASS deterministic AND `infra/scripts/check-all.sh visual` 3× consecutive PASS deterministic (hook context) AND vitest stays at flake-zero (no regression from 15.x changes).

**FRs realized:** FR10-TEST-DETERMINISM-PYTEST-1, FR10-TEST-DETERMINISM-PLAYWRIGHT-1, FR10-TEST-FIXTURE-CLEANUP-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.

**Architectural anchors:** none (test-infrastructure only per NFR10-SCOPE-1).

**Blocked by:** none (entry epic for Init 10).

##### Story 15.1 — Pytest threading deadlock: `test_concurrent_refresh_one_wins`

**Realizes:** FR10-TEST-DETERMINISM-PYTEST-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1 (with Phase 2 decision boundary for prod-side carve).
**Architectural anchor:** none.
**Depends on:** none (entry story for E15).

Acceptance check shape per SCP Appendix A Story 15.1 (4-phase: instrumentation → root-cause-analysis → fix per chosen path → verify). Phase 1 instrumentation pins whether the threading deadlock is test-only (rewrite without `threading.Thread`) or prod-side race (`create_pool` concurrency requires `asyncio.Lock`). Phase 2 decision is data-driven from Phase 1; both paths acceptable per NFR10-SCOPE-1 boundary-carve.

**Verification:** `timeout 60 uv run pytest tests/test_auth_refresh.py::test_concurrent_refresh_one_wins -v` → exit 0 in <30s, 5× consecutive. `timeout 600 uv run pytest tests/test_auth_refresh.py` → exit 0 in <120s, 3× consecutive (also covers downstream victim `test_reuse_outside_grace_burns_family`). `timeout 600 uv run pytest tests/` → exit 0, 3× consecutive (full suite stays green).

##### Story 15.2 — Visual-regression baseline batch refresh (86 stale snapshots + 8 anon-login-only timeouts)

**Realizes:** FR10-TEST-DETERMINISM-PLAYWRIGHT-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 15.1, 15.3).

Acceptance check shape per SCP Appendix A Story 15.2 (4-phase: classification triage → stale-baseline regen batch → anon-login-only spec fix → verify). **Decision boundary:** if classification phase reveals more than 5 real UX regressions (vs stale-baseline drift), HALT Story 15.2 and surface to operator — that signal is bigger than a regen story; it's an Init-10-amending discovery requiring SCP revision.

**Verification:** standalone Playwright + check-all.sh hook context 3× consecutive each, identical pass/fail verdict. Baseline acceptance gate sign-off lines per regenerated PNG per project-context.md UI Quality Gates contract.

##### Story 15.3 — Per-file `client` fixture refactor → centralized `conftest.py`

**Realizes:** FR10-TEST-FIXTURE-CLEANUP-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 15.1, 15.2).

Per Epic 8 retro item §10 (≥12 files, past 3× saturation). Inventory ~16 files in `apps/api/tests/test_{2fa,auth,admin,invite,share}_*.py`; promote single `isolated_client` fixture in `conftest.py`; remove per-file fixtures via auto-discovery. Pure refactor; no behavior change. `git diff --stat` should show fixture file deletions only.

**Verification:** `timeout 600 uv run pytest tests/` → exit 0, 3× consecutive; baseline pytest pass-count matches pre-refactor.

### Epic 16 — Catalog Power-User Features

**Goal.** Ship 6 user-facing catalog improvements: bilingual descriptions with on-demand AI auto-fill, anonymous share-link viewer (member-generated, 7d hard-cap TTL, revocable from UI), admin manual model-add + STL upload, restored bulk STL download ZIP.

**Acceptance gate.** End-to-end functional verification on `.190`: member→anonymous share round-trip works (mint + link open + revoke); admin manual-add flow works (form → upload → thumbnail render fires → model in catalog); admin Generate description button works (preview → accept → persist); member catalog detail Download all (ZIP) works; visual verification per NFR10-VISUAL-VERIFICATION-1 on all UI surfaces.

**FRs realized:** FR10-DESC-1, FR10-DESC-2, FR10-SHARE-ANON-1, FR10-SHARE-ANON-2, FR10-MANUAL-ADD-1, FR10-MANUAL-ADD-2, FR10-DOWNLOAD-1, NFR10-SCHEMA-MIGRATION-1, NFR10-VISUAL-VERIFICATION-1, NFR10-SHARE-SECURITY-1.

**Architectural anchors:** Decision L (Story 16.1), Decision M (Story 16.3), Decision N (Stories 16.4 + 16.5).

**Blocked by:** E15 close (test signal must be reliable).

##### Story 16.1 — ModelNote bilingual schema migration

**Realizes:** FR10-DESC-1, NFR10-SCHEMA-MIGRATION-1, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** Decision L (architecture.md § Initiative 10).
**Depends on:** none (entry story for E16).

Per Decision L: forward-only Alembic migration drops `body NOT NULL` for description-kind, adds `body_pl: str | None` + `body_en: str | None`, backfills `body → body_en` for description rows in migration up(). Updates SQLModel + Pydantic schemas + DescriptionPanel.tsx rendering logic.

**Verification:** Alembic up + down both succeed on test DB; DescriptionPanel renders PL → EN fallback → empty-state correctly in both locales; visual baselines regen for catalog-detail spec set.

##### Story 16.2 — "Generate description" admin button + sources pipeline

**Realizes:** FR10-DESC-2, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** Decision L (extends).
**Depends on:** Story 16.1.

Admin-only button on model-detail page opens dialog with source toggles (external URL scrape + Nextcloud notes) + free-form context + locale selector. Backend enqueues arq job → Claude API call (Haiku 4.5 default) → preview UI → accept persists via PUT.

**Verification:** end-to-end on `.190` — admin opens dialog, generates, accepts, refreshes page, sees persisted description in both locales; visual baselines for the new dialog component.

##### Story 16.3 — Anonymous share-link frontend viewer + member-side UI

**Realizes:** FR10-SHARE-ANON-1, FR10-SHARE-ANON-2, NFR10-VISUAL-VERIFICATION-1, NFR10-SHARE-SECURITY-1.
**Architectural anchor:** Decision M (architecture.md § Initiative 10).
**Depends on:** none (independent of 16.1, 16.2 — uses existing model-detail components).

Per Decision M: new route `apps/web/src/routes/share/$token.tsx` renders anonymous viewer WITHOUT AuthGate, no ModuleRail; reuses Viewer3DInline + DescriptionPanel + FilesTab (download-only). Member-side: share-gen dialog with TTL dropdown (1d/3d/7d) on model-detail + "My share links" settings page with revoke.

**Auth-boundary contract audit:** Codex review per memory [[auth-boundary-contract-audit]] before merge — verify NO `current_user` calls inside `/share/$token`, NO cookies sent to `/api/share/*`, NO admin-mutating UI elements visible.

**Verification:** member mints link → anonymous (incognito) browser opens link → sees model-detail without left rail → STL download works → revoke from "My share links" → link returns 404. Visual baselines for: (a) anonymous viewer at desktop+mobile, (b) member share-gen dialog, (c) "My share links" page.

##### Story 16.4 — Admin manual model add

**Realizes:** FR10-MANUAL-ADD-1, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** Decision N (architecture.md § Initiative 10).
**Depends on:** Story 16.1 (for bilingual description fields in form).

Per Decision N: new endpoint `POST /api/admin/models` (multipart/form-data, admin-only). New admin route `apps/web/src/routes/admin/models/new.tsx` with form + file drop zones. Existing audit-log + thumbnail-render-enqueue patterns reused.

**Verification:** admin creates model via UI with all fields + thumbnail + STL → model lands in catalog → thumbnail renders within polling budget → audit log shows `sot.model.create_manual` event. Visual baselines for the new admin route.

##### Story 16.5 — Admin file upload to existing model

**Realizes:** FR10-MANUAL-ADD-2, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** Decision N (extends).
**Depends on:** Story 16.4 (reuses multipart patterns).

New endpoint `POST /api/admin/models/{id}/files` (multipart, admin-only) with `kind` selector. Simple replace semantics for primary STL/STEP/F3D; append for images. UI: "Upload file" CTA on model-detail (admin-visible) opens dropzone dialog.

**Verification:** admin uploads STL replacement → primary STL replaces → thumbnail re-renders (if revealed). Visual baseline for the upload dialog.

##### Story 16.6 — Bulk STL download (ZIP) restoration

**Realizes:** FR10-DOWNLOAD-1, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** none (regression restore).
**Depends on:** none.

Restore `GET /api/sot/models/{id}/bundle` (or current-naming equivalent — verify against last-shipped naming). Returns `application/zip` with all printable files at top-level with original filenames. Member + admin auth. UI: "Download all" CTA on model-detail (verify if already wired per Init 0 SLICE-13 history; reconnect if not).

**Verification:** member triggers Download all → ZIP downloads with correct contents (manually inspect with `unzip -l`). Visual baseline for the CTA.

### Epic 17 — Operator UX & Backlog Sweep

**Goal.** Close 4 small-surface items: admin tables fluid full-width universal pattern (~6 lines diff per designer subagent), TB-016 runbook doc-honesty (3 findings), DOC-DRIFT-2 remaining 4 drifts close-out, baseline regen sign-off.

**Acceptance gate.** Admin invites + admin users tables fluid on 3 viewport widths verified visually; TB-016 doc commit landed (runbook fingerprint baseline shift); DOC-DRIFT-2 status flipped to done in triage-backlog.md.

**FRs realized:** FR10-UX-TABLES-1, FR10-TRIAGE-1, FR10-TRIAGE-2, NFR10-VISUAL-VERIFICATION-1.

**Architectural anchors:** none.

**Blocked by:** E15 close (visual baselines stable enough for 17.1 baseline regen).

##### Story 17.1 — Admin tables fluid full-width universal pattern

**Realizes:** FR10-UX-TABLES-1, NFR10-VISUAL-VERIFICATION-1.
**Architectural anchor:** none.
**Depends on:** none.

Per designer subagent recommendation (2026-05-22): remove `max-w-7xl` from `InvitesPage.tsx:148`, `min-w-[1200px]` from `InvitesPage.tsx:229`, `max-w-6xl` from `UsersPage.tsx:279`. Sessions page (`max-w-3xl`) left alone (form-style settings). ~6 lines diff. Optional `whitespace-nowrap` on timestamp/IP columns if natural wrap looks ugly.

**Verification:** visual baselines regen for admin-invites + admin-users across 4 viewport projects (desktop-light, desktop-dark, mobile-light, mobile-dark); baseline-reviewed sign-off lines per project-context.md UI Quality Gates contract. Manual verification at 1366px / 1920px / 2560px viewports.

##### Story 17.2 — Visual baselines regen sign-off (bundled into 17.1)

**Realizes:** NFR10-VISUAL-VERIFICATION-1 forward contract enforcement.
**Status:** bundled into Story 17.1 commit; listed here for visibility only. May collapse into 17.1.

##### Story 17.3 — TB-016 agent runbook doc-honesty fixes

**Realizes:** FR10-TRIAGE-1.
**Architectural anchor:** none.
**Depends on:** none.

Apply 3 findings per triage-backlog TB-016 recommended dispositions:

- Finding A — option 2 (budget bump 60s → 120s + 1-sentence mesh-size variance qualifier) in `docs/agents-add-model-runbook.md:418-427`
- Finding B — full rewrite of `:142` per fix sketch (drop `D:\` Windows-specific reference, generic browser-default phrasing)
- Finding C — rewrite `:303` + update example payload `:395` (active bilingual-name guidance + both fields populated in example)

Single doc-only commit; auto-deploy skipped per `feedback_auto_deploy_dev`. Runbook fingerprint baseline shift (single roll, not three). Triage-backlog.md status update: TB-016 → done.

##### Story 17.4 — DOC-DRIFT-2 remaining drifts close-out

**Realizes:** FR10-TRIAGE-2.
**Architectural anchor:** none.
**Depends on:** none.

Patch 4 drifts:

- Drift 3 — Decision B INTEGER→UUID schema rewrite (largest doc-debt) in `architecture.md` Initiative 5 section
- Drift 5 — `refresh_tokens` autogenerate cleanup (code-side rename in `apps/api/app/modules/auth/`)
- Drift 16 — `ratelimit_share_*` Settings field naming cosmetic in `apps/api/app/core/config.py`
- Drift 17 — `test_create_share_requires_admin` rename in `apps/api/tests/test_share_admin.py`

Single `docs(bmad)` commit for drift 3 (doc-only) + 1 `chore` commit for drifts 5, 16, 17 (code-side). Possibly 2 commits total. Triage-backlog.md status update: DOC-DRIFT-2 → done.

### Cross-references

- PRD: `prd.md` § Initiative 10.
- Architecture: `architecture.md` § Initiative 10 (Decisions L, M, N).
- SCP: `sprint-change-proposal-2026-05-22-init10.md` (full draft).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-15 / epic-16 / epic-17.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]], [[feedback_vanilla_bmad_first]], [[feedback_frontend_visual_verification]], [[feedback_pytest_timeout]], [[feedback_visual_failure_mode_triage]], [[feedback_auth_boundary_contract_audit]].
- Triage cross-reference: TB-016 + DOC-DRIFT-2 promoted via Stories 17.3 + 17.4; TB-014 + TB-017 declined-defer with documented rationale; TB-018 retroactively done; TB-019 reserved for admin-table-width (folded into 17.1, no separate entry needed); TB-020 reserved for OTEL data-prepper operator-runbook reminder.

## Initiative 11 — Triage Quick Wins Bundle

**Status:** 🚧 planning (started 2026-05-23 after SCP approval).
**SCP:** `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11 — first phase of the 5-init triage-backlog cleanup batch.
**Trigger:** Operator 2026-05-23 morning request "paczka ze wszystkich obecnie otwartych backlogowych tematów" + Option 1 (5-init clustering) selected via AskUserQuestion.
**Mode:** ITCM autonomous; 5 quick-dev-shaped stories executed sequentially; no operator-handshake pauses; per-story Codex review via `gpt-5.4-mini` (routine class per [[feedback_codex_model_routing]]).

### Overview

Five triage-backlog candidates promoted in one epic-batch because they share **job-shape: one-commit fixes with pre-pinned root cause + isolated surface + low coordination cost**. Bundling into E18 (rather than 5 separate single-story epics) preserves the BMAD epic-ceremony surface (sprint-status entries, retro at close) while letting the autonomous chain warm up cheaply on small wins before tackling E19 (share enrichment epic). Each story is independently verifiable; failures in one do not block the others.

### Requirements Inventory

| ID | Description |
|---|---|
| **FR11-FIX-NOTE-1** | Admin add-note flow must POST to correct API path (`/admin/models/{model_id}/notes`), not the bare `/admin/notes` (which returns 404). |
| **FR11-UX-USERS-TABLE-1** | Admin Users page table must scroll horizontally inside its container, mirroring Admin Invites page pattern. Page itself must not scroll horizontally. |
| **FR11-ENUM-CREALITY-1** | `ModelSource` and `ExternalSource` enums must contain `crealitycloud` value to match agent-runbook supported-hosts table. |
| **FR11-TEST-PYTEST-1** | Full pytest suite must pass deterministically; two carry-forward failures from Init 9 Story 15.1 unmasking (`test_redis_down_passes_through_with_warning` + `test_list_files_returns_image_kinds_in_position_order`) must be resolved without scope creep into unrelated tests. |
| **FR11-DOC-DRIFT-1** | TB-016 remaining drifts (Drift 5 — `refresh_tokens` autogenerate cleanup, Drift 16 — `ratelimit_share_*` Settings field naming) must be closed; the 17-drift carry-forward chain becomes fully resolved. |
| **NFR11-DETERMINISM-1** | Full pytest suite green 3× consecutive after Story 18.4 lands (variance = 0). |
| **NFR11-DEPLOY-GATE-1** | Auto-deploy to .190 after every code-touching story merge per [[feedback_auto_deploy_dev]]. Doc-only stories (18.5 partial) skip deploy. |
| **NFR11-CODEX-ROUTING-1** | Per-story Codex review on `gpt-5.4-mini` (routine class) per [[feedback_codex_model_routing]] — 5 reviews in this epic do not warrant `gpt-5.5` heavyweight quota burn. |

### Epic List

#### Epic 18: Triage Quick Wins Bundle

##### Story 18.1 — TB-025 add-note 404 fix

**Realizes:** FR11-FIX-NOTE-1.
**Architectural anchor:** none (path-string correction).
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"`.

Frontend POST path correction in `apps/web/src/modules/catalog/hooks/mutations/useCreateNote.ts:17`: change `"/admin/notes"` → `` `/admin/models/${input.model_id}/notes` ``. The API endpoint is at `admin_router.py:871` (`POST /admin/models/{model_id}/notes`); the bare `/admin/notes` route doesn't exist for POST. Test mocks updated to match: `useCreateNote.test.tsx:28` + `AddNoteSheet.test.tsx:65` expected URL strings.

**Verification:** unit tests green (3 tests touched); manual browser verification per [[feedback_frontend_visual_verification]] — open a catalog model in admin context, add a note via AddNoteSheet, confirm 200 response + note appears in OperationalNotesTab without 404 error in network panel.

**Triage-backlog status update:** TB-025 → `Status: done` (in `_bmad-output/triage-backlog.md`).

##### Story 18.2 — TB-028 Admin Users table overflow wrapper

**Realizes:** FR11-UX-USERS-TABLE-1.
**Architectural anchor:** none (sibling-page CSS parity).
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"`.

Wrap `<table className="w-full text-sm">` in `apps/web/src/modules/admin/UsersPage.tsx:360` with `<div className="rounded border border-border overflow-x-auto">`, mirroring the wrapper at `apps/web/src/modules/admin/InvitesPage.tsx:228`. The InvitesPage already uses the industry-standard fluid-table-with-overflow pattern (designer subagent confirmed this 2026-05-22 in Init 10 Story 17.1 recon).

**Verification:** manual browser verification at 1366px viewport — confirm horizontal scrollbar appears INSIDE the table container, NOT on the page itself. Visual baseline regen for admin-users-empty + admin-users-populated specs across 4 viewport projects (desktop-light, desktop-dark, mobile-light, mobile-dark) with baseline-reviewed sign-off lines per UI Quality Gates.

**Triage-backlog status update:** TB-028 → `Status: done`.

##### Story 18.3 — TB-014 crealitycloud enum + Alembic migration

**Realizes:** FR11-ENUM-CREALITY-1.
**Architectural anchor:** none (existing enum extension; precedent in Init 0 SoT migrations).
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"`.

Add `crealitycloud = "crealitycloud"` to both `ModelSource` (`apps/api/app/core/db/models/_enums.py:16`) and `ExternalSource` (`_enums.py:42`) StrEnums. New Alembic migration `apps/api/migrations/versions/0018_add_crealitycloud_enum.py` chaining after the most recent migration (verify head with `alembic heads`):

```python
def upgrade() -> None:
    op.execute("ALTER TYPE modelsource ADD VALUE IF NOT EXISTS 'crealitycloud'")
    op.execute("ALTER TYPE externalsource ADD VALUE IF NOT EXISTS 'crealitycloud'")

def downgrade() -> None:
    # PG enum value removal requires full type recreation; documented as non-reversible
    # per project convention (forward-only migrations for enum extensions).
    pass
```

Runbook update: `docs/agents-add-model-runbook.md` source-detection table — drop the "(workaround)" caveat for `crealitycloud.com → other / other` mapping; change to `crealitycloud.com → crealitycloud / crealitycloud`.

**Verification:** Alembic migration applies cleanly to .190; smoke-test by creating a test model with `source=crealitycloud` via the API; confirm enum constraint accepts the value; pytest enum-related tests green.

**Triage-backlog status update:** TB-014 → `Status: done`.

##### Story 18.4 — TB-021 pytest 2 pre-existing failures fix

**Realizes:** FR11-TEST-PYTEST-1, NFR11-DETERMINISM-1.
**Architectural anchor:** none (test-side fixes).
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"`.

Two distinct deterministic failures unmasked by Init 9 Story 15.1 (which closed the threading deadlock that blocked alphabetically-later tests from running):

**Failure A — `test_redis_down_passes_through_with_warning` cross-file pollution**:
- **Symptom:** PASSES in isolation AND at file-level (6/6 file tests green) but FAILS in full-suite context.
- **Investigation phase (~30 min):** identify the leaking earlier-running file. Hypothesis bag: (1) autouse fixture from another file mutates a session-scoped resource consumed by `isolated_client_redis_down`; (2) `caplog` capture interaction with logger reconfiguration done by some earlier test. Use `pytest --collect-only` + bisection (alphabetical halving) to find the offender.
- **Fix shape:** depends on hypothesis. Most likely: change a session-scoped fixture to function-scoped, OR add explicit per-test logger reset, OR upgrade the failing test's own fixture to be more defensive.

**Failure B — `test_list_files_returns_image_kinds_in_position_order` 401 Unauthorized**:
- **Symptom:** FAILS in isolation with 401 on `GET /api/models/{id}/files?kind=image`.
- **Root cause:** test uses plain `client` fixture (unauthenticated) but endpoint requires `current_member_or_admin` per Init 6 default-deny posture (NFR6-SEC-1).
- **Fix shape:** swap `client` for the admin-authed equivalent (`admin_client` or whatever the existing pattern is in `conftest.py`). One-line fix once the right fixture is identified.

**Verification:** `timeout 600 uv run pytest apps/api/tests/ -x` 3× consecutive PASS deterministically (variance = 0). NFR11-DETERMINISM-1.

**Triage-backlog status update:** TB-021 → `Status: done`.

##### Story 18.5 — TB-016 remaining 4 (= Drifts 5 + 16) closure

**Realizes:** FR11-DOC-DRIFT-1.
**Architectural anchor:** none (code rename + Settings field naming).
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"` (Drift 5 = code-side; Drift 16 = cosmetic but in `apps/api/app/core/config.py` so still code-side).

Per Init 10 Story 17.4 explicit deferral note ("Drifts 5 (refresh_tokens autogenerate cleanup) + 16 (ratelimit_share_* Settings naming) deferred per triage low-value-cosmetic note"), Story 18.5 closes both:

- **Drift 5 — `refresh_tokens` autogenerate cleanup**: Story-spec discovery phase — search `apps/api/app/modules/auth/` for `refresh_tokens` autogenerate references that drift from canonical naming; identify what "autogenerate cleanup" means in context (likely a stale alembic autogenerate artifact or comment referring to a removed pattern). Action depends on discovery; likely a chore-rename or a stale comment removal.

- **Drift 16 — `ratelimit_share_*` Settings field naming cosmetic**: in `apps/api/app/core/config.py`, the `ratelimit_share_*` fields naming pattern drifts from the rest of the Settings class convention. Story-spec discovery phase — identify the exact field names and the canonical convention (look at sibling Settings fields like `cookie_*`, `jwt_*`, `auth_*` for the pattern). Rename to match. Pure cosmetic; no behavior change.

**Verification:** ruff + ruff format clean; pytest fully green (no behavior touched, just rename); manual git diff inspection shows no semantic change.

**Note on commit shape:** likely single `chore(api): close TB-016 remaining drifts 5+16` commit covering both surfaces; auto-deploy applies (code-side, not doc-only).

**Triage-backlog status update:** TB-016 → `Status: done`.

### Cross-references

- PRD: minimal Init 11 PRD section (drafted inline, no `bmad-edit-prd` needed for this scope).
- Architecture: no architecture impact for Init 11; no new Decisions.
- SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11 + § 5.1 detailed change proposals.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-18.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]], [[feedback_codex_model_routing]] (mini for routine reviews), [[feedback_frontend_visual_verification]], [[feedback_pytest_timeout]], [[feedback_auto_deploy_dev]], [[feedback_scp_pre_enumeration_phase]].
- Triage cross-reference: TB-025 + TB-028 + TB-014 + TB-021 + TB-016 (Drifts 5 + 16 residue) promoted via Stories 18.1-18.5; on completion all 5 candidates move from `Status: candidate` to `Status: done` in `_bmad-output/triage-backlog.md`.

## Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening

**Status:** 🚧 planning (started 2026-05-23 after Init 11 close + operator-calibration AskUserQuestion).
**SCP:** `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 12 (calibrated by 2026-05-23 grilling: security-first priority, 60 req/min cap, 2 MB/s + 5 concurrent per IP, carousel = member-view-scoped).
**Trigger:** Operator batch report 2026-05-22 item #2 ("widok shared modelu jest trochę za biedny") + 2026-05-23 paczka-shape extension.
**Mode:** ITCM autonomous AFTER operator-calibration; security stories (19.1-19.3) ship before UX uplift (19.4-19.6) per operator priority; Story 19.7 depends on Init 13 TB-022 and ships last (or moves into Init 13 if convenient).

### Overview

Init 10 Story 16.3 (anonymous share viewer at `/share/<token>`) deliberately shipped minimum-viable: static "Download STL" button only. Operator hands-on feedback 2026-05-22: too austere; recipients deserve member-parity catalog view (scoped to the one shared item, no auth-required actions). At the same time the anonymous endpoint is now a real public attack surface — share token leak → loop downloads → outbound pipe saturation. Init 12 ships both arms of the response: **security hardening** (request-rate cap + throughput cap + threat model doc) MUST land before the UX uplift expands the surface; **UX uplift** (full file list + description + bilingual carousel + STL preview renders + 3D viewer) brings the share view to member-parity.

**Carousel framing decision (operator 2026-05-23):** anonymous share view = "the view a logged-in member would see for this one catalog item, MINUS member-only actions reserved for future capabilities (e.g. request-print, personal-library add)." NOT "admin view minus admin actions" — admin will become a strict superset of member with extra capabilities (analytics, system config, force actions). Anonymous recipient sees only the catalog-detail surface scoped to the shared item.

### Requirements Inventory

| ID | Description |
|---|---|
| **NFR12-DDOS-RATE-1** | `/api/share/{token}/*` MUST be rate-limited to **60 requests per minute per (token, IP) tuple**. Reject above with 429 + Retry-After header. Keying via Redis with `share:ratelimit:` prefix. |
| **NFR12-DDOS-THROUGHPUT-1** | `/api/share/{token}/files/*` (file downloads) MUST be throughput-capped to **2 MB/s per stream** AND **5 concurrent connections per IP**. Implemented via Nginx `limit_rate` + `limit_conn` directives (edge proxy in `~/repos/configs/nginx/`). |
| **NFR12-THREAT-MODEL-1** | architecture.md Init 12 H2 MUST contain a "§ Threat vectors enumerated" section per [[feedback_security_vector_enumeration]] listing all cookie-sending vectors, auth-state-consultation points, browser-default-credentials behaviors, and SPA reactivity gotchas specific to the share-anon surface. |
| **FR12-SHARE-FILE-LIST-1** | `GET /api/share/{token}/files` MUST return paginated list of all files on the shared model with share-scoped download URLs (Init 6 Decision N pattern). Anonymous; admin-auth NOT consulted. |
| **FR12-SHARE-DESCRIPTION-1** | Anonymous share view MUST render bilingual description (body_pl + body_en per Init 10 Decision L); language switch follows `i18n` locale per UI session. |
| **FR12-SHARE-CAROUSEL-1** | Anonymous share view MUST render the same `ModelGallery`-style carousel that authenticated catalog detail shows (admin photo-order respected; all photos navigatable). Share-scoped image URLs per Init 6 Decision N. |
| **FR12-STL-PREVIEW-RENDERS-1** | New render-worker task generates 4 STL preview images per STL file (iso/front/side/top views) stored as `ModelFile` rows with new `image_kind = "stl_preview"` enum value + Alembic migration. Trigger: lazy-on-first-share-access OR proactive arq cron (story-spec decision). |
| **FR12-SHARE-3D-VIEWER-1** | Anonymous share view MUST embed `Viewer3DInline` (no download button replacement) using share-scoped STL URL via `srcOverride` prop. Depends on Init 13 TB-022 (Viewer3DInline srcOverride extension). |
| **NFR12-DEPLOY-GATE-1** | Auto-deploy to .190 after every code-touching story merge per [[feedback_auto_deploy_dev]]. Nginx edge config changes for NFR12-DDOS-THROUGHPUT-1 sync via `~/repos/configs/sync.sh`. |
| **NFR12-CODEX-ROUTING-1** | Per-story Codex review on `gpt-5.5` (heavy/security class) for 19.1-19.3 + 19.7 per [[feedback_codex_model_routing]]; `gpt-5.4-mini` for 19.4-19.6 (routine FE/render work). |
| **NFR12-FRONTEND-VISUAL-1** | Every UI story (19.5, 19.7) MUST pass agent-browser visual verification before commit per [[feedback_frontend_visual_verification]]. |

### Architectural Decisions (anchor for E19)

Drafted inline below; full architecture.md extension lands during Story 19.1 spec prep.

- **Decision Q — Request-rate middleware**: FastAPI middleware (NOT Nginx) keyed per `(token_hash, client_ip)` tuple. Redis-backed `INCR` + `EXPIRE` pattern with `share:ratelimit:` prefix; 60s rolling window; 429 + Retry-After response on cap. Reason: FastAPI middleware can introspect the share-token validity + log structured events; Nginx-side rate limit would key only on IP (too coarse for a single-user-many-recipients link) or only on token (too coarse for separating legitimate concurrent viewers).
- **Decision R — Throughput-limit at Nginx edge**: `/api/share/{token}/files/*` location block carries `limit_rate 2m;` + per-IP `limit_conn_zone $binary_remote_addr zone=share_per_ip:10m; limit_conn share_per_ip 5;`. Reason: Nginx is more efficient at byte-cap streaming than app-level throttling; concurrent-connection cap defends against single-IP parallel-download exhaustion.
- **Decision S — STL preview rendering**: new arq task in `workers/render/` consuming ModelFile id + producing 4 `ModelFile` rows with `image_kind=stl_preview` and `position` reflecting view order (iso=0, front=1, side=2, top=3). New Alembic migration extends ModelFileKind enum + adds index on `(model_id, image_kind)` for query efficiency. Job dispatch: lazy on first `GET /api/share/{token}/...` access (avoids upfront cost on never-shared models) with idempotency guard via `(model_id, image_kind, kind=stl_preview)` uniqueness check; new model_files page exposes preview URLs as share-scoped.
- **Decision T — Share view file list endpoint**: `GET /api/share/{token}/files` returning `PaginatedFileList` shape (same as admin endpoint but share-scoped URLs). Admin permissions NOT consulted (share token IS the auth); rate-limit middleware (Q) applies; throughput limit (R) applies to subsequent file content fetches.

### Epic List

#### Epic 19: Anonymous Share View Enrichment + DDoS Hardening

##### Story 19.1 — Request-rate middleware (NFR12-DDOS-RATE-1)

**Realizes:** NFR12-DDOS-RATE-1.
**Architectural anchor:** Decision Q.
**Depends on:** Redis (existing); architecture.md Init 12 H2 Decision Q drafted in spec prep.
**Codex tag:** `--commit <SHA>` (default `gpt-5.5` — heavy/security review class).

FastAPI middleware in `apps/api/app/modules/share/ratelimit.py` (new file) decorating responses on the share router. Keys: `share:ratelimit:{token_hash}:{client_ip}` with 60s expiry, INCR + EXPIRE pattern. Cap: 60 INCR results in 429 + `Retry-After: 60` header. Soft-alert at 30 (half-cap) logged at `app.share.ratelimit` logger with `event.action=share.ratelimit.soft_alert`. Settings field: `ratelimit_share_anon_window_seconds = 60`, `ratelimit_share_anon_threshold = 60`, `ratelimit_share_anon_soft_threshold = 30`.

**Verification:** new pytest cases in `apps/api/tests/test_ratelimit_share_anon.py`: (a) 60 requests in 60s PASS; (b) 61st request returns 429 + correct Retry-After; (c) 60 requests within 30s + 30s sleep + new request PASSES (window expires); (d) cap is per-IP (different IPs share token, both get full 60). Use `share_caplog`-style dedicated handler for the soft-alert log assertion per Story 18.4 lesson. Manual smoke: hit `/api/share/<token>/...` 61 times via curl, observe 429.

**Triage-backlog status update:** TB-026 sub-item #6 (Request-rate cap) → done.

##### Story 19.2 — Throughput-limit middleware / Nginx limit_rate (NFR12-DDOS-THROUGHPUT-1)

**Realizes:** NFR12-DDOS-THROUGHPUT-1.
**Architectural anchor:** Decision R.
**Depends on:** Nginx config sync repo `~/repos/configs/nginx/`; operator must `sync.sh` after merge.
**Codex tag:** `--commit <SHA>` (default `gpt-5.5` — heavy/security review class; nginx config requires careful review).

Edge proxy config in `~/repos/configs/nginx/3d-portal.conf` adds a dedicated `location ~ ^/api/share/[^/]+/files/` block carrying `limit_rate 2m;` + a `limit_conn_zone $binary_remote_addr zone=share_per_ip:10m;` directive (defined in http context) + `limit_conn share_per_ip 5;` in the location. `infra/nginx-180/3d-portal.conf` mirrored. App-side complement: optional `streaming_throughput_floor` in Settings (commented; relies on Nginx for now).

**Verification:** manual via curl with `--limit-rate` and `&` parallelism: (a) single download at full speed caps at ~2 MB/s; (b) 5 parallel downloads from same IP succeed; (c) 6th parallel returns 503. Per [[feedback_external_test_source]] use `ezop-kbk.ddns.net` for out-of-network parallel-stream verification (separate LAN). Document the smoke probe in Story 19.2 acceptance notes.

**Triage-backlog status update:** TB-026 sub-item #7 (Throughput cap) → done.

##### Story 19.3 — Threat model doc + Decision Q+R+S+T finalization (NFR12-THREAT-MODEL-1)

**Realizes:** NFR12-THREAT-MODEL-1.
**Architectural anchor:** all of Init 12.
**Depends on:** 19.1 + 19.2 shipped (so the threat-vector list reflects real shape).
**Codex tag:** `--commit <SHA>` (default `gpt-5.5` — heavy/security review on threat model).

Extend `architecture.md` with `## Initiative 12` H2 section. Subsections:
1. Overview + carousel scope clarification (member-view-scoped framing per operator)
2. Decision Q (request-rate middleware) — final form
3. Decision R (throughput cap) — nginx config sketch
4. Decision S (STL preview rendering) — Alembic migration + arq task shape
5. Decision T (share file list endpoint) — endpoint signature + response shape
6. **§ Threat vectors enumerated** per [[feedback_security_vector_enumeration]]:
   - Cookie-sending vectors on `/api/share/<token>/*` (verified absent via TB-023-mirrored credentialless fixture in Init 14)
   - Auth-state-consultation: AuthProvider must NOT fire `/auth/me` on /share/* (carried forward from Init 10 Story 16.3 Codex round-1 fix)
   - Browser-default-credentials behaviors: `<img src>` + `<a href download>` + `<link rel=preload>` all send same-origin cookies by default; mitigation via fetch-blob anchor pattern (Story 16.3 Codex round-2 carry-forward)
   - SPA reactivity: route change to /share/* must reactively skip auth (history.pushState monkey-patch from Story 16.3)
   - Rate-limit bypass attempts: token rotation, IP spoofing via X-Forwarded-For (Nginx must NOT trust untrusted X-Forwarded-For)
   - Token leak vectors: log redaction, referer leak via outbound resources

**Verification:** doc-only commit; `docs(bmad)` scope; auto-deploy skipped per [[feedback_auto_deploy_dev]]. Cross-LLM review (Codex) on the threat-vector enumeration before declaring done.

##### Story 19.4 — Share file list endpoint (FR12-SHARE-FILE-LIST-1)

**Realizes:** FR12-SHARE-FILE-LIST-1.
**Architectural anchor:** Decision T.
**Depends on:** 19.1 + 19.2 shipped (rate-limit + throughput middlewares in place before exposing new fileset).
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"` (routine FE/BE endpoint extension).

Backend: `GET /api/share/{token}/files` in `apps/api/app/modules/share/router.py` returning `PaginatedFileList` with share-scoped URLs per Init 6 Decision N. Pydantic model `ShareFileListView` mirrors `ModelFileRead` but uses share-scoped URLs. Pagination via existing query params. Pytest cases in `test_share_public.py`: (a) anonymous GET returns 200 with file list; (b) URLs are share-scoped (NOT `/api/models/{id}/files/{file_id}/content`); (c) rate-limit applies (>60 req/min returns 429).

##### Story 19.5 — Anonymous share view description + carousel (FR12-SHARE-DESCRIPTION-1 + FR12-SHARE-CAROUSEL-1)

**Realizes:** FR12-SHARE-DESCRIPTION-1, FR12-SHARE-CAROUSEL-1.
**Architectural anchor:** none (FE component reuse).
**Depends on:** 19.4 (file list endpoint) for accessing photo files.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"` (routine FE).
**Carries:** NFR12-FRONTEND-VISUAL-1 — agent-browser smoke + visual baselines for /share/$token route.

Frontend: `apps/web/src/routes/share/$token.tsx` updated to render bilingual description (reuses `DescriptionPanel` component scoped to share-token-fetched ModelDetail shape) + `ModelGallery`-style carousel using share-scoped image URLs from Story 19.4 endpoint. NO admin/member action buttons; carousel + description are read-only. Per operator framing: this is the catalog-detail-page-minus-actions for anonymous recipients.

##### Story 19.6 — STL preview render job (FR12-STL-PREVIEW-RENDERS-1)

**Realizes:** FR12-STL-PREVIEW-RENDERS-1.
**Architectural anchor:** Decision S.
**Depends on:** none.
**Codex tag:** `--commit <SHA> -c review_model="gpt-5.4-mini"` (worker task; mid complexity).

Backend: new arq task `render_stl_previews(model_file_id)` in `workers/render/` producing 4 PNG/JPEG previews via existing trimesh + matplotlib stack (iso/front/side/top views; matplotlib camera positions). Output stored as `ModelFile` rows with new enum value `image_kind=stl_preview` + Alembic migration 0019 extending the enum. Dispatch: lazy on first `GET /api/share/{token}/files` if STL file exists but previews missing; idempotency guard via `(model_id, image_kind=stl_preview)` query. Share view consumes previews via existing file list endpoint (no new endpoint).

##### Story 19.7 — Anonymous share view 3D viewer integration (FR12-SHARE-3D-VIEWER-1)

**Realizes:** FR12-SHARE-3D-VIEWER-1.
**Architectural anchor:** Decision N (Init 6 share-scoped URLs).
**Depends on:** **Init 13 Story 20.3 (TB-022 Viewer3DInline srcOverride extension)** MUST ship first.
**Codex tag:** `--commit <SHA>` (default `gpt-5.5` — security review on share-scoped 3D viewer integration; cookie-leak class regression risk).
**Carries:** NFR12-FRONTEND-VISUAL-1 — agent-browser smoke + visual baselines.

Frontend: `apps/web/src/routes/share/$token.tsx` swaps static "Download STL" button for embedded `Viewer3DInline` component using share-scoped STL URL via `srcOverride` prop (extension shipped in Init 13 Story 20.3). NO download button removal — keep it alongside the viewer for users who want the file without browsing. Anonymous credentialless contract: `assertCredentialless` helper from Init 14 Story 21.2 applies (verifies no cookie leak on viewer asset fetches).

**Note:** if Init 14 Story 21.2 ships before Story 19.7, fold its `assertCredentialless` assertion into Story 19.7 visual baseline scaffolding. If 21.2 hasn't shipped, ship 19.7 with manual smoke and absorb the maszynowo assertion in 21.2.

### Cross-references

- PRD: extend `prd.md` with `## Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening` H2 section via `bmad-edit-prd` skill (drafted during Story 19.1 spec prep with operator-calibrated thresholds and carousel framing).
- Architecture: extend `architecture.md` with `## Initiative 12` H2 section (Decisions Q+R+S+T) — drafted during Story 19.3 (threat model doc).
- SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 12 + § 5.2 (operator-calibration of 2026-05-23 AskUserQuestion locks the parameters).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-19.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]], [[feedback_codex_model_routing]] (heavy class on security stories), [[feedback_security_vector_enumeration]] (mandatory § Threat vectors enumerated), [[feedback_voice_heavy_dedicated_grilling]] (2026-05-23 grilling pinned all 4 product decisions), [[feedback_autonomous_sleep_on_budget]] (pauza-na-reset rather than force-end), [[feedback_external_test_source]] (Story 19.2 parallel-stream verification).
- Triage cross-reference: TB-026 (7 sub-items) promoted to Init 12; sub-items mapped: #1 carousel → 19.5; #2 STL previews → 19.6; #3 3D viewer → 19.7; #4 file list → 19.4; #5 description → 19.5; #6 request-rate → 19.1; #7 throughput → 19.2.

## Initiative 13 — Catalog UX Uplift

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13. Predecessor: Init 12. Single epic E20 with 3 stories.

### Overview

Catalog UX polish batch — operator-aligned 2026-05-23 (AskUserQuestion): Add Model CTA top-right toolbar + modal-over-route + full form; catalog srcSet 2x candidate dropped for retina users; Viewer3DInline `srcOverride` hook (Story 20.3) shipped FIRST as Init 12 Story 19.7 prerequisite.

### Stories (Epic 20)

- **Story 20.1** (commit a9d7d18) — catalog srcSet perf: dropped `${thumbUrl} 1x, ${fullUrl} 2x` srcSet from ModelCard + CardCarousel. Resolves TB-027 retina perf concern (partial, fully closed by Init 16 TB-037 gallery tier).
- **Story 20.2** (commits 7f6dd10 + 83b225a fix-up) — admin Add Model CTA + modal. AddModelForm extracted to reusable component; AddModelModal Dialog wrapper; AddModelButton in catalog toolbar (admin-only). Resolves TB-029.
- **Story 20.3** (commits 8284032 + 027e710 lint fix-up) — Viewer3DInline `srcOverride` hook. Enables non-default-auth contexts (Init 12 Story 19.7 share-view 3D viewer consumer). Resolves TB-022.

### Decisions

- **Decision U** (architecture) — Add Model modal-over-route shape (form embed; Story 20.2).
- **Decision V** (architecture) — srcSet retina drop (Story 20.1).

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13.
- Architecture: `architecture.md` § Initiative 13 (Decisions U + V).
- PRD: `prd.md` § Initiative 13 (FR13-CATALOG-* + Decisions U + V).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-20.

## Initiative 14 — Test Infrastructure Hardening

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14. Single epic E21 with 2 stories.

### Overview

Test infrastructure hardening batch — Story 21.1 (TB-018 #2 hydrate pollution) verified ALREADY CLOSED via Init 9 Story 14.2; no work needed. Story 21.2 (TB-023 credentialless test fixture) shipped maszynowo NFR10-SHARE-SECURITY-1 contract enforcement.

### Stories (Epic 21)

- **Story 21.1** — TB-018 #2 verified ALREADY CLOSED via fa4a628 (Init 9 Story 14.2); no implementation. Triage-backlog updated.
- **Story 21.2** (commit ea3bfd0) — credentialless test fixture: `make_anonymous_client` helper + `assert_no_set_cookie_in_response` in conftest.py + 3 new credentialless contract tests in test_share_public.py (13/13 PASS). Resolves TB-023.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-21.
- Memory: [[reference_external_test_source]] (Story 21.2 pen-test source ezop-kbk.ddns.net).

## Initiative 15 — Meta + Deferred

**Status:** ✅ shipped 2026-05-23 (meta-only; doc-only commit). Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15. NOT an epic (per SCP §2.2 Init 15 deliberately bypasses epic structure for meta/skill-file work).

### Overview

- **TB-024 closed** (commit 80f25d4): BMAD skill template updates from Init 10 retro. bmad-create-story checklist §3.6 "Already-Shipped DISASTERS" + bmad-create-architecture template "Authoring guidance" for 4-cell dual-field matrix. Per-project skill files under `.claude/skills/`; doc-only commit; no deploy.
- **TB-017 DEFERRED** per SCP — TOTP_FERNET_KEY rotation runbook, trigger date 2027-05-20, doc authoring ≤2 months before.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § init-15-meta.

## Initiative 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)

**Status:** 🚧 planning (started 2026-05-24). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-24-init16.md` (status `approved` 2026-05-24). Predecessor Initiative 15 closed 2026-05-23. Initiative 16 is a **triage backlog cleanup batch** sweeping 9 open candidates post-Init-15. Three epics E22+E23+E24 plus one standalone Story S25.1, ~8 stories total.

### Overview

Operator authorized "wszystkie otwarte backlog itemy (chyba że deferred na konkretną datę)" 2026-05-24. Pre-SCP enumeration reconciled apparent in-scope set against Init 11-15 shipped state — items closed-by-displacement (TB-018 #2 via Story 21.1, TB-023 via Story 21.2, TB-022 via Story 20.3, TB-027 partial via Story 20.1, TB-029 via Story 20.2 review, TB-026 #6 per-IP via Story 19.1, TB-026 #7 throughput shipped-in-code via Story 19.2 review) removed from Init 16 actionable scope; the genuine 9 in-scope candidates grouped per job-shape:

- **Epic 22 — Image tier pipeline + symmetric fullscreen viewer** (items: TB-037 + TB-036 + TB-035 + TB-027 verify + TB-032 subsumed): backend gallery tier worker variant pipeline + FE carousel consumption (share + catalog detail) + NEW symmetric fullscreen image viewer mounting on both anonymous /share/$token AND authenticated /catalog/$modelId + post-tier hygiene pass.
- **Epic 23 — Share-view security hardening** (items: TB-033 + TB-034 + TB-026 sub#6 per-token addition): blob cache StrictMode refcount + revocation policy + STL preview source-tracking + single-flight lock + per-token rate-limit cap on top of Story 19.1 per-IP cap.
- **Epic 24 — Test infrastructure hygiena** (item: TB-030): centralized `_admin_token` helper sweeping 13 test files.
- **Standalone Story 25.1 — Mobile photo-reorder touch-action** (item: TB-038): one-line `touch-action: none` on dnd-kit DragHandle.

### Functional Requirements

- **FR16-TIER-1:** `generate_thumbnail` worker produces `.thumb.webp` (existing, ~10-50 KB, 128px) AND `.gallery.webp` (NEW, ~150-500 KB, designer-tuned default 1920px longest-edge). `?variant=gallery` routing with silent fallback to original. Backfill script extended.
- **FR16-CAROUSEL-TIER-1:** ShareCarousel + CardCarousel main frame consume `?variant=gallery`; thumb strip + card-grid stay `?variant=thumb`. Visual baselines regen.
- **FR16-VIEWER-1:** NEW symmetric fullscreen image viewer mounts on BOTH /share/$token AND /catalog/$modelId (operator-decided 2026-05-24). Fetches `?variant=full` fullscreen; `?variant=thumb` strip. Designer UX session BEFORE Story 22.3 spec authoring.
- **FR16-HYGIENE-TIER-1:** Post-tier backfill smoke output; TB-035 unidentified format triage; TB-027 retina serves gallery verification; TB-036 503 rate verification.
- **FR16-BLOB-CACHE-1:** `acquireShareBlob` `_pending` count map for StrictMode safety; page-mount-scoped invalidation (autonomous Decision X policy A). Closes TB-033.
- **FR16-STL-PREVIEW-LOCK-1:** Source-track previews by STL sha256 (boring-tech); single-flight Redis SETNX lock TTL 300s. Closes TB-034.
- **FR16-RATELIMIT-PER-TOKEN-1:** Per-token sliding window via Redis ZADD; configurable env defaults 60 req/min/token. Composable with Story 19.1 per-IP middleware. Closes TB-026 sub#6 per-token addition.
- **FR16-TEST-HELPERS-1:** NEW `apps/api/tests/_test_helpers.py` with `admin_token`/`agent_token`/`member_token` reading `get_settings().jwt_secret`; 13 test files migrate.
- **FR16-MOBILE-DRAG-1:** Tailwind `touch-none` on DragHandle button in PhotosTab.tsx:244-253. Closes TB-038.

### Non-Functional Requirements

- **NFR16-PERF-1: Gallery tier ≤500 KB for typical phone-photo inputs.** Pytest fixture exercises Pillow pipeline; designer may tune target during Story 22.3 UX session.
- **NFR16-DETERMINISM-1: Cross-framework test-suite determinism carried forward.** Vitest + pytest + playwright visual pass deterministically 3× consecutive after each Init 16 story merge. Story 24.1 explicit gate.
- **NFR16-VISUAL-VERIFICATION-1: Pre-CR agent-browser visual verify on every UI-touching story** (22.2 carousel, 22.3 fullscreen viewer NEW surface, 25.1 mobile drag). Backend/test-only stories exempt.
- **NFR16-SECURITY-1: Story 23.3 ships with explicit threat-vector enumeration in spec** per [[feedback_security_vector_enumeration]] — token leak vectors, IP-pool attacker, retry-after exploitation, share-scoped DDoS multiplier. Codex `gpt-5.5` review.
- **NFR16-SCOPE-DESIGNER-GATE-1: Story 22.3 spec authoring gated by designer UX session output.** Designer produces inline UX spec block BEFORE `bmad-create-story` finalizes.

### Decisions

- **Decision W** (architecture): Gallery tier variant pipeline shape.
- **Decision X** (architecture): Blob cache hardening shape (StrictMode + revocation policy).
- **Decision Y** (architecture): Per-token rate-limit middleware shape (Redis sliding window, composable per-IP+per-token).

### Out of scope (intentional)

- **TB-017** date-deferred 2027-05-20.
- **TB-026 sub#1-5** share-view UX enrichment OUT per [[feedback_share_view_scope_boundary]] terminus.
- **TB-032** subsumed by TB-037.
- **TB-022** already shipped via Story 20.3.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-24-init16.md`.
- Architecture extension: `architecture.md` § Initiative 16 (Decisions W + X + Y).
- PRD extension: `prd.md` § Initiative 16 (FR16-* + NFR16-*).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-22 / epic-23 / epic-24 / 25-1-mobile-photo-reorder-touch-action.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]], [[feedback_voice_heavy_dedicated_grilling]], [[feedback_share_view_scope_boundary]], [[feedback_default_to_bmad_workflow]], [[feedback_scp_pre_enumeration_phase]], [[feedback_codex_model_routing]], [[feedback_codex_parallel_review]], [[feedback_pre_merge_gate_checklist]], [[feedback_frontend_visual_verification]], [[feedback_security_vector_enumeration]], [[feedback_auto_deploy_dev]], [[feedback_batch_close_out_rule]], [[feedback_pytest_timeout]], [[feedback_shared_cache_in_react]], [[feedback_worker_single_flight]], [[feedback_collaboration_division]], [[reference_external_test_source]].
- Triage cross-reference: 9 candidates promoted (TB-030 + TB-033 + TB-034 + TB-035 + TB-036 + TB-037 + TB-038 + TB-026 sub#6 per-token + TB-027 verify); 1 housekeeping (TB-029 status flip → done per Init 13 Story 20.2 reconciliation); 1 new TB candidate filed (TB-039 — Init 11-15 H2 backfill housekeeping); 2 declined-defer (TB-017 date-deferred + TB-022 already shipped via Story 20.3); 1 subsumed (TB-032 by TB-037).

## Initiative 17 — Post-Init-16 Operator Hands-On Findings + Housekeeping Sweep

**Status:** 🚧 planning (started 2026-05-24, same session as Init 16 close-out). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-24-init17.md` (status `approved` 2026-05-24). Predecessor Initiative 16 closed 2026-05-24 (aggregate retro at `init-16-retro-2026-05-24.md`). Initiative 17 is a **focused follow-up sweep** clearing the Init 16 close-out tail (5 operator-hands-on findings) plus catch-up housekeeping (TB-039 Init 11-15 H2 backfill, deferred during Init 16 budget pacing). Three epics E26+E27+E28 plus Standalone Story 29.1, ~7 stories total.

### Overview

Init 16 (Triage Backlog Cleanup Batch) shipped 2026-05-24 with 14 commits + 14 deploys to .190 across Epic 22 (image tier pipeline + symmetric fullscreen viewer), Epic 23 (share-view security hardening), Epic 24 (test infra), and Standalone Story 25.1 (mobile drag). Operator hands-on verification post-deploy surfaced 5 findings — all P2/P3, all boring-tech fix-shapes:

- **Epic 26 — Image viewer + carousel UX polish** (TB-044 fullscreen viewer responsive scaling + TB-046 ModelGallery thumb strip variant=thumb): closes user-visible UX regressions on Init 16 NEW Story 22.3 surface + Init 16 follow-up (catalog detail strip).
- **Epic 27 — Share-view burst-mitigation + diagnostic gap** (TB-047 acquireShareBlob semaphore + TB-045 backfill warning file_id): closes Init 12 carry-forward TB-036 root cause + Story 22.1 diagnostic gap.
- **Epic 28 — Catalog admin toolbar polish + viewer hidden-strip P3** (TB-048 AddModelButton alignment + TB-043 hidden-strip coords gesture guard): small CSS polish + Story 22.3 round-3 P3 deferred-to-Init-17 fix.
- **Standalone Story 29.1 — Init 11-15 H2 backfill** (TB-039): doc-only paste-from-SCP into canonical `epics.md` / `prd.md` / `architecture.md`.

Plus inline housekeeping: 4 stale "candidate" status flips (TB-018, TB-022, TB-023, TB-032 — all already DONE via Init 11-15 stories but status field never updated).

### Functional Requirements (compact)

- **FR17-VIEWER-SCALE-1**: Fullscreen image viewer scales to fit available main-frame area, preserving aspect ratio, with strip + nav chevrons always in viewport (`min-h-0` flex shrink-fix + `max-h-[calc(95vh-5rem)]` on main image). **Verifiable:** visual baselines refresh + operator manual verify on 4k/8k portrait + landscape images.
- **FR17-CAROUSEL-THUMB-1**: ModelGallery (catalog detail) thumb strip URLs append `?variant=thumb` (mirror Story 22.2 share-side pattern). **Verifiable:** HAR capture shows strip thumbs serve WebP not original.
- **FR17-SHARE-CONCURRENCY-1**: `acquireShareBlob` in `shareBlobCache.ts` enforces max 4 concurrent in-flight fetches; queue overflows. **Verifiable:** vitest SEMAPHORE-1 + SEMAPHORE-2 tests + post-deploy HAR shows ≤4 simultaneous `/api/share/<token>/files/*` connections.
- **FR17-BACKFILL-DIAGNOSTIC-1**: `thumbnail.unidentified` + `gallery.unidentified` warnings emit `model_file_id=%s storage_path=%s` inline in message body (preserves structured `extra` for GlitchTip). **Verifiable:** re-run backfill on .190; operator captures file_id via grep.
- **FR17-TOOLBAR-ALIGN-1**: AddModelButton vertical-baseline aligns with search input in CatalogList toolbar. **Verifiable:** visual baseline.
- **FR17-VIEWER-GESTURE-1**: ImageFullscreenViewer onTouchStart switches from `strip.contains(e.target)` to coordinate-based `stripOrigin` flag (computed from getBoundingClientRect on strip + touch clientY). Preserves Story 22.3 round-3 `pointer-events-none` patch. **Verifiable:** manual touch verify on hidden vs visible strip.
- **FR17-DOC-BACKFILL-1**: Init 11/13/14/15 H2 sections appended to `prd.md`, `architecture.md`, `epics.md` from `sprint-change-proposal-2026-05-23-init-11-15.md` source. **Verifiable:** `grep '## Initiative 1[1345]'` returns hits in all 3 canonical docs.

### Non-Functional Requirements

- **NFR17-VISUAL-VERIFICATION-1**: Stories 26.1 + 26.2 + 28.1 carry agent-browser visual baseline regen per [[feedback_frontend_visual_verification]].
- **NFR17-DETERMINISM-1**: Carries forward Init 10-16 cross-framework determinism contract. Vitest + pytest 3× consecutive identical pass counts after each story merge.

### Decisions

- **Decision Z** (architecture): Share-view concurrency semaphore shape (cap=4, queue overflow via promise chain in `shareBlobCache.ts`). See `architecture.md` § Initiative 17 Decision Z.

### Out of scope (intentional)

- **TB-017** (TOTP rotation runbook, trigger 2027-05-20) — date-deferred.
- **TB-041 (mentioned only)** — stl_preview orphan cleanup; defensive maintenance; defer.
- **TB-042 (mentioned only)** — main-frame next/prev prefetch; YAGNI for current operator catalog.

### Cross-references

- Predecessor: Initiative 16 — closed 2026-05-24 (aggregate retro at `init-16-retro-2026-05-24.md`).
- Source SCP: `sprint-change-proposal-2026-05-24-init17.md`.
- PRD: `prd.md` § Initiative 17 (FR17-* + NFR17-*).
- Architecture: `architecture.md` § Initiative 17 (Decision Z).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-26 / epic-27 / epic-28 / 29-1-init-11-15-h2-backfill.
- Memory entries: [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]], [[feedback_codex_model_routing]] (all gpt-5.4-mini), [[feedback_frontend_visual_verification]], [[feedback_pre_merge_gate_checklist]], [[feedback_docs_hygiene]] (Story 29.1 closes Init 11-15 H2 backfill debt).
- Triage cross-reference: 7 candidates promoted (TB-039 + TB-043 + TB-044 + TB-045 + TB-046 + TB-047 + TB-048); 4 housekeeping stale-marker flips (TB-018, TB-022, TB-023, TB-032 — all already DONE in prior initiatives).

#### Epic E26 — Image viewer + carousel UX polish

##### Story 26.1 — Fullscreen viewer responsive scaling (FR17-VIEWER-SCALE-1, TB-044)

**Realizes:** FR17-VIEWER-SCALE-1. **Codex tag:** `gpt-5.4-mini`. **Carries:** NFR17-VISUAL-VERIFICATION-1.

Frontend: `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` main-frame flex container gets `min-h-0` class. Main image `renderImage(...)` className changes to `max-h-[calc(95vh-5rem)] max-w-full object-contain`. Visual baselines regen for `catalog-detail-image-viewer-open-*` (4 viewports × light + dark = 8 PNGs).

##### Story 26.2 — ModelGallery strip variant=thumb (FR17-CAROUSEL-THUMB-1, TB-046)

**Realizes:** FR17-CAROUSEL-THUMB-1. **Codex tag:** `gpt-5.4-mini`. **Carries:** NFR17-VISUAL-VERIFICATION-1.

Frontend: `apps/web/src/modules/catalog/components/ModelGallery.tsx` adds `thumbUrlFor(modelId, fileId)` helper. Strip map block uses it instead of raw `srcFor`. Main frame stays on `galleryUrlFor` (Story 22.2 baseline preserved).

#### Epic E27 — Share-view burst-mitigation + diagnostic gap

##### Story 27.1 — acquireShareBlob semaphore cap=4 (FR17-SHARE-CONCURRENCY-1, TB-047)

**Realizes:** FR17-SHARE-CONCURRENCY-1. **Architectural anchor:** Decision Z. **Codex tag:** `gpt-5.4-mini`.

Frontend: `apps/web/src/routes/share/shareBlobCache.ts` adds module-level `_concurrentFetches: number = 0` + `_queue: Array<() => void> = []` + constant `MAX_CONCURRENT_FETCHES = 4`. `acquireShareBlob(src)` cache-miss branches acquire semaphore: `_concurrentFetches < 4` → increment + fetch; else queue release-callback. Cold-fetch resolve decrements + shifts queue. Generation guard (Story 23.1 round-2) preserved. 2 new vitest tests.

##### Story 27.2 — Backfill warning file_id inline (FR17-BACKFILL-DIAGNOSTIC-1, TB-045)

**Realizes:** FR17-BACKFILL-DIAGNOSTIC-1. **Codex tag:** `gpt-5.4-mini`.

Backend: `apps/api/app/workers/generate_thumbnail.py` warning emission format changes to inline `model_file_id=%s storage_path=%s` in message body. Mirror change in `enqueue_thumbnail_backfill.py`. Structured `extra={...}` preserved for GlitchTip.

#### Epic E28 — Catalog admin toolbar polish + viewer hidden-strip P3

##### Story 28.1 — AddModelButton alignment (FR17-TOOLBAR-ALIGN-1, TB-048)

**Realizes:** FR17-TOOLBAR-ALIGN-1. **Codex tag:** `gpt-5.4-mini`. **Carries:** NFR17-VISUAL-VERIFICATION-1.

Frontend: identify alignment-breaking class in `CatalogList.tsx` toolbar or `AddModelButton.tsx`; apply minimal CSS fix (1-3 LOC). Visual baseline regen.

##### Story 28.2 — Viewer hidden-strip coords gesture guard (FR17-VIEWER-GESTURE-1, TB-043)

**Realizes:** FR17-VIEWER-GESTURE-1. **Codex tag:** `gpt-5.4-mini`.

Frontend: `ImageFullscreenViewer.tsx:onTouchStart` switches from `strip.contains(e.target)` to coordinate-based `stripOrigin` flag computed via `stripRef.current?.getBoundingClientRect()` + comparing `touch.clientY` to strip's vertical bounds. `onTouchEnd` suppresses `step()` when `start.stripOrigin === true`. Pre-existing Story 22.3 round-3 `pointer-events-none` on hidden strip preserved (works together with coords check).

#### Standalone Story S29.1 — Init 11-15 H2 backfill (FR17-DOC-BACKFILL-1, TB-039)

**Realizes:** FR17-DOC-BACKFILL-1. **Codex tag:** `gpt-5.4-mini` (optional, doc-only). **Deploy:** SKIPPED per [[feedback_auto_deploy_dev]] doc-only skip clause.

Append Init 11 / 13 / 14 / 15 (meta) H2 sections to `epics.md` / `prd.md` / `architecture.md` from source SCP `sprint-change-proposal-2026-05-23-init-11-15.md`. Init 12 already present (verify; no-op). Init 15 minimal (meta + deferred; single paragraph per doc).


## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md` (status `approved` 2026-05-25). Predecessor Init 17 closed 2026-05-24 (aggregate retro at `init-17-retro-2026-05-24.md`). Init 18 is a **focused post-ship use-case-enumeration-gap correction sweep**: one new epic E30 with three stories closing the membership-path decision tree at `/share/<token>` for B5 (active member receiving share link from another member) without touching anonymous share-view CONTENT (per [[feedback_share_view_scope_boundary]] carve-out 2026-05-25). Phase B (anonymous CONTENT parity) deferred as future-initiative candidate.

### Overview

Brainstorming session 2026-05-25-0030 + Sally UX recommendation (`share-flow-membership-path-ux.md`) produced 3 render modes for `/share/<token>`: (1) anonymous (B1/B2/B3/B4/B6) — unchanged content, new chrome (Sign in + Lang + Theme toggles); (2) enriched member view (B5) — canonical catalog detail UI + dismissible info-bar; (3) request-access page (B7) — deferred. All three operator decisions (Sign in carve-out / Lang+Theme toggles / info-bar dismissal scope) resolved 2026-05-25 before correct-course began. Single epic, three stories, all P2.

### Functional Requirements (compact)

(See `prd.md` § Initiative 18 for full FR text; summary:)

- **FR18-SHARE-RESOLVE-1**: new authenticated endpoint `GET /api/me/share-links/<token>/resolve`.
- **FR18-SHARE-RESOLVE-2**: existing `/api/share/<token>/*` public family stays untouched (NFR10 contract preservation).
- **FR18-FE-CONDITIONAL-RENDER-1**: `/share/<token>` route splits on `useAuth()`.
- **FR18-MEMBER-SHARE-VIEW-1**: `MemberShareView` renders canonical catalog detail UI at share URL.
- **FR18-INFO-BAR-1**: dismissible info-bar with sessionStorage persistence per modelId.
- **FR18-RETURN-URL-1**: Sign in navigates to `/login?next=/share/<token>` via existing `next` convention.
- **FR18-CHROME-ADDITIONS-1**: share-view header gains ThemeToggle + LangToggle + SignInButton (right-aligned, mirrors TopBar order).

### Non-Functional Requirements

- **NFR18-SHARE-ANON-CONTRACT-1**: NFR10 credentialless contract preservation (pre-merge grep invariant).
- **NFR18-TOKEN-ENUMERATION-1**: resolve endpoint uniform 404 for invalid/expired/revoked.
- **NFR18-VISUAL-VERIFICATION-1**: Stories 30.2 + 30.3 carry visual baseline regen per [[feedback_frontend_visual_verification]].
- **NFR18-I18N-PARITY-1**: 5 new i18n keys in BOTH en.json + pl.json (Polish diacritics).
- **NFR18-DETERMINISM-1**: vitest + pytest 3× consecutive identical pass counts after each story merge.

### Decisions

- **Decision AA** (architecture): authenticated share-resolve endpoint at `/api/me/share-links/<token>/resolve` (separate prefix from public `/api/share/<token>/*` family). See `architecture.md` § Initiative 18 Decision AA.
- **Decision AB** (architecture): `/share/*` AppShell chrome bypass conditional on `useAuth()`. See `architecture.md` § Initiative 18 Decision AB.
- **Decision AC** (UX): info-bar dismissal `sessionStorage` per modelId. See `architecture.md` § Initiative 18 Decision AC.

### Out of scope (intentional)

- Phase B (anonymous CONTENT parity) — future-initiative candidate.
- B7 request-access page — defer until granular sharing exists.
- B6 disabled-account richer handling — defer until usage data exists.
- Multi-tab race / session-expiry-mid-view / mid-session account creation — handle ad-hoc.
- Cross-cutting edge cases x-1 through x-8 — handle ad-hoc.
- Path β multi-button SHARE / intent declaration — killed Brainstorm Phase 1.
- Audit emission on resolve endpoint (deferred to follow-up TB if operator wants telemetry).

### Cross-references

- Predecessor: Initiative 17 — closed 2026-05-24.
- Source SCP: `sprint-change-proposal-2026-05-25-init18.md`.
- PRD: `prd.md` § Initiative 18 (FR18-* + NFR18-*).
- Architecture: `architecture.md` § Initiative 18 (Decisions AA + AB + AC).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-30 / 30-1 / 30-2 / 30-3.
- Brainstorm: `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md`.
- UX: `_bmad-output/ux/share-flow-membership-path-ux.md`.
- Memory entries: [[feedback_share_view_scope_boundary]] (amended carve-out), [[feedback_feature_proposal_use_case_enumeration]] (canonical correction precedent), [[feedback_codex_model_routing]] (Story 30.1 → gpt-5.5; Stories 30.2 + 30.3 → gpt-5.4-mini), [[feedback_auth_boundary_contract_audit]] (Story 30.1 hot-spot), [[feedback_security_vector_enumeration]] (Story 30.1 § Threat vectors enumerated), [[feedback_frontend_visual_verification]] (Stories 30.2 + 30.3), [[feedback_pre_merge_gate_checklist]] (all 3 stories), [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]].

#### Epic E30 — Share-Flow Membership-Path Completion

##### Story 30.1 — Authenticated share-resolve endpoint + return-URL plumbing (FR18-SHARE-RESOLVE-1, FR18-SHARE-RESOLVE-2, FR18-RETURN-URL-1 FE-plumbing portion, NFR18-SHARE-ANON-CONTRACT-1, NFR18-TOKEN-ENUMERATION-1)

**Realizes:** FR18-SHARE-RESOLVE-1 + FR18-SHARE-RESOLVE-2 + FR18-RETURN-URL-1 (frontend plumbing portion). **Architectural anchor:** Decision AA. **Codex tag:** `gpt-5.5` (NFR-SECURITY adjacency per [[feedback_security_vector_enumeration]] + [[feedback_auth_boundary_contract_audit]]; new authenticated endpoint sits adjacent to public credentialless bypass family — pre-merge codex review is the operational boundary-preservation gate).

Backend: `apps/api/app/modules/share/member_router.py` adds new endpoint `GET /api/me/share-links/<token>/resolve` returning `ShareResolveResponse(model_id: UUID, access: Literal["granted"])` HTTP 200 for valid token + authenticated caller. Implementation: delegate to `ShareService.resolve(token)` (NEW service method that reads from existing share-token storage; returns model_id or raises `ShareTokenInvalid` for invalid/expired/revoked; uniform exception surfaces as 404). Future B7 hook: `access` field is forward-compat (`Literal["granted"]` today; future `Literal["granted", "request_needed"]` when granular sharing lands).

`apps/api/app/modules/share/service.py`: add `resolve(token: str) -> UUID` method (or `ShareResolveResult` dataclass with `model_id` for forward-compat). MUST mirror existing `validate_active` / `get_by_token` storage-read pattern; MUST NOT add any auth dep at service layer.

Frontend (return-URL plumbing — minor): `apps/web/src/routes/login.tsx` (or wherever login post-success navigation is handled) verify that the existing `next` query-param convention from AppShell anonymous-redirect (Story 11.3 / commit 64447ff) honors arbitrary `/share/<token>` paths. If the existing handler already accepts any relative path starting with `/`, no changes needed — confirm via vitest RU-1. If it whitelists specific path prefixes (security-defensive open-redirect prevention), extend whitelist to include `/share/` prefix. Document the relative-path + same-origin assertion in Story 30.1 spec § Threat vectors.

**Pre-merge invariants (AC enforcement):**

1. `grep -rE "Depends\((get_)?current_(user|admin)\)" apps/api/app/modules/share/router.py` returns ZERO matches (NFR10 credentialless contract preserved).
2. Resolve endpoint dep tree includes `current_user` (positive invariant via FastAPI route introspection in pytest).
3. Token-state-enumeration grep: response bodies for RESOLVE-3 / -4 / -5 are byte-identical (uniform 404).
4. `ShareResolveResponse` model has no field named `expires_at` / `revoked_at` / `created_at` (no token-state leakage in 200 response body).
5. Return-URL handler accepts `/share/<token>` (vitest RU-1) AND rejects absolute URLs / external schemes (vitest RU-2 negative).

**Test target counts:** backend baseline + ~8 new (RESOLVE-1 through -5 + CONTRACT-1 + dep-tree + service-layer-unit); vitest baseline + ~2 new (RU-1, RU-2). NO new visual baselines for Story 30.1 (pure backend + login plumbing).

**Out of scope:** audit emission on resolve (deferred); resolve endpoint paginated list (single-token resolve only); rate-limit on resolve (inherits global auth-scope rate-limit; no per-token throttling — would require new bucket key, defer until needed); B7 "access_needed" branch (forward-compat field present, implementation deferred).

##### Story 30.2 — Frontend conditional render + `MemberShareView` + info-bar (FR18-FE-CONDITIONAL-RENDER-1, FR18-MEMBER-SHARE-VIEW-1, FR18-INFO-BAR-1, NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1 partial)

**Realizes:** FR18-FE-CONDITIONAL-RENDER-1 + FR18-MEMBER-SHARE-VIEW-1 + FR18-INFO-BAR-1. **Architectural anchors:** Decisions AB + AC. **Codex tag:** `gpt-5.4-mini` (FE composition + new component, no security class).

**Depends on:** Story 30.1 (needs resolve endpoint to obtain `model_id` from token).

Frontend route (`apps/web/src/routes/share/$token.tsx`): replace the unconditional anonymous render with `useAuth()`-gated split. Sketch:

```tsx
function ShareTokenRoute() {
  const { token } = Route.useParams();
  const { user } = useAuth();
  if (user !== null) {
    return <MemberShareView token={token} />;
  }
  return <AnonymousShareView token={token} />;  // existing path, extracted
}
```

Existing inline anonymous render extracted into named `AnonymousShareView` component within the same file (no behavior change; just refactor for the split).

AppShell change (`apps/web/src/shell/AppShell.tsx`): bypass condition gains `&& !auth.isAuthenticated` guard per Decision AB. Add explanatory comment referencing Init 18 Decision AB + FR18-MEMBER-SHARE-VIEW-1.

New component `MemberShareView` (file placement decided in spec — either under `apps/web/src/modules/catalog/components/` or `apps/web/src/routes/share/`):

- Calls `useShareResolve(token)` hook (new) that wraps `api("/api/me/share-links/<token>/resolve")` in a `useQuery` with query-key `["share", "resolve", token]`.
- On success, renders the canonical catalog detail component tree with `model_id` (reuse existing `CatalogDetail` / `ModelHero` / `ModelGallery` / STL list / description components from `apps/web/src/modules/catalog/`).
- On 404, renders an explicit "token invalid or expired" message (re-uses anonymous share-view's existing token-invalid copy + Sign in CTA).
- On 401 (defensive — shouldn't happen if AppShell gating is right): triggers AuthContext refresh + falls back to AnonymousShareView.
- Renders `<ShareMemberContextInfoBar modelId={data.model_id} />` at top of main content area.

New component `ShareMemberContextInfoBar`:

- shadcn `Alert` primitive (`variant="default"`).
- Tailwind: `mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm`.
- Icon: `Info` from `lucide-react` `size-4` muted-foreground.
- Action: `<Link to="/catalog/$id" params={{ id: modelId }}>` — TanStack Router-typed.
- Dismiss: close button right-side; sessionStorage key `share-context-dismissed:<modelId>` per Decision AC; safe-fallback for unavailable sessionStorage (always-render + in-memory dismiss for lifetime of component).

New i18n keys (Story 30.2 owns these 3):

- `share.member_context.banner`: "Otworzyłeś ten model z linku udostępnionego." / "You opened this model from a shared link."
- `share.member_context.open_in_catalog`: "Otwórz w katalogu" / "Open in catalog".
- `share.member_context.dismiss_aria`: "Zamknij informację" / "Dismiss notice".

(Story 30.3 owns the remaining 2: `share.view.signin_cta` + `share.view.signin_aria`.)

**Test target counts:**

- Vitest: baseline + ~6 new (CR-1 anonymous render, CR-2 authenticated render, IB-1 renders on first visit, IB-2 hidden after dismiss, IB-3 re-shows for different modelId, IB-4 re-shows new session — IB-4 via sessionStorage.clear() mock).
- Visual (Playwright): NEW spec `apps/web/tests/visual/share-member-enriched.spec.ts` × 4 projects = 4 baseline PNGs covering enriched render with info-bar visible. Second NEW spec `share-member-enriched-dismissed.spec.ts` × 4 projects = 4 baseline PNGs covering enriched render with info-bar dismissed via sessionStorage pre-seed. Total: 8 new baselines bundled in same commit per FR13 Baseline Acceptance Gate.

**Pre-merge invariants:**

1. `useAuth()` import + branching present in `share/$token.tsx`.
2. AppShell `isSharePath` bypass condition includes `!auth.isAuthenticated` guard.
3. `MemberShareView` calls `api("/api/me/share-links/<token>/resolve")` exactly once per token (memoized via `useQuery`).
4. `ShareMemberContextInfoBar` reads sessionStorage on mount with key pattern `share-context-dismissed:<modelId>`.
5. 3 new i18n keys present in BOTH en.json + pl.json with non-empty values (`grep -E "share\.member_context\.(banner|open_in_catalog|dismiss_aria)"`).
6. Visual baselines for 2 new specs × 4 projects = 8 PNGs staged in commit; `baseline-reviewed:` sign-off line present in commit message per FR13.

**Out of scope:** comments / member actions / advanced metadata blocks beyond what `/catalog/$id` already renders (no NEW catalog features in Story 30.2 — pure render reuse); permission-check edge case for member-without-model-access (deferred to B7 follow-up if it materializes; today all members have access to all models).

##### Story 30.3 — Frontend share-view chrome additions (FR18-CHROME-ADDITIONS-1, FR18-RETURN-URL-1 Sign-in-click portion, NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1 partial)

**Realizes:** FR18-CHROME-ADDITIONS-1 + FR18-RETURN-URL-1 (Sign in click navigation portion; backend handler portion lives in Story 30.1). **Codex tag:** `gpt-5.4-mini` (CSS + new component, no security class).

**Independent of:** Stories 30.1 + 30.2 — can land in parallel.

Frontend (`apps/web/src/routes/share/$token.tsx` header section, OR new `apps/web/src/routes/share/ShareHeader.tsx` extracted component — spec authoring decision):

Existing minimal header `<header>Portal 3D · Oglądasz udostępniony model</header>` becomes a two-side flex layout: brand + banner on the left; `<ThemeToggle /> + <LangToggle /> + <SignInButton token={token} />` right-aligned. Right-side control order MUST mirror member TopBar (`ThemeToggle + LangToggle + UserMenu` — UserMenu and SignInButton occupy the same slot semantically). Existing banner text remains (Sally Deliverable 1 rationale: combine, don't replace).

New component `SignInButton`:

```tsx
export function SignInButton({ token }: { token: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => void navigate({ to: "/login", search: { next: `/share/${token}` }, replace: false })}
      aria-label={t("share.view.signin_aria")}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <LogIn className="size-4" />
      {t("share.view.signin_cta")}
    </button>
  );
}
```

Responsive (mobile < 640px): the right-side control group wraps below brand+banner row; OR toggles stay icon-only on mobile (Sally Deliverable 1 sketch — final decision: spec author picks the cleaner shape based on actual viewport behavior, document the choice in Story 30.3 spec). Mobile layout MUST not regress today's banner visibility.

New i18n keys (Story 30.3 owns these 2):

- `share.view.signin_cta`: "Zaloguj się" / "Sign in".
- `share.view.signin_aria`: "Zaloguj się, aby zobaczyć więcej opcji" / "Sign in to access more options".

**Test target counts:**

- Vitest: baseline + ~3 new (CHROME-1 Sign in click navigates to `/login?next=...`, CHROME-2 LangToggle present, CHROME-3 ThemeToggle present).
- Visual (Playwright): EXISTING share-view visual baseline (if present) gets baselines REGENERATED to include the new chrome; OR new spec `share-anonymous-with-signin.spec.ts` × 4 projects = 4 new baseline PNGs (spec authoring decides). Either way: 4 baseline PNGs covering anonymous render with new chrome. Per [[feedback_share_view_scope_boundary]] amended carve-out: visual baseline regen for membership-path chrome is warranted (NOT operator-manual-verify); contrast with anonymous CONTENT changes which would still require operator manual verify.

**Pre-merge invariants:**

1. Share-view header contains `<ThemeToggle />` + `<LangToggle />` + `<SignInButton />` (grep + DOM-assert in vitest).
2. Right-side control order matches member TopBar (ThemeToggle first, LangToggle second, SignInButton/UserMenu third).
3. SignInButton onClick navigates with `search: { next: "/share/<token>" }` (vitest CHROME-1).
4. 2 new i18n keys present in BOTH en.json + pl.json.
5. Mobile layout doesn't crop the banner text (visual baseline regen per [[feedback_frontend_visual_verification]]).
6. Baseline-reviewed sign-off line per FR13 for the 4 regenerated / newly-created PNGs.

**Out of scope:** A/B test of Sign in button placement (Sally Deliverable 1 alternatives — operator-locked Option (a) right-aligned combined-with-banner); SignInButton color/variant experimentation (Tailwind classes locked per Sally Deliverable 1 visual spec); Sign in copy variants ("Have an account? Sign in" etc. — Sally Deliverable 3 locked single string).

#### Standalone stories — none for Init 18

(No standalone stories outside Epic E30 in Init 18 scope.)


## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)

**Status:** 🚧 planning (started 2026-05-29). Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md` (status `approved` 2026-05-29). Predecessor: Init 18 (in-flight; Phase A complete per Init 18 retro 2026-05-29). Init 19 queues behind Init 18 per ITCM autonomous mode convention. Single epic E31, 5 stories (31.1-31.5), all `gpt-5.4-mini` Codex routing (no NFR-SECURITY adjacency).

### Overview

Init 19 integrates the standalone Spoolman instance at `.190:7912` as a read-only inventory mirror, surfaced via a new `/spools` route + a landing-page low-stock card. First portal-side outbound HTTP to a non-observability service. MVP-A scope is read-only visibility only; Phase B (catalog ↔ filament linkage) / Phase C (restricted writes) / Phase D (cost calc UX) / Phase E (share-token inventory snapshot) parked with explicit precondition triggers (see `prd.md` § Initiative 19 § Out of scope). Decision AF in `architecture.md` ensures cost-data is CARRIED end-to-end in MVP-A DTOs so future Phase D lights up without portal-side schema backfill.

### Requirements Inventory

**FR ↔ Epic / Story matrix:**

| FR | Epic | Story | Notes |
|---|---|---|---|
| FR19-LOWSTOCK-1 | E31 | 31.4 | Landing low-stock card; members + admin visible (NOT admin-only per operator decision 2). |
| FR19-SPOOLS-VIEW-1 | E31 | 31.2 (backend) + 31.3 (frontend) | `/spools` route renders inventory list (active spools + active filaments); members + admin visible. |
| FR19-CACHE-1 | E31 | 31.1 | Redis 30s TTL + arq 60s poll + SETNX leader-election per Decision AD. |
| FR19-FAILURE-1 | E31 | 31.3 (frontend FE soft-fail UI) + 31.1 (backend cache-empty handling) | Soft-fail with "Last updated HH:MM" indicator; explicit empty state on cold-start + Spoolman down. |
| FR19-DATA-CARRY-1 | E31 | 31.2 | DTOs surface ALL Spoolman cost-relevant fields per Decision AF; `api-types.gen.ts` mirrors automatically. |

**NFR ↔ Epic / Story matrix:**

| NFR | Epic | Story | Notes |
|---|---|---|---|
| NFR19-NETWORK-1 | E31 | 31.1 (env wiring) + 31.5 (ops doc) | Internal docker network per Decision AE; configs-side coordination PR is a Story 31.1 § Pre-merge precondition. |
| NFR19-OBS-1 | E31 | 31.1 | `external_service=spoolman` tag + OTel span + GlitchTip breadcrumb on every Spoolman client call. |
| NFR19-DETERMINISM-1 | E31 | All stories (pre-merge gate) | 3× consecutive identical pytest + vitest pass counts after each story merge. arq poll idempotent. |
| NFR19-I18N-PARITY-1 | E31 | 31.3 + 31.4 + 31.5 | ~12 new `modules.spools.*` keys in BOTH en.json + pl.json. Material names PCTG/PETG/PLA/TPU untranslated. |
| NFR19-VISUAL-VERIFICATION-1 | E31 | 31.3 + 31.4 + 31.5 | New visual baselines: landing card 4 PNGs + `/spools` index 4 PNGs + soft-fail state 4 PNGs ≈ 12 PNGs across 3 specs. `baseline-reviewed:` sign-off per FR13. |

### Epic List

| Epic | Name | Status | Stories |
|---|---|---|---|
| E31 | Spoolman Read-Only Inventory | 🚧 backlog | 31.1 + 31.2 + 31.3 + 31.4 + 31.5 |

#### Epic E31 — Spoolman Read-Only Inventory

**Goal:** ship the MVP-A baseline cell — read-only `/spools` route + landing low-stock card + backend Spoolman client + Redis cache + arq poll + env config + i18n + ops doc + visual baselines. Single epic spanning backend + frontend + ops. Sequencing: 31.1 → 31.2 → (31.3 ∥ 31.4) → 31.5.

##### Story 31.1 — Backend Spoolman client + Redis cache + arq poll job + env config (FR19-CACHE-1, NFR19-NETWORK-1, NFR19-OBS-1; Decisions AD + AE)

**Realizes:** FR19-CACHE-1 + NFR19-NETWORK-1 + NFR19-OBS-1. Anchors Decisions AD (cache topology + poll cadence + leader-election + observability) and AE (network transport).

**Codex routing:** `gpt-5.4-mini` (read-only outbound HTTP to LAN-only homelab service; no NFR-SECURITY adjacency; no public-bypass family adjacency; no auth boundary changes).

**Sketch:** new `apps/api/app/modules/spools/` package (`__init__.py`, `client.py` for the httpx wrapper, `service.py` for cache + poll logic, `models.py` for Pydantic DTOs — the latter expanded in Story 31.2). Adds `SPOOLMAN_URL` (default `http://spoolman:8000`) + `SPOOLMAN_AUTH_TOKEN` (default empty / unused in MVP-A; reserved for future P3d auth) env slots to `apps/api/app/core/config.py` `Settings`. arq cron `poll_spoolman_summary` registered in `apps/api/app/workers/__init__.py` `WorkerSettings.cron_jobs` (every 60s). Redis SETNX `spools:poll-lock` (90s expiry) acquired before refresh.

**Pre-enumeration save** (per [[feedback_scp_pre_enumeration_phase]] § A):

- **Files reused:** `apps/api/app/core/config.py` (Pydantic `Settings`), `apps/api/app/core/redis.py` (`RedisFactory.get()`), `apps/api/app/workers/__init__.py` (`WorkerSettings` cron registration — established by Init 5 refresh-token cleanup cron at 03:15 UTC).
- **Methods extended:** `Settings` gains 2 fields (`SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN`); `WorkerSettings.cron_jobs` gains 1 cron entry.
- **New service-layer entry points:** `SpoolsService.get_summary()` (cache read; falls through to single live fetch on miss) + `SpoolsService.refresh_summary()` (cron-driven, lock-protected).
- **Test fixtures:** pytest with httpx mock per Decision AD § Testing (P14a) for unit speed; ONE env-gated live integration test keyed off `SPOOLMAN_LIVE_TEST=1` (P14d) pinning the contract against a real Spoolman instance.
- **Contracts enforced:** new `external_service=spoolman` tag is a pre-merge grep invariant. Response bodies NEVER logged at INFO — entity counts only.
- **Defensive policies adjacent:** none reversed; cache topology is greenfield for the `spools:summary:v1` key.

**Pre-merge precondition (OD8 close-out):** configs-side side verifies the Spoolman compose binds to a non-routable host interface (NOT `0.0.0.0` exposed via the router). **NOT a 3d-portal commit.** Documented in `docs/operations.md` addendum (Story 31.5 owns the doc; Story 31.1 owns the verification gate language).

**Test target counts:**

- pytest with httpx mock: cache hit (cache-warm path returns cached snapshot, no client call), cache miss (cold-start path falls through to single live fetch + cache SET), lock contention (two parallel `refresh_summary()` calls — only one acquires SETNX), Spoolman timeout (5s default; circuit breaker opens after 3 consecutive failures + auto-closes after 30s), Spoolman 5xx response (handled identically to timeout). ≈ 5-7 new pytest cases in `apps/api/tests/test_spools.py`.
- env-gated `SPOOLMAN_LIVE_TEST=1` integration test: skipped by default (CI green without Spoolman access); pinning contract against `http://localhost:7912/api/v1/*` when explicitly enabled.

**Pre-merge invariants:**

1. `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` present in `apps/api/app/core/config.py` `Settings`.
2. arq cron `poll_spoolman_summary` registered in `apps/api/app/workers/__init__.py`.
3. `external_service=spoolman` grep returns hits in `apps/api/app/modules/spools/client.py`.
4. Response-body grep on `logger.info` in `apps/api/app/modules/spools/` returns ZERO hits (response bodies not logged at INFO).
5. Redis SETNX lock key `spools:poll-lock` + 90s expiry present.
6. Configs-side Spoolman bind verification documented (Story 31.5 ops-doc addendum lands the verification recipe; Story 31.1 commit message references the OD8 close-out).

**Out of scope:** mutation surface (use/measure/CRUD); cost arithmetic; per-spool detail page; multi-instance support; websocket subscription. All parked with explicit triggers in `prd.md` § Out of scope.

##### Story 31.2 — Backend `/api/spools/*` routes + DTOs with cost-data carry-through (FR19-SPOOLS-VIEW-1, FR19-DATA-CARRY-1; Decision AF)

**Realizes:** FR19-SPOOLS-VIEW-1 + FR19-DATA-CARRY-1. Anchors Decision AF (data-model carry-through).

**Codex routing:** `gpt-5.4-mini` (DTO + route work; no auth boundary changes; no NFR-SECURITY adjacency).

**Depends on:** Story 31.1 (needs `SpoolsService.get_summary()` to serve route responses).

**Sketch:** new `apps/api/app/modules/spools/router.py` with three routes: `GET /api/spools/summary` (low-stock + entity counts for the landing card), `GET /api/spools/spools` (active spools list for `/spools` index), `GET /api/spools/filaments` (active filaments list — mirrors Spoolman's filament-as-SKU vs spool-as-physical-instance distinction per OD9). All routes use `Depends(current_user)` per operator decision 2 (members + admin visible). All routes added to `_PUBLIC_ROUTES` allowlist is **explicitly NOT done** (NFR6 default-deny posture preserved — `/api/spools/*` requires auth).

**Pre-enumeration save:**

- **Files reused:** `apps/api/app/main.py` (router registration), `apps/api/app/core/auth.py` (`current_user` dep — Init 5 Decision C). DTOs from Story 31.1 (`SpoolView`, `FilamentView` minimal subset) expanded with full Decision AF cost-relevant fields.
- **Methods extended:** `SpoolsService.get_summary()` adds threshold-aware low-stock filtering (`remaining_weight < SPOOLMAN_LOW_STOCK_THRESHOLD_G` env-tunable, default 200g).
- **Service-layer entry point:** `SpoolsService.get_low_stock()` + `SpoolsService.list_spools()` + `SpoolsService.list_filaments()`.
- **Test fixtures:** existing `client` fixture; existing `authed_member_client` + `authed_admin_client` (Init 5); httpx-mocked Spoolman via Story 31.1's mock fixture.
- **Contracts enforced:** `Depends(current_user)` (NOT `current_admin`) per operator decision 2; route-enforcement pytest gate from Init 6 automatically covers this. NFR10 credentialless contract on `/api/share/<token>/*` UNTOUCHED (Init 19 introduces a new auth-bearing surface but does NOT touch share routes).
- **Defensive policies adjacent:** none reversed.

**Test target counts:**

- pytest in `apps/api/tests/test_spools_router.py`: 6 routes × happy + auth-required = ~12 cases (anonymous returns 401, member returns 200, admin returns 200). DTO schema invariant test verifies ALL Decision AF cost-relevant fields present in the response body (FR19-DATA-CARRY-1 contract assertion). Low-stock threshold filter test (sample spool below threshold → present in `/summary`; above → absent).
- api-types regeneration: `apps/web/src/lib/api-types.gen.ts` regenerated after route landing (existing OpenAPI generation pipeline).

**Pre-merge invariants:**

1. `Depends(current_user)` (NOT `current_admin`) on all three routes — grep + endpoint-introspection pytest gate.
2. `_PUBLIC_ROUTES` allowlist in `apps/api/app/main.py` UNCHANGED (no new public route).
3. NFR10 credentialless contract preserved: `Depends(current_user)` MUST NOT appear in `apps/api/app/modules/share/router.py` (grep invariant carried forward from Init 18).
4. All Decision AF cost-relevant fields present in DTO serialization (pytest schema invariant).
5. `api-types.gen.ts` regenerated; field set matches Decision AF.

**Out of scope:** cost arithmetic; per-spool detail route; mutation endpoints; share-token inventory snapshot.

##### Story 31.3 — Frontend `/spools` route + index page + states (FR19-SPOOLS-VIEW-1, FR19-FAILURE-1, NFR19-VISUAL-VERIFICATION-1, NFR19-I18N-PARITY-1 partial)

**Realizes:** FR19-SPOOLS-VIEW-1 (frontend half) + FR19-FAILURE-1 (UI soft-fail) + NFR19-VISUAL-VERIFICATION-1 (4 baselines) + NFR19-I18N-PARITY-1 (subset).

**Codex routing:** `gpt-5.4-mini` (pure FE composition; no security class).

**Depends on:** Story 31.2 (needs `/api/spools/*` routes to drive `useSpoolsSummary` hook).

**Sketch:** replace `apps/web/src/routes/spools/index.tsx` `<ComingSoonStub moduleKey="spools" />` with real component tree. New `apps/web/src/modules/spools/components/SpoolsIndexPage.tsx` + `apps/web/src/modules/spools/hooks/useSpoolsSummary.ts` (TanStack Query, `["spools", "summary"]` query-key, `staleTime: 60_000`, `gcTime: 5 * 60_000` per Decision AD magic-constant contracts). States: loading skeleton, populated list, empty (Spoolman returns zero spools — operator deliberately archived all), soft-fail (cache present + Spoolman currently down), error (cold-start + Spoolman down).

**Pre-enumeration save:**

- **Files reused:** `apps/web/src/lib/api.ts` (`api()` fetch wrapper with cookie + CSRF header automation); shadcn primitives (`Card`, `Skeleton`, `Alert`); `useTranslation` from `react-i18next`.
- **Existing route shell:** `apps/web/src/routes/spools/index.tsx` ships a `<ComingSoonStub />` — replace with `<SpoolsIndexPage />`. `apps/web/src/shell/ModuleRail.tsx:11` already routes to `/spools` (the link exists; just the page is a stub).
- **Contracts enforced:** AppShell `AuthGate` already redirects anonymous visitors to `/login?next=/spools`; component-level role gating NOT added (members + admin both visible per operator decision 2).
- **Cache-topology table** (per [[feedback_scp_pre_enumeration_phase]] § B — Story 31.3 reads from a queryKey no other route touches today):

  | Concern | Source: Story 31.3 | Source: any related route/hook |
  |---|---|---|
  | Staleness budget (`staleTime`) | `60_000` per Decision AD (matches arq poll cadence) | n/a — single consumer (landing card is Story 31.4, will share the same hook) |
  | Retry policy | TanStack default (single retry on 5xx; no retry on 4xx) | n/a |
  | Cache propagation on mutations | n/a (read-only mirror; no mutations in MVP-A) | n/a |
  | Cache eviction on route exit | none (cache survives navigation; landing card revisit is warm) | n/a |
  | Cache seeding on this route | none (arq poll seeds the Redis backend; FE just reads via API) | landing low-stock card (Story 31.4) shares the same hook |

  Decision rule: both columns agree (only Story 31.3 + 31.4 own this queryKey; Story 31.4 inherits the same topology via `useSpoolsSummary` reuse) → simple shared-cache reuse is fine; no spec call-out needed beyond Story 31.4's depends-on Story 31.3.

**New i18n keys (Story 31.3 owns the index-page subset):**

- `modules.spools.index.title`: "Filamenty i szpule" / "Filaments and spools".
- `modules.spools.index.spools_section_title`: "Aktywne szpule" / "Active spools".
- `modules.spools.index.filaments_section_title`: "Aktywne filamenty" / "Active filaments".
- `modules.spools.index.empty`: "Brak aktywnych szpul w Spoolman." / "No active spools in Spoolman."
- `modules.spools.states.loading`: "Wczytywanie inwentarza…" / "Loading inventory…".
- `modules.spools.states.last_updated`: "Ostatnia aktualizacja: {{time}} ({{ago}})" / "Last updated: {{time}} ({{ago}})".
- `modules.spools.states.spoolman_unavailable`: "Spoolman jest tymczasowo niedostępny." / "Spoolman is temporarily unavailable."

**Test target counts:**

- vitest in `apps/web/src/modules/spools/components/SpoolsIndexPage.test.tsx`: ≈ 5 cases — happy (renders list), empty (Spoolman has zero active), loading skeleton, soft-fail (`isFetching: false` + cached data + sibling `last-success-ts` stale), error (cold-start + no cache + 5xx).
- Playwright NEW spec `apps/web/tests/visual/spools-index.spec.ts` × 4 projects = 4 baselines covering the populated state. Soft-fail and empty-state baselines belong to Story 31.4 / 31.5 visual baseline coverage to keep Story 31.3 footprint focused.

**Pre-merge invariants:**

1. `apps/web/src/routes/spools/index.tsx` no longer renders `ComingSoonStub`.
2. `useSpoolsSummary` hook uses `queryKey: ["spools", "summary"]` + `staleTime: 60_000` + `gcTime: 5 * 60_000` (magic-constant contract pointing per Decision AD).
3. 7 new i18n keys present in BOTH `en.json` and `pl.json` with non-empty values (`grep -E "modules\\.spools\\.(index|states)\\."`).
4. 4 visual baselines staged in commit; `baseline-reviewed:` sign-off line in commit message per FR13.

**Out of scope:** per-spool detail navigation (defer to future Phase B); cost arithmetic display (Phase D); spool/filament filtering UI (YAGNI for current 9-spool/16-filament instance); cross-link to catalog detail (Phase B).

##### Story 31.4 — Frontend landing low-stock card (FR19-LOWSTOCK-1, NFR19-VISUAL-VERIFICATION-1, NFR19-I18N-PARITY-1 partial)

**Realizes:** FR19-LOWSTOCK-1 + NFR19-VISUAL-VERIFICATION-1 (4 + 4 = 8 PNG baselines: 4 happy + 4 soft-fail) + NFR19-I18N-PARITY-1 (subset).

**Codex routing:** `gpt-5.4-mini` (pure FE composition; no security class).

**Depends on:** Story 31.2 (needs `/api/spools/summary` route to drive the hook). Independent of Story 31.3 (different mount points; share the same `useSpoolsSummary` hook).

**Sketch:** new `apps/web/src/modules/spools/components/LowStockCard.tsx`. Mounted on the landing dashboard page (locate current landing implementation in `apps/web/src/routes/index.tsx` or equivalent; Story 31.4 author confirms exact mount point at spec time). Threshold from env (default 200g; backend filters via `/api/spools/summary` per Story 31.2). Card displays each below-threshold spool: vendor + material + color swatch + `remaining_weight` + % remaining bar. Empty state: "Wszystkie szpule mają zapas" / "All spools fully stocked" (suppresses card render if zero items).

**Pre-enumeration save:**

- **Files reused:** shadcn `Card` primitive; shared `useSpoolsSummary` hook from Story 31.3; `apps/web/src/lib/api.ts` `api()` wrapper.
- **Mount point:** landing dashboard (`apps/web/src/routes/index.tsx`); the landing page is the post-login default per AppShell routing — currently authenticated landing layout includes catalog summary cards.
- **Contracts enforced:** members + admin both see the card (no role gating). Anonymous visitors never reach landing (AppShell `AuthGate` redirects). Card visible alongside catalog summary cards — no displacement.

**New i18n keys (Story 31.4 owns the landing-card subset):**

- `modules.spools.lowstock.card_title`: "Niskie zapasy" / "Low stock".
- `modules.spools.lowstock.threshold_hint`: "Próg: {{threshold_g}}g" / "Threshold: {{threshold_g}}g".
- `modules.spools.lowstock.empty`: "Wszystkie szpule mają zapas." / "All spools fully stocked."
- `modules.spools.lowstock.remaining_g`: "{{remaining}}g pozostało" / "{{remaining}}g remaining".

**Test target counts:**

- vitest in `apps/web/src/modules/spools/components/LowStockCard.test.tsx`: ≈ 4 cases — happy (lists below-threshold spools), empty (zero below-threshold), soft-fail (cache present + Spoolman down — banner indicator visible), threshold respected (above-threshold spool absent).
- Playwright NEW spec `apps/web/tests/visual/landing-low-stock.spec.ts` × 4 projects = 4 happy baselines (one of which captures the two real low-stock spools at session start per brainstorm B5 signal — PLA Speed Matt White 138.9g + PCTG Army Green 163.2g). Soft-fail variant baseline spec `apps/web/tests/visual/landing-low-stock-softfail.spec.ts` × 4 projects = 4 more PNGs. Total: 8 new baselines bundled in commit per FR13.

**Pre-merge invariants:**

1. `<LowStockCard />` mounted on landing dashboard route.
2. Threshold env wiring resolves; default 200g surfaces on first visit (verify via mocked fixture in vitest).
3. 4 new i18n keys present in BOTH `en.json` and `pl.json` (`grep -E "modules\\.spools\\.lowstock\\."`).
4. 8 visual baselines staged in commit; `baseline-reviewed:` sign-off line per FR13.

**Out of scope:** click-through navigation to per-spool detail (Phase B); cost arithmetic on the card (Phase D); admin-only visibility variant (overridden by operator decision 2).

##### Story 31.5 — i18n parity finalization + ops doc + visual baseline regen of any affected existing specs (NFR19-I18N-PARITY-1, NFR19-VISUAL-VERIFICATION-1)

**Realizes:** NFR19-I18N-PARITY-1 (final parity sweep) + NFR19-VISUAL-VERIFICATION-1 (regen any existing baselines that drift due to landing-page mount changes from Story 31.4).

**Codex routing:** `gpt-5.4-mini` (docs + i18n + visual baseline regen; no code class).

**Depends on:** Stories 31.3 + 31.4 (must land first so the i18n key inventory is final and any landing-page baseline drift is observable).

**Sketch:**

- Parity sweep: confirm all `modules.spools.*` keys added by Stories 31.3 + 31.4 are present in BOTH `en.json` and `pl.json`; fill any gaps. Verify Polish diacritics (ą / ę / ó / ł / etc.) render correctly in the running app via `npm run dev` smoke. Material names PCTG / PETG / PLA / TPU stay untranslated (P15c — codified as a comment in `pl.json` near the locale section if not already present).
- Ops doc: `docs/operations.md` addendum documenting (a) `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` + `SPOOLMAN_LOW_STOCK_THRESHOLD_G` env slots; (b) soft-fail behavior (cache survives Spoolman outage with explicit "Last updated HH:MM" indicator); (c) how to verify Spoolman bind address on `.190` (the OD8 close-out recipe — verify the configs-side compose binds to non-routable interface NOT `0.0.0.0`); (d) operator-facing troubleshooting: where to look in GlitchTip if Spoolman polling alerts surface (breadcrumb category `spoolman.client`).
- Baseline regen: if the landing-page baseline drifts due to Story 31.4's card mount (likely — the card occupies dashboard real estate), regenerate the affected existing landing-page baselines with `--update-snapshots` and bundle the new PNGs with `baseline-reviewed:` sign-off per FR13. Apply [[feedback_visual_failure_mode_triage]] discipline: classify each drift as `stale-baseline` (regen OK) vs `deterministic-fail` (real regression — STOP).

**Pre-enumeration save:**

- **Files reused:** `apps/web/src/locales/en.json` + `pl.json`; `docs/operations.md`; existing visual specs that touch the landing page.
- **No new components:** Story 31.5 is i18n + docs + baseline-regen-only.
- **Contracts enforced:** [[feedback_visual_failure_mode_triage]] discipline — blanket regen masks real regressions, so each drift gets classified before regen.

**Test target counts:**

- No new vitest / pytest. i18n grep invariant: every `modules.spools.*` key in en.json present in pl.json with non-empty value (and vice versa).
- Playwright regen: any landing-page baseline that drifts due to Story 31.4's card mount; count depends on which existing baselines touch the landing page.

**Pre-merge invariants:**

1. `modules.spools.*` parity grep: zero one-sided keys.
2. `docs/operations.md` addendum present (Spoolman env slots + soft-fail behavior + OD8 verification recipe + GlitchTip troubleshooting pointer).
3. Material-names-untranslated comment present in `pl.json`.
4. Any regenerated existing baseline includes `baseline-reviewed:` sign-off line in commit message per FR13.

**Out of scope:** new visual baselines beyond Story 31.3 + 31.4's own specs (those are owned by their respective stories); new ops runbooks beyond the addendum; new memory entries (none warranted by this MVP-A pass).

#### Standalone stories — none for Init 19

(No standalone stories outside Epic E31 in Init 19 scope.)

## Initiative 20 — STL Slicer Estimates (Per-Part MVP)

**Status:** 🚧 planning (started 2026-05-31). Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` (status `approved` 2026-05-31 — approval scoped to planning-artifact appends, NOT code; implementation planning remains BLOCKED per SCP § 5). Predecessor: Init 19 (Spoolman) — Init 20 queues behind Init 19 close-out per ITCM convention and consumes the Spoolman inventory SoT. Single epic E32, 6 stories (32.1-32.6). Architecture: `architecture.md` § Initiative 20 (Decisions AH + AI + AJ).

> **Story breakdown is epic-level sketch.** Full acceptance criteria, task lists, pre-enumeration saves, test-target counts, and Codex routing are produced per story by `bmad-create-story` at dev-entry time. The OD gate (OD-1/OD-2/OD-7/OD-8/OD-9, PRD § Open decisions) was **RESOLVED 2026-05-31** by operator delegation, which cleared authoring of the **Story 32.1** spec (`_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md`, status `ready-for-dev`). Stories 32.2–32.6 remain `backlog` with no spec files — they are authored individually at their own dev-entry time. **Resolving the OD gate did NOT authorize dev-story execution / code implementation of any story** — that remains gated on an explicit operator go per SCP § 5.

### Overview

Init 20 ships **per-STL** slicer estimates (print time, filament mass/length/volume, informational cost, classified warnings) via a real headless OrcaSlicer slice in a containerized worker, with results cached keyed `(stl_hash, bundle_hash)` so they only recompute when a meaningful input changes. A request/basket total is a **linear sum** of per-STL estimate × quantity — there is no whole-plate / whole-basket slicing. The user-facing `PrintIntentPreset` is separated from the internal resolved `SlicerProfileBundle`. Spoolman stays the inventory SoT; Fenrir is the research/export bench only (no production dependency). Feasibility was proved on the bench for PLA + TPU; adaptive layer height is gated on a proven negative.

### Requirements Inventory

**FR ↔ Epic / Story matrix:**

| FR | Epic | Story | Notes |
|---|---|---|---|
| FR20-RESOLVER-1 | E32 | 32.1 | Orca system+user inheritance merge + normalize + validate + hash + snapshot. Resolver precedence: exact bundle > custom override > material default > unsupported. Anchors Decision AH. |
| FR20-ESTIMATE-1 | E32 | 32.2 (slice) + 32.3 (parse) | Headless slice produces g-code; pure parser emits typed `EstimateRecord` with attribution. Anchors Decisions AI + AJ. |
| FR20-CACHE-1 | E32 | 32.3 | `(stl_hash, bundle_hash)` cache schema + cost-carry fields + dedup. Anchors Decision AJ. |
| FR20-FAILURE-1 | E32 | 32.2 (worker classify) + 32.6 (FE soft-fail) | Warnings non-blocking; failures explicit; soft-fail "Last estimated HH:MM (Xm ago)". |
| FR20-SPOOLMAN-MAP-1 | E32 | 32.5 | Spoolman `filament.extra` → resolved filament JSON overrides (esp. TPU volumetric speed); folded into `bundle_hash`. |
| FR20-PRESET-1 | E32 | 32.6 | `PrintIntentPreset` selector ↔ `SlicerProfileBundle` separation; preset never leaks Orca internals. |

**NFR ↔ Epic / Story matrix:**

| NFR | Epic | Story | Notes |
|---|---|---|---|
| NFR20-REPRODUCIBLE-1 | E32 | 32.4 | Hash-driven invalidation; **cost-only changes recompute arithmetically (no re-slice)** — the load-bearing efficiency rule (Decision AJ / OD-7). |
| NFR20-CONTAINER-1 | E32 | 32.2 | Orca headless in a dedicated container; no Fenrir production dependency; configs-side compose PR (NOT a 3d-portal commit). |
| NFR20-ATTRIBUTION-1 | E32 | 32.3 | `settings_ids` from g-code on every record. |
| NFR20-RESOURCE-1 | E32 | 32.2 (concurrency cap) + 32.4 (dedup) | Bounded slice concurrency + no recompute storms. |
| NFR20-OBS-1 | E32 | 32.2 + 32.5 | Slicer-worker + Spoolman-read instrumentation per the observability-logging contract. |
| NFR20-DETERMINISM-1 | E32 | All stories (pre-merge gate) | 3× consecutive identical pytest + vitest pass counts; arq slice job idempotent on the key. |
| NFR20-I18N-PARITY-1 | E32 | 32.6 | `modules.estimates.*` / `modules.slicer.*` keys in BOTH en.json + pl.json. Material names untranslated. |
| NFR20-VISUAL-VERIFICATION-1 | E32 | 32.6 | New baselines for estimate display + preset selector + soft-fail/warning/failure states × 4 projects. |

### Epic List

| Epic | Name | Status | Stories |
|---|---|---|---|
| E32 | STL Slicer Estimates (Per-Part MVP) | 🚧 backlog | 32.1 + 32.2 + 32.3 + 32.4 + 32.5 + 32.6 |

#### Epic E32 — STL Slicer Estimates (Per-Part MVP)

**Goal:** ship the per-STL estimate MVP — profile resolver, containerized headless slicer worker, g-code parse + cache, hash-driven invalidation with cost-only arithmetic recompute, Spoolman-mapped overrides, and the frontend preset selector + estimate display. Backend + worker + frontend, plus a configs-side slicer-worker compose PR (coordinated, NOT a 3d-portal commit). **Sequencing:** 32.1 → 32.2 → 32.3 → 32.4 → 32.5 → (32.6 follows once 32.3 serves estimates; 32.5 and 32.6 can overlap). Each story carries the NFR20-DETERMINISM-1 pre-merge gate; the frontend story carries NFR20-I18N-PARITY-1 + NFR20-VISUAL-VERIFICATION-1.

##### Story 32.1 — Profile resolver: inheritance merge + normalize + validate + hash + snapshot (FR20-RESOLVER-1; Decision AH)

**Realizes:** FR20-RESOLVER-1. Anchors Decision AH.

**Sketch:** new `apps/api/app/modules/slicer/` package with the resolver: recursively merge the vendored Orca system profile tree with the user partials (user wins), inject top-level `type`, drop the instantiation field, apply the Spoolman override layer (consumed from Story 32.5; stub-tolerant until then), validate via a dry `--info` / minimal-slice smoke + a required-key schema assertion (`filament_max_volumetric_speed` for TPU), compute canonicalized `bundle_hash = H(machine ∥ process ∥ filament ∥ orca_version)`, and persist `SlicerProfileBundle` + `SourceProfileSnapshot` (append-only). Resolver precedence: exact bundle > custom override > material-class default > unsupported (unsupported ⇒ classified failure, never silent fallback). Productionizes the proven `orca_resolve_profiles.py` path. One-time Fenrir-bench export of resolved profiles into vendored artifacts (bench step, not a prod dependency).

**Depends on:** none (first story; foundational). **Coordinates with:** 32.5 for the override-layer interface.

**Test targets (sketched; finalized by bmad-create-story):** pytest on the merge/normalize path with PLA + TPU fixtures; hash-stability assertion (cosmetic JSON churn ⇒ stable hash); CLI-acceptance smoke (resolved triple accepted by Orca `--info`); precedence-resolution cases incl. the unsupported→failure branch.

**Out of scope:** the slice itself (32.2); cache/estimate records (32.3); live Spoolman read (32.5); adaptive layer height (gated).

##### Story 32.2 — Containerized headless OrcaSlicer worker: job shape + CLI invoke + failure classification (FR20-ESTIMATE-1 slice half, FR20-FAILURE-1 worker half, NFR20-CONTAINER-1, NFR20-RESOURCE-1, NFR20-OBS-1; Decision AI)

**Realizes:** FR20-ESTIMATE-1 (slice half) + FR20-FAILURE-1 (worker classification) + NFR20-CONTAINER-1 + NFR20-RESOURCE-1 (concurrency cap) + NFR20-OBS-1. Anchors Decision AI.

**Sketch:** app-side worker client in `apps/api/app/modules/slicer/` that takes the `(stl_ref, bundle_ref)` 2-tuple, runs Orca `--info` as a cheap manifold pre-check, invokes the headless CLI slice with the resolved triple + STL, and emits g-code to a temp path (parse-and-discard handled in 32.3). Failure classification: warnings (non-blocking) vs failures (non-manifold, non-zero exit, CLI-rejected profile, parse failure, timeout → `status: failed` + reason). Bounded slice concurrency (small cap, OD-6). STL cache layout `<cache_root>/stl/<hash[:2]>/<hash>.stl`. **Configs-side coordination (NOT a 3d-portal commit):** `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` PR adds the dedicated container (OrcaSlicer 2.3.2 AppImage + verified deps; `--appimage-extract` path — spike per risk R3) + network topology; `infra/.env.example` gains `ORCA_VERSION` + `FENRIR_EXPORT_PATH` slots (`FENRIR_EXPORT_PATH` is a **bench-only** export path, NOT a production runtime path — per Decision AI / NFR20-CONTAINER-1, no `/mnt/c` path appears in production config).

**Depends on:** 32.1 (needs resolved bundles to feed the slice).

**Test targets (sketched):** pytest on the worker client with a mocked Orca invocation (happy slice, warning slice, each failure branch); concurrency-cap assertion; `--info` pre-check fast-fail on a non-manifold fixture. AppImage-in-container is verified out-of-band (configs-side smoke) since CI cannot run the AppImage.

**Out of scope:** g-code parsing + cache write (32.3); invalidation (32.4); the resolver (32.1); g-code retention (parse-and-discard).

##### Story 32.3 — G-code metadata parse + `(stl_hash, bundle_hash)` cache schema + cost-carry fields (FR20-ESTIMATE-1 parse half, FR20-CACHE-1, NFR20-ATTRIBUTION-1; Decision AJ)

**Realizes:** FR20-ESTIMATE-1 (parse half) + FR20-CACHE-1 + NFR20-ATTRIBUTION-1. Anchors Decision AJ.

**Sketch:** a small **pure, unit-testable** parser (g-code text in → typed `EstimateRecord` struct out) over the confirmed-present metadata lines; time strings (`3h35m47s`) normalize to seconds; missing/garbled lines ⇒ classified failure, never a silent zero. `EstimateRecord` keyed `(stl_hash, bundle_hash)` with `time_seconds`, `filament_g`, `filament_mm`, `filament_cm3`, `filament_cost`, `settings_ids` (attribution), `warnings`, `status`, `computed_at`. Cache read/write + dedup on the key (a `fresh` recompute is a no-op). Cost field is carried so cost-only recompute (32.4) can update it arithmetically.

**Depends on:** 32.2 (needs g-code output). **Unblocks:** 32.4 + 32.6.

**Test targets (sketched):** parser fixtures captured from the proven PLA (76.76 g / 3h35m47s) + TPU (77.25 g / 8h06m05s) slices; time-string normalization edge cases; missing-line → failure; cache hit/miss/dedup; `settings_ids` attribution invariant.

**Out of scope:** invalidation triggers (32.4); the slice (32.2); FE display (32.6).

##### Story 32.4 — Invalidation rules + recompute queue + cost-only arithmetic recompute (FR20-CACHE-1 invalidation, NFR20-REPRODUCIBLE-1, NFR20-RESOURCE-1 dedup; Decision AJ)

**Realizes:** FR20-CACHE-1 (invalidation) + NFR20-REPRODUCIBLE-1 + NFR20-RESOURCE-1 (recompute dedup). Anchors Decision AJ (recompute-trigger table).

**Sketch:** implement the exhaustive recompute-trigger table — STL content change (`stl_hash`), bundle re-tune (new `bundle_hash`), Orca upgrade (`orca_version` ∈ hash), Spoolman mapped-override change (`spoolman_overrides_ref` folded into hash). **Critical:** a Spoolman **cost-only** change (`spool.price`, density unchanged) recomputes the cost field **arithmetically without re-slicing** (`cost = mass × price/gram`, or `spool.price` override) — never enqueues a slice (prevents the R1 recompute-storm DoS). Stale records served with an explicit `stale` flag + queued; recompute idempotent + deduped on the key.

**Depends on:** 32.3 (needs `EstimateRecord` + cache). **Coordinates with:** 32.5 (the mapped-override-change trigger).

**Test targets (sketched):** each trigger-table row → correct stale/recompute behavior; **the load-bearing test** — a cost-only Spoolman change updates the cost field WITHOUT invoking the slicer worker, in <1s; staleness flag served, not hidden; idempotent recompute on a `fresh` record.

**Out of scope:** the slice (32.2); FE staleness UI (32.6); g-code retention.

##### Story 32.5 — Spoolman-mapped custom filament overrides (FR20-SPOOLMAN-MAP-1, NFR20-OBS-1; Decisions AH override layer + AJ linkage)

**Realizes:** FR20-SPOOLMAN-MAP-1 + NFR20-OBS-1 (Spoolman-read instrumentation). Anchors Decision AH § override layer + Decision AJ § Spoolman linkage.

**Sketch:** map Spoolman `filament.extra` fields (and the inherited `filament.extra.url` purchase link) onto the resolved filament JSON — **especially `filament_max_volumetric_speed`, nozzle/bed temps, density for TPU and unusual filaments** where the generic class default is wrong. Link by profile-style reference (Init 19 B2 insight — isolate from Spoolman entity churn), reusing the Init 19 Spoolman client/cache. Override set captured in `spoolman_overrides_ref` + folded into `bundle_hash` so a mapped-field change invalidates dependent estimates (the trigger consumed by 32.4). Spoolman stays inventory SoT — read-only consumption, no duplication.

**Depends on:** 32.1 (resolver override layer) + Init 19 Spoolman client. **Feeds:** 32.4 (mapped-override-change trigger).

**Test targets (sketched):** TPU volumetric-speed override correctly clamps the resolved filament JSON; a mapped-field change re-hashes the bundle + marks dependent estimates stale; Spoolman read tagged `external_service=spoolman`; cost-only field change does NOT re-hash (routes to 32.4 arithmetic path).

**Out of scope:** cost arithmetic itself (32.4); inventory mutation (Spoolman owns it); non-mapped filament fields.

##### Story 32.6 — Frontend `PrintIntentPreset` selector + estimate display + soft-fail/warning/failure states (FR20-PRESET-1, FR20-FAILURE-1 FE half, NFR20-I18N-PARITY-1, NFR20-VISUAL-VERIFICATION-1)

**Realizes:** FR20-PRESET-1 + FR20-FAILURE-1 (FE soft-fail/warning/failure UI) + NFR20-I18N-PARITY-1 + NFR20-VISUAL-VERIFICATION-1.

**Sketch:** new `apps/web/src/modules/estimates/` — a `PrintIntentPreset` selector (material class ∈ {PLA, PETG, PCTG, TPU}, quality tier, optional pinned spool/overrides) and an estimate display on the catalog detail + request/queue surfaces showing time / mass / length / volume / informational cost + classified warnings. States: loading, populated, `stale` (explicit "estimate may be out of date, recomputing"), soft-fail ("Last estimated HH:MM (Xm ago)"), failure ("couldn't estimate, here's why"). The preset MUST NOT leak Orca internals (no raw layer-height floats, no `filament_max_volumetric_speed` in the UI). i18n parity for all new keys; new visual baselines × 4 projects with `baseline-reviewed:` sign-off per FR13.

**Depends on:** 32.3 (needs the estimate API) + 32.4 (staleness states).

**Test targets (sketched):** vitest on the selector + each display state; an invariant test asserting no Orca-internal field names render in the preset surface; Playwright baselines for populated + stale + soft-fail + warning + failure states.

**Out of scope:** whole-basket totals UI beyond a linear sum; cost quoting / checkout (not e-commerce); per-layer visualization (g-code not retained); adaptive layer height (gated).

#### Standalone stories — none for Init 20

(No standalone stories outside Epic E32 in Init 20 scope.)

## Initiative 21 — Admin-Managed Orca Process Profiles + User-Facing Selector Options

**Status:** 🚧 in-progress (started 2026-06-04). 33.1 + 33.2 **shipped** on `main`; **PROFILE-LIB-1 shipped/done** (ff-merged @`221bbe1`, full check-all 16/16 green, live `.190` G-SMOKE passed — 7 stored blocks all `usable`); **33.3 FROZEN/BLOCKED** pending profile-model correction (2026-06-06). **Next ready slice = PROFILE-OFFER-1** (`PrintProfileOffer`/`ProfileChain` minimal data-model + admin-CRUD + dry chain-validation; real resolver publication / live slicing gated to a later step; offer-composition UI gated on a UX checkpoint). Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` (status `approved-but-corrected` — operator go; approval scoped to planning-artifact appends, NOT code; implementation gated per SCP § 7) + the 2026-06-06 model-correction SCP. Predecessor: Init 20 (STL Slicer Estimates, Epic E32 — shipped); Init 21 builds on its resolver + the EST-TIERS-1 availability bridge and supersedes the EST-TIERS-1 hand-placement workaround. Single epic E33. Architecture: `architecture.md` § Initiative 21 (Decisions AK + AL = compiled-intent projection; AM = separate-block library; AN = offer/chain layer). Kanban: `t_ce1927cf`.

> ⚠️ **DOMAIN-MODEL CORRECTION (2026-06-06) — read before any further E33 work.** Source: `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md`. The fixed `printer_ref × material_class × quality_tier` slot grid + uploaded intent triple described throughout this Init 21 section is **NOT the canonical domain model** — it is a **transitional compiled-intent / resolver projection** (MVP compatibility surface for the existing resolver/worker, **kept, not deprecated**). The **canonical model is separate Orca-like building blocks** — `MachineProfile` (required for valid Orca slicing; a real current Orca machine, e.g. K1 Max / MicroSwiss HF; later carries machine-capability material restrictions), `ProcessProfile` (**the most important portal-facing block** — drives gram/material estimates, print strategy, and the member quality/process choice), `FilamentProfile` (needed by Orca; drives max volumetric speed, compatibility, time estimates; bridges to Spoolman material types) — plus product-facing `ProfileChain` (compiled intent for the existing resolver) and `PrintProfileOffer` (member/admin offer). Shipped 33.1/33.2 are **preserved, not reverted** (reclassified as the compiled-projection read/write). **Story 33.3 (grid lifecycle) is FROZEN/BLOCKED**; the next slice is re-pointed to a small **profile-library inventory CRUD** (add/import, list, get-curated-metadata, delete — **process profiles first**, machine/filament as supporting refs; **no raw Orca JSON viewer**) → then `PrintProfileOffer`/`ProfileChain`. No data migration is forced — the block/offer layer compiles into the same resolver intent path the grid already writes; `bundle_hash` / append-only stores / provenance snapshots are preserved. Material taxonomy stays the small generic bridge (PLA/PETG/PCTG/TPU, later ABS/ASA). Member spool-picker / request-flow UX is deferred. See that SCP § 3–§ 6.

> **Story breakdown is epic-level sketch.** Full acceptance criteria, task lists, pre-enumeration saves, test-target counts, and Codex routing are produced per story by `bmad-create-story` at dev-entry time. **No story spec files exist yet** — stories stay `backlog`. **UX-PROFILE-1 (`bmad-ux` / Sally) is a REQUIRED, OPEN work item** that designs the admin profile grid + the user-facing selector surface and **blocks finalizing the FE acceptance criteria** for Story 33.1 (grid) and the selector behavior; it must run before/with FE story authoring. Authoring these planning artifacts did NOT authorize dev-story execution / code implementation — that remains gated on an explicit operator go per SCP § 7.

### Overview

Init 21 gives the operator a first-class **admin panel to see, import, and manage Orca process/intent profiles** per `(printer_ref, material_class, quality_tier)` slot, and makes the **user-facing Files/STL selector expose only admin-approved + material-compatible options**. Today profiles are hand-placed on the `.190` portal-content volume under `SLICER_VENDORED_PROFILES_DIR` and per-tier availability is derived purely from disk presence (the EST-TIERS-1 bridge); only `standard.json` exists for the catalog printer/material, so Aesthetic/Strong resolve to `unsupported_material_class` and are disabled. This initiative replaces hand-placement + the disk-presence gate with an admin-managed, **compatibility-constrained** surface where **offerable = imported ∧ resolvable ∧ compatible** (TPU is specific enough to require dedicated, declared-compatible process profiles; a PLA/PETG-derived process slot must never be surfaced as TPU-valid even if it resolves). The user-facing `GET /api/estimates/quality-tiers` `{quality_tier, available, reason}` contract is preserved — only the *source of truth* behind "available" gains an admin-managed, compatibility-aware front end. Process/intent profiles only — NOT Spoolman inventory/cost (a separate SoT). The Init 20 `bundle_hash`, `source_system_tree_hash` provenance snapshot, and append-only stores are preserved invariants.

### Requirements Inventory

**FR ↔ Epic / Story matrix:**

| FR | Epic | Story | Notes |
|---|---|---|---|
| FR21-PROFILE-INVENTORY-1 | E33 | 33.1 | Admin-only read of the managed inventory (per-slot `{imported, resolvable, compatible, reason, portal_label, provenance}`) as a superset projection over the resolver. Anchors Decision AK. |
| FR21-COMPAT-1 | E33 | 33.1 (consume read-only) + 33.2 (enforce on import) | Material/filament-class ↔ process-profile compatibility map; neither surface offers an incompatible combination. Anchors Decision AK (OD-7). |
| FR21-PROFILE-IMPORT-1 | E33 | 33.2 | Validated import (structural `resolve()` ∧ compatibility) → in-place vendored-tree write + sidecar manifest + audit; incompatible-slot import rejected. Anchors Decision AL. |
| FR21-SELECTOR-1 | E33 | 33.1 (projection) + 33.2 (end-to-end) | User selector consumes admin-approved + compatibility-filtered availability; preserved `{quality_tier, available, reason}` DTO. |

**NFR ↔ Epic / Story matrix:**

| NFR | Epic | Story | Notes |
|---|---|---|---|
| NFR21-PROVENANCE-1 | E33 | 33.2 | Import preserves unrelated `bundle_hash`; in-place system-tree write yields a new `source_system_tree_hash` snapshot automatically. |
| NFR21-NO-422-1 | E33 | 33.1 + 33.2 | No member-reachable resolve 422 — offer only offerable slots. |
| NFR21-UX-1 | E33 | 33.1 (grid) + selector (UX-PROFILE-1) | UX-designed admin grid + selector (disabled-with-explanation vs hidden); `bmad-ux` before/with FE work. |
| NFR21-AUTH-1 | E33 | 33.1 + 33.2 | `/api/admin/*` profiles route admin-gated via `current_admin`, absent from `_PUBLIC_ROUTES`; Init 6 route-enforcement gate passes. |
| NFR21-OBS-1 | E33 | 33.2 | Import/manage writes via `record_event` (`slicer_profile.import`/`.delete`) + instrumented per the observability contract; no profile bodies logged in full. |
| NFR21-I18N-PARITY-1 | E33 | 33.1 (grid) + selector | `modules.admin.profiles.*` + compatibility-reason keys in BOTH en.json + pl.json. Material names untranslated. |
| NFR21-VISUAL-VERIFICATION-1 | E33 | 33.1 + selector | New baselines for offerable vs not-offerable-with-reason states × 4 projects; gated on UX-PROFILE-1. |
| NFR21-DETERMINISM-1 | E33 | All stories (pre-merge gate) | 3× consecutive identical pytest + vitest pass counts. |

### Epic List

| Epic | Name | Status | Stories |
|---|---|---|---|
| E33 | Admin-Managed Orca Process Profiles | 🚧 backlog | 33.1 + 33.2 + 33.3 (read-only first) |

#### Epic E33 — Admin-Managed Orca Process Profiles

**Goal:** ship the admin profile-management surface — a read-only managed-inventory admin grid first, then a validated import/publish write path, then optional lifecycle management — so the operator can see/import/manage Orca process profiles in-product and the user selector exposes only admin-approved + material-compatible options, retiring the EST-TIERS-1 hand-placement workaround. Backend (admin router) + frontend (admin tab + selector), plus a write-slice-only configs-side portal-content RW-mount coordination (NOT a 3d-portal commit). **Sequencing: read-first, write-second** (mirrors the proven Story 32.6 read-seam-first pattern): 33.1 (read-only, zero write/deploy risk) → 33.2 (write path, carries the novel risk) → 33.3 (optional). UX-PROFILE-1 designs the FE surfaces before/with 33.1's FE half + the selector. Each story carries NFR21-DETERMINISM-1; the FE work carries NFR21-UX-1 + NFR21-I18N-PARITY-1 + NFR21-VISUAL-VERIFICATION-1.

##### Story 33.1 — Read-only admin profile inventory + compatibility surfacing (PROFILE-ADMIN-1; FR21-PROFILE-INVENTORY-1, FR21-COMPAT-1 read-only, FR21-SELECTOR-1 projection, NFR21-NO-422-1, NFR21-AUTH-1, NFR21-UX-1, NFR21-I18N-PARITY-1, NFR21-VISUAL-VERIFICATION-1; Decision AK)

**Realizes:** FR21-PROFILE-INVENTORY-1 + FR21-COMPAT-1 (read-only consumption) + FR21-SELECTOR-1 (projection). Anchors Decision AK. **Recommended FIRST slice — safe, deploy-clean.**

**Sketch:** **Backend (additive, read-only):** `GET /api/admin/profiles?printer_ref=…` (admin-gated via `current_admin`, mounted under `/api/admin`, absent from `_PUBLIC_ROUTES`) returning per `(printer_ref, material_class, quality_tier)` slot `{imported, resolvable, compatible, reason, portal_label, provenance: {source_system_tree_hash, orca_version}}`. Reuses the EST-TIERS-1 `resolve_preset` resolvability logic + `VendoredProfileSource` provenance — **no new resolve logic**, an admin-facing superset projection — plus the OD-7 compatibility map to compute `compatible` + the structured `reason` when a slot is resolvable-but-incompatible. **Frontend:** new `"profiles"` tab in `AdminTabs.tsx` (extend `ActiveTab`) + `routes/admin/profiles.tsx`, gated on `isAdmin`, rendering the printer × material × tier grid with imported/resolvable/**compatibility** status + human-readable reason + provenance. Read-only list view; en+pl i18n parity. **FE surface is UX-designed (UX-PROFILE-1), not a raw status dump.**

**Depends on:** Init 20 resolver + EST-TIERS-1 availability seam (shipped). **UX dependency:** UX-PROFILE-1 before FE ACs are locked. **Coordinates with:** 33.2 (which authors/edits the map this story consumes read-only).

**Acceptance boundaries (sketched; finalized by bmad-create-story):**
- Non-admin → 403; route authenticated + absent from `_PUBLIC_ROUTES` (Init 6 route-enforcement gate passes).
- The inventory's `resolvable`/`reason` for every tier **agrees** with `GET /api/estimates/quality-tiers` for the same printer/material — shared parity test (one source of truth).
- Per slot, a clear **compatibility status + reason**: offerable (imported ∧ resolvable ∧ compatible) or not, and when not, *why* (not imported / not resolvable / incompatible for this material class). A resolvable-but-incompatible slot is shown **not offerable** with an explicit incompatibility reason — never "available."
- The inventory **never marks an incompatible `(material_class, quality_tier)` slot offerable**; a shared test asserts the projection feeding the user selector excludes incompatible slots (no TPU-incompatible process choice for TPU, nor vice-versa); selector parity asserted.
- Provenance fields project from the resolved bundle's snapshot; **no Orca-internal keys, no file paths, no g-code** leak into the DTO.
- **Read-only** — no write/upload/multipart surface, no on-disk write, no configs change, no slicer-worker module → SW-DEPLOY-1 overlay rebuild NOT triggered.

**Test targets (sketched):** pytest on 403-for-non-admin; the resolvability-parity assertion vs `quality-tiers`; the incompatible-slot-not-offerable + selector-projection-excludes-incompatible assertions; the no-internal-leak DTO fence. vitest on the grid states; Playwright baselines for offerable vs not-offerable-with-reason states (post UX-PROFILE-1).

**Out of scope:** import/upload, delete, re-slice, metadata mutation, printer registry, label editing, **authoring/editing the compatibility map** (consumed read-only here; authored in 33.2/33.3).

##### Story 33.2 — Validated import/publish write path (PROFILE-ADMIN-2; FR21-PROFILE-IMPORT-1, FR21-COMPAT-1 enforcement, FR21-SELECTOR-1 end-to-end, NFR21-PROVENANCE-1, NFR21-NO-422-1, NFR21-AUTH-1, NFR21-OBS-1; Decision AL) — carries the novel risk

**Realizes:** FR21-PROFILE-IMPORT-1 + FR21-COMPAT-1 (enforcement) + FR21-SELECTOR-1 (end-to-end). Anchors Decision AL.

**Sketch:** multipart import of an intent triple → validate via the existing `resolve()` (OD-3 structural resolvability) **AND** validate material/process compatibility (OD-7) → on success write the triple **in-place** into `SLICER_VENDORED_PROFILES_DIR/intents/...` (OD-2) → on-disk sidecar manifest (portal label, importer, timestamp, original filename, status, **per-slot compatibility status + reason**, OD-4) + admin audit (`slicer_profile.import` via `record_event`). Mirrors the `sot/admin_router.py` multipart + `_write_atomic` + audit shape (JSON payloads, far smaller than STL). This slice owns the **vendored-dir write-posture reversal** (read-only-at-runtime → admin write) and the **configs RW-volume coordination** (HC2, NOT a 3d-portal commit). Defer the optional re-slice trigger (OD-6) — gated on EST-PARSE-1.

**Depends on:** 33.1 (the inventory read + compatibility-map consumption it writes to).

**Acceptance boundaries (sketched):**
- **No incompatible publish:** an import targeting a slot whose profile is not compatible with the declared material/filament class (e.g. a non-TPU process profile into a TPU slot) is **rejected with a clear structured reason** and NOT published/exposed — structural resolvability alone does not make a slot offerable (resolvable ∧ compatible). Rejection reason surfaced in the admin panel.
- **Selector invariant end-to-end:** after a successful import the user selector offers the newly-published slot **only if** compatible; an incompatible or compatible-but-unpublished slot never becomes member-reachable (no member-reachable 422; no incompatible combination offered).
- The compatibility decision + reason for each imported slot persist to the sidecar manifest and are reflected by the 33.1 inventory read (single source of truth).
- **Provenance preserved (NFR21-PROVENANCE-1):** import does not perturb an unrelated bundle's `bundle_hash`; an in-place system-tree write yields a distinct `source_system_tree_hash` snapshot; append-only stores untouched.
- Import audit-logged (`slicer_profile.import`); route admin-gated + out of `_PUBLIC_ROUTES`.

**Test targets (sketched):** pytest on incompatible-slot rejection + not-exposed; successful-compatible import → resolves + inventory reflects it; unrelated-bundle hash byte-stability across import; system-tree-mutation → distinct snapshot hash; audit-event assertion; 403-for-non-admin.

**Out of scope:** re-slice/backfill on import (OD-6, gated on EST-PARSE-1); label rename / disable / delete (33.3); printer registry; real-Orca CLI slice-validation (optional follow-up); any Spoolman change.

##### Story 33.3 — Profile lifecycle management: rename label / disable / delete (PROFILE-ADMIN-3; ⛔ FROZEN/BLOCKED 2026-06-06; FR21-PROFILE-INVENTORY-1 manage extension, NFR21-AUTH-1, NFR21-OBS-1)

> ⛔ **FROZEN / BLOCKED (2026-06-06) — DO NOT author or start.** Story 33.3 manages the **fixed-grid slots as the management surface** — exactly the grid-as-canonical assumption corrected by `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md`. Continuing it would deepen the wrong model and create rework once the separate-block **profile-library inventory** (the re-pointed next slice) lands. Do not create a 33.3 spec until that correction is accepted and the next slice is sequenced. The next E33 slice is **PROFILE-LIB-1** (operator-facing profile-block inventory CRUD — process profiles first) → **PROFILE-OFFER-1** (`PrintProfileOffer`/`ProfileChain`), per the 2026-06-06 SCP § 6.

**Realizes:** profile lifecycle management once import exists. **Optional / lowest priority. Currently FROZEN — superseded by the re-pointed profile-library next slice (2026-06-06 correction).**

**Sketch:** admin actions over already-imported profiles — edit the portal label, disable (hide from the selector without deleting the file), delete (with audit). Each action updates the sidecar manifest + audit log (`slicer_profile.delete` etc.) and is reflected by the 33.1 inventory read. Admin-gated; no new resolve logic.

**Depends on:** 33.2 (import/manifest must exist). **UX dependency:** UX-PROFILE-1 (manage actions + rejection-reason surfacing).

**Test targets (sketched):** pytest on disable → slot no longer offerable in the selector projection but still listed in the admin inventory as disabled; delete → audited + removed from inventory; 403-for-non-admin.

**Out of scope:** printer registry; arbitrary free-text tier labels (OD-1 deferred); bulk operations; re-slice.

##### Story PROFILE-LIB-1 — Operator Orca profile-block inventory CRUD/import (process profiles first) (re-pointed next slice 2026-06-06; FR21-PROFILE-INVENTORY-1 block-model extension, NFR21-AUTH-1, NFR21-OBS-1, NFR21-I18N-PARITY-1, NFR21-VISUAL-VERIFICATION-1, NFR21-DETERMINISM-1; Decision AM)

> ✅ **SHIPPED / DONE (2026-06-06).** Per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 6, PROFILE-LIB-1 was the re-pointed next E33 slice after the profile-model correction (not Story 33.3, frozen). It is now **done** — ff-merged to `main` @`221bbe1` (backend `f7702ee` / FE `38a6a90` / visual `05f5004` / metadata fixes `24fb0a8`+`221bbe1`), full `check-all.sh` 16/16 green, and live `.190` **G-SMOKE passed** (7 stored blocks, all `validation_state=usable`). Spec: `_bmad-output/implementation-artifacts/profile-lib-1-operator-profile-block-inventory.md` (sprint-status row `profile-lib-1-operator-profile-block-inventory: done`). The formal independent external review (Gemini/Codex) was **not separately executed** — closeout was on the basis of full-gate green + repo-local self-review + merge + live smoke under operator direction (recorded transparently, not faked). **The next E33 ready slice is now PROFILE-OFFER-1** (see the Story PROFILE-OFFER-1 section below). PROFILE-LIB-1 delivered **inventory CRUD only** — it does not resolve/compile blocks into slicer input.

**Realizes:** the FIRST surface of the corrected canonical **separate-block** model — a small, **additive** operator-facing inventory of separate Orca profile **blocks** (`process` profiles first; `filament` + `machine` as supporting blocks), so the operator is not dependent on manual file placement. **Inventory CRUD only**, ahead of the `PrintProfileOffer`/`ProfileChain` offer layer (PROFILE-OFFER-1).

**Scope:** four admin-gated routes on the existing `slicer/admin_router.py` — `POST /api/admin/profiles/library` (import/upload a block), `GET /api/admin/profiles/library` (list), `GET /api/admin/profiles/library/{block_id}` (get one block's **curated metadata + validation state**), `DELETE /api/admin/profiles/library/{block_id}` (remove, audited). New `slicer/profile_library.py` engine: **classify** each block as machine/process/filament (or reject `unsupported`/`error`); **extract minimized curated metadata** only (`name`, `profile_type`, `inherit`(+resolved chain), `settings_id`, `material_type`/`compatible_printers` for filament, `source`/`is_system`); **derive** `usable` / `requires_attention` / `error`; **flag** the Fenrir governance rule (a user process block must inherit a *system* process profile — Orca silently drops invalid inheritance, the portal surfaces it). Blocks stored in an **additive** `<root>/library/<profile_type>/<block_id>{.json,.manifest.json}` subtree (server-derived path-safe `block_id`=uuid5(type:name), upsert on re-import), **disjoint** from the `system/`+`intents/` (grid) trees. FE: minimal admin inventory CRUD (upload, type-filtered list process-first, validation-state badge, curated detail — **NO raw Orca JSON**, delete-confirm). **Reuses 33.2 foundations** (atomic two-phase publish, `ezop:ezop 664` metadata preservation, filename sanitizer, audit, leak fence, containment assert).

**Depends on:** 33.1 + 33.2 (done) + the 2026-06-06 SCP (accepted baseline). **UX:** proceeds under the existing UX-PROFILE-1 direction (SCP § 8 — the heavy relationship/offer UI gate is for PROFILE-OFFER-1, not this light inventory).

**Coexistence (SCP § 4):** the 33.1/33.2 fixed `printer_ref × material_class × quality_tier` grid is the **transitional compiled-intent projection** — **kept, untouched**; PROFILE-LIB-1 adds the separate-block library **alongside** it with **no data migration** (the block/offer layer compiles into the same resolver intent path in a later slice; `bundle_hash`/append-only stores/provenance stay invariant).

**Out of scope (SCP § 6 deferred register):** `PrintProfileOffer`/`ProfileChain` offer-compile (PROFILE-OFFER-1); N×M relationship editor; raw Orca JSON viewer / raw field editor; member spool-picker / request-flow / catalog-selector change; machine-capability material-policy enforcement (record the seam only); any `resolver.py`/`compatibility.py`/grid/`bundle_hash`/append-only/`intents`-`system`-tree change; Alembic/DB; Spoolman read/write. **SW-DEPLOY-1 not triggered** (api-side engine; blocks are data on the shared volume). **Live `.190` smoke NOT authorized by this card** (future/operator runtime gate).

**Gates:** G-DEVGO (explicit operator dev-go — write-bearing E33 story, SCP-2026-06-04 § 7 pattern; code BLOCKED, spec authoring only); G-DATA (real Orca profile-BLOCK exports to pin the classifier explicit-`type` branch + the user-process governance fixture — orca-profiles repo not on host, synthetic substitution forbidden; heuristic-classify + storage + CRUD + tests against the existing bench fixtures proceed without it); G-SMOKE (live `.190` RW-mount/vendoring smoke — future/operator runtime gate, not run).

##### Story PROFILE-OFFER-1 — Minimal PrintProfileOffer / ProfileChain layer over the profile-block library (re-sequenced next slice 2026-06-06; FR21-PROFILE-INVENTORY-1 offer-model extension, NFR21-AUTH-1, NFR21-OBS-1, NFR21-I18N-PARITY-1, NFR21-VISUAL-VERIFICATION-1, NFR21-DETERMINISM-1; Decision AN)

> ▶ **NEXT READY SLICE (2026-06-06).** Per `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 6 ("THEN" step) + § 8, the next E33 slice after PROFILE-LIB-1 (done) is **PROFILE-OFFER-1** — the `PrintProfileOffer`/`ProfileChain` layer. Spec authored: `_bmad-output/implementation-artifacts/profile-offer-1-print-profile-offer-chain.md` (status `ready-for-dev`; sprint-status row `profile-offer-1-print-profile-offer-chain`). **Story 33.3 stays FROZEN — do NOT resurrect it.**

**Realizes:** the canonical **offer/chain** surface (SCP § 3.4–3.5) as a **minimal, additive** layer that **consumes** the PROFILE-LIB-1 block library. The admin composes a `PrintProfileOffer` by selecting **exactly one** machine + **one** process + **one** filament block (an embedded `ProfileChain` value object), plus a member/admin **label**, **visibility**, **default** flag, and **compatible material categories** (the small generic `{PLA,PETG,PCTG,TPU}` bridge). The backend **validates the chain dry** (all three blocks present, correctly typed, not `error`, filament↔machine compatible, material-category consistent) and derives `usable` / `requires_attention` / `invalid` — **reading curated manifests only, NO `resolve()`, NO raw Orca bodies, NO slicing.**

**Scope:** five admin-gated routes on the existing `slicer/admin_router.py` — `POST /api/admin/profiles/offers` (create), `GET /api/admin/profiles/offers` (list, read-time revalidated), `GET /api/admin/profiles/offers/{offer_id}` (get one), `PATCH .../{offer_id}` (edit label/visibility/default/categories — chain immutable), `DELETE .../{offer_id}` (remove, audited; library untouched). New `slicer/profile_offer.py` engine: the `ProfileChain` value object (three library `block_id` refs); the `PrintProfileOffer` **on-disk sidecar** `<root>/offers/<offer_id>.json` (server-minted path-safe `offer_id`=uuid4().hex — stable across mutable label edits, deliberately unlike `block_id`=uuid5(type:name)); the dry `validate_chain` engine; offer DTOs (`extra="forbid"`, `chain_blocks` echo reuses `ProfileLibraryBlock`, NO raw Orca body); audit `slicer_profile.offer_create/.offer_update/.offer_delete`. FE (**gated on G-UXGATE**): a minimal offer surface (three single-select slot pickers reading `useProfileLibrary` + label/visibility/default/category-multi, list + validation-state badge, curated detail — **NO raw Orca JSON**, edit, delete-confirm). **Reuses PROFILE-LIB-1/33.2 foundations** (`publish_pair` atomic write, `ezop:ezop 664` metadata preservation incl. the `221bbe1` fresh-dir fix, leak fence, containment assert, audit).

**Depends on:** PROFILE-LIB-1 (done) + 33.1 + 33.2 (done) + the 2026-06-06 SCP (accepted baseline). **UX:** the FE offer-composition UI is **gated on G-UXGATE** — a `bmad-ux` / Sally design checkpoint (extends UX-PROFILE-1) because offer composition **is** relationship UI (SCP § 8). The backend proceeds without it.

**Coexistence (SCP § 4):** the 33.1/33.2 fixed grid is the **transitional compiled-intent projection** that **still feeds the member selector + estimates** — **kept, untouched**; PROFILE-OFFER-1 adds the offer/chain layer **alongside** it with **no data migration** and **no resolver publication** in this slice.

**Out of scope (SCP § 6/§ 9 deferred register):** **real resolver publication / live slicing** (compile an offer's chain into the `intents/` path + slice/estimate over it — **G-PUBLISH**, a later slice); standalone `ProfileChain` registry / chain CRUD (chain is embedded); N×M relationship editor (single-select per slot); raw Orca JSON viewer / raw field editor; member-facing surface / selector change / spool-picker / request-flow; machine-capability material-policy enforcement (record the seam only); any `resolver.py`/`compatibility.py`/grid/`bundle_hash`/append-only/`intents`-`system`-tree/library-**write** change; Alembic/DB; Spoolman read/write. **SW-DEPLOY-1 not triggered** (offers are api-side curated data on the shared volume). **Live `.190` smoke NOT authorized by this card** (G-SMOKE — future/operator runtime gate).

**Gates:** G-DEVGO (explicit operator dev-go — write-bearing E33 story; code BLOCKED, spec authoring only); G-UXGATE (UX/admin design checkpoint REQUIRED before the FE composition UI — SCP § 8; backend proceeds without it; output `ux-profile-offer-1-*`); G-PUBLISH (real resolver publication / live slicing **explicitly deferred** — recorded so future agents do not fold it in; safe default: the member selector keeps consuming the grid projection until then); G-DATA (**satisfied** — validates over already-imported library blocks + committed fixtures); G-SMOKE (live `.190` RW-mount/vendoring smoke — future/operator runtime gate, not run).

#### Standalone stories — none for Init 21

(No standalone stories outside Epic E33 in Init 21 scope. UX-PROFILE-1 is a `bmad-ux` work item, tracked in sprint-status as `ux-profile-1-*`, not a dev story; the PROFILE-OFFER-1 offer-composition UX checkpoint is tracked as `ux-profile-offer-1-*`.)

## Initiative 22 — Admin Operational Observability (Worker/Job Console)

**Status:** 🚧 planning (started 2026-06-06). Source SCP: `sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md` (status `proposed` 2026-06-06 — approval scoped to planning-artifact appends, NOT code; implementation gated). Discovery + architecture/UX design: `_bmad-output/implementation-artifacts/spec-admin-jobs-console.md` (candidate id **ADMIN-JOBS-1**, commit `dcb9df8`). Predecessor: Init 21 (Admin-Managed Orca Process Profiles, Epic E33) — whose slice/recompute queues this console observes. Single epic **E34**. Architecture: `architecture.md` § Initiative 22 (Decisions AO + AP + AQ). **Sequenced BEFORE G-PUBLISH** (the Init 21 PROFILE-OFFER-1 real-resolver publication / live slicing step) so the operator can observe queue effects before publishing begins.

> **Story breakdown is epic-level sketch.** Full acceptance criteria, task lists, pre-enumeration saves, test-target counts, and Codex routing are produced per story by `bmad-create-story` at dev-entry time. **No story spec file exists yet — Story 34.1 stays `backlog`.** Authoring these planning artifacts did NOT authorize dev-story execution / code implementation — that remains gated on an explicit operator dev-go (G-DEVGO). sprint-status `development_status` rows are seeded by `bmad-sprint-planning` after this landing (not yet present).

### Overview

Init 22 gives the operator a **read-only, admin-only worker/job console** over the three live ARQ pools (API `arq:api`, Render `arq:queue`, Slicer `arq:slicer`), so that after changing STL/render inputs or profile offers they can see whether a worker woke and whether jobs are **queued / running / succeeded / failed**. Today there is no such surface — `GET /api/health` (`apps/api/app/main.py:200-202`) returns only `{status,version}` and never touches arq. The console adds a backend snapshot endpoint **`GET /api/admin/queues`** (new `apps/api/app/modules/queue/` package, OD-4) + a frontend **`/admin/queues`** admin tab, built strictly by reusing the lifespan-owned `app.state` arq/Redis, the arq read surface, and the existing business-keyed status keys as a job-context layer. **Read-only and admin-only**: no retry/kill/purge/pause/resume; MVP is a raw-arq live snapshot (exact `zcard` queued + bounded `SCAN` in-progress + bounded hard-capped `SCAN` recent results — never unbounded `KEYS`); the durable job-activity ledger is deferred (G-LEDGER). API-read-only + FE ⇒ **SW-DEPLOY-1 overlay-rebuild gate NOT tripped**.

### Requirements Inventory

**FR ↔ Epic / Story matrix:**

| FR | Epic | Story | Notes |
|---|---|---|---|
| FR22-QUEUE-SNAPSHOT-1 | E34 | 34.1 | `GET /api/admin/queues` read-only snapshot over `app.state` arq/Redis (zcard queued + bounded SCAN in-progress + bounded hard-capped SCAN recent, never KEYS; allowlisted fields). Anchors Decision AO. |
| FR22-LIVENESS-1 | E34 | 34.1 | Tri-state worker liveness from `<queue>:health-check` presence+age; raw counters + `interval_s` surfaced verbatim. Anchors Decision AP. |
| FR22-CONSOLE-UI-1 | E34 | 34.1 | `/admin/queues` admin tab — per-queue cards + running strip + recent ~1h list (retention label); fails-closed states; focus-gated polling. |

**NFR ↔ Epic / Story matrix:**

| NFR | Epic | Story | Notes |
|---|---|---|---|
| NFR22-LEAK-FENCE-1 | E34 | 34.1 | Field-allowlist DTO; never raw pickled `args`/`kwargs`/`result`; curated `error_class`/`context`; allowlist + negative path/secret tests. Anchors Decision AQ. |
| NFR22-AUTH-1 | E34 | 34.1 | `current_admin`-gated, absent from `_PUBLIC_ROUTES`; route-enforcement gate green with no allowlist edit; 403/401 tests. |
| NFR22-READONLY-1 | E34 | 34.1 | `GET` only; no enqueue/abort/purge/pause/resume; console cannot mutate queue state. |
| NFR22-REDIS-LOAD-1 | E34 | 34.1 | No unbounded `KEYS`; bounded `SCAN` + `zcard`; focus-gated polling; magic-constant discipline on interval + `recent[]` cap. |
| NFR22-RETENTION-HONESTY-1 | E34 | 34.1 | `recent[]` labelled "~last 1h, Redis-resident" so a vanished failure is not read as resolved. |
| NFR22-I18N-PARITY-1 | E34 | 34.1 | `modules.admin.queues.*` keys in BOTH en.json + pl.json; queue ids/function names untranslated. |
| NFR22-VISUAL-VERIFICATION-1 | E34 | 34.1 | Baselines for populated/empty/error × 4 projects; AdminTabs ripple from the new tab. |
| NFR22-DETERMINISM-1 | E34 | 34.1 | 3× consecutive identical pytest + vitest pass counts before merge. |

### Epic List

| Epic | Name | Status | Stories |
|---|---|---|---|
| E34 | Admin Worker/Job Queue Console | 🚧 backlog | 34.1 (single read-only MVP slice) |

#### Epic E34 — Admin Worker/Job Queue Console

**Goal:** ship the admin worker/job console — a single read-only MVP slice (backend snapshot endpoint + FE admin tab + tests + visual baselines) — so the operator can observe the three ARQ pools (queued/running/liveness/recent) in-product, answering UC1 ("did my change wake the backend?"), UC2 ("is something running ahead of mine?"), and UC3 ("what are these red jobs?"). Backend (new `queue` admin module) + frontend (admin tab + route). **Read-first / visibility-first** (mirrors the proven 33.1 read-only-deploy-clean slice): a raw-arq live snapshot now, with the durable ledger + operator-action controls as later epic stories. The story carries NFR22-DETERMINISM-1; the FE work carries NFR22-I18N-PARITY-1 + NFR22-VISUAL-VERIFICATION-1; the whole slice carries the NFR22-LEAK-FENCE-1 safety contract.

##### Story 34.1 — Read-only admin ARQ queue console (ADMIN-JOBS-1; FR22-QUEUE-SNAPSHOT-1, FR22-LIVENESS-1, FR22-CONSOLE-UI-1, NFR22-LEAK-FENCE-1, NFR22-AUTH-1, NFR22-READONLY-1, NFR22-REDIS-LOAD-1, NFR22-RETENTION-HONESTY-1, NFR22-I18N-PARITY-1, NFR22-VISUAL-VERIFICATION-1, NFR22-DETERMINISM-1; Decisions AO + AP + AQ)

**Realizes:** the entire Init 22 MVP — FR22-QUEUE-SNAPSHOT-1 + FR22-LIVENESS-1 + FR22-CONSOLE-UI-1. Anchors Decisions AO + AP + AQ. **Single read-only, deploy-clean slice.**

**Sketch:** **Backend (additive, read-only):** `GET /api/admin/queues` in a new `apps/api/app/modules/queue/admin_router.py` (mounted in `apps/api/app/router.py`; `current_admin` default-value dep; absent from `_PUBLIC_ROUTES`), computing the snapshot DTO entirely from `request.app.state.arq` / `.redis` — per-pool `queued` = `redis.zcard(queue_name)`; `worker` liveness + counters from the `<queue>:health-check` string; `running_jobs` from a bounded `SCAN MATCH arq:in-progress:*` (function name + curated context only); `recent` from a bounded, hard-capped `SCAN MATCH arq:result:*` (**never** `all_job_results()`'s unbounded `KEYS`), projected to allowlisted fields + grouped by `JobResult.queue_name`; `context` derived from the existing `render:status:{model_id}` / slicer `EstimateStatus` keys and/or the job id — never from raw `args`/`kwargs`/`result`; plus a `retention_note`. **Frontend:** new `"queues"` tab in `AdminTabs.tsx` + `routes/admin/queues.tsx`, gated on `isAdmin` (AuthGate discipline: defer to shell for anonymous; role-tier redirect only for authenticated-non-admin), rendering per-queue cards (queued/running headline + tri-state liveness chip with age + interval + raw counters, failed-count weighted) + a "running now" strip + a "recent (~last hour)" list with the retention caveat label; loading skeleton / empty ("no jobs queued") / error states that **fail closed/visible**; focus-gated polling (pause when the tab/document is hidden). en+pl i18n parity.

**Depends on:** the live arq pools + `app.state` arq/Redis (shipped). **No UX-design blocker** — the console mirrors the existing admin-tab pattern; no new UX work item is required for the MVP.

**Acceptance boundaries (sketched; finalized by bmad-create-story):**
- Non-admin → 403; anonymous → 401; route authenticated + absent from `_PUBLIC_ROUTES` (Init 6 route-enforcement gate passes with **no** allowlist edit).
- **Leak fence:** the serialized response matches the field allowlist and contains **no** `args`/`kwargs`/`result` keys; `error_class` is a curated category, `context.ref` an id/hash-prefix; a negative test asserts no path-like substrings (`/`, drive letters, `..`) and no secret-looking material.
- **Bounded-SCAN-not-KEYS:** no unbounded `KEYS` in the snapshot path; in-progress + recent use bounded `SCAN`, `recent[]` is hard-capped; depth via `zcard`.
- **Liveness tri-state:** `alive` / `idle-stale` / `unknown-down` derived from `<queue>:health-check` presence + age; `interval_s` reflects the worker's actual `health_check_interval` (not a hardcoded number); coarse ~1h granularity is shown honestly.
- **Retention honesty:** the recent panel is labelled "~last 1h, Redis-resident."
- **Fails-closed UX:** on a failed read the console renders an error panel + Retry, never a fabricated green/empty state.
- **Read-only:** `GET` only — no enqueue/abort/purge/pause/resume surface; a test asserts the queue module exposes only the read endpoint.
- **Deploy-clean:** API-read-only + FE; no worker image change → SW-DEPLOY-1 overlay rebuild NOT triggered.

**Test targets (sketched):** pytest (fakeredis) seeding `arq:*` keys (queued zsets, in-progress keys, result keys, health strings) → assert the snapshot DTO; 403-non-admin + 401-anonymous; route-enforcement gate green with no `_PUBLIC_ROUTES` edit; leak-fence allowlist + negative path/secret/args/kwargs/result assertions; bounded-SCAN-not-`KEYS` assertion; liveness tri-state mapping over varied health-key age/presence. vitest on the card/strip/list states + loading/empty/error (fails-closed) + focus-gated polling start/stop + i18n key parity (en/pl). Playwright baselines for populated (mixed liveness + a failed job) / empty / error across the 4 projects + AdminTabs ripple. Determinism: 3× consecutive identical pytest + vitest counts.

**Out of scope (deferred with named gates):** durable job-activity ledger (G-LEDGER); retry/kill/purge/pause/resume operator-action controls (G-ACTIONS); worker `health_check_interval` lowering for near-real-time liveness (G-LIVENESS); WebSocket/SSE push; multi-instance / historical charts / alerting; the member-facing print `/queue` module slot (unrelated v2 surface).

**Gates:** **G-DEVGO** (explicit operator dev-go — implementation BLOCKED, spec authoring only until `bmad-create-story` + dev-go); **G-PUBLISH-before** (ADMIN-JOBS-1 is sequenced BEFORE the Init 21 PROFILE-OFFER-1 real-resolver-publication / live-slicing step so the operator can observe slice/recompute/render queues before publishing effects); **G-LEDGER** (durable job-activity ledger — DB-backed append-only event model surviving past Redis TTL; worker instrumentation + Alembic — deferred named slice, closes UC3 long-term); **G-LIVENESS** (worker `health_check_interval` lowering for near-real-time liveness — worker-config + redeploy — deferred; running/queued stay exact without it); **G-ACTIONS** (destructive operator-action controls retry/kill/purge/pause/resume — deferred until visibility is proven).

#### Standalone stories — none for Init 22

(No standalone stories outside Epic E34 in Init 22 scope. No `bmad-ux` work item is required for the read-only MVP — the console mirrors the existing admin-tab pattern.)
