---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain (skipped — domain=general, complexity=low; no domain-specific concerns uncovered elsewhere)
  - step-06-innovation (skipped — innovation signal already covered in Executive Summary's What Makes This Special)
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
status: complete
releaseMode: phased
classification:
  projectType: web_app
  domain: general
  complexity: low
  projectContext: brownfield
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-glitchtip-distillate.md
  - _bmad-output/project-context.md
  - docs/operations.md
  - docs/plans/2026-04-30-glitchtip-integration-design.md
  - docs/plans/2026-04-30-glitchtip-integration-plan.md
  - "~/repos/configs/docs/glitchtip-agent-guide.md"
  - "~/repos/configs/docs/observability-logging-contract.md"
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 0
  projectDocs: 6
workflowType: 'prd'
projectMode: 'brownfield'
initiatives:
  - id: 0
    name: 'Product Foundation — Home 3D-Printing Catalog'
    status: 'shipped_retrospective'
    completed: '2026-04 (v1 cutover)'
    documented: '2026-05-15'
    sections: 'see "Initiative 0" H2 below'
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
    status: 'shipped'
    started: '2026-05-18'
    completed: '2026-05-20'
    sections: 'see "Initiative 5" H2 below'
  - id: 6
    name: 'Post-Cutover Default-Deny Auth Posture'
    status: 'shipped'
    started: '2026-05-20'
    completed: '2026-05-21'
    sections: 'see "Initiative 6" H2 below'
  - id: 7
    name: 'Account & Admin UX Polish'
    status: 'planning'
    started: '2026-05-21'
    sections: 'see "Initiative 7" H2 below'
  - id: 8
    name: 'Catalog Mobile & Image Performance'
    status: 'planning'
    started: '2026-05-21'
    sections: 'see "Initiative 8" H2 below'
  - id: 9
    name: 'Test Isolation Cleanup'
    status: 'planning'
    started: '2026-05-21'
    sections: 'see "Initiative 9" H2 below'
  - id: 10
    name: 'Operator Polish Batch'
    status: 'planning'
    started: '2026-05-22'
    sections: 'see "Initiative 10" H2 below'
  - id: 19
    name: 'Spoolman Read-Only Inventory (MVP-A)'
    status: 'planning'
    started: '2026-05-29'
    sections: 'see "Initiative 19" H2 below'
  - id: 21
    name: 'Admin-Managed Orca Process Profiles + User-Facing Selector Options'
    status: 'planning'
    started: '2026-06-04'
    sections: 'see "Initiative 21" H2 below'
---

# Product Requirements Document — 3d-portal

**Maintainer:** Ezop
**Created:** 2026-05-09 (Initiative 1)
**Last updated:** 2026-06-04 (Initiative 21 Admin-Managed Orca Process Profiles planning extension via sprint-change-proposal-2026-06-04-profile-admin.md, status `approved` 2026-06-04 — H2 append after Initiative 20)

This is the living project PRD for **3d-portal**. It grows over time, one **Initiative** at a time. Each initiative is a coherent scope (feature, refactor, observability delta, etc.) and gets its own H2 section below with full Executive Summary / Success Criteria / Functional Requirements / Non-Functional Requirements / etc. Use [`bmad-edit-prd`](../../_bmad/) to add or extend an initiative — do **not** fork the file (`prd-v2.md`, `prd-glitchtip.md`).

## Initiatives Index

| # | Name | Status | Shipped | Notes |
|---|---|---|---|---|
| 0 | Product Foundation — Home 3D-Printing Catalog | ✅ shipped (retro) | 2026-04 v1 | The actual portal product: catalog browse + 3D STL viewer + share-links + admin + audit log + async render pipeline + AI-agent-readable surface (`/agent-runbook`, `/openapi.json`, triage scripts). Documented retrospectively 2026-05-15 to fix the foundation that the original 2026-05-09 BMAD chain skipped. See section "Initiative 0" below. |
| 1 | Useful GlitchTip Delta | ✅ shipped | 2026-05-10 | Symbolication + filters + verify ritual + triage script. Brownfield delta layered on the 2026-04-30 Sentry/glitchtip-cli baseline. See section "Initiative 1" below. |
| 2 | Agent Runbook + Legacy SoT Triage | ✅ shipped | 2026-05-11 | Agent-executable runbook for URL → portal model creation, served by the portal itself (`/agent-runbook` endpoint) + OpenAPI for endpoint discovery. Includes legacy SoT folder triage decision. See section "Initiative 2" below. |
| 3 | UI Theme Compliance & Visual Regression Hardening | ✅ shipped | 2026-05-13 | Systemic light/dark theme defect remediation + visual-regression turned into a real quality gate (in-repo ESLint color-literal ban + Stylelint scoped per-file + axe `color-contrast` scan + git pre-commit hook for baseline acceptance + 2 new project-context.md rules). Epic 5 closed single-session autonomous 2026-05-13. See section "Initiative 3" below. |
| 5 | Public Registration & User Account Management | ✅ shipped | 2026-05-20 | Member role + invite-based registration + TOTP 2FA + admin panel + security audit hard-gate + atomic edge cutover. Five sequenced epics E6-E10. Closed at commit `7e5aea0` (cutover) + retro `2429157` (2026-05-20). See section "Initiative 5" below. |
| 6 | Post-Cutover Default-Deny Auth Posture | ✅ shipped | 2026-05-21 | Single epic E11 (7 stories 11.1-11.7) closing the Init 5 cutover drift: backend default-deny `/api/*` with `_PUBLIC_ROUTES` allowlist + route-enforcement pytest gate + share-scoped asset endpoint + shell-level AuthGate + audit re-run + cutover-smoke external probe + sibling allowlist rollback. NFR6-SEC-1 HARD GATE PASS (69/69 auth-boundary probe + 3/3 route enforcement). Closing commit `2641b6c`. See section "Initiative 6" below. |
| 7 | Account & Admin UX Polish | 🚧 planning | — | Single epic E12 (5 stories 12.1-12.5): admin invites unblock + i18n + layout fix, admin users inactive-filter, display name on registration + self-service edit, settings hub + 2FA discoverability + user-menu link, sessions UX (pagination/sort/UA-filter). Each story carries mandatory NFR7-UX-1 pre-CR agent-browser visual-verification gate. Source SCP: `sprint-change-proposal-2026-05-21.md`. See section "Initiative 7" below. |
| 8 | Catalog Mobile & Image Performance | 🚧 planning | — | Single epic E13 (2 stories 13.1-13.2): mobile carousel arrows visible at ≤sm breakpoint + thumbnail pipeline (Pillow on-upload, 800px longest side WebP @ q80, query-param variant endpoint, srcSet on catalog cards, backfill script). NFR8-PERF-1 ≤50 KB thumbnail payload budget. Source SCP: `sprint-change-proposal-2026-05-21.md`. See section "Initiative 8" below. |
| 9 | Test Isolation Cleanup | 🚧 planning | — | Single epic E14 (3 stories 14.1-14.3): vitest admin module finder fixes (18→0 failures), pytest hydrate DB-pollution close, visual-regression hook-context flake fix. Test-infrastructure only (NFR9-SCOPE-1 — no production-code touches). Promoted from TB-018 via operator scope-pull 2026-05-21. Scheduled FIRST in SCP execution chain — unblocks Init 7 admin test surfaces. Source SCP: `sprint-change-proposal-2026-05-21.md`. See section "Initiative 9" below. |
| 10 | Operator Polish Batch | 🚧 planning | — | 3 epics (E15 Test Health & Determinism — 3 stories; E16 Catalog Power-User Features — 6 stories; E17 Operator UX & Backlog Sweep — 4 stories). Mix of bugfix (pytest threading deadlock, stale visual baselines), regression (bulk STL download ZIP restore), new ficzers (ModelNote bilingual schema + auto-fill descriptions, anonymous share-link viewer, admin manual model-add + STL upload), UX polish (fluid full-width admin tables), TB-* sweep. Source SCP: `sprint-change-proposal-2026-05-22-init10.md`. See section "Initiative 10" below. |
| 19 | Spoolman Read-Only Inventory (MVP-A) | 🚧 planning | — | Single epic E31 (5 stories 31.1-31.5): backend httpx client + Redis 30s TTL + arq 60s poll job + SETNX leader-election + `/api/spools/*` routes with cost-data carry-through DTOs, frontend `/spools` route + landing low-stock card, i18n + ops doc + visual baselines. First portal initiative integrating an outbound non-observability service (Spoolman at `.190:7912`). Members + admin visible (NOT admin-only). Three architecture Decisions (AD cache topology, AE network transport, AF data carry-through). All stories `gpt-5.4-mini` Codex routing — no NFR-SECURITY adjacency. Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md`. See section "Initiative 19" below. |
| 20 | STL Slicer Estimates (Per-Part MVP) | 🚧 planning | — | Single epic E32 (6 stories 32.1-32.6): profile resolver (Orca system+user inheritance merge + normalize + validate + hash + provenance snapshot), containerized headless OrcaSlicer worker, g-code metadata parse + `(stl_hash, bundle_hash)` cache, hash-driven invalidation + cost-only arithmetic recompute, Spoolman-mapped custom filament overrides (esp. TPU volumetric speed), frontend `PrintIntentPreset` selector + estimate display + soft-fail states. Per-STL estimates only (time, filament mass/mm/cm³, informational cost); request totals are linear sums — NO whole-plate/basket slicing, NOT e-commerce. Spoolman stays inventory SoT; Fenrir is research/export bench only (no production dependency). Three architecture Decisions (AH resolver, AI slicer-worker container, AJ cache/invalidation). Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md`. Discovery: `brainstorming-session-2026-05-31-1926.md`. See section "Initiative 20" below. |
| 21 | Admin-Managed Orca Process Profiles + User-Facing Selector Options | 🚧 planning | — | Single epic E33 (3 stories 33.1-33.3, read-only first): admin panel to see/import/manage Orca **process/intent** profiles per `(printer_ref, material_class, quality_tier)` slot so the user-facing Files/STL selector exposes only **admin-approved + compatible** options. Builds on the Init 20 resolver + the EST-TIERS-1 availability bridge (which it supersedes: availability stops being derived purely from disk presence and becomes admin-managed). **OD-1 RESOLVED (operator 2026-06-04): fixed `{aesthetic,standard,strong} × {PLA,PETG,PCTG,TPU}` grid + an explicit material/filament-class ↔ process-profile compatibility map** — offerable = imported ∧ resolvable ∧ compatible (TPU only offers TPU-compatible process profiles). Read-only inventory ships first (zero write/deploy risk); validated import is the second slice (vendored-dir write posture + sidecar manifest, no DB). FR21-COMPAT-1 + NFR21-UX-1 (UX-PROFILE-1 — `bmad-ux` designs the admin grid + selector before/with FE work). Two architecture Decisions (AK admin inventory read + compatibility-map representation/enforcement, AL import write posture + sidecar metadata). Process/intent profiles only — NOT Spoolman inventory/cost. Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md`. Kanban: `t_ce1927cf`. See section "Initiative 21" below. |

## Initiative 0 — Product Foundation: Home 3D-Printing Catalog

**Status:** shipped retrospective (v1 cutover 2026-04; documented 2026-05-15). Author: Ezop. **Framing:** this initiative documents the actual portal product that was already shipped before any BMAD planning began. The original 2026-05-09 BMAD chain jumped to Initiative 1 (GlitchTip delta) without first writing a foundation initiative, leaving the PRD describing only deltas. This section fixes that.

### Document Map

This initiative is intentionally lighter on Functional Requirements detail than a forward-looking initiative because **the FRs already shipped — the source of truth is the running code, not this document**. The aim of this section is to make the foundation legible to downstream BMAD steps and AI agents, not to re-spec v1.

| Section | Purpose |
|---|---|
| Executive Summary | Why the portal exists and what it does |
| Project Classification | Type / domain / complexity / context for the foundation |
| Success Criteria | What "v1 succeeds" looked like, retroactively |
| Product Scope | What v1 shipped + what was deliberately excluded + future-proofing slots |
| User Journeys | The four core flows that v1 supports |
| Functional Requirements | Capability inventory grouped by module (admin, catalog, share, sot, runbook), not gated by AC tables — those live in the source-of-truth design spec `docs/design/2026-04-29-portal-design.md` |
| Non-Functional Requirements | Performance / Security / Reliability bounds that the foundation accepted as constraints |

### Executive Summary

3d-portal is a self-hosted web portal where Ezop's personal 3D-printing model collection lives, polished enough to be a daily-driver for the household and **structured enough to be operated by AI agents as a first-class user from the 2026-04-29 design onward**. It is reachable at `https://3d.ezop.ddns.net` via homelab DDNS, gated by edge nginx basic-auth for household members, and runs on a single Docker host (`.190`) with an nginx edge LXC (`.180`) in front.

The portal turns a folder tree on a Windows machine into a polished catalog with **household browse access**, **point-to-point share links for recipients outside the household** (sporadic but real use), **JWT-gated admin actions with audit trail**, an **async render pipeline** (4-view thumbnails via `trimesh` + `matplotlib`), and a **directly-operable HTTP surface for AI agents** (`/agent-runbook` Markdown + `/openapi.json` enriched with operation IDs + `glitchtip-triage.sh` BMAD bridge).

v1 was specified in `docs/design/2026-04-29-portal-design.md` and implemented per `docs/plans/2026-04-29-portal-v1-implementation.md` in 12 phases through April 2026. The cutover ran the legacy one-way Windows → server rsync into retirement and made the portal DB + content volume the authoritative source of truth.

This Initiative 0 retrospectively documents that foundation so future initiatives (1: GlitchTip delta — shipped; 2: agent runbook — in progress; 3: UI theme hardening — in progress; future: Moonraker, Spoolman, member-print-requests, print queue / OpenSearch / Postgres / HA — **all four slots confirmed real intent 2026-05-15**) layer on a documented base.

**Explicit maintainer's stance, captured during 2026-05-15 elicitation:** there is **no fixed v1 "done" target** for the portal as a whole. Each shipped capability surfaces the next one in the maintainer's head — *"co zrobimy jedną funkcjonalność, to zaraz mi przychodzi do głowy kolejna"*. The portal is a portfolio of evolving capabilities, not a product with a defined finish line. The Success Criteria below reflect that — they're driver-shaped, not metric-shaped.

#### What Makes This Special

Three things, validated against Ezop's voice 2026-05-15:

1. **The maintainer's identity, not the project description, drives the AI-first design.** Self-described: *"AI-loop operator + pasjonat druku 3D; solo-dev coraz mniej — w czasach agentów wolę delegować bardziej doświadczonym."* This is why AI agents are weighted equally with human users in the design from day one — they're the operator's primary co-workers, not a future integration target. The 2026-04-29 spec already had `/agent-runbook`, cookie-password agent role, and the BMAD triage bridge in scope.
2. **Server owns the SoT, not the Windows folder.** Reverse-sync direction matters — the portal DB + content volume are authoritative. The Windows tree is a bootstrap source, not a real-time mirror. This unblocks every metadata capability (tags, categories, prints log, audit log, external links) because they have a real home.
3. **Living-doc planning + no-finish-line stance, by explicit design.** Each new scope extends the same PRD / architecture / epics files as a new Initiative H2 — never forks. The portal isn't structured around "ship MVP → maintain"; it's structured around a continuous stream of bounded initiatives where each initiative has its own success criteria but the product as a whole doesn't.

**Core insight:** Initiative 0 here is **retrospective scaffolding** that legitimizes the living-doc structure. The FRs below are listed for navigability (so downstream BMAD steps and AI agents know what already exists), not as work items. New capability for v2+ goes through a fresh initiative.

### Project Classification

| Field | Value | Rationale |
|---|---|---|
| **Project type** | `web_app` (multi-part monorepo) | React 19 SPA + FastAPI backend + arq worker, served behind nginx edge. 4 parts: `apps/web/`, `apps/api/`, `workers/render/`, `infra/`. |
| **Domain** | `general` | Self-hosted homelab catalog. No HIPAA/PCI/GDPR-scale compliance. No vertical-specific constraints. Standard practices apply. |
| **Complexity** | `medium` | Full-stack v1: 4 parts, 5 backend modules (admin/auth/runbook/share/sot), 11 Alembic migrations, async render pipeline, 3 surfaces (household browse, public share, AI-agent API). Above the `low` complexity that subsequent initiatives have been. |
| **Project context** | `brownfield` (retrospective) | v1 already shipped per the 2026-04-29 implementation plan; this document codifies the shipped state, not new work. |

### Success Criteria

**Maintainer's explicit stance, captured verbatim 2026-05-15:**

> *"Generalnie to na zasadzie 'używam i jest mi z tym dobrze' — ale ja nie widzę takiego docelowego stanu. W sensie: co zrobimy jedną funkcjonalność, to zaraz mi przychodzi do głowy kolejna. Więc obawiam się, że nie będzie takich Success targetów. Byłbym/jestem ciężkim klientem biznesowym."*

This shapes the section below: **no fixed business metrics** (retention, NPS, DAU, error budget — none apply to a single-household homelab tool with no commercial proxy). The portal succeeds, retrospectively, when the maintainer keeps using it as his daily driver and each of the **three drivers behind v1 stays satisfied**. Subsequent initiatives carry their own bounded success criteria; product-level success is not measured beyond "still being used + still being extended".

#### Driver Success — the three pain points that triggered v1 (confirmed 2026-05-15)

1. **Metadata + remote browse works.** Tags / categories / prints log / external links live in `portal.db`, not folder names. Catalog is browseable from desktop or phone over DDNS — the legacy "RDP to look at folder" workflow is retired. **"Aha moment"** (verbatim from Ezop): opening `/catalog` on his phone outside the house, rotating an STL in the 3D viewer, finding a model he printed last year.
2. **Sharing + audit works.** Share-link generation is one-click; the link reaches a non-household recipient without auth gymnastics (sporadic but real use confirmed); every admin write produces an `AuditLog` row queryable from the admin UI.
3. **AI-agent ergonomics works.** A fresh Claude Code or Codex session reads `/agent-runbook` + `/openapi.json` and performs catalog ingestion end-to-end without external documentation. `glitchtip-triage.sh <issue_id>` produces a usable BMAD story stub from a production issue ID.

#### Technical health (observable, not target-shaped)

These are properties of v1 that are continuously verifiable, NOT thresholds being measured against:

- **All four parts deploy together.** `web` (nginx serving React `dist/`), `api` (uvicorn FastAPI), `worker` (arq), `redis` come up as one compose stack on `.190`.
- **Renders are async and self-healing.** arq job → worker produces 4 PNG views → written back as `ModelFile` rows. Job status TTL self-clears after 1h.
- **Auth is cookie + password + CSRF, no bearer-token regression.** 2026-05-10 correction is authoritative. Frontend `api()` helper attaches `X-Portal-Client: web` CSRF + `credentials: "include"`; raw `fetch` is forbidden.
- **Observability into homelab GlitchTip + OTel collector.** Structured JSON logs per `~/repos/configs/docs/observability-logging-contract.md`. OTel distro 0.50b0 instruments FastAPI / Redis / SQLAlchemy. Initiative 1 added debug-ID symbolication on top.
- **Postgres-ready data plane.** SQLModel + Alembic abstract the swap to a `DATABASE_URL` flip; 11 migrations are SQLite-compatible patterns.

#### What does NOT count as a success criterion (and why)

Explicit exclusions per Ezop's "no target state" stance:

- **"Adoption among household members"** — household members use it (confirmed regular use 2026-05-15); past that, more use isn't a metric, just a nice property.
- **"Number of share-links generated"** — share-link use is sporadic by design; lifecycle works whether invoked 0 or 50 times.
- **"Time-to-deploy / deploy frequency"** — every merge to `main` deploys; cadence is what work demands, not a target.
- **"Error budget / SLO"** — single-host, household-scale; no SLA, no error budget concept.
- **"GlitchTip event count / triage rate"** — those are Initiative 1's metrics, scoped to that initiative; not foundation-level.

#### Observable foundation health (continuously verifiable, not "done" targets)

| Property | Verification | Status (2026-05-15) |
|---|---|---|
| Production URL reachable | `curl -fsS https://3d.ezop.ddns.net/api/health` | Live |
| Catalog has models | `curl /api/sot/models?limit=1` returns ≥1 model | Live |
| Share link bypasses basic-auth | `curl https://3d.ezop.ddns.net/share/<test-token>` from outside LAN without auth | Live |
| 3D viewer renders STL | Manual: open `/catalog/<id>`, rotate STL | Live, theme-aware |
| Render pipeline produces 4 PNGs per model | `ls $portal-content/<model_uuid>/*.png \| wc -l` | 4 per model post-render |
| Audit log captures every admin write | `curl /api/admin/audit?limit=10` after admin action | Live |
| Single-command deploy | `bash infra/scripts/deploy.sh` runs to completion | Live |
| AI agent can read runbook | `curl https://3d.ezop.ddns.net/agent-runbook` returns markdown | Live (Initiative 2 ongoing for enrichment) |

### Product Scope

#### MVP — Foundation v1 (shipped)

- **Catalog module (web):** list + grid + search + filter, detail page with photos/renders/STL files, 3D STL viewer (three.js + react-three-fiber + drei, theme-aware materials via `--color-viewer-*` tokens), responsive layout (mobile screenshots).
- **Auth module (api):** JWT login via `/api/auth/login` (bcrypt), refresh tokens with rotation (migration `0009`), CSRF middleware requiring `X-Portal-Client: web` header.
- **Admin module (api + web):** CRUD over Model / ModelFile / Tag / Category / Print / ExternalLink. Audit log query endpoint. JWT-gated UI behind `<AuthGate>`.
- **Share module (api + web):** Generate share token with TTL (Redis-backed), list active tokens, revoke. Public `/share/<token>` route bypasses household basic-auth via nginx location rule.
- **Sot module (api):** Source-of-truth ingestion via cookie + password agent flow. `scripts/hydrate_local_tree.py` for reverse-sync `.190` → WSL.
- **Runbook module (api):** `/agent-runbook` endpoint serving Markdown for AI agents.
- **Render worker:** arq job consumer, `trimesh` + `matplotlib` 4-view rendering, output PNGs written back as `ModelFile` rows.
- **Infra:** Docker Compose stack on `.190` (web + api + worker + redis), nginx edge on `.180` (DDNS TLS, basic-auth, share-bypass location rules), SQLite nightly backup with 30-day retention, BuildKit secret mount pattern for production secrets.
- **Observability baseline:** GlitchTip wired for web + api + worker (Initiative 1 adds debug-ID symbolication on top), structured JSON logs, OTel distro 0.50b0.

#### Growth Features (Post-MVP, addressed by subsequent initiatives)

These are explicit pointers into the existing initiatives ledger — each is a sibling H2 in this PRD:

- **Initiative 1 — Useful GlitchTip Delta** (✅ shipped 2026-05-10) — symbolication + filters + verify ritual + triage bridge.
- **Initiative 2 — Agent Runbook + Legacy SoT Triage** (✅ shipped 2026-05-11) — `/agent-runbook` enrichment + OpenAPI enrichment + legacy folder triage.
- **Initiative 3 — UI Theme Compliance & Visual Regression Hardening** (✅ shipped 2026-05-13) — theme defect remediation + VR gate hardening.

#### Vision — real future intent (confirmed 2026-05-15)

**All four future-proofing slots are real intent, not speculative.** Ezop affirmed 2026-05-15 that each becomes its own Initiative when the external gate trips — they're not "maybe someday", they're sequenced pipeline items waiting for context. Slots already scaffolded in code:

- **Moonraker bridge** (`apps/web/src/modules/printer/` slot) — **real intent.** Gate: at least one Moonraker-driven printer running consistently in the homelab.
- **Spoolman bridge** (`apps/web/src/modules/spools/` slot) — **real intent.** Gate: Spoolman already deployed in the homelab compose stack (or scheduled).
- **Member-print-requests** (`apps/web/src/modules/requests/` slot + `User.role=member`) — **real intent.** Gate: per-user auth model decided (OIDC via existing homelab Authentik vs. native portal accounts).
- **Print queue / OpenSearch full-text / Postgres migration / HA** — **real intent for the technical-flip group.** Each gate is its own threshold: queue UX demand, SQLite text-search bottleneck, SQLite storage/concurrency ceiling, acceptable-downtime budget change.

Additional surfaces not in the slot list but mentioned in earlier scoping (lower confidence):

- **Mobile photo upload** (admin endpoint exists; upload volume + reverse-rsync flow pending). Demand-pull rather than affirmed.
- **OIDC / SSO** (auth isolated in `app.core.auth/`; plug-in point exists). Likely arrives as part of member-print-requests rather than as a standalone initiative.

#### Hard exclusions — confirmed forever (2026-05-15)

- **Multi-tenant.** Single household, single SoT, single admin. The one architectural choice that will NEVER be revisited. There will never be "Ezop's catalog vs. someone else's catalog" inside this product.

#### Not in current plans, but not ruled out forever (Ezop did NOT affirmatively exclude these 2026-05-15)

The earlier autonomous draft framed these as "deliberate exclusions forever"; Ezop's elicitation softens them. They're not on any roadmap today, but the door isn't closed:

- **Public marketplace surface.** Share links are point-to-point today; whether the portal ever grows a discovery surface is undecided.
- **Print farm (multi-printer fleet management).** The future `printer/` slot is sized for a single Moonraker-driven printer; multi-printer fleet isn't in plans but isn't ruled out.
- **Mobile-native app (React Native / Capacitor).** Responsive web is enough today; a native app isn't in the roadmap but isn't ruled out.

### User Journeys

The foundation supports four user journeys end-to-end. These are intentionally short — each one's full UX detail lives in the v1 design spec.

#### J0.1 — Michał (admin) curates a new model

1. Adds the STL file + photos to a local folder under Windows/Nextcloud (legacy bootstrap path) OR uploads directly via admin UI (post-SoT-cutover path).
2. Opens `/login`, authenticates via cookie + password JWT login.
3. Reaches `/catalog/$id` for the new model, fills in name + description + tags + categories + external links (MakerWorld, Printables).
4. Triggers a render via the admin "Render" button → arq enqueues a job → worker produces 4 PNG views → catalog grid thumbnail appears within ~30s for a typical small model.
5. Audit log captures every metadata write.

**Authoritative source:** `docs/design/2026-04-29-portal-design.md` + `apps/api/app/modules/admin/router.py`.

#### J0.2 — Household member browses the catalog

1. Opens `https://3d.ezop.ddns.net` from any device on the LAN or via DDNS from outside.
2. Edge nginx basic-auth prompts for household credentials (htpasswd-backed).
3. After auth, lands on `/catalog`, sees full collection with thumbnails.
4. No admin actions visible (no JWT, no `current_admin` dependency satisfied → admin endpoints return 401 if probed).
5. Can rotate STL in 3D viewer, see photos, see prints log, follow external links.

**Authoritative source:** `apps/web/src/modules/catalog/` + `infra/nginx-180/3d-portal.conf`.

#### J0.3 — Friend outside the household receives a share link

1. Michał generates a share token from admin UI (or via `POST /api/admin/share` directly).
2. Token URL `https://3d.ezop.ddns.net/share/<token>` lands in a chat / email.
3. Recipient clicks the URL — edge nginx has `location /share/` and `location /api/share/` blocks that explicitly bypass basic-auth.
4. Recipient sees a read-only single-model view (STL, photos, renders).
5. Token TTL expires per Redis TTL; admin can revoke at any time via `DELETE /api/admin/share/{token}`.

**Authoritative source:** `apps/api/app/modules/share/{router,admin_router}.py` + `infra/nginx-180/3d-portal.conf` share-bypass location blocks.

#### J0.4 — AI agent operates the catalog

1. Fresh Claude Code / Codex session lands on the project, reads `_bmad-output/project-context.md` (136 implementation rules).
2. Needs to operate the catalog → opens `/agent-runbook` (Markdown served by FastAPI).
3. Runbook describes the URL → catalog model creation flow, references `/openapi.json` for full endpoint spec.
4. Agent authenticates via cookie + password flow per `bootstrap_agent.py`, performs catalog operations through the documented API.
5. If a production error appears in GlitchTip: agent runs `infra/scripts/glitchtip-triage.sh <issue_id>` → gets a markdown story stub → feeds it into `bmad-quick-dev` or `bmad-create-story`.

**Authoritative source:** `apps/api/app/modules/runbook/router.py` + `infra/scripts/glitchtip-triage.sh` + `_bmad-output/project-context.md`.

### Functional Requirements (capability inventory, not work items)

These document what the foundation provides. They are not gated by acceptance criteria tables — the source of truth is the running code + `docs/design/2026-04-29-portal-design.md`. Numbered for downstream traceability only.

#### Catalog (apps/web/src/modules/catalog/ + apps/api/app/modules/sot/)

- **FR0-CAT-1.** List view + grid view of models, with thumbnails (rendered server-side by the worker).
- **FR0-CAT-2.** Free-text search across model name, tags, categories.
- **FR0-CAT-3.** Filter by tags. Filter by categories.
- **FR0-CAT-4.** Detail page per model: photos gallery, renders gallery, STL files list with select-for-render toggles, prints log, external links.
- **FR0-CAT-5.** 3D STL viewer using three.js + react-three-fiber, materials/edges/grid driven by `--color-viewer-*` theme tokens.
- **FR0-CAT-6.** Responsive layout — desktop + mobile breakpoints, light + dark theme.

#### Admin (apps/api/app/modules/admin/ + apps/web/src/routes/catalog/$id/)

- **FR0-ADM-1.** Edit model metadata: name, description, tags, categories.
- **FR0-ADM-2.** Manage model files: upload STL/photo/3mf, delete, mark `selected_for_render`, reorder via `position` field (migration `0006`).
- **FR0-ADM-3.** Add prints to prints log: date, filament, notes, photos.
- **FR0-ADM-4.** Manage external links: URL (indexed for de-duplication via migration `0011`), label, source.
- **FR0-ADM-5.** Audit log query: every admin write produces an `AuditLog` row (user_uuid + timestamp + action + entity ref) per migration `0005`.
- **FR0-ADM-6.** All admin endpoints require `current_admin` dependency (JWT + role=admin).

#### Share (apps/api/app/modules/share/)

- **FR0-SHARE-1.** Generate share token for one model, with TTL (Redis-backed native TTL).
- **FR0-SHARE-2.** Public `/share/<token>` route + `/api/share/<token>` API bypass household basic-auth via nginx location rules.
- **FR0-SHARE-3.** Admin can list active tokens and revoke individually via `DELETE /api/admin/share/{token}`.

#### Auth + CSRF (apps/api/app/modules/auth/ + apps/api/app/core/csrf.py)

- **FR0-AUTH-1.** JWT login via `POST /api/auth/login` with bcrypt password verify.
- **FR0-AUTH-2.** Refresh tokens with rotation (migration `0009_refresh_tokens`).
- **FR0-AUTH-3.** CSRF middleware requires `X-Portal-Client: web` header on browser writes; frontend `api()` helper attaches automatically.
- **FR0-AUTH-4.** `User.role` enum: `admin` (wired), `member` (placeholder v2), `agent` (wired for sot ingestion via cookie + password flow).

#### Source-of-truth (apps/api/app/modules/sot/)

- **FR0-SOT-1.** Public read endpoints: list models, get model, list tags, list categories.
- **FR0-SOT-2.** Agent write endpoints (admin role): create model, update metadata, upload file. Auth = cookie + password (NOT bearer token).
- **FR0-SOT-3.** Reverse-sync support via `scripts/hydrate_local_tree.py` for `.190` → WSL bootstrap.

#### Agent runbook (apps/api/app/modules/runbook/)

- **FR0-RUN-1.** `GET /agent-runbook` returns Markdown describing the URL → catalog model creation flow.
- **FR0-RUN-2.** Runbook content lives in repo under `docs/agents-add-model-runbook.md`; served verbatim by the route.
- **FR0-RUN-3.** Initiative 2 enriches `/openapi.json` with operation IDs for agent consumption.

#### Render pipeline (workers/render/ + admin trigger)

- **FR0-RND-1.** `POST /api/admin/models/{model_uuid}/render` enqueues an arq job; optional body `selected_stl_file_ids: []` pins which STLs participate.
- **FR0-RND-2.** Worker opens STL with `trimesh`, renders 4 isometric views via `matplotlib`, writes PNGs back as `ModelFile` rows.
- **FR0-RND-3.** Job status TTL: 1 hour; stuck "running" self-clears.
- **FR0-RND-4.** Bulk-enqueue via `bash infra/scripts/render-all.sh "<bearer-jwt>"` for fresh content-volume deploys.

### Non-Functional Requirements (foundation bounds)

#### Performance

- **NFR0-PERF-1.** Catalog list page (50 models, thumbnails resolved) renders in ≤2s on mid-range desktop + ≤4s on mid-range mobile over LAN.
- **NFR0-PERF-2.** STL viewer initial render ≤3s for typical home-print model (≤50MB STL).
- **NFR0-PERF-3.** Render worker produces 4-view PNG set in ≤30s for typical home-print model (≤50MB STL).

#### Security

- **NFR0-SEC-1.** Admin endpoints require JWT + role=admin. Agent endpoints (sot writes) require cookie + password authenticated session, not bearer token.
- **NFR0-SEC-2.** CSRF middleware enforces `X-Portal-Client: web` header on browser writes.
- **NFR0-SEC-3.** `SENTRY_AUTH_TOKEN` (and all production secrets) mounted as BuildKit secrets, never as `ARG` (would persist in `docker history`).
- **NFR0-SEC-4.** Share-link URLs are opaque tokens (Redis-keyed); no enumerable IDs.
- **NFR0-SEC-5.** Household basic-auth on edge nginx is the only public-facing auth gate; `/share/*` and `/api/share/*` are the only explicit bypass paths.

#### Reliability

- **NFR0-REL-1.** SQLite nightly backup with 30-day retention at `/mnt/raid/3d-portal-state/backups/`.
- **NFR0-REL-2.** Compose stack restart preserves data (volumes + state).
- **NFR0-REL-3.** Worker job failure does NOT poison the queue — failed jobs surface in structured logs and are retried per arq default policy.
- **NFR0-REL-4.** Auth-token refresh via `POST /api/auth/refresh` is silent — frontend `api()` retries `401 access_expired` once before surfacing the error.

#### Integration

- **NFR0-INT-1.** Frontend → backend over HTTP through `api()` helper exclusively (CSRF + credentials + silent refresh).
- **NFR0-INT-2.** Backend → worker through Redis arq broker exclusively (no direct HTTP).
- **NFR0-INT-3.** Worker depends on `portal-api` editable for shared SQLModel entities (no schema duplication).
- **NFR0-INT-4.** Backend → GlitchTip via Sentry SDK + REST (Initiative 1 added debug-ID symbolication on top).
- **NFR0-INT-5.** Backend → homelab OTel collector via OTLP-HTTP (`opentelemetry-instrumentation-*` 0.50b0 pinned).

#### Observability

- **NFR0-OBS-1.** Structured JSON logs per `~/repos/configs/docs/observability-logging-contract.md` from api + worker. Loggers namespaced `app.<module>.<area>`.
- **NFR0-OBS-2.** Frontend + backend + worker errors flow to homelab GlitchTip (shared DSN, `setTag('service', ...)` distinguishes).
- **NFR0-OBS-3.** OpenTelemetry traces span FastAPI + Redis + SQLAlchemy automatically (no manual span code in handlers).

#### Maintenance

- **NFR0-MAINT-1.** Every successful merge to `main` triggers `infra/scripts/deploy.sh` (doc-only commits skipped). [[feedback_auto_deploy_dev]].
- **NFR0-MAINT-2.** Plans / internal docs stay local — `_bmad-output/` and `docs/plans/` are gitignored. [[feedback_local_only_docs]].
- **NFR0-MAINT-3.** All committed file content in English. Polish stays conversational only.
- **NFR0-MAINT-4.** Visual regression baseline (`npm run test:visual` from `apps/web/`) is mandatory for any UI change. Baselines committed to repo.

## Initiative 1 — Useful GlitchTip Delta

**Status:** shipped 2026-05-10. Author: Ezop. Brownfield delta layered on the 2026-04-30 Sentry/glitchtip-cli baseline (Phases 0-5 of `docs/plans/2026-04-30-glitchtip-integration-plan.md`).

### Document Map

For readers landing cold (especially AI agents in downstream BMAD steps):

| Section | Purpose |
|---|---|
| Executive Summary + What Makes This Special | The pitch and the differentiator (BMAD-input loop framing) |
| Project Classification | Type / domain / complexity / context — single-row context for downstream steps |
| Success Criteria | User / Business / Technical / Measurable Outcomes |
| Product Scope | MVP / Growth / Vision feature inventory |
| User Journeys | 4 narrative journeys (J1–J4) + capability-to-MVP mapping table |
| Web App Specific Requirements | Frozen-baseline table + observability delta surfaces (build / SDK / CLI) |
| Project Scoping & Phased Development | MVP strategy + resource list + risk-mitigation table |
| Functional Requirements | 30 FRs across 7 capability areas — binding capability contract |
| Non-Functional Requirements | 17 NFRs across Performance / Security / Reliability / Integration |

### Executive Summary

3d-portal already ships errors to GlitchTip from web, api, and worker (baseline shipped 2026-04-30 via `docs/plans/2026-04-30-glitchtip-integration-plan.md`). The plumbing works, but the loop does not: production frontend stack frames arrive minified (`app-DhGq2.js:13`), the issue list is unfiltered noise from extensions and `ResizeObserver` loops, and there is no post-deploy ritual that proves symbolication is alive. The result is the predictable failure mode of homelab observability — installed, never opened — while the underlying infrastructure (Postgres, RAM, container lifecycle) burns regardless.

This PRD specifies the delta that converts GlitchTip from event store to **structured input for the BMAD planning pipeline and AI-agent debugging loop**. Production errors must land in `bmad-quick-dev` / `bmad-create-story` as ready-to-implement bug stubs without anyone remembering to open a UI. To deliver that:

- Replace `glitchtip-cli` upload (currently in `infra/scripts/upload-sourcemaps.sh`) with `@sentry/vite-plugin` 5.2.x integrated into the `vite build` step inside the docker image. Single-source release expression (`apps/web/src/release.ts` exporting `RELEASE`) makes drift a TypeScript error. CLI script stays in repo as documented manual recovery against GlitchTip backend issue #299.
- Tighten `apps/web/src/instrument.ts` with empirically-derived `denyUrls` / `ignoreErrors` / `beforeSend` filters (ruleset derived from a 30-day sample of real noise on the homelab GlitchTip instance, NOT anticipated noise) and add useful tags aligned with the homelab observability contract (`service.version`, `host.name`, `git.commit`, `route.pathname`, `model.id`, `auth.is_authenticated`).
- Add `infra/scripts/verify-symbolication.sh` (smoke + tripwire + failed-verify GlitchTip event) and `infra/scripts/glitchtip-triage.sh <issue_id>` (issue → BMAD story stub). `deploy.sh` calls verify as non-fatal warning + checks `infra/.last-verify` timestamp so the manual ritual cannot silently decay.

Backend and worker SDK polish are explicitly out of scope, gated on the frontend round demonstrating measurable triage value (≥3 production issues opened from a GlitchTip event referencing `<issue_id>` within 30 days post-rollout). Alerting (push notifications) and CI auto-verify are similarly out of scope, deferred to follow-up briefs.

#### What Makes This Special

Three things together set this PRD apart from a generic "wire up better source maps" effort:

1. **GlitchTip is structured input for the BMAD planning loop, not an end destination.** The success metric is not "events arrive" or "stack is symbolicated" — it is "≥3 bug fixes shipped through the `glitchtip-triage.sh` → `bmad-quick-dev` chain in 30 days post-rollout". Tag richness, agent-readable triage, and the triage script exist to feed planning, not to populate dashboards.
2. **AI agents are roughly half the user base** and the design optimizes accordingly. REST/curl/jq over UI clickability; CLI scripts over dashboards; pull-only over push notifications. The `glitchtip-agent-guide.md` REST recipes are the primary debugging interface, not a fallback.
3. **"Replacement keeps predecessor as documented manual recovery for one release cycle"** is promoted from this brief's local pragmatism (CLI fallback against issue #299) into a repeatable repo-wide principle. Every future replacement in 3d-portal inherits this discipline.

**Core insight:** "Useful" means load-bearing for the planning + execution loop. Solo dev + AI agents poll on cadence and pull on suspicion — push notifications would be noise. Skipping alerting in v1 is the design, not deferred scope.

### Project Classification

| Field | Value | Rationale |
|---|---|---|
| **Project type** | `web_app` | Host project = React 19 + Vite 6 SPA served by nginx. PRD modifies build pipeline, SDK init, and operational scripts of an existing web_app. |
| **Domain** | `general` | Self-hosted homelab catalog. No HIPAA/PCI/GDPR-scale compliance, no vertical-specific constraints. Standard practices apply. |
| **Complexity** | `low` | ~2–3 person-days of work touching 5–7 files in one module plus 2 new operational scripts. Stable stack, no novel technology. Phase 0 dry-run gate mitigates the only material risk (GlitchTip backend issue #299). |
| **Project context** | `brownfield` | Sentry SDK + glitchtip-cli pipeline already shipped (Phases 0–5 of `docs/plans/2026-04-30-glitchtip-integration-plan.md`, 2026-04-30). This PRD describes the delta layered on top, not a new system. |

### Success Criteria

#### User Success

The user surface is two-shaped: AI agents pulling via REST as the primary debugging persona, Michał as escalation/secondary.

- **AI agent triage takes one chain, not three.** `glitchtip-triage.sh <issue_id>` returns a markdown story stub directly paste-ready into `bmad-quick-dev` or `bmad-create-story`. No second tool, no UI, no manual cross-referencing. Acceptance: the stub contains top frame `(filename:line)`, fingerprint, route context, release SHA, last 5 events, and at least one suggested file to edit.
- **"Aha moment" lands within 30 seconds of a deploy.** Operator runs `bash infra/scripts/deploy.sh`, follow-up `verify-symbolication.sh` fires a smoke event tagged `smoke.run_id=<uuid>`, polls GlitchTip REST, returns success with the resolved frame at `apps/web/src/<...>.tsx:<line>`. Total wall time including poll budget ≤30s.
- **Triaging a real production error from the GlitchTip issue list to a BMAD story stub takes one command.** No UI clicking, no copy-paste-and-clean. Pull-only ergonomics is the design, not a degraded mode.

#### Business Success

Reframed for a single-tenant homelab: "business success" = operational discipline metrics, since revenue / user growth / market share do not apply.

- **Triage value gate** (decides whether the backend follow-up brief proceeds): ≥3 production issues opened from a GlitchTip event (via `glitchtip-triage.sh` or human-noticed UI lookup) within 30 days post-rollout. Below 3 → backend brief paused; the loop is not yet load-bearing.
- **Sunk-infra reclaim.** GlitchTip already runs on `.190` consuming Postgres, RAM, and a container slot whether used or not. Success means operational cost is amortized against actual debugging value, not a passive bullet on the architecture diagram.
- **Recovery-path discipline holds.** "Every replacement keeps its predecessor as documented manual recovery for one release cycle" applies cleanly: `infra/scripts/upload-sourcemaps.sh` stays in repo with header comment; invoked manually, it works without modification.

#### Technical Success

- **Real symbolication.** Any uncaught frontend exception in production produces a GlitchTip event whose top stack frame resolves to `apps/web/src/<...>.tsx:<line>` with line numbers matching the TS source. Confirmed by `verify-symbolication.sh` after every deploy until CI takes over.
- **One source of release truth.** Build-time and runtime `release` import the `RELEASE` constant from `apps/web/src/release.ts`. Drift = TypeScript compile error, not runtime mystery. Build log shows the upload step exiting non-zero on auth-token failure (no warn-and-continue).
- **Quiet by default.** First 25 issues sorted by `lastSeen desc`, measured 7 days post-rollout, contain zero matches against the deny list. Filter ruleset is derived from a 30-day sample of real noise on the homelab GlitchTip — empirical, not anticipated.
- **No source map leakage to production bundle.** `vite build` outputs `.map` files for upload but `filesToDeleteAfterUpload` removes them from `dist/` before docker image extraction. Verified by `docker history` showing no `.map` in nginx serve layer; verified by `curl` on prod assets returning 404 for `.map` URLs.
- **No `SENTRY_AUTH_TOKEN` in image layers.** Token mounted as BuildKit secret; `docker history apps_web:<tag>` shows no leak in environment, build args, or RUN-cached layers.
- **Determinism preserved.** `deploy.sh`'s "extract dist from image" rule still holds. Bundle hashes identical regardless of which dev box runs the build — build runs INSIDE the image, not on the host.

#### Measurable Outcomes

| Outcome | Measurement | Target |
|---|---|---|
| Smoke event resolves to source line | `verify-symbolication.sh` exit code 0 + top frame matches `^apps/web/src/.+\.tsx?$` | Every deploy until CI auto-verify lands |
| Issue list noise on first 25 | `curl /api/0/projects/homelab/3d-portal/issues/?limit=25&sort=lastSeen` post-7-day-rollout | Zero matches against deny list |
| Triage value gate (backend brief trigger) | Count of GlitchTip issue IDs referenced in BMAD story commits over 30 days | ≥3 |
| Build-step upload failure handling | `vite build` exit code on simulated 401 from GlitchTip upload | Non-zero (hard fail) |
| Source map exposure | `curl https://3d.ezop.ddns.net/assets/*.js.map` | 404 for all map files |
| Auth token image-layer leak | `docker history apps_web:0.1.0 \| grep -i sentry` | No matches |
| Manual-ritual decay | Time gap between latest `infra/.last-verify` timestamp and latest deploy | ≤1 deploy cycle (warning if exceeded) |

### Product Scope

#### MVP — Minimum Viable Product

The full scope of this PRD IS the MVP. Carving smaller dilutes the "useful GlitchTip" thesis below load-bearing.

- **Phase 0 pre-flight gate.** One-shot `vite build` against homelab GlitchTip with `@sentry/vite-plugin` 5.2.x; verify issue #299 does not fire. Abort or proceed.
- **Discovery.** Sample 30-day issues from homelab GlitchTip; derive `denyUrls` / `ignoreErrors` empirically.
- **Plugin migration.** `@sentry/vite-plugin` 5.2.x in `apps/web/vite.config.ts`; `apps/web/src/release.ts` single-source `RELEASE`; Dockerfile BuildKit secret for auth token; `SENTRY_ORG=homelab` / `SENTRY_PROJECT=3d-portal` / `SENTRY_URL=http://192.168.2.190:8800` as build args.
- **SDK polish.** `apps/web/src/instrument.ts` with empirical filter ruleset + structured tags aligned with `observability-logging-contract.md` (`service.version`, `host.name`, `git.commit`, `route.pathname`, `model.id`, `auth.is_authenticated`).
- **Operational scripts.** `infra/scripts/verify-symbolication.sh` and `infra/scripts/glitchtip-triage.sh <issue_id>`.
- **`deploy.sh` integration.** Calls verify as non-fatal warning post-deploy; warns at next invocation if `infra/.last-verify` timestamp older than previous deploy.
- **`upload-sourcemaps.sh` decoupling.** Header comment marking as manual-recovery path; removed from `deploy.sh` wiring; runnable on demand.
- **Documentation.** `docs/operations.md` rewrites the symbolication section; `_bmad-output/project-context.md` adds three execution-discipline rules.

#### Growth Features (Post-MVP)

Each its own future brief; gates explicit so the path is not vibes-driven.

- **Backend Sentry SDK polish.** Tags from FastAPI handlers (operation, auth role, `audit.event_id`), `beforeSend` for known-benign Pydantic 422s, optional artifact-bundle pattern for backend. **Gate:** ≥3 production issues opened from a GlitchTip event within 30 days post-MVP rollout.
- **Alerting.** GlitchTip → webhook (Slack-like / email) on first occurrence of a new issue in last 24h. **Gate:** measurable evidence that pull-only failed (real production incident triaged >24h after first event).
- **CI auto-verify.** `verify-symbolication.sh` runs automatically post-deploy via a BMAD `tea` CI pipeline; gates deploy on exit code. **Gate:** 3d-portal has a CI runner reachable from `.190` LAN (currently none exists for this repo).

#### Vision (Future)

- **Multi-project pattern reuse.** Vite-plugin contract (env-var spec, BuildKit secret pattern, `release.ts` single-source) promoted into `~/repos/configs/docs/observability-logging-contract.md` so the next homelab project starts at this brief's end-state.
- **Observability-as-BMAD-input** as a generic pattern, not GlitchTip-specific. Other observability tools (OpenSearch, Prometheus alerts) could expose triage scripts emitting BMAD story stubs.
- **CI-grade verify harness.** `verify-symbolication.sh` generalized into a multi-check post-deploy smoke harness reusable across services in the homelab.
- **Operational metrics dashboard.** After 6+ months in production, surface count of "GlitchTip → BMAD story → ship" cycles per week as a load-bearing health metric in the homelab observability dashboard. Closes the BMAD-input thesis with an evidence trail.

### User Journeys

This is internal infrastructure for a single-developer homelab; "personas" are not aspirational marketing constructs but actual people / processes that hit the system:

- **AI agent** (Claude Code, Codex, Gemini, etc.) — primary debugging surface; reads GlitchTip via REST/curl/jq, never opens UI.
- **Michał** — solo developer; human escalation path when an agent escalates or when triaging in person between sessions.
- **`deploy.sh`** — non-human actor; the deploy script that orchestrates build + ship + verify and emits operator-readable signals.

#### Journey 1 — AI agent triages a production error (happy path)

A user reports "the catalog detail page sometimes shows nothing when I open model 142". An AI agent in a `bmad-quick-dev` session takes the report.

**Opening:** Agent runs `./infra/scripts/glitchtip-triage.sh 142` (or queries `GET /api/0/projects/homelab/3d-portal/issues/?statsPeriod=24h&query=catalog` directly). Response: a structured markdown stub naming `apps/web/src/modules/catalog/components/ExternalLinksPanel.tsx:73` as the top frame, fingerprint `tx_a7e2`, route `/catalog/$id`, model `m_142`, release `0.1.0+ab12cd3`, last 5 events spanning 12 minutes.

**Rising action:** Agent does not need to open the GlitchTip UI. The stub already names the file, the line, and the conditions. Agent runs `bmad-quick-dev` with the stub as direct input — a story stub becomes a working bug fix without an intervening "let me click around in the dashboard" step.

**Climax:** TDD red phase reproduces the malformed `external_links` parse error in `ExternalLinksPanel.test.tsx`. Green phase fixes the parser. Refactor extracts validation. `npm run test:visual` confirms no UI regression.

**Resolution:** PR ff-merges, `deploy.sh` runs auto-deploy. After deploy, `verify-symbolication.sh` confirms GlitchTip is still hot. Agent marks the GlitchTip issue resolved via `curl -X PUT /api/0/issues/142/ -d '{"status":"resolved"}'`.

**Capabilities revealed:**

- `glitchtip-triage.sh` script with stable output contract (markdown story stub, defined fields).
- Useful tags on every event: `route.pathname`, `model.id`, `release` with git SHA, `auth.is_authenticated`.
- Symbolicated stack frames pointing at real `.tsx:line`.
- REST PUT on issue status (baseline; documented as part of the workflow).

#### Journey 2 — `deploy.sh` runs `verify-symbolication.sh` and it fails

Operator runs `bash infra/scripts/deploy.sh` after a normal feature merge. Build, ship, restart all complete. Then:

**Opening:** `deploy.sh` calls `infra/scripts/verify-symbolication.sh` as a non-fatal warning. Verify launches a smoke event with `smoke.run_id=<uuid>` via the prod URL `?__sentry_smoke=<uuid>`, polls GlitchTip REST `/issues/?statsPeriod=5m`. After 30 seconds the matching event appears but the top frame is `index-DhGq2.js:13` — not a `.tsx`.

**Rising action:** Verify exits non-zero internally; `deploy.sh` prints a loud red warning ("⚠ symbolication verification FAILED"). It also writes `infra/.last-verify` with a `FAILED` marker AND emits a synthetic GlitchTip event tagged `deploy.verification=failed`. No deploy rollback — the deploy succeeded; only its observability post-condition failed.

**Climax:** Operator (or AI agent on next session) sees the warning, checks the build log, finds the plugin upload step warned with "release not found" (issue #299 fired). They run `bash infra/scripts/upload-sourcemaps.sh` manually — the CLI fallback path. CLI uploads under release `0.1.0+ab12cd3` successfully.

**Resolution:** Operator re-runs `bash infra/scripts/verify-symbolication.sh` standalone. Event resolves to `.tsx:line`. Last-verify timestamp updates. The next `deploy.sh` invocation starts clean.

**Capabilities revealed:**

- Failed-verify writes `infra/.last-verify` with FAILED marker.
- Failed-verify emits synthetic GlitchTip event so the alarm channel exists in-band.
- `deploy.sh` prints loud warning but does NOT block deploy on verify failure.
- CLI fallback (`upload-sourcemaps.sh`) accepts the same release tag as the plugin (single-source `RELEASE`).
- Standalone re-run of `verify-symbolication.sh` is a documented recovery step.

#### Journey 3 — Plugin upload fails hard during build (issue #299 or auth)

Same flow as Journey 2 but earlier — at `vite build` time inside the docker image build.

**Opening:** Operator runs `bash infra/scripts/deploy.sh`. Build phase enters the Vite plugin's upload step. Plugin returns 401 (auth token expired) OR plugin uploads return 200 but the `assemble` call returns 404 (issue #299).

**Rising action:** Plugin is configured with hard-fail policy. `vite build` exits non-zero. `docker build` fails. `deploy.sh` aborts with no image shipped — production stays at the previous version.

**Climax:** Operator sees the build log clearly naming the failing step (e.g., "sentry-cli upload: 404 release not found"). The current image on `.190` is unchanged; users see no degradation.

**Resolution:** Operator decides: rotate the auth token (if 401), or run the manual recovery (CLI upload + retry deploy with plugin disabled for one cycle, file follow-up to investigate #299) if it's the GlitchTip-side bug. Either way, the recovery path is documented in `operations.md`.

**Capabilities revealed:**

- Plugin failure policy = hard-fail = build aborts, image not shipped.
- Build log surfaces upload-step exit reason cleanly (no "warning, continuing").
- CLI fallback is the documented recovery; `operations.md` names the exact flag/sequence to use it.
- Token rotation is a single-step operational task (re-mint via UI, update `infra/.env`).

#### Journey 4 — Auth token rotation (operational maintenance)

Quarterly or after a perceived risk event, Michał rotates `GLITCHTIP_AUTH_TOKEN`.

**Opening:** Michał opens GlitchTip web UI on LAN/VPN, navigates Profile → Auth Tokens, creates a new token with scopes `org:read`, `project:read`, `project:write`, `project:releases`, `event:write`.

**Rising action:** New token replaces value in `infra/.env` (dev box only). Old token revoked. Michał immediately runs `bash infra/scripts/deploy.sh` to validate the new token works in the plugin upload step.

**Climax:** Build completes; plugin upload succeeds against `:8800` with the new token. Deploy ships, `verify-symbolication.sh` passes. New token is now the active one.

**Resolution:** Old token revoked in UI; Michał notes the rotation date in `docs/operations.md`. No production impact, no downtime, no special handling.

**Capabilities revealed:**

- Token-rotation steps documented in `operations.md`.
- BuildKit secret mount reads token from `infra/.env` at build time, so rotation = edit one file + run deploy.
- Required token scopes named explicitly so the operator can replicate without trial and error.
- Rotation is a same-day operation, not a multi-step migration.

#### Journey Requirements Summary

| Capability | Revealed by | In MVP |
|---|---|---|
| `glitchtip-triage.sh <issue_id>` with stable markdown story-stub contract | J1 | ✓ |
| Useful event tags (`route.pathname`, `model.id`, `git.commit`, `auth.is_authenticated`, `host.name`, `service.version`, `build.time`) | J1 | ✓ |
| Symbolicated stack frames in production events | J1, J2 | ✓ |
| `verify-symbolication.sh` (smoke event + 30s poll + fingerprint match) | J2 | ✓ |
| `infra/.last-verify` timestamp file (success + FAILED marker) | J2 | ✓ |
| Failed verify emits synthetic GlitchTip event tagged `deploy.verification=failed` | J2 | ✓ |
| `deploy.sh` warns on stale last-verify but does not block | J2 | ✓ |
| Plugin hard-fail on upload error → `vite build` exits non-zero | J3 | ✓ |
| `infra/scripts/upload-sourcemaps.sh` runnable as manual recovery (decoupled, header-commented) | J2, J3 | ✓ |
| BuildKit secret for `SENTRY_AUTH_TOKEN` | J3, J4 | ✓ |
| Token rotation procedure documented in `operations.md` | J4 | ✓ |
| Single-source `RELEASE` constant (drift = TS error) | J1, J2, J3 | ✓ |

### Web App Specific Requirements (Observability Delta)

#### Project-Type Overview

The host project is an existing React 19 + Vite 6 SPA. Standard `web_app` concerns (SPA/MPA, browser support, SEO, real-time, accessibility) are **frozen at baseline** — this delta does not touch any of them. The slice introduces three architectural surfaces the host did not need before: build-pipeline observability hooks, runtime SDK filtering + tagging, and operational CLI scripts.

#### Frozen Baseline (No Changes)

| Concern | Baseline state | Touched by this PRD? |
|---|---|---|
| Routing / SPA | TanStack Router + `<Sentry.ErrorBoundary>` (Phase 3, 2026-04-30) | No |
| Browser support | Evergreen | No |
| SEO | N/A — auth-gated homelab | No |
| Real-time | None in v1 (`queue`/`printer`/`spools` are v2 slots) | No |
| Accessibility | i18n keyset gated by visual regression | No (visual reg matrix preserves no-regression invariant) |

#### Build Pipeline Requirements

- **Plugin placement.** `@sentry/vite-plugin` MUST be the last entry in `vite.config.ts` `plugins[]`. Earlier placement risks tree-shaking stripping instrumentation and/or maps generating before debug-ID injection.
- **Build mode.** Plugin runs on `vite build` only (not `vite serve`). Dev server stays untouched.
- **Source-map invariant.** `build.sourcemap = 'hidden'` (already set). Plugin's `filesToDeleteAfterUpload: ['./dist/**/*.map']` removes maps from `dist/` post-upload, before docker image extraction reads `dist/`.
- **Token transport.** `SENTRY_AUTH_TOKEN` flows via BuildKit secret mount, NOT plain `ARG`. Other Sentry/GlitchTip configuration (`SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_URL`) flows via plain build args.
- **Determinism.** Plugin executes inside the docker build stage that produces `dist/`. Local `pnpm build` is not part of `deploy.sh` — bundle hashes derive from the in-image build only.

#### SDK Config Requirements

- **Single-source release.** `apps/web/src/release.ts` exports `RELEASE: string`. Imported by both `instrument.ts` (runtime) and `vite.config.ts` (build-time plugin). Drift = TypeScript compile error, not runtime mystery.
- **Tag taxonomy.** Aligned with `~/repos/configs/docs/observability-logging-contract.md` (ECS-style dotted names): `service.version`, `host.name`, `deployment.environment`, plus 3d-portal-specific `git.commit`, `build.time`, `route.pathname`, `model.id`, `auth.is_authenticated`. Static tags attach at SDK init; route-bound tags attach on TanStack Router navigation events.
- **`beforeSend` filter contract.** Drops events on: deny-list URL match, `!navigator.onLine`, or `ApiError.detail === "access_expired"` (normal refresh-flow noise). Returns the event for everything else.
- **Filter ruleset source.** Derived from a 30-day GlitchTip issue sample collected in Phase 0 Discovery. Anticipated minimums (browser-extension URLs, `ResizeObserver loop`) are a floor, not a ceiling.

#### CLI / Operational Script Requirements

This slice INTRODUCES `cli_commands` to the project (standard `web_app` `skip_sections` does not apply here).

- **`infra/scripts/verify-symbolication.sh`** — bash + curl + jq. Reads auth from `infra/.env`. Triggers smoke event with `smoke.run_id=<uuid>`, polls REST for ≤30s, asserts top frame matches `^apps/web/src/.+\.tsx?$`. Exit code 0 on success, non-zero on FAILED. Side effects: write `infra/.last-verify` (timestamp + status); emit synthetic GlitchTip event tagged `deploy.verification=failed` on failure.
- **`infra/scripts/glitchtip-triage.sh <issue_id>`** — bash + curl + jq. Read-only against GlitchTip REST. Outputs markdown story stub with defined fields (top frame, fingerprint, route, model_id, release SHA, last 5 events, suggested file). Stable contract — downstream BMAD tools parse this format.
- **Dependencies.** `jq` required on dev box for both scripts. Both use `set -euo pipefail`; no silent `|| true` on critical operations.
- **Error model.** REST 4xx/5xx surfaces as non-zero exit + stderr. Token scope mismatch (e.g., missing `event:write`) results in 403 → hard error in script.

#### Implementation Considerations

- **Idempotency.** `verify-symbolication.sh` re-runnable: each run uses a fresh `smoke.run_id=<uuid>`, no state collision. `glitchtip-triage.sh` is read-only.
- **Network reachability.** Build-time upload (`:8800`) requires LAN reach to `.190` (1MB body limit on HTTPS forces LAN HTTP). Runtime ingest (`https://glitchtip.ezop.ddns.net`) works over public internet. Off-LAN dev box → deploy fails by design.
- **Visual regression interaction.** No UI changes in this PRD; `npm run test:visual` produces zero diffs across all 4 projects (desktop-light/dark, mobile-light/dark). Any diff = unintended regression = stop signal.

### Project Scoping & Phased Development

The phasing structure is defined by the input brief — this section formalizes Strategy, Resources, and Risk Mitigation. For the actual feature breakdown across phases, see the **Product Scope** section above (MVP / Growth / Vision).

#### MVP Strategy & Philosophy

**MVP Approach: "Operational discipline MVP."** Goal is to prove the GlitchTip-as-BMAD-input loop is load-bearing for a single solo-dev + AI-agent debugging workflow before investing in adjacent surfaces (backend polish, alerting, CI auto-verify). Each Phase 2 trigger is a measurable threshold, not a calendar date.

**Resource Requirements:**

- **Team:** Solo developer (Michał) + AI agents executing BMAD stories. No additional human contributors.
- **Skills required:**
  - Vite 6 + TypeScript build configuration
  - BuildKit secret mounting in multi-stage Dockerfile
  - Bash + curl + jq scripting
  - GlitchTip REST API + chunk-upload protocol
  - TanStack Router event subscriptions
- **External access required at build/run time:**
  - LAN/VPN reach to `192.168.2.190:8800` (GlitchTip chunk-upload endpoint)
  - Public internet to `https://glitchtip.ezop.ddns.net` (event ingest)
  - Existing `GLITCHTIP_AUTH_TOKEN` in `infra/.env` with required scopes (or operator UI access to mint one)
- **Time budget:** 2–3 person-days wall-clock for MVP, broken into stories during `bmad-create-epics-and-stories` (Step CE).

#### Phase Boundaries

- **Phase 1 (MVP) — this PRD's scope.** Ships when all Technical Success criteria pass and `verify-symbolication.sh` returns green on the deploy that lands the changes.
- **Phase 2 (Growth) — gated, not scheduled.** Each item in Growth Features (Backend Sentry polish; Alerting; CI auto-verify) carries an explicit measurable gate. None ships on a date; each ships when its gate fires.
- **Phase 3 (Vision) — direction, not commitment.** Multi-project pattern reuse, observability-as-BMAD-input as a generic pattern, CI-grade verify harness, operational metrics dashboard. No timeline. Listed to keep architectural intent visible during MVP execution so MVP decisions don't accidentally close those doors.

#### Risk Mitigation Strategy

| Risk class | Specific risk | Mitigation in MVP |
|---|---|---|
| Technical | GlitchTip backend issue #299 fires (`artifactbundle/assemble` 404) | Phase 0 dry-run gate (one-shot `vite build` against homelab GlitchTip BEFORE merging plugin). If #299 fires → abort plugin migration, keep CLI flow, ship SDK polish + scripts only. |
| Technical | Plugin upload hard-fail blocks deploy on transient GlitchTip outage | CLI fallback documented + one-command runnable (`bash infra/scripts/upload-sourcemaps.sh`). Operator runs CLI → re-runs deploy. No production downtime — deploy aborts before image ship; prod stays at previous version. |
| Technical | Source map leakage to public bundle | `filesToDeleteAfterUpload` + `build.sourcemap='hidden'` invariant + post-deploy `curl` 404 verification. Codified in Technical Success #4. |
| Technical | `SENTRY_AUTH_TOKEN` leaks via image layers | BuildKit secret mount instead of `ARG`. `docker history` check codified in Technical Success #5. |
| Operational | Manual verify ritual decays over time | Instrumented: `verify-symbolication.sh` writes timestamp; `deploy.sh` warns at next invocation if last-verify older than last deploy. Synthetic GlitchTip event on failure provides in-band alarm channel. |
| Operational | Auth token expires or scope drifts | Quarterly rotation procedure in `operations.md` (Journey 4). 403 from upload step surfaces as hard build failure with clear stderr → operator re-mints. |
| Resource | Solo developer scope creep | Brief explicitly out-of-scopes backend, alerting, CI auto-verify with measurable gates. Phase 0 + Discovery + ≤2–3 person-day budget enforced via BMAD story decomposition in Step CE. |
| Market | N/A — single-tenant homelab, no commercial/market exposure | — |

### Functional Requirements

This section is the capability contract for downstream work. Architects, story-writers, and AI agents implementing this PRD will only support what is listed here. All capabilities are stated implementation-agnostically at PRD altitude — the architecture brief pins specific tools and protocols.

#### A. Production Frontend Symbolication

- **FR1:** Production `vite build` emits unique debug IDs into the served JavaScript bundle and emits matching source maps to a non-public artifact location (not the deployed bundle).
- **FR2:** The build uploads source maps + debug IDs to the homelab GlitchTip instance such that GlitchTip can resolve a runtime stack frame to its original `.tsx:line` source location.
- **FR3:** The runtime SDK reports a `release` value identical to the `release` used at upload time, derived from a single shared expression in the codebase (drift-impossible by construction).
- **FR4:** When the upload step fails for any reason (auth, network, GlitchTip-side bug), the production build fails hard with a non-zero exit and the deploy aborts before any image is shipped. There is no warn-and-continue path.

#### B. Event Noise Filtering & Tagging

- **FR5:** The runtime SDK drops events originating from browser-extension URLs (`chrome-extension://`, `moz-extension://`, `safari-web-extension://`).
- **FR6:** The runtime SDK drops events matching well-known noise titles (e.g., `ResizeObserver loop limit exceeded`, `Non-Error promise rejection captured`) plus an empirically-derived deny-list determined from a 30-day sample of real events on the homelab GlitchTip instance.
- **FR7:** The runtime SDK drops events when the user is offline (`!navigator.onLine`) or when an `ApiError` represents a normal `access_expired` refresh-flow round-trip.
- **FR8:** Every emitted event carries static identity tags: `service.version`, `host.name` (build host), `deployment.environment`, `git.commit`, `build.time`. These attach once at SDK init.
- **FR9:** Every emitted event carries dynamic context tags: `route.pathname`, `model.id` (when present in the current route), `auth.is_authenticated`. These re-attach on each TanStack Router navigation event.

#### C. Post-Deploy Verification

- **FR10:** Operators (human or automated) can run a single command that triggers a deterministic frontend smoke event in production, polls GlitchTip for that event, and asserts the top stack frame resolves to a real source file path.
- **FR11:** The verification process uses a unique per-run fingerprint (`smoke.run_id=<uuid>`) so concurrent or accidental matching events cannot produce false positives.
- **FR12:** The verification process has a bounded time budget (≤30 seconds total wall-clock) and exits non-zero if it cannot match a successfully-symbolicated event within that window. **Exit code contract:** `0` = success (smoke event symbolicated to a real `.tsx:line`); `1` = symbolication broken (event found but top frame fails the `^apps/web/src/.+\.tsx?$` regex); `2` = GlitchTip unreachable (REST network error or 5xx); `3` = auth/scope failure (REST 401/403); `4` = timeout (no matching event within 30s budget). Stable contract — `deploy.sh` and any downstream automation depend on these specific codes.
- **FR13:** A successful verification persists a timestamp + status marker that subsequent `deploy.sh` invocations can read.
- **FR14:** A failed verification persists a `FAILED` marker and emits a synthetic GlitchTip event tagged `deploy.verification=failed`, providing an in-band alarm channel without external infrastructure.
- **FR15:** `deploy.sh` invokes the verification step at the end of every deploy as a non-fatal warning (deploy success is decoupled from verification result, but operator output makes the result loud).
- **FR16:** `deploy.sh` warns on its NEXT invocation if the previous deploy did not record a successful verification (instrumented decay protection).

#### D. GlitchTip-to-BMAD Triage Bridge

- **FR17:** Operators can run a single command (`<script> <issue_id>`) to convert a GlitchTip issue into a structured markdown story stub.
- **FR18:** The story stub contains a stable, documented set of fields: top stack frame `(filename:line)`, fingerprint, route context, `model.id` when present, release SHA, last 5 events with timestamps, and at least one suggested file to edit.
- **FR19:** The story stub conforms to a documented schema with fields in fixed order (per FR18) and is parsed unmodified by `bmad-quick-dev` or `bmad-create-story` invocations — no manual reformatting, no preprocessing, no field reshuffling required.
- **FR20:** The triage command is read-only against GlitchTip — running it does not modify any issue state.

#### E. Build-Time Security & Determinism

- **FR21:** The GlitchTip authentication token used for source-map upload never appears in the final docker image's layer history (verifiable via `docker history`).
- **FR22:** The deployed bundle does not expose source map files publicly (`*.js.map` URLs return 404 from production).
- **FR23:** The build executes inside the same docker image stage that produces the deployed `dist/` artifacts — bundle hashes derive from the in-image build only, regardless of which dev box invoked the deploy.
- **FR24:** Production `build.sourcemap` setting remains `'hidden'` so the deployed bundle has no `sourceMappingURL` directive — browsers do not fetch maps in any context.

#### F. Operational Continuity & Recovery

- **FR25:** A documented one-command CLI fallback path exists for source-map upload that does not depend on the in-build plugin succeeding.
- **FR26:** The fallback path uses the same release identity as the primary plugin path so symbolication on the homelab GlitchTip is consistent regardless of which path delivered the maps.
- **FR27:** Operators can rotate `GLITCHTIP_AUTH_TOKEN` in a single same-day operation: re-mint via UI, update `infra/.env`, run a normal deploy. The procedure is documented in the operations runbook.
- **FR28:** Required token scopes (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`) are explicitly listed in the runbook so an operator can replicate without trial and error.

#### G. Documentation & Execution Discipline

- **FR29:** The operations runbook (`docs/operations.md`) replaces its current "Sentry vite-plugin out-of-scope follow-up" note with the new ritual: deploy + verify; manual recovery procedure; token rotation procedure; triage script usage.
- **FR30:** The project context file (`_bmad-output/project-context.md`) carries three new execution-discipline rules: run verify-symbolication after every deploy until CI lands; use the triage script before manual triage of a GlitchTip-reported bug; "every replacement keeps its predecessor as documented manual recovery for one release cycle".

### Non-Functional Requirements

Selective: only categories that materially apply to a single-tenant homelab observability delta. Scalability and Accessibility are intentionally omitted.

#### Performance

- **NFR-P1: SDK runtime overhead is bounded.** Sentry SDK at runtime consumes ≤2 KB additional payload per emitted event (event body excluding stack frames, capped via `tracesSampleRate: 0` and structured breadcrumb limits inherited from baseline). User-perceived page load impact: zero — SDK init is non-blocking via the deferred module bundle.
- **NFR-P2: Build-time plugin upload latency is bounded.** Source-map upload to `:8800` adds ≤10 seconds to docker build wall-clock for the current bundle size (~2 MB minified, ~6 MB source maps total). If upload exceeds 60 s, the build fails with a clear timeout error.
- **NFR-P3: `verify-symbolication.sh` total budget ≤30 seconds.** Includes smoke event emission, GlitchTip ingestion lag, REST poll, fingerprint match. Hard exit at 30 s with FAILED marker (codifies FR12 as an SLO).
- **NFR-P4: `glitchtip-triage.sh` returns within 5 seconds for typical issue lookup.** Single REST GET to `/issues/<id>/events/latest/`; 10 s ceiling for large events. No retry loop on transient 5xx — fail clean.

#### Security

- **NFR-S1: Token-at-rest scope.** `GLITCHTIP_AUTH_TOKEN` exists ONLY in `infra/.env` on the dev box (mode 600). Never on `.190`. Never in image layers. Never in commit history. Never in BMAD planning artifacts (the gitignored `_bmad-output/` enforces the last point).
- **NFR-S2: Token rotation cadence.** Quarterly rotation is the documented baseline (Journey 4). Ad-hoc rotation triggered by perceived risk events (laptop loss, accidental disclosure, scope drift). Rotation is a same-day operation per FR27.
- **NFR-S3: Token scope minimization.** The build-time token carries exactly the scopes needed for upload + release management + triage (`org:read`, `project:read`, `project:write`, `project:releases`, `event:write`). It does NOT carry `org:write`, `org:admin`, or anything else.
- **NFR-S4: Build-time network exposure minimized.** The build process reaches out to exactly two hosts: `192.168.2.190:8800` (GlitchTip chunk upload) and any registry mirrors needed for `npm install`. No outbound to public Sentry SaaS, no telemetry to plugin vendor (`@sentry/vite-plugin` configured with `telemetry: false` for self-hosted targets).
- **NFR-S5: No source-code leakage post-deploy.** Verified at every deploy via `verify-symbolication.sh` extension OR documented manual `curl https://3d.ezop.ddns.net/assets/<hash>.js.map` returning 404. (Codified as FR22; this NFR ratifies the cadence: every deploy.)

#### Reliability

- **NFR-R1: `verify-symbolication.sh` false-positive rate ≤1 per 100 deploys.** A false positive (script reports SUCCESS while symbolication is actually broken) erodes trust faster than any other failure mode. Implementation requirement: regex match on top frame `filename` MUST match `^apps/web/src/.+\.tsx?$` — permissive globs forbidden.
- **NFR-R2: CLI fallback path verified at least once per release cycle.** When the active path is the plugin (default after MVP lands), the fallback CLI path is manually exercised at least once per release cycle (operator runs `bash infra/scripts/upload-sourcemaps.sh` against the current build to confirm it still works). Codified as a `project-context.md` execution-discipline rule.
- **NFR-R3: Deploy never ships in observability-broken state without operator-visible signal.** Either (a) plugin upload succeeds and a happy verify lands, or (b) plugin upload fails and the deploy aborts entirely (FR4), or (c) plugin upload succeeds but verify fails — and in case (c), `deploy.sh` prints a loud red warning AND a synthetic GlitchTip event emits AND `infra/.last-verify` carries a FAILED marker that the next deploy reads (FR14 + FR16). Three independent signals; the failure cannot stay silent.
- **NFR-R4: Manual ritual decay detection window: 1 deploy cycle.** `deploy.sh` warns at next invocation if `infra/.last-verify` timestamp is older than the previous deploy. Codified as FR16; this NFR sets the maximum tolerable gap.

#### Integration

- **NFR-I1: GlitchTip REST API dependency is versioned.** Implementation depends on GlitchTip 6.1.x API surface (`/api/0/projects/...`, `/api/0/issues/...`, chunk-upload protocol). When the homelab GlitchTip upgrades to 7.x, this PRD's scripts require re-validation — tracked in `operations.md` upgrade checklist.
- **NFR-I2: Tag taxonomy alignment with `observability-logging-contract.md`.** Static identity tags (`service.version`, `host.name`, `deployment.environment`) follow the contract's ECS-style dotted naming. 3d-portal-specific extensions (`route.pathname`, `model.id`, `git.commit`, `build.time`, `auth.is_authenticated`) preserve the dotted convention. Drift in either direction requires explicit reconciliation, not silent divergence.
- **NFR-I3: BMAD pipeline contract for `glitchtip-triage.sh` output.** Output format is stable and documented (FR18). Changes to the field set or order are breaking changes requiring a follow-up PRD, not a silent edit. Fixed field order: top frame `(filename:line)`, fingerprint, route context, `model.id` (when present), release SHA, last 5 events, suggested file. **Verifiable:** `./infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -` returns zero changes. Diff failure during verify / CI means schema drift and must be reconciled to PRD via a follow-up edit, not absorbed silently.
- **NFR-I4: configs repo cross-reference integrity.** Brief and PRD reference `~/repos/configs/docs/glitchtip-agent-guide.md` and `observability-logging-contract.md` as load-bearing inputs. Revisions to those documents that affect this PRD's scope (new GlitchTip endpoints, new tag conventions) require reconciliation into a follow-up PRD or amendment, not silent absorption.

## Initiative 2 — Agent Runbook + Legacy SoT Triage

**Status:** ✅ shipped 2026-05-11 (started 2026-05-10, single-session autonomous + Codex review cycles). Maintainer: Ezop. Brownfield extension to the SoT-migrated catalog (`portal.db` + `portal-content` volume, completed 2026-05-06 per `docs/operations.md` § "SoT migration"). Initiative 2 closes the gap admitted at `docs/operations.md:381-385` ("agent does most creates anyway" but no runbook exists) and triages the legacy `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` folder that the SoT migration left behind.

### Document Map

For readers landing cold (especially AI agents in downstream BMAD steps):

| Section | Purpose |
|---|---|
| Executive Summary + What Makes This Special | The pitch and the differentiator (self-serving runbook + OpenAPI auto-discovery) |
| Project Classification | Type / domain / complexity / context — single-row context for downstream steps |
| Success Criteria | User / Operational / Technical / Measurable Outcomes |
| Product Scope | MVP / Growth / Vision feature inventory |
| Functional Requirements | 11 FRs across 7 capability groups (A–G) — binding capability contract |
| Non-Functional Requirements | 8 NFRs across Pull-Only Ergonomics / Security / Reliability / Documentation / Portability |

### Executive Summary

After Slices 2A–2D + 3A–3F shipped the SoT catalog (`portal.db` on `.190` plus the `portal-content` volume; 89 models, 821 binary files, 243 tags, 43 categories at the time of cutover), one operational seam stayed open: the workflow "agent receives a URL (Printables / Thangs / Thingiverse / MakerWorld / Creality Cloud) and lands the model in the portal" exists only implicitly. The legacy `AGENTS.md` at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` documented this workflow for the pre-SoT file-based world (`_index/index.json`, folder layout invariants, Printables GraphQL `getDownloadLink`, 3MF conversion). That knowledge has not been ported to the new SoT-on-DB world. `docs/operations.md:381-385` acknowledges the gap directly: *"Full-page /admin/models/new for creating a model from scratch. Admin can use the API or the migration script in the meantime; the agent does most creates anyway."* — but no runbook exists.

Initiative 2 closes that gap and adds a second-order improvement: the runbook is **served by the portal itself**, not just committed to `docs/`. The portal becomes a self-documenting target. Bootstrap reduces to three lines an operator types to a fresh agent (Claude, Codex, anything else): "3d-portal is at `https://3d.ezop.ddns.net`; `curl /agent-runbook` for principles + workflow; `curl /api/openapi.json` for endpoint catalog; agent password at `~/.config/3d-portal/agent.password` — login via `POST /api/auth/login`, ride the cookie." Everything else is pulled by the agent on demand.

The runbook is split by **what auto-discovery can and cannot deliver**: narrative, behavioral rules, and external-API recipes (Printables GraphQL) live in the curated runbook markdown; endpoint catalogs, request/response schemas, and status codes live in OpenAPI (auto-generated by FastAPI from route signatures — drift-impossible). A new endpoint in `apps/api/app/modules/sot/admin_router.py` requires zero runbook update.

The legacy folder (`/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`, ~2.7 GB on Windows-synced Nextcloud volume) is also triaged: it currently serves three roles — (a) restore snapshot for `migrate_from_index_json.py` + `hydrate_local_tree.py`, (b) 2.7 GB 3MF originals archive (redundant — bits are on `.190`), (c) home of the un-migrated `AGENTS.md` runbook knowledge. Once the runbook adoption (FRs A–B) lands, role (c) ends. Initiative 2 produces a written decision either retiring `Model.legacy_id` + 4 migration scripts entirely, or freezing them with a "do-not-touch-unless-restore" marker; rationale captured in `docs/migration-reports/` for durability.

#### What Makes This Special

Three properties together set this initiative apart from a generic "write an internal agent doc" effort:

1. **The portal documents itself.** `/agent-runbook` is served by the same FastAPI process that handles `/api/admin/models`. Runbook deploys with API; version-skew between "agent reads stale runbook from a forked repo" and "API has different endpoints" is impossible by construction. Bootstrap for a new agent is one URL.
2. **Layered auto-discovery (narrative + OpenAPI), not duplicated catalog.** Endpoint signatures live in OpenAPI (auto-generated, drift-impossible). The runbook documents behavioral rules and external-API recipes that OpenAPI cannot express ("first STL upload auto-enqueues render", "3MF must convert before upload"). New `@router.post` requires zero runbook edit. Adding a new behavioral rule does require a runbook edit — and that edit is the only manual surface.
3. **Agent-portable, not Claude-specific.** Tools invoked are CLI (`curl`, `jq`, `python3`, `agent-browser` for browser-only sources) or REST. Claude, Codex, or a future homelab automation script can execute the same runbook against the same endpoints with the same token. No `Read` / `Bash` / agent-specific abstractions leak into the runbook.

**Core insight:** Initiative 2 inherits Initiative 1's principle (*"AI agents are roughly half the user base"*) and pushes it one layer deeper. Where Initiative 1 made errors agent-readable (triage script → BMAD stub), Initiative 2 makes the **portal's operational surface** agent-readable (self-served runbook + auto-discovered endpoints). The single onboarding URL is the load-bearing simplification.

### Project Classification

| Field | Value | Rationale |
|---|---|---|
| **Project type** | `tooling+docs` | Output is one markdown runbook + one read-only FastAPI route + optional CLI script + one migration-report decision doc + OpenAPI metadata enrichment. No production-business-logic code paths added. |
| **Domain** | `general` | Self-hosted homelab catalog. No vertical-specific compliance. |
| **Complexity** | `low` | ~1 markdown doc (`docs/agents-add-model-runbook.md`, sourced from existing legacy AGENTS.md + new agent-token + REST workflow content), ~10 lines of FastAPI route, nginx pass rule, optional ~150-line Python CLI, one migration-report markdown. Estimated 1–2 person-days of agent execution time. |
| **Project context** | `brownfield` | Layered on the post-SoT-migration codebase (Slices 2A–2D + 3A–3F, 2026-05-06 + 2026-05-10). Initiative 1 (GlitchTip delta) already established the "AI agents as primary consumer" design discipline; Initiative 2 extends it. |

### Success Criteria

#### User Success (the user is the agent)

- **One URL onboarding.** A fresh agent given `https://3d.ezop.ddns.net/agent-runbook` + `~/.config/3d-portal/agent.password` path can create a model from a Printables URL within 15 minutes of receiving its first instruction, without reading any file in `~/repos/3d-portal/`. Acceptance: FR8 smoke-test executed by an agent that has never seen the repo.
- **Auto-discovery for endpoint mechanics.** Agent never needs to read `apps/api/app/modules/sot/admin_router.py` to know the endpoint surface. `curl https://3d.ezop.ddns.net/api/openapi.json | jq '.paths | keys[]'` returns the full catalog; per-endpoint schema is one further `jq` away. Acceptance: FR8 smoke-test transcript shows OpenAPI used as the endpoint source, not source-file reads.
- **Agent-portable.** Claude and Codex can both execute the runbook. Acceptance: NFR5 — runbook contains no `Read`/`Bash`/`Edit`/agent-specific tool names.

#### Operational Success

- **Zero manual upkeep on endpoint changes.** Adding a new endpoint in `app/modules/sot/admin_router.py` requires no runbook edit. Verified by NFR8 (no endpoint signatures duplicated in runbook markdown). The first such drift incident would invalidate the architecture; tracked as a follow-up if it occurs.
- **Legacy folder decision is written, not implicit.** The "drop `legacy_id` + scripts vs. freeze with marker" call lands in `docs/migration-reports/2026-05-XX-legacy-sot-folder-decision.md` with the inputs to the call (last `legacy_id` use date from `audit_log`, schema compatibility verification, backup strategy if scripts retire). Acceptance: FR7 + NFR4.

#### Technical Success

- **`/agent-runbook` endpoint live and verified at every deploy.** `deploy.sh` smoke-tests `/agent-runbook` returns content with a known fingerprint. Acceptance: NFR7 (sha256-pinned section in verify chain).
- **OpenAPI surface enriched for agent consumption.** Endpoint operations under `admin/` and `sot/` carry `summary` + `description`. Agent-writable endpoints tagged `agent-write`. Key request models have `examples` in `json_schema_extra`. Acceptance: FR11 enforced via a Pytest covering OpenAPI shape.

#### Measurable Outcomes

- ≥1 model successfully created via the documented runbook by an agent invoked in a fresh session (no repo context), within 30 days of Initiative 2 shipping. Captured as the `agent-runbook-smoke-2026-05-XX.md` artifact in `_bmad-output/implementation-artifacts/`.
- 0 endpoint-signature duplications between `docs/agents-add-model-runbook.md` and `apps/api/app/modules/sot/admin_router.py`, verified by NFR8 grep at smoke-test time.

### Product Scope

**MVP (FR1–FR8, FR10–FR11, all 8 NFRs):**
- Runbook content (curated narrative + Printables GraphQL recipe + 3MF workflow + source-detection table).
- `/agent-runbook` FastAPI route serving the markdown.
- OpenAPI surface enrichment (summaries, descriptions, tags, examples).
- Pre-flight checklist (DB-era: `GET /api/categories`, dedup-check).
- Token security model.
- Legacy folder triage decision (written rationale).
- End-to-end smoke-test acceptance.
- Deploy.sh verify integration for `/agent-runbook`.

**Growth (FR9):**
- `infra/scripts/add-model-from-url.py` CLI encoding the runbook as executable Python.

**Vision (deferred, out of scope):**
- Auto-categorization (suggest category from model name + description via LLM).
- Auto-tagging (extract tags from source metadata).
- Multi-source ingestion in one command (URL list as batch).

### Functional Requirements

#### A. Runbook Content & Curation

- **FR1: Agent runbook lives at one durable path.** The runbook file `docs/agents-add-model-runbook.md` is the authoritative source. The same content is also served via `GET https://3d.ezop.ddns.net/agent-runbook` (`Content-Type: text/markdown; charset=utf-8`). The content covers: agent principles (pull-only, REST + cookie session, idempotence); auth model (where the agent password lives, how to login + reuse cookies + CSRF header); source-detection table; per-source fetch recipes; 3MF conversion procedure; pre-flight checklist; pointer to OpenAPI for endpoint signatures. **The runbook MUST NOT duplicate endpoint signatures** — it points at OpenAPI for those. **Verifiable:** sha256 of a known intro section matches between the file and the endpoint response.
- **FR2: Source-detection table.** The runbook contains a table mapping URL host → fetch strategy. Sources covered at MVP: `printables.com` (GraphQL `getDownloadLink`), `thangs.com`, `thingiverse.com`, `makerworld.com`, `crealitycloud.com` (last four via `agent-browser` CLI against the operator's logged-in browser session). New sources extend the table by appending a row, no other runbook changes.
- **FR3: Printables GraphQL recipe.** Adapted from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` § "Downloading from Printables". Covers: endpoint `https://api.printables.com/graphql/`, authentication header pattern (no auth required for `getDownloadLink` on public models), mutation signature `getDownloadLink(id: STL_ID, printId: PRINT_ID, fileType: stl, source: model_detail)`, JSON response shape, file-fetch step. Includes one worked example with a real model ID.
- **FR4: 3MF conversion procedure.** Every `.3mf` file entering the catalog MUST be converted to per-object STLs via `infra/scripts/migrate_catalog_3mf.py --convert <file.3mf>` (script already exists per `docs/plans/2026-05-02-catalog-3mf-to-stl-migration-plan.md`). The original `.3mf` is archived to `_archive/3mf-originals/` (on `.190`) and not uploaded to the portal. The runbook documents the call signature and the post-condition; it does not duplicate the script's internal logic.

#### B. Self-Serving Endpoint & OpenAPI Discovery

- **FR10: `/agent-runbook` is the single discovery URL.** Public read endpoint (no auth — the runbook teaches authentication; gating it on auth is paradoxical). Edge proxy (`~/repos/configs/nginx/3d-portal.conf`) passes `/agent-runbook` to the API container. Response: `text/markdown` body, `200 OK` on success, `503` if the runbook file is missing in the image (deploy bug). Bootstrap message an operator gives to a fresh agent: `(1)` portal URL, `(2)` `curl /agent-runbook` for principles, `(3)` token path on the local machine. Three lines, no repo clone.
- **FR11: OpenAPI surface enrichment for agent consumption.** Each `@router.post/get/put/patch/delete` in `apps/api/app/modules/{admin,sot}/` carries an explicit `summary` (one-line) and `description` (multi-line, includes behavioral side-effects e.g. "auto-enqueues render on first STL upload"). Endpoints callable by the `agent` role are tagged `agent-write` (already exists as a role concept). Key Pydantic request models (`ModelCreate`, `ModelFilePatch`, `ModelPatch`, etc.) carry `model_config = {"json_schema_extra": {"examples": [...]}}` with at least one realistic example payload. **Verifiable:** Pytest in `apps/api/tests/test_openapi_agent_surface.py` asserts `summary` non-empty on all admin/sot routes + at least one example on each agent-writable request model.

#### C. Auth & Security

- **FR5: Agent service-account credentials security model documented in the runbook.** The agent service account is a regular `User` row with `role=agent`; credentials are a password (NOT a long-lived bearer token) at `~/.config/3d-portal/agent.password` (mode `600`, owner `ezop`). Login flow: `pw=$(cat ~/.config/3d-portal/agent.password); curl -c /tmp/portal-cookies.txt -X POST -H 'X-Portal-Client: web' -H 'Content-Type: application/json' -d '{"email":"agent@portal.local","password":"'"$pw"'"}' https://3d.ezop.ddns.net/api/auth/login` → server sets `portal_access` (`Path=/api`, ~30 min TTL) + `portal_refresh` (`Path=/api/auth`) cookies. All subsequent calls reuse via `-b /tmp/portal-cookies.txt`. **Mutations also require `-H 'X-Portal-Client: web'`** (CSRF gate). The password is read **inline** via `$(cat ~/.config/3d-portal/agent.password)` directly into the login body — never `export PASSWORD=$(...)` (persists in shell history), never echoed to stdout, never written to any file under `_bmad-output/` or `docs/` or any tracked path. JWT TTL is ~30 min; long-running agent sessions either cron daily re-login or call `POST /api/auth/refresh` with the refresh cookie. Rotation procedure documented: re-mint via `python -m scripts.bootstrap_agent --email agent@portal.local --rotate` on `.190` (prints new password to stdout once — capture and replace the file contents), no service restart required.

#### D. Operational Invariants

- **FR6: Pre-flight checklist (DB-era).** The runbook lists 5 pre-conditions the agent MUST verify before `POST /api/admin/models`: (1) category slug exists — query `GET /api/categories` and confirm the target slug is present; (2) model name sanitized — no Polish diacritics, no leading/trailing whitespace, no file extension; (3) at least one `.stl` file ready to upload after any 3MF/OBJ/STEP conversion; (4) duplicate-check — model not already in catalog under the same external-link URL (query existing models or rely on FR-link tag); (5) all source files in expected formats per FR4. The checklist is enforced by the agent, not the API — failures yield "stop and ask the operator", not "POST anyway and let the API 4xx".

#### E. Legacy SoT Folder Triage

- **FR7: Legacy folder decision recorded with written rationale.** Output: `docs/migration-reports/2026-05-XX-legacy-sot-folder-decision.md` (date stamped at execution). The document captures: (a) last observed use of `Model.legacy_id` field (query `audit_log` for any READ/WRITE referencing `legacy_id` since 2026-05-06); (b) schema compatibility check — would `migrate_from_index_json.py`, `backfill_legacy_renders.py`, `backfill_iso_thumbnail.py`, `fix_legacy_render_names.py` still run against the current schema (post-Alembic-0008) without code changes; (c) backup strategy if scripts are retired (one-time export of `Model.legacy_id` column to a frozen JSON + the existing 3MF archive becoming pure backup, OR keep scripts + folder as frozen restore artifact). Decision space: **drop `Model.legacy_id` + retire the 4 migration scripts entirely** OR **freeze the folder + scripts + `legacy_id` with a "do-not-touch-unless-restore" marker in `apps/api/scripts/README.md`**. The doc states the chosen option and the reasoning; execution (Alembic migration to drop the column, or README marker creation) is captured as a follow-up story.

#### F. Acceptance Contract

- **FR8: End-to-end smoke-test acceptance.** An agent (Claude or Codex) executes the full runbook flow against one real Printables URL in a fresh session (no prior repo context). Full transcript captured as `_bmad-output/implementation-artifacts/agent-runbook-smoke-2026-05-XX.md`. The smoke-test verifies: (a) `GET /agent-runbook` returned valid markdown ≥ a known minimum byte length and matching sha256 fingerprint of an intro paragraph; (b) `GET /api/openapi.json` returned valid OpenAPI 3.x JSON with at least the `admin/models` and `admin/models/{id}/files` paths present; (c) the agent issued `POST /api/admin/models`, `POST /api/admin/models/{id}/files` (multipart STL upload), and observed the auto-enqueued render in `arq-worker` logs OR via `GET /api/models/{id}` thumbnail field becoming non-null within 60 s; (d) the model is visible in the catalog at `https://3d.ezop.ddns.net/`. The transcript includes commands run, status codes, request/response bodies (token redacted), and the resulting model UUID.

#### G. Optional Growth — CLI Script

- **FR9: `infra/scripts/add-model-from-url.py`** (Growth scope; deferable). Single-file Python (≤200 lines) that encodes the runbook flow as executable code. Positional arg: source URL. Optional flags: `--category <slug>`, `--password-file <path>` (default `~/.config/3d-portal/agent.password`), `--email <addr>` (default `agent@portal.local`), `--portal <base-url>` (default `https://3d.ezop.ddns.net`). The script performs the full login flow internally (`POST /api/auth/login` → cookie jar → reuse for subsequent calls), with `X-Portal-Client: web` on every mutation. Progress logged to stdout as structured JSON-lines (mirrors observability contract). Exit code: `0` + model UUID on stdout on success; non-zero with one-line JSON error payload otherwise. The script is a thin shim — domain logic (source detection, GraphQL recipe, conversion procedure) lives in the runbook markdown and is duplicated only as code in the script. Drift detection: a `--verify-against-runbook` mode fetches `/agent-runbook` and asserts the script's source-detection table matches a known sub-section sha256.

### Non-Functional Requirements

Selective: only categories that materially apply to a single-tenant homelab tooling+docs initiative.

#### Pull-Only Ergonomics & UX

- **NFR1: Pull-only ergonomics.** REST + token only; no UI flows, no push notifications, no webhooks. Mirrors Initiative 1's design discipline (Section *"What Makes This Special"* under Initiative 1). The agent decides cadence; the portal only responds.

#### Security

- **NFR2: Credentials-at-rest scope.** `~/.config/3d-portal/agent.password` is mode `600`, owner `ezop`, never copied to any tracked path, never logged, never echoed to tool output. The password never appears in `_bmad-output/` artifacts (gitignored, but the rule applies regardless). Inline-read-only pattern (`$(cat ...)` directly in the `POST /api/auth/login` body, never via `export`) is the documented call shape. Cookie jars (`/tmp/portal-cookies.txt` or similar) carry the JWT post-login and inherit the same don't-leak discipline — out of tracked paths, never echoed.

#### Reliability

- **NFR3: Verification before completion.** "Runbook file exists" ≠ "Runbook works". Initiative 2 is complete only when FR8 smoke-test transcript exists and validates end-to-end. This codifies the project's existing AI-agent-execution-discipline rule (`_bmad-output/project-context.md` § "AI agent execution discipline").
- **NFR7: Deploy verify includes runbook endpoint.** `infra/scripts/deploy.sh` (or its sibling verify script) smoke-tests `GET /agent-runbook` after `alembic upgrade head` and before exit. Verification: `200 OK`, `Content-Type` starts with `text/markdown`, body sha256 of a known fingerprint section matches a checked-in expected value in `infra/.runbook-fingerprint` (single line). Mismatch → stderr warning + non-fatal exit (same model as `verify-symbolication.sh` per NFR-R3 of Initiative 1). The fingerprint is updated whenever the runbook intro paragraph changes — committed as part of the runbook edit, never silently.

#### Documentation & Decision Hygiene

- **NFR4: Decision documentation, not just decision execution.** FR7 (legacy folder triage) produces a written rationale in `docs/migration-reports/` BEFORE the executing action (Alembic migration or README marker). Future agents reading the migration scripts in `apps/api/scripts/` can find "why is this script frozen / retired" from one grep. Sidecar discipline: any irreversible cleanup in this initiative writes its rationale before the cleanup.
- **NFR8: Auto-discovery principle — runbook does NOT duplicate endpoint signatures.** Curated narrative + behavioral context live in the runbook (markdown). Endpoint catalog + request/response schemas + status codes live in OpenAPI (auto-generated from FastAPI route signatures — drift-impossible by construction). A new `@router.post` in `app/modules/sot/admin_router.py` requires **zero** runbook update. A new behavioral side-effect (e.g., a new auto-enqueue trigger, a new validation rule) **does** require a runbook update — and that is the only manual surface. **Verifiable:** the FR8 smoke-test asserts the runbook contains zero occurrences of OpenAPI-only artifacts (path templates with `/api/`, HTTP-method-uppercase preceding such paths, JSON-schema field listings). Grep heuristic encoded in the smoke-test script.

#### Portability & Integration

- **NFR5: Agent-portability (Claude + Codex + future).** The runbook is executable by any LLM agent with shell + REST capability. Tools invoked are CLI (`curl`, `jq`, `python3`, `agent-browser` for browser-only sources) or REST endpoints accessible through any agent's Bash-equivalent. The runbook does NOT name Claude-specific (`Read`, `Edit`, `Grep`, `Glob`) or Codex-specific tools, nor agent-internal abstractions (`mcp__*`). Verifiable: smoke-test transcript shows runbook content only references CLI/REST.
- **NFR6: Idempotence on URL re-import.** Running the runbook against an already-imported URL returns the existing model UUID rather than creating a duplicate row. Detection: pre-flight checklist FR6.4 (duplicate-check via existing `ExternalLink` rows) catches it before `POST /api/admin/models`. If detection fails and a duplicate is created anyway, the operator can `DELETE /api/admin/models/{id}` (soft-delete) without affecting the original.

## Initiative 3 — UI Theme Compliance & Visual Regression Hardening

**Status:** ✅ shipped 2026-05-13 (started 2026-05-13, single-session autonomous execution ~3h elapsed). Maintainer: Ezop. Brownfield remediation of three documented light/dark theme incidents (`c35b5dc` light-theme polish, TB-010 viewer3D HSL parse, AgentsOnboardingDialog 2026-05-13) plus structural hardening of the visual-regression process that failed to catch any of them. Epic 5 is the only epic under this initiative. Source brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-ui-theme-hardening.md` + distillate sibling.

### Document Map

For readers landing cold (especially AI agents in downstream BMAD steps):

| Section | Purpose |
|---|---|
| Executive Summary + What Makes This Special | The pitch and the differentiator (BMAD-formal not multi-QD; tooling-enforced not convention-only) |
| Project Classification | Type / domain / complexity / context — single-row context for downstream steps |
| Success Criteria | User / Operational / Technical / Measurable — all leading indicators, no lagging metrics |
| Product Scope | MVP (Phase A audit + C-early tooling + B remediation + C-prevention gates) / Vision (3–6 month outlook) / Out (explicit non-goals) |
| Functional Requirements | 17 FRs across 4 groups (A Audit / B Tooling-early / C Remediation / D Prevention) — binding capability contract; each FR ties to one Epic 5 story |
| Non-Functional Requirements | 9 NFRs across Build Quality / Operator Workflow / Documentation / Portability — single-operator constraints encoded |

### Executive Summary

3d-portal's frontend has shipped three theme/contrast defects to the production-equivalent dev host in the last four weeks — a Select-popover/Sheet/i18n cluster (`c35b5dc`, 2026-05-12), the viewer3D black-mesh HSL parse incident (TB-010, 2026-05-12), and the AgentsOnboardingDialog light-mode contrast collapse (2026-05-13). The Playwright visual-regression CI (`toHaveScreenshot()` across four projects: desktop/mobile × light/dark) reported green throughout. The reason: the baseline PNGs themselves carry the defects. The 2026-05-13 incident is the headline — `apps/web/src/ui/dialog.tsx:34` and `:56` use hardcoded RGBA literals (`bg-[rgba(0,0,0,0.15)]`, `bg-[rgba(8,12,20,0.5)]`) that bypass the entire `theme.css` token system. Every dialog in the application carries the same defect. The baseline at `apps/web/tests/visual/__snapshots__/agents-info-dialog.spec.ts/agents-dialog-desktop-light.png` was captured **with the bug already in place** — green CI means "matches the corrupted baseline", which is not the contract operators thought they were buying.

Initiative 3 is a BMAD-formal epic (single Epic 5, three sequenced phases), NOT a multi-QD batch. The 2026-05-10 UI-review retrospective documented the routing miss for this exact pattern; the pre-existing-issue threshold (3 incidents within 4 weeks, all same class) is exceeded. Phase A audits the surface (color-literal sweep across `apps/web/src/**`, baseline integrity audit of all ~82 PNGs plus the 14 currently-skipped specs, interactive-surface coverage matrix). Phase C-early lands tooling **before** mass remediation, so violations show up in CI during the fix work: in-repo ESLint `no-restricted-syntax` rule banning color literals (zero-dependency, deterministic), Stylelint with token-file-split (`viewer-tokens.css` carved out to host the legacy-HSL three.js tokens with a per-file `color-function-notation: 'legacy'` override; main `theme.css` keeps modern syntax), `@axe-core/playwright` contrast scan scoped to `runOnly: ['color-contrast']`. Phase B remediates (Dialog/Overlay tokenization, viewer-overlay tokenization, dark-mode override completeness for success/warning/destructive, bulk fix, baseline regen with operator sign-off, open-state spec expansion split per primitive). Phase C-prevention closes the loop: a git pre-commit hook enforces the baseline acceptance gate (parses commit message, requires `baseline-reviewed:` line per changed PNG), `project-context.md` gets two new rules with `rule_count` advancing 134 → 136, the Codex review prompt for UI commits is enriched at a concrete artifact path (`.codex/review-prompts/ui-theme-checks.md`), and axe scan promotes from `warn` to `fail`.

The work is bounded: 11 base UI primitives, 23 `--color-*` tokens, ~82 existing PNG baselines, ~10 currently-uncovered interactive surfaces, two lint integration points (ESLint + Stylelint), one git hook, two new procedural rules. Stakeholder is the single operator. No external customers, no SaaS migration, no design-system redesign, no Storybook adoption (numerical LOC comparison vs the proposed alternative is in the brief; rejection stands).

#### What Makes This Special

Three properties together set this initiative apart from a "fix a bug" effort:

1. **Tooling-enforced, not convention-only.** The 2026-05-10 UI-review retrospective documented that conventions in CLAUDE.md and project-context.md get bypassed under load. Every new rule in Phase C-prevention is paired with a tooling defense (git hook, lint rule, axe scan). The "Baseline Acceptance Gate" is enforced by a pre-commit hook precisely so it cannot be skipped by a future agent who simply does not read the rule.
2. **Layered lint, not single-tool-bet.** Primary enforcement is the in-repo ESLint `no-restricted-syntax` rule (zero external dependency, deterministic, survives the disappearance of any community plugin). The pre-1.0 single-maintainer `@poupe/eslint-plugin-tailwindcss` is wired as an optional enhancement layer at `warn`, not as the critical path. Stylelint covers the CSS file itself (where the three.js HSL-parse incident originated) via a token-file-split that lets a per-file `color-function-notation` override coexist with the intentionally mixed-notation design.
3. **Sequencing puts prevention before remediation.** Phase A → Phase C-early (tooling) → Phase B (remediation, with lint live) → Phase C-prevention (gates + rules + axe promotion). The Phase B fixes are validated by the same gate that will then defend `main` going forward — not a separate gate built after the fact.

**Core insight:** Initiative 3 inherits the brownfield-cleanup discipline that defined Initiative 1 (every replacement keeps its predecessor as documented manual recovery) and Initiative 2 (auto-discovery beats curated catalogs), and adds a third pattern: **automated gates beat documented rules** for any constraint that crosses a multi-week pattern threshold.

### Project Classification

| Field | Value | Rationale |
|---|---|---|
| **Project type** | `tooling+remediation` | Output is a mix of tokenization fixes in `apps/web/src/ui/`, a `viewer-tokens.css` extraction, new lint configuration (ESLint + Stylelint), a `@axe-core/playwright` integration, a git pre-commit hook, ~8 new Playwright specs, ~32 regenerated PNG baselines, two new `project-context.md` rules, and one `.codex/review-prompts/ui-theme-checks.md` artifact. No business-logic code paths added. No backend changes. |
| **Domain** | `general` | Self-hosted homelab catalog. No vertical-specific compliance. Frontend-only initiative. |
| **Complexity** | `low-to-medium` | ~14 stories across three phases, all bounded; surface is well-enumerated (11 primitives, 23 tokens, 82 baselines, 10 coverage gaps). Estimated 2–3 sprint-equivalent units of operator-driven agent execution. |
| **Project context** | `brownfield` | Layered on the 2026-05-12 post-TB-012 baseline where the visual-regression suite passed clean (90 / 0 / 14-skipped). Initiative 1 (GlitchTip delta) and Initiative 2 (Agent runbook) already established the BMAD-formal-not-QD discipline for repeated-pattern fixes; Initiative 3 is the third instance and the first whose pattern was an established repeat at planning time. |

### Success Criteria

#### User Success (the user is the operator + downstream AI agents)

- **Operator QA load drops to spot-check.** Operator stops finding light-mode contrast defects post-deploy. Current rate ~1 per 2–3 weeks. Acceptance: tracked at 30/60/90-day check-ins post Epic-5 close; 90-day zero-incident is the vision target, not a binding criterion.
- **AI agents see clean visual surface in BMAD checkpoints.** Every Codex review / BMAD `bmad-checkpoint-preview` screenshot reflects the actual designed state, not corrupted baselines. Acceptance: FR12 coverage matrix at 100% green at Epic close.

#### Operational Success

- **Lint and Stylelint block bad commits.** `npm run lint --max-warnings=0` fails on any new hardcoded color literal in `apps/web/src/ui/**`. Stylelint fails on hex outside `var(--token)` or wrong HSL notation in either token file. Acceptance: FR4 + FR5; pre-merge gate observable per commit.
- **Baseline acceptance is a git hook, not a convention.** Every commit touching `apps/web/tests/visual/__snapshots__/**` requires a `baseline-reviewed: <basename>, <reviewer>, <YYYY-MM-DD>` line in its commit message. Acceptance: FR13; `git log --grep='baseline-reviewed:'` shows the line on every baseline-touching commit since Epic 5 close, exercised ≥3 times within 30 days post-close.
- **Visual coverage contract is enforced.** Adding a new interactive UI primitive without an open-state Playwright spec covering `{desktop, mobile} × {light, dark}` is rejected by tooling. Acceptance: FR14.

#### Technical Success

- **All 23 `--color-*` tokens are token-only-consumed in `apps/web/src/ui/`.** Zero `bg-[#`, `bg-[rgba(`, `bg-[hsl(`, raw palette utilities (`bg-zinc-N`, `text-white`, `border-red-500`) in those files. Acceptance: FR4 lint rule green at `--max-warnings=0`.
- **`.dark {}` block is override-complete.** Every `--color-*` token defined in the light `@theme {}` has a matching `.dark` override (currently 19 of 23 are overridden; success/warning/destructive plus card-foreground edge-cases will be audited). Acceptance: FR9.
- **`@axe-core/playwright` contrast scan promoted to `fail`.** At Epic 5 close, the scan with `runOnly: ['color-contrast']` returns zero violations on all 4 projects (desktop/mobile × light/dark). Acceptance: FR17 + the last-story-of-epic close gate.

#### Measurable Outcomes

- 0 hardcoded color literals in `apps/web/src/ui/**` at Epic 5 close, verified by lint. State-observable per commit.
- 100% coverage matrix green in `_bmad-output/implementation-artifacts/interactive-surface-coverage-matrix-2026-05-XX.md` at Epic 5 close (every interactive primitive covered open-state × 4 projects).
- `project-context.md` `rule_count` advances 134 → 136. Activity metric — paired with the FR13 first-pass enforcement test.
- 14 currently-skipped specs disposed (skip→unskip or skip→delete decision recorded per spec in the Phase A baseline integrity audit).

### Product Scope

**MVP (FR1–FR17, all 9 NFRs):**
- Three Phase A audit artifacts (color-literal sweep + token-reader inventory; baseline integrity per the 82 PNGs + 14-skip dispositions; interactive-surface coverage matrix).
- Three Phase C-early tooling integrations (in-repo `no-restricted-syntax` ESLint rule + optional `@poupe` plugin; token-file split + Stylelint; `@axe-core/playwright` with scoped `runOnly: ['color-contrast']`).
- Six Phase B remediation deliverables (Dialog/Overlay tokenization + new `--color-overlay` token if needed; viewer-overlay tokenization + new `--color-viewer-tooltip` token; `.dark {}` completeness for success/warning/destructive; bulk fix of remaining offenders; baseline regen with operator sign-off; open-state spec expansion sub-split per primitive).
- Five Phase C-prevention deliverables (git pre-commit hook for baseline sign-off; coverage-contract enforcement; two new `project-context.md` rules; Codex review prompt enrichment at `.codex/review-prompts/ui-theme-checks.md`; axe scan promotion `warn` → `fail`).

**Vision (deferred, out of scope but named for the Epic 5 retro):**
- Move three.js consumers off CSSOM parsing to a build-time generated TS constants file (`viewer-tokens.ts`). Most-robust path against the CSS-parser-mismatch incident class; not in Epic 5.
- Recurring monthly baseline audit codified as a scheduled BMAD chore. Default informal first; promote if pattern proves out at Epic 5 retro.
- Selector-policy lint rule (PL-locale enforcement on `tests/visual/*.spec.ts` `getByRole({name:...})` regexes). Phase A coverage matrix may reveal whether violation count justifies it.
- Storybook adoption — **rejected**, numerical LOC comparison in brief.
- Argos CI / Chromatic / Percy — **rejected**, SaaS friction for solo-operator context.
- Full WCAG 2.2 a11y audit — separate future initiative; axe `runOnly: ['color-contrast']` is the scope here.

### Functional Requirements

#### A. Audit (read-only, Phase A; stories 5.1–5.3)

- **FR1: Static color-literal sweep + token-reader inventory.** Output: `_bmad-output/implementation-artifacts/theme-token-violations-2026-05-XX.md` enumerates every file:line under `apps/web/src/**` where a hardcoded color literal appears (`bg-[rgba(`, `bg-[#`, `bg-[hsl(`, raw palette utilities `bg-zinc-N` / `text-white` / `border-red-500` etc.), severity-ranked. Output: `_bmad-output/implementation-artifacts/token-reader-inventory-2026-05-XX.md` enumerates every reader of `--color-*` tokens via non-browser parsers (`getPropertyValue('--color-*')`, `getComputedStyle(...).getPropertyValue`, three.js Color consumers). The brief's working assumption is `readMeshTokens.ts` + `palette.ts:10` are the only ones; this FR proves or refutes that. (Story 5.1.)
- **FR2: Baseline integrity audit + skip disposition.** Output: `_bmad-output/implementation-artifacts/baseline-integrity-audit-2026-05-XX.md` records per-baseline OK/buggy/uncertain verdict for all ~82 PNGs in `apps/web/tests/visual/__snapshots__/`. Reviewer-fatigue countermeasure encoded in the workflow: ≤20 PNGs per session, ≤2 sessions per day. The 14 currently-skipped specs are individually decided skip→unskip or skip→delete; decision recorded in the same artifact. (Story 5.2.)
- **FR3: Interactive-surface coverage matrix.** Output: `_bmad-output/implementation-artifacts/interactive-surface-coverage-matrix-2026-05-XX.md` is a table — rows = interactive primitives (Dialog, Sheet, Popover, Select, Dropdown, Tooltip, ConfirmDialog, EditTagsSheet, EditDescriptionSheet, RenderSheet, AddPrintSheet, AddNoteSheet, UserMenu, FilterRibbon TagPicker), columns = `{open, closed} × {desktop, mobile} × {light, dark}` — gap cells flagged. Output drives the granularity of FR12's open-state spec expansion. (Story 5.3.)

#### B. Tooling-early (Phase C-early, lands BEFORE remediation; stories 5.10–5.12)

- **FR4: In-repo ESLint `no-restricted-syntax` rule banning color literals.** `apps/web/eslint.config.js` extended with a rule pattern matching `/^(?:bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\[(?:#|rgb|hsl|oklch|color\()/` in JSX `className` literals plus a list of banned raw palette prefixes (`bg-zinc-`, `bg-red-`, `bg-blue-`, ..., `text-white`, `text-black`). Tier `error` for files under `apps/web/src/ui/**`, `warn` elsewhere. **Optional layer:** `@poupe/eslint-plugin-tailwindcss` `prefer-theme-tokens` + `no-arbitrary-value-overuse` at `warn` only — wired as enhancement, not as critical path; if the pre-1.0 single-maintainer plugin goes silent the in-repo rule alone delivers ≥80% of the value. **Verifiable:** `npm run lint --max-warnings=0` fails on a deliberate test commit injecting `bg-[rgba(0,0,0,0.5)]` into `apps/web/src/ui/dialog.tsx`. (Story 5.10.)
- **FR5: Token-file split + Stylelint with per-file overrides.** `apps/web/src/styles/viewer-tokens.css` is created by moving the 4 `--color-viewer-*` declarations out of `theme.css` (along with the 7-line three.js-parse-constraint comment block); `theme.css` imports it. `apps/web/.stylelintrc` (or equivalent flat config) wires `stylelint` + `color-no-hex` + `stylelint-color-no-non-variables` + per-file overrides: `viewer-tokens.css` pins `color-function-notation: 'legacy'`; `theme.css` pins `color-function-notation: 'modern'` (or leaves unset). `npm run lint` script chained: `eslint . --max-warnings=0 && stylelint "apps/web/src/styles/*.css"`. **Verifiable:** the lint chain rejects a test commit injecting `color: #aabbcc` into either CSS file. (Story 5.11.)
- **FR6: `@axe-core/playwright` contrast scan integrated.** `apps/web/tests/visual/playwright.config.ts` (or a sibling `accessibility-axe.spec.ts`) runs an axe scan with `runOnly: ['color-contrast']` once per project (desktop-light, desktop-dark, mobile-light, mobile-dark). Initial level `warn` — does not block iteration during remediation. Per-test `disableRules('color-contrast')` escape hatch documented for known-noisy nodes (overlapping z-index, disabled controls). Promoted to `fail` by FR17 at Epic 5 close. **Verifiable:** scan runs as part of `npm run test:visual`; current state at Phase B start is the violation baseline. (Story 5.12.)

#### C. Remediation (Phase B, with Phase C-early gates live; stories 5.4–5.9)

- **FR7: Dialog/Overlay tokenization.** `apps/web/src/ui/dialog.tsx` lines 34 (`DialogOverlay`) and 56 (`DialogContent`) replace hardcoded RGBA with token-based classes. `apps/web/src/ui/sheet.tsx:29` (`SheetOverlay`) gets the same treatment (mirror of dialog defect; `SheetContent` was already fixed at `c35b5dc`). If `bg-background/N` opacity modifiers cannot deliver the visual intent in light mode, a new `--color-overlay` / `--color-overlay-foreground` token pair is added to `theme.css` + matching `.dark` override (decision deferred to architecture extension). **Verifiable:** the lint rule from FR4 reports zero violations on `dialog.tsx` + `sheet.tsx` post-change. (Story 5.4.)
- **FR8: Viewer-overlay tokenization.** `apps/web/src/modules/catalog/components/viewer3d/measure/RimOverlay.tsx:8` and `MeasureOverlay.tsx:16` replace `bg-zinc-900/95 text-white ring-white/15` raw palette literals with token-based classes. Likely requires a new `--color-viewer-tooltip` token (legacy-HSL form, lives in `viewer-tokens.css` per FR5). **Verifiable:** lint rule from FR4 reports zero violations on those files post-change. (Story 5.5.)
- **FR9: Dark-mode override completeness.** The `.dark {}` block in `theme.css` adds overrides for `--color-success`, `--color-warning`, `--color-destructive` (currently inheriting their light values), and the audit (FR2) confirms the rest of the 23 tokens are intentionally or correctly overridden. **Verifiable:** every `--color-*` declared in `@theme {}` has a matching declaration in `.dark` OR is annotated with a comment explaining the deliberate inheritance. (Story 5.6.)
- **FR10: Bulk fix of remaining Phase A offenders.** Files outside `apps/web/src/ui/` and `apps/web/src/modules/catalog/components/viewer3d/measure/` flagged by FR1 are batched and tokenized. Scope budget: only files where the lint rule from FR4 reports violations at `warn` level on `main` post Phase C-early. **Verifiable:** lint at `--max-warnings=0` passes across the entire frontend after the batch lands. (Story 5.7.)
- **FR11: Baseline regeneration with operator sign-off.** Every baseline PNG affected by FR7–FR10 is regenerated via `npx playwright test --update-snapshots --grep <spec>`. Each commit touching `apps/web/tests/visual/__snapshots__/**` must include a `baseline-reviewed: <basename>, <reviewer>, <YYYY-MM-DD>` line for each changed PNG. Enforcement is the git hook from FR13 — convention alone is rejected. **Verifiable:** `git log --grep='baseline-reviewed:'` shows the line on every baseline-touching commit. (Story 5.8, depends on FR13 hook landing before runs.)
- **FR12: Open-state visual spec expansion.** New Playwright specs cover the gap surfaces from the FR3 matrix. **Sub-split per primitive** to keep effort bounded: (a) Select dropdowns, (b) ConfirmDialog + EditTagsSheet + EditDescriptionSheet bundle, (c) Tooltip + UserMenu, (d) remaining gaps (RenderSheet, AddPrintSheet, AddNoteSheet, FilterRibbon TagPicker). Each new spec runs across all 4 projects; each captured baseline PNG goes through the FR11 sign-off gate. **Verifiable:** the FR3 coverage matrix re-runs at 100% green after FR12 lands. (Story 5.9, sub-split 5.9a–d.)

#### D. Prevention (Phase C-prevention, closes Epic; stories 5.13a, 5.13b, 5.13, 5.14, 5.15)

- **FR13: Baseline Acceptance Gate via git pre-commit hook.** New file `apps/web/.husky/pre-commit` (or equivalent shell hook outside husky if husky is rejected in architecture). When a commit touches `apps/web/tests/visual/__snapshots__/**`, the hook parses the commit message (`git diff --cached --name-only` collects changed PNG basenames; commit message is read from the in-flight commit-msg file) and requires one `baseline-reviewed: <basename>, <reviewer>, <YYYY-MM-DD>` line per changed PNG. Rejects the commit otherwise. **First-pass enforcement test:** within 30 days post Epic 5 close, the rule has been exercised on at least 3 commits — observable via `git log --grep='baseline-reviewed:'`. **Verifiable:** a test commit touching one snapshot PNG without the line is rejected with exit code non-zero. (Story 5.13a.)
- **FR14: Visual Coverage Contract enforcement.** Extension of the FR13 hook (or a sibling check) — when a new `apps/web/src/ui/*.tsx` file appears in a commit and no matching `apps/web/tests/visual/*.spec.ts` is present in the same commit, the hook rejects. Mechanism choice (extend FR13 hook vs add an ESLint custom rule on a similar condition) deferred to architecture extension. **Verifiable:** a test commit adding `apps/web/src/ui/new-primitive.tsx` without a matching spec is rejected. (Story 5.13b.)
- **FR15: `project-context.md` rule additions.** Two new rules: "Baseline Acceptance Gate" (cites the FR13 hook script path and the `baseline-reviewed:` format) and "Visual Coverage Contract" (cites the FR14 enforcement mechanism). Frontmatter `rule_count` advances 134 → 136. Activity metric — paired with FR13's first-pass enforcement test which is the actual outcome metric. (Story 5.13.)
- **FR16: Codex review prompt enrichment for UI commits.** New artifact at `.codex/review-prompts/ui-theme-checks.md` (path TBD-by-architecture) — a concrete prompt fragment that instructs Codex to check for: (a) color literals in `apps/web/src/ui/**`, (b) `.dark {}` override completeness for any new `--color-*` token, (c) open-state visual spec coverage for any new `apps/web/src/ui/*.tsx`, (d) selector locale-awareness in any new `tests/visual/*.spec.ts`. Invocation: a wrapper script detects UI commits via `git diff --name-only HEAD~1` matching `apps/web/src/(ui|styles)/.*` or `apps/web/tests/visual/.*`, and runs `cat .codex/review-prompts/ui-theme-checks.md prompt-tail.md | codex exec -` for those; bare `codex review --commit <SHA>` is retained for non-UI commits. **Acceptance criterion:** replaying the enriched prompt against historical commit `10bc3de` (the TB-010 partial commit that baked the black-mesh + overlap bugs into 14 baselines) surfaces at least one of those two defects. (Story 5.14.)
- **FR17: Axe contrast scan promotion to `fail` level.** Closing story of Epic 5. Pre-promotion: the scan from FR6 returns zero violations on all 4 projects with `runOnly: ['color-contrast']`. The `warn` level is changed to `fail` in the visual-regression config; `npm run test:visual` now blocks on contrast violations. **Verifiable:** the test suite reports zero contrast violations at promotion time; a deliberate test commit injecting low-contrast text fails the suite post-promotion. **This is the gate between Epic 5 and "feature work resumes".** (Story 5.15.)

### Non-Functional Requirements

Selective: only categories that materially apply to a single-operator frontend remediation+prevention initiative.

#### Build Quality

- **NFR1: Lint-green build is the merge contract.** `npm run lint --max-warnings=0` passes on every commit reaching `main`. ESLint (with the FR4 rule) and Stylelint (FR5) are chained in the same `lint` npm script — both must pass. Failures block the auto-deploy contract (`feedback_auto_deploy_dev.md`) by failing CI / failing the local pre-commit hook chain.
- **NFR2: Stylelint scoped per-file overrides, not file-wide pins.** The `theme.css` ↔ `viewer-tokens.css` HSL-notation split is intentional and load-bearing for three.js consumers. The Stylelint config encodes this via per-file overrides only; no file-wide `color-function-notation` pin in the root config. Mixing two notations in the same file remains forbidden — that is the failure mode the split exists to prevent.

#### Operator Workflow

- **NFR3: Convention-only enforcement is explicitly rejected.** Every Phase C-prevention rule is paired with a tooling defense (git hook for FR13/FR14, lint rules for FR4/FR5, axe scan for FR6/FR17, Codex prompt enrichment for FR16). The 2026-05-10 UI-review retro documented that rules in CLAUDE.md and project-context.md get bypassed when not enforced by tooling; Initiative 3 commits to the inverse principle.
- **NFR4: Operator eye-review time budget acknowledged in workflow.** Phase A FR2 baseline audit (~82 PNGs) + Phase B FR11 regen sign-offs + Phase B FR12 new baselines (~32 PNGs) ≈ ~114 PNG sign-offs across Epic 5 ≈ ~2 hours of focused click-through distributed over the epic. Fatigue countermeasure encoded in FR2: ≤20 PNGs per session, ≤2 sessions per day. Sampling fallback (100% for first 4 weeks of Phase B, 25% thereafter once lint+Stylelint gates are live) is the contingency if PNG count balloons past 50; decision recorded at the Epic 5 mid-point check-in.
- **NFR5: No SaaS adoption.** No Chromatic, Percy, Argos CI. No external visual-regression service. Initiative 3 stays inside the repo + local Playwright + git hook + operator sign-off. Rationale: solo-operator context, no reviewer pool to amortize SaaS pricing/process across.
- **NFR6: No Storybook adoption.** Numerical LOC comparison in the brief: Storybook 8 + Tailwind v4 integration is non-trivial today, would add ~330 LOC of catalogue boilerplate (11 primitives × ~30 LOC stories) for zero living-catalogue consumer benefit in single-operator context. Epic 5's FR12 open-state spec expansion (~200 LOC of specs + 32 baselines) is roughly equivalent in maintenance surface but delivers per-commit contrast/light-dark verification rather than a UI catalogue.

#### Documentation & Conventions

- **NFR7: English in committed file content.** All code, configs, commit messages, project-context.md rules, and `.codex/review-prompts/ui-theme-checks.md` content are English. Polish stays conversational between Ezop and the agent.
- **NFR8: `_bmad-output/` stays gitignored.** Brief, distillate, PRD-extension (this section), architecture-extension-to-be, epics-extension-to-be, all story files, all retros — operator-local. Memory + `MEMORY.md` are the persistent surface across sessions. Initiative 3 inherits this from Initiatives 1 + 2 without deviation.

#### Portability

- **NFR9: Single-operator workflow constraint is design-constraining.** Gate mechanisms (git hooks, lint, axe) are observable on the operator's local machine via `git status` / `npm run lint` / `npm run test:visual` — no remote CI dependency. The Codex review prompt enrichment (FR16) is invoked from the operator's local shell via `codex exec`. Initiative 3 does not introduce any tooling that requires a reviewer pool, a CI runner, or an external service.

## Initiative 5 — Public Registration & User Account Management

**Status:** 🚧 planning (started 2026-05-18; brief v2 + Sprint Change Proposal approved). Maintainer: Ezop. Source brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (v2, 213 lines, adversarial review applied: P0×2 + P1×3 + P2×1 fixed) + distillate sibling. Source CC proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Sequenced into five epics: **E6** (Member role + invite-based registration), **E7** (TOTP 2FA + recovery codes), **E8** (Admin panel: users + invites), **E9** (Security audit — HARD GATE blocking E10), **E10** (Edge cutover — atomic).

**Brief working-label mapping.** The brief uses dotted notation `5.1`–`5.5` as working labels. These map 1:1 onto project-global epic IDs: brief `5.1` → E6, `5.2` → E7, `5.3` → E8, `5.4` → E9, `5.5` → E10. Story IDs follow the project-global convention `<epic-id>.<local-story-num>` (per CC §3.4 vanilla-alignment correction, AGENTS.md v2 2026-05-18). The dotted brief labels are PRD-time historical artifacts; downstream `epics.md` and `sprint-status.yaml` use the global IDs exclusively.

**Initiative 0 + Initiative 2 are unchanged.** Initiative 5 is purely additive: the existing cookie+JWT auth stack stays, the existing share-token Redis pattern stays as the template for invite tokens, the existing audit-log surface gains 16 new actions but no contract changes, and the `agent` service account is preserved exactly (no 2FA forced, ever).

### Document Map

For readers landing cold (especially AI agents in downstream BMAD steps):

| Section | Purpose |
|---|---|
| Executive Summary + What Makes This Special | The pitch and the differentiator (additive-on-thick-baseline; audit-before-cutover hard-gate; member-is-one-bit-of-permission) |
| Project Classification | Type / domain / complexity / context — single-row context for downstream steps |
| Success Criteria | Six leading-indicator SCs verbatim from brief v2 — operator-side friction reduction, not engagement metrics |
| Product Scope | MVP (FR5-* + NFR5-*) / Vision (post-cutover trajectory) / Out (explicit non-goals from brief Q5) |
| Functional Requirements | 24 FRs across 8 area groupings (INVITE / REGISTER / MEMBER / 2FA / ADMIN / AUDIT / RATELIMIT / CUTOVER) — binding capability contract; each FR ties to one of the five epics |
| Non-Functional Requirements | 12 NFRs across 6 categories (SEC / PERF / AUDIT / CROSS-REPO / INT / OBS) — audit-gate condition, integration invariants with Init 0/2, cross-repo coordination |
| Cross-references | Brief v2 + distillate + Init 0 baseline anchors + forward refs to architecture.md / epics.md / sprint-status.yaml |

### Executive Summary

3d-portal today admits exactly two principals: `admin` (Michał) and `agent` (the AI service account). All household browse access is gated at the nginx edge via IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`, covering homelab LAN + VPN); there is no path for a non-household friend or family member to obtain a per-person login. The portal already ships with a `member` role in the User enum (`apps/api/app/core/db/models/_enums.py`), a complete cookie+JWT auth stack (`portal_access` 10min + `portal_refresh` 30d with family rotation, CSRF via `X-Portal-Client: web`), an audit log with first-class auth-event taxonomy, and a Redis-backed share-token implementation that is the perfect template for invite tokens — but no registration path for anyone who is not Michał.

Initiative 5 closes that gap in five sequenced epics. **E6 (member + invite-based registration)** wires the core flow: admin generates a single-use invite link with operator-chosen TTL and pre-bound role, recipient lands on `/register?token=<token>` and supplies email + password, and the resulting `member` account gains catalog browse + 3D viewer + share-link generation. **E7 (TOTP 2FA + recovery codes)** adds optional second-factor authentication with eight single-use recovery codes; enforcement is per-role via a config flag with the `agent` role explicitly excluded from any enforcement list. **E8 (admin panel)** ships two tabs in the existing admin UI for user and invite lifecycle operations, so routine operator actions no longer require DB poking. **E9 (security audit)** is a hard gate before E10 — formal pre-cutover audit with `bandit` + `semgrep` + `pip-audit` + OWASP ZAP + `codex review`; gate condition is zero open Critical/High findings and at most three "accepted-with-rationale" Mediums (the fourth forces auto-fail). **E10 (edge cutover)** is an atomic single-commit edit in the sibling nginx config repo that drops both `auth_basic` and the IP allowlist, leaving nginx as a thin TLS terminator + share-bypass rewrite while the portal authenticates itself.

The work is bounded. The cutover is the smallest change in the initiative — drop two nginx directives. The bulk of the effort is the audit that lets the portal trust the cutover, not the cutover itself. Estimated diff: ~3-4 Alembic migrations, ~6 new modules in `apps/api/app/modules/`, ~4 new React routes, 16 new audit-log actions, one sibling-repo nginx config edit. First-wave audience is friends-and-family (~10-20 people realistically in the first 90 days); the portal remains gated — invite-only registration replaces IP allowlist as the gate, it does not remove the gate.

#### What Makes This Special

Three properties together set this initiative apart from a "rip out auth_basic" effort:

1. **Building on a thick existing baseline, not greenfield.** Cookie+JWT auth, family-based refresh rotation with reuse detection, CSRF middleware, AuditLog with `record_event()` helper, share-token Redis pattern, password hashing, role enum (with `member` already enumerated) all ship today. Initiative 5 is mostly additive — new tables and columns, new pages, new audit actions, one config edit. The Initiative 0 foundation makes most of the cost vanish.
2. **The audit is an epic, not a story tacked onto the cutover.** Multi-PR security batches from review docs are epics in disguise (per `feedback_default_to_bmad_workflow.md`). E9 is one epic with a hard-gate exit criterion (zero Critical/High; ≤3 accepted Mediums; 4th forces fix sprint) and explicit second-opinion artifact requirements (`codex review --commit <SHA>` for every Medium disposition). This sequencing — pay the audit cost before the LAN whitelist drops, not after — is the operator's banking-IT instinct encoded as a planning structure.
3. **Member's permission expansion is one bit.** `member` gains `/api/share/*` POST capability. That is the only permission member gets above today's anonymous-LAN-browser. No per-model ACL, no team accounts, no messaging, no comments. The simplicity is the moat — but member-amplified share-link distribution is a recognized asymmetric risk (FR5-MEMBER-3 per-member rate-limit + daily cap, mitigated in E9 audit scope).

**Core insight:** Initiative 5 inherits the brownfield-cleanup discipline of Initiatives 1/2/3 and adds a fourth pattern specific to security work: **hard-gate sequencing beats "yolo cutover" overrides**. The audit gate has no bypass flag. If E9 finds an unfixable Critical, E10 is parked and the issue triages to a fix sprint before the cutover runs.

### Project Classification

| Field | Value | Rationale |
|---|---|---|
| **Project type** | `web_app` (multi-part monorepo; security delta) | Output spans new backend modules (~6 in `apps/api/app/modules/`), new frontend routes (~4 in `apps/web/src/`), DB migrations (~3-4 Alembic), one sibling-repo nginx config edit, 16 new audit-log actions. No worker changes, no render-pipeline changes. |
| **Domain** | `general` (homelab + friends-and-family) | Self-hosted catalog with a curated first-wave audience. No HIPAA/PCI/GDPR-scale compliance — but the cutover from network-perimeter trust to portal-self-auth raises the security bar materially. |
| **Complexity** | `medium` | Five sequenced epics (~25-35 stories total, exact count at sprint-planning time), security audit hard-gate, cross-repo cutover, 2FA enrollment + recovery codes drill, rate-limit middleware. Above the `low` of Init 1/2/3 single-epic deltas; below Init 0's foundation. |
| **Project context** | `brownfield` | Built on the Init 0 foundation (auth, share-token Redis pattern, audit-log) + Init 1 observability + Init 2 agent flow. The `member` role is already enumerated; the cookie+JWT + family-rotation stack is already production-tested. Initiative 5 is the path from "two principals" to "an invite-gated friend circle". |

### Success Criteria

Verbatim from brief v2 §"Success Criteria". Leading-indicator-first, observable from the admin panel itself per Q3 framing. Success is operator-side reduction-of-friction, not external engagement metrics.

1. **First-wave activation:** within 30 days of cutover (E10 close), at least 5 invites generated, at least 3 invites consumed, at least 2 distinct member users with non-null `last_active_at` updated in the last 7 days. (Floor, not stretch.)
2. **Admin panel handles routine ops without DB poking.** All four core admin actions (generate invite, revoke invite, change user role, reset user password) are exercised through the panel UI at least once in the first 30 days; zero panel-triggered operations require SQL inspection to complete.
3. **Zero account-takeover incidents in the first 90 days.** No `auth.refresh.reuse_detected` events for non-attacking causes (UA churn excluded via the existing 30s grace); no `auth.login.fail` patterns matching credential-stuffing (≥10 failures from one IP across ≥3 emails within 5 minutes).
4. **E9 audit produces a clean cutover artifact.** Pre-cutover audit report at `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md` shows zero open Critical/High findings at the moment of E10 deployment. Every Medium has a documented disposition (fixed / mitigated / accepted-with-rationale).
5. **2FA enrollment + recovery-code path is drill-verified against `.190`.** E7 ships with a documented end-to-end recovery-code drill artifact at `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-MM-DD.md`, executed against the deployed `.190` instance (NOT against CI fixtures). The drill steps: enroll a test user → log out → log in with TOTP → consume a recovery code in place of TOTP → regenerate recovery codes → disable TOTP → verify normal login still works. Artifact captures timestamps, request IDs, and AuditLog row deltas. First-wave adoption by real members is intentionally NOT an SC ("path works, not adoption").
6. **Rate-limit holds the line on `/api/auth/login`.** Post-cutover, the endpoint rejects ≥5 rapid failures from one IP within 60 seconds with HTTP 429. Verified by `siege`/`hey` benchmark in the audit, reproducible on demand.

### Product Scope

#### MVP (FR5-* + NFR5-*) — In scope, verbatim from brief v2

- New `invite_tokens` DB table + Redis-fronted storage + admin endpoints + UI for generate/list/revoke.
- New `/register?token=<token>` public route + form (email, password with zxcvbn ≥3 ≥12-char check, token validation).
- New `member` role permission scope: catalog browse, viewer, share-link generate. Member-blocked: `admin/*`, agent-runbook, audit log read.
- Extension of `current_admin` dependency family with a `current_member_or_admin` variant for shared resources; share-router auth expanded from `admin`-only to `{admin, member}`.
- 2FA columns on `users` table (`totp_secret`, `totp_enabled_at`); recovery-codes table; 2FA enrollment route + UI (QR + manual secret); `enforce_2fa_for_roles` config flag.
- Admin panel: Users tab + Invites tab; React routes under `apps/web/src/modules/admin/`.
- `is_active: bool` soft-delete column on `users` + `last_active_at: datetime` column (throttled write ≤1/5min).
- Rate-limit middleware on `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`. Tunable thresholds in config. Redis-backed sliding-window (architecture decision finalized at architecture.md).
- Security audit tooling: bandit, semgrep, pip-audit, npm/osv-scanner, OWASP ZAP, codex review. Outputs as artifacts in `_bmad-output/implementation-artifacts/`.
- Nginx edge cutover: edit `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (sibling repo) — drop `auth_basic` + IP allowlist; preserve share bypass + agent-runbook bypass. Atomic single commit + reload.
- 16 new audit-log actions emitted via `record_event()` (enumerated in FR5-AUDIT-1); 1+ new entity_types added to `KNOWN_ENTITY_TYPES` (Story 6.1 adds `invite_token`; E7 may add `recovery_code`).

#### Vision (post-E10 trajectory, named for retro)

- **+30 days post-cutover:** first-wave (~5-10 people) onboarded. Admin panel is operator's daily-driver for user ops. Nginx is a thin TLS + proxy + share-bypass layer.
- **+90 days:** per Q3 framing — first-wave members either engage (login signal + ad-hoc print requests via Messenger as a placeholder channel) or they don't (also acceptable; operator-side win still holds). 2FA path proven through ≥1 enrollment OR ≥1 force-enroll OR ≥1 recovery-code drill.
- **+6 months / Initiative 6 candidate:** `member-print-requests` unblocked — every print request becomes `request.user_id` rather than "Michał remembers which Messenger thread this came from". Per-user prints log becomes feasible. Per-user favorites tag becomes feasible.
- **+12 months (vision, not commitment):** self-hosted mail server arrives → self-service password reset → email deliverability checks → possibly widening the first-wave from friends-and-family to a moderated hobby-print community. Each step is its own initiative; Initiative 5 deliberately stops at the friends-and-family threshold.

#### Out (explicit non-goals — confirmed at brief elicitation Q5)

- Social login (Google/GitHub/etc.) — native accounts only.
- OIDC/SSO federation (Authentik in homelab) — `member-print-requests` initiative may revisit.
- Per-model ACL (member X sees subset of catalog) — all-or-nothing access for `member` role.
- Team/group accounts.
- User-to-user messaging.
- Public read-only browse mode — portal stays gated by login; `/share/*` is the only escape hatch.
- Self-service password reset via email — blocked on self-hosted mail server (separate future initiative).
- Email deliverability verification — RFC format validation only.
- Webhook/event push to external systems on auth events.
- Multi-tenant. (One household, one SoT, one admin, multiple members.)

### Functional Requirements

24 FRs across 8 area-prefix groupings. Each FR is a capability statement with a verifiable acceptance check. Implementation details (DB column shapes, middleware internals, route paths under `/api/auth/*`) are architecture.md's domain.

#### A. Invite token lifecycle (FR5-INVITE-*; admin-side, drives E6)

- **FR5-INVITE-1: Admin can generate single-use invite tokens.** TTL presets `1d / 3d / 7d / 30d` plus a custom-TTL input; pre-bound role default `member`; entropy 256 bits via `secrets.token_urlsafe(32)`. Storage is dual-backed: Redis at `invite:token:{token}` (active state + TTL + revoke) and a row in the new `invite_tokens` table (audit history outliving the Redis TTL). Audit event: `auth.invite.generated`. **Verifiable:** an admin-generated token has 32-byte entropy; the matching DB row exists with `generated_by`, `generated_at`, `role`, `ttl_seconds` populated.
- **FR5-INVITE-2: Admin can list active and historical invites.** The Invites tab in the admin panel filters by status (`active` / `used` / `expired` / `revoked`) and exposes per-row metadata: `generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`. **Verifiable:** filter applied; the row count and per-row metadata match the DB state.
- **FR5-INVITE-3: Admin can revoke an active (unused) invite token.** Revocation is immediate (Redis key deletion + DB row update with `revoked_at`). Audit event: `auth.invite.revoked`. A revoked-but-still-shown-in-the-list token MUST NOT be consumable. **Verifiable:** a `POST /api/admin/invites/{id}/revoke` followed by `GET /register?token=<that-token>` returns HTTP 410 Gone.
- **FR5-INVITE-4: A used invite token is single-use; replay attempts fail closed.** Consumption deletes the Redis key and updates the DB row with `used_by` + `used_at` + `used_from_ip`. A second consumption attempt — regardless of source IP — returns HTTP 410 Gone, emits `auth.register.fail` with reason `token_consumed`, and never creates a duplicate user. **Verifiable:** scripted double-consume against the same token; first registers, second is rejected with 410.

#### B. Public registration flow (FR5-REGISTER-*; drives E6)

- **FR5-REGISTER-1: Public `/register?token=<token>` route accepts a valid unused invite token.** Token validation: Redis lookup; on miss → HTTP 404 + audit event `auth.register.fail` with reason `token_invalid`. The route is the only public-write surface introduced by Initiative 5 — every other write requires authentication. **Verifiable:** a request with a tampered/unknown token returns 404 + the audit row is present.
- **FR5-REGISTER-2: Registration form captures email + password and enforces strength.** Email format is validated to RFC syntax only — no deliverability verification, no DNS/MX check (per Out-of-scope). Password requires zxcvbn score ≥3 AND length ≥12 characters; failure returns HTTP 422 with the failing rule cited in the response body. **Verifiable:** a deliberate weak password (`password123!`) is rejected with 422 and the response body identifies the failing strength check.
- **FR5-REGISTER-3: Successful registration creates a user account with the invite-bound role and issues the standard cookie pair.** The role on the created user matches the invite's pre-bound role (default `member`). The invite is marked consumed (FR5-INVITE-4 semantics). The response sets `portal_access` (10min) + `portal_refresh` (30d) cookies — the same auth surface as `/api/auth/login`. Audit event: `auth.register.success`. **Verifiable:** post-registration, `curl --cookie ...` against `/api/catalog/*` returns 200 without an extra login step.

#### C. Member permission scope (FR5-MEMBER-*; drives E6)

- **FR5-MEMBER-1: `member` role is the third principal that browses authenticated catalog content; share-router minting expands from admin-only to member-or-admin.** Catalog browse (`/api/catalog/*`, `/api/sot/*` GET) is available to any authenticated principal (admin, member, agent) per architecture.md § Initiative 5 Decision C per-route allowlist table — **`member` is an addition to the eligible set, not a new minimum**. The share-router minting endpoint (`POST /api/admin/share`) expands its dependency from `current_admin` to `current_member_or_admin` (FR5-MEMBER-2 codifies the new dependency name). **Verifiable:** a member-authenticated `POST /api/admin/share` returns 201 with a fresh share token; the same request as an unauthenticated user returns 401; an agent-authenticated `GET /api/categories` returns 200 (NFR5-INT-1 preserved). <!-- Initiative 6 clarification 2026-05-20: original wording "`member` role grants browse" was ambiguous and read as member-minimum; the architecture intent (Decision C table) was always "any authenticated user". Implementation drift in sot/router.py shipping `Public, unauthenticated` was masked by nginx allowlist pre-cutover (see Initiative 6 retro). -->

- **FR5-MEMBER-2: `member` role is denied all admin and audit surfaces.** Denied: any `/api/admin/*` route, `/api/audit/*` read endpoints, `/agent-runbook` operations requiring admin scope. Permission check: the existing `current_admin` dependency stays admin-only. A new `current_member_or_admin` dependency is introduced and applied to the share-router only. **Verifiable:** a member-authenticated `GET /api/admin/users` returns 403.
- **FR5-MEMBER-3: Member-generated share tokens are subject to per-member rate-limit and daily volume cap.** Architectural floor: ≤20 share-tokens per member per day; soft-fail alert (log-and-continue) at 50% of the threshold; hard-fail (HTTP 429) at 100%. Mitigation against the compromised-member share-link amplification surface (brief working assumption §"Member share-link generation is a deliberate amplification surface"). The cap is configurable in `apps/api/app/core/config.py`. **Verifiable:** a scripted 21-share-creation burst from one member account succeeds 20 times and is rejected on the 21st with HTTP 429.

#### D. TOTP 2FA + recovery codes (FR5-2FA-*; drives E7)

- **FR5-2FA-1: User can enroll TOTP 2FA with mandatory recovery codes generated at enrollment.** Enrollment route at `/settings/2fa` displays a QR code (via `pyotp`) and a manual secret fallback. On confirmation, the secret persists in `users.totp_secret` (encrypted at rest), the enrollment timestamp in `users.totp_enabled_at`. At the same step, 8 single-use recovery codes are generated, displayed once (download-as-txt + clipboard-copy options), and stored hashed in a new `recovery_codes` table. The user CANNOT re-display the cleartext codes after enrollment. Audit event: `auth.totp.enrolled`. **Verifiable:** post-enrollment, the QR scanned into Google Authenticator / 1Password produces 6-digit codes that match the TOTP verify endpoint; refreshing the enrollment page does NOT re-show the cleartext codes.
- **FR5-2FA-2: Login flow extends with a second-factor step for users with TOTP enabled.** For users where `totp_enabled_at IS NOT NULL`, `POST /api/auth/login` with valid email + password returns a partial-auth state (no `portal_access` cookie yet) and the frontend prompts for the second factor. The second step accepts either the current 6-digit TOTP code OR a recovery code. Recovery code consumption is one-way (`used_at` set, row stays for audit) and emits `auth.recovery_code.used`. Wrong second factor returns HTTP 401 with `auth.totp.verify.fail`; correct second factor returns HTTP 200 + `portal_access` cookie set, audit event `auth.totp.verify.success`. **Verifiable:** scripted login with correct password and wrong TOTP returns 401; with correct TOTP returns 200 + cookies set.
- **FR5-2FA-3: 2FA enforcement is per-role via a config flag with the `agent` role explicitly excluded.** The flag `enforce_2fa_for_roles: list[Role]` lives in `apps/api/app/core/config.py` (default `[]`). At app startup, the value MUST be validated: if `Role.agent` is in the list, the app refuses to boot with a clear error (`"agent role MUST NEVER appear in enforce_2fa_for_roles"`). Admin can additionally force-enroll any individual user via the admin panel (FR5-ADMIN-2 `force-2FA-enrollment` action) — per-user override that does not depend on the role flag. **Verifiable:** a deliberate config containing `[Role.agent]` causes the app to fail-fast on startup.
- **FR5-2FA-4: User can regenerate recovery codes and disable TOTP from `/settings/2fa`.** Regenerating recovery codes invalidates all previous unconsumed codes (`recovery_codes.invalidated_at` set on the prior batch) and shows the new batch once. Disabling TOTP clears `totp_enabled_at` to `NULL`, invalidates all unused recovery codes, and emits `auth.totp.disabled`. Both actions require re-authentication (current password + current TOTP) before they take effect. **Verifiable:** post-disable, login succeeds without a second-factor step and the AuditLog shows `auth.totp.disabled` with `actor == target`.

#### E. Admin panel — users + invites (FR5-ADMIN-*; drives E8)

- **FR5-ADMIN-1: Admin panel has two new tabs: `/admin/users` and `/admin/invites`.** The Users tab lists users with columns: `email`, `role`, `created_at`, `last_active_at`, `totp_enabled` flag, `is_active`. The Invites tab lists invites per FR5-INVITE-2. Both tabs paginate at the existing admin-list default. **Verifiable:** at least one row per tab is rendered when seeded test data exists; column values match the DB state.
- **FR5-ADMIN-2: Per-user actions are available from the Users tab and emit matching audit events.** Actions: `change role` (audit `user.role_changed`), `force 2FA enrollment` (audit `auth.totp.enrolled` with `actor != target` flag), `issue password reset link` (FR5-ADMIN-3), `deactivate (is_active=False)` (audit `user.deactivated`), `force logout-all-sessions` (audit `user.force_logout`; backend invalidates all refresh-token families for the target user). Reactivating a deactivated user emits `user.reactivated`. **Verifiable:** each action triggered from the panel produces the documented audit row with the correct `actor_user_id` / `target_user_id` pair.
- **FR5-ADMIN-3: Admin-issued password reset link is functionally an invite token; delivery is out-of-band.** Shape: single-use, short TTL (default 1 hour, configurable), Redis-fronted at `invite:reset:{token}`. The endpoint emits `auth.password.reset.initiated`; consumption (via a public `/reset-password?token=<token>` route mirroring the registration form's password-strength gates) emits `auth.password.reset.completed`. Delivery is out-of-band by the operator (same channel as the original invite — SMS / Messenger / personal mail) until self-hosted mail server arrives (Out-of-scope here). The same workflow covers the lost-2FA-AND-lost-recovery-codes lockout path: operator force-disables 2FA on the user's account (audit `auth.totp.disabled` with `actor != target`), then issues a reset link. **Verifiable:** scripted issue → out-of-band delivery → consumption flow completes; both audit events present.
- **FR5-ADMIN-4: Bulk user operations are deliberately NOT in the v1 panel UI.** The panel ships single-user actions only (FR5-ADMIN-2). If more than one user needs disabling or role-changing at once (e.g., a friend-group falls out of trust), the operator uses a DB-direct script. Deferred to a future admin-panel-v2 if the pattern recurs. Documenting the deliberate exclusion prevents future agents from inferring missing CRUD scope as a bug. **Verifiable:** the panel UI exposes no "select all" or "bulk action" controls; the architectural decision is recorded in architecture.md.

#### F. Audit-log taxonomy (FR5-AUDIT-*; cross-cutting, drives E6/E7/E8)

- **FR5-AUDIT-1: 16 new audit-log actions are emitted via the existing `record_event()` helper.** Actions (passed as `action=` kwarg — free-form strings, NOT registry entries): `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`, `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`, `auth.password.reset.initiated`, `auth.password.reset.completed`, `user.deactivated`, `user.reactivated`, `user.role_changed`, `user.force_logout`. New entity_types added to `KNOWN_ENTITY_TYPES` (the entity-type registry at `apps/api/app/core/audit.py:28-44`): `invite_token` (Story 6.1, shipped); E7 may add `recovery_code` or reuse the existing `user` entity_type (Story 7.1 decision). Each event includes structured payload fields `actor_user_id`, `target_user_id` (where distinct from actor), `request_id`, `ip`. Each event is queryable via the existing `/api/admin/audit?action=<action>` endpoint with the standard filter shape. No parallel logging surface is introduced. **Verifiable:** an integration test exercises one event per action and verifies the row; the row's `entity_type` is in `KNOWN_ENTITY_TYPES`. **Pre-2026-05-19 wording said "16 new audit-log actions are registered in `KNOWN_ENTITY_TYPES`" — that conflated action names (free-form) with entity-type registry values (closed-set). Actions are convention; entity_types are the registry.**

#### G. Rate limiting (FR5-RATELIMIT-*; cross-cutting, drives E6 + E9)

- **FR5-RATELIMIT-1: Rate-limit middleware applies to `/api/auth/login`, `/api/auth/refresh`, and `/api/auth/register?token=`.** Thresholds tunable in `apps/api/app/core/config.py`. Implementation strategy: Redis-backed sliding-window (architectural decision in architecture.md Decision G). Default `/api/auth/login` policy: ≥5 failures from one IP within 60 seconds returns HTTP 429 (matches Success Criterion #6). Default `/api/auth/register?token=` policy: brute-force exposure sized such that ≥10⁶ attempts are required to deplete the 256-bit token entropy under the threshold (verified by E9 audit per NFR5-SEC-3). **Verifiable:** scripted 6-failure burst on `/api/auth/login` from one IP returns 429 on the 6th call; documented in `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md`.
- **FR5-RATELIMIT-2: Per-member share-token creation cap (FR5-MEMBER-3) is implemented in the same middleware family.** The cap key is per-member-per-day; the soft-fail alert (50% threshold) emits a tagged log entry that surfaces in GlitchTip per NFR5-OBS-1. The hard-fail (100% threshold) returns HTTP 429. **Verifiable:** the audit smoke artifact records both the soft-alert log emission and the hard-fail HTTP behavior.

#### H. Edge cutover (FR5-CUTOVER-*; drives E10)

- **FR5-CUTOVER-1: The nginx edge configuration at `~/repos/configs/nginx/3d.ezop.ddns.net.conf` is edited atomically in a single commit.** The edit drops both `auth_basic` and the IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`) in the same commit. The `/share/*` and `/agent-runbook` bypass location rules are preserved unchanged. The config diff is captured in architecture.md Decision K (nginx config diff). **Verifiable:** post-reload `curl -fsS https://3d.ezop.ddns.net/api/catalog/models` from outside the LAN-allowlist returns the portal's authentication challenge (HTTP 401 or login redirect), not nginx's `auth_basic` 401.
- **FR5-CUTOVER-2: The cutover is followed immediately by a 4-scenario post-reload smoke matrix executed against `.190`.** Scenarios: (1) anonymous `GET /share/<test-token>` returns 200 (share bypass preserved); (2) `agent` service account `POST /api/admin/models` (cookie+password) returns 201 (agent flow unchanged); (3) `member` login returns 200 + `portal_access` cookie set (new path live); (4) `admin` login returns 200 + admin scope verified (existing path unchanged). The smoke output is captured to `_bmad-output/implementation-artifacts/cutover-smoke-2026-MM-DD.md`. **Verifiable:** every scenario passes within ~30 seconds total; artifact contains timestamps, request IDs, and AuditLog row deltas.
- **FR5-CUTOVER-3: Rollback is single-command and must complete in ≤30 seconds.** Rollback path: `git revert <cutover-sha>` in the sibling repo + `nginx -s reload` on `.180`. The Epic 10 acceptance criterion includes a verified rollback drill (revert + reload + smoke re-run + revert-the-revert + reload + smoke re-run) executed before the cutover is considered closed. Any of the 4 smoke scenarios regressing post-reload triggers immediate rollback. Estimated total cutover window including drill: ~5 minutes. **Verifiable:** the drill artifact captures the rollback timing and the re-run smoke output.

### Non-Functional Requirements

12 NFRs across 6 categories. The Init 5 NFRs encode the security gate condition (NFR5-SEC-*), the integration invariants with Init 0/2 (NFR5-INT-*), and the cross-repo coordination (NFR5-CROSS-REPO-*).

#### A. Security (NFR5-SEC-*; drives E9 hard-gate)

- **NFR5-SEC-1: E9 audit gate condition.** E9 (security audit) is the hard gate before E10 (edge cutover). Gate condition: **zero open Critical/High findings**; **at most 3 "accepted-with-rationale" Medium findings** across the entire audit; the 4th forces auto-fail and triggers a fix sprint. Critical and High findings have no "accepted" disposition path — fixed-or-bust. Audit tooling stack: `bandit` (Python SAST), `semgrep` (multi-lang with OWASP top-10 rulesets), `pip-audit` + `npm audit`/`osv-scanner` (deps), OWASP ZAP active scan against `.190`, `codex review` on new auth/invite/2FA modules. **Verifiable:** the audit report at `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md` shows the disposition table; the cutover does NOT happen until the table satisfies the gate condition.
- **NFR5-SEC-2: Single-operator self-attestation mitigation.** Every Medium finding disposition (fixed / mitigated / accepted-with-rationale) requires a documented second-opinion artifact from `codex review --commit <SHA>` against the relevant patch. "Accepted-with-rationale" specifically requires an explicit countersignature line in the audit report (`countersigned: codex review SHA=<commit>, date=<YYYY-MM-DD>`). The operator is both auditor and gate-keeper, which creates a self-attestation risk; the countersignature plus the max-3-Mediums cap is the documented compensating control.
- **NFR5-SEC-3: Audit scenario coverage matrix.** The E9 audit MUST execute and report on these scenarios: invite-token brute force (rate-limit thresholds must reject before 256-bit entropy depletion by a margin of ≥10⁶); refresh-token replay against the family-rotation logic (`auth.refresh.reuse_detected` triggers on replay); CSRF/JWT tampering on every mutating endpoint; IDOR scan on every admin endpoint; rate-limit verification on `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`; member share-link amplification surface (FR5-MEMBER-3 enforcement check). Each scenario produces a row in the audit report with PASS/FAIL/MITIGATED status.

#### B. Performance (NFR5-PERF-*; cross-cutting)

- **NFR5-PERF-1: `last_active_at` write is throttled to ≤1 per 5 minutes per user.** Updates fire in auth middleware on authenticated requests; the throttle is operationally invisible to the user. Rationale: avoid SQLite write churn at request-path frequency (a single member generating 50 requests/minute would otherwise produce 50 writes/minute against `users.last_active_at`). Implementation: in-memory + Redis-backed last-write timestamp; only writes if `now() - last_write >= 5min`.
- **NFR5-PERF-2: Edge cutover window (Epic 10 deployment) is ≤5 minutes.** Includes the post-reload smoke matrix execution (FR5-CUTOVER-2) and the verified rollback drill (FR5-CUTOVER-3). The rollback path itself MUST complete in ≤30 seconds (`git revert` + `nginx -s reload`).

#### C. Audit integrity (NFR5-AUDIT-*; cross-cutting)

- **NFR5-AUDIT-1: Every Initiative 5 audit action is emitted via the existing `record_event()` helper — no parallel logging surface.** Every admin write that mutates user state (FR5-ADMIN-2), every invite/2FA event (FR5-INVITE-*, FR5-2FA-*), and every registration outcome (FR5-REGISTER-*) emits its audit record. Query path: existing `/api/admin/audit` endpoint with the standard filter shape. The 16 actions enumerated in FR5-AUDIT-1 are the complete Init 5 surface — adding a new audit action mid-stream is a planning event, not an implementation discretion.

#### D. Cross-repo coordination (NFR5-CROSS-REPO-*; drives E10)

- **NFR5-CROSS-REPO-1: The Epic 10 nginx edit bypasses `3d-portal`'s deploy.sh skip-gate.** The edit lives in sibling repo `~/repos/configs/nginx/3d.ezop.ddns.net.conf`; the `infra/.last-deploy-sha` state file is gitignored in `3d-portal` only and has no equivalent in the sibling repo. The Epic 10 acceptance criterion includes a closing reference commit in `3d-portal` (e.g., `docs/operations.md` cutover-date update with a non-skip-prefixed message such as `feat(infra): record edge cutover date 2026-MM-DD`) to record the cutover within `3d-portal`'s deploy history.
- **NFR5-CROSS-REPO-2: The Epic 10 rollback story spans both repos.** Story acceptance includes: `git revert <sha>` in the sibling repo; `nginx -s reload` on `.180`; re-execution of the 4-scenario smoke matrix; "revert the revert" if the original smoke passed (else issue triages to the fix-sprint queue). Sprint planning must reflect the cross-repo coordination explicitly (the story has tasks against two working trees).

#### E. Integration with existing baseline (NFR5-INT-*; preserves Init 0/2)

- **NFR5-INT-1: The `agent` role (Init 2 service account) is preserved exactly.** The agent flow at `POST /api/admin/models` (cookie+password) is unchanged. The `agent` role MUST NEVER appear in `enforce_2fa_for_roles` list (validated at app startup per FR5-2FA-3). Migration of existing `admin` (Michał) and `agent` (AI) rows is null-op — schema additions only (new nullable columns + new tables), no data rewrite. The agent-runbook endpoint at `/agent-runbook` continues to bypass portal authentication after the cutover.
- **NFR5-INT-2: The `/share/*` location bypass is preserved across the cutover.** The `/share/*` location rule continues to bypass portal authentication after Epic 10 — share tokens stay anonymous-accessible per their TTL. Both bypasses (share + agent-runbook) are preserved in the cutover nginx config diff (FR5-CUTOVER-1) and verified by the smoke matrix scenarios 1 + 2 (FR5-CUTOVER-2). Initiative 0's share-token TTL and revoke semantics are unchanged.

#### F. Observability (NFR5-OBS-*; cross-cutting)

- **NFR5-OBS-1: All new auth events produce GlitchTip-visible structured log entries.** Registration, invite consumption, 2FA enrollment/verify, recovery-code use, password reset events all flow through the existing `JsonFormatter` plumbing with namespaced loggers (`app.auth.invite`, `app.auth.totp`, `app.auth.register`, `app.admin.users`). Counter-shaped events for `auth.register.fail`, `auth.totp.verify.fail`, and `auth.login.fail` are observable in the GlitchTip dashboard for credential-stuffing detection (Success Criterion #3 evidence path).
- **NFR5-OBS-2: Initiative 5 produces two named drill artifacts under `_bmad-output/implementation-artifacts/`.** First: `2fa-recovery-drill-2026-MM-DD.md` (Epic 7 close artifact, per Success Criterion #5) — the recovery-code drill executed against the `.190` instance, capturing timestamps + request IDs + AuditLog row deltas. Second: `cutover-smoke-2026-MM-DD.md` (Epic 10 close artifact, per FR5-CUTOVER-2) — the 4-scenario smoke matrix output with the rollback-drill timing.

### Cross-references

- **Brief v2** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines; adversarial-review applied: P0×2 + P1×3 + P2×1 fixed). Binding content source for this section.
- **Brief distillate** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5688 tokens, LLM-optimized).
- **Sprint Change Proposal** — `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Document-shape and numbering decisions are locked here; content outline §4.2 2A defines this section.
- **18 brief working assumptions** challenged during discovery survive into this PRD section (brief v2 §"Working assumptions"). The four load-bearing ones are encoded here: member share-link amplification surface (FR5-MEMBER-3 + NFR5-SEC-3), E9 gate authority + max-3-Mediums cap (NFR5-SEC-1 + NFR5-SEC-2), `last_active_at` throttling (NFR5-PERF-1), invite-token dual-backed storage (FR5-INVITE-1).
- **Architecture extension** — Initiative 5 architecture decisions (A-K in-scope: dual-backed token storage, token shape, member permission scope diff, 2FA column shape, recovery-codes schema, 2FA enforcement config flag, rate-limit middleware Redis sliding-window, per-member share cap, soft-delete + last_active_at throttling, nginx config diff + rollback, cross-repo smoke matrix; L-N deferred: self-service mail reset, OIDC federation, per-model ACL) — to be authored in Session C as `## Initiative 5` H2 in `architecture.md` (manual edit; no `bmad-edit-architecture` skill exists; per AGENTS.md v2 vanilla-first subsection).
- **Epics extension** — Initiative 5 epics (E6 / E7 / E8 / E9 / E10) and stories (~25-35 total, exact count finalizes at sprint-planning time) — to be authored in Session D as `## Initiative 5` H2 in `epics.md` (manual edit).
- **Sprint status** — `_bmad-output/implementation-artifacts/sprint-status.yaml` — to be extended in Session F via `bmad-sprint-planning` with `epic-6` … `epic-10` keys + per-story entries (status `backlog`).
- **Init 0 baseline anchors** — auth stack (Init 0 § Auth module), share-token Redis pattern (Init 0 § Share module), audit log (Init 0 § Admin module audit endpoint), `member` role enum slot (Init 0 § Project Classification + `apps/api/app/core/db/models/_enums.py:10-13`). Initiative 5 is purely additive on these anchors; no Init 0 contract changes.
- **Stakeholders consulted (per brief v2):** Ezop (operator, locked all five top-level decisions); existing BMAD artifacts (prd.md / architecture.md / project-context.md / AGENTS.md); apps/api code recon; apps/web code recon; edge infra sibling repo (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`); memory entries (`feedback_default_to_bmad_workflow.md`, `feedback_brief_autonomous_skip_elicitation.md`, `feedback_invoke_codex_directly.md`, `user_role.md`, `feedback_collaboration_division.md`).

## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20).
Predecessor Initiative 5 closed `7e5aea0` (cutover) + `2429157` (retro). Initiative 6 is **bug-fix-scope-expansion** triggered by Story 9.2 audit scope miss (read-side `/api/*` not probed) + Story 10.3 cutover removing the nginx allowlist that had been load-bearing for app-level auth gating. Source artifacts: `security-audit-2026-05-20.md` § Supplemental High-002 + `codex-review-64447ff-2026-05-20.md` (P1×2 + P2) + Init 5 retro doc-drift items #1-3.

### Overview

Initiative 5 cutover (Story 10.3, sibling configs `5a95b23`) removed the nginx IP allowlist. The architecture intent (Decision C lines 1489-1490) had always specified `current_user` for `/api/sot/*` + `/api/catalog/*`, but implementation in `apps/api/app/modules/sot/router.py` had shipped without that dependency — drift masked by the nginx perimeter. Post-cutover, anonymous external read access to the operator's private catalog metadata was a real privacy regression. Hot-fix attempt `64447ff` was reverted at `be43b92` after Codex P1×2 review caught share-recipient + agent-service-account regressions.

Initiative 6 closes the gap with a **single epic E11** of 7 stories, structured around the operator-aligned non-negotiable D-LOCK-1: all `/api/*` default-deny; explicit allowlist for `/api/auth/*` + `/api/share/{token}*` (resolve + share-scoped asset endpoint per Decision N hardened-(a)); `/api/health` moved to LAN-only. Mechanical enforcement (Story 11.4 pytest enumeration) prevents drift recurrence. Frontend shell-level AuthGate (Story 11.3) ensures anonymous users see only the login surface.

### Functional Requirements

- **FR6-AUTH-1: Default-deny posture on `/api/*` is mechanically enforced.** Every FastAPI route registered with `prefix="/api"` MUST have an explicit auth dependency (`current_user`, `current_member_or_admin`, `current_admin`, or one of the future variants) OR appear in the `_PUBLIC_ROUTES` allowlist constant in `apps/api/app/main.py`. A pytest enumeration test (`apps/api/tests/test_route_enforcement_gate.py`) asserts this property and fails CI on drift. **Verifiable:** the test runs in <1s; adding a new `/api/*` route without auth dep AND without allowlist entry fails the test with a specific error naming the route.
- **FR6-AUTH-2: Anonymous-allowed `/api/*` surface is exactly enumerated.** The `_PUBLIC_ROUTES` allowlist contains: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register`, `/api/auth/totp/verify` (partial-auth step for users mid-2FA-login), `/api/auth/password-reset/consume`, `/api/share/{token}` (resolve), `/api/share/{token}/files/{file_id}/content` (share-scoped asset per Decision N), `/api/csrf-token` (if exists; TBD Story 11.1). Any addition to this list requires a Sprint Change Proposal — it cannot be added in a single story. **Verifiable:** the allowlist constant has exactly these entries and matches the production FastAPI route table.
- **FR6-SHARE-1: Anonymous share-recipients access thumbnails + STL binary via share-scoped asset endpoint.** New endpoint `GET /api/share/{token}/files/{file_id}/content` validates token via existing `ShareService.resolve(token)`, runs scope-check (file belongs to resolved model AND kind ∈ {image, print, stl} AND model not soft-deleted), emits `share.asset.fetched` audit with token-hash (NEVER clear token), serves binary content with `Cache-Control: no-store`. Anonymous-allowed (no auth Depends). Share-router refactored to emit `/api/share/{token}/files/{fid}/content` URLs instead of `/api/models/{m}/files/{f}/content`. Logging.py token-redaction regex extended for path-segment tokens. **Verifiable:** anonymous `GET /api/share/{valid-token}/files/{valid-file-id}/content` returns 200 with the file body for image/print/stl kinds; same request with file from a different model returns 404; same request for `source` or `archive_3mf` kind returns 404; same request with revoked token returns 404 (all 404s uniform — no IDOR enumeration oracle). See architecture.md § Initiative 6 Decision N (hardened-(a) per Codex peer-grill 2026-05-20).
- **FR6-SHELL-1: Frontend AuthGate operates at shell level; anonymous users see only the login surface.** `AppShell.tsx` evaluates authentication state ONCE at shell mount. If `pathname` is in `_PUBLIC_PATHS` (login, register, reset-password, share, share-recipient consumption) → render bare children. Else if authenticated → render full shell (ModuleRail + TopBar + children). Else → redirect to `/login?next=<currentPath>`. Module rail, top bar, and "Coming soon" stubs (Kolejka, Filamenty, etc.) DO NOT render for anonymous users. **Verifiable:** anonymous user navigating to `/`, `/catalog`, or any module slot is redirected to `/login?next=...`; module rail is absent from DOM at the redirect target.
- **FR6-SHELL-2: AuthGate `next` query parameter uses `searchStr` from TanStack ParsedLocation.** `AppShell.tsx` (or remaining shell-level AuthGate logic) reads `searchStr` (string with leading `?`) from `useLocation()`, NOT the parsed `search` object. The `next` redirect URL preserves the original search string. **Verifiable:** anonymous user at `/catalog?category_id=xyz` is redirected to `/login?next=%2Fcatalog%3Fcategory_id%3Dxyz` (URL-encoded original path + searchStr); no `[object Object]` artifacts.
- **FR6-AGENT-1: Agent service-account ingestion preserved.** `apps/api/scripts/hydrate_local_tree.py` continues to pre-flight `/api/categories` + `/api/models?external_url=...` using its existing cookie auth flow (Init 2 baseline). Story 11.1 uses `current_user` (not `current_member_or_admin`) on SoT GET endpoints, which accepts the `agent` role. **Verifiable:** scripted agent login + `GET /api/categories` returns 200; the agent runbook flow end-to-end completes without HTTP 403 on any SoT endpoint.
- **FR6-AUDIT-RERUN-1: Six-scenario audit Scenario 4 (IDOR) target list expands to ALL `/api/*` endpoints.** `infra/scripts/audit-six-scenarios.sh` Scenario 4 enumerates the live FastAPI route table (via `/api/openapi.json` or equivalent), iterates each route as anonymous + as `member`-authenticated, asserts expected response codes (anonymous → 401 except `_PUBLIC_ROUTES`; member → 200/201/403 per route's posture). **Verifiable:** Scenario 4 output includes per-route status; any `/api/*` route returning 200 anonymously that is not in `_PUBLIC_ROUTES` fails the scenario.
- **FR6-CUTOVER-PROBE-1: Cutover-smoke matrix includes automated external-host probe.** `infra/scripts/cutover-smoke.sh` extends with a fifth scenario calling `curl -fsS -o /dev/null -w "%{http_code}" https://3d.ezop.ddns.net/api/categories` from a non-LAN source (CI runner, public VPS, or operator's mobile data network). Expected: 401. **Verifiable:** scenario fails the smoke run if external host returns 200.

### Non-Functional Requirements

- **NFR6-SEC-1: Initiative 6 inherits Init 5 NFR5-SEC-1 audit gate condition.** Story 11.5 audit re-run gate-condition: zero open Critical/High findings; ≤3 accepted-rationale Mediums; 4th forces auto-fail. This is a re-execution of the six-scenario audit with extended Scenario 4, NOT a new audit format.
- **NFR6-SEC-2: Per-Medium codex review countersignature inherits from NFR5-SEC-2.** Same compensating control for single-operator self-attestation.
- **NFR6-SEC-3: Pre-merge codex review for auth-boundary stories.** Stories 11.1, 11.2, 11.3 (auth boundary contracts) get codex review BEFORE merge to main — not after — to catch the same cognitive-pattern miss that produced hot-fix 64447ff. Documented in `docs/operations.md` post-Initiative 6 close.
- **NFR6-PERF-1: Route enforcement test (`test_route_enforcement_gate.py`) runs in <1 second.** Mechanical enumeration; no DB hit; pure FastAPI route-table introspection.
- **NFR6-INT-1: NFR5-INT-1 + NFR5-INT-2 preserved exactly.** Agent service-account flow (cookie+password, `agent` role) and `/share/{token}` anonymous bypass both continue to work. Verified by Story 11.5 audit Scenario 2 (agent ingestion) + Scenario 1 (share bypass) reproducers.
- **NFR6-CROSS-REPO-1: Sibling configs rollback story spans both repos.** Story 11.7 reverts sibling `70cb5ba` (temporary IP allowlist) + records cutover-date update in `docs/operations.md` (`3d-portal`). Mirrors NFR5-CROSS-REPO-1 mechanism.
- **NFR6-OBS-1: New audit-row contract for share-scoped asset endpoint.** Each successful binary fetch via `/api/share/{token}/files/{file_id}/content` emits `share.asset.fetched` audit event with `actor_user_id=null`, `target_token_hash` (sha256, NEVER clear token), `target_model_id`, `target_file_id`, `target_file_kind`, `ip`. Failed lookups (token invalid, file out-of-scope, kind not in {image,print,stl}, soft-deleted model) emit `share.asset.fail` with reason field (audit-only — no clear-token leak).

### Cross-references

- Predecessor: Initiative 5 (Public Registration & User Account Management) — closed 2026-05-20 `7e5aea0` + retro `2429157`.
- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `approved` 2026-05-20, batch-presented mode).
- Source artifacts (problem evidence): `security-audit-2026-05-20.md` § Supplemental High-002; `codex-review-64447ff-2026-05-20.md` § P1+P2 findings; `initiative-5-retro-2026-05-20.md` § Doc-drift batch items #1-3.
- Source design-grill: `codex-design-grill-share-asset-2026-05-20.md` (Codex adversarial review of share-asset trade-off; output of `/tmp/codex-share-asset-grill.md` background run 2026-05-20 ~22:50).
- Architecture extension: `architecture.md` § Initiative 6 (Decisions M, N, O) — manual edit per CC convention.
- Epics extension: `epics.md` § Initiative 6 (single Epic E11 with 7 stories).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via `bmad-sprint-planning` (epic-11 + per-story entries status `backlog`).
- Memory entries informing this initiative: [[itcm-autonomous-mode]] (frame-shift before drafting addition 2026-05-20), [[auth-boundary-contract-audit]] (explicit enumeration phase for auth-boundary commits + SCP recommendations).

## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status `approved` 2026-05-21). Predecessor Initiative 6 closed 2026-05-21 (Stories 11.1–11.7 shipped, cutover-smoke Scenario 5 PASS, audit gate PASS, commit `2641b6c`). Initiative 7 is **additive polish** on Init 5 admin + account self-service surfaces and Init 0 registration flow. Single Epic E12 with 5 stories.

### Overview

Initiative 5 shipped a complete authentication + admin substrate (E6 member role + invites, E7 TOTP 2FA, E8 admin panel users + invites) but the user-facing surfaces have minimum-viable UX. Operator hands-on use 2026-05-21 surfaced five polish gaps: admin Invites nav tab is grayed-out placeholder despite admin role + missing translations + viewport overflow; admin Users panel has no inactive-user filter; registration auto-derives display name from email prefix with no user agency; 2FA enrollment feature is fully present but undiscoverable (no settings hub, no user-menu link); active-sessions list grows unbounded with no pagination/sort/filter, cluttered by API/curl probe sessions.

Initiative 7 raises these surfaces to operator-acceptable UX with five stories, all frontend-heavy. Each story carries a mandatory pre-CR visual-verification AC (NFR7-UX-1) as direct response to Init 6's admin-invites shipping incident.

### Functional Requirements

- **FR7-ADMIN-INVITES-1: Admin Invites nav tab is enabled for admin role.** `apps/web/src/modules/admin/AdminTabs.tsx` replaces the hardcoded `<span aria-disabled="true">` invites entry with a `<Link to="/admin/invites">` element matching the existing styling of the other admin tabs (Users, Models, Categories, Tags, Audit). **Verifiable:** authenticated admin loading `/admin` sees a clickable Invites tab in the admin nav; non-admin authenticated users continue to see the admin module gated (per Init 5 admin role check).
- **FR7-ADMIN-INVITES-2: Admin Invites page renders complete pl/en translations.** The ~20 i18n keys currently missing from `apps/web/src/locales/pl.json` + `en.json` (e.g. `admin.invites.title`, `admin.invites.column_role`, `admin.invites.action_revoke`, etc. — full key list enumerated during Story 12.1 spec) are added with parity between Polish and English locale files. **Verifiable:** loading `/admin/invites` with `lang=pl-PL` renders Polish labels; with `lang=en-US` renders English labels; no raw `admin.invites.*` key strings visible in DOM.
- **FR7-ADMIN-INVITES-3: Admin Invites table fits viewport at desktop default and admin-mobile breakpoints.** Table layout is responsive (max-width on table container, horizontal scroll if needed for narrow viewports, left margin compressed from current Init 5 default). **Verifiable:** Playwright snapshot of `/admin/invites` at desktop-light (1280×720) shows complete table within viewport; mobile-light (390×844 Pixel 5) shows table with horizontal scroll affordance and no right-edge clipping.
- **FR7-ADMIN-USERS-1: Admin Users panel hides inactive users by default with checkbox toggle.** `apps/web/src/modules/admin/UsersPage.tsx` query adds an `is_active` filter param defaulting to `True`. A checkbox labeled "Pokaż nieaktywne konta" / "Show inactive accounts" toggles the filter to `None` (shows all). Inactive rows when shown are visually distinguishable (e.g. muted text color via theme token) but not hidden. **Verifiable:** default load of `/admin/users` shows only `is_active=true` rows; checkbox-checked load shows all rows with inactive rows visually muted.
- **FR7-REG-DISPLAY-1: Registration form accepts optional display name with auto-suggest from email prefix.** Registration page (path TBD during Story 12.3 spec — likely `apps/web/src/routes/auth/register.tsx` or similar) adds an optional `display_name` text field below the email field. On email blur, if the display-name field is empty, populate with email prefix (text before `@`). User can edit/override before submit. Backend `POST /api/auth/register` accepts an optional `display_name` field in the request body. Backend stores the provided value if non-empty; falls back to email prefix server-side if absent. **Verifiable:** filling registration form with email `foo@example.com` populates display-name field with `foo`; user typing `Foo Bar` before submit results in `display_name="Foo Bar"` on the created User row.
- **FR7-SETTINGS-HUB-1: A `/settings` hub page exists and lists all settings sections.** New route `apps/web/src/routes/settings/index.tsx` renders a hub listing: Profile (`/settings/profile`), 2FA (`/settings/2fa`), Sessions (`/settings/sessions`). Each entry is a card or list-row with i18n label + brief description. Anonymous users redirected to `/login?next=%2Fsettings` (per Init 6 FR6-SHELL-1 shell-level AuthGate). **Verifiable:** authenticated user loading `/settings` sees three section entries; clicking any entry navigates to the section route.
- **FR7-SETTINGS-HUB-2: A "Settings" link is visible in the user-menu in the top-bar.** `apps/web/src/shell/TopBar.tsx` (or wherever the user-menu dropdown lives) adds a "Settings" link routing to `/settings`. Placement after the user's name/avatar and before "Sign out". **Verifiable:** authenticated user clicking the user-menu avatar/dropdown sees a "Settings" entry routing to `/settings`.
- **FR7-SESSIONS-1: Active sessions list supports pagination with default page size 20.** `apps/web/src/routes/settings/sessions.tsx` paginates the existing `/api/auth/sessions` endpoint response (which already accepts `offset` + `limit` per backend code at L351-368). UI: page-size selector (default 20, options 10/20/50), prev/next page controls, total-count indicator. **Verifiable:** session list with >20 entries shows pagination controls; clicking next page advances the offset.
- **FR7-SESSIONS-2: Active sessions list filters non-browser User-Agents by default with reveal-toggle.** `apps/web/src/routes/settings/sessions.tsx` adds a checkbox labeled "Pokaż API/non-browser sesje" / "Show API/non-browser sessions" defaulting OFF. When OFF, sessions whose `user_agent` matches a non-browser pattern (e.g. `curl/`, `httpie/`, `python-requests/`, `Mozilla/5.0` not matching a known-browser-fingerprint set TBD during Story 12.5 spec) are excluded from the list. When ON, all sessions show with the non-browser sessions visually distinguishable (e.g. icon or muted color). Sort defaults to `last_used_at DESC`. **Verifiable:** session list with browser + curl entries shows only browser entries by default; checkbox-checked shows all entries with curl entries visually distinguishable.

### Non-Functional Requirements

- **NFR7-UX-1: Pre-CR visual verification gate on every UI story.** Stories 12.1–12.5 each have a mandatory non-functional AC: before marking ready for code-review, the implementing agent loads affected routes in a real browser (agent-browser primary, Playwright fallback) at desktop-default (1280×720) and mobile (≤414px) viewports, captures snapshots, and verifies: (a) route loads without console errors, (b) all i18n keys resolve (no raw `module.section.key` literals), (c) no unintended viewport overflow, (d) all interactive elements clickable (TB-015 class — no `pointer-events: none` swallowing), (e) nav links to/from this surface enabled where appropriate (Init 6 admin-invites class). Snapshots attached to Dev Agent Record. CR may reject for missing snapshots OR observable defects.
- **NFR7-A11Y-1: New interactive controls reachable by keyboard.** Checkboxes (FR7-ADMIN-USERS-1, FR7-SESSIONS-2), enabled nav link (FR7-ADMIN-INVITES-1), display-name field (FR7-REG-DISPLAY-1), pagination controls (FR7-SESSIONS-1), user-menu Settings link (FR7-SETTINGS-HUB-2) are all keyboard-reachable via Tab + activated via Enter/Space per shadcn/ui + base-ui default behavior. **Verifiable:** Playwright keyboard-navigation test reaches each new control within ≤10 Tab presses from page-load focus position.
- **NFR7-COMPAT-1: Initiative 6 default-deny posture preserved.** No new public routes added to `_PUBLIC_ROUTES` allowlist in `apps/api/app/main.py`. All new backend endpoints in Initiative 7 (display-name update endpoint, settings-related endpoints if any) carry `current_user` Depends. **Verifiable:** Story 11.4 route enforcement test continues to pass after Initiative 7 stories merge.

### Cross-references

- Predecessor: Initiative 6 (Post-Cutover Default-Deny Auth Posture) — closed 2026-05-21 `2641b6c`.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this initiative + Init 8 + Init 9 share one SCP).
- Source observations: operator batch report 2026-05-21 + pre-SCP Explore subagent recon 2026-05-21.
- Architecture extension: `architecture.md` § Initiative 7 (Decision Q — settings hub topology; light-touch).
- Epics extension: `epics.md` § Initiative 7 (single Epic E12 with 5 stories 12.1–12.5).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via manual epics.md-mirroring append (epic-12 with 5 backlog stories).
- Memory entries informing this initiative: [[itcm-autonomous-mode]], [[feedback_frontend_visual_verification]], [[feedback_default_to_bmad_workflow]].
- Triage cross-reference: TB-018 (test-isolation cleanup bundle) is NOT part of Initiative 7 — it has been promoted to its own **Initiative 9** in the same SCP per operator scope-pull 2026-05-21, scheduled FIRST in the execution chain to unblock Init 7's admin test surfaces.

## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status `approved` 2026-05-21). Predecessor Initiative 7 (Account & Admin UX Polish) running in parallel — Initiative 8 has no Init 7 dependency. Single Epic E13 with 2 stories.

### Overview

Initiative 0 (Product Foundation) shipped the catalog read-surface (E0.4) with minimum-viable visual quality on mobile and no image transformation pipeline. Operator hands-on use 2026-05-21 surfaced two catalog UX gaps: mobile catalog carousel has no prev/next arrows because the `opacity-0 group-hover:opacity-100` pattern doesn't fire on touch devices (users can only navigate via dots, hard to hit, and accidentally click into the model detail); catalog cards serve full-resolution original images (operator uploads 8K+ phone photos that take seconds to load on mobile data and waste bandwidth).

Initiative 8 raises catalog mobile UX with two stories: 13.1 makes mobile carousel arrows always-visible at sm-breakpoint and below; 13.2 introduces an on-upload thumbnail pipeline (Pillow, 800px longest side, WebP @ q80) with a query-param variant endpoint, srcSet on catalog cards, and a one-shot backfill script for existing uploads.

### Functional Requirements

- **FR8-CAROUSEL-MOBILE-1: Catalog carousel prev/next arrows are visible on mobile (≤sm breakpoint).** `apps/web/src/ui/custom/CardCarousel.tsx` and `apps/web/src/modules/catalog/components/ModelGallery.tsx` arrow buttons change from `opacity-0 group-hover:opacity-100` (current — invisible on touch) to `sm:opacity-0 sm:group-hover:opacity-100` (new — desktop unchanged behavior, mobile always-visible). **Verifiable:** Playwright snapshot of catalog list page at mobile-light (390×844 Pixel 5) shows prev/next arrow buttons rendered visibly; desktop-light (1280×720) snapshot shows arrows hidden until hover (current behavior preserved).
- **FR8-THUMB-1: Image-kind file uploads generate a thumbnail variant on upload.** `apps/api/app/modules/admin/router.py` model-file create endpoint (image kind) enqueues an arq task that generates a thumbnail variant via Pillow: 800px longest side, WebP container, quality 80, EXIF orientation honored. Thumbnail stored alongside original in `portal-content` volume with naming convention `<original-filename>.thumb.webp`. **Verifiable:** uploading a 4000×3000 JPEG as image-kind file results in (a) original preserved as-is, (b) sibling `<filename>.thumb.webp` file created within 30 seconds, (c) thumbnail is 800×600 (longest-side scaled), (d) thumbnail file size ≤50 KB (NFR8-PERF-1).
- **FR8-THUMB-2: Asset content endpoint supports `variant=thumb` query param.** `apps/api/app/modules/sot/router.py` GET `/api/models/{model_id}/files/{file_id}/content?variant=thumb` returns the thumbnail variant if it exists; falls back to original if not (e.g. for files uploaded before thumbnail pipeline shipped and not yet backfilled). **Verifiable:** `curl /api/models/.../files/.../content?variant=thumb` returns the `.thumb.webp` file with `Content-Type: image/webp`; same request without `variant=thumb` returns original with original content-type.
- **FR8-THUMB-3: Catalog cards request thumbnail variant via srcSet.** `apps/web/src/modules/catalog/components/ModelGallery.tsx` (and any catalog-card image-srcing site) renders `<img srcSet="${full} 2x, ${thumb} 1x">` or equivalent. Detail view (model-page large image) continues to use full-resolution original. **Verifiable:** Playwright network capture on catalog list shows requests to `?variant=thumb` URLs; model-detail page navigation shows requests to full-res URLs.

### Non-Functional Requirements

- **NFR8-PERF-1: Thumbnail variant payload ≤50 KB for typical phone-photo inputs.** Pytest fixture exercises Pillow pipeline with representative samples (3000×4000 JPEG, 4000×3000 JPEG, 2000×3000 PNG with alpha) and asserts output ≤50 KB per sample. **Verifiable:** test fixture in `apps/api/tests/test_thumbnail_pipeline.py` runs in <5s and passes for all sample categories.
- **NFR8-COMPAT-1: WebP browser support fallback posture.** WebP is supported by all browsers in the project's tested matrix (Chromium-based, Firefox 65+, Safari 14+). Frontend does NOT include a JPEG fallback `<source>` in `<picture>`; if a future browser-compat regression surfaces, the fallback gets added in a follow-up story. **Decision rationale:** the project's user base is technical (operator + invited members on modern browsers); WebP compatibility headache is not load-bearing today.
- **NFR8-UX-1: Pre-CR visual verification gate on every UI story.** Same shape as NFR7-UX-1 — Stories 13.1 and 13.2 both have the mandatory pre-CR agent-browser snapshot pass. Especially important for 13.1 (mobile-only behavior change) and 13.2 (srcSet wiring is easy to miss in unit tests).

### Cross-references

- Predecessor: Initiative 0 (Product Foundation) — shipped retrospective 2026-04 v1.
- Parallel-running: Initiative 7 (Account & Admin UX Polish) — no Init 7 dependency.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this initiative + Init 7 + Init 9 share one SCP).
- Source observations: operator batch report 2026-05-21 items #8 + #9 + pre-SCP Explore subagent recon 2026-05-21.
- Architecture extension: `architecture.md` § Initiative 8 (Decision P — thumbnail pipeline shape; on-upload + query-param variant + backfill).
- Epics extension: `epics.md` § Initiative 8 (single Epic E13 with 2 stories 13.1 + 13.2).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via manual epics.md-mirroring append (epic-13 with 2 backlog stories).
- Memory entries informing this initiative: [[itcm-autonomous-mode]], [[feedback_frontend_visual_verification]].

## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status `approved` 2026-05-21). Predecessor Initiative 6 closed 2026-05-21. Initiative 9 is **brownfield test-infrastructure cleanup** on test surfaces that pre-date Initiatives 5+6 and have failed silently through multiple sprint close-outs. **Scheduled FIRST in this SCP's execution chain** (before Initiative 7 + Initiative 8) because the test surfaces directly interfere with planned Init 7 + 8 stories. Single Epic E14 with 3 stories.

### Overview

Three pre-existing test-isolation gaps surfaced across Initiative 5 + 6 close-outs and were originally parked in `_bmad-output/triage-backlog.md` as TB-018 for a future dedicated CC session. Operator scope-pull 2026-05-21 promoted them into this SCP's scope, with the technical rationale that the affected test surfaces (admin module vitest + admin visual baselines + User/ModelFile pytest fixtures) coincide with Initiative 7 Stories 12.1, 12.2, 12.3, 12.5 + Initiative 8 Story 13.2 — leaving the issues parked would force the new stories to develop on unreliable test signal.

Initiative 9 closes the three gaps with three stories, each verified by determinism (NFR9-DETERMINISM-1). Initiative 9 does NOT carry the NFR7-UX-1 / NFR8-UX-1 visual-verification gate because its stories are test-infrastructure-only and have no observable UI surface (test files, conftest, hook chain).

### Functional Requirements

- **FR9-VITEST-ADMIN-1: Vitest admin module test suite has 0 failures.** `apps/web/src/modules/admin/InvitesPage.test.tsx` + `GenerateInviteModal.test.tsx` + `InviteTokenDisplayModal.test.tsx` + `ResetLinkDisplayModal.test.tsx` + `UsersPage.test.tsx` collectively go from 18 failing tests to 0 failing tests. Fix path: regenerate finder selectors (text/role/label matchers) against the current i18n keys + DOM shape. ITCM constraint: prefer test-side fixes; component-side changes only if structurally infeasible (and any component-side change must be justified in the story's Dev Agent Record as "this is an actual component bug, not a test bug"). **Verifiable:** `npm run test apps/web/src/modules/admin/` returns 0 failures; 5 affected files all pass; total admin-module vitest count grows or stays same (no test deletions to mask failures).
- **FR9-PYTEST-HYDRATE-1: `test_hydrate_creates_local_tree` passes deterministically when run after `test_sot_model_file_content`.** Root cause investigation (Story 14.2): identify the leak path of `FAKE_STL_PAYLOAD_AAA` from `test_sot_model_file_content.py` into the `/api/models` listing that `test_hydrate_creates_local_tree` iterates. Fix tightens the `apps/api/tests/conftest.py` isolation contract (probable: function-scoped DB fixture, or explicit teardown for FAKE_STL seeds, or DB transaction rollback at test exit). **Verifiable:** running `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in this exact order across 10 consecutive invocations yields all-PASS (NFR9-DETERMINISM-1 confirmation).
- **FR9-VISUAL-HOOK-1: Visual-regression hook-context produces identical pass/fail verdict to standalone Playwright invocation across ALL existing baselines.** Investigation (Story 14.3 begins with instrumentation pass): determine whether the divergence is port collision, build-SHA drift, snapshot cache invalidation, or environment-variable propagation. Fix removes the divergence. **Verifiable:** `infra/scripts/check-all.sh` visual stage and `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` produce same `passed/failed/skipped` counts for the full baseline set, run back-to-back, ≥3 consecutive runs in each context (NFR9-DETERMINISM-1).

### Non-Functional Requirements

- **NFR9-DETERMINISM-1: Each Initiative 9 fix is verified by ≥3 consecutive successful runs of the affected test suite.** This is the test-infrastructure analog of the UI visual-verification gate — a procedural commitment to "the fix actually fixed it, repeatably, not just luckily once." Story 14.1 verification: `npm run test apps/web/src/modules/admin/` 3× consecutive. Story 14.2 verification: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` 3× consecutive. Story 14.3 verification: full visual-regression baseline set via `check-all.sh` 3× consecutive vs standalone 3× consecutive, identical verdict each time. Logged in Dev Agent Record per story.
- **NFR9-SCOPE-1: No production-code changes in Initiative 9 stories.** All work is test-side (test files, conftest, hook chain). If any of the three stories surface what looks like a production-code bug (e.g. a real component bug masquerading as a finder mismatch), the story stops, the bug is escalated to operator as a real product blocker, and Initiative 9 does not absorb the fix. Production-code fixes belong in a follow-up story under whichever initiative owns the surface.

### Cross-references

- Predecessor: Initiative 6 (Post-Cutover Default-Deny Auth Posture) — closed 2026-05-21 `2641b6c`.
- Successor (Initiative 9 unblocks): Initiative 7 (Account & Admin UX Polish), specifically Stories 12.1, 12.2, 12.3, 12.5; Initiative 8 (Catalog Mobile & Image Performance), specifically Story 13.2.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this document).
- Source observations: TB-018 entry in `_bmad-output/triage-backlog.md` + operator scope-pull 2026-05-21 (mid-SCP-review).
- Architecture extension: `architecture.md` § Initiative 9 (pointer-only — no architectural decisions; test-infrastructure only).
- Epics extension: `epics.md` § Initiative 9 (single Epic E14 with 3 stories 14.1, 14.2, 14.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-14.
- Memory entries informing this initiative: [[feedback_preexisting_issue_threshold]] (threshold-derived candidacy mechanism), [[feedback_vitest_manual_cleanup]] (global `vitest.setup.ts` registers `afterEach(cleanup)` since commit a026e97 — Story 14.1 cleanups should NOT re-introduce per-file boilerplate), [[feedback_pytest_timeout]] (Story 14.2 verification MUST wrap pytest in `timeout 600`), [[feedback_visual_failure_mode_triage]] (Story 14.3 grep failure-mode breakdown before fixing).
- Triage cross-reference: TB-018 entry status flips `candidate` → `promoted` on SCP approval 2026-05-21, then `promoted` → `done` per-Story-14.x close. TB-015 promotion (standalone quick-dev shipped 2026-05-21 commit `e59abe5`) is independent of Initiative 9.

## Initiative 10 — Operator Polish Batch

**Status:** 🚧 planning (started 2026-05-22). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-22-init10.md` (status `approved` 2026-05-22). Predecessor Initiative 9 closed 2026-05-22 (chained autonomous batch with Init 7+8). Initiative 10 is a **stakeholder-batch-driven enhancement initiative** spanning test-suite determinism + catalog power-user features + operator UX polish + backlog sweep. Three epics E15+E16+E17 with ~13 stories total.

### Overview

10 stakeholder items grouped per [SCP §1](sprint-change-proposal-2026-05-22-init10.md):

- **Epic 15 — Test Health & Determinism** (item #1): close 1 pytest threading deadlock + 86 stale-baseline visual-regression failures + ~16-file per-file `client` fixture refactor. Audit-driven scope from recon subagent 2026-05-22; vitest already at flake-zero, no work needed there.
- **Epic 16 — Catalog Power-User Features** (items #4.1, #4.2, #5, #8, #9, #10): ModelNote bilingual schema migration (body → body_pl + body_en) + on-demand "Generate description" admin UI + anonymous share-link frontend viewer (member-generated, 7d hard-cap TTL, revocable from UI) + admin manual model-add + admin STL/file upload to existing model + bulk STL download ZIP restoration.
- **Epic 17 — Operator UX & Backlog Sweep** (items #2, #3): admin tables fluid full-width universal pattern (designer subagent recommendation — confirms operator intuition; ~6 lines diff across 3 files) + TB-016 agent runbook doc-honesty fixes (3 findings) + DOC-DRIFT-2 remaining 4 drifts close-out.

Items #6 (OTEL collector data-prepper backpressure) and #7 (401 scan-pattern security inquiry) are RECONCLUDED OUT-OF-SCOPE per SCP §B — Operator Action Items (Appendix B of SCP): #6 is infra-side (~75% confidence per OTEL recon subagent; operator action SSH `.190` + restart data-prepper), #7 is blocked on SSH connectivity restoration. Neither folds into any Init 10 epic.

### Functional Requirements

**Test Health (Epic 15):**

- **FR10-TEST-DETERMINISM-PYTEST-1:** `cd apps/api && timeout 600 uv run pytest tests/` completes deterministically (exit 0, no hang, no timeout) across 3 consecutive invocations. Root cause: `test_concurrent_refresh_one_wins` (`apps/api/tests/test_auth_refresh.py:164-194`) threading deadlock with non-thread-safe `_patch_arq_pool` autouse fixture. Story 15.1 Phase 1 instrumentation pins whether the fix is test-only (rewrite without `threading.Thread`) or prod-side (`asyncio.Lock` around `create_pool` race) — both paths acceptable, decision is data-driven.
- **FR10-TEST-DETERMINISM-PLAYWRIGHT-1:** `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` completes with 0 unhandled failures, deterministic exit 0 across 3 consecutive invocations (standalone) AND `infra/scripts/check-all.sh visual` (hook context) — identical pass/fail verdict. Story 15.2 closes 86 deterministic failures (78 stale-baseline drift across 12 spec files from Init 5/6/7/8 UI evolution + 8 `page.waitForURL` timeouts in `anon-login-only.spec.ts`).
- **FR10-TEST-FIXTURE-CLEANUP-1:** Per-file `client` fixture redundancy resolved across ~16 files in `apps/api/tests/test_{2fa,auth,admin,invite,share}_*.py`. Single centralized `isolated_client` fixture in `apps/api/tests/conftest.py` (Epic 8 retro carry-forward item §10). Pure refactor; no behavior change in any test.

**Catalog Power-User Features (Epic 16):**

- **FR10-DESC-1:** `ModelNote` schema migrates from single `body: str` to bilingual `body_pl: str | None` + `body_en: str | None`. Forward-only Alembic migration: drop `body NOT NULL`, add new nullable columns, backfill `UPDATE model_note SET body_en = body WHERE kind = 'description'`, drop legacy `body`. Frontend `DescriptionPanel.tsx` renders `body_pl` if locale=`pl` and `body_pl IS NOT NULL`, fallback `body_en`, else empty-state.
- **FR10-DESC-2:** Admin-only "Generate description" button on model-detail surfaces a dialog with source toggles (external-URL scrape from existing `ModelExternalLink` if present + Nextcloud catalog notes via existing rsync state) + free-form additional-context textarea + locale selector (pl / en / both). Backend enqueues arq job that calls Claude API (Haiku 4.5 default; budget-bounded) and returns generated content. Frontend polls (5s/60s) and shows preview UI with regenerate + accept/reject CTAs. Accept persists via `PUT /api/admin/models/{id}/notes`.
- **FR10-SHARE-ANON-1:** New TanStack Router file-route `apps/web/src/routes/share/$token.tsx` renders anonymous viewer with NO ModuleRail, minimal TopBar (logo only), reuses `Viewer3DInline` + `DescriptionPanel` + `FilesTab` (download-only — no upload affordances). Route MUST NOT trigger `AuthGate`. Data fetched via existing `/api/share/<token>/*` endpoints (Init 6 Decision N).
- **FR10-SHARE-ANON-2:** Member-side UI: share-link generation dialog with TTL dropdown (1d / 3d / 7d) on model-detail page (visible to `current_member_or_admin` per Init 5 FR5-MEMBER-1). New "My share links" page at `apps/web/src/routes/settings/share-links.tsx` listing all member-minted share-tokens + revoke CTA (`DELETE /api/admin/share/{token}` — backend already supports). Rate-limit reuses Init 5 FR5-MEMBER-3 (20/day, no API changes).
- **FR10-MANUAL-ADD-1:** Admin-only endpoint `POST /api/admin/models` accepting `multipart/form-data` with JSON manifest (name_pl, name_en, category_id, source, rating, external_url, description_pl, description_en, tag_ids) + file uploads (thumbnail, images, files). Same audit-log + thumbnail-render-job-enqueue patterns as existing agent endpoint. New admin route `apps/web/src/routes/admin/models/new.tsx`. Members continue to use agent flow (operator decision §1.1).
- **FR10-MANUAL-ADD-2:** Admin-only endpoint `POST /api/admin/models/{id}/files` accepting multipart with `kind` (stl/step/f3d/image/thumbnail) + file. Simple replace semantics: primary STL/STEP/F3D replace existing; images/thumbnails append. No versioning yet. UI "Upload file" CTA on model-detail (admin-visible only) opens dropzone dialog with kind selector.
- **FR10-DOWNLOAD-1:** Restore `GET /api/sot/models/{id}/bundle` (or equivalent per current module conventions — verify against last-shipped naming) returning `application/zip` with all printable files (STL + STEP + F3D + .3mf if present) at top-level with original filenames. Member + admin auth (matches `/api/sot/models/{id}/files/{fid}/content`). UI "Download all (ZIP)" CTA on model-detail (already partially wired per Init 0 SLICE-13 history; verify + connect to restored endpoint).

**Operator UX & Backlog Sweep (Epic 17):**

- **FR10-UX-TABLES-1:** Admin tables (Invites, Users) render fluid full-width (no `max-w-*` cap on container, no `min-w-[*]` on table). Sessions page (`max-w-3xl`) retained — form-style settings, not data-dense listing. Visual baselines regenerated for admin-invites + admin-users baselines across 4 viewport projects.
- **FR10-TRIAGE-1:** TB-016 agent runbook doc-honesty fixes (3 findings): Finding A (poll budget 60s → 120s + 1-sentence mesh-size variance qualifier), Finding B (full rewrite of `agents-add-model-runbook.md:142` dropping `D:\` Windows-specific path reference), Finding C (rewrite `:303` + update example payload `:395` active bilingual-name guidance). Single doc-only commit; auto-deploy skipped.
- **FR10-TRIAGE-2:** DOC-DRIFT-2 close-out: remaining 4 drifts patched across `_bmad-output/planning-artifacts/{epics.md, architecture.md, prd.md}` (Drift 3 Decision B INTEGER→UUID schema rewrite, Drift 5 `refresh_tokens` autogenerate code-side cleanup, Drift 16 `ratelimit_share_*` Settings field naming cosmetic, Drift 17 `test_create_share_requires_admin` test rename). 1-2 commits (docs + code-side).

### Non-Functional Requirements

- **NFR10-DETERMINISM-1: Cross-framework test-suite determinism contract.** Vitest + pytest + playwright visual all pass deterministically across 3 consecutive invocations after Epic 15 close. Forward-applicable to Init 11+: any future test flake observed requires immediate root-cause + permanent fix (no `retry: 3`, no skip-tag, no per-story flake-investigation cycles). Carries the Init 9 NFR9-DETERMINISM-1 spirit at whole-suite grade.
- **NFR10-SCOPE-1: No production-code changes in Epic 15 stories EXCEPT where root-cause analysis pins a real prod-side bug (Story 15.1 decision boundary).** Carries Init 9 NFR9-SCOPE-1 with the explicit boundary-carve for the threading deadlock — if Phase 1 instrumentation reveals a real `create_pool` concurrency race, prod-side fix is in scope and Initiative 10 absorbs it (with appropriate Codex review per Story 15.1 AC).
- **NFR10-SCHEMA-MIGRATION-1: Story 16.1 ModelNote bilingual migration is forward-only.** No rollback path defined; the prior Alembic revision tag is kept for emergency revert. Migration may run with <2-min downtime window (catalog is single-instance, acceptable). Backfill `body → body_en` is part of the migration script, not a separate manual step. Rollback path: down-migration to prior revision (drop body_pl + body_en, restore body NOT NULL); operator must accept data loss in body_pl values if rollback is needed.
- **NFR10-VISUAL-VERIFICATION-1: Every UI-touching Init 10 story carries the pre-CR agent-browser visual-verification gate established in Init 7+8+9.** Forward contract per memory [[feedback_frontend_visual_verification]]. Applies to: 16.1 (DescriptionPanel render diff), 16.2 (Generate dialog UI), 16.3 (anonymous share viewer + member-side share UI + My share links page), 16.4 (admin model-add form), 16.5 (admin file-upload dialog + button), 16.6 (Download all CTA wiring), 17.1 (admin tables fluid width). Stories 15.1+15.2+15.3 are test-infrastructure-only (no UI surface) — gate does NOT apply per Init 9 precedent.
- **NFR10-SHARE-SECURITY-1: Anonymous share viewer (FR10-SHARE-ANON-1) MUST NOT expose admin-mutating endpoints, MUST NOT leak `current_user` state, MUST NOT bypass existing share-token revoke semantics.** Frontend must NOT call `/api/auth/me` or any `current_user`-dependent endpoint inside `/share/$token` route. All asset fetches go through `/api/share/<token>/*` (anonymous-allowed per Init 6 Decision N + auth-boundary contract per Init 6 NFR6-SEC-1). Story 16.3 acceptance includes a Codex auth-boundary contract audit per memory [[auth-boundary-contract-audit]].

### Decisions

- **Decision L** (architecture): ModelNote bilingual schema migration shape (see `architecture.md` § Initiative 10 Decision L).
- **Decision M** (architecture): Anonymous share-link frontend route shell (see `architecture.md` § Initiative 10 Decision M).
- **Decision N** (architecture): Admin manual-add model + file upload write surface (see `architecture.md` § Initiative 10 Decision N).

### Out of scope (intentional)

- **Item #6 — OTEL collector data-prepper backpressure.** RECONCLUDED infra-side ~75% confidence per OTEL recon subagent 2026-05-22. Operator action: SSH `.190` + `docker logs data-prepper --tail 200` + restart if stuck. Belongs to `~/repos/configs/` operational maintenance, not 3d-portal code.
- **Item #7 — 401 scan-pattern security inquiry.** BLOCKED on SSH connectivity to `.190` from dev box (timeout at SCP-draft time 2026-05-22). Operator action: restore SSH; Claude can run log-analysis subagent on demand once unblocked.
- **Contributor role** (rejected in operator decision §1.1): no new role between member and admin. Manual model add stays admin-only.
- **30d/never share-link TTL** (rejected in operator decision §1.1): hard-cap 7d. Operator can re-evaluate in Init 11+ if security posture warrants longer TTLs.
- **Blanket auto-fill description pass** (rejected in operator decision §1.1): on-demand `Generate` button per-model with admin preview-accept-or-edit. No batch job that touches all NULL descriptions at once.
- **TB-014 (crealitycloud enum), TB-017 (TOTP key rotation runbook):** declined-defer with documented rationale (see SCP §3.5 + triage-backlog.md).

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-22-init10.md` (full ~580-line draft + recon outputs in Appendix C).
- Architecture extension: `architecture.md` § Initiative 10 (Decisions L + M + N).
- Epics extension: `epics.md` § Initiative 10 (E15 + E16 + E17 with ~13 stories).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-15 / epic-16 / epic-17.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]] (ITCM ownership pattern), [[feedback_vanilla_bmad_first]] (BMAD discipline floor), [[feedback_frontend_visual_verification]] (UI story AC gate), [[feedback_pytest_timeout]] (Story 15.1 verification), [[feedback_visual_failure_mode_triage]] (Story 15.2 triage), [[feedback_auth_boundary_contract_audit]] (Story 16.3 Codex review).
- Triage cross-reference: TB-016 + DOC-DRIFT-2 promoted via Story 17.3 + 17.4; TB-014 + TB-017 declined-defer with documented rationale; TB-018 retroactively done.

## Initiative 11 — Triage Quick Wins Bundle

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11. Predecessor: Init 10. Single epic E18 with 5 stories.

### Overview

Triage quick wins bundle — 5 small fixes from operator hands-on backlog: TB-025 add-note 404 (POST path fix), TB-028 admin Users table overflow-wrapper, TB-014 crealitycloud enum, TB-021 pytest 2 pre-existing failures, TB-016 remaining doc drifts.

### Functional Requirements

- **FR11-FIX-NOTE-1**: `useCreateNote` POSTs to `/admin/models/{id}/notes` matching API contract.
- **FR11-UX-USERS-TABLE-1**: admin Users page wraps table in `overflow-x-auto` mirroring Invites pattern.
- **FR11-ENUM-CREALITY-1**: `crealitycloud` added to `ModelSource` + `ExternalSource` StrEnums.
- **FR11-TEST-PYTEST-1**: 2 pre-existing pytest failures fixed (test_redis_down_passes_through_with_warning + test_list_files_returns_image_kinds_in_position_order).
- **FR11-DOC-DRIFT-1**: TB-016 doc drifts 5 + 16 closed.

### Non-Functional Requirements

- **NFR11-DETERMINISM-1**: full pytest 846/846 PASS deterministic post-Story-18.4.
- **NFR11-CODEX-ROUTING-1**: all 5 Codex reviews on gpt-5.4-mini (routine class per [[feedback_codex_model_routing]]).

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 11.
- Epics: `epics.md` § Initiative 11 (Epic 18 with stories 18.1-18.5).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-18.

## Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening

**Status:** ✅ shipped 2026-05-23 (Stories 19.1, 19.3, 19.4, 19.7 fully closed CLEAN; Story 19.2 nginx throughput cap in configs repo — operator manual deploy + sync.sh required; Stories 19.5 + 19.6 in `review` status with Codex review carry-forward). Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 12. Single epic E19 with 7 stories.

### Overview

Anonymous share view enrichment + DDoS hardening batch — operator-calibrated 2026-05-23 (AskUserQuestion): security-first priority, 60 req/min cap, 2 MB/s + 5 concurrent per IP, carousel = member-view-scoped (not admin-minus). 7 stories realizing TB-026 sub-items 1-7 + Decision Q (request-rate middleware) + Decision R (Nginx throughput cap) + Decision S (STL preview render pipeline) + Decision T (share file list endpoint).

### Functional Requirements

- **FR12-SHARE-RATELIMIT-1**: per-(token, IP) request-rate middleware on `/api/share/*` (60 req/min sliding window). Story 19.1.
- **FR12-SHARE-THROUGHPUT-1**: nginx `limit_rate 2m` + `limit_conn share_anon_conn 5` on share asset endpoint. Story 19.2.
- **FR12-SHARE-FILE-LIST-1**: `GET /api/share/{token}/files` paginated file list endpoint. Story 19.4.
- **FR12-SHARE-DESCRIPTION-1 + FR12-SHARE-CAROUSEL-1**: anonymous share view bilingual description + ShareCarousel with thumb strip. Story 19.5.
- **FR12-STL-PREVIEW-RENDERS-1**: lazy STL preview render job (4-view iso/front/side/top WebPs). Story 19.6.
- **FR12-SHARE-3D-VIEWER-1**: embedded Viewer3DInline on share view via `srcOverride` (depends on Init 13 Story 20.3). Story 19.7.

### Non-Functional Requirements

- **NFR12-DDOS-RATE-1**: 60 req/min/(token,IP) cap.
- **NFR12-DDOS-THROUGHPUT-1**: 2 MB/s + 5 concurrent per IP cap (Story 19.2 nginx).
- **NFR12-THREAT-MODEL-1**: 6 threat vectors enumerated in architecture.md (Story 19.3 / Decisions Q+R+S+T).
- **NFR12-FRONTEND-VISUAL-1**: agent-browser smoke + visual baselines for /share/$token route on UI-touching stories.

### Decisions

- Decision Q (request-rate middleware), R (Nginx throughput cap), S (STL preview render pipeline), T (share file list endpoint) — see `architecture.md` § Initiative 12.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 12.
- Architecture: `architecture.md` § Initiative 12 (Decisions Q + R + S + T).
- Epics: `epics.md` § Initiative 12 (Epic 19 with stories 19.1-19.7).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-19.

## Initiative 13 — Catalog UX Uplift

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13. Predecessor: Init 12. Single epic E20 with 3 stories.

### Overview

Catalog UX polish batch — operator-aligned 2026-05-23 (AskUserQuestion): Add Model CTA top-right toolbar + modal-over-route + full form; catalog srcSet 2x candidate dropped for retina users; Viewer3DInline `srcOverride` hook (Story 20.3) shipped FIRST as Init 12 Story 19.7 prerequisite.

### Functional Requirements

- **FR13-CATALOG-PERF-1**: drop `${thumbUrl} 1x, ${fullUrl} 2x` srcSet candidate (Story 20.1). Resolves TB-027 retina perf.
- **FR13-CATALOG-CTA-1**: admin Add Model CTA + modal (Story 20.2). AddModelForm reusable component, AddModelModal Dialog wrapper, AddModelButton catalog toolbar (admin-only). Resolves TB-029.
- **FR13-VIEWER-SRCOVERRIDE-1**: Viewer3DInline `srcOverride` prop for non-default-auth contexts (Story 20.3). Resolves TB-022.

### Decisions

- **Decision U** — Add Model modal-over-route shape.
- **Decision V** — srcSet retina drop.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 13.
- Architecture: `architecture.md` § Initiative 13 (Decisions U + V).
- Epics: `epics.md` § Initiative 13 (Epic 20 with stories 20.1-20.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-20.

## Initiative 14 — Test Infrastructure Hardening

**Status:** ✅ shipped 2026-05-23. Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14. Single epic E21 with 2 stories.

### Overview

Test infrastructure hardening batch — Story 21.1 (TB-018 #2 hydrate pollution) verified ALREADY CLOSED via Init 9 Story 14.2; no work needed. Story 21.2 (TB-023 credentialless test fixture) shipped maszynowo NFR10-SHARE-SECURITY-1 contract enforcement.

### Functional Requirements

- **FR14-TEST-CREDENTIALLESS-1**: `make_anonymous_client` helper + `assert_no_set_cookie_in_response` assertion in conftest.py + 3 credentialless contract tests on share-router endpoints (Story 21.2). Resolves TB-023.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 14.
- Epics: `epics.md` § Initiative 14 (Epic 21 with stories 21.1-21.2).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-21.

## Initiative 15 — Meta + Deferred

**Status:** ✅ shipped 2026-05-23 (meta-only; doc-only commit). Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15. NOT an epic (per SCP §2.2 — Init 15 deliberately bypasses epic structure for meta/skill-file work).

### Overview

- **TB-024 closed** (commit 80f25d4): BMAD skill template updates from Init 10 retro. bmad-create-story checklist §3.6 "Already-Shipped DISASTERS" + bmad-create-architecture template "Authoring guidance" for 4-cell dual-field matrix.
- **TB-017 DEFERRED** per SCP — TOTP_FERNET_KEY rotation runbook, trigger date 2027-05-20, doc authoring ≤2 months before.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-23-init-11-15.md` § Initiative 15.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § init-15-meta.

## Initiative 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)

**Status:** 🚧 planning (started 2026-05-24). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-24-init16.md` (status `approved` 2026-05-24). Predecessor Initiative 15 closed 2026-05-23 (meta + deferred). Initiative 16 is a **triage backlog cleanup batch** sweeping 9 open candidates post-Init-15. Three epics E22+E23+E24 plus standalone Story S25.1, ~8 stories total.

**Note on H2 backfill debt:** Initiatives 11, 12, 13, 14, 15 H2 sections are NOT yet present in this PRD (carried in `sprint-change-proposal-2026-05-23-init-11-15.md` only). Tracked as TB-039 (Init 11-15 H2 backfill housekeeping) and scheduled for Init 16 close-out hygiene pass.

### Overview

Operator authorized "wszystkie otwarte backlog itemy (chyba że deferred na konkretną datę)" 2026-05-24. Pre-SCP enumeration reconciled apparent in-scope set against Init 11-15 shipped state (closed-by-displacement items removed); 9 genuine in-scope candidates grouped into 3 epics + 1 standalone story per job-shape. Full SCP details in source document; this PRD section consolidates the requirements-level contract.

### Functional Requirements

**Image tier pipeline + symmetric fullscreen viewer (Epic 22):**

- **FR16-TIER-1: `generate_thumbnail` worker produces gallery tier variant alongside existing thumb tier.** `<basename>.gallery.webp` (NEW, ~150-500 KB, designer-tuned default 1920px longest-edge) generated at thumbnail-job dispatch on upload + via backfill script. `GET /api/models/{id}/files/{fid}/content?variant=gallery` returns the gallery WebP blob; silent fallback to original when sibling missing (mirrors thumb fallback pattern). **Verifiable:** pytest fixture in `apps/api/tests/test_thumbnail_pipeline.py` asserts gallery output ≤500 KB on representative samples + variant routing test validates `?variant=gallery` URL resolves to expected blob shape.
- **FR16-CAROUSEL-TIER-1: ShareCarousel + CardCarousel main frame consume `?variant=gallery`.** `apps/web/src/routes/share/$token.tsx:ShareCarousel` main frame switches from full-blob URLs (`data.images`) to `?variant=gallery`; thumb strip stays `?variant=thumb`. `apps/web/src/ui/custom/CardCarousel.tsx` (catalog detail surface) main frame consumes `?variant=gallery`; card-grid stays `?variant=thumb` (Story 20.1 baseline). **Verifiable:** visual baselines regenerated for both surfaces across 4 viewport projects; operator manual verify per [[feedback_frontend_visual_verification]].
- **FR16-VIEWER-1: NEW symmetric fullscreen image viewer mounts on both anonymous and authenticated surfaces.** Component mounts on BOTH `/share/$token` AND `/catalog/$modelId` detail page (operator-decided symmetric per 2026-05-24 AskUserQuestion). Fetches `?variant=full` (original blob) for fullscreen frame; thumb strip uses `?variant=thumb`. UX shape locked by designer UX session BEFORE Story 22.3 spec authoring (modal vs OOTB lightbox, dimensions, trigger pattern, mobile gestures, i18n keys). **Verifiable:** visual baselines created on both routes; agent-browser smoke pass per NFR16-VISUAL-VERIFICATION-1.
- **FR16-HYGIENE-TIER-1: Post-tier-ship hygiene pass.** Backfill rerun on .190 produces `inspected=N rendered=N errors=0` smoke output. Any `thumbnail.unidentified` warning triaged. Sample 5-10 catalog cards on retina viewport devtools to verify gallery tier serves at ~150-500 KB band. Re-run HAR-analog capture on share-view carousel to verify 503 rate ≪ pre-tier baseline. **Verifiable:** smoke log captured + carousel HAR-analog showing ≥80% drop in 503 count vs pre-tier baseline.

**Share-view security hardening (Epic 23):**

- **FR16-BLOB-CACHE-1: Share-view blob cache hardened against StrictMode refcount leak + revocation invalidation gaps.** `acquireShareBlob` at `apps/web/src/routes/share/$token.tsx:88-148` tracks inflight subscribers in `_pending: Map<string, number>` count map; resolve handler uses `_pending[src]` as initial refCount (revoke + skip cache if 0 — all unmounted). Page-mount-scoped invalidation: clear `_shareBlobCache` + `_shareBlobInflight` on `/share/$token` route unmount. **Verifiable:** deterministic mounting test mocks StrictMode double-mount + asserts refCount converges to 0 + URL revoked when consumers unmount with inflight load.
- **FR16-STL-PREVIEW-LOCK-1: STL preview previews source-tracked + single-flight lock.** `workers/render/render/worker.py:render_stl_previews` source-tracks by STL sha256 (boring-tech choice): `ModelFile.original_name = f"<view>-{stl_sha256[:8]}.png"`. Worker counts only previews matching CURRENT primary STL's sha256. Single-flight Redis SETNX lock with TTL=300s at share router dispatch: `lock_key = f"share:stl_preview_lock:{stl_for_preview}"`. **Verifiable:** race-condition contention test: spawn 2 concurrent share-view requests; assert only ONE arq job enqueued.
- **FR16-RATELIMIT-PER-TOKEN-1: NEW per-share-token request-count rate-limit middleware.** Per-token sliding window via Redis ZADD/ZREMRANGEBYSCORE/ZCARD on key `share_token_ratelimit:<token>`. Configurable env: `SHARE_PER_TOKEN_RATELIMIT_PER_MINUTE` (default 60 per operator 2026-05-24), `SHARE_PER_TOKEN_RATELIMIT_WINDOW_SECONDS` (default 60). 429 response with `Retry-After` header on overage. Composable with Story 19.1 per-IP middleware: BOTH checks fire; EITHER overage returns 429. **Verifiable:** pytest fixture exercises both legs independently + operator pen-test from `ezop-kbk.ddns.net` per [[reference_external_test_source]] AFTER deploy.

**Test infrastructure hygiena (Epic 24):**

- **FR16-TEST-HELPERS-1: Centralized `_admin_token` test helpers in `apps/api/tests/_test_helpers.py`.** Exports `admin_token(user_id)`, `agent_token(user_id)`, `member_token(user_id)` reading `get_settings().jwt_secret` (NOT hardcoded constant). 13 test files migrated to import + use centralized helpers (file list per SCP §4.3). Reference pattern: Story 18.4 `be11035` + `2ae6569`. Pure refactor; no behavior change in any test. **Verifiable:** full pytest 846+/846+ PASS deterministic 3× consecutive (NFR16-DETERMINISM-1 sub-clause).

**Mobile UX (Standalone Story 25.1):**

- **FR16-MOBILE-DRAG-1: Mobile photo-reorder drag works on touch devices.** Tailwind `touch-none` (= `touch-action: none`) added to `DragHandle` button at `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:244-253`. On touch devices, vertical drag now reorders rows without scrolling the page; touching outside the grip area (`flex-1` button) still scrolls naturally (preserves scroll-reach UX). **Verifiable:** agent-browser touch viewport emulation + operator hands-on verify on phone.

### Non-Functional Requirements

- **NFR16-PERF-1: Gallery tier blob size ≤500 KB for typical phone-photo inputs.** Pytest fixture exercises Pillow pipeline with representative samples (3000×4000 JPEG, 4000×3000 JPEG, 2000×3000 PNG with alpha) and asserts gallery output ≤500 KB per sample. Designer may tune target dimensions during Story 22.3 UX session — final value locked into Story 22.1 spec AC. **Verifiable:** test fixture in `apps/api/tests/test_thumbnail_pipeline.py` runs in <5s and passes for all sample categories.
- **NFR16-DETERMINISM-1: Cross-framework test-suite determinism contract carried forward from Init 10-11.** Vitest + pytest + playwright visual all pass deterministically across 3 consecutive invocations after each Init 16 story merge. Story 24.1 carries explicit 3× consecutive full-pytest determinism gate (846+/846+ PASS). Forward-applicable: any future test flake observed requires immediate root-cause + permanent fix (no `retry: 3`, no skip-tag, no per-story flake-investigation cycles).
- **NFR16-VISUAL-VERIFICATION-1: Pre-CR agent-browser visual-verification gate on every UI-touching Init 16 story.** Applies to: 22.2 (carousel main-frame gallery tier — both ShareCarousel + CardCarousel surfaces), 22.3 (NEW symmetric fullscreen viewer — baselines CREATED on both routes), 25.1 (mobile photo-reorder touch viewport). Stories 22.1, 22.4, 23.1, 23.2, 23.3, 24.1 are backend / test-infrastructure / pure-state changes — gate does NOT apply. **Verifiable:** Dev Agent Record per affected story documents agent-browser smoke pass with screenshot citation.
- **NFR16-SECURITY-1: Story 23.3 per-token rate-limit ships with explicit threat-vector enumeration in spec.** Enumerate: share-token leak vectors (referrer header, log, screenshot share, copy-paste-then-redistribute), IP-pool attacker scenarios (per-IP cap defeated by botnet → per-token cap catches), retry-after backoff exploitation, share-scoped DDoS multiplier. Codex review on `gpt-5.5` (security class) per [[feedback_codex_model_routing]]; round-2 fix-up if P1/P2 surface.
- **NFR16-SCOPE-DESIGNER-GATE-1: Story 22.3 spec authoring gated by designer UX session output.** Designer (`bmad-agent-ux-designer` Sally subagent) produces inline UX spec block covering modal pattern, gallery tier dimensions, trigger pattern, mobile gesture support, i18n keys BEFORE `bmad-create-story` finalizes Story 22.3 spec. Operator surface during session: voice-heavy questions surface via Claude as proxy (per [[feedback_voice_heavy_dedicated_grilling]] dedicated-grilling rule); operator otherwise not interrupted.

### Decisions

- **Decision W** (architecture): Gallery tier variant pipeline shape (see `architecture.md` § Initiative 16 Decision W).
- **Decision X** (architecture): Blob cache hardening shape — StrictMode refcount + revocation policy A (see `architecture.md` § Initiative 16 Decision X).
- **Decision Y** (architecture): Per-token rate-limit middleware shape (see `architecture.md` § Initiative 16 Decision Y).

### Out of scope (intentional)

- **TB-017 — TOTP_FERNET_KEY rotation runbook.** Date-deferred 2027-05-20.
- **TB-026 sub#1-5 — share-view UX enrichment.** OUT per [[feedback_share_view_scope_boundary]] (post-Init-12 share view terminus). TB-037 fullscreen viewer is the deliberate image-quality exception.
- **TB-032 — `?variant=thumb2x` retina pipeline.** Subsumed by TB-037.
- **TB-022 — Viewer3DInline `srcOverride` hook.** ALREADY SHIPPED via Init 13 Story 20.3.

### Cross-references

- Predecessor: Initiative 15 — closed 2026-05-23.
- Source SCP: `sprint-change-proposal-2026-05-24-init16.md`.
- Architecture extension: `architecture.md` § Initiative 16 (Decisions W + X + Y).
- Epics extension: `epics.md` § Initiative 16 (E22 + E23 + E24 + S25.1).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-22 / epic-23 / epic-24 / 25-1-mobile-photo-reorder-touch-action.
- Memory entries informing this initiative: [[feedback_itcm_autonomous_mode]], [[feedback_voice_heavy_dedicated_grilling]], [[feedback_share_view_scope_boundary]], [[feedback_default_to_bmad_workflow]], [[feedback_scp_pre_enumeration_phase]], [[feedback_codex_model_routing]], [[feedback_frontend_visual_verification]], [[feedback_security_vector_enumeration]], [[feedback_pre_merge_gate_checklist]], [[feedback_pytest_timeout]], [[feedback_shared_cache_in_react]], [[feedback_worker_single_flight]], [[feedback_collaboration_division]], [[reference_external_test_source]].
- Triage cross-reference: 9 candidates promoted (TB-030 + TB-033 + TB-034 + TB-035 + TB-036 + TB-037 + TB-038 + TB-026 sub#6 per-token + TB-027 verify); 1 housekeeping flip (TB-029 backlog status → done per Init 13 Story 20.2 reconciliation); 1 new TB candidate filed (TB-039 — Init 11-15 H2 backfill housekeeping); 2 declined-defer (TB-017 + TB-022 already shipped); 1 subsumed (TB-032 by TB-037).

## Initiative 17 — Post-Init-16 Operator Hands-On Findings + Housekeeping Sweep

**Status:** 🚧 planning (started 2026-05-24, same session as Init 16 close-out). Source SCP: `sprint-change-proposal-2026-05-24-init17.md` (status `approved`). Init 17 = focused follow-up sweep clearing the Init 16 close-out tail (5 operator-hands-on findings) plus catch-up housekeeping (TB-039 Init 11-15 H2 backfill). Three epics E26+E27+E28 plus Standalone Story 29.1, ~7 stories total. All items P2/P3, boring-tech fix-shapes, no security/data-integrity class.

### Functional Requirements

- **FR17-VIEWER-SCALE-1**: Fullscreen image viewer scales to fit available main-frame area, preserving aspect ratio, with strip + nav chevrons always in viewport. `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` main flex container gets `min-h-0` shrink-fix; main image className uses `max-h-[calc(95vh-5rem)] max-w-full object-contain` to subtract strip height (`h-20` = 5rem). **Verifiable:** visual baselines refresh + operator manual verify on 4k/8k portrait + landscape images.
- **FR17-CAROUSEL-THUMB-1**: ModelGallery (catalog detail) thumb strip URLs append `?variant=thumb` mirroring Story 22.2 share-side pattern. Main frame stays on `galleryUrlFor` (Story 22.2 baseline). **Verifiable:** HAR capture shows strip thumbs serve WebP (`?variant=thumb` → `.thumb.webp` sibling) not original 4-8 MB blob.
- **FR17-SHARE-CONCURRENCY-1**: `acquireShareBlob` in `apps/web/src/routes/share/shareBlobCache.ts` enforces max 4 concurrent in-flight fetches; overflow queued via promise chain. Composes with Story 23.1 generation guard (semaphore wraps fetch, not generation check). Resolves Init 12 carry-forward TB-036 root cause where carousel mount could burst-launch 8+ fetches → nginx `limit_conn share_anon_conn 5` rejected with 503. **Verifiable:** vitest SEMAPHORE-1 (8 concurrent calls → only 4 in-flight; remaining 4 release sequentially) + SEMAPHORE-2 (release fires on rejection).
- **FR17-BACKFILL-DIAGNOSTIC-1**: `thumbnail.unidentified` + `gallery.unidentified` warnings emit `model_file_id=%s storage_path=%s` inline in message body. Structured `extra={"labels.model_file_id": ..., "labels.storage_path": ...}` preserved for GlitchTip compatibility. **Verifiable:** re-run backfill on .190; operator captures file_id via container-stdout grep on `model_file_id=`.
- **FR17-TOOLBAR-ALIGN-1**: AddModelButton vertical-baseline aligns with search input baseline in CatalogList toolbar. **Verifiable:** visual baseline + screenshot comparison vs `tmp/add_model_misalligned.png`.
- **FR17-VIEWER-GESTURE-1**: ImageFullscreenViewer onTouchStart switches from `strip.contains(e.target)` (Story 22.3 round-2) to coordinate-based `stripOrigin` flag (computed via `stripRef.current?.getBoundingClientRect()` + comparing touch `clientY` to strip vertical bounds). onTouchEnd suppresses `step()` when `start.stripOrigin === true`. Preserves Story 22.3 round-3 `pointer-events-none` on hidden strip (orthogonal fix; works together). **Verifiable:** manual touch verify — hidden-strip-area drag should restore chrome (NOT navigate) AND visible-strip horizontal drag should scroll natively (NOT navigate).
- **FR17-DOC-BACKFILL-1**: Init 11 / 13 / 14 / 15 H2 sections appended to canonical `prd.md` + `architecture.md` + `epics.md` from source SCP `sprint-change-proposal-2026-05-23-init-11-15.md`. Init 12 already present. Init 15 (meta + deferred) minimal coverage. **Verifiable:** `grep '## Initiative 1[1345]'` returns hits in all 3 canonical docs.

### Non-Functional Requirements

- **NFR17-VISUAL-VERIFICATION-1**: Stories 26.1 (viewer scaling — regen `catalog-detail-image-viewer-open-*` 8 PNGs) + 26.2 (catalog-detail strip — regen `catalog-detail-*` 8 PNGs likely near-zero-diff) + 28.1 (toolbar align — regen `catalog-list-*` PNGs) carry agent-browser visual baseline regen per [[feedback_frontend_visual_verification]]. Hook-context PASS matches standalone.
- **NFR17-DETERMINISM-1**: Carries forward Init 10-16 cross-framework determinism. Vitest 426+/426+ PASS (424 baseline + 2 from Story 27.1 semaphore + 0-2 from other stories) deterministic 3× consecutive. Pytest 911+/911+ PASS deterministic (no regression on Story 27.2 logging-only change).

### Decisions

- **Decision Z** (architecture): Share-view concurrency semaphore shape — cap=4, promise-chain queue overflow, composes with Story 23.1 generation guard. See `architecture.md` § Initiative 17 Decision Z.

### Out of scope (intentional)

- **TB-017** — TOTP_FERNET_KEY rotation runbook. Date-deferred 2027-05-20.
- **TB-041** (mentioned only, not yet formally filed) — stl_preview orphan cleanup. Defensive; defer.
- **TB-042** (mentioned only, not yet formally filed) — main-frame next/prev prefetch. YAGNI for current operator catalog (≤15-photo shares typical).

### Cross-references

- Predecessor: Initiative 16 — closed 2026-05-24 (aggregate retro at `init-16-retro-2026-05-24.md`).
- Source SCP: `sprint-change-proposal-2026-05-24-init17.md`.
- Architecture extension: `architecture.md` § Initiative 17 (Decision Z).
- Epics extension: `epics.md` § Initiative 17 (E26 + E27 + E28 + S29.1).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-26 / epic-27 / epic-28 / 29-1-init-11-15-h2-backfill.
- Memory entries: [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]], [[feedback_codex_model_routing]] (gpt-5.4-mini all stories), [[feedback_frontend_visual_verification]], [[feedback_pre_merge_gate_checklist]], [[feedback_docs_hygiene]] (Story 29.1 closes Init 11-15 H2 backfill debt), [[feedback_share_view_scope_boundary]] (Story 27.1 is bug-fix not UX iteration), [[feedback_autonomous_sleep_on_budget]] (family-time clause active per Init 16 update).
- Triage cross-reference: 7 candidates promoted (TB-039 + TB-043 + TB-044 + TB-045 + TB-046 + TB-047 + TB-048); 4 housekeeping stale-marker flips (TB-018, TB-022, TB-023, TB-032 — all already DONE in prior initiatives).


## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Source SCP: `sprint-change-proposal-2026-05-25-init18.md` (status `approved` 2026-05-25). Init 18 = post-ship use-case-enumeration-gap correction sweep: the `/share/<token>` feature shipped under an implicit anonymous-only recipient assumption. Real recipient population includes member-with-active-session (B5) who today gets the degraded anonymous view. Init 18 completes the membership-path decision tree without touching anonymous share-view CONTENT (per [[feedback_share_view_scope_boundary]] terminus policy, amended 2026-05-25 with explicit chrome+enrich-in-place carve-out). Single epic E30, three stories, all P2 (UX-gap, not security/data-integrity class). Phase B (anonymous CONTENT parity) deferred as future-initiative candidate.

### Overview

Brainstorming session 2026-05-25-0030 + Sally UX recommendation produced 3 render modes for `/share/<token>`:

1. **Anonymous share-view** (B1/B2/B3/B4/B6 — engineering-collapse: "session cookie absent OR session cookie invalid"): existing share-view, UNCHANGED CONTENT, with new chrome additions (LangToggle + ThemeToggle + Sign in button).
2. **Enriched member share-view** (B5 — engineering: "session cookie valid + user has access to model"): canonical catalog detail UI at `/share/<token>` URL, full member chrome (TopBar + ModuleRail), plus dismissible info-bar pointing at `/catalog/$id`.
3. **Request-access page** (B7 — future, granular sharing not yet implemented): deferred, no story in Init 18.

### Functional Requirements

- **FR18-SHARE-RESOLVE-1**: New authenticated endpoint `GET /api/me/share-links/<token>/resolve` returns `{model_id: UUID, access: "granted"}` HTTP 200 for valid token + authenticated caller with access to model. **Verifiable:** pytest RESOLVE-1 (happy path 200), RESOLVE-2 (401 unauthenticated), RESOLVE-3 (404 invalid token), RESOLVE-4 (404 expired token, uniform with RESOLVE-3 per token-status-enumeration protection), RESOLVE-5 (404 revoked token, uniform).
- **FR18-SHARE-RESOLVE-2**: The new endpoint MUST NOT change the existing `/api/share/<token>/*` public family (NFR10 credentialless contract preservation, per [[feedback_share_view_scope_boundary]] amended carve-out language). **Verifiable:** pytest CONTRACT-1 (no `Depends(current_user)` added to any `/api/share/<token>/*` route via grep + endpoint dep introspection).
- **FR18-FE-CONDITIONAL-RENDER-1**: `/share/<token>` route renders `MemberShareView` when `useAuth().isAuthenticated === true`, `AnonymousShareView` (current behavior) otherwise. **Verifiable:** vitest CR-1 + CR-2 + Playwright `share-anonymous-with-signin.spec.ts` + `share-member-enriched.spec.ts`.
- **FR18-MEMBER-SHARE-VIEW-1**: `MemberShareView` calls the resolve endpoint to obtain `model_id`, then renders the canonical `/catalog/$id` component tree (ModelHero + ModelGallery + STL list + description + member actions) wrapped in AppShell + TopBar + ModuleRail. URL stays `/share/<token>` (no redirect; brainstorm rα-1 mitigation by design). **Verifiable:** Playwright `share-member-enriched.spec.ts` × 4 projects compares `/share/<token>` (auth) vs `/catalog/$id` (auth) — identical except for info-bar presence.
- **FR18-INFO-BAR-1**: Dismissible info-bar at top of main content area: "Otworzyłeś ten model z linku udostępnionego. [Otwórz w katalogu]". Dismissal state in `sessionStorage` keyed `share-context-dismissed:<modelId>`. **Verifiable:** vitest IB-1 (renders on first visit), IB-2 (hidden after dismiss), IB-3 (re-shows for different `<modelId>`), IB-4 (re-shows in new session).
- **FR18-RETURN-URL-1**: Sign in button navigates to `/login?next=/share/<token>` (using existing `next` query param from Story 11.3 / AppShell anonymous-redirect convention). Post-login navigation honors `next` per existing `/login` route handling. **Verifiable:** Playwright RU-1 (Sign in click → URL contains `next=%2Fshare%2F...`); existing login tests already verify `next` honoring (no new test needed there).
- **FR18-CHROME-ADDITIONS-1**: Share-view header gains `<ThemeToggle />` + `<LangToggle />` + `<SignInButton />` in a right-aligned control group, mirroring TopBar order. Desktop ≥ 640px: single row with banner text. Mobile < 640px: Sign in button wraps below brand+banner; toggles stay right-aligned icon-only. **Verifiable:** Playwright `share-anonymous-with-signin.spec.ts` × 4 projects (desktop-light/dark + mobile-light/dark).

### Non-Functional Requirements

- **NFR18-SHARE-ANON-CONTRACT-1**: NFR10 credentialless contract on `/api/share/<token>/*` MUST stay intact. New auth-bearing endpoint lives under separate prefix `/api/me/share-links/<token>/resolve`. Pre-merge grep invariant: `Depends(current_user)` MUST NOT appear in `apps/api/app/modules/share/router.py`. **Verifiable:** AC-grep in Story 30.1 pre-merge invariants.
- **NFR18-TOKEN-ENUMERATION-1**: Resolve endpoint MUST return uniform 404 for invalid / expired / revoked tokens (no distinct error codes that would leak token-state to a brute-force probe). Same convention as Init 6 Story 6.4 invite token contract. **Verifiable:** pytest RESOLVE-3 / -4 / -5 all assert identical response body and headers.
- **NFR18-VISUAL-VERIFICATION-1**: All three stories carry visual baseline regen per [[feedback_frontend_visual_verification]] + Story 5.13 Baseline Acceptance Gate. New baselines bundled in same commit as the producing change; reviewer sign-off per FR13 commit-message rule.
- **NFR18-I18N-PARITY-1**: 5 new i18n keys MUST appear in BOTH `en.json` and `pl.json` (project-context.md i18n rule). Polish diacritics correct. Pre-merge grep invariant: every new key present in both files with non-empty value.
- **NFR18-DETERMINISM-1**: Carries forward Init 10-17 determinism contract. Vitest + pytest 3× consecutive identical pass counts after each story merge.

### Decisions

- **Decision AA** (architecture): Authenticated share-resolve endpoint prefix — `/api/me/share-links/<token>/resolve`, NOT `/api/share/<token>/resolve`. Preserves NFR10 credentialless contract on existing public family. See `architecture.md` § Initiative 18 Decision AA.
- **Decision AB** (architecture): `/share/*` AppShell chrome bypass policy — conditional based on `useAuth()` result. Anonymous + loading → bypass (existing minimal header); authenticated → full AppShell (TopBar + ModuleRail), enabling Variant γ enrich-in-place. See `architecture.md` § Initiative 18 Decision AB.
- **Decision AC** (UX): Info-bar dismissal persistence — `sessionStorage` per-modelId (Sally Decision 3, operator-approved 2026-05-25). See `architecture.md` § Initiative 18 Decision AC.

### Out of scope (intentional)

- **Phase B (anonymous CONTENT parity)** — description placement parity, multi-STL listing parity, fullscreen 3D viewer for anonymous. Future-initiative candidate; would require full reversal of terminus policy + own brainstorm pass.
- **B7 future granular sharing** ("request access" page) — defer until granular-sharing feature exists.
- **B6 disabled-account handling beyond fall-through to anonymous** — defer until disabled-account usage data exists.
- **Multi-tab race / session-expiry-mid-view / mid-session account creation** (brainstorm α-3, α-4, α-6) — handle ad-hoc per operator's Phase 2 decision.
- **Cross-cutting edge cases x-1 through x-8** (history-leak, OCR-typed URL, group-chat propagation, bot crawling, phishing, link revocation mid-view, dual-link from two senders, WebView session isolation) — handle ad-hoc.
- **Multi-button SHARE / intent declaration at link-generation time** (Path β, killed at Brainstorm Phase 1).
- **Self-serve registration CTA on share-view** (C5, ruled out).
- **Native-app handoff** (C7, ruled out).
- **Action-bridge UI** (C8, covered by portal-native flows).
- **Audit emission on resolve endpoint** — read-only operation, mirrors `share` read-pattern (no audit per Init 6 convention). If operator later wants audit for "who-resolved-what" telemetry, it's a follow-up TB.

### Cross-references

- Predecessor initiative: Initiative 17 — closed 2026-05-24 (aggregate retro at `init-17-retro-2026-05-24.md`).
- Source SCP: `sprint-change-proposal-2026-05-25-init18.md`.
- Architecture extension: `architecture.md` § Initiative 18 (Decisions AA + AB + AC).
- Epics extension: `epics.md` § Initiative 18 (Epic E30 + Stories 30.1 + 30.2 + 30.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-30 / 30-1-* / 30-2-* / 30-3-*.
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md`.
- UX input: `_bmad-output/ux/share-flow-membership-path-ux.md`.
- Memory entries: [[feedback_share_view_scope_boundary]] (amended 2026-05-25 with carve-out), [[feedback_feature_proposal_use_case_enumeration]] (this initiative is the canonical correction precedent), [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]], [[feedback_codex_model_routing]] (gpt-5.4-mini for FE stories, gpt-5.5 for Story 30.1 due to NFR-SECURITY adjacency per [[feedback_security_vector_enumeration]]), [[feedback_frontend_visual_verification]], [[feedback_pre_merge_gate_checklist]], [[feedback_auth_boundary_contract_audit]] (Story 30.1 touches auth boundary — new authenticated endpoint adjacent to public bypass family).
- Triage cross-reference: zero NEW TB filings by Init 18 (gap was surfaced 2026-05-24 and went straight to brainstorming → UX → correct-course; no intermediate triage step needed). Phase B registered in `triage-backlog.md` as future-initiative candidate.


## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)

**Status:** 🚧 planning (started 2026-05-29). Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md` (status `approved` 2026-05-29, operator Polish explicit approval "Akceptuję i idziemy dalej"). Init 19 is the first portal initiative to integrate the standalone Spoolman instance at `.190:7912` as a read-only inventory mirror, surfaced via a new `/spools` route + a landing-page low-stock card. Single epic E31, ~5 stories (31.1–31.5), all `gpt-5.4-mini` Codex routing (no NFR-SECURITY adjacency — read-only outbound HTTP to a LAN-only homelab service). Brainstorm source: `_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md` (118 distinct ideas across 6 techniques; 15-parameter morphological grid; MVP-A baseline cell selected; OD1–OD10 register resolved). Phase B (catalog ↔ filament linkage), Phase C (restricted writes), Phase D (cost calc UX), Phase E (share-token inventory snapshot) parked with explicit precondition triggers (see § Out of scope).

### Overview

The 2026-04-29 portal v1 design and the 2026-05-04 Source-of-Truth design both explicitly *punted* Spoolman integration as out of scope, with `docs/superpowers/specs/2026-05-04-portal-source-of-truth-design.md:46` saying verbatim: *"Filament cost calculator / Spoolman integration (separate brainstorm)"*. AGENTS.md and `docs/architecture.md:45` both tag a `modules/spools/` "v2 slot" as the integration destination but provide zero detail beyond that. `apps/web/src/routes/spools/index.tsx` ships a `ComingSoonStub` rendering "Spools / Filamenty" with no backing implementation. The operator's daily-driver workflow today involves a separate browser tab to `http://.190:7912/` whenever inventory questions arise, completely disconnected from catalog browsing.

Init 19 is the *separate brainstorm* the 2026-05-04 design referenced. It establishes the integration template (httpx client + Redis cache + arq poll job + soft-fail UX) cleanly so future Phase B/C/D/E inherit the template without ripping it out. MVP-A scope is **read-only visibility only**: no mutation surface (operator keeps the direct Spoolman UI for adding spools/filaments; future Laura-delegated tasks also use the direct UI per operator decision 4), no catalog-filament linkage, no cost calculator UX — but cost-data IS carried end-to-end in MVP-A DTOs per Decision AF so future Phase D can light up without a portal-side schema backfill.

Verified Spoolman facts at brainstorm session start: instance running 0.23.1 on `.190` port 7912, 9 active spools + 16 filaments + 2 vendors, two real low-stock spools (PLA Speed Matt White 138.9g + PCTG Army Green 163.2g) — MVP-A is demoable on day-one with real signal.

### Functional Requirements

- **FR19-LOWSTOCK-1**: Landing page surfaces a "Low stock" card listing active spools with `remaining_weight` below a configurable threshold (default 200g; env-tunable). Card visible to all authenticated users (members + admin) — NOT admin-only (operator decision 2, overrides brainstorm Black Hat default). **Verifiable:** vitest + Playwright visual baseline showing the two real low-stock spools at session start (or whatever the live state is).
- **FR19-SPOOLS-VIEW-1**: `/spools` route renders an inventory list of active spools + active filaments (mirroring Spoolman's filament-vs-spool distinction per OD9). Members + admin both visible. No mutation affordances. **Verifiable:** vitest + Playwright visual × 4 projects.
- **FR19-CACHE-1**: Cache topology per Decision AD — Redis 30s TTL on the `spools:summary:v1` canonical key + arq 60s poll job `poll_spoolman_summary` + Redis SETNX leader-election lock `spools:poll-lock` (90s expiry; prevents thundering herd if multiple API workers run). **Verifiable:** backend pytest exercising cache hit/miss + lock contention.
- **FR19-FAILURE-1**: When Spoolman is unreachable, the landing card and `/spools` view display the last cached snapshot with an explicit "Last updated HH:MM (Xm ago)" indicator (P6b soft-fail; brainstorm Black-Hat risk mitigation). Never render 500. If cache is empty (cold-start + Spoolman down), render an explicit "Spoolman unavailable" empty state. **Verifiable:** vitest with mocked-down upstream + Playwright visual of the stale state.
- **FR19-DATA-CARRY-1**: Cached DTOs surface ALL Spoolman cost-relevant fields end-to-end (Filament: `price`, `weight`, `spool_weight`; Spool: `price`, `spool_weight`, `remaining_weight`, `initial_weight`, `used_weight`) per Decision AF. The MVP-A UX does NOT compute cost; it carries the data so future Phase D can light up without portal-side backfill. **Verifiable:** `api-types.gen.ts` diff shows the fields; backend pytest schema invariant.

### Non-Functional Requirements

- **NFR19-NETWORK-1**: Portal-api MUST reach Spoolman via internal docker network per Decision AE (P4b primary; P4a fallback as one-line transitional posture). MUST NOT expose Spoolman through `nginx-180` edge. **Verifiable:** configs-side compose diff + portal-side env config grep for `SPOOLMAN_URL`.
- **NFR19-OBS-1**: Every Spoolman client call tagged `external_service=spoolman` per `~/repos/configs/docs/observability-logging-contract.md`; OTel span around the httpx call; GlitchTip breadcrumb category `spoolman.client`. Response bodies NOT logged at INFO (brainstorm anti-pattern 8). **Verifiable:** pre-merge grep invariant on `external_service=spoolman` presence + entity-count-only log assertion.
- **NFR19-DETERMINISM-1**: Carries forward Init 10-18 determinism contract. Vitest + pytest 3× consecutive identical pass counts after each story merge. arq poll job idempotent (brainstorm anti-pattern 1 + 11 — leader-election prevents double-poll).
- **NFR19-I18N-PARITY-1**: All new `modules.spools.*` i18n keys present in BOTH `en.json` and `pl.json` with Polish diacritics correct (~12 keys: landing-card title + threshold copy + index page strings + soft-fail "Last updated" copy + empty-state + error-state). Material names PCTG / PETG / PLA / TPU stay untranslated (P15c).
- **NFR19-VISUAL-VERIFICATION-1**: New visual baselines for the landing low-stock card (4 projects) + `/spools` index page (4 projects) + soft-fail state of the landing card (4 projects). Total ~12 PNGs across ~3 specs. Baseline-reviewed sign-off per FR13 pre-commit hook.

### Decisions

- **Decision AD** (architecture): Cache topology + poll cadence + leader-election + observability — Redis 30s TTL on `spools:summary:v1` + arq 60s poll job + Redis SETNX `spools:poll-lock` (90s) + `external_service=spoolman` tag on every client call. Embedded cache-coherence table for the single `["spools", "summary"]` query-key (per [[feedback_scp_pre_enumeration_phase]] § B discipline + Init 18 round-7 lesson). See `architecture.md` § Initiative 19 Decision AD.
- **Decision AE** (architecture): Network transport — primary topology P4b internal docker network (`http://spoolman:8000/api/v1/*`) requires a configs-side coordination PR attaching Spoolman to `portal-network`; P4a host-network fallback (`http://localhost:7912/api/v1/*`) is a one-line transitional posture if the configs PR slips. Same `SPOOLMAN_URL` env var wraps both shapes. P4c (nginx-fronted Spoolman) and P3d (Spoolman auth) rejected for LAN-only context. See `architecture.md` § Initiative 19 Decision AE.
- **Decision AF** (architecture): Data-model carry-through — backend DTOs (`apps/api/app/modules/spools/models.py`) for `SpoolView` and `FilamentView` surface ALL cost-relevant Spoolman fields end-to-end (Filament: `price`, `weight`, `spool_weight`; Spool: `price`, `spool_weight`, `remaining_weight`, `initial_weight`, `used_weight`, `first_used`, `last_used`, `archived`, `lot_nr`). Frontend `api-types.gen.ts` mirrors via OpenAPI generation. MVP-A UX uses only the visibility subset (qty + status + % remaining bar); broader fields are CARRIED so Phase D (cost calc UX) lights up without backfill. See `architecture.md` § Initiative 19 Decision AF.

### Out of scope (intentional; precondition triggers documented)

- **Phase B — catalog detail × material match (free-form text)**. Trigger: operator wants per-model material context on catalog detail page. ~2 stories on top of MVP-A.
- **Phase C — `recommended_material_profile` SoT structure**. Trigger: catalog SoT design round picks up filament linkage (blocks on SoT-side decision).
- **Phase D — cost calculator UX**. Trigger: operator wants per-print cost rollup on catalog detail or queue entry. MVP-A's Decision AF carry-through means zero backfill cost when triggered.
- **MVP-D — restricted writes (use / measure)**. Trigger: direct Spoolman UI ergonomic regression for operator OR Laura (per operator decision 4: NOT triggered by mere usage telemetry). Anti-pattern 3 from brainstorm Reverse phase reinforced.
- **MVP-E — share-token inventory snapshot**. Trigger: operator wants to advertise printable-right-now stock to an external recipient. Independent of Phase B/C/D.
- **Multi-instance support, websocket subscription, anonymous read of `/spools`, vendor pricing extension, in-portal Spoolman compose ownership** — all explicitly out of MVP-A.

### Cross-references

- Predecessor initiative: Initiative 18 — Phase A in-flight; Init 19 queues behind Init 18 close-out per ITCM autonomous mode convention.
- Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md`.
- Architecture extension: `architecture.md` § Initiative 19 (Decisions AD + AE + AF).
- Epics extension: `epics.md` § Initiative 19 (Epic E31 + Stories 31.1 + 31.2 + 31.3 + 31.4 + 31.5).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-31 / 31-1-* / 31-2-* / 31-3-* / 31-4-* / 31-5-*.
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md`.
- Configs-side coordination: `~/repos/configs/docker-compose-recipes/spoolman.yml` PR per Decision AE — **NOT a 3d-portal commit**; HC2 trip-wire honored (portal repo never edits configs files).
- Memory entries: [[feedback_scp_pre_enumeration_phase]] (cache enumeration discipline + magic-constant contract rule applied to Decision AD + staleTime/gcTime/Redis-TTL justifications), [[feedback_codex_model_routing]] (gpt-5.4-mini for all Init 19 stories — no NFR-SECURITY adjacency, no public-bypass family adjacency, no auth boundary changes), [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]], [[feedback_vanilla_bmad_first]] (H2-append pattern is canonical brownfield workaround per AGENTS.md vanilla-first subsection).
- Triage cross-reference: zero NEW TB filings by Init 19 SCP-authoring step. Pre-pass `init-19-readiness` (TB-050 + TB-051) closed 2026-05-29 (sprint-status.yaml `init-19-readiness: done`) — promoted cache-coherence enumeration + magic-constant contract rule into `[[feedback_scp_pre_enumeration_phase]]` and bookkeeping into triage-backlog.md before this Spoolman SCP was authored, so the SCP itself leverages the new discipline (cache-coherence table embedded in Decision AD).

## Initiative 20 — STL Slicer Estimates (Per-Part MVP)

**Status:** 🚧 planning (started 2026-05-31). Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` (status `approved` 2026-05-31 — operator delegation to continue downstream BMAD planning after the discovery + SCP commit; approval is scoped to planning-artifact appends, NOT to code implementation — implementation planning remains BLOCKED per SCP § 5). Init 20 introduces trustworthy, reproducible **per-STL** slicer estimates (print time, filament mass/length/volume, informational cost) by running a real headless OrcaSlicer slice in a containerized worker and parsing the g-code metadata. Single epic E32, 6 stories (32.1-32.6). Brainstorm source: `_bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md` (71 ideas across 6 techniques; CLI feasibility proved on the Fenrir WSL bench for PLA + TPU). Predecessor: Initiative 19 (Spoolman) — Init 20 queues behind Init 19 close-out per ITCM convention and consumes Spoolman as the filament inventory SoT it established.

### Overview

Estimate queries today require manual math (filament weight × assumed cost/g) or a separate Orca GUI invocation; the 2026-05-04 portal Source-of-Truth design explicitly punted per-STL estimates as out of scope, and this initiative is the promised discovery-then-build follow-up. Init 20 produces a **per-STL** estimate keyed to exactly the inputs that affect it, cached so it only recomputes when something meaningful changes. A request/basket total is a **linear sum** of per-STL estimate × quantity — there is **no whole-plate / whole-basket slicing**, because plate packing introduces arrangement as a variable, destroys per-part attribution, and is the wrong tool for a friends-&-family request assistant. The portal is a printer/admin tool and request assistant, **not e-commerce**: "cost" is an informational owner-side figure derived from the slice, never a quote or checkout price.

The estimate is **reproducible** (same STL + same resolved bundle ⇒ same numbers, via input hashing + source-profile snapshots), **attributable** (every record names the `*_settings_id` lines from the g-code), and **invalidatable** (STL edit, bundle re-tune, Orca upgrade, or a mapped Spoolman override change marks it stale and queues recompute rather than silently serving wrong numbers). Two object families are deliberately separated: the thin, human-meaningful **`PrintIntentPreset`** (user-facing — material class, quality tier, optional overrides) and the concrete resolved **`SlicerProfileBundle`** (internal — the full machine/process/filament JSONs Orca actually consumes). The separation isolates the user-facing surface from Orca version churn and profile re-tuning.

Verified feasibility at brainstorm session start (CLI spikes on Fenrir WSL, OrcaSlicer 2.3.2 Linux AppImage): a PLA slice of `Qstool.stl` (resolved Creality K1 Max MicroSwiss HF + Rosa3D PLA Starter + 0.20 mm) produced 76.76 g / 61.90 cm³ / 25735.79 mm / 3h35m47s / cost 4.60 with a *floating cantilever* warning; a TPU slice (Rosa3D Flex 96A + 0.20 mm TPU FlowTech) produced 77.25 g / 8h06m05s with `filament_max_volumetric_speed` 2.8. All required g-code metadata lines are confirmed present. Adaptive layer height returned a **proven negative** (`adaptive_layer_height=1` did not change the layer-Z schedule or estimates) and is therefore **gated** out of MVP.

### Functional Requirements

- **FR20-RESOLVER-1**: A profile resolver produces CLI-acceptable resolved bundles by recursively merging the Orca system profile tree with the user partials (user wins on conflict), injecting the top-level `type`, dropping the instantiation field that breaks the CLI, applying the Spoolman-mapped override layer, validating against a real `--info` / minimal-slice smoke check, then computing `bundle_hash` and writing a `SlicerProfileBundle` + `SourceProfileSnapshot`. Raw Orca user partials are CLI-rejected (proven — `--datadir` does not fix it), so the resolve step is **mandatory**, not optional. **Resolver precedence (load-bearing):** exact bundle > custom override > material-class default > unsupported (a request that resolves to "unsupported" is an explicit classified failure, never a silent fallback). **Verifiable:** backend pytest on the merge/normalize/validate path (PLA + TPU fixtures) + a hash-stability assertion (canonicalized JSON ⇒ stable `bundle_hash`).
- **FR20-ESTIMATE-1**: A per-STL `EstimateRecord` carries `time_seconds`, `filament_g`, `filament_mm`, `filament_cm3`, `filament_cost` (informational), `settings_ids` (attribution), classified `warnings`, and `status` (`fresh`/`stale`/`queued`/`failed`), attributable to the exact resolved bundle that produced it. Parsed from the confirmed-present g-code metadata lines by a small unit-testable pure function (g-code text in → typed struct out; time strings like `3h35m47s` normalize to seconds; missing/garbled lines ⇒ classified failure, never a silent zero). **Verifiable:** backend pytest on the parser with fixtures captured from the proven PLA + TPU slices.
- **FR20-CACHE-1**: Estimates are cached keyed `(stl_hash, bundle_hash)` — and since `bundle_hash` folds in `orca_version` and the Spoolman-override set, that 2-tuple is the complete reproducibility key. Stale records are served with an explicit `stale` flag and queued for recompute (deduped on the key so two requests for the same part+bundle don't slice twice); recomputing a `fresh` record is idempotent. **Verifiable:** backend pytest on cache hit/miss + dedup + staleness transitions.
- **FR20-FAILURE-1**: When the slicer worker is unreachable or a slice fails, the estimate surface soft-fails — it shows the last cached estimate with an explicit "Last estimated HH:MM (Xm ago)" indicator (mirroring the Init 19 Spoolman soft-fail pattern), and a never-estimated part shows an explicit "couldn't estimate, here's why" state rather than vanishing. Slice **warnings** (e.g. *floating cantilever*) are captured and surfaced **non-blocking**; slice **failures** (non-manifold mesh, Orca non-zero exit, parse failure, timeout) set `status: failed` + reason. **Verifiable:** vitest with mocked-down worker + backend pytest on the failure-classification branches.
- **FR20-SPOOLMAN-MAP-1**: A `PrintIntentPreset` (or a per-request line) MAY pin a specific Spoolman filament record; optional custom filament/process overrides — **especially `filament_max_volumetric_speed`, nozzle/bed temps, and density for TPU and unusual filaments** where the generic class default is wrong — are mapped from the Spoolman `filament.extra` fields onto the resolved filament JSON and folded into `bundle_hash` via `spoolman_overrides_ref`. Spoolman remains the inventory source of truth (Init 19 contract); the slicer initiative consumes filament records and the `filament.extra.url` purchase link, it does not own or duplicate inventory. **Verifiable:** backend pytest asserting a mapped-field change re-hashes the bundle and marks dependent estimates stale.
- **FR20-PRESET-1**: A user-facing `PrintIntentPreset` selector (material class ∈ {PLA, PETG, PCTG, TPU}, quality tier, optional pinned spool/overrides) drives estimate display on the catalog detail + request/queue surfaces; the preset is the **stable user-facing contract** and MUST NOT leak Orca internals (no raw layer-height floats, no `filament_max_volumetric_speed` in the UI). The preset → `SlicerProfileBundle` mapping lives entirely server-side. **Verifiable:** vitest on the selector + an invariant test asserting no Orca-internal field names appear in the rendered preset surface.

### Non-Functional Requirements

- **NFR20-REPRODUCIBLE-1**: Hash-driven invalidation on STL change / bundle re-tune / Orca version change / Spoolman mapped-override change. **Cost-only changes recompute arithmetically (no re-slice)** — `cost = mass × price/gram` is pure post-slice arithmetic, so a Spoolman price tick must NOT trigger a minutes-long re-slice (the single most important efficiency rule; Pre-Mortem flagged "re-slicing on every price tick" as the top self-inflicted-DoS risk). **Verifiable:** backend pytest proving a cost-only Spoolman change recomputes the cost field without invoking the slicer worker, in <1s.
- **NFR20-CONTAINER-1**: Orca runs headless in a **containerized slicer-worker** (OrcaSlicer 2.3.2 AppImage + the verified GL/GTK dep set); there is **no production dependency on Fenrir** — Fenrir `.100` WSL is the research/export bench only. Bench-only paths (`/mnt/c/Users/ezope/...`, the Fenrir AppImage path) MUST NOT appear in production runtime config; production paths are container-internal cache roots + the `.190`-mirrored STL source. **Verifiable:** configs-side compose diff (slicer-worker service) + a portal-side grep invariant that no `/mnt/c` path appears in production config.
- **NFR20-ATTRIBUTION-1**: Every `EstimateRecord` names which printer/filament/process settings produced it (`{filament,print,printer}_settings_id` from the g-code) so an estimate can always be traced back to a resolved bundle. **Verifiable:** backend pytest schema invariant on the `settings_ids` field.
- **NFR20-RESOURCE-1**: Slice concurrency is bounded (small cap, likely 1-2 on `.190`) to avoid starving the API/render workers; combined with the cost-only-arithmetic rule this prevents a recompute-storm CPU DoS. **Verifiable:** worker-config assertion on the concurrency cap + the dedup test from FR20-CACHE-1.
- **NFR20-OBS-1**: Every slicer-worker job and any outbound Spoolman read is instrumented per `~/repos/configs/docs/observability-logging-contract.md` (structured-log tags, OTel span, GlitchTip breadcrumb); g-code is parse-and-discard (not logged in full). **Verifiable:** pre-merge grep invariant on the observability tags.
- **NFR20-DETERMINISM-1**: Carries forward the Init 10-19 determinism contract — vitest + pytest 3× consecutive identical pass counts after each story merge; the arq slice job is idempotent on the `(stl_hash, bundle_hash)` key.
- **NFR20-I18N-PARITY-1**: All new `modules.estimates.*` / `modules.slicer.*` i18n keys present in BOTH `en.json` and `pl.json` with correct Polish diacritics (preset labels, quality-tier copy, soft-fail "Last estimated" copy, warning/failure states). Material names PLA / PETG / PCTG / TPU stay untranslated (Init 19 P15c precedent).
- **NFR20-VISUAL-VERIFICATION-1**: New visual baselines for the estimate display + `PrintIntentPreset` selector + soft-fail / warning / failure states across the 4 Playwright projects, with `baseline-reviewed:` sign-off per the FR13 pre-commit hook.

### Decisions

- **Decision AH** (architecture): Resolver architecture — recursive Orca system+user inheritance merge, `type` injection + instantiation drop, Spoolman override layer, real-slice validation, canonicalized `bundle_hash` over machine ∥ process ∥ filament ∥ `orca_version`, append-only/versioned bundles, `SourceProfileSnapshot` for provenance. Folding `orca_version` into the hash makes an Orca upgrade a clean bulk-invalidation event. See `architecture.md` § Initiative 20 Decision AH.
- **Decision AI** (architecture): Slicer-worker container — containerized headless OrcaSlicer 2.3.2 AppImage in a **dedicated** `slicer-worker` service (OD-2; leaning dedicated over extending `workers/render/` because of the GL/GTK dep bloat + minutes-long-vs-sub-second failure profile). Job contract is the `(stl_ref, bundle_ref)` 2-tuple; STL cache layout `<root>/stl/<hash[:2]>/<hash>.stl`; g-code parse-and-discard (OD-5 leaning). Configs-side compose PR owns the container/network topology (NOT a 3d-portal commit). See `architecture.md` § Initiative 20 Decision AI.
- **Decision AJ** (architecture): Cache / invalidation / cost arithmetic — `EstimateRecord` keyed `(stl_hash, bundle_hash)` with an exhaustive recompute-trigger table; **cost-only Spoolman changes recompute arithmetically without re-slicing** (OD-7; the load-bearing efficiency rule). See `architecture.md` § Initiative 20 Decision AJ.

### Open decisions — load-bearing set RESOLVED 2026-05-31 (operator delegation)

Carried from the brainstorm OD register; the load-bearing ones were surfaced here per the SCP § 4.1 handoff. **The five load-bearing decisions (OD-1, OD-2, OD-7, OD-8, OD-9) are RESOLVED 2026-05-31** by operator delegation (Ezop / Michał, ITCM autonomous mode) using the safe defaults below — they match the prior brainstorm conversation and the already-ratified architecture Decisions AH/AI/AJ. **Resolving this gate authorizes (a) recording these resolutions and (b) authoring the Story 32.1 spec to `ready-for-dev`. It does NOT authorize dev-story execution / code implementation of any Init 20 story** — that remains BLOCKED pending an explicit operator go per SCP § 5. Stories 32.2–32.6 stay `backlog` and are authored individually by `bmad-create-story` at their own dev-entry time.

- **OD-1 — RESOLVED (intent/strength presets, NOT raw slicer params).** The user-facing `quality_tier` is a **strength / intent label**, never a raw slicer parameter. Initial canonical preset keys: **`aesthetic`, `standard`, `strong`**. Their concrete Orca process settings (walls / top / bottom / infill / pattern / layer height) live in the exported/resolved `SlicerProfileBundle` / Orca process-profile refs and are **operator-configurable**; the UI MUST NOT expose raw Orca internals (FR20-PRESET-1). Initial mapping *examples only* (NOT immutable product constants, NOT to be hard-coded): `aesthetic`/weak → low-wall / low-infill or a lightning-style process profile; `standard` → ~3 walls / 15% gyroid; `strong` → ~5 walls / 40% gyroid. The concrete process-profile refs are confirmed against the real Orca profiles at resolver-build time (Story 32.1); the enum *labels* are fixed here.
- **OD-2 — RESOLVED (dedicated `slicer-worker`).** A dedicated containerized `slicer-worker` service is the intended production shape. Do **not** extend `workers/render/` for Orca — the dependency / runtime / failure profile differs (GL/GTK dep bloat; minutes-long slice vs sub-second render). Ratified as Decision AI default.
- **OD-7 — RESOLVED (arithmetic recompute only).** A cost-only change recomputes the cost field **arithmetically** (`cost = mass × price/gram`); it never triggers a re-slice. Ratified as Decision AJ rule + NFR20-REPRODUCIBLE-1.
- **OD-8 — RESOLVED (`.190`-mirrored catalog/cache for MVP).** The MVP worker reads the existing `.190`-mirrored catalog / cache for catalog STLs. Ad-hoc request uploads (STLs not in the catalog SoT) are **future / gated** and MUST NOT block the MVP.
- **OD-9 — RESOLVED (dedicated `slicer` + `estimates` modules).** Backend code lives under a new `apps/api/app/modules/slicer/` (an `estimates` subpackage is acceptable only if the repo convention strongly prefers it); frontend under `apps/web/src/modules/estimates/`. Preserve the `PrintIntentPreset` (user-facing) vs `SlicerProfileBundle` (internal) separation. NOT folded into the `requests` v2 slot.

The remaining brainstorm ODs (OD-3..OD-6, OD-10) are implementation-phase / story-local and are resolved per-story by `bmad-create-story`, not in this gate.

### Out of scope (intentional; gated with explicit triggers)

- **Adaptive / variable layer height — GATED** on a proven negative result. **Spike exit criterion:** demonstrate a CLI-only path produces a *different, correct* layer schedule + estimate for a known part. The data model must not bake in "estimates assume uniform layer height" in a way that blocks a later variable-height bundle — but no MVP work goes here.
- **Whole-basket / whole-plate slicing & arrangement** — totals stay `Σ (per-STL estimate × qty)`.
- **Multi-printer optimization / printer auto-selection** — the preset (or its default) names the machine; the resolver does not "shop" for the fastest printer.
- **E-commerce** — no checkout, quoting engine, public pricing, or payment; cost is informational + owner-facing.
- **Live Fenrir dependency in production** — Fenrir is the research/export bench; profiles are exported once into vendored artifacts.
- **Retaining g-code / per-layer breakdowns for visualization** (OD-5) — parse-and-discard in MVP.
- **Additional material classes beyond PLA/PETG/PCTG/TPU** — additive post-MVP, no schema change.
- **Support-generation tuning UI / per-model mesh repair** — manifold/repair is an input-validation concern (Orca `--info` already reports manifold), not an MVP feature.

### Cross-references

- Predecessor initiative: Initiative 19 — Spoolman Read-Only Inventory; Init 20 queues behind Init 19 close-out per ITCM autonomous-mode convention and consumes the Spoolman inventory SoT it established.
- Source SCP: `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md`.
- Architecture extension: `architecture.md` § Initiative 20 (Decisions AH + AI + AJ).
- Epics extension: `epics.md` § Initiative 20 (Epic E32 + Stories 32.1 + 32.2 + 32.3 + 32.4 + 32.5 + 32.6).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-32 / 32-1-* … 32-6-* (Story 32.1 `ready-for-dev` after the 2026-05-31 OD-gate resolution + story-spec authoring; 32-2 … 32-6 stay `backlog`).
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md` (data model § 2, resolver § 3, slicer-worker § 4, invalidation § 5, gated capabilities § 6, OD register § 9, risk register § 8).
- Configs-side coordination: `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` PR per Decision AI — **NOT a 3d-portal commit**; HC2 boundary honored (portal repo never edits configs files).
- Memory entries: [[feedback_scp_pre_enumeration_phase]] (pre-enumeration + cache-topology + magic-constant contract discipline applies to every Init 20 story spec — esp. the resolver hash constants + cache TTLs + slice-concurrency cap).

## Initiative 21 — Admin-Managed Orca Process Profiles + User-Facing Selector Options

**Status:** 🚧 planning (started 2026-06-04). Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` (status `approved` 2026-06-04 — operator go: *"Ok, możemy ruszać z pracami"*; approval is scoped to planning-artifact appends, NOT to code implementation — implementation remains BLOCKED per SCP § 7). Init 21 gives the operator a first-class **admin panel to see, import, and manage Orca process/intent profiles**, and makes the **user-facing Files/STL selector expose only admin-approved + material-compatible options**. It builds directly on Initiative 20 (the resolver + the EST-TIERS-1 availability bridge) and supersedes the EST-TIERS-1 hand-placement workaround: the per-tier availability signal stops being "derived purely from disk presence" and becomes "derived from the admin-managed, compatibility-constrained profile inventory" — while the user-facing `GET /api/estimates/quality-tiers` `{quality_tier, available, reason}` contract is preserved. Single epic E33, 3 stories (33.1-33.3), **read-only inventory first**. Predecessor: Initiative 20 (STL Slicer Estimates, Epic E32 — shipped). Kanban continuity card: `t_ce1927cf`.

### Overview

Today Orca process/intent profiles — the load-bearing input to every per-part estimate — are managed **outside the product**: an operator hand-places exported JSON onto the `.190` portal-content volume under `SLICER_VENDORED_PROFILES_DIR`, in the fixed resolver layout `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` (`apps/api/app/modules/slicer/resolver.py:114-123`). There is no in-product way to see what is installed, import a new profile, or expose a new quality tier to users. Only `standard.json` exists for the catalog printer/material, so a member who picks **Aesthetic** or **Strong** would hit a classified `unsupported_material_class` resolve failure (`resolver.py:226`) → HTTP 422; the EST-TIERS-1 bridge currently hides that by disabling those tiers in the selector (`GET /api/estimates/quality-tiers`, `router.py:101-131`). Init 21 turns that hand-placement + disk-presence gate into an admin-managed surface.

The initiative is deliberately **process/intent profiles only** — printer + print-quality recipes. It is **NOT** filament inventory, ordering, spool availability, or cost (that is Spoolman / Init 19, a separate SoT); a Spoolman *override* still layers onto a resolved filament at resolve time (Story 32.5), and the admin panel neither owns nor duplicates it. It must **preserve existing estimate / provenance safety**: the content-addressed `bundle_hash`, the append-only bundle/estimate stores, the `source_system_tree_hash` provenance snapshot (`resolver.py:300-309`), and the loud-classified resolver failures are invariants this initiative builds on, never edits.

**The grid is fixed, but NOT uniformly populated.** OD-1 was resolved by the operator (2026-06-04) to the **fixed `{aesthetic, standard, strong} × {PLA, PETG, PCTG, TPU}` enum grid** (the named FE↔BE `QualityTier` / `MaterialClass` contract — `QUALITY_TIER_ORDER` at `router.py:51`, `QUALITY_TIERS` at `apps/web/src/modules/estimates/lib/preset.ts:25`), **with an explicit material/filament-class ↔ process-profile compatibility mapping** layered over it. Some `(material_class, quality_tier)` cells are legitimately *incompatible* and must never be offered: TPU is specific enough to require dedicated, declared-compatible process profiles, so a PLA/PETG-derived process slot must never be surfaced as TPU-valid even if it happens to resolve. The load-bearing rule is therefore **offerable = imported ∧ resolvable ∧ compatible** — resolvability is necessary but not sufficient.

### Functional Requirements

- **FR21-PROFILE-INVENTORY-1** (read slice — Story 33.1): An admin-only read of the managed profile inventory returns, per `(printer_ref, material_class, quality_tier)` slot, `{imported, resolvable, compatible, reason, portal_label, provenance}` where `provenance` projects from the resolved bundle's snapshot (`source_system_tree_hash`, `orca_version`). It reuses the EST-TIERS-1 `resolve_preset` resolvability logic and the `VendoredProfileSource` provenance — **no new resolve logic**, just an admin-facing superset projection — plus the compatibility map (FR21-COMPAT-1) to compute `compatible` and the structured `reason` for a resolvable-but-incompatible slot. Mounted under the existing admin router (`prefix="/api/admin"`, `apps/api/app/modules/admin/router.py:29`), admin-gated, absent from `_PUBLIC_ROUTES`. **Verifiable:** backend pytest asserting (a) non-admin → 403, (b) `resolvable`/`reason` parity with `GET /api/estimates/quality-tiers` for the same printer/material (shared one-source-of-truth assertion), (c) no Orca-internal keys / file paths / g-code leak into the DTO.
- **FR21-COMPAT-1** (compatibility map — Stories 33.1 read-only / 33.2 enforce): A first-class **material/filament-class ↔ process-profile compatibility mapping** over the fixed grid declares which process (quality-tier) slots are valid for a given filament/material class. **Neither the admin panel nor the user selector ever offers an incompatible material/process combination** (e.g. TPU only offers TPU-compatible process profiles; a PLA-class process profile occupying a TPU slot is shown as **not offerable** with an explicit incompatibility reason, never as "available"). The map is an **explicit declaration, not implied by file presence** — `offerable = imported ∧ resolvable ∧ compatible`. The admin panel surfaces per-slot compatibility **status + human-readable reason** (not imported / not resolvable / incompatible for this material class). Representation/enforcement is Decision AK (OD-7); the concrete per-material compatible-slot set (e.g. which slots are TPU-compatible) is admin-data confirmed at the PRD/data phase. **Verifiable:** a shared test asserts the projection feeding the user selector excludes incompatible slots (so neither surface can offer a TPU-incompatible process choice for TPU, nor vice-versa).
- **FR21-PROFILE-IMPORT-1** (write slice — Story 33.2): A validated import path accepts an Orca intent triple, validates it via the existing `resolve()` merge/normalize/required-keys path (structural resolvability, OD-3) **AND** validates material/process compatibility (FR21-COMPAT-1 / OD-7), then writes the validated triple into the vendored intents tree (OD-2) so a previously-gated tier becomes genuinely available — **only for compatible slots**. An import targeting an incompatible slot is **rejected with a clear structured reason** and is NOT published. Mirrors the existing admin multipart-upload + audit pattern (`apps/api/app/modules/sot/admin_router.py` upload + `record_event`). **Verifiable:** backend pytest asserting (a) an incompatible-slot import is rejected and never exposed, (b) after a successful compatible import the slot resolves and the inventory read (FR21-PROFILE-INVENTORY-1) reflects it, (c) the import is audit-logged.
- **FR21-SELECTOR-1** (user-facing — Stories 33.1 projection / 33.2 end-to-end): The user-facing Files/STL process/material selector consumes the **admin-approved + compatibility-filtered** availability, built on EST-TIERS-1 — the availability *signal* gains a compatibility dimension while the `{quality_tier, available, reason}` DTO shape is preserved (`reason` carries the incompatibility cause). After a successful import the selector offers the newly-published slot **only if** it is compatible; an incompatible or compatible-but-unpublished slot is never a member-reachable choice. **Verifiable:** vitest asserting the selector never renders an incompatible `(material_class, quality_tier)` choice; selector parity with the inventory projection asserted by a shared test.

### Non-Functional Requirements

- **NFR21-PROVENANCE-1**: The initiative preserves the Init 20 reproducibility invariants — importing or managing a profile MUST NOT perturb the `bundle_hash` of an unrelated already-persisted bundle, and an admin write that mutates the system tree yields a *new* `source_system_tree_hash` snapshot identity automatically (`resolver.py:300-309` — the provenance mechanism was deliberately built for in-place edits of vendored profiles). The append-only bundle/estimate stores and the `bundle_hash` input order are not edited. **Verifiable:** backend pytest asserting an unrelated bundle's hash is byte-stable across an import, and that a system-tree mutation produces a distinct snapshot hash.
- **NFR21-NO-422-1**: No member-reachable resolve 422 — a tier is offered to a member only when it is `imported ∧ resolvable ∧ compatible`, so the selector cannot present a choice that resolves to a classified failure. This is the contract EST-TIERS-1 protected (disable-the-tier) carried forward into the admin-managed model (offer-only-offerable). **Verifiable:** backend + vitest asserting every member-offerable slot resolves successfully and no offered slot maps to `unsupported_material_class` / incompatible.
- **NFR21-UX-1** (UX-PROFILE-1 — required): Both frontend surfaces (the admin profile grid and the user-facing selector) are **UX-designed decision-support UIs over a constrained compatibility grid, not crude dropdowns or raw status dumps**. A UX designer (`bmad-ux` / Sally) designs the admin grid + the selector — including how an incompatible/unavailable slot is **disabled-with-explanation vs. hidden**, how the reason is communicated, and how an incompatible slot is visually distinguished from an available one — **before or alongside** the FE story work. UX-PROFILE-1 is an OPEN work item that blocks finalizing the selector + admin-grid FE acceptance criteria; it consumes the OD-7 compatibility-map contract (backend = source of truth) and designs the *surfacing*, not the rules. **Verifiable:** UX deliverable referenced by the FE story spec before its ACs are locked; FE story carries NFR21-VISUAL-VERIFICATION-1 baselines for the designed states.
- **NFR21-AUTH-1**: Every new `/api/admin/*` profiles route is admin-gated via the pre-baked `current_admin` dependency (`apps/api/app/core/auth/dependencies.py` — `admin_required` 403) and is absent from `_PUBLIC_ROUTES`, satisfying the Init 6 mechanical route-enforcement gate (`apps/api/tests/test_route_enforcement_gate.py`). **Verifiable:** the existing route-enforcement pytest passes with the new route present; a 403-for-non-admin test exists.
- **NFR21-OBS-1**: Profile import/manage writes go through `app.core.audit.record_event` (actions `slicer_profile.import` / `.delete`) and are instrumented per `~/repos/configs/docs/observability-logging-contract.md` (structured-log tags, OTel span). The read inventory is a normal instrumented GET. No Orca-internal profile bodies or g-code are logged in full. **Verifiable:** pre-merge grep invariant on the audit action + observability tags.
- **NFR21-I18N-PARITY-1**: All new `modules.admin.profiles.*` / selector compatibility-reason i18n keys are present in BOTH `en.json` and `pl.json` with correct Polish diacritics (compatibility status/reason copy, import/reject copy). Material names PLA / PETG / PCTG / TPU stay untranslated (Init 19/20 precedent).
- **NFR21-VISUAL-VERIFICATION-1**: New visual baselines for the admin profile grid (offerable vs. not-offerable-with-reason states) and the selector compatibility behavior across the 4 Playwright projects, with `baseline-reviewed:` sign-off per the FR13 pre-commit hook. Gated on the UX-PROFILE-1 design.
- **NFR21-DETERMINISM-1**: Carries forward the Init 10-20 determinism contract — vitest + pytest 3× consecutive identical pass counts after each story merge.

### Decisions

- **Decision AK** (architecture): Admin-managed profile **inventory read + compatibility-map representation & enforcement** — a managed-inventory read projected over the existing resolver (`resolve_preset` resolvability + `VendoredProfileSource` provenance), and the OD-7 compatibility map as a first-class explicit declaration extending the named FE↔BE `QualityTier`/`MaterialClass` contract (backend = source of truth, FE mirrors it, parity-tested). `offerable = imported ∧ resolvable ∧ compatible`. See `architecture.md` § Initiative 21 Decision AK.
- **Decision AL** (architecture): Profile **import write posture + on-disk metadata** — validated import (structural `resolve()` ∧ compatibility) writes the intent triple directly into `SLICER_VENDORED_PROFILES_DIR/intents/...` (OD-2; in-place edit, provenance-snapshot-safe), with admin metadata in an **on-disk sidecar manifest** (portal label, importer, timestamp, original filename, per-slot compatibility status/reason) + the existing admin audit log; **no Alembic migration in v1** (OD-4 — matches the slicer subsystem's no-DB posture). Configs-side portal-content RW-volume coordination is a write-slice-only HC2 boundary item. See `architecture.md` § Initiative 21 Decision AL.

### Open decisions — OD-1 RESOLVED (operator 2026-06-04); OD-2..OD-7 safe defaults applied

- **OD-1 — RESOLVED (operator, 2026-06-04): fixed grid + compatibility mapping.** Admin fills/exposes the existing `{aesthetic, standard, strong} × {PLA, PETG, PCTG, TPU}` slots; "admin-approved labels" = admin controls *availability* of the existing named tiers, NOT free-text relabeling. The grid carries an explicit compatibility map binding which process slots are valid per material class (TPU example). Arbitrary free-text tier taxonomy remains **deferred** (would churn the FE↔BE `QualityTier` named contract — large/risky).
- **OD-2 — safe default: write the validated intent triple in-place** into `SLICER_VENDORED_PROFILES_DIR/intents/...` (one source of truth; provenance snapshot binds content hash on in-place edits). Staging/approval two-step deferred. **Write slice only**; needs configs RW-volume coordination (HC2). Read slice unaffected.
- **OD-3 — safe default: structural resolvability** for import validation (run the existing `resolve()` merge/normalize/required-keys with the default `NullCliValidator`) — availability == resolvability is the live contract. Real-Orca CLI validation (worker-only) is an optional async follow-up.
- **OD-4 — safe default: on-disk sidecar manifest** for admin metadata (consistent with the no-DB / append-only slicer subsystem) + reuse the existing admin audit log. **No Alembic migration in v1.**
- **OD-5 — safe default: no multi-printer.** v1 manages profiles for the single existing `slicer_default_printer_ref` / `CATALOG_ESTIMATE_PRINTER_REF`. A printer registry is a separate future initiative.
- **OD-6 — safe default: no re-slice in the read slice; optional in the write slice**, gated on the estimate parser/backfill pipeline being healthy (EST-PARSE-1). Import can reuse the existing EST-RECOMPUTE-1 `POST /api/estimates/recompute` per (stl_hash, preset) rather than a new bulk enqueue.
- **OD-7 — safe default (confirm representation at arch/data phase): the compatibility map is a first-class explicit declaration** — resolvability is necessary but not sufficient; a cell is offered only when BOTH structurally resolvable AND declared compatible. Lives alongside the fixed-grid contract (per-material allowed-tier table; backend SoT, FE mirrors, parity-tested — mirroring `QUALITY_TIER_ORDER` ↔ `QUALITY_TIERS`). The admin sidecar manifest records per-slot compatibility status + reason. Concrete TPU-compatible slot set is admin-data, deferred to the data phase. Detailed in Decision AK.

### Out of scope (intentional; deferred with named triggers)

- **Arbitrary admin-defined tier labels / free-text taxonomy** — OD-1 resolved to the fixed enum grid + compatibility mapping, NOT free-text relabeling.
- **Printer registry / multi-printer management** — stays single default printer ref (OD-5).
- **Real-Orca slice-validation at import time** — structural resolvability only (OD-3); real-Orca CLI validation is an optional worker-only follow-up.
- **Any change to Spoolman inventory / cost** — process/intent profiles only; Spoolman stays the inventory SoT (Init 19).
- **Any change to the `bundle_hash` input order or the append-only bundle/estimate stores** — those are preserved invariants (NFR21-PROVENANCE-1).
- **Bulk re-slice / backfill on import** — deferred (OD-6), gated on EST-PARSE-1; reuse EST-RECOMPUTE-1 if needed.

### Cross-references

- Predecessor initiative: Initiative 20 — STL Slicer Estimates (Epic E32, shipped). Init 21 builds on its resolver + the EST-TIERS-1 availability bridge and supersedes the EST-TIERS-1 hand-placement workaround.
- Source SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` (status `approved` 2026-06-04). Kanban: `t_ce1927cf`.
- Architecture extension: `architecture.md` § Initiative 21 (Decisions AK + AL).
- Epics extension: `epics.md` § Initiative 21 (Epic E33 + Stories 33.1 + 33.2 + 33.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-33 / 33-1-* … 33-3-* + ux-profile-1-* (all `backlog`).
- UX work item: **UX-PROFILE-1** (`bmad-ux` / Sally) — REQUIRED for the admin grid + user selector surfaces (NFR21-UX-1); blocks the FE story ACs. See SCP § 9.
- Superseded bridge: EST-TIERS-1 (`_bmad-output/implementation-artifacts/deferred-work.md`) — the disk-presence-derived quality-tier availability gate becomes admin-managed.
- Memory entries: [[feedback_scp_pre_enumeration_phase]] (pre-enumeration + magic-constant contract discipline applies to every Init 21 story spec — esp. the compatibility-map representation and any import size/validation constants).
