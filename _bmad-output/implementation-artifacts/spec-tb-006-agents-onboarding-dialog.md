---
title: 'TB-006 admin agents-onboarding dialog'
type: 'feature'
created: '2026-05-11'
status: 'done'
route: 'one-shot'
---

# TB-006 admin agents-onboarding dialog

## Intent

**Problem:** Admin who wants to onboard a fresh AI agent (Claude, Codex, future LLMs) has to remember the three-line bootstrap (curl runbook + curl OpenAPI + path to credentials file). Documented in `docs/agents-add-model-runbook.md` and elsewhere — none of those locations are convenient at onboarding-time. Friction grows in multi-month-quiet repos when admin forgets where the bootstrap lives.

**Approach:** Surface the bootstrap from the SPA. Admin-only DropdownMenuItem "For agents / Dla agentów" in the existing UserMenu opens a Dialog containing three labeled copy-blocks (runbook fetch, OpenAPI fetch, credentials file path) + two outbound links (full runbook, OpenAPI Swagger). Modal over `/admin/agents` route because (a) no other admin routes exist, (b) smaller visual surface, (c) no routing change required. Each copy button uses `navigator.clipboard.writeText` + sonner toast for success/error feedback.

## Design decisions (Ezop's choices: 1a / 2β / 3β / 4β)

- **Placement (1):** admin user-menu entry (highest discoverability for target role).
- **Copy mechanism (2):** Copy button per block (one-click vs select+Ctrl+C friction).
- **Fingerprint live-check panel (3):** out-of-scope, deferred (duplicates `infra/.last-verify-runbook` post-deploy guard).
- **i18n (4):** full PL i18n on surrounding prose + button labels; command strings stay as literal EN text.

## Files

- [`apps/web/src/shell/AgentsInfoDialog.tsx`](../../apps/web/src/shell/AgentsInfoDialog.tsx) — new component; Dialog primitive + 3× `CopyableBlock` + 2× outbound links. Hard-coded prod URLs (commented WHY).
- [`apps/web/src/shell/UserMenu.tsx`](../../apps/web/src/shell/UserMenu.tsx) — `isAdmin` from `useAuth()` + new admin-only `DropdownMenuItem` + `useState(agentsDialogOpen)` controlling the dialog; `<AgentsInfoDialog>` mounted only under admin gate.
- [`apps/web/src/shell/UserMenu.test.tsx`](../../apps/web/src/shell/UserMenu.test.tsx) — 3 vitest cases (member-no-entry / admin-sees-and-opens / clipboard-success-toast) using **fetch-level mock** per `project-context.md` rule (no `vi.mock('@/lib/api')`).
- [`apps/web/src/locales/en.json` + `pl.json`](../../apps/web/src/locales/en.json) — 14 new keys (11 base + 3 per-block aria-labels post-review).
- [`apps/web/tests/visual/agents-info-dialog.spec.ts`](../../apps/web/tests/visual/agents-info-dialog.spec.ts) — Playwright 2 specs (menu-open / dialog-rendered) **scoped to popup / dialog element** (not fullPage; catalog background isn't stubbed and shouldn't affect snapshots).
- [`__snapshots__/agents-info-dialog.spec.ts/*.png`](../../apps/web/tests/visual/__snapshots__/agents-info-dialog.spec.ts/) — 8 baselines (4 projects × 2 specs).

## Out-of-band: host Node upgrade (operator-authorized)

During TB-006 visual regression generation, Playwright's webServer failed under host Node 18.19.1 (`import.meta.dirname` undefined in `unplugin/dist/index.mjs:873` — TB-002 follow-up surfacing in production rather than just vitest). Ezop authorized full upgrade (`Node 18 możesz całkowicie wywalić`). Path B: NodeSource Node 22 LTS → installed `nodejs 22.22.2-1nodesource1`, replaced Ubuntu's 18.19.1. `npm 10.9.7` bundled. `apps/web/node_modules/` reinstalled clean under new ABI. **All 318 vitest tests + Playwright `npm run dev`-backed tests now run cleanly without the TB-002 mock fallback path.** TB-002 stubs in `vite-config.test.ts` remain as defense-in-depth (fresh-Docker / contributor-box scenarios).

## Adversarial review summary

`feature-dev:code-reviewer` (no conversation context) returned 0×P0 + 3×P1 + 1×P2 + 1×P3. All P1 + P2 applied:

- **P1 #1** (88) — three Copy buttons had identical visible text AND identical `aria-label` ("Copy") → screen-reader hears "Copy, Copy, Copy" with no context. Fix: split `buttonLabel` (visible "Copy") from `ariaLabel` (per-block descriptive). Added 3 new i18n keys: `agents.dialog.copy_runbook_aria` / `_openapi_aria` / `_credentials_aria`.
- **P1 #2** (83) — full-page screenshots without stubbing catalog API routes → non-deterministic background. Fix: scoped screenshots to `[data-slot='dropdown-menu-content']` and `[data-slot='dialog-content']` locators. Snapshots now show only the popup/dialog content, deterministic regardless of background.
- **P1 #3** (85) — test used `vi.mock("@/lib/api")` which `project-context.md` explicitly bans ("Mocking `api()` hides CSRF + 401-retry logic regressions"). Fix: replaced with `vi.spyOn(globalThis, "fetch").mockImplementation(...)` returning a stubbed `/api/auth/me` response while letting `api()`'s CSRF + retry logic execute normally.
- **P2 #4** (80) — hard-coded URLs were unexplained → future "fix" could derive from `window.location.origin`. Added WHY comment: off-portal AI agent needs the canonical internet-facing address regardless of admin's browsing host.
- **P3 #5** — redundant per-file `afterEach(cleanup)` (global setup already registers it); silently dropped during the fetch-mock rewrite.

## Verification

- `npm run test` (vitest): **81 files / 318 tests pass** (3 new in `UserMenu.test.tsx`).
- `npm run lint`: clean (`--max-warnings=0`).
- `npx tsc --noEmit`: clean.
- `npx playwright test --config=tests/visual/playwright.config.ts tests/visual/agents-info-dialog.spec.ts`: 8/8 pass against committed baselines; deterministic across two consecutive runs.
- Spot-check (via Read tool, no displayed UI): menu shows "Dla agentów" / "For agents" admin entry; dialog renders title + 3 copy blocks (each with command + aria-labeled button) + 2 external links; mobile-light layout wraps commands with `break-all whitespace-pre-wrap`, copy buttons stay visible with `shrink-0`.

## Operator final review

Visual baselines are committed PNGs. Ezop reviews them in the diff and decides whether the visual delta is intentional. Per `project-context.md`: "Inspect `__snapshots__/` diffs intentionally; do not blanket-update without reading the visual delta."

Known cosmetic note (not a regression, pre-existing primitive behavior): DialogDescription muted-foreground text contrast in **light mode** is low — affects every dialog in the codebase, not just this one. Outside TB-006 scope.
