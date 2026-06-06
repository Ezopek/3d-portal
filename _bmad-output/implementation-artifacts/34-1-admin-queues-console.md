---
baseline_commit: 3e6ed4e24f77fb1b733252c12fc3ae3bc5752930
---

# Story 34.1: Read-only admin ARQ queue console (ADMIN-JOBS-1)

Status: done

<!--
  Authored by bmad-create-story (BMAD-canonical route [CS] Create Story, phase 4-implementation),
  consuming the discovery+design spec _bmad-output/implementation-artifacts/spec-admin-jobs-console.md
  (commit dcb9df8). Source planning artifacts: epics.md § Initiative 22 (Epic E34 + Story 34.1);
  prd.md § Initiative 22 (FR22-QUEUE-SNAPSHOT-1 / FR22-LIVENESS-1 / FR22-CONSOLE-UI-1 + the NFR22-*
  family, all RATIFIED OD-1..OD-5); architecture.md § Initiative 22 (Decisions AO + AP + AQ); source
  SCP sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md (status proposed).

  GATE NOTE (load-bearing): "ready-for-dev" = the story context is complete and dev-ready. It is a
  SPEC gate ONLY. Actual bmad-dev-story execution / code implementation remains BLOCKED until an
  explicit operator dev-go (G-DEVGO). This spec authoring is doc-only — NO code, NO branch, NO deploy,
  NO commit performed here. The MVP is API-read-only + FE → no worker image change → the SW-DEPLOY-1
  overlay-rebuild gate is NOT tripped. ADMIN-JOBS-1 is sequenced BEFORE G-PUBLISH (the Init 21
  PROFILE-OFFER-1 real-resolver publication / live-slicing step) so the operator can observe
  slice/recompute/render queue effects before publishing begins.
-->

## Story

As an **admin/operator of the 3d-portal**,
I want **a read-only in-product console showing the live state of the three ARQ worker pools (API `arq:api`, Render `arq:queue`, Slicer `arq:slicer`) — per pool: how many jobs are queued and running, a tri-state worker-liveness signal, raw heartbeat counters, plus a "running now" strip and a "recent (~last hour)" list of successes/failures with a curated business-context label and a curated error class**,
so that **I can answer at a glance: "did my change wake the backend?" (UC1 — work goes queued→running), "is something already running ahead of mine?" (UC2 — I waited 5 min and nothing changed), and "what are these red jobs?" (UC3 — I notice failures and can discuss them with Laura/ITCM) — without ever exposing raw job payloads or being able to mutate the queues.**

This is the **single read-only, deploy-clean MVP slice** of Epic E34. It introduces **no write/mutation surface (no retry/kill/purge/pause/resume), no new DB table, no Alembic migration, no worker instrumentation, and no `configs` change** — so the SW-DEPLOY-1 overlay rebuild is **NOT** triggered. The durable job-activity ledger (G-LEDGER), operator-action controls (G-ACTIONS), and worker `health_check_interval`-lowering for near-real-time liveness (G-LIVENESS) are explicitly deferred.

## Acceptance Criteria

### Backend — read-only snapshot (`GET /api/admin/queues`)

1. **AC-1 — Endpoint shape & auth.** A new `GET /api/admin/queues` endpoint exists in a new `apps/api/app/modules/queue/` package (`admin_router.py`, OD-4), mounted under `/api/admin` in `apps/api/app/router.py`, **admin-gated via the `current_admin` default-value dependency** (`apps/api/app/core/auth/dependencies.py:76`), and **absent from `_PUBLIC_ROUTES`** (`apps/api/app/main.py:50`). A non-admin (member/agent) request → **403**; an anonymous request → **401**. (FR22-QUEUE-SNAPSHOT-1, NFR22-AUTH-1, Decision AQ clause 1.)
2. **AC-2 — Route-enforcement gate green, no allowlist edit.** Because the route carries an auth `Depends`, the Init 6 route-enforcement gate (`apps/api/tests/test_route_enforcement_gate.py:56`) passes **without** adding the route to `_PUBLIC_ROUTES`. No SCP/allowlist edit is needed or made. (NFR22-AUTH-1.)
3. **AC-3 — Reads only via `app.state`; no ad-hoc connections.** The handler reads the arq pool and raw Redis exclusively via `request.app.state.arq` / `request.app.state.redis` (the FastAPI-lifespan-owned objects created once in `apps/api/app/main.py:90-91`). It **never** opens an ad-hoc Redis/arq connection (project-context backend rule). (Decision AO.)
4. **AC-4 — Snapshot DTO shape.** The response is a `QueueSnapshot` DTO with: `generated_at` (UTC); a `queues[]` array (one entry per pool: `name` ∈ {`arq:api`,`arq:queue`,`arq:slicer`}, friendly `role` ∈ {`api`,`render`,`slicer`}, `queued: int`, `running: int`, and a `worker` sub-object — see AC-7); a `running_jobs[]` array (`queue`, `function`, `job_id`, `started_age_s`, curated `context`); a `recent[]` array (`queue`, `function`, `outcome` ∈ {`success`,`failed`}, `finished_at`, `duration_s`, `job_id`, curated `context`, curated `error_class` on failures); and a `retention_note` string. The three pools are always present even when idle (empty ≠ error). (FR22-QUEUE-SNAPSHOT-1, Decision AO.)
5. **AC-5 — `queued` is exact via `zcard`.** Per pool, `queued = redis.zcard(queue_name)` — exact, O(1), **no scan**. (FR22-QUEUE-SNAPSHOT-1, Decision AO step 1.)
6. **AC-6 — `running_jobs` via bounded SCAN, function-name only.** `running_jobs` is built from a **bounded `SCAN MATCH arq:in-progress:* COUNT <small>`** (never `KEYS`); for each id the handler reads the **function name only** (e.g. via `Job(job_id, ...).info()`), attributes it to a pool, and computes `started_age_s`. Cardinality ≤ total concurrency (≈ 1 api + 2 render + N slicer). It **must not** call `queued_jobs()` (which deserializes pickled args). (FR22-QUEUE-SNAPSHOT-1, NFR22-REDIS-LOAD-1, Decision AQ clause 4.)
7. **AC-7 — Worker liveness tri-state (Decision AP).** Per pool, `worker` carries `liveness` ∈ {`alive`,`idle`,`unknown`} derived from the `<queue>:health-check` key: `alive` = present AND age < `interval_s`; `idle` = present AND age ≥ `interval_s`; `unknown` = absent. It also surfaces `heartbeat_at` (nullable), `heartbeat_age_s` (nullable), `interval_s` (read from the worker's actual `health_check_interval` — **3600s today — NOT a hardcoded console constant**), and the raw `counters` parsed from the health string (`complete`/`failed`/`retried`/`ongoing`/`queued`, from arq's `j_complete/j_failed/j_retried/j_ongoing/queued`). (FR22-LIVENESS-1, Decision AP.)
8. **AC-8 — `recent` via bounded, hard-capped SCAN — NEVER `KEYS`.** `recent` is built from a **bounded `SCAN MATCH arq:result:* COUNT <small>` with a hard cap** (the `recent[]` cap magic-constant, § Magic-constant discipline); it **must not** use `all_job_results()` (which issues an unbounded `KEYS arq:result:*` — `arq/connections.py:192-208`, the exact broad scan the controller warned against). Each result key is `deserialize_result`-ed and projected to the **allowlisted fields only** (AC-10), grouped by `JobResult.queue_name`. The list is ephemeral (arq `keep_result` ~1h TTL). (FR22-QUEUE-SNAPSHOT-1, NFR22-REDIS-LOAD-1, Decision AO step 4.)
9. **AC-9 — Curated `context`, never raw payload.** Each `running_jobs`/`recent` entry's `context` is derived **only** from the existing business-keyed status keys (`render:status:{model_id}`, slicer `EstimateStatus`) and/or the job id (slicer's deterministic `slice:<stl_hash>:<bundle_hash>` yields a stl-hash prefix) — e.g. `{kind: "model"|"estimate"|..., ref: "<id-or-hash-prefix>"}`. It is **never** derived from raw `args`/`kwargs`/`result`. `context.ref` is an id / hash-prefix, **never a filesystem path**. (Decision AO step 5, Decision AQ clause 3.)
10. **AC-10 — Leak fence: field allowlist, not denylist (load-bearing).** The serialized response carries **only** the allowlisted fields enumerated in AC-4/AC-7 (`name`, `role`, `queued`, `running`, liveness fields, counters, `function`, `job_id`, ages/durations/timestamps, `outcome`/`success`, curated `context`, curated `error_class`, `retention_note`, `generated_at`). It contains **no** `args`, `kwargs`, or `result` keys, and no raw pickled payload anywhere. A fence test asserts the response matches the allowlist (mirrors the 33.1 AC-9 provenance fence). (NFR22-LEAK-FENCE-1, Decision AQ clause 2.)
11. **AC-11 — Curated `error_class`, no raw error bodies.** On a failed `recent` entry, `error_class` is a **curated category** (the exception type name at most), **never** a traceback or message that could embed a path or secret. A negative test asserts no path-like substrings (`/`, drive letters, `..`) and no secret-looking material anywhere in the serialized response. (NFR22-LEAK-FENCE-1, Decision AQ clause 3/5.)
12. **AC-12 — Read-only / deploy-clean.** The queue module exposes **`GET` only** — no enqueue, abort, purge, pause, or resume verb/route; the console cannot mutate queue state. No new DB table, no Alembic migration, no worker (`workers/render/` / overlay / `WorkerSettings`) change, no `config.py` change, no `configs`-side coordination. A test asserts the queue module exposes only the read endpoint. (NFR22-READONLY-1, Decision AQ clause 5, G-ACTIONS deferred.)
13. **AC-13 — Namespaced structured logging, no payloads.** The handler uses a namespaced logger `app.queue.admin` with structured JSON per `~/repos/configs/docs/observability-logging-contract.md`; **no job payloads are logged**. (Decision AQ logging clause.)

### Frontend — admin console tab (`/admin/queues`)

14. **AC-14 — Queues admin tab + route.** `AdminTabs.tsx` (`apps/web/src/modules/admin/AdminTabs.tsx:6`) gains a `"queues"` value on `ActiveTab`, a `<Link role="tab" to="/admin/queues">`, and a new `apps/web/src/routes/admin/queues.tsx` route component **mirroring `profiles.tsx`**, including the **AuthGate discipline** (defer to the shell `AuthGate` for anonymous — no synchronous `<Navigate>` that strips `?next=`; role-tier redirect only for **authenticated-non-admin**). Gated on `useAuth().isAdmin`. Adding the route ripples `routeTree.gen.ts` (regen per [[reference_web_routetree_regen]]). (FR22-CONSOLE-UI-1, NFR22-AUTH-1, Init 10 retro rule.)
15. **AC-15 — Per-queue cards (UC1/UC2 headline).** Three per-queue cards (API / Render / Slicer) each render: the friendly role + queue id (untranslated technical id), a prominent **queued** and **running** count (the UC1/UC2 headline), a **liveness chip** (alive/idle/unknown) that also shows `heartbeat_age_s` + `interval_s` so the coarse ~1h granularity is **honest**, and the raw counters (complete/failed/retried/ongoing). The **failed** counter is visually weighted (the UC3 entry point). (FR22-CONSOLE-UI-1, FR22-LIVENESS-1.)
16. **AC-16 — "Running now" strip (UC2).** A strip renders the `running_jobs[]` set: function + which queue + how long it's been running (`started_age_s`) + curated context (e.g. "render_model · model &lt;ref&gt;"). Directly answers UC2 ("is something running ahead of mine?"). Empty → a neutral "nothing running" state (not an error). (FR22-CONSOLE-UI-1.)
17. **AC-17 — "Recent (~last hour)" list with retention label (UC3).** A list renders `recent[]` (successes + failures), filterable by queue and outcome, each row showing function + duration + curated context + curated `error_class` on failures, with failures visually distinguished. The panel is **explicitly labelled "~last 1h, Redis-resident"** (from `retention_note`) so a vanished failure is **not** misread as "resolved." (FR22-CONSOLE-UI-1, NFR22-RETENTION-HONESTY-1.)
18. **AC-18 — Fails-closed states (admin-fails-closed discipline).** Loading → a **skeleton** (not a bare spinner). Empty queues → "no jobs queued" / "nothing running" (not an error). `GET /api/admin/queues` error → an **error panel + Retry**; the console **must not** fabricate a green/empty state on a failed read (mirrors 33.1 AC-15 admin-fails-closed). (FR22-CONSOLE-UI-1.)
19. **AC-19 — Focus-gated polling (NFR22-REDIS-LOAD-1).** The panel polls `GET /api/admin/queues` on a bounded interval (the polling-interval magic-constant, § Magic-constant discipline) **while the tab/document is visible**, and **pauses when hidden** (`visibilitychange`). TanStack Query key `["admin","queues"]`, `staleTime: 0` (live-state purpose per UC1/UC2). No WebSocket/SSE. (FR22-CONSOLE-UI-1, NFR22-REDIS-LOAD-1.)
20. **AC-20 — a11y / theme / i18n.** Status is conveyed by **icon + text + color** (never color alone, WCAG 1.4.1 — same bar as 33.1 AC-13); **zero inline hex**, reusing existing tokens (`--color-success` [added in 33.1], `--color-warning`, `--color-destructive`, `text-muted-foreground`, `border-border`). All copy via `useTranslation()`. (FR22-CONSOLE-UI-1, project-context frontend rule.)

### Cross-cutting — i18n, visual, determinism

21. **AC-21 — i18n parity.** New keys under `modules.admin.queues.*` (tab label, per-card labels, the three liveness labels, counter labels, running-strip + recent-list headers, the retention caveat string, outcome/error labels, loading/empty/error copy) land in **both `en.json` + `pl.json` with full key parity** and correct Polish diacritics. Queue ids (`arq:api`/`arq:queue`/`arq:slicer`) and arq **function names** stay **untranslated** (technical identifiers). (NFR22-I18N-PARITY-1.)
22. **AC-22 — Visual baselines.** New Playwright baselines across the 4 projects (`desktop-light/dark`, `mobile-light/dark`), each with a `baseline-reviewed:` sign-off line: (1) **populated** console — mixed liveness across the three cards + a failed job in the recent list + a running job in the strip; (2) **empty** (idle pools, nothing running, empty recent); (3) **error** panel (fails-closed). API stubbed via `apps/web/tests/visual/api-stubs.ts`. The new admin tab ripples the `AdminTabs` visual baselines. (NFR22-VISUAL-VERIFICATION-1, [[reference_web_routetree_regen]].)
23. **AC-23 — Determinism gate.** 3× consecutive identical pytest + vitest pass counts before merge. (NFR22-DETERMINISM-1.)

## Tasks / Subtasks

- [x] **T1 — Backend queue module + snapshot endpoint (AC-1..AC-9, AC-12, AC-13)**
  - [x] Create `apps/api/app/modules/queue/__init__.py` + `apps/api/app/modules/queue/admin_router.py` with `router = APIRouter(prefix="/api/admin", tags=["admin-queues"])` and `GET /queues`, admin-gated (`_user_id: uuid.UUID = current_admin`), mirroring the `sot/admin_router.py` / `slicer/admin_router.py` sibling convention.
  - [x] Mount in `apps/api/app/router.py` (`include_router`) alongside the other admin routers.
  - [x] Add DTO schemas (`QueueSnapshot`, `QueueEntry`, `WorkerLiveness`, `RunningJob`, `RecentJob`) in a `schemas.py` in the new module (Pydantic v2, `extra="forbid"`; allowlist-only fields per AC-10).
  - [x] Compute `queued` via `redis.zcard(queue_name)` (AC-5); `worker` liveness + counters from the `<queue>:health-check` string with age from the heartbeat ts / TTL (AC-7); `running_jobs` via bounded `SCAN arq:in-progress:*` + function-name-only resolution (AC-6); `recent` via bounded hard-capped `SCAN arq:result:*` + `deserialize_result` → allowlist projection (AC-8); `context` from business-keyed status keys / job id only (AC-9); `retention_note`.
  - [x] All Redis/arq access through `request.app.state.arq` / `.redis` only (AC-3). Namespaced logger `app.queue.admin`, no payloads (AC-13).
  - [x] Define the three pools + their `health-check` key derivation in **one** small backend table/const (queue id → role), single source of truth for both the snapshot and the tests.
- [x] **T2 — Magic-constant declarations (§ Magic-constant discipline)**
  - [x] Declare the `recent[]` SCAN hard cap and the `SCAN COUNT` as named backend constants with docstrings pointing each to its contract (display/perf default + homelab single-Redis load bound) — NOT "feels right" (TB-016 lesson). The FE polling interval is a named FE constant, similarly documented.
- [x] **T3 — Backend tests (AC-1,2,6,7,8,10,11,12, AC-23)** — TDD red→green with `fakeredis`
  - [x] `apps/api/tests/test_admin_queues_snapshot.py`: seed fake `arq:*` keys — queued zsets (per pool), `arq:in-progress:<id>` keys, `arq:result:<id>` keys (success + failure), `<queue>:health-check` strings of varying age/presence — and assert the snapshot DTO (queued exact; running attribution; recent grouping + outcome).
  - [x] **Liveness tri-state** test (AC-7): `alive`/`idle`/`unknown` over seeded health keys of varying age/presence; assert `interval_s` reflects the seeded value, not a hardcoded number.
  - [x] **Leak-fence** test (AC-10): allowlisted field set on the serialized response; **no** `args`/`kwargs`/`result` keys.
  - [x] **No-path/secret** negative test (AC-11): no path-like substrings / drive letters / `..` / secret-looking material; `error_class` is a curated category.
  - [x] **Bounded-SCAN-not-KEYS** assertion (AC-8): no unbounded `KEYS` in the snapshot path; `recent[]` respects the hard cap; depth via `zcard`.
  - [x] **Auth** tests (AC-1): 403-for-non-admin (member + agent) + 401 anonymous.
  - [x] **Read-only** test (AC-12): the queue module exposes only the read endpoint (no mutating verb/route).
  - [x] **Route-enforcement gate** (AC-2) passes unchanged (no `_PUBLIC_ROUTES` edit).
- [x] **T4 — FE admin tab + route + console (AC-14..AC-20)**
  - [x] Extend `AdminTabs.tsx` `ActiveTab` + add the `Queues` tab link; add `routes/admin/queues.tsx` mirroring `profiles.tsx` (AuthGate discipline). Regen `routeTree.gen.ts` per [[reference_web_routetree_regen]].
  - [x] Add a `useAdminQueues()` hook (TanStack Query, queryKey `["admin","queues"]`, `staleTime: 0`) calling `api("/api/admin/queues")`; focus-gated polling (start on visible, stop on `visibilitychange` hidden) (AC-19).
  - [x] Build per-queue cards (queued/running headline + liveness chip w/ age+interval + raw counters, failed weighted), the "running now" strip, the "recent (~last hour)" list with the retention caveat label + queue/outcome filter, and loading-skeleton / empty / error+Retry (fails-closed) states.
  - [x] Status by icon+text+color; zero inline hex; reuse existing tokens (AC-20).
- [x] **T5 — FE tests (AC-15..AC-21, AC-23)**
  - [x] vitest (colocated, `afterEach(cleanup)` per project-context): per-queue cards across mixed liveness; running strip; recent list **with the retention label**; loading/empty/error (fails-closed); **focus-gated polling start/stop** (mock `visibilitychange`).
  - [x] i18n parity check (en/pl key-set equality; diacritics present; queue ids + function names untranslated).
  - [x] Don't mock `api()` — intercept at the `fetch` level.
- [x] **T6 — Visual baselines (AC-22)**
  - [x] Add stubs to `apps/web/tests/visual/api-stubs.ts` for `/api/admin/queues` (populated / empty / error), add specs producing the 3 fixtures, generate baselines across the 4 projects, and include `baseline-reviewed:` sign-off lines per changed PNG (pre-commit baseline gate). Capture the AdminTabs baseline ripple.
- [x] **T7 — Determinism + self-review (AC-23)**
  - [x] Run backend pytest 3× + vitest 3×, confirm identical counts; run `npm run lint` (`--max-warnings=0`), ruff check/format, typecheck. Full gate (`infra/scripts/check-all.sh`) at merge/closeout per AGENTS.md § Pre-push.

## Dev Notes

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] — existence checklist)

1. **No console reads the pools today (NEW surface, REUSE seams).** `GET /api/health` (`apps/api/app/main.py:200-202`) returns only `{"status":"ok","version":…}` and never touches arq. There is **no** existing queue/job/worker read endpoint. Build a new `queue` module; do not re-implement arq.
2. **arq pool + raw Redis are lifespan-owned (REUSE via `app.state`).** `app.state.redis = RedisFactory(...)` and `app.state.arq = await create_pool(...)` are created once in the FastAPI lifespan (`apps/api/app/main.py:90-91`) and closed on shutdown (`:93-94`). Reach them via `request.app.state.arq` / `.redis` — **never** an ad-hoc connection (project-context backend rule). (AC-3.)
3. **arq read surface (REUSE, do not invent):** key prefixes are fixed in `arq/constants.py` — `arq:job:`, `arq:in-progress:`, `arq:result:`, plus the per-queue `<queue>:health-check` suffix. Depth = `redis.zcard(queue_name)`. **Avoid `ArqRedis.queued_jobs()`** (it deserializes pickled args — leak surface). **Avoid `all_job_results()`** — it issues `KEYS arq:result:*` (`arq/connections.py:192-208`), the unbounded blocking scan the controller forbade; replace with a bounded `SCAN` + hard cap. `Job(job_id).info()` gives the function name without a broad scan once you hold an id. (AC-6, AC-8.)
4. **`JobResult` leak fields (FENCE):** `deserialize_result` yields `function`, `args`, `kwargs`, `job_try`, `enqueue_time`, `success`, `result`, `start_time`, `finish_time`, `queue_name`, `job_id` (`arq/jobs.py:58-64`). **`args`, `kwargs`, `result` are pickled business payloads — they must NEVER reach the DTO** (AC-10/AC-11). Project to the allowlist only.
5. **Business-keyed status keys (REUSE as `context`):** render worker writes `render:status:{model_id}` / `render:stl_preview:{model_file_id}` (`running|done|failed`, 60-min TTL); slicer keeps an `EstimateStatus` (`fresh|stale|queued`) keyed `(stl_hash, bundle_hash)`. These give "what was this job about" without a new ledger. (AC-9.)
6. **Admin router + auth convention (NEW sibling, follow precedent):** admin reads live in a per-module `admin_router.py` mounted in `apps/api/app/router.py` (cf. `sot/admin_router.py`, `share/admin_router.py`, `slicer/admin_router.py`); `current_admin` is a **default-value dependency** — `_user_id: uuid.UUID = current_admin` (`apps/api/app/core/auth/dependencies.py:76`). New `queue/admin_router.py` follows this exact shape. (AC-1.)
7. **Route-enforcement gate (CONTRACT):** `apps/api/tests/test_route_enforcement_gate.py:56` iterates the route table and requires each `/api/*` route to carry an auth `Depends` **or** appear in `_PUBLIC_ROUTES` (`apps/api/app/main.py:50`). A `current_admin`-gated route passes with **no** allowlist edit. Do not touch `_PUBLIC_ROUTES`. (AC-2.)
8. **FE admin chrome (EXTEND, mirror profiles tab):** `AdminTabs.tsx:6` `ActiveTab = "users" | "invites" | "profiles" | "profile-library" | "profile-offers"` — **add `"queues"`** + a `<Link role="tab" to="/admin/queues">`, and a new `routes/admin/queues.tsx` mirroring `routes/admin/profiles.tsx` (AuthGate discipline: defer to shell for anonymous; role-tier redirect only for authenticated-non-admin). Adding a TanStack route ripples `routeTree.gen.ts` ([[reference_web_routetree_regen]]) + the AdminTabs visual baselines. (AC-14, AC-22.)
9. **The member `/queue` slot is NOT this feature.** `apps/web/src/routes/queue/index.tsx` + `ModuleRail.tsx:10` (`{key:"queue", to:"/queue"}`) are the **member-facing future print queue** ("Coming soon" stub). ADMIN-JOBS-1 is operator/infra observability → it lives in the **admin area** (`/admin/queues`), NOT the member slot (Decision AO location clause).
10. **Visual + i18n conventions (EXTEND):** admin keys under `modules.admin.queues.*` in `apps/web/src/locales/{en,pl}.json` (full parity, Polish diacritics; queue ids + function names untranslated). Visual snapshots in `apps/web/tests/visual/*.spec.ts` with API stubbed via `apps/web/tests/visual/api-stubs.ts`; admin specs already exist (`admin-profiles.spec.ts`, …). (AC-21, AC-22.)
11. **Defensive policies in scope (no reversal):** (a) "no member-reachable infra leak" — enforced by `current_admin` + the leak fence (AC-1/AC-10/AC-11); (b) "no ad-hoc Redis connection" — enforced by reusing `app.state` (AC-3). No earlier-initiative policy is reversed by this work.

### ARQ topology — the three pools (grounded)

| Pool | `queue_name` | Source (verified @ baseline 3e6ed4e) | Functions | health key (derived) |
|---|---|---|---|---|
| **API** | `arq:api` | `apps/api/app/workers/__init__.py:28,34` (`API_QUEUE_NAME`) | `cleanup_refresh_tokens`, `generate_thumbnail`, `poll_spoolman_summary` | `arq:api:health-check` |
| **Render** | `arq:queue` (arq default — no explicit `queue_name`) | `workers/render/render/worker.py:450` (`class WorkerSettings`) | `render_model`, `render_stl_previews` | `arq:queue:health-check` |
| **Slicer** | `arq:slicer` | `apps/api/app/modules/slicer/worker.py:35,63` (`SLICER_QUEUE_NAME`) | `slice_estimate` | `arq:slicer:health-check` |

`health_check_interval` defaults to **3600s** and none of the three pools override it (`arq/worker.py:210`; TTL set at `:785` = `(interval+1)*1000 ms`). So liveness is coarse (~1h) — **accepted for MVP** (OD-2/Decision AP/G-LIVENESS); `running`/`queued` stay exact regardless. Surface `interval_s` + `heartbeat_age_s` verbatim so the coarseness is honest.

### Cache-topology enumeration (per [[feedback_scp_pre_enumeration_phase]] § B — FE fetch story)

| Concern | This story (`["admin","queues"]`) | Related surface |
|---|---|---|
| Staleness budget (`staleTime`) | `staleTime: 0` — the panel's purpose is **live** queue state per UC1/UC2; any staleness defeats it. Backed by focus-gated interval polling. | none — no other surface reads queue infra state |
| Retry policy | default; console fails **closed/visible** (error panel + Retry, AC-18), no fail-open | n/a |
| Cache propagation on mutations | none (read-only; no mutations exist in MVP) | n/a |
| Cache eviction on route exit | stop the poll on unmount / `visibilitychange` hidden (AC-19); no cross-route contamination | n/a |
| Cache seeding | none | n/a |

No row diverges with a peer → simple isolated cache. The one contract is `staleTime: 0` + focus-gated polling, pointed at UC1/UC2 (live state), not at any peer value.

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **Polling interval (proposed 3–5 s):** points to the contract "UC1/UC2 want to *watch* work start/finish; the operator's own UC2 cites a 5-minute wait, so few-second resolution is ample" — **and** is bounded below by "must not hammer a homelab single Redis: 3 `zcard` + 2 small SCANs per poll." **Arbitrary-but-bounded product default** — mark as such; replace if perf telemetry or operator preference pins it (TB-016 lesson: do not justify a polling budget by "feels right").
- **`recent[]` SCAN hard cap (proposed ~50):** arbitrary display/perf default — "enough to spot a cluster of failures in the 1h window without an unbounded fetch." Mark arbitrary; revisit when the ledger lands (G-LEDGER).
- **`SCAN COUNT` (small):** a Redis cursor batch hint, not a result cap; keep small to avoid long single calls on the homelab Redis.
- **`interval_s`:** NOT a console-chosen constant — read from the worker's actual `health_check_interval` (3600s today) and surfaced verbatim; liveness thresholds derive from it.

### Open decisions — all RATIFIED to safe default (controller, 2026-06-06)

The discovery spec surfaced OD-1..OD-5; the controller ratified every safe default (prd.md § Initiative 22). None is a remaining blocker to authoring:

- **OD-1 — RATIFIED:** MVP = raw-arq snapshot + reuse of business-keyed status keys; durable ledger **DEFERRED** (Decision AO; G-LEDGER).
- **OD-2 — RATIFIED:** accept coarse (~1h) health-key liveness for MVP (running/queued stay exact); worker `health_check_interval`-lowering deferred (Decision AP; G-LIVENESS).
- **OD-3 — RATIFIED:** label `recent[]` "~last hour, Redis-resident" (AC-17, NFR22-RETENTION-HONESTY-1).
- **OD-4 — RATIFIED:** new `apps/api/app/modules/queue/` package as the backend module home; endpoint `GET /api/admin/queues` (AC-1).
- **OD-5 — RATIFIED:** single read-only MVP story (this story); durable ledger + operator-action controls are later epic stories.

### Gates (carried from epics.md § E34)

- **G-DEVGO** — explicit operator dev-go. **Implementation BLOCKED**; this story is spec authoring only. `ready-for-dev` is a SPEC gate, not a code-go.
- **G-PUBLISH-before** — ADMIN-JOBS-1 is sequenced **BEFORE** the Init 21 PROFILE-OFFER-1 real-resolver-publication / live-slicing step so the operator can observe slice/recompute/render queues before publishing effects.
- **G-LEDGER** — durable job-activity ledger (DB-backed append-only event model surviving past Redis TTL; worker instrumentation + Alembic) — deferred named slice; closes UC3 long-term.
- **G-LIVENESS** — worker `health_check_interval` lowering for near-real-time liveness (worker-config + redeploy) — deferred; running/queued stay exact without it.
- **G-ACTIONS** — destructive operator-action controls (retry/kill/purge/pause/resume) — deferred until visibility is proven.

### Out of scope (deferred with named gates)

Durable job-activity ledger (G-LEDGER); retry/kill/purge/pause/resume operator-action controls (G-ACTIONS); worker `health_check_interval` lowering (G-LIVENESS); WebSocket/SSE push; multi-instance / historical charts / alerting; the member-facing print `/queue` module slot (unrelated v2 surface).

### Deploy / smoke (preview — gated on G-DEVGO, not part of spec authoring)

MVP is **API-read-only + FE** → no worker image change → **SW-DEPLOY-1 overlay rebuild NOT triggered** (cf. 33.1 deploy-clean reasoning); standard API+web deploy path. Post-deploy smoke (when dev-go fires): `GET /api/admin/queues` with admin creds on `.190` (curl with `X-Portal-Client: web` + cookies, per CLAUDE.md auth ops), enqueue a known job (e.g. trigger a thumbnail/render), confirm it appears queued→running→recent; confirm a non-admin gets 403.

### References

- Discovery + design: `_bmad-output/implementation-artifacts/spec-admin-jobs-console.md` (ADMIN-JOBS-1, commit `dcb9df8`) — grounds every seam.
- PRD: `prd.md` § Initiative 22 (FR22-QUEUE-SNAPSHOT-1 / FR22-LIVENESS-1 / FR22-CONSOLE-UI-1 + NFR22-* + ratified OD-1..OD-5).
- Architecture: `architecture.md` § Initiative 22 (Decision AO read-model+location+ledger-deferred / AP coarse-health-key liveness / AQ leak-fence read-only privacy).
- Epics: `epics.md` § Initiative 22 (Epic E34 + Story 34.1).
- Source SCP: `sprint-change-proposal-2026-06-06-init22-admin-jobs-console.md` (status `proposed`).
- Template / convention: `_bmad-output/implementation-artifacts/33-1-readonly-admin-profile-inventory.md` (read-only admin slice shape, leak-fence pattern, fails-closed UX, deploy-clean reasoning).
- arq 0.28.0 grounding: `arq/constants.py` (key prefixes), `arq/jobs.py:25-64,152-169` (JobStatus + JobResult leak fields), `arq/connections.py:183-220` (`queued_jobs`, `all_job_results` = `KEYS`), `arq/worker.py:171,210,255,775,785` (health-check key + `health_check_interval` default 3600 + counters + TTL).
- Code seams (verified @ baseline 3e6ed4e): `apps/api/app/main.py:50,90-91,93-94,200-202`; `apps/api/app/router.py` (admin router mounts); `apps/api/app/core/auth/dependencies.py:76` (`current_admin`); `apps/api/tests/test_route_enforcement_gate.py:56`; `apps/api/app/workers/__init__.py:28,34`; `workers/render/render/worker.py:450`; `apps/api/app/modules/slicer/worker.py:35,63`; `apps/web/src/modules/admin/AdminTabs.tsx:6`; `apps/web/src/routes/admin/profiles.tsx`; `apps/web/src/shell/ModuleRail.tsx`; `apps/web/tests/visual/api-stubs.ts`.
- Memory: [[feedback_scp_pre_enumeration_phase]] (pre-enumeration + cache-topology + magic-constant contract discipline — §§ above), [[reference_web_routetree_regen]] (routeTree regen + AdminTabs baseline ripple).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, bmad-dev-story workflow). Operator dev-go (G-DEVGO) granted 2026-06-06; implemented on branch `feat/E34.1-admin-queues-console` off `main@d05847d`.

### Debug Log References

- arq 0.28.0 grounded directly in the installed package (`apps/api/.venv/.../arq/`): key prefixes (`arq:job:`/`arq:in-progress:`/`arq:result:`), `<queue>:health-check` suffix, `JobDef`/`JobResult` leak fields, `deserialize_job`/`deserialize_result`, and `all_job_results`==unbounded `KEYS` (deliberately NOT used). Confirmed `health_check_interval` default = 3600 and `job_timeout` default = 300 via `inspect.signature(arq.worker.Worker)`.
- Backend test seam: `app.dependency_overrides[get_queue_conn]` injects a `fakeredis.aioredis.FakeRedis` wrapped in a `_NoKeysRedis` proxy that raises on any `.keys(...)` — the bounded-SCAN-not-KEYS contract (AC-8) is asserted structurally, not just by output shape.
- Liveness derivation uses the health-key remaining TTL (`pttl`): `age = (interval+1) - ttl_s`; `alive` when `age < interval`, `idle` otherwise, `unknown` when absent (`pttl == -2`). `interval_s` is read from arq's contract (its `health_check_interval` default, which no pool overrides) — NOT a console literal (AC-7).
- `running_jobs` attribution is by arq function-name → pool (a running job is no longer in any queue zset), via the single `FUNCTION_TO_POOL` map in `constants.py`. `started_age_s` is derived from the job blob's `enqueue_time` (the only per-job timestamp arq persists for an in-progress job) — documented as an MVP proxy in `service.py`.
- `context.ref` for slicer jobs is the stl-hash prefix parsed from the deterministic `slice:<stl_hash>:<bundle_hash>` job id (`app/modules/slicer/enqueue.py`); render/api jobs use random uuids → `ref` stays null. Never a path (AC-9).
- Visual: the new `Kolejki` (Queues) tab rippled the 5 tab-bearing admin specs on the `desktop-light` project only (the suite filters admin specs off the other 3 projects). 14 stale baselines regenerated; triaged via `git status` — scope is exactly the tab-bearing admin pages + the 12 new admin-queues PNGs, nothing else. Confirmed visually that the only delta on rippled pages is the added tab.

### Completion Notes List

- **Backend** — new read-only `apps/api/app/modules/queue/` package: `constants.py` (SSOT pool table `arq:api`/`arq:queue`/`arq:slicer` + magic-constant declarations with contract-pointing docstrings), `schemas.py` (Pydantic v2 `extra="forbid"` allowlist DTOs), `service.py` (bounded `zcard` + `SCAN`, never `KEYS`; allowlist projection; tri-state liveness), `admin_router.py` (`GET /api/admin/queues`, `current_admin`-gated). Mounted in `app/router.py`. (AC-1..AC-13.)
- **Leak fence (load-bearing)** — DTO carries only allowlisted fields; `args`/`kwargs`/`result` are never projected. Tests assert no `args`/`kwargs`/`result` keys, no path-like substrings (`/`, drive letters, `..`), no secret-looking material, and `error_class` is the curated exception type name only. (AC-10/AC-11.)
- **Frontend** — `/admin/queues` admin tab + route (AuthGate discipline: defer to shell for anonymous, role-tier redirect only for authenticated-non-admin), `useAdminQueues()` hook (`["admin","queues"]`, `staleTime: 0`, focus-gated polling — `refetchInterval` returns false when `document.hidden`, `visibilitychange` re-arms on visible), `QueuesPage` with per-queue cards (queued/running headline + liveness chip w/ age+interval + counters, failed weighted), running-now strip, recent list with retention caveat + queue/outcome filters, and skeleton/empty/error+Retry fails-closed states. Status by icon+text+color, zero inline hex. (AC-14..AC-20.)
- **i18n** — 33 `modules.admin.queues.*` + `admin.tabs.queues` keys with full en/pl parity and Polish diacritics; queue ids + arq function names untranslated. (AC-21.)
- **Tests/gates run** (this session): backend focused `tests/test_admin_queues_snapshot.py` + `tests/test_route_enforcement_gate.py` 3× → 16 passed each; full backend `pytest` → 1623 passed, 3 skipped (no regressions); FE `QueuesPage.test.tsx` 3× → 10 passed each; full `vitest` → 617 passed; `npm run typecheck` clean; `npm run lint` clean (`--max-warnings=0`); `ruff format --check` + `ruff check` clean on touched Python; full Playwright visual suite → 410 passed, 24 skipped (exit 0). Determinism (AC-23) confirmed.
- **Scope discipline** — read-only `GET` only (no retry/kill/purge/pause/resume), no DB table/migration, no worker/`config.py`/`configs` change → SW-DEPLOY-1 NOT triggered. Reads exclusively via lifespan-owned `request.app.state.arq`; never an ad-hoc connection.
- **Deferred to controller** — commit/push/deploy (left dirty on the story branch per repo pattern). The pre-commit baseline gate needs a `baseline-reviewed: <basename>, Ezopek/Claude, 2026-06-06` line per changed PNG in the commit message (14 modified + 12 new admin-queues PNGs) — see the visual-baseline list below.

### Controller closeout (2026-06-06)

- **Visual-baseline correction (real blocker found + fixed).** The initial controller `infra/scripts/check-all.sh` run surfaced a genuine visual regression: only *some* of the AdminTabs-ripple baselines had been regenerated in the dev-story session, so the visual stage failed on **46 screenshots**. The controller corrected the mechanical gap by running `cd apps/web && npm run test:visual -- --update-snapshots`, regenerating **all** affected AdminTabs-ripple baselines across desktop/mobile × light/dark. (This widens the AdminTabs ripple beyond the desktop-light-only set the dev-story session had captured — the additional regenerated baselines are part of the controller's commit scope.)
- **Visual re-check green.** Controller reran `npm run test:visual` → **456 passed, 24 skipped**.
- **Full gate all-green.** Controller reran the full `infra/scripts/check-all.sh` after the baseline fix. Final log `/tmp/admin-jobs-check-all-2.log`: **`passed: 16`, `all green.`** (AC-23 determinism + full pre-push gate satisfied.)
- **Independent review — Gemini, APPROVE.** Gemini independent review (prompt `/tmp/3d-portal-admin-jobs-gemini-review.md`) returned **Critical: None / Important: None / Minor: None — Verdict: APPROVE.** Caveat: Gemini reported its shell tool was unavailable, so it reviewed the **current code** via its search/read tools rather than a `git diff`. Independent approval + all-green gates → story moved `review` → `done`.

### File List

**Added (backend):**
- `apps/api/app/modules/queue/__init__.py`
- `apps/api/app/modules/queue/constants.py`
- `apps/api/app/modules/queue/schemas.py`
- `apps/api/app/modules/queue/service.py`
- `apps/api/app/modules/queue/admin_router.py`
- `apps/api/tests/test_admin_queues_snapshot.py`

**Added (frontend):**
- `apps/web/src/modules/admin/QueuesPage.tsx`
- `apps/web/src/modules/admin/QueuesPage.test.tsx`
- `apps/web/src/modules/admin/hooks/useAdminQueues.ts`
- `apps/web/src/routes/admin/queues.tsx`
- `apps/web/tests/visual/admin-queues.spec.ts`
- `apps/web/tests/visual/__snapshots__/admin-queues.spec.ts/` (12 PNGs: populated/empty/error × desktop-light/dark, mobile-light/dark)

**Modified:**
- `apps/api/app/router.py` (mount `queue_admin_router`)
- `apps/web/src/modules/admin/AdminTabs.tsx` (`"queues"` tab + link)
- `apps/web/src/routes/admin/queues.tsx` route ripple → `apps/web/src/routeTree.gen.ts` (regenerated)
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` (`modules.admin.queues.*` + `admin.tabs.queues`)
- `apps/web/tests/visual/api-stubs.ts` (`stubAdminQueues`)
- `apps/web/tests/visual/__snapshots__/` — 14 stale baselines regenerated for the AdminTabs ripple (desktop-light): `admin-invites` (2), `admin-profile-library` (4), `admin-profile-offers` (4), `admin-profiles` (1), `admin-users` (3)
- `_bmad-output/implementation-artifacts/34-1-admin-queues-console.md` (this record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (status → review)

### Visual baseline sign-off (for the controller commit message — pre-commit baseline gate)

```
baseline-reviewed: queues-populated-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: queues-populated-desktop-dark, Ezopek, 2026-06-06
baseline-reviewed: queues-populated-mobile-light, Ezopek, 2026-06-06
baseline-reviewed: queues-populated-mobile-dark, Ezopek, 2026-06-06
baseline-reviewed: queues-empty-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: queues-empty-desktop-dark, Ezopek, 2026-06-06
baseline-reviewed: queues-empty-mobile-light, Ezopek, 2026-06-06
baseline-reviewed: queues-empty-mobile-dark, Ezopek, 2026-06-06
baseline-reviewed: queues-error-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: queues-error-desktop-dark, Ezopek, 2026-06-06
baseline-reviewed: queues-error-mobile-light, Ezopek, 2026-06-06
baseline-reviewed: queues-error-mobile-dark, Ezopek, 2026-06-06
baseline-reviewed: admin-invites-empty-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: admin-invites-mixed-status-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: library-detail-expanded-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: library-empty-upload-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: library-import-rejected-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: library-list-mixed-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: offers-compose-open-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: offers-create-rejected-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: offers-detail-expanded-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: offers-list-mixed-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: admin-profiles-mixed-status-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: admin-users-empty-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: admin-users-many-rows-desktop-light, Ezopek, 2026-06-06
baseline-reviewed: admin-users-one-row-desktop-light, Ezopek, 2026-06-06
```

### Change Log

| Date | Change |
|---|---|
| 2026-06-06 | bmad-dev-story: implemented Story 34.1 / ADMIN-JOBS-1 (read-only admin ARQ queue console). Backend `GET /api/admin/queues` (bounded `zcard`+`SCAN`, allowlist DTO, tri-state liveness, leak fence) + FE `/admin/queues` console (cards / running strip / recent list, focus-gated polling, fails-closed). 23 ACs satisfied; backend+FE focused tests 3× deterministic; full visual suite green (410 passed). Status → review. No commit/deploy (left dirty for controller). |
| 2026-06-06 | Controller closeout: initial `check-all.sh` caught a real visual regression — only some AdminTabs-ripple baselines were regenerated (46 screenshots failed). Controller fixed via `npm run test:visual -- --update-snapshots` (all affected AdminTabs-ripple baselines across desktop/mobile × light/dark); visual re-check `npm run test:visual` → 456 passed, 24 skipped. Full `infra/scripts/check-all.sh` rerun → `passed: 16`, `all green` (`/tmp/admin-jobs-check-all-2.log`). Gemini independent review (`/tmp/3d-portal-admin-jobs-gemini-review.md`): 0 Critical / 0 Important / 0 Minor — APPROVE (caveat: shell tool unavailable, reviewed current code not a git diff). Status review → done. |
