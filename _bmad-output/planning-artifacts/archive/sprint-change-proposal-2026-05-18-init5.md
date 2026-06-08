---
title: "Sprint Change Proposal — Initiative 5 (Public Registration & User Account Management) plan extension"
type: sprint-change-proposal
initiative_scope: 5
status: approved
created: 2026-05-18
last_updated: 2026-05-18
author: Claude (BMAD bmad-correct-course skill, vanilla-aligned) + Ezop (operator review + approvals)
mode: incremental
change_scope_classification: major
related_artifacts:
  - product-brief-3d-portal-user-accounts.md            # v2, binding input
  - product-brief-3d-portal-user-accounts-distillate.md # binding input
  - prd.md                                              # to be extended
  - architecture.md                                     # to be extended
  - epics.md                                            # to be extended
  - implementation-artifacts/sprint-status.yaml         # to be extended (Session F)
  - sprint-change-proposal-2026-05-18.md                # Phase 1 (cleanup) — predecessor proposal
supersedes: none
superseded_by: none
---

# Sprint Change Proposal — Initiative 5 Planning Chain Extension

## Section 1 — Issue Summary

### 1.1 Problem statement

The portal today admits exactly two principals: `admin` (Michał) and `agent` (the AI service account). All household browse access is gated at the nginx edge via IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`); there is no notion of a per-person login for anyone who is not Michał. The `member` role exists in the User enum but is unreachable — no registration path, no admin UI for invite issuance, no 2FA infrastructure, and the network perimeter is still load-bearing for trust.

Initiative 5 closes that gap. It opens the portal to a curated friends-and-family circle via invite-link registration (single-use tokens with operator-chosen TTL, pre-bound role, audit trail), adds optional TOTP 2FA with mandatory recovery codes, ships an admin panel for user + invite lifecycle management, and — gated by a hard pre-cutover security audit — drops the nginx edge gate so the portal authenticates itself rather than relying on the homelab network perimeter.

### 1.2 Issue categorization

Per CC checklist §1.2: **"New requirement emerged from stakeholders"**. This is a scheduled new-initiative addition planned and authorized via the product-brief discovery pass (2026-05-18). It is NOT a reactive trigger from a failing story; all Initiative 0/1/2/3 epics are `done` (with E4.6 Growth scope deferred per AC).

### 1.3 Evidence

Source documents, all binding inputs to this proposal:

- **Brief v2** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines, adversarial review applied: P0×2 + P1×3 + P2×1 fixed).
- **Distillate** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5688 tokens, LLM-optimized).
- **18 working assumptions** challenged during discovery and surviving into PRD (brief §"Working assumptions").
- **6 stakeholder-consulted sources** — operator, existing BMAD artifacts, apps/api code recon, apps/web code recon, edge infra sibling repo, memory entries.
- **Predecessor proposal** — `sprint-change-proposal-2026-05-18.md` (Phase 1 cleanup + vanilla recalibration, commit `bf919c2` 2026-05-18). This proposal extends that hygienic baseline.

Halt-conditions per CC checklist §1: trigger clear ✓, evidence sufficient ✓.

---

## Section 2 — Impact Analysis

### 2.1 Epic impact

| Epic state | Count | Detail |
|---|---|---|
| Currently in-progress | 0 | All Init 0/1/2/3 epics `done` (E4.6 Growth scope `backlog`/deferred per AC) |
| To add | 5 | E6 (Member+invite), E7 (TOTP+recovery), E8 (Admin panel), E9 (Security audit HARD GATE), E10 (Edge cutover) |
| To modify | 0 | No Init 0/1/2/3 epic modified — Init 5 is purely additive |
| To remove | 0 | None |

**Sequencing:** E6 → E7 → E8 → **E9 (hard gate)** → E10. Gate condition (E9 → E10): zero open Critical/High findings; ≤3 "accepted-with-rationale" Mediums.

### 2.2 Artifact conflicts (CC checklist §3)

| Artifact | Current state | Change | Impact level |
|---|---|---|---|
| `prd.md` | Init 0/1/2/3 H2 sections present | Append `## Initiative 5` H2 (~250-350 lines) via `bmad-edit-prd` | High (PRD ownership) |
| `architecture.md` | Init 0/1/2/3 H2 sections present | Manual append `## Initiative 5` H2 (~350-450 lines) — no `bmad-edit-architecture` skill | High (canonical workaround) |
| `epics.md` | Init 0/1/2/3 H2 sections, E1-E5 global epic IDs | Manual append `## Initiative 5` H2 + Epic 6-10 H4 + Stories 6.x-10.x H5 (~600-800 lines) | High (canonical workaround) |
| `sprint-status.yaml` | epic-1...epic-5 + supporting entries `done` | Append `epic-6`...`epic-10` + per-story entries (status `backlog`) via `bmad-sprint-planning` | Medium (delegated to skill) |
| UX design doc | N/A (none exists for Init 5) | N/A — admin panel reuses existing patterns; `/register` form is net-new but simple; visual ACs land at Story level | None (skip UX doc) |
| `AGENTS.md` / `project-context.md` | Vanilla-first subsection v2 (2026-05-18) | NO changes in this proposal — defer to post-E10 cutover (rate-limit middleware, 2FA enforcement flag, member share rate-limit cap → docelowe rule additions) | None (out-of-scope) |
| `deploy.sh` skip-gate | Range-based, shipped `bc324e2` + `0745209` | No change in this proposal. Init 5 code commits fire deploy per `feedback_auto_deploy_dev.md`. E10 nginx-edit BYPASSES skip-gate (sibling repo, gitignored `infra/.last-deploy-sha`) — brief flag in E10 AC | None for this proposal |
| Playwright visual matrix | 4 projects, axe-contrast scans active (Init 3) | New admin pages + `/register` automatically covered by existing matrix; new specs land at Story level | Low (automatic) |

### 2.3 Technical impact (per brief)

- **DB migrations**: ~3-4 Alembic migrations (invite_tokens, users.2FA columns, recovery_codes, users.is_active + last_active_at).
- **Backend modules**: ~6 new in `apps/api/app/modules/` (invite service, 2FA endpoints, admin users/invites router, rate-limit middleware, `/register` public route, member permission helpers).
- **Frontend routes**: ~4 new in `apps/web/src/`.
- **Sibling repo edits**: ~1 nginx config change in `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (E10).
- **Cross-cutting**: 16 new audit-log actions registered in `KNOWN_ENTITY_TYPES`.

---

## Section 3 — Recommended Approach (CC checklist §4)

### 3.1 Path forward evaluation

| Option | Viable? | Rationale |
|---|---|---|
| 1: Direct Adjustment (add new epics) | ✅ | Init 5 is purely additive; doc shape locked to monolithic H2-append per AGENTS.md v2 (2026-05-18) |
| 2: Potential Rollback | ❌ N/A | Init 0-3 `done` and unrelated; nothing to roll back |
| 3: PRD MVP Review | ❌ N/A | Init 0-3 MVP shipped; Init 5 is new scope, not redefinition of existing |

### 3.2 Selected approach: **Option 1 — Direct Adjustment**

Add 5 new epics under a new `## Initiative 5` H2 section in prd.md / architecture.md / epics.md (monolithic single-file H2-append pattern). This continues the established Init 0/1/2/3 convention and is vanilla-BMAD-aligned given the documented multi-initiative methodology gap.

### 3.3 Key locked decisions (binding inputs from brief v2)

These are NOT re-decided in this proposal — they are confirmed locked and carried into the downstream skills:

1. **Five sequenced epics**: E6 (Member+invite), E7 (TOTP+recovery), E8 (Admin panel), E9 (Security audit HARD GATE), E10 (Edge cutover).
2. **E9 hard gate**: zero open Critical/High; ≤3 "accepted-with-rationale" Mediums (4th forces auto-fail + fix sprint).
3. **Member permission expansion**: `member` gains `/api/share/*` POST capability. Mitigation: per-member rate-limit + daily volume cap (architecture decision H).
4. **Agent role is sacrosanct**: `agent` MUST NEVER appear in `enforce_2fa_for_roles` list.
5. **Invite-token storage dual-backed**: Redis primary (active/TTL/revoke) + DB row (audit history, outlives Redis TTL).
6. **2FA optional by default**: per-role config flag for enforcement + admin per-user force-enrollment via panel.
7. **Cross-repo cutover smoke matrix**: 4 scenarios post-reload (share GET, agent POST, member login, admin login). E10 nginx edit in sibling `~/repos/configs/nginx/3d.ezop.ddns.net.conf`.

### 3.4 Vanilla BMAD alignment correction (this session)

During CC §3.1 PRD analysis, a conflict surfaced between session goal briefing (proposing local `Epic 1-5` numbering under Init 5 H2) and binding state (epics.md line 66 + project-context.md line 211, both confirming project-global numbering).

**Correction applied**: vanilla BMAD `epics-template.md` uses `## Epic {{N}}` with `{{N}}` unique within the file. Multi-initiative monolithic file preserves this by treating N as project-global. Session goal's "Epic 1-5 local under Init 5" interpretation would have created duplicate `Epic 1`/`Epic 2`/`Epic 3` headers in the file, violating vanilla unique-N assumption.

**Locked for downstream skills**:
- Epic IDs: **project-global E6 / E7 / E8 / E9 / E10** under Init 5 H2 (continuing E1-E3 / E4 / E5 from Init 1/2/3).
- Story IDs: **`<global-epic-id>.<local-story-num>`** → `Story 6.1, 6.2, ...`, `7.1, 7.2, ...`, etc.
- Brief's working-label notation `5.1-5.5` maps 1:1 onto E6-E10 (recorded in Init 5 Overview section of each artifact).
- Header levels: `## Initiative 5` (H2) → `### Overview/Requirements/...` (H3) → `#### Epic N` (H4) → `##### Story N.M` (H5).

This correction is the only content-level decision made in this CC pass; all other content decisions remain the brief's domain.

---

## Section 4 — Detailed Change Proposals

The three approved proposals (Step 3 incremental, all approved by operator):

### 4.1 Proposal #1 — Document-level structure & numbering

| Artifact | Action | Approved? |
|---|---|---|
| `prd.md` | extend via append `## Initiative 5` H2 (via `bmad-edit-prd`) | ✅ |
| `architecture.md` | extend via manual append `## Initiative 5` H2 | ✅ |
| `epics.md` | extend via manual append `## Initiative 5` H2 + Epic 6-10 H4 + Stories H5 | ✅ |
| `sprint-status.yaml` | extend via `bmad-sprint-planning` | ✅ |
| `AGENTS.md` / `project-context.md` | NO changes in this proposal (deferred post-E10) | ✅ |

Numbering convention: **Epic 6-10 project-global**, Stories `<epic-id>.<story-num>`. Brief's `5.1-5.5` maps 1:1 onto E6-E10.

### 4.2 Proposal #2 — Per-artifact content outline

**2A — `prd.md § Initiative 5`** (~250-350 lines): Overview / 23 FRs grouped by area (FR5-INVITE-* / FR5-REGISTER-* / FR5-MEMBER-* / FR5-2FA-* / FR5-ADMIN-* / FR5-AUDIT-* / FR5-RATELIMIT-* / FR5-CUTOVER-*) / 12 NFRs (NFR5-SEC-* / NFR5-PERF-* / NFR5-AUDIT-* / NFR5-CROSS-REPO-* / NFR5-INT-* / NFR5-OBS-*) / MVP Scope verbatim from brief / 6 Success Criteria verbatim / Cross-references.

**2B — `architecture.md § Initiative 5`** (~350-450 lines): Overview / Decisions A-K in-scope (invite-token dual-backed storage / token shape 32-byte entropy / member permission scope diff / 2FA column shape / recovery codes schema / 2FA enforcement config flag / rate-limit middleware Redis sliding-window / per-member share cap / is_active soft-delete + last_active_at throttled / nginx config diff + rollback / cross-repo smoke matrix) / Decisions L-N deferred (self-service mail reset / OIDC federation / per-model ACL) / Cross-references to E0.3 auth + E0.6 share-token + E0.5 admin/audit.

**2C — `epics.md § Initiative 5`** (~600-800 lines): Overview + working-label mapping / Requirements Inventory FR↔Epic + NFR↔Epic / Epic List table / Epic 6 H4 + Stories 6.1-6.N / Epic 7 H4 + Stories / Epic 8 H4 + Stories / Epic 9 H4 + Stories (HARD GATE) / Epic 10 H4 + Stories / Cross-references. Story-decomposition estimate per epic ~25-35 stories total (exact list finalized at sprint-planning time).

**2D — `sprint-status.yaml`** extension via `bmad-sprint-planning`: `epic-6` ... `epic-10` keys + per-story entries (status `backlog` on creation). Header comment update with Init 5 planning chain date.

### 4.3 Proposal #3 — Handoff plan & skill chain order

| Sesja | Skill / Action | Output | Recipient role |
|---|---|---|---|
| A (this session) | `bmad-correct-course` | This proposal document | CC agent |
| B (fresh context) | `bmad-edit-prd` | prd.md extended with `## Initiative 5` H2 | PM agent |
| C (fresh context) | Manual edit architecture.md | architecture.md extended with `## Initiative 5` H2 + Decisions A-K + L-N | Architect agent (manual, no skill) |
| D (fresh context) | Manual edit epics.md | epics.md extended with `## Initiative 5` H2 + Epic 6-10 + Stories 6.x-10.x | Architect agent (manual, no skill) |
| E (fresh context) | `bmad-check-implementation-readiness` | Readiness report covering Init 0+1+2+3+5 (gate) | Readiness check agent |
| F (fresh context) | `bmad-sprint-planning` | sprint-status.yaml extended (epic-6...epic-10 + per-story entries) | PO/DEV coordinator |
| G+ (fresh contexts) | `bmad-create-story` → `bmad-dev-story` → `bmad-code-review` per story | Story files + dev commits + reviews | Developer agent |

**Sequencing within story-cycle**: E6 → E7 → E8 → E9 (gate) → E10. E10 stories blocked on E9 gate-condition artifact (zero open Critical/High in audit report).

### 4.4 Per-Epic effort + risk estimate

| Epic | Name | Stories (est.) | Effort | Risk | Why |
|---|---|---|---|---|---|
| E6 | Member role + invite-based registration | ~6-8 | Medium | Medium | New auth surface, DB migration, member permission expansion, share-router auth expanded |
| E7 | 2FA TOTP + recovery codes | ~5-6 | Medium | Medium | Auth flow extension, standard `pyotp`, recovery-codes table |
| E8 | Admin panel: users + invites | ~5-7 | Medium | Low | Additive UI on existing admin module |
| E9 | Security audit (HARD GATE) | ~4-5 | High | **High** | Load-bearing, blocks E10, potential audit findings = fix sprint, strict gate |
| E10 | Edge cutover (atomic) | ~3-4 | Low | **High** | Atomic nginx-config-commit + reload, rollback-must-work, cross-repo |

**Total estimated effort**: 4-6 weeks back-to-back per brief Vision section.

---

## Section 5 — Implementation Handoff

### 5.1 Change scope classification

**Major** per CC Step 5: fundamentalne rozszerzenie aktywnego planu o nową Inicjatywę 5 z 5 epikami, security audit hard-gate, cross-repo cutover. Wymaga pełnego BMAD planning chain z fresh-context per skill.

### 5.2 Handoff recipients (CC §5.5)

- **PM/Architect role** (Sesje B-D): PRD authoring + architecture/epics manual extensions.
- **Implementation Readiness gate** (Sesja E): blocking check before sprint-planning.
- **PO/DEV coordination** (Sesja F): sprint-planning ownership; from this point onward Developer agent owns story cycle.
- **Developer agent** (Sesje G+): per-story dev cycle.

### 5.3 Responsibilities per role

| Role | Responsibilities |
|---|---|
| CC agent (this session) | Produce this proposal, finalize handoff, update todo list for downstream sessions |
| PM agent (B) | Faithful PRD extension from brief v2 (no re-elicitation of locked decisions); FR/NFR ID assignment; FR↔Epic mapping table |
| Architect agent (C, D) | Manual extension of architecture.md (Decisions A-K + L-N from brief) and epics.md (Epic 6-10 H4 + Stories 6.x-10.x H5) preserving Init 0-3 history |
| Readiness check agent (E) | Verify FR↔NFR↔Decision↔Epic↔Story coverage across all Init 0+1+2+3+5; surface gaps as P1/P2 findings before allowing F |
| PO/DEV coordinator (F) | Translate epics.md Story list into sprint-status.yaml entries; preserve global epic numbering |
| Developer agent (G+) | Per-story BMAD cycle: create-story → dev-story → code-review |

### 5.4 Success criteria for this proposal

Per brief §"Success Criteria" + CC handoff completion:

1. **Planning chain artifact integrity**: prd.md / architecture.md / epics.md wszystkie mają `## Initiative 5` H2 section, ze spójnym FR↔Decision↔Story mapping. Initiatives Index w trzech plikach + frontmatter `initiatives:` zaktualizowane.
2. **Readiness report PASS** w Sesji E zanim ruszy Sesja F.
3. **sprint-status.yaml** ma `epic-6` ... `epic-10` + per-story entries z status `backlog`, gotowe na `bmad-create-story` invocation.
4. **Doc shape compliance**: monolithic single-file H2-append pattern zachowany (no per-feature split, no `prd-user-accounts.md` etc.) per AGENTS.md v2.
5. **Vanilla BMAD alignment**: Epic IDs project-global (E6-E10), Story IDs `<epic-id>.<story-num>`, każdy skill invoked w fresh context per vanilla recommendation.

### 5.5 Out of scope for this proposal

The following are explicitly NOT addressed here and remain for downstream skills/sessions:

- Exact FR/NFR/Decision/Story numbering and full text (deferred to `bmad-edit-prd` + manual edits).
- Exact per-story acceptance criteria (deferred to `bmad-create-story` per story).
- AGENTS.md / project-context.md rule additions for rate-limit / 2FA enforcement (deferred to post-E10 cutover).
- E9 security audit report content (produced at E9 execution time).
- E10 cutover artifact (produced at E10 execution time).

### 5.6 Hard rules carried forward (binding for all downstream sessions)

1. Brief v2 + distillate are binding source-of-truth. Re-elicitation of locked decisions = drift signature.
2. Doc shape = monolithic single-file H2-append. No per-feature split, no `prd-user-accounts.md`. Per AGENTS.md v2 (2026-05-18) vanilla-first subsection.
3. Epic numbering = project-global. E6, E7, E8, E9, E10 under `## Initiative 5` H2. Story IDs `<epic-id>.<story-num>`.
4. Skill discipline: if any downstream skill protests current state, STOP and consult operator. Do NOT silently route-around.
5. Each skill invoked in fresh context window per vanilla BMAD recommendation.
6. Communication language: Polish (per `_bmad/bmm/config.yaml`). Document output language: English.

---

## Section 6 — Approval (CC §6.3)

Approvals collected incrementally during the CC pass:

| Proposal | Operator decision | Timestamp |
|---|---|---|
| Epic numbering correction (global E6-E10) | Approved | 2026-05-18 |
| Mode: Incremental | Approved | 2026-05-18 |
| Proposal #1 (document-level structure & numbering) | Approved | 2026-05-18 |
| Proposal #2 (per-artifact content outline 2A+2B+2C+2D) | Approved (all four) | 2026-05-18 |
| Proposal #3 (handoff plan — 5 sesji B-F, manual C+D osobno) | Approved | 2026-05-18 |
| Section 6 final review of complete proposal | Approved | 2026-05-18 |

---

## Section 7 — Appendix: Initial briefing reconciliation log

For traceability, the corrections applied to the session goal briefing during CC pass execution:

### 7.1 Epic numbering — corrected

| Field | Initial briefing | Corrected | Reason |
|---|---|---|---|
| Epic IDs in Init 5 | "vanilla per-section local `#### Epic 1` ... `#### Epic 5`" | "project-global `#### Epic 6` ... `#### Epic 10`" | Conflict with `epics.md` line 66 + `project-context.md` line 211 (both binding facts confirming project-global numbering). Vanilla `epics-template.md` uses `## Epic {{N}}` with `{{N}}` unique-in-file — multi-initiative monolithic file preserves this via global numbering. Local `Epic 1-5` under Init 5 H2 would create duplicate headers in the file. |
| Story IDs | "(implied) `Story 1.1, 1.2 ... 5.N`" | "`<global-epic-id>.<local-story-num>` → `Story 6.1, 6.2 ... 10.N`" | Consequence of corrected epic numbering. |

### 7.2 Sprint-status path — corrected

| Field | Initial briefing | Corrected | Reason |
|---|---|---|---|
| sprint-status.yaml location | "`_bmad-output/planning-artifacts/sprint-status.yaml`" | "`_bmad-output/implementation-artifacts/sprint-status.yaml`" | BMM config: `implementation_artifacts: "{project-root}/_bmad-output/implementation-artifacts"`. The file already exists at the correct location; briefing path was a slip. |

### 7.3 Items confirmed (no correction needed)

- Doc shape: monolithic single-file H2-append ✓ confirmed by AGENTS.md v2 (2026-05-18) vanilla-first subsection.
- Brief v2 + distillate as binding inputs ✓.
- Skill chain order: bmad-edit-prd → manual architecture → manual epics → bmad-check-implementation-readiness → bmad-sprint-planning ✓.
- Communication language Polish + document output English ✓.

### 7.4 Memory feedback to file (for future sessions)

For potential update to existing memory entries `feedback_vanilla_bmad_first.md` + `feedback_bmad_skill_discovery_checklist.md` (post-approval, not part of this proposal):

- When CC is invoked for adding a new Initiative to an active multi-Initiative monolithic file, the binding state check at session start MUST include reading `epics.md` for the active epic numbering convention (line 66 in this repo's file) BEFORE accepting any session-goal briefing that prescribes local numbering. This is an extension of the existing skill-discovery checklist.

---

_End of proposal. Awaiting final operator approval per CC §6.3 — see Section 6 above._
