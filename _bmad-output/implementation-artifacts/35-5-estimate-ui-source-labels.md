---
baseline_commit: 7e7644105d49ad1a5dd621b6c1226db70e0bda40
---

# Story 35.5: Estimate UI source labels

Status: done

<!--
  Authored by the repo-local BMAD author (Laura/Hermes delegated). Source planning artifacts:
  epics.md § Initiative 23 (Epic E35 + Story 35.5); architecture.md § Initiative 23 Decision AS;
  SCP sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md § Task 7.

  GATE NOTE — G-UXGATE: a bmad-ux checkpoint is REQUIRED before/with FE work (35.4 + 35.5).
  All tasks in this story are [G-UXGATE]-gated. The backend API that surfaces
  `profile_selection_context` was shipped in 35.3 — this story is FE-only and requires the
  operator to confirm the bmad-ux output before implementation proceeds.
-->

## Story

As a **user viewing a print estimate**,
I want **to see a clear indicator of whether the estimate used an exact filament profile match,
a generic material default, or no profile at all (unavailable)**,
so that **I am never misled into thinking a default-fallback estimate is as precise as an
exact filament mapping, and I always know when no estimate can be computed without it
blocking my order or request path (FR23-UI-LABEL-1, NFR23-HONESTY-1, NFR23-NO-BLOCK-1).**

This is the **user-facing estimate UI source labels slice** of Epic E35 (SCP Task 7). It
consumes the `profile_selection_context` field on `EstimateView` that was shipped in Story 35.3
— it does **not** re-implement policy precedence, resolver/bundle logic, or backend APIs.

## Acceptance Criteria

### api-types.ts — frontend DTO mirroring

- [ ] **AC-1** `apps/web/src/lib/api-types.ts` gains:
  - `EstimateProfileSource` union type: `"exact_filament_mapping" | "default_material_profile" | "unavailable_no_profile"`
  - `ProfileSelectionContextView` interface (mirrors `slicer/schemas.py`):
    ```ts
    export interface ProfileSelectionContextView {
      estimate_profile_source: EstimateProfileSource;
      selected_material: string | null;
      selected_spoolman_filament_ref: string | null;
      selected_filament_name: string | null;
      orca_filament_profile_name: string | null;
    }
    ```
  - `EstimateView.profile_selection_context: ProfileSelectionContextView | null` (additive optional field, `null` when no `spoolman_filament_ref` was passed — backward-compatible with existing tests).

### ProfileSourceBadge component

- [ ] **AC-2** A new `apps/web/src/modules/estimates/components/ProfileSourceBadge.tsx` component
  accepts `context: ProfileSelectionContextView` and renders one of three states:
  - `exact_filament_mapping`: a subtle positive badge (e.g. `variant="outline"`) with label
    `t("modules.estimates.profile_source.exact")`. No material name shown — Orca profile name
    is **admin-scoped** and MUST NOT appear in the user-facing badge.
  - `default_material_profile`: a muted/secondary badge with label
    `t("modules.estimates.profile_source.default", { material: context.selected_material })`.
    Renders the material name (normalized to uppercase by the backend, e.g. "PLA"). Example:
    "Domyślny profil PLA" (PL) / "Default PLA profile" (EN).
  - `unavailable_no_profile`: NOT rendered by this component — the absent state already
    signals unavailability (see AC-4 / AC-5). This branch is a safety no-op.
- [ ] **AC-3** `ProfileSourceBadge.tsx` has a collocated `ProfileSourceBadge.test.tsx`
  (Vitest + Testing Library, `afterEach(cleanup)` mandatory). Tests cover: exact renders
  badge text; default renders material name in label; null context renders nothing (safety);
  `unavailable_no_profile` renders nothing.

### EstimateDisplay integration

- [ ] **AC-4** In `EstimateDisplay.tsx`, the **absent** state branch is extended to distinguish
  two sub-cases based on `data.profile_selection_context?.estimate_profile_source`:
  - `"unavailable_no_profile"`: render `messageKey="modules.estimates.states.absent.no_profile"`
    ("No filament profile configured for this material — estimate unavailable") instead of the
    generic absent message. Keep the `OverrideContextPanel` + optional recompute affordance as
    before; the order/request path is NOT blocked (NFR23-NO-BLOCK-1).
  - All other absent cases (null context or any other source): current behavior unchanged.
- [ ] **AC-5** For `fresh` / `stale` / `queued` / `failed` states where
  `data.profile_selection_context !== null`:
  - Render `<ProfileSourceBadge context={data.profile_selection_context} />` just BELOW the
    `<OverrideContextPanel>` section (not inside it — separate visual row).
  - For `exact_filament_mapping` and `default_material_profile` the badge is always shown.
  - `orca_filament_profile_name` is NEVER rendered in the user-facing UI (admin/debug-scoped).
- [ ] **AC-6** When `data.profile_selection_context === null` (no filament pin, legacy path),
  `EstimateDisplay` renders identically to today — no badge, no empty placeholder.
  **Regression: all existing `EstimateDisplay.test.tsx` assertions still pass without modification.**

### EstimateChip integration

- [ ] **AC-7** In `EstimateChip.tsx`, the **absent** state renders an additional aria-label
  hint when `data.profile_selection_context?.estimate_profile_source === "unavailable_no_profile"`:
  use `t("modules.estimates.chip.absent_no_profile")` instead of `t("modules.estimates.chip.absent")`.
  Visual/icon treatment is unchanged (still `EM_DASH` + muted spool icon) — only the
  tooltip/aria-label differs so screen readers convey the reason.
- [ ] **AC-8** For `fresh`/`stale`/`queued` states with `profile_selection_context` present,
  `EstimateChip` appends a subtle badge indicator ONLY for `default_material_profile`:
  a small `(~)` or text suffix in the chip's `title`/`aria-label` via
  `t("modules.estimates.chip.fresh_default", { mass })` etc. (exact/absent/queued/stale variants
  each get a `_default` sibling key). For `exact_filament_mapping` no extra chip indicator is
  needed — it is the confident/expected path. Keep the chip NON-INTERACTIVE.

### i18n

- [ ] **AC-9** `apps/web/src/locales/en.json` gains (under the `modules.estimates` namespace):
  ```json
  "modules.estimates.profile_source.exact": "Exact filament profile",
  "modules.estimates.profile_source.default": "Default {{material}} profile",
  "modules.estimates.states.absent.no_profile": "No filament profile configured for this material — estimate unavailable.",
  "modules.estimates.chip.absent_no_profile": "No filament profile — estimate unavailable.",
  "modules.estimates.chip.fresh_default": "Estimated filament {{mass}} (default profile).",
  "modules.estimates.chip.stale_default": "Estimated filament {{mass}} — may be out of date (default profile).",
  "modules.estimates.chip.queued_default": "Estimated filament {{mass}} — recomputing… (default profile).",
  "modules.estimates.chip.queued_no_value_default": "Recomputing estimate (default profile)…"
  ```
- [ ] **AC-10** `apps/web/src/locales/pl.json` gains matching Polish keys:
  ```json
  "modules.estimates.profile_source.exact": "Dokładny profil filamentu",
  "modules.estimates.profile_source.default": "Domyślny profil {{material}}",
  "modules.estimates.states.absent.no_profile": "Brak skonfigurowanego profilu filamentu dla tego materiału — wycena niedostępna.",
  "modules.estimates.chip.absent_no_profile": "Brak profilu filamentu — wycena niedostępna.",
  "modules.estimates.chip.fresh_default": "Szacowany filament {{mass}} (profil domyślny).",
  "modules.estimates.chip.stale_default": "Szacowany filament {{mass}} — może być nieaktualny (profil domyślny).",
  "modules.estimates.chip.queued_default": "Szacowany filament {{mass}} — przeliczanie… (profil domyślny).",
  "modules.estimates.chip.queued_no_value_default": "Przeliczanie wyceny (profil domyślny)…"
  ```

### Visual regression

- [ ] **AC-11** New `apps/web/tests/visual/estimate-profile-source.spec.ts` covering:
  1. `fresh + exact_filament_mapping` — normal estimate display + exact badge
  2. `fresh + default_material_profile` — normal estimate + "Default PLA profile" badge + chip `_default` variant
  3. `absent + unavailable_no_profile` — absent state with "no profile configured" copy
  4. `stale + default_material_profile` — stale banner + default badge
  Each scenario tested in all 4 visual projects (desktop-light / desktop-dark / mobile-light /
  mobile-dark) = 16 snapshots total. Mock `/api/estimates` via `page.route` (same pattern as
  `estimates-display.spec.ts`) with `profile_selection_context` field set in the stub body.

## Tasks / Subtasks

### 1. Frontend types (api-types.ts)

1. [x] **(RED)** Add Vitest unit test asserting `ProfileSelectionContextView` shape and that
   `EstimateView.profile_selection_context` is nullable. Run — fails (type doesn't exist yet).
2. [x] **(GREEN)** Add `EstimateProfileSource`, `ProfileSelectionContextView` types and
   `profile_selection_context` field to `EstimateView` in `apps/web/src/lib/api-types.ts`.
3. [x] **(VERIFY)** `npm run typecheck` from `apps/web/` — zero errors.

### 2. ProfileSourceBadge component (AC-2, AC-3)

4. [x] **(RED)** Create `ProfileSourceBadge.test.tsx` (co-located) — test all 4 input cases
   (exact, default, unavailable, null). Run — fails (component absent).
5. [x] **(GREEN)** Implement `ProfileSourceBadge.tsx` using the existing `Badge` UI component
   (`import { Badge } from "@/ui/badge"`) and `useTranslation`. The component is pure/stateless.
6. [x] **(VERIFY)** `npm run test -- ProfileSourceBadge` — all cases green.

### 3. EstimateDisplay integration (AC-4, AC-5, AC-6)

7. [x] Extend `EstimateDisplay.tsx`:
   - Import `ProfileSourceBadge`.
   - In the `absent` branch: check `data.profile_selection_context?.estimate_profile_source === "unavailable_no_profile"` → swap `messageKey`.
   - In the `fresh/stale/queued/failed` branch: render `<ProfileSourceBadge>` after `<OverrideContextPanel>` when context is non-null.
8. [x] **(VERIFY)** Run existing `EstimateDisplay.test.tsx` — all tests still pass (regression).

### 4. EstimateChip integration (AC-7, AC-8)

9. [x] Extend `EstimateChip.tsx`:
   - Absent branch: swap `aria-label`/`title` for `unavailable_no_profile`.
   - Fresh/stale/queued branches: use `_default` i18n key variants when
     `data.profile_selection_context?.estimate_profile_source === "default_material_profile"`.
10. [x] **(VERIFY)** Run existing `EstimateChip.test.tsx` — all tests still pass (regression).

### 5. i18n (AC-9, AC-10)

11. [x] Add new keys to `apps/web/src/locales/en.json` under `modules.estimates.*`.
12. [x] Add matching Polish keys to `apps/web/src/locales/pl.json`.
13. [x] **(VERIFY)** `npm run lint` from `apps/web/` — zero warnings (i18n-lint catches missing keys).

### 6. Visual regression (AC-11)

14. [x] Create `apps/web/tests/visual/estimate-profile-source.spec.ts` with 4 scenarios ×
    4 visual projects = 16 snapshots. Add stubs to `api-stubs.ts` if needed (or inline in the
    spec — use same pattern as `estimates-display.spec.ts`).
15. [x] Run all 4 visual projects; commit baselines with `baseline-reviewed:` sign-offs.
16. [x] Update sprint-status: `35-5-estimate-ui-source-labels` → `review`.

## Dev Notes

### Pre-enumeration save (existence checklist)

**REUSE — do NOT re-implement:**

| What | Where |
|------|-------|
| `EstimateView` interface | `apps/web/src/lib/api-types.ts:449` — add additive nullable field |
| `OverrideContextView` interface | `apps/web/src/lib/api-types.ts:441` — DO NOT touch |
| `EstimateDisplay` component | `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` — extend, do not rewrite |
| `EstimateChip` component | `apps/web/src/modules/estimates/components/EstimateChip.tsx` — extend, do not rewrite |
| `OverrideContextPanel` component | `apps/web/src/modules/estimates/components/OverrideContextPanel.tsx` — DO NOT modify |
| `Badge` UI component | `apps/web/src/ui/badge.tsx` — reuse directly; do not re-author a badge |
| `useEstimate` hook | `apps/web/src/modules/estimates/hooks/useEstimate.ts` — DO NOT modify; hook already returns `EstimateView` which will gain the new field |
| `api()` helper | `apps/web/src/lib/api.ts` — used by `useEstimate`; no change needed |
| `EM_DASH`, `formatMass` | `apps/web/src/modules/estimates/lib/format.ts` — chip formatters, reuse |
| `cleanup` pattern | Every multi-`it` test file uses `afterEach(cleanup)` from `@testing-library/react` — mandatory |
| Visual test pattern | `apps/web/tests/visual/estimates-display.spec.ts` — copy stub + clock pattern exactly |
| `_test.ts` fixture | `apps/web/tests/visual/_test.ts` — already stubs unauthenticated routes; reuse |

### Backend API — what 35.3 shipped

The `/api/estimates` and `/api/estimates/recompute` responses now carry:

```ts
// EstimateView (backend: slicer/schemas.py EstimateView)
{
  ...existingFields,
  profile_selection_context: {          // null when no spoolman_filament_ref passed
    estimate_profile_source: "exact_filament_mapping"
                           | "default_material_profile"
                           | "unavailable_no_profile",
    selected_material: string | null,   // normalized (uppercase), from policy
    selected_spoolman_filament_ref: string | null,   // null for default_material_profile
    selected_filament_name: string | null,           // human Spoolman name
    orca_filament_profile_name: string | null,       // null for unavailable_no_profile
  } | null
}
```

**`unavailable_no_profile` + `status="absent"` invariant:** when no profile is configured,
backend returns `status="absent"` + `profile_selection_context.estimate_profile_source="unavailable_no_profile"`.
The UI must distinguish this from a regular absent (no estimate computed yet) — different
copy, same visual treatment (no numbers).

**`orca_filament_profile_name` is admin-scoped:** it carries the Orca internal system tree
profile name. It MUST NOT appear in the user-facing UI (per SCP Task 7 § step 5 + FR20-PRESET-1
extended to the policy source context). Render material name (`selected_material`) for the
default badge; render nothing Orca-specific for the exact badge.

### ProfileSourceBadge — exact rendering contract

```tsx
// exact_filament_mapping: confident, minimal badge
<Badge variant="outline">{t("modules.estimates.profile_source.exact")}</Badge>

// default_material_profile: muted badge with material name
<Badge variant="secondary">
  {t("modules.estimates.profile_source.default", { material: context.selected_material })}
</Badge>

// unavailable_no_profile | null → render nothing (absent state handles its own copy)
return null;
```

Use the existing `Badge` component from `apps/web/src/ui/badge.tsx` — variants `"outline"` and
`"secondary"` are already styled project-wide. Do not introduce new badge variants.

### EstimateDisplay absent-branch extension — code sketch

```tsx
// In EstimateDisplay.tsx — absent branch
if (data.status === "absent") {
  const isUnavailable =
    data.profile_selection_context?.estimate_profile_source === "unavailable_no_profile";

  return (
    <div className="flex flex-col gap-3">
      <div role="status" className="rounded-lg border p-2">
        <EmptyState
          messageKey={
            isUnavailable
              ? "modules.estimates.states.absent.no_profile"
              : "modules.estimates.states.absent.body"
          }
          tone="muted"
          icon={<FileQuestion className="size-8" />}
        />
      </div>
      <OverrideContextPanel context={data.override_context} />
      {recompute("absent")}
    </div>
  );
}
```

For `fresh/stale/queued/failed`, insert after `<OverrideContextPanel>`:

```tsx
{data.profile_selection_context !== null && (
  <ProfileSourceBadge context={data.profile_selection_context} />
)}
```

### EstimateChip extension — code sketch

```tsx
// absent branch — check for unavailable before falling through to generic absent
if (data.status === "absent") {
  const isUnavailable =
    data.profile_selection_context?.estimate_profile_source === "unavailable_no_profile";
  const titleKey = isUnavailable
    ? "modules.estimates.chip.absent_no_profile"
    : "modules.estimates.chip.absent";
  return (
    <ChipShell title={t(titleKey)} className={base}>
      <SpoolIcon className="size-3.5 text-muted-foreground/60" />
      <span className="text-muted-foreground">{EM_DASH}</span>
    </ChipShell>
  );
}

// fresh branch
const isDefault =
  data.profile_selection_context?.estimate_profile_source === "default_material_profile";

// fresh
return (
  <ChipShell
    title={t(isDefault ? "modules.estimates.chip.fresh_default" : "modules.estimates.chip.fresh", { mass })}
    className={base}
  >
    <SpoolIcon className="size-3.5 text-muted-foreground" />
    <span className="font-medium text-foreground">{mass}</span>
  </ChipShell>
);
```

Apply the same `isDefault` guard to the `stale` and `queued` branches.

### EstimateChip — data access note

`EstimateChip` currently calls `useEstimate` and branches on `data.status`. The `data` object
is typed as `EstimateView` — after AC-1, it will carry `profile_selection_context` (nullable).
No hook changes needed; the chip reads it directly from `query.data`.

**However**, `EstimateChip` branches on `data.status === "absent"` AFTER the loading check and
before accessing numeric fields. The `profile_selection_context` field on an absent record
comes from the same `data` object, so NO extra fetch is required.

### Visual test — stub shape

```ts
// In estimate-profile-source.spec.ts — extend the estimates-display.spec.ts pattern
function estimateWithSource(
  status: string,
  source: "exact_filament_mapping" | "default_material_profile" | "unavailable_no_profile",
  numericOverrides: Record<string, unknown> = {},
) {
  return {
    status,
    time_seconds: 12947,
    filament_g: 76.76,
    filament_mm: 25735.79,
    filament_cm3: 61.9,
    filament_cost: 4.6,
    currency: "PLN",
    computed_at: "2026-06-02T10:00:00Z",
    warnings: [],
    failure_reason: null,
    override_context: {
      material_class: "PLA",
      quality_tier: "standard",
      pinned_filament_name: "Bambu PLA Basic",
      custom_overrides_applied: false,
      purchase_url: null,
    },
    profile_selection_context: {
      estimate_profile_source: source,
      selected_material: "PLA",
      selected_spoolman_filament_ref: source === "exact_filament_mapping"
        ? "Bambu\x1fPLA\x1fPLA Basic" : null,
      selected_filament_name: "Bambu PLA Basic",
      orca_filament_profile_name: source !== "unavailable_no_profile"
        ? "Bambu PLA Basic @BBL X1C" : null,
    },
    ...numericOverrides,
  };
}
```

### Visual test — routeTree.gen.ts

This story adds NO new routes (pure component/style changes). `routeTree.gen.ts` regeneration
is **NOT needed** for 35.5. The reference in `memory/reference_web_routetree_regen.md` applies
to stories adding new TanStack route files.

### 35.4 FE tasks still gated

35.4 FE tasks (5–10 in that story) remain gated on G-UXGATE. 35.5 is **also** gated on
G-UXGATE — confirm with operator that the bmad-ux checkpoint output is available before
starting implementation. If 35.4 FE tasks run concurrently with 35.5, note that the
`AdminTabs.tsx` addition in 35.4 causes a visual baseline ripple across ALL admin specs —
that ripple must be resolved before 35.5 visual baselines are signed off.

### Magic-constant discipline (TB-051)

No new numeric constants. Enum variant strings (`"exact_filament_mapping"`, etc.) are the
`EstimateProfileSource` StrEnum values — mirror them literally in the TypeScript union type,
never hard-code ad-hoc strings. i18n keys follow the existing `modules.estimates.*` namespace
convention — no flat or non-namespaced keys.

### Out of scope (deferred to 35.6 / later)

- Bounded default-matrix backfill + enqueue guardrails (35.6)
- Admin-facing UX for 35.4 FE (gated on the same G-UXGATE, separate story)
- Any change to `OverrideContextPanel` or `useEstimate` — not needed for this story
- `orca_filament_profile_name` in any user-facing UI — admin-scoped, never expose

### Project Structure Notes

**FE files to CREATE [G-UXGATE]:**
- `apps/web/src/modules/estimates/components/ProfileSourceBadge.tsx`
- `apps/web/src/modules/estimates/components/ProfileSourceBadge.test.tsx`
- `apps/web/tests/visual/estimate-profile-source.spec.ts`

**FE files to MODIFY [G-UXGATE]:**
- `apps/web/src/lib/api-types.ts` — add `EstimateProfileSource`, `ProfileSelectionContextView`, update `EstimateView`
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` — absent branch distinction + badge render
- `apps/web/src/modules/estimates/components/EstimateChip.tsx` — absent/chip title variants for profile source
- `apps/web/src/locales/en.json` — add `modules.estimates.profile_source.*` + absent.no_profile + chip `_default` keys
- `apps/web/src/locales/pl.json` — add matching Polish keys

No backend changes. No Alembic migration. No new routes. No routeTree.gen.ts regeneration.
No worker image change → SW-DEPLOY-1 NOT tripped.

### References

- `architecture.md` § Initiative 23 / Decision AS — classified `EstimateProfileSource` contract.
- `epics.md` § Initiative 23 / Epic E35 / Story 35.5 + FR23-UI-LABEL-1 + NFR23-HONESTY-1 + NFR23-NO-BLOCK-1.
- SCP `sprint-change-proposal-2026-06-07-spoolman-filament-profile-estimates.md` § Task 7.
- `35-3-estimate-api-source-metadata.md` — shipped `ProfileSelectionContextView` DTO + `EstimateView.profile_selection_context`.
- `35-4-admin-policy-management.md` § G-UXGATE note — same gate applies here; 35.4 FE tasks still pending.
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx` — current render tree (lines 1–289).
- `apps/web/src/modules/estimates/components/EstimateChip.tsx` — current chip render tree (lines 1–168).
- `apps/web/src/modules/estimates/components/OverrideContextPanel.tsx` — DO NOT modify.
- `apps/web/tests/visual/estimates-display.spec.ts` — visual test pattern to replicate.
- `project-context.md` § Critical Implementation Rules — Tailwind v4, i18n mandatory (never hard-code copy), visual regression mandatory for any UI change.
- `memory/reference_web_routetree_regen.md` — routeTree regen NOT needed (no new route files).
- `memory/feedback_sprint_status_vanilla_shape.md` — sprint-status format rules.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `EstimateProfileSource` union type and `ProfileSelectionContextView` interface to `api-types.ts`; made `profile_selection_context` optional on `EstimateView` for backward compat (no modification to existing test fixtures required).
- `ProfileSourceBadge.tsx` — pure stateless component; uses `Badge variant="outline"` for exact, `variant="secondary"` for default-material; returns null for unavailable/null. 4/4 unit tests.
- `EstimateDisplay.tsx` — absent branch extended to distinguish `unavailable_no_profile` → swaps `messageKey`; fresh/stale/queued renders `<ProfileSourceBadge>` after `<OverrideContextPanel>` when context non-null. All 20 existing regression tests pass unmodified.
- `EstimateChip.tsx` — absent branch swaps `title`/`aria-label` for `unavailable_no_profile`; fresh/stale/queued use `_default` i18n key variants for `default_material_profile`. All 10 existing regression tests pass unmodified.
- 8 EN + 8 PL i18n keys added under `modules.estimates.*`; lint clean.
- Visual spec `estimate-profile-source.spec.ts` — 4 scenarios × 4 projects = 16 baseline snapshots generated and signed off. Existing estimates-display visual spec: 20/20 passes (no regression).
- `orca_filament_profile_name` never exposed in user-facing UI per SCP Task 7 § step 5.

### File List

**Created:**
- `apps/web/src/lib/api-types-profile-source.test.ts`
- `apps/web/src/modules/estimates/components/ProfileSourceBadge.tsx`
- `apps/web/src/modules/estimates/components/ProfileSourceBadge.test.tsx`
- `apps/web/tests/visual/estimate-profile-source.spec.ts`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-exact-desktop-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-exact-desktop-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-exact-mobile-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-exact-mobile-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-default-desktop-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-default-desktop-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-default-mobile-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-fresh-default-mobile-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-absent-unavailable-desktop-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-absent-unavailable-desktop-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-absent-unavailable-mobile-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-absent-unavailable-mobile-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-stale-default-desktop-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-stale-default-desktop-dark.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-stale-default-mobile-light.png`
- `apps/web/tests/visual/__snapshots__/estimate-profile-source.spec.ts/estimate-profile-source-stale-default-mobile-dark.png`

**Modified:**
- `apps/web/src/lib/api-types.ts`
- `apps/web/src/modules/estimates/components/EstimateDisplay.tsx`
- `apps/web/src/modules/estimates/components/EstimateDisplay.test.tsx`
- `apps/web/src/modules/estimates/components/EstimateChip.tsx`
- `apps/web/src/modules/estimates/components/EstimateChip.test.tsx`
- `apps/web/src/locales/en.json`
- `apps/web/src/locales/pl.json`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Senior Developer Review (AI)

- **AC-1 to AC-11**: Verified and implemented.
- **Bug Fix**: Fixed AC-5 violation in `EstimateDisplay.tsx` where the `ProfileSourceBadge` was missing in the `failed` state branch.
- **Test Coverage**: Expanded `EstimateDisplay.test.tsx` to cover the `failed` state badge rendering. Verified that all existing and new tests pass.
- **Documentation**: Updated File List to include modified test files that were previously omitted.
- **Status**: APPROVE.

## Change Log

- **2026-06-09**: Initial implementation of Story 35.5 (api-types, ProfileSourceBadge, EstimateDisplay, EstimateChip, i18n, visual tests).
- **2026-06-10**: AI Review (Hermes) - fixed AC-5 badge rendering in failed state, expanded test coverage, updated file list. Status updated to `done`.
