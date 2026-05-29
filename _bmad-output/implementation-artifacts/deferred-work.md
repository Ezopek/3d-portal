# Deferred Work — quick-dev review backlog

Findings from BMAD reviews that are real but **not blocking** the current story. Each entry has enough context that a future promotion to its own quick-dev story (or absorbing into a related one) can happen without re-deriving context.

---

## Deferred from: quick-dev review of deploy-skip-gate-range (2026-05-16)

Source: 3 BMAD subagent reviews + 1 Codex review of `feat/deploy-skip-gate-range` (commits `bc324e2` + `0745209`). All findings here are **defensive robustness improvements** on top of a spec-compliant implementation — the Acceptance Auditor confirmed all ACs are met. Two P1s from that batch were patched in-flight (`0745209`: SHA-format validation).

### DSG-1 — `2>/dev/null` on state-file write swallows real errno

**Source:** Blind Hunter [P2]

**Where:** `infra/scripts/deploy.sh` — the state-file write block before final `echo "Done."`:

```bash
echo "$deploy_sha_full" > "$last_deploy_path" 2>/dev/null || \
  echo "[deploy-skip-gate] WARN: failed to update $last_deploy_path (non-fatal)" >&2
```

**Problem:** `2>/dev/null` suppresses the actual `bash` error message (permission denied, disk full, etc.). The fallback WARN fires but operator gets no errno hint. Next run re-deploys because the state file wasn't updated, which is correct fail-direction — but diagnosing why takes longer than it should.

**Fix sketch:** Capture the error: `if ! { echo "$deploy_sha_full" > "$last_deploy_path"; } 2>/tmp/dsg-write-err; then echo "[deploy-skip-gate] WARN: failed to update ... ($(cat /tmp/dsg-write-err))" >&2; fi`. Or just drop `2>/dev/null` so bash's error reaches stderr naturally before the WARN.

### DSG-2 — `last_short` lacks a defensive fallback (mirror of `head_short`'s `|| echo unknown`)

**Source:** Blind Hunter [P3]

**Where:** `infra/scripts/deploy.sh`, gate block:

```bash
head_short="$(... || echo unknown)"  # has fallback
last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha")"  # NO fallback
```

**Problem:** If `git rev-parse --short` somehow fails for the validated `last_deploy_sha` (extremely unlikely — we already passed `rev-parse --verify`, so the object resolves), `set -e` would kill the script. Asymmetric defensive style.

**Fix sketch:** `last_short="$(git -C "$REPO_DIR" rev-parse --short "$last_deploy_sha" 2>/dev/null || echo "${last_deploy_sha:0:7}")"`.

### DSG-3 — State-file write is non-atomic (kill-mid-write → zero-byte file)

**Source:** Blind Hunter [P3]

**Where:** Same write block as DSG-1.

**Problem:** `echo > file` opens the file (truncating to zero) BEFORE writing the payload. SIGKILL between truncate and write leaves an empty file. Next run hits the new (post-fix-up) SHA-format check → empty fails regex → WARN+deploy. Safe direction, but the state is lost for the next legitimate skip.

**Fix sketch:** `printf '%s\n' "$deploy_sha_full" > "$last_deploy_path.tmp" && mv "$last_deploy_path.tmp" "$last_deploy_path"`. The `mv` is atomic on the same filesystem.

### DSG-4 — Leading-whitespace commit subjects bypass the gate

**Source:** Edge Case Hunter [P2]

**Where:** `infra/scripts/deploy.sh`, the per-subject match loop in the gate.

**Problem:** A commit subject like `" docs: typo"` (leading space) is non-empty, does not match `docs:` (no leading space in the prefix), so `all_skip=false` → deploy. Safe-side failure, but technically the subject reflects a docs-only change.

**Fix sketch:** Either trim leading whitespace before match: `subject="${subject#"${subject%%[![:space:]]*}"}"`, or document the case as "intentional — leading-whitespace subjects are non-conformant and always deploy."

**Why deferred:** Probably not actually encountered in practice; current `set -euo pipefail` plus `git log --format=%s` consistently produces clean subjects.

### DSG-5 — Concurrent `deploy.sh` invocations: TOCTOU on `.last-deploy-sha`

**Source:** Edge Case Hunter [P2]

**Where:** Conceptual; affects both the read-and-decide block and the write-on-success block.

**Problem:** Two operators (or operator + scheduled task) running `deploy.sh` simultaneously: both read the same stale SHA, both pass the gate, both deploy, both write at end — last writer wins. The state file may end up reflecting the wrong "latest deploy".

**Why deferred:** 3d-portal is single-operator + single-host. The current `feedback_auto_deploy_dev.md` flow has no concurrent-invocation pattern. If a future epic introduces autonomous scheduled deploys alongside operator runs, this becomes a real concern.

**Fix sketch:** `flock -n /tmp/3d-portal-deploy.lock` wrap on the whole script (or at minimum on the gate-read + state-write windows).

---

## Promoted to story / absorbed

_(none yet)_

---

## Deferred from: quick-dev review of tb-015-measure-clear-clickable (2026-05-21)

Source: 3 BMAD subagent reviews of TB-015 fix (pointer-events-auto on MeasureSummary footer div). Spec fully satisfied per Acceptance Auditor. All other P2/P3 findings either patched in-flight (parentElement fragility, row-delete selector specificity, inline-host coverage) or rejected as noise. ONE finding warrants a parking entry.

### TB-015-D1 — Touch / mobile pointer-events propagation inside backdrop-blur ancestor

**Source:** Edge Case Hunter [P3]

**Where:** `apps/web/src/modules/catalog/components/viewer3d/controls/MeasureSummary.tsx:42` — the outer `<div className="rounded-md border border-border bg-card/85 backdrop-blur-md text-xs">` host of the summary panel.

**Hypothesis:** iOS Safari has documented edge cases where `pointer-events: none` combined with `backdrop-filter: blur(...)` and certain stacking contexts can swallow touch events differently from desktop. Our TB-015 fix is verified for desktop via vitest + future agent-browser; mobile-light (touch) verification is included in the visual-verification gate, but iOS Safari specifically isn't in our 4-project Playwright matrix (we use Chromium-based Pixel 5 emulation, not WebKit). This means a real-iOS-Safari regression would not be caught by automated gates today.

**Why deferred (not promoted):**
- The fix mirrors the existing per-row `<li>` pattern (`MeasureSummary.tsx:50`) which has been shipped and used on mobile catalog visits for months without reports. If `backdrop-blur` + `pointer-events-none` were a real iOS Safari issue, per-row × delete would have surfaced it long before TB-015.
- The risk is bounded (one specific browser engine, edge case, mitigated by the same pattern already in production).
- Promoting now would scope-creep TB-015's "one-line fix" into a multi-browser audit — premature.

**Trigger to promote:** any operator report of "Wyczyść pomiary doesn't work on my iPhone" post-TB-015 deploy, OR formal addition of WebKit / iOS Safari to the visual-regression Playwright matrix as a project initiative.

**Code map:** `MeasureSummary.tsx:42` (outer host with backdrop-blur), `MeasureSummary.tsx:82` (the new pointer-events-auto footer), `Viewer3DModal.tsx:390` (the pointer-events-none wrapper that the fix neutralizes).

---

## Declined / done

_(none yet)_
