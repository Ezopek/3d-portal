# Story 36.3: Member offer picker UI

Status: done

<!--
  Authored from G-UXGATE artifact 2026-06-14:
  _bmad-output/ux/ux-profile-publish-2-member-offer-picker-ux-2026-06-14.md
  Source initiative: PROFILE-PUBLISH-2 / Initiative 24 / Epic E36.
-->

## Story

As an **authenticated portal member**,
I want **to choose an admin-published print profile offer while viewing STL files**,
so that **I can see the estimate that corresponds to that published offer without exposing Orca internals or triggering new slicing work**.

## Acceptance Criteria

### Placement and mode switching

- **AC-1** Render a compact offer picker in the model `FilesTab` STL view, below `CatalogEstimateProfileSelector` and above the STL file list.
- **AC-2** The existing material selector drives the offer list filter via `GET /api/profiles/offers/published?material={material_class}`.
- **AC-3** The picker has a default **None / standard preset** option that preserves the existing preset-based estimate flow.
- **AC-4** Selecting an offer switches each STL row `EstimateChip` to `GET /api/estimates?offer_id=...&stl_hash=...`.
- **AC-5** Selecting an offer switches each expanded `RowEstimatePanel` to the same offer-based estimate read.
- **AC-6** Offer selection is ephemeral component state; it is not persisted across navigation.
- **AC-7** If the selected offer disappears after material change/refetch, clear the selection back to `None`.

### Auth, states, and honesty

- **AC-8** Anonymous/unknown auth does not cause redirects or side effects in the picker; shell `AuthGate` owns auth.
- **AC-9** Transport error fetching offers fails open: existing preset estimate flow remains usable and the picker shows retry.
- **AC-10** No compatible offers for a material renders no picker at all (absent, non-error state), matching the UX TL;DR.
- **AC-11** `not_computed` renders as a clear "not yet available" state, not as a generic error and not as zero grams.
- **AC-12** `unavailable_no_profile` remains honest and distinct from computed estimate states.
- **AC-13** Reuse existing `ProfileSourceBadge` semantics for exact/default profile context; default material estimates must not look exact.

### i18n, a11y, and scope boundaries

- **AC-14** Add PL/EN i18n parity under `modules.member.offers.*`.
- **AC-15** Use accessible native radio semantics (`fieldset`/`legend`/radio controls) for the picker.
- **AC-16** No inline hex/theme-token violations.
- **AC-17** Do **not** implement G-ENQUEUE: no request-estimate CTA, no on-demand slicing, no queue mutation.
- **AC-18** Do not expose backend internals such as bundle hashes in the member UI.

## Tasks / Subtasks

1. [x] **(RED)** Add failing frontend tests for published-offer hooks, offer-mode estimates, picker states/i18n, and honesty rendering.
2. [x] **(GREEN)** Add `usePublishedOffers` for the member offer list endpoint.
3. [x] **(GREEN)** Add `useOfferEstimate` for the `offer_id + stl_hash` read path.
4. [x] **(GREEN)** Add `PublishedOfferPicker` and wire it into `FilesTab` with ephemeral state and deselect-on-disappearance behavior.
5. [x] **(GREEN)** Extend `EstimateChip` and `RowEstimatePanel` to support offer mode without changing preset mode.
6. [x] **(GREEN)** Render `not_computed` honestly in chip/panel surfaces.
7. [x] **(GREEN)** Add PL/EN i18n keys and member offer DTO typings.
8. [x] **(VERIFY)** Run targeted Vitest tests plus web typecheck/lint/full test suite.

## Dev Notes

- UX SoT: `_bmad-output/ux/ux-profile-publish-2-member-offer-picker-ux-2026-06-14.md`.
- Backend prerequisites are Story 36.1 (`GET /api/profiles/offers/published`) and Story 36.2 (`GET /api/estimates?offer_id=...&stl_hash=...`).
- OD-2 from the UX artifact is preserved: the UI does not send `spoolman_filament_ref` in offer mode.
- G-ENQUEUE is explicitly deferred; this story is read-only from the member UI.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 via repo-local Claude Code for implementation; Laura/Hermes controller verification and one small controller fix for loading/error render order.

### Completion Notes List

- 2026-06-14 — Implemented on branch `feat/E36.3-member-offer-picker-ui`.
- RED evidence: targeted Vitest initially failed after tests were authored because implementation was missing; intermediate run after implementation also exposed test matcher convention mismatch (`toBeInTheDocument` unsupported in this repo) before tests were adjusted to project style.
- GREEN targeted evidence: `npm run test -- --reporter=verbose --run src/modules/estimates/hooks/usePublishedOffers.test.tsx src/modules/estimates/hooks/useOfferEstimate.test.tsx src/modules/estimates/components/PublishedOfferPicker.test.tsx src/modules/estimates/components/OfferEstimateHonesty.test.tsx src/modules/estimates/components/EstimateChip.test.tsx` → **5 files / 31 tests passed**.
- Web gate evidence: `npm run typecheck` passed; `npm run lint -- --max-warnings=0` passed; `npm run test` passed **126 files / 653 tests**.
- Full closeout gate evidence: `.hermes/run-logs/check-all-20260614_005605-E36.3.log` — `infra/scripts/check-all.sh` passed **16/16**, including visual regression **472 passed / 24 skipped**.
- Scope held: no backend changes, no G-ENQUEUE, no on-demand slicing, no queue mutation, no `spoolman_filament_ref` sent by offer mode.

### File List

- `apps/web/src/lib/api-types.ts`
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`
- `apps/web/src/modules/estimates/components/EstimateChip.tsx`
- `apps/web/src/modules/estimates/components/EstimateChip.test.tsx`
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx`
- `apps/web/src/modules/estimates/components/OfferEstimateHonesty.test.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.test.tsx`
- `apps/web/src/modules/estimates/components/RowEstimatePanel.tsx`
- `apps/web/src/modules/estimates/hooks/useOfferEstimate.ts`
- `apps/web/src/modules/estimates/hooks/useOfferEstimate.test.tsx`
- `apps/web/src/modules/estimates/hooks/usePublishedOffers.ts`
- `apps/web/src/modules/estimates/hooks/usePublishedOffers.test.tsx`

## Change Log

- 2026-06-14 — Story created and implemented from G-UXGATE; status `done` external review/full closeout gate complete.
- 2026-06-14 — Controller refinement: made loading/no-offers states visually absent to preserve fail-open behavior and avoid baseline ripple when no compatible offers exist.
- 2026-06-14 — Aider diff review returned `APPROVE`.
