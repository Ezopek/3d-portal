#!/usr/bin/env node
/*
 * Baseline Acceptance Gate (Initiative 3, Story E5.13, FR13).
 *
 * Runs as part of apps/web/.husky/pre-commit. Reads:
 *   - Staged file list via `git diff --cached --name-only --diff-filter=AM`
 *   - In-flight commit message via .git/COMMIT_EDITMSG (created by git's
 *     commit-tree pipeline when a commit-msg hook would run; pre-commit
 *     runs BEFORE the commit message is finalized — at this point the
 *     commit message is in MERGE_MSG or COMMIT_EDITMSG depending on the
 *     invocation. We try both, falling back to reading the message via
 *     `git diff --cached --name-only` only if neither file exists.)
 *
 * If any staged file matches apps/web/tests/visual/__snapshots__/**\/*.png,
 * the commit message MUST contain one line per changed PNG basename:
 *   baseline-reviewed: <basename>, <reviewer>, <YYYY-MM-DD>
 *
 * The hook runs BEFORE the user has finalized the commit message, so we
 * support two paths:
 *   - $HUSKY_GIT_PARAMS or argv contains the message path (commit-msg-style)
 *   - Otherwise we accept either .git/COMMIT_EDITMSG (set by git pre-commit
 *     when -m was used) or fall back to soft-rejecting with a clear hint.
 *
 * Real-world usage: developers run `git commit -m "..."` with the
 * baseline-reviewed lines IN the -m message. The git pre-commit hook does
 * NOT yet see that message; it only sees the staged tree. So this check
 * cannot verify the message at pre-commit time perfectly. Two workable
 * paths:
 *   (a) Use commit-msg hook instead of pre-commit for message parsing.
 *   (b) Have pre-commit only WARN about baseline regen + a separate
 *       commit-msg hook enforces the message-line presence.
 *
 * This script implements (b)'s pre-commit half: it emits an informational
 * message naming the changed PNG basenames and reminding the operator that
 * the commit-msg hook (apps/web/.husky/commit-msg) will enforce the
 * sign-off lines. The commit-msg hook does the actual rejection. Both run
 * automatically when core.hooksPath points at apps/web/.husky/.
 *
 * See architecture.md § Initiative 3 § Decision E + E5.13 spec.
 */

import { execSync } from "node:child_process";
import { basename } from "node:path";
import process from "node:process";

const stagedOutput = execSync(
  "git diff --cached --name-only --diff-filter=AM",
  { encoding: "utf8" },
);
const stagedPaths = stagedOutput.split("\n").filter(Boolean);

const stagedPngs = stagedPaths.filter((p) =>
  /^apps\/web\/tests\/visual\/__snapshots__\/.+\.png$/i.test(p),
);

if (stagedPngs.length === 0) process.exit(0);

const pngBasenames = stagedPngs.map((p) => basename(p));

// Commit-msg hook invocation passes the message file path as argv[2].
// Pre-commit invocation does NOT — and .git/COMMIT_EDITMSG at that point
// still holds the PREVIOUS commit's message (git updates it after pre-commit
// fires). So we can only enforce reliably in commit-msg mode. Pre-commit
// emits an informational warning naming the staged PNGs and exits 0;
// commit-msg does the actual rejection.
const commitMsgPath = process.argv[2];
if (!commitMsgPath) {
  console.warn(
    "[baseline-acceptance-gate] INFO: pre-commit detected " +
      `${stagedPngs.length} staged baseline PNG(s). ` +
      "Final enforcement happens in commit-msg hook. Required sign-off format per PNG:",
  );
  for (const b of pngBasenames) {
    console.warn(`    baseline-reviewed: ${b}, <reviewer>, YYYY-MM-DD`);
  }
  process.exit(0);
}

let commitMsg = "";
try {
  const fs = await import("node:fs");
  commitMsg = fs.readFileSync(commitMsgPath, "utf8");
} catch (err) {
  console.error(
    `[baseline-acceptance-gate] ERROR: cannot read commit message at ${commitMsgPath}: ${err.message}`,
  );
  process.exit(1);
}

const missing = [];
for (const b of pngBasenames) {
  // Match line: `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD`
  // Anchored to line start. Reviewer name may contain whitespace.
  const re = new RegExp(
    `^baseline-reviewed:\\s+${b.replace(/[.+?^${}()|[\]\\]/g, "\\$&")}\\s*,\\s*.+\\s*,\\s*\\d{4}-\\d{2}-\\d{2}\\s*$`,
    "m",
  );
  if (!re.test(commitMsg)) missing.push(b);
}

if (missing.length > 0) {
  console.error("[baseline-acceptance-gate] REJECTED");
  console.error(
    `  ${stagedPngs.length} staged baseline PNG(s), ${missing.length} missing sign-off line(s).`,
  );
  console.error("  Add to commit message (one line per PNG):");
  for (const b of missing) {
    console.error(`    baseline-reviewed: ${b}, <reviewer>, YYYY-MM-DD`);
  }
  console.error(
    "  Per Initiative 3 / Epic 5 / Story E5.13 (FR13). See _bmad-output/planning-artifacts/architecture.md § Decision E.",
  );
  process.exit(1);
}

console.log(
  `[baseline-acceptance-gate] OK — ${stagedPngs.length} PNG(s) signed off.`,
);
