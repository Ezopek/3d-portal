---
title: 'TB-007 verify-symbolication.sh per-run tmpdir (eliminate /tmp/gt-* race)'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
route: 'one-shot'
---

# TB-007 verify-symbolication.sh per-run tmpdir

## Intent

**Problem:** `verify-symbolication.sh` wrote transient state to four hardcoded `/tmp/gt-*.json` paths (poll output, event details, smoke-meta for TB-001 title-guard, alarm envelope + envelope-response). Under concurrent verify invocations (operator + CI both triggered within the same minute) the files would interleave reads and writes, allowing `issue_id` from one run to flow into another run's downstream logic (TB-001 title-guarded DELETE, regex assertion). Promoted from the TB-001 adversarial review (P1 #3, confidence 82) as a pre-existing pattern that TB-001 amplified.

**Approach:** Create a per-run tmpdir alongside the existing `chrome_user_dir`; single combined EXIT trap cleans both. Migrate all 5 hardcoded paths to `$tmp_dir/<name>.json`. Created BEFORE the smoke trigger preflight (the first place that can call `fail_verify` → `emit_alarm` → envelope-file writes) so `$tmp_dir` is always resolved when any helper needs it. No behavioral change in the verify ritual itself.

## Files

- [`infra/scripts/verify-symbolication.sh`](../../infra/scripts/verify-symbolication.sh):
  - `tmp_dir="$(mktemp -d -t verify-gt-XXXXXX)"` + `trap 'rm -rf "$tmp_dir" "$chrome_user_dir"' EXIT` (combined cleanup) right before the smoke trigger preflight.
  - `gt_get` poll output: `/tmp/gt-issues.json` → `"$tmp_dir/issues.json"`.
  - `gt_get` event details: `/tmp/gt-event.json` → `"$tmp_dir/event.json"` (3 read sites).
  - `cleanup_smoke_issue` title-guard: `/tmp/gt-smoke-meta.json` → `"$tmp_dir/smoke-meta.json"`.
  - `emit_alarm` envelope payload: `/tmp/gt-envelope.json` → `"$tmp_dir/envelope.json"`.
  - `emit_alarm` curl response: `/tmp/gt-envelope-response.json` → `"$tmp_dir/envelope-response.json"`.

## Adversarial review summary

`feature-dev:code-reviewer` (no conversation context) returned 0×P0 + 2×P1 (one recanted) + 2×P2 + 2×P3.

- **P1 #1** (82) — `gt_get`'s open `$out` parameter is the structural erosion vector for the TB-007 invariant: any future caller passing a path outside `$tmp_dir` silently reintroduces the race. **Applied:** renamed parameter to `out_file` + one-line guard `[[ "$out_file" == "$tmp_dir/"* ]] || exit 1`.
- **P1 #2** — reviewer self-recanted (confidence dropped <80). Skipped.
- **P1 #3** (88) — `fail_verify`'s `msg` had no default, so any under-argumented call would hit `unbound variable` under `set -u` with a confusing error. **Applied:** `msg="${4:-}"` (matches the existing pattern for `rel`/`frame`).
- **P2 #1, #2** — both flagged as not-TB-007-regression; skipped.
- **P3 #1** — `cleanup_smoke_issue` title-guard comment still described the shared-file race as a live risk; **applied** clarifying note that TB-007 eliminates the shared-file variant, title-guard remains as defence-in-depth against the query-engine returning a wrong `.[0]`.
- **P3 #2** — comment verbosity noted, no fix.

## Verification

- `bash -n` syntax check: clean (twice — pre and post review patches).
- `grep -n "/tmp/gt-" infra/scripts/verify-symbolication.sh`: only the explanatory comment block survives; all 5 code references migrated.
- Live e2e two-pair (default + `--keep-smoke`) on `.190`:
  - Pre-review: smoke 88 deleted, smoke 89 retained.
  - Post-review (after P1 #1 + #3 + P3 #1 patches): smoke 90 deleted, smoke 91 retained.
- `ls /tmp/verify-gt-* /tmp/verify-chrome-*` after each run: no leftover dirs → EXIT trap cleanup confirmed.
- All previous verify-symbolication call paths (FR12 exit codes 0/1/2/3/4/5, alarm POST, title-guarded DELETE) share the same plumbing — behavior unchanged, only path resolution differs.
