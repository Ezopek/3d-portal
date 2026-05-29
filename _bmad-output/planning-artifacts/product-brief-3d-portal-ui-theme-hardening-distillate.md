---
title: "Product Brief Distillate: 3d-portal — UI Theme Compliance & Visual Regression Hardening (Initiative 3)"
type: llm-distillate
source: "product-brief-3d-portal-ui-theme-hardening.md"
created: 2026-05-13
last_updated: 2026-05-13
purpose: "Token-efficient context for downstream PRD/architecture/epics creation"
initiative: 3
epic_seed: 5
revision: "v2 (adversarial-review-applied)"
---

# Distillate — Initiative 3 / Epic 5 (UI Theme Compliance & Visual Regression Hardening)

Reference detail captured during contextual discovery (artifact analyzer + web research + adversarial review) that did not fit the executive brief but is load-bearing for PRD-level decisions.

---

## Frozen technical facts

### Incident chain (chronological)

- **2026-04 → 2026-05-12 (`c35b5dc`)** `fix(web): light-theme polish — popover tokens, sheet bg, i18n for Add print/Add note`. Three defects: (1) Select popover missing `--color-popover` token, (2) `SheetContent` carried `bg-[rgba(8,12,20,0.5)]` hardcoded, (3) Add* CTAs untranslated. Spec: `_bmad-output/implementation-artifacts/spec-ui-light-theme-polish.md`. Visual-regression deferred to TB-009.
- **2026-05-10 → 2026-05-12 (`fd049e5` TB-009, `c0daf7a` TB-010/011/012)** Visual baseline rot from PR `212c025` (UI-review batch i18n+a11y sweep). ~66 fails on bare main, 32 PNGs regenerated, 2 src bugs surfaced (`MeasureSummary.tsx:37` summary.empty vs summary_empty key; theme.css viewer-* tokens space-separated HSL → three.js Color parses as white → black PBR mesh). Final post-`c0daf7a`: 90 passed / 0 failed / 14 skips.
- **2026-05-13 (this brief)** AgentsOnboardingDialog (TB-006 base, shipped 2026-05-11) renders broken in light mode. Root cause: `apps/web/src/ui/dialog.tsx:34` (`DialogOverlay: bg-[rgba(0,0,0,0.15)]`) + `:56` (`DialogContent: bg-[rgba(8,12,20,0.5)]`). Baseline `agents-dialog-desktop-light.png` HAS THE BUG BAKED IN — visual-regression green because corrupted-baseline-matches-corrupted-render.

### Surviving violations at brief time (audit snapshot, 2026-05-13)

Five concrete sites; expected count from full Phase A sweep is similar order:

- `apps/web/src/ui/dialog.tsx:34` — `DialogOverlay` `bg-[rgba(0,0,0,0.15)]`
- `apps/web/src/ui/dialog.tsx:56` — `DialogContent` `bg-[rgba(8,12,20,0.5)] text-foreground` (the headline defect this brief is named for)
- `apps/web/src/ui/sheet.tsx:29` — `SheetOverlay` `bg-[rgba(0,0,0,0.15)]` (mirror of dialog defect; `SheetContent` already fixed at `c35b5dc`, `SheetOverlay` was not)
- `apps/web/src/modules/catalog/components/viewer3d/measure/RimOverlay.tsx:8` — `bg-zinc-900/95 text-white ring-white/15` (raw palette literal, over-canvas tooltip)
- `apps/web/src/modules/catalog/components/viewer3d/measure/MeasureOverlay.tsx:16` — same pattern (`bg-zinc-900/95 text-white ring-white/15`)

### Theme system inventory (verified against theme.css 2026-05-13)

- Tailwind v4 (`@import "tailwindcss"`, no `tailwind.config.js`). Tokens in `apps/web/src/styles/theme.css` `@theme {}` block.
- **23 unique `--color-*` tokens total** (verified by `grep -E "^\\s+--color-[a-z-]+:" theme.css | sort -u | wc -l = 23`):
  - **19 base/UI surface tokens** (lines 8–26): `background`, `foreground`, `card`, `card-foreground`, `popover`, `popover-foreground`, `muted`, `muted-foreground`, `primary`, `primary-foreground`, `accent`, `accent-foreground`, `border`, `input`, `ring`, `success`, `warning`, `destructive`, `chip-foreground`.
  - **4 viewer tokens** (lines 34–37): `viewer-mesh-paint`, `viewer-mesh-edge`, `viewer-grid`, `viewer-measure`.
  - Plus 3 `--radius-*` and 1 `--font-sans`.
- **`.dark {}` overrides 19 of 23 — omits `--color-success`, `--color-warning`, `--color-destructive`, and `--color-card-foreground` is overridden but worth audit**. Latent risk: success/warning/destructive in dark mode inherit light values, may produce wrong contrast. Phase A audit must surface this; Phase B remediation adds the overrides.
- **HSL syntax split (intentional, documented)**: lines 8–26 use modern space-separated `hsl(H S% L%)` for browser tokens; lines 34–37 use legacy comma-separated `hsl(H, S%, L%)` for viewer-* tokens. Documented in 7-line inline comment block (lines 27–33). Three.js Color (r0.171) only parses legacy form.
- **`bg-popover`** consumed only by `dropdown-menu` (×2) and `select` (×3); popover token was introduced specifically for the `c35b5dc` fix. Most primitives use `bg-background` / `bg-card`.

### UI primitives inventory (`apps/web/src/ui/`, 11 files, ~1165 LOC)

`badge.tsx`, `button.tsx`, `card.tsx`, `dialog.tsx` (160 LOC), `dropdown-menu.tsx` (266 LOC), `input.tsx`, `select.tsx` (199 LOC), `separator.tsx`, `sheet.tsx` (136 LOC), `tabs.tsx`, `tooltip.tsx`. Built on `@base-ui/react` primary + Radix for `dialog/dropdown-menu/tabs/tooltip` (legacy keep).

### Visual regression infrastructure

- **Spec count**: 18 spec files under `apps/web/tests/visual/`, ~629 LOC.
- **Projects**: 4 — `desktop-light`, `desktop-dark`, `mobile-light` (Pixel 5), `mobile-dark` (Pixel 5).
- **Baselines**: ~82 PNG files, 14 pre-existing skips persistent. **Phase A audit (Story 5.2) must decide skip→unskip or skip→delete for each of the 14 skips.**
- **Config**: `tests/visual/playwright.config.ts`, locale `pl-PL`, TZ `Europe/Warsaw`, baseURL `http://localhost:5173`, `fullyParallel: true`, snapshot template `{testDir}/__snapshots__/{testFilePath}/{arg}-{projectName}{ext}`.
- **Specs with open-state coverage** (~7 of 18): sessions, catalog-card-carousel, agents-info-dialog, files-tab-admin, viewer3d-measure-plane, viewer3d-measure-pp, viewer3d-modal-open, viewer3d-inline-loaded, viewer3d-mobile (partial). Remainder (11) are static page snapshots.
- **Surfaces with ZERO open-state baseline** (gap inventory): `Select` dropdowns, `FilterRibbon` TagPicker, `ConfirmDialog`, `EditTagsSheet`, `EditDescriptionSheet`, `RenderSheet`, `AddPrintSheet`, `AddNoteSheet`, `UserMenu`, `Tooltip`. These are the surfaces that produced 2026-05-10 + 2026-05-11 regressions.

### Lint toolchain (current state)

- ESLint 9 flat config: `apps/web/eslint.config.js`, 110 LOC. `tseslint.configs.recommended` + `react.configs.flat.recommended` + `jsx-runtime` + `react-hooks` recommended. `react-refresh/only-export-components` warn (gated by `--max-warnings=0`). `no-restricted-syntax` forbids `/api/files|catalog/` literals/template-elements only.
- **No color/theme-token rule**. **No Tailwind palette ban**. **No Stylelint installed.**
- Prettier 3.4.0 used as formatter via `format` script. `eslint-config-prettier` disables conflicts. **No husky/lint-staged/pre-commit hooks** — this absence is the substrate for Phase C-prevention (Baseline Acceptance Gate hook adds the first one).
- Verify-symbolication.sh is the only deploy-time gate post-merge. No pre-commit gate runs visual regression.

### Codex review pattern

- Per-commit, not pre-commit. Invocation: `codex review --commit <SHA>` after dev-commit + auto-deploy.
- Has caught (representative): TB-007 P1 race; TB-008 Alembic revision >32 chars; TB-010 selector-summary overlap + black mesh; every Epic 4 commit had ≥1 finding.
- Review prompt format converged on lean direct-prompt (per `feedback_codex_review_invocation.md`).
- **Limitation**: there is no pluggable prompt template on the `codex review --commit` codepath. Story 5.14's "prompt enrichment" is therefore an invocation-mode change for UI commits: `cat .codex/review-prompts/ui-theme-checks.md prompt-tail.md | codex exec -` instead of bare `codex review`. Decision on detection ("is this a UI commit?") deferred to architecture: simplest is `git diff --name-only HEAD~1` heuristic matching `apps/web/src/(ui|styles)/.*` or `apps/web/tests/visual/.*`.

---

## Constraints — non-negotiable

- **Initiative 3 = Epic 5** (project-global epic numbering; I1 shipped E1–E3 2026-05-10; I2 shipped E4 2026-05-11). PRD/architecture/epics files must be EXTENDED via `## Initiative 3 — <name>` H2 — NOT forked.
- **`_bmad-output/` is gitignored.** Brief, distillate, PRD-extension, epics-extension, story files all operator-local. Memory + `MEMORY.md` are the persistent surface across sessions.
- **English in committed file content** (code, docs, commit messages). Polish stays conversational.
- **Auto-deploy contract** (`feedback_auto_deploy_dev.md`): every code/infra commit to `main` triggers `infra/scripts/deploy.sh` without asking; doc-only skip. CSS/UI-primitive edits ALWAYS deploy. Lint failures must block this loop.
- **Three.js Color parse constraint** (`feedback_threejs_hsl_parsing.md`): any `--color-viewer-*` token MUST be comma-separated HSL. Modern space-separated syntax silently parses as white. Root cause of TB-010 black mesh. Defense in Epic 5: split tokens into separate file + scoped Stylelint pin (NOT a file-wide pin on theme.css — that would clash with browser tokens).
- **Single-linter discipline for ESLint chain.** In-repo `no-restricted-syntax` is the first-line dependency-free rule; `@poupe/eslint-plugin-tailwindcss` is optional enhancement layer. Stylelint runs as a separate linter on CSS only — `npm run lint` script chains both (`eslint ... && stylelint ...`).
- **No SaaS adoption.** No Chromatic / Percy / Argos CI. Solo-operator context. Human-eye gate via git pre-commit hook + Playwright HTML report.
- **Vitest `globals: false` quirk** is resolved: `vitest.setup.ts` (commit `a026e97`) globally registers `afterEach(cleanup)`. Existing per-file `afterEach(cleanup)` calls are harmless redundancy.
- **Tailwind v4 is non-negotiable** (`@import "tailwindcss"`, `@theme {}` block). v3 patterns do not apply.

## Rejected approaches (do not re-propose)

- **Multi-quick-dev batch.** Pattern is repeat-class (3 incidents in 4 weeks); the 2026-05-10 UI-review retro D1 explicitly forbids this routing. BMAD epic, not QD chain.
- **Chromatic / Percy / Argos CI.** Pricing/process aimed at design-system teams with reviewer pool. Solo-operator. Adds external service dependency for a problem solvable with local Playwright + lint + procedural rule + git hook. Argos OSS tier is the closest fit but adds non-trivial integration cost.
- **oxlint as second linter.** Faster + narrower but adds dual-toolchain complexity. Single-linter discipline matches the rest of the project; ESLint in-repo `no-restricted-syntax` rule (+ optional `@poupe` plugin) path chosen instead.
- **`francoismassart/eslint-plugin-tailwindcss`.** Only partial Tailwind v4 support (beta channel). If a plugin is adopted at all, `@poupe/eslint-plugin-tailwindcss` (v4-first) is the choice. **But the primary first-line enforcement is in-repo `no-restricted-syntax` — no plugin dependency.** Plugin acceptable risk: v0.3.1 (2026-04-07), single-maintainer (Alejandro Mery), pre-1.0; if it goes silent the in-repo rule still delivers ≥80% of the value.
- **Stylelint `color-function-notation: 'legacy'` applied file-wide to `theme.css`** — this proposal was in v1 of the brief and was rejected during adversarial review. The rule is file-wide; pinning legacy would either auto-fix every modern browser-token HSL to comma form (mass change, semantically OK but a 17-line edit no-one asked for) or generate 17 violations the operator silences with `stylelint-disable-next-line` (theatre). **Resolution:** split `--color-viewer-*` tokens into `apps/web/src/styles/viewer-tokens.css`, scope per-file Stylelint override pinning `color-function-notation: 'legacy'` on that file, main `theme.css` keeps modern syntax (rule unset or pinned `modern`).
- **`--update-snapshots` reflexively on any failure.** Buggy baselines accumulate exactly this way. Baseline regen must be deliberate with diff review + commit-message sign-off + git hook enforcement.
- **Auto-running `--update-snapshots` in CI.** Same anti-pattern at a different scope.
- **Storybook adoption.** Comparison vs Epic 5 alternative (open-state spec expansion, Story 5.9): Storybook 8 + Tailwind v4 integration is currently non-trivial (PostCSS plugin compatibility active issue surface); shadcn/ui primitive coverage adds 11 story files at ~30 LOC each ≈ 330 LOC of catalogue boilerplate; single-operator context yields no living-catalogue consumer benefit. Epic 5 alternative: 8 open-state specs at ~25 LOC ≈ 200 LOC, plus 32 baselines. Roughly equivalent LOC but specs deliver per-commit contrast/light-dark verification while Storybook delivers a catalogue with no consumer. Rejection stands.
- **Full WCAG 2.2 audit.** Out of scope. Axe `runOnly: ['color-contrast']` is the scope; broader a11y (keyboard nav, ARIA, focus management) is a separate future initiative.
- **CI infrastructure migration** (e.g., move visual regression to GitHub Actions). Adds host-drift risk to baselines (font/AA-rendering); current local model is stable post-TB-010.
- **Design-system redesign or theme refresh.** Tokens stay where they are.
- **Theming features beyond fixing what exists.** No auto-dark-mode detection, no per-user theme persistence, no additional theme variants.
- **Backend or worker changes.** Initiative 3 is frontend-only.
- **`vi.mock("@/lib/api")`** for new test work (per project-context.md ban — fetch-level stubs only).
- **Convention-only sign-off** (commit-message convention without enforcement). Original v1 brief proposal; rejected during adversarial review because the routing-miss retro documented that conventions in CLAUDE.md and project-context.md get bypassed. Resolution: git pre-commit hook parses commit message and rejects baseline-touching commits without `baseline-reviewed:` line.
- **Moving three.js consumers off CSSOM parsing to build-time TS constants** (most robust path against parser-mismatch class). Named as deferred future option; not in Epic 5 scope. Re-evaluate at Epic 5 retro.

## Anti-patterns named (avoid in implementation)

- **"Looks-right is good enough" baseline regen.** Every regenerated PNG must be reviewed at 100% zoom in the Playwright HTML report; commit message records the sign-off; **git hook enforces the sign-off line**. Codex review surfaced the corrupted TB-010 baselines only because it independently viewed the commit diff.
- **Token-bypass via arbitrary Tailwind values** (`bg-[#...]`, `bg-[rgba(...)]`, `text-[hsl(...)]`). The ENTIRE problem class. Phase C-early in-repo `no-restricted-syntax` rule forbids it in `apps/web/src/ui/**` at `error`, warns elsewhere.
- **Raw Tailwind palette utilities in `apps/web/src/ui/**`** (`bg-zinc-N`, `text-white`, `border-red-500`). Bypass tokens silently. Phase C-early rule lists these as banned prefixes via the same `no-restricted-syntax` config.
- **EN-only regex selectors in `apps/web/tests/visual/*.spec.ts`.** Tests run under forced `locale=pl-PL`; EN selectors silently fail. TB-009 selector-fix policy documented in spec comments but no lint rule yet — candidate for a follow-up rule in `no-restricted-syntax` (Phase C ideal but may slip to Epic-5 follow-up).
- **Mixing `hsl(H S% L%)` and `hsl(H, S%, L%)` notations in the same token file.** Rejected approach. Resolution: split token file (see Constraints).
- **Adding a new interactive UI primitive without open-state visual spec in the same commit.** Phase C-prevention "Visual Coverage Contract" rule forbids this; the git pre-commit hook (or a second hook) blocks the commit if a new file appears under `apps/web/src/ui/` without a matching spec under `apps/web/tests/visual/`.
- **Adding a new `--color-*` token without a `.dark {}` override.** Phase A audit surfaces the 3 existing examples (success/warning/destructive). Phase B remediation adds them. Future regression risk: defended by code-review discipline; lint rule for this is hard to express mechanically (deferred).
- **Convention-only enforcement.** Rules that live only in project-context.md or CLAUDE.md without a tooling counterpart get bypassed. Every new rule in Phase C-prevention is paired with a tooling defense (hook, lint, or test).

---

## Phase plan (substrate for Epic 5 stories — sequenced)

**Sequencing principle**: lint tooling lands EARLY (after Phase A audit, before Phase B mass remediation) so violations appear in CI during remediation — this way Phase B fixes are validated by the same gate that will then defend `main` going forward.

### Phase A — Audit (read-only)

| Story # | Surface | Output | Effort |
|---|---|---|---|
| 5.1 | Static color-literal sweep across `apps/web/src/**` + enumeration of every CSS-variable reader (`getPropertyValue('--color-*')`, three.js Color consumers) | `theme-token-violations-2026-05-XX.md` + `token-reader-inventory-2026-05-XX.md` | S |
| 5.2 | Baseline integrity audit, all 82 PNGs in `tests/visual/__snapshots__/` + skip-disposition for the 14 currently-skipped specs | `baseline-integrity-audit-2026-05-XX.md` with per-baseline OK/buggy/uncertain verdict + skip resolution log | M (sessions ≤20 PNGs / ≤2/day) |
| 5.3 | Interactive-surface coverage matrix | `interactive-surface-coverage-matrix-2026-05-XX.md` — table of every primitive × {open, closed} × {desktop, mobile} × {light, dark}, gap cells flagged | S |

All three parallelizable. No code changes. Output drives Phase B story granularity.

### Phase C-early — Tooling (after A, before B; runs during B)

| Story # | Surface | Effort |
|---|---|---|
| 5.10 | In-repo ESLint `no-restricted-syntax` rule: ban color literals (`bg-[rgba(`, `bg-[#`, `bg-[hsl(`, raw palette utilities `bg-zinc-N`, `text-white`, `border-red-500`, etc.) in `apps/web/src/ui/**` at `error`, warn elsewhere. Zero external dependency. Optional layer: `@poupe/eslint-plugin-tailwindcss` `prefer-theme-tokens` + `no-arbitrary-value-overuse` at `warn`. | M |
| 5.11 | Token-file split: extract `--color-viewer-*` tokens to `apps/web/src/styles/viewer-tokens.css`, imported by `theme.css`. Adopt `stylelint` + per-file overrides: `viewer-tokens.css` pins `color-function-notation: 'legacy'`; main `theme.css` pins or leaves `'modern'`. Add `color-no-hex` + `stylelint-color-no-non-variables` to forbid hex outside `var(--token)` references. Wire into `npm run lint` script (`eslint ... && stylelint ...`). | M |
| 5.12 | Integrate `@axe-core/playwright` with `runOnly: ['color-contrast']` per project (desktop-light/dark × mobile-light/dark) in `tests/visual/playwright.config.ts`. Initial level `warn`. Configure `disableRules` per-test escape hatch for known-noisy nodes. | M |

### Phase B — Remediation (Phase C-early gates live)

| Story # | Surface | Effort | Depends on |
|---|---|---|---|
| 5.4 | Dialog/Overlay tokenization (`dialog.tsx`, `sheet.tsx` `SheetOverlay`) + new `--color-overlay` token if needed | M | 5.1, 5.10, 5.11 |
| 5.5 | Viewer-overlay tokenization (`RimOverlay`, `MeasureOverlay`) — new `--color-viewer-tooltip` token(s) in `viewer-tokens.css` (legacy HSL) | S | 5.1, 5.10, 5.11 |
| 5.6 | Dark-mode override completeness (`--color-success`, `--color-warning`, `--color-destructive` add to `.dark {}`) | S | 5.1 |
| 5.7 | Bulk fix of remaining Phase-A offenders (outside `ui/**`) | M | 5.1, 5.10 |
| 5.8 | Baseline regeneration with operator sign-off (every buggy/affected PNG) | M | 5.2, 5.4–5.7, 5.13a (hook) |
| 5.9 | Open-state spec expansion. **Split into per-primitive sub-stories** to avoid effort-balloon: 5.9a Select, 5.9b ConfirmDialog/EditSheets bundle, 5.9c Tooltip + UserMenu, 5.9d remaining gaps from 5.3 matrix. Each sub-story includes per-baseline sign-off via the hook from 5.13a. | L (split) | 5.3, 5.13a |

5.8 and 5.9 are the bottlenecks. Both produce PNGs subject to the hook in 5.13a — so 5.13a (or at least a working draft of the hook) must land before either runs.

### Phase C-prevention — Gates + rules (after B; closes Epic)

| Story # | Surface | Effort |
|---|---|---|
| 5.13a | **Git pre-commit hook**: `apps/web/.husky/pre-commit` (or equivalent shell). When commit touches `apps/web/tests/visual/__snapshots__/**`, parse commit message; require one `baseline-reviewed: <baseline-basename>, <reviewer>, <YYYY-MM-DD>` line per changed PNG (basename collected via `git diff --cached --name-only`). Reject otherwise. **This is the gate that turns convention into contract.** | M |
| 5.13b | **Visual Coverage Contract enforcement**: extension of 5.13a hook (or a sibling) — when a new `apps/web/src/ui/*.tsx` file appears, require a matching `apps/web/tests/visual/*.spec.ts` exercising it in open state. Alternative: ESLint custom rule on the same condition. Decide in architecture. | S |
| 5.13 | `project-context.md` rule additions (2 rules): "Baseline Acceptance Gate" (cites 5.13a hook path + `baseline-reviewed:` format) and "Visual Coverage Contract" (cites 5.13b enforcement). `rule_count` 134 → 136. | S |
| 5.14 | Codex review prompt enrichment — concrete artifact at `.codex/review-prompts/ui-theme-checks.md`. Invocation: detect UI commits via `git diff --name-only` against `apps/web/src/(ui|styles)/.*` or `apps/web/tests/visual/.*`; use `cat .codex/review-prompts/ui-theme-checks.md prompt-tail.md \| codex exec -` for those; bare `codex review --commit <SHA>` otherwise. **Acceptance criterion**: replaying the enriched prompt against commit `10bc3de` (the TB-010 partial commit that baked black-mesh + overlap bugs into 14 baselines) surfaces at least one of those two defects. | S |
| 5.15 | **Axe contrast scan promotion to `fail` level.** Closing story. Gates Epic 5 → "feature work resumes". Pre-promotion check: scan returns zero violations on all 4 projects with `runOnly: ['color-contrast']`. | S |

---

## Success Criteria → leading indicators (PRD-ready)

(Migrated from brief executive section for distillate completeness.)

1. **Zero hardcoded color literals** in `apps/web/src/ui/**` — verified by `npm run lint --max-warnings=0` (5.10 in-repo rule). Per-commit observable.
2. **`theme.css` + `viewer-tokens.css` Stylelint-enforced** — hex outside `var(--token)` forbidden; legacy/modern HSL pinned per file. Per-commit observable.
3. **Axe `color-contrast` scan** in all 4 projects: `warn` during Phase B, **`fail` at Epic 5 close** (5.15). Per-`test:visual`-run observable.
4. **Baseline Acceptance Gate is a hook** (5.13a). Observable: `git log --grep='baseline-reviewed:'` shows the line on every baseline-touching commit since Epic 5 close; zero baseline-regen commits in the 30 days post-close lack the line. **First-pass enforcement test**: within 30 days post-close, rule exercised on ≥3 commits.
5. **Visual Coverage Contract** (5.13b) — every interactive primitive in `apps/web/src/ui/` has open-state coverage across `{desktop, mobile} × {light, dark}`. Observable: coverage matrix table at Epic close (5.3 → updated by 5.9) shows 100% green.
6. **`project-context.md` rule_count** 134 → 136. Activity metric — paired with #4's first-pass enforcement test.

**Vision target (not a Success Criterion)**: 90 days post-Epic-5 close, zero light-mode contrast incidents shipped via QD-channel. Current rate ~1 per 2–3 weeks. Tracked at Epic 5 retro and at 90-day review.

---

## Open decisions deferred to PRD / architecture

- **New token surface**: `--color-overlay` / `--color-overlay-foreground` (semantic-additive) vs `bg-background/N` opacity modifiers (token-reuse) for Dialog/Sheet overlays. Architecture extension decides.
- **Stylelint integration mechanism**: `npm run lint` chain (`eslint . && stylelint "**/*.css"`) vs single config with stylelint-orchestration. Decide in architecture; the chain is the simpler default.
- **Hook implementation choice**: `husky` (adds dev-dependency; standard) vs hand-rolled `.git/hooks/pre-commit` shell script (no dependency, opaque to other dev tooling). Decide in architecture; husky is the simpler default if it's already implied by any other dependency.
- **5.13b mechanism**: extend 5.13a hook vs separate ESLint custom rule. Decide in architecture based on which mechanism gives a faster developer feedback loop.
- **`@axe-core/playwright` per-test escape hatches**: which known-noisy nodes (overlapping z-index, disabled controls) need `disableRules('color-contrast')` per-test. Discovered during 5.12.
- **Recurring baseline audit cadence**: monthly operator-led informal vs codified as scheduled BMAD chore. Default: informal first, codify if pattern proves out. Revisit at Epic 5 retro.
- **Selector-policy lint rule for spec files** (PL-locale enforcement): defer to a follow-up — Phase A coverage matrix may reveal if violation count justifies it.

## Cross-references

- `_bmad-output/planning-artifacts/prd.md` — extend with `## Initiative 3` section; FRs from this distillate's Phase A/C-early/B/C-prevention tables.
- `_bmad-output/planning-artifacts/architecture.md` — extend with `## Initiative 3` section; decisions (token surface, lint integration, hook mechanism, 5.13b mechanism, axe scope).
- `_bmad-output/planning-artifacts/epics.md` — append Epic 5 entry, ~14 stories enumerated above (5.1–5.3, 5.10–5.12, 5.4–5.9 with 5.9 sub-split, 5.13a/5.13b/5.13, 5.14, 5.15).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Epic 5 entries to be added after story-creation cycle.
- `_bmad-output/project-context.md` — target for two new rules (Phase C-prevention 5.13).
- `_bmad-output/triage-backlog.md` — 90-day vision-target tracking bucket.
