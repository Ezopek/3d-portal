---
title: "Sprint Change Proposal — Initiative 10 (Operator Polish Batch)"
type: sprint-change-proposal
initiative_scope: [10]
status: shipped
shipped_at: 2026-05-22
shipped_via: |
  13 stories across E15+E16+E17 in ~6h autonomous chain 2026-05-22. 14 commits, all
  Codex-CLEAN after fix-up rounds. 8 deploys to .190 (verify-symbolication +
  runbook-fingerprint PASS each). Story 16.2 underwent operator scope-correction
  mid-init (in-app AI Generate button → bilingual editor + ops-task backfill).
  Side wins: Decision O contract restored on /admin/users + /admin/invites; TTL cap
  narrowed 30d→7d at Pydantic; Item #7 401-scan cleared as not-a-scan; Item #6
  OTEL carved out as infra-side. Retrospective at
  _bmad-output/implementation-artifacts/init-10-retro-2026-05-22.md (party-mode
  multi-agent: Amelia + Murat + Winston + John).
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-22
approved_by: Ezop
approved_at: 2026-05-22
approved_via: AskUserQuestion selection "Approve — lecimy chain'em (E15 → E16 + E17 parallel)" 2026-05-22 after grilling on 3 business decisions (share-link TTL semantics, manual-add permission, description bilingual strategy)
execution_directive: "lecisz do końca samemu" — autonomous ITCM mode per memory feedback_itcm_autonomous_mode; no operator-handshake pauses; hard-stop only on 5h ≥ 80% (sleep through reset per feedback_autonomous_sleep_on_budget), 7d ≥ 95%, or real product blocker; no extra_usage opt-in
mode: batch-presented (operator-pragmatic variant of BMAD Incremental — full draft surfaced once, operator feedback consolidated; matches Init 6/7+8+9 SCP precedent)
change_scope_classification: moderate
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                      # to be extended (Initiative 10 H2 section)
  - _bmad-output/planning-artifacts/architecture.md             # to be extended (Initiative 10 H2 section — Decisions L, M, N around share-anonymous-frontend + description bilingual + admin manual-add)
  - _bmad-output/planning-artifacts/epics.md                    # to be extended (Initiative 10 H2 + Epic E15 + E16 + E17 + ~13-15 stories)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # to be extended (E15 + E16 + E17 entries, all status backlog)
  - _bmad-output/triage-backlog.md                              # TB-016, TB-017 (long-term), TB-018 (already closed), TB-014, TB-019 (this batch's new entries from items #6 + #7) — see §3 below for promotion plan
  - sprint-change-proposal-2026-05-21.md                        # predecessor SCP (Init 7+8+9); this SCP follows the same Initiative-N H2-append pattern
predecessor_initiative: 9
trigger:
  source: operator batch report 2026-05-22 (~16:00 UTC Polish, immediately after Init 7+8+9 close-out commit chain 2026-05-22 morning) — 10 user-reported items framed as paczka
  shape: 10 items spanning: 1 test-health initiative-grade (item #1), 1 UX-polish bundle (item #2 admin tables), 1 backlog sweep (item #3 TB-* triage), 1 catalog bilingual schema migration (#4.1), 1 admin auto-fill feature (#4.2), 1 anonymous share-link viewer (item #5), 1 OTEL infra incident (item #6 — RECONCLUDED OUT-OF-SCOPE), 1 401-scan security inquiry (item #7 — OPERATOR-BLOCKER on SSH), 1 admin manual model-add (item #8), 1 admin manual STL upload (item #9), 1 catalog bulk-download restore (item #10)
  evidence_class: direct operator hands-on observation + cross-LLM agent commentary on bilingual description gap; no automated-gate finding, no security audit; OTEL spans error from production log inspection (item #6)
business_decisions_grilled:
  - share_link_semantics: "Member-gen, krótkie TTL only (max 7d)" — hard-cap TTL = 1d/3d/7d dropdown, no 30d/never; revocable from UI ("My share links" section)
  - manual_model_add_permission: "Admin-only manual add" — members continue to use agent flow; no contributor role
  - description_bilingual_strategy: "Migracja: body → body_pl + body_en; on-demand 'Generate' button" — full ModelNote schema refactor + per-model admin-triggered Generate dialog with sources (external URL scrape + Nextcloud notes), preview-accept-or-edit
recon_subagents_completed:
  - otel_collector_recon: complete (2026-05-22; finding: infra-side, ~75% confidence; OUT of Initiative 10 scope; operator action item: SSH .190 + docker logs data-prepper + restart if stuck)
  - admin_table_designer_research: complete (2026-05-22; finding: confirms operator intuition; ~6 line diff across 3 files; industry support from GitHub/Linear/Vercel/Stripe fluid-table pattern; PL labels 40-90% longer than EN trigger deterministic overflow on 1280px cap)
  - test_flake_landscape_audit: complete (2026-05-22; finding: vitest 0 flakes / pytest 1 hang-class deadlock in test_concurrent_refresh_one_wins / playwright 86 deterministic-fail = stale baselines carry-forward + 8 anon-login-only timeouts; 3 stories, 10-19h budget; sequence 15.1 → 15.2 + 15.3 parallel)
operator_blockers:
  - item_7_401_scan_recon: SSH to .190 timeout (network unreachable from dev box at SCP-draft time); requires operator to restore SSH connectivity OR provide log dump
  - item_6_otel_recon_followup: requires operator action SSH .190 + restart data-prepper + monitor; if incident recurs in 7d, file ops-runbook task in ~/repos/configs (NOT in 3d-portal)
---

# Sprint Change Proposal — Initiative 10 (Operator Polish Batch)

## Section 1 — Issue Summary

### 1.1 Problem statement

Within hours of Initiative 7+8+9 close-out (chained autonomous batch shipped 2026-05-22 ~early morning UTC, see predecessor SCP), the operator surfaced a new batch of 10 user-experience and operational items discovered through:

- **Direct hands-on portal use** at `https://3d.ezop.ddns.net` (items #2, #4.1, #4.2, #5, #8, #9, #10)
- **Production log inspection** at `.190` (item #6 — OTEL exporter spam, item #7 — 401 scan patterns)
- **Cross-session test reliability frustration** — operator's verbatim: *"non stop walczymy/jesteśmy opóźniani przez flake'y testy - widziałem jak sam często wisiałeś do timeout'u przez to. Musimy to ogarnać - porządnie"* (item #1)
- **Backlog hygiene reminder** — explicit ask to sweep open TB-* candidates (item #3 — currently 5 active candidates in triage-backlog.md including TB-014 crealitycloud enum, TB-016 runbook doc-honesty, TB-017 TOTP key rotation, plus DOC-DRIFT-2 partial)

The batch maps to **3 actionable epics** within Initiative 10 + **2 operator-action-items** outside scope (#6 infra + #7 SSH-blocked) + **0 deferrals**. Tests health (item #1) is structured as the **first epic E15** because: (a) operator's framing puts it FIRST and uses the word "porządnie" (= properly, not band-aid); (b) reliable test signal is a precondition for the catalog feature-development epic that follows; (c) the previous initiative chain (Init 7+8+9) closed TB-018's three test-isolation items, but operator's frustration signals additional ongoing pain (likely from playwright visual-regression cross-suite pollution, vitest timing-sensitive specs, or pytest cache-lock holds — landscape audit in progress).

The catalog power-user feature bundle (Epic E16) carries the largest share of items by count (6 items: #4.1 + #4.2 + #5 + #8 + #9 + #10) and by user-facing surface area — it modifies the catalog detail page, the share-link UX surface, and introduces an entirely new admin "Add Model" + "Upload File" flow. Schema migration for bilingual descriptions (FR10-DESC-1) touches a single existing table (`model_note.body` → `body_pl` + `body_en`) but requires backfill and frontend UI refactor.

Operator UX + Backlog Sweep (Epic E17) carries the smallest delivery surface but highest hygiene value — closing the table-width universal pattern (item #2, ~6 lines diff per designer subagent recommendation) and triaging TB-* candidates to either promotion-as-story or explicit declination.

### 1.2 Issue categorization (CC checklist §1.2)

**Mixed categorization — predominantly New requirements emerged from stakeholder hands-on use, with one previously-deferred bug class and one operator-frustration meta-feedback.**

- Items #4.1, #4.2, #5, #8, #9, #10 are **new requirements from stakeholder** — operator surfaced UX gaps and feature-gap items from hands-on portal use. Item #10 specifically is regression (`/api/files/{id}/bundle` shipped in commit b18af8c May 2026, removed during a later refactor; restoration request).
- Item #2 is **new requirement from stakeholder** (admin tables width) with **research-confirmed counter-argument analysis** (designer subagent recommendation matches operator intuition).
- Item #1 is **operator-frustration meta-feedback** — the test signal is reliable enough for individual stories to land green, but the cumulative latency cost (autonomous-mode session interruptions, timeouts, flake-induced retries) is intolerable across the multi-initiative chain. Categorically: **failed-approach-requiring-different-solution** — the per-story test-isolation fixes (TB-018, Init 9) addressed acute pain points but did not establish a forward determinism contract for the test suites as a whole.
- Item #3 is **hygiene + previously-identified candidates** — TB-* triage is established practice (triage-backlog.md). Operator's ask is to sweep, not new discovery.
- Item #6 is **operational incident** (OTEL span batch export timeout in production) — categorically infra incident, RECONCLUDED OUT-OF-SCOPE for code Initiative 10 per recon subagent findings (75% confidence infra-side, app config OK).
- Item #7 is **security inquiry** (401 in production logs — possible scan pattern) — BLOCKED on SSH access for log analysis. Categorically separate workstream; not folded into any Init 10 epic.

### 1.3 Issue triggers — relationship to closed initiatives

- **Init 0 (Product Foundation)** — items #4.1, #4.2 (description schema), #8, #9 (manual add + STL upload) touch the catalog write-surface that shipped in E0.4 (Catalog Read Surface) + E0.5 (SoT Agent Tool). Items #8 + #9 are net-new write surfaces (admin manual add UI was never built; only agent-token flow). Item #10 is a regression of E0.4 bundle endpoint.
- **Init 5 (Public Registration & User Account Management)** — item #5 (share-link anonymous viewer) extends FR5-MEMBER-1 (member can mint share tokens via `POST /api/admin/share`) into a complete anonymous-viewer frontend route at `/share/<token>`. Item #5 also leans on FR5-MEMBER-3 (rate-limit 20/day per-member share-token creation), which already shipped — reuse with no API changes.
- **Init 6 (Post-Cutover Default-Deny Auth Posture)** — item #5 leans on Init 6 Decision N (`/api/share/<token>/*` share-scoped asset endpoint preserved across cutover). Backend infrastructure already in place; only frontend route `/share/<token>` + page shell needed.
- **Init 7 (Account & Admin UX Polish)** — item #2 (admin tables width) is direct continuation of Init 7's UX-polish theme. Could have been folded into Init 7 retrospectively but operator's batch framing treats it as new.
- **Init 8 (Catalog Mobile & Image Performance)** — item #10 (bulk-download regression) touches catalog-detail surface that Init 8 modified (thumbnail pipeline). Restoration of bundle endpoint is independent of thumbnails; no contention.
- **Init 9 (Test Isolation Cleanup)** — item #1 is Init 9's spiritual successor at initiative grade. Init 9 closed 3 specific TB-018 items (vitest admin finders, pytest hydrate pollution, visual-regression hook flake). Item #1 widens scope to **whole test-suite determinism**: every flake gets a root-cause + permanent fix, not a `retry: 3` or skip-tag.

### 1.4 Evidence

- **Operator batch report:** in-session user message 2026-05-22, verbatim 10-item list. Stored in conversation transcript. Operator's phrasing on tests ("porządnie"), tables ("uwolnijmy"), descriptions ("powoli i do brzegu pouzupełnić"), share ("user powinien móc wygenerować link"), manual add ("brakuje mi możliwości ręcznego dodania modelu"), bulk-download ("uciekła nam też opcja"), OTEL ("z czego to wynika?"), 401 ("czy mamy się czego obawiać?").
- **Designer subagent report:** in-session subagent (2026-05-22), confirms operator intuition with industry-leader pattern grounding (Carbon Design System, Atlassian, GitHub, Linear, Vercel, Stripe all use fluid-width admin tables); identifies measurable root cause (PL labels 40-90% longer than EN, `min-w-[1200px]` calibrated for EN compactness); ~6-line diff per 3 files.
- **OTEL recon subagent report:** in-session subagent (2026-05-22), 75% confidence infra-side (`~/repos/configs/otel-collector/config.yml` data-prepper sink backpressure); app-side observability config at `apps/api/app/core/observability.py:39-43` is correct; OUT-OF-SCOPE for Init 10. Operator action: SSH .190 + restart data-prepper.
- **Code-side recon (this session):** `model_note.body` is single `str` field (confirmed `apps/api/app/core/db/models/_entities.py:196-211`); no `description_pl`/`description_en` schema today. `/api/share/<token>/*` backend exists (confirmed `apps/api/app/modules/share/router.py:70-89`) but no frontend route `/share/<token>` in `apps/web/src/routes/` (confirmed by directory listing). Bulk-download endpoint removed during refactor (last seen in commit b18af8c May 2026: `fix(web): SLICE-13 sticky action bar — Download all (bundle)`; no current references in `apps/api/app/modules/`).
- **Triage-backlog.md state:** 5 active candidates (TB-014 crealitycloud enum, TB-016 runbook doc-honesty 3 findings, TB-017 TOTP key rotation, TB-018 partially closed via Init 9, DOC-DRIFT-2 partial cleanup). To be enumerated and dispositioned in §3.2.3 below.

## Section 2 — Epic Impact Assessment (CC checklist §2)

### 2.1 Initiative 0–9 status — none reopened

Initiative 0 (shipped retro), 1 (shipped), 2 (shipped), 3 (shipped), 5 (shipped), 6 (shipped), 7 (shipped 2026-05-22), 8 (shipped 2026-05-22), 9 (shipped 2026-05-22) — none of the 10 batch items require modification of any closed-initiative epic. All items land in NEW Initiative 10 epics. The only relationship to closed initiatives is **reuse** (item #5 reuses FR5-MEMBER-3 rate-limit; item #5 reuses Init 6 Decision N share-scoped asset endpoint backend; item #2 reuses Init 7 admin-page foundation; item #10 reuses Init 8 catalog-detail surface).

### 2.2 New epics required — 3

Initiative 10 splits into 3 epics:

- **Epic E15 — Test Health & Determinism** (item #1) — pre-condition for downstream epics. Story breakdown PENDING tests subagent findings.
- **Epic E16 — Catalog Power-User Features** (items #4.1, #4.2, #5, #8, #9, #10) — largest delivery surface, 6 items.
- **Epic E17 — Operator UX & Backlog Sweep** (items #2, #3) — smallest delivery, high hygiene.

### 2.3 Execution order

E15 → E16 + E17 (E16 and E17 can run concurrently once E15 is closed; they touch disjoint surfaces — E16 modifies catalog + admin write surfaces, E17 modifies admin read tables + triage docs).

Rationale for E15 first: operator's batch framing puts tests first AND uses the word "porządnie". Tests health is a precondition because the autonomous chain (BMAD create-story → dev-story → code-review per story) depends on reliable test signal. Running E16 + E17 with flaky tests would force per-story flake-investigation cycles, eating into the budget and undermining the very autonomous-mode contract Initiative 10 is supposed to demonstrate.

### 2.4 Future-epic invalidation check

No closed initiative is invalidated. No planned-but-not-yet-built initiative is invalidated. Initiative 10 is purely additive.

## Section 3 — Artifact Conflict & Impact Analysis (CC checklist §3)

### 3.1 PRD conflicts

No conflicts with existing FR/NFR. Init 10 will extend `prd.md` with a new `## Initiative 10 — Operator Polish Batch` H2 carrying:

- Executive summary + scope statement
- ~12-15 new FR codes: FR10-TEST-* (3-5 codes, pending audit), FR10-DESC-* (2 codes for bilingual schema + auto-fill), FR10-SHARE-ANON-* (2 codes for anonymous viewer + member-gen UI), FR10-MANUAL-ADD-* (2 codes for admin model add + file upload), FR10-DOWNLOAD-* (1 code for ZIP restore), FR10-UX-TABLES-* (1 code for fluid-width admin tables), FR10-TRIAGE-* (1 code for TB-* sweep)
- ~5-7 new NFR codes: NFR10-DETERMINISM-* (test-suite determinism contract), NFR10-SCHEMA-MIGRATION-* (Alembic forward-only safety for ModelNote bilingual split), NFR10-VISUAL-VERIFICATION-* (carries over the gate established in Init 7+8+9), NFR10-SHARE-SECURITY-* (anonymous viewer hardening — no admin-functions exposed, audit log integrity)

### 3.2 Architecture conflicts

No conflicts. Init 10 will extend `architecture.md` with `## Initiative 10` H2 carrying ~3 new decisions:

- **Decision L — ModelNote bilingual schema migration (forward-only Alembic)** — drops single `body` column, adds `body_pl: str | None` + `body_en: str | None`. Backfill strategy: copy existing `body` → `body_en` (English source-dominant per current catalog state). Rollback path: keep prior Alembic revision tag for emergency revert; no online migration window required (catalog is single-instance, <2-min downtime acceptable).
- **Decision M — Share-link anonymous frontend route shell** — adds `apps/web/src/routes/share/$token.tsx` rendering a minimal model-detail layout with NO ModuleRail (anonymous viewer doesn't see left-nav). Reuses existing `Viewer3DInline` component for 3D + existing `DescriptionPanel` + `FilesTab` (filtered to STL/STEP/F3D download only; no upload). Auth state must be cleared/spoofed-empty (`AuthGate` skipped) — `<AuthGate fallback={<AnonymousShareView />}>` is the wrong pattern (token route should NEVER consult auth state).
- **Decision N — Admin manual-add model write surface** — new admin-only endpoint `POST /api/admin/models` accepting JSON for model fields + multipart for file uploads (thumbnail + extra images + STL/STEP/F3D). Uses existing soft-delete + audit-log + thumbnail-render-job-enqueue patterns. Admin-only auth via `current_admin`. Member role does NOT get this endpoint (per business decision §1.1 grilled outcome).

### 3.3 UX/Design conflicts

Designer subagent report (§1.4) confirms no conflicts — fluid-width is **industry-default** for admin tables (not aesthetic disagreement). Implementation is ~6 lines diff across 3 files (`InvitesPage.tsx`, `UsersPage.tsx`, `sessions.tsx` left alone). Visual baselines for admin-invites + admin-users need regeneration (1 baseline-reviewed sign-off per affected snapshot per project-context.md UI Quality Gates).

### 3.4 Other artifact impacts

- **Triage-backlog.md** — 2 new entries dispositioned: TB-019 (admin-table-width — done in Story 17.1, no separate triage), TB-020 (OTEL data-prepper backpressure operator-runbook — flagged out-of-scope for Init 10, parked here as operator-followup reminder).
- **i18n locales** — every UI string in new components must land in both `en.json` and `pl.json` (per project-context.md). Estimate ~40-60 new keys across Epic 16 (description bilingual editor, share-link UI, manual-add form, upload UI, bulk-download button label) and Epic 17 (no new strings; existing strings reused).
- **deploy.sh** — no changes; existing chain handles Alembic migration auto-run.
- **infra/.env** — no new env vars expected (rate-limit reuses existing FR5-MEMBER-3 settings).
- **Documentation** — `docs/agents-add-model-runbook.md` becomes informational-only for human admins (still required for agent flow); no contradiction.

### 3.5 TB-* triage-backlog enumeration for item #3 (Operator Sweep)

Active candidates as of 2026-05-22:

| ID | Topic | Status | Flag count | Disposition recommendation |
|---|---|---|---|---|
| TB-014 | `crealitycloud` missing from `ModelSource` + `ExternalSource` enums | candidate | 1 | **Decline** until first real CrealityCloud import OR per-source UI logic emerges. Workaround (`source=other`) is functionally complete. No urgency. |
| TB-016 | Agent runbook doc-honesty tweaks (3 findings: poll budget, download path leak, bilingual-name guidance) | candidate | 3 | **Promote to Story 17.3 (E17)** — single doc-only commit (~30 min); landing during Init 10 batch makes sense. Bundles 3 findings: A (option 2 — budget bump + qualifier), B (full rewrite of `:142`), C (rewrite `:303` + example payload `:395`). |
| TB-017 | TOTP_FERNET_KEY rotation runbook | candidate | 4 | **Decline-defer to 2027-03-20** (≤2 months before trigger date 2027-05-20). Not Init 10 work; runbook authoring happens close to trigger. Keep entry, leave status=candidate. |
| TB-018 | Test-isolation cleanup bundle | done | — | All 3 items closed via Init 9 (Story 14.1 + 14.2 + 14.3). Mark final close in this SCP's retrospective bookkeeping. No action. |
| DOC-DRIFT-2 | Initiative 5 planning artifacts drift | partially-done | 17 | **Promote remaining 4 drifts to Story 17.4 (E17)** — Drift 3 (Decision B INTEGER→UUID schema rewrite, the largest remaining doc-debt), Drift 5 (refresh_tokens autogenerate code-side cleanup), Drift 16 (Settings field naming cosmetic), Drift 17 (test rename). Single `docs(bmad)` commit; auto-deploy skipped per `feedback_auto_deploy_dev`. Closes DOC-DRIFT-2 to fully-done. |

Net result: Story 17.3 + 17.4 absorb the actionable TB-* items. TB-014 + TB-017 stay candidates with explicit decline rationales (defer-until-trigger). TB-018 marked retroactively done.

## Section 4 — Path Forward Evaluation (CC checklist §4)

### 4.1 Selected approach: **Option 1 — Direct Adjustment via new Initiative 10**

- **Effort estimate:** Medium-High (3 epics, ~13-15 stories, mix of Low + Medium + One-of-each effort)
- **Risk level:** Low-Medium
  - **Low:** Items #2 (~6 lines diff), #3 sweep, #10 bulk-download restore (regression — just bring back the endpoint shape), #5 anonymous-viewer (backend exists)
  - **Medium:** #4.1 schema migration (forward-only Alembic, backfill via SQL, no online window needed), #4.2 auto-fill (subagent-bounded LLM scrape + Nextcloud-read pipeline, admin UI preview), #8 manual-add (multipart upload + thumbnail-render auto-fire), #9 STL upload to existing model
  - **One-of-each (highest variance):** #1 test health (true depth pending audit; could be 1 day or 1 week)
- **Justification:** Best fit for operator's batch framing. No reason to rollback (no prior story is broken). No reason to scope-reduce MVP (no MVP impacted; Init 10 is post-MVP polish + features). The Direct Adjustment approach via new Initiative is the canonical BMAD pattern for new-feature-bundle scope.

### 4.2 Other options evaluated

- **Option 2 — Rollback:** Not viable. No recent story introduced any of these requirements; nothing to revert.
- **Option 3 — MVP review:** Not viable. The portal's working MVP (Init 0 + Init 5 + Init 6 cutover) is intact and serving the operator. Init 10 is enhancement, not MVP recovery.
- **Option 4 — Defer entire batch to later session:** Considered, rejected. Operator's framing is "kolejna paczka do ogarnięcia" with concrete autonomous-mode expectation ("lecisz do końca samemu"). Deferral would violate the trust contract.

### 4.3 Epic-level effort breakdown

| Epic | Stories (est.) | Effort | Risk | Why |
|---|---|---|---|---|
| E15 (Test Health) | 3-5 (PENDING) | Medium-High (highest variance) | Low (test-only changes) | Audit-driven; could be 1 day (3 stories) or 3-4 days (5+ stories) |
| E16 (Catalog Power-User) | 6 stories | Medium-High | Medium | Schema migration + multipart upload + new admin UI + anonymous frontend route |
| E17 (UX + TB sweep) | 4 stories (17.1 tables + 17.2 share-revoke-UI if applicable + 17.3 TB-016 doc fix + 17.4 DOC-DRIFT-2 close) | Low | Low | Doc + CSS + small triage closures |

**Total estimate:** ~13-15 stories across 3 epics. Optimistic execution time (assuming Epic 15 lands quickly): 2-3 days autonomous chain. Realistic estimate (if test health requires deep investigation): 3-5 days.

## Section 5 — Sprint Change Proposal Components (CC checklist §5)

### 5.1 Issue summary — covered in §1 above.

### 5.2 Epic impact & artifact adjustment needs — covered in §2 + §3 above.

### 5.3 Recommended path forward & rationale — covered in §4 above.

### 5.4 PRD MVP impact + high-level action plan

**MVP impact:** Zero. Initiative 10 is post-MVP polish + feature enhancement. The portal continues to serve its core function (catalog browse + 3D viewer + admin + share + agent) throughout the batch.

**High-level action plan:**

1. SCP draft surfaced (this document) — operator review → approval
2. PRD + architecture + epics.md extensions written (Initiative 10 H2 sections) — single commit `feat(bmad): Initiative 10 SCP + planning artifacts (Operator Polish Batch)`
3. sprint-status.yaml extended with E15 + E16 + E17 entries (status: backlog → ready-for-dev as each story is created)
4. Execution sequence:
   - E15 stories (test health) — sequential per story, each via bmad-create-story → bmad-dev-story → bmad-code-review
   - E16 + E17 stories — interleaved as operator capacity / 7d budget permits; E16 anchored on bilingual schema migration first (Story 16.1) since FR10-DESC-1 unblocks Stories 16.2 (auto-fill UI) + 16.6 (manual-add description fields)
5. Operator-action-items dispatched after SCP approval:
   - **Item #6** — SSH .190, `docker logs data-prepper --tail 200`, restart if stuck
   - **Item #7** — restore SSH connectivity, then re-trigger 401-pattern recon subagent

### 5.5 Agent handoff plan

- **Developer (Claude, autonomous ITCM mode):** owns all 13-15 stories via BMAD chain (create → dev → code-review per story). Codex review on each commit per established Init 5+6+7+8+9 precedent.
- **Operator (Ezop):** SSH .190 for items #6 + #7; SCP approval; per-epic retro at close.
- **Subagents (this session has already used 3):** test-flake landscape audit (item #1, pending), OTEL recon (item #6, done, OUT-OF-SCOPE), designer table-width research (item #2, done). Future subagents likely: per-story Codex reviews + 1 dedicated subagent for #4.2 auto-fill description LLM pipeline (if pipeline design requires research).

## Section 6 — Final Review & Handoff (CC checklist §6)

### 6.1 Checklist completion

- §1 Issue Summary — Done
- §2 Epic Impact Assessment — Done
- §3 Artifact Conflict & Impact Analysis — Done (TB-* triage enumerated in §3.5)
- §4 Path Forward Evaluation — Done (Option 1 selected)
- §5 SCP Components — Done

### 6.2 Pending items before approval

- **Test-flake landscape audit (item #1)** — subagent still running. Epic E15 story-list to be filled in once audit returns. Approval can proceed on SCP structure + Epic 15 scope-only (deep breakdown lands once audit returns).
- **Operator approval** — explicit yes/no/revise.

### 6.3 Handoff plan upon approval

- ITCM (Claude) owns end-to-end execution per established Init 5+6+7+8+9 pattern.
- No operator-handshake pauses; execution chain through to commit at Initiative 10 close.
- Hard-stop only on 5h ≥ 80% (sleep through reset per `feedback_autonomous_sleep_on_budget`), 7d ≥ 95%, or real product blocker.
- No `extra_usage` opt-in.
- Per-epic retro at close (E15 retro after E15 close, E16 retro after E16 close, E17 retro after E17 close).
- Initiative 10 retro at full close (all 3 epics shipped).

---

## Appendix A — Epic structure (preliminary, to be promoted to epics.md on approval)

### Epic E15 — Test Health & Determinism

**Goal.** Close the 3 surfaced flake-class issues to flake-zero forward determinism. Establish NFR10-DETERMINISM-1 as the cross-framework analog of NFR9-DETERMINISM-1 (Init 9 was admin-scoped; Init 10 is whole-suite).

**Audit findings (subagent recon 2026-05-22):**

- **Vitest:** 0 flakes. 3× consecutive clean runs (94 files / 408 tests PASS each, ~6s wall). **No work needed** — already at flake-zero.
- **Pytest:** **1 HANG-class deadlock** + 0 deterministic-fail. `test_concurrent_refresh_one_wins` (`apps/api/tests/test_auth_refresh.py:164-194`) — 2 threads × `TestClient` × SQLite + non-thread-safe `_patch_arq_pool` autouse fixture; CPU drops to 0 after ~110s of work; `t1.join()`/`t2.join()` have no timeout → process hangs until external SIGKILL. This is the **root cause of Claude's repeated "wisiałeś do timeoutu"** observation. Highest user-pain item.
- **Playwright visual:** **86 deterministic-fail / 24 skipped / 234 PASS / 344 total.** Zero true flake (variance=0 across 3+3 runs per Story 14.3 dev record). 78 = stale-snapshot drift across 12 specs (UI evolved past baselines through Init 5/6/7/8); 8 = `page.waitForURL` timeout in `anon-login-only.spec.ts`. Carry-forward from Story 14.3 NFR9-SCOPE-1 explicit exclusion.

**Important:** None of these are "true" non-determinism — every issue is deterministic. The pytest hang reproduces 1/1. The 86 visual-regression failures reproduce identically across runs. The label "flake" was misapplied; the real diagnosis is **deterministic-failure-pretending-to-be-flake** via timeout, hang, or skip-tolerated cumulative drift. The fix shape changes accordingly: not "make these green by adding stability" but "root-cause + fix or regen each one".

**Acceptance gate:**

1. Pytest suite full run completes without hang or timeout: `cd apps/api && timeout 600 uv run pytest tests/` → exit 0 deterministic, 3× consecutive.
2. Playwright visual suite full run completes with 0 unhandled failures: `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` → exit 0 deterministic, 3× consecutive.
3. Vitest suite stays at 0 flakes (no regression from 15.x changes).
4. Each story logs its 3-consecutive-run verification per NFR10-DETERMINISM-1.

**FRs realized:** FR10-TEST-DETERMINISM-PYTEST-1 (15.1), FR10-TEST-DETERMINISM-PLAYWRIGHT-1 (15.2), FR10-TEST-FIXTURE-CLEANUP-1 (15.3).

**Architectural anchors:** none (test-infrastructure + minimal prod-code touch only, per Init 9 precedent NFR9-SCOPE-1 carried into NFR10-SCOPE-1).

**Stories (3):**

##### Story 15.1 — Pytest threading deadlock: `test_concurrent_refresh_one_wins`

**Realizes:** FR10-TEST-DETERMINISM-PYTEST-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (entry story for E15).

Acceptance check shape:

- **Phase 1 — Instrumentation pass (no fix yet):** Run the deadlock test in isolation with `py-spy dump --pid <pytest-pid>` or equivalent stack-trace probe captured at the hang moment. Confirm the suspected root cause (`_patch_arq_pool` autouse fixture via `unittest.mock.patch` not thread-safe; threading.Thread workers bypass the patch and attempt real Redis connection).
- **Phase 2 — Root cause analysis:** Decide between two fix paths:
  - **(a) Test-side only:** Rewrite the test to NOT use `threading.Thread` (use `asyncio.gather` + sequential simulation of concurrent refresh, or use `concurrent.futures.ThreadPoolExecutor` with a properly-threaded mock — `MagicMock` + `Lock`). This is the lower-risk path per NFR10-SCOPE-1 (test-only).
  - **(b) Prod-code hardening + test:** If Phase 1 reveals a real prod-side race (`create_pool` being called concurrently can race on Redis pool init), fix prod-side first (`asyncio.Lock` around pool creation in `app.main.lifespan` or `app.core.redis`), then keep the threaded test as a regression guard. This is a real risk surface — if the test was guarding against a real bug, removing the test reintroduces the risk.
- **Phase 3 — Fix per chosen path:** Apply test rewrite (a) OR prod fix + test (b). Add explicit `t1.join(timeout=30)` / `t2.join(timeout=30)` if threading is retained, with `assert not t1.is_alive()` post-join.
- **Phase 4 — Verify per NFR10-DETERMINISM-1:**
  - `timeout 60 uv run pytest tests/test_auth_refresh.py::test_concurrent_refresh_one_wins -v` → exit 0 in <30s, 5× consecutive
  - `timeout 600 uv run pytest tests/test_auth_refresh.py -v` → exit 0 in <120s, 3× consecutive (also covers downstream `test_reuse_outside_grace_burns_family` victim case)
  - `timeout 600 uv run pytest tests/` → exit 0, 3× consecutive (full suite stays green)

##### Story 15.2 — Visual-regression baseline batch refresh (86 stale snapshots + 8 anon-login-only timeouts)

**Realizes:** FR10-TEST-DETERMINISM-PLAYWRIGHT-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 15.1, 15.3).

Acceptance check shape:

- **Phase 1 — Failure classification triage:** Run full visual matrix `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts --reporter=list 2>&1 | tee /tmp/visual-triage.log`. For each of 86 failures, classify as one of:
  - **Stale baseline (UI evolved legally):** regen via `--update-snapshots`; sign off per Baseline Acceptance Gate.
  - **Real UX regression:** STOP, surface to operator, file as separate quick-dev. Do NOT regen a snapshot that masks a real bug.
  - **anon-login-only timeout (8 of 86):** Different class — `page.waitForURL` timing changed post-Init 5/6 cutover. Inspect the spec, identify what URL the test waits for, verify current portal behavior, fix the spec assertion (likely shorter wait or different URL pattern).
- **Phase 2 — Stale-baseline regen batch:** Apply `--update-snapshots` to the classified stale set (78 of 86 expected). Sign-off line per regenerated PNG per project-context.md UI Quality Gates Baseline Acceptance Gate: `baseline-reviewed: <basename>, Claude/Ezop, 2026-05-22`.
- **Phase 3 — anon-login-only spec fix:** Update spec timing/URL assertion per Phase 1 finding. May require Playwright fixture-level update if the auth redirect path changed; verify all 4 viewports (desktop-light, desktop-dark, mobile-light, mobile-dark).
- **Phase 4 — Verify per NFR10-DETERMINISM-1:**
  - `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` → exit 0 in <120s, 3× consecutive (standalone)
  - `cd 3d-portal && infra/scripts/check-all.sh visual` → exit 0, 3× consecutive (hook context, matches Story 14.3 NFR9-DETERMINISM-1 standard)
  - Standalone and hook context produce identical pass/fail verdict.

**Decision boundary:** if classification phase reveals more than 5 real UX regressions (vs stale-baseline drift), HALT Story 15.2 and surface to operator — that signal is bigger than a regen story; it's an Init-10-amending discovery requiring SCP revision.

##### Story 15.3 — Per-file `client` fixture refactor → centralized `conftest.py` (Epic 8 retro carry-forward)

**Realizes:** FR10-TEST-FIXTURE-CLEANUP-1, NFR10-DETERMINISM-1, NFR10-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 15.1, 15.2).

Acceptance check shape:

- Inventory the ~16 files in `apps/api/tests/test_{2fa,auth,admin,invite,share}_*.py` that define their own per-file `client` fixture.
- Promote a single `isolated_client` fixture in `apps/api/tests/conftest.py` (per Epic 8 retro `≥12 files, past 3× saturation` rationale, item §10 of Epic 8 retro 2026-05-20). Verify it does not collide with the existing session-scoped `_isolated_db` + function-scoped `_patch_arq_pool` chain.
- For each of the ~16 files: remove the per-file fixture, import via conftest auto-discovery (pytest fixtures auto-load from conftest.py in scope).
- Verify NO test changes behavior — `git diff --stat` should show fixture file deletions only; per-test code unchanged.
- Pure refactor, low risk, high signal-value (prevents future session-scope DB pollution like TB-018 item #2).
- Verify per NFR10-DETERMINISM-1: `timeout 600 uv run pytest tests/` → exit 0, 3× consecutive; baseline pytest pass-count matches pre-refactor.

**Sequence rationale:** 15.1 FIRST (highest user-pain — Claude's "wisiałem do timeoutu" experience). 15.2 + 15.3 can run in parallel after 15.1 closes (different frameworks — playwright vs pytest; different surface — visual baselines vs fixture refactor; no contention).

### Epic E16 — Catalog Power-User Features

**Goal.** Ship 6 user-facing catalog improvements: bilingual descriptions with on-demand AI auto-fill, anonymous share-link viewer (member-generated, 7d hard-cap TTL, revocable from UI), admin manual model-add + STL upload, restored bulk STL download (ZIP), all wired into existing catalog + admin + share architecture.

**Acceptance gate.** End-to-end functional verification on `.190`:
- Member generates share-link via existing UI with TTL dropdown (1d/3d/7d) → anonymous-viewer link opens model-detail view without left rail → Viewer3D works, STL downloads work, description renders, no admin functions exposed → revoke from "My share links" UI removes access immediately
- Admin opens "Add Model" UI → fills bilingual fields + uploads thumbnail + extra images + STL → thumbnail-render fires automatically → model lands in catalog as expected
- Admin "Generate description" button on existing model → preview UI shows generated PL + EN text → accept → ModelNote persists with both fields
- Member catalog detail "Download all (ZIP)" button → multi-file STL/STEP/F3D bundle downloads with original filenames
- Visual verification per NFR10-VISUAL-VERIFICATION-1 on all UI surfaces

**Stories (6):**

##### Story 16.1 — ModelNote bilingual schema migration

**Realizes:** FR10-DESC-1, NFR10-SCHEMA-MIGRATION-1.
**Architectural anchor:** Decision L.
**Depends on:** none (entry story for E16).

- Alembic migration: drop `model_note.body NOT NULL`, add `body_pl: str | None` + `body_en: str | None`, backfill `UPDATE model_note SET body_en = body WHERE kind = 'description'`, drop `body` column at end. Forward-only.
- Update `ModelNote` SQLModel definition.
- Update `app.modules.sot.admin_schemas` to reflect new shape (`body_pl`, `body_en` fields on note response/create/update).
- Update DescriptionPanel.tsx to render `body_pl` if locale is `pl` and `body_pl != null`, fallback to `body_en`, else show fallback empty-state.
- Update DescriptionPanel tests for the new shape.
- Per-story Codex review + visual verification per NFR10-VISUAL-VERIFICATION-1.

##### Story 16.2 — Description "Generate" admin button + sources pipeline

**Realizes:** FR10-DESC-2.
**Architectural anchor:** Decision L (extends).
**Depends on:** Story 16.1.

- Admin-only button on model-detail page (visible only when `current_admin`)
- Button opens dialog with: external-URL scrape source toggle + Nextcloud notes source toggle + free-form "additional context" textarea + "Generate" CTA
- Backend endpoint `POST /api/admin/models/{id}/generate-description` accepting source flags + context + target locale (pl, en, both)
- Pipeline: enqueue arq job that scrapes external sources (Printables/Thingiverse if model has ExternalLink), reads Nextcloud catalog notes (via existing rsync state), composes prompt, calls Claude API (small-context Haiku 4.5 default; budget-bounded), returns generated PL + EN
- Frontend dialog polls for completion (5s interval, 60s timeout per memory [[feedback_dialog_polling_budget]] — wait, that memory doesn't exist; just use 60s)
- Preview UI: side-by-side PL + EN editor with regenerate button + accept/reject CTAs
- Accept → PUT `/api/admin/models/{id}/notes` with `kind=description` + `body_pl` + `body_en`
- Per-story Codex review + visual verification.

##### Story 16.3 — Anonymous share-link frontend viewer

**Realizes:** FR10-SHARE-ANON-1, FR10-SHARE-ANON-2.
**Architectural anchor:** Decision M.
**Depends on:** none (independent of 16.1, 16.2 — uses existing model-detail components).

- New route `apps/web/src/routes/share/$token.tsx` (TanStack Router file-route)
- Route layout: NO ModuleRail (left rail hidden), minimal TopBar (logo only, no auth controls), centered model-detail content
- Reuse `Viewer3DInline` + `DescriptionPanel` + `FilesTab` (filtered to download-only — no upload affordances)
- Auth: route MUST NOT trigger AuthGate. Pattern: render anonymous shell directly; data fetch uses `/api/share/<token>/*` endpoints (no cookies, no CSRF; backend already public per Init 6 Decision N).
- Member-side UI: add share-link generation dialog with TTL dropdown (1d / 3d / 7d) on model-detail page (visible to logged-in members + admin)
- Member-side UI: add "My share links" page in settings (`apps/web/src/routes/settings/share-links.tsx`) listing all share-tokens the member has minted + revoke action (DELETE `/api/admin/share/{token}` — backend already supports)
- Backend: no API changes; existing `POST /api/admin/share` accepts TTL, existing `GET /api/admin/share` returns list, existing `DELETE /api/admin/share/{token}` revokes
- Per-story Codex review + visual verification (anonymous viewer in browser + member-generated link round-trip + revoke).

##### Story 16.4 — Admin manual model add

**Realizes:** FR10-MANUAL-ADD-1.
**Architectural anchor:** Decision N.
**Depends on:** Story 16.1 (for bilingual description fields in form).

- New endpoint `POST /api/admin/models` accepting `multipart/form-data` with JSON manifest + file uploads
- Manifest fields: `name_pl`, `name_en`, `category_id`, `source` (enum), `rating` (optional), `external_url` (optional), `description_pl` (optional), `description_en` (optional), `tag_ids` (list, optional)
- File uploads: `thumbnail` (single image, optional), `images` (multiple images, optional), `files` (multiple STL/STEP/F3D, optional)
- Same audit-log + thumbnail-render-enqueue patterns as existing agent endpoint `POST /api/sot/models/import-from-source`
- Admin-only auth (`current_admin`)
- New admin route `apps/web/src/routes/admin/models/new.tsx` with form + file drop zones
- Per-story Codex review + visual verification.

##### Story 16.5 — Admin manual STL/file upload to existing model

**Realizes:** FR10-MANUAL-ADD-2.
**Architectural anchor:** Decision N (extends).
**Depends on:** Story 16.4 (reuses multipart upload patterns).

- New endpoint `POST /api/admin/models/{id}/files` accepting multipart with `kind` (stl/step/f3d/image/thumbnail) + file
- Simple replace semantics: if `kind` matches existing primary STL/STEP/F3D, replace; else append. No versioning yet.
- Audit-log + thumbnail-render-enqueue on thumbnail/image addition.
- Admin-only auth.
- UI: "Upload file" CTA on model-detail page (visible to admin only), opens dropzone dialog with kind selector + drag-drop
- Per-story Codex review + visual verification.

##### Story 16.6 — Bulk STL download (ZIP) restoration

**Realizes:** FR10-DOWNLOAD-1.
**Architectural anchor:** none (regression restore).
**Depends on:** none.

- Restore `GET /api/files/{model_id}/bundle` endpoint (or its current-naming-conventions equivalent — verify against last-shipped naming in `apps/api/app/modules/`; likely `GET /api/sot/models/{id}/bundle` per current module conventions)
- Returns `application/zip` with all printable files (STL + STEP + F3D + .3mf if present) at top-level of ZIP with original filenames
- Member + admin auth (auth check identical to existing `/api/files/{id}/content` route)
- UI: "Download all" CTA on model-detail page (already exists per Init 0 SLICE-13 history — verify, may already be wired, just needs endpoint behind it)
- Per-story Codex review + visual verification.

### Epic E17 — Operator UX & Backlog Sweep

**Goal.** Close 4 small-surface items: admin-tables fluid-width universal pattern (~6 lines diff), TB-016 runbook doc-honesty (3 findings), DOC-DRIFT-2 remaining 4 drifts, and any incidental new TB-* surfaced during Init 10 execution.

**Acceptance gate.**
- Admin invites + admin users tables: fluid width verified on 3 viewports (1366px laptop, 1920px desktop, 2560px ultra-wide); PL labels render without horizontal scroll on 1920px+; visual baselines regen'd with sign-off per Init 7+8+9 precedent.
- TB-016 doc-only commit landed; runbook fingerprint baseline shift verified.
- DOC-DRIFT-2 4 remaining drifts patched; triage-backlog.md updated to status=done.

**Stories (4):**

##### Story 17.1 — Admin tables fluid-width universal pattern

**Realizes:** FR10-UX-TABLES-1.
**Architectural anchor:** none.
**Depends on:** none.

- Remove `max-w-7xl` from `InvitesPage.tsx:148`
- Remove `min-w-[1200px]` from `InvitesPage.tsx:229` (table)
- Remove `max-w-6xl` from `UsersPage.tsx:279`
- Sessions (`max-w-3xl`) — leave alone (form-style settings page per designer recommendation)
- Optional: add `whitespace-nowrap` on timestamp/IP columns if natural wrap looks ugly post-fix
- Regen visual baselines for admin-invites + admin-users (8 baselines per project × 4 projects = up to 32 PNGs; in practice closer to 12-16)
- Per-story Codex review + visual verification across PL + EN locales × 4 viewports.

##### Story 17.2 — Visual baselines regen sign-off

**Realizes:** NFR10-VISUAL-VERIFICATION-1 (forward contract enforcement).
**Architectural anchor:** none.
**Depends on:** Story 17.1.

- Standard visual baseline acceptance gate per Init 7+8+9 commit-msg trailer pattern (`baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD`)
- Bundled into Story 17.1's commit, NOT a separate story — listed here for visibility only. May collapse into 17.1.

##### Story 17.3 — TB-016 agent runbook doc-honesty fixes

**Realizes:** FR10-TRIAGE-1 (TB-016 promotion).
**Architectural anchor:** none.
**Depends on:** none.

- Apply 3 findings per triage-backlog TB-016 recommended dispositions:
  - Finding A — option 2 (budget bump 60s → 120s + 1-sentence qualifier on mesh size variance)
  - Finding B — full rewrite of `agents-add-model-runbook.md:142` per fix sketch (drop `D:\` reference, generic browser-default phrasing)
  - Finding C — rewrite `:303` + update example payload `:395` (active bilingual-name guidance + both fields populated in example)
- Single doc-only commit; auto-deploy skipped per `feedback_auto_deploy_dev`.
- Runbook fingerprint baseline shift (single roll, not three).
- Triage-backlog.md status update: TB-016 → done.

##### Story 17.4 — DOC-DRIFT-2 remaining drifts close-out

**Realizes:** FR10-TRIAGE-2 (DOC-DRIFT-2 close).
**Architectural anchor:** none.
**Depends on:** none.

- Patch remaining 4 drifts in `_bmad-output/planning-artifacts/{epics.md, architecture.md, prd.md}`:
  - Drift 3 — Decision B INTEGER→UUID schema rewrite (largest doc-debt; full type-by-type rewrite of Decision B column table)
  - Drift 5 — `refresh_tokens` autogenerate cleanup (code-side rename in `apps/api/app/modules/auth/`)
  - Drift 16 — `ratelimit_share_*` vs `share_ratelimit_*` cosmetic rename in `apps/api/app/core/config.py` Settings field
  - Drift 17 — `test_create_share_requires_admin` rename in `apps/api/tests/test_share_admin.py`
- Single `docs(bmad)` commit + 1 code-side commit (for code-side drifts 5, 16, 17) — possibly 2 commits.
- Triage-backlog.md status update: DOC-DRIFT-2 → done.

---

## Appendix B — Operator action items (outside Init 10 scope)

### B.1 Item #6 — OTEL collector data-prepper sink

**Status:** OUT-OF-SCOPE for Initiative 10 per OTEL recon subagent findings (75% confidence infra-side).

**Operator actions (recommended order):**

1. `ssh ezop@192.168.2.190 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "otel-collector|data-prepper"'`
2. `ssh ezop@192.168.2.190 'docker logs data-prepper --tail 200 2>&1'` — look for OOM / opensearch reject / queue full
3. `curl -fsS http://192.168.2.190:13133` — otel-collector health_check
4. Restart `data-prepper` if stuck: `ssh ezop@192.168.2.190 'cd /opt/configs && docker compose restart data-prepper'`
5. If incident recurs in 7d → file `infra/observability collector-dataprepper-backpressure` as ops-runbook task in `~/repos/configs/docs/server-190-backend.md`

**Optional follow-up (separate future-Init story, NOT in Init 10):** api-side hardening with `OTEL_BSP_EXPORT_TIMEOUT_MILLIS=5000` + `OTEL_BSP_MAX_QUEUE_SIZE=2048` in `infra/.env` + Sentry breadcrumb suppressor on these warnings — only if incident recurs.

### B.2 Item #7 — 401 scan-pattern security inquiry

**Status:** OPERATOR-BLOCKER on SSH connectivity (timeout from dev box at SCP-draft time).

**Operator actions:**

1. Restore SSH connectivity to `.190` (likely VPN / network mode toggle; investigate dev-box side)
2. Re-trigger 401-pattern recon (Claude can run subagent once SSH works) — sample:
   ```bash
   ssh ezop@192.168.2.190 "cd /opt/3d-portal && docker compose logs --since 24h api 2>&1 | \
     grep -E '\b401 Unauthorized' | awk '{print \$1,\$2,\$3,\$4,\$5}' | sort | uniq -c | sort -rn | head -30"
   ```
3. Analyze:
   - Source IPs (single source = scan; multiple = legitimate users hitting expired sessions)
   - Path patterns (e.g., `/api/models/<uuid>` = legitimate; `/wp-admin`, `/admin.php`, `/.env` = scanner)
   - Frequency (1 req/min = legit; 100 req/sec = active scan)
4. If active scan pattern confirmed → fail2ban or nginx-level IP block at edge proxy in `~/repos/configs/nginx/3d.ezop.ddns.net.conf`
5. If legitimate user-side (expired tokens) → no action; existing auth refresh path handles

---

## Appendix C — Recon outputs (for reference)

### C.1 OTEL recon (completed 2026-05-22)

**Diagnosis:** Infra-side ~75% confidence; code-side P3 smell ~10%.

**App-side config:** Correct. `apps/api/app/core/observability.py:39-43` uses `OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces", headers=headers_dict)` — clean OTLP HTTP/protobuf, default timeout 10s, default retry 3. Endpoint `http://192.168.2.190:4318` matches `~/repos/configs/docs/observability-logging-contract.md:28` contract. Token matches `bearertokenauth` extension in `~/repos/configs/otel-collector/config.yml:1-4`.

**Most likely root cause:** Backend collector → data-prepper sink stuck. `~/repos/configs/otel-collector/config.yml:64-68` exports to `localhost:21893`; collector has `network_mode: host`, data-prepper in `opensearch-net` network on public port `21893:21893`. If data-prepper down/slow → backpressure → batch processor rejects → collector returns timeout to client → exactly this log spam.

**No recent collector config changes:** Last commit `d851f7f` in `configs/otel-collector/` is 2026-04-12 — runtime/operational issue, not configuration drift.

**Optional code-side hardening (future Init):** `OTEL_BSP_EXPORT_TIMEOUT_MILLIS=5000` + breadcrumb suppressor; XS-size story; only file if recurrent.

### C.2 Designer table-width research (completed 2026-05-22)

**Recommendation:** Confirms operator intuition. Fluid full-width is industry-default for admin tables (GitHub, Linear, Vercel, Stripe, Carbon Design System, Atlassian). The `max-w-65-75ch` line-length argument applies to **prose**, not table cells. The "looks cleaner" counter-argument is design-by-aesthetics with no metric backing.

**Measurable root cause:** PL labels 40-90% longer than EN ("Wygenerowane przez" 18 chars vs "Generated by" 12; "Wykorzystane z IP" 17 vs "Used from IP" 12). `min-w-[1200px]` was calibrated for EN compactness; PL hits or exceeds 1280px (`max-w-7xl`) and triggers `overflow-x-auto`.

**Implementation (Story 17.1):** ~6 lines diff. Remove `max-w-7xl` from InvitesPage:148, `min-w-[1200px]` from InvitesPage:229 table, `max-w-6xl` from UsersPage:279. Leave Sessions (`max-w-3xl`) alone (form-style settings page).

**Counter-argument considered:** On 1920+ ultra-wide, saccade distance between first/last column grows. Mitigation per industry: zebra-striping or `hover:bg-muted` on `<tr>` (already present via `border-t`); optional sticky first column at >1600px. NOT cap whole table. Industry research (Carbon, PencilAndPaper enterprise-table studies) does not establish a threshold for capping; YAGNI.

### C.3 Test-flake landscape audit (completed 2026-05-22)

**Headline:** Cumulative test pain is real (operator's frustration is valid) BUT none of it is true non-determinism. Every issue reproduces deterministically. The "flake" label was misapplied to: (a) one threading deadlock that hangs to timeout, (b) 86 stale-baseline carry-forward failures (variance=0 across runs), (c) 0 actual vitest flakes.

**Counts:**
- **Vitest:** 0 flakes, 94 files / 408 tests PASS 3× consecutive
- **Pytest:** 1 hang-class deadlock + 0 deterministic-fail; full suite cannot run to completion (~17% before hang)
- **Playwright visual:** 86 deterministic-fail (78 stale-baseline + 8 anon-login-only timeout) + 24 skip + 234 PASS / 344 total

**Pytest deadlock pinned:** `test_concurrent_refresh_one_wins` (`apps/api/tests/test_auth_refresh.py:164-194`). Suspected root cause: `_patch_arq_pool` autouse fixture (`apps/api/tests/conftest.py:14-29`) via `unittest.mock.patch` is NOT thread-safe; threading.Thread workers may bypass the patch → attempt real Redis connect → futex_wait_queue forever. `t1.join()`/`t2.join()` have no timeout → pytest never returns.

**Decision boundary item:** Story 15.1 Phase 1 instrumentation will pin whether this is **test-only** (just rewrite the test without threading) OR **real prod-side race** (fix prod-side `create_pool` concurrency, retain threaded test as guard).

**Investment:** 10-19h total (15.1 = 2-4h, 15.2 = 4-8h, 15.3 = 3-5h, retro 1-2h). 2-3 working days spread across 4-6 BMAD sessions.

---

**End of SCP draft. Awaiting tests-audit completion and operator approval.**
