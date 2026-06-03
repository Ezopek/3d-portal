---
title: 'EST-INGEST-1 — catalog STL hash ingestion + first estimate trigger'
type: 'feature'
created: '2026-06-03'
status: 'review'
baseline_commit: '4063f05'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/apps/api/app/modules/slicer/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Epic 32 slicer stack ships every primitive to slice an STL and read its
estimate, but nothing connects a *real catalog STL part* to the `(stl_hash, bundle_hash)`
key the estimate store is read by, and nothing triggers a first slice — so the shipped
estimate read seam (`GET /api/estimates`) and the planned FilesTab chip can only ever show
`absent`. EST-INGEST-1 is the Epic 32 retro §5 keystone that makes per-part estimates real.

**Approach:** Add a backend ingestion service that, for a catalog STL `ModelFile`, resolves a
single configurable **default print-intent preset** to a persisted bundle (real writing
`BundleStore`), populates the content-hash `StlCache` from the mirrored catalog STL copy, and
idempotently enqueues the first slice via the existing Story 32.2/32.4 primitives. The catalog
part → `stl_hash` mapping is **already persisted** — `ModelFile.sha256` for `kind=stl` is the
byte-exact lowercase sha256 of the STL bytes (proven by test), identical to `compute_stl_hash`
and to the value `GET /api/estimates?stl_hash=…` is read by — so **no Alembic migration**. The
trigger surface is an operator-supervised backfill script mirroring `enqueue_thumbnail_backfill.py`.

## Boundaries & Constraints

**Always:**
- Reuse Epic 32 primitives byte-for-byte: `resolve_intent`/`resolve` (persists the bundle),
  `StlCache.populate_from_source`, `enqueue_slice_estimate` (+ `slice_job_id` dedupe),
  `EstimateStore.read`, `validate_content_hash`. Do NOT re-implement hashing, store layout,
  concurrency, dedupe, or queue routing.
- Content-hash discipline against STL bytes: the enqueued `stl_hash` is freshly computed from
  the actual STL bytes by `populate_from_source`; a test proves it equals `ModelFile.sha256`.
- Idempotent + deduped enqueue: skip enqueue when a `fresh` estimate already exists for the
  `(stl_hash, bundle_hash)`; rely on `slice_job_id` for in-flight dedupe. Re-running the
  backfill must not re-slice already-estimated parts (mirror thumbnail-backfill `already_present`).
- Explicit, classified status per part — never a silent zero, never a silent skip. Absent/
  unavailable prerequisites (no vendored profile, malformed/missing STL, unsupported material)
  surface as a typed status/log line; finite-guard semantics of the downstream record are preserved.
- Resolve through the REAL writing `BundleStore` (so the worker can `load_bundle`), NOT the read
  seam's non-mutating `_ReadOnlyBundleStore`.
- STL parts only (`ModelFileKind.stl`); exclude `stl_preview`, `source`, `archive_3mf`, images.
- Backend + script + tests only. TDD: failing test first for the sha256-equality proof and each
  service branch.

**Ask First:**
- Any need to widen beyond the single default preset (e.g. slice all material×quality combos
  per STL), to auto-trigger on upload/hydrate, or to add an HTTP ingestion endpoint.
- Any change to `bundle_hash` / `stl_hash` / `slice_job_id` derivation or the estimate-store key.

**Never:**
- No Alembic migration / no new DB column or table (mapping already lives on `ModelFile.sha256`).
- No raw g-code exposure; no Orca internals leaking into any API/DTO/log.
- No `POST /api/estimates/recompute` (EST-RECOMPUTE-1 stays deferred).
- No frontend / FilesTab chip (UX-doc Story A stays separate); no readback/proof UI.
- No admin profile/filament management.
- No second Spoolman poll; no write to the Windows catalog.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First slice | STL part, default preset resolvable, no estimate yet | resolve→persist bundle, populate cache, enqueue `(stl_hash,bundle_hash)`; status `enqueued` | N/A |
| Already fresh | `fresh` estimate exists for `(stl_hash,bundle_hash)` | no enqueue; status `already_fresh` | N/A |
| In-flight dup | same key enqueued while queued/running | `slice_job_id` de-dups (arq drops dup); status `enqueued` (idempotent) | N/A |
| Stale/failed/absent record | record exists but not `fresh` | enqueue (re-slice); status `enqueued` | N/A |
| Unsupported material / no vendored profile | `resolve` returns `ResolveFailure` | NO enqueue; status `resolve_failed` carrying the `ResolveReason` | classified, logged, not raised |
| Missing/empty STL on disk | `storage_path` absent or unreadable | NO enqueue; status `missing_stl` | logged, skip part, continue |
| Path escape | `storage_path` resolves outside content dir | NO enqueue; status `error` | logged, skip part |
| Non-STL kind | image/source/3mf/stl_preview | skipped (not inspected) | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/app/modules/slicer/ingest.py` -- NEW. The ingestion service: `ingest_stl_part(...)`
  (one `ModelFile`) + `ingest_model_estimates(...)` (a model's STL parts) returning typed
  per-part `IngestResult`. Pure, seam-injected (`arq_pool`, `stl_cache`, resolver fn, `estimate_store`,
  default preset, `content_dir`).
- `apps/api/app/core/config.py` -- add `slicer_default_printer_ref`, `slicer_default_material_class`,
  `slicer_default_quality_tier` settings (the default ingest preset).
- `apps/api/scripts/enqueue_estimate_backfill.py` -- NEW. Operator-supervised backfill mirroring
  `enqueue_thumbnail_backfill.py`: `--dry-run` / `--inline`-style guards, idempotent skip, summary.
- `apps/api/app/modules/slicer/enqueue.py` -- REUSE `enqueue_slice_estimate` / `slice_job_id` (no edit).
- `apps/api/app/modules/slicer/resolver.py` -- REUSE `resolve` / `resolve_intent` (no edit).
- `apps/api/app/modules/slicer/stl_cache.py` -- REUSE `populate_from_source` / `compute_stl_hash` /
  `validate_content_hash` (no edit).
- `apps/api/app/modules/slicer/estimate_store.py` -- REUSE `read` (no edit).
- `apps/api/app/core/db/models/_entities.py` -- `ModelFile.sha256` / `kind` (read-only reference).
- `apps/api/tests/test_slicer_ingest.py` -- NEW. sha256-equality proof + every I/O-matrix branch.

## Tasks & Acceptance

**Execution:**
- [x] `apps/api/tests/test_slicer_ingest.py` -- write failing tests FIRST: (1) sha256-equality proof —
  `compute_stl_hash(stl)` == streaming `hashlib.sha256` of the same bytes == a value `validate_content_hash`
  accepts (the contract `ModelFile.sha256` is minted under, for both upload and hydrate paths); (2) every
  I/O-matrix row of the service with seams (fake arq pool capturing `enqueue_job`, real tmp `StlCache` +
  `EstimateStore`, fake resolver returning success/failure).
- [x] `apps/api/app/core/config.py` -- add the three default-preset settings.
- [x] `apps/api/app/modules/slicer/ingest.py` -- implement `IngestResult` + `IngestStatus` + the service.
- [x] `apps/api/scripts/enqueue_estimate_backfill.py` -- backfill walking `kind=stl` rows; dry-run +
  enqueue modes; idempotent skip; operator summary; route to `arq:slicer`.
- [x] `apps/api/tests/test_enqueue_estimate_backfill.py` -- cover dry-run inventory, enqueue path, skip-fresh.

**Acceptance Criteria:**
- Given a catalog STL `ModelFile`, when `ModelFile.sha256` is compared to `compute_stl_hash` of its
  bytes, then they are byte-equal lowercase 64-hex and accepted by `validate_content_hash` (proven test).
- Given a resolvable default preset and no prior estimate, when the part is ingested, then exactly one
  `(stl_hash, bundle_hash)` job is enqueued on `arq:slicer` with `_job_id = slice:<stl_hash>:<bundle_hash>`,
  the bundle is persisted in the real `BundleStore`, and the STL is present in the cache.
- Given a `fresh` estimate already exists, when ingested again, then no enqueue occurs (`already_fresh`).
- Given `resolve` fails (unsupported/missing profile), when ingested, then no enqueue occurs and the
  result carries the classified `ResolveReason` (`resolve_failed`) — no exception, no silent zero.
- Given a missing/unreadable/escaping STL path, when ingested, then no enqueue and a classified
  `missing_stl`/`error` result; the backfill continues to the next part.
- Given the full backend suite, when run, then it stays green and no new Alembic revision is added.

## Design Notes

**Mapping = `ModelFile.sha256` (no migration).** `hydrate_local_tree.py:_sha256_of_file` and
`sot/admin_service.py::_write_atomic` both compute plain streaming `hashlib.sha256` over the raw file
bytes; hydrate additionally *verifies* `disk_sha == master_sha`. That is exactly `compute_stl_hash`.
So for `kind=stl`, `ModelFile.sha256` IS the `stl_hash` the slicer mints, reads, and dedupes by —
the part→hash linkage is already persisted and indexed (`ModelFile.sha256` index, unique
`(model_id, sha256, kind)`). The service still lets `populate_from_source` recompute the hash from the
actual bytes (canonical, path-safe); `ModelFile.sha256` is used for the read/idempotency pre-check and
is what the future FE passes as `?stl_hash=`. The equality test is the load-bearing proof gate.

**Ingest flow (per STL part):** validate `kind=stl` → resolve absolute path under `content_dir`
(reuse the `(content_dir / storage_path).resolve()` + `relative_to` guard from
`enqueue_thumbnail_backfill.py:101-107`) → if missing ⇒ `missing_stl` → `resolve(default_preset, real
BundleStore)`; failure ⇒ `resolve_failed(reason)` (no enqueue) → compute candidate `stl_hash`
(= `ModelFile.sha256`, validated) and `estimate_store.read(stl_hash, bundle_hash)`; if `fresh` ⇒
`already_fresh` → else `enqueue_slice_estimate(arq_pool, source_stl=abs_path, bundle_hash, stl_cache)`
⇒ `enqueued`. The worker writes the `EstimateRecord` on completion (initial display state stays `absent`
until the slice lands — first-class per the read seam).

**Magic constants → contracts:**
- `slicer_default_material_class = "PLA"`, `slicer_default_quality_tier = "standard"` — because the
  shipped FilesTab UX recommendation (`_bmad-output/ux/stl-estimate-display-catalog-files-ux.md`,
  default preset bar "PLA · Standard") is the contract for what the chip shows on first load. The first
  slice must populate that exact bundle or the default-load chip is permanently `absent`.
- `slicer_default_printer_ref = "creality-k1-max-microswiss-hf"` — the homelab printer identity (the
  ref used as THE printer across the Epic 32 test suite). Env-overridable; resolve fails LOUD and
  classified if no vendored profile matches it. **Arbitrary-until-multi-printer:** replace when a
  printer registry / per-model printer selection lands. Operator owns confirming a vendored profile for
  `(this printer, PLA, standard)` exists on `.190` — see Verification runtime gate.

## Verification

**Commands:**
- `cd apps/api && python -m pytest tests/test_slicer_ingest.py tests/test_enqueue_estimate_backfill.py -q`
  -- expected: all pass (sha256 proof + every I/O-matrix branch).
- `cd apps/api && python -m pytest -q` -- expected: full backend suite stays green; no new failures.
- `ruff format apps/api && ruff check apps/api` -- expected: clean.
- `git diff --check` -- expected: no whitespace errors.
- `! ls apps/api/migrations/versions/ | grep -i ingest` -- expected: no new migration (mapping reused).

**Runtime gate (controller-owned, not closed by this branch — SW-DEPLOY-1 pattern):**
- On `.190`, confirm a vendored Orca profile exists for `(slicer_default_printer_ref, PLA, standard)`
  so ingestion produces real estimates rather than only classified `resolve_failed`. The enqueued slice
  runs on the `portal-slicer-worker` overlay — the SW-DEPLOY-1 overlay rebuild + in-container Orca/import
  smoke applies on the deploy that ships this. Backfill is operator-supervised, never auto-run by `deploy.sh`.
