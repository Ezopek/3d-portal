---
story: 40.3
status: done
branch: feat/E40.3-member-visible-default-offer-selection
created: 2026-06-21T15:21Z
updated: 2026-06-21T15:27Z
---

# Story 40.3 — Member visible/default offer selection

## Goal

Finish the member-facing Epic 40 offer-first correction after Stories 40.1–40.2:

- `GET /api/profiles/offers/published` must expose only offers that are both published and `visibility == "visible"`.
- The member-safe offer DTO must carry `is_default` so the catalog can start on the operator-chosen default offer without exposing admin-only internals.
- `FilesTab` must select the default visible offer when the offer list loads, with fallback to the first visible offer, while preserving a valid manual selection and explicit manual fallback to preset mode.

## Acceptance criteria

- AC1 — Hidden-but-published offers are omitted from the member published-offers response.
- AC2 — Member DTO includes `is_default: boolean` and still excludes `visibility`, `publish_state`, bundle hashes, chain/block refs, paths, and other internals.
- AC3 — `FilesTab` auto-selects the first `is_default` visible offer after the list loads.
- AC4 — If no visible offer is default, `FilesTab` falls back to the first visible offer.
- AC5 — A still-valid manual selected offer remains selected after refetch/list settle.
- AC6 — Manual clear to `None`/preset mode is preserved while the current list remains valid; empty list clears selection.
- AC7 — Existing auth gates and no-STL behavior remain unchanged.

## Implementation summary

- Backend member route now filters sidecars by `publish_state == published` and `visibility == visible`.
- `MemberPublishedOfferView` / web API type now include safe `is_default`.
- `FilesTab` selection effect now chooses default-or-first on load and keeps render side effects out of render.
- Picker contract remains unchanged except fixtures now include `is_default`; the existing none option remains available for manual fallback to preset mode.

## Files changed

- `apps/api/app/modules/slicer/member_router.py`
- `apps/api/app/modules/slicer/schemas.py`
- `apps/api/tests/test_member_profile_offers.py`
- `apps/web/src/lib/api-types.ts`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.test.tsx`
- `apps/web/src/modules/estimates/hooks/usePublishedOffers.test.tsx`

## Verification evidence

Controller-run targeted gates on canonical dev worktree (`192.168.2.170:/home/ezop/repos/3d-portal`):

```text
cd apps/api && uv run pytest tests/test_member_profile_offers.py -q
17 passed, 30 warnings in 2.99s

cd apps/web && npm run test -- FilesTab.test.tsx usePublishedOffers.test.tsx PublishedOfferPicker.test.tsx --run
Test Files 3 passed (3); Tests 43 passed (43)

apps/api/.venv/bin/ruff format --check apps/api/app/modules/slicer/member_router.py apps/api/app/modules/slicer/schemas.py apps/api/tests/test_member_profile_offers.py
3 files already formatted

apps/api/.venv/bin/ruff check apps/api/app/modules/slicer/member_router.py apps/api/app/modules/slicer/schemas.py apps/api/tests/test_member_profile_offers.py
All checks passed!

cd apps/web && npm run typecheck
portal-web@0.1.0 typecheck / tsc -b — exit 0

cd apps/web && npm run lint -- --max-warnings=0
eslint/stylelint — exit 0 (React-version settings warning only)

Aider review (`laura-aider-review-diff`)
Verdict: APPROVE

infra/scripts/check-all.sh 2>&1 | tee .hermes/run-logs/check-all-E40.3-20260621T152359Z.log
passed: 16/16; all green.
```

## 40.4 disposition

A read-only 40.4 assessment found legacy `material_defaults` / intent-grid surfaces are not safely removable in this pass. They still back valid admin/internal operations and tests. Story 40.4 should remain a future gated refactor/deletion story, not part of the safe Epic 40 closeout after 40.3.

Recommended closeout path: finish 40.3, full gate, external review, merge/deploy/smoke, then close Epic 40 with 40.4 deferred/gated.

## Dev Agent Record

- Implementation helper started from `main @ ea08d60` on branch `feat/E40.3-member-visible-default-offer-selection`.
- Controller verified diff and ran targeted gates above.
- Aider review approved the diff.
- Full closeout gate passed: `.hermes/run-logs/check-all-E40.3-20260621T152359Z.log` (16/16, all green).
- Status set to `done` after controller verification.
