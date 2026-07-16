# Deferred Work — quick-dev review backlog  [ARCHIVED / FROZEN 2026-07-16]

> **FROZEN 2026-07-16 — accepted into the production baseline.**
> This ledger is closed. `main` as of 2026-07-16 is the production baseline
> (see `../PRODUCTION-BASELINE-2026-07-16.md`). The open entries below
> (DSG-1..5, TB-015-D1, SPOOL-PREQ-1-D1, PROFILE-LIB-GUARD-1,
> PROFILE-OFFER-SYNC-1) are known, non-blocking debt that is **not** carried
> into the tag-taxonomy / model-catalog rebuild. If any resurfaces as a real
> problem, re-triage it individually as a fresh item under the new initiative —
> do not treat this file as a live backlog.

Findings from BMAD reviews that are real but **not blocking** the current story. Each entry has enough context that a future promotion to its own quick-dev story (or absorbing into a related one) can happen without re-deriving context.

---

## Deferred from: quick-dev review of deploy-skip-gate-range (2026-05-16)

Source: 3 BMAD subagent reviews + 1 Codex review of `feat/deploy-skip-gate-range` (commits `bc324e2` + `0745209`). All findings here are **defensive robustness improvements** on top of a spec-compliant implementation — the Acceptance Auditor confirmed all ACs are met. Two P1s from that batch were patched in-flight (`0745209`: SHA-format validation).

### DSG-1 — `2>/dev/null` on state-file write swallows real errno

**Source:** Blind Hunter [P2]

**Where:** `infra/scripts/deploy.sh` — the state-file write block before final `echo "Done."`:

```bash
echo "$deploy_sha_full" > "$last_deploy_path" 2>/dev/null || \
  echo "[deploy-skip-gate] WARN: failed to update $last_deploy_path (non-fatal)" >&2
```

**Problem:** `2>/dev/null` suppresses the actual `bash` error message (permission denied, disk full, etc.). The fallback WARN fires but operator gets no errno hint. Next run re-deploys because the state file wasn't updated, which is correct fail-direction — but diagnosing why takes longer than it should.

**Fix sketch:** Capture the error: `if ! { echo "$deploy_sha_full" > "$last_deploy_path"; } 2>/tmp/dsg-write-err; then echo "[deploy-skip-gate] WARN: failed to update ... ($(cat /tmp/dsg-write-err))" >&2; fi`. Or just drop `2>/dev/null` so bash's error reaches stderr naturally before the WARN.

### DSG-2 — `last_short` lacks a defensive fallback (mirror of `head_short`'s `|| echo unknown`)

**Source:** Blind Hunter [P3]

**Where:** `infra/scripts/deploy.sh`, gate block:

```bash
head_short="$(... || echo unknown)"  # has fallback
last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha")"  # NO fallback
```

**Problem:** If `git rev-parse --short` somehow fails for the validated `last_deploy_sha` (extremely unlikely — we already passed `rev-parse --verify`, so the object resolves), `set -e` would kill the script. Asymmetric defensive style.

**Fix sketch:** `last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha" 2>/dev/null || echo "${last_deploy_sha:0:7}")"`.

### DSG-3 — State-file write is non-atomic (kill-mid-write → zero-byte file)

**Source:** Blind Hunter [P3]

**Where:** Same write block as DSG-1.

**Problem:** `echo > file` opens the file (truncating to zero) BEFORE writing the payload. SIGKILL between truncate and write leaves an empty file. Next run hits the new (post-fix-up) SHA-format check → empty fails regex → WARN+deploy. Safe direction, but the state is lost for the next legitimate skip.

**Fix sketch:** `printf '%s\n' "$deploy_sha_full" > "$last_deploy_path.tmp" && mv "$last_deploy_path.tmp" "$last_deploy_path"`. The `mv` is atomic on the same filesystem.

### DSG-4 — Leading-whitespace commit subjects bypass the gate

**Source:** Edge Case Hunter [P2]

**Where:** `infra/scripts/deploy.sh`, the per-subject match loop in the gate.

**Problem:** A commit subject like `" docs: typo"` (leading space) is non-empty, does not match `docs:` (no leading space in the prefix), so `all_skip=false` → deploy. Safe-side failure, but technically the subject reflects a docs-only change.

**Fix sketch:** Either trim leading whitespace before match: `subject="${subject#"${subject%%[![:space:]]*}"}"`, or document the case as "intentional — leading-whitespace subjects are non-conformant and always deploy."

**Why deferred:** Probably not actually encountered in practice; current `set -euo pipefail` plus `git log --format=%s` consistently produces clean subjects.

### DSG-5 — Concurrent `deploy.sh` invocations: TOCTOU on `.last-deploy-sha`

**Source:** Edge Case Hunter [P2]

**Where:** Conceptual; affects both the read-and-decide block and the write-on-success block.

**Problem:** Two operators (or operator + scheduled task) running `deploy.sh` simultaneously: both read the same stale SHA, both pass the gate, both deploy, both write at end — last writer wins. The state file may end up reflecting the wrong "latest deploy".

**Why deferred:** 3d-portal is single-operator + single-host. The current `feedback_auto_deploy_dev.md` flow has no concurrent-invocation pattern. If a future epic introduces autonomous scheduled deploys alongside operator runs, this becomes a real concern.

**Fix sketch:** `flock -n /tmp/3d-portal-deploy.lock` wrap on the whole script (or at minimum on the gate-read + state-write windows).

---

## Promoted to story / absorbed

_(none yet)_

---

## Deferred from: quick-dev review of tb-015-measure-clear-clickable (2026-05-21)

Source: 3 BMAD subagent reviews of TB-015 fix (pointer-events-auto on MeasureSummary footer div). Spec fully satisfied per Acceptance Auditor. All other P2/P3 findings either patched in-flight (parentElement fragility, row-delete selector specificity, inline-host coverage) or rejected as noise. ONE finding warrants a parking entry.

### TB-015-D1 — Touch / mobile pointer-events propagation inside backdrop-blur ancestor

**Source:** Edge Case Hunter [P3]

**Where:** `apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx:42` — the outer `<div className="rounded-md border border-border bg-card/85 backdrop-blur-md text-xs">` host of the summary panel.

**Hypothesis:** iOS Safari has documented edge cases where `pointer-events: none` combined with `backdrop-filter: blur(...)` and certain stacking contexts can swallow touch events differently from desktop. Our TB-015 fix is verified for desktop via vitest + future agent-browser; mobile-light (touch) verification is included in the visual-verification gate, but iOS Safari specifically isn't in our 4-project Playwright matrix (we use Chromium-based Pixel 5 emulation, not WebKit). This means a real-iOS-Safari regression would not be caught by automated gates today.

**Why deferred (not promoted):**
- The fix mirrors the existing per-row `<li>` pattern (`MeasureSummary.tsx:50`) which has been shipped and used on mobile catalog visits for months without reports. If `backdrop-blur` + `pointer-events-none` were a real iOS Safari issue, per-row × delete would have surfaced it long before TB-015.
- The risk is bounded (one specific browser engine, edge case, mitigated by the same pattern already in production).
- Promoting now would scope-creep TB-015's "one-line fix" into a multi-browser audit — premature.

**Trigger to promote:** any operator report of "Wyczyść pomiary doesn't work on my iPhone" post-TB-015 deploy, OR formal addition of WebKit / iOS Safari to the visual-regression Playwright matrix as a project initiative.

**Code map:** `MeasureSummary.tsx:42` (outer host with backdrop-blur), `MeasureSummary.tsx:82` (the new pointer-events-auto footer), `Viewer3DModal.tsx:390` (the pointer-events-none wrapper that the fix neutralizes).

---

## Deferred from: Story 32.3 deploy/runtime smoke (2026-06-01)

Source: controller runtime smoke after Story 32.3 (`9a7aea5`) was committed/merged/deployed. `infra/scripts/deploy.sh` ran the normal path — built/shipped `portal-api`/`web`/`render` and restarted the base compose stack — but the new app-side slicer modules did not reach the running slicer worker until the controller intervened manually.

### SW-DEPLOY-1 — deploy automation does not rebuild/restart the slicer-worker overlay on slicer/portal-api changes

**Source:** Controller runtime verification (2026-06-01).

**Where:** `infra/scripts/deploy.sh` (base deploy path) vs. the configs-side overlay service `3d-portal-slicer-worker-1`, defined in `/mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.yml` and built from `/mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.Dockerfile` (image `portal-slicer-worker:0.1.0`, layered on `portal-api:0.1.0`).

**Problem:** `deploy.sh` rebuilds and restarts only the base stack. The slicer-worker overlay lives configs-side and is **not** touched by `deploy.sh`. After the 32.3 deploy, `3d-portal-slicer-worker-1` kept running the older `portal-slicer-worker:0.1.0` image, which predated the new modules `app.modules.slicer.gcode_parse` and `app.modules.slicer.estimate_store`. So the worker that actually executes slice/estimate jobs was running stale code while `portal-api` had already advanced — a silent version skew between the API image and the slicer-worker image.

**Why it matters:** The slicer-worker image is built **on top of** the fresh `portal-api` image but only when something explicitly rebuilds it. Any story that lands slicer-adjacent app code (or otherwise bumps the `portal-api` base image) will deploy "green" via `deploy.sh` while the slicer worker silently runs old modules — `ModuleNotFoundError` / behavioral drift surfaces only when a slice/estimate job runs, well after the deploy is reported done. This is exactly the failure mode that hit 32.3; it was only caught because the controller ran a runtime import smoke from inside the container.

**Manual repair performed (so 32.3 runtime is verified, not broken):** controller rebuilt `portal-slicer-worker:0.1.0` on `.190` from `slicer-worker.Dockerfile` after the fresh `portal-api:0.1.0` image landed, then restarted the overlay:

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f /mnt/raid/configs/docker-compose-recipes/workers/slicer-worker.yml \
  --profile slicer-worker up -d slicer-worker
```

Post-repair runtime verification PASSED: slicer-worker image `sha256:217a827f95e130652998bc8a404fd85f3970704ca8d87f897744c39d2cc36a04`, modules `gcode_parse=True` and `estimate_store=True`, Orca 2.3.2 present, parser/cache smoke passed.

**Fix sketch:** Teach the deploy automation to detect when slicer-adjacent app code (or the `portal-api` base image) changes and, on that condition, rebuild + restart the slicer-worker overlay as part of the deploy — either folded into `deploy.sh` (with the configs overlay paths/profile) or factored into a dedicated slicer-worker deploy script/gate invoked after the base stack is up. The gate should finish by verifying, from inside `3d-portal-slicer-worker-1`: (a) the slicer module imports resolve (`gcode_parse`, `estimate_store`), (b) the Orca binary path is present and runnable, (c) the parser/cache smoke passes. Crosses the repo↔configs boundary, so this is a coordinated change (see HC2 / configs-side ownership) — likely a small `deploy.sh` hook plus a configs-side recipe/script, not a one-file edit.

**Trigger / priority:** Real should-fix-soon tech debt — **not blocking 32.3** (runtime was manually repaired and verified above). Promote before the next story that touches `app.modules.slicer.*` or otherwise rebases the `portal-api` image (e.g. 32.4 invalidation/recompute, 32.5 Spoolman override, 32.6 FE), since each such deploy currently re-opens the same silent-skew window. Until automated, every deploy that changes slicer code MUST be followed by the manual overlay rebuild + in-container import/Orca/parser smoke above.

**STATUS — app-repo side IMPLEMENTED (2026-06-02, bmad-quick-dev).** Promoted per the Epic 32 retro §5/A1 recommendation and implemented on branch `feat/SW-DEPLOY-1-slicer-overlay-deploy` (sprint-status key `sw-deploy-1-slicer-worker-overlay-deploy`):
- `infra/scripts/slicer-worker-overlay.sh` — `detect`/`rebuild`/`smoke`/`deploy` subcommands; env-var-driven configs paths/image/profile/host (recipe **referenced, never vendored** — HC2 preserved); `DRY_RUN=1` command-generation seam; `FORCE_SLICER_WORKER_REBUILD=1` (manual 32.4/32.5 gate closure) + `SKIP_SLICER_WORKER=1` (hard opt-out).
- `infra/scripts/deploy.sh` — overlay phase wired **after** `alembic upgrade head`; **any** rebuild/restart/smoke failure is **FATAL** and aborts before the state-file write, so a failed run is not recorded successful (rebuild made fatal per Gemini review — a swallowed build failure would pass the presence-based smoke against the stale image). Detection is `portal-api`-base-aware: any `apps/api/**` change ⇒ rebuild needed; web/docs/render-only ⇒ skip.
- In-container smoke now covers all three classes named in the fix sketch **plus** 32.4/32.5: importlib(`gcode_parse`,`estimate_store`,`recompute`,`overrides`,`spoolman_invalidation`) + Settings(`slicer_estimate_store_dir`,`slicer_orca_bin`) + Orca `--help` reachability + `parse_gcode_metadata`/`map_filament_extra` functional smoke.
- Tests: `infra/scripts/tests/test_slicer_worker_overlay.py` (13 cases, stdlib+pytest, no Docker/SSH) + a `check-all.sh` stage. Docs: `docs/operations.md` § "Slicer-worker overlay deploy".

**STATUS — PROMOTED & CLOSED (2026-06-02). No longer deferred.** The app-repo automation shipped as story `sw-deploy-1-slicer-worker-overlay-deploy` (commit `7d65de1`, merged to `origin/main` as `19d6dd3`), and the controller-owned `.190` runtime gate has since been exercised and **closed**:
- Post-merge `deploy.sh` exited 0 (base stack restarted, migrations OK, symbolication verify OK release `0.1.0+19d6dd3`, runbook fingerprint OK); the overlay hook correctly **auto-skipped** the rebuild for this range (`0f34c07..HEAD` touched no `apps/api`, so `portal-api` stayed cached — AC2 base-aware behavior).
- Forced gate-closure run `FORCE_SLICER_WORKER_REBUILD=1 infra/scripts/slicer-worker-overlay.sh deploy` exited 0: `docker build portal-slicer-worker:0.1.0` OK (image `sha256:83779407c257b765c41e7340a5d7016de59d1f80e16fb2b2bfee5b69e7dbe454`), overlay recreated/started, in-container smoke `SLICER_WORKER_SMOKE_OK modules=5 orca=/opt/orca/orca estimate_store_dir=/data/content/slicer`.
- Runtime probe `.190`: `/api/health` → `{"status":"ok","version":"0.1.0"}`; `3d-portal-slicer-worker-1` on `portal-slicer-worker:0.1.0` Up; `importlib` True for `gcode_parse`/`estimate_store`/`recompute`/`overrides`/`spoolman_invalidation`; `estimate_store_dir=/data/content/slicer`; `orca_bin=/opt/orca/orca`.

This also **closed the open 32.4/32.5 overlay gate (retro A2)** — the worker image now carries the `recompute`/`overrides`/`spoolman_invalidation` modules. No configs-repo edit was required (the recipe already existed from 32.2/32.3); if the recipe paths ever relocate, only the env-var defaults change. See `sw-deploy-1-slicer-worker-overlay-deploy.md` for the full closeout.

---

## Deferred from: Story 32.5 dev-story (2026-06-02)

Source: Story 32.5 (Spoolman-mapped filament overrides) AC-6 / AC-9 scope fence. The classification + dispatch primitive (`apply_spoolman_filament_change`) is implemented and proven correct under unit tests with injected fakes + a caller-supplied `affected_keys` set, mirroring how Story 32.4 left its event source to 32.5.

### SPOOL-EVT-1 — live Spoolman-change event source + `filament_ref → estimate-keys` reverse index

**Source:** Story 32.5 AC-6 (explicit deferral) + AC-9 scope fence.

**Where:** `apps/api/app/modules/slicer/spoolman_invalidation.py` (`apply_spoolman_filament_change`, `affected_keys` parameter) ↔ the Init 19 Story 31.1 poll loop (`apps/api/app/modules/spools/service.py`).

**Problem:** Story 32.5 ships the dispatch that, given a single filament's `old → new` state + a caller-supplied set of affected `(stl_hash, bundle_hash)` keys, classifies a mapped-vs-cost-only change and drives the Story 32.4 engine. It does **not** ship the live trigger source: there is no wiring that (a) detects a Spoolman `filament.extra` / `price` / `weight` change across Init 19 poll ticks (a poll-diff over successive `SpoolsService.get_summary()` snapshots), nor (b) enumerates *which* estimate keys depend on a given filament ref (a `bundle_hash → filament_ref` reverse index, or a full `EstimateStore.iter_all_estimates` re-resolve sweep). So in v1 nothing automatically calls `apply_spoolman_filament_change` when Spoolman inventory actually changes — a mapped-field edit or a price tick on `.190` does not yet invalidate/recompute dependent estimates on its own.

**Why it matters:** Until this lands, the cost-only-no-re-slice guarantee + the mapped-override invalidation are *available primitives*, not an *end-to-end live behavior*. A real Spoolman price edit won't recompute cached estimate costs, and a real mapped-field edit won't mark dependent estimates stale, without an operator/ops trigger calling the dispatch with the affected key set. This is the same boundary Story 32.4 drew (it deferred its event source to 32.5); 32.5 deliberately keeps the same fence to avoid the broad work (a reverse index or full re-resolve sweep) that exceeds its scope.

**Fix sketch:** A future ops/poll story adds either (1) a `bundle_hash → {filament_ref}` reverse index maintained at bundle-persist time (so a changed filament ref maps directly to its dependent bundles/estimate keys), or (2) a periodic/triggered `iter_all_estimates` re-resolve sweep that re-derives each estimate's current bundle and diffs it against the stored key. Either feeds the `affected_keys` set into `apply_spoolman_filament_change`. The poll-diff half hooks the Init 19 snapshot refresh: keep the previous snapshot, diff `filaments` by ref on each tick, and for each changed filament call the dispatch with that filament's affected keys. Pure app-side; no new Spoolman read (reuses the existing cache).

**Trigger / priority:** Real follow-up, **not blocking 32.5** (the dispatch primitive is the load-bearing deliverable and is fully tested). Promote when the live "Spoolman change automatically updates estimates" behavior is needed end-to-end (likely alongside or after Story 32.6's FE estimate display, which is the first surface where a stale/recomputed estimate becomes user-visible).

**STATUS — reverse-index / intent-attribution LANDED via SPOOL-PREQ-1 (shipped on `main` as commit `35360d6`; originally 2026-06-03, bmad-quick-dev).** The "enumerate which estimate keys depend on a given filament" half (fix-sketch option 1, the `bundle_hash → {filament_ref}` reverse index) is built, tested, and on `main` (branch `feat/SPOOL-PREQ-1-spoolman-reverse-index`). Spec: `spec-spool-preq-1-spoolman-reverse-index.md`. What shipped:
- `apps/api/app/modules/slicer/attribution_store.py` — `AttributionStore`, the THIRD append-only file-store sidecar (ref-hash fanout `<root>/attribution/<refhash[:2]>/<refhash>.json`, additive idempotent merge under the estimate-store flock + atomic-publish discipline). Keyed by the churn-stable `spoolman_filament_ref` (hashed for the path, raw ref round-tripped in the body). Persists `ref → {(PrintIntentPreset, bundle_hash)}` — portal-owned intent only, NO Orca internals / NO raw override values.
- `apps/api/app/modules/slicer/resolver.py` — optional `attribution_sink` DI seam on `resolve()` (mirrors `override_provider`): on a successful resolve whose intent pins a `spoolman_filament_ref`, records `(ref, intent, bundle_hash)` — on BOTH the fresh-persist and exact-bundle-cache-hit branches. `None` sink or unpinned ref ⇒ byte-identical no-op (zero perturbation of existing resolve hashes/tests). `resolve_intent()` defaults to a real settings-wired store so the convenience entry point populates the index wherever it resolves.
- `lookup_affected_keys(ref, *, attribution_store, estimate_store)` — the deterministic join SPOOL-EVT-1 calls: composes the persisted index with the EXISTING `EstimateStore.iter_all_estimates` (single pass, bundle_hash → {stl_hash}) to return, per pinning intent, an `AffectedGroup(intent, bundle_hash, affected_keys=[(stl_hash, bundle_hash)…])`.

**CONCRETE REMAINING STEP for SPOOL-EVT-1 (the poll-diff event source):**
1. Hook the Init 19 poll refresh (`apps/api/app/modules/spools/service.py` `refresh_summary`, driven by the `poll_spoolman_summary` cron): keep the PREVIOUS `SpoolmanSnapshot` (the service does not retain one today — add a prior-snapshot cache, e.g. a second Redis key) and on each tick diff `filaments` keyed by `spoolman_filament_ref(f)` (the same churn-stable ref this index uses).
2. For each changed ref, call `groups = lookup_affected_keys(changed_ref, attribution_store=…, estimate_store=…)`.
3. For each `group` in `groups`, call `apply_spoolman_filament_change(store, arq_pool, intent=group.intent, old=old_filament, new=new_filament, source=…, bundle_store=…, orca_version=…, affected_keys=group.affected_keys)`. One call per pinning intent (each intent re-resolves against `new` internally to get its new `bundle_hash`).
4. Pure app-side; reuses the existing Spoolman cache (no second poll). Wire the stores from settings (`AttributionStore`/`EstimateStore`/`BundleStore` on `slicer_bundle_store_dir` / `slicer_estimate_store_dir`).

**STATUS — SHIPPED & CLOSED (2026-06-04). No longer deferred.** The poll-diff event source — the only piece that was left — landed on `main` as commit `4063f05` (feat: add Spoolman poll diff invalidation source); the controller/Laura merge + `.190` deploy gate that were outstanding have since completed. It was implemented on branch `feat/SPOOL-EVT-1-spoolman-change-source` (code-side). Spec: `spec-spool-evt-1-spoolman-change-source.md`. What shipped, against the 4-step plan above:
- `apps/api/app/modules/spools/service.py` — `SpoolsService.refresh_summary` gains an optional `change_handler: SnapshotChangeHandler | None` (a NEW generic, slicer-agnostic Protocol so spools owns ONLY snapshot retention + the diff handoff — no spools→slicer import). A NEW **additive** Redis key `spools:summary:prev:v1` (TTL `3600s`, comfortably > the 60s cadence; NOT the 30s public `_CACHE_KEY`) retains the previous successful snapshot. `_handle_snapshot_change` warms the baseline on the first poll (NO dispatch), then on subsequent ticks hands `(previous, current)` to the handler and advances the baseline **only after a clean handler run** (transient handler failure ⇒ same delta re-diffs next tick; downstream is idempotent — `mark_stale` + `_job_id`-deduped enqueue + in-place cost recompute). Handler errors are swallowed + logged (`spools.poll.change_handler_error`) — never break the poll/lock-release. The request-path `get_summary` cold-cache refresh calls `refresh_summary` WITHOUT a handler, so it never dispatches nor retains a baseline.
- `apps/api/app/modules/slicer/spoolman_event_source.py` — NEW. `SpoolmanInvalidationHandler` implements `SnapshotChangeHandler`: diffs filaments by `spoolman_filament_ref`, gates on `classify_spoolman_delta(old,new) is not None` BEFORE the O(all-estimates) `lookup_affected_keys` scan (no-op/irrelevant change ⇒ skip), and for each `AffectedGroup` with non-empty `affected_keys` calls `apply_spoolman_filament_change` once per pinning intent. Added/removed refs (name/vendor/material edits that re-key the ref) and empty-key groups are intentionally not dispatched. `build_spoolman_invalidation_handler(arq_pool, settings=…)` is the settings-wired composition root.
- `apps/api/app/workers/spoolman_poll.py` — the cron now builds the handler with `_ctx["redis"]` (the arq pool arq injects per job; `worker.py:361`) and passes it as `change_handler`. No second Spoolman read — the handler consumes the snapshot the poll already fetched.
- Tests: `apps/api/tests/test_slicer_spoolman_event_source.py` (13 cases, on-disk tmp + fakeredis, no Orca/httpx/real-Redis) — handler no-op/cost-only/mapped/missing-attribution/added-ref/empty-keys + service first-poll-warmup/dispatch/handler-error-isolation/request-path-isolation + cron-wiring.

**Scope fences at the time this slice shipped (historical):** this event-source slice itself carried NO catalog→`stl_hash` ingestion, NO `POST /api/estimates/recompute`, NO UI, NO second Spoolman poll. NOTE (reconciled 2026-06-04): EST-INGEST-1 (commit `5b10f71`) and EST-RECOMPUTE-1 (commit `e00bfd4`) have since shipped separately on `main` — they are no longer deferred (see their entries below); the NO-UI / NO-second-Spoolman-poll fences remain accurate for this slice. The end-to-end "Spoolman change auto-updates estimates" now works **for estimate keys that have been resolved+persisted through the SPOOL-PREQ-1 attribution index** — it does NOT auto-derive estimates for catalog parts that were never sliced (that needs EST-INGEST-1). A missing attribution record or an as-yet-uncomputed bundle is a no-dispatch, by design.

**DEPLOY CAVEAT (SW-DEPLOY-1-adjacent):** the cron runs in the **api-arq-worker** container (queue `arq:api`). The mapped-override path re-resolves the intent there (writes a bundle to the bundle-store volume, reads vendored profiles) and enqueues the re-slice onto the dedicated slicer queue (`arq:slicer`) where the slicer-worker overlay executes it. So the api-arq-worker needs the vendored-profiles dir + bundle/estimate/attribution store volumes mounted (it shares the api image+volumes, which already resolve intents). No NEW worker image is required for this slice (no new slicer module the slicer-worker must import — `spoolman_event_source` runs api-side), but the standard SW-DEPLOY-1 overlay rebuild + in-container smoke still applies on any deploy that bumps `portal-api`.

**Deferred perf note (carried, NOT built in SPOOL-PREQ-1):** `lookup_affected_keys` does one `iter_all_estimates` pass per changed ref — O(all estimates). If a future Orca-upgrade-scale bulk diff makes that hot, add a `bundle_hash → {stl_hash}` index written at estimate-persist time (`worker_job.slice_estimate`, where both hashes are in scope) to make the join O(bundles-for-ref). Intentionally not built now (no second index; reuse existing iteration).

**SW-DEPLOY-1 reminder:** the mapped-override path enqueues a re-slice that runs on the slicer-worker overlay, so any deploy of 32.5 must follow the SW-DEPLOY-1 manual overlay rebuild + in-container import/Orca/resolve-override smoke above (the new `overrides`/`SpoolmanOverrideProvider`/`spoolman_invalidation` modules + the `SpoolmanFilament.extra` field must reach the worker image).

---

## Deferred from: Story 32.6 dev-story (2026-06-02)

Source: Story 32.6 (frontend `PrintIntentPreset` selector + estimate display + the narrow estimate read/resolve API seam) AC-1b explicit-optional deferral. The read-only seam (AC-1, `GET /api/estimates`) shipped; the optional guarded recompute-enqueue endpoint (AC-1b) was judged unnecessary for the 32.6 display MVP and deferred per the AC-1b "OPTIONAL for the MVP slice … MAY be deferred to a follow-up (recorded in `deferred-work.md`)" clause.

### EST-RECOMPUTE-1 — optional guarded `POST /api/estimates/recompute` enqueue endpoint

**STATUS: SHIPPED & CLOSED (2026-06-04). No longer deferred.** Landed on `main` as commit `e00bfd4` (feat(estimates): add guarded recompute now action) — the Laura review/gates/merge/deploy that were pending have since completed (originally implemented on branch `feat/EST-RECOMPUTE-1-recompute-now`). Promoted once EST-INGEST-1 shipped (catalog `ModelFileRead` carries real per-part `sha256`; production dry-run found 525 STL parts ready for ingestion), creating the real user need to (re)queue estimates from the UI. What landed:
- Backend: authenticated, CSRF-gated, non-public `POST /api/estimates/recompute` in `apps/api/app/modules/slicer/router.py` taking the SAME preset-resolution inputs as the GET read (as a validated `RecomputeRequest` body). `validate_content_hash`-gates `stl_hash` before resolve/store/queue; resolves via the SAME resolver seam; reuses Story 32.4 `enqueue_recompute` byte-identically (no re-derived job-id/queue, no source-file hashing, no new worker job). Idempotency/self-DoS guard: already-`queued` ⇒ no re-enqueue (`enqueued=false`); `fresh`/`stale` ⇒ enqueue + `mark_queued`; `absent`/`failed` ⇒ enqueue by hash WITHOUT fabricating numbers (honest projected state). Returns a narrow UI-safe `RecomputeResponse {enqueued, estimate: EstimateView}` (no `bundle_hash`/job-id/queue/g-code leak). Arq injected via the `get_arq_pool` dependency seam (fakeable in tests).
- The read-vs-enqueue divergence the fix sketch flagged is resolved: `SettingsEstimateResolver` gained a `persist_bundle` flag; the recompute resolver (`get_recompute_resolver`) uses the REAL writing `BundleStore` so a content-miss bundle is persisted before the worker's by-hash load (the GET read path stays non-mutating, `persist_bundle=False`).
- Frontend: `useRecomputeEstimate` TanStack mutation (via `api()`, invalidates the exact estimate query key) + a recompute button on `EstimateDisplay` for `absent`/`stale`/`failed` states (none on `fresh`/`queued`), wired through `EstimatesPanel`; en/pl strings added; copy stays honest (no live-Spoolman-propagation promise — i18n-honesty test still green).
- Tests: 10 backend pytest cases in `tests/test_estimate_api.py` (auth, malformed-hash short-circuit, resolver-422, queued-idempotent, fresh/stale enqueue-once+mark_queued, absent/failed no-fabrication, deterministic 32.4 enqueue kwargs via fake arq, no-internal-leak); the scope-fence test in `tests/test_slicer_worker.py` updated to allow exactly one guarded POST while preserving intent (one GET + one POST, reuses 32.4 plumbing, no bulk/unbounded/source-write surface). Frontend vitest: `useRecomputeEstimate.test.tsx` (3) + 8 new `EstimateDisplay` button cases.
- **Deploy note still applies:** this endpoint's enqueue runs on the `portal-slicer-worker` overlay — its deploy MUST follow the SW-DEPLOY-1 manual overlay rebuild + in-container import/Orca smoke. Full `check-all.sh` (incl. Playwright visual regression for the new button) is Laura's closeout gate — NOT run from this dev session.

The original deferral rationale + fix sketch are retained below for history.

**Source:** Story 32.6 AC-1b (explicit optional deferral) + the AC-9 scope fence.

**Where:** would live in `apps/api/app/modules/slicer/router.py` (the new estimates router), reusing the **existing** Story 32.4 `apps/api/app/modules/slicer/recompute.py` (`enqueue_recompute` / `invalidate`) + `enqueue.py` primitives byte-identically (CALLED, not edited). FE affordance would mount in `apps/web/src/modules/estimates/` (a "recompute now" button on `EstimateDisplay` for an `absent`/`stale` key).

**Problem:** Story 32.6 ships only the read-only seam: `GET /api/estimates` resolves a `PrintIntentPreset` → `bundle_hash`, reads the persisted `EstimateRecord`, and projects the UI-safe DTO; an absent/stale record is a terminal display state until something *else* marks it (the deferred live event source, SPOOL-EVT-1, or an operator/ops trigger). There is **no** authenticated endpoint that lets the UI (re)queue a slice for an already-resolvable `(stl_hash, preset→bundle_hash)` whose record is `stale`/`absent`. So the `EstimateDisplay` renders `absent`/`stale` as terminal-until-the-deferred-event-source-fires, with no user-driven "recompute now" path.

**Why deferred (not blocking 32.6):**
- The read seam alone satisfies the 32.6 display goal (FR20-PRESET-1 + FR20-FAILURE-1 FE half) — render every estimate state honestly. No "recompute now" affordance is in the 32.6 visual scope.
- Deferring keeps the **read-only** deploy path clean: a read-only seam changes no worker code path, so the standard API/web deploy suffices and the SW-DEPLOY-1 slicer-worker overlay-rebuild entanglement is avoided (an enqueue endpoint would re-queue a slice that runs on the `portal-slicer-worker` overlay, re-opening the SW-DEPLOY-1 window on every deploy).
- It is genuinely optional per AC-1b's own text ("include the enqueue seam only if a button-driven 'recompute now' is in the visual scope").

**Fix sketch (when promoted):** add a separate authenticated `POST /api/estimates/recompute` that (1) `validate_content_hash`-gates the caller `stl_hash`, (2) resolves the preset to `bundle_hash` via the SAME `SettingsEstimateResolver` path the read endpoint uses (note: the read path resolves through a non-mutating `_ReadOnlyBundleStore` — review blocker #1; an enqueue path that genuinely needs a persisted bundle must resolve through the real writing `BundleStore`, a deliberate divergence to call out), (3) calls the existing Story 32.4 `enqueue_recompute` for a `stale`/`absent` key only, idempotent per the 32.4 `_job_id` dedupe (no re-enqueue of an already-`queued` key — bounds the R1 self-DoS), returning `status="queued"`. Tests per AC-1b: `test_recompute_endpoint_enqueues_via_story_324_primitive`, `test_recompute_endpoint_idempotent_on_already_queued`, `test_recompute_endpoint_requires_auth`.

**Trigger / priority:** Real follow-up, **not blocking 32.6**. Promote when a user-driven "recompute now" affordance enters scope, OR alongside the catalog↔STL ingestion story (below) that first produces real per-part `stl_hash`es worth recomputing on demand. **Deploy note:** unlike the 32.6 read-only seam, this endpoint's enqueue runs on the slicer-worker overlay — its deploy MUST follow the SW-DEPLOY-1 manual overlay rebuild + in-container import/Orca smoke.

### EST-INGEST-1 — catalog↔STL ingestion (part → `stl_hash` linkage feeding the estimate read)

**STATUS: SHIPPED & CLOSED (2026-06-04). No longer deferred.** Landed on `main` as commit `5b10f71` (feat: ingest catalog STL estimates) — catalog `ModelFileRead` now carries real per-part `sha256`, feeding the Story 32.6 estimate read seam (and consumed by EST-DISPLAY-1 / EST-RECOMPUTE-1). The original deferral rationale + fix sketch below are retained for history.

**Source:** Story 32.6 AC-9 (explicit out-of-scope dependency) + the pre-enumeration grep (zero `stl_hash`/`content_hash` references under `apps/api/app/modules/catalog/`).

**Where:** `apps/api/app/modules/catalog/` (no `stl_hash` linkage today) ↔ the Story 32.3 `EstimateStore` content key `(stl_hash, bundle_hash)` the 32.6 read seam reads by.

**Problem:** There is no path from a catalog part to the content hash the estimate store is keyed by. 32.6 ships the display + read seam keyed by a **supplied** `stl_hash` (driven by a self-contained route/tests); it does NOT hash catalog STLs, persist a part→`stl_hash` map, or trigger a first slice. Until that ingestion lands, the live catalog-detail estimate is wired against supplied/known hashes, not auto-derived from every catalog part.

**Why deferred (not blocking 32.6):** building the ingestion (STL hashing + part→hash persistence + first-slice trigger) is broad work that exceeds the 32.6 display story; AC-9 surfaces it explicitly as OUT OF SCOPE rather than silently bridging it.

**Fix sketch (when promoted):** a dedicated ingestion story that hashes catalog STLs (reusing the existing `stl_cache`/content-hash discipline), persists the part→`stl_hash` map, and triggers the first resolve+slice — feeding real hashes into the 32.6 read seam (and EST-RECOMPUTE-1 if promoted).

**Trigger / priority (historical — now SHIPPED, see STATUS above):** Real follow-up, **not blocking 32.6**. Promote when the live catalog-detail estimate (auto-derived per part) is needed end-to-end.

---

## Deferred from: SPOOL-PREQ-1 review (2026-06-03)

Source: 3 BMAD adversarial subagent reviews (Blind Hunter, Edge-Case Hunter, Acceptance Auditor) of `feat/SPOOL-PREQ-1-spoolman-reverse-index`. Auditor APPROVE; the two Important edge-case findings (empty-string ref recorded; whole-intent dedup bloat) were patched in-flight (falsy-ref guard in `resolver._record_attribution`; dedup-by-`bundle_hash` in `AttributionStore.record`). One finding is parked as genuinely out of this story's scope.

### SPOOL-PREQ-1-D1 — blank-field Spoolman filaments collapse toward a degenerate `spoolman_filament_ref`

**Source:** Edge-Case Hunter [Important, re-scoped to defer].

**Where:** `apps/api/app/modules/slicer/overrides.py:174` `spoolman_filament_ref` — `(vendor_name or "") ∥ (material or "") ∥ name`.

**Problem:** A Spoolman filament with blank `vendor_name` + blank `material` yields a near-degenerate ref `"\x1f\x1f<name>"`; all-blank yields `"\x1f\x1f"`. Two distinct near-empty filaments can collapse toward the same ref bucket, which the SPOOL-PREQ-1 index (and any future SPOOL-EVT-1 diff) would then over-join. SPOOL-PREQ-1's `""`-ref guard closes the *empty-string* pin, but not the `"\x1f\x1f"` degeneracy, which originates upstream in the ref derivation.

**Why deferred (not fixed in SPOOL-PREQ-1):** the ref-derivation contract is owned by `overrides.py` / Story 32.5, not by this story's reverse index. A blank-vendor+blank-material+blank-name Spoolman record is not a realistic inventory state, and guarding it belongs at the ref-derivation seam (e.g. reject/skip a blank ref in `spoolman_filament_ref`, or require a non-blank Spoolman name) — fixing it inside the attribution store would be the wrong layer. Surfaced so a future Spoolman-ingestion hardening pass can decide the upstream policy.

**Trigger / priority:** Low. Promote if real Spoolman inventory ever produces blank vendor/material/name filaments, or alongside SPOOL-EVT-1 when the poll-diff first consumes real `spoolman_filament_ref`s.

---

## Deferred from: STL estimate profile-availability gating — product decision (2026-06-04)

Source: operator/controller product decision after runtime verification of the EST-DISPLAY-1 compact STL estimate profile selector (commit `60e4dd1 fix(catalog): compact STL estimate profile selector`). This is a **recorded product/UX decision**, not a review finding — the decision is made; the implementation is the parked bridge work below. No code is changed by this entry.

### EST-TIERS-1 — gate the Catalog STL estimate selector to actually-resolvable process profiles (no 422 path)

**Source:** Operator/controller product decision (2026-06-04), grounded in controller runtime + code evidence.

**Where:**
- FE: `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx` (the compact `quality_tier`-only selector) + `apps/web/src/modules/estimates/lib/preset.ts` (`QUALITY_TIERS = ["aesthetic", "standard", "strong"]`, `DEFAULT_QUALITY_TIER = "standard"`). The selector renders all three tiers as plain `<option>`s; the standalone `PrintIntentPresetSelector` shares the same `QUALITY_TIERS` source.
- BE contract: `apps/api/app/modules/slicer/router.py:131-136` catches `PresetResolveError` from the resolver and returns **HTTP 422** `detail="preset not resolvable"` for `GET /api/estimates`; lines 138-140 read the estimate store only AFTER a successful resolve; `apps/api/app/modules/slicer/estimate_read.py:164-178` projects a store miss for a *resolvable* profile as **HTTP 200** body `status="absent"` (null numerics).
- Vendored intents: `/data/content/slicer/vendored/intents/creality-k1-max-microswiss-hf/PLA/` on `.190` contains only `standard.json`; `aesthetic.json` and `strong.json` are absent.

**Problem:** The selector exposes `aesthetic` / `standard` / `strong`, but only `standard` is vendored for the catalog printer/material identity (`creality-k1-max-microswiss-hf` · PLA). Controller live resolver smoke (`SettingsEstimateResolver(redis_factory=None)`): `standard` resolves OK (`bundle_hash=25b03be589a4…`); `aesthetic` and `strong` both raise `PresetResolveError` reason `unsupported_material_class` (the resolver maps the missing intent partial to that classified failure). Through the router that surfaces as a user-facing **HTTP 422** the moment a member picks Aesthetic or Strong. Note the contract asymmetry the decision relies on: **missing process profile → 422**, whereas a **missing/backfilled estimate for an otherwise-resolvable profile → HTTP 200 `status="absent"`** — only the former is the failing path being closed here.

**Product decision (operator/controller, made — not open):**
- The interim path is **NOT** to fake / vendor placeholder Orca intent profiles for `aesthetic` / `strong`, and **NOT** to leave selectable options that 422.
- Implement the safe transition state: the Files/STL estimate selector must expose **only process profiles that are actually resolvable** for the selected printer/material, **or** clearly **disable** the unavailable ones without firing a failing request.
- Preferred compact UX: **Standard selectable**; **Aesthetic / Strong may be shown but disabled** with short honest copy (e.g. "profile not imported yet") if visibility is judged useful — otherwise omit them. **No 422 / no error toast / no error path** reachable from this surface.
- Availability must **not be hardcoded in the frontend** — add / adjust the backend contract if needed so the FE derives which profiles are resolvable for a given printer/material rather than baking the `standard`-only assumption into TS. (The `QUALITY_TIERS` constant is currently the hardcode that would have to go.)
- This is a **bridge** until the admin profile-management panel exists (the surface that will let an operator import/manage Orca intent profiles, at which point Aesthetic/Strong become genuinely available rather than gated).

**Why deferred (not built in this entry):** This entry **records the decision**; the controller task explicitly scopes to artifact capture with no application-code change, no profile vendoring, no backfill. The implementation is a follow-up quick-dev story.

**Fix sketch (when promoted):**
- BE: expose resolvable-profile availability per `(printer_ref, material_class)` so the FE can query it — e.g. a small read endpoint or an `available: bool` projection per tier — instead of the FE assuming `standard`-only. Keep `GET /api/estimates` semantics unchanged (still 422 for a genuinely unresolvable preset; the FE simply stops offering it).
- FE: drive the `CatalogEstimateProfileSelector` options from that availability signal (replace the static `QUALITY_TIERS` map): resolvable tiers selectable; unavailable tiers either omitted or rendered `disabled` with the "profile not imported yet" copy (en + pl parity). Default stays `standard` (the EST-INGEST-1 ingest default, guaranteed resolvable). No request fires for a disabled tier.
- This is a **visible UI change** → it must clear the **mockup / render mini-gate** before merge, plus the standard `npm run test:visual` baseline pass.

**Trigger / priority:** Real should-fix product correction — a currently-reachable user-facing 422 on a member surface. Promote as a small quick-dev story now (bridge), and **fold into / supersede by the admin profile-management panel initiative** when that lands (the panel removes the gate by making the missing profiles importable). Cross-ref: EST-DISPLAY-1 spec "Implementation note — EST-TIERS-1 quality-tier availability bridge" section (`spec-est-display-1-filestab-estimate-chip.md`).

**STATUS — IMPLEMENTED via `bmad-quick-dev` (2026-06-04, author of record), pending controller review / full gate / merge / deploy.** Promoted from the parked decision above and built on branch `fix/EST-TIERS-1-quality-tier-availability`. The earlier exploratory Hermes draft (explicitly non-authoritative) was **inspected and adopted with one correctness fix** through the quick-dev flow — it is no longer a non-authoritative draft. What landed:
- **Backend availability contract** — `GET /api/estimates/quality-tiers?material_class=…&printer_ref=…` (`apps/api/app/modules/slicer/router.py`, schemas in `schemas.py`). Resolves each portal quality tier through the **same** `resolve_preset` resolver seam as `GET /api/estimates`; a `PresetResolveError` becomes a UI-safe `{quality_tier, available:false, reason:"profile_not_imported"}` row (no path/Orca leak) instead of a user-triggered 422. `GET /api/estimates` + `POST /api/estimates/recompute` semantics are unchanged (still 422 for a genuinely unresolvable preset; still HTTP 200 `status="absent"` for a resolvable store miss). Authenticated, not in `_PUBLIC_ROUTES`.
- **Frontend consumption** — `useQualityTierAvailability` hook (5-min `staleTime`) + `FilesTab` passes the result to `CatalogEstimateProfileSelector`. Unavailable tiers render `disabled` with honest copy (`<profile> — profile not imported yet` / `profil niezaimportowany`); the selector ignores change events for disabled tiers, so **no chip/panel re-key and no estimate read/recompute request fires** for Aesthetic/Strong while their profiles are missing. Standard stays selectable.
- **Correctness fix on adoption (not in the draft):** availability is **fail-open** — a tier is disabled only when the backend explicitly returns `available:false`. An in-flight, empty, or errored availability fetch leaves every tier selectable, so a transient availability-endpoint failure can never lock out Standard (the draft's `=== true` + `?? []` would have disabled the whole selector, including Standard, on a fetch error). Regression test added (`CatalogEstimateProfileSelector.test.tsx` — empty list keeps all tiers selectable).
- **i18n** — `modules.estimates.selector.profile_unavailable_option` added to en.json + pl.json.
- **Mockup / render mini-gate** — `.hermes/sketches/t_41d3aef1/quality-tier-availability-disabled.html` (gitignored scratch) renders the chosen "visible-but-disabled" direction; a Playwright case `filestab-estimate-tiers-disabled.png` was added to `apps/web/tests/visual/catalog-filestab-estimate.spec.ts`.
- **Focused gates run (this session):** `pytest tests/test_estimate_api.py` 23 passed; `vitest` selector + FilesTab 29 passed; web `tsc -b` + `eslint --max-warnings=0` clean; `ruff format --check` + `ruff check` clean on the changed Python.
- **Gate-fix follow-up (2026-06-04, post-controller `check-all`):** the controller's full `check-all.sh` passed 14 stages and surfaced two real failures in this dev's authored surface, now fixed (focused-scope only):
  1. **API scope-fence test** (`tests/test_slicer_worker.py::test_slicer_module_mounts_only_narrow_estimates_read_router`) still asserted a single `@router.get`. EST-TIERS-1 legitimately adds a second narrow authenticated GET. Updated the fence to its true shape — **exactly two GETs** (quality-tier availability + estimate read) **and one POST** (guarded recompute), with an added `"/quality-tiers"` path assertion; the no-bulk / no-source-write / reuse-Story-32.4-enqueue invariants are unchanged. Repro: `pytest tests/test_slicer_worker.py` → **49 passed**.
  2. **Visual case** (`catalog-filestab-estimate.spec.ts`) timed out. Two real bugs: (a) the generic `**/api/estimates**` route **shadowed** `/api/estimates/quality-tiers`, so the availability rows never reached the selector — the earlier "fail-open → identical render" assumption was wrong; it broke the *new* case. Fix: fold both reads into **one** `**/api/estimates**` handler that branches on the path, so precedence semantics no longer matter and no tiers request is left unhandled (which would also stall `waitForReady`'s `networkidle`). (b) the option assertion matched **English** copy, but the visual projects render **pl-PL** (`locale: "pl-PL"` → i18n navigator detect). Fix: assert the locale-independent disabled DOM state (`option[value="strong"][disabled]`); the localized honest copy is pixel-verified by the snapshot. Existing chip baselines (fresh/stale/absent/expanded) are **unchanged** — full spec re-run **20 passed**. The 4 new `filestab-estimate-tiers-disabled-*` baselines (desktop/mobile × light/dark) were generated + inspected: the closed compact selector matches the `fresh` state byte-for-byte (Standard selectable + selected), with Aesthetic/Strong disabled in the native dropdown.
- **NOT done by this dev session (controller-owned):** re-run of full `infra/scripts/check-all.sh`, external review, commit/ff-merge/deploy, and **committing the 4 new untracked `tiers-disabled-*` baseline PNGs** (generated + verified locally this session; baseline ownership stays with the controller per the EST-DISPLAY-1 precedent). Deploy note: this is a **read-only** API addition + FE — it does **not** enqueue a slice, so the SW-DEPLOY-1 slicer-worker overlay rebuild is **not** triggered by this change (no new slicer-worker module).

**Prerequisite / runtime blocker — t_81a1e5bd estimate backfill BLOCKED by `unparseable_time` (2026-06-04).** Independent of EST-TIERS-1's FE gating: the Kanban backfill task `t_81a1e5bd` safe-enqueued 525 STL estimate jobs, but the live slicer-worker persisted sampled estimates as **`failed` / `unparseable_time`**. Pause point: `fresh=0`, `failed=12`, `absent=513`, `arq:slicer queued=501`, slicer-worker **stopped/paused**. Resuming or draining the queued slicer work is gated on a parser/runtime fix — Kanban `t_e4afd776` / **EST-PARSE-1** (parser/runtime fix prerequisite) — which must land before the backfill is retried. Do NOT resume the worker or drain/purge the queue until that fix is in.

**Runtime-freshness caveat (applies repo-wide, 2026-06-04).** The shipped-on-`main` estimate-chain commits (EST-INGEST-1 `5b10f71`, EST-RECOMPUTE-1 `e00bfd4`, EST-DISPLAY-1 `c4d9cad`/`60e4dd1`, SPOOL-PREQ-1 `35360d6`, SPOOL-EVT-1 `4063f05`) are truthful as **shipped code on origin/main**, but shipped code does **not** imply fresh production estimates: live estimate coverage stays stale until the EST-PARSE-1 / t_e4afd776 parser fix and the t_81a1e5bd backfill complete.

---

## Deferred from: operator discussion — profile library delete/update lifecycle (2026-06-07)

Source: operator request after reviewing current PROFILE-LIB-1 / PROFILE-OFFER-1 behavior: hard-deleting a profile block that is already referenced by a `PrintProfileOffer` currently succeeds, and the next offer read revalidates the offer as `invalid` with `unknown_block`. That is technically safe but too easy to do accidentally.

### PROFILE-LIB-GUARD-1 — block deleting profile blocks that are referenced by offers

**Source:** Operator request, "Opcja A" from the delete-behavior discussion (2026-06-07).

**Where:**
- Backend: `apps/api/app/modules/slicer/admin_router.py` `DELETE /api/admin/profiles/library/{block_id}`.
- Engine helpers: `apps/api/app/modules/slicer/profile_offer.py` / `profile_library.py`.
- Tests: `apps/api/tests/test_admin_profile_library.py`, `apps/api/tests/test_admin_profile_offers.py`.

**Problem:** `profile_library.delete_block(root, block_id)` removes the block body + manifest without checking whether any offer sidecar references that `block_id` in its embedded `chain`. Read-time offer revalidation then marks affected offers `invalid unknown_block`; the offer is not eagerly deleted. This is a good fail-safe after accidental external filesystem loss, but it is a poor admin UX for an intentional in-product delete.

**Desired behavior:** The admin delete endpoint should fail closed when the block is referenced by one or more offers:

- `DELETE /api/admin/profiles/library/{block_id}` returns **409 `profile_block_in_use`** when any offer chain references the block.
- Response includes a leak-fenced list of affected offers, e.g. `{offer_id, label, publish_state}` only; no raw Orca body, no filesystem path.
- No block files are deleted and no `slicer_profile.library_delete` audit is emitted on the refused delete.
- Non-referenced block delete keeps existing semantics: 204 on first delete, 404 on re-delete, audited.
- Keep current read-time `invalid unknown_block` behavior as a resilience fallback for out-of-band filesystem deletion or corrupted state; do not remove that test/contract.

**Fix sketch:** Add a pure helper like `profile_offer.offers_referencing_block(root, block_id) -> list[dict]` that scans `list_offers(root)` and checks `sidecar["chain"].values()`. Call it in `delete_profile_block` before `profile_library.delete_block`. If non-empty, raise `_reject(409, "profile_block_in_use", ...)` with a structured, leak-fenced payload. Add tests for: referenced block delete returns 409 and leaves block intact; unreferenced block delete still 204/audited; out-of-band delete still causes offer list/get to show `invalid unknown_block`.

**Trigger / priority:** Should-fix soon before heavier operator use of the profile library. This is a small safety story and can be bundled with the offer freshness/resync UX below if that story is promoted.

### PROFILE-OFFER-SYNC-1 — detect stale published offers after profile-block upsert and offer one-click republish/reslice

**Source:** Operator request (2026-06-07): after a profile block upsert/update, show that affected offers require republish/reslice and allow doing it now or later; on the offers screen, show a status badge that the offer is not current plus an adjacent resync/reslice/re-estimate action.

**Where:**
- Backend import/upsert: `POST /api/admin/profiles/library` in `apps/api/app/modules/slicer/admin_router.py`.
- Offer publish state: `apps/api/app/modules/slicer/profile_publish.py` and `profile_offer.py` sidecars under `<root>/offers/*.json`.
- Offer DTOs: `apps/api/app/modules/slicer/schemas.py` `PrintProfileOffer`.
- Frontend: `apps/web/src/modules/admin/ProfileLibraryPage.tsx`, `ProfileOffersPage.tsx`, hooks under `apps/web/src/modules/admin/hooks/`.
- Tests: backend offer/library tests; frontend ProfileOffersPage/ProfileLibraryPage tests; visual baseline for the stale badge/action.

**Problem:** Re-importing a library block with the same `(profile_type, name)` is an atomic upsert with the same `block_id`, so existing offers keep referencing it. However, if that block affects slicing, any already-published offer still carries its old `published_bundle_hash` / estimate until the operator republishes. Today there is no explicit stale/sync state in the offer DTO and no UI prompt after upsert, so an operator can believe the offer reflects the new profile when the published bundle still reflects the old one.

**Desired behavior:**

1. **On profile block upsert/update:** if the imported block overwrote an existing block and that block is referenced by any published offer, the UI shows a modal/banner: "Affected offers require republish/reslice" with affected offer labels and two choices:
   - **Republish/reslice now** — call the existing publish path for each affected offer, using each offer's existing `published_stl_hash` when present.
   - **Later** — leave offers marked stale.
2. **On the offers screen:** each offer shows a sync badge derived from read-time state, e.g. `current`, `stale`, `unpublished`, `invalid`, `queued/recomputing` if available. Stale offers get an adjacent `Republish / reslice` action.
3. **Backend contract:** expose enough data for the frontend without raw Orca bodies or internal paths. A candidate DTO addition: `sync_state`, `sync_reasons`, and `affected_by_block_update` / `needs_republish` metadata. Keep `publish_state` as the existing persisted state; add sync as a derived/read-time projection.
4. **No automatic silent reslice.** The operator must explicitly choose "now"; otherwise the system only marks/surfaces stale. This avoids surprise CPU/queue spikes.

**Implementation notes / design options:**

- Staleness detection must be deterministic and cheap enough for list view. Prefer a sidecar fingerprint over re-running full Orca resolve on every list:
  - At publish time, store a `published_chain_fingerprint` derived from the referenced block manifests/bodies or manifest `imported_at`/content hash.
  - At read time, recompute the current chain fingerprint from referenced blocks; mismatch + `publish_state=published` ⇒ `sync_state=stale`.
  - If a referenced block is missing, `validation_state=invalid` still wins.
- If exact bundle freshness is required, a later stronger variant can dry-resolve the chain and compare to `published_bundle_hash`, but do not make offer-list rendering mutate bundle stores or enqueue jobs.
- Reuse existing `POST /api/admin/profiles/offers/{offer_id}/publish`; if `published_stl_hash` is present, the FE can republish with that hash. If absent, require operator to choose an STL before resync.
- The profile-import response may need an additive envelope or a sibling endpoint to report `affected_offers`. Avoid breaking the existing `ProfileLibraryBlock` response unless the API-types and FE callers are migrated in the same story.

**Acceptance sketch:**

- Given an offer is published and references process block P, when P is upserted with the same name/type but changed content, then the offer list returns `sync_state="stale"` and the FE shows a stale badge plus resync action.
- Given the operator clicks resync, then the existing publish path is called with the offer's previous `published_stl_hash`, a new publish state is written, and the stale badge clears after refetch.
- Given the operator chooses later after import, then no slice is enqueued and the stale badge remains visible.
- Given an unpublished offer references the updated block, then import may show it as affected but the offer is not `stale`; it is simply `unpublished` / not-current by definition.
- Given an invalid offer with a missing block, `invalid` wins over `stale`.

**Trigger / priority:** Product/ops should-fix. Promote after or with PROFILE-LIB-GUARD-1; highest value once profile updates become routine and offers are actually member-facing / relied on for production estimates.

---

## Deferred from: operator queue — Files tab STL/source/3MF delete UI (2026-06-14)

Source: operator request: "Nie mogę z poziomu portalu usunąć plików STL z modelu... Nie ma takiego przycisku..."

Tracked as sprint-status backlog row: `37-1-stl-file-delete-ui`.
Story sketch: `_bmad-output/implementation-artifacts/37-1-stl-file-delete-ui.md`.

**Problem:** The backend already exposes admin file deletion and `PhotosTab` already has a confirmation-driven delete UX, but `FilesTab` does not expose a delete button for STL/source/3MF rows. Operators cannot remove uploaded STL files from the portal UI.

**Desired behavior:** Add a Files tab delete action using the existing `useDeleteFile(modelId)` / `DELETE /api/admin/models/{model_id}/files/{file_id}` path, with confirmation, query invalidation, selected-file fallback/empty-state handling, i18n parity, tests, and visual coverage. Keep the delete affordance admin-scoped; do not expose file deletion to normal members by accident.

---

## Declined / done

_(none yet)_
