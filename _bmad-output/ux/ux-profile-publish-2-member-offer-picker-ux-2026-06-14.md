---
title: "UX-PROFILE-PUBLISH-2 — Member-Facing Published Profile Offer Picker (UX Design)"
artifact: ux-recommendation
topic: member-facing-published-profile-offer-picker
work_item: ux-profile-publish-2-member-offer-picker
gate: G-UXGATE
initiative: 24
epic: E36
story: 36.3 (MEMBER-OFFER-UI-1)
designer: Sally
date: 2026-06-14
canonical_path: _bmad-output/ux/ux-profile-publish-2-member-offer-picker-ux-2026-06-14.md
status: >
  done (G-UXGATE satisfied — UX artifact authored, sprint-status row updated to done.
  Story 36.3 FE authoring is unblocked. No app/test/config/infra code touched;
  no deploy, no commit by this UX pass.)
bmad_route: >
  bmad-ux (Create UX, menu-code CU, phase 2-planning) — confirmed via session-start
  bmad-help routing; brownfield discovery/design-only carve-out, output under the
  git-tracked _bmad-output/ux/**/*.md surface per AGENTS.md.
scope: >
  UI/UX product design ONLY for the MEMBER offer-picker surface (Story 36.3).
  No frontend/backend/infra/test/config code, no deploy, no commit.
  Designs the surfacing of the Decision AT estimate-by-offer read path;
  the resolution rules and DTO contracts are backend SoT and are NOT re-litigated here.
source_artifacts:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md
  - _bmad-output/planning-artifacts/prd.md § Initiative 24
  - _bmad-output/planning-artifacts/architecture.md § Initiative 24 / Decision AT
  - _bmad-output/planning-artifacts/epics.md § Initiative 24 / Story 36.3
  - apps/api/app/modules/slicer/member_router.py (Story 36.1 — live backend)
  - apps/api/app/modules/slicer/router.py (Story 36.2 — live backend, offer_id path)
  - apps/api/app/modules/slicer/schemas.py (MemberPublishedOfferView, EstimateView)
  - apps/web/src/modules/catalog/components/tabs/FilesTab.tsx (placement host)
  - apps/web/src/modules/estimates/hooks/useEstimate.ts (hook to extend)
  - apps/web/src/modules/estimates/components/ProfileSourceBadge.tsx (reuse for honesty labels)
predecessors:
  - UX-PROFILE-1 (done) — profile-admin-selector-ux-2026-06-04.md
  - UX-PROFILE-OFFER-1 (done) — ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md
  - Stories 36.1 + 36.2 (on main) — the backend endpoints this surface consumes
downstream: bmad-create-story for Story 36.3 (member offer picker UI) — this artifact provides the FE ACs.
mockups: []
---

# Member-Facing Published Profile Offer Picker — UX Design (G-UXGATE)

**Author:** Sally (UX Designer) — 2026-06-14
**Work item:** `ux-profile-publish-2-member-offer-picker` — the G-UXGATE checkpoint required before
Story 36.3 FE implementation per SCP § 8 (OD-3 resolved: YES, gate required) and architecture
Decision AT.
**Surface:** one new MEMBER-facing picker in the model `FilesTab` (STL sub-view) — allows a member
to select a published print profile offer and see the resulting estimate with E35 honesty labels.

> **Routing note (mandatory protocol):** `bmad-help` consulted at session start. AGENTS.md §
> BMAD-vanilla-first + SCP OD-3 resolution require a `bmad-ux`/Sally pass (canonical UIX route
> **[CU] Create UX**, phase 2-planning) before the member offer-picker UI is built. This is
> brownfield (PRD/architecture/epics for Init 24 exist; 36.1/36.2 backend is on `main`), authored
> as a focused UX recommendation on the git-tracked `_bmad-output/ux/**/*.md` surface.
> **No PRD/architecture/app/test/config code touched.** The next ceremony is `bmad-create-story`
> for Story 36.3, which consumes this artifact to lock its FE ACs.

---

## TL;DR — recommendation

1. **Surface published profile offers as a compact inline picker in the FilesTab STL view,
   positioned between the existing `CatalogEstimateProfileSelector` and the STL file list.**
   When no published offers are compatible with the current material selection, the picker is
   absent — not an error state, just nothing extra. (§ C)

2. **The material selection in the existing `CatalogEstimateProfileSelector` drives the offer
   list filter.** Calls `GET /api/profiles/offers/published?material={material_class}`. When the
   member changes material, the offer list refreshes and any previously selected offer is cleared
   if no longer in the new list. (§ D)

3. **Selection is global to the FilesTab** (same scope as the existing preset selector) and
   ephemeral (component state, no persistence). When an offer is selected, every STL row's
   `EstimateChip` and the expanded `RowEstimatePanel` switch to offer mode:
   `GET /api/estimates?offer_id=...&stl_hash=...`. A "None" option (the default) restores the
   existing preset-based estimate flow. (§ D)

4. **Seven member-facing states, each with a distinct, honest treatment.** The hardest are
   `not_computed` (estimate not yet available for this offer+STL) and
   `unavailable_no_profile` (E35 source: no filament profile for the offer's material). Neither
   renders as an error — both show a specific, non-misleading message. (§ E)

5. **E35 `ProfileSourceBadge` is reused verbatim for offer-based estimates.** Fallback estimates
   (`default_material_profile`) must not appear exact. No new badge type; the existing badge
   carries the distinction. The `not_computed` and `unavailable_no_profile` states each have
   dedicated UI copy, separate from the badge. (§ F)

6. **Fail OPEN for the picker, like every member-facing estimate surface (Init 10 precedent).**
   A transport error fetching the offer list does not lock out the STL estimate experience — the
   existing preset-based estimate path remains fully functional. The offer picker shows a Retry
   affordance but is never a blocker. (§ E.5)

7. **G-ENQUEUE is explicitly out of scope for 36.3.** When `status: not_computed`, the member
   sees a clear "not yet available" state only — no "Request estimate" CTA, no enqueue, no
   promise of a timeline. If a G-ENQUEUE gate is named in a later story, it must go through its
   own UX pass. (§ K)

---

## Constraints in force

- **Backend is SoT.** `GET /api/profiles/offers/published` and `GET /api/estimates?offer_id=...`
  are the only contracts; this design does not extend, change, or re-litigate them.
- **AuthGate discipline (Init 10 retro, NFR24-AUTHGATE-1).** The offer picker component must
  NOT redirect for anonymous/unknown auth. Defer to the shell `AuthGate`. Act only for
  authenticated-but-unauthorized scenarios (none apply here — both endpoints are member-accessible).
- **Frontend rule: zero inline hex.** All theme tokens from `apps/web/src/styles/theme.css`.
  No new token needed by this surface (all required tokens exist from prior initiatives).
- **No `E35 ProfileSourceBadge` copy change.** Existing badge keys
  `modules.estimates.profile_source.exact` and `modules.estimates.profile_source.default` carry
  the honesty distinction; new keys are only for states the badge does not cover.
- **i18n mandatory (NFR24-I18N-1).** All new member-facing strings in both `en.json` + `pl.json`,
  full parity, correct Polish diacritics, under `modules.member.offers.*`.
- **Visual regression mandatory (NFR24-VISUAL-1).** Baselines across the 4 Playwright projects.
- **G-ENQUEUE explicitly out of scope.** No on-demand estimate enqueue in 36.3 (§ K).

---

## A. Problem / scope / non-goals

### A.1 Problem

Backend stories 36.1 + 36.2 are on `main`. They expose:
- A member-accessible published-offer list (`GET /api/profiles/offers/published`)
- An offer-based estimate read path (`GET /api/estimates?offer_id=...&stl_hash=...`)

No member-facing UI consumes either. Story 36.3 is blocked on G-UXGATE — it cannot be authored
or developed until this UX artifact defines the interaction model, states, and AC checklist.

The member currently sees estimates via the existing preset-based selector
(`CatalogEstimateProfileSelector`: material + quality-tier → bundle-hash → estimate). This is the
Init 20/33 surface. The Init 24 offer picker is an ADDITIVE layer that lets a member pick a
specific published print profile offer and see its estimate — a richer, admin-curated choice that
carries the E35 filament policy honesty labels.

### A.2 Scope

- New `PublishedOfferPicker` component in `apps/web/src/modules/estimates/components/` (or
  `apps/web/src/modules/catalog/components/` — exact module determined at story create-time via
  code recon; the UX contract is module-agnostic).
- Placement in `FilesTab.tsx` between `CatalogEstimateProfileSelector` and the STL file list,
  gated on `active === "stl" && stlFiles.length > 0`.
- New `usePublishedOffers(material)` hook — `GET /api/profiles/offers/published?material=...`.
- New `useOfferEstimate(stlHash, offerId)` hook (or extension of `useEstimate`) — calls
  `GET /api/estimates?offer_id=...&stl_hash=...`.
- `EstimateChip` and `RowEstimatePanel` extended to optionally accept `offerId` as an alternative
  to `preset` (implementation detail — see § J).
- All new i18n keys in `modules.member.offers.*`.
- Visual baselines for populated / empty / unavailable × 4 Playwright projects.

### A.3 Non-goals (explicitly excluded from 36.3)

| Out of scope | Why |
|---|---|
| Admin offer management | Shipped in PROFILE-OFFER-1; no change in this slice. |
| On-demand estimate enqueue | G-ENQUEUE is a named deferred gate; see § K. |
| Offer-based print request / ordering | Not a member-facing concern in this slice. |
| Member ability to create, edit, or delete offers | Admin-only surface. |
| Persistent offer selection (localStorage, URL param) | MVP: component state is sufficient. |
| Spoolman spool-level filament selection in the offer picker | `spoolman_filament_ref` optional param is available on the backend (OD-2); the FE does NOT expose it in this slice. The picker requests estimates without a filament ref, resolving via the E35 material-default policy. |
| Raw Orca / bundle internals surfaced anywhere | DTO fence is the backend's SoT; this UX adds no display of internal fields. |
| Changes to the existing `CatalogEstimateProfileSelector` | The selector keeps working as-is; the offer picker is additive. |
| New routes / admin tab changes | 36.3 is a component addition within the existing FilesTab. |

---

## B. Backend contracts consumed

### B.1 `GET /api/profiles/offers/published`

**Story:** 36.1. **Auth:** authenticated member or admin (anonymous → 401, handled by shell AuthGate).

**Query params:**
- `material` (optional, case-insensitive) — filters `compatible_material_categories`.
  Example: `?material=PLA`

**Response:** `MemberPublishedOfferListResponse`

```
{
  "offers": [
    {
      "offer_id":                   string,   // 32-char hex; never null
      "portal_label":               string,   // admin-assigned display name; DATA (untranslated)
      "quality_tier":               string | null,  // "aesthetic"|"standard"|"strong"; null if block unavailable
      "compatible_material_categories": string[],  // e.g. ["PLA", "PETG"]
      "printer_name":               string | null   // derived from machine block; null if unavailable
    }
  ]
}
```

**DTO fence (NFR24-LEAKFENCE-1):** `bundle_hash`, raw Orca profile refs, chain block IDs,
sidecar paths, and `publish_state` internals are absent. The FE must NEVER expect or render any
of these fields.

**FE behavior:**
- Call with `?material={preset.material_class}` to filter to the current material.
- An empty `offers` array is a normal, non-error response (no published offers for this material).
- A 401 is handled transparently by the `api()` client (shell AuthGate takes over).
- No result → picker renders the "no compatible offers" state, not an error.

### B.2 `GET /api/estimates` (extended — Story 36.2)

**Auth:** authenticated member (anonymous → 401).

**Query params for offer mode:**
- `stl_hash` (required) — 64-char lowercase hex content hash of the STL file.
- `offer_id` (required for offer mode) — 32-char hex offer identifier.
- `spoolman_filament_ref` (optional) — **NOT sent from the 36.3 FE** in this slice (OD-2 deferred;
  the backend resolves via material-default policy when absent, see § F).

**Response:** `EstimateView` (existing schema, unchanged by 36.2)

```
{
  "status":       "fresh"|"stale"|"queued"|"failed"|"absent"|"not_computed",
  "time_seconds": int | null,
  "filament_g":   float | null,
  "filament_mm":  float | null,
  "filament_cm3": float | null,
  "filament_cost": float | null,
  "currency":     string | null,
  "computed_at":  string | null,
  "warnings":     [],
  "failure_reason": null | string,
  "override_context": { "material_class": ..., "quality_tier": ... },
  "profile_selection_context": {
    "estimate_profile_source": "exact_filament_mapping"|"default_material_profile"|"unavailable_no_profile",
    "selected_material": string | null,
    ...
  } | null,
  "offer_id": string | null   // echoes back the requested offer_id
}
```

**Key statuses for the offer path:**

| Status | Meaning | UX treatment |
|---|---|---|
| `fresh` / `stale` | Estimate available; `profile_selection_context` carries honesty label | Show estimate + ProfileSourceBadge (§ F) |
| `not_computed` | Estimate not yet computed for this (offer, STL) pair | "Not yet available" state (§ E.3) |
| `failed` | Slicer ran and failed | Show `failure_reason` hint (same as existing preset path) |
| `queued` | Compute in flight (edge: admin just published) | Show loading/queued state |
| `404` (HTTP) | Offer not found or no longer published | "Offer unavailable" state (§ E.7) |

**NFR24-NO-422-1 guarantee:** the offer → resolve path will NEVER return a 422. The FE should
never need to handle a 422 from this endpoint in offer mode.

---

## C. Placement in model Files/STL estimate surface

### C.1 Exact insertion point in FilesTab

The `PublishedOfferPicker` is inserted in `FilesTab.tsx` under the same guard that wraps the
existing `CatalogEstimateProfileSelector`:

```
active === "stl" && stlFiles.length > 0
```

**Stack order (top → bottom within the STL view):**

```
1. [existing] file-type chip strip (STL · Source · 3MF)
2. [existing] CatalogEstimateProfileSelector  ← material + quality-tier picker
3. [NEW]      PublishedOfferPicker            ← offer picker (this artifact)
4. [existing] admin render controls (isAdmin)
5. [existing] STL file list rows
```

The offer picker sits visually **below** the existing selector and **above** the file list. Its
vertical presence is proportional to the number of offers: a single offer is compact; 3–5 offers
fit in one "row" on desktop, stack on mobile.

### C.2 Design rationale

- **Below the material selector:** the offer list is filtered by `preset.material_class`, so the
  selector above is the natural parent control. Seeing "material = PLA, then offers for PLA" reads
  as a cause-effect sequence.
- **Above the file list:** the selected offer changes estimates for all rows; placing it above
  all rows makes the global scope of the control visually evident.
- **Not a modal or drawer:** offer selection is a fast, reversible micro-interaction. A modal
  would add unnecessary ceremony. The compact inline approach is consistent with the existing
  `CatalogEstimateProfileSelector` pill-group style.
- **Not merged into `CatalogEstimateProfileSelector`:** offers are a different abstraction (a
  curated, admin-published chain) from the generic preset (material + quality-tier). Merging them
  would muddy the product framing and complicate the component. Separation is intentional.

---

## D. Interaction model

### D.1 Offer picker control type

**Recommendation: compact radio group, one item per offer.**

Each option shows:
- `portal_label` (the offer name — DATA, untranslated, rendered as-is)
- `quality_tier` chip (optional — omitted when null; values: "aesthetic" / "standard" / "strong";
  reuse `modules.estimates.quality.{tier}` i18n keys)
- `printer_name` (optional — omitted when null; rendered as muted subtext)

A **"None (standard estimate)"** radio option appears first and is the **default selection**.
Choosing it restores the preset-based estimate path.

**Visual language:** match the `CatalogEstimateProfileSelector` pill-group style. The offer radio
buttons are styled as selectable pill cards (not a native `<select>` — each offer needs its
quality-tier chip and printer name, which a native option cannot carry). On mobile, pills wrap
to a second row or stack vertically.

**Maximum offers in picker:** at v1, the backend has no pagination on the offer list; the FE
renders all returned offers. A small guard note: if the operator publishes an unreasonable
number (>10), the picker could overflow — recorded as a deferred concern in § K.

### D.2 Material-driven offer list filter

The `PublishedOfferPicker` is always in sync with `preset.material_class`:

```
usePublishedOffers(material = preset.material_class)
```

When `preset.material_class` changes (member switches material in `CatalogEstimateProfileSelector`):
- The offer list query key changes → TanStack Query issues a new fetch for the new material.
- The current `selectedOfferId` state is **cleared** if the newly-fetched offer list does not
  contain the previously selected offer (the offer might be incompatible with the new material).
- If it does contain the same offer (the offer is multi-material), selection is preserved.

This prevents the FE from calling the estimate endpoint with an offer that is incompatible with
the currently-selected material, producing a confusing cross-material estimate.

### D.3 Estimate mode switching

The `FilesTab` maintains a `selectedOfferId: string | null` state (default `null`).

| State | Estimate path used |
|---|---|
| `selectedOfferId === null` | **Preset mode** (existing) — `GET /api/estimates?stl_hash=...&material_class=...&quality_tier=...&printer_ref=...` |
| `selectedOfferId !== null` | **Offer mode** — `GET /api/estimates?stl_hash=...&offer_id=...` |

Both `EstimateChip` and `RowEstimatePanel` receive the active mode (either `preset` or `offerId`)
and call the appropriate hook. The mode is global to the FilesTab — all rows switch together.

**The existing `canReadSelectedEstimate` gate (NFR21-NO-422-1 guard) is bypassed in offer mode.**
The offer mode path has no 422 risk (NFR24-NO-422-1 guaranteed by the backend); the estimate is
gated only on `offer_id !== null && stlHash.length > 0`. No availability-check round-trip is
needed before firing the offer estimate request.

### D.4 Selection persistence and scope

- **Scope:** global to the `FilesTab` component instance (same as the existing preset selector).
  Not per-STL-file.
- **Persistence:** **ephemeral component state** only. Navigating away and back resets to "None".
- **No localStorage, no URL param** for this slice. The MVP approach is sufficient; persistence
  can be added as a triage backlog item if operator feedback surfaces demand for it.

### D.5 Loading / refetch behavior

**Offer list (`usePublishedOffers`):**

| Setting | Value | Rationale |
|---|---|---|
| `staleTime` | `30_000` ms | Offers change infrequently (admin-published); 30s freshness is sufficient without hammering the backend on every tab visit. |
| `gcTime` | `5 * 60_000` ms | Match the `useEstimate` GC budget — keep offers warm across tab switches. |
| `refetchOnWindowFocus` | `true` | If admin publishes a new offer while the tab is open, returning focus brings it in. |
| `retry` | `false` | A network error shows the Retry affordance (member choice); auto-retry adds noise. |
| `enabled` | `isAuthenticated && stlFiles.length > 0` | Do not fire for anonymous visitors or tabs without STL files. |

**Cache key:** `["member", "offers", "published", { material: preset.material_class }]`

**Offer estimate (`useOfferEstimate`):**

| Setting | Value | Rationale |
|---|---|---|
| `staleTime` | `60_000` ms | Match `useEstimate` — estimates change no faster than the slicer worker cadence. |
| `gcTime` | `5 * 60_000` ms | Same as `useEstimate`. |
| `retry` | `false` | A transport error shows the retry affordance inline. |
| `enabled` | `offerId !== null && stlHash.length > 0` | Only fire when an offer is selected AND the file has a hash. |

**Cache key:** `["estimates", stlHash, { offerId }]`

This is deliberately DIFFERENT from the preset cache key (`["estimates", stlHash, presetKey(preset), printerRef]`). The two modes use separate cache entries so switching between "None" and an offer is always a fresh independent read, not a stale preset number shown for an offer path.

---

## E. Member-facing states

The following states are exhaustive. Every state must have a coded implementation path in the
Story 36.3 component.

### E.1 Populated offers (normal case)

**Trigger:** `GET /api/profiles/offers/published?material=...` returns ≥1 offer.

**Treatment:**
- `PublishedOfferPicker` renders with the "None" option selected (default).
- Each published offer is displayed as a selectable pill card with `portal_label`, optional
  `quality_tier` chip, optional `printer_name`.
- Selecting an offer updates `selectedOfferId`, triggering all STL rows to switch to offer mode.
- The selected offer is highlighted (e.g., `ring-1 ring-primary`, matching the existing selector
  active style).

**Accessibility:** the picker is a `role="radiogroup"` with a labelled `legend` (the picker
section heading). Each option is a `<label>` wrapping a visually-hidden `<input type="radio">`.
See § H.

### E.2 No compatible offers

**Trigger:** `GET /api/profiles/offers/published?material=...` returns an empty `offers` array,
OR the backend returns 200 with no offers for the current material.

**Treatment:** The `PublishedOfferPicker` renders a **small, muted notice** — NOT an error state:

> *(i18n key: `modules.member.offers.picker.no_offers_for_material`)*
> "No published profiles for {material} yet."

This is rendered as a `text-xs text-muted-foreground` line, no icon, no Retry button (nothing is
broken — the admin simply hasn't published an offer for this material). The STL list and the
existing preset-based estimate flow continue unaffected.

### E.3 Offer selected — estimate `not_computed`

**Trigger:** An offer is selected, and `GET /api/estimates?offer_id=...&stl_hash=...` returns
`{ status: "not_computed" }` for a given STL row.

**Treatment in `EstimateChip`:** replace the grams number with a muted label:

> *(i18n key: `modules.member.offers.estimate.not_computed_chip`)*
> "—"  (em dash, `text-muted-foreground`)

**Treatment in `RowEstimatePanel`:** show a dedicated notice panel (not an error, not a spinner):

> *(i18n key: `modules.member.offers.estimate.not_computed_title`)*
> "Estimate not yet available"
> *(i18n key: `modules.member.offers.estimate.not_computed_detail`)*
> "The estimate for this file with the selected profile hasn't been computed yet."

**No Retry button.** Retrying would return the same `not_computed` until the admin triggers
a backfill. No promise of a timeline. No G-ENQUEUE CTA (explicitly out of scope, § K).

**Honesty: the `profile_selection_context` is present on the `not_computed` response** but should
NOT be shown — it describes what the estimate source WOULD be if computed. Showing a source badge
on a `not_computed` state would be misleading (implying an estimate exists with that source).
The source badge is shown ONLY for `fresh` / `stale` status (§ F).

### E.4 Offer selected — estimate `unavailable_no_profile`

**Trigger:** An offer is selected; the estimate is found but
`profile_selection_context.estimate_profile_source === "unavailable_no_profile"`.

**Treatment:** this is a VALID estimate with E35 source label — it means no filament profile
matched for the offer's material, so the estimate was computed without an exact filament (or with
a degraded/absent profile). The estimate numbers (if present) should be shown.

The `ProfileSourceBadge` handles this:
- It renders nothing for `unavailable_no_profile` (per existing badge logic).
- The `RowEstimatePanel` shows the estimate numbers (if non-null) with no source badge — the
  absence of a badge is the honest signal that the profile source is unavailable.

**Additional treatment for `not_computed` + `unavailable_no_profile` combination:**
If `status: "not_computed"` AND `profile_selection_context.estimate_profile_source ===
"unavailable_no_profile"`, only the `not_computed` state (§ E.3) is shown — the source context
is suppressed as described above.

### E.5 Transport error fetching the offer list

**Trigger:** `GET /api/profiles/offers/published` fails with a network error or non-401 HTTP
error.

**Treatment:** The `PublishedOfferPicker` renders an inline error state:

> *(i18n key: `modules.member.offers.picker.transport_error`)*
> "Couldn't load published profiles."
> [Retry] button (i18n key: `modules.member.offers.picker.retry`)

**Fail-OPEN posture:** the transport error in the offer picker **does NOT affect the existing
preset-based estimate flow**. The STL file list and `CatalogEstimateProfileSelector` remain
fully functional. The offer picker's error is contained within its own region.

### E.6 Anonymous / auth unknown (AuthGate discipline)

**Trigger:** `useAuth().isAuthenticated === false` OR auth state is still loading
(loading / unknown).

**Treatment:** the `PublishedOfferPicker` renders **nothing** (returns `null`). It does NOT show
a login prompt, does NOT redirect, and does NOT call `GET /api/profiles/offers/published`. The
shell `AuthGate` handles the unauthenticated case; component-level redirect is forbidden by the
Init 10 AuthGate discipline (AGENTS.md).

The offer picker is gated on:
```typescript
enabled: isAuthenticated && stlFiles.length > 0
```

When `!isAuthenticated`, `usePublishedOffers` is disabled and the component returns null. The
existing estimate chip/panel remain functional (they have their own auth handling already).

### E.7 Offer disappears / unpublished after refetch

**Trigger:** An offer was selected; the member later (after a `refetchOnWindowFocus` or manual
retry of the offer list) fetches the offer list and the previously-selected offer is no longer
present OR the estimate endpoint returns `404` for that offer.

**Treatment (offer list refetch path):**
- When `usePublishedOffers` refetches and the `selectedOfferId` is absent from the new list,
  the `selectedOfferId` state is cleared (reset to `null`).
- The picker silently deselects; the estimate display falls back to preset mode.
- No toast, no error — the offer simply is no longer available.

**Treatment (estimate 404 path):**
- If `GET /api/estimates?offer_id=...&stl_hash=...` returns `404` for the selected offer:
  - The specific STL row shows an "Offer unavailable" inline notice in the chip/panel.
  - The offer picker remains visible (other rows may still have estimates for the same offer).
  - Next offer-list refetch will clear the selection if the offer is gone.
  - `(i18n key: modules.member.offers.estimate.offer_unavailable_chip)` — "—" in the chip.
  - `(i18n key: modules.member.offers.estimate.offer_unavailable_title)` — "Profile no longer available" in the panel.

---

## F. Honesty labels — E35 profile source for offer-based estimates

**Background:** E35 (`estimate_profile_source`) distinguishes:
- `exact_filament_mapping` — a specific Spoolman filament was mapped; the estimate uses exact parameters.
- `default_material_profile` — no exact filament matched; the estimate uses the material-default profile.
- `unavailable_no_profile` — no filament profile exists for the offer's material; the estimate is absent or degraded.

For offer-based estimates (offer mode), the `profile_selection_context.estimate_profile_source`
is populated the same way as for preset-based estimates. The E35 `ProfileSourceBadge` component
is reused verbatim.

### F.1 When to show the source badge in offer mode

**Show the badge:** when `status ∈ {fresh, stale}` AND `profile_selection_context !== null`.

**Do NOT show the badge:** when `status === "not_computed"` (see § E.3 — showing a source badge
for an absent estimate would be misleading).

### F.2 The honesty rule (NFR24-HONESTY-1)

> **Fallback estimates must not appear exact.**

| `estimate_profile_source` | Visual treatment | Badge rendered | Rationale |
|---|---|---|---|
| `exact_filament_mapping` | Full estimate numbers + `ProfileSourceBadge` (exact variant) | "Exact filament profile" (subtle outline badge) | Highest confidence; show numbers + badge |
| `default_material_profile` | Full estimate numbers + `ProfileSourceBadge` (default variant) | "Default {material} profile" (muted badge) | Reduced confidence; badge explicitly labels the fallback |
| `unavailable_no_profile` | Estimate numbers (if non-null) + no source badge | *(badge renders nothing)* | Absence of badge = honest signal; no "exact" decoration on a degraded result |

The FE must NOT special-case or suppress the `default_material_profile` badge in offer mode.
If the offer resolves via a material-default profile, the "Default {material} profile" badge must
appear. Hiding it would violate NFR24-HONESTY-1.

### F.3 OD-2 note — `spoolman_filament_ref` not sent in this slice

The backend supports an optional `spoolman_filament_ref` param on the estimate-by-offer path
(OD-2 default: absent → material-default only). Story 36.3 **does not send `spoolman_filament_ref`**.
As a result, offer-mode estimates in this slice will always resolve via `default_material_profile`
or `unavailable_no_profile` (unless the admin has configured an exact filament mapping at the
policy level for the offer's material). The `exact_filament_mapping` path is possible if the
E35 policy store maps a material to an exact filament without a spool ref, but the FE handles
all three sources identically via badge reuse — no special code for offer mode.

---

## G. i18n key recommendations

**Namespace:** `modules.member.offers.*` (per NFR24-I18N-1).

All keys must be added to **both** `apps/web/src/locales/en.json` **and** `apps/web/src/locales/pl.json`
with full parity and correct Polish diacritics.

**Convention:** `portal_label` and `printer_name` values from the API are DATA (admin-assigned strings)
and render untranslated. Only structural UI text uses i18n keys.
Quality tier values reuse the existing `modules.estimates.quality.{tier}` keys.

### G.1 Offer picker UI

| Key | English value | Polish value |
|---|---|---|
| `modules.member.offers.picker.heading` | "Published profiles" | "Opublikowane profile" |
| `modules.member.offers.picker.none_option` | "Standard estimate" | "Standardowy szacunek" |
| `modules.member.offers.picker.none_option_aria` | "Use standard estimate (no profile selected)" | "Użyj standardowego szacunku (bez wybranego profilu)" |
| `modules.member.offers.picker.offer_aria` | "Select profile: {{label}}" | "Wybierz profil: {{label}}" |
| `modules.member.offers.picker.quality_label` | "Quality: {{tier}}" | "Jakość: {{tier}}" |
| `modules.member.offers.picker.printer_label` | "Printer: {{printer}}" | "Drukarka: {{printer}}" |
| `modules.member.offers.picker.no_offers_for_material` | "No published profiles for {{material}} yet." | "Brak opublikowanych profili dla materiału {{material}}." |
| `modules.member.offers.picker.loading` | "Loading profiles…" | "Ładowanie profili…" |
| `modules.member.offers.picker.transport_error` | "Couldn't load published profiles." | "Nie udało się załadować profili." |
| `modules.member.offers.picker.retry` | "Retry" | "Spróbuj ponownie" |

### G.2 Offer-mode estimate states

| Key | English value | Polish value |
|---|---|---|
| `modules.member.offers.estimate.not_computed_chip` | "—" | "—" |
| `modules.member.offers.estimate.not_computed_title` | "Estimate not yet available" | "Szacunek jeszcze niedostępny" |
| `modules.member.offers.estimate.not_computed_detail` | "The estimate for this file with the selected profile hasn't been computed yet." | "Szacunek dla tego pliku z wybranym profilem nie został jeszcze obliczony." |
| `modules.member.offers.estimate.offer_unavailable_chip` | "—" | "—" |
| `modules.member.offers.estimate.offer_unavailable_title` | "Profile no longer available" | "Profil nie jest już dostępny" |
| `modules.member.offers.estimate.offer_unavailable_detail` | "The selected print profile is no longer published." | "Wybrany profil druku nie jest już opublikowany." |

### G.3 Accessibility labels (aria-only copy)

| Key | English value | Polish value |
|---|---|---|
| `modules.member.offers.picker.region_label` | "Print profile offers" | "Oferty profili druku" |
| `modules.member.offers.picker.selected_offer_aria` | "Selected: {{label}}" | "Wybrano: {{label}}" |

---

## H. Accessibility notes

### H.1 Keyboard and focus

- The `PublishedOfferPicker` is rendered as a `<fieldset>` with a `<legend>` (hidden visually
  if the heading is also visible, or shown as the primary heading). The `<legend>` text uses
  `modules.member.offers.picker.region_label`.
- Each offer option is a visually-styled `<label>` wrapping a hidden `<input type="radio">`.
  This gives native keyboard navigation (arrow keys cycle through offers in the group) without
  custom JS keyboard handling.
- Focus styles follow the existing ring pattern (`ring-2 ring-primary`) — no custom focus style.
- The "None" option is the first in the group and is selected by default, so Tab → first offer
  is already in a defined state (the "None" radio is focused and checked).

### H.2 Screen reader announcements

- The `<fieldset>` / `<legend>` pattern gives the group a name read by screen readers: "Print
  profile offers, group: [option 1], [option 2], …"
- Each radio label reads: `portal_label` + quality tier (if present) + printer name (if present).
  Use `aria-label` on the input if the visible label order (chip then text) differs from the
  natural reading order: `aria-label` = `modules.member.offers.picker.offer_aria` interpolated
  with `label`.
- When `selectedOfferId` changes, no imperative `aria-live` announcement is needed — the radio
  group's native selection change is announced by AT.
- The `not_computed` and `offer_unavailable` states render inside a `role="status"` region so
  that they are announced when they appear (non-interruptive polite live region).

### H.3 Color and status

- Quality tier chips reuse the existing quality tier styling (text labels + optional color
  accent). Status is never conveyed by color alone (WCAG 1.4.1 — icon or text label accompanies
  every state change).
- The `no_offers_for_material` muted notice carries no icon — it is purely muted text — but the
  text itself is the indicator (not color alone), which is acceptable for a purely informational
  notice.
- The transport error state uses `text-destructive` token but ALSO has the text "Couldn't load
  published profiles." — color + text, WCAG 1.4.1 satisfied.

### H.4 Hit targets

- Each radio pill card: minimum 44 × 44 px tap target (WCAG 2.5.5 AAA; match the existing
  `CatalogEstimateProfileSelector` pill sizing).
- The Retry button in the error state: standard `Button` primitive (already meets tap target).

### H.5 Reduced motion

No animations required for this component. The only visual change on selection is a class swap
(`ring-primary` vs no ring) — instant, no transition. Compliant with `prefers-reduced-motion`
without special handling.

---

## I. Visual baseline matrix for Story 36.3

Six baseline states × 4 Playwright projects = **24 PNG baselines** total.
Each baseline file must carry `baseline-reviewed: <date>` in its adjacent `.json` metadata or
in the test's `toMatchSnapshot` call comment.

| # | Baseline state | Description | Key assertion |
|---|---|---|---|
| 1 | **Picker populated — "None" selected** | `active === "stl"`, ≥1 published offer for the current material, "None" radio selected, rows show preset-based estimates. | Picker visible; "None" option checked; all rows show normal estimate chips. |
| 2 | **Picker populated — offer selected** | Same as #1 but an offer is selected; rows switch to offer-mode estimates (`fresh`, `exact_filament_mapping`). | Selected offer highlighted (ring-primary); chips show grams values; ProfileSourceBadge (exact) visible in expanded panel. |
| 3 | **Picker populated — offer selected, `default_material_profile`** | Offer selected; estimate returns `fresh` + `profile_selection_context.estimate_profile_source === "default_material_profile"`. | "Default {material} profile" source badge visible in expanded panel; chip shows grams value. |
| 4 | **`not_computed` state** | Offer selected; estimate returns `status: "not_computed"`. | Chip shows "—" (muted); expanded panel shows "Estimate not yet available" notice; no source badge; no spinner. |
| 5 | **No compatible offers** | `GET /api/profiles/offers/published?material=...` returns empty list. | Picker renders muted "No published profiles for {material} yet." text; no radio group; existing preset estimate path unaffected. |
| 6 | **Transport error** | `GET /api/profiles/offers/published` fails. | Picker renders error copy + Retry button; file list / preset estimates unaffected. |

**API stubs required** (consistent with existing visual test pattern in
`apps/web/tests/visual/api-stubs.ts`):
- `GET /api/profiles/offers/published` — stub variants: populated list, empty list, 500 error.
- `GET /api/estimates` with `offer_id` param — stub variants: `fresh` + exact, `fresh` + default,
  `not_computed`, `404` (offer unavailable).

**4 Playwright projects:** `desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`
(the existing vitest/Playwright project matrix).

---

## J. Acceptance-criteria handoff checklist for Story 36.3

The following checklist is the minimum set of ACs that `bmad-create-story` must lock Story 36.3
against. Each AC is concrete, testable, and traceable to this design artifact.

### J.1 Component and hook structure

- [ ] **AC-1** `PublishedOfferPicker` component exists in `apps/web/src/modules/estimates/components/`
  (or catalog equivalent — exact location confirmed at create-story via code recon).
- [ ] **AC-2** `usePublishedOffers(material: string)` hook exists; calls
  `GET /api/profiles/offers/published?material={material}` with cache settings per § D.5;
  is disabled when `!isAuthenticated`.
- [ ] **AC-3** `useOfferEstimate(stlHash: string, offerId: string)` hook exists (or `useEstimate`
  extended); calls `GET /api/estimates?stl_hash=...&offer_id=...`; does NOT send
  `spoolman_filament_ref`; uses cache key `["estimates", stlHash, { offerId }]`.
- [ ] **AC-4** `EstimateChip` accepts an optional `offerId` prop; when provided, uses
  `useOfferEstimate` instead of `useEstimate`; renders `not_computed_chip` copy (§ E.3) for
  `status === "not_computed"` and `offer_unavailable_chip` copy (§ E.7) for 404.
- [ ] **AC-5** `RowEstimatePanel` accepts an optional `offerId` prop; same switching logic as AC-4;
  renders the correct panels for `not_computed`, `offer_unavailable`, and normal states.

### J.2 FilesTab integration

- [ ] **AC-6** `FilesTab` maintains `selectedOfferId: string | null` state (default `null`).
- [ ] **AC-7** `PublishedOfferPicker` is rendered between `CatalogEstimateProfileSelector` and
  the STL file list, under the guard `active === "stl" && stlFiles.length > 0 && isAuthenticated`.
- [ ] **AC-8** `PublishedOfferPicker` does NOT render when `!isAuthenticated` (returns null; no redirect).
- [ ] **AC-9** When `preset.material_class` changes, `usePublishedOffers` is called with the new
  material. If `selectedOfferId` is not in the new offer list, it is reset to `null`.
- [ ] **AC-10** When `selectedOfferId !== null`, `EstimateChip` and `RowEstimatePanel` use offer
  mode for ALL STL rows simultaneously.
- [ ] **AC-11** When `selectedOfferId === null`, chip/panel use the existing preset mode — no
  behavioral change from the pre-36.3 implementation.

### J.3 Picker states

- [ ] **AC-12** Populated state (§ E.1): picker renders a `<fieldset>` radiogroup with "None"
  first; each offer shows `portal_label` + optional quality_tier chip + optional printer_name.
- [ ] **AC-13** No-offers state (§ E.2): picker renders
  `modules.member.offers.picker.no_offers_for_material` muted text; no radiogroup; no error styling.
- [ ] **AC-14** Transport error state (§ E.5): picker renders error text + Retry button; the
  existing preset estimate flow is unaffected.
- [ ] **AC-15** AuthGate state (§ E.6): picker renders null; `usePublishedOffers` is not called.

### J.4 Estimate states

- [ ] **AC-16** `not_computed` (§ E.3): chip shows `—` (muted); expanded panel shows
  `not_computed_title` + `not_computed_detail`; no source badge; no Retry; no spinner.
- [ ] **AC-17** `offer_unavailable` / 404 (§ E.7): chip shows `—` (muted); panel shows
  `offer_unavailable_title` + `offer_unavailable_detail`; next offer-list refetch clears
  `selectedOfferId` if the offer is absent from the new list.
- [ ] **AC-18** `fresh` / `stale` with `estimate_profile_source`: `ProfileSourceBadge` renders
  the correct variant (`exact` / `default` / nothing for `unavailable_no_profile`).
- [ ] **AC-19** Source badge is NOT shown when `status === "not_computed"`, even though
  `profile_selection_context` may be populated in the response.

### J.5 Honesty rule (NFR24-HONESTY-1)

- [ ] **AC-20** `default_material_profile` badge is displayed for offer-mode estimates that
  resolve via the material-default path — it is never suppressed or replaced with "exact."
- [ ] **AC-21** A vitest unit test asserts: rendering `EstimateDisplay` (or `RowEstimatePanel`)
  with `estimate_profile_source: "default_material_profile"` + `status: "fresh"` renders the
  "Default {material} profile" badge visible. This test must fail if the badge is hidden in
  offer mode.

### J.6 i18n and theming

- [ ] **AC-22** All new `modules.member.offers.*` keys (§ G) present in both `en.json` and
  `pl.json` with full parity and correct Polish diacritics.
- [ ] **AC-23** Zero inline hex colors in the new component. All tokens from `theme.css`.
- [ ] **AC-24** `portal_label` and `printer_name` values render untranslated (DATA convention).
- [ ] **AC-25** Quality tier chips reuse `modules.estimates.quality.{tier}` keys.

### J.7 Accessibility

- [ ] **AC-26** `PublishedOfferPicker` uses `<fieldset>` + `<legend>` semantics; each option is
  a native `<input type="radio">` (keyboard arrow-key navigation works out of the box).
- [ ] **AC-27** `not_computed` and `offer_unavailable` panels use `role="status"` for polite
  AT announcement.
- [ ] **AC-28** Status (error, unavailable) never conveyed by color alone — icon or text label
  accompanies every state indicator.

### J.8 Visual regression

- [ ] **AC-29** 6 baseline states × 4 Playwright projects = 24 PNGs, each with
  `baseline-reviewed:` annotation (§ I). API stubs for offer list and offer estimate must be
  added to `apps/web/tests/visual/api-stubs.ts` BEFORE the baseline capture run.
- [ ] **AC-30** `npm run test:visual` green (all 24 baselines pass) before merge.

---

## K. Risks / edge cases / deferred items

### K.1 G-ENQUEUE — explicitly out of scope

When `status === "not_computed"`, a member has no way to trigger an estimate. There is **no
"Request estimate" button, no enqueue CTA, no G-ENQUEUE logic** in Story 36.3. This is by design
(SCP § 3, SCP OD-4 — the on-demand enqueue question is a separate gate). If future operator
feedback shows the `not_computed` state is reached frequently and a member-triggered enqueue is
desired, a `G-ENQUEUE` gate should be named as a new work item and given its own UX pass before
implementation. **Do not pre-implement enqueue hooks or dead-code any enqueue path in 36.3.**

### K.2 Offer list overflow (>10 offers)

The backend currently returns all published offers in one response (no pagination). If an
operator publishes many offers for one material, the picker could become unwieldy. At MVP, this
is acceptable (Michał's homelab is single-operator; 2–4 offers per material is a realistic
ceiling). If growth necessitates pagination, add to triage backlog at that time.

### K.3 `quality_tier` null on an offer DTO

If a published offer's process block is unavailable at sidecar-read time, `quality_tier` is
`null`. The FE must handle this gracefully: omit the quality chip rather than rendering "null" or
crashing. The offer remains pickable.

### K.4 `printer_name` null on an offer DTO

Same as K.3 for `printer_name`. Omit the printer subtext, do not crash.

### K.5 Cross-material offer display

The `?material=` filter on `GET /api/profiles/offers/published` is the FE's responsibility to
apply correctly. If the FE forgets to send `?material=` and shows all offers regardless of
material, the member could select an offer and get an estimate for an incompatible material/offer
combination. The backend does not validate material compatibility in the estimate-by-offer path.
AC-7 (picker rendered with `material` filter from `preset.material_class`) mitigates this, and
the story should include a unit test asserting the filter param is always passed.

### K.6 `selectedOfferId` deselect edge case on fast material switch

If the member rapidly changes material and the offer list refetch arrives asynchronously, there
is a brief window where `selectedOfferId` refers to an offer not yet confirmed in the new list.
The estimate chips might show a 404 state briefly before the deselect logic clears the selection.
This is acceptable UX for MVP (< 1s; the deselect happens on the next render after the offer
list settles). A debounce or optimistic clear on material change could improve it; not required
for 36.3.

### K.7 `spoolman_filament_ref` param (OD-2 deferred)

OD-2 default is: FE does not send `spoolman_filament_ref`. This means offer estimates always use
the material-default or unavailable path, never the exact-filament path. The `ProfileSourceBadge`
will show "Default {material} profile" for most offer estimates. This is honest and correct. If
a future operator wants exact-filament offer estimates, OD-2 can be revisited by surfacing a
Spoolman filament selector in the offer picker UI — that is a new UX pass, not a 36.3 scope item.

### K.8 No offer selected — no visual residue

When `selectedOfferId === null` ("None" selected), there must be no leftover offer-mode UI in
the chip or panel. The components must cleanly restore to the pre-36.3 preset mode appearance.
A regression test (unit test or visual snapshot) should assert this.

---

## Gate disposition

- ✅ **G-UXGATE — SATISFIED by this artifact.** Story 36.3 FE authoring and dev-story execution
  may proceed. The `ux-profile-publish-2-member-offer-picker` sprint-status row is updated to
  `done`.
- ⛔ **G-ENQUEUE — NOT authorized, NOT designed, NOT a 36.3 concern.** See § K.1.
- ⛔ **G-36.2-DONE — externally gated.** Story 36.3 branch may not be opened until 36.2 is on
  `main` and sprint-status is `done`. (36.1 and 36.2 are reported on `main` by the controller;
  the sprint-status rows show `review` — those should be updated to `done` as part of the 36.1/36.2 close-out before 36.3 dev-story starts.)
- ⛔ **No deploy / no live `.190` smoke / no commit / no merge** performed by this UX pass.

---

## Cross-references

- SCP: `sprint-change-proposal-2026-06-13-profile-publish-2-member-offer-surface.md` § 7/§ 8 (G-UXGATE directive, OD-3 resolution).
- Architecture: `architecture.md` § Initiative 24 / Decision AT.
- Epics: `epics.md` § Initiative 24 / Story 36.3 (MEMBER-OFFER-UI-1, gated ACs unblocked by this artifact).
- PRD: `prd.md` § Initiative 24 (FR24-MEMBER-OFFER-UI-1, NFR24-HONESTY-1, NFR24-UNAVAIL-UX-1, NFR24-AUTHGATE-1, NFR24-I18N-1, NFR24-VISUAL-1).
- Live backend contracts: `apps/api/app/modules/slicer/member_router.py` (36.1), `apps/api/app/modules/slicer/router.py` lines 259–300 (36.2 offer path), `apps/api/app/modules/slicer/schemas.py` (`MemberPublishedOfferView`, `EstimateView`).
- Placement host: `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`.
- Hook to extend: `apps/web/src/modules/estimates/hooks/useEstimate.ts`.
- Badge reuse: `apps/web/src/modules/estimates/components/ProfileSourceBadge.tsx`.
- Prior UX style: `profile-admin-selector-ux-2026-06-04.md` (UX-PROFILE-1), `ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md` (UX-PROFILE-OFFER-1).
- Memory: [[feedback_scp_pre_enumeration_phase]], [[reference_web_routetree_regen]] (no new routes in 36.3 — the picker is a component addition within `FilesTab`, no route change; confirm at create-story recon).
