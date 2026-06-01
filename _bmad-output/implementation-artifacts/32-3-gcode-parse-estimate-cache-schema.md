---
baseline_commit: da2f593580c4bebf46ed995c9d3383fbf9a12127
---

# Story 32.3: G-code metadata parse → typed `EstimateRecord` + `(stl_hash, bundle_hash)` append-only cache schema + cost-carry fields

Status: ready-for-dev

## Story

As a **portal backend that can now run a real headless slice and hand the temp g-code to a parser sink (Story 32.2) but has no typed estimate it can persist, read back, or recompute**,
I want **a small pure, unit-testable g-code metadata parser (g-code text in → typed `EstimateRecord` fields out; time strings like `3h35m47s` normalize to seconds; a missing/garbled metadata line ⇒ a classified parse failure, never a silent zero), a typed `EstimateRecord` keyed `(stl_hash, bundle_hash)` carrying `time_seconds` / `filament_g` / `filament_mm` / `filament_cm3` / `filament_cost` / `settings_ids` (attribution) / `warnings` / `status` / `computed_at`, an append-only content-addressed estimate cache (write / read / dedup on the key — a `fresh` re-write is an idempotent no-op), and the parser-sink + persist integration that slots into the Story 32.2 `GcodeSink` seam WITHOUT reshaping the slice orchestration**,
so that **Story 32.4 has a persisted, cost-carrying `EstimateRecord` keyed on exactly the `(stl_hash, bundle_hash)` reproducibility tuple it will invalidate/recompute against (cost-only changes recomputed arithmetically from the carried `filament_g` + `filament_cost`, never by re-slicing — NFR20-REPRODUCIBLE-1 / Decision AJ), Story 32.6 has a typed record (time / mass / length / volume / cost / warnings / `settings_ids`) to render and a classified `failed` state to soft-fail on, every estimate is traceable to the exact resolved profile that produced it (NFR20-ATTRIBUTION-1), and a garbled slice never surfaces a plausible-but-wrong number (FR20-ESTIMATE-1 parse half)**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AJ) + § 4.3 (Epic E32 story sketch).
Architectural anchor: Decision **AJ** (cache / invalidation / cost arithmetic — `EstimateRecord` keyed `(stl_hash, bundle_hash)`, the complete reproducibility key; cost is derived post-slice arithmetic, not a slice input) per `architecture.md` § Initiative 20. Decision AH (Story 32.1) supplies the `bundle_hash`; Decision AI (Story 32.2) supplies the g-code + `SliceOutcome` this story parses.
Realizes **FR20-ESTIMATE-1** (parse half — the typed `EstimateRecord` + the pure g-code-metadata parser) + **FR20-CACHE-1** (cache read/write + dedup on the key; the explicit `status` field — `stale`/`queued` *transitions* are Story 32.4) + **NFR20-ATTRIBUTION-1** (`settings_ids` provenance). Consumes the g-code temp path + `SliceOutcome` Story 32.2 produces; feeds the persisted, cost-carrying `EstimateRecord` Story 32.4 invalidates/recomputes and Story 32.6 displays.
OD-gate context: authored after the **2026-05-31 OD-gate resolution** (OD-5 leaning **parse-and-discard** — the parser runs in-job over the temp g-code which is still deleted at job end, zero durable g-code retention; OD-7 cost-only arithmetic recompute — 32.3 *carries* `filament_g` + `filament_cost` so 32.4 can recompute without re-slicing; OD-8 `.190`-mirrored source; OD-9 dedicated `slicer` module — see `prd.md` § Initiative 20 § Open decisions). Per the PRD § Open-decisions note, Stories 32.2–32.6 are authored individually by `bmad-create-story` at their own dev-entry time; **this is Story 32.3's dev-entry authoring**. Authoring this spec to `ready-for-dev` does NOT itself start `bmad-dev-story` — execution remains controller-routed (ITCM autonomous mode). Unlike Story 32.2 there is **no external configs-side coordination gate**: the `slicer-worker` container already exists and is deployed (Story 32.2 done/merged/deployed on `.190`); 32.3 is **pure app-side** (parser + schema + file-backed cache + the in-process sink seam).
**Codex tag (recommended `gpt-5.5`; controller confirms — route per `[[feedback_codex_model_routing]]`):** this story is **single-adjacency: data-integrity**. A mis-parsed metadata line, a wrong time-string normalization, or a silent-zero on a missing line produces a plausible-but-wrong estimate that propagates into 32.4 recompute + 32.6 display; the `settings_ids` attribution is the traceability contract (NFR20-ATTRIBUTION-1); the `(stl_hash, bundle_hash)` cache key must be content-hash-complete or a re-tune/Orca-upgrade would alias an old estimate (R9 "stale served as fresh"). **No runtime-boundary adjacency** (this story spawns NO subprocess — the real Orca invocation is Story 32.2; here the parser is a pure function over text and the store is a local append-only file write). **No public-route / auth-bypass adjacency** (zero HTTP routes — AC-13).

## Acceptance Criteria

### AC-1 — Typed `EstimateRecord` + `EstimateStatus` + `EstimateFailureReason` appended to the existing `models.py` (no `SliceOutcome` reshape)

Extend `apps/api/app/modules/slicer/models.py` (Story 32.1/32.2's file — one module, no new models file) with the estimate data-model surfaces of Decision AJ:

- **`EstimateStatus`** (`StrEnum`): `fresh`, `stale`, `queued`, `failed`. This story writes only `fresh` (successful parse) and `failed` (classified parse failure); the `stale`/`queued` *transitions* are Story 32.4 (invalidation/recompute) — the enum values exist now so 32.4 extends behavior, not shape.
- **`EstimateFailureReason`** (`StrEnum`): the g-code-metadata parse failure taxonomy — at minimum `parse_failure` plus granular reasons (`missing_metadata_line`, `unparseable_time`, `unparseable_numeric`). This is the **realization of the `parse_failure` reason the Story 32.2 `models.py` docstring reserved** — placed on the *estimate* record, NOT on `SliceOutcome`, so the slice-**invocation** taxonomy (`SliceStatus`/`SliceFailureReason`/`SliceOutcome`) stays **byte-unreshaped** exactly as Story 32.2 AC-6 promised ("32.3 extends the taxonomy without reshaping `SliceOutcome`"). Slice-invocation outcomes (`non_manifold`, `timeout`, …) are an orthogonal axis owned by 32.2 and are NOT duplicated here.
- **`EstimateRecord`** (Pydantic `BaseModel`) — the typed per-STL estimate, keyed `(stl_hash, bundle_hash)`:
  - `stl_hash: str`, `bundle_hash: str` — the cache key (the complete reproducibility tuple; `bundle_hash` already folds `orca_version` + the Spoolman-override set per Story 32.1).
  - `orca_version: str` — carried for traceability (already inside `bundle_hash`; stored denormalized so a record is self-describing).
  - `time_seconds: int | None` — normalized print time (AC-3).
  - `filament_g: float | None`, `filament_mm: float | None`, `filament_cm3: float | None` — filament usage.
  - `filament_cost: float | None` — **informational** owner-side cost from the slice's own cost line; **carried so Story 32.4 can recompute it arithmetically** (`cost = mass × price/gram`) without re-slicing (AC-7, OD-7, NFR20-REPRODUCIBLE-1). Never a quote/checkout price.
  - `settings_ids: dict[str, str]` — the `{filament,print,printer}_settings_id` g-code lines (NFR20-ATTRIBUTION-1, AC-7).
  - `warnings: list[SliceWarning]` — carried verbatim from the Story 32.2 `SliceOutcome.warnings` (reuse the existing `SliceWarning` model; do NOT redefine it).
  - `status: EstimateStatus`, `reason: EstimateFailureReason | None` (set only when `status == failed`).
  - `computed_at: str` — ISO provenance timestamp; **excluded from any content identity / dedup comparison** (AC-6) and from determinism assertions (AC-12), mirroring the Story 32.1 `created_at`-excluded-from-hash discipline.
- On a `failed` record the numeric fields are `None` (never `0` — a zero is a plausible-but-wrong value a caller could spend/print against; `None` + `reason` is the no-silent-zero contract, FR20-ESTIMATE-1 / FR20-FAILURE-1 parse half).

**Tests (red→green):** `test_estimate_status_enum_values`; `test_estimate_failure_reason_extends_not_reshapes_sliceoutcome` (assert `SliceOutcome`/`SliceFailureReason` field sets unchanged); `test_estimate_record_failed_has_none_numerics_not_zero`; `test_estimate_record_reuses_slicewarning_model`.

### AC-2 — Pure, unit-testable g-code metadata parser (`gcode_parse.py`): text in → typed parsed fields out

New `apps/api/app/modules/slicer/gcode_parse.py` — a **pure function** `parse_gcode_metadata(gcode_text: str) -> ParsedEstimate | EstimateParseFailure` (no file I/O, no clock, no subprocess; the I/O lives in the sink/store, AC-8/AC-5):

- Parses the **confirmed-present OrcaSlicer 2.3.2 g-code metadata footer lines** (PRD § Init 20 feasibility; the real line shapes captured by the Story 32.2 in-container PLA/TPU slice — see AC-11 contract pointing):
  - `; estimated printing time (normal mode) = 3h35m47s` → `time_seconds` (via AC-3).
  - `; filament used [mm] = 25735.79` → `filament_mm`.
  - `; filament used [cm3] = 61.90` → `filament_cm3`.
  - `; filament used [g] = 76.76` → `filament_g`.
  - `; total filament cost = 4.60` → `filament_cost`.
  - `; filament_settings_id = "…"`, `; printer_settings_id = "…"`, `; print_settings_id = "…"` → `settings_ids` (AC-7; surrounding quotes stripped).
- Matching is **key-anchored + separator-tolerant** (regex on the metadata key + `=` + value), robust to whitespace; it does NOT depend on line ordering or on g-code body content (only the comment footer). Returns a typed `ParsedEstimate` (the numeric/attribution fields) on success; the record assembly (adding the key + status + warnings) is the caller's job (AC-8).
- The parser carries **no key context** (`stl_hash`/`bundle_hash`/`orca_version` are added by the caller, AC-8) — keeping it a pure text→struct function maximally unit-testable (the FR20-ESTIMATE-1 "small unit-testable pure function" contract).

**Tests (red→green):** fixtures authored from the proven bench metadata (PLA: `76.76 g` / `61.90 cm3` / `25735.79 mm` / `3h35m47s` / cost `4.60`; TPU: `77.25 g` / `8h06m05s`) under `apps/api/tests/fixtures/slicer/gcode/`; `test_parses_all_metadata_fields_pla`; `test_parses_tpu_metadata`; `test_settings_ids_extracted_and_dequoted`; `test_parse_is_order_independent`; `test_parser_is_pure_no_io` (no file/clock access).

### AC-3 — Time-string normalization (`3h35m47s` → seconds) as a pure function with edge cases

A pure `parse_duration_to_seconds(value: str) -> int | None` (in `gcode_parse.py`):

- Normalizes the OrcaSlicer duration grammar: optional `d`/`h`/`m`/`s` tokens, e.g. `3h35m47s`, `8h06m05s`, `35m47s`, `47s`, and (defensively) `1d2h3m4s`. Multipliers point to the time-format contract (AC-11): `1d = 86400`, `1h = 3600`, `1m = 60`, `1s = 1`.
- A value that matches no token / is empty / is garbled returns `None` → the caller classifies `unparseable_time` (AC-4), never `0` (a zero-second print is a plausible-but-wrong silent zero).

**Tests (red→green):** `test_duration_h_m_s`; `test_duration_m_s_only`; `test_duration_s_only`; `test_duration_with_days`; `test_duration_garbled_returns_none`; `test_duration_empty_returns_none`.

### AC-4 — Missing / garbled metadata line ⇒ classified parse failure, never a silent zero (FR20-ESTIMATE-1 / FR20-FAILURE-1 parse half)

- A **required** metadata line absent from the g-code (`time`, `filament_g`, `filament_mm`, `filament_cm3`) ⇒ `parse_gcode_metadata` returns a typed `EstimateParseFailure(reason=missing_metadata_line, detail="<which line>")`. (`filament_cost` and `settings_ids` are **non-fatal**: cost is informational and may be absent if no spool price is configured; missing `settings_ids` degrade attribution but do not invalidate the numbers — record them as absent, do NOT fail. Name this required-vs-optional split explicitly in the parser.)
- A **present-but-unparseable** value (non-numeric mass, a time string AC-3 can't normalize) ⇒ `EstimateParseFailure(reason=unparseable_time | unparseable_numeric, detail=…)`.
- The caller (AC-8) turns an `EstimateParseFailure` into a persisted `EstimateRecord(status=failed, reason=…, numerics=None)` — so Story 32.6 can render "couldn't estimate, here's why" and Story 32.4 knows the key has been attempted. **Never** a success-with-zero.

**Tests (red→green):** `test_missing_time_line_classifies_missing_metadata_line`; `test_missing_filament_g_classifies_missing_metadata_line`; `test_non_numeric_mass_classifies_unparseable_numeric`; `test_unparseable_time_classifies_unparseable_time`; `test_missing_cost_is_non_fatal`; `test_missing_settings_ids_is_non_fatal_attribution_degrades`; `test_parse_failure_never_returns_silent_zero`.

### AC-5 — Append-only content-addressed estimate cache (`estimate_store.py`): write / read + path-safety + layout

New `apps/api/app/modules/slicer/estimate_store.py` — `EstimateStore` rooted at one settings-sourced dir (AC-9), mirroring the Story 32.1 `bundle_store.py` append-only / atomic-write / first-write-wins contract (no DB — per SCP "No DB schema; append-only estimate records", and per `bundle_store.py:4`):

- **Layout:** `<estimate_root>/estimates/<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json` — hash-prefix fan-out (AC-11) grouping every bundle-variant estimate for one STL under one `<stl_hash>/` dir (so Story 32.4 can enumerate the sibling estimates affected by a bundle re-tune without a full scan).
- **Path-safety:** BOTH `stl_hash` and `bundle_hash` pass `validate_content_hash` (reuse `stl_cache.validate_content_hash`, do NOT re-author the 64-lowercase-hex gate) **before** any path is interpolated, so a malformed/traversal-shaped hash can never escape the store root (the Story 32.2 review-fix #2 discipline).
- **Write:** `write(record: EstimateRecord) -> Path` — atomic temp-write + link-publish (reuse the `bundle_store._atomic_write` pattern); `read(stl_hash, bundle_hash) -> EstimateRecord | None` (a miss is `None`, never a fabricated default).

**Tests (red→green):** `test_estimate_store_write_then_read_roundtrip`; `test_estimate_store_layout_is_stl_then_bundle_fanout`; `test_estimate_store_rejects_malformed_stl_hash`; `test_estimate_store_rejects_malformed_bundle_hash`; `test_estimate_store_read_miss_returns_none`; `test_estimate_store_atomic_write_no_partial_on_concurrent_read`.

### AC-6 — Cache dedup / idempotency: a `fresh` re-write on an existing key is a no-op (FR20-CACHE-1)

- Writing an `EstimateRecord` for a `(stl_hash, bundle_hash)` that already holds a **`fresh`** record is an **idempotent no-op** (the existing record is left untouched; identity is the content-addressed key + the pinned inputs, so re-slicing the same part+bundle yields the same numbers — re-computing a `fresh` record changes nothing). `computed_at` differences alone do NOT count as a change (it is excluded from the dedup comparison, AC-1).
- A write over a **`failed`** (or, post-32.4, `stale`/`queued`) record **does** replace it (a retry that now parses cleanly must win). Name the "fresh ⇒ no-op, non-fresh ⇒ replace" rule explicitly; it is the FR20-CACHE-1 dedup contract and the seam Story 32.4 recompute rides.
- **Scope fence:** 32.3 owns *write-time dedup on the key*; it does **NOT** own the recompute *queue* dedup (`_job_id`, that is the Story 32.2 enqueue + Story 32.4 recompute concern) nor any `stale`/`queued` *transition* (Story 32.4).

**Tests (red→green):** `test_fresh_rewrite_is_idempotent_noop`; `test_rewrite_over_failed_replaces`; `test_computed_at_difference_alone_is_not_a_change`.

### AC-7 — Cost-carry + attribution fields persisted (NFR20-ATTRIBUTION-1 + the Story 32.4 arithmetic-recompute seam)

- `filament_cost` (from `; total filament cost`) AND `filament_g` (mass) are both persisted on every successful record, because Story 32.4's cost-only arithmetic recompute (`cost = mass × price/gram`, OD-7 / NFR20-REPRODUCIBLE-1) needs the **mass** carried so it can recompute cost from a new Spoolman price **without re-slicing**. Document this carry as the explicit 32.4 seam (a Spoolman price tick must never trigger a minutes-long re-slice — the Pre-Mortem R1 top self-DoS risk).
- `settings_ids` carries `filament_settings_id` + `print_settings_id` + `printer_settings_id` so every estimate names which resolved profile produced it (NFR20-ATTRIBUTION-1 — "an estimate can always be traced back to a resolved bundle"). The field is a `dict[str, str]`; absent ids degrade attribution but do not fail the record (AC-4).

**Tests (red→green):** `test_record_carries_filament_g_and_cost_for_arithmetic_recompute`; `test_settings_ids_attribution_present_on_success`; `test_attribution_invariant_record_names_its_profile`.

### AC-8 — Parser-sink + persist integration via the Story 32.2 `GcodeSink` seam, WITHOUT reshaping the slice orchestration

The Story 32.2 seam (`GcodeSink = Callable[[Path], None]`, default `discard_sink`, called inside `worker_job._classify` while the temp g-code still exists) is the integration point — Story 32.2 AC-5 promised 32.3 "slots in without reshaping `worker_job.py`". Honor that literally:

- New `ParsingGcodeSink` (in `gcode_parse.py` or a small `sink.py`) — a **per-job, callable, stateful** sink: `__call__(self, gcode_path: Path) -> None` reads the file and stashes `self.result: ParsedEstimate | EstimateParseFailure` (parse happens **in-job, while the temp g-code is alive**; the file is still discarded at block exit by the unchanged 32.2 scratch-dir context manager — zero durable g-code, OD-5 / Story 32.2 AC-5).
- **`_classify` and `run_slice_job` are NOT reshaped** (byte-identical orchestration; their `sink(gcode)` call site is untouched). The ONLY edit to `worker_job.py` is in the thin arq entry `slice_estimate(ctx, stl_hash, bundle_hash)`: construct a fresh `ParsingGcodeSink()`, pass it as `gcode_sink=`, and **after** `run_slice_job` returns, assemble + persist:
  - On `SliceOutcome.status ∈ {ok, warning}` + `sink.result` is a `ParsedEstimate` → build `EstimateRecord(status=fresh, key + orca_version + parsed fields + warnings=outcome.warnings)` and `ctx["estimate_store"].write(record)` (subject to the AC-6 dedup).
  - On a `ParsedEstimate` failure (`sink.result` is `EstimateParseFailure`) → write `EstimateRecord(status=failed, reason=…, numerics=None)`.
  - On `SliceOutcome.status == failed` (slice-**invocation** failure — `non_manifold`/`timeout`/… ) → **no estimate is written by this story** (the invocation failure is fully described by `SliceOutcome`; persisting an invocation-failure estimate record is Story 32.4's recompute-state concern, NOT 32.3's parse half). Name this boundary explicitly.
- `EstimateStore` is wired into the worker `ctx` at startup: extend `SlicerWorkerSettings.on_startup` (in `worker.py`) to set `ctx["estimate_store"] = EstimateStore(settings.slicer_estimate_store_dir)` — mirroring how `stl_cache`/`bundle_store`/`cli` are already wired. (The default no-op `discard_sink` path stays valid for any caller that does not opt into persistence.)

**Tests (red→green):** `test_parsing_sink_stashes_parsed_result`; `test_parsing_sink_does_not_retain_gcode_after_job` (temp file gone at block exit); `test_slice_estimate_persists_fresh_record_on_ok`; `test_slice_estimate_persists_failed_record_on_parse_failure`; `test_slice_estimate_writes_no_record_on_invocation_failure`; `test_classify_and_run_slice_job_orchestration_unreshaped` (assert the 32.2 `_classify`/`run_slice_job` signatures + call site unchanged).

### AC-9 — Settings slot `slicer_estimate_store_dir` + env/compose alignment + NFR20-CONTAINER-1 grep invariant

- Append ONE settings slot to `apps/api/app/core/config.py` (mirroring the Story 32.2 append pattern, with an inline `because "…"` contract comment per AC-11): `slicer_estimate_store_dir` (sourced `SLICER_ESTIMATE_STORE_DIR`), default under `portal_content_dir` (e.g. `/data/content/slicer/estimates`), container-internal — NEVER a `/mnt/c`/Fenrir/`.exe` literal.
- Document it in `infra/env.example` AND wire it into the `infra/docker-compose.yml` `api` + `arq-worker` env blocks AND (since the parsing sink runs inside the `slicer-worker`) note it as a slicer-worker-runtime var, so `infra/scripts/check-settings-env-compose.py` stays green (the drift gate that bit Story 32.1/32.2 at pre-push).
- **Grep invariant (NFR20-CONTAINER-1):** `grep -rniE "/mnt/c|fenrir|\.exe|[Ww]indows" apps/api/app/modules/slicer/ apps/api/app/core/config.py` returns **ZERO** path/exe literal matches (the new parser/store/sink files included).

**Tests (red→green):** `test_config.py` default-value test for `slicer_estimate_store_dir`; `test_no_bench_or_windows_path_literal_in_slicer_module` extended to cover the new files; run `infra/scripts/check-settings-env-compose.py` → OK.

### AC-10 — Observability per the logging contract (NFR20-OBS-1); g-code NEVER logged in full

Reuse the Story 32.2 instrumentation pattern (`worker_job._emit_completion` / OTel span / GlitchTip breadcrumb):

- One structured line on estimate persist: `stl_hash`, `bundle_hash`, `estimate_status` (`fresh`/`failed`), `orca_version`, and on failure `estimate_failure_reason`. Carry the `labels.*` tag shape already used by the slicer module.
- **GlitchTip breadcrumb** on a parse `failed` (category `slicer`, level `error`, with `stl_hash`/`bundle_hash`/`reason` — no g-code body).
- **g-code is parse-and-discard and is NEVER logged in full** (it is large + derivable) — logs may carry the metadata-line *count* or the parsed scalar fields, never the raw g-code body. The parse failure `detail` may name *which* line was missing, never dump the file.

**Tests (red→green):** `test_estimate_persist_emits_structured_tags`; `test_parse_failure_emits_failure_reason_and_breadcrumb`; `test_full_gcode_never_appears_in_logs`.

### AC-11 — Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

Every literal below carries an inline `because "…"` contract comment pointing to the **contract it serves**, not to a peer usage or a framework default:

| Literal | Location | Contract pointed to |
|---|---|---|
| each g-code metadata key token (`estimated printing time`, `filament used [g]`, `filament used [cm3]`, `filament used [mm]`, `total filament cost`, `{filament,print,printer}_settings_id`) | `gcode_parse.py` | because **"the proven OrcaSlicer 2.3.2 g-code metadata footer field names (PRD § Init 20 feasibility); the parser's contract IS the real Orca output, confirmed against the Story 32.2 in-container PLA/TPU slice g-code"** |
| time-unit multipliers `86400` / `3600` / `60` / `1` | `gcode_parse.py` | because **"the d/h/m/s grammar of Orca's `estimated printing time` line — the time-format contract, not arbitrary"** |
| `<hash[:2]>` estimate-store fan-out prefix length | `estimate_store.py` | because **"hash-prefix fan-out mirrors `stl_cache`/`bundle_store` (Decision AI/AH) to bound per-directory entry count"** |
| the `<stl_hash>/<bundle_hash>.json` two-level key layout | `estimate_store.py` | because **"the `(stl_hash, bundle_hash)` cache key is the complete reproducibility tuple (Decision AJ); grouping by `stl_hash` lets Story 32.4 enumerate the sibling estimates a bundle re-tune invalidates"** |
| required-vs-optional metadata-field split (time/g/mm/cm3 fatal; cost/settings_ids non-fatal) | `gcode_parse.py` | because **"cost is informational + may be absent without a spool price; attribution degrades but the numbers stay valid — FR20-ESTIMATE-1 numerics are the load-bearing fields, cost/attribution are not"** |

There is **no arbitrary TTL / staleness / timeout constant in this story** — staleness *transitions* and any recompute budget are Story 32.4; 32.3 only stores the `status` field. If a reviewer finds a bare magic number without a contract comment, it is a P1 fix-up.

### AC-12 — Determinism gate (NFR20-DETERMINISM-1)

After this story lands, three consecutive `pytest apps/api/tests/test_slicer*.py -v` runs return identical pass counts (no flakes). The parser is deterministic by construction (pure text→struct, no clock/random/subprocess); `computed_at` is the only non-deterministic field and is excluded from every assertion (frozen or ignored). The estimate write is idempotent on `(stl_hash, bundle_hash)` (AC-6). Coverage: T-DET.

### AC-13 — Scope fence: parser / schema / cache only; explicit dev-story boundaries

- **Zero** changes under `apps/web/` (the `PrintIntentPreset` selector + estimate display + soft-fail/warning/failure UI is Story 32.6).
- **Zero** new route mounting: `apps/api/app/main.py:_PUBLIC_ROUTES` + `apps/api/app/router.py` byte-identical to pre-story state (grep/diff invariant). This story exposes **no HTTP surface** — the estimate read/display API is Story 32.6.
- **Zero** Alembic migration: the estimate cache is an **append-only file store** (per SCP "No DB schema; append-only estimate records" + `bundle_store.py:4`), NOT a table. No new file under `apps/api/migrations/versions/`.
- **No invalidation / recompute / cost-arithmetic** (Story 32.4): no `stale`/`queued` transition logic, no recompute queue, no Orca-upgrade/bundle-re-tune trigger table, no `cost = mass × price/gram` computation (32.3 only *carries* the mass + cost fields). The `EstimateStatus` enum *values* `stale`/`queued` exist (AC-1) but nothing in 32.3 *sets* them.
- **No Spoolman override implementation** (Story 32.5): 32.3 consumes the `bundle_hash` already produced; it does not read Spoolman, map `filament.extra`, or compute `spoolman_overrides_ref`.
- **No re-slice / no subprocess / no real Orca**: the parser is pure over text; the slice itself is Story 32.2.
- **No `SliceOutcome` reshape** (Story 32.2 contract): `SliceStatus`/`SliceFailureReason`/`SliceOutcome` field sets unchanged; `_classify`/`run_slice_job` orchestration byte-identical (AC-8).
- **No new heavy Python dependency** in `apps/api/pyproject.toml`: parsing is stdlib (`re`); the store is stdlib (`json`, `pathlib`, `hashlib`/`os` reused from the 32.1/32.2 pattern).
- **No g-code retention** beyond the in-job parse (OD-5; the 32.2 scratch-dir context manager still deletes it).

**Tests/grep:** `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` returns zero lines; no new `apps/api/migrations/versions/` file; `apps/api/pyproject.toml` dependency block unchanged; the `SliceOutcome`-unchanged assertion from AC-1.

## Tasks / Subtasks

> **TDD discipline (AGENTS.md § Execution discipline):** every logic-bearing task writes the failing test FIRST (red), then implements to green, then refactors. The parser + time-normalization + store + dedup + classification logic is the red→green core; there is **no subprocess and no real Orca in this story** (pure parse + local file store), so the entire suite runs deterministically in CI with no env gate.

- [ ] **T1** (AC-1) — Extend `models.py` with the estimate surfaces *(red→green)*
  - [ ] T1.1 Failing tests: `EstimateStatus`/`EstimateFailureReason` values; `EstimateRecord` failed-record `None`-not-`0`; reuses `SliceWarning`; `SliceOutcome` field set unchanged.
  - [ ] T1.2 Append `EstimateStatus`, `EstimateFailureReason`, `EstimateRecord` to `models.py` (NO `SliceOutcome` change).
- [ ] **T2** (AC-2, AC-3, AC-4) — Pure g-code parser + time normalization *(red→green)*
  - [ ] T2.1 Failing tests: parse all fields (PLA + TPU fixtures), settings-id dequote, order-independence, purity; duration grammar edge cases; missing/garbled → classified failure, never silent zero; cost/settings_ids non-fatal.
  - [ ] T2.2 Implement `gcode_parse.py` (`parse_gcode_metadata` + `parse_duration_to_seconds` + the required/optional split) with the AC-11 contract comments.
  - [ ] T2.3 Author `apps/api/tests/fixtures/slicer/gcode/{pla_standard,tpu_standard,missing_time,garbled}.gcode` from the documented bench metadata (NO real retained g-code — synthetic footers matching the proven Orca 2.3.2 line shapes).
- [ ] **T3** (AC-5, AC-6) — Append-only estimate store + dedup *(red→green)*
  - [ ] T3.1 Failing tests: write/read roundtrip, `<stl_hash>/<bundle_hash>` layout, malformed-hash rejection (both hashes), read-miss `None`, atomic write; fresh-rewrite no-op, non-fresh replace, `computed_at`-only-change-is-not-a-change.
  - [ ] T3.2 Implement `estimate_store.py` reusing `validate_content_hash` + the `bundle_store` atomic-write/first-write-wins pattern + the AC-6 dedup rule.
- [ ] **T4** (AC-7) — Cost-carry + attribution invariants *(red→green)*
  - [ ] T4.1 Failing tests: record carries `filament_g` + `filament_cost` (the 32.4 arithmetic seam); `settings_ids` attribution present on success; attribution invariant.
  - [ ] T4.2 Confirm the `EstimateRecord` assembly populates these (covered by T1/T2 implementation; add the explicit invariant tests).
- [ ] **T5** (AC-8) — Parser-sink + persist integration via the 32.2 seam *(red→green)*
  - [ ] T5.1 Failing tests: `ParsingGcodeSink` stashes the parse result + retains no g-code post-job; `slice_estimate` persists `fresh` on ok/warning, `failed` on parse failure, **nothing** on invocation failure; `_classify`/`run_slice_job` orchestration unreshaped.
  - [ ] T5.2 Implement `ParsingGcodeSink`; edit ONLY the `slice_estimate` arq entry in `worker_job.py` (construct sink → pass `gcode_sink=` → assemble+persist after `run_slice_job`); wire `ctx["estimate_store"]` in `worker.py` `on_startup`. Leave `_classify`/`run_slice_job` byte-identical.
- [ ] **T6** (AC-9) — Settings slot + env/compose alignment + grep invariant
  - [ ] T6.1 Append `slicer_estimate_store_dir` to `config.py` (with `because` comment); `test_config.py` default test.
  - [ ] T6.2 Document in `infra/env.example` + wire into `infra/docker-compose.yml` env blocks; run `infra/scripts/check-settings-env-compose.py` → OK.
  - [ ] T6.3 Extend the grep-invariant test to the new slicer files (no `/mnt/c`/Fenrir/`.exe`/Windows path literal).
- [ ] **T7** (AC-10) — Observability *(red→green)*
  - [ ] T7.1 Failing tests: estimate-persist structured tags, parse-failure reason tag + breadcrumb, full g-code never in logs.
  - [ ] T7.2 Implement the structured-log line + OTel attributes + GlitchTip breadcrumb in the `slice_estimate` persist path (reuse the 32.2 `_emit_completion` shape).
- [ ] **T-DET** (AC-12) — Determinism gate: 3× consecutive identical pytest pass counts on the slicer suite; document in Dev Agent Record (`computed_at` excluded).
- [ ] **T8** (AC-13) — Scope fence *(grep/diff)*
  - [ ] T8.1 `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` → 0 lines; no new `apps/api/migrations/versions/` file; `pyproject.toml` deps unchanged; `SliceOutcome` field set unchanged.
- [ ] **T9** (full quality gate) — `ruff format --check` + `ruff check` clean on `apps/api/`; `pytest apps/api/tests/ -v` green = baseline + new slicer estimate cases (no env-gated/real-Orca test in this story — fully deterministic). No vitest/Playwright (backend only).
- [ ] **T10** (handoff) — dev-story flips `ready-for-dev → review`; code-review owns `→ done`. **Commit / ff-merge / deploy NOT performed by dev-story — controller-owned (ITCM).** Story branch: `feat/E32.3-gcode-parse-estimate-cache-schema` (created by dev-story at start, NOT now). Suggested commit scope when the controller commits: `feat(api): g-code metadata parser + EstimateRecord append-only cache (Story 32.3, Init 20)`.

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 20 — FR20-ESTIMATE-1 (parse half + the typed `EstimateRecord` field list), FR20-CACHE-1 (cache keyed `(stl_hash, bundle_hash)` + dedup + explicit `status`), NFR20-ATTRIBUTION-1 (`settings_ids`), NFR20-REPRODUCIBLE-1 (the cost-carry rationale 32.4 consumes), NFR20-OBS-1, NFR20-DETERMINISM-1.
- **Architecture:** `architecture.md` § Initiative 20 — Decision **AJ** (cache / invalidation / cost arithmetic: `EstimateRecord` keyed `(stl_hash, bundle_hash)`; the recompute-trigger table is *consumed* by 32.4 but its key shape + the cost-only-arithmetic rationale are defined here; staleness explicit never silent). Decision AH (Story 32.1) supplies `bundle_hash`; Decision AI (Story 32.2) supplies the g-code + `SliceOutcome`.
- **Epics:** `epics.md` § Initiative 20 § Story 32.3 (sketch + the `EstimateRecord` field list + the test-target sketch).
- **SCP:** `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AJ) + § 4.3 (Story 32.3 sketch: "Estimate parse + cache schema + cost-carry fields").
- **Story 32.2 (done):** `_bmad-output/implementation-artifacts/32-2-slicer-worker-container-cli-invoke-classify.md` — supplies the `GcodeSink` seam (AC-5: "32.3 slots in without reshaping `worker_job.py`"), the `SliceOutcome`/`SliceWarning`/`SliceStatus`/`SliceFailureReason` models, `worker.py` `SlicerWorkerSettings.on_startup` ctx wiring, `stl_cache.validate_content_hash`/`is_content_hash`, and `cli.parse_slice_warnings`. The `models.py` docstring (lines 156-158, 180-185) explicitly reserves the `parse_failure` reason for this story.
- **Story 32.1 (done):** `_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md` — supplies the `bundle_store.py` append-only / atomic-write / first-write-wins pattern `EstimateStore` mirrors, and the `created_at`-excluded-from-identity discipline `computed_at` follows.
- **Memory entries (read before implementation):**
  - `[[feedback_scp_pre_enumeration_phase]]` — § A pre-enumeration (below), § B cache-coherence table (below), § C magic-constant contract pointing (AC-11). This story deliberately has **no arbitrary TTL/timeout constant** (staleness is 32.4) — the § C trap does not bite here.
  - `[[feedback_codex_model_routing]]` — Story 32.3 review-tier routing (single-adjacency: data-integrity; recommended `gpt-5.5`; controller confirms).
  - `[[feedback_itcm_autonomous_mode]]` — dev-story execution is controller-routed; this spec authoring does not itself start dev-story.

### Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

Run 2026-06-01 against post-Story-32.2 repo state (`main` @ `da2f593`):

1. **Files reused / extended (existing — DO NOT duplicate):**
   - `apps/api/app/modules/slicer/models.py` — `SliceWarning` (reused verbatim on `EstimateRecord.warnings`), `SliceOutcome`/`SliceStatus`/`SliceFailureReason` (read, NOT reshaped). T1 APPENDS the estimate surfaces to this one file.
   - `apps/api/app/modules/slicer/worker_job.py` — the `GcodeSink` seam + `discard_sink` + the `slice_estimate` arq entry. T5 supplies a real `ParsingGcodeSink` and edits ONLY `slice_estimate` (assemble+persist); `_classify`/`run_slice_job` stay byte-identical (32.2 AC-5).
   - `apps/api/app/modules/slicer/worker.py` — `SlicerWorkerSettings.on_startup` already wires `stl_cache`/`bundle_store`/`cli` into `ctx`. T5.2 ADDS `ctx["estimate_store"]` the same way.
   - `apps/api/app/modules/slicer/stl_cache.py` — `validate_content_hash`/`is_content_hash` (the 64-lowercase-hex path-safety gate). `estimate_store.py` REUSES these for BOTH hashes; does NOT re-author the gate.
   - `apps/api/app/modules/slicer/bundle_store.py` — the append-only fan-out store + `_atomic_write` first-write-wins pattern. `estimate_store.py` MIRRORS this shape (no DB, per SCP).
   - `apps/api/app/modules/slicer/cli.py` — `parse_slice_warnings` already extracts warnings into `SliceOutcome.warnings`; 32.3 carries those onto `EstimateRecord`, it does NOT re-parse warnings from g-code.
   - `apps/api/app/core/config.py` — `Settings` (carries `slicer_*` slots + `portal_content_dir`). T6 APPENDS `slicer_estimate_store_dir` in the same pattern.
2. **NEW (Story 32.3 owns):** `apps/api/app/modules/slicer/gcode_parse.py` (pure parser + `ParsingGcodeSink`) + `apps/api/app/modules/slicer/estimate_store.py` (append-only cache) + `apps/api/tests/test_slicer_estimate.py` (parser + store + sink + persist cases) + `apps/api/tests/fixtures/slicer/gcode/*.gcode` (synthetic footers from documented bench metadata; NO real g-code retained).
3. **MODIFIED (append-only / minimal):** `apps/api/app/modules/slicer/models.py` (estimate surfaces) + `apps/api/app/modules/slicer/worker_job.py` (`slice_estimate` arq entry ONLY) + `apps/api/app/modules/slicer/worker.py` (`ctx["estimate_store"]` wiring) + `apps/api/app/core/config.py` (one slot) + `apps/api/tests/test_config.py` (default) + `infra/env.example` (env) + `infra/docker-compose.yml` (env refs for the gate).
4. **Contracts UNTOUCHED:** `_PUBLIC_ROUTES`, `apps/api/app/router.py`, `share/router.py` (no routes — AC-13). `SliceOutcome`/`_classify`/`run_slice_job` (32.2 contract — AC-8). `apps/api/app/modules/spools/*` (Story 32.5). `workers/render/*`, `apps/api/app/workers/*`. No Alembic. No `apps/web/`. `~/repos/configs/*` (HC2 — and unlike 32.2 there is **no** configs-side gate; the container already exists).

**Net scope:** ~2 new module files + 1 new test file + small synthetic g-code fixtures + 6 modified files (5 append-only, 1 thin arq-entry edit) + 0 Alembic + 0 routes + 0 new heavy deps + 0 configs-repo edits + 0 subprocess.

### Cache-coherence / boundary enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

Backend file-store story (no React Query / TanStack cache), so the FE cache-topology table does not apply. The coherence concerns this story owns:

| Concern | Source: Story 32.3 (this story) | Related surface |
|---|---|---|
| Estimate key completeness | `EstimateRecord` keyed `(stl_hash, bundle_hash)` — the complete reproducibility tuple; `bundle_hash` already folds `orca_version` + the Spoolman-override set (Story 32.1) | Story 32.4 invalidation/recompute keys off this exact tuple; if 32.3 keyed on a partial id, a re-tune/Orca-upgrade would alias an old estimate (R9 "stale served as fresh"). The store layout groups by `stl_hash` so 32.4 can enumerate sibling estimates affected by a bundle re-tune. |
| Write-time dedup vs recompute-queue dedup | 32.3 owns **write-time** dedup (`fresh` re-write = no-op, AC-6) | The recompute **queue** dedup (`_job_id`, Story 32.2 enqueue) + the `stale`/`queued` *transitions* are Story 32.4. Two distinct dedups on the same key — name the split so 32.4 doesn't re-implement write-time dedup. |
| Parse-failure axis vs invocation-failure axis | parse failures classified on `EstimateRecord` (`EstimateStatus.failed` + `EstimateFailureReason`) | Slice-**invocation** failures stay on `SliceOutcome` (`SliceStatus.failed` + `SliceFailureReason`, Story 32.2). Two orthogonal failure axes; 32.6 reads both (an absent estimate + a failed `SliceOutcome` = "couldn't slice"; a `failed` `EstimateRecord` = "sliced but couldn't parse"). |
| g-code lifetime | parse happens **in-job** in `ParsingGcodeSink` while the 32.2 scratch dir is alive; nothing g-code-shaped is persisted | The 32.2 context-managed scratch dir still deletes the temp g-code at block exit (AC-5); only the typed `EstimateRecord` crosses the job boundary. |
| Cost-carry seam | `filament_g` + `filament_cost` persisted | Story 32.4 recomputes `cost = mass × price/gram` from the carried mass without re-slicing (OD-7); 32.3 must carry BOTH or 32.4 is forced to re-slice (the R1 self-DoS the rule exists to prevent). |

Decision rule: the estimate cache key MUST be the content-hash-complete `(stl_hash, bundle_hash)` tuple (both `validate_content_hash`-gated); the two failure axes stay orthogonal (no `parse_failure` bolted onto `SliceFailureReason`); the cost-carry fields are load-bearing for 32.4 and are non-optional on a successful record.

### Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` § C)

All literals in AC-11 carry an inline `because "…"` comment pointing to the contract they serve. The g-code metadata key tokens + the d/h/m/s multipliers point to the **real OrcaSlicer 2.3.2 output format** (the parser's contract is the bench g-code, confirmed via the Story 32.2 in-container slice). The fan-out prefix + the two-level key layout point to the `stl_cache`/`bundle_store` hash-layout convention + the Decision AJ key shape. The required-vs-optional field split points to the FR20-ESTIMATE-1 load-bearing-numerics contract. **This story introduces no arbitrary TTL/staleness/timeout constant** — staleness transitions + any recompute budget are Story 32.4 — so the "arbitrary default, replace at benchmark" framing that 32.2's timeouts needed does not apply here.

### Threat-vector enumeration

Story 32.3 routes to the higher review tier for **data-integrity** adjacency only (NOT runtime-boundary, NOT auth-boundary). Survey:

- **No HTTP surface, no auth, no CSRF, no public-bypass family touch** — zero routes mounted (AC-13).
- **No subprocess / no real Orca / no STL mesh handling** — the runtime-boundary risk class that put Story 32.2 in the higher tier is absent here; 32.3 is a pure text parser + a local append-only JSON file write.
- **Data-integrity (the real risk class):** a mis-parsed metadata line, a wrong `3h35m47s→seconds` normalization, or a silent zero on a missing line → a plausible-but-wrong estimate propagating into 32.4 recompute + 32.6 display, and a user could print/quote against it. Mitigated by AC-4 (classified failure, never silent zero; `None`-not-`0` on failure) + the attribution invariant (AC-7, `settings_ids` so a bad estimate is at least traceable to its profile) + the pure-deterministic parser (AC-2/AC-12).
- **Path-safety:** the estimate-store path is built only from two `validate_content_hash`-gated hashes (64 lowercase hex) — no user-controlled path component, no traversal vector (reuses the Story 32.2 review-fix #2 gate).
- **No PII** — Orca g-code metadata (times, masses, profile-id strings) is not personal data.
- **g-code logging:** AC-10 forbids full g-code in logs (large, derivable; parse-and-discard); the parse-failure `detail` names which line, never dumps the body.

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/slicer/gcode_parse.py` | NEW | T2 — pure `parse_gcode_metadata` + `parse_duration_to_seconds` + `ParsingGcodeSink` (parse-in-job) |
| `apps/api/app/modules/slicer/estimate_store.py` | NEW | T3 — append-only content-addressed `(stl_hash, bundle_hash)` cache (write/read + dedup, mirrors `bundle_store`) |
| `apps/api/app/modules/slicer/models.py` | MODIFY (append) | T1 — `EstimateStatus` / `EstimateFailureReason` / `EstimateRecord` (NO `SliceOutcome` change) |
| `apps/api/app/modules/slicer/worker_job.py` | MODIFY (thin) | T5.2 — `slice_estimate` arq entry ONLY: build sink → pass `gcode_sink=` → assemble+persist. `_classify`/`run_slice_job` byte-identical |
| `apps/api/app/modules/slicer/worker.py` | MODIFY (append) | T5.2 — `ctx["estimate_store"] = EstimateStore(...)` in `on_startup` |
| `apps/api/app/core/config.py` | MODIFY (append slot) | T6.1 — `slicer_estimate_store_dir` (with `because` comment) |
| `apps/api/tests/test_slicer_estimate.py` | NEW | T1–T7, T-DET pytest cases (pure; no env gate, no real Orca) |
| `apps/api/tests/fixtures/slicer/gcode/*.gcode` | NEW | synthetic metadata footers from documented bench values (NO real g-code retained) |
| `apps/api/tests/test_config.py` | EXTEND | T6.1 — default-value coverage |
| `infra/env.example` | EXTEND | T6.2 — `SLICER_ESTIMATE_STORE_DIR` |
| `infra/docker-compose.yml` | MODIFY | T6.2 — env refs to satisfy `check-settings-env-compose.py` |

**Files this story MUST NOT touch:** `apps/api/app/main.py` (`_PUBLIC_ROUTES`), `apps/api/app/router.py`, `apps/api/app/modules/share/router.py`, `apps/api/app/modules/spools/*` (Story 32.5), `workers/render/*`, `apps/api/app/workers/*`, `apps/web/`, `apps/api/migrations/`, `~/repos/configs/*` (HC2 — no configs gate in this story), and the `_classify`/`run_slice_job` orchestration + `SliceOutcome` model (Story 32.2 contract — AC-8).

### Project Structure Notes

- OD-9-resolved: the parser + store join the existing `apps/api/app/modules/slicer/` bounded-context module (same package as the 32.1 resolver + 32.2 worker). No new top-level package; no `estimates` subpackage (the repo convention keeps the bounded context flat — `models`/`resolver`/`cli`/`worker_job`/`stl_cache`/`bundle_store`/`gcode_parse`/`estimate_store` all siblings).
- The estimate cache is the SECOND append-only file store in the module (after `bundle_store`), deliberately mirroring it (no DB, per SCP) — the runtime is not novel.
- The frontend `apps/web/src/modules/estimates/` surface (OD-9) is Story 32.6, NOT this story.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 20 — Decision AJ (cache key `(stl_hash, bundle_hash)`, recompute-trigger table consumed by 32.4, cost-only-arithmetic rationale, staleness-explicit-never-silent)]
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 20 — FR20-ESTIMATE-1 (parse half + `EstimateRecord` fields) + FR20-CACHE-1 + NFR20-ATTRIBUTION-1 + NFR20-REPRODUCIBLE-1 + NFR20-OBS-1 + NFR20-DETERMINISM-1]
- [Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 20 § Story 32.3]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3]
- [Source: `_bmad-output/implementation-artifacts/32-2-slicer-worker-container-cli-invoke-classify.md` — `GcodeSink` seam (AC-5), `SliceOutcome`/`SliceWarning`, reserved `parse_failure`, `validate_content_hash`, `worker.py` ctx wiring]
- [Source: `_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md` — `bundle_store` append-only/atomic-write pattern, `created_at`-excluded-from-identity discipline]

## Dev Agent Record

### Agent Model Used

_To be filled by `bmad-dev-story` at implementation time._

### Debug Log References

### Completion Notes List

### File List

### Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-06-01 | 0.1 | Story 32.3 spec authored (`bmad-create-story`); status `backlog → ready-for-dev`. App-side g-code parser + `EstimateRecord` schema + append-only `(stl_hash, bundle_hash)` cache + cost-carry; no routes / no Alembic / no `SliceOutcome` reshape / no configs gate. | Claude (`bmad-create-story`) |
