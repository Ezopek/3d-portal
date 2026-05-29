---
title: 'Deploy skip-gate for docs:/chore:/wip: commits'
type: 'feature'
created: '2026-05-16'
status: 'abandoned' # was in-review; reverted 2026-05-16 after Codex P1 (HEAD-only gate swallows multi-commit ff-merge with skip-prefix tail). Spec retained for redesign reference — see AGENTS.md § Deploy gate (planned — design under review).
baseline_commit: 'a5cc6e7efa896ac28a0d7b7adcadeeada24a5dbd'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/infra/scripts/deploy.sh'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `infra/scripts/deploy.sh` runs unconditionally on every push to `main`, but the just-locked-in gitflow in `AGENTS.md` says deploy must skip when HEAD commit prefix is `docs:`, `chore:`, or `wip:`. Without a script-level gate the convention is documentation only — Claude / Codex / Ezop must each remember to manually skip the deploy call, which is exactly the inconsistency the gate is meant to eliminate.

**Approach:** Add an early-exit guard at the top of `deploy.sh` that reads the HEAD commit subject, matches it against a configurable skip-prefix array, logs a structured skip line, and exits 0 before any build/push/SSH work happens. No changes to the existing deploy flow when the gate doesn't trip.

## Boundaries & Constraints

**Always:**
- Skip-rule MUST live inside `deploy.sh` itself, not in a separate hook, wrapper, or git config. The AGENTS.md decision is explicit.
- Skip-prefix list MUST be a single bash array declared near the top of the script (above the main flow) — extending the list is a one-line array edit, not a logic edit.
- Prefix match is **exact, case-sensitive, including the trailing colon**. `docs:` matches; `docs ` (no colon), `Docs:` (capital D), `docstring` (no colon) do not.
- On skip: emit exactly one line to stdout in the format `[deploy-skip] <prefix>: skipping deploy for commit <short-SHA>` and exit 0.
- On non-skip: script behavior is bit-for-bit identical to today — no new env vars, no reordering, no extra output.
- Must remain compatible with `set -euo pipefail` (already on at line 5).

**Ask First:**
- Any prefix added beyond `docs:`, `chore:`, `wip:` (e.g. proposed `test:`, `style:`). New prefixes are an AGENTS.md change first, then a code change.
- Any failure mode where `git log` could fail and the script must decide skip-vs-deploy (e.g. detached HEAD, no commits yet) — current proposal is "if HEAD subject unreadable, deploy as before" to fail safe in the deploy direction, but flag if implementation reveals a more nuanced case.

**Never:**
- No regex magic. The match is `[[ "$subject" == "$prefix"* ]]` against literal prefix strings.
- No CI-side validation of commit prefixes (out of scope; AGENTS.md is the convention source).
- No retroactive enforcement (no rejecting commits without proper prefix at commit time — that's a pre-commit hook story, not this).
- No bypass flag (`--force-deploy` or env var). If the operator wants to deploy a `docs:` commit, they amend the message or push a follow-up commit. Keeping the gate non-bypassable preserves the "deploy state = main HEAD" invariant.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Doc-only commit | HEAD subject `docs: refine gitflow ...` | `[deploy-skip] docs: skipping deploy for commit a5cc6e7` to stdout, exit 0, no build/push/SSH calls | N/A |
| Chore commit | HEAD subject `chore: bump pin ...` | `[deploy-skip] chore: skipping deploy for commit <sha>`, exit 0 | N/A |
| WIP commit | HEAD subject `wip: half-done refactor` | `[deploy-skip] wip: skipping deploy for commit <sha>`, exit 0 | N/A |
| Feature commit | HEAD subject `feat: add foo` | No skip log; script proceeds to existing build flow | N/A |
| Fix commit | HEAD subject `fix(api): nil deref` | No skip log; script proceeds to existing build flow | N/A |
| Prefix-lookalike | HEAD subject `documentation overhaul` | No skip (literal `docs:` not matched); script proceeds | N/A |
| Capitalized | HEAD subject `Docs: typo` | No skip (case-sensitive); script proceeds | N/A |
| `git log` failure | HEAD unreadable (corrupt repo, detached state mid-operation) | Script proceeds as if non-skip (fail-safe in deploy direction); log `[deploy-skip-gate] WARN: could not read HEAD subject, proceeding with deploy` to stderr | Continue, do not exit on read failure |

</frozen-after-approval>

## Code Map

- `infra/scripts/deploy.sh` — auto-deploy script invoked manually after every code/infra merge to `main` (per `feedback_auto_deploy_dev.md`). Currently no skip logic. The gate goes near the top, after `set -euo pipefail` and the `REPO_DIR` / config block, before the `DEPLOY_START_TS` capture (which must remain pre-build for verify-symbolication.sh).
- `AGENTS.md` (read-only context) — section `## Branching and workflow` § Deploy gate defines the skip-prefix list and the rule. Spec mirrors that list verbatim.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (read-only) — receives a status entry for this quick-dev story at close-out per BMAD convention.

## Tasks & Acceptance

**Execution:**
- [x] `infra/scripts/deploy.sh` — Insert skip-gate block immediately after the `LOCAL_ENV=` line (line ~12), before `DEPLOY_START_TS=`. Block contents: (a) declare `SKIP_PREFIXES=("docs:" "chore:" "wip:")` array; (b) read HEAD subject via `git -C "$REPO_DIR" log -1 --format=%s HEAD 2>/dev/null || true`; (c) capture short SHA via `git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown`; (d) if subject is empty, warn on stderr and fall through; (e) loop over `SKIP_PREFIXES`, matching with `[[ "$subject" == "$prefix"* ]]`; (f) on match: echo skip line to stdout, `exit 0`.

**Acceptance Criteria:**
- Given HEAD commit subject starts with any element of `SKIP_PREFIXES`, when `infra/scripts/deploy.sh` runs, then a single `[deploy-skip] <prefix>: skipping deploy for commit <short-SHA>` line is printed to stdout and the script exits 0 before any `docker compose build` invocation.
- Given HEAD commit subject does NOT match any skip prefix, when `infra/scripts/deploy.sh` runs, then no skip log is emitted and the script behaves bit-for-bit as the pre-gate version.
- Given `git log -1 --format=%s HEAD` cannot resolve a subject (e.g. corrupt state), when `infra/scripts/deploy.sh` runs, then a single `[deploy-skip-gate] WARN: ...` line is emitted to stderr and the script proceeds with deploy (fail-safe direction).
- Given the prefix match is case-sensitive and colon-terminated, when HEAD subject is `Docs: typo` or `documentation`, then the script does NOT skip.

## Spec Change Log

<!-- Empty until first bad_spec loopback. -->

## Design Notes

The check sits inside the script, not as a pre-commit or wrapper layer, because:
1. AGENTS.md explicitly requires it ("skip-rule MUST live in deploy.sh itself, not in an out-of-band hook").
2. `deploy.sh` is invoked by hand (`bash infra/scripts/deploy.sh`) — no GitHub Actions webhook, no systemd timer — so the gate must be where the operator runs the script, otherwise it's bypassed by accident.

Failure-direction choice (fail-safe = deploy, not skip): if the gate cannot determine HEAD state, the safe action is to **deploy** because a missed deploy on a real feature commit is louder (`.190` shows stale) than an extra deploy on a doc-only commit (build cache hits, almost no-op). Inverting this would create silent skip cascades.

Why no `--force-deploy` flag: the deploy state of `.190` should equal `main` HEAD. A bypass flag breaks that invariant ("the script says skip but I ran it anyway"). If a `docs:` commit really needs to deploy (e.g. it's actually shipping a templating change disguised as docs), the operator amends the commit message to a non-skip prefix — that's the right escape hatch.

Golden snippet (illustrative, not normative — actual implementation may differ in formatting):

```bash
# --- Deploy skip-gate (AGENTS.md § Deploy gate) ---------------------------
SKIP_PREFIXES=("docs:" "chore:" "wip:")
head_subject="$(git -C "$REPO_DIR" log -1 --format=%s HEAD 2>/dev/null || true)"
head_sha="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [[ -z "$head_subject" ]]; then
  echo "[deploy-skip-gate] WARN: could not read HEAD subject, proceeding with deploy" >&2
else
  for prefix in "${SKIP_PREFIXES[@]}"; do
    if [[ "$head_subject" == "$prefix"* ]]; then
      echo "[deploy-skip] $prefix skipping deploy for commit $head_sha"
      exit 0
    fi
  done
fi
```

## Verification

**Commands:**
- `bash -n infra/scripts/deploy.sh` — expected: exit 0 (syntax check). Built-in; no external dep.
- `shellcheck infra/scripts/deploy.sh` — expected: no new warnings vs current baseline. **Note:** shellcheck is not installed on this WSL host (verified at spec time). If unavailable, mark as deferred and rely on `bash -n` + manual review of the diff against existing skip annotations in `glitchtip-triage.sh:111` and `verify-symbolication.sh:136`.
- Smoke-test (no full deploy): from a clean state on `main` with HEAD = a `docs:` commit (e.g. current `a5cc6e7`), run `bash infra/scripts/deploy.sh` — expected: prints `[deploy-skip] docs: skipping deploy for commit a5cc6e7` and exits 0 within ~100ms (no docker calls).
- Smoke-test inverse: temporarily checkout a recent `feat:` or `fix:` SHA (e.g. `fc79d77`), run the script with `--dry-run` if such a flag exists, or interrupt with Ctrl-C immediately after the first `echo "→ Build images locally"` line appears — expected: skip line absent, build line present (confirms non-skip path entered).

**Manual checks (if no CLI):**
- After landing this story to `main`, the merge commit itself is `feat:` prefix → deploy SHOULD fire normally. Verify `.190` rebuilds.
- Subsequent `chore:` or `docs:` commit on `main` → verify `bash infra/scripts/deploy.sh` exits with a skip log instead of rebuilding.
