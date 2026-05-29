# Story 9.4: Audit report authoring + gate-condition sign-off

Status: review

> **Story role:** FOURTH and FINAL Epic 9 story — renders the **audit report artifact** that consolidates Stories 9.1-9.3 outputs into a single operator-readable + auditable markdown document, and **renders the gate-condition decision line** that either unblocks Epic 10 (PASS) or triggers a fix sprint (FAIL). The decision is structural — there is no procedural override. Depends on 9.1 + 9.2 + 9.3 complete.

## Story

As the ITCM running the **HARD GATE security audit blocking E10 cutover**,
I want **a single operator-facing audit report committed to `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` (gitignored) that renders the Tools run summary (from 9.1), Six-scenario coverage table (from 9.2), Findings disposition table (from 9.3 + 9.1/9.2 inputs), Methodology section (citing the self-attestation rationale from 9.3), AND an explicit gate-condition decision line as either `**E10 cleared to proceed**` (PASS) or `**E10 blocked, fix sprint required**` (FAIL)**,
so that **the NFR5-SEC-1 gate condition is rendered structurally — no ambiguity, no manual override path**.

The report's format mirrors Init 1's `verify-symbolication.sh` precedent + Story 7.6's `2fa-recovery-drill-2026-05-20.md` precedent for operator familiarity (artifact-shape consistency across Init 0/1/5).

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §452-464.

### AC1 — Audit report file structure

File: `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` (gitignored). Sections (in order):

1. **Title + Date + Auditor**: `# Security Audit — Initiative 5 / Epic 9 — YYYY-MM-DD` + `**Auditor:** Ezop (single-operator self-attestation, codex countersignature per Medium disposition per NFR5-SEC-2)` + `**Subject:** 3d-portal Initiative 5 deliverables (Epics 6 + 7 + 8) deployed at https://3d.ezop.ddns.net`.

2. **Methodology**: cites the tooling stack from 9.1 (bandit / semgrep / pip-audit / npm audit / OWASP ZAP), the six-scenario matrix from 9.2, the codex countersignature pattern from 9.3 (referencing `audit-raw/YYYY-MM-DD/self-attestation-rationale.md`), and the single-operator self-attestation mitigation explicitly.

3. **Tools run summary** (table):
   | Tool | Target | Output | Critical | High | Medium | Low/Info |
   |------|--------|--------|----------|------|--------|----------|
   | bandit | apps/api+workers/render | audit-raw/.../bandit-*.txt | 0 | 0 | N | M |
   | semgrep | apps/api+apps/web+workers/render | audit-raw/.../semgrep.json | 0 | 0 | N | M |
   | pip-audit | apps/api+workers/render | audit-raw/.../pip-audit-*.txt | 0 | 0 | N | M |
   | npm audit | apps/web | audit-raw/.../npm-audit.json | 0 | 0 | N | M |
   | OWASP ZAP baseline | https://3d.ezop.ddns.net | audit-raw/.../zap-baseline.html | 0 | 0 | N | M |

4. **Six-scenario coverage** (table, from 9.2 `six-scenario-coverage.json`):
   | # | Scenario | Verdict | Evidence | Reproducer |
   |---|----------|---------|----------|------------|
   | 1 | Invite-token brute force | PASS | scenario-1-output.txt | scenario-1-*.sh |
   | 2 | Refresh-token replay | PASS | scenario-2-output.txt | scenario-2-*.sh |
   | 3 | CSRF + JWT tampering | PASS | scenario-3-results.txt | scenario-3-*.sh |
   | 4 | IDOR scan `/api/admin/*` | PASS | scenario-4-results.txt | scenario-4-*.sh |
   | 5 | Login rate-limit | PASS | scenario-5-output.txt | scenario-5-*.sh |
   | 6 | Member share-link amplification | PASS | scenario-6-output.txt | scenario-6-*.sh |

5. **Findings disposition** (table, from 9.3 `medium-findings.json`):
   | ID | Source | Severity | Title | Disposition | Patch SHA / Codex SHA | Countersigned |
   |----|--------|----------|-------|-------------|----------------------|---------------|
   | med-001 | bandit | Medium | ... | fixed | <patch_sha> / <codex_sha> | YYYY-MM-DD |
   | med-002 | scenario-3 | Medium | ... | mitigated | (n/a) / <codex_sha> | YYYY-MM-DD |
   | med-003 | semgrep | Medium | ... | accepted-with-rationale | (n/a) / <codex_sha> | YYYY-MM-DD |

   Each Medium row also cites the rationale (one-line summary; full text in 9.3's per-finding codex review output file).

6. **Gate-condition decision line**: ONE of the following two verbatim lines:

   **PASS** (NFR5-SEC-1 gate condition met):
   ```
   **E10 cleared to proceed** — gate condition PASS: zero open Critical/High findings; N accepted-rationale Mediums (N ≤ 3); audit complete on YYYY-MM-DD.
   ```

   **FAIL** (gate condition unmet):
   ```
   **E10 blocked, fix sprint required** — gate condition FAIL: <reason: M open Criticals OR P open Highs OR Q accepted-rationale Mediums (Q ≥ 4)>; triaging the following findings: <list of finding IDs>; audit reruns after fix sprint.
   ```

7. **Re-run reproducer** (one-line cite): `bash audit-raw/YYYY-MM-DD/reproducers.sh all` reruns the full audit from the same git HEAD.

### AC2 — On PASS: E10 unblock signal

The audit report's gate-condition PASS line IS the unblock signal — there is no separate flag-flip in sprint-status.yaml or anywhere else. Story 10.1 dev session reads the audit report; if it sees the PASS line, it proceeds. If the audit report doesn't exist, or contains FAIL, Story 10.1 STOPS.

**Done-When:** the report file exists on disk AND contains the PASS line verbatim.

### AC3 — On FAIL: fix-sprint triage via bmad-correct-course

The FAIL line cites the failing findings explicitly. Per epics §463 verbatim:
> "the failing findings are triaged into a fix sprint (likely new E9.x or carry-over E9.x stories created via CC re-invocation per AGENTS.md vanilla-first subsection — NOT a procedural drift; CC is canonical for post-ship scope change including 'this audit failed, what now')"

The dev agent invokes `bmad-correct-course` (or its inline equivalent) to author the fix-sprint stories. Audit reruns AFTER the fix sprint closes — Story 9.4 is NOT considered done until a PASS decision is signed off.

### AC4 — Artifact gitignored

Per `feedback_local_only_docs.md` + epics §464 verbatim ("artifact committed to local `_bmad-output/` only (gitignored)"), the audit report lives ONLY at `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` — NOT committed to git. The corresponding sprint-status entry (`9-4-audit-report-gate-condition-signoff: done`) IS committed (sprint-status is the only persistent index).

### AC5 — Reproducibility window

The audit report is valid for **30 days** OR until next significant deploy (whichever first). After expiry, Story 9.4 must be re-invoked (E9 reopens). This window is a soft convention, not enforced by tooling — documented in the report's Methodology section.

## Files

### Created

- `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` — AC1 (gitignored).

### Modified

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flip `9-4-audit-report-gate-condition-signoff: backlog` → `ready-for-dev` → `done` (the audit-result note in the comment is what records the PASS/FAIL decision in version-controlled state). Also: on PASS, flip `epic-9: in-progress` → `done` AND `epic-10: backlog` → `in-progress` (unblock E10).

### Untouched

- No backend changes, no frontend changes, no infra/scripts changes — pure artifact authoring.

## Tasks

- [x] T1 — Read all inputs
- [x] T2 — Compose the report
- [x] T3 — Render gate-condition decision
- [x] T4 — Sign off
- [x] T5 — Commit + push (sprint-status only — audit report is gitignored)
- [x] T6 — Deploy (skipped — `_bmad-output/` gitignored, no deploy impact)

### T1 — Read all inputs

1. Story 9.1: `audit-raw/YYYY-MM-DD/tool-versions.txt`, `bandit-*.txt`, `semgrep.json`, `pip-audit-*.txt`, `npm-audit.json`, `zap-baseline.{html,json}`.
2. Story 9.2: `audit-raw/YYYY-MM-DD/six-scenario-coverage.json`, all six `scenario-N-*.sh` + output files.
3. Story 9.3: `audit-raw/YYYY-MM-DD/medium-findings.json`, `self-attestation-rationale.md`, `codex-reviews/*.md`.

### T2 — Compose the report

Apply the AC1 section layout. Use markdown tables (NOT HTML). Each table row cites the underlying gitignored evidence path.

### T3 — Render gate-condition decision

1. Parse Critical/High counts from Tools run summary (T2 tables). If ZERO across all rows: candidate-PASS.
2. Parse `accepted-with-rationale` count from Findings disposition table. If ≤3 AND candidate-PASS: render PASS line.
3. If any Critical/High > 0 OR `accepted-with-rationale` > 3: render FAIL line + enumerate the failing finding IDs.

### T4 — Sign off

1. Verify: `grep -F "E10 cleared to proceed" security-audit-*.md` returns a line (PASS) OR `grep -F "E10 blocked" security-audit-*.md` returns a line (FAIL). Exactly one of these.
2. If PASS: edit `sprint-status.yaml`:
   - `epic-9: in-progress` → `done`
   - `9-4-audit-report-gate-condition-signoff: ready-for-dev` → `done` with PASS note + date
   - `epic-10: backlog` → `in-progress`
3. If FAIL: invoke bmad-correct-course (or inline equivalent) per AC3.

### T5 — Commit + push (sprint-status only — audit report is gitignored)

1. Commit `chore(audit): Epic 9 security audit signed off (Story 9.4 — PASS|FAIL)`. Body: cites the audit-report-relative-path (`_bmad-output/...`) + the verbatim gate-condition decision line + Medium counts.
2. Branch: `chore/E9.4-audit-signoff`.
3. Post-merge codex review: optional — codex already countersigned per Medium in 9.3.

### T6 — Deploy

Skip — `_bmad-output/` is gitignored, no deploy impact.

## Test Plan

The Story 9.4 deliverable is an artifact + a state-machine flip. Test plan:
- The audit report file exists and contains all six AC1 sections.
- Exactly one of the two AC1.6 gate-condition decision lines is present.
- On PASS: `sprint-status.yaml` has `epic-10: in-progress`. On FAIL: a CC re-invocation log exists.

## Dev Notes

### What if a finding can't be classified

If a Story 9.1 or 9.2 output produces a finding the dev session can't confidently classify Critical/High/Medium/Low — escalate to operator. Don't downgrade to keep the gate-PASS path open; the gate fails-closed by design.

### What if Story 9.3's codex countersignature is incomplete

If Story 9.3 was interrupted (e.g., codex budget exhausted before all Mediums countersigned) — the audit report renders FAIL with reason "incomplete countersignature per NFR5-SEC-2". Re-run Story 9.3, then re-author the audit report.

### Why the gate-condition decision line is verbatim

The two PASS/FAIL lines (AC1.6) are quoted directly from epics §461. Future audits (Init 6+) reuse the same format for cross-audit comparability. Do NOT improvise wording.

### Convention cross-references

- Artifact-format precedent: Story 3.1 `verify-symbolication.sh` runbook artifact + Story 7.6 `2fa-recovery-drill-2026-05-20.md` (operator-readable single-file markdown with table sections + decision line).
- Gate-state machine precedent: NONE — this is the first HARD GATE in this repo. Subsequent initiatives may adopt the same pattern.
- Gitignored-artifact precedent: ALL Init 5 retrospectives + `audit-raw/*` (per `_bmad-output/` root gitignore).

## Dev Agent Record

### Implementation notes (Sesja AZ — 2026-05-20)

**T1 — Inputs consolidated.** Read tool-versions.txt (bandit 1.9.4 / semgrep 1.163.0 / pip-audit 2.10.0 / npm 10.9.7 / node v22.22.2 / zaproxy 2.17.0; git HEAD `9a8b935` at scan). Parsed bandit (apps/api: 0/0/0/11, workers/render: 0/0/0/0), semgrep (9 results), pip-audit (4 advisories, deduped — shared `uv.lock`), npm-audit (7 moderates), ZAP baseline (3 Medium + 7 Low + 4 Info via JSON `riskcode` enumeration). Loaded `six-scenario-coverage-attempt-8.json` (final attempt, all six PASS) + `medium-findings.json` (23 Mediums, 23/23 mitigated, 0 fixed, 0 accepted-with-rationale) + `self-attestation-rationale.md` (binding language for Methodology section).

**T2 — Audit report authored.** Wrote `_bmad-output/implementation-artifacts/security-audit-2026-05-20.md` (~190 lines, 6 AC1 sections + reproducer cite). Sections rendered in spec order: Title + Date + Auditor + Subject + git HEAD + window-expiry header → §1 Methodology (tooling stack + six-scenario matrix + codex countersignature + self-attestation mitigation + reproducibility window) → §2 Tools run summary (7-row markdown table with absolute output paths) → §3 Six-scenario coverage (6-row table + per-scenario notes from JSON) → §4 Findings disposition (24-row table = 1 fixed-pre-gate High `high-001` + 23 mitigated Mediums `med-001..023`; mitigation rationale summary grouped by category) → §5 Gate-condition decision (verbatim PASS line) → §6 Re-run reproducer (one-line cite). Footer carries sprint-status flip summary.

Format follows AC1 verbatim (markdown tables, not HTML). Each table row cites its underlying gitignored evidence path. The fixed High finding (`high-001`) is included with `disposition=fixed`, `patch_sha=7c148cb` to satisfy NFR5-SEC-1 "zero OPEN Critical/High" semantics — Story 9.2 surfaced it; Story 9.2 close-out fixed it pre-gate.

**T3 — Gate-condition rendered PASS.** Per T3 algorithm:
1. Critical/High count across Tools run summary = 0 across all 7 rows → candidate-PASS.
2. `accepted-with-rationale` count from Findings disposition = 0 ≤ 3 → PASS line eligible.
3. Verbatim AC1.6 PASS line rendered: `**E10 cleared to proceed** — gate condition PASS: zero open Critical/High findings; 0 accepted-rationale Mediums (0 ≤ 3); audit complete on 2026-05-20.`

Mutex check: `grep -F "E10 cleared to proceed" security-audit-2026-05-20.md` returns 1 match; `grep -F "E10 blocked" security-audit-2026-05-20.md` returns 0 matches — exactly one of the two AC1.6 decision lines is present.

**T4 — Sprint-status sign-off.** Updated `_bmad-output/implementation-artifacts/sprint-status.yaml`:
- `epic-9: in-progress` → `done` (with verbatim PASS line + audit-window cite)
- `9-4-audit-report-gate-condition-signoff: ready-for-dev` → `done` (Sesja AZ close-out note)
- `epic-10: backlog` → `in-progress` (HARD GATE unblocked — first story 10.1 next)
- `last_updated` note prepended with Sesja AZ summary

`bmad-correct-course` was NOT invoked (PASS path — AC3 fix-sprint triage only applies on FAIL).

**T5 — Commit.** Created branch `chore/E9.4-audit-signoff` from `main`. Committed `sprint-status.yaml` only — the audit report itself (`security-audit-2026-05-20.md`) is gitignored under `_bmad-output/` per AC4 + `feedback_local_only_docs.md`. Commit message cites audit-report-relative-path + verbatim gate-condition decision line + Medium counts per spec T5.1.

**T6 — Deploy.** Skipped per spec — `_bmad-output/` is gitignored; sprint-status change is a doc-class commit with no runtime impact. `feedback_auto_deploy_dev.md` carve-out for "doc-only commits skipped" applies.

### Debug Log

- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/` had 8 `six-scenario-coverage-attempt-N.json` snapshots — final attempt-8 selected per Story 9.2 close-out convention (last attempt is canonical, prior attempts retained for forensics).
- ZAP `zap-baseline.json` `alerts[]` array parsed via Python; `riskcode` enum mapped to Critical=4 / High=3 / Medium=2 / Low=1 / Info=0 → 3 Mediums + 7 Lows + 4 Info confirms `medium-findings.json` 3-Medium count for ZAP.
- semgrep result-set: 2 `ERROR` + 7 `WARNING` severity → all 9 entries map to Medium per Story 9.3 disposition catalogue (severity-to-disposition mapping was set in 9.3, not re-derived here).
- pip-audit advisory count: 4 unique CVEs (idna 3.13, urllib3 2.6.3 ×2, pyjwt 2.12.1) appear in both apps/api and workers/render pip-audit outputs because both services share `apps/api/uv.lock` (workers/render imports the same Fernet/PyJWT/httpx stack). Tools run summary renders them per-target (4 + 4) without double-counting in Findings disposition (deduped to med-010..013).
- No HALT conditions encountered. No regressions to verify (no code change). No tests to run (no code change). No type-check / lint to run (no code change).

### Completion notes

- AC1 (report file structure): ✅ all 6 sections present in spec order with absolute evidence-path cites.
- AC2 (PASS = unblock signal): ✅ structural gate cleared via verbatim PASS line — no separate flag-flip needed; Story 10.1 will read the report and proceed.
- AC3 (FAIL → bmad-correct-course): N/A — gate cleared PASS.
- AC4 (artifact gitignored): ✅ written under `_bmad-output/implementation-artifacts/` which is covered by root `.gitignore` line 65 (`_bmad-output/`). `git status` confirms no tracking attempt.
- AC5 (30-day reproducibility window): ✅ documented in Methodology + footer; expiry 2026-06-19.

## File List

### Created
- `_bmad-output/implementation-artifacts/security-audit-2026-05-20.md` — Epic 9 HARD GATE audit report (gitignored).

### Modified
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — flipped `epic-9` (in-progress → done), `9-4-audit-report-gate-condition-signoff` (ready-for-dev → done), `epic-10` (backlog → in-progress); refreshed `last_updated` with Sesja AZ note.
- `_bmad-output/implementation-artifacts/9-4-audit-report-gate-condition-signoff.md` (this file) — Status backlog → review; added Tasks checkboxes + Dev Agent Record + File List + Change Log.

### Untouched (per spec)
- No backend / frontend / infra / scripts changes.

## Change Log

| Date | Change | Sesja |
|------|--------|-------|
| 2026-05-20 | Audit report `security-audit-2026-05-20.md` rendered; gate-condition PASS; sprint-status sign-off flips landed (E9 done, 9.4 done, E10 in-progress) | AZ |
