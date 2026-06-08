---
type: sprint-change-proposal
created: 2026-05-18
last_updated: 2026-05-18 (v2 — vanilla recalibration + audit findings)
status: decisions-locked-pending-execution
author: Claude (bmad-correct-course, Opus 4.7)
scope: single-session-cleanup-then-init-5-vanilla-planning
trigger: |
  Two related triggers landed in 2026-05-18 session: (1) Initiative 5 user-accounts
  planning was reverted after a previous-session drift caught operator's attention
  (silent route-around protesting bmad-create-prd, never called bmad-help,
  never considered bmad-correct-course); (2) operator-locked decision to clean up
  legacy non-vanilla state in repo. Initial draft of this proposal recommended
  retro-migrating prd.md/architecture.md/epics.md into per-feature files.
  Mid-session sanity check revealed that interpretation was wrong: vanilla BMAD
  assumes a single project-wide PRD/architecture/epics model (autoritative source:
  docs.bmad-method.org/llms-full.txt; reinforced by every skill's hardcoded
  outputFile = {planning_artifacts}/{prd,architecture,epics}.md).
  Proposal pivoted to recalibration + audit-driven cleanup.
related_artifacts:
  - _bmad-output/planning-artifacts/init5-handoff-2026-05-18.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md
  - _bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md
  - AGENTS.md § "BMAD vanilla-first" (will be corrected by this proposal)
  - feedback_vanilla_bmad_first (memory; will be corrected)
  - feedback_bmad_skill_discovery_checklist (memory; unchanged — skill-discipline rules are correct)
---

# Sprint Change Proposal v2 — Vanilla recalibration + audit-driven cleanup + Init 5 vanilla planning

## 1. Issue Summary

Two related triggers in 2026-05-18 session:

1. **Initiative 5 (user-accounts) planning was reverted** after drift detection in previous session — `bmad-create-prd` protested on finished PRD, agent silently routed-around to `bmad-edit-prd`, `architecture.md` directly edited without ceremony, `bmad-help` never called, `bmad-correct-course` never considered. All decisions preserved in brief v2 + distillate; doc-tree shape for Init 5 is the open question.

2. **Operator-locked decision** end-of-2026-05-18: clean up legacy non-vanilla state in repo + ensure ongoing work matches vanilla.

**Initial misdiagnosis (corrected during this session):** The first draft of this proposal recommended retro-migrating monolithic `prd.md`/`architecture.md`/`epics.md` into per-feature files (`prd-foundation.md`, `prd-glitchtip.md`, etc.). That recommendation was based on **a wrong interpretation of "vanilla BMAD"**. Sanity-check via skill source files + autoritative docs revealed:

- Every vanilla planning skill hardcodes singular `outputFile = {planning_artifacts}/{prd,architecture,epics}.md` (e.g. `bmad-create-prd/SKILL.md:95`, `bmad-create-architecture/steps/*.md` × 6, `bmad-create-epics-and-stories/steps/*.md` × 4).
- `bmad-sprint-planning` is the only skill that mentions multiple files — explicit per-epic (`epic-1.md`, `epic-2.md`), NOT per-feature/per-initiative.
- `docs.bmad-method.org/llms-full.txt` (autoritative): *"BMAD assumes a single project-wide PRD model. The documentation does not address multi-initiative brownfield scenarios. This appears to be a gap in the current guidance."*
- `bmad-correct-course/SKILL.md` itself explicitly mandates **modify-in-place semantics** ("sections to update", "before/after", "Artifact Conflicts: PRD, Architecture, UI/UX documents needing updates", "Modify existing epic scope", "Add new epic entries").

**Conclusion:** 3d-portal's `## Initiative N` H2-append pattern in monolithic `prd.md`/`architecture.md`/`epics.md` is **a pragmatic workaround for the documented BMAD methodology gap on multi-initiative brownfield**, NOT a drift. It is the closest-to-vanilla shape attainable given that BMAD has no per-feature filing convention. Procedural drifts (skipping `bmad-help`, routing-around-protest, direct artifact edits) are the actual bugs to avoid — and those rules already correctly encoded in AGENTS.md § "Workflow expectations" first bullet + skill discovery checklist.

Categorization: **Misunderstanding** — agent (me) over-interpreted the methodology gap as a drift, codified that interpretation into AGENTS.md vanilla-first subsection + memory, then queued a major migration based on the misinterpretation. Operator's sanity-check caught it mid-flow.

## 2. Impact Analysis

### 2.1 What needs correction (false claims to remove)

| Location | False claim | Replacement |
|---|---|---|
| `AGENTS.md` L194 | "multi-section single `prd.md` with `## Initiative N` H2 sections appended per feature ... [is] legacy non-vanilla state" | Drop — pattern is pragmatic workaround for BMAD's documented multi-initiative gap |
| `AGENTS.md` L196 | "The existing `## Initiative 0/1/2/3` H2 sections in `_bmad-output/planning-artifacts/{prd,architecture}.md` are legacy non-vanilla state; do NOT extend that pattern in new work." | Drop entirely; new Init 5 SHOULD extend the same pattern via `bmad-edit-prd` |
| Memory `feedback_vanilla_bmad_first.md` body | "multi-section single PRD instead of per-feature PRD files" listed as deviation | Drop the per-feature-PRD framing; reframe around procedural drifts (skill discipline) |
| Project-context `L209-211` | **NO CHANGE** — accurately describes vanilla-aligned pragmatic shape; was correct all along |

### 2.2 What stays correct (skill-discipline rules preserved)

These rules from AGENTS.md vanilla-first subsection + memory entries remain authoritative:

1. Session-start `bmad-help` is mandatory (per AGENTS.md § "Workflow expectations" first bullet)
2. `bmad-correct-course` is canonical entry for post-ship scope changes (PRD edits, architecture changes, new features, mid-sprint adjustments)
3. If a skill protests, STOP and consult operator — no silent route-around
4. No direct artifact edits bypassing skill ceremony (with one realistic exception: epics.md + architecture.md have no edit-skill, so manual H2-append after CC recommendation is the canonical path)
5. Per-task skill discovery checklist (confirm bmad-help called, check CSV phase + after, consult CC for post-ship, STOP on protest)

### 2.3 Vanilla audit of `_bmad-output/` — current state

Categorization of all 65+ files:

**KEEP — vanilla, current, load-bearing (no action):**
- Core BMAD artifacts: `prd.md`, `architecture.md`, `epics.md`, `sprint-status.yaml` — vanilla outputs, monolithic, evolved via H2-append (the pragmatic workaround for methodology gap)
- `project-context.md`, `triage-backlog.md`, `deferred-work.md` — convention-aligned, active
- 4 product briefs + 4 distillates (3d-portal main, glitchtip, ui-theme-hardening, user-accounts) — vanilla
- 17 vanilla story specs (`1-1` … `4-3`) — `bmad-create-story` outputs
- 12 quick-dev specs (`spec-tb-*`) + 5 misc quick-dev specs — `bmad-quick-dev` outputs (non-canonical filenames but legit skill product)
- 5 retros (epic-1/2/4/5 + ui-review) — `bmad-retrospective` outputs
- 5 code reviews in `code-reviews/` — `bmad-code-review` outputs
- Story-output audit-trail artifacts (baseline-integrity-audit-2026-05-13, interactive-surface-coverage-matrix, theme-token-violations, token-reader-inventory, glitchtip-discovery, phase0-result, agent-runbook-smoke)

**ARCHIVE — done its job, move to `_bmad-output/planning-artifacts/archive/`:**

| File | Reason |
|---|---|
| `prd-validation-report.md` (2026-05-09) | Stale; validated only Init 1 PRD state (Init 0/2/3 not validated). Post-Init-5 re-validation will produce a current one. |
| `implementation-readiness-report-2026-05-15.md` (2026-05-16 run 3) | Current as of pre-Init-5; will be regenerated post-Init-5 readiness check. |
| `init5-handoff-2026-05-18.md` | Bridge between sessions; current session reached for it; after Init 5 PRD lands → no further value. |
| `codex-readiness-rerun-2026-05-16-prompt.md` | One-shot prompt artifact; Codex 3rd run shipped 2026-05-16; output captured in readiness report. |
| `epic-1-symbolication-regression.md` | Duplicate audit trail; both bugs captured in `epic-1-retro-2026-05-10.md` + sprint-status comments. |
| `spec-deploy-skip-gate.md` (status: abandoned) | Replaced by `spec-deploy-skip-gate-range.md` (shipped 2026-05-16). Retention "for redesign reference" obsolete; redesign already shipped. |

**HYGIENE NOTE — Init 2 brief gap:**
- Init 2 (Agent Runbook) shipped 2026-05-11 with no product brief in `_bmad-output/planning-artifacts/`. Init 0/1/3/5 all have briefs; Init 2 doesn't.
- Per memory `feedback_docs_hygiene` ("flag every skip as explicit hygiene decision"): add explicit disclaimer in `epics.md § Initiative 2 § Overview`, e.g.: *"**No product brief.** Init 2 was planned and executed via the autonomous chain (Session 2, 2026-05-10) without a separate brief stage — the Init 2 scope is small enough that brief + distillate were folded into the PRD extension. Acknowledged hygiene gap per `feedback_docs_hygiene`."*

**DELETE — surplus:**
- `_bmad-output/test-artifacts/test-reviews/` (empty dir)
- `_bmad-output/test-artifacts/` (parent, if empty after the above)

## 3. Recommended Approach (v2 — recalibrated)

**Two-phase plan, single session for Phase 1:**

### Phase 1 — Recalibration + cleanup (this session, ~10-20 min)

1. **Correct AGENTS.md § "BMAD vanilla-first" subsection** (drop false claim, preserve skill-discipline rules).
2. **Correct memory `feedback_vanilla_bmad_first.md`** (analogous correction).
3. **`mkdir _bmad-output/planning-artifacts/archive/`**, move 6 stale/done files (see § 2.3 ARCHIVE table).
4. **Add Init 2 hygiene note** in `epics.md § Initiative 2 § Overview`.
5. **`rm -rf _bmad-output/test-artifacts/test-reviews`** (empty dir cleanup); remove parent if empty.
6. **Verify**: `ls` archive contents + `wc -l` of edited artifacts + grep for residual "legacy non-vanilla" / "per-feature files" strings in AGENTS.md + memory.

Phase 1 is executable in this same context window. Zero code touched; doc-only operations. `_bmad-output/` is gitignored so no commit ceremony for those moves; `AGENTS.md` correction is a tracked commit.

### Phase 2 — Initiative 5 vanilla planning chain (fresh sessions, ~60-90 min spread)

Skill flow on the post-cleanup baseline:

1. `bmad-help` (mandatory session-start, per AGENTS.md)
2. `bmad-correct-course` → produces sprint change proposal recommending the Init 5 extension path. Inputs: brief v2 + distillate + post-cleanup `prd.md`/`architecture.md`/`epics.md` state.
3. Per CC recommendation: `bmad-edit-prd` on `prd.md` → adds `## Initiative 5 — Public Registration & User Account Management` H2 section (continuation of Init 0/1/2/3 pattern; vanilla-aligned per CC's modify-in-place semantics).
4. Manual edit `architecture.md` → adds `## Initiative 5` H2 section. No `bmad-edit-architecture` skill exists; the vanilla path via CC is manual edit (operator can later rerun `bmad-create-architecture` if a full rewrite is desired, but that would overwrite the monolith — not appropriate for brownfield).
5. Manual edit `epics.md` → adds `## Initiative 5` H2 section with epics (Init 5 has 5 epics per brief: invite + member role, 2FA, admin panel, security audit gate, edge cutover). Stories nested under each epic per BMAD template (`### Story N.M`).
6. `bmad-check-implementation-readiness` → produces fresh `implementation-readiness-report-2026-05-18.md` covering Init 0+1+2+3+5.
7. `bmad-sprint-planning` → updates `sprint-status.yaml` with Init 5 epics + stories.

Init 5 content (FRs/NFRs/architecture decisions) comes verbatim from brief v2 + distillate. **No re-elicitation.**

### 3.1 Why this is vanilla-aligned

- **Single-file modify-in-place** matches every vanilla skill's hardcoded outputFile + autoritative methodology docs.
- **`bmad-edit-prd` for new initiative on existing PRD** is what the skill is for ("Edit an existing PRD ... Improving an existing PRD").
- **Manual H2-append for architecture/epics** is the canonical workaround given no edit-skill exists (`bmad-create-architecture`/`bmad-create-epics-and-stories` are overwrite-style; manual edit preserves Init 0-3 history).
- **`bmad-correct-course` as canonical entry** — already invoked in this session, decisions already locked.

## 4. Detailed Change Proposals

### 4.1 AGENTS.md § "BMAD vanilla-first" correction

Replace L192-205 with corrected version. Diff sketch:

- Drop: "examples observed in this repo: multi-section single `prd.md` with `## Initiative N` H2 sections appended per feature"
- Drop: paragraph L196 entirely ("The existing `## Initiative 0/1/2/3` H2 sections ... are legacy non-vanilla state; do NOT extend that pattern in new work.")
- Drop: "Repo precedent that diverges from vanilla — examples observed in this repo: [...], direct edits to `architecture.md` instead of rerunning `bmad-create-architecture` via `bmad-correct-course`, routing-around a protesting skill — MUST be flagged to the operator with both options surfaced."
- Reframe: skill-discipline rules (the actual content — mandatory bmad-help, no routing-around, bmad-correct-course canonical entry, no direct artifact edits bypassing CC recommendation) remain.
- Add brief context: "BMAD vanilla assumes a single project-wide PRD model and has no documented support for multi-initiative brownfield projects (per docs.bmad-method.org/llms-full.txt). This repo's `## Initiative N` H2-append pattern in monolithic `prd.md`/`architecture.md`/`epics.md` is a pragmatic workaround for that methodology gap; it is the closest-to-vanilla shape attainable given the gap, and IS the pattern new initiatives should extend."

### 4.2 Memory `feedback_vanilla_bmad_first.md` correction

Analogous: keep skill-discipline framing, drop per-feature/multi-section framing.

### 4.3 Archive moves

```
mkdir -p _bmad-output/planning-artifacts/archive/
mv _bmad-output/planning-artifacts/prd-validation-report.md _bmad-output/planning-artifacts/archive/
mv _bmad-output/planning-artifacts/implementation-readiness-report-2026-05-15.md _bmad-output/planning-artifacts/archive/
mv _bmad-output/planning-artifacts/init5-handoff-2026-05-18.md _bmad-output/planning-artifacts/archive/
mv _bmad-output/planning-artifacts/codex-readiness-rerun-2026-05-16-prompt.md _bmad-output/planning-artifacts/archive/
mv _bmad-output/implementation-artifacts/epic-1-symbolication-regression.md _bmad-output/planning-artifacts/archive/
mv _bmad-output/implementation-artifacts/spec-deploy-skip-gate.md _bmad-output/planning-artifacts/archive/
```

Note: cross-file moves (epic-1-symbolication-regression + spec-deploy-skip-gate live in `implementation-artifacts/` originally) end up in the single `planning-artifacts/archive/` to keep the archive cohesive. Operator can override if they prefer `implementation-artifacts/archive/` for those two.

### 4.4 Init 2 hygiene note

Edit `_bmad-output/planning-artifacts/epics.md` § Initiative 2 § Overview (~line 718, after `**Status:** ✅ shipped 2026-05-11 ...` line). Add a sentence-level note: *"**No product brief in `_bmad-output/planning-artifacts/`.** Init 2 was planned + executed via the autonomous chain (Session 2, 2026-05-10) without a separate brief stage; scope was small enough that brief + distillate were folded into the PRD extension directly. Acknowledged hygiene gap per `feedback_docs_hygiene`."*

### 4.5 Delete empty dirs

```
rm -rf _bmad-output/test-artifacts/test-reviews
rmdir _bmad-output/test-artifacts 2>/dev/null  # only if empty after above
```

## 5. Implementation Handoff

### 5.1 Scope classification

**Minor** — doc corrections + file moves + one sentence-level addition. Zero code touched. Phase 1 is single-session direct-implementation by current agent.

### 5.2 Routing

| Phase | Operator action | Executor | Output |
|---|---|---|---|
| Phase 0 — Approve v2 proposal | Read this doc, approve or revise | (operator review) | This sprint change proposal v2 approved |
| Phase 1 — Cleanup + recalibration | Approve execution | Current Claude session (this context) | Edited AGENTS.md + memory + 6 archived files + Init 2 note + cleanup verified |
| Phase 1 commit | (operator only) git commit `chore(bmad): vanilla recalibration + audit cleanup` | (operator-controlled) | Tracked commit on AGENTS.md (only AGENTS.md is tracked; _bmad-output is gitignored) |
| Phase 2 step 1 | `/bmad-help` in fresh session | Operator-driven | Routing recommendation (expected: `bmad-correct-course` for Init 5 extension) |
| Phase 2 step 2 | `/bmad-correct-course` | Fresh session | New sprint change proposal recommending `bmad-edit-prd` + manual edits |
| Phase 2 step 3 | `/bmad-edit-prd` on `prd.md` | Fresh session per step | `## Initiative 5` H2 in `prd.md` |
| Phase 2 step 4 | Manual edit `architecture.md` | Fresh session OR same as step 3 | `## Initiative 5` H2 in `architecture.md` |
| Phase 2 step 5 | Manual edit `epics.md` + stories | Fresh session OR same as step 4 | `## Initiative 5` H2 in `epics.md` |
| Phase 2 step 6 | `/bmad-check-implementation-readiness` | Fresh session | New readiness report |
| Phase 2 step 7 | `/bmad-sprint-planning` | Fresh session | Updated sprint-status.yaml |

### 5.3 Success criteria for Phase 1

- `grep -c "legacy non-vanilla\|per-feature PRD files" AGENTS.md` returns `0`
- `grep -c "multi-section single PRD\|per-feature" ~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_vanilla_bmad_first.md` returns `0` (or low) — false framing dropped
- `ls _bmad-output/planning-artifacts/archive/` shows 6 archived files
- `ls _bmad-output/planning-artifacts/prd-validation-report.md _bmad-output/planning-artifacts/implementation-readiness-report-2026-05-15.md _bmad-output/planning-artifacts/init5-handoff-2026-05-18.md _bmad-output/planning-artifacts/codex-readiness-rerun-2026-05-16-prompt.md _bmad-output/implementation-artifacts/epic-1-symbolication-regression.md _bmad-output/implementation-artifacts/spec-deploy-skip-gate.md` all return `No such file or directory`
- `grep -c "No product brief in" _bmad-output/planning-artifacts/epics.md` returns `1`
- `ls _bmad-output/test-artifacts/` shows empty or directory doesn't exist
- Skill-discipline rules (mandatory bmad-help, no routing-around, CC canonical entry) still present in AGENTS.md (positive grep check)

### 5.4 Success criteria for Phase 2 (later, post-Init-5 planning)

- `_bmad-output/planning-artifacts/prd.md` contains `## Initiative 5` H2 section
- `_bmad-output/planning-artifacts/architecture.md` contains `## Initiative 5` H2 section
- `_bmad-output/planning-artifacts/epics.md` contains `## Initiative 5` H2 section
- `sprint-status.yaml` contains entries for Init 5 epics + stories
- All Init 5 content matches brief v2 + distillate (no re-elicitation evidence)

## 6. Locked decisions

| Decision | Final answer | Source |
|---|---|---|
| Cleanup approach | Recalibration + audit-driven cleanup (NOT per-feature migration) | Operator sanity-check 2026-05-18; vanilla = single-file modify-in-place |
| sprint-status.yaml shape | Keep flat global | Operator approved (Recommended) |
| Epic numbering convention | Per-file local `## Epic {{N}}` (BMAD vanilla template); but Init 5 H2 in current monolithic `epics.md` will continue Init 0/1/2/3 pattern (`#### Epic N` under `## Initiative 5`) — H2-append pragmatic workaround | Operator chose "as close to BMAD vanilla as possible"; resolves to current pattern |
| Init 5 doc shape | Monolithic single-file H2 extension (continuation) | Forced by vanilla recalibration |
| Stale vanilla reports | Archive both (prd-validation-report + readiness-report-2026-05-15) | Operator approved (Recommended) |
| Init 2 brief gap | Skip + explicit hygiene note in epics.md | Operator approved (Recommended) |
| Archive location | `_bmad-output/planning-artifacts/archive/` | Operator approved (Recommended) |

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AGENTS.md correction drops a load-bearing rule by accident | Low | Medium | Diff review before commit; success-criteria grep checks (positive: skill-discipline rules present; negative: false claims absent) |
| Archived files needed later for forensic reference | Low | Low | Archive vs delete keeps them recoverable; only loss is one mv operation away from restore |
| Init 5 vanilla path needs adjustments not anticipated in Phase 2 plan | Medium | Low | Phase 2 step 2 (`bmad-correct-course`) produces its own sprint change proposal; that proposal is the authoritative routing for Init 5, not this one. This doc only guarantees Phase 1 leaves a hygienic baseline. |
| Operator wants to revisit per-feature shape later | Low | Medium | If methodology evolves, future migration is a new CC pass; nothing in Phase 1 forecloses that option |
| Some "spec-*" filename specs are deemed non-canonical and should be renamed | Low | Low | Scope-bounded out of Phase 1 (operator review can prioritize separately); naming inconsistency is hygiene debt not vanilla violation |

## 8. Open operator decision — Phase 1 execution

All sub-decisions are locked (§ 6). The remaining question is execution authority.

If operator approves Phase 1 execution in this session:

- I will execute steps 4.1 — 4.5 in this single context window.
- Phase 2 will run in fresh sessions per BMAD-help CSV constraint ("recommend running each skill in a fresh context window").
- Commit will be operator-only (AGENTS.md is tracked; _bmad-output is gitignored).

If operator wants Phase 1 in a fresh session:

- This proposal becomes the input for a fresh `bmad-quick-dev` invocation.
- Cost: re-load proposal as spec.

If operator wants additional clarification before Phase 1:

- Pause here, surface the specific concern.
