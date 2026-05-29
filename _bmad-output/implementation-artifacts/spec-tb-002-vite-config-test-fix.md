---
title: 'TB-002 vite-config.test.ts file-level loading error'
type: 'bugfix'
created: '2026-05-11'
status: 'done'
route: 'one-shot'
---

# TB-002 vite-config.test.ts file-level loading error

## Intent

**Problem:** `apps/web/src/vite-config.test.ts` fails at module-load time with `TypeError: paths[0] must be string` from `unplugin/dist/index.mjs:873` under Node 18.19.1. Both `it` blocks never register; `vitest` reports "Test Files 1 failed | 79 passed (80)" without ever running the file's assertions. Root cause: unplugin evaluates `path.resolve(import.meta.dirname, ...)` at module top-level; `import.meta.dirname` is only defined in Node ≥ 20.11. Host runs Node 18 even though `package.json#engines.node` pins `>=20.11` (soft npm constraint, warn-only). Whenever the test fails, the operator sees a red file in `npm run test` that masks any other regression — confirmed 7× during the 2026-05-10 UI-review batch (frequency-within-session rule).

**Approach:** Stub the two direct unplugin transitives imported by `vite.config.ts` with `vi.mock` before importing the live config. Production `vite.config.ts` is unchanged. The assertions still verify plugin name + LAST position in `flattened plugins[]`, against the real `vite.config.ts` plugin ordering — drift detection on plugin reordering is preserved.

## Suggested Review Order

1. [Diff — the only changed file](../../apps/web/src/vite-config.test.ts) — read the comment block first; it documents WHY two stubs (not one) and what to do if the test regresses with a third unplugin transitive.
2. [Triage backlog entry → Declined/done](../triage-backlog.md) — TB-002 row, now closed with commit reference.
3. [Sprint status `last_updated`](./sprint-status.yaml) — line carries the one-line summary of this work.

Adversarial review (`feature-dev:code-reviewer` subagent, no conversation context) returned 3 PATCH findings, 0 HALT, 0 reject-from-reviewer. All 3 patches applied in the same working tree before commit:

- Sentry stub aligned to `() => [{ name: "sentry-vite-plugin" }]` (production shape is `Plugin[]`) — eliminates future-false-negative if Sentry adds a second internal plugin.
- Comment expanded with breadcrumb for next dev: "If this test starts failing again under a similar TypeError, check `vite.config.ts` for newly-added plugins that depend transitively on `unplugin` and add a matching `vi.mock` here."
- Reworded "ordering of named-export resolution is not guaranteed" → "which transitive evaluates first is an implementation detail of the package graph at any given version."

Follow-up surfaced (NOT in this fix's scope, deliberate per "no silent scope creep"): host runs Node 18.19.1 vs `engines.node >=20.11`. `nvm use 22` on the dev box would address the proximate cause, but stubbing is defensive-in-depth and protects fresh-Docker / contributor-box scenarios too. Operator's call whether to add a follow-up TB.
