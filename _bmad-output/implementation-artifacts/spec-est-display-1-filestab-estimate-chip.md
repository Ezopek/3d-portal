---
title: 'EST-DISPLAY-1 — FilesTab inline STL estimate grams chip + global preset + expanded panel'
type: 'feature'
created: '2026-06-03'
status: 'review'
baseline_commit: '5b10f71'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/ux/stl-estimate-display-catalog-files-ux.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-est-ingest-1-catalog-stl-hash-ingest.md'
  - '{project-root}/_bmad-output/implementation-artifacts/32-6-frontend-print-intent-preset-estimate-display.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** EST-INGEST-1 (merged @ 5b10f71) now slices the catalog's 525 STL parts against
the **default print-intent preset** (`PLA · standard`, printer `creality-k1-max-microswiss-hf`)
and writes real `EstimateRecord`s keyed by `(stl_hash, bundle_hash)`, where `stl_hash ==
ModelFile.sha256` for `kind=stl`. Story 32.6 shipped every display primitive (`EstimateDisplay`,
`PrintIntentPresetSelector`, `useEstimate`, formatters, `modules.estimates.*` copy) but nothing
wires them into the catalog, so a member browsing a model's files still sees no estimate. This is
the UX-doc "Story A" (read/display) — the first place a member sees a slicer estimate in the catalog.

**Approach:** A pure **wiring + presentation** story over already-shipped primitives. Add a
member-visible **global estimate-profile selector** above the FilesTab STL list, an inline
**grams-only chip** on each collapsed STL row (tasteful spool icon + fixed scan column, filename
truncates first), and an **expanded panel** that reuses the shipped `EstimateDisplay` beside the
inline 3D viewer — all bound to the same global preset. Reads are keyed by `ModelFileRead.sha256`
as the `stl_hash`; when `sha256` is missing, no `GET /api/estimates` call fires and the chip shows
an honest no-hash/absent state. Every state renders honestly and mutually-exclusively. Read-only:
no enqueue, no recompute, no admin profile management.

## Boundaries & Constraints

**Always:**
- Reuse the Story 32.6 primitives 1:1: `EstimateDisplay`, `PrintIntentPresetSelector`, `useEstimate`,
  `format.ts` (`formatMass`), `defaultPreset`/`presetKey`, and all shipped `modules.estimates.*` copy.
  New code = the spool icon, the grams chip, a thin global-preset row panel wrapper, the FilesTab
  wiring, and short `modules.estimates.chip.*` aria/title keys.
- Use `ModelFileRead.sha256` as `stl_hash` (EST-INGEST-1 proved the byte-equality). The chip/panel
  re-key on `sha256 + preset + printerRef` exactly like 32.6's `useEstimate`.
- The catalog printer identity MUST equal the EST-INGEST-1 ingest default
  (`slicer_default_printer_ref = "creality-k1-max-microswiss-hf"`) — otherwise the chip reads a
  bundle that was never sliced and is permanently `absent`. Encode this as a named FE contract
  constant (`CATALOG_ESTIMATE_PRINTER_REF`) with a comment pointing at the backend setting.
- Default preset = `defaultPreset()` (`PLA · standard · no pin`), matching the EST-INGEST-1 default
  bundle so the first-load chip shows real numbers, not `absent`.
- Member-visible: the preset bar + chip are NOT gated on `isAdmin`. Any logged-in viewer re-keys
  the estimates they see.
- Honest, mutually-exclusive chip states: `no-hash / loading / absent / fresh / stale / queued /
  failed / network-error`. Grams-only in the chip; never silent-zero (em-dash via `formatMass`).
- Chip is a non-interactive `<span>`; spool SVG `aria-hidden`; accessible `title`/`aria-label`
  conveys state. `tabular-nums` grams. State signalled by more than color (glyph + text).
- Tailwind/theme tokens only — zero inline hex. i18n parity (en+pl) for every new string.

**Ask First:**
- Preset persistence beyond ephemeral component state (sessionStorage / per-user / per-model).
- Per-part (non-global) preset, time-in-chip, or cost-in-chip — all UX Open Questions (Q3/Q7/Q9),
  defaulted here to grams-only / global / panel-only-cost.

**Never:**
- No enqueue / no recompute affordance / no `POST /api/estimates/recompute` (EST-RECOMPUTE-1 deferred).
- No admin profile/filament management (separate Admin Panel initiative).
- No raw `fetch` — use the existing `api()`/`useEstimate` path.
- No change to the admin `selected_for_render` checkbox or the **Re-render preview** button (a
  different snapshot-render pipeline) — they stay visually + semantically separate.
- No backend/API/DTO change; no new estimate logic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected chip | Expanded panel |
|----------|--------------|---------------|----------------|
| No hash | STL `sha256 === ""` | spool + em-dash, muted; title `chip.no_hash`; **no** request fired | (panel also shows no-hash absent, no request) |
| Loading | hash present, query pending+fetching | skeleton shimmer, `aria-busy` | `EstimateDisplay` spinner |
| Absent | `status==="absent"` (store miss) | spool + em-dash, muted; title `chip.absent` | `EstimateDisplay` absent EmptyState |
| Fresh | `status==="fresh"` | spool + `formatMass(g)`, normal `tabular-nums`; title `chip.fresh` | full `<dl>`, no banner |
| Stale | `status==="stale"` | grams + amber accent + dot glyph; title `chip.stale` | amber stale banner + last-estimated |
| Queued | `status==="queued"` | last-known grams (or em-dash) + spinner; title `chip.queued` | queued banner + last-known numbers |
| Failed | `status==="failed"` | em-dash + alert glyph, destructive; title `chip.failed` | failed title + `failure.{reason}` |
| Network error | query `isError` | em-dash + alert glyph, quiet destructive; title `chip.error` | retryable error EmptyState |
| Non-STL kind | source/3mf row | no chip, no preset bar | n/a (no expand) |

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/estimates/lib/preset.ts` — add `CATALOG_ESTIMATE_PRINTER_REF` contract
  constant (= backend `slicer_default_printer_ref`), with comment.
- [x] `apps/web/src/locales/en.json` + `pl.json` — add `modules.estimates.chip.*` keys (parity).
- [x] `apps/web/src/modules/estimates/components/SpoolIcon.tsx` — inline 24×24 `currentColor` spool SVG.
- [x] `apps/web/src/modules/estimates/components/EstimateChip.tsx` — grams-only collapsed chip; uses
  `useEstimate`; renders the full state matrix honestly.
- [x] `apps/web/src/modules/estimates/components/RowEstimatePanel.tsx` — thin wrapper binding the
  global preset to `EstimateDisplay` via `useEstimate` (shared query key ⇒ no double fetch).
- [x] `apps/web/src/modules/catalog/components/tabs/FilesTab.tsx` — global preset bar (member-visible,
  STL tab only, list non-empty), per-row chip keyed by `f.sha256`, expanded panel beside `Viewer3DInline`.
- [x] Tests: `EstimateChip.test.tsx`, extend `FilesTab.test.tsx`, focused visual spec.

**Acceptance Criteria:**
- AC-1: A member (non-admin) sees the global estimate-profile selector above the STL list when the
  STL tab is active and has ≥1 STL; it is absent for the Source/3MF tabs.
- AC-2: Each collapsed STL row shows a grams-only chip; `GET /api/estimates` is called with
  `stl_hash = f.sha256`, the selected preset, and `printer_ref = CATALOG_ESTIMATE_PRINTER_REF`.
- AC-3: A `fresh` response renders the grams value (`formatMass`) in the chip; the expanded row
  renders the shipped `EstimateDisplay` with the full breakdown, bound to the same preset.
- AC-4: When `f.sha256 === ""`, NO estimate request fires and the chip shows the honest no-hash state.
- AC-5: `absent / failed / network-error` render mutually-exclusively as em-dash + the correct
  glyph/title; the chip never shows `0 g`.
- AC-6: Changing the global preset re-keys every visible chip's query (new `presetKey`).
- AC-7: The admin `selected_for_render` checkbox and **Re-render preview** button are unchanged and
  visually separate; there is NO recompute/enqueue affordance anywhere on the estimate surface.
- AC-8: en/pl key parity holds; no estimate string promises automatic live propagation (i18n-honesty).

## Design Notes

**Printer-ref contract (load-bearing).** EST-INGEST-1 slices against
`slicer_default_printer_ref = "creality-k1-max-microswiss-hf"` (config.py:185). The standalone
`/estimates` demo route uses `DEFAULT_PRINTER_REF = "p1s"` — a placeholder, NOT the ingest identity.
The catalog chip MUST use the ingest identity or every read is `absent`. `CATALOG_ESTIMATE_PRINTER_REF`
in `preset.ts` is that contract, marked arbitrary-until-multi-printer (replace when a printer registry
/ per-model printer selection lands), mirroring the backend magic-constant note.

**Shared query key, no double fetch.** Both `EstimateChip` and `RowEstimatePanel` call `useEstimate`
with the same `(stlHash, preset, printerRef)` ⇒ identical TanStack queryKey ⇒ the expanded panel
reuses the chip's cached read; only one network request per `(hash, preset)`.

**Preset scope = ephemeral global (UX Q1 default).** One `useState(defaultPreset)` in FilesTab feeds
the bar, every chip, and the expanded panel. No persistence in v1 (resets on navigate) — the smallest
honest unit per the UX recommendation.

**Selector reuse vs. compact projection.** v1 reuses `PrintIntentPresetSelector` verbatim (reuse-first;
fully tested). The UX §A compact horizontal projection + mobile summary-sheet is deferred polish — it
does not change the read contract and is not load-bearing for "grams visible inline".

## Verification

**Commands / closeout evidence:**
- `git diff --check` and `git diff --cached --check` — clean.
- `npm run test -- FilesTab EstimateChip` — 2 files / 28 tests passed.
- `npm run lint -- --max-warnings=0` — clean (pre-existing React-version warning only).
- `npm run typecheck` — clean.
- `infra/scripts/check-all.sh` — 16/16 stages green, including web production build, web vitest, api/worker/infra pytest, web visual regression `404 passed / 24 skipped`, settings/env/compose diff, uv lock checks, and local-env-secrets.

**Visual baseline result.** Controller regenerated/reviewed the affected catalog-detail/share/viewer
baselines plus the new focused `catalog-filestab-estimate` four-state matrix; the final aggregate
visual regression passed (`404 passed / 24 skipped`).

## Correction — STL-preset-compact (post-done product correction)

> bmad-quick-dev, 2026-06-04, branch `fix/STL-preset-compact` (off `main`). Author-of-record record
> only; controller (Laura/ITCM) owns review + commit/merge/deploy. Status row NOT flipped here.

**Product signal.** The Catalog detail → Files → STL tab is an orientational per-STL **gram-estimate
preview** surface — NOT print ordering and NOT spool availability. The shipped v1 reused
`PrintIntentPresetSelector` verbatim (see *Design Notes → Selector reuse vs. compact projection*),
which exposed three full-width labelled controls (Material, Quality, Pinned filament) in a `<fieldset>`
panel above the list. Material class and the Spoolman pin are unnecessary — and misleading (they imply
ordering/spool semantics) — on this surface. The only high-leverage choice here is the print
process/quality profile.

**Change.**
- New `apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx` — a compact,
  right-aligned, inline `quality_tier`-only selector, visually subordinate to the STL list.
- `FilesTab.tsx` now renders `CatalogEstimateProfileSelector` instead of `PrintIntentPresetSelector`
  on the STL surface. `material_class` (PLA) and `spoolman_filament_ref` (null) stay as the
  **internal preset defaults** carried in the same `PrintIntentPresetInput` state ⇒ the estimate
  query keys (`sha256 + preset + printerRef`) and the chip/panel re-render behaviour are **unchanged**
  except for the tier the member actually picks (AC-2/AC-6 preserved).
- `PrintIntentPresetSelector` and the standalone `/estimates` surface (`EstimatesPanel`) are
  **untouched** — material/pin selection still lives there.
- i18n: new `modules.estimates.selector.profile_label` key (en `Estimate profile` / pl `Profil wyceny`).

**Scope guard.** No backend/API/DTO change; no enqueue/recompute; no ordering or spool-availability
semantics added to this surface. The expanded `RowEstimatePanel` (read-only provenance: "computed
against PLA · Standard") is intentionally retained — it reports what the estimate reflects, it is not
an input control.

**Verification (authoring env).**
- `npx vitest run` (from `apps/web`) — `src/modules/estimates` + `src/modules/catalog/components/tabs`:
  14 files / 128 tests passed, incl. new `CatalogEstimateProfileSelector.test.tsx` (5) and the extended
  `FilesTab.test.tsx` (21: material/pin-absent + profile re-key assertions).
- `npm run typecheck` — clean. `npm run lint -- --max-warnings=0` — clean (pre-existing React-version
  warning only).
- `npm run test:visual -- catalog-filestab-estimate --update-snapshots` — 16 baselines (4 states ×
  4 projects) regenerated + reran green; delta inspected (fresh + expanded, desktop-light): compact
  `Profil wyceny` selector replaces the fieldset panel, grams chip + full expanded `EstimateDisplay`
  intact. Controller owns final aggregate `check-all.sh` visual sign-off.

## Decision — process-profile availability gating (product decision, no code here)

> Operator/controller product decision, 2026-06-04. **Decision record only** — no application code,
> no profile vendoring, no backfill changed by this note. Implementation is parked as EST-TIERS-1 in
> `deferred-work.md` and is a follow-up quick-dev story. Status row NOT flipped.

**Context.** The compact `CatalogEstimateProfileSelector` (above) exposes the full
`QUALITY_TIERS = ["aesthetic", "standard", "strong"]` set (`preset.ts`), but for the catalog
printer/material identity (`creality-k1-max-microswiss-hf` · PLA) only `standard.json` is vendored on
`.190` (`…/vendored/intents/creality-k1-max-microswiss-hf/PLA/`). Controller live resolver smoke:
`standard` resolves (`bundle_hash=25b03be589a4…`); `aesthetic` + `strong` raise `PresetResolveError`
(reason `unsupported_material_class`), which `router.py:131-136` surfaces as **HTTP 422**
`"preset not resolvable"` on `GET /api/estimates`. So a member picking Aesthetic or Strong on this
member-visible surface currently hits a user-facing 422. (Contrast: a *resolvable* profile with no
stored estimate is HTTP 200 `status="absent"` per `estimate_read.py:164-178` — that honest absent
state is fine and unaffected; only the unresolvable-profile 422 is the failing path.)

**Decision.**
- Do **not** fake/vendor placeholder Orca intents for the missing tiers, and do **not** leave
  selectable options that 422.
- The selector must offer **only resolvable process profiles** for the active printer/material, **or**
  render unavailable ones **disabled** with short honest copy (e.g. "profile not imported yet") when
  visibility is useful. No 422 / no error toast / no error path from this surface.
- Availability is **not** hardcoded in the FE: add/adjust the backend contract so the FE derives
  resolvable tiers per `(printer_ref, material_class)` rather than baking in the `standard`-only
  assumption (the static `QUALITY_TIERS` map is the hardcode to retire).
- **Bridge** until the admin profile-management panel exists (which makes the missing profiles
  importable, removing the gate).
- Implementation is a **visible UI change** ⇒ must clear the mockup/render mini-gate + `test:visual`
  baseline pass when built.

**Where it lives.** Parked as `EST-TIERS-1` in `deferred-work.md` (full evidence, fix sketch, promote
trigger). This section is the surface-local anchor on the spec the selector was last corrected under.
