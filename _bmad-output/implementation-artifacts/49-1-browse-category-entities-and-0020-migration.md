---
baseline_commit: d6299faed0a2c02469c55bd2f83e7e7ed2691c97
---

# Story 49.1: `BrowseCategory` + `ModelBrowseCategory` entities and Alembic `0020_browse_categories` (atomic)

Status: done

<!-- Native bmad-create-story (action=create), 2026-07-26, Claude Opus 5 agent session, routed via bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story` (menu CS, action `create`). Baseline HEAD 47fe971 on branch docs/init26-e49-1-create-validate, working tree clean. VALIDATED 2026-07-26 by native bmad-create-story (action=validate, menu VS) in a fresh independent context, same baseline HEAD 47fe971 — verdict PASS, 0 critical / 0 important / 3 minor amendments, §7 file set unchanged at 7 files; see §16. Next canonical step: bmad-dev-story (DS), gated on controller confirmation under G26-DEVGO. NO human review of this document has occurred; no Ezop and no Laura sign-off is recorded or implied. -->

## 1. Story

As the **catalog owner**,
I want the **browse-category schema (`browse_category` + `model_browse_category`) to exist in both the SQLModel ORM and the Alembic chain, in one atomic commit**,
so that **every downstream Initiative 26 story (seed, read API, admin governance, frontend) has a stable, additive, reversible data foundation to build on — without touching the retired Initiative 25 category contract.**

**Epic:** E49 — Browse-category data + additive API foundation (backend).
**Story key:** `49-1-browse-category-entities-and-0020-migration`.
**Requirements:** FR26-CAT-1 (structural half), FR26-CAT-2 (structural half), FR26-CAT-4 (schema half only), NFR26-SCHEMA-ADDITIVE-1, NFR26-DETERMINISM-1.
**Architecture:** Decision AX (data model), Decision AZ (migration posture). Decision AY is **not** in this story.

## 2. Gate and authorization posture (truthful)

- **G26-MIGRATE** — open, and **explicitly NOT a destructive gate**. `0020` creates two tables that do not exist, drops nothing, and `downgrade()` is implemented. The destructive-go protocol that governed `0019` (fresh verified backup under `flock /tmp/3d-portal-deploy.lock`, demonstrated restore-readiness, sole-substantive-change deploy, whole-commit revert plan) **does not apply**. Standing pre-deploy backup policy is sufficient. [Source: `architecture.md` § Decision AZ "Deploy posture"]
- **G26-DEVGO** — open. **No implementation may start on this story** until it passes `bmad-create-story:validate` **and** the controller confirms this specific ready story under the user's standing initiative authorization.
- **G26-SCP-RATIFY, G26-ROUTE-PATH, G26-UXGATE, G26-CAT-SET** — closed; none of them gate this story. G26-LIB (Decision BA / E53) is unrelated.
- **This story requires no live-DB action of any kind.** All verification runs against tmpdir SQLite scratch databases created by the test fixtures.

## 3. Binding constraints (carried verbatim; a violation is a story defect, not a preference)

1. `BrowseCategory` and `ModelBrowseCategory` are **new, independent entities**. Nothing from Initiative 25 is un-retired.
2. Model↔category is **M:N**. A model may have **zero** categories, is DB-valid in that state, and stays public/visible.
3. **`Model` gains no column.** `Model.category_id` is never reintroduced — it does not exist at HEAD (`_entities.py:63-88`) and must not appear.
4. `Tag`, `TagGroup`, `ModelTag` semantics are **byte-unchanged**. `Tag.group_id` stays a single nullable FK (no Tag↔TagGroup M:N).
5. A category is **not** a `TagGroup` and is never mechanically generated from tag data.
6. Flat MVP with an optional `parent_id`; the product depth-2 ceiling is enforced in the **service layer** (Story 49.5), **not** in DDL and **not** in this story. Story 49.1 is **structural entities + migration only**.
7. Migration `0020_browse_categories` has `down_revision = "0019_drop_category"`, creates `browse_category` and `model_browse_category`, **reuses no retired table name**, is **additive** and **safely reversible**.
8. ORM entities and the migration are **inseparable**: `test_orm_migration_parity.py` must pass on this story branch, and it fails on either half alone.
9. Composite-pair uniqueness, `model_id` `CASCADE`, `category_id` `RESTRICT`, and reverse-direction indexing.
10. **No** seed content, **no** API/router/service/schema behaviour, **no** UI, **no** model assignments, **no** live-DB action, **no** destructive DDL.

## 4. Acceptance Criteria

**AC-1 — `BrowseCategory` entity exists with the Decision AX shape.**
`apps/api/app/core/db/models/_entities.py` defines `class BrowseCategory(SQLModel, table=True)` with `__tablename__ = "browse_category"` and fields: `id` (uuid PK, `default_factory=uuid.uuid4`), `slug: str`, `name_en: str`, `name_pl: str | None`, `description_en: str | None`, `description_pl: str | None`, `inclusion_criterion: str | None`, `position: int = 0`, `parent_id: uuid.UUID | None` (self-FK → `browse_category.id`, `ondelete="RESTRICT"`, nullable), `created_at`, `updated_at` (both `default_factory=_now_utc`). `__table_args__` carries exactly one entry: `Index("uq_browse_category_slug", "slug", unique=True)`.

**AC-2 — `ModelBrowseCategory` is the `ModelTag` shape verbatim.**
`class ModelBrowseCategory(SQLModel, table=True)` with `__tablename__ = "model_browse_category"`; composite PK `(model_id, category_id)`; `model_id` → `model.id` `ondelete="CASCADE"`; `category_id` → `browse_category.id` `ondelete="RESTRICT"`; `created_at`; `__table_args__ = (Index("ix_model_browse_category_cat_model", "category_id", "model_id"),)`. Both FK columns are built with the shared `uuid_fk(...)` helper (`_helpers.py:50-70`), exactly as `ModelTag` does at `_entities.py:117-127`.

**AC-3 — No implicit index naming.**
`slug` is declared as a bare `slug: str` field and carries **no** `Field(unique=True, index=True)`. The uniqueness and the index come **only** from the explicit `Index("uq_browse_category_slug", ...)`. This is the drift trap `TagGroup` documents in-source at `_entities.py:31-36`; `Tag.slug` (`:51`) is the *opposite*, auto-named pattern and must **not** be copied here.

**AC-4 — Package re-export.**
`apps/api/app/core/db/models/__init__.py` imports `BrowseCategory` and `ModelBrowseCategory` from `._entities` (alphabetical position in the existing import block, `:18-27`) and adds both names to `__all__` (`:40-63`), so `from app.core.db.models import BrowseCategory, ModelBrowseCategory` works at every call site.

**AC-5 — Migration `0020_browse_categories` exists and is chained.**
`apps/api/migrations/versions/0020_browse_categories.py` with `revision = "0020_browse_categories"`, `down_revision = "0019_drop_category"`, `branch_labels = None`, `depends_on = None`. Column types use the `0018` idiom: `sa.Uuid(as_uuid=True)` for uuid columns, `sa.String()`, `sa.Integer(..., nullable=False, server_default="0")` for `position`, `sa.DateTime(), nullable=False` with **no** server_default for timestamps.

**AC-6 — `upgrade()` is structural only, with no seed content.**
`upgrade()` creates `browse_category`, then `op.create_index("uq_browse_category_slug", "browse_category", ["slug"], unique=True)`, then `model_browse_category` with the composite PK, then `op.create_index("ix_model_browse_category_cat_model", "model_browse_category", ["category_id", "model_id"])`. It inserts **zero rows**. It touches **no** existing table — no `batch_alter_table` on `model`, `tag`, `tag_group`, or `model_tag`.

**AC-7 — `downgrade()` is implemented and reversible.**
`downgrade()` drops the two indexes and then `model_browse_category` before `browse_category` (child-before-parent). It does **not** raise `NotImplementedError`. A module docstring records **why** this deliberately departs from `0018`/`0019`, so a future reader does not "fix" it into a raise for false consistency. [Source: `architecture.md` § Decision AZ]

**AC-8 — No retired name is reused.**
Neither the migration nor the ORM mentions the table `category`, the column `model.category_id`, the index `ix_model_category_id`, or any `Category*` Python identifier. `0019_drop_category` is not reverted, not edited, and not re-ordered.

**AC-9 — ORM ↔ Alembic parity: empty `compare_metadata` diff.**
`apps/api/tests/test_orm_migration_parity.py` passes **unmodified**: `alembic upgrade head` on a scratch SQLite DB followed by `compare_metadata(ctx, SQLModel.metadata)` returns `[]`. This is the mechanical proof of story atomicity.

**AC-10 — Single Alembic head, correctly named.**
`ScriptDirectory.get_heads() == ["0020_browse_categories"]`. The existing assertion at `test_migration_0019.py:100-103`, which hard-codes `["0019_drop_category"]`, is updated in this same commit (see §6 finding F-1).

**AC-11 — `0019`'s forward-only contract is still proven, without a false negative.**
`test_migration_0019.py::test_downgrade_from_head_raises_not_implemented` is re-pinned so it still proves `0019.downgrade()` raises. Its binding intent is preserved; only its traversal target changes (see §6 finding F-2).

**AC-12 — Constraint behaviour is executably proven.**
A new entity test file asserts, against a fresh ORM-built SQLite engine with `PRAGMA foreign_keys=ON`: (a) `BrowseCategory` round-trips with defaults (`position == 0`, nullable fields `None`); (b) duplicate `slug` raises `IntegrityError`; (c) duplicate `(model_id, category_id)` pair raises `IntegrityError`; (d) deleting a `Model` removes its `model_browse_category` rows (CASCADE); (e) deleting a `BrowseCategory` that has assignments raises `IntegrityError` (RESTRICT); (f) a `BrowseCategory` with `parent_id = None` persists, a child resolves its parent, and deleting a parent that has a child raises `IntegrityError` (RESTRICT self-FK); (g) a `Model` with **zero** category rows persists and is unaffected.

**AC-13 — Migration-level structural proof.**
A new migration test asserts, against a tmpdir scratch DB: upgrade to `0020_browse_categories` creates both tables and both **named** indexes; `browse_category` has exactly the AC-1 column set with `position` NOT NULL default `0` and `parent_id` nullable; `model_browse_category` has both columns as PK; `PRAGMA foreign_key_list` proves `model_browse_category.model_id → model.id ON DELETE CASCADE`, `model_browse_category.category_id → browse_category.id ON DELETE RESTRICT`, and `browse_category.parent_id → browse_category.id ON DELETE RESTRICT`; downgrade to `0019_drop_category` removes both tables and both indexes while `model`, `tag`, `tag_group`, `model_tag` survive; re-upgrade restores everything identically (idempotency).

**AC-14 — Alembic-vs-SQLModel index-set parity covers the new tables.**
`test_migration_0004.py::test_alembic_and_sqlmodel_emit_equivalent_index_sets` (`:142-200`) has `browse_category` and `model_browse_category` added to its `new_tables` list (`:166-174`), so the two schema-construction paths (Alembic vs `init_schema`) are proven to agree on the new tables' index sets — not merely on the pre-existing ones.

**AC-15 — Existing entity and contract non-regression.**
`Model`, `Tag`, `TagGroup`, `ModelTag`, `ModelFile`, `ModelPrint`, `ModelExternalLink`, `ModelNote` class bodies are unchanged. `test_db_entity_tables.py`, `test_tag_group_entity.py`, `test_db_models.py`, `test_sot_*` (models list/detail, tags, tag-groups, admin tags/tag-groups), `test_route_enforcement_gate.py`, `test_openapi_agent_surface.py`, `test_runbook_openapi_consistency.py` and every worker test pass **unmodified**. No new `/api/*` route exists, so the route-enforcement gate and the OpenAPI surface tests are structurally untouched.

**AC-16 — Merge gate.**
`infra/scripts/check-all.sh` reports **16/16 stages passed** on this branch alone, with no stage skipped. Determinism per NFR26-DETERMINISM-1: 3× consecutive identical `pytest` (apps/api) and `vitest` (apps/web) pass counts.

## 5. Tasks / Subtasks — strict RED → GREEN

> **Discipline:** every task writes its failing assertion **first**, observes the specific failure, then implements. "It should fail" is not evidence — paste the actual failure. Because AC-9 couples the two halves, tasks T2 and T3 land in the **same commit**; the tree is expected to be red between them and that is by design.

### T1 — RED: pin the two existing head-coupled assertions (AC-10, AC-11)

- [x] **T1.1 (RED, evidence-first).** Before any new file exists, run `pytest tests/test_migration_0019.py -q` from `apps/api/` and record that all three tests currently pass at HEAD `47fe971`. This is the baseline the story must not silently break.
- [x] **T1.2.** Edit `tests/test_migration_0019.py::test_single_head_is_0019_drop_category` → assert `script.get_heads() == ["0020_browse_categories"]`, and rename it to `test_single_head_is_0020_browse_categories`. Update the module docstring's "exactly one head named `0019_drop_category`" sentence. **Do not** relax it to a length check — the assertion's value is that it names the head.
- [x] **T1.3.** Edit `test_downgrade_from_head_raises_not_implemented` → `command.upgrade(cfg, "0019_drop_category")` then `command.downgrade(cfg, "-1")`, still expecting `NotImplementedError`; rename to `test_downgrade_from_0019_raises_not_implemented` and add a comment citing this story: `0019` is no longer head, and a `-1` step from `0020` would exercise `0020.downgrade()` (implemented), turning a real forward-only proof into a false negative. This is the same head-pinning adjustment Story 47.5's `d11` applied to the `test_migration_0004/0005/0009/0012/0014` family.
- [x] **T1.4 (RED confirmed).** Re-run `pytest tests/test_migration_0019.py -q`. `test_single_head_is_0020_browse_categories` must now **fail** with `AssertionError: ['0019_drop_category'] != ['0020_browse_categories']`. Paste it. Leave `test_upgrade_head_drops_category_schema` untouched — its assertions are exact-name set membership (`"category" not in objs`), and `browse_category` is a distinct name, so it stays green before and after.

### T2 — RED→GREEN: ORM entities (AC-1, AC-2, AC-3, AC-4)

- [x] **T2.1 (RED).** Create `apps/api/tests/test_browse_category_entity.py` following `test_tag_group_entity.py:18-32` verbatim: in-memory SQLite engine, an explicit `event.listens_for(e, "connect")` handler running `PRAGMA foreign_keys=ON` (SQLite does **not** enforce `ON DELETE` without it), then `SQLModel.metadata.create_all(e)`. Write the AC-12 (a)–(g) assertions. Run it: it must fail at import (`ImportError: cannot import name 'BrowseCategory'`). Paste it.
- [x] **T2.2 (GREEN).** Add `BrowseCategory` and `ModelBrowseCategory` to `_entities.py`, appended after `ModelTag` (or in the file's existing reading order — do not reorder existing classes). Use `uuid_fk(...)` for all three FK columns. `parent_id` self-FK: `parent_id: uuid.UUID | None = Field(default=None, sa_column=uuid_fk("browse_category.id", ondelete="RESTRICT", nullable=True))`. **Two precedents, both in-repo, both stronger than a guess:** the migration-side self-referential `category` table in `0004:21-28` proves it works on SQLite; and the *ORM*-side `class Category` that Story 47.5 deleted (recoverable with `git show 98246d7^:apps/api/app/core/db/models/_entities.py`) used this exact `Field(default=None, sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=True))` line and was `compare_metadata`-green for its whole life. Copy that line's shape; do **not** resurrect the `Category*` identifier or its `uq_category_root_slug` partial index — `browse_category.slug` is globally unique (AC-1), not unique-per-parent.
- [x] **T2.3 (GREEN).** Extend `models/__init__.py`: add both names to the `from ._entities import (...)` block and to `__all__`, preserving alphabetical order.
- [x] **T2.4.** Re-run `pytest tests/test_browse_category_entity.py -q` → all green. Then run `pytest tests/test_orm_migration_parity.py -q` → it must now **FAIL** with a diff reporting two `add_table` entries. **This failure is the required proof of atomicity** (`ORM metadata and migrated schema differ: [('add_table', Table('browse_category', ...)), ('add_table', Table('model_browse_category', ...))]`). Paste it verbatim into the Dev Agent Record. Do not commit here.

### T3 — RED→GREEN: migration `0020_browse_categories` (AC-5, AC-6, AC-7, AC-8, AC-13)

- [x] **T3.1 (RED).** Create `apps/api/tests/test_migration_0020.py` with the AC-13 assertions, mirroring `test_migration_0018.py` — same `_alembic_cfg` / `_objects` / `_columns` / `_foreign_keys` helpers and the same `_round_trip_db` fixture that overrides `DATABASE_URL` (`env.py:12` reads `get_settings().database_url` and **ignores** the URL set on the Alembic `Config`, so the env var is the only knob that works). Pin every traversal to `0020_browse_categories` and `0019_drop_category` — never `"head"` for the downgrade leg. Run it: must fail (`Can't locate revision identified by '0020_browse_categories'`). Paste it.
- [x] **T3.2 (GREEN).** Create `apps/api/migrations/versions/0020_browse_categories.py`. Docstring states: Initiative 26 / Epic 49 / Story 49.1, Decision AX + AZ, additive **and reversible**, ships atomically with the ORM entities, no seed content (41.3 precedent), no table name reused (`0019` dropped `category`; this creates `browse_category`), and the explicit rationale for the implemented `downgrade()`.
- [x] **T3.3 (GREEN).** `upgrade()` — `op.create_table("browse_category", ...)` with `sa.Uuid(as_uuid=True)` PK, `sa.String()` label/description/criterion columns, `sa.Integer(nullable=False, server_default="0")` for `position`, `sa.Column("parent_id", sa.Uuid(as_uuid=True), sa.ForeignKey("browse_category.id", ondelete="RESTRICT"), nullable=True)`, and `sa.DateTime(), nullable=False` timestamps; then `op.create_index("uq_browse_category_slug", "browse_category", ["slug"], unique=True)`; then `op.create_table("model_browse_category", ...)` with both FK columns `primary_key=True` (the `0004:142-157` `model_tag` idiom); then `op.create_index("ix_model_browse_category_cat_model", "model_browse_category", ["category_id", "model_id"])`.
- [x] **T3.4 (GREEN).** `downgrade()` — `op.drop_index("ix_model_browse_category_cat_model", table_name="model_browse_category")`, `op.drop_table("model_browse_category")`, `op.drop_index("uq_browse_category_slug", table_name="browse_category")`, `op.drop_table("browse_category")`. Child table first.
- [x] **T3.5 (GREEN).** `pytest tests/test_migration_0020.py -q` → green. `pytest tests/test_migration_0019.py -q` → all three green (T1's edits now hold). `pytest tests/test_orm_migration_parity.py -q` → **green, empty diff** (AC-9 satisfied). Paste all three.

### T4 — GREEN: index-parity coverage extension (AC-14)

- [x] **T4.1 (RED).** In `tests/test_migration_0004.py::test_alembic_and_sqlmodel_emit_equivalent_index_sets`, add `"browse_category"` and `"model_browse_category"` to the `new_tables` list (`:166-174`). Run it. If it fails, the ORM and the migration disagree on index naming — that is exactly what AC-3 exists to prevent, and the fix belongs in the ORM/migration, never in the test's expectation.
- [x] **T4.2.** Confirm `test_alembic_upgrade_head_creates_all_new_tables` (`:51-81`) still passes without edit — it computes `expected - names`, a subset check, so new tables at head do not break it. If it needed editing, something is wrong; stop and report.

### T5 — Non-regression sweep (AC-15)

- [x] **T5.1.** `pytest -q` in `apps/api/` — full suite green. Explicitly confirm zero edits were needed in `test_db_entity_tables.py`, `test_tag_group_entity.py`, `test_sot_models_list.py`, `test_sot_models_detail.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_sot_admin_tags.py`, `test_sot_admin_tag_groups.py`, `test_route_enforcement_gate.py`, `test_openapi_agent_surface.py`, `test_runbook_openapi_consistency.py`, `test_migration_0004.py` (beyond T4.1), `test_migration_0005/0009/0012/0014.py`, `test_2fa_schema.py`.
- [x] **T5.2.** `pytest -q` in `workers/render/` — green. The worker imports shared entities from `app.core.db.models` via the editable `portal-api` dep; adding classes is additive, but prove it rather than assume it.
- [x] **T5.3.** `git diff --stat` — assert the changed-file set matches §7 **exactly**. Any extra file is scope creep and must be justified or reverted.
- [x] **T5.4.** `ruff format` + `ruff check --fix` in `apps/api/` — clean.

### T6 — Merge gate (AC-16)

- [x] **T6.1.** `infra/scripts/check-all.sh` → **16/16 stages passed**, no stage skipped. Record the log filename and the exact HEAD + dirty-state it ran against (standing epic:47 evidence-provenance action item). **DONE — controller-owned run, log `.hermes/run-logs/check-all-e49-1-controller.log`, exit 0, terminal line `all green.`** 16 `==>` stage headers, all 16 reported `✓`, zero stages skipped (the single `skipping` string in the log is part of a *vitest test name*, not a stage skip). Stage results: apps/api pytest **1762 passed / 3 skipped** (399.15s), apps/web vitest **136 files / 785 tests passed**, workers/render pytest **21 passed**, infra/scripts pytest **13 passed**, apps/web visual regression **536 passed / 32 expected skips** (2.6m), both `uv-lock-check` stages green (no lock drift). Provenance: ran against **HEAD `d6299faed0a2c02469c55bd2f83e7e7ed2691c97`** with an intentionally dirty tree of the 9 files in §15 File List (7 implementation + story + sprint-status); this dev session's own earlier in-session `check-all` attempt was killed by session teardown and is **not** cited as evidence.
- [x] **T6.2.** Determinism: 3× consecutive `pytest` (apps/api) and `vitest` (apps/web) runs with **identical** pass counts. Record the triple. **DONE — controller-owned run, log `.hermes/run-logs/determinism-e49-1-controller.log`, exit 0, `API_RC=0 WEB_RC=0`.** Verified by counting summary lines in the log: **exactly three** API summaries, each byte-identical `1762 passed, 3 skipped, 2014 warnings`; **exactly three** web summaries, each `Test Files 136 passed (136)` + `Tests 785 passed (785)`. NFR26-DETERMINISM-1 satisfied.
- [x] **T6.3.** Controller created one atomic story commit on `feat/E49.1-browse-category-entities` with subject `feat(api): add browse category entities and 0020 migration`; the final status/evidence closeout was folded into that same commit by amend. No split ORM/migration commit exists.
- [x] **T6.4.** **CONFIRMED against the real working tree** — `git status --porcelain` matches **zero** `apps/web/tests/visual/__snapshots__/**/*.png` and **zero** `apps/web/src/ui/*.tsx` (the whole change set is API-side; `apps/web/**` is untouched), so neither husky hook fires and no sign-off line was pre-filled. No `baseline-reviewed:` line is required — this commit stages **zero** `apps/web/tests/visual/__snapshots__/**/*.png` and adds **zero** `apps/web/src/ui/*.tsx`, so neither husky hook (`_check-baseline-review.mjs`, `_check-visual-coverage.mjs`) fires. Do not pre-fill a sign-off line.

## 6. Verify-at-create findings (traced at HEAD `47fe971`, not carried from the epic sketch)

The epic sketch and Decision AZ both carry a `VERIFY-AT-CREATE-STORY` marker: *"re-check the `test_migration_00xx` family for the head-pinning pattern Story 47.5's `d11` applied against the raising `0019.downgrade()`; confirm a single Alembic head."* That trace was run this session against every migration-touching test. Results:

| # | Finding | Evidence | Disposition |
|---|---|---|---|
| **F-1** | **`test_migration_0019.py:100-103` hard-codes the head id** — `assert script.get_heads() == ["0019_drop_category"]`. Adding `0020` breaks it. The epic sketch says "confirm a single Alembic head" but does **not** name this existing assertion. | `tests/test_migration_0019.py:100-103` | **In-story edit required** (T1.2, AC-10). Not a defect in `0020`; the test is doing its job. |
| **F-2** | **`test_migration_0019.py:91-97` would become a false negative.** It runs `command.upgrade(cfg, "head")` then `command.downgrade(cfg, "-1")` expecting `NotImplementedError`. With `0020` at head, `-1` exercises `0020.downgrade()`, which is **implemented** — the test would fail, and a naive "fix" (deleting it) would silently drop the proof that `0019` is forward-only. | `tests/test_migration_0019.py:91-97` | **In-story re-pin required** (T1.3, AC-11): upgrade to `0019_drop_category`, then `-1`. Intent preserved. |
| **F-3** | `test_migration_0019.py:70-88` (`upgrade head`, asserts `"category" not in objs`) is **safe**. The check is exact-name set membership; `browse_category` is a distinct name. | `tests/test_migration_0019.py:70-88` | No edit. Verified, not assumed. |
| **F-4** | The rest of the `test_migration_00xx` family is **already pinned to `0018_facet_tags`** by 47.5's `d11` and is unaffected by `0020`: `test_migration_0004.py:84-93,96-105`, `test_migration_0005.py:70-76,99-103`, `test_migration_0009.py:32-36`, `test_migration_0012.py:65,89,97`, `test_migration_0014.py:72,89,97`. | listed lines | No edit. **The `d11` pattern does not need re-application** — this is the concrete answer to the sketch's marker. |
| **F-5** | Forward-only `upgrade head` call sites are unaffected because they never traverse downward: `test_migration_0004.py:53,158`, `test_migration_0005.py:48,111,136`, `test_migration_0009.py:47`, `test_2fa_schema.py:265`, `test_orm_migration_parity.py:60`. | listed lines | No edit. |
| **F-6** | **`test_migration_0004.py:142-200` has a coverage gap, not a break.** The Alembic-vs-`init_schema` index-parity guard iterates a hard-coded `new_tables` list (`:166-174`) that will not include the new tables. It will stay green while proving nothing about them. | `tests/test_migration_0004.py:166-174` | **In-story extension** (T4.1, AC-14). Small, targeted, and squarely the drift class AC-3 guards. |
| **F-7** | **`test_migration_0004.py:51-81` is safe** — `missing = expected - names` is a subset check, so head gaining tables cannot break it. | `tests/test_migration_0004.py:80-81` | No edit. |
| **F-8** | **The atomicity claim is confirmed against the actual gate, not restated.** `test_orm_migration_parity.py:58-73` runs `command.upgrade(cfg, "head")` then `compare_metadata(ctx, SQLModel.metadata)` and asserts `diff == []`. An entities-only branch yields two `add_table` diffs; a migration-only branch yields two `remove_table` diffs. Neither half passes `check-all` alone. | `tests/test_orm_migration_parity.py:58-73` | Confirms the merge into one story. **This test must pass unmodified** — editing it would defeat the story. |
| **F-9** | **A real ORM trap the sketch's prose invites.** The epic sketch writes "`slug` unique+index". Taken literally as `Field(unique=True, index=True)` (the `Tag.slug` pattern at `_entities.py:51`) it emits an auto-named `ix_browse_category_slug` **plus** an unnamed UNIQUE constraint, alongside the explicit `uq_browse_category_slug` — guaranteed `compare_metadata` drift and exactly the failure `TagGroup` documents in-source at `_entities.py:31-36`. | `_entities.py:31-36` vs `:51` | **Bound by AC-3**: bare `slug: str` + explicit `Index(...)` only. Follow `TagGroup`, not `Tag`. |
| **F-10** | **The `server_default="0"` + `compare_metadata` interaction is already proven safe in this repo.** `tag_group.position` uses `sa.Integer(nullable=False, server_default="0")` in `0018:46` against an ORM `position: int = Field(default=0)` (`_entities.py:42`), and the parity test is green at HEAD. `browse_category.position` may use the identical idiom. | `0018_facet_tags.py:46`, `_entities.py:42` | Evidenced precedent, not a guess. |
| **F-11** | `Model` carries **no** `category_id` at HEAD — `0019` removed it and `_entities.py:63-88` confirms. There is nothing to remove and nothing to guard against re-adding beyond AC-8's grep. | `_entities.py:63-88`, `0019_drop_category.py:29-37` | Confirmed. |
| **F-12** | `uuid_fk(...)` (`_helpers.py:50-70`) already accepts `ondelete`, `nullable`, `index`, `primary_key` — it covers all three new FK columns with **zero** helper changes. `_helpers.py` stays untouched. | `_helpers.py:50-70` | No new helper. |
| **F-13** | **SQLite FK enforcement requires an explicit pragma in the self-contained test style.** `test_tag_group_entity.py:18-32` installs `PRAGMA foreign_keys=ON` on its in-memory engine; without it, CASCADE/RESTRICT assertions pass vacuously. `test_db_entity_tables.py:83-88` instead uses `create_engine_for_url` + `init_schema`, whose RESTRICT/CASCADE tests (`:373-406`) are green — so that path enables it too. | listed lines | AC-12 binds the new test to the `test_tag_group_entity.py` pattern. |
| **F-14** | **`check-all.sh` really is 16 stages** — 16 `run_stage` invocations at `infra/scripts/check-all.sh:54,57,60,63,66,77,80,83,86,89,95,98,104,110,112,119` (the helper definition at `:30` and the comment at `:70` are not stages). "16/16" is verified, not folklore. | `infra/scripts/check-all.sh` | AC-16 is well-formed. |
| **F-15** | **Stale cross-references in planning artifacts, reported not fixed — two instances of one drift class.** (a) `architecture.md:3351` (Decision AZ) still calls the starter seed "a separate admin-run seed story (**49.3**)"; the controller review renumbered it to **49.2**, which `epics.md:4473` and `sprint-status.yaml:380` both record correctly. (b) `architecture.md:3386` still records **`G26-CAT-SET 🔓 open, routed`** and `implementation-readiness-report-2026-07-26.md:204` still records it as `routed`, while `epics.md:4471` and `sprint-status.yaml:2,380` record it **closed** by commit `48db6bb`. §2 of this story states `closed`, matching the newer pair. | `architecture.md:3351,3386`; `implementation-readiness-report-2026-07-26.md:204` | **Not edited by this story.** Story creation does not own planning-artifact corrections; that is `bmad-correct-course` territory. Flagged for the controller. **Harmless to 49.1** — (a) concerns the seed story's number and (b) concerns a gate that governs **49.2**, not 49.1. Neither changes a 49.1 obligation, so neither blocks this story. |
| **F-16** | **Story-file naming convention confirmed against the repo, not the skill default.** The skill's `default_output_file` is `{implementation_artifacts}/{story_key}.md`; on-disk precedent agrees (`43-1-api-types.md`, `47-5-category-orm-dto-0019-atomic-cutover.md`). The `spec-*.md` family is the parallel quick-dev/spec artifact family, not the create-story output. | `_bmad-output/implementation-artifacts/` listing | Artifact written at the canonical path. |
| **F-17** | **No `project-context.md` exists at a repo-root glob**, but the file the `persistent_facts` entry targets **does** exist at `_bmad-output/project-context.md` (144 rules, last updated 2026-05-29) and was loaded as foundational context for this run. | `_bmad-output/project-context.md` | Loaded. Its Alembic rule ("adding a column = new migration in `apps/api/migrations/versions/`; `init_schema` is dev/test only") is directly binding here. |
| **F-18** | **Subagent usage was declined for this run.** The workflow invites parallel research subagents; this session's harness instruction forbids launching agents unless the user requests it. All artifact and code tracing was performed inline, in one context, against HEAD `47fe971`. Stated so the validate pass knows the provenance of every §6 claim. | — | Disclosed, not hidden. |

## 7. Predicted file changes (exact)

**Changed / created — 7 files, one commit:**

| File | Action | Why |
|---|---|---|
| `apps/api/app/core/db/models/_entities.py` | **MODIFY** | Add `BrowseCategory` + `ModelBrowseCategory`. Existing classes byte-unchanged. |
| `apps/api/app/core/db/models/__init__.py` | **MODIFY** | Re-export both names in the `._entities` import block and `__all__`. |
| `apps/api/migrations/versions/0020_browse_categories.py` | **NEW** | The migration half. |
| `apps/api/tests/test_browse_category_entity.py` | **NEW** | AC-12 constraint behaviour. |
| `apps/api/tests/test_migration_0020.py` | **NEW** | AC-13 structural round-trip + FK/index proof. |
| `apps/api/tests/test_migration_0019.py` | **MODIFY** | F-1 head id (AC-10) + F-2 re-pin (AC-11). Two tests, plus the docstring. |
| `apps/api/tests/test_migration_0004.py` | **MODIFY** | F-6: extend `new_tables` at `:166-174` (AC-14). One list literal. |

**Explicitly UNCHANGED (assert with `git diff --stat`; any hit is a defect):**

- `apps/api/app/core/db/models/_helpers.py`, `_enums.py`, `_audit.py`, `_auth.py`, `_user.py`, `_recovery.py`
- `apps/api/migrations/versions/0001…0019*.py` (all nineteen), `apps/api/migrations/env.py`, `apps/api/alembic.ini`
- `apps/api/app/core/db/session.py`, `seed.py`
- `apps/api/app/main.py` (`_PUBLIC_ROUTES` needs no edit — this story adds no route)
- `apps/api/app/modules/**` — the entire `sot`, `admin`, `share`, `auth`, `invite`, `slicer`, `spools`, `queue`, `runbook` tree
- `apps/api/tests/test_orm_migration_parity.py` — **must pass unmodified**; editing it defeats the story
- `apps/api/tests/test_db_entity_tables.py`, `test_tag_group_entity.py`, `test_db_models.py`, `test_migration_0005/0009/0012/0014.py`, `test_2fa_schema.py`, `test_sot_*.py`, `test_route_enforcement_gate.py`, `test_openapi_agent_surface.py`, `test_runbook_openapi_consistency.py`
- `apps/web/**` — every source file, `api-types.ts`, `locales/en.json`, `locales/pl.json`, every `tests/visual/**` spec and every `__snapshots__/**/*.png`
- `workers/render/**`
- `docs/**`, `infra/**`, `AGENTS.md`, `CLAUDE.md`, `README.md`
- `_bmad-output/planning-artifacts/**` (including the F-15 stale reference)

**Workflow tracking, outside the code commit:** `_bmad-output/implementation-artifacts/sprint-status.yaml` — this create pass sets `49-1-…` to `ready-for-validation`; `:validate` and the dev/closeout cycle own every later transition.

## 8. Dev Notes

### 8.1 Files being modified — current state, change, and what must be preserved

**`apps/api/app/core/db/models/_entities.py` (207 lines at HEAD).** Today it holds eight table classes: `TagGroup` (`:29-44`), `Tag` (`:47-60`), `Model` (`:63-88`), `ModelFile` (`:91-114`), `ModelTag` (`:117-127`), `ModelPrint` (`:130-144`), `ModelExternalLink` (`:147-181`), `ModelNote` (`:184-206`). Every UUID FK goes through `uuid_fk()`; every timestamp is `default_factory=_now_utc`. **Preserve:** `Model` has no `category_id` and must not gain one; `Tag.group_id` (`:54-57`) stays a single nullable `SET NULL` FK; `ModelTag` (`:117-127`) is the shape to copy and must itself stay byte-identical.

**`ModelTag` is the literal template** (`:117-127`):
```python
class ModelTag(SQLModel, table=True):
    __tablename__ = "model_tag"
    __table_args__ = (Index("ix_model_tag_tag_model", "tag_id", "model_id"),)

    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", primary_key=True),
    )
    tag_id: uuid.UUID = Field(
        sa_column=uuid_fk("tag.id", ondelete="RESTRICT", primary_key=True),
    )
    created_at: datetime.datetime = Field(default_factory=_now_utc)
```
`ModelBrowseCategory` is this with `tag_id → category_id`, `tag.id → browse_category.id`, and the index renamed. Nothing new is invented (Decision AX, "pre-enumeration save").

**`apps/api/app/core/db/models/__init__.py` (63 lines).** The `._entities` import block is `:18-27`, `__all__` is `:40-63`, both alphabetical. Note `:14` imports `app.modules.invite.models` purely for the `SQLModel.metadata` registration side-effect — the same dual-registration `env.py:8-9` performs. Class definition in `_entities.py` is what registers a table on the metadata; the `__init__` re-export exists for call-site ergonomics. Add both.

**`apps/api/migrations/versions/0019_drop_category.py` (43 lines) — read, not edited.** It is the parent revision. Its `downgrade()` raises `NotImplementedError` (`:40-43`), which is exactly why F-2 exists. Do not touch it.

**`apps/api/migrations/env.py` (45 lines) — read, not edited.** `target_metadata = SQLModel.metadata` (`:17`); `config.set_main_option("sqlalchemy.url", get_settings().database_url)` at `:12` **overrides** whatever URL a test sets on the `Config` object — which is why every migration test overrides the `DATABASE_URL` env var and clears the `get_settings` / `get_engine` LRU caches instead.

**`apps/api/tests/test_orm_migration_parity.py` (74 lines) — read, not edited.** The gate. `command.upgrade(cfg, "head")` at `:60`, `compare_metadata` at `:66`, `assert diff == []` at `:73`.

### 8.2 Migration idiom, sourced from `0018`

`0018_facet_tags.py:40-52` is the shape to follow: `sa.Uuid(as_uuid=True)` PK, `sa.String()` text columns, `sa.Integer(nullable=False, server_default="0")` for a positional int, `sa.DateTime(), nullable=False` with **no** server_default for timestamps (the ORM supplies them via `default_factory=_now_utc`), then a separately named `op.create_index(...)`. `0004:142-158` is the shape for a composite-PK join table plus its reverse index. **`batch_alter_table` is not needed anywhere in `0020`** — it exists in `0018`/`0019` only because SQLite requires a table copy to alter an *existing* table; `0020` alters nothing.

### 8.3 Why the ORM and migration cannot be split (say it once, plainly)

`test_orm_migration_parity.py` upgrades a scratch DB to head and diffs it against `SQLModel.metadata`. Entities without the migration → metadata has two tables the DB lacks → non-empty diff → red. Migration without the entities → DB has two tables metadata lacks → non-empty diff → red. `check-all.sh` runs `apps/api pytest` as one of its 16 stages, so neither half can pass the merge gate alone, so neither half is independently mergeable, so they are one story and one commit. This is the same coupling E41 retro action item #2 recorded and Story 47.5 obeyed — applied here at decomposition time rather than discovered at spec-authoring, which is what the standing epic:47 stale-precondition action item asks for.

### 8.4 Project rules that bind this story specifically

- **Alembic owns production schema.** `deploy.sh` runs `alembic upgrade head` before the container starts; `init_schema(engine)` fires only when `environment != "production"`. A new table = a new migration, always. [Source: `_bmad-output/project-context.md` § FastAPI, § Catalog data integrity]
- **ruff is the only formatter/linter** for `apps/api`: `select = ["E","F","W","I","B","UP","SIM","RUF"]`, line-length 100, py312. Run `ruff check --fix` and `ruff format` before commit.
- **Worker shares these entities** via the editable `portal-api` dep and must never redefine them (`workers/render/` imports from `app.core.db.models`). Additive classes are safe, but T5.2 proves it.
- **English in all committed content** — code, comments, docstrings, commit message.
- **Trunk-only `main`, ff-only merges, no squash across commits, conventional commit with a scope.** Branch `feat/E49.1-browse-category-entities` (or equivalent `feat/` name) off `main`.
- **Doc-only commits skip deploy; this one does not** — it is application code. Deploy timing is the controller's call at closeout, under the standing (non-destructive) pre-deploy backup policy.

### 8.5 Previous-story intelligence

There is **no** prior story file in Epic 49 — 49.1 is the first. The load-bearing predecessors are in Initiative 25:

- **Story 41.1** (`41-1-taggroup-entity-tag-membership-category-removal.md`) — the additive-ORM-entity precedent, and the origin of the explicit-index-naming rule now embedded as a source comment at `_entities.py:31-36`.
- **Story 41.2** (`41-2-alembic-0018-facet-tags-drop-category.md`) — the additive+reversible migration precedent whose idioms `0020` copies, and whose docstring records why destructive DDL was deferred rather than bundled.
- **Story 41.3** (`41-3-optional-starter-taxonomy-seed.md`) — the "seed content lives outside the migration" precedent that keeps `upgrade()` structural (AC-6), and that Story 49.2 inherits.
- **Story 47.5** (`47-5-category-orm-dto-0019-atomic-cutover.md`) — the single-commit atomic ORM+migration shape, the origin of `test_orm_migration_parity.py`, and the `d11` head-pinning adjustment whose *re-check* is this story's `VERIFY-AT-CREATE-STORY` marker (answered in §6, F-1…F-5). Its review history is also the cautionary tale: create's file:line map was confirmed correct, yet the validate pass still had to amend the file set (eleven additional frontend vitest fixtures, an extra API test file, and a rewritten head-pinning task) — which is why §7 lists unchanged files as assertions to check, not as prose.

### 8.6 Git intelligence (last 5 commits)

`47fe971` docs(init26): reconcile sprint planning · `48db6bb` docs(init26): add targeted UX and taxonomy · `9c8a9a0` docs: plan Initiative 26 catalog discovery · `da87e71` fix(web): contain mobile fullscreen image viewer · `a7910bc` fix(web): align upload limit with edge proxy.

Three of the five are Initiative 26 **planning-only** commits — no application code has been written for this initiative yet. `da87e71` is Story 48.1 (frontend only, does not touch the API). **Consequence:** this story is the first Initiative 26 code commit, and there is no in-flight backend work to coordinate with or rebase around. `main` at `47fe971` is the clean base.

### 8.7 Library / version notes

No new dependency is added or bumped. The story uses only what is already declared in `apps/api/pyproject.toml`: `sqlmodel>=0.0.22` (`:14`) — a **floor**, not a pin; the **resolved** runtime version is **SQLModel 0.0.38 with pydantic 2.13.3** — `alembic>=1.14` (`:15`), SQLAlchemy's `sa.Uuid(as_uuid=True)`, and `requires-python = ">=3.12"` (`:4`, matching ruff `target-version = "py312"`). Verified on the resolved version, because AC-1 and AC-12 depend on it: a `uuid.UUID | None` / `str | None` field declared **without** an explicit `default=` — including the `Field(sa_column=uuid_fk(...))` form AC-1 uses for `parent_id` — still resolves to `None` rather than becoming a required argument. AC-1's nullable field list and AC-12 (a)/(f) are therefore consistent as literally written. Following the repo's own `Field(default=None, sa_column=...)` house style (`Tag.group_id`, `_entities.py:54-57`) is still preferred for readability. `uv.lock` for both `apps/api` and `workers/render` must remain unchanged — `check-all.sh` runs `uv-lock-check` for both (`:110`, `:112`), and a lock drift there is a real failure, not noise. **No web research was performed or needed**: nothing here depends on an external API surface, a new library version, or a recent breaking change.

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `compare_metadata` drift from an auto-named index (F-9) | **Medium** — the sketch's own prose invites it | Red merge gate | AC-3 binds `slug` to the bare-field + explicit-`Index` pattern; AC-14 adds the two tables to the index-parity guard so drift is caught by name, not by symptom. |
| The `test_migration_0019` head assertions are "fixed" by deletion rather than re-pinning | Low | Silent loss of the `0019` forward-only proof | F-2 states the intent explicitly; AC-11 requires the proof to survive, and T1.3 requires the rename to carry the new pin in its name. |
| The commit is split into two (entities, then migration) "for reviewability" | Low | Neither half merges; wasted cycle | §8.3 + AC-9; T2.4 deliberately produces and records the red parity failure so the coupling is observed, not merely asserted. |
| SQLite `PRAGMA foreign_keys` off → CASCADE/RESTRICT assertions pass vacuously | Medium | False green on AC-12 | F-13 + AC-12 bind the new test to `test_tag_group_entity.py:18-32`'s explicit pragma listener. |
| A self-referential FK on SQLite behaves unexpectedly at `create_table` | Low | Migration fails | Precedent on **both** halves: `0004:21-28` already creates the self-FK `category` table (migration side), and the `class Category` deleted by 47.5 carried the same `uuid_fk` self-FK on the ORM side with a green parity gate (T2.2). AC-13 still proves `browse_category.parent_id → browse_category.id ON DELETE RESTRICT` via `PRAGMA foreign_key_list` rather than by inspection. |
| Scope creep into Decision AY (a router, a schema, a `model_count` helper) | Medium | Story stops being reviewable; forward dependency on unowned decisions | §10 non-goals; T5.3's `git diff --stat` assertion against §7. |
| `0020` is later "fixed" into a raising `downgrade()` for consistency with `0018`/`0019` | Low | Loses a genuinely safe rollback | AC-7 requires the rationale **in the migration's own docstring**, where the future reader will be. |

## 10. Non-goals (this story ships none of these)

- **No seed content.** Zero rows inserted by the migration or by anything else. The eight governed starter categories fixed by the UX/taxonomy SoT belong to **Story 49.2**, which still owes its documented real multi-model distribution check against the live catalogue before seeding.
- **No API surface** — no `GET /api/categories`, no `GET /api/categories/{slug}`, no `?category=<slug>`, no `ModelDetail.categories`, no router, no Pydantic schema, no service function, no `model_count` helper. All Decision AY, **Story 49.3**.
- **No admin governance** — no CRUD, no replace-set assignment, no audit `entity_type`, and **no depth-2 or self-cycle enforcement**. Story 49.1 ships the `parent_id` *column*; the *rule* is service-layer and belongs to **Story 49.5**.
- **No tag-aware search** (Story 49.4). `sot/service.py` is untouched.
- **No frontend** — no types, hooks, URL state, routes, components, i18n keys, or visual baselines. E50–E53.
- **No model assignments.** `model_browse_category` ships empty.
- **No destructive DDL, no endpoint retirement, no reverting `0019`.**
- **No live-DB action, no deploy, no commit/push/merge** by the create or validate passes.
- **No documentation edits.** `docs/operations.md` and `cutover-smoke.sh` only go stale when the **read API** deploys — that correction is explicitly owned by Story 49.3 (readiness finding M-1), not by this story.

## 11. Branch and commit atomicity

- **Branch:** one story branch off `main` at `47fe971` (e.g. `feat/E49.1-browse-category-entities`). The current branch `docs/init26-e49-1-create-validate` is a **planning** branch and carries only this artifact plus the `sprint-status.yaml` transition; implementation does **not** happen on it.
- **Commit:** exactly **one** implementation commit containing all seven files in §7. The ORM half and the migration half are inseparable (§8.3).
- **Gate:** that single commit must pass `check-all.sh` 16/16 on its own — the repo's binding mergeability rule.
- **Merge:** ff-only into `main`, no squash-across-commits, per AGENTS.md / project-context git rules.
- **Revert shape:** a whole-commit `git revert` cleanly removes both halves and leaves the parity gate green — which is only true because they are one commit.

## 12. Traceability

| Item | Source |
|---|---|
| Story identity, atomicity rationale, branch shape | `epics.md:4463-4471` (Story 49.1); `sprint-status.yaml:379` |
| Epic goal, additive-only boundary | `epics.md:4455-4461` |
| Entity field list, RESTRICT/CASCADE rationale, identifier-naming rationale, depth-2-in-service | `architecture.md:3285-3301` (Decision AX) |
| Migration posture, `downgrade()` implemented, table-name collision safety, deploy posture, the `VERIFY-AT-CREATE-STORY` marker | `architecture.md:3347-3361` (Decision AZ) |
| `ModelTag`-is-the-pattern, parity-gate-already-exists | `architecture.md:3273-3283` (pre-enumeration save) |
| FR26-CAT-1 / -2 / -4 verifiables | `prd.md:2244,2245,2247` |
| NFR26-SCHEMA-ADDITIVE-1, NFR26-DETERMINISM-1 | `prd.md:2269,2268` |
| Renumber history (49.1 = former 49.1+49.2 merged) | `epics.md:4461`; `sprint-status.yaml:2,378-383` |
| Readiness verdict CONDITIONALLY READY; R-1 (ORM+migration merged); C-2 accepted deviation | `implementation-readiness-report-2026-07-26.md:87,114,179,187` |
| G26-MIGRATE is not a destructive gate | `implementation-readiness-report-2026-07-26.md:204`; `architecture.md:3361,3386` |
| Mergeability rule (16/16 per branch) | `epics.md:4385`; `sprint-status.yaml:364-368` |
| Source SCP | `sprint-change-proposal-2026-07-26-init26-catalog-discovery.md` (§ 2.1 retired-vs-new boundary, § 6 decisions, § 9 decomposition) |
| Category set / governance (context for 49.2, not binding here) | `ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md` |
| Code anchors | `_entities.py:29-44,47-60,63-88,117-127`; `_helpers.py:50-70`; `models/__init__.py:14,18-27,40-63`; `0004_entity_tables.py:142-158`; `0018_facet_tags.py:36-81`; `0019_drop_category.py:23-43`; `migrations/env.py:8-17`; `test_orm_migration_parity.py:58-73`; `test_migration_0018.py:33-68,92-156`; `test_migration_0019.py:70-103`; `test_migration_0004.py:51-81,142-200`; `test_tag_group_entity.py:18-32`; `test_db_entity_tables.py:83-88,340-406`; `infra/scripts/check-all.sh:54-119` |

## 13. Project structure notes

The story lands entirely inside the established `apps/api` layout: DB entities in `app/core/db/models/`, Alembic revisions in `migrations/versions/`, tests in `tests/test_<area>.py`. No new directory, no new module, no new package. **Detected variance:** none. The only convention judgement made is the new test filenames — `test_browse_category_entity.py` mirrors `test_tag_group_entity.py` (the 41.1 entity-test precedent) and `test_migration_0020.py` mirrors `test_migration_0018.py`; both follow the existing naming exactly.

## 14. Testing standards summary

- pytest with `asyncio_mode = "auto"`; session-scoped `_isolated_db` and autouse `_patch_arq_pool` fixtures in `tests/conftest.py`. **Migration tests deliberately bypass `_isolated_db`** by overriding `DATABASE_URL` and clearing the `get_settings` / `get_engine` LRU caches — copy that fixture verbatim from `test_migration_0018.py:71-89`.
- TDD is mandatory for backend logic: red → green → refactor, with the failure output recorded.
- No real network, no real Redis, no live DB anywhere in this story.
- Frontend: `vitest` and `test:visual` are run as part of `check-all.sh` 16/16 but **must not require any change** — this story adds no UI. A visual-baseline delta here would be an environmental drift signal to investigate, never something to blanket-update as part of this commit.

## 15. Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`) agent session, 2026-07-26. Native `bmad-dev-story` (DS), routed via native `bmad-help` → `_bmad/_config/bmad-help.csv` row `bmad-dev-story` (menu **DS**, `preceded-by: bmad-create-story:validate`). Skill customization resolved via `resolve_customization.py --skill .claude/skills/bmad-dev-story --key workflow`: no team/user override (`activation_steps_prepend` / `activation_steps_append` both empty, `on_complete` empty); `persistent_facts` = `file:{project-root}/**/project-context.md`, satisfied by `_bmad-output/project-context.md` and loaded as foundational context.

Branch `feat/E49.1-browse-category-entities`, `baseline_commit` **`d6299faed0a2c02469c55bd2f83e7e7ed2691c97`** (clean tree at start). Note the baseline is `d6299fa`, not the `47fe971` named throughout §1–§17 — `d6299fa` is the later docs commit that recorded this story's own validate pass; no application file changed between the two, so every §6/§12 code anchor was re-confirmed exact at `d6299fa` before use.

**Authorization — truthful.** **G26-DEVGO was granted for this specific story by Laura/controller on 2026-07-26 under Ezop's standing Initiative 26 authorization.** That is a **controller confirmation**, recorded as such. It is **NOT** an Ezop signature, **NOT** an Ezop review, and **NOT** a human review of this story document or of the resulting diff — no human has read either. No reviewer sign-off of any kind is recorded, implied, or inheritable from this record.

**Subagents: none used** (harness restriction — agents are not launched unless the user asks). All tracing and implementation was inline in one context.

### Debug Log References

Strict TDD, observable RED before GREEN on every slice. Failures are quoted as actually produced, not paraphrased.

**T1.1 — baseline (evidence-first).** `pytest tests/test_migration_0019.py -q` at `d6299fa`, pre-change → **`3 passed`**. Establishes that the T1.4 red is caused by this story and is not a pre-existing failure.

**T1.4 — RED (AC-10), exactly as §6 F-1 predicted:**

```
FAILED tests/test_migration_0019.py::test_single_head_is_0020_browse_categories
E   AssertionError: assert ['0019_drop_category'] == ['0020_browse_categories']
E     At index 0 diff: '0019_drop_category' != '0020_browse_categories'
1 failed, 2 passed in 1.39s
```

`test_upgrade_head_drops_category_schema` stayed green unedited (F-3 confirmed — exact-name set membership, and `browse_category` is a distinct name). The re-pinned `test_downgrade_from_0019_raises_not_implemented` was already green at this point, so the F-2 false-negative was prevented rather than observed as a failure.

**T2.1 — RED (ORM entities absent):**

```
ImportError while importing test module '.../tests/test_browse_category_entity.py'
E   ImportError: cannot import name 'BrowseCategory' from 'app.core.db.models'
1 error in 0.22s
```

**T2.4 — GREEN then the required atomicity RED.** `pytest tests/test_browse_category_entity.py -q` → **`14 passed`**. Then `pytest tests/test_orm_migration_parity.py -q` → **FAILED**, which is the mechanical proof of AC-9 coupling:

```
E   AssertionError: ORM metadata and migrated schema differ:
E     [('add_table', Table('browse_category', ...)),
E      ('add_index', Index('uq_browse_category_slug', ..., unique=True)),
E      ('add_table', Table('model_browse_category', ...)),
E      ('add_index', Index('ix_model_browse_category_cat_model', ...))]
E   Left contains 4 more items
1 failed in 0.87s
```

Alembic's own log lines: `Detected added table 'browse_category'` / `Detected added index 'uq_browse_category_slug' on '('slug',)'` / `Detected added table 'model_browse_category'` / `Detected added index 'ix_model_browse_category_cat_model' on '('category_id', 'model_id')'`. §6 F-8 predicted "two `add_table` diffs"; the actual diff is those two **plus** the two matching `add_index` entries — a superset, consistent with the prediction and with AC-3's explicit index names appearing under exactly the intended names. The entities half was deliberately **not** committed at this point.

**T3.1 — RED (migration absent):**

```
E   alembic.util.exc.CommandError: Can't locate revision identified by '0020_browse_categories'
1 failed in 0.51s
```

**T3.5 — GREEN, all three, closing the atomicity loop:** `tests/test_migration_0020.py` → **`1 passed`**; `tests/test_migration_0019.py` → **`3 passed`** (T1's re-pins now hold); `tests/test_orm_migration_parity.py` → **`1 passed`** — `compare_metadata` diff is **empty**, satisfying AC-9.

**T4 — GREEN.** `tests/test_migration_0004.py` → **`4 passed`**, covering both the extended index-parity guard (AC-14, new tables now actually proven, not merely listed) and `test_alembic_upgrade_head_creates_all_new_tables` **unedited** (T4.2 / F-7 confirmed — `expected - names` is a subset check).

**Pre-existing warning, not introduced here.** `test_orm_migration_parity.py` emits `SAWarning: Cannot correctly sort tables; there are unresolvable cycles between tables "model, model_file"`. Verified pre-existing by stashing the change set and re-running at baseline (same single warning). It concerns `model` ↔ `model_file`, both untouched by this story.

### Completion Notes List

- **All 16 ACs satisfied.** AC-1/AC-3: `BrowseCategory` declares a bare `slug: str` with uniqueness and indexing coming **only** from the single explicit `Index("uq_browse_category_slug", "slug", unique=True)` in `__table_args__` — the `TagGroup` pattern (`_entities.py:31-36`), deliberately **not** the auto-naming `Tag.slug` pattern that F-9 identified as a guaranteed drift trap. AC-2: `ModelBrowseCategory` is the `ModelTag` shape verbatim (composite PK, both FK columns via the shared `uuid_fk(...)` helper, reverse-direction index). AC-4: both names re-exported from `._entities` and added to `__all__` in alphabetical position.
- **Migration is additive and genuinely reversible.** `0020_browse_categories`, `down_revision = "0019_drop_category"`, `branch_labels = None`, `depends_on = None`. `upgrade()` creates two tables + two named indexes and inserts **zero rows**; it touches **no** existing table and uses **no** `batch_alter_table` (nothing pre-existing is altered). `downgrade()` is implemented and drops child-before-parent. The module docstring records **why** this departs from `0018`/`0019` — `0019` is forward-only because it destroys pre-existing production data, whereas `0020` only drops two tables it created itself — so a future reader does not "fix" it into a `raise` for false consistency (AC-7).
- **AC-8 verified by grep, not assumption.** No `category` table, no `model.category_id`, no `ix_model_category_id`, and no `Category*` Python identifier (other than `BrowseCategory` / `ModelBrowseCategory` / `browse_category`) appears in any new file. `0019_drop_category` was not reverted, edited, or re-ordered. The Initiative 25 retirement stands.
- **AC-12 proven executably, and non-vacuously.** 14 entity tests against a fresh ORM-built SQLite with an explicit `PRAGMA foreign_keys=ON` listener (F-13 — without it the CASCADE/RESTRICT assertions would pass vacuously): defaults round-trip (`position == 0`, all optionals `None`), duplicate `slug` → `IntegrityError`, duplicate `(model_id, category_id)` → `IntegrityError`, `Model` delete CASCADEs its assignment rows while the category survives, deleting an assigned category is RESTRICTed, self-FK parent/child resolution with RESTRICT on a parent holding a child, and a `Model` with **zero** categories persists and is unaffected. Slug uniqueness is asserted **global** (a child cannot reuse a root's slug) — the retired `uq_category_root_slug` per-parent shape is deliberately not reproduced.
- **AC-13 proven at the migration level** via `PRAGMA table_info` / `foreign_key_list`: exact 11-column set on `browse_category`, `position` NOT NULL with server_default `0`, `parent_id` nullable, timestamps NOT NULL with **no** server_default, composite PK on both join columns, and all three FK `ON DELETE` actions (`model_id`→CASCADE, `category_id`→RESTRICT, `parent_id`→RESTRICT). Downgrade removes exactly the four new objects while `model`/`tag`/`tag_group`/`model_tag` survive; re-upgrade restores everything identically. Every traversal is pinned to an explicit revision id — never `"head"` — so a future `0021` cannot silently change what the test exercises.
- **AC-15 non-regression held with zero edits outside §7.** `test_orm_migration_parity.py` is **byte-unmodified** and passes (editing it would have defeated the story). No `_helpers.py` change was needed (F-12). Full apps/api suite **1762 passed / 3 skipped** = the 1747-pass baseline **+ 15 new tests** (14 entity + 1 migration), so no pre-existing test was disturbed. `workers/render` **21 passed** — the shared-entity import surface tolerated the additive classes, proven rather than assumed (T5.2).
- **ruff clean:** `ruff format .` → `273 files left unchanged`; `ruff check --fix .` → `All checks passed!`.
- **Scope held exactly.** `git status` is the §7 seven-file set plus the two workflow-tracking artifacts, and nothing else. No seed content, no API/router/service/schema behaviour, no UI, no model assignments, no live-DB action, no destructive DDL, no dependency or `uv.lock` change (both `uv-lock-check` stages green), no planning-artifact edit. §6 **F-15's two stale planning cross-references remain reported-not-fixed** — still `bmad-correct-course` territory, still harmless to 49.1.
- **Merge gate green on controller-owned evidence.** `check-all.sh` **16/16, no stage skipped**, log `.hermes/run-logs/check-all-e49-1-controller.log` (exit 0, terminal `all green.`); determinism triples identical, log `.hermes/run-logs/determinism-e49-1-controller.log` (exit 0, `API_RC=0 WEB_RC=0`). This dev session's own earlier in-session `check-all` attempt was killed by session teardown and is **not** cited.
- **Not done, and not claimed: no commit, squash, push, merge, deploy, live-DB or production access, no native code review, and no Aider review.** T6.3 is left **unchecked** on purpose — it is controller-owned and there is nothing to check off, because no commit exists. The seven implementation files are uncommitted in the working tree awaiting controller review under `AGENTS.md` one-commit / ff-only rules.

### File List

**Implementation — exactly the §7 seven-file set, reconciled against real `git status --porcelain`:**

| File | Action |
|---|---|
| `apps/api/app/core/db/models/_entities.py` | MODIFY — added `BrowseCategory` + `ModelBrowseCategory` after `ModelTag`; existing classes unchanged |
| `apps/api/app/core/db/models/__init__.py` | MODIFY — re-export both names in the `._entities` block and `__all__` |
| `apps/api/migrations/versions/0020_browse_categories.py` | **NEW** — additive, reversible migration |
| `apps/api/tests/test_browse_category_entity.py` | **NEW** — AC-12 constraint behaviour (14 tests) |
| `apps/api/tests/test_migration_0020.py` | **NEW** — AC-13 structural round-trip + FK/index proof |
| `apps/api/tests/test_migration_0019.py` | MODIFY — F-1 head id (AC-10) + F-2 re-pin (AC-11) + docstring |
| `apps/api/tests/test_migration_0004.py` | MODIFY — F-6 `new_tables` extension (AC-14) |

**Workflow tracking, outside the implementation set (§7 permits both):** `_bmad-output/implementation-artifacts/49-1-browse-category-entities-and-0020-migration.md` (frontmatter `baseline_commit`, task checkboxes, this Dev Agent Record, Status) and `_bmad-output/implementation-artifacts/sprint-status.yaml` (Story 49.1 → `review`, `epic-49` → `in-progress`).

**Explicitly unchanged, as §7 requires:** `test_orm_migration_parity.py`, `_helpers.py`, `env.py`, `alembic.ini`, `0001…0019*.py`, `app/modules/**`, `app/main.py`, `apps/web/**` (including every `tests/visual/**` spec and every `__snapshots__/**/*.png`), `workers/render/**`, `docs/**`, `infra/**`, both `uv.lock` files, and `_bmad-output/planning-artifacts/**`.

## 16. Validation Record

**Create pass (this document).** Native `bmad-create-story` action=`create`, 2026-07-26, Claude Opus 5 agent session, baseline HEAD `47fe971`, branch `docs/init26-e49-1-create-validate`, working tree clean. Routed via `bmad-help` → `_bmad/_config/bmad-help.csv` row `bmad-create-story` (CS / `create`). Skill customization resolved via `resolve_customization.py --key workflow`: no team or user override present (`_bmad/custom/` contains only `config.toml` / `config.user.toml`), so the base workflow ran unmodified except where §6 F-18 and §17 disclose otherwise. Every file:line claim in §6 and §12 was traced this session against HEAD `47fe971` — none is carried from the epic sketch. **No code, no migration, no test, and no live DB was touched. No commit, push, merge, or deploy was performed. No Ezop and no Laura review or sign-off is recorded or implied; no human has read this document.**

**Validate pass — PASS.** Native `bmad-create-story` action=`validate` (bmad-help → `_bmad/_config/bmad-help.csv` row `bmad-create-story`, menu **VS**, action `validate`, `preceded-by: bmad-create-story:create`, `followed-by: bmad-dev-story`), 2026-07-26, Claude Opus 5 agent session, **fresh independent context**. Baseline HEAD `47fe971`, branch `docs/init26-e49-1-create-validate`. Skill customization re-resolved (`resolve_customization.py --skill .claude/skills/bmad-create-story --key workflow`): no team/user override; `persistent_facts` = `file:{project-root}/**/project-context.md`, satisfied by `_bmad-output/project-context.md`. Checklist executed: `.claude/skills/bmad-create-story/checklist.md`.

**Method — independent re-trace, not a re-read of §6.** Every binding AC and every predicted file was re-derived from the code at HEAD `47fe971` and from the current working-tree diff. Two claims were additionally **executed**, not inspected.

**Executable verification (read-only, tmpdir scratch DBs only):**

- `pytest tests/test_migration_0019.py tests/test_orm_migration_parity.py -q` → **4 passed** at HEAD. Confirms the T1.1 baseline and confirms F-8's parity gate is green *before* the story, so the T2.4 red is a real signal and not a pre-existing failure.
- SQLModel/pydantic behaviour probe on the **resolved** runtime (0.0.38 / 2.13.3): an optional field declared with `Field(sa_column=uuid_fk(...))` and no explicit `default=` resolves to `None`, not to a required argument. This retires a suspected AC-1 ↔ AC-12(a)/(f) contradiction — **the suspicion was disproved**, AC-1 is implementable exactly as written. Recorded in §8.7.

**Confirmed by independent trace (spot-list, all exact at HEAD `47fe971`):** `_entities.py:29-44` (`TagGroup` explicit-index comment), `:47-60` (`Tag.slug = Field(unique=True, index=True)` — the anti-pattern AC-3 forbids), `:63-88` (`Model`, **no** `category_id`), `:117-127` (`ModelTag`, quoted byte-accurately in §8.1) · `_helpers.py:50-70` (`uuid_fk` already accepts `ondelete`/`nullable`/`index`/`primary_key`) · `models/__init__.py:14,18-27,40-63` · `env.py:12,17` (the `set_main_option` override that forces the `DATABASE_URL` fixture idiom) · `0004:21-28` (self-FK precedent), `:142-158` (composite-PK join idiom) · `0018:40-52` (column idiom), `:46` (`server_default="0"`) · `0019:23,29-43` (`revision`, raising `downgrade()`) · `test_orm_migration_parity.py:58-73` · `test_migration_0019.py:70-88,91-97,100-103` · `test_migration_0004.py:80-81,166-174` · `test_migration_0018.py` (`_alembic_cfg`/`_objects`/`_columns`/`_foreign_keys` + `_round_trip_db`; `_foreign_keys` returns `on_delete`, which is what AC-13 needs) · `test_tag_group_entity.py:18-32` (FK pragma listener) · `session.py:12-26` (`create_engine_for_url` enables `PRAGMA foreign_keys = ON`, confirming F-13's secondary claim) · `pyproject.toml:44-49` (ruff config, verbatim as §8.4 states) · `check-all.sh` = **16** `run_stage` invocations (17 grep hits minus the `run_stage()` definition at `:30`), `uv-lock-check` at `:110`/`:112`. Planning anchors re-opened and confirmed exact: `epics.md:4385,4463,4473`; `architecture.md:3273-3283,3285-3301,3347-3361,3351,3386`; `prd.md:2244,2245,2247,2268,2269`; `implementation-readiness-report-2026-07-26.md:87,114,179,187,204`; `sprint-status.yaml:2,364-368,378-383`.

**Two checks the create pass did not run, added here — both clean:**

1. **Repo-wide head-coupling sweep.** `grep -rn '0019_drop_category\|get_heads'` over `apps/`, `workers/`, `infra/`, `docs/`, `.githooks/`. `test_migration_0019.py:103` is the **only** assertion that hard-codes the head id; every other `test_migration_00xx` is pinned to `0018_facet_tags` by 47.5's `d11`, and **no** deploy script, hook, doc or runbook pins a revision id. §7's changed-file set is therefore complete on the head-coupling axis — F-1/F-2/F-4/F-5 hold under an independent sweep, not just the create pass's enumeration.
2. **Additive-surface break sweep.** No test in `apps/api/tests/` asserts set-equality on `models.__all__` or on the DB table-name set (`test_migration_0004.py:81` is `expected - names`, a subset check). Adding two ORM classes, two re-exports and two tables cannot break an unlisted test by widening a set. AC-15's "passes unmodified" claim survives.

**Amendments applied by this pass (three, all minor, story file only):**

- **§8.7 — factual correction.** The create pass wrote "SQLModel 0.0.22" as the version in use. `pyproject.toml:14` declares `sqlmodel>=0.0.22` — a floor, not a pin — and the resolved runtime is **0.0.38 / pydantic 2.13.3**. Rewritten to state floor-vs-resolved correctly, and to record the probe result above so a dev agent does not re-litigate AC-1's nullable-field defaults.
- **T2.2 + §9 risk row — precedent strengthened.** Both cited only the *migration*-side self-FK precedent (`0004`). The directly applicable **ORM**-side precedent is the `class Category` deleted by 47.5, which used exactly `Field(default=None, sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=True))` and was `compare_metadata`-green for its whole life; it is recoverable at `git show 98246d7^:apps/api/app/core/db/models/_entities.py`. Named, with an explicit warning not to also copy its `Category*` identifiers or its `uq_category_root_slug` partial index (`browse_category.slug` is globally unique per AC-1, not unique-per-parent).
- **F-16 → F-15 — drift scope corrected.** F-15 named one stale planning reference. There are **two** instances of the same class: `architecture.md:3351` (seed story still "49.3") **and** `architecture.md:3386` + `implementation-readiness-report-2026-07-26.md:204` (both still record `G26-CAT-SET` as open/routed, while `epics.md:4471` and `sprint-status.yaml:2,380` record it closed by `48db6bb`). §2's "closed" is substantively correct — it matches the newer pair. Classified truthfully as **planning-artifact drift, reported not fixed**: instance (a) concerns the seed story's number and (b) concerns a gate that governs **49.2**. Neither changes a 49.1 obligation, so neither blocks this story. **Per the operator instruction, no planning artifact was edited** — correcting them is `bmad-correct-course` territory, and it is flagged for the controller.

**Findings: 0 critical, 0 important, 3 minor (all amended above).** No AC was rewritten, no AC was relaxed, no task was deleted, and the §7 changed-file set is unchanged at **7 files** — the validate pass found nothing to add to or remove from it. Notably it did **not** repeat 47.5's history, where validate had to expand create's file set.

**Scope and safety re-confirmed by this pass.** No seed content, no API/router/service/schema, no UI, no model assignments, no live-DB action, no destructive DDL anywhere in the ACs or tasks. Working-tree diff at the start of this pass was exactly two lines in `sprint-status.yaml` (`last_updated` comment + the `49-1-…` status) and no application file. **This pass touched no code, no migration, no test, and no database. No commit, push, merge or deploy was performed.**

**Provenance — truthful.** Both the create pass and this validate pass were run by a Claude Opus 5 agent session. **No human has reviewed this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable from this record.** No research subagents were used in either pass (harness restriction; disclosed at §6 F-18 and §17.3 for create, and true again here) — every claim above was traced inline in this context against HEAD `47fe971`.

**Disposition: PASS → story status `ready-for-dev`.** `epic-49` is deliberately left at `backlog` per §17.2 — the validate pass reviewed that disclosed deviation and **upholds** it: this project's 43.1/47.5 precedent flips the epic at `bmad-dev-story`, and under an open **G26-DEVGO** promoting the epic before any code exists would misreport state. §17.1 (two-step `ready-for-validation` → `ready-for-dev`) is likewise upheld and is now discharged by this record.

**Next canonical action:** `bmad-dev-story` (**DS**), in a fresh context, on a new `feat/` branch off `main` at `47fe971` — **only after** the controller confirms this specific ready story under G26-DEVGO.

## 17. Disclosed deviations from the base workflow

1. **The create pass set the story to `ready-for-validation`, not directly to `ready-for-dev`; the validate pass has now advanced it to `ready-for-dev`.** The base skill template hard-codes `ready-for-dev` during create and its step 6 writes that value into `sprint-status.yaml`. **This project's own repeated precedent is the two-step form** — create → `ready-for-validation`, then `:validate` (VS) → `ready-for-dev` — recorded in `sprint-status.yaml:2` for Stories 43.1, 43.2, 43.3 and 47.5, and matching the `bmad-help.csv` sequencing (`bmad-create-story:create` → `followed-by: bmad-create-story:validate`). The operator instruction for this run states the same. The project convention governed the create pass, and the divergence from the vanilla template text remains recorded here rather than silently applied; it is now discharged by the PASS record in §16.
2. **`epic-49` is left at `backlog`, not flipped to `in-progress`.** The base workflow step 1 auto-promotes an epic when its first story is created. This project's precedent is explicitly the opposite — `sprint-status.yaml:2` records "epic-43 stays backlog until dev-go" at 43.1's create pass, and "epic-47 stays backlog (not done)" at 47.5's — with the flip happening at `bmad-dev-story`. Under an open G26-DEVGO, marking an epic in-progress before any code exists would misreport state. Reported, not silently decided: the validate pass or the controller may overrule this.
3. **No research subagents were used** (§6, F-18). The workflow invites them; this session's harness forbids launching agents unless the user asks. All analysis was inline against HEAD `47fe971`.

## 18. Native code-review record (`bmad-code-review`)

**Verdict: APPROVE.** 0 critical, 0 important-blocking, 14 minor / forward-looking findings. **No fix loop is required for Story 49.1.**

> **SUPERSEDED IN PART — see §18.1.** This native verdict is preserved verbatim as the record of what the `bmad-code-review` pass concluded. It was **overridden by the controller**: the latent self-FK downgrade finding below was upgraded from "medium (latent), record a caveat in the docstring" to **blocking**, and a bounded review-fix loop was run. Five findings are now `[x]` because §18.1 fixed them, not because this pass did.

Native `bmad-code-review` (menu **CR**), 2026-07-26, Claude Opus 5 agent session in a **fresh independent context**, routed via native `bmad-help` → `_bmad/_config/bmad-help.csv` row `bmad-code-review` (phase `4-implementation`, `preceded-by: bmad-dev-story`). Customization resolved via `resolve_customization.py --skill .claude/skills/bmad-code-review --key workflow`: no team/user override (`activation_steps_prepend`/`activation_steps_append`/`on_complete` all empty); `persistent_facts` = `file:{project-root}/**/project-context.md` — **no file matches that repo-root glob**, so no persistent fact was loaded by the glob as written (the dev pass satisfied it from `_bmad-output/project-context.md`; that file was read here as context, not via the glob).

Target: branch `feat/E49.1-browse-category-entities`, the full uncommitted tracked + untracked working tree (9 files) against `baseline_commit` `d6299fa`. Review mode `full` (this document is the spec). Diff under review: 819 lines.

**Canonical parallel adversarial gate — all three layers ran, none failed, none returned empty:** Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`), Acceptance Auditor (spec-vs-diff). Each was launched without prior conversation context, at the same model capability as this session. `failed_layers` is empty. Every layer finding below was independently re-verified by this session before triage; five layer findings were rejected as false or spec-mandated (see "Dismissed").

**Executed independently by this session (read-only; tmpdir/in-memory scratch SQLite only — no live DB, no production access):**

- `pytest tests/test_browse_category_entity.py tests/test_migration_0020.py tests/test_migration_0019.py tests/test_migration_0004.py tests/test_orm_migration_parity.py -q` → **23 passed** (14 + 1 + 3 + 4 + 1), one pre-existing `model`/`model_file` `SAWarning`.
- **Non-vacuity probe (AC-12).** Rebuilt the ORM SQLite engine **without** the `PRAGMA foreign_keys=ON` listener and repeated the RESTRICT delete → it **succeeded**. The listener is genuinely load-bearing and the CASCADE/RESTRICT assertions are **not vacuous**. (Note the wording caveat in R-6 below.)
- **Index-shape probe (AC-1/AC-3).** `BrowseCategory.__table__.indexes` = exactly `[('uq_browse_category_slug', unique=True, ['slug'])]`; `create_all` DDL confirms `FOREIGN KEY(parent_id) REFERENCES browse_category (id) ON DELETE RESTRICT`.
- **`0019` re-pin proof (AC-11).** `command.upgrade(cfg, "0019_drop_category")` + `downgrade(cfg, "-1")` resolves `-1` against the DB's current revision (0019 → 0018), so `0019.downgrade()` is still the code under test. The proof survives; it does not pass for the wrong reason.
- **Scope/retirement (AC-8, AC-15).** `git diff HEAD -- apps/api/app/core/db/models/_entities.py` has **zero** `-` lines (pure append between `ModelTag` and `ModelPrint`). `test_orm_migration_parity.py`, `_helpers.py` and every `0001…0019` revision are byte-untouched. Every `category_id` occurrence in the change set is the **new** `model_browse_category.category_id`; no `category` table, no `model.category_id`, no `ix_model_category_id`, no bare `Category*` identifier.
- **Merge-gate evidence, inspected not trusted.** `.hermes/run-logs/check-all-e49-1-controller.log`: exactly **16** `==>` stage headers, summary `passed: 16` with all 16 `✓`, terminal `all green.`, no `skipped:`/`failed:` block. The three `skip` string hits are a vitest **test name**, the 3 pytest skips, and the 32 expected visual skips — **no stage was skipped**. `.hermes/run-logs/determinism-e49-1-controller.log`: exactly **three** API summaries, each `1762 passed, 3 skipped, 2014 warnings`, and exactly **three** web summaries, each `Test Files 136 passed (136)` / `Tests 785 passed (785)`; trailer `API_RC=0 WEB_RC=0`. Only one e49 `check-all` log exists in `.hermes/run-logs/` — the teardown-killed in-session attempt left no artifact, and none was counted.
- **Latent-hazard probe (R-10).** Reproduced `DROP TABLE` on a self-FK `RESTRICT` table under `PRAGMA foreign_keys=ON` with a parent/child pair → `IntegrityError: FOREIGN KEY constraint failed`. Confirmed `migrations/env.py` builds its engine via `engine_from_config` and never issues the pragma, so the hazard is not reachable on the actual Alembic path today.

**Per-AC result: AC-1 … AC-16 all PASS.** AC-9 (`compare_metadata` empty diff, parity test byte-unmodified), AC-10/AC-11 (head re-pinned by name; `0019`'s raising downgrade still proven), AC-13 (all three `ON DELETE` actions proven via `PRAGMA foreign_key_list`, every traversal pinned to an explicit revision id) and AC-16 were each re-derived from the code and the logs, not read off §15. **T6.3 is correctly left unchecked** — controller-owned, no commit exists; treated as intentional, **not** a product defect.

### Review Findings

Severity is this workflow's own rating, not the reviewing layers'. None of the below violates an AC of Story 49.1, and none blocks the commit.

- [x] [Review][Patch] **FIXED (§18.1).** Source comment points the wrong way: "the `Tag.slug` pattern **below**" [`apps/api/app/core/db/models/_entities.py:143`] — `Tag` is at `:47-61`, i.e. **83 lines above** `BrowseCategory` (`:130`). AC-3 itself cites `:51` correctly; only the comment's direction word is wrong. Severity low.
- [x] [Review][Patch] **FIXED (§18.1).** Same comment's parenthetical is factually false: `Field(unique=True, index=True)` does **not** emit "an auto-named index PLUS an unnamed UNIQUE constraint" [`apps/api/app/core/db/models/_entities.py:142-145`] — probed on the exact model it names: `Tag.__table__.indexes == [('ix_tag_slug', unique=True, ['slug'])]` and `Tag.__table__.constraints` holds only the FK and the PK. SQLAlchemy folds `unique+index` into **one** unique index. The comment's real (and correct) point is the **name** — `ix_…` vs the explicit `uq_…`. The same overstatement is carried in §6 F-9. Severity low; the AC-3 decision is unaffected and remains right.
- [x] [Review][Patch] **FIXED (§18.1).** Test docstring inverts the vacuity argument [`apps/api/tests/test_browse_category_entity.py:8-10`] — it claims the CASCADE/RESTRICT assertions "would pass vacuously" without the pragma. Probed: without the pragma they **fail loudly** (`DID NOT RAISE` / surviving child rows). The pragma is load-bearing for the tests being *correct*, not for them being non-vacuous. Same wording appears in §6 F-13 and AC-12. Severity low; the tests themselves are sound.
- [x] [Review][Patch] **UPGRADED TO BLOCKING BY THE CONTROLLER AND FIXED IN CODE, NOT IN A DOCSTRING (§18.1).** `0020`'s downgrade-safety rationale needs one caveat [`apps/api/migrations/versions/0020_browse_categories.py:113-120`] — `DROP TABLE browse_category` performs an implicit per-row delete on SQLite, and the self-FK `RESTRICT` fires on it. Reproduced: with a parent/child pair and `PRAGMA foreign_keys=ON`, the drop raises `FOREIGN KEY constraint failed` — **after** `drop_index("uq_browse_category_slug")` has already run, leaving a half-reverted schema. Not reachable today because `migrations/env.py` never enables the pragma (verified) and production runs only `alembic upgrade head` (`infra/scripts/deploy.sh:148`); the child-before-parent comment covers only the *cross-table* RESTRICT. Severity medium (latent). Unambiguous minimal fix: record the dependency on Alembic's pragma-off engine in the docstring.
- [x] [Review][Patch] **FIXED (§18.1).** `test_migration_0020.py` under-asserts `browse_category`'s own structure [`apps/api/tests/test_migration_0020.py:129-147`] — `BROWSE_CATEGORY_COLUMNS` is a **name-only** set; only `position`, `parent_id`, `created_at`, `updated_at` have their `(type, notnull, default)` inspected, and `_pk_columns` is asserted for `model_browse_category` (`:149`, `:221`) but **never** for `browse_category`. A `0020` that omitted `primary_key=True` on `id`, or made `slug`/`name_en` nullable, would pass this test unchanged. The parity gate does catch nullability, so this is lost redundancy rather than an open hole — but the file's docstring sells it as the structural proof. Severity low. **This is the only missing-test finding.**
- [x] [Review][Defer] `position` carries `server_default="0"` on the Alembic path and **no** default on the `create_all`/`init_schema` path [`apps/api/migrations/versions/0020_browse_categories.py:66` vs `apps/api/app/core/db/models/_entities.py:156`] — verified: Alembic emits `position INTEGER DEFAULT '0' NOT NULL`, `create_all` emits `position INTEGER NOT NULL`, and `BrowseCategory.__table__.c.position.server_default is None`. `compare_metadata` cannot see it (`compare_server_default` defaults to `False` and `migrations/env.py` never enables it), so AC-9 is structurally incapable of catching this class. **Exactly what AC-1 + AC-5 mandate**, and the shipped `tag_group.position` precedent §6 F-10 cites has the identical split — so not a defect here. Forward hazard: a raw-SQL/Core `INSERT` omitting `position` succeeds on the deployed Alembic-built DB and raises `NOT NULL constraint failed` in every pytest/dev DB. **Story 49.2's seed must set `position` explicitly, or use the ORM.** Severity medium — deferred, pre-existing pattern.
- [x] [Review][Defer] Soft-deleted models keep the `RESTRICT` alive [`apps/api/app/core/db/models/_entities.py:178-180` × `:82`] — `model_browse_category.model_id` CASCADE only fires on a **hard** row delete, and the application soft-deletes (`Model.deleted_at`). Verified: after `UPDATE model SET deleted_at=…`, deleting that model's only category is still blocked. AC-12(d)/(e) exercise hard delete only, so the interaction is uncharacterised. **Story 49.5's category-delete endpoint will surface this as an unexplained `IntegrityError`** on a category the admin sees as empty. `model_tag` has the identical shape. Severity medium — deferred, pre-existing shape mandated by binding constraint 9.
- [x] [Review][Defer] `downgrade()`'s safety rationale is time-bound [`apps/api/migrations/versions/0020_browse_categories.py:29-37`] — "it only creates two brand-new, initially empty tables" is true at *upgrade* time, not at *downgrade* time. Verified: with a seeded parent, child, model and one assignment, `alembic downgrade 0019_drop_category` succeeds and destroys all of it silently. Also: before this story, `alembic downgrade -1` at head hit `0019`'s raising downgrade — an accidental-downgrade tripwire that `0020` removes. Design is ratified (AC-7 / Decision AZ), so this is not a defect; no test downgrades a **non-empty** schema (`tests/test_migration_0020.py:192-204` downgrades an empty one). Severity medium — deferred; revisit at 49.2 when the tables stop being empty.
- [x] [Review][Defer] Timestamps read back tz-**naive** [`apps/api/app/core/db/models/_entities.py:161-162`] — declared as plain `datetime.datetime`, so `UTCDateTime` (`_helpers.py:18-37`) is bypassed and `got.created_at.tzinfo is None`; comparing one to an aware `datetime.now(UTC)` raises `TypeError`. `_entities.py` does not import `UTCDateTime` at all and **all nine** of its classes share this, while `_auth.py`/`_user.py`/`_recovery.py`/`invite/models.py` use the decorator — a genuine repo split, not introduced here. AC-1 mandates `default_factory=_now_utc` verbatim. `tests/test_browse_category_entity.py:66-67` only asserts `is not None`. Severity medium — deferred, repo-wide.
- [x] [Review][Defer] `compare_metadata` is blind to FK `ondelete` as well as to server defaults [`apps/api/tests/test_orm_migration_parity.py:66-73`, `apps/api/migrations/env.py:31-40`] — mutation-tested by the Blind Hunter layer: flipping `category_id` RESTRICT→CASCADE on the ORM side alone still yields `[]`. Nullability, index presence and index uniqueness **are** caught (also mutation-verified). The gate's own docstring and §8.3 call it "the mechanical proof of story atomicity"; that is accurate for tables/indexes/nullability and overstated for `ondelete`/defaults. Today the hole is covered by `test_migration_0020.py:157-179` plus the entity tests. Severity low — deferred, pre-existing gate design.
- [x] [Review][Defer] `browse_category.parent_id` is the only unindexed FK in the new schema [`apps/api/app/core/db/models/_entities.py:157-160`] — the retired `category` table the migration cites as precedent also had `op.create_index("ix_category_parent", "category", ["parent_id"])` (`0004_entity_tables.py:38`); `0020` drops that from the pattern without saying so. **AC-1 mandates exactly one `__table_args__` entry**, so the implementation is correct as specified. Forward note for 49.5's child listings and for the RESTRICT self-FK check. Severity low — deferred.
- [x] [Review][Defer] `parent_id` cycles are writable and then unremovable [`apps/api/app/core/db/models/_entities.py:157-160`] — `UPDATE … SET parent_id = id` and an A→B→A cycle are both accepted (cycle *rejection* is explicitly Story 49.5 per binding constraint 6, so accepting the write is an agreed deferral). The uncovered part is **recovery**: a single `DELETE` removing the whole cycle raises `FOREIGN KEY constraint failed`, because RESTRICT is immediate and per-row; the rows must be `UPDATE`d to `parent_id = NULL` first, which no ORM delete path does. Severity low — deferred to 49.5.
- [x] [Review][Defer] `slug` validation is unclaimed by any story [`apps/api/app/core/db/models/_entities.py:150`] — `''`, `'   '`, a 5000-character slug, and `LAMPS` coexisting with `lamps` are all accepted (BINARY collation ⇒ byte-exact uniqueness). Unlike depth and cycles, slug hygiene is **not** named as a 49.5 deferral anywhere. Same posture as the retired `category` table, so not a regression. Severity low — deferred; flagged for 49.2/49.5 scoping.
- [x] [Review][Defer] `updated_at` has no `onupdate` and no test would notice [`apps/api/app/core/db/models/_entities.py:162`] — verified: mutating `name_en` leaves `updated_at` at the creation timestamp. The repo's convention is manual maintenance in `admin_service.py`; until 49.5 does that, the column duplicates `created_at`. Severity low — deferred, repo-wide pattern.
- [x] [Review][Defer] Entity fixture hand-rolls its own engine + pragma instead of `create_engine_for_url` [`apps/api/tests/test_browse_category_entity.py:23-35` vs `app/core/db/session.py:12-27`] — so if someone removed `PRAGMA foreign_keys = ON` from the real engine factory, the running app would silently lose CASCADE/RESTRICT enforcement while all 14 new tests stayed green. Inherited verbatim from `test_tag_group_entity.py:18-32`, and **AC-12 explicitly binds the new test to that pattern**. Severity low — deferred, pre-existing.
- [x] [Review][Defer] `sqlite3.connect` helpers commit but never close [`apps/api/tests/test_migration_0020.py:58,70,77,89,182`] — `with sqlite3.connect(...)` is a transaction context manager, not a closing one; one round-trip leaks ~10 connections to a file Alembic reopens mid-traversal. Inherited from `test_migration_0019.py:39-50`. Severity low — deferred, pre-existing.
- [x] [Review][Defer] Neither controller evidence log records its own HEAD or dirty-state [`.hermes/run-logs/check-all-e49-1-controller.log`, `.hermes/run-logs/determinism-e49-1-controller.log`] — T6.1 explicitly invokes the standing epic:47 **evidence-provenance** action item, and the "ran against HEAD `d6299fa` with an intentionally dirty 9-file tree" claim lives **only in §5/§15 prose**. Both logs open directly on `==> apps/api ruff format`; grepping them for `HEAD`/`commit`/`dirty`/`d6299fa` returns nothing. Corroboration is circumstantial but consistent (`1762 passed` = the stated 1747 baseline + the 15 tests that exist only in this change set). AC-16 as written is satisfied. Severity low — deferred, controller/process-owned, not a code issue.
- [x] [Review][Defer] `tag_group` is still absent from the index-parity guard's `new_tables` [`apps/api/tests/test_migration_0004.py:161-174`] — the list now covers both new browse tables (AC-14 satisfied), but `tag_group`, added by `0018`, was never added and remains unguarded. Pre-existing, outside §7 scope, **not caused by this story**. Severity low — deferred.

**Dismissed as noise or false (5, dropped from the list above, recorded so they are not re-raised):**

1. *"`test_migration_0020.py:187` reintroduces a bare `category` literal that `0019`'s test avoids"* — **false**. `test_migration_0019.py:84` also uses the bare `"category"` literal; its runtime assembly covers only `category_id`/`ix_model_category_id` — and `test_migration_0020.py:187-190` performs exactly the same assembly (`f"ix_model_{legacy}_id"`, `f"{legacy}_id"`). The discipline was kept, not dropped.
2. *"The head-name assertion now lives in the wrong file"* — **spec-mandated**. AC-10 / T1.2 / §6 F-1 require editing that existing assertion in place rather than relocating it.
3. *"`test_upgrade_head_drops_category_schema` still traverses to `head`"* — **spec-mandated**. T1.4 and §6 F-3 explicitly require leaving it untouched; its assertions are exact-name set membership and stay valid as head advances.
4. *"Sibling `position` has no tie-breaker, so ordering is non-deterministic"* — **handled downstream**. Story 49.3 already specifies ordering by `(position, slug)` (`sprint-status.yaml`, `49-3-category-read-api-and-model-scope`), which is deterministic. NFR26-DETERMINISM-1 is a test-count property and is discharged separately.
5. *"`uq_browse_category_slug` is an index, not a named constraint, so `ON CONFLICT ON CONSTRAINT` is unavailable"* — **not reachable**. Production is SQLite (`infra/docker-compose.yml:27`), and the inference form `ON CONFLICT (slug)` works on both dialects.

Additionally recorded, **not** a finding: AC-1 writes `position: int = 0` while the code is `position: int = Field(default=0)` (`_entities.py:156`). Semantically identical, and it is exactly the `TagGroup.position` shape (`:42`) that §6 F-10 cites as the `compare_metadata`-safe precedent. Reading AC-1 literally would have diverged from its own cited precedent.

**Disclosed deviations of this review pass from the base `bmad-code-review` workflow:**

1. **Step 1's checkpoint HALT was not taken.** The operator instruction that invoked this run identified the target (branch, spec, tracked+untracked scope) and demanded a consolidated verdict in one pass. The Tier-1 cascade resolved the target without ambiguity, so there was nothing to ask.
2. **Step 4's patch HALT was not taken and no patch was applied.** The run is **review-only** by explicit operator instruction — no implementation or test file was modified, created, or deleted. All five `patch` findings are left as unchecked action items, which is the outcome of option 2 ("leave as action items").
3. **Step 4 §6 (status update) was deliberately NOT executed.** The base workflow would set this story to `done` or `in-progress` and sync `sprint-status.yaml`. By explicit operator instruction, **Story 49.1 stays at `review` and `epic-49` stays at `in-progress`; neither was marked `done`.** No line of `sprint-status.yaml` was touched by this pass.
4. **No `deferred-work.md` entry was written.** Step 4 §2 would append the `defer` findings to `{implementation_artifacts}/deferred-work.md`; that file does not exist, and creating a new ledger artifact is outside this run's authorization. The eleven `defer` findings are recorded here in full and are flagged for the controller.
5. **Subagents were used, and that is a change from §17.3.** The create and dev passes ran without them under a harness restriction; this run's operator instruction explicitly requested the parallel adversarial gate, so all three layers were launched as independent subagents with no prior conversation context.

**Provenance — truthful.** This review was performed by a **Claude Opus 5 agent session** and by three subagent review layers. **No human has reviewed this code or this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable from this record.** No commit, squash, push, merge, deploy, live-DB access or production access was performed. This pass ran no Aider review — the independent Aider diff-review gate is separate and still outstanding.

**Next canonical step:** controller review of the uncommitted diff, then the independent Aider review gate, then one commit under the repo's one-commit / ff-only rules. Optionally `bmad-retrospective` (**ER**) once Epic 49 completes.

## 18.1 Bounded review-fix loop (controller-directed)

**Trigger — the controller overruled the native triage.** The §18 pass rated the self-FK downgrade hazard *medium (latent)* and proposed a docstring caveat, on the reasoning that `migrations/env.py` never enables `PRAGMA foreign_keys`. The controller rejected that disposition: a `downgrade()` that is only safe because an unrelated file happens not to issue a pragma is not a *safely reversible* migration, and §18's own "genuinely safe and complete rollback" claim (`0020_browse_categories.py:29-37`) is then conditional in a way the docstring did not state. **Controller verdict: REQUEST_CHANGES.**

**Gate provenance — stated exactly as known to this session.** The controller instruction that invoked this pass reports that the independent Aider diff-review gate returned **REQUEST_CHANGES** on the same finding. **This session did not run Aider and holds no Aider log**; the verdict is recorded here as relayed by the controller, not as something this pass executed or verified. The §18 statement "This pass ran no Aider review" remains true of §18.

**Method: strict TDD, RED observed before any implementation change.**

### RED (observed, not asserted)

A new focused test was written first — `tests/test_migration_0020.py::test_migration_0020_downgrade_under_foreign_key_enforcement`. It upgrades a tmpdir scratch DB to `0020_browse_categories`, inserts a `browse_category` parent/child pair, then executes **the revision's own `downgrade()` body** (loaded by path via `importlib`) through `Operations(MigrationContext.configure(connection))` on a connection where `PRAGMA foreign_keys=ON` is explicitly set **and asserted** (`PRAGMA foreign_keys` → `1`) — SQLite silently ignores that pragma inside an open transaction, so asserting it is what stops the test being vacuous.

Against the **pre-fix** `downgrade()` it failed:

```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint failed
[SQL:
DROP TABLE browse_category]
```

**The partial drop is worse than §18 recorded, and was measured, not assumed.** A probe inspected `sqlite_master` after the failure and again after the connection was closed **without** `commit()`. The three preceding statements — `drop_index ix_model_browse_category_cat_model`, `drop_table model_browse_category`, `drop_index uq_browse_category_slug` — are **still gone on disk**, because SQLite DDL issued outside an explicit transaction autocommits (Alembic logs "Will assume non-transactional DDL" for `SQLiteImpl`). So the failure does not roll back: it leaves a **permanently half-reverted schema** — `browse_category` alive but stripped of its unique-slug index, and the join table destroyed. §18's "leaving a half-reverted schema" was right about the shape and understated the persistence.

### GREEN (the fix)

`downgrade()` now disarms the **internal** self-FK before any drop operation:

```python
op.execute("UPDATE browse_category SET parent_id = NULL WHERE parent_id IS NOT NULL")
```

Scoped, and lossless by construction: every row it touches belongs to a table the next four statements delete, so nulling `parent_id` discards no surviving data — it only removes the ordering constraint between rows that are all going away. The pre-existing child-before-parent drop order (which covers the *cross-table* RESTRICT on `model_browse_category.category_id`) is unchanged; this covers the *intra-table* one the original comment did not.

The test proves **completeness**, not merely absence of an exception: after the downgrade, both tables and both named indexes are gone, and `model` / `tag` / `tag_group` / `model_tag` all survive.

### Also fixed in this pass (four §18 `[Review][Patch]` findings)

- **`tests/test_migration_0020.py` structural under-assertion.** Added direct assertions for `browse_category`: `_pk_columns(...) == {"id"}`, and required-vs-optional nullability pinned on **both** halves — `id`/`slug`/`name_en`/`position`/`created_at`/`updated_at` `NOT NULL`; `name_pl`/`description_en`/`description_pl`/`inclusion_criterion`/`parent_id` nullable. A `0020` that lost `primary_key=True` on `id`, or that made `slug`/`name_en` nullable, now fails in this file rather than only in the parity gate. These assertions were **green on first run** — they are regression hardening, not part of the RED.
- **`_entities.py:140-147` comment — direction and factual claim.** "the `Tag.slug` pattern **below**" → **above** (`Tag` is at `:47-61`, `BrowseCategory` at `:130`). The claim that `Field(unique=True, index=True)` emits "an auto-named index PLUS an unnamed UNIQUE constraint" is **false and was removed**; re-probed independently by this session on the resolved SQLModel **0.0.38**: `Tag.__table__.indexes == [('ix_tag_slug', unique=True, ['slug'])]` and `Tag.__table__.constraints` holds only `PrimaryKeyConstraint` + `ForeignKeyConstraint` — SQLAlchemy folds `unique+index` into exactly **one** unique index. The comment now states the real reason for the explicit `Index(...)`: **exact `uq_browse_category_slug` naming/parity** with `0020`, since the shorthand would auto-name it `ix_browse_category_slug`. The AC-3 decision is unaffected and remains correct. (§6 F-9 still carries the same overstatement and was **not** edited — planning-artifact text is outside this pass's authorization; flagged for the controller.)
- **`tests/test_browse_category_entity.py:8-10` docstring — inverted vacuity argument.** Rewritten: without the pragma the CASCADE/RESTRICT assertions **fail loudly** (`DID NOT RAISE` for RESTRICT, surviving child rows for CASCADE) or stop exercising any DB action — they do **not** pass vacuously. The listener is what makes them *correct*. (The same wording in §6 F-13 and AC-12 was left untouched, same reason as above.)
- **`0020` downgrade rationale comment — corrected location wording (was "docstring"; §18.3 I-6).** The hazard-and-dependency text was added as an **in-function comment inside `downgrade()`** (`0020_browse_categories.py:113-127` as shipped at the time of that edit), not to the module docstring at `:29-37`, which is byte-identical to what §18 quoted pre-fix and still carries its uncaveated "genuinely safe and complete rollback" wording (ledgered as a `[Defer]` at §18 line 492). The substance of the claim shipped; only this bullet's original location word was wrong, and it is corrected here.

### Scope discipline

Exact schema, both index names, all `ON DELETE` actions, every AC behaviour and the story's file set are **unchanged**. No seed content, no API/router/service/schema, no UI, no dependency change, no live DB. `upgrade()` is byte-untouched. No planning artifact outside this story file was edited.

### Verification executed by this pass

- `ruff format --check` + `ruff check` on the four touched Python files → **4 files already formatted**, **All checks passed!**
- `pytest tests/test_migration_0020.py tests/test_browse_category_entity.py tests/test_orm_migration_parity.py tests/test_migration_0019.py tests/test_migration_0004.py -q` → **24 passed** (2 + 14 + 1 + 3 + 4), one pre-existing `model`/`model_file` `SAWarning`. Previous total was 23; the delta is the one new FK-enforcement test.
- No `check-all`, no determinism run, no full suite — out of this pass's scope by instruction; those remain controller-owned.

### Files changed by this pass (4 code/test + this story file)

| File | Change |
| --- | --- |
| `apps/api/migrations/versions/0020_browse_categories.py` | `downgrade()`: scoped `UPDATE … SET parent_id = NULL` before any drop, + rationale comment |
| `apps/api/tests/test_migration_0020.py` | new FK-enforcement downgrade test + `_load_revision` helper + `browse_category` PK/nullability assertions |
| `apps/api/app/core/db/models/_entities.py` | `BrowseCategory.__table_args__` comment corrected (direction + the false UNIQUE-constraint claim) |
| `apps/api/tests/test_browse_category_entity.py` | module docstring: vacuity argument corrected |
| `_bmad-output/implementation-artifacts/49-1-…-migration.md` | §18 finding checkboxes + this §18.1 |

### Status and remaining gates

**Story 49.1 stays at `review`. `epic-49` stays at `in-progress`. Neither was marked `done`; `sprint-status.yaml` was not touched by this pass.** No commit, squash, push, merge or deploy was performed.

Still outstanding before this story can close:

1. **Controller re-review of the updated uncommitted diff** — in particular the new `downgrade()` statement and the new test.
2. **Independent Aider diff-review gate, re-run on the fixed diff.** The relayed REQUEST_CHANGES was against the pre-fix diff; a fix does not discharge the gate, a fresh green run does. Under the standing rulebook, `rc=4` = REQUEST_CHANGES.
3. **Full `check-all` + determinism re-run** — the §18 evidence logs (`.hermes/run-logs/check-all-e49-1-controller.log`, `determinism-e49-1-controller.log`) predate this pass and no longer describe the code under review. AC-16 needs fresh artifacts. Expected API delta: **1763 passed** (one new test), pending measurement — not asserted here.
4. **The eleven `defer` findings and the two planning-artifact drifts** (§16 F-15) remain open and controller-owned; still no `deferred-work.md`.

**Provenance — truthful.** This review-fix pass was performed by a **Claude Opus 5 agent session**. **No human has reviewed this code or this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable.** No subagents were used. The Aider verdict above is **relayed from the controller instruction, not executed here**. No commit, push, merge, deploy, live-DB or production access was performed.

## 18.2 Native re-review record (`bmad-code-review`, post-repair)

**Verdict: REQUEST_CHANGES.** 0 critical, **2 important**, 4 minor. The controller-mandated `downgrade()` repair itself is **sound and is approved on its merits** — see "Focus verdict" below. The requested changes are **one missing test** and **outstanding AC-16 gate evidence**; neither requires a change to shipped behaviour, and no finding contradicts an AC.

Native `bmad-code-review` (menu **CR**), 2026-07-26, Claude Opus 5 agent session, routed via native `bmad-help` → `_bmad/_config/bmad-help.csv` row `bmad-code-review` (phase `4-implementation`, `preceded-by: bmad-dev-story`). Customization resolved via `resolve_customization.py --skill .claude/skills/bmad-code-review --key workflow`: no team/user override; `persistent_facts` = `file:{project-root}/**/project-context.md` — no file matches that repo-root glob as written (`_bmad-output/project-context.md` exists and was read as context, not via the glob).

Target: branch `feat/E49.1-browse-category-entities`, full uncommitted tracked + untracked working tree (9 files) against `baseline_commit` `d6299fa`. Review mode `full` (this document is the spec). Code diff under review: 941 lines.

**Canonical parallel adversarial gate — all three layers ran in fresh independent contexts at this session's model capability; none failed, none returned empty. `failed_layers` is empty.** Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`), Acceptance Auditor (spec-vs-diff). Every layer finding below was independently re-verified by this session before triage; severities are this workflow's own, not the layers'.

**Executed independently by this session (read-only; tmpdir/scratch SQLite and a `/tmp` repo copy only — no live DB, no production access, no repo file modified):**

- **Drop-order mutation, run against a `/tmp` copy of `apps/api`** (repo file never touched). Swapped `downgrade()` to drop `browse_category` before `model_browse_category`, then ran the shipped suite: `pytest tests/test_migration_0020.py tests/test_orm_migration_parity.py tests/test_migration_0019.py -q` → **6 passed**. The order regression is invisible to the suite.
- **Same mutant driven through `Operations(MigrationContext.configure(connection))` with `PRAGMA foreign_keys` asserted `= 1`**, parameterised on the seed data:
  - mutant + the shipped test's data (parent/child only) → `COMPLETED, leftover=[]` — **test would pass**;
  - mutant + one `model` + one `model_browse_category` row → `RAISED IntegrityError: FOREIGN KEY constraint failed`, `leftover=['browse_category','ix_model_browse_category_cat_model','model_browse_category','uq_browse_category_slug']`;
  - shipped code, both seeds → `COMPLETED, leftover=[]`.
  This proves the child-before-parent order is genuinely load-bearing **and** that nothing in the suite pins it.
- **Transaction shape, measured not assumed.** In the mutant-with-join-rows abort above, **all four** objects survive — i.e. the traversal rolled back completely. The leading `UPDATE` is DML, so pysqlite opens an implicit transaction and the subsequent DDL is no longer autocommitting. This is a real, beneficial side effect of the repair that the source does not state (see M-1/M-2).
- **Evidence-log inspection at absolute paths.** `.hermes/run-logs/check-all-e49-1-final-controller.log` (mtime 09:29:04, **post-fix**): 16 `==>` stage headers, `passed: 16`, all 16 `✓`, terminal `all green.`, `apps/api pytest` **1763 passed / 3 skipped / 2014 warnings**. `.hermes/run-logs/determinism-e49-1-final-controller.log` (mtime 09:45:02): **still executing at review time** — 3 `=== API RUN ===` headers, **2 of 3** API summaries complete (each `1763 passed, 3 skipped, 2014 warnings`), 3 of 3 web summaries complete (each `Tests 785 passed (785)`), **no `API_RC=/WEB_RC=` trailer yet**. Neither final log is cited anywhere in this story.
- **Deploy-path reachability.** `infra/scripts/deploy.sh:148` runs `alembic upgrade head` only; no repo script, hook, compose file or doc under `infra/` runs `alembic downgrade`. The only `alembic downgrade` strings in the repo are prose in `docs/superpowers/specs/2026-05-04-portal-source-of-truth-design.md:1115,1123`.
- **Working-tree integrity.** `git status --porcelain` is the same 9 entries before and after this pass; `HEAD` is still `d6299fa`. No implementation or test file was created, edited or deleted by this review.

**Focus verdict — the repair is safe, bounded, and does not hide another FK or transaction issue.** Confirmed by three independent lines of evidence (two layers plus this session):

- **Sufficient for the self-FK path.** The revision's own `downgrade()` completes with `PRAGMA foreign_keys=ON` across every row shape enumerated: empty, single root, parent/child, multi-level chain, `parent_id = id` self-loop, A→B→A cycle, orphan `parent_id`, and with join rows present (including rows referencing a soft-deleted model). The Edge Case Hunter ran a 10-state × 2-path × 2-pragma matrix — 40 cells, all clean.
- **Bounded.** A `PRAGMA foreign_key_list` sweep of every table confirms the only inbound FKs to `browse_category` are `browse_category.parent_id` and `model_browse_category.category_id`; the schema has zero triggers and zero views. The `UPDATE` is `WHERE parent_id IS NOT NULL` on a table the next four statements delete, so it can touch nothing that survives. `ON DELETE RESTRICT` fires on parent-side DELETE, never on nulling the referencing column, so the statement cannot itself trip the FK.
- **Non-vacuous.** Removing only the `UPDATE` line in a `/tmp` copy makes `test_migration_0020_downgrade_under_foreign_key_enforcement` **fail** with `IntegrityError: FOREIGN KEY constraint failed [SQL: DROP TABLE browse_category]`. Mutation-proved independently by the Blind Hunter and the Edge Case Hunter.
- **The round-trip test really is blind to this class**, as the new test's docstring claims: every connection `migrations/env.py` opens reports `PRAGMA foreign_keys -> 0`. The new test is not redundant.
- **`upgrade()` is byte-unaffected** and still inserts zero rows.

**Per-AC result: AC-1 … AC-15 PASS on independent re-derivation. AC-16 is NOT currently discharged for the code under review** — not because the repair broke it, but because the fresh determinism triple had not finished at review time (see I-2). The `[x]` on T5.1/T6.1/T6.2 still points at the pre-fix logs.

### Review Findings

- [x] [Review][Patch] **FIXED (§18.3) — I-1. IMPORTANT (missing test) — the new FK-enforcement test seeds no `model_browse_category` rows, so the cross-table RESTRICT drop-order invariant is unguarded** [`apps/api/tests/test_migration_0020.py:294-302`] — the seed inserts only a `browse_category` parent/child pair, so the only FK armed under enforcement is the *self*-FK. The `category_id → browse_category.id` RESTRICT — the one `0020_browse_categories.py:130-132` explicitly says the drop order exists to satisfy — is never live during the traversal. Mutation-proved by all three sources: with the order swapped, the whole suite stays green on the shipped seed, while one assignment row turns the same build into `IntegrityError: FOREIGN KEY constraint failed` with the downgrade impossible and `alembic_version` stuck at `0020_browse_categories`. This is the same defect class §18.1 just repaired, one FK over. Unambiguous minimal fix: add one `model` row and one `model_browse_category` row to the existing seed. **This is the only missing-test finding.**
- [x] [Review][Patch] **FIXED (§19) — I-2. IMPORTANT (gate evidence) — AC-16 is discharged by the frozen final2 check-all and determinism artifacts** [`.hermes/run-logs/`] — §18's cited logs (`check-all-e49-1-controller.log` 08:20:34, `determinism-e49-1-controller.log` 08:41:38) predate the §18.1 code edits (09:12:55–09:13:24) and record `1762 passed` against the current `1763 passed`; §18.1 "Still outstanding" #3 discloses this honestly and its predicted 1763 is now **measured correct**. Fresh artifacts exist but are **uncited**: `check-all-e49-1-final-controller.log` is complete and green (16/16, `all green.`, 1763 passed / 3 skipped), while `determinism-e49-1-final-controller.log` was **still running** at review time (2 of 3 API summaries, no `API_RC=/WEB_RC=` trailer). Action: let the triple finish, then cite both final logs and re-scope §18's "AC-1 … AC-16 all PASS" line, which now reads as current but is not.
- [x] [Review][Patch] **FIXED (§18.3) — I-3. MINOR — the rationale comment's transaction sentence reads as a claim about the current function, but is only true of the pre-fix counterfactual** [`apps/api/migrations/versions/0020_browse_categories.py:118-121`] — "Because SQLite DDL **here** runs outside a transaction, the earlier drops have ALREADY been committed at that point, leaving a permanently half-reverted schema." Once the `UPDATE` is the first statement that is no longer true of this body: measured above, an abort mid-`downgrade()` now rolls back completely. The motivation is correct; the mechanism sentence needs the counterfactual framing ("without this `UPDATE` …") so a future reader does not rely on it as a property of the shipped code.
- [x] [Review][Defer] **DEFERRED BY THE CONTROLLER (§18.3/§19) — I-4. MINOR — the repair's losslessness silently depends on the drops sharing pysqlite's implicit transaction** [`apps/api/migrations/versions/0020_browse_categories.py:125-128`] — the "loses NO surviving data" claim holds because the following drops are in the same transaction, a property nothing in the file states or tests. The Blind Hunter demonstrated that under an `isolation_level = AUTOCOMMIT` engine, or via offline `alembic downgrade --sql` (which emits the `UPDATE` and the four DDL statements with no `BEGIN`/`COMMIT` wrapper), a later failure leaves `browse_category` alive with its hierarchy permanently erased. **Not reachable on any shipped path** — `deploy.sh:148` runs `upgrade head` only and nothing in the repo runs a downgrade or sets AUTOCOMMIT. One sentence in the comment closes it.
- [x] [Review][Patch] **FIXED (§18.3) — I-5. MINOR — the new FK test never asserts its own precondition** [`apps/api/tests/test_migration_0020.py:290-302`] — it inserts the parent/child pair and goes straight into the engine block; it is demonstrably not vacuous today (mutation-proved), but a `SELECT count(*) FROM browse_category WHERE parent_id IS NOT NULL` assertion would pin the precondition against future schema or insert drift.
- [x] [Review][Patch] **FIXED (§18.3) — I-6. MINOR (record accuracy) — §18.1's "`0020` downgrade docstring" bullet names the wrong location** [this file, §18.1] — the module docstring at `0020_browse_categories.py:29-37` is byte-identical to what §18 quoted pre-fix and still reads "0020 destroys nothing … a genuinely safe and complete rollback" with no caveat. The hazard-and-dependency text was in fact added as an **in-function comment** at `:114-127`, where it does name both explicitly. The claimed substance shipped; only the bullet's location wording is loose.
- [x] [Review][Defer] `upgrade()` has the same non-atomic-DDL window and is unrepaired and unrecoverable [`apps/api/migrations/versions/0020_browse_categories.py:91-111`] — it issues no DML, so nothing opens a transaction; the Blind Hunter proved a failure at the last `create_index` leaves `browse_category`, `uq_browse_category_slug` and `model_browse_category` on disk with `alembic_version` still at `0019_drop_category`, and a retry then fails with `table browse_category already exists`. Production is SQLite (`infra/docker-compose.yml:27`), so this is real — but `0018`/`0019` share the pattern, so it is a **pre-existing class, not a 49.1 regression**. The asymmetry (downgrade now incidentally atomic, upgrade not) is worth one line of documentation. Deferred, pre-existing.
- [x] [Review][Defer] `downgrade()` is not re-runnable, so a database already in the half-reverted state has no repair path [`apps/api/migrations/versions/0020_browse_categories.py:113-136`] — reproduced: from a manufactured half-reverted state, `command.downgrade(cfg, "0019_drop_category")` fails with `OperationalError: no such index: ix_model_browse_category_cat_model`. The repair prevents that state arising via the online path; it does not heal a DB downgraded by a pre-repair build. Deferred, no such database exists (the migration has never been deployed).
- [x] [Review][Defer] The extended index-parity guard passes silently for a table that does not exist [`apps/api/tests/test_migration_0004.py:172-180`] — `_index_set` returns `set()` for an absent table on both sides, so if either construction path lost a table entirely the guard would still be green. AC-14 is satisfied as written; an existence assertion per table would close the residue. Deferred, pre-existing helper shape.
- [x] [Review][Defer] The eleven §18 `[Review][Defer]` findings were independently re-reproduced and **re-confirmed unchanged** by the Edge Case Hunter — `position` server_default split, soft-deleted-model RESTRICT, non-empty downgrade destroying real rows, tz-naive timestamps, `compare_metadata` blind to `ondelete`, unindexed `parent_id`, writable-but-unremovable `parent_id` cycles, unvalidated `slug`, `updated_at` without `onupdate`, hand-rolled test engine, unclosed `sqlite3.connect` helpers. None became a defect in this pass; none is newly caused by the repair. Deferred, already ledgered in §18.

**Dismissed as false or already handled (recorded so they are not re-raised):**

1. *"The post-fix `check-all-e49-1-final-controller.log` is truncated/killed at 9 of 16 stages"* (Acceptance Auditor) — **false, an artefact of reading a file mid-write.** Re-inspected after completion: 16 stage headers, `passed: 16`, terminal `all green.`, `1763 passed / 3 skipped`. The layer sampled it at 09:23 while the run was still in progress; it finished at 09:29:04.
2. *"The `UPDATE` violates AC-6 / binding constraint 10 / §10 non-goals"* — **false.** AC-6 constrains `upgrade()` only, and `upgrade()` is byte-untouched (verified: zero rows in both tables after upgrade). The statement is DML, not DDL, so "no destructive DDL" does not reach it, and it cannot be more destructive than the `DROP TABLE`s AC-7 itself mandates on the same rows. It is not seed content, not a model assignment, and not a live-DB action.
3. *"AC-7 is no longer satisfied because a statement was prepended"* — **false.** Both named indexes are still dropped, `model_browse_category` (`:134`) still precedes `browse_category` (`:136`), nothing raises `NotImplementedError`, and the departure rationale is still recorded. T3.4's prescribed order is unchanged; the `UPDATE` reorders nothing.
4. *"`position = 2**31` / `2**70` boundary failures"* — **not reachable.** `2**70` raises `OverflowError` at the SQLite driver and `2**31` round-trips fine; only a PostgreSQL `int4` would care, and nothing in the repo targets PostgreSQL.
5. *"The `0020` module docstring's unconditional safety claim is false"* — **already ledgered**, not new: §18 line 492 records the time-bound rollback rationale as an agreed `[Defer]`. Re-confirmed (a downgrade over seeded data succeeds and destroys it silently), not re-raised.

**§18.1's own claims — independently re-verified TRUE:**

| §18.1 claim | Verdict | How verified |
|---|---|---|
| `_entities.py` comment direction "below" → "above" | **TRUE** | `Tag` at `:47-60`, `BrowseCategory` at `:130`; comment `:144` now reads "above" |
| The false "auto-named index PLUS an unnamed UNIQUE constraint" claim removed | **TRUE** | Probed on the resolved runtime (SQLModel 0.0.38 / SQLAlchemy 2.0.49) by two layers independently: `Tag.__table__.indexes == [('ix_tag_slug', unique=True, ['slug'])]`, constraints hold only PK + FK. The corrected comment's stated reason — the auto-generated **name**, not the object count — is the right one, and AC-3 is unaffected |
| `test_browse_category_entity.py:8-13` vacuity argument corrected | **TRUE** | Running a `/tmp` copy with the pragma listener deleted → **3 failed, 11 passed**: `DID NOT RAISE` on both RESTRICT tests and surviving child rows on the CASCADE test. They fail loudly; they do not pass vacuously |
| Direct `_pk_columns(...) == {"id"}` + required/optional nullability assertions added | **TRUE** | `tests/test_migration_0020.py:155,157-168`; reflected DDL confirms `PRIMARY KEY (id)`, the 6 NOT NULL / 5 nullable split, and `position INTEGER DEFAULT '0' NOT NULL` |
| `ruff format --check` + `ruff check` clean on the four touched files | **TRUE** | Re-run: `4 files already formatted`, `All checks passed!`, rc=0 (whole repo: `273 files already formatted`) |
| `pytest` over the five files → 24 passed (2+14+1+3+4) | **TRUE** | Re-run: **24 passed**, per-file split exactly 2 / 14 / 1 / 3 / 4 |
| Scope held; `upgrade()` byte-untouched; no planning artifact outside this file edited | **TRUE** | `git status --porcelain` = exactly the 9 expected entries; `test_orm_migration_parity.py` byte-unmodified and passing; `0001…0019*.py`, `env.py`, `alembic.ini`, `_helpers.py`, `app/modules/**`, `apps/web/**`, `workers/render/**`, both `uv.lock` untouched; `_entities.py` and `__init__.py` diffs contain zero `-` lines. `0020_browse_categories.py` is untracked so git holds no pre-fix snapshot — corroborated instead by §18's pre-fix line citations `:29-37` and `:66` still landing byte-exactly, confining every §18.1 edit to `downgrade()` |

**Record truthfulness.** No fabricated or implied human sign-off exists anywhere in this document. `Status: review` and `epic-49: in-progress` are both intact and were not touched by this pass. T6.3 remains the single unchecked task box and is correctly justified — `HEAD` is still `d6299fa` and no commit exists. §18.1 correctly labels the Aider verdict as relayed, not executed.

**Disclosed deviations of this re-review pass from the base `bmad-code-review` workflow:**

1. **Step 1's checkpoint HALT was not taken.** The operator instruction resolved the Tier-1 target unambiguously (branch, spec, tracked + untracked scope) and required a consolidated verdict in one pass.
2. **Step 4 §5's patch HALT was not taken and no patch was applied.** This run is **review-only** by explicit operator instruction — no implementation or test file was modified, created or deleted. All six `patch` findings are left as unchecked action items, which is the workflow's option 2 outcome.
3. **Step 4 §6 (status update and sprint sync) was deliberately NOT executed.** The base workflow would set this story to `in-progress` and sync `sprint-status.yaml`. By explicit operator instruction, **Story 49.1 stays at `review` and `epic-49` stays at `in-progress`.** No line of `sprint-status.yaml` was touched by this pass.
4. **No `deferred-work.md` entry was written.** That ledger still does not exist and creating it remains outside this run's authorization; the `defer` findings are recorded here in full.
5. **Subagents were used** — the operator instruction explicitly required the canonical three-layer parallel gate in fresh independent contexts.

**Provenance — truthful.** This re-review was performed by a **Claude Opus 5 agent session** and by three subagent review layers. **No human has reviewed this code or this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable from this record.** No commit, squash, push, merge, deploy, live-DB access or production access was performed. This pass ran **no Aider review**; the independent Aider diff-review gate on the fixed diff is separate and still outstanding.

**Next canonical step:** close I-1 (one test seed) and I-2 (cite the completed final gate logs), then re-run the independent Aider gate on the fixed diff, then one commit under the repo's one-commit / ff-only rules.

## 18.3 Native re-review repair (controller-directed, bounded to I-1)

**Trigger — §18.2's native re-review returned REQUEST_CHANGES; the controller accepted I-1 and scoped this pass to it.** I-1 is a real hole of exactly the class §18.1 repaired one FK over: `test_migration_0020_downgrade_under_foreign_key_enforcement` seeded a `browse_category` parent/child pair but **no** `model_browse_category` row, so only the *self*-FK was armed during the traversal and the cross-table `category_id → browse_category.id` RESTRICT — the FK the child-before-parent drop order exists to satisfy — was never live. A mutant that drops `browse_category` before the join table therefore passed.

### The repair (test only — no schema, no behaviour change)

`tests/test_migration_0020.py::test_migration_0020_downgrade_under_foreign_key_enforcement`:

- **Seed extended** with one minimal legal `model` row against the **actual post-0019 `model` schema** (re-derived from a migrated scratch DB, not from the ORM source): `id`, `slug`, `name_en`, `date_added`, `created_at`, `updated_at` are its only `NOT NULL` columns without a `server_default`; `source`/`status` take their server defaults, `rating` stays `NULL` (satisfying `ck_model_rating_range`) and `thumbnail_file_id` stays `NULL`, so no `model_file` row is needed.
- **One `model_browse_category` row** referencing that model and the child category — this is what arms the cross-table RESTRICT.
- **Preconditions asserted before the downgrade** (closing I-5 in the same edit), all on the *same* connection that runs `downgrade()`: `PRAGMA foreign_keys` → `1` (pre-existing), `SELECT count(*) FROM browse_category WHERE parent_id IS NOT NULL` → `1`, the assignment row present → `1`, and `PRAGMA foreign_key_check` → **empty**, so any `IntegrityError` in the traversal comes from the drop order under test and never from a broken fixture.
- **Final assertions kept verbatim**: both tables and both named indexes gone, and `model` / `tag` / `tag_group` / `model_tag` all surviving. The docstring now states that the cross-table RESTRICT is under test and that a parent/child pair alone leaves the drop order unpinned.

### Mutation evidence — executed, on a `/tmp` copy only; the repo file was never modified

`rsync` copy of `apps/api` to `/tmp/mut0020/api`, `downgrade()`'s four statements reordered there so `browse_category` drops **before** `model_browse_category`:

| Build | Seed | Result |
| --- | --- | --- |
| **mutant** (reversed drop order) | repaired seed (parent/child + model + assignment) | **RED — 1 failed, 1 passed.** `sqlite3.IntegrityError: FOREIGN KEY constraint failed` / `sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint failed`, `[SQL: DROP TABLE browse_category]` |
| **mutant** (reversed drop order) | pre-repair seed (parent/child only) | **2 passed** — the blindness I-1 reported, reproduced directly |
| **production order** (repo, unmutated) | repaired seed | **2 passed** |

That triple is the proof the repair asks for: the reversed order now fails, the shipped order passes, and the old seed demonstrably could not tell them apart. `/tmp/mut0020` was deleted afterwards; `git status --porcelain` is the same 9 entries as before this pass and `HEAD` is still `d6299fa`.

### Source-comment correction (I-3)

`0020_browse_categories.py` `downgrade()`'s rationale comment previously asserted, as a property of the shipped body, that "Because SQLite DDL **here** runs outside a transaction, the earlier drops have ALREADY been committed at that point". §18.2 measured that this is no longer true of this function. The sentence is now **explicitly counterfactual**: it names the pre-fix body and the RED actually observed for it (autocommitted DDL → a permanently half-reverted schema: `browse_category` alive without `uq_browse_category_slug`, `model_browse_category` already destroyed), and then states that with the `UPDATE` first this no longer holds here, because the `UPDATE` is DML and pysqlite opens an implicit transaction on the supported online path which the drops below share. The motivation for the `UPDATE` is unchanged and the statement itself is byte-identical.

**Deliberately not expanded:** I-4 (losslessness under an `AUTOCOMMIT` engine / offline `--sql`) and the deferred `upgrade()` non-atomic-DDL asymmetry are **not** addressed here — out of this pass's bounded scope by controller instruction. They remain open in §18.2.

### Verification executed by this pass

- `pytest tests/test_migration_0020.py -q` → **2 passed**.
- `pytest tests/test_migration_0020.py tests/test_browse_category_entity.py tests/test_orm_migration_parity.py tests/test_migration_0019.py tests/test_migration_0004.py -q` → **24 passed**, 1 pre-existing `SAWarning`. Per-file: **2 / 14 / 1 / 3 / 4** — the same 24 as §18.1, since this pass hardens an existing test rather than adding one. **No new test count; the expected API total therefore stays 1763.**
- `ruff format --check` + `ruff check` on the two touched Python files → **2 files already formatted**, **All checks passed!**, both rc=0.
- No `check-all`, no determinism run, no full suite, no Aider — outside this pass's scope; controller-owned.

### Files changed by this pass

| File | Change |
| --- | --- |
| `apps/api/tests/test_migration_0020.py` | FK-enforcement test: `model` + `model_browse_category` seed rows, four pre-downgrade preconditions, docstring note on the cross-table RESTRICT |
| `apps/api/migrations/versions/0020_browse_categories.py` | `downgrade()` rationale comment only — partial-autocommit sentence reframed as counterfactual. **No statement changed** |
| `_bmad-output/implementation-artifacts/49-1-…-migration.md` | §18.2 checkboxes (I-1/I-3/I-5/I-6 `[x]`, I-2/I-4 left open), §18.1 location wording, this §18.3 |

### Status and remaining gates

**Story 49.1 stays at `review`. `epic-49` stays at `in-progress`. `sprint-status.yaml` was not touched by this pass.** No commit, squash, push, merge, deploy or live-DB access was performed.

Still outstanding before this story can close:

1. **I-2 — AC-16 gate evidence is still not discharged, and this pass made it staler, not fresher.** `check-all-e49-1-final-controller.log` and `determinism-e49-1-final-controller.log` describe the pre-§18.3 code. **The determinism triple that §18.2 observed mid-flight never completed: it was controller-killed before finishing when this edit became necessary**, so there is no complete post-§18.1 determinism artifact either, and no log is cited by this story. Fresh `check-all` + a fresh determinism triple are required against the current tree; expected API count **1763 passed / 3 skipped**, unchanged by this pass and not asserted here.
2. **Fresh native re-review** of the updated diff (this pass is a repair, not a review; §18.2's REQUEST_CHANGES is discharged only on I-1/I-3/I-5/I-6).
3. **Independent Aider diff-review gate, re-run on the current diff.** `rc=4` = REQUEST_CHANGES under the standing rulebook. Not run here.
4. **I-4 plus the eleven §18 / three §18.2 `[Defer]` findings** remain open and controller-owned; still no `deferred-work.md`.

**Provenance — truthful.** This repair pass was performed by a **Claude Opus 5 agent session**. **No human has reviewed this code or this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable.** No subagents were used. No Aider review was executed or relayed in this pass. No commit, push, merge, deploy, live-DB or production access was performed.

## 18.4 Final native re-review record (`bmad-code-review`, post-§18.3)

**Verdict: APPROVE.** 0 critical, 0 important, 4 minor. **No blocking missing test remains.** The §18.2 REQUEST_CHANGES is discharged on I-1: the FK-enforcement test's cross-table blindness is closed, and closed *correctly* — the hardened fixture was independently mutation-proved in both directions, and the "fragile fixture" hypothesis was tested and **disproved**. Every original AC and the §18.1 `downgrade()` repair remain correct. **I-2 (fresh `check-all` + determinism triple) is an outstanding controller-run gate, not a code defect**, and is recorded as such below.

Native `bmad-code-review` (menu **CR**), 2026-07-26, Claude Opus 5 agent session, routed via native `bmad-help` → `_bmad/_config/bmad-help.csv` row `bmad-code-review` (phase `4-implementation`, `preceded-by: bmad-dev-story`). Customization resolved via `resolve_customization.py --skill .claude/skills/bmad-code-review --key workflow`: no team/user override (`activation_steps_prepend`/`activation_steps_append`/`on_complete` all empty); `persistent_facts` = `file:{project-root}/**/project-context.md` — no file matches that repo-root glob as written; `_bmad-output/project-context.md` exists and was loaded as foundational context, not via the glob.

Target: branch `feat/E49.1-browse-category-entities`, full uncommitted tracked + untracked working tree (9 files) against `baseline_commit` `d6299fa`. Review mode `full` (this document is the spec, §18.2/§18.3 read as triage history only — every verdict below is re-derived from code). Code diff under review: **990 lines**.

**Canonical parallel adversarial gate — all three layers ran in fresh independent contexts at this session's model capability; none failed, none returned empty. `failed_layers` is empty.** Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`), Acceptance Auditor (spec-vs-diff). Every layer finding was independently re-verified by this session before triage; severities below are this workflow's own, per step 3's instruction to disregard the layers' ratings.

### Focus verdict — I-1 is closed, and the fixture is not fragile

**Closed, mutation-proved by this session on a `/tmp` copy (the repo file was never modified):**

| Build (`/tmp/rv49`, `/tmp/rv49b`) | Seed | Result |
| --- | --- | --- |
| **mutant A** — `drop_table("browse_category")` moved *before* `drop_table("model_browse_category")` | shipped (repaired) seed | **RED — `1 failed, 1 passed`**, `FAILED test_migration_0020_downgrade_under_foreign_key_enforcement` |
| **mutant A** | pre-repair seed (parent/child only, assignment precondition removed) | **`2 passed`** — the I-1 blindness reproduced directly |
| production order (unmutated) | shipped seed | **`24 passed`** across all five touched files |

That triple is the exact proof I-1 asked for: the reversed drop order now fails, the shipped order passes, and the old seed demonstrably could not tell them apart. Independently corroborated by both hunter layers (Blind Hunter M1/M2/M9; the Edge Case Hunter's 10-state × 2-path × 2-pragma counterfactual matrix, in which "drop order reversed" fails on exactly the three states that carry join rows).

**Not fragile — the hypothesis was tested, not assumed.** The seed hard-codes the post-0019 `model` NOT NULL-without-default set (`id, slug, name_en, date_added, created_at, updated_at`), relies on `source`/`status` server defaults and on `rating`/`thumbnail_file_id` staying NULL (satisfying `ck_model_rating_range` with no `model_file` row). Both of those enumerations were verified exact against a migrated scratch DB. The Blind Hunter then simulated the specific drift that would matter — a probe `0021` adding a NOT NULL column to `model` — and **`test_migration_0020.py` passed unchanged**, because every traversal in the file is pinned to `command.upgrade(cfg, "0020_browse_categories")`, which freezes the `model` schema at that revision permanently. The revision-pinning discipline the file advertises is precisely what makes the raw INSERT durable. The Edge Case Hunter's independent conclusion agrees and adds the decisive property: the fixture **cannot silently disarm**, because four preconditions are asserted on the same connection that runs `downgrade()` — `PRAGMA foreign_keys == 1`, `count(*) WHERE parent_id IS NOT NULL == 1`, the assignment row `== 1`, and `PRAGMA foreign_key_check == []`. Any schema or insert drift therefore fails **loudly and locally**, and a broken fixture cannot masquerade as the assertion under test. The `uuid.uuid4().hex` and literal timestamp forms are incidental but harmless: the ids are only ever compared to each other, and `foreign_key_check` fails if they ever stop linking.

**The §18.1 repair itself remains correct and bounded.** The shipped `downgrade()` completes with `PRAGMA foreign_keys=ON` across every row state exercised by this session and the two layers: empty, single root, parent/child, 3-level chain, `parent_id = id` self-loop, A→B→A cycle, orphan `parent_id`, join rows present, and join rows referencing a soft-deleted model — on both the direct `Operations(MigrationContext.configure(...))` path and the online `command.downgrade` path, with `leftover=[]` in every cell. A `PRAGMA foreign_key_list` sweep of the full head schema re-confirms the only inbound FKs to the new tables are `browse_category.parent_id` and `model_browse_category.category_id`, with zero triggers and zero views, so there is no hidden FK path the `UPDATE` fails to disarm. `upgrade()` is byte-unaffected and still inserts zero rows. Removing only the `UPDATE` line still fails the test (`IntegrityError … [SQL: DROP TABLE browse_category]`), so the statement remains load-bearing.

**Executed independently by this session (read-only; tmpdir/in-memory scratch SQLite and `/tmp` repo copies only — no live DB, no production access, no repo file created, edited or deleted):**

- `pytest tests/test_migration_0020.py tests/test_browse_category_entity.py tests/test_orm_migration_parity.py tests/test_migration_0019.py tests/test_migration_0004.py -q` → **24 passed**, one pre-existing `model`/`model_file` `SAWarning`. Unchanged from §18.3, as expected — §18.3 hardened an existing test rather than adding one.
- The three-cell mutation matrix above, on two throwaway `/tmp` copies, both deleted afterwards.
- A third mutation (**mutant C**): the `UPDATE` moved from first to third position, still ahead of the `browse_category` drop → **`24 passed`**. This is what makes finding N-2 below real rather than theoretical.
- Gate-log freshness, at absolute paths: `check-all-e49-1-final-controller.log` mtime **09:29:04**, `determinism-e49-1-final-controller.log` mtime **09:49:17**, both **earlier** than the §18.3 edits (`tests/test_migration_0020.py` **09:51:44**, `migrations/versions/0020_browse_categories.py` **09:51:53**). The determinism log holds **3** `=== API RUN ===` headers but only **2** completed summaries and **no** `API_RC=/WEB_RC=` trailer — the controller-killed third run §18.3 describes. Confirmed by inspection, not inferred.
- Working-tree integrity: `git status --porcelain` is the same 9 entries before and after this pass; `HEAD` is still `d6299fa`.

**Per-AC result: AC-1 … AC-15 PASS on independent re-derivation. AC-16 is NOT discharged for the code under review** — not because anything broke it, but because no completed `check-all` + determinism artifact describes the current tree (I-2, below). An independent full-suite run of `apps/api` on the current tree by the Acceptance Auditor layer returned **1763 passed / 3 skipped**, matching §18.3's expected count — but that is a single suite run, not the 16-stage gate, and is recorded as corroboration only.

**The prepended `UPDATE` re-ruled from the AC text, not inherited from §18.2's dismissal.** AC-6 constrains `upgrade()` only, and `upgrade()` is byte-untouched (zero rows in both tables after upgrade, asserted in-test). AC-7's operative clauses all hold: both named indexes dropped, `model_browse_category` before `browse_category`, no `NotImplementedError`, rationale recorded. Binding constraint 10's "no destructive DDL" does not reach a DML statement that destroys strictly less than the `DROP TABLE`s AC-7 itself mandates on the same rows. §10's non-goals are untouched — not seed content, not a model assignment, not a live-DB action. And AC-7's headline property is *reversible*: without the `UPDATE`, `downgrade()` under FK enforcement aborts into a half-reverted schema, so the statement is what makes AC-7 true rather than nominal.

### Review Findings

Four minor findings, all documentation-accuracy. None violates an AC, none blocks the commit, and none is a missing test that would let a real defect ship.

- [x] [Review][Patch] **N-1. FIXED — the FK-enforcement test's docstring states the pre-fix hazard in the present tense, as if it were what the shipped body does** [`apps/api/tests/test_migration_0020.py:280-283`] — "…with a parent/child pair present: `DROP TABLE browse_category` then performs an implicit per-row delete and the self-referential `ON DELETE RESTRICT` fires on it, aborting the drop AFTER `uq_browse_category_slug` has already been dropped — a half-reverted schema." With the `UPDATE` in place that is false on both counts, and it contradicts the same docstring's own closing line (`:291-292`, "The proof is that the downgrade is COMPLETE") and the test's terminal assertions (`:367-371`). This is **exactly the I-3 defect class**: §18.3 reframed the claim as counterfactual in the migration comment but did not mirror the fix one file over. Raised independently by the Blind Hunter and the Acceptance Auditor. Unambiguous minimal fix: counterfactual framing ("*without* the leading `UPDATE`, `DROP TABLE browse_category` would …"). Severity low.
- [x] [Review][Patch] **N-2. FIXED — the `0020` module docstring never mentions that `downgrade()` now issues DML** [`apps/api/migrations/versions/0020_browse_categories.py:29-37`] — the header a future operator reads first still says only "0020 destroys nothing — it only creates two brand-new, initially empty tables, so dropping them again is a genuinely safe and complete rollback", with no reference to the `UPDATE … SET parent_id = NULL` that erases the whole hierarchy ahead of the drops. The substance is recorded in the in-function comment (`:113-131`) and the time-bound half of this claim is already ledgered (§18 line 492 `[Defer]`, §18.3 I-6), so this is residue rather than a new defect — but the docstring is where the claim is least qualified. Severity low.
- [x] [Review][Patch] **N-3. FIXED — `test_migration_0019.py`'s rewritten docstring is inexact for one of the two re-pinned assertions** [`apps/api/tests/test_migration_0019.py:10-12`] — "Both keep their original binding intent — only their **traversal target** moved." True of `test_downgrade_from_0019_raises_not_implemented`; `test_single_head_is_0020_browse_categories` (`:109-115`) performs no traversal at all — what moved is its expected head id. AC-10 and AC-11 both PASS on substance. Severity nit.
- [x] [Review][Defer] **N-4. MINOR — the incidental rollback-atomicity of `downgrade()` is positional and untested; this is the coverage face of the controller-deferred I-4** [`apps/api/migrations/versions/0020_browse_categories.py:120-133`] — the in-function comment's mechanism sentence is true only because the `UPDATE` is the **first** statement (DML ⇒ pysqlite opens an implicit transaction that the subsequent DDL shares). **Measured by this session (mutant C): moving the `UPDATE` to third position keeps all 24 tests green** while the property is gone — a later failure then autocommits a half-reverted schema with `alembic_version` still at `0020`. Corroborated by the Blind Hunter with an injected-failure probe (production order → all four objects and every `parent_id` survive; `UPDATE` moved → `browse_category` present, join table gone). No AC requires atomicity (AC-7 holds in the mutant too), no shipped path runs a downgrade (`infra/scripts/deploy.sh:148` runs `alembic upgrade head` only), and §18.2's **I-4 already ledgers this exact transaction dependency as open and controller-deferred**. Routed `defer` to stay consistent with that disposition rather than re-escalating it under a new name. Severity low-medium.

**New `[Defer]` findings (not previously ledgered) — flagged for the controller, not actionable inside 49.1:**

- [x] [Review][Defer] `hard_delete_model`'s forensic audit snapshot has no category count, so CASCADE-destroyed assignments will leave no audit record [`apps/api/app/modules/sot/admin_service.py:339-412` × the new FK at `apps/api/app/core/db/models/_entities.py:177-179`] — reproduced by the Edge Case Hunter: a model in 2 categories, hard-deleted via the service, leaves `before_json` counting only `file_count`/`link_count`/`note_count`/`print_count`/`tag_count` and zero mention of categories, while the join rows are gone. **Not fixable here** — §7 explicitly forbids touching `app/modules/**`, and the join table is empty until 49.2. Real from 49.2 onward. Severity medium (forward).
- [x] [Review][Defer] `inclusion_criterion` is the only monolingual human-text column on the entity [`apps/api/app/core/db/models/_entities.py:157`, `apps/api/migrations/versions/0020_browse_categories.py:65`] — every other prose column is an `_en`/`_pl` pair, and the eight governed categories this column exists to hold already have **Polish** names and criteria (`ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md:97-146`) on a pl-PL-primary product. **Spec-mandated** by AC-1 and `architecture.md:3289`, so the implementation is faithful; changing it is `bmad-correct-course` territory and is cheapest **now**, while both tables are still empty. Severity low-medium (forward, controller decision).
- [x] [Review][Defer] `test_migration_0020.py` asserts index **names** but never index **uniqueness**, and column **sets** but never column **types** [`apps/api/tests/test_migration_0020.py:143-149`, `:152`, `:236-250`] — mutation-proved: dropping `unique=True` from `op.create_index("uq_browse_category_slug", …)` is caught by `test_orm_migration_parity.py` and by **nothing** in this file; a `0020` declaring `slug` as `sa.Integer()` in *both* halves would pass. AC-13 requires neither, and coverage is not lost (the parity gate holds it) — it is misplaced relative to the file's own "structural proof" framing. Severity low.
- [x] [Review][Defer] `alembic upgrade head` fails on a dev DB whose schema came from `init_schema()` [`apps/api/migrations/versions/0020_browse_categories.py:57` — no `if_not_exists`] — reproduced: `OperationalError: table browse_category already exists`, `alembic_version` stuck at `0019_drop_category`. Dev-only (`app/main.py` skips `init_schema` when `environment == "production"`) and shared by every revision in the chain. Pre-existing class, not a 49.1 regression. Severity low.

**Re-confirmed `[Defer]` findings (already ledgered in §18 / §18.2; independently re-reproduced, none became a defect and none is caused by the §18.3 repair):** `position` server_default split between the Alembic and `create_all` paths (with the concrete 49.2 hazard: a raw seed omitting `position` works in prod, fails in dev/test); soft-deleted models retaining assignment rows so `RESTRICT` blocks a visibly-empty category; a non-empty `downgrade()` destroying real curated content once 49.2 seeds; `downgrade base` partially applying `0020` before hitting `0019`'s raise; `downgrade()` not being re-runnable from a half-reverted state; offline `--sql` emitting no transaction wrapper (I-4); `compare_metadata` blind to `ondelete` and server defaults; unindexed `browse_category.parent_id` (which also full-scans on every `RESTRICT` child check and on the repair's own `UPDATE`); writable-but-unremovable `parent_id` cycles; byte-exact slug uniqueness with no case/whitespace/length guard; tz-naive timestamps bypassing `UTCDateTime`; `updated_at` without `onupdate`; the hand-rolled entity-test engine; unclosed `sqlite3.connect` helpers; the index-parity guard passing vacuously for an absent table; `tag_group` still missing from that guard's `new_tables`; and the two §16 F-15 planning-artifact drifts. Also re-confirmed: the `upgrade()` non-atomic-DDL window, unrepaired and shared with `0018`/`0019`.

**I-2 — stated factually, as an outstanding gate rather than a code defect.** AC-16 is not discharged for the code under review. Both "final" controller logs predate the §18.3 edits by roughly two minutes (mtimes above), `check-all-e49-1-final-controller.log` is complete and green (16/16, `all green.`, `1763 passed / 3 skipped`) but describes the pre-§18.3 tree, and `determinism-e49-1-final-controller.log` never completed its third API run. **No log is cited by this story as AC-16 evidence, and this pass created none.** A fresh `check-all` plus a fresh determinism triple against the current tree are required; expected API count **1763 passed / 3 skipped**, unchanged by §18.3 and not asserted here. This is controller-owned and, per the instruction that invoked this pass, is explicitly **not** treated as an implementation defect.

**Dismissed as false, spec-mandated, or already handled (recorded so they are not re-raised):**

1. *"The head-name assertion lives in a file named for `0019`, so a future author will not find it"* — **spec-mandated.** AC-10 / T1.2 / §6 F-1 require editing that existing assertion in place; §18 dismissal #2 already covered the relocation argument. The Blind Hunter's own probe confirms it fires correctly when a `0021` appears.
2. *"`test_upgrade_head_drops_category_schema` still traverses to `head`, contradicting `test_migration_0020.py`'s pin-everything discipline"* — **spec-mandated.** T1.4 and §6 F-3 explicitly require leaving it untouched; §18 dismissal #3.
3. *"The `test_migration_0004.py` extension buys no new detection, since both drift mutations also fail the parity gate"* — **true but not a defect.** AC-14 mandates the extension; both paths derive from the same `SQLModel.metadata`, so the redundancy is inherent. Recorded honestly, not raised.
4. *"`position` accepts negatives and duplicates with no tie-breaker, so browse ordering is non-deterministic"* — **handled downstream**, §18 dismissal #4: Story 49.3 orders by `(position, slug)`.
5. *"`parent_id` cycles are writable and then undeletable"* — **already ledgered** as a 49.5 deferral in §18; re-reproduced, not new. The degenerate `parent_id == id` self-loop is both insertable and deletable, so it never arms the FK.
6. *"`drop_index` before `drop_table` is dead DDL"* — **AC-7 mandates dropping both indexes**, and `0018` shares the pattern; its contribution to the unrecoverable half-revert state is the already-ledgered "`downgrade()` is not re-runnable" finding.
7. *"AC-1's `position: int = 0` diverges from the shipped `Field(default=0)`"* — **already recorded as a non-finding** in §18; semantically identical and the `TagGroup.position` shape §6 F-10 cites as the `compare_metadata`-safe precedent.

**Source-comment accuracy re-audited.** Every factual claim in the change set's comments and docstrings was re-checked against the code it names, and all are TRUE as shipped **except N-1 and N-3 above**: `0004:21-30` really is the `category` self-FK `create_table`; `0004:142-158` really is the `model_tag` composite-PK idiom plus its reverse index; `migrations/env.py` really does use `engine_from_config` and never issues the FK pragma (the app binds `PRAGMA foreign_keys = ON` per-engine at `app/core/db/session.py:17-19`, so it cannot leak into Alembic's engine); the corrected `_entities.py` `__table_args__` comment (direction "above" and the name-not-object-count reason) is right, re-probed on the resolved runtime — `Tag.__table__.indexes == [('ix_tag_slug', unique=True, ['slug'])]` with constraints holding only PK + FK; the corrected `test_browse_category_entity.py` vacuity paragraph is right (deleting the pragma listener yields loud failures, not vacuous passes); and `test_migration_0020.py`'s "fixture mirrors `test_migration_0018.py` verbatim" claim was compared line-for-line and holds. Production really is SQLite (`app/core/config.py:31`), so the whole FK analysis is production-relevant rather than test-only.

**Record truthfulness.** No fabricated or implied human sign-off exists anywhere in this document. `Status: review` and `epic-49: in-progress` are both intact and were not touched by this pass. T6.3 remains the single unchecked task box and is correctly justified — `HEAD` is still `d6299fa` and no commit exists. §18.1's Aider verdict is still correctly labelled as relayed, not executed.

**Disclosed deviations of this pass from the base `bmad-code-review` workflow:**

1. **Step 1's checkpoint HALT was not taken.** The operator instruction resolved the Tier-1 target unambiguously (branch, spec, tracked + untracked scope) and required a consolidated verdict in one pass.
2. **Step 4 §5's patch HALT was not taken and no patch was applied.** This run is **review-only** by explicit operator instruction — no implementation or test file was modified, created or deleted. The three `patch` findings (N-1, N-2, N-3) are left as unchecked action items, which is the workflow's option 2 outcome.
3. **Step 4 §6 (status update and sprint sync) was deliberately NOT executed.** The base workflow would set this story to `done` on an APPROVE verdict and sync `sprint-status.yaml`. By explicit operator instruction, **Story 49.1 stays at `review` and `epic-49` stays at `in-progress`; neither was marked `done`.** No line of `sprint-status.yaml` was touched by this pass.
4. **Step 4 §7's next-steps HALT was not taken** — the instruction that invoked this run required a returned verdict, not an interactive menu.
5. **No `deferred-work.md` entry was written.** Step 4 §2 would append the `defer` findings to `{implementation_artifacts}/deferred-work.md`; that file still does not exist and creating a new ledger artifact remains outside this run's authorization. The `defer` findings are recorded here in full.
6. **Subagents were used** — the operator instruction explicitly required the canonical three-layer parallel gate in fresh independent contexts.

**Provenance — truthful.** This final re-review was performed by a **Claude Opus 5 agent session** and by three subagent review layers. **No human has reviewed this code or this document. No Ezop sign-off and no Laura sign-off is recorded, implied, or inheritable from this record.** No commit, squash, push, merge, deploy, live-DB access or production access was performed. All mutation experiments ran on `/tmp` copies, since deleted; the repo working tree is byte-identical to its state at the start of this pass. This pass ran **no Aider review** — the independent Aider diff-review gate on the current diff is separate and still outstanding.

### Status and remaining gates

**Story 49.1 stays at `review`. `epic-49` stays at `in-progress`. `sprint-status.yaml` was not touched by this pass.** No commit, squash, push, merge or deploy was performed.

Still outstanding before this story can close — **none of them a code defect**:

1. **I-2 — fresh `check-all` (16/16) + a completed determinism triple** against the current tree, then cite both logs. Expected API count `1763 passed / 3 skipped`. Controller-owned.
2. **Independent Aider diff-review gate, re-run on the current diff.** `rc=4` = REQUEST_CHANGES under the standing rulebook. Not run here.
3. **The three minor `patch` findings (N-1, N-2, N-3)** — documentation-accuracy only; the controller may fold them into the commit or ledger them.
4. **I-4, N-4 and the re-confirmed `[Defer]` set, plus the two §16 F-15 planning drifts** — open and controller-owned; still no `deferred-work.md`.

## 19. Controller final disposition

**Disposition: DONE — Laura/controller, 2026-07-26.** This is a controller decision under Ezop's standing Initiative 26 authorization, not an Ezop signature or a claim that Ezop personally reviewed the code.

- Native BMAD final re-review: **APPROVE**, 0 Critical, 0 Important, no blocking missing test (Blind Hunter + Edge Case Hunter + Acceptance Auditor, fresh contexts).
- Independent Aider final re-review: **APPROVE**, 0 Critical, 0 Important, no missing tests.
- Final merge gate: `.hermes/run-logs/check-all-e49-1-final2-controller.log` → **16/16**, API **1763 passed / 3 skipped**, Web Vitest **136 files / 785 tests**, visual **536 passed / 32 expected skips**, terminal `all green.`
- Final determinism: `.hermes/run-logs/determinism-e49-1-final2-controller.log` → API **3× 1763 passed / 3 skipped / 2014 warnings**, Web **3× 136 files / 785 tests**, trailer `API_RC=0 WEB_RC=0`.
- Frozen-tree evidence: `.hermes/run-logs/e49-1-final2-manifest.log` records baseline `d6299fa`, identical before/after status and SHA-256 for all nine story files, and `FINAL_MANIFEST_STABLE`.
- N-1/N-2/N-3 were folded in as documentation-only corrections after native approval; no SQL, schema, ORM or test behaviour changed. Native `git diff --check` is clean.
- Deferred findings remain explicitly ledgered in §18/§18.2/§18.4 and are routed to their owning future stories or a separate correct-course pass; none blocks Story 49.1.

The story branch contains one atomic implementation commit. No live database was accessed during development or review. Merge, push and deployment are controller-owned actions performed after this record is committed; their external SHAs and production evidence belong in Git/deploy logs rather than in this self-referential artifact.
