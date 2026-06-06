---
baseline_commit: 893bb97
story_key: profile-publish-1-compile-offer-chain-resolver-bridge
candidate_id: PROFILE-PUBLISH-1
supersedes_placeholder: PROFILE-OFFER-2  # the provisional name used in profile-offer-1-print-profile-offer-chain.md:535
epic: E33
initiative: 21
anchors_decision: AR  # architecture.md § Initiative 21 (proposed by this story; confirmed at G-ARCH)
realizes_gate: G-PUBLISH  # the backend half of the long-deferred publish/live-slicing gate
---

# Story PROFILE-PUBLISH-1: Compile a usable PrintProfileOffer's ProfileChain into a real resolver bundle + prove live slicing (G-PUBLISH backend bridge)

Status: **in-progress — backend bridge implemented locally 2026-06-06 on
`feat/E33-profile-publish-1-resolver-bridge`; targeted backend gates green. G-ARCH SATISFIED (Decision AR =
option b, chain-addressed resolve-tail; Gemini architecture review APPROVE 2026-06-06), G-DEVGO SATISFIED by
operator "możemy lecieć z PUBLISH" 2026-06-06, and G-DATA SELECTED (offer
`561d9ea327e143da9bfcc1031cda8077` / catalog STL hash
`282d26c1660c41b30d15b293b5c92bfe494ab62d76350009ceba55e714774b7f`)**. No deploy, no production write, no live
smoke, and no commit are authorized in this dev-story run; controller owns review/merge/deploy/live smoke. FE
publish controls, full `check-all.sh`, contracted external review, merge/deploy, and live smoke remain open.

<!--
  Authored by the repo-local BMAD author of record (Claude Opus 4.8, 2026-06-06) in the bmad-create-story [CS]
  shape, following the vanilla-first routing and the exact convention of PROFILE-LIB-1 (Decision AM) and
  PROFILE-OFFER-1 (Decision AN): each E33 slice is a story that anchors a new architecture Decision, appends an
  epics.md story section, adds a sprint-status row, and is gated on G-DEVGO + slice-specific gates.

  WHY A STORY, NOT A CORRECT-COURSE: G-PUBLISH is NOT an unplanned scope change. It is the explicitly-recorded
  next slice — SCP-2026-06-06-epic33 § 3.4 ("ProfileChain — the compiled-intent path the existing resolver/worker
  already consumes"), § 3.5, § 6 ("THEN ... a representative compiled chain that compiles INTO the existing
  resolver intent path so the resolver/worker/bundle_hash are preserved"), § 10 ("The corrected model is designed
  to compile into the existing resolver intent path, so the resolver, bundle_hash, append-only stores, and
  provenance snapshots remain invariants"); architecture Decision AN ("real resolver publication / live slicing is
  G-PUBLISH — a later slice"); profile-offer-1.md:533-539 (G-PUBLISH gate, "needs its own slice — provisionally
  PROFILE-OFFER-2 — an operator go, and likely a deploy/RW smoke"). The "never touches resolve()/bundle_hash"
  invariant was scoped IN THOSE SLICES (LIB-1/OFFER-1) with G-PUBLISH named as the graduation. So a new story
  anchoring Decision AR is the convention — no CC needed.

  THIS SLICE IS THE FIRST E33 SLICE TO LEGITIMATELY TOUCH THE RESOLVE / BUNDLE / SLICE PATH. That is a real
  escalation over LIB-1/OFFER-1 (which were additive, api-side, deploy-clean). Consequences recorded below:
  SW-DEPLOY-1 IS triggered (apps/api/app/modules/slicer/** change + the slicer worker consumes the new bundle);
  a live .190 LIVE-SLICING G-SMOKE is a deploy-GO precondition; external review is high-stakes (Gemini default,
  Codex fallback warranted for resolver/slice-path + data-integrity adjacency).

  DELIBERATELY NARROW. This slice proves the BACKEND publish bridge + one real live slice/estimate over ONE usable
  offer. It does NOT change the member selector (decision recorded below — member offer surface is a follow-on
  PROFILE-PUBLISH-2). The shipped 33.1/33.2 fixed grid stays the transitional compiled-intent projection that
  STILL feeds the member selector + estimates; no forced migration; no member-reachable change.

  Source artifacts (verified read 2026-06-06):
    - SCP sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md — § 3.4 (ProfileChain = the
      compiled bundle the resolver consumes), § 3.5 (PrintProfileOffer carries a representative ProfileChain for
      estimate slicing), § 3.7 (member request-flow is SEPARATE, must not block), § 4 (grid = transitional
      compiled-intent projection feeding the member selector; KEPT, coexist, NO forced migration), § 6 ("THEN"
      PROFILE-OFFER → offers compile into the existing resolver intent path; deferred register), § 7 (preserved
      33.2 safety foundations incl. resolve() reused verbatim single-SoT + atomic publish + live-RW-smoke
      methodology AI-1/AI-4), § 10 (impact — resolver/bundle_hash/append-only/provenance are invariants).
    - epics.md § Initiative 21 (Story PROFILE-OFFER-1 section + this PROFILE-PUBLISH-1 section appended this run).
    - architecture.md § Initiative 21 — Decision AN (offer/chain layer, shipped; names G-PUBLISH as the later
      slice); Decision AR (proposed by this story).
    - Shipped PROFILE-OFFER-1 (profile-offer-1-print-profile-offer-chain.md, done @741ce7b, live .190 G-SMOKE
      PASSED) — the offer/chain data model + admin CRUD + dry validation this story BUILDS ON. profile_offer.py
      (ProfileChain, validate_chain/evaluate_offer, store_offer/list_offers/read_offer/delete_offer/offer_path,
      offers/<offer_id>.json sidecar). G-PUBLISH was explicitly left out of OFFER-1.
    - Code read (read-only, 2026-06-06): apps/api/app/modules/slicer/resolver.py (resolve() 234-375 merge →
      normalize_for_cli → required-key check → CLI smoke → compute_bundle_hash → persist snapshot+bundle;
      resolve_intent() 378-407 settings-wired wrapper; compute_bundle_hash() 74-111; VendoredProfileSource 114-202
      incl. intent_path/system_tree_hash); bundle_store.py (BundleStore.write_bundle 61-70 / write_snapshot 83-88,
      append-only idempotent os.link first-write-wins, hash-fanout layout); estimate_store.py (EstimateStore.write
      79-99 append-only, dedup); enqueue.py (enqueue_slice_estimate 42-68 → arq:slicer, deduped job id
      slice:<stl_hash>:<bundle_hash>); worker.py / worker_job.py (slice_estimate(stl_hash, bundle_hash) → load
      bundle → --info manifold pre-check → headless Orca slice → parse → estimate store; parse-and-discard g-code);
      router.py (GET /api/estimates member read keyed by resolved bundle_hash → EstimateView); estimate_read.py
      (EstimateResolver.resolve_preset / SettingsEstimateResolver); compatibility.py (MATERIAL_TIER_COMPATIBILITY
      grid SoT — NOT touched); profile_library.py (read_block / block_path / library_root — the publish step is
      the FIRST legitimate reader of the raw block BODY .json, not just the .manifest.json); import_service.py
      (publish_pair / publish_single atomic write + ezop:ezop 664 metadata preservation incl. 221bbe1 fresh-dir
      fix); core/audit.py (slicer_profile entity_type + record_event); config.py (slicer_vendored_profiles_dir,
      slicer_bundle_store_dir, orca_version, slicer worker timeouts/concurrency); docs/operations.md § SW-DEPLOY-1
      (overlay rebuild auto-scoped off apps/api/** changes + worker smoke, fatal-on-fail).

  GATE NOTE: "draft" = the slice is scoped + Decision AR is now G-ARCH-confirmed as option (b), and G-DEVGO/G-DATA are now satisfied; it is ready-for-dev. Do NOT
  flip this row to ready-for-dev or start dev-story before those three close.
-->

## Story

As an **admin/operator of the 3d-portal**,
I want **to PUBLISH a single, fully-`usable` `PrintProfileOffer` — compiling its embedded `ProfileChain` (three
library blocks: machine + process + filament) into a real resolver-produced, byte-pinned Orca bundle with a real
`bundle_hash`, persisted into the existing append-only bundle store, and then to run ONE live slice/estimate over
ONE designated catalog STL so the offer is proven to produce a real time/filament estimate** —
so that **the long-deferred G-PUBLISH bridge between the canonical offer/chain layer and the real
resolver/worker/`bundle_hash`/estimate path exists and is proven end-to-end over one offer, WITHOUT changing the
member-facing selector (which keeps consuming the transitional 33.1/33.2 grid projection unchanged), WITHOUT
touching the grid `intents/`/`system/` trees, and WITHOUT a forced migration — turning a published offer into a
member-facing choice is an explicit, separately-gated follow-on (PROFILE-PUBLISH-2).**

This is the **backend half of the explicitly-deferred G-PUBLISH gate** named in SCP § 6 and architecture Decision
AN (provisionally "PROFILE-OFFER-2"; renamed **PROFILE-PUBLISH-1** for clarity). It anchors architecture **Decision
AR**. It is deliberately **publish-bridge + one live-slice proof + admin-only observation** — it is **NOT** a member
offer selector, **NOT** an N×M editor, **NOT** a raw Orca JSON viewer, **NOT** a Spoolman mutation, **NOT** a member
order/request flow, and it does **NOT** alter the `bundle_hash` input order or the append-only store layout.

## Decision confirmed by G-ARCH (Decision AR: publish bridge mechanism)

> **This is the load-bearing open decision. The architect + operator must pick before the dev-story cycle.**

An offer carries a `ProfileChain` = three library `block_id`s (machine/process/filament), a `label`,
`compatible_material_categories`, visibility/default. The resolver today consumes an **intent triple** read from
`<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` (a `PrintIntentPreset` keyed by the grid
coordinate). An offer has **no** `(printer_ref, material_class, quality_tier)` coordinate. So "compile the chain
into resolver input" has two candidate mechanisms:

- **Option (a) — intent-coordinate publish (NOT recommended).** Publishing an offer writes/overlays an
  `intents/<printer>/<material>/<tier>.json` triple derived from the chain's three blocks. **Rejected as the
  default** because: an offer has no grid coordinate, so this forces a *synthetic/assigned* `(printer, material,
  tier)` onto it, and writing into the grid `intents/` tree risks colliding with / overwriting the **transitional
  grid projection that still feeds the member selector** — a direct violation of SCP § 4 (grid KEPT, coexist, NO
  forced migration) and of the OFFER-1/LIB-1 fence ("never touch the `intents/`/`system/` trees").

- **Option (b) — chain-addressed resolve-tail (RECOMMENDED).** Add a new resolver entry that resolves a
  `ProfileChain` **directly from its three library block bodies**, reusing the existing `resolve()` tail
  **verbatim** (inheritance-merge → `normalize_for_cli` → required-key schema check → CLI smoke validation →
  `compute_bundle_hash` → persist `SlicerProfileBundle` + `SourceProfileSnapshot` append-only), **without** reading
  or writing the `intents/`/`system/` (grid) trees and **without** minting a synthetic grid coordinate. Faithful to
  SCP § 3.4/§ 6/§ 10 — "the existing resolver intent **path**" means the resolve→bundle→slice **machinery** (single
  SoT), not the grid **directory**; `bundle_hash` and the append-only stores are preserved exactly; the offer
  publish stays **disjoint** from the grid intents tree (consistent with the offer sidecar being disjoint from
  `system/`/`intents/`/`library/`). This is the minimal bridge that keeps the grid untouched.

**G-ARCH result: option (b) confirmed.** Gemini architecture review (log `.hermes/run-logs/g-publish-gemini-architect-20260606_210937.log`) returned **APPROVE**: chain-addressed resolve-tail preserves the grid invariant, reuses the load-bearing resolve/bundle machinery, and avoids synthetic coordinate debt. The Acceptance Criteria below remain written against (b).

## Decision recorded (NOT deferred silently) — the member selector stays OUT of this slice

**The member-facing selector does NOT change in PROFILE-PUBLISH-1.** Rationale (challenged for overreach):
1. SCP § 3.7 marks the member material/spool/request flow as **separate future work that must not block** profile
   work; SCP § 4 keeps the **grid projection feeding the member selector** with no forced migration.
2. A member-facing offer selector carries its own load-bearing contracts — **NFR21-NO-422-1** (no member-reachable
   resolve 422), **FR21-SELECTOR-1** (member surface), and a **UX gate** (offer-as-member-choice is member-facing
   relationship UI). Folding it in would entangle the live-slicing proof with member-UX risk and blow the slice.
3. The minimal surface needed to *prove* the bridge is **admin-only observation** (publish action + a published-
   state/estimate readout on the existing admin offer detail). That is in scope; a member offer selector is not.

**Safe default preserved:** until the follow-on **PROFILE-PUBLISH-2 (member offer surface)** lands, members keep
seeing exactly the shipped 33.1/33.2 grid projection. The operator MAY, at dev-go, choose to fold a minimal member
readout into a follow-on — but not into this slice.

## Acceptance Criteria

> ACs are written against **Decision AR option (b)**. AC-1..AC-7 are the backend bridge; AC-8..AC-11 the CRUD/
> observation surface; AC-12..AC-16 cross-cutting (smoke, deploy, provenance, scope fence). Final ACs + task lists
> are re-confirmed by `bmad-create-story` at dev-entry after G-ARCH/G-DEVGO/G-DATA close.

### Backend — the publish/compile bridge (`slicer/profile_publish.py` — new orchestrator)

1. **AC-1 — New additive publish orchestrator; grid + library-write + offer-validation engines untouched.** A new
   `apps/api/app/modules/slicer/profile_publish.py` orchestrates the publish bridge. It **reuses** the `resolve()`
   tail verbatim (single SoT — no second resolution path; SCP § 7) and the append-only `BundleStore`/
   `EstimateStore` + `enqueue_slice_estimate` as-is. It does **NOT** edit `compatibility.py`, the `intents/`/
   `system/` (grid) trees, the 33.1 read endpoint, the 33.2 import path, the `bundle_hash` input order, the
   append-only store layout, or the PROFILE-OFFER-1 `profile_offer.py` validation/CRUD bodies (it **reads**
   `read_offer`/`validate_chain` and **adds** a publish-state field — see AC-5). A test asserts no mutation of the
   grid/compat/store-layout surfaces (`git diff` body-unchanged, mirroring the OFFER-1/LIB-1 fences).

2. **AC-2 — Resolve a ProfileChain directly (Decision AR option b), reusing the resolve tail verbatim.** A new
   entry (`resolve_chain(...)` in `resolver.py`, or an orchestration in `profile_publish.py` that calls the
   existing resolver primitives) takes the offer's three library `block_id`s, reads each block's **raw body**
   (`<root>/library/<type>/<block_id>.json` — the publish step is the FIRST legitimate reader of the raw block
   body; OFFER-1 validation read only the `.manifest.json`), and runs the SAME pipeline `resolve()` runs for an
   intent triple: inheritance-merge → `normalize_for_cli` → required-key schema check → CLI smoke validation →
   `compute_bundle_hash(machine, process, filament, orca_version, overrides_ref=None)`. It reads **neither** the
   `intents/` **nor** mints a grid coordinate. A classified failure (e.g. `cli_rejected_profile`, missing required
   keys) maps to a structured publish-reject reason — **nothing is persisted/published on failure**. (SCP § 3.4;
   § 7 resolve-reused-verbatim.)

3. **AC-3 — Real `bundle_hash` + append-only persistence (NFR21-PROVENANCE-1 preserved).** On a successful
   resolve, the produced `SlicerProfileBundle` (real `bundle_hash`) + its `SourceProfileSnapshot` are persisted via
   the existing `BundleStore.write_bundle` / `write_snapshot` — **append-only, idempotent, first-write-wins**
   (`os.link`). Publishing the same chain twice yields the **same** `bundle_hash` and a NO-OP store write
   (determinism). Publishing a DIFFERENT offer/chain **MUST NOT** perturb any unrelated already-persisted bundle's
   hash or bytes. A test asserts (a) re-publish is byte-stable/idempotent and (b) an unrelated bundle is
   byte-unchanged across a publish. (NFR21-PROVENANCE-1; `bundle_store.py` append-only contract.)

4. **AC-4 — Publish only a `usable` offer; gate order; structured rejects.** `POST /api/admin/profiles/offers/
   {offer_id}/publish` (AC-8) gate order: validated hex `offer_id` else **404**; offer absent else **404**;
   **re-run `validate_chain` at publish time** (read-time truth, never trust a stale stored state) — if `invalid`
   → **409/422 `offer_not_usable`** (structured reason categories from OFFER-1: `unknown_block`/`wrong_block_type`/
   `block_unusable`), if `requires_attention` → **409 `offer_requires_attention`** (publishing a flagged offer is
   blocked in this slice; resolving the flag is operator work), only `usable` proceeds → resolve+persist (AC-2,3) →
   enqueue ONE slice (AC-6) → set publish-state (AC-5) → audit (AC-7) → **200/202** with the publish result DTO. A
   resolve failure (AC-2) → **422 `chain_resolve_failed`** with the classified reason, **nothing published**.

5. **AC-5 — Offer publish-state marker (on the existing sidecar; atomic; no DB).** Publishing records, on the
   offer's `<root>/offers/<offer_id>.json` sidecar, an additive publish-state block: `published_bundle_hash`,
   `published_at`, `published_by`, `publish_state ∈ {published, unpublished}`, and the `source_snapshot_ref`. The
   write reuses the **shared atomic** `import_service.publish_single` + the **`ezop:ezop 664` owner/mode
   preservation** (incl. the `221bbe1` fresh-dir fix) — on ANY failure the sidecar is byte-identical and no temp
   remains. **No Alembic, no DB** (consistent with the slicer subsystem's on-disk/append-only posture; the offer
   sidecar already exists from OFFER-1). The sidecar schema bumps to `offer_manifest_version = "2"` (additive
   publish-state; v1 sidecars read forward as `publish_state = unpublished`). (SCP § 7 atomic-publish +
   permission-preservation; OFFER-1 AC-3/AC-7 reused.)

6. **AC-6 — Enqueue exactly ONE live slice/estimate over ONE designated STL.** Publish enqueues
   `enqueue_slice_estimate(arq_pool, source_stl=<designated STL>, bundle_hash=<published>, stl_cache)` onto
   `arq:slicer` (deduped job id `slice:<stl_hash>:<bundle_hash>`), which runs the existing
   `slice_estimate(stl_hash, bundle_hash)` worker job → `--info` manifold pre-check → headless Orca slice → g-code
   parse-and-discard → `EstimateStore.write` (append-only). The STL is the **operator-designated G-DATA STL**
   (a real catalog STL on `.190`) — **not** synthesized. The slice is a real estimate, not a stub. (Worker path:
   `enqueue.py` → `worker_job.py`; estimate cache `estimate_store.py`.)

7. **AC-7 — Audit publish/unpublish (NFR21-OBS-1), reusing `slicer_profile`; leak-fenced.** Publish emits
   `record_event(action="slicer_profile.offer_publish", entity_type="slicer_profile", entity_id=<offer_id-as-UUID>,
   actor_user_id=<admin>, after={published_bundle_hash, machine/process/filament block_ids, designated_stl_hash,
   estimate_job_id})`; unpublish (AC-9) emits `.offer_unpublish`. `slicer_profile` is **already** in
   `KNOWN_ENTITY_TYPES` — only the audit.py comment block gains a one-line extension naming the two new actions (no
   registry add). The audit payload carries **no Orca body, no g-code, no filesystem path** — only the
   `bundle_hash`, hash-prefix ids, and block_ids. (NFR21-OBS-1; OFFER-1 audit shape reused.)

### Backend — publish/unpublish/observe endpoints (on the existing `slicer/admin_router.py`)

8. **AC-8 — `POST /api/admin/profiles/offers/{offer_id}/publish`.** Admin-gated (`current_admin`), absent from
   `_PUBLIC_ROUTES`, CSRF automatic. Body: optional `{ stl_hash }` (the designated STL; default = the
   operator-configured G-DATA catalog STL). Runs AC-4 gate order; returns the publish result DTO (AC-11). The
   route-enforcement gate passes with **no** `_PUBLIC_ROUTES` edit; the `test_slicer_worker.py` admin-router
   route-surface fence is extended by the two sanctioned routes. (NFR21-AUTH-1.)

9. **AC-9 — `POST /api/admin/profiles/offers/{offer_id}/unpublish` — rollback-safe.** Sets the offer's
   `publish_state = unpublished` (atomic sidecar re-write, AC-5) and audits `.offer_unpublish`. It does **NOT**
   delete the persisted bundle/snapshot/estimate (the append-only stores are never mutated — un-publish is a
   marker flip, re-publish is idempotent via `bundle_hash`). `404` when the offer is absent; idempotent (un-
   publishing an unpublished offer is a `200` NO-OP, not `500`). This is the offer-scoped rollback primitive.

10. **AC-10 — Admin-only estimate observation (reuse the existing read path; no new member surface).** The
    published bundle's estimate is observable by reusing the existing `GET /api/estimates` read keyed by the
    published `bundle_hash` (+ the designated `stl_hash`) → `EstimateView` (status absent/queued/fresh/stale/
    failed + time/filament_g/cost). **No member selector change, no new member endpoint.** If a thin admin
    convenience is wanted, it is an admin-gated read returning the same curated `EstimateView` for the offer's
    published bundle — **curated numbers + `bundle_hash` only, NO raw Orca body / g-code / path**.

11. **AC-11 — Publish DTOs (`extra="forbid"`, no raw body).** New `slicer/schemas.py` DTOs: `OfferPublishResult`
    (`offer_id`, `published_bundle_hash`, `publish_state`, `published_at`, `estimate_job_id`,
    `estimate: EstimateView | null`) and the publish request body. Every DTO is `ConfigDict(extra="forbid")` and
    carries **no raw Orca key body, no filesystem path, no g-code** (the OFFER-1/LIB-1/33.2 leak fence; a negative-
    assertion test mirrors it). Reuse the existing `EstimateView` for the estimate echo.

### Frontend — minimal admin publish/observe (small; NO member surface)

12. **AC-12 — Minimal admin publish/observe surface (additive to the shipped offer detail).** On the existing
    admin `ProfileOffersPage` offer detail (shipped in OFFER-1), add: a **Publish** action (enabled only for a
    `usable` offer; disabled-with-reason otherwise), an **Unpublish** action, a **published-state** indicator
    (`published_bundle_hash` prefix + `published_at`), and a **published-estimate readout** (status + time/grams
    via the AC-10 read). It **fails closed/visible** on error. New TanStack hooks `usePublishOffer()` /
    `useUnpublishOffer()` (`api()`, `retry: false`, invalidate `["admin","profile-offers"]`). **No member-facing
    surface, no selector change, no raw Orca JSON.** New i18n keys under `modules.admin.profileOffers.publish.*`
    in **both** en.json + pl.json (parity + diacritics; `bundle_hash`/numbers render as data, untranslated).
    *(This FE may be split to a small T5 after the backend+smoke prove the bridge; the load-bearing proof is the
    backend + the live smoke, not the FE.)*

### Cross-cutting — live smoke, deploy, provenance, determinism, scope fence

13. **AC-13 — Live `.190` LIVE-SLICING G-SMOKE is a deploy-GO precondition (33.2 AI-1/AI-4 methodology).** After
    contracted-review APPROVE + full gates + deploy, a live smoke on `.190` over ONE operator-designated usable
    offer + ONE designated catalog STL asserts: (a) `publish` → a real `SlicerProfileBundle` persisted with a real
    `bundle_hash`, **deterministic/idempotent** on re-publish; (b) a real slice runs on `arq:slicer` and produces a
    real `EstimateView` (non-null time + filament_g) cached in the estimate store; (c) the offer sidecar publish-
    state lands `ezop:ezop 664`; (d) the grid `intents/`/`system/` trees + an unrelated bundle are **byte-
    unchanged**; (e) **no member-reachable change** (the member selector still serves the grid projection); (f) no
    Orca body / g-code / path leaked in any DTO/log/audit. Emits a `PROFILE_PUBLISH_SMOKE_OK` marker (RC=0).
    **NOT run by this card** — operator/runtime gate.

14. **AC-14 — SW-DEPLOY-1 IS triggered (escalation vs LIB-1/OFFER-1).** This slice changes
    `apps/api/app/modules/slicer/**` (the resolve entry + publish orchestrator) and the **slicer worker consumes
    the newly-published bundle** to slice. Per `docs/operations.md § SW-DEPLOY-1`, the overlay
    `portal-slicer-worker:0.1.0` is rebuilt + smoked (importlib presence, Settings validation, Orca reachability,
    functional smoke) as a **fatal-on-fail** step of `deploy.sh`. A test/spec note records that this is the first
    E33 slice to trip SW-DEPLOY-1 (LIB-1/OFFER-1 were deploy-clean). `SKIP_SLICER_WORKER=1` only if the overlay is
    not deployed on the host.

15. **AC-15 — Determinism gate.** 3× consecutive identical pytest + vitest pass counts; `ruff check`/`format`,
    `npm run typecheck`, `npm run lint -- --max-warnings=0`, `git diff --check` clean; full
    `infra/scripts/check-all.sh` green before any ff-merge. (NFR21-DETERMINISM-1.)

16. **AC-16 — Scope fence (what this story does NOT do).** **No** member selector / member offer surface / NO-422
    contract change (→ PROFILE-PUBLISH-2; safe default: member selector keeps consuming the 33.1/33.2 grid
    projection — SCP § 3.7/§ 4). **No** write to the grid `intents/`/`system/` trees and **no** synthetic grid
    coordinate minted (Decision AR option b keeps the publish disjoint). **No** change to the 33.1 read, the 33.2
    import, `compatibility.py`, the `bundle_hash` input order, or the append-only store **layout** (only additive
    writes through the existing append-only contracts). **No** N×M editor, **no** raw Orca JSON viewer/editor.
    **No** Spoolman read/write/mutation and **no** concrete-filament/spool override publication (the offer's
    optional override layer stays deferred — publish uses the chain's filament block as-is). **No** Alembic / DB
    (publish-state on the existing on-disk offer sidecar; bundles/estimates in the existing append-only stores).
    **No** broad member order/request flow. (SCP § 6/§ 9 deferred register.)

## Tasks / Subtasks (sketched; finalized by bmad-create-story after G-ARCH/G-DEVGO/G-DATA)

- [x] **T0 — G-ARCH: confirm Decision AR bridge mechanism (a vs b).** Gemini architecture review APPROVE (2026-06-06, `.hermes/run-logs/g-publish-gemini-architect-20260606_210937.log`); Decision AR confirmed as option (b), chain-addressed resolve-tail; architecture.md Decision AR flipped proposed → accepted; ACs remain
      if (a). **BLOCKS all code.**
- [x] **T1 — Chain-addressed resolve + publish orchestrator (AC-1,2,3)** — new `slicer/profile_publish.py` +
      `resolve_chain` entry; `tests/test_profile_publish_resolve.py`. RED first: resolve a usable chain →
      deterministic `bundle_hash`; a chain that fails CLI smoke → classified reject, nothing persisted; re-publish
      idempotent; unrelated bundle byte-stable. Assert the resolve tail is REUSED (no second resolution path) and
      the `intents/`/`system/` trees are never read/written.
- [x] **T2 — Publish-state storage on the offer sidecar (AC-5)** + `tests/test_profile_publish_store.py` — additive
      v2 publish-state via `publish_single` atomic + owner/mode preservation; injected-failure leaves sidecar byte-
      identical + no temp; v1 sidecar reads forward as unpublished.
- [x] **T3 — Publish/unpublish/observe endpoints (AC-4,8,9,10,11)** — extend `slicer/admin_router.py` +
      `slicer/schemas.py` + `tests/test_admin_profile_publish.py`. Gate order; 404/409/422 rejects; idempotent
      unpublish; reuse `GET /api/estimates`; route-enforcement green with no `_PUBLIC_ROUTES` edit; route-surface
      fence extended (+2 POST); leak-fence negative assertion.
- [x] **T4 — Enqueue + worker integration + audit (AC-6,7)** — wire `enqueue_slice_estimate` over the designated
      STL; audit `.offer_publish`/`.offer_unpublish` (comment-only audit.py extend); test the enqueue contract +
      audit shape (fakeredis / stubbed pool).
- [ ] **T5 — Minimal admin publish/observe FE (AC-12)** — `usePublishOffer`/`useUnpublishOffer` + Publish/Unpublish
      actions + published-state + estimate readout on the offer detail; en/pl i18n parity; vitest + (if a new
      visual state) baselines. *NO member surface.* (May be split as a follow-on if the operator wants backend+smoke
      proof first.) **Not touched in this backend-only pass per operator scope.**
- [ ] **T6 — Determinism + SW-DEPLOY-1 awareness + self-review (AC-14,15)** — 3× pytest/vitest; full check-all.sh;
      record SW-DEPLOY-1 trigger in the deploy note. **Partial only:** self-review + targeted backend gates green;
      full `check-all.sh` and 3x determinism remain controller closeout work.
- [ ] **T7 (controller-owned) — review + ff-merge + deploy (SW-DEPLOY-1) + live `.190` LIVE-SLICING G-SMOKE
      (AC-13).** External review Gemini-default / Codex-fallback (resolver/slice-path + data-integrity adjacency =
      high-stakes); deploy with the slicer-worker overlay rebuild; the AC-13 smoke as the deploy-GO precondition.

## Dev Notes

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] § A — existence checklist)

1. **Resolve machinery (REUSE VERBATIM — single SoT):** `resolver.py` `resolve()` (234-375) tail = merge →
   `normalize_for_cli` → required-key check → CLI smoke → `compute_bundle_hash` (74-111) → persist. `resolve_chain`
   reuses this tail; it does **not** add a second resolution path (SCP § 7).
2. **Append-only stores (REUSE — never re-implement):** `bundle_store.py` `write_bundle` (61-70) / `write_snapshot`
   (83-88) idempotent first-write-wins `os.link`; `estimate_store.py` `write` (79-99). Publishing a new bundle is
   additive; an unrelated bundle is byte-stable (NFR21-PROVENANCE-1).
3. **Enqueue + worker (REUSE):** `enqueue.py` `enqueue_slice_estimate` (42-68) → `arq:slicer`, deduped
   `slice:<stl_hash>:<bundle_hash>`; `worker_job.py` `slice_estimate(stl_hash, bundle_hash)`. The publish enqueues
   exactly one job over the designated STL.
4. **Estimate read (REUSE — admin observation):** `GET /api/estimates` (router.py) + `EstimateResolver` /
   `EstimateView` — keyed by the published `bundle_hash`. No new member surface.
5. **Library raw-body read (REUSE/EXTEND):** `profile_library.read_block` / `block_path` — the publish step is the
   FIRST legitimate reader of the raw block **body** `.json` (OFFER-1 read only the `.manifest.json`). Confirm the
   body is the verbatim Orca block usable by the inheritance-merge.
6. **Offer read + dry validation (REUSE):** `profile_offer.read_offer` / `validate_chain` — re-validate at publish
   time (read-time truth). Add the publish-state field via `store_offer`/`publish_single`; do not reshape the
   OFFER-1 validation bodies.
7. **Atomic single-file write + metadata preservation (REUSE):** `import_service.publish_single` (added in OFFER-1)
   + the `ezop:ezop 664` owner/mode preservation (incl. the `221bbe1` fresh-dir fix). The publish-state write reuses
   it.
8. **Audit (REUSE, comment-only extend):** `core/audit.py` — `slicer_profile` already in `KNOWN_ENTITY_TYPES`; add
   `.offer_publish`/`.offer_unpublish` as a one-line comment extension (mirrors OFFER-1's `.offer_create` etc.).
9. **Admin router (EXTEND):** `slicer/admin_router.py` — add the two publish routes on the same `router`;
   `current_admin`; no `_PUBLIC_ROUTES` edit; CSRF automatic.
10. **Config (REUSE):** `config.py` `slicer_vendored_profiles_dir`, `slicer_bundle_store_dir`, `orca_version`,
    slicer worker timeouts/concurrency. The designated G-DATA STL is operator data, not a new config slot unless a
    default catalog STL ref is wanted (magic-constant discipline below).
11. **SW-DEPLOY-1 (RESPECT — now TRIGGERED):** `docs/operations.md § SW-DEPLOY-1` — `apps/api/**` change + the
    worker consuming the new bundle ⇒ overlay rebuild + worker smoke, fatal-on-fail. First E33 slice to trip it.
12. **Compatibility SoT (DO NOT TOUCH):** `compatibility.py` `MATERIAL_TIER_COMPATIBILITY` is the **grid**
    projection's gate — this slice does not consume or edit it. The offer-chain compatibility was already validated
    dry in OFFER-1; publish re-validates the chain, not the grid tier-map.

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **`offer_manifest_version = "2"` (AC-5):** points to the publish-state sidecar contract v2 (additive over the
  OFFER-1 v1). A v1 sidecar (no publish-state) reads forward as `publish_state = unpublished`. Bumping is a future
  migration; not the library-manifest or intent-manifest version.
- **`bundle_hash` input order (AC-3):** points to the Init 20 / `compute_bundle_hash` contract
  `machine ∥ process ∥ filament ∥ orca_version [∥ overrides_ref]` — **reused unchanged** (NFR21-PROVENANCE-1).
  Publishing an offer with no concrete override passes `overrides_ref=None` (backward-compatible, hash unchanged).
- **Designated G-DATA STL:** points to ONE real catalog STL on `.190` (operator-confirmed), not a synthesized
  fixture for the live smoke; unit/integration tests drive the enqueue contract with a stubbed pool + a bench STL.
- **One slice per publish (AC-6):** points to "prove the bridge over ONE offer" — not a batch re-slice of all
  estimates (that is the recompute/invalidation path, out of scope).

### Architecture / constraints

- **Decision AR** (architecture.md § Initiative 21, **accepted** by G-ARCH 2026-06-06; option b): the
  **offer-chain publish bridge** — a chain-addressed resolve entry (option b) reusing the `resolve()` tail verbatim
  to produce a real `bundle_hash`, persisting append-only, recording an additive publish-state on the offer
  sidecar, and enqueuing one live slice/estimate — **without** touching the grid `intents/`/`system/` trees or the
  `bundle_hash` input order. Consumes Decision AM (library bodies) + Decision AN (offer/chain). Decisions AK/AL (the
  grid) remain the transitional compiled-intent projection feeding the member selector — **untouched**.
- Preserves Init 20 `bundle_hash` / `source_system_tree_hash` / append-only invariants (NFR21-PROVENANCE-1):
  publishing is additive to the append-only stores; an unrelated bundle is byte-stable; the input order is
  unchanged.
- NFR21-NO-422-1 holds trivially: no new member-reachable resolve (the member selector is unchanged).
- Backend rules: `Annotated` DI, `current_admin` default-value dep, namespaced logger, no `os.environ`, ruff
  `E,F,W,I,B,UP,SIM,RUF` line-length 100, TDD red→green. Frontend rules: `import type`,
  `noUncheckedIndexedAccess`, `@/*` alias, network via `api()` only, i18n mandatory, no inline hex, ESLint
  `--max-warnings=0`, `afterEach(cleanup)`.

### Project Structure Notes

- **New backend:** `apps/api/app/modules/slicer/profile_publish.py` (publish orchestrator + chain-addressed
  resolve, or a `resolve_chain` entry in `resolver.py` — G-ARCH/dev's choice within option b) +
  `tests/test_profile_publish_resolve.py` + `tests/test_profile_publish_store.py` +
  `tests/test_admin_profile_publish.py`. **Edited:** `slicer/admin_router.py` (2 publish routes),
  `slicer/schemas.py` (publish DTOs), `slicer/profile_offer.py` (additive publish-state field on store/read — body-
  preserving), `core/audit.py` (comment-only), `tests/test_slicer_worker.py` (route-surface fence +2 POST).
  Possibly `resolver.py` (the new `resolve_chain` entry — the FIRST E33 edit to resolver.py).
- **New/edited FE (T5, minimal):** `apps/web/src/modules/admin/hooks/usePublishOffer.ts` + `useUnpublishOffer.ts`;
  edited `ProfileOffersPage.tsx` (publish/unpublish actions + published-state + estimate readout), `en.json`/
  `pl.json`, `lib/api-types.ts`, and (if a new visual state) `apps/web/tests/visual/`.
- **No** `_PUBLIC_ROUTES` edit, **no** Alembic, **no** new `config.py` slot (reuses existing slicer settings),
  **no** `compatibility.py`/grid/`intents`-`system`-tree change. **SW-DEPLOY-1 IS triggered** (apps/api/** +
  worker-consumed bundle).

### References

- SCP: [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md]
  — § 3.4 (ProfileChain = compiled bundle the resolver consumes), § 3.5 (offer carries a representative chain for
  estimate slicing), § 3.7 (member request-flow separate — must not block), § 4 (grid = transitional projection
  feeding the member selector; coexist, no migration), § 6 ("THEN" — offers compile into the existing resolver
  intent path; deferred register), § 7 (resolve reused verbatim + atomic publish + live-RW-smoke methodology),
  § 10 (resolver/bundle_hash/append-only/provenance are invariants).
- Epics: [Source: _bmad-output/planning-artifacts/epics.md § Initiative 21] (Story PROFILE-PUBLISH-1 section
  appended by this run).
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md § Initiative 21] — Decision AR (accepted
  by G-ARCH 2026-06-06, option b); Decisions AM (library) + AN (offer/chain) consumed; AK/AL (grid projection) untouched.
- Shipped: profile-offer-1-print-profile-offer-chain.md (done @741ce7b, live .190 G-SMOKE PASSED — the offer/chain
  data model + admin CRUD + dry validation this story builds on; G-PUBLISH explicitly left out there);
  `apps/api/app/modules/slicer/{resolver.py, bundle_store.py, estimate_store.py, enqueue.py, worker.py,
  worker_job.py, estimate_read.py, profile_offer.py, profile_library.py, import_service.py, admin_router.py,
  schemas.py, compatibility.py}`, `apps/api/app/core/audit.py`, `apps/api/app/modules/slicer/router.py`
  (GET /api/estimates), `docs/operations.md § SW-DEPLOY-1`.
- Memory: [[feedback_scp_pre_enumeration_phase]] — pre-enumeration + magic-constant discipline applied above.

### Operator / data / config gates (surface BEFORE dev-go)

- **G-ARCH — SATISFIED 2026-06-06.** Gemini architecture review APPROVE confirmed Decision AR option (b):
  chain-addressed resolve-tail. Conditions recorded before dev: pass the three raw library block bodies cleanly
  into the resolve tail without fabricating `intents/` paths; preserve provenance with block IDs/manifest versions;
  keep the `bundle_hash` input sequence byte-identical.
- **G-DEVGO — SATISFIED 2026-06-06.** Operator said: "możemy lecieć z PUBLISH". This authorizes BMAD dev-story entry, but does not bypass review/deploy/smoke gates.
- **G-PUBLISH — REALIZED (backend half) by this story.** The long-deferred publish/live-slicing gate (recorded in
  OFFER-1/LIB-1 and Decision AN) is now sequenced as PROFILE-PUBLISH-1. It is no longer "deferred forever" — it is
  the active next E33 slice. The member-facing half (offer-as-member-choice) remains deferred to PROFILE-PUBLISH-2.
- **G-DATA — SATISFIED 2026-06-06 (controller-selected live candidates from `.190`).** Usable offer: `561d9ea327e143da9bfcc1031cda8077` (`Standard`, visible default, `validation_state=usable`, reasons `[]`). Designated real catalog STL: `282d26c1660c41b30d15b293b5c92bfe494ab62d76350009ceba55e714774b7f` at `/mnt/raid/3d-portal-content/models/018ae11f-5b83-4d9a-9cf7-09e603f07553/files/46e58081-e697-421a-9dcf-9c456d9aac91.stl` (235884 bytes). Synthetic-substitution remains forbidden for the live smoke; unit/integration tests run against bench fixtures + a stubbed arq pool without it.
- **SW-DEPLOY-1 — TRIGGERED (deploy gate).** `apps/api/**` change + the worker consuming the published bundle ⇒
  overlay `portal-slicer-worker:0.1.0` rebuild + functional smoke, fatal-on-fail (`docs/operations.md`).
- **G-SMOKE — live `.190` LIVE-SLICING smoke (deploy-GO precondition, AC-13).** Run only after contracted-review
  APPROVE + full gates + deploy. NOT authorized / NOT run by this card.

## Dev Agent Record

### Agent Model Used

Codex (GPT-5), BMAD `bmad-dev-story` execution under Laura supervision.

### Debug Log References

- 2026-06-06 — RED first:
  `cd apps/api && uv run pytest tests/test_profile_publish_resolve.py tests/test_profile_publish_store.py tests/test_admin_profile_publish.py -q`
  failed during collection because `resolve_chain` / `profile_publish` did not exist.
- 2026-06-06 — self-review RED regression:
  `cd apps/api && uv run pytest tests/test_admin_profile_publish.py::test_publish_sidecar_store_failure_does_not_enqueue -q`
  failed because publish enqueued before sidecar-store failure; orchestrator order corrected.

### Completion Notes

- Implemented Decision AR option (b): `resolve_chain` reads `library/{machine,process,filament}/{block_id}.json`
  bodies and delegates to the existing resolver tail; no grid `intents/` write/read or synthetic intent coordinate.
- Added `profile_publish.py` orchestration: publish revalidates the offer, resolves the chain, persists append-only
  bundle/snapshot through existing store, writes additive v2 offer publish-state, enqueues one slicer estimate, and
  audits publish/unpublish.
- Publish-state is sidecar-only and forward-compatible: v1/no publish fields reads as `unpublished`; unpublish clears
  active publish refs and does not delete append-only bundle/cache/estimate artifacts.
- Minimal admin observation surface is backend-only: publish fields appear on existing offer DTOs; publish returns
  bundle hash/job id; unpublish returns the offer DTO. No frontend was touched.
- Scope fences held: no `_PUBLIC_ROUTES` edit, no member selector/web change, no Alembic/DB change, no Spoolman
  mutation, no raw Orca JSON viewer, no N x M editor, no deploy, no production write, no live smoke, no commit.
- Non-blocking environment note: `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` was not present on this
  host/mount when checked; no catalog write/live smoke was performed in this pass.

### Test / Gate Results

- `cd apps/api && uv run pytest tests/test_profile_publish_resolve.py tests/test_profile_publish_store.py tests/test_admin_profile_publish.py tests/test_profile_offer_store.py tests/test_profile_offer_validate.py tests/test_admin_profile_offers.py tests/test_slicer_resolver.py tests/test_slicer_worker.py tests/test_route_enforcement_gate.py -q`
  -> `168 passed, 1 skipped, 112 warnings in 6.72s`.
- `cd apps/api && uv run ruff format --check app tests/test_profile_publish_resolve.py tests/test_profile_publish_store.py tests/test_admin_profile_publish.py tests/test_slicer_worker.py`
  -> `117 files already formatted`.
- `cd apps/api && uv run ruff check app tests/test_profile_publish_resolve.py tests/test_profile_publish_store.py tests/test_admin_profile_publish.py tests/test_slicer_worker.py`
  -> `All checks passed!`.
- `git diff --check` -> exit 0, no output.
- `git diff -- apps/api/app/main.py apps/web` -> exit 0, no output; `_PUBLIC_ROUTES` and member/web surface were not
  edited.

### File List

- `_bmad-output/implementation-artifacts/profile-publish-1-compile-offer-chain-resolver-bridge.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `apps/api/app/core/audit.py`
- `apps/api/app/modules/slicer/admin_router.py`
- `apps/api/app/modules/slicer/profile_offer.py`
- `apps/api/app/modules/slicer/profile_publish.py`
- `apps/api/app/modules/slicer/resolver.py`
- `apps/api/app/modules/slicer/schemas.py`
- `apps/api/tests/test_admin_profile_publish.py`
- `apps/api/tests/test_profile_publish_resolve.py`
- `apps/api/tests/test_profile_publish_store.py`
- `apps/api/tests/test_slicer_worker.py`

### Change Log

- 2026-06-06 — BMAD dev-story backend pass implemented PROFILE-PUBLISH-1 bridge and left story
  `in-progress`; T5 frontend, full closeout gates, external review, deploy, and live smoke remain controller-owned.
