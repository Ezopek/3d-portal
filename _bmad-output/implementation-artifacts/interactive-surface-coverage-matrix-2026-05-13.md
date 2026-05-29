---
title: "Interactive-Surface Coverage Matrix — Initiative 3 / Story 5.3"
type: audit-report
story: E5.3
date: 2026-05-13
status: complete
---

## Scope and method

Read-only audit. Cross-references every Radix/base-ui interactive primitive instance in `apps/web/src/` against the open-state visual-regression specs in `apps/web/tests/visual/`. No source-tree changes.

Primitive instances enumerated via grep on `apps/web/src/**/*.tsx` for the elements `Dialog`, `DialogContent`, `Sheet`, `SheetContent`, `Popover.*`, `Select`, `SelectContent`, `DropdownMenu`, `DropdownMenuContent`, `Tooltip`, `TooltipContent`. Matches inside `apps/web/src/ui/` (primitive definitions themselves) and import lines were filtered out. Custom bespoke open/close widgets that are *not* Radix primitives (`FileSelector` inside `Viewer3DModal`, `TagPicker` inside `FilterRibbon`) are listed as informational rows because they are the open-state surfaces the brief calls out, but they do not count toward the primitive-coverage tally.

Visual specs surveyed: all 18 files in `apps/web/tests/visual/*.spec.ts`. Each spec read in full to determine which components it exercises and which open the dialog/sheet/popover/select/dropdown/tooltip. Each non-skipped spec runs in 4 Playwright projects per `apps/web/tests/visual/playwright.config.ts`: `desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark` — unless a `test.skip` viewport guard narrows it (e.g., `viewer3d-mobile.spec.ts` is mobile-only).

## PART 1 — Interactive primitive instances (by containing component)

### Dialog

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx:223` | `Viewer3DModal` | Mounted-when-open from `FilesTab` "expand / powiększ" button on STL row |
| 2 | `apps/web/src/shell/AgentsInfoDialog.tsx:83` | `AgentsInfoDialog` | `UserMenu` → "For agents / Dla agentów" item |
| 3 | `apps/web/src/modules/catalog/components/dialogs/DeleteModelDialog.tsx:41` | `DeleteModelDialog` | `ModelHero` admin DropdownMenu → "Delete" item |
| 4 | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` (consumer: `tabs/OperationalNotesTab.tsx:110`) | `ConfirmDialog` (OperationalNotesTab) | Note row "Delete" action |
| 5 | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` (consumer: `tabs/PhotosTab.tsx:117`) | `ConfirmDialog` (PhotosTab) | Photo row "Delete" action |
| 6 | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` (consumer: `tabs/PrintsTab.tsx:123`) | `ConfirmDialog` (PrintsTab) | Print row "Delete" action |
| 7 | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` (consumer: `routes/settings/sessions.tsx:143`) | `ConfirmDialog` (sessions / revoke current) | Sessions page "Revoke current session" |

### Sheet

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.tsx:65` | `EditTagsSheet` | `ModelHero` (controlled `open` prop) |
| 2 | `apps/web/src/modules/catalog/components/sheets/EditDescriptionSheet.tsx:38` | `EditDescriptionSheet` | `ModelHero` admin DropdownMenu → "Edit description" item |
| 3 | `apps/web/src/modules/catalog/components/sheets/RenderSheet.tsx:51` | `RenderSheet` (success branch, side="right") | `ModelHero` admin DropdownMenu → "Re-render" item, after submit |
| 4 | `apps/web/src/modules/catalog/components/sheets/RenderSheet.tsx:65` | `RenderSheet` (form branch, side="right") | `ModelHero` admin DropdownMenu → "Re-render" item |
| 5 | `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx:62` | `AddPrintSheet` | `PrintsTab` "Add print" button |
| 6 | `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx:65` | `AddNoteSheet` | `OperationalNotesTab` "Add note" button |
| 7 | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:123` | `FilterRibbon` mobile-filters sheet | `SheetTrigger` button with `SlidersHorizontal` icon (mobile only, `md:hidden`) |
| 8 | `apps/web/src/modules/catalog/routes/CatalogList.tsx:149` | `CatalogList` mobile-categories sheet | `SheetTrigger` button (mobile only) |

### Popover

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/modules/catalog/components/viewer3d/controls/TolerancePopover.tsx:16` | `TolerancePopover` | `Popover.Trigger` "Tolerance / Tolerancja" button inside Viewer3DModal toolbar |

### Select

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:173` | `FilterRibbon` status filter | `SelectTrigger` with `aria-label={t("catalog.filters.status")}` |
| 2 | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:197` | `FilterRibbon` source filter | `SelectTrigger` with `aria-label={t("catalog.filters.source")}` |
| 3 | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:221` | `FilterRibbon` sort filter | `SelectTrigger` with `aria-label={t("catalog.filters.sort")}` |
| 4 | `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx:75` | `AddNoteSheet` kind select | `SelectTrigger` inside the AddNote sheet |

### DropdownMenu

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/shell/UserMenu.tsx:47` | `UserMenu` | `DropdownMenuTrigger` rendered as `Button` showing user display name |
| 2 | `apps/web/src/modules/catalog/components/ModelHero.tsx:106` | `ModelHero` admin menu | `DropdownMenuTrigger` admin "kebab" button |
| 3 | `apps/web/src/modules/catalog/components/popovers/StatusPopover.tsx:23` | `StatusPopover` | `DropdownMenuTrigger` wrapping a status chip span (consumer: `ModelHero` line 134) |
| 4 | `apps/web/src/modules/catalog/components/popovers/RatingPopover.tsx:21` | `RatingPopover` | `DropdownMenuTrigger` wrapping a rating chip span (consumer: `ModelHero` line 143) |

### Tooltip

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| 1 | `apps/web/src/modules/catalog/components/viewer3d/controls/ViewToolbar.tsx:43` | `ViewToolbar` icon-button tooltip (function `IconBtn`) | Hover on any of the 4+ icon buttons inside the Viewer3DModal control bar (e.g., reset, wireframe, the 4 measure-mode buttons) |

### Custom (non-Radix) open/close surfaces — informational

These do not consume a Radix primitive but the brief explicitly inventories them as gap surfaces, so they are listed for completeness. They are not counted in the primitive coverage percentage but are flagged for Story 5.12 sub-split derivation if the operator chooses to extend the coverage criterion beyond strict Radix primitives.

| # | Component file | Component name | Trigger element |
|---|---|---|---|
| C1 | `apps/web/src/modules/catalog/components/viewer3d/controls/FileSelector.tsx:35` | `FileSelector` (custom toggleable list with internal `useState`) | `<button>` with `aria-expanded` inside `Viewer3DModal` |
| C2 | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:246` (function `TagPicker`) | `TagPicker` (inline list shown when `tagPickerOpen===true`) | `Button` "Add tag / Anuluj" at line 106 |

## PART 2 — Existing visual specs and their open-state coverage

| Spec file | Exercises | Opens primitive? | Which primitive instance | Projects |
|---|---|---|---|---|
| `admin-thumbnail-flow.spec.ts` | (skipped — Slice 3D pending) | n/a | n/a | n/a |
| `agents-info-dialog.spec.ts` | `UserMenu`, `AgentsInfoDialog` | yes (two) | UserMenu DropdownMenu (`agents-menu-open.png`); AgentsInfoDialog (`agents-dialog.png`) | 4/4 |
| `catalog-card-carousel.spec.ts` | `CatalogList` card carousel dots (DOM interaction, not a primitive) | no | n/a | 4/4 |
| `catalog-detail-admin.spec.ts` | (skipped — Slice 3E pending) | n/a | n/a | n/a |
| `catalog-detail.spec.ts` | `/catalog/:id` full-page baseline | no | n/a | 4/4 |
| `catalog-list.spec.ts` | `/catalog` full-page baseline + overflow + chip contrast | no | n/a | 4/4 |
| `dev.spec.ts` | `/dev/components` showcase route | no (renders primitives in *closed* state on the showcase only) | n/a | 4/4 |
| `empty-states.spec.ts` | catalog empty state branches | no | n/a | 4/4 |
| `files-tab-admin.spec.ts` | (skipped — Slice 3E pending) | n/a | n/a | n/a |
| `focus-ring.spec.ts` | first-tab focus outline | no | n/a | 4/4 |
| `sessions.spec.ts` | `/settings/sessions` desktop + mobile baseline | no (page-level — does not open the `ConfirmDialog`) | n/a | 4/4 (mobile test has explicit `viewport: 375x800`) |
| `v2-placeholders.spec.ts` | `/queue` ComingSoonStub | no | n/a | 4/4 |
| `viewer3d-inline-loaded.spec.ts` | inline canvas mount on detail page | no (no modal/dialog opened) | n/a | 4/4 |
| `viewer3d-measure-plane.spec.ts` | Viewer3DModal + p2pl mode + tolerance popover | yes (three) | `Viewer3DModal` (Dialog #1 above); inside it the `ViewToolbar` Tooltip (incidentally rendered around mode buttons but state is hover); `TolerancePopover` (`viewer3d-tolerance-popover.png`) | 4/4 |
| `viewer3d-measure-pp.spec.ts` | Viewer3DModal + p2p mode + clicks | yes | `Viewer3DModal` Dialog (open state captured in `viewer3d-measure-pp.png`) | 4/4 |
| `viewer3d-mobile.spec.ts` | mobile detail file-list collapsed (no canvas) | no | n/a | mobile-light + mobile-dark (skip guard `mobile-*` only) |
| `viewer3d-modal-closed.spec.ts` | Viewer3DModal opened, file pill closed | yes | `Viewer3DModal` Dialog (`viewer3d-modal-closed.png`) | 4/4 |
| `viewer3d-modal-open.spec.ts` | Viewer3DModal + open file pill | yes — but the file pill is the custom `FileSelector`, NOT a Radix primitive | `Viewer3DModal` Dialog; `FileSelector` (custom open state, `viewer3d-modal-open.png`) | 4/4 |

Aggregate: of the 18 specs, 6 actually open a Radix primitive in an open state: `agents-info-dialog`, `viewer3d-measure-plane`, `viewer3d-measure-pp`, `viewer3d-modal-closed`, `viewer3d-modal-open`. Note: `viewer3d-mobile.spec.ts` only runs on the two `mobile-*` projects.

## PART 3 — Coverage matrix (sorted by primitive type)

| surface | containing component file | primitive type | open-state spec exists? | covering spec(s) | projects covered | gap notes |
|---|---|---|---|---|---|---|
| AgentsInfoDialog | `apps/web/src/shell/AgentsInfoDialog.tsx:83` | Dialog | yes | `agents-info-dialog.spec.ts` ("agents dialog renders…") | 4/4 | covered |
| ConfirmDialog (OperationalNotesTab → delete note) | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` invoked from `tabs/OperationalNotesTab.tsx:110` | Dialog | no | — | 0/4 | [GAP] — no Playwright spec opens this; only unit test (`ConfirmDialog.test.tsx`) |
| ConfirmDialog (PhotosTab → delete photo) | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` invoked from `tabs/PhotosTab.tsx:117` | Dialog | no | — | 0/4 | [GAP] |
| ConfirmDialog (PrintsTab → delete print) | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` invoked from `tabs/PrintsTab.tsx:123` | Dialog | no | — | 0/4 | [GAP] |
| ConfirmDialog (sessions → revoke current) | `apps/web/src/ui/custom/ConfirmDialog.tsx:42` invoked from `routes/settings/sessions.tsx:143` | Dialog | no | — | 0/4 | [GAP] — `sessions.spec.ts` captures the page baseline but does not click "Revoke current" |
| DeleteModelDialog | `apps/web/src/modules/catalog/components/dialogs/DeleteModelDialog.tsx:41` | Dialog | no | — | 0/4 | [GAP] — only reachable via ModelHero admin DropdownMenu → "Delete" |
| Viewer3DModal | `apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx:223` | Dialog | yes | `viewer3d-modal-closed.spec.ts`, `viewer3d-modal-open.spec.ts`, `viewer3d-measure-plane.spec.ts`, `viewer3d-measure-pp.spec.ts` | 4/4 | covered (multiple specs) |
| ModelHero admin DropdownMenu | `apps/web/src/modules/catalog/components/ModelHero.tsx:106` | DropdownMenu | no | — | 0/4 | [GAP] |
| RatingPopover (named "Popover" but uses DropdownMenu) | `apps/web/src/modules/catalog/components/popovers/RatingPopover.tsx:21` | DropdownMenu | no | — | 0/4 | [GAP] — note misleading filename: it is a DropdownMenu |
| StatusPopover (named "Popover" but uses DropdownMenu) | `apps/web/src/modules/catalog/components/popovers/StatusPopover.tsx:23` | DropdownMenu | no | — | 0/4 | [GAP] — same naming surprise as RatingPopover |
| UserMenu | `apps/web/src/shell/UserMenu.tsx:47` | DropdownMenu | yes | `agents-info-dialog.spec.ts` ("user menu open with 'For agents' item visible") | 4/4 | covered |
| TolerancePopover | `apps/web/src/modules/catalog/components/viewer3d/controls/TolerancePopover.tsx:16` | Popover | yes | `viewer3d-measure-plane.spec.ts` ("tolerance popover opens") | 4/4 | covered |
| AddNoteSheet kind Select | `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx:75` | Select | no | — | 0/4 | [GAP] — embedded inside AddNoteSheet; needs the sheet to be open first |
| FilterRibbon source Select | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:197` | Select | no | — | 0/4 | [GAP] |
| FilterRibbon sort Select | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:221` | Select | no | — | 0/4 | [GAP] |
| FilterRibbon status Select | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:173` | Select | no | — | 0/4 | [GAP] |
| AddNoteSheet | `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx:65` | Sheet | no | — | 0/4 | [GAP] |
| AddPrintSheet | `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx:62` | Sheet | no | — | 0/4 | [GAP] |
| CatalogList mobile-categories sheet | `apps/web/src/modules/catalog/routes/CatalogList.tsx:149` | Sheet | no | — | 0/4 | [GAP] — mobile-only surface, easy to cover by clicking the categories trigger on mobile-* |
| EditDescriptionSheet | `apps/web/src/modules/catalog/components/sheets/EditDescriptionSheet.tsx:38` | Sheet | no | — | 0/4 | [GAP] |
| EditTagsSheet | `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.tsx:65` | Sheet | no | — | 0/4 | [GAP] |
| FilterRibbon mobile-filters sheet | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:123` | Sheet | no | — | 0/4 | [GAP] — mobile-only surface |
| RenderSheet (form branch) | `apps/web/src/modules/catalog/components/sheets/RenderSheet.tsx:65` | Sheet | no | — | 0/4 | [GAP] |
| RenderSheet (success branch) | `apps/web/src/modules/catalog/components/sheets/RenderSheet.tsx:51` | Sheet | no | — | 0/4 | [GAP] — post-submit confirmation state; same component, distinct snapshot value |
| ViewToolbar Tooltip | `apps/web/src/modules/catalog/components/viewer3d/controls/ViewToolbar.tsx:43` | Tooltip | no | — | 0/4 | [GAP] — `viewer3d-measure-plane.spec.ts` may incidentally hover an icon but does not assert tooltip open state |
| FileSelector (custom, not Radix) | `apps/web/src/modules/catalog/components/viewer3d/controls/FileSelector.tsx:35` | (custom) | yes | `viewer3d-modal-open.spec.ts` | 4/4 | covered (informational — not a Radix primitive) |
| TagPicker (custom, not Radix) | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:246` | (custom) | no | — | 0/4 | [GAP] (informational — not a Radix primitive; brief explicitly inventories it) |

## PART 4 — Gap analysis for Story 5.12 sub-split derivation

The brief proposes 4 sub-stories: 5.12a Select dropdowns; 5.12b ConfirmDialog + EditSheets; 5.12c Tooltip + UserMenu; 5.12d remaining (RenderSheet + AddPrintSheet + AddNoteSheet + FilterRibbon TagPicker mobile sheet). With the actual primitive count and grouping affinities (shared route + shared trigger chain), I propose a small adjustment.

### Proposed bundles (validated against actual findings)

#### 5.12a — Select dropdowns

- `FilterRibbon` status Select
- `FilterRibbon` source Select
- `FilterRibbon` sort Select
- `AddNoteSheet` kind Select (requires AddNoteSheet to be open first — coupled with 5.12b/5.12d)

Affinity: same primitive type, three live on the `/catalog` route under one component, one is nested inside a Sheet. Suggestion: cover the three FilterRibbon selects in one spec on `/catalog`, and capture the AddNoteSheet kind Select as part of the AddNoteSheet open-state spec to avoid double-opening the parent sheet.

#### 5.12b — ConfirmDialog + EditSheets

- `ConfirmDialog` (PhotosTab / PrintsTab / OperationalNotesTab / sessions) — 4 invocations of the same primitive instance, snapshots should cover at least one tab's variant per project (PrintsTab covers the destructive-action layout deterministically since `sessions.spec.ts` already establishes the sessions baseline).
- `EditTagsSheet`
- `EditDescriptionSheet`
- (Bonus) `DeleteModelDialog` — this is NOT a ConfirmDialog but is a sibling destructive dialog on the same route, and only reachable through the `ModelHero` admin DropdownMenu which is also in 5.12c. Group it here if the operator wants destructive-dialog coverage co-located; or move to 5.12c if "open the ModelHero menu → click Delete" is the natural fixture chain.

Affinity: ConfirmDialog is one primitive with 4 callsites; covering one variant per project validates the primitive's open-state baseline. EditSheets share the same hero trigger chain. Recommend grouping `DeleteModelDialog` here.

#### 5.12c — Tooltip + UserMenu + ModelHero admin DropdownMenu

- `ViewToolbar` Tooltip (open-state via hover on an icon button inside Viewer3DModal — the modal is already covered by 4 specs, so just adding a hover step is cheap)
- `UserMenu` is already covered by `agents-info-dialog.spec.ts` → **drop from 5.12c**
- `ModelHero` admin DropdownMenu — gap (the brief grouped this implicitly under "UserMenu"; it is a distinct surface that the brief's list of 10 mentioned as a single line item)
- `StatusPopover` (DropdownMenu masquerading as a Popover)
- `RatingPopover` (DropdownMenu masquerading as a Popover)

Recommendation: rename this bundle to **"Tooltip + admin DropdownMenu cluster"** since UserMenu is already covered. Pair the two `*Popover` triggers (status chip, rating chip) with the ModelHero admin kebab — all three live in `ModelHero`, share fixtures, and all snapshot a DropdownMenu open-state.

#### 5.12d — Remaining sheets

- `RenderSheet` form branch
- `RenderSheet` success branch
- `AddPrintSheet`
- `AddNoteSheet` (which auto-covers its inner Select per 5.12a)
- `FilterRibbon` mobile-filters Sheet (mobile-* projects only)
- `CatalogList` mobile-categories Sheet (mobile-* projects only) — **add to bundle (not in brief)**
- `TagPicker` (custom) — keep if 5.12 scope extends to custom open-state surfaces

Recommendation: split mobile-only surfaces (`FilterRibbon` mobile sheet, `CatalogList` mobile-categories sheet) into a mobile-projects-only sub-spec to avoid empty `desktop-*` snapshots.

### Adjustments to brief

- **Drop `UserMenu` from 5.12c** (already covered by `agents-info-dialog.spec.ts`).
- **Add `CatalogList` mobile-categories Sheet to 5.12d** (the brief omitted it).
- **Add `DeleteModelDialog` to 5.12b** (the brief grouped it implicitly under "ConfirmDialog+EditSheets" via the "model-detail dialogs" listing in Story 5.3 dev notes).
- **Clarify in 5.12c that `StatusPopover` / `RatingPopover` are DropdownMenu**, not Popover (naming surprise — code-base uses `popovers/` folder for DropdownMenu-backed components).
- **`RenderSheet` has two render branches** (form and success) — note in 5.12d whether the coverage target is both branches or only the form branch.
- **`TolerancePopover` is already covered** by `viewer3d-measure-plane.spec.ts` and does NOT need a new spec.

## PART 5 — Conclusions

### Counts

- **Total interactive primitive instances:** 25 Radix primitives (Dialog: 7, Sheet: 8, Popover: 1, Select: 4, DropdownMenu: 4, Tooltip: 1). Plus 2 informational custom open-state surfaces (FileSelector, TagPicker).
- **Currently covered (open state):** 4 Radix instances — Viewer3DModal Dialog, AgentsInfoDialog Dialog, UserMenu DropdownMenu, TolerancePopover Popover.
- **Coverage:** **4 / 25 = 16% on Radix primitives**. Including the two custom surfaces: 5 / 27 = 18.5%. The aggregate "coverage matrix at 100%" criterion in `prd.md` § Initiative 3 § "Success Criteria" requires the remaining 21 Radix gaps to close in Phase B (Story 5.12).
- **Gap surface count:** 21 Radix instances flagged `[GAP]` + 1 custom (TagPicker) = 22 gaps.

### Verification of brief's 10-surface gap list

The brief documented "10 surfaces with zero open-state baseline": Select dropdowns, FilterRibbon TagPicker, ConfirmDialog, EditTagsSheet, EditDescriptionSheet, RenderSheet, AddPrintSheet, AddNoteSheet, UserMenu, Tooltip.

**Verdict: refuted-with-diff.** The brief's count of 10 surface families is roughly right but the actual instance count is meaningfully higher, and one entry (UserMenu) is wrong.

Diff against the brief:

- **REFUTED — UserMenu** is already covered by `agents-info-dialog.spec.ts` ("user menu open with 'For agents' item visible") in `desktop-light/dark + mobile-light/dark`. The brief listed it as a gap; it is not.
- **CONFIRMED — Select dropdowns** are gaps, but there are 4 distinct Select instances (FilterRibbon × 3 + AddNoteSheet kind), not "the Select dropdowns" generically.
- **CONFIRMED — FilterRibbon TagPicker** is a gap, but it is a custom inline component, not a Radix primitive (worth flagging in 5.12 scoping — if Story 5.12 strictly covers Radix primitives, TagPicker may be deferred).
- **CONFIRMED — ConfirmDialog** is a gap, but with 4 distinct invocations (Photos / Prints / OperationalNotes tabs + sessions/revoke). Covering one invocation validates the primitive baseline.
- **CONFIRMED — EditTagsSheet, EditDescriptionSheet, RenderSheet, AddPrintSheet, AddNoteSheet** are all gaps. Note `RenderSheet` has two render branches (form + success).
- **CONFIRMED — Tooltip** is a gap (ViewToolbar, viewer3d-only — the brief mentions "catalog hover tooltips" but the catalog cards do not currently use the `Tooltip` primitive at all).
- **MISSING from brief — `DeleteModelDialog`** (1 instance, gap) — distinct from ConfirmDialog.
- **MISSING from brief — `ModelHero` admin DropdownMenu** (1 instance, gap) — the kebab menu on the model detail hero.
- **MISSING from brief — `StatusPopover` / `RatingPopover`** (2 instances, gaps) — both are DropdownMenus despite the directory name, reached from the hero chip.
- **MISSING from brief — `CatalogList` mobile-categories Sheet** (mobile-only gap) — not explicitly listed in the brief.
- **MISSING from brief — `FilterRibbon` mobile-filters Sheet** (mobile-only gap) — the brief mentions "FilterRibbon TagPicker" but not the mobile filters sheet which is a distinct surface.

### Surprises and naming caveats

- `StatusPopover` and `RatingPopover` live in `apps/web/src/modules/catalog/components/popovers/` but **use `DropdownMenu`, not `Popover`**. Naming-mismatch landmine for anyone scoping 5.12 by directory or by name. Worth a one-line comment in the 5.12c spec header.
- `viewer3d-modal-open.spec.ts` does cover an open dropdown, but it is the **custom** `FileSelector`, not a Radix `Select` or `DropdownMenu`. If Story 5.12 measures Radix-primitive coverage strictly, this spec is informational only.
- `RenderSheet` renders **two different content trees** (form vs. success) under the same component file — both are open-state snapshots and should be counted distinctly.
- The `dev.spec.ts` showcase route renders some primitives in **closed** state for component-gallery purposes — it does not contribute to open-state coverage.
- 4 of the 18 spec files are placeholders (`admin-thumbnail-flow`, `catalog-detail-admin`, `files-tab-admin` deferred to Slices 3D/3E) and use `test.describe.skip`. Plan around this when sequencing Story 5.12; they are not blockers.

### Sub-split bundle confirmation for Story 5.12

The brief's 4-bundle decomposition holds in shape but needs the adjustments above. Final proposed bundles for sprint planning:

- **5.12a Select dropdowns:** FilterRibbon × 3 (status / source / sort). AddNoteSheet kind Select absorbed into 5.12d's AddNoteSheet open-state spec.
- **5.12b Destructive dialogs + EditSheets:** ConfirmDialog (one invocation as primitive baseline — PrintsTab recommended), DeleteModelDialog, EditTagsSheet, EditDescriptionSheet.
- **5.12c Tooltip + admin DropdownMenu cluster:** ViewToolbar Tooltip (hover assertion), ModelHero admin DropdownMenu, StatusPopover (DropdownMenu), RatingPopover (DropdownMenu). Drop UserMenu (already covered).
- **5.12d Remaining sheets:** RenderSheet (form + success), AddPrintSheet, AddNoteSheet (includes inner kind Select), FilterRibbon mobile-filters Sheet (mobile-* only), CatalogList mobile-categories Sheet (mobile-* only). TagPicker (custom) deferred to a follow-up if Story 5.12 scope excludes non-Radix surfaces.

Total new specs needed for 100% Radix-primitive coverage: approximately 14–16 (counting one spec per primitive instance is overkill; some can share fixtures). With co-located fixtures (e.g., open ModelHero kebab once, snapshot menu + DeleteModelDialog + StatusPopover + RatingPopover via separate steps), the spec count can be compressed.
