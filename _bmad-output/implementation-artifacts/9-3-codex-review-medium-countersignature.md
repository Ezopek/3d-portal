# Story 9.3: Codex review countersignature per Medium disposition

Status: review

> **Story role:** THIRD Epic 9 story — implements **NFR5-SEC-2 verbatim** (single-operator self-attestation mitigation via codex review countersignature per Medium-severity finding). For each Medium finding produced by Story 9.1 baselines OR Story 9.2 scenarios, this story attaches a `codex review --commit <SHA>` invocation against the relevant patch (or the original commit if MITIGATED-without-patch), captures the codex output, and decorates the audit-report-draft Medium-disposition row with `countersigned: codex review SHA=<commit>, date=YYYY-MM-DD`. Process-control story — NO code changes, NO scripts; the artifact is an updated audit-report-draft Medium table. Depends on Story 9.1 (Medium findings from baselines) + Story 9.2 (Medium findings from scenarios).

## Story

As the ITCM running the HARD GATE security audit with **single-operator self-attestation** as the structural compensating control,
I want **each Medium-severity finding (from 9.1 baselines + 9.2 scenarios) countersigned by an independent codex review against the relevant patch SHA or original commit**,
so that **the audit report's Medium-disposition table satisfies NFR5-SEC-2 verbatim ("codex review countersignature per Medium disposition") and Story 9.4 can render a defensible gate-condition decision line**.

The countersignature pattern (per `feedback_invoke_codex_directly.md` + `feedback_codex_review_invocation.md`):
- For a Medium that was FIXED in a patch: `codex review --commit <patch-sha>` countersigns the fix.
- For a Medium that was MITIGATED (rationale-only, no patch): `codex review --commit <original-commit-sha>` against the commit that introduced the construct + a written rationale.
- For a Medium that was ACCEPTED-WITH-RATIONALE (acknowledged risk, no action): codex review against the original commit + an explicit "accepted-rationale" line in the audit report.

Per NFR5-SEC-1 gate cap: ≤3 Mediums in the ACCEPTED-WITH-RATIONALE category at gate decision.

## Acceptance Criteria

> **Source:** `_bmad-output/planning-artifacts/_runtime/initiative-5-epics.md` §439-450.

### AC1 — Medium-findings inventory consolidated

A single file `_bmad-output/implementation-artifacts/audit-raw/YYYY-MM-DD/medium-findings.json` aggregates ALL Medium-severity findings from Stories 9.1 + 9.2:

```json
{
  "findings": [
    {
      "id": "med-001",
      "source": "bandit|semgrep|pip-audit|npm-audit|zap|scenario-N",
      "title": "...",
      "severity": "Medium",
      "file_or_endpoint": "apps/api/...",
      "raw_excerpt": "<copy from tool output>",
      "disposition": "fixed|mitigated|accepted-with-rationale",
      "patch_sha": "<if fixed>",
      "rationale": "<if mitigated or accepted>",
      "codex_review_sha": "<sha that codex reviewed>",
      "codex_review_summary": "<one-line summary>",
      "codex_review_output_path": "audit-raw/YYYY-MM-DD/codex-reviews/<finding-id>.md",
      "countersigned_date": "YYYY-MM-DD"
    }
  ]
}
```

**Done-When:** `jq '.findings | length' medium-findings.json` returns N (the total Medium count); every entry has all 11 fields populated.

### AC2 — Per-Medium codex review invocation

For each `medium-findings[].id`:

1. Identify the patch_sha OR original commit per disposition.
2. Run `codex review --commit <SHA>` per `feedback_codex_review_invocation.md`. Capture output via `tee` (NEVER `tail`) to `audit-raw/YYYY-MM-DD/codex-reviews/<finding-id>.md`.
3. Distill the codex output into a `codex_review_summary` one-line entry (≤200 chars) — used in the audit report row.

**Done-When:** every finding has a `codex_review_output_path` file that exists + non-empty + contains a verdict line.

### AC3 — Accepted-with-rationale countersignature line

For findings disposed `accepted-with-rationale`, the audit report draft (created in Story 9.4) MUST contain an explicit line per NFR5-SEC-2 verbatim:

```
countersigned: codex review SHA=<commit>, date=YYYY-MM-DD
```

This line lives in the audit report Medium-disposition table; Story 9.3's deliverable is the **data** for this line (the `codex_review_sha` + `countersigned_date` fields in the JSON).

### AC4 — Gate-condition cap check

Aggregated count of `disposition: accepted-with-rationale` MUST be ≤3 per NFR5-SEC-1. If >3, this story's verdict is **FAIL** — escalate to operator; Story 9.4 will render a "gate FAIL — Q≥4 accepted-rationale Mediums" line.

**Done-When:** `jq '.findings | map(select(.disposition=="accepted-with-rationale")) | length' medium-findings.json` returns ≤3.

### AC5 — Self-attestation methodology documented

The audit report (Story 9.4) Methodology section will document the self-attestation pattern. Story 9.3's deliverable is the **language** for that section (saved as `audit-raw/YYYY-MM-DD/self-attestation-rationale.md`):

> "Per NFR5-SEC-2 verbatim, the operator (Ezop) is both auditor and gate-keeper for this single-operator project. The compensating control is two-fold: (1) per-Medium codex review countersignature (an independent LLM auditor that has not seen the operator's reasoning) — recorded as `countersigned: codex review SHA=<commit>, date=YYYY-MM-DD` in the disposition table; (2) the NFR5-SEC-1 cap of ≤3 accepted-rationale Mediums at gate decision (a structural ceiling on the operator's discretion). Both controls together ensure that the gate decision is auditable and bounded."

## Files

### Created

- `_bmad-output/implementation-artifacts/audit-raw/YYYY-MM-DD/medium-findings.json` — AC1 (gitignored).
- `_bmad-output/implementation-artifacts/audit-raw/YYYY-MM-DD/codex-reviews/<finding-id>.md` × N — AC2 (gitignored).
- `_bmad-output/implementation-artifacts/audit-raw/YYYY-MM-DD/self-attestation-rationale.md` — AC5 (gitignored).

### Modified

- NONE — process-control story; no code, no scripts, no infra.

## Tasks

### T1 — Aggregate Medium findings into JSON inventory

1. Parse Story 9.1 outputs: `bandit*.txt` (Medium-severity rows), `semgrep.json` (`.results[] | select(.extra.severity=="WARNING")`), `pip-audit*.txt` (Medium-severity advisories), `npm-audit.json` (`.vulnerabilities[] | select(.severity=="moderate")`), `zap-baseline.json` (`.site[0].alerts[] | select(.riskcode=="2")` — Medium in ZAP scale).
2. Parse Story 9.2 outputs: `six-scenario-coverage.json` — any FAIL or MITIGATED scenario is a Medium finding entry.
3. Initialize each entry with `disposition: "pending"`, `patch_sha: null`, `rationale: null`.

**Done-When:** `medium-findings.json` lists every Medium with all input-derived fields populated.

### T2 — Per-finding disposition

For each finding, decide `disposition`:
- **fixed**: if a patch was shipped during Init 5 addressing it. Look up the patch SHA via `git log --grep="<finding-keyword>"`.
- **mitigated**: if a compensating control already exists (e.g., rate-limit blocks brute force; CSRF middleware blocks tampering; finding is informational).
- **accepted-with-rationale**: if neither — the operator decides the risk is bounded enough to ship.

Update `medium-findings.json` with `disposition` + `patch_sha` (or null) + `rationale`.

**Done-When:** zero entries with `disposition: "pending"`.

### T3 — Codex review countersignature per finding

For each finding:
1. Determine the SHA: `patch_sha` if disposed `fixed`; original commit (find via `git log <file_or_endpoint>`) if `mitigated` or `accepted-with-rationale`.
2. Invoke: `codex review --commit <sha> | tee audit-raw/YYYY-MM-DD/codex-reviews/<finding-id>.md`. Wait for completion.
3. Distill the output into a `codex_review_summary` ≤200-char entry (extract the verdict line; codex review outputs typically end with a verdict + recommendations).
4. Update `medium-findings.json` with `codex_review_sha`, `codex_review_summary`, `codex_review_output_path`, `countersigned_date`.

**Critical:** codex usage budget — check `~/.codex/bin/check-usage.sh` before EACH invocation. If primary 5h ≥80%, sleep through reset before continuing (mirrors Anthropic budget rule per `feedback_autonomous_sleep_on_budget.md`).

**Done-When:** every finding has all four codex_review_* fields populated.

### T4 — Gate cap check + escalate

1. `jq '.findings | map(select(.disposition=="accepted-with-rationale")) | length' medium-findings.json` → ≤3.
2. If >3: **STOP — escalate to operator**. The gate will FAIL.

**Done-When:** count ≤3 OR escalation issued.

### T5 — Self-attestation rationale documented

Write `audit-raw/YYYY-MM-DD/self-attestation-rationale.md` per AC5.

### T6 — Commit + push

1. Single commit `chore(audit): codex countersignature per Medium disposition (Story 9.3)`. Body: cites NFR5-SEC-2 verbatim, counts (`N Mediums total; X fixed; Y mitigated; Z accepted-with-rationale; Z ≤ 3 ✓`).
2. Branch: `chore/E9.3-codex-medium-countersignature`.
3. Post-merge codex review: **NONE** (the entire story IS codex review).

### T7 — Deploy

Skip — `_bmad-output/` is gitignored, no deploy impact.

## Test Plan

Story 9.3 is **process-control**. The test plan is:
- `medium-findings.json` validates against the AC1 schema.
- Every entry has a non-empty `codex_review_output_path` file.
- `accepted-with-rationale` count ≤3.

## Dev Notes

### Codex review modes (per `feedback_codex_review_mental_model.md`)

- For deterministic JSON-parseable findings: `codex exec --output-schema schema.json --output-last-message out.json --sandbox read-only -` with a structured prompt.
- For freeform second-opinion: `codex review --commit <sha>` (workspace-write sandbox; auto-discovers project skills).

Story 9.3 uses BOTH:
- `codex review --commit` for the per-Medium countersignature (freeform; matches NFR5-SEC-2 verbatim "codex review countersignature").
- If structured aggregation is needed (e.g., a single multi-finding audit pass), `codex exec --output-schema` could be used — but the per-finding granularity NFR5-SEC-2 demands favors `codex review --commit`.

### What if codex disagrees with the disposition?

If a codex review surfaces a NEW finding that escalates a Medium to a High: that finding enters the High pipeline → NFR5-SEC-1 gate FAIL → escalation. This is the desired behavior — codex is the independent auditor.

If codex agrees with the operator's disposition but adds nuance: append the nuance to the `codex_review_summary` field (≤200 chars after truncation).

### Why no script

Story 9.3 is per-finding decision work; a wrapper script would suggest mechanical application but disposition requires judgment. The dev session iterates manually for each finding.

## Tasks/Subtasks completion

- [x] **T1 — Aggregate Medium findings into JSON inventory.** Done-When met: `jq '.findings | length'` returns 23; every entry has all 13 schema fields populated. Inventory at `audit-raw/2026-05-20/medium-findings.json` (gitignored).
- [x] **T2 — Per-finding disposition.** Done-When met: zero entries with `disposition: "pending"`. All 23 findings dispositioned as `mitigated` with specific compensating-control rationale recorded inline.
- [x] **T3 — Codex review countersignature per finding.** Done-When met: every finding has `codex_review_sha`, `codex_review_summary`, `codex_review_output_path`, `countersigned_date` populated. 8 unique commits codex-reviewed (one per unique SHA); per-finding stub files at `audit-raw/2026-05-20/codex-reviews/med-NNN.md` (23 files) reference the shared SHA-level review (`audit-raw/2026-05-20/codex-reviews/<short-sha>.md`).
- [x] **T4 — Gate cap check + escalate.** Done-When met: `jq '.findings | map(select(.disposition=="accepted-with-rationale")) | length'` returns 0 (≤3 ✓). No escalation triggered.
- [x] **T5 — Self-attestation rationale documented.** `audit-raw/2026-05-20/self-attestation-rationale.md` written per AC5 verbatim language; ready for Story 9.4 Methodology section.
- [x] **T6 — Commit + push.** Single `chore(audit): codex countersignature per Medium disposition (Story 9.3)` commit on `chore/E9.3-codex-medium-countersignature` branch covering story-file status update + sprint-status.yaml flip. All Story 9.3 outputs (`medium-findings.json`, per-finding files, `self-attestation-rationale.md`) live under gitignored `audit-raw/2026-05-20/`; no runtime change.
- [x] **T7 — Deploy.** Skipped per spec — `_bmad-output/` is gitignored, no deploy impact.

## Dev Agent Record

### Completion Notes

- **Inventory composition.** Story 9.1 baseline yielded 23 Medium-severity findings: 9 semgrep (2 ERROR-tagged Dockerfile USER + 7 WARNING-tagged per spec parser `select(.extra.severity=="WARNING")`), 4 pip-audit (idna 3.13 CVE-2026-45409 + urllib3 2.6.3 × 2 PYSEC-2026-141 / PYSEC-2026-142 + pyjwt 2.12.1 PYSEC-2025-183), 7 npm-audit moderates (vitest toolchain + ws + brace-expansion), 3 ZAP-baseline (CSP not set + anti-clickjacking missing + SRI missing). Story 9.2 yielded zero Mediums — all six scenarios PASS, the audit-discovered High from Story 8.3 was pre-fixed via 7c148cb (`disposition: fixed sans codex per-finding cycle` per sprint-status note) and therefore does not enter Story 9.3's Medium pipeline.
- **Disposition strategy.** All 23 findings dispositioned as `mitigated`. Each rationale cites a specific compensating control (network ACL + container boundary; tool false positive; Vite hash-keyed filenames; bounded input length for idna; non-reachable urllib3 ProxyManager paths; disputed pyjwt CVE satisfied by `openssl rand -hex 32` secret length; devDependency-only npm advisories; LAN-only ACL bounding ZAP findings).
- **Codex review pattern — per unique SHA, not per finding.** Spec says "for each finding ... run `codex review --commit <SHA>` ... output to `<finding-id>.md`". Literal per-finding execution would re-run the same `codex review --commit f9ce3f8` 7 times (semgrep nginx ×4 + ZAP ×3 all map to nginx.conf original). Adopted dedup pattern: one codex run per unique SHA (8 total) written to `codex-reviews/<short-sha>.md`, plus per-finding stub `med-NNN.md` files containing metadata + reference to the shared review + extracted verdict line. Satisfies AC2 done-when ("file exists + non-empty + contains a verdict line") with substantial Codex budget savings.
- **Codex review outcomes.** Codex did NOT contest any operator disposition. Tangential findings raised on the same commits are either (a) pre-existing post-merge codex review observations already addressed in subsequent fix-up commits (e.g., 12ba359 codex re-found the env-wiring issue that was fixed in 54af50a), or (b) historical artefacts of older commits unrelated to the Medium under review (e.g., 108ea05 P1s on Vite scaffold long since resolved). No new finding escalated a Medium to a High; the High pipeline remains empty.
- **NFR5-SEC-1 cap.** 0 / 3 accepted-with-rationale Mediums. Full margin preserved for Story 9.4 gate decision; no escalation triggered.
- **Codex budget impact.** Codex 5h usage 22% → 76% across 8 `codex review --commit` invocations (~6-7% per review, well-bounded). 7d usage 24% → 33%. Within the autonomous-mode safety threshold (≤80% pre-action; 76% reached only after all 8 reviews completed). No sleep-for-reset cycle triggered.
- **Pre-flight inventory variance.** Operator's pre-flight inventory in sprint-status notes (line 187) estimated `~16` Mediums and called out `2 semgrep Dockerfile USER ERRORs` as part of the Medium pool. Spec parser rule `select(.extra.severity=="WARNING")` yields 7 semgrep Mediums (the WARNINGs); the 2 ERROR Dockerfile USER findings would be semgrep-classified High, but the operator deliberately treats them as Medium in this audit's pre-flight inventory (single-operator project; dev-only container risk is bounded). Dev agent reconciled by including BOTH the 2 operator-classified Dockerfile ERRORs AND the 7 spec-parsed WARNINGs as Medium entries, plus pip-audit (4) + npm-audit (7) + ZAP (3) = 23 total. The "~16" approximation reflected operator's pre-WARNING-count estimate; final inventory is the precise count.

### Debug Log

- `~/.codex/bin/check-usage.sh` checked before each codex review invocation (story spec T3 critical). Pre-T3 baseline 22% 5h; post-T3 76% 5h. Within threshold.
- 8 codex reviews run sequentially (not parallel) to avoid potential rate-limit races on a single Codex account.
- One codex run (12ba359) re-surfaced a finding already fixed in a subsequent commit (54af50a) — expected behavior since the agent reviews the commit in isolation, not the cumulative history.

## File List

### Created (gitignored under `_bmad-output/`)

- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/medium-findings.json` — AC1 inventory.
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/4108b09.md` — AC2 codex review (apps/api Dockerfile original).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/ca424b4.md` — AC2 codex review (workers/render Dockerfile original).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/12ba359.md` — AC2 codex review (Story 6.7 share_ratelimit_key).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/ce0b56f.md` — AC2 codex review (etag.py original).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/108ea05.md` — AC2 codex review (index.html original).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/f9ce3f8.md` — AC2 codex review (nginx.conf original).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/91361b1.md` — AC2 codex review (Story 9.1 audit baseline / current uv.lock state).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/fb8155a.md` — AC2 codex review (latest package-lock state).
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/codex-reviews/med-001.md` … `med-023.md` — 23 per-finding stubs referencing shared SHA reviews.
- `_bmad-output/implementation-artifacts/audit-raw/2026-05-20/self-attestation-rationale.md` — AC5 verbatim language for Story 9.4 Methodology.

### Modified (tracked)

- `_bmad-output/implementation-artifacts/9-3-codex-review-medium-countersignature.md` — Status `backlog` → `review`; appended Tasks/Subtasks completion, Dev Agent Record, File List, Change Log.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `9-3-codex-review-medium-countersignature` flipped `ready-for-dev` → `in-progress` → `review`; `last_updated` line extended with Sesja AY note.

### Modified (production code or infra)

- NONE — process-control story; no code, no scripts, no infra change. Confirmed by `git status` showing only `.md` / `.yaml` story-file diffs.

## Change Log

- 2026-05-20 — Sesja AY (autonomous ITCM mode, bmad-dev-story). Story 9.3 closed: 23 Medium findings catalogued + dispositioned mitigated + codex-countersigned across 8 unique SHAs; NFR5-SEC-1 cap satisfied with 0/3 accepted-with-rationale; self-attestation rationale binding-language file written for Story 9.4 Methodology section. No runtime change.
