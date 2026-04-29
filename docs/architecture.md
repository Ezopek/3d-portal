# Architecture overview

This document condenses the system architecture. For the full design specification, see `docs/design/2026-04-29-portal-design.md`.

## Components

```
[Browser] ─https─▶ [nginx-180 (edge)] ─proxy─▶ [.190 docker-compose stack]
                         │                          │
                         │                          ├─ web   (nginx + React build)
                         │                          ├─ api   (FastAPI + Pydantic + SQLModel)
                         │                          ├─ worker (arq render queue)
                         │                          └─ redis (cache + queue + share tokens)
                         │
                  household basic auth
                  (bypass: /share/*)

[catalog-data volume]    ←─rsync─── [Windows / Nextcloud-synced 3d_modelowanie repo]
       (read-only)                    (source of truth, managed by Claude CLI)
[portal-renders volume]
       (worker writes, api reads)
[portal-state volume]
       SQLite + future uploads
```

## Container responsibilities

**Web container** — nginx serving the built React SPA (`dist/`), static assets only. Exposes `127.0.0.1:8080` on `.190` and is reverse-proxied by nginx-180.

**API container** — FastAPI on uvicorn. Reads catalog from read-only volume, serves files (STL/img with ETag), manages share tokens, JWT login, and audit log. Mounts catalog-data (ro), portal-renders (ro), and portal-state (rw). Talks to Redis.

**Worker container** — arq worker. Pre-renders thumbnails for models without `images/` using `trimesh` and matplotlib (4 views per model, written to the dedicated `portal-renders` volume). Mounts catalog-data (ro) and portal-renders (rw). Talks to Redis.

**Redis container** — share tokens with native TTL, render job queue, computed caches (facets, top-tag counts).

## Data sync direction

One-way Windows → `.190` rsync via `infra/scripts/sync-data.sh`. The catalog repo on Windows stays the single source of truth; the portal never writes back. After each sync, the script POSTs `/api/admin/refresh-catalog` to invalidate in-memory caches.

## Future-proofing slots

These are already in place for future expansion:

| Future feature | What's already in place |
|---|---|
| Postgres migration | SQLModel + alembic; flip `DATABASE_URL` |
| Print queue | `apps/api/app/modules/queue/`, `modules/queue/` in web; arq broker on Redis |
| Moonraker integration | `modules/printer/` slot; existing OTel collector; env var `MOONRAKER_URL` |
| Spoolman integration | `modules/spools/` slot; HTTP client to existing Spoolman compose |
| Print requests | `modules/requests/` slot; `User.role = member` in schema |
| Mobile photo upload | `POST /api/admin/models/{id}/prints` + new uploads volume + reverse rsync |
| WebSocket / SSE live updates | nginx-180 already has WS upgrade headers; Redis pub/sub ready |
| OIDC / SSO | Auth isolated in `core/auth/`; can be replaced with Authentik client |
| Full-text search backend | OpenSearch is already in homelab; portal can query `https://192.168.2.190:9200` |

## References

- `docs/design/2026-04-29-portal-design.md` — full specification
- `docs/plans/2026-04-29-portal-v1-implementation.md` — implementation plan
- `docs/operations.md` — deployment and operations runbook
