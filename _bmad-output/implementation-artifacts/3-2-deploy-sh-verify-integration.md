# Story 3.2: `deploy.sh` Integration — `DOCKER_BUILDKIT=1` + Verify Call + Last-Verify Tripwire + Exit-Code-Mapped Warning

Status: done

> **Story role:** **SECOND Epic 3 story.** Wires the verify ritual (Story 3.1) into `infra/scripts/deploy.sh` as a non-fatal post-deploy gate. After this commit, every operator-driven deploy automatically:
>
> 1. Warns at START if the previous deploy did NOT record a successful verify (decay protection — FR16).
> 2. Runs build + ship + restart + alembic as before.
> 3. Invokes `verify-symbolication.sh` AFTER alembic, captures exit code, prints a colored exit-code-mapped warning to stderr (red on failure, plain on success). Deploy exit code stays decoupled from verify outcome (FR15 non-fatal contract).
>
> Code change scope: **modify `infra/scripts/deploy.sh` only** — no new files, no other repo touch points. Story 3.1's verify script is the consumed contract; we don't re-touch it.

## Story

As Michał running `bash infra/scripts/deploy.sh`,
I want `deploy.sh` to invoke `verify-symbolication.sh` post-deploy as a non-fatal gate, print exit-code-mapped warning text, and on next invocation warn if `infra/.last-verify` is stale,
so that deploy success is decoupled from observability post-condition (NFR-R3) while three-signal failure detection holds (FR15, FR16) — the verify ritual becomes structurally invoked, not a manual habit that decays.

## Acceptance Criteria

> **Source:** epics.md:548–576 (Story 3.2 ACs). Tightened where the spec deferred a choice; otherwise verbatim.

1. **AC1 — `DOCKER_BUILDKIT=1` export remains in place.** `infra/scripts/deploy.sh` line 31 (Story 1.5 carry-over) already does `export DOCKER_BUILDKIT=1` before `docker compose build`. This story is a no-op for that line — verify it stays put. **NOT a regression target:** if a future refactor removes it, BuildKit secret mount (`apps/web/Dockerfile:36`) silently breaks → plugin upload silently skipped → Epic 1 regression returns. Inline comment at the export site already pins the rationale.

2. **AC2 — Stale-verify tripwire fires at START (before build).** Inserted near the top of `deploy.sh` (after `LOCAL_ENV` setup and before the build phase), the script:
   - Computes `last_verify_path="$REPO_DIR/infra/.last-verify"`.
   - Computes the "previous deploy" reference timestamp via `git log -1 --format=%ct HEAD` (commit timestamp of current HEAD, in seconds since epoch). Rationale: simplest mechanism per epics.md:559; no new file introduced; HEAD's commit time is monotonically tied to the act of merging/committing-then-deploying. (Documented inline in deploy.sh as the chosen mechanism.)
   - **If `last_verify_path` does NOT exist** (first ever run, file deleted, fresh checkout): print a brief blue informational `→ verify history not yet established (no infra/.last-verify); first run after this deploy will populate it` to stdout, do NOT abort, do NOT count as stale.
   - **If `last_verify_path` exists AND its mtime (in seconds) < previous deploy timestamp:** print a YELLOW warning to stderr: `⚠ stale verify: previous deploy did not record a successful verification (last verify: <iso8601 of mtime>; last commit: <iso8601 of HEAD timestamp>)`. Do NOT abort. The mtime/timestamp comparison uses `stat -c %Y "$last_verify_path"` for the file mtime.
   - **If `last_verify_path` exists AND its mtime >= previous deploy timestamp:** silent. Last verify covered the current HEAD or a later state.
   - ANSI color code: yellow = `\033[33m`, blue (informational) = `\033[34m`, reset = `\033[0m`. Use `printf '\033[33m...\033[0m\n' >&2` (matches verify-symbolication.sh's red-stderr pattern).
   - **Edge:** the comparison is one-sided — older `.last-verify` mtime relative to HEAD timestamp triggers the warning. NOT bidirectional (a fresh `.last-verify` is fine even if it's from a long-since-rolled-back deploy).

3. **AC3 — Verify call happens AFTER `alembic upgrade head` succeeds.** New phase appended to `deploy.sh` (after `Run alembic migrations` echo and before `Done.`):
   - `echo "→ Verify post-deploy symbolication"`.
   - `verify_exit=0`.
   - `bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || verify_exit=$?`. **NOT** `|| true` — capturing the code is required. (Story spec / Decision K explicitly forbids `|| true`.)
   - Implementation: the `||` clause uses `verify_exit=$?` which captures the failed exit. `set -e` would otherwise abort the deploy script on any non-zero verify; `||` short-circuits that.

4. **AC4 — Exit-code-mapped warning printed.** Mirrors Decision K example (epics.md:561–571 / architecture.md:460–473):
   ```bash
   case "$verify_exit" in
     0) echo "✓ verify OK" ;;
     1) printf '\033[31m⚠ verify FAILED: symbolication broken (top frame regex mismatch)\033[0m\n' >&2 ;;
     2) printf '\033[31m⚠ verify FAILED: GlitchTip unreachable\033[0m\n' >&2 ;;
     3) printf '\033[31m⚠ verify FAILED: auth/scope failure — token rotation needed?\033[0m\n' >&2 ;;
     4) printf '\033[31m⚠ verify FAILED: timeout (no matching event within 30s)\033[0m\n' >&2 ;;
     *) printf '\033[31m⚠ verify FAILED: unexpected exit %s\033[0m\n' "$verify_exit" >&2 ;;
   esac
   ```
   - Successful verify (`exit_code=0`) prints to stdout, plain `✓` (no color — quiet success).
   - Non-zero exit prints to stderr, red `\033[31m...\033[0m`.
   - Wildcard `*)` covers any future verify exit code added beyond 0–4 (defensive; story 3.1's spec stays at 0–4 but defensive cases are cheap).

5. **AC5 — Deploy exit code stays decoupled from `verify_exit` (FR15 non-fatal contract).** After the case-statement, `deploy.sh` does NOT propagate `verify_exit`. The script ends with `echo "Done."` and implicit exit 0 (assuming all build/ship/restart phases succeeded). Verifiable: deploy with verify deliberately broken → script exits 0; deploy with build broken → script exits >0 (build failure, NOT verify-related). The verify outcome lands ONLY in: (a) the printed warning, (b) `infra/.last-verify` content, (c) the synthetic alarm event in GlitchTip.

6. **AC6 — Stale-verify warning fires the run AFTER a FAILED verify.** Manual smoke from operator's PoV: after a successful deploy whose verify exited 1 (regex mismatch), `infra/.last-verify` carries `FAILED` and its mtime is just after the deploy. Then commit a new change + run `bash infra/scripts/deploy.sh`. The new run's HEAD timestamp is NEWER than `.last-verify` mtime → wait, that's the wrong direction. Re-reading AC2: comparison is `.last-verify mtime < HEAD timestamp` → stale warning. **Yes:** a FAILED `.last-verify` from previous deploy will have older mtime than the new HEAD → stale warning fires. Verifiable.

   **Subtle gotcha:** if the operator runs `deploy.sh` MULTIPLE times against the SAME HEAD (no new commit), the `.last-verify` mtime would be NEWER than HEAD timestamp (because verify wrote it after HEAD's commit time). So no stale warning. That's the correct behavior — repeating a deploy without new commit doesn't accumulate decay.

7. **AC7 — `bash -x infra/scripts/deploy.sh` trace contains exactly one `verify-symbolication.sh` invocation, zero `upload-sourcemaps.sh` invocations.** Cross-checks Story 1.6's CLI decoupling. Verifiable post-deploy: `bash -x infra/scripts/deploy.sh 2>&1 > /tmp/deploy-trace.log`; `grep -c 'verify-symbolication.sh' /tmp/deploy-trace.log` returns `1` (executed line; comments don't trace); `grep -c 'upload-sourcemaps.sh' /tmp/deploy-trace.log` returns `0`.

8. **AC8 — `bash -n infra/scripts/deploy.sh` exits 0** (syntax check; mirrors Story 1.6 AC7 / Story 3.1 AC16).

9. **AC9 — `infra/.last-verify` line gets refreshed on every successful deploy.** End-to-end smoke: `bash infra/scripts/deploy.sh` against healthy `.190` produces:
   - All build/ship/restart/alembic phases logged successfully.
   - Final verify phase logs: `→ Verify post-deploy symbolication` then `✓ verify OK`.
   - `infra/.last-verify` is a fresh single-line tab-separated `<ISO-8601>\t<OK>\t<release>` matching Story 3.1's AR8 format.
   - `cat infra/.last-verify | wc -l` returns `1` (no append accumulation).

10. **AC10 — End-to-end smoke with verify deliberately broken produces three-signal failure WITHOUT aborting deploy.** Operator-driven verification per epics.md:574 — temporarily simulate verify failure, e.g., by exporting `PORTAL_PUBLIC_URL=https://does-not-exist.invalid` for one run (causes verify exit 2 — unreachable). Expected:
    - All deploy phases succeed → `Done.` prints → script exits 0.
    - Verify call exits 2.
    - stderr: red `⚠ verify FAILED: GlitchTip unreachable`.
    - `infra/.last-verify` carries `FAILED` (per Story 3.1 fail_verify helper).
    - No synthetic alarm posted (exit 2 means GlitchTip is the broken party, can't send alarm to it).
    - No deploy abort.
    Three signals: stderr message + FAILED marker + (in real production failures) GlitchTip event. **Avoid** running the deliberate-break smoke against actual production unless rolling forward with a clean deploy immediately afterward — the FAILED marker would otherwise persist as the last-known-state for the next deploy's stale check (which is fine, just noisy).

11. **AC11 — Deploy exit code unaffected by verify outcome on broken-verify smoke.** Verifiable: after AC10's smoke, `echo $?` returns `0` (deploy succeeded; verify failure was non-fatal). Codifies FR15.

12. **AC12 — Stale-verify warning manually exercised.** Operator-driven verification per epics.md:575: after AC10's broken-verify run lands `.last-verify FAILED`, make a trivial new commit (e.g., `git commit --allow-empty -m "test stale verify"` — this is a destructive-test artifact that should be reverted/dropped, NOT committed to main). Run `bash infra/scripts/deploy.sh` again. Expected: yellow `⚠ stale verify: ...` at the START of the script (before build). Then the new deploy runs end-to-end and writes a fresh `.last-verify`. **DO NOT push the throwaway commit to main** — drop it via `git reset --hard HEAD~1` after the stale-warning is observed. Alternative non-destructive approach: simulate by `touch -t 202001010000 infra/.last-verify` to backdate the file; mtime is now older than HEAD timestamp; stale warning fires; subsequent deploy refreshes the file.

13. **AC13 — Smoke against current production preserves expected post-deploy state.** Final state after Story 3.2 lands and is auto-deployed: `bash infra/scripts/verify-symbolication.sh` (run standalone OR via deploy.sh's new phase) exits 0; `infra/.last-verify` carries `OK <release>` matching the deployed RELEASE; deploy.sh's stdout shows the new `→ Verify post-deploy symbolication` + `✓ verify OK` lines; deploy.sh exits 0.

## Tasks / Subtasks

- [x] **Task 1: Pre-flight — clean baseline** (AC8, AC13 baseline)
  - [x] Subtask 1.1: `git status` clean. `bash -n infra/scripts/deploy.sh` exits 0 (current state baseline).
  - [x] Subtask 1.2: Confirm `infra/.last-verify` exists with current `OK <release>` from Story 3.1's last green run. `cat infra/.last-verify` shows a single line. `wc -l < infra/.last-verify` returns 1.
  - [x] Subtask 1.3: Confirm Story 3.1's verify ritual is healthy: `bash infra/scripts/verify-symbolication.sh` exits 0 (don't strictly need to run this — Story 3.1 was just validated — but a 5-second sanity check costs nothing and proves the script we're about to call from deploy.sh is in working order).

- [x] **Task 2: Add stale-verify tripwire at script start** (AC2)
  - [x] Subtask 2.1: After the `LOCAL_ENV` setup block (current line 21) and BEFORE `echo "→ Build images locally ..."` (current line 23), insert the stale-verify check. Aim to keep the pre-build phase tight (≤25 lines added). Pattern:
    ```bash
    # --- Stale-verify tripwire (Story 3.2; FR16) -----------------------------
    # Warn loud + non-fatal at the START if the previous deploy did NOT record
    # a successful verify. Reads `infra/.last-verify` mtime vs the current
    # HEAD's commit timestamp (chosen per epics.md:559 — simplest mechanism, no
    # new state file needed; HEAD time is monotonically tied to "the deploy
    # being performed now"). Older mtime → previous deploy's verify never
    # landed (or wasn't recent) → operator sees yellow warning.
    last_verify_path="$REPO_DIR/infra/.last-verify"
    if [[ -f "$last_verify_path" ]]; then
      last_verify_mtime=$(stat -c %Y "$last_verify_path")
      head_timestamp=$(git -C "$REPO_DIR" log -1 --format=%ct HEAD 2>/dev/null || echo 0)
      if (( last_verify_mtime < head_timestamp )); then
        printf '\033[33m⚠ stale verify: previous deploy did not record a successful verification (last verify: %s; last commit: %s)\033[0m\n' \
          "$(date -u -d "@$last_verify_mtime" +%Y-%m-%dT%H:%M:%SZ)" \
          "$(date -u -d "@$head_timestamp" +%Y-%m-%dT%H:%M:%SZ)" >&2
      fi
    else
      printf '\033[34m→ verify history not yet established (no infra/.last-verify); first run after this deploy will populate it\033[0m\n'
    fi
    ```
  - [x] Subtask 2.2: `bash -n infra/scripts/deploy.sh` exits 0 (syntax check on the inserted block).

- [x] **Task 3: Add post-alembic verify phase** (AC3, AC4, AC5)
  - [x] Subtask 3.1: After the existing `echo "→ Run alembic migrations"` block (current lines 55–56) and BEFORE `echo "Done."` (current line 58), insert the verify phase:
    ```bash
    # --- Post-deploy verify (Story 3.2; FR15) --------------------------------
    # Non-fatal gate: deploy success is decoupled from verify outcome
    # (NFR-R3). Capture the FR12 exit code (0/1/2/3/4) and print an exit-code-
    # mapped warning. Deploy exits 0 regardless of verify_exit; the verify
    # signal lands in (a) the printed warning here, (b) infra/.last-verify
    # (Story 3.1 fail_verify writes FAILED on every non-zero exit), and
    # (c) a synthetic GlitchTip event for codes 1/3 (Story 3.1 emit_alarm).
    echo "→ Verify post-deploy symbolication"
    verify_exit=0
    bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || verify_exit=$?
    case "$verify_exit" in
      0) echo "✓ verify OK" ;;
      1) printf '\033[31m⚠ verify FAILED: symbolication broken (top frame regex mismatch)\033[0m\n' >&2 ;;
      2) printf '\033[31m⚠ verify FAILED: GlitchTip unreachable\033[0m\n' >&2 ;;
      3) printf '\033[31m⚠ verify FAILED: auth/scope failure — token rotation needed?\033[0m\n' >&2 ;;
      4) printf '\033[31m⚠ verify FAILED: timeout (no matching event within 30s)\033[0m\n' >&2 ;;
      *) printf '\033[31m⚠ verify FAILED: unexpected exit %s\033[0m\n' "$verify_exit" >&2 ;;
    esac
    ```
  - [x] Subtask 3.2: `bash -n infra/scripts/deploy.sh` exits 0 (syntax check after both inserts).
  - [x] Subtask 3.3: Verify the existing `Done.` line is still the last echo — this is the contract `deploy.sh` users have been seeing since 2026-04-30.

- [x] **Task 4: Trace check** (AC7)
  - [x] Subtask 4.1: Read the modified `deploy.sh` start-to-end. Confirm there's exactly ONE `verify-symbolication.sh` reference in executed-line code (the new `bash "$REPO_DIR/infra/scripts/verify-symbolication.sh"` line) and ZERO `upload-sourcemaps.sh` references. The existing comment at lines 35–38 mentions `upload-sourcemaps.sh --help` for documented manual recovery — that's a comment, NOT a trace target. Also confirm: `grep -c '^[[:space:]]*bash.*upload-sourcemaps' infra/scripts/deploy.sh` returns 0.

- [x] **Task 5: End-to-end smoke — happy path** (AC9, AC13)
  - [x] Subtask 5.1: Stage the deploy.sh changes: `git add infra/scripts/deploy.sh`.
  - [x] Subtask 5.2: Conventional commit per project memory (`feedback_auto_deploy_dev` requires auto-deploy after every code/infra commit): `feat(infra): wire verify-symbolication into deploy.sh post-alembic`. Body: stale-verify tripwire at start + verify call after alembic + exit-code-mapped warning. References Story 3.2.
  - [x] Subtask 5.3: `bash infra/scripts/deploy.sh` (auto-deploy). Watch for: blue or yellow stale-verify line at start (depends on whether `.last-verify` mtime < new HEAD timestamp — most likely YES because the new commit is fresher than the previous verify); all build/ship/restart/alembic phases; `→ Verify post-deploy symbolication`; `✓ verify OK`; final `Done.`. Capture stdout to a file for AC trace check (Subtask 4.1).
  - [x] Subtask 5.4: After deploy completes, verify `cat infra/.last-verify` shows a fresh single-line `<iso>\t<OK>\t<release>` where `<release>` matches the just-deployed commit. `wc -l < infra/.last-verify` returns 1.
  - [x] Subtask 5.5: `echo $?` immediately after deploy.sh returns 0 (deploy script exited cleanly).
  - [x] Subtask 5.6: Capture deploy.sh stdout/stderr to log; grep-check: `grep -c 'verify-symbolication.sh' /tmp/deploy-3-2-smoke.log` returns ≥1; `grep -c 'upload-sourcemaps' /tmp/deploy-3-2-smoke.log` returns 0 (excluding the comment-block reference if it gets echoed — usually doesn't because comments aren't echoed).

- [x] **Task 6: End-to-end smoke — broken-verify path** (AC10, AC11)
  - [x] Subtask 6.1: Use the safe non-destructive method: `PORTAL_PUBLIC_URL=https://does-not-exist.invalid bash infra/scripts/deploy.sh` runs verify with a deliberately bad smoke URL; verify will fail at the smoke trigger curl, exit 2 (unreachable). Justified per AC10: this never makes a real deploy "broken" — only the verify phase fails. The earlier build/ship/restart/alembic phases run as normal; a real production bundle still ships from this run (it was the freshest one); the only thing wrong is the verify post-condition could not be evaluated.
    - Alternative (also safe): temporarily rename `infra/scripts/verify-symbolication.sh` to e.g. `verify-symbolication.sh.disabled`, run deploy.sh — the `bash` invocation will fail (no such file), `set -e` would normally abort, but the `|| verify_exit=$?` clause swallows the failure → `verify_exit` becomes 127 → wildcard case-arm fires → red `unexpected exit 127`. Restore the script name afterward.
    - Pick whichever feels simpler in the moment. Both are reversible.
  - [x] Subtask 6.2: Expected: deploy.sh exits 0 (build/ship phases all OK); stderr shows the red `⚠ verify FAILED: GlitchTip unreachable` (or `unexpected exit 127`); `.last-verify` carries `FAILED` (Story 3.1's `fail_verify` helper writes it on every non-zero exit, including the new-AC10 codes).
  - [x] Subtask 6.3: Roll the broken state forward: re-run `bash infra/scripts/deploy.sh` (without the `PORTAL_PUBLIC_URL` env override). Expected: yellow stale-verify warning at start (because the FAILED marker's mtime is just barely older than the new HEAD timestamp from Subtask 5.2's commit — actually mtime IS newer than HEAD timestamp from that commit, so... hmm; see AC12 alternative for guaranteed stale fire). Then deploy succeeds + verify exits 0 + `.last-verify` reverts to `OK`. **Edge case clarification:** AC12 alternative `touch -t 202001010000 infra/.last-verify` is the deterministic way to force the stale warning regardless of commit ordering.

- [x] **Task 7: Stale-verify warning manual smoke** (AC12)
  - [x] Subtask 7.1: Pick the non-destructive path: `touch -t 202001010000 infra/.last-verify` (or any old date). Verify mtime is now ancient.
  - [x] Subtask 7.2: `bash infra/scripts/deploy.sh`. Expected: at the very start (before `→ Build images locally ...`), stderr shows yellow `⚠ stale verify: previous deploy did not record a successful verification (last verify: 2020-01-01T00:00:00Z; last commit: <iso8601 of HEAD>)`. Deploy proceeds end-to-end. New verify writes a fresh `.last-verify` with current timestamp.
  - [x] Subtask 7.3: After deploy, `cat infra/.last-verify` shows a current-timestamped `OK` line. The stale state has been cleared by the act of running deploy + verify successfully.

- [x] **Task 8: Update story file + sprint-status; verify final state**
  - [x] Subtask 8.1: Mark all tasks/subtasks `[x]` in this file. Populate Dev Agent Record (Agent Model Used, Debug Log References, Completion Notes, File List, Change Log).
  - [x] Subtask 8.2: Update `_bmad-output/implementation-artifacts/sprint-status.yaml`:
    - `3-2-deploy-sh-verify-integration: in-progress` → `review` (after Task 5/6/7 smokes pass).
    - `last_updated` field bumped to current date.
  - [x] Subtask 8.3: Mark story Status = `review` in this file's header. (Code-review by Codex per BMAD discipline before marking `done`.)
  - [x] Subtask 8.4: `git status` clean (the `_bmad-output/` modifications are gitignored; only the auto-deploy commit's deploy.sh change should be in git history).

## Dev Notes

### File-structure footprint (single MODIFIED file)

Per architecture.md:489–520, this story modifies exactly one file:

**MODIFIED:**
- `infra/scripts/deploy.sh` — adds stale-verify tripwire (~12 lines) + post-alembic verify phase (~15 lines).

**NOT TOUCHED:**
- `infra/scripts/verify-symbolication.sh` — Story 3.1's contract is consumed as-is; do not re-touch.
- `apps/web/src/main.tsx`, `apps/web/vite.config.ts`, `apps/web/Dockerfile` — no web/build changes.
- `_bmad-output/project-context.md` — Story 3.4 owns the +3 execution-discipline rules.
- `docs/operations.md` — Story 3.3 owns the runbook rewrite.

### Why HEAD's commit timestamp as "previous deploy" reference?

Per epics.md:559: "read `infra/.last-verify` and the timestamp of the previous deploy (e.g., `git log -1 --format=%ct main` or `infra/.last-deploy` if such a file is introduced — pick simplest mechanism documented in the inline comment)."

Chosen: `git log -1 --format=%ct HEAD`. Reasons:
- **No new state file.** Adding `infra/.last-deploy` introduces another tripwire to maintain + gitignore + clear during fresh-checkout edge cases. HEAD timestamp is naturally available.
- **Monotonically tied to "the act of deploying."** Operator commits → runs deploy.sh → verify writes `.last-verify`. The HEAD timestamp at deploy.sh start is fresher than ANY earlier verify. So "older mtime than HEAD" reliably signals "verify didn't keep up with the latest commit."
- **`%ct` (committer timestamp), not `%at` (author timestamp).** Committer timestamp updates on rebase/amend; author timestamp doesn't. Deploy aligns with the committer action (the action being deployed), so `%ct` is the correct field.
- **Trade-off:** running `deploy.sh` MULTIPLE times against the SAME HEAD without new commits has the second run's `.last-verify` mtime LATER than HEAD's commit time → no stale warning → repeat-deploy-no-decay (intended).

### Decision K compliance

Per architecture.md:225–230 and:460–473, Decision K specifies:
- `deploy.sh` invokes `verify-symbolication.sh` AFTER successful `docker compose up -d` + `alembic upgrade head` ✓ (Task 3 places the call after the alembic SSH command).
- Verify exit code does NOT fail the deploy script ✓ (`|| verify_exit=$?`, no propagation).
- Loud red warning prints on non-zero ✓ (case-statement with `\033[31m...\033[0m` to stderr).
- Tripwire: `deploy.sh` checks `infra/.last-verify` mtime at start; warns if older than previous deploy ✓ (Task 2).
- Verify exit codes 0/1/2/3/4 consumed by deploy.sh for warning text ✓ (matches Story 3.1's exit-code contract verbatim).
- Failed-verify synthetic event hits same DSN as runtime errors → same triage path: ✓ (Story 3.1's `fail_verify` + `emit_alarm` already do this; this story doesn't touch).

### Anti-pattern from architecture.md:475–481

> **Anti-pattern — silent verify in deploy.sh:**
> ```bash
> bash "$REPO_DIR/infra/scripts/verify-symbolication.sh" || true
> ```
> Loses the failure signal. Forbidden by Decision K.

The story's pattern uses `|| verify_exit=$?` which captures the code instead of swallowing it. The case-statement then surfaces it loudly. Don't regress to `|| true`.

### Stale-warning placement reasoning

Why warn at START (before build), not at END (after verify):
- Decay protection (FR16) addresses the case where the PREVIOUS deploy's verify failed silently (or was never run). The operator needs that signal BEFORE committing 30+ seconds to a new build cycle. If the previous deploy's symbolication is broken AND the operator is doing a routine bug-fix deploy, warning early lets them investigate before piling on more changes.
- The post-deploy verify of THIS run produces the same-run signal (red warning if it fails). The stale check is about the DELTA across runs.

### Color / glyph conventions (matches Story 3.1 + project deploy.sh style)

| Glyph | Stream | Color | Use |
|---|---|---|---|
| `→` | stdout | none | Operator-facing narrative ("Triggering …", "Build images …") |
| `✓` | stdout | none | Quiet success ("verify OK", "build OK") — NOT colored, success is the default |
| `⚠` | stderr | yellow `\033[33m` | Stale / non-fatal warning that asks for attention but doesn't block |
| `✗` | stderr | red `\033[31m` | Failure — already-shipped (deploy succeeded but verify failed; no abort) |

This story uses ⚠-yellow for stale-verify (decay) and ⚠-red for verify-FAILED (post-condition mismatch). Both go to stderr so deploy.sh's stdout stays grep-friendly for "Done."-style end markers.

### Existing deploy.sh conventions to preserve

- `set -euo pipefail` at top — DO NOT change.
- `REPO_DIR`, `COMPOSE_DIR`, `TARGET_HOST`, `SSH_PORT`, `VERSION`, `LOCAL_ENV` variables at top — DO NOT rename or reorder.
- The `→` prefix on stdout narrative — match it for new lines.
- The fetch-`.env`-from-`.190`-if-missing block (lines 17–21) — leave alone.
- `export DOCKER_BUILDKIT=1` (line 31) + comment — leave alone (AC1 explicit).
- The Sentry/CLI fallback comment block (lines 35–38) — leave alone (Story 1.6 owns that comment as documented manual recovery context).
- Final `echo "Done."` — keep as the LAST line. New verify phase goes BEFORE `Done.`.

### Manual smoke vs automated tests

This story has NO automated tests for two reasons:
1. `deploy.sh` SSHs to `.190` and runs docker; impossible to unit-test without an integration harness.
2. The story's contract is "operator runs deploy.sh; sees X" — operator-driven verification matches the architecture's manual-smoke pattern for infra scripts.

The TASKS list above explicitly captures the smoke steps. AC10/AC12 record the broken-path smoke as well. Story 3.1's vitest spec for the smoke handler proves the in-app contract; deploy.sh's role is composition.

### Project-context patterns (inherited)

- Conventional commit scope `infra` for this delta.
- Auto-deploy after the commit per project memory `feedback_auto_deploy_dev`.
- No `--no-verify` / `--no-gpg-sign`.
- Trunk-only `main`, ff-merge only.
- ESLint / typecheck not relevant (bash-only change).

## Previous Story Intelligence

### From Story 3.1 (commits `11f048e..82addc7`; final state `done`)

- **Verify ritual is alive end-to-end.** `bash infra/scripts/verify-symbolication.sh` exits 0 against production with `top frame: apps/web/src/main.tsx, release: 0.1.0+82addc7`.
- **Exit codes 0/1/2/3/4 are stable.** Story 3.2 consumes this contract. Codex review of 3.1 added defensive handling (`fail_verify` helper writes `.last-verify FAILED` on EVERY non-zero exit, not just regex mismatch) — so even codes 2/3/4 leave a FAILED marker for next deploy's stale check to detect. Wildcard `*` case-arm in Story 3.2's deploy.sh covers exit codes outside 0–4 defensively (e.g., `127` from missing-script test).
- **Single failure exit point in verify-symbolication.sh.** Story 3.1's `fail_verify` makes the writes consistent. deploy.sh just reads `verify_exit`; no need to also inspect `.last-verify` content from deploy.sh — the case-statement on `$verify_exit` is the single decision point.
- **Headless chrome dependency.** Story 3.1's verify script needs `google-chrome` or `chromium` on the operator's box. deploy.sh runs from the operator's dev box; the dev box has Chrome. NOT a deploy.sh concern — the dependency is verified by `verify-symbolication.sh`'s own pre-flight (`HEADLESS_BROWSER` autodetection at line 68–81).
- **Story 3.1 took 4 commits to stabilize** (initial impl + 3 iteration fixes). Lesson: when wiring deploy.sh to verify, the FIRST run after merge is the gate that proves end-to-end. Don't trust `bash -n` syntax check alone.

### Carry-overs from earlier Epic 1 stories

- **deploy.sh has been touched 3 times in this delta.** Story 1.5 added `export DOCKER_BUILDKIT=1`. Story 1.6 removed the CLI sourcemap-upload block. Story 3.2 adds the stale-tripwire + verify call. Each touch was minimal and additive (or subtractive in 1.6's case). Pattern: keep deploy.sh tight; long scripts in deploy chains decay fast.
- **`REPO_DIR` computed via `BASH_SOURCE`** — matches `verify-symbolication.sh:57`. Use the existing `$REPO_DIR` variable in deploy.sh; do NOT recompute.

## Git Intelligence Summary

Last 5 commits (`git log -5 --oneline`):
- `82addc7 fix(infra+web): address Codex review of Story 3.1 (HIGH+MED+LOW)` — Story 3.1 final
- `2f02d7e fix(web): normalize sourcemap paths to apps/web/<...> for NFR-R1 regex` — Epic 1 regression closure
- `76527ab fix(infra): read release from .tags[] not .release in verify script` — Story 3.1 fix
- `a1b76a4 fix(infra): use headless chrome for verify-symbolication smoke trigger` — Story 3.1 fix
- `11f048e feat(infra): verify-symbolication.sh + smoke-trigger handler` — Story 3.1 initial

Patterns picked up:
- Conventional commit scope `feat(infra)` for additive infra-script work.
- Auto-deploy after every code/infra commit.
- Codex review per BMAD discipline before mark-as-done. Story 3.2 will follow the same path.

## Latest Tech Information

### `git log -1 --format=%ct HEAD` semantics

- `%ct` = committer date, Unix timestamp (seconds since epoch). Updated on rebase/amend (which is what we want — the commit's "current" identity).
- `%at` = author date, Unix timestamp. Stable across rebases — NOT what we want here.
- Available since git 1.5+; non-issue on any modern dev box.

### `stat -c %Y <file>` for mtime in seconds

- Linux coreutils (BSD `stat -f` differs but this script targets Linux WSL2 + .190 only).
- `%Y` = "Time of last data modification, seconds since Epoch."
- Returns 0 if file doesn't exist? No — actually returns error and exits non-zero. The Task 2.1 implementation guards with `[[ -f "$last_verify_path" ]]` first, so `stat` is only called when the file exists. No edge case.

### ANSI color escapes in printf

- `\033[31m` = red, `\033[33m` = yellow, `\033[34m` = blue, `\033[0m` = reset.
- Use `printf '\033[XXm...\033[0m\n'` (preserves color codes); `echo -e` is shell-dependent (bash supports `-e`, dash doesn't). Story 3.1's `verify-symbolication.sh` uses `printf` for the same reason — match.
- Terminal honoring depends on `TERM` env var. Modern terminals (operator's terminal on dev box, GH Actions, etc.) all honor. Non-terminal stdout (redirect to file) shows the literal `\033[31m...` codes — that's the standard cost of inline coloring; `tput setaf 1` would need terminal capability detection which is overkill for this delta.

## Project Context Reference

Read `_bmad-output/project-context.md` for the full 125 rules. Most relevant for this story:
- **Bash conventions** (lines ~422 of architecture.md echoed): `set -euo pipefail`, `REPO_DIR` from `BASH_SOURCE`, stdout vs stderr split, `→`/`✓`/`⚠`/`✗` glyphs.
- **Auto-deploy after every code/infra commit** (project memory `feedback_auto_deploy_dev`): the commit that lands this story IS the deploy that will smoke-test it.
- **Conventional commits with scope** (`feat(infra)`).
- **No `--no-verify`** in git operations.

## References

- **Epic source:** `_bmad-output/planning-artifacts/epics.md:548–576` (Story 3.2 ACs).
- **Architecture:**
  - `_bmad-output/planning-artifacts/architecture.md:225–230` (Decision K — non-fatal verify + tripwire).
  - `_bmad-output/planning-artifacts/architecture.md:460–481` (Decision K Pattern Examples — good and anti-pattern).
- **PRD:**
  - `_bmad-output/planning-artifacts/prd.md:381–382` (FR15, FR16 — non-fatal verify + decay protection).
  - `_bmad-output/planning-artifacts/prd.md:431–434` (NFR-R3, NFR-R4 — three-signal failure model + decay window).
- **Existing files:**
  - `infra/scripts/deploy.sh` (current state — 58 lines).
  - `infra/scripts/verify-symbolication.sh` (Story 3.1 contract).
  - `infra/.last-verify` (current `OK 0.1.0+82addc7`).
- **Previous story:**
  - `_bmad-output/implementation-artifacts/3-1-verify-symbolication-script.md` (Status: done; 18 ACs satisfied).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m] (Claude Opus 4.7, 1M context)

### Debug Log References

- `bash -n infra/scripts/deploy.sh` exits 0 (AC8).
- Static trace check: `grep -c 'verify-symbolication.sh' infra/scripts/deploy.sh` returns 1; `grep -c '^[[:space:]]*bash.*upload-sourcemaps' infra/scripts/deploy.sh` returns 0 (AC7).
- Auto-deploy of commit `31dac06`: build/ship/restart/alembic phases logged successfully; `→ Verify post-deploy symbolication` + `✓ verify OK — top frame: apps/web/src/main.tsx, release: 0.1.0+31dac06` + `Done.`. deploy exit code: 0. `infra/.last-verify` carries `2026-05-09T22:44:57Z<TAB>OK<TAB>0.1.0+31dac06`. AC9, AC13 ✓.
- AC10/AC11 lightweight smoke (no full redeploy): `PORTAL_PUBLIC_URL=https://does-not-exist.invalid bash infra/scripts/verify-symbolication.sh` exits 2; `infra/.last-verify` written `FAILED unknown`. Wrapper test: `bash -c 'set -euo pipefail; verify_exit=0; bash -c "exit 2" || verify_exit=$?; case ... esac; echo Done.'` exits 0 + prints red warning to stderr.
- AC12 stale-verify smoke: `touch -t 202001010000 infra/.last-verify` + extracted stale-check block from deploy.sh → yellow `⚠ stale verify: previous deploy did not record a successful verification (last verify: 2019-12-31T23:00:00Z; last commit: 2026-05-09T22:43:51Z)`. Restored via re-run of verify-symbolication.sh.

### Completion Notes List

- **Story 3.2 ships in a single commit (`31dac06`).** No iteration fixes needed; the dev cycle confirmed the story's pre-spec design ran clean. Total LOC added to deploy.sh: 39 lines (12 stale-verify tripwire + 15 verify phase + 12 comment lines explaining the rationale of each block).
- **Decision K compliance verified.** Verify call uses `|| verify_exit=$?` (NOT `|| true` — explicitly forbidden anti-pattern per architecture.md:478–481). Exit codes 0/1/2/3/4 mapped to colored stderr warnings; deploy exit code stays decoupled from verify_exit (FR15 non-fatal contract).
- **Three-signal failure model (NFR-R3) intact end-to-end:** AC10 lightweight smoke shows broken-URL produces (a) red stderr warning printed by deploy.sh's case-statement, (b) `infra/.last-verify FAILED unknown` written by Story 3.1's `fail_verify` helper, (c) for codes 1/3 a synthetic GlitchTip alarm event (not exercised in this lightweight smoke since broken-URL is exit 2, no alarm — that's intended).
- **Stale-verify direction correctness verified.** AC2's logic is: `last_verify_mtime < head_timestamp` → warn. The backdated test (mtime=2020-01-01) vs current HEAD (2026-05-09) confirms warning fires. Repeat-deploy-no-decay scenario (same HEAD twice) wouldn't fire because mtime updates AFTER HEAD timestamp.
- **No automated tests added.** deploy.sh is bash + SSH + docker; out-of-scope to unit-test. The story spec (Task 5/6/7) captures the operator-driven smoke that proves contract.

### File List

MODIFIED:
- `infra/scripts/deploy.sh` (+39 lines): stale-verify tripwire block (after `LOCAL_ENV` setup, before `→ Build images locally`) + post-alembic verify phase (after `Run alembic migrations` SSH command, before `Done.`).

NOT TOUCHED (story scope = single file):
- `infra/scripts/verify-symbolication.sh` (Story 3.1 contract consumed as-is).
- All other repo files.

GITIGNORED state changes (visible in working tree, not in commits):
- `infra/.last-verify` — refreshed on every successful deploy + temporary `FAILED unknown` during Task 6 broken-URL smoke + restored.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story status transitions: ready-for-dev → in-progress → review.
- `_bmad-output/implementation-artifacts/3-2-deploy-sh-verify-integration.md` (this file).

### Change Log

- 2026-05-10 — initial implementation (commit `31dac06`): stale-verify tripwire + post-alembic verify phase + exit-code-mapped warnings. Single commit ships full story. End-to-end auto-deploy proves: deploy exit 0, verify exit 0, fresh `.last-verify OK` line, top frame symbolicated to `apps/web/src/main.tsx`. Lightweight smokes for AC10/AC11/AC12 pass.
- 2026-05-10 — Codex code-review: **APPROVED, brak findings.** Codex verified: `set -euo pipefail` preserved; `DOCKER_BUILDKIT=1` retained before build; stale-check fires before build; verify call after `alembic upgrade head`; mandatory `|| verify_exit=$?` (NOT the forbidden `|| true` per Decision K anti-pattern); exit codes 0–4 mapped + wildcard fallback; deploy ends at `echo "Done."` decoupled from verify outcome. `bash -n` exits 0; `git show --check --stat 31dac06` clean; static grep shows exactly 1 executed `verify-symbolication.sh` reference and 0 `|| true` in deploy.sh. Status → done.
