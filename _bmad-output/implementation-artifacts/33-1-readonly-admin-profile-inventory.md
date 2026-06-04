---
baseline_commit: 8583deb6caca29c116e584d0c1a032136ec5b254
---

# Story 33.1: Read-only admin profile inventory + compatibility surfacing (PROFILE-ADMIN-1)

Status: done

<!--
  Authored by bmad-create-story (BMAD-canonical route [CS] Create Story, phase 4-implementation),
  consuming UX-PROFILE-1 (_bmad-output/ux/profile-admin-selector-ux-2026-06-04.md) with Q1 RESOLVED
  as Path B (member selector surfaces material). Source artifacts: epics.md § Initiative 21 Story 33.1;
  architecture.md § Initiative 21 Decision AK (+ OD-7); prd.md § Initiative 21; SCP
  sprint-change-proposal-2026-06-04-profile-admin.md § 5/6/9.

  GATE NOTE: "ready-for-dev" = the story context is complete and dev-ready. Actual dev-story execution
  still respects the SCP § 7 operator dev-go gate; this spec authoring is doc-only (no code/deploy/commit).
  One DATA gate (Q5 — concrete per-material compatible-slot set) must be operator-confirmed before the
  visual fixtures/baselines are finalized; see "Open questions for operator" — it does not block backend
  authoring (the map is a structural SoT table; only its concrete TPU row content awaits confirmation).
-->

## Story

As an **admin/operator of the 3d-portal**,
I want **a read-only in-product inventory of the Orca process/intent profiles per `(printer_ref, material_class, quality_tier)` slot — each slot showing whether it is imported, resolvable, and compatible, with a human-readable reason and provenance — and a member-facing catalog selector that only ever offers compatible, available process choices for the chosen material**,
so that **I can see at a glance which profiles are set up vs missing vs structurally incompatible (the TPU case), and members can never select an incompatible or unavailable combination (no member-reachable resolver 422) — retiring the EST-TIERS-1 hand-placement workaround.**

This is the **first, read-only, deploy-clean slice** of Epic E33. It introduces **no write/upload surface, no on-disk write, no `configs` change, and no slicer-worker module** — so the SW-DEPLOY-1 overlay rebuild is **NOT** triggered. Import (33.2) and lifecycle management (33.3) are out of scope.

## Acceptance Criteria

### Backend — admin inventory read (`GET /api/admin/profiles`)

1. **AC-1 — Endpoint shape & auth.** A new `GET /api/admin/profiles?printer_ref=<ref>` endpoint exists, mounted under `/api/admin`, **admin-gated via `current_admin`** (`apps/api/app/core/auth/dependencies.py`), and **absent from `_PUBLIC_ROUTES`** (`apps/api/app/main.py:50`). A non-admin (member/agent) request → **403**; an anonymous request → 401. (FR21-PROFILE-INVENTORY-1, NFR21-AUTH-1.)
2. **AC-2 — Route-enforcement gate green.** Because the route carries an auth `Depends`, the Init 6/11.4 route-enforcement gate (`apps/api/tests/test_route_enforcement_gate.py`) passes **without** adding the route to `_PUBLIC_ROUTES`. No SCP/allowlist edit is needed or made. (NFR21-AUTH-1.)
3. **AC-3 — Per-slot DTO.** The response enumerates every `(printer_ref, material_class, quality_tier)` slot over the **named FE↔BE grid** (`MATERIAL_CLASSES` × `QUALITY_TIER_ORDER`) and returns per slot:
   `{material_class, quality_tier, imported: bool, resolvable: bool, compatible: bool, offerable: bool, status: "offerable"|"not_imported"|"not_resolvable"|"incompatible", reason: str|null, portal_label: str|null, provenance: {source_system_tree_hash: str|null, orca_version: str|null}}`.
   `offerable === (imported && resolvable && compatible)`. (FR21-PROFILE-INVENTORY-1, Decision AK.)
4. **AC-4 — One status per slot by fixed precedence.** `status` is derived by the UX § A precedence (top wins): **Incompatible** (`!compatible`) → **Not imported** (`compatible && !imported`) → **Not resolvable** (`compatible && imported && !resolvable`) → **Offerable**. Every non-offerable slot carries a non-null structured `reason` whose category matches its `status` (`incompatible_for_material` / `profile_not_imported` / `not_resolvable`). A **resolvable-but-incompatible** slot reads `compatible=false, offerable=false, status="incompatible"` — **never "available."** (FR21-COMPAT-1 read-only, NFR21-NO-422-1.)
5. **AC-5 — `resolvable` reuses the EST-TIERS-1 seam (no new resolve logic).** `resolvable` is computed via the **same** `resolve_preset` path that backs `GET /api/estimates/quality-tiers` (`apps/api/app/modules/slicer/router.py:111-137`, `estimate_read.SettingsEstimateResolver.resolve_preset`). `imported` is the **presence of the intent-triple file** at `VendoredProfileSource` path `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` (`apps/api/app/modules/slicer/resolver.py:114-148`) — distinct from `resolvable` (a present-but-malformed file is `imported=true, resolvable=false`). The inventory adds provenance + import + compatibility metadata as a **superset projection**; it does not re-derive resolution. (Decision AK; arch.md:2869-2871.)
6. **AC-6 — Resolvability parity (shared SoT test).** For every `(printer_ref, material_class, quality_tier)` the inventory's `resolvable` value **agrees** with the `available` value of `GET /api/estimates/quality-tiers` for the same printer/material — asserted by a **shared parity test** so the two surfaces cannot drift (one source of truth). (Decision AK; epics.md:3841.)
7. **AC-7 — Compatibility map is a first-class backend SoT declaration (OD-7).** `compatible` is evaluated against an **explicit per-material allowed-tier table** declared in **one** backend module (`apps/api/app/modules/slicer/compatibility.py`, new), the **source of truth**. The table is keyed `material_class → frozenset[quality_tier]`. Resolvability is **necessary but not sufficient**: a slot is `compatible=false` whenever its `quality_tier` is not in its `material_class`'s allowed set, **regardless of whether it resolves**. The map is **consumed read-only** here; authoring/editing it belongs to 33.2/33.3. (FR21-COMPAT-1, OD-7, Decision AK.)
8. **AC-8 — Selector projection excludes incompatible slots (shared test).** A single projection function derives the member-selector availability from the same per-slot computation, and a **shared test asserts the projection never surfaces an incompatible `(material_class, quality_tier)`** — neither the admin grid nor the member selector can offer a TPU-incompatible process choice for TPU (nor a TPU-only process for a non-TPU material). Selector parity asserted. (FR21-COMPAT-1 verifiable clause, FR21-SELECTOR-1, NFR21-NO-422-1.)
9. **AC-9 — Provenance no-leak fence.** `provenance` exposes **only** `source_system_tree_hash` (the `resolver.py:309` snapshot hash, may be truncated for display) and `orca_version` (`resolver.py:311`). The DTO contains **no Orca-internal profile keys, no filesystem paths, no g-code, no raw profile bodies**. A test asserts the serialized response matches an allowlisted field set (negative assertion on path-like / known-internal-key substrings). (FR21-PROFILE-INVENTORY-1, NFR21-OBS-1.)
10. **AC-10 — Read-only / deploy-clean.** No write/upload/multipart surface, no on-disk write, no `config.py` slot change, no Alembic migration, no slicer-worker (`workers/render/` / overlay) change. The vendored-dir read-only-at-runtime posture is **unchanged** (the write-posture reversal is Story 33.2). (Epics.md:3845; SCP § "Deploy-safety property".)

### Frontend — admin grid (UX-PROFILE-1)

11. **AC-11 — Profiles admin tab + route.** `AdminTabs.tsx` (`apps/web/src/modules/admin/AdminTabs.tsx:6`) gains a third tab: `ActiveTab` extends to `"users" | "invites" | "profiles"`, a `<Link role="tab" to="/admin/profiles">`, and a new `apps/web/src/routes/admin/profiles.tsx` route component **mirroring `users.tsx`/`invites.tsx`** including the **AuthGate discipline** (defer to the shell `AuthGate` for anonymous — no synchronous `<Navigate>` that strips `?next=`; role-tier redirect only for **authenticated-non-admin**). Gated on `useAuth().isAdmin`. (NFR21-AUTH-1, UX § B.1, Init 10 retro rule.)
12. **AC-12 — Grid = status matrix with one badge per cell.** Desktop renders a **4×3 matrix** (rows = `MATERIAL_CLASSES` in resolve order PLA/PETG/PCTG/TPU; columns = `QUALITY_TIERS` aesthetic/standard/strong); mobile collapses to **stacked per-material cards**. Each cell shows exactly **one** status (offerable / not imported / not resolvable / incompatible) by the AC-4 precedence, with a **human-readable reason** on every non-offerable cell, an always-visible **legend**, and a **printer-context header** (`Creality K1 Max · Microswiss HF`, single-printer v1 note). (NFR21-UX-1, UX § B.)
13. **AC-13 — Status visual distinction (a11y).** **Offerable is the only saturated-positive status** (new `--color-success` token); **Incompatible is the most de-emphasised** (muted/hatched, no action); **Not resolvable** is the only warning (`--color-warning`); **Not imported** is neutral. **No two statuses share a color, and status is never conveyed by color alone** — every cell carries **icon + text label + color** (WCAG 1.4.1). The grid is legible in greyscale. (NFR21-UX-1, UX § B.3/§ F.)
14. **AC-14 — Provenance affordance.** Offerable cells expose provenance behind a per-cell **ⓘ popover** (keyboard-dismissible, focus-trapped per the in-use shadcn/Radix primitive) showing `orca_version` + a **short `source_system_tree_hash`** (first 12 chars, monospace, copyable). **No Orca-internal/path/g-code** rendered — the FE mirror of the AC-9 DTO fence. (FR21-PROFILE-INVENTORY-1, UX § B.4.)
15. **AC-15 — Empty / loading / error (admin fails CLOSED/visible).** Loading → skeleton matrix (not a bare spinner). Empty → the grid still renders all slots (compatible-empty as **Not imported**, structurally-invalid as **Incompatible**) plus a one-line hint. `GET /api/admin/profiles` error → an **error panel with Retry**; the admin grid **must not** fabricate slot statuses or fall open to "all offerable." (UX § E.)
16. **AC-16 — Read-only affordances only.** No write controls ship. A compatible-**Not imported** cell may show a **disabled "Import" placeholder** signposting 33.2 (inert, with an "available in the import slice" tooltip — Q4 default applied); Incompatible cells show no action. (Epics.md:3845/3849, UX § H/Q4.)

### Frontend — member catalog selector (Q1 = Path B: surfaces material)

17. **AC-17 — Material is surfaced on the catalog selector (documented reversal).** `CatalogEstimateProfileSelector.tsx` (`apps/web/src/modules/estimates/components/CatalogEstimateProfileSelector.tsx`) is extended so the member **selects `material_class`** (PLA/PETG/PCTG/TPU); the `quality_tier` set then filters by that material's compatibility. This is a **deliberate reversal of the shipped EST-DISPLAY-1 "material internal / PLA-pinned" decision (`:22-34`)** and **MUST** carry an in-code comment block citing **both** decisions + **both** rationales (NFR-carve-out-reversal discipline, per UX § H/Q1 and [[feedback_scp_pre_enumeration_phase]] adjacency). (FR21-SELECTOR-1, UX § H/Q1 RESOLVED Path B.)
18. **AC-18 — Preserved invariant: catalog stays an estimate preview, not ordering/spool.** Surfacing `material_class` does **not** introduce ordering, quoting, or Spoolman spool-availability semantics: the resolve **`spoolman_filament_ref` pin stays `null`** on the catalog surface; filament-instance/spool selection remains exclusive to `/estimates`. The "no ordering/spool semantics" property is now held by the **bounded estimate-read contract** (`material_class` is a resolve input only), **not** by material-pinning. A test/grep asserts `spoolman_filament_ref` is not surfaced/settable on the catalog selector. (NFR21-NO-422-1 adjacency; EST-DISPLAY-1 invariant preserved by a different mechanism.)
19. **AC-19 — Hybrid disabled-vs-hidden, split by cause.** For the chosen material: **incompatible** tiers are **hidden** (removed from DOM/tab order — never teased); **compatible-but-unavailable** tiers (not imported / not resolvable) are **disabled-with-explanation** (visible, greyed, reason via tooltip + `aria-describedby` + helper line). A member can **never select** a non-offerable slot (`if (!isAvailable(tier)) return;`-style guard) → **NFR21-NO-422-1 holds structurally**. (FR21-SELECTOR-1, UX § C.)
20. **AC-20 — Fail-OPEN preserved on the member surface.** The shipped EST-TIERS-1 fail-open posture is kept: on a transient availability-fetch error / loading / omitted prop, tiers stay **selectable** and **Standard is never locked out** (`isAvailable(tier) = availabilityByTier.get(tier)?.available !== false`). Compatibility **hiding** and availability **disabling** apply **only** once the backend positively declares the state. (Deliberate asymmetry: admin fails closed/visible, member fails open — UX § E.)
21. **AC-21 — FE↔BE compatibility-map parity.** The FE mirrors the per-material allowed-tier table (in `apps/web/src/modules/estimates/lib/preset.ts`, alongside `MATERIAL_CLASSES`/`QUALITY_TIERS`) and a **vitest parity test asserts it agrees with the backend SoT** — same proven `QUALITY_TIER_ORDER ↔ QUALITY_TIERS` mirroring pattern. The FE never renders an option the projection marks incompatible. (FR21-COMPAT-1, arch.md:2871/2891.)

### Cross-cutting — i18n, visual, determinism

22. **AC-22 — i18n parity.** New keys under `modules.admin.profiles.*` (tab label, column/row headers, the four status labels, each non-offerable reason, legend, provenance labels, empty/error copy) and `modules.estimates.selector.*` (member reason strings `reason_not_imported`, `reason_unavailable`, material-control labels) land in **both `en.json` + `pl.json` with full key parity** and correct Polish diacritics. **Material names PLA/PETG/PCTG/TPU stay untranslated** (Init 19/20 convention); quality-tier display reuses existing `modules.estimates.quality.*`. (NFR21-I18N-PARITY-1.)
23. **AC-23 — One new theme token, no inline hex.** Add `--color-success` (+ its `.dark` variant) to `@theme {}` in `apps/web/src/styles/theme.css`; consume via the Tailwind class. **Zero inline hex** anywhere; all other statuses reuse existing tokens (`--color-warning`, `text-muted-foreground`, `border-border`, `--color-destructive`). (Project-context frontend rule, UX § F.)
24. **AC-24 — Visual baselines (NFR21-VISUAL-VERIFICATION-1).** New Playwright baselines across the 4 projects (`desktop-light/dark`, `mobile-light/dark`), each with a `baseline-reviewed:` sign-off line: (1) admin grid **mixed-status** fixture exercising all four statuses incl. the TPU row; (2) admin grid **empty**; (3) admin grid **error** panel; (4) member selector showing **offerable + compatible-unavailable (disabled-with-reason) + incompatible-hidden** with the **material control** (Path B); (5) provenance popover open (desktop). API stubbed via `apps/web/tests/visual/api-stubs.ts`. (NFR21-VISUAL-VERIFICATION-1.)
25. **AC-25 — Determinism gate.** 3× consecutive identical pytest + vitest pass counts before merge. (NFR21-DETERMINISM-1.)

## Tasks / Subtasks

- [ ] **T1 — Backend compatibility map (SoT) (AC-7)**
  - [ ] Add `apps/api/app/modules/slicer/compatibility.py` declaring `MATERIAL_TIER_COMPATIBILITY: dict[MaterialClass, frozenset[QualityTier]]` as the single source of truth, with a module docstring pointing each entry to the **OD-7 operator-confirmed compatibility contract** (NOT "what resolves" — magic-constant discipline).
  - [ ] **BLOCKED on Q5 data confirmation** for the concrete content (at minimum the TPU row). Until confirmed, scaffold the table structure + a clearly-flagged placeholder TPU row and surface Q5 in the operator question list; do not bake concrete fixtures/baselines against an unconfirmed map.
  - [ ] Expose `is_compatible(material_class, quality_tier) -> bool` + `incompatibility_reason(...) -> str` helpers.
- [ ] **T2 — Backend admin inventory endpoint (AC-1..AC-5, AC-9, AC-10)**
  - [ ] Add `apps/api/app/modules/slicer/admin_router.py` with `router = APIRouter(prefix="/api/admin", tags=["admin-profiles"])` and `GET /profiles`, admin-gated (`_user_id: uuid.UUID = current_admin`), mirroring the `sot/admin_router.py` sibling convention.
  - [ ] Mount in `apps/api/app/router.py` (`include_router`) alongside the other admin routers.
  - [ ] Add `AdminProfileSlot` + `AdminProfileInventoryResponse` to `apps/api/app/modules/slicer/schemas.py` (DTO per AC-3; provenance sub-model with only `source_system_tree_hash` + `orca_version`).
  - [ ] Compute `imported` from `VendoredProfileSource` intent-file presence; `resolvable` by reusing `resolve_preset` (catch `PresetResolveError`); `compatible` from T1; `status`/`offerable`/`reason` by AC-4 precedence; `provenance` from the resolved bundle snapshot (`resolver.py:302-311`) with the no-leak fence.
  - [ ] Factor the per-slot computation + the **selector projection** into a shared function so AC-6/AC-8 can assert one source of truth.
- [ ] **T3 — Backend tests (AC-1,2,4,6,8,9, AC-25)**
  - [ ] `apps/api/tests/test_admin_profiles_inventory.py`: 403-for-non-admin (member + agent) + 401 anonymous; DTO shape + precedence/status mapping for each of the four statuses; imported-vs-resolvable distinction (present-but-malformed file).
  - [ ] **Resolvability parity** test (AC-6): assert inventory `resolvable` == `quality-tiers` `available` for every slot (shared helper).
  - [ ] **Incompatible-not-offerable** + **selector-projection-excludes-incompatible** (AC-8) including the TPU row once Q5 is confirmed.
  - [ ] **No-internal-leak** DTO fence (AC-9): allowlisted field set; negative assertion on path/g-code/internal-key substrings.
  - [ ] Route-enforcement gate (AC-2) passes unchanged (no `_PUBLIC_ROUTES` edit).
- [ ] **T4 — FE admin tab + route + grid (AC-11..AC-16, AC-23)**
  - [ ] Extend `AdminTabs.tsx` `ActiveTab` + add the `Profiles` tab link; add `routes/admin/profiles.tsx` mirroring `users.tsx`/`invites.tsx` (AuthGate discipline).
  - [ ] Add `useAdminProfiles(printerRef)` hook (TanStack Query, queryKey `["admin","profiles",printerRef]`, `staleTime` justified by contract — see Cache topology below) calling `api("/api/admin/profiles?...")`.
  - [ ] Build the matrix (desktop) / stacked-cards (mobile) grid component with status badges (icon+text+color), legend, printer header, per-cell reason, provenance ⓘ popover, loading skeleton, empty hint, error+Retry panel, inert disabled-Import placeholder.
  - [ ] Add `--color-success` (+ `.dark`) to `theme.css`; zero inline hex.
- [ ] **T5 — FE member selector Path B (AC-17..AC-21)**
  - [ ] Extend `CatalogEstimateProfileSelector.tsx` to surface a **material control** + filter tiers by the FE compatibility mirror; hybrid hidden(incompatible)/disabled-with-reason(compatible-unavailable); preserve fail-open + Standard-never-locked-out.
  - [ ] Add the **reversal comment block** (EST-DISPLAY-1 ← Init 21 Path B, both rationales) and keep `spoolman_filament_ref = null` (AC-18); assert no spool/order control is introduced.
  - [ ] Add the FE compatibility mirror in `preset.ts` + a **vitest FE↔BE parity test** (AC-21).
  - [ ] Recommended control: **segmented pill group** for tiers (per-option `aria-describedby` reason); documented fallback = native `<select>` + helper line (Q2 default applied — see open questions).
- [ ] **T6 — FE tests (AC-12..AC-21, AC-22, AC-25)**
  - [ ] vitest (colocated, `afterEach(cleanup)` per project-context): grid status states + reason rendering + provenance popover + empty/error; member selector material control + hide/disable behavior + fail-open; FE↔BE compat parity.
  - [ ] i18n parity check (en/pl key-set equality; diacritics present; materials untranslated).
  - [ ] Don't mock `api()` — intercept at `fetch` level.
- [ ] **T7 — Visual baselines (AC-24)**
  - [ ] Add stubs to `apps/web/tests/visual/api-stubs.ts` for `/api/admin/profiles` (+ selector availability), add specs producing the 5 fixtures, generate baselines across the 4 projects, and include `baseline-reviewed:` sign-off lines per changed PNG (pre-commit baseline gate).
- [ ] **T8 — Determinism + self-review (AC-25)**
  - [ ] Run backend pytest 3× + vitest 3×, confirm identical counts; run `npm run lint` (`--max-warnings=0`), ruff check/format, typecheck.

## Dev Notes

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] — existence checklist)

1. **Resolver read contract (REUSE, do not re-derive):** `apps/api/app/modules/slicer/resolver.py` — `VendoredProfileSource` (`:114-148`) maps an intent triple to `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json`; a missing intent classifies `unsupported_material_class` (`:226`), never a silent fallback. `resolve()` (`:192`) yields the provenance snapshot `{source_system_tree_hash (:309), orca_version (:311)}`. **`imported` = file presence; `resolvable` = `resolve_preset` success — distinct.**
2. **EST-TIERS-1 availability seam (REUSE for `resolvable`):** `GET /api/estimates/quality-tiers` at `apps/api/app/modules/slicer/router.py:100-140` iterates `QUALITY_TIER_ORDER` (`:51`), calls `resolver.resolve_preset(intent)` (`estimate_read.SettingsEstimateResolver.resolve_preset`, `:256`), and reports `{quality_tier, available, reason="profile_not_imported"|null}`. **The inventory MUST agree on resolvability for the same slot (AC-6 parity test).** Reason today is a single generic string — the inventory adds the richer compatibility/import reasons on top, but `resolvable` itself must match.
3. **Schemas to extend (REUSE file):** `apps/api/app/modules/slicer/schemas.py` already holds `QualityTierAvailability` (`:86`) + `QualityTierAvailabilityResponse`. Add the admin DTO here, same module.
4. **Admin router convention (NEW sibling, follow precedent):** admin reads/writes for a subsystem live in a sibling `admin_router.py` (cf. `sot/admin_router.py`, `share/admin_router.py`, `invite/admin_router.py` — all mounted in `apps/api/app/router.py:1-32`). New `slicer/admin_router.py` mounts `GET /api/admin/profiles`. `current_admin` is used as a **default-value dependency** (`_user_id: uuid.UUID = current_admin`), per `admin/router.py:48`.
5. **Route-enforcement gate (CONTRACT):** `apps/api/tests/test_route_enforcement_gate.py:76` iterates routes and requires each `/api/*` route to have an auth `Depends` **or** appear in `_PUBLIC_ROUTES` (`main.py:50`). The new route has `current_admin` → passes with **no** allowlist edit. Do not touch `_PUBLIC_ROUTES`.
6. **Named FE↔BE grid contract (EXTEND, parity pattern):** backend `MaterialClass`/`QualityTier` literals (`slicer/models.py`; mirrored `api-types.ts:419,422`) ↔ FE `MATERIAL_CLASSES` (`preset.ts:14`) + `QUALITY_TIERS` (`preset.ts:25`). The OD-7 compatibility map extends this exact contract (per-material allowed-tier table), backend SoT + FE mirror + parity test — same shape as `QUALITY_TIER_ORDER ↔ QUALITY_TIERS`.
7. **FE admin chrome (EXTEND):** `AdminTabs.tsx:6` `ActiveTab = "users" | "invites"`; routes `apps/web/src/routes/admin/{users,invites}.tsx`. **No profiles tab today** — add the third tab + route, mirror the AuthGate discipline of the existing two.
8. **FE member selector (EXTEND, carries the reversal):** `CatalogEstimateProfileSelector.tsx` — native `<select>` exposing only `quality_tier`; material PLA-pinned/internal (`:22-34`); fail-open `isAvailable` (`:46-53`); selection guard (`:66`); availability via `useQualityTierAvailability(materialClass, printerRef)`. Path B surfaces material here → the documented EST-DISPLAY-1 reversal.
9. **Contracts already enforced in the area + mechanism:** (a) member-reachable-422 avoidance — mechanism = selector never offers a non-offerable slot (disable/hide) + backend projection SoT; (b) EST-DISPLAY-1 "no ordering/spool semantics" — mechanism **changes** from material-pinning to the bounded estimate-read contract (`spoolman_filament_ref=null`, material is a resolve input only) — this is the NFR-carve-out reversal, verify the invariant still holds by the new mechanism (AC-18).
10. **Defensive-policy reversal triggered:** EST-DISPLAY-1 material-internal/PLA-pinned → reversed by Init 21 Q1 Path B. Surfaced as a **named decision** in UX § H/Q1 + this spec (AC-17/AC-18), not an incidental code change. Four-step recipe applied: in-code comment citing both inits/rationales (T5); invariant re-verified by a different mechanism (AC-18); FE assertion that no spool/order control is introduced; captured as a decision in the UX artifact + sprint-status.
11. **Single printer v1:** `CATALOG_ESTIMATE_PRINTER_REF = "creality-k1-max-microswiss-hf"` (`preset.ts:41`). Grid shows one printer context (header, not a selector); printer registry is a future initiative.

### Cache-topology enumeration (per [[feedback_scp_pre_enumeration_phase]] § B — FE fetch story)

| Concern | Source: this story (`["admin","profiles",printerRef]`) | Source: related (`useQualityTierAvailability`) |
|---|---|---|
| Staleness budget (`staleTime`) | Admin inventory is operator-facing truth; a moderate `staleTime` is fine, but it must reflect imports. **v1: `staleTime: 0` / `refetchOnMount: "always"`** because "the admin must see the true current import/resolve state on tab entry per FR21-PROFILE-INVENTORY-1" — not because it matches any peer. (33.2 import success should `invalidateQueries(["admin","profiles"])`; out of scope here but note the key contract.) | Member selector availability; existing EST-TIERS-1 behavior, unchanged. |
| Retry policy | Default; admin fails **closed/visible** (error panel + Retry, AC-15) — no fail-open. | Existing fail-**open** (AC-20), unchanged. |
| Cache propagation on mutations | None this story (read-only). Reserve the `["admin","profiles"]` key for 33.2 import invalidation. | n/a |
| Cache eviction on route exit | None required (no cross-route contamination risk — admin-only surface). | n/a |
| Cache seeding on this route | None. | n/a |

Rows do not diverge in a way that needs a private cache; the one contract is **`staleTime: 0` on the admin inventory** so an out-of-band import is reflected on next tab visit. Pointed to FR21-PROFILE-INVENTORY-1, not to a peer value.

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **Per-material allowed-tier table (T1):** every entry points to the **OD-7 operator-confirmed compatibility contract** (Q5), NOT to "what resolves." The concrete TPU row is **operator data** — flag Q5; do not bake an unconfirmed map into fixtures/baselines.
- **`source_system_tree_hash` truncation = 12 chars (AC-14):** arbitrary display default (readability), explicitly marked arbitrary — copyable full value via the popover; no contract pins 12.
- **`staleTime: 0` (admin inventory):** points to FR21-PROFILE-INVENTORY-1 (admin must see true current state), not to a peer query's value.

### Architecture / constraints

- Decision AK (arch.md:2878-2898): inventory is a **read-only superset projection over the resolver**, not a new resolution path; `offerable = imported ∧ resolvable ∧ compatible`; backend is compatibility SoT, FE mirrors + parity test; concrete map deferred to data phase (Q5).
- Decision AL (import write posture) is **Story 33.2** — out of scope here.
- Backend rules: `Annotated` DI, `current_admin` default-value dep, namespaced logger, no `os.environ`, ruff `E,F,W,I,B,UP,SIM,RUF` line-length 100. TDD red→green.
- Frontend rules: `import type` for types, `noUncheckedIndexedAccess` (no `!`), `@/*` alias, network via `api()` only, i18n mandatory, no inline hex, ESLint `--max-warnings=0`, `afterEach(cleanup)` in multi-`it` vitest files.

### Project Structure Notes

- **New backend files:** `apps/api/app/modules/slicer/compatibility.py`, `apps/api/app/modules/slicer/admin_router.py`, `apps/api/tests/test_admin_profiles_inventory.py`. **Edited:** `apps/api/app/modules/slicer/schemas.py`, `apps/api/app/router.py`.
- **New FE files:** `apps/web/src/routes/admin/profiles.tsx`, an admin-profiles grid component + `useAdminProfiles` hook under `apps/web/src/modules/admin/`, visual specs. **Edited:** `AdminTabs.tsx`, `CatalogEstimateProfileSelector.tsx`, `preset.ts`, `theme.css`, `en.json`/`pl.json`, `api-types.ts` (add the admin DTO types — generated section convention), `apps/web/tests/visual/api-stubs.ts`.
- No `_PUBLIC_ROUTES` edit, no Alembic, no `config.py` slot, no `workers/render/` change, no `configs`-repo change. SW-DEPLOY-1 not triggered.

### References

- Epics: [Source: _bmad-output/planning-artifacts/epics.md#Story 33.1] (lines 3831-3849) — sketch, acceptance boundaries, test targets, out-of-scope.
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md#Initiative 21] — Decision AK (lines 2878-2898), OD-7 compatibility map, resolver/availability-seam enumeration (2869-2876).
- PRD: [Source: _bmad-output/planning-artifacts/prd.md#Initiative 21] — FR21-PROFILE-INVENTORY-1, FR21-COMPAT-1, FR21-SELECTOR-1, NFR21-NO-422-1/-AUTH-1/-UX-1/-I18N-PARITY-1/-VISUAL-VERIFICATION-1/-OBS-1/-DETERMINISM-1.
- UX: [Source: _bmad-output/ux/profile-admin-selector-ux-2026-06-04.md] — § A precedence, § B admin grid, § C hybrid disabled-vs-hidden, § D TPU example, § E fail postures, § F a11y/i18n/visual, § G the 9 FE ACs, **§ H/Q1 RESOLVED Path B (reversal discipline)**.
- SCP: [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md] — § 5 (OD-1 resolved, OD-7), § 6 (PROFILE-ADMIN-1 recommended first slice), § 7 (operator dev-go gate), § 9 (UX-PROFILE-1).
- Code: `apps/api/app/modules/slicer/{resolver.py,router.py,estimate_read.py,schemas.py}`, `apps/api/app/main.py:50`, `apps/api/app/router.py`, `apps/api/app/modules/admin/router.py:48`, `apps/api/tests/test_route_enforcement_gate.py`, `apps/web/src/modules/admin/AdminTabs.tsx`, `apps/web/src/modules/estimates/{components/CatalogEstimateProfileSelector.tsx,lib/preset.ts}`, `apps/web/src/lib/api-types.ts:419-422`.
- Memory: [[feedback_scp_pre_enumeration_phase]] — pre-enumeration + cache-topology + magic-constant discipline applied above.

### Open questions for operator (saved for the end, per create-story protocol)

- **Q5 RESOLVED (2026-06-04 operator decision):** TPU is exposed as **standard-only** for Story 33.1. Rationale: the operator uses separate TPU-specific Orca profiles in practice; until the profile import/manage UI exists, the read-only slice should avoid pretending TPU shares the PLA/PETG/PCTG tier spread. Implemented in backend SoT + FE mirror + tests/baselines.
- **Q2 (control type — default applied, non-blocking):** the spec prescribes the UX-recommended **segmented pill group** for tiers (accessible per-option reason), with the native-`<select>` + helper-line fallback documented. Confirm appetite for the control swap (it touches the EST-DISPLAY-1 component + its baselines) or accept the default.
- **Q3/Q4 (provenance disclosure depth / not-imported affordance — defaults applied, non-blocking):** ⓘ popover (Q3) and inert disabled-Import placeholder (Q4) per UX recommendations; flag if a different treatment is preferred.

## Dev Agent Record

### Agent Model Used

Laura / Hermes controller with Codex fallback reviewer. Gemini CLI smoke passed, but review invocations timed out without useful output; fallback was recorded and used read-only.

### Debug Log References

- `.hermes/run-logs/check-all-E33-1-final3-with-admin-profiles-visual-20260604_225528.log` — final full repo gate, `16/16 all green`; visual regression `412 passed / 24 skipped`.
- `.hermes/run-logs/check-all-E33-1-final2-20260604_224606.log` — pre-admin-profiles-visual full gate, all green.
- Codex fallback review identified a member selector material-switch race and missing admin profiles visual coverage; both were addressed before final gate.

### Completion Notes List

- Implemented read-only `GET /api/admin/profiles` with admin auth, slot DTOs, status precedence, leak-fenced provenance, and shared compatibility projection.
- Q5 resolved and implemented: `TPU = standard` only; PLA/PETG/PCTG keep aesthetic+standard+strong.
- Implemented admin Profiles tab/page/grid and member catalog selector Path B (material surfaced; incompatible tiers hidden; compatible-unavailable tiers disabled with reason; spool pin remains null).
- Closed Codex review finding: estimate reads are now availability-gated so material-switch races cannot fire member-reachable resolver 422s; added regression coverage.
- Added admin profiles visual baseline across desktop/mobile and light/dark; updated selector-related visual baselines.
- Final full gate passed: `infra/scripts/check-all.sh` → 16/16 green.

### File List

Key files changed/added:

- `_bmad-output/planning-artifacts/{prd.md,architecture.md,epics.md,sprint-change-proposal-2026-06-04-profile-admin.md}`
- `_bmad-output/ux/profile-admin-selector-ux-2026-06-04.md`
- `apps/api/app/modules/slicer/{admin_router.py,compatibility.py,resolver.py,schemas.py}`
- `apps/api/app/router.py`
- `apps/api/tests/{test_admin_profiles_inventory.py,test_slicer_compatibility.py,test_slicer_worker.py}`
- `apps/web/src/modules/admin/{AdminTabs.tsx,ProfileInventoryGrid.tsx,ProfileInventoryGrid.test.tsx,ProfilesPage.tsx,ProfilesPage.test.tsx,hooks/useAdminProfiles.ts,profiles-i18n.test.ts}`
- `apps/web/src/routes/admin/profiles.tsx`
- `apps/web/src/modules/estimates/{components/CatalogEstimateProfileSelector.tsx,components/CatalogEstimateProfileSelector.test.tsx,components/EstimateChip.tsx,components/EstimateChip.test.tsx,components/RowEstimatePanel.tsx,hooks/useEstimate.ts,lib/preset.ts,lib/preset-compatibility.test.ts}`
- `apps/web/src/modules/catalog/components/tabs/{FilesTab.tsx,FilesTab.test.tsx}`
- `apps/web/src/{lib/api-types.ts,locales/en.json,locales/pl.json,routeTree.gen.ts}`
- `apps/web/tests/visual/admin-profiles.spec.ts` plus generated visual snapshots for admin profiles and updated selector/admin-tab baselines.
