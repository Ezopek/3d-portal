# Story 32.2: Containerized headless OrcaSlicer worker — job shape + real CLI invoke + failure classification

Status: ready-for-dev

## Story

As an **autonomous portal backend that holds resolved, CLI-acceptable slice bundles (Story 32.1) but cannot yet turn an STL into an estimate**,
I want **an app-side slicer-worker subsystem in the existing `apps/api/app/modules/slicer/` package that takes an idempotent `(stl_ref, bundle_ref)` job, pulls the content-hashed STL from the `.190`-mirrored cache + the resolved triple from the Story 32.1 bundle store, runs a real headless OrcaSlicer `--info` manifold pre-check then a headless CLI slice with that triple, emits g-code to a temp path it parses-and-discards in Story 32.3 (no durable g-code retention here), and classifies every outcome (success, non-blocking warning, or a typed failure: non-manifold, non-zero exit, CLI-rejected profile, missing STL/bundle, timeout) under a bounded slice concurrency cap + a bounded slice-wall-time timeout**,
so that **Story 32.3 has a g-code source + a typed `SliceOutcome` to parse into an `EstimateRecord`, Story 32.4 can key invalidation/recompute on the same `(stl_hash, bundle_hash)` job, an unreachable worker or a bad mesh fails loud + classified (never a plausible-but-wrong silent zero — FR20-FAILURE-1), and the heavy minutes-long slice runs in a dedicated container with NO production dependency on Fenrir / Windows / `/mnt/c` (NFR20-CONTAINER-1) and cannot starve the API/render workers (NFR20-RESOURCE-1)**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AI) + § 4.3 (Epic E32 story sketch).
Architectural anchor: Decision **AI** (slicer-worker container — runtime boundary, `(stl_ref, bundle_ref)` job IO, `--info` pre-check + headless slice, STL cache layout, warning/failure classification, bounded concurrency, configs/app boundary HC2) per `architecture.md` § Initiative 20.
Realizes **FR20-ESTIMATE-1** (slice half) + **FR20-FAILURE-1** (worker classification half) + **NFR20-CONTAINER-1** + **NFR20-RESOURCE-1** (concurrency cap) + **NFR20-OBS-1** (slicer-worker instrumentation). Consumes the `SlicerProfileBundle` + `bundle_hash` Story 32.1 produced; feeds the g-code + `SliceOutcome` Story 32.3 parses.
OD-gate context: authored after the **2026-05-31 OD-gate resolution** (OD-2 dedicated slicer-worker container; OD-5 leaning **parse-and-discard** — NO g-code retention; OD-6 small bounded slice concurrency; OD-8 worker reads the `.190`-mirrored catalog STL, never Windows directly; OD-9 dedicated `slicer` module — see `prd.md` § Initiative 20 § Open decisions). **Authoring this spec to `ready-for-dev` does NOT authorize dev-story execution — implementation remains gated on an explicit operator go per SCP § 5, AND additionally on the configs-side `slicer-worker` container recipe coordination gate (AC-12).**
**Codex tag (recommended `gpt-5.5`; controller confirms — route per `[[feedback_codex_model_routing]]`):** this story is **dual-adjacency**. (1) **Runtime-boundary / resource-safety:** it spawns a real OrcaSlicer subprocess over an STL mesh and bounds it with a concurrency cap + a wall-time timeout — an unbounded/leaky invocation is a self-inflicted CPU/disk DoS on `.190` (R1/R3 risk class), and the NFR20-CONTAINER-1 no-bench-path invariant is a deployment-boundary guarantee. (2) **Data-integrity:** a misclassified outcome (a failed/timed-out slice surfaced as a valid estimate, or a silent zero) produces a plausible-but-wrong number downstream. Both warrant the higher review tier. No public-route / auth-bypass adjacency (this story mounts zero HTTP routes — AC-13).

## Acceptance Criteria

### AC-1 — Worker subsystem extends the existing OD-9 `slicer` module (no parallel package, no router)

The slice subsystem ships as **new files inside the existing** `apps/api/app/modules/slicer/` package (Story 32.1 owns `models / merge / resolver / overrides / validation / bundle_store`):

- `cli.py` — the Orca command builder + the subprocess invocation layer (`--info` pre-check argv + slice argv + a timeout-bounded runner). **Reuses/extends the Story 32.1 `validation.build_orca_smoke_command` seam** rather than re-authoring the argv shape; the Orca entrypoint is read from a settings slot (AC-9), never a literal.
- `stl_cache.py` — the content-hashed STL cache addressing + read (AC-4).
- `worker_job.py` — the arq task entry point (`slice_estimate`) that orchestrates: load bundle → load/locate STL → `--info` pre-check → slice → classify → emit `SliceOutcome` → discard temp g-code (AC-2, AC-3, AC-5, AC-6).
- `worker.py` — a `SlicerWorkerSettings` arq entrypoint (functions=`[slice_estimate]`, dedicated `queue_name`, `max_jobs` concurrency cap, `redis_settings`) — the entry the **configs-side** `slicer-worker` container runs (`arq app.modules.slicer.worker.SlicerWorkerSettings`). Mirrors `apps/api/app/workers/__init__.py:WorkerSettings` + `workers/render/render/worker.py` shape.
- `enqueue.py` (or an enqueue helper alongside `worker_job.py`) — the API-side enqueue function that computes/ensures `stl_hash`, populates the STL cache from the mirrored catalog copy, and enqueues `(stl_hash, bundle_hash)` deduped on the key.
- **Extend `models.py`** (Story 32.1's file) with the slice result types: `SliceStatus` (`ok` / `warning` / `failed`), `SliceFailureReason` (`StrEnum`: `non_manifold`, `non_zero_exit`, `cli_rejected_profile`, `missing_stl`, `missing_bundle`, `timeout`), `SliceWarning`, and `SliceOutcome` (status + optional reason + warnings + temp-g-code ref + timing). **Do NOT** add an `EstimateRecord` here — that typed-estimate shape is Story 32.3.

**No `router.py`, no route mount** in this story (the estimate request/display surface is Stories 32.3/32.6). The package stays a top-level bounded-context module (OD-9), not folded into a `requests` v2 slot.

### AC-2 — Idempotent `(stl_ref, bundle_ref)` 2-tuple job; nothing else in the payload

- The arq job payload is the **2-tuple only**: `(stl_hash, bundle_hash)` (`stl_ref` = the content hash of the STL; `bundle_ref` = the Story 32.1 `bundle_hash`). The worker pulls the STL from the cache (AC-4) and the resolved triple from the bundle store (AC-4) — **no profile JSON, no STL bytes, no file paths travel in the payload** (Decision AI § Job contract).
- **Idempotent on the key:** the job is enqueued with a deterministic `_job_id = f"slice:{stl_hash}:{bundle_hash}"` so a duplicate enqueue while one is queued/running is a de-dup no-op (arq drops the duplicate job_id). Re-running a completed job for the same key is safe/repeatable (pure function of the two content-addressed inputs + pinned `orca_version`).
- The job is enqueued to the **dedicated slicer queue** (AC-10 queue-name constant), NOT the render default `arq:queue` nor `arq:api` — so the slicer pool never grabs a `render_model` / `generate_thumbnail` job and rejects it (the cross-queue-grab bug documented in `apps/api/app/workers/__init__.py`).

**Tests (red→green; arq invocation mocked, real Orca NOT run in CI):** `test_enqueue_uses_stl_bundle_tuple_job_id_for_dedupe`; `test_enqueue_targets_dedicated_slicer_queue`; `test_job_payload_carries_only_the_two_hashes`.

### AC-3 — Real headless Orca CLI invocation: `--info` manifold pre-check BEFORE the slice

`cli.py` implements the real invocation contract (the seam Story 32.1 only specified as `ORCA_SMOKE_COMMAND_TEMPLATE` / `build_orca_smoke_command`):

- **Pre-check:** run Orca `--info` over the STL first (cheap; reports manifold yes/no + facet count + volume per the proven bench behavior). Parse the `--info` output; **`manifold: no` ⇒ fast-fail `non_manifold`** WITHOUT attempting the full slice (saves the minutes-long slice on a known-bad mesh — Decision AI § Failure classification + brainstorm § "Validation pre-check").
- **Slice:** on a manifold mesh, run the headless slice with the resolved triple JSONs (materialized to temp files for `--load-settings "<machine>;<process>"` + `--load-filaments "<filament>"`) + the STL, emitting g-code to a temp path. The slice argv is built by extending the Story 32.1 `build_orca_smoke_command` shape (same `orca` entrypoint + `--load-*` flags) — single source of truth for the argv, no divergent re-implementation.
- The **Orca entrypoint** is resolved from a settings slot (AC-9), defaulting to a **container-internal** path (the `--appimage-extract` entrypoint inside the configs-side container), NEVER a `/mnt/c` / Fenrir / `.exe` literal.
- **Real Orca is NOT executed in CI** (no AppImage in CI). The unit suite injects a **fake/mocked subprocess runner** (a `subprocess`-shaped seam, e.g. an injected `runner` callable) so happy/warning/each-failure path is exercised deterministically. The real run is verified out-of-band on the configs-side container (AC-12) + an env-gated bench test mirroring Story 32.1's `ORCA_SMOKE_TEST` pattern (`@pytest.mark.skipif(os.environ.get("ORCA_SMOKE_TEST") != "1", ...)`).

**Tests (red→green):** `test_info_precheck_runs_before_slice`; `test_non_manifold_info_fast_fails_without_slicing` (asserts the slice runner is NEVER called); `test_slice_argv_reuses_validation_command_shape`; `test_orca_entrypoint_read_from_settings_not_hardcoded`; env-gated `test_real_orca_slice_smoke` (skipped unless `ORCA_SMOKE_TEST=1`).

### AC-4 — Resolved triple from the 32.1 bundle store; STL content-hash cache `<cache_root>/stl/<hash[:2]>/<hash>.stl`; `.190`-mirrored source boundary

- **Bundle input:** the worker loads the `SlicerProfileBundle` (and thus the `ResolvedTriple`) for `bundle_hash` from the Story 32.1 append-only bundle store (`<bundle_root>/bundles/<hash[:2]>/<hash>.json`, `slicer_bundle_store_dir`). A `bundle_hash` with no bundle file ⇒ classified `missing_bundle` failure (the resolver should have persisted it; a miss is an integrity fault, never a silent default).
- **STL cache:** the worker reads the STL from a **content-hashed cache** at `<cache_root>/stl/<hash[:2]>/<hash>.stl` (hash-prefix fan-out mirroring the render/STL layout — Decision AI). A cache miss ⇒ classified `missing_stl` failure.
- **Source/cache boundary (OD-8):** the cache is populated **API-side at enqueue** by copying the `.190`-**mirrored** catalog STL (the portal-content copy at `models/{model_id}/files/{file_uuid}.stl`) into the content-addressed cache path. The worker **only reads the mirrored cache** — it NEVER reads Windows / `/mnt/c` / Fenrir directly (NFR20-CONTAINER-1 / OD-8). The cache root is a settings slot (AC-9), defaulting under `portal_content_dir`.
- **No STL bytes in the payload** (AC-2): the content hash is the only reference that crosses the queue.

**Tests (red→green):** `test_loads_resolved_triple_from_bundle_store_by_hash`; `test_missing_bundle_classifies_missing_bundle`; `test_stl_cache_path_is_hash_fanout_layout`; `test_cache_miss_classifies_missing_stl`; `test_enqueue_populates_cache_from_mirrored_catalog_copy`; `test_worker_never_reads_windows_or_fenrir_path` (the cache-read path takes only the cache root + hash).

### AC-5 — Temp g-code output; parse-and-discard deferred to 32.3; ZERO durable g-code retention in this story

- The slice writes g-code to a **temp path** (e.g. `tempfile`-managed, under a slicer scratch dir), captured in the `SliceOutcome` as a transient ref for the in-job hand-off to the (Story 32.3) parser seam.
- **OD-5 parse-and-discard:** this story does **NOT** parse the g-code into typed estimate fields (that pure parser is Story 32.3) and does **NOT** retain g-code beyond the worker job lifetime. The temp g-code file is **deleted at job end** (success OR failure), via a `try/finally` / context-managed scratch dir — no g-code survives in any durable store, log, or volume.
- The hand-off seam to Story 32.3 is designed now (a `GcodeSink`/parser-callable injection point, defaulting to a no-op/discard in this story) so 32.3 slots in without reshaping `worker_job.py`. With the default no-op sink, the job emits the `SliceOutcome` (status + warnings + reason) and discards.

**Tests (red→green):** `test_gcode_written_to_temp_path`; `test_temp_gcode_discarded_on_success`; `test_temp_gcode_discarded_on_failure`; `test_no_gcode_retained_in_durable_store_or_log`; `test_parser_sink_is_injected_default_noop` (proves the 32.3 seam is DI-clean and discards by default).

### AC-6 — Failure + warning classification (FR20-FAILURE-1 worker half): typed `SliceOutcome`, never a silent zero

`worker_job.py` returns a typed `SliceOutcome` (AC-1) classifying every outcome — never a bare `None`/0 a caller could misread as a valid estimate:

- **Warning (non-blocking):** slice succeeded + Orca emitted warnings (e.g. *floating cantilever*) → `status: warning`, warnings captured in `SliceOutcome.warnings`, the g-code/estimate is still valid (surfaced non-blocking by Story 32.6).
- **Failure** → `status: failed` + a machine-readable `SliceFailureReason`:
  - `non_manifold` — `--info` pre-check reports non-manifold (AC-3 fast-fail).
  - `non_zero_exit` — Orca slice exits non-zero.
  - `cli_rejected_profile` — Orca rejects the triple at load (should already be caught at Story 32.1 resolve-time validation, Decision AH § 5; re-classified here as defense-in-depth).
  - `missing_stl` / `missing_bundle` — cache/bundle-store miss (AC-4).
  - `timeout` — slice exceeded the wall-time budget (AC-7).
- **Scope note (seam to 32.3):** g-code **metadata parse failure** (missing/garbled `; estimated printing time` etc.) is classified by the Story 32.3 **parser**, not here — this story classifies the **invocation** outcome only. The shared `status: failed` + reason taxonomy is designed so 32.3 extends it (adds a `parse_failure` reason) without reshaping `SliceOutcome`.
- **Never silent:** a failed/timed-out slice NEVER returns success-with-zero; the worker emits `status: failed` so Story 32.6 can render "couldn't estimate, here's why".

**Tests (red→green; mocked runner, one per branch):** `test_warning_slice_is_non_blocking_warning_status`; `test_non_zero_exit_classifies_non_zero_exit`; `test_cli_rejected_profile_classifies_cli_rejected_profile`; `test_timeout_classifies_timeout`; `test_failure_never_returns_silent_zero`; (+ `non_manifold`/`missing_*` covered by AC-3/AC-4 tests).

### AC-7 — Bounded slice concurrency + bounded slice-wall-time timeout (NFR20-RESOURCE-1)

- **Concurrency cap:** `SlicerWorkerSettings.max_jobs` is a **small bounded cap** (default `1`) so a minutes-long CPU-heavy slice cannot starve the API/render workers on `.190` (NFR20-RESOURCE-1 / OD-6). The cap is configurable via a settings slot (AC-9) for the configs-side container to lift to `2` if `.190` headroom allows.
- **Timeout:** the slice subprocess runs under a bounded **wall-time** timeout; on expiry the process group is terminated and the outcome is classified `timeout` (AC-6). The timeout bounds **slice compute wall-time** (minutes), NOT the printed-part time (the proven PLA `3h35m` / TPU `8h06m` are *print* times, irrelevant to slice wall-time).
- **Timeout value is an explicit conservative default pending a benchmark, NOT a contractual constant** (per `[[feedback_scp_pre_enumeration_phase]]` § C — and explicitly avoiding the TB-016 "60s budget justified by happy-path size" anti-pattern): there is no measured slice-wall-time distribution yet. Default `SLICER_SLICE_TIMEOUT_SECONDS` to a conservative value (e.g. `900`) marked *"arbitrary safety ceiling — replace once the configs-side container R3 spike benchmarks real slice wall-time across the PLA/TPU/large-mesh corpus"*. The `--info` pre-check carries its own short timeout (e.g. `60`, same arbitrary-pending-benchmark framing).
- The dedup (`_job_id`, AC-2) complements the cap: identical `(stl_hash, bundle_hash)` work never double-runs.

**Tests (red→green):** `test_slicer_worker_settings_concurrency_cap_default_is_bounded` (asserts `max_jobs` small + sourced from settings); `test_slice_timeout_terminates_and_classifies_timeout`; `test_timeout_value_read_from_settings`.

### AC-8 — Observability per the logging contract (NFR20-OBS-1); g-code NEVER logged in full

Every slice job is instrumented per `~/repos/configs/docs/observability-logging-contract.md`, reusing the `workers/render/render/observability.py` pattern:

- **Structured-log tags:** `stl_hash`, `bundle_hash`, `status`, `failure_reason` (when failed), `orca_version`, `slice_wall_ms`, `manifold` (from `--info`), `warning_count`. One structured line on job start + one on completion.
- **OTel span** around the slice job (e.g. `slicer.slice`) with the same attributes; **GlitchTip breadcrumb** on failure.
- **g-code is parse-and-discard and is NEVER logged in full** (AC-5): logs may carry the metadata-line *count* or a truncated head for debugging, never the full g-code body (it is large + derivable).

**Tests (red→green):** `test_job_emits_structured_tags_on_completion`; `test_failure_emits_failure_reason_tag`; `test_full_gcode_never_appears_in_logs` (assert the captured log records contain no g-code body).

### AC-9 — Settings slots; NFR20-CONTAINER-1 grep invariant (no bench path in production app/config/runtime)

- New settings appended to `apps/api/app/core/config.py` (mirroring the Story 32.1 append pattern, each with an inline `because "…"` contract comment per AC-10):
  - `slicer_orca_bin` (sourced `ORCA_BIN`) — the Orca entrypoint, default a **container-internal** path (e.g. `/opt/orca/orca` or the `--appimage-extract` AppRun); NEVER a bench/Windows literal.
  - `slicer_stl_cache_dir` (sourced `SLICER_STL_CACHE_DIR`) — STL content-hash cache root, default under `portal_content_dir` (e.g. `/data/content/slicer/stl-cache`).
  - `slicer_max_concurrency` (sourced `SLICER_MAX_CONCURRENCY`, default `1`) — AC-7 cap.
  - `slicer_slice_timeout_seconds` + `slicer_info_timeout_seconds` (AC-7).
- **Grep invariant (NFR20-CONTAINER-1):** `grep -rniE "/mnt/c|fenrir|\.exe|[Ww]indows" apps/api/app/modules/slicer/ apps/api/app/core/config.py` returns **ZERO** matches for any bench/Windows path or executable literal; the Orca path is read from `slicer_orca_bin`, never hard-coded. (The word "windows" may legitimately appear only in a comment explaining the invariant — the test targets path/exe literals, not the prose; keep the module free of both to keep the grep clean.)
- Settings/env/compose alignment: the new env vars are documented in `infra/env.example` AND wired into the `infra/docker-compose.yml` `api` + `arq-worker` env blocks (the `infra/scripts/check-settings-env-compose.py` gate that bit Story 32.1 at pre-push). `ORCA_BIN`'s **production runtime home is the configs-side `slicer-worker` container** (AC-12), not the api/arq-worker — document it as a slicer-worker-runtime var; if the gate requires a portal-side env reference, add it with the container-internal default + a comment that the live value is set by the configs-side recipe.

**Tests (red→green):** config default-value tests for each new slot in `apps/api/tests/test_config.py`; `test_no_bench_or_windows_path_literal_in_slicer_module` (the grep invariant as a test, all files not just `*.py`).

### AC-10 — Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

Every literal below appears in code with a single-line `because "…"` contract comment beside it:

| Literal | Location | Contract pointed to |
|---|---|---|
| slicer queue name (e.g. `"arq:slicer"`) | `worker.py` | because **"dedicated queue so the slicer pool never grabs a render/api job and rejects it 'function not found' — the cross-queue-grab bug in `app/workers/__init__.py`; mirrors `API_QUEUE_NAME`"** |
| `_job_id = f"slice:{stl_hash}:{bundle_hash}"` | `enqueue.py` | because **"idempotent dedupe on the complete `(stl_hash, bundle_hash)` reproducibility key — Decision AI § Concurrency; identical work must never double-run (NFR20-RESOURCE-1)"** |
| `max_jobs` concurrency cap default `1` | `worker.py` / `config.py` | because **"small bounded cap so a minutes-long slice can't starve API/render workers on `.190` — NFR20-RESOURCE-1 / OD-6"** |
| `slicer_slice_timeout_seconds` default (e.g. `900`) | `config.py` | because **"ARBITRARY conservative safety ceiling on slice WALL-TIME (not print time) — replace once the configs-side R3 container spike benchmarks real slice wall-time; NOT a contractual value (avoids the TB-016 anti-pattern)"** |
| `slicer_info_timeout_seconds` default (e.g. `60`) | `config.py` | because **"ARBITRARY short ceiling on the cheap `--info` pre-check — replace at benchmark; the pre-check is sub-slice fast by design"** |
| `<hash[:2]>` STL-cache fan-out prefix length | `stl_cache.py` | because **"hash-prefix fan-out mirrors the render/STL + Story 32.1 bundle layout (Decision AI) to bound per-directory entry count"** |
| Orca `--info` manifold parse token (`manifold` / `yes`/`no`) | `cli.py` | because **"the proven bench `--info` output field gating the fast-fail before a full slice — Decision AI § Failure classification; brainstorm § 'Validation pre-check'"** |
| `slicer_orca_bin` default (container-internal path) | `config.py` | because **"the `--appimage-extract` entrypoint inside the configs-side slicer-worker container — NFR20-CONTAINER-1; MUST NOT be a `/mnt/c`/Fenrir/`.exe` literal"** |

A magic constant in the new slicer files without an adjacent contract comment is a P1 review fix-up.

### AC-11 — Determinism gate (NFR20-DETERMINISM-1)

After this story lands, three consecutive `pytest apps/api/tests/test_slicer*.py -v` runs return identical pass counts (no flakes). The worker logic is deterministic by construction under the injected mock runner (no real Orca, no clock/random in the classification path; any `created_at`/timing is excluded from assertions or frozen). The arq slice job is idempotent on `(stl_hash, bundle_hash)` (AC-2). Coverage: T-DET below.

### AC-12 — Configs-side `slicer-worker` container recipe is a coordinated EXTERNAL dependency, NOT a 3d-portal commit (HC2 boundary)

This story owns **app-layer worker code only**. The container topology that actually runs Orca is configs-side and is an explicit **coordination gate** — recorded here, NOT implemented in this repo:

- A `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` recipe — now **merged to configs `origin/main`** (PR [#1](https://github.com/Ezopek/configs/pull/1) merged 2026-06-01; `origin/main` at merge commit `948418097c6d4188a16fecac61dcbc22fa591946` — `9484180 Add 3d-portal slicer worker compose recipe (#1)`; the merged branch head was `2607cab36d9b4cbf720da5916fba608080aaa0d7`, which also carried an unrelated pre-committed agent-toolchain OAuth usage fix — the Story-32.2-relevant files are `docker-compose-recipes/workers/slicer-worker.yml` + `DOCUMENTATION.md`; both present on `origin/main`, verified by `git show origin/main:docker-compose-recipes/workers/slicer-worker.yml` + a `DOCUMENTATION.md` grep — controller-verified). The recipe sits alongside the pre-existing `docker-compose-recipes/{firecrawl,glitchtip,opensearch,otel-collector,spoolman}.yml`; pre-merge, standalone `docker compose -f …/slicer-worker.yml config --quiet`, the 3d-portal overlay `config --quiet`, and `git diff --check` all passed (it was first scaffolded on branch `feat/3d-portal-slicer-worker-recipe`). It is **merged but NOT yet synced / deployed / restarted on the `.190` runtime, and there is still no real slicer-capable portal image / Orca-in-container smoke** — so the AC-12 deploy/image/smoke gate REMAINS OPEN (only the PR/merge half is done). The recipe adds the dedicated `slicer-worker` service:
  - **OrcaSlicer 2.3.2** Linux AppImage (`ORCA_VERSION=2.3.2`, the value Story 32.1 already pinned into `config.py` + `infra/docker-compose.yml`), run via **`--appimage-extract`** (squashfs-extract-and-run, avoids FUSE in-container — the **R3 spike** flagged in Decision AI / brainstorm § container).
  - the **verified Orca dep set** (per `architecture.md` Decision AI): `libopengl0`, `libglu1-mesa`, `libgtk-3-0`, `libwebkit2gtk-4.1-0`, `libsecret-1-0`, `libgstreamer-plugins-base1.0-0`, `libmspack0`.
  - runs `arq app.modules.slicer.worker.SlicerWorkerSettings` against the shared Redis; mounts the `portal-content` volume (read STL cache + bundle store); network topology to reach Redis (and, in 32.5, Spoolman).
  - sets `ORCA_BIN` to the container-internal extracted entrypoint + the slicer settings env (AC-9).
- **Acceptance evidence CI cannot produce:** the real Orca-in-container slice smoke (a known PLA + TPU fixture → exit 0 + expected g-code metadata lines) is verified **out-of-band on the configs-side container**, since CI has no AppImage. The portal-side env-gated `ORCA_SMOKE_TEST=1` test (AC-3) is the bench bridge.
- **Gate:** dev-story may author + green the app-side worker code on the story branch, but the worker is **NOT "deployed"/done** until (a) the configs-side `slicer-worker.yml` recipe — now **PR'd + merged** to configs `origin/main` (PR #1, merge commit `9484180`; see above), but still **NOT yet synced/deployed** on `.190` — is **synced/deployed** on `.190`, and the `--appimage-extract` R3 spike resolves against a real slicer-capable portal image, and (b) the out-of-band Orca-in-container smoke passes. Surface this as a blocking pre-merge note, NOT a silent assumption. No portal-side commit touches `~/repos/configs/*`.

**Verification (doc/grep, not code):** `git diff main -- '~/repos/configs/*'` is empty (no configs edits in the portal branch); the Dev Notes record the recipe contract + dep set + R3 spike + out-of-band smoke as the external gate.

### AC-13 — Scope fence: backend/worker only; explicit dev-story scope boundaries

- **Zero** changes under `apps/web/` (frontend preset + estimate display + soft-fail UI is Story 32.6).
- **Zero** new route mounting: `apps/api/app/main.py:_PUBLIC_ROUTES` + `apps/api/app/router.py` byte-identical to pre-story state (grep/diff invariant). This story exposes no HTTP surface.
- **Zero** Alembic migration: no `EstimateRecord` table, no estimate cache schema — that is Story 32.3 (and per SCP the estimate store is append-only/no-DB anyway). No new file under `apps/api/migrations/versions/`.
- **No estimate parse / cache / dedup** (Story 32.3); **no invalidation / recompute / cost-arithmetic** (Story 32.4); **no Spoolman override implementation** beyond *consuming* the `bundle_hash` / resolved triple already produced by 32.1 (the real Spoolman-backed override provider is Story 32.5); **no adaptive/variable layer height** (gated); **no whole-plate / whole-basket slicing** (per-STL only); **no g-code retention** (AC-5 parse-and-discard).
- **No new heavy Python dependency** in `apps/api/pyproject.toml`: subprocess invocation is stdlib (`subprocess`, `tempfile`, `hashlib`, `shutil`); arq is already present. The Orca AppImage + GL/GTK deps belong to the **configs-side container** (AC-12), NOT to `apps/api/pyproject.toml`.
- **No deploy** until the AC-12 configs gate + out-of-band Orca smoke pass AND the operator go per SCP § 5 is given.

**Tests/grep:** `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` returns zero lines; no new `apps/api/migrations/versions/` file; `apps/api/pyproject.toml` dependency block unchanged.

## Tasks / Subtasks

> **TDD discipline (AGENTS.md § Execution discipline):** each logic-bearing task writes the failing test FIRST (red), then implements to green, then refactors. The classification + cache-addressing + dedupe logic is the red-green core; the Orca subprocess is an injected mock runner in CI (real run is bench/container-gated, AC-3/AC-12).

- [ ] **T1** (AC-1) — Extend the `slicer` module skeleton
  - [ ] T1.1 Add `cli.py`, `stl_cache.py`, `worker_job.py`, `worker.py`, `enqueue.py` with docstrings citing Decision AI + this spec path. No `router.py`.
  - [ ] T1.2 Extend `models.py` with `SliceStatus`, `SliceFailureReason`, `SliceWarning`, `SliceOutcome` (NO `EstimateRecord` — that is 32.3). Tests for the enum/result shapes.
- [ ] **T2** (AC-2) — Idempotent enqueue + dedicated queue *(red→green)*
  - [ ] T2.1 Failing tests: `_job_id` dedupe shape, dedicated slicer queue, payload carries only the 2 hashes.
  - [ ] T2.2 Implement `enqueue.py` (compute/ensure `stl_hash`, populate cache from mirrored catalog copy, enqueue `(stl_hash, bundle_hash)` with `_job_id` + `_queue_name`).
- [ ] **T3** (AC-3) — Real Orca invocation in `cli.py` *(red→green; mocked runner)*
  - [ ] T3.1 Failing tests: `--info` runs before slice, non-manifold fast-fail (slice runner never called), slice argv reuses the `build_orca_smoke_command` shape, entrypoint from settings.
  - [ ] T3.2 Implement the `--info` parse + the timeout-bounded subprocess runner seam + the slice argv; env-gated real-Orca smoke test (`ORCA_SMOKE_TEST=1`).
- [ ] **T4** (AC-4) — Bundle-store + STL content-hash cache reads *(red→green)*
  - [ ] T4.1 Failing tests: load triple from bundle store by hash, `missing_bundle`, hash-fanout cache path, `missing_stl`, enqueue populates cache from the mirrored catalog copy, worker never reads Windows/Fenrir.
  - [ ] T4.2 Implement `stl_cache.py` (addressing + read + populate-from-mirrored-source) + bundle-store read in `worker_job.py`.
- [ ] **T5** (AC-5) — Temp g-code emit + parse-and-discard + 32.3 sink seam *(red→green)*
  - [ ] T5.1 Failing tests: g-code to temp path, discarded on success + on failure, no durable retention / no full g-code in log, injected parser-sink default no-op.
  - [ ] T5.2 Implement the context-managed scratch dir + the `GcodeSink` injection point (default discard).
- [ ] **T6** (AC-6) — Failure + warning classification *(red→green; one test per branch)*
  - [ ] T6.1 Failing tests for `warning`, `non_zero_exit`, `cli_rejected_profile`, `timeout`, never-silent-zero (`non_manifold`/`missing_*` from T3/T4).
  - [ ] T6.2 Implement the `SliceOutcome` classification in `worker_job.py`; note the `parse_failure` reason is reserved for Story 32.3.
- [ ] **T7** (AC-7) — Bounded concurrency + slice/info timeout *(red→green)*
  - [ ] T7.1 Failing tests: bounded `max_jobs` default from settings, timeout terminates + classifies `timeout`, timeout value from settings.
  - [ ] T7.2 Implement `SlicerWorkerSettings.max_jobs` + the wall-time timeout (process-group terminate) + the contract comments (AC-10).
- [ ] **T8** (AC-8) — Observability *(red→green)*
  - [ ] T8.1 Failing tests: structured tags on completion, failure-reason tag, full g-code never in logs.
  - [ ] T8.2 Implement the structured-log tags + OTel span + GlitchTip breadcrumb (reuse `workers/render/render/observability.py` pattern).
- [ ] **T9** (AC-9, AC-10) — Settings slots + env/compose alignment + magic-constant contracts
  - [ ] T9.1 Append `slicer_orca_bin`, `slicer_stl_cache_dir`, `slicer_max_concurrency`, `slicer_slice_timeout_seconds`, `slicer_info_timeout_seconds` to `config.py` (with `because` comments); config default tests.
  - [ ] T9.2 Document in `infra/env.example` + wire into `infra/docker-compose.yml` env blocks; run `infra/scripts/check-settings-env-compose.py` → OK (allowlist `ORCA_BIN`/slicer vars as slicer-worker-runtime if needed).
  - [ ] T9.3 Grep invariant test: no `/mnt/c` / Fenrir / `.exe` / Windows-path literal in the slicer module + `config.py`.
- [ ] **T10** (AC-12) — Configs-side coordination gate (DOC ONLY, no configs edit)
  - [ ] T10.1 Record the `slicer-worker.yml` recipe contract (OrcaSlicer 2.3.2 AppImage `--appimage-extract` + verified dep set + `arq …SlicerWorkerSettings` + volume/network + `ORCA_BIN`) + the R3 spike + the out-of-band Orca-in-container smoke as the external pre-merge gate in Dev Notes. Assert `git diff main -- '~/repos/configs/*'` empty.
- [ ] **T11** (AC-13) — Scope fence *(grep/diff)*
  - [ ] T11.1 `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` → 0 lines; no new `apps/api/migrations/versions/` file; `pyproject.toml` deps unchanged.
- [ ] **T-DET** (AC-11) — Determinism gate: 3× consecutive identical pytest pass counts on the slicer suite; document in Dev Agent Record.
- [ ] **T12** (full quality gate) — `ruff format --check` + `ruff check` clean on `apps/api/`; `pytest apps/api/tests/ -v` green = baseline + new slicer-worker cases (env-gated real-Orca smoke skipped). No vitest/Playwright (backend/worker only).
- [ ] **T13** (handoff) — dev-story flips `ready-for-dev → review`; code-review owns `→ done`. **Commit / ff-merge / deploy NOT performed by dev-story — controller-owned, AND gated on the AC-12 configs recipe + out-of-band Orca smoke + operator go (SCP § 5).** Story branch: `feat/E32.2-slicer-worker-container-cli-invoke-classify` (created by dev-story at start, NOT now). Suggested commit scope when the controller commits: `feat(api): containerized headless Orca slicer worker — CLI invoke + classify (Story 32.2, Init 20)`.

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 20 — FR20-ESTIMATE-1, FR20-FAILURE-1, NFR20-CONTAINER-1, NFR20-RESOURCE-1, NFR20-OBS-1.
- **Architecture:** `architecture.md` § Initiative 20 — Decision **AI** (slicer-worker container: runtime boundary, `(stl_ref, bundle_ref)` job IO, `--info` pre-check + slice, STL cache layout, warning/failure classification, bounded concurrency, configs/app HC2 boundary). Decision AH (Story 32.1) supplies the bundle + hash this worker consumes; Decision AJ (Stories 32.3/32.4) consumes this worker's g-code + `SliceOutcome`.
- **Epics:** `epics.md` § Initiative 20 § Story 32.2 (sketch + FR/NFR matrix).
- **SCP:** `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3.
- **Brainstorm:** `_bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md` (§ container/AppImage, § validation pre-check `--info`, OD-5 parse-and-discard, OD-6 concurrency).
- **Story 32.1 (done):** `_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md` — supplies `SlicerProfileBundle` / `ResolvedTriple` / `bundle_store` / `validation.build_orca_smoke_command` + `ORCA_SMOKE_COMMAND_TEMPLATE` (the seams this story implements for real) + the `orca_version` / `slicer_vendored_profiles_dir` / `slicer_bundle_store_dir` settings already wired into `config.py` + `infra/docker-compose.yml`.
- **Memory entries (read before implementation):**
  - `[[feedback_scp_pre_enumeration_phase]]` — pre-enumeration § A + magic-constant contract § C (AC-10 source; the timeout-as-arbitrary-default framing in AC-7/AC-10 directly applies the TB-016 anti-pattern lesson).
  - `[[feedback_codex_model_routing]]` — Story 32.2 review-tier routing (dual-adjacency: runtime-boundary/resource-safety + data-integrity); controller assigns the concrete model (recommended `gpt-5.5`).
  - `[[feedback_itcm_autonomous_mode]]` — dev-story execution NOT yet authorized (operator go per SCP § 5 + the AC-12 configs gate); spec authoring only.

### Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

Run 2026-06-01 against post-Story-32.1 repo state (commit `3e6168b`):

1. **Files reused / extended (existing — DO NOT duplicate):**
   - `apps/api/app/modules/slicer/validation.py` — `build_orca_smoke_command` + `ORCA_SMOKE_COMMAND_TEMPLATE` + `CliValidator`/`NullCliValidator` seam. T3 implements the REAL invocation by extending this argv shape (single source of truth), NOT a parallel command builder.
   - `apps/api/app/modules/slicer/models.py` — `ResolvedTriple`, `SlicerProfileBundle`, `MaterialClass`. T1.2 APPENDS the slice-outcome types here (one module, no new models file).
   - `apps/api/app/modules/slicer/bundle_store.py` — the append-only bundle read (`<bundle_root>/bundles/<hash[:2]>/<hash>.json`). T4 reads the triple through it; does NOT re-implement store IO.
   - `apps/api/app/core/config.py` — `Settings` (already carries `orca_version`, `slicer_vendored_profiles_dir`, `slicer_bundle_store_dir`, `portal_content_dir`). T9 APPENDS the worker slots (pattern mirrors the Story 32.1 additions).
   - `apps/api/app/workers/__init__.py` — `WorkerSettings` + `API_QUEUE_NAME` dedicated-queue precedent (the cross-queue-grab bug rationale). `workers/render/render/worker.py` — arq job + `RedisSettings` bare-class-attr pattern (the classmethod gotcha) + `render/observability.py` instrumentation pattern. T2/T7/T8 mirror these; do NOT touch render or api worker code.
   - STL source: catalog STL lives at `portal-content` `models/{model_id}/files/{file_uuid}.stl` (the `.190`-mirrored copy). T2/T4 populate the content-hash cache from there (OD-8), never from Windows/Fenrir.
2. **NEW (Story 32.2 owns):** `apps/api/app/modules/slicer/{cli,stl_cache,worker_job,worker,enqueue}.py` + `apps/api/tests/test_slicer_worker.py` (+ `test_slicer_cli.py` / `test_slicer_cache.py` if split). Optional: small STL/g-code-output fixtures under `apps/api/tests/fixtures/slicer/` (a tiny manifold + a tiny non-manifold mesh for the `--info` parse test; NO real g-code retained).
3. **MODIFIED (append-only):** `apps/api/app/modules/slicer/models.py` (slice-outcome types) + `apps/api/app/core/config.py` (worker slots) + `apps/api/tests/test_config.py` (defaults) + `infra/env.example` (env block) + `infra/docker-compose.yml` (env refs for the gate).
4. **Contracts UNTOUCHED:** `_PUBLIC_ROUTES`, `apps/api/app/router.py`, `share/router.py`, the route-enforcement gate (this story mounts no routes — AC-13). `apps/api/app/modules/spools/*` untouched (Story 32.5 reuses it). `workers/render/*` untouched. No NFR reversal. `~/repos/configs/*` untouched (HC2 — AC-12).

**Net scope:** ~5 new module files + 1–3 new test files + (optional) tiny mesh fixtures + 5 modified files + 0 Alembic + 0 routes + 0 new heavy deps + 0 configs-repo edits.

### Cache-coherence / boundary enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

This is a backend worker story (no React Query / TanStack cache), so the FE cache-topology table does not apply. The coherence concerns this story owns:

| Concern | Source: Story 32.2 (this story) | Related surface |
|---|---|---|
| Job key completeness | the job IS keyed `(stl_hash, bundle_hash)` — exactly the Story 32.4 invalidation key; `bundle_hash` already folds `orca_version` + Spoolman override set (Story 32.1) | Story 32.4 invalidation/recompute keys off this same tuple — the job dedupe (`_job_id`) MUST use the complete tuple or a re-tune/Orca-upgrade would alias an old slice (R9 class). |
| STL cache ↔ catalog coherence | content-hash addressing (`<hash>`); a changed STL has a new hash ⇒ new cache entry + new job key | Story 32.4 STL-content-change trigger relies on `stl_hash` changing; the cache is populated from the `.190`-mirrored catalog copy at enqueue (OD-8). |
| g-code lifetime | parse-and-discard; temp file deleted at job end (AC-5) | Story 32.3 parses the temp g-code within the same job (the `GcodeSink` seam); no durable g-code crosses the story boundary. |
| Outcome classification taxonomy | `SliceStatus` + `SliceFailureReason` (invocation outcomes) | Story 32.3 EXTENDS with `parse_failure`; Story 32.6 renders warning/failed/stale states. The taxonomy is designed to extend, not reshape. |

Decision rule: the job dedupe key + the STL cache address MUST both be content-hash-complete; nothing slice-affecting is passed by mutable id or out-of-band path.

### Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` § C)

All literals in AC-10 carry an inline `because "…"` comment. The **slice/info timeout values are explicitly marked ARBITRARY conservative defaults pending the configs-side R3 slice-wall-time benchmark** — NOT contractual constants — directly applying the TB-016 lesson (do not justify a timeout by a happy-path size; justify by a measured distribution or mark it arbitrary). The queue name + `_job_id` shape + concurrency cap DO point to contracts (cross-queue-grab avoidance, reproducibility-key completeness, NFR20-RESOURCE-1).

### Threat-vector enumeration

Story 32.2 routes to the higher review tier for **runtime-boundary / resource-safety** AND **data-integrity** adjacency (not auth-boundary). Survey:

- **No HTTP surface, no auth, no CSRF, no public-bypass family touch** — zero routes mounted (AC-13).
- **Subprocess invocation over an STL mesh:** the worker spawns a real OrcaSlicer process over a user-supplied mesh. Mitigations in-scope: the `--info` manifold pre-check fast-fails bad meshes before the expensive slice; the bounded `max_jobs` cap + the wall-time timeout (process-group terminate) bound CPU/wall-time so a pathological mesh cannot hang or starve the API/render workers (R1/R3 self-inflicted-DoS class); the STL path is content-hash-derived (`<hash[:2]>/<hash>.stl`) — no user-controlled path component, no traversal vector; the Orca argv is built from fixed flags + content-addressed temp files, not string-interpolated user input.
- **Deployment-boundary integrity (NFR20-CONTAINER-1):** the Orca entrypoint + all paths are settings-sourced container-internal values; the grep invariant (AC-9) guarantees no `/mnt/c` / Fenrir / `.exe` literal reaches production app/config. The container itself is configs-side (AC-12).
- **Data-integrity (the second real risk class):** a misclassified slice (failed/timed-out surfaced as valid, or a silent zero) → a plausible-but-wrong estimate downstream. Mitigated by AC-6 (typed `SliceOutcome`, never silent zero) + the never-silent-zero test.
- **No PII** — STL meshes + Orca profile JSON + g-code metadata are not personal data.
- **g-code logging:** AC-8 forbids full-g-code in logs (large, derivable; parse-and-discard).

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/slicer/cli.py` | NEW | T3 — Orca `--info` pre-check + slice argv + timeout-bounded runner (extends `validation.build_orca_smoke_command`) |
| `apps/api/app/modules/slicer/stl_cache.py` | NEW | T4 — content-hash STL cache addressing + read + populate-from-mirrored-source |
| `apps/api/app/modules/slicer/worker_job.py` | NEW | T2/T4/T5/T6 — the `slice_estimate` arq task: load → pre-check → slice → classify → discard |
| `apps/api/app/modules/slicer/worker.py` | NEW | T7 — `SlicerWorkerSettings` (dedicated queue + `max_jobs` cap + redis) the configs-side container runs |
| `apps/api/app/modules/slicer/enqueue.py` | NEW | T2 — API-side idempotent enqueue (`_job_id` + cache populate) |
| `apps/api/app/modules/slicer/models.py` | MODIFY (append) | T1.2 — `SliceStatus` / `SliceFailureReason` / `SliceWarning` / `SliceOutcome` |
| `apps/api/tests/test_slicer_worker.py` (+ `test_slicer_cli.py`/`test_slicer_cache.py`) | NEW | T2–T8, T-DET pytest cases (mocked Orca runner; env-gated real smoke) |
| `apps/api/tests/fixtures/slicer/` | EXTEND (optional) | tiny manifold + non-manifold mesh for the `--info` parse test (NO g-code retained) |
| `apps/api/app/core/config.py` | MODIFY (append slots) | T9.1 — `slicer_orca_bin` + `slicer_stl_cache_dir` + `slicer_max_concurrency` + slice/info timeouts |
| `apps/api/tests/test_config.py` | EXTEND | T9.1 — default-value coverage |
| `infra/env.example` | EXTEND | T9.2 — `ORCA_BIN` + `SLICER_STL_CACHE_DIR` + concurrency/timeout env (slicer-worker-runtime) |
| `infra/docker-compose.yml` | MODIFY | T9.2 — env refs to satisfy the `check-settings-env-compose.py` gate |

**Files this story MUST NOT touch:** `apps/api/app/main.py` (`_PUBLIC_ROUTES`), `apps/api/app/router.py`, `apps/api/app/modules/share/router.py`, `apps/api/app/modules/spools/*` (Story 32.5), `workers/render/*`, `apps/api/app/workers/*` (api-arq worker — the slicer worker is its own entrypoint), `apps/web/`, `apps/api/migrations/`, `~/repos/configs/*` (HC2 boundary — the slicer-worker container is configs-side, AC-12).

### Project Structure Notes

- OD-9-resolved: the worker code joins the existing `apps/api/app/modules/slicer/` bounded-context module (same package as the Story 32.1 resolver). The dedicated arq entrypoint (`SlicerWorkerSettings` in `slicer/worker.py`) is what the **configs-side `slicer-worker` container** runs — distinct from the api-arq worker (`apps/api/app/workers/WorkerSettings`, queue `arq:api`) and the render worker (`workers/render/`, default `arq:queue`). Three worker pools, three queues, no cross-grab.
- The slice job is the FIRST arq task in the `slicer` module; it follows the proven render-worker shape (bare-class `redis_settings`, dedicated queue) so the runtime is not novel.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 20 — Decision AI (slicer-worker container, job IO, `--info` pre-check, STL cache, classification, concurrency, HC2 boundary)]
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 20 — FR20-ESTIMATE-1 + FR20-FAILURE-1 + NFR20-CONTAINER-1 + NFR20-RESOURCE-1 + NFR20-OBS-1]
- [Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 20 § Story 32.2]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3]
- [Source: `_bmad-output/implementation-artifacts/32-1-profile-resolver-merge-normalize-validate-hash.md` — bundle/triple/validation seams consumed]

## Dev Agent Record

> To be completed by `bmad-dev-story` when implementation is authorized (operator go per SCP § 5 + the AC-12 configs-side coordination gate). Spec authoring only at this point — no code written.

### Agent Model Used

_(dev-story fills in)_

### Debug Log References

_(dev-story fills in — RED→GREEN evidence per task)_

### Completion Notes List

_(dev-story fills in — AC-by-AC evidence + exact test counts)_

### File List

_(dev-story fills in)_
