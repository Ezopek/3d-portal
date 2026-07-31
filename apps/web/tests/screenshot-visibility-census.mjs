#!/usr/bin/env node
/* global process */
/*
 * Story 54.2 / AC-6 (Decision D-2) — per-SCREENSHOT `toBeVisible()` census.
 *
 * WHY THIS EXISTS
 * ---------------
 * `epics.md:4595` (epic:45 / epic:46 TEST-AUTHORING) states the rule per
 * screenshot: "every screenshot preceded by an explicit `toBeVisible()`".
 * Every figure circulating before this script was a per-FILE grep, which is
 * wrong in BOTH directions:
 *   - false negative: a file with `toBeVisible` in test 1 and none in test 5
 *     counts as covered (`settings-2fa.spec.ts` has 6 screenshots and zero
 *     `toBeVisible` anywhere, yet a file-level count records it as "1 spec");
 *   - false positive: a file whose only visibility proof lives in a helper
 *     counts as uncovered.
 * Story 54.2 § 2 V-5 recorded three mutually incompatible file-level figures
 * (10 / 32, and 20 from an earlier session). This script SUPERSEDES all three.
 *
 * ATTRIBUTION RULE (AC-6 / VS-4 requires this to be stated explicitly)
 * -------------------------------------------------------------------
 * The unit is an OCCURRENCE = (screenshot call site, the `test()` that reaches
 * it). A `toHaveScreenshot` call written directly in a test body is one
 * occurrence. A call written inside a file-local helper is one occurrence PER
 * CALLING TEST — `filter-ribbon-selects-open.spec.ts` makes exactly one
 * `toHaveScreenshot` call, inside a helper, reached by three tests, so it
 * contributes 3 occurrences (and 12 baselines once the 4 Playwright projects
 * are multiplied in; baselines are NOT what this script counts).
 *
 * An occurrence is COVERED when a `toBeVisible()` assertion is evaluated
 * before it on the same path. Three ways that can happen, all recognised:
 *   1. `toBeVisible()` earlier in the same function body;
 *   2. `toBeVisible()` inside a file-local helper that is CALLED earlier in
 *      the same body (resolved one level deep, transitively);
 *   3. for a helper-hosted screenshot, `toBeVisible()` anywhere in the calling
 *      test before the helper call.
 * Everything is source-position ordered, so a `toBeVisible()` that runs AFTER
 * the screenshot does not count.
 *
 * The parse is a real TypeScript AST (`typescript` is already a devDependency
 * via `tsc -b`), not a regex sweep — a regex cannot tell a helper body from a
 * test body, and that distinction is the whole point of the rule.
 *
 * USAGE
 * -----
 *   node tests/screenshot-visibility-census.mjs            # human summary
 *   node tests/screenshot-visibility-census.mjs --json     # machine output
 *   node tests/screenshot-visibility-census.mjs --strict   # exit 1 if any
 *                                                          # occurrence is
 *                                                          # uncovered
 */

import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const HERE = dirname(fileURLToPath(import.meta.url));
const VISUAL_DIR = resolve(HERE, "visual");
const REPO_WEB = resolve(HERE, "..");

/** The strict rule from `epics.md:4595`. Deliberately just this one matcher. */
const VISIBILITY_MATCHER = "toBeVisible";
/**
 * Weaker proofs that are NOT the rule but are worth reporting, so a reviewer
 * can tell "no proof at all" from "proof of a different shape".
 */
const WEAK_MATCHERS = new Set([
  // `locator.waitFor({ state: "visible" })` — a real visibility wait, but not
  // the assertion the rule names; 105 call sites use it in this suite.
  "waitFor",
  "waitForSelector",
  "toBeAttached",
  "toHaveText",
  "toContainText",
  "toHaveCount",
  "toBeChecked",
  "toHaveScreenshot",
]);

function specFiles() {
  return readdirSync(VISUAL_DIR)
    .filter((f) => f.endsWith(".spec.ts"))
    .sort()
    .map((f) => join(VISUAL_DIR, f));
}

/** The callee name of a call expression, e.g. `a.b.toBeVisible()` -> "toBeVisible". */
function calleeName(node) {
  const e = node.expression;
  if (ts.isIdentifier(e)) return e.text;
  if (ts.isPropertyAccessExpression(e)) return e.name.text;
  return null;
}

/** Root identifier of a call chain, e.g. `test.describe(...)` -> "test". */
function calleeRoot(node) {
  let e = node.expression;
  while (ts.isPropertyAccessExpression(e) || ts.isCallExpression(e)) {
    e = ts.isCallExpression(e) ? e.expression : e.expression;
  }
  return ts.isIdentifier(e) ? e.text : null;
}

function isFunctionLike(node) {
  return (
    ts.isFunctionDeclaration(node) ||
    ts.isFunctionExpression(node) ||
    ts.isArrowFunction(node) ||
    ts.isMethodDeclaration(node)
  );
}

/**
 * Collect, per file:
 *   - tests:   { name, body, pos, end }  (the callback of `test(...)`)
 *   - helpers: Map<name, { body, pos, end }> for file-scope functions
 */
function collectScopes(sf) {
  const tests = [];
  const helpers = new Map();
  const hooks = [];

  function visit(node) {
    if (ts.isCallExpression(node) && calleeRoot(node) === "test") {
      const name = calleeName(node);
      // `test.beforeEach(...)` always runs before every test in its scope, so
      // a `toBeVisible()` in it does precede the screenshot.
      if (name === "beforeEach" || name === "beforeAll") {
        const fn = node.arguments.find((a) => isFunctionLike(a));
        if (fn) hooks.push({ body: fn, pos: fn.getStart(sf), end: fn.getEnd() });
      }
      // `test(...)`, `test.only(...)`, `test.fixme(...)` declare a test.
      // `test.describe(...)`/`test.beforeEach(...)` do not.
      const isDecl =
        name === "test" || name === "only" || name === "fixme" || name === "skip";
      if (isDecl) {
        const [titleArg, fnArg] = node.arguments;
        const fn = fnArg && isFunctionLike(fnArg) ? fnArg : null;
        if (fn) {
          tests.push({
            title:
              titleArg && ts.isStringLiteralLike(titleArg)
                ? titleArg.text
                : "<computed>",
            body: fn,
            pos: fn.getStart(sf),
            end: fn.getEnd(),
          });
        }
      }
    }
    if (ts.isFunctionDeclaration(node) && node.name && node.body) {
      helpers.set(node.name.text, { body: node, pos: node.getStart(sf), end: node.getEnd() });
    }
    if (ts.isVariableDeclaration(node) && node.name && ts.isIdentifier(node.name)) {
      const init = node.initializer;
      if (init && isFunctionLike(init)) {
        helpers.set(node.name.text, { body: init, pos: init.getStart(sf), end: init.getEnd() });
      }
    }
    ts.forEachChild(node, visit);
  }

  visit(sf);
  return { tests, helpers, hooks };
}

/** All call expressions inside `node`, with their source position. */
function callsIn(sf, node) {
  const out = [];
  function visit(n) {
    if (ts.isCallExpression(n)) {
      out.push({ name: calleeName(n), root: calleeRoot(n), pos: n.getStart(sf), node: n });
    }
    ts.forEachChild(n, visit);
  }
  ts.forEachChild(node, visit);
  return out;
}

/**
 * Does `scope` prove visibility strictly before `beforePos`?
 * Recurses into file-local helpers called before that position.
 */
function provesVisibility(sf, scope, beforePos, helpers, matcher, seen = new Set()) {
  for (const call of callsIn(sf, scope)) {
    if (call.pos >= beforePos) continue;
    if (call.name === matcher) return { proved: true, via: "inline" };
    // A helper invoked earlier can carry the proof.
    if (call.name && helpers.has(call.name) && !seen.has(call.name)) {
      seen.add(call.name);
      const helper = helpers.get(call.name);
      const inner = provesVisibility(sf, helper.body, Number.MAX_SAFE_INTEGER, helpers, matcher, seen);
      if (inner.proved) return { proved: true, via: `helper:${call.name}` };
    }
  }
  return { proved: false, via: null };
}

/** Which scope (test or helper) most tightly encloses `pos`. */
function enclosingScope(pos, tests, helpers) {
  let best = null;
  for (const t of tests) {
    if (pos >= t.pos && pos <= t.end) {
      if (!best || t.pos > best.pos) best = { kind: "test", name: t.title, ...t };
    }
  }
  for (const [name, h] of helpers) {
    if (pos >= h.pos && pos <= h.end) {
      if (!best || h.pos > best.pos) best = { kind: "helper", name, ...h };
    }
  }
  return best;
}

/** Every test that reaches `helperName`, directly or through other helpers. */
function testsReaching(sf, helperName, tests, helpers) {
  const reached = [];
  for (const t of tests) {
    const stack = [{ scope: t.body, limit: Number.MAX_SAFE_INTEGER }];
    const seen = new Set();
    let found = null;
    while (stack.length > 0 && !found) {
      const { scope } = stack.pop();
      for (const call of callsIn(sf, scope)) {
        if (call.name === helperName) {
          found = { callPos: call.pos, direct: scope === t.body };
          break;
        }
        if (call.name && helpers.has(call.name) && !seen.has(call.name)) {
          seen.add(call.name);
          stack.push({ scope: helpers.get(call.name).body });
        }
      }
    }
    if (found) reached.push({ test: t, callPos: found.callPos });
  }
  return reached;
}

function analyseFile(file) {
  const src = readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true);
  const { tests, helpers, hooks } = collectScopes(sf);
  const rel = relative(REPO_WEB, file);
  const occurrences = [];
  // A `beforeEach` proof covers every screenshot in its file.
  const hookProof = hooks.some(
    (h) =>
      provesVisibility(sf, h.body, Number.MAX_SAFE_INTEGER, helpers, VISIBILITY_MATCHER).proved,
  )
    ? { proved: true, via: "beforeEach" }
    : { proved: false, via: null };

  for (const call of callsIn(sf, sf)) {
    if (call.name !== "toHaveScreenshot") continue;
    const pos = call.pos;
    const { line } = sf.getLineAndCharacterOfPosition(pos);
    const scope = enclosingScope(pos, tests, helpers);

    if (!scope) {
      occurrences.push({
        file: rel,
        line: line + 1,
        host: "file-scope",
        test: "<none>",
        covered: false,
        via: null,
        weak: null,
      });
      continue;
    }

    if (scope.kind === "test") {
      const inline = provesVisibility(sf, scope.body, pos, helpers, VISIBILITY_MATCHER);
      const proof = inline.proved ? inline : hookProof;
      occurrences.push({
        file: rel,
        line: line + 1,
        host: "test-body",
        test: scope.name,
        covered: proof.proved,
        via: proof.via,
        weak: proof.proved ? null : weakProof(sf, scope.body, pos, helpers),
      });
      continue;
    }

    // Helper-hosted: one occurrence per calling test (VS-4).
    const callers = testsReaching(sf, scope.name, tests, helpers);
    const helperInline = provesVisibility(sf, scope.body, pos, helpers, VISIBILITY_MATCHER);
    const helperProof = helperInline.proved ? helperInline : hookProof;
    if (callers.length === 0) {
      occurrences.push({
        file: rel,
        line: line + 1,
        host: `helper:${scope.name}`,
        test: "<unreached>",
        covered: helperProof.proved,
        via: helperProof.via,
        weak: helperProof.proved ? null : weakProof(sf, scope.body, pos, helpers),
      });
    }
    for (const caller of callers) {
      const callerProof = helperProof.proved
        ? helperProof
        : provesVisibility(sf, caller.test.body, caller.callPos, helpers, VISIBILITY_MATCHER);
      occurrences.push({
        file: rel,
        line: line + 1,
        host: `helper:${scope.name}`,
        test: caller.test.title,
        covered: callerProof.proved,
        via: callerProof.via,
        weak: callerProof.proved
          ? null
          : weakProof(sf, caller.test.body, caller.callPos, helpers),
      });
    }
  }

  return { file: rel, occurrences, callSites: new Set(occurrences.map((o) => o.line)).size };
}

function weakProof(sf, scope, beforePos, helpers) {
  for (const m of WEAK_MATCHERS) {
    if (m === "toHaveScreenshot") continue;
    const r = provesVisibility(sf, scope, beforePos, helpers, m);
    if (r.proved) return m;
  }
  return null;
}

const files = specFiles().map(analyseFile);
const all = files.flatMap((f) => f.occurrences);
const uncovered = all.filter((o) => !o.covered);
const callSiteTotal = files.reduce((n, f) => n + f.callSites, 0);

const report = {
  generated_by: "apps/web/tests/screenshot-visibility-census.mjs",
  unit: "occurrence = (toHaveScreenshot call site) x (test that reaches it)",
  matcher: VISIBILITY_MATCHER,
  spec_files_scanned: files.length,
  spec_files_with_screenshots: files.filter((f) => f.callSites > 0).length,
  call_sites: callSiteTotal,
  occurrences: all.length,
  covered: all.length - uncovered.length,
  uncovered: uncovered.length,
  uncovered_with_weak_proof: uncovered.filter((o) => o.weak !== null).length,
  uncovered_with_no_proof: uncovered.filter((o) => o.weak === null).length,
  uncovered_detail: uncovered.map((o) => ({
    file: o.file,
    line: o.line,
    host: o.host,
    test: o.test,
    weak_proof: o.weak,
  })),
};

if (process.argv.includes("--json")) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} else {
  process.stdout.write(
    [
      "Story 54.2 / AC-6 — per-screenshot toBeVisible() census",
      `  unit           : ${report.unit}`,
      `  matcher        : ${report.matcher}()`,
      `  spec files     : ${report.spec_files_scanned} scanned, ${report.spec_files_with_screenshots} with >=1 screenshot`,
      `  call sites     : ${report.call_sites}`,
      `  occurrences    : ${report.occurrences}`,
      `  covered        : ${report.covered}`,
      `  UNCOVERED      : ${report.uncovered}` +
        ` (${report.uncovered_with_weak_proof} with a weaker visibility wait,` +
        ` ${report.uncovered_with_no_proof} with no proof of any shape)`,
      "",
      ...(uncovered.length > 0
        ? [
            "Uncovered occurrences:",
            ...uncovered.map(
              (o) =>
                `  ${o.file}:${o.line}  [${o.host}]  "${o.test}"` +
                (o.weak ? `  (weak proof: ${o.weak})` : "  (no proof of any shape)"),
            ),
            "",
          ]
        : []),
    ].join("\n"),
  );
}

if (process.argv.includes("--strict") && uncovered.length > 0) process.exit(1);
