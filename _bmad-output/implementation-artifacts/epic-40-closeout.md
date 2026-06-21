---
epic: 40
status: done
created: 2026-06-21T15:36Z
updated: 2026-06-21T15:36Z
release: 0.1.0+f66c0ed
---

# Epic 40 closeout — Profile Offer as estimate source of truth

## Outcome

Epic 40 is closed with the safe product correction complete:

1. **40.1 — Offer-driven estimate recompute backend**: `POST /api/admin/profiles/offers/recompute-estimates` recomputes estimates directly from Profile Offers and no longer depends on `material_defaults`.
2. **40.2 — Admin offer recompute UI**: Profile Offers page makes offer-driven recompute the primary admin action; legacy policy/default-matrix controls are Advanced/Legacy.
3. **40.3 — Member visible/default offer selection**: member published-offer list now returns only `visibility == visible` offers and carries safe `is_default`; `FilesTab` starts on the operator default visible offer.

## Deferred gated scope

`40-4-demote-legacy-profile-grid` remains backlog/deferred by design. Assessment artifact:

- `_bmad-output/implementation-artifacts/40-4-demote-legacy-profile-grid-assessment.md`

Rationale: legacy `material_defaults` and intent-grid code still back valid admin/internal operations and tests. Removal requires a future explicit operator gate and staged, non-destructive refactor.

## Verification

- Story 40.3 targeted API: `17 passed` in `apps/api/tests/test_member_profile_offers.py`.
- Story 40.3 targeted web: `43 passed` across `FilesTab`, `usePublishedOffers`, `PublishedOfferPicker` tests.
- Aider diff review: `APPROVE`.
- Full gate: `.hermes/run-logs/check-all-E40.3-20260621T152359Z.log` — `passed: 16`, `all green`.
- Push lean gate: `11 passed`.
- Deploy: `infra/scripts/deploy.sh` completed; release `0.1.0+f66c0ed`.
- Deploy smoke: `SLICER_WORKER_SMOKE_OK`, GlitchTip symbolication OK, runbook fingerprint OK.
- Live route smoke on `.190`: `/` HTTP 200; unauth `/api/profiles/offers/published` HTTP 401 `missing_access`.
- Live web bundle contains release `0.1.0+f66c0ed`, `/profiles/offers/published`, and `is_default`.

## Final status

`epic-40: done`; `40-4-demote-legacy-profile-grid` stays backlog/deferred/gated, not silently removed.
