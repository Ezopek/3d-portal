---
title: 'SPOOL-EVT-1 — live Spoolman-change event source (poll-diff trigger)'
type: 'feature'
created: '2026-06-03'
status: 'in-review'
baseline_commit: '35360d65824029a84ca80e23dddd1471ddc8439e'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-spool-preq-1-spoolman-reverse-index.md'
  - '{project-root}/apps/api/app/modules/slicer/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Spoolman live-invalidation chain has every primitive but no trigger. Story 32.5
shipped `apply_spoolman_filament_change` (classify cost-only vs mapped-override + dispatch into
the Story 32.4 engine, given a single filament's old→new state + a caller-supplied
`affected_keys` set). SPOOL-PREQ-1 shipped the persisted reverse index +
`lookup_affected_keys(ref) → AffectedGroup[]`. What was still missing: nothing detects a real
Spoolman filament change across poll ticks and feeds those primitives. A real price edit or a
mapped-field edit on `.190` does not, today, invalidate/recompute dependent estimates on its own.

**Approach:** Extend the EXISTING Init 19 Spoolman poll (no second read). `SpoolsService` retains
the previous successful snapshot in an additive Redis key and, on each successful cron refresh,
hands `(previous, current)` to an injected, slicer-agnostic `SnapshotChangeHandler`. The slicer
side (`SpoolmanInvalidationHandler`) diffs filaments by the churn-stable `spoolman_filament_ref`,
classifies each changed ref, looks up the affected `(stl_hash, bundle_hash)` keys via SPOOL-PREQ-1,
and dispatches one `apply_spoolman_filament_change` per pinning intent.

## Boundaries & Constraints

**Always:**
- Use the EXISTING poll/refresh flow as the source — NO second Spoolman read (consume the snapshot
  the poll already fetched).
- Persist the previous successful snapshot in a NEW additive Redis key with a TTL safely greater
  than the 60s poll cadence (NOT the 30s public summary cache). Adding a key is additive — it does
  not alter the 31.x contract keys.
- Diff filaments by `spoolman_filament_ref` (the same churn-stable `vendor∥material∥name` key
  SPOOL-PREQ-1 indexes by). Classify only real changes via `classify_spoolman_delta`; a no-op /
  irrelevant change must not dispatch.
- For each changed ref, `lookup_affected_keys` then `apply_spoolman_filament_change` once per group
  (per pinning intent). The dispatch already guards cost-only (no enqueue) vs mapped (re-resolve +
  enqueue) and per-status writes.
- First poll after deploy warms the baseline and dispatches NOTHING.
- Keep `SpoolsService` slicer-agnostic — the change-notification seam is a generic Protocol; the
  diff/classify/dispatch lives in the slicer module; the cron is the composition root.
- Handler errors are isolated — never break the poll success path or the Redis lock release.

**Ask First:**
- Any need to add a second Spoolman poll, change `EstimateRecord`/`SpoolmanSnapshot` shape, thread
  the filament ref through the slice-job payload, or add an Alembic table — HALT.

**Never:**
- Catalog→`stl_hash` ingestion (EST-INGEST-1), `POST /api/estimates/recompute` (EST-RECOMPUTE-1),
  any UI, or a claim of automatic end-to-end catalog estimates beyond persisted/attributed keys.
- A second `bundle_hash → {stl_hash}` index — reuse `lookup_affected_keys` (SPOOL-PREQ-1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First poll after deploy | prev key absent | write baseline, NO handler call, NO dispatch | N/A |
| No-op diff | prev == current (or byte-identical filament) | classify None for every ref ⇒ no dispatch; baseline advanced | N/A |
| Irrelevant change | only `color_hex` differs | classify None ⇒ no dispatch | N/A |
| Cost-only change | `price`/`weight` differ, mapped fields equal | `spoolman_cost_only` ⇒ recompute cost in place, NO enqueue (R1 guard) | N/A |
| Mapped-override change | a `filament.extra` mapped field differs | re-resolve to new bundle_hash, mark OLD stale, enqueue NEW re-slice | resolve-fail ⇒ skip |
| Missing attribution | changed ref absent from the SPOOL-PREQ-1 index | `lookup_affected_keys → []` ⇒ no dispatch | N/A |
| Attribution, no estimates | pin known, no estimate for bundle | group with empty `affected_keys` ⇒ skip (no enqueue, no wasted re-resolve) | N/A |
| Added ref | ref only in current | no prior state ⇒ no dispatch | N/A |
| Removed ref | ref only in previous | not iterated ⇒ no dispatch (orphan cleanup out of scope) | N/A |
| Handler raises | handler throws mid-diff | poll still succeeds (cache written), baseline NOT advanced (re-diff next tick), warning logged | swallow + log |
| Request-path refresh | `get_summary` cold-cache fallback | refresh WITHOUT handler ⇒ no dispatch, no baseline write | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/app/modules/slicer/spoolman_event_source.py` — NEW. `SpoolmanInvalidationHandler`
  (diff → classify-gate → `lookup_affected_keys` → `apply_spoolman_filament_change`) +
  `build_spoolman_invalidation_handler` (settings-wired composition root).
- `apps/api/app/modules/spools/service.py` — add `SnapshotChangeHandler` Protocol, the additive
  `spools:summary:prev:v1` key (+ TTL), the optional `change_handler` param on `refresh_summary`,
  and `_handle_snapshot_change` (warmup + at-least-once dispatch + isolated errors).
- `apps/api/app/workers/spoolman_poll.py` — build the handler with `_ctx["redis"]` and pass it as
  `change_handler`.
- `apps/api/app/modules/slicer/spoolman_invalidation.py` — REUSE `apply_spoolman_filament_change` /
  `classify_spoolman_delta` (no change).
- `apps/api/app/modules/slicer/attribution_store.py` — REUSE `lookup_affected_keys` (no change).
- `apps/api/tests/test_slicer_spoolman_event_source.py` — NEW. 13 tests (handler + service + cron).
- `_bmad-output/implementation-artifacts/deferred-work.md` — UPDATE SPOOL-EVT-1 → IMPLEMENTED.

## Tasks & Acceptance

**Execution:**
- [x] `spoolman_event_source.py` — handler + builder.
- [x] `service.py` — Protocol + prev-snapshot retention + `change_handler` seam + warmup + isolation.
- [x] `spoolman_poll.py` — wire the handler onto the existing cron (no second read).
- [x] `test_slicer_spoolman_event_source.py` — 13 tests.
- [x] `deferred-work.md` — SPOOL-EVT-1 marked IMPLEMENTED with deploy caveat.

**Acceptance Criteria:**
- Given a first successful poll after deploy, when the cron refresh runs, then the previous-snapshot
  baseline is warmed and NO invalidation is dispatched.
- Given two successive snapshots that differ only in a price/weight field for a ref with persisted
  attribution + estimate, when the poll runs, then exactly one cost-only recompute happens in place
  and NO re-slice is enqueued.
- Given a mapped-field (`filament.extra`) change for an attributed ref, when the poll runs, then the
  OLD estimate is marked stale and a re-slice is enqueued against the re-resolved bundle hash.
- Given a changed ref with no attribution (or no computed estimate), when the poll runs, then nothing
  is dispatched.
- Given a handler that raises, when the poll runs, then the poll still succeeds and the baseline is
  not advanced (the delta re-diffs next tick).
- Given a request-path cold-cache refresh, when `get_summary` falls back, then no dispatch and no
  baseline write occur.

## Verification

**Commands:**
- `cd apps/api && uv run pytest tests/test_slicer_spoolman_event_source.py -q` — all new tests pass.
- `cd apps/api && uv run pytest tests/test_spools.py tests/test_spools_routes.py tests/test_slicer_spoolman_overrides.py tests/test_slicer_attribution.py tests/test_slicer_estimate.py tests/test_estimate_api.py -q` — green (no regression).
- `cd apps/api && uv run ruff format --check . && uv run ruff check .` — clean.
- `git diff --check` — no whitespace errors.
- `cd apps/api && uv run pytest -q` — full backend suite green.

## Design Notes

- **At-least-once + idempotent.** The baseline advances only after a clean handler run, so a transient
  handler crash re-diffs the same delta next tick rather than dropping it. Safe because the downstream
  is idempotent: `mark_stale` is idempotent, the re-slice enqueue is `_job_id`-deduped (32.4), and
  cost-only recompute is in-place arithmetic.
- **Churn-stable ref is load-bearing.** name/vendor/material edits re-key the ref → surface as
  removed+added (no correlatable old→new) and are intentionally not dispatched. price/weight/extra
  edits keep the ref stable and are exactly what the diff catches. This inherits SPOOL-PREQ-1-D1
  (blank-field ref degeneracy), still parked upstream in `overrides.spoolman_filament_ref`.
- **Bounded by attribution.** End-to-end "Spoolman change auto-updates estimates" works only for keys
  resolved+persisted through the SPOOL-PREQ-1 index. Auto-deriving estimates for never-sliced catalog
  parts needs EST-INGEST-1 (out of scope). A missing/uncomputed attribution is a no-dispatch by design.
- **Deploy:** the cron runs in the api-arq-worker; the mapped path re-resolves there (bundle-store
  write + vendored-profiles read) and enqueues onto `arq:slicer`. No NEW slicer-worker module is
  introduced (the event source runs api-side), but the SW-DEPLOY-1 overlay rebuild + smoke still
  applies on any `portal-api` bump.
