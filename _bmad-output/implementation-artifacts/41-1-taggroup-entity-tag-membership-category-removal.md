---
baseline_commit: 49fd86ebbdb11a0b8c8e403f3cff88b87fcc8edc
---

# Story 41.1: `TagGroup` entity + `Tag` group membership (additive ORM foundation)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a catalog platform maintainer,
I want a first-class `TagGroup` entity and nullable group membership on `Tag` added to the ORM **additively**,
so that downstream migration (41.2) and API work (E42) have a stable facet-tag data contract to build on — without breaking the currently-green backend.

## Acceptance Criteria

1. **`TagGroup` entity added** to `apps/api/app/core/db/models/_entities.py`, table `tag_group`, fields: `id` (uuid PK, `default_factory=uuid.uuid4`), `slug` (str, unique), `name_en` (str), `name_pl` (str | None = None), `position` (int, default `0`), `created_at`/`updated_at` (`default_factory=_now_utc`). The `slug` unique index is declared with an **explicit name `uq_tag_group_slug`** via `__table_args__` (not `Field(index=True)`), so the ORM index name matches the migration 41.2 will create.
2. **`Tag` amended** (same file): add `group_id: uuid.UUID | None` — nullable FK → `tag_group.id`, `ondelete="SET NULL"`, built with the `uuid_fk(...)` helper (no `index=True`, to match the 0018 sketch which adds the column + FK but no index); add `group_position: int = 0`. All existing `Tag` fields/behavior unchanged.
3. **`TagGroup` re-exported** from `apps/api/app/core/db/models/__init__.py`: added to the `from ._entities import (...)` block and to `__all__` (alphabetical placement), matching the existing pattern for `Tag`, `Category`, etc.
4. **`Category` and `Model.category_id` remain untouched.** No removal in this story. No file that references `Category`, `category_id`, or `category_ids` is modified (backend modules or test fixtures). Removal is deferred and coupled to the E42 backend cut-over — see **Dev Notes → Sequencing determination**.
5. **No Alembic migration is added in this story.** Migration `0018_facet_tags_drop_category` is owned by story 41.2. In tests/dev the new table + columns appear automatically because schema is built by `init_schema()` → `SQLModel.metadata.create_all()` (not Alembic).
6. **Backend suite is green, 3× consecutive identical pass counts** (NFR25-DETERMINISM-1), plus `ruff check` + `ruff format` clean. No existing `Tag`/`Category`/`Model` test regresses.
7. **A focused entity test** (new `apps/api/tests/test_tag_group_entity.py`) asserts: a `TagGroup` row persists and round-trips; a `Tag` with `group_id=None` persists (groupless allowed); a `Tag` linked to a group resolves it; deleting the group sets the surviving `Tag.group_id` back to `NULL` (SET NULL behavior). `group_position` defaults to `0`.

## Tasks / Subtasks

- [x] Task 1 — Add `TagGroup` entity (AC: #1)
  - [x] Insert `class TagGroup(SQLModel, table=True)` in `_entities.py`, placed just before `class Tag` (keeps the tag cluster together; FK targets resolve by table-name string regardless of class order).
  - [x] Fields exactly as AC #1. For `slug`, use `__table_args__ = (Index("uq_tag_group_slug", "slug", unique=True),)` following the `Category` explicit-index precedent (`_entities.py:37-46`) — do **not** use `slug: str = Field(unique=True, index=True)` (that yields the auto name `ix_tag_group_slug`, which would drift from the 41.2 migration).
- [x] Task 2 — Amend `Tag` with group membership (AC: #2)
  - [x] Add `group_id: uuid.UUID | None = Field(default=None, sa_column=uuid_fk("tag_group.id", ondelete="SET NULL", nullable=True))` — mirror the `Model.thumbnail_file_id` nullable-SET NULL pattern (`_entities.py:95-98`). No `index=True`.
  - [x] Add `group_position: int = Field(default=0)`.
- [x] Task 3 — Export `TagGroup` (AC: #3)
  - [x] Add `TagGroup` to the `from ._entities import (...)` tuple and to `__all__` in `apps/api/app/core/db/models/__init__.py` (alphabetical).
- [x] Task 4 — Entity test (AC: #7)
  - [x] New `apps/api/tests/test_tag_group_entity.py`. Conftest exposes no reusable `session` fixture, so the test follows the self-contained direct-model-construction style of `test_refresh_token_model.py` (local in-memory SQLite engine from `SQLModel.metadata.create_all`, with `PRAGMA foreign_keys=ON` so SET NULL is actually exercised).
  - [x] Assert: persist `TagGroup(slug=..., name_en=...)`; persist `Tag(slug=..., name_en=..., group_id=None)`; persist `Tag(..., group_id=group.id)` and read back; delete the group + commit and confirm the linked tag's `group_id` is `NULL`; `group_position == 0` by default.
- [x] Task 5 — Verify (AC: #5, #6)
  - [x] Confirm **no** file under `apps/api/migrations/versions/` is added (41.2 owns 0018).
  - [x] `ruff check --fix` + `ruff format` on `apps/api`.
  - [x] Run the backend suite 3× and confirm identical, all-green pass counts.

## Dev Notes

### Scope is deliberately ADDITIVE-ONLY — do not remove `Category`/`category_id` in this story

This is the single most important guardrail. The epic sketch title says "Category removal," but **removing `Category` or `Model.category_id` in isolation is impossible without breaking the green-before-merge gate (NFR25-DETERMINISM-1)** — verified against the code:

- Test/dev schema is built from the **ORM** via `init_schema()` → `SQLModel.metadata.create_all()` (`apps/api/app/core/db/session.py:39`; project-context "Schema ownership"). So adding `TagGroup`/`Tag.group_id` is immediately live in tests **with no migration**; but removing `Category` from the ORM breaks any module that imports it — at **import time**, failing pytest *collection* for the whole suite.
- `Category` / `Model.category_id` are referenced live across the backend (non-slicer — the `slicer/*` "category" hits are `reason_category`/warning-code strings, unrelated, per SCP §2.4.2):
  - `apps/api/app/modules/share/router.py:16,144` — `from ...models import (Category, ...)` + `select(Category).where(Category.id == model.category_id)`; emitted at `:228` as `ShareModelView.category` (`share/models.py:40`).
  - `apps/api/app/modules/sot/service.py` — `list_categories_tree`, `Model.category_id` filter (`:97,99,168`).
  - `apps/api/app/modules/sot/admin_service.py` — `create/update/delete_category`, `_would_cycle`, model create/patch validate `category_id`.
  - `apps/api/app/modules/sot/router.py` / `admin_router.py` — `/categories` endpoints + `CategorySummary`/`CategoryTree` schemas.
  - Dozens of **test fixtures** build `Category(...)` and pass `category_id=` when constructing `Model` (e.g. `test_sot_admin_models.py`, `test_ratelimit_share_cap.py`, `test_share_member_router.py`, `test_admin_render_sot.py`, `test_sot_model_files.py`, `test_sot_admin_external_links.py`). `Model.category_id` is currently `NOT NULL`, so those fixtures require it.

Removing the entity would force editing ~8 app modules + dozens of test fixtures in one story — that is exactly the work E42 (42.1 filter, 42.3 category-endpoint removal, 42.5 model create/patch + share DTO) decomposes into. Pulling it into 41.1 would swallow E42 and blur the epic. **Therefore 41.1 = additive only; the removal lands atomically with the E42 backend cut-over + migration.** Files listed above must NOT be touched here.

### No migration in this story

41.1 is ORM-only. Migration `0018_facet_tags_drop_category` is story 41.2's deliverable. Tests stay green because `init_schema` (dev/test path, `environment != "production"`) rebuilds the schema from the ORM. Do not add anything under `apps/api/migrations/versions/`. (Production schema is Alembic-owned — that's 41.2's concern.)

### Exact patterns to reuse (do not invent)

- **Explicit-named unique index** (for `TagGroup.slug`) — copy the `Category` precedent, `_entities.py:37-46`, which names its index explicitly *specifically so the ORM name matches the Alembic migration*. Use `Index("uq_tag_group_slug", "slug", unique=True)` in `__table_args__`. The 41.2 sketch creates exactly `op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)` (SCP §4.2) — names must match or the future `test_migration_0018` schema-parity check drifts.
- **Nullable SET NULL FK** (for `Tag.group_id`) — copy `Model.thumbnail_file_id` (`_entities.py:95-98`) / `ModelPrint.photo_file_id` (`:149-152`): `Field(default=None, sa_column=uuid_fk("tag_group.id", ondelete="SET NULL", nullable=True))`. The `uuid_fk` helper (`_helpers.py`) centralizes the `(sa_uuid_type, ForeignKey, nullable, index, primary_key)` shape — pass `nullable=True`, leave `index` at its `False` default.
- **Timestamps** — `created_at`/`updated_at: datetime.datetime = Field(default_factory=_now_utc)` exactly like every other entity in the file.
- **`__init__.py` re-export contract** — the package docstring notes historical `from app.core.db.models import Category, ...` imports must keep working; add `TagGroup` to both the import tuple and `__all__`.

### Field shape notes

- `position` / `group_position`: use `Field(default=0)`. The SCP entity sketch writes `position: int`; defaulting to `0` matches the migration's `server_default="0"` (SCP §4.2) and keeps test fixtures ergonomic (no need to pass it). `group_position: int = 0` is the epic's own spelling.
- `name_pl: str | None = None` (bilingual-optional, same as `Tag.name_pl`/`Category.name_pl`).
- Class placement: put `TagGroup` immediately above `class Tag`. SQLAlchemy resolves the string FK target `"tag_group.id"` by table name at mapper-configure time, so definition order does not affect correctness — this is purely for readability.

### Testing standards

- Backend pytest, `asyncio_mode = "auto"`; auto-fixtures in `apps/api/tests/conftest.py` give a tmp-SQLite `_isolated_db` initialized via `init_schema`, and mock arq (no real Redis/network). Use the provided `session` fixture; construct models directly (this is an entity test, not an HTTP test — no `TestClient`/login needed).
- New test file: `apps/api/tests/test_tag_group_entity.py` (mirrors `test_<area>.py` convention).
- Determinism: run the suite 3× and confirm identical green counts before considering the story done (NFR25-DETERMINISM-1). `ruff check` + `ruff format` must be clean (`E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312).

### Project Structure Notes

- Files to create/modify (exhaustive for this story):
  - **Modify** `apps/api/app/core/db/models/_entities.py` — add `TagGroup`, amend `Tag`.
  - **Modify** `apps/api/app/core/db/models/__init__.py` — export `TagGroup`.
  - **Create** `apps/api/tests/test_tag_group_entity.py`.
- Files that must **NOT** change in this story (they belong to E42 / the coupled removal): `share/router.py`, `share/models.py`, `sot/router.py`, `sot/service.py`, `sot/schemas.py`, `sot/admin_router.py`, `sot/admin_service.py`, `sot/admin_schemas.py`, and every existing test that constructs `Category`/`category_id`.
- No frontend changes (E43+ owns `api-types`/hooks/UI).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 41.1 — `TagGroup` entity + `Tag` group membership + `Category` removal (FR25-TAX-1)]
- [Source: _bmad-output/planning-artifacts/epics.md#Requirements Inventory] — FR25-TAX-1 (E41: 41.1, 41.2); NFR25-DETERMINISM-1 (3× green before merge).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md#4.2 Architecture amendment] — entity shapes + migration 0018 sketch (additive DDL + destructive DDL) + Architecture Decision AV.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md#2.4] — diligence findings: share/Category coupling (§2.4.1), slicer "category" false-positive (§2.4.2).
- [Source: apps/api/app/core/db/models/_entities.py:29-69] — current `Category` + `Tag`; `:37-46` explicit-index precedent; `:85-98` FK patterns.
- [Source: apps/api/app/core/db/models/_helpers.py] — `uuid_fk`, `_now_utc`.
- [Source: apps/api/app/core/db/models/__init__.py] — re-export + `__all__` contract.
- [Source: apps/api/app/core/db/session.py:39] — `init_schema` = `SQLModel.metadata.create_all()` (test/dev schema source).
- [Source: _bmad-output/project-context.md#FastAPI (backend)] — "Schema ownership: production schema owned by Alembic; adding tables = new migration" (satisfied by 41.2).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (bmad-dev-story workflow)

### Debug Log References

- New entity test initially failed with `FOREIGN KEY constraint failed` on the two tests that link a `Tag` to a `TagGroup` in a single session. Root cause was test-construction, not the model: with no ORM `relationship()` declared, SQLAlchemy's unit-of-work does not order the `Tag` insert after the `TagGroup` insert, so the FK child row was written before its parent while `PRAGMA foreign_keys=ON`. Fixed by committing the `TagGroup` before adding the dependent `Tag` (realistic ordering). Model definition unchanged.

### Completion Notes List

- Implemented **additive-only** per the story's central guardrail: `TagGroup` entity + `Tag.group_id`/`group_position` added; `Category`, `Model.category_id`, and all E42-owned modules/fixtures left untouched (verified via `git diff` — no `category` additions, only 3 files changed).
- `TagGroup.slug` uniqueness declared via explicit `Index("uq_tag_group_slug", "slug", unique=True)` in `__table_args__` (not `Field(index=True)`) so the ORM index name matches the migration 41.2 will create.
- `Tag.group_id` uses `uuid_fk("tag_group.id", ondelete="SET NULL", nullable=True)` with `index` left at its `False` default — matches the 0018 sketch (column + FK, no index).
- No Alembic migration added (AC #5): `apps/api/migrations/versions/` is untouched; new table/columns appear in tests via `init_schema()` → `create_all()`.
- Determinism (NFR25-DETERMINISM-1): full backend suite run 3× consecutively — **1669 passed, 3 skipped** each time. `ruff check` + `ruff format` clean (no changes to the new code).

### File List

- Modified: `apps/api/app/core/db/models/_entities.py`
- Modified: `apps/api/app/core/db/models/__init__.py`
- Created: `apps/api/tests/test_tag_group_entity.py`

## Change Log

- 2026-07-18 — Implemented additive ORM foundation: added `TagGroup` entity + `Tag.group_id`/`group_position`, re-exported `TagGroup`, added focused entity test. Backend suite 3× green (1669 passed, 3 skipped); ruff clean. Status → review.

## Review Findings

_Code review 2026-07-18 (bmad-code-review). 3 layers: Blind Hunter, Edge Case Hunter, Acceptance Auditor (PASS — all 7 AC + additive-only guardrail satisfied). 1 patch, 2 deferred, 10 dismissed as noise/spec-mandated/repo-convention. 1 decision-needed (production deploy coupling vs. migration 0018) reviewed and dismissed by operator — considered adequately documented as Question #2._

- [x] [Review][Patch] `tag_group.slug` uniqueness is never tested — FIXED 2026-07-18: added `test_tag_group_slug_is_unique` asserting `IntegrityError` on a duplicate slug (6 passed, ruff clean) [apps/api/tests/test_tag_group_entity.py]
- [x] [Review][Defer] No ORM↔migration drift guard — the inline "0018 will create `uq_tag_group_slug`" promise is unverified by tooling (no `compare_metadata`/autogenerate test); 41.2 owns the migration + schema-parity test [apps/api/tests/] — deferred, pre-existing
- [x] [Review][Defer] `Tag.group_id` FK is unindexed — spec-mandated for 41.1 (AC #2, matches the 0018 sketch: column + FK, no index); revisit when E42 adds group-scoped tag queries [apps/api/app/core/db/models/_entities.py:87] — deferred, pre-existing

---

## Story Creation Questions / Decisions for Operator

1. **Sequencing decision made in this story (please confirm):** `41-1` is scoped **additive-only** — it adds `TagGroup` + `Tag.group_id`/`group_position` but does **NOT** remove `Category`/`Model.category_id`, despite the sprint-status key naming "category-removal." Rationale: the removal cannot pass the green-before-merge gate in isolation (breaks pytest collection via ~8 backend imports + dozens of test fixtures), and would swallow E42's 42.1/42.3/42.5. The `Category`/`category_id` removal should land atomically with the E42 backend cut-over.
2. **Downstream coupling to flag for 41.2 / E42 planning (not a 41.1 blocker):** migration `0018` as sketched mixes **additive** DDL (create `tag_group`, add `tag.group_id`/`group_position`) with **destructive** DDL (drop `model.category_id` + `category` table). The destructive half cannot run in production until the ORM + all app references to `Category` are gone (else prod queries break — prod uses Alembic, not `create_all`). Consider splitting `0018` into an additive migration (lands with E41) and a destructive one (lands atomically at the E42 cut-over), or defining a single atomic "category retirement" story at the end of E42. Surface at 41.2 create-story.
