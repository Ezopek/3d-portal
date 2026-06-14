# Story 38.4: Member offer request-estimate CTA

Status: backlog

<!--
  Source: E38 decomposition decision (2026-06-14). Supersedes the G-ENQUEUE / CTA half of the
  original 38-1 story. Refines its acceptance criteria into offer-mode-only scope.
  Prefers 38.3 (FilesTab offer-first UX) done first, but can proceed independently.
  Touches apps/api/**; SW-DEPLOY-1 applies on deploy.
-->

## Story

As a **member selecting a published profile offer for a model STL**, I want **to request an estimate when the selected offer + STL pair has not been computed yet**, so that **the offer-based pricing flow is complete without requiring operator backfill or manual queue work**.

## Context

Story 36.2 shipped offer-mode estimate read: `GET /api/estimates?stl_hash=...&offer_id=...` returns `{ status: "not_computed" }` when no estimate record exists for the (STL, published bundle) pair. The `G-ENQUEUE` path (letting the member trigger the enqueue) was explicitly deferred to E38.

The existing `POST /api/estimates/recompute` endpoint (EST-RECOMPUTE-1) accepts preset inputs (`material_class + quality_tier + printer_ref + stl_hash`). This story extends it to accept an offer-mode input (`stl_hash + offer_id`), which internally resolves the offer → published bundle → enqueues the by-hash re-slice using the same `enqueue_recompute` primitive.

This story prefers Story 38.3 (FilesTab offer-first UX) to be done first so the FE wiring lands in the cleaner FilesTab surface, but the backend extension and `EstimateDisplay` CTA changes are independent.

## Acceptance Criteria

### Backend — offer-mode recompute

- [ ] `POST /api/estimates/recompute` is extended to accept offer mode: when `offer_id` is present in the request body (alongside `stl_hash`), the endpoint routes to the offer-mode path.
- [ ] Offer-mode request body: `{ stl_hash: str, offer_id: str }`. The preset fields (`material_class`, `quality_tier`, `printer_ref`, `spoolman_filament_ref`) are **not required** and **not used** in offer mode; include them and they are ignored (or validate as mutually exclusive — record decision in implementation).
- [ ] Preset-mode recompute remains backward compatible: existing `{ stl_hash, material_class, quality_tier, printer_ref }` body continues to work unchanged.
- [ ] Offer-mode validates `stl_hash` via the existing `validate_content_hash` gate before any store/queue work.
- [ ] Offer-mode reads the offer sidecar; if the offer is not found or `publish_state != "published"`, returns 404 matching the offer read path (`GET /api/estimates` with invalid `offer_id`).
- [ ] Offer-mode derives `published_bundle_hash` from the offer sidecar (same as the 36.2 read path). No live Orca resolve.
- [ ] Offer-mode enqueues by `(stl_hash, published_bundle_hash)` using the existing `enqueue_recompute` helper — no new queue scheme, no new job type.
- [ ] If the estimate record is already `queued`, return `enqueued=false` (idempotent no-op — same R1 self-DoS guard as preset mode).
- [ ] For `absent` / `not_computed`, `stale`, and `failed` offer estimates: return `enqueued=true` with an honest `EstimateView` projection (the existing record state — do **not** fabricate a `queued` record or numbers).
- [ ] Response: `RecomputeResponse { enqueued: bool, estimate: EstimateView }` — same shape as preset mode. No `bundle_hash`, job id, queue name, Orca body, or filesystem path in the response.
- [ ] Auth + CSRF requirements remain at least as strict as the existing recompute endpoint. Not public.

### Frontend — EstimateDisplay offer recompute CTA

- [ ] `EstimateDisplay` renders a request-estimate CTA when `status == "not_computed"` **and** an offer recompute handler is provided via props. The CTA is not shown when no handler is wired (preserves backward compat for preset-mode surfaces that have no recompute handler in this path).
- [ ] CTA copy: "Request estimate" (en) / "Poproś o wycenę" (pl) — offer/request language, not "Quality" or legacy preset wording.
- [ ] Clicking the CTA calls the offer-mode recompute mutation, disables the button while in-flight (pending state), and re-enables on error.
- [ ] On success: invalidate the exact offer estimate query key (`["estimates", stlHash, { offerId }]`). The UI refetches; if the backend returns `enqueued=true` with the current honest state (still `not_computed`), the CTA transitions to a local "queued" state (non-interactive, copy: "Estimate requested" / "Wycena w kolejce") until the next background refetch brings a real `queued`/`fresh` record.
- [ ] `queued` offer estimates render as already in-flight and do not show a duplicate request CTA.
- [ ] Offer 404 / unavailable state remains honest (no silent fallback to preset mode) — existing 36.3 behavior.

### Frontend — hook

- [ ] New hook `useRecomputeOfferEstimate` (or extend `useRecomputeEstimate` with an offer-mode overload) takes `{ stlHash, offerId }` and posts to `POST /api/estimates/recompute` with the offer-mode body.
- [ ] Hook wires into `RowEstimatePanel` offer mode: when the expanded row is in offer mode and `status == "not_computed"`, pass the offer recompute handler to `EstimateDisplay`.

### FilesTab integration

- [ ] If 38.3 is done first: the recompute CTA lands in the already-cleaned-up FilesTab (standalone `PublishedOfferPicker` surface). No additional FilesTab changes needed beyond what 38.3 delivers.
- [ ] If implemented before 38.3: wire the CTA handler via `RowEstimatePanel` into the existing FilesTab offer mode surface; the quality-selector removal remains gated on 38.3.

### Tests

- [ ] Backend: offer-mode recompute — malformed hash (short-circuit), missing offer (404), unpublished offer (404), already-queued no-op (`enqueued=false`), `not_computed`/`absent` enqueue (`enqueued=true`, honest state), `stale` enqueue, `failed` enqueue, no-internal-leak response fence.
- [ ] Backend: preset-mode tests unaffected (regression check on existing `test_estimate_api.py` cases).
- [ ] Frontend: `useRecomputeOfferEstimate` — request body sends `{ stl_hash, offer_id }` to correct endpoint; query key invalidated on success.
- [ ] `EstimateDisplay` tests: `not_computed` with no handler → no CTA; `not_computed` with handler → CTA renders; click calls handler; `queued` state → no duplicate CTA.
- [ ] `RowEstimatePanel` / `FilesTab` tests: offer `not_computed` expanded row shows request-estimate CTA and calls the offer recompute mutation.
- [ ] Visual baseline updated for `not_computed` offer CTA state in the FilesTab expanded row.
- [ ] Full `infra/scripts/check-all.sh` gate before merge.

## Likely files

### Backend

- `apps/api/app/modules/slicer/schemas.py` — extend `RecomputeRequest` with optional `offer_id`; add offer-mode discriminator/validation
- `apps/api/app/modules/slicer/router.py` — offer-mode branch in `recompute_estimate`; offer sidecar read + `published_bundle_hash` derivation
- `apps/api/tests/test_estimate_api.py` — offer-mode recompute cases

### Frontend

- `apps/web/src/modules/estimates/hooks/useRecomputeEstimate.ts` or new `useRecomputeOfferEstimate.ts`
- `apps/web/src/modules/estimates/hooks/*.test.tsx`
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` — `not_computed` CTA
- `apps/web/src/modules/estimates/components/EstimateDisplay.test.tsx`
- `apps/web/src/modules/estimates/components/RowEstimatePanel.tsx` — wire handler in offer mode
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/tests/visual/__snapshots__/**`

## Non-goals / scope fences

- Do not remove backend preset estimate support globally.
- Do not remove admin profile quality tiers, profile import quality metadata, or the standalone `/estimates` debug surface.
- Do not expose raw Orca / profile internals to the member UI.
- Do not create bulk/unbounded recompute from member UI.
- Do not invent a new slicer queue path; reuse existing `enqueue_recompute` primitive.
- Do not auto-enqueue without a user action.
- Do not fabricate `queued` records server-side for absent estimates (backend returns honest state; FE handles local queued transition UI).

## Deploy notes

- `apps/api/app/modules/slicer/router.py` change enqueues to the slicer worker via arq queue → **SW-DEPLOY-1 applies**.
- Deploy requires slicer-worker overlay rebuild + in-container smoke (standard SW-DEPLOY-1 protocol from `docs/operations.md`).
- Normal app deploy otherwise.

## Open questions (not blocking story creation)

1. Should offer-mode and preset-mode request bodies be strictly mutually exclusive (validate that `offer_id` and preset fields are not both present), or silently ignore preset fields when `offer_id` is present? Recommendation: strict — if `offer_id` is present, preset fields must be absent; return 422 otherwise. Confirm before dev-story.
2. See E38 decomposition decision OQ-3 for the "backend writes queued record for absent estimates" question if product wants the refetch to immediately show `queued` rather than `not_computed`.

## Change Log

- 2026-06-14 — created from E38 decomposition. Refines and supersedes the G-ENQUEUE / CTA half of the original single `38-1-member-offer-request-estimate-cta.md` story. Backend ACs tightened; FilesTab ACs separated into 38.3.
