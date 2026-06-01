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

## Boundaries (this story)

No HTTP routes, no DB/Alembic schema, and no real Orca execution — the slicer-
worker container (Story 32.2, OD-2) implements the real `CliValidator`; the real
Spoolman-backed `OverrideProvider` is Story 32.5. A real-Orca acceptance smoke
test exists but is env-gated (`ORCA_SMOKE_TEST=1`), default-skipped.
