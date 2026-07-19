# Story 42.1: `GET /api/models` facet filtering

Status: review

<!-- Validated 2026-07-19 via bmad-create-story:validate — VERDICT: PASS. All three prior open questions resolved into ratified decisions against approved sources (FR25-FILT-1/2, mockup 04/08B/08D, HANDOFF §3/§5). See "## Validation Record" at the end. No dev-start open questions remain. -->

## Story

As a **catalog user (admin / member / agent)**,
I want **`GET /api/models` to filter by facet tags (AND-between-groups / OR-within-group, with an all/any override) and to surface untagged models**,
so that **the catalog can be browsed by the new facet taxonomy and the post-cutover "everything is untagged" state can be triaged — with the retired `category` filter gone from the query contract**.

Traces: **FR25-FILT-1**, **FR25-FILT-2** (Epic E42; SCP `sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md`).

## Acceptance Criteria

1. **`category_ids` is removed from the `GET /api/models` filter contract.** The `category_ids` query parameter no longer exists on the endpoint (removed from `get_models` in `router.py` and from `list_models` in `service.py`). Stale clients that still send `?category_ids=...` are **not** rejected — FastAPI ignores unknown query params — so the endpoint returns unfiltered-by-category results rather than a 422. **This story changes the query interface ONLY.** `Model.category_id` (ORM column at `_entities.py:109-111` + DB column), the `Category` ORM class, `ModelSummary.category_id` / `ModelDetail.category` response fields, `get_model_detail`'s `category` embed, and the destructive Alembic `0019_drop_category` are **all left untouched here**. Their removal is owned by a **later E42 removal story** (the ORM `class Category` + `Model.category_id` drop + `0019` must land in one migration/commit per the E41-retro action item in `sprint-status.yaml`; response-schema `category` field removal follows the E42 removal/DTO stories 42.3/42.5). See the Validation Record note on the E42 removal-story ownership gap — it does **not** block 42.1.
2. **New query params added:** `tag_ids: list[uuid.UUID] | None`, `tag_match: "all" | "any"` (default `all`), `untagged: bool` (default `false`). `tag_match` is a validated enum: an unknown value (e.g. `?tag_match=both`) returns **422** (mirror the `source` / `sort` enum-validation precedent in `test_list_filter_by_source_rejects_unknown_value`).
3. **Default semantics (`tag_match=all`) = AND between groups, OR within a group** (ratified from FR25-FILT-1 + mockup 04). Selected `tag_ids` are partitioned by `Tag.group_id`. Within one group a model matches if it has **any** of that group's selected tags; across groups a model must match **every** group that has a selected tag. **RESOLVED (D1):** groupless tags (`group_id IS NULL`) form a **single "groupless" pseudo-group** (OR-within) that AND-combines with the real groups — this matches the FacetSidebar "Inne"/groupless pseudo-facet (HANDOFF §4/§9.4) and mockup 04's "OR wewnątrz grupy". **RESOLVED (D3):** a requested `tag_id` **not found in the DB** (e.g. a merged/deleted tag) becomes its own singleton bucket with zero members → an unsatisfiable AND clause → **empty result**, preserving today's strict-AND behavior (the current per-tag loop already yields empty for an unknown tag id).
4. **`tag_match=any` override = pure OR across all selected tags**, grouping ignored: a model matches if it has any of the listed `tag_ids`. (This backs the E44 "Switch to OR" empty-result CTA — mockup 08D.) **RESOLVED (D3, any-mode):** an unknown `tag_id` simply never matches under OR, so it is **effectively ignored** and known ids still match. The all-vs-any difference (unknown → empty in `all`; unknown → ignored in `any`) is not an inconsistency — each follows directly from the AND vs OR definition, and both are covered by explicit tests.
5. **`untagged=true` surfaces zero-tag models** (FR25-FILT-2; mockup 08B pinned "Bez tagów" pseudo-facet). **Zero-tag** means a model with **no `model_tag` rows at all** — `Model.id NOT IN (SELECT model_id FROM model_tag)`. This is **distinct** from a groupless *tag* (a real tag whose `group_id IS NULL`); do not conflate the two (see Terminology in Dev Notes). Two scopes:
   - **Standalone** (`untagged=true`, no `tag_ids`): returns exactly the zero-tag models.
   - **Combined** (`untagged=true` **and** non-empty `tag_ids`): **RESOLVED (D2)** — the untagged predicate is **OR-combined (union)** with the tag predicate (result = tag-matches ∪ zero-tag models). The approved sources define only the standalone case; the combination is undefined there, so this is the ratified fail-safe/product-consistent contract: a model can never be both untagged and tag-matching, so AND would be **provably always empty**, and the mockup's empty-result philosophy (08D "Przełącz na OR / Wyczyść") is to never trap the user in a guaranteed-empty set. Union is the only additive, non-empty interpretation and matches the pinned-pseudo-facet triage intent.
6. **Empty `tag_ids` + `untagged=false` → all models** (subject to other filters). This is the current default and must not regress; `test_list_models_returns_envelope` and the sort/pagination tests stay green.
7. **All other filters, sort, pagination, and eager embeds are unchanged and still AND-combine with the tag filters:** `status`, `source`, `q`, `external_url`, `include_deleted`, `sort`, `offset`, `limit`, plus the eager `tags` / `gallery_file_ids` / `image_count` attach pipeline. No change to `_apply_sort`, the total-count subquery, or the response envelope shape. **Count/pagination safety (must hold):** the tag/untagged predicate is added to `base` via a single `base = base.where(predicate)` **before** the `total_stmt = select(func.count()).select_from(base.subquery())` at `service.py:199` — so `total` reflects the tag filter and paging stays correct. The other filters (`status`/`source`/`q`/`external_url`) remain separate `.where()` calls AND-combined with the tag predicate (they are outside the OR-with-untagged term).
8. **OpenAPI `description` on the route and the `list_models` docstring are rewritten** to describe the new contract: no `category_ids`; `tag_ids` + `tag_match` (all/any, default all) with AND-between-groups / OR-within-group; `untagged`. The stale "`category_ids` (OR …)" and "`tag_ids` (AND — model has ALL listed tags)" wording (`router.py:88-89`) must be gone.
9. **Backend suite green, 3× consecutive identical pass counts** (NFR25-DETERMINISM-1); `ruff check` + `ruff format` clean on `apps/api`. Category-filter tests in `test_sot_models_list.py` are **migrated/replaced** (not left referencing the removed param), and the tag-semantics tests are extended to cover grouped tags, `tag_match` toggle, and `untagged`. No unrelated test regresses.

## Tasks / Subtasks

- [x] **Task 1 — Service layer: rewrite tag filtering in `list_models`** (`apps/api/app/modules/sot/service.py`) (AC: #1, #3, #4, #5, #6, #7, #8)
  - [x] Add a `TagMatch(StrEnum)` next to `ModelListSort` with members `all = "all"`, `any = "any"`.
  - [x] Remove the `category_ids` parameter and the `if category_ids: base = base.where(Model.category_id.in_(category_ids))` block. `Model.category_id` untouched elsewhere.
  - [x] Add params `tag_match: TagMatch = TagMatch.all` and `untagged: bool = False`; keep `tag_ids: list[uuid.UUID] | None = None`.
  - [x] **Added `and_` to the sqlalchemy import.** `all`-mode predicate is a single `and_(*clauses)` boolean object.
  - [x] Replaced the per-tag AND loop with the group-aware algorithm; composed with `untagged` per AC #5 and applied as a single `base = base.where(predicate)` **before** the total-count subquery.
  - [x] Updated the `list_models` docstring to the new contract; stale category/tag-AND lines removed.
- [x] **Task 2 — Router: update `get_models` signature + OpenAPI description** (`apps/api/app/modules/sot/router.py`) (AC: #1, #2, #8)
  - [x] Dropped the `category_ids` param and its pass-through.
  - [x] Added `tag_match: TagMatch = TagMatch.all` and `untagged: bool = False`; pass `tag_ids`/`tag_match`/`untagged` through; imported `TagMatch` from `app.modules.sot.service`.
  - [x] Rewrote the route `description=` string.
- [x] **Task 3 — Tests: migrate category tests, extend tag semantics** (`apps/api/tests/test_sot_models_list.py`) (AC: #2–#7, #9)
  - [x] Removed `test_list_models_filter_by_category` + `test_list_filter_by_category_ids_multi`; migrated `category_ids` usages in `test_list_models_includes_seeded_model_with_tags` (→ `tag_ids`), `test_list_models_pagination` (→ `tag_ids`, now proves tag-filtered count/paging), `test_list_sort_rating_puts_nulls_last` (→ `source=printables`), `test_list_combined_filters` (→ `source=printables`+`tag_ids`). `_seed_model` still passes `category_id` (column stays `NOT NULL`).
  - [x] Extended `seeded_listing` in place with `TagGroup` `list-grp-a`/`list-grp-b` + groupless `tag_w`; assigned x,y→grp_a, z→grp_b, w groupless on m1/m3. Truth table: m1=x,y,w | m2=x | m3=z,w | m4=x,y,z | m5=none.
  - [x] Added tests (a)–(k). (f)/(g) untagged tests use `isolated_client` (fresh per-test DB) — see Completion Notes deviation: `untagged` is a DB-wide predicate, so exact "only zero-tag" is only assertable on a controlled seed, not the session-shared DB. Also added `test_list_any_empty_tag_ids_is_unfiltered` (external-review suggestion: `tag_match=any` + no ids is unfiltered).
- [x] **Task 4 — Verify gates** (AC: #9)
  - [x] `cd apps/api && uv run ruff check . && uv run ruff format --check .` clean.
  - [x] Full backend suite 3× (`uv run pytest -q -p no:cacheprovider`): **1694 passed, 3 skipped** all three times (370.65s / 379.93s / 384.70s). Baseline 1685→1694 = −2 removed category tests +11 new facet tests.

## Dev Notes

### Current state of the code being modified (READ THESE FIRST)

- **`apps/api/app/modules/sot/service.py:140-255` — `list_models`.** Today it takes `category_ids` (OR via `Model.category_id.in_(...)`, line 168-169) and `tag_ids` (**pure AND**: a `for tid in tag_ids: base = base.where(Model.id.in_(select(ModelTag.model_id).where(ModelTag.tag_id == tid)))` loop, line 172-175). After the tag loop it applies `source`/`q`/`external_url`, then a total-count subquery, sort, pagination, and eager-loads tags + gallery. **Preserve everything from line 176 onward unchanged.** `ModelListSort` (a `StrEnum`) is defined at line 44 — add `TagMatch` beside it.
- **`apps/api/app/modules/sot/router.py:84-127` — `get_models`.** Thin pass-through to `list_models`. `category_ids` is `Annotated[list[uuid.UUID] | None, Query()]` (line 103); `tag_ids` uses the same `Query()` pattern (line 105) — reuse it. The `description=` block (line 88-98) hard-codes the old filter semantics and must be rewritten.
- **`apps/api/app/core/db/models/_entities.py:80-93` — `Tag`.** Post-Epic-41 it has `group_id: uuid.UUID | None` (FK `tag_group.id`, `ondelete=SET NULL`, **nullable**) and `group_position: int`. `ModelTag` (line 153-163) is the unchanged M2M with index `ix_model_tag_tag_model (tag_id, model_id)` — good for the `select(ModelTag.model_id).where(ModelTag.tag_id.in_(...))` subqueries. `Model.category_id` (line 109-111) is still `NOT NULL` FK `category.id ON DELETE RESTRICT` — **untouched this story** (destructive drop is `0019_drop_category`, owed by E42 but not this story).
- **`apps/api/tests/test_sot_models_list.py`** — module-scoped `seeded_listing` fixture (5 models across 2 categories, tags x/y/z, all **groupless**). Helpers `_seed_cat`, `_seed_tag`, `_seed_model(session, slug, *, category_id, status, tags)`. `category_id` is required by `_seed_model` because the column is `NOT NULL` — keep passing a category when seeding even though you no longer filter by it.

### Filter algorithm (the crux of this story)

Partition the requested `tag_ids` by their group, then build one boolean predicate:

- **`tag_match=all` (default):**
  - Load `{tag_id → group_id}` for the requested ids: `select(Tag.id, Tag.group_id).where(Tag.id.in_(tag_ids))`.
  - Group the ids: all tags sharing a non-null `group_id` go into that group's bucket; **groupless** tags (`group_id IS NULL`) all go into one shared "groupless" bucket (**D1 — resolved**, see below); any **requested id not found in the DB** (compute the set-difference `set(tag_ids) - set(found_ids)` in Python) becomes its own singleton bucket so it correctly yields zero matches (**D3** — preserves current strict-AND behavior for unknown tags; AC #9 test (j)).
  - For each bucket, build a clause `Model.id.in_(select(ModelTag.model_id).where(ModelTag.tag_id.in_(bucket_ids)))`. Combine the per-bucket clauses with **`and_(*clauses)`** into one boolean object (→ **AND between groups**); `in_(bucket_ids)` inside one bucket → **OR within group**. Do NOT emit them as separate `base.where()` calls — you need one object to OR with `untagged`.
- **`tag_match=any`:** single clause `Model.id.in_(select(ModelTag.model_id).where(ModelTag.tag_id.in_(tag_ids)))` — grouping ignored; an unknown id contributes no rows and is thus silently ignored (**D3, any-mode**; AC #9 test (k)).
- **`untagged`:** `Model.id.notin_(select(ModelTag.model_id))` (models with zero `model_tag` rows). NULL-safe: `ModelTag.model_id` is a `primary_key` (NOT NULL, `_entities.py:157`), so the classic `NOT IN (subquery with NULLs)` pitfall does not apply. When both `tag_ids` and `untagged=true` are present, OR the tag predicate with the untagged predicate (**D2**, AC #5). When only `untagged=true`, use the untagged predicate alone.

Build the predicate as a Python object and `base = base.where(predicate)` **once, before** the total-count subquery (`service.py:199`), rather than mutating `base` mid-partition — this composes the `untagged` OR-combination cleanly AND keeps `total` filter-correct (AC #7). Empty `tag_ids` + `untagged=false` → no tag predicate at all (AC #6). Import `and_` alongside the existing `func, nullslast, or_` at `service.py:12`.

### Terminology — groupless tag ≠ untagged model (do NOT conflate)

Two different concepts that both involve "no group/no tag" — keep them separate in code, names, and tests:

| Concept | Predicate | Renders as | Filter param |
|---|---|---|---|
| **Groupless tag** | a real `Tag` row with `Tag.group_id IS NULL` | "Inne"/groupless pseudo-**facet** in FacetSidebar (a group of real tags) | selected via `tag_ids` (its tag id) |
| **Untagged / zero-tag model** | a `Model` with **no** `model_tag` rows: `Model.id NOT IN (SELECT model_id FROM model_tag)` | pinned "Bez tagów" pseudo-facet (triage) + ghost-chip on card | `untagged=true` |

A groupless tag still tags a model; an untagged model has zero tags. A model can carry a groupless tag and therefore is **not** untagged. Name tests accordingly (e.g. `test_list_all_groupless_tag_is_own_and_bucket` vs `test_list_untagged_returns_zero_tag_models`).

### Groupless-tag bucketing — RESOLVED (D1, no longer an open question)

**Decision:** all groupless tags (`group_id IS NULL`) form **one** OR-within "groupless" pseudo-group that AND-combines with the real groups. **Source of truth:** FacetSidebar renders groupless tags under a single "Inne"/groupless pseudo-facet (HANDOFF §4, §9.4 — `tag.group_id` nullable specifically to support this), and mockup 04 defines "OR wewnątrz grupy, AND między grupami"; selecting multiple chips within one visible facet is OR. So the groupless pseudo-facet behaves as one group. **Consequence for tests:** the current `test_list_filter_by_tag_ids_and_semantics` (tag_x + tag_y, expects AND → `{m1, m4}`) no longer means AND once x,y share a group — it must be switched to two tags in **different** groups (x in grp_a, z in grp_b → AND → `{m4}`), per Task 3. This decision is final; no mockup re-confirmation needed at dev-start.

### Scope fences (do NOT do these here)

- Do **not** remove `Category`, `Model.category_id`, `CategorySummary`, `list_categories_tree`, `get_model_detail`'s category embed, or `ModelSummary.category_id` — these belong to later E42 removal work (endpoint removal 42.3, model-create/patch + share-DTO 42.5, api-types 43.1) and the **destructive `0019_drop_category` migration**, which the E41-retro action item requires to land in one commit with the `class Category` + `Model.category_id` ORM drop. This story only changes the **`GET /api/models` query interface**; leaving `category_id` as a live `NOT NULL` column is expected and required (so `_seed_model` must keep passing `category_id`).
- Do **not** touch `/api/tags`, `/api/tag-groups`, admin routers, or `share/router.py` — separate E42 stories.
- No Alembic migration in this story. No frontend changes (E43+).

### Testing standards

- Backend pytest, `asyncio_mode="auto"`. These are `TestClient` tests using the `client` fixture and the module's `get_engine()` + `Session` seeding idiom; the `_default_admin_cookie` autouse fixture (`test_sot_models_list.py:21`) authenticates every request (GET `/models` requires an authenticated user of any role — Initiative 6 default-deny). No new fixture plumbing needed beyond adding `TagGroup` rows.
- Determinism (NFR25-DETERMINISM-1): full backend suite 3× with identical green counts before marking done: `cd apps/api && uv run pytest -q -p no:cacheprovider`. Ruff clean: rules `E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312.
- Seed rows in `seeded_listing` are module-scoped and inserted once (unique slugs required); if you add a `TagGroup`/tag, give it a unique slug or extend the existing fixture in place rather than re-seeding per test.

### Project Structure Notes

- Files touched: `apps/api/app/modules/sot/service.py`, `apps/api/app/modules/sot/router.py`, `apps/api/tests/test_sot_models_list.py`. All within the existing `sot` module — no new files, no new module, no schema change.
- `TagMatch` lives in `service.py` beside `ModelListSort` and is imported by `router.py` (same pattern already used for `ModelListSort`), so the enum is validated by FastAPI at the query layer (422 on bad value) exactly like `sort` and `source`.
- Transition note: with `category_ids` removed from the backend but the E43/E44 frontend still shipping category UI on `main` until later epics, the live web app may send `?category_ids=` that the API silently ignores. This is expected given the E42-before-E43 sequencing and is not a regression.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 42.1 — `GET /api/models` facet filtering] — story sketch + FR trace.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md#FR25-FILT-1 / FR25-FILT-2 (lines 110-111, 173)] — canonical filter semantics: "AND between groups, OR within a group; `tag_match` is the user override; `untagged=true` returns only models with zero tags".
- [Source: _bmad-output/planning-artifacts/prd.md#Initiative 25 FR25-FILT-1/2 (lines 4169-4170)] — FR→epic/story trace for facet filtering + untagged.
- [Source: docs/design/HANDOFF-tagi-fasetowe.md §3 (API), §5 (edge states), §9.4 (`tag.group_id` nullable for groupless/Untagged)] — design SoT for the facet contract; confirms untagged = zero-tag triage (08B) and groupless "Inne" pseudo-facet.
- [Source: docs/design/katalog-tagi-fasetowe.html — mockup 04 (AND/OR toggle default AND, "OR wewnątrz grupy, AND między grupami"), 08B (pinned "Bez tagów" pseudo-facet), 08D (empty-result "Przełącz na OR / Wyczyść")] — visual SoT inspected directly (not via prose); backs D1/D2/D3.
- [Source: apps/api/app/modules/sot/service.py:140-255] — `list_models` current implementation (category OR + tag pure-AND).
- [Source: apps/api/app/modules/sot/router.py:84-127] — `get_models` route + OpenAPI description to rewrite.
- [Source: apps/api/app/core/db/models/_entities.py:80-93,153-163] — `Tag.group_id` (nullable) + `ModelTag` M2M.
- [Source: apps/api/tests/test_sot_models_list.py] — fixtures + tests to migrate.
- [Source: _bmad-output/implementation-artifacts/41-2-alembic-0018-facet-tags-drop-category.md] — determinism-gate wording + baseline pass counts context.

## Previous Story Intelligence

From Epic 41 (`41-1`, `41-2`, `41-3`, all done 2026-07-18/19):

- **Epic 41 was additive-only.** Despite the name "…-category-removal", `Category` and `Model.category_id` are **still on `main`** in the ORM and DB. Migration `0018_facet_tags` added `tag_group` + `tag.group_id`/`group_position` only; the destructive `0019_drop_category` is deferred to E42. So this story correctly filters on tags **without** any category schema change and must not assume category is gone.
- **The test suite builds schema from the ORM (`init_schema()` → `create_all()`), never from Alembic** (`41-2` Dev Notes). So there is no ORM↔migration parity test to trip; your only gate is the pytest suite itself.
- **Determinism gate is real and enforced at review** (`41-2`/`41-3`): 3× identical green counts, evidence logged. Baseline after 41.3 was **1685 passed, 3 skipped** (~380s/run). Full runs are ~6–7 min each — budget for it.
- **Review is native BMAD + Aider** (per 41.x records). Keep the diff minimal and the ruleset (`E,F,W,I,B,UP,SIM,RUF`) clean to avoid review churn.

## Git Intelligence Summary

Recent commits (`git log`): `cf2ca46 feat(api): add starter facet taxonomy seed` (41.3), `dfcc874 feat(api): add facet tag schema migration` (41.2), plus BMAD epic-41 docs closeout. Pattern: backend-only facet-tag foundation landing story-by-story on `main`; commit style `feat(api): <imperative summary>`. This story is the next backend increment (API contract) on that same trajectory — expect a single `feat(api): ...` commit touching `service.py` + `router.py` + the list test.

## Project Context Reference

No `project-context.md` present in-repo. Vendor-neutral SoT is `AGENTS.md`; cross-repo catalog schema at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md`; observability/log contract and GlitchTip guides under `~/repos/configs/docs/` (per project `CLAUDE.md`). Not directly relevant to this pure-query story, but consult if a logging line is added.

## Resolved Decisions (validation 2026-07-19 — no dev-start open questions)

All three prior open questions were resolved against approved sources during `bmad-create-story:validate`. They are **decisions, not questions** — do not re-open at dev-start.

1. **D1 — Groupless-tag bucketing (`tag_match=all`).** All groupless tags (`group_id IS NULL`) = one OR-within pseudo-group that AND-combines with real groups. Source: FR25-FILT-1, mockup 04 ("OR wewnątrz grupy, AND między grupami"), HANDOFF §4/§9.4 (single "Inne" pseudo-facet; `group_id` nullable exists for it). Impact: `test_list_filter_by_tag_ids_and_semantics` switches to different-group tags (x,z) to keep asserting AND. See Dev Notes → Groupless-tag bucketing.
2. **D2 — `untagged=true` + `tag_ids` combination.** OR / union (result = tag-matches ∪ zero-tag models). Approved sources define only the standalone `untagged` case (FR25-FILT-2, mockup 08B); the combination is undefined there, so the ratified fail-safe/product-consistent contract is union: AND is provably always-empty, and the mockup empty-result ethos (08D "Przełącz na OR / Wyczyść") is to never trap the user in guaranteed-empty. See AC #5.
3. **D3 — Unknown `tag_id`.** `all` mode: unknown id → own singleton bucket → empty result (preserves current strict-AND). `any` mode: unknown id → never matches → silently ignored, known ids still match. The difference is a direct consequence of AND vs OR, not an inconsistency. Both covered by tests (j)/(k). See AC #3/#4.

### Deferred / cross-story notes (non-blocking, filed for `bmad-correct-course`)

- **E42 removal-story ownership gap.** epics.md §E42 lists 42.3 (endpoint removal) and 42.5 (create/patch + share DTO) but **no story is explicitly named as owner of the `class Category` + `Model.category_id` ORM drop + destructive Alembic `0019_drop_category`** that the E41-retro action item (`sprint-status.yaml` action_items) requires to land in one migration/commit. This does **not** block 42.1 (which fences all of it out) but E42 sprint-planning/create-story must assign it before the removal story starts. Filed to triage-backlog.
- **Tag-merge staleness × D3.** `POST /tags/merge` (admin) deletes the duplicate tag id, so a saved filter / bookmarked URL holding a merged-away `tag_id` will return empty in `all` mode (D3). Acceptable now; revisit if it becomes a real UX complaint (would be a later product decision, not 42.1).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (native BMAD `bmad-dev-story`, Claude author; Laura controller).

### Debug Log References

- RED (focused, `test_sot_models_list.py`): 6 failed / 26 passed — `test_list_all_or_within_group`, `test_list_any_is_pure_or_across_tags`, `test_list_untagged_returns_zero_tag_models`, `test_list_untagged_with_tag_ids_is_union`, `test_list_tag_match_rejects_unknown_value`, `test_list_any_unknown_tag_id_is_ignored`. Confirmed the old strict-AND path fails the new semantics before writing production code.
- GREEN (focused): 32 passed.
- Ruff: `ruff check .` → All checks passed; `ruff format --check .` → clean (266 files). One RUF002/RUF003 ambiguous-unicode hit (`∨`/`∧`/`∪` in docstring/comment) fixed to ASCII.
- Full suite 3×: 1694 passed, 3 skipped every run (370.65s / 379.93s / 384.70s). `git diff --check` clean.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Validated 2026-07-19 via `bmad-create-story:validate` (see Validation Record below) — PASS.
- Implemented 2026-07-19 via native `bmad-dev-story` (strict RED→GREEN). Predicate applied once (`base.where(...)`) before the total-count subquery per AC #7; `all`-mode uses `and_(*bucket_clauses)` (AND between buckets, `in_(bucket_ids)` OR within); groupless tags share one bucket (D1); unknown ids become singleton zero-member buckets (D3 all → empty); `any`-mode is a single `in_(tag_ids)` OR (D3 any → unknown ignored); `untagged` = `Model.id.notin_(select(ModelTag.model_id))`, OR-unioned with the tag predicate when both present (D2).
- **Deviation (documented):** the two `untagged` tests (f)/(g) use the existing `isolated_client` fixture (fresh per-test DB) instead of the module-scoped `seeded_listing`. Reason: `untagged` is a DB-wide predicate and the session-scoped shared test DB (`conftest.py::_isolated_db`, `scope="session"`) carries tag-less models from all 31 model-seeding test files, so an exact "only zero-tag models" assertion is only sound on a controlled seed. All other new tests stay on `client` + `seeded_listing` as the story predicted. No new fixture plumbing added (reused `isolated_client` + `encode_token`).
- **External-review suggestions incorporated:** explicit `tag_match=any` + empty tag_ids is-unfiltered coverage (`test_list_any_empty_tag_ids_is_unfiltered`); explicit `untagged=true` + `tag_ids` union (`test_list_untagged_with_tag_ids_is_union`); tag-filtered pagination/count now concretely proven (`test_list_models_pagination` migrated from `category_ids` to `tag_ids`, asserting `total==5` under the tag predicate).
- Scope fences honored: `Category`/`Model.category_id`/schemas/`0019` untouched; no Alembic migration; no frontend; only the 3 predicted files changed.

### File List

- `apps/api/app/modules/sot/service.py` — `TagMatch` enum, `and_` import, `list_models` signature (drop `category_ids`, add `tag_match`/`untagged`), group-aware tag predicate + untagged union, docstring rewrite.
- `apps/api/app/modules/sot/router.py` — `get_models` signature (drop `category_ids`, add `tag_match`/`untagged`), `TagMatch` import, OpenAPI `description` rewrite.
- `apps/api/tests/test_sot_models_list.py` — category-test migration, `seeded_listing` extended (2 groups + groupless tag), facet tests (a)–(k) + `any`-empty-unfiltered coverage.

## Validation Record

**Workflow:** `bmad-create-story:validate` (native BMAD 6.10, `bmm` module) · **Date:** 2026-07-19 · **Verdict: PASS** (ready-for-dev confirmed).

Sources inspected first-hand (not via story prose): `AGENTS.md`, `CLAUDE.md`, `_bmad/_config/bmad-help.csv` + `skill-manifest.csv`, PRD §Initiative 25, architecture/epics §Initiative 25 + §E42, SCP FR25-FILT-1/2, `docs/design/HANDOFF-tagi-fasetowe.md`, and the mockup HTML `docs/design/katalog-tagi-fasetowe.html` (screens 04/08B/08D read directly), plus live code `sot/service.py:140-255`, `sot/router.py:84-127`, `_entities.py:80-93,109-111,153-163`, and `tests/test_sot_models_list.py`.

### Controller review concerns — resolution

| # | Concern | Resolution |
|---|---|---|
| 1 | `untagged` "only zero-tag" vs union-with-`tag_ids` contradiction | **Fixed.** AC #5 rewritten: standalone = zero-tag only; combined = **union (D2)**, ratified as the fail-safe contract (approved sources define only standalone; AND is provably always-empty). Traceable to FR25-FILT-2 + mockup 08B/08D. No longer an open question. |
| 2 | Groupless tag (`group_id IS NULL`) vs zero-tag model (`untagged`) conflation | **Fixed.** Added Terminology table (Dev Notes); AC #5 states the distinction; Task 3 mandates non-colliding test names (`..._groupless_...` vs `..._untagged_...`). |
| 3 | Groupless bucketing for `tag_match=all` | **Fixed (D1).** One OR-within groupless pseudo-group, AND-combining with real groups — from mockup 04 + HANDOFF §4/§9.4. Removed from open questions; existing AND test re-pointed to different-group tags. |
| 4 | Unknown tag id for `all` and `any` | **Fixed (D3).** `all` → empty (strict AND preserved); `any` → ignored. Both made explicit in AC #3/#4 with rationale + tests (j)/(k). |
| 5 | Service query correctness / efficiency / count+pagination safety / testability | **Verified & tightened.** Predicate applied once to `base` before the count subquery (`service.py:199`) → count/paging safe (AC #7). Subqueries hit `ix_model_tag_tag_model`. `NOT IN` NULL-safe (`ModelTag.model_id` is PK/NOT NULL). Encoded the missing **`and_` import** (`service.py:12`) and the "combine buckets with `and_(*clauses)`, not repeated `.where()`" requirement — the one real dev-trap. All expressible on the existing SQLModel/SQLite `client` fixture. |
| 6 | No category ORM/schema/DTO removal leaks; destructive migration coupling assigned correctly | **Verified.** 42.1 fences out `Category`/`Model.category_id`/schemas/`0019` (AC #1 + Scope fences corrected). Flagged (non-blocking) that epics.md §E42 does not name an explicit owner for the ORM drop + `0019_drop_category` — filed to triage-backlog for `bmad-correct-course`. |
| 7 | Status / sprint truthfulness | **Truthful.** Validation passed → story stays `ready-for-dev`; `sprint-status.yaml` already records `42-1-models-facet-filtering: ready-for-dev` + `epic-42: in-progress`. No sprint-status change required. |

### Checklist (create-story quality gate)

- [x] Story maps to real FRs (FR25-FILT-1/2) with epic/SCP/PRD/mockup traceability.
- [x] Every AC is unambiguous and testable; no self-contradiction (AC #5 fixed).
- [x] All files-to-modify read first-hand; current-state notes accurate to line numbers.
- [x] Reuse over reinvention (extends `list_models`; no new files/module/schema).
- [x] Regression fences explicit (count subquery, `_apply_sort`, eager pipeline, envelope, `category_id` column all preserved).
- [x] Scope boundaries hard-fenced (no ORM/schema/DTO/migration/frontend leak).
- [x] Determinism gate carried (3× identical green; baseline 1685p/3s minus removed category tests plus new tag/untagged tests).
- [x] No template placeholders left; no dev-start open questions (all → ratified decisions).

### Remaining blockers

None. Story is implementation-ready.
