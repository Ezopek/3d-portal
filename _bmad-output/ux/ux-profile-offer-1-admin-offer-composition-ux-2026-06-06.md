---
title: "UX-PROFILE-OFFER-1 — Admin PrintProfileOffer Composition Surface (UX Design Checkpoint)"
artifact: ux-recommendation
topic: admin-print-profile-offer-composition-and-validation-surface
work_item: UX-PROFILE-OFFER-1
gate: G-UXGATE
initiative: 21
epic: E33
story: PROFILE-OFFER-1 (profile-offer-1-print-profile-offer-chain)
designer: Sally
date: 2026-06-06
canonical_path: _bmad-output/ux/ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md
status: done (UX checkpoint authored — satisfies G-UXGATE for PROFILE-OFFER-1; unblocks FE tasks T5/T6 against AC-16..AC-20. This is a lightweight admin-design checkpoint, NOT a member-facing UX pass and NOT a G-PUBLISH authorization. No app/test/config/infra code touched; no deploy, no commit by this pass.)
bmad_route: bmad-ux (Create UX, menu-code CU, phase 2-planning) — confirmed via session-start bmad-help routing; brownfield discovery/design-only carve-out, output under the git-tracked _bmad-output/ux/**/*.md UX surface per AGENTS.md (parallel to UX-PROFILE-1 profile-admin-selector-ux-2026-06-04.md).
scope: >
  UI/UX product design ONLY for the ADMIN offer-composition surface — no frontend/backend/infra/test/config
  code, no deploy, no commit, no live smoke. Designs the SURFACING of the Decision AN offer/chain validation
  model (slicer/profile_offer.py) the backend already owns as SoT; the validation rules themselves are
  backend SoT and are NOT re-litigated here. Member-facing surfaces are explicitly OUT of scope (the member
  selector keeps consuming the shipped 33.1/33.2 grid projection until G-PUBLISH).
source_artifacts:
  - _bmad-output/implementation-artifacts/profile-offer-1-print-profile-offer-chain.md — Story PROFILE-OFFER-1, AC-16..AC-20 (the FE ACs this checkpoint unblocks), AC-1..AC-15 (backend contract this surface renders), AC-22 (scope fence)
  - apps/api/app/modules/slicer/profile_offer.py — the validation engine SoT: OfferValidationState {usable, requires_attention, invalid}, the 8 reason categories, evaluate_offer/validate_chain/revalidate_offers (read-time revalidation), the {PLA,PETG,PCTG,TPU} material table
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md — § 3.4 (ProfileChain), § 3.5 (PrintProfileOffer), § 3.6 (material taxonomy), § 4 (grid = transitional projection, coexist, no migration), § 6 (PROFILE-OFFER-1 boundaries + deferred register), § 8 (UX checkpoint REQUIRED before relationship/offer-composition UI — THIS gate), § 9 (deferred register)
  - _bmad-output/planning-artifacts/architecture.md § Initiative 21 — Decision AN (offer/chain layer; this surface renders it), Decision AM (block library it consumes), AK/AL (grid projection, untouched)
predecessors:
  - UX-PROFILE-1 (done) — _bmad-output/ux/profile-admin-selector-ux-2026-06-04.md — the admin profiles grid + member selector design this checkpoint EXTENDS (SCP § 8 "extends UX-PROFILE-1"). Reuses its status-never-by-color-alone, admin-fails-closed, i18n-parity, and visual-baseline disciplines.
  - PROFILE-LIB-1 (done @221bbe1) — the block library this offer surface READS via useProfileLibrary; ProfileLibraryPage.tsx is the closest FE pattern reference (validation badges, curated-detail-no-raw-JSON expander, ConfirmDialog delete).
downstream: bmad-dev-story resumes PROFILE-OFFER-1 T5/T6 (FE offer surface + hooks + i18n + visual baselines) against this design. G-PUBLISH (resolver publication / live slicing over an offer) remains a SEPARATE, later, separately-gated slice — NOT authorized here.
operator_directive: >
  "Ok, lećmy 🙂 Niech bmad ogarnia 🙂" — delegated continuation, scoped by the controller as permission to
  run the UX checkpoint artifact required by G-UXGATE, NOT permission to deploy / live-smoke / publish
  resolver output. Honoured: this is a design-only artifact.
mockups: []  # No new HTML mockups this pass — the surface reuses the shipped ProfileLibraryPage / UsersPage visual language (validation badges, ConfirmDialog, AdminTabs shell). The layout is specified in prose + ASCII below; production uses Tailwind/theme classes, zero inline hex, reusing the UX-PROFILE-1 / PROFILE-LIB-1 badge token set.
---

# Admin PrintProfileOffer Composition — UX Design Checkpoint (G-UXGATE)

**Author:** Sally (UX Designer) — 2026-06-06
**Work item:** UX-PROFILE-OFFER-1 — the G-UXGATE checkpoint REQUIRED by PROFILE-OFFER-1 AC-16 / SCP § 8 before the FE offer-composition UI (T5/T6) is built.
**Surface:** one new ADMIN surface — an offer sub-tab/section under the existing admin "profiles" area (or a sibling `routes/admin/profile-offers.tsx`, dev's choice within the `AdminTabs` shell). It composes, lists, edits, and deletes `PrintProfileOffer`s over the shipped PROFILE-LIB-1 block library.

> **Routing note (mandatory protocol):** `bmad-help` consulted at session start. PROFILE-OFFER-1 AC-16 + SCP § 8 require a `bmad-ux`/Sally checkpoint (the canonical UIX route is **[CU] Create UX**, phase 2-planning) before the relationship/offer-composition UI is built, because *offer composition IS relationship UI* and must not regress into an Orca-GUI clone or an unusable N×M matrix. This is brownfield (PRD/architecture/epics for Init 21 exist and are approved; the backend AC-1..AC-15 is already dev-complete and green), authored as a focused UX recommendation on the git-tracked `_bmad-output/ux/**/*.md` surface, parallel to UX-PROFILE-1. **No PRD/architecture/app/test/config/code touched.** The next ceremony that turns this into work is `bmad-dev-story` resuming PROFILE-OFFER-1 T5/T6.

---

## TL;DR — recommendation

1. **The surface is admin-only and deliberately minimal: a list + a compose/detail panel.** List every offer with its label, its three selected block names, and one validation-state badge; compose/edit an offer in a side panel (or modal on mobile) with **exactly three single-select pickers** (machine, process, filament) over the existing library, a label field, a visibility toggle, a default toggle, and a `{PLA,PETG,PCTG,TPU}` material-category multi-select. **No N×M matrix, no Orca-GUI clone, no raw Orca JSON viewer/editor anywhere.** (§ B, § C)
2. **Product/UX frame — this is a validated offer/chain DATA surface, not ordering, not spool availability, not resolver publishing, not slicing.** Composing an offer writes a curated sidecar and runs a *dry* chain validation; it does **not** compile into the resolver intent path, does **not** slice, and does **not** change what members see. The member selector remains on the shipped 33.1/33.2 grid until G-PUBLISH. (§ A.0)
3. **One offer, one validation badge, by a fixed precedence: `invalid` > `requires_attention` > `usable`** — the same precedence `profile_offer.py` already computes server-side. The badge reuses the shipped PROFILE-LIB-1 token set (`usable` → success, `requires_attention` → warning, `invalid` → destructive). Every non-`usable` offer surfaces a human-readable *reason* per flagged category; **status is never conveyed by color alone** (icon + text + color). (§ A, § D)
4. **The chain (the three block refs) is IMMUTABLE after create; label/visibility/default/categories are editable.** This is a deliberate UX recommendation, not a limitation to fix — see § C.4 for the rationale (identity↔chain simplicity, no silent re-validation surprise, mirrors the backend PATCH contract AC-12). "Change the blocks" = delete + re-create, signposted in the edit panel. (§ C.4)
5. **Fail CLOSED/visible, like the UX-PROFILE-1 admin grid.** On a list/load error the surface shows an error panel with Retry — it never fabricates offers or falls open to "all usable." A create/edit rejection (e.g. `invalid_chain`, `unsupported_material_category`) surfaces the structured reason inline at the control; the offer is **not** silently stored. (§ D, § E)
6. **Read-time validation can flip an offer after a referenced block changes** (`revalidate_offers`, AC-10) — e.g. deleting a referenced block flips an offer to `invalid · unknown_block` on the next list. The surface must treat the badge as *live truth recomputed server-side*, never a cached create-time snapshot — hence `staleTime: 0` + `refetchOnMount: "always"` (AC-18). The detail panel explains the flip in plain language. (§ D.3, § E)
7. **Delete is behind a `ConfirmDialog`** (mirror `UsersPage` / `ProfileLibraryPage`), and the confirm copy states the honest blast radius: deleting an offer removes only the offer — it never touches the referenced library blocks (offers reference, they do not own). (§ C.5)

---

## Constraints in force (from the story + backend SoT + code reality)

- **Backend is the source of truth for validation.** `slicer/profile_offer.py` already computes `OfferValidationState ∈ {usable, requires_attention, invalid}` and the reason categories. UX designs the *surfacing*, not the rules. The FE localizes machine-readable reason CATEGORIES; **no display text comes from the backend** (AC-4).
- **Single-select per slot — NOT an N×M relationship grid (AC-17, AC-22).** Three independent single-selects (machine / process / filament). This is the explicit anti-pattern the gate exists to prevent (SCP § 8).
- **No raw Orca JSON rendered anywhere (AC-11, AC-17, AC-22).** The detail panel shows only the curated `chain_blocks` echo (block name, type, material_type, inherit chain, compatible_printers) — the same no-leak fence PROFILE-LIB-1's detail expander already honours. No file paths, no g-code, no Orca-internal keys.
- **Material category table is the small generic `{PLA, PETG, PCTG, TPU}`** (SCP § 3.6); an out-of-table category is rejected `422 unsupported_material_category` and never minted. This is NOT the grid's `compatibility.py` tier-compat map (untouched).
- **Frontend rule: zero inline hex** — theme tokens only. Reuse the UX-PROFILE-1 / PROFILE-LIB-1 badge token set (`--color-success`, `--color-warning`, `--color-destructive`, `text-muted-foreground`, `border-border`). No new color token is required by this surface.
- **i18n mandatory (AC-19, NFR21-I18N-PARITY-1)** — every user-visible string in both `en.json` + `pl.json`, full parity, correct Polish diacritics, under `modules.admin.profileOffers.*`. **Offer `label`s, block `name`s, and `material_type`s render as DATA (untranslated).**
- **Visual regression mandatory (AC-20, NFR21-VISUAL-VERIFICATION-1)** — new baselines across the 4 Playwright projects, gated on this design.
- **AuthGate discipline (Init 10 retro / CLAUDE.md):** the offer route defers to the shell `AuthGate` for anonymous and role-redirects only authenticated-non-admin — mirror `users.tsx` / `invites.tsx` / `profile-library.tsx` exactly. Admin-only surface; all five backend routes carry `current_admin` (AC-15).

---

## A.0 Product/UX frame — what this surface IS and is NOT (SCP § 4 / § 6 / AC-22)

This is the load-bearing framing the gate protects. State it on the surface itself (a quiet one-line subheader) so neither the operator nor a future agent mistakes it for more than it is:

| This surface IS | This surface is NOT |
|---|---|
| A **validated offer/chain DATA editor** — compose a `PrintProfileOffer` (one machine + one process + one filament block + label/visibility/default/categories) and see its dry validation state. | **Ordering / a quote** — no price, no spool, no request. |
| A **dry-validation preview** — `usable`/`requires_attention`/`invalid` computed by reading curated block manifests only. | **Resolver publishing or slicing** — composing an offer does NOT compile into the `intents/` path and does NOT slice (G-PUBLISH, deferred). |
| **Admin-only operator config** over the shipped block library. | **A member-facing surface** — members still use the shipped 33.1/33.2 grid selector; this surface changes nothing they see. |
| A **single-select-per-slot** composer. | **An N×M relationship matrix / an Orca-GUI clone / a raw-Orca JSON viewer-editor.** |
| **Spoolman-free** — material *categories* are the small generic bridge, not concrete spools. | A **Spoolman / spool-availability** surface. |

> **Member-UX boundary (SCP Appendix A):** turning an offer into a real member-facing choice is the explicitly-gated **G-PUBLISH** step (a later slice). This checkpoint neither designs nor authorizes it. The "default" and "visibility" controls here are *offer metadata for that future step*, validated now but not yet projected to any member surface.

---

## A. The offer validation-state model — one offer, one badge, by precedence

Every offer resolves (server-side, recomputed at read time) to **exactly one** primary state by this fixed precedence (top wins) — identical to `profile_offer._state_for`:

| # | State (badge) | Condition | Storable at create? | Meaning to the admin |
|---|---|---|---|---|
| 1 | **invalid** | any structural reason present (`unknown_block` / `wrong_block_type` / `block_unusable`) | **NO** — create is rejected `422 invalid_chain`; an *existing* offer can flip to invalid at read time (e.g. a referenced block was deleted) and is **kept, flagged** | The chain is structurally broken; the offer cannot be offered. |
| 2 | **requires_attention** | any non-structural flag present (`block_requires_attention` / `filament_machine_incompatible` / `material_category_mismatch` / `default_but_hidden` / `duplicate_default`) and no structural reason | **YES** — stored + listed + flagged | The offer is composed but has an operator-actionable concern. |
| 3 | **usable** | no reasons | YES | All three blocks present, correctly typed, compatible, consistent — ready (for the future G-PUBLISH step). |

**Why precedence, and why it matters for the surface:** the admin's primary scan is "is this offer OK?" — one badge answers it. The reason list is *secondary* detail behind the badge (inline on the row for `invalid`, in the detail panel otherwise). This is the same one-status-per-cell discipline UX-PROFILE-1 established for the grid, applied to the offer row.

### A.1 The eight reason categories → member-facing-free admin copy

The backend emits machine-readable categories; the FE localizes each to a short, honest admin line (i18n keys under `modules.admin.profileOffers.reason.*`). **No raw paths / g-code / Orca internals in any copy** (AC-19). Suggested English copy (Polish parity required, correct diacritics):

| Category (backend SoT) | State it drives | Suggested EN admin copy (i18n key sketch) |
|---|---|---|
| `unknown_block` | invalid | "A selected block no longer exists in the library." |
| `wrong_block_type` | invalid | "A selected block is the wrong type for its slot." |
| `block_unusable` | invalid | "A selected block can't be used." |
| `block_requires_attention` | requires_attention | "A selected block needs attention." |
| `filament_machine_incompatible` | requires_attention | "This filament isn't declared compatible with this machine." |
| `material_category_mismatch` | requires_attention | "The filament's material isn't in this offer's categories." |
| `default_but_hidden` | requires_attention | "This offer is marked default but hidden — it won't be offered." |
| `duplicate_default` | requires_attention | "Another visible offer is already the default for this material category." |

Endpoint-level rejection categories (surfaced inline at the compose control, never stored on reject — AC-9) also need keys: `invalid_chain`, `unsupported_material_category`, `invalid_offer`, `invalid_json`, and `not_found` (for a stale edit/delete target). Reuse the structured-error mapping pattern (`importRejectionCategory`) from PROFILE-LIB-1 (AC-18).

---

## B. Layout — list + compose/detail panel (the minimal admin flow, AC-17)

### B.1 Information architecture

- **Entry:** an offers section under the existing admin "profiles" area — either a new sub-tab in the profiles area or a sibling `routes/admin/profile-offers.tsx` within the `AdminTabs` shell (dev's choice; whichever keeps the admin chrome coherent with the shipped `profile-library` tab). `isAdmin`-gated, AuthGate discipline per § Constraints.
- **Two regions, compact:** a **list** (the scan target) + a **compose/detail panel**. Recommended desktop layout: list as the primary column, panel as a right-side drawer/inline panel that opens for *compose* (empty) or *detail/edit* (a selected offer). Mobile: the panel becomes a full-width modal/sheet (the three pickers + toggles stack vertically). This is the same list-plus-detail instinct as `ProfileLibraryPage`, not a new paradigm.

### B.2 The list

Each offer row shows, left→right:
- the offer **label** (DATA, untranslated) + optional one-line description;
- the **three selected block names** as a compact `machine · process · filament` trio (block `name`s are DATA) — names, never ids, never raw bodies;
- one **validation-state badge** (§ A) — and, for `invalid` rows only, the first reason inline (it's the most urgent and shouldn't require an expand);
- quiet **visibility** (hidden/visible) + **default** indicators (a small chip/icon, text-labelled);
- row actions: **edit**, **delete** (behind confirm).

Deterministic order matches the backend (`created_at` then `offer_id`, AC-10). Optional filters: `?material_category=` and `?visibility=` (AC-10) — render as the same flat filter-chip group `ProfileLibraryPage` uses.

```
  Offers                                              [ + Compose offer ]
  Filter:  [ All ]  [ PLA ] [ PETG ] [ PCTG ] [ TPU ]   ·   [ visible ] [ hidden ]
  ───────────────────────────────────────────────────────────────────────────────
  ● usable            "Rosa PLA — standard"      K1 Max · 0.20 MicroSwiss · Rosa PLA
                       visible · default(PLA)                         [edit] [delete]
  ⚠ requires_attention "Flex draft"              K1 Max · 0.20 TPU · Rosa Flex
                       hidden                     filament_machine_incompatible
                                                                      [edit] [delete]
  ✕ invalid            "Old PETG offer"           (machine) · 0.20 MicroSwiss · —
                       A selected block no longer exists in the library.
                                                                      [edit] [delete]
```

### B.3 The compose/detail panel

**Compose (new offer):** three single-select pickers + label + visibility toggle + default toggle + material-category multi-select + a live validation hint + a **Save** action. (§ C)

**Detail (existing offer):** the curated `chain_blocks` echo (block name, type, material_type, inherit chain, compatible_printers — NO raw JSON), the full reason list with the § A.1 copy, and an **Edit** affordance for label/visibility/default/categories. The chain pickers render **read-only** here (immutable — § C.4), with a "change blocks = delete + re-create" hint.

---

## C. Controls — the compose form (AC-17)

### C.1 The three single-select slot pickers

- **Three independent single-selects:** machine, process, filament. Each populated from `useProfileLibrary` filtered to the matching `profile_type` (the shipped library query — read-only consumption, no cross-invalidation, AC-18). Options show the block **name** (DATA); a block already in `requires_attention` may carry a small inline warning marker so the admin sees the propagation source before saving.
- **NOT an N×M matrix.** Three rows, three dropdowns. A combobox/searchable-select is fine if the library grows; a plain native `<select>` is an acceptable lower-effort floor (unlike the member tier control in UX-PROFILE-1, there is no per-option disabled-reason requirement here — every library block is a legal selection; validation happens on the composed chain, not per option).
- **No raw Orca preview** in or under the picker — at most the curated block name + type.

### C.2 Label / description

`label` is a required member/admin display string (DATA, untranslated), `description` optional. Mirror the `ProfileLibraryPage` upload label field.

### C.3 Visibility / default / material categories

- **Visibility toggle** — `hidden` (default) / `visible`. A clear two-state control (switch or segmented pair), text-labelled.
- **Default toggle** — `is_default` (default off). Pair it with a quiet helper that names the two attention cases the backend will flag: *default + hidden* → `default_but_hidden`; *two visible defaults sharing a category* → `duplicate_default`. Surfacing the rule *before* save reduces avoidable `requires_attention` states.
- **Material-category multi-select** — constrained to `{PLA, PETG, PCTG, TPU}` (AC-3/AC-9). Render as a 4-checkbox/chip group (materials untranslated). An out-of-table value is structurally impossible from the UI; the `422 unsupported_material_category` path is the defense-in-depth backstop, surfaced inline if it ever fires.

### C.4 Chain immutability after create — UX recommendation + rationale (AC-12)

**Recommendation: keep the chain immutable on edit** (the backend PATCH already forbids it, AC-12). On the detail/edit panel the three pickers are read-only with an explicit, friendly hint: *"To change the selected blocks, delete this offer and compose a new one."* The label/visibility/default/categories remain editable.

**Why this is the right UX, not a gap to close:**
1. **Identity stays simple.** `offer_id` is a minted token stable across label edits (AC-6); keeping the chain fixed means an offer's *meaning* (its three blocks) never silently changes under a stable id — an audit/diff reads cleanly.
2. **No silent re-validation surprise.** Editing a block ref would re-run the whole chain validation and could flip `usable → invalid` mid-edit; a delete + re-create makes that a deliberate, visible act.
3. **It mirrors the backend contract exactly** (AC-12 — chain immutable on PATCH), so the UI and API agree and there's no "the form let me change it but the server rejected it" mismatch.
4. **Chain mutation/versioning is explicitly deferred** (SCP § 9). If a future slice wants in-place chain edits, that's a deliberate product decision with its own validation-flow design — not something this minimal surface should fake.

(If a future operator finds delete+re-create too heavy at scale, that's the trigger to design chain-versioning — recorded as a deferred seam, not built here.)

### C.5 Delete — behind a confirm with honest blast radius (AC-13)

Delete sits behind a `ConfirmDialog` (mirror `UsersPage` / `ProfileLibraryPage`). The confirm copy states the truth: **deleting an offer removes only the offer; it does not touch the referenced library blocks** (offers reference, they do not own — AC-13). Re-deleting an already-gone offer surfaces a soft `not_found`, not a crash (idempotent-safe).

---

## D. Validation badge & reason surfacing; fails-closed (AC-17)

### D.1 Badge — reuse the shipped token set, never color alone

Reuse the PROFILE-LIB-1 / UX-PROFILE-1 badge tokens (icon + text + color, WCAG 1.4.1):

| Offer state | Icon | Token (reuse, no hex) | Treatment |
|---|---|---|---|
| **usable** | ● filled check | `bg-success/10 text-success` | The one positive/saturated badge. |
| **requires_attention** | ⚠ warning | `bg-warning/10 text-warning` | The actionable-concern badge. |
| **invalid** | ✕ / XCircle | `bg-destructive/10 text-destructive` | The structurally-broken badge; first reason inline on the row. |

This is the exact `StateBadge` mapping in `ProfileLibraryPage.tsx:36-38` (library uses `error` where offers use `invalid` — same destructive token, one new label key). No new color token required.

### D.2 Reason surfacing

- **invalid** → first reason inline on the list row (urgency); full list in the detail panel.
- **requires_attention** → badge on the row, full reason list in the detail panel (the § A.1 copy).
- **usable** → badge only, no reason text.

Every reason renders from its localized category key (§ A.1); the detail reason list mirrors `ProfileLibraryPage`'s `reasons` list styling (`text-warning`).

### D.3 Read-time-revalidation honesty (AC-10, AC-18)

The badge is **live truth recomputed server-side at read time**, not the create-time snapshot. Because a referenced block can be deleted/changed out from under an offer (`revalidate_offers`), the query MUST use `staleTime: 0` + `refetchOnMount: "always"` (AC-18) so the admin never sees a stale `usable`. When an offer has flipped (e.g. to `invalid · unknown_block`), the detail panel explains it in plain language ("A selected block no longer exists in the library — re-compose this offer with a current block"). No optimistic insert/remove; the list reconciles from the server (AC-18).

### D.4 Fails-closed / fails-visible

- **List load error** (`GET /offers` fails) → an **error panel with Retry** (mirror `ProfileLibraryPage` `error_title` + `retry`). The surface **fails CLOSED/visible** — it never fabricates offers or falls open to "all usable." (Same posture as the UX-PROFILE-1 admin grid: admin needs truth.)
- **Create/edit rejection** (`422 invalid_chain` / `unsupported_material_category` / `invalid_offer`, or `413` over-cap) → surface the structured reason inline at the form; **nothing is stored** (AC-9). The form stays populated so the admin can correct and resubmit; **no auto-retry** on writes (AC-18).

---

## E. States — usable / requires_attention / invalid + the edge cases + empty/loading/error

Per the task's required coverage, every state below has a defined treatment. The first eight are backend reason categories; the rest are surface states.

| State / case | Where it shows | Treatment |
|---|---|---|
| **usable** | row badge | success badge, no reason text. |
| **requires_attention** | row badge + detail | warning badge + reason list. |
| **invalid** | row badge + inline reason | destructive badge + first reason on the row, full list in detail. |
| **unknown_block / stale reference** | invalid | "A selected block no longer exists…" — the read-time-revalidation flip case; detail explains re-compose. |
| **wrong_block_type** | invalid | "A selected block is the wrong type for its slot." |
| **block_unusable** | invalid | "A selected block can't be used." (guarded; rare.) |
| **block_requires_attention** | requires_attention | "A selected block needs attention." — propagation; detail names which block. |
| **duplicate_default** | requires_attention | "Another visible offer is already the default for this material category." — both colliding offers flag (computed across the set). |
| **default_but_hidden** | requires_attention | "Marked default but hidden — it won't be offered." — surfaced *before* save by the § C.3 helper too. |
| **material_category_mismatch** | requires_attention | "The filament's material isn't in this offer's categories." |
| **filament_machine_incompatible** | requires_attention | "This filament isn't declared compatible with this machine." |
| **unsupported_material_category** | create reject (422) | inline at the material control; structurally unreachable from the chip UI, backstop only. |
| **invalid_chain / invalid_offer / invalid_json / 413** | create reject | inline at the form; nothing stored; form stays populated. |
| **not_found** | edit/delete of a vanished offer | soft message + refetch; never a crash. |
| **Empty** | list | "No offers composed yet — compose one to validate a machine + process + filament chain." (the compose affordance is present, not a dead end). |
| **Loading** | list | skeleton rows (mirror the library list), never a bare spinner. |
| **Error** | list | error panel + Retry, fails CLOSED/visible (§ D.4). |

---

## F. Accessibility, i18n, visual

### Accessibility
- **Status never by color alone** (WCAG 1.4.1): every badge is icon + text label + color (reuse the shipped `StateBadge`).
- **Form semantics:** each picker/toggle/multi-select has a programmatic label; the live validation hint and inline rejection are wired via `aria-describedby` / `role="alert"` (mirror `ProfileLibraryPage` error wiring).
- **ConfirmDialog** is focus-trapped + keyboard-dismissible (the shipped Radix/shadcn primitive).
- **Hit targets** ≥ the existing control sizing; the compose panel is operable on a Pixel-5 width (controls stack).

### i18n (NFR21-I18N-PARITY-1, AC-19)
- New keys under **`modules.admin.profileOffers.*`** — compose action/copy, the three `validation_state` labels, each of the eight `reason.*` categories + the create/edit rejection categories (`invalid_chain` / `unsupported_material_category` / `invalid_offer` / `invalid_json` / `not_found`), the filter labels, the three slot-picker labels, visibility/default labels, edit + delete-confirm copy.
- **Both `en.json` + `pl.json`, full parity, correct Polish diacritics.**
- **Offer `label`s, block `name`s, and `material_type`s render as DATA (untranslated)** (Init 19/20 convention). The validation-state badge labels reuse the PROFILE-LIB-1 badge label keys where the wording matches; `invalid` gets its own label (library used `error`).

### Visual / theming (zero inline hex)
- Reuse `--color-success` / `--color-warning` / `--color-destructive`, `text-muted-foreground`, `border-border`. **No new token required** by this surface (the one new token UX-PROFILE-1 added, `--color-success`, already shipped).
- Dark-mode variants come for free from the reused tokens.

### Visual regression (NFR21-VISUAL-VERIFICATION-1, AC-20)
Baselines across the 4 Playwright projects (desktop-light/dark, mobile-light/dark), each with a `baseline-reviewed:` sign-off — exactly the four AC-20 states:
1. **Offer list** — a mixed-state fixture: one `usable` + one `requires_attention` + one `invalid` offer in one screen.
2. **Compose panel open** — the three slot pickers + label + toggles + category multi-select.
3. **Create rejection** — e.g. `invalid_chain` (or `unsupported_material_category`) surfaced inline, nothing stored.
4. **Offer detail** — the curated chain blocks + a `requires_attention` reason (NO raw JSON).

API stubbed via `apps/web/tests/visual/api-stubs.ts` (offers GET/POST/PATCH/DELETE + a post-create list variant + a library list stub for the pickers, AC-20).

---

## G. How PROFILE-OFFER-1 FE acceptance criteria consume this design (AC mapping)

This checkpoint is the artifact AC-16 / SCP § 8 require. It unblocks the gated FE acceptance criteria:

| AC | What it requires | How this design satisfies it |
|---|---|---|
| **AC-16** (G-UXGATE) | A `bmad-ux`/Sally UX checkpoint, extending UX-PROFILE-1, signs off the composition layout so it does not regress into an Orca-GUI clone or N×M matrix; output is a `ux-profile-offer-1-*` artifact + sprint-status row. | **THIS artifact** (`ux-profile-offer-1-admin-offer-composition-ux-2026-06-06.md`) + the new sprint-status row. Layout signed off: list + compose/detail panel, single-select-per-slot, no Orca clone, no N×M, no raw JSON (§ A.0, § B, § C). **G-UXGATE satisfied.** |
| **AC-17** | Minimal admin surface: list + 3 single-select pickers + label/visibility/default/category-multi + validation badge + detail expander + edit + delete-confirm; single-select per slot; no raw Orca JSON; fails closed/visible. | § B (list + panel), § C (controls, single-select, immutable chain, delete-confirm), § D (badge + fails-closed). |
| **AC-18** | CRUD hooks + cache topology: `useProfileOffers`/create/update/delete, key `["admin","profile-offers"]`, `staleTime:0`+`refetchOnMount:"always"`, `retry:false`, invalidate-on-write, read-only consume of `useProfileLibrary`, no optimistic insert/remove, localized `reason_category`. | § C.1 (pickers read library read-only), § D.3 (read-time-revalidation → staleTime 0), § D.4 (no-auto-retry, server reconcile), § A.1 (localized reason categories). Cache-topology table in the story stands. |
| **AC-19** | i18n parity `modules.admin.profileOffers.*` en+pl + diacritics; reasons/states/filters/labels/edit/delete keys; data fields untranslated; reuse badge tokens; zero inline hex. | § F (i18n) + § A.1 (reason copy) + § D.1 (token reuse). |
| **AC-20** | Visual baselines for 4 UX-designed states × 4 projects, `baseline-reviewed:` per PNG, API stubbed. | § F (the four enumerated states = the AC-20 list, stub guidance). |

**FE tasks unblocked:** **T5** (FE offer surface — hooks + compose/list/detail/edit/delete + i18n + AdminTabs wiring) and **T6** (FE + visual tests — colocated vitest + the four Playwright baselines × four projects). Both were `⛔ gated on T4/G-UXGATE`; T4 (the UX checkpoint, AC-16) is now satisfied by this artifact. **T1–T3 backend stays as-is (dev-complete, green).** The remaining closeout (full `check-all.sh`, external review per AGENTS.md, ff-merge, G-SMOKE) is the controller's, unchanged.

---

## H. Gate disposition — what this checkpoint does and does NOT authorize

- ✅ **G-UXGATE — SATISFIED by this artifact.** The FE offer-composition surface (T5/T6) may now be built against this design. Recorded on the PROFILE-OFFER-1 story (Dev Agent Record / Gate disposition) and the sprint-status row.
- ⛔ **G-PUBLISH — NOT satisfied, NOT authorized.** This checkpoint does **not** authorize compiling an offer's `ProfileChain` into the resolver `intents/` path, running a live slice/estimate over an offer, or projecting an offer to any member surface. That is a separate, later, separately-gated slice (provisionally PROFILE-OFFER-2) with its own operator go and its own UX/runtime gates. The member selector keeps consuming the shipped 33.1/33.2 grid projection until then (SCP § 4 coexist, no forced migration).
- ⛔ **No deploy / no live `.190` smoke (G-SMOKE) / no commit / no merge** authorized or performed by this UX pass. Design-only, per the operator/controller scoping of the "Niech bmad ogarnia" delegation.

---

## Cross-references

- Story: `_bmad-output/implementation-artifacts/profile-offer-1-print-profile-offer-chain.md` — AC-16..AC-20 (unblocked), AC-1..AC-15 (backend rendered), AC-22 (scope fence), Dev Agent Record (gate disposition updated).
- Backend SoT: `apps/api/app/modules/slicer/profile_offer.py` — `OfferValidationState`, the 8 reason categories, `evaluate_offer` / `validate_chain` / `revalidate_offers`, `OFFER_MATERIAL_CATEGORIES`.
- Predecessor UX (extended): `_bmad-output/ux/profile-admin-selector-ux-2026-06-04.md` (UX-PROFILE-1) — status-never-by-color-alone, admin-fails-closed, i18n-parity, visual-baseline disciplines.
- FE pattern references: `apps/web/src/modules/admin/ProfileLibraryPage.tsx` (`StateBadge` tokens `:36-38`, curated-detail-no-raw-JSON expander, `ConfirmDialog` delete, error panel), `UsersPage.tsx` (multi-action + ConfirmDialog), `AdminTabs.tsx` (shell), `hooks/useProfileLibrary.ts` (read-only consumed by the pickers).
- SCP: `sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md` — § 3.4/§ 3.5/§ 3.6, § 4, § 6, § 8 (this gate), § 9, Appendix A (member-UX boundary).
- Architecture: `architecture.md` § Initiative 21 — Decision AN (rendered here), AM (consumed), AK/AL (grid, untouched).
- Memory: [[feedback_scp_pre_enumeration_phase]] — the magic-constant contract rule: the `{PLA,PETG,PCTG,TPU}` table, the badge token set, and the reason categories all point to the backend SoT (`profile_offer.py`), not to re-invented FE constants.
