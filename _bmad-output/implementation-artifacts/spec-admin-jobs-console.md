---
artifact_type: discovery + architecture/UX design spec (pre-correct-course)
candidate_id: ADMIN-JOBS-1
title: Admin worker/job console for ARQ queues
date: 2026-06-06
status: discovery — implementation BLOCKED (no apps/ code this pass)
authored_by: Claude Opus 4.8 (repo-local BMAD author of record), under Laura/ITCM supervision
proposed_initiative: 22 (Admin Operational Observability) — to be assigned by bmad-correct-course
proposed_epic: E34 — to be assigned by bmad-correct-course
sequencing: land BEFORE G-PUBLISH (profile-offer publishing) so the operator can observe slice/recompute queue effects once publishing begins
---

# ADMIN-JOBS-1 — Admin worker/job console for ARQ queues (discovery + design spec)

<!--
  ROUTING + SCOPE NOTE (read first).

  This is a DISCOVERY / architecture+UX design spec, NOT a bmad-create-story output and NOT a
  sprint-ready story. It is authored at ITCM (Laura/controller) direction as the pre-work that the
  canonical BMAD entry point — bmad-correct-course — will formalize into planning artifacts.

  Why this shape (BMAD vanilla-first, AGENTS.md § "BMAD vanilla-first" item 3): ADMIN-JOBS-1 is a NEW
  feature after MVP. The canonical entry for any post-ship scope change is `bmad-correct-course`, which
  lands the new Initiative/Epic into prd.md / architecture.md / epics.md (the `## Initiative N` H2-append
  pattern), after which bmad-sprint-planning seeds the sprint-status row and bmad-create-story authors
  the numbered per-story spec(s) in this directory. This pass does the grounded discovery that feeds
  correct-course; it does NOT edit planning artifacts, does NOT assign a real epic/story number, and does
  NOT touch apps/ code. Filename uses the repo's unnumbered `spec-*.md` design-spec convention
  (cf. spec-deploy-skip-gate-range.md, spec-ui-light-theme-polish.md) precisely because no epic number is
  assigned yet — fabricating `34-1-…` would pre-empt correct-course's job.

  GATE: implementation stays blocked until (a) bmad-correct-course lands the epic and (b) the operator's
  dev-go gate fires (same gate shape as the 33.x SCP § 7). See § 13 (Routing & next BMAD step) and
  § 11 (sprint-status decision).

  The one judgment call surfaced for the controller: authoring a design-spec doc in
  implementation-artifacts/ *before* correct-course runs. Precedent exists (the 33.x flow had an SCP +
  design specs precede the numbered stories); this is discovery feeding the canonical entry, not a
  route-around of it. Flagged transparently per § 13.
-->

## 1. Business goal & use cases (translated from operator's Polish source)

**As an admin, I want a frontend panel showing the state of the backend job queues/workers, so I can see
whether the changes I make wake the backend and whether jobs are queued, running, succeeded, or failed.**

Primary use cases (operator-stated):

- **UC1 — "Did my change wake the backend?"** I change STL files / render inputs, or I change profile
  offers → I open the job-queue panel to confirm a worker is already picking the work up
  (queued → running).
- **UC2 — "Why hasn't anything changed after 5 minutes?"** I changed STL/render inputs, waited 5 minutes,
  still see no result → I open the panel and check whether another task is currently running (e.g. a
  profile-offer / slicer job ahead of mine) or whether nothing was enqueued at all.
- **UC3 — "What are these red jobs?"** I open the panel out of curiosity → I notice failed jobs → I ask
  Laura/ITCM what they are and whether they're already handled. (Implies failures must be **legible and
  durable enough to discuss after the fact** — see the ledger tradeoff in § 5.)

Non-goals for the MVP, stated up front (detail in § 12): no retry / kill / purge / pause / resume
controls; no raw Redis/ARQ internals dump as the product surface; no WebSocket/SSE; no multi-instance
fan-in.

## 2. Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] § A — existence checklist)

Every claim below is grounded in current code (file:line) or in the installed `arq==0.28.0` source
(`apps/api/.venv/.../arq/`). The MVP must REUSE these seams, not re-implement them.

1. **ARQ pools already exist (3); no console reads them yet.** All three `WorkerSettings`
   are live and there is **no** API endpoint exposing queue/job/worker state today — `GET /api/health`
   (`apps/api/app/main.py:200-202`) returns only `{"status":"ok","version":…}` and never touches arq.
   (§ 3 enumerates the pools.)
2. **arq pool + raw Redis are owned by the FastAPI lifespan.** `app.state.arq = await create_pool(...)`
   and `app.state.redis = RedisFactory(...)` are created once in `apps/api/app/main.py:64-94` and closed
   on shutdown. Handlers reach them via `request.app.state.arq` / `request.app.state.redis.get()` — the
   console endpoint MUST use these, not open ad-hoc connections (project-context backend rule).
3. **arq exposes a usable read surface (REUSE, do not invent):** `ArqRedis.queued_jobs(queue_name=…)`
   (`arq/connections.py:210`), `ArqRedis.all_job_results()` (`:192`), `Job.status()` →
   `JobStatus{deferred,queued,in_progress,complete,not_found}` (`arq/jobs.py:25-39`,`:152-169`), and the
   per-queue health-check key (§ 6). Key prefixes are fixed in `arq/constants.py`:
   `arq:job:`, `arq:in-progress:`, `arq:result:`, `arq:retry:`, queue-name health suffix `:health-check`.
4. **Business-keyed job status ALREADY partially exists (REUSE as the context layer):**
   - Render worker writes `render:status:{model_id}` and `render:stl_preview:{model_file_id}` Redis keys
     with values `running|done|failed`, 60-min TTL (`workers/render/render/worker.py` ~`:23-24,67,206-210,242-256,321-376`).
     The render enqueue endpoint already returns a `status_key` to the client for polling
     (`apps/api/app/modules/sot/admin_router.py:408,415`).
   - Slicer keeps an `EstimateStatus` (`fresh|stale|queued`) in `EstimateStore` (slicer module), keyed by
     `(stl_hash, bundle_hash)`.
   These give *model/estimate-keyed* status with reasons — the console can surface them as the "what was
   this job about" layer for MVP without building a new ledger (§ 5 tradeoff).
5. **Admin backend convention (NEW sibling, follow precedent):** admin reads live in a per-module
   `admin_router.py` mounted in `apps/api/app/router.py`; e.g. `sot/admin_router.py`,
   `share/admin_router.py`, `slicer/admin_router.py` (the 33.1 sibling, prefix `/api/admin`,
   `current_admin` as a **default-value dependency**: `_user_id: uuid.UUID = current_admin`,
   `apps/api/app/core/auth/dependencies.py:76`). A new console endpoint follows this exact shape.
6. **Route-enforcement gate (CONTRACT):** `apps/api/tests/test_route_enforcement_gate.py` iterates the
   FastAPI route table and requires every `/api/*` route to carry an auth `Depends` **or** appear in
   `_PUBLIC_ROUTES` (`apps/api/app/main.py:50`). A `current_admin`-gated console route passes with **no**
   `_PUBLIC_ROUTES` edit. Do not touch the allowlist.
7. **Admin FE chrome (EXTEND, mirror profiles tab):** `apps/web/src/modules/admin/AdminTabs.tsx`
   (Users / Invites / Profiles / Profile Library / Profile Offers) + per-tab route under
   `apps/web/src/routes/admin/*.tsx`. The auth discipline is the Init 10 retro rule: defer to the shell
   `AuthGate` for anonymous (no synchronous `<Navigate>` that strips `?next=`); role-tier redirect only
   for **authenticated-non-admin**. The console adds one tab + one route, mirroring `profiles.tsx`.
8. **The `/queue` module slot is NOT this feature.** `apps/web/src/routes/queue/index.tsx` +
   `ModuleRail.tsx:10` (`{key:"queue", to:"/queue"}`) are the **member-facing future print queue**
   (AGENTS.md:7 — "print queue" among the v2 modules), a "Coming soon" stub. ADMIN-JOBS-1 is
   **operator/infra observability**, semantically different. **Decision D1 (§ 9): the console lives in the
   admin area (`/admin/queues`), NOT in the member `/queue` slot.** Conflating them would mis-scope a
   member module and put infra internals on a member route.
9. **i18n + visual conventions (EXTEND):** admin keys under `admin.*` / `modules.admin.*` in
   `apps/web/src/locales/{en,pl}.json` (full key parity, Polish diacritics; product nouns like queue
   names stay untranslated). Visual snapshots in `apps/web/tests/visual/*.spec.ts` with API stubbed via
   `apps/web/tests/visual/api-stubs.ts`; admin specs already exist (`admin-users.spec.ts`,
   `admin-profiles.spec.ts`, …). Adding a TanStack route ripples `routeTree.gen.ts` (regen per
   [[reference_web_routetree_regen]]) and the AdminTabs visual baselines.
10. **Defensive policies in scope:** (a) the NFR "no member-reachable surface leaks infra" family —
    enforced here by `current_admin` + the leak fence (§ 8); (b) "no ad-hoc Redis connection" — enforced
    by reusing `app.state`. No earlier-initiative policy is *reversed* by this work.

## 3. ARQ topology — the three pools (grounded)

| Pool | File | `queue_name` | Functions | Cron | `max_jobs` | `job_timeout` | health key (derived) |
|---|---|---|---|---|---|---|---|
| **API** | `apps/api/app/workers/__init__.py:31` | `arq:api` | `cleanup_refresh_tokens`, `generate_thumbnail`, `poll_spoolman_summary` | cleanup @03:15 UTC; spoolman poll @60s | default | default | `arq:api:health-check` |
| **Render** | `workers/render/render/worker.py:450` | `arq:queue` (default) | `render_model`, `render_stl_previews` | none | 2 | 300s | `arq:queue:health-check` |
| **Slicer** | `apps/api/app/modules/slicer/worker.py:60` | `arq:slicer` | `slice_estimate` | none | `settings.slicer_max_concurrency` | dynamic | `arq:slicer:health-check` |

**Enqueue sites (REUSE knowledge for context extraction):**

| Site | Target fn | Queue | Job-id strategy |
|---|---|---|---|
| `sot/admin_service.py::enqueue_render` (~`:1794`) | `render_model` | `arq:queue` | random |
| `sot/admin_router.py` (~`:495`) | `generate_thumbnail` | `arq:api` (`_queue_name=API_QUEUE_NAME`) | random |
| `share/router.py` (~`:125`) | `render_stl_previews` | `arq:queue` | random (single-flight Redis lock) |
| `slicer/enqueue.py::enqueue_slice_estimate` (~`:61`) | `slice_estimate` | `arq:slicer` | **deterministic** `slice:<stl_hash>:<bundle_hash>` |
| `slicer/recompute.py::enqueue_recompute` (~`:184`) | `slice_estimate` | `arq:slicer` | **deterministic** (same id → idempotent re-slice) |

**Cross-queue contract (do not break):** `apps/api/app/workers/__init__.py:19-27` mandates that every
api-side `enqueue_job` pass `_queue_name=API_QUEUE_NAME` so the render worker doesn't grab and reject the
job ("function not found", the pre-Init-8 bug). The console is read-only and does not enqueue, so it
cannot regress this — but the console's per-queue grouping makes a future cross-queue misroute *visible*,
which is a bonus diagnostic.

## 4. ARQ read surface — what raw arq can and cannot tell us (grounded in arq 0.28.0)

| Signal | How (cheap → expensive) | Cost | Caveat |
|---|---|---|---|
| **Queued depth** per queue | `redis.zcard("<queue_name>")` | O(1), no scan | exact, live |
| **Queued job list** per queue | `ArqRedis.queued_jobs(queue_name=…)` → `zrange` + per-job deserialize | O(n) deserialize | **deserializes pickled `args`/`kwargs`** → leak risk (§ 8) |
| **Running ("in_progress")** | key existence `arq:in-progress:<job_id>` | needs ids → **SCAN** `arq:in-progress:*` | bounded by total concurrency (≤ ~5 here); no native list method |
| **Per-queue counters + last heartbeat** | read `<queue>:health-check` string | O(1) per queue | string `j_complete/j_failed/j_retried/j_ongoing/queued` + ts; refreshed only every `health_check_interval` (§ 6) |
| **Recent results (success/fail)** | `all_job_results()` = **`KEYS arq:result:*`** + per-key deserialize | **O(N) blocking `KEYS`** + deserializes `result`/`args` | **must replace with bounded `SCAN`**; results expire (`keep_result`, default 1h) — ephemeral |
| **Single job status** | `Job(job_id).status()` | O(1) pipeline | only if you already hold the id |

`JobResult` fields available (`arq/jobs.py:58-64`, confirmed via `deserialize_result`): `function`,
`args`, `kwargs`, `job_try`, `enqueue_time`, `success`, `result`, `start_time`, `finish_time`,
`queue_name`, `job_id`. **`args`, `kwargs`, `result` are pickled business payloads — they are the leak
surface and must never reach the frontend (§ 8).**

**Hard finding — KEYS:** `all_job_results()` uses Redis `KEYS arq:result:*` (`arq/connections.py:192-208`),
which blocks Redis and is exactly the "broad key scan" the controller warned against. MVP must use a
**bounded `SCAN` with `MATCH arq:result:* COUNT <small>` and a hard cap** (see § 7 magic-constant note),
or accept the low cardinality given the 1h TTL — but never an unbounded `KEYS` in a request path.

## 5. Decision D2 — data model: raw-arq snapshot now, durable ledger deferred (the tradeoff the controller asked us to justify)

**Options considered:**

- **(A) Raw-arq snapshot only.** Compute everything per-request from Redis (zcard + health keys +
  in-progress SCAN + bounded result SCAN). No new table, no worker changes.
- **(B) Application-level normalized job-activity ledger.** A DB-backed append-only event model
  (`queued → started → succeeded/failed`, with business context: which model/profile/STL, who triggered,
  duration, error class) written by each worker/enqueue path; the console reads the table.
- **(C) Hybrid.** Raw-arq for the *live* layer (queued/running/liveness — UC1, UC2); a ledger for the
  *durable, context-rich failure history* (UC3 "ask Laura later").

**Decision: ship (A) for the MVP slice; design toward (C) with the ledger as an explicit deferred slice.**

Justification (contract-pointed, not preference):

- UC1 + UC2 need only the **live** state (is work queued / running right now). Raw arq answers these
  exactly and cheaply (zcard + in-progress SCAN + health key). No ledger required.
- UC3 needs failures to be **legible and survive long enough to discuss**. Raw arq results expire with
  `keep_result` (default **1h**, `arq/jobs.py` + worker default) and carry **no business context** (only
  function name + pickled args). So raw arq is *sufficient for failures inside the 1h window* but
  *insufficient for "what was this red job about, days later."*
- **The MVP closes the UC3 gap cheaply by reusing the existing business-keyed status keys** (§ 2.4:
  `render:status:{model_id}`, slicer `EstimateStatus`) as the context layer, instead of building a new
  table. This gives "this failed job was the render for model X" without worker instrumentation or an
  Alembic migration — i.e. **MVP risk stays at API-read-only**.
- The full durable ledger (B) is **deferred** because it is invasive: it touches every enqueue site and
  every worker function (write-on-transition), needs an Alembic migration, and risks the worker
  idempotency/retry contract. Visibility-first (the controller's stated philosophy) means we prove the
  surface with (A)+(reuse) before paying (B)'s cost. The deferred ledger is named in § 12 so it is a
  planned next slice, not a silent omission.

**Consequence baked into the UX (§ 9):** the console must be **honest about retention** — it labels the
recent-history panel as "last ~1h (Redis-resident)" so the operator is not misled into thinking a
disappeared failure was resolved. That honesty *is* the bridge until the ledger lands.

## 6. Decision D3 — worker liveness strategy (and the hourly-granularity finding)

arq sets `<queue_name>:health-check` to a human-readable string every `health_check_interval` seconds and
gives it TTL `(interval+1)*1000 ms` (`arq/worker.py:255-259,773-785`).

**Hard finding:** `health_check_interval` defaults to **3600 s (1 hour)** and **none of the three pools
override it** (§ 3). So out of the box:

- The health key is refreshed at most **once per hour** (or right after a job completes *if* an hour has
  elapsed), and expires ~1h after the last refresh.
- Therefore "is this worker alive *right now* (last few seconds)?" is **NOT answerable** from the health
  key at useful resolution. A worker that has been idle <1h shows a stale-but-present key; a worker dead
  >1h shows an absent key.

**MVP liveness model (no worker change required):** present liveness as a **tri-state derived from the
health key's presence + age**, honestly labelled:
- `alive` — health key present AND age < interval (fresh heartbeat).
- `idle/stale` — health key present but age ≥ interval (alive-but-quiet, or just-missed-refresh).
- `unknown/down` — health key absent (no heartbeat within ~1h ⇒ likely down, but cannot distinguish
  "down" from ">1h idle" without the override below).

Show the raw heartbeat counters (`j_complete/j_failed/j_retried/j_ongoing/queued`) and the heartbeat
timestamp verbatim so the operator can reason about it.

**Recommended deferred enhancement (flag, do not do this pass):** lowering `health_check_interval` to e.g.
30–60 s on each `WorkerSettings` gives true near-real-time liveness. That is a **worker-config change**
(`apps/api/app/workers/__init__.py`, `workers/render/render/worker.py`,
`apps/api/app/modules/slicer/worker.py`) → triggers a worker image rebuild/redeploy and is **out of this
read-only API-only MVP**. Surfaced as **Open Decision OD-2 (§ 10)** for the operator: accept hourly-coarse
liveness for MVP, or pull the interval-lowering into the first slice (small but crosses into worker code +
deploy). Recommended default: **accept coarse liveness for MVP**; the *running/queued* signals (which UC1/UC2
actually need) are exact regardless of health-key granularity.

## 7. Backend design (proposed — to be ratified by correct-course/create-story)

**Endpoint (read-only, admin-only):** `GET /api/admin/queues` (new `apps/api/app/modules/queue/admin_router.py`
or co-located under an admin observability module; the backend `queue` slot has no Python package yet —
correct-course decides module home). Mounted in `apps/api/app/router.py`; `current_admin` default-value
dep; absent from `_PUBLIC_ROUTES`.

**Response shape (proposed DTO):**

```jsonc
{
  "generated_at": "2026-06-06T12:00:00Z",
  "queues": [
    {
      "name": "arq:slicer",            // stable id; display label from a fixed FE map, untranslated
      "role": "slicer",                // friendly role: api | render | slicer
      "queued": 3,                     // zcard(queue_name) — exact, live
      "running": 1,                    // count of in-progress jobs attributed to this queue
      "worker": {
        "liveness": "alive|idle|unknown",   // D3 tri-state
        "heartbeat_at": "…|null",
        "heartbeat_age_s": 12,
        "interval_s": 3600,            // surfaced so the operator understands granularity
        "counters": { "complete": 120, "failed": 2, "retried": 1, "ongoing": 1, "queued": 3 }
      }
    }
  ],
  "running_jobs": [                    // bounded SCAN arq:in-progress:* → resolve job def
    { "queue": "arq:queue", "function": "render_model", "job_id": "…",
      "started_age_s": 42, "context": { "kind": "model", "ref": "<model_id>" } }
  ],
  "recent": [                          // bounded SCAN arq:result:* (NOT KEYS), capped, last ~1h
    { "queue": "arq:slicer", "function": "slice_estimate", "outcome": "failed",
      "finished_at": "…", "duration_s": 8.1, "job_id": "slice:…",
      "context": { "kind": "estimate", "ref": "<stl_hash-prefix>" }, "error_class": "<curated>" }
  ],
  "retention_note": "recent[] is Redis-resident (~1h); durable failure history is a deferred slice"
}
```

**Computation (all via `app.state`):**
- `queued` = `redis.zcard(queue_name)` per pool. Exact, no scan.
- `worker` = parse `<queue>:health-check` string + compute age from TTL/timestamp.
- `running_jobs` = bounded `SCAN MATCH arq:in-progress:* COUNT <small>`; for each id, `Job(id).info()` to get
  function + (curated) context; attribute to queue by the in-progress job's def. Cardinality ≤ total
  concurrency (≈ 1 api + 2 render + N slicer) so the SCAN is tiny.
- `recent` = bounded `SCAN MATCH arq:result:* COUNT <small>` with a **hard cap** (§ magic-constant), per
  key `deserialize_result` → project to the **allowlisted** fields only; group by `JobResult.queue_name`.
- `context` = derived from the **existing** business-keyed status keys (§ 2.4) and/or the job id
  (slicer's deterministic `slice:<stl_hash>:<bundle_hash>` yields a stl-hash prefix). **Never** from raw
  `args`/`kwargs`/`result`.

**Logging/observability:** namespaced logger `app.queue.admin` (project-context backend rule); structured
JSON; no payloads logged.

## 8. Decision D4 — privacy / leak fence (the load-bearing safety contract)

The single biggest risk: arq stores **pickled `args`, `kwargs`, and `result`** on every queued job and
every result (§ 4). These can contain absolute filesystem paths, model internals, Spoolman data, token
material, or anything a task was called with. **The console must never serialize raw arq payloads.**

Fence (each clause becomes an AC + a negative test in the eventual story):

1. **Admin-only.** `current_admin`; non-admin → 403; anonymous → 401. Route-enforcement gate green with
   no `_PUBLIC_ROUTES` edit (§ 2.6).
2. **Field allowlist, not denylist.** The DTO carries only: `queue_name`, friendly `role`, `function`
   name, `job_id`, counts, timings/ages, `success/outcome`, liveness, and a **curated `context`**. A test
   asserts the serialized response matches the allowlist and contains **no** `args`/`kwargs`/`result`
   keys (mirrors the 33.1 AC-9 provenance fence pattern).
3. **No raw paths / no raw error bodies.** `error_class` is a curated category (exception type name at
   most), never a traceback or message that might embed a path or secret. `context.ref` is an id /
   hash-prefix, never a filesystem path. Negative test asserts no path-like substrings (`/`, drive
   letters, `..`).
4. **No `args`/`kwargs` deserialization leak.** `queued_jobs()` deserializes args; the console either
   avoids `queued_jobs()` entirely (uses `zcard` for depth + `Job.info()` only for the bounded
   in-progress set, reading function name only) or, if a queued list is shown, projects function + id +
   enqueue-time only.
5. **No secrets, ever** (project-context cross-cutting rule). JWT/admin/Spoolman secrets never appear;
   the health string and counters contain none, but the fence test guards regressions.
6. **No destructive surface.** Endpoint is `GET` only; no enqueue, no abort, no purge (those are deferred
   operator-action slices, § 12). The console cannot mutate queue state.

## 9. Frontend / UIX design (proposed)

**D1 (restated): home = admin area, new tab `/admin/queues`.** Mirror the profiles-tab pattern
(`AdminTabs.tsx` + `routes/admin/queues.tsx`), AuthGate discipline (defer to shell for anonymous;
role-tier redirect only for authenticated-non-admin). **Not** the member `/queue` module slot.

**Layout (operator-first, maps to the use cases):**

- **Per-queue cards (3): API / Render / Slicer.** Each shows: friendly role + queue id, a prominent
  **queued** and **running** count (the UC1/UC2 headline), a **liveness chip** (alive/idle/unknown, with
  the heartbeat age + interval shown so coarse granularity is honest), and the raw counters
  (complete/failed/retried). Failed-count is visually weighted (the UC3 "I notice red jobs" entry point).
- **"Running now" strip.** The bounded in-progress list: function + which queue + how long it's been
  running + curated context (e.g. "render_model · model <id>"). Directly answers UC2 ("is something else
  running ahead of mine?").
- **"Recent (~last hour)" list.** Successes + failures from the result SCAN, grouped/filterable by queue
  and outcome, each with function + duration + curated context + curated `error_class` on failures.
  **Explicitly labelled with the retention caveat** (§ 5 consequence) so a vanished failure is not read
  as "resolved".
- **States:** loading → skeleton (not a bare spinner); empty queue → "no jobs queued" (not an error);
  endpoint error → error panel + Retry. **Console fails CLOSED/visible** (admin surface): never fabricate
  green/empty when the read failed (mirrors 33.1 AC-15 admin-fails-closed discipline).

**Polling (not WebSocket/SSE for MVP):** the panel polls `GET /api/admin/queues` on an interval while the
tab is focused; pause when the tab/document is hidden. Interval is a **magic constant — see § magic-constant
note below.**

**a11y / theme / i18n:** status conveyed by icon + text + color (never color alone, WCAG 1.4.1 — same bar
as 33.1 AC-13); zero inline hex, reuse existing tokens (`--color-success` already added in 33.1,
`--color-warning`, `--color-destructive`, `text-muted-foreground`); all copy via `useTranslation()` with
`modules.admin.queues.*` keys in **both** `en.json` + `pl.json` (full parity, Polish diacritics). Queue
ids/function names stay **untranslated** (technical identifiers).

### Cache-topology enumeration (per [[feedback_scp_pre_enumeration_phase]] § B — FE fetch story)

| Concern | This story (`["admin","queues"]`) | Related surface |
|---|---|---|
| Staleness budget (`staleTime`) | `staleTime: 0` because "the panel's purpose is live queue state per UC1/UC2 — any staleness defeats it"; backed by interval polling | none — no other surface reads queue infra state |
| Retry policy | default; console fails **closed/visible** (error panel + Retry), no fail-open | n/a |
| Cache propagation on mutations | none (read-only; no mutations exist in MVP) | n/a |
| Cache eviction on route exit | none required (admin-only, no cross-route contamination; consider stopping the poll on unmount) | n/a |
| Cache seeding | none | n/a |

No row diverges with another surface → simple isolated cache; no private-key gymnastics needed. The one
contract is `staleTime: 0` + focus-gated polling, pointed at UC1/UC2 (live state), not at any peer value.

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **Polling interval (proposed 3–5 s):** points to the contract "UC1/UC2 want to *watch* work start/finish;
  the operator's own UC2 mentions a 5-minute wait, so few-second resolution is ample" — **and** is bounded
  below by "must not hammer a homelab single Redis: 3 `zcard` + 2 small SCANs per poll." This is an
  **arbitrary-but-bounded product default** (mark as such): replace if perf telemetry or operator
  preference pins it. (Cf. the TB-016 lesson — do not justify a polling budget by "feels right"; here it
  points to the UC + the Redis-load bound.)
- **`recent[]` SCAN cap (proposed ~50):** arbitrary display/perf default — "enough to spot a cluster of
  failures in the 1h window without unbounded fetch." Mark arbitrary; revisit when the ledger lands.
- **Heartbeat-age `interval_s`:** NOT a constant we choose — it is read from the worker's actual
  `health_check_interval` (3600 s today) and surfaced verbatim. Liveness thresholds derive from it, not
  from a hardcoded number.

## 10. Open decisions (explicit — surfaced for the operator/correct-course)

- **OD-1 — Data model confirmation.** § 5 recommends MVP = raw-arq snapshot + reuse of existing
  business-keyed status keys, with the durable ledger deferred. Confirm, or pull the ledger into the
  first slice (heavier; touches workers + Alembic). *Recommended default: MVP = (A)+reuse; ledger deferred.*
- **OD-2 — Liveness granularity (§ 6).** Accept coarse (~1h) health-key liveness for MVP (running/queued
  stay exact), or pull worker `health_check_interval`-lowering into slice 1 (worker code + redeploy).
  *Recommended default: accept coarse for MVP.*
- **OD-3 — Recent-history retention messaging.** Confirm the UX explicitly labels `recent[]` as "~last
  hour, Redis-resident" (the § 5 honesty bridge). *Recommended default: yes, label it.*
- **OD-4 — Module home for the backend route.** New `apps/api/app/modules/queue/` Python package vs.
  co-locating under an existing admin/observability module. *Recommended default: new `queue` module
  package — it's the natural backend mirror of the v2 `queue` slot, scoped to admin observability for now.*
- **OD-5 — Slicing of the work.** Recommend a single read-only MVP story (backend snapshot endpoint + FE
  admin tab/panel + tests + baselines), mirroring 33.1's "first read-only deploy-clean slice" shape, with
  the ledger + operator-actions as later epic stories. correct-course assigns the actual epic/story
  numbers.

All five have a safe, evidence-backed default; none is a hard blocker to *authoring*. They are operator
calls because they trade scope/risk, which the controller owns (AGENTS.md autonomous-mode "real product
blocker" list — architectural/scope decisions).

## 11. Sprint-status decision (task step 3)

**No `sprint-status.yaml` row is added in this pass.** Justification (evidence-backed):

- `sprint-status.yaml` is the **canonical tracker derived from `epics.md` via `bmad-sprint-planning`**;
  rows are flipped `backlog → ready-for-dev` by `bmad-create-story` and epics `backlog → in-progress` by
  the vanilla first-story rule (see the file's own `last_updated` trail for 33.1, lines 1-2; project-context
  § "BMAD planning artifacts"). A story row presupposes the epic already exists in `epics.md`.
- ADMIN-JOBS-1's epic is **not yet landed** in `epics.md` (latest is Initiative 21 / E33). Hand-adding a
  row referencing a non-existent epic would create a dangling tracker entry and is a procedural drift
  (route-around of the planning chain) — exactly the BMAD vanilla-first anti-pattern AGENTS.md § "BMAD
  vanilla-first" warns against.
- This artifact is a discovery candidate with **implementation BLOCKED**; there is nothing dev-ready to
  track yet.

The sprint-status row is created **after** `bmad-correct-course` lands the epic and `bmad-sprint-planning`
seeds it (§ 13). This is the convention-correct moment, not now.

## 12. Deferred scope (explicit — not silent omissions)

- **Operator-action controls:** retry / kill (abort) / purge / pause / resume. arq *does* support abort
  (`arq:abort` sorted set, `Job.abort()`), so these are feasible later — but they are **destructive queue
  mutations**, deliberately excluded from a visibility-first MVP (controller instruction). Later
  operator-action slice(s) after visibility is proven.
- **Durable job-activity ledger (§ 5 option B/C):** DB-backed append-only event model with business
  context surviving past Redis TTL; worker instrumentation + Alembic migration. The named next slice that
  closes UC3's "discuss it days later" fully.
- **Worker `health_check_interval` lowering (§ 6 / OD-2):** near-real-time liveness; worker-config +
  redeploy.
- **WebSocket/SSE push:** polling is sufficient for MVP per controller; revisit only if polling load or
  latency proves inadequate (no current evidence it will).
- **Multi-instance / historical charts / alerting:** single-homelab, single-instance assumption holds;
  trend charts and "notify me on failure" are post-MVP.
- **Member-facing print `/queue` module:** unrelated v2 slot (§ 2.8); not touched.

## 13. Routing & recommended next BMAD step

1. **`bmad-correct-course`** (canonical entry for this new-feature scope change) — produce the Sprint
   Change Proposal in `planning-artifacts/` and land the new **Initiative 22 / Epic E34** into
   `prd.md` (`bmad-edit-prd`) + `architecture.md` + `epics.md` (manual `## Initiative N` H2-append), with
   the FR/NFR ids (e.g. `FR22-QUEUE-CONSOLE-1`, `NFR22-LEAK-FENCE-1`, `NFR22-AUTH-1`,
   `NFR22-VISUAL-VERIFICATION-1`, `NFR22-I18N-PARITY-1`) and Decisions D1–D4 + OD-1..OD-5 from this spec.
   correct-course also resolves OD-1/OD-2 with the operator (the scope/risk calls).
2. **`bmad-sprint-planning`** — seed the `sprint-status.yaml` epic/story rows from the landed epic.
3. **`bmad-create-story`** — author the numbered per-story spec(s) (e.g. `34-1-admin-queues-console.md`)
   in this directory, consuming this discovery spec + the planning artifacts, with the full AC list.
4. **Operator dev-go gate**, then `bmad-dev-story` on a `feat/E34.1-…` branch (AGENTS.md § Branching).

**Implementation remains BLOCKED** until steps 1–3 + the dev-go gate. This pass is discovery only.

## 14. Tests / gates the eventual story must carry (preview)

- **Backend (TDD red→green, `fakeredis`):** seed fake `arq:*` keys (queued zsets, in-progress keys,
  result keys, health strings) and assert the snapshot DTO; 403-non-admin + 401-anonymous; route-enforcement
  gate green with no `_PUBLIC_ROUTES` edit; **leak-fence test** (allowlist match + negative path/secret/
  args/kwargs/result assertions, § 8); bounded-SCAN-not-KEYS assertion (no unbounded `KEYS` in the path).
- **Frontend (vitest, colocated, `afterEach(cleanup)`):** per-queue cards, running strip, recent list with
  retention label, loading/empty/error (fails-closed), focus-gated polling start/stop, i18n key parity
  (en/pl), no mock of `api()` (intercept at fetch).
- **Visual baselines (mandatory, 4 projects desktop/mobile × light/dark):** populated panel (mixed
  liveness + a failed job), empty, error; API stubbed in `api-stubs.ts`; `baseline-reviewed:` sign-off per
  PNG; AdminTabs baseline ripple from the new tab.
- **Determinism gate:** 3× consecutive identical pytest + vitest counts before merge.
- **Deploy/live-smoke:** MVP is **API-read-only + FE** → no worker image change → **does not** trigger a
  worker/overlay rebuild (cf. 33.1's SW-DEPLOY-1 reasoning). Post-deploy smoke: hit `GET /api/admin/queues`
  with admin creds on `.190` (curl with `X-Portal-Client: web` + cookies, per CLAUDE.md auth ops),
  enqueue a known job (e.g. trigger a thumbnail/render) and confirm it appears queued→running→recent;
  confirm a non-admin gets 403. (If OD-2 pulls in the worker interval change, the smoke must add a worker
  redeploy + heartbeat-freshness check.)

## 15. References

- Memory: [[feedback_scp_pre_enumeration_phase]] (pre-enumeration + cache-topology + magic-constant
  discipline applied in §§ 2, 9), [[reference_web_routetree_regen]] (routeTree regen + AdminTabs baseline
  ripple, § 2.9).
- Template / convention: `_bmad-output/implementation-artifacts/33-1-readonly-admin-profile-inventory.md`
  (read-only admin slice shape, leak-fence pattern, fails-closed UX, deploy-clean reasoning).
- arq 0.28.0 source (grounding): `arq/constants.py` (key prefixes), `arq/jobs.py:25-64,152-169`
  (JobStatus + JobResult), `arq/connections.py:183-220` (`queued_jobs`, `all_job_results`),
  `arq/worker.py:187-259,773-785` (health-check key + interval + counters).
- Code seams: `apps/api/app/main.py:64-94,200-202` (lifespan, health), `apps/api/app/router.py`
  (admin router mounts), `apps/api/app/core/auth/dependencies.py:76` (`current_admin`),
  `apps/api/app/main.py:50` + `apps/api/tests/test_route_enforcement_gate.py` (route gate),
  `apps/api/app/workers/__init__.py`, `workers/render/render/worker.py`,
  `apps/api/app/modules/slicer/worker.py` (the 3 pools), `apps/api/app/modules/{sot,share,slicer}/`
  (enqueue sites + business-keyed status keys), `apps/web/src/modules/admin/AdminTabs.tsx`,
  `apps/web/src/routes/admin/profiles.tsx`, `apps/web/src/shell/ModuleRail.tsx`,
  `apps/web/tests/visual/api-stubs.ts`.
