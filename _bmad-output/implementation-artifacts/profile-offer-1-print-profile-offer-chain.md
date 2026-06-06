---
baseline_commit: 221bbe1
story_key: profile-offer-1-print-profile-offer-chain
epic: E33
initiative: 21
---

# Story PROFILE-OFFER-1: Minimal PrintProfileOffer / ProfileChain layer over the profile-block library

Status: ready-for-dev (context complete; dev-story execution BLOCKED pending G-DEVGO operator dev-go.
The FE offer-composition surface is additionally gated on G-UXGATE; real resolver publication / live
slicing is OUT of this slice and gated as G-PUBLISH. Spec authoring ONLY — NO code, NO deploy, NO commit.)

<!--
  Authored by the repo-local BMAD author of record (Claude Opus 4.8, 2026-06-06) following the
  bmad-create-story [CS] shape and the repo's vanilla-first routing. This is the SECOND slice of the
  corrected canonical separate-block model and the THEN step named in the 2026-06-06 profile-model
  correction SCP § 6 / § 8: a small, additive PrintProfileOffer + ProfileChain layer that CONSUMES
  the PROFILE-LIB-1 block library (shipped/done @221bbe1, live .190 G-SMOKE passed).

  Deliberately MINIMAL. This first offer slice proves the DATA MODEL + admin CRUD + dry chain
  VALIDATION. It does NOT compile/publish a chain into the resolver intent path and does NOT slice
  (that is the explicitly-gated G-PUBLISH step / a later slice). The shipped 33.1/33.2 fixed grid
  stays the transitional compiled-intent projection that still feeds the member selector + estimates;
  no forced migration.

  Source artifacts (verified read 2026-06-06):
    - SCP sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md — § 3.4 (ProfileChain),
      § 3.5 (PrintProfileOffer), § 3.6 (material taxonomy = small generic bridge), § 4 (grid =
      transitional compiled-intent projection, kept, coexist, no forced migration), § 6 (THEN
      PROFILE-OFFER-1 boundaries + deferred register), § 7 (preserved 33.2 safety foundations),
      § 8 (UX checkpoint REQUIRED before heavy relationship/offer-composition UI), § 9 (deferred
      register — do not over-expand), Appendix A (offer/chain model fields, member-UX boundary).
    - epics.md § Initiative 21 (Story PROFILE-LIB-1 section + this PROFILE-OFFER-1 section appended).
    - architecture.md § Initiative 21 — Decision AM (separate-block library, shipped) names
      "Decision AN / PROFILE-OFFER-1" as the offer/chain layer; this story anchors Decision AN.
    - Shipped PROFILE-LIB-1 (profile-lib-1-operator-profile-block-inventory.md, done @221bbe1) — the
      block library this story READS and the foundations (publish_pair atomic write, ezop:ezop 664
      metadata preservation, leak fence, containment assert, audit) it REUSES.
    - Code read: apps/api/app/modules/slicer/profile_library.py (classify_profile,
      extract_curated_metadata, resolve_inherit_chain, derive_validation_state, block_path,
      library_root, list_blocks, read_block, store_block/snapshot_block/restore_block, delete_block,
      build_block_manifest, _assert_within_library, is_valid_block_id, derive_block_id;
      import_service.publish_pair / _json_bytes), slicer/admin_router.py (library routes + current_admin
      + _MAX_PROFILE_BYTES), slicer/schemas.py (ProfileLibraryBlock / ProfileLibraryListResponse,
      extra="forbid"), slicer/compatibility.py (MATERIAL_TIER_COMPATIBILITY — grid SoT, NOT touched),
      core/audit.py (slicer_profile entity_type + record_event); FE
      apps/web/src/modules/admin/{ProfileLibraryPage.tsx, hooks/useProfileLibrary.ts}, lib/api-types.ts.

  GATE NOTE: "ready-for-dev" = the story context is dev-ready. Actual dev-story execution stays BLOCKED
  pending (G-DEVGO) an explicit operator dev-go (this is a write-bearing E33 story — it writes offer
  sidecars into the operator-managed vendored tree, SCP-2026-06-04 § 7 pattern). The FE
  offer-composition surface is additionally gated on (G-UXGATE) a UX/admin design checkpoint
  (extends UX-PROFILE-1; SCP § 8 — offer composition IS relationship UI). Real resolver publication /
  live slicing over an offer is OUT of scope here and recorded as (G-PUBLISH) for a later slice.
-->

## Story

As an **admin/operator of the 3d-portal**,
I want **to compose a `PrintProfileOffer` by selecting exactly one machine block + one process block + one filament block from the existing profile-block library, give it a member/admin label, mark its visibility/default, and declare its compatible material categories — and have the backend validate the resulting `ProfileChain` (all three blocks exist, are the right type, are not in `error` state, and are internally compatible) and surface a clear `usable` / `requires_attention` / `invalid` state — then list, inspect, edit (label/visibility/default/categories), and delete those offers**,
so that **the canonical offer/chain layer over the separate Orca-like blocks exists and is validated as a data model + admin CRUD surface, WITHOUT yet compiling anything into the resolver intent path or slicing — the shipped 33.1/33.2 grid stays the transitional compiled-intent projection feeding the member selector untouched, and turning an offer into real slicer input + a member-facing choice is an explicit, separately-gated later step (G-PUBLISH).**

This is the **THEN** step the 2026-06-06 profile-model correction named after PROFILE-LIB-1 (SCP § 6).
It is the **first surface of `PrintProfileOffer` / `ProfileChain`** (architecture Decision AN). It is
deliberately **offer data-model + admin CRUD + dry validation only** — it is **NOT** an N×M
relationship editor, **NOT** a raw Orca JSON viewer/editor, **NOT** a member spool-picker /
request-flow, **NOT** a full Orca-GUI clone, **NOT** any Spoolman mutation, and it does **NOT** publish
a compiled chain into the resolver intent path or run live slicing (G-PUBLISH, deferred).

## Acceptance Criteria

### Backend — offer/chain data model + validation engine (`slicer/profile_offer.py`)

1. **AC-1 — New additive engine module; library + grid both untouched.** A new
   `apps/api/app/modules/slicer/profile_offer.py` holds the offer/chain data model, the offer storage
   layer, and the dry chain-validation engine. It is **purely additive**: it does NOT edit
   `resolver.py`'s `resolve()`, `compatibility.py`, the `intents/`/`system/` (grid) trees,
   `bundle_hash`, the append-only bundle/snapshot/estimate stores, the PROFILE-LIB-1
   `profile_library.py` *write* path, or the 33.1/33.2 grid endpoints. It only **reads** the library
   via `profile_library.list_blocks` / `read_block` and reuses `import_service.publish_pair` for its
   own sidecar writes. A test asserts the engine never imports/calls the grid/resolve/bundle symbols
   and that `git diff` against those surfaces is body-unchanged (mirrors the PROFILE-LIB-1 AC-1 fence).
   (SCP § 4 coexist-no-migration; § 1 additive.)
2. **AC-2 — `ProfileChain` value object (embedded, not separately CRUD'd).** A `ProfileChain` is the
   triple of library block references `{machine_block_id, process_block_id, filament_block_id}`
   (each a 32-char hex `block_id` validated via `profile_library.is_valid_block_id`). In this slice the
   chain is an **embedded value object inside an offer** (an offer carries exactly one representative
   `ProfileChain`) — there is **NO** standalone reusable chain registry / chain CRUD endpoints (that is
   deferred; SCP § 9). The chain carries no raw Orca body — only the three `block_id`s plus the
   validation result (AC-4). (SCP § 3.4.)
3. **AC-3 — `PrintProfileOffer` data model (curated, on-disk sidecar, no DB).** A `PrintProfileOffer`
   carries: `offer_id` (server-derived path-safe, AC-6); `label` (member/admin display string, DATA —
   not translated); optional `description`; the embedded `ProfileChain` (AC-2); `visibility ∈
   {hidden, visible}`; `is_default: bool`; `compatible_material_categories: list[str]` constrained to
   the small generic table `{PLA, PETG, PCTG, TPU}` (SCP § 3.6 — an out-of-table category is rejected
   `422 unsupported_material_category`, never minted); `validation_state ∈ {usable,
   requires_attention, invalid}` + machine-readable `reasons: list[str]`; `created_at`, `created_by`,
   `updated_at`. It is stored as an **on-disk sidecar** (AC-5), consistent with the slicer subsystem's
   no-DB / append-only posture (SCP § 4 no-DB; Decision AM precedent) — **no Alembic, no DB table**.
   The on-disk sidecar is sufficient because an offer is low-cardinality operator config that must live
   on the same operator-managed `portal-content` volume as the blocks it references and is read by the
   same api-side engine; a DB table would introduce the slicer subsystem's first Alembic schema against
   its documented Boundaries for no functional gain in this slice. (SCP § 3.5; § 4.)
4. **AC-4 — Dry chain-validation engine (`usable` / `requires_attention` / `invalid`), NO resolve, NO
   slice.** `validate_chain(chain, *, library_root) -> (ValidationState, reasons)` validates a chain by
   **reading the referenced blocks' curated manifests only** (`profile_library.read_block`) — it does
   **NOT** call `resolve()`, does **NOT** read raw Orca bodies, does **NOT** write `intents/`, and does
   **NOT** slice. Precedence `invalid` > `requires_attention` > `usable`:
   - **`invalid`** (offer stored but not offerable; or rejected per AC-9 gate order — see AC-9):
     a referenced `block_id` is **missing** from the library (`unknown_block`); or a referenced block's
     `profile_type` does **not** match its slot (`wrong_block_type` — e.g. a `process` block in the
     machine slot); or a referenced block is itself in `error` state (cannot occur for stored blocks —
     PROFILE-LIB-1 never stores `error` blocks — but guarded as `block_unusable`).
   - **`requires_attention`** (stored + listed, flagged): a referenced block is `requires_attention`
     (propagated as `block_requires_attention`); or the filament block's `compatible_printers` is
     present and does **not** include the machine block's printer identity
     (`filament_machine_incompatible`); or the offer's `compatible_material_categories` does not
     include the filament block's `material_type` (`material_category_mismatch`); or
     `is_default ∧ visibility==hidden` (`default_but_hidden`); or two **visible** offers share a default
     for the same material category (`duplicate_default` — computed across the offer set on
     list/validate, AC-7).
   - **`usable`**: all three blocks present, correctly typed, all `usable`, filament↔machine compatible
     (or `compatible_printers` absent), material category consistent, no default conflict.
   Each non-`usable` reason is a machine-readable CATEGORY (the FE localizes it; no display text from
   the backend). Deeper Orca process↔filament slice-time validity is **explicitly deferred to
   G-PUBLISH** (it requires the resolver path). (SCP § 3.4–3.6; § 6.)
5. **AC-5 — Offer storage layout (additive `offers/` subtree).** Offers live in a NEW subtree under the
   existing `slicer_vendored_profiles_dir` root, **disjoint from** `system/`, `intents/` (grid), and
   `library/` (blocks): `<root>/offers/<offer_id>.json` (the curated offer sidecar v1 — there is NO
   separate body/manifest split because an offer has no raw Orca body, only curated refs). The layout is
   owned by a single `offer_path(root, offer_id) -> Path` helper (single SoT, mirroring
   `profile_library.block_path`), with a `<root>/offers` containment assert reusing the
   `profile_library._assert_within_library` pattern (factor a shared `_assert_within(root, subdir,
   target)` helper if behavior-preserving). (SCP § 4 separate/additive.)
6. **AC-6 — Server-derived, path-safe `offer_id` (identity stable across label edits).** `offer_id` is
   **derived server-side**, NOT taken from the request: `offer_id = uuid4().hex` minted once at create
   time and immutable thereafter. **Contract — why uuid4, not uuid5(label):** the offer identity must be
   (a) **path-safe** (32-char lowercase hex, no separators/traversal/attacker control — same structural
   property as the PROFILE-LIB-1 `block_id`) AND (b) **stable across `label` edits** — an offer's label,
   visibility, default, and categories are all mutable (AC-12), so identity must NOT be derived from any
   mutable field. (This deliberately differs from `block_id = uuid5(type:name)`, which is derived from a
   block's **immutable** `(type, name)` to make re-import an UPSERT; an offer has no immutable natural
   key, so a minted token is correct.) The `{offer_id}` route param is validated as 32-char lowercase
   hex → `404` otherwise (never joined raw). A containment assert (AC-5) is applied belt-and-braces.
   (Magic-constant discipline [[feedback_scp_pre_enumeration_phase]] § C.)
7. **AC-7 — Atomic store + metadata preservation (PROFILE-LIB-1 / 33.2 foundations reused).** Writing an
   offer sidecar reuses the **shared rollback-safe atomic publish** (`import_service.publish_pair` /
   `_json_bytes`) and the **same owner/mode preservation** (files land `ezop:ezop 664` on the
   operator-managed bind mount — the `31bcf0c` / `221bbe1` metadata-preservation fix that PROFILE-LIB-1
   already carries) so a fresh `offers/` directory and its files inherit the correct owner/mode. On ANY
   failure the `offers/` subtree is byte-identical to before and no temp remains. The duplicate-default
   check (AC-4) is computed by reading the existing offer set, NOT by mutating other offers. **Reuse the
   existing helpers — do not re-implement them.** (SCP § 7 atomic-publish + permission-preservation.)

### Backend — CRUD endpoints (on the existing `slicer/admin_router.py`)

8. **AC-8 — DTOs (`extra="forbid"`, no raw body).** New `slicer/schemas.py` DTOs:
   `ProfileChainRef` (`machine_block_id`, `process_block_id`, `filament_block_id`);
   `PrintProfileOffer` (`offer_id`, `label`, `description: str|null`, `chain: ProfileChainRef`,
   `visibility`, `is_default`, `compatible_material_categories: list[str]`, `validation_state`,
   `reasons: list[str]`, `created_at`, `created_by`, `updated_at`, plus a **resolved-for-display**
   `chain_blocks: list[ProfileLibraryBlock]` echo so the FE can render the selected blocks' curated
   metadata WITHOUT a second round-trip and WITHOUT any raw Orca body); `PrintProfileOfferListResponse`
   (`offers: list[PrintProfileOffer]`); `PrintProfileOfferCreate` / `PrintProfileOfferUpdate` request
   bodies. Reuse the existing `ProfileLibraryBlock` for the `chain_blocks` echo and
   `ProfileImportRejection` for structured rejections. Every DTO is `ConfigDict(extra="forbid")` and
   carries **no raw Orca key body, no filesystem path, no g-code** (the PROFILE-LIB-1 / 33.2 leak fence;
   a negative-assertion test mirrors it). `visibility = Literal["hidden","visible"]`;
   `validation_state = Literal["usable","requires_attention","invalid"]`. (Pre-enum: extend the module,
   same fence.)
9. **AC-9 — `POST /api/admin/profiles/offers` — create an offer.** JSON body `PrintProfileOfferCreate`
   (`label`, optional `description`, `chain: {machine_block_id, process_block_id, filament_block_id}`,
   `visibility` default `hidden`, `is_default` default `false`, `compatible_material_categories`). Gate
   order: **body size 413** (reuse `_MAX_PROFILE_BYTES = 1 MiB` — same contract as the library import; an
   offer JSON is a small object) → **parse/shape 422 `invalid_json` / `invalid_offer`** → **material
   category gate 422 `unsupported_material_category`** (an out-of-`{PLA,PETG,PCTG,TPU}` category) → **hard
   chain gate 422 `invalid_chain`** when validation returns `invalid` for a structural reason
   (`unknown_block` / `wrong_block_type` / `block_unusable`) — **nothing stored** → otherwise derive
   validation state (AC-4; `requires_attention` does NOT block storage) → **atomic store** (AC-7) →
   **audit** → **201** with the `PrintProfileOffer` DTO (AC-8). Admin-gated (`current_admin`), absent
   from `_PUBLIC_ROUTES`, CSRF automatic (middleware) — same posture as the library routes. (SCP § 6;
   § 3.5.)
10. **AC-10 — `GET /api/admin/profiles/offers` — list offers.** Returns every offer's curated DTO
    (`PrintProfileOffer`), read from `<root>/offers/*.json`, optionally filtered by
    `?material_category=` and/or `?visibility=`. Each offer's `validation_state` + `reasons` are
    **recomputed at read time** against the current library state (AC-4) so a stale `usable` is never
    served after a referenced block was deleted — a deleted referenced block surfaces as `invalid`
    `unknown_block` on the next list (no eager cross-deletion of offers; the offer remains, flagged).
    The `chain_blocks` echo is populated from the library; a missing referenced block yields a null/omit
    entry plus the `unknown_block` reason, never a raw-body leak. Deterministic ordering (by
    `created_at` then `offer_id`). A missing/empty `offers/` tree ⇒ `200` empty list. (SCP § 6.)
11. **AC-11 — `GET /api/admin/profiles/offers/{offer_id}` — get one offer.** Returns the single
    `PrintProfileOffer` DTO (validated hex, AC-6), `404 not_found` when absent, with the same read-time
    revalidation + `chain_blocks` echo. **Curated metadata + validation state only — NO raw Orca JSON
    body** (no raw-Orca preview anywhere — SCP § 6). (SCP § 6.)
12. **AC-12 — `PATCH /api/admin/profiles/offers/{offer_id}` — edit label/visibility/default/categories
    (audited).** Partial update of `label`, `description`, `visibility`, `is_default`, and/or
    `compatible_material_categories` ONLY. The **chain (block refs) is immutable on PATCH** — changing the
    selected blocks means deleting the offer and creating a new one (keeps `offer_id` ↔ chain identity
    simple; chain mutation/versioning is deferred, SCP § 9). On edit: re-run the material-category gate
    (AC-9) + re-derive validation state (AC-4) + atomic re-write (AC-7) + bump `updated_at` + audit;
    `404 not_found` when absent. (SCP § 6.)
13. **AC-13 — `DELETE /api/admin/profiles/offers/{offer_id}` — remove an offer (audited).** Removes the
    offer sidecar for `offer_id`, `404 not_found` when absent, `204` on success, **audited** (AC-14).
    Deleting an offer does **NOT** touch the referenced library blocks (offers reference, they do not
    own). Re-deleting an absent offer is `404` (idempotent-safe, not 500). (SCP § 6.)
14. **AC-14 — Audit on create/edit/delete (NFR21-OBS-1), reusing `slicer_profile`.** Create emits
    `record_event(action="slicer_profile.offer_create", entity_type="slicer_profile",
    entity_id=<offer_id-as-UUID>, actor_user_id=<admin>, after={label, visibility, is_default,
    compatible_material_categories, machine_block_id, process_block_id, filament_block_id,
    validation_state})`; edit emits `.offer_update`; delete emits `.offer_delete` with the same
    `entity_id`. `entity_type="slicer_profile"` is **already in `KNOWN_ENTITY_TYPES`** — only the comment
    block above it gains a one-line extension naming the three new actions (no registry entry). The audit
    payload carries **no Orca body, no g-code, no filesystem path**. A rejected create (size/parse/
    category/invalid_chain) is **not** audited. (NFR21-OBS-1; reuse the PROFILE-LIB-1 audit shape.)
15. **AC-15 — Route-enforcement gate green; no `_PUBLIC_ROUTES` edit.** All offer routes carry
    `current_admin` (default-value `Depends`), so `tests/test_route_enforcement_gate.py` passes
    **without** any `_PUBLIC_ROUTES` allowlist edit. Non-admin → 403, anonymous → 401, mutating routes
    require the CSRF `X-Portal-Client: web` header (existing middleware). The `test_slicer_worker.py`
    admin-router route-surface fence is extended to admit the four/five sanctioned offer routes (one
    mechanical fence update, mirroring how the library routes evolved it). (NFR21-AUTH-1.)

### Frontend — minimal admin offer surface (GATED on G-UXGATE; no raw JSON viewer, no N×M editor)

16. **AC-16 — UX checkpoint precedes the composition UI (G-UXGATE, SCP § 8).** Because offer composition
    (selecting machine+process+filament + label/visibility/default/categories) **is relationship UI**,
    the FE offer-composition surface MUST NOT be built until a **UX/admin design checkpoint**
    (extends UX-PROFILE-1, `bmad-ux` / Sally) signs off the composition layout — explicitly so it does
    **not** regress into an Orca-GUI clone or an unusable N×M matrix (SCP § 8). The backend (AC-1..AC-15)
    proceeds **without** G-UXGATE; the FE tasks (T4–T6) are blocked on it. The checkpoint output is a
    `ux-profile-offer-1-*` artifact + sprint-status row (parallel to `ux-profile-1-*`).
17. **AC-17 — Minimal offer surface (list + compose + edit + delete).** After G-UXGATE, a minimal admin
    surface (a sub-tab/section under the existing admin "profiles" area or a sibling route
    `routes/admin/profile-offers.tsx`, dev's choice within the `AdminTabs` shell) renders: a **compose**
    affordance — three **single-select** block pickers (machine / process / filament) populated from the
    library list (the PROFILE-LIB-1 `useProfileLibrary` data), a label field, a visibility toggle, a
    default toggle, and a material-category multi-select constrained to `{PLA,PETG,PCTG,TPU}`; a **list**
    of offers showing label + the three selected block names + a **validation-state badge** (`usable` /
    `requires_attention` / `invalid` styling); a **detail/expand** showing the chain's curated blocks +
    flagged reasons; an **edit** affordance for label/visibility/default/categories; and a **delete**
    behind a confirm dialog (mirror the `UsersPage` / `ProfileLibraryPage` `ConfirmDialog` pattern). It is
    **single-select per slot** — explicitly **NOT** an N×M relationship grid. **No raw Orca JSON is
    rendered anywhere.** The surface fails **closed/visible** on error. (SCP § 6; § 8.)
18. **AC-18 — CRUD hooks + cache topology.** New TanStack hooks in `apps/web/src/modules/admin/hooks/`:
    `useProfileOffers(filters?)` (query, key `["admin","profile-offers", filters ?? "all"]`,
    `staleTime: 0` + `refetchOnMount: "always"` — admin must see true offer state incl. read-time
    revalidation; the same contract `useProfileLibrary` uses); `useCreateProfileOffer()` /
    `useUpdateProfileOffer()` / `useDeleteProfileOffer()` (mutations via `api()`, `retry: false`,
    `onSuccess → invalidateQueries(["admin","profile-offers"])`). The compose pickers read from
    `useProfileLibrary` (the shipped library query) — **read-only consumption, no cross-invalidation**
    of the library cache from offer mutations. The mutations surface the structured `reason_category`
    (reuse `importRejectionCategory`) localized; **no optimistic insert/remove** — the list reconciles
    from the server. (Cache-topology table below.)
19. **AC-19 — i18n parity + tokens.** New keys under `modules.admin.profileOffers.*` (compose action/
    copy, the three `validation_state` labels, each `reason` category — `unknown_block` /
    `wrong_block_type` / `block_unusable` / `block_requires_attention` / `filament_machine_incompatible`
    / `material_category_mismatch` / `default_but_hidden` / `duplicate_default` /
    `unsupported_material_category` / `invalid_chain` / `not_found`, the filter labels, the slot picker
    labels, edit/delete-confirm copy) land in **both `en.json` + `pl.json` with full key parity** +
    correct Polish diacritics. **Offer `label`s, block `name`s, and `material_type`s render as DATA
    (untranslated).** No inline hex — reuse existing tokens; the validation-state badges reuse the
    PROFILE-LIB-1 badge token set. (NFR21-I18N-PARITY-1.)

### Cross-cutting — visual, determinism, scope fence

20. **AC-20 — Visual baselines (GATED on G-UXGATE; UX-designed states).** After G-UXGATE, new Playwright
    baselines across the 4 projects (`desktop-light/dark`, `mobile-light/dark`), each with a
    `baseline-reviewed:` sign-off: (1) the offer **list** with a mix of `usable` + `requires_attention` +
    `invalid` offers; (2) the **compose** affordance open with the three slot pickers; (3) a **create
    rejection** (e.g. `invalid_chain` / `unsupported_material_category`); (4) an offer **detail** with the
    chain blocks + a `requires_attention` reason. API stubbed via `apps/web/tests/visual/api-stubs.ts`
    (add `/api/admin/profiles/offers` GET/POST/PATCH/DELETE stubs + a post-create list variant + a library
    list stub for the pickers). (NFR21-VISUAL-VERIFICATION-1.)
21. **AC-21 — Determinism gate.** 3× consecutive identical pytest + vitest pass counts; `ruff
    check`/`format`, `npm run typecheck`, `npm run lint -- --max-warnings=0`, `git diff --check` clean;
    full `infra/scripts/check-all.sh` green before any ff-merge. (NFR21-DETERMINISM-1.)
22. **AC-22 — Scope fence (what this story does NOT do).** **No** resolver publication / compile of an
    offer's chain into the `intents/` path and **no** live slicing or estimate over an offer
    (**G-PUBLISH** — a later slice). **No** standalone `ProfileChain` registry / chain CRUD (the chain is
    an embedded value object). **No** N×M relationship editor (single-select per slot only). **No** raw
    Orca JSON viewer / raw field editor. **No** member-facing surface, selector change, spool-picker, or
    request-flow (the member selector still consumes the shipped 33.1/33.2 grid projection — SCP § 3.7).
    **No** Spoolman read/write/mutation (concrete-filament/Spoolman overrides are a later layer —
    SCP § 3.3). **No** machine-capability material-policy enforcement (record the seam only — SCP § 3.1).
    **No** change to the 33.1 grid read, the 33.2 grid import, `compatibility.py`, `resolve()`,
    `bundle_hash`, the append-only stores, the `intents/`/`system/` trees, or the PROFILE-LIB-1 library
    *write* path (offers only **read** the library). **No** Alembic / DB (on-disk sidecar only).
    **No** new slicer-worker module → **SW-DEPLOY-1 NOT triggered** (offers are api-side curated data on
    the shared `portal-content` volume). **No** live `.190` smoke (**G-SMOKE** — operator/runtime gate,
    not run by this card). (SCP § 6 deferred register; § 9.)

## Tasks / Subtasks

- [ ] **T1 — Offer/chain data model + dry validation engine (AC-2,3,4)** — new `slicer/profile_offer.py`
      + `tests/test_profile_offer_validate.py`
  - [ ] RED first: `validate_chain` over library fixtures — a fully-`usable` chain; an `unknown_block`;
        a `wrong_block_type`; a `requires_attention` propagation; a `filament_machine_incompatible`; a
        `material_category_mismatch`; a `default_but_hidden`; a `duplicate_default` across two offers.
  - [ ] Assert the engine reads ONLY curated manifests (`read_block`) — never raw bodies, never
        `resolve()`; leak-fence negative test (no raw Orca key / g-code / path in any DTO/manifest/audit).
- [ ] **T2 — Offer storage layer (AC-5,6,7)** — in `slicer/profile_offer.py` +
      `tests/test_profile_offer_store.py`
  - [ ] `offer_path` single-SoT layout; `offer_id = uuid4().hex` server-minted; hex validator for
        GET/PATCH/DELETE; `<root>/offers` containment assert (reuse/extend `_assert_within`).
  - [ ] `store_offer` / `list_offers` / `read_offer` / `delete_offer` — reuse `publish_pair` +
        owner/mode preservation (incl. fresh-directory metadata inheritance, the `221bbe1` fix); read-time
        revalidation in list/read.
  - [ ] Tests: atomic store leaves byte-identical tree on injected failure + no temp; owner/mode preserved
        (skip chown assert in non-root dev per the existing `suppress(PermissionError)` pattern); delete
        idempotency/404; list recomputes validation after a referenced block is removed.
- [ ] **T3 — CRUD endpoints (AC-8..AC-15)** — extend `slicer/admin_router.py` + `slicer/schemas.py` +
      `tests/test_admin_profile_offers.py`
  - [ ] DTOs (`extra="forbid"`, no raw body; reuse `ProfileLibraryBlock` for `chain_blocks`).
  - [ ] Five routes on the existing router object (POST/GET-list/GET-one/PATCH/DELETE
        `/api/admin/profiles/offers[/{offer_id}]`); `current_admin`; no `_PUBLIC_ROUTES` edit; CSRF
        automatic.
  - [ ] Create gate order (413 → 422 invalid_json/invalid_offer → 422 unsupported_material_category →
        422 invalid_chain → store → audit → 201); list/get (filters + read-time revalidation + 404);
        PATCH (chain immutable, re-validate, audit); delete (204/404, audited; library untouched).
  - [ ] Audit `slicer_profile.offer_create`/`.offer_update`/`.offer_delete` (reuse `slicer_profile`
        entity_type + comment-only audit.py extension).
  - [ ] Tests: 403 non-admin / 401 anon / 413 over-cap / 422 invalid_chain (not stored) / 422
        unsupported_material_category; successful create ⇒ 201 + DTO + sidecar + audit;
        requires_attention case stored+flagged; list/get/patch/delete round-trip; deleting a referenced
        block flips the offer to `invalid` on next list; leak-fence negative assertion; extend
        `test_slicer_worker.py` route-surface fence (AC-15).
- [ ] **T4 — UX checkpoint (AC-16; G-UXGATE)** — `bmad-ux` / Sally design pass for the offer-composition
      surface (extends UX-PROFILE-1). **BLOCKS T5/T6.** Produces `ux-profile-offer-1-*` artifact +
      sprint-status row. Until signed off, NO FE composition code is written.
- [ ] **T5 — FE offer surface (AC-17,18,19)** *(gated on T4)* — `apps/web/src/modules/admin/` +
      `routes/admin/`
  - [ ] `useProfileOffers` / `useCreateProfileOffer` / `useUpdateProfileOffer` / `useDeleteProfileOffer`
        hooks (cache topology per the table); compose pickers read `useProfileLibrary`.
  - [ ] Offer surface: compose (3 single-select slot pickers + label/visibility/default/category-multi),
        list + validation-state badges, detail expander (curated only, NO raw JSON), edit, delete +
        ConfirmDialog; fails closed/visible.
  - [ ] i18n `modules.admin.profileOffers.*` en+pl parity + diacritics; zero inline hex; data fields
        untranslated. Wire into `AdminTabs` / route shell with the existing auth gate.
- [ ] **T6 — FE + visual tests (AC-17,18,19,20,21)** *(gated on T4)* — colocated vitest
      (`afterEach(cleanup)`) + Playwright baselines for the 4 states × 4 projects; `baseline-reviewed:`
      per PNG; `api-stubs.ts` offer + library stubs. Intercept at `fetch`, do not mock `api()`.
- [ ] **T7 — Determinism + self-review (AC-21)**
  - [ ] pytest 3× + vitest 3× identical; ruff/format/typecheck/lint/diff --check; full `check-all.sh`
        green before ff-merge.

## Dev Notes

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] § A — existence checklist)

1. **Library read surface (REUSE read-only):** `profile_library.list_blocks(root, profile_type=?)`
   (`profile_library.py:504`), `read_block(root, block_id)` (`:529`), `is_valid_block_id` (`:349`),
   `library_root` (`:354`), `block_path` (`:359`) — the offer engine READS these to resolve a chain's
   block refs to curated metadata. It does **not** touch the library *write* path (`store_block` /
   `delete_block` / `publish_pair`-via-library).
2. **Atomic publish + metadata preservation (REUSE verbatim):** `import_service.publish_pair` +
   `_json_bytes` (imported at `profile_library.py:31`) — the rollback-safe two-phase write +
   `ezop:ezop 664` owner/mode preservation (incl. the `221bbe1` fresh-directory metadata inheritance
   fix). The offer sidecar is a single JSON file; reuse `publish_pair` (it already handles a body +
   sidecar pair — for an offer, pass the curated JSON as the body and either a trivial companion or
   factor a single-file variant behavior-preserving; prefer reusing the proven path over a new writer).
3. **Containment assert (REUSE/EXTEND):** `profile_library._assert_within_library` (`:374`) — generalize
   to `_assert_within(root, subdir, target)` (behavior-preserving) or add a sibling `offers/` assert;
   the `offer_id` hex validation (AC-6) plus this assert close the path-traversal class structurally.
4. **Compatibility SoT (DO NOT TOUCH):** `compatibility.py` `MATERIAL_TIER_COMPATIBILITY` /
   `is_compatible` is the **grid** projection's live gate — this story does NOT consume or edit it. The
   offer-chain compatibility (AC-4) is a **separate** check over the blocks' curated metadata
   (filament `compatible_printers` / `material_type`); the AC-3/AC-9 material-category table is the small
   generic `{PLA,PETG,PCTG,TPU}` bridge (SCP § 3.6), NOT the tier-compat map.
5. **Audit registry (REUSE, comment-only extend):** `core/audit.py` — `slicer_profile` is already in
   `KNOWN_ENTITY_TYPES`; `record_event` gates only `entity_type`, so `.offer_create`/`.offer_update`/
   `.offer_delete` need no registry add — only the comment block gains one line (mirrors how
   PROFILE-LIB-1 added `.library_import`/`.library_delete`).
6. **Admin router (EXTEND):** `slicer/admin_router.py` already mounts on `app/router.py`; the offer routes
   are added to the **same** `router` object alongside the library routes. `current_admin`,
   `_MAX_PROFILE_BYTES` (`1 MiB`), and the reject/size-capped-read shapes are reusable.
7. **DTOs (EXTEND module):** `slicer/schemas.py` holds the `AdminProfile*` + `ProfileLibrary*` DTOs (all
   `extra="forbid"`, no-leak fence). Add the offer DTOs here, same fence; reuse `ProfileLibraryBlock` for
   the `chain_blocks` echo and `ProfileImportRejection` for rejections.
8. **CSRF (AUTOMATIC):** `core/auth/csrf.py` middleware enforces `X-Portal-Client: web` on mutating
   `/api/*`; the FE `api()` wrapper covers it. No route-level CSRF code.
9. **FE CRUD reference (MIRROR):** `ProfileLibraryPage.tsx` + `hooks/useProfileLibrary.ts` (the just-shipped
   list + detail + delete-confirm + structured-error mapping + disjoint cache key) are the closest
   reference; `UsersPage.tsx` for the multi-action + `ConfirmDialog` pattern. `routes/admin/profile-library.tsx`
   is the auth-gated route shell to mirror.
10. **api-types (EXTEND):** `lib/api-types.ts` holds the `ProfileLibraryBlock` + `ValidationState` +
    `ProfileType` TS types; add `PrintProfileOffer` / `ProfileChainRef` / offer list-response /
    `OfferVisibility` types here.
11. **Slicer module Boundaries (RESPECT):** `slicer/README.md` § Boundaries — on-disk JSON only, no
    DB/Alembic, atomic, concurrency-safe. The offer sidecar stays on-disk (SCP § 4 no-DB).
12. **Member selector seam (DO NOT TOUCH in this slice):** the member selector + estimate path consume the
    33.1/33.2 grid projection. Offers are **not** published to it here (G-PUBLISH). Record the seam:
    publishing an offer's chain into the resolver intent path is the bridge a later slice builds.

### Cache-topology enumeration (per [[feedback_scp_pre_enumeration_phase]] § B — FE CRUD story)

| Concern | Source: this story (`useProfileOffers` + create/update/delete) | Source: PROFILE-LIB-1 (`useProfileLibrary` `["admin","profile-library"]`) |
|---|---|---|
| Staleness budget (`staleTime`) | `staleTime: 0` + `refetchOnMount: "always"` — admin must see true offer state, especially because validation is **recomputed server-side at read time** (AC-10) and can flip after a referenced block changes. Points to "admin must see true inventory state". | `staleTime: 0` + `refetchOnMount: "always"`. **AGREE** → simple reuse. |
| Retry policy | **No auto-retry** on create/update/delete writes (admin re-submits explicitly) — points to NFR21-OBS-1 (one audit event per real op) + admin-fails-closed. | `retry: false`. **AGREE.** |
| Cache propagation on mutations | `invalidateQueries(["admin","profile-offers"])` on create/update/delete. Own key namespace, distinct from `["admin","profile-library"]` and `["admin","profiles"]`. Offer mutations do **NOT** invalidate the library cache (offers reference, they don't mutate blocks). | library invalidates `["admin","profile-library"]`. **Distinct keys, no overlap.** |
| Cache eviction on route exit | None (admin-only; no cross-route contamination). | None. **AGREE.** |
| Cache seeding on this route | The compose pickers **read** `useProfileLibrary` (shared canonical library query) — read-only consumption, no seeding/override of the library cache from the offer route. | n/a. **One-way read; no divergence.** |

All rows AGREE or use a deliberately-disjoint key namespace; the one cross-query touch is the compose
pickers **reading** the library query read-only (no cross-invalidation). Call-out: **no-auto-retry on
writes** (pointed to the one-audit-event + fail-closed contracts).

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **`_MAX_PROFILE_BYTES = 1 MiB` (AC-9):** reused from the library import — an offer JSON is a small
  object (curated refs + a handful of fields). **Not** re-derived; **not** the STL cap.
- **`offer_id = uuid4().hex` (AC-6):** points to two contracts — (a) the id must be **path-safe**
  (32-char hex, no attacker-controlled segment, structurally closing the traversal class) AND (b)
  **stable across mutable label/visibility/default/category edits** (an offer has no immutable natural
  key, so identity is a minted token). Deliberately **differs** from `block_id = uuid5(type:name)`
  (derived from a block's **immutable** key to make re-import an upsert) — the contrast is the
  justification, not "matches the block id shape".
- **`offer_manifest_version = "1"` (sidecar, AC-3):** points to the **PROFILE-OFFER-1 offer-sidecar
  contract v1**, a NEW schema distinct from the library-manifest v1 and the intent-manifest v1. Bumping
  it is a future migration.
- **Material category table `{PLA, PETG, PCTG, TPU}` (AC-3/AC-9):** points to SCP § 3.6 "keep generic
  categories small and aligned"; an out-of-table category ⇒ `422 unsupported_material_category`, never a
  minted narrow category. ABS/ASA are a later expansion (deferred).

### Architecture / constraints

- **Decision AN** (architecture.md § Initiative 21, anchored by this story): the **PrintProfileOffer /
  ProfileChain layer** — an additive `<root>/offers/<offer_id>.json` curated sidecar subtree, server-
  minted path-safe `offer_id`, an embedded `ProfileChain` value object referencing three library
  `block_id`s, a **dry read-only chain-validation** engine (NO `resolve()`, NO slicing) that consumes the
  Decision AM library, and admin CRUD over it — reusing the AM/AL atomic-publish + metadata-preservation
  + audit + leak-fence foundations. **It does NOT compile into the resolver intent path** (the
  publish/slice bridge is the explicitly-gated G-PUBLISH step / a later slice). Decisions AK/AL (the
  grid) remain the transitional compiled-intent projection feeding the member selector; Decision AM (the
  block library) is what AN consumes.
- Preserves Init 20 `bundle_hash` / `source_system_tree_hash` / append-only invariants
  (NFR21-PROVENANCE-1) trivially (offers never enter the resolve/bundle path in this slice).
- Backend rules: `Annotated` DI, `current_admin` default-value dep, namespaced logger, no `os.environ`,
  ruff `E,F,W,I,B,UP,SIM,RUF` line-length 100, TDD red→green. Frontend rules: `import type`,
  `noUncheckedIndexedAccess` (no `!`), `@/*` alias, network via `api()` only, i18n mandatory, no inline
  hex, ESLint `--max-warnings=0`, `afterEach(cleanup)`.

### Project Structure Notes

- **New backend:** `apps/api/app/modules/slicer/profile_offer.py` (data model + storage + dry
  validation) + `apps/api/tests/test_profile_offer_validate.py` + `tests/test_profile_offer_store.py` +
  `tests/test_admin_profile_offers.py`. **Edited:** `slicer/admin_router.py` (offer routes),
  `slicer/schemas.py` (offer DTOs), `core/audit.py` (comment-only one line),
  `tests/test_slicer_worker.py` (route-surface fence + the offer routes).
- **New FE (gated on G-UXGATE):** `apps/web/src/modules/admin/hooks/useProfileOffers.ts` +
  `useCreateProfileOffer.ts` + `useUpdateProfileOffer.ts` + `useDeleteProfileOffer.ts` + an offer
  surface component (+ `routes/admin/profile-offers.tsx` if a sibling route) + visual specs.
  **Edited:** `AdminTabs.tsx` (if a new tab), `en.json`/`pl.json`, `lib/api-types.ts`,
  `apps/web/tests/visual/api-stubs.ts`.
- **No** `_PUBLIC_ROUTES` edit, **no** Alembic, **no** `config.py` slot (reuses
  `slicer_vendored_profiles_dir`), **no** `workers/render/` change, **no** `resolver.py`/
  `compatibility.py`/grid/library-write change. SW-DEPLOY-1 not triggered.

### References

- SCP: [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md]
  — § 3.4 (ProfileChain), § 3.5 (PrintProfileOffer), § 3.6 (material taxonomy), § 4 (grid = projection,
  coexist, no migration), § 6 (THEN PROFILE-OFFER-1 boundaries + deferred register), § 7 (preserved 33.2
  foundations), § 8 (UX checkpoint), § 9 (deferred register), Appendix A.
- Epics: [Source: _bmad-output/planning-artifacts/epics.md § Initiative 21] (Story PROFILE-OFFER-1
  section appended by this run).
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md § Initiative 21] — Decision AN
  (anchored by this run); Decision AM (library) consumed; AK/AL (grid projection) untouched.
- Shipped: profile-lib-1-operator-profile-block-inventory.md (done @221bbe1 — the block library this
  story reads + the foundations reused); `apps/api/app/modules/slicer/{profile_library.py,
  import_service.py, admin_router.py, schemas.py, compatibility.py}`, `apps/api/app/core/audit.py`,
  `apps/web/src/modules/admin/{ProfileLibraryPage.tsx,hooks/useProfileLibrary.ts}`,
  `apps/web/src/lib/{api.ts,api-types.ts}`.
- Memory: [[feedback_scp_pre_enumeration_phase]] — pre-enumeration + cache-topology + magic-constant
  discipline applied above.

### Operator / data / config gates (surface BEFORE dev-go)

- **G-DEVGO — operator dev-go (process, SCP-2026-06-04 § 7 pattern).** This is a **write-bearing** E33
  story (it writes offer sidecars into the operator-managed vendored tree). Code implementation stays
  BLOCKED until an explicit operator dev-go, mirroring PROFILE-LIB-1. This spec is doc-only (no code/
  deploy/commit).
- **G-UXGATE — UX/admin design checkpoint (process, SCP § 8 — REQUIRED before the FE composition UI).**
  Offer composition is relationship UI; a `bmad-ux` / Sally checkpoint (extends UX-PROFILE-1) must sign
  off the composition layout before T5/T6 are built, so it does not regress into an Orca-GUI clone or an
  N×M matrix. The **backend (T1–T3) proceeds without it**; only the FE is blocked. Output:
  `ux-profile-offer-1-*` artifact + sprint-status row.
- **G-PUBLISH — real resolver publication / live slicing (product + runtime, EXPLICITLY DEFERRED).**
  Compiling an offer's `ProfileChain` into the resolver `intents/` path and running a live slice/estimate
  over it is **OUT of this slice**. It touches the live slicing/`bundle_hash`/member-estimate path and
  needs its own slice (provisionally PROFILE-OFFER-2), an operator go, and likely a deploy/RW smoke. It
  is recorded here so future agents do **not** fold publication into PROFILE-OFFER-1. **Safe default
  implied by the SCP:** until G-PUBLISH lands, the member selector keeps consuming the 33.1/33.2 grid
  projection unchanged (SCP § 4 coexist, no forced migration).
- **G-DATA — real Orca block exports: SATISFIED for this slice.** The offer layer validates over the
  **already-imported** library blocks (PROFILE-LIB-1 shipped 7 real-derived blocks live on `.190`, and
  committed sanitized fixtures under `apps/api/tests/fixtures/slicer/library/`). No new real-Orca
  discovery is needed — the chain validation operates on curated metadata already in the library. (Open
  product question recorded, not blocking: the exact filament↔machine compatibility key used for
  `filament_machine_incompatible` — `compatible_printers` string-match vs a normalized printer ref — is
  pinned against the existing library fixtures during T1; if the fixtures prove insufficient the dev
  flags it rather than guessing, per the magic-constant discipline.)
- **G-SMOKE — live `.190` RW-mount + vendoring smoke (runtime, NOT authorized by this card).** The
  `offers/` subtree rides the same known-RW `portal-content` volume PROFILE-LIB-1's `library/` already
  proved live. A real offer create/list/delete against the `.190` tree + an owner/mode
  (`ezop:ezop 664`) assertion is the deploy-GO precondition — **recorded as a future/operator runtime
  gate, explicitly NOT run by this card.**

### Review / fix-up budget

- External review: **Gemini** default (`laura-gemini-review`) on the focused diff; **Codex**
  fallback/high-stakes — this slice has an **on-disk-write adjacency** (a new `offers/` subtree) + a
  **validation/leak-fence** surface, so a Codex countersignature is warranted if Gemini surfaces any
  atomicity/leak/validation-correctness doubt. Tag `# gemini-review:` / `# codex-review:` per AGENTS.md.
- Fix-up budget 0-4, likely surfaces: (a) read-time revalidation correctness (a deleted referenced block
  must flip the offer to `invalid` on the next list, not serve a stale `usable`); (b) `offer_id`
  identity vs mutable label (do NOT derive id from label); (c) the leak fence (a raw Orca key slipping
  into the `chain_blocks` echo, the sidecar, or the audit); (d) the chain validation accidentally
  invoking `resolve()` / reading raw bodies / writing `intents/` (scope-fence breach); (e) i18n parity /
  Polish diacritics on the new reason categories; (f) duplicate-default detection across the offer set.

## Dev Agent Record

(Empty — dev-story not started. Execution BLOCKED pending G-DEVGO; FE additionally gated on G-UXGATE;
real resolver publication / live slicing is OUT of scope, gated as G-PUBLISH.)
