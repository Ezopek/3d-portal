---
title: 'Story 25.1 — Mobile photo-reorder touch-action (TB-038)'
type: 'bugfix'
status: 'ready-for-dev'
story_id: '25.1'
epic: '(standalone — no parent epic)'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-038'
fr_ref: 'FR16-MOBILE-DRAG-1'
nfr_ref: 'NFR16-VISUAL-VERIFICATION-1'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.4-mini per [[feedback_codex_model_routing]] routine FE class)'
estimated_effort: '5-15 min one-line CSS + visual verify + commit'
created: '2026-05-24'
---

# Story 25.1 — Mobile photo-reorder `touch-action: none` on dnd-kit handle (TB-038)

Status: ready-for-dev

## Story

As an admin curating photo order on a touch device (operator's reported observation 2026-05-24),
I want the drag handle to claim the touch gesture so vertical finger movement reorders the photo row instead of scrolling the page,
so that mobile photo curation actually works (closes the canonical dnd-kit + TouchSensor pitfall documented upstream at https://docs.dndkit.com/api-documentation/sensors/touch#touch-action).

## Acceptance Criteria

1. **AC1 — `touch-action: none` applied to DragHandle.** `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:244-253` `DragHandle` button className extended with Tailwind `touch-none` (= `touch-action: none`). The complete className changes from `"cursor-grab text-muted-foreground"` to `"cursor-grab touch-none text-muted-foreground"` (or equivalent Tailwind-ordered form).

2. **AC2 — Mobile drag reorders rows without scrolling the page.** Verified via agent-browser touch viewport emulation OR Playwright touch device emulation per [[feedback_frontend_visual_verification]]: dragging the grip icon vertically reorders the photo row instead of scrolling the page. Touching outside the grip area (`flex-1` button section) still scrolls the page naturally (preserves scroll-reach UX — the photo list itself can be scrolled, just not via the grip handle).

3. **AC3 — Desktop unaffected.** PointerSensor (mouse) behavior unchanged. No regression on desktop drag (already worked).

4. **AC4 — No unit-test regression.** Existing `PhotosTab.test.tsx` (if any tests exist for the surface) continues to PASS. `npm run typecheck` + `npm run lint` clean for the touched file.

5. **AC5 — Codex review CLEAN (gpt-5.4-mini routine FE class).** Routine refactor; no security/concurrency sensitivity. Codex CLEAN expected on round-1.

## Tasks / Subtasks

- [ ] **T1 — Add `touch-none` to DragHandle className** (AC: #1)
  - [ ] T1.1 — Edit `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:247` to change className from `"cursor-grab text-muted-foreground"` to `"cursor-grab touch-none text-muted-foreground"`.

- [ ] **T2 — Verify on touch viewport** (AC: #2, #3)
  - [ ] T2.1 — agent-browser navigate to `/admin/models/<id>` Photos tab on a model with multiple photos. Emulate touch viewport (e.g. iPhone 12 or generic mobile). Drag the grip icon vertically — confirm the photo row visually moves with the finger AND the page does not scroll.
  - [ ] T2.2 — Verify touching outside the grip area still scrolls the page (touch the photo thumbnail or filename text → swipe → page scrolls).
  - [ ] T2.3 — Verify on desktop (PointerSensor with mouse) no regression — drag still works.

- [ ] **T3 — Pre-merge gates** (AC: #4)
  - [ ] T3.1 — `cd apps/web && npm run typecheck` exit 0.
  - [ ] T3.2 — `cd apps/web && npm run lint` exit 0.
  - [ ] T3.3 — `cd apps/web && npx vitest run src/modules/catalog/components/tabs/PhotosTab.test.tsx` (if file exists) — PASS.

- [ ] **T4 — Commit + Codex review + auto-deploy** (AC: #5)
  - [ ] T4.1 — Single dev commit: `fix(catalog,admin): touch-action none on PhotosTab DragHandle for mobile drag (Story 25.1, TB-038)`.
  - [ ] T4.2 — ff-merge to `main`.
  - [ ] T4.3 — `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` → CLEAN.
  - [ ] T4.4 — Auto-deploy to .190 per [[feedback_auto_deploy_dev]].
  - [ ] T4.5 — Sprint-status flip `25-1-mobile-photo-reorder-touch-action: backlog → done` (skipping interim review state for trivial one-line change after Codex CLEAN).
  - [ ] T4.6 — Triage-backlog TB-038 status → done with commit cite.

## Dev Notes

### Root cause (re-statement from TB-038)

`apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:46-51` configures dnd-kit with BOTH `PointerSensor` (desktop) and `TouchSensor` (mobile, `activationConstraint: { delay: 250, tolerance: 5 }`). The `DragHandle` button at lines 244-253 spreads `{...attributes} {...listeners}` from `useSortable` onto a button with className `"cursor-grab text-muted-foreground"` — no `touch-action` declaration.

Per https://docs.dndkit.com/api-documentation/sensors/touch#touch-action: without `touch-action: none` on the draggable element, the browser claims the vertical pan gesture for native scrolling BEFORE the TouchSensor can call `event.preventDefault()`. The 250ms activation delay actually makes it worse: by the time the sensor wants to claim the gesture, the browser has already committed to scrolling.

### Why minimum-viable fix is correct

The dnd-kit upstream guidance is explicit: add `touch-action: none` to the draggable handle. Tailwind exposes this as `touch-none` utility class. Single-class addition; mechanical; no API change; no test fixture change.

### Optional follow-up (NOT in Story 25.1 scope)

Per Story 25.1 spec optional AC3 in original TB-038 write-up: revisit TouchSensor `delay: 250` activation threshold for snappier feel post-fix. Likely reducible to `delay: 100` or moved to `distance`-based activation now that `touch-action: none` is in place. DEFERRED — operator can surface during review if they want snappier drag-start.

### Why this is NOT bundled with TB-040 mobile-gesture-deferrals from Story 22.3

Story 22.3 designer spec (`_bmad-output/implementation-artifacts/22-3-designer-ux-spec.md`) deferred pinch-to-zoom + swipe-down-to-close on the NEW fullscreen image viewer to a hypothetical TB-040 candidate. That's a different surface entirely (image fullscreen viewer, NEW component) and a different gesture class (pinch + swipe-vertical-on-image). Story 25.1 is the existing PhotosTab drag handle. No overlap.

## File List

**MODIFIED (1):**
- `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx` — single className addition at line 247

**Diff stats expected:**
- 1 file, 1 line modified, 0 lines deleted (cumulative addition: ~12 characters for `touch-none ` prefix)

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Typecheck | `cd apps/web && npm run typecheck` | Exit 0 |
| Lint | `cd apps/web && npm run lint` | Exit 0 |
| Mobile drag manual | agent-browser touch viewport on `/admin/models/<id>` Photos tab | Drag handle reorders without page scroll |
| Desktop no-regression | agent-browser desktop viewport same surface | Drag still works via mouse |
| Codex review | `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` | CLEAN |

## References

- [Init 16 SCP §4.4](sprint-change-proposal-2026-05-24-init16.md#44-standalone-story-s251--mobile-photo-reorder-touch-action) — Standalone Story 25.1 originating scope.
- [epics.md § Initiative 16 § Standalone Story S25.1](../planning-artifacts/epics.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Story 25.1 description.
- [prd.md § FR16-MOBILE-DRAG-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Verifiable requirement.
- [triage-backlog.md § TB-038](../triage-backlog.md) — Original candidate write-up + dnd-kit upstream link.
- https://docs.dndkit.com/api-documentation/sensors/touch#touch-action — upstream dnd-kit guidance.
- Memory entries:
  - [[feedback_codex_model_routing]] — gpt-5.4-mini for routine FE class.
  - [[feedback_frontend_visual_verification]] — touch viewport emulation required.
  - [[feedback_auto_deploy_dev]] — auto-deploy on commit to main.

## Dev Agent Record

### Agent Model Used

(Filled in by dev-story execution)

### Debug Log References

(Filled in during dev-story phase)

### Completion Notes List

(Filled in during dev-story phase)

### File List

(Filled in during dev-story phase — expected match to File List above)
