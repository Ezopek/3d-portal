---
baseline_commit: 7e7644105d49ad1a5dd621b6c1226db70e0bda40
---

# Story 35.6: Bounded default-matrix backfill + enqueue guardrails

Status: done

<!--
  Authored by the repo-local BMAD author (Laura/Hermes delegated). Source planning artifacts:
  epics.md § Initiative 23 (Epic E35 + Story 35.6); architecture.md § Initiative 23 Decision AS;
  SCP sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md § Task 8.
  FR23-BACKFILL-1 + NFR23-QUEUE-BOUND-1.

  GATE NOTE — G-BACKFILL-OPT-IN: exact per-filament override backfill is operator-opt-in only
  (never part of the default matrix). The default matrix covers ONLY material_defaults × active
  published offers. No concrete-filament N×M×K precompute.

  G-DEVGO: per-story gate; this file is the create-story output. Operator must give explicit
  dev-go before implementation begins.
-->

## Story

As an **operator running the portal**,
I want **the bounded default-matrix estimates to be pre-computed automatically whenever a
new STL is uploaded, a new profile offer is published, or a material default changes**,
so that **users see estimates immediately for all generic-material filaments without waiting
for a first-access slice, and the queue never explodes from concrete-filament N×M×K
precompute (FR23-BACKFILL-1, NFR23-QUEUE-BOUND-1).**

This is the **bounded default-matrix backfill + enqueue guardrails** slice of Epic E35.
It ships the three event-driven hooks (new-STL ingest, offer-publish, material-default-change)
and the operator-supervised one-shot `enqueue_default_matrix_backfill.py` script.
It does NOT re-implement policy precedence, resolver/bundle logic, or API/UI surfaces —
those were shipped in Stories 35.1–35.5.

---

## Acceptance Criteria

### A. `resolve_chain` extension (resolver.py)

- [x] **AC-1** `resolver.py::resolve_chain` gains an optional
  `profile_selection: ProfileSelection | None = None` parameter (default `None`).
  - When `None` → behavior is byte-identical to today (no regression).
  - When `source is EstimateProfileSource.unavailable_no_profile` →
    return `ResolveFailure(reason=ResolveReason.unavailable_no_profile, message=...)` immediately,
    before any hashing or writing (same guard that `resolve()` applies at line 444–452).
  - Otherwise → call `_apply_profile_selection(partials, profile_selection)` on the
    assembled partials dict BEFORE passing them to `_resolve_partials`, substituting the
    filament component with the policy-selected Orca profile.
  - When the selection succeeds, propagate it to the `ResolveSuccess` outcome via
    `.model_copy(update={"profile_selection": profile_selection})` (same pattern as
    `resolve()` lines 467–468).

### B. Matrix enumeration helper (new `slicer/matrix_backfill.py`)

- [x] **AC-2** New module `apps/api/app/modules/slicer/matrix_backfill.py` contains:
  - `MatrixCell` dataclass (frozen):
    `offer_id: str`, `offer_label: str`, `material: str`, `orca_profile_ref: str`.
  - `enumerate_matrix_cells(offers: list[dict], policy: ProfilePolicy) -> list[MatrixCell]`:
    - Iterates published offers only (`profile_publish.publish_state_of(sidecar).publish_state == "published"`).
    - For each published offer × each enabled `policy.material_defaults` entry where the
      material key is in `sidecar.get("compatible_material_categories", [])`.
    - Returns one `MatrixCell` per (offer, material) pair. NEVER includes `filament_overrides`
      entries (G-BACKFILL-OPT-IN: exact overrides are excluded from the default matrix).
    - A disabled material default (`enabled=False`) is not included.
  - `ResolvedMatrixCell` dataclass (frozen):
    `cell: MatrixCell`, `bundle_hash: str | None`, `profile_selection: ProfileSelection | None`,
    `resolve_failed: bool = False`.
  - `resolve_matrix_cells(cells, *, source, store, orca_version, validator) -> list[ResolvedMatrixCell]`:
    - For each `MatrixCell`, reads the offer sidecar, reconstructs its chain via
      `profile_offer.chain_of(sidecar)`, builds a `ProfileSelection(source=default_material_profile,
      orca_filament_profile_ref=cell.orca_profile_ref, selected_material=cell.material)`,
      calls `resolve_chain(chain, source=source, store=store, orca_version=orca_version,
      validator=validator, material_class=cell.material, profile_selection=profile_selection)`.
    - `ResolveSuccess` → `ResolvedMatrixCell(cell, bundle_hash=outcome.bundle.bundle_hash, ...)`.
    - `ResolveFailure` → `ResolvedMatrixCell(cell, bundle_hash=None, resolve_failed=True, ...)`;
      log one structured line per failure (offer_id + material + reason — NO profile body).
  - `load_active_matrix(root, policy_store, source, store, orca_version, validator)` convenience:
    loads `profile_offer.list_offers(root)`, loads `policy_store.load()`, calls
    `enumerate_matrix_cells` then `resolve_matrix_cells`; returns `list[ResolvedMatrixCell]`
    (cells with `bundle_hash=None` included so callers can count/log them).

- [x] **AC-3** `enumerate_matrix_cells` is a pure function (no I/O) — testable without disk.

### C. New script `scripts/enqueue_default_matrix_backfill.py`

- [x] **AC-4** New `apps/api/scripts/enqueue_default_matrix_backfill.py`:
  - Docstring + module-level usage examples matching the `enqueue_estimate_backfill.py`
    style (operator-supervised, NOT auto-run by `deploy.sh`).
  - `--dry-run` flag: enumerate matrix cells and STL count only; NO bundle resolution,
    NO enqueue. Reports `[dry-run] matrix_cells=K stl_count=S would_enqueue=W missing_stl=M`.
    `would_enqueue` = `matrix_cells × STL-with-file-on-disk` count (no freshness check in dry-run).
  - `--verbose` / `-v` flag: emit INFO-level structured logs.
  - `--include-overrides` flag (opt-in only): additionally run filament_overrides entries
    through the same pipeline (G-BACKFILL-OPT-IN: only when this flag is explicitly set;
    default is default-matrix only).
  - Live mode summary: `inspected=N cells=K enqueued=E already_fresh=F resolve_failed=R missing_stl=M errors=X`.
  - Exit 0 on success (even with some classified failures); exit 1 on unexpected error.

- [x] **AC-5** `BackfillStats` dataclass extended (or new `MatrixBackfillStats`) with:
  `inspected`, `cells_total`, `cells_resolved`, `cells_resolve_failed`,
  `enqueued`, `already_fresh`, `missing_stl`, `errors`.

- [x] **AC-6** `run()` function is seam-injected (engine, stl_cache, estimate_store,
  arq_pool, matrix_cells: list[ResolvedMatrixCell], content_dir, dry_run) — same
  testability posture as `enqueue_estimate_backfill.py::run()`.
  For each `ResolvedMatrixCell` where `bundle_hash is not None` (resolved):
    - Walk all catalog `kind=stl` ModelFile rows (from DB via Session).
    - For each row: path-escape guard → missing-STL check → freshness check via
      `EstimateStore.read(stl_hash, cell.bundle_hash)` → skip if `EstimateStatus.fresh` →
      enqueue via `enqueue_slice_estimate(arq_pool, source_stl=..., bundle_hash=cell.bundle_hash, stl_cache=stl_cache)`.

### D. STL ingest hook (`ingest.py` + `sot/admin_router.py`)

- [x] **AC-7** New async function in `apps/api/app/modules/slicer/ingest.py`:
  ```python
  async def ingest_stl_for_default_matrix(
      model_file: ModelFile,
      *,
      resolved_cells: list[ResolvedMatrixCell],
      arq_pool: Any,
      stl_cache: StlCache,
      estimate_store: EstimateStore,
      content_dir: Path,
  ) -> list[IngestResult]:
  ```
  For each `ResolvedMatrixCell` with `bundle_hash is not None`: calls `ingest_stl_part`
  with the `model_file` and the cell's `bundle_hash` (synthetic `resolve_fn` that always
  returns a `ResolveSuccess` with the pre-resolved bundle). Returns one `IngestResult` per cell.
  Cells with `bundle_hash=None` are logged (one line) and excluded from the result list.
  A classified failure on one cell does NOT stop the others.

- [x] **AC-8** In `apps/api/app/modules/sot/admin_router.py::admin_upload_file`
  (currently around line 447), AFTER the `session.commit()` + `tmp_path.rename(final_path)`
  path and ONLY when `kind == ModelFileKind.stl`:
  - Load the active resolved matrix via `load_active_matrix(...)` using settings-wired seams.
  - Call `ingest_stl_for_default_matrix(file_row, resolved_cells=..., arq_pool=request.app.state.arq, ...)`.
  - Wrap in a `try/except Exception` that logs the error structured
    (`"slicer.matrix_ingest_hook.error"`) but never re-raises — the STL upload response
    is never 500'd by a backfill side-effect.
  - No `BackgroundTasks` needed (matrix resolution is bounded I/O; homelab scale).

### E. Offer-publish hook (`slicer/admin_router.py`)

- [x] **AC-9** In `apps/api/app/modules/slicer/admin_router.py::publish_profile_offer`
  (around line 1162), AFTER `profile_publish.publish_offer(...)` succeeds:
  - Read the just-published offer sidecar: `sidecar = profile_offer.read_offer(source.root, offer_id)`.
  - Build a single-offer matrix: `cells = enumerate_matrix_cells([sidecar], store.load())`.
    (Loads the policy via `ProfilePolicyStore(settings.slicer_profile_policy_dir).load()`.)
  - If `cells` is non-empty: resolve bundles for those cells only, then walk ALL catalog STLs
    and enqueue (stl_hash, bundle_hash) pairs that are not already fresh.
  - Use `arq_pool` (already available as a dep at line 1151) for enqueue calls.
  - Wrap in `try/except Exception` — a backfill failure must NEVER roll back the publish.
  - Log summary: `"slicer.offer_publish_matrix_hook"` with `offer_id`, `cells_count`, `enqueued`.

### F. Material-default change hook (`slicer/admin_router.py`)

- [x] **AC-10** In `apps/api/app/modules/slicer/admin_router.py::upsert_material_default`
  (around line 1392), AFTER `store.save(candidate)`:
  - Compare old vs. new material default for the changed `norm` key:
    - If `orca_filament_profile_ref` CHANGED (or this is a brand-new entry that is enabled):
      trigger re-enqueue for all published offers where `norm` is in
      `offer.compatible_material_categories` × all catalog STLs.
    - If only `enabled` changed (profile ref unchanged): no re-enqueue needed.
    - If the entry was disabled → no enqueue (disabled defaults yield no new bundles).
  - Mechanism: use `load_active_matrix(...)` filtered to the changed material only
    (enumerate only the new `candidate` policy, not the old one — old bundles become
    orphaned cache automatically, no explicit staleing needed per Decision AS).
  - An arq pool is needed: access via `request.app.state.arq` (the `request: Request`
    param is already present at line 1398).
  - Wrap in `try/except Exception` — a backfill failure must NEVER roll back the policy save.
  - Log summary: `"slicer.policy_material_default_matrix_hook"` with `material`, `enqueued`.

### G. Tests

- [x] **AC-11** New `apps/api/tests/test_matrix_backfill.py`:
  - Tests for `enumerate_matrix_cells`:
    - Published offer + enabled default + compatible material → 1 cell returned.
    - Published offer + disabled default → 0 cells.
    - Unpublished offer → 0 cells.
    - Published offer + material NOT in `compatible_material_categories` → 0 cells.
    - `filament_overrides` entries NEVER appear in cells (G-BACKFILL-OPT-IN guard).
    - Two offers × two compatible materials → 4 cells.
  - Tests for `resolve_matrix_cells` (using a fake `resolve_chain` seam):
    - Success path: cell with resolved bundle_hash.
    - Failure path: `resolve_failed=True` cell, log emitted, others continue.
  - Tests for `enqueue_default_matrix_backfill.run()`:
    - Dry-run: no enqueue, correct `would_enqueue` count.
    - Live mode: already-fresh skip, enqueue path.
    - Resolve-failed cell: `cells_resolve_failed` incremented, no enqueue for that cell.
    - Missing STL: `missing_stl` incremented.

- [x] **AC-12** Extend `apps/api/tests/test_slicer_resolver.py` (or add to
  `tests/test_slicer_profile_selection.py`) with at least 2 tests for
  `resolve_chain(..., profile_selection=...)`:
  - `profile_selection=None` → byte-identical result to current `resolve_chain` call (no regression).
  - `profile_selection` with `default_material_profile` → success with filament component substituted.
  - `profile_selection` with `unavailable_no_profile` → `ResolveFailure(reason=ResolveReason.unavailable_no_profile)` returned early (no bundle written).

- [x] **AC-13** Deterministic test-count rule: 3 consecutive `pytest` runs produce the same
  count for the added/modified test files.

### H. Observability

- [x] **AC-14** Every `resolve_matrix_cells` failure emits exactly one structured log line:
  ```python
  logger.warning("slicer.matrix_backfill.resolve_failed", extra={
      "labels.offer_id": cell.offer_id,
      "labels.material": cell.material,
      "labels.reason": outcome.reason.value,
  })
  ```
  Never logs Orca profile body, filament names, or raw block contents.

- [x] **AC-15** Hook success summary lines (AC-9, AC-10) carry `offer_id`/`material`,
  `cells_count`, `enqueued`, `already_fresh` — never bundle body or filament data.

---

## Tasks / Subtasks

### 1. Extend `resolve_chain` (AC-1)

1. [x] **(RED)** In `tests/test_slicer_resolver.py` (or `test_slicer_profile_selection.py`),
   add 3 tests for `resolve_chain(..., profile_selection=...)` (AC-12): null=no-regression,
   default_material success, unavailable→failure. Run — fails (no `profile_selection` param yet).
2. [x] **(GREEN)** Add `profile_selection: ProfileSelection | None = None` to `resolve_chain`
   in `apps/api/app/modules/slicer/resolver.py`. Apply the guard + `_apply_profile_selection`
   + `model_copy` propagation (pattern from `resolve()` lines 444–468).
3. [x] **(VERIFY)** `pytest tests/test_slicer_resolver.py -q` — 3 new tests green, no regressions.

### 2. New `matrix_backfill.py` module (AC-2, AC-3)

4. [x] **(RED)** Create `apps/api/tests/test_matrix_backfill.py` with pure-function tests for
   `enumerate_matrix_cells` (AC-11 cases). Run — fails (module absent).
5. [x] **(GREEN)** Create `apps/api/app/modules/slicer/matrix_backfill.py` with
   `MatrixCell`, `ResolvedMatrixCell`, `enumerate_matrix_cells`, `resolve_matrix_cells`,
   `load_active_matrix` (AC-2).
6. [x] **(VERIFY)** `pytest tests/test_matrix_backfill.py::test_enumerate_matrix_cells_* -q` — green.

### 3. New backfill script (AC-4–6)

7. [x] **(RED)** Add `run()` + `BackfillStats` tests to `test_matrix_backfill.py` (AC-11 run
   tests). Run — fails (script absent).
8. [x] **(GREEN)** Create `apps/api/scripts/enqueue_default_matrix_backfill.py` with `run()`,
   `MatrixBackfillStats`, `_print_summary()`, `main()` (AC-4–6). Mirror structure of
   `enqueue_estimate_backfill.py` exactly (seam injection, argparse, exit codes).
9. [x] **(VERIFY)** `pytest tests/test_matrix_backfill.py -q` — all run tests green.

### 4. `ingest_stl_for_default_matrix` + STL upload hook (AC-7, AC-8)

10. [x] **(GREEN)** Add `ingest_stl_for_default_matrix` to `ingest.py` (AC-7).
11. [x] **(VERIFY)** `pytest tests/test_slicer_ingest.py -q` — no regressions.
12. [x] Wire the STL upload hook in `sot/admin_router.py::admin_upload_file` (AC-8).
    - Load active matrix: `load_active_matrix(source.root, ...)` using settings.
    - Call `ingest_stl_for_default_matrix` guarded in `try/except`.
    - Add `source: Annotated[VendoredProfileSource, Depends(get_import_profile_source)]`
      to the handler if not already present.
13. [x] **(VERIFY)** `pytest tests/ -q -k "upload"` — no regressions in upload path tests.

### 5. Offer-publish hook (AC-9)

14. [x] Wire the post-publish matrix hook in `slicer/admin_router.py::publish_profile_offer`
    (AC-9): load policy → enumerate cells for this offer → resolve → walk STLs → enqueue.
15. [x] **(VERIFY)** `pytest tests/test_slicer_policy_admin.py -q` — no regressions in
    publish tests.

### 6. Material-default change hook (AC-10)

16. [x] Wire the post-save matrix hook in `slicer/admin_router.py::upsert_material_default`
    (AC-10): compare old vs. new orca_filament_profile_ref → if changed, load offers →
    resolve cells → walk STLs → enqueue.
17. [x] **(VERIFY)** `pytest tests/test_slicer_policy_admin.py -q` — no regressions in
    material-default tests.

### 7. Observability + determinism (AC-14, AC-15, AC-13)

18. [x] Confirm structured log keys match AC-14/AC-15 (grep for `labels.offer_id`,
    `labels.material`, `labels.reason`).
19. [x] Run `pytest apps/api/tests/ -q` three consecutive times; confirm identical counts
    each run (AC-13).

---

## Senior Developer Review (AI)

### Critical Findings
- **Fixed:** `upsert_material_default` hook was triggering backfill for ALL materials compatible with the affected offers, potentially causing queue explosions. Refactored `enumerate_matrix_cells` to support `material_filter` and ensured the hook only backfills the changed material.
- **Fixed:** `enqueue_default_matrix_backfill.py` was ignoring the `--include-overrides` flag in live mode. Implemented Spoolman snapshot loading and manual override-cell addition in the production run path.
- **Fixed:** Redundant sidecar reads in `resolve_matrix_cells`. Introduced `offers_map` optimization to reuse pre-loaded sidecars, significantly reducing I/O during full matrix backfills.

### Important Findings
- **Fixed:** Dry-run `would_enqueue` count in the backfill script was ignoring filament overrides even when requested. Corrected the count logic to include overrides in the enumeration phase.
- **Verified:** `resolve_chain` extension correctly handles `ProfileSelection` metadata and propagates it to `ResolveSuccess`, ensuring policy provenance is preserved in the backfill path.
- **Verified:** All event-driven hooks (STL upload, offer publish, material default change) are properly guarded with `try/except` and structured logging, preventing backfill side-effects from failing primary admin operations.

### Minor Findings
- **Added:** New test case `test_enumerate_with_material_filter_returns_only_matching_cells` to verify the fix for the critical backfill scope issue.
- **Improved:** `load_active_matrix` now uses the `offers_map` optimization for better performance during full system backfills.

### Verdict: APPROVE

---

## Change Log

### [2026-06-10] AI-Review (Hermes)
- Status: done
- Issues fixed: 1 Critical, 1 High, 2 Medium.
- Verification: 57 tests passed; AC-1 through AC-15 verified.
- Sync: sprint-status.yaml updated to done.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### File List

- `apps/api/app/modules/slicer/matrix_backfill.py`
- `apps/api/app/modules/slicer/resolver.py`
- `apps/api/app/modules/slicer/ingest.py`
- `apps/api/app/modules/sot/admin_router.py`
- `apps/api/app/modules/slicer/admin_router.py`
- `apps/api/scripts/enqueue_default_matrix_backfill.py`
- `apps/api/tests/test_matrix_backfill.py`
- `apps/api/tests/test_slicer_resolver.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
