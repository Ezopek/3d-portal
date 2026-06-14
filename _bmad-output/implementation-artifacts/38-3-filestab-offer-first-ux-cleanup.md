# Story 38.3: FilesTab offer-first UX cleanup

Status: backlog

<!--
  Source: E38 decomposition decision (2026-06-14). Supersedes the FilesTab UX half of the
  original 38-1 story.
  Pure frontend story; no backend changes. Independent of 38.1 and 38.2.
  Preferred predecessor to 38.4 (offer recompute CTA), but 38.4 can proceed independently.
-->

## Story

As a **member browsing a model's STL files**, I want **the estimate panel to show only the published profile offer picker** — without the legacy Material/Quality selector — so that **the pricing surface reflects how the shop actually works, and I am not confused by a quality dropdown that belongs to the old estimate system**.

## Context

`FilesTab` currently renders `CatalogEstimateProfileSelector` as the top-level estimate-mode wrapper. That component contains both a Quality tier select (`aesthetic` / `standard` / `strong`) and the `PublishedOfferPicker` as a child. The quality select is a leftover from the pre-offer era; with E36 shipping the offer picker, the quality tier row is dead UI for the member estimate surface.

The operator decision: remove `CatalogEstimateProfileSelector` and the visible quality select from the FilesTab member estimate bar. Keep a compact, standalone `PublishedOfferPicker` in its place. The offer picker must not depend on `preset.material_class` to filter offers in this surface.

This story does **not** touch the backend and does **not** add the recompute CTA (that is Story 38.4).

## Acceptance Criteria

### Remove quality selector from FilesTab member surface

- [ ] `CatalogEstimateProfileSelector` is removed from `FilesTab.tsx`. The quality tier select (Aesthetic / Standard / Strong) is no longer rendered in the member FilesTab estimate bar.
- [ ] The `preset` state, `useQualityTierAvailability`, and `setPreset` wiring that fed `CatalogEstimateProfileSelector` are removed from `FilesTab` if they are no longer needed. Any remaining offer-specific state is kept; preset-only state is cleaned up.
- [ ] `CatalogEstimateProfileSelector` and `useQualityTierAvailability` are not deleted globally — they may still be used in standalone estimate surfaces outside the member catalog. Only their usage in `FilesTab` is removed.

### Standalone PublishedOfferPicker in FilesTab

- [ ] A compact `PublishedOfferPicker` is rendered directly in the FilesTab estimate bar in place of `CatalogEstimateProfileSelector`.
- [ ] The offer picker calls `usePublishedOffers()` with no `material_class` filter (or with a nullable/undefined filter) so it lists **all member-safe published offers** — not filtered by a legacy preset material class.
- [ ] The offer picker wiring in the STL row (expanded panel via `RowEstimatePanel`, chip via `EstimateChip`) uses the same offer selection state as before (Story 36.3 `selectedOfferId` / `onSelectOffer` props). No new props are added; only the container changes.
- [ ] Selected offer mode is the exclusive estimate surface when a published offer exists. No fallback to preset mode in the FilesTab member view.
- [ ] When no published offers are available (empty list), the FilesTab renders the existing empty/unavailable state from Story 36.3 rather than falling back to the quality selector.

### No recompute CTA in this story

- [ ] `EstimateDisplay` `not_computed` state does **not** gain a request-estimate button in this story. That CTA is Story 38.4.
- [ ] `not_computed` renders its existing "estimate not yet available" display (Story 36.3 text, no interactive element).

### Tests + visual

- [ ] `FilesTab.test.tsx`: quality select is NOT rendered in the member STL FilesTab; `CatalogEstimateProfileSelector` is NOT rendered; `PublishedOfferPicker` IS rendered and receives offers.
- [ ] Existing FilesTab offer-mode chip and expanded-panel tests continue to pass (offer selection → estimate display).
- [ ] Visual baseline updated for the FilesTab estimate bar (quality select row gone, offer picker at same or equivalent position).
- [ ] `tsc -b` + `eslint --max-warnings=0` + focused vitest before merge.
- [ ] Full `infra/scripts/check-all.sh` gate before merge.

## Likely files

### Frontend

- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx` — primary change; remove `CatalogEstimateProfileSelector`, wire standalone `PublishedOfferPicker`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.tsx` — possibly minor prop adjustments if it relied on a parent `material_class` prop
- `apps/web/src/modules/estimates/hooks/usePublishedOffers.ts` — check/update if `material_class` is currently required
- `apps/web/tests/visual/` — FilesTab estimate bar baseline(s)

### No backend changes.

## Non-goals / scope fences

- Do not delete `CatalogEstimateProfileSelector` globally; it may still be used elsewhere (standalone estimate debug/admin surface).
- Do not add the offer recompute CTA (that is 38.4).
- Do not add preset/quality mode to the member FilesTab; this story removes it, not replaces it with another preset selector.
- Do not add an offer-native material/category filter in this story. All published offers are listed.
- Do not change the admin-facing estimate surfaces.

## Deploy notes

- Frontend-only. No backend deployment required.
- SW-DEPLOY-1 **not triggered**.
- Snapshot baselines will change (quality select row removed). Run `npm run test:visual` and confirm the new baseline with the operator before merge.

## Change Log

- 2026-06-14 — created from E38 decomposition. Covers the FilesTab quality-selector removal half of the original single 38-1 story.
