---
title: 'Vitest global afterEach(cleanup) — kill the per-file boilerplate gotcha'
type: 'chore'
created: '2026-05-10'
status: 'done'
route: 'one-shot'
---

# Vitest global afterEach(cleanup) — kill the per-file boilerplate gotcha

## Intent

**Problem:** `apps/web/vitest.config.ts` runs with `globals: false`, so `@testing-library/react` cannot register its own `afterEach(cleanup)` automatically. Every new component test file that calls `render()` more than once must remember to add `afterEach(cleanup)` itself, or the second `it` block fails with `Found multiple elements`. This gotcha hit 3× in the 2026-05-10 UI-review batch (`login.test.tsx`, `OperationalNotesTab.test.tsx`, `ConfirmDialog.test.tsx`) and is documented as memory `feedback_vitest_manual_cleanup.md`. Memory keeps me safe; a global setup file makes the project itself safe.

**Approach:** Add `apps/web/vitest.setup.ts` that registers `afterEach(cleanup)` once globally, and wire it via `setupFiles: ["./vitest.setup.ts"]` in `vitest.config.ts`. Existing per-file `afterEach(cleanup)` calls are now redundant but kept in place — `cleanup()` is idempotent (empty-mount no-op), and bulk-removing the boilerplate from ~15 test files is out of scope for this quick-dev. New test files written from this point on can drop the boilerplate. Action item AI-6 / decision D4 from the UI-review retrospective.

## Suggested Review Order

**The change itself**

- The new global hook — single `afterEach(cleanup)` registration that fires for every test in every file.
  [`vitest.setup.ts:9-11`](../../apps/web/vitest.setup.ts#L9-L11)

- Wiring point — one-line `setupFiles` entry in the existing test config.
  [`vitest.config.ts:36`](../../apps/web/vitest.config.ts#L36)

**Adversarial-review patch**

- TypeScript coverage gap caught by the cynical review subagent: the new setup file was outside every tsconfig include, so `tsc -b` would have skipped type-checking it. Fix: add to `tsconfig.node.json` alongside `vite.config.ts`. Bonus: `vitest.config.ts` was also missing — included while in the neighbourhood.
  [`tsconfig.node.json:12`](../../apps/web/tsconfig.node.json#L12)

**Verification (no test changes needed)**

- Full vitest suite continues to pass at 311/311 with the global hook active, confirming idempotent double-cleanup with the existing per-file `afterEach(cleanup)` calls. `vite-config.test.ts` pre-existing fail unchanged (TB-002, separate triage candidate).
  Verified locally: `cd apps/web && npx vitest run` → `Test Files 1 failed | 79 passed (80) | Tests 311 passed (311)`.
