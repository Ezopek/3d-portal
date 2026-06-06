---
title: "Sprint Change Proposal — Initiative 21 / Epic 33 Profile-Model Correction (Orca-like building blocks, not a fixed slot grid)"
type: sprint-change-proposal
status: proposed                       # repo-local correct-course author of record (Claude, 2026-06-06); planning-artifact correction only — NO code, NO commit, NO deploy
proposed_by: Claude (BMAD correct-course, repo-local author of record, 2026-06-06)
proposed_at: 2026-06-06
skill: bmad-correct-course
mode: correction (partial supersession of the 2026-06-04 profile-admin SCP's domain-model framing; preserves the shipped 33.1/33.2 value)
change_scope_classification: moderate
  # No new initiative/epic. Re-frames the Init 21 / Epic E33 domain model BEFORE Story 33.3 lifecycle work.
  # Freezes 33.3; re-points the next slice; demotes the fixed slot grid from "canonical model" to
  # "transitional compiled-intent projection". 33.1 (read-only inventory) + 33.2 (validated import/publish)
  # remain shipped on main — their value is preserved, only their model-status framing is corrected.
corrects: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md
  # Corrects the 2026-06-04 SCP where it treats the fixed `printer_ref × material_class × quality_tier`
  # resolver slot grid + the uploaded intent triple as the PRIMARY / canonical admin & profile model.
  # That framing is product-model-wrong. This SCP does NOT revert 33.1/33.2; it reclassifies the grid as a
  # compiled projection for the existing resolver/worker and re-targets future profile/admin UX onto
  # separate Orca-like building blocks (MachineProfile / ProcessProfile / FilamentProfile) plus
  # product-facing offers/chains (PrintProfileOffer / ProfileChain).
predecessor_initiative: 20             # STL Slicer Estimates (Epic E32) — the resolver + EST-TIERS-1 bridge the grid compiles into
related_artifacts:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-04-profile-admin.md   # CORRECTED (supersession/correction banner added)
  - _bmad-output/planning-artifacts/prd.md                      # current-state anchor patched (Initiative 21)
  - _bmad-output/planning-artifacts/architecture.md             # current-state anchor patched (Initiative 21 — Decisions AK/AL transitional note)
  - _bmad-output/planning-artifacts/epics.md                    # current-state anchor patched (Initiative 21 — 33.3 freeze + model-correction banner)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # 33.3 frozen/blocked; top + epic-33 + 33-3 comments updated; 33.1/33.2 history preserved
  - _bmad-output/implementation-artifacts/33-1-readonly-admin-profile-inventory.md       # shipped (done) — preserved; reclassified as compiled-intent projection read
  - _bmad-output/implementation-artifacts/33-2-validated-profile-import-publish.md        # shipped (done) — preserved; reclassified; its safety foundations carried forward
  - _bmad-output/implementation-artifacts/33-2-closeout-retro-2026-06-05.md               # source of the preserved 33.2 safety foundations (validation/atomic-publish/audit/manifest/perm/smoke)
  - apps/api/app/modules/slicer/resolver.py                     # VendoredProfileSource — the compiled-intent projection target (read-only reference, NOT edited)
  - apps/api/app/modules/slicer/admin_router.py                 # GET/POST /api/admin/profiles (shipped 33.1/33.2; read-only reference, NOT edited)
constraints_honored:
  - "Modified only repo-local BMAD/planning/status artifacts under _bmad-output/."
  - "No apps/ / workers/ / infra/ / runtime-config / code / migration / test / package / deploy changes."
  - "No commit, push, deploy, restart, or live smoke."
trigger:
  source: |
    Operator/controller (Laura ITCM) product correction recorded on Kanban (t_533dd579, t_44f0b0d3) and in the
    durable Laura Wiki research (transcribed verbatim in § Appendix A): the current Init 21 / Epic 33 artifacts
    treat the fixed resolver slot grid (`printer_ref × material_class × quality_tier`) and the uploaded intent
    triple as the PRIMARY admin/profile model. Orca profiles must instead be modeled like Orca itself — separate
    MachineProfile, ProcessProfile, and FilamentProfile libraries/blocks, plus product-facing offers/chains. The
    fixed slots may remain as an MVP compatibility / compiled projection for the current resolver/worker, but
    future admin/profile UX must not treat them as the canonical model. This correction must land BEFORE any
    Story 33.3 lifecycle work continues.
  evidence_class: |
    Grounded in shipped code (33.1/33.2 on origin/main, releases 0.1.0+…6a242e0 / +31bcf0c live on .190) and in
    filesystem/repo/API observation of real Orca profiles on Fenrir (~/repos/orca-profiles, system + user split).
    Confidence: medium pending operator acceptance of this correct-course; the correction is a domain-model
    re-framing, not a claim that the shipped code is broken.
---

# Sprint Change Proposal — Initiative 21 / Epic 33 Profile-Model Correction

**Date:** 2026-06-06
**Skill:** `bmad-correct-course`
**Initiative / Epic:** 21 / E33 (Admin-Managed Orca Process Profiles + User-Facing Selector Options)
**Corrects (partial supersession):** `sprint-change-proposal-2026-06-04-profile-admin.md` — domain-model framing only.
**Status of shipped work:** Story 33.1 `done`, Story 33.2 `done` (both on `main`, deployed). **Neither is reverted.**
**Action on Story 33.3:** **FROZEN / BLOCKED** pending acceptance of this correction.

> **Scope of this artifact.** Planning-/status-artifact correction ONLY. No application code, no `apps/` /
> `workers/` / `infra/` / configs / migrations / tests / package / deploy changes. No commit, push, deploy,
> restart, or live smoke performed by this run. This SCP re-frames the Init 21 domain model and re-targets the
> next slice; it does **not** change the behaviour of the shipped 33.1/33.2 surfaces.

---

## 1. Issue Summary

**Triggering correction.** The 2026-06-04 profile-admin SCP, and the Init 21 PRD / architecture / epics
sections it graduated into, treat the **fixed resolver slot grid** —
`printer_ref × material_class × quality_tier` with `{aesthetic, standard, strong} × {PLA, PETG, PCTG, TPU}`
and the uploaded **intent triple** (`{machine, process, filament}` partial) — as the **primary, canonical
admin and profile model**. The shipped Stories 33.1 (read-only admin inventory) and 33.2 (validated
import/publish) implement exactly that grid-first model.

**Why that is product-model-wrong.** Orca itself does not model profiles as a fixed grid of pre-fused
triples. It maintains **three separate, independently-versioned profile libraries** — *machine* (printer),
*process* (print/quality), and *filament* — where user profiles are **partial deltas that inherit from
system profiles**, and effective slicing is the *resolution of an inheritance chain* across all three plus
compatibility constraints. Real Orca profiles observed on Fenrir confirm this shape (see § Appendix A
evidence). A fixed `material_class × quality_tier` grid of opaque fused triples:

- **collapses three orthogonal libraries into one cell**, so the operator cannot manage a process profile
  independently of the machine/filament it happens to be paired with;
- **hides inheritance and compatibility** (the very things that make an Orca chain valid), forcing the model
  to re-discover them as ad-hoc "compatibility map" patches over the grid (the OD-7 layer in the 2026-06-04
  SCP is exactly this symptom);
- **does not extend** to the natural future product surfaces — a process-profile library the operator curates,
  member-facing *offers* over compatible chains, and a Spoolman-bridged filament selection.

**What this correction does.** It demotes the fixed slot grid from *canonical domain model* to **transitional
compiled-intent / resolver projection** (an MVP compatibility surface for the existing resolver/worker, kept,
not deprecated), and establishes the **Orca-like separate-building-block model** as the canonical target for
all *future* admin/profile UX. It then re-points the next slice away from "more grid lifecycle" (the current
33.3) and toward a **small operator-facing profile-library inventory** (import/list/get/delete, process
profiles first), ahead of a `PrintProfileOffer` / `ProfileChain` offer layer.

**Non-goal of this SCP.** It is *not* a rewrite of shipped code, *not* a revert of 33.1/33.2, and *not* a
demand to build a full Orca profile manager next. It is a model-framing correction plus a re-sequenced,
deliberately small next slice.

## 2. What is wrong with the current (grid-as-canonical) framing — precisely

| Current artifact framing | Problem | Corrected framing |
|---|---|---|
| Fixed `printer_ref × material_class × quality_tier` grid is the **admin model** (PRD Init 21 Overview; epics E33; Decisions AK/AL). | Treats a *compiled resolver input layout* as the *domain model*. The grid is what the resolver reads, not how profiles are authored or how Orca structures them. | Grid = **compiled-intent projection** for the resolver/worker. Canonical model = three separate blocks + chains + offers. |
| Uploaded **intent triple** (`{machine, process, filament}` fused partial) is the unit of import (33.2). | Fuses three independently-inheriting Orca libraries into one opaque artifact; loses per-block identity, inheritance, and reuse. | Import **separate Orca profile blocks** (process / filament / machine), each with its own identity, `inherits` chain, and settings id. The triple becomes a *compiled* output of a selected chain, not the import unit. |
| Compatibility is an **OD-7 "compatibility map" patched over the grid**. | Re-implements, as a side table, the compatibility that Orca already expresses via `filament_type` / `compatible_printers` / inheritance. | Compatibility is a **property of the blocks and the chain** (filament `material_type`/`compatible_printers`, machine capability, process↔filament validity), surfaced as offer compatibility. |
| "admin-approved labels" = admin toggles availability of fixed named tiers. | No path to a real **process-profile library** or to **member-facing offers** that are not 1:1 with the three hard-coded tier names. | `PrintProfileOffer` carries the member/admin label, visibility/default, compatible material categories, and a representative compiled chain — decoupled from the three fixed tier names. |

## 3. Corrected canonical domain model (Orca-like building blocks)

Future admin/profile UX is modeled on Orca's own structure: **separate libraries/blocks** plus
**product-facing offers/chains**. The fixed grid is a compiled projection of selected chains, not the model.

### 3.1 MachineProfile (printer) — *required for valid Orca slicing*

- **Why it exists:** Orca cannot slice without a machine profile; it defines the printer/hotend capabilities
  and constraints the chain is valid against. **A real, current Orca machine profile must back it** — e.g. the
  observed *AI Creality K1 Max (0.4 nozzle) — MicroSwiss HF Hotend Speed*, which **inherits** *Creality K1
  Max*. v1 stays single-printer (the existing `slicer_default_printer_ref` / `CATALOG_ESTIMATE_PRINTER_REF`,
  `creality-k1-max-microswiss-hf`); a printer registry remains deferred.
- **Fields:** stable ref / imported source path / resolved hash; Orca `name`, `printer_settings_id`,
  `inherits` chain; machine capabilities; **a future seam for machine-capability material restrictions** (a
  machine may later constrain which materials/processes it can run — recorded as a seam now, enforced later).
- **Portal role:** supporting reference for a valid chain; **not** a member-facing pick in v1.

### 3.2 ProcessProfile (print/quality) — *the most important portal-facing block*

- **Why it is primary:** the process/intent profile is the **main driver of gram/material estimates, print
  strategy, and the member-facing quality/process choice**. It is the block the operator most needs to
  curate, and the one the portal most needs to expose. Observed examples: *AI 0.20mm TPU — FlowTech*,
  *AI 0.20mm PCTG — MicroSwiss HF* (process-level variants).
- **Fields:** stable ref / imported source path / resolved hash; Orca `name`, `print_settings_id`, `inherits`
  chain; layer height, wall/infill/support strategy, speed/flow-related choices; visibility + intended
  product-quality semantics.
- **Governance (from Fenrir orca-profiles):** a user **process** profile must `inherit` from a **system
  process** profile, **not** from another user process profile — Orca may silently drop an invalid
  user-process inheritance. Import validation/classification must enforce/record this.
- **Portal role:** **primary member-facing quality choice** and the first block the inventory slice manages.

### 3.3 FilamentProfile — *needed by Orca; matters for speed / compatibility / time / Spoolman bridge*

- **Why it matters:** Orca needs a filament profile to slice, and it carries the properties that drive
  **maximum volumetric speed, printer/material compatibility, and time estimates**. It is also the **bridge to
  Spoolman material types**. Observed example: *AI Rosa3D Flex 96A Black* **inherits** *Generic TPU @System*,
  `filament_type: [TPU]`, `compatible_printers: [Creality K1 Max (0.4 nozzle)]`.
- **Fields:** stable ref / imported source path / resolved hash; Orca `name`, `filament_settings_id`,
  `inherits` chain; generic `material_type` / `filament_type` bridge; **optional** concrete Spoolman
  filament/spool association (below the generic category).
- **Portal role:** maps to a generic material category for validation/compatibility; concrete filament
  variants matter for speed/time/safety but are an override layer, not the primary member identity in v1.

### 3.4 ProfileChain — *the validated, compiled bundle*

- `machine_ref + filament_ref + process_ref` → a validated/resolved Orca-compatible bundle. **This is the
  compiled-intent path the existing resolver/worker already consumes** (the current intent triple is one
  compiled `ProfileChain`). It is where inheritance resolution + compatibility validation produce the
  byte-pinned input the `bundle_hash` is computed over.

### 3.5 PrintProfileOffer — *the member/admin-facing product surface*

- Member/admin **label, description, default/visibility**; **compatible material categories**; optional
  concrete filament/spool overrides; and a **representative `ProfileChain`** used for estimate slicing.
- This decouples what a member sees ("Strong PETG", "Aesthetic PLA", …) from the three hard-coded tier names
  and from the opaque grid cells, while still compiling down to a `ProfileChain` for the resolver.

### 3.6 Material taxonomy policy

- Use `material_type` / Spoolman material as a **generic category + validation bridge**, not full filament
  identity. Keep categories small and aligned: **PLA, PETG, PCTG, TPU** (later ABS/ASA).
- Map Orca `filament_type` and Spoolman material through a **normalized category table**; do **not** mint
  custom narrow material types per vendor/color/product. Allow concrete-filament overrides *below* the category
  layer.

### 3.7 Member UX boundary (later request-flow work — do NOT block profile work on it)

- Likely future member flow: *selected material/spool candidate → compatible quality / print-profile offers →
  estimate.* The final spool picker, color/stock/requestable UX, and material/spool-first request flow are
  **future request-flow work** and must not block the process/profile correction. The catalog member selector
  surfacing material (the shipped 33.1 Path-B decision) is a deliberate, documented EST-DISPLAY-1 reversal and
  is preserved; the broader spool picker is out of scope here.

## 4. Disposition of the shipped 33.1/33.2 slot-grid (the required migration/compatibility ruling)

**Ruling: the fixed slot grid is TRANSITIONAL — an MVP compatibility / compiled-intent projection for the
existing resolver/worker. It is KEPT, NOT deprecated, NOT reverted. It is NO LONGER the canonical domain
model.**

- **33.1 — read-only admin profile inventory (`GET /api/admin/profiles`):** preserved and shipped. Reclassified
  as a **read over the compiled-intent projection** (per-slot imported/resolvable/compatible/provenance). It
  remains valid and useful as an operator view of *what the resolver currently sees*. Future inventory UX
  (§ 6) is a **separate, additive** profile-library surface; it does not delete or rewrite this grid read.
- **33.2 — validated import/publish (`POST /api/admin/profiles/import`):** preserved and shipped. Reclassified
  as **publishing a compiled chain into the resolver's intent path**. Its safety foundations are explicitly
  carried forward (§ 7). The *import unit* changes conceptually for future work (separate blocks, not a fused
  triple), but the existing endpoint keeps working as the compiled-projection writer.
- **Compatibility (OD-7 map):** preserved as the live gate behind the projection
  (`compatibility.py` single SoT), reclassified as an **interim expression of block/chain compatibility** until
  the separate-block model carries compatibility natively (filament `material_type`/`compatible_printers`,
  machine capability, process↔filament validity).
- **Migration posture:** **no data migration is forced by this SCP.** The grid projection and the future
  block libraries are designed to **coexist**: the block/offer layer compiles *into* the same resolver intent
  path the grid already writes, so the resolver/worker, `bundle_hash`, append-only stores, and provenance
  snapshots are untouched. A later story may add a compatibility shim that derives grid cells from selected
  offers/chains; that is additive and deferred, not a breaking migration.
- **What is corrected, concretely:** the PRD/architecture/epics language that calls the fixed grid the *admin
  model* / *canonical model* is annotated (current-state anchors, § 12) to read "transitional compiled-intent
  projection; canonical model = separate Orca-like blocks + chains + offers (this SCP)."

## 5. Story 33.3 — FROZEN / BLOCKED

**Story 33.3 (PROFILE-ADMIN-3 — profile lifecycle: rename label / disable / delete over the fixed grid) is
frozen pending acceptance of this correction.** Its premise — lifecycle management of fixed-grid slots as the
management surface — is exactly the grid-as-canonical assumption being corrected. Continuing it would deepen
the wrong model and create rework once the separate-block inventory (§ 6) lands.

- `sprint-status.yaml` `33-3-profile-lifecycle-manage` stays machine-status `backlog` (no unknown-enum
  introduced) but its comment is updated to **⛔ FROZEN / BLOCKED pending Init 21 profile-model correction
  (this SCP); do NOT author or start**. No 33.3 story spec is to be created until this SCP is accepted and the
  next slice (§ 6) is sequenced.
- `epic-33` stays `in-progress` (33.1/33.2 shipped; the epic is mid-flight, now re-pointed); `epic-33` and the
  top `last_updated` comments are annotated with the correction.
- 33.1 and 33.2 rows keep their `done` status and full history — **untouched** except for nothing (their rows
  are not edited; their disposition is recorded here and in the current-state anchors).

## 6. Recommended next slice — small profile-library inventory (process first), then offers/chains

The next slice is deliberately **small, safe, and additive**, mirroring the proven read-first sequencing.
**Do NOT build a full Orca profile manager, an arbitrary N×M relationship editor, or the member spool picker.**

### ▶ NEXT — **PROFILE-LIB-1: operator-facing profile-block inventory CRUD (process profiles first)**

A small operator frontend + API surface so the operator is **not dependent on manual file placement only**:

- **add/import** an Orca profile block (**process profiles first**; filament + machine as supporting refs
  required for a valid chain);
- **list** imported profiles;
- **get** one profile's **curated metadata + validation state** (NOT a raw Orca JSON preview/viewer);
- **delete/remove** an imported profile.
- **Backend** validates, **classifies** (machine / process / filament), and processes profile metadata
  server-side, extracting **minimized metadata only**: `name`, source path / upload identity, `inherits`,
  settings id, `material_type` (filament), `compatible_printers` where present; and surfaces clear
  **success / error / usable / requires-attention** feedback.
- **UI** shows the **curated metadata + validation state**, not raw Orca JSON. **No raw Orca JSON
  preview/viewer.**
- **Enforce process-inheritance governance** (§ 3.2): a user process profile must inherit a *system* process
  profile; flag/reject invalid user-process inheritance.
- **Safety:** additive, read-mostly with a small validated write; reuses the shipped 33.2 safety foundations
  (§ 7); single-printer (no registry); no Spoolman mutation; no `bundle_hash`/append-only/provenance change;
  SW-DEPLOY-1 not triggered (data on the shared volume, no new slicer module).

### ▶ THEN — **PROFILE-OFFER-1: `PrintProfileOffer` / `ProfileChain` layer**

Model the canonical **offer/chain** surface (§ 3.4–3.5): `MachineProfileRef` + `FilamentProfileRef` +
`ProcessProfileRef` → validated `ProfileChain`; `PrintProfileOffer` with label/visibility/default, compatible
material categories, optional concrete-filament overrides, and a representative compiled chain that compiles
**into the existing resolver intent path** (so the resolver/worker/`bundle_hash` are preserved). The member
selector then consumes admin-approved, compatible offers.

### Deferred (named triggers) — record so the next story is NOT over-expanded

- Full Orca profile **manager UI** / raw Orca field editor / raw Orca JSON preview-viewer — deferred.
- Arbitrary **N×M relationship editor** — deferred until a heavy-relationship-UI design gate (§ 8) proves it
  worth the complexity.
- **Member spool picker** + color/tag/filter/requestable/"cemetery" spool design — future request-flow work
  (§ 3.7).
- Broad **material-catalog expansion** beyond PLA/PETG/PCTG/TPU(+ABS/ASA) — deferred.
- **Machine-capability material policy** beyond recording the seam (§ 3.1) — deferred.
- **Live mutation** of Orca profiles on Fenrir or of Spoolman — out of scope.
- Arbitrary admin-defined **free-text tier taxonomy** — remains deferred (OD-1, 2026-06-04 SCP).

## 7. Preserved 33.2 foundations (carry forward — do NOT re-litigate)

From the 33.2 closeout retro (`33-2-closeout-retro-2026-06-05.md`) and spec — these are validated and **kept**
by both the next slice and any future block/offer work:

- **`resolve()` reused verbatim, single SoT** — validation rides the real resolver against the real system
  tree; no second resolution path; `compatibility.py` stays the single live compat gate.
- **Atomic, write-before-write-safe publish** — gate order size → shape → compatibility → structural resolve
  → atomic publish → manifest → audit; reject leaves a byte-identical tree, no temp leftovers, two-phase
  intent+manifest commit with rollback.
- **Audit trail** — `slicer_profile.import` (and `.delete`) via `record_event`, leak-fenced (no Orca-internal
  bodies / g-code / file paths in DTOs or logs).
- **On-disk sidecar manifest** posture (no-DB / append-only subsystem) — point-in-time record, not a second
  SoT.
- **Permission/metadata preservation on the operator-managed shared tree** — preserve `ezop:ezop 664`
  owner/group/mode on every write (the `31bcf0c` runtime fix).
- **Live-RW-smoke methodology** — a green dev gate is necessary but not sufficient for write-path stories on a
  bind-mounted/operator-managed tree; a live RW smoke asserting file owner/group/mode + atomicity, run only
  after contracted-review APPROVE, is a deploy-GO precondition (AI-1/AI-4 in the 33.2 retro).

## 8. UX checkpoint required before heavy relationship UI

Before any heavy **relationship-building / N×M / offer-composition UI**, a **UX/admin design checkpoint** is
required (extends UX-PROFILE-1, `bmad-ux` / Sally). The PROFILE-LIB-1 inventory surface (import/list/get/delete
with curated metadata + validation state) is intentionally light and can proceed under the existing UX
direction; the offer/chain relationship UI must pass a design gate first so it does not regress into an Orca-GUI
clone or an unusable N×M matrix.

## 9. Deferred-work register (so future workers do not over-expand the next story)

The deferred list in § 6 is the authoritative register for this correction. Future story authors must treat
PROFILE-LIB-1 as **inventory CRUD only** (process-first), and PROFILE-OFFER-1 as the **offer/chain** layer —
neither expands into a full Orca manager, an arbitrary relationship editor, or the member request-flow / spool
picker without a fresh correct-course + UX gate.

## 10. Impact analysis

- **Epic/initiative:** no new epic; Init 21 / E33 re-pointed. 33.1/33.2 shipped value preserved; 33.3 frozen;
  next slice re-sequenced to PROFILE-LIB-1 → PROFILE-OFFER-1.
- **Code:** none in this run. The corrected model is designed to **compile into the existing resolver intent
  path**, so the resolver, `bundle_hash`, append-only bundle/estimate stores, and provenance snapshots remain
  invariants (NFR21-PROVENANCE-1 unchanged).
- **Deploy safety:** unchanged — vendored profiles are data on the shared `portal-content` volume; no new
  slicer module ⇒ SW-DEPLOY-1 not triggered.
- **Artifacts patched this run:** this SCP (new); a correction banner on the 2026-06-04 SCP; current-state
  anchors on `prd.md` / `architecture.md` / `epics.md` Initiative 21; `sprint-status.yaml` top + `epic-33` +
  `33-3` comments (33.3 frozen). 33.1/33.2 specs and rows are **not** edited (their disposition is recorded
  here + in the anchors).

## 11. Acceptance-criteria mapping (this correction)

| # | Criterion | Where satisfied |
|---|---|---|
| 1 | Repo-local BMAD/Claude artifact/status update written | This SCP + anchors + sprint-status (§ 12 of the task; § 10 here). |
| 2 | Separate machine/process/filament blocks, not fixed grid as canonical | § 3 (3.1–3.5). |
| 3 | Machine profiles required for Orca slicing, real current Orca machine, later machine-capability material restrictions | § 3.1. |
| 4 | Process profiles most important portal-facing block (grams/material estimates, strategy, quality choice) | § 3.2. |
| 5 | Filament profiles needed by Orca; max volumetric speed, compatibility, time estimates, Spoolman material mapping | § 3.3 + § 3.6. |
| 6 | State whether 33.1/33.2 grid is MVP/compiled-intent, deprecated, or needs migration/compatibility | § 4 (transitional compiled-intent; kept; coexist; no forced migration). |
| 7 | sprint-status / anchors warn 33.3 blocked pending model correction | § 5 + sprint-status `33-3` comment + epics/prd/arch anchors. |
| 8 | Concrete safe next slice: profile-library import/list/get/delete (process first; filament/machine supporting); then offers/chains | § 6 (PROFILE-LIB-1 → PROFILE-OFFER-1). |
| 9 | Existing 33.1/33.2 grid artifacts addressed with migration/compatibility note | § 4 + current-state anchors. |
| 10 | No app code changes | § Scope banner + § 10 + constraints_honored frontmatter. |

## 12. Verification performed (this correction run)

- **Routing:** correct-course is the canonical entry for a post-ship scope/model correction (AGENTS.md §
  "BMAD vanilla-first"). This SCP is the discovery+correction artifact; downstream PRD/arch/epics edits here
  are *narrow current-state anchors*, not a re-plan.
- **Grounding (read-only, cited):** 2026-06-04 SCP (full); Init 21 sections of `prd.md` (1937–2001),
  `architecture.md` (2861–2929, Decisions AK/AL), `epics.md` (3787–3885); `sprint-status.yaml` rows
  `epic-33`/`33-1`/`33-2`/`33-3`/`ux-profile-1`; 33.2 closeout retro; deferred-work EST-TIERS-1.
- **Boundaries:** no `apps/` / `workers/` / `infra/` / configs / migrations / tests / package / deploy edits;
  no commit/push/deploy/restart/smoke. Mechanical verification (git status/diff --check, grep readback, YAML
  parse) recorded in the run summary.

## Appendix A — Durable research input (Laura Wiki, verbatim; source unavailable on this host)

> Status: durable research context for 3d-portal and BMAD Epic 33/Profile Admin correct-course. Supersedes the
> shorter 2026-06-06 note and replaces unavailable scratch output from Kanban card 3d-portal/t_44f0b0d3.
>
> Executive recommendation: Do not build a full Orca profile manager as the next slice. Build an
> override-ready PrintProfileOffer / ProfileChain layer that imports or references separate Orca-like building
> blocks, then compiles selected chains into the existing slicer/resolver path.
>
> Recommended next slice sequence:
> 1. Treat Story 33.1/33.2 fixed `printer_ref × material_class × quality_tier` slots as a transitional
>    compiled-intent projection, not the canonical domain model.
> 2. Add a small operator-facing profile import/list inventory before or as the first part of offer-chain work:
>    add/import Orca profile blocks (especially process profiles); list imported profiles; fetch/get one
>    profile's curated metadata and validation state; delete/remove an imported profile; backend validates and
>    classifies profile type; extract minimized metadata (name, source path/upload identity, `inherits`,
>    settings id, `material_type` for filament, compatible printers where present); show clear
>    success/error/usable/requires-attention feedback; do not build a raw Orca JSON preview/viewer in the UI.
> 3. Introduce a canonical offer/chain model: `MachineProfileRef` (default K1 Max / MicroSwiss HF machine chain
>    for valid Orca slicing and machine capability constraints); `FilamentProfileRef` (maps to a generic
>    material category and concrete Spoolman-known filament/spool when needed); `ProcessProfileRef` (primary
>    member-facing quality/process choice and main driver of gram estimates); `PrintProfileOffer`
>    (member/admin-visible offer: label, visibility/default, compatible material categories, optional
>    concrete-filament overrides, and a representative compiled chain).
> 4. Keep member UX narrow for now: material/spool-first request flow and spool picker design are future
>    request-flow work. Do not block process/profile work on final color/stock/requestable UX.
> 5. Keep full N×M relationship editing, raw Orca GUI parity, and arbitrary profile-manager operations deferred
>    until a later operator/admin design gate proves they are worth the complexity.
>
> Evidence:
> - Kanban t_533dd579 records product correction: current 33.1/33.2 slot-grid import is technically safe but
>   product-model-wrong if treated as canonical. Correct-course must freeze 33.3 until it resolves the
>   Orca-like profile block model.
> - Kanban t_44f0b0d3 reported same direction: use override-ready PrintProfileOffer / ProfileChain, not a full
>   Orca manager.
> - Real Orca profile files observed on Fenrir: user/default profiles split by machine, filament, process; user
>   profiles are partial deltas inheriting system profiles. Machine example: AI Creality K1 Max (0.4 nozzle) -
>   MicroSwiss HF Hotend Speed inherits Creality K1 Max. Filament example: AI Rosa3D Flex 96A Black inherits
>   Generic TPU @System, has filament_type [TPU], compatible_printers [Creality K1 Max (0.4 nozzle)]. Process
>   examples: AI 0.20mm TPU - FlowTech and AI 0.20mm PCTG - MicroSwiss HF are process-level variants.
>   system/Creality inventory is much larger: typed machine, filament, process records.
> - User profiles are partial deltas; effective Orca slicing requires inheritance resolution against system
>   profiles, compatibility constraints, and sidecar/identity metadata.
> - Fenrir /home/ezop/repos/orca-profiles separates profiles/baseline and profiles/ai, with sync-pull/sync-push
>   and Spoolman sync. Governance says process profiles must inherit from a system process profile, not another
>   user process profile; Orca may silently drop invalid user-process inheritance.
> - Spoolman sample showed material categories PLA, PETG, PCTG, TPU plus concrete
>   vendor/name/color/subtype/density/diameter/weight/url data. Orca filament_type and Spoolman material should
>   map through generic material category, but concrete filament variants matter for speed/time/safety.
>
> Domain model should be:
> - MachineProfile: stable ref / imported source path / resolved hash; Orca name, printer_settings_id, inherits
>   chain; machine capabilities and future policy gates.
> - FilamentProfile: stable ref / imported source path / resolved hash; Orca name, filament_settings_id,
>   inherits chain; generic material_type / filament_type bridge; optional concrete Spoolman filament/spool
>   association.
> - ProcessProfile: stable ref / imported source path / resolved hash; Orca name, print_settings_id, inherits
>   chain; layer height, wall/infill/support strategy, speed/flow-related choices; visibility and intended
>   product quality semantics.
> - ProfileChain: machine_ref + filament_ref + process_ref; validated/resolved Orca-compatible bundle; compiled
>   intent path for existing resolver/worker.
> - PrintProfileOffer: member/admin label, description, default/visibility; compatible material types; optional
>   concrete filament/spool overrides; representative ProfileChain for estimate slicing.
>
> Material taxonomy policy: use material_type / Spoolman material as a generic category and validation bridge,
> not full filament identity; keep generic categories small and aligned (PLA, PETG, PCTG, TPU, later ABS/ASA);
> map Orca filament_type and Spoolman material through normalized category table; do not create custom narrow
> material types for every vendor/color/product; allow concrete-filament overrides below category layer.
>
> Member UX boundary: likely future flow selected material/spool candidate -> compatible quality / print-profile
> offers -> estimate; but this is later request-flow work; do not block profile/process correction on final
> spool picker UX.
>
> Minimum viable profile fidelity: high value now — process profile fidelity; representative
> machine+filament+process chain validity; material bridge; concrete-filament override hooks. Lower value now —
> full arbitrary graph editing; raw Orca field editor; member-visible machine/raw-filament pickers; exact
> print-time promises.
>
> Deferred: full Orca profile manager UI; arbitrary N×M relationship editor; final member spool picker;
> color/tag/filter/requestable/cemetery spool design; raw Orca field editing; broad material catalog expansion;
> machine capability policy beyond recording seam; live mutation of Orca profiles or Spoolman.
>
> Caveats: Direct Orca GUI export not exercised; evidence filesystem/repo/API based. User profile .info sidecars
> counted not deeply analyzed. Spoolman sample small/current-state only. Confidence medium pending BMAD
> correct-course acceptance.

### Appendix A.1 — Operator refinements (must be included)

- Before/alongside `PrintProfileOffer`/`ProfileChain`, include a small operator-facing **profile inventory
  CRUD** surface for Orca profile blocks, **especially process profiles**.
- **Not** a raw JSON preview/viewer.
- MVP operations: **add/import, list, fetch/get one curated metadata/detail, delete/remove**.
- Backend **validates, classifies, processes** profile metadata with clear success/error states.
- UI shows **curated metadata + validation state**, not raw Orca JSON.
- Relationship building/offers can remain later, but **process/profile addition needs a small frontend
  surface** so the operator is not dependent on manual file placement only.
