# Story 36.1: Member-accessible published-offer list endpoint + safe DTO

Status: ready-for-dev

<!--
  Authored for PROFILE-PUBLISH-2 / Initiative 24 after BMAD correct-course planning.
  Source planning artifacts:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md
  - _bmad-output/planning-artifacts/prd.md § Initiative 24
  - _bmad-output/planning-artifacts/architecture.md § Initiative 24 / Decision AT
  - _bmad-output/planning-artifacts/epics.md § Initiative 24 / Epic E36

  Planning-only story. Implementation must happen on a story branch after explicit dev-go.
-->

## Story

As an **authenticated portal member**,
I want **to list the admin-published print profile offers that are safe and compatible for member display**,
so that **the later member offer picker can show human-readable profile choices without leaking Orca bundle/profile internals.**

This is the first backend slice of Epic E36 / PROFILE-PUBLISH-2. It is read-only over the existing published offer sidecars and does not change the admin offer API, the fixed-grid projection, resolver behavior, bundle store layout, estimate store, or slicer worker path. SW-DEPLOY-1 is **NOT** triggered.

## Acceptance Criteria

### Endpoint + auth

- **AC-1** Add member-accessible `GET /api/profiles/offers/published`.
- **AC-2** The endpoint is gated by `current_user` / authenticated-member access, **not** `current_admin`.
- **AC-3** Anonymous requests return 401.
- **AC-4** The route is not added to `_PUBLIC_ROUTES` and remains covered by the route-enforcement gate.
- **AC-5** The existing admin offer endpoints under `/api/admin/profiles/offers/*` remain unchanged.

### Published-only + compatibility filter

- **AC-6** The endpoint reads the existing offer store/listing and returns only offers whose publish state is published.
- **AC-7** Unpublished, draft, disabled, malformed, or unpublishable offers are omitted rather than partially exposed.
- **AC-8** Optional `?material=PLA` filters returned offers by `compatible_material_categories` using the same material-key normalization convention already used by profile/estimate policy code where applicable.
- **AC-9** Without `?material=...`, all published offers that are safe for member display are returned.

### Safe member DTO / leak fence

- **AC-10** The response DTO is purpose-built for members, tentatively `MemberPublishedOfferView`.
- **AC-11** Each item exposes only safe fields needed by the member picker:
  - `offer_id`
  - `portal_label`
  - `quality_tier`
  - `compatible_material_categories`
  - `printer_name`
- **AC-12** The serialized member response must not include `bundle_hash`, raw Orca profile ref names, profile-chain/block bodies, sidecar paths, sidecar internals, publish-state internals, or raw filesystem paths.
- **AC-13** A negative leak-fence test asserts the excluded field names/values do not appear in the serialized JSON.

### Deploy and scope boundaries

- **AC-14** No Alembic migration, DB table, worker function, arq queue, resolver mutation, or slicer-worker image change is introduced.
- **AC-15** No on-demand estimate enqueue is introduced in this story; that belongs to later G-ENQUEUE work if approved.
- **AC-16** The story is backend/API-only; no frontend offer picker is implemented here.

## Tasks / Subtasks

1. **(RED)** Add backend tests for the member published-offer endpoint before production code:
   - anonymous request returns 401;
   - authenticated member gets 200;
   - only published offers are returned;
   - `?material=...` filters by compatible material categories;
   - response JSON fails closed against internal fields (`bundle_hash`, raw Orca refs, chain bodies, sidecar paths/internals);
   - route-enforcement test remains green without adding the route to `_PUBLIC_ROUTES`.
2. **(GREEN)** Add the API route and DTO in the appropriate profile/offers module, reusing the existing offer store/listing functions instead of duplicating sidecar parsing.
3. Wire the router under `/api/profiles/offers/published` without changing admin routes.
4. **(VERIFY)** Run targeted pytest for the new tests and adjacent profile-offer tests; run ruff format/check on touched backend files.
5. Update this story's Dev Agent Record, sprint-status row, and commit on the story branch.

## Dev Notes

### Pre-enumeration / existing anchors

- Admin/profile offer primitives were shipped by E33 / PROFILE-OFFER-1 and PROFILE-PUBLISH-1. Reuse the existing profile-offer list/store code instead of re-reading sidecar files manually.
- Published offer state already carries `bundle_hash` internally, but this story must **not** expose it to members. Story 36.2 consumes it server-side for estimate-by-offer lookup.
- E35 `EstimateProfileSource` metadata is not directly returned by this list endpoint; it appears after selection in Story 36.2/36.3.

### Out of scope

- Estimate-by-offer lookup (`offer_id + stl_hash → EstimateView`) — Story 36.2.
- Member offer picker UI — Story 36.3 after G-UXGATE.
- On-demand estimate enqueue — deferred G-ENQUEUE.
- Admin offer CRUD/publish/unpublish changes — none.

### References

- SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md`.
- PRD: `_bmad-output/planning-artifacts/prd.md` § Initiative 24.
- Architecture: `_bmad-output/planning-artifacts/architecture.md` § Initiative 24 / Decision AT.
- Epics: `_bmad-output/planning-artifacts/epics.md` § Initiative 24 / Epic E36.

## Dev Agent Record

### Agent Model Used

_To be filled by the implementing dev-story agent._

### Completion Notes List

_To be filled during implementation._

### File List

_To be filled during implementation._

## Change Log

- 2026-06-13 — story authored; status set to ready-for-dev. Implementation not started.
