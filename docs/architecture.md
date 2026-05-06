# Architecture overview

This document condenses the system architecture. For the full design specification, see `docs/design/2026-04-29-portal-design.md`.

## Components

```
[Browser] ─https─▶ [nginx-180 (edge)] ─proxy─▶ [.190 docker-compose stack]
                         │                          │
                         │                          ├─ web    (nginx + React build)
                         │                          ├─ api    (FastAPI + Pydantic + SQLModel)
                         │                          ├─ worker (arq render queue)
                         │                          └─ redis  (queue + share tokens)
                         │
                  household basic auth
                  (bypass: /share/*)

[portal-content volume]   (api + worker read/write — STL, photos, renders)
[portal-state volume]     (SQLite — `portal.db`, the catalog source of truth)
```

## Container responsibilities

**Web container** — nginx serving the built React SPA (`dist/`), static assets only. Exposes `127.0.0.1:8080` on `.190` and is reverse-proxied by nginx-180.

**API container** — FastAPI on uvicorn. Owns the SoT entity tables (model, model_file, tag, category, etc.), serves binary content from `portal-content` with ETag, manages share tokens, JWT login, and audit log. Mounts portal-content (rw) and portal-state (rw). Talks to Redis.

**Worker container** — arq worker. Pre-renders thumbnails (4 views per model) on demand using `trimesh` + matplotlib, writing the resulting PNGs back as `ModelFile` rows under `portal-content`. Mounts portal-content (rw) and portal-state (rw). Talks to Redis.

**Redis container** — share tokens with native TTL, render job queue.

## Data flow

The SQLite database under `/data/state/portal.db` is the catalog source of truth. Models, files, tags, categories, notes, prints, and external links are created and edited via the admin API (`/api/admin/*`). Binary content (STL, photos, renders) lives under `portal-content` and is referenced by `model_file.storage_path`. Reverse-sync to WSL uses an `agent`-role JWT (see `scripts/hydrate_local_tree.py`).

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
