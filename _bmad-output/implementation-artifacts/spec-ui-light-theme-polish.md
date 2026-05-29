---
title: 'Light-theme polish — popover tokens, sheet bg, i18n for Add print/Add note'
type: 'bugfix'
created: '2026-05-11'
status: 'done'
baseline_commit: 'c09dec5'
final_commit: 'c35b5dc'
review:
  reviewer: 'codex'
  verdict: 'APPROVE'
  findings: 0
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Three light-theme UI defects spotted in screenshot review on `/catalog`: (1) `<Select>` dropdown panels render with browser fallback (dark) in both modes because `bg-popover` / `text-popover-foreground` referenced in `apps/web/src/ui/select.tsx` map to CSS tokens never defined in `theme.css`; (2) `<SheetContent>` panel background is hardcoded `bg-[rgba(8,12,20,0.5)]` ignoring theme, causing an ugly dark wash behind white `CategoryTreeSidebar` items in light mode; (3) `AddPrintSheet` and `AddNoteSheet` are entirely untranslated (no `useTranslation()`), and the Kind dropdown shows raw enum values `operational` / `ai_review` / `other`.

**Approach:** Add the two missing `--color-popover[-foreground]` tokens to both `@theme` and `.dark` blocks; swap the hardcoded sheet panel bg to themed `bg-background/90` (overlay scrim stays as-is); wire `useTranslation()` into both sheets with new `catalog.prints.*` / `catalog.notes.*` / `catalog.notes.kinds.*` keys plus a new `common.save` (`common.cancel` already exists, reuse). DB enum values stay literal — only UI labels translated.

## Boundaries & Constraints

**Always:**
- All user-visible strings via `t("…")`; new colors as CSS tokens in `theme.css` referenced via Tailwind classes (no inline hex/rgba in `.tsx`).
- `en.json` and `pl.json` key sets stay in sync.
- ESLint `--max-warnings=0`, TypeScript strict + `noUncheckedIndexedAccess`.
- Visual regression on all 4 projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`); snapshots updated only after intentional diff review.
- Auto-deploy to `.190` after ff-merge to `main` per memory.

**Ask First:**
- Any visual-regression diff touching surfaces other than dropdowns / sheets / Add modals.

**Never:**
- Touch `SheetOverlay` scrim, `CategoryTreeSidebar`, `FilterRibbon`, `EditTagsSheet`, `EditDescriptionSheet`, `RenderSheet`.
- Translate the `kind` enum in DB / API payload — backend contract stays literal.
- Add CSS tokens beyond `--color-popover[-foreground]`.
- Rename existing locale keys.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error |
|----------|---------------|----------------------------|-------|
| Status dropdown | Click on `/catalog`, theme=light | Panel white bg, dark text | N/A |
| Status dropdown | Theme=dark | Panel dark card-tone bg, light text (no regression) | N/A |
| AddPrintSheet PL create | `print=null`, lang=pl | Header `Dodaj wydruk`; labels `Data` / `Notatka`; buttons `Anuluj` / `Zapisz`; toast `Wydruk dodany` | onError stays `e.message` |
| AddPrintSheet PL edit | existing `print`, lang=pl | Header `Edytuj wydruk`; toast `Wydruk zaktualizowany` | Same |
| AddNoteSheet PL | lang=pl, opens Kind | Labels `Rodzaj` / `Treść`; options `Operacyjna` / `Recenzja AI` / `Inne`; POST/PATCH body still carries literal `operational` / `ai_review` / `other` | Same |
| AddNoteSheet edit `description`-kind note | existing `kind=description` | Kind dropdown defaults to `Operacyjna` label, submits `operational` (behavior preserved) | Same |
| Mobile drawers light | mobile width, theme=light, open `Kategorie` or `Filtry` | Sheet panel themed-light (`bg-background/90`), no dark wash | N/A |
| Mobile drawers dark | theme=dark | Panel dark-themed; no regression | N/A |
| Locale EN | switch to EN, open either sheet | All strings render EN equivalents | N/A |

</frozen-after-approval>

## Code Map

- `apps/web/src/styles/theme.css` — add `--color-popover` + `--color-popover-foreground` to `@theme {}` (light) and `.dark {}` blocks.
- `apps/web/src/ui/sheet.tsx:54` — swap `bg-[rgba(8,12,20,0.5)]` → `bg-background/90` in `SheetContent`. Line 29 (`SheetOverlay`) untouched.
- `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx` — add `useTranslation()`; replace inline strings and 4 toast strings.
- `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx` — same; render `<SelectItem>` label via `t(\`catalog.notes.kinds.${k}\`)`; preserve `description → operational` fallback.
- `apps/web/src/locales/en.json` — add 16 keys: `catalog.prints.{add,edit,date,note,added,updated}`, `catalog.notes.{add,edit,kind,body,added,updated}`, `catalog.notes.kinds.{operational,ai_review,other}`, `common.save`. Reuse `common.cancel`.
- `apps/web/src/locales/pl.json` — mirror with Sally's PL translations.
- `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.test.tsx` + `AddNoteSheet.test.tsx` — add `import "@/locales/i18n";` so `getByRole({ name: /^save$/i })` matches translated EN `"Save"`.

Side-effect snapshot churn: `EditTagsSheet`, `EditDescriptionSheet`, `RenderSheet`, `FilterRibbon`, `CatalogList` mobile drawers (all consume `<SheetContent>`). Expected: identical perception in dark, clearly better in light.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/styles/theme.css` — light: `--color-popover: hsl(0 0% 100%)`, `--color-popover-foreground: hsl(222 47% 11%)`; dark: `--color-popover: hsl(222 47% 11%)`, `--color-popover-foreground: hsl(210 40% 98%)`.
- [x] `apps/web/src/ui/sheet.tsx` — `SheetContent` className: `bg-[rgba(8,12,20,0.5)]` → `bg-background/90`.
- [x] `apps/web/src/locales/en.json` + `pl.json` — add the 16 keys per Sally's table.
- [x] `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx` — wire `useTranslation`; replace all hardcoded strings + toasts.
- [x] `apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx` — same; `<SelectItem>` text via `t(\`catalog.notes.kinds.${k}\`)`; keep `description → operational` mapping intact.
- [x] `apps/web/src/modules/catalog/components/sheets/AddPrintSheet.test.tsx` + `AddNoteSheet.test.tsx` — add `import "@/locales/i18n";`.
- [~] Run `npm run test:visual` (4 projects); inspect diffs; `--update-snapshots` only after visual review. **DEFERRED — see Spec Change Log entry 2026-05-11-A. Visual regression baseline broken by pre-existing rot (~66 failures on bare `c09dec5` before this story's changes; verified via stash-and-rerun). Filed as TB-009. Manual smoke on `.190` substitutes for this story's UI contract.**

**Acceptance Criteria:**
- Given light theme, when any `<Select>` dropdown opens, then the panel renders white background + dark text; dark theme remains unchanged.
- Given PL locale, `AddPrintSheet` shows `Dodaj wydruk` / `Edytuj wydruk` headers, PL labels, PL buttons; success toasts in PL.
- Given PL locale, `AddNoteSheet` Kind dropdown shows `Operacyjna` / `Recenzja AI` / `Inne`, but POST/PATCH payload still carries literal enum values (`operational` / `ai_review` / `other`).
- Given any locale, editing a `description`-kind note defaults to `Operacyjna` label and submits `operational` (behavior preserved).
- Given EN locale, both sheets render EN strings.
- Given mobile + light theme, both drawers (`Kategorie` / `Filtry`) show a themed-light sheet panel; dark theme unchanged.
- `npm run lint` (apps/web) — 0 warnings; `npx tsc --noEmit` — clean; `npm run test` — green incl. the 6 sheet tests; `npm run test:visual` — green on all 4 projects after intentional snapshot update.

## Spec Change Log

### 2026-05-11-A — Visual regression deferred to TB-009

**Trigger:** During implementation step-03 verification, `npm run test:visual` produced 66 failures / 24 passes / 14 skips across 4 projects on the branch HEAD. Stash-and-rerun on bare baseline `c09dec5` reproduced identical failures, confirming pre-existing breakage unrelated to this story.

**Failure categories (from sub-agent diagnostic):**
1. ~30 viewer3d test-logic timeouts on `getByRole("tab", { name: /^files\b/i })` — `viewer3d-modal-*`, `viewer3d-measure-*`, `viewer3d-inline-loaded`, `viewer3d-mobile`.
2. 8 sessions.spec.ts timeouts on `text=Active sessions`.
3. ~28 catalog/dev/empty-states snapshot pixel drifts — observed evidence: `"no preview"` (EN, in expected baseline) vs `"brak podglądu"` (PL, currently rendered) → locale/state drift between baseline capture and current render.

**Why this story can't repair it:** The fix touches `<Select>` popover panel + `<SheetContent>` panel — both visible only when open. No existing visual spec opens either surface in steady state (grepped `apps/web/tests/visual/*.spec.ts`). Even with a clean baseline, the suite would not exercise this fix.

**Amendment:** Visual regression step marked `[~]` deferred. Filed as TB-009 for separate triage (forensic agent investigating which commits introduced each category; results inform TB-009 spec).

**KEEP:** Manual smoke on `.190` (browser dropdown + sheet open in light + dark + PL/EN) substitutes for visual regression for this story specifically. The substitution decision is one-off and scoped to this story — the project-wide rule "visual regression mandatory for UI change" remains in effect for future stories.

## Design Notes

**Why `bg-background/90` for `SheetContent`:** `--color-background` and `--color-card` are near-identical in this theme; `background` is the semantically correct "page surface" for a fullscreen-ish sheet. No new token needed for one consumer.

**Why introduce `--color-popover` instead of swapping `select.tsx` to `bg-card`:** Token approach is canonical (shadcn convention; surfaces other selects in the same fix without per-component churn). Light uses card-white; dark uses card-elevated equivalent.

**i18n init in tests:** Without `import "@/locales/i18n";`, `t("common.save")` returns the literal key — `/^save$/i` regex won't match. Pattern established in `apps/web/src/ui/custom/ModelCard.test.tsx:9`.

## Verification

**Commands:**
- `cd apps/web && npm run lint` — 0 warnings.
- `cd apps/web && npx tsc --noEmit` — 0 errors.
- `cd apps/web && npm run test` — green (incl. 3 AddPrintSheet + 3 AddNoteSheet tests).
- `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` — all 4 projects pass after intentional snapshot update.
- `bash infra/scripts/deploy.sh` (repo root) — auto-deploy to `.190` post ff-merge.

**Manual checks on `.190`:**
- `/catalog`, toggle light/dark → status dropdown re-themes correctly.
- PL locale → `Dodaj wydruk` modal labels in PL; EN locale → EN equivalents.
- `Dodaj notatkę` Kind dropdown shows PL labels; network tab confirms literal enum in payload.
- Mobile (~390×844), light theme → both drawers show light-themed sheet panel.

## Suggested Review Order

**Theme tokens — the foundation that unlocks dropdown theming**

- New light-theme popover tokens; chose card-white + card-foreground to match shadcn convention.
  [`theme.css:12-13`](../../apps/web/src/styles/theme.css#L12-L13)

- Mirror in `.dark` — same card/foreground pairing in dark palette.
  [`theme.css:44-45`](../../apps/web/src/styles/theme.css#L44-L45)

**Sheet panel — the visible light-mode fix**

- Single class swap from hardcoded dark `rgba` to themed `bg-background/90`. Overlay scrim line 29 untouched (intentional).
  [`sheet.tsx:54`](../../apps/web/src/ui/sheet.tsx#L54)

**AddNoteSheet — the trickier of the two i18n wirings**

- Dynamic kind label via template-literal i18n key; `value={k}` stays literal so API payload contract is preserved.
  [`AddNoteSheet.tsx:82`](../../apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx#L82)

- `useState` initializer preserves the `description → operational` legacy-kind fallback (regression risk).
  [`AddNoteSheet.tsx:22`](../../apps/web/src/modules/catalog/components/sheets/AddNoteSheet.tsx#L22)

**AddPrintSheet — straightforward i18n wiring (mirrors the Note pattern minus the kind dropdown)**

- Header conditional uses two distinct keys for create vs edit.
  [`AddPrintSheet.tsx:66`](../../apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx#L66)

- Toast strings translated alongside form copy.
  [`AddPrintSheet.tsx:43`](../../apps/web/src/modules/catalog/components/sheets/AddPrintSheet.tsx#L43)

**Locale resources**

- Kind enum labels (`Operacyjna` / `Recenzja AI` / `Inne`) — Sally's verbatim translations.
  [`pl.json:125-127`](../../apps/web/src/locales/pl.json#L125-L127)

- EN counterparts plus the rest of the new key set; key parity with `pl.json` verified.
  [`en.json:113`](../../apps/web/src/locales/en.json#L113)

**Test i18n init (peripheral)**

- One-line import initializes i18next so `/^save$/i` matches translated `"Save"`. Pattern from `ModelCard.test.tsx:9`.
  [`AddPrintSheet.test.tsx:7`](../../apps/web/src/modules/catalog/components/sheets/AddPrintSheet.test.tsx#L7)

- Same for AddNoteSheet test.
  [`AddNoteSheet.test.tsx:7`](../../apps/web/src/modules/catalog/components/sheets/AddNoteSheet.test.tsx#L7)
