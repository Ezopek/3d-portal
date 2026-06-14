---
baseline_commit: 4322d17752a5dc1832d9f2df3c706756654778d6
---

# Story 38.1: Admin offer sync-state foundation

Status: done

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

- [ ] At `POST /api/admin/profiles/offers/{offer_id}/publish` time, the server derives a `published_chain_fingerprint` from the chain's current block manifests: for each slot in the chain (`machine_block_id`, `process_block_id`, `filament_block_id`), read the block's curated manifest and extract its `imported_at` field; concatenate in a deterministic order (machine + process + filament) with `|` separator; SHA-256 the concatenation → 64-char hex string stored as `published_chain_fingerprint` in the offer sidecar.
- [ ] If any referenced block manifest is unreadable at publish time, the publish call fails (the chain is already `invalid` at that point — this is the existing `invalid unknown_block` path). Concretely: `derive_chain_fingerprint()` returns `None` when any manifest is missing or `imported_at` is not a string; `publish_offer()` MUST treat `None` as a hard failure, raise an `HTTPException` using the existing invalid-chain error path, and MUST NOT call `apply_published_state()` — no sidecar with `published_chain_fingerprint: null` is ever written.
- [ ] Existing offers without `published_chain_fingerprint` (published before this story) read as `sync_state="stale"` (conservative fail-open: no fingerprint = we cannot confirm currency).
- [ ] No re-derive at list/get time calls Orca or writes to the bundle/estimate store.

### `sync_state` projection in offer DTO

- [ ] `PrintProfileOffer` gains a derived (non-persisted) field `sync_state: OfferSyncState` where `OfferSyncState = Literal["current", "stale", "unknown"]`.
- [ ] `sync_state` derivation at read time:
  - `invalid` offer (existing `validation_state` field) → `sync_state = "unknown"` (the `invalid` badge dominates the UI).
  - `unpublished` offer → `sync_state = "unknown"` (not published, no published fingerprint to compare).
  - `published` + no `published_chain_fingerprint` in sidecar → `sync_state = "stale"` (backward compat for pre-38.1 publishes).
  - `published` + `published_chain_fingerprint` present → re-derive the current chain fingerprint using the same `imported_at` approach from the already-loaded `chain_block_manifests` → if equal: `sync_state = "current"`; if different: `sync_state = "stale"`; if `len(chain_block_manifests) < 3` → `sync_state = "stale"` (defensive fallback; this branch is only reachable when `resolved_state != "invalid"` because the `invalid` check above returns `"unknown"` first — do NOT apply this fallback if `resolved_state == "invalid"`).
- [ ] `sync_state` derivation MUST NOT trigger additional disk reads at list/get time: it reuses the `chain_block_manifests` already loaded by `revalidate_offers()` / `validate_chain()` (the AC-10 revalidation already reads the 3 manifests; the fingerprint check piggybacks on those reads).
- [ ] `PrintProfileOffer` admin DTO exposed through `GET /api/admin/profiles/offers` and `GET /api/admin/profiles/offers/{offer_id}` — both include `sync_state`.
- [ ] Member-facing `GET /api/profiles/offers/published` DTO (`MemberPublishedOfferView` in `schemas.py`) does NOT expose `sync_state` — it is admin-only metadata. Keep the member DTO lean.

### Block delete guard (PROFILE-LIB-GUARD-1)

- [ ] `DELETE /api/admin/profiles/library/{block_id}`: before deletion, call a new pure helper `profile_offer.offers_referencing_block(root, block_id) -> list[dict]` that iterates `list_offers(root)` and checks each sidecar's `chain` values for the given `block_id`.
- [ ] The delete guard blocks deletion if **ANY** offer references the block — including unpublished/draft offers. The guard scope is intentionally broader than the import `stale_offers` field (which lists published-only).
- [ ] If any offers reference the block, return **HTTP 409** with body: `{ "reason_category": "profile_block_in_use", "message": "...", "offers": [{ "offer_id": ..., "label": ..., "publish_state": ... }] }` — no raw Orca body, no filesystem path, no `published_bundle_hash`.
- [ ] On a 409, no block files are deleted and no `slicer_profile.library_delete` audit event is emitted.
- [ ] Non-referenced block delete keeps existing semantics: 204 on first delete, 404 on re-delete, `slicer_profile.library_delete` audit emitted.
- [ ] Existing read-time `invalid unknown_block` behavior is preserved as a resilience fallback for out-of-band filesystem deletion; do not remove that test/contract.

### Import response: affected offers list

- [ ] `POST /api/admin/profiles/library` (block upsert) response envelope gains an additive field `stale_offers: list[dict]` — an empty list when no published offers reference the upserted block, or a leak-fenced list `[{ "offer_id": ..., "label": ..., "publish_state": ... }]` when any do.
- [ ] `stale_offers` is derived at upsert time by calling `offers_referencing_block` and filtering to **`publish_state == "published"` offers only** (contrast with the delete guard which checks all offers). Unpublished offers are excluded from `stale_offers` because they are not serving members and will receive a fresh fingerprint on their next publish.
- [ ] `stale_offers` is added as an optional field **directly on `ProfileLibraryBlock`** (`stale_offers: list[dict] = Field(default_factory=list)`). The `import_profile_block` endpoint response_model stays `ProfileLibraryBlock` — no subclass, no schema rename, no OpenAPI model name change. This is the safest additive path: strict clients that already deserialise `ProfileLibraryBlock` by name are unaffected; `stale_offers` defaults to `[]` for all non-import callers (none exist — there is only the one import endpoint returning this schema, so the default is a safety measure for future callers).
- [ ] The field name and shape are stable enough for Story 38.2 to build a post-import modal on.

### Tests

- [ ] `test_admin_profile_offers.py`: `sync_state == "current"` for a freshly published offer; `sync_state == "stale"` after the referenced block is re-imported (same block_id, new `imported_at`); `sync_state == "stale"` for an offer published before this story (no fingerprint in sidecar); `sync_state == "unknown"` for an unpublished offer.
- [ ] `test_admin_profile_library.py`: 409 on delete of a block referenced by at least one offer; offer list in 409 body is leak-fenced (no bundle_hash/path); 204 on delete of unreferenced block (existing test updated/verified); out-of-band delete still causes offer list/get to return `invalid unknown_block` (existing contract).
- [ ] `test_admin_profile_library.py`: block upsert response includes `stale_offers: []` when no published offer references the block; `stale_offers: [...]` when at least one published offer references it.
- [ ] Determinism: 3× consecutive identical pytest pass counts on the affected test files before merge.
- [ ] Full `infra/scripts/check-all.sh` gate before merge.

## Tasks

- [x] **T1 — `profile_offer.py`: add helper functions**
  - [x] T1.1 Add `import hashlib` (stdlib) at the top.
  - [x] T1.2 Add `derive_chain_fingerprint(chain: ProfileChain, *, root: Path | str) -> str | None` — reads each block's manifest via `read_block()`, extracts `imported_at`, concatenates as `"{machine}|{process}|{filament}"`, returns `hashlib.sha256(concat.encode()).hexdigest()` or `None` if any manifest is missing or `imported_at` is not a string. This is the write-path helper (used in publish).
  - [x] T1.3 Add `OfferSyncState = Literal["current", "stale", "unknown"]` type alias (needed by schemas + internal derivation).
  - [x] T1.4 Add `derive_sync_state(sidecar: dict, *, chain_block_manifests: list[dict], resolved_state: OfferValidationState) -> OfferSyncState` — the read-path pure function that derives sync_state WITHOUT additional disk I/O by reusing `chain_block_manifests` (already loaded by the revalidation pass). Logic (evaluated in order, return on first match): (1) `resolved_state == "invalid"` → `"unknown"` (invalid badge dominates; do not fall through to len-check); (2) `sidecar.get("publish_state") != "published"` → `"unknown"`; (3) no `published_chain_fingerprint` in sidecar → `"stale"`; (4) `len(chain_block_manifests) < 3` → `"stale"` (defensive fallback; only reachable when resolved_state is NOT invalid, per step 1); (5) otherwise SHA-256 of `"|".join(m.get("imported_at","") for m in chain_block_manifests)` and compare to stored fingerprint → `"current"` or `"stale"`.
  - [x] T1.5 Add `offers_referencing_block(root: Path | str, block_id: str) -> list[dict]` — iterates `list_offers(root)`, checks each `sidecar["chain"]` for the given `block_id` in any of the three slot fields, returns matching raw sidecars.
  - [x] T1.6 Update `__all__` to export all new names.

- [x] **T2 — `schemas.py`: DTO changes**
  - [x] T2.1 Add `OfferSyncState = Literal["current", "stale", "unknown"]` at the PROFILE-OFFER-1 DTO section (mirrors `profile_offer.OfferSyncState`; keeps the public contract in schemas.py as the source of truth for the wire format).
  - [x] T2.2 Add `sync_state: OfferSyncState = "unknown"` field to `PrintProfileOffer` (non-persisted, computed at read time by `admin_router._offer_dto`).
  - [x] T2.3 Add `stale_offers: list[dict] = Field(default_factory=list)` **directly to `ProfileLibraryBlock`** (NOT a subclass). This is the safest additive approach: the OpenAPI schema name stays `ProfileLibraryBlock`, existing strict clients are not broken, and 38.2 can depend on the field name being stable. Add a comment: `# added 38.1: populated by import endpoint only; empty list for all other callers`.
  - [x] T2.4 Do NOT add `sync_state` to `MemberPublishedOfferView` — it must remain absent (the member leak-fence test).

- [x] **T3 — `profile_publish.py`: fingerprint at publish time**
  - [x] T3.1 Add `"published_chain_fingerprint"` to `_PUBLISH_HASH_KEYS` tuple so `apply_unpublished_state()` clears it on unpublish.
  - [x] T3.2 Update `apply_published_state()` signature to accept `chain_fingerprint: str | None` kwarg and write it as `updated["published_chain_fingerprint"] = chain_fingerprint` (alongside the other publish fields).
  - [x] T3.3 Update `publish_state_of()` dataclass `OfferPublishMetadata` to include `published_chain_fingerprint: str | None = None` and read it from the sidecar.
  - [x] T3.4 In `publish_offer()`, after `revalidate_offer()` confirms the chain is usable, call `from app.modules.slicer.profile_offer import derive_chain_fingerprint` (import at function level is fine given existing import pattern) and derive the fingerprint BEFORE calling `apply_published_state()`. **If `derive_chain_fingerprint()` returns `None`** (manifest missing or `imported_at` invalid), the publish MUST fail immediately — raise `HTTPException` using the existing invalid-chain error path (do NOT call `apply_published_state()`; do NOT write a sidecar with `published_chain_fingerprint: null`). Only if the fingerprint is a non-None string, pass it to `apply_published_state()`. The fingerprint derivation re-reads the 3 manifests — this is acceptable (3 small files); the revalidation already read them, but the existing code doesn't pass them through from `revalidate_offer()` to `publish_offer()`, so a second read is the pragmatic choice here (at publish time, not on every list/get).
  - [x] T3.5 Optionally bump `_OFFER_MANIFEST_VERSION_V2` constant to `"3"` and update the `offer_manifest_version` written on publish — this is a judgment call; if chosen, update the constant in BOTH `profile_offer.py` and `profile_publish.py` and document the bump reason. If NOT bumped, absence of `published_chain_fingerprint` is the only forward-compat signal (which the `"stale"` fallback covers). Either choice is valid — document which was chosen in the sidecar.

- [x] **T4 — `admin_router.py`: wire sync_state + delete guard + import response**
  - [x] T4.1 Add imports: `from app.modules.slicer.schemas import OfferSyncState` (add to existing import block at lines 81–104); `from app.modules.slicer.profile_offer import derive_sync_state, offers_referencing_block` (add to the `profile_offer` module-level import or use `profile_offer.derive_sync_state` / `profile_offer.offers_referencing_block`). No `ProfileLibraryImportResponse` import — `stale_offers` is now a field on `ProfileLibraryBlock` directly.
  - [x] T4.2 Update `_offer_dto()` (lines 785–820): after the `PrintProfileOffer(...)` constructor block, add computation of `sync_state` via `profile_offer.derive_sync_state(sidecar, chain_block_manifests=resolved.chain_block_manifests, resolved_state=resolved.state)` and pass it as `sync_state=sync_state` into the constructor.
  - [x] T4.3 Update `delete_profile_block()` (lines 751–770): BEFORE the `profile_library.delete_block()` call, call `offers_referencing_block(source.root, block_id)`. If the list is non-empty, raise `HTTPException(status_code=409, detail={"reason_category": "profile_block_in_use", "message": f"block is referenced by {len(referencing)} offer(s)", "offers": [{"offer_id": s.get("offer_id"), "label": s.get("label"), "publish_state": s.get("publish_state")} for s in referencing]})`. Do NOT emit the audit event on 409.
  - [x] T4.4 Add `responses={409: {"description": "Block in use by one or more offers"}}` to the `@router.delete("/profiles/library/{block_id}")` decorator.
  - [x] T4.5 Update `import_profile_block()` (lines 597–690): keep `response_model=ProfileLibraryBlock` on the decorator (no change — `stale_offers` is now a field on `ProfileLibraryBlock`); after the audit `record_event()` call, compute `stale = offers_referencing_block(source.root, block_id)` and return `ProfileLibraryBlock(**_block_dto(manifest).model_dump(), stale_offers=[{"offer_id": s.get("offer_id"), "label": s.get("label"), "publish_state": s.get("publish_state")} for s in stale if s.get("publish_state") == "published"])`. The filter to `published`-only is intentional — unpublished offers are not serving members and will receive a fresh fingerprint on their next publish.

- [x] **T5 — Tests: `test_admin_profile_offers.py`**
  - [x] T5.1 Add test: freshly published offer has `sync_state == "current"`. (Note: existing publish tests in `test_admin_profile_publish.py` mock the bundle store + arq pool — reuse the same seam pattern. Alternatively this test can call `GET /api/admin/profiles/offers/{offer_id}` on a published offer and assert `sync_state`.)
  - [x] T5.2 Add test: after re-importing the process block (same fixture → same block_id, new `imported_at`), the offer's `sync_state` becomes `"stale"`.
  - [x] T5.3 Add test: an offer whose sidecar lacks `published_chain_fingerprint` (manually written or via `profile_offer.store_offer()` with a crafted sidecar) has `sync_state == "stale"`.
  - [x] T5.4 Add test: an unpublished offer has `sync_state == "unknown"`.
  - [x] T5.5 Assert that `sync_state` does NOT appear in `GET /api/profiles/offers/published` (member DTO leak-fence). Can be a negative assertion on response JSON keys.
  - [x] T5.6 **[fingerprint-None failure]** Add test: publish attempt for an offer whose chain includes a block whose manifest has a missing or non-string `imported_at` (simulate by patching the manifest on disk or by using a test-double for `read_block`) returns HTTP 4xx (the existing invalid-chain error status) and does NOT write a published sidecar — verify the offer sidecar on disk remains unpublished after the failed call.

- [x] **T7 — Unit tests: `profile_offer.py` helpers (mandatory)**
  These unit tests exercise the pure helpers in isolation, without HTTP. Add to `test_profile_offer_store.py` or `test_profile_offer_validate.py` (whichever already imports `profile_offer`).
  - [x] T7.1 `derive_chain_fingerprint`: valid chain (all 3 manifests present, `imported_at` strings) → returns 64-char hex string; same inputs → deterministic same output.
  - [x] T7.2 `derive_chain_fingerprint`: one manifest missing `imported_at` (key absent or value is `None` / `int`) → returns `None`.
  - [x] T7.3 `derive_sync_state`: `resolved_state == "invalid"` → always `"unknown"` regardless of fingerprint in sidecar (verify the `len < 3` fallback is NOT reached by passing only 1 manifest and confirming `"unknown"` not `"stale"`).
  - [x] T7.4 `offers_referencing_block`: two offer sidecars reference the block (one via `machine_block_id`, one via `filament_block_id`) → returns list of length 2; a third sidecar with a different block_id in all slots → not included.
  - [x] T7.5 409 body shape: the delete-guard integration test (T6.1) asserts the exact JSON keys in the 409 response body: `reason_category`, `message`, `offers`; each entry in `offers` contains exactly `offer_id`, `label`, `publish_state` and nothing else (no `published_bundle_hash`, no filesystem paths).

- [x] **T6 — Tests: `test_admin_profile_library.py`**
  - [x] T6.1 Add test: `DELETE /api/admin/profiles/library/{block_id}` returns 409 with `reason_category == "profile_block_in_use"` and non-empty `offers` list when the block is used by at least one offer sidecar — **including when that offer is unpublished** (create an offer sidecar that references the block but has `publish_state != "published"`; verify DELETE still returns 409).
  - [x] T6.2 Assert the 409 body does NOT contain `published_bundle_hash`, filesystem paths, or raw Orca body fields (leak-fence).
  - [x] T6.3 Assert no block files were removed (library snapshot before == library snapshot after on 409).
  - [x] T6.4 Assert no audit event was written on 409 (`AuditLog` table count unchanged).
  - [x] T6.5 Verify existing 204 delete test still passes for an unreferenced block.
  - [x] T6.6 Add test: block upsert response includes `stale_offers: []` when no published offer exists; `stale_offers` list has one entry when a published offer references the just-upserted block.
  - [x] T6.7 Verify existing `invalid unknown_block` contract: manually delete a block file after offer creation → list/get still returns `validation_state == "invalid"` with `unknown_block` reason (existing test, confirm it still passes with the new guard in place).

## Dev Notes

### Codebase orientation

The relevant surface is entirely within `apps/api/app/modules/slicer/`. No DB migration, no worker changes, no FE changes in this story.

**Key files to read before implementing:**

| File | What to understand |
|------|-------------------|
| `profile_offer.py` | `ProfileChain`, `chain_of()`, `list_offers()`, `read_offer()`, `store_offer()`, `revalidate_offers()`, `ResolvedOffer`, `validate_chain()` returns `ChainValidation` with `chain_blocks` in m→p→f order |
| `profile_publish.py` | `apply_published_state()`, `_PUBLISH_HASH_KEYS`, `publish_offer()`, `OfferPublishMetadata`, `publish_state_of()` |
| `admin_router.py:785` | `_offer_dto()` — where `sync_state` must be wired; `_block_dto()` at line 552; `delete_profile_block()` at line 751; `import_profile_block()` at line 597 |
| `schemas.py:319` | `PrintProfileOffer` DTO — where `sync_state` field is added; `MemberPublishedOfferView` at line 372 must NOT receive it; `ProfileLibraryBlock` at line 240 |
| `profile_library.py:529` | `read_block(root, block_id) -> dict | None` — returns the curated manifest dict; the `imported_at` key is at manifest field `"imported_at"` (set at line 418 of profile_library.py) |

### Chain block manifest shape (the `imported_at` key)

`profile_library.build_block_manifest()` (line 396) stores `imported_at` as an ISO 8601 UTC string. `read_block()` returns this dict verbatim. The fingerprint input is:

```
sha256(f"{machine_imported_at}|{process_imported_at}|{filament_imported_at}".encode()).hexdigest()
```

The ordering MUST be fixed as machine→process→filament (matches `_CHAIN_SLOTS` in `profile_offer.py:65`). The separator `|` is chosen because ISO 8601 timestamps never contain `|`, making collision impossible.

### Why `chain_block_manifests` can be reused at read time

`validate_chain()` (profile_offer.py:158) iterates `_CHAIN_SLOTS = ("machine", "process", "filament")` and calls `read_block()` for each. The result is stored as `ChainValidation.chain_blocks` (present-only, in slot order). `ResolvedOffer.chain_block_manifests` carries these manifests. `_offer_dto()` in admin_router.py already has access to `resolved.chain_block_manifests`. The fingerprint check reuses these manifests — no additional disk reads.

The read-time fingerprint derivation uses `chain_block_manifests` directly:
```python
def derive_sync_state(sidecar, *, chain_block_manifests, resolved_state):
    # Step 1: invalid dominates — return "unknown" immediately; do NOT fall through
    # to the len<3 check (that would return "stale" for invalid unknown_block, which is wrong)
    if resolved_state == "invalid":
        return "unknown"
    # Step 2: unpublished offers have no published fingerprint to compare
    if sidecar.get("publish_state") != "published":
        return "unknown"
    stored = sidecar.get("published_chain_fingerprint")
    # Step 3: backward compat — offers published before 38.1 have no fingerprint
    if not stored:
        return "stale"
    # Step 4: defensive fallback (only reachable when resolved_state != "invalid")
    if len(chain_block_manifests) < 3:
        return "stale"
    parts = [m.get("imported_at", "") for m in chain_block_manifests]
    current = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return "current" if current == stored else "stale"
```

### `_PUBLISH_HASH_KEYS` and unpublish

`profile_publish.py:49` defines `_PUBLISH_HASH_KEYS = ("published_bundle_hash", "source_snapshot_ref", "published_stl_hash")`. `apply_unpublished_state()` sets each to `None`. Add `"published_chain_fingerprint"` to this tuple so it is cleared on unpublish.

### 409 detail shape for delete guard

The existing `_reject()` helper at admin_router.py:287 produces `HTTPException(status_code=..., detail={"reason_category": ..., "message": ...})`. The 409 for block-in-use needs an additional `"offers"` key — raise `HTTPException` directly (not via `_reject`) with the extended detail dict. FastAPI serializes the `detail` dict as the response body.

### `stale_offers` field on `ProfileLibraryBlock` (additive, not a subclass)

**Decision: do NOT create a `ProfileLibraryImportResponse` subclass.** Adding `stale_offers` as a subclass would rename the OpenAPI schema from `ProfileLibraryBlock` to `ProfileLibraryImportResponse`, breaking strict clients that reference the schema by name. Instead, add the field directly to `ProfileLibraryBlock`:

```python
# In schemas.py, inside ProfileLibraryBlock:
stale_offers: list[dict] = Field(default_factory=list)
# added 38.1: populated by import endpoint only; empty list for all other callers
```

Return from `import_profile_block` as:
```python
return ProfileLibraryBlock(
    **_block_dto(manifest).model_dump(),
    stale_offers=[
        {"offer_id": s.get("offer_id"), "label": s.get("label"), "publish_state": s.get("publish_state")}
        for s in offers_referencing_block(source.root, block_id)
        if s.get("publish_state") == "published"
    ],
)
```

`response_model` on the decorator stays `ProfileLibraryBlock` — no change. The `stale_offers` field defaults to `[]` so all existing serialisation paths and tests are unaffected.

### `offers_referencing_block` implementation

```python
def offers_referencing_block(root: Path | str, block_id: str) -> list[dict]:
    result = []
    for sidecar in list_offers(root):
        chain = sidecar.get("chain") or {}
        if block_id in (
            chain.get("machine_block_id"),
            chain.get("process_block_id"),
            chain.get("filament_block_id"),
        ):
            result.append(sidecar)
    return result
```

This iterates the full offer store once. The offer store is small (admin-curated, not user-generated). No caching needed.

### Test seam (existing fixtures)

Both `test_admin_profile_offers.py` and `test_admin_profile_library.py` use:
- `_SYSTEM_PARENTS` = `("system_filament_generic_tpu.json", "system_process_020_standard.json", "system_machine_k1max.json")` seeded into `<tmp_root>/system/`
- User blocks: `user_machine_k1max_microswiss.json`, `user_process_tpu_flowtech.json`, `user_filament_rosa_flex.json`
- All fixtures in `apps/api/tests/fixtures/slicer/library/`
- `_import_chain_blocks()` helper in `test_admin_profile_offers.py` does the 3-block import

For publish-requiring tests in T5.1/T5.2: the existing `test_admin_profile_publish.py` shows how to mock `bundle_store`, `stl_cache`, `arq_pool` for the publish endpoint. You can either copy that seam or write unit tests that directly call `profile_publish.publish_offer()` with test doubles. The simplest approach for T5.2 (stale after re-import) is:
1. Publish the offer (need full publish seam with DB + STL + arq mocks).
2. Re-import the same process block fixture via `POST /api/admin/profiles/library` (this updates `imported_at`).
3. `GET /api/admin/profiles/offers/{offer_id}` → assert `sync_state == "stale"`.

Alternatively, directly manipulate the sidecar on disk (via `profile_offer.store_offer()`) to simulate a pre-38.1 offer with no `published_chain_fingerprint` (for T5.3) — this avoids needing the full publish stack for some of the sync_state tests.

### Edge case: fingerprint derivation at publish vs. read time

The two uses of the fingerprint algorithm MUST produce identical results for the same block state. Both read `imported_at` from the curated manifest. At publish time, `derive_chain_fingerprint()` calls `read_block()` fresh. At read time, `derive_sync_state()` uses `chain_block_manifests` (already in memory from the revalidation pass). The manifests are the same objects (read from disk in the same session). This is correct.

**Potential issue:** if a block is updated BETWEEN the revalidation read and the sync_state derivation within the same request, the manifests in memory may be stale. This is a non-issue in practice: there is no concurrent writer during a single HTTP request; the filesystem is operator-controlled.

### Offer manifest version bump decision

The current sidecar `offer_manifest_version` is `"2"` (defined in `profile_offer.py:44` and mirrored in `profile_publish.py:48`). Adding `published_chain_fingerprint` is a new optional publish-time field. A v3 bump is optional — without it, the code uses presence/absence of the key as the compat signal (covered by the `"stale"` fallback). If bumping: update BOTH constants and document in a comment.

### `OfferSyncState` in schemas.py vs. profile_offer.py

Define `OfferSyncState = Literal["current", "stale", "unknown"]` in BOTH files:
- In `profile_offer.py`: used as the return type of `derive_sync_state()` (internal, no Pydantic import needed).
- In `schemas.py`: used as the `PrintProfileOffer.sync_state` field type (the public DTO surface).

Keeping them in both files avoids a circular import between schemas.py and profile_offer.py. They are identical types.

### Leak-fence invariants (do not break)

- `MemberPublishedOfferView` in `schemas.py:372`: must NOT gain `sync_state`, `published_chain_fingerprint`, or any chain internals.
- The 409 delete-guard body must NOT contain: `published_bundle_hash`, `source_snapshot_ref`, `published_stl_hash`, filesystem paths, block body content.
- The `stale_offers` import response field must NOT contain: `published_bundle_hash`, `source_snapshot_ref`, filesystem paths.
- `_offer_audit_payload()` at admin_router.py:845 does NOT need to include `sync_state` (it's derived, not stored).

## Testing / Gate Plan

1. **TDD order**: Write the failing test first for each group (T5.x, T6.x, T7.x), then implement the corresponding production code.
2. **Unit-level tests (mandatory)**: T7.x tests for `derive_chain_fingerprint`, `derive_sync_state`, and `offers_referencing_block` in `test_profile_offer_store.py` or `test_profile_offer_validate.py` are **required**, not optional. They must be written before the helper implementations (TDD) and must cover: missing `imported_at` → `None` return; `invalid` resolved_state short-circuits before `len<3` check; multiple offers referencing the same block; exact 409 body key set.
3. **Integration tests**: The existing T3 seam (real tmp vendored root via `seam` fixture) covers the HTTP surface.
4. **Determinism gate**: Run `pytest apps/api/tests/test_admin_profile_offers.py apps/api/tests/test_admin_profile_library.py -x` three times consecutively — all must pass with identical counts.
5. **Full gate**: `infra/scripts/check-all.sh` before merge.

## Dependency Notes for 38.2

Story 38.2 (Admin offer stale badge + resync action) depends on:

- `sync_state: OfferSyncState` in `PrintProfileOffer` DTO — must be stable before 38.2 FE starts.
- `stale_offers` field in the import response — 38.2 uses this to show a post-import "these offers are now stale" modal.
- The `"profile_block_in_use"` 409 shape — 38.2 may surface the block-in-use error in the library management UI.
- No other 38.2 backend dependency on 38.1; 38.2 adds the admin FE plus the resync endpoint.

**38.2 MUST NOT start** until the `sync_state` DTO contract is merged and the endpoint returns it consistently. The DTO contract in this story (`"current" | "stale" | "unknown"`) is stable and must not be renamed without updating 38.2 simultaneously.

## Likely files

### Backend (changes)

- `apps/api/app/modules/slicer/schemas.py` — add `OfferSyncState`; add `sync_state` to `PrintProfileOffer`; add `stale_offers` to `ProfileLibraryBlock` (no new class needed)
- `apps/api/app/modules/slicer/profile_offer.py` — `offers_referencing_block()`; `derive_chain_fingerprint()`; `derive_sync_state()`; import `hashlib`; update `__all__`
- `apps/api/app/modules/slicer/profile_publish.py` — add `published_chain_fingerprint` to `_PUBLISH_HASH_KEYS`; update `apply_published_state()`; update `OfferPublishMetadata`; call `derive_chain_fingerprint` in `publish_offer()`
- `apps/api/app/modules/slicer/admin_router.py` — wire `sync_state` in `_offer_dto()`; add 409 guard in `delete_profile_block()`; update `import_profile_block()` response

### Tests (new + updated)

- `apps/api/tests/test_admin_profile_offers.py` — new sync_state tests (T5.x); member DTO negative assertion
- `apps/api/tests/test_admin_profile_library.py` — 409 delete guard tests (T6.1–T6.4); stale_offers import tests (T6.6); existing contract regression (T6.5, T6.7)

### No frontend changes in this story.

## Non-goals / Scope Fences

- Do not change the member-facing published-offer DTO (no `sync_state` leak to members).
- Do not add automatic/silent reslice on import or on stale detection. The operator chooses when to resync (Story 38.2).
- Do not re-run Orca resolve or write to the bundle/estimate store in the fingerprint derivation path.
- Do not remove the `invalid unknown_block` read-time resilience path for out-of-band block loss.
- Do not add bulk-delete or bulk-resync in this story.
- Do not touch `member_router.py`, `profile_selection.py`, `recompute.py`, or any worker path.
- Do not start 38.2, 38.3, or 38.4.

## Deploy Notes

- Backend read-path + sidecar-schema addition only. No new slicer worker module imported.
- SW-DEPLOY-1 **not triggered** — no `apps/api/app/modules/slicer/recompute.py` or worker-job paths changed.
- Alembic migration: **not required** — offer sidecars are file-backed, not DB rows.
- Normal API + web deploy is sufficient after merge.

## Dev Agent Record

### Completion Notes

- T3.5 (manifest version bump): decided NOT to bump — absence of `published_chain_fingerprint` is the sole compat signal, covered by the `"stale"` fallback.
- T5.1/T5.2/T5.6 publish tests: switched from HTTP import (`_import_chain_blocks`) to direct `_store_chain_block_t5` seeding from `INTENTS_FIXTURE` — mirrored pattern from `test_admin_profile_publish.py` — because HTTP import requires system parent inheritance resolution which failed with `chain_resolve_failed: missing_system_profile`.
- T6.5 existing test: had to delete offers out-of-band (filesystem) rather than via HTTP DELETE, because the new 409 guard correctly blocks deletion while offers reference the block.
- Regression in `test_list_revalidates_after_referenced_block_deleted`: fixed by replacing HTTP DELETE with `profile_library.delete_block()` direct call.
- `ProfileLibraryBlock.stale_offers` double-kwarg TypeError: fixed by mutating `model_dump()` dict before unpacking.

### Debug Log

| Issue | Fix |
|-------|-----|
| `seam_publish` → `offer_requires_attention` (chain resolve failed missing system profile) | Replaced HTTP import with direct `_store_chain_block_t5` seeder from INTENTS_FIXTURE |
| `ProfileLibraryBlock(**_block_dto(...).model_dump(), stale_offers=...)` TypeError | `block_data = .model_dump(); block_data["stale_offers"] = ...; return ProfileLibraryBlock(**block_data)` |
| `test_list_revalidates_after_referenced_block_deleted` → 409 instead of 204 | Changed to out-of-band `_pl.delete_block(root, process)` |
| 25 ruff errors in test files | 12 auto-fixed; 13 manually fixed (E402 imports, RUF059 unpacked vars, F841 unused) |

### Senior Developer Review (AI)

- 2026-06-14 — Aider diff review: **APPROVE**. No critical/important changes requested.
- Controller verification: targeted pytest `91 passed`; full gate log `.hermes/run-logs/38-1-check-all-final.log` shows `16/16` and `all green.`

## File List

### Modified

- `apps/api/app/modules/slicer/profile_offer.py` — `derive_chain_fingerprint`, `derive_sync_state`, `offers_referencing_block`, `OfferSyncState`, `__all__`
- `apps/api/app/modules/slicer/schemas.py` — `OfferSyncState`, `PrintProfileOffer.sync_state`, `ProfileLibraryBlock.stale_offers`
- `apps/api/app/modules/slicer/profile_publish.py` — `_PUBLISH_HASH_KEYS`, `OfferPublishMetadata`, `apply_published_state`, `publish_offer`
- `apps/api/app/modules/slicer/admin_router.py` — `_offer_dto` sync_state wire, delete guard 409, import response stale_offers
- `apps/api/tests/test_admin_profile_offers.py` — T5.1–T5.6 tests + regression fix
- `apps/api/tests/test_admin_profile_library.py` — T6.1–T6.7 tests
- `apps/api/tests/test_profile_offer_store.py` — T7.1–T7.5 unit tests

## Change Log

- 2026-06-14 — created from E38 decomposition. Supersedes the PROFILE-OFFER-SYNC-1 backend half of `deferred-work.md` + PROFILE-LIB-GUARD-1.
- 2026-06-14 — enriched to ready-for-dev with full implementation context (Tasks/Subtasks, Dev Notes, concrete file paths, function signatures, testing plan, dependency notes for 38.2).
- 2026-06-14 — implemented: all T1–T7 tasks complete; 91 tests pass (3× determinism gate); check-all.sh 16/16 green; status → review.
- 2026-06-14 — revised after Aider story review: (1) T3.4 + AC: fingerprint None → HTTPException, no null sidecar; T5.6 new test. (2) T1.4 + AC + Dev Notes pseudocode: derive_sync_state step ordering made explicit; len<3 fallback only reachable when resolved_state != invalid. (3) AC + T6.1: delete guard explicitly blocks on ANY offer including unpublished; stale_offers import field filters to published-only. (4) T7 task group added: mandatory helper unit tests for derive_chain_fingerprint, derive_sync_state, offers_referencing_block, exact 409 body shape. (5) T2.3 + T4.1/4.5 + Dev Notes: replaced ProfileLibraryImportResponse subclass with additive stale_offers field directly on ProfileLibraryBlock; response_model unchanged; no OpenAPI schema rename.
