# 3d-portal Documentation Index

**Generated:** 2026-05-15 by `bmad-document-project` (initial scan, quick level).
**Purpose:** Primary navigation hub for AI agents and human readers reasoning about the portal.

---

## Project Overview

- **Type:** Monorepo with 4 parts (multi-part).
- **Primary languages:** TypeScript (frontend), Python 3.12 (backend + worker), Bash (infra scripts).
- **Architecture:** Service-oriented — React SPA + FastAPI + arq worker + Redis, behind edge nginx.
- **Deployment:** Self-hosted homelab (`.190` Docker host, `.180` nginx edge, DDNS `3d.ezop.ddns.net`).

### Quick Reference per part

#### web (`apps/web/`)

- **Type:** web
- **Tech stack:** React 19 + Vite 6 + TS 5.6 + TanStack Router 1.x + TanStack Query 5.x + Tailwind v4 + shadcn/ui + three.js 0.171 + Sentry SDK 8.x
- **Entry:** `apps/web/src/main.tsx`
- **Architecture pattern:** Component-based SPA with bounded-context module folders + TanStack file-style routes.

#### api (`apps/api/`)

- **Type:** backend
- **Tech stack:** Python 3.12 + FastAPI ≥0.115 + Pydantic 2.9 + SQLModel 0.0.22 + Alembic + Redis 5.2 + PyJWT + bcrypt
- **Entry:** `apps/api/app/main.py` (`create_app()` factory)
- **Architecture pattern:** Module-bounded API surface, one router per `app.modules.<name>`, JWT + CSRF middleware, SQLModel ORM.

#### worker (`workers/render/`)

- **Type:** backend (async job processor)
- **Tech stack:** Python 3.12 + arq + trimesh ≥4.5 + matplotlib ≥3.9 + Pillow ≥11
- **Entry:** `workers/render/render/` (arq job handlers)
- **Architecture pattern:** Redis-queued job consumer; depends on `portal-api` editable for shared SQLModel entities.

#### infra (`infra/`)

- **Type:** infra
- **Tech stack:** Docker Compose + nginx + Bash scripts
- **Entry:** `infra/scripts/deploy.sh`
- **Architecture pattern:** Compose stack on `.190`, edge proxy on `.180`, secrets via BuildKit mount.

---

## Generated Documentation

- [Project Overview](./project-overview.md) — capability inventory, user personas, deployment, future-proofing slots.
- [Architecture](./architecture.md) — component topology and integration points (pre-existing, kept as authoritative).
- [Source Tree Analysis](./source-tree-analysis.md) — annotated tree with critical-file pointers.
- [Operations Runbook](./operations.md) — deploy, backup, failure modes (pre-existing).

## Spec & Plans (pre-existing)

- [v1 Design Spec](./design/2026-04-29-portal-design.md) — full original design specification.
- [v1 Implementation Plan](./plans/2026-04-29-portal-v1-implementation.md) — what was scheduled to ship in v1.
- [GlitchTip Integration Design](./plans/2026-04-30-glitchtip-integration-design.md) — Initiative 1 source.
- [GlitchTip Integration Plan](./plans/2026-04-30-glitchtip-integration-plan.md) — Initiative 1 phased plan.
- [Agents Add-Model Runbook](./agents-add-model-runbook.md) — Initiative 2 runbook draft.
- [Acceptance Results](./acceptance-results.md) — v1 acceptance verification log.

## BMAD Planning Artifacts

Located under [`_bmad-output/planning-artifacts/`](../_bmad-output/planning-artifacts/):

- `prd.md` — living initiatives PRD (Initiative 1-3 as of 2026-05-15; Initiative 0 backfill pending).
- `architecture.md` — initiative-scoped architecture deltas.
- `epics.md` — E1-E5 (E0 backfill pending).
- `prd-validation-report.md` — PRD validation log.
- `product-brief-3d-portal.md` — **Initiative 0 / Product Foundation brief** (created 2026-05-15). Describes the actual portal product. Distillate at `product-brief-3d-portal-distillate.md`.
- `product-brief-3d-portal-glitchtip.md` — Initiative 1 (GlitchTip) brief. Originally named `product-brief-3d-portal.md`; renamed 2026-05-15 because its scope was the GlitchTip delta, not the portal product itself. Distillate at `product-brief-3d-portal-glitchtip-distillate.md`.
- `product-brief-3d-portal-ui-theme-hardening.md` — Initiative 3 brief. Distillate sibling.

## BMAD Implementation Artifacts

Located under [`_bmad-output/implementation-artifacts/`](../_bmad-output/implementation-artifacts/):

- `sprint-status.yaml` — current sprint state (epic + story status).
- `1-1-...` through `4-3-...` — story files for Epics 1-4.
- `spec-tb-*.md` — triage-backlog spec stubs (cross-story issues promoted to specs).
- `epic-{1,2,4,5}-retro-*.md` — epic retrospectives.
- `code-reviews/` — per-story review documents.

## Cross-repo references

- `~/repos/configs/docs/observability-logging-contract.md` — structured-log + trace contract (load-bearing).
- `~/repos/configs/docs/glitchtip-agent-guide.md` — GlitchTip REST recipes for AI agents.
- `~/repos/configs/nginx/3d-portal.conf` — edge nginx config (deployed via configs repo `sync.sh`).
- `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` — upstream catalog folder schema.
- `~/repos/orca-profiles/AGENTS.md` — Michał's git workflow conventions (shared across repos).

## Getting Started (for AI agents)

1. Read [`project-overview.md`](./project-overview.md) to understand WHAT the portal is and WHO it serves.
2. Read [`../_bmad-output/project-context.md`](../_bmad-output/project-context.md) to absorb the 136 implementation rules (must-respect when writing code).
3. Read [`architecture.md`](./architecture.md) for the component topology.
4. Read [`source-tree-analysis.md`](./source-tree-analysis.md) when you need to locate a specific concern.
5. Check [`../_bmad-output/implementation-artifacts/sprint-status.yaml`](../_bmad-output/implementation-artifacts/sprint-status.yaml) for what's in-flight before opening any new work.
6. Follow BMAD workflow routing: invoke `bmad-help` from `_bmad/_config/bmad-help.csv` if unsure which skill applies to your task.

---

## Verification recap

- Tests/extractions executed: pattern scan over `apps/`, `workers/`, `infra/`, `docs/`, `_bmad-output/`. Module + migration counts cross-checked against router files and `migrations/versions/`.
- Outstanding risks or follow-ups: none for this overview — the backfill chain (rename misnamed briefs → write product brief → add Initiative 0 to PRD → add E0 to epics → update architecture.md pointer) completed 2026-05-15.
- Recommended next checks: re-run `bmad-document-project` (deep-dive mode) when a new module/initiative materially changes the system shape — e.g., when the queue backend gets wired, when Moonraker/Spoolman bridges ship, or when SQLite gets flipped to Postgres.
