# Story 38.3: FilesTab offer-first UX cleanup

Status: ready-for-dev

<!--
  Source: E38 decomposition decision (2026-06-14). Supersedes the FilesTab UX half of the
  original 38-1 story.
  Pure frontend story; no backend changes. Independent of 38.1 and 38.2.
  Preferred predecessor to 38.4 (offer recompute CTA), but 38.4 can proceed independently.

  Spec revision 2026-06-14: addresses Aider review — hook API clarification, preset retention
  contract, EstimateChip/RowEstimatePanel non-modification, expanded test scope, visual
  baseline positioning, TypeScript flow, docs/comment updates.
-->

## Story

As a **member browsing a model's STL files**, I want **the estimate panel to show only the published profile offer picker** — without the legacy Material/Quality selector — so that **the pricing surface reflects how the shop actually works, and I am not confused by a quality dropdown that belongs to the old estimate system**.

## Context

`FilesTab` currently renders `CatalogEstimateProfileSelector` as the top-level estimate-mode wrapper. That component exposes a Material `<select>` and a Quality tier `<select>` (Aesthetic / Standard / Strong), with the `PublishedOfferPicker` as a child passed via the `children` slot (Story 36.4).

Both selects are leftovers from the pre-offer era. With E36 shipping the offer picker, the Material and Quality selects are dead UI for the member estimate surface.

The operator decision: remove `CatalogEstimateProfileSelector` and its two visible selects from the FilesTab member estimate bar. Keep a compact, standalone `PublishedOfferPicker` in its place. The offer picker must list **all** published offers — not filtered by a legacy preset material class.

This story does **not** touch the backend and does **not** add the recompute CTA (that is Story 38.4).

### Code-inspection findings (inform the implementation)

| Finding | Impact on implementation |
|---|---|
| `usePublishedOffers(material: string, ...)` — `material` is currently required | Must make optional; backend already supports omitted `?material` (returns all published offers; see `member_router.py` line 96 `if material is not None:`) |
| `EstimateChip` `preset: PrintIntentPresetInput` — required prop | Do NOT remove; pass frozen `defaultPreset` constant |
| `RowEstimatePanel` `preset: PrintIntentPresetInput` — required prop | Do NOT remove; pass frozen `defaultPreset` constant |
| `useQualityTierAvailability` + `canReadSelectedEstimate` in FilesTab — gate for preset-fallback 422 prevention (NFR21-NO-422-1) | RETAIN; this is load-bearing for the preset fallback path (no offer selected → chip uses `useEstimate` gated by `canReadSelectedEstimate`) |
| `selectedOfferId` is `string \| null` flowing into `offerId?: string \| null` props | Type-safe as-is; no TypeScript changes needed |
| `CatalogEstimateProfileSelector` renders `children` at line 174 | The `children` slot is how `PublishedOfferPicker` is currently embedded; removing the parent removes the slot |
| Backend endpoint `GET /profiles/offers/published?material=...` — `material` is optional (FastAPI `str \| None = None`) | Confirmed no backend change needed |

## Acceptance Criteria

### AC-1: Remove CatalogEstimateProfileSelector from FilesTab JSX

- [ ] `CatalogEstimateProfileSelector` is removed from `FilesTab.tsx` JSX. The Material `<select>` and Quality tier `<select>` (Aesthetic / Standard / Strong) are no longer rendered in the member FilesTab estimate bar.
- [ ] The `CatalogEstimateProfileSelector` import is removed from `FilesTab.tsx`.
- [ ] `CatalogEstimateProfileSelector` and `useQualityTierAvailability` are **not deleted globally** — they are used in standalone estimate surfaces outside the member catalog. Only their *usage* in `FilesTab` is changed (see AC-4 for what stays).

### AC-2: usePublishedOffers — make material parameter optional

- [ ] `usePublishedOffers` signature changes from `(material: string, options)` to `(material: string | undefined, options)`.
- [ ] When `material` is `undefined`, the hook omits the `?material` query param in the fetch URL (do not send `material=undefined` or `material=`). Use `if (material) { params.set("material", material); }` or equivalent guard before building the URL.
- [ ] The query key changes to `["member", "offers", "published", { material }]` — TanStack Query serializes `{ material: undefined }` as `{}` which is correctly distinct from `{ material: "pla" }`. No additional key shaping needed.
- [ ] All existing callers of `usePublishedOffers` that pass a material string continue to work unchanged (the parameter is now optional, not removed).

### AC-3: Standalone PublishedOfferPicker in FilesTab

- [ ] `FilesTab` calls `usePublishedOffers(undefined, { isAuthenticated: isAuthenticated === true, hasStlFiles: active === "stl" })` — no `material_class` argument, listing **all** published offers.
- [ ] `PublishedOfferPicker` is rendered directly in the FilesTab estimate bar (not as a child of `CatalogEstimateProfileSelector`) when `active === "stl" && stlFiles.length > 0 && isAuthenticated`.
- [ ] The standalone picker is wrapped in a minimal outer container `<div>` positioned at the same location in the FilesTab layout where `CatalogEstimateProfileSelector` was. The container must apply at minimum `flex items-center justify-end` styling so the picker remains right-aligned in the estimate bar area (match the existing visual rhythm). Exact class choices are at the dev agent's discretion but must pass visual sign-off (see AC-9).
- [ ] Props passed to `PublishedOfferPicker` are unchanged from the current `children`-slot call: `offers`, `selectedOfferId`, `onSelect`, `isLoading`, `isError`, `onRetry`, `isAuthenticated`.
- [ ] The `useEffect` that deselects `selectedOfferId` when the offer disappears from the published list (lines 104–108 of the current `FilesTab.tsx`) is **retained unchanged** — it guards against a selected offer being unpublished mid-session.

### AC-4: Internal preset state retained; quality availability gate preserved

These are explicitly NOT removed despite no longer driving visible UI, because they feed
load-bearing internal wiring.

- [ ] `const [preset, setPreset] = useState<PrintIntentPresetInput>(defaultPreset)` is replaced by `const preset = defaultPreset` — a frozen constant. `useState` and `setPreset` are removed; the constant is never mutated. Because `CatalogEstimateProfileSelector` is removed from `FilesTab` JSX in AC-1, there is no remaining `onChange={setPreset}` prop chain in FilesTab after this change.
- [ ] `useQualityTierAvailability` call is **retained** in `FilesTab` with `defaultPreset.material_class` as the material argument (since `preset` is now always `defaultPreset`, this is effectively a static call). This preserves the NFR21-NO-422-1 gate: `canReadSelectedEstimate` continues to gate `EstimateChip` and `RowEstimatePanel` when in preset-fallback mode (no offer selected).
- [ ] `catalogTierAvailability`, `selectedTierAvailability`, and `canReadSelectedEstimate` are retained and computed the same way as before. Only the `catalogTierAvailability` prop pass to `CatalogEstimateProfileSelector` is removed (since that component is removed from JSX).
- [ ] `EstimateChip` receives `preset={preset}` (the frozen constant) and `enabled={canReadSelectedEstimate}` unchanged. When `offerId` is set, the chip's internal `presetQuery` is disabled and `offerQuery` drives it — `preset` is still a required prop but does not affect the offer-mode estimate path.
- [ ] `RowEstimatePanel` receives `preset={preset}` (the frozen constant) and `enabled={canReadSelectedEstimate}` unchanged. Same dual-mode logic as `EstimateChip`.
- [ ] The import of `useQualityTierAvailability` remains in `FilesTab.tsx`.
- [ ] The imports of `defaultPreset`, `CATALOG_ESTIMATE_PRINTER_REF`, and `PrintIntentPresetInput` remain in `FilesTab.tsx`.

### AC-5: EstimateChip and RowEstimatePanel are NOT modified

- [ ] `EstimateChip.tsx` is **not changed**. The `preset: PrintIntentPresetInput` required prop, the `offerId?: string | null` optional prop, and all internal hook calls (`useEstimate` disabled when `offerId` provided, `useOfferEstimate` active when `offerId` provided) remain as shipped in Story 36.3.
- [ ] `RowEstimatePanel.tsx` is **not changed**. Same contract.
- [ ] These components already implement offer-mode correctly; the only wiring change is that the `preset` value passed from `FilesTab` is now always `defaultPreset` rather than a user-selected value.

### AC-6: Selected offer mode is the default visible surface; preset fallback is silent

- [ ] When `isAuthenticated === true` and `active === "stl" && stlFiles.length > 0`, the `PublishedOfferPicker` is the **only** visible estimate-selection control.
- [ ] When `selectedOfferId !== null`, chips and panels operate in offer mode (offer estimate, not preset estimate). When `selectedOfferId === null` (user selects "None" or no offer selected yet), chips/panels fall back to preset mode silently using `defaultPreset` — no visible preset selector is shown.
- [ ] When no published offers are available (empty list), `PublishedOfferPicker` renders nothing (existing AC-3 behavior from Story 36.3). The FilesTab shows no estimate-selection controls and chips/panels continue in preset-fallback mode.

### AC-7: No recompute CTA in this story

- [ ] `EstimateDisplay` `not_computed` state does **not** gain a request-estimate button in this story. That CTA is Story 38.4.
- [ ] `not_computed` renders its existing "estimate not yet available" display (Story 36.3 text, no interactive element).

### AC-8: Tests — usePublishedOffers

- [ ] `usePublishedOffers.test.tsx`: add a test `"omits material param when called with undefined"` — calls `usePublishedOffers(undefined, { isAuthenticated: true, hasStlFiles: true })` and asserts the fetch URL contains `/api/profiles/offers/published` with NO `material=` query param.
- [ ] The existing `"calls the correct endpoint with the material param when enabled"` test continues to pass (material still accepted when provided).
- [ ] The existing disabled-when-false tests continue to pass (call site changes to `undefined` but disable options are unchanged).

### AC-9: Tests — FilesTab

- [ ] `FilesTab.test.tsx`: add `installRouter` handler for `/profiles/offers/published` that returns `{ offers: [] }` (default empty, no picker rendered) so existing tests are not broken by the new fetch.
- [ ] Update the mock in tests that call `mockUseAuth.mockReturnValue(...)` to include `isAuthenticated: true` where the offer picker is the subject under test.
- [ ] Remove or rewrite tests that assert Material/Quality selects are present (these tests will fail after this story):
  - `"shows the member-visible estimate selector on the STL tab only"` — replace with: assert `PublishedOfferPicker` container IS rendered on the STL tab when `isAuthenticated: true`; assert it is NOT rendered when switching to the Source tab.
  - `"does not render the selector when there are no STL files"` — update: assert `CatalogEstimateProfileSelector` is NOT rendered (query by `getByLabelText(/material/i)` will no longer match — replace with a check that no material/quality label is in the DOM).
  - `"surfaces material + quality (Path B reversal) but NO pinned-filament/spool control"` — **remove** this test; the material/quality selectors are removed.
  - `"changing the estimate profile re-keys the estimate read to the chosen quality tier"` — **remove** (no visible selector to change).
  - `"disables unavailable tiers from backend availability before they can fire estimate reads"` — **remove** (no tier select).
  - `"does not fire an estimate read while a material switch lands on an unavailable target tier"` — **remove** (no material select).
  - `"non-admin does not see the Re-render button (but DOES see the estimate selector)"` — replace the `expect(screen.getByLabelText(/material/i)).toBeTruthy()` assertion with an assertion appropriate to the new surface (e.g., `expect(screen.queryByLabelText(/material/i)).toBeNull()` to confirm no material select; optionally assert the authenticated offer picker context is visible).
- [ ] Add a new test `"CatalogEstimateProfileSelector is not rendered in the member FilesTab"` — asserts `screen.queryByLabelText(/material/i)` and `screen.queryByLabelText(/quality/i)` are both `null` on the STL tab.
- [ ] Add a new test `"PublishedOfferPicker is rendered when offers are available"` — mocks `/profiles/offers/published` to return one offer, `mockUseAuth` with `isAuthenticated: true`, asserts the offer label appears and the picker `<select>` is present.
- [ ] Add a new test `"PublishedOfferPicker is not rendered on non-STL tabs"` — switch to Source tab, assert no offer picker `<select>` in DOM.
- [ ] Existing offer-mode chip and expanded-panel tests (if any exist from Story 36.3 coverage) continue to pass.

### AC-10: Visual baseline

- [ ] Visual baseline updated for the FilesTab estimate bar: Material + Quality selects are gone; the standalone `PublishedOfferPicker` appears at the right of the estimate bar area (or the bar is absent if no offers available).
- [ ] The dev agent must obtain operator visual sign-off before merging. Run `npm run test:visual` with `--update-snapshots` only after classifying the diff as `stale-baseline` (AGENTS.md § Visual baseline triage before regen).

### AC-11: Comments and docs cleanup

- [ ] The JSX comment block in `FilesTab.tsx` above the estimate selector (currently starting with `{/* EST-DISPLAY-1 (UX §A; product correction) — compact, member-visible estimate process / quality profile selector, visually subordinate to the STL list. ...`)` is updated to reflect the new offer-first surface (remove references to "quality profile selector", "Story 36.4: PublishedOfferPicker is passed as children so that the offer select appears as a third inline item").
- [ ] `PublishedOfferPicker.tsx` JSX doc comment says "Renders as a label + `<select>` flex item designed to sit inside `CatalogEstimateProfileSelector`'s children slot". Update this to reflect standalone usage (remove the reference to the children slot, note standalone as the primary FilesTab usage).
- [ ] No other docs/comments need updating in this story (global components and their standalone estimate/debug surfaces are out of scope).

### AC-12: Quality gates

- [ ] `tsc -b` clean (no new TypeScript errors).
- [ ] `npm run lint --max-warnings=0` clean.
- [ ] Focused `vitest` covering changed files green.
- [ ] Full `infra/scripts/check-all.sh` gate before merge.

## Likely files

### Modified

- `apps/web/src/modules/estimates/hooks/usePublishedOffers.ts` — make `material` optional; omit param from URL when undefined; queryKey unchanged (handles undefined naturally)
- `apps/web/src/modules/estimates/hooks/usePublishedOffers.test.tsx` — add undefined-material test
- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx` — primary change: remove `CatalogEstimateProfileSelector` JSX + import; freeze `preset` to constant; call `usePublishedOffers(undefined, ...)`;  wire standalone `PublishedOfferPicker`; update comment
- `apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx` — remove/rewrite selector tests; add offer-picker tests; add `installRouter` handler for offers endpoint
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.tsx` — minor JSX comment update (standalone usage note)
- `apps/web/tests/visual/` — FilesTab estimate bar baseline(s) updated

### NOT modified

- `apps/web/src/modules/estimates/components/EstimateChip.tsx`
- `apps/web/src/modules/estimates/components/RowEstimatePanel.tsx`
- `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx`
- `apps/web/src/modules/estimates/hooks/useQualityTierAvailability.ts`
- Any backend file

## Non-goals / scope fences

- Do not delete `CatalogEstimateProfileSelector` globally; it may still be used in standalone estimate debug/admin surfaces.
- Do not remove `useQualityTierAvailability` from `FilesTab` — it is the load-bearing 422 gate (NFR21-NO-422-1) for preset-fallback mode.
- Do not modify `EstimateChip` or `RowEstimatePanel` — they already handle both offer and preset modes.
- Do not add the offer recompute CTA (that is 38.4).
- Do not add an offer-native material/category filter in this story. All published offers are listed (no `material` arg to `usePublishedOffers`).
- Do not change the admin-facing estimate surfaces.
- Do not redesign the offer picker layout or add new UI elements to it.

## Deploy notes

- Frontend-only. No backend deployment required.
- SW-DEPLOY-1 **not triggered**.
- Snapshot baselines will change (Material + Quality selects removed). Run `npm run test:visual` and confirm the new baseline with the operator before merge.

## Change Log

- 2026-06-14 — created from E38 decomposition. Covers the FilesTab quality-selector removal half of the original single 38-1 story.
- 2026-06-14 — spec revised for implementation readiness (Aider review response):
  - CRITICAL: clarified `usePublishedOffers` material→optional (backend already supports; AC-2).
  - CRITICAL: clarified preset state → frozen constant; `useQualityTierAvailability` / `canReadSelectedEstimate` retained as internal 422 gate; `EstimateChip`/`RowEstimatePanel` `preset` prop preserved (AC-4, AC-5).
  - CRITICAL: STL hash-bearing estimate continuity confirmed — `preset` prop still passed to chips/panels; offer mode disables preset query internally.
  - IMPORTANT: added explicit EstimateChip/RowEstimatePanel non-modification AC (AC-5).
  - IMPORTANT: expanded test scope — new tests for offer picker, updated/removed selector tests, `installRouter` handler for offers endpoint (AC-8, AC-9).
  - IMPORTANT: standalone PublishedOfferPicker container/positioning spec (AC-3).
  - MINOR: docs/comment cleanup AC (AC-11).
  - MINOR: TypeScript flow note — confirmed `selectedOfferId: string | null` flows correctly; no additional TS work.
