---
project_name: '3d-portal'
user_name: 'Ezop'
date: '2026-05-10'
last_updated: '2026-05-29'
sections_completed: ['technology_stack', 'language_specific', 'framework_specific', 'testing', 'code_quality', 'workflow', 'critical_dont_miss', 'observability', 'initiative_11_18_lessons']
status: 'complete'
rule_count: 144
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Core

- **Frontend:** React 19 + TypeScript 5.6 (strict, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`), Vite 6, Tailwind CSS v4 (`@tailwindcss/postcss`), shadcn/ui (on `@base-ui/react` + Radix), TanStack Router 1.x + Query 5.x, i18next 24 / react-i18next 15, Three.js 0.171 + `@react-three/fiber` 9 / `@react-three/drei` 10, Sentry/GlitchTip SDK 8.x.
- **Backend:** Python 3.12, FastAPI ≥0.115, Pydantic 2.9, SQLModel 0.0.22, Alembic ≥1.14, Redis client 5.2, arq ≥0.26, PyJWT ≥2.10, bcrypt ≥4.0.
- **Worker:** arq + `trimesh` ≥4.5 + matplotlib ≥3.9 + Pillow ≥11. Editable dep on `portal-api` (shared SQLModel models).
- **Data plane:** SQLite (`portal.db` on `portal-state` volume) — Postgres-ready via SQLModel + Alembic. Binary content on `portal-content` volume. Redis for arq queue + share-token TTL.
- **Observability:** OpenTelemetry distro 0.50b0 (FastAPI/Redis/SQLAlchemy instrumentation, OTLP-HTTP exporter); Sentry SDK ≥2.20. Structured JSON logs per `~/repos/configs/docs/observability-logging-contract.md`.

### Version constraints AI must respect

- **Tailwind v4 (NOT v3).** `@import "tailwindcss"` in `theme.css`, no `tailwind.config.js`. Custom theme tokens live inline in `@theme {}` block. v3 patterns (`tailwind.config.content`, JIT mode) do not apply — do not regenerate them.
- **OTel contrib pins are intentional** (`opentelemetry-instrumentation-* >=0.50b0`). No stable 1.x exists for these packages. Do not bump to imagined `1.x` versions.
- **React 19** — uses new `use()` / Actions API. Older React 18 patterns (`useTransition` defaults, `Suspense` quirks) may differ.
- **shadcn 4.x flow** — components sourced via `npx shadcn add`, land in `apps/web/src/ui/`. Depend on `@base-ui/react` + Radix primitives. Do not paste pre-v4 shadcn snippets.
- **TypeScript 5.6 with `noUncheckedIndexedAccess` + `strict`** — array/object index access yields `T | undefined`. Handle the `undefined` branch; do not paper over with non-null `!`.
- **Python 3.12 minimum** — use modern syntax (`match`, `Self`, PEP 695 generics) where it improves clarity.
- **i18next 24 + react-i18next 15** — language detector + Suspense pattern is the new style; older v13/14 examples don't apply.

## Critical Implementation Rules

### Language-Specific Rules

#### TypeScript (frontend)

- **`verbatimModuleSyntax: true` + `isolatedModules: true`** are on. Use `import type { Foo } from "..."` for type-only imports — bare `import { Foo }` of a type fails the build. Mixing types and values from one module: `import { thing, type Bar } from "..."`.
- **`noUncheckedIndexedAccess: true`** — `arr[i]` is `T | undefined`, dict access too. Branch with `if (!x) return ...` or use a guard; do **not** silence with `!`.
- **Path alias `@/*` = `apps/web/src/*`.** Cross-module imports go through `@/lib`, `@/ui`, `@/shell`, `@/modules/...`. No deep relative `../../..` chains across module boundaries.
- **No inline hex colors anywhere in `.tsx`/`.ts`.** Use Tailwind classes that reference CSS variables in `apps/web/src/styles/theme.css` (e.g. `bg-card text-card-foreground border-border`). New colors → add a `--color-*` token to `@theme {}` in `theme.css`, then use the Tailwind class.
- **Network calls go through `api()` from `@/lib/api`.** It auto-attaches the `X-Portal-Client: web` CSRF header, sets `credentials: "include"`, and retries once on `401 access_expired` via the silent refresh path. Bypassing it (raw `fetch`) silently breaks auth + CSRF.
- **API errors throw `ApiError` (status, body, message).** UI code catches it, doesn't re-implement status parsing.
- **ESLint must pass with `--max-warnings=0`** (`npm run lint` from `apps/web/`). No "I'll silence the warning" — fix it.

#### Python (backend + worker)

- **FastAPI dependency injection uses `Annotated`**: `session: Annotated[Session, Depends(get_session)]`. Do not regress to older `Depends()` default-arg style.
- **Auth dependencies are pre-baked**: `current_user` and `current_admin` from `app.core.auth.dependencies`. Use them as default values on parameters; do not re-implement JWT parsing in handlers.
- **Routers live under `app.modules.<name>.router` and mount with their own `prefix="/api/<name>"`.** New v1 endpoints: pick the right module (`auth`, `share`, `admin`, `sot`); v2 slots (`queue`, `spools`, `printer`, `requests`) exist in `apps/web/src/modules/` only — backend slots are NOT yet scaffolded as Python packages.
- **DB access via SQLModel `Session.exec(select(...))`.** No raw SQLAlchemy `Query`, no string SQL. Soft-delete pattern: `Model.deleted_at.is_(None)` is the live-row filter.
- **HTTP error surface uses `raise HTTPException(status, "message")`.** Don't catch-and-rewrap unless adding genuine context.
- **Loggers are namespaced**: `_LOG = logging.getLogger("app.<module>.<area>")`. Output is forced JSON via `app.core.logging.JsonFormatter`; do not configure handlers in modules. Canonical fields per `~/repos/configs/docs/observability-logging-contract.md`.
- **Settings come from `app.core.config.get_settings()`** (cached `pydantic-settings`). Don't read `os.environ` directly in modules.
- **ruff with `E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312 target.** Run `ruff check --fix` and `ruff format` before commit; both API and worker share the same config.
- **Worker depends on `portal-api` editable.** Shared SQLModel entities live in `app.core.db.models` and are imported by the worker; do not duplicate model definitions in `workers/render/`.

### Framework-Specific Rules

#### React 19 + TanStack stack

- **Routing:** TanStack Router with file-style modules. Routes live in `apps/web/src/routes/__root.tsx` and module-local route components in `apps/web/src/modules/<name>/routes/*.tsx`. Read params/search via `useParams({ from: "/path/$id" })` / `useSearch({ from: "..." })`, navigate via `useNavigate()`. The root route wraps `<AppShell><Outlet /></AppShell>`.
- **Server state via TanStack Query, not local state.** Each module has `hooks/use<Entity>.ts` that wraps `api(...)` calls in `useQuery` / `useMutation`. Query-key convention: `["<bounded-context>", "<entity>", ...filters]` — e.g. `["sot", "tags", q]`. Keep `staleTime` explicit; default of 0 is rarely what you want for catalog data.
- **Auth state lives in `AuthContext` (`apps/web/src/shell/AuthContext.tsx`)** and is consumed via `useAuth()`. Wrap protected subtrees in `<AuthGate>`. Do not compute auth state independently inside modules.
- **AppShell + ModuleRail + TopBar** are the only top-level chrome. Modules render INTO the shell via `<Outlet />`; never render a competing shell.
- **i18n is mandatory for user-visible strings.** Use `useTranslation()` + `t("namespace.key")`; add the key to both `apps/web/src/locales/en.json` and `pl.json`. Never hard-code Polish or English copy in a component — even error fallbacks (`t("errors.network")`).
- **Theme/dark mode** is governed by `ThemeProvider`; do not toggle classes manually. Dark variants come from `.dark { --color-* : ... }` in `theme.css`, picked up by Tailwind v4 automatically through `@custom-variant dark`.
- **3D rendering uses `@react-three/fiber` + `@react-three/drei`.** STL viewing is in catalog module — keep new viewer features there. Material/edge/grid colors must come from the `--color-viewer-*` tokens in `theme.css`, not hard-coded.

#### FastAPI (backend)

- **`create_app()` factory in `app/main.py`** is the only place that builds the FastAPI instance. It runs in this order: Sentry → OTel observability → FastAPI() → `instrument_app(app)` → `install_csrf_middleware(app)` → routers. Don't reorder; Sentry must come first to capture OTel setup errors.
- **Lifespan owns Redis + arq pool** (`app.state.redis`, `app.state.arq`). Handlers reach them via `request.app.state.redis.get()` / `request.app.state.arq`. Do not open ad-hoc Redis connections inside handlers.
- **Each module is `app.modules.<name>` and exposes a `router: APIRouter`** mounted in `app/router.py`. Admin write endpoints for an entity go in a sibling `admin_router.py` (see `share/router.py` vs `share/admin_router.py`); do not mix admin-only writes into the public router.
- **Schema ownership:** production schema is owned by Alembic — `deploy.sh` runs `alembic upgrade head` before the container starts. `init_schema(engine)` only fires when `environment != "production"` (dev/test). Adding columns or tables = new alembic migration in `apps/api/migrations/versions/`.
- **OpenAPI surface is at `/api/docs` + `/api/openapi.json`** (NOT `/docs`); the edge proxy only forwards `/api`.
- **Health endpoint contract:** `GET /api/health` → `{"status": "ok", "version": ...}`. Don't rename or restructure; deploy + uptime checks rely on it.

#### arq worker

- **`WorkerSettings` in `apps/api/app/workers/__init__.py`** is the single source of cron + on_startup hooks. New scheduled jobs add to `cron_jobs`; new task functions add to `functions`. The dedicated `arq-worker` container in `infra/docker-compose.yml` shares the API image but overrides the command to `arq app.workers.WorkerSettings`.
- **Render worker (`workers/render/`) is a separate process and image** with its own `WorkerSettings`. Do not collapse the two — render dependencies (matplotlib, trimesh) are heavy and stay isolated.
- **Worker tasks must be idempotent** (arq retries on failure). New tasks emit structured JSON logs through the same `JsonFormatter` plumbing.

### Testing Rules

#### Backend (`apps/api/`, `workers/render/`)

- **pytest with `asyncio_mode = "auto"`** — async tests don't need `@pytest.mark.asyncio`. `pytest-asyncio` is the runner; `pytest-cov` for coverage; `fakeredis` for Redis-dependent units.
- **Tests run isolated by `conftest.py` auto-fixtures** (`apps/api/tests/conftest.py`):
  - `_isolated_db` (session): tmpdir SQLite, schema initialized via `init_schema`, env vars set (`DATABASE_URL`, `JWT_SECRET="test-secret-not-real"`, `COOKIE_SECURE=false`, etc.). `get_settings.cache_clear()` + `get_engine.cache_clear()` — necessary because both are LRU-cached.
  - `_patch_arq_pool` (autouse): mocks `arq.create_pool`. **Tests never hit a real Redis.** Worker enqueues are asserted via the mock (`fake_pool.enqueue_job`).
- **`TestClient` from `fastapi.testclient`** drives HTTP tests. Because `COOKIE_SECURE=false` is set in the test env, cookie auth works over `http://testserver`.
- **Auth in tests** is exercised via the real login flow (`POST /api/auth/login` then ride the cookies), not by minting a JWT directly. This keeps tests honest about the cookie + CSRF surface.
- **CSRF in tests:** mutating requests must include `X-Portal-Client: web` (matches frontend behavior) — there's no test backdoor.
- **TDD discipline** for backend logic per AGENTS.md: red → green → refactor. New endpoints land with a failing test first.
- **Tests live in `apps/api/tests/test_<area>.py`**, fixtures in `apps/api/tests/fixtures/`. Worker tests live in `workers/render/tests/`.

#### Frontend (`apps/web/`)

- **Two test surfaces:**
  - `npm run test` — Vitest + Testing Library (jsdom). Unit + integration on hooks, components, utility code. Test files colocated as `*.test.ts` / `*.test.tsx`.
  - `npm run test:visual` — Playwright snapshot tests in `apps/web/tests/visual/*.spec.ts`. **Mandatory for any UI change.**
- **Visual regression matrix is fixed (4 projects):** `desktop-light`, `desktop-dark`, `mobile-light` (Pixel 5), `mobile-dark`. Locale `pl-PL`, timezone `Europe/Warsaw`. Run all four projects when touching UI.
- **API is stubbed for visual tests** via `apps/web/tests/visual/api-stubs.ts` — visual tests are deterministic and never hit a live backend. Add new stubs there when a route exercises new endpoints.
- **Snapshot updates:** `npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots`. Inspect `__snapshots__/` diffs intentionally; do not blanket-update without reading the visual delta.
- **Vitest tests are colocated** (next to the file under test). No separate `__tests__/` mirror tree.
- **Don't mock `api()`** — call through it; intercept at `fetch` level if you must (msw or vi.fn around `globalThis.fetch`). Mocking `api()` hides CSRF + 401-retry logic regressions.
- **Vitest `globals: false` → manual `afterEach(cleanup)` per test file.** With `globals: false` in `vitest.config.ts`, `@testing-library/react`'s auto-cleanup does NOT register; the second `it(...)` block in any test file accumulates DOM nodes from the first and fails with `Found multiple elements`. Until a global `setupFiles` is added, every new test file with multiple `it` blocks must include `import { cleanup } from "@testing-library/react"; afterEach(cleanup);`. Hit 3× during 2026-05-10 UI-review batch.
- **Visual smoke per UI-touching PR.** For any PR that mounts a rendered React component (not just hooks/config/utility), run a quick Playwright snapshot or take a manual screenshot at desktop+mobile before commit. Cost ~30s; benefit: catches visual regressions PR-by-PR while the mental model is fresh, not at end-of-batch when reverting is expensive. UI-review batch retro 2026-05-10 surfaced this — 3-of-8 smoke coverage was acceptable but risky.

#### Cross-cutting

- **No real network in any test.** Backend mocks arq + uses tmp SQLite; frontend stubs `/api/*` in visual, uses jsdom + mock fetch in vitest.
- **No time estimates, no flaky tolerations** — a flaky test is a bug to fix, not a `retry: 3` to add.
- **Sentry-test endpoint** (`POST /api/admin/sentry-test`, 204) deliberately throws to prove GlitchTip plumbing. It's an asserted endpoint, not an oversight; do not "fix" it.

### Code Quality & Style Rules

#### Frontend

- **ESLint 9 flat config** (`apps/web/eslint.config.js`). `npm run lint` runs `eslint . --max-warnings=0`. Zero warnings tolerated — `eslint-disable` comments need a justification in the same line.
- **Prettier formatter** (`npm run format`). Don't mix prettier-style and custom-style formatting in one file; prettier is the tiebreaker.
- **`react-refresh/only-export-components` is `warn`** but with `--max-warnings=0` it gates merges. Keep route components and providers as the only exports of their files; co-located non-component exports trigger the rule.
- **Ignored from lint:** `dist/`, `node_modules/`, `**/*.gen.ts` (generated types), `**/*.config.{ts,js}`, `tests/visual/__snapshots__/**`, `test-results/**`. Do not lint or hand-edit `*.gen.ts` — it's API type generation output.
- **Folder layout under `apps/web/src/`:**
  - `shell/` — top-level chrome (AppShell, ModuleRail, TopBar, AuthContext, AuthGate, Theme/Lang providers).
  - `modules/<name>/` — bounded contexts; each has `routes/`, `components/`, `hooks/`. v2 slots (`queue`, `spools`, `printer`, `requests`) hold "Coming soon" placeholders only.
  - `ui/` — shadcn/ui primitives and project-specific composites (e.g. `ui/custom/ModelCard`).
  - `lib/` — cross-module utilities: `api.ts`, `refresh.ts`, `api-types.ts` (generated), search helpers, etc.
  - `locales/` — `en.json`, `pl.json`. Both keep the same key set.
  - `routes/` — TanStack Router file routes (`__root.tsx`, `<module>/`).
- **Naming:** components `PascalCase.tsx`, hooks `useThing.ts`, utility modules `kebab-case.ts` only when they're not classes/components. Test files mirror the source name with `.test.` infix.
- **Imports order (enforced by prettier + eslint):** node/external → `@/...` aliases → relative. `import type` separated only when readability demands.

#### Backend

- **ruff is the single source of formatting + linting** (`ruff check --fix`, `ruff format`). Same config in `apps/api/pyproject.toml` and `workers/render/pyproject.toml`: `select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]`, `line-length = 100`, `target-version = "py312"`. No `black`, no `isort`.
- **Module layout under `apps/api/app/`:**
  - `core/` — cross-cutting plumbing: `auth/`, `config.py`, `db/` (engine, session, models, seed), `logging.py`, `observability.py`, `redis.py`, `sentry.py`. Modules import FROM core, not vice versa.
  - `modules/<name>/` — bounded contexts. Each has `router.py` (public surface) and optionally `admin_router.py` (admin writes), `service.py` (logic), `models.py` (Pydantic request/response shapes — DB models live in `core.db.models`).
  - `workers/__init__.py` — arq `WorkerSettings`.
  - `migrations/` — Alembic.
- **Naming:** modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`. Pydantic models suffix by purpose: `XRead`, `XCreate`, `XUpdate`, `XView` (e.g. `ShareModelView`, `LoginRequest`, `LoginResponse`). DB entities in `core.db.models` are bare nouns (`Model`, `Tag`, `User`).

#### Documentation

- **English in committed content** (code, comments, docstrings, commit messages, markdown docs). Polish stays in conversation only.
- **Comment policy:** comment the WHY when non-obvious (workaround, hidden constraint, surprising choice). Skip narrative WHATs that the names already convey.
- **Docs are sharded:** specs in `docs/design/<date>-<topic>.md`, plans in `docs/plans/<date>-<topic>.md`. Architecture overview in `docs/architecture.md`, runbook in `docs/operations.md`. AGENTS.md is the vendor-neutral source of truth — update it when a rule has cross-agent reach.

### Development Workflow Rules

#### Git

- **Trunk-only `main`, fast-forward merges only.** No merge commits, no rebase-merge that produces new SHAs without ff. Topic branches live briefly, then ff into `main`.
- **Branch naming:** `feat/<short-topic>`, `fix/<short-topic>`, `docs/<short-topic>`, `chore/<short-topic>`, `refactor/<short-topic>`, `test/<short-topic>`. Same convention as `~/repos/orca-profiles/`.
- **Conventional commits with a scope:**
  `feat(viewer3d): Diameter mode button`, `fix(api): cookie path on refresh`, `docs(catalog): rim detection design review`, `chore(deps): bump trimesh to 4.5.2`, `test(api): cover refresh-token rotation family`. Scope is the bounded context (`viewer3d`, `catalog`, `auth`, `share`, `sot`, `infra`, `deps`, `web`, `api`, `worker`, etc.). Subject in lower-case, no trailing period.
- **No remote at the time of writing** — first push gated on Michał's decision. Treat `origin` as TBD; don't add CI hooks that assume it.
- **No `--no-verify`, no `--no-gpg-sign`** unless explicitly asked; if a hook fails, fix the underlying issue rather than skip.

#### Deploy

- **Auto-deploy after every code/infra commit to `main`** by running `infra/scripts/deploy.sh` immediately, without asking. `.190` is dev/working — there is no separate staging.
- **Doc-only commits skip the deploy** (changes confined to `docs/`, root `*.md`, `AGENTS.md`, `CLAUDE.md`).
- **`deploy.sh` flow:** pulls canonical `infra/.env` from `.190` if missing locally → `docker compose build` locally → extracts `dist/` from the freshly built web image → uploads images and dist over SSH (`PORTAL_HOST`, `PORTAL_SSH_PORT`) → restarts the compose stack on `.190` → runs `alembic upgrade head` before the API container is healthy.
- **Edge proxy lives in `~/repos/configs/`** (not in this repo). Changes to `infra/nginx-180/3d-portal.conf` must be copied into `~/repos/configs/nginx/` and deployed via that repo's `sync.sh`. The portal repo's deploy doesn't touch the edge.
- **First-time setup is one-shot:** htpasswd for nginx, JWT secret via `openssl rand -hex 32`, GlitchTip project DSN. Each documented in `docs/operations.md`; do not re-run them on routine deploys.

#### Cross-repo touchpoints

Before non-trivial work, glance at:

- `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` — catalog schema and sync invariants.
- `~/repos/configs/docs/observability-logging-contract.md` — canonical log + trace fields.
- `~/repos/configs/docs/glitchtip-agent-guide.md` — frontend error tracking flow.
- `~/repos/orca-profiles/AGENTS.md` — git workflow Michał uses across repos.

#### AI agent execution discipline

These rules apply regardless of which workflow/skill is driving — they're the floor every agent stands on.

- **TDD for backend logic** — red → green → refactor. New endpoints land with a failing test first, not a "tests can come later" promise.
- **Visual regression is mandatory for any UI change** — `npm run test:visual` from `apps/web/`, all four projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`). A passing typecheck and lint do not substitute for a visual diff.
- **Verification before completion.** Never claim "done", "fixed", "passing", or "ready to merge" without running the actual command and reading the output. If you cannot run the verification (e.g. browser test in headless env), say so explicitly — do not assert success on inference.
- **Evidence before assertions.** Cite real file paths, line numbers, command output, log lines. "Should work" is not a status; "I ran X and it returned Y" is.
- **Plan before non-trivial implementation.** A spec or plan exists before code is written for any multi-step feature. Ad-hoc dives are reserved for one-shot fixes and Quick Dev intent.
- **Stop at unknown unknowns.** If a task hinges on a fact you don't have (cross-repo behavior, prod data shape, an unread spec), pause and surface the gap rather than guessing.
- **No silent scope creep.** A bug fix doesn't carry a refactor; a feature doesn't carry unrelated cleanup. If you find collateral work, list it and let Michał decide.

#### Workflow source of truth

- **BMAD owns the workflow in this repo** (planning + execution + review). The catalog of skills lives in `_bmad/_config/bmad-help.csv`.
- **Before starting ANY implementation work, route through BMAD first.** The first action of any non-trivial task is to pick the BMAD entry point — never start writing code or opening PRs ad-hoc, even when the task feels "scoped enough" or the user has already approved direction. If the routing isn't obvious, invoke `bmad-help`.
- Routing decision tree:
  - New feature / multi-PR initiative → BMAD planning chain (PRD → architecture → epics & stories → sprint planning → `bmad-create-story` → `bmad-dev-story`).
  - Single drobna zmiana / bugfix that fits in one commit → `bmad-quick-dev`.
  - Tests on existing code → BMAD `tea` module (`bmad-testarch-test-design`, `bmad-testarch-framework`, etc.).
  - Code review → `bmad-code-review`.
  - Post-epic / post-batch reflection → `bmad-retrospective`.
- **Multi-PR batches that emerged from a review or discovery doc are still epics in disguise** — they need stories under sprint-status.yaml and proper retro at the end. Failing this rule was the lesson from the 2026-05-10 UI-review batch (7 PRs shipped without sprint-status entries; retro happened only because Ezop asked).
- **BMAD planning artifacts are living singular documents.** `_bmad-output/planning-artifacts/prd.md`, `architecture.md`, and `epics.md` are project-wide growing docs. Each new scope/initiative EXTENDS them via a new `## Initiative N — <name>` section at the bottom — it does NOT fork them into per-delta files (`prd-v2.md`, `epics-glitchtip.md`, etc.). All three docs maintain an `## Initiatives Index` table near the top + an `initiatives:` frontmatter array. Convention adopted 2026-05-10 after Session 1 BMAD-canonical alignment; replaces the earlier delta-scoped framing of Initiative 1 (GlitchTip).
- **Use `bmad-edit-prd` to extend `prd.md`** for a new initiative. There is no analogous `bmad-edit-epics` / `bmad-edit-architecture` skill — extend `epics.md` and `architecture.md` manually in the existing Initiative-wrapper pattern (`## Initiative N — <name>` H2 → child H3 sections for Overview / Requirements / Epics / Decisions / etc.).
- **Epic numbering is project-global, NOT initiative-local.** `epics.md` Initiative 1 owns E1-E3; Initiative 2's first epic is E4, not E1. Story IDs follow (`E4.1`, `E4.2`, ...). `sprint-status.yaml` is already a global tracker by design — append new epics/stories there as in Initiative 1.

### Critical Don't-Miss Rules

#### Auth & sessions

- **Refresh tokens rotate on every use.** Reusing an already-rotated `portal_refresh` triggers **family invalidation** — every session for that user gets revoked. Tests, scripts, and migrations must NOT replay an old refresh token thinking it's a "spare". One refresh = one rotation.
- **Cookies have specific paths and don't move.** `portal_access` on `Path=/api`, `portal_refresh` on `Path=/api/auth`. Changing path = clients silently lose auth. The same applies to `httpOnly`, `Secure`, `SameSite=Strict` flags — only `Secure` is conditionally relaxed (`COOKIE_SECURE=false` for dev/test).
- **`/api/share/*` is the public bypass and stays that way.** Adding `Depends(current_user)` or `Depends(current_admin)` to anything under `/api/share/*` breaks public share-link viewing. Admin write ops on shares live under `/api/admin/share/*` (separate `admin_router.py`).
- **The 401 retry path checks `detail`.** `apps/web/src/lib/api.ts` only retries when the body's `detail` is `"access_expired"` or `"missing_access"`. Other 401s are real failures, not refresh candidates — don't expand the retry surface without thinking through CSRF + replay attacks.
- **`COOKIE_SECURE=false` is dev/test only.** Never ship it in `.env.production`. The test conftest already sets it; if production logs show `COOKIE_SECURE=false`, that's a leak.
- **Audit log writes go through `app.core.audit.record_event`.** Don't `INSERT INTO audit_log` directly; the helper enforces the canonical schema.

#### Catalog data integrity

- **The portal NEVER writes to the Windows catalog.** Windows → `.190` is a one-way rsync; portal-to-Windows writes are forbidden. New "edit on .190" features must stay on `portal-content` / `portal-state` and be reverse-synced via the agent token + `scripts/hydrate_local_tree.py`, not by mutating Windows paths.
- **Soft delete: filter live rows with `Model.deleted_at.is_(None)`.** Hard-deleting is wrong by default — soft-delete preserves audit trail and share-token integrity.
- **Schema migrations go through Alembic.** Adding a column = new migration in `apps/api/migrations/versions/`; `init_schema(engine)` is dev/test convenience only and silently no-ops in production.

#### Infra & deploy

- **Don't try to "build dist locally and upload it."** `deploy.sh` deliberately extracts `dist/` from the just-built web image to guarantee bundle-hash determinism — local node/pnpm versions would diverge from the image.
- **Don't edit nginx config from this repo and expect it to deploy.** The edge proxy lives in `~/repos/configs/`; changes to `infra/nginx-180/3d-portal.conf` are a draft until copied to `~/repos/configs/nginx/` and deployed via that repo's `sync.sh`.
- **The cleanup cron at 03:15 UTC is real.** `apps/api/app/workers/__init__.py` defines an arq cron in a dedicated `arq-worker` container that prunes expired/revoked refresh tokens. Don't move or rename it without updating the runbook.
- **`/api/health` is a contract.** Deploy + uptime checks call it; don't change shape (`{"status": "ok", "version": ...}`) or path.

#### Observability

- **Run `verify-symbolication.sh` after every deploy until CI auto-verify lands.** `infra/scripts/deploy.sh` calls it automatically after `alembic upgrade head` (Story 3.2). This rule applies if/when an agent runs a partial deploy or skips `deploy.sh` (e.g., copies an image manually, hot-swaps a service). NFR-R3's three-signal failure model (stdout warning + `infra/.last-verify FAILED` + synthetic GlitchTip event tagged `deploy.verification=failed`) only holds when the verify script actually runs.
- **Use `glitchtip-triage.sh <issue_id>` before manual triage of a GlitchTip-reported bug** (script ships in Story 2.5). The markdown stub IS the triage interface for AI agents; opening the GlitchTip web UI is the slow path. The fixed-order schema (`tests/golden/triage-schema.txt`) is paste-ready into `bmad-quick-dev` / `bmad-create-story`. Pull-only ergonomics is design, not a degraded mode.
- **Every replacement keeps its predecessor as documented manual recovery for one release cycle.** Codifies the brief's principle (see `infra/scripts/upload-sourcemaps.sh` retained alongside the in-build `@sentry/vite-plugin` upload — same `RELEASE` identity, same chunk-upload protocol; one is active, the other is the on-demand fallback). Promoted from this delta's local pragmatism into a repo-wide principle for any future swap of an active mechanism. The predecessor stays even if the active path is "obviously" working — graceful-degradation is the contract.

#### UI quality gates (Initiative 3 / Epic 5)

- **Baseline Acceptance Gate** — any commit touching `apps/web/tests/visual/__snapshots__/**/*.png` MUST include a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line per changed PNG in the commit message. Enforced by `apps/web/.husky/pre-commit` + `commit-msg` hooks via `_check-baseline-review.mjs`. The hook rejects commits missing any sign-off line (exit 1). Convention without tooling has historically been bypassed (see `ui-review-retro-2026-05-10.md` routing miss) — this rule's value comes from the mechanical gate, not the documentation. The hook fires automatically once `git config core.hooksPath apps/web/.husky` is set (handled by `npm run prepare` from `apps/web/package.json`).
- **Visual Coverage Contract** — any commit ADDING a new `apps/web/src/ui/*.tsx` MUST also stage a matching `apps/web/tests/visual/<basename>.spec.ts` (or `<basename>-*.spec.ts`) exercising the open state. Enforced by the same pre-commit hook via `_check-visual-coverage.mjs`. Applies to file ADDITIONS only (`--diff-filter=A`); modifying an existing primitive does not require a new spec. The matching-spec check is filename-pattern-based; deeper content validation (does the spec actually open the primitive?) is deferred to code review.

#### Frontend gotchas

- **Don't bypass `api()`** — raw `fetch("/api/...")` skips CSRF header + 401-retry path and silently breaks logged-in flows. Same applies to mutations in TanStack Query: the `mutationFn` calls `api()`.
- **Don't `!`-shortcut `noUncheckedIndexedAccess`.** `arr[0]!.foo` compiles but lies; the runtime crash is on you. Use a guard or default.
- **Don't mock `api()` in tests** — intercept at `fetch` level. Mocking the wrapper hides CSRF/retry regressions.
- **Don't paste pre-Tailwind-v4 / pre-shadcn-4 / pre-React-19 snippets.** They look right and break in subtle ways (config schema, theming, hooks). Re-derive against the live `theme.css` and current shadcn flow.
- **Visual regression is the gate, not typecheck.** Light/dark × desktop/mobile snapshots must update intentionally.

#### Backend gotchas

- **Don't open ad-hoc Redis connections.** Use `request.app.state.redis.get()` / `request.app.state.arq` — the lifespan owns connection lifecycle.
- **Don't bump OTel contrib pins to imagined `1.x` versions.** They legitimately stay on `0.5xb`. CI/typecheck will not catch a hallucinated version, install will.
- **Don't duplicate SQLModel entities in the worker.** The render worker imports from `app.core.db.models` via the editable `portal-api` dep. Forking the schema shape silently desyncs.
- **Don't read `os.environ` directly in modules** — go through `app.core.config.get_settings()` (cached). Direct env reads bypass test fixtures' env override.
- **Don't "fix" `POST /api/admin/sentry-test`.** It deliberately raises to prove GlitchTip plumbing — that's the contract.

#### Cross-cutting

- **No secrets in commits, plans, or `_bmad-output/`.** Memory note already says implementation plans stay local; the same applies to GPC outputs that inline hostnames or sample tokens. JWT secret + admin password live only in `.env.production` on `.190`.
- **`docs/plans/` is gitignored.** Don't move plans into a tracked path, even if the plan looks "publishable".
- **Cross-repo grounding before non-trivial work.** Catalog schema, observability contract, GlitchTip guide, orca-profiles git workflow — read the linked AGENTS.md first.

---

## Lessons codified through Initiatives 11–18

These additions extend the rules above with patterns that emerged after the file was first authored (2026-05-10). Where AGENTS.md already carries the authoritative text, the entry is a pointer — read AGENTS.md for the full rule; the bullet here exists so this file remains a single-pass agent briefing.

### Workflow + operator boundary

- **Autonomous ITCM mode is in force** (effective 2026-05-19; see AGENTS.md § "Autonomous development mode"). Once initiative business alignment is closed, the BMAD-aware agent owns the dev-and-fix pipeline end-to-end: which skill next, commit/merge/deploy timing, subagent-vs-inline, Codex-review-now-vs-after-batch. Operator intervenes only on real product blockers (architectural decisions, cross-repo coordination, hardware state, hard-gate failures, initiative close-out). Procedural confirmation traffic is off the table. The mandatory session-start `bmad-help` handshake is the one operator-visible check that survives autonomous mode.
- **Self-triggering is part of autonomous mode.** State check at session start (business alignment closed + active initiative + ready stories + tooling available) is sufficient signal to fire the run; no explicit "go" prompt required. Same for bug-fix sessions: an operator-reported incident with adequate context triggers; the agent does not wait for "OK, start fixing".
- **Vanilla-BMAD discipline is the floor** (AGENTS.md § "BMAD vanilla-first"). Any procedural deviation from standard skill flow is a bug unless there is a documented operator-approved strong reason. Route-around of a protesting skill, direct artifact edits bypassing `bmad-correct-course`, skipped session-start `bmad-help`, name-match skill selection ("create PRD" → `bmad-create-prd` on a finished `prd.md`) — all drift. The `## Initiative N` H2-append pattern in monolithic `prd.md`/`architecture.md`/`epics.md` is the *vanilla-compatible workaround* for the documented multi-initiative gap, NOT a drift.
- **Story branches are the unit of work; ff-only merges; no squash** (AGENTS.md § "Branching and workflow"). Per-commit history is what `codex review --commit <SHA>` consumes; squashing destroys that context. `infra/scripts/check-all.sh` is the one-shot gate wrapper. Deploy gate is range-based skip-prefix evaluation on `<last-deploy-sha>..HEAD`; the state file `infra/.last-deploy-sha` is gitignored and only updated on successful deploy.
- **Codex review-fix-commit chain is the close-out pattern.** Each story closes with `codex review --commit <HEAD>`; each round-N fix-up commit body documents (a) the Codex finding, (b) the fix, (c) the test verification, (d) the accepted trade-off when any. A chain may run many rounds without process collapse if each round closes a real edge case at diminishing real-world probability (Init 18 Story 30.2 ran 7 rounds with that property). Codex routing per `[[feedback_codex_model_routing]]`: `gpt-5.4-mini` for routine FE/perf; `gpt-5.5` for NFR-SECURITY adjacency (public-bypass family, open-redirect, auth boundary, concurrency primitives, data integrity).

### Spec-authoring discipline (Init 18 retro codification — TB-050 + TB-051)

- **Cache-coherence enumeration is mandatory for stories that fetch data and might share data with other surfaces.** Before authoring the AC block, fill a 5-row table — staleness budget / retry policy / cache propagation (mutations) / cache eviction on route exit / cache seeding on this route — once for the current story and once for any related route/hook. If two columns disagree, name the design choice (private cache vs canonical queryKey + observer-level force-fresh override) before the spec ships. Init 18 Story 30.2 ran 7 Codex rounds because four coupled invariants (revocation surfaces promptly; admin mutations propagate; probe + render atomic; share-seeded cache must not contaminate later `/catalog/<id>`) were not enumerated up front. Process aid promoted as Init 19 readiness (`triage-backlog.md` TB-050; pending the memory-file edit). Reference implementation of the terminus shape: `apps/web/src/routes/share/useShareModelProbe.ts` + `MemberShareView.tsx` unmount cleanup + the synchronous `qc.removeQueries` in the info-bar nav handler.
- **Magic constants in specs require contract-pointing justification.** Every numeric constant in AC (staleTime, gcTime, retry count, timeout, page size, rate-limit window, polling budget) must point to the *contract it serves*, not the *other place it appears*. `staleTime: 0 because "revocation must surface on next visit per FR18-X"` is good; `staleTime: 5min because "matches AuthContext meQuery staleTime"` is a category error — the contracts diverge. Init 18 Story 30.2 round-1 P1 was prescribed inline by the spec because the justification (matches meQuery) was true but irrelevant. Process aid promoted as Init 19 readiness (`triage-backlog.md` TB-051; pending the memory-file edit, bundled with TB-050).
- **Pre-enumeration phase** (`[[feedback_scp_pre_enumeration_phase]]`) asks "what files / methods / fixtures already exist?" before authoring tasks; the cache-coherence + magic-constant rules above extend it, not replace it. Pre-enumeration paid full price at INTAKE on Init 18 (3 would-be duplicate builds caught across the 3 stories); the cache-topology miss happened *after* pre-enumeration but *before* the design fully closed.

### Share-view + NFR carve-out boundary

- **Share-view scope boundary** (`[[feedback_share_view_scope_boundary]]` 2026-05-25 amendment): chrome affordance additions on the anonymous `/share/<token>` view are OK (Sign in / Lang / Theme — Story 30.3 shipped); CONTENT enrichment on the anonymous body is NOT OK. The line is mechanical: header gets affordances; carousel + STL list + 3D viewer + description + footer notice stay untouched. AC-7 invariant + diff-line-count check enforces this. Membership-path completion (Story 30.2 `MemberShareView` rendering canonical catalog detail when an authenticated member visits a share) is in scope per the same amendment; Phase B (anonymous CONTENT parity) remains a future-initiative candidate, NOT Init 18+ carry-over.
- **NFR carve-out reversal is a recognized pattern** (Init 10 → Init 18 reversal of NFR10-SHARE-SECURITY-1 `/auth/me` gating on `/share/*`). When loosening a defensive policy from an earlier initiative, the four-step recipe is: (1) explicit reversal in code with a comment block citing BOTH inits + BOTH rationales — Init 18 does this at `apps/web/src/shell/AuthContext.tsx:36-46`; (2) verify the actual invariant the policy was protecting is still enforced by a different mechanism — Init 18's NFR10 data contract is now carried by `fetchShareView` `credentials: "omit"` in `apps/web/src/lib/share-api.ts`, not by AuthContext gating; (3) pre-merge grep invariant proving (2) still holds; (4) capture as an explicit Decision in the SCP. Triage entry TB-052 holds this pattern as a *candidate* — promoted only when a second carve-out reversal surfaces, since N=1 makes the abstraction shape less confident. Until then, the in-place reference is Init 18 retro §2 W3 plus the `AuthContext.tsx:36` comment block.

### Init 11–18 retro carry-forwards (still live)

- **NFR10 credentialless contract on `/api/share/<token>/*`** is the binding rule for the anonymous public-bypass family. `apps/web/src/lib/share-api.ts` `fetchShareView` uses `credentials: "omit"`. `apps/api/app/modules/share/router.py` carries zero `Depends(current_*)` references (mechanical grep test `CONTRACT-1`). Do not relax either gate. The Init 18 Decision AB `/auth/me` carve-out is on AuthContext / route gating only, NOT on the data-fetch contract.
- **Mechanical route enforcement gate** (Init 6 Decision M, `apps/api/tests/test_route_enforcement_gate.py`) iterates the FastAPI route table and asserts each `/api/*` route either has an auth `Depends` or appears in `_PUBLIC_ROUTES`. This is the structural fix for the post-cutover audit High-002 drift class — adding a new `/api/*` route without picking auth-or-allowlist will fail this test.
- **Share-view threat-vector enumeration** (per `[[feedback_security_vector_enumeration]]`): cookie-sending, auth-state-consultation, browser-default-credentials, SPA reactivity, rate-limit bypass, token-leak vectors. Every share-touching story re-validates the six during impl; aggregate retro cross-checks them at initiative close.
- **Sprint-status is the canonical workflow tracker.** `_bmad-output/implementation-artifacts/sprint-status.yaml` carries epic/story status plus a rolling commit/deploy trail in inline comments. Multi-PR batches emerged from review or discovery docs are still epics in disguise — they need sprint-status entries and a retro at the end (UI-review batch 2026-05-10 lesson).
- **Visual baseline hygiene cadence** — baselines drift environmentally (Playwright / browser-render upgrades) on the order of days-to-weeks. The hygiene-commit pattern (single `test:` prefix commit with `baseline-reviewed:` sign-offs, "No runtime deploy" body note) handles it. `494223e` (2026-05-29) regenerated 26 baselines across 5 specs after a 4-day idle gap; the existing rule worked end-to-end. No scheduled cron yet — operator decides if `npm run test:visual` weekly becomes worth the triage cost (TB candidate TB-NEW-VISUAL-BASELINE-CADENCE, not promoted).

---

## Usage Guidelines

**For AI agents:**

- Read this file before implementing any code in `3d-portal`.
- Follow ALL rules exactly as documented.
- When in doubt, prefer the more restrictive option.
- Surface gaps or contradictions to Michał rather than guessing.

**For humans:**

- Keep this file lean and focused on agent needs.
- Update when the technology stack, auth flow, or deploy mechanics change.
- Review periodically; remove rules that become obvious as the team grows.
- This file is generated/maintained via the BMAD `bmad-generate-project-context` skill — re-run it for major refreshes rather than hand-patching wholesale.

Last Updated: 2026-05-29 (Init 19 readiness pass — added § "Lessons codified through Initiatives 11–18" capturing autonomous ITCM mode, vanilla-BMAD discipline, story-branch + Codex review chain, cache-coherence enumeration, magic-constant contract-pointing, share-view scope boundary, NFR carve-out reversal pattern, and live Init 11-18 carry-forwards. Authored 2026-05-29 by Laura/ITCM liaison; previously last regenerated 2026-05-13.)
