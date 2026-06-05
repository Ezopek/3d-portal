---
title: 'E33.1 correction — estimate quality_tier control back to a native select'
type: 'bugfix'
created: '2026-06-05'
status: 'done'
context: []
baseline_commit: '4fc6cfe'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Shipped Story 33.1 rendered the `quality_tier` control in `CatalogEstimateProfileSelector` as a segmented pill / radio-button group (`role=radiogroup` + `role=radio` buttons). The operator (controller) corrected this: quality must be a native `<select>`/combobox again, because more profile/quality options may be added later and a select scales better and avoids layout drift on the compact catalog Files/STL surface.

**Approach:** Replace only the quality_tier render layer — swap the `radiogroup` of `<button role="radio">` elements for a single native `<select>` whose `<option>`s carry the same tier labels. All selection/compatibility/availability logic (`isAvailable`, `isTierCompatible`, `selectTier`, `selectMaterial`, `compatibleTiers`) is unchanged; only the JSX control type and the test/visual assertions that key off `role=radio` change. Material already is a `<select>` and stays one.

## Boundaries & Constraints

**Always:** Incompatible tiers stay HIDDEN (not rendered as options); compatible-but-unavailable tiers stay PRESENT but `disabled` with reason text inline in the option label; fail-open preserved (omitted / empty / missing availability → tier selectable); Standard never locked out; `spoolman_filament_ref` stays `null` on every emitted preset; the quality `<select>` keeps an accessible name via a `<label htmlFor>`.

**Ask First:** Any change to backend availability/compatibility contracts, preset shape, or i18n reason keys beyond what already exists.

**Never:** No print-ordering / spool-selection / quote surface added. No change to `material_class` exposure (Path B stays). No new resolve logic. No change to `FilesTab` wiring or the availability hook.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Compatible + available tier | PLA, `standard` available | Rendered as enabled `<option>`; selectable; onChange emits `{quality_tier}` | N/A |
| Compatible but unavailable | PLA, `strong` `available:false` `profile_not_imported` | `<option disabled>` with `"Strong · Not available yet"` text; cannot be selected | guard in `selectTier` ignores it |
| Incompatible tier | TPU, `aesthetic`/`strong` | Not rendered as an option at all | N/A |
| Fail-open (no availability) | PLA, `availability` omitted / `[]` / missing row | All compatible tiers enabled and selectable; Standard never disabled | tier stays selectable |
| Material change re-keys tier | PLA/standard → TPU | onChange emits TPU with a compatible tier and `spoolman_filament_ref: null` | falls to first compatible tier |

</frozen-after-approval>

## Code Map

- `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx` -- the component; quality control JSX (lines ~122-172) is the only render block that changes; logic functions untouched.
- `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.test.tsx` -- vitest unit tests; replace `role=radio` queries with `role=option` / select `change` events.
- `apps/web/tests/visual/catalog-filestab-estimate.spec.ts` -- visual spec; the `button[role="radio"]:disabled` count assertion becomes `option:disabled`.
- `apps/web/tests/visual/__snapshots__/` -- Playwright baselines for the FilesTab estimate states change (selector control re-rendered).
- `apps/web/src/locales/{en,pl}.json` -- existing `modules.estimates.selector.*` reason keys reused as-is (no new keys).

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx` -- replaced the `role=radiogroup` + `<button role="radio">` block with a labelled native `<select>` whose `<option>`s map `compatibleTiers`; disabled option for unavailable tiers with inline reason text; `onChange` calls existing `selectTier`. Logic functions kept verbatim; removed now-unused `cn` import and `reasonIdBase`.
- [x] `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.test.tsx` -- updated assertions from radio to option/select semantics; added a case asserting no radio/radiogroup remains; preserved every behavioral case (hide incompatible, disable unavailable + ignore selection, fail-open, spool null, both locales). 8/8 green.
- [x] `apps/web/tests/visual/catalog-filestab-estimate.spec.ts` -- replaced `button[role="radio"]:disabled` locator with `option:disabled`; updated the comment.
- [x] `apps/web/tests/visual/__snapshots__/` -- regenerated the 20 affected FilesTab estimate baselines via `--update-snapshots` (stale-baseline class confirmed by diff inspection: change confined to the selector row).

**Acceptance Criteria:**
- Given the catalog Files/STL surface, when the selector renders, then the quality control is a single native `<select>` with an accessible name, not a group of radio buttons.
- Given a tier that is compatible but `available:false`, when options render, then that tier is a `disabled` `<option>` showing the localized reason text and cannot be selected.
- Given a tier incompatible with the chosen material, when options render, then no option exists for it.
- Given availability is omitted/empty/missing, when the selector renders, then every compatible tier (incl. Standard) is an enabled, selectable option.
- Given any selection or material change, when `onChange` fires, then `spoolman_filament_ref` is `null`.

## Spec Change Log

Step-04 adversarial review (2026-06-05) — three perspectives: Acceptance Auditor (`feature-dev:code-reviewer`), Blind Hunter + Edge Case Hunter (`general-purpose`; the BMAD-specific reviewer subagent types are not registered in this harness, so the available equivalents were used). No `intent_gap` / `bad_spec` — no loopback. Three `patch`-class findings applied within scope; one rejected.

- **patch (hardened invariant #3)** — `selectTier` spread `{ ...value, quality_tier }` without re-nulling `spoolman_filament_ref`, leaving the operator's load-bearing invariant dependent on caller context (pre-existing in the radio version). Now emits `spoolman_filament_ref: null` explicitly; new unit test: caller carrying a stale ref → tier change emits null.
- **patch (regression guard)** — both reviewers flagged that a controlled `<select value={value.quality_tier}>` with no matching `<option>` (incompatible current tier) silently falls back to the first option, desyncing from `value` — a regression vs the self-defending radiogroup. Edge Case Hunter proved it unreachable via the current `FilesTab` caller, but the operator's rationale is *future* tier growth, so the component is now self-defending: `selectedTier` coerces to the first compatible tier. New unit test: TPU + incompatible `strong` → displays `standard`.
- **patch (dead code)** — removing the `sr-only` reason span orphaned `modules.estimates.selector.reason_*_tooltip`; removed both keys from `en.json` + `pl.json` (no other consumer; no unused-i18n gate exists).
- **reject** — `reasonKey: string | null` in a template literal: only reached on the non-null branch; no issue.

Accepted downgrade (not a fix): the old `aria-describedby` + sr-only tooltip carried a `{material}`-interpolated sentence a native `<option>` cannot host; the reason collapses to short inline option text, which still reaches assistive tech.

## Design Notes

Native `<option>` cannot host an `sr-only` `<span>`, so the unavailable-tier reason that was a visible-suffix + `aria-describedby` tooltip on the button collapses to inline option text (`"{label} · {reason}"`) plus the `disabled` attribute — the same honest copy, conveyed in the only channel a select option supports. `selectTier`'s `isAvailable`/`isTierCompatible` guards stay as defense-in-depth even though a disabled option can't be chosen through the native control.

## Verification

**Commands:**
- `npm run test -- CatalogEstimateProfileSelector` (from `apps/web/`) -- expected: all selector unit tests green.
- `npm run lint --max-warnings=0` + `npm run typecheck` (from `apps/web/`) -- expected: clean.
- `npm run test:visual -- catalog-filestab-estimate` (from `apps/web/`) -- expected: green after baseline regen for the affected states.
- `infra/scripts/check-all.sh` -- expected: full closeout gate green before any controller merge.

**Results (2026-06-05):**
- `npm run test -- CatalogEstimateProfileSelector FilesTab` -- 33 passed.
- `npm run typecheck` + `npm run lint --max-warnings=0` -- exit 0.
- `npm run test:visual` (full suite) -- 412 passed / 24 skipped / 0 failed. Stale baselines regenerated for every spec that captures the catalog-detail Files tab (the selector bar): `catalog-filestab-estimate`, `catalog-detail`, `share-member-enriched`, `share-member-enriched-dismissed`, `viewer3d-mobile`. Diffs verified confined to the selector row + its downward reflow.
- `infra/scripts/check-all.sh` -- closeout log under `.hermes/run-logs/check-all-E33-1-quality-select-final-*.log`.

## Suggested Review Order

**Control swap (the change itself)**

- Native `<select>` for quality replaces the radiogroup; `<option disabled>` carries the inline reason.
  [`CatalogEstimateProfileSelector.tsx:141`](../../apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx#L141)
- Self-defending controlled value — coerces to the first compatible tier so display never desyncs from `value`.
  [`CatalogEstimateProfileSelector.tsx:89`](../../apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx#L89)
- `selectTier` defensively re-nulls `spoolman_filament_ref` (invariant #3).
  [`CatalogEstimateProfileSelector.tsx:114`](../../apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx#L114)

**Tests & assertions**

- Component unit tests: option/select semantics, self-defend case, spool-null case, no radio remains.
  [`CatalogEstimateProfileSelector.test.tsx:45`](../../apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.test.tsx#L45)
- FilesTab integration tests: radio→option/select queries (the file the closeout gate caught).
  [`FilesTab.test.tsx:281`](../../apps/web/src/modules/catalog/components/tabs/FilesTab.test.tsx#L281)
- Visual spec: disabled-tier locator `button[role=radio]` → `option:disabled`.
  [`catalog-filestab-estimate.spec.ts:213`](../../apps/web/tests/visual/catalog-filestab-estimate.spec.ts#L213)

**Cleanup**

- Orphaned tooltip i18n keys removed from both locales.
  [`en.json:660`](../../apps/web/src/locales/en.json#L660)
