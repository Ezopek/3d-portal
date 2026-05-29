---
title: "Sprint Change Proposal — Initiative 19 (Spoolman Read-Only Inventory, MVP-A)"
type: sprint-change-proposal
initiative_scope: [19]
status: approved
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-29
approved_by: operator (Michał / Ezop) — Polish explicit approval text "Akceptuję i idziemy dalej"
approved_at: 2026-05-29
approved_via: operator chat (Polish explicit approval; ITCM autonomous mode now engages — downstream bmad-edit-prd + manual architecture/epics/sprint-status appends fire in this same session)
execution_directive: |
  Pre-SCP business alignment phase: brainstorming session
  2026-05-29-0840 (6 phases — First Principles / Morphological /
  What-If / Reverse / Six Hats / Constraint Mapping; 118 ideas; 15
  morphological parameters × ~60 option cells). Five operator
  decisions resolved post-brainstorm, pre-SCP (this run): (1) MVP-A
  scope (baseline cell from brainstorm Phase 2); (2) `/spools` is
  read-only-visible to MEMBERS too (not admin-only — overrides the
  brainstorm Black-Hat default OD2 = "admin-only" + T4.5); (3)
  transport/topology delegated to technical recommendation in this
  SCP; (4) Spoolman is LAN-only today AND operator values the
  convenient direct Spoolman UI for adding spools/filaments — future
  Laura-delegated tasks may also add spools/filaments, so the
  direct-UI convenience stays unless there's a strong reason
  otherwise (locks write surface OUT of MVP indefinitely); (5) cost
  calculation should consider Spoolman native `price` + weight
  fields first — verified via live OpenAPI: Filament has
  `price` + `weight` + `spool_weight`; Spool has `price` +
  `spool_weight` + `remaining_weight` + `initial_weight` +
  `used_weight`. ITCM autonomous mode from
  [[feedback_itcm_autonomous_mode]] does NOT yet apply — this SCP IS
  the business-alignment artifact; operator approval gate required
  before ITCM execution.
mode: batch-presented (operator-pragmatic; matches Init 6 / 7+8+9 /
  10 / 11-15 / 16 / 17 / 18 SCP precedent — full draft surfaced
  once, operator approves → autonomous execution)
change_scope_classification: moderate  # 1 new initiative, 1 new epic E31, ~5 stories, single-Phase MVP-A scope. New backend module + frontend module + env-config additions + 1 configs-side coordination note. No DB migration. No new auth surface. No NFR-SECURITY adjacency (read-only outbound HTTP to a LAN-only homelab service).
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                         # extend (Initiative 19 H2 — FR19-* + NFR19-*)
  - _bmad-output/planning-artifacts/architecture.md                # extend (Initiative 19 H2 — Decisions AD + AE + AF)
  - _bmad-output/planning-artifacts/epics.md                       # extend (Initiative 19 H2 + Epic E31 — ~5 stories)
  - _bmad-output/implementation-artifacts/sprint-status.yaml       # extend (epic-31 + 31-1 / 31-2 / 31-3 / 31-4 / 31-5 entries, status backlog)
  - _bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md   # source brainstorm (118 ideas; baseline + alternative cells; OD1-OD10 register)
  - ~/repos/configs/docker-compose-recipes/spoolman.yml            # configs-side coordination PR (Decision AE Network Topology — attach Spoolman to portal-network so portal-api container can resolve `spoolman:8000`). 1 PR, copy-and-edit pattern per HC2. NOT a 3d-portal commit.
  - infra/.env.example (or apps/api/.env-style equivalent)         # documents new env slots SPOOLMAN_URL + SPOOLMAN_AUTH_TOKEN (B4 from brainstorm)
predecessor_initiative: 18
trigger:
  source: |
    Operator request 2026-05-29 to enumerate the Spoolman integration
    scope space before authoring a PRD. Resulting brainstorm
    (2026-05-29-0840.md, autonomous-facilitation mode) ran 6
    techniques against 15 morphological parameters and surfaced a
    high-confidence baseline cell (MVP-A) plus alternative cells +
    open-decisions register OD1-OD10. The brainstorm explicitly
    routes downstream work to bmad-correct-course (per AGENTS.md §
    BMAD vanilla-first + § Workflow expectations — brownfield + post-
    foundation feature = correct-course entry, NOT bmad-create-prd).
  shape: |
    Net-new initiative adding a Spoolman read-only inventory
    integration to the existing portal. Three orthogonal value
    axes were identified (V1 read-side surfacing, V2 catalog ↔
    filament linkage, V3 mutation surface); MVP-A occupies axis V1
    only. New backend module `apps/api/app/modules/spools/` + new
    frontend module `apps/web/src/modules/spools/` (swap from
    ComingSoonStub to real implementation) + landing-dashboard low-
    stock card + arq poll job + Redis cache + env config additions
    + 1 configs-side coordination PR for network topology. NO
    mutation surface, NO catalog-filament linkage, NO cost
    calculator UI. Single Phase scope; Phase B (catalog ↔ filament
    linkage), Phase C (restricted writes), Phase D (cost calc UX)
    parked as future-initiative candidates with explicit precondition
    triggers.
  evidence_class: |
    Structured 6-technique brainstorming session 2026-05-29-0840
    (118 distinct ideas; 15-parameter morphological grid; 20 What-If
    scenarios; 20 Reverse anti-patterns; Six Hats convergence; full
    constraint map separating HC/SC/IC tiers). Verified Spoolman
    facts at session start: instance running 0.23.1 on .190 port
    7912, 9 active spools + 16 filaments + 2 vendors, two real
    low-stock spools (PLA Speed Matt White 138.9g + PCTG Army Green
    163.2g) — MVP-A is demoable on day-one with real signal (B5
    from brainstorm). Spoolman OpenAPI inspected live by operator
    post-brainstorm — Filament has price+weight+spool_weight, Spool
    has price+spool_weight+remaining_weight+initial_weight+used_weight
    (drives Decision AF cost-data carry-through stance).
business_decisions_aligned_pre_scp:
  - mvp_a_baseline_cell_locked: |
      Operator 2026-05-29 (post-brainstorm): proceed with MVP-A
      (brainstorm Phase 2 baseline cell P1b + P2b + P3a + P4b +
      P5a + P6b + P7c + P8b + P9a + P10a + P11a + P12a + P13a + P14a
      + P15a) as the initiative scope. Alternative cell (catalog
      detail + free-form material) parked as Phase B candidate.
      Resolves OD1.
  - spools_route_member_visible_not_admin_only: |
      Operator 2026-05-29: `/spools` read-only view is visible to
      MEMBERS too, not admin-only. Backend route auth dep =
      `Depends(current_user)`, NOT `Depends(current_admin)`.
      OVERRIDES brainstorm Black Hat default + Theme 4 T4.5 which
      recommended "admin-only by default for MVP" pending feedback.
      Rationale (operator): inventory visibility has near-zero
      sensitivity in the household-trust model; surfacing material
      stock to members aligns with the existing read-side trust
      posture (members can already browse the full catalog). Future
      visibility tightening (e.g. anonymous opt-in via share token)
      is a separate decision. Resolves OD2.
  - transport_delegated_to_technical_recommendation: |
      Operator 2026-05-29: transport/topology left to this SCP's
      technical recommendation. SCP recommends Decision AE: P4b
      docker-internal network — portal-api container resolves
      `http://spoolman:8000/api/v1/*` over a shared compose network.
      Requires a configs-side PR to
      `~/repos/configs/docker-compose-recipes/spoolman.yml` attaching
      the Spoolman container to a network the portal-api compose
      stack joins. Fallback P4a (portal-api on host network calls
      `http://localhost:7912/api/v1/*`) acceptable as one-line
      transitional posture if the configs PR slips behind Init 19
      schedule. Resolves OD4.
  - write_surface_out_of_mvp_indefinitely: |
      Operator 2026-05-29: Spoolman is LAN-only today AND operator
      values the convenient direct Spoolman UI for adding spools
      and filaments; future Laura-delegated tasks may also add
      spools/filaments, and the direct-UI convenience should be
      kept unless there's a strong reason otherwise. This locks the
      write surface (MVP-D from brainstorm Theme 6) OUT of MVP-A
      AND removes "usage telemetry suggests demand" as the Phase-
      next trigger. New trigger: "direct Spoolman UI ergonomic
      regression for operator or Laura". Anti-pattern 3 from
      brainstorm Reverse phase ("surface Delete spool button before
      operator demand") is reinforced. Refines OD-class beyond OD1
      lock.
  - cost_calc_native_fields_first_data_carry_through_in_mvp_a: |
      Operator 2026-05-29: cost calculation should consider
      Spoolman native price + weight fields first (verified via live
      OpenAPI inspection — Filament.price + Filament.weight +
      Filament.spool_weight; Spool.price + Spool.spool_weight +
      Spool.remaining_weight + Spool.initial_weight +
      Spool.used_weight). Decision AF: even MVP-A's cached
      Spool/Filament snapshot models MUST carry these fields end-
      to-end (DTO + Redis cache schema + frontend `api-types.gen.ts`
      surface), so future Phase D (cost calc UX) can light up
      without a portal-side schema backfill. The cost UX itself
      stays OUT of MVP-A — landing-card surface is qty-and-status
      only. Resolves OD7 design stance (carry-through data without
      surfacing UX).
non_resolved_decisions_carried_into_correct_course_step:
  - cache_topology_recommendation_locked: |
      OD5 resolved by this SCP per Decision AD: Redis 30s TTL +
      arq 60s poll job + Redis SETNX leader-election (anti-
      pattern 11 from brainstorm). No websocket subscription in
      MVP-A (P8c parked until queue/printer modules make 60s lag
      intolerable). 3-row cache-coherence table embedded in
      Decision AD (per [[feedback_scp_pre_enumeration_phase]] cache
      enumeration discipline + Init 18 round-7 lesson) — staleness
      budget + propagation + eviction defined for the single
      `["spools", "summary"]` query-key.
  - test_posture_recommendation_locked: |
      OD6 resolved by this SCP per Decision AD § Testing: pytest
      with httpx mock (P14a) for unit speed + ONE env-gated live
      integration test (P14d) keyed off `SPOOLMAN_LIVE_TEST=1`,
      pinning the contract against a real Spoolman instance.
      Vitest mocks `fetch` at boundary per the existing
      web-test convention; no api() mocking.
  - spoolman_bind_address_verification_as_configs_side_precondition: |
      OD8 resolved by operator's LAN-only declaration plus a 1-line
      configs-side precondition: before Story 31.1 ships, configs
      side verifies the Spoolman compose binds to a non-routable
      host interface (i.e. NOT `0.0.0.0` exposed via the router).
      Documented as Story 31.1 § Pre-merge precondition (not a 3d-
      portal commit).
  - filament_spool_distinction_preserved: |
      OD9 resolved per Reverse anti-pattern 18: the portal-side
      cached snapshot mirrors Spoolman's filament-as-SKU vs spool-
      as-physical-instance distinction faithfully. Two cache
      entries: `["spools", "spool", spool_id]` per spool +
      `["spools", "filament", filament_id]` per filament. Collapsing
      to spool-level only is rejected (would silently break when a
      second spool of an existing filament SKU arrives).
  - module_naming_kept_at_spools: |
      OD10 resolved: module folder keeps the existing placeholder
      name `spools/` (lower-churn against existing frontend stub
      `apps/web/src/routes/spools/index.tsx` + `ModuleRail.tsx:11` +
      `modules.spools` i18n key + AGENTS.md "v2 slot" mention).
      Renaming to `inventory/` or `filaments/` rejected.
  - parked_phases_with_explicit_triggers: |
      Brainstorm Theme 6 MVP-B/C/D/E are parked with explicit
      precondition triggers (NOT vague "future work"):
      - **MVP-B (catalog detail × material match, free-form text)**:
        trigger = "operator wants per-model material context on
        catalog detail page". ~2 stories on top of MVP-A.
      - **MVP-C (recommended_material_profile SoT structure)**:
        trigger = "catalog SoT design round picks up filament
        linkage" — would touch catalog SoT, so blocks on a SoT-
        side decision.
      - **MVP-D (restricted writes — use/measure)**: trigger =
        "direct Spoolman UI ergonomic regression for operator OR
        Laura". Per operator decision 4, NOT triggered by mere
        usage telemetry.
      - **MVP-E (share-token inventory snapshot)**: trigger =
        "operator wants to advertise printable-right-now stock to
        an external recipient". Independent of Phase B/C/D.
      - **Phase D (cost calc UX)**: trigger = "operator wants per-
        print cost rollup on catalog detail or queue entry". MVP-A
        already carries the data fields per Decision AF, so the
        backfill cost is zero.
---

# Sprint Change Proposal — Initiative 19 (Spoolman Read-Only Inventory, MVP-A)

**Date:** 2026-05-29
**Skill:** `bmad-correct-course` (vanilla-aligned; brownfield routing per AGENTS.md § BMAD vanilla-first)
**Predecessor initiative:** Initiative 18 (Share-Flow Membership-Path Completion, Phase A — planning, in-progress per `sprint-change-proposal-2026-05-25-init18.md`).

## 1. Issue Summary

**Triggering observation.** The 2026-04-29 portal v1 design and the 2026-05-04 Source-of-Truth design both explicitly *punted* Spoolman integration as out of scope, with `docs/superpowers/specs/2026-05-04-portal-source-of-truth-design.md:46` saying verbatim: *"Filament cost calculator / Spoolman integration (separate brainstorm)"*. AGENTS.md and `docs/architecture.md:45` both tag a `modules/spools/` "v2 slot" as the integration destination but provide zero detail beyond that. `apps/web/src/routes/spools/index.tsx` ships a `ComingSoonStub` rendering "Spools / Filamenty" with no backing implementation. The operator's daily-driver workflow today involves a separate browser tab to `http://.190:7912/` whenever inventory questions arise, completely disconnected from catalog browsing.

**Problem framing.** This SCP is the *separate brainstorm* the 2026-05-04 design referenced. It is **not** a bug-fix or scope-pivot SCP; it is a net-new feature initiative being routed through `bmad-correct-course` because the brownfield + post-foundation routing convention (AGENTS.md § Workflow expectations) sends all new initiative-scoped work through correct-course for PRD/architecture/epics extension. Vanilla `bmad-create-prd` is greenfield-only.

**Discovery evidence.**

- Brainstorming session `_bmad-output/brainstorming/brainstorming-session-2026-05-29-0840.md` (118 distinct ideas across 6 techniques; 15-parameter morphological grid; live verification of Spoolman state at session start).
- Spoolman OpenAPI live-inspection by operator post-brainstorm — verified the data shape that drives Decision AF (cost-data carry-through).
- Five operator decisions recorded post-brainstorm pre-SCP (frontmatter `business_decisions_aligned_pre_scp` block above).

## 2. Impact Analysis

### Epic impact

**No existing epic is affected.** All currently-planning initiatives (Init 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18) operate on the existing portal modules (auth / admin / catalog / share / sot / runbook). Initiative 19 introduces a **new** epic E31 (project-global numbering — Init 18 ends at E30) with ~5 stories, scheduled to land *after* Init 18 closes per ITCM autonomous mode's "active initiative completes before next initiative business-alignment fires" convention.

**No epic resequencing needed.** Init 18 is already mid-flight; Init 19 queues behind it. Sprint-status.yaml gets new entries `epic-31` + `31-1` through `31-5`, all `status: backlog` until Init 18 closes.

### Artifact conflict and adjustment surface

| Artifact | Action | Detail |
|---|---|---|
| `_bmad-output/planning-artifacts/prd.md` | EXTEND | New `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 after Init 18. Adds FR19-LOWSTOCK-1, FR19-SPOOLS-VIEW-1, FR19-CACHE-1, FR19-FAILURE-1, FR19-DATA-CARRY-1 + NFR19-NETWORK-1, NFR19-OBS-1, NFR19-DETERMINISM-1, NFR19-I18N-PARITY-1, NFR19-VISUAL-VERIFICATION-1. Initiatives Index table row + frontmatter `initiatives:` array entry. |
| `_bmad-output/planning-artifacts/architecture.md` | EXTEND | New `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 with three Decisions: **AD** (cache topology + poll cadence + leader-election + cache-coherence table), **AE** (network transport — internal docker network with configs-side coordination + P4a fallback), **AF** (data-model carry-through — surface Spoolman price + weight fields in MVP-A DTOs/cache for future cost-calc UX). Initiatives Index table row + frontmatter array entry. |
| `_bmad-output/planning-artifacts/epics.md` | EXTEND | New `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 + `#### Epic E31 — Spoolman Read-Only Inventory` + 5 stories `31.1`–`31.5` (project-global epic numbering). Initiatives Index table row + frontmatter array entry. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | EXTEND | New entries `epic-31` + `31-1-*` … `31-5-*`, all `status: backlog`. Append to bottom; do NOT reorder existing epic-30 entries. |
| `apps/api/app/modules/spools/` | NEW PACKAGE (deferred to story exec) | New backend module mirroring existing module layout (`__init__.py`, `router.py`, `service.py`, `client.py` — the httpx wrapper, `models.py` — Pydantic DTOs). NOT touched in this SCP — story-level work. |
| `apps/web/src/modules/spools/` | NEW PACKAGE (deferred to story exec) | New frontend module (`hooks/useSpoolsSummary.ts`, `components/LowStockCard.tsx`, `routes/SpoolsIndexPage.tsx`). NOT touched in this SCP. |
| `apps/web/src/routes/spools/index.tsx` | MODIFY (deferred to story exec) | Replace `<ComingSoonStub moduleKey="spools" />` with real component tree. NOT touched in this SCP. |
| `apps/api/app/core/config.py` | MODIFY (deferred to story exec) | Add `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` fields to `Settings` (Pydantic, `pydantic-settings`). NOT touched in this SCP — Story 31.1 work. |
| `infra/docker-compose.yml` | MODIFY (deferred to story exec) | Add `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` env wiring + join the new shared docker network from Decision AE. NOT touched in this SCP. |
| `~/repos/configs/docker-compose-recipes/spoolman.yml` | MODIFY (out-of-repo) | Configs-side coordination PR per HC2 + Decision AE — attach Spoolman to a portal-reachable docker network. **NOT a 3d-portal commit.** Documented as Story 31.1 § Pre-merge precondition. |
| `apps/web/src/locales/en.json` + `pl.json` | MODIFY (deferred to story exec) | Add `modules.spools.*` namespace (low-stock copy, stale-since indicator, empty-state copy, error-state copy). |

### Technical impact

- **Data plane:** zero schema changes; zero Alembic migrations. Spoolman state is mirrored read-only in Redis cache; no portal DB tables touched.
- **Auth surface:** zero new auth dependencies; existing cookie+CSRF middleware unchanged. The new `/api/spools/*` routes use the existing `current_user` dep (per operator decision 2). The `_PUBLIC_ROUTES` allowlist (Init 6 Decision M) is NOT touched — `/api/spools/*` requires auth.
- **Outbound network:** **first portal-side outbound HTTP to a non-observability service.** Today portal-api only egresses to GlitchTip/OTel/Sentry endpoints. New egress class `external_service=spoolman` introduced per Decision AD § Observability (mandatory tag from day one, brainstorm anti-pattern 14).
- **Workers:** new arq job `poll_spoolman_summary` registered in `apps/api/app/workers/__init__.py` (the API-image arq worker, not the render worker per AGENTS.md § Worker depends on `portal-api` editable). Cron schedule: every 60s. Single-poller leader-election via Redis SETNX (brainstorm anti-pattern 11).
- **Frontend perf:** landing page gains one new card; payload impact ≤2 KB JSON (9 spools × ~200 bytes summary fields). No new heavy dependencies.
- **Deploy:** `infra/scripts/deploy.sh` flow unchanged. Configs-side Spoolman compose change deploys via `~/repos/configs` `sync.sh`, NOT via portal deploy (HC2 trip-wire preserved).
- **Observability:** new structured-log tag `external_service=spoolman` on every Spoolman client call; OTel span around the httpx call (per `~/repos/configs/docs/observability-logging-contract.md`). GlitchTip breadcrumb category `spoolman.client`.

## 3. Recommended Approach

**Path forward: Option 1 — Direct Adjustment** (vanilla H2 append pattern per `[[feedback_vanilla_bmad_first]]` + AGENTS.md `BMAD vanilla-first` subsection; matches Init 5 / Init 10 / Init 18 SCP precedents).

**Rationale.**

- **No rollback candidate.** Nothing recently shipped overlaps with Spoolman scope; no rework possible.
- **No PRD MVP redefinition needed.** This is net-new scope, not a rewrite of an existing requirement. Initiative-level H2 append is the canonical living-doc extension pattern.
- **Effort:** Low–Medium. New backend module (~300 LOC service + client + router), new frontend module (~200 LOC component + hook + route), 1 configs-side PR (~10 LOC), ~5 stories single-developer pace = ~3–5 working days under autonomous ITCM mode.
- **Risk:** Low. Read-only outbound HTTP to a LAN-only service. No auth boundary changes. No public-bypass family adjacent (this is NOT `/api/share/*` or `/api/admin/*` adjacent). No NFR-SECURITY adjacency per `[[feedback_codex_model_routing]]` — story-level Codex review tag = `gpt-5.4-mini` for all Init 19 stories.
- **Sustainability:** The MVP-A baseline cell establishes the integration template (httpx client + Redis cache + arq poll job + soft-fail UX) cleanly. Future Phase B/C/D/E inherit the template without ripping it out.

**Scope envelope (locked).**

- ✅ IN: Read-only `/spools` route showing low-stock summary + full-inventory list (filterable). Landing-page low-stock card. Backend service + httpx client + Redis cache + arq poll. Env config additions. Configs-side coordination note. Visual baselines for landing card + `/spools` index.
- ❌ OUT: Catalog detail material-match annotation. Recommended-material-profile SoT structure. Mutation surface (use/measure/CRUD). Cost calculator UX. Share-token inventory snapshot. Multi-instance support. Websocket subscription. Anonymous read of `/spools`.

**Initiative scope summary.**

| Field | Value |
|---|---|
| Initiative # | **19** |
| Initiative name | Spoolman Read-Only Inventory (MVP-A) |
| Predecessor | Init 18 (in-flight) |
| Epic # (project-global) | **E31** |
| Story count | ~5 (31.1 backend client + cache + poll; 31.2 backend `/api/spools/*` routes + DTOs with cost-data carry-through; 31.3 frontend `/spools` page; 31.4 landing low-stock card; 31.5 i18n + visual baselines + env config + ops doc) |
| Codex routing | All stories `gpt-5.4-mini` per `[[feedback_codex_model_routing]]` — no NFR-SECURITY adjacency (read-only outbound HTTP to LAN-only service; no public-bypass family adjacency; no auth boundary changes) |
| Scope class | moderate (PO/DEV — backlog reorganization needed; no PM/Architect involvement) |

## 4. Detailed Change Proposals

This SCP defines WHAT to extend in the planning artifacts. The downstream `bmad-edit-prd` skill + manual architecture/epics append (per AGENTS.md "there is no bmad-edit-epics skill" + project-context.md § Workflow source of truth) carries out the actual file edits. The SCP itself is the operator-approval gate.

### 4.1 PRD extension — `_bmad-output/planning-artifacts/prd.md`

**Action:** Append new `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 section after Init 18 (after line 1795). Update Initiatives Index table (line 106) with the new row. Update frontmatter `initiatives:` array with the new entry. Update `last updated` line (102) with this SCP reference. Use `bmad-edit-prd` skill.

**New Initiative 19 H2 content outline** (full FR/NFR text drafted at PRD-edit time):

```
## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)

**Status:** 🚧 planning (started 2026-05-29). Source SCP:
`sprint-change-proposal-2026-05-29-spoolman.md`. First portal initiative
to integrate the standalone Spoolman instance at `.190:7912` as a
read-only inventory mirror, surfaced via a new `/spools` route + a
landing-page low-stock card. Single epic E31, ~5 stories, all `gpt-5.4-mini`
Codex routing. Phase B (catalog ↔ filament linkage), Phase C
(restricted writes), Phase D (cost calc UX), Phase E (share-token
inventory snapshot) parked with explicit precondition triggers (see §
Out of scope).

### Overview

[Synthesis from brainstorm Phase 1 First-Principles distillation +
operator post-brainstorm decisions; brainstorm Theme 6 MVP-A baseline
cell; first portal outbound-HTTP-to-non-observability surface.]

### Functional Requirements

- **FR19-LOWSTOCK-1**: Landing page surfaces a "Low stock" card listing
  active spools with `remaining_weight` below a configurable threshold
  (default 200g; env-tunable). Card visible to all authenticated users
  (members + admin) — NOT admin-only. Verifiable: vitest + Playwright
  visual baseline showing the two real low-stock spools at session
  start (or whatever the live state is).
- **FR19-SPOOLS-VIEW-1**: `/spools` route renders an inventory list of
  active spools + active filaments (mirroring Spoolman's
  filament-vs-spool distinction per OD9). Members + admin both visible.
  No mutation affordances. Verifiable: vitest + Playwright visual ×4.
- **FR19-CACHE-1**: Cache topology per Decision AD — Redis 30s TTL +
  arq 60s poll + Redis SETNX leader-election. Verifiable: backend
  pytest exercising cache hit/miss + lock contention.
- **FR19-FAILURE-1**: When Spoolman is unreachable, the landing card
  and `/spools` view display the last cached snapshot with an explicit
  "Last updated HH:MM (Xm ago)" indicator (P6b soft-fail; brainstorm
  Black-Hat risk mitigation). Never render 500. Verifiable: vitest
  with mocked-down upstream + Playwright visual of the stale state.
- **FR19-DATA-CARRY-1**: Cached DTOs surface ALL Spoolman cost-relevant
  fields end-to-end (Filament: price, weight, spool_weight; Spool:
  price, spool_weight, remaining_weight, initial_weight, used_weight)
  per Decision AF. The MVP-A UX does NOT compute cost; it carries the
  data so future Phase D can light up without portal-side backfill.
  Verifiable: api-types.gen.ts diff shows the fields; backend pytest
  schema invariant.

### Non-Functional Requirements

- **NFR19-NETWORK-1**: Portal-api MUST reach Spoolman via internal
  docker network per Decision AE (or P4a fallback). MUST NOT expose
  Spoolman through nginx-180 edge. Verifiable: configs-side compose
  diff + portal-side env config grep.
- **NFR19-OBS-1**: Every Spoolman client call tagged
  `external_service=spoolman` per
  `~/repos/configs/docs/observability-logging-contract.md`; OTel span
  around httpx call; GlitchTip breadcrumb category `spoolman.client`.
  Response bodies NOT logged at INFO (brainstorm anti-pattern 8). Tag
  presence is a pre-merge grep invariant.
- **NFR19-DETERMINISM-1**: Carries forward Init 10-18 determinism
  contract. Vitest + pytest 3× consecutive identical pass counts after
  each story merge. arq poll job idempotent (anti-pattern 1 + 11).
- **NFR19-I18N-PARITY-1**: All new `modules.spools.*` i18n keys present
  in BOTH en.json and pl.json with Polish diacritics correct (rough
  estimate: ~12 keys for landing card + index + states). Material names
  PCTG/PETG/PLA/TPU stay untranslated (P15c).
- **NFR19-VISUAL-VERIFICATION-1**: New visual baselines for the
  landing low-stock card (4 projects) + `/spools` index page (4
  projects) + soft-fail state of the landing card (4 projects). Total
  ~12 PNGs across ~3 specs. Baseline-reviewed sign-off per FR13
  pre-commit hook.

### Decisions

- **Decision AD** (architecture): cache topology — Redis 30s TTL + arq
  60s poll + Redis SETNX leader-election + observability tag. See
  `architecture.md` § Initiative 19 Decision AD.
- **Decision AE** (architecture): network transport — internal docker
  network with configs-side coordination + P4a fallback. See
  `architecture.md` § Initiative 19 Decision AE.
- **Decision AF** (architecture): data-model carry-through — DTOs +
  cache surface Spoolman price + weight fields end-to-end. See
  `architecture.md` § Initiative 19 Decision AF.

### Out of scope (intentional; precondition triggers documented)

- **Phase B — catalog detail × material match (free-form text)**.
  Trigger: operator wants per-model material context on catalog detail.
- **Phase C — recommended_material_profile SoT structure**. Trigger:
  catalog SoT design round picks up filament linkage (blocks on
  SoT-side decision).
- **Phase D — cost calculator UX**. Trigger: operator wants per-print
  cost rollup on catalog detail or queue entry. MVP-A's Decision AF
  carry-through means zero backfill cost when triggered.
- **MVP-D — restricted writes (use/measure)**. Trigger: direct
  Spoolman UI ergonomic regression for operator OR Laura (NOT usage
  telemetry per operator decision 4).
- **MVP-E — share-token inventory snapshot**. Trigger: operator
  wants to advertise printable-right-now stock to external recipient.
- **Multi-instance support, websocket subscription, anonymous read,
  vendor pricing extension, in-portal Spoolman compose ownership**
  — all explicitly out of MVP-A.

### Cross-references

- Predecessor: Initiative 18 (in-flight).
- Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md`.
- Architecture: `architecture.md` § Initiative 19 (Decisions AD + AE + AF).
- Epics: `epics.md` § Initiative 19 (Epic E31 + stories 31.1–31.5).
- Sprint status: `sprint-status.yaml` § epic-31 / 31-1 / 31-2 / 31-3 /
  31-4 / 31-5.
- Brainstorm: `brainstorming-session-2026-05-29-0840.md`.
- Configs-side coordination: `~/repos/configs/docker-compose-recipes/spoolman.yml`
  PR (NOT a 3d-portal commit).
- Memory entries: [[feedback_scp_pre_enumeration_phase]] (cache
  enumeration discipline applied to Decision AD), [[feedback_codex_model_routing]]
  (gpt-5.4-mini for all Init 19 stories — no NFR-SECURITY adjacency),
  [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]],
  [[feedback_vanilla_bmad_first]].
```

### 4.2 Architecture extension — `_bmad-output/planning-artifacts/architecture.md`

**Action:** Append new `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 section after Init 18 (after line 2658). Update Initiatives Index table (line 85) with new row. Update frontmatter `initiatives:` array. Manual edit per AGENTS.md (no `bmad-edit-architecture` skill exists).

**Three Decisions to author** (full text at architecture-edit time):

#### Decision AD — Cache topology + poll cadence + leader-election + observability

- Backend httpx.AsyncClient with explicit timeout (5s) + circuit breaker (3 consecutive failures → 30s open).
- Single canonical Redis cache key: `spools:summary:v1` (JSON-encoded snapshot of all active spools + filaments + vendors). 30s TTL.
- arq cron job `poll_spoolman_summary` every 60s. Acquires Redis SETNX lock `spools:poll-lock` with 90s expiry before refreshing the snapshot (anti-pattern 11 leader-election; prevents thundering herd if multiple API workers run).
- Cache-coherence table (per `[[feedback_scp_pre_enumeration_phase]]` discipline + Init 18 round-7 lesson):

  | Query key | Staleness budget | Retry | Mutation propagation | Eviction on route exit | Seeding on route enter |
  |---|---|---|---|---|---|
  | `["spools", "summary"]` | 60s acceptable | n/a (read-only mirror; staleness is the contract) | n/a (no mutations in MVP-A) | none (cache survives navigation; stays warm for landing-card revisit) | none (poll job seeds; UI just reads) |

- Magic-constant contract pointing (per `[[feedback_scp_pre_enumeration_phase]]` rule):
  - `staleTime: 60_000` because **"low-stock landing card freshness budget is 60s per FR19-CACHE-1; matches arq poll cadence"** (the contract is the poll cadence, NOT the auth meQuery staleTime — Init 18 round-1 P1 lesson).
  - `gcTime: 5 * 60_000` because **"keep the snapshot in-memory across landing card / `/spools` route transitions"**.
  - Redis TTL `30s` because **"upper bound on stale snapshot served from cache; poll runs every 60s but a fresh request within the 30-60s window can serve the slightly-staler cached value"**.
- Failure semantics: Spoolman unreachable → frontend reads last cached value + reads a sibling `spools:summary:last-success-ts` key for the "Last updated HH:MM" indicator. If cache is empty (cold-start + Spoolman down), `/spools` and the landing card render an explicit "Spoolman unavailable" empty state — not 500.
- Observability: every httpx call instrumented with structured-log fields `external_service=spoolman` + `endpoint=GET /api/v1/spool` + duration_ms + status_code. OTel span name `spoolman.client.<endpoint>`. Sentry/GlitchTip breadcrumb category `spoolman.client`. Response bodies summarized (entity counts only) — NEVER logged in full (anti-pattern 8).

#### Decision AE — Network transport (internal docker network + configs-side coordination)

- **Primary topology (P4b — recommended):** portal-api container resolves `http://spoolman:8000/api/v1/*`. Requires the configs-side Spoolman compose to join a docker network the portal compose stack also joins (e.g. `portal-network`). Configs-side PR scope: add `networks: [portal-network]` to the Spoolman service block and declare the external network. ~10 LOC, single file, copy-and-deploy via `~/repos/configs/sync.sh` (HC2 trip-wire honored — portal repo never edits configs files).
- **Fallback topology (P4a):** if the configs-side PR is not yet in place when Story 31.1 begins, portal-api runs on the docker host network and calls `http://localhost:7912/api/v1/*`. One-line transitional posture; same env var (`SPOOLMAN_URL`) wraps both shapes.
- **Rejected:** P4c (nginx-fronted Spoolman) — adds latency + complexity for zero security gain in a LAN-only deployment. Reconsider if Spoolman ever exposes externally (would require P3d Spoolman auth too).
- **Rejected:** P4e (sidecar service in `apps/api/app/modules/spools/`) is fine as an *organizational* shape (it IS where the httpx wrapper lives) but is NOT a transport choice — transport is still P4b or P4a.
- **Future swap-out cost:** isolated httpx client in `apps/api/app/modules/spools/client.py` means swapping P4b → P4a → P3d-with-auth is a one-file change. Anti-pattern 7 honored: `SPOOLMAN_URL` env-driven, NOT hardcoded.

#### Decision AF — Data-model carry-through for future cost-calc UX

- Backend DTOs (`apps/api/app/modules/spools/models.py`) for `SpoolView` and `FilamentView` surface ALL cost-relevant fields end-to-end:
  - `FilamentView`: `id`, `name`, `vendor_id`, `vendor_name`, `material`, `color_hex`, `price` (currency-tagged float, nullable), `weight` (grams, the full-spool weight), `spool_weight` (grams, empty-cardboard weight).
  - `SpoolView`: `id`, `filament_id`, `price` (override, nullable), `remaining_weight` (grams), `initial_weight` (grams), `used_weight` (grams), `spool_weight` (grams), `first_used` (ISO8601 nullable), `last_used` (ISO8601 nullable), `archived` (bool), `lot_nr` (str nullable).
- Frontend `apps/web/src/lib/api-types.gen.ts` mirrors these fields automatically via the OpenAPI generation pipeline (no manual TypeScript typing).
- MVP-A UX uses ONLY `id`, `name`, `vendor_name`, `material`, `color_hex`, `remaining_weight`, `initial_weight` (for the % remaining bar) — but the broader fields are CARRIED in the cache and DTOs so future Phase D (cost calc UX) can light up without a portal-side schema backfill. Per operator decision 5: Spoolman native price+weight fields are the canonical cost-data source.
- Future Phase D arithmetic (NOT in MVP-A): `remaining_value = remaining_weight × (filament.price / filament.weight)` (or spool.price override if set). Documented in the architecture H2 as a forward-design note, NOT implemented.

#### Cross-references

- PRD: `prd.md` § Initiative 19 (FR19-* + NFR19-* link back to Decisions AD + AE + AF).
- Epics: `epics.md` § Initiative 19 (Story 31.1 implements Decisions AD + AE; Story 31.2 implements Decision AF DTOs; Stories 31.3 + 31.4 + 31.5 are pure FE).
- Source SCP: `sprint-change-proposal-2026-05-29-spoolman.md` § §3 + §4.2.
- Memory entries informing decisions: `[[feedback_scp_pre_enumeration_phase]]` (cache-coherence table format + magic-constant contract pointing applied), `[[feedback_codex_model_routing]]` (gpt-5.4-mini routing locked).

### 4.3 Epics extension — `_bmad-output/planning-artifacts/epics.md`

**Action:** Append new `## Initiative 19 — Spoolman Read-Only Inventory (MVP-A)` H2 + `#### Epic E31 — Spoolman Read-Only Inventory` + ~5 stories 31.1–31.5 after Init 18 (after line ~3414). Update Initiatives Index table + frontmatter array. Manual edit (no `bmad-edit-epics` skill).

**Story breakdown sketch** (full Given/When/Then at `bmad-create-story` time per AGENTS.md `bmad-correct-course` §3.3 rule #4):

| Story | Realizes | Codex tag | Notes |
|---|---|---|---|
| **31.1** Backend Spoolman client + Redis cache + arq poll job + env config | FR19-CACHE-1, NFR19-NETWORK-1, NFR19-OBS-1; Decisions AD + AE | gpt-5.4-mini | New `apps/api/app/modules/spools/client.py` (httpx wrapper) + `service.py` (cache + poll logic) + arq cron registration. Adds `SPOOLMAN_URL` + `SPOOLMAN_AUTH_TOKEN` env slots. Mocked pytest + env-gated `SPOOLMAN_LIVE_TEST=1` smoke test. § Pre-merge precondition: configs-side Spoolman compose verified to bind to non-routable interface (OD8 close-out). |
| **31.2** Backend `/api/spools/*` routes + DTOs with cost-data carry-through | FR19-SPOOLS-VIEW-1, FR19-DATA-CARRY-1; Decision AF | gpt-5.4-mini | New `apps/api/app/modules/spools/router.py` with `GET /api/spools/summary` + `GET /api/spools/spools` + `GET /api/spools/filaments`. All routes `Depends(current_user)` per operator decision 2 (members visible). DTOs surface ALL cost-relevant Spoolman fields. api-types.gen.ts regenerated. |
| **31.3** Frontend `/spools` route + index page + states | FR19-SPOOLS-VIEW-1, FR19-FAILURE-1, NFR19-VISUAL-VERIFICATION-1, NFR19-I18N-PARITY-1 partial | gpt-5.4-mini | Replace `ComingSoonStub` at `apps/web/src/routes/spools/index.tsx` with real impl. New `apps/web/src/modules/spools/components/SpoolsIndexPage.tsx` + `hooks/useSpoolsSummary.ts` (TanStack Query, `["spools", "summary"]` key, `staleTime: 60_000`). Empty / loading / soft-fail / error states. New Playwright spec `spools-index.spec.ts` × 4 projects = 4 baselines. |
| **31.4** Frontend landing low-stock card | FR19-LOWSTOCK-1, NFR19-VISUAL-VERIFICATION-1, NFR19-I18N-PARITY-1 partial | gpt-5.4-mini | New `apps/web/src/modules/spools/components/LowStockCard.tsx`. Mounted on landing page (find current landing impl + add card). Threshold from env (default 200g). New Playwright spec `landing-low-stock.spec.ts` × 4 projects = 4 baselines (one of which shows the two real low-stock spools per B5 brainstorm signal). Soft-fail variant baseline = 4 more PNGs. |
| **31.5** i18n keys + ops doc + visual baseline regen of any affected existing specs + docs/operations.md addendum | NFR19-I18N-PARITY-1, NFR19-VISUAL-VERIFICATION-1 | gpt-5.4-mini | ~12 new `modules.spools.*` i18n keys in BOTH en.json + pl.json. `docs/operations.md` addendum: SPOOLMAN_URL env slot + soft-fail behavior + how to verify Spoolman bind address on `.190`. If landing-page baseline changes due to the new card, regenerate the affected existing spec with `baseline-reviewed:` sign-off. |

**Standalone stories outside E31:** none.

### 4.4 Sprint status extension — `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Action:** Append new entries after the existing epic-30 block, all `status: backlog`:

```yaml
epic-31:
  initiative: 19
  name: "Spoolman Read-Only Inventory (MVP-A)"
  status: backlog
  scp: sprint-change-proposal-2026-05-29-spoolman.md
  stories: [31-1, 31-2, 31-3, 31-4, 31-5]
31-1-backend-spoolman-client-cache-poll:
  epic: 31
  status: backlog
  codex_routing: gpt-5.4-mini
31-2-backend-spools-routes-dto-cost-carry:
  epic: 31
  status: backlog
  codex_routing: gpt-5.4-mini
  blocked_by: 31-1
31-3-frontend-spools-route-index-page:
  epic: 31
  status: backlog
  codex_routing: gpt-5.4-mini
  blocked_by: 31-2
31-4-frontend-landing-low-stock-card:
  epic: 31
  status: backlog
  codex_routing: gpt-5.4-mini
  blocked_by: 31-2
31-5-i18n-ops-doc-baseline-regen:
  epic: 31
  status: backlog
  codex_routing: gpt-5.4-mini
  blocked_by: [31-3, 31-4]
```

### 4.5 Configs-side coordination note — `~/repos/configs/docker-compose-recipes/spoolman.yml`

**Action (out-of-repo):** 1 PR adding `networks: [portal-network]` to the Spoolman service block and declaring the external network. Scope ~10 LOC, single file. Deploy via `~/repos/configs/sync.sh`. **NOT a 3d-portal commit.** Owner: configs-side. Trigger: before Story 31.1 enters dev. If the PR slips, Story 31.1 falls back to P4a (host-network) per Decision AE fallback clause; no Init 19 schedule slip.

## 5. Implementation Handoff

**Change scope classification:** **moderate**. New initiative end-to-end (PRD + architecture + epics + sprint-status entries + ~5 stories), but no PM/Architect involvement needed — all architectural decisions are operator-confirmed-or-recommended-here, no NFR-SECURITY adjacency, no DB migration, no cross-repo design coordination beyond a single ~10 LOC configs-side compose tweak.

**Handoff recipients (post-approval, in order):**

1. **`bmad-edit-prd`** (next BMAD session, fresh context) — append Initiative 19 H2 to `prd.md` per §4.1.
2. **Manual append to `architecture.md`** (same session as PRD edit or fresh session) — append Initiative 19 H2 + Decisions AD/AE/AF per §4.2. No `bmad-edit-architecture` skill exists.
3. **Manual append to `epics.md`** (same session) — append Initiative 19 H2 + Epic E31 + stories 31.1–31.5 per §4.3. No `bmad-edit-epics` skill exists.
4. **Manual append to `sprint-status.yaml`** (same session) — entries per §4.4.
5. **Configs-side coordination PR** (parallel, before Story 31.1 dev fires) — per §4.5.
6. **`bmad-sprint-planning`** — confirm Init 19 sequencing relative to Init 18 close-out + any currently planning initiatives.
7. **`bmad-create-story`** + **`bmad-dev-story`** chain on stories 31.1 → 31.2 → (31.3 ∥ 31.4) → 31.5. All stories `gpt-5.4-mini` Codex routing.
8. **`bmad-retrospective`** after E31 closes.

**Success criteria for implementation:**

- A fresh `git pull` + `infra/scripts/deploy.sh` + visit to landing as an authenticated member shows the real low-stock spools card with the two spools at session start (or the live state) — `[[feedback_b5_demoable_signal]]` brainstorm B5.
- Stopping the Spoolman container leaves the landing card + `/spools` route in soft-fail mode with explicit "Last updated HH:MM (Xm ago)" — NOT a 500 (FR19-FAILURE-1).
- Members and admins both see `/spools` (operator decision 2). Anonymous visitors hit the existing auth redirect.
- Visual baselines exist for landing card (4 projects) + `/spools` index (4 projects) + soft-fail state (4 projects). Pre-commit hook accepts via `baseline-reviewed:` sign-off (FR13).
- `pytest` + `npm run test:visual` green per AGENTS.md gates.
- Determinism: 3× consecutive identical pytest + vitest pass counts after each story merge (NFR19-DETERMINISM-1).
- `external_service=spoolman` tag present in all Spoolman client structured logs (NFR19-OBS-1 grep invariant).
- `Depends(current_user)` (NOT `current_admin`) on all `/api/spools/*` routes (operator decision 2 enforcement; route-enforcement pytest gate from Init 6 covers this automatically).
- No `Depends(current_*)` on any `/api/share/<token>/*` route (NFR10 preservation; unchanged by Init 19 but worth grep-asserting since this initiative introduces the second auth-bearing surface adjacent to share-tokens after Init 18 Decision AA).

**Deferred-by-design follow-ups** (carried forward verbatim for whichever brainstorm/PRD revisits Spoolman later):

- **MVP-B / Phase B**: catalog detail × material match (free-form text). Trigger: per-model material context demand.
- **MVP-C / Phase C**: `recommended_material_profile` SoT structure. Trigger: catalog SoT design round picks up filament linkage.
- **MVP-D**: restricted writes (use/measure). Trigger: direct Spoolman UI ergonomic regression for operator OR Laura (NOT usage telemetry).
- **MVP-E / Phase E**: share-token inventory snapshot. Trigger: operator wants to advertise printable-right-now stock externally.
- **Phase D**: cost calc UX. Trigger: per-print cost rollup demand. Decision AF carries the data fields in MVP-A so Phase D has zero backfill cost.

## Appendix A — Checklist execution summary (per `checklist.md`)

| Section | Item | Status | Notes |
|---|---|---|---|
| 1 — Trigger and Context | 1.1 Triggering story | [N/A] | No triggering story (net-new initiative; trigger is brainstorm + 2026-05-04 SoT design carve-out) |
| 1 | 1.2 Core problem | [Done] | "Spoolman & catalog live in two separate tabs that never see each other" (B1 first-principles insight) |
| 1 | 1.3 Evidence | [Done] | Brainstorm artifact + Spoolman OpenAPI inspection + verified .190 instance state |
| 2 — Epic Impact | 2.1 Current epic | [N/A] | No current epic affected (net-new) |
| 2 | 2.2 Epic-level changes | [Done] | Add new Epic E31 (project-global numbering) |
| 2 | 2.3 Future epic review | [Done] | Phases B/C/D/E parked with explicit triggers; no current planning-stage epic blocked |
| 2 | 2.4 Invalidation / gap epics | [N/A] | No existing epic invalidated |
| 2 | 2.5 Sequencing | [Done] | Init 19 queues behind Init 18 close-out per ITCM autonomous mode convention |
| 3 — Artifact Conflict | 3.1 PRD | [Done] | Extension via Initiative 19 H2 append; no goal/MVP rewrite needed |
| 3 | 3.2 Architecture | [Done] | New Decisions AD + AE + AF; no existing decision revisited |
| 3 | 3.3 UI/UX | [Done] | New landing card + `/spools` page; no existing journey altered; no UX-spec doc exists for Init 19 (small surface, no Sally session needed) |
| 3 | 3.4 Other artifacts | [Done] | Env config + ops doc + configs-side compose PR + visual baselines |
| 4 — Path Forward | 4.1 Direct Adjustment | [Viable] | Chosen path; H2 append + new module |
| 4 | 4.2 Rollback | [Not viable] | Nothing to roll back |
| 4 | 4.3 MVP Review | [Not viable] | Net-new scope; no existing MVP to redefine |
| 4 | 4.4 Selected approach | [Done] | Option 1 — Direct Adjustment with new Initiative 19 |
| 5 — SCP Components | 5.1 Issue summary | [Done] | §1 above |
| 5 | 5.2 Epic + artifact summary | [Done] | §2 above |
| 5 (continued) | 5.3+ recommended approach + detailed proposals + handoff | [Done] | §3 + §4 + §5 above |

## Appendix B — Operator decision register (audit trail)

| # | Decision | Operator stance 2026-05-29 | SCP integration |
|---|---|---|---|
| OD1 | Initial slice scope | **MVP-A baseline cell** | Locked. §3 envelope + §4.1 H2 outline. |
| OD2 | Auth posture on `/spools` | **Members + admin visible (NOT admin-only)** — overrides brainstorm default | Locked. §3 + §4.3 Story 31.2 `Depends(current_user)`. Success-criteria grep enforced. |
| OD3 | Material-linkage representation | Out of MVP-A scope | Parked as Phase B trigger. |
| OD4 | Transport / topology | **Delegated to SCP** | Resolved as Decision AE (§4.2): P4b primary + P4a fallback + configs-side coordination PR. |
| OD5 | Caching + propagation | Not addressed by operator | Resolved as Decision AD (§4.2): P7c + P8b + SETNX leader-election. |
| OD6 | Test posture | Not addressed by operator | Resolved as Decision AD § Testing: P14a mock + P14d env-gated live smoke. |
| OD7 | Cost calculator | **Native fields first; data carry-through in MVP-A; UX deferred** | Resolved as Decision AF (§4.2): DTO + cache surface full price + weight fields; no UX. |
| OD8 | Spoolman bind verification | **Implicit via operator's LAN-only declaration** | Resolved as Story 31.1 § Pre-merge precondition (1-line configs-side check, NOT 3d-portal commit). |
| OD9 | Filament vs spool identity | Not explicitly addressed | Resolved per Reverse anti-pattern 18: distinct cache entries + DTO models; collapsing rejected. |
| OD10 | Naming | Not explicitly addressed | Kept as `spools/` (matches placeholder + AGENTS.md). |
| (new) | Write surface trigger redefinition | **Direct Spoolman UI ergonomic regression for operator OR Laura** (NOT usage telemetry) | Refines MVP-D parked-with-trigger language in §3 + §5 deferred-by-design list. |
| (new) | Cost-data canonical source | **Spoolman native price + weight + per-spool override** | Locked as Decision AF (§4.2). |
