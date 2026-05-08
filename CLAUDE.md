# Claude-specific notes

Read `AGENTS.md` first — it is the vendor-neutral source of truth for this repo.

## Conversation language

Conversation with Michał is in Polish. All committed file content (code, docs, commit messages) is in English.

## Cross-repo context

Before non-trivial work, glance at:

- `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md` — catalog schema
- `~/repos/configs/docs/observability-logging-contract.md` — log + trace contract
- `~/repos/configs/docs/glitchtip-agent-guide.md` — frontend error tracking
- `~/repos/orca-profiles/AGENTS.md` — git workflow Michał uses across repos

## Workflow expectations

BMAD owns the workflow in this repo (planning + execution + review). The skill catalog lives in `_bmad/_config/bmad-help.csv`; invoke `bmad-help` if unsure where to start. Typical routing:

- New feature → BMAD planning chain (PRD → architecture → epics & stories → sprint planning → story cycle).
- Drobne zmiany / bugfix → `bmad-quick-dev`.
- Tests on existing code → BMAD `tea` module (`bmad-testarch-test-design`, `bmad-testarch-framework`, etc.).

Execution discipline (TDD red/green/refactor, verification before completion, evidence before assertions, mandatory visual regression for UI changes via `npm run test:visual` from `apps/web/`) is encoded in `_bmad-output/project-context.md` — read it before implementing.
