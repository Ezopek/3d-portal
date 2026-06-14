# Story 36.2: Member estimate-by-offer resolution

---
baseline_commit: c01d3bd
---

Status: done

<!--
  Authored for PROFILE-PUBLISH-2 / Initiative 24 after operator confirmation of OD-1/OD-2/OD-4 defaults.
  Source planning artifacts:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md
  - _bmad-output/planning-artifacts/prd.md § Initiative 24
  - _bmad-output/planning-artifacts/architecture.md § Initiative 24 / Decision AT
  - _bmad-output/planning-artifacts/epics.md § Initiative 24 / Epic E36
-->

## Story

As an **authenticated portal member**,
I want **to read an estimate for a selected published profile offer using only `offer_id + stl_hash`**,
so that **the member picker can display the existing estimate or an honest not-yet-computed state without exposing resolver/bundle internals or triggering a slice.**

This is the second backend slice of Epic E36 / PROFILE-PUBLISH-2. It extends the existing estimate read surface with a published-offer lookup path. It is read-only and does not change admin offer APIs, bundle-store layout, estimate-store layout, queues, slicer workers, or frontend UI. SW-DEPLOY-1 is **NOT** triggered by design.

## Confirmed operator decisions

- **OD-1 accepted:** extend existing `GET /api/estimates` with optional `offer_id`, not a new endpoint.
- **OD-2 accepted:** `spoolman_filament_ref` remains optional; absent means material-default policy context only.
- **OD-4 accepted for this slice:** no on-demand enqueue; a missing estimate is reported as `not_computed`.

## Acceptance Criteria

### Endpoint shape + auth

- **AC-1** Extend existing authenticated `GET /api/estimates` with optional `offer_id`.
- **AC-2** Calls without `offer_id` keep the existing preset-resolution behavior unchanged.
- **AC-3** Calls with `offer_id` require only `stl_hash + offer_id`; `material_class`, `quality_tier`, and `printer_ref` are not required on this path.
- **AC-4** Anonymous requests still return 401 through `current_user`; the route is not added to `_PUBLIC_ROUTES`.

### Published-offer read path

- **AC-5** With `offer_id`, the endpoint reads the offer sidecar and requires active `publish_state == published` with a valid `published_bundle_hash`.
- **AC-6** Missing, malformed, or unpublished offers return 404, not a member-facing resolve 422.
- **AC-7** The offer path reads `EstimateStore(stl_hash, published_bundle_hash)` directly and does not call live resolver / Orca / queue code.
- **AC-8** If a record exists, return normal `EstimateView` projected from that record.
- **AC-9** If no record exists, return `EstimateView.status == "not_computed"` with `offer_id`, nullable numerics, and no fabricated values.

### Policy honesty / leak fence

- **AC-10** Optional `spoolman_filament_ref` may be supplied on the offer path and is used only to compute E35 `profile_selection_context` from the existing profile policy; it must not change the published bundle key or trigger live resolve.
- **AC-11** When policy has no profile, `profile_selection_context.estimate_profile_source == unavailable_no_profile` and the response remains 200 `not_computed`/estimate, not 422.
- **AC-12** Serialized responses must not leak `bundle_hash`, raw Orca refs, profile-chain block IDs, sidecar paths, source snapshot refs, queue/job IDs, or g-code.

### Scope boundaries

- **AC-13** No POST, recompute, enqueue, worker, arq, Alembic, DB, or frontend changes are introduced.
- **AC-14** Existing recompute endpoint is unchanged.
- **AC-15** Full gate remains required before merge.

## Tasks / Subtasks

1. [x] **(RED)** Add backend tests for offer-id read path before production code:
   - `offer_id + stl_hash` works without preset query fields;
   - missing/unpublished offer returns 404;
   - existing record is read by the published bundle hash and resolver is not called;
   - absent record returns `not_computed` and no fabricated numerics;
   - optional `spoolman_filament_ref` yields E35 policy context including unavailable;
   - leak fence forbids published bundle / sidecar internals in serialized JSON.
2. [x] **(GREEN)** Extend `GET /api/estimates` with an offer-id branch while preserving the existing preset branch.
3. [x] Add/adjust DTO status support for `not_computed` without exposing internal keys.
4. [x] **(VERIFY)** Run targeted pytest for estimate API + member offer tests and ruff on touched files.
5. [x] Update Dev Agent Record, sprint-status row, commit, review, full gate, ff-merge.

## Dev Notes

- Reuse `profile_offer.read_offer` / `profile_publish.publish_state_of` rather than parsing paths manually.
- The offer path must not call `resolver.resolve_preset()`; the point is to avoid member-reachable resolve 422s and consume the already-published bundle hash.
- `not_computed` is distinct from existing preset-path `absent`: `absent` means a resolved preset had no estimate; `not_computed` means the selected published offer has no estimate for this STL yet and enqueue is explicitly out-of-scope.
- If process/material display context must be derived, derive from existing published offer sidecar/library metadata only; never from raw Orca bodies.

## Dev Agent Record

### Agent Model Used

Hermes/Laura controller using strict TDD, with Aider/OpenRouter diff review (`APPROVE`).

### Completion Notes List

- 2026-06-13 — Story 36.2 implemented on branch `feat/E36.2-member-estimate-by-offer-resolution`.
  - RED evidence: new 36.2 tests initially failed because `offer_id` was not accepted and FastAPI required preset fields (`6 failed`, all 422 instead of expected offer-path behavior).
  - GREEN evidence: 36.2 targeted offer-path tests passed (`9 passed`).
  - Adjacent verification: `tests/test_estimate_api.py`, `tests/test_member_profile_offers.py`, and slicer route-count guard passed (`52 passed`).
  - Lint/format: `ruff format --check` and `ruff check` passed on touched API files; `apps/web` `npm run typecheck` passed after mirroring the new DTO status/type.
  - Full closeout gate: `infra/scripts/check-all.sh` passed all 16 stages (`all green.`), log `.hermes/run-logs/check-all-20260613_222759-E36.2.log`.
  - Review: first Aider diff review requested changes for an unsafe `assert`; code now explicitly validates `published_bundle_hash` and returns 404 on malformed publish metadata. Follow-up Aider diff review returned `APPROVE`.
  - Scope held: no resolver call, no live Orca, no enqueue, no recompute mutation, no worker/arq/Alembic/DB change. Existing preset path remains backward-compatible when `offer_id` is absent.
  - Policy note: optional `spoolman_filament_ref` computes E35 policy context from the existing policy store only; it never changes the published bundle key.
  - External caveat: public-domain deploy verify may still fail if the existing `3d.ezop.ddns.net` TLS certificate remains expired; local runtime/API health is the reliable deploy smoke until cert renewal.

### File List

- `apps/api/app/modules/slicer/router.py`
- `apps/api/app/modules/slicer/schemas.py`
- `apps/api/tests/test_estimate_api.py`
- `apps/web/src/lib/api-types.ts`
- `_bmad-output/implementation-artifacts/36-2-member-estimate-by-offer-resolution.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-06-13 — story authored; status set to ready-for-dev.
- 2026-06-13 — implementation complete; status moved to review.
