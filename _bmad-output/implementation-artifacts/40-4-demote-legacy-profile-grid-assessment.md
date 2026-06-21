---
story: 40.4
status: deferred-gated
created: 2026-06-21T15:27Z
updated: 2026-06-21T15:27Z
---

# Story 40.4 assessment — demote legacy profile grid / material defaults

## Recommendation

Do **not** implement destructive removal in Epic 40 closeout. Keep `40-4-demote-legacy-profile-grid` as a future gated refactor/deletion story.

40.1–40.3 now complete the safe product correction:

- estimates can be recomputed directly from Profile Offers without `material_defaults`;
- admin UI makes offer recompute primary and pushes policy/default-matrix controls into Advanced/Legacy;
- member catalog sees visible offers and starts from the operator default.

The remaining legacy grid / `material_defaults` code still backs valid admin/internal operations and test coverage, so removal is not a safe “finish the epic” action.

## Evidence summary

Active `material_defaults` / policy paths remain:

- `apps/api/app/modules/slicer/profile_policy.py` — policy model/store.
- `apps/api/app/modules/slicer/matrix_backfill.py` — legacy default-matrix enumeration.
- `apps/api/app/modules/slicer/admin_router.py` — admin policy read/upsert/delete and `POST /api/admin/policy/default-matrix-backfill`.
- `apps/web/src/modules/admin/ProfileOffersPage.tsx` and `apps/web/src/modules/admin/hooks/useProfilePolicy.ts` — Advanced/Legacy policy UI still intentionally available.
- Tests: `apps/api/tests/test_slicer_policy_admin.py`, `apps/api/tests/test_matrix_backfill.py`, `apps/api/tests/test_admin_profile_publish.py`.

Active legacy intent-grid paths remain:

- `apps/api/app/modules/slicer/resolver.py` — grid intent source and legacy resolver path.
- `apps/api/app/modules/slicer/import_service.py` — admin import can still write `intents/<printer>/<material>/<tier>.json`.
- `apps/api/app/modules/slicer/admin_router.py` — `/api/admin/profiles` inventory and `/api/admin/profiles/import` remain valid admin/internal surfaces.
- `apps/web/src/modules/admin/ProfileInventoryGrid.tsx` and `apps/web/src/modules/admin/hooks/useImportProfile.ts` — legacy admin grid/import UI remains available.

## Future 40.4 shape

A future explicit 40.4 should be staged and non-destructive first:

1. Feature-flag or further isolate legacy profile grid / policy surfaces as admin-debug/internal.
2. Keep existing endpoints/data stores during compatibility period.
3. Gather caller/test evidence and update docs/OpenAPI copy.
4. Only after separate operator approval consider code/data removal.
5. Never silently delete live `intents/`, bundle, estimate, or policy files.

## Closeout disposition

Epic 40 can close after 40.3 deploy/live smoke with 40.4 deferred/gated. This is intentional, not unfinished implementation drift.
