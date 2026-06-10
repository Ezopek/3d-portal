---
baseline_commit: 3155a14ae423b423a63f759dcb02e563890ea106
---

# Story 35.3: Estimate ingest/read API + DTO source metadata

Status: done

<!--
  Authored by the repo-local BMAD author (Laura/Hermes delegated). Source planning artifacts:
  epics.md § Initiative 23 (Epic E35 + Story 35.3); architecture.md § Initiative 23 Decision AS;
  SCP sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md § Task 5.

  GATE NOTE: operator delegated implementation of 35.3 in the task prompt (G-DEVGO for this slice).
  Backend API/DTO only — no admin UI (35.4/35.5), no backfill (35.6). Additive DTO fields +
  new exception routing + policy-wiring in the read resolver. No Alembic, no worker image change
  → SW-DEPLOY-1 NOT tripped.
-->

## Story

As the **estimate read/recompute API**,
I want **to derive the profile-selection policy result for a request's `spoolman_filament_ref` and surface it as structured DTO metadata (`estimate_profile_source` / `selected_material` / `selected_spoolman_filament_ref` / `selected_filament_name` / `orca_filament_profile_name`) alongside the existing estimate, returning a classified absence (not 422) when no profile is configured for the selected filament**,
so that **the UI (Story 35.5) and admin tooling (Story 35.4) can display honest exact/default/unavailable labels and the order/request path is never blocked by a missing estimate profile (NFR23-HONESTY-1, NFR23-NO-BLOCK-1).**

This is the **estimate API/DTO source-metadata slice** of Epic E35 (SCP Task 5), realizing **FR23-ESTIMATE-API-1**, **NFR23-HONESTY-1**, **NFR23-NO-BLOCK-1**, **NFR23-OBS-1**. It consumes the shipped 35.1 `ProfilePolicyStore`/`select_profile` seam and the 35.2 `ResolveSuccess.profile_selection` metadata — it does **not** re-implement precedence or the resolver/bundle logic.

## Acceptance Criteria

### Backward compatibility — no-filament path unchanged

- [x] **AC-1** GET `/api/estimates` and POST `/api/estimates/recompute` without `spoolman_filament_ref` behave **byte-identically** to today: `profile_selection_context=null` in the response, `bundle_hash` unchanged, no policy store load triggered, no Spoolman snapshot read beyond the existing override path.

### `ProfileSelectionContextView` DTO

- [x] **AC-2** A new `ProfileSelectionContextView` Pydantic model in `schemas.py` is `extra="forbid"` and carries **exactly** these fields (no extras, no internal-leak fields):
  - `estimate_profile_source: EstimateProfileSource` (one of `exact_filament_mapping` / `default_material_profile` / `unavailable_no_profile`)
  - `selected_material: str | None`
  - `selected_spoolman_filament_ref: str | None`
  - `selected_filament_name: str | None`
  - `orca_filament_profile_name: str | None`
  No `bundle_hash`, no `settings_ids`, no raw Orca profile body, no filesystem path, no g-code cross the DTO fence (FR20-PRESET-1 extended to the policy-source context). A negative-assertion test confirms no extra field survives `extra="forbid"`.
- [x] **AC-3** `EstimateView` gains one additive optional field: `profile_selection_context: ProfileSelectionContextView | None = None`. Existing `EstimateView` slots are **unchanged** (regression: all existing `test_estimate_api.py` assertions still pass without modification).

### `unavailable_no_profile` → 200 absent, never 422

- [x] **AC-4** GET `/api/estimates` with a `spoolman_filament_ref` whose policy resolves to `unavailable_no_profile` returns **200** with `status="absent"` + `profile_selection_context.estimate_profile_source="unavailable_no_profile"`. All numeric fields are `None`. **Never a 422** — the order/request path stays open (NFR23-NO-BLOCK-1).
- [x] **AC-5** POST `/api/estimates/recompute` with the same scenario returns **200** `{enqueued: false, estimate: {status: "absent", profile_selection_context: {estimate_profile_source: "unavailable_no_profile", ...}}}`. **No job is enqueued** for an `unavailable_no_profile` filament (no guessed fallback slice).
- [x] **AC-6** Non-`unavailable_no_profile` resolve failures (`missing_system_profile`, `cli_validation_failed`, `invalid_partial`, `unsupported_material_class`) **still** raise `PresetResolveError` → **422** (unchanged behavior for genuine profile-system errors).

### Filament-selected paths — `profile_selection_context` populated

- [x] **AC-7** GET `/api/estimates` with a `spoolman_filament_ref` that resolves to `exact_filament_mapping` returns `profile_selection_context.estimate_profile_source="exact_filament_mapping"`, `selected_material` set (normalized, from snapshot), `selected_spoolman_filament_ref` set (the stable ref key), `selected_filament_name` set (the Spoolman filament's human `name` from the snapshot map), `orca_filament_profile_name` set (the resolved Orca filament profile name / ref).
- [x] **AC-8** GET `/api/estimates` with a `spoolman_filament_ref` that resolves to `default_material_profile` returns `profile_selection_context.estimate_profile_source="default_material_profile"`, `selected_material` set, `selected_spoolman_filament_ref=null` (a default is per-material, not per-filament), `selected_filament_name` set (from snapshot if found, else `null`), `orca_filament_profile_name` set.
- [x] **AC-9** The same `profile_selection_context` is present on **both** the GET read response and the POST recompute response when the filament is resolvable (fresh/stale/queued/failed/absent estimate state with a non-unavailable profile source).

### Single Spoolman read per resolve_preset call

- [x] **AC-10** When `spoolman_filament_ref` is provided, `_filaments_by_ref()` is called **exactly once** per `resolve_preset` call; the resulting `filaments_by_ref` dict is **shared** between the `SpoolmanOverrideProvider` (numeric override path, Init 20) and `select_profile` (policy selection path, Init 23). **No second Spoolman snapshot read** is triggered (NFR23-OBS-1 / Init 20 NFR20-OBS-1 symmetry).

### Policy store wiring

- [x] **AC-11** The profile-selection policy is loaded via `ProfilePolicyStore(settings.slicer_profile_policy_dir).load()` — **never** a hard-coded path. An absent/empty store (no `profile_policy.json`) returns `ProfilePolicy()` (no configured defaults) → `unavailable_no_profile` for any filament.
- [x] **AC-12** Policy load is called **only** on the `spoolman_filament_ref is not None` branch; the no-filament path does not touch the policy store.

### Pure helper

- [x] **AC-13** A pure `build_profile_selection_context(profile_selection: ProfileSelection | None, selected_filament_name: str | None = None) -> ProfileSelectionContextView | None` in `estimate_read.py`:
  - `profile_selection=None` → `None`
  - `unavailable_no_profile` → `ProfileSelectionContextView(estimate_profile_source=unavailable_no_profile, orca_filament_profile_name=None, ...)`
  - `exact_filament_mapping` / `default_material_profile` → full view (no clock, no I/O, deterministic same-inputs-same-output).

### Observability (NFR23-OBS-1)

- [x] **AC-14** No **new** log fields or Sentry breadcrumb values carry filament names/bodies/Orca profile bodies. The `UnavailableProfileError` routing at the router boundary emits a single structured log (profile-source label + reason only). The existing `build_filaments_by_ref` snapshot-boundary log (counts only) is already sufficient for the snapshot path.

## Tasks / Subtasks

1. [x] **(RED)** Write `apps/api/tests/test_slicer_estimate_source_metadata.py`:
   - `ProfileSelectionContextView` field set + no-leak assertion (AC-2).
   - `build_profile_selection_context` pure function: `None` input → `None`; `unavailable_no_profile` → correct view; `exact_filament_mapping` → all fields populated; `default_material_profile` → `selected_spoolman_filament_ref=None` (AC-13).
   - `UnavailableProfileError` carries `profile_selection` + `selected_filament_name`.
   Run to confirm failure (classes/functions absent).

2. [x] **(RED continued)** Extend `apps/api/tests/test_estimate_api.py` with **new** test cases (do NOT break existing assertions):
   - GET absent + `unavailable_no_profile` → 200, `status="absent"`, `profile_selection_context.estimate_profile_source="unavailable_no_profile"` (AC-4).
   - GET absent + `exact_filament_mapping` → 200, `profile_selection_context` populated per AC-7.
   - GET absent + `default_material_profile` → 200, `profile_selection_context` per AC-8.
   - GET no-filament → `profile_selection_context=null` (AC-1 / AC-3 regression).
   - POST recompute + `unavailable_no_profile` → 200, `enqueued=False`, `status="absent"` (AC-5).
   - POST recompute + non-unavailable filament → `profile_selection_context` present in response (AC-9).
   - Existing `PresetResolveError` → still 422 for non-unavailable failures (AC-6).
   Run to confirm new cases fail (classes/functions absent).

3. [x] **(GREEN)**
   - `apps/api/app/modules/slicer/schemas.py`: import `EstimateProfileSource` from `profile_policy`; add `ProfileSelectionContextView`; add `profile_selection_context: ProfileSelectionContextView | None = None` to `EstimateView`.
   - `apps/api/app/modules/slicer/estimate_read.py`:
     - Add `UnavailableProfileError(profile_selection: ProfileSelection, selected_filament_name: str | None)` exception class.
     - Add `build_profile_selection_context(profile_selection, selected_filament_name) -> ProfileSelectionContextView | None` pure function.
     - Extend `ResolvedPreset` with two additive fields: `profile_selection: ProfileSelection | None = None`, `selected_filament_name: str | None = None`.
     - Extend `project_estimate` signature with `profile_selection_context: ProfileSelectionContextView | None = None`; pass it to `EstimateView`.
     - In `SettingsEstimateResolver.resolve_preset`: on the `spoolman_filament_ref is not None` branch, AFTER `filaments_by_ref` is built (reusing the existing call), load the policy and call `select_profile`; if `unavailable_no_profile` → raise `UnavailableProfileError`; else attach `profile_selection` to the returned `ResolvedPreset`.
   - `apps/api/app/modules/slicer/router.py`:
     - Import `UnavailableProfileError`, `build_profile_selection_context`.
     - In `read_estimate`: catch `UnavailableProfileError` → build context → return absent view (not raise 422).
     - In `recompute_estimate`: catch `UnavailableProfileError` → build context → return `RecomputeResponse(enqueued=False, estimate=absent_view_with_context)`.
     - On the success path: pass `build_profile_selection_context(resolved.profile_selection, resolved.selected_filament_name)` to `project_estimate`.

4. [x] **(VERIFY)** Targeted pytest **3×** on `test_slicer_estimate_source_metadata.py` + extended `test_estimate_api.py` + `test_slicer_profile_selection.py` + `test_slicer_profile_policy.py` regression set. `ruff format --check` + `ruff check` on all touched files.
5. [x] Flip sprint-status `35-3-estimate-api-source-metadata` row `backlog → in-progress → review` (on green). Commit on the story branch.
6. [x] Gemini review (`laura-gemini-review`) on the focused diff; record verdict.

## Dev Notes

### Pre-enumeration save (existence checklist)

**REUSE — do NOT re-implement:**

| What | Where |
|------|-------|
| `EstimateProfileSource` StrEnum | `profile_policy.py:49` |
| `ProfileSelection` model | `profile_policy.py:96` — fields: `source`, `orca_filament_profile_ref`, `selected_material`, `selected_spoolman_filament_ref` |
| `ProfilePolicy.resolve_selection(material, spoolman_filament_ref)` | `profile_policy.py:144` — DO NOT re-implement precedence |
| `build_filaments_by_ref(snapshot)` | `profile_selection.py:41` — `{spoolman_filament_ref(f): f for f in snapshot.filaments}`, soft-fails to `{}` on `None` snapshot |
| `select_profile(*, policy, spoolman_filament_ref, fallback_material, filaments_by_ref)` | `profile_selection.py:75` — derives `ProfileSelection`, pure + deterministic |
| `ProfilePolicyStore` + `.load()` | `profile_policy.py:205` — mtime-cached, returns `ProfilePolicy()` on absent file |
| `settings.slicer_profile_policy_dir` | `config.py:141` (already exists, `Path("/data/content/slicer")`) |
| `_filaments_by_ref()` | `estimate_read.py:292` — ALREADY reads the Spoolman snapshot + builds the `{spoolman_filament_ref(f): f}` map; REUSE this result for both override and policy paths (one read rule) |
| `SpoolmanFilament.name` | `spools/models.py:25` — the human display name for `selected_filament_name` |
| `ResolveReason.unavailable_no_profile` | `models.py:142` (added in 35.2) |
| `ResolveSuccess.profile_selection` | `models.py:170` (added in 35.2) — `None` for legacy resolves |
| `_ReadOnlyBundleStore` | `estimate_read.py:197` — unchanged |
| `PresetResolveError` | `estimate_read.py:85` — kept; only `unavailable_no_profile` is reclassified |
| `_FakeResolver` pattern | `test_estimate_api.py` — extend (add `fail_unavailable` flag) but do NOT replace |

### `SettingsEstimateResolver.resolve_preset` wiring (exact sequence)

```python
async def resolve_preset(self, intent: PrintIntentPreset) -> ResolvedPreset:
    settings = get_settings()
    source = VendoredProfileSource(settings.slicer_vendored_profiles_dir)
    bundle_store = ...  # unchanged

    pinned_filament = None
    profile_selection = None
    selected_filament_name = None

    if intent.spoolman_filament_ref is not None:
        filaments_by_ref = await self._filaments_by_ref()   # ONE read — shared below
        pinned_filament = filaments_by_ref.get(intent.spoolman_filament_ref)
        provider = SpoolmanOverrideProvider(filaments_by_ref)  # existing override path

        # NEW: policy selection reusing the SAME filaments_by_ref map
        from app.modules.slicer.profile_policy import ProfilePolicyStore
        from app.modules.slicer.profile_selection import select_profile
        policy = ProfilePolicyStore(settings.slicer_profile_policy_dir).load()
        selection = select_profile(
            policy=policy,
            spoolman_filament_ref=intent.spoolman_filament_ref,
            filaments_by_ref=filaments_by_ref,
        )
        if selection.source == EstimateProfileSource.unavailable_no_profile:
            raise UnavailableProfileError(
                profile_selection=selection,
                selected_filament_name=pinned_filament.name if pinned_filament else None,
            )
        profile_selection = selection
        selected_filament_name = pinned_filament.name if pinned_filament else None
    else:
        provider = NoopOverrideProvider()

    outcome = resolve(intent, source=source, store=bundle_store,
                      override_provider=provider, ...,
                      profile_selection=profile_selection)  # 35.2 seam
    if not isinstance(outcome, ResolveSuccess):
        raise PresetResolveError(outcome.reason.value)  # unchanged for real errors
    return ResolvedPreset(
        bundle_hash=outcome.bundle.bundle_hash,
        pinned_filament=pinned_filament,
        profile_selection=profile_selection,          # NEW
        selected_filament_name=selected_filament_name, # NEW
    )
```

**Critical:** `_filaments_by_ref()` is called ONCE; its result feeds `SpoolmanOverrideProvider` AND `select_profile`. Do not add a second `await self._filaments_by_ref()` call.

### Router handler changes (exact pattern)

```python
# read_estimate — catch UnavailableProfileError BEFORE the 422 branch
try:
    resolved = await resolver.resolve_preset(intent)
except UnavailableProfileError as exc:
    ctx = build_profile_selection_context(
        exc.profile_selection, exc.selected_filament_name
    )
    return project_estimate(None, override_context=override_context_no_filament,
                            profile_selection_context=ctx)
except PresetResolveError as exc:
    raise HTTPException(status_code=422, detail="preset not resolvable") from exc
```

Where `override_context_no_filament` = `build_override_context(intent, None)` (no pinned filament for the unavailable path). Compute it before the try block.

For `recompute_estimate` — same catch pattern; return `RecomputeResponse(enqueued=False, estimate=...)`.

### `build_profile_selection_context` — shape

```python
def build_profile_selection_context(
    profile_selection: ProfileSelection | None,
    selected_filament_name: str | None = None,
) -> ProfileSelectionContextView | None:
    if profile_selection is None:
        return None
    return ProfileSelectionContextView(
        estimate_profile_source=profile_selection.source,
        selected_material=profile_selection.selected_material,
        selected_spoolman_filament_ref=profile_selection.selected_spoolman_filament_ref,
        selected_filament_name=selected_filament_name,
        orca_filament_profile_name=profile_selection.orca_filament_profile_ref,
    )
```

`orca_filament_profile_ref` IS the Orca system filament profile **name** (not an integer id). The DTO field is named `orca_filament_profile_name` for readability. `None` for `unavailable_no_profile` (where `profile_selection.orca_filament_profile_ref` is also `None`).

### Magic-constant discipline

No new numeric constants. `slicer_profile_policy_dir` is the existing settings slot. Log messages use string labels from `EstimateProfileSource.value` — never hard-coded strings.

### Out of scope (deferred to later E35 stories)

- Admin policy management surface (35.4)
- User-facing UI source labels / badges (35.5)
- Bounded default-matrix backfill + enqueue guardrails (35.6)
- `quality-tiers` endpoint (`GET /api/estimates/quality-tiers`): **no change** — it passes `spoolman_filament_ref=None` today and that path is unchanged (AC-1 / AC-12)

### Regression guard: `_FakeResolver` extension pattern

The `_FakeResolver` in `test_estimate_api.py` must be extended (not replaced) to raise `UnavailableProfileError` when a new `fail_unavailable: ProfileSelection | None` flag is set. Existing `fail_reason` / `fail_tiers` logic stays untouched. Pattern:

```python
if self.fail_unavailable is not None:
    from app.modules.slicer.estimate_read import UnavailableProfileError
    raise UnavailableProfileError(
        profile_selection=self.fail_unavailable, selected_filament_name="Test Filament"
    )
```

All existing `_FakeResolver`-based tests remain unmodified.

### `ResolvedPreset` — additive fields (dataclass)

`ResolvedPreset` is a `@dataclass(frozen=True)`. Add two fields with defaults:

```python
@dataclass(frozen=True)
class ResolvedPreset:
    bundle_hash: str
    pinned_filament: SpoolmanFilament | None = None
    profile_selection: ProfileSelection | None = None    # NEW
    selected_filament_name: str | None = None           # NEW
```

`bundle_hash` stays `str` (not `str | None`) — `unavailable_no_profile` is handled by raising `UnavailableProfileError` before `ResolvedPreset` is constructed.

### Project Structure Notes

All changes are in `apps/api/app/modules/slicer/` and `apps/api/tests/`. No new modules needed.

- `schemas.py` — DTOs (this is the public ⊥ internal split file; additive only)
- `estimate_read.py` — read service + resolver (pure projection helpers + production resolver)
- `router.py` — HTTP handlers
- `tests/test_slicer_estimate_source_metadata.py` — NEW (pure unit tests, mirrors 35.2's `test_slicer_profile_selection.py` scope)
- `tests/test_estimate_api.py` — EXTEND (new test cases, existing cases untouched)

### References

- `architecture.md` § Initiative 23 / Decision AS (clauses 3, 6 — classified absence + result metadata).
- `epics.md` § Initiative 23 / Epic E35 / Story 35.3 + FR23-ESTIMATE-API-1 + NFR23-HONESTY-1 + NFR23-NO-BLOCK-1 + NFR23-OBS-1.
- SCP `sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md` § Task 5 (estimate ingestion/read APIs for selected filament context).
- `project-context.md` § Critical Implementation Rules — Python FastAPI patterns; no `os.environ` direct reads; `ruff check --fix` + `ruff format`; TDD red → green → refactor.
- `35-2-resolver-bundle-policy-integration.md` § Pre-enumeration save (sources for `build_filaments_by_ref`, `select_profile`, `profile_selection.py`).

## Dev Agent Record

### Agent Model Used

Gemini CLI (YOLO mode)

### Debug Log References

### Completion Notes List

- Fixed missing `fallback_material=intent.material_class` in `SettingsEstimateResolver.resolve_preset`.
- Added `labels.reason: "unconfigured"` to `UnavailableProfileError` logs in `router.py`.
- Added regression test `test_35_3_settings_resolver_uses_fallback_material_when_spoolman_down` to `test_slicer_estimate_source_metadata.py`.

### File List

- `apps/api/app/modules/slicer/schemas.py`
- `apps/api/app/modules/slicer/estimate_read.py`
- `apps/api/app/modules/slicer/router.py`
- `apps/api/tests/test_estimate_api.py`
- `apps/api/tests/test_slicer_estimate_source_metadata.py`

## Senior Developer Review (AI)

### Findings

- **CRITICAL**: Missing `fallback_material=intent.material_class` in `select_profile` call in `estimate_read.py`. This would have broken material-default fallbacks when Spoolman was down or the filament was missing from the snapshot. Fixed by Reviewer.
- **HIGH**: AC-14 violation: `labels.reason` missing from `UnavailableProfileError` logs in `router.py`. Fixed by Reviewer.
- **MEDIUM**: AC-1 "byte-identical" claim is strictly violated as adding a new field (even if `null`) changes the JSON bytes. However, this is accepted as an additive schema change.
- **MEDIUM**: Added regression test `test_35_3_settings_resolver_uses_fallback_material_when_spoolman_down` to verify the fallback logic fix.

### Verdict

**APPROVE WITH FIXES APPLIED**
The implementation was mostly correct but had a critical regression in the fallback logic. The reviewer applied the fixes and verified with a new regression test.
