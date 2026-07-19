---
baseline_commit: 6a6a1163425d50447317c2eb4733dd13b7a7d0e4
---
# Story 42.2: Tags + tag-groups read API

Status: done

<!-- Authored + self-validated 2026-07-19 via native bmad-help → bmad-sprint-status → bmad-create-story (Claude author; Laura controller). All eight controller contract questions resolved code-first against approved sources + live code; no dev-start open questions remain. See "## Resolved Decisions" and "## Validation Record". -->

## Story

As a **catalog user (admin / member / agent) and the future facet-sidebar frontend**,
I want **`GET /api/tags` to expose each tag's facet membership (`group_id` + `group_position`) and an opt-in per-tag model count (`?with_counts=true`), plus a new `GET /api/tag-groups` read endpoint that returns groups with their tags and per-tag counts in one round-trip**,
so that **the facet taxonomy (Initiative 25) has the read surface the sidebar (`useTagGroups()`), the model-detail grouped-tag rendering, and the admin group screen will consume — without any category coupling and without an N+1 fetch**.

Traces: **FR25-TAX-1**, **FR25-BROWSE-1**, **FR25-DETAIL-1**; **NFR25-DETERMINISM-1** (Epic E42; SCP `sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md`; architecture.md § Initiative 25 Decision AW read-surface).

## Acceptance Criteria

1. **`TagRead` gains facet membership (additive).** The shared `TagRead` schema (`apps/api/app/modules/sot/schemas.py`) adds `group_id: uuid.UUID | None` and `group_position: int`. Both are direct `Tag` ORM columns (`_entities.py:87-91`, landed in Epic 41) so `from_attributes` reads them at zero query cost. This is **purely additive**: existing consumers ignore unknown keys, and because `ModelSummary.tags` / `ModelDetail.tags` embed `TagRead`, the two new fields also appear (additively) on every `GET /api/models` and `GET /api/models/{id}` tag — this is **intended** (FR25-DETAIL-1 grouped rendering needs `group_id` per model-embedded tag) and must not regress the existing model list/detail tests. **RESOLVED (D-SHAPE-1):** the `group` *slug string* from the HANDOFF §2 sketch is **NOT** added to `TagRead` — the FK `group_id` is the canonical membership pointer, the human label/slug is delivered authoritatively by `GET /api/tag-groups`, and adding a slug to the model-embedded `TagRead` would force a per-tag join on the hot model-list path (Ponytail: no redundant field). Architecture line 3192/3207 says "`group`/`group_id` (+ `group_position`)"; `group_id` + `group_position` satisfy the load-bearing intent, slug is intentionally deferred to the group endpoint.

2. **`GET /api/tags` without counts returns the enriched-but-count-free shape.** With no `with_counts` (or `with_counts=false`), each item is exactly `{id, slug, name_en, name_pl, group_id, group_position}` — **no `model_count` key present**. The existing `q` substring filter (over `slug`/`name_en`/`name_pl`, case-insensitive) and `limit` (default 50, max 200, 422 over max) behaviour is **unchanged** (`test_get_tags_*` in `test_sot_tags.py` stay green, extended only to assert the two new keys exist).

3. **`GET /api/tags?with_counts=true` adds a per-tag `model_count: int`.** Each returned item additionally carries `model_count` = the number of **distinct non-deleted models** carrying that tag. **RESOLVED (D-COUNT-1 — count scope):** "count" means **`COUNT(model_tag rows joined to Model WHERE Model.deleted_at IS NULL)`** — i.e. distinct non-deleted models. This mirrors the only existing catalog-count precedent, `list_categories_tree` (`service.py:100-105`, counts `Model.deleted_at.is_(None)`), and the default visibility of `list_models` (`service.py:184-185`). There is **no** separate "visible/available/published" concept on `Model` beyond `deleted_at` (`status` is not a visibility gate — every status shows in the catalog), so soft-delete is the only scope filter. Counts are computed in **one** `GROUP BY` query (no N+1, AC #8). `with_counts` composes with `q` and `limit`: counts attach to whichever tags the `q`/`limit` filter returns.

4. **New `GET /api/tag-groups` endpoint.** Returns an envelope `{groups: [TagGroupRead], groupless: [TagReadWithCount]}` where:
   - `TagGroupRead = {id, slug, name_en, name_pl, position, tags: [TagReadWithCount]}`.
   - `TagReadWithCount` = `TagRead` (AC #1 shape) **plus** `model_count: int` (same D-COUNT-1 definition as AC #3).
   - `groups` = every real `TagGroup` row (**including empty groups** — a group with zero tags is returned with `tags: []`; presentation-level hiding is the E44 sidebar's job, the read API returns the full governance-relevant set), ordered by **`position ASC, then slug ASC`** as a stable tie-break.
   - Within each group, `tags` are ordered by **`group_position ASC, then slug ASC`** (`group_position` exists precisely for intra-group ordering, HANDOFF §2).
   - `groupless` = every `Tag` with `group_id IS NULL` (the real-tags-without-a-facet set the sidebar renders under the single "Inne"/groupless pseudo-facet, HANDOFF §9.4), ordered by `group_position ASC, then slug ASC`, each carrying `model_count`.
   **RESOLVED (D-ENVELOPE-1):** groupless tags are returned as a **sibling `groupless` array, NOT as a synthetic `TagGroupRead` with `id=null`** — this keeps `TagGroupRead.id` a non-nullable UUID (clean FE typing / admin addressability) and makes the real-group vs pseudo-facet distinction explicit at the contract level, matching FacetSidebar's "real groups + pinned Inne pseudo-facet". **RESOLVED (D-UNTAGGED-1 — do NOT conflate):** `groupless` is about *tags whose `group_id IS NULL`*; it is **unrelated** to the *untagged model* concept (`Model` with zero `model_tag` rows, owned by 42.1's `untagged=true`). `GET /api/tag-groups` says nothing about untagged models. See Terminology in Dev Notes.

5. **Counts are consistent across both endpoints.** For any given tag, its `model_count` from `GET /api/tags?with_counts=true` **equals** its `model_count` inside `GET /api/tag-groups` — guaranteed by construction: both call the **same** `_tag_model_counts(session)` helper (D-COUNT-1). A test asserts equality for at least one tag with a non-zero, non-trivial count.

6. **Auth posture: authenticated default-deny, outside `_PUBLIC_ROUTES` (unchanged).** Both `GET /api/tags` (already) and the new `GET /api/tag-groups` require an authenticated user of **any** role (admin / member / agent) via the `current_user` dependency; anonymous → **401**, unknown role → **403**. Neither route is added to `main.py:_PUBLIC_ROUTES`. **RESOLVED (D-AUTH-1):** this matches (a) the epics.md §42.2 sketch ("Outside `_PUBLIC_ROUTES` per existing auth posture"), (b) every existing SoT read (`test_sot_auth_boundary.py`, the Init 6 Story 11.1 default-deny gate), and (c) the just-shipped sibling story 42.1 which kept `GET /api/models` on `current_user` outside the allowlist. The architecture.md §Initiative 25 paragraph (line 3211) that calls these "public catalog reads" to be "added to `_PUBLIC_ROUTES`" is **not** overridden here merely because "code says otherwise" — it is superseded on four independent grounds, none of which is a security downgrade: (1) **more-specific source wins** — the story-level source, epics.md §42.2, explicitly directs "Outside `_PUBLIC_ROUTES` per existing auth posture (confirm at create-story)", which is exactly this create-story confirmation; (2) **internal contradiction** — architecture.md line 3224 states Initiative 25 "honours Init 6 Decision M default-deny `_PUBLIC_ROUTES` posture", directly contradicting §3211; (3) **false premise** — §3211's instruction rests on the claim that `GET /api/categories` "must be deleted from the allowlist", but the live `_PUBLIC_ROUTES` (`main.py:50-61`) is health/auth/share only and `test_sot_categories_anonymous_returns_401` proves categories was **never** allowlisted, so the paragraph was written against a mistaken model of the current auth posture; (4) **no source requests anonymity + safety** — no approved source (PRD, SCP §4.2, HANDOFF) asks for an *anonymous* catalog; making these reads public would expose the entire model catalog to unauthenticated users — an unrequested product/security decision. Keeping `current_user` is therefore the source-backed **and** conservative (non-downgrade) posture; the alternative would need explicit owner approval via `bmad-correct-course`, not a silent create-story flip. Adding `/api/tags`/`/api/tag-groups` to the allowlist would also break `test_sot_tags_anonymous_returns_401` (AC-3, Init 6). The §3211 doc drift is filed to triage-backlog as **TB-055** for a `bmad-correct-course` documentation-correction pass; it does **not** block this story.

7. **Auth-boundary tests for the new route.** `test_sot_auth_boundary.py` is extended with `/api/tag-groups`: anonymous → 401 (AC-3 pattern), agent/member/admin → 200 (AC-2/4/5 pattern), mirroring the existing six-endpoint table. (`GET /api/tags` anonymous-401 / role-200 coverage already exists there — leave it; add tag-groups only.)

8. **No N+1; efficient query plans.** `with_counts` on `GET /api/tags` and the whole `GET /api/tag-groups` assembly each run a **bounded, constant number** of queries regardless of tag/group cardinality:
   - `_tag_model_counts` = **one** `GROUP BY` query: `select(ModelTag.tag_id, func.count()).select_from(ModelTag).join(Model, Model.id == ModelTag.model_id).where(Model.deleted_at.is_(None)).group_by(ModelTag.tag_id)` → `dict[tag_id, count]`, defaulting missing tags to 0. Uses the existing `ix_model_tag_tag_model (tag_id, model_id)` covering index (`_entities.py:155`).
   - `GET /api/tag-groups` = 3 queries total: all `TagGroup` rows (1), all `Tag` rows (1), `_tag_model_counts` (1). Groups/tags are bucketed **in Python** (single pass), so there is **no per-group `WHERE group_id = ?` query** — which is why the currently-unindexed `tag.group_id` (E41-retro action item) is **not** needed by this read pattern (discharge note in Dev Notes). No lazy relationship access anywhere (functions build Pydantic objects from explicit selects, matching the `service.py` "no ORM lazy-load" idiom).
   - **No-N+1 is verifiable, not merely asserted in prose.** The constant-query property is guaranteed *by construction* (explicit selects + Python bucketing, no ORM relationship attribute access), and a test **proves** it: wrap the endpoint call in a SQLAlchemy `event.listen(engine, "before_cursor_execute", ...)` counter (or `sqlalchemy.event` on the session's connection) and assert the query count for `GET /api/tag-groups` is **independent of group/tag cardinality** — seed N groups × M tags, then 2N groups × 2M tags, and assert the counter is equal (and small, ≤ a fixed bound) across both. The same harness asserts `GET /api/tags?with_counts=true` issues exactly one additional aggregate query versus the no-count path. This is the reasonable, repo-idiomatic verification method (no new dependency).

9. **OpenAPI + docstrings.** The `GET /api/tags` route **renders a non-empty, honest OpenAPI response schema**: `response_model=list[TagListItem]` (a named component with `model_count` as an optional integer) — **not** `response_model=None`, which the FastAPI 0.136 probe (D-RESPONSEMODEL-1) proves emits an empty `schema: {}` and would violate this AC. The route `description=` and `list_tags` docstring document `with_counts`, the base key set, both response shapes, and the new `group_id`/`group_position` fields; the new `GET /api/tag-groups` route has a complete `description=` (envelope shape, ordering, groupless handling, empty-group inclusion, count scope, default-deny auth) and its service fn has a docstring. No stale category wording introduced.

10. **Backend suite green, 3× consecutive identical pass counts** (NFR25-DETERMINISM-1); `ruff check` + `ruff format --check` clean on `apps/api`. New tests for `with_counts`, the `group_id`/`group_position` fields, `GET /api/tag-groups` (shape, ordering, groupless, empty groups, counts, cross-endpoint consistency), and the auth boundary. No unrelated test regresses; the additive `TagRead` fields do not break any existing model-list/detail/schema test.

## Tasks / Subtasks

- [x] **Task 1 — Schemas: enrich `TagRead`, add `TagReadWithCount`, `TagGroupRead`, `TagGroupsResponse`** (`apps/api/app/modules/sot/schemas.py`) (AC: #1, #2, #3, #4)
  - [x] Add `group_id: uuid.UUID | None` and `group_position: int` to `TagRead` (keep it `from_attributes`; order fields after `name_pl`).
  - [x] Add `class TagListItem(TagRead)` — the **conditional-count** item for `GET /api/tags`: `model_count: int | None = None` **plus** a `@model_serializer(mode="wrap")` that pops `model_count` from the dumped dict **only when it is `None`** (so `with_counts=false` items have no `model_count` key, while `group_id: null` / `name_pl: null` are preserved). See D-RESPONSEMODEL-1 in Dev Notes for why this beats `response_model=None` and `response_model_exclude_none=True` (both probe-falsified). Import `model_serializer` from `pydantic`.
  - [x] Add `class TagReadWithCount(TagRead): model_count: int` (subclass, **required** count — used by `GET /api/tag-groups` where the count is always present; distinct from `TagListItem`'s optional count). The base `TagRead` embedded in models stays count-free.
  - [x] Add `class TagGroupRead(_OrmBase): id: uuid.UUID; slug: str; name_en: str; name_pl: str | None; position: int; tags: list[TagReadWithCount]`.
  - [x] Add `class TagGroupsResponse(BaseModel): groups: list[TagGroupRead]; groupless: list[TagReadWithCount]`.
- [x] **Task 2 — Service: count helper + `list_tags(with_counts)` + `list_tag_groups`** (`apps/api/app/modules/sot/service.py`) (AC: #3, #4, #5, #8)
  - [x] Add `_tag_model_counts(session) -> dict[uuid.UUID, int]` — the single `GROUP BY` query (D-COUNT-1); import `Model`/`ModelTag` are already imported; `func` already imported.
  - [x] Extend `list_tags(session, *, q=None, limit=50, with_counts=False) -> list[TagListItem]` — keep the current query/order/filter; build `TagListItem` items either way (so the route's `response_model=list[TagListItem]` matches). When `with_counts`, fetch `_tag_model_counts` once and set `model_count = counts.get(tag.id, 0)`; when not, leave `model_count` unset (`None`) so the serializer drops the key. (`TagRead` embedded in models is untouched — only the standalone `/api/tags` items become `TagListItem`.) Keep the default `limit` consistent with the router (see Task 3 note on the default-50 discrepancy).
  - [x] Add `list_tag_groups(session) -> TagGroupsResponse`: fetch all `TagGroup` (order `position, slug`), all `Tag` (one query), `_tag_model_counts` once; bucket tags by `group_id` in Python; build `TagGroupRead` per group with tags sorted `(group_position, slug)` and `model_count` attached; include empty groups (`tags: []`); collect `group_id IS NULL` tags into `groupless` sorted `(group_position, slug)`. Return the envelope.
- [x] **Task 3 — Router: `with_counts` on `GET /api/tags`, new `GET /api/tag-groups`** (`apps/api/app/modules/sot/router.py`) (AC: #2, #3, #4, #6, #9)
  - [x] Add `with_counts: bool = False` param to `get_tags`; pass through. **Realization (D-RESPONSEMODEL-1 — probe-validated, do NOT use `response_model=None`):** declare `response_model=list[TagListItem]` and return `list[TagListItem]` from `list_tags`. `TagListItem` carries `model_count: int | None = None`; the service sets `model_count` only when `with_counts=true`, and `TagListItem`'s `@model_serializer` (Task 1) drops the key when it is `None`. This yields the exact AC #2/#3 contract (**no `model_count` key** without counts; `model_count: int` with counts; `group_id: null` and `name_pl: null` **preserved**) **and** a complete, honest OpenAPI schema (a single named `TagListItem` component with `model_count` as an optional integer). Do the `description=` documenting of `with_counts`, the base key set, and both shapes for AC #9.
  - [x] **Align the `list_tags` default `limit`.** The router declares `limit=Query(default=50, ...)` (`router.py:79`) but `service.py:list_tags` currently defaults `limit=200`; the router value wins in production, but `test_get_tags_default_limit_is_200` asserts the **200-boundary is the max**, not the default (it requests `?limit=200`). Do not change public behaviour — keep router default 50, service default irrelevant when called via router; only touch the service default if needed for a direct-call test. Leave the boundary test semantics intact.
  - [x] Add `get_tag_groups` route (`@router.get("/tag-groups", response_model=TagGroupsResponse, ...)`) with `session` + `_user_id: uuid.UUID = current_user`, full `description=` (AC #9), returning `list_tag_groups(session)`. Import the new schemas/service fn.
- [x] **Task 4 — Tests** (AC: #2–#8, #10)
  - [x] `tests/test_sot_tags.py`: extend to assert `group_id`/`group_position` keys present (with and without a group; **assert `group_id` is present as an explicit `null` for a groupless tag and `name_pl: null` is preserved** — the D-RESPONSEMODEL-1 exact-key guard against an `exclude_none`-style regression); add `with_counts=true` tests (count matches seeded associations; count excludes a soft-deleted model; count is 0 for an unused tag; `model_count` key absent when `with_counts` omitted).
  - [x] `tests/test_sot_tags.py`: **OpenAPI honesty test (AC #9)** — GET `/openapi.json`, assert the `GET /api/tags` 200 response schema is non-empty (references a `TagListItem` component, not `{}`) and that `model_count` is advertised as an optional integer. This is the regression guard proving `response_model=None` was not used.
  - [x] `tests/test_sot_tag_groups.py` (**new**): group order by `(position, slug)`; intra-group tag order by `(group_position, slug)`; empty group returned with `tags: []`; groupless tags in the `groupless` array (not under any group); per-tag `model_count` correct + non-deleted scope; envelope keys `{groups, groupless}`; a groupless tag never appears in `groups`.
  - [x] `tests/test_sot_tag_groups.py` cross-endpoint consistency test (AC #5): same tag's `model_count` equal from `/api/tags?with_counts=true` and `/api/tag-groups`.
  - [x] `tests/test_sot_tag_groups.py` **constant-query-count test (AC #8, no-N+1)**: via a `before_cursor_execute` counter, assert `GET /api/tag-groups` issues the same (bounded) number of queries for a small vs a doubled seed (cardinality-independent), and that `with_counts=true` adds exactly one aggregate query over the no-count path.
  - [x] `tests/test_sot_auth_boundary.py`: add `/api/tag-groups` anonymous-401 + agent/member/admin-200 (AC #7).
  - [x] `tests/test_sot_schemas.py`: extend `test_tag_read_from_orm` to assert `group_id`/`group_position` round-trip; add a `TagReadWithCount` / `TagGroupRead` / `TagGroupsResponse` shape test.
- [x] **Task 5 — Verify gates** (AC: #10)
  - [x] `cd apps/api && uv run ruff check . && uv run ruff format --check .` clean.
  - [x] Full backend suite **3× consecutive identical** green counts (`uv run pytest -q -p no:cacheprovider`). Record the pass/skip counts and per-run durations. Baseline after 42.1 = **1694 passed, 3 skipped** (~6–7 min/run); expect +N new tests, same across all three runs. `git diff --check` clean.

## Dev Notes

### Current state of the code being modified (READ THESE FIRST)

- **`apps/api/app/modules/sot/schemas.py:35-40` — `TagRead`.** Today `{id, slug, name_en, name_pl}`, `from_attributes=True` (via `_OrmBase`). Embedded in `ModelSummary.tags` (`:107`) and therefore in `ModelDetail`. Adding `group_id`/`group_position` here is the single-point, additive change that also enriches model responses (intended, AC #1). `CategorySummary`/`CategoryNode`/`CategoryTree` in this file are **untouched** (removed by 42.3/42.5/43.1, not here).
- **`apps/api/app/modules/sot/service.py:122-142` — `list_tags`.** Returns `list[TagRead]`, orders by `Tag.slug`, `q` filters case-insensitively over `slug`/`name_en`/`name_pl`, `limit` caps. `func`, `or_`, `select`, `Model`, `ModelTag`, `Tag` are **already imported** at the top (`:12-27`). Extend in place — do not rewrite the query.
- **`apps/api/app/modules/sot/service.py:58-119` — `list_categories_tree`.** The count-scope precedent: `select(Model.category_id, func.count(Model.id)).where(Model.deleted_at.is_(None)).group_by(...)`. Your `_tag_model_counts` mirrors this exactly but groups `ModelTag.tag_id` via a join to `Model` for the `deleted_at` filter. **Do not modify this function** (category-owned, later story).
- **`apps/api/app/modules/sot/router.py:65-82` — `get_tags`.** `@router.get("/tags", response_model=list[TagRead], ...)`, `q`/`limit`/`current_user`. Add `with_counts`; the new `/tag-groups` route sits right after it. The route `description=` already documents the default-deny posture — reuse that wording.
- **`apps/api/app/core/db/models/_entities.py:61-93` — `TagGroup` + `Tag`.** `TagGroup{id, slug, name_en, name_pl, position, created_at, updated_at}` with `uq_tag_group_slug` unique index. `Tag{... group_id (nullable FK tag_group.id ON DELETE SET NULL), group_position(int, default 0)}`. `ModelTag` (`:153-163`) M2M with `ix_model_tag_tag_model (tag_id, model_id)`. **No** `deleted_at`/`hidden`/`is_active` on either `Tag` or `TagGroup` (see D-LIFECYCLE-1). All landed additively in Epic 41.
- **`apps/api/app/main.py:50-61` — `_PUBLIC_ROUTES`.** Only `/api/health`, `/api/auth/{login,logout,refresh,register,2fa/verify,password-reset}`, `/api/share/{token}*`. **Categories is not here; tags is not here.** Do not add tags or tag-groups (D-AUTH-1). Touching this file is out of scope for 42.2.
- **`apps/api/tests/test_sot_auth_boundary.py`** — the Init 6 Story 11.1 six-endpoint default-deny gate (anonymous-401 / agent-200 / member-200 / admin-200 / rogue-403). Add tag-groups following the identical `_clear_cookie`/`_mint_cookie` pattern; no seeding needed (an empty DB still returns 200 with `{groups: [], groupless: []}`).

### The two count-bearing queries (the crux)

```python
def _tag_model_counts(session: Session) -> dict[uuid.UUID, int]:
    """Distinct non-deleted models per tag (D-COUNT-1). One GROUP BY; no N+1."""
    rows = session.exec(
        select(ModelTag.tag_id, func.count())
        .select_from(ModelTag)
        .join(Model, Model.id == ModelTag.model_id)
        .where(Model.deleted_at.is_(None))
        .group_by(ModelTag.tag_id)
    ).all()
    return {tag_id: n for tag_id, n in rows}
```

`list_tag_groups` then does exactly three reads (`TagGroup`, `Tag`, `_tag_model_counts`) and buckets in Python — no per-group query, so no `tag.group_id` index is needed for this read pattern (discharge the E41-retro "evaluate an index on tag.group_id" action item **for reads**; it stays open for admin per-group queries in 42.4). `ModelTag.model_id` is a NOT-NULL PK, so the `JOIN` is exact and `func.count()` counts one row per (tag, model) association = distinct models per tag (a model can hold a tag at most once — `ModelTag` composite PK `(model_id, tag_id)`).

### Terminology — three "no-group/no-tag" concepts, keep them separate (do NOT conflate)

| Concept | Predicate | This story | Owner |
|---|---|---|---|
| **Groupless tag** | real `Tag` with `Tag.group_id IS NULL` | returned in `GET /api/tag-groups` `groupless[]`; `TagRead.group_id = null` | **42.2** |
| **Empty group** | `TagGroup` with zero member tags | returned in `groups[]` with `tags: []` | **42.2** |
| **Untagged model** | `Model` with zero `model_tag` rows | **NOT** in scope — `untagged=true` on `GET /api/models` | 42.1 (done) |

A groupless tag still tags models (has a `model_count`); an empty group has no tags; an untagged model has no tags. Name tests so these never collide (`..._groupless_tag_...`, `..._empty_group_...`; do not reuse "untagged").

### Resolved contract decisions (no dev-start open questions)

- **D-RESPONSEMODEL-1** — `GET /api/tags` uses `response_model=list[TagListItem]` where `TagListItem(TagRead)` has `model_count: int | None = None` + a `@model_serializer(mode="wrap")` that drops `model_count` only when `None`. **Probe-validated against FastAPI 0.136 / Pydantic 2.13** (independent validation 2026-07-19): (a) `response_model=None` emits `schema: {}` in OpenAPI — the return annotation is discarded, so the "OpenAPI infers from the annotation" claim is false → violates AC #9; (b) `response_model_exclude_none=True` is **global** and strips `group_id: null` **and** `name_pl: null` from groupless/pl-less tags → violates AC #2's required key set; (c) a union return annotation serializes correctly only with a fragile member-order dependency. The `TagListItem` + per-field serializer is the smallest design that yields the exact key contract **and** a single honest OpenAPI schema. `GET /api/tag-groups` keeps the separate **required-count** `TagReadWithCount`. AC #2/#3/#9.
- **D-SHAPE-1** — `TagRead` adds `group_id` + `group_position` only; **no `group` slug string** (redundant on the hot model-embed path; label comes from `/api/tag-groups`). The design SoT HANDOFF §2/§3 modelled a flat `group: str|null` slug on `TagRead`; architecture Decision AU **superseded** that by introducing the `TagGroup` table + `group_id` FK, so following `group_id` (the newer, more-specific source) over the HANDOFF slug is correct precedence. **Exact label-resolution contract:** `group_id` is the canonical facet pointer on every tag (embedded and standalone); the human group label (`slug`/`name_en`/`name_pl`/`position`) is delivered **only** by `GET /api/tag-groups`. E43's `useTagGroups()` provides the `group_id → group` map (one cached fetch, app-wide), so E45 grouped-detail rendering resolves labels with **zero** extra per-tag query and no N+1. If a consumer of `GET /api/tags` needs the group label inline, it resolves via the same cached map — it does not get the slug embedded. AC #1.
- **D-COUNT-1** — count = distinct **non-deleted** models per tag (`Model.deleted_at IS NULL`), per the `list_categories_tree` precedent + `list_models` default visibility; no visible/available/status scope exists. AC #3.
- **D-ENVELOPE-1** — `GET /api/tag-groups` = `{groups: [TagGroupRead], groupless: [TagReadWithCount]}`; groupless as a sibling array (not a null-id pseudo-group); empty groups included; order groups `(position, slug)`, tags `(group_position, slug)`. AC #4.
- **D-UNTAGGED-1** — groupless tag ≠ untagged model; `/api/tag-groups` is silent about untagged models (owned by 42.1). AC #4 + Terminology.
- **D-AUTH-1** — authenticated `current_user` (any role), **outside** `_PUBLIC_ROUTES`; architecture.md §3211 "public reads → add to `_PUBLIC_ROUTES`" is code-falsifiable (would break `test_sot_tags_anonymous_returns_401`; categories was never in the allowlist) → not followed, filed to triage. AC #6.
- **D-LIFECYCLE-1** — neither `Tag` nor `TagGroup` has any soft-delete/hidden/active lifecycle column, so there is **nothing to filter**: all tags/groups are live and returned. Tag deletion is hard-delete gated by `model_tag` RESTRICT (admin merge-or-empty, `POST /tags/merge`, unchanged). If a hidden/archived lifecycle is ever wanted it is a new product decision + migration, out of scope here.
- **D-CONSISTENCY-1** — one `_tag_model_counts` helper feeds both endpoints → counts identical by construction. AC #5.

### Scope fences (do NOT do these here)

- **Read APIs only.** No admin group CRUD / rename / reorder / move-to-group and no `POST/PATCH/DELETE /api/admin/tag-groups` — that is **42.4** (admin group governance). No use or change of `POST /tags/merge`.
- **No category-endpoint removal** (`GET /api/categories`, admin category CRUD, `list_categories_tree`, `Category*` schemas) — that is **42.3**. Leave every category symbol live.
- **No `Category` / `Model.category_id` ORM or DB change, no `0019_drop_category` migration** — owned by the E42 destructive-removal story (E41-retro action item: ORM drop + `0019` land in one commit). **No Alembic migration at all in 42.2** (schema is unchanged — `group_id`/`group_position`/`tag_group` already shipped in `0018`).
- **No `ModelCreate`/`ModelPatch`/`ShareModelView` changes** (42.5).
- **No frontend** — `apps/web/src/lib/api-types.ts` (`TagRead`, `useTagGroups()`), hooks, components are **E43+**. Do not touch them even though this story defines the contract they will consume.
- **No `GET /api/models` filter changes** — 42.1 is done; the only model-response effect here is the *additive* `group_id`/`group_position` on embedded tags (a schema side-effect, not a filter/route change).

### Testing standards

- Backend pytest, `asyncio_mode="auto"`, `TestClient` `client` fixture + `get_engine()`/`Session` seeding idiom. `GET /api/tags` / `GET /api/tag-groups` require an authenticated user of any role — the `_default_admin_cookie` autouse fixture in `test_sot_tags.py` (and the equivalent in a new `test_sot_tag_groups.py`) authenticates every request; copy that fixture.
- Seed `TagGroup` + `Tag` + `Model` + `ModelTag` rows directly via `Session` (as `test_tag_group_entity.py` and `test_sot_models_list.py` do). For the non-deleted-count test, seed one model with `deleted_at` set and assert it is excluded. Use **unique slugs** per test (the session-scoped shared DB persists rows across the file) or a fresh/isolated DB where an exact global assertion is needed (the 42.1 `isolated_client` precedent for DB-wide predicates — relevant if you assert exact `groups`/`groupless` membership globally; prefer scoping assertions to your uniquely-slugged seed rows instead).
- Determinism (NFR25-DETERMINISM-1): full backend suite 3× identical green before done. Ruff rules `E,F,W,I,B,UP,SIM,RUF`, line-length 100, py312. Watch RUF002/003 ambiguous-unicode in any docstring (42.1 hit `∨`/`∧`/`∪`).

### Project Structure Notes

- Files touched (all in the existing `sot` module — **no new module, no schema/migration**): `apps/api/app/modules/sot/schemas.py`, `apps/api/app/modules/sot/service.py`, `apps/api/app/modules/sot/router.py`, `apps/api/tests/test_sot_tags.py`, `apps/api/tests/test_sot_auth_boundary.py`, `apps/api/tests/test_sot_schemas.py`, and **new** `apps/api/tests/test_sot_tag_groups.py`.
- Expected commit shape: a single `feat(api): ...` touching the three `sot` source files + the test files (matching the 42.1 `feat(api):` precedent).
- The additive `TagRead` fields flow into `GET /api/models` responses on `main` before the E43 frontend types add them — consistent with the E42-before-E43 sequencing; not a regression (unknown-key-tolerant clients).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 42.2 — Tags + tag-groups read API (line 4228-4230)] — sketch + FR trace + "Outside `_PUBLIC_ROUTES` (confirm at create-story)".
- [Source: _bmad-output/planning-artifacts/prd.md#Initiative 25 FR25-TAX-1 / FR25-BROWSE-1 / FR25-DETAIL-1 (lines 2172, 2176-2177)] — facet groups first-class; sidebar per-tag counts; grouped detail rendering.
- [Source: _bmad-output/planning-artifacts/architecture.md#Initiative 25 Decision AW read surface (lines 3190-3211)] — `GET /api/tags` returns `group`/`group_id`+`group_position`, `?with_counts`; new `GET /api/tag-groups` (groups + tags + per-tag counts) backing `useTagGroups()`; **NOTE line 3211 "public reads → `_PUBLIC_ROUTES`" is superseded by code — see D-AUTH-1**.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md#§4.2 API contract (line 174-175), §4.3 Epic 42 (line 193)] — "GET /tags (group + counts); new GET /tag-groups".
- [Source: docs/design/HANDOFF-tagi-fasetowe.md §3 (API), §8 (starter taxonomy), §9.1/§9.4 (client-side search over fetched groups; single "Inne" groupless pseudo-facet; `tag.group_id` nullable)] — design SoT for the read contract.
- [Source: apps/api/app/modules/sot/service.py:58-142] — `list_categories_tree` count-scope precedent + `list_tags` to extend.
- [Source: apps/api/app/modules/sot/schemas.py:35-40,91-122] — `TagRead` to enrich; `ModelSummary`/`ModelDetail` embed it.
- [Source: apps/api/app/modules/sot/router.py:65-82] — `get_tags` route to extend + insertion point for `/tag-groups`.
- [Source: apps/api/app/core/db/models/_entities.py:61-93,153-163] — `TagGroup`, `Tag.group_id`/`group_position`, `ModelTag` + `ix_model_tag_tag_model`.
- [Source: apps/api/app/main.py:50-61] — live `_PUBLIC_ROUTES` (health/auth/share only).
- [Source: apps/api/tests/test_sot_auth_boundary.py] — default-deny gate to extend for `/api/tag-groups`.
- [Source: apps/api/tests/test_sot_tags.py, tests/test_tag_group_entity.py, tests/test_sot_schemas.py:44-53] — test idioms + `TagRead` round-trip to extend.
- [Source: _bmad-output/implementation-artifacts/42-1-models-facet-filtering.md] — sibling-story precedent: determinism gate wording, baseline 1694p/3s, auth posture (`current_user`, outside `_PUBLIC_ROUTES`), groupless≠untagged terminology, `feat(api):` commit shape.

## Previous Story Intelligence

From Epic 41 (41.1/41.2/41.3, done) and Epic 42.1 (done, deployed at `caafbe7`/`0d9c2d4`):

- **Epic 41 was additive-only** — `TagGroup`, `Tag.group_id`, `Tag.group_position` are live on `main` (migration `0018_facet_tags`); `Category`/`Model.category_id` are **still present** (destructive `0019_drop_category` deferred to the E42 removal story). So 42.2 reads the facet columns with **no schema change** and must not assume category is gone.
- **The test suite builds schema from the ORM** (`init_schema()` → `create_all()`), never from Alembic (41.2 Dev Notes) — no ORM↔migration parity test to trip; the pytest suite is the only gate.
- **Determinism gate is enforced at review** (41.x, 42.1): 3× identical green counts with logged evidence; baseline after 42.1 = **1694 passed, 3 skipped**, ~6–7 min/run.
- **42.1 established the exact patterns 42.2 reuses**: `current_user`/outside-`_PUBLIC_ROUTES` posture, the groupless-tag vs untagged-model terminology discipline, one-query-no-N+1 count subqueries hitting `ix_model_tag_tag_model`, `feat(api):` single commit, native BMAD + Aider review, and the "planning-artifact drift resolved code-first + filed to triage, not a blocker" move (42.1 did it for the E42 removal-ownership gap; 42.2 does it for the §3211 `_PUBLIC_ROUTES` mislabel).

## Git Intelligence Summary

Recent commits: `0d9c2d4 feat(api): add facet-aware model filtering` (42.1), `caafbe7 docs(bmad): close story 42.1`, plus 41.x/TB-054 closeouts. Pattern: backend-only facet-tag increments landing story-by-story on `main` as `feat(api):`. 42.2 is the next backend read-API increment on that trajectory — expect a single `feat(api):` touching the three `sot` source files + tests, no migration, no frontend.

## Project Context Reference

No `project-context.md` in-repo. Vendor-neutral SoT is `AGENTS.md` (default-deny auth posture, TDD, 3× determinism, no silent scope creep); cross-repo catalog schema at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md`; observability/log + GlitchTip contracts under `~/repos/configs/docs/`. Managed Ponytail minimal-diff policy applies (smallest correct diff; no redundant `group` slug field — D-SHAPE-1) but never overrides the auth/test/architecture gates above.

## Resolved Decisions (self-validation 2026-07-19 — no dev-start open questions)

All eight controller contract questions were resolved code-first against approved sources + live code. They are **decisions, not questions** — do not re-open at dev-start.

| # | Controller question | Resolution |
|---|---|---|
| 1 | Exact `GET /api/tags` shape w/ and w/o `with_counts` | **D-SHAPE-1 / D-RESPONSEMODEL-1 / AC #1-3, #9.** Base: `{id, slug, name_en, name_pl, group_id, group_position}`; `with_counts=true` adds `model_count: int` (key absent otherwise). No `group` slug string. Realized via `response_model=list[TagListItem]` + a drop-when-None `@model_serializer` (probe-validated: exact keys **and** honest OpenAPI; `response_model=None` / `exclude_none` both rejected). |
| 2 | What does "count" mean (all / non-deleted / visible / other) | **D-COUNT-1 / AC #3.** Distinct **non-deleted** models (`Model.deleted_at IS NULL`), per `list_categories_tree` precedent; no visible/status scope exists. |
| 3 | Group embed shape + client compat | **D-SHAPE-1 / AC #1.** Additive `group_id`+`group_position` on shared `TagRead`; flows additively into model responses (intended, FR25-DETAIL-1); unknown-key-tolerant → compatible. |
| 4 | `/api/tag-groups` envelope/order/groupless/empty | **D-ENVELOPE-1 / AC #4.** `{groups, groupless}`; groups `(position, slug)`; tags `(group_position, slug)`; empty groups included with `tags: []`; groupless = sibling array of `group_id IS NULL` tags. |
| 5 | Hidden/deleted tag/group lifecycle | **D-LIFECYCLE-1.** No such columns on `Tag`/`TagGroup` → nothing to filter; all live. |
| 6 | Auth / public posture / portal_access | **D-AUTH-1 / AC #6-7.** `current_user` (any role), outside `_PUBLIC_ROUTES`; anonymous 401 / rogue 403; §3211 "public" mislabel not followed (code-falsifiable), filed to triage. |
| 7 | Query efficiency / no N+1 / pagination+search interaction | **AC #8.** Bounded queries: `with_counts` = +1 GROUP BY; `/tag-groups` = 3 queries, Python bucketing; `tag.group_id` index not needed for reads; `with_counts`∘`q`∘`limit` compose. |
| 8 | Consistency of counts across the two endpoints | **D-CONSISTENCY-1 / AC #5.** Single `_tag_model_counts` helper → identical by construction; asserted by a cross-endpoint test. |

### Deferred / cross-story notes (non-blocking, filed for `bmad-correct-course` / triage-backlog)

- **TB — architecture.md §3211 `_PUBLIC_ROUTES` mislabel.** The Decision-AW read-surface paragraph calls `GET /api/tags`/`/api/models`/`/api/tag-groups` "public catalog reads" that "must be added to `_PUBLIC_ROUTES`" and states `GET /api/categories` "must be deleted from the allowlist" — all three claims are contradicted by live code (`main.py:50-61` allowlist = health/auth/share only; `test_sot_auth_boundary.py` asserts anonymous-401 for these reads under Init 6 Decision M default-deny). Code-grounded, unambiguous → resolved in-story (D-AUTH-1, keep authenticated) and filed to `_bmad-output/triage-backlog.md` for a documentation-correction pass by `bmad-correct-course`. Not a blocker (AGENTS.md: code-grounded drifts are encoded in-story + filed, not escalated).
- **E41-retro `tag.group_id` index action item — partially discharged for reads.** `GET /api/tag-groups` fetches all tags in one query and buckets by `group_id` in Python (no `WHERE group_id = ?`), so no index is needed for this read pattern. The action item stays **open** for admin per-group queries (42.4) that may filter by `group_id`.
- **`group` slug on `TagRead` (D-SHAPE-1 deferral).** If a future consumer genuinely needs the group slug on the model-embedded tag (rather than resolving via `group_id` → `/api/tag-groups`), that is an additive product decision for E43/E45, not 42.2.

## Validation Record

**Workflow:** native `bmad-create-story` (BMAD 6.10, `bmm`), authored + self-validated in one pass (Claude author; Laura controller) · **Date:** 2026-07-19 · **Verdict: READY-FOR-DEV** (no dev-start blockers).

Sources inspected first-hand (not via prose): `AGENTS.md`, `CLAUDE.md`, managed `PONYTAIL.md`, `_bmad/_config/bmad-help.csv`, `sprint-status.yaml`, PRD §Initiative 25 (FR25-TAX-1/BROWSE-1/DETAIL-1 + NFR block), architecture.md §Initiative 25 Decision AW (lines 3156-3225), SCP §4.2/§4.3, `docs/design/HANDOFF-tagi-fasetowe.md`, and live code: `sot/router.py` (full), `sot/service.py` (full), `sot/schemas.py` (full), `_entities.py` (full), `admin_service.py:368-402` (count idiom), `main.py:50-61` (`_PUBLIC_ROUTES`), `tests/test_sot_tags.py`, `tests/test_sot_auth_boundary.py`, `tests/test_tag_group_entity.py`, `tests/test_sot_schemas.py:44-98`, and confirmed no `/tag-groups` route/`useTagGroups`/`with_counts` exists yet.

### Checklist (create-story quality gate)

- [x] Story maps to real FRs (FR25-TAX-1 / BROWSE-1 / DETAIL-1) with epic/SCP/PRD/architecture/HANDOFF traceability.
- [x] Every AC unambiguous and testable; no self-contradiction (all eight contract questions → ratified decisions).
- [x] All files-to-modify read first-hand; current-state notes accurate to line numbers.
- [x] Reuse over reinvention (extends `list_tags`/`TagRead`; one shared count helper; no new module/migration).
- [x] Regression fences explicit (additive `TagRead`; count subquery scope; no category/model-filter/frontend/migration leak).
- [x] Scope boundaries hard-fenced (read APIs only; 42.3/42.4/42.5/E43 out).
- [x] Auth posture code-grounded (default-deny `current_user`, outside `_PUBLIC_ROUTES`); §3211 drift resolved + filed, not invented.
- [x] Determinism gate carried (3× identical green; baseline 1694p/3s + new tests).
- [x] No template placeholders; no dev-start open questions.

### Remaining blockers

None. Story is implementation-ready.

## Independent Validation Record (native `bmad-create-story:validate`, 2026-07-19)

**Validator:** fresh independent native BMAD story validator (Claude; Laura controller). **Workflow:** native `bmad-help` → native `bmad-create-story:validate`. **Verdict: PASS (ready-for-dev)** after the edits below. Sources read first-hand (not via story prose): `sot/schemas.py`, `sot/service.py`, `sot/router.py` (full), `_entities.py:55-165`, `main.py:40-79`, `tests/test_sot_auth_boundary.py` (full), architecture.md §3156-3225 (Decisions AU/AV/AW), epics.md §42.2, SCP §4.2, `docs/design/HANDOFF-tagi-fasetowe.md` §3/§9, memory `initiative-25-facet-tags`. Two throwaway FastAPI 0.136 / Pydantic 2.13 runtime probes were run (no repo code modified).

**Findings & resolutions (critical 0 · important 1 · minor 3):**

1. **[IMPORTANT — resolved by edit] Response-model design violated AC #9.** The story's Task 3 prescribed `response_model=None` and claimed "FastAPI infers OpenAPI from the return annotation." **Probe-falsified:** `response_model=None` emits an empty `schema: {}` for the 200 response (annotation discarded) → an undocumented OpenAPI contract, contradicting AC #9. Also confirmed the controller's `response_model_exclude_none=True` candidate is **wrong** — it is global and strips `group_id: null` / `name_pl: null`, breaking AC #2's key set. **Encoded the smallest correct design (D-RESPONSEMODEL-1):** `response_model=list[TagListItem]` where `TagListItem(TagRead)` has `model_count: int | None = None` + a `@model_serializer(mode="wrap")` that drops `model_count` only when `None`. Probe-verified: exact keys both ways **and** a single honest OpenAPI component. Added an OpenAPI-honesty regression test to Task 4. `/api/tag-groups` keeps the separate required-count `TagReadWithCount`.

2. **[MINOR — verified + wording tightened] Auth posture (§3211 "public").** Verified `_PUBLIC_ROUTES` (`main.py:50-61`) = health/auth/share only; `test_sot_categories_anonymous_returns_401` proves categories was never allowlisted. Confirmed **no** approved source (PRD/SCP §4.2/HANDOFF) requests an anonymous catalog, and epics §42.2 explicitly directs "Outside `_PUBLIC_ROUTES` … confirm at create-story". Keeping `current_user` is the source-backed **and** non-downgrade posture; making the catalog anonymous would be an unrequested product/security decision. Not a genuine unresolved decision → **not BLOCKED**. Re-grounded AC #6 on four independent grounds (more-specific epic source, architecture line 3224 internal contradiction, §3211's false premise, no-source-requests-anonymity + safety) instead of "code outranks the decision." **TB-055** is the correct procedural artifact (doc-only `bmad-correct-course`), already open and accurately worded.

3. **[MINOR — resolved by edit] Group-label resolution contract (§3211/HANDOFF shape).** HANDOFF §2/§3 modelled a flat `group` slug on `TagRead`; architecture Decision AU superseded it with `TagGroup` + `group_id` FK. Verified no consumer needs the slug embedded: E44/E45 resolve `group_id → label` via the app-wide cached `useTagGroups()` map (zero extra per-tag query, no N+1). Stated the exact contract in D-SHAPE-1 (`group_id` canonical everywhere; labels only from `/api/tag-groups`) and noted the "hot-path join" justification is really one avoided `TagGroup` join, not an N+1.

4. **[MINOR — resolved by edit] No-N+1 was prose-only.** Added a concrete verification method (SQLAlchemy `before_cursor_execute` counter; cardinality-independence assertion) to AC #8 and a constant-query-count test to Task 4, so the no-N+1 claim is proven, not merely asserted.

**Independently verified as already-correct (no change needed):** count scope `Model.deleted_at IS NULL` mirrors `list_categories_tree` (`service.py:101-105`); `ModelTag` composite PK `(model_id, tag_id)` → `func.count()` = distinct models per tag (no double-count); constant query counts (with_counts +1; `/tag-groups` 3); envelope `{groups, groupless}` with empty groups included and groupless as a sibling array matches HANDOFF §9.4 "Inne" pseudo-facet + edge-case-08 nullable `group_id`; ordering `(position, slug)` / `(group_position, slug)`; `Tag`/`TagGroup` carry no lifecycle column (D-LIFECYCLE-1); additive `TagRead` fields are `from_attributes` zero-cost. Auth-boundary test extension (Task 4) and the 3× determinism gate are appropriate.

**Edits made (allowed artifacts only):** this story file (`42-2-tags-tag-groups-read-api.md`) — AC #2/#6/#9, Tasks 1/2/3/4, Dev Notes (D-RESPONSEMODEL-1 added, D-SHAPE-1 expanded), Resolved-Decisions table, this record. No production/test code, sprint-status, or TB-055 change was required (TB-055 already open and accurate; status stays `ready-for-dev`).

## Dev Agent Record

**Agent:** Claude (Opus 4.8, native BMAD `bmad-dev-story`) · **Controller:** Laura (owns review/commit/merge/deploy). **Branch:** `feat/E42.2-tags-tag-groups-read-api` from `main@6a6a116`. **Date:** 2026-07-19.

### Debug Log / execution trace

- Session-start `bmad-help` → canonical entry `bmad-dev-story` (preceded-by `create-story:validate`, done). Read AGENTS.md, CLAUDE.md, managed Ponytail, `project-context.md`, full story, sprint-status, and every named source/test file first-hand.
- **De-risked the binding D-RESPONSEMODEL-1 with a throwaway runtime probe** (Pydantic 2 / FastAPI): `TagListItem(TagRead)` + `@model_serializer(mode="wrap")` drop-when-None → confirmed exact key sets both ways (no-count omits `model_count`; `group_id`/`name_pl` nulls preserved; `model_count=0` kept) **and** a non-empty honest OpenAPI schema (`array` of `$ref TagListItem`, `model_count` as optional integer). No repo code touched by the probe.
- **Strict RED→GREEN TDD.** Wrote all tests first; captured RED before any production edit: collection `ImportError` for the new schema/service symbols + 5 behavioral failures (group fields, with_counts, OpenAPI honesty, tag-groups anon 404≠401, tag-groups role-200). Then implemented schemas → service → router; focused suite went green (56 passed). One iteration: OpenAPI test used `/openapi.json`; this app serves it at `/api/openapi.json` — corrected the test (not a product bug).
- **No-N+1 proven at the service layer** (per story guidance to isolate the read surface from auth/session overhead): `_count_selects` `before_cursor_execute` counter asserts `list_tag_groups` issues the same, ≤3 SELECTs for a 2×2 vs a doubled 4×4 seed (cardinality-independent), and `list_tags(with_counts=True)` = exactly one aggregate over the no-count path (`1 → 2`).
- Scope fences held: no admin CRUD, no category removal, no migration, no frontend, no model-filter/DTO change. The additive `TagRead` fields flow into `GET /api/models` responses (intended, AC #1) and did not regress any model list/detail test.

### Completion Notes

- **AC #1** — `TagRead` gains `group_id`/`group_position` (zero-cost `from_attributes`); additive, flows into model responses. **AC #2/#3** — `GET /api/tags?with_counts` via `TagListItem` (optional count + drop-when-None serializer): count-free shape omits `model_count`, count shape adds `int`; composes with `q`/`limit`. **AC #4** — new `GET /api/tag-groups` → `{groups, groupless}`, empty groups included (`tags: []`), group order `(position, slug)`, tag order `(group_position, slug)`, groupless sibling array. **AC #5** — single `_tag_model_counts` helper → counts identical across both endpoints (cross-endpoint test). **AC #6/#7** — both routes stay outside `_PUBLIC_ROUTES`; auth-boundary extended for `/api/tag-groups` (anon 401; agent/member/admin 200). **AC #8** — constant/bounded query count proven by SQLAlchemy event counter. **AC #9** — honest `response_model=list[TagListItem]` + OpenAPI-honesty regression test (no `response_model=None`); full `description=`/docstrings, no stale category wording. **AC #10** — ruff clean; backend suite **3× consecutive identical: 1718 passed, 3 skipped** (baseline 1694 + 24 new). Count scope = distinct non-deleted models (`Model.deleted_at IS NULL`, D-COUNT-1).
- Native BMAD `bmad-code-review`: **APPROVE** (0 Critical / 0 Important / 2 non-blocking Minor). Independent Aider diff review: **APPROVE**; its scale/ordering notes are future concerns, and both claimed missing tests were already present.
- Full repo closeout gate: `infra/scripts/check-all.sh` **16/16 all green**; visual stage **464 passed / 24 skipped**. Implementation committed as `3cf5a4b` with no scope bleed.

### File List

- `apps/api/app/modules/sot/schemas.py` — enrich `TagRead`; add `TagListItem`, `TagReadWithCount`, `TagGroupRead`, `TagGroupsResponse`.
- `apps/api/app/modules/sot/service.py` — add `_tag_model_counts`, `list_tag_groups`; extend `list_tags(with_counts=)` → `list[TagListItem]`.
- `apps/api/app/modules/sot/router.py` — `with_counts` param + `response_model=list[TagListItem]` on `GET /api/tags`; new `GET /api/tag-groups` route.
- `apps/api/tests/test_sot_tags.py` — group-fields, with_counts (+/soft-delete/zero), no-count key absence, OpenAPI honesty.
- `apps/api/tests/test_sot_tag_groups.py` — **new**: envelope, ordering, empty groups, groupless, count scope, cross-endpoint consistency, constant-query-count.
- `apps/api/tests/test_sot_auth_boundary.py` — `/api/tag-groups` anon-401 + agent/member/admin-200.
- `apps/api/tests/test_sot_schemas.py` — `TagRead` group round-trip; `TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse` shapes.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 42.2 → review.
- `_bmad-output/implementation-artifacts/42-2-tags-tag-groups-read-api.md` — tasks/DAR/File List/Change Log/status (this file).

## Change Log

| Date | Change |
|---|---|
| 2026-07-19 | Story 42.2 implemented on `feat/E42.2-tags-tag-groups-read-api` (RED→GREEN TDD). Read APIs only: `GET /api/tags` + `group_id`/`group_position`/`?with_counts`; new `GET /api/tag-groups` (`{groups, groupless}`, per-tag counts). No migration/frontend/category/admin change. Ruff clean; backend 3× 1718p/3s. Status → review. Left for Laura: independent review, commit, ff-merge, deploy. |
| 2026-07-19 | Controller closeout: native BMAD + Aider APPROVE; full `check-all.sh` 16/16 green; implementation commit `3cf5a4b`. Status → done, ready for ff-merge/push/deploy. |
