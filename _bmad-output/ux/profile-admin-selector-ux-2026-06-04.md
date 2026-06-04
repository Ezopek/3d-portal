---
title: "UX-PROFILE-1 — Admin-Managed Orca Process Profiles: Admin Grid + User-Facing Selector (UX Design)"
artifact: ux-recommendation
topic: admin-managed-orca-process-profiles-grid-and-user-selector
work_item: UX-PROFILE-1
initiative: 21
epic: E33
designer: Sally
date: 2026-06-04
canonical_path: _bmad-output/ux/profile-admin-selector-ux-2026-06-04.md
status: done (deliverable authored — UX-PROFILE-1 design complete; the load-bearing Q1 material-exposure decision is now RESOLVED as Path B by the operator/controller 2026-06-04 — the catalog member selector SURFACES material, a deliberate, discipline-documented reversal of the shipped EST-DISPLAY-1 material-internal/PLA-pinned decision; member-selector FE ACs are now unblocked. Remaining open questions Q2–Q5 carry recommendations/defaults and do not gate Story 33.1.)
bmad_route: bmad-ux (Create UX, menu-code CU, phase 2-planning) — confirmed via session-start bmad-help; brownfield discovery-only carve-out, output under _bmad-output/ux/ per AGENTS.md tracked surface
scope: UI/UX product design ONLY — no frontend/backend/infra/test/config code, no deploy, no commit. Designs the SURFACING of the Decision AK compatibility map; the rules themselves are backend SoT.
source_artifacts:
  - _bmad-output/planning-artifacts/prd.md § Initiative 21 — FR21-COMPAT-1, FR21-SELECTOR-1, FR21-PROFILE-INVENTORY-1, NFR21-UX-1, NFR21-I18N-PARITY-1, NFR21-VISUAL-VERIFICATION-1
  - _bmad-output/planning-artifacts/architecture.md § Initiative 21 — Decision AK (inventory read + compatibility-map representation/enforcement, offerable = imported ∧ resolvable ∧ compatible), Decision AL (import write posture)
  - _bmad-output/planning-artifacts/epics.md § Initiative 21 — Epic E33, Story 33.1 (this artifact unblocks its FE ACs), 33.2, 33.3
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md § 9 (UX-PROFILE-1 directive), § 5 (OD-1 resolved, OD-7 compat map)
  - _bmad-output/implementation-artifacts/sprint-status.yaml — row ux-profile-1-admin-selector-ux-design
predecessors:
  - Initiative 20 / Epic E32 (shipped) — slicer resolver, EST-TIERS-1 availability seam (GET /api/estimates/quality-tiers), CatalogEstimateProfileSelector, EstimateDisplay
  - EST-DISPLAY-1 (shipped, est-display-1-filestab-estimate-chip) — the catalog Files/STL member selector that this work extends; deliberately exposes ONLY quality_tier (material PLA-pinned, internal)
downstream: bmad-create-story for Story 33.1 (read-only admin inventory + selector projection) — this artifact unblocks its FE acceptance criteria (NFR21-UX-1)
operator_directive: "UX involvement required so the frontend is done well; the user-facing selector must only ever offer compatible process/material combinations (TPU example), as good UX, not a crude dropdown."
note: >
  Canonical UX-PROFILE-1 deliverable, consolidated at the dated path on 2026-06-04. Authored earlier the
  same day as profile-admin-grid-and-selector-ux.md and renamed in place to the canonical
  profile-admin-selector-ux-2026-06-04.md — single source of truth, no duplicate. Mockup paths below are
  unchanged and still valid (same _bmad-output/ux/ directory).
mockups:
  - mockups/profile-admin-grid.html
  - mockups/profile-selector-states.html
---

# Admin-Managed Orca Process Profiles — Admin Grid + User Selector (UX Discovery)

**Author:** Sally (UX Designer) — 2026-06-04
**Work item:** UX-PROFILE-1 (REQUIRED, NFR21-UX-1) — blocks finalizing the FE acceptance criteria for Story 33.1 and the selector behavior.
**Surfaces:**
1. **Admin** — new `"profiles"` tab in `AdminTabs.tsx` → `routes/admin/profiles.tsx`: a `printer × material × quality-tier` inventory grid.
2. **Member** — the catalog `CatalogDetail → FilesTab (active === "stl")` process/quality selector (`CatalogEstimateProfileSelector.tsx`), extended so it only ever offers compatible combinations.

> **Routing note (mandatory protocol):** `bmad-help` was invoked at session start. The catalog's canonical UIX route is **`[CU] Create UX` (`bmad-ux`, phase 2-planning, preceded-by `bmad-prd`)**. This is brownfield (PRD/architecture/epics for Init 21 already exist and are approved); the operator scoped the task as discovery/design-only with an explicit deliverable shape, so this is authored as a focused UX recommendation under the `bmad-ux` output surface (`_bmad-output/ux/**/*.md`, a git-tracked path per AGENTS.md). **No PRD/architecture/code touched.** Next ceremony that turns this into work is `bmad-create-story` on Story 33.1, which consumes this artifact to lock its FE ACs.

---

## TL;DR — recommendation

1. **The load-bearing model is `offerable = imported ∧ resolvable ∧ compatible`.** Every slot resolves to exactly **one** of four statuses by a fixed precedence: **Incompatible → Not imported → Not resolvable → Offerable**. `compatible` is a structural property of the `(material, tier)` cell (from the Decision AK compat map); `imported`/`resolvable` are file/resolve properties. (§ A)
2. **Admin grid = a 4×3 status matrix** (material rows × tier columns) for the single v1 printer, with one status badge per cell, a human-readable reason for every non-offerable cell, a legend, and provenance behind a per-cell affordance. **Matrix on desktop, stacked per-material cards on mobile.** (§ B)
3. **Member selector — the disabled-vs-hidden decision is answered as a HYBRID, split by cause** (this is the core UX call the operator asked for):
   - **Compatible-but-unavailable** (not imported / not resolvable) → **disabled-with-explanation** (visible, greyed, reason in tooltip + aria + helper line). It's a real tier that can light up once the admin imports — telling the member it exists is honest; hiding it erases a known option.
   - **Incompatible** (structurally invalid for the chosen material) → **hidden** from the member. It will *never* be valid for this material; showing it disabled would falsely imply it might unlock. It lives only in the admin grid. (§ C)
4. **The floor invariant holds either way:** a member can never *select* an unofferable slot (disabled and hidden both prevent selection), so **NFR21-NO-422-1** is preserved structurally. (§ C)
5. **Preserve the shipped EST-TIERS-1 fail-OPEN posture on the member surface** (Standard is never locked out on a transient availability-fetch error/loading); the **admin grid fails CLOSED/visible** (shows an error panel, never fabricates slot statuses). Different surfaces, deliberately different postures. (§ E)
6. **Upgrade the tier control from a native `<select>` to a segmented pill group** so each disabled tier can carry an accessible inline reason (native `<option disabled>` cannot). Native-select-plus-helper-line is the documented lower-effort fallback. (§ C.3)
7. **The one flagged operator decision is now RESOLVED as Path B (operator/controller, 2026-06-04):** the catalog member selector **surfaces material** — this makes the TPU directive live on the main member surface and is a **deliberate reversal** of the shipped EST-DISPLAY-1 "material internal / PLA-pinned" decision, taken under NFR-carve-out-reversal discipline (old rationale / new requirement / preserved invariant / mechanism in § H / Q1). The admin grid and compatibility model are unchanged by the choice; only the member-selector material control is now in 33.1's FE scope.

---

## Constraints in force (from operator brief + code reality)

- **`offerable = imported ∧ resolvable ∧ compatible`** (PRD FR21-COMPAT-1; architecture Decision AK). Resolvability is **necessary but not sufficient** — a resolvable-but-incompatible slot (e.g. a PLA-class process profile sitting in a TPU slot) must read as **not offerable**, never "available."
- **The grid is fixed but NOT uniformly populated.** `{aesthetic, standard, strong} × {PLA, PETG, PCTG, TPU}` (the named FE↔BE `QualityTier`/`MaterialClass` contract — `QUALITY_TIERS` in `apps/web/src/modules/estimates/lib/preset.ts:25`, `MATERIAL_CLASSES` at `:18`). Some cells are legitimately incompatible. **TPU is the worked example** (§ D): TPU requires dedicated, declared-compatible process profiles.
- **Backend is the source of truth for compatibility.** UX designs the *surfacing*, not the rules. The concrete per-material compatible-slot set is admin data, confirmed at the data phase (Q5).
- **The member surface is an orientational gram-ESTIMATE preview, not ordering and not spool availability** (EST-DISPLAY-1 product framing, `CatalogEstimateProfileSelector.tsx:22-34`). No quote, no spool semantics. This artifact does not re-open that — except where Q1 (material exposure) forces an explicit operator choice.
- **Single printer in v1** — `creality-k1-max-microswiss-hf` (`CATALOG_ESTIMATE_PRINTER_REF`, `preset.ts:43`; OD-5). The grid shows one printer context; a printer registry is a future initiative.
- **Read-only first (Story 33.1).** The admin grid is a read-only list view; import/manage *actions* (33.2/33.3) are designed here as affordance placeholders only, so the visual language is forward-compatible — but 33.1 ships no write surface.
- **Frontend rule: zero inline hex** — theme tokens only (`bg-card`, `border-border`, `text-muted-foreground`, `--color-warning`, …). New semantic colors → add a `--color-*` token to `@theme {}` in `theme.css`, then use the Tailwind class. The static HTML mockups approximate the tokens for illustration; production uses Tailwind/theme classes.
- **i18n mandatory** — every user-visible string in both `en.json` + `pl.json`; material names PLA/PETG/PCTG/TPU stay untranslated (Init 19/20 precedent).
- **Visual regression mandatory** (NFR21-VISUAL-VERIFICATION-1) — new baselines across the 4 Playwright projects, gated on this design.

---

## Current state (read from code, 2026-06-04)

**Admin chrome** — `apps/web/src/modules/admin/AdminTabs.tsx`: `type ActiveTab = "users" | "invites"`, two `<Link role="tab">` entries to `/admin/users` and `/admin/invites`, active style `border-primary text-foreground`, inactive `border-transparent text-muted-foreground`. Routes mirror in `routes/admin/`. **There is no profiles tab today.** UX-PROFILE-1 adds a third: extend `ActiveTab` with `"profiles"`, add `routes/admin/profiles.tsx`, gate on `useAuth().isAdmin`.

**Member selector** — `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx` (the live EST-DISPLAY-1 surface):

- A right-aligned native `<select>` exposing **only `quality_tier`** (`QUALITY_TIERS` = aesthetic/standard/strong). Material is **PLA-pinned and internal** (`:28-33` — "Material class is held at the EST-INGEST-1 default (PLA)… never surfaced here"). The Spoolman pin stays `null`. Material + filament selection live only on the standalone `/estimates` surface.
- Availability comes from `useQualityTierAvailability(materialClass, printerRef)` → `GET /api/estimates/quality-tiers` → `{ printer_ref, material_class, tiers: [{ quality_tier, available, reason }] }`. Today `reason` is `"profile_not_imported" | string | null`.
- **Disabled mechanism today:** unavailable tiers render as `<option disabled>` with label `modules.estimates.selector.profile_unavailable_option` ("{profile} — unavailable"). The reason string is **not surfaced** to the member — a native `<option>` cannot carry an accessible per-option explanation.
- **Fail-OPEN invariant (load-bearing, keep it):** `isAvailable(tier) = availabilityByTier.get(tier)?.available !== false` (`:46-53`). An omitted prop (standalone use), an empty list (still loading), or a missing row (fetch errored) all leave the tier **selectable** — "a disabled-everything selector on a transient fetch error would be worse than the 422 this gate closes." **Standard is never locked out.**

**Why this matters for UX-PROFILE-1:** the member surface currently has (a) no material control and (b) a disabled mechanism that hides its own reason. Both are exactly what this design must resolve to deliver "good UX, not a crude dropdown." Init 21 extends `{quality_tier, available, reason}` so `available` folds in the compatibility dimension and `reason` carries the incompatibility cause (PRD FR21-SELECTOR-1) — the DTO shape is preserved; the *presentation* is what we design.

---

## A. The status model — one cell, one status, by precedence

Every `(printer_ref, material_class, quality_tier)` slot carries the Decision AK DTO `{imported, resolvable, compatible, reason, portal_label, provenance}`. Three booleans yield up to four meaningful states; the UI must show **exactly one primary status per cell**, chosen by this **precedence** (top wins):

| # | Status (displayed) | Condition | Meaning | Actionable? |
|---|---|---|---|---|
| 1 | **Incompatible** | `compatible === false` | This `(material, tier)` recipe is **structurally not valid** for this material class (compat map). Permanent. | No — importing here is meaningless. |
| 2 | **Not imported** | `compatible && !imported` | The slot is a valid recipe but **no profile is installed yet**. Transient — an admin import lights it up. | Yes (import, in 33.2). |
| 3 | **Not resolvable** | `compatible && imported && !resolvable` | A profile is installed but **fails to resolve** (malformed / missing required keys / classified resolver failure). Needs operator attention. | Yes (re-import / fix, 33.2/33.3). |
| 4 | **Offerable** | `imported && resolvable && compatible` | Installed, resolves, valid → **offered to members.** | Manage (label/disable/delete, 33.3). |

**Why precedence, and why Incompatible first:** `compatible` is a property of the *cell*, independent of any file. A cell that is incompatible should never invite an import (status 2/3) nor read as offerable (status 4) — so it is reported first and rendered as a structural N/A. This precedence is the single rule both the admin grid and the member-selector projection follow, which is what lets a shared test assert "neither surface offers an incompatible slot" (PRD FR21-COMPAT-1 verifiable clause).

**This maps 1:1 to the four task-required states:** offerable / not imported / not resolvable / incompatible.

---

## B. Admin profile grid (Story 33.1 — read-only)

### B.1 Information architecture

- **Tab:** `Profiles` joins `Users` / `Invites` in `AdminTabs` (extend `ActiveTab` → `"profiles"`, route `routes/admin/profiles.tsx`, `isAdmin`-gated). Follow the **shell-level AuthGate discipline** (Init 10 retro / CLAUDE.md): the route component fires the role-tier redirect **only for authenticated-non-admin**; for anonymous it defers to the shell `AuthGate` (no synchronous `<Navigate>` that strips `?next=`). Mirror `users.tsx`/`invites.tsx` exactly.
- **Printer context header:** `Printer: Creality K1 Max · Microswiss HF` with a quiet "single printer (v1)" note. One printer in v1 → a header, not a selector. (Forward-compat: when a printer registry lands, this becomes a printer picker above the grid; the grid below is unchanged.)
- **Legend:** the four statuses with their icon + color + one-line meaning. Always visible (the grid is unreadable without it for a first-time admin).

### B.2 Layout — matrix (desktop) / stacked cards (mobile)

**Desktop — a 4×3 matrix.** Rows = `material_class` in resolve order (PLA, PETG, PCTG, TPU); columns = `quality_tier` in `QUALITY_TIER_ORDER` (Aesthetic, Standard, Strong). The matrix is the right shape because the admin's primary scan is *pattern* recognition — "TPU only has Strong; everything else is set up" — which a flat list buries.

```
            Aesthetic        Standard         Strong
  PLA       ● Offerable      ● Offerable      ○ Not imported
            "standard"                         + Import (33.2)
  PETG      ○ Not imported   ● Offerable      ○ Not imported
  PCTG      ⚠ Not resolvable ● Offerable      ○ Not imported
  TPU       ▦ Incompatible   ▦ Incompatible   ○ Not imported
            (not valid for TPU)               + Import (33.2)
```

Each cell shows: **status badge (icon + label)** · for **Offerable**, the `portal_label` + a provenance affordance (ⓘ) · for **Not imported (compatible)**, a disabled "Import" affordance placeholder (signposts 33.2; greyed/inert in the read-only slice — Q4) · for **Not resolvable**, the structured failure reason inline or on hover · for **Incompatible**, a muted "not valid for {material}" subtext and **no action**.

**Mobile — stacked cards.** One card per `material_class`; inside, three tier rows (`[badge] Aesthetic — reason`). The matrix collapses because a 3-column grid with reason text doesn't fit a Pixel-5 width without truncating the reason — and the reason is the whole point. (Same responsive instinct as the EST-DISPLAY-1 desktop-table → mobile-stack pattern.)

### B.3 Status visual language (theme tokens, never hex)

| Status | Icon | Color token | Treatment |
|---|---|---|---|
| **Offerable** | ● filled check | `--color-success` *(new — see § F)* | Solid badge `bg-success/10 text-success`, portal_label in `text-foreground`. |
| **Not imported** | ○ dashed ring | `text-muted-foreground` + `border-dashed border-border` | Neutral, *empty-but-valid*. Reads as "slot awaiting a profile," not an error. |
| **Not resolvable** | ⚠ warning | `--color-warning` (exists) | `bg-warning/10 text-warning`; the only status that signals "operator: something is broken." |
| **Incompatible** | ▦ hatch / `—` | `text-muted-foreground` (de-emphasised) | Hatched/muted cell, **lowest visual weight** — structurally out of the offering. Distinct from "Not imported": incompatible is *not actionable*, not imported *is*. |

**Critical distinction the operator named — "how an incompatible slot is visually distinguished from an available one":** Offerable is the **only** status that gets a saturated/positive color (success green). Incompatible is the **most de-emphasised** (muted hatch, no action). Not-imported is neutral-with-affordance; Not-resolvable is the lone warning. No two statuses share a color, and **status is never conveyed by color alone** — icon + text label accompany every cell (WCAG 1.4.1; § F).

### B.4 Provenance disclosure

`provenance: { source_system_tree_hash, orca_version }` is **secondary** — it must not crowd the status, which is the scan target. Recommendation: a per-cell **ⓘ popover** (or an expandable detail row on mobile) revealing `orca_version` and a **short** `source_system_tree_hash` (first 12 chars, monospace, with copy). **Hard fence (mirror the DTO no-leak rule):** the grid surfaces **no Orca-internal keys, no file paths, no g-code** — only the projected provenance fields. The UI is the second line of defence; the backend DTO is the first.

---

## C. Member selector — disabled-with-explanation vs hidden (the core decision)

### C.1 The decision: HYBRID, split by *why* a slot is not offered

The operator asked for a deliberate decision. The honest answer is that "not offered" has **two ontologically different causes** that deserve **different treatments**:

| Cause | Nature | Treatment | Rationale |
|---|---|---|---|
| **Compatible but unavailable** (not imported / not resolvable) | **Transient / operational** — the admin can make it available | **DISABLED-with-explanation** (visible, greyed, reason) | It's a *real* tier for this material that just isn't set up. Telling the member "Strong isn't available yet" is honest and preserves the shipped EST-TIERS-1 behavior. Hiding it would erase a known, soon-possible option and make the selector feel arbitrary. |
| **Incompatible** (compat map says invalid for this material) | **Permanent / structural** — it will *never* be valid for this material | **HIDDEN** from the member | Showing a disabled "TPU · Aesthetic" implies it might unlock — it never will. For the member, an incompatible combination is *not a choice that exists* for this material. It is surfaced only in the admin grid, where the structural fact is the admin's concern. |

**Why not the two pure options:**
- **All-disabled** (show every non-offerable tier greyed): clutters the member surface with impossible combinations and *teases* recipes that can never exist for the chosen material. Fails the "good UX, not a crude dropdown" bar.
- **All-hidden** (show only offerable tiers): opaque. The member loses the "Standard is a thing, it's just not imported yet" signal that EST-TIERS-1 deliberately gives, and a tier silently vanishing reads as a bug.

The hybrid keeps the *transparency* of disabled where it's earned (operational gaps) and the *cleanliness* of hidden where it's right (structural impossibility).

### C.2 The floor invariant (independent of the above)

**A member can NEVER select a non-offerable slot.** Disabled prevents selection (`if (!isAvailable(tier)) return;`, `CatalogEstimateProfileSelector.tsx:66`); hidden removes it entirely. Either way the selector cannot re-key an estimate read into a resolver 422 → **NFR21-NO-422-1 holds structurally**, regardless of which treatment a slot gets.

### C.3 Control type — upgrade for the reason

The native `<select>` + `<option disabled>` **cannot carry an accessible per-option reason** (no tooltip, no `aria-describedby` per option). Since the whole point is "explain *why*," recommendation:

- **Primary: a segmented pill group for the 3 tiers** (a Radix/shadcn ToggleGroup-style control). Each pill is independently disabled-able and carries its reason via tooltip + `aria-describedby`. Three options fit a pill row comfortably, even on mobile. Disabled pills read greyed with a small ⓘ; the active pill uses `border-primary`.
- **Fallback (lower effort, still satisfies the contract): keep the native `<select>`** but (a) keep the disabled options, (b) add a **helper line** under the control naming the currently-disabled tiers and why ("Strong isn't available for PLA yet — not imported"), wired via `aria-describedby`. This preserves the shipped component with minimal change while still surfacing the reason.

Either control: **incompatible tiers are absent** (hidden, per C.1), **compatible-unavailable tiers are present-but-disabled-with-reason.**

### C.4 Reason copy (member-facing, short, honest)

| Slot state | Member-facing message (i18n key sketch) |
|---|---|
| Not imported | `modules.estimates.selector.reason_not_imported` — "Not available yet" (tooltip: "This quality isn't set up for {material} yet.") |
| Not resolvable | `modules.estimates.selector.reason_unavailable` — "Not available" (tooltip: "This profile can't be used right now.") — member sees a *soft* unavailability, **not** the raw resolver failure class (that's admin-only detail). |
| Incompatible | *(hidden — no member copy)* |

The member never sees resolver internals or the word "incompatible" — they see a clean set of valid choices plus, where honest, a greyed "not available yet."

---

## D. TPU worked example (the operator's named case)

**Setup.** Suppose the compat map (Decision AK / Q5 admin data) declares, for `material_class = TPU`, that only `strong` is a TPU-compatible process slot (`aesthetic`, `standard` are **not** valid TPU recipes); and suppose the operator has not yet imported the TPU·Strong profile.

**Admin grid (TPU row):**

| Cell | `{compatible, imported, resolvable}` | Displayed status | Reason shown |
|---|---|---|---|
| TPU · Aesthetic | `{false, –, –}` | **▦ Incompatible** | "Not a valid process for TPU." — no import action. |
| TPU · Standard | `{false, –, –}` | **▦ Incompatible** | "Not a valid process for TPU." — no import action. |
| TPU · Strong | `{true, false, –}` | **○ Not imported** | "No TPU·Strong profile installed yet." — **+ Import** (33.2). |

The admin sees, at a glance: TPU offers exactly one recipe slot (Strong), currently empty and importable; the other two are structurally off the table. If the admin later tries (33.2) to import a **PLA-class process profile into TPU·Strong**, it is **rejected with a structured reason** even though it might *resolve* — `resolvable ∧ ¬compatible` is still not offerable (FR21-COMPAT-1 enforcement). The rejection surfaces in the grid.

**Member selector (when material resolves to TPU):**
- `Aesthetic` and `Standard` are **hidden** (structurally incompatible — never teased).
- `Strong` is **shown disabled-with-explanation** ("Not available yet") until the admin imports it; the instant a compatible TPU·Strong profile is imported and resolves, `Strong` becomes **selectable** and the member can read its estimate. **At no point can the member pick a non-TPU process for TPU**, and at no point do they hit a 422.

This is the directive — "TPU only offers TPU-compatible process/profile choices" — realised as: *incompatible → invisible to the member; compatible-but-unavailable → visible, honest, disabled; compatible-and-ready → offered.*

> **Note (Q1 RESOLVED — Path B):** "when material resolves to TPU" presumes material is *known* on the member surface. With Q1 resolved as **Path B** (§ H / Q1), the catalog selector now **surfaces material**, so this TPU example is live on the **catalog member selector** as well as the admin grid and the standalone `/estimates` surface. The compatibility model and admin design are unchanged by the resolution.

---

## E. States — empty / loading / error (both surfaces)

**Admin grid:**
- **Loading:** a skeleton matrix (4×3 placeholder cells) — never a spinner-only blank.
- **Empty (nothing imported):** the grid still renders **all** slots — compatible-empty cells as **Not imported**, structurally-invalid cells as **Incompatible**. There is no "blank grid"; the empty state *is* the all-not-imported grid, plus a one-line hint: "No profiles imported yet — import one to offer it to members" (the import affordance is 33.2; in 33.1 it's an inert placeholder).
- **Error (`GET /api/admin/profiles` fails):** an **error panel with Retry**. The admin grid **fails CLOSED/visible** — it must **not** fabricate slot statuses or fall open to "all offerable." Admin needs truth; a wrong grid is worse than an honest error.

**Member selector:**
- **Loading / empty / fetch error → fail OPEN, unchanged from EST-TIERS-1** (`CatalogEstimateProfileSelector.tsx:46-53`): tiers stay **selectable**, Standard is never locked out. Compatibility **hiding** and availability **disabling** apply **only** once the backend positively declares the state. A transient failure must never strand the member with an empty/all-disabled selector. (Deliberate asymmetry with the admin grid: the member needs a working default more than they need the truth; the admin is the opposite.)

This asymmetry is itself a design decision worth stating: **admin fails closed/visible, member fails open** — same data, opposite consequence of being wrong.

---

## F. Accessibility, i18n, visual

### Accessibility
- **Status never by color alone** (WCAG 1.4.1): every status badge is **icon + text label + color**. The matrix is legible in greyscale and to color-blind users.
- **Grid semantics:** `role="table"` (or a real `<table>`) with `scope="col"` tier headers and `scope="row"` material headers; each cell's status + reason is screen-reader reachable (not tooltip-only).
- **Member disabled options:** `aria-disabled` + `aria-describedby` → the reason node, so a screen reader announces "Strong, dimmed, not available yet." **Hidden (incompatible) options are removed from the DOM/tab order** — not merely visually hidden — so they don't confuse AT.
- **Focus order** logical; popovers (provenance) are keyboard-dismissible and focus-trapped per the shadcn/Radix primitives already in use.
- **Hit targets** ≥ the existing control sizing; pill group remains tappable on mobile.

### i18n (NFR21-I18N-PARITY-1)
- New keys under **`modules.admin.profiles.*`** — tab label, column/row headers, the four status labels, each non-offerable **reason**, the legend, provenance labels, empty/error copy.
- New keys under **`modules.estimates.selector.*`** — the member reason strings (`reason_not_imported`, `reason_unavailable`).
- **Both `en.json` + `pl.json`, full parity, correct Polish diacritics.** **Material names PLA/PETG/PCTG/TPU stay untranslated** (Init 19/20 convention). Quality tier display reuses existing `modules.estimates.quality.*`.

### Visual / theming (zero inline hex)
- Reuse `--color-warning` (Not resolvable), `text-muted-foreground` + `border-border` (Not imported / Incompatible), `--color-destructive` (fetch error).
- **Add one new token: `--color-success`** (+ its `.dark` variant) in `@theme {}` in `theme.css` for the **Offerable** status — there is no positive/green semantic token today, and Offerable needs to be the one saturated-positive status. This is the only new color the design requires; introduce it via the token rule, not inline.
- Dark-mode variants for every status (the `.dark { --color-* }` pattern, picked up by `@custom-variant dark`).

### Visual regression (NFR21-VISUAL-VERIFICATION-1)
Baselines to capture across the 4 Playwright projects (desktop-light/dark, mobile-light/dark), each with a `baseline-reviewed:` sign-off:
1. Admin grid — a **mixed-status** fixture exercising all four statuses in one screen (incl. the TPU row).
2. Admin grid — **empty** state (all not-imported / incompatible).
3. Admin grid — **error** panel.
4. Member selector — **offerable + compatible-unavailable (disabled-with-reason) + incompatible-hidden** in one fixture.
5. Provenance popover open (desktop).

---

## G. How Story 33.1 (PROFILE-ADMIN-1) FE acceptance criteria consume this design

The sprint-status row records UX-PROFILE-1 as **blocking the FE ACs for 33.1 (grid) + the selector**. This artifact unblocks them. The FE ACs `bmad-create-story` should lock against this design:

1. **One-status-per-cell by precedence** — the grid renders every `(material, tier)` slot with exactly one of {Offerable, Not imported, Not resolvable, Incompatible} per § A precedence; an incompatible cell renders as structural N/A (de-emphasised, **not actionable**) and **never** as "available." (Realises FR21-COMPAT-1 read-only surfacing.)
2. **Reason on every non-offerable cell** — human-readable, from the precedence-mapped i18n key (§ B.3 / C.4). (NFR21-UX-1.)
3. **Visual distinction** — Offerable is the only positive-color status; Incompatible is the most de-emphasised; no two statuses share a color; status carries icon + text, not color alone (§ B.3, § F). (NFR21-UX-1, a11y.)
4. **Provenance affordance** on offerable cells (short snapshot hash + orca_version, popover); **no Orca-internal/path/g-code leak** in the rendered grid (§ B.4) — visual mirror of the DTO fence. (FR21-PROFILE-INVENTORY-1.)
5. **Member selector behavior** — compatible-but-unavailable → disabled-with-explanation; incompatible → hidden; **Standard never locked out** (fail-open preserved, § C.2/E). (FR21-SELECTOR-1, NFR21-NO-422-1.)
6. **Projection parity has a visual counterpart** — the member selector never renders an option the projection marks incompatible (the shared-projection test asserts data; the snapshot asserts presentation). (FR21-COMPAT-1 verifiable clause.)
7. **i18n parity** keys enumerated (§ F); material names untranslated. (NFR21-I18N-PARITY-1.)
8. **Visual baselines** enumerated (§ F.5). (NFR21-VISUAL-VERIFICATION-1.)
9. **AuthGate discipline** — profiles route defers to shell AuthGate for anonymous, role-redirects only authenticated-non-admin (§ B.1). (NFR21-AUTH-1, Init 10 retro rule.)

**Q1 is now RESOLVED as Path B** (operator/controller, 2026-06-04): the member selector **exposes material**, so the catalog selector's *material control* IS in 33.1's FE scope, the tier set filters by the chosen material's compatibility, and the TPU worked example (§ D) is live on the catalog member surface — not only on the admin grid + `/estimates`. This was the one previously-gated half of 33.1; it is unblocked. The reversal of the EST-DISPLAY-1 material-internal decision is carried under NFR-carve-out-reversal discipline — see the resolved § H / Q1. The admin grid + compatibility model were never gated and are unchanged.

---

## H. Open questions for operator review

> Per AGENTS.md autonomous-mode rules, **Q1 was a genuine load-bearing decision** (a planning-artifact tension with the shipped EST-DISPLAY-1 decision) and was surfaced rather than guessed. It is now **RESOLVED** (below). The rest carry recommendations and can proceed under the defaults unless the operator overrides.

- **Q1 — (LOAD-BEARING) Does the catalog member selector now surface MATERIAL? → RESOLVED: Path B (operator/controller, 2026-06-04).**
  The TPU directive ("TPU only offers TPU-compatible process choices") only bites on the catalog surface if material is *selectable* there. EST-DISPLAY-1 originally held material at PLA, internal (`CatalogEstimateProfileSelector.tsx:22-34`), exposing only quality_tier; material/spool lived only on the standalone `/estimates` surface.
  - **Path A (NOT chosen) — keep material PLA-pinned on the catalog selector.** Smallest, no reversal; the TPU example would be exercised only on the admin grid + `/estimates`.
  - **Path B (CHOSEN) — surface material on the catalog selector** (member picks material → tier set filters by that material's compatibility). Makes the TPU directive live on the main member surface.

  **Resolution — Path B, documented with NFR-carve-out-reversal discipline** (the repo's four-step recipe for loosening an earlier-initiative decision):
  1. **Old rationale (EST-DISPLAY-1, shipped):** the catalog Files/STL selector deliberately exposed *only* `quality_tier`, holding `material_class` at the PLA default and internal, to keep the catalog preview an orientational gram-estimate — explicitly **not** ordering, **not** spool availability — and to avoid re-opening spool/quote semantics on the catalog surface.
  2. **New requirement (operator/controller, 2026-06-04):** the member-facing selector must surface **material**, because the operator requires material-specific compatibility — e.g. a TPU selection must offer only TPU-compatible process/profile choices. A PLA-pinned selector cannot express the TPU directive on the surface members actually use.
  3. **Preserved invariant (unchanged across the reversal):** (a) **no incompatible material/process combination is ever offered** — `offerable = imported ∧ resolvable ∧ compatible`, incompatible slots hidden, compatible-but-unavailable disabled-with-explanation; (b) **no member-reachable resolve 422** (NFR21-NO-422-1) — a member can never *select* an unofferable slot; (c) the catalog surface stays an **estimate preview only** — surfacing `material_class` does **not** introduce ordering, quoting, or Spoolman spool-availability semantics (the `spoolman_filament_ref` pin stays `null`; filament-instance/spool selection remains exclusive to `/estimates`).
  4. **Mechanism that holds the preserved invariant (and that the EST-DISPLAY-1 "no ordering/spool" contract now rides instead of PLA-pinning):** the **backend compatibility projection is the source of truth** — the member selector consumes the projected `{quality_tier, available, reason}` (compatibility folded into `available`, cause into `reason`) and renders material → tier sets purely from it; the FE mirrors the per-material allowed-tier table and a parity test asserts agreement. Material exposure is a *selection-and-filtering* control over the existing estimate read, not a spool/order control — the "no ordering/spool semantics" property is now enforced by the bounded read contract (`material_class` is a resolve input only; no spool pin, no quote field) rather than by hiding the material dimension.

  **Implementation obligation carried into Story 33.1 (per the discipline):** the FE change to `CatalogEstimateProfileSelector.tsx` that surfaces material must carry a code comment citing **both** decisions (EST-DISPLAY-1 material-internal ← Init 21 Path B) + **both** rationales, and the story must verify the "no ordering/spool semantics" invariant is still held by a *different* mechanism (the bounded estimate read contract + `spoolman_filament_ref = null`), not by material-pinning. The admin grid, compatibility model, and disabled-vs-hidden logic are unchanged by this resolution.

- **Q2 — Tier control type:** segmented **pill group** (richer, accessible per-option reason — recommended) vs **native `<select>` + helper line** (lower effort, preserves the shipped component). Recommend pills; confirm appetite for the control swap (it touches the EST-DISPLAY-1 component + its baselines).

- **Q3 — Provenance disclosure depth in the grid:** per-cell **ⓘ popover** (recommended) vs an always-expanded detail row vs a separate detail drawer. Recommend popover (keeps the scan clean).

- **Q4 — Not-imported affordance in the read-only slice:** show a **disabled "Import" placeholder** on compatible-empty cells (signposts 33.2 — recommended, makes the grid's future obvious) vs show **nothing** until 33.2 ships. Minor; recommend the disabled placeholder with a "available in the import slice" tooltip.

- **Q5 — (Data, not UX) Concrete per-material compatible-slot set:** the exact map (e.g. *which* tiers are TPU-compatible) is admin data confirmed at the data phase (Decision AK / OD-7). The grid and selector render **whatever the backend map declares** — this design is map-shape-agnostic — but the **visual fixtures and baselines** (§ F.5) need a representative map to snapshot against. Recommend the operator confirm at least the TPU row for the fixture.

---

## Cross-references

- PRD: `prd.md` § Initiative 21 — FR21-COMPAT-1, FR21-SELECTOR-1, NFR21-UX-1, NFR21-I18N-PARITY-1, NFR21-VISUAL-VERIFICATION-1.
- Architecture: `architecture.md` § Initiative 21 — Decision AK (compatibility map representation/enforcement; `offerable = imported ∧ resolvable ∧ compatible`), Decision AL (import write posture — 33.2).
- Epics: `epics.md` § Initiative 21 — Story 33.1 (this artifact unblocks its FE ACs), 33.2 (import — compatibility enforcement + rejection surfacing), 33.3 (lifecycle manage).
- SCP: `sprint-change-proposal-2026-06-04-profile-admin.md` § 9 (UX-PROFILE-1 directive), § 5 (OD-1 resolved, OD-7 compat map).
- Live code surfaced: `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx`, `.../hooks/useQualityTierAvailability.ts`, `.../lib/preset.ts`, `apps/web/src/modules/admin/AdminTabs.tsx`.
- Predecessor UX artifact (format + conventions): `_bmad-output/ux/stl-estimate-display-catalog-files-ux.md`.
- Memory: [[feedback_scp_pre_enumeration_phase]] — the magic-constant contract rule applies to the per-material compatible-slot set (Q5) and any selector/grid constants in the 33.1 story spec (point each to the operator-confirmed compatibility contract, not to "what resolves").
- Mockups: `mockups/profile-admin-grid.html`, `mockups/profile-selector-states.html` (illustrative; production uses Tailwind/theme classes, zero inline hex).
