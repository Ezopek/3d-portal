---
title: "Sprint Change Proposal — Initiative 22 / Epic E34: Admin Worker/Job Console for ARQ Queues (ADMIN-JOBS-1)"
type: sprint-change-proposal
status: proposed                       # repo-local correct-course author of record (Claude, 2026-06-06); planning-artifact landing only — NO code, NO commit, NO deploy
proposed_by: Claude (BMAD correct-course, repo-local author of record, 2026-06-06)
proposed_at: 2026-06-06
skill: bmad-correct-course
mode: new-initiative (post-MVP scope addition; brownfield — the canonical entry for a new feature after ship is bmad-correct-course)
change_scope_classification: moderate
  # New Initiative 22 / Epic E34 landed into prd.md / architecture.md / epics.md (## Initiative N H2-append).
  # Single read-only MVP story (ADMIN-JOBS-1). No existing epic/story re-pointed; no shipped code touched.
  # sprint-status development_status row-seeding is deferred to bmad-sprint-planning (this SCP updates the
  # tracker comment trail only — see § 9). Implementation BLOCKED until bmad-create-story + operator dev-go.
source_discovery_artifact: _bmad-output/implementation-artifacts/spec-admin-jobs-console.md
  # Committed discovery + architecture/UX design spec (commit dcb9df8 "docs: design admin jobs console").
  # This SCP is the canonical correct-course graduation of that discovery into Initiative/Epic planning artifacts.
predecessor_initiative: 21             # Admin-Managed Orca Process Profiles (Epic E33) — its slice/recompute queues are exactly what this console observes
sequencing: |
  ADMIN-JOBS-1 lands BEFORE G-PUBLISH (the Init 21 PROFILE-OFFER-1 real-resolver-publication / live-slicing
  step) so the operator can OBSERVE the slice/recompute/render queue effects once publishing begins. Visibility
  before the effects it makes visible — the same read-first discipline that sequenced 33.1 ahead of 33.2.
related_artifacts:
  - _bmad-output/implementation-artifacts/spec-admin-jobs-console.md            # DISCOVERY source (committed dcb9df8) — grounds every claim here
  - _bmad-output/planning-artifacts/prd.md                                      # EXTENDED — ## Initiative 22 H2 (FR22-* / NFR22-*); Index + frontmatter
  - _bmad-output/planning-artifacts/architecture.md                            # EXTENDED — ## Initiative 22 H2 (Decisions AO + AP + AQ); Index + frontmatter
  - _bmad-output/planning-artifacts/epics.md                                    # EXTENDED — ## Initiative 22 H2 (Epic E34 + Story 34.1 sketch); Index + frontmatter
  - _bmad-output/implementation-artifacts/sprint-status.yaml                    # comment-trail anchor updated (top last_updated); development_status rows deferred to bmad-sprint-planning
  - _bmad-output/implementation-artifacts/33-1-readonly-admin-profile-inventory.md   # precedent — read-only admin slice shape / leak-fence / fails-closed UX / deploy-clean reasoning
constraints_honored:
  - "Modified only repo-local BMAD/planning/status artifacts under _bmad-output/."
  - "No apps/ / workers/ / infra/ / runtime-config / code / migration / test / package / deploy changes."
  - "No commit, push, deploy, restart, or live smoke."
  - "No app routes/components/tests authored; no dev-story run. Implementation BLOCKED until create-story + dev-go."
trigger:
  source: |
    Operator/controller (Laura ITCM) post-MVP scope addition: the operator wants a frontend panel showing the
    state of the backend ARQ job queues/workers, so that after changing STL/render inputs or profile offers they
    can see whether a worker wakes and whether jobs are queued / running / succeeded / failed (UC1-UC3 in the
    discovery spec § 1). The grounded discovery + architecture/UX design was authored and committed on main at
    dcb9df8 as `spec-admin-jobs-console.md`; this correct-course pass formalizes it into Initiative 22 / Epic E34.
  evidence_class: |
    Grounded in current code (file:line) and the installed arq==0.28.0 source, enumerated in the discovery spec
    §§ 2-8. No console/queue-observability endpoint exists today (GET /api/health returns {status,version} only).
    Confidence: high for the read surface (all seams cited in code); the only operator scope/risk calls (OD-1..OD-5)
    carry safe, evidence-backed defaults, all RATIFIED by the controller in this task (§ 6).
---

# Sprint Change Proposal — Initiative 22 / Epic E34: Admin Worker/Job Console for ARQ Queues

**Date:** 2026-06-06
**Skill:** `bmad-correct-course` (canonical entry for a post-ship new-feature scope change — AGENTS.md § "BMAD vanilla-first" item 3)
**Initiative / Epic:** **22 / E34** — Admin Operational Observability (Worker/Job Console)
**Candidate id:** ADMIN-JOBS-1
**Source discovery:** `spec-admin-jobs-console.md` (committed `dcb9df8 docs: design admin jobs console`)
**Predecessor:** Initiative 21 (Admin-Managed Orca Process Profiles, Epic E33) — whose slice/recompute queues this console observes.

> **Scope of this artifact.** Planning-/status-artifact landing ONLY. No application code, no `apps/` / `workers/`
> / `infra/` / configs / migrations / tests / package / deploy changes. No commit, push, deploy, restart, or live
> smoke performed by this run. This SCP lands a new Initiative/Epic and a single read-only MVP story sketch;
> **implementation stays BLOCKED until `bmad-create-story` authors the numbered story spec and the operator's
> dev-go gate fires** (same gate shape as the Init 21 / 33.x flow).

---

## 1. Issue Summary

**Triggering need.** The portal runs **three live ARQ worker pools** (API, Render, Slicer — discovery § 3) and
there is **no in-product way to observe them**. `GET /api/health` (`apps/api/app/main.py:200-202`) returns only
`{"status":"ok","version":…}` and never touches arq. When the operator changes STL/render inputs or profile
offers, they cannot tell from the product whether a worker woke, whether their job is queued/running, or whether
something failed. Three operator-stated use cases (discovery § 1):

- **UC1 — "Did my change wake the backend?"** — confirm a worker picked the work up (queued → running).
- **UC2 — "Why hasn't anything changed after 5 minutes?"** — check whether another job is running ahead, or
  whether nothing was enqueued at all.
- **UC3 — "What are these red jobs?"** — notice failed jobs and be able to discuss them after the fact.

**What this initiative does.** Lands a **read-only, admin-only worker/job console** — a backend snapshot endpoint
`GET /api/admin/queues` and a frontend `/admin/queues` admin tab — built strictly by **reusing existing seams**
(the FastAPI-lifespan-owned arq pool + raw Redis on `app.state`, the arq read surface, and the existing
business-keyed status keys as a context layer). It answers UC1/UC2 with exact live signals (`zcard` queued +
in-progress SCAN) and UC3 within arq's ~1h result retention, honestly labelled.

**What this initiative is NOT.** Not a durable job ledger (deferred, § 5 / § 8); not operator-action controls
(retry/kill/purge/pause/resume — deferred, § 8); not a raw Redis/ARQ internals dump as the product surface; not
WebSocket/SSE; not the member-facing `/queue` print-queue module slot (a semantically different v2 surface,
discovery § 2.8 / Decision AO-location).

## 2. Why `bmad-correct-course`, and what this pass produces

ADMIN-JOBS-1 is a **new feature after MVP** in a brownfield repo with an existing PRD/architecture/epics model.
Per AGENTS.md § "BMAD vanilla-first" item 3 and the project-context routing rule, the canonical entry for any
post-ship scope change is `bmad-correct-course` (NOT the greenfield `bmad-create-prd` chain). This pass:

1. **Lands Initiative 22 / Epic E34** into `prd.md` (FR/NFR ids), `architecture.md` (Decisions AO/AP/AQ), and
   `epics.md` (Epic E34 + Story 34.1 sketch) via the `## Initiative N` H2-append pattern (project-context § "BMAD
   planning artifacts are living singular documents"; epic numbering is project-global → E34 follows E33).
2. **Produces this Sprint Change Proposal** as the discovery → planning graduation record.
3. **Defers `sprint-status.yaml` development_status row-seeding to `bmad-sprint-planning`** (§ 9) — only the
   tracker comment trail is anchored here.

The grounded change-analysis (correct-course checklist steps 1-2) was already performed in the committed discovery
spec; this SCP is the explicit edit-proposal + handoff (steps 3-6). The one judgment call flagged transparently:
authoring a design-spec in `implementation-artifacts/` *before* correct-course ran (the discovery spec) — precedent
exists (the 33.x flow had SCP + design specs precede the numbered stories); it is discovery feeding the canonical
entry, not a route-around of it.

## 3. ARQ topology this console reads (grounded — discovery § 3)

| Pool | `queue_name` | Functions | health key | `max_jobs` |
|---|---|---|---|---|
| **API** (`apps/api/app/workers/__init__.py:31`) | `arq:api` | `cleanup_refresh_tokens`, `generate_thumbnail`, `poll_spoolman_summary` | `arq:api:health-check` | default |
| **Render** (`workers/render/render/worker.py:450`) | `arq:queue` | `render_model`, `render_stl_previews` | `arq:queue:health-check` | 2 |
| **Slicer** (`apps/api/app/modules/slicer/worker.py:60`) | `arq:slicer` | `slice_estimate` | `arq:slicer:health-check` | `settings.slicer_max_concurrency` |

The console is read-only and never enqueues, so it cannot regress the cross-queue `_queue_name=API_QUEUE_NAME`
routing contract (`apps/api/app/workers/__init__.py:19-27`); its per-queue grouping makes a future cross-queue
misroute *visible* as a bonus diagnostic.

## 4. Recommended approach — single read-only MVP story (Direct Adjustment, additive)

**Direct Adjustment** (correct-course step 3 classification): add one new initiative with a single read-only MVP
story. No rollback, no MVP-scope reduction, no existing-story edits. The MVP is deliberately the smallest surface
that answers UC1-UC3:

- **Backend** — `GET /api/admin/queues` (read-only, `current_admin`-gated, absent from `_PUBLIC_ROUTES`), computing
  the snapshot DTO entirely from `app.state.arq` / `app.state.redis`: `queued` = `redis.zcard(queue_name)` per pool
  (exact, O(1)); `worker` liveness/counters from the `<queue>:health-check` string; `running_jobs` from a **bounded
  `SCAN MATCH arq:in-progress:*`** (cardinality ≤ total concurrency); `recent` from a **bounded `SCAN MATCH
  arq:result:*` with a hard cap** (NEVER the unbounded `KEYS` that `all_job_results()` uses). `context` derived from
  the existing business-keyed status keys (`render:status:{model_id}`, slicer `EstimateStatus`) and/or the job id —
  **never** from raw pickled `args`/`kwargs`/`result`. (Discovery § 7.)
- **Frontend** — a new `"queues"` admin tab + `routes/admin/queues.tsx` mirroring the profiles-tab pattern
  (`AdminTabs.tsx` + `routes/admin/*.tsx`), AuthGate discipline (defer to shell for anonymous; role-tier redirect
  only for authenticated-non-admin — Init 10 retro rule). Per-queue cards (queued/running headline + liveness chip +
  raw counters), a "running now" strip, a "recent (~last hour)" list with the retention caveat label, and
  loading/empty/error states that **fail closed/visible** (never fabricate green/empty when the read failed).
  Focus-gated polling (no WebSocket/SSE). (Discovery § 9.)

**Effort/risk:** API-read-only + FE. **No worker image change → does NOT trip the SW-DEPLOY-1 overlay-rebuild
gate** (cf. 33.1's deploy-clean reasoning). The load-bearing risk is the **privacy/leak fence** (§ Decision AQ),
mitigated by a field-allowlist DTO + negative tests.

## 5. Data model — raw-ARQ snapshot now, durable ledger deferred (Decision AO)

The controller-asked tradeoff (discovery § 5 / Decision D2), RATIFIED:

- **MVP = raw-arq live snapshot + reuse of the existing business-keyed status keys** as the context layer. UC1/UC2
  need only live state (queued/running right now) — raw arq answers these exactly and cheaply. UC3 failures are
  legible **within arq's ~1h `keep_result` window**; the existing `render:status:{model_id}` / slicer
  `EstimateStatus` keys supply "what was this job about" without a new table, Alembic migration, or worker
  instrumentation. MVP risk stays API-read-only.
- **The durable job-activity ledger is DEFERRED, not omitted** — named as the later slice that closes UC3's
  "discuss it days later" fully (DB-backed append-only event model with business context surviving past Redis TTL;
  worker write-on-transition instrumentation + Alembic). Recorded in § 8 and as **G-LEDGER**.
- **UX honesty bridge:** because raw results expire (~1h), the recent-history panel is **explicitly labelled
  "last ~1h (Redis-resident)"** so a vanished failure is not misread as "resolved" (Decision AO consequence;
  OD-3 default ratified).

## 6. Open decisions — all RATIFIED to safe default by the controller (this task)

The discovery spec surfaced OD-1..OD-5, each with a safe evidence-backed default. The task instruction ratifies
every default explicitly ("Product/architecture defaults to ratify unless BMAD finds a real blocker"). **BMAD found
no real blocker.** Resolution:

| OD | Decision | Resolution (ratified) |
|---|---|---|
| **OD-1** | Data model | **MVP = raw-arq snapshot + reuse existing status keys; durable ledger DEFERRED** (§ 5, Decision AO). |
| **OD-2** | Liveness granularity | **Accept coarse (~1h) health-key liveness for MVP**; running/queued stay exact; worker `health_check_interval`-lowering DEFERRED (Decision AP). |
| **OD-3** | Recent-history retention messaging | **Yes — label `recent[]` "~last hour, Redis-resident"** (Decision AO consequence; NFR22-RETENTION-HONESTY-1). |
| **OD-4** | Backend module home | **New `apps/api/app/modules/queue/` package** (the backend mirror of the v2 `queue` slot, scoped to admin observability) — endpoint `GET /api/admin/queues`. |
| **OD-5** | Slicing of the work | **Single read-only MVP story (ADMIN-JOBS-1)**; ledger + operator-actions are later epic stories. |

These are operator calls because they trade scope/risk; with the controller's ratification they carry no open
blocker into create-story. (Recorded in `prd.md` § Initiative 22 "Open decisions — ratified".)

## 7. The leak fence — load-bearing safety contract (Decision AQ / NFR22-LEAK-FENCE-1)

The single biggest risk: arq stores **pickled `args`, `kwargs`, and `result`** on every queued job and every result
(discovery § 4/§ 8). These can embed absolute paths, model internals, Spoolman data, or token material. **The console
must never serialize raw arq payloads.** The fence (each clause → an AC + negative test in the create-story spec):

1. **Admin-only** — `current_admin`; non-admin → 403; anonymous → 401; route-enforcement gate green with **no
   `_PUBLIC_ROUTES` edit**.
2. **Field allowlist, not denylist** — the DTO carries only `queue_name`, friendly `role`, `function` name,
   `job_id`, counts, timings/ages, `success/outcome`, liveness, and a **curated `context`**. A test asserts the
   serialized response matches the allowlist and contains **no** `args`/`kwargs`/`result` keys.
3. **No raw paths / no raw error bodies** — `error_class` is a curated category (exception type name at most),
   `context.ref` an id/hash-prefix; negative test asserts no path-like substrings.
4. **No `args`/`kwargs` deserialization leak** — avoid `queued_jobs()` (it deserializes args); use `zcard` for depth
   + `Job.info()` for the bounded in-progress set, function name only.
5. **No secrets, ever**; **No destructive surface** — `GET` only; no enqueue/abort/purge.

## 8. Deferred scope (explicit — named triggers, NOT silent omissions)

- **Durable job-activity ledger** (§ 5) — DB-backed append-only event model surviving past Redis TTL; worker
  instrumentation + Alembic. **G-LEDGER.** Closes UC3 long-term.
- **Operator-action controls** — retry / kill (abort) / purge / pause / resume. arq supports abort (`arq:abort` +
  `Job.abort()`) so feasible later, but they are **destructive queue mutations**, excluded from a visibility-first
  MVP. **G-ACTIONS.**
- **Worker `health_check_interval` lowering** (OD-2) — near-real-time liveness; worker-config + redeploy.
  **G-LIVENESS.**
- **WebSocket/SSE push** — polling is sufficient for MVP; revisit only on proven load/latency inadequacy.
- **Multi-instance / historical charts / alerting** — single-homelab assumption holds; post-MVP.
- **Member-facing print `/queue` module** — unrelated v2 slot (discovery § 2.8); not touched.

## 9. sprint-status decision (row-seeding deferred to bmad-sprint-planning)

**No `development_status` row is seeded in this correct-course pass.** Per the discovery routing (§ 13) and the
canonical BMAD chain, the order is: **`bmad-correct-course` lands the epic in `epics.md` → `bmad-sprint-planning`
seeds the `sprint-status.yaml` epic/story rows → `bmad-create-story` flips the story `backlog → ready-for-dev`.**
This pass is step 1. Seeding rows now would do sprint-planning's job and pre-empt the chain; the repo evidence
confirms epic rows physically land at the sprint-planning/create-story stage (e.g. `epic-33` first appeared at the
33.1 create-story/feat commit), not in the planning SCP.

What this pass DOES touch in `sprint-status.yaml`: **only the top `last_updated:` comment trail** is updated to
anchor the Init 22 / E34 landing, the BLOCKED-until-create-story+dev-go gate, and the G-PUBLISH-before sequencing.
All existing `development_status` keys/statuses are preserved byte-for-byte. (Task constraint: "If a sprint-status
YAML row is added/updated, keep it parseable and preserve existing statuses" — satisfied: no status rows changed.)

The seeded rows, when `bmad-sprint-planning` runs, will be (recorded here for that step, NOT applied now):
`epic-34: backlog`, `34-1-admin-queues-console: backlog`, `epic-34-retrospective: backlog`.

## 10. Impact analysis

- **Epic/initiative:** NEW Initiative 22 / Epic E34 (project-global numbering — follows E33). No existing
  initiative re-pointed; no shipped code touched.
- **PRD:** new `## Initiative 22` H2 — FR22-QUEUE-SNAPSHOT-1, FR22-LIVENESS-1, FR22-CONSOLE-UI-1; NFR22-LEAK-FENCE-1,
  NFR22-AUTH-1, NFR22-READONLY-1, NFR22-REDIS-LOAD-1, NFR22-RETENTION-HONESTY-1, NFR22-I18N-PARITY-1,
  NFR22-VISUAL-VERIFICATION-1, NFR22-DETERMINISM-1. Index + frontmatter extended.
- **Architecture:** new `## Initiative 22` H2 — Decision AO (read-model: raw-arq snapshot over `app.state` + context
  reuse + location = admin area, ledger deferred), AP (coarse-health-key tri-state liveness, interval-lowering
  deferred), AQ (leak fence / read-only privacy contract). Index + frontmatter extended.
- **Epics:** new `## Initiative 22` H2 — Epic E34 + Story 34.1 sketch + Gates (G-DEVGO, G-PUBLISH-before, G-LEDGER,
  G-ACTIONS, G-LIVENESS). Index + frontmatter extended.
- **Code:** none in this run. The MVP is API-read-only + FE; reuses `app.state` arq/Redis (no ad-hoc connection),
  the arq read surface, and existing business-keyed status keys. **SW-DEPLOY-1 not triggered** (no worker image
  change).
- **sprint-status:** comment-trail anchor only (§ 9); rows deferred to `bmad-sprint-planning`.

## 11. Acceptance-criteria mapping (this landing)

| # | Criterion | Where satisfied |
|---|---|---|
| 1 | Canonical correct-course/planning pass run; canonical artifacts updated | This SCP + `## Initiative 22` in prd/architecture/epics (§ 2, § 10). |
| 2 | Initiative/Epic anchor for ADMIN-JOBS-1 | Initiative 22 / Epic E34 / Story 34.1, all three docs + this SCP. |
| 3 | G-PUBLISH-before sequencing anchored | frontmatter `sequencing`; epics § Gates (G-PUBLISH-before); prd/arch cross-refs. |
| 4 | Deferred durable ledger named (not omitted) | § 5, § 8 (G-LEDGER); Decision AO; prd "Out of scope". |
| 5 | Coarse health-key liveness accepted (MVP), interval-lowering deferred | § 6 OD-2; Decision AP (G-LIVENESS). |
| 6 | Recent history labelled Redis-resident / ~1h | § 5; NFR22-RETENTION-HONESTY-1; Decision AO consequence. |
| 7 | Admin-only, read-only scope; no retry/kill/purge/pause/resume | § 4, § 7 (Decision AQ); NFR22-READONLY-1; § 8 (G-ACTIONS). |
| 8 | Implementation blocked until create-story / dev-go | Scope banner; § 9 (G-DEVGO); epics Status note. |
| 9 | Endpoint/routes `GET /api/admin/queues` + `/admin/queues` | § 4; Decision AO; FR22-QUEUE-SNAPSHOT-1 / FR22-CONSOLE-UI-1. |
| 10 | No app code changes; sprint-status parseable, statuses preserved | Scope banner + § 9 + constraints_honored frontmatter. |

## 12. Implementation handoff & next BMAD steps

**Change scope: Moderate** (new initiative + single story; backlog sequencing, no code). Routing:

1. **`bmad-sprint-planning`** — seed `sprint-status.yaml` rows from the landed Epic E34 (§ 9).
2. **`bmad-create-story`** — author the numbered story spec `34-1-admin-queues-console.md` in
   `implementation-artifacts/`, consuming this SCP + the discovery spec, with the full AC list (the discovery § 14
   test/gate preview: leak-fence allowlist + negative tests, bounded-SCAN-not-KEYS assertion, 403/401 auth, focus-
   gated polling, i18n parity, visual baselines incl. AdminTabs ripple, determinism 3×).
3. **Operator dev-go gate**, then `bmad-dev-story` on a `feat/E34.1-admin-queues-console` branch (AGENTS.md §
   Branching).

**Implementation remains BLOCKED** until steps 1-2 + the dev-go gate (G-DEVGO). This pass is planning only.

## 13. Verification performed (this landing run)

- **Routing:** invoked `bmad-help` at session start → confirmed `bmad-correct-course` as the canonical entry for a
  post-ship new-feature scope change (catalog row `bmad-correct-course … anytime … change proposal`). Resolved the
  correct-course customization workflow (empty prepend/append; persistent fact = `project-context.md`).
- **Grounding (read-only, cited):** discovery spec `spec-admin-jobs-console.md` (full); `prd.md` Init 21 (1937-2003)
  + Initiatives Index + frontmatter; `architecture.md` Init 21 (2861-2935) + Index + frontmatter; `epics.md` Init 21
  (3787-3920) + Index + frontmatter; `sprint-status.yaml` structure (`development_status` flat map, statuses
  `done/in-progress/backlog/ready-for-dev`) + git evidence that epic rows land at create-story; project-context §
  "BMAD planning artifacts are living singular documents" (H2-append, project-global epic numbering).
- **Boundaries:** no `apps/` / `workers/` / `infra/` / configs / migrations / tests / package / deploy edits; no
  commit/push/deploy/restart/smoke; no dev-story. Mechanical verification (git status/diff --check, grep readback,
  YAML parse of `sprint-status.yaml`) recorded in the run summary.
- **Open blockers:** none. OD-1..OD-5 ratified to safe default by the controller (§ 6).
