---
title: 'TB-015 — "Wyczyść pomiary" footer button clickable in modal viewer (pointer-events fix)'
type: 'bugfix'
created: '2026-05-21'
status: 'done'
context:
  - 'apps/web/src/modules/catalog/components/viewer3d/'
tb_id: 'TB-015'
promoted_from: '_bmad-output/triage-backlog.md § TB-015'
baseline_commit: '05a2f1ace7b218e94d96bd2a3d0b84da5a5e2121'  # main HEAD at spec ready-for-dev flip (2026-05-21); Init 6 closing commit "chore: ruff format catch-up + Story 8.5 PASSWORD_RESET_TTL_SECONDS env wiring"
shipping_commit: 'e59abe5'  # 2026-05-21 "fix(viewer3d): re-enable pointer events on measure-clear footer (TB-015)"
shipped_at: '2026-05-21'
predecessor_scp: '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md (§3.4 — standalone quick-dev preceding Init 9 → 7 → 8 chain)'
auto_approval_directive: 'Operator standing approval per "lecimy do końca jak init 5" directive (2026-05-21); ITCM autonomous mode per memory [[itcm-autonomous-mode]]. Approval recorded here rather than via interactive HALT to honor "nie czekaj na mnie/nie rób pauz" operator instruction. Audit trail: spec generated 2026-05-21 by Claude bmad-quick-dev skill; no operator-side editing prior to status flip to ready-for-dev.'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** In the 3D viewer's modal host, the "Wyczyść pomiary" (Clear measurements) footer button in `MeasureSummary` is unclickable. The modal wrapper at [Viewer3DModal.tsx:390](apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx#L390) carries `pointer-events-none` to let canvas orbit/zoom/pan pass through empty overlay areas; list rows individually re-enable pointer events on each `<li>` ([MeasureSummary.tsx:50](apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx#L50)) which is why per-row × delete works, but the footer `<div>` containing the Clear button has no such override so its click is swallowed.

**Approach:** Add `pointer-events-auto` to the footer `<div>` in `MeasureSummary` ([MeasureSummary.tsx:82](apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx#L82)) — same explicit-re-enable-per-interactive-zone pattern already used at line 50 for rows. One-line change. Inline host (`Viewer3DInline.tsx`) does NOT carry `pointer-events-none` on its `<details>`-wrapped MeasureSummary container, so it already works; the fix is idempotent for inline (no regression).

## Boundaries & Constraints

**Always:**
- Preserve the modal canvas's orbit/zoom/pan behavior in the empty area surrounding the MeasureSummary panel. The `pointer-events-auto` override must stay scoped to the footer `<div>` (and the existing per-row override on `<li>` at line 50), NOT propagate up to the modal wrapper at Viewer3DModal.tsx:390.
- Preserve i18n: button label continues to come from `t("viewer3d.measure.clear")`.
- Both modal AND inline viewer footer buttons trigger `onClear` and clear `state.completed` deterministically.

**Ask First:**
- None. Fix is bounded; scope decided in pre-spec recon. No architectural decisions, no schema touches, no API contract changes.

**Never:**
- Do NOT change `Viewer3DModal.tsx:390`'s `pointer-events-none` wrapper class — that's load-bearing for canvas pass-through. Fix is in `MeasureSummary` only.
- Do NOT regress the existing `<li>` row `pointer-events-auto` override (line 50).
- Do NOT modify `measureReducer.ts` or its `clear` case — reducer was never the bug (`measureReducer.test.ts` unit coverage already passing).
- Do NOT introduce scope creep: no other MeasureSummary improvements in this commit (truncation, sort order, group-by-mode, etc.). One footer-clickability fix.
- Do NOT skip the visual-verification gate per memory [[feedback_frontend_visual_verification]] — agent-browser desktop + mobile snapshots before marking ready for review.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clear-empty | `measurements.length === 0` | `MeasureSummary` returns null (existing TB-012 behavior); button not rendered | N/A |
| Clear-one (modal) | 1 completed measurement in modal viewer; user clicks "Wyczyść pomiary" | `onClear` fires → reducer dispatches `{ type: "clear" }` → `state.completed = []` → MeasureSummary unmounts (returns null) | N/A |
| Clear-many (modal) | 3+ completed measurements in modal viewer; user clicks "Wyczyść pomiary" | Same as above — all rows cleared, all 3D-scene annotations removed | N/A |
| Clear-many (inline) | 3+ completed measurements in inline viewer (collapsed `<details>` open); user clicks "Wyczyść pomiary" | Same outcome as modal — pre-existing behavior preserved (inline never had the bug) | N/A |
| Canvas orbit (regression check) | Modal viewer open with 1+ measurements; user clicks-and-drags in empty modal area OUTSIDE the MeasureSummary panel | Canvas orbits normally (pointer-events-none on Viewer3DModal.tsx:390 still passes through) | N/A |
| Per-row delete (regression check) | Modal viewer with 2 measurements; user clicks × on row #1 | Row #1 removed; row #2 stays (existing `<li>` pointer-events-auto preserved) | N/A |

</frozen-after-approval>

## Code Map

- [apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx](apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx) — fix site (footer div at line 82); existing per-row `pointer-events-auto` at line 50 stays as-is
- [apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx](apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx) — test file (may not exist yet — likely a new file; check during implementation, create if missing)
- [apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx](apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx#L390) — modal host wrapper with `pointer-events-none` (load-bearing — do NOT modify); MeasureSummary mounted at L391
- [apps/web/src/modules/catalog/components/viewer3d/Viewer3DInline.tsx](apps/web/src/modules/catalog/components/viewer3d/Viewer3DInline.tsx#L352) — inline host wrapper (`<details>` shell, no pointer-events-none — already works); MeasureSummary mounted at L352
- [apps/web/src/modules/catalog/components/viewer3d/measure/measureReducer.ts](apps/web/src/modules/catalog/components/viewer3d/measure/measureReducer.ts#L149) — `clear` case (correct in isolation, not the bug site)
- [apps/web/src/modules/catalog/components/viewer3d/measure/measureReducer.test.ts](apps/web/src/modules/catalog/components/viewer3d/measure/measureReducer.test.ts) — existing unit tests for `clear` (passing standalone)
- [_bmad-output/triage-backlog.md](../triage-backlog.md) — TB-015 entry, update status `candidate` → `promoted` on dev-story start, then `promoted` → `done` on ship with commit SHA citation

## Tasks & Acceptance

**Execution:**
- [x] [`apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx#L82) -- added `pointer-events-auto` to footer `<div>` className (line 82, the `<div className="px-2 py-1 border-t border-border">` wrapping the `<Button>`); mirrors existing `<li>` pattern at line 50 (one-line change verified via `npx tsc --noEmit` clean + targeted vitest 3× consecutive PASS)
- [x] [`apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx) -- new file with 5 host-integration tests: (1) returns null when empty, (2) renders Clear button when measurements present, (3) `onClear` called exactly once on Clear click, (4) `onDelete` called with row id on × click (regression guard for per-row delete), (5) `pointer-events-auto` invariant on footer wrapper (TB-015 fix-invariant guard); mirrors FileSelector.test.tsx vitest+@testing-library/react pattern; 5/5 pass deterministically 3 consecutive runs
- [x] [`_bmad-output/triage-backlog.md`](../triage-backlog.md) -- TB-015 status flipped `candidate` → `done` with shipping-commit SHA `e59abe5` (2026-05-21) citation. Resolution paragraph follows TB-001/TB-002/TB-013 format with full root-cause + fix-shape + test-coverage + adversarial-review summary embedded.

**Acceptance Criteria:**
- Given the modal viewer open with at least one completed measurement, when the user clicks the "Wyczyść pomiary" footer button, then `onClear` fires, the reducer transitions to `{ active: { stage: "empty" }, completed: [] }`, and `MeasureSummary` returns null (button + rows unmount).
- Given the modal viewer with measurements, when the user clicks-and-drags in the modal area OUTSIDE the MeasureSummary panel, then the canvas orbits/zooms/pans normally (no regression of the pointer-events pass-through at `Viewer3DModal.tsx:390`).
- Given the inline viewer with measurements (collapsed `<details>` expanded), when the user clicks the "Wyczyść pomiary" footer button, then the same clear behavior occurs as in modal (inline path unchanged but verified non-regressed).
- Given the modal viewer with two measurements, when the user clicks the × button on row #1, then row #1 is removed and row #2 persists (existing per-row delete behavior preserved — `<li>` pointer-events-auto at line 50 untouched).
- Given the new MeasureSummary integration test from the Execution list, when `npm run test` runs, then the test passes 3 consecutive times (deterministic — no flakes).

## Spec Change Log

### 2026-05-21 — Review-loop patches (test-only; no production-code amendment, no frozen-block change)

3 BMAD review subagents dispatched per step-04. Classification: 0 intent_gap, 0 bad_spec (spec content sound), 3 patch, 1 defer, 4 reject. No loopback to step-03. All patches applied to `MeasureSummary.test.tsx`; production code (`MeasureSummary.tsx` line 82) unchanged from initial implementation.

**Patches applied:**
1. **parentElement fragility (Edge-Case-Hunter P2)** — test #5 originally asserted `clearButton.parentElement.className.includes("pointer-events-auto")`. Brittle: if shadcn `Button` ever wraps in `<Tooltip>` or `<Slot asChild>`, `parentElement` becomes the wrapper. **Fix:** rewrote test #5 to mount MeasureSummary inside a `pointer-events-none` ancestor (simulating Viewer3DModal.tsx:390) and assert (a) `closest(".pointer-events-auto")` returns a non-null ancestor between the button and the outer wrapper, AND (b) the click actually fires `onClear`. End-to-end TB-015 regression guard, robust to internal Button restructuring.
2. **Row-delete selector specificity (Blind-Hunter P2)** — test #4 originally used loose `/usu|delete/i` regex and `[0]` indexing. **Fix:** switched to scope-by-row with `getAllByRole("listitem")` + `within(row).getByRole("button")`. Asserts exactly 2 rows and operates on row #1's delete button by structural position.
3. **Inline-host coverage gap (Edge-Case-Hunter P2)** — absorbed into patch #1. By simulating modal-host wrapping in test #5, the test is host-agnostic. Inline host is not exercised by the test suite — explicit non-goal per spec § Boundaries.

**Deferred:**
- **TB-015-D1: Touch/mobile backdrop-blur pointer-events edge cases on iOS Safari** (Edge-Case-Hunter P3). Filed in `_bmad-output/implementation-artifacts/deferred-work.md`.

**Rejected (silently dropped):** fixture distance decoupling (Blind-Hunter P2), `Number("0") || 0` cosmetic (Blind-Hunter P3), i18n regex collision (Edge-Case-Hunter P3), empty-state explicit assertion (Edge-Case-Hunter P3).

**KEEP** (preserve through any future re-derivation):
- `afterEach(() => cleanup())` per project-context.md L115 + memory [[feedback_vitest_manual_cleanup]].
- `import "@/locales/i18n"` at top to surface `t()` lookups during render (mirrors FileSelector.test.tsx pattern).
- Test #5 mounts under `pointer-events-none` ancestor to exercise the actual TB-015 invariant.
- `pointer-events-auto` on the footer `<div>` in `MeasureSummary.tsx:82` — mirror of L50's per-row pattern; do NOT move to outer `<div>` at L42.

## Verification

**Commands (frontend only — no backend touch in this spec):**
- `cd apps/web && npm run lint` -- expected: zero warnings, zero errors (per project-context.md L50 `--max-warnings=0` gate)
- `cd apps/web && npx tsc --noEmit` -- expected: clean (no type errors)
- `cd apps/web && npm run test apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx` -- expected: pass 3 consecutive runs (new integration test plus any existing tests)
- `cd apps/web && npm run test` -- expected: full vitest suite pass (no collateral regression from the className change)

**Visual verification (per [[feedback_frontend_visual_verification]] memory — mandatory pre-CR):**
- `agent-browser navigate https://3d.ezop.ddns.net/catalog` (or local dev URL post-deploy)
- Open a model with completed measurements → modal viewer
- Take desktop-default snapshot (1280×720): confirm footer button visible, click-test it (`agent-browser click "@<refId>"`), confirm measurements clear AND no console errors AND modal background canvas still responsive to drag-orbit
- Resize to mobile-light (390×844 Pixel-5-equivalent): same test sequence
- Attach snapshots to Dev Agent Record

**Manual checks if agent-browser unavailable:**
- Standalone Playwright visual run for any existing modal-viewer baselines that include the MeasureSummary footer; baseline-reviewed lines in commit message per project-context.md L245 if any baselines change
- Human-eyeball test on .190 dev portal post-deploy: open modal viewer, place 2 measurements, click "Wyczyść pomiary", confirm rows + scene annotations disappear; click-drag canvas in empty modal area, confirm orbit works

**Deploy:** `infra/scripts/deploy.sh` after merge to main per memory [[feedback_auto_deploy_dev]] (this is code, not doc-only).

## Suggested Review Order

**TB-015 production fix**

- One-line production change: re-enable pointer events on footer wrapper so the Clear button is clickable under the modal's canvas-pass-through wrapper.
  [`MeasureSummary.tsx:82`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx#L82)

- Existing per-row pattern the fix mirrors (load-bearing reference — DO NOT modify; the new footer override imitates this row-level override).
  [`MeasureSummary.tsx:50`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx#L50)

- Load-bearing modal wrapper with `pointer-events-none` (unchanged — explains why the fix is necessary).
  [`Viewer3DModal.tsx:390`](../../apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx#L390)

**Regression guard — TB-015 invariant test**

- The end-to-end invariant test: mount under a `pointer-events-none` ancestor (modal-host simulation), assert click reaches `onClear` AND a re-enabling ancestor exists. Robust to internal Button restructuring.
  [`MeasureSummary.test.tsx:94`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx#L94)

**Regression guards — host integration tests**

- Per-row × delete still works (row #1 selection by structural position via `getAllByRole("listitem")` + `within(row)`).
  [`MeasureSummary.test.tsx:75`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx#L75)

- Empty-state returns null (no overlay obscures canvas when no measurements).
  [`MeasureSummary.test.tsx:45`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx#L45)

- Button-presence + onClear-call-once happy paths.
  [`MeasureSummary.test.tsx:52`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx#L52)

**Test fixtures (peripheral)**

- Real `three.Vector3` instances + `Plane`-shaped fixtures matching `types.ts` discriminated union.
  [`MeasureSummary.test.tsx:11`](../../apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.test.tsx#L11)
