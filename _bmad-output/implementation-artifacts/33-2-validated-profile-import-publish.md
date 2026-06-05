---
baseline_commit: 6aa79ae0bc7f18502349fcfd77a7ffd2d17d87bb
---

# Story 33.2: Validated import/publish write path (PROFILE-ADMIN-2)

Status: review

<!--
  Authored by bmad-create-story (BMAD-canonical route [CS] Create Story, phase 4-implementation,
  preceded-by bmad-sprint-planning, validated against bmad-help routing 2026-06-05). This is the
  SECOND slice of Epic E33 and carries the only novel risk in Initiative 21 — it reverses the
  vendored-dir read-only-at-runtime posture (a named decision, Decision AL / OD-2).

  Source artifacts:
    - epics.md § Initiative 21 Story 33.2 (lines 3851-3868)
    - architecture.md § Initiative 21 Decision AL (lines 2900-2917) + Decision AK (read it consumes)
    - prd.md § Initiative 21 — FR21-PROFILE-IMPORT-1 (1953), FR21-COMPAT-1 (1952), FR21-SELECTOR-1
      (1954), NFR21-PROVENANCE-1 (1958), NFR21-NO-422-1 (1959), NFR21-AUTH-1 (1961), NFR21-OBS-1 (1962)
    - UX-PROFILE-1 (_bmad-output/ux/profile-admin-selector-ux-2026-06-04.md) § B.1 import affordance,
      § D TPU rejection example, § E admin-fails-closed
    - SCP sprint-change-proposal-2026-06-04-profile-admin.md § 6 (PROFILE-ADMIN-2), § 5 (OD-2/3/4/6/7),
      § 7 (operator dev-go gate), § 3 (deploy-safety property)
    - Shipped Story 33.1 (33-1-readonly-admin-profile-inventory.md) — the inventory read + compat SoT
      this story writes to and extends. NOTE the 2026-06-05 post-ship correction (native <select>) —
      no bearing on this backend-heavy slice; the selector compatibility behavior is preserved.

  GATE NOTE: "ready-for-dev" = the story context is complete and dev-ready. Actual dev-story execution
  remains BLOCKED pending an explicit operator dev-go (SCP § 7, mirrors Init 20 scope-of-approval
  discipline). This spec authoring is doc-only (no code/deploy/commit). TWO gates must clear before
  dev STARTS the write path — see "Operator / data / config gates": (G1) confirm the api container's
  portal-content mount is RW for the vendored subtree (HC2 boundary — a ~/repos/configs change if not,
  NOT a 3d-portal commit); (G2) confirm the sample/fixture intent-triple JSONs used to exercise a
  successful import. Backend non-write scaffolding (DTOs, validation seam, manifest schema, tests with
  fakes) can be authored without G1; the live-write AC verification needs it.
-->

## Story

As an **admin/operator of the 3d-portal**,
I want **to import a validated Orca process/intent profile through the admin panel — uploading the `{machine, process, filament}` triple for a `(printer_ref, material_class, quality_tier)` slot, with the import rejected unless it is BOTH structurally resolvable AND declared compatible for that material class — so that on success the profile is written in-place into the vendored intents tree, recorded in an on-disk sidecar manifest, and audit-logged**,
so that **a previously-gated tier (e.g. Aesthetic / Strong, or a TPU-compatible slot) becomes genuinely available to members with no member-reachable resolver 422, retiring the EST-TIERS-1 hand-placement workaround — while the `bundle_hash`, append-only stores, and provenance snapshots of every unrelated bundle stay byte-stable.**

This is the **second, write-bearing slice** of Epic E33 and **carries the initiative's only novel risk**: it **reverses** the vendored-dir read-only-at-runtime posture (Decision AL / OD-2 — a deliberate, named reversal contained to this slice). It builds directly on the Story 33.1 inventory read + the `compatibility.py` SoT (which it now also enforces at write time). Lifecycle management — rename label / disable / delete (Story 33.3) — and re-slice-on-import (OD-6, gated on EST-PARSE-1) are **out of scope**.

## Acceptance Criteria

### Backend — validated import endpoint (`POST /api/admin/profiles/import`)

1. **AC-1 — Endpoint shape & auth.** A new `POST /api/admin/profiles/import` endpoint exists on `slicer/admin_router.py` (the same router as the 33.1 inventory GET, `prefix="/api/admin"`), **admin-gated via `current_admin`** (default-value `Depends`, `apps/api/app/core/auth/dependencies.py`), and **absent from `_PUBLIC_ROUTES`** (`apps/api/app/main.py`). A non-admin (member/agent) request → **403**; an anonymous request → 401. The route is a mutating request, so the CSRF `X-Portal-Client: web` header is required and enforced **automatically by the existing CSRF middleware** (`apps/api/app/core/auth/csrf.py`) — no route-level CSRF code. (FR21-PROFILE-IMPORT-1, NFR21-AUTH-1.)
2. **AC-2 — Route-enforcement gate green.** Because the route carries an auth `Depends`, the Init 6 / Story 11.4 route-enforcement gate (`apps/api/tests/test_route_enforcement_gate.py`) passes **without** adding the route to `_PUBLIC_ROUTES`. No allowlist edit is made.
3. **AC-3 — Request shape.** The endpoint accepts **multipart/form-data** mirroring the `sot/admin_router.py` `admin_upload_file` shape (NOT calling it — see AC-13): a `file` (the intent-triple JSON, an `UploadFile`) plus explicit form fields `printer_ref: str`, `material_class: MaterialClass`, `quality_tier: QualityTier`, and an optional `portal_label: str | None`. **The target slot is taken from the form fields, never inferred from file content** (the uploaded JSON is the partials only). `material_class` / `quality_tier` outside the named `Literal` sets → 422 (FastAPI validation). (FR21-PROFILE-IMPORT-1.)
4. **AC-4 — Upload size cap (magic-constant: pointed to a contract).** The uploaded file is capped at **`_MAX_PROFILE_BYTES = 1 * 1024 * 1024` (1 MiB)** → over-cap returns **413**. Justification: an intent triple is a **small JSON object** (`{machine, process, filament}` of merged Orca key/values), orders of magnitude below the 500 MB STL cap (`_MAX_FILE_BYTES`) that the model-upload path uses — this cap is an explicit safety bound against a non-profile payload, NOT a reuse of the STL cap. Marked arbitrary-but-bounded: revisit only if a legitimate vendored triple is shown to exceed it. (Magic-constant discipline, [[feedback_scp_pre_enumeration_phase]] § C.)
5. **AC-5 — Compatibility gate FIRST (OD-7, cheap, no I/O).** Before any disk write or resolve, the target slot is checked against the **`compatibility.py` SoT** via `is_compatible(material_class, quality_tier)`. An import targeting an **incompatible** slot (e.g. `TPU·aesthetic` or `TPU·strong` given the Q5 `TPU = {standard}` map, or any non-TPU process slot dropped into a TPU slot) is **rejected with HTTP 422** and a structured detail `{reason_category: "incompatible_for_material", message: ...}` — `INCOMPATIBLE_REASON` from `compatibility.py`. **Resolvability alone does not make a slot publishable** (`resolvable ∧ ¬compatible` is still not offerable). Nothing is written; the vendored tree is byte-unchanged. (FR21-COMPAT-1 enforcement, Decision AL gate 2.)
6. **AC-6 — Malformed-triple gate.** The uploaded payload must parse as JSON and be an **object carrying dict `machine`, `process`, `filament` entries** — the SAME shape gate the resolver applies (`resolver.py:265-275`). A non-JSON body, a non-object, or a missing/non-dict kind → **422** with `{reason_category: "invalid_partial", message: ...}`. Nothing is written. (FR21-PROFILE-IMPORT-1.)
7. **AC-7 — Structural resolvability gate via the existing `resolve()` path (OD-3) — REUSE, do not reshape.** The import validates by running the **existing `resolve()` merge → normalize → required-keys → (Null)CLI path** (`apps/api/app/modules/slicer/resolver.py:220-361`) against the uploaded partials + the **real** vendored system tree, with the default `NullCliValidator` (availability == resolvability is the live contract; real-Orca CLI validation is the OD-3 optional follow-up, NOT in v1). A `ResolveFailure` → **422** with the classified `ResolveReason` as `reason_category` (`unsupported_material_class` / `missing_system_profile` / `invalid_partial` / `cli_validation_failed`) + message. **The validation MUST NOT publish (write to the live `intent_path`) before it passes** — see AC-8. (FR21-PROFILE-IMPORT-1, Decision AL gate 1, NFR21-PROVENANCE-1.)
   - **Recommended mechanism (validate-from-payload, no live-tree exposure):** a small `StagedProfileSource(VendoredProfileSource)` subclass that **inherits `system_tree()` from the real vendored root** but overrides `intent_partials(intent)` to return the **uploaded dict** (and `has_intent → True`), passed into `resolve(...)`. This reuses `resolve()` verbatim, validates against the real system tree, and **never writes the live `intent_path` until validation succeeds**. A documented fallback (write-to-`intent_path`-then-rollback-on-failure) is **discouraged** — it transiently exposes an unvalidated file to a concurrent resolve; prefer the staged source.
8. **AC-8 — Atomic publish; failed validation leaves the tree byte-identical.** On success the validated triple is written to its `VendoredProfileSource.intent_path(intent)` (`<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json`) **atomically** (write to a sibling temp file + `fsync` + `os.rename`, mirroring the `_write_atomic` tmp→rename discipline — see AC-13). On ANY validation rejection (AC-5/6/7) **no file is created or modified in the live vendored tree and no temp file is left behind** — a test asserts the tree is byte-identical before vs after a rejected import. Re-import of an already-imported slot **overwrites in place atomically** (upsert; the provenance snapshot identity changes automatically — AC-11). (Decision AL, OD-2, NFR21-PROVENANCE-1.)
9. **AC-9 — On-disk sidecar manifest (OD-4, no DB).** On a successful publish an on-disk **sidecar manifest** is written next to the intent file (recommended: `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.manifest.json`), atomically and in the same publish step. Schema (v1):
   `{manifest_version: "1", portal_label: str|null, imported_by: str(uuid), imported_at: iso8601, original_filename: str, status: "published", compatibility: {compatible: bool, reason: str|null}, provenance: {source_system_tree_hash: str, orca_version: str}}`.
   `manifest_version: "1"` points to the **OD-4 sidecar contract v1** (not a peer value). The manifest stores **import metadata + a snapshot of the compatibility verdict at import time** (informational/audit history); it is **NOT** a second compatibility SoT — see AC-10. (Decision AL on-disk-sidecar, OD-4.)
10. **AC-10 — Single compatibility SoT preserved (no dual-SoT drift).** The **live** `compatible` flag surfaced by the 33.1 inventory read stays computed from **`compatibility.py`** (the Decision AK code SoT). The sidecar manifest's `compatibility` block is a **point-in-time record of the verdict at import**, consumed for audit/history — it does **NOT** override or shadow the live code map. This is an explicit design decision: surfacing the live gate from the manifest would create a second source of truth that could drift from `compatibility.py` — precisely the divergence class [[feedback_scp_pre_enumeration_phase]] § A.5 warns against. (Decision AK boundary + Decision AL "manifest reflects ... compatibility decision" reconciled.)
11. **AC-11 — Provenance + reproducibility invariants preserved (NFR21-PROVENANCE-1).** (a) Importing an intent triple for slot A **MUST NOT perturb the `bundle_hash`** of any unrelated already-persisted bundle — a test resolves an unrelated slot B before and after an import of slot A and asserts a **byte-identical `bundle_hash`**. (b) The import writes **only** the intent file (+ its manifest); it does **not** edit the system tree, so the `source_system_tree_hash` of unrelated bundles is unchanged; the resolver's existing in-place-edit provenance mechanism (`resolver.py:328-347`) means that *were* the system tree mutated it would yield a new snapshot identity automatically — the import does not re-invent provenance. (c) The **append-only bundle/estimate stores and the `bundle_hash` input order are NOT edited** (no `resolver.py` reshape). (NFR21-PROVENANCE-1.)
12. **AC-12 — Audit on every import (NFR21-OBS-1).** A successful import emits `record_event(action="slicer_profile.import", entity_type="slicer_profile", entity_id=<deterministic slot id>, actor_user_id=<importer>, after={printer_ref, material_class, quality_tier, portal_label, source_system_tree_hash, original_filename})`. **`"slicer_profile"` is added to `KNOWN_ENTITY_TYPES`** in `apps/api/app/core/audit.py:41-58` (with a one-line comment per the existing convention) — without it `record_event` raises `ValueError`. The audit payload carries **no Orca-internal profile body and no g-code** (NFR21-OBS-1 fence). A rejected import is **not** audited as an import (optionally logged, not a `record_event`). (NFR21-OBS-1.)
13. **AC-13 — Reuse the upload SHAPE, not the `ModelFile` helper.** The import mirrors the `sot/admin_router.py` `admin_upload_file` **multipart + atomic-write + audit shape**, but **does NOT call** `upload_model_file` / `_write_atomic` (those are coupled to `ModelFile` rows, the 500 MB binary cap, the catalog content dir, and render enqueue). The profile import writes a **small JSON file** into the **vendored** tree with its own JSON-appropriate cap (AC-4) and its own atomic helper. (Pre-enumeration: reuse + extend, never parallel-implement the wrong surface.)

### Backend — inventory read extension (surface manifest label)

14. **AC-14 — 33.1 inventory read surfaces `portal_label` from the manifest.** The shipped 33.1 inventory loop (`slicer/admin_router.py` `build_slot`, currently hardcoding `portal_label=None`) is **minimally extended** to read the sidecar manifest (when present) and populate `AdminProfileSlot.portal_label`. The live `imported` / `resolvable` / `compatible` / `status` / `offerable` / `provenance` fields stay computed exactly as in 33.1 (the manifest does NOT replace any of them — AC-10). A slot with no manifest reads `portal_label=None` (unchanged behavior). The AC-6 resolvability-parity test from 33.1 still holds. (Decision AL "inventory reflects manifest"; FR21-PROFILE-INVENTORY-1.)

### Backend — end-to-end selector invariant

15. **AC-15 — Selector invariant end-to-end (NFR21-NO-422-1, FR21-SELECTOR-1).** After a successful **compatible** import, the slot resolves and the shared `member_selector_tiers(...)` projection (`slicer/admin_router.py:129-148`) surfaces it as **available**; an **incompatible** slot is never published (AC-5) and so is never surfaced (the projection already omits incompatible slots — 33.1 AC-8). A test drives import → inventory read → projection and asserts: (a) the just-imported compatible slot is offerable + projected-available; (b) **no incompatible `(material_class, quality_tier)` is ever projected**; (c) every projected-available slot resolves successfully (no member-reachable `unsupported_material_class` / incompatible). (NFR21-NO-422-1, FR21-SELECTOR-1 end-to-end.)

### Frontend — admin import affordance (UX-PROFILE-1 § B.1 / § D / § E)

16. **AC-16 — Inert Import placeholder becomes a live import action.** The 33.1 inert `ImportPlaceholder` on **compatible-not-imported** cells (`apps/web/src/modules/admin/ProfileInventoryGrid.tsx:157`) is wired into a real import affordance: clicking it opens an **import control** (file picker / small modal) that posts the selected JSON file + the cell's `(printer_ref, material_class, quality_tier)` to `POST /api/admin/profiles/import` via the `api()` wrapper (which adds `X-Portal-Client: web`). **Incompatible cells still show no import action** (unchanged from 33.1). Re-import on an already-offerable cell is a minor affordance (a quiet "replace" action) — **deferred to 33.3** unless trivial; the primary path is importing into a not-imported compatible cell. (UX § B.1 / § H Q4.)
17. **AC-17 — Import mutation + cache invalidation.** A new `useImportProfile()` TanStack mutation (`apps/web/src/modules/admin/hooks/`) posts the multipart import and on success calls **`invalidateQueries(["admin","profiles"])`** — the exact key contract the 33.1 `useAdminProfiles` hook reserved (`hooks/useAdminProfiles.ts` docstring) — so the grid refetches and the cell flips from **Not imported** to **Offerable**. (Cache-topology table below; FR21-SELECTOR-1.)
18. **AC-18 — Rejection reason surfaced in the admin panel (admin fails CLOSED/visible).** A rejected import (422 incompatible / not-resolvable / invalid, 413 too-large) surfaces the structured `reason_category` as a **human-readable, localized** message at the import affordance (inline error or toast) — the admin sees *why* (UX § D: "the rejection surfaces in the grid"; UX § E: admin fails closed/visible, never fabricates success). The grid is **not** optimistically flipped to offerable before the server confirms. (NFR21-UX-1, UX § E.)

### Cross-cutting — i18n, visual, determinism

19. **AC-19 — i18n parity.** New keys under `modules.admin.profiles.import.*` (import action label, file-picker copy, success copy, each rejection reason: `incompatible_for_material` / `not_resolvable` / `invalid_partial` / `unsupported_material_class` / `missing_system_profile` / `cli_validation_failed` / `too_large`, optional portal-label field label) land in **both `en.json` + `pl.json` with full key parity** and correct Polish diacritics. Reuse the existing `modules.admin.profiles.reason.*` keys where the category already exists (33.1). **Material names PLA/PETG/PCTG/TPU stay untranslated** (Init 19/20 convention). (NFR21-I18N-PARITY-1.)
20. **AC-20 — No new theme token; no inline hex.** The import affordance reuses existing tokens (`--color-destructive` for rejection, `--color-success` from 33.1 for the post-import offerable flip, `text-muted-foreground`, `border-border`). **Zero inline hex.** (Project-context frontend rule.)
21. **AC-21 — Visual baselines (NFR21-VISUAL-VERIFICATION-1, UX-designed states).** New Playwright baselines across the 4 projects (`desktop-light/dark`, `mobile-light/dark`), each with a `baseline-reviewed:` sign-off line: (1) import affordance/modal **open** on a compatible-not-imported cell; (2) **rejection** state showing a localized incompatibility/not-resolvable reason; (3) **post-import success** — the cell now **Offerable**. API stubbed via `apps/web/tests/visual/api-stubs.ts` (add an `/api/admin/profiles/import` stub + a post-import inventory variant). (NFR21-VISUAL-VERIFICATION-1.)
22. **AC-22 — Determinism gate.** 3× consecutive identical pytest + vitest pass counts before merge. (NFR21-DETERMINISM-1.)

### Scope fence

23. **AC-23 — Write-slice scope fence (what this story does NOT do).** No lifecycle actions (rename label / disable / delete — Story 33.3); **no re-slice / backfill on import** (OD-6 — deferred, gated on EST-PARSE-1; do NOT enqueue any slice); no printer registry (single `creality-k1-max-microswiss-hf`, OD-5); no real-Orca CLI slice-validation (OD-3 follow-up); no Spoolman change; **no `resolver.py` reshape**, no `bundle_hash` input-order change, no append-only-store edit, no Alembic migration / slicer DB schema (OD-4). **No slicer-worker / `workers/render/` change → SW-DEPLOY-1 overlay rebuild NOT triggered** (vendored profiles are *data* on the shared volume, visible to the worker without an image rebuild — SCP § 3 deploy-safety). The only out-of-repo coordination is the HC2 portal-content RW-mount **verification** (gate G1) — a `~/repos/configs` concern if a change is needed, **NOT a 3d-portal commit**. (Epics 33.2 out-of-scope; Decision AL configs/app boundary.)

## Tasks / Subtasks

- [x] **T1 — Audit entity-type registration (AC-12)**
  - [ ] Add `"slicer_profile"` to `KNOWN_ENTITY_TYPES` in `apps/api/app/core/audit.py:41-58` + a one-line comment in the block above it (action `slicer_profile.import` / `.delete`, the latter reserved for 33.3), matching the existing comment convention.
  - [ ] RED test first: `record_event(..., entity_type="slicer_profile", ...)` no longer raises `ValueError`.
- [x] **T2 — Staged validation seam (AC-7) — reuse `resolve()` verbatim**
  - [ ] Add `StagedProfileSource(VendoredProfileSource)` (in `slicer/resolver.py` or a small `slicer/import_service.py`): inherits `system_tree()`/`system_tree_hash()` from the real root, overrides `intent_partials(intent)` to return the uploaded dict and `has_intent → True`. NO change to `resolve()` itself.
  - [ ] Validation helper: `validate_import(partials, intent, *, real_root, orca_version) -> ResolveOutcome` that builds a `StagedProfileSource` and calls the existing `resolve(...)` with `NullCliValidator` + `NoopOverrideProvider` + a throwaway/tmp `BundleStore` (validation must not pollute the live append-only store — use a temp store or a no-persist path; assert no live-store write on the validation path).
- [x] **T3 — Atomic publish + sidecar manifest (AC-8, AC-9, AC-10)**
  - [ ] `publish_intent(partials, intent, *, manifest_meta) -> None`: write the triple JSON to `source.intent_path(intent)` via tmp-file + `fsync` + `os.rename` (dedicated JSON atomic helper, NOT `_write_atomic`); write the `.manifest.json` sidecar atomically in the same step. `os.makedirs(parents, exist_ok=True)` for the slot dirs.
  - [ ] Manifest schema v1 per AC-9; `manifest_version="1"`; compatibility block is a point-in-time record (AC-10 — does NOT become the live SoT).
  - [ ] Rollback/cleanup guarantee: on any failure no live file/temp file remains (AC-8 byte-identical assertion).
- [x] **T4 — Import endpoint (AC-1..AC-8, AC-12, AC-13)**
  - [ ] Add `POST /profiles/import` to `slicer/admin_router.py` (multipart: `file`, `printer_ref`, `material_class`, `quality_tier`, optional `portal_label`; `_user_id = current_admin`; `_MAX_PROFILE_BYTES` cap → 413).
  - [ ] Gate order: size (413) → parse+shape (422 invalid_partial) → compatibility (422 incompatible_for_material) → structural resolve (422 classified ResolveReason) → publish (atomic) → manifest → audit → 201 + updated `AdminProfileSlot`.
  - [ ] Add `AdminProfileImportResponse` (or reuse `AdminProfileSlot`) + a structured rejection detail model to `slicer/schemas.py` (`extra="forbid"`, no internal leak).
  - [ ] No `_PUBLIC_ROUTES` edit (AC-2); CSRF automatic (AC-1).
- [x] **T5 — Inventory read manifest surfacing (AC-14)**
  - [ ] Extend `build_slot` / the inventory loop to read the sidecar manifest (when present) and populate `portal_label`; keep all other fields as 33.1. Add a `manifest_label_for(intent) -> str | None` reader on the source seam or import service.
- [x] **T6 — Backend tests (AC-1,2,5,6,7,8,9,11,12,14,15, AC-22)** — `apps/api/tests/test_admin_profiles_import.py`
  - [ ] 403 non-admin (member + agent) + 401 anonymous; 413 over-cap.
  - [ ] Incompatible-slot import (TPU·aesthetic, TPU·strong) → 422 `incompatible_for_material`, **not written** (tree byte-identical).
  - [ ] Malformed triple (non-JSON / missing kind / non-dict kind) → 422 `invalid_partial`, not written.
  - [ ] Structural resolve failure (required-key gap) → 422 classified reason, not written.
  - [ ] Successful compatible import (e.g. PETG·strong, or TPU·standard) → 201; intent file present at `intent_path`; inventory read now `imported ∧ resolvable ∧ offerable`; sidecar manifest written with importer/timestamp/label/compat-snapshot; audit `slicer_profile.import` emitted with `entity_type="slicer_profile"`.
  - [ ] **Provenance invariant (AC-11):** unrelated slot B `bundle_hash` byte-stable across an import of slot A; import does not write the system tree / append-only bundle store on the validation path.
  - [ ] **Atomicity (AC-8):** vendored tree byte-identical after a rejected import; no temp leftover.
  - [ ] **End-to-end selector (AC-15):** import → inventory → `member_selector_tiers` projects the new slot available; incompatible never projected; every projected slot resolves.
  - [ ] Reuse the 33.1 test DI pattern (`app.dependency_overrides` for the source/resolver seams; fake/tmp vendored root) — see `test_admin_profiles_inventory.py` fixtures.
- [x] **T7 — FE import affordance + mutation (AC-16,17,18,19,20)**
  - [ ] Wire `ProfileInventoryGrid` `ImportPlaceholder` → live import control (file picker / small modal) on compatible-not-imported cells; incompatible cells unchanged.
  - [ ] Add `useImportProfile()` mutation (multipart via `api()`); on success `invalidateQueries(["admin","profiles"])`; surface rejection `reason_category` localized (admin fails closed/visible, no optimistic flip).
  - [ ] i18n keys `modules.admin.profiles.import.*` (en + pl parity, diacritics); reuse existing `reason.*` keys; zero inline hex.
- [x] **T8 — FE tests (AC-16..AC-20, AC-22)**
  - [ ] vitest (colocated, `afterEach(cleanup)`): import affordance opens on compatible-not-imported; success → invalidation + cell flips offerable; each rejection reason rendered; incompatible cells show no import; i18n parity check (en/pl key-set equality, materials untranslated).
  - [ ] Don't mock `api()` — intercept at `fetch` level.
- [ ] **T9 — Visual baselines (AC-21)**
  - [ ] Add `/api/admin/profiles/import` stub + post-import inventory variant to `apps/web/tests/visual/api-stubs.ts`; specs for the 3 states × 4 projects; `baseline-reviewed:` sign-off per PNG.
- [ ] **T10 — Determinism + self-review (AC-22)**
  - [ ] Backend pytest 3× + vitest 3× identical counts; `npm run lint --max-warnings=0`, `ruff check`/`format`, typecheck; full `infra/scripts/check-all.sh` green before the ff-merge.

## Dev Notes

### Pre-enumeration save (per [[feedback_scp_pre_enumeration_phase]] § A — existence checklist)

1. **Import-target file path (REUSE):** `VendoredProfileSource.intent_path(intent)` (`apps/api/app/modules/slicer/resolver.py:144-157`) is the single source of the `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` layout. The import writes **exactly** this path — do not re-derive the layout. `has_intent` (`:159-166`) is the `imported` existence check 33.1 already uses.
2. **Validation path (REUSE, do not reshape):** `resolve()` (`resolver.py:220-361`) is the structural-resolvability gate — merge (`resolve_inheritance`) → `normalize_for_cli` → malformed-shape gate (`:265-275`, mirror its `{machine,process,filament}` dict check for AC-6) → `check_required_keys` → `NullCliValidator`. It takes a `source: VendoredProfileSource`; the staged-source subclass (AC-7) feeds the uploaded partials in without touching disk. `resolve_intent` (`:364-393`) is the settings-wired entry but reads the **live** root — use it only as the post-publish re-resolve, not for pre-publish validation.
3. **Compatibility SoT (REUSE, enforce):** `apps/api/app/modules/slicer/compatibility.py` — `is_compatible(material_class, quality_tier)` (`:52-58`) + `INCOMPATIBLE_REASON = "incompatible_for_material"` (`:37`). Q5 map: TPU = `{standard}` only; PLA/PETG/PCTG = all three tiers (`:43-49`). The import enforces this map at write time (33.1 only consumed it read-only).
4. **Per-slot projection (REUSE):** `build_slot` / `member_selector_tiers` (`slicer/admin_router.py:94-148`) are the shared SoT 33.1 shipped; AC-14 extends `build_slot` (`portal_label`), AC-15 asserts the projection end-to-end. `derive_status_and_reason` (`:75-91`) is unchanged.
5. **Upload + audit shape (REUSE the SHAPE only):** `sot/admin_router.py` `admin_upload_file` (`:447-501`) + `sot/admin_service.py` `_write_atomic` (`:475-503`, 500 MB `_MAX_FILE_BYTES`) + `upload_model_file` audit (`:583-594`). The profile import mirrors *multipart + atomic-write + audit* but is JSON-into-vendored-tree, NOT `ModelFile`-into-content-dir (AC-13) — do not call those helpers.
6. **Audit registry (EXTEND):** `apps/api/app/core/audit.py` — `record_event` (`:61-98`) **rejects an unknown `entity_type` with `ValueError`** (`:81-86`); `KNOWN_ENTITY_TYPES` (`:41-58`) does **not** contain `slicer_profile` → must add it (AC-12). Action strings are unconstrained (only `entity_type` is gated).
7. **Config slots (REUSE):** `apps/api/app/core/config.py` — `slicer_vendored_profiles_dir` (`:118`, default `/data/content/slicer/vendored`, documented read-only-at-runtime — this story is the named reversal), `portal_content_dir` (`:28`, `/data/content` — same volume the api ALREADY writes model uploads to → strong signal the RW mount is already in place, gate G1 verifies), `orca_version` (`:112`, `2.3.2`), `slicer_bundle_store_dir` (`:124`).
8. **CSRF (AUTOMATIC):** `apps/api/app/core/auth/csrf.py` middleware enforces `X-Portal-Client: web` on all mutating `/api/*` (except `/api/share/*`). The import POST needs no route-level CSRF code; the FE `api()` wrapper adds the header (AC-1/AC-16).
9. **Route mount (EXTEND):** `apps/api/app/router.py:13,33` already `include_router(slicer_admin_router)`. The new POST is added to the **same** router object — no new `include_router` needed.
10. **Slicer module Boundaries (RESPECT):** `apps/api/app/modules/slicer/README.md` § Boundaries — "no DB/Alembic schema; append-only on-disk JSON; first-write-wins, concurrency-safe." The sidecar manifest stays on-disk (OD-4 — no Alembic). Honour first-write-wins/atomic semantics for the manifest + intent write.
11. **DTOs (EXTEND module):** `slicer/schemas.py:134-196` holds the 33.1 `AdminProfile*` DTOs (all `extra="forbid"`, no-leak fence). Add the import-response + rejection-detail models here, same fence.
12. **Defensive-policy reversal triggered (NAME IT):** the vendored dir's **read-only-at-runtime posture** (config docstring `:113-118`; SCP § 2.7) is reversed by this write slice. Per the repo's NFR-carve-out-reversal discipline this is a **named decision (Decision AL / OD-2)** contained to 33.2 — surface it in the import-service module docstring citing Decision AL + the old read-only rationale, mirroring how 33.1's selector reversal cited EST-DISPLAY-1.
13. **FE import surface (EXTEND):** `ProfileInventoryGrid.tsx:157` inert `ImportPlaceholder`; `hooks/useAdminProfiles.ts` reserves `invalidateQueries(["admin","profiles"])` for exactly this story; `ProfilesPage.tsx` fails-closed on error. No member-selector change in this story (the catalog selector is read-only over availability; import is admin-only).

### Cache-topology enumeration (per [[feedback_scp_pre_enumeration_phase]] § B — FE mutation story)

| Concern | Source: this story (import mutation) | Source: 33.1 (`useAdminProfiles`, `["admin","profiles",printerRef]`) |
|---|---|---|
| Staleness budget (`staleTime`) | n/a (mutation, no cached read of its own) | `staleTime: 0` + `refetchOnMount: "always"` — points to FR21-PROFILE-INVENTORY-1 (admin must see true state). Unchanged. |
| Retry policy | **No auto-retry on the import POST** — a write must not silently re-fire; the admin re-submits explicitly. Points to NFR21-OBS-1 (one audit event per real import) + admin-fails-closed (UX § E). | Default; admin grid fails closed/visible (error panel + Retry). Unchanged. |
| Cache propagation on mutations | **`invalidateQueries(["admin","profiles"])` on success** → grid refetches, cell flips offerable. This is the key contract 33.1 reserved (the two columns AGREE — 33.1 explicitly left the propagation hook for 33.2). | Reserved the key; `staleTime:0` guarantees the refetch is fresh. |
| Cache eviction on route exit | None (admin-only surface; no cross-route contamination). | None. Unchanged. |
| Cache seeding on this route | None. | None. |

Columns **AGREE** (33.1 pre-reserved the invalidation contract) → simple reuse; the one call-out is **no-auto-retry on the write** (pointed to the one-audit-event + fail-closed contracts, not to a framework default).

### Magic-constant discipline (per [[feedback_scp_pre_enumeration_phase]] § C)

- **`_MAX_PROFILE_BYTES = 1 MiB` (AC-4):** points to the contract "an intent triple is a small JSON object, far below the 500 MB STL `_MAX_FILE_BYTES`" — an explicit safety bound, NOT a reuse of the STL cap; marked arbitrary-but-bounded (revisit only if a real triple exceeds it). **Not** justified by "matches some other cap."
- **`manifest_version = "1"` (AC-9):** points to the **OD-4 sidecar contract v1**, not to a peer version string.
- **No-auto-retry on the import POST:** points to NFR21-OBS-1 (exactly one audit event per real import) + admin-fails-closed, not to a React Query default.
- **Compatibility map values (TPU = {standard}, etc.):** unchanged from 33.1's `compatibility.py` (Q5 operator decision) — this story does **not** re-declare them; it enforces the existing SoT. Any NEW concrete slot the operator wants importable is **data (gate G2)**, surfaced before fixtures, never guessed from "what resolves."

### Architecture / constraints

- **Decision AL** (arch.md:2900-2917): in-place vendored-tree write (OD-2) + two import gates (structural resolve OD-3 ∧ compatibility OD-7) + on-disk sidecar manifest (OD-4, no DB) + structural provenance safety + configs RW-mount as a **write-slice-only HC2 item**. Deploy-safety: vendored profiles are *data* on the shared volume → no SW-DEPLOY-1 overlay rebuild.
- **Decision AK** (arch.md:2878-2898): the read this story writes to; `compatibility.py` stays the compat SoT (AC-10).
- **OD-6 re-slice DEFERRED** (gated on EST-PARSE-1): do NOT enqueue any slice on import. The estimate-freshness/backfill pipeline state (paused on `unparseable_time`, recent parser commits) is **independent of this slice** — verify it only if a future story turns on OD-6.
- Backend rules: `Annotated` DI, `current_admin` default-value dep, namespaced logger, no `os.environ`, ruff `E,F,W,I,B,UP,SIM,RUF` line-length 100, TDD red→green. Frontend rules: `import type`, `noUncheckedIndexedAccess` (no `!`), `@/*` alias, network via `api()` only, i18n mandatory, no inline hex, ESLint `--max-warnings=0`, `afterEach(cleanup)`.

### Project Structure Notes

- **New backend:** `apps/api/app/modules/slicer/import_service.py` (staged-source + validate + atomic publish + manifest; or fold into `admin_router.py` if small) + `apps/api/tests/test_admin_profiles_import.py`. **Edited:** `slicer/admin_router.py` (POST + `build_slot` manifest-label), `slicer/schemas.py` (import DTOs), `slicer/resolver.py` *(only if `StagedProfileSource` lives there — no `resolve()` change)*, `core/audit.py` (`KNOWN_ENTITY_TYPES`).
- **New FE:** `apps/web/src/modules/admin/hooks/useImportProfile.ts` + an import-control component + visual specs. **Edited:** `ProfileInventoryGrid.tsx` (live import affordance), `en.json`/`pl.json`, `api-types.ts` (import DTO types), `apps/web/tests/visual/api-stubs.ts`.
- **No** `_PUBLIC_ROUTES` edit, **no** Alembic, **no** `config.py` slot, **no** `workers/render/` change, **no** `resolver.py` reshape, **no** `configs`-repo commit. SW-DEPLOY-1 not triggered.

### References

- Epics: [Source: _bmad-output/planning-artifacts/epics.md#Story 33.2] (lines 3851-3868).
- Architecture: [Source: _bmad-output/planning-artifacts/architecture.md#Initiative 21] — Decision AL (2900-2917), Decision AK (2878-2898), pre-enumeration table (2867-2876).
- PRD: [Source: _bmad-output/planning-artifacts/prd.md#Initiative 21] — FR21-PROFILE-IMPORT-1 (1953), FR21-COMPAT-1 (1952), FR21-SELECTOR-1 (1954), NFR21-PROVENANCE-1 (1958), NFR21-NO-422-1 (1959), NFR21-AUTH-1 (1961), NFR21-OBS-1 (1962).
- UX: [Source: _bmad-output/ux/profile-admin-selector-ux-2026-06-04.md] — § B.1 (import affordance), § D (TPU import-rejection worked example), § E (admin fails closed/visible), § H Q4 (import-affordance default).
- SCP: [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md] — § 6 (PROFILE-ADMIN-2 acceptance boundaries), § 5 (OD-2/3/4/6/7), § 3 (deploy-safety), § 7 (operator dev-go gate).
- Shipped: 33-1-readonly-admin-profile-inventory.md (the read this story writes to); `apps/api/app/modules/slicer/{admin_router.py,compatibility.py,resolver.py,schemas.py}`, `apps/api/app/core/audit.py`, `apps/api/app/modules/sot/{admin_router.py,admin_service.py}`, `apps/api/app/core/config.py`, `apps/api/app/core/auth/csrf.py`, `apps/web/src/modules/admin/{ProfileInventoryGrid.tsx,hooks/useAdminProfiles.ts,ProfilesPage.tsx}`.
- Memory: [[feedback_scp_pre_enumeration_phase]] — pre-enumeration + cache-topology + magic-constant discipline applied above.

### Operator / data / config gates (surface BEFORE dev-go)

- **G1 — HC2 portal-content RW mount (config, VERIFY — potential blocker).** The import writes from the **api container** into `/data/content/slicer/vendored/...` (same `portal-content` volume the api already writes model uploads to via `admin_upload_file`). Strong signal the mount is already RW, but Decision AL flags it explicitly: **confirm the api container mounts the vendored subtree RW** (not a separate RO mount). If a change is needed it is a `~/repos/configs/docker-compose-recipes/...` (+ api compose) edit — an **HC2 boundary item, NOT a 3d-portal commit** — and a hard blocker for the live-write ACs (AC-8/15). Backend scaffolding + tests-with-fakes proceed without it.
- **G2 — Sample/fixture intent triples (data).** A successful-import test/baseline needs at least one **valid intent-triple JSON** for a compatible slot (e.g. PETG·strong or TPU·standard) that resolves against the live system tree. Confirm the operator supplies (or points to) a representative triple; do **not** synthesize one that "happens to resolve" against an unconfirmed shape (magic-constant discipline). The incompatible-rejection tests need no operator data (any well-formed triple aimed at TPU·aesthetic suffices).
- **G3 — Operator dev-go (process, SCP § 7).** Code implementation stays BLOCKED until the explicit operator dev-go (mirrors Init 20 scope-of-approval). This spec is doc-only.
- **G4 — Destructive/write-risk note.** First in-product write to the vendored tree (the read-only-posture reversal). Risks bounded by: atomic publish (AC-8), validate-before-publish (AC-7), unrelated-bundle byte-stability (AC-11), no append-only-store edit (AC-23). No `bundle_hash` / provenance invariant is weakened.
- **No-re-slice deferred invariant (OD-6):** import does NOT trigger a re-slice in this story; do not enqueue. Carried as AC-23.

### Review / fix-up budget

- External review: **Gemini** default (`laura-gemini-review`) on the focused diff. **Codex** fallback/high-stakes — this slice has a **data-integrity + on-disk-write adjacency** (provenance invariants, first vendored-tree write), so a Codex countersignature is warranted if Gemini surfaces any provenance/atomicity doubt. Tag `# gemini-review:`/`# codex-review:` per AGENTS.md.
- Fix-up budget 0-4, likely surfaces: (a) atomic-write/rollback edge (temp leftover on crash mid-publish); (b) staged-source validation accidentally writing to the live append-only bundle store (must use a throwaway/no-persist store); (c) manifest-vs-`compatibility.py` dual-SoT temptation (AC-10 — keep the live gate in code); (d) audit payload leak fence (no profile body / g-code); (e) i18n parity / Polish diacritics on the rejection-reason keys.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context) — repo-local BMAD dev agent, bmad-dev-story flow.

### Operator / data gate resolution (G2/G3, recorded at dev-start)

- **G3 — operator dev-go RECEIVED** (Michał via Laura/controller, 2026-06-05; SCP § 7 satisfied). Code implementation unblocked; work proceeds on branch `feat/E33.2-validated-profile-import-publish`.
- **G2 — sample/fixture intent triples (RESOLVED for tests via real bench-derived data).** The operator's "TPU / Rosa Flex" direction maps to the real Orca filament profile **`Rosa3D Flex 96A`** (`filament_type: ["TPU"]`, `filament_max_volumetric_speed: ["3.5"]`), already vendored as a bench-derived test fixture: `apps/api/tests/fixtures/slicer/system/rosa3d_flex_96a.json` + `apps/api/tests/fixtures/slicer/intents/creality-k1-max-microswiss-hf/TPU/standard.json`. The successful-import unit/integration tests drive the import path against this **real-derived** TPU·standard triple (and the existing PLA·standard `Rosa3D PLA Starter` triple) — NOT a synthesized "happens-to-resolve" guess. The incompatible-rejection tests (TPU·aesthetic / TPU·strong) need no operator data.
- **G1 — HC2 portal-content RW-mount + live vendored-tree write smoke: OPEN (runtime gate).** This dev host has no `/data/content` mount and no access to the live Fenrir/.190 vendored tree, so the in-product live-write ACs (AC-8/AC-15) cannot be smoke-tested here. The backend writes via a `VendoredProfileSource`-rooted path that is overridable in tests (tmp dirs), so all import/publish/manifest/atomicity behavior IS verified against a tmp vendored root. The live RW-mount confirmation + a real import against the .190 vendored tree remain an operator/runtime gate — see Completion Notes "Remaining gates".

### External fallback review (2026-06-05) — findings + fix evidence

Review source: **fallback Hermes review subagent** (the Gemini and Codex CLIs were unavailable this run, so the default Gemini / Codex-countersignature route could not execute — NOT a Gemini or Codex review; recorded honestly per the review-routing contract). Verdict: **REQUEST_CHANGES** with two blockers, both now FIXED on this branch.

- **[Critical] Path traversal on the `printer_ref` write path — FIXED.** `printer_ref` was an unconstrained form string joined into `VendoredProfileSource.intent_path()`, so an admin caller could publish outside `<root>/intents` via `../../tmp/evil`, separators, or an absolute path. Fix (two layers, defense-in-depth):
  1. Syntactic gate `is_safe_printer_ref()` (`import_service.py`) — a single-segment charset `^[a-z0-9][a-z0-9._-]*$` that rejects every separator (`/`,`\`), parent ref (`..`), absolute path, leading dot, and whitespace; wired into the endpoint as gate **(2b)** returning structured **422 `invalid_printer_ref`** BEFORE any write.
  2. Containment assert `is_within_intents_root()` (`import_service.py`) — resolves the final publish target and asserts it stays at/below `<root>/intents`; wired as gate **(4b)** right before publish (belt-and-braces).
  Tests: `is_safe_printer_ref` accept/reject table (incl. `../../tmp/evil`, `..`, `/etc/passwd`, `a/b`, `a\b`, `.hidden`, empty, spaces); `is_within_intents_root` containment; endpoint-level parametrized traversal tests proving **422 + structured `invalid_printer_ref` + tree byte-identical + no escape-marker file written + no temp leftover**.
- **[High] intent+manifest publish not atomic/rollback-safe — FIXED.** `publish_intent()` wrote the intent then the manifest as two independent atomic writes, so a manifest-write failure left a live intent paired with a stale/missing manifest. Fix: `publish_intent()` now **stages BOTH files to fsynced temp siblings first, then commits intent then manifest; if the manifest commit fails the just-committed intent is rolled back** to its prior state (restored bytes on a re-import, removed on a fresh import). So the (intent, manifest) pair is published as a unit — on any failure the tree is byte-identical to before and no temp remains. Tests inject a manifest-only `os.rename` failure and assert byte-identical tree + correct prior pair preserved + no temp leftovers, for **both** a fresh import (nothing left behind) and a re-import (prior `first` intent+manifest restored, not the failed `second`/TPU re-import).

### Debug Log References

Targeted gates run during dev (all from `apps/api/` venv unless noted):

- `python -m pytest tests/test_audit.py -q` → **5 passed** (T1; AC-12 entity-type registration).
- `python -m pytest tests/test_slicer_import_service.py -q` → **11 passed** (T2/T3; staged validation seam + atomic publish + manifest).
- `python -m pytest tests/test_admin_profiles_import.py -q` → **16 passed** (T4/T6; endpoint auth/gates/atomicity/provenance/e2e selector).
- `python -m pytest tests/test_admin_profiles_inventory.py -q` → green (AC-14 manifest-label surfacing; 33.1 parity preserved).
- `python -m pytest tests/test_route_enforcement_gate.py -q` → **3 passed** (AC-2; no `_PUBLIC_ROUTES` edit).
- Aggregate of the five backend suites above → **47 passed** (warnings only: pre-existing JWT key-length + sqlite datetime-adapter deprecations).
- Broader backend regression `pytest -k "slicer or admin_profiles or audit or route_enforcement"` → **541 passed, 2 skipped** (after evolving the `test_slicer_worker.py` admin-router route-surface fence to admit the new sanctioned POST — the one regression this resume surfaced and fixed; ORCA_SMOKE_TEST-gated cases skipped).

**Post-fallback-review fix gates (2026-06-05):**

- `pytest tests/test_slicer_import_service.py` → **27 passed** (was 11; +16: path-safety helpers, containment, rollback-safe publish fresh + re-import manifest-failure).
- `pytest tests/test_admin_profiles_import.py` → **24 passed** (was 16; +8 endpoint traversal: parametrized bad `printer_ref` + no-escape-write proof).
- `pytest test_slicer_import_service + test_admin_profiles_import + test_audit + test_admin_profiles_inventory + route-surface fence` → **69 passed**.
- Broader regression `pytest -k "slicer or admin_profiles or audit or route_enforcement"` → **565 passed, 2 skipped** (was 541; +24 new tests, 0 failures).
- `ruff check` + `ruff format --check` on the four changed API files/tests → **All checks passed / already formatted**.
- `git diff --check` → clean.
- `ruff check app/ tests/test_admin_profiles_import.py tests/test_slicer_import_service.py tests/test_audit.py` → **All checks passed**; `ruff format` applied to changed files.
- FE (`apps/web/`): `npm run typecheck -- --pretty false` → pass; `npm run lint -- --max-warnings=0` → **exit 0** (only the pre-existing eslint-plugin-react "React version not specified" notice, not a counted warning).
- FE vitest (relevant files): `npx vitest run ProfileInventoryGrid.test.tsx hooks/useImportProfile.test.tsx profiles-i18n.test.ts ProfilesPage.test.tsx` → **23 passed** (4 files). `window.scrollTo` stderr is pre-existing jsdom/router noise, not a failure.
- `git diff --check` → clean.

### Completion Notes List

**Implemented (code-side green):**

- **T1 (AC-12):** added `slicer_profile` to `KNOWN_ENTITY_TYPES` (`app/core/audit.py`) with the existing one-line convention comment; RED test first (`test_audit.py`).
- **T2 (AC-7):** `StagedProfileSource(VendoredProfileSource)` + `validate_import()` in new `app/modules/slicer/import_service.py` — reuses `resolve()` **verbatim** against the real system tree while feeding the uploaded partials from memory; a `_NoPersistBundleStore` guarantees the validation path neither reads nor writes the live append-only bundle/snapshot store. `resolve()` itself unchanged.
- **T3 (AC-8/9/10):** `publish_intent()` writes the validated partials + a v1 sidecar `.manifest.json` via an atomic **tmp→fsync→os.rename UPSERT** (deliberately NOT the append-only `os.link` of `bundle_store`, since a re-import overwrites in place). Manifest carries a point-in-time compat snapshot — NOT a second SoT (AC-10).
- **T4 (AC-1..8,12,13):** `POST /api/admin/profiles/import` on the existing `slicer/admin_router.py`, `current_admin`-gated, no `_PUBLIC_ROUTES` edit, CSRF automatic. Gate order: size 413 → shape 422 `invalid_partial` → compatibility 422 `incompatible_for_material` → structural resolve 422 (classified `ResolveReason`) → atomic publish → manifest → audit (`slicer_profile.import`, leak-fenced after-payload: no profile body / g-code) → 201 + `AdminProfileSlot`. Structured rejection detail via new `ProfileImportRejection` schema.
- **T5 (AC-14):** additive read-only `VendoredProfileSource.manifest_label()` (deferred import, no `resolve()` reshape) + `build_slot(portal_label=…)`; the inventory loop surfaces the manifest label, all other slot fields unchanged.
- **T6:** `test_admin_profiles_import.py` (16) + `test_slicer_import_service.py` (11) drive the real bench-derived `Rosa3D Flex 96A` TPU triple against a **real tmp vendored root** (production wiring), covering 403/401/413, incompatible-not-written + byte-identical tree, malformed/resolve-failure rejections, success+manifest+audit, AC-11 unrelated-`bundle_hash` byte-stability + no append-only-store write, and the AC-15 end-to-end selector projection.
- **T7 (AC-16..20):** `useImportProfile()` mutation (multipart via `api()`; `retry:false` per cache-topology; `onSuccess → invalidateQueries(["admin","profiles"])`). `ProfileInventoryGrid` `ImportControl` replaces the inert placeholder — live file-picker on compatible-not-imported cells only (incompatible cells carry no action), localized rejection reason surfaced (reuses 33.1 `reason.*` for shared categories + new `import.error.*`), **no optimistic flip**. Zero inline hex (reuses `--color-destructive`/`text-destructive`, `border-border` tokens). i18n keys `modules.admin.profiles.import.*` added to en + pl with parity + Polish diacritics (covered by `profiles-i18n.test.ts` prefix match). Stale `import_placeholder*` keys removed.
- **`api()` enhancement:** `apps/web/src/lib/api.ts` now skips the forced `application/json` content-type when the body is `FormData` (browser sets the multipart boundary) — lets the import ride the wrapper and keep the CSRF header + 401-retry instead of a raw `fetch`. Non-breaking (no FormData currently flows through `api()`).
- **T8:** FE tests — `useImportProfile.test.tsx` (multipart shape, CSRF header, no JSON content-type, portal_label conditional, invalidation, no-auto-retry, `importRejectionCategory`) + `ProfileInventoryGrid.test.tsx` (live-enabled action, no action on incompatible, multipart POST, localized rejection + no offerable flip, too_large mapping).

**Remaining gates / open items (status kept at `review`, NOT `done`):**

1. **T9 / AC-21 — Visual baselines: PARTIAL.** The existing `admin-profiles.spec.ts` mixed-status grid baseline was intentionally updated after visual inspection to include the live `Importuj` control in the PETG/Standardowa not-imported cell; full Playwright visual regression later passed. However, the spec's dedicated **three-state** import visual baselines (import affordance open / rejection / post-import offerable × 4 projects) plus explicit per-PNG `baseline-reviewed:` sign-offs are still not fully represented as separate cases, so AC-21 remains a review follow-up rather than `done`.
2. **T10 / AC-22 — Full gate: GREEN; 3× determinism still not separately run.** Controller reran full `infra/scripts/check-all.sh` after review fixes: `.hermes/run-logs/check-all-E33-2-controller-v3-after-review-fix-20260605_101039.log` → **16/16 all green** (API ruff/check/pytest, web typecheck/build/lint/vitest/visual, worker tests, settings/env/lock/secrets). The spec's extra 3× identical pytest+vitest determinism loop was not run separately.
3. **External review: FALLBACK APPROVED; contracted Gemini/Codex still pending CLI availability.** First fallback Hermes review returned REQUEST_CHANGES with two blockers; both were fixed and tested. A second independent fallback Hermes re-review then returned **APPROVE** (targeted import-service/import-endpoint tests: 51 passed). This is still not claimed as the contracted Gemini default review + Codex countersignature because those CLIs were unavailable on `.170`.
4. **G1 — live RW-mount + real .190/Fenrir import smoke: OPEN runtime gate.** Not verifiable on this dev host (no `/data/content` mount, no live vendored tree access). No live-write smoke was performed; no such claim is made.

### File List

**Backend — new:**
- `apps/api/app/modules/slicer/import_service.py` (+ fallback-review fixes: `is_safe_printer_ref` / `is_within_intents_root` traversal guards; rollback-safe two-phase `publish_intent` with `_stage_temp` / `_restore_or_remove`)
- `apps/api/tests/test_slicer_import_service.py` (+ path-safety + containment + rollback-publish tests)
- `apps/api/tests/test_admin_profiles_import.py` (+ endpoint traversal tests)

**Backend — modified:**
- `apps/api/app/core/audit.py` (KNOWN_ENTITY_TYPES + convention comment)
- `apps/api/app/modules/slicer/admin_router.py` (import endpoint, DI seam, `build_slot` portal_label, inventory manifest surfacing, `ProfileInventorySource.manifest_label`; + fallback-review fix: gates (2b) `printer_ref` path-safety 422 + (4b) containment assert)
- `apps/api/app/modules/slicer/resolver.py` (additive read-only `VendoredProfileSource.manifest_label`)
- `apps/api/app/modules/slicer/schemas.py` (`ProfileImportRejection`)
- `apps/api/tests/test_audit.py` (slicer_profile coverage)
- `apps/api/tests/test_admin_profiles_inventory.py` (`_FakeSource.manifest_label`)
- `apps/api/tests/test_slicer_worker.py` (evolved the admin-router route-surface fence from 33.1 read-only to the 33.2 sanctioned ONE-GET + ONE-POST write surface)

**Frontend — new:**
- `apps/web/src/modules/admin/hooks/useImportProfile.ts`
- `apps/web/src/modules/admin/hooks/useImportProfile.test.tsx`

**Frontend — modified:**
- `apps/web/src/lib/api.ts` (FormData-safe content-type)
- `apps/web/src/lib/api-types.ts` (`ProfileImportRejection`)
- `apps/web/src/modules/admin/ProfileInventoryGrid.tsx` (live `ImportControl`)
- `apps/web/src/modules/admin/ProfileInventoryGrid.test.tsx` (33.2 affordance tests)
- `apps/web/src/modules/admin/ProfilesPage.tsx` (thread `printerRef`)
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` (import.* keys; removed stale placeholder keys)

**BMAD artifacts — modified:**
- `_bmad-output/implementation-artifacts/33-2-validated-profile-import-publish.md` (this record)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (33-2 status)


**Gate evidence added by controller after Codex contracted review:**

- Operator gave explicit live runtime smoke GO on 2026-06-05 after dev/review gate recovery.
- Gemini CLI availability check: binary present (`gemini 0.45.1`), but contracted review unavailable:
  - default model attempt failed with `429 RESOURCE_EXHAUSTED / MODEL_CAPACITY_EXHAUSTED` for `gemini-3-flash-preview`;
  - direct focused-diff `gemini-2.5-pro` attempt did not produce a verdict before the bounded wait.
  This is recorded as reviewer/tool availability, not as a code approval.
- Codex contracted review (pasted focused diff, no sandbox) initially returned `REQUEST_CHANGES` with two Important findings:
  1. audit failure after publish could leave an unaudited live intent+manifest pair;
  2. raw multipart `file.filename` was stored in manifest/audit metadata.
- Fixes applied:
  - endpoint snapshots prior intent+manifest before publish and restores the pair if required `record_event(...)` fails after publish;
  - `sanitize_original_filename(...)` keeps basename-only, replaces control/percent escapes, trims and truncates before both sidecar manifest and audit payload.
- Targeted Codex-fix test: `python -m pytest apps/api/tests/test_admin_profiles_import.py -q` → **26 passed**.
- Full gate after Codex fixes: `.hermes/run-logs/check-all-E33-2-post-codex-fix-20260605_140515.log` → **16/16 all green**.
- Codex re-review after fixes: `.hermes/run-logs/codex-rereview-E33-2-after-fix-20260605_141455.log` → **APPROVE**, Critical=None, Important=None, Minor=None.
- Remaining before story `done`: ff-merge/deploy/live import smoke evidence on `.190`.
