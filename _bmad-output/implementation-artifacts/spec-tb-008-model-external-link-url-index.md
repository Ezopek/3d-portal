---
title: 'TB-008 ModelExternalLink.url index for the dedup filter'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
route: 'one-shot'
---

# TB-008 ModelExternalLink.url index for the dedup filter

## Intent

**Problem:** TB-004 (commit `afaa847`, 2026-05-11) added `?external_url=<url>` query param to `GET /api/models`; service-layer filter subqueries `ModelExternalLink.url`. The column had no index → full table scan. Tolerable at homelab scale (~200 rows on 2026-05-12) but not under any future bulk-import sweep. TB-004's adversarial review surfaced this as P2 #3 (defer + promote).

**Approach:** Add `Index("ix_model_external_link_url", "url")` to `ModelExternalLink.__table_args__`. Non-unique because the codebase explicitly tests the multi-model-per-URL case (`test_list_models_external_url_combines_with_other_filters` seeds two models pointing at the same target URL). New Alembic migration `0011_index_model_external_link_url.py` chained `0010_drop_model_legacy_id → 0011`. Mirrors the additive-index pattern from migration 0009 (no `batch_alter_table` — non-destructive).

## Files

- [`apps/api/app/core/db/models/_entities.py`](../../apps/api/app/core/db/models/_entities.py) — `ModelExternalLink.__table_args__` gains `Index("ix_model_external_link_url", "url")`.
- [`apps/api/migrations/versions/0011_index_model_external_link_url.py`](../../apps/api/migrations/versions/0011_index_model_external_link_url.py) — new migration. Upgrade: `op.create_index(...)`. Downgrade: `op.drop_index(...)`.

## Adversarial review summary

`feature-dev:code-reviewer` (no conversation context) returned 0×P0 + 2×P1 + 2×P2 + 2×P3.

- **P1 #1** (88) — verify the full revision chain resolves. Done: `alembic history --verbose` shows `0011_index_model_external_link_url (head) → 0010_drop_model_legacy_id → 0009 → 0008 → … → 0001`. Chain clean.
- **P1 #2** (85) — revision-ID format consistency. Both 0010 and 0011 use descriptive full strings; 0009 and earlier use bare short tokens. Pattern mixed by project precedent (0006 also uses descriptive). Inheritance from 0010 is consistent. No fix needed beyond the chain verification.
- **P2 #3** (82) — `op.drop_index(..., table_name=...)` keyword arg. Confirmed correct.
- **P2 #4** (80) — non-unique vs unique. Non-unique is correct given the codebase's intentional multi-model-per-URL test fixture. Documented in inline comment.
- **P3 #5** — "~200 rows today" phrasing went stale; rewrote to "low-thousands of rows" + cited the test that exercises the multi-model-per-URL case.
- **P3 #6** — `EXPLAIN QUERY PLAN` test gap is acceptable for homelab scale.

## Verification

- `alembic history --verbose`: chain resolves end-to-end; 0011 is `(head)` with parent 0010.
- `.venv/bin/pytest -q`: 407 passed (no test count change — TB-008 is index-only).
- `.venv/bin/ruff check` + `--format check` on changed files: clean.
- `init_schema(engine)` (dev/test) reads `__table_args__` directly → no SQLModel/Alembic divergence on a fresh DB.
- Production migration applies via `deploy.sh` → `alembic upgrade head` on next deploy.
