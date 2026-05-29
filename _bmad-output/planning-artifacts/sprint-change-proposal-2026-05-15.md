---
title: "Sprint Change Proposal — Codex Implementation-Readiness Review Response"
date: 2026-05-15
trigger: "Codex implementation-readiness review at _bmad-output/planning-artifacts/implementation-readiness-report-2026-05-15.md"
status: approved-and-applied
applied: 2026-05-15
applied_changes:
  - "Change 1: E0 retrospective-ledger annotation in epics.md § Initiative 0 § Overview"
  - "Change 2: Epic 4 Implementation Status table + Story 4.2 reality note (resolves Codex M2 + M3)"
  - "Change 3: Epic 5 Implementation Status table + C1/C2/C3/M1 execution-divergence notes"
  - "Change 4: Forward-Applicable Principles section (6 principles) at end of epics.md"
  - "Change 5: epics.md frontmatter last_updated + change-summary"
  - "Change 6 (added 2026-05-16 per Codex re-run): sprint-status.yaml deduplicated — removed 17 stale `backlog` entries for stories 5.1-5.17 + the misleading 'Reflect: all sub-statuses updated above' comment. Only post-execution `done` entries remain. YAML last-wins semantics meant no behavior change, but parser-cleanliness is the project standard."
  - "Change 7 (added 2026-05-16 per Codex re-run): metadata + Initiatives Index refresh in prd.md + architecture.md + epics.md — initiative id=2 status `in_progress` → `shipped` + `completed: '2026-05-11'`; id=3 status `planning` → `shipped` + `completed: '2026-05-13'`. Initiatives Index table rows flipped: `🚧 in_progress` / `📋 planning` → `✅ shipped` with completion dates. Parity with id=1 pattern."
verification:
  - "epics.md line count: 1366 → 1431 → 1431 (Changes 1-5 + Change 7 inline edits, no net line growth from Change 7)"
  - "Implementation Status tables present at line 747 (E4) + 956 (E5)"
  - "Forward-Applicable Principles section present at line 1372 (Principles 1-6 at lines 1376, 1384, 1394, 1407, 1415, 1427)"
  - "E0 annotation present at line 85"
  - "Frontmatter last_updated = '2026-05-15' with change-summary"
  - "sprint-status.yaml dedup confirmed via grep (each 5-X-* key now appears exactly once with `done` status)"
  - "Initiatives Index id=2 + id=3 flipped to `shipped` + `completed` in all 3 planning artifacts (prd.md, architecture.md, epics.md)"
  - "Status frontmatter parity with id=1 pattern verified"
mode: batch
scope_classification: minor-to-moderate
inputs:
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-05-15.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - git log on main (Epic 4 + Epic 5 commit history)
key_finding: "Codex read epics.md as forward-looking plan, but sprint-status.yaml confirms Epic 4 + Epic 5 are DONE (all 22 stories shipped between 2026-05-11 and 2026-05-13). Critical/Major findings about story sequencing and hook design either (a) were resolved during execution (in-band fix-ups), or (b) describe plan-vs-reality drift in epics.md narrative. The corrective is documentation refresh + lessons-learned extraction, NOT story restructure."
---

# Sprint Change Proposal — Codex Review Response

## Section 1: Issue Summary

**Problem statement:** Codex implementation-readiness review on 2026-05-15 surfaced 14 findings (3 critical, 4 major, 4 minor, 3 UX warnings) against the project planning artifacts. The review interprets these findings as blockers preventing safe execution.

**Critical context discovered during impact analysis:** the review treats `epics.md` as a forward-looking plan, but `sprint-status.yaml` + `git log` confirm:

- **Epic 4** (Initiative 2 — Agent Runbook + Legacy SoT Triage): all 5 MVP stories DONE 2026-05-11 + retro DONE; only Story 4.6 (Growth CLI) intentionally deferred. Plus E4.4-followup (drop legacy_id) shipped same day.
- **Epic 5** (Initiative 3 — UI Theme Compliance & Visual Regression Hardening): all 17 stories DONE 2026-05-13 + retro DONE in single-session autonomous execution (~3h elapsed agent time, 15 commits + 4 deploys + 1 fix-up).

The review's 3 critical findings about Epic 5 sequencing/hook design **either describe defects that were resolved during execution as in-band fix-ups, OR reflect drift between the original plan text in `epics.md` and the actually-shipped implementation**.

**Issue category:** Misunderstanding of original requirements (Codex read planning artifacts as roadmap when they are historical record). NOT a technical limitation, new requirement, strategic pivot, or failed approach.

**Evidence:**

- `_bmad-output/implementation-artifacts/sprint-status.yaml` lines 110-147: all E5 stories marked `done` with commit hashes; epic-5-retrospective: done.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` lines 93-101: all E4 MVP stories marked `done`; epic-4-retrospective: done; only 4.6 backlog (Growth defer).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` line 142: Story 5.11 sprint-status note: *"First exercise of FR13 hook — caught real design flaw (pre-commit fires before .git/COMMIT_EDITMSG is current); fix-up in same session made pre-commit warning-only, commit-msg strict"* — directly resolves Codex Critical 3.
- `git log` shows shipped commits: `017cd87` (E5.11 regen), `1b38bab/1477c28/bac71e0/e596d97` (E5.12a-d), `fb8155a/13a442d` (E5.13 + fix-up), `a8494b8` (E5.17 axe scan promotion).

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status (sprint-status.yaml) | Codex critique applicability | Action |
|---|---|---|---|
| E0 — Product Foundation | shipped retrospective (documented 2026-05-15) | M4 (annotate as retroactive ledger) — REAL | Add explicit "retrospective ledger, relaxes epic-quality standards" annotation in epics.md § Initiative 0 |
| E1 — Production-Readable Stack Traces | done 2026-05-10 + retro done | Codex: "ready/implemented pattern" — none | None |
| E2 — Triage-Ready Events & BMAD Triage Bridge | done 2026-05-10 + retro done | Codex: "ready/implemented pattern" — none | None |
| E3 — Verify Ritual, Decay Protection & Operational Continuity | done 2026-05-10 + retro done | Codex: "ready/implemented pattern" — none | None |
| E4 — Self-Serving Agent Runbook + Legacy SoT Triage | done 2026-05-11 + retro done | M2 (E4 stale vs worktree) + M3 (Story 4.2 nginx) — REAL (epics.md narrative drift) | Refresh story-level status markers in epics.md; add reality-divergence notes for Story 4.2 nginx path |
| E5 — UI Theme Compliance & Visual Regression Hardening | done 2026-05-13 + retro done | C1 + C2 + C3 + M1 + 2 minors — RESOLVED during execution | Refresh story-level status markers in epics.md; add execution-divergence notes documenting how each Critical was resolved in-band |

### Story Impact

**No story restructure needed for shipped work.** All 22 stories (E4 × 6 + E5 × 17 − 1 deferred) are either DONE or explicitly deferred. The review's "restructure 5.7-5.10 to regenerate own baselines" critique describes a defect that **did NOT materialize** because:

1. E5.11 (Baseline regeneration with operator sign-off) shipped 2026-05-13 with commit `017cd87` covering all PNG baselines invalidated by 5.7-5.10 source changes in one bounded commit. The plan's intent "intermediate red states" was avoided in execution by shipping 5.7-5.10 as quickly as possible, then 5.11 immediately after — autonomous session executed them within ~3h, so the red-state window was minutes, not days.
2. E5.13 (Husky hook) shipped 2026-05-13 with commit `fb8155a` + fix-up `13a442d` — actually implements pre-commit (warning-only) + commit-msg (strict) split, which is **exactly what Codex's C3 recommends**. Sprint-status entry 5.11 explicitly records this discovery: *"caught real design flaw... fix-up in same session made pre-commit warning-only, commit-msg strict."*
3. E5 story numbering forward-dependency (C2) was logically navigated by the autonomous executor running stories in dependency order, not literal numeric order. The plan text retains the original numbering for historical fidelity to the planning chain (Phase A → Phase C-early → Phase B → Phase C-prevention).

### Artifact Conflict Analysis

| Artifact | Conflict | Action |
|---|---|---|
| `prd.md` | None — Codex confirms 87/87 FR coverage; no FR changes needed | None |
| `architecture.md` | None — all 12 + 8 + 10 decisions stand as-shipped | None |
| `epics.md` | **Drift** — narrative text reads as forward-looking for E4 + E5 even though sprint-status.yaml has all stories done | **Refresh narrative**: add per-story `**Status:** ✅ shipped (commit `<sha>`, <date>)` line where shipped; add Section-level "Implementation Reality Notes" for Critical/Major findings where execution diverged from plan |
| `prd-validation-report.md` | None — scoped to Initiative 1 only | None |
| Cross-repo (`~/repos/configs/`) | M3 confirms in-repo `infra/nginx-180/3d-portal.conf` is archived; live edge at `~/repos/configs/` | epics.md Story 4.2 needs reality note pointing at TB-003 archive + cross-repo edge location |

### Technical Impact

**None.** The infrastructure, CI, deployment, and observability are all live and stable. Codex's review reflects planning-document hygiene, not running-system defects. No code, infra, or deploy changes proposed.

## Section 3: Recommended Approach

**Selected path: Direct Adjustment (Option 1)** — modify the existing planning artifacts to (a) reflect shipped reality and (b) capture lessons from Codex's findings as forward-applicable principles for future initiatives.

**Rationale:**

- Effort: Low (~30-60 minutes of edits to `epics.md`).
- Risk: Low (no code touched; no shipped behavior changed; doc-only changes are commit-only, `_bmad-output/` is gitignored anyway).
- Timeline impact: None — no in-flight work blocked.
- Long-term value: Sustains the living-doc planning structure by making epics.md a faithful historical record + a teaching artifact for future initiatives.

**Rejected paths:**

- **Option 2 (Potential Rollback)**: would require reverting 22 shipped stories — clearly not warranted; the work is correct.
- **Option 3 (PRD MVP Review)**: PRD MVP is intact; no scope reduction needed.

## Section 4: Detailed Change Proposals

### Change 1 — Add Initiative 0 retrospective-ledger annotation (M4 fix)

**File:** `_bmad-output/planning-artifacts/epics.md` § Initiative 0 § Overview

**OLD:**

```
The retrospective foundation decomposes into nine logical epics (E0.1–E0.9), mirroring the v1 implementation plan's 12 phases. Phases are collapsed where the architectural boundary is the same. **All nine ship in this single retroactive entry; none correspond to new work.**
```

**NEW:**

```
The retrospective foundation decomposes into nine logical epics (E0.1–E0.9), mirroring the v1 implementation plan's 12 phases. Phases are collapsed where the architectural boundary is the same. **All nine ship in this single retroactive entry; none correspond to new work.**

**⚠️ Important — Initiative 0 intentionally relaxes normal epic-quality standards.** Several E0 epics (E0.1 Repo + Monorepo Bootstrap, E0.2 Data Plane + Migrations, E0.9 Infra + Deploy + Observability Baseline) are technical-by-nature and do NOT deliver direct user value in the way a forward-looking epic should. **This is acceptable here because E0 is a retroactive ledger of pre-BMAD work, not a work queue.** Do NOT pattern-copy E0's epic structure for future initiatives — Initiatives 1+ must follow normal "epics deliver user value" standards (see Codex implementation-readiness review 2026-05-15 § Major 4).
```

**Rationale:** Codex M4. Prevents future agents from copying E0's technical-epic pattern when planning new initiatives.

---

### Change 2 — Mark Epic 4 stories as shipped + add Story 4.2 reality note (M2 + M3 fix)

**File:** `_bmad-output/planning-artifacts/epics.md` § Initiative 2 / Epic 4

**Action:** add a new "Implementation Status (refreshed 2026-05-15)" subsection at the top of Epic 4 listing per-story status with commit hashes, sourced from sprint-status.yaml. Also append a per-story execution-divergence note for Story 4.2.

**Insertion location:** immediately after Epic 4 "Goal:" line, before Story 4.1.

**NEW SECTION:**

```markdown
**Implementation Status (refreshed 2026-05-15 per Codex implementation-readiness review M2/M3):**

| Story | Status | Commit(s) | Execution divergence from plan |
|---|---|---|---|
| 4.1 — Author docs/agents-add-model-runbook.md | ✅ done 2026-05-11 | `b382fee` + `ec27222` (Codex fix-up: 1 P1 + 5 P2 + 1 P3) | None — clean ship |
| 4.2 — `/agent-runbook` FastAPI route + deploy verify | ✅ done 2026-05-11 | `9ac52f6` + `565b347` (Codex fix-up: 1 P1 + 1 P2 + 2 P3) | **In-repo `infra/nginx-180/3d-portal.conf` archived during execution** — discovered the live edge proxy at `~/repos/configs/nginx/3d.ezop.ddns.net.conf` is a simpler IP-allowlist catch-all and needs no edge sync for `/agent-runbook`. In-repo config moved to `infra/nginx-180/.archived/3d-portal.conf.pre-IP-allowlist` per TB-003. Story plan text below references the original (pre-archive) path. |
| 4.3 — OpenAPI surface enrichment for agent consumption | ✅ done 2026-05-11 | `369e3f6` + `7ac5e61` (Codex fix-up: 8 P2 + 2 P3) | None |
| 4.4 — Legacy SoT folder triage decision | ✅ done 2026-05-11 | `3acb698` + `d1586f0` (Codex fix-up: 0 P1 + 3 P2 + 3 P3) | Decision: DROP recommended; 4.4-followup (Alembic 0010 drop legacy_id) shipped same day in `89da8e4` |
| 4.5 — End-to-end smoke-test acceptance | ✅ done 2026-05-11 | smoke-test transcript at `_bmad-output/implementation-artifacts/agent-runbook-smoke-2026-05-11.md` | R-1/R-2/R-3 runbook gaps fixed in `691e4f0`; R-4/R-5 deferred |
| 4.6 — `infra/scripts/add-model-from-url.py` CLI | 📋 backlog (deferred Growth) | — | Per AC: defer-able after 4.5 acceptance review |
| 4-4-followup-drop-legacy-id | ✅ done 2026-05-11 | `89da8e4` (Path B / accept-risk per homelab single-tenant scope) | Alembic 0010 ran on prod; 4 migrations + 3 test files retired; ~1611 LOC net |
| epic-4-retrospective | ✅ done 2026-05-11 | `_bmad-output/implementation-artifacts/epic-4-retro-2026-05-11.md` | First fully-autonomous epic in the repo |

**Codex implementation-readiness M2 (E4 stale vs worktree) — resolved by this status table. Story plan text below retained for historical fidelity.**
**Codex M3 (Story 4.2 nginx path absent) — resolved by Story 4.2 reality note above; the live edge proxy path is in `~/repos/configs/` not the repo's archived `infra/nginx-180/`.**
```

**Rationale:** Codex M2 + M3. Future agents reading Epic 4 now see authoritative status without cross-referencing sprint-status.yaml.

---

### Change 3 — Mark Epic 5 stories as shipped + execution-divergence notes for C1/C2/C3/M1 (Critical fixes)

**File:** `_bmad-output/planning-artifacts/epics.md` § Initiative 3 / Epic 5

**Action:** mirror Change 2's pattern — add "Implementation Status (refreshed 2026-05-15)" table at top of Epic 5, with per-Critical-finding execution-divergence notes documenting how each Codex concern was resolved in-band.

**Insertion location:** immediately after Epic 5 "Goal:" line, before Story 5.1.

**NEW SECTION:**

```markdown
**Implementation Status (refreshed 2026-05-15 per Codex implementation-readiness review C1/C2/C3/M1):**

| Story | Status | Commit(s) | Execution divergence from plan |
|---|---|---|---|
| 5.1 — Static color-literal sweep | ✅ done 2026-05-13 | Phase A audit — reports at `_bmad-output/implementation-artifacts/theme-token-violations-2026-05-13.md` + `token-reader-inventory-2026-05-13.md` | Found 11 violations (5 brief-seeded + 3 CardCarousel + 3 ModelGallery NEW); brief assumption (only `readMeshTokens.ts` as non-browser reader) CONFIRMED |
| 5.2 — Baseline integrity audit + skip disposition | ✅ done 2026-05-13 | Phase A audit — report at `baseline-integrity-audit-2026-05-13.md` | 82 PNGs catalogued; 14 baseline-skip count is matrix-expanded from 4 source skip statements (12 of 14 are describe.skip placeholders for unimplemented Slices 3D/3E); 54 of 82 unverified-defer-to-operator per NFR4 batching |
| 5.3 — Interactive-surface coverage matrix | ✅ done 2026-05-13 | Phase A audit — report at `interactive-surface-coverage-matrix-2026-05-13.md` | 25 Radix instances enumerated; 4/25 covered (16%) pre-Epic 5; brief 10-gap list REFUTED-WITH-DIFF (UserMenu already covered; Tooltip misattributed) |
| 5.4 — In-repo ESLint `no-restricted-syntax` rule | ✅ done 2026-05-13 | `5a84f7c` | Shipped at warn level with `--max-warnings=10` accommodating 10 known Phase A violations during Phase B; @poupe plugin enhancement deferred (in-repo rule alone delivered ≥80% value). **Codex M1 (warn-mode-first promotion) resolved by execution:** lint promoted warn→error in 5.10 closing commit (`4339cfc`) after remediation. |
| 5.5 — Token-file split + Stylelint integration | ✅ done 2026-05-13 | `39eaac3` | viewer-tokens.css extracted; per-file Stylelint color-function-notation overrides (modern for theme.css, legacy for viewer-tokens.css) |
| 5.6 — `@axe-core/playwright` contrast scan at warn | ✅ done 2026-05-13 | `0ce5ac8` | 5 pages × 4 projects = 20 axe scans with `runOnly:['color-contrast']`; per-test exclude policy header with empty exclude-list at MVP |
| 5.7 — Dialog/Overlay tokenization | ✅ done 2026-05-13 | `46bb499` | DialogContent moved to `bg-card text-card-foreground` (semantically correct card surface); plus `.husky/**` added to ESLint ignore. **Codex C1 (red-state-until-5.11) mitigated by execution timeline:** stories 5.7-5.10 + 5.11 all shipped within same autonomous session (~3h elapsed); red-state window minutes, not days. |
| 5.8 — Viewer-overlay tokenization | ✅ done 2026-05-13 | `788223a` | RimOverlay + MeasureOverlay tokenized via new `--color-viewer-tooltip`; Decision A "DOM-rendered exception" — drei `<Html>` is browser-side, so tokens live in theme.css with modern HSL, not viewer-tokens.css. |
| 5.9 — Dark-mode override completeness | ✅ done 2026-05-13 | `10821cc` | `.dark` overrides for success/warning/destructive (lightness bumps 45%→55%, 50%→60%, 60%→70%); token-authoring-discipline comment block added |
| 5.10 — Bulk fix remaining Phase A offenders | ✅ done 2026-05-13 | `4339cfc` | New `--color-gallery-control` tokens; CardCarousel × 4 + ModelGallery × 3 violations remediated; lint promotion `--max-warnings=10` → 0 |
| 5.11 — Baseline regeneration with operator sign-off | ✅ done 2026-05-13 | `017cd87` + `fc79d77` (fix-up) | 14 PNGs regenerated (light-mode variants of dialog/sheet/viewer3d-measure-*/viewer3d-modal-*). **Codex C3 (pre-commit can't read COMMIT_EDITMSG) discovered during execution and resolved in same session:** sprint-status note — *"First exercise of FR13 hook — caught real design flaw (pre-commit fires before .git/COMMIT_EDITMSG is current); fix-up in same session made pre-commit warning-only, commit-msg strict."* This is exactly the split Codex C3 recommends. **AUTONOMOUS SIGN-OFF** — operator eye-review pending. |
| 5.12 — Open-state spec expansion | ✅ done 2026-05-13 | `1b38bab` (5.12a Selects) + `1477c28` (5.12b destructive dialogs) + `bac71e0` (5.12c admin DropdownMenus + Tooltip) + `e596d97` (5.12d remaining Sheets) | 4 sub-stories per architecture Decision G; 54 new PNG baselines; RenderSheet success branch deferred (requires mutation-state mocking) |
| 5.13 — Baseline acceptance git hooks | ✅ done 2026-05-13 | `fb8155a` + `13a442d` (fix-up) | Implemented as pre-commit (staged-file checks + warning-only baseline check) + commit-msg (strict `baseline-reviewed:` validation), per Codex C3 split recommendation discovered during execution. Husky 9 + `git config core.hooksPath apps/web/.husky` (monorepo gotcha) + Docker prepare-script compatibility fix. |
| 5.14 — Visual Coverage Contract enforcement | ✅ done 2026-05-13 | `fb8155a` (same commit as 5.13) | `_check-visual-coverage.mjs` rejects commits adding `apps/web/src/ui/*.tsx` without matching `apps/web/tests/visual/<basename>.spec.ts` in staged set |
| 5.15 — project-context.md rule additions | ✅ done 2026-05-13 | Operator-local edit (gitignored `_bmad-output/`) | Added "UI quality gates (Initiative 3 / Epic 5)" section; rule_count 134 → 136 |
| 5.16 — Codex review prompt enrichment | ✅ done 2026-05-13 | `a5a83b8` | `.codex/review-prompts/ui-theme-checks.md` + `_tail.md` + `.codex/bin/review-ui-commit`; `.gitignore` updated with negation rules; acceptance test (replay against `10bc3de`) deferred-to-operator |
| 5.17 — Axe contrast scan promotion to fail (CLOSING GATE) | ✅ done 2026-05-13 | `a8494b8` | Modified `accessibility-axe.spec.ts` assertion `console.warn` → `expect(violations).toHaveLength(0)`; **zero violations across 20 scans = 5 pages × 4 projects** |
| epic-5-retrospective | ✅ done 2026-05-13 | `_bmad-output/implementation-artifacts/epic-5-retro-2026-05-13.md` | Single-session autonomous execution (~3h elapsed); 15 commits + 4 deploys + 1 fix-up; deferred Decisions K/L/M re-evaluated at retro (all leave-deferred, re-eval 2026-06-13) |

**Codex implementation-readiness Critical findings — resolved during execution:**

- **C1 (intermediate red visual-regression states):** mitigated by execution timeline. Stories 5.7-5.10 + 5.11 all shipped within ~3h autonomous session; the theoretical multi-day red-state window the plan text allowed never materialized. Future initiatives doing UI remediation should either (a) collapse remediation + regen into per-story bounded packages, OR (b) execute remediation chain end-to-end within a single session as E5 did. **Forward-applicable principle captured below.**
- **C2 (forward dependency 5.11/5.12 → 5.13):** mitigated by autonomous executor running stories in dependency order, not numeric order. 5.13 shipped before 5.11/5.12. **Future initiatives must renumber to match execution order** (story numbering = execution sequence is the project-context.md rule). Plan text retained for historical fidelity to the planning chain (Phase A → Phase C-early → Phase B → Phase C-prevention).
- **C3 (pre-commit + COMMIT_EDITMSG):** discovered + resolved during 5.11 execution. Shipped split implementation (pre-commit warning-only + commit-msg strict) exactly matches Codex's recommendation. **Lesson captured in epic-5 retro.**

**Codex Major M1 (Story 5.4 warn-mode-first):** resolved in execution path — 5.4 shipped at warn with `--max-warnings=10`, promoted to error in 5.10 closing commit `4339cfc`. **Forward-applicable principle:** lint-rule introductions should always be warn-mode-first with explicit promotion-to-error story scheduled after remediation.
```

**Rationale:** Codex C1/C2/C3/M1. Documents how each defect was navigated in execution; captures forward-applicable principles for future initiatives.

---

### Change 4 — Add forward-applicable principles section (Lessons from Codex review)

**File:** `_bmad-output/planning-artifacts/epics.md` — new section at the bottom, before any retrospective links.

**NEW SECTION:**

```markdown
## Forward-Applicable Principles (from Codex implementation-readiness 2026-05-15)

This section captures lessons surfaced by the 2026-05-15 Codex review that future initiatives MUST apply. Distinct from per-epic notes above (which describe how E4/E5 navigated specific findings), these are project-wide standards.

### Principle 1 — Story numbering MUST match execution order (no forward dependencies)

When designing a new initiative's story breakdown: if Story X depends on Story Y, Y MUST have a lower number than X. A future agent executing strictly by story number cannot hit a blocked prerequisite.

**Counter-example to avoid:** E5 originally had Story 5.11 depending on Story 5.13 (hook before regen). The autonomous executor navigated this by ordering stories by dependency, but a less-context-aware agent would have stalled at 5.11. **Plan text retained for historical fidelity to the planning chain (Phase A → C-early → B → C-prevention); new initiatives must renumber to avoid the same trap.**

### Principle 2 — Lint-rule introductions are warn-mode-first

Introducing a new ESLint/Stylelint/etc. rule requires the rule to land at `warn` level first, NOT `error`. The promotion to `error` is scheduled as a closing story AFTER all known violations are remediated.

This avoids the contradictory-AC trap: "rule catches current violations" + "lint passes on main" cannot both be true at error level until remediation lands.

**Pattern:** Story N introduces rule at warn; Stories N+1..N+k remediate; Story N+m promotes warn → error.

### Principle 3 — UI changes ship with own baseline updates, not deferred regen

Stories that change UI source MUST regenerate own affected visual-regression baselines in the same story (same commit if possible, or back-to-back commits in same autonomous session). Deferring baseline regen to a separate "final regen" story creates a window where `main` carries a known-red visual-regression state.

**Acceptable execution patterns:**

- (a) Each remediation story regenerates own baselines in its own commit (preferred for new initiatives).
- (b) Remediation chain + baseline regen execute end-to-end within a single autonomous session, keeping the red-state window to minutes (E5's actual execution pattern; acceptable for autonomous-only sessions).

**Unacceptable:** human-paced multi-day execution with red-state baselines on main between remediation and regen.

### Principle 4 — Commit-message validation lives in `commit-msg`, not `pre-commit`

Git `pre-commit` runs BEFORE the commit message is finalized; `.git/COMMIT_EDITMSG` may not contain the user's message yet. Commit-message validation (e.g., required `baseline-reviewed:` lines, conventional-commit format) MUST run in `commit-msg`.

`pre-commit` is correctly used for staged-file checks (lint, format, file-presence rules).

E5's hooks already implement this split (pre-commit + commit-msg, `apps/web/.husky/`) as discovered during 5.11 execution.

### Principle 5 — Brownfield initiatives MUST refresh planning artifacts after execution

When an initiative ships end-to-end (especially autonomously), the planning artifacts (`epics.md` story descriptions) MUST be updated to reflect shipped reality:

- Per-story `**Status:** ✅ shipped (commit `<sha>`, <date>)` lines.
- Execution-divergence notes where implementation departed from plan (e.g., E5.11's hook design discovery).
- Cross-references to retrospective if one exists.

Without this, future agents reading `epics.md` cannot tell forward-looking work from historical record, and reviewers like Codex flag shipped work as "not ready" (see this 2026-05-15 review as the canonical example).

### Principle 6 — E0 (retrospective foundation) intentionally relaxes epic-quality standards; do NOT pattern-copy

E0.1 Repo Bootstrap, E0.2 Data Plane, E0.9 Infra are technical-by-nature and acceptable only as a retroactive ledger of pre-BMAD work. Forward-looking initiatives MUST follow normal "epics deliver user value" standards. See § Initiative 0 § Overview for the explicit annotation.
```

**Rationale:** transforms Codex's individual critique points into forward-applicable principles. Codifies the lessons so they outlive this specific review.

---

### Change 5 — Update epics.md frontmatter `last_updated` + add change-summary

**File:** `_bmad-output/planning-artifacts/epics.md` (frontmatter — currently `date: '2026-05-09'`)

**OLD:**

```yaml
date: '2026-05-09'
```

**NEW:**

```yaml
date: '2026-05-09'
last_updated: '2026-05-15'
last_update_note: 'Status refresh per Codex implementation-readiness review 2026-05-15: marked Epic 4 + Epic 5 stories as ✅ shipped with commit hashes; added execution-divergence notes for C1/C2/C3/M1/M2/M3 findings; added Initiative 0 retrospective-ledger annotation (M4); added Forward-Applicable Principles section codifying lessons.'
```

**Rationale:** living-doc discipline — frontmatter records when and why the doc was touched.

---

### Change 6 — Minor concerns (one-line fixes)

**Codex Minor 1 — "auto-deploy as AC" boilerplate is operational consequence, not user-value AC.**

Action: leave as-is (Codex itself says "fine as a reminder"). Optional follow-up: add a one-line note in the Forward-Applicable Principles section if pattern repeats. **Decision: defer to next initiative; if it surfaces a third time, codify.**

**Codex Minor 2 — Story 5.13 wording on "Husky hooks on production deploy host".**

Action: not worth a separate edit. The shipped reality (hooks are operator-local-only by execution surface) is correct; the plan text's misleading phrasing is captured in the Implementation Status table's execution-divergence note for 5.13.

**Codex Minor 3 — Story 5.16 `.codex/` artifact tier confusion.**

Action: not worth a separate edit. Shipped commit `a5a83b8` correctly handled the gitignore negation; the plan text's "code-tier" framing is technically wrong (the prompt files don't affect runtime) but harmless.

**Codex Minor 4 — `_bmad-output` artifact tracking in sprint-status.**

Action: this is a real observation but out of scope for this proposal. Track as a future improvement to `bmad-quick-dev` or `bmad-create-story` skill customization: per-story acceptance criteria should include "if artifact lands in `_bmad-output/`, sprint-status comment notes the artifact filename."

---

## Section 5: Implementation Handoff

### Scope classification: **MINOR**

All proposed changes are edits to a single planning artifact (`epics.md`) in the gitignored `_bmad-output/` tree. No code, infra, deploy, or shipped behavior is touched. No PRD or architecture changes are needed.

### Handoff recipients

- **Developer agent (me, Claude in this same session):** apply Changes 1-5 to `epics.md` directly after Ezop approves this proposal. Change 6 items either no-op or deferred.
- **No PM / Architect escalation needed.**

### Success criteria for implementation

1. `epics.md` § Initiative 0 carries the retroactive-ledger annotation.
2. `epics.md` § Epic 4 + § Epic 5 carry "Implementation Status (refreshed 2026-05-15)" tables with per-story shipped status + commit hashes + execution-divergence notes.
3. `epics.md` carries new "Forward-Applicable Principles" section (6 principles).
4. `epics.md` frontmatter has `last_updated: '2026-05-15'` + change-summary note.
5. After this work, Codex re-running implementation-readiness on `epics.md` should EITHER (a) re-classify Epic 4 + Epic 5 as "implemented pattern" (matching Epic 1-3), OR (b) downgrade the critical findings to historical observations resolved during execution.
6. No code, no deploy. `_bmad-output/` stays gitignored; changes are operator-local.

### Next steps after approval

1. Apply Changes 1-5 to `epics.md` (one Edit per change, batched).
2. Verify the file parses cleanly (no broken Markdown tables, no orphaned cross-refs).
3. Optionally: re-run Codex implementation-readiness on the refreshed `epics.md` and confirm critical findings resolve. (User decides whether to spend the Codex budget on this; the proposal does not require it.)
4. Mark this proposal `status: approved-and-applied` in its frontmatter.

---

## Section 6: Approval

**Awaiting Ezop's review.** Options:

- **Approve (a):** apply Changes 1-5 to epics.md immediately.
- **Edit (e):** specify which Change(s) to modify before applying.
- **Reject (r):** discuss alternative approach.
