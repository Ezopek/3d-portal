# Story 35.1: Profile-selection policy model + store + precedence resolver

Status: done

<!--
  Authored by the repo-local BMAD author (Laura/Hermes delegated). Source planning artifacts:
  epics.md § Initiative 23 (Epic E35 + Story 35.1); SCP
  sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md (status approved — Task 1).

  GATE NOTE: Unlike the default G-DEVGO posture (spec-only until explicit operator dev-go), the
  operator delegated implementation of THIS first slice (35.1) in the task prompt. This story is
  therefore authored AND implemented in the same run on branch
  feat/spoolman-filament-profile-estimates. Pure/standalone/deploy-clean: a new module + tests + one
  settings slot, no resolver/API/worker coupling, no Alembic, no on-disk worker change → SW-DEPLOY-1
  overlay-rebuild gate NOT tripped. Later E35 stories (35.2–35.6) stay gated on per-story
  bmad-create-story + dev-go.
-->

## Story

As the **portal operator**,
I want **a portal-owned profile-selection policy (generic-material default Orca filament profiles plus optional per-Spoolman-filament exact overrides) with a deterministic precedence resolver and a file-backed store**,
so that **later slices can pick the Orca filament profile for an estimate from Spoolman's generic material — automatically for normal colors, with an explicit exact-override exception path — and classify each estimate's profile source honestly (exact / default / unavailable).**

This is the **pure, standalone, deploy-clean foundation slice** of Epic E35 (SCP Task 1). It adds **no** resolver/API/worker coupling, **no** DB table, **no** Alembic migration, and **no** worker image change — so SW-DEPLOY-1 is **NOT** triggered.

## Acceptance Criteria

### Policy model + normalization

- **AC-1** `EstimateProfileSource` is a `StrEnum` with exactly `exact_filament_mapping`, `default_material_profile`, `unavailable_no_profile`.
- **AC-2** `normalize_material(" pla ")` → `"PLA"`; `normalize_material("")` / whitespace-only / `None` → `None` (unconfigured — never an invented variant; no `PLA+`→`PLA` coercion).
- **AC-3** `MaterialDefault` and `FilamentOverride` are Pydantic v2 models with `extra="forbid"`, carrying `orca_filament_profile_ref: str` + `enabled: bool = True`.
- **AC-4** `ProfilePolicy` holds `material_defaults: dict[str, MaterialDefault]` + `filament_overrides: dict[str, FilamentOverride]`; material-default keys are normalized at construction so `" pla "` and `"PLA"` collapse to one entry.

### Precedence resolution (pure)

- **AC-5** Exact override wins: a selected `spoolman_filament_ref` present + `enabled` in `filament_overrides` ⇒ `exact_filament_mapping` with that profile ref, regardless of the material default.
- **AC-6** Material default: no usable override but a normalized material present + `enabled` in `material_defaults` ⇒ `default_material_profile` with that profile ref.
- **AC-7** Unavailable: no usable override and no usable material default ⇒ `unavailable_no_profile` with `orca_filament_profile_ref is None`.
- **AC-8** Disabled fall-through: an `enabled=false` exact override falls through to the material default (or unavailable); a disabled material default ⇒ unavailable.
- **AC-9** The `ProfileSelection` result carries `source`, `orca_filament_profile_ref` (None iff unavailable), `selected_material` (the normalized material), and `selected_spoolman_filament_ref` (set only on an exact mapping).

### Store + validation seam

- **AC-10** `ProfilePolicyStore.save()`→`.load()` is an identity roundtrip; `.load()` on a missing file returns an empty `ProfilePolicy`.
- **AC-11** `.save()` is atomic (a concurrent reader never sees a partial file — temp + fsync + `os.replace`, mirroring `attribution_store` / `estimate_store`); `.load()` is mtime-cached and re-reads after a save.
- **AC-12** Overrides are keyed by `spoolman_filament_ref()` (vendor∥material∥name), never the churning Spoolman integer id (NFR23-STABLE-KEY-1).
- **AC-13** `unknown_profile_refs(policy, known_refs)` returns the set of policy profile refs absent from `known_refs` — a pure validation seam with **no** concrete Orca ref hard-coded in the model or its tests.
- **AC-14** A `slicer_profile_policy_dir` settings slot + a settings-wired `load_profile_policy()` convenience exist (no hard-coded bench path).

## Tasks / Subtasks

1. **(RED)** Write `apps/api/tests/test_slicer_profile_policy.py` covering AC-1..AC-14; run to confirm failure (module absent).
2. **(GREEN)** Implement `apps/api/app/modules/slicer/profile_policy.py`: enum, `normalize_material`, models, `ProfileSelection`, `ProfilePolicy.resolve_selection`, `ProfilePolicyStore`, `unknown_profile_refs`, `load_profile_policy`.
3. Add the `slicer_profile_policy_dir` settings slot in `apps/api/app/core/config.py`.
4. **(VERIFY)** Run targeted pytest (3× determinism), `ruff format` + `ruff check` on touched files.
5. Update sprint-status 35-1 row + commit on the story branch.

## Dev Notes

### Pre-enumeration save (existence checklist)

- `spoolman_filament_ref(filament)` already exists at `overrides.py:174` (vendor∥material∥name, `\x1f`-joined) — REUSE for override keying; do NOT add a second ref function.
- `MaterialClass = Literal["PLA","PETG","PCTG","TPU"]` at `models.py:22` — the resolver's *known* material classes. The policy material keys are normalized **strings** (not the Literal) because the SCP allows materials beyond the current resolver set (e.g. `ABS`) to be *configured-or-unconfigured* without a code change; coupling the policy key to the Literal would forbid that. The 35.2 resolver integration is where the Literal still gates the actual vendored-profile resolve.
- Atomic-publish + flock idiom: `attribution_store.py:212` `_atomic_publish` + `:193` `_record_lock` — MIRROR, do not reinvent.
- Settings idiom: `config.py:118` `slicer_bundle_store_dir` (a `Path` slot) — add `slicer_profile_policy_dir` the same way.

### Magic-constant discipline

- The policy store filename is the only literal: `profile_policy.json`. No numeric magic constants in this slice.

### Out of scope (deferred to later E35 stories)

resolver/bundle wiring (35.2); Spoolman snapshot → material/ref map (35.2/35.3); estimate API + DTO metadata (35.3); admin surface (35.4); UI labels (35.5); bounded backfill (35.6).

### References

- SCP: `sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md` § Task 1 + § Data model target.
- epics.md § Initiative 23 / Epic E35 / Story 35.1.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M) — repo-local BMAD author/dev (Laura/Hermes delegated).

### Completion Notes List

- 2026-06-07 (repo-local BMAD author): RED→GREEN→REFACTOR complete on `feat/spoolman-filament-profile-estimates`.
  - RED: `tests/test_slicer_profile_policy.py` (25 tests) failed on absent module (confirmed).
  - GREEN: `apps/api/app/modules/slicer/profile_policy.py` implemented (enum, `normalize_material`,
    models, `ProfileSelection`, `ProfilePolicy.resolve_selection`, `ProfilePolicyStore`,
    `unknown_profile_refs`, `load_profile_policy`) + `slicer_profile_policy_dir` settings slot +
    env.example + docker-compose api/arq-worker wiring.
  - Gates run (scope-targeted): `test_slicer_profile_policy.py` **25 passed ×3** (NFR23-DETERMINISM-1);
    related slicer suites (resolver + estimate + spoolman_overrides) **191 passed, 1 skipped** (no
    regression); settings↔env↔compose drift gate **OK** (54/52/42 aligned); `ruff format --check` +
    `ruff check` **clean** on all touched files; import sanity (`load_profile_policy` + settings) OK.
- **Close-out gate (review → done): CLEARED.** External Gemini review (`laura-gemini-review`,
  gemini-2.5-pro) recorded **APPROVE** — 0 Critical / 0 Important / 0 Minor. Controller then ran the
  full repo merge gate `infra/scripts/check-all.sh` — **all green, 16 passed / 0 failed** (apps/api +
  workers/render `ruff format`/`check`, apps/web typecheck + build + lint + vitest, apps/api +
  workers/render + infra/scripts pytest, apps/web visual regression, settings↔env↔compose diff,
  uv-lock checks ×2; local-env-secrets skipped OK — no `infra/.env`). Deploy-clean backend-only
  foundation slice — pure additive module + config defaults, SW-DEPLOY-1 NOT triggered, no deploy
  needed.

### File List

- `apps/api/app/modules/slicer/profile_policy.py` (new)
- `apps/api/tests/test_slicer_profile_policy.py` (new)
- `apps/api/app/core/config.py` (modified — `slicer_profile_policy_dir` slot)

## Change Log

- 2026-06-07 — story authored + implemented (same run, operator-delegated 35.1 dev-go).
- 2026-06-07 — controller closeout: Gemini APPROVE on record + full `check-all.sh` 16/16 green; status review → done.
