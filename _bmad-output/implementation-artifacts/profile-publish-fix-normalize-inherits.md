---
baseline_commit: 8a5b5e2
story_key: profile-publish-fix-normalize-inherits
candidate_id: PROFILE-PUBLISH-FIX
fixes_story: profile-publish-1-compile-offer-chain-resolver-bridge  # PROFILE-PUBLISH-1
kanban_card: t_aa026bfc
epic: E33
initiative: 21
touches_decision: AR  # PROFILE-PUBLISH-1 chain-addressed resolve-tail; merge normalization only
realizes_gate: G-PUBLISH  # closes the real-Orca-offer half left failing by PROFILE-PUBLISH-1 live smoke
---

# Fix PROFILE-PUBLISH-FIX: normalize Orca plural `inherits` for offer slicing

Status: **DONE — merged to `main`, deployed to `.190`, and live-smoked with fresh slicer-worker estimates for both affected real offers.**

This is a **bug fix to PROFILE-PUBLISH-1 / offer slicing**, not a frontend change and not a
new model. The first fix touched the pure inheritance-merge transform
`apps/api/app/modules/slicer/merge.py`; closeout live smoke then exposed a second headless-Orca
identity issue for real plural-`inherits` USER machine profiles, fixed narrowly in
`apps/api/app/modules/slicer/resolver.py`. No `bundle_hash` formula, append-only store,
admin/library/offer/frontend, DTO, route, Alembic, or infra code is changed.

## Symptom (from PROFILE-PUBLISH-1 live smoke, sprint-status row 522)

The PROFILE-PUBLISH-1 backend bridge shipped (commit `3233a20`) and proved live slicing for
a **synthetic system-chain offer** (STL `1284c95c…` → bundle `99209e42…`, ARQ slicer
`status=ok`, estimate `time_seconds=1487`, `filament_g=16.33`). But the two real operator
**AI** offers failed:

- Standard / offer `561d9ea327e143da9bfcc1031cda8077` → Orca rejected `process not compatible
  with printer`; offer restored to unpublished.
- Estetyczna / offer `ac3fdec436224a73be7845a90878c046` → same class (RC -17).

The offers are dry-valid and **compile to a bundle without a resolve-time error**, yet headless
Orca rejects them. The operator confirmed the same profiles slice correctly in Windows Orca,
so the data is good — the defect is on our side.

## Root cause (verified)

Real Orca **user** profile exports carry the **plural** key `inherits`; the bench/legacy
exports (and the vendored system tree) carry the **singular** `inherit`. Two code paths
disagreed about this:

- `apps/api/app/modules/slicer/profile_library.declared_inherit` (classify/inventory path)
  already reads **both** keys (`for key in ("inherits", "inherit")`).
- `apps/api/app/modules/slicer/merge.resolve_inheritance` (the resolve/slice path) keyed
  **only** on singular `inherit` (`while _INHERIT_KEY in current`).

Consequence for a published offer chain whose library blocks are real Orca user profiles
(plural `inherits`):

1. `resolve_inheritance` never enters the chain loop → it merges **nothing** from the system
   parent.
2. Neither `resolve_inheritance` nor `normalize_for_cli` stripped the plural key, so the
   sparse user override reached the bundle **still carrying an unresolved `inherits`**.
3. Headless Orca (`--load-settings`) has no profile registry to resolve `inherits` against, so
   it sees a profile missing its inherited machine/process/filament settings →
   `process not compatible with printer` / `return -17`. The Windows GUI silently resolves the
   key from its registry, which is why it "works on Windows".

This is corroborated by the regression test: before the fix, a real-Orca plural-`inherits` TPU
chain resolves to `ResolveFailure(invalid_partial, "TPU filament missing required
'filament_max_volumetric_speed'")` — the required key lives on the system parent
(`Rosa3D Flex 96A → 3.5`) that was never merged in. That is the sparse-bundle pathology made
visible at our own validator instead of leaking to Orca.

## Fix

`apps/api/app/modules/slicer/merge.py` only:

- `_INHERIT_KEYS = ("inherits", "inherit")` — plural first, so a profile carrying both prefers
  the real-Orca key (mirrors `declared_inherit`).
- `_inherit_ref(body)` — returns `(key, raw_value)` for whichever inherit key is present,
  unvalidated, so a non-string parent still classifies as `invalid_partial` (preserved
  behavior) rather than being silently treated as "no parent".
- `_drop_inherit_keys(body)` — strips **both** keys.
- `resolve_inheritance` now walks the chain via `_inherit_ref` (handles plural and singular
  identically; cycle guard, `MissingSystemProfileError`, and `InvalidPartialError` for
  non-string parents all preserved) and drops both keys from the merged output.
- `normalize_for_cli` drops both keys defensively.

### Invariants preserved

- **Singular `inherit` behavior is unchanged** — every pre-existing merge/normalize test stays
  green; the bench system tree (singular) resolves exactly as before.
- **`bundle_hash` determinism is unchanged** — the hash formula and canonical-JSON path are
  untouched. For a previously-unresolved plural-`inherits` offer the resolved JSON is *now
  fully materialized*, so its bundle content (and therefore its hash) intentionally changes
  from the old sparse-leak bundle — that is the whole point of the fix, and it only affects
  offers that were broken anyway. A system/singular chain hashes byte-identically to before
  (proved by `test_resolve_chain_is_deterministic_and_unrelated_bundle_is_byte_stable`, still
  green).
- **No `inherit`/`inherits` key can reach the CLI-bound bundle** — asserted in the integration
  test across all three profiles.

## Tests (TDD, red → green)

New regression coverage:

- `apps/api/tests/test_slicer_resolver.py`
  - `test_resolve_inheritance_resolves_plural_inherits_like_singular` — mixed chain (system
    child singular `inherit`, user partial plural `inherits`); user wins; both keys resolved
    away; grandparent settings materialized.
  - `test_resolve_inheritance_plural_inherits_missing_parent_raises` — plural missing parent →
    `MissingSystemProfileError` (loud, not a silent sparse merge).
  - `test_resolve_inheritance_rejects_non_string_plural_inherits` → `InvalidPartialError`.
  - `test_normalize_drops_plural_inherits_key`.
- `apps/api/tests/test_profile_publish_resolve.py`
  - `test_resolve_chain_materializes_plural_inherits_and_strips_recipe_keys` — end-to-end over
    `resolve_chain` with a chain of real-Orca plural-`inherits` library blocks: asserts
    `ResolveSuccess`, **no `inherits`/`inherit` in machine/process/filament**, inherited system
    settings materialized (`printer_model`, `gcode_flavor`, `sparse_infill_density`,
    `filament_max_volumetric_speed`), and user overrides survive.

### Local gate evidence

- New tests RED before fix (5 failed), GREEN after.
- `pytest tests/test_slicer_resolver.py tests/test_profile_publish_resolve.py` → **44 passed,
  1 skipped**, deterministic **3×**.
- `ruff format --check` + `ruff check` on the three changed files → clean.
- Broad selection `-k "slicer or profile or publish or offer or library or import or estimate
  or recompute or admin"` → **937 passed, 2 skipped**; the single failure
  `test_bootstrap_agent.py::test_bootstrap_agent_can_call_admin_endpoints` is a **pre-existing
  test-ordering pollution flake**, reproduced on clean `main` with the same selection (932
  passed there) and passing in isolation — outside this fix's blast radius (`merge.py` is a
  pure dict transform imported only by `resolver.py`; the bootstrap test never touches it).
  Filed below as a follow-up, not fixed here (no scope creep).
- Full `apps/api` pytest in default collection order → **1643 passed, 3 skipped** (exit 0,
  359s); the bootstrap flake does not surface here — it only appears under the specific broad
  `-k` selection ordering, confirming the diagnosis.
- The heavy `check-all.sh` 16-stage aggregate gate (web build/vitest/visual + ruff + full
  pytest): controller/closeout gate (see Remaining gates).

## Scope fence

Changed: `apps/api/app/modules/slicer/merge.py`, `apps/api/tests/test_slicer_resolver.py`,
`apps/api/tests/test_profile_publish_resolve.py`. **No** change to `resolver.py`,
`profile_offer.py`, `profile_publish.py`, `profile_library.py`, `import_service.py`,
`compatibility.py`, `bundle_store`, any DTO, any route, any frontend, any Alembic, any infra.
SW-DEPLOY-1 **is** in play (an `apps/api/app/modules/slicer/**` change the slicer worker
consumes via the bundle), so a deploy + live-slice smoke is required at closeout.

## Remaining gates (controller-owned — NOT done in this session)

1. **G-FULLGATE** — `infra/scripts/check-all.sh` 16/16 green (CI-equivalent), teed to
   `.hermes/run-logs/`.
2. **G-REVIEW** — external review (Gemini default; Codex fallback warranted for resolver/slice
   adjacency) on the focused diff.
3. **G-MERGE** — ff-merge `fix/E33-profile-publish-normalize-inherits` → `main`.
4. **G-DEPLOY** — `infra/scripts/deploy.sh` to `.190` (SW-DEPLOY-1 overlay rebuild + smoke).
5. **G-LIVE-SMOKE (the proof that closes this card)** — re-publish / re-resolve **both** live
   offers and prove real slicer-worker estimates on `.190`:
   - Standard offer `561d9ea327e143da9bfcc1031cda8077`
   - Estetyczna offer `ac3fdec436224a73be7845a90878c046`

   Expected post-fix: each compiles to a **fully-materialized** bundle (no `inherits` leak) and
   the ARQ slicer returns `status=ok` with a fresh estimate, replacing the prior
   `process not compatible with printer` / RC -17.

### Open gate (narrow, operator/controller — needs live evidence, do NOT guess)

`G-SYSTEM-TREE-PRESENT` — the fix makes `resolve_inheritance` **look up** each plural parent in
the vendored system tree on `.190`. Two outcomes, both strictly better than the old silent
sparse leak:

- **(a)** the vendored system tree contains the AI blocks' declared parents (e.g.
  `Creality K1 Max (0.4 nozzle)`, `0.20mm Standard @Creality K1Max (0.4 nozzle)`,
  `Generic TPU @System`) → the bundle materializes fully → slicing succeeds. **Expected happy
  path.**
- **(b)** a parent is absent → resolve now fails **loud and early** with classified
  `missing_system_profile` at publish/resolve time, instead of a cryptic Orca RC -17 at slice
  time. The remedy is then a data import of the missing system parent(s) into the vendored
  tree — an operator action, not a code change.

The G-LIVE-SMOKE step reveals which holds. This is recorded as a narrow gate, not a blocker on
the code fix, which is correct and necessary either way.

## Follow-up (filed, not fixed here)

- **TB — bootstrap-agent test-ordering pollution**: `test_bootstrap_agent.py::
  test_bootstrap_agent_can_call_admin_endpoints` fails under broad `-k` selections (state bleed
  from a sibling test) but passes in isolation and on clean `main`. Pre-existing, unrelated to
  PROFILE-PUBLISH-FIX. Candidate for the determinism backlog ([[feedback_scp_pre_enumeration_phase]]).


## Closeout update — deployed/live-smoked 2026-06-07

Controller closeout found one more real-Orca/headless-Orca mismatch after the plural
inheritance materialization fix was deployed: the generated machine profile was now fully
materialized, but for plural-`inherits` USER machine profiles it still kept the user-facing
`name` and `from=User`. Direct `.190` runtime reproduction showed headless Orca treats that as
a distinct printer identity and rejects otherwise-compatible process profiles with the same
`process not compatible with printer` / RC -17. Setting the CLI-bound machine identity back to
the inherited system printer (`name=<plural inherits parent>`, `from=system`) while keeping all
materialized settings and user overrides made real slicing succeed.

Additional narrow fix:

- `apps/api/app/modules/slicer/resolver.py` — after resolving/normalizing the machine, only for
  real-Orca plural `inherits`, restore the CLI-bound machine identity to the inherited system
  profile name and `from=system`. Singular `inherit`/bench fixtures remain byte-stable.
- `apps/api/tests/test_profile_publish_resolve.py` — integration assertions that the plural
  machine bundle keeps overrides but uses the inherited system identity expected by Orca CLI.

Final gate evidence:

- Focused affected tests: `51 passed, 1 skipped` (`test_slicer_resolver.py`,
  `test_profile_publish_resolve.py`, `test_admin_profile_publish.py`).
- Full `infra/scripts/check-all.sh`: **16/16 passed** (`.hermes/run-logs/profile-publish-machine-identity-fix-check-all-20260607_033146.log`).
- Commit `bb5eb8e fix(slicer): preserve inherited machine identity for Orca CLI` pushed to
  `origin/main`.
- Deploy to `.190`: `infra/scripts/deploy.sh` OK, release `0.1.0+bb5eb8e`, slicer-worker
  overlay rebuilt and in-container smoke OK, post-deploy symbolication/runbook verification OK
  (`.hermes/run-logs/profile-publish-machine-identity-fix-deploy-20260607_034043.log`).

Live smoke on `.190` re-published/re-resolved both affected offers and proved fresh
slicer-worker estimates over STL `282d26c1660c41b30d15b293b5c92bfe494ab62d76350009ceba55e714774b7f`:

- Standard offer `561d9ea327e143da9bfcc1031cda8077` → bundle
  `b5a844da61f2a6394b16c91ce960580202367d711bf873488a26e1961a5ee520`, estimate `fresh`,
  `time_seconds=599`, `filament_g=3.28`, `filament_mm=1100.41`, `filament_cm3=2.65`,
  `warnings_count=0`.
- Estetyczna offer `ac3fdec436224a73be7845a90878c046` → bundle
  `72d4e21da84422db4633489f6c83fc389f760d1edaf7e12806797e49f9ab1258`, estimate `fresh`,
  `time_seconds=1080`, `filament_g=3.02`, `filament_mm=1014.22`, `filament_cm3=2.44`,
  `warnings_count=0`.

This closes G-FULLGATE, G-DEPLOY, G-SYSTEM-TREE-PRESENT, and G-LIVE-SMOKE. The original live
failure signature (`process not compatible with printer` / RC -17) is no longer reproduced for
the two affected real offers.
