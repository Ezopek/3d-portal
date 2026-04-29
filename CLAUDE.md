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

Use the `superpowers` plugin skills (`brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `test-driven-development`, `verification-before-completion`) by default. Visual regression is mandatory for UI changes (`npm run test:visual` from `apps/web/`).
