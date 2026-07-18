---
baseline_commit: 49fd86ebbdb11a0b8c8e403f3cff88b87fcc8edc
---

# Story 41.2: Alembic migration `0018_facet_tags` (additive facet-tag schema; category drop deferred to E42 cut-over)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a catalog platform maintainer,
I want the Alembic **production** schema brought into parity with the facet-tag ORM landed in 41.1 — via a forward migration that creates `tag_group` and adds `tag.group_id`/`tag.group_position` — **without** dropping `category`/`model.category_id` yet,
so that production is deployable at every commit and the destructive category retirement lands atomically with the E42 backend cut-over that actually removes `Category` from the ORM and app code.

## Acceptance Criteria

1. **New migration `apps/api/migrations/versions/0018_facet_tags.py`** with `revision = "0018_facet_tags"`, `down_revision = "0017_model_note_bilingual"` (full slug — mirror `0017`'s own `down_revision` style at `0017_model_note_bilingual.py:29`), `branch_labels = None`, `depends_on = None`. It is the single new Alembic head after this story.
2. **`upgrade()` creates `tag_group`** via `op.create_table("tag_group", ...)` with columns matching the ORM (`_entities.py:61-77`): `id` (`sa.Uuid(as_uuid=True)`, `primary_key=True`), `slug` (`sa.String()`, `nullable=False`), `name_en` (`sa.String()`, `nullable=False`), `name_pl` (`sa.String()`, `nullable=True`), `position` (`sa.Integer()`, `nullable=False`, `server_default="0"`), `created_at` + `updated_at` (`sa.DateTime()`, `nullable=False`, **no** `server_default` — mirrors every other table in `0004`). Then `op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)` — the index name **must** be exactly `uq_tag_group_slug` to match the ORM (`_entities.py:66`) and satisfy the drift-guard deferred from 41-1.
3. **`upgrade()` adds group membership to `tag`** via `with op.batch_alter_table("tag") as b:` (batch required on SQLite to add a FK): `b.add_column(sa.Column("group_id", sa.Uuid(as_uuid=True), nullable=True))`, `b.add_column(sa.Column("group_position", sa.Integer(), nullable=False, server_default="0"))`, `b.create_foreign_key("fk_tag_group_id", "tag_group", ["group_id"], ["id"], ondelete="SET NULL")`. No index on `group_id` (matches 41.1 ORM — `Tag.group_id` has no `index=True`).
4. **`upgrade()` does NOT touch `model`, `model.category_id`, or `category`.** No `drop_column`, no `drop_index`, no `drop_table`, no `drop_constraint` on those objects. The destructive category-retirement DDL is explicitly **deferred to the E42 backend cut-over** (see Dev Notes → Sequencing determination). This is the single most important guardrail of this story.
5. **`downgrade()` is implemented and reversible** (this migration is purely additive, so — unlike the destructive drop — it is fully recoverable): inside `with op.batch_alter_table("tag") as b:` drop `group_position` then `group_id` (the batch table-copy removes the inline FK with the column — precedent `0010:36-38`, `0005:125-126`); then `op.drop_index("uq_tag_group_slug", table_name="tag_group")` and `op.drop_table("tag_group")`. Order: reverse of `upgrade()`.
6. **`alembic upgrade head` and a full round-trip succeed.** A new `apps/api/tests/test_migration_0018.py` (mirroring `test_migration_0012.py` / `test_migration_0014.py` verbatim in fixture shape) asserts: after `command.upgrade(cfg, "head")` — `tag_group` table + `uq_tag_group_slug` index exist, and `tag` has columns `group_id` (nullable) + `group_position` (NOT NULL, default `"0"`); after `command.downgrade(cfg, "0017_model_note_bilingual")` — `tag_group` + `uq_tag_group_slug` are gone and `tag.group_id`/`tag.group_position` are gone while `tag.slug`/`ix_tag_slug` survive; after re-`upgrade(head)` — all facet objects return (idempotency). Also assert **`category` table and `model.category_id` still exist after `upgrade(head)`** (proves the drop was NOT performed — the deferral guardrail, AC #4).
7. **Alembic has exactly one head after this story** (`0018_facet_tags`). Verify with `alembic heads` (single line) — no branch/multiple-heads drift.
8. **Backend suite green, 3× consecutive identical pass counts** (NFR25-DETERMINISM-1), plus `ruff check` + `ruff format` clean on `apps/api`. The pre-existing suite (which builds schema from the ORM via `init_schema()`, not Alembic) is unaffected; only the two new migration-round-trip test cases add to the count. No existing test regresses.

## Tasks / Subtasks

- [x] Task 1 — Write additive migration `0018_facet_tags.py` (AC: #1, #2, #3, #4)
  - [x] Copy the module skeleton/header conventions from `0017_model_note_bilingual.py` (docstring with Revision ID / Revises / rationale; `from __future__ import annotations`; `import sqlalchemy as sa`; `from alembic import op`; the four revision globals). Set `revision = "0018_facet_tags"`, `down_revision = "0017_model_note_bilingual"`.
  - [x] `upgrade()`: create `tag_group` (columns + types exactly per AC #2, copying the column-shape idiom from `0004:22-37`), then `op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)`.
  - [x] `upgrade()`: `batch_alter_table("tag")` — add `group_id` (nullable), `group_position` (NOT NULL server_default `"0"`), `create_foreign_key("fk_tag_group_id", "tag_group", ["group_id"], ["id"], ondelete="SET NULL")`.
  - [x] Confirm `upgrade()` contains **zero** references to `model`, `category_id`, or `category`. Add an explicit code comment stating the destructive drop is deferred to the E42 cut-over (with the reason: prod deployability + forward-only irreversibility).
- [x] Task 2 — Write reversible `downgrade()` (AC: #5)
  - [x] `batch_alter_table("tag")`: `drop_column("group_position")`, `drop_column("group_id")` (FK removed with the column via batch copy — do NOT `drop_constraint` an unnamed-on-SQLite FK).
  - [x] `op.drop_index("uq_tag_group_slug", table_name="tag_group")`, `op.drop_table("tag_group")`.
- [x] Task 3 — Migration round-trip + deferral-guard test (AC: #6, #7)
  - [x] New `apps/api/tests/test_migration_0018.py`. Copy the `_alembic_cfg` + `_round_trip_db` fixture and `_objects(db_path)` helper **verbatim** from `test_migration_0012.py` (they override `DATABASE_URL` because `env.py` reads `get_settings().database_url`, and clear the `get_settings`/`get_engine` lru_caches). Add a `_tag_columns` / `_columns(table)` PRAGMA helper mirroring `test_migration_0014.py:_user_columns` to assert `group_id`/`group_position` shape.
  - [x] Assertions per AC #6: forward creates `tag_group` + `uq_tag_group_slug` + tag columns; `category`/`model.category_id` still present (deferral proof); downgrade removes only the facet objects; re-upgrade restores them.
  - [x] (Optional, if cheap) assert `alembic heads` yields a single head — or rely on `command.upgrade(cfg, "head")` succeeding unambiguously (multiple heads would raise).
- [x] Task 4 — Verify (AC: #7, #8)
  - [x] `python -m alembic -c apps/api/alembic.ini heads` (run from `apps/api`, or `cd apps/api && alembic heads`) shows exactly `0018_facet_tags (head)`.
  - [x] `ruff check --fix` + `ruff format` on `apps/api`.
  - [x] Run the backend suite 3× and confirm identical, all-green pass counts (expect prior green count + the new `test_migration_0018` cases).
- [x] Task 5 — Record the deferred destructive DDL (AC: #4)
  - [x] Append a "Deferred from: story 41.2" section to `_bmad-output/implementation-artifacts/deferred-work.md` describing the destructive migration owed by the E42 cut-over (see Dev Notes → Deferred work).

## Dev Notes

### Sequencing determination — 41.2 is the ADDITIVE half of 0018; the category drop is DEFERRED to E42 (READ FIRST)

The epic sketch and `NFR25-SCHEMA-MIGRATION-1` name a single migration `0018_facet_tags_drop_category` that both **adds** the facet schema **and drops** `category` + `model.category_id`, forward-only with a raising `downgrade`. **This story deliberately implements only the additive half and defers the destructive half.** This is the direct resolution of the coupling that story 41.1 escalated to be decided here (41-1 "Story Creation Questions / Decisions for Operator" #2, and the code-review decision-needed the operator dismissed as "adequately documented as Question #2"). Rationale, verified against the code:

- **41.1 was additive-only.** `class Category` and `Model.category_id` are **still in the ORM** (`_entities.py:29-58` for `Category`; `:110-112` for `Model.category_id`, still `NOT NULL`) and still referenced live across the backend (`share/router.py`, `sot/service.py`, `sot/admin_service.py`, `sot/router.py`, `sot/admin_router.py`) plus dozens of test fixtures. Removing them from the ORM is E42 work (42.1/42.3/42.5), not landed yet.
- **Production applies migrations by running `alembic upgrade head` against the image built from HEAD** — a manual step in the deploy ritual (`docs/operations.md:234`, step 4 of `infra/scripts/deploy.sh`; the container `CMD` is just `uvicorn`, no migrate-on-boot). There is **no** automatic migrate-on-merge, but any deploy — including an unrelated hotfix — during the multi-week E41→E47 window would run the full chain to head.
- **A destructive, forward-only 0018 on `main` is therefore a deploy landmine.** If `alembic upgrade head` runs it while the deployed image's ORM still has `Category`/`category_id` and live routes still `select(Category)`, prod drops the `category` table + column and the catalog/share endpoints 500. Worse, `downgrade()` raises `NotImplementedError` by design → **unrecoverable**: re-deploying the previous image gives an app expecting a `category` table that no longer exists. Every *other* mid-initiative breakage is a rollback-able code state; the destructive migration is the one irreversible one. It must not exist on `main` until E42 has removed the ORM + app references.
- **The green-before-merge gate does NOT force the drop into this story** (unlike 41.1, where removing `Category` from the ORM broke pytest *collection*). The test suite builds schema from the ORM via `init_schema()` → `create_all()` (`session.py:39`) and **never runs Alembic**; migration tests run the chain in **isolation** against a throwaway SQLite DB. So the additive-only migration keeps everything green, and there is no ORM↔migration parity test that a deferred drop would trip (confirmed: no `compare_metadata`/autogenerate test exists — deferred-work item from 41-1).

**Net:** 41.2 delivers `0018_facet_tags` (additive, reversible). The destructive `drop model.category_id` + `drop_table("category")` moves to a **new migration** created **atomically with the E42 story that removes `Category` from the ORM** (candidate: a `0019_drop_category` alongside 42.5 / the final E42 cut-over). This preserves "main is deployable at every commit" and keeps ORM↔migration parity at every point. The sprint-status key still reads `…-drop-category`; treat it as a slug only — exactly as 41.1's key said `…-category-removal` for an additive-only story (operator-accepted precedent). **Flag this determination for operator confirmation** (see Story Creation Questions).

### Exact DDL facts — do NOT guess names/types (introspected from `0004_entity_tables.py`)

- **UUID columns** in every migration use `sa.Uuid(as_uuid=True)` (`0004:24`, etc.). Use it for `tag_group.id` and `tag.group_id`.
- **Timestamps** are `sa.DateTime(), nullable=False` with **no** `server_default` in migrations (`0004:34-35`) — the ORM supplies values via `default_factory=_now_utc`. Match that for `tag_group.created_at`/`updated_at`.
- **Integer defaults**: `position`/`group_position` → `sa.Integer(), nullable=False, server_default="0"` (mirrors `source`/`status` server_defaults at `0004:79-80`; matches ORM `Field(default=0)`).
- **`uq_tag_group_slug`** is the required index name (ORM `_entities.py:66` names it explicitly for exactly this parity). The `Category` precedent (explicit-named index to match Alembic) is `_entities.py:31-47`.
- **The category drop you are NOT doing** (for reference / the future E42 migration): index is `ix_model_category_id` (`0004:91`); the `category.id` FK on `model` is an **unnamed inline** `sa.ForeignKey` (`0004:73-78`) so the future batch drop needs **no** `drop_constraint`; `category` table's own indexes `ix_category_parent`, `ix_category_slug`, `uq_category_root_slug` go with `drop_table` (`0004:38-51`, `0004:250-253`).

### Files being modified/created — current state & what must be preserved

- **CREATE** `apps/api/migrations/versions/0018_facet_tags.py` — the migration. Current head is `0017_model_note_bilingual` (`versions/` listing; no `0018*` exists yet). Preserve the single-linear-head chain: `down_revision = "0017_model_note_bilingual"`.
- **CREATE** `apps/api/tests/test_migration_0018.py` — round-trip + deferral guard. Mirror `test_migration_0012.py` (create-table round-trip) and `test_migration_0014.py` (column-shape PRAGMA). Both use a tmpdir DB + `DATABASE_URL` override + lru_cache clears — copy verbatim, do not invent a new harness.
- **MODIFY** `_bmad-output/implementation-artifacts/deferred-work.md` — append the deferred destructive-DDL note.
- **Do NOT modify** `_entities.py` (41.1 already landed the ORM; 41.2 is migration-only), `__init__.py`, or any `sot/`/`share/`/`category`-referencing module or test. The ORM is the source of truth this migration is catching up to — it must not change here.
- No frontend changes (E43+ owns FE).

### env.py / alembic wiring (why the test fixture is shaped the way it is)

- `apps/api/alembic.ini` + `migrations/env.py`: `env.py` reads the DSN from `get_settings().database_url` and **ignores** the URL set on the Alembic `Config` object directly. That is why the round-trip fixture sets the `DATABASE_URL` env var (not `cfg.set_main_option` alone) **and** clears `get_settings`/`get_engine` lru_caches before/after. Copy the fixture exactly from `test_migration_0012.py:38-61`.
- `command.upgrade(cfg, "head")` runs the entire `0001→0018` chain against the fresh throwaway DB; `command.downgrade(cfg, "0017_model_note_bilingual")` steps back one revision. This is the established pattern (`test_migration_0014.py:65-100`).

### Testing standards

- Backend pytest, `asyncio_mode = "auto"`; the migration test is a plain sync test using `alembic.command` + `sqlite3` introspection (no `TestClient`, no `session` fixture, no `asyncio`). It manages its own DB lifecycle via the copied `_round_trip_db` fixture.
- Determinism (NFR25-DETERMINISM-1): run the full backend suite 3× and confirm identical green counts before marking done. `ruff` clean (`E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312).
- This story partially discharges the 41-1 deferred "ORM↔migration drift guard" item: `test_migration_0018` pins the `uq_tag_group_slug` name and the `group_id`/`group_position` shape against the migration. (A full `compare_metadata` autogenerate diff remains out of scope — note it stays deferred.)

### Deferred work (append to `deferred-work.md`)

Destructive category-retirement DDL — `op.drop_index("ix_model_category_id")` + `op.batch_alter_table("model").drop_column("category_id")` + `op.drop_table("category")`, forward-only (`downgrade` raises) — is **owed by the E42 backend cut-over** and must land in the **same commit/migration** as the ORM removal of `class Category` + `Model.category_id` (E42 stories 42.1/42.3/42.5). It was pulled out of 41.2 (migration `0018_facet_tags` is additive-only) because a forward-only destructive migration on `main` bricks prod on any `alembic upgrade head` deploy performed before the ORM/app `Category` references are gone, and forward-only makes it unrecoverable. Suggested revision id when it lands: `0019_drop_category` (`down_revision = "0018_facet_tags"`).

### Project Structure Notes

- Migration files live in `apps/api/migrations/versions/`, named `NNNN_slug.py`, revision id == filename stem. Migration tests live in `apps/api/tests/test_migration_NNNN.py`. Both conventions are followed exactly here.
- No variance from project structure. The only intentional deviation from the *epic sketch* is the additive/destructive split documented above, kept inside the same story boundary and file-naming otherwise unchanged.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 41.2 — Alembic migration `0018_facet_tags_drop_category`] — migration sketch (steps 1-4) + `NFR25-SCHEMA-MIGRATION-1`.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md#4.2] — `0018` DDL sketch (lines 128-170); Architecture Decision AV (index `ix_model_category_id` named @ `0004:91`; `category.id` FK unnamed inline @ `0004:73-78`; `down_revision="0017_model_note_bilingual"`).
- [Source: _bmad-output/implementation-artifacts/41-1-taggroup-entity-tag-membership-category-removal.md] — additive-only precedent; Question #2 (destructive coupling escalated to 41.2); review deferred "ORM↔migration drift guard → `test_migration_0018`".
- [Source: _bmad-output/implementation-artifacts/deferred-work.md] — 41-1 deferred drift-guard + unindexed-FK items.
- [Source: apps/api/migrations/versions/0004_entity_tables.py:22-95] — `category`/`tag`/`model` create DDL; exact column types, index names, unnamed inline FK.
- [Source: apps/api/migrations/versions/0017_model_note_bilingual.py:23-55] — module skeleton; `revision`/`down_revision` full-slug style; `batch_alter_table` add-column idiom.
- [Source: apps/api/migrations/versions/0010_drop_model_legacy_id.py / 0005_user_uuid_audit_log.py] — SQLite batch drop-column removes inline FK without `drop_constraint`.
- [Source: apps/api/tests/test_migration_0012.py:23-70] — round-trip fixture (`_alembic_cfg`, `_round_trip_db`, `_objects`) to copy verbatim; create-table assertion style.
- [Source: apps/api/tests/test_migration_0014.py:34-101] — column-shape PRAGMA helper + downgrade/re-upgrade idempotency assertions.
- [Source: apps/api/app/core/db/models/_entities.py:61-96] — `TagGroup` + `Tag.group_id`/`group_position` ORM the migration must match (`uq_tag_group_slug` @ :66).
- [Source: apps/api/app/core/db/session.py:39] — `init_schema` = `create_all()`: test/dev schema source (migrations don't run in the suite).
- [Source: docs/operations.md:229-234] — deploy ritual; `alembic upgrade head` is a manual step against the HEAD-built image (why a destructive migration on main is a deploy landmine).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (BMAD dev-story)

### Debug Log References

- Full backend suite ×3 (determinism, NFR25-DETERMINISM-1): `uv run pytest -q -p no:cacheprovider` → **1671 passed, 3 skipped** on all three runs (364s / 377s / 379s). The count includes the single new node `test_migration_0018_round_trip`; the pre-existing suite is unaffected as expected (schema built from ORM via `init_schema()`, not Alembic).
- `uv run alembic -c alembic.ini heads` → `0018_facet_tags (head)` (single line — no branch/multi-head drift, AC #7).
- `ruff check` + `ruff format --check` on the two new files → clean.
- TDD: `test_migration_0018` written first and confirmed RED (chain stopped at 0017, `tag_group` absent) before the migration was authored; GREEN after. One assertion adjusted: SQLite renders the batch-reflected `group_position` server_default as `'0'` (quoted), so the test normalizes with `.strip("'")` — verifies NOT NULL + default-zero semantics regardless of SQLite's quoting.

### Completion Notes List

- Implemented **additive-only** migration `0018_facet_tags` exactly as scoped (operator-confirmed additive/destructive split; dev-go granted). `upgrade()` creates `tag_group` (+ `uq_tag_group_slug` unique index, name pinned to match ORM `_entities.py:66`) and adds `tag.group_id` (nullable) / `tag.group_position` (NOT NULL, `server_default="0"`) with FK `fk_tag_group_id` → `tag_group.id` `ON DELETE SET NULL` via `batch_alter_table`.
- **Deferral guardrail (AC #4) honored:** `upgrade()` contains zero references to `model`, `category_id`, or `category`; an explicit code comment records that the destructive category-retirement DDL is deferred to the E42 cut-over. `test_migration_0018` asserts `category` table + `model.category_id` still exist after `upgrade(head)` as an executable proof the drop was NOT performed.
- `downgrade()` is fully reversible (reverse of upgrade: drop `group_position`→`group_id` in batch, then drop index, then drop `tag_group`); round-trip + re-upgrade idempotency verified. `tag`/`tag.slug`/`ix_tag_slug` survive the downgrade.
- Recorded the deferred destructive DDL (`0019_drop_category`, forward-only, must land atomically with the E42 ORM removal of `Category`) in `deferred-work.md`.
- No changes to `_entities.py`, `sot/`, `share/`, or any `category`-referencing module/test — migration-only story. No commit/push/deploy/live-DB actions performed (per operator scope).
- ✅ Resolved review finding [LOW] Test-coverage gap: extended `test_migration_0018.py` with an executable `PRAGMA foreign_key_list(tag)` assertion proving the `tag.group_id` → `tag_group.id` FK carries `ON DELETE SET NULL` after `upgrade(head)`, is gone after `downgrade`, and is restored after re-`upgrade`. Test-only change (new `_foreign_keys` helper + 3 assertions); no migration/production code touched — the FK was already correct. Focused migration suite green (21 passed), ruff clean.

### File List

- **CREATE** `apps/api/migrations/versions/0018_facet_tags.py`
- **CREATE** `apps/api/tests/test_migration_0018.py`
- **MODIFY** `_bmad-output/implementation-artifacts/deferred-work.md` (dev confirmation + destructive-DDL owed by E42)
- **MODIFY** `_bmad-output/implementation-artifacts/sprint-status.yaml` (41-2 status: ready-for-dev → in-progress → review)

## Change Log

- 2026-07-18 — Story 41.2 implemented: additive, reversible Alembic migration `0018_facet_tags` (creates `tag_group`; adds `tag.group_id`/`group_position`; FK `fk_tag_group_id` ON DELETE SET NULL) + `test_migration_0018` round-trip/deferral-guard test. Destructive category drop deferred to E42 (`0019_drop_category`). Suite green 3× (1671 passed, 3 skipped); single Alembic head `0018_facet_tags`; ruff clean. Status → review.
- 2026-07-18 — Addressed native review findings — 1 item resolved [LOW]: added executable `PRAGMA foreign_key_list(tag)` assertion in `test_migration_0018.py` (FK → `tag_group.id`, `ON DELETE SET NULL`; absent after downgrade; restored after re-upgrade). Test-only; migration/production code unchanged. Focused migration tests green (21 passed); ruff check + format clean. Status stays review.
- 2026-07-18 — Final native BMAD re-review **APPROVE** and independent Aider review **APPROVE**; controller focused gate green (21 migration tests, 7 story-focused tests, single Alembic head, ruff/format, diff check). Status → done.

## Story Creation Questions / Decisions for Operator

1. **Scoping decision made in this story (please confirm) — additive/destructive split of migration `0018`.** Per the coupling story 41.1 escalated (its Question #2), this story implements migration `0018_facet_tags` as **additive-only** (create `tag_group`; add `tag.group_id`/`group_position`; reversible `downgrade`) and **defers** the destructive `drop model.category_id` + `drop_table("category")` (forward-only) to a new migration that lands **atomically with the E42 story removing `Category` from the ORM/app** (suggested `0019_drop_category`). Reason: prod applies `alembic upgrade head` against the HEAD image on any deploy; a forward-only destructive `0018` on `main` before the ORM removal would irrecoverably brick prod catalog/share. This deviates from the literal `NFR25-SCHEMA-MIGRATION-1` mapping (which puts the drop in 41.2) — confirm the split, or instruct to ship the full destructive `0018` now (accepting the deploy-window landmine). The sprint-status key `…-drop-category` is treated as a slug only.
2. **E42 planning follow-up (not a 41.2 blocker):** ensure sprint-planning/create-story for E42 assigns the deferred `0019_drop_category` migration to the same story that removes `class Category` + `Model.category_id` from `_entities.py` (likely 42.5 or a dedicated cut-over story), so ORM and migration head stay in parity and the forward-only drop is never on `main` ahead of the ORM removal. Recorded in `deferred-work.md`.

## Senior Developer Review (native, adversarial)

- **Reviewer:** independent native BMAD reviewer (fresh context, no implementer transcript)
- **Date:** 2026-07-18
- **Outcome:** **APPROVE**

### Verified

- **AC #1** — `revision="0018_facet_tags"`, `down_revision="0017_model_note_bilingual"`, `branch_labels=None`, `depends_on=None`. `alembic heads` → `0018_facet_tags (head)` (single head, executably verified). Chain is strictly linear; no other file has `down_revision` → `0017`.
- **AC #2** — `tag_group` columns match ORM `_entities.py:61-77` exactly (UUID PK, `slug`/`name_en` NOT NULL, `name_pl` nullable, `position` Integer NOT NULL `server_default="0"`, `created_at`/`updated_at` DateTime NOT NULL with no server_default — matches 0004 idiom). `uq_tag_group_slug` unique index name pinned to ORM `_entities.py:66`.
- **AC #3** — batch add `group_id` (nullable) + `group_position` (NOT NULL `server_default="0"`); FK `fk_tag_group_id` → `tag_group.id` `ON DELETE SET NULL` via `batch_alter_table`. Matches ORM `Tag.group_id`/`group_position`.
- **AC #4 (guardrail)** — `upgrade()` has zero references to `model`/`category_id`/`category`; explicit deferral comment present; `test_migration_0018` asserts `category` table + `model.category_id` survive `upgrade(head)`. Deferral is executably proven.
- **AC #5** — `downgrade()` is exact reverse (drop `group_position`→`group_id` in batch, drop index, drop table); FK removed by batch table-copy (no `drop_constraint`).
- **AC #6/#7** — `test_migration_0018.py` fixture matches `test_migration_0012.py` verbatim + `_columns` PRAGMA helper from `test_migration_0014.py`. Test **passes**; all 14 `test_migration_*` pass together (no `DATABASE_URL`/lru_cache leakage). `env.py:12` overrides `sqlalchemy.url` with `get_settings().database_url`, so the fixture's `DATABASE_URL` override correctly targets the tmpdir DB.
- **AC #8** — `ruff check` + `ruff format --check` clean on both new files. Scope clean: only migration + test + `sprint-status.yaml` + `deferred-work.md` touched; ORM/`sot`/`share` untouched.

### Non-blocking notes

- **[LOW] Test-coverage gap:** the round-trip test verifies `group_id`/`group_position` shape but never executably asserts the FK (`PRAGMA foreign_key_list(tag)` → `fk_tag_group_id`, `on_delete=SET NULL`). FK correctness rests on source inspection only. Optional to add before E42 relies on the SET-NULL semantics.
  - **[RESOLVED 2026-07-18]** `test_migration_0018.py` now adds a `_foreign_keys(db_path, table)` helper over `PRAGMA foreign_key_list` and executably asserts, after `upgrade(head)`, that `tag` has exactly one `group_id` FK → `tag_group.id` with `on_delete == "SET NULL"`; asserts the FK is **absent** after `downgrade` to 0017 (dropped with the column via batch table-copy); and asserts it is **restored** with the same SET-NULL semantics after re-`upgrade(head)`. Note: SQLite's `PRAGMA foreign_key_list` does not expose the constraint *name*, so the assertion pins target table/column + ON DELETE action (not the `fk_tag_group_id` literal — that stays a source/`compare_metadata`-only concern, per the INFO note below). No migration/production code changed — the FK was already correct; the test just makes it executably proven. Focused migration tests green (21 passed), ruff check + format clean.
- **[INFO] FK-name parity:** ORM `uuid_fk` emits an unnamed `ForeignKey` (SQLAlchemy auto-name) while the migration names it `fk_tag_group_id`. Harmless on SQLite/create_all; would surface only in a future `compare_metadata` drift guard, which is explicitly deferred.
- **[INFO] Determinism claim:** dev-reported full-suite 3× (1671p/3s) was not independently re-run here (~18 min/run); new test + all 14 migration tests independently verified green. Regression risk is negligible (suite builds schema from ORM via `init_schema()`, never runs Alembic).

---

_Ultimate context engine analysis completed — comprehensive developer guide created._
