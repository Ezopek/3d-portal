# Agent Instructions — 3D Portal

Vendor-neutral source of truth for AI agents working in this repo. Per-platform pointers (e.g. `CLAUDE.md`) only carry platform-specific behavior.

## Project overview

Self-hosted 3D printing portal for Michał's homelab. v1 implements a catalog browser for the model collection at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`. Future modules (print queue, filament inventory, printer status, print requests) have architectural slots but no implementation in v1.

Authoritative spec: `docs/design/2026-04-29-portal-design.md`. Current implementation plan: `docs/plans/2026-04-29-portal-v1-implementation.md`. AI-agent execution rules and unobvious gotchas: `_bmad-output/project-context.md` (regenerated via the BMAD `bmad-generate-project-context` skill).

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

Single-developer repo with GitHub remote at `git@github.com:Ezopek/3d-portal.git`.

### Trunk

`main` is the only long-lived branch. History is linear (no merge commits) — use fast-forward merges only. Never force-push to `main`.

### Story branches (the unit of work)

Every BMAD story is implemented on its own short-lived branch — *not* in a series of commits directly on `main`. This prevents partial features from reaching `.190` via auto-deploy and lets `codex review --commit <SHA>` see complete context.

**Branch naming:** `feat/E{epic}.{story}-<kebab-slug>` (e.g. `feat/E5.14-catalog-filters`, `feat/E6.2-worker-snapshot-render`). For bug fixes and triage-backlog items the same shape with a different prefix: `fix/E5.11-deploy-hook` or `fix/TB-013-api-stubs`.

**Lifecycle:**

1. `bmad-dev-story` (or `bmad-quick-dev`) starts → create branch from `main`:
   ```bash
   git checkout main && git pull
   git checkout -b feat/E5.14-catalog-filters
   ```
2. Work happens on the branch — atomic commits per logical unit, fix-up commits stay on the branch (no longer pollute `main`).
3. Quality gates must all be green before merge:
   - `ruff format --check` + `ruff check` clean on `apps/api/` and `workers/render/`
   - `pytest` full suite green on `apps/api/`
   - `npm run lint --max-warnings=0` and `npm run test:visual` green on `apps/web/`
   - Codex review pass: `codex review --commit <HEAD-of-branch>` (per the review-fix-commit close-out pattern)
   - Pre-commit hook itself working (it has broken before — verify before relying on it)
4. Merge to `main` with fast-forward only — never a merge commit, never a squash:
   ```bash
   git checkout main && git merge --ff-only feat/E5.14-catalog-filters
   git branch -d feat/E5.14-catalog-filters
   git push origin main
   ```
   ff-only is mandatory because per-commit history is what `codex review --commit <SHA>` consumes; squashing destroys that context.
5. If `main` advanced and ff is no longer possible, rebase the branch onto `main` first, then ff-merge.

### Deploy gate (planned — design under review)

The eventual goal: `infra/scripts/deploy.sh` should skip the build/push cycle when a push to `main` is non-deploying. The first attempt (skip if HEAD commit prefix is `docs:` / `chore:` / `wip:`) was reverted on 2026-05-16 — multi-commit ff-merges ending in a `chore:` catch-up commit would silently swallow earlier code commits in the same push, which is exactly the failure pattern the gate is meant to prevent. Correct fix is range-based: check `<last-deploy-sha>..HEAD` and skip only when **every** commit in range is skip-prefixed, backed by a new `infra/.last-deploy-sha` state file written at the end of each successful deploy. Design + implementation deferred to a future iteration.

**Until the gate ships:** `feedback_auto_deploy_dev.md` continues to govern. The operator (or agent) decides per-push whether to invoke `deploy.sh` — doc-only pushes are skipped manually, code/infra pushes are deployed by hand.

Story branches still never trigger a deploy directly: their commits don't touch `main` until the final ff-merge.

### Trivial commits direct to main

Direct-to-main is allowed in three narrow cases — everything else goes through a story branch:

| Case | Commit prefix | Rule |
|---|---|---|
| Doc-only | `docs:` | Only `*.md`, `AGENTS.md`, `CLAUDE.md`, `_bmad-output/` docs. No code, no config, no infra. |
| Config-only without runtime effect | `chore:` | E.g. `_bmad/_config/`, `.gitignore`, formatter config. If it changes how the app runs, it's not a chore — it's a fix or feat and goes on a branch. |
| Hotfix | `fix:` + `# hotfix-rationale: <reason>` in body | Production-level urgency only. Run Codex review inline (`codex review --commit <SHA>`) immediately after pushing. |

Threshold check before committing direct: *would I want this in its own grouping in `git log` looking back?* If yes — story branch. If no — direct commit OK.

### Parallel story work — deferred

The team considered enabling parallel work on two stories at once (e.g. Ezop on a frontend story interactively while Claude/Codex runs a worker story autonomously). **Deferred** — current single-developer pace doesn't justify the tooling cost. If parallel work becomes a real bottleneck, the minimum viable setup is:

1. `git worktree add ../3d-portal-E{N}.{M} feat/E{N}.{M}-<slug>` — one working dir per story; avoids file conflicts.
2. `_bmad-output/implementation-artifacts/sprint-status.yaml` — multiple `in-progress` slots simultaneously; resolve any merge conflict manually at close-out.
3. `flock /tmp/3d-portal-deploy.lock infra/scripts/deploy.sh` — serialize deploys so two near-simultaneous merges to `main` can't race on `.190`.

Until then: one story `in-progress` at a time, serial merges.

### Don't

- Don't force-push `main`.
- Don't create merge commits on `main` (always ff). If you can't ff, rebase the branch first.
- Don't squash-merge story branches — per-commit history is what Codex reviews.
- Don't keep stale story branches after merge — delete them with `git branch -d`.
- Don't bypass the story-branch flow for code/infra changes just because "this one is small". The threshold is in the table above — code changes outside `docs:` / `chore:` always go on a branch.
- Don't commit secrets just because the remote is private. Hostnames and IPs already in committed docs (`docs/operations.md`, `infra/`) are acceptable; never add API tokens, passwords, or fresh keys.

## Workflow expectations

BMAD owns planning + execution + review in this repo. Skill catalog: `_bmad/_config/bmad-help.csv`.

- Agents with BMAD skills (e.g. Claude Code) invoke `bmad-help` when unsure where to start.
- Agents without BMAD skills (e.g. Codex, Gemini) read `_bmad-output/project-context.md` for execution rules and the relevant story spec in `_bmad-output/` before implementing.

Typical routing for Claude Code:

- New feature → BMAD planning chain (PRD → architecture → epics & stories → sprint planning → story cycle).
- Small change or bugfix → `bmad-quick-dev`.
- Tests on existing code → BMAD `tea` module (`bmad-testarch-test-design`, `bmad-testarch-framework`, etc.).

### Execution discipline

These rules apply to every agent regardless of platform:

- **TDD for logic-bearing code** — red → green → refactor. New behavior lands with a failing test first, not a "tests can come later" promise.
- **Verification before completion** — never claim "done", "fixed", or "passing" without running the actual command and reading its output. If verification isn't possible in the current environment, say so explicitly rather than asserting success on inference.
- **Evidence before assertions** — cite real file paths, line numbers, command output, log lines. "Should work" is not a status; "I ran X and it returned Y" is.
- **Mandatory visual regression for UI changes** — `npm run test:visual` from `apps/web/` before any commit that touches the frontend.
- **Plan before non-trivial implementation** — multi-step features need a spec or story; ad-hoc dives are reserved for one-shot fixes.
- **Systematic debugging on any bug, test failure, or unexpected behavior** — reproduce → narrow → root-cause → fix → verify. No fix-first guesses.
- **No silent scope creep** — a bug fix doesn't carry a refactor; a feature doesn't carry unrelated cleanup. Surface collateral work and let Michał decide.

Full execution rules and project-specific gotchas: `_bmad-output/project-context.md` — read it before implementing.

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
