# Slicer module — Orca profile resolver (Epic 32 / Story 32.1, Initiative 20)

Productionizes Decision **AH**: a first-class profile-resolver subsystem that
turns Orca's **partial, inheritance-based** profile tree into CLI-acceptable,
reproducible slice inputs. Raw Orca *user* profiles are partial — they `inherit`
a system profile and lack a top-level `type`, so the Orca CLI rejects them
directly. The merge IS the load-bearing complexity.

## Pipeline

```
resolve(intent, source, store, override_provider, validator, orca_version)
  └─ source.intent_partials   read vendored {machine,process,filament} user partials
  └─ resolve_inheritance      recursive inherit-chain merge, USER PARTIAL WINS  (merge.py)
  └─ normalize_for_cli        inject top-level `type`; drop `instantiation`       (merge.py)
  └─ apply_filament_overrides Spoolman override layer onto filament (seam)        (overrides.py)
  └─ compute_bundle_hash      canonical H(machine ∥ process ∥ filament ∥ orca_version) (resolver.py)
  └─ [exact bundle?]          content hit ⇒ return cached bundle (idempotent)
  └─ check_required_keys      e.g. TPU needs filament_max_volumetric_speed        (validation.py)
  └─ validator.validate       CLI-acceptance smoke seam (NullCliValidator default)(validation.py)
  └─ store.write_snapshot/bundle  append-only hash-fanout persist                 (bundle_store.py)
     ⇒ ResolveSuccess(bundle, triple) | ResolveFailure(reason, message)
```

## Resolver precedence (load-bearing, never a silent fallback)

`exact bundle > custom override > material-class default > unsupported`. An
intent with no vendored profile fails **loud and classified**
(`ResolveFailure` + a machine-readable `ResolveReason`), never a silent fallback
to a wrong default:

| reason code | when |
|---|---|
| `unsupported_material_class` | no vendored intent for the material class |
| `missing_system_profile`     | an `inherit` reference is absent from the system tree |
| `invalid_partial`            | required key missing (e.g. TPU `filament_max_volumetric_speed`) |
| `cli_validation_failed`      | the CLI-acceptance smoke returned not-OK |

## `bundle_hash` (reproducibility key — AC-5/AC-10)

`H(machine ∥ process ∥ filament ∥ orca_version ∥ overrides_ref)`, each JSON
canonicalized (sorted keys, stable float repr) so cosmetic churn does NOT churn
the hash. The input order is **byte-pinned** (changing it requires an SCP).
`orca_version` is folded in so an Orca upgrade is a clean bulk-invalidation event
(Decision AJ). The applied-override fingerprint (`spoolman_overrides_ref`) is
folded in **after** `orca_version` (and only when an override layer is applied),
so an override whose applied values happen to equal the material-class default —
a no-op on the filament JSON — still produces a distinct `bundle_hash` carrying
its override provenance instead of colliding with the no-override bundle. A plain
no-override hash stays byte-identical to the 4-part key.

## Storage (AC-6 — no DB)

Append-only on-disk JSON on the `portal-content` volume, hash-fanout layout
mirroring the render/STL cache. `SLICER_BUNDLE_STORE_DIR` is the store **root**;
`BundleStore` adds the `bundles/` and `snapshots/` children itself:

```
<store_root>/bundles/<bundle_hash[:2]>/<bundle_hash>.json
<store_root>/snapshots/<snapshot_hash[:2]>/<snapshot_hash>.json
```

Identity IS the hash: writing an existing hash is an idempotent no-op; a re-tune
creates a NEW file and never mutates the old one. Writes are **first-write-wins
and concurrency-safe** — each writer stages to a unique temp file and publishes
via an atomic `os.link`, which refuses to overwrite an already-published hash even
if the `exists()` pre-check raced. `created_at` is provenance only and is excluded
from every content hash. The provenance snapshot also records
`source_system_tree_hash` (the content identity of the vendored system tree), so
an in-place edit of a vendored system profile yields a new snapshot identity.

## Settings (AC-10/AC-12)

| setting | env | default | role |
|---|---|---|---|
| `orca_version` | `ORCA_VERSION` | `2.3.2` | folded into `bundle_hash` |
| `slicer_vendored_profiles_dir` | `SLICER_VENDORED_PROFILES_DIR` | `/data/content/slicer/vendored` | vendored artifact root |
| `slicer_bundle_store_dir` | `SLICER_BUNDLE_STORE_DIR` | `/data/content/slicer` | append-only store root (holds `bundles/` + `snapshots/`) |

The vendored profiles are **exported artifacts** (a one-time bench snapshot),
never a live read of an external host at resolve time. The bench export-path env
var (documented in `infra/env.example`) is a **bench-only** one-time-export path,
NOT read by production runtime — the resolver only ever reads
`SLICER_VENDORED_PROFILES_DIR`.

## Slicer worker (Story 32.2 — headless Orca CLI invoke + classify, Decision AI)

Story 32.2 adds the worker subsystem that consumes a resolved bundle and turns an
STL into a typed slice outcome. New files in this package:

| file | role |
|---|---|
| `cli.py` | Orca command builders (`--info` pre-check + slice argv, reusing `validation.build_orca_load_flags`) + the timeout-bounded `SubprocessRunner` seam + output parsing (`manifold`, warnings, profile-rejection). Entrypoint from `slicer_orca_bin`. |
| `stl_cache.py` | content-hash STL cache `<root>/stl/<hash[:2]>/<hash>.stl`; populated API-side from the mirrored catalog copy, read-only at the worker. |
| `worker_job.py` | the `slice_estimate` arq task: load bundle → locate STL → `--info` manifold pre-check → slice → classify → hand temp g-code to the (32.3) parser sink → discard. Returns a typed `SliceOutcome`. |
| `worker.py` | `SlicerWorkerSettings` arq entrypoint (dedicated `arq:slicer` queue, bounded `max_jobs`, redis) — what the configs-side `slicer-worker` container runs. |
| `enqueue.py` | API-side idempotent enqueue: populate cache + enqueue the `(stl_hash, bundle_hash)` 2-tuple deduped on `_job_id`. |

Job contract: the payload is the **2-tuple `(stl_hash, bundle_hash)` only** —
no profile JSON, STL bytes, or file paths cross the queue. The job is idempotent on
`_job_id = slice:<stl_hash>:<bundle_hash>` and lands on the dedicated `arq:slicer`
queue (never the render `arq:queue` / api `arq:api`).

Classification (`SliceOutcome` / `SliceFailureReason`) is never a silent zero:
`non_manifold` (fast-fail before the slice), `non_zero_exit`, `cli_rejected_profile`,
`missing_stl`, `missing_bundle`, `timeout`; plus a non-blocking `warning` status.
g-code is **parse-and-discard** (OD-5): written to a context-managed scratch dir and
deleted at job end — zero durable retention. The Story 32.3 parser slots into the
`GcodeSink` seam (default no-op discard) without reshaping `worker_job.py`.

| setting | env | default | role |
|---|---|---|---|
| `slicer_orca_bin` | `ORCA_BIN` / `SLICER_ORCA_BIN` | `/opt/orca/orca` | Orca entrypoint (container-internal; never a literal) |
| `slicer_stl_cache_dir` | `SLICER_STL_CACHE_DIR` | `/data/content/slicer/stl-cache` | content-hash STL cache root |
| `slicer_max_concurrency` | `SLICER_MAX_CONCURRENCY` | `1` | arq `max_jobs` cap (NFR20-RESOURCE-1) |
| `slicer_slice_timeout_seconds` | `SLICER_SLICE_TIMEOUT_SECONDS` | `900` | ARBITRARY slice wall-time ceiling (pending R3 benchmark) |
| `slicer_info_timeout_seconds` | `SLICER_INFO_TIMEOUT_SECONDS` | `60` | ARBITRARY `--info` ceiling (pending R3 benchmark) |

## Boundaries

No HTTP routes, no DB/Alembic schema. Real Orca is NOT run in CI — `cli.py` injects a
subprocess-shaped runner seam (fake in the unit suite); the real run is verified
out-of-band on the configs-side `slicer-worker` container (Story 32.2 AC-12) plus the
env-gated `ORCA_SMOKE_TEST=1` bench bridge. The real Spoolman-backed
`OverrideProvider` is Story 32.5; g-code metadata parsing into an estimate is Story
32.3. The container topology that runs Orca is configs-side (HC2 boundary), never a
commit in this repo.
