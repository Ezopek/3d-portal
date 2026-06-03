---
title: 'SPOOL-PREQ-1 — Spoolman filament reverse index / intent attribution'
type: 'feature'
created: '2026-06-03'
status: 'in-review'
baseline_commit: '58611b139f643d278e018b0e0964046ad2518f9e'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
  - '{project-root}/apps/api/app/modules/slicer/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SPOOL-EVT-1 (live Spoolman invalidation) cannot be soundly wired from existing persisted state. `apply_spoolman_filament_change` already exists and takes a single `intent` plus `affected_keys: (stl_hash, bundle_hash)[]`, but no persisted record links a Spoolman `spoolman_filament_ref` back to the intents and bundle/estimate keys it produced. `SlicerProfileBundle.spoolman_overrides_ref` is only a fingerprint of mapped override *values*, never a filament ref, so the affected key set is unrecoverable today.

**Approach:** Persist, at resolve time, an append-only reverse-index sidecar keyed by `spoolman_filament_ref → {(intent, bundle_hash)}` (resolve is the only point where the intent's filament ref and the resulting `bundle_hash` are simultaneously in scope). Add a deterministic lookup that joins that index with the existing `EstimateStore` iteration to return, per pinning intent, the affected `(stl_hash, bundle_hash)` estimate keys — exactly the inputs SPOOL-EVT-1's deferred poll-diff event source feeds into `apply_spoolman_filament_change`.

## Boundaries & Constraints

**Always:**
- Use `PrintIntentPreset.spoolman_filament_ref` (derived by `overrides.spoolman_filament_ref`, the churn-stable `vendor∥material∥name` key) as the attribution key — NEVER infer a ref from `spoolman_overrides_ref`.
- Append-only file-store sidecar on the slicer content root, mirroring `bundle_store.py` / `estimate_store.py` atomicity (unique tmp + atomic publish; additive merge; never mutate/delete prior entries).
- Hash the raw ref for the on-disk filename (the ref carries a `\x1f` separator + arbitrary text → not path-safe); store the raw ref inside the record for round-trip.
- Resolver change is a DI seam (Protocol + Noop default) mirroring `override_provider`: ref `None` (today's default) OR no sink injected ⇒ byte-identical no-op, zero perturbation of existing resolve hashes/tests.
- Lookup is deterministic (stable ordering) and pure of external I/O beyond the two file stores.
- Store only the portal-owned `PrintIntentPreset` as intent context — it carries NO Orca internals and NO raw override values (frontend-safe by construction).

**Ask First:**
- Any need to thread the intent/filament_ref through the arq slice-job payload, change `EstimateRecord`'s shape, or add an Alembic table — all signal the file-store-sidecar approach is insufficient; HALT.

**Never:**
- Catalog→`stl_hash` ingestion (EST-INGEST-1), `POST /api/estimates/recompute` (EST-RECOMPUTE-1), live Spoolman event dispatch / poll-diff wiring, or any UI.
- A second `bundle_hash → {stl_hash}` index — reuse `EstimateStore.iter_*`; record the perf option as a deferred note only.
- Exposing Orca internals or raw override values anywhere in the record or lookup result.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Resolve, ref pinned | `resolve()` succeeds, `intent.spoolman_filament_ref="V\x1fPLA\x1fX"`, `bundle_hash=B` | one index entry `ref→{(intent,B)}` persisted under `hash(ref).json` | N/A |
| Resolve, ref None | `resolve()` succeeds, `spoolman_filament_ref is None` | NO index file written; resolve byte-identical to today | N/A |
| Noop sink / no sink | `resolve()` with default (no sink injected) | NO index write | N/A |
| Idempotent add | same `(ref,intent,B)` recorded twice | single entry; second add is a no-op, prior file unchanged | N/A |
| Multiple variants per ref | two intents (diff `quality_tier`) pin same ref → `B1`,`B2` | record holds both `(intent1,B1)`,`(intent2,B2)` | N/A |
| Lookup, known ref | index has `ref→{(intent,B)}`; `EstimateStore` has `(S1,B)`,`(S2,B)` fresh | group `(intent, B, [(S1,B),(S2,B)])`, deterministic order | N/A |
| Lookup, ref with no estimates | index has `ref→{(intent,B)}`, no estimate for `B` | group `(intent, B, [])` (bundle known, no keys yet) | N/A |
| Lookup, unknown ref | ref absent from index | empty list | N/A |
| Lookup, malformed/empty store | index file absent or estimates dir absent | empty list; never raises | swallow / empty |

</frozen-after-approval>

## Code Map

- `apps/api/app/modules/slicer/attribution_store.py` — NEW. `AttributionRecord` (Pydantic: `spoolman_filament_ref: str`, `entries: list[AttributionEntry{intent: PrintIntentPreset, bundle_hash: str}]`) + `AttributionStore` (append-only, ref-hash fanout) + `AttributionSink` Protocol + `NoopAttributionSink` + the `lookup_affected_keys(ref, *, attribution_store, estimate_store)` join.
- `apps/api/app/modules/slicer/resolver.py` — add optional `attribution_sink: AttributionSink = NoopAttributionSink()` param to `resolve()`; on success with a pinned ref, `sink.record(ref, intent, bundle_hash)`. Wire the real store in `resolve_intent()` from settings.
- `apps/api/app/modules/slicer/overrides.py` — REUSE `spoolman_filament_ref` (no change).
- `apps/api/app/modules/slicer/estimate_store.py` — REUSE `iter_all_estimates` / `iter_stl_estimates` (no change).
- `apps/api/app/core/config.py` — REUSE `slicer_bundle_store_dir` as the content root (no new setting unless a distinct subdir is needed; the store owns its `attribution/` subtree).
- `apps/api/tests/test_slicer_attribution.py` — NEW. Persist + DI-seam + lookup tests (on-disk tmp_path, no Redis/Orca/httpx).
- `_bmad-output/implementation-artifacts/deferred-work.md` — UPDATE SPOOL-EVT-1 entry with the concrete remaining step.

## Tasks & Acceptance

**Execution:**
- [x] `apps/api/app/modules/slicer/attribution_store.py` -- create `AttributionEntry`/`AttributionRecord`/`AffectedGroup` models, `AttributionStore` (append-only ref-hash fanout `<root>/attribution/<refhash[:2]>/<refhash>.json`, additive idempotent merge keyed by `bundle_hash`, under the estimate-store flock + atomic-publish discipline), `AttributionSink` Protocol + `NoopAttributionSink`, and `lookup_affected_keys` -- the persisted reverse index + lookup join.
- [x] `apps/api/app/modules/slicer/resolver.py` -- add the optional `attribution_sink` DI seam to `resolve()` (record only on success + truthy pinned ref, on both fresh + cache-hit branches), wire the real store in `resolve_intent()` -- the resolve-time write boundary, non-breaking by default.
- [x] `apps/api/tests/test_slicer_attribution.py` -- 22 tests for the I/O matrix: persist semantics, resolver DI seam (None/Noop/empty-ref = no write, byte-identical), lookup semantics + determinism.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- updated SPOOL-EVT-1 with the resume step + deferred perf-index note + the SPOOL-PREQ-1 review defer (D1).

**Acceptance Criteria:**
- Given a successful resolve whose intent pins a `spoolman_filament_ref`, when `resolve()` runs with the real sink, then exactly one append-only record exists keyed by the ref's hash, carrying the raw ref + `(intent, bundle_hash)`.
- Given an intent with `spoolman_filament_ref is None` (or no sink injected), when `resolve()` runs, then no attribution file is written and the resolve output is byte-identical to the pre-change behavior (existing resolver tests stay green).
- Given a seeded index and `EstimateStore`, when `lookup_affected_keys(ref)` is called, then it returns one group per pinning intent with the correct, deterministically-ordered `(stl_hash, bundle_hash)` keys; an unknown ref returns an empty list and a missing store never raises.
- Given the deferred-work file, when the story closes, then SPOOL-EVT-1 records the concrete resume step (poll-diff → lookup → `apply_spoolman_filament_change` per group).

## Spec Change Log

**2026-06-03 — review pass (3 adversarial subagents; no spec loopback).** Acceptance Auditor APPROVE; all actioned findings classified `patch` (caused by the change, trivially fixable — no `intent_gap`/`bad_spec`). Applied in-flight:
- **EC-1 (empty-string ref):** the resolver seam guarded `is None`, letting a degenerate `spoolman_filament_ref=""` pin write an index bucket. Tightened to a falsy check (`not ref`) so `None` and `""` alike are no-ops. Test: `test_resolve_with_empty_string_ref_writes_no_attribution`.
- **EC-2 + BH-1 (dedup unit / sort uniformity):** dedup keyed on the whole frozen intent let resolve-irrelevant UI fields (`notes`, `is_default`) bloat one `(ref, bundle_hash)` into multiple entries → duplicate `AffectedGroup`s. Re-keyed dedup to `bundle_hash` (the resolve-determining unit — ref is fixed per record and `bundle_hash` subsumes material/quality/printer/override). Unified both write branches through one `sorted(...)` so the deterministic-order contract is path-independent. Test: `test_record_dedups_by_bundle_hash_ignoring_ui_only_fields`.
- **EC-4 (doc):** documented that `lookup_affected_keys` returns ALL-status keys (`failed`/`stale`/`queued` included) and the 32.4 engine guards per status.
- **Rejected:** BH-5 (no parent-dir fsync) — deliberately matches `estimate_store`/`bundle_store`. **Deferred:** blank-field `"\x1f\x1f"` ref degeneracy → upstream `overrides.spoolman_filament_ref` concern, parked as SPOOL-PREQ-1-D1.

KEEP (must survive any re-derivation): the resolve-time-only write boundary; the DI seam with `None`-default byte-identical no-op; ref-hashed filename + raw-ref body round-trip; reuse of `EstimateStore.iter_*` (no second index); flock + atomic-publish mirroring the estimate store.

## Design Notes

Two intents sharing one filament ref resolve to two different `bundle_hash`es, and SPOOL-EVT-1 must re-resolve *each* pinning intent against the new filament to compute its new `bundle_hash` (`apply_spoolman_filament_change` does this internally). Hence the index stores `(intent, bundle_hash)` pairs and the lookup groups by intent. The `(stl_hash, bundle_hash)` join reuses `EstimateStore.iter_all_estimates()` filtered by the bundle_hashes of interest — O(all estimates) per changed ref, acceptable at homelab scale; a `bundle_hash → {stl_hash}` index is the deferred optimization, not built here.

Filename safety (magic constant): fan-out prefix length `2` — points to the contract "mirror `bundle_store`/`estimate_store` per-directory entry-count bound (Decision AI)", not an arbitrary value. The ref-hash filename is sha256 of the raw ref (path-safety contract: the ref contains `\x1f` + arbitrary vendor text and must never reach the filesystem verbatim).

## Verification

**Commands:**
- `cd apps/api && uv run pytest tests/test_slicer_attribution.py -q` -- expected: all new tests pass (red→green TDD).
- `cd apps/api && uv run pytest tests/test_slicer_resolver.py tests/test_slicer_store.py tests/test_slicer_spoolman_overrides.py tests/test_estimate_api.py -q` -- expected: green (no regression from the DI seam).
- `cd apps/api && uv run ruff format --check . && uv run ruff check .` -- expected: clean on touched files.
- `git diff --check` -- expected: no whitespace errors.
- `cd apps/api && uv run pytest -q` -- expected: full backend suite green (run if practical).

## Suggested Review Order

**Design intent (entry point)**

- The append-only reverse index + lookup join — start here to grasp the whole design.
  [`attribution_store.py:125`](../../apps/api/app/modules/slicer/attribution_store.py#L125)

**Persist semantics**

- `record()` — dedup keyed on `bundle_hash` (resolve-determining unit), single sort path, idempotent no-op.
  [`attribution_store.py:157`](../../apps/api/app/modules/slicer/attribution_store.py#L157)
- The lookup join: index ⋈ `EstimateStore.iter_all_estimates`, status-agnostic, deterministic.
  [`attribution_store.py:238`](../../apps/api/app/modules/slicer/attribution_store.py#L238)

**Resolver DI seam (the write boundary)**

- `_record_attribution` — fires only on success + truthy ref; `None` sink/ref = byte-identical no-op.
  [`resolver.py:171`](../../apps/api/app/modules/slicer/resolver.py#L171)
- `resolve_intent` defaults a real settings-wired store so the index populates downstream.
  [`resolver.py:336`](../../apps/api/app/modules/slicer/resolver.py#L336)

**Tests + deferred handoff**

- 22 tests: persist, DI-seam no-op, lookup determinism, dedup, empty-ref guard.
  [`test_slicer_attribution.py:1`](../../apps/api/tests/test_slicer_attribution.py#L1)
- SPOOL-EVT-1 concrete resume step + deferred perf-index note + review defer D1.
  [`deferred-work.md`](./deferred-work.md)
