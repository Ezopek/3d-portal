# Story 38.1: Admin offer sync-state foundation

Status: backlog

<!--
  Source: E38 decomposition decision (2026-06-14). Supersedes the single-story 38-1 capture.
  Covers: PROFILE-OFFER-SYNC-1 backend half + PROFILE-LIB-GUARD-1 from deferred-work.md.
  Backend-only story; no frontend changes.
-->

## Story

As an **admin**, I want **published offers to carry a sync state that tells me whether the underlying profile blocks have changed since last publish**, so that **I can see at a glance whether a published offer still reflects the current profile library, without silently serving stale configurations to members**.

## Context

Story 36.3 shipped the member-facing offer picker; E37 shipped FilesTab file delete. Published offers reference profile blocks via a chain (`machine_block_id`, `process_block_id`, `filament_block_id`). Re-importing a block with the same `(profile_type, name)` is an atomic upsert that keeps the `block_id` stable, so existing offer sidecars still reference the same IDs — but their content has changed. Today there is no fingerprint stored at publish time, so the API cannot tell whether the offer reflects the current blocks without re-running full Orca resolve.

Additionally, `DELETE /api/admin/profiles/library/{block_id}` currently succeeds even when the block is referenced by published offers, marking those offers `invalid unknown_block` at next read time. A guard is needed.

This story delivers the **backend-only foundation** (fingerprint + DTO + delete guard) that Story 38.2 builds its FE surface on.

## Acceptance Criteria

### Chain fingerprint at publish time

- [ ] At `POST /api/admin/profiles/offers/{offer_id}/publish` time, the server derives a `published_chain_fingerprint` from the chain's current block manifests: for each slot in the chain (`machine_block_id`, `process_block_id`, `filament_block_id`), read the block's curated manifest and extract its `imported_at` field; concatenate in a deterministic order (machine + process + filament); SHA-256 the concatenation → 64-char hex string stored as `published_chain_fingerprint` in the offer sidecar.
- [ ] If any referenced block manifest is unreadable at publish time, the publish call fails (the chain is already `invalid` at that point — this is the existing `invalid unknown_block` path).
- [ ] Existing offers without `published_chain_fingerprint` (published before this story) read as `sync_state="stale"` (conservative fail-open: no fingerprint = we cannot confirm currency).
- [ ] No re-derive at list/get time calls Orca or writes to the bundle/estimate store.

### `sync_state` projection in offer DTO

- [ ] `PrintProfileOffer` gains a derived (non-persisted) field `sync_state: OfferSyncState` where `OfferSyncState = Literal["current", "stale", "unknown"]`.
- [ ] `sync_state` derivation at read time:
  - `invalid` offer (existing `validation_state` field) → `sync_state` irrelevant; include as `"unknown"` or omit (the `invalid` badge dominates the UI).
  - `unpublished` offer → `sync_state = "unknown"` (not published, no published fingerprint to compare).
  - `published` + no `published_chain_fingerprint` in sidecar → `sync_state = "stale"` (backward compat for pre-38.1 publishes).
  - `published` + `published_chain_fingerprint` present → re-derive the current chain fingerprint (same `imported_at` approach) → if equal: `sync_state = "current"`; if different: `sync_state = "stale"`; if any block now missing → `validation_state = "invalid"` wins.
- [ ] `sync_state` derivation must NOT break existing offer list performance: it reads at most 3 small manifest JSON files per offer. The offer list endpoint already validates each offer's chain (AC-10 revalidation contract); fingerprint check piggybacks on the same manifest reads.
- [ ] `PrintProfileOffer` admin DTO exposed through `GET /api/admin/profiles/offers` and `GET /api/admin/profiles/offers/{offer_id}` — both include `sync_state`.
- [ ] Member-facing `GET /api/profiles/offers/published` DTO (E36 Story 36.1) does NOT expose `sync_state` — it is admin-only metadata. Keep the member DTO lean.

### Block delete guard (PROFILE-LIB-GUARD-1)

- [ ] `DELETE /api/admin/profiles/library/{block_id}`: before deletion, call a new pure helper `profile_offer.offers_referencing_block(root, block_id) -> list[dict]` that iterates `list_offers(root)` and checks each sidecar's `chain` values for the given `block_id`.
- [ ] If any offers reference the block, return **HTTP 409** `detail="profile_block_in_use"` with a structured, leak-fenced body: `{ "offers": [{ "offer_id": ..., "label": ..., "publish_state": ... }] }` — no raw Orca body, no filesystem path, no `published_bundle_hash`.
- [ ] On a 409, no block files are deleted and no `slicer_profile.library_delete` audit event is emitted.
- [ ] Non-referenced block delete keeps existing semantics: 204 on first delete, 404 on re-delete, `slicer_profile.library_delete` audit emitted.
- [ ] Existing read-time `invalid unknown_block` behavior is preserved as a resilience fallback for out-of-band filesystem deletion; do not remove that test/contract.

### Import response: affected offers list

- [ ] `POST /api/admin/profiles/library` (block upsert) response envelope gains an additive field `stale_offers: list[dict]` — an empty list when no published offers reference the upserted block, or a leak-fenced list `[{ "offer_id": ..., "label": ..., "publish_state": ... }]` when any do.
- [ ] `stale_offers` is derived at upsert time by calling the same `offers_referencing_block` helper and filtering to those that were `published` at the time of import.
- [ ] The existing `ProfileLibraryBlock` response schema for the upsert is extended (not replaced); the new `stale_offers` field is optional/defaulting to `[]` so old FE code that ignores extra fields is unaffected.
- [ ] The field name and shape are stable enough for Story 38.2 to build a post-import modal on.

### Tests

- [ ] `test_admin_profile_offers.py`: `sync_state == "current"` for a freshly published offer; `sync_state == "stale"` after the referenced block is re-imported (same block_id, new `imported_at`); `sync_state == "stale"` for an offer published before this story (no fingerprint in sidecar); `sync_state == "unknown"` for an unpublished offer.
- [ ] `test_admin_profile_library.py`: 409 on delete of a block referenced by at least one offer; offer list in 409 body is leak-fenced (no bundle_hash/path); 204 on delete of unreferenced block (existing test updated); out-of-band delete still causes offer list/get to return `invalid unknown_block` (existing contract).
- [ ] `test_admin_profile_library.py`: block upsert response includes `stale_offers: []` when no published offer references the block; `stale_offers: [...]` when at least one published offer references it.
- [ ] Determinism: 3× consecutive identical pytest pass counts on the affected test files before merge.
- [ ] Full `infra/scripts/check-all.sh` gate before merge.

## Likely files

### Backend

- `apps/api/app/modules/slicer/schemas.py` — add `OfferSyncState` literal; add `sync_state` field to `PrintProfileOffer`
- `apps/api/app/modules/slicer/profile_offer.py` — `offers_referencing_block()` helper; fingerprint derivation helper; upsert response `stale_offers`; read-time `sync_state` projection
- `apps/api/app/modules/slicer/admin_router.py` — 409 guard in delete handler; `stale_offers` in import response
- `apps/api/tests/test_admin_profile_offers.py`
- `apps/api/tests/test_admin_profile_library.py`

### No frontend changes in this story.

## Non-goals / scope fences

- Do not change the member-facing published-offer DTO (no `sync_state` leak to members).
- Do not add automatic/silent reslice on import or on stale detection. The operator chooses when to resync (Story 38.2).
- Do not re-run Orca resolve or write to the bundle/estimate store in the fingerprint derivation path.
- Do not remove the `invalid unknown_block` read-time resilience path for out-of-band block loss.
- Do not add bulk-delete or bulk-resync in this story.

## Deploy notes

- Backend read-path + sidecar-schema addition only. No new slicer worker module imported.
- SW-DEPLOY-1 **not triggered** — no `apps/api/app/modules/slicer/recompute.py` or worker-job paths changed.
- Alembic migration: **not required** — offer sidecars are file-backed, not DB rows.
- Normal API + web deploy is sufficient.

## Change Log

- 2026-06-14 — created from E38 decomposition. Supersedes the PROFILE-OFFER-SYNC-1 backend half of `deferred-work.md` + PROFILE-LIB-GUARD-1.
