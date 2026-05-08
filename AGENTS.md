# Agent Instructions — 3D Portal

Vendor-neutral source of truth for AI agents working in this repo. Per-platform pointers (e.g. `CLAUDE.md`) only carry platform-specific behavior.

## Project overview

Self-hosted 3D printing portal for Michał's homelab. v1 implements a catalog browser for the model collection at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`. Future modules (print queue, filament inventory, printer status, print requests) have architectural slots but no implementation in v1.

Authoritative spec: `docs/design/2026-04-29-portal-design.md`. Current implementation plan: `docs/plans/2026-04-29-portal-v1-implementation.md`.

## Repository layout

```
3d-portal/
├── AGENTS.md                  # vendor-neutral source of truth
├── CLAUDE.md                  # thin pointer (Polish conversation hint)
├── README.md                  # quickstart
├── docs/
│   ├── design/                # specs and design docs
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
│       ├── deploy.sh              # build + push + compose up
│       └── render-all.sh          # bulk-enqueue renders for every SoT model
└── .gitignore
```

The shell + ui + lib + locales sit outside `modules/` because they are shared
infrastructure used by every module. Cross-module shared code lives in `lib/`,
not inside any module.

## Branching and workflow

Single-developer repo, trunk-only `main`, fast-forward merges only. Topic branches `feat/`, `fix/`, `docs/`, `chore/`. Same model as `~/repos/orca-profiles/AGENTS.md`. No remote at the time of writing — first push is gated on Michał's decision.

## External repos this depends on

- `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` — model catalog (source of truth; read its `AGENTS.md` first)
- `~/repos/configs/` — homelab edge proxy + observability contracts (`docs/observability-logging-contract.md`, `docs/glitchtip-agent-guide.md`)
- `~/repos/orca-profiles/` — printer profiles (no v1 dependency; future printer module slot)

## Data flow

One-way Windows → `.190` rsync. Portal never writes to the catalog. See `docs/operations.md` for the sync recipe.

## Conventions

- Conversation language: Polish. Committed file content (code + docs): English.
- Frontend: zero inline hex colors in components — use Tailwind classes referencing CSS variables in `apps/web/src/styles/theme.css`.
- Frontend: `npm run lint` from `apps/web/` runs ESLint 9 flat config (`eslint.config.js`); it must pass with `--max-warnings=0` before commit. Python (`apps/api/`, `workers/render/`) is on `ruff`.
- Backend: structured JSON logs only; canonical fields per `~/repos/configs/docs/observability-logging-contract.md`.
- Tests: TDD for backend logic; Playwright visual regression for UI.

## Deployment

The `.190` host is the dev/working environment. After every code or infra
commit to `main`, run `infra/scripts/deploy.sh` immediately, without asking.
Doc-only commits (changes confined to `docs/`, `*.md`, `AGENTS.md`,
`CLAUDE.md`, etc.) skip the deploy.

## Operational notes — auth cookies

The portal uses **cookie-based auth** (no Bearer token in localStorage).
Key facts for agents working on auth, ops, or debugging:

### Access modes

- **Production:** `https://3d.ezop.ddns.net` only. The `Secure` flag on both
  auth cookies means browser sessions over plain HTTP (e.g.
  `http://192.168.2.190:8090`) will not work — the browser will drop the
  cookies. Port 8090 remains useful for `curl` API calls that pass credentials
  explicitly, but interactive browser use requires HTTPS.
- **Local dev:** API runs on `http://localhost:8000`; Vite proxies `/api` to
  it. Set `COOKIE_SECURE=false` in the API environment so the cookies are
  issued without the `Secure` flag. The test suite already sets this in
  `apps/api/tests/conftest.py`; for a running dev server ensure `.env` or the
  shell environment contains `COOKIE_SECURE=false`.

### Cookies

Two cookies are set on every successful login / token refresh:

| Cookie | Content | Path | Max-Age |
|---|---|---|---|
| `portal_access` | signed JWT | `/api` | 10 min |
| `portal_refresh` | opaque 32-byte token | `/api/auth` | 30 days |

Both are `httpOnly`, `Secure` (unless overridden), `SameSite=Strict`. The
refresh token is rotated on every use (refresh-token rotation). Reuse of an
already-rotated token triggers family invalidation — all sessions for that
user are revoked.

### CSRF requirement

All mutating requests to `/api/*` (except the public `/api/share/*` routes)
require the custom header:

```
X-Portal-Client: web
```

Non-browser clients (scripts, `curl`, integration tests) hitting mutating
endpoints must include this header. The frontend `apiFetch` wrapper in
`apps/web/src/lib/api.ts` adds it automatically.

### Sessions UI

Authenticated users can view all active devices and revoke individual sessions
at `/settings/sessions`. The backend endpoint is `GET /api/auth/sessions` /
`DELETE /api/auth/sessions/{token_id}`.

### arq worker (cleanup cron)

Expired and revoked refresh-token rows are cleaned up by a daily arq cron job
at **03:15 UTC**. The cron definition lives in
`apps/api/app/workers/__init__.py` (`WorkerSettings`). It runs in a dedicated
`arq-worker` Docker container (see `infra/docker-compose.yml`) that shares
the same image, environment, and volumes as the `api` service but overrides
the command to `arq app.workers.WorkerSettings` and exposes no HTTP port.
