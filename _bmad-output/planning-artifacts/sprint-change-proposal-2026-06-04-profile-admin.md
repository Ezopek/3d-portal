---
title: "Sprint Change Proposal — Initiative 21 (Admin-Managed Orca Process Profiles + User-Facing Selector Options)"
type: sprint-change-proposal
status: approved-but-corrected         # operator go 2026-06-04 ("Ok, możemy ruszać z pracami"); approval scoped to planning-artifact appends (PRD/arch/epics/sprint-status), NOT to code implementation. DOMAIN-MODEL FRAMING CORRECTED 2026-06-06 — see corrected_by below.
corrected_by: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md
correction_summary: |
  This SCP's central framing — that the fixed `printer_ref × material_class × quality_tier` resolver slot grid
  and the uploaded intent triple are the PRIMARY/canonical admin & profile model — is product-model-wrong and
  was corrected by the 2026-06-06 profile-model-correction SCP. The fixed slot grid is reclassified as a
  TRANSITIONAL compiled-intent / resolver projection (MVP compatibility surface), NOT the canonical model. The
  canonical model is separate Orca-like building blocks (MachineProfile / ProcessProfile / FilamentProfile) plus
  product-facing offers/chains (PrintProfileOffer / ProfileChain). Shipped Stories 33.1 (read-only inventory)
  and 33.2 (validated import/publish) are PRESERVED, not reverted; their safety foundations carry forward. Story
  33.3 (grid lifecycle) is FROZEN/BLOCKED pending the correction; the next slice is re-pointed to a small
  profile-library inventory CRUD (process profiles first) → PrintProfileOffer/ProfileChain. Read § 5/§ 6/§ 9 of
  the 2026-06-06 SCP. The OD-7 "compatibility map over the grid" below is reclassified as an interim expression
  of block/chain compatibility, kept as the live gate behind the projection.
proposed_by: Claude (BMAD correct-course discovery, repo-local author of record, 2026-06-04)
proposed_at: 2026-06-04
approved_by: operator (Michał / Ezop, ITCM controller/Laura)   # OD-1 resolved: fixed grid + material/process compatibility mapping; UX-PROFILE-1 required
approved_at: 2026-06-04
skill: bmad-correct-course
mode: batch-presented (operator-pragmatic; phase-1 discovery artifact requesting operator go before PRD → arch phase entry)
change_scope_classification: moderate
  # New initiative (Init 21), new epic E33, ~3-5 stories. Reuses the existing slicer resolver +
  # EST-TIERS-1 availability contract + existing admin module/auth/upload patterns. The first slice
  # is read-only (no write surface, deploy-clean). Write/import slice carries the only novel risk
  # (vendored-dir write posture + configs RW-volume coordination). No DB schema proposed for v1.
kanban_card: "t_ce1927cf — 3DPORTAL-PROFILE-ADMIN: admin-managed Orca process profiles and user-facing selector options"
predecessor_initiative: 20             # STL Slicer Estimates (Epic E32) — this builds directly on its resolver + EST-TIERS-1 bridge
supersedes_bridge: "EST-TIERS-1 (deferred-work.md) — the disk-presence-derived quality-tier availability gate becomes admin-managed"
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                      # EXTEND on approval (Initiative 21 — FR21-* + NFR21-*)
  - _bmad-output/planning-artifacts/architecture.md             # EXTEND on approval (Initiative 21 — Decision(s) AK+)
  - _bmad-output/planning-artifacts/epics.md                    # EXTEND on approval (Initiative 21 H2 + Epic E33 + stories)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # EXTEND on approval (epic-33 + story rows, status: backlog)
  - _bmad-output/implementation-artifacts/deferred-work.md      # EST-TIERS-1 entry — the recorded product decision this initiative fulfils
  - apps/api/app/modules/slicer/resolver.py                     # VendoredProfileSource — the read contract the panel manages the inputs of
  - apps/api/app/modules/slicer/router.py                       # GET /api/estimates/quality-tiers — the EST-TIERS-1 availability seam to admin-ify
  - apps/api/app/modules/admin/router.py                        # /api/admin — the admin router a profiles endpoint mounts under
  - apps/web/src/modules/admin/AdminTabs.tsx                    # the admin tab nav a "Profiles" tab joins
  - ~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml  # configs-side: portal-content volume RW mount (HC2 coordination, write slice only)
trigger:
  source: |
    Operator selected the next product direction (2026-06-04, controller/Laura ITCM): an admin panel
    that imports, names, and manages Orca process profiles, so the user-facing Files/STL estimate
    selector exposes admin-approved portal options. Kanban continuity card t_ce1927cf.
  evidence_class: |
    Grounded in shipped code on origin/main, not blue-sky. The slicer resolver (Epic E32 / Story 32.1)
    already consumes vendored Orca intent partials from a fixed on-disk layout; the EST-TIERS-1 bridge
    (shipped) already derives per-tier availability by resolving each portal quality tier and reports
    which are importable. Today those profiles are hand-placed on the .190 portal-content volume as a
    one-time bench export; only `standard.json` exists for the catalog printer/material, so Aesthetic /
    Strong resolve to `unsupported_material_class` and are disabled in the user selector. This
    initiative replaces the hand-placement + disk-presence gate with an admin-managed surface.
runtime_dependency_note: |
    Estimate FRESHNESS on .190 is independent of this initiative's read-only first slice but gates the
    import→re-slice path (see § 5 OD-6 and § 8). The t_81a1e5bd backfill was paused on
    `unparseable_time`; recent commits (55c0caa parse Orca subsecond duration; 8583deb repair fallback
    after non-zero slicer exit; 2ecc308 aggressive admesh repair) target exactly that parser/repair
    path. VERIFY current backfill/parser state before scoping any slice that enqueues slices.
---

# Sprint Change Proposal — Initiative 21 (Admin-Managed Orca Process Profiles)

> ⚠️ **DOMAIN-MODEL FRAMING CORRECTED (2026-06-06).** This SCP treats the fixed
> `printer_ref × material_class × quality_tier` slot grid + uploaded intent triple as the **primary/canonical**
> admin & profile model. That framing is **product-model-wrong** and has been corrected by
> **`sprint-change-proposal-2026-06-06-epic33-profile-model-correction.md`**. Read that SCP first. In short: the
> fixed slot grid is **transitional compiled-intent / resolver projection** (kept as MVP compatibility, not the
> canonical model); the canonical model is **separate Orca-like blocks** (MachineProfile / ProcessProfile /
> FilamentProfile) **+ offers/chains** (PrintProfileOffer / ProfileChain). Shipped 33.1/33.2 are **preserved,
> not reverted**; **Story 33.3 is FROZEN/BLOCKED**; the next slice is re-pointed to a small profile-library
> inventory CRUD (process profiles first) → PrintProfileOffer/ProfileChain. The § 5 OD-7 "compatibility map
> over the grid" is reclassified as an interim expression of block/chain compatibility (kept as the live gate).

**Date:** 2026-06-04
**Skill:** `bmad-correct-course` (phase-1 discovery → phase-2 PRD on operator go)
**Predecessor initiative:** Initiative 20 (STL Slicer Estimates, Epic E32 — shipped through `0.1.0+8583deb`).
**Kanban card:** `t_ce1927cf` (3DPORTAL-PROFILE-ADMIN).

## 1. Issue Summary

**Triggering observation.** Orca process/intent profiles are the load-bearing input to every per-part
estimate, yet they are managed **outside the product**: an operator hand-places exported JSON onto the
`.190` portal-content volume under `SLICER_VENDORED_PROFILES_DIR`. There is no in-product way to see
what is installed, import a new profile, or expose a new quality tier to users. Today only
`standard.json` exists for `creality-k1-max-microswiss-hf` · PLA, so a member who picks **Aesthetic**
or **Strong** would hit a `PresetResolveError` → HTTP 422; the EST-TIERS-1 bridge currently hides that
by disabling those tiers in the selector.

**Problem framing.** Give the operator a first-class **admin panel to import, name, and manage Orca
process profiles**, and make the **user-facing Files/STL selector expose only admin-approved portal
options**. The EST-TIERS-1 deferred-work entry already records this as the intended successor:
*"This is a **bridge** until the admin profile-management panel exists (the surface that will let an
operator import/manage Orca intent profiles, at which point Aesthetic/Strong become genuinely
available rather than gated)."* This initiative is that panel.

**Explicit non-goals (product framing, locked):**
- This is **process/intent profiles only** — printer + print-quality recipes. It is **NOT** filament
  inventory, ordering, spool availability, or cost (that is Spoolman / Init 19, a separate SoT). A
  Spoolman *override* still layers onto a resolved filament at resolve time (Story 32.5); the admin
  panel does not own or duplicate that.
- It must **preserve existing estimate / backfill / provenance safety**: the content-addressed
  `bundle_hash`, the append-only bundle/estimate stores, the `source_system_tree_hash` provenance
  snapshot, and the loud-classified resolver failures are invariants this initiative builds on, never
  edits.

**What this supersedes.** The EST-TIERS-1 availability signal stops being "derived purely from disk
presence" and becomes "derived from the admin-managed profile inventory." The *user-facing contract is
unchanged* — `GET /api/estimates/quality-tiers` keeps returning `{quality_tier, available, reason}`
(`apps/api/app/modules/slicer/router.py:100-143`) and the selector keeps consuming it
(`apps/web/src/modules/estimates/hooks/useQualityTierAvailability.ts`). Only the *source of truth*
behind "available" gains an admin-managed front end.

## 2. Pre-enumeration save (per feedback-scp-pre-enumeration-phase)

Reuse + extend, never parallel-implement. Findings to bake into the downstream story specs:

1. **Resolver read contract (the thing the panel manages the inputs of).**
   `apps/api/app/modules/slicer/resolver.py:114-159` — `VendoredProfileSource` reads
   `<root>/system/*.json` (system tree, keyed by Orca `name`) and
   `<root>/intents/<printer_ref>/<material_class>/<quality_tier>.json` (the composite `{machine,
   process, filament}` user-partial triple). A missing intent file ⇒ classified
   `unsupported_material_class` (resolver.py:222-231), never a silent fallback. **An imported profile
   is, in resolver terms, an intent triple file dropped into that path.**
2. **Availability seam already exists — admin-ify, don't re-derive.**
   `GET /api/estimates/quality-tiers` (router.py:100-143) resolves each tier via the same
   `resolve_preset` seam and reports availability; `QUALITY_TIER_ORDER` (router.py:51) and FE
   `QUALITY_TIERS` (`apps/web/src/modules/estimates/lib/preset.ts:25-29`) are a **named FE↔BE
   contract** mirroring the backend `QualityTier` literal. The admin inventory read should return a
   **superset** of this (add provenance + import metadata) and the two must agree on resolvability.
3. **Admin auth guard — reuse.** `apps/api/app/core/auth/dependencies.py:76` `current_admin`
   (`_current_admin_dep`, role-claim `== "admin"`, 403 `admin_required`). The profiles router mounts
   under the existing admin router `apps/api/app/modules/admin/router.py:29` (`prefix=/api/admin`).
4. **Multipart upload pattern — reuse for the write slice.** `apps/api/app/modules/sot/admin_router.py:447-501`
   (`admin_upload_file`) + service `apps/api/app/modules/sot/admin_service.py:511-619`
   (`upload_model_file`, `_write_atomic`, 500 MB cap, `record_event` audit at :583-596). A profile
   import endpoint mirrors this shape (much smaller payloads — JSON, not STL).
5. **FE admin surface — extend.** Add a `"profiles"` tab to `apps/web/src/modules/admin/AdminTabs.tsx:6`
   (`ActiveTab` union) + a route under `apps/web/src/routes/admin/`; gate with
   `useAuth().isAdmin` (`apps/web/src/shell/AuthContext.tsx:67`), mirroring `users.tsx`/`invites.tsx`.
6. **Contracts/provenance the work must preserve (name the mechanism).**
   - `bundle_hash` reproducibility (resolver.py:74-111) — byte-pinned input order; changing it needs
     an SCP. Importing a profile must **not** perturb the hash of an unrelated already-persisted bundle.
   - `source_system_tree_hash` (resolver.py:300-319) — the provenance snapshot was **deliberately
     designed for in-place edits of vendored profiles** ("the vendored profiles are edited IN PLACE").
     So an admin write that mutates the system tree yields a *new snapshot identity* automatically —
     provenance safety is structural, not something the panel must re-invent.
   - Append-only bundle/estimate stores (no DB; AC-6). The slicer subsystem has **no Alembic schema**
     by design (slicer README § Boundaries). v1 should not introduce one (see OD-4).
7. **Defensive policy that would be *reversed* by a write surface — surface as a named decision.**
   The vendored dir is documented as **read-only at runtime** ("exported artifacts … never a live read
   of an external host at resolve time"; slicer README § Settings; `config.py:118`). An admin write
   path changes that posture. This is a deliberate, named decision (OD-2), not an incidental code
   change — and it is *contained to the write slice*, not the read-only first slice.
8. **No existing profile write surface.** Grep of `apps/api` confirms every `slicer_vendored_profiles_dir`
   reference is read-only consumption. Nothing to collide with; the write path is genuinely new.

## 3. Impact Analysis

### Epic impact
**New Initiative 21 / Epic E33** (project-global numbering — `epics.md` tail is Init 20 / Epic E32).
No existing epic is modified. Queues behind the in-flight estimate/parser stabilization per ITCM
convention.

### Artifact surface (on operator approval — NOT this run)

| Artifact | Action | Detail |
|---|---|---|
| `prd.md` | EXTEND | `## Initiative 21` H2: FR21-PROFILE-INVENTORY-1 (admin read of managed profiles), FR21-PROFILE-IMPORT-1 (validated import), FR21-SELECTOR-1 (user selector consumes admin-approved availability), **FR21-COMPAT-1 (material/filament-class ↔ process-profile compatibility mapping — neither admin panel nor user selector offers an incompatible material/process combination; admin panel surfaces compatibility status + reason; OD-1/OD-7)**, NFR21-PROVENANCE-1 (preserve bundle_hash + snapshot invariants), NFR21-NO-422-1 (no member-reachable resolve 422), **NFR21-UX-1 (admin/profile-selector surface is UX-designed — UX-PROFILE-1)**. |
| `architecture.md` | EXTEND | New Decision **AK** — admin profile-management surface: managed-inventory read over the resolver, import validation via the existing `resolve()` path, **material/process compatibility-map representation + enforcement (OD-7) layered over the fixed `QualityTier × material_class` grid**, on-disk metadata posture (OD-4), vendored-dir write posture (OD-2). |
| `epics.md` | EXTEND | `## Initiative 21` H2 + `#### Epic E33` + stories (see § 6). |
| `sprint-status.yaml` | EXTEND | `epic-33` + story rows, `status: backlog`. |
| `apps/api/app/modules/admin/` (or `modules/slicer/admin_router.py`) | NEW/EXTEND | Admin profiles router under `/api/admin`. Read slice is additive + read-only. |
| `apps/web/src/modules/admin/` + `routes/admin/` | NEW/EXTEND | Profiles tab + page. |
| `~/repos/configs/.../slicer-worker.yml` + api compose | COORDINATE (write slice only) | portal-content volume RW mount for the api container if the import writes to the vendored tree (HC2 boundary). |

### Deploy-safety property (important)
Vendored profiles are **data on the shared `portal-content` volume**, not code in the worker image.
An admin write to that volume is visible to the slicer-worker overlay **without an image rebuild**, so
this initiative does **not** trip the SW-DEPLOY-1 overlay-rebuild gate (no new slicer module). The
read-only first slice is a pure API+web change with the standard deploy path.

## 4. Recommended Approach

**Option 1 — Direct Adjustment (recommended).** Phase-1 discovery (this SCP) → operator go → Phase-2
PRD `## Initiative 21` append → Phase-3 architecture Decision AK + `epics.md` Epic E33 → sprint-planning
→ story cycle. Matches the Init 18/19/20 precedent (vanilla H2 append).

**Sequencing within the epic: read-first, write-second** (mirrors the proven Story 32.6 pattern, where
the read seam shipped and the enqueue was deferred). The first slice carries **zero** novel deploy/write
risk; all the genuinely new posture decisions (OD-2, OD-4) are isolated to the second slice.

**Scope envelope (proposed, lockable on approval):**
- ✅ IN: An admin-only read of the managed profile inventory (per printer/material/tier: imported?,
  resolvable?, **compatible?** + reason, provenance, portal label). A validated import path that writes
  an intent triple into the resolver's source so a new tier becomes genuinely available **only for
  material-compatible slots**. A material/filament-class ↔ process-profile **compatibility mapping**
  over the fixed grid (OD-1 resolved, OD-7) so neither the admin panel nor the user selector ever offers
  an incompatible material/process combination (e.g. TPU only gets TPU-compatible process profiles). The
  user selector consuming admin-approved + compatibility-filtered availability (built on EST-TIERS-1 —
  the availability *signal* gains a compatibility dimension; the `{quality_tier, available, reason}` DTO
  shape is preserved, `reason` carries the incompatibility cause).
- ❌ OUT (deferred, named): arbitrary admin-defined tier labels / free-text taxonomy (OD-1 resolved to
  the **fixed enum grid + compatibility mapping**, not free-text relabeling); a printer registry /
  multi-printer management (stays single default printer ref, OD-5); real-Orca slice-validation at
  import time (structural resolvability only, OD-3); any change to Spoolman inventory/cost; any change to
  the `bundle_hash` input order or the append-only stores.

## 5. Open Decisions (safe defaults applied; one flagged for operator)

| # | Decision | Safe default applied | Why safe / blocking? |
|---|---|---|---|
| **OD-1** | Does admin define **arbitrary** tier labels, or fill the **fixed** `quality_tier × material_class × printer_ref` grid? | **RESOLVED — ACCEPTED (operator, 2026-06-04): fixed grid, *with* compatibility mapping.** Admin imports profiles into existing `{aesthetic, standard, strong} × {PLA,PETG,PCTG,TPU}` slots and controls which are exposed; "admin-approved labels" = admin controls *availability* of the existing named tiers, not free-text relabeling. **Critically, the fixed grid is NOT assumed fully/uniformly populated:** the grid carries an explicit **compatibility mapping** that binds/limits which process (quality-tier) profile slots are valid for a given filament/material class. Some `(material_class, quality_tier)` cells are legitimately *incompatible* and must never be offered. **Worked example:** TPU is specific enough to require dedicated process profiles; the admin panel and the user selector must only allow TPU-compatible process/tier choices for TPU (and must not offer a PLA/PETG-derived process slot as if it were TPU-valid). | **RESOLVED — operator accepted fixed grid.** Arbitrary free-text labels remain deferred to a follow-up (would churn the FE↔BE `QualityTier` named contract — preset.ts + models literal + bundle paths → large/risky). The accepted scope **adds** a material/filament-class ↔ process-profile **compatibility constraint** layer over the fixed enum grid (see PROFILE-ADMIN-1/2 acceptance boundaries and OD-7). |
| **OD-2** | Where does an imported profile get **written**? | **Write the validated intent triple directly into `SLICER_VENDORED_PROFILES_DIR/intents/...`** (one source of truth; provenance snapshot already binds content hash on in-place edits). A staging/approval two-step is deferred. | Safe — the provenance mechanism (resolver.py:300-319) was built for in-place edits. **Write slice only**; needs configs RW-volume coordination (HC2). Read slice unaffected. |
| **OD-3** | Does import validation require a **real Orca slice**, or **structural resolvability**? | **Structural resolvability** (run the existing `resolve()` merge/normalize/required-keys with the default `NullCliValidator`) — this is exactly what determines the user-facing 422/availability today. Real-Orca CLI validation (worker-only) is an optional async follow-up. | Safe — availability == resolvability is the live contract. Honest boundary; avoids coupling import to the slicer-worker overlay. |
| **OD-4** | Where does admin **metadata** live (portal label, importer, timestamp, original filename, status)? | **On-disk sidecar manifest** in the vendored tree (consistent with the slicer subsystem's no-DB / append-only posture) **+ reuse the existing admin audit log** (`record_event`, action `slicer_profile.import`/`.delete`) for who/when. **No Alembic migration in v1.** | Safe — matches subsystem precedent (no slicer DB schema). DB-table alternative noted but not recommended for v1. |
| **OD-5** | Multi-printer? | **No.** v1 manages profiles for the single existing `slicer_default_printer_ref` / `CATALOG_ESTIMATE_PRINTER_REF` (`creality-k1-max-microswiss-hf`). A printer registry is a separate future initiative. | Safe — single-printer is the live arbitrary-until-multi-printer baseline; don't conflate. |
| **OD-6** | Does the import path **trigger a re-slice** so new estimates appear? | **Not in the read slice; optional in the write slice** — and gated on the estimate parser/backfill pipeline being healthy (EST-PARSE-1 / t_e4afd776). Import can reuse the existing EST-RECOMPUTE-1 `POST /api/estimates/recompute` per (stl_hash, preset) rather than a new bulk enqueue. | Safe — avoids a bulk-enqueue surface; respects the paused-backfill runtime state. Verify parser state before scoping. |
| **OD-7** | How is the **material/filament-class ↔ process-profile compatibility mapping** (from the OD-1 acceptance) represented and enforced? | **Default proposal (confirm at PRD/arch phase): the compatibility map is a first-class, explicit declaration — not implied by mere file presence.** Resolvability (`resolve_preset`) remains *necessary* but is **not sufficient**: a cell is offered to users only when it is BOTH structurally resolvable AND declared compatible for that material class. The map most naturally lives alongside the fixed-grid contract (extend the FE↔BE `QualityTier`/`material_class` named contract with a per-material allowed-tier / compatibility table; backend is the source of truth, FE mirrors it — mirroring the existing `QUALITY_TIER_ORDER`↔`QUALITY_TIERS` parity). The admin sidecar manifest (OD-4) records per-slot compatibility status + reason. **TPU example:** TPU's allowed process slots are declared explicitly so a PLA-class process profile cannot be surfaced as TPU-valid even if it happens to resolve. | **Follow-on from the resolved OD-1 — needs PRD/arch confirmation of representation, not a product go/no-go.** Safe default = reuse the existing named-contract + parity-test pattern; no new free-text taxonomy. Enforcement boundary is specified in PROFILE-ADMIN-1/2 acceptance (below). The exact concrete TPU-compatible slot set is an admin-data question, deferred to the data/PRD phase. |

**OD-1 is now RESOLVED** (operator, 2026-06-04): **fixed grid accepted**, *with* an explicit
material/filament-class ↔ process-profile **compatibility mapping** (TPU and similar materials require
dedicated, declared-compatible process profiles; incompatible cells are never offered). This keeps the
feature in the "fill the existing grid" envelope (small, safe) rather than "design a free-text profile
taxonomy" (large, deferred), while adding a bounded compatibility-constraint layer. The downstream
representation/enforcement of that mapping is tracked as **OD-7** (a PRD/arch-phase representation
question, not a product go/no-go). All remaining open decisions (OD-2..OD-7) have safe defaults
supported by shipped-code precedent and can proceed under those defaults unless the operator overrides.

## 6. Recommended next slice / story

**Epic E33 — Admin-Managed Orca Process Profiles.** Proposed story breakdown (lock at epics phase):

### ▶ Recommended FIRST slice — **PROFILE-ADMIN-1: read-only admin profile inventory** (safe, deploy-clean)

Establish the admin surface + the managed-inventory read contract before any write path. This is the
smallest safe vertical and is independent of the estimate-freshness/parser runtime state.

**Backend (additive, read-only):** `GET /api/admin/profiles?printer_ref=…` (admin-gated via
`current_admin`), returning, per `(printer_ref, material_class, quality_tier)` slot:
`{imported: bool, resolvable: bool, compatible: bool, reason, portal_label, provenance: {snapshot_hash,
source_system_tree_hash, orca_version}}`. Reuses the EST-TIERS-1 `resolve_preset` resolvability logic
and `VendoredProfileSource` provenance — **no new resolve logic**, just an admin-facing superset
projection — plus the OD-7 compatibility map to compute `compatible` and the structured `reason` when a
slot is resolvable-but-incompatible (e.g. a non-TPU process profile occupying a TPU slot). Mounts under
the existing admin router. Not in `_PUBLIC_ROUTES`.

**Frontend:** new `"profiles"` tab in `AdminTabs.tsx` + `routes/admin/profiles.tsx`, gated on `isAdmin`,
rendering the grid (printer × material × tier) with imported / resolvable / **compatibility** status and
**human-readable compatibility reason** (why a slot is or isn't offerable — incompatible material class,
unresolved, not imported), plus provenance. Read-only list view; en+pl i18n parity. **The frontend
surface (this admin grid and the downstream user selector) is a UX-designed surface, not a raw status
dump — see § 9 UX work item UX-PROFILE-1.**

**Acceptance boundaries (PROFILE-ADMIN-1):**
- AC: non-admin → 403; the route is authenticated and absent from `_PUBLIC_ROUTES`.
- AC: the inventory's `resolvable`/`reason` for every tier **agrees** with what
  `GET /api/estimates/quality-tiers` returns for the same printer/material (one source of truth — a
  shared test asserts parity).
- AC (compatibility surfacing): the admin panel surfaces, per slot, a clear **compatibility status and
  reason** — every slot is classified as offerable (imported ∧ resolvable ∧ compatible) or not, and when
  not, the panel shows *why* (not imported / not resolvable / **incompatible for this material class**).
  A resolvable-but-incompatible slot (e.g. a PLA-class process profile sitting in a TPU slot) is shown
  as **not offerable** with an explicit incompatibility reason — it must never read as "available."
- AC (no incompatible offer — read-slice scope): the admin inventory **never marks an incompatible
  `(material_class, quality_tier)` slot as offerable**, and a shared test asserts the projection feeding
  the user selector excludes incompatible slots (so the user-facing selector cannot surface a
  TPU-incompatible process choice for TPU, nor vice-versa). Selector parity with this projection is
  asserted by test.
- AC: provenance fields project from the resolved bundle's snapshot; **no Orca-internal keys, no file
  paths, no g-code** leak into the DTO (mirrors the existing no-internal-leak fence).
- AC: **read-only** — no write/upload/multipart surface; no new on-disk write; no configs change; no
  slicer-worker module → SW-DEPLOY-1 overlay rebuild NOT triggered.
- Out of scope: import/upload, delete, re-slice, metadata mutation, printer registry, label editing.
  (The compatibility *map* is consumed read-only here; **authoring/editing** the map is PROFILE-ADMIN-2/3.)

### Then — **PROFILE-ADMIN-2: validated import/publish write path** (carries the novel risk)
Multipart import of an intent triple → validate via `resolve()` (OD-3 structural) **AND validate
material/process compatibility (OD-7)** → write into the vendored intents tree (OD-2) → sidecar manifest
(incl. per-slot compatibility status + reason, OD-4) + audit (OD-4). This slice owns the vendored-dir
write-posture decision and the configs RW-volume coordination (HC2). Defer the optional re-slice
trigger (OD-6) — and gate it on EST-PARSE-1 being resolved.

**Acceptance boundaries (PROFILE-ADMIN-2 — compatibility-relevant):**
- AC (no incompatible publish): an import that targets a slot whose profile is **not compatible with the
  declared material/filament class** (e.g. a non-TPU process profile imported into a TPU slot) is
  **rejected with a clear, structured reason** and is NOT published/exposed — structural resolvability
  alone does not make a slot offerable (OD-7: resolvable ∧ compatible). The rejection reason is surfaced
  in the admin panel.
- AC (selector invariant preserved end-to-end): after a successful import, the user-facing selector
  offers the newly-published slot **only if** it is compatible; an incompatible or
  compatible-but-unpublished slot never becomes a member-reachable choice (no member-reachable 422 and
  no incompatible material/process combination offered).
- AC: the compatibility decision and reason for each imported slot are persisted to the sidecar manifest
  and reflected by the PROFILE-ADMIN-1 inventory read (single source of truth).

### Optional — **PROFILE-ADMIN-3: manage (rename label / disable / delete)** profile lifecycle, once import exists.

## 7. Implementation Handoff

**Blocker — UPDATED 2026-06-04 (operator go):** Downstream planning-artifact appends (PRD /
architecture / epics / sprint-status) are now **APPROVED and COMPLETED** (Init 21 / FR21-* + NFR21-* in
`prd.md`; Decisions AK + AL in `architecture.md`; Epic E33 + Stories 33.1-33.3 in `epics.md`; `epic-33`
+ `33-1..33-3` + `ux-profile-1` `backlog` rows in `sprint-status.yaml`). **ALL code implementation
remains BLOCKED pending an explicit operator dev-go** — mirroring the 2026-05-31 (Init 20)
scope-of-approval discipline (approval is scoped to planning artifacts, NOT to `apps/` / `workers/` /
production code or configs). **No `apps/` / `workers/` / configs / production code was touched in the
planning run.**

**Handoff sequence (post-approval):**
1. **OD-1 RESOLVED** (operator, 2026-06-04: fixed grid **+ compatibility mapping**). Remaining product
   input is data-shaped, not go/no-go: confirm the concrete per-material compatible-slot set (e.g. which
   process slots are TPU-compatible) during the PRD/data phase, and confirm the OD-7 representation.
2. **`bmad-ux` → UX-PROFILE-1** — UX designer designs the admin profile grid + the user-facing selector
   surface (compatibility status/reasoning, disabled-vs-hidden incompatible slots) **before/with** FE
   story authoring (see § 9).
3. **`bmad-prd` (update intent)** — append `## Initiative 21` H2 (FR21-* incl. FR21-COMPAT-1 / NFR21-*
   incl. NFR21-UX-1).
4. **Manual append `architecture.md`** — Decision AK (incl. OD-7 compatibility-map representation).
5. **Manual append `epics.md`** — Epic E33 + stories PROFILE-ADMIN-1..3.
6. **`bmad-sprint-planning`** — sequence E33 (read slice first).
7. **`bmad-create-story` → `bmad-dev-story`** on PROFILE-ADMIN-1.
8. **Configs-side coordination** — only when PROFILE-ADMIN-2 lands the write path (portal-content RW mount).

**Success criteria:** An admin can see, in-product, which Orca process profiles are installed and
resolvable per printer/material/tier (slice 1); import a new validated profile so a previously-gated
tier (Aesthetic/Strong) becomes genuinely available to users with no member-reachable 422 (slice 2),
retiring the EST-TIERS-1 hand-placement workaround — all while the `bundle_hash`, append-only stores,
and provenance snapshots remain byte-stable for unaffected bundles.

## 8. Verification performed (this discovery run)

- **Routing:** Invoked `bmad-help` (catalog `_bmad/_config/bmad-help.csv`); confirmed
  `bmad-correct-course` (CC) is the catalog's designated path for a significant brownfield change, and
  that PRD/architecture/epics are `required` gates this discovery feeds. Honored the
  feedback-scp-pre-enumeration-phase memory (§ 2 above).
- **Grounding (read-only, cited):** resolver vendored layout + classified-failure contract
  (`resolver.py:114-159`, `:222-231`); EST-TIERS-1 availability seam (`router.py:51,100-143`;
  `useQualityTierAvailability.ts`); FE selector named contract (`preset.ts:25-41`); admin auth guard
  (`auth/dependencies.py:76`), admin router (`admin/router.py:29`), multipart upload + audit pattern
  (`sot/admin_router.py:447-501`, `sot/admin_service.py:511-619`), role enum
  (`db/models/_enums.py:10-13`), FE admin tabs/role gate (`AdminTabs.tsx:6`, `AuthContext.tsx:67`),
  vendored-dir config + read-only posture (`config.py:118`), provenance-on-in-place-edit
  (`resolver.py:300-319`); the EST-TIERS-1 recorded product decision (`deferred-work.md`).
- **Numbering:** `epics.md` tail = Init 20 / Epic E32 → this is Init 21 / Epic E33 (no collision).
- **Runtime caveat noted, not asserted:** estimate freshness/backfill on .190 was paused on
  `unparseable_time` (t_81a1e5bd / EST-PARSE-1 / t_e4afd776); recent commits 55c0caa/2ecc308/8583deb
  target that path — VERIFY current state before scoping any re-slice (OD-6). The read-only first slice
  does not depend on it.
- **Boundaries respected:** no code/deploy/commit; only this planning artifact was written.

## 9. UX work item (required — open)

**UX-PROFILE-1 — UX designer involvement is REQUIRED for the admin/profile-selector surface.**
(Operator directive, 2026-06-04.) Both frontend surfaces this initiative touches are decision-support
UIs over a constrained compatibility grid, **not** crude dropdowns or raw status dumps, and must be
designed by a UX designer (`bmad-ux` / Sally) before or alongside the FE story work:

1. **Admin profile grid (PROFILE-ADMIN-1/2/3).** How the `printer × material × tier` grid presents
   imported / resolvable / **compatibility** status and the *reason* a slot is or isn't offerable
   (incompatible material class, unresolved, not imported); how an incompatible slot is visually
   distinguished from an available one; how import/manage actions and their rejection reasons (incl.
   compatibility rejections from PROFILE-ADMIN-2) are surfaced.
2. **User-facing Files/STL process/material selector.** The core operator directive: the selector must
   **only ever offer compatible process/material combinations** (TPU gets only TPU-compatible process
   profiles, etc.), and must do so in a way that is good UX — a deliberate decision on whether
   incompatible/unavailable options are **disabled-with-explanation vs. hidden**, how the reason is
   communicated to the member, and how this reads against the existing EST-TIERS-1 availability behavior.
   This must not regress to a "crude dropdown."

**Status:** OPEN work item. Blocks finalizing the FE acceptance criteria for the selector and admin grid.
**Owner:** UX designer (`bmad-ux`), feeding FR21-COMPAT-1 / NFR21-UX-1 and the PROFILE-ADMIN-1/2 FE ACs.
**Dependency:** consumes the OD-7 compatibility-map contract (backend source of truth) — UX designs the
*surfacing*, not the underlying compatibility rules.
