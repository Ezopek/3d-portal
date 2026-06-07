# Spoolman Filament Profile Estimates Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make print estimates select the Orca filament profile from Spoolman-backed generic material defaults plus concrete filament overrides, so new normal filaments estimate automatically while unusual filaments can be pinned by an admin.

**Architecture:** Spoolman remains the source of truth for filament inventory and generic material type. The portal owns estimate-profile policy: material-type default Orca filament profiles, optional per-Spoolman-filament Orca profile mappings, and an explicit estimate source/confidence returned to the UI. Slice/cache identity remains `(stl_hash, bundle_hash)`, where the bundle hash already folds in the selected filament profile/override layer. The bounded default matrix is precomputed/backfilled so users do not wait for normal generic-material estimates; concrete per-filament override estimates remain explicit/operator-controlled.

**Tech Stack:** FastAPI/Pydantic v2/SQLModel backend, existing `modules/spools` Spoolman snapshot cache, existing `modules/slicer` resolver/bundle/estimate stores, React 19 + TanStack Router frontend.

---

## Accepted product decision

1. Spoolman material values are assumed to stay generic (`PLA`, `PETG`, `PCTG`, `TPU`, `ABS`, ...), not variant-specific (`PLA Speed`, `PLA Matt`).
2. Portal does not require a manual portal-side material update/restart for every new color/ordinary filament.
3. Estimate profile resolution order for a selected Spoolman filament is:
   1. explicit mapping: `spoolman_filament_ref -> Orca FilamentProfile`;
   2. material default: `spoolman.material -> default Orca FilamentProfile`;
   3. unavailable estimate: no compatible profile configured.
4. If only a material default exists, the estimate is allowed but must be labelled as default/fallback, not exact.
5. Missing estimate must not block an order/request; it only means time/grams/cost are unavailable or approximate depending on UI wording.
6. Offer/process compatibility remains broad and capability-based: `compatible_material_categories` answers "can this process be used for this generic material?" and must not be auto-narrowed to the currently selected filament.

## Does the slicing matrix explode?

It grows, but it is manageable if we keep slicing lazy and keyed by the real resolved bundle.

The theoretical matrix is:

```text
catalog STL part × print profile offer/process × selected Orca filament profile
```

Production policy should precompute the **bounded default matrix** so users do not wait for first estimates:

- when a new STL enters the catalog, enqueue estimates for every active profile offer/process and every configured **default generic Orca filament profile** whose material is compatible with that offer;
- when a new profile offer/process is published, enqueue estimates for every catalog STL and every compatible configured material default;
- when a material default profile changes, enqueue or mark stale the affected `STL × offer/process × material-default-profile` rows;
- do **not** precompute every concrete Spoolman filament. Concrete per-filament overrides are a smaller admin-managed exception path and may be backfilled separately/explicitly;
- enqueue only if `(stl_hash, bundle_hash)` has no fresh/queued estimate;
- keep worker concurrency bounded by the slicer queue and docker-compose CPU limits;
- cache by `bundle_hash`, because two Spoolman filaments that resolve to the same Orca filament profile/default should share the same estimate bundle where the resolved JSON is byte-identical.

Homelab scale makes the bounded default matrix acceptable. The actual risks are queue/backfill ergonomics and **UI honesty**: fallback/default estimates must not look exact.

## Data model target

### Backend enums / DTO fields

Add an estimate profile source enum, e.g.:

```python
class EstimateProfileSource(StrEnum):
    exact_filament_mapping = "exact_filament_mapping"
    default_material_profile = "default_material_profile"
    unavailable_no_profile = "unavailable_no_profile"
```

Expose UI-safe fields on estimate views:

```python
estimate_profile_source: EstimateProfileSource
selected_material: str | None
selected_spoolman_filament_ref: str | None
selected_filament_name: str | None
orca_filament_profile_name: str | None
```

User-facing copy can then distinguish:

- exact: "Estymacja dla wybranego filamentu";
- default: "Estymacja na podstawie domyślnego profilu PLA";
- unavailable: "Brak profilu estymacji dla tego materiału".

### Persistent policy storage

Prefer a portal-owned small JSON store first, not a DB migration, unless existing admin config already expects DB-backed settings.

Suggested append/replace-safe shape:

```json
{
  "material_defaults": {
    "PLA": {"orca_filament_profile_ref": "AI Rosa3D PLA Starter", "enabled": true},
    "PETG": {"orca_filament_profile_ref": "AI Generic PETG", "enabled": true}
  },
  "filament_overrides": {
    "Vendor\u001fPLA\u001fFiberlogy PLA Matt": {
      "orca_filament_profile_ref": "AI Fiberlogy PLA Matt",
      "enabled": true
    }
  }
}
```

Notes:

- Key explicit overrides by existing `spoolman_filament_ref()`, not Spoolman integer id.
- Normalize material keys at portal boundary: trim + uppercase. Do not invent variant categories from Spoolman names.
- Validate Orca profile refs against vendored/available filament profiles before saving.

## Implementation tasks

### Task 1: Add profile-selection policy model and store

**Objective:** Represent material defaults and per-filament override mappings in a small portal-owned policy store.

**Files:**
- Create: `apps/api/app/modules/slicer/profile_policy.py`
- Test: `apps/api/tests/test_slicer_profile_policy.py`

**Steps:**
1. Write tests for material normalization: `" pla " -> "PLA"`, empty/unknown strings rejected or classified.
2. Write tests for resolution precedence: exact filament override wins over material default.
3. Write tests for unavailable profile: no override + no default returns `unavailable_no_profile`.
4. Implement Pydantic policy models and a filesystem-backed `ProfilePolicyStore` with atomic write.
5. Add validation seams but avoid hard-coding concrete Orca refs in model tests.

### Task 2: Extend resolver input/result with profile source metadata

**Objective:** Let the resolver know which Spoolman filament/material is selected and return how the Orca filament profile was chosen.

**Files:**
- Modify: `apps/api/app/modules/slicer/models.py`
- Modify: `apps/api/app/modules/slicer/resolver.py`
- Test: existing resolver tests plus new profile-policy cases

**Steps:**
1. Replace or extend `PrintIntentPreset.spoolman_filament_ref` semantics from "override extra only" to "selected Spoolman filament for estimate policy".
2. Add `EstimateProfileSource`/metadata to `ResolveSuccess` or a sibling UI projection model. Keep internal bundle format content-addressed.
3. Ensure default material-class resolve path remains byte-identical when no selected filament is supplied.
4. Ensure unsupported material/no default produces a classified absence, not a wrong fallback.

### Task 3: Map Spoolman snapshot to generic material + stable filament ref

**Objective:** Build the candidate selection data from the existing Spoolman cache without adding a second live Spoolman read.

**Files:**
- Modify: `apps/api/app/modules/slicer/overrides.py` or split into `spoolman_profiles.py`
- Modify: `apps/api/app/modules/spools/models.py` if extra fields are missing
- Test: `apps/api/tests/test_slicer_spoolman_profile_selection.py`

**Steps:**
1. Reuse `SpoolsService.get_summary()` and `spoolman_filament_ref()`.
2. Build a map: `ref -> {name, vendor, material, extra}`.
3. Soft-fail when Spoolman snapshot is unavailable: no exact mapping, material default only if material is known from caller; otherwise unavailable.
4. Log only counts/reason categories, never full filament bodies.

### Task 4: Resolve Orca filament profile by policy before bundle materialization

**Objective:** Make `bundle_hash` reflect the selected Orca filament profile/default so estimate cache keys naturally separate exact/default material variants.

**Files:**
- Modify: `apps/api/app/modules/slicer/resolver.py`
- Modify: `apps/api/app/modules/slicer/bundle_store.py` only if provenance field needs extension
- Test: resolver/bundle hash tests

**Steps:**
1. Given selected `spoolman_filament_ref`, try policy exact override.
2. Else use policy material default for normalized Spoolman material.
3. Else return classified no-estimate state to the caller; do not enqueue slice.
4. Apply existing `filament.extra` numeric overrides only after base Orca profile selection, if still wanted.
5. Verify two colors of generic PLA resolve to the same bundle when they share the default profile and no extra overrides.
6. Verify PLA Matt exact override resolves to a different bundle from generic PLA.

### Task 5: Update estimate ingestion/read APIs for selected filament context

**Objective:** Estimate endpoints should accept/derive the selected Spoolman filament and return exact/default/unavailable state.

**Files:**
- Modify: `apps/api/app/modules/slicer/ingest.py`
- Modify: `apps/api/app/modules/slicer/estimate_read.py`
- Modify: `apps/api/app/modules/slicer/router.py`
- Modify: `apps/api/app/modules/slicer/schemas.py`
- Test: API/read DTO tests

**Steps:**
1. Add optional selected filament ref/input to estimate read/recompute/enqueue paths.
2. Preserve current default estimate behavior for catalog screens that have no selected spool yet.
3. Return `absent/unavailable` with source `unavailable_no_profile` when no profile exists; do not enqueue.
4. Keep existing `fresh/stale/queued/failed` semantics for resolvable bundle keys.
5. Include profile-source labels in logs and Sentry breadcrumbs.

### Task 6: Add admin policy management surface

**Objective:** Allow admin to configure material defaults and exact filament overrides without restart.

**Files:**
- Backend: new/modified admin router under `apps/api/app/modules/slicer/`
- Frontend: likely new settings/admin section under `apps/web/src/modules/estimates/` or settings
- Tests: backend auth/validation tests + frontend component tests

**Steps:**
1. Backend endpoints:
   - list available Spoolman material types from current snapshot;
   - list known Orca filament profiles;
   - get/update material default mappings;
   - get/update per-filament overrides.
2. Frontend table: material defaults with status configured/unconfigured.
3. Frontend table: Spoolman filaments with optional exact Orca profile override.
4. Validate save server-side: profile exists, material key normalized, ref is stable.
5. No restart requirement: policy store is read on demand or cached with mtime invalidation.

### Task 7: Update user-facing estimate UI wording

**Objective:** Make exact/default/unavailable estimates clear and non-misleading.

**Files:**
- Modify: `apps/web/src/lib/api-types.ts`
- Modify: estimate/profile selector components under `apps/web/src/modules/estimates/`
- Modify: locales `apps/web/src/locales/{pl,en}.json`
- Tests: frontend rendering tests

**Steps:**
1. Add badges/tooltips for profile source.
2. Exact: normal confident estimate display.
3. Default fallback: show estimate with subtle badge, e.g. "domyślny profil PLA".
4. Unavailable: show no time/grams/cost but keep request/order path available.
5. Avoid exposing Orca internals too loudly to normal users; show exact Orca profile mainly in admin/debug context.

### Task 8: Bounded default-matrix backfill and queue controls

**Objective:** Precompute the default estimate matrix users are expected to see immediately, while preventing accidental concrete-filament N×M×K expansion.

**Files:**
- Modify: `apps/api/scripts/enqueue_estimate_backfill.py`
- Modify: catalog STL ingestion hooks
- Modify: profile-offer publish hooks
- Modify: recompute/invalidation code if needed
- Test: backfill dry-run summaries and enqueue dedupe tests

**Steps:**
1. Backfill the default matrix by default: every catalog STL × every active offer/process × every compatible configured material default Orca profile.
2. On new STL ingestion, enqueue that STL across all active compatible offer/default-material combinations.
3. On profile offer/process publish, enqueue that offer across all catalog STLs and compatible configured material defaults.
4. On material default mapping change, mark stale or re-enqueue affected default-material bundle estimates.
5. Keep exact per-Spoolman-filament overrides out of the default matrix unless an explicit operator/admin action requests backfill for that override.
6. Dry-run must report counts by `(offer/process, material, profile_source)` before enqueueing.
7. Existing dedupe on `(stl_hash, bundle_hash)` remains the main safety valve.
8. Respect slicer-worker concurrency and docker-compose CPU limits; queue length is acceptable, unbounded parallel Orca is not.

### Task 9: Integration smoke on live-like data

**Objective:** Prove the three target scenarios end-to-end.

**Files:**
- Tests/fixtures as needed
- Deployment smoke script or documented operator commands

**Scenarios:**
1. New PLA color, no exact mapping: estimate resolves via default PLA and shares bundle/cache with other generic PLA.
2. ABS with no material default: estimate unavailable, order path not blocked.
3. PLA Matt with exact mapping: first fallback/default, then admin maps exact profile, estimate uses different bundle and displays exact source.

**Verification commands:**
- `cd apps/api && pytest tests/test_slicer_profile_policy.py tests/test_slicer_resolver.py tests/test_slicer_estimate.py -q`
- `infra/scripts/check-all.sh` before merge/deploy
- Live smoke after deploy: query a known model + three selected filament refs and confirm source labels and queue behavior.

## Risks and guardrails

- **Misleading fallback estimates:** Must be labelled. This is the main product risk.
- **Wrong Spoolman key:** Use `spoolman_filament_ref()`, not integer ids.
- **Material spelling drift:** Normalize, display unknowns as unconfigured, do not silently coerce `PLA+` unless we deliberately add an alias table.
- **Queue explosion:** Lazy only. Backfill defaults only unless operator explicitly opts in.
- **Cache invalidation:** Changing a material default changes future bundle hashes. Old estimates can remain as orphaned cache; active reads should use the newly resolved bundle key.
- **Profile availability:** Admin save must validate Orca profile refs against vendored profiles to avoid deferred RC -17-style failures.

## Suggested delivery slices

1. Backend policy model + resolver integration, no UI admin yet: enough to test exact/default/unavailable with fixtures.
2. Read API/UI source labels: users see honest estimates.
3. Admin mapping UI: no restart/manual code edits.
4. Backfill/recompute ergonomics: operator-safe maintenance.

Do not bundle this with unrelated slicer repair fallback work currently present on `fix/slicer-repair-fallback-estimates`; keep branch/diff boundaries clean.
