# Sprint Change Proposal — PROFILE-PUBLISH-2: Member-Facing Published Profile Offer Surface

**Date:** 2026-06-13
**Status:** approved-for-planning
**Proposed by:** Laura/Hermes (controller-delegated planning run)
**Initiative:** 24 — Member-Facing Published Profile Offer Surface (PROFILE-PUBLISH-2)
**Epic:** E36
**Source:** controller task brief 2026-06-13 — PROFILE-PUBLISH-2 planning for member-facing published profile offers
**Predecessor:** Initiative 21 (E33 — Admin-Managed Orca Process Profiles + backend PROFILE-PUBLISH-1 bridge, ✅ done) + Initiative 23 (E35 — Spoolman Filament Profile Estimates, ✅ done)

---

## § 1 — What shipped and what is deferred

**Shipped (prerequisites):**

- **E33 / PROFILE-PUBLISH-1** — admin can import, publish, and compile a `PrintProfileOffer`'s `ProfileChain` into a real resolver-produced `bundle_hash` persisted in the append-only bundle store. One live Orca slice over one catalog STL was proven end-to-end (G-PUBLISH backend bridge, ✅ `3233a20`). Admin-only. Member selector untouched — kept consuming the 33.1/33.2 fixed grid projection.
- **E35 / Stories 35.1–35.6** — Spoolman-backed filament profile policy: `EstimateProfileSource` (`exact_filament_mapping` / `default_material_profile` / `unavailable_no_profile`), honest estimate labels in the UI, bounded default-matrix backfill. Published estimate metadata is available in `EstimateView` DTOs.

**Explicitly deferred by PROFILE-PUBLISH-1 (Decision AR, AC-16):**

> "No member selector / member offer surface / NO-422 contract change → PROFILE-PUBLISH-2. Safe default: member selector keeps consuming the 33.1/33.2 grid projection."

PROFILE-PUBLISH-2 is the realization of that deferred gate. It is NOT a scope change — it is the named follow-on slice confirmed in SCP `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` § 6 and architecture Decision AR.

---

## § 2 — Product intent

A member who opens a model's file/estimate view should be able to:

1. See the compatible, admin-published print profile offers available for that model.
2. Select an offer → the estimate display updates to show the time/grams/cost for that offer, using E35 honest labels (exact filament / default material / unavailable).
3. If no compatible offer exists, or the estimate for the selected offer is not yet computed, the UI explains this clearly instead of showing a wrong/empty state.
4. The selection does NOT expose Orca bundle/profile internals to the member — only portal labels, quality tier, printer name, and the E35 honesty label.

The member offer surface **does not** change the existing admin API for offers, does not touch the 33.1/33.2 grid, and does not add any new Alembic migration.

---

## § 3 — Scope boundaries (what this initiative covers and excludes)

### In scope

- New `GET /api/profiles/offers/published` endpoint (member-accessible, authenticated) — lists published offers with a safe DTO (no Orca raw fields).
- Estimate-by-offer resolution endpoint or extension — given `offer_id + stl_hash`, returns the `EstimateView` (with E35 source labels) or a pending/unavailable status.
- Member UI: offer picker component in the model file/estimate view; selection updates the estimate display; unavailability state shown clearly.
- E35 honesty labels surfaced to the member for the selected offer's estimate (exact/default/unavailable).
- i18n parity (en + pl) for all new member-facing strings.
- Visual regression baselines for the new member UI surface.
- NFR21-NO-422-1 realized: no member-reachable 422 from the offer → resolve path.

### Explicitly out of scope

- Admin offers API (`/api/admin/profiles/offers/*`) — preserved unchanged.
- 33.1/33.2 fixed-grid projection — preserved unchanged (member still sees this via the existing estimate selector when no offer is explicitly chosen).
- Spoolman write/mutation — none.
- N×M offer editor / raw Orca JSON viewer — none.
- Alembic / DB migration — none.
- Member print request / order flow changes — none (member offer selection is informational/estimate context only in this slice).
- SW-DEPLOY-1 worker overlay rebuild — NOT triggered (new endpoints are read-only over already-published bundles + existing estimate store; no new slicer worker path).
- Real-time estimate queue push (WebSocket/SSE) — none; polling via existing estimate status is sufficient for MVP.
- Member ability to trigger new estimate slices for an offer — read existing estimates only; backfill handled by E35's 35.6 machinery and future admin-triggered backfill.

---

## § 4 — Architecture decision record (Decision AT)

See `architecture.md` § Initiative 24 — Decision AT appended in this run.

**Summary:** The member-facing offer surface introduces a **separate** member-accessible endpoint (`GET /api/profiles/offers/published`) distinct from the admin endpoint, with a hard DTO safety fence (no Orca raw bundle_hash, no profile ref names, no chain internals). Estimate-by-offer resolution extends the existing `GET /api/estimates` path with an `offer_id` lookup that maps offer → published `bundle_hash` → existing estimate record. No new slicer work is enqueued on-demand (read-only over already-published bundles). The E35 `EstimateProfileSource` metadata flows through verbatim.

Key open decisions (recorded; defaults proposed; operator confirmation needed before 36.2 dev-story):

- **OD-1 — Endpoint shape for estimate-by-offer**: extend `GET /api/estimates?offer_id=...&stl_hash=...` vs. new `GET /api/estimates/by-offer`. **Proposed default: extend existing endpoint with `offer_id` query param** (keeps the read surface unified; no new route to maintain). Rationale: the existing endpoint already returns `EstimateView` keyed by `bundle_hash`; adding an `offer_id` param that resolves to the published bundle_hash is additive and backward-compatible.
- **OD-2 — Filament context for offer resolution**: the estimate-by-offer read needs a `spoolman_filament_ref` or `material` param to apply E35's policy precedence (`exact > default > unavailable`). **Proposed default: optional `spoolman_filament_ref` param; when absent, resolve via material default only** (matches the existing estimate display context where no specific spool is selected by the member).
- **OD-3 — G-UXGATE for offer picker UI**: does the member offer picker UI require a `bmad-ux` design pass before Story 36.3 frontend work? **Proposed default: YES — G-UXGATE is required** before 36.3 FE implementation (consistent with Init 21 PROFILE-OFFER-1 precedent where `UX-PROFILE-OFFER-1` was required before FE composition). A `ux-profile-publish-2-member-offer-picker` work item should precede 36.3.

---

## § 5 — Functional requirements

| ID | Description | Story |
|---|---|---|
| FR24-MEMBER-OFFER-LIST-1 | Member-accessible endpoint listing published offers with safe DTO (portal_label, quality_tier, compatible_material_categories, printer_name; no raw Orca fields). | 36.1 |
| FR24-COMPAT-FILTER-1 | Optional `?material=PLA` query param filters by `compatible_material_categories`; returns ALL published offers when absent. | 36.1 |
| FR24-MEMBER-OFFER-RESOLVE-1 | Estimate-by-offer resolution: `offer_id` + `stl_hash` → published `bundle_hash` → `EstimateView` (with E35 source metadata) or pending/unavailable status. | 36.2 |
| FR24-MEMBER-OFFER-UI-1 | Member UI: offer picker on model file/estimate view; selection updates estimate display; E35 honesty labels shown; unavailability state explained. | 36.3 |

---

## § 6 — Non-functional requirements

| ID | Description | Story |
|---|---|---|
| NFR24-NO-422-1 | No member-reachable 422 from the offer → resolve path. Published offer + any filament/material context resolves to estimate / pending / unavailable — never a server error. (Realizes NFR21-NO-422-1 for the member surface.) | 36.2 |
| NFR24-LEAKFENCE-1 | Member offer DTO must NOT include raw `bundle_hash`, raw Orca profile ref names, raw chain/block body fields, or internal sidecar paths. Verified by a negative DTO test. | 36.1 |
| NFR24-HONESTY-1 | E35 `EstimateProfileSource` labels flow through to the member offer picker: exact / default / unavailable shown distinctly. Fallback estimates must not appear as exact. | 36.2+36.3 |
| NFR24-UNAVAIL-UX-1 | When no compatible offer exists OR estimate is unavailable, the UI shows a clear, non-misleading message (not an empty spinner, not a wrong state). | 36.3 |
| NFR24-AUTH-1 | Both new backend endpoints are authenticated-member-accessible (not admin-only). Anonymous → 401. Unpublished offer → 404. Admin offers API unchanged. | 36.1+36.2 |
| NFR24-AUTHGATE-1 | Frontend offer picker defers to shell `AuthGate` for anonymous/unknown auth state; role-tier block only for authenticated-non-member (per Init 10 authgate discipline). | 36.3 |
| NFR24-I18N-1 | All new `modules.member.offers.*` i18n keys present in both `en.json` and `pl.json`. | 36.3 |
| NFR24-VISUAL-1 | Playwright visual baselines for the offer picker in populated / empty / unavailable states across 4 projects (desktop/mobile × light/dark). | 36.3 |
| NFR24-DETERMINISM-1 | 3× consecutive identical pytest + vitest pass counts before merge of any story. | 36.1–36.3 |

---

## § 7 — Epic and story breakdown

**Initiative 24 → Single epic E36 → 3 stories (36.1, 36.2, 36.3)**

### Story 36.1 — Member-accessible published-offer list endpoint + safe DTO

**Candidate ID:** MEMBER-OFFER-LIST-1
**Realizes:** FR24-MEMBER-OFFER-LIST-1, FR24-COMPAT-FILTER-1, NFR24-LEAKFENCE-1, NFR24-AUTH-1, NFR24-DETERMINISM-1
**Sketch:** New `GET /api/profiles/offers/published` in a member-accessible router (NOT inside `admin/` namespace; gated on `current_user` dep, not `current_admin`). Reads `profile_offer.py`'s `list_offers()` → filters for `publish_state == "published"` → projects to a safe member DTO (`MemberPublishedOfferView`: offer_id, portal_label, quality_tier, compatible_material_categories, printer_name — no bundle_hash, no chain body, no raw Orca profile refs). Optional `?material=PLA` param pre-filters by `compatible_material_categories`. Added to `router.py` outside `_PUBLIC_ROUTES`. Tests: 401 anonymous; 200 for member; DTO safety fence negative test (no raw Orca fields); published-only filter; material filter.
**Deploy:** read-only over existing offer sidecar files → **SW-DEPLOY-1 NOT triggered**.
**Gates:** G-DEVGO (first new E36 story; implementation BLOCKED until create-story + dev-go).

### Story 36.2 — Member estimate-by-offer resolution

**Candidate ID:** MEMBER-OFFER-RESOLVE-1
**Realizes:** FR24-MEMBER-OFFER-RESOLVE-1, NFR24-NO-422-1, NFR24-HONESTY-1, NFR24-AUTH-1, NFR24-DETERMINISM-1
**Sketch:** Extend `GET /api/estimates` with an optional `offer_id` query param. When `offer_id` is supplied, the endpoint: (a) reads the offer sidecar → validates `publish_state == "published"` → retrieves the `bundle_hash` from the offer's published state; (b) reads the existing estimate from `EstimateStore` keyed by `(stl_hash, bundle_hash)` → returns `EstimateView` (with E35 `estimate_profile_source` metadata) if present; (c) if not present → returns `{status: "not_computed"}` (no on-demand enqueue in this slice — read-only); (d) if offer not published or not found → returns 404 (not 422). No new slicer path, no new worker call. Backward-compatible: callers without `offer_id` continue to use the existing resolve path unchanged.
**Deploy:** backend-only extension of existing read endpoint → **SW-DEPLOY-1 NOT triggered**.
**Open decisions:** OD-1 (endpoint shape — default: extend existing), OD-2 (filament context param — default: optional `spoolman_filament_ref`). Confirm before dev-story.
**Gates:** G-DEVGO; G-UXGATE (OD-3 resolved before 36.3 FE; 36.2 backend may proceed without UX gate).

### Story 36.3 — Member UI — offer picker + estimate display

**Candidate ID:** MEMBER-OFFER-UI-1
**Realizes:** FR24-MEMBER-OFFER-UI-1, NFR24-HONESTY-1, NFR24-UNAVAIL-UX-1, NFR24-AUTHGATE-1, NFR24-I18N-1, NFR24-VISUAL-1, NFR24-DETERMINISM-1
**Sketch:** New offer picker component in the model file/estimate view (`apps/web/src/modules/catalog/` or `modules/estimates/` — exact location determined at create-story time after code recon). Calls 36.1's endpoint to list compatible offers for the current model's material. Renders a selector (radio group or tab strip — TBD by UX gate). On selection: calls 36.2's `GET /api/estimates?offer_id=...&stl_hash=...` → displays `EstimateView` with E35 source label (exact/default/unavailable chip). Unavailability states: "No published offer for this model/material" (no offers), "Estimate not yet computed" (not_computed), "No filament profile available" (unavailable). AuthGate discipline: defer to shell `AuthGate` for anonymous; no component-level redirect on unknown auth. en+pl i18n parity. Visual baselines for populated/empty/unavailable × 4 Playwright projects.
**Prerequisite:** G-UXGATE (`ux-profile-publish-2-member-offer-picker` design artifact required before FE implementation).
**Gates:** G-DEVGO; **G-UXGATE** (required before FE dev-story); G-36.2-DONE (36.2 backend must be on `main` before 36.3 FE story branch).

---

## § 8 — Sequencing and gates

```
36.1 → 36.2 → [G-UXGATE] → 36.3
```

- **36.1** can start immediately after G-DEVGO (operator dev-go).
- **36.2** depends on 36.1 being on `main` (uses the offer sidecar read path).
- **G-UXGATE** (`ux-profile-publish-2-member-offer-picker`) is a `bmad-ux` work item that must precede 36.3 FE dev-story. Can run in parallel with 36.1 + 36.2 backend work.
- **36.3** depends on 36.2 on `main` + G-UXGATE completed.

Sprint-status rows seeded by this SCP: `epic-36` / `36-1-member-published-offer-list-endpoint` / `36-2-member-estimate-by-offer-resolution` / `ux-profile-publish-2-member-offer-picker` / `36-3-member-offer-picker-ui` / `epic-36-retrospective`. Story 36.1 is now `ready-for-dev`; the remaining rows stay `backlog`. Implementation remains BLOCKED until explicit operator dev-go and story-branch execution.

---

## § 9 — Open product/architecture questions for operator

1. **OD-1 (endpoint shape)**: Extend `GET /api/estimates?offer_id=...` vs. new `GET /api/estimates/by-offer`. Proposed default: extend existing. Does the operator accept this?
2. **OD-2 (filament context)**: Optional `spoolman_filament_ref` param for estimate-by-offer; absent → material-default only. Does the operator accept this?
3. **OD-3 (UX gate)**: `ux-profile-publish-2-member-offer-picker` required before 36.3 FE. Does the operator want to schedule this now, or defer the UX gate and allow 36.3 to proceed with a minimal/wire-frame approach?
4. **Estimate unavailability UX**: When `status: not_computed`, should the member see a "Request estimate" button that enqueues a slice, or just a "Not yet available" state? (The on-demand enqueue is out of scope for this slice; this question determines whether a G-ENQUEUE gate should be named for a later story.)

---

## § 10 — What does NOT change

- Admin API (`/api/admin/profiles/*`, `/api/admin/profiles/offers/*`) — untouched.
- The 33.1/33.2 fixed-grid projection feeding the existing estimate selector — untouched.
- `compatibility.py` `MATERIAL_TIER_COMPATIBILITY` grid — untouched.
- `profile_publish.py` orchestrator, `bundle_store.py`, `estimate_store.py` — read-only consumption.
- E35 `ProfilePolicyStore`, `EstimateProfileSource` — consumed, not modified.
- Alembic / DB schema — no migration.
- Slicer worker / arq pool / SW-DEPLOY-1 — NOT triggered by this initiative's read-only surface.

---

## § 11 — Cross-references

- Predecessor: `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` (named G-PUBLISH + PROFILE-PUBLISH-2 as the deferred follow-on).
- Architecture: `architecture.md` § Initiative 24 (Decision AT — appended in this run).
- Epics: `epics.md` § Initiative 24 (Epic E36, stories 36.1–36.3 — appended in this run).
- PRD: `prd.md` § Initiative 24 (appended in this run).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — rows seeded in this run (all `backlog`).
- Memory: [[feedback_scp_pre_enumeration_phase]] (pre-enumeration + cache-topology + magic-constant contract applied to 36.1–36.3 sketches above), [[reference_web_routetree_regen]] (route + AdminTabs ripple if any new routes added).
