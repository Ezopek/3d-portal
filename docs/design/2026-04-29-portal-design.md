# 3D Portal — Design Spec

**Date:** 2026-04-29
**Status:** Draft, pending user review
**Author:** Claude Opus 4.7 (brainstorming session with Michał)

## 1. Goal

Build a self-hosted **3D Printing Portal** for Michał's homelab, accessible to
his family on phones and desktops, that starts as a browser for his existing
3D-model collection and expands into a multi-module platform covering print
queue, filament inventory, printer status, and print requests.

Out of scope for v1: print queue, printer integration, filament inventory,
print requests. These get architectural slots from day one but no UI/logic.

## 2. Users and Access Model

### 2.1 Roles

| Role | Who | Permissions |
|---|---|---|
| `admin` | Michał (one user) | Full: edit catalog, manage share-links, add print photos, manage queue (Phase 2+) |
| `member` | Future: family members with accounts | Read + favorites + comment + request a model (Phase 2+) |
| `anonymous` | Anyone past household auth, or visiting `/share/:token` | Read-only catalog browsing |

In v1, only `admin` is implemented (one user seeded from env vars). The
`member` role exists in the schema but isn't issued.

### 2.2 Authentication layers

| Layer | Mechanism | Scope |
|---|---|---|
| Household gate | `nginx` basic auth on `.180` (one shared password) | All paths except `/share/*` |
| Admin login | FastAPI + JWT (30 min, no refresh — re-login on expiry) | `/api/admin/*` and admin UI actions |

Family members enter the household password once per browser; admin login is
an additional gate only for Michał-edits.

`/share/:token` paths bypass the household gate entirely so external visitors
can see one model without any password.

## 3. Architecture

### 3.1 Components

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

### 3.2 Container responsibilities

- **`web`** — nginx serving the built React SPA (`dist/`), static assets only.
  Exposes `127.0.0.1:8080` on `.190`. Reverse-proxied by nginx-180.
- **`api`** — FastAPI on uvicorn. Reads catalog from read-only volume,
  serves files (STL/img with ETag), manages share tokens, JWT login, audit log.
  Mounts: `catalog-data:ro`, `portal-renders:ro`, `portal-state:rw`. Talks
  to Redis.
- **`worker`** — arq worker. Pre-renders thumbnails for models without
  `images/` using `trimesh` + matplotlib (4 views per model, written to
  the dedicated `portal-renders` volume). Mounts: `catalog-data:ro`,
  `portal-renders:rw`. Talks to Redis.
- **`redis`** — share tokens with native TTL, render job queue, computed
  caches (facets, top-tag counts).

### 3.3 Data sync

**Direction:** one-way Windows → `.190`. The catalog repo on Windows stays
the single source of truth; Claude CLI continues to manage it as before.

**Mechanism:** `infra/scripts/sync-data.sh` (rsync over SSH) executed from
WSL after a catalog change, plus an optional cron safety net every 15 min.
After sync, the script POSTs `/api/admin/refresh-catalog` to invalidate
the in-memory catalog and computed caches.

Future bidirectional sync (for `v2`-style print-photo upload from phone) gets
a separate volume `/mnt/raid/3d-portal-uploads/` with a reverse rsync; not
implemented in v1.

## 4. Repository Layout

Monorepo at `~/repos/3d-portal/`:

```
3d-portal/
├── AGENTS.md                  # vendor-neutral source of truth
├── CLAUDE.md                  # thin pointer (Polish conversation hint)
├── README.md                  # quickstart
├── docs/
│   ├── design/                # specs (this file lives here)
│   ├── plans/                 # implementation plans
│   ├── architecture.md        # high-level system overview
│   └── operations.md          # deploy, sync, runbook
├── apps/
│   ├── api/                   # FastAPI + Pydantic v2 + SQLModel
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/          # config, db, redis, auth, logging
│   │   │   └── modules/
│   │   │       ├── catalog/   # v1 — APIRouter + service + models
│   │   │       ├── share/     # v1
│   │   │       ├── queue/     # v2 slot
│   │   │       ├── spools/    # v2 slot
│   │   │       ├── printer/   # v2 slot
│   │   │       └── requests/  # v2 slot
│   │   └── tests/
│   └── web/                   # React 19 + Vite + TS + Tailwind v4 + shadcn/ui
│       ├── package.json
│       ├── Dockerfile         # multi-stage: build → nginx:alpine
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.tsx
│       │   ├── instrument.ts  # Sentry/GlitchTip init
│       │   ├── shell/         # AppShell, ModuleRail, TopBar, ThemeProvider, AuthGate, LangProvider
│       │   ├── modules/
│       │   │   ├── catalog/   # v1 — routes/, components/, hooks/
│       │   │   ├── queue/     # v2 — Coming soon placeholder
│       │   │   ├── spools/    # v2
│       │   │   ├── printer/   # v2
│       │   │   └── requests/  # v2
│       │   ├── ui/            # shadcn/ui primitives (shared)
│       │   ├── lib/           # api client, theme hook, search (Fuse.js)
│       │   ├── locales/       # en.json, pl.json
│       │   └── routes/        # TanStack Router root
│       └── tests/
│           └── visual/        # Playwright snapshot tests
├── workers/
│   └── render/                # arq worker
│       ├── pyproject.toml
│       ├── Dockerfile
│       └── render/
│           ├── worker.py
│           └── trimesh_render.py
├── infra/
│   ├── docker-compose.yml         # production stack
│   ├── docker-compose.dev.yml     # local dev with hot reload
│   ├── nginx-180/
│   │   └── 3d-portal.conf         # to be deployed via configs/sync.sh
│   ├── env.example
│   └── scripts/
│       ├── sync-data.sh           # rsync Windows → .190
│       └── deploy.sh              # build + push + compose up
└── .gitignore
```

The shell + ui + lib + locales sit outside `modules/` because they are shared
infrastructure used by every module. Cross-module shared code lives in `lib/`,
not inside any module.

## 5. Data Model

### 5.1 Catalog (source of truth on Windows)

Already migrated to English in 2026-04-29 catalog migration. Schema in
`3d_modelowanie/AGENTS.md`. Key fields used by the portal:

```jsonc
{
  "id": "001",
  "name_en": "...",
  "name_pl": "...",
  "path": "decorum/...",
  "category": "decorations",
  "subcategory": "articulated_figures",
  "tags": ["dragon", "smok", "egg", "jajko", ...],   // bilingual flat array
  "source": "printables" | "makerworld" | "thangs" | "creality_cloud" | "other" | "unknown",
  "printables_id": null,
  "thangs_id": null,
  "makerworld_id": null,
  "source_url": null,
  "rating": null,
  "status": "printed" | "not_printed",
  "notes": "",                                       // English
  "thumbnail": null,
  "date_added": "2026-04-12",
  "prints": []                                       // NEW field, optional, default []
}
```

**Schema additions for v1:**

- `prints: Print[]` — array of print events for the model.
  ```jsonc
  {
    "path": "{model_path}/prints/2026-04-29-front.jpg",
    "date": "2026-04-29",
    "notes_en": "First successful print, PLA black",
    "notes_pl": "Pierwszy udany wydruk, PLA czarny"
  }
  ```

This requires a one-line update to the catalog schema in
`3d_modelowanie/AGENTS.md` plus a default `[]` for existing entries.

### 5.2 SQLite (`portal-state` volume on `.190`)

```python
# apps/api/app/core/db/models.py

class UserRole(str, Enum):
    admin = "admin"
    member = "member"

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str          # bcrypt
    created_at: datetime
    last_login_at: datetime | None = None

class AuditEvent(SQLModel, table=True):
    id: int = Field(primary_key=True)
    at: datetime = Field(default_factory=datetime.utcnow, index=True)
    actor_user_id: int | None = Field(foreign_key="user.id")
    kind: str                    # "share.created", "render.triggered", "catalog.refresh", "auth.login.success", ...
    payload: str                 # JSON string

# v2 slots (defined but not used in v1):
# class PrintJob(SQLModel, table=True): ...
# class PrintRequest(SQLModel, table=True): ...
```

Migrations: alembic. Initial migration creates `user` + `auditevent`. The
admin user is seeded at startup if no row exists, from `ADMIN_EMAIL` and
`ADMIN_PASSWORD` env vars.

### 5.3 Redis keys

```
share:token:{token}         JSON {model_id, expires_at, created_by}, TTL=expires_at-now
share:by-model:{model_id}   SET[token]   for listing
arq:queue:render            arq queue
render:status:{model_id}    "pending" | "running" | "done" | "failed", TTL=1h
cache:facets                JSON {category: {...}, status: {...}, tags: [...]}, TTL=5min or invalidated
cache:catalog:projection    JSON list-view projection, invalidated by /api/admin/refresh-catalog
```

Redis is configured with `--save 60 1` so share tokens survive restart;
losing all on disaster is acceptable.

## 6. API

All endpoints are under `/api`. Module endpoints are namespaced:
`/api/catalog/...`, `/api/share/...`, `/api/admin/...`, `/api/auth/...`.

### 6.1 v1 endpoints

```
# Public (household-auth gate at nginx)
GET  /api/health                                  liveness probe
GET  /api/catalog/models                          list-view projection (paginated, sortable)
GET  /api/catalog/models/{id}                     full model detail
GET  /api/catalog/models/{id}/files               files in model directory
GET  /api/files/{model_id}/{path:path}            STL/image download with ETag

# Share-link (no auth)
GET  /api/share/{token}                           resolve to model (subset projection)

# Authenticated (admin JWT required)
POST /api/auth/login                              email + password → JWT (30 min)
POST /api/auth/me                                 current user info
POST /api/auth/logout                             client-side token discard (server is stateless)

POST /api/admin/share                             create share token {model_id, expires_in_hours}
DELETE /api/admin/share/{token}                   invalidate
GET    /api/admin/share                           list active tokens

POST /api/admin/refresh-catalog                   re-read index.json, invalidate caches
POST /api/admin/render/{model_id}                 enqueue render
GET  /api/admin/jobs/{job_id}                     job status (poll, or future SSE)
GET  /api/admin/audit                             audit log (paginated)
```

### 6.2 List-view projection

`GET /api/catalog/models` returns a lightweight projection optimized for grid
rendering and client-side search:

```jsonc
{
  "models": [
    {
      "id": "001",
      "name_en": "...",
      "name_pl": "...",
      "category": "decorations",
      "tags": ["dragon", "smok", "egg", "jajko"],
      "source": "printables",
      "status": "printed",
      "rating": null,
      "thumbnail_url": "/api/files/001/images/Dragon_v2.0_C.png",   // resolved server-side
      "has_3d": true,
      "date_added": "2026-04-12"
    },
    ...
  ],
  "total": 90
}
```

The frontend caches this with TanStack Query and runs Fuse.js search +
filters + sort entirely client-side. With ~90 entries (and likely growth to
a few hundred), this is well under any performance bound.

### 6.3 v2 endpoints (slot, not implemented)

- `/api/queue/...` — print queue CRUD, drag-reorder, status
- `/api/spools/...` — proxy to Spoolman REST API
- `/api/printer/...` — Moonraker WebSocket proxy + cached status
- `/api/requests/...` — print request submission and approval

## 7. Frontend

### 7.1 Stack

- React 19 + TypeScript + Vite
- TailwindCSS v4 (CSS-first config) + shadcn/ui
- TanStack Router (typed routes), TanStack Query (server state)
- `react-i18next` (PL/EN), Fuse.js (client-side search), `@sentry/react`
- 3D viewer: Google's `<model-viewer>` web component (drop-in tag)
- Forms (later): react-hook-form + zod

### 7.2 Modular shell

The top-level `AppShell` provides:
- **`ModuleRail`** — left rail on desktop (≥1024px), bottom tab bar on mobile.
  Renders 5 module entries (Catalog, Queue, Spools, Printer, Requests). v2
  modules show a "Coming soon" placeholder route.
- **`TopBar`** — module title + breadcrumb + search (catalog has it,
  others may not), `ThemeToggle`, `LangToggle`, admin login button (or user
  menu when logged in).
- **`ThemeProvider`** — light/dark via `class="dark"` on `<html>`. Default:
  `prefers-color-scheme`. Persisted in `localStorage`.
- **`LangProvider`** — react-i18next. Default: `navigator.language` if `pl-*`
  → PL, else PL fallback (family-first). Persisted in `localStorage`.
- **`AuthGate`** — wraps admin-only UI. Reads JWT from `localStorage`.

### 7.3 Routes

```
/                       Landing (module list + recently added strip)
/catalog                Catalog grid + filters
/catalog/:id            Model detail page
/share/:token           Standalone share view (no shell)
/queue                  Coming soon (v2)
/spools                 Coming soon
/printer                Coming soon
/requests               Coming soon
/login                  Admin login (visible to all)
/dev/components         Design playground (admin-only)
```

### 7.4 Catalog UX (v1 only fully implemented module)

**List view (`/catalog`)**:
- Mobile: 2-col card grid, two horizontal filter pill rows (category +
  status/quality), search in topbar, no sidebar.
- Desktop: 240px sidebar with facet groups (Categories with counts, Status,
  Top tags), 4-col card grid.
- Card: square thumbnail (first `images/*` from catalog, or `iso` view from
  `portal-renders` if no images, served via `/api/files/{id}/thumbnail`),
  status badge (printed/not), source badge, name_en (primary) + name_pl
  (secondary), top 2 tags.
- Sort dropdown at end of filter bar: Recently added (default) / Oldest /
  Name A–Z / Name Z–A / Status.

**Detail view (`/catalog/:id`)**:
- Image gallery merging Printables `images/*` (catalog-data) + own
  `prints/*` (catalog-data) + computed renders (portal-renders volume, served
  by API as `/api/files/{id}/render/{view}.png`).
- Title (large, bilingual stacked), tags, source link.
- Tabs: **Info** (category, status, rating, date added, notes) /
  **Files** (list of files with download icons + "View 3D" for STL) /
  **My prints** (gallery of `prints[]` with notes; admin-only "Add via
  Claude CLI" hint).
- Action buttons (sticky on mobile): **Download STL**, **View 3D**,
  **Open in Orca** (URL handler if available, else hidden), **Share**
  (admin-only) — opens dialog with token + URL.

**Share view (`/share/:token`)**:
- Standalone, no shell, no ModuleRail.
- Header: minimal logo + "shared with you".
- Body: same gallery + name + 1 line of context + Download STL.
- No tabs, no other models, no admin hints. Footer link to home page only if
  user is in household (i.e., browser already has basic auth cookie); for
  external visitors, just a "3D Portal by ezop" link.

### 7.5 Design system

- Tokens via Tailwind classes referencing CSS variables; **zero inline
  hex colors** in components. A failing rule (e.g., ESLint plugin or
  manual review) keeps this enforced.
- Single `theme.css` file holds light + dark variable sets.
- shadcn/ui primitives are the only component library. Custom components
  (ModelCard, FilterBar, ModuleRail, ThemeToggle, LangToggle, etc.) live
  in `apps/web/src/ui/custom/` and follow the same token discipline.

### 7.6 Internationalization

- `react-i18next` with `en.json` and `pl.json` flat-key files.
- All UI strings via `t('...')` or `<Trans>`.
- Catalog content (`name_en`, `name_pl`, `notes`) selected by active locale;
  tags shown as-is (mixed bilingual array), all are searchable.
- Backend errors return translation keys, not strings.
- i18n string coverage verified by unit test (every `t()` key resolves in
  both `en.json` and `pl.json`). Visual regression covers the default
  locale; an `EN smoke` snapshot run is added when string lengths diverge
  enough to risk overflow.

### 7.7 Design verification flow

A dedicated route `/dev/components` (admin-only) renders every shadcn
primitive + every custom component in all variants, side by side in light
and dark.

**Playwright visual regression**:
- Snapshots for `/dev/components`, `/catalog`, `/catalog/:id`, `/share/:token`
  in `{light, dark} × {mobile, desktop}` = 4 variants per route.
- Default locale for snapshots is PL (family-first); EN smoke pass added
  ad-hoc when needed.
- Baselines in `apps/web/tests/visual/__snapshots__/`.
- `npm run test:visual` runs locally; failure on diff.

**Agent workflow on UI changes**:
1. Edit code.
2. Run `npm run test:visual`.
3. If diff: visually inspect each diff, accept or fix.
4. Open `/dev/components` via chrome-devtools-mcp for sanity check.
5. Report visual diffs in PR/summary.
6. Human reviewer (Michał) clicks through 2–3 routes in both themes.

## 8. Deployment and Operations

### 8.1 Docker-compose stack on `.190`

Lives at `/mnt/raid/docker-compose/3d-portal/`. Synced from
`~/repos/3d-portal/infra/docker-compose.yml` via the project's deploy script.

Four services: `web`, `api`, `worker`, `redis`. Volumes:
- `/mnt/raid/3d-portal-data/` — catalog data (rsync target from Windows,
  read-only for all containers)
- `/mnt/raid/3d-portal-renders/` — pre-rendered thumbnails written by
  `worker`, read by `api` (separate from catalog-data so that rsync's
  `--delete` cannot remove them)
- `/mnt/raid/3d-portal-state/` — SQLite + future uploads, read-write for
  `api` only
- `redis-data` (named volume) — Redis persistence

Environment from `infra/env.example` filled into a real `.env` on `.190`
(not committed). Required vars: `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
`JWT_SECRET`, `PORTAL_VERSION`, `OTEL_EXPORTER_OTLP_ENDPOINT`,
`SENTRY_DSN_WEB`.

### 8.2 Edge proxy on `.180`

A new file `~/repos/configs/nginx/3d-portal.conf` is added to the existing
proxy config repo and deployed via `bash sync.sh` (which auto-reloads
nginx). TLS comes from the existing http-block configuration on `.180`;
the server block does not duplicate cert directives.

```nginx
upstream portal_backend { server 192.168.2.190:8080; }

server {
    listen 443 ssl http2;
    server_name 3d.ezop.ddns.net;

    auth_basic            "3D Portal — household login";
    auth_basic_user_file  /etc/nginx/htpasswd-3d-portal;

    location /share/ {
        auth_basic off;
        proxy_pass http://portal_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://portal_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

The `htpasswd-3d-portal` file is generated and deployed alongside, with the
shared family password chosen at setup time.

### 8.3 Sync flow Windows → `.190`

`infra/scripts/sync-data.sh` uses `rsync` over SSH from WSL:

```bash
SOURCE="/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/"
DEST="ezop@192.168.2.190:/mnt/raid/3d-portal-data/"

rsync -avz --delete \
  --exclude='.git/' --exclude='.claude/' --exclude='.codex/' \
  --exclude='.playwright-mcp/' --exclude='.superpowers/' \
  --exclude='docs/' --exclude='AGENTS.md' --exclude='CLAUDE.md' \
  --include='*/' \
  --include='_index/index.json' \
  --include='**/*.stl' --include='**/*.3mf' --include='**/*.step' \
  --include='**/images/**' --include='**/prints/**' \
  --exclude='*' \
  "$SOURCE" "$DEST"

curl -fsS -u "${PORTAL_AUTH}" \
  -X POST "https://3d.ezop.ddns.net/api/admin/refresh-catalog" || true
```

Triggered:
- Manually from WSL after a catalog edit.
- As the final step of the catalog repo's "add model" workflow (update to
  `3d_modelowanie/AGENTS.md` documents this).
- Optional cron every 15 min on Windows Task Scheduler / WSL cron as a
  safety net.

### 8.4 Local dev cycle

`infra/docker-compose.dev.yml`:
- `web` — Vite dev server with HMR, source bind-mounted.
- `api` — uvicorn `--reload`, source bind-mounted.
- `worker` — arq watcher, source bind-mounted.
- `redis` — same as prod.
- `catalog-data` — bind-mount of `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`
  (or a fixtures copy), read-only by default in dev.

Agent workflow:
1. `git worktree add .worktrees/feature-x -b feat/x`
2. `docker compose -f infra/docker-compose.dev.yml up`
3. Edit. Vite + uvicorn auto-reload.
4. `npm run test:visual && npm run test && pytest && ruff check .`
5. Open `/dev/components` via chrome-devtools-mcp for sanity.
6. Commit, ff-merge to `main`, deploy.

### 8.5 Observability

Per `~/repos/configs/docs/observability-logging-contract.md` and
`glitchtip-agent-guide.md`.

**Backend (api + worker)** — OpenTelemetry SDK, OTLP HTTP exporter to
`http://192.168.2.190:4318`. Resource attributes:

| Attribute | Value |
|---|---|
| `service.name` | `3d-portal-api` / `3d-portal-worker` |
| `service.namespace` | `backend` |
| `service.version` | `${PORTAL_VERSION}` |
| `deployment.environment` | `production` / `dev` |

Structured JSON logs with canonical fields (`@timestamp`, `message`,
`log.level`, `service.*`, `event.*`, `trace.id`, `span.id`,
`labels.{model_id, user_role, ...}`). Stable `event.dataset` values:
`3d-portal.api`, `3d-portal.worker`, `3d-portal.access`. Logs auto-route
into `ss4o_logs-3d-portal.api-backend` etc.

The OTLP token is read from the existing infrastructure secret source
documented in the observability contract — no hardcoded credentials.

**Frontend (web)** — `@sentry/react` pointing at GlitchTip. A new GlitchTip
project `3d-portal-web` is created via the GlitchTip API at setup time;
its DSN goes into `VITE_SENTRY_DSN` (`apps/web/.env.production`).
ErrorBoundary wraps modules in the shell. Errors include `trace.id` tag
when available so they correlate with backend traces in OpenSearch.

Verification step after first deploy: send `Sentry.captureMessage("test
from 3d-portal-web")` and confirm in panel.

### 8.6 Backup

- SQLite (`portal.db`): nightly cron on `.190` copies to
  `/mnt/raid/3d-portal-state/backups/portal-$(date +%F).db`, retention 30
  days.
- Catalog data: already covered by Nextcloud (Windows side) + RAID on
  `.190`. No extra backup.
- Redis: ephemeral. Loss on disaster (expired tokens, queued jobs) is
  acceptable.

## 9. Future-Proofing

These slots exist in the architecture from day one but have no
implementation in v1:

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

## 10. MVP Scope (v1)

**In scope:**
- Catalog module: list, detail, search, filters, sort, share-links, render
  worker for missing thumbnails.
- Modular shell with all 5 module entries (4 of them as "Coming soon"
  placeholders).
- Authentication: household basic auth at nginx + admin JWT in API.
- i18n: PL + EN with persistent toggle.
- Theme: light + dark with persistent toggle.
- Design system: shadcn/ui, theme tokens, `/dev/components` playground.
- Visual regression: Playwright snapshots in 4 variants per route.
- Observability: OTel to homelab collector, GlitchTip for frontend.
- Deployment: docker-compose on `.190`, nginx config on `.180`, sync script.
- Backup: SQLite nightly cron.

**Out of scope (Phase 2+):**
- Print queue, printer status, filament inventory, print requests.
- Member accounts (only admin in v1).
- Mobile photo upload (Claude CLI only in v1).
- WebSocket / SSE live updates.
- Postgres.
- Caching beyond Redis (e.g., CDN).

## 11. Acceptance Criteria

A v1 release is acceptable when:

1. Family member can open `https://3d.ezop.ddns.net` on a phone, enter the
   household password once, and browse the catalog in Polish with a
   responsive 2-column grid.
2. Filters (category, status) and sort (recently added) work entirely on
   the client without further server roundtrips.
3. Clicking a model opens detail view with at least one image (existing
   `images/*` from catalog or computed render from `portal-renders`),
   download STL works, and "View 3D" loads the model in `<model-viewer>`.
4. Michał can log in as admin from any module and see additional actions:
   create/list/revoke share-links, trigger render, refresh catalog.
5. A share-link `/share/:token` opens the standalone view without
   prompting for the household password and without exposing other models.
6. Theme toggle and language toggle persist across reloads and respect
   system defaults on first visit.
7. `/dev/components` renders without errors in both themes.
8. Playwright snapshot suite passes for all 4 variants
   (`{light, dark} × {mobile, desktop}`, PL default) of every covered route.
9. A 5xx in the API surfaces in OpenSearch under
   `service.name=3d-portal-api` with correlated `trace.id` and `span.id`,
   and a frontend error appears in GlitchTip under the `3d-portal-web`
   project.
10. `infra/scripts/sync-data.sh` from WSL completes in under 30 s for
    incremental catalog changes and triggers a successful
    `/api/admin/refresh-catalog`.

## 12. Open Items (deferred to implementation time)

These items were noted during brainstorming but are not blocking for the
spec; they get resolved during implementation:

- Whether `orca-slicer://` URL handler exists on Michał's Windows install
  (if yes, the "Open in Orca" button uses it; if no, it stays hidden).
- Retroactive `date_added` recovery from `_katalog/katalog.json` git
  history, optional follow-up session.
- Whether to expose admin API responses with `trace.id` in headers for
  manual debugging (cosmetic).
