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

Every BMAD story is implemented on its own short-lived branch — *not* in a series of commits directly on `main`. This prevents partial features from reaching `.190` via auto-deploy and gives external reviewers a complete focused branch/diff context.

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
   - External review pass: Gemini via `laura-gemini-review` for routine focused review; Codex via `codex review --commit <HEAD-of-branch>` only for fallback, high-stakes, or repo-mandated countersignature (per the review-fix-commit close-out pattern)
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
   ff-only is mandatory because per-commit history gives reviewers and deployment audits a precise context; squashing destroys that context.
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
| Doc-only | `docs:` | Only `*.md`, `AGENTS.md`, `CLAUDE.md`, and tracked `_bmad-output/` docs (markdown plus `implementation-artifacts/sprint-status.yaml`). Untracked `_bmad-output/` paths (logs, audit-raw, code-reviews, story-automator scratch) cannot land via `docs:` because they cannot land at all — see § BMAD artifact tracking. No code, no config, no infra. |
| Config-only without runtime effect | `chore:` | E.g. `_bmad/_config/`, `.gitignore`, formatter config. If it changes how the app runs, it's not a chore — it's a fix or feat and goes on a branch. |
| Hotfix | `fix:` + `# hotfix-rationale: <reason>` in body | Production-level urgency only. Run external review inline immediately after pushing: Gemini by default, Codex when high-stakes/repo-mandated. |

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
- Don't squash-merge story branches — per-commit history is what external reviewers and deployment audits consume.
- Don't keep stale story branches after merge — delete them with `git branch -d`.
- Don't bypass the story-branch flow for code/infra changes just because "this one is small". The threshold is in the table above — code changes outside `docs:` / `chore:` always go on a branch.
- Don't commit secrets just because the remote is private. Hostnames and IPs already in committed docs (`docs/operations.md`, `infra/`) are acceptable; never add API tokens, passwords, or fresh keys.

## Workflow expectations

BMAD owns planning + execution + review in this repo. Skill catalog: `_bmad/_config/bmad-help.csv`.

- **Agents with BMAD skills (e.g. Claude Code) MUST invoke `bmad-help` at the start of every session before any planning or implementation work.** `bmad-help` reads `_bmad/_config/bmad-help.csv` (the skill catalog with `phase` + `after` dependencies) and recommends the canonical entry skill for the current lifecycle stage. Skipping it is the most common BMAD drift trigger and is the single biggest cause of agents reaching for the wrong skill by name-match. **Exempt sessions:** (a) trivial single-shot tasks where no BMAD ceremony applies (typo fix, single-file Q&A); (b) child sessions spawned by `bmad-story-automator` (these execute a single workflow step — create-story / dev-story / automate / code-review / retrospective — already determined by the parent orchestrator inside the canonical chain; re-invoking `bmad-help` would either be redundant or risk routing the child away from the orchestrator-chosen skill). When in doubt outside these exemptions, run it — cost is ~30s.
- Agents without BMAD skills (e.g. Codex, Gemini) read `_bmad-output/project-context.md` for execution rules and the relevant story spec in `_bmad-output/` before implementing.

Typical routing for Claude Code:

- New feature in **greenfield context** (no prior PRD/architecture artifacts) → full BMAD planning chain (PRD → architecture → epics & stories → sprint planning → story cycle).
- New feature in **brownfield context** (PRD/architecture already exist — the normal case here) → `bmad-correct-course` FIRST. It analyzes the change and routes to the right ceremony (PRD edit, architecture rerun, new epics, sprint planning update). The full planning chain is for greenfield only — do not invoke `bmad-create-prd` on a finished `prd.md`.
- Small change or bugfix → `bmad-quick-dev`.
- Tests on existing code → BMAD `tea` module (`bmad-testarch-test-design`, `bmad-testarch-framework`, etc.).
- **Mid-session scope pivot → re-invoke `bmad-help`.** If the work shifts (was planning, now implementing; was bug-fix, now feature; surprised by an unfamiliar artifact state), the session-start call no longer covers the new task — re-run `bmad-help` to confirm the new canonical entry.

### BMAD artifact tracking

`_bmad-output/` is the working directory for every BMAD skill in this repo. A curated subset of it is tracked in git so that cross-agent context survives between sessions and tools that have no BMAD harness (Codex, Gemini, reviewers landing on a fresh clone) can still read the planning + execution surface AGENTS.md points them at (`_bmad-output/project-context.md`, `_bmad-output/triage-backlog.md`, story specs, retros, sprint-status). The rest stays local — raw transcripts and tool scratch reference internal hosts/paths, balloon repo size, and have no readers outside the session that produced them.

`.gitignore` is the source of truth for the split. The default rule is `_bmad-output/**` ignored; the explicit `!` unignore lines below it enumerate the tracked surface. The current curated set:

| Path | Tracked? | Notes |
|---|---|---|
| `_bmad-output/project-context.md` | yes | Execution rules for non-BMAD agents; regenerated via `bmad-generate-project-context`. |
| `_bmad-output/triage-backlog.md` | yes | Cross-initiative triage queue consumed by `bmad-correct-course`. |
| `_bmad-output/planning-artifacts/**/*.md`, `**/*.yaml` | yes | PRD, architecture, epics, product briefs, sprint-change proposals, readiness reports, `_runtime/`, `archive/`. |
| `_bmad-output/implementation-artifacts/*.md` | yes | Story specs, retros, security audits, spec-tb-*, cutover smoke reports. Top-level only; `codex-review-*.md` is explicitly excluded as transcript noise. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | yes | Sprint state consumed by `bmad-sprint-status` and the story-automator orchestrator. |
| `_bmad-output/ux/**/*.md` | yes | UX flow specs produced by `bmad-create-ux-design`. |
| `_bmad-output/brainstorming/*.md` | yes | Brainstorming session transcripts. |
| `_bmad-output/implementation-artifacts/codex-review-*.md`, `*.log` | local | Codex review transcripts/logs — large, raw, reference internal SHAs and paths. |
| `_bmad-output/implementation-artifacts/audit-raw/` | local | Raw audit dumps. |
| `_bmad-output/implementation-artifacts/code-reviews/` | local | Pre-cutover code-review transcripts (large markdown logs, not story specs). |
| `_bmad-output/story-automator/` | local | Orchestrator scratch: monitor logs, complexity probes, agent state files. |
| `_bmad-output/test-artifacts/` | local | TEA scratch. |

**Workflow rules:**

- Use `git status` after BMAD skills finish — newly produced artifacts that match a tracked pattern will show up unstaged. Commit them with `docs:` (see § Trivial commits direct to main) when they are skill output without code changes; bundle them with the story-branch commit when they belong to a story.
- Before staging anything from `_bmad-output/`, sanity-check for embedded secrets or sensitive identities. The curated tracking pattern is permissive (e.g. `implementation-artifacts/*.md` matches everything at that level), so a one-off sensitive artifact dropped there will be picked up. If a tracked-by-default artifact must stay local, add an explicit ignore line above the unignore block and note why.
- To add a new tracked artifact type, extend `.gitignore` with an explicit `!_bmad-output/<path>` line and update the table above in the same commit. Do not flip the default rule (`_bmad-output/**`) — keeping default-deny is what makes the curated subset auditable.
- Never widen the tracked set by deleting an ignore line silently. The split is operator-approved; changes to it land as `chore: ` commits with a one-line rationale in the body.

### BMAD vanilla-first

**Vanilla BMAD skill discipline is the default. Any procedural deviation from standard skill flow is treated as a bug** unless there is a documented, operator-approved strong reason. The procedural drifts to avoid: routing-around a protesting skill, direct artifact edits that bypass a `bmad-correct-course` recommendation, skipping mandatory session-start `bmad-help`, treating BMAD as a library of named skills matched by user-verb (e.g. *"create PRD"* → `bmad-create-prd`) rather than as a methodology with phase ordering and routing.

**On doc shape** — vanilla BMAD assumes a single project-wide PRD/architecture/epics model (per `docs.bmad-method.org/llms-full.txt`: *"BMAD assumes a single project-wide PRD model. The documentation does not address multi-initiative brownfield scenarios."*). Every vanilla planning skill hardcodes singular `outputFile = {planning_artifacts}/{prd,architecture,epics}.md`. This repo's `## Initiative N` H2-append pattern in monolithic `prd.md`/`architecture.md`/`epics.md` is the **pragmatic workaround** for that documented methodology gap — it is the closest-to-vanilla shape attainable for multi-initiative brownfield, and IS the pattern new initiatives extend (via `bmad-edit-prd` on `prd.md` + manual edits on architecture/epics, since no `bmad-edit-architecture` or `bmad-edit-epics` skill exists).

**Skill discovery checklist for any non-trivial BMAD task:**

1. Confirm `bmad-help` has been called for the current session (mandatory at session start per the rule above; re-call after any mid-session scope pivot). If somehow skipped, run it NOW before proceeding.
2. Check `_bmad/_config/bmad-help.csv` for `phase` + `after` dependencies before invoking any skill. Misalignment with current project state → reconsider.
3. `bmad-correct-course` is the canonical entry point for ANY post-ship scope change — PRD edits, architecture changes, scope corrections, new features after MVP, mid-sprint adjustments. Per its catalog description: *"May recommend start over, update PRD, redo architecture, sprint planning, or correct epics and stories."* It is not just for emergencies.
4. If a skill rejects the current state (e.g. `bmad-create-prd` detects `step-12-complete` and refuses), STOP and consult the operator before routing to a different skill. Never silently switch skills to work around a protest.

Background: the 2026-05-18 retro on the (since-reverted) user-accounts initiative caught a recurring drift pattern — the agent treats BMAD as a library of named skills (matching operator verbs to skill names: *"create PRD"* → `bmad-create-prd`) rather than as a methodology with phase ordering and routing. `bmad-help` and `bmad-correct-course` exist precisely to short-circuit that pattern. A subsequent recalibration pass (2026-05-18 v2) corrected an earlier-in-this-section misframing: the H2-append doc pattern is a vanilla-compatible pragmatic workaround, NOT a drift. Only procedural skill-discipline violations are drifts.

### Autonomous development mode (effective 2026-05-19)

When Laura/operator explicitly delegates autonomous execution for an initiative, and the business surface is closed — brief, PRD, architecture, epics aligned and the readiness check has passed (or a bug report carries enough context to start root-causing) — the BMAD-aware agent may take operational ownership of the dev-and-fix pipeline. By default for this repo, Laura is ITCM/controller and story execution is explicitly routed; do not self-trigger broad autonomous runs merely because a ready story exists. Procedural confirmation traffic inside an already-delegated run ("which skill next", "should I commit", "spawn subagent or run inline") is still owned by the agent.

**Self-triggering is opt-in for this repo.** Unlike actively-managed live repos such as `crypto-manager`, `3d-portal` should not start large autonomous story work just from a session-start state check unless Laura/operator has explicitly delegated that run. Bug-fix sessions with adequate context may proceed inside the scoped request. The only inputs that still gate operator decision are the blockers listed below (greenfield biznesowy scope, security trade-off, irreversible deploy decision, etc.).

**Same shape for bug-fix work.** The agent owns the investigation → reproduce → root-cause → fix → verify chain. A single focused question is fair if external context is genuinely missing (production log only the operator can pull, hardware screenshot, network state). A guided walkthrough is not.

**Tools the agent should reach for autonomously:**

- **Subagents** via the `Agent` tool — `Explore` for codebase recon, `Plan` for multi-file design, `general-purpose` for parallel research, BMAD-domain subagents (dev / architect / TEA) per the skill catalog. Default to spawning when the work is parallelizable or context-isolating; default to inline when the task is small and serial.
- **Story-automator** (`bmad-story-automator` + `bmad-story-automator-review`) — the canonical multi-story / multi-epic build orchestrator. Run it for "build all stories in initiative N" rather than hand-walking the create-story → dev-story → code-review → retrospective chain. Handles tmux session isolation, programmatic complexity scoring, escalation on non-autonomous decisions, YOLO retrospectives, full resumability via state file.
- **Gemini CLI** as the default read-only external reviewer / researcher for routine focused diffs (`laura-gemini-review`, plan/read-only mode). It is available in non-interactive shells at `/home/ezop/.local/bin/gemini` (v0.44.1 via the standardized nvm Node v24.16.0 toolchain). Do NOT reuse Gemini Code Assist OAuth tokens in third-party tools — only official Gemini CLI auth (Google account flow) or a dedicated `GEMINI_API_KEY` env var.
- **Codex** as fallback/high-stakes peer reviewer (`codex review --commit <SHA>` / `codex exec --output-schema ... -` / `laura-codex-review-diff`) or when a repo artifact explicitly mandates Codex countersignature. For NFR-prefixed security gates with countersignature requirements (e.g. Init 5's NFR5-SEC-2 max-3-Mediums-with-codex-review), Codex review remains contractually mandatory, not optional. If Gemini is used where a prior artifact expected Codex, label the deviation explicitly in the commit body or artifact (`# gemini-review: <reason>`).
- **1M context window** when the work benefits from holding the whole repo + planning artifact set in a single session rather than spawning sub-sessions just for budget.

**Budget discipline stays in force.** Check `laura-agent-usage` / Claude usage before heavyweight autonomous work. At Claude 5h ≥ 80%, sleep through the reset rather than burning `extra_usage` without an explicit operator opt-in. Story-automator's resume mode is the natural pause point — stop, sleep, resume from state file. Check `laura-agent-usage gemini-daily` / `codex-daily` when routing external review; preserve Codex/OpenAI budget for fallback/high-stakes or repo-mandated review.

**What counts as a "real product blocker" — acceptable to surface mid-flight:**

- Architectural decision the operator must own (security trade-off, cross-repo cutover, irreversible deploy step).
- Cross-repo coordination requiring operator action in a sibling repo (`~/repos/configs/` nginx edit, Windows catalog write, agent-token rotation).
- Hardware / homelab / network state the agent cannot inspect (printer down, `.180` edge unreachable, VPN dropped).
- Load-bearing scope ambiguity with no code-grounded resolution — a planning-artifact contradiction that would force a guess the operator might disagree with. Drifts that have an unambiguous code-grounded answer (path mismatch, type mismatch, naming alignment) get encoded in-story + filed in `_bmad-output/triage-backlog.md` for `bmad-correct-course` follow-up; they are not blockers.
- A HARD-GATE failure that contractually blocks downstream work (e.g. Init 5's NFR5-SEC-1 audit gate condition).
- Initiative completion — full retrospective ready for operator review and sign-off.

**What does NOT count as a blocker** — own it: which skill next (answer via `bmad-help` + `bmad-help.csv` `phase` / `after` columns), commit / merge / deploy timing (AGENTS.md § Branching + § Deploy + the `feedback_auto_deploy_dev.md` memory entry), `bmad-correct-course` now-vs-later (default deferred unless next-story path-collision risk), subagent-vs-inline, external-review-now-vs-after-batch (Gemini default; Codex fallback/high-stakes or repo-mandated), general BMAD methodology routing.

**BMAD vanilla-first stays in force, no exceptions.** The autonomy is *operational ownership of when and how to invoke the skills*, not *license to bypass them*. Every action routes through the canonical chain; skill protests still trigger STOP, not route-around; `bmad-correct-course` is still the canonical entry for any post-ship scope change. The mandatory session-start `bmad-help` handshake is the one operator-visible procedural check that survives autonomous mode; everything between session start and initiative close runs autonomously.

Source: 2026-05-19 operator decision after Sesja G of Initiative 5. The pattern being closed: agent dragging operator into procedural micro-decisions (session boundaries, accept/proceed prompts, methodology routing) when business alignment was already settled. Rule applies to every BMAD-aware agent (Claude Code primary; Gemini/Codex/future LLMs inherit via this AGENTS.md entry according to their reviewer/executor role). Cross-referenced in agent-local memory as `feedback_itcm_autonomous_mode.md` for fast recall.

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

## Scope boundaries

Initiative 10 retro codified this; surfaced previously as the OTEL collector incident (item #6) when the originally-scoped recon revealed it was an infra-side problem misclassified as portal-app work.

- **Infrastructure concerns** belong to `~/repos/configs`, NOT to 3d-portal initiatives. This includes: logging pipeline (otel-collector, data-prepper, opensearch), deployment topology, reverse-proxy rules (nginx-180 / nginx-190 / nginx-kbk), TLS / certificate provisioning, host-level systemd / docker daemon config, observability sinks (Sentry/GlitchTip backend, not the SDK integration).
- **3d-portal initiatives** scope only app-layer concerns: FastAPI / SQLModel / React / Tanstack / Three.js / arq tasks / Alembic migrations / API contracts / UI components / static asset pipelines.
- **Recon subagent assesses the split** when an item is scope-ambiguous. Heuristic: if the recon finds that `>50%` of the fix surface lives outside `apps/` + `workers/` + `infra/` in 3d-portal, carve out to `configs/`. The OTEL recon (2026-05-22) called it `~75% infra-side` and the item dropped from Init 10 scope correctly.
- **Symptom triage rule**: when a production log error originates from a library/integration (e.g. opentelemetry-sdk's "Failed to export span batch"), check the recipient (collector / sink) BEFORE the sender (app code). 3d-portal's role is to send OTEL spans; the collector pipeline downstream is `configs/` territory.

## Data flow

One-way Windows → `.190` rsync. Portal never writes to the catalog. See `docs/operations.md` for the sync recipe.

## Conventions

- Conversation language: Polish. Committed file content (code + docs): English.
- Frontend: zero inline hex colors in components — use Tailwind classes referencing CSS variables in `apps/web/src/styles/theme.css`.
- Frontend: `npm run lint` from `apps/web/` runs ESLint 9 flat config (`eslint.config.js`); it must pass with `--max-warnings=0` before commit. Python (`apps/api/`, `workers/render/`) is on `ruff`.
- Backend: structured JSON logs only; canonical fields per `~/repos/configs/docs/observability-logging-contract.md`.
- Tests: TDD for backend logic; Playwright visual regression for UI.
- **Frontend auth gating discipline** (Init 10 retro codification): component-level authorization checks (role / permission / ownership inside a route component) MUST NOT redirect when authentication state is unknown or anonymous. Defer to the shell-level `AuthGate` for the unauthenticated case; act only on `authenticated-but-unauthorized`. Anti-pattern that surfaced in Init 6 retro + Init 10 Story 15.2 P2 fix-up: `AdminUsersRoute` + `AdminInvitesRoute` rendered `<Navigate to="/" replace />` synchronously when `!isAdmin` for ANY auth state, racing AppShell.AuthGate's useEffect and stripping the original `pathname` from `/login?next=` for anonymous deep-link visitors. Decision O (anonymous redirect with pathname preservation) requires deferring to the shell gate for `!isAuthenticated` users — only fire the role-tier `<Navigate>` for authenticated-non-admin users.
- **Test discipline — hang/timeout class bugs** (Init 10 Murat codification): after fix-up of any test in hang / timeout / deadlock class, mandatory full pytest suite re-run before claim "fixed". Masked tests have non-zero prior. Init 10 Story 15.1 closed a pytest threading deadlock; full-suite re-run revealed 2 pre-existing failures (TB-021) that had been masked for ~2 days because the runner couldn't reach them. NFR10-DETERMINISM-1 "3× consecutive PASS" is the EXIT criterion, not the POST-FIX protocol — the re-run IS the new execution path.
- **Visual baseline triage before regen** (Init 10 Murat codification): before invoking `--update-snapshots`, classify each failure as `stale-baseline` (regen OK), `deterministic-fail` (real bug — do NOT regen, surface to operator), or `flake-candidate` (need 3× run probe to confirm non-determinism). Blanket regen masks real UX regressions. Carry-forward from [[feedback_visual_failure_mode_triage]] memory.

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
