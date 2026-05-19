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
   - `npm run lint --max-warnings=0`, `npm run typecheck`, `npm run test`, and `npm run test:visual` green on `apps/web/`
   - Codex review pass: `codex review --commit <HEAD-of-branch>` (per the review-fix-commit close-out pattern)
   - Pre-commit hook itself working (it has broken before — verify before relying on it)

   One-shot wrapper: `infra/scripts/check-all.sh` runs every gate above (skip
   individual stages with `SKIP_VISUAL=1`, `SKIP_PYTEST=1`, etc.). Opt in to
   auto-run on push with `git config core.hooksPath .githooks`.
4. Merge to `main` with fast-forward only — never a merge commit, never a squash:
   ```bash
   git checkout main && git merge --ff-only feat/E5.14-catalog-filters
   git branch -d feat/E5.14-catalog-filters
   git push origin main
   ```
   ff-only is mandatory because per-commit history is what `codex review --commit <SHA>` consumes; squashing destroys that context.
5. If `main` advanced and ff is no longer possible, rebase the branch onto `main` first, then ff-merge.

### Deploy gate (active)

`infra/scripts/deploy.sh` evaluates a **range-based skip-gate** before any build/push work. It compares each commit in `<last-deploy-sha>..HEAD` against `SKIP_PREFIXES=("docs:" "chore:" "wip:")` and skips the deploy **only when every commit in the range is skip-prefixed**. Any single non-skip commit (e.g. `feat:`, `fix:`) forces the full deploy.

**State file:** `infra/.last-deploy-sha` — local, gitignored, holds the full SHA of the last successfully deployed commit. Written **only** at the end of a successful deploy run; skipped pushes leave it unchanged. That "no update on skip" property makes the gate composable: three consecutive `docs:` pushes still let a subsequent `feat:` push see the whole accumulated range.

**Lifecycle:**

| Situation | Behavior |
|---|---|
| First run after this gate lands (state file missing) | stderr `WARN`, deploy normally, write HEAD on success |
| `HEAD == last-deploy-sha` (empty range) | stdout `[deploy-skip] no new commits since last deploy`, exit 0 |
| All commits in range skip-prefixed | stdout `[deploy-skip] all N commits ... skip-prefixed`, exit 0, state file unchanged |
| At least one non-skip commit in range | Full deploy; on success write new HEAD to state file |
| State SHA unresolved (rebased / GC'd) | stderr `WARN: unresolved`, deploy normally, overwrite state on success |

**Match rules:** prefix match is exact, case-sensitive, includes the trailing colon. `docs:` matches `docs: x`; `Docs:`, `documentation`, and `chore(release):` do **NOT** match (scoped Conventional Commits bypass the gate and deploy — extending to `chore(*):` is a future call).

**No bypass flag.** "Deploy state of `.190` = main HEAD" invariant is preserved by design. The escape hatch when a skip-prefixed commit really needs to deploy: amend the commit message to a non-skip prefix.

Story branches still never trigger a deploy directly — their commits don't touch `main` until the final ff-merge.

The design history (including the abandoned HEAD-only first attempt that swallowed code commits in mixed ff-merges) is in `_bmad-output/implementation-artifacts/spec-deploy-skip-gate.md` (status `abandoned`) and the active spec `spec-deploy-skip-gate-range.md`.

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

- **Agents with BMAD skills (e.g. Claude Code) MUST invoke `bmad-help` at the start of every session before any planning or implementation work.** `bmad-help` reads `_bmad/_config/bmad-help.csv` (the skill catalog with `phase` + `after` dependencies) and recommends the canonical entry skill for the current lifecycle stage. Skipping it is the most common BMAD drift trigger and is the single biggest cause of agents reaching for the wrong skill by name-match. The only exempt sessions are trivial single-shot tasks where no BMAD ceremony applies (typo fix, single-file Q&A); when in doubt, run it — cost is ~30s.
- Agents without BMAD skills (e.g. Codex, Gemini) read `_bmad-output/project-context.md` for execution rules and the relevant story spec in `_bmad-output/` before implementing.

Typical routing for Claude Code:

- New feature in **greenfield context** (no prior PRD/architecture artifacts) → full BMAD planning chain (PRD → architecture → epics & stories → sprint planning → story cycle).
- New feature in **brownfield context** (PRD/architecture already exist — the normal case here) → `bmad-correct-course` FIRST. It analyzes the change and routes to the right ceremony (PRD edit, architecture rerun, new epics, sprint planning update). The full planning chain is for greenfield only — do not invoke `bmad-create-prd` on a finished `prd.md`.
- Small change or bugfix → `bmad-quick-dev`.
- Tests on existing code → BMAD `tea` module (`bmad-testarch-test-design`, `bmad-testarch-framework`, etc.).
- **Mid-session scope pivot → re-invoke `bmad-help`.** If the work shifts (was planning, now implementing; was bug-fix, now feature; surprised by an unfamiliar artifact state), the session-start call no longer covers the new task — re-run `bmad-help` to confirm the new canonical entry.

### BMAD vanilla-first

**Vanilla BMAD skill discipline is the default. Any procedural deviation from standard skill flow is treated as a bug** unless there is a documented, operator-approved strong reason. The procedural drifts to avoid: routing-around a protesting skill, direct artifact edits that bypass a `bmad-correct-course` recommendation, skipping mandatory session-start `bmad-help`, treating BMAD as a library of named skills matched by user-verb (e.g. *"create PRD"* → `bmad-create-prd`) rather than as a methodology with phase ordering and routing.

**On doc shape** — vanilla BMAD assumes a single project-wide PRD/architecture/epics model (per `docs.bmad-method.org/llms-full.txt`: *"BMAD assumes a single project-wide PRD model. The documentation does not address multi-initiative brownfield scenarios."*). Every vanilla planning skill hardcodes singular `outputFile = {planning_artifacts}/{prd,architecture,epics}.md`. This repo's `## Initiative N` H2-append pattern in monolithic `prd.md`/`architecture.md`/`epics.md` is the **pragmatic workaround** for that documented methodology gap — it is the closest-to-vanilla shape attainable for multi-initiative brownfield, and IS the pattern new initiatives extend (via `bmad-edit-prd` on `prd.md` + manual edits on architecture/epics, since no `bmad-edit-architecture` or `bmad-edit-epics` skill exists).

**Skill discovery checklist for any non-trivial BMAD task:**

1. Confirm `bmad-help` has been called for the current session (mandatory at session start per the rule above; re-call after any mid-session scope pivot). If somehow skipped, run it NOW before proceeding.
2. Check `_bmad/_config/bmad-help.csv` for `phase` + `after` dependencies before invoking any skill. Misalignment with current project state → reconsider.
3. `bmad-correct-course` is the canonical entry point for ANY post-ship scope change — PRD edits, architecture changes, scope corrections, new features after MVP, mid-sprint adjustments. Per its catalog description: *"May recommend start over, update PRD, redo architecture, sprint planning, or correct epics and stories."* It is not just for emergencies.
4. If a skill rejects the current state (e.g. `bmad-create-prd` detects `step-12-complete` and refuses), STOP and consult the operator before routing to a different skill. Never silently switch skills to work around a protest.

Background: the 2026-05-18 retro on the (since-reverted) user-accounts initiative caught a recurring drift pattern — the agent treats BMAD as a library of named skills (matching operator verbs to skill names: *"create PRD"* → `bmad-create-prd`) rather than as a methodology with phase ordering and routing. `bmad-help` and `bmad-correct-course` exist precisely to short-circuit that pattern. A subsequent recalibration pass (2026-05-18 v2) corrected an earlier-in-this-section misframing: the H2-append doc pattern is a vanilla-compatible pragmatic workaround, NOT a drift. Only procedural skill-discipline violations are drifts.

### Autonomous development mode (ITCM rule, effective 2026-05-19)

**Once the business side is settled — brief, PRD, architecture, epics aligned and approved (or a bug report has enough context to start root-causing) — Claude takes full operational ownership of development and coordination.** Ezop's role flips to operator-level intake: receive results, decide on real product blockers, sign off at initiative completion. Procedural confirmation prompts ("which skill next?", "should I commit?", "ready for next session?", "spawn subagent or inline?") are OFF the table. Same rule for bug-fix work — Claude leads investigation + reproduction + fix + verification; asks ONE focused question if external incident details are genuinely missing, never a guided walkthrough.

**Tools to use autonomously:** subagents (`Agent` tool — `Explore`, `Plan`, `general-purpose`, BMAD subagents per the skill catalog), Codex (`codex review --commit <SHA>` / `codex exec --output-schema ... -` per `~/.claude/codex-invocation-guide.md`), 1M-context window for full repo + planning-artifact folds in a single session. `~/.claude/bin/check-usage.sh` before heavyweight autonomous work; at 5h ≥ 80% sleep through reset rather than burning `extra_usage` without explicit operator opt-in.

**What counts as a "real product blocker" (acceptable to surface mid-flight):**

- Architectural decision the operator must own (security tradeoff, cross-repo cutover, irreversible deploy step).
- Cross-repo coordination requiring action in a sibling repo (`~/repos/configs/` nginx edit, Windows catalog write, agent-token rotation).
- Hardware / homelab / network state Claude cannot inspect (printer down, `.180` edge unreachable, VPN dropped).
- Truly load-bearing scope ambiguity — a planning-artifact contradiction with no code-grounded resolution that would force a guess the operator might disagree with. Drifts that have an unambiguous code-grounded answer (path mismatch, type mismatch, naming alignment) get encoded in-story + flagged for `bmad-correct-course` follow-up; they are NOT blockers.
- Initiative completion (full retrospective ready for operator review).

**What does NOT count as a blocker** (own the call autonomously): "which skill next" (answer: `bmad-help` + bmad-help.csv `phase`/`after`), "commit / merge / deploy now" (AGENTS.md § Branching + § Deploy + auto-deploy memory rule), "run bmad-correct-course now or later" (default deferred unless next-story path-collision risk), "spawn subagent or inline" (own it), "Codex review now or after batch" (own it per batch-close-out memory rule), procedural BMAD methodology questions in general.

**BMAD vanilla-first stays in force, no exceptions.** ITCM autonomy is *operational ownership of when/how to invoke skills*, not *license to bypass skills*. Every action still routes through the canonical chain; protests still trigger STOP not route-around; `bmad-correct-course` is still the canonical entry for post-ship scope changes. The mandatory session-start `bmad-help` handshake is the only operator-visible procedural check; everything between session start and initiative close runs on ITCM autonomy.

Background: 2026-05-19, after Sesja G of Initiative 5 spec-creation cycle. Operator surfaced the pattern of being dragged into procedural micro-decisions (which session boundary, accept/proceed prompts, methodology routing questions) and stated the new rule: *"po obgadaniu/brainstormingu i dogadaniu wszystkich BIZNESOWYCH zagwostek TY W PEŁNI PRZEJMUJESZ PRACE NAD CAŁYM DEVELOPMENTEM"* and *"dla mnie Ty jesteś ITCMem który mnie obsługuje a samemu tylko delegujesz i koordynujesz"*. Encoded as a project rule binding for every BMAD-aware agent (Claude Code primarily; mirrored in agent-specific memory for cross-session recall).

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
