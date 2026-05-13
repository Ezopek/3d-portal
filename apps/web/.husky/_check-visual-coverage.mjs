#!/usr/bin/env node
/*
 * Visual Coverage Contract enforcement (Initiative 3, Story E5.14, FR14).
 *
 * Runs as part of apps/web/.husky/pre-commit. When the staged set adds a
 * new file under apps/web/src/ui/*.tsx, the same commit MUST also stage a
 * matching visual spec at apps/web/tests/visual/<basename>.spec.ts or
 * apps/web/tests/visual/<basename>-*.spec.ts.
 *
 * Rationale: prevents shipping a new interactive UI primitive without
 * open-state coverage in the visual-regression matrix. See architecture.md
 * § Initiative 3 § Decision G.
 *
 * Edge case: the rule applies to ADDED files (`--diff-filter=A`), not
 * MODIFIED files. Modifying an existing primitive does not require a new
 * spec (the existing one continues to cover it). This is intentional —
 * we are gating ADDITIONS, not edits.
 *
 * Subdirectories under apps/web/src/ui/ (e.g. `apps/web/src/ui/custom/`)
 * are excluded — `*.tsx` at the top level only. Custom/library
 * wrappers under sub-directories don't necessarily map to a primitive
 * worth open-state-testing on their own (CardCarousel, for example, is
 * a composition; it's tested via its consumer flows). If this exclusion
 * proves wrong in practice, tighten the regex during a Phase C-prevention
 * retrospective.
 */

import { execSync } from "node:child_process";
import { basename } from "node:path";
import process from "node:process";

const stagedOutput = execSync(
  "git diff --cached --name-only --diff-filter=A",
  { encoding: "utf8" },
);
const stagedPaths = stagedOutput.split("\n").filter(Boolean);

const newUiPrimitives = stagedPaths.filter((p) =>
  /^apps\/web\/src\/ui\/[^/]+\.tsx$/i.test(p),
);

if (newUiPrimitives.length === 0) process.exit(0);

const allStagedAm = execSync(
  "git diff --cached --name-only --diff-filter=AM",
  { encoding: "utf8" },
);
const stagedAmPaths = allStagedAm.split("\n").filter(Boolean);

const missing = [];
for (const primitivePath of newUiPrimitives) {
  const stem = basename(primitivePath, ".tsx");
  const stemEsc = stem.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
  const specRegex = new RegExp(
    `^apps/web/tests/visual/${stemEsc}(?:-[^/]+)?\\.spec\\.ts$`,
    "i",
  );
  const matchedSpec = stagedAmPaths.find((p) => specRegex.test(p));
  if (!matchedSpec) missing.push({ primitive: primitivePath, stem });
}

if (missing.length > 0) {
  console.error("[visual-coverage-contract] REJECTED");
  console.error(
    `  ${newUiPrimitives.length} new UI primitive(s); ${missing.length} missing matching visual spec.`,
  );
  for (const { primitive, stem } of missing) {
    console.error(
      `    - ${primitive} — needs apps/web/tests/visual/${stem}.spec.ts (or ${stem}-<variant>.spec.ts)`,
    );
  }
  console.error(
    "  Per Initiative 3 / Epic 5 / Story E5.14 (FR14). See _bmad-output/planning-artifacts/architecture.md § Decision G.",
  );
  process.exit(1);
}

console.log(
  `[visual-coverage-contract] OK — ${newUiPrimitives.length} new UI primitive(s) have matching specs.`,
);
