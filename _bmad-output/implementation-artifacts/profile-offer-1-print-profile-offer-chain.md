---
baseline_commit: 221bbe1
story_key: profile-offer-1-print-profile-offer-chain
epic: E33
initiative: 21
---

# Story PROFILE-OFFER-1: Minimal PrintProfileOffer / ProfileChain layer over the profile-block library

Status: done (code-side) — backend (T1–T3) AND frontend (T5–T6) dev-complete + verified; **controller full
aggregate gate PASSED + external review APPROVE** (see Controller closeout below). Remaining merge/deploy/G-SMOKE
are controller-owned and NOT yet executed. **T4 (G-UXGATE) SATISFIED
2026-06-06** by the `bmad-ux`/Sally checkpoint `_bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md`;
**T5/T6 BUILT 2026-06-06** against that checkpoint by the controller-resumed `bmad-dev-story` flow: the minimal admin
offer surface (`ProfileOffersPage` — 3 single-select pickers, list + validation badges, curated detail, edit,
delete-confirm, fails-closed), the four CRUD hooks, en/pl i18n parity, and the 4 Playwright baselines × 4 projects.
All story ACs except the **controller-owned** closeout gates are met: focused vitest (offers 8 + i18n 4) + full web
vitest (607) green, `npm run typecheck` + `npm run lint` clean, 16 visual baselines generated + stable on re-run +
visually reviewed, `git diff --check` clean. **Controller closeout (2026-06-06):** full `infra/scripts/check-all.sh`
PASSED — RC=0, 16/16 stages green (incl. apps/web visual regression 444 passed / 24 skipped), log
`.hermes/run-logs/profile-offer-1-controller-check-all-20260606_145028.log`; external review **Gemini CLI 0.45.2 →
APPROVE** (no blockers / no important / no nits), log `.hermes/run-logs/profile-offer-1-gemini-review-20260606_145933.log`.
G-DEVGO satisfied (operator dev-go 2026-06-06). **G-PUBLISH remains explicitly deferred** (no resolver publication /
live slicing / member-selector change). **Remaining controller-owned post-code steps NOT yet executed:** ff-merge to
`main`, `infra/scripts/deploy.sh`, and the runtime **G-SMOKE** on `.190`. No commit/merge/deploy/live-smoke has
happened yet. See Dev Agent Record for the exact slice.

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

- [x] **T1 — Offer/chain data model + dry validation engine (AC-2,3,4)** — new `slicer/profile_offer.py`
      + `tests/test_profile_offer_validate.py` ✅
  - [x] RED first: `validate_chain` over library fixtures — a fully-`usable` chain; an `unknown_block`;
        a `wrong_block_type`; a `requires_attention` propagation; a `filament_machine_incompatible`; a
        `material_category_mismatch`; a `default_but_hidden`; a `duplicate_default` across two offers.
        (RED confirmed via ImportError, then GREEN — 14 tests.)
  - [x] Assert the engine reads ONLY curated manifests (`read_block`) — never raw bodies, never
        `resolve()`; leak-fence negative test (no raw Orca key / g-code / path in any DTO/manifest/audit).
        (Additive-fence test: no import of resolver/compatibility/bundle_store, no call-form grid symbols.)
- [x] **T2 — Offer storage layer (AC-5,6,7)** — in `slicer/profile_offer.py` +
      `tests/test_profile_offer_store.py` ✅ (22 tests)
  - [x] `offer_path` single-SoT layout; `offer_id = uuid4().hex` server-minted; hex validator for
        GET/PATCH/DELETE; `<root>/offers` containment assert (new behavior-preserving `_assert_within`).
  - [x] `store_offer` / `list_offers` / `read_offer` / `delete_offer` — reuse the shared atomic write +
        owner/mode preservation via NEW `import_service.publish_single` (single-file variant reusing
        `_stage_temp`'s fsync + metadata source, incl. the `221bbe1` fresh-dir fix); read-time
        revalidation in `revalidate_offers`/`revalidate_offer`.
  - [x] Tests: atomic store leaves byte-identical tree on injected `os.rename` failure + no temp; owner/mode
        preserved (mode asserted in tmpfs; chown best-effort via the shared `suppress(PermissionError)`);
        delete idempotency/404; list recomputes validation after a referenced block is removed.
- [x] **T3 — CRUD endpoints (AC-8..AC-15)** — extend `slicer/admin_router.py` + `slicer/schemas.py` +
      `tests/test_admin_profile_offers.py` ✅ (25 tests)
  - [x] DTOs (`extra="forbid"`, no raw body; reuse `ProfileLibraryBlock` for `chain_blocks`; hex
        field-validators on `ProfileChainRef`).
  - [x] Five routes on the existing router object (POST/GET-list/GET-one/PATCH/DELETE
        `/api/admin/profiles/offers[/{offer_id}]`); `current_admin`; no `_PUBLIC_ROUTES` edit; CSRF
        automatic. Route-enforcement gate passes WITHOUT allowlist edit.
  - [x] Create gate order (413 → 422 invalid_json/invalid_offer → 422 unsupported_material_category →
        422 invalid_chain → store → audit → 201); list/get (filters + read-time revalidation + 404);
        PATCH (chain immutable via `extra="forbid"`, re-validate, audit); delete (204/404, audited; library
        untouched).
  - [x] Audit `slicer_profile.offer_create`/`.offer_update`/`.offer_delete` (reuse `slicer_profile`
        entity_type + comment-only audit.py extension).
  - [x] Tests: 403 non-admin / 401 anon / 413 over-cap / 422 invalid_chain (not stored) / 422
        unsupported_material_category; successful create ⇒ 201 + DTO + sidecar + audit;
        requires_attention case stored+flagged; list/get/patch/delete round-trip; deleting a referenced
        block flips the offer to `invalid` on next list; leak-fence negative assertion; extended
        `test_slicer_worker.py` route-surface fence (GETs 3→5, POSTs 2→3, +1 PATCH, DELETEs 1→2) (AC-15).
- [x] **T4 — UX checkpoint (AC-16; G-UXGATE)** — ✅ **DONE 2026-06-06** (`bmad-ux`/Sally checkpoint).
      Artifact: `_bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md` (extends
      UX-PROFILE-1 per SCP § 8) + sprint-status row `ux-profile-offer-1-admin-offer-composition-ux-design`.
      Signs off the minimal admin offer-composition layout (list + compose/detail panel, single-select-per-slot,
      NO N×M / NO Orca-GUI clone / NO raw-Orca JSON), the validation-badge + reason surfacing (all 8 backend
      reason categories + endpoint rejections mapped to admin copy), fails-closed/read-time-revalidation
      honesty, a11y/i18n/visual-state guidance, and the AC-16..AC-20 → T5/T6 mapping. **G-UXGATE SATISFIED →
      T5/T6 UNBLOCKED.** Design-only: no app/test/config/code, no deploy/live-smoke/commit by this pass.
      G-PUBLISH NOT authorized by this checkpoint.
- [x] **T5 — FE offer surface (AC-17,18,19)** ✅ *(built 2026-06-06 against the G-UXGATE checkpoint)*
  - [x] `useProfileOffers` / `useCreateProfileOffer` / `useUpdateProfileOffer` / `useDeleteProfileOffer`
        hooks (cache topology per the table — key `["admin","profile-offers", filters ?? "all"]`,
        `staleTime:0`+`refetchOnMount:"always"`, `retry:false`, invalidate-on-write); compose pickers read
        `useProfileLibrary` read-only (no cross-invalidation); `offerRejectionCategory` reuses the rejection shape.
  - [x] Offer surface (`ProfileOffersPage.tsx`): compose/edit panel (3 single-select native `<select>` slot
        pickers + label/description/visibility/default/category-multi), list + validation-state badges (icon+text
        +color, never color alone), detail expander (curated chain blocks + reasons, NO raw JSON), edit (chain
        read-only — immutable hint), delete + `ConfirmDialog`; empty/loading/error states; fails closed/visible.
        Material + visibility filter chips wired to the server query.
  - [x] i18n `modules.admin.profileOffers.*` (60 keys) en+pl full parity + diacritics; zero inline hex (reuses
        success/warning/destructive tokens); data fields (label/block name/material) untranslated. Wired into
        `AdminTabs` (`profile-offers` tab) + sibling route `routes/admin/profile-offers.tsx` (AuthGate discipline:
        defer to shell for anon, role-redirect authenticated-non-admin). `routeTree.gen.ts` regenerated.
- [x] **T6 — FE + visual tests (AC-17,18,19,20,21)** ✅ *(built 2026-06-06)*
  - [x] colocated vitest `ProfileOffersPage.test.tsx` (8 tests, `afterEach(cleanup)`, intercept at `fetch`) +
        `profile-offers-i18n.test.ts` (4 parity tests) — all green. Playwright `admin-profile-offers.spec.ts`:
        the 4 states (list-mixed / compose-open / create-rejected / detail-expanded) × 4 projects = 16 baselines,
        `baseline-reviewed:` per screenshot, stable on re-run; `stubProfileOffers` added to `api-stubs.ts`.
- [x] **T7 — Determinism + self-review (AC-21)** — backend + FE portions DONE; full aggregate gate PASSED by the controller (check-all RC=0, 16/16 green).
  - [x] Backend determinism: full `pytest` suite green (1610 passed, 3 skipped); new offer suite 3×
        identical (61 passed each run); `ruff format --check` + `ruff check` clean on all touched files.
  - [x] FE determinism: full web `vitest` green (119 files / 607 tests, incl. the global i18n parity test +
        the 12 new offer tests); `npm run typecheck` clean; `npm run lint --max-warnings=0` clean; 16 offer
        visual baselines stable on a clean re-run; `git diff --check` clean.
  - [x] Full `infra/scripts/check-all.sh` green before ff-merge — the controller's CI-equivalent aggregate
        merge gate. **PASSED 2026-06-06** (RC=0, 16/16 stages green incl. apps/web visual regression 444 passed /
        24 skipped), log `.hermes/run-logs/profile-offer-1-controller-check-all-20260606_145028.log`. No merge in
        this bookkeeping run (ff-merge/deploy/G-SMOKE remain controller-owned, not yet executed).

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

### Agent

Repo-local BMAD developer of record (Claude Opus 4.8, 1M ctx), `bmad-dev-story` workflow, 2026-06-06.
Operator dev-go ("Ok, lećmy 🙂 Niech bmad ogarnia 🙂") satisfied G-DEVGO. Branch
`feat/E33-profile-offer-1-print-profile-offer-chain` from `main @4e798ab`. No commit/merge/deploy by
the dev agent (left for the controller). `baseline_commit: 221bbe1` preserved from the spec frontmatter.

### Implementation Plan / approach

TDD red→green per task. Backend implemented as a purely-additive layer over PROFILE-LIB-1:

- **T1 — engine** (`profile_offer.py`): `ProfileChain` value object + `validate_chain` (chain-intrinsic:
  `unknown_block` / `wrong_block_type` / `block_unusable` → invalid; `block_requires_attention` /
  `filament_machine_incompatible` → requires_attention) + `evaluate_offer` (layers the offer-scoped
  `material_category_mismatch` / `default_but_hidden` / `duplicate_default`). Reads ONLY curated manifests
  via `profile_library.read_block` — no `resolve()`, no raw bodies, no `intents/` write, no slicing.
- **Filament↔machine identity pin (AC-4 / G-DATA open question):** resolved against the real library
  fixtures, NOT guessed. A filament's `compatible_printers` references the SYSTEM machine name; a USER
  machine block customizes its own `name` but inherits that system name. So the machine identity set =
  `{name} ∪ {inherit} ∪ inherit_chain`; the user block matches via its inherited system name, the system
  block via its own name. Verified against `user_machine_k1max_microswiss` ↔ `user_filament_rosa_flex`.
- **T2 — storage** (`profile_offer.py`): `offer_id = uuid4().hex` (path-safe + edit-stable, deliberately
  UNLIKE `block_id = uuid5(type:name)`); `<root>/offers/<offer_id>.json` single-SoT layout via
  `offer_path`; new behavior-preserving `_assert_within(root, subdir, target)` containment helper;
  read-time revalidation in `revalidate_offers` (recomputes state + cross-offer `duplicate_default` from
  the current library — a deleted referenced block flips to `invalid unknown_block`, the offer is NOT
  eagerly deleted). Atomic writes reuse a NEW `import_service.publish_single` (single-file variant that
  shares `_stage_temp`'s fsync + `ezop:ezop 664` metadata source, incl. the `221bbe1` fresh-dir fix) —
  no re-implemented unsafe write.
- **T3 — endpoints** (`admin_router.py` + `schemas.py`): five admin-gated routes
  (POST/GET-list/GET-one/PATCH/DELETE `/api/admin/profiles/offers[/{offer_id}]`) on the existing router;
  `extra="forbid"` DTOs (`ProfileChainRef` with hex field-validators; `chain_blocks` reuses
  `ProfileLibraryBlock`); create gate order 413 → 422 invalid_json → 422 invalid_offer → 422
  unsupported_material_category → 422 invalid_chain → store → audit → 201; PATCH keeps the chain immutable
  (it's forbidden on the update DTO → 422); audit-failure rollback mirrors the library import.
  `slicer_profile.offer_create/.offer_update/.offer_delete` reuse the `slicer_profile` entity_type
  (comment-only `audit.py` extension). No `_PUBLIC_ROUTES` edit; route-enforcement gate green.

### Completion Notes

- **Backend (T1–T3) dev-complete and green.** New offer suite: `test_profile_offer_validate.py` (14) +
  `test_profile_offer_store.py` (22) + `test_admin_profile_offers.py` (25) = 61 tests, 3× deterministic.
  Full backend suite **1610 passed, 3 skipped** (no regressions). `ruff format --check` + `ruff check`
  clean on every touched file.
- **Route-surface fence extended (AC-15):** `test_slicer_worker.py` now asserts 5 GETs / 3 POSTs / 1 PATCH
  / 2 DELETEs on `admin_router.py` (was 3/2/0/1) — the one sanctioned mechanical fence update.
- **Leak fence verified:** offer DTO, sidecar, `chain_blocks` echo, and audit payload carry no raw Orca
  key / g-code / filesystem path (negative assertions in both the engine and endpoint tests).
- **Scope fences honoured (AC-22):** no `resolve()`/`compatibility.py`/grid/`bundle_hash`/append-only/
  `intents/`/`system/`/library-WRITE change; no Alembic/DB; no Spoolman; no member-selector change; no raw
  Orca viewer; no N×M editor; no standalone chain registry; SW-DEPLOY-1 not triggered. G-PUBLISH not
  touched (no compile into the resolver intent path, no slicing).
- **T4 / G-UXGATE — SATISFIED 2026-06-06 (`bmad-ux`/Sally checkpoint).** Artifact authored:
  `_bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md` (extends UX-PROFILE-1 per
  SCP § 8), + sprint-status row `ux-profile-offer-1-admin-offer-composition-ux-design=done`, + this story's
  Status/T4/T5/T6 updated. It signs off the minimal admin offer-composition layout (list + compose/detail
  panel, single-select-per-slot, NO N×M / NO Orca-GUI clone / NO raw-Orca JSON), maps all 8 backend reason
  categories + the endpoint rejections to admin copy, specifies fails-closed + read-time-revalidation honesty,
  a11y/i18n/visual-state guidance, and the AC-16..AC-20 → T5/T6 mapping. **Design-only**: no app/test/config/
  code touched, no deploy/live-smoke/commit by the UX pass. **G-PUBLISH is NOT satisfied/NOT authorized** by
  this checkpoint (resolver publication / live slicing / member projection remain a separate later slice).
- **FE (T5–T6) BUILT + GREEN 2026-06-06 (controller-resumed `bmad-dev-story`).** Implemented against the
  G-UXGATE checkpoint, consuming the existing backend contract verbatim (no backend change required — the DTOs,
  gate order, reason categories, and read-time revalidation were all already in place):
  - **Hooks (AC-18):** `useProfileOffers(filters?)` (key `["admin","profile-offers", filters ?? "all"]`,
    `staleTime:0`+`refetchOnMount:"always"`); `useCreateProfileOffer` / `useUpdateProfileOffer` /
    `useDeleteProfileOffer` (`retry:false`, `invalidateQueries(["admin","profile-offers"])` on success, no
    optimistic insert/remove); `offerRejectionCategory` extracts the structured `reason_category`. Compose pickers
    read `useProfileLibrary()` read-only — no cross-invalidation of the library cache.
  - **Surface (AC-17):** `ProfileOffersPage.tsx` — compose/edit panel with 3 single-select native `<select>`
    pickers (machine/process/filament, the UX-endorsed floor — NOT an N×M matrix), label/description, visibility
    toggle, default toggle + the attention-rule helper, `{PLA,PETG,PCTG,TPU}` category multi-select; a list with
    one validation badge per offer (precedence `invalid`>`requires_attention`>`usable`, icon+text+color), the first
    reason inline on `invalid` rows; a curated detail expander (chain blocks + full reason list, NO raw Orca JSON);
    edit (chain read-only + "delete + re-create" hint, mirrors PATCH AC-12); delete behind `ConfirmDialog` with the
    honest blast-radius copy; empty/loading/error states; fails closed/visible (error panel + Retry). Material +
    visibility filter chips drive the server query.
  - **i18n (AC-19):** 60 keys under `modules.admin.profileOffers.*` + `admin.tabs.profileOffers`, en/pl full
    parity + Polish diacritics; all 8 reason categories + endpoint rejections localized; data fields untranslated;
    zero inline hex (reuses the shipped success/warning/destructive token set).
  - **Wiring:** `AdminTabs` gains the `profile-offers` tab; sibling route `routes/admin/profile-offers.tsx`
    (AuthGate discipline — defers to the shell for anon, role-redirects authenticated-non-admin only);
    `routeTree.gen.ts` regenerated (additions only).
  - **Tests (AC-20/21):** `ProfileOffersPage.test.tsx` (8 vitest, fetch-intercept, `afterEach(cleanup)`) +
    `profile-offers-i18n.test.ts` (4 parity) green; `admin-profile-offers.spec.ts` 4 states × 4 projects = 16
    Playwright baselines (`baseline-reviewed:` per PNG, stable on re-run); `stubProfileOffers` added to `api-stubs.ts`.
- **Verification run by the dev agent (FE):** full web `vitest` 607 passed (no regressions); `npm run typecheck`
  clean; `npm run lint --max-warnings=0` clean; 16 visual baselines generated + re-run stable + visually reviewed
  (list/compose/rejection/detail render correctly); `git diff --check` clean. Backend untouched, so the prior
  backend determinism (1610 pytest / ruff) stands.
- **Honest status:** moved to `review`. All story ACs except the controller-owned closeout gates are satisfied;
  the FE acceptance criteria (AC-17..AC-20) are now built + verified, not just designed.

### Controller next step (not a dev-agent call)

**T5/T6 are built + verified** (FE offer surface + hooks + i18n + the 4 Playwright baselines × 4 projects), so the
whole card is dev-complete. The closeout gate + external review are now done; the remaining steps are controller-owned:

1. ✅ **DONE 2026-06-06** — Full `infra/scripts/check-all.sh` green (the CI-equivalent aggregate gate — build +
   vitest + pytest + visual regression in one run): **RC=0, 16/16 stages green** (incl. apps/web visual regression
   444 passed / 24 skipped), log `.hermes/run-logs/profile-offer-1-controller-check-all-20260606_145028.log`.
2. ✅ **DONE 2026-06-06** — External review per AGENTS.md: **Gemini CLI 0.45.2** read-only review → verdict
   **APPROVE** (no blockers / no important / no nits), log
   `.hermes/run-logs/profile-offer-1-gemini-review-20260606_145933.log`. Note: Gemini initially attempted an
   unavailable shell tool but still produced a read-only code-review verdict; the controller had already verified
   the target state + gates separately, so the APPROVE stands on inspected code, not faked. No Codex countersign was
   required (Gemini surfaced no atomicity/leak/validation doubt).
3. ⏳ **NOT yet executed (controller-owned)** — ff-merge of `feat/E33-profile-offer-1-print-profile-offer-chain` to
   `main`, then `infra/scripts/deploy.sh`.
4. ⏳ **NOT yet executed (controller-owned)** — Runtime **G-SMOKE** on `.190` (offer create/list/delete against the
   live `portal-content` volume + `ezop:ezop 664` owner/mode assertion).

This bookkeeping pass moved the card `review → done` on the **code side only** (gate green + review APPROVE); steps 3
and 4 have **not** happened and remain the controller's next actions.

**G-PUBLISH stays explicitly deferred** — this slice does not compile an offer's chain into the resolver intent
path, does not slice, and does not change the member selector (still on the 33.1/33.2 grid projection).

### File List

**New (backend):**
- `apps/api/app/modules/slicer/profile_offer.py` — engine (chain/offer model + dry validation) + storage
- `apps/api/tests/test_profile_offer_validate.py` — T1 validation-engine tests (14)
- `apps/api/tests/test_profile_offer_store.py` — T2 storage-layer tests (22)
- `apps/api/tests/test_admin_profile_offers.py` — T3 CRUD endpoint tests (25)

**Modified (backend):**
- `apps/api/app/modules/slicer/import_service.py` — added `publish_single` (single-file atomic publish,
  reuses `_stage_temp`); no change to `publish_pair` / `publish_intent` behavior
- `apps/api/app/modules/slicer/admin_router.py` — 5 offer routes + `_offer_dto` / gate / audit helpers
- `apps/api/app/modules/slicer/schemas.py` — offer DTOs (`ProfileChainRef`, `PrintProfileOffer`,
  list/create/update, `OfferVisibility`, `OfferValidationState`) + `field_validator` import
- `apps/api/app/core/audit.py` — comment-only: name the 3 `slicer_profile.offer_*` actions
- `apps/api/tests/test_slicer_worker.py` — route-surface fence extended for the 5 offer routes (AC-15)

**New (UX checkpoint — T4 / G-UXGATE):**
- `_bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md` — the `bmad-ux`/Sally
  admin offer-composition UX design checkpoint that satisfies G-UXGATE (AC-16)

**Modified (process):**
- `_bmad-output/implementation-artifacts/profile-offer-1-print-profile-offer-chain.md` — this record
  (Status + T4 done + T5/T6 unblocked + Dev Agent Record G-UXGATE disposition)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — offer row G-UXGATE note + new
  `ux-profile-offer-1-admin-offer-composition-ux-design: done` row

**New (FE — T5/T6, 2026-06-06):**
- `apps/web/src/modules/admin/ProfileOffersPage.tsx` — the admin offer composition surface
- `apps/web/src/modules/admin/hooks/useProfileOffers.ts` — list query (filters + cache topology)
- `apps/web/src/modules/admin/hooks/useCreateProfileOffer.ts` — create mutation + `offerRejectionCategory`
- `apps/web/src/modules/admin/hooks/useUpdateProfileOffer.ts` — patch mutation
- `apps/web/src/modules/admin/hooks/useDeleteProfileOffer.ts` — delete mutation
- `apps/web/src/routes/admin/profile-offers.tsx` — auth-gated sibling route
- `apps/web/src/modules/admin/ProfileOffersPage.test.tsx` — 8 vitest (fetch-intercept)
- `apps/web/src/modules/admin/profile-offers-i18n.test.ts` — 4 i18n parity tests
- `apps/web/tests/visual/admin-profile-offers.spec.ts` — 4 states × 4 projects Playwright spec
- `apps/web/tests/visual/__snapshots__/admin-profile-offers.spec.ts/*.png` — 16 baselines (baseline-reviewed)

**Modified (FE — T5/T6, 2026-06-06):**
- `apps/web/src/lib/api-types.ts` — offer TS types (`PrintProfileOffer`, `ProfileChainRef`, list/create/update,
  `OfferVisibility`, `OfferValidationState`, `ProfileOffersFilters`)
- `apps/web/src/modules/admin/AdminTabs.tsx` — `profile-offers` tab
- `apps/web/src/locales/en.json` + `pl.json` — `modules.admin.profileOffers.*` + `admin.tabs.profileOffers` (60 keys, parity)
- `apps/web/src/routeTree.gen.ts` — regenerated for the new route (additions only)
- `apps/web/tests/visual/api-stubs.ts` — added `stubProfileOffers`
- `apps/web/tests/visual/__snapshots__/{admin-users,admin-invites,admin-profiles,admin-profile-library,admin-dropdowns-tooltip-open}.spec.ts/*.png`
  — **collateral regen (44 PNGs):** adding the `profile-offers` tab to the shared `AdminTabs` shifts the tab bar on
  every admin page. Triaged per AGENTS.md "visual baseline triage before regen": the diff is **exclusively** the
  new tab (verified against the `admin-users-empty` diff — every other pixel identical), i.e. `stale-baseline`, NOT
  a deterministic regression. Regenerated + re-run stable (108 admin baselines green).

**NOT touched by the FE run:** `apps/api/**` (the FE consumes the existing T1–T3 backend contract verbatim — no
DTO/type/route change was required), `resolver.py` / `compatibility.py` / grid / library-write, Alembic, member
selector. G-PUBLISH not touched.

### Change Log

| Date | Change |
|---|---|
| 2026-06-06 | dev-story started; branch from `main @4e798ab`; sprint-status → in-progress. |
| 2026-06-06 | T1 engine + tests (RED→GREEN, 14). T2 storage + tests (22). T3 DTOs + 5 routes + tests (25). `publish_single` added; audit comment + route-surface fence extended. |
| 2026-06-06 | Backend determinism: full suite 1610 passed / 3 skipped; new suite 3× identical (61); ruff clean. |
| 2026-06-06 | FE (T4–T6) left BLOCKED on G-UXGATE (no UX checkpoint artifact); story kept in-progress, not "review". |
| 2026-06-06 | **T4 / G-UXGATE SATISFIED** — `bmad-ux`/Sally checkpoint `_bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md` authored (extends UX-PROFILE-1, SCP § 8). FE T5/T6 unblocked (AC-16 met; AC-17..20 designed). Sprint-status: offer-row G-UXGATE note + new `ux-profile-offer-1-admin-offer-composition-ux-design=done` row. Design-only; G-PUBLISH NOT authorized; no code/deploy/commit by the UX pass. |
| 2026-06-06 | **T5/T6 BUILT** (controller-resumed `bmad-dev-story`) — FE offer surface (`ProfileOffersPage`) + 4 CRUD hooks + `api-types` + en/pl i18n (60 keys, parity) + `AdminTabs` tab + `routes/admin/profile-offers.tsx` (+ `routeTree.gen.ts` regen) + vitest (8 + 4) + Playwright 16 baselines (4 states × 4 projects) + `stubProfileOffers`. Consumes the existing backend contract verbatim (no `apps/api/**` change). Verified: web vitest 607 / typecheck / lint / git diff --check clean; baselines stable + reviewed. Collateral: the shared `AdminTabs` gained the offer tab, so 44 admin baselines (users/invites/profiles/profile-library/dropdowns × 4 projects) were regenerated — triaged `stale-baseline` (diff is exclusively the new tab; re-run 108 green). **Status → review.** Remaining = controller-owned (check-all.sh, external review, ff-merge, G-SMOKE). G-PUBLISH still deferred; no commit/merge/deploy/live-smoke by the dev agent. |
| 2026-06-06 | **CONTROLLER CLOSEOUT (review → done, code-side).** Full `infra/scripts/check-all.sh` PASSED — RC=0, 16/16 stages green (apps/api ruff format+check, workers/render ruff format+check, apps/web typecheck + production build + lint + vitest, apps/api pytest, workers/render pytest, infra/scripts pytest, apps/web visual regression 444 passed / 24 skipped, settings-env-compose-diff, uv-lock-check ×2, local-env-secrets), log `.hermes/run-logs/profile-offer-1-controller-check-all-20260606_145028.log`. External review **Gemini CLI 0.45.2 → APPROVE** (no blockers / no important / no nits), log `.hermes/run-logs/profile-offer-1-gemini-review-20260606_145933.log` (Gemini initially tried an unavailable shell tool but still produced a read-only verdict; controller verified target state + gates separately — recorded honestly, not faked). G-PUBLISH still explicitly deferred. **Remaining controller-owned + NOT yet executed:** ff-merge → `main`, `infra/scripts/deploy.sh`, runtime G-SMOKE on `.190`. No commit/merge/deploy/live-smoke at this bookkeeping pass. |
