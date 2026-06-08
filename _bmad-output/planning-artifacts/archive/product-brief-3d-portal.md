---
title: "Product Brief: 3d-portal — Self-Hosted Home 3D-Printing Catalog, AI-First by Design"
status: "complete"
created: "2026-05-15"
updated: "2026-05-15 (post-guided-elicitation revision — replaces 2026-05-15 autonomous draft)"
scope: "Initiative 0 / Product Foundation — retrospective brief documenting the actual portal product (v1 shipped, modules: catalog/auth/share/admin/sot/runbook). Backfilled because the original 2026-05-09 BMAD chain jumped straight to Initiative 1 (GlitchTip delta) and never wrote a foundation brief for the portal itself. This revision was elicited from Ezop via bmad-product-brief guided flow (Stage 3, 3 rounds, ~10 questions) — earlier autonomous draft is superseded."
inputs:
  - docs/project-overview.md
  - docs/source-tree-analysis.md
  - docs/architecture.md
  - docs/operations.md
  - docs/design/2026-04-29-portal-design.md
  - docs/plans/2026-04-29-portal-v1-implementation.md
  - README.md
  - _bmad-output/project-context.md
  - Ezop guided elicitation 2026-05-15 (bmad-product-brief Stage 3)
voice_validation: "Persona, problem framing, success criteria stance, vision, and exclusions reflect Ezop's explicit answers in 2026-05-15 elicitation. 'What makes this special', user journeys, and tech-stack-implied sections remain Claude synthesis from existing docs."
---

# Product Brief: 3d-portal — Self-Hosted Home 3D-Printing Catalog, AI-First by Design

## Executive Summary

3d-portal is a self-hosted web portal where Ezop's personal 3D-printing model collection lives, polished enough to be a daily-driver for the household and structured enough to be operated by AI agents (Claude Code, Codex, future Gemini) as a first-class user. The portal is reachable at `https://3d.ezop.ddns.net` via homelab DDNS, gated by edge nginx basic-auth for household members, and runs on a single Docker host (`.190`) with an nginx edge LXC (`.180`) in front.

**The portal is the product, not the catalog data.** Catalog metadata + STL/photo binaries are the substrate; the value is in the catalog being browseable from anywhere, share-able to a single recipient outside the household, audit-trail-bound for admin actions, and — load-bearing — **directly operable by AI agents via a documented HTTP surface** (`/agent-runbook`, `/openapi.json`, cookie + password agent flow, `glitchtip-triage.sh` BMAD bridge). The design from the 2026-04-29 spec already treated AI agents as a primary surface, not a bolt-on.

v1 shipped: catalog browse with 3D STL viewer (three.js), JWT-gated admin with audit log, share-link lifecycle with TTL, async render pipeline (4 isometric thumbnails via `trimesh` + `matplotlib`), and the agent surface. This Initiative 0 documents that foundation retrospectively so Initiatives 1-3 (GlitchTip delta, agent runbook enrichment, theme hardening) and future initiatives (Moonraker, Spoolman, member-print-requests, print queue, etc.) layer on a documented base instead of an implicit one.

**One thing this brief makes explicit that earlier docs didn't:** there is **no fixed v1 "done" target**. The maintainer's stance — captured in his own words during this brief's elicitation — is that each shipped capability surfaces the next one in his head. The portal is a portfolio of evolving capabilities, not a product with a finish line. Success criteria below reflect that.

## The Problem

Ezop wanted his 3D-printing model collection to feel like **a polished homelab tool he could open from his phone, share with friends, and let AI agents operate on** — not a folder tree on a Windows machine. Before the portal, the collection lived as a one-way `rsync` from `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` to a homelab server. It "worked" in the same way a backup tape works: data was preserved, but everything beyond preservation was missing.

The single concrete pain point that pushed v1 over the line: **metadata had nowhere to live, and browsing wasn't possible without RDP**. Tags, categories, prints log, external links — all of this had to be encoded in folder names or kept in a separate document. Looking up "did I print that fridge thing last year?" from a phone required SSH-ing into the server and `ls`-ing the rsync target. The catalog was *technically* accessible; it wasn't *practically* useable.

The other things that became possible once a portal existed — share links to friends, audit log of admin actions, AI-agent operation via documented API, in-browser 3D viewing — were not the trigger. They were the design pulling those capabilities forward because once you commit to building a real catalog tool, you commit to building it for everyone the catalog touches, **including the AI agents that Ezop increasingly delegates work to in 2026.**

## The Solution

**A four-part monorepo with the source of truth owned by the server, not the Windows folder.**

- **React 19 + Vite 6 + TanStack SPA** in `apps/web/` — the daily-driver UI. Catalog browse (list / grid / search / filter), per-model detail page (photos, renders, STL files, prints log, external links), in-browser 3D STL viewer (three.js + react-three-fiber, theme-token-driven materials), responsive (desktop + mobile, light + dark theme). Admin actions gated behind `<AuthGate>`. All HTTP through `api()` helper (CSRF + credentials + silent refresh). i18n in English + Polish, theme-token-driven dark mode that doesn't hard-code colors anywhere.
- **FastAPI on Python 3.12 in `apps/api/`** — the catalog SoT owner. Modules: `auth` (JWT + bcrypt + refresh-token rotation + CSRF middleware), `share` (public + admin), `admin` (CRUD over Model / ModelFile / Tag / Category / Print / ExternalLink / AuditLog), `sot` (agent reverse-sync via cookie + password — NOT bearer token), `runbook` (Markdown served at `/agent-runbook` for AI agents). SQLModel ORM with Alembic, 11 migrations, Postgres-ready.
- **arq render worker in `workers/render/`** — async thumbnail pipeline. `trimesh` opens STL, `matplotlib` renders 4 isometric views, output written back as `ModelFile` rows under the content volume. Triggered per-model from admin UI or bulk-enqueued via `infra/scripts/render-all.sh`. Job status TTL is 1h so it self-clears.
- **Docker Compose on `.190` + nginx edge on `.180`** in `infra/`. Edge nginx terminates DDNS TLS + household basic-auth + a location-rule bypass for `/share/*` so anonymous share-link recipients don't hit the password prompt. Content + state volumes survive container rebuilds. SQLite nightly backup with 30-day retention.

**The AI-agent surface is first-class, by design, from the 2026-04-29 spec onward.** Frontend errors flow to homelab GlitchTip with debug-ID symbolication (Initiative 1 layer); structured JSON logs follow the cross-repo `~/repos/configs/docs/observability-logging-contract.md`; OpenTelemetry distro 0.50b0 instruments FastAPI / Redis / SQLAlchemy → OTLP-HTTP exporter. AI agents read the catalog via OpenAPI (`/openapi.json`, enriched with operation IDs in Initiative 2) and the runbook (`/agent-runbook`), can triage a GlitchTip issue into a BMAD story stub via `infra/scripts/glitchtip-triage.sh`, and verify a deploy via `infra/scripts/verify-symbolication.sh`.

**Deploy is one command.** `bash infra/scripts/deploy.sh` builds images locally (BuildKit-secret-mounted `SENTRY_AUTH_TOKEN`), ships to `.190` via SSH, restarts compose, runs Alembic migrations. Every merge to `main` triggers it; doc-only commits skipped.

## What Makes This The Right Call

- **Server owns the SoT, not the Windows folder.** Reverse-sync direction matters — the portal DB + content volume are authoritative. The Windows tree is a bootstrap source, not a real-time mirror. This unblocks every metadata capability (tags, categories, prints log, audit log) because they have a real home.
- **AI agents are a designed user, not a bolted-on API.** The 2026-04-29 spec already had `/agent-runbook` + cookie-password agent role + the BMAD triage bridge in scope. Ezop's own 2026-05-15 framing: *"solo-dev coraz mniej — w czasach agentów wolę delegować bardziej doświadczonym."* The portal's HTTP surface is shaped around what AI agents need to read and write, not around what a human admin would tolerate.
- **Living-doc planning, not waterfall.** The PRD, architecture, and epics ledgers all use the "living initiatives" pattern — each new scope extends the same file, never forks. This brief is Initiative 0; Initiatives 1-3 are shipped/in-progress; the next one comes when Ezop has shipped enough of the current ones to surface the next idea. **Explicit stance:** there's no "done" target for the portal as a whole; only "done" for each initiative.
- **Future-proofing slots are real, not speculative.** `apps/web/src/routes/{queue,printer,spools,requests}/` and `apps/api/app/modules/queue/` are scaffolded as placeholders today. Ezop's confirmed 2026-05-15: **all four are real intent** for the 12-24 month horizon, gated on external dependencies (Moonraker-driven printer, Spoolman in the homelab, per-user auth decision for member-print-requests). Slots existing means when the gate trips, the route + module structure is already there.
- **One hard exclusion. Everything else is "not in current plans".** Multi-tenant is the only deliberate forever-exclusion. Public marketplace, print farm, mobile-native — none of these are *currently* in the plan, but Ezop hasn't ruled them out as a category. The brief reflects that ambiguity instead of pretending the exclusions are stronger than they are.

## Who This Serves

**Primary — Ezop, AI-loop operator and 3D-printing enthusiast.**

- Self-described: *"AI-loop operator + pasjonat druku 3D"*. Identity: someone who orchestrates AI agents to ship code, with home 3D printing as the domain the agents work in. "Solo dev" is increasingly past tense — *"w czasach agentów wolę delegować bardziej doświadczonym"*.
- Daily-driver use: browse catalog from desktop or phone (the **"aha moment"** — opening `/catalog` on his phone outside the house and finding a model he printed last year, rotating it in the 3D viewer); occasionally curate (tag, category, notes, prints log, external link); trigger renders when adding new models; review audit log when something seems off.
- Self-aware as a *"ciężki klient biznesowy"* — there's no defined finish line, each capability surfaces the next one in his head. The portal isn't a product with a launch and a sunset; it's a portfolio he'll keep extending.

**Secondary — household members (actively using).**

- Reach the portal through household basic-auth on edge nginx.
- Read-only catalog browse, no admin actions, no per-user account in v1.
- **Confirmed 2026-05-15: regular use.** The portal lets a household member say *"did you print that thing for the fridge already?"* and check themselves, without bothering Ezop.

**Tertiary — share-link recipients outside the household (sporadic use).**

- Receive a `/share/<token>` URL — bypasses basic-auth via nginx location rule, no JWT, no signup.
- View a single model's STL + photos + renders for as long as the Redis-backed token TTL allows.
- **Confirmed 2026-05-15: real use case, but practically sporadic.** The lifecycle works; the volume is low.

**Quaternary (first-class by design) — AI agents.**

- Claude Code, Codex, future Gemini sessions debugging or extending the portal.
- Consume the portal's HTTP API directly — read the catalog, manage share tokens, trigger renders, ingest new models via the `sot` module (cookie + password flow, **not** bearer token — 2026-05-10 correction stands).
- Read the self-served Markdown runbook at `/agent-runbook` to operate the URL → catalog model creation flow without leaving the portal context.
- Bridge production errors into BMAD planning via `glitchtip-triage.sh <issue_id>` → markdown story stub for `bmad-quick-dev` / `bmad-create-story`.
- **This is not "secondary": the design has weighted AI-agent ergonomics equally with human ergonomics from day one.** REST/curl/jq over UI clickability, CLI scripts over dashboards, pull-only over push notifications, structured logs over freeform output.

## Success Criteria

**Ezop's explicit stance, 2026-05-15:** *"Generalnie to na zasadzie 'używam i jest mi z tym dobrze' — ale ja nie widzę takiego docelowego stanu. W sensie: co zrobimy jedną funkcjonalność, to zaraz mi przychodzi do głowy kolejna. Więc obawiam się, że nie będzie takich Success targetów. Byłbym/jestem ciężkim klientem biznesowym."*

The portal succeeds, retrospectively, when the maintainer keeps using it as his daily driver and each of the three drivers behind v1 stays satisfied:

1. **Metadata + remote browse works.** Tags / categories / prints log / external links live in `portal.db`, not folder names. Catalog is browseable from desktop or phone over DDNS — the legacy "RDP to look at folder" workflow is retired.
2. **Sharing + audit works.** Share-link generation is one-click; the link reaches a non-household recipient without auth gymnastics; every admin write produces an `AuditLog` row queryable from the admin UI.
3. **AI-agent ergonomics works.** A fresh Claude Code or Codex session reads `/agent-runbook` + `/openapi.json` and performs catalog ingestion end-to-end without external documentation. `glitchtip-triage.sh <issue_id>` produces a usable BMAD story stub from a production issue ID.

**Beyond those three:** there are no fixed business metrics. v1 success was not gated on "user retention" or "issues opened in 30 days" or any other commercial proxy — those don't apply to a single-household homelab tool. The catalog being used + AI agents being able to operate it is the whole signal.

**What does NOT count as a success criterion** (and why):

- "**Adoption among household members**" — they use it (confirmed); past that, more use isn't a metric, just a nice property.
- "**Number of share-links generated**" — share-link use is sporadic by design; the lifecycle works whether it's invoked 0 or 50 times.
- "**Time-to-deploy / deploy frequency**" — every merge to `main` deploys; cadence is what the work demands, not a target.
- "**Error budget / SLO**" — single-host, household-scale; no SLA, no error budget concept.

## Scope

### MVP — Foundation v1 (shipped 2026-04)

Documented in detail in `docs/design/2026-04-29-portal-design.md`. Highlights:

- **Catalog module (web)** — list + grid + search + filter, detail page, 3D STL viewer, responsive layout, theme-token-driven light/dark.
- **Auth module (api)** — JWT + bcrypt + refresh rotation + CSRF middleware.
- **Admin module (api + web)** — full CRUD over catalog entities + audit log.
- **Share module (api + web)** — Redis-backed token TTL, nginx-bypass location rules, admin revoke.
- **Sot module (api)** — cookie + password agent flow, reverse-sync via `scripts/hydrate_local_tree.py`.
- **Runbook module (api)** — `/agent-runbook` Markdown endpoint.
- **Render worker** — `trimesh` + `matplotlib` 4-view pipeline.
- **Infra** — Docker Compose on `.190`, nginx edge on `.180`, BuildKit secrets, SQLite nightly backup, one-command deploy.
- **Observability baseline** — GlitchTip (web + api + worker), OTel distro 0.50b0, structured JSON logs.

### Growth Features (Post-MVP, layered as initiatives)

These are explicit pointers into the PRD initiatives ledger — each is a sibling H2 in `prd.md`:

- **Initiative 1 — Useful GlitchTip Delta** (✅ shipped 2026-05-10) — debug-ID symbolication + filter ruleset + verify ritual + triage bridge.
- **Initiative 2 — Agent Runbook + Legacy SoT Triage** (🚧 in progress) — `/agent-runbook` enrichment + OpenAPI operation-IDs + legacy folder triage.
- **Initiative 3 — UI Theme Compliance & Visual Regression Hardening** (🚧 in progress) — theme defect remediation + visual-regression gate hardening.

### Hard exclusions (deliberate, forever)

- **Multi-tenant.** Single household, single SoT, single admin. There will never be "Ezop's catalog vs. someone else's catalog" inside this product. This is the one architectural choice removing a class of complexity that won't be revisited.

### Not in current plans (but not ruled out forever)

These were *not* affirmatively excluded by Ezop in 2026-05-15 elicitation — there's no current intent to build them, but they're not a forever-no:

- **Public marketplace surface.** Share links are point-to-point today; whether the portal ever grows a discovery surface is undecided.
- **Print farm (multi-printer fleet management).** The future `printer/` slot is sized for a single Moonraker-driven printer; multi-printer fleet is not in plans but the door isn't closed.
- **Mobile-native app (React Native / Capacitor).** Responsive web is enough today; a native app isn't in the roadmap but isn't ruled out.

### Real future intent — all 4 future-proofing slots (confirmed 2026-05-15)

Each becomes its own Initiative when external gate trips:

- **Moonraker bridge** (`printer/` slot) — real intent. Gate: at least one Moonraker-driven printer running consistently in the homelab.
- **Spoolman bridge** (`spools/` slot) — real intent. Gate: Spoolman already deployed in the homelab compose stack (or scheduled to be).
- **Member-print-requests** (`requests/` slot + `User.role=member` + per-user auth) — real intent. Gate: per-user auth model decided (OIDC via existing homelab Authentik vs. native portal accounts).
- **Print queue / OpenSearch full-text / Postgres migration / HA** — real intent for the technical-flip group. Each gate is its own threshold: queue UX demand, SQLite text-search bottleneck, SQLite ceiling, acceptable-downtime budget change.

## Vision (12-24 months)

The portal becomes the single operational surface for Ezop's home 3D-printing workflow: catalog + print queue + printer telemetry + spool inventory + member-print-requests all in one polished homelab app, with **AI agents staying first-class consumers of every new surface**. Each new capability ships with an OpenAPI contract + a runbook section + (when it touches operations) a triage script.

Concretely, the 4 future-proofing slots get wired:

- **Moonraker bridge** — show live print progress per printer; queue jobs from the catalog detail page; surface print success/failure in the prints log automatically.
- **Spoolman bridge** — track filament inventory; link prints to spools used; surface low-stock warnings.
- **Member-print-requests** — household members log in (per-user accounts, not just collective basic-auth) and request a model be printed. Admin approves/declines.
- **Technical flips on demand** — Postgres swap when SQLite hits a ceiling, OpenSearch for full-text when SQLite text search becomes a bottleneck, HA if the single-host outage budget changes.

The end-state is not a fixed product. It's a portfolio of capabilities maintained at the cadence the operator's interest sustains — and explicitly: *"co zrobimy jedną funkcjonalność, to zaraz mi przychodzi do głowy kolejna"*.

## Maintenance posture

- **Owner-operator:** Ezop (solo, increasingly delegating to AI agents). No team, no human PR review process beyond `ultrareview` and `bmad-code-review` skills + Codex cross-LLM reviews. BMAD workflow + Claude/Codex review chain compensate for the absence of a human reviewer.
- **Deploy cadence:** every successful merge to `main` deploys to `.190` via `bash infra/scripts/deploy.sh`. Doc-only commits skipped.
- **Backup posture:** SQLite nightly cron at `/mnt/raid/3d-portal-state/backups/`, 30-day retention. Content volume (large binaries) is on RAID; no per-file backup beyond that.
- **Failure tolerance:** single-host failure (`.190` down) → portal offline until host recovery; acceptable for a household tool. No HA, no multi-region, no failover.
- **Stance on "done":** there isn't one. Each Initiative completes; the portal as a whole doesn't. New Initiatives surface as the operator's interest and external context shift.
