## Repository context

Authoritative documents to consult if needed for the review:

- `_bmad-output/project-context.md` — 136 rules covering tech stack, code quality, framework conventions, and gotchas.
- `_bmad-output/planning-artifacts/prd.md` § "Initiative 3" — capability contract (FRs + NFRs).
- `_bmad-output/planning-artifacts/architecture.md` § "Initiative 3" — architectural decisions A–J.
- `_bmad-output/planning-artifacts/epics.md` § "Epic 5" — story-by-story scope.

The `_bmad-output/` directory is gitignored (operator-local). Reference paths
that exist in the repo (e.g., `apps/web/src/styles/theme.css`) carry their
documentation inline.

## Per-LLM review etiquette

- Quote real file:line ranges, not invented ones.
- If unsure whether a finding is real, flag with a "verify" caveat rather than
  asserting.
- Surface findings only — do not write a fix. The operator decides if a
  fix-up commit lands in-band or as a follow-up story.
