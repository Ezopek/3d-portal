---
baseline_commit: 179c08de4588bb19facbe9e341644b456b7309d2
---

# Story 32.4: Estimate invalidation / recompute engine — stale transitions + idempotent recompute enqueue + cost-only arithmetic recompute (no re-slice)

Status: ready-for-dev

## Story

As a **portal backend that now persists a typed, cost-carrying `EstimateRecord` keyed `(stl_hash, bundle_hash)` (Story 32.3) but has no way to invalidate one when an input changes, no way to recompute one without re-slicing, and no explicit way to serve a known-superseded estimate as `stale` rather than silently as `fresh`**,
I want **an invalidation / recompute engine over the existing `EstimateStore` that (a) transitions a `fresh` record to `stale` — preserving its last-known numerics so it stays *servable* — and to `queued` when a re-slice is enqueued; (b) enqueues a recompute against the dedicated slicer queue *idempotently* (riding the Story 32.2 `_job_id` dedupe so a duplicate trigger while one recompute is in flight is a no-op); and (c) — the load-bearing efficiency rule — recomputes a `filament_cost` field *arithmetically* (`cost = filament_g × price_per_gram`) directly in the store, with NO Orca re-slice and NO slicer-worker job, in well under a second**,
so that **the exhaustive Decision AJ recompute-trigger table is realized in code (STL content change / bundle re-tune / Orca upgrade / Spoolman mapped-override → stale + idempotent re-slice; Spoolman cost-only price change → cheap in-place arithmetic), a Spoolman price tick can NEVER trigger a minutes-long re-slice storm (the Pre-Mortem R1 top self-inflicted-DoS risk; NFR20-REPRODUCIBLE-1 / NFR20-RESOURCE-1), a superseded estimate is served with an explicit `stale` flag instead of vanishing or masquerading as fresh (FR20-CACHE-1 / FR20-FAILURE-1), the no-silent-zero / failed-vs-fresh invariants Story 32.3 locked down are preserved through every transition, and Story 32.5 (Spoolman mapped-override + cost-only price-change wiring) and Story 32.6 (FE stale/soft-fail display) have the engine + the explicit served-status contract they consume**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AJ) + § 4.3 (Epic E32 story sketch — Story 32.4 "invalidation / recompute queue / cost arithmetic").
Architectural anchor: Decision **AJ** (cache / invalidation / cost arithmetic) per `architecture.md` § Initiative 20 — specifically the **recompute-trigger table** (exhaustive-by-design, closes risk R9 "cache key incomplete → stale served as fresh") and the **cost-only-arithmetic rule** (OD-7, load-bearing efficiency decision). Story 32.3 (Decision AJ first half) supplies the persisted `EstimateRecord` + `EstimateStore` this story transitions; Story 32.1 (Decision AH) supplies the `bundle_hash`; Story 32.2 (Decision AI) supplies the slice-job + the `_job_id` dedupe + the dedicated `arq:slicer` queue this story re-enqueues onto.
Realizes **FR20-CACHE-1** (the `stale`/`queued` *transitions* + recompute dedup Story 32.3 explicitly deferred here) + **NFR20-REPRODUCIBLE-1** (hash-driven invalidation on STL / bundle / Orca / mapped-override change + the cost-only-arithmetic-without-re-slice rule, verified by a pytest proving a cost-only change recomputes cost without invoking the slicer worker, in <1s) + **NFR20-RESOURCE-1** (the cost-only-arithmetic + recompute dedup that, with the Story 32.2 concurrency cap, prevents a recompute-storm CPU DoS). Touches **FR20-FAILURE-1** (the explicit `stale` served-flag contract — never a silent hide, never a stale-served-as-fresh).
OD-gate context: authored after the **2026-05-31 OD-gate resolution** — **OD-7 RESOLVED (arithmetic recompute only)**: a cost-only change recomputes the cost field arithmetically (`cost = mass × price/gram`) and NEVER triggers a re-slice (`prd.md` § Initiative 20 § Open decisions). Per the PRD § Open-decisions note, Stories 32.2–32.6 are authored individually by `bmad-create-story` at their own dev-entry time; **this is Story 32.4's dev-entry authoring**. Authoring this spec to `ready-for-dev` does NOT itself start `bmad-dev-story` — execution remains controller-routed (ITCM autonomous mode). Like Story 32.3 (and unlike Story 32.2) there is **no external configs-side coordination gate** for the *spec*: 32.4 is pure app-side (a recompute engine + `EstimateStore` transition methods + a thin recompute-enqueue helper). See the **Runtime / deploy verification (SW-DEPLOY-1)** Dev Note for the deploy-time caveat that applies because 32.4 lands code under `app.modules.slicer.*`.
**Codex tag (recommended `gpt-5.5`; controller confirms — route per `[[feedback_codex_model_routing]]`):** this story is **single-adjacency: data-integrity** (same class as Story 32.3, NOT runtime-boundary, NOT auth-boundary). The risk surface is: a wrong stale/fresh transition that serves an out-of-date estimate as `fresh` (R9), a cost-only path that accidentally re-slices (R1 self-DoS) or that writes a `0`/`nan`/negative cost (silent-zero / poisoned-arithmetic), a non-idempotent recompute enqueue that double-runs an expensive slice, or a transition that violates the Story 32.3 failed/fresh invariants. **No HTTP surface** (zero routes — the estimate read API is Story 32.6, AC-9). **No subprocess / no real Orca** in the cost-only path (pure arithmetic + a local file write); the re-slice path *enqueues* onto the existing Story 32.2 worker but does not itself spawn Orca.

## Acceptance Criteria

### AC-1 — `EstimateStore` stale transition: `fresh → stale` preserving last-known numerics (servable, never hidden)

Extend `apps/api/app/modules/slicer/estimate_store.py` (Story 32.3's store — one module, no new store file) with an explicit transition that supersedes a record WITHOUT discarding its numbers:

- New `EstimateStore.mark_stale(stl_hash, bundle_hash) -> EstimateRecord | None`:
  - On an existing `fresh` record → write a copy with `status = stale`, **preserving every numeric field** (`time_seconds` / `filament_g` / `filament_mm` / `filament_cm3` / `filament_cost`), `settings_ids`, `warnings`, `orca_version`, and the **original `computed_at`** (the stale record still describes *when it was last validly computed* — the FR20-FAILURE-1 "Last estimated HH:MM" provenance Story 32.6 renders). Return the updated record.
  - **Idempotent:** an already-`stale` (or `queued`) record → no-op, return the existing record unchanged (no `computed_at` churn).
  - A `failed` record → **no-op** (a failed record has no valid estimate to go stale; it stays `failed` and a clean re-slice replaces it via the Story 32.3 `write` failed⇒fresh path). Return the existing `failed` record.
  - A cache miss → return `None` (never fabricate a record to mark stale).
- The transition write **bypasses the Story 32.3 `write()` `fresh`-no-op dedup** (which exists to make a *re-compute of the same fresh content* idempotent) — `mark_stale` is a deliberate *status change*, not a content re-write. Implement it via a force-publish path under the **same per-record `_record_lock`** so it is race-safe against a concurrent slice persist (reuse `_record_lock` + `_atomic_publish`; do NOT re-author the locking/atomic-write discipline).
- **Explicit-stale contract:** a `stale` record is **served**, not hidden — `EstimateStore.read` returns it exactly as stored (Story 32.3 already returns whatever is persisted; AC-9 forbids any read-side coercion of `stale → fresh` or any drop of a stale record's numerics). Story 32.6 reads `status` and renders the "may be out of date, recomputing" flag.

**Tests (red→green):** `test_mark_stale_fresh_preserves_numerics_and_computed_at`; `test_mark_stale_is_idempotent_on_already_stale`; `test_mark_stale_on_failed_record_is_noop_stays_failed`; `test_mark_stale_on_miss_returns_none`; `test_stale_record_is_returned_by_read_not_hidden`.

### AC-2 — `EstimateStore` queued transition: `stale|fresh → queued` (recompute in flight)

- New `EstimateStore.mark_queued(stl_hash, bundle_hash) -> EstimateRecord | None`:
  - Transitions a `fresh` or `stale` record to `status = queued`, again **preserving the last-known numerics + original `computed_at`** (a `queued` record is still servable — the UI shows the last estimate while the recompute runs). Idempotent on an already-`queued` record.
  - A `failed` record → no-op (a failed key with no valid estimate is re-sliced via the normal enqueue, not "queued over a good number"); a miss → `None`.
  - The `stale → queued → (recompute) → fresh` lifecycle from the Decision AJ table: `mark_stale` is the *invalidation* edge, `mark_queued` is the *enqueued-recompute* edge, and the Story 32.2 worker's `slice_estimate` persist (Story 32.3 `write`, failed/stale/queued ⇒ replace) is the *fresh* terminus.
- Same force-publish-under-`_record_lock` discipline as AC-1.

**Tests (red→green):** `test_mark_queued_from_stale_preserves_numerics`; `test_mark_queued_from_fresh_preserves_numerics`; `test_mark_queued_idempotent`; `test_mark_queued_on_failed_is_noop`; `test_mark_queued_on_miss_returns_none`.

### AC-3 — Cost-only arithmetic recompute: `cost = filament_g × price_per_gram`, in-place, NO re-slice (OD-7, NFR20-REPRODUCIBLE-1 — the load-bearing rule)

New `apps/api/app/modules/slicer/recompute.py` — `recompute_cost_only(store, stl_hash, bundle_hash, *, price_per_gram) -> EstimateRecord | None`:

- Reads the record for the key; on a `fresh` (or `stale`/`queued` — a servable record carrying `filament_g`) record, computes `new_cost = filament_g * price_per_gram` and writes the record back **with `filament_cost = new_cost` updated and `computed_at` re-stamped, every other field (including `status`, the slice-derived numerics, `settings_ids`, `warnings`) unchanged**. The status is **NOT** changed to `stale`/`queued` — a cost-only change does NOT invalidate the *slice output*, so the record stays the status it was (a `fresh` record stays `fresh`).
- **NO arq job is enqueued; NO slicer worker is invoked; NO Orca subprocess is spawned.** This is the entire point of OD-7: cost is derived post-slice arithmetic, never a slice input (architecture.md § Decision AJ cost-only-arithmetic rule). The function touches only the `EstimateStore` (one read + one atomic write).
- **No-silent-zero / poisoned-arithmetic guards** (the data-integrity contract):
  - `price_per_gram` MUST be a finite, non-negative `float`; a `None` / `nan` / `inf` / negative value → raise `ValueError` (a `ValueError` from the caller's bad input is correct — it must NOT silently write `cost = 0`, `nan`, or a negative cost). The Story 32.3 `EstimateRecord._reject_non_finite` field-validator is the defense-in-depth backstop at the model edge.
  - A record whose `filament_g` is `None` (only possible on a `failed` record, which the AC-3 path excludes) or a `failed` record → **no-op, return `None`** (a failed estimate has no mass to multiply; never fabricate a cost onto a failure).
  - A cache miss → `None` (never write a cost onto a key with no estimate).
- The in-place fresh→fresh update **bypasses the Story 32.3 `write()` fresh-no-op** (it IS a deliberate content change to the cost field) — express it via a force-publish under `_record_lock` (an `EstimateStore` method, e.g. `update_cost`, that AC-3 calls), reusing AC-1's force-publish path. The original slice-derived numerics are immutable through this path; ONLY `filament_cost` + `computed_at` change.

**Tests (red→green):** `test_cost_only_recompute_updates_cost_from_mass_and_price`; `test_cost_only_recompute_does_not_enqueue_any_slice` (assert a spy `arq_pool` / the worker enqueue is NEVER called — the R1-DoS guard); `test_cost_only_recompute_does_not_spawn_subprocess` (no `subprocess`/Orca); `test_cost_only_recompute_preserves_slice_numerics_and_status` (time/g/mm/cm3 + `status=fresh` unchanged; only cost + `computed_at` change); `test_cost_only_recompute_rejects_non_finite_price` (parametrized `None`/`nan`/`inf`); `test_cost_only_recompute_rejects_negative_price`; `test_cost_only_recompute_on_failed_record_is_noop_none`; `test_cost_only_recompute_on_miss_returns_none`; `test_cost_only_recompute_completes_well_under_one_second` (a loose wall-time assertion proving the path is arithmetic, not a slice — NFR20-REPRODUCIBLE-1's <1s contract; assert ≪1s, e.g. < 0.5s, to leave CI headroom).

### AC-4 — Idempotent recompute enqueue (re-slice path), riding the Story 32.2 `_job_id` dedupe

New `enqueue_recompute(arq_pool, *, stl_hash, bundle_hash) -> ...` (in `recompute.py`, or a thin extension of `enqueue.py` — reuse, do NOT duplicate the enqueue plumbing):

- Enqueues a `slice_estimate` job for the **already-cached** `(stl_hash, bundle_hash)` onto the dedicated `arq:slicer` queue with the deterministic `_job_id = slice_job_id(stl_hash, bundle_hash)` (`= "slice:<stl>:<bundle>"`) so a duplicate recompute trigger while one is queued/running is an **arq de-dup no-op** (NFR20-RESOURCE-1 / Decision AI § Concurrency). **Reuse the existing `slice_job_id`, `SLICE_JOB_NAME`, `SLICER_QUEUE_NAME`** from `enqueue.py` / `worker.py` / `worker_job.py` — do NOT re-derive the job-id shape or the queue name.
- **Difference from `enqueue_slice_estimate` (Story 32.2):** the Story 32.2 helper takes a `source_stl: Path` and calls `stl_cache.populate_from_source(...)` because it is the *first* enqueue (the STL may not be cached yet). A **recompute** is by definition a re-run for a key whose STL is already content-addressed in the cache (a bundle re-tune / Orca upgrade / mapped-override change does NOT change `stl_hash`), so `enqueue_recompute` enqueues **by hash directly** — no `source_stl`, no re-population. If the STL is somehow absent from the cache the worker classifies a typed `missing_stl` `SliceOutcome` (Story 32.2) — a typed failure, never a silent zero; document this as the deliberate boundary.
- The enqueue does NOT itself write the estimate record — the worker's `slice_estimate` persist (Story 32.3) owns the fresh terminus. `enqueue_recompute` only pushes the deduped job.

**Tests (red→green):** `test_enqueue_recompute_uses_deterministic_job_id` (`_job_id == "slice:<stl>:<bundle>"`); `test_enqueue_recompute_targets_slicer_queue` (`_queue_name == SLICER_QUEUE_NAME`); `test_enqueue_recompute_is_idempotent_dedupe` (two enqueues for the same key → the same `_job_id`, asserting the de-dup contract — a fake `arq_pool` records the `_job_id`/`_queue_name` kwargs); `test_enqueue_recompute_does_not_repopulate_stl_cache` (no `populate_from_source` call — it is a by-hash re-run).

### AC-5 — Recompute-trigger dispatch: the Decision AJ table realized in code (cheap arithmetic path vs. stale+re-slice path)

New `recompute.py` typed dispatch realizing the **exhaustive** Decision AJ recompute-trigger table — every trigger routes to exactly one of the two recompute paths, so the table cannot grow a silent gap (R9):

- `RecomputeTrigger` (`StrEnum`) with the table's trigger kinds — at minimum: `stl_content_change`, `bundle_retune`, `orca_upgrade`, `spoolman_mapped_override`, `spoolman_cost_only`. Each value carries (in the docstring / an inline `because` comment) the table row it implements.
- A dispatch function `invalidate(store, arq_pool, *, trigger, stl_hash, bundle_hash, price_per_gram=None) -> EstimateRecord | None` (signature shaped to the two paths — name the params to the contract):
  - **`spoolman_cost_only`** → the **cheap arithmetic path** (AC-3): `recompute_cost_only(...)` with the supplied `price_per_gram`; **NO** `mark_stale`, **NO** enqueue. (`price_per_gram` is REQUIRED for this trigger; a missing one is a `ValueError`, not a silent skip.)
  - **`bundle_retune` / `orca_upgrade` / `spoolman_mapped_override`** → the **stale + idempotent re-slice path**: `mark_stale(stl_hash, bundle_hash)` → `enqueue_recompute(arq_pool, stl_hash=..., bundle_hash=...)` → `mark_queued(stl_hash, bundle_hash)` (the `stale → queued` lifecycle). For a `bundle_retune` / `spoolman_mapped_override`, the *new* `bundle_hash` is the re-slice target and the *old* record is marked stale — name which hash is which in the function contract (the old→new bundle mapping itself is computed by Story 32.1 resolve / Story 32.5 Spoolman linkage and is **passed in**, not derived here — see AC-7 scope fence).
  - **`stl_content_change`** → documented as **handled by content-addressing** (a new `stl_hash` is a new key ⇒ a natural cache miss ⇒ a normal first enqueue via the Story 32.2 `enqueue_slice_estimate`; the old key is orphaned for a future GC). 32.4 does NOT implement orphan GC (explicit out-of-scope, AC-9); the dispatch documents this trigger as "no in-place transition — new key, new estimate" so the table stays exhaustive without bolting on GC.
- The dispatch is the single chokepoint that decides "cheap arithmetic vs. expensive re-slice"; it is where the R1 self-DoS guard lives (a `spoolman_cost_only` trigger can NEVER reach the enqueue path).

**Tests (red→green):** `test_dispatch_cost_only_takes_arithmetic_path_no_enqueue`; `test_dispatch_cost_only_without_price_raises`; `test_dispatch_bundle_retune_marks_stale_then_enqueues_then_queued`; `test_dispatch_orca_upgrade_marks_stale_and_enqueues`; `test_dispatch_mapped_override_marks_stale_and_enqueues`; `test_recompute_trigger_enum_covers_decision_aj_table` (assert every architecture-table row has a `RecomputeTrigger` value — the exhaustiveness guard against R9).

### AC-6 — Bulk recompute primitives for the enumerable triggers (Orca upgrade / bundle re-tune fan-out), reusing the Story 32.3 store layout

The Decision AJ table has two *bulk* triggers — an Orca upgrade ("all estimates effectively stale; bulk recompute") and a bundle re-tune ("the sibling estimates a bundle re-tune invalidates"). Story 32.3 chose the `<root>/estimates/<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json` layout **specifically so 32.4 can enumerate without a full scan** — realize that:

- `EstimateStore.iter_stl_estimates(stl_hash) -> Iterator[EstimateRecord]` — yields every persisted bundle-variant estimate under one `<stl_hash>/` dir (the sibling set a bundle re-tune touches). Path-safe (the `stl_hash` is `validate_content_hash`-gated before any path is built — reuse the gate). A miss / empty dir yields nothing (never raises).
- `EstimateStore.iter_all_estimates() -> Iterator[EstimateRecord]` — walks the whole `estimates/` subtree (the Orca-upgrade bulk set). Skips the lock/`.tmp` sidecars (only `*.json` records). Used by the Orca-upgrade bulk path; **`log()` / document the count** so a bulk invalidation is observable (NFR20-OBS-1) and never silently truncated.
- A bulk helper `recompute_cost_only_bulk(store, keys, *, price_per_gram)` and/or a `invalidate_bulk(store, arq_pool, *, trigger, keys)` that iterates the per-key primitives (AC-3/AC-5) over a supplied key set. **The *which-keys* decision is the caller's** (Story 32.5 maps a Spoolman filament → the affected bundles; an Orca-upgrade ops trigger supplies "all"); 32.4 supplies the iteration mechanism + the per-key correctness, not the event source (AC-7).

**Tests (red→green):** `test_iter_stl_estimates_yields_all_bundle_variants_for_one_stl`; `test_iter_stl_estimates_ignores_lock_and_tmp_sidecars`; `test_iter_stl_estimates_on_missing_stl_yields_nothing`; `test_iter_all_estimates_walks_full_subtree`; `test_bulk_cost_recompute_applies_to_each_key_no_enqueue`; `test_bulk_invalidate_marks_each_stale_and_enqueues_each` (dedupe still per-key).

### AC-7 — Scope coordination with Story 32.5 (Spoolman) — engine here, event-wiring there

32.4 ships the recompute *engine* and the *primitives*; it does NOT implement the Spoolman mapping or read Spoolman:

- `recompute_cost_only` / `invalidate(trigger=spoolman_cost_only)` take `price_per_gram` as a **caller-supplied `float`** — 32.4 does NOT read Spoolman, does NOT compute `price_per_gram = filament.price / filament.weight`, does NOT resolve a `spool.price` override. That derivation is Story 32.5 / Init 19 Spoolman-client territory (the Spoolman filament `price`/`weight` fields live in `apps/api/app/modules/spools/models.py`). Document the input contract: *grams × (currency per gram) = currency*; the caller owns currency/units.
- `invalidate(trigger=bundle_retune | spoolman_mapped_override)` take the **new** `bundle_hash` as a caller-supplied input — 32.4 does NOT compute the new `bundle_hash`, does NOT map `filament.extra` onto the filament JSON, does NOT compute `spoolman_overrides_ref`. That is Story 32.5 (which folds `spoolman_overrides_ref` into `bundle_hash`, producing the new hash 32.4 invalidates against — the trigger 32.5's spec says "consumed by 32-4").
- 32.4 does NOT wire any live event source (no Spoolman-poll hook, no config-reload Orca-version-change detector). The dispatch functions are the seam Story 32.5 (and a future ops trigger) call; 32.4 proves them correct under unit tests with injected fakes. Name this boundary in the module docstring so 32.5 extends the wiring, not the engine.

**Tests (red→green):** `test_recompute_does_not_import_or_read_spools_module` (the engine takes `price_per_gram`/`bundle_hash` as inputs — assert no `app.modules.spools` import in `recompute.py`); `test_cost_only_input_is_price_per_gram_not_spoolman_entity` (the function signature carries a scalar, not a Spoolman record).

### AC-8 — Observability per the logging contract (NFR20-OBS-1); no g-code, no full record dumps

Reuse the Story 32.2/32.3 instrumentation pattern (`_emit_*` structured `labels.*` line + OTel span + GlitchTip breadcrumb):

- One structured line per transition / recompute, carrying `stl_hash`, `bundle_hash`, the trigger kind, and the resulting `estimate_status` (`stale`/`queued`/`fresh`). The cost-only path additionally tags that it took the **arithmetic** path (so a dashboard can confirm cost ticks never hit the slicer queue — the R1 guard is observable). A bulk path emits the **count** of records touched (never silently truncated).
- The recompute path emits NO g-code (there is none in the cost-only path; the re-slice path's g-code is the worker's parse-and-discard, Story 32.2/32.3) and does NOT dump the full `EstimateRecord` JSON into a log line — only the hashes / status / trigger / count.
- OTel span on the cost-only recompute (`slicer.recompute` or similar) mirroring the Story 32.3 `slicer.estimate` span attributes (`slicer.{stl_hash,bundle_hash,estimate_status}` + the trigger); no estimate *numbers* need go into span attributes beyond status.

**Tests (red→green):** `test_cost_only_recompute_emits_arithmetic_path_tag`; `test_invalidate_emits_trigger_and_status_tags`; `test_bulk_invalidate_emits_count`; `test_recompute_never_logs_full_record_or_gcode`.

### AC-9 — Scope fence: recompute engine only; explicit dev-story boundaries

- **Zero** changes under `apps/web/` (the `stale`/`queued`/soft-fail/"Last estimated HH:MM" display is Story 32.6).
- **Zero** new route mounting: `apps/api/app/main.py` (`_PUBLIC_ROUTES`) + `apps/api/app/router.py` byte-identical to pre-story state (grep/diff invariant). This story exposes **no HTTP surface** — the estimate read/recompute-trigger API is Story 32.6 / a future ops endpoint. (Per the task scope: "no route work unless existing API boundary requires it" — no estimate API boundary exists yet, so none is added.)
- **Zero** Alembic migration: the estimate cache is the Story 32.3 **append-only file store**, NOT a table; transitions are atomic file rewrites. No new file under `apps/api/migrations/versions/`. (No DB ⇒ no migration is "truly needed".)
- **No `SliceOutcome` / slice-orchestration reshape** (Story 32.2 contract): `SliceStatus`/`SliceFailureReason`/`SliceOutcome` field sets unchanged; `_classify`/`run_slice_job`/`slice_estimate` in `worker_job.py` **byte-identical** (32.4 enqueues onto the existing worker; it does NOT change what the worker does). `worker.py` `SlicerWorkerSettings` unchanged (no new arq function — the cost-only path is synchronous, not a worker job).
- **No `EstimateRecord` shape change** beyond what already exists: the `stale`/`queued` enum values already exist (Story 32.3 AC-1); 32.4 SETS them but does NOT add fields. (If a transition needs a new field — e.g. a `superseded_by` pointer — STOP and surface it; the default design needs none.)
- **No Spoolman read / no `filament.extra` mapping / no `spoolman_overrides_ref` computation** (Story 32.5) — AC-7.
- **No orphan-record GC**: a `stl_content_change` orphans the old `stl_hash` dir; reaping it is a future maintenance concern, explicitly deferred (documented in the dispatch, AC-5). 32.4 does not delete records.
- **No new config slot / no new magic constant**: staleness here is **event-driven** (a trigger fires), NOT time-based — there is **no TTL / staleness-age / recompute-budget constant** to add (per `[[feedback_scp_pre_enumeration_phase]]` § C; the `<1s` cost-only figure is a *performance contract* asserted in a test, not a literal baked into code). The Story 32.6 "Xm ago" display derives age from `computed_at` at render time — not a backend constant. If a reviewer finds a bare magic number, it is a P1 fix-up.
- **No raw g-code retention**: the cost-only path never touches g-code; the re-slice path rides the unchanged Story 32.2/32.3 parse-and-discard.
- **No new heavy Python dependency** in `apps/api/pyproject.toml`: arithmetic is stdlib; the store transitions reuse `fcntl`/`os`/`tempfile`/`pathlib`/`json` already imported by `estimate_store.py`.

**Tests/grep:** `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` returns zero lines; no new `apps/api/migrations/versions/` file; `apps/api/pyproject.toml` dependency block unchanged; the `SliceOutcome`/`_classify`/`run_slice_job`/`slice_estimate`-unchanged assertions; `apps/api/app/core/config.py` Settings field set unchanged (no new slicer slot).

### AC-10 — NFR20-CONTAINER-1 grep invariant + drift gate stays green

- **Grep invariant (NFR20-CONTAINER-1):** `grep -rniE "/mnt/c|fenrir|\.exe|[Ww]indows" apps/api/app/modules/slicer/` returns **ZERO** path/exe literal matches (the new `recompute.py` included).
- Because 32.4 adds **no** config slot (AC-9), `infra/scripts/check-settings-env-compose.py` must stay at the Story 32.3 alignment (50/48/38) **unchanged** — run it as a regression guard, not as a thing to bump.

**Tests (red→green):** extend `test_no_bench_or_windows_path_literal_in_*` to cover `recompute.py`; run `infra/scripts/check-settings-env-compose.py` → OK (unchanged counts).

### AC-11 — Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

This story is, by design (AC-9), **constant-free** for time/size/count: staleness is event-driven, not TTL'd; there is no recompute budget, no batch size, no retry count. The two reused literals carry their contract by reuse:

| Literal | Location | Contract pointed to |
|---|---|---|
| `_job_id` shape `"slice:<stl>:<bundle>"` | reused from `enqueue.slice_job_id` | because **"the idempotent dedupe key is the complete `(stl_hash, bundle_hash)` reproducibility tuple — Decision AI § Concurrency / NFR20-RESOURCE-1; reused verbatim from Story 32.2 so a recompute and a first-slice for the same key collide into one job"** |
| `cost = filament_g * price_per_gram` | `recompute.py` | because **"OD-7 / Decision AJ cost-only-arithmetic rule — cost is derived post-slice arithmetic (mass × price/gram), never a slice input; the formula IS the contract, and re-slicing for a price change is the R1 self-DoS this rule forbids"** |

If a reviewer finds any **arbitrary** TTL / staleness-age / budget / batch constant introduced by this story, it is a P1 fix-up (AC-9 says there should be none).

### AC-12 — Determinism gate (NFR20-DETERMINISM-1)

After this story lands, three consecutive `pytest apps/api/tests/test_slicer*.py -v` runs return identical pass counts (no flakes). The recompute engine is deterministic by construction (arithmetic + file transitions; no clock in the *decision* path — `computed_at` is the only non-deterministic field, re-stamped via the Story 32.3 `_now_iso`/equivalent and excluded from every assertion); the cost-only update is idempotent given the same `(record, price_per_gram)`; the enqueue is idempotent on `_job_id` (AC-4). Concurrent transitions are serialized by the per-record `_record_lock` (AC-1). Coverage: T-DET (including a concurrency test mirroring the Story 32.3 `test_concurrent_fresh_write_does_not_overwrite_existing_fresh` for the new transition path).

### AC-13 — Quality gate green (TDD evidence)

`ruff format --check` + `ruff check` clean on `apps/api/`; full backend `pytest -q` green (baseline + the new recompute cases); `git diff --check` clean; the AC-9 diff/grep invariants and the AC-10 grep + drift gate green. No vitest/Playwright (backend-only story). All assertions are evidence-backed command output in the Dev Agent Record (AGENTS.md § Execution discipline — no "should pass").

## Tasks / Subtasks

> **TDD discipline (AGENTS.md § Execution discipline):** every logic-bearing task writes the failing test FIRST (red), then implements to green, then refactors. There is **no subprocess and no real Orca in this story** — the cost-only path is pure arithmetic + a file write, and the re-slice path is asserted via a fake `arq_pool` (the real worker is Story 32.2, already done). The whole suite runs deterministically in CI with no env gate.

- [ ] **T1** (AC-1, AC-2) — `EstimateStore` stale/queued transitions *(red→green)*
  - [ ] T1.1 Failing tests: `mark_stale` fresh⇒stale preserves numerics + original `computed_at`; idempotent on stale/queued; no-op on failed; `None` on miss; `read` still returns a stale record (not hidden). Same matrix for `mark_queued` (from fresh + from stale).
  - [ ] T1.2 Implement `mark_stale` / `mark_queued` on `estimate_store.py` via a shared **force-publish-under-`_record_lock`** helper (reuse `_record_lock` + `_atomic_publish`; do NOT re-author them). A transition reads the existing record, constructs the status-changed copy preserving numerics/`computed_at`, and force-publishes (bypassing the `write()` fresh-no-op deliberately, with an in-code `because` comment).
- [ ] **T2** (AC-3) — Cost-only arithmetic recompute *(red→green)*
  - [ ] T2.1 Failing tests: cost updated from mass × price; **no enqueue / no subprocess**; slice numerics + status preserved; reject non-finite + negative price; no-op `None` on failed / miss; completes ≪1s.
  - [ ] T2.2 Implement `recompute.py::recompute_cost_only` + the `EstimateStore.update_cost` force-publish path (reuses T1.2's helper). Guard `price_per_gram` finite + non-negative BEFORE any write (raise `ValueError`); `filament_g` absent / failed / miss ⇒ `None`. ONLY `filament_cost` + `computed_at` change. AC-11 `because` comment on the formula.
- [ ] **T3** (AC-4) — Idempotent recompute enqueue *(red→green)*
  - [ ] T3.1 Failing tests (fake `arq_pool` recording `enqueue_job` kwargs): `_job_id == "slice:<stl>:<bundle>"`; `_queue_name == SLICER_QUEUE_NAME`; dedupe (two calls → same `_job_id`); no `populate_from_source` (by-hash re-run).
  - [ ] T3.2 Implement `enqueue_recompute` reusing `slice_job_id` / `SLICE_JOB_NAME` / `SLICER_QUEUE_NAME`; enqueue by hash directly (no `source_stl`). Document the `missing_stl`-if-uncached boundary.
- [ ] **T4** (AC-5) — Recompute-trigger dispatch (the Decision AJ table) *(red→green)*
  - [ ] T4.1 Failing tests: `RecomputeTrigger` covers every architecture-table row; `spoolman_cost_only` → arithmetic, no enqueue; missing `price_per_gram` on cost-only ⇒ raise; `bundle_retune`/`orca_upgrade`/`spoolman_mapped_override` → stale → enqueue → queued; `stl_content_change` documented (new key, no transition).
  - [ ] T4.2 Implement `RecomputeTrigger` + `invalidate(...)` dispatch in `recompute.py` (the single cheap-vs-expensive chokepoint; the R1 guard lives here).
- [ ] **T5** (AC-6) — Enumeration + bulk primitives *(red→green)*
  - [ ] T5.1 Failing tests: `iter_stl_estimates` yields all bundle variants for one STL, ignores lock/`.tmp` sidecars, empty on miss; `iter_all_estimates` walks the subtree; bulk cost recompute applies per-key with no enqueue; bulk invalidate marks each stale + enqueues each (per-key dedupe).
  - [ ] T5.2 Implement `iter_stl_estimates` / `iter_all_estimates` on `estimate_store.py` (reuse the `validate_content_hash` gate; skip `.lock`/`.tmp`) + the bulk helpers in `recompute.py`.
- [ ] **T6** (AC-7) — Story 32.5 coordination boundary *(red→green)*
  - [ ] T6.1 Failing tests: `recompute.py` does not import `app.modules.spools`; cost-only input is a scalar `price_per_gram`, not a Spoolman record.
  - [ ] T6.2 Confirm the engine takes `price_per_gram` / new `bundle_hash` as inputs; module docstring names the "engine here, Spoolman wiring in 32.5" boundary.
- [ ] **T7** (AC-8) — Observability *(red→green)*
  - [ ] T7.1 Failing tests: cost-only emits an arithmetic-path tag; invalidate emits trigger + status tags; bulk emits a count; no full-record/g-code dump in logs.
  - [ ] T7.2 Implement `_emit_*` structured lines + the `slicer.recompute` OTel span (reuse the 32.3 `_emit_estimate_persist` / `slicer.estimate` shape).
- [ ] **T-DET** (AC-12) — Determinism gate: 3× consecutive identical pytest pass counts on the slicer suite; `computed_at` excluded from assertions; a concurrency test on the transition path (two threads racing a transition, lock serializes, no torn write).
- [ ] **T8** (AC-9, AC-10) — Scope fence + grep/drift *(grep/diff)*
  - [ ] T8.1 `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` → 0 lines; no Alembic version file; `pyproject.toml` deps unchanged; `config.py` Settings field set unchanged (no new slot); `SliceOutcome`/`_classify`/`run_slice_job`/`slice_estimate` byte-identical.
  - [ ] T8.2 NFR20-CONTAINER-1 grep invariant ZERO over the slicer module (incl. `recompute.py`); `check-settings-env-compose.py` → OK at the unchanged 50/48/38.
- [ ] **T9** (AC-13, full quality gate) — `ruff format --check` + `ruff check` clean on `apps/api/`; full backend `pytest -q` green (record the exact baseline + new-case counts). No vitest/Playwright (backend only).
- [ ] **T10** (handoff) — dev-story flips `ready-for-dev → review`; code-review owns `→ done`. **Commit / ff-merge / deploy NOT performed by dev-story — controller-owned (ITCM).** Story branch: `feat/E32.4-invalidation-recompute-queue-cost-arithmetic`. Suggested commit scope when the controller commits: `feat(api): estimate invalidation/recompute engine + cost-only arithmetic recompute (Story 32.4, Init 20)`. **Deploy caveat (SW-DEPLOY-1):** see the Dev Note — any deploy of this story MUST rebuild/restart the `slicer-worker` overlay + run the in-container import/Orca/parser-cache smoke, because 32.4 lands code under `app.modules.slicer.*`.

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 20 — FR20-CACHE-1 (the `stale`/`queued` transitions + recompute dedup deferred from 32.3), FR20-FAILURE-1 (the explicit `stale`-served-flag / soft-fail contract), NFR20-REPRODUCIBLE-1 (hash-driven invalidation + **cost-only-arithmetic-no-re-slice**, the <1s pytest contract), NFR20-RESOURCE-1 (recompute dedup + concurrency cap → no recompute-storm DoS), NFR20-OBS-1, NFR20-DETERMINISM-1, OD-7 (RESOLVED: arithmetic recompute only).
- **Architecture:** `architecture.md` § Initiative 20 — Decision **AJ** (the **recompute-trigger table** this story realizes in code; the **cost-only-arithmetic rule** + the R1 Pre-Mortem self-DoS rationale; "staleness is explicit, never silent"). Decision AH (Story 32.1) supplies `bundle_hash`; Decision AI (Story 32.2) supplies the slice-job + `_job_id` dedupe + the `arq:slicer` queue.
- **Epics:** `epics.md` § Initiative 20 § Story 32.4 (sketch: invalidation / recompute queue / cost arithmetic; Stories 32.3 + 32.4 jointly implement Decision AJ).
- **SCP:** `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AJ) + § 4.3 (Story 32.4 sketch).
- **Story 32.3 (done):** `_bmad-output/implementation-artifacts/32-3-gcode-parse-estimate-cache-schema.md` — supplies the `EstimateRecord` (with the `stale`/`queued` enum values already present + the failed/fresh model invariants + the `_reject_non_finite` field validator), the `EstimateStore` (`read`/`write`/`_record_path`/`_load`/`_record_lock`/`_atomic_publish` + the `<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json` layout chosen for 32.4 enumeration), and the no-silent-zero / failed-vs-fresh contracts this story must preserve through every transition.
- **Story 32.2 (done):** `_bmad-output/implementation-artifacts/32-2-slicer-worker-container-cli-invoke-classify.md` — supplies `enqueue.slice_job_id` / `enqueue_slice_estimate` (the `_job_id` dedupe), `worker.SLICER_QUEUE_NAME` / `SlicerWorkerSettings`, `worker_job.SLICE_JOB_NAME` / `slice_estimate`, and the `missing_stl` typed-failure path a by-hash recompute relies on.
- **Story 32.1 (done):** `_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md` — `bundle_hash` folds `orca_version` + the override set (so an Orca upgrade / mapped-override re-hashes the bundle, which is *why* those triggers produce a new key); `overrides.py` `spoolman_overrides_ref` is the Story 32.5 seam folded into `bundle_hash`.
- **Memory entries (read before implementation):**
  - `[[feedback_scp_pre_enumeration_phase]]` — § A pre-enumeration (below), § B cache-coherence table (below), § C magic-constant contract pointing (AC-11). This story is deliberately **constant-free** (event-driven staleness, no TTL) — the § C trap that bit nothing in 32.3 also does not bite here, and AC-9/AC-11 make "no arbitrary constant" an explicit reviewer check.
  - `[[feedback_codex_model_routing]]` — Story 32.4 review-tier routing (single-adjacency: data-integrity; recommended `gpt-5.5`; controller confirms).
  - `[[feedback_itcm_autonomous_mode]]` — dev-story execution is controller-routed; this spec authoring does not itself start dev-story.

### Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

Run 2026-06-01 against post-Story-32.3 repo state (`main` @ `179c08d`):

1. **Files reused / extended (existing — DO NOT duplicate):**
   - `apps/api/app/modules/slicer/estimate_store.py` — `EstimateStore.read`/`write` + the private `_record_path`/`_load`/`_record_lock`/`_atomic_publish` + the `<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json` layout. T1/T2/T5 **APPEND** `mark_stale`/`mark_queued`/`update_cost`/`iter_stl_estimates`/`iter_all_estimates`, all routed through a shared **force-publish-under-`_record_lock`** helper that REUSES `_record_lock` + `_atomic_publish` (the locking + atomic-write discipline is NOT re-authored). The new transitions deliberately **bypass the `write()` fresh-no-op** because a status change / cost change IS a deliberate content change (the no-op exists only for an identical fresh re-slice).
   - `apps/api/app/modules/slicer/models.py` — `EstimateRecord` (`stale`/`queued` enum values ALREADY exist, AC-1 of 32.3; the failed/fresh `model_validator` + the `_reject_non_finite` field validator). 32.4 **SETS** `stale`/`queued` and updates `filament_cost`; it adds **NO field** and changes **NO validator** (a `stale`/`queued` record is intentionally unconstrained by the 32.3 validator so it can carry servable numerics).
   - `apps/api/app/modules/slicer/enqueue.py` — `slice_job_id` + `enqueue_slice_estimate` + `EnqueueResult`. T3 reuses `slice_job_id` and adds a thin **by-hash** `enqueue_recompute` (no `populate_from_source` — the recompute STL is already cached). Does NOT duplicate the enqueue plumbing.
   - `apps/api/app/modules/slicer/worker.py` / `worker_job.py` — `SLICER_QUEUE_NAME` / `SLICE_JOB_NAME` / `slice_estimate` / `_classify` / `run_slice_job`. **READ + reused, NOT reshaped** (32.4 enqueues onto the existing worker; the worker's behavior is unchanged — AC-9). The worker's `slice_estimate` persist (failed/stale/queued ⇒ replace via 32.3 `write`) is the *fresh terminus* of the `stale → queued → fresh` lifecycle.
   - `apps/api/app/modules/slicer/stl_cache.py` — `validate_content_hash`/`is_content_hash`. The new enumeration + transition methods REUSE these for path-safety; they do NOT re-author the 64-lowercase-hex gate.
2. **NEW (Story 32.4 owns):** `apps/api/app/modules/slicer/recompute.py` (the engine: `RecomputeTrigger`, `recompute_cost_only`, `enqueue_recompute`, `invalidate`, the bulk helpers, the `_emit_*`/span instrumentation) + `apps/api/tests/test_slicer_recompute.py` (transition + cost-arithmetic + dispatch + enqueue-dedupe + enumeration + obs + determinism cases). (Tests MAY instead extend `test_slicer_estimate.py` for the `EstimateStore` transition methods — keep store-method tests next to the store's existing tests, engine tests in the new file; the dev decides the split, but every AC has a named test.)
3. **MODIFIED (append-only / minimal):** `apps/api/app/modules/slicer/estimate_store.py` (append the transition + enumeration methods + the shared force-publish helper) + `apps/api/tests/test_slicer_estimate.py` (transition-method cases, if co-located).
4. **Contracts UNTOUCHED:** `_PUBLIC_ROUTES`, `apps/api/app/router.py`, `apps/api/app/main.py` (no routes — AC-9). `SliceStatus`/`SliceFailureReason`/`SliceOutcome` + `_classify`/`run_slice_job`/`slice_estimate` + `SlicerWorkerSettings` (Story 32.2 contract — AC-9). `EstimateRecord` field set + validators (Story 32.3 — AC-9). `apps/api/app/modules/spools/*` (Story 32.5 — AC-7). `apps/api/app/core/config.py` Settings (no new slot — AC-9). `workers/render/*`, `apps/api/app/workers/*`. No Alembic. No `apps/web/`. `~/repos/configs/*` (HC2 — no configs-side gate for the *spec*; the deploy-time overlay rebuild is SW-DEPLOY-1, a runtime concern noted below).

**Net scope:** 1 new module file (`recompute.py`) + 1 new (or extended) test file + 1 modified store file (append-only methods) + 0 new config slots + 0 Alembic + 0 routes + 0 `SliceOutcome`/worker reshape + 0 new heavy deps + 0 configs-repo edits + 0 subprocess.

### Cache-coherence / boundary enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

Backend file-store story (no React Query / TanStack cache — that's Story 32.6), so the FE cache-topology table does not apply. The coherence concerns this story owns:

| Concern | Source: Story 32.4 (this story) | Related surface |
|---|---|---|
| Stale-vs-fresh serve | a `stale`/`queued` record is SERVED with its status flag + last-known numerics + original `computed_at` (AC-1/AC-2) — never hidden, never coerced to `fresh` | Story 32.6 reads `status` and renders "may be out of date, recomputing" / "Last estimated HH:MM (Xm ago)". The R9 contract: a superseded estimate is NEVER served as `fresh`. |
| Cheap vs. expensive recompute path | the `invalidate` dispatch (AC-5) is the single chokepoint: `spoolman_cost_only` → arithmetic (no enqueue); all slice-affecting triggers → stale + idempotent enqueue | The R1 Pre-Mortem self-DoS guard: a Spoolman price tick must NEVER reach the enqueue path (NFR20-REPRODUCIBLE-1 + the `test_cost_only_recompute_does_not_enqueue_any_slice` assertion). |
| Recompute-queue dedup | `enqueue_recompute` rides the Story 32.2 `_job_id = slice:<stl>:<bundle>` (AC-4) | Distinct from the Story 32.3 *write-time* dedup (`fresh` re-write = no-op). Two dedups on the same key: write-time (32.3) + queue-time (32.2/32.4) — 32.4 reuses the queue-time one verbatim, does NOT re-implement write-time dedup. |
| Transition race-safety | every transition (`mark_stale`/`mark_queued`/`update_cost`) runs under the Story 32.3 per-record `_record_lock` over read-modify-publish | The worker's `slice_estimate` persist also takes `_record_lock`; a recompute transition and a concurrent slice persist for the same key are serialized — no torn write, no lost transition (T-DET concurrency test). |
| Key change vs. in-place transition | `spoolman_cost_only` / mark_stale-queued = **in-place** (same key); `stl_content_change` / `bundle_retune` / `orca_upgrade` / `mapped_override` = **new key** (the hash changes) → the *old* record is marked stale (servable) and the *new* key is enqueued | The old→new `bundle_hash` mapping is computed by Story 32.1 resolve / Story 32.5 Spoolman linkage and PASSED IN (AC-7); 32.4 does not derive it. `stl_content_change`'s new key is a natural miss handled by the Story 32.2 first-enqueue; orphan GC of the old key is deferred (AC-9). |
| Cost-carry consumed | `recompute_cost_only` multiplies the Story 32.3-carried `filament_g` by the caller's `price_per_gram` | Story 32.3 carries `filament_g` + `filament_cost` specifically so 32.4 can recompute WITHOUT re-slicing (OD-7). If `filament_g` were absent the cost path can't run — but the 32.3 `fresh` invariant guarantees it present on every servable record. |

Decision rule: the dispatch (AC-5) is the load-bearing coherence chokepoint — it MUST route `spoolman_cost_only` to the arithmetic path and every slice-affecting trigger to the stale+enqueue path, and it MUST preserve the Story 32.3 failed/fresh invariants + the no-silent-zero contract through every transition (a `failed` record never gains a number; a `stale`/`queued` record keeps its servable numbers; a cost recompute never writes `0`/`nan`/negative).

### Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` § C)

This story is **constant-free by design** (AC-9, AC-11): staleness is *event-driven* (a trigger fires), NOT time-based, so there is **no TTL / staleness-age / recompute-budget / batch-size / retry-count constant** to introduce. The Story 32.6 "Xm ago" indicator derives age from `computed_at` *at render time* (FE), not from a backend threshold. The `<1s` cost-only figure (NFR20-REPRODUCIBLE-1) is a **performance contract asserted in a test** (`test_cost_only_recompute_completes_well_under_one_second`), not a literal in code. The two reused literals (`_job_id` shape, the `cost = mass × price/gram` formula) point to their contracts in the AC-11 table. **If the dev finds itself reaching for a numeric staleness/budget literal, that is a design smell — STOP and reconsider** (the trigger is the signal, not a clock).

### Threat-vector enumeration

Story 32.4 routes to the higher review tier for **data-integrity** adjacency only (NOT runtime-boundary, NOT auth-boundary — same posture as Story 32.3). Survey:

- **No HTTP surface, no auth, no CSRF, no public-bypass family touch** — zero routes mounted (AC-9).
- **No subprocess / no real Orca in the cost-only path** — pure arithmetic + a local atomic file write. The re-slice path *enqueues* a job onto the existing Story 32.2 worker but does not spawn Orca itself; the runtime-boundary risk class lives in 32.2 (done), not here.
- **Data-integrity (the real risk class):**
  - **R9 "stale served as fresh"** — a wrong transition that leaves a superseded estimate readable as `fresh`. Mitigated by the explicit `mark_stale`/`mark_queued` status edges (AC-1/AC-2) + the AC-9 read-side-no-coercion fence + the `test_stale_record_is_returned_by_read_not_hidden` assertion.
  - **R1 "re-slice storm self-DoS"** — a cost-only change accidentally hitting the expensive enqueue path. Mitigated by the dispatch chokepoint (AC-5) + `test_cost_only_recompute_does_not_enqueue_any_slice` + `test_dispatch_cost_only_takes_arithmetic_path_no_enqueue` (the single most important test in the story).
  - **Silent-zero / poisoned-arithmetic** — a cost recompute writing `0` / `nan` / `inf` / negative. Mitigated by the AC-3 finite+non-negative `price_per_gram` guard (raise, never silently zero) + the Story 32.3 `_reject_non_finite` model-edge backstop + the failed-record no-op (no mass ⇒ no fabricated cost).
  - **Non-idempotent recompute** — a double-run of an expensive slice. Mitigated by the reused `_job_id` dedupe (AC-4) + `test_enqueue_recompute_is_idempotent_dedupe`.
  - **Lost/torn transition under concurrency** — mitigated by the per-record `_record_lock` over read-modify-publish (AC-1, reused from 32.3) + the T-DET concurrency test.
- **Path-safety:** every transition / enumeration path is built only from `validate_content_hash`-gated hashes (reuse the Story 32.3 gate) — no user-controlled path component, no traversal vector.
- **No PII.** **g-code:** the cost-only path never touches g-code; the re-slice path rides the unchanged parse-and-discard (AC-8 forbids full-record/g-code log dumps).

### Runtime / deploy verification (SW-DEPLOY-1 — note, NOT in-scope to fix)

Story 32.4 lands code under `apps/api/app/modules/slicer/*` (`recompute.py` + `estimate_store.py` edits), which the `slicer-worker` overlay image (`portal-slicer-worker:0.1.0`, layered on `portal-api`) executes. Per the deferred item **SW-DEPLOY-1** (`_bmad-output/implementation-artifacts/deferred-work.md`), `infra/scripts/deploy.sh` rebuilds/restarts only the base stack — it does **NOT** rebuild/restart the configs-side `slicer-worker` overlay — so a deploy can leave the worker running stale slicer modules (a silent API↔worker version skew, exactly the failure that hit Story 32.3).

**Therefore, whenever this story is committed/merged/deployed (controller-owned, ITCM), the deploy MUST be followed by the documented manual overlay rebuild + in-container smoke** (from `deferred-work.md` § SW-DEPLOY-1):

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f /mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.yml \
  --profile slicer-worker up -d slicer-worker
# then verify from inside 3d-portal-slicer-worker-1:
#   (a) slicer modules import — incl. the NEW `recompute` + the `estimate_store` edits
#   (b) Orca binary present + runnable
#   (c) parser/cache smoke passes
```

**Important nuance:** the **cost-only arithmetic recompute path runs API-side** (synchronous, no slicer-worker job — AC-3), so a stale worker image does NOT silently break the cost path. The **re-slice recompute path** (enqueue) DOES run on the worker, so the skew matters for it. Either way the overlay rebuild + import smoke is mandatory on any deploy of this story (the worker must carry the new `app.modules.slicer.recompute` import even though it only *enqueues* onto the worker — `slice_estimate` itself is unchanged, but the image base advances with `portal-api`).

**Implementing SW-DEPLOY-1 (the deploy-automation fix) is explicitly OUT of scope for 32.4** (it crosses the repo↔configs boundary — HC2 — and is its own deferred item to promote separately). 32.4 only carries the verification *note* so the controller's deploy step is correct.

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/slicer/recompute.py` | NEW | T2/T3/T4/T5/T7 — the engine: `RecomputeTrigger`, `recompute_cost_only`, `enqueue_recompute`, `invalidate` dispatch, bulk helpers, `_emit_*`/`slicer.recompute` span |
| `apps/api/app/modules/slicer/estimate_store.py` | MODIFY (append) | T1/T2/T5 — `mark_stale`/`mark_queued`/`update_cost`/`iter_stl_estimates`/`iter_all_estimates` + the shared force-publish-under-`_record_lock` helper (reuses `_record_lock`/`_atomic_publish`; no re-author) |
| `apps/api/tests/test_slicer_recompute.py` | NEW | T2–T7, T-DET — engine + dispatch + cost-arithmetic + enqueue-dedupe + obs + determinism cases (pure; no env gate, no real Orca) |
| `apps/api/tests/test_slicer_estimate.py` | EXTEND (optional) | T1 — `EstimateStore` transition-method cases, co-located with the existing store tests (dev's split) |

**Files this story MUST NOT touch:** `apps/api/app/main.py` (`_PUBLIC_ROUTES`), `apps/api/app/router.py`, `apps/api/app/modules/share/router.py`, `apps/api/app/modules/spools/*` (Story 32.5 — AC-7), `apps/api/app/core/config.py` (no new slot — AC-9), `apps/api/app/modules/slicer/models.py` (no field/validator change — AC-9), `apps/api/app/modules/slicer/worker.py` + the `_classify`/`run_slice_job`/`slice_estimate` orchestration in `worker_job.py` + `SliceOutcome` (Story 32.2 contract — AC-9), `workers/render/*`, `apps/api/app/workers/*`, `apps/web/`, `apps/api/migrations/`, `~/repos/configs/*` (HC2 — SW-DEPLOY-1 is a runtime/deploy note, not an in-repo edit).

### Project Structure Notes

- OD-9-resolved: the recompute engine joins the existing `apps/api/app/modules/slicer/` bounded-context module (siblings: `models`/`resolver`/`merge`/`overrides`/`validation`/`cli`/`stl_cache`/`bundle_store`/`worker`/`worker_job`/`enqueue`/`gcode_parse`/`estimate_store` → + `recompute`). No new top-level package; no `estimates`/`recompute` subpackage (the repo convention keeps the bounded context flat).
- The recompute engine is a thin orchestration layer over the Story 32.3 `EstimateStore` + the Story 32.2 enqueue — it introduces no new persistence mechanism (the append-only file store is reused; transitions are atomic rewrites of existing records).
- The frontend `apps/web/src/modules/estimates/` stale/soft-fail/"Last estimated HH:MM" display (OD-9) is Story 32.6, NOT this story; the ops/Spoolman *event wiring* that fires these triggers is Story 32.5 + a future ops surface, NOT this story (AC-7).

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 20 — Decision AJ (recompute-trigger table, cost-only-arithmetic rule + R1 rationale, staleness-explicit-never-silent)]
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 20 — FR20-CACHE-1 + FR20-FAILURE-1 + NFR20-REPRODUCIBLE-1 (<1s cost-only contract) + NFR20-RESOURCE-1 + NFR20-OBS-1 + NFR20-DETERMINISM-1 + OD-7 RESOLVED]
- [Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 20 § Story 32.4]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3]
- [Source: `_bmad-output/implementation-artifacts/32-3-gcode-parse-estimate-cache-schema.md` — `EstimateRecord` + `EstimateStore` (`_record_lock`/`_atomic_publish`/layout) + failed/fresh + no-silent-zero contracts]
- [Source: `_bmad-output/implementation-artifacts/32-2-slicer-worker-container-cli-invoke-classify.md` — `slice_job_id`/`enqueue_slice_estimate`/`SLICER_QUEUE_NAME`/`slice_estimate`/`missing_stl`]
- [Source: `_bmad-output/implementation-artifacts/deferred-work.md` § SW-DEPLOY-1 — the deploy-overlay-rebuild caveat]

## Out of scope (explicit)

- **Frontend** stale/queued/soft-fail/"Last estimated HH:MM (Xm ago)" display + the estimate read route → Story 32.6.
- **Spoolman mapping / event wiring**: reading Spoolman, mapping `filament.extra`, computing `spoolman_overrides_ref` / the new `bundle_hash`, deriving `price_per_gram` from `filament.price`/`weight`, detecting a Spoolman price/mapped-field change in the poll → Story 32.5 (32.4 takes `price_per_gram` / new `bundle_hash` as inputs — AC-7).
- **Orphan-record GC**: reaping the old `stl_hash` dir after an STL content change → future maintenance concern (AC-9).
- **SW-DEPLOY-1 implementation** (teaching `deploy.sh` to rebuild/restart the slicer-worker overlay) → separate deferred item, crosses HC2 (Dev Note carries the manual verification step only).
- **New config / TTL / staleness budget** — none (event-driven staleness; AC-9/AC-11).
- **Any `SliceOutcome` / worker-orchestration / `EstimateRecord`-shape change** → Story 32.2 / 32.3 contracts frozen (AC-9).

## Risks

- **R1 (top, self-DoS): a cost-only Spoolman change re-slices.** Mitigation: the AC-5 dispatch chokepoint routes `spoolman_cost_only` to the arithmetic path with NO enqueue; `test_cost_only_recompute_does_not_enqueue_any_slice` is the load-bearing guard. Likelihood low / impact high → the single most-watched test.
- **R9: stale served as fresh.** Mitigation: explicit `mark_stale`/`mark_queued` edges preserving servable numerics + the read-side no-coercion fence (AC-1/AC-2/AC-9). Likelihood low / impact high.
- **Poisoned-arithmetic (nan/inf/negative cost).** Mitigation: AC-3 finite+non-negative `price_per_gram` guard (raise, never silent-zero) + the 32.3 model-edge `_reject_non_finite` backstop. Likelihood low / impact medium.
- **Lost transition under concurrency.** Mitigation: per-record `_record_lock` reused from 32.3 over read-modify-publish + the T-DET concurrency test. Likelihood low / impact medium.
- **Deploy version skew (SW-DEPLOY-1).** Mitigation: the mandatory overlay-rebuild + in-container smoke note (Dev Note); the cost-only path is API-side so it is resilient to a stale worker, but the re-slice path needs the rebuilt worker. Likelihood medium (every slicer-code deploy) / impact medium → controller deploy-step responsibility, not a code fix here.

## Gate plan

| Gate | Command | Expected |
|---|---|---|
| Unit (new) | `uv run pytest tests/test_slicer_recompute.py -q` (+ `test_slicer_estimate.py` transition cases) | all green; the AC-1..AC-8 named tests present |
| Slicer suite | `uv run pytest tests/test_slicer*.py -q` | green; determinism 3× identical (AC-12, incl. the transition concurrency test) |
| Full backend | `uv run pytest -q` | green (record baseline + new-case counts) |
| Lint | `uv run ruff format --check .` + `uv run ruff check .` (`apps/api/`) | clean |
| Scope fence | `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` | 0 lines (AC-9) |
| No-Alembic / no-dep / no-config-slot | inspect `migrations/versions/`, `pyproject.toml`, `config.py` Settings field set | unchanged (AC-9) |
| Worker/model frozen | assert `SliceOutcome`/`_classify`/`run_slice_job`/`slice_estimate`/`EstimateRecord` field+sig unchanged | byte-identical (AC-9) |
| NFR20-CONTAINER-1 | `grep -rniE "/mnt/c|fenrir|\.exe|[Ww]indows" apps/api/app/modules/slicer/` | ZERO (AC-10) |
| Drift gate | `python3 infra/scripts/check-settings-env-compose.py` | OK, unchanged 50/48/38 (AC-10) |
| Diff hygiene | `git diff --check && git diff --cached --check` | clean |

**Handoff:** dev-story flips `ready-for-dev → review`; `bmad-code-review` (prefer a different LLM; Codex `gpt-5.5`, single-adjacency data-integrity) owns `review → done`. **Commit / ff-merge / deploy + the SW-DEPLOY-1 overlay rebuild remain controller-owned (ITCM)** — NOT performed by dev-story.

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-06-01 | 0.1 | Story 32.4 spec authored (`bmad-create-story`); status `backlog → ready-for-dev`. App-side estimate invalidation/recompute engine: `mark_stale`/`mark_queued` transitions (servable, never hidden), cost-only arithmetic recompute (`cost = mass × price/gram`, no re-slice, <1s), idempotent recompute enqueue (reused `_job_id` dedupe), the Decision AJ recompute-trigger dispatch, bulk/enumeration primitives. No routes / no Alembic / no config slot / no `SliceOutcome`/worker reshape / no Spoolman read / no FE. Realizes FR20-CACHE-1 (transitions) + NFR20-REPRODUCIBLE-1 + NFR20-RESOURCE-1; anchors Decision AJ recompute-trigger table; coordinates with 32.5 (engine here, Spoolman wiring there). SW-DEPLOY-1 deploy-overlay-rebuild caveat noted (not fixed). Codex tag `gpt-5.5` (single-adjacency data-integrity). Spec authoring only — NO code; dev-story execution controller-routed (ITCM). | Claude Opus 4.8 (`bmad-create-story`) |
