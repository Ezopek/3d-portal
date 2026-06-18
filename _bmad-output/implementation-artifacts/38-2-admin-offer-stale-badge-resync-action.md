# Story 38.2: Admin offer stale badge + resync action

Status: done

<!--
  Source: E38 decomposition decision (2026-06-14). Covers PROFILE-OFFER-SYNC-1 frontend half.
  Depends on: Story 38.1 (sync_state DTO + stale_offers in import response).
  Frontend-only for admin surfaces; reuses existing publish endpoint.
-->

## Story

As an **admin managing profile offers**, I want **stale offers to surface a visible badge and a one-click resync/republish action**, so that **I know which published offers no longer reflect the current profile library and can resync them explicitly — without surprises for members**.

## Context

Story 38.1 adds `sync_state` to the admin offer DTO and `stale_offers` to the block-upsert response. This story wires those signals into the admin UI:

1. A sync-state badge on each offer row in `ProfileOffersPage`.
2. A resync/republish action that triggers the existing `POST /api/admin/profiles/offers/{offer_id}/publish` endpoint.
3. A post-import notification on `ProfileLibraryPage` after a block upsert, listing affected published offers with a "Resync now / Later" choice.

No new backend endpoints are introduced. All resync actions must be **explicit operator choices**; nothing reslices automatically.

## Acceptance Criteria

### ProfileOffersPage — sync-state badge

- [x] Each offer row in the admin offer list (`ProfileOffersPage`) shows a `sync_state` badge:
  - `sync_state == "current"` → no badge or a subtle "current" indicator (design: keep the row uncluttered when everything is fine).
  - `sync_state == "stale"` → visible amber/warning badge labelled "Stale" (en) / "Nieaktualna" (pl).
  - `sync_state == "unknown"` (unpublished offers) → no badge (their publish_state badge already makes them visually distinct).
- [x] The badge is derived from the `sync_state` field returned by `GET /api/admin/profiles/offers`; no additional API call per row.
- [x] The existing `publish_state` and `validation_state` badges remain unchanged; `sync_state` is additive.

### ProfileOffersPage — resync action

- [x] A stale published offer row has an adjacent resync action (button or icon-button): "Republish" (en) / "Opublikuj ponownie" (pl).
- [x] Clicking republish calls the existing `POST /api/admin/profiles/offers/{offer_id}/publish` with the offer's current `published_stl_hash` (if the offer was published with a known STL hash) or prompts the operator to select an STL if `published_stl_hash` is absent.
- [x] On success: invalidate the admin offers query key; the offer row updates to `sync_state = "current"` after refetch.
- [x] On failure: show an honest inline error; do not silently swallow publish failures.
- [x] `invalid` offers must NOT show a resync action (the offer cannot be resync'd until the referenced block issue is resolved).
- [x] `unpublished` offers must NOT show a resync action from the stale path (they have their own publish flow).

### ProfileLibraryPage — post-import notification

- [x] After a successful block upsert (`POST /api/admin/profiles/library`), when the response `stale_offers` list is non-empty, show an inline notification/banner: "X published offer(s) now require republish: [offer labels]" with two choices:
  - **Republish now** — for each offer in `stale_offers`, call `POST /api/admin/profiles/offers/{offer_id}/publish` sequentially (or with bounded parallelism). Show per-offer success/failure inline.
  - **Later** — dismiss the notification. The stale badge will be visible on the offers page.
- [x] When `stale_offers` is empty, no notification is shown.
- [x] The notification is non-blocking (it does not prevent the operator from continuing to use the UI).
- [x] "Republish now" in the notification uses the same publish path as the offers-page resync action; no new endpoint.

### i18n

- [x] All new copy keys under `modules.admin.offers.*` and `modules.admin.library.*` in both `en.json` and `pl.json`.
- [x] Key naming consistent with existing admin i18n keys.

### Tests

- [x] `ProfileOffersPage` unit tests: stale badge renders for `sync_state == "stale"`; current renders no badge; invalid offer has no resync button; resync button calls publish mutation and invalidates query.
- [x] `ProfileLibraryPage` unit tests: post-import notification renders when `stale_offers` non-empty; "Republish now" calls publish for each offer; "Later" dismisses the notification without calling publish.
- [x] Focused vitest pass + `tsc -b` + `eslint --max-warnings=0` before merge.
- [x] Visual baselines updated for offer list with stale badge and resync button (4 Playwright projects).
- [x] Full `infra/scripts/check-all.sh` gate before merge.

## Likely files

### Frontend

- `apps/web/src/modules/admin/ProfileOffersPage.tsx` — sync-state badge, resync action
- `apps/web/src/modules/admin/ProfileOffersPage.test.tsx` (or adjacent)
- `apps/web/src/modules/admin/ProfileLibraryPage.tsx` — post-import notification
- `apps/web/src/modules/admin/ProfileLibraryPage.test.tsx` (or adjacent)
- `apps/web/src/modules/admin/hooks/` — mutation for republish, query invalidation
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/tests/visual/` — admin offer list baseline(s)

### No backend changes in this story (reuses 38.1 DTO + existing publish endpoint).

## Non-goals / scope fences

- Do not add a "bulk resync all stale offers" action in this story.
- Do not add a stale-offers indicator to member-facing pages.
- Do not change the publish endpoint behavior; it already handles the publish write.
- Do not introduce automatic background reslice.
- If `published_stl_hash` is absent for a stale offer, prompting for an STL is sufficient; do not auto-select one.

## Dependencies

- **Story 38.1 must be done** (or at minimum its DTO contract finalized) before this story's dev-story phase, so the `sync_state` field and `stale_offers` import response are available to the FE.
- Existing `POST /api/admin/profiles/offers/{offer_id}/publish` from E33 — no changes required.

## Change Log

- 2026-06-14 — created from E38 decomposition. Covers PROFILE-OFFER-SYNC-1 frontend half.
