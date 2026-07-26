# Story 49.1: `BrowseCategory` + `ModelBrowseCategory` entities and Alembic `0020_browse_categories` (atomic)

Status: ready-for-dev

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

- [ ] **T1.1 (RED, evidence-first).** Before any new file exists, run `pytest tests/test_migration_0019.py -q` from `apps/api/` and record that all three tests currently pass at HEAD `47fe971`. This is the baseline the story must not silently break.
- [ ] **T1.2.** Edit `tests/test_migration_0019.py::test_single_head_is_0019_drop_category` → assert `script.get_heads() == ["0020_browse_categories"]`, and rename it to `test_single_head_is_0020_browse_categories`. Update the module docstring's "exactly one head named `0019_drop_category`" sentence. **Do not** relax it to a length check — the assertion's value is that it names the head.
- [ ] **T1.3.** Edit `test_downgrade_from_head_raises_not_implemented` → `command.upgrade(cfg, "0019_drop_category")` then `command.downgrade(cfg, "-1")`, still expecting `NotImplementedError`; rename to `test_downgrade_from_0019_raises_not_implemented` and add a comment citing this story: `0019` is no longer head, and a `-1` step from `0020` would exercise `0020.downgrade()` (implemented), turning a real forward-only proof into a false negative. This is the same head-pinning adjustment Story 47.5's `d11` applied to the `test_migration_0004/0005/0009/0012/0014` family.
- [ ] **T1.4 (RED confirmed).** Re-run `pytest tests/test_migration_0019.py -q`. `test_single_head_is_0020_browse_categories` must now **fail** with `AssertionError: ['0019_drop_category'] != ['0020_browse_categories']`. Paste it. Leave `test_upgrade_head_drops_category_schema` untouched — its assertions are exact-name set membership (`"category" not in objs`), and `browse_category` is a distinct name, so it stays green before and after.

### T2 — RED→GREEN: ORM entities (AC-1, AC-2, AC-3, AC-4)

- [ ] **T2.1 (RED).** Create `apps/api/tests/test_browse_category_entity.py` following `test_tag_group_entity.py:18-32` verbatim: in-memory SQLite engine, an explicit `event.listens_for(e, "connect")` handler running `PRAGMA foreign_keys=ON` (SQLite does **not** enforce `ON DELETE` without it), then `SQLModel.metadata.create_all(e)`. Write the AC-12 (a)–(g) assertions. Run it: it must fail at import (`ImportError: cannot import name 'BrowseCategory'`). Paste it.
- [ ] **T2.2 (GREEN).** Add `BrowseCategory` and `ModelBrowseCategory` to `_entities.py`, appended after `ModelTag` (or in the file's existing reading order — do not reorder existing classes). Use `uuid_fk(...)` for all three FK columns. `parent_id` self-FK: `parent_id: uuid.UUID | None = Field(default=None, sa_column=uuid_fk("browse_category.id", ondelete="RESTRICT", nullable=True))`. **Two precedents, both in-repo, both stronger than a guess:** the migration-side self-referential `category` table in `0004:21-28` proves it works on SQLite; and the *ORM*-side `class Category` that Story 47.5 deleted (recoverable with `git show 98246d7^:apps/api/app/core/db/models/_entities.py`) used this exact `Field(default=None, sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=True))` line and was `compare_metadata`-green for its whole life. Copy that line's shape; do **not** resurrect the `Category*` identifier or its `uq_category_root_slug` partial index — `browse_category.slug` is globally unique (AC-1), not unique-per-parent.
- [ ] **T2.3 (GREEN).** Extend `models/__init__.py`: add both names to the `from ._entities import (...)` block and to `__all__`, preserving alphabetical order.
- [ ] **T2.4.** Re-run `pytest tests/test_browse_category_entity.py -q` → all green. Then run `pytest tests/test_orm_migration_parity.py -q` → it must now **FAIL** with a diff reporting two `add_table` entries. **This failure is the required proof of atomicity** (`ORM metadata and migrated schema differ: [('add_table', Table('browse_category', ...)), ('add_table', Table('model_browse_category', ...))]`). Paste it verbatim into the Dev Agent Record. Do not commit here.

### T3 — RED→GREEN: migration `0020_browse_categories` (AC-5, AC-6, AC-7, AC-8, AC-13)

- [ ] **T3.1 (RED).** Create `apps/api/tests/test_migration_0020.py` with the AC-13 assertions, mirroring `test_migration_0018.py` — same `_alembic_cfg` / `_objects` / `_columns` / `_foreign_keys` helpers and the same `_round_trip_db` fixture that overrides `DATABASE_URL` (`env.py:12` reads `get_settings().database_url` and **ignores** the URL set on the Alembic `Config`, so the env var is the only knob that works). Pin every traversal to `0020_browse_categories` and `0019_drop_category` — never `"head"` for the downgrade leg. Run it: must fail (`Can't locate revision identified by '0020_browse_categories'`). Paste it.
- [ ] **T3.2 (GREEN).** Create `apps/api/migrations/versions/0020_browse_categories.py`. Docstring states: Initiative 26 / Epic 49 / Story 49.1, Decision AX + AZ, additive **and reversible**, ships atomically with the ORM entities, no seed content (41.3 precedent), no table name reused (`0019` dropped `category`; this creates `browse_category`), and the explicit rationale for the implemented `downgrade()`.
- [ ] **T3.3 (GREEN).** `upgrade()` — `op.create_table("browse_category", ...)` with `sa.Uuid(as_uuid=True)` PK, `sa.String()` label/description/criterion columns, `sa.Integer(nullable=False, server_default="0")` for `position`, `sa.Column("parent_id", sa.Uuid(as_uuid=True), sa.ForeignKey("browse_category.id", ondelete="RESTRICT"), nullable=True)`, and `sa.DateTime(), nullable=False` timestamps; then `op.create_index("uq_browse_category_slug", "browse_category", ["slug"], unique=True)`; then `op.create_table("model_browse_category", ...)` with both FK columns `primary_key=True` (the `0004:142-157` `model_tag` idiom); then `op.create_index("ix_model_browse_category_cat_model", "model_browse_category", ["category_id", "model_id"])`.
- [ ] **T3.4 (GREEN).** `downgrade()` — `op.drop_index("ix_model_browse_category_cat_model", table_name="model_browse_category")`, `op.drop_table("model_browse_category")`, `op.drop_index("uq_browse_category_slug", table_name="browse_category")`, `op.drop_table("browse_category")`. Child table first.
- [ ] **T3.5 (GREEN).** `pytest tests/test_migration_0020.py -q` → green. `pytest tests/test_migration_0019.py -q` → all three green (T1's edits now hold). `pytest tests/test_orm_migration_parity.py -q` → **green, empty diff** (AC-9 satisfied). Paste all three.

### T4 — GREEN: index-parity coverage extension (AC-14)

- [ ] **T4.1 (RED).** In `tests/test_migration_0004.py::test_alembic_and_sqlmodel_emit_equivalent_index_sets`, add `"browse_category"` and `"model_browse_category"` to the `new_tables` list (`:166-174`). Run it. If it fails, the ORM and the migration disagree on index naming — that is exactly what AC-3 exists to prevent, and the fix belongs in the ORM/migration, never in the test's expectation.
- [ ] **T4.2.** Confirm `test_alembic_upgrade_head_creates_all_new_tables` (`:51-81`) still passes without edit — it computes `expected - names`, a subset check, so new tables at head do not break it. If it needed editing, something is wrong; stop and report.

### T5 — Non-regression sweep (AC-15)

- [ ] **T5.1.** `pytest -q` in `apps/api/` — full suite green. Explicitly confirm zero edits were needed in `test_db_entity_tables.py`, `test_tag_group_entity.py`, `test_sot_models_list.py`, `test_sot_models_detail.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_sot_admin_tags.py`, `test_sot_admin_tag_groups.py`, `test_route_enforcement_gate.py`, `test_openapi_agent_surface.py`, `test_runbook_openapi_consistency.py`, `test_migration_0004.py` (beyond T4.1), `test_migration_0005/0009/0012/0014.py`, `test_2fa_schema.py`.
- [ ] **T5.2.** `pytest -q` in `workers/render/` — green. The worker imports shared entities from `app.core.db.models` via the editable `portal-api` dep; adding classes is additive, but prove it rather than assume it.
- [ ] **T5.3.** `git diff --stat` — assert the changed-file set matches §7 **exactly**. Any extra file is scope creep and must be justified or reverted.
- [ ] **T5.4.** `ruff format` + `ruff check --fix` in `apps/api/` — clean.

### T6 — Merge gate (AC-16)

- [ ] **T6.1.** `infra/scripts/check-all.sh` → **16/16 stages passed**, no stage skipped. Record the log filename and the exact HEAD + dirty-state it ran against (standing epic:47 evidence-provenance action item).
- [ ] **T6.2.** Determinism: 3× consecutive `pytest` (apps/api) and `vitest` (apps/web) runs with **identical** pass counts. Record the triple.
- [ ] **T6.3.** Squash into **one commit** on one story branch. Suggested subject: `feat(api): add browse category entities and 0020 migration`. Body records the atomicity rationale and the two re-pinned `test_migration_0019` assertions.
- [ ] **T6.4.** No `baseline-reviewed:` line is required — this commit stages **zero** `apps/web/tests/visual/__snapshots__/**/*.png` and adds **zero** `apps/web/src/ui/*.tsx`, so neither husky hook (`_check-baseline-review.mjs`, `_check-visual-coverage.mjs`) fires. Do not pre-fill a sign-off line.

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

_(not yet implemented — no dev session has run)_

### Debug Log References

_(empty — T2.4 and T3.1/T3.5 failure/pass output goes here)_

### Completion Notes List

_(empty)_

### File List

_(empty — to be filled by the dev session and reconciled against §7)_

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
