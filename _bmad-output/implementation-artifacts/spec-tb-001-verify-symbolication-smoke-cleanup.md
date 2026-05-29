---
title: 'TB-001 verify-symbolication.sh auto-cleanup of smoke issues post-verify'
type: 'bugfix'
created: '2026-05-11'
status: 'done'
route: 'one-shot'
---

# TB-001 verify-symbolication.sh auto-cleanup of smoke issues post-verify

## Intent

**Problem:** Each `verify-symbolication.sh` invocation emits a smoke event with a UUID-tagged title (`Error: smoke <uuid>`). GlitchTip refuses to deduplicate (unique title fingerprint) → every deploy adds exactly one issue. With Story 3.2's `deploy.sh` wiring (verify runs after `alembic upgrade head`), pollution grows monotonically: ~18 issues in 3 weeks of testing (2026-04-30 → 2026-05-10). Without intervention, future Story 2.1-style empirical discovery sessions would have to filter signal from smoke noise.

**Approach:** Add `cleanup_smoke_issue()` helper that issues `DELETE /api/0/issues/<id>/` against GlitchTip on the success exit path only. Failure paths (`fail_verify`) retain the issue as evidence for operator inspection. DELETE failures (transport, 401/403, unexpected codes) emit stderr warnings but never propagate — non-fatal per FR15 contract. `--keep-smoke` flag bypasses cleanup for operator debugging. Title-guard via one extra GET before the destructive call prevents wrong-issue deletion in pathological scenarios (concurrent runs, query-engine quirks).

## Suggested Review Order

1. [Diff — `infra/scripts/verify-symbolication.sh`](../../infra/scripts/verify-symbolication.sh) — read the helper's WHY block first; it documents WHY title-guard, WHY non-fatal, WHY only the success exit path.
2. [Triage backlog entry → Declined/done](../triage-backlog.md) — TB-001 row closed with commit reference + TB-007 candidate added (pre-existing `/tmp/gt-*.json` race surfaced by review).
3. [Sprint status `last_updated`](./sprint-status.yaml) — line carries the one-line summary.

Adversarial review (`feature-dev:code-reviewer` subagent) returned 2× P1 + 1× P2 + 2× P3 + 4× OK confirmations. Patches applied:

- **P1 #2 — title-guard** before DELETE (`GET /api/0/issues/<id>/` → assert `title == "Error: smoke <smoke_run_id>"` before DELETE). Closes the only realistic wrong-issue DELETE path.
- **P2 #4** — docstring exit-4 note: orphan smoke from post-deadline ingest lag is not auto-cleaned; manual sweep advised after extended debugging on a failing verify.
- **P3 #6** — `event:write` scope note clarified: verified sufficient on homelab GlitchTip 6.1.x, upstream Sentry OSS may require project:admin.

Deferred:
- **P1 #3 — `/tmp/gt-*.json` race condition** (all four tmpfiles, pre-existing pattern): TB-001 amplifies the *consequence* (DELETE on possibly-wrong ID) but title-guard from P1 #2 subsumes the destructive impact. Promoted to **TB-007** in triage-backlog. Mitigation: `mktemp -d` for a per-run tmpdir, mirror `chrome_user_dir` pattern from line 280.
- **P3 #8** — `--help` sed regex fragility on blank lines inside docstring: pre-existing, low impact (no blank lines in current docstring).

## Live e2e (pre-commit)

| Scenario | Result |
|---|---|
| Default success path → DELETE | smoke id=70 → matched → top frame OK → DELETE 20x → `GET /issues/70/` → 404 |
| `--keep-smoke` success path | smoke id=71 → matched → top frame OK → "retained" → `GET /issues/71/` → 200 → manual DELETE cleanup |
| Syntax check | `bash -n` clean |
| Help text | `--help` prints updated docstring including Flags + exit-4 note |
| Unknown arg | `--foo` → "✗ unknown argument: --foo (use --help for usage)" → exit 1 |

Pre-existing smoke pollution at TB-001 land time: 16 issues from runs prior to this fix. Operator's call to sweep historically — TB-001 only prevents future accumulation, doesn't backfill. Auto-deploy after commit triggers `verify-symbolication.sh` end-to-end (now with cleanup), serving as a live integration test.
