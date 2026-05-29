---
title: "Product Brief Distillate: 3d-portal — Product Foundation (Initiative 0)"
type: llm-distillate
source: "product-brief-3d-portal.md"
created: "2026-05-15"
purpose: "Token-efficient context for downstream PRD creation (Initiative 0 / Product Foundation backfill). Captures the load-bearing technical facts of the v1 portal that the executive brief glosses over."
---

# Distillate — 3d-portal Product Foundation

Reference detail for the actual portal product (catalog + share + render + admin + agent surface). Layered with: Initiative 1 (GlitchTip delta — see `product-brief-3d-portal-glitchtip-distillate.md`), Initiative 2 (Agent runbook), Initiative 3 (UI theme hardening). This distillate covers ONLY the foundation.

---

## Frozen technical facts — system topology

- **Two-host deployment:** `.180` (nginx edge LXC, DDNS TLS + household basic-auth + share-bypass location rules) → `.190` (Docker Compose stack).
- **Public URL:** `https://3d.ezop.ddns.net` (DDNS, ezop.ddns.net domain).
- **`.190` compose services:** `web` (nginx + React `dist/`, `127.0.0.1:8080`), `api` (uvicorn + FastAPI, `:8000`), `worker` (arq, no HTTP port), `redis` (queue + share-token TTL).
- **Volumes:** `portal-state` (small — SQLite at `/data/state/portal.db`), `portal-content` (large — STL, photos, renders; mounted rw by api + worker).
- **Backup posture:** SQLite nightly cron → `/mnt/raid/3d-portal-state/backups/portal-YYYY-MM-DD.db`, 30-day retention. RAID below for content volume; no per-file backup.
- **Single host = dev + prod.** `.190` is the working environment per [[feedback_auto_deploy_dev]]. Every successful merge to `main` triggers `infra/scripts/deploy.sh` (doc-only commits skipped).

## Frozen technical facts — frontend (apps/web/)

- **React 19 + TypeScript 5.6 strict** (`noUncheckedIndexedAccess`, `verbatimModuleSyntax`, `isolatedModules`). Use `import type` for type-only imports.
- **Vite 6 build, Tailwind v4** (`@import "tailwindcss"` + inline `@theme {}` block; **no `tailwind.config.js`**).
- **shadcn/ui 4.x flow** on `@base-ui/react` + Radix; components land in `apps/web/src/ui/` via `npx shadcn add`.
- **TanStack Router 1.x + Query 5.x.** Routes are file-style under `apps/web/src/routes/`. Root wraps `<AppShell><Outlet /></AppShell>`. Module-local routes also live under `apps/web/src/modules/<name>/routes/*.tsx`. Read params via `useParams({ from: "/path/$id" })`.
- **State convention:** server state in TanStack Query (`["<bounded-context>", "<entity>", ...filters]`), auth state in `AuthContext` (single source via `useAuth()`), never recompute auth inside modules. Wrap protected subtrees in `<AuthGate>`.
- **HTTP helper `api()` from `@/lib/api` is MANDATORY.** Attaches `X-Portal-Client: web` CSRF header, sets `credentials: "include"`, retries once on `401 access_expired` via silent refresh. Bypassing with raw `fetch` silently breaks auth + CSRF.
- **API errors throw `ApiError`** (status, body, message). UI catches it; no per-call status parsing.
- **i18n is mandatory** for user-visible strings — `useTranslation()` + `t("namespace.key")`, parity required in `apps/web/src/locales/{en,pl}.json`. Never hard-code Polish or English (even fallbacks).
- **Theme is token-driven** via `apps/web/src/styles/theme.css`. CSS variables in `@theme {}`, dark variant via `.dark { --color-* }`. **No inline hex anywhere in .tsx/.ts.** New colors → add `--color-*` token, then use the Tailwind class.
- **Viewer3D (three.js Color) requires legacy CSS HSL syntax** in `--color-viewer-*` tokens — comma-separated `hsl(H, S%, L%)`. Space-separated silently parses to white, breaks MeshStandardMaterial. See [[feedback_threejs_hsl_parsing]].
- **3D rendering uses `@react-three/fiber` + `@react-three/drei`.** STL viewer lives in catalog module. Material/edge/grid colors come from `--color-viewer-*`.
- **Sentry SDK 8.x** wired via `apps/web/src/instrument.ts`. Release constant in `apps/web/src/release.ts` (single source for SDK + vite-plugin upload). Initiative 1 added `@sentry/vite-plugin` 5.2.x.
- **ESLint must pass with `--max-warnings=0`** (`npm run lint` from `apps/web/`). No silenced warnings.
- **Vitest globals=false.** Auto-cleanup from `@testing-library` does NOT run by default. Per [[feedback_vitest_manual_cleanup]] a global `vitest.setup.ts` registers `afterEach(cleanup)` once (commit `a026e97`).

## Frozen technical facts — backend (apps/api/)

- **Python 3.12, FastAPI ≥0.115, Pydantic 2.9, SQLModel 0.0.22, Alembic ≥1.14, PyJWT ≥2.10, bcrypt ≥4.0.**
- **App factory:** `app.main.create_app()`. Order: Sentry → OTel observability → `FastAPI()` → `instrument_app(app)` → `install_csrf_middleware(app)` → routers. Sentry must come FIRST to capture OTel setup errors.
- **Lifespan owns Redis + arq pool** (`app.state.redis`, `app.state.arq`). Handlers reach via `request.app.state.*`. No ad-hoc Redis connections inside handlers.
- **Routers under `app.modules.<name>`** with own `prefix="/api/<name>"`. Admin write endpoints go in a sibling `admin_router.py` (`share/router.py` vs `share/admin_router.py`); never mix admin writes into public router.
- **FastAPI DI uses `Annotated`:** `session: Annotated[Session, Depends(get_session)]`. Auth dependencies pre-baked: `current_user`, `current_admin` from `app.core.auth.dependencies`. No re-implementing JWT parsing in handlers.
- **DB access via SQLModel `Session.exec(select(...))`.** No raw SQLAlchemy `Query`, no string SQL. Soft-delete pattern: `Model.deleted_at.is_(None)` is the live-row filter.
- **HTTP errors:** `raise HTTPException(status, "message")`. Don't catch-and-rewrap without adding context.
- **Loggers namespaced:** `_LOG = logging.getLogger("app.<module>.<area>")`. JSON output forced via `app.core.logging.JsonFormatter`. Canonical fields per `~/repos/configs/docs/observability-logging-contract.md`.
- **Settings via `app.core.config.get_settings()`** (cached `pydantic-settings`). Don't read `os.environ` directly in modules.
- **ruff config:** `E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312 target. `ruff check --fix` + `ruff format` before commit. Same config for api + worker.
- **Migrations:** 11 versions to date (`0001_initial.py` through `0011_index_ext_link_url.py`). Notable schema events: `0005` user_uuid + audit_log, `0009` refresh tokens, `0011` ExternalLink URL index.

## Frozen technical facts — worker (workers/render/)

- **arq + trimesh ≥4.5 + matplotlib ≥3.9 + Pillow ≥11.**
- **Editable dep on `portal-api`** — shared SQLModel entities live in `app.core.db.models` and are imported. Do NOT duplicate model definitions in `workers/render/`.
- **Render output:** 4 isometric PNG views per model, written back as `ModelFile` rows under `portal-content`.
- **Trigger paths:** `POST /api/admin/models/{model_uuid}/render` (single, optional `selected_stl_file_ids: []` body), `infra/scripts/render-all.sh "<bearer-jwt>"` (bulk).
- **Job status TTL:** 1 hour — stuck "running" self-clears.

## Frozen technical facts — auth + CSRF + share

- **Auth mechanism:** cookie + password flow (NOT bearer token). 2026-05-10 correction: agent.token/Bearer narrative in earlier docs was wrong; real flow is cookie + password matching `apps/api/app/modules/sot/admin_router.py` + `bootstrap_agent.py`.
- **JWT login:** `POST /api/auth/login` (bcrypt verify), refresh via `POST /api/auth/refresh` (refresh tokens with rotation, migration `0009`).
- **CSRF middleware:** browser writes require `X-Portal-Client: web` header. Frontend `api()` attaches automatically.
- **Roles:** `User.role ∈ {admin, member, agent}` enum. `admin` and `agent` are wired; `member` is v2 slot (member-print-requests).
- **Share lifecycle:** token stored in Redis with native TTL. Public route `/share/<token>` + API `/api/share/<token>` both bypass household basic-auth via nginx location rules in `infra/nginx-180/3d-portal.conf`. Revoke via admin UI or `DELETE /api/admin/share/{token}`.

## Frozen technical facts — observability + agent surface

- **GlitchTip:** homelab `:8800` (LAN HTTP for chunk-upload), `https://glitchtip.ezop.ddns.net` (DDNS public for SDK ingestion). Single shared DSN; service distinguished via `setTag('service', 'web'|'api'|'render')`.
- **Sourcemap upload:** `@sentry/vite-plugin` 5.2.x inside docker build context (BuildKit `--mount=type=secret,id=sentry_token`). Fallback: `bash infra/scripts/upload-sourcemaps.sh` (legacy CLI flow, kept as documented manual recovery for one release cycle).
- **OpenTelemetry distro 0.50b0** instruments FastAPI / Redis / SQLAlchemy → OTLP-HTTP exporter → homelab collector. Pinned contrib versions (no stable 1.x yet for these packages).
- **Structured JSON logs** per `~/repos/configs/docs/observability-logging-contract.md` — load-bearing for agent triage.
- **Agent runbook** served at `/agent-runbook` (FastAPI route in `apps/api/app/modules/runbook/`). Initiative 2 adds OpenAPI enrichment with operation IDs for agent consumption.
- **Triage scripts:** `infra/scripts/glitchtip-triage.sh <issue_id>` produces a markdown story stub for `bmad-quick-dev` / `bmad-create-story`. `infra/scripts/verify-symbolication.sh` is a post-deploy smoke check.

## Constraints — non-negotiable

- **Server owns the SoT.** The portal DB + content volume are authoritative. Windows/Nextcloud folder is a bootstrap source, not a real-time mirror. Reverse-sync flows server → WSL via `scripts/hydrate_local_tree.py` (cookie + password flow).
- **English in committed content** (code, docs, commit messages, file content). Polish stays conversational only.
- **Auto-deploy after every code/infra commit to `main`** ([[feedback_auto_deploy_dev]]). Doc-only commits skipped.
- **Mandatory visual regression** for any UI change. `npm run test:visual` from `apps/web/`. Baselines committed.
- **Plans/internal docs stay local** ([[feedback_local_only_docs]]). `_bmad-output/` and `docs/plans/` are gitignored.
- **TDD red → green → refactor** for code with logic. New behavior lands with a failing test first.
- **Verification before completion.** Never claim "done" without running the actual command and reading the output. Evidence > inference.
- **No silent scope creep.** A bug fix doesn't carry a refactor. Collateral work is listed and the user decides.

## Rejected approaches

### Hard never — confirmed by Ezop 2026-05-15

- **Multi-tenant catalog.** Single household, single SoT, single admin. No per-user catalog, no isolation surface, no "tenants" abstraction. The one architectural choice that will NEVER be revisited. Removes ~50% of the system complexity by construction.
- **One-way Windows → server rsync as SoT.** Replaced because metadata had nowhere to live; deletes propagated; no audit log. Server-owned SoT with reverse-sync is the only path forward.
- **Bearer token for the agent role.** Earlier docs said "agent.token / Bearer"; reality is cookie + password matching `bootstrap_agent.py`. 2026-05-10 correction is authoritative.

### Not in current plans, but not ruled out forever (Ezop did NOT affirmatively exclude these 2026-05-15)

- **Public marketplace surface.** Share links are point-to-point today; whether the portal ever grows a discovery surface is undecided. Not in v1, not in any planned initiative — but the door isn't closed.
- **Per-printer fleet management.** The `printer/` slot is sized for a single Moonraker-driven printer. Multi-printer fleet isn't in plans; if Ezop ever runs multiple printers and wants central management, that becomes its own initiative.
- **React Native / Capacitor mobile app.** Responsive web is enough today; a native app isn't in the roadmap but isn't ruled out as a category.

### Out of scope for v1, but already in the future-proofing slots (real intent — confirmed 2026-05-15)

- **Per-user accounts beyond admin.** Household basic-auth at the nginx edge is the user model for browsers in v1. `member` role is scaffolded but not wired to per-user views. Per-user accounts arrive with the member-print-requests initiative; OIDC vs. native auth decision is open.
- **Moonraker integration / real-time printer telemetry.** Future initiative when at least one Moonraker-driven printer is running consistently.
- **Spoolman integration.** Future initiative when Spoolman is in the homelab.
- **Postgres migration.** SQLModel + Alembic make the swap a `DATABASE_URL` flip; v1 ships on SQLite because volume is tiny. Flip when SQLite hits a real ceiling.
- **OpenSearch full-text backend.** Cluster available at homelab `https://192.168.2.190:9200`; v1 catalog queries SQLite directly. Flip when SQLite text search becomes a bottleneck.
- **HA / multi-host deployment.** Single-host failure means portal offline; acceptable for v1. Flip when the downtime budget changes.

## Anti-patterns named (avoid when extending)

- **Rendering inside the API process.** All renders go through arq → worker. The API never blocks on a render.
- **Bypassing `api()` helper from frontend.** Raw `fetch` silently breaks CSRF + silent refresh; never appropriate.
- **Inline hex colors in .tsx/.ts.** Always go through a `--color-*` Tailwind token.
- **Hard-coded Polish or English copy** — even fallback strings. Always `t("namespace.key")` with parity in both locale JSONs.
- **Re-implementing JWT parsing in handlers.** Use `current_user` / `current_admin` dependencies, period.
- **Opening ad-hoc Redis connections.** Use `request.app.state.redis` / `request.app.state.arq`.
- **Reordering `create_app()` setup.** Sentry must come first; CSRF middleware before routers.
- **Forking planning docs** (`prd-v2.md`, `architecture-glitchtip.md`, `epics-foundation.md`). The living-doc structure forbids forks — extend the same file as a new Initiative section.
- **`prd-validation-report.md` rescoping.** When new initiatives ship, validate them in additional reports — do NOT mutate the existing 2026-05-09 validation log for Initiative 1.
- **Top stack frame symbolicating to a minified `app-DhGq2.js:13`.** Initiative 1 made debug-ID symbolication mandatory; any regression here is a P0 (see [[feedback_visual_failure_mode_triage]] for triage discipline on this class of failure).
- **Mocking the database in integration tests** — banking-IT debugging culture transferred here. Real Session, real Postgres-fake (sqlite in-memory if needed), no Mocks of `Session.exec`.

## Stakeholder map

Voice-validated 2026-05-15 via guided elicitation. Self-described identity for the primary persona: *"AI-loop operator + pasjonat druku 3D; solo-dev coraz mniej — w czasach agentów wolę delegować bardziej doświadczonym."*

| Persona | Surface | Decision power | Real-world use |
|---|---|---|---|
| Ezop — AI-loop operator + 3D-printing enthusiast | Admin UI, JWT-gated `/api/admin/*`, audit log, deploy script | All — solo owner | Daily-driver; the "aha moment" is browsing the catalog from his phone outside the house |
| Household member (spouse / parents / kids) | Read-only catalog browse via basic-auth | None (no admin) | Confirmed regular use 2026-05-15 — "did you print that thing for the fridge yet?" lookups happen |
| Share-link recipient outside the household | `/share/<token>` only | None | Confirmed real but sporadic use 2026-05-15 — lifecycle works whether invoked 0 or 50 times |
| AI agent (Claude / Codex / Gemini) — first-class by design | `/agent-runbook`, `/openapi.json`, `/api/sot/*` (cookie auth), GlitchTip REST, BMAD planning chain | Operates within Ezop's authority — every action eventually flows through Ezop's review and decision | Increasing share of work over time; design weighted AI ergonomics equally with human ergonomics from the 2026-04-29 spec onward |

No external stakeholders (no corp customer, no compliance audit, no SLA). The product is for Ezop first, household second, AI agents third (but with first-class ergonomic weight in the design).

## Maintainer's stance on "done"

Captured verbatim 2026-05-15 during guided elicitation:

> "Generalnie to na zasadzie 'używam i jest mi z tym dobrze' — ale ja nie widzę takiego docelowego stanu. W sensie: co zrobimy jedną funkcjonalność, to zaraz mi przychodzi do głowy kolejna. Więc obawiam się, że nie będzie takich Success targetów. Byłbym/jestem ciężkim klientem biznesowym."

Implication for downstream PRD planning: **do NOT structure Initiative 0 (or the product as a whole) around fixed success metrics borrowed from commercial-product templates** (retention, NPS, DAU, error budget). The portal succeeds when (a) Ezop keeps using it as his daily driver, and (b) the three drivers from v1 (metadata + remote browse, share + audit, AI-agent ergonomics) stay satisfied. Subsequent initiatives (1-3 + future) each carry their own bounded success criteria — but the product-level success is not measured beyond "still being used + still being extended".

## Open questions deferred to future initiatives

- **Per-user auth model for member-print-requests.** OIDC via existing homelab Authentik vs. native portal accounts. Gate: print-requests initiative.
- **OpenSearch full-text backend.** Gate: SQLite text search becomes a noticeable bottleneck.
- **Postgres migration.** Gate: SQLite hits a real ceiling (storage size, concurrency, replication need).
- **CI runner.** Today there is no CI; every check runs manually before deploy. Gate: a homelab CI runner (likely Forgejo Actions on existing self-hosted Forgejo) gets stood up.
- **HA / multi-host.** Single-host failure means portal offline. Gate: acceptable downtime budget changes.
