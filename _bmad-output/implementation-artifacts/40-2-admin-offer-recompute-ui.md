---
story: 40.2
title: Admin offer recompute UI as primary action
status: done
epic: 40
branch: feat/E40.2-admin-offer-recompute-ui
created: 2026-06-21
source_correct_course: _bmad-output/planning-artifacts/profile-offers-estimate-sot-correct-course-2026-06-19.md
depends_on:
  - 40.1-profile-offer-estimate-sot
scope: frontend story spec only — do not implement in this artifact pass
---

# Story 40.2 — Admin offer recompute UI as primary action

## Goal

Make the admin Profile Offers screen reflect the Epic 40 source-of-truth correction: profile offers, not `material_defaults`, drive slicer estimates. The primary admin recompute action must call the new offer-driven backend endpoint from Story 40.1, while legacy material-default/default-matrix controls move to an explicitly advanced/collapsed area with copy that explains they are optional per-spool/legacy overrides and are not required for offer estimates.

## Current code context

- `apps/web/src/modules/admin/ProfileOffersPage.tsx`
  - `BackfillSummary` already renders the counter shape returned by the legacy default-matrix backfill; Story 40.1 intentionally reused this response shape for offer recompute.
  - `ProfilePolicyPanel` is currently rendered near the top of `ProfileOffersPage`, collapsed by default, and owns:
    - `GET /api/admin/policy` gated on panel expansion via `useProfilePolicy(open)`;
    - material-default upsert/delete controls;
    - legacy `POST /api/admin/policy/default-matrix-backfill` inspect/run controls with dry-run + confirm.
  - There is no primary offer-driven recompute card/button yet.
  - Offer rows already expose stale republish/resync behavior; per-offer recompute can be added if it fits naturally, but should not replace the global current-offers action.
- `apps/web/src/modules/admin/hooks/useProfilePolicy.ts`
  - `useDefaultMatrixBackfill` posts to `/admin/policy/default-matrix-backfill`.
  - A new hook should post to `/admin/profiles/offers/recompute-estimates`.
- `apps/web/src/lib/api-types.ts`
  - `DefaultMatrixBackfillResponse` exists and can be reused/aliased for the response.
  - Add the request type for the new endpoint if missing: `{ dry_run?: boolean; visible_only?: boolean; offer_id?: string | null; max_cells?: number | null }`.
- Tests already cover the page and visual baselines:
  - `apps/web/src/modules/admin/ProfileOffersPage.test.tsx`
  - `apps/web/src/modules/admin/profile-offers-i18n.test.ts`
  - `apps/web/tests/visual/admin-profile-offers.spec.ts`
  - `apps/web/tests/visual/api-stubs.ts`

## Backend contract already available from Story 40.1

Endpoint: `POST /api/admin/profiles/offers/recompute-estimates`

Request defaults:

```json
{
  "dry_run": true,
  "visible_only": true,
  "offer_id": null,
  "max_cells": null
}
```

Response: same counters as `DefaultMatrixBackfillResponse`:

- `dry_run`
- `inspected`
- `cells_total`
- `cells_resolved`
- `cells_resolve_failed`
- `would_enqueue`
- `enqueued`
- `already_fresh`
- `missing_stl`
- `errors`

Important semantics:

- `visible_only=true` means current member-facing offers only.
- `offer_id` scopes recompute to one offer.
- `dry_run=true` inspects only; `dry_run=false` enqueues.
- `max_cells`, if supplied and exceeded, rejects before enqueue.
- Backend changes are out of scope unless the frontend type surface reveals a true contract mismatch.

## Acceptance Criteria

1. **Primary offer-driven recompute action exists above legacy policy controls.**
   - On `ProfileOffersPage`, the main estimate maintenance action is labeled in offer-first language, e.g. "Recompute estimates for all STL files (current offers)".
   - It is visually and structurally separate from material-default policy controls and appears before/above the advanced legacy panel.
   - It targets current offers by default: request body uses `dry_run: true` for inspection and `visible_only: true` unless the user explicitly confirms a real run.

2. **Main action calls the new endpoint, not the legacy matrix endpoint.**
   - Dry-run/inspect posts to `/api/admin/profiles/offers/recompute-estimates` with `dry_run: true`, `visible_only: true`, no `offer_id`.
   - Confirmed run posts to the same endpoint with `dry_run: false`, `visible_only: true`, no `offer_id`.
   - Existing legacy `POST /api/admin/policy/default-matrix-backfill` remains reachable only inside the advanced/legacy panel.

3. **Dry-run-first + explicit confirm flow is preserved.**
   - The primary action must let the admin inspect counters before enqueueing.
   - A real enqueue remains behind `ConfirmDialog` or an equivalent explicit confirmation.
   - Pending, error, and summary states are visible and do not silently fall through.

4. **Counters are rendered with existing summary semantics.**
   - Reuse `BackfillSummary` or a renamed generic summary component so the same counters are displayed consistently.
   - The UI copy should clarify `would_enqueue` is the dry-run estimate and `enqueued` is the confirmed-run result if this is not already clear from surrounding text.

5. **Advanced/legacy policy panel is demoted, not removed.**
   - `ProfilePolicyPanel` / material defaults / default-matrix backfill remain available but live under a clearly labeled Advanced/Legacy collapsed section.
   - Copy must state these controls are optional per-spool/legacy overrides and are **not required** for offer estimates.
   - The advanced panel should stay collapsed by default and should continue to gate `GET /api/admin/policy` until opened.
   - No `material_defaults`, `filament_overrides`, resolver, grid, or backend legacy code is deleted in this story.

6. **Per-offer scoped recompute is supported if natural and low-risk.**
   - If implemented, each offer row may expose a scoped recompute/inspect action that posts the new endpoint with `offer_id` and `visible_only` consistent with backend semantics.
   - It must still use dry-run-first + confirm for real enqueue.
   - It must not distract from or block the global current-offers recompute action.
   - If the row-level UI would require awkward state or broad churn, leave it out and record it as a follow-up; the story still passes on the global action.

7. **Translations and accessibility are complete.**
   - Add/adjust English and Polish i18n keys for the primary offer recompute action, confirm text, errors, summaries, and advanced/legacy explanatory copy.
   - Buttons have accessible names; status/error messages use existing accessible patterns (`role=alert` where appropriate).
   - State is not communicated by color alone.

8. **No member-facing behavior changes.**
   - Do not change FilesTab, member offer visibility/default behavior, or estimate selection in this story; those belong to 40.3.
   - Do not remove legacy grid/material-default code; removal/demotion beyond this admin panel belongs to 40.4.

9. **Small, reviewable diff.**
   - Prefer adding a focused `useOfferEstimateRecompute` hook/type over broad API-client refactors.
   - Prefer reusing existing `BackfillSummary`, `ConfirmDialog`, `Button`, and page layout primitives.
   - Avoid unrelated copy, styling, or route changes.

## Implementation Tasks

- [ ] Add frontend types for `OfferEstimateRecomputeRequest` and, if useful, `OfferEstimateRecomputeResponse` as an alias to `DefaultMatrixBackfillResponse`.
- [ ] Add a hook (likely under `apps/web/src/modules/admin/hooks/`) that posts to `/admin/profiles/offers/recompute-estimates`.
- [ ] Extract or rename `BackfillSummary` only as much as needed so it can describe offer recompute results without being semantically tied to policy/default-matrix copy.
- [ ] Add a primary offer-recompute card/section near the top of `ProfileOffersPage`:
  - inspect/dry-run button;
  - confirmed run button/dialog;
  - summary counters;
  - error state;
  - link to `/admin/queues` after enqueue remains appropriate.
- [ ] Keep request defaults explicit in the UI layer (`visible_only: true`; dry-run first).
- [ ] Move/relabel `ProfilePolicyPanel` into an Advanced/Legacy area with explanatory copy.
- [ ] Keep legacy backfill controls inside the advanced panel and ensure they still call `/admin/policy/default-matrix-backfill` only from there.
- [ ] Optionally add per-offer scoped recompute if it remains small; otherwise leave as follow-up.
- [ ] Update `en.json` and `pl.json` keys; update i18n coverage tests.
- [ ] Update component tests and visual stubs for the new endpoint and UI state.
- [ ] Update visual snapshots/baselines after classifying failures as expected stale baselines.

## Tests and Gates

### Unit/component tests (`apps/web`)

Add/update tests in `ProfileOffersPage.test.tsx` for:

- primary inspect posts to `/api/admin/profiles/offers/recompute-estimates` with `dry_run: true`, `visible_only: true`, and no `offer_id`;
- confirmed run posts to the same endpoint with `dry_run: false`, `visible_only: true`;
- summary counters render after dry-run and after confirmed run;
- endpoint errors surface visibly;
- advanced/legacy policy panel remains collapsed by default and still gates the policy fetch until opened;
- legacy default-matrix backfill is still available inside the advanced/legacy panel and still calls `/api/admin/policy/default-matrix-backfill`;
- if per-offer scoped recompute is implemented, assert `offer_id` is sent and dry-run-first still applies.

Update `profile-offers-i18n.test.ts` so every new key is present in both `en.json` and `pl.json`.

### Visual tests

Update `apps/web/tests/visual/admin-profile-offers.spec.ts` and `api-stubs.ts`:

- stub `POST **/api/admin/profiles/offers/recompute-estimates**` with deterministic counters;
- add or update baseline for the new primary offer-recompute card in the default offer-list view;
- update the expanded advanced/legacy panel baseline to reflect demoted copy and labeling;
- if a summary state is visually distinct, add a focused baseline for dry-run results only if it provides meaningful regression coverage.

Before regenerating snapshots, classify each visual diff per AGENTS.md visual-baseline triage: `stale-baseline`, `deterministic-fail`, or `flake-candidate`.

### Commands/gates

From `apps/web/` for this frontend story:

```bash
npm run lint -- --max-warnings=0
npm run typecheck
npm run test
npm run test:visual
```

Before merge/closeout per repo rules:

```bash
infra/scripts/check-all.sh
```

External review: routine diff review via Aider per current Laura rulebook (`laura-aider-review-diff`), unless the controller explicitly escalates.

## Safety / Non-goals

- No backend endpoint changes unless a true type/contract mismatch is discovered.
- No live mutation outside normal frontend test stubs.
- No destructive deletion of legacy policy, material-default, default-matrix, resolver, or grid code.
- No changes to member visible/default selection (`40.3`).
- No removal of legacy product grid/material-default code beyond admin-panel demotion (`40.4`).
- No raw Orca JSON, profile internals, secrets, or queue internals rendered in the UI.
- Real enqueue remains explicit-confirm only; dry-run is the first/default flow.

## Dependencies and Follow-ups

- Depends on 40.1 being present at HEAD: `POST /api/admin/profiles/offers/recompute-estimates` with the contract above.
- 40.3 will handle member-facing visibility filtering and default offer selection.
- 40.4 will handle broader legacy grid/material-default demotion/removal after 40.1–40.3 prove the offer-first path.
- Optional follow-up if skipped here: row-level per-offer recompute CTA with `offer_id` scope.


## Implementation Closeout — 2026-06-21

- Added the primary offer-driven estimate recompute panel on `ProfileOffersPage`.
- The inspect action posts `POST /api/admin/profiles/offers/recompute-estimates` with `dry_run: true` and `visible_only: true`.
- The confirmed run posts the same endpoint with `dry_run: false` and `visible_only: true` behind the existing confirmation dialog.
- Reused the existing backfill counter summary shape for dry-run/run results.
- Demoted material-default/default-matrix controls to a collapsed Advanced/Legacy panel, preserving lazy `GET /api/admin/policy` fetch and legacy backfill behavior.
- Updated API types, admin hook, English/Polish copy, component/i18n tests, visual stubs, and visual baselines.

### Verification evidence

- Aider story-spec review: `APPROVE`.
- Focused web gate: `npm run lint -- --max-warnings=0`, `npm run typecheck`, `npm run test -- ProfileOffersPage.test.tsx profile-offers-i18n.test.ts`, and `npm run test:visual -- tests/visual/admin-profile-offers.spec.ts` passed.
- Aider implementation review: `APPROVE`.
- Full closeout gate: `infra/scripts/check-all.sh` passed all 16 stages; evidence log in `.hermes/run-logs/check-all-E40.2-*`.

### Visual baseline classification

All updated `admin-profile-offers` snapshots are expected stale-baseline updates from the new offer recompute panel and Advanced/Legacy policy copy. No unrelated visual surface changed.
