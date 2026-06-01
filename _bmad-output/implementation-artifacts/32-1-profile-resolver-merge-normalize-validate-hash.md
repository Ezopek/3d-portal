# Story 32.1: Profile resolver — inheritance merge + normalize + validate + hash + snapshot

Status: done

## Story

As an **autonomous portal backend that must turn Orca's partial, inheritance-based profile tree into CLI-acceptable, reproducible slice inputs**,
I want **a first-class profile-resolver subsystem in a new `apps/api/app/modules/slicer/` package that recursively merges the vendored Orca system profile tree with the user partials (user wins), injects the top-level `type`, drops the instantiation field that breaks the CLI, applies a stub-tolerant Spoolman override layer, validates the merged triple via a specified Orca `--info` / minimal-slice smoke (execution dependency-injected, real run gated to a bench), computes a canonicalized `bundle_hash` over `machine ∥ process ∥ filament ∥ orca_version`, and persists an append-only `SlicerProfileBundle` + `SourceProfileSnapshot`**,
so that **Story 32.2's slicer-worker can feed Orca a resolved triple it actually accepts (raw user partials are CLI-rejected — proven), Story 32.3+ can key estimates on a complete, churn-stable `(stl_hash, bundle_hash)` reproducibility tuple, and an unsupported/invalid intent fails loud and classified rather than silently resolving to a wrong default that would produce a plausible-but-wrong estimate**.

Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 (Decision AH) + § 4.3 (Epic E32 story sketch).
Architectural anchor: Decision **AH** (resolver architecture — system+user inheritance merge + override layer + canonicalized hashing + append-only bundles + provenance snapshot) per `architecture.md` § Initiative 20.
Realizes **FR20-RESOLVER-1**; lays the bundle/hash foundation Stories 32.2 (slice), 32.3 (cache key), 32.4 (invalidation), and 32.5 (Spoolman override layer) all build on.
OD-gate context: authored after the **2026-05-31 OD-gate resolution** (OD-1 intent/strength presets `aesthetic|standard|strong`; OD-2 dedicated slicer-worker; OD-7 cost-only arithmetic; OD-8 `.190`-mirrored catalog STL source; OD-9 dedicated `slicer` + `estimates` modules — see `prd.md` § Initiative 20 § Open decisions). **Authoring this spec to `ready-for-dev` does NOT authorize dev-story execution — that remains gated on an explicit operator go per SCP § 5.**
**Codex tag:** `gpt-5.5` per `[[feedback_codex_model_routing]]` — **data-integrity adjacency**: an incomplete or non-canonical `bundle_hash` silently serves a stale/wrong estimate as fresh (R9 cache-key-incomplete class), and a silent fallback on an unsupported profile produces a plausible-but-wrong number. Hash completeness + the no-silent-fallback precedence contract are reproducibility-integrity primitives, not routine logic. No NFR-SECURITY public-bypass / auth-boundary adjacency (this story mounts no routes).

## Acceptance Criteria

### AC-1 — Module skeleton exists at the OD-9-resolved path

A new package `apps/api/app/modules/slicer/` ships with:

- `__init__.py` (empty re-export module).
- `models.py` — internal Pydantic shapes: `PrintIntentPreset`, `SlicerProfileBundle`, `SourceProfileSnapshot`, `ResolvedTriple`, plus the resolver result/failure types (AC-7).
- `resolver.py` — the resolver orchestration (merge → normalize → override → validate → hash → snapshot/persist).
- `merge.py` — the pure recursive inheritance-merge + normalize functions (no I/O; unit-testable in isolation).
- `overrides.py` — the Spoolman override-layer **interface** (`OverrideProvider` protocol + a no-op default; AC-8).
- `validation.py` — the CLI-acceptance validator **interface** + the specified Orca smoke command (AC-9).
- `bundle_store.py` — the append-only on-disk bundle + snapshot persistence (AC-6).

**No `router.py`** in this story (the slicer initiative mounts its first route in a later story; this story adds zero HTTP surface). The package mirrors the layout of existing modules (`apps/api/app/modules/spools/`, `apps/api/app/modules/share/`). **OD-9:** code lives under `apps/api/app/modules/slicer/` (NOT folded into the `requests` v2 slot; NOT an `estimates` subpackage — the repo convention is a top-level module per bounded context, matching `spools/`).

### AC-2 — Vendored Orca source profiles + checked-in PLA/TPU fixtures; bench export documented; ZERO live Fenrir / `/mnt/c` read in code

- The Orca **system profile tree + user partials** consumed by the resolver are **vendored/exported artifacts** — a one-time snapshot from the Fenrir bench, NOT a live read of Fenrir's `/mnt/c/...` at resolve time. The production vendored-artifact location is read from a settings slot (AC-10), defaulting to a container-internal path; the bench export step (operator/bench-side, `FENRIR_EXPORT_PATH`) is documented in Dev Notes as **NOT a production runtime path**.
- Test fixtures: the proven PLA bundle (resolved Creality K1 Max MicroSwiss HF + Rosa3D PLA Starter + 0.20 mm) and TPU bundle (Rosa3D Flex 96A + 0.20 mm TPU FlowTech) source partials + their expected resolved triples are checked in under `apps/api/tests/fixtures/slicer/` (small JSON; no STL, no g-code).
- **Grep invariant (AC-12 enforces):** no `/mnt/c` path and no Fenrir hostname/path literal appears anywhere under `apps/api/app/modules/slicer/`.

### AC-3 — Recursive system→user inheritance merge, user partial wins (proven Fenrir resolver behavior)

`merge.py` exposes a pure function `resolve_inheritance(system_tree: dict, user_partial: dict) -> dict` that:

- Recursively resolves the Orca `inherit` chain (a user partial `inherit`s a system profile, which may itself `inherit` a parent system profile), deep-merging keys child-over-parent.
- **User partial wins on every conflict** with its inherited system defaults (the partial is the most-derived layer).
- Is a **pure function** (no I/O, no global state) so it is unit-testable against the checked-in fixtures.

**TDD (red→green):** write the failing test first — `test_resolve_inheritance_user_partial_overrides_system_default` asserts that a key set in the user partial overrides the same key from the inherited system profile, and a key present only in the system parent is carried through. Then implement to green. Cover a ≥2-level `inherit` chain (user → system child → system parent).

### AC-4 — Normalize: inject top-level `type`, drop the instantiation field that breaks the CLI

`merge.py` exposes `normalize_for_cli(merged: dict, *, profile_kind: Literal["machine","process","filament"]) -> dict` that:

- Injects the top-level `type` field (`"machine"` / `"process"` / `"filament"`) that raw user partials lack — the omission is exactly why the Orca CLI rejects raw partials (proven; `--datadir` does not fix it).
- Drops/normalizes the problematic **instantiation** field (the `instantiation` key Orca's resolved-system profiles carry that the CLI `--load-*` path rejects) and any other normalization the proven `orca_resolve_profiles.py` PoC applied.
- Leaves all slicing-relevant keys intact (no lossy normalization of process/filament settings).

**TDD:** `test_normalize_injects_type_for_each_kind` (red first) asserts `type` present + correct per kind; `test_normalize_drops_instantiation_field` asserts the instantiation field is absent post-normalize while a sample slicing key survives.

### AC-5 — Canonicalized `bundle_hash` over `machine ∥ process ∥ filament ∥ orca_version`; cosmetic JSON churn does NOT change the hash

`resolver.py` exposes `compute_bundle_hash(machine: dict, process: dict, filament: dict, orca_version: str) -> str` that:

- Canonicalizes each JSON (sorted keys, normalized number formatting) before hashing, so **cosmetic churn** (key reordering, whitespace, `1.0` vs `1.00` float formatting) produces an **identical** hash.
- Concatenates the three canonicalized JSONs **in the fixed order machine ∥ process ∥ filament**, then appends `orca_version`, then hashes (the hash input ordering is a byte-pinned contract per AC-10).
- Folding `orca_version` into the hash makes an Orca upgrade a clean bulk-invalidation event (Decision AJ, realized in Story 32.4).

**TDD (the load-bearing reproducibility test, red first):**
- `test_bundle_hash_is_stable_across_cosmetic_json_churn` — same semantic triple, two cosmetically-different JSON encodings (reordered keys + reformatted floats) ⇒ **identical** `bundle_hash`.
- `test_bundle_hash_changes_when_a_slicing_value_changes` — flip one process value (e.g. wall count) ⇒ **different** hash.
- `test_bundle_hash_changes_when_orca_version_changes` — same triple, different `orca_version` ⇒ different hash.
- `test_bundle_hash_input_order_is_machine_process_filament` — pin the concatenation order (swapping two equal-shaped JSONs across slots yields a different hash), guarding against a silent reorder regression.

### AC-6 — Append-only `SlicerProfileBundle` + `SourceProfileSnapshot` persisted with provenance (NO DB schema)

- Persistence is an **append-only on-disk JSON store** on the `portal-content` volume — **NOT** an Alembic table (per SCP: "No DB schema; append-only estimate records"). Layout mirrors the render/STL hash-fanout shape: `<bundle_root>/bundles/<bundle_hash[:2]>/<bundle_hash>.json` for the bundle (the resolved triple refs + `orca_version` + `bundle_hash` + `source_snapshot_ref` + optional `spoolman_overrides_ref` + `created_at`), and `<bundle_root>/snapshots/<snapshot_hash[:2]>/<snapshot_hash>.json` for the `SourceProfileSnapshot`.
- **Append-only / versioned:** writing a bundle that already exists at its `bundle_hash` is an idempotent no-op (the hash IS the identity); a re-tune produces a NEW `bundle_hash` + file, and the old bundle file is never mutated or deleted by this story.
- **`SourceProfileSnapshot` provenance fields (AC):** `source_system_tree_ref` (path/id of the vendored system tree used), `source_user_partial_hash` (content hash of the raw user partial), `orca_version`, `resolver_version` (a constant in `resolver.py`, bumped when merge/normalize logic changes), `created_at`. So a bundle can be re-resolved and diffed if the upstream Orca system tree changes.

**TDD:** `test_persist_bundle_is_idempotent_on_same_hash` (writing twice ⇒ one file, no mutation); `test_snapshot_records_source_path_hash_and_orca_version` (provenance fields populated from the resolve inputs); `test_retune_creates_new_bundle_file_leaving_old_intact`.

### AC-7 — Resolver precedence + classified failure (never a silent fallback)

`resolver.py` exposes the resolve entry point returning a **typed result**, never `None`-as-fallback:

- **Precedence (load-bearing contract):** `exact bundle > custom override > material-class default > unsupported`. The resolver tries, in order: (1) an exact pre-resolved bundle for the `(material_class, quality_tier, printer_ref, overrides)` intent; (2) a custom-override resolve; (3) the material-class default profile; (4) **unsupported** ⇒ classified failure.
- An intent that resolves to "unsupported" (no material-class default, missing required profile, etc.) returns a **classified failure** — a typed `ResolveFailure` (or raises a `ResolverError` subclass) carrying a machine-readable reason code (`unsupported_material_class`, `missing_system_profile`, `cli_validation_failed`, `invalid_partial`) — **never a silent fallback to a wrong default** and never a bare `None` the caller might misread as "fresh".

**TDD (red first, one test per precedence branch):**
- `test_resolve_prefers_exact_bundle_when_present`.
- `test_resolve_falls_through_to_material_default_when_no_exact_bundle`.
- `test_resolve_unsupported_material_class_yields_classified_failure` — asserts the typed failure + reason code, asserts NO bundle file is written, asserts it does NOT silently return a default bundle.
- `test_resolve_invalid_partial_yields_classified_failure` (missing required key, e.g. TPU without `filament_max_volumetric_speed`).

### AC-8 — Spoolman override-layer interface designed now, stub-tolerant until Story 32.5

`overrides.py` defines the override-layer **interface** the resolver consumes, designed now so Story 32.5 slots in without reshaping the resolver:

- `class OverrideProvider(Protocol)` with `def overrides_for(self, intent: PrintIntentPreset) -> FilamentOverrides | None` (returns mapped Spoolman `filament.extra` fields — esp. `filament_max_volumetric_speed`, nozzle/bed temps, density — or `None` when no override pins a spool).
- A default `NoopOverrideProvider` returning `None` (MVP path until Story 32.5 ships the real Spoolman-backed provider).
- The resolver applies overrides onto the **filament** JSON **before** hashing, and folds the applied override set into the bundle via `spoolman_overrides_ref` so a later mapped-field change re-hashes (the trigger Story 32.4 consumes). With the no-op provider, `spoolman_overrides_ref` is absent/empty and the hash is override-free.

**TDD:** `test_resolver_uses_injected_override_provider` — inject a fake provider returning a `filament_max_volumetric_speed` override; assert it lands in the resolved filament JSON AND changes the `bundle_hash` vs the no-op path. `test_noop_provider_yields_override_free_bundle` — default provider ⇒ no `spoolman_overrides_ref`, hash matches the no-override resolve. **Out of scope here:** the live Spoolman read + the real mapping logic (Story 32.5); this story only proves the seam is correct and DI-clean.

### AC-9 — Resolved triple is accepted by the Orca CLI: smoke command SPECIFIED, execution dependency-injected, real run bench-gated

`validation.py` defines:

- `class CliValidator(Protocol)` with `def validate(self, triple: ResolvedTriple) -> ValidationResult` — the seam the resolver calls in its validate step.
- A `NullCliValidator` (always-OK) used by the pure unit suite (the merge/hash/precedence tests do not need a real Orca).
- The **exact specified smoke command** the real validator (implemented in Story 32.2 inside the slicer-worker container) will run, documented as a constant + Dev-Notes block: an Orca `--info` (or minimal headless slice) invocation over the three resolved JSONs — e.g. `orca --info --load-settings "<machine.json>;<process.json>" --load-filaments "<filament.json>" <tiny-probe.stl>` — that must exit 0 for the triple to be accepted. **Actual Orca execution is NOT implemented in this story** (the container is Story 32.2 per OD-2); this story ships the interface + the command spec + a required-key schema assertion (e.g. TPU triple MUST carry a sane `filament_max_volumetric_speed`).
- A **real-Orca acceptance smoke test** is provided but **env-gated** `@pytest.mark.skipif(os.environ.get("ORCA_SMOKE_TEST") != "1", ...)` (mirrors Init 19's `SPOOLMAN_LIVE_TEST` pattern) — default-skipped in CI and autonomous runs; opt-in only on a bench with the Orca AppImage. CI proves the resolver logic; the bench proves CLI acceptance.

**TDD:** `test_resolver_calls_validator_before_persisting` (a failing validator ⇒ classified `cli_validation_failed`, NO bundle persisted); `test_required_key_schema_assertion_tpu_volumetric_speed` (missing key ⇒ classified failure); plus the env-gated `test_resolved_triple_accepted_by_orca_cli_smoke` (skipped unless `ORCA_SMOKE_TEST=1`).

### AC-10 — Magic-constant contracts (per `[[feedback_scp_pre_enumeration_phase]]` § C)

Every literal below appears in code with a single-line `because "…"` contract comment beside it:

| Literal | Location | Contract pointed to |
|---|---|---|
| hash input order `machine ∥ process ∥ filament ∥ orca_version` | `resolver.py` `compute_bundle_hash` | because **"byte-pinned reproducibility-key ordering — Decision AH; reorder ⇒ silent cache-key divergence (R9). Change requires an SCP."** |
| hash algorithm (e.g. `sha256`) | `resolver.py` | because **"content-addressed bundle identity; collision-resistance over a tiny JSON corpus — Decision AH"** |
| canonicalization params (sort_keys + float-normalization rule) | `resolver.py` | because **"cosmetic JSON churn must NOT churn the hash — FR20-RESOLVER-1 hash-stability AC-5"** |
| `<bundle_hash[:2]>` fan-out prefix length | `bundle_store.py` | because **"hash-prefix fan-out mirrors the render/STL cache layout (Decision AI) to bound per-directory entry count"** |
| `resolver_version` constant | `resolver.py` | because **"provenance — bump when merge/normalize logic changes so an old SourceProfileSnapshot is diffable against a re-resolve — AC-6"** |
| `orca_version` source (settings slot, not hard-coded) | `resolver.py` / `config.py` | because **"folded into bundle_hash so an Orca upgrade is a clean bulk-invalidation event — Decision AJ / NFR20-REPRODUCIBLE-1"** |

A magic constant in `apps/api/app/modules/slicer/` without an adjacent contract comment is a P1 review fix-up.

### AC-11 — Adaptive / variable layer height stays gated; data model must not bake a uniform-layer assumption

- This story implements **fixed-layer-height** resolution only. Adaptive/variable layer height is **GATED** (proven negative: `adaptive_layer_height=1` did not change the layer-Z schedule/estimate).
- **Forward-compat invariant:** the `SlicerProfileBundle` / `ResolvedTriple` shape MUST NOT hard-encode "estimates assume uniform layer height" in a way that blocks a later variable-height bundle (e.g. do not collapse the process profile to a single scalar layer-height field that a future variable-height profile could not populate; keep the full process JSON). **TDD:** `test_bundle_preserves_full_process_json_not_a_flattened_layer_height` — assert the persisted bundle carries the full process JSON, not a lossy single-layer-height scalar. No adaptive-height code is written.

### AC-12 — No production dependency on Fenrir or `/mnt/c`; Fenrir export path is bench-only

- **Grep invariant:** `grep -rnE "/mnt/c|fenrir" apps/api/app/modules/slicer/` returns ZERO matches (case-insensitive). The vendored-artifact location is read from the settings slot (AC-10), never a hard-coded bench path.
- `infra/env.example` documents `ORCA_VERSION` + `FENRIR_EXPORT_PATH` with a comment stating `FENRIR_EXPORT_PATH` is a **bench-only one-time-export** path, NOT read by production runtime (per NFR20-CONTAINER-1). The configs-side slicer-worker container topology is a separate workstream (Story 32.2; NOT a 3d-portal commit).
- **TDD:** `test_resolver_reads_vendored_artifacts_from_settings_not_hardcoded_path` — point the settings slot at the test fixtures dir and assert the resolver reads from there (proves no hard-coded bench path).

### AC-13 — Determinism gate (NFR20-DETERMINISM-1)

After this story lands, three consecutive `pytest apps/api/tests/test_slicer*.py -v` runs return identical pass counts (no flakes). The resolver is pure/deterministic by construction (no clock/random in the hash path; `created_at` timestamps are excluded from `bundle_hash`). Coverage: T-DET below.

### AC-14 — Scope fence: backend-only, no routes, no Alembic, no `apps/web`, no new heavy deps

- Zero changes under `apps/web/`. Zero new route mounting (`apps/api/app/main.py:_PUBLIC_ROUTES` and `apps/api/app/router.py` byte-identical to pre-story state — grep invariant). Zero Alembic migration (AC-6 store is filesystem JSON). No new heavy dependency (canonical JSON + `hashlib` are stdlib; Pydantic already present). The Orca AppImage + GL/GTK deps belong to the Story 32.2 container, NOT to `apps/api/pyproject.toml`.
- **TDD/grep:** `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` returns zero lines; no new entry in `apps/api/migrations/versions/`.

## Tasks / Subtasks

> **TDD discipline (AGENTS.md § Execution discipline):** each logic-bearing task writes the failing test FIRST (red), then implements to green, then refactors. The pure `merge.py` / hash / precedence functions are the red-green core; the validator + override seams are interface-first with injected fakes.

- [x] **T1** (AC-1) — Create `apps/api/app/modules/slicer/` package skeleton
  - [x] T1.1 `__init__.py` (empty); stub `models.py`, `resolver.py`, `merge.py`, `overrides.py`, `validation.py`, `bundle_store.py` with module docstrings citing Decision AH + the Story 32.1 spec path. No `router.py`.
- [x] **T2** (AC-2) — Vendor Orca source profiles + check in PLA/TPU fixtures
  - [x] T2.1 Place the PLA + TPU source partials + expected resolved triples under `apps/api/tests/fixtures/slicer/` (small JSON only).
  - [x] T2.2 Document the bench-export step + production vendored-artifact location in Dev Notes; add the settings slot wiring in T8.
- [x] **T3** (AC-3, AC-4) — Pure inheritance merge + normalize in `merge.py` *(red→green)*
  - [x] T3.1 Write failing tests `test_resolve_inheritance_user_partial_overrides_system_default` (≥2-level chain) + `test_normalize_injects_type_for_each_kind` + `test_normalize_drops_instantiation_field`.
  - [x] T3.2 Implement `resolve_inheritance` + `normalize_for_cli` to green; mirror the proven `orca_resolve_profiles.py` behavior.
- [x] **T4** (AC-5, AC-10) — Canonicalized `bundle_hash` *(red→green)*
  - [x] T4.1 Write failing tests: cosmetic-churn stability, slicing-value change, orca_version change, input-order pinning.
  - [x] T4.2 Implement `compute_bundle_hash` with canonical JSON + fixed order + `orca_version`; inline contract comments per AC-10.
- [x] **T5** (AC-6) — Append-only bundle + snapshot store in `bundle_store.py` *(red→green)*
  - [x] T5.1 Write failing tests: idempotent-on-same-hash, snapshot-provenance, retune-creates-new-file-leaving-old.
  - [x] T5.2 Implement hash-fanout filesystem store on `portal-content`; `resolver_version` constant; `created_at` excluded from hash. NO Alembic.
- [x] **T6** (AC-7) — Resolver precedence + classified failure in `resolver.py` *(red→green)*
  - [x] T6.1 Write failing tests, one per precedence branch incl. both classified-failure cases (assert NO silent fallback, NO bundle written on failure).
  - [x] T6.2 Implement the typed result/failure model + the precedence chain.
- [x] **T7** (AC-8, AC-9) — Override-layer + CLI-validator seams *(interface-first)*
  - [x] T7.1 `OverrideProvider` protocol + `NoopOverrideProvider`; tests for injected-override hash change + noop override-free bundle.
  - [x] T7.2 `CliValidator` protocol + `NullCliValidator` + the specified Orca smoke-command constant + required-key schema assertion; tests: validator-called-before-persist, required-key failure, env-gated real-Orca smoke (`ORCA_SMOKE_TEST=1`).
- [x] **T8** (AC-2, AC-10, AC-12) — Settings slots + env docs
  - [x] T8.1 Add the vendored-artifact-location + `orca_version` settings (sourced from `ORCA_VERSION`) to `apps/api/app/core/config.py` (append, with contract comments); config tests for defaults.
  - [x] T8.2 `infra/env.example`: document `ORCA_VERSION` + `FENRIR_EXPORT_PATH` (bench-only, NOT production runtime).
- [x] **T9** (AC-11) — Forward-compat: full process JSON preserved *(red→green)*
  - [x] T9.1 Failing test `test_bundle_preserves_full_process_json_not_a_flattened_layer_height`; ensure the bundle shape stores the full process JSON. No adaptive-height code.
- [x] **T10** (AC-12, AC-14) — Grep invariants + scope fence
  - [x] T10.1 `grep -rniE "/mnt/c|fenrir" apps/api/app/modules/slicer/` → 0; `test_resolver_reads_vendored_artifacts_from_settings_not_hardcoded_path`.
  - [x] T10.2 `git diff main -- apps/api/app/main.py apps/api/app/router.py apps/web/` → 0 lines; no new `apps/api/migrations/versions/` file; no new heavy dep in `apps/api/pyproject.toml`.
- [x] **T-DET** (AC-13) — Determinism gate: 3× consecutive identical pytest pass counts on the slicer suite; document in Dev Agent Record.
- [x] **T11** (full quality gate) — `ruff format` + `ruff check` clean on `apps/api/`; `pytest apps/api/tests/ -v` green = baseline + new slicer/config cases (env-gated real-Orca smoke skipped). No vitest/Playwright (backend-only).
- [x] **T12** (handoff) — dev-story flipped `ready-for-dev → review` (rework); code-review owns `→ done`. **External review APPROVED 2026-06-01 (Critical/Important/Minor: none) → status flipped `review → done`.** **Commit/ff-merge/deploy NOT performed — controller-owned** (per task constraints). Suggested commit scope when the controller commits: `feat(api): Orca profile resolver — merge + normalize + hash + snapshot (Story 32.1, Init 20)`.

## Dev Notes

### Source-of-truth references

- **PRD:** `prd.md` § Initiative 20 — FR20-RESOLVER-1 (+ the resolved OD-1/OD-2/OD-7/OD-8/OD-9 in § Open decisions).
- **Architecture:** `architecture.md` § Initiative 20 — Decision **AH** (resolver responsibilities 1–7, precedence contract, hashing/versioning, data-model surfaces, ownership topology). Decisions AI (slicer-worker; Story 32.2) + AJ (cache/invalidation; Stories 32.3/32.4) consume this story's bundle + hash.
- **Epics:** `epics.md` § Initiative 20 § Story 32.1 (sketch + FR/NFR matrix).
- **SCP:** `sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3.
- **Brainstorm:** `_bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md` (§ 2 data model + ownership topology, § 3 resolver, § 9 OD register).
- **Proven PoC (bench-only, NOT a prod dependency):** `orca_resolve_profiles.py` (Fenrir bench, `/home/ezop/tmp/...` — may be absent on any non-bench machine; this story PRODUCTIONIZES its behavior into `apps/api/app/modules/slicer/merge.py`, it does not import or depend on it).
- **Memory entries (read before implementation):**
  - `[[feedback_scp_pre_enumeration_phase]]` — pre-enumeration § A + cache-coherence § B + magic-constant contract § C (AC-10 source).
  - `[[feedback_codex_model_routing]]` — Story 32.1 → `gpt-5.5` (data-integrity adjacency: hash completeness + no-silent-fallback).
  - `[[feedback_itcm_autonomous_mode]]` — dev-story execution is NOT yet authorized for this story (operator go per SCP § 5); spec authoring only.

### Pre-enumeration save (per `[[feedback_scp_pre_enumeration_phase]]` § A)

Run 2026-05-31 against pre-Story-32.1 repo state:

1. **Files reused (existing — DO NOT duplicate):**
   - `apps/api/app/core/config.py` — `Settings`. T8 EXTENDS with the vendored-artifact-location + `orca_version` slots (pattern mirrors the Init 19 Spoolman field additions).
   - `apps/api/app/modules/spools/client.py` — the Init 19 Spoolman client/cache. Story 32.1 does NOT touch it; Story **32.5** reuses it to back the real `OverrideProvider`. This story only designs the `OverrideProvider` seam (AC-8) so 32.5 slots in without reshaping the resolver.
   - `apps/api/tests/conftest.py` — `monkeypatch` + tmp-path patterns. New slicer tests add local fixtures; no global conftest edit.
   - Hash-fanout layout precedent: the render worker's `<root>/stl|thumb/<hash[:2]>/<hash>` shape (Decision AI) — `bundle_store.py` mirrors it.
2. **NEW (Story 32.1 owns):** `apps/api/app/modules/slicer/{__init__,models,resolver,merge,overrides,validation,bundle_store}.py` + `apps/api/tests/test_slicer_resolver.py` (+ `test_slicer_store.py` if split) + `apps/api/tests/fixtures/slicer/`.
3. **MODIFIED (append-only):** `apps/api/app/core/config.py` (2 slots) + `apps/api/tests/test_config.py` (default cases) + `infra/env.example` (env block).
4. **Contracts UNTOUCHED:** `_PUBLIC_ROUTES`, `share/router.py`, the route-enforcement gate (Story 32.1 mounts no routes — AC-14). No NFR reversal.

**Net scope:** ~7 new module files + 1–2 new test files + 1 fixtures dir + 3 modified files + 0 Alembic + 0 routes + 0 new heavy deps.

### Cache-coherence enumeration (per `[[feedback_scp_pre_enumeration_phase]]` § B)

Story 32.1 produces the **`bundle_hash` half** of the `(stl_hash, bundle_hash)` reproducibility key. It writes the append-only bundle/snapshot store but reads/writes **no Redis estimate cache** (that is Stories 32.3/32.4). The one coherence concern this story owns:

| Concern | Source: Story 32.1 (this story) | Related surface |
|---|---|---|
| `bundle_hash` completeness | folds machine ∥ process ∥ filament ∥ `orca_version` **+ applied Spoolman override set** (`spoolman_overrides_ref`) | Story 32.4 invalidation keys off exactly this hash — an input NOT folded in here = a stale-served-as-fresh bug (R9). AC-5 + AC-8 pin completeness. |
| Hash stability vs churn | canonical JSON ⇒ cosmetic churn does not churn the hash | prevents needless re-slice storms downstream (Story 32.4) |
| Bundle identity | `bundle_hash` IS the file identity; append-only, idempotent | Stories 32.2/32.3 reference bundles by `bundle_hash`; never by a mutable id |

Decision rule: the hash MUST fold **every input that changes slicer output**; cost-only/price is deliberately NOT folded (it is post-slice arithmetic — Decision AJ / OD-7, realized in Story 32.4). This split is the load-bearing design choice and is enumerated here per § B.

### Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` § C)

All literals in AC-10 carry an inline `because "…"` comment. The hash-input ordering + canonicalization params are the highest-stakes constants (a silent change diverges every cache key) — they are byte-pinned and "change requires an SCP" per AC-10.

### Threat-vector enumeration

Story 32.1 routes to `gpt-5.5` for **data-integrity** adjacency, not security-boundary adjacency. Brief survey:

- **No HTTP surface, no auth, no CSRF, no public-bypass family touch** — this story mounts zero routes (AC-14).
- **Filesystem write** to the `portal-content` bundle store: paths are content-hash-derived (`<hash[:2]>/<hash>.json`) — no user-controlled path component, no traversal vector. Resolver inputs are vendored artifacts + checked-in fixtures, not request bodies.
- **No PII** — Orca profile JSON is machine/process/filament settings.
- **Data-integrity (the real risk class):** an incomplete `bundle_hash` or a silent fallback on unsupported input → a plausible-but-wrong estimate served as authoritative. Mitigated by AC-5 (completeness + stability tests), AC-7 (classified failure, never silent fallback), AC-8 (override set folded in).

### Files this story touches

| File | Action | Why |
|---|---|---|
| `apps/api/app/modules/slicer/__init__.py` | NEW (empty) | T1.1 package marker |
| `apps/api/app/modules/slicer/models.py` | NEW | T1.1 — Pydantic shapes + result/failure types |
| `apps/api/app/modules/slicer/merge.py` | NEW | T3 — pure inheritance merge + normalize |
| `apps/api/app/modules/slicer/resolver.py` | NEW | T4 + T6 — hash + precedence + orchestration |
| `apps/api/app/modules/slicer/overrides.py` | NEW | T7.1 — `OverrideProvider` seam + no-op default |
| `apps/api/app/modules/slicer/validation.py` | NEW | T7.2 — `CliValidator` seam + smoke-command spec |
| `apps/api/app/modules/slicer/bundle_store.py` | NEW | T5 — append-only bundle + snapshot store |
| `apps/api/tests/test_slicer_resolver.py` (+ `test_slicer_store.py`) | NEW | T3–T7, T9, T10 pytest cases |
| `apps/api/tests/fixtures/slicer/` | NEW | T2 — PLA + TPU source partials + expected triples |
| `apps/api/app/core/config.py` | MODIFY (append 2 slots) | T8.1 — vendored-artifact location + `orca_version` |
| `apps/api/tests/test_config.py` | EXTEND | T8.1 — default-value coverage |
| `infra/env.example` | EXTEND | T8.2 — `ORCA_VERSION` + `FENRIR_EXPORT_PATH` (bench-only) docs |

**Files this story MUST NOT touch:** `apps/api/app/main.py` (`_PUBLIC_ROUTES`), `apps/api/app/router.py`, `apps/api/app/modules/share/router.py`, `apps/api/app/modules/spools/*` (Story 32.5 reuses it), `workers/render/`, `apps/web/`, `apps/api/migrations/`, `~/repos/configs/*` (HC2 boundary — the slicer-worker container is Story 32.2, configs-side).

### Project Structure Notes

- OD-9-resolved: backend module is `apps/api/app/modules/slicer/` (top-level bounded-context module, mirroring `spools/`); the user-facing `estimates` module is frontend-only (`apps/web/src/modules/estimates/`, Story 32.6). `PrintIntentPreset` (user-facing) lives in `models.py` here but is NOT exposed via any route in this story; `SlicerProfileBundle` (internal) is never sent to the client.
- No conflict with the existing module layout; this is an additive new package.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` § Initiative 20 — Decision AH (resolver responsibilities, precedence contract, hashing/versioning)]
- [Source: `_bmad-output/planning-artifacts/prd.md` § Initiative 20 — FR20-RESOLVER-1 + § Open decisions (OD-1/2/7/8/9 resolved 2026-05-31)]
- [Source: `_bmad-output/planning-artifacts/epics.md` § Initiative 20 § Story 32.1]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-31-stl-slicer-estimates.md` § 4.2 + § 4.3]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (repo-local Claude/BMAD dev-story executor, autonomous mode under Laura/controller).

### Debug Log References

**Rework context.** A prior implementation passed its own tests (33 green) but an
independent reviewer returned **REQUEST_CHANGES**: it was a flat single-PLA
`SlicerProfile` (bounds-checked scalar fields) with *fabricated* AC numbering that
did not match this story's AC-1..AC-14 at all — no Orca triple, no inheritance
merge, no bundle store, no precedence/override/validator seams. The shallow files
(`profile.py`, `validator.py`, `profiles/base_pla.json`) were **deleted** and the
subsystem rebuilt to the actual Decision AH contract under strict TDD.

**RED→GREEN evidence (strict TDD):**

1. RED — wrote fixtures + `test_slicer_resolver.py` + `test_slicer_store.py` first;
   ran them against the (still-shallow) module:
   `ModuleNotFoundError: No module named 'app.modules.slicer.bundle_store'` →
   `Interrupted: 2 errors during collection` (collection-time red).
2. GREEN — implemented `models.py`, `merge.py`, `overrides.py`, `validation.py`,
   `bundle_store.py`, rewrote `resolver.py`; reran the slicer suite →
   `34 passed, 1 skipped` (the skip = env-gated real-Orca smoke).
3. Config slots — added `test_config.py` cases for `orca_version` +
   `slicer_*_dir` defaults (RED on missing fields → GREEN after `config.py` edit);
   `tests/test_config.py` `8 passed`.
4. Fixed an AC-12 leak caught by re-running the grep invariant
   (`grep -rniE "/mnt/c|fenrir" apps/api/app/modules/slicer/` returned `1` — the
   `FENRIR_EXPORT_PATH` literal in `README.md`); reworded the README, tightened the
   grep test to cover all files (not just `*.py`); invariant back to `0`.

### Completion Notes List

- **AC-1** module skeleton at `apps/api/app/modules/slicer/` (no `router.py`):
  `models / merge / resolver / overrides / validation / bundle_store`.
- **AC-2** PLA + TPU source partials + system tree + expected PLA triple checked in
  under `apps/api/tests/fixtures/slicer/`; bench export documented in
  `infra/env.example` (NOT a prod runtime path); zero `/mnt/c`/Fenrir literal in the
  module (AC-12 grep = 0).
- **AC-3** `resolve_inheritance` — recursive, deep-merge child-over-parent, **user
  partial wins**, ≥2-level chain (user → `0.20mm Standard` → `fdm_process_common`),
  inherit-cycle guarded; pure (no I/O).
- **AC-4** `normalize_for_cli` — injects top-level `type` per kind, drops
  `instantiation`, preserves all slicing keys (incl. full process JSON).
- **AC-5/AC-10** `compute_bundle_hash` — canonical JSON (sorted keys, stable float
  repr), fixed order `machine ∥ process ∥ filament ∥ orca_version`, sha256, NUL slot
  separator; cosmetic-churn-stable; every magic constant carries an inline `because`
  contract comment; `orca_version`/`resolver_version` sourced per AC-10.
- **AC-6** append-only hash-fanout store (`bundles/<hash[:2]>/<hash>.json`,
  `snapshots/...`); idempotent first-write-wins (no mutation); provenance snapshot
  (`source_system_tree_ref`, `source_user_partial_hash`, `orca_version`,
  `resolver_version`, `created_at` excluded from hash); NO Alembic.
- **AC-7** precedence `exact bundle > custom override > material-class default >
  unsupported`; typed `ResolveFailure` + `ResolveReason` codes
  (`unsupported_material_class`, `missing_system_profile`, `invalid_partial`,
  `cli_validation_failed`); no silent fallback, no bundle written on failure.
- **AC-8** `OverrideProvider`/`NoopOverrideProvider` seam; override applied to
  filament before hashing, folded via `spoolman_overrides_ref`; injected override
  changes the hash, no-op path is override-free.
- **AC-9** `CliValidator`/`NullCliValidator` seam + `ORCA_SMOKE_COMMAND_TEMPLATE` /
  `build_orca_smoke_command` + required-key schema (TPU `filament_max_volumetric_speed`);
  env-gated `test_resolved_triple_accepted_by_orca_cli_smoke` (`ORCA_SMOKE_TEST=1`,
  default-skipped).
- **AC-10** settings: `orca_version` (`ORCA_VERSION`, default `2.3.2`),
  `slicer_vendored_profiles_dir`, `slicer_bundle_store_dir`; the old invented
  `slicer_orca_enabled` flag removed.
- **AC-11** `test_bundle_preserves_full_process_json_not_a_flattened_layer_height` —
  full process JSON retained; no uniform-layer-height assumption baked in.
- **AC-12** grep invariant `0`; `resolve_intent` reads the settings slot, never a
  hard-coded path.
- **AC-13** determinism: 3× consecutive slicer-suite runs identical
  (`34 passed, 1 skipped` each).
- **AC-14** scope fence: `git diff main -- apps/api/app/main.py apps/api/app/router.py
  apps/web/` empty; no new `apps/api/migrations/versions/` file; `pyproject.toml`
  unchanged (stdlib `json`/`hashlib`/`datetime` + existing Pydantic only).

**Test evidence (exact counts):**

- `uv run pytest -q tests/test_slicer_resolver.py tests/test_slicer_store.py` →
  **34 passed, 1 skipped** (3× identical — AC-13).
- `uv run pytest -q tests/test_config.py` → **8 passed**.
- `uv run pytest -q` (full backend) → **989 passed, 2 skipped** (baseline before
  rework: 986 passed, 1 skipped; the +1 skip is the new env-gated Orca smoke).
- `uv run ruff format --check` + `uv run ruff check` on changed files → clean.
- `git diff --check` → clean.

**Not done (correctly out of scope / controller-owned):** real Orca execution
(Story 32.2), real Spoolman-backed override provider (Story 32.5), commit / ff-merge
/ deploy (controller owns), and the external review pass that flips `review → done`.

### File List

**New (Story 32.1 owns):**

- `apps/api/app/modules/slicer/models.py`
- `apps/api/app/modules/slicer/merge.py`
- `apps/api/app/modules/slicer/overrides.py`
- `apps/api/app/modules/slicer/validation.py`
- `apps/api/app/modules/slicer/bundle_store.py`
- `apps/api/tests/test_slicer_store.py`
- `apps/api/tests/fixtures/slicer/system/*.json` (7 profiles)
- `apps/api/tests/fixtures/slicer/intents/creality-k1-max-microswiss-hf/{PLA,TPU}/standard.json`
- `apps/api/tests/fixtures/slicer/expected/pla_standard_triple.json`

**Rewritten:**

- `apps/api/app/modules/slicer/__init__.py`
- `apps/api/app/modules/slicer/resolver.py`
- `apps/api/app/modules/slicer/README.md`
- `apps/api/tests/test_slicer_resolver.py`

**Modified (append-only):**

- `apps/api/app/core/config.py` (added `orca_version` + 2 slicer dirs; removed `slicer_orca_enabled`)
- `apps/api/tests/test_config.py` (added orca_version + slicer-dir default cases)
- `infra/env.example` (added `ORCA_VERSION` + bench-only `FENRIR_EXPORT_PATH` + slicer dirs)

**Deleted (off-contract shallow impl):**

- `apps/api/app/modules/slicer/profile.py`
- `apps/api/app/modules/slicer/validator.py`
- `apps/api/app/modules/slicer/profiles/base_pla.json`

### Review rework — independent REQUEST_CHANGES (2026-06-01)

An independent reviewer returned **REQUEST_CHANGES** on the post-rework branch.
Five findings were fixed under strict TDD (failing test first, then implementation);
scope was limited to the findings — no unrelated refactors.

1. **bundle_hash must fold override identity (not just final filament JSON).**
   Bug: an override whose applied values equal the material-class default is a no-op
   on the filament JSON, so it hashed identically to the no-override resolve and the
   exact-cache branch returned the no-override bundle *without* `spoolman_overrides_ref`
   — silently dropping override provenance. Fix: `compute_bundle_hash` now folds the
   override fingerprint (`overrides_ref`) in after `orca_version` (appended only when
   present, so plain no-override hashes stay byte-identical to the legacy 4-part key).
   Tests: `test_bundle_hash_folds_override_fingerprint`,
   `test_resolve_override_equal_to_default_is_distinct_from_noop`. README updated.
2. **Malformed intent partials must classify, not crash.** A vendored intent file
   missing `machine`/`process`/`filament` (or with a non-dict entry, or not an object)
   raised a bare `KeyError`/`TypeError`/`AttributeError`. Fix: a shape gate (step 1b in
   `resolve`) returns `ResolveFailure(reason=invalid_partial)`. Test:
   `test_resolve_malformed_partial_yields_invalid_partial` (5 parametrized shapes).
   **Follow-up (focused reviewer):** a dict entry whose `inherit` is the wrong *type*
   (e.g. `{"machine": {"inherit": ["M"]}}`) clears the shape gate (it is a dict) but
   `resolve_inheritance` then raised a bare `TypeError: unhashable type: list` on the
   cycle check. Fix: `resolve_inheritance` now raises a typed `InvalidPartialError` when
   `inherit` is not a system-profile name string, which `resolve` catches and classifies
   as `invalid_partial`. The parametrized test grew to **6 shapes** (added the
   invalid-inherit-type case).
3. **Snapshot provenance must bind system-tree content, not just its path.** The
   vendored system tree is edited in place; the snapshot hashed only the root-path
   string + user-partial hash, so an in-place system-profile change aliased the old
   snapshot. Fix: `SourceProfileSnapshot.source_system_tree_hash` (a content hash of
   the whole system tree) is added and folded into `snapshot_hash`. Test:
   `test_snapshot_hash_reflects_system_tree_content`.
4. **Append-only writes must be concurrency-safe / first-write-wins.** The old
   `_atomic_write` used a shared `<hash>.json.tmp` (writer race) and `tmp.replace(path)`
   (overwrote between `exists()` and publish). Fix: unique per-writer tmp via
   `tempfile.mkstemp` + atomic `os.link` publish that raises `FileExistsError` if the
   path exists (kept = first writer's; provenance preserved even when `exists()` races).
   Test: `test_write_bundle_first_write_wins_even_if_exists_check_races`.
5. **`SLICER_BUNDLE_STORE_DIR` default no longer double-nests.** Default was
   `/data/content/slicer/bundles`, but `BundleStore` appends its own `bundles/` child →
   `…/slicer/bundles/bundles/…`. Fix: default is now the store ROOT `/data/content/slicer`
   (holds `bundles/` + `snapshots/`); `config.py`, `infra/env.example`, README, and the
   config test aligned. Tests: `test_default_store_dir_is_root_no_double_bundles_nesting`,
   updated `test_slicer_artifact_dirs_default_under_portal_content`.

**Files modified in this rework** (all pre-existing — no new files):
`apps/api/app/modules/slicer/resolver.py`, `…/models.py`, `…/bundle_store.py`,
`…/README.md`, `apps/api/app/core/config.py`, `infra/env.example`,
`apps/api/tests/test_slicer_resolver.py`, `apps/api/tests/test_slicer_store.py`,
`apps/api/tests/test_config.py`.

**Review-rework test evidence (exact counts, verified):**

- RED first: `tests/test_slicer_resolver.py tests/test_slicer_store.py tests/test_config.py`
  → **11 failed, 41 passed, 1 skipped** (the 11 were exactly the new findings' tests:
  `TypeError` on `overrides_ref`, `KeyError`/`TypeError`/`AttributeError` on malformed
  partials, equal snapshot hashes, clobbered first-write, double-`bundles` nesting).
- GREEN after fixes (same trio): **52 passed, 1 skipped** — 3× consecutive identical
  (determinism, AC-13).
- `uv run pytest -q` (full backend) → **999 passed, 2 skipped** (was 989 passed,
  2 skipped before the +10 review-fix tests).
- `uv run ruff check` + `uv run ruff format --check` on changed files → clean
  (`All checks passed!`, `11 files already formatted`).
- `git diff --check` + `git diff --cached --check` → clean.

### Review approval — close-out (2026-06-01)

**Status flip: `review → done`.**

A final external review pass — sourced from the **Hermes delegate external reviewer**
(used because `laura-gemini-review` / the Gemini CLI were **not available on this
host**) — returned **APPROVED** with **no Critical, no Important, no Minor** findings
after the latest invalid-inherit fix. The reviewer confirmed:

- malformed `inherit` of the wrong type in machine/process/filament returns
  `ResolveFailure(reason=invalid_partial)` (the focused follow-up fix, finding 2);
- override-equals-default hash/provenance behavior (finding 1);
- system-tree identity hash binding (finding 3);
- `BundleStore` first-write-wins concurrency safety (finding 4);
- default store dir without double `bundles/` nesting (finding 5);
- the Story 32.1 Decision AH contract (AC-1..AC-14) overall.

**Final controller gates (verified, post invalid-inherit fix):**

- `git diff --check` && `git diff --cached --check` → clean.
- Targeted `tests/test_slicer_resolver.py tests/test_slicer_store.py tests/test_config.py`
  → **53 passed, 1 skipped** (+1 over the 52 in the prior rework — the added
  invalid-inherit-type parametrized shape).
- Edge reproduction: malformed `inherit` list ⇒ `ResolveFailure invalid_partial`.
- Full backend `uv run pytest -q` → **1000 passed, 2 skipped** (was 999 passed,
  2 skipped before the invalid-inherit-type test).
- `ruff check` + `ruff format --check` → clean.

**Still controller-owned (NOT performed here):** commit / ff-merge / deploy.

### Pre-push gate fix — settings/env/compose drift (2026-06-01)

The pre-push `infra/scripts/check-all.sh` stage `settings-env-compose-diff` failed:
the three new Settings fields (`orca_version`, `slicer_vendored_profiles_dir`,
`slicer_bundle_store_dir`) were documented in `infra/env.example` but **not wired**
into the `api` / `arq-worker` `environment:` blocks of `infra/docker-compose.yml`,
and `FENRIR_EXPORT_PATH` (bench-only export path, not a production Settings field)
had no allowlist entry.

Fix (minimal, no behavior change):

- Wired `ORCA_VERSION` / `SLICER_VENDORED_PROFILES_DIR` / `SLICER_BUNDLE_STORE_DIR`
  into both the `api` and `arq-worker` env blocks with `${VAR:-<default>}` defaults
  matching `config/env.example` (`2.3.2`, `/data/content/slicer/vendored`,
  `/data/content/slicer`).
- Added `FENRIR_EXPORT_PATH` to `KNOWN_INFRA_ONLY` in
  `infra/scripts/check-settings-env-compose.py` (bench-only, NFR20-CONTAINER-1).

Gate result after fix: `check-settings-env-compose.py` → **OK** (44 Settings / 42
env.example / 32 compose env refs aligned); `git diff --check` &&
`git diff --cached --check` → clean.
