---
title: "Product Brief: 3d-portal — UI Theme Compliance & Visual Regression Hardening (Initiative 3)"
type: product-brief
initiative: 3
status: complete
created: 2026-05-13
last_updated: 2026-05-13
author: Ezop (operator) + Claude (BMAD planning chain)
mode: autonomous
revision_notes: |
  v2 (2026-05-13) — adversarial review pass applied. Fixed P0×2 (Stylelint notation
  pin file-wide vs mixed-design via token file split; @poupe plugin single-maintainer
  → in-repo no-restricted-syntax is first-line, plugin is enhancement layer) + P1×5
  (phase sequencing within Epic 5 commits to A→C-tooling-early→B→C-prevention;
  Success Criterion #5 refactored to leading indicators; baseline sign-off
  enforced by git pre-commit hook not commit-message convention; Story 5.14
  concretized to artifact-path + invocation + acceptance criteria; operator
  time-budget explicit + sampling-strategy fallback) + most P2/P3 tightenings.
related_artifacts:
  - product-brief-3d-portal-ui-theme-hardening-distillate.md
  - prd.md (to be extended with `## Initiative 3` section)
  - architecture.md (to be extended with `## Initiative 3` section)
  - epics.md (Epic 5 — first epic under Initiative 3)
---

# Product Brief: UI Theme Compliance & Visual Regression Hardening

## Executive Summary

The 3d-portal frontend has shipped three theme/contrast defects in light mode in the last four weeks — each caught only after the bug reached the production-equivalent dev host. The visual-regression CI (Playwright `toHaveScreenshot()` across four projects: desktop/mobile × light/dark) reported green throughout, because the baseline screenshots themselves carried the same defects. The most recent incident (the AgentsOnboardingDialog, 2026-05-13) is a base UI primitive — `apps/web/src/ui/dialog.tsx` uses hardcoded RGBA literals (`bg-[rgba(0,0,0,0.15)]`, `bg-[rgba(8,12,20,0.5)]`) that bypass the entire `theme.css` token system. Every dialog in the application carries the same defect.

This initiative is **not another quick-dev patch**. The pattern crosses the documented escalation threshold (3+ incidents within 4 weeks, all same class) and the procedural retrospective on the 2026-05-10 UI-review batch already flagged the routing miss that this class of defect was an epic in disguise. Initiative 3 — Epic 5 — closes both the technical surface (sweep & tokenize every primitive, audit every existing baseline against the human eye, expand open-state coverage to every interactive surface) and the procedural surface (lint enforcement at multiple layers, baseline acceptance gate **enforced by a git pre-commit hook**, visual coverage contract for any new UI primitive). Single-pass remediation, prevention rules carry forward.

The work is bounded: ~11 base UI primitives in `apps/web/src/ui/`, 23 `--color-*` tokens (19 base + 4 viewer) in `theme.css`, ~82 existing PNG baselines, 14 currently-skipped specs, ~10 currently-uncovered interactive surfaces, two lint integration points (in-repo ESLint `no-restricted-syntax` as first-line plus optional `@poupe` plugin enhancement) plus a scoped Stylelint pass on a split-out `viewer-tokens.css`, one git hook, two new project-context.md rules. Stakeholder is a single operator. No external customers, no SaaS migration, no design-system redesign.

## The Problem

**The defect class.** Light-mode contrast and theme-token bypass bugs ship to production undetected. Documented incidents in the last 30 days:

| Date | Surface | Root cause | Detection |
|---|---|---|---|
| 2026-04 → 2026-05-12 | `Select` popover, `Sheet` content, `Add*` sheets | Missing `--color-popover` token, hardcoded `bg-[rgba(8,12,20,0.5)]` in `SheetContent`, untranslated CTAs | Manual operator catch + spec `spec-ui-light-theme-polish.md` → commit `c35b5dc` |
| 2026-05-12 (TB-010) | Viewer3D mesh | `theme.css` `--color-viewer-*` tokens used modern space-separated HSL → three.js Color silently parses as white → mesh renders solid black in BOTH themes | Operator visual catch + Codex P2 finding on partial commit `10bc3de` |
| 2026-05-13 (this session) | `Dialog` primitive (base, app-wide) | `apps/web/src/ui/dialog.tsx:34` + `:56` hardcoded RGBA bypass tokens; description text uses `text-muted-foreground` on translucent dark bg in light mode → unreadable | Operator visual catch — screenshot from `.190` of `AgentsOnboardingDialog` |

**Why CI did not catch any of these.** The Playwright visual-regression suite passed green at all three points. For the dialog incident the baseline `apps/web/tests/visual/__snapshots__/agents-info-dialog.spec.ts/agents-dialog-desktop-light.png` **was captured with the bug already in place** — current renders match the corrupted baseline. Green is correct under the contract "looks like the baseline", which is not the contract operators thought they were buying.

**Why this is not just a recurring quick-dev situation.** The 2026-05-10 UI-review retrospective documented the routing miss explicitly: multi-PR batches from review docs are epics in disguise. The pre-existing-issue threshold (3 stories OR ≥5 within a single session — `feedback_preexisting_issue_threshold.md`) is exceeded by this defect class. The 2026-05-10 retro's Decision D3 ("visual-smoke per UI PR") is encoded as a soft norm in `project-context.md` but never wired into automation; the next agent writing a UI story is not forced to obey it. **The lesson is structural**: convention-only enforcement loses to convention-only bypass, exactly as the same retro documented for the routing miss itself.

**Cost of the status quo.** Operator carries the full QA load. Every shipped contrast defect lands on the dev host, gets caught visually, generates a quick-dev or spec, costs 1–3 hours and at least one auto-deploy cycle. Pattern frequency is ~1 incident per 2–3 weeks. The audit done while drafting this brief found **five concrete surviving violations** that will ship as the next 1–3 incidents unless something structural changes:

- `apps/web/src/ui/dialog.tsx:34` (`DialogOverlay`) — `bg-[rgba(0,0,0,0.15)]`
- `apps/web/src/ui/dialog.tsx:56` (`DialogContent`) — `bg-[rgba(8,12,20,0.5)]` text-foreground (the headline-defect line)
- `apps/web/src/ui/sheet.tsx:29` (`SheetOverlay`) — `bg-[rgba(0,0,0,0.15)]`
- `apps/web/src/modules/catalog/components/viewer3d/measure/RimOverlay.tsx:8` — `bg-zinc-900/95 text-white ring-white/15`
- `apps/web/src/modules/catalog/components/viewer3d/measure/MeasureOverlay.tsx:16` — same pattern

Plus a latent risk: `theme.css` `.dark {}` block omits overrides for `--color-success`, `--color-warning`, `--color-destructive` — three tokens inherit their light values in dark mode and may produce wrong contrast wherever they are applied.

## The Solution

A single BMAD-formal initiative — **Epic 5** under Initiative 3 — executed in three sequenced phases with an explicit ordering that lets prevention tooling drive remediation, not the reverse:

**Phase A — Audit (read-only inventory).** Three parallel investigations producing three reports under `_bmad-output/implementation-artifacts/`:
- *Theme-token compliance sweep:* statically grep `apps/web/src/**` for color literals (`bg-[rgba`, `bg-[#`, `bg-[hsl(`, raw Tailwind palette utilities like `bg-zinc-N` / `text-white`). Output: severity-ranked offender list with file:line precision. Also enumerate every CSS-variable reader in the repo (`getPropertyValue('--color-*')`, `getComputedStyle(...).getPropertyValue`, three.js Color consumers) — every token-reader that is not the browser CSS engine is a potential parser-mismatch trap; the brief assumes only `palette.ts:10`/`readMeshTokens.ts`, the audit must confirm.
- *Baseline integrity audit:* human-eye review of every existing PNG snapshot under `apps/web/tests/visual/__snapshots__/`. **Reviewer-fatigue countermeasure:** batched in sessions of ≤20 PNGs, max 2 sessions/day. Also enumerate the 14 currently-skipped specs and decide skip→unskip or skip→delete per spec. Output: per-baseline OK/buggy/uncertain verdict + skip resolution.
- *Interactive-surface coverage matrix:* enumerate every Radix/base-ui primitive instance in the app and cross-reference against the open-state visual specs. Output: coverage matrix with gap cells marked.

**Phase C-early — Tooling adoption** (sequenced AFTER Phase A audit, BEFORE Phase B remediation). The rationale: lint must be live during remediation so violations appear in CI on every commit, instead of being chased after the fact.
- *In-repo ESLint `no-restricted-syntax` rule banning color literals* (`bg-[rgba(`, `bg-[#`, `bg-[hsl(`, raw palette utilities like `bg-zinc-N`, `text-white`, `border-red-500`). This is the **first-line, dependency-free** enforcement. Tier `error` in `apps/web/src/ui/**`, `warn` elsewhere. Zero external dependencies, deterministic, survives the disappearance of any community plugin.
- *Optional enhancement: `@poupe/eslint-plugin-tailwindcss`* for `prefer-theme-tokens` / `no-arbitrary-value-overuse` semantic rules (catches token-existence not just regex). Wired as `warn` initially; gated on the in-repo rule being green first. **Risk acknowledged**: plugin is pre-1.0 single-maintainer (v0.3.1, 2026-04-07); if it goes silent the in-repo rule alone still delivers ≥80% of the value.
- *Token-file split for Stylelint compatibility:* the current `theme.css` mixes modern space-separated HSL (browser tokens) and legacy comma-separated HSL (viewer tokens) intentionally. Stylelint's `color-function-notation` rule is file-wide and cannot pin one form per token group within one file. **Resolution:** split `--color-viewer-*` tokens into `apps/web/src/styles/viewer-tokens.css` (imported by `theme.css`); scope a per-file Stylelint override on `viewer-tokens.css` pinning `color-function-notation: 'legacy'`; main `theme.css` keeps modern syntax with `color-function-notation: 'modern'` or unset. Deferred-but-named option: move three.js consumers off CSSOM parsing to a build-time generated TS constants file (`viewer-tokens.ts`) — most robust, bigger lift, not in Epic 5.
- *`@axe-core/playwright` contrast scan* with `runOnly: ['color-contrast']` (scoped, not full a11y rule pack) per project. Initial level `warn` (don't block iteration during remediation); promoted to `fail` post-remediation.

**Phase B — Remediation** (write phase, runs with lint live):
- *Dialog/Overlay tokenization first* (highest-fanout: every dialog in app uses these). Replace hardcoded RGBA with `bg-background/N` or a new `--color-overlay` / `--color-overlay-foreground` token if needed. Mirror the pattern that worked for `SheetContent` in `c35b5dc`.
- *Viewer-overlay tokenization* (`RimOverlay`, `MeasureOverlay`) — likely new `--color-viewer-tooltip` tokens (comma-HSL form, in the split-out `viewer-tokens.css`).
- *Dark-mode override completeness*: add `.dark {}` overrides for `--color-success`, `--color-warning`, `--color-destructive` (currently missing).
- *Bulk fix of remaining Phase-A offenders.*
- *Baseline regeneration* — every regenerated PNG requires explicit operator sign-off (see Phase C-prevention for the enforcement mechanism, not convention).
- *Open-state spec expansion* — sub-split into per-primitive sub-stories rather than one 32-baseline blob: Select, ConfirmDialog/EditSheets, Tooltip+UserMenu, etc.

**Phase C-prevention — Process & contract** (the load-bearing deliverable; without this, Epic 5 is "fixed once, repeats next quarter"):
- *Baseline acceptance gate enforced by git pre-commit hook* (`apps/web/.husky/pre-commit` or equivalent shell hook). When a commit touches `apps/web/tests/visual/__snapshots__/**`, the hook parses the commit message and requires a `baseline-reviewed: <baseline-basename>, <reviewer>, <YYYY-MM-DD>` line for each changed PNG. **This is the contract** — convention alone (the original v1 proposal) repeats the routing-miss anti-pattern.
- *`project-context.md` new rule: "Baseline Acceptance Gate"* — narrative + the hook reference. Rule body cites the hook script path and the `baseline-reviewed:` format.
- *`project-context.md` new rule: "Visual Coverage Contract"* — any new interactive UI primitive merged to `apps/web/src/ui/` must ship with an open-state visual spec covering `{desktop, mobile} × {light, dark}` in the same commit. **Enforced by an ESLint custom rule** (or a second pre-commit hook) that checks for a matching spec when a new file appears under `apps/web/src/ui/`.
- *Codex review prompt enrichment* — concrete artifact at `.codex/review-prompts/ui-theme-checks.md` (path TBD-by-architecture). Invocation: `cat .codex/review-prompts/ui-theme-checks.md prompt-tail.md | codex exec -` for UI-touching commits; default `codex review --commit <SHA>` retained for non-UI commits. Acceptance criterion: replaying the prompt against commit `10bc3de` (the historical TB-010 partial commit that baked the black-mesh + overlap bugs into 14 baselines) surfaces at least one of those two defects.
- *Axe contrast scan promotion to `fail` level* — last story of Epic 5; closes the loop.

## What Makes This Different

- **BMAD-formal end-to-end** — PRD extension → architecture extension → Epic 5 → stories → sprint-planning → story cycle. No multi-QD shortcut. The 2026-05-10 routing-miss retro is the explicit prior art: repeated-pattern fixes are epics, not batches.
- **Not buying a SaaS** — Chromatic / Percy / Argos CI are aimed at design-system teams with reviewer pool. Solo-operator context with local Playwright + lint + procedural rule + git hook achieves ~90% of the value at zero external-service friction.
- **Lint enforcement layered, not single-tool-bet** — in-repo `no-restricted-syntax` is the first-line guarantee (deterministic, zero-dep, survives plugin abandonment); `@poupe` plugin is enhancement; Stylelint covers the CSS file. No critical path depends on any single community-maintained plugin.
- **Sign-off is a hook, not a convention** — the 2026-05-10 routing-miss retro documented that conventions in CLAUDE.md and project-context.md get bypassed. Epic 5's "Baseline Acceptance Gate" is enforced by a git hook precisely so it cannot be bypassed by a future agent simply not reading the rule.
- **Not redesigning the design system** — tokens stay where they are. The intervention is "stop bypassing them" + "verify what we already have works" + "split out viewer tokens so Stylelint can defend them". The single justified additions are `--color-overlay` (if Dialog/Sheet pattern needs it) and `--color-viewer-tooltip` (decided in architecture extension).
- **Prevention is co-equal with remediation** — Phase C is split into C-early (tooling, before B) and C-prevention (gates + rules, after B). Without this sequencing, the same incident class returns within 30 days.
- **Storybook rejection is honest, not asserted** — see Scope section for the numerical comparison.

## Who This Serves

**Primary: Ezop (operator).** Solo developer. Every shipped contrast defect lands on his QA. Currently absorbs ~1–3 hours per incident plus context-switch cost. Initiative 3 reduces frequency to a measurable floor (zero light-mode contrast defects shipped via QD-channel for 90 days post-close — see Vision).

**Secondary: AI agents** (Claude / Codex / future Gemini). The agent runbook (Initiative 2) does not depend on UI rendering, but every BMAD checkpoint screenshot and every retro narrative is poisoned by visual rot. A clean baseline set lets the visual-regression suite be used as a real signal in agent-driven code-review flows.

**Not in scope: external customers.** Homelab single-tenant context, IP-allowlist gated edge proxy. No public-facing UX impact to model. Family-user v2 milestone exists in the 2026-05-10 UI-review doc as a vision target; Epic 5 does not commit specific deliverables to family-v2 but its outputs (clean baseline set, contrast lint, coverage matrix) make any future family-v2 cycle cheaper.

## Success Criteria

Measurable, leading-indicator-first, observable on every commit:

1. **Zero hardcoded color literals** in `apps/web/src/ui/**`, verified by `npm run lint --max-warnings=0` failing the build on any new occurrence. Observable per commit via CI/local lint.
2. **`theme.css` Stylelint-enforced**: `viewer-tokens.css` pins `color-function-notation: 'legacy'`, `theme.css` keeps modern syntax. Hex outside `var(--token)` references forbidden. Observable per commit.
3. **`@axe-core/playwright` contrast scan with `runOnly: ['color-contrast']`** integrated; level `warn` during Phase B remediation, **promoted to `fail` at Epic 5 close**. Observable per `npm run test:visual`.
4. **Baseline Acceptance Gate is a hook, not a convention** — `apps/web/.husky/pre-commit` (or equivalent) rejects commits touching `apps/web/tests/visual/__snapshots__/**` without a `baseline-reviewed:` line per changed PNG. Observable: `git log --grep='baseline-reviewed:'` shows the line on every baseline-touching commit since Epic 5 close; zero baseline-regen commits in the 30 days post-close lack the line. **First-pass enforcement test**: within 30 days of Epic 5 close, the rule has been exercised on at least 3 commits in `git log` history.
5. **Visual Coverage Contract** — every interactive primitive in `apps/web/src/ui/` (Dialog, Sheet, Popover, Select, Dropdown, Tooltip; full list determined in Phase A) has open-state coverage across `{desktop, mobile} × {light, dark}`. Observable: Phase A coverage matrix table at Epic close shows 100% green.
6. **`project-context.md` rule_count** advances from 134 to 136 with the two new rules. Activity metric — paired with #4's first-pass enforcement test, which is the actual outcome metric.

## Scope

**In:**
- All files under `apps/web/src/ui/` (currently 11 primitives, ~1165 LOC).
- All files under `apps/web/src/modules/**/*.tsx` for the static color-literal sweep (the audit). Remediation outside `ui/` only where the audit surfaces direct violations — not a project-wide refactor.
- All ~82 PNG baselines under `apps/web/tests/visual/__snapshots__/` plus the 14 currently-skipped specs (Phase A decides skip→unskip or skip→delete per spec).
- `apps/web/src/styles/theme.css` — split into `theme.css` (browser tokens, modern HSL) + `viewer-tokens.css` (three.js tokens, legacy HSL); add missing `.dark {}` overrides for success/warning/destructive; add `--color-overlay` / `--color-viewer-tooltip` if needed.
- ESLint config: `apps/web/eslint.config.js` — in-repo `no-restricted-syntax` rule; optional `@poupe/eslint-plugin-tailwindcss`.
- New Stylelint config: `apps/web/.stylelintrc` (or equivalent flat config) with per-file overrides.
- `@axe-core/playwright` integration in `apps/web/tests/visual/playwright.config.ts`.
- Git hook: `apps/web/.husky/pre-commit` (or equivalent shell script) — enforces `baseline-reviewed:` line on baseline-touching commits + (optionally) checks for matching open-state spec when a new `apps/web/src/ui/*.tsx` file appears.
- `.codex/review-prompts/ui-theme-checks.md` — concrete Codex prompt fragment for UI-touching commits.
- `_bmad-output/project-context.md` rule additions (2 rules, +2 rule_count).

**Out (explicit non-goals):**
- Design-system redesign or visual refresh. Token values and visual hierarchy unchanged.
- Library migration. `@base-ui/react` + Radix stays. shadcn/ui flow stays.
- Auto-dark-mode detection, per-user theme persistence, additional theme variants.
- Backend or worker changes. This initiative is frontend-only.
- CI infrastructure migration (e.g., adopting Argos CI or moving visual regression to GitHub Actions).
- Full WCAG 2.2 a11y audit. Axe contrast scan is the scope; broader a11y (keyboard nav, ARIA, focus management) is a separate future initiative.
- Moving three.js consumers off CSSOM parsing to build-time TS constants. Named as the most-robust future path for parser-mismatch defense; not in Epic 5 scope.
- Storybook adoption. **Numerical comparison vs Epic 5's open-state spec expansion**: Storybook 8 + Tailwind v4 integration is currently non-trivial (Tailwind v4 PostCSS plugin compatibility is an active issue surface), shadcn/ui primitive coverage adds 11 story files at ~30 LOC each (~330 LOC of catalogue boilerplate), single-operator context yields no living-catalogue consumer benefit. The proposed Epic 5 alternative (8 open-state specs at ~25 LOC each + 32 baselines) is roughly equivalent in LOC but produces actual contrast/light-dark verification per commit rather than a UI catalogue. Rejection holds; the comparison is on the record.

## Vision

**Epic 5 close (target: ~2–3 sprint-equivalent units of work).** Defect class extinguished. Lint + Stylelint + axe contrast scan + 2 procedural rules + 1 git hook + Codex prompt enrichment in place. Every new UI story automatically routed through the Visual Coverage Contract via the hook. Operator QA load returns to "spot-check after deploy" instead of "find the bug I already shipped".

**90 days post-Epic-5 close (vision target, not a Success Criterion).** Zero light-mode contrast incidents shipped via QD-channel. Current rate ~1 per 2–3 weeks; the aspiration is at least three full cycles with no recurrence. **Why this is vision not criterion**: not falsifiable in a useful timeframe (cannot tell at day 30); the leading indicators in §Success Criteria are the actually-actionable signals. Tracked retrospectively at Epic 5 retro and at 90-day review.

**3–6 months out.** Baseline acceptance gate is muscle memory. Recurring monthly baseline audit (operator-led, ~30 min cadence) catches drift the per-PR gate hides — codified informally first, promoted to BMAD-skill if pattern proves out.

**1 year out (if Initiative 4+ shape up as new feature scope).** Visual-regression suite is a trusted signal in agent-driven dev flows: Codex review reads the snapshot diff alongside the code diff; baseline corruption gets caught at PR time, not at production-equivalent time. The 2026-05-10 routing-miss retro becomes a closed chapter.

The vision is unambitious by design. This is brownfield cleanup; the win is the boring outcome — predictable, repeatable UI quality from a single-operator team.

---

## Working assumptions (challenged during discovery; surviving into PRD)

- Three.js viewer is the only non-browser CSS-token consumer in the repo. `palette.ts:10` and `readMeshTokens.ts` are the only currently-known readers; **Phase A audit must enumerate the actual count** before this assumption is load-bearing for Phase B/C.
- Stakeholder load model is single-operator; no reviewer pool. Procedural gates lean on tooling (git hook, lint) plus operator sign-off — convention alone is rejected as enforcement.
- Auto-deploy contract holds: every code-touching commit deploys to `.190`; Stylelint/ESLint failures must block this loop.
- `_bmad-output/` stays gitignored; this brief is operator-local and tracked via memory + `MEMORY.md`.
- **Operator eye-review time budget**: 82 existing PNGs (Phase A 5.2) + ~32 new PNGs (Phase B 5.9) = ~114 PNG sign-offs across Epic 5, ~1 min/PNG = ~2 hours of focused click-through distributed across the epic. Phase A budgets sessions of ≤20 PNGs / ≤2 sessions per day as the fatigue countermeasure. If Phase B PNG count balloons past 50, fall back to a sampling strategy: 100% review for first 4 weeks, 25% spot-check thereafter once lint+Stylelint gates are live.

## Stakeholders consulted

- **Ezop** (operator) — pre-loaded the incident trigger + pattern history + three-phase structure proposal + explicit autonomous-mode authorization.
- Memory & feedback files: `feedback_default_to_bmad_workflow.md`, `feedback_visual_failure_mode_triage.md`, `feedback_threejs_hsl_parsing.md`, `feedback_preexisting_issue_threshold.md`, `feedback_local_only_docs.md`.
- Retros: `ui-review-retro-2026-05-10.md`, `epic-1-retro-2026-05-10.md`, `epic-2-retro-2026-05-10.md`, `epic-4-retro-2026-05-11.md`.
- Web research: `@poupe/eslint-plugin-tailwindcss` health verification (single-maintainer pre-1.0 → fallback named), Stylelint `color-function-notation` mechanism verification (file-wide → token-file split mandated), `@axe-core/playwright` scoped-rule pattern.

## Next step

Route to `bmad-create-prd` for PRD extension into `_bmad-output/planning-artifacts/prd.md` under new `## Initiative 3` H2 section. PRD focus: FR/NFR/Decisions for the three-phase structure (A → C-early → B → C-prevention), with explicit story enumeration and per-story acceptance criteria.
