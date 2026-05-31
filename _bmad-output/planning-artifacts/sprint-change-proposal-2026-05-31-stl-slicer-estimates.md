---
title: "Sprint Change Proposal — Initiative 20 (STL Slicer Estimates, Per-Part MVP)"
type: sprint-change-proposal
initiative_scope: [20]
status: proposed
proposed_by: Claude (BMAD autonomous brainstorm discovery, 2026-05-31)
proposed_at: 2026-05-31
brainstorm_source: _bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md
execution_directive: |
  Phase-1 (analysis/discovery) complete. Brainstorm artifact finalized: per-STL estimates
  architecture grounded in proven CLI feasibility (PLA + TPU slices, g-code parsing,
  resolver script). MVP scope locked: linear-sum per-part, no whole-basket, no e-commerce,
  no Fenrir prod dependency, adaptive layer height gated. 10 open decisions + risk register
  ready for PRD/architecture handoff. Next: bmad-correct-course routing with this SCP as input.
mode: batch-presented (operator-pragmatic; phase-1 discovery artifact requesting PRD → arch phase entry)
change_scope_classification: moderate-to-large
  # New initiative, new epic E32, ~5-6 stories. Backend resolver + containerized slicer worker +
  # cache/invalidation logic. Frontend estimate UI integration. No DB schema; append-only estimate
  # records. Configs-side compose PR for slicer-worker container. High technical novelty.
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                         # extend (Initiative 20 H2 — FR20-* + NFR20-*)
  - _bmad-output/planning-artifacts/architecture.md                # extend (Initiative 20 H2 — Decisions AH + AI + AJ)
  - _bmad-output/planning-artifacts/epics.md                       # extend (Initiative 20 H2 + Epic E32 — ~5-6 stories)
  - _bmad-output/implementation-artifacts/sprint-status.yaml       # extend (epic-32 + story entries)
  - _bmad-output/brainstorming/brainstorming-session-2026-05-31-1926.md   # source discovery
  - ~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml  # configs-side container + network
  - infra/.env.example                                              # ORCA_VERSION, FENRIR_EXPORT_PATH slots
predecessor_initiative: 19
trigger:
  source: |
    Operator request 2026-05-31 to enumerate the STL slicer estimate scope before PRD authoring.
    Brainstorm (2026-05-31-1926.md, autonomous facilitation) covered problem statement, data
    model, resolver + slicer-worker architectures, invalidation rules, gated capabilities
    (adaptive layer height), and 10 open decisions. Per-STL linear-sum MVP is demoable
    (PLA + TPU feasibility proved; g-code metadata parsing confirmed).
  evidence_class: |
    CLI feasibility spikes on Fenrir WSL with OrcaSlicer 2.3.2 Linux AppImage. Qstool.stl
    (PLA + TPU slices) produce g-code with all required metadata lines. Orca user profiles
    are partial JSON; resolver script (orca_resolve_profiles.py) proves merge + normalization
    path end-to-end. Brainstorm sketch addresses ownership (Spoolman = inventory SoT; Orca
    tree = resolution recipe; portal = resolved bundles + cache).
business_decisions_aligned_pre_scp: null  # operator approval gate deferred to bmad-correct-course PRD session
---

# Sprint Change Proposal — Initiative 20 (STL Slicer Estimates, Per-Part MVP)

**Date:** 2026-05-31
**Skill:** `bmad-correct-course` (phase-1 discovery → phase-2 PRD)
**Predecessor initiative:** Initiative 19 (in-flight).

## 1. Issue Summary

**Triggering observation.** Estimate queries today require manual math (filament weight × assumed cost/g) or a separate Orca GUI invocation. The 2026-05-04 portal SoT design explicitly punted per-STL estimates as out-of-scope; this SCP is the promised discovery phase.

**Problem framing.** Owner-side decision-making needs "how long / how much filament for *this part*", which composes linearly to a request basket total. **Per-STL, not per-basket:** whole-plate slicing introduces packing as a variable, destroys per-part attribution, and is a different tool than a friends-&-family request assistant.

**Discovery evidence.**
- Brainstorming session `brainstorming-session-2026-05-31-1926.md` (71 ideas; 6 techniques; feasibility proof on Fenrir).
- Orca CLI headless with resolved profiles: PLA + TPU slices succeed; g-code metadata lines confirmed present.
- Resolver proof-of-concept (`orca_resolve_profiles.py`): merges system + user profiles, normalizes, emits CLI-acceptable JSON.

## 2. Impact Analysis

### Epic impact

**New Epic E32** (project-global numbering — Init 19 ends at E31) with ~5–6 stories. **No existing epic affected.** Init 20 queues behind Init 19 close-out per ITCM convention.

### Artifact surface

| Artifact | Action | Detail |
|---|---|---|
| `_bmad-output/planning-artifacts/prd.md` | EXTEND | New `## Initiative 20` H2 after Init 19. Functional + NFR (reproducibility, cache, soft-fail, Spoolman linkage, gating adaptive height). |
| `_bmad-output/planning-artifacts/architecture.md` | EXTEND | New `## Initiative 20` H2 with three Decisions: **AH** (resolver + inheritance merge + hashing), **AI** (slicer-worker container + job shape), **AJ** (cache/invalidation + cost-only arithmetic rule). |
| `_bmad-output/planning-artifacts/epics.md` | EXTEND | New `## Initiative 20` H2 + `#### Epic E32` + ~5–6 stories (32.1 resolver; 32.2 worker container; 32.3 cache/parse; 32.4 invalidation/recompute; 32.5 Spoolman mapping; 32.6 frontend integration). |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | EXTEND | New entries `epic-32` + story rows, all `status: backlog`. |
| `apps/api/app/modules/slicer/` | NEW PACKAGE | Backend resolver, worker client, cache logic, estimate models. |
| `apps/web/src/modules/estimates/` | NEW/EXTEND | Frontend estimate display, PrintIntentPreset selector, soft-fail UI. |
| `~/repos/configs/docker-compose-recipes/workers/slicer-worker.yml` | NEW CONFIG | Dedicated slicer-worker container (OrcaSlicer AppImage + deps); network topology. Configs-side PR (NOT 3d-portal commit). |
| `infra/.env.example` | MODIFY | `ORCA_VERSION`, `FENRIR_EXPORT_PATH` slots. |
| Fenrir bench | EXPORT STEP | One-time snapshot of resolved Orca machine/process/filament profiles from the system tree + user partials, exported as vendored artifacts (not a prod dependency). |

## 3. Recommended Approach

**Option 1: Direct Adjustment** — Phase-1 discovery → Phase-2 PRD → Phase-3 architecture + epics (vanilla H2 append pattern per AGENTS.md § Workflow expectations). Matches Init 18 / 19 precedent.

**Rationale:** Feasibility proved. Ownership topology (Spoolman = SoT, Orca = recipe, portal = bundles + estimates) locked. Resolver + worker architecture grounded, not blue-sky. No rollback needed. **OD-7 (cost-only arithmetic recompute)** and **OD-2 (dedicated worker vs extend render)** are the load-bearing open decisions for PRD/architecture to resolve; the rest are implementation-phase.

**Scope envelope (locked):**
- ✅ IN: Per-STL estimate (time, filament mass/mm/cm³, cost-info) for PLA/PETG/PCTG/TPU classes. Resolver (system+user merge, normalize, validate, hash). Containerized headless Orca worker. Cache keyed `(stl_hash, bundle_hash)` with explicit staleness. Spoolman override mapping (esp. TPU volumetric speed). PrintIntentPreset (user-facing) ↔ SlicerProfileBundle (internal) separation. Estimate invalidation on bundle change / Orca upgrade / STL edit. Cost-only arithmetic recompute (not re-slice).
- ❌ OUT: Adaptive/variable layer height (gated; proved negative). Whole-basket/plate slicing. Multi-printer optimization. E-commerce. Live Fenrir in production. Retain g-code (parse-and-discard). Additional material classes (post-MVP; no schema change).

## 4. Detailed Proposals

### 4.1 PRD extension

**Action:** Append new `## Initiative 20 — STL Slicer Estimates (Per-Part MVP)` H2 after Init 19 H2. Use `bmad-edit-prd` skill.

**Content outline:**
- Status: 🚧 planning (started 2026-05-31).
- Overview: per-STL estimates (time, filament, cost-info) via headless OrcaSlicer. Reproducible cache. Spoolman inventory linkage. Soft-fail on unreachable. No adaptive height (gated).
- FR20-ESTIMATE-1: per-STL estimate record with time/filament/cost fields, attributable to resolved profile settings.
- FR20-CACHE-1: cache keyed `(stl_hash, bundle_hash)` with explicit staleness indicator + recompute queue.
- FR20-FAILURE-1: soft-fail when slicer worker down; show "Last estimated HH:MM (Xm ago)".
- FR20-SPOOLMAN-MAP-1: optional custom overrides (esp. TPU volumetric speed) mapped from Spoolman `filament.extra` onto resolved filament JSON.
- NFR20-REPRODUCIBLE-1: hash-driven invalidation on STL change / bundle re-tune / Orca version / Spoolman override change. Cost-only changes recompute arithmetically (no re-slice).
- NFR20-CONTAINER-1: Orca runs headless in a containerized worker; no Fenrir production dependency.
- Open decisions: OD-1 (quality_tier enum), OD-2 (dedicated worker vs render-extend), OD-7 (cost arithmetic), OD-8 (STL source), OD-9 (module placement).

### 4.2 Architecture extension

**Action:** Append new `## Initiative 20` H2 + three Decisions. Manual edit (no bmad-edit-architecture skill).

**Decision AH — Resolver architecture (system + user merge + hashing):**
Recursive merge Orca system profile tree with user partials, inject `type`, drop instantiation, validate. Hash over resolved machine + process + filament + orca_version for cache key. Bundles are append-only/versioned. SourceProfileSnapshot for provenance. Folding orca_version into bundle_hash makes upgrades a clean invalidation event.

**Decision AI — Slicer-worker container (app boundary, job IO, STL cache):**
Containerized OrcaSlicer AppImage v2.3.2 + GL/GTK deps in a dedicated slicer-worker service (OD-2: dedicated vs extend render). Input: `(stl_ref, bundle_ref)`. Output: parsed EstimateRecord fields from g-code metadata. STL cache: `<root>/stl/<hash[:2]>/<hash>.stl`. No g-code retention (parse-and-discard per OD-5 leaning).

**Decision AJ — Cache / invalidation / cost arithmetic:**
EstimateRecord key: `(stl_hash, bundle_hash)`. Recompute triggers (table): STL content → new hash, bundle re-tune → new hash, Orca upgrade → hash change, Spoolman override change → hash change (folded via `spoolman_overrides_ref`). **Cost-only Spoolman change (OD-7):** recompute cost arithmetically without re-slicing (critical efficiency rule; prevents recompute storms on price ticks).

### 4.3 Epics extension

**Action:** Append new `## Initiative 20` H2 + Epic E32 + ~5–6 stories. Manual edit.

Story sketch:
- **32.1** Resolver (merge, normalize, validate, hash, snapshot).
- **32.2** Slicer-worker container (AppImage, job shape, CLI invoke).
- **32.3** Estimate parse + cache schema + cost-carry fields.
- **32.4** Invalidation rules + recompute queue.
- **32.5** Spoolman override mapping (volumetric speed, temps, density).
- **32.6** Frontend PrintIntentPreset selector + estimate display + soft-fail states.

## 5. Implementation Handoff

**Blocker:** Implementation planning remains **BLOCKED** until PRD + architecture H2 appends are verified. This is phase-1 discovery output.

**Handoff sequence (post-approval):**
1. **`bmad-correct-course`** (this SCP + brainstorm artifact as input) → routes to PRD/architecture phases.
2. **`bmad-edit-prd`** — append Initiative 20 H2.
3. **Manual append `architecture.md`** — Decisions AH + AI + AJ.
4. **Manual append `epics.md`** — Epic E32 + stories 32.1–32.6.
5. **Configs-side coordination** — slicer-worker compose PR (per HC2 boundary).
6. **`bmad-sprint-planning`** — sequence Init 20 after Init 19 close-out.
7. **`bmad-create-story` + `bmad-dev-story`** chain on stories 32.1→6.

**Success criteria:** Real per-STL estimates (time, filament, cost-info) show on catalog detail + queue entry. Stopping the slicer worker leaves estimates in soft-fail with timestamp. Hash-keyed cache means re-slicing only happens on meaningful input changes. Cost-only Spoolman price changes recompute arithmetically in <1s (not minutes).
