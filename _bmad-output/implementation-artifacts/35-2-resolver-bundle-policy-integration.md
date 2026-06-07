# Story 35.2: Resolve Orca filament profile by policy before bundle materialization

Status: in-progress

<!--
  Authored by the repo-local BMAD author (Laura/Hermes delegated). Source planning artifacts:
  epics.md § Initiative 23 (Epic E35 + Story 35.2); architecture.md § Initiative 23 Decision AS
  (appended this run — G-ARCH satisfied before resolver integration); SCP
  sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md (Tasks 2–4).

  GATE NOTE: operator delegated implementation of 35.2 in the task prompt (G-DEVGO for this slice).
  Backend resolver integration ONLY — no admin/user UI (35.4/35.5), no estimate API wiring (35.3),
  no backfill (35.6). App-layer: a new selection helper + a resolver parameter + two additive model
  fields. No Alembic, no on-disk worker contract change → SW-DEPLOY-1 NOT tripped.
-->

## Story

As the **portal estimate pipeline**,
I want **the resolver to choose the Orca filament profile from the Story 35.1 profile-selection policy (exact override > material default > unavailable) before it materializes the bundle, deriving the selection's material from the Init 19 cached Spoolman snapshot**,
so that **two generic-PLA colors that share a material default share one estimate bundle, a PLA Matt exact override gets its own bundle, a missing profile becomes a classified no-estimate absence that never slices a wrong fallback, and the no-selected-filament catalog path stays byte-identical to today.**

This is the **resolver/bundle integration slice** of Epic E35 (SCP Tasks 2–4), realizing **FR23-RESOLVER-1** + **FR23-SNAPSHOT-MAP-1** and preserving **NFR23-CACHE-INVARIANT-1** + **NFR23-OBS-1**. It consumes the shipped 35.1 `ProfilePolicy.resolve_selection` — it does **not** re-implement precedence.

## Acceptance Criteria

### Opt-in seam + backward compatibility

- **AC-1** `resolve()` (and the settings-wired `resolve_intent()`) gains an optional `profile_selection: ProfileSelection | None = None`. With `None` (every existing caller's default) the resolve is **byte-identical** to the Init 20 material-class-default path: same resolved `triple`, same `bundle_hash`, same persisted bundle bytes (NFR23-CACHE-INVARIANT-1).
- **AC-2** `ResolveSuccess` gains an additive `profile_selection: ProfileSelection | None = None`. It is populated on a successful resolve **iff** a selection was supplied — on **both** the fresh-persist and the `from_cache=True` branches — and stays `None` for legacy (no-selection) resolves.

### Profile substitution → bundle identity

- **AC-3** For an `exact_filament_mapping` / `default_material_profile` selection, the resolver re-targets the filament partial's `inherit` to `selection.orca_filament_profile_ref` (a system filament profile **name**) **before** `resolve_inheritance` runs, so the resolved filament JSON reflects the chosen system profile. A non-dict / missing filament partial is left untouched and still classifies as `invalid_partial` via the existing `_resolve_partials` shape gate (no `KeyError` leak).
- **AC-4** Two **distinct** generic-PLA selections (different `spoolman_filament_ref`, same `default_material_profile` ref, no numeric extras) resolve to the **same** `bundle_hash` and a **byte-identical** persisted bundle; the second resolve returns `from_cache=True`.
- **AC-5** A PLA Matt `exact_filament_mapping` selection (a **different** `orca_filament_profile_ref`) resolves to a **different** `bundle_hash` than the generic-PLA default bundle.
- **AC-6** Override ordering: the `filament.extra` numeric override layer applies **after** the policy-selected base profile is materialized. An exact/default selection with no numeric extras leaves `spoolman_overrides_ref` absent (the AC-4 byte-identical-shared property holds); a selection **plus** a numeric override re-hashes via `overrides_ref` to a distinct bundle.

### Classified absence — no wrong fallback

- **AC-7** `ResolveReason` gains `unavailable_no_profile` (additive StrEnum value). An `unavailable_no_profile` selection ⇒ `ResolveFailure(reason=ResolveReason.unavailable_no_profile)` with **no** bundle and **no** snapshot written (the `store.write_bundle` / `write_snapshot` calls are not reached).
- **AC-8** The existing ingest path (`if not isinstance(outcome, ResolveSuccess): … no enqueue`) declines to enqueue on an `unavailable_no_profile` failure — verified by a resolver-level no-write assertion (no spurious slice of a guessed fallback). The order/request path stays open (surfaced honestly by 35.3, out of scope here).

### Selection sourcing — snapshot → material/ref (FR23-SNAPSHOT-MAP-1)

- **AC-9** A pure `build_filaments_by_ref(snapshot)` returns `{spoolman_filament_ref(f): f}` reusing the **one** `overrides.spoolman_filament_ref` function; a `None` snapshot ⇒ an **empty** map (soft-fail, no exception).
- **AC-10** A pure `select_profile(*, policy, spoolman_filament_ref, fallback_material=None, filaments_by_ref=None)` derives the material from the snapshot map for a present-and-found ref (the snapshot material **wins** over `fallback_material`), falls back to `fallback_material` when the ref is absent / the map is empty, and delegates precedence to `policy.resolve_selection`. Pure + deterministic (no clock, no live read).
- **AC-11** Soft-fail: a cold/`None` snapshot (empty map) raises no exception — the selection uses `fallback_material` (⇒ `default_material_profile` if a default is configured, else `unavailable_no_profile`), never a guessed material and never a hard error.

### Invariants / observability

- **AC-12** No second live Spoolman read in the resolve path: `select_profile` consumes a **pre-fetched** map (mirroring `SpoolmanOverrideProvider`), and `resolve()` stays synchronous.
- **AC-13** NFR23-OBS-1: selection/soft-fail logging carries the profile-source label + counts/reason categories only (filament count, `degraded` reason) — **never** filament names/bodies.
- **AC-14** NFR23-CACHE-INVARIANT-1: `compute_bundle_hash`'s signature/contract is **unchanged** — no new hash input is added; bundle separation arises solely from the changed resolved-filament JSON.

## Tasks / Subtasks

1. **(RED)** Write `apps/api/tests/test_slicer_profile_selection.py` (snapshot map + `select_profile` precedence/soft-fail — AC-9..AC-11) and extend `apps/api/tests/test_slicer_resolver.py` (resolver `profile_selection` seam, substitution, shared/distinct bundle, override ordering, classified absence + no-write, result metadata — AC-1..AC-8, AC-12..AC-14). Run to confirm failure (param/field/reason/helpers absent).
2. **(GREEN)**
   - `apps/api/app/modules/slicer/models.py`: add `ResolveReason.unavailable_no_profile`; add `ResolveSuccess.profile_selection: ProfileSelection | None = None` (import `ProfileSelection` from `profile_policy` — no cycle: `profile_policy` imports neither `models` nor `overrides`).
   - `apps/api/app/modules/slicer/resolver.py`: add `profile_selection` param to `resolve()` + `resolve_intent()`; add `_apply_profile_selection(partials, selection)` (defensive: leaves a non-dict/missing filament untouched); return `ResolveFailure(unavailable_no_profile)` before any write when the selection is unavailable; attach `profile_selection` to `ResolveSuccess` on success (fresh + cache branches) via `model_copy`.
   - Create `apps/api/app/modules/slicer/profile_selection.py`: `build_filaments_by_ref`, `select_profile`, structured counts-only obs logging.
3. **(VERIFY)** Targeted pytest (3× determinism) on `test_slicer_profile_selection.py` + `test_slicer_resolver.py` + the existing `test_slicer_profile_policy.py`/`test_slicer_estimate.py` regression set; `ruff format --check` + `ruff check` on touched files.
4. Flip sprint-status `35-2-...` row backlog → in-progress → (on green) review; commit on the story branch.
5. Gemini review (`laura-gemini-review`) on the focused diff; record verdict.

## Dev Notes

### Pre-enumeration save (existence checklist)

- `ProfilePolicy.resolve_selection(*, material, spoolman_filament_ref)` + `ProfileSelection` + `EstimateProfileSource` already exist at `profile_policy.py:144` / `:96` / `:49` — REUSE; do NOT re-implement precedence.
- `spoolman_filament_ref(filament)` at `overrides.py:174` (vendor∥material∥name) — REUSE for the snapshot map key; the `build_spoolman_override_provider` snapshot→`filaments_by_ref` idiom at `overrides.py:240-262` is the soft-fail template (snapshot `None` ⇒ empty map + `degraded` log).
- Filament partial is `{"inherit": "<system filament profile name>"}` (`tests/fixtures/slicer/intents/.../PLA/standard.json`); `merge.resolve_inheritance` looks the parent up by name in `system_tree`. An `orca_filament_profile_ref` IS such a name — substituting `inherit` re-targets the base profile.
- `_resolve_partials` (`resolver.py:235`) owns the shared tail (merge → override → hash → validate → persist) and already classifies a non-dict/missing partial as `invalid_partial` — apply substitution upstream of it and keep that gate authoritative.
- ingest's no-enqueue branch: `ingest.py:147` `if not isinstance(outcome, ResolveSuccess): … return resolve_failed` — an `unavailable_no_profile` failure flows through it unchanged (no new ingest edit in this story).
- `compute_bundle_hash` (`resolver.py:75`) — DO NOT add a hash input; the filament JSON change is the whole mechanism (NFR23-CACHE-INVARIANT-1).

### Magic-constant discipline

- No new numeric constants. The only new literals are the obs log message/label keys (counts-only). No concrete Orca profile ref is hard-coded in module code; test fixtures supply named system filament profiles for substitution.

### Out of scope (deferred to later E35 stories)

estimate ingest/read API + DTO source metadata + the live snapshot→selection wiring at the request boundary (35.3); admin policy surface + the `unknown_profile_refs` save validation (35.4); UI source labels (35.5); bounded default-matrix backfill + recompute/invalidation of changed-default bundles (35.6).

### References

- architecture.md § Initiative 23 / Decision AS (resolver integration clauses 1–6).
- SCP § Task 2 (resolver input/result), § Task 3 (snapshot → material/ref), § Task 4 (resolve profile before bundle materialization).
- epics.md § Initiative 23 / Epic E35 / Story 35.2.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M) — repo-local BMAD author/dev (Laura/Hermes delegated).

### Completion Notes List

- _pending implementation in this run._

### File List

- `apps/api/app/modules/slicer/models.py` (modify — `ResolveReason.unavailable_no_profile` + `ResolveSuccess.profile_selection`)
- `apps/api/app/modules/slicer/resolver.py` (modify — `profile_selection` param + `_apply_profile_selection` + unavailable short-circuit + success metadata)
- `apps/api/app/modules/slicer/profile_selection.py` (new — snapshot map + `select_profile` + obs)
- `apps/api/tests/test_slicer_profile_selection.py` (new)
- `apps/api/tests/test_slicer_resolver.py` (modify — resolver policy integration cases)

## Change Log

- 2026-06-07 — story authored (G-ARCH satisfied first); implementation in same run (operator-delegated 35.2 dev-go).
