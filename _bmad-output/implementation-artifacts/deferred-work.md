# Deferred Work — quick-dev review backlog

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

**SW-DEPLOY-1 reminder:** the mapped-override path enqueues a re-slice that runs on the slicer-worker overlay, so any deploy of 32.5 must follow the SW-DEPLOY-1 manual overlay rebuild + in-container import/Orca/resolve-override smoke above (the new `overrides`/`SpoolmanOverrideProvider`/`spoolman_invalidation` modules + the `SpoolmanFilament.extra` field must reach the worker image).

---

## Deferred from: Story 32.6 dev-story (2026-06-02)

Source: Story 32.6 (frontend `PrintIntentPreset` selector + estimate display + the narrow estimate read/resolve API seam) AC-1b explicit-optional deferral. The read-only seam (AC-1, `GET /api/estimates`) shipped; the optional guarded recompute-enqueue endpoint (AC-1b) was judged unnecessary for the 32.6 display MVP and deferred per the AC-1b "OPTIONAL for the MVP slice … MAY be deferred to a follow-up (recorded in `deferred-work.md`)" clause.

### EST-RECOMPUTE-1 — optional guarded `POST /api/estimates/recompute` enqueue endpoint

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

**Source:** Story 32.6 AC-9 (explicit out-of-scope dependency) + the pre-enumeration grep (zero `stl_hash`/`content_hash` references under `apps/api/app/modules/catalog/`).

**Where:** `apps/api/app/modules/catalog/` (no `stl_hash` linkage today) ↔ the Story 32.3 `EstimateStore` content key `(stl_hash, bundle_hash)` the 32.6 read seam reads by.

**Problem:** There is no path from a catalog part to the content hash the estimate store is keyed by. 32.6 ships the display + read seam keyed by a **supplied** `stl_hash` (driven by a self-contained route/tests); it does NOT hash catalog STLs, persist a part→`stl_hash` map, or trigger a first slice. Until that ingestion lands, the live catalog-detail estimate is wired against supplied/known hashes, not auto-derived from every catalog part.

**Why deferred (not blocking 32.6):** building the ingestion (STL hashing + part→hash persistence + first-slice trigger) is broad work that exceeds the 32.6 display story; AC-9 surfaces it explicitly as OUT OF SCOPE rather than silently bridging it.

**Fix sketch (when promoted):** a dedicated ingestion story that hashes catalog STLs (reusing the existing `stl_cache`/content-hash discipline), persists the part→`stl_hash` map, and triggers the first resolve+slice — feeding real hashes into the 32.6 read seam (and EST-RECOMPUTE-1 if promoted).

**Trigger / priority:** Real follow-up, **not blocking 32.6**. Promote when the live catalog-detail estimate (auto-derived per part) is needed end-to-end.

---

## Declined / done

_(none yet)_
