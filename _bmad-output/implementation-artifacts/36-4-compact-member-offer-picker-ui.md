# Story 36.4: Compact member offer picker UI

Status: done

<!--
  Follow-up to Story 36.3. Operator correction 2026-06-14:
  The 36.3 large radio/card offer picker is visually too loud for a member-facing surface.
  Replace with a compact inline select control integrated into the existing estimate profile bar.
-->

## Story

As an **authenticated portal member**,
I want **to see the print profile offer selector as a subtle inline control alongside the existing
material and quality selects**,
so that **the estimate bar does not distract me when offers are irrelevant, and I can still choose
an offer without switching UX paradigms**.

## Acceptance Criteria

### Compact layout

- **AC-1** The offer selector renders as a compact label + `<select>` control, visually matching
  the existing Material and Quality selects in `CatalogEstimateProfileSelector`.
- **AC-2** The offer select is appended as a third item inside the same flex row as Material and
  Quality — one unified estimate profile bar, not two stacked rows.
- **AC-3** When no compatible offers are available (empty list), the offer select is absent; the
  estimate profile bar shows only Material and Quality.
- **AC-4** The offer select label reads "Profile" (EN) / "Profil" (PL) — a neutral label that
  does not imply admin or ordering semantics.

### Option content

- **AC-5** First option is always "Standard estimate" (EN) / "Szacowanie standardowe" (PL) with
  `value=""` — selecting it returns `null` (preset mode).
- **AC-6** Each published offer appears as an `<option>` whose text is `offer.portal_label` only.
  `printer_name` is **not** shown in any option text, aria label, or tooltip.
- **AC-7** Selecting an offer option calls `onSelect(offer.offer_id)`.

### Behavior and error handling

- **AC-8** Loading state: offer select absent (silent fail-open); existing preset flow unaffected.
- **AC-9** Transport error: compact inline error text + Retry button; existing preset flow
  unaffected (same fail-open guarantee as 36.3).
- **AC-10** When no offer is selected (`selectedOfferId === null`), estimate flow uses existing
  preset path unchanged.
- **AC-11** When an offer is selected, each STL row `EstimateChip` and expanded `RowEstimatePanel`
  use the `offer_id` path as per 36.3 — no behavior change from 36.3 in offer mode.
- **AC-12** `isAuthenticated=false` → component renders null (AuthGate discipline preserved).
- **AC-13** Deselect-on-disappearance from 36.3 is preserved (offer removed from list → clears
  selection).

### Scope boundaries

- **AC-14** Do **not** display `printer_name` in member UI under any circumstance.
- **AC-15** G-ENQUEUE remains out of scope (no request-estimate CTA, no on-demand slicing).
- **AC-16** Existing `CatalogEstimateProfileSelector` material/quality behavior is unchanged.
- **AC-17** No multilingual offer descriptions (deferred — future story when DTO supports it).

### i18n, a11y, testing

- **AC-18** PL/EN parity: all new i18n keys exist in both locale files.
- **AC-19** New key: `modules.member.offers.picker.select_label` for the compact label.
- **AC-20** Tests updated: verify no `printer_name` in rendered output; verify standard-estimate
  fallback option exists; verify onSelect called with offer_id; verify error/fail-open preserved;
  verify i18n key parity.
- **AC-21** No inline hex/theme-token violations (Tailwind CSS variable classes only).

## Tasks / Subtasks

1. [x] **(RED)** Update `PublishedOfferPicker.test.tsx` — add `printer_name not shown` test,
       update select-based assertions, update i18n parity list.
2. [x] **(GREEN)** Add `children?: ReactNode` slot to `CatalogEstimateProfileSelector` so the
       offer select can live in the same flex row.
3. [x] **(GREEN)** Refactor `PublishedOfferPicker` from fieldset/radiogroup cards to a compact
       label + `<select>` control (bare flex item, no outer wrapper).
4. [x] **(GREEN)** Wire `PublishedOfferPicker` as a child slot of `CatalogEstimateProfileSelector`
       in `FilesTab` — remove the current separate render block.
5. [x] **(GREEN)** Add `modules.member.offers.picker.select_label` to `en.json` and `pl.json`.
6. [x] **(VERIFY)** Run targeted Vitest tests + web typecheck + lint; record evidence.

## Dev Notes

- Do NOT delete `CatalogEstimateProfileSelector` material/quality controls — only extend with a
  child slot.
- `printer_name` may remain in `MemberPublishedOfferView` DTO / API — only hide it in member UI.
- Deferred: offer descriptions in `portal_label` could become multilingual once DTO supports it;
  leave a `# FUTURE` comment near the option text render.
- 36.3 `usePublishedOffers` and `useOfferEstimate` hooks remain unchanged.
- 36.3 `EstimateChip` and `RowEstimatePanel` offer-mode paths remain unchanged.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 via repo-local Claude Code; Laura/Hermes controller.

### Completion Notes List

- 2026-06-14 — Implemented on branch `feat/E36.4-compact-member-offer-picker-ui`.
- RED evidence: targeted Vitest on updated `PublishedOfferPicker.test.tsx` → 7 failed / 4 passed
  (combobox-based assertions failed because old fieldset/radio markup was still in place; i18n test
  failed because `select_label` key was missing).
- GREEN evidence: targeted run → **11/11 passed**.
- Web gate evidence: `npm run typecheck` passed; `npm run lint -- --max-warnings=0` passed;
  `npm run test -- --run` passed **126 files / 657 tests**.
- Scope held: no backend changes, no G-ENQUEUE, no printer_name in member UI, no admin-only controls exposed.
- **Close-out gate** (`infra/scripts/check-all.sh`, 2026-06-14, log `check-all-20260614_013620-E36.4.log`):
  passed: 16 / 16 — all green. Vitest 126 files / 657 tests passed. Visual regression: 472 passed /
  24 skipped — no baseline regen needed.
- **External Aider review** (log `aider-review-20260614_014530-E36.4.log`): **APPROVE**.

### File List

- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.tsx`
- `apps/web/src/modules/estimates/components/PublishedOfferPicker.test.tsx`
- `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx`

## Change Log

- 2026-06-14 — Story created from operator correction after 36.3 delivery.
