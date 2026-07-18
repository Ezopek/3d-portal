---
baseline_commit: 49fd86ebbdb11a0b8c8e403f3cff88b87fcc8edc
---

# Story 41.2: Alembic migration `0018_facet_tags` (additive facet-tag schema; category drop deferred to E42 cut-over)

Status: ready-for-dev

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

- [ ] Task 1 — Write additive migration `0018_facet_tags.py` (AC: #1, #2, #3, #4)
  - [ ] Copy the module skeleton/header conventions from `0017_model_note_bilingual.py` (docstring with Revision ID / Revises / rationale; `from __future__ import annotations`; `import sqlalchemy as sa`; `from alembic import op`; the four revision globals). Set `revision = "0018_facet_tags"`, `down_revision = "0017_model_note_bilingual"`.
  - [ ] `upgrade()`: create `tag_group` (columns + types exactly per AC #2, copying the column-shape idiom from `0004:22-37`), then `op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)`.
  - [ ] `upgrade()`: `batch_alter_table("tag")` — add `group_id` (nullable), `group_position` (NOT NULL server_default `"0"`), `create_foreign_key("fk_tag_group_id", "tag_group", ["group_id"], ["id"], ondelete="SET NULL")`.
  - [ ] Confirm `upgrade()` contains **zero** references to `model`, `category_id`, or `category`. Add an explicit code comment stating the destructive drop is deferred to the E42 cut-over (with the reason: prod deployability + forward-only irreversibility).
- [ ] Task 2 — Write reversible `downgrade()` (AC: #5)
  - [ ] `batch_alter_table("tag")`: `drop_column("group_position")`, `drop_column("group_id")` (FK removed with the column via batch copy — do NOT `drop_constraint` an unnamed-on-SQLite FK).
  - [ ] `op.drop_index("uq_tag_group_slug", table_name="tag_group")`, `op.drop_table("tag_group")`.
- [ ] Task 3 — Migration round-trip + deferral-guard test (AC: #6, #7)
  - [ ] New `apps/api/tests/test_migration_0018.py`. Copy the `_alembic_cfg` + `_round_trip_db` fixture and `_objects(db_path)` helper **verbatim** from `test_migration_0012.py` (they override `DATABASE_URL` because `env.py` reads `get_settings().database_url`, and clear the `get_settings`/`get_engine` lru_caches). Add a `_tag_columns` / `_columns(table)` PRAGMA helper mirroring `test_migration_0014.py:_user_columns` to assert `group_id`/`group_position` shape.
  - [ ] Assertions per AC #6: forward creates `tag_group` + `uq_tag_group_slug` + tag columns; `category`/`model.category_id` still present (deferral proof); downgrade removes only the facet objects; re-upgrade restores them.
  - [ ] (Optional, if cheap) assert `alembic heads` yields a single head — or rely on `command.upgrade(cfg, "head")` succeeding unambiguously (multiple heads would raise).
- [ ] Task 4 — Verify (AC: #7, #8)
  - [ ] `python -m alembic -c apps/api/alembic.ini heads` (run from `apps/api`, or `cd apps/api && alembic heads`) shows exactly `0018_facet_tags (head)`.
  - [ ] `ruff check --fix` + `ruff format` on `apps/api`.
  - [ ] Run the backend suite 3× and confirm identical, all-green pass counts (expect prior green count + the new `test_migration_0018` cases).
- [ ] Task 5 — Record the deferred destructive DDL (AC: #4)
  - [ ] Append a "Deferred from: story 41.2" section to `_bmad-output/implementation-artifacts/deferred-work.md` describing the destructive migration owed by the E42 cut-over (see Dev Notes → Deferred work).

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

### Debug Log References

### Completion Notes List

### File List

## Change Log

## Story Creation Questions / Decisions for Operator

1. **Scoping decision made in this story (please confirm) — additive/destructive split of migration `0018`.** Per the coupling story 41.1 escalated (its Question #2), this story implements migration `0018_facet_tags` as **additive-only** (create `tag_group`; add `tag.group_id`/`group_position`; reversible `downgrade`) and **defers** the destructive `drop model.category_id` + `drop_table("category")` (forward-only) to a new migration that lands **atomically with the E42 story removing `Category` from the ORM/app** (suggested `0019_drop_category`). Reason: prod applies `alembic upgrade head` against the HEAD image on any deploy; a forward-only destructive `0018` on `main` before the ORM removal would irrecoverably brick prod catalog/share. This deviates from the literal `NFR25-SCHEMA-MIGRATION-1` mapping (which puts the drop in 41.2) — confirm the split, or instruct to ship the full destructive `0018` now (accepting the deploy-window landmine). The sprint-status key `…-drop-category` is treated as a slug only.
2. **E42 planning follow-up (not a 41.2 blocker):** ensure sprint-planning/create-story for E42 assigns the deferred `0019_drop_category` migration to the same story that removes `class Category` + `Model.category_id` from `_entities.py` (likely 42.5 or a dedicated cut-over story), so ORM and migration head stay in parity and the forward-only drop is never on `main` ahead of the ORM removal. Recorded in `deferred-work.md`.

---

_Ultimate context engine analysis completed — comprehensive developer guide created._
