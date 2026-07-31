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

**API container** — FastAPI on uvicorn. Owns the SoT entity tables (model, model_file, tag, tag_group, browse_category, model_browse_category, etc.), serves binary content from `portal-content` with ETag, manages share tokens, JWT login, and audit log. Mounts portal-content (rw) and portal-state (rw). Talks to Redis.

**Worker container** — arq worker. Pre-renders thumbnails (4 views per model) on demand using `trimesh` + matplotlib, writing the resulting PNGs back as `ModelFile` rows under `portal-content`. Mounts portal-content (rw) and portal-state (rw). Talks to Redis.

**Redis container** — share tokens with native TTL, render job queue.

## Data flow

The SQLite database under `/data/state/portal.db` is the catalog source of truth. Models, files, tags (facet-grouped), browse categories, notes, prints, and external links are created and edited via the admin API (`/api/admin/*`). Binary content (STL, photos, renders) lives under `portal-content` and is referenced by `model_file.storage_path`. Reverse-sync to WSL uses an `agent`-role JWT (see `scripts/hydrate_local_tree.py`).

## Classification: browse categories and facet tags

**Retired — the single-category taxonomy.** Until the Story 47.5 cutover, every model carried
exactly one mandatory `category`, and categories formed a recursive tree. Alembic migration
`0019_drop_category` dropped it. `Model.category_id` is **not coming back**; nothing in the
current system reintroduces a mandatory single classification.

**Current — two independent layers.** A model is classified by two layers that never imply each
other:

- **Facet tags** (`tag`, `tag_group`, `model_tag`) — many-to-many refinements, grouped into
  facets (type, room, system, use case, printer, material, creator, level). OR within a group,
  AND between groups.
- **Browse categories** (`browse_category`, `model_browse_category`, migration
  `0020_browse_categories`) — many-to-many, **optional** broad browse entry points. A model may
  carry zero, one or many. Categories are a browse *scope*, not another filter, and they are
  independent of tags: assigning one never adds the other, and there is no inference in either
  direction.

**Zero categories is a valid, publicly visible state.** An uncategorized model appears in
`GET /api/models` and renders normally on every user-facing surface; only the admin surface
flags it as needing curation. It is not an error condition.

Admission criteria, per-category examples, the Category-vs-Tag rule and the curation-QA routine
live in `docs/browse-category-governance.md`.

## Future-proofing slots

These are already in place for future expansion:

| Future feature | What's already in place |
|---|---|
| Postgres migration | SQLModel + alembic; flip `DATABASE_URL` |
| Print queue | `apps/api/app/modules/queue/`, `modules/queue/` in web; arq broker on Redis |
| Moonraker integration | `modules/printer/` slot; existing OTel collector; env var `MOONRAKER_URL` |
| Spoolman integration | `modules/spools/` slot; HTTP client to existing Spoolman compose |
| Filament profile policy | `EstimateProfileSource` logic; portal-owned mapping from Spoolman material to Orca profiles |
| Print requests | `modules/requests/` slot; `User.role = member` in schema |
| Mobile photo upload | `POST /api/admin/models/{id}/prints` + new uploads volume + reverse rsync |
| WebSocket / SSE live updates | nginx-180 already has WS upgrade headers; Redis pub/sub ready |
| OIDC / SSO | Auth isolated in `core/auth/`; can be replaced with Authentik client |
| Full-text search backend | OpenSearch is already in homelab; portal can query `https://192.168.2.190:9200` |

## References

- `docs/design/2026-04-29-portal-design.md` — full specification
- `docs/plans/2026-04-29-portal-v1-implementation.md` — implementation plan
- `docs/operations.md` — deployment and operations runbook
- `docs/browse-category-governance.md` — browse-category admission criteria, Category-vs-Tag rule, curation QA
