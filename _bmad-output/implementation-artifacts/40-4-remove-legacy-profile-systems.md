---
story: 40.4
id: 40-4-demote-legacy-profile-grid
status: done
created: 2026-06-21T17:53Z
updated: 2026-06-21T17:53Z
operator_gate: opened-explicitly
---

# 40.4 — Remove legacy profile systems

## Operator decision

The previous 40.4 assessment deferred removal because legacy systems still had active callers. On 2026-06-21 the operator explicitly reopened the gate and decided that old profile systems must be removed completely: no old Profiles grid, no `material_defaults`, no default-matrix, no parallel legacy SoT.

Safety boundary: this story deletes repository code/tests/UI/docs for the legacy systems. It does **not** delete live external profile files or runtime data outside the repo.

## Final SoT

The remaining profile source of truth is:

1. **Profile Library** imported machine/process/filament blocks.
2. **Profile Offers** composed from Profile Library blocks.
3. Published offer `published_bundle_hash` for estimate lookup/recompute.
4. Offer-driven recompute endpoint: `POST /api/admin/profiles/offers/recompute-estimates`.

## Removed surfaces

### Backend

- Removed old admin profile grid/import endpoints:
  - `GET /api/admin/profiles`
  - `POST /api/admin/profiles/import`
- Removed profile policy/material-default/default-matrix system:
  - `/api/admin/policy*`
  - `profile_policy.py`
  - `profile_selection.py`
  - `enqueue_default_matrix_backfill.py`
  - default-matrix STL upload hook.
- Removed estimate read/router policy fallback and profile-selection metadata.
- Kept Profile Library, Profile Offers, member published offers, publish/unpublish, and offer-driven recompute.

### Frontend

- Removed `/admin/profiles` route/tab/page.
- Removed `ProfileInventoryGrid`, old admin profile hooks, and legacy import UI/tests.
- Removed Profile Offers policy/advanced panel and policy/default-matrix locale keys/visual stubs.
- Kept Profile Library and Profile Offers as the only admin profile surfaces.

### Tests

- Deleted legacy policy/grid/import tests.
- Updated resolver/estimate/SOT/worker tests to the single-SoT architecture.
- Kept and updated Profile Library, Profile Offers, member offers, publish, and offer recompute coverage.

## Verification run by controller

- Python compile: `python3 -m compileall -q apps/api/app apps/api/tests` — pass.
- API targeted regression:
  - command: `uv run pytest tests/test_admin_profile_publish.py tests/test_admin_profile_offers.py tests/test_admin_profile_library.py tests/test_member_profile_offers.py tests/test_matrix_backfill.py tests/test_route_enforcement_gate.py tests/test_slicer_resolver.py tests/test_estimate_api.py tests/test_slicer_worker.py tests/test_sot_admin_files.py -q --tb=short`
  - result: `240 passed, 1 skipped`.
- Web targeted regression:
  - `npm run typecheck` — pass.
  - `npm run lint -- --max-warnings=0` — pass.
  - `npm run test -- --run ProfileOffersPage AdminTabs ProfileLibraryPage profile-offers-i18n profile-library-i18n` — `31 passed`.
- Residue scan over `apps/` excluding current `/profiles/offers` and `/profiles/library` routes: no matches for old `material_defaults`, default-matrix, `ProfileInventoryGrid`, `ProfilesPage`, old `/admin/profiles`, policy module, or old import hooks.

## Notes

Full gate, Aider review, merge/deploy, and live smoke remain controller steps after this artifact.
