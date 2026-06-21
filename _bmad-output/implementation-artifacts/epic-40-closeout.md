---
epic: 40
status: done
created: 2026-06-21T15:36Z
updated: 2026-06-21T17:53Z
release: pending-40.4-deploy
---

# Epic 40 closeout — Profile Offer as estimate source of truth

## Outcome

Epic 40 now closes with one profile SoT only:

1. **40.1 — Offer-driven estimate recompute backend**: estimates recompute directly from Profile Offers and their `published_bundle_hash`.
2. **40.2 — Admin offer recompute UI**: Profile Offers exposes the recompute action as the admin operation.
3. **40.3 — Member visible/default offer selection**: member offer list returns only visible published offers and carries safe `is_default`.
4. **40.4 — Legacy profile systems removed**: old Profiles grid/import, profile policy, `material_defaults`, default-matrix backfill, and related UI/tests/scripts are removed from the repo.

## Operator gate

40.4 was initially deferred by assessment. The operator then explicitly decided that no legacy profile systems should remain. This closeout records that decision and the implementation that followed it.

## Final status

`epic-40: done`; `40-1`, `40-2`, `40-3`, and `40-4` are done. Final deploy/live smoke is tracked by controller gate evidence after merge.
