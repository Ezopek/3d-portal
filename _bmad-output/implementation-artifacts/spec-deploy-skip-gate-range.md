---
title: 'Deploy skip-gate (range-based) — docs:/chore:/wip: across commit range'
type: 'feature'
created: '2026-05-16'
status: 'done'
baseline_commit: 'c6f065f90629d1899198f7a1fdec8bbb852ff925'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/infra/scripts/deploy.sh'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `deploy.sh` runs unconditionally; the documented gate in AGENTS.md is "(planned)". The first attempt (HEAD-only check, commit `a739eef`, reverted 2026-05-16) failed P1 review because a story branch ending in `chore: ruff format` after a `feat:` commit puts `chore:` at HEAD → HEAD-only gate would swallow the earlier code commit's deploy.

**Approach:** Range-based gate. After every successful deploy, write the deployed commit's SHA to `infra/.last-deploy-sha` (local, gitignored). On next run, evaluate `git log --format=%s <last-deploy-sha>..HEAD` and skip the deploy **only when every commit subject in that range** starts with an element of `SKIP_PREFIXES=("docs:" "chore:" "wip:")`. Missing or unresolvable state file → WARN to stderr and deploy (never trust HEAD-only as fallback).

## Boundaries & Constraints

**Always:**
- Skip-rule lives inside `deploy.sh`; no out-of-band hook.
- `SKIP_PREFIXES` is a single bash array near the top of the script — extending it is a one-line array edit.
- Prefix match: exact, case-sensitive, including colon (`docs:` matches; `Docs:`, `documentation`, `chore(release):` do NOT).
- Range eval: `git log --format=%s "<last-deploy-sha>..HEAD"`. ALL subjects must be skip-prefixed for the gate to skip; empty range (`HEAD == last-deploy-sha`) also skips.
- On skip: one stdout line + `exit 0`. State file is **NOT** updated on skip — preserves the "next run sees the same range" invariant that makes the gate composable across consecutive skip-prefixed pushes.
- On deploy: bit-for-bit identical to today through every existing step; immediately before final `echo "Done."`, write full HEAD SHA to `infra/.last-deploy-sha`. Write is best-effort — failure here must not fail the deploy.
- State file failure modes (missing, empty, contains a SHA that doesn't resolve via `git rev-parse --verify <sha>^{commit}`) all degrade to the same WARN-and-deploy path. WARN messages go to stderr.
- Must remain compatible with `set -euo pipefail` (deploy.sh line 5).

**Ask First:**
- Adding new skip-prefixes beyond `docs:`/`chore:`/`wip:` (e.g. `test:`, `style:`) is an AGENTS.md change first.
- Changing state-file location (current proposal: `infra/.last-deploy-sha`, sibling to `.last-verify*`).

**Never:**
- No regex. Match is `[[ "$subject" == "$prefix"* ]]` against literal strings.
- No `--force-deploy` bypass flag — escape hatch is amending the commit message.
- No retroactive `.last-deploy-sha` backfill — first run after this story takes the WARN path and writes the file on success.
- No state update on skip (see Always § composability invariant).
- No HEAD-only fallback when state is missing/invalid — always WARN+deploy, never assume HEAD alone tells the truth.

## I/O & Edge-Case Matrix

| Scenario | State | Expected Behavior |
|----------|-------|-------------------|
| First run | `.last-deploy-sha` missing | stderr `[deploy-skip-gate] WARN: <path> missing — first run, proceeding`, deploy; on success write HEAD |
| Empty range | File present, HEAD == sha | stdout `[deploy-skip] no new commits since last deploy (<short-range>), skipping`, exit 0, file unchanged |
| All-skip | 3 commits in range, all `docs:`/`chore:` | stdout `[deploy-skip] all 3 commits in <short-range> are skip-prefixed, skipping deploy`, exit 0, file unchanged |
| Mixed range | Range has at least one `feat:`/`fix:` | No skip log, full deploy; on success file updated to new HEAD |
| Stale / invalid SHA | File has SHA that doesn't resolve (rebase, GC, empty file, garbage) | stderr `[deploy-skip-gate] WARN: last-deploy-sha '<sha>' unresolved (rebased or GC'd), proceeding`, deploy; on success overwrite file |
| Capitalized prefix | Range commit `Docs: typo` | Non-match → deploy |
| Scoped Conventional | Range commit `chore(release): bump` | Non-match (literal `chore:` does not match `chore(`) → deploy. Known asymmetry; widening match is a future-AGENTS.md call. |

</frozen-after-approval>

## Code Map

- `infra/scripts/deploy.sh` — gate block after `LOCAL_ENV=` (line ~12), before `DEPLOY_START_TS=`; state-file write before final `echo "Done."` (~line 175) after both post-deploy verifies. Existing flow untouched.
- `infra/.last-deploy-sha` — new local file, gitignored, created at runtime.
- `.gitignore` — add `infra/.last-deploy-sha` (check for an existing broader pattern first).
- `AGENTS.md` § Deploy gate — rewrite from "(planned)" to "(active)" with the range rule, state-file lifecycle, bootstrap behavior, no-bypass invariant. One-sentence pointer to the abandoned predecessor spec.
- Read-only references: abandoned `spec-deploy-skip-gate.md`, memory `feedback_deploy_skip_gate_design.md`.

## Tasks & Acceptance

**Execution:**
- [x] `infra/scripts/deploy.sh` — Insert gate block at documented position. Logic: declare `SKIP_PREFIXES`, read `last_deploy_path`; branch missing → WARN+deploy; branch present → validate SHA via `git rev-parse --verify <sha>^{commit}`; on validation-fail WARN+deploy; on OK compute range, iterate subjects from `git log --format=%s`, match each against `SKIP_PREFIXES`; if all match (or empty range) emit skip line + `exit 0`. Use short SHAs in skip-log range, full SHA internally.
- [x] `infra/scripts/deploy.sh` — Insert state-write block at end (before `echo "Done."`, after both verifies). Capture `deploy_sha_full="$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || true)"`; if non-empty, `echo "$deploy_sha_full" > "$last_deploy_path"`; on write-failure emit a stderr WARN but do NOT fail the deploy.
- [x] `.gitignore` — Append `infra/.last-deploy-sha` if no broader pattern already covers it. Group near existing `infra/.last-verify*` entries if such grouping exists.
- [x] `AGENTS.md` § Deploy gate — Rewrite from "(planned)" to "(active)": range rule, `SKIP_PREFIXES` list, state-file path + lifecycle (write on deploy-success only, skips do NOT update), bootstrap WARN, unresolved-SHA defensive path, no-bypass invariant, pointer to abandoned spec for design rationale.

**Acceptance Criteria:**
- Given `infra/.last-deploy-sha` is missing, when `deploy.sh` runs, then a single `[deploy-skip-gate] WARN:` line goes to stderr and the script proceeds with deploy (no skip log on stdout, no early exit).
- Given the file contains a valid SHA and every commit subject in `<sha>..HEAD` starts with an element of `SKIP_PREFIXES`, when `deploy.sh` runs, then exactly one `[deploy-skip] all <N> commits in <short-range>` line goes to stdout, the script exits 0, and the state file is unchanged on disk.
- Given the same state but at least one subject is non-skip, when `deploy.sh` runs, then no skip log is emitted, the full deploy flow runs, and on completion the new full HEAD SHA is written into `infra/.last-deploy-sha`.
- Given the file's SHA does not resolve (`git rev-parse --verify <sha>^{commit}` fails), when `deploy.sh` runs, then `[deploy-skip-gate] WARN: ... unresolved` goes to stderr and the script proceeds with deploy.
- Given `HEAD == last-deploy-sha` (empty range), when `deploy.sh` runs, then `[deploy-skip] no new commits since last deploy` goes to stdout and the script exits 0.
- Given the state-write at end-of-deploy encounters a write error, when the deploy has otherwise completed, then `echo "Done."` still prints and the script exits 0 (state-write is best-effort).

## Spec Change Log

<!-- Empty until first bad_spec loopback. -->

## Design Notes

State file placement (`infra/.last-deploy-sha`) follows the precedent of `infra/.last-verify` and `infra/.last-verify-runbook` — local-only, single-purpose, sibling to deploy.sh.

`git rev-parse --verify <sha>^{commit}` is the defensive guard against rebased / GC'd SHAs. Without it, `git log` on a stale range either errors (kills script via `set -e`) or returns surprises.

"No state update on skip" makes the gate composable across multiple skip-prefixed pushes: after three consecutive `docs:` pushes the state still points at the last-deployed `feat:`, and a fourth `feat:` push correctly sees the whole range (including the three intervening `docs:` commits) — none would be silently dropped if a later operator amended a commit message.

Golden snippet (gate; illustrative formatting):

```bash
SKIP_PREFIXES=("docs:" "chore:" "wip:")
last_deploy_path="$REPO_DIR/infra/.last-deploy-sha"
head_short="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"

if [[ ! -f "$last_deploy_path" ]]; then
  echo "[deploy-skip-gate] WARN: $last_deploy_path missing — first run, proceeding with deploy" >&2
else
  last_deploy_sha="$(tr -d '[:space:]' < "$last_deploy_path")"
  if ! git -C "$REPO_DIR" rev-parse --verify "${last_deploy_sha}^{commit}" >/dev/null 2>&1; then
    echo "[deploy-skip-gate] WARN: last-deploy-sha '$last_deploy_sha' unresolved (rebased or GC'd), proceeding with deploy" >&2
  else
    range="${last_deploy_sha}..HEAD"
    last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha")"
    short_range="${last_short}..${head_short}"
    subjects="$(git -C "$REPO_DIR" log --format=%s "$range" 2>/dev/null || true)"
    if [[ -z "$subjects" ]]; then
      echo "[deploy-skip] no new commits since last deploy ($short_range), skipping"
      exit 0
    fi
    commit_count="$(git -C "$REPO_DIR" rev-list --count "$range" 2>/dev/null || echo 0)"
    all_skip=true
    while IFS= read -r subject; do
      [[ -z "$subject" ]] && continue
      matched=false
      for prefix in "${SKIP_PREFIXES[@]}"; do
        [[ "$subject" == "$prefix"* ]] && { matched=true; break; }
      done
      if ! $matched; then all_skip=false; break; fi
    done <<< "$subjects"
    if $all_skip; then
      echo "[deploy-skip] all $commit_count commits in $short_range are skip-prefixed, skipping deploy"
      exit 0
    fi
  fi
fi
```

## Verification

**Commands:**
- `bash -n infra/scripts/deploy.sh` — expect exit 0.
- Smoke-1 (state missing): `rm -f infra/.last-deploy-sha && timeout 2 bash infra/scripts/deploy.sh 2>&1 | head -8` — expect stderr `WARN: ... missing — first run`, then `→ Build images locally`.
- Smoke-2 (empty range): `git rev-parse HEAD > infra/.last-deploy-sha && bash infra/scripts/deploy.sh` — expect stdout `[deploy-skip] no new commits since last deploy`, exit 0, ~100ms.
- Smoke-3 (mixed range deploys): `echo a5cc6e7efa896ac28a0d7b7adcadeeada24a5dbd > infra/.last-deploy-sha && timeout 2 bash infra/scripts/deploy.sh 2>&1 | head -10` — current branch HEAD is `feat:` and the range from `a5cc6e7` includes this `feat:` → expect no skip line, `→ Build images locally` before timeout.
- Smoke-4 (stale SHA): `echo deadbeefdeadbeefdeadbeefdeadbeefdeadbeef > infra/.last-deploy-sha && timeout 2 bash infra/scripts/deploy.sh 2>&1 | head -8` — expect stderr `WARN: ... unresolved`, then `→ Build images locally`.
- Cleanup: `rm -f infra/.last-deploy-sha` after smoke testing.

**Manual checks:**
- `touch infra/.last-deploy-sha && git status --short` → file should NOT appear (gitignore working).
- AGENTS.md § Deploy gate text reads identically to the implemented behavior (same prefixes, same state-file path, same lifecycle words).
