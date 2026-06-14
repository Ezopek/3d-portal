# Story 38.1: Member offer estimate CTA + remove legacy FilesTab quality selector

> **SUPERSEDED — 2026-06-14**
> This story was too coarse. It has been split into four focused stories by the E38 decomposition
> pass. Do not pull work items from this file.
>
> Superseded by:
> - **38.1** `38-1-admin-offer-sync-state-foundation.md` — admin backend: chain fingerprint + sync_state DTO + PROFILE-LIB-GUARD-1
> - **38.2** `38-2-admin-offer-stale-badge-resync-action.md` — admin FE: stale badge + resync action
> - **38.3** `38-3-filestab-offer-first-ux-cleanup.md` — FilesTab offer-first UX (remove quality selector)
> - **38.4** `38-4-member-offer-request-estimate-cta.md` — member offer request-estimate CTA (G-ENQUEUE)
>
> Planning decision: `_bmad-output/planning-artifacts/_runtime/e38-decomposition-decision.md`

Status: superseded

<!--
  Source: operator decision 2026-06-14 — "następny slice to musi być G-ENQUEUE / request-estimate CTA oraz ukrycie/wywalenie starego selecta Jakość/Quality - bo to pozostałość po starym systemie wyceń".
  Backlog/story capture only. Not implemented until explicit dev-go.
-->

## Story

As a **member selecting a published profile offer for a model STL**,
I want **to request an estimate when the selected offer/STL pair is not computed yet**,
so that **the offer-based pricing flow is complete without exposing the old preset/quality selector or requiring operator backfill/manual queue work**.

## Product decision

The member FilesTab should treat **published profile offers** as the primary estimate-selection surface.
The old FilesTab `Quality` / preset selector is legacy UI from the pre-offer estimate system and should be removed or hidden from the member catalog FilesTab for this slice.

This does **not** delete backend preset support, admin profile quality tiers, profile import quality metadata, or the standalone `/estimates` debug/MVP surface unless a later story explicitly deprecates them. The scope is the model FilesTab member experience.

## Current-state note

Already shipped building blocks:

- Offer read path: `GET /api/estimates?stl_hash=...&offer_id=...` returns the selected published offer's estimate or `status == "not_computed"` when no estimate record exists.
- Preset recompute path: `POST /api/estimates/recompute` exists for preset inputs (`stl_hash + material_class + quality_tier + printer_ref [+ spoolman_filament_ref]`) and enqueues an idempotent by-hash re-slice.
- UI display: `EstimateDisplay` already renders a recompute CTA for preset `absent`/`stale`/`failed` when an `onRecompute` handler is provided.
- FilesTab offer mode: `PublishedOfferPicker` is currently nested as a child of `CatalogEstimateProfileSelector`, so the offer picker is visually coupled to the legacy Material/Quality bar.

Current gap:

- Offer mode is read-only; `not_computed` has no request-estimate CTA.
- The old `Quality` select remains visible in FilesTab even when published offers are the intended model/STL pricing path.

## Acceptance Criteria

### Backend / API

- [ ] Extend the guarded recompute endpoint to support offer mode, either by extending `POST /api/estimates/recompute` or adding an equivalent narrow route.
- [ ] Offer-mode recompute input requires exactly `stl_hash + offer_id` and does **not** require `material_class`, `quality_tier`, or `printer_ref` from the member UI.
- [ ] Preset-mode recompute remains backward compatible for existing standalone estimate surfaces/tests.
- [ ] Offer-mode recompute validates `stl_hash` before any store/queue work.
- [ ] Offer-mode recompute validates `offer_id` as a published offer and requires a valid `published_bundle_hash`; missing/malformed/unpublished offers return 404, matching the offer read path.
- [ ] Offer-mode recompute enqueues by `(stl_hash, published_bundle_hash)` using the existing idempotent `enqueue_recompute` helper; do not create a new queue/job-id scheme.
- [ ] If the estimate record is already `queued`, return `enqueued=false` and do not enqueue a duplicate.
- [ ] For absent/`not_computed`, stale, and failed offer estimates, return `enqueued=true` with an honest `EstimateView` projection; do not fabricate numbers.
- [ ] Response remains UI-safe: no `bundle_hash`, job id, queue name, Orca body, filesystem path, or raw profile chain.
- [ ] Auth/CSRF requirements remain at least as strict as the existing recompute endpoint; the route is not public.

### Frontend / FilesTab UX

- [ ] Remove/hide `CatalogEstimateProfileSelector` and the visible `Quality` select from the model FilesTab member estimate bar.
- [ ] Keep a compact `PublishedOfferPicker`/offer selection surface in the FilesTab STL view.
- [ ] The offer picker should no longer depend on changing a legacy `preset.material_class` control in this surface. Prefer listing all member-safe published offers, or introduce an offer-native filter only if product copy/UX requires it.
- [ ] Offer mode remains the path used by `EstimateChip` and `RowEstimatePanel` when an offer is selected.
- [ ] `EstimateDisplay` renders a request-estimate CTA for `status == "not_computed"` when an offer recompute handler is wired.
- [ ] Clicking the CTA calls the offer-mode recompute mutation, disables/pending-states the button while in flight, and invalidates the exact offer estimate query key (`["estimates", stlHash, { offerId }]`) on success.
- [ ] `queued` offer estimates render as already in-flight and do not show a duplicate request button.
- [ ] Offer 404/unavailable state remains honest and retryable; it must not silently fall back to preset mode.
- [ ] i18n copy uses offer/request language (e.g. "Request estimate" / "Poproś o wycenę") rather than legacy "Quality" wording.

### Tests / gates

- [ ] Backend tests cover offer-mode recompute: malformed hash, missing/unpublished offer, already queued no-op, absent/not_computed enqueue, stale/fresh/failed behavior as appropriate, and response leak fence.
- [ ] Frontend hook tests cover the offer recompute request body/endpoint and query invalidation.
- [ ] `EstimateDisplay` tests cover `not_computed` with and without a wired request handler.
- [ ] FilesTab tests verify the old Quality select is not rendered in the member STL FilesTab, while offer picker remains available.
- [ ] FilesTab tests verify request-estimate CTA appears for selected-offer `not_computed` expanded row and calls the offer recompute mutation.
- [ ] Visual baseline updated for the FilesTab estimate bar change and `not_computed` request CTA state.
- [ ] Full closeout gate required before merge: `infra/scripts/check-all.sh` all green.
- [ ] Deploy requires normal app deploy plus slicer-worker overlay behavior if `apps/api/**` changes trigger it; runtime smoke must include `/api/health` and at least one offer-mode recompute/request dry or fake-safe verification where feasible.

## Likely files

### Backend

- `apps/api/app/modules/slicer/schemas.py`
- `apps/api/app/modules/slicer/router.py`
- `apps/api/tests/test_estimate_api.py`

### Frontend

- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx`
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx`
- `apps/web/src/modules/estimates/components/EstimateDisplay.test.tsx`
- `apps/web/src/modules/estimates/components/RowEstimatePanel.tsx`
- `apps/web/src/modules/estimates/components/EstimateChip.tsx` only if offer mode state handling changes
- `apps/web/src/modules/estimates/hooks/useOfferEstimate.ts`
- `apps/web/src/modules/estimates/hooks/useRecomputeEstimate.ts` or new `useRecomputeOfferEstimate.ts`
- `apps/web/src/modules/estimates/hooks/*.test.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.tsx` if all-offer/no-material-filter behavior needs UI adjustment
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/tests/visual/__snapshots__/**`

## Non-goals / scope fences

- Do not remove backend preset estimate support globally in this story.
- Do not remove admin profile quality tiers or profile import quality metadata.
- Do not expose raw Orca/profile internals to the member UI.
- Do not create bulk/unbounded recompute from member UI.
- Do not invent a new slicer queue path; reuse existing recompute enqueue primitives.
- Do not silently enqueue without a user action in the member UI; existing bounded backfill hooks remain separate.

## Open questions for story author

1. Should FilesTab offer picker list **all published offers** by default, or keep an offer-native category/material filter that is not the old Quality selector?
2. Should the collapsed chip for `not_computed` remain an em dash only, or indicate that the expanded panel can request an estimate?
3. Should successful request immediately refetch and show `queued` if no estimate record existed, or is `not_computed` acceptable until the worker writes a record? Backend currently does not fabricate absent queued records; changing that would be a product/API decision.
4. Should admins still see the old preset selector somewhere for diagnostics, or is the standalone `/estimates` surface enough?

## Suggested implementation approach

1. Start backend TDD: offer-mode recompute request contract and idempotent enqueue behavior.
2. Implement minimal backend extension while preserving preset-mode tests.
3. Add frontend offer recompute hook and query invalidation.
4. Extend `EstimateDisplay` so `not_computed` can render a request CTA when a handler is present.
5. Refactor FilesTab: separate PublishedOfferPicker from CatalogEstimateProfileSelector; hide/remove Quality selector in member FilesTab.
6. Wire `RowEstimatePanel` offer mode to the offer recompute handler.
7. Update i18n and tests.
8. Run targeted tests, Aider review, full gate, visual baseline review, merge/deploy.

## Notes / risks

- This story touches `apps/api/**`, so deploy may trigger the slicer-worker overlay path. Closeout must respect the existing SW-DEPLOY-1 guardrails.
- Removing the Quality selector changes snapshot baselines and may affect shared catalog/detail/share visual tests.
- The old selector encoded material filtering for offers. Removing it means the offer list source/filter contract must be consciously updated, not accidentally left dependent on default PLA.
- If absent offer recompute returns `not_computed` immediately after enqueue, the UI copy must say "request queued" without promising immediate numbers.

## Change Log

- 2026-06-14 — captured from operator decision; status `backlog`.
