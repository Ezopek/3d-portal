# E38 Decomposition Decision

**Date:** 2026-06-14  
**Status:** approved (batch/autonomous — operator intent distilled from 2026-06-14 conversation)  
**Source SCP:** `sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md` → E36/E37 done → E38 next.

---

## Trigger

Operator requested three capabilities as "the next slice" in a single coarse note captured as Story 38.1. BMAD correct-course pass requested to split into sensible story units before dev-story phase.

---

## Superseded artifact

`_bmad-output/implementation-artifacts/38-1-member-offer-request-estimate-cta.md` — original single-story capture. **Superseded by this decomposition.** That file now carries a `SUPERSEDED` header; do not pull work items from it.

---

## Scope confirmed for E38

Three operator-requested capabilities:

| # | Capability | Deferred-work ref |
|---|-----------|-------------------|
| A | Member offer request-estimate CTA (`G-ENQUEUE`) — when offer + STL returns `not_computed`, member can request/queue the estimate. | G-ENQUEUE in E36 SCP |
| B | Remove legacy `Quality`/preset select from model FilesTab member estimate surface. | none (UX debt from pre-offer era) |
| C | Admin offer freshness/resync — after a profile block is re-imported, affected published offers surface as stale + provide explicit republish/resync action. No silent automatic reslice. | `PROFILE-OFFER-SYNC-1` in `deferred-work.md` |

Also bundled into 38.1 (backend foundation):

| # | Capability | Deferred-work ref |
|---|-----------|-------------------|
| D | Admin profile-block delete guard — refuse deletion of blocks referenced by offers (409). | `PROFILE-LIB-GUARD-1` in `deferred-work.md` |

---

## Decomposition rationale

The original 38.1 blended three delivery axes (admin backend contract, admin FE, member FE) with different risk profiles and zero shared dependencies between admin and member threads. Keeping them as one story would:
- Force backend contract finalization before any FE starts.
- Couple SW-DEPLOY-1 risk (offer recompute triggers slicer worker) with a pure FE cleanup.
- Produce a story too large to review clearly.

### Chosen split: 4 stories

```
38.1  Admin offer sync-state foundation        [backend only]      independent
38.2  Admin offer stale badge + resync action  [frontend + admin]  requires 38.1 DTO
38.3  FilesTab offer-first UX cleanup          [frontend only]     independent
38.4  Member offer request-estimate CTA        [backend + FE]      prefers 38.3 done first
```

**Parallelism available:** 38.1 and 38.3 are fully orthogonal and can be developed concurrently. 38.2 requires the 38.1 `sync_state` DTO; 38.4 prefers 38.3's cleaned-up FilesTab surface but can proceed independently if needed.

**SW-DEPLOY-1 boundary:** only 38.4 touches `apps/api/app/modules/slicer/` in a way that enqueues to the slicer worker → only 38.4 deploy requires slicer-worker overlay rebuild. 38.1 is backend-only read-path addition; 38.2 and 38.3 are FE-only; none of them trigger SW-DEPLOY-1.

### Why not fewer stories?

- 38.1 + 38.2 cannot merge: the admin backend DTO contract must be reviewable independently of the FE implementation; bundling would make it hard to bisect a regression.
- 38.3 + 38.4 cannot merge: 38.3 is a pure FE cleanup with no backend risk; 38.4 adds a backend endpoint and carries SW-DEPLOY-1. Separating keeps deploy complexity contained.

### Why not more stories?

- PROFILE-LIB-GUARD-1 (block delete guard) is genuinely small (one pre-delete check + test) and is logically cohesive with the admin backend foundation work in 38.1. Splitting it out further would be ceremony.
- Fingerprint storage and `sync_state` derivation are one atomic backend design decision; splitting them across stories would leave an inconsistent backend state mid-sprint.

---

## Open questions (recorded, not blocking planning)

1. **Import-response affected-offers list (38.2):** Should `POST /api/admin/profiles/library` response include a list of affected published offers after a block upsert? Currently it returns a 200 with the block manifest only. Adding affected-offer metadata in the response avoids a second FE fetch for the post-import banner, but requires an additive envelope change. Default recommendation: add a `stale_offers` field (empty list when none) to the existing upsert response envelope without breaking the `ProfileLibraryBlock` contract. If operator prefers a separate `GET /api/admin/profiles/library/{block_id}/affected-offers` endpoint instead, update 38.2 accordingly before dev-story.

2. **Offer picker filter in 38.3:** After removing `CatalogEstimateProfileSelector`, the `PublishedOfferPicker` loses its legacy `material_class` filter. Default: list all member-safe published offers (no client-side material filter). If product later wants an offer-native material/category filter, that is a separate story.

3. **Post-recompute state in 38.4:** After a member clicks "Request estimate", the offer recompute backend returns an honest `EstimateView` (still `not_computed` for an absent record). Should the UI immediately refetch and show `queued`, or display an informational "request queued" state from the CTA response? Backend does NOT fabricate a `queued` record for an absent estimate. Recommendation: use `enqueued=true` from the CTA response to transition the UI to a local "queued" state until the next background refetch, without fabricating a server record. Defer the "backend writes a queued record for absent estimates" behavior to a future story if needed.

---

## Dependency graph

```
[38.1 admin sync-state backend] ──► [38.2 admin FE resync action]
                                           │
                                           └─ (both can be done in parallel with)

[38.3 FilesTab offer-first UX] ──► [38.4 member offer recompute CTA]
```

All four stories are in `epic-38: backlog`. No story in E38 depends on any story in a future epic.
