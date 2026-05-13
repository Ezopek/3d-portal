# UI theme + visual-regression review checks (Initiative 3 / Epic 5)

You are reviewing a 3d-portal commit that touches one or more of:

- `apps/web/src/ui/**/*.tsx` (base UI primitives — shadcn/Radix surface)
- `apps/web/src/styles/*.css` (theme tokens, design system)
- `apps/web/src/modules/**/components/**/*.tsx` (consumer components with UI surface)
- `apps/web/tests/visual/*.spec.ts` (Playwright visual specs)

In addition to your default review heuristics, run these four UI-specific checks
and surface any findings as P0/P1/P2/P3 per the existing project convention.

## Check 1 — Color literals in className

Grep the diff for any of the following patterns in JSX `className` attributes:

- `bg-[#...]`, `bg-[rgba(...)]`, `bg-[rgb(...)]`, `bg-[hsl(...)]`, `bg-[oklch(...)]`, `bg-[color(...)]` (and same prefixes with `text-`, `border-`, `fill-`, `stroke-`, `ring-`, `from-`, `to-`, `via-`, `shadow-`, `outline-`, `decoration-`, `caret-`, `accent-`, `placeholder-`).
- Raw Tailwind palette utilities: `(bg|text|border)-(red|blue|green|zinc|gray|slate|stone|neutral|amber|yellow|orange|emerald|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)-N` where N ∈ {50, 100, …, 950}.
- `bg-white`, `bg-black`, `text-white`, `text-black`.

These are forbidden in `apps/web/src/**` per the in-repo ESLint rule. If the diff
introduces any (the rule should catch this at lint time, but a P1 here is
warranted if it slipped through). For files outside `apps/web/src/ui/**`, the
rule is warn-tier; reviewer should note it but it does not block merge.

Tokens to use instead: `bg-card`, `bg-background`, `bg-popover`, `bg-overlay`,
`text-foreground`, `text-card-foreground`, `text-muted-foreground`, `bg-success`,
`bg-warning`, `bg-destructive`, etc. — see `apps/web/src/styles/theme.css`.

## Check 2 — `.dark {}` override completeness

Any new `--color-*` token added to `@theme {}` in `apps/web/src/styles/theme.css`
MUST have a matching declaration in the `.dark {}` block below — UNLESS the
value is intentionally theme-invariant and an inline comment explains the
reason (e.g., `bg-gallery-control` floats over arbitrary photos).

If the diff adds a `--color-*` without the corresponding `.dark` declaration,
flag P1.

## Check 3 — Open-state visual spec coverage

If the diff ADDS a new `apps/web/src/ui/*.tsx` file (a new base primitive
under `apps/web/src/ui/`, not subdirectories), the same commit MUST also stage
a matching `apps/web/tests/visual/<basename>.spec.ts` (or `<basename>-*.spec.ts`)
exercising the open state.

The husky pre-commit hook (`apps/web/.husky/_check-visual-coverage.mjs`)
enforces this; if your review sees a new `apps/web/src/ui/X.tsx` with no
matching `X.spec.ts` in the diff, flag P1 and ask how the hook was bypassed
(`--no-verify`?).

## Check 4 — Selector locale-awareness in new visual specs

Any new `apps/web/tests/visual/*.spec.ts` `getByRole({ name: <regex> })` call
MUST use a PL string in its regex — Playwright runs under forced
`locale: "pl-PL"` (see `apps/web/tests/visual/playwright.config.ts`). An
EN-only regex like `getByRole("button", { name: /open/i })` will silently
fail because the rendered button says "Otwórz".

Examples of correct PL-aware selectors:

- `getByRole("button", { name: /^otwórz\b/i })`
- `getByRole("heading", { name: /pliki/i })`
- `getByRole("heading", { level: 1 })` (role-only, no name regex)

If the diff adds a spec with an EN-only `name:` regex, flag P2 (the test
will likely fail-deterministically on first run; if it passes by accident,
the assertion isn't actually testing the intended element).

## Output format

Per the existing 3d-portal review convention, surface findings as:

```
P0 (blocks merge):
- ...

P1 (must fix before merge OR fix-up commit):
- ...

P2 (worth fixing, may defer to follow-up):
- ...

P3 (nit / nice-to-have):
- ...
```

If no findings under any check: state "Initiative 3 checks: no findings."

Then proceed to your default review heuristics (bug surface, security, perf,
correctness, etc.) as a separate output block.
