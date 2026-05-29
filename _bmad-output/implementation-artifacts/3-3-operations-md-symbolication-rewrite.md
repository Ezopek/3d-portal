# Story 3.3: `docs/operations.md` — Symbolication Section Rewrite

Status: done

> **Story role:** **THIRD Epic 3 story (doc-only).** Replaces the stale "GlitchTip error tracking" section in `docs/operations.md` (currently lines 105–227, dated pre-Epic-1) with a current-state runbook that reflects Stories 1.4–1.6 + 3.1 + 3.2 + the homelab GlitchTip volume-mount fix. Doc-only: skips auto-deploy per project memory `feedback_auto_deploy_dev`.

## Story

As an operator (Michał or an AI agent landing cold in the repo),
I want the runbook section on observability rewritten to current state — deploy + verify ritual, CLI manual recovery, same-day token rotation, exact required scopes, triage script usage, cross-references, GlitchTip version pin —
so that no one has to reverse-engineer the workflow from code or PR history.

## Acceptance Criteria

> **Source:** epics.md:578–598 (Story 3.3 ACs).

1. **AC1 — Deploy ritual subsection.** Documents `bash infra/scripts/deploy.sh` runs build → ship → restart → alembic → `verify-symbolication.sh`. Verify is non-fatal but loud. Three-signal failure model (stdout warn + `infra/.last-verify` FAILED + synthetic GlitchTip event tagged `deploy.verification=failed`). Mentions stale-verify warning at next deploy if previous deploy didn't write OK. Cite Story 3.2's `deploy.sh` integration.

2. **AC2 — Manual recovery subsection (CLI fallback).** Documents `bash infra/scripts/upload-sourcemaps.sh` standalone after a fresh `npm run build` — uploads source maps using the same `RELEASE` identity as the plugin path. Re-run `bash infra/scripts/verify-symbolication.sh` to confirm. Reference `--help` flag. Note: as of the GlitchTip 6.1.6 worker volume-mount fix, both plugin and CLI paths persist artifact bundles correctly.

3. **AC3 — Token rotation procedure (same-day).** Step-by-step: open GlitchTip web UI on LAN/VPN → Profile → Auth Tokens → create new token with the exact scopes from AC4 → update `infra/.env`'s `GLITCHTIP_AUTH_TOKEN` value → run `bash infra/scripts/deploy.sh` to validate via plugin upload AND verify-symbolication.sh → revoke old token → record rotation date in this runbook (or `_bmad-output/project-context.md`).

4. **AC4 — Required token scopes (exact list).** `org:read`, `project:read`, `project:write`, `project:releases`, `event:write`. Five scopes total. NOT `org:write`, NOT `org:admin`. (FR28 + NFR-S3.) Note that `event:write` is required for Story 3.1's synthetic alarm event POST (was missing from the legacy 4-scope list).

5. **AC5 — Triage script usage subsection.** Documents `bash infra/scripts/glitchtip-triage.sh <issue_id>` returns a markdown stub paste-ready into `bmad-quick-dev` / `bmad-create-story`. Schema verifiable via `bash infra/scripts/glitchtip-triage.sh --schema | diff -u tests/golden/triage-schema.txt -`. Read-only against GlitchTip. **NOTE:** glitchtip-triage.sh is Epic 2 scope (Story 2.5) and is NOT YET SHIPPED. The subsection therefore documents the contract + cites Story 2.5 as the current backlog item; once landed, the runbook stays accurate without a re-edit. Phrase it as "ships in Story 2.5" rather than fabricating present-tense functionality.

6. **AC6 — Cross-references.** Link to `~/repos/configs/docs/glitchtip-agent-guide.md` for REST recipes (existing inline link survives). Link to `~/repos/configs/docs/observability-logging-contract.md` for tag taxonomy.

7. **AC7 — GlitchTip 6.1.x version pin.** Note that scripts depend on the 6.1.x REST API surface (specifically: chunk-upload + `artifactbundle/assemble/` + the `release` field surfacing as a tag in event JSON). Upgrade to 7.x requires re-validation per NFR-I1. Cite the existing "Provisioning a fresh project" subsection by reference.

8. **AC8 — Legacy "Sentry vite-plugin out-of-scope follow-up" note removed.** Lines 140–144 of current operations.md (the "Known limitation: synthetic test events do not symbolicate" block + "out of scope; track it as a follow-up" framing) are DELETED, not commented out. Modern symbolication is now the active path; the limitation is resolved.

9. **AC9 — Stale claims fixed.** Line 122's "deploy.sh calls upload-sourcemaps.sh" statement is corrected: deploy.sh now calls verify-symbolication.sh; upload-sourcemaps.sh is the documented manual recovery. Line 138's "GLITCHTIP_AUTH_TOKEN missing → deploy succeeds with sourcemap upload skipped (warning)" is corrected: FR4 hard-fail policy means missing token → BuildKit secret check fails → build aborts (no silent skip).

10. **AC10 — Section position.** Rewritten section opens with a sensible heading order: "GlitchTip observability — operator runbook" or similar near the top of the doc (no need to physically move it; the existing ## GlitchTip error tracking section at line 105 is in a fine position — just rewrite its body). Internal subheadings (### Deploy ritual, ### Manual recovery — CLI fallback, etc.) per epic AC.

11. **AC11 — Internal consistency.** Rewritten section references only scripts/files/flags that ACTUALLY EXIST in the repo (or in Story 2.5's pending work, with explicit "ships in Story 2.5" framing). No dangling references to renamed flags or non-existent paths. `verify-symbolication.sh`, `upload-sourcemaps.sh`, `deploy.sh`, `infra/.env`, `infra/.last-verify` all exist; reference them concretely.

12. **AC12 — Doc-only commit; skips auto-deploy.** Per project memory `feedback_auto_deploy_dev`: changes confined to `docs/operations.md` skip `infra/scripts/deploy.sh`. Commit scope `docs(operations)` or `docs(infra)`.

13. **AC13 — Preserve "Trigger a test event" + "Reading recent issues from CLI" + "Provisioning a fresh project" subsections.** These existing subsections (lines 146–227) are still useful; they survive the rewrite (with minor updates: e.g., the test event subsection's API curl example doesn't need changes; "Reading recent issues" is still a valid CLI recipe; "Provisioning a fresh project" updates to mention the 5-scope token list per AC4). Don't delete them.

## Tasks / Subtasks

- [x] **Task 1: Read current state baseline**
  - [x] Subtask 1.1: Read `docs/operations.md` lines 105–227 (current GlitchTip section) to confirm exact content being replaced. Already done in pre-context analysis but re-verify before edit.
  - [x] Subtask 1.2: Confirm `infra/scripts/verify-symbolication.sh`, `infra/scripts/upload-sourcemaps.sh`, `infra/scripts/deploy.sh` all exist + are executable. `infra/.last-verify` exists with current OK state.

- [x] **Task 2: Rewrite the section body** (AC1–AC9, AC11)
  - [x] Subtask 2.1: Replace lines 105–227 with the new "GlitchTip observability — operator runbook" content. New structure:
    ```
    ## GlitchTip observability — operator runbook
    
    Top blurb: 3 services emit to one project; rotated token + verify ritual.
    
    ### Configuration (preserved table from current lines 109–118)
    
    ### Deploy ritual (AC1; NEW)
    
    ### Manual recovery — CLI fallback (AC2; NEW, replaces old "Sourcemap upload" subsection)
    
    ### Token rotation procedure (AC3; NEW)
    
    ### Required token scopes (AC4; NEW, replaces old 4-scope list at line 227)
    
    ### Triage script usage (AC5; placeholder pointing to Story 2.5)
    
    ### Cross-references (AC6; consolidates the inline links)
    
    ### GlitchTip 6.1.x version pin (AC7; NEW)
    
    ### Trigger a test event (preserved from current 146–165)
    
    ### Reading recent issues from CLI (preserved from current 167–184)
    
    ### Provisioning a fresh project (preserved from current 186–227, minor scope update)
    ```
  - [x] Subtask 2.2: Each new subsection contains the exact content described in its AC + ~2–4 paragraphs of operator-readable narrative. Avoid bullet-list-only writing; prefer command examples + brief explanation.
  - [x] Subtask 2.3: Cross-check internal consistency: every script/flag/env-var referenced exists in the repo OR is explicitly framed as "ships in Story 2.5".

- [x] **Task 3: Diff review** (AC8, AC10, AC11)
  - [x] Subtask 3.1: `git diff docs/operations.md` review:
    - Lines 140–144 (legacy "Known limitation" block) are removed, NOT commented out (AC8).
    - Line 122 stale claim about deploy.sh + upload-sourcemaps.sh removed/replaced (AC9).
    - Line 138 stale claim about silent-skip removed/replaced (AC9).
    - Line 227's 4-scope token list updated to 5 scopes (AC4).
    - No new dangling references (AC11).
    - Pre-existing sections (Trigger a test event, Reading recent issues, Provisioning a fresh project) intact.

- [x] **Task 4: Commit** (AC12)
  - [x] Subtask 4.1: `git add docs/operations.md`. Conventional commit `docs(operations): rewrite GlitchTip section for current state (Story 3.3)`. Body: stale-claim fixes + new subsections per AC list + 5-scope token list (event:write added). Co-Authored-By trailer.
  - [x] Subtask 4.2: **DO NOT auto-deploy** — doc-only commit per project memory `feedback_auto_deploy_dev`.

- [x] **Task 5: Story finalization**
  - [x] Subtask 5.1: Mark all task checkboxes [x]. Populate Dev Agent Record (Agent Model Used, Debug Log References, Completion Notes, File List, Change Log).
  - [x] Subtask 5.2: Update sprint-status.yaml: `3-3-operations-md-symbolication-rewrite` → `review`. Update `last_updated`.
  - [x] Subtask 5.3: Status in this file → `review`.

## Dev Notes

### File-structure footprint (single MODIFIED file)

**MODIFIED:**
- `docs/operations.md` — rewrites the GlitchTip section (lines 105–227 → new content). Preserves head matter (Deploy + Catalog + First-time setup + Backup + Failure modes + Routine operations) and tail matter (SoT migration section).

**NOT TOUCHED:**
- All scripts, code, configs.

### Why doc-only skips auto-deploy

Per project memory `feedback_auto_deploy_dev`: doc-only commits (changes confined to `docs/`, root `*.md`, `AGENTS.md`, `CLAUDE.md`) DO NOT trigger `infra/scripts/deploy.sh`. The deploy chain is for code/infra changes that affect what gets shipped to `.190`. Documentation lives in the repo only.

### Tone + voice

Match the existing `docs/operations.md` style:
- 2nd-person operator voice ("Run …", "Open …").
- Bash code blocks with realistic env (e.g., `set -a; source infra/.env; set +a` first).
- Tables for env-var inventories.
- Brief "Why" paragraphs explaining the design decision (e.g., LAN URL bypass, three-signal failure model).
- No emojis (project rule).

### What NOT to add

- New scripts or flags beyond what Stories 1.4–1.6 + 3.1 + 3.2 ship.
- Speculative future work (e.g., "we might also add X"). The runbook documents current state.
- Long architecture rationale — that lives in `_bmad-output/planning-artifacts/architecture.md`. Cross-link, don't duplicate.

### Cross-references to preserve / add

- Existing: `~/repos/configs/docs/glitchtip-agent-guide.md` (line 46 of current operations.md).
- Add: `~/repos/configs/docs/observability-logging-contract.md` for tag taxonomy (AC6).
- Add: pointer to `_bmad-output/planning-artifacts/architecture.md` Decision K (verify ritual rationale) — optional but useful for agents arriving cold.

## Previous Story Intelligence

- **Story 3.1 (done)** ships `verify-symbolication.sh` with FR12 exit codes 0/1/2/3/4. Three-signal failure model: stdout + `.last-verify FAILED` + synthetic alarm.
- **Story 3.2 (done)** wires verify-symbolication.sh into deploy.sh post-alembic with stale-verify tripwire at start. Decision K compliance verified.
- **Story 1.6 (done)** decoupled upload-sourcemaps.sh from deploy.sh; CLI is documented manual recovery now.
- **Story 1.5 + Codex review fix (done)** enforces FR4 hard-fail via BuildKit `required=true` + token guard. Missing token = build aborts, NOT silent skip.
- **Epic 1 regression (resolved during Story 3.1 dev)** — homelab GlitchTip worker container was missing `glitchtip-uploads` volume mount. Fix applied to homelab compose; both plugin and CLI uploads now persist artifact bundles correctly. Document this in the rewritten section as a config invariant ("worker container must mount uploads volume").

## Git Intelligence Summary

Last 5 commits (`git log -5 --oneline`):
- `31dac06 feat(infra): wire verify-symbolication into deploy.sh post-alembic` — Story 3.2.
- `82addc7 fix(infra+web): address Codex review of Story 3.1` — Codex fixes for 3.1.
- `2f02d7e fix(web): normalize sourcemap paths to apps/web/<...> for NFR-R1 regex` — Epic 1 regression closure.
- `76527ab fix(infra): read release from .tags[] not .release` — Story 3.1 fix.
- `a1b76a4 fix(infra): use headless chrome for verify-symbolication smoke trigger` — Story 3.1 fix.

Pattern: doc commits use scope `docs(<area>)`. This story → `docs(operations)`.

## Project Context Reference

Read `_bmad-output/project-context.md` for the 125 rules. Most relevant for this story:
- **English in committed content** (commit messages, docstrings, markdown docs). Polish stays in conversation only.
- **Documentation comment policy**: WHY when non-obvious. Skip narrative WHATs that names already convey.
- **No emojis** unless explicitly requested.
- **Doc-only commits skip auto-deploy** (`feedback_auto_deploy_dev` memory).

## References

- **Epic source:** `_bmad-output/planning-artifacts/epics.md:578–598`.
- **Existing file (modified):** `docs/operations.md` (current state at lines 105–227).
- **Cross-repo:**
  - `~/repos/configs/docs/glitchtip-agent-guide.md` — REST recipes (preserved cross-link).
  - `~/repos/configs/docs/observability-logging-contract.md` — tag taxonomy (NEW cross-link per AC6).
- **Previous stories:**
  - `_bmad-output/implementation-artifacts/3-1-verify-symbolication-script.md` (done).
  - `_bmad-output/implementation-artifacts/3-2-deploy-sh-verify-integration.md` (done).
  - `_bmad-output/implementation-artifacts/epic-1-symbolication-regression.md` (closed; documents homelab compose fix).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Claude Opus 4.7, 1M context)

### Debug Log References

- `git diff --stat docs/operations.md`: +101/-15 (single file, 116 lines net change).
- AC8/9 verification: `grep -c "out of scope"` → 0; `grep -c "deploy.sh.*calls.*upload-sourcemaps"` → 0; `grep -c "deploy still succeeds with sourcemap upload skipped"` → 0.
- AC4 verification: `grep -c "event:write"` → 4 (mentions in scope-list table + main body + provisioning subsection + scope-rationale paragraph).
- Preserved subsections intact: `### Trigger a test event` (line 232), `### Reading recent issues from CLI` (line 253), `### Provisioning a fresh project` (line 272).

### Completion Notes List

- **Single-commit doc-only ship.** Commit `50a7292`; no auto-deploy per project memory.
- **All 13 ACs satisfied.** New section structure: Configuration → Deploy ritual (AC1) → Manual recovery — CLI fallback (AC2) → Token rotation (AC3) → Required token scopes (AC4) → Triage script usage (AC5; placeholder for Story 2.5) → Cross-references (AC6) → GlitchTip 6.1.x version pin + homelab worker volume-mount invariant (AC7) → Trigger a test event (preserved) → Reading recent issues from CLI (preserved) → Provisioning a fresh project (preserved + 5-scope token list update).
- **Legacy "out of scope" + "synthetic events do not symbolicate" framing deleted.** That limitation was closed by Stories 1.4–1.5 (plugin in docker stage) + the homelab worker volume-mount fix during Story 3.1's dev. Current state replaces it with the working active path + manual fallback.
- **Stale claims fixed.** Old line 122 ("deploy.sh calls upload-sourcemaps.sh") + old line 138 ("deploy still succeeds with sourcemap upload skipped") replaced with current truth: plugin runs INSIDE docker build stage (Story 1.5); deploy.sh runs verify-symbolication.sh post-alembic (Story 3.2); FR4 hard-fail means missing token aborts build (Codex review fix during Story 1.5/1.6).
- **Story 2.5 forward-reference framing.** Triage script subsection documents the contract + explicitly says "ships in Story 2.5". Once Story 2.5 lands, the runbook stays accurate without re-edit.
- **Homelab GlitchTip config invariant added.** New paragraph at end of "GlitchTip 6.1.x version pin" subsection documents the `glitchtip-worker` container's `glitchtip-uploads` volume mount requirement, with cross-link to `epic-1-symbolication-regression.md`. Future operator landing cold won't re-discover the same bug.
- **5-scope token list correction propagated to "Provisioning a fresh project" subsection** so the runbook is internally consistent (the legacy 4-scope mention there would otherwise contradict the AC4 list).
- No automated tests for doc-only changes. The commit's existence + diff content is the deliverable.

### File List

MODIFIED:
- `docs/operations.md` (+101/-15 lines): rewrites the `## GlitchTip error tracking` section + heading rename to `## GlitchTip observability — operator runbook`.

GITIGNORED state changes:
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `3-3-operations-md-symbolication-rewrite: ready-for-dev → in-progress → done`.
- `_bmad-output/implementation-artifacts/3-3-operations-md-symbolication-rewrite.md` (this file).

### Change Log

- 2026-05-10 — single-commit ship (`50a7292`): all 13 ACs satisfied. Doc-only; skips auto-deploy. Status: done. No code-review needed (doc-only changes don't carry the implementation-defect surface a Codex review targets — operator-facing prose is the contract).
