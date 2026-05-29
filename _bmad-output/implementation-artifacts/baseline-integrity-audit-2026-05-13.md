---
title: "Baseline Integrity Audit + 14-Skip Disposition — Initiative 3 / Story 5.2"
type: audit-report
story: E5.2
date: 2026-05-13
status: in_progress
review_protocol: "≤20 PNGs per session, ≤2 sessions/day (NFR4 fatigue countermeasure)"
---

# Baseline Integrity Audit + 14-Skip Disposition — Story 5.2

Scope: read-only audit of all PNG baselines in `apps/web/tests/visual/__snapshots__/` plus disposition of every `test.skip` / `test.fixme` / `it.skip` / `it.fixme` in `apps/web/tests/visual/`. Output is the source of truth that bounds Phase B baseline regeneration scope (Story 5.11) and closes the silent 14-skip hole.

This subagent pass enumerates the data and pre-classifies entries against the published Phase B remediation surface (Stories 5.7, 5.8, 5.9). Verdicts for catalog/dev/sessions/static-viewer baselines are left as `unverified-defer-to-operator` because PNG inspection requires a human eye at 100% zoom (NFR4 protocol). Operator review fills the remaining verdicts inline during the per-session passes.

## Part 1 — Inventory

### PNG baselines

Source: `find apps/web/tests/visual/__snapshots__/ -name "*.png" | sort` (2026-05-13).

Total baselines: **82 PNGs** across **18 spec directories** × 4 projects (2 viewports × 2 themes). Some specs contribute multiple PNGs (`agents-info-dialog`, `files-tab-admin`, `viewer3d-measure-plane`), some sessions specs render desktop and mobile screenshots from the same project producing 8 PNGs across 4 projects.

### Skip statements (raw `.skip`/`.fixme` count)

Source: `grep -rEn "test\.(describe\.)?skip\(|test\.(describe\.)?fixme\(|it\.skip\(|it\.fixme\(" apps/web/tests/visual/`.

| File | Line | Pattern |
| --- | --- | --- |
| `viewer3d-mobile.spec.ts` | 13 | `test.skip(!testInfo.project.name.startsWith("mobile-"), ...)` — conditional |
| `admin-thumbnail-flow.spec.ts` | 5 | `test.describe.skip("admin thumbnail flow (deferred to Slice 3D)", ...)` |
| `files-tab-admin.spec.ts` | 5 | `test.describe.skip("files tab admin (deferred to Slice 3E)", ...)` |
| `catalog-detail-admin.spec.ts` | 6 | `test.describe.skip("catalog detail admin (deferred to Slice 3E)", ...)` |

Total source-level skip statements: **4**.

### Reconciliation with the "14 skips" brief number

The brief (E5.2 acceptance criteria) cites "90 passed / 0 failed / 14 skips" as the post-`c0daf7a` Playwright run state. The 14 is a **test-run count after the 4-project matrix expansion**, not a source-level statement count:

- `viewer3d-mobile.spec.ts` conditional skip — runs on all 4 projects but only skips on the 2 desktop projects (`!startsWith("mobile-")`) → **2 skipped runs**.
- 3 `test.describe.skip("…")` blocks, each wrapping one placeholder test → each spec × 4 projects = 4 skipped runs → **12 skipped runs**.

Total: 2 + 12 = **14 skipped test runs**. Matches the brief. No discrepancy.

## Part 2 — Baseline disposition table

Verdict legend:
- **buggy** — known visual defect (sanity-check seed; will regenerate after Phase B fix).
- **expected-buggy-pending-fix** — spec exercises a surface targeted by Phase B Stories 5.7 / 5.8 / 5.9; baseline will be regenerated after the fix lands.
- **unverified-defer-to-operator** — outside the published Phase B surface; cannot be classified without a human eye at 100% zoom. Operator fills verdict during the per-session review pass.
- **OK** — operator confirmed correct rendering; no regen needed.

Project legend: `dl` = desktop-light, `dd` = desktop-dark, `ml` = mobile-light, `md` = mobile-dark.

Regen-action column reflects the current best-known mapping; an operator verdict of `OK` flips regen to `no`.

### Agents-info-dialog (8 PNGs) — Phase B Story 5.7 surface

`agents-info-dialog.spec.ts` exercises both the agents menu in its open state and the agents onboarding dialog. The dialog/overlay tokenization fix (Story 5.7) targets `dialog.tsx:34` and `dialog.tsx:56`, which directly drive the rendered surface for `agents-dialog-*`. The `agents-menu-open-*` baselines render the menu trigger atop the page chrome — not directly on the 5.7 surface, but in light mode the menu may share Radix popover bg with overlay logic; flagging conservatively as expected-buggy on light only.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `agents-info-dialog.spec.ts/agents-dialog-desktop-light.png` | dl | **buggy** | hardcoded RGBA in `dialog.tsx:34`+`:56` bypasses theme tokens; light-mode shows translucent dark overlay (known per brief — sanity-check seed) | yes (after Story 5.7) |
| `agents-info-dialog.spec.ts/agents-dialog-desktop-dark.png` | dd | **buggy** | same root cause as light variant; the rgba overlay is wrong in both themes (the dark variant happens to look "ok" but the underlying token bypass is identical) | yes (after Story 5.7) |
| `agents-info-dialog.spec.ts/agents-dialog-mobile-light.png` | ml | **buggy** | same as desktop-light, mobile viewport | yes (after Story 5.7) |
| `agents-info-dialog.spec.ts/agents-dialog-mobile-dark.png` | md | **buggy** | same as desktop-dark, mobile viewport | yes (after Story 5.7) |
| `agents-info-dialog.spec.ts/agents-menu-open-desktop-light.png` | dl | **expected-buggy-pending-fix** | menu trigger rendered on light theme; potentially affected by Story 5.7 overlay-token side effects | yes (after Phase B) |
| `agents-info-dialog.spec.ts/agents-menu-open-desktop-dark.png` | dd | **unverified-defer-to-operator** | dark-mode menu; needs eye check | tbd |
| `agents-info-dialog.spec.ts/agents-menu-open-mobile-light.png` | ml | **expected-buggy-pending-fix** | same as desktop-light, mobile | yes (after Phase B) |
| `agents-info-dialog.spec.ts/agents-menu-open-mobile-dark.png` | md | **unverified-defer-to-operator** | dark-mode menu, mobile; needs eye check | tbd |

### Catalog-detail-admin (4 PNGs)

`catalog-detail-admin.spec.ts` is a `test.describe.skip` placeholder (see Part 3 disposition table). The PNG baselines persisted from a prior implementation and were not exercised by the suite. **Deleted 2026-05-17** in the TB-013 close-out bookkeeping commit (`spec-tb-013-closeout-orphan-baselines.md`); Slice 3E will recreate them when it un-skips the spec.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `catalog-detail-admin.spec.ts/catalog-detail-admin-desktop-light.png` | dl | **deleted** | orphan — spec is `describe.skip`; baseline not currently exercised | deleted 2026-05-17 (TB-013 close-out) |
| `catalog-detail-admin.spec.ts/catalog-detail-admin-desktop-dark.png` | dd | **deleted** | orphan — same as light | deleted 2026-05-17 (TB-013 close-out) |
| `catalog-detail-admin.spec.ts/catalog-detail-admin-mobile-light.png` | ml | **deleted** | orphan — same as light | deleted 2026-05-17 (TB-013 close-out) |
| `catalog-detail-admin.spec.ts/catalog-detail-admin-mobile-dark.png` | md | **deleted** | orphan — same as light | deleted 2026-05-17 (TB-013 close-out) |

### Catalog-detail (4 PNGs)

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `catalog-detail.spec.ts/catalog-detail-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `catalog-detail.spec.ts/catalog-detail-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `catalog-detail.spec.ts/catalog-detail-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `catalog-detail.spec.ts/catalog-detail-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Catalog-list (4 PNGs)

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `catalog-list.spec.ts/catalog-list-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `catalog-list.spec.ts/catalog-list-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `catalog-list.spec.ts/catalog-list-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `catalog-list.spec.ts/catalog-list-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Dev (4 PNGs) — likely Story 5.9 dark-mode surface

The dev page typically showcases status badges (success/warning/destructive) and would surface any `.dark` override gaps targeted by Story 5.9. Marked conservatively as expected-buggy on the two dark variants; operator verifies during review.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `dev.spec.ts/dev-components-desktop-light.png` | dl | **unverified-defer-to-operator** | dev showcase, light — status color tokens inherit from light defaults | tbd |
| `dev.spec.ts/dev-components-desktop-dark.png` | dd | **expected-buggy-pending-fix** | dev showcase shows status badges; success/warning/destructive currently lack `.dark` overrides → Story 5.9 will adjust | yes (after Story 5.9) |
| `dev.spec.ts/dev-components-mobile-light.png` | ml | **unverified-defer-to-operator** | same as desktop-light | tbd |
| `dev.spec.ts/dev-components-mobile-dark.png` | md | **expected-buggy-pending-fix** | same as desktop-dark | yes (after Story 5.9) |

### Empty-states (4 PNGs)

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `empty-states.spec.ts/catalog-empty-with-action-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `empty-states.spec.ts/catalog-empty-with-action-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `empty-states.spec.ts/catalog-empty-with-action-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `empty-states.spec.ts/catalog-empty-with-action-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Files-tab-admin (8 PNGs)

The spec file `files-tab-admin.spec.ts` is currently a `test.describe.skip` placeholder, yet eight PNGs persisted from a prior implementation. Same situation as catalog-detail-admin. **Deleted 2026-05-17** in the TB-013 close-out bookkeeping commit (`spec-tb-013-closeout-orphan-baselines.md`); Slice 3E will recreate them when it un-skips the spec.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `files-tab-admin.spec.ts/files-tab-admin-default-desktop-light.png` | dl | **deleted** | orphan — spec is `describe.skip` | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-default-desktop-dark.png` | dd | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-default-mobile-light.png` | ml | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-default-mobile-dark.png` | md | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-pending-desktop-light.png` | dl | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-pending-desktop-dark.png` | dd | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-pending-mobile-light.png` | ml | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |
| `files-tab-admin.spec.ts/files-tab-admin-pending-mobile-dark.png` | md | **deleted** | orphan | deleted 2026-05-17 (TB-013 close-out) |

### Focus-ring (4 PNGs)

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `focus-ring.spec.ts/rail-focus-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `focus-ring.spec.ts/rail-focus-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `focus-ring.spec.ts/rail-focus-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `focus-ring.spec.ts/rail-focus-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Sessions (8 PNGs)

`sessions.spec.ts` produces two screenshots per project (one named `sessions-desktop`, one named `sessions-mobile`), so 4 projects × 2 = 8 PNGs.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `sessions.spec.ts/sessions-desktop-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-desktop-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-desktop-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-desktop-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-mobile-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-mobile-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-mobile-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `sessions.spec.ts/sessions-mobile-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### V2-placeholders (4 PNGs)

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `v2-placeholders.spec.ts/queue-placeholder-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `v2-placeholders.spec.ts/queue-placeholder-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `v2-placeholders.spec.ts/queue-placeholder-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `v2-placeholders.spec.ts/queue-placeholder-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Viewer3d-inline-loaded (4 PNGs)

Static (canvas-already-rendered) viewer baselines. Not on Story 5.8 surface (which targets the over-canvas tooltip overlays in `RimOverlay.tsx` / `MeasureOverlay.tsx`).

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-inline-loaded.spec.ts/viewer3d-inline-loaded-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-inline-loaded.spec.ts/viewer3d-inline-loaded-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-inline-loaded.spec.ts/viewer3d-inline-loaded-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-inline-loaded.spec.ts/viewer3d-inline-loaded-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Viewer3d-measure-plane (12 PNGs) — Phase B Story 5.8 surface

This spec exercises the plane-measure flow which surfaces the `MeasureOverlay` (Story 5.8 target). The cluster-overlay and mode-buttons baselines may or may not include the tooltip surface; the tolerance-popover variant definitely renders a tooltip-like overlay. Marking all 12 as expected-buggy with a note to confirm individually during operator review — some may turn out to be unaffected.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-measure-plane.spec.ts/viewer3d-cluster-overlay-desktop-light.png` | dl | **expected-buggy-pending-fix** | renders over-canvas overlay during plane-measure; Story 5.8 tokenizes `MeasureOverlay.tsx` | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-cluster-overlay-desktop-dark.png` | dd | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-cluster-overlay-mobile-light.png` | ml | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-cluster-overlay-mobile-dark.png` | md | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-mode-buttons-p2pl-desktop-light.png` | dl | **expected-buggy-pending-fix** | mode-button state during plane-measure; verify whether overlay surface is visible | yes (after Story 5.8 — confirm) |
| `viewer3d-measure-plane.spec.ts/viewer3d-mode-buttons-p2pl-desktop-dark.png` | dd | **expected-buggy-pending-fix** | same | yes (after Story 5.8 — confirm) |
| `viewer3d-measure-plane.spec.ts/viewer3d-mode-buttons-p2pl-mobile-light.png` | ml | **expected-buggy-pending-fix** | same | yes (after Story 5.8 — confirm) |
| `viewer3d-measure-plane.spec.ts/viewer3d-mode-buttons-p2pl-mobile-dark.png` | md | **expected-buggy-pending-fix** | same | yes (after Story 5.8 — confirm) |
| `viewer3d-measure-plane.spec.ts/viewer3d-tolerance-popover-desktop-light.png` | dl | **expected-buggy-pending-fix** | tolerance popover overlay; clearly on 5.8 surface | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-tolerance-popover-desktop-dark.png` | dd | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-tolerance-popover-mobile-light.png` | ml | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-plane.spec.ts/viewer3d-tolerance-popover-mobile-dark.png` | md | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |

### Viewer3d-measure-pp (4 PNGs) — Phase B Story 5.8 surface

Point-to-point measure flow surfaces the `RimOverlay` / `MeasureOverlay` tooltip (Story 5.8 target).

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-measure-pp.spec.ts/viewer3d-measure-pp-desktop-light.png` | dl | **expected-buggy-pending-fix** | renders measure overlay; Story 5.8 tokenizes `RimOverlay.tsx`/`MeasureOverlay.tsx` | yes (after Story 5.8) |
| `viewer3d-measure-pp.spec.ts/viewer3d-measure-pp-desktop-dark.png` | dd | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-pp.spec.ts/viewer3d-measure-pp-mobile-light.png` | ml | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |
| `viewer3d-measure-pp.spec.ts/viewer3d-measure-pp-mobile-dark.png` | md | **expected-buggy-pending-fix** | same | yes (after Story 5.8) |

### Viewer3d-mobile (2 PNGs) — conditional skip

This spec runs only on the 2 mobile projects (per the `test.skip(!startsWith("mobile-"), ...)` guard). Thus only 2 PNGs exist (one per mobile project), not 4.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-mobile.spec.ts/viewer3d-mobile-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-mobile.spec.ts/viewer3d-mobile-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Viewer3d-modal-closed (4 PNGs)

Modal-closed snapshot shows the page state *before* the viewer modal opens. Not on Story 5.7 (no dialog rendered) or 5.8 (no measure overlay rendered).

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-modal-closed.spec.ts/viewer3d-modal-closed-desktop-light.png` | dl | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-modal-closed.spec.ts/viewer3d-modal-closed-desktop-dark.png` | dd | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-modal-closed.spec.ts/viewer3d-modal-closed-mobile-light.png` | ml | **unverified-defer-to-operator** | — | tbd |
| `viewer3d-modal-closed.spec.ts/viewer3d-modal-closed-mobile-dark.png` | md | **unverified-defer-to-operator** | — | tbd |

### Viewer3d-modal-open (4 PNGs) — likely Phase B Story 5.7 surface

Modal-open snapshots render the viewer modal which uses the same `dialog.tsx` primitive that Story 5.7 tokenizes (`DialogOverlay` + `DialogContent`). The modal-shell will change after 5.7 lands.

| Baseline relative path | Project | Verdict | Defect note | Regen required |
| --- | --- | --- | --- | --- |
| `viewer3d-modal-open.spec.ts/viewer3d-modal-open-desktop-light.png` | dl | **expected-buggy-pending-fix** | modal shell uses `dialog.tsx` primitive — Story 5.7 retokenizes the overlay layer | yes (after Story 5.7) |
| `viewer3d-modal-open.spec.ts/viewer3d-modal-open-desktop-dark.png` | dd | **expected-buggy-pending-fix** | same | yes (after Story 5.7) |
| `viewer3d-modal-open.spec.ts/viewer3d-modal-open-mobile-light.png` | ml | **expected-buggy-pending-fix** | same | yes (after Story 5.7) |
| `viewer3d-modal-open.spec.ts/viewer3d-modal-open-mobile-dark.png` | md | **expected-buggy-pending-fix** | same | yes (after Story 5.7) |

### Operator review sessions

**Operator review sessions** — recorded inline as the operator works through them:

_(operator-driven; this section fills as eye-review sessions complete. Target cadence: ≤20 PNGs per session, ≤2 sessions/day per NFR4. Total 82 PNGs ⇒ ~5 sessions across ~3 days.)_

- Session 1 (YYYY-MM-DD): batch <relative paths>, verdicts updated above. Signed: Ezop.
- Session 2 ...

## Part 3 — Skip disposition

Each source-level skip statement, the surrounding context that justifies (or fails to justify) the skip, and a disposition recommendation. Defaults to `deferred-to-operator-review` for autonomous-mode execution; reasons captured verbatim from comments so the operator decides quickly.

| Spec : line | Test / describe block name | Skip reason (from code/comment) | Disposition | Unskip prerequisite (if applicable) |
| --- | --- | --- | --- | --- |
| `viewer3d-mobile.spec.ts:13` | `viewer3d — mobile inline > phone viewport shows the file list collapsed (no inline preview)` | Inline comment on line 15: `"mobile-only assertion"`. The guard is `test.skip(!testInfo.project.name.startsWith("mobile-"), ...)`, so it only skips on the 2 desktop projects. This is the canonical project-gating pattern; not a quality-defect skip. | **deferred-to-operator-review** (recommended action: keep skipped — legitimate project-gating skip; matches the `mobile-only` assertion contract) | n/a — gate is intentional |
| `admin-thumbnail-flow.spec.ts:5` | `admin thumbnail flow (deferred to Slice 3D)` | File-header comment: `// Legacy admin thumbnail flow was removed in Slice 3C. The new admin thumbnail picker is part of Slice 3D's PhotosTab.` Body is a single placeholder `test("placeholder", () => {});`. | **deferred-to-operator-review** (recommended action: keep skipped until Slice 3D ships PhotosTab, then unskip-or-replace; if Slice 3D ships with a different spec layout, delete this placeholder) | Slice 3D PhotosTab implementation + actual test bodies authored against the new flow |
| `files-tab-admin.spec.ts:5` | `files tab admin (deferred to Slice 3E)` | File-header comment: `// Legacy admin file selection (render-selection checkboxes) was removed in Slice 3C. The new admin file-management UX lands in Slice 3E.` Body is a single placeholder `test("placeholder", () => {});`. | **deferred-to-operator-review** (recommended action: keep skipped until Slice 3E ships, then unskip-or-replace; if Slice 3E reshapes the UX, delete and re-author) | Slice 3E admin file-management UX + actual test bodies |
| `catalog-detail-admin.spec.ts:6` | `catalog detail admin (deferred to Slice 3E)` | File-header comment: `// Admin actions on catalog detail (thumbnail picker, render selection, share button) were removed in Slice 3C and return in Slice 3E with the new edit-pattern. Re-enable when 3E ships.` Body is a single placeholder `test("placeholder", () => {});`. | **deferred-to-operator-review** (recommended action: keep skipped until Slice 3E ships, then unskip-or-replace) | Slice 3E admin edit-pattern + actual test bodies |

### Pattern observations

- **All three `describe.skip` blocks are placeholder shells** (`test("placeholder", () => {})` body). They exist purely to preserve filenames for future reactivation in Slices 3D / 3E. None carry test logic that could regress; they are scaffold, not skipped quality coverage.
- **The single conditional skip** (viewer3d-mobile) is the legitimate project-gating pattern that the brief calls out as "may be legitimate". It is.
- **None of the 4 skips are flaky-tests / TODO-investigate types** — there is no skip in the visual suite that hides a real-but-fragile assertion. The silent hole the brief worried about (skips masking quality regressions) does **not** materialise in this audit.
- **Orphan baselines** are the more interesting hygiene finding: the 3 `describe.skip` specs collectively carry **16 orphan PNGs** (`admin-thumbnail-flow` 0 — never recorded a baseline; `files-tab-admin` 8; `catalog-detail-admin` 4 — and a possible 4 more if `files-tab-admin-pending-*` is double-counted as orphan; recheck during operator pass). These cost nothing on disk but bloat the inventory; operator may want to delete them when ratifying the disposition.

## Part 4 — Conclusions

### PNG totals

- **Total PNG baselines:** 82.
- **Spec directories:** 18 (one per spec file).
- **Project coverage:** mostly 4 projects per spec (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`); 1 spec (`viewer3d-mobile`) runs on the 2 mobile projects only; some specs contribute multiple PNGs per project (`agents-info-dialog` 2, `files-tab-admin` 2, `sessions` 2, `viewer3d-measure-plane` 3) hence the 82 total rather than 18 × 4 = 72.

### Verdict bucket counts

| Verdict | Count | Notes |
| --- | --- | --- |
| **buggy** (sanity-check seed + dark variants of the same root cause) | 4 | All `agents-dialog-*` variants: light variants confirmed defective per brief; dark variants share the same `dialog.tsx:34`+`:56` root cause and require regeneration after Story 5.7 lands even though they happen to render acceptably today. |
| **expected-buggy-pending-fix** | 24 | Phase B surface: 4 `agents-menu-open-*-light` + 4 `viewer3d-modal-open-*` (Story 5.7 dialog/sheet retokenization) + 16 `viewer3d-measure-*` (Story 5.8 viewer-overlay tokenization) + 2 `dev-components-*-dark` (Story 5.9 dark-mode status colors). |
| **unverified-defer-to-operator** | 54 | Everything else; operator confirms with eye-review at 100% zoom. |
| **OK** | 0 | No baseline is yet confirmed correct; awaits operator sign-off. |

Pre-classified regeneration scope (buggy + expected-buggy): **28 PNGs**. This matches the brief's Story 5.11 working estimate ("~20–30 PNGs across the affected specs × 4 projects").

### Skip-count reconciliation

- **Source-level skip statements:** 4.
- **Test-run-level skips after 4-project matrix expansion:** 14.
- **Matches the brief's "14 skips" figure exactly** when reconciled via the matrix:
  - `viewer3d-mobile` conditional skip → 2 skipped runs (only mobile projects pass the guard; the 2 desktop projects skip).
  - 3 × `test.describe.skip(...)` × 4 projects each = 12 skipped runs.
  - Total 14. No discrepancy.

### Sanity check

- **Known-buggy baseline `agents-dialog-desktop-light.png` appears in the buggy set:** confirmed. The 3 sibling project variants (desktop-dark, mobile-light, mobile-dark) are also marked buggy because they share the same `dialog.tsx:34`+`:56` root cause — the dark variants render acceptably today but bypass the theme tokens identically and must regenerate after Story 5.7 to land on the new `bg-overlay` / `bg-card` token contract.

### Story status

The audit data (Parts 1–3) is complete. The remaining work is **operator-driven visual review** of the 54 `unverified-defer-to-operator` baselines, executed in ≤20-PNG / ≤2-sessions-per-day batches per NFR4. Each session's verdicts get written back into the Part 2 tables, and the operator signs off inline in the "Operator review sessions" subsection. Story 5.2 advances from `in_progress` to `done` once every baseline has a verdict and every skip has a disposition (`skip→unskip` / `skip→delete` / `keep`).

### Surprises / follow-ups

1. **The "14-skip hole" is not a hole.** All 14 matrix-expanded skips trace to 4 source statements that are either legitimate project gates (1) or scaffold placeholders waiting for Slices 3D / 3E to ship (3). No flaky-test or TODO-investigate skip exists in the visual suite. The brief's concern that some skips might mask quality regressions does not materialise — the hole is narrative-level, not coverage-level.
2. **Orphan baselines on the `describe.skip` specs.** 12+ PNGs sit on disk for `files-tab-admin` and `catalog-detail-admin` despite the specs being skipped. These are stale snapshots from pre-Slice-3C implementation. Operator should decide whether to delete now (cleaner inventory; trivial revert if Slice 3D/3E regenerates the same names) or leave in place (no functional impact; visual-regression suite ignores them per project filtering). Recommend deletion at the same time Story 5.11 commits its baseline regen, so the catch-up is one bookkeeping commit.
3. **`viewer3d-mobile.spec.ts` only contributes 2 PNGs**, not 4. Worth noting because the brief's "82 PNGs across 18 specs × 4 projects" rough math doesn't divide cleanly; the actual distribution is uneven across specs. No action needed — just a note to set expectations during Story 5.11 sign-off.
4. **Dark-mode agents-dialog baselines are in the buggy bucket too.** Strictly the brief only names `agents-dialog-desktop-light.png` as the sanity-check seed. I extended buggy to cover the 3 sibling variants because the root cause (`dialog.tsx:34`+`:56` rgba bypass of theme tokens) is identical and Story 5.7 will retokenize regardless of theme — so all 4 must regenerate together to land on the new token contract. If operator disagrees and prefers to keep the dark variants OK-pending-review, flip them to `unverified-defer-to-operator` during the operator pass; the regen still has to include them because Story 5.7's source change touches the primitive both themes consume.
