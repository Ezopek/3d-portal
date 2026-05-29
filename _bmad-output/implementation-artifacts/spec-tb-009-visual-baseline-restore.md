---
title: 'TB-009 — Restore Playwright visual-regression baseline (locale-mismatch rot from i18n sweep 212c025)'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
baseline_commit: 'c35b5dc'
final_commit: 'fd049e5'
review:
  reviewer: 'codex'
  verdict: 'APPROVE'
  findings: 0
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `npm run test:visual` produces ~66 fails / 24 passes / 14 skips across all 4 projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`) on bare `main`, unrelated to current dev work (stash-and-rerun verified during light-theme-polish, c35b5dc). The broken gate blocks every future UI PR. Forensics pin 58+ failures to `212c025` (`feat(web): i18n + a11y sweep`) — switched copy and tab labels to `t(...)` without updating Playwright selectors or regenerating snapshots; remaining 8 trace to May-8 sessions+i18n batch (`0eebfe9` / `eaac1c4`). **R3 scope discovery (see Spec Change Log 2026-05-12-A): viewer3d snapshots additionally drifted from real product evolution (palette refactor, toolbar icons, MeasureSummary introduction) AND surface a pre-existing src bug (`MeasureSummary.tsx:37` calls `t("viewer3d.measure.summary.empty")` but locale key is `summary_empty`). Viewer3d snapshot regen + src fix split into TB-010 to keep TB-009 test-only.**

**Approach:** Three prongs, strict order: (a) fix viewer3d selectors matching English `/^files\b/i` so they resolve under `locale: "pl-PL"` (prefer locale-agnostic `getByRole("tab")`, PL text only when role-only is ambiguous) — this fixes selector timeouts but viewer3d screenshots remain failing pending TB-010; (b) same selector fix on `sessions.spec.ts` `text=Active sessions`; (c) after a+b selectors resolve, regenerate snapshots for the 8 catalog/dev specs (NOT viewer3d) after inspecting ≥4 representative diffs. Single PR acceptable.

## Boundaries & Constraints

**Always:**
- Selectors locale-aware — role-only without `name`, or `name` matching the current PL render.
- Snapshot regen only after prongs (a)+(b) selectors resolve cleanly (else stale capture freezes failures into baseline).
- Inspect ≥4 representative diffs (1 per project) before any wholesale `--update-snapshots`.
- ESLint `--max-warnings=0` clean; `npx tsc --noEmit` clean; `en.json` / `pl.json` key parity preserved.
- 4 projects GREEN for `sessions` and the 8 catalog/dev specs at end. Viewer3d failures (~30) acknowledged as **known issue → TB-010**.

**Ask First:**
- Any change to `playwright.config.ts` `locale` (flipping to `en-US` masks the bug suite-wide).
- Any selector requiring a component-source edit (adding `aria-label` / `data-testid`).

**Never:**
- `test.skip` / `test.fixme` to make a spec green — fix, don't silence.
- Touch component source (`apps/web/src/**`) — root cause is in tests.
- Edit any i18n key in `en.json` / `pl.json`.
- `--update-snapshots` blindly without the ≥4-diff inspection.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error Handling |
|----------|---------------|----------|----------------|
| viewer3d tab under PL | `locale: "pl-PL"`, tab `"Pliki"` | Role-only or PL-`name` filter resolves in default timeout | Ambiguous? Scope container + `nth()`; never EN regex |
| Sessions heading | PL render of `"Aktywne sesje"` | PL match or `getByRole("heading", { level: 1 })` | Multiple h1s? Scope to main landmark |
| Spec correct, snapshot stale | Selectors green; snapshot shows `"no preview"`, UI renders `"brak podglądu"` | Targeted `--update-snapshots` for the 8 specs; diffs = PL text + minor reflow | Layout/colour drift unrelated to text → HALT |
| EN-only selector "fix" (anti-pattern) | `name: /^files\b/i` retained | Spec re-times-out next CI | Reject in self-review |
| Snapshot regen captures transient | Animation / lazy image not settled | Diff oscillates between runs | Re-run; if still flaky, file separately |
| Dark-only failure post-fix | Light projects green, dark still fail | Separate category; do not mask | If categorically new → HALT |
| viewer3d screenshot drift beyond locale text | After selector fix, viewer3d still fails on `toHaveScreenshot` (cube colour, toolbar icons, raw i18n key) | Acknowledge as TB-010 scope; do NOT regen viewer3d snapshots in TB-009 (would bake raw `summary.empty` key into baseline) | Discovered in implementation, see Spec Change Log 2026-05-12-A |

</frozen-after-approval>

## Code Map

All paths live under `apps/web/tests/visual/`.

**Prong (a) — viewer3d selector resolves under PL (selectors only, ~30 screenshot fails persist → TB-010).** Cause: `212c025` flipped `apps/web/src/modules/catalog/components/SecondaryTabs.tsx:46` to `t("catalog.tabs.files")` → `"Pliki"`. All six specs share the broken `getByRole("tab", { name: /^files\b/i })` pattern — identical swap to each: `viewer3d-modal-open`, `viewer3d-modal-closed`, `viewer3d-measure-pp`, `viewer3d-measure-plane`, `viewer3d-inline-loaded`, `viewer3d-mobile`. **TB-009 does NOT regenerate viewer3d snapshots** — they additionally drifted from `846e2d5`/`7fe96bd`/`8a02101` (palette refactor / toolbar icons) and `34125a4`/`8be931b` (MeasureSummary surfaces a `summary.empty`/`summary_empty` key mismatch). TB-010 owns the src fix + viewer3d snapshot regen.

**Prong (b) — sessions (8 fails = 4 projects × 2 asserts).** Cause: `0eebfe9` / `eaac1c4` left EN selector vs PL render at `apps/web/src/routes/settings/sessions.tsx:47` (`t("auth.sessions.title")` = `"Aktywne sesje"`). Edit: `sessions.spec.ts:54` — `text=Active sessions` → role-based or PL match.

**Prong (c) — snapshot regen after (a)+(b) green (~28 pixel drifts).** Cause: `212c025` shipped user-copy changes across `ModelGallery.tsx`, `SecondaryTabs.tsx`, `FilterRibbon.tsx`, `PhotosTab.tsx`, `PrintsTab.tsx`, `OperationalNotesTab.tsx`, `DescriptionPanel.tsx`, `MetadataPanel.tsx`, `ExternalLinksPanel.tsx` without snapshot updates (`git show 212c025 --name-only | grep __snapshots__` = 0). Regenerate for: `catalog-list`, `catalog-detail`, `dev`, `empty-states` (incl. `"no preview"` → `"brak podglądu"`), `focus-ring`, `v2-placeholders`, `agents-info-dialog`, `catalog-card-carousel` — each plus its `__snapshots__/<name>.spec.ts-snapshots/*`.

Out of scope, must stay untouched: `admin-thumbnail-flow.spec.ts`, `catalog-detail-admin.spec.ts`, `files-tab-admin.spec.ts`, `api-stubs.ts`, `helpers.ts`, `fixtures/`.

## Tasks & Acceptance

**Execution** (strict order — never regen snapshots before selectors are green):

- [x] `viewer3d-modal-open.spec.ts` — replace EN-regex tab selector with locale-agnostic role-only filter (or scoped `nth()` if ambiguous).
- [x] `viewer3d-modal-closed.spec.ts` — same selector swap.
- [x] `viewer3d-measure-pp.spec.ts` — same.
- [x] `viewer3d-measure-plane.spec.ts` — same.
- [x] `viewer3d-inline-loaded.spec.ts` — same.
- [x] `viewer3d-mobile.spec.ts` — same.
- [x] `sessions.spec.ts` — `text=Active sessions` → role-based heading match (or PL text).
- [x] Gate run `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts sessions.spec.ts` — all 4 projects GREEN before prong (c). (Viewer3d selectors verified resolving but screenshots intentionally left failing → TB-010.)
- [x] Inspect ≥4 representative HTML diffs (1 per project) from the 8 catalog/dev specs; confirm PL-text + expected reflow only.
- [x] Targeted `--update-snapshots` for the 8 catalog/dev specs ONLY (not viewer3d, not suite-wide); commit regenerated `__snapshots__/`.
- [x] Full re-run `npm run test:visual` — sessions + 8 catalog/dev specs GREEN on all 4 projects; viewer3d ~30 failures persist as known TB-010 (matches Spec Change Log expectation).
- [x] `git diff --name-only main...HEAD -- apps/web/src/` — must be empty.

**Acceptance Criteria:**
- Given the merge commit, `npm run test:visual` returns 0 failures for `sessions.spec.ts` and the 8 catalog/dev specs across all 4 projects. Viewer3d ~30 failures persist; documented as known TB-010 issue (no NEW failures introduced beyond what TB-010 will own).
- 14 pre-existing skips unchanged — no new `test.skip` / `test.fixme`.
- Merge diff filtered to `apps/web/src/` is empty (no component source touched).
- No `name` regex matches an English-only literal in any modified spec.
- Regenerated catalog/dev snapshots show PL text + minor reflow only — no colour, layout, or component-shape drift (anything beyond → HALT).
- Selector pattern is documented (PR description or one-line spec comment) — explicit role-only vs PL-name choice so future i18n sweeps don't re-break the suite.

## Spec Change Log

### 2026-05-12-A — Viewer3d snapshot regen split out to TB-010 (intent_gap, R3 decision)

**Trigger:** During Phase 2 gate run, sub-agent surfaced 34 `toHaveScreenshot` pixel-diff failures in viewer3d specs AFTER selector swap (prong a) succeeded. Inspection of `viewer3d-modal-open desktop-light` diff revealed:

1. **Pre-existing src bug** — `apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx:37` calls `t("viewer3d.measure.summary.empty")` (dot) but locale files key is `viewer3d.measure.summary_empty` (underscore). Raw i18n key renders in UI. Split-commit regression (`34125a4` src + `8be931b` locales).
2. **Real product drift** — cube colour (grey→black, palette refactor `846e2d5`/`7fe96bd`/`8a02101`), toolbar icons (letter glyphs → icon-only), item-counter position. Legitimate post-baseline product evolution.

**Why this is intent_gap:** Frozen Intent assumed prong (a) selector-fix would make viewer3d green. False — selectors resolve, but `toHaveScreenshot` still fails on legitimate drift. Spec Code Map listed only 8 catalog/dev specs for snapshot regen. Spec.Never explicitly forbids touching `apps/web/src/**` — so `summary.empty` fix can't be added to TB-009.

**Three options surfaced to Ezop:**
- **R1** — drop viewer3d entirely from TB-009; revert selector swaps; file TB-010 for everything viewer3d-related.
- **R2** — extend TB-009 with src fix (amend Boundaries.Never) + viewer3d snapshot regen.
- **R3** — keep viewer3d selector swaps in TB-009 (they're test-side, correct, and respect spec.Never); explicitly defer viewer3d snapshot regen + `summary.empty` src fix to TB-010; weaken AC to "sessions + 8 catalog/dev green; viewer3d failures isolated as known TB-010".

**Ezop chose R3.**

**Amendment:**
- Intent.Problem extended with R3 scope discovery callout.
- Intent.Approach clarifies prong (a) is "selector-only" (snapshots stay failing pending TB-010).
- Boundaries.Always weakened "all 4 projects GREEN" → "sessions + 8 catalog/dev GREEN; viewer3d acknowledged as TB-010".
- I/O Matrix gains a row covering this drift category.
- Code Map prong (a) caveat: "TB-009 does NOT regenerate viewer3d snapshots".
- Tasks.Execution: gate run scope narrowed to `sessions.spec.ts` only; final visual-run AC reflects partial-green expectation.
- Acceptance Criteria split: full-green for sessions+catalog/dev, viewer3d failures persist as documented known issue.

**KEEP:** sub-agent's Phase 1 selector-swap work in 7 spec files is preserved (correct work, respects all constraints). Phase 3 (catalog/dev regen) proceeds as originally specified. PL-name match strategy chosen for viewer3d (`/^pliki\b/i`) and role-only `getByRole("heading", { level: 1 })` for sessions — both correct, kept.

**Follow-up — TB-010 to be filed after TB-009 ships:** (a) fix `summary.empty` → `summary_empty` (one-line decision: rename src OR rename locale key), (b) verify cube/toolbar drift is intended product evolution, (c) regenerate 6 viewer3d snapshots after src fix.

## Design Notes

**Root cause:** Playwright `locale: "pl-PL"` renders every page through the PL i18n bundle. Pre-`212c025`, specs used English-literal selectors because tabs/headings rendered hardcoded English. `212c025` swapped to `t(...)` (correct in product code) but did not update specs or regenerate snapshots in the same commit. May-8 sessions batch repeated the pattern at smaller scale.

**Selector policy going forward:** Prefer `getByRole("tab")` / `getByRole("heading")` without `name`, scoped to a container if multiple match. When `name` is unavoidable, match the PL literal and add a one-line comment naming the locale dependency so the next i18n sweep updates selectors atomically with copy.

**Systemic angle:** `212c025` shipped in the 2026-05-10 UI-review multi-PR batch — the same operational pattern that prompted memory `feedback_default_to_bmad_workflow.md` ("multi-PR batches from review docs are epics in disguise"). Epic-routed scoping would have folded visual-baseline maintenance into story AC and prevented this rot. TB-009 is the cleanup; the prevention is that routing rule.

**Why fix tests, not components:** `t(...)` is the intended end state; tests own "contract holds under realistic conditions" — which include PL.

## Verification

**Commands** (`PW=npx playwright test --config=tests/visual/playwright.config.ts`, run from `apps/web/`):
- Gate (after prongs a+b): `$PW viewer3d-*.spec.ts sessions.spec.ts` — all 4 projects green.
- Regen (only after gate): `$PW --update-snapshots catalog-list.spec.ts catalog-detail.spec.ts dev.spec.ts empty-states.spec.ts focus-ring.spec.ts v2-placeholders.spec.ts agents-info-dialog.spec.ts catalog-card-carousel.spec.ts` — inspect HTML report first.
- Full: `npm run test:visual` — 0 failures across all 4 projects.
- `npm run lint` — 0 warnings; `npx tsc --noEmit` — 0 errors.
- From repo root: `git diff --name-only main...HEAD -- apps/web/src/` — empty (no component changes); `... -- apps/web/tests/visual/` — 7 spec files + regenerated snapshots for the 8 catalog/dev specs.

**Manual checks:**
- Open the Playwright HTML report after prong (c); spot-check 4 diff images (one per project) — confirm text-only deltas, no layout/colour surprises.
- `grep -nE "test\.(skip|fixme|only)" apps/web/tests/visual/*.spec.ts` — no new entries vs pre-fix baseline.

## Suggested Review Order

**Selector strategy decision (the keystone)**

- PL-name match `name: /^pliki\b/i` chosen over role-only because SecondaryTabs has 3-5 sibling tabs (ambiguous). Locale dependency commented inline.
  [`viewer3d-modal-open.spec.ts:24`](../../apps/web/tests/visual/viewer3d-modal-open.spec.ts#L24)

- Sessions chose role-only `getByRole("heading", { level: 1 })` — single `<h1>`, no ambiguity, locale-agnostic preferred when possible.
  [`sessions.spec.ts:56`](../../apps/web/tests/visual/sessions.spec.ts#L56)

**Prong (a) — viewer3d selectors (same swap × 6)**

- Identical pattern across 6 specs; reviewing one + the diff stat for the others is sufficient.
  [`viewer3d-modal-closed.spec.ts`](../../apps/web/tests/visual/viewer3d-modal-closed.spec.ts) · [`viewer3d-measure-pp.spec.ts`](../../apps/web/tests/visual/viewer3d-measure-pp.spec.ts) · [`viewer3d-measure-plane.spec.ts`](../../apps/web/tests/visual/viewer3d-measure-plane.spec.ts) · [`viewer3d-inline-loaded.spec.ts`](../../apps/web/tests/visual/viewer3d-inline-loaded.spec.ts) · [`viewer3d-mobile.spec.ts`](../../apps/web/tests/visual/viewer3d-mobile.spec.ts)

**Prong (c) — regenerated snapshots (the bulk)**

- 28 modified PNGs (catalog/dev specs) + 8 new sessions baselines. Spot-check ≥4 (1 per project) to confirm PL-text + minor reflow only.
  [`__snapshots__/`](../../apps/web/tests/visual/__snapshots__/)

**Scope guard (sanity)**

- `git diff --name-only c35b5dc HEAD -- apps/web/src/` MUST be empty — TB-009 is test-only. Verified in the commit body.

**Out-of-scope acknowledgment**

- Viewer3d screenshots (~26 failures) intentionally left red — owned by TB-010 (filing pending). Spec Change Log entry 2026-05-12-A is the audit trail for this scope split.
