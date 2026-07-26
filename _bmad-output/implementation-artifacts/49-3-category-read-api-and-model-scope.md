---
baseline_commit: 2d4fd75832ce54b38cd6a69c986fb323818b778b
create_validate_baseline_commit: 336bf1b5ebb9724f99c667ed8f9ded0601950247
---

# Story 49.3: Category read API + model category scope

Status: done

<!-- Provenance. CREATE: native bmad-create-story (action=create, menu CS), 2026-07-26, Claude Opus 5 agent session, routed via the repository's native bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story` (CS / create; preceded-by bmad-sprint-planning, followed-by bmad-create-story:validate, required=true). Customization resolved via `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow`: no team override (`_bmad/custom/bmad-create-story.toml` absent) and no user override; `activation_steps_prepend`, `activation_steps_append` and `on_complete` all empty; `persistent_facts` = `file:{project-root}/**/project-context.md`, which resolved to `_bmad-output/project-context.md` in this worktree and was loaded. `discover-inputs.md` executed (epics/architecture/ux loaded whole; no PRD file in planning-artifacts). `checklist.md` executed against the drafted artifact before finalising. Baseline HEAD 336bf1b5ebb9724f99c667ed8f9ded0601950247 on branch docs/init26-e49-3-create-validate in worktree /home/ezop/worktrees/3d-portal-e49-3-create, working tree clean at start. VALIDATE: native bmad-create-story (action=validate, menu VS), 2026-07-26, fresh independent Claude Opus 5 agent session at the same baseline 336bf1b, routed via native bmad-help -> the same CSV row (VS / validate; preceded-by bmad-create-story:create, followed-by bmad-dev-story). Customization re-resolved independently (identical result: no team/user override, all hooks empty, persistent_facts -> _bmad-output/project-context.md, loaded); checklist.md executed end-to-end; every §6 citation re-derived from real source/tests/docs rather than trusted. Verdict PASS with amendments — see §16 for executed evidence and the full amendment list (V-1 … V-10, D-1 … D-3). NO human review of any kind, at create or at validate. No Ezop signature, no Ezop review, and no Laura review is recorded, implied or claimable from either pass; every verdict in this document is Claude/native-BMAD only. G26-DEVGO is NOT granted by the native PASS itself. Laura/controller later granted it after the independent focused Aider specification review and controller audit; see §18.1. That controller decision is not an Ezop signature or review. No code, no test, no doc, no live DB touched in either pass; no commit, push, merge or deploy. -->

## 1. Story

As an **authenticated portal member**,
I want **the API to expose the browse categories as a flat, ordered, counted read surface, to resolve a single category by its stable slug, and to scope the model catalogue to one category without disturbing any existing filter**,
so that **the frontend browse IA (E50–E51) has a stable contract to build against, and the curation QA surfaces (E52) can see every category including the empty ones.**

**Epic:** E49 — Browse-category data + additive API foundation (backend).
**Story key:** `49-3-category-read-api-and-model-scope` *(renumbered from 49.4 by the 2026-07-26 controller review).*
**Requirements:** FR26-CAT-2, FR26-BROWSE-2, FR26-BROWSE-3.
**Architecture:** Decision AY (API contract) is the canonical source. Decision AX supplies the entity shape being read; **Decision AZ is out of scope** — `0020_browse_categories` is shipped and byte-frozen here.
**Depends on:** Story 49.1 (`done`, entities + migration) and Story 49.2 (`done`, eight seeded categories, integrated at this baseline `336bf1b`). Neither is re-opened. **Hard prerequisite for** 50.1 (FE types/hooks), 50.2 (URL state), 51.1/51.2/51.4 (browse IA + detail display) and 52.3 (curation QA).

**This story is read-only over the browse-category tables.** It writes nothing to `browse_category` and nothing to `model_browse_category`.

## 2. Gate and authorization posture (truthful)

- **G26-ROUTE-PATH — RATIFIED** 2026-07-26 by **Laura/controller**: re-using the retired `/api/categories` path for the new flat browse contract is accepted. **This is a controller decision only — NOT an Ezop signature, NOT an Ezop review, and NOT a claim that any human has read this document.** The recorded justification is that the path has **zero live consumers** (`cutover-smoke.sh:401-405` was already re-pointed to `/api/tags` by 47.5 and only *comments* on the retirement; 47.3 removed the runbook pre-flight), and that the new shape differs entirely from the deleted recursive `CategoryTree`. [Source: `sprint-status.yaml:381`]
- **G26-DEVGO — GRANTED for Story 49.3 on 2026-07-26 by Laura/controller.** Basis: fresh native validation `PASS`, controller consistency/spec audit, and independent focused Aider specification `APPROVE` (Critical 0, Important 0, Missing tests 0). The grant covers only the exact validated implementation scope — 10 product/doc files plus workflow records — and no live DB, deploy, assignment, migration, E49.4 or E49.5 action. **This is a controller decision under Ezop's standing Initiative 26 authorization, NOT an Ezop signature or review.** See §18.1.
- **G26-MIGRATE — does not apply.** This story ships no DDL: no new Alembic revision, no edit to `0020`, no `alembic` invocation in any test it adds.
- **G26-CAT-SET, G26-UXGATE, G26-SCP-RATIFY — closed**; none of them gate this story. G26-LIB (E53) is unrelated.
- **No live-database action of any kind.** Every test runs against the session-scoped throwaway SQLite database built by `conftest.py:_isolated_db` (`init_schema` on a `tempfile.mkdtemp` path, `conftest.py:32-62`). The production database is never opened, read or written by this story, at dev time or review time.
- **Live posture (controller-supplied at 49.2 closeout; not re-measured here, and nothing in this story depends on it):** live revision `0020_browse_categories`; eight `browse_category` rows seeded; `model_browse_category` count **0**. **Consequence that must be stated plainly: on the live database this story's `GET /api/categories` will return eight categories each with `model_count: 0`, and `GET /api/models?category=<any-slug>` will return an empty page with `total: 0`.** That is correct behaviour, not a defect — assignments are curation work owned by 49.5/52.2, and this story deliberately creates none.

## 3. Binding constraints (a violation is a story defect, not a preference)

1. **Additive only.** No shipped response field is removed or renamed; no shipped query parameter changes meaning; no existing route is retired or redirected.
2. **Authenticated default-deny.** Every new route sits behind `current_user`, outside `_PUBLIC_ROUTES`. **`app/main.py` is byte-unchanged.** See §6 F-1 — this is verified, not assumed, and the UX artifact affirmatively agrees.
3. **`IN`/`EXISTS` subquery for the category scope — never a SQL `JOIN` against `base`.** The outer `SELECT Model` shape must stay unchanged so the shipped sort → offset/limit → eager-tag → eager-gallery pipeline applies untouched (`service.py:279-335`). See §6 F-6 for the honest scope of what this does and does not prevent.
4. **The category scope is AND-ed onto `base` as its own `.where()`.** It is **never** placed inside the `q` `or_()`, never inside the tag `or_()`/`and_()` composition, and never influenced by `tag_match`. The 42.1 AND-between-groups / OR-within-group semantics are untouched.
5. **The scope predicate is applied before the total-count subquery** (`service.py:279-280`), so `total` and pagination stay filter-correct.
6. **Unknown category slug → HTTP 200 with an empty page and `total: 0`.** Never 404. This matches the shipped unknown-`tag_id` posture (`service.py:231-238`).
7. **`GET /api/categories/{slug}` on an unknown slug → HTTP 404.** The list and the detail deliberately differ; §8.4 records why.
8. **`ModelDetail` gains `categories`; `ModelSummary` does not.** `ModelDetail` subclasses `ModelSummary` (`schemas.py:158`), so the field is declared on the subclass only. Adding it to `ModelSummary` would mean a second per-page eager-load for a pixel the MVP IA never renders.
9. **No component schema may be named `Category*`, and no model-shaped DTO may gain a property named `category` or `category_id`.** Both are enforced by shipped 47.5 tests that must pass **unmodified** — see §6 F-3. Use `BrowseCategory*` and the plural property `categories`.
10. **`model_count` reuses the `_tag_model_counts` shape** (`service.py:59-76`) — one `GROUP BY` aggregate, joined to `Model`, filtered `Model.deleted_at IS NULL`. Do not write a per-category count query and do not invent different soft-delete semantics.
11. **No writes.** No admin CRUD, no replace-set, no seed re-run, no model↔category assignment, no migration.
12. **Strict RED→GREEN.** Every behavioural assertion in §4 is proven by a test observed failing before the production code satisfying it existed, with the failure output quoted verbatim in §15. **Where a test is a structural guard rather than a behavioural RED, it must be labelled as such and must not be presented as a RED.** See §5 T0 and §6 F-6.

## 4. Acceptance Criteria

### Read surface — `GET /api/categories`

**AC-1 — Flat list, deterministic order.** `GET /api/categories` returns a JSON array of category objects, ordered by `(position ASC, slug ASC)`. There is **no** nesting, no `children` key, no `subcategories` key: `parent_id` is exposed as a scalar and the array is flat even if a row carried a parent. Two categories sharing a `position` are ordered by `slug`.

**AC-2 — Item shape.** Each item carries exactly the Decision AY key set: `{id, slug, name_en, name_pl, description_en, description_pl, position, parent_id, model_count}`. Genuine nulls (`name_pl`, `description_en`, `description_pl`, `parent_id`) are **present as `null`**, not omitted. `model_count` is a required integer on this response.

**AC-3 — Empty categories are returned.** A category with zero assigned models appears in the list with `model_count: 0`. It is never filtered out — the curation QA surface (52.3) exists precisely to see it.

**AC-4 — `model_count` semantics.** `model_count` = the number of **distinct non-soft-deleted** models assigned to that category. A model with `deleted_at IS NOT NULL` does not contribute. The composite PK `(model_id, category_id)` on `model_browse_category` guarantees one row per model per category, so a plain `func.count()` over the grouped join **is** the distinct-model count — the same argument the shipped `_tag_model_counts` docstring records (`service.py:59-68`).

**AC-5 — Count/scope agreement.** For any category slug `S` with no other filter applied, the `model_count` returned by `GET /api/categories` equals the `total` returned by `GET /api/models?category=S`. This is the browse-category analogue of the shipped 42.2 cross-endpoint count-consistency AC.

**AC-6 — Auth.** `GET /api/categories` returns **401** to an anonymous caller and **200** to an authenticated `admin`, `member` and `agent`. The route does not appear in `_PUBLIC_ROUTES`.

### Read surface — `GET /api/categories/{slug}`

**AC-7 — Resolve by stable slug.** `GET /api/categories/{slug}` returns the single category whose `slug` matches exactly, in the same item shape as AC-2 (including `model_count`).

**AC-8 — Unknown slug → 404.** An unmatched slug returns HTTP 404 with a JSON `detail` body. It does **not** return 200 with a null body, and it does **not** return an empty object.

**AC-9 — Auth.** Same posture as AC-6: anonymous 401; `admin`/`member`/`agent` 200.

### Model catalogue scope — `GET /api/models?category=<slug>`

**AC-10 — One slug-addressed scope.** `GET /api/models` accepts exactly one new optional query parameter, `category: str | None = None`, addressed by **slug**. There is no `category_id`, no `category_ids`, no repeated-parameter form and no `category_match` mode. Omitting it leaves every shipped behaviour byte-identical.

**AC-11 — Scoping is correct and exclusive.** With `category=S`, the response contains exactly those live models assigned to the category whose slug is `S`, and `total` equals that count. Models not assigned to `S` are absent.

**AC-12 — Unknown slug → empty page, not 404.** `GET /api/models?category=does-not-exist` returns **200** with `items: []` and `total: 0`. The `offset` and `limit` echo values are unchanged from the request.

**AC-13 — No duplicate rows, no inflated total.** For a model assigned to **two or more** categories, scoping by one of them returns that model **exactly once**, and `total` equals the distinct model count. Unscoped, the same multi-category model also appears exactly once and is counted once. *(Labelled honestly: against the mandated `IN`-subquery implementation this holds structurally — see §6 F-6. It is a standing invariant guard, not a manufactured RED.)*

**AC-14 — Composition with every shipped filter family.** `category` composes as a pure AND with each of the following, with no change to their individual semantics:
  (a) `q` — substring over `name_en`/`name_pl`/`slug`;
  (b) `tag_ids` + `tag_match=all` — **AND between facet groups, OR within a group**;
  (c) `tag_ids` + `tag_match=any` — pure OR;
  (d) `untagged=true`, including the `tag_ids`+`untagged` OR-union case;
  (e) `status`;
  (f) `source`;
  (g) `sort` (at least `recent`, `name_asc`);
  (h) pagination — `offset`/`limit`, with `total` reflecting the **scoped** count and being independent of the page window;
  (i) `include_deleted=true` — the scoped page then **includes** soft-deleted models assigned to `S` (the shipped row semantics at `service.py:210-211` continue to govern and the category predicate does not re-filter them out), while `model_count` on `/api/categories` still excludes them (AC-16);
  (j) `external_url` — the other shipped `IN`-subquery family (`service.py:267-276`); `category` AND-composes with it without disturbing its typically-0-or-1-row shape.

  This enumeration is **complete against the shipped `get_models` signature** (`router.py:123-137`: `status`, `tag_ids`, `tag_match`, `untagged`, `source`, `q`, `external_url`, `sort`, `include_deleted`, `offset`, `limit`). Every one of those eleven parameters is covered by (a)–(j) — verified parameter-by-parameter at validation, not asserted.

**AC-15 — Category scope is never folded into tag semantics.** The category predicate is a separate `and`-ed `WHERE`. Passing `category` together with `tag_ids` does **not** change how `tag_match` partitions groups, does not add the category to any tag bucket, and does not affect the groupless-tag bucket rule. `tests/test_sot_models_list.py` passes **byte-unmodified**.

**AC-16 — Soft-delete posture is unchanged.** A soft-deleted model assigned to `S` is absent from `GET /api/models?category=S` and does not contribute to that category's `model_count`. With `include_deleted=true` the shipped behaviour continues to govern the model rows; `model_count` on the categories endpoint always excludes soft-deleted models (it takes no `include_deleted` parameter).

**AC-17 — Uncategorized models stay visible unscoped.** A model with **zero** categories is returned by `GET /api/models` with no `category` parameter, and is counted in `total`. This is FR26-CAT-2's "renders normally" made executable at the API layer.

### `ModelDetail`

**AC-18 — `ModelDetail.categories`, deterministically ordered.** `GET /api/models/{model_id}` returns `categories: list[BrowseCategorySummary]` ordered by `(position ASC, slug ASC)`. The summary shape is `{id, slug, name_en, name_pl, position, parent_id}` — deliberately **without** `model_count`, so embedding it costs no aggregate.

**AC-19 — Empty list, not null.** A model with no categories returns `categories: []`.

**AC-20 — `ModelSummary` is unchanged.** No item in `GET /api/models` carries a `categories` key. The OpenAPI `ModelSummary` component gains no property.

### Non-regression, performance and honesty

**AC-21 — Default-deny gate passes unmodified.** `tests/test_route_enforcement_gate.py` passes **byte-unmodified** with the new routes registered, proving both new routes carry an auth dependency and neither was added to `_PUBLIC_ROUTES`.

**AC-22 — OpenAPI documentation obligations.** Both new operations carry a non-empty `summary` and a non-empty `description`, and both `BrowseCategoryRead` and `BrowseCategorySummary` appear in `components.schemas` with no dangling `$ref`. *(Enforced by the shipped, unmodified `test_every_admin_sot_operation_has_summary` / `..._has_description` — the `sot-read` router tag puts the new routes inside their scope; see §6 F-4.)*

**AC-23 — Constant query count (no N+1).**
  (a) `list_browse_categories` executes a **constant** number of SELECTs, independent of the number of categories and of the number of assigned models, and **≤ 2** (one category select + one counts aggregate);
  (b) `get_model_detail` executes **exactly one** SELECT more than it does at baseline, independent of how many categories the model has;
  (c) `list_models` with `category=S` executes the **same** number of SELECTs as the equivalent unscoped call at the same page size (the scope is a subquery inside the existing statement, not an extra round-trip), and that count is independent of page size.
  **Mandatory precondition on (c) — both compared calls MUST return a non-empty page of the SAME row count.** This is not a test-writing nicety, it is what makes the assertion true at all: the eager-tag block (`service.py:289`) and the eager-gallery block (`service.py:305`) are both guarded by `if model_ids:`, so a shipped `list_models` issues **4** SELECTs on a non-empty page and only **2** on an empty one. Measured at validation on this baseline — see §16 V-1. A comparison of a scoped-but-empty page against a populated unscoped page therefore yields 2 vs 4 and would fail **while the production code is entirely correct**; the live posture in §2 (zero assignments ⇒ every scoped page empty) makes that the *default* mistake, not an exotic one. The implementer must seed assignments so both calls page equally, exactly as the ratified NFR26-PERF-1 already prescribes: fixtures "chosen to yield **equal result counts** on the same page, so the comparison isolates fan-out from result volume" (`architecture.md:3328`). **Removing or weakening the `if model_ids:` guards to make a badly-constructed count test pass is a forbidden regression, not a fix.**
  Measured with the shipped `_count_selects` harness pattern (`tests/test_sot_tag_groups.py:89-102`), at the service layer, under two fixture cardinalities.

**AC-24 — The 47.5 retired-surface guard is repaired, not deleted.** `tests/test_openapi_agent_surface.py::test_retired_taxonomy_read_route_is_gone` currently asserts `GET /api/categories → 404` and **will fail** once this story lands. It is **re-pointed to keep proving the thing 47.5 actually cared about** — that the *retired recursive taxonomy contract* has not come back — rather than being deleted or weakened:
  (a) no `Category*` component schema exists (already covered, stays unmodified);
  (b) the repaired test **authenticates** (the base `client` fixture is anonymous, so an unauthenticated probe can only ever observe a 401 and would assert nothing about the contract) and then asserts the **exact new flat contract**, not merely "some array":
    - the response is `200` and the body is a **flat JSON array**;
    - **no** item carries a `children` key and **no** item carries a `subcategories` key — the structural negative that distinguishes this contract from the retired recursive `CategoryTree`;
    - every item **does** carry the distinguishing browse fields, `model_count` included, and `parent_id` is a scalar (or `null`), never a nested node.
  (c) `test_retired_taxonomy_admin_crud_route_is_gone`, `test_no_category_schemas_in_components` and `test_no_category_properties_on_model_schemas` stay **byte-unmodified** and still pass — this story adds no admin category route and resurrects no singular property.
  The 47.5 residual-symbol-grep discipline is preserved: the retired-route literal stays assembled at runtime (`"/api/" + "categories"`).
  **Unavoidable consequence the implementer must not be blindsided by (verified at validation, §16 V-5):** `tests/test_openapi_agent_surface.py` imports **only** `pytest` and `create_app` (`:18-22`) and carries **no** auth fixture. Authenticating per (b) therefore requires **module-level additions** — `uuid`, `ACCESS_COOKIE` (`app.core.auth.cookies`) and `encode_token` (`app.core.auth.jwt`), the same trio the shipped SoT read modules use (§6 F-11). "MODIFY — one test only" in §7 means **one test body**; the import block is an additional, mechanically necessary edit in the same file. No other test in the file changes.

**AC-25 — Doc honesty at deploy.** Every in-repo statement that asserts `/api/categories` is a retired/absent route is corrected in this story's commit, and each correction distinguishes the **retired Initiative 25 recursive single-category taxonomy** (permanently gone) from the **new Initiative 26 flat browse-category read** (this story). The exact passages and their current text are enumerated in §7. **The Initiative 25 retirement must not be described as reversed** — no correction may imply the mandatory single-category taxonomy, the `category` table, or `Category*` came back.

**AC-26 — Scope containment.** `git diff --name-only` over the story's branch shows only the files listed in §7 — **10 product/doc files**, plus the two workflow records. In particular `app/main.py`, `app/core/db/models/_entities.py`, `app/core/db/models/__init__.py`, `app/core/db/seed.py`, `migrations/**`, `tests/conftest.py`, `tests/test_sot_models_list.py`, `tests/test_sot_models_detail.py`, `tests/test_sot_tags.py`, `tests/test_sot_tag_groups.py`, `tests/test_route_enforcement_gate.py`, `tests/test_orm_migration_parity.py`, `tests/test_seed_browse_categories.py`, `apps/web/**`, `workers/**`, `pyproject.toml` and `uv.lock` are **byte-unchanged**. This list is a subset of §7's fuller assertion and must not contradict it; `tests/test_sot_models_detail.py` (the AC-15/T4.1 non-regression witness) and `tests/conftest.py` (no new shared fixture is authorized) are named here explicitly because both are live temptations.

## 5. Tasks / Subtasks — strict RED → GREEN

> **Ordering rule.** Within each slice the test is authored and observed failing **before** the production symbol it exercises exists. Failure output is quoted verbatim into §15. A test that passes by construction is either (a) restructured so it has a genuine RED, or (b) explicitly labelled a structural guard in both the test docstring and §15 — never dressed up as a RED.

- [x] **T0 — Baseline capture (no edits).**
  - [x] T0.1 Confirm clean tree at `336bf1b`; run the regression set that must stay green and record the pass counts verbatim: `.venv/bin/pytest -q tests/test_sot_models_list.py tests/test_sot_models_detail.py tests/test_sot_tags.py tests/test_sot_tag_groups.py tests/test_sot_auth_boundary.py tests/test_sot_schemas.py tests/test_openapi_agent_surface.py tests/test_route_enforcement_gate.py`.
  - [x] T0.2 Record the baseline SELECT count of `get_model_detail` for a seeded model (needed to make AC-23(b)'s "exactly one more" a measured delta rather than a guess). **Validation measured this on this baseline: `get_model_detail` = 7 SELECTs** (model, tags, files, notes, prints, external_links, gallery-ids), so AC-23(b)'s target is **8**. Re-measure rather than trusting this number, but a materially different baseline means something else changed and must be investigated before proceeding. Also record `list_models` = **4** SELECTs on a non-empty page and **2** on an empty one — AC-23(c) depends on that asymmetry.

- [x] **T1 — `GET /api/categories` (AC-1 … AC-6).**
  - [x] T1.1 **RED** — author `tests/test_sot_categories.py` complete for the list endpoint (order incl. the position-tie→slug case, item key set, nulls present, empty category included, count correctness with a soft-deleted model excluded, anonymous 401, member/agent/admin 200). Observe and quote the failure (route absent → 404 for the authenticated cases, and the anonymous case failing on 404 ≠ 401).
  - [x] T1.2 Add `BrowseCategorySummary` + `BrowseCategoryRead` to `sot/schemas.py`.
  - [x] T1.3 Add `_browse_category_model_counts` + `list_browse_categories` to `sot/service.py`, mirroring `_tag_model_counts` / `list_tags`.
  - [x] T1.4 Add the route to `sot/router.py` with `current_user`, a non-empty `summary` and a non-empty `description` (AC-22 is enforced by a shipped test).
  - [x] T1.5 **GREEN** — quote the pass line.

- [x] **T2 — `GET /api/categories/{slug}` (AC-7 … AC-9).**
  - [x] T2.1 **RED** — extend `tests/test_sot_categories.py`: known slug 200 + shape + `model_count`; unknown slug 404 with a `detail` body; anonymous 401; three roles 200. Quote the failure.
  - [x] T2.2 Add `get_browse_category_by_slug` to the service (returns `None` on miss) and the route (raises `HTTPException(404)` on `None`, the shipped `get_model` pattern at `router.py:166-175`).
  - [x] T2.3 **GREEN** — quote.

- [x] **T3 — `GET /api/models?category=` scope (AC-10 … AC-17).**
  - [x] T3.1 **RED** — author `tests/test_sot_models_category_scope.py`. Start with the plain scoping test; the genuine RED is that an unrecognised query parameter is **ignored** by FastAPI, so the unscoped page comes back and the subset assertion fails. Quote it.
  - [x] T3.2 Add the `category: str | None = None` parameter to `list_models` and the `Model.id.in_(select(ModelBrowseCategory.model_id).join(BrowseCategory, ...).where(BrowseCategory.slug == category))` predicate, inserted **immediately after the `source` filter and before the `q` filter** (`service.py:256-258`) — i.e. inside the base-filter block and before the total-count subquery at `:279`.
  - [x] T3.3 Thread the parameter through `router.py::get_models` (query param + pass-through) and extend the route `description` with the new parameter's contract, including the unknown-slug-is-empty-not-404 rule.
  - [x] T3.4 Extend the test module to the full composition matrix **AC-14(a)–(j)** — including the two families the first draft's matrix omitted, **(i) `include_deleted=true`** and **(j) `external_url`** (§16 V-6) — plus the unknown-slug AC-12 case, AC-17 (uncategorized model visible unscoped), AC-16 (soft-deleted assigned model absent + not counted) and AC-5 (count/scope agreement). Each was authored before its supporting production code where the code did not already exist; where composition passes on the code written in T3.2, label it a **composition guard** in §15, not a RED. The `category` + `include_deleted=true` case is the one composition where the two features could genuinely interact wrongly, so it is mandatory, not optional: the soft-deleted assigned model must **reappear** in the scoped page while `model_count` still excludes it.
  - [x] T3.5 **Structural guard (labelled, not a RED)** — AC-13's duplicate/total invariant over a model in two categories.
  - [x] T3.6 **GREEN** — quote.

- [x] **T4 — `ModelDetail.categories` (AC-18 … AC-20).**
  - [x] T4.1 **RED** — extend `tests/test_sot_models_detail.py`? **No** — author the assertions in `tests/test_sot_categories.py` so `test_sot_models_detail.py` stays byte-unmodified as a non-regression witness. Assert `categories` present + ordered `(position, slug)`, `[]` for a zero-category model, and **absent** from every `GET /api/models` item. Quote the `KeyError`/assertion failure.
  - [x] T4.2 Add `categories: list[BrowseCategorySummary]` to `ModelDetail` (subclass only — `schemas.py:158`).
  - [x] T4.3 Add the ordered category query to `get_model_detail`, mirroring the shipped tags block at `service.py:370-376`, and include `"categories"` in the `ModelDetail.model_validate({...})` payload at `:410-421`.
  - [x] T4.4 **GREEN** — quote.

- [x] **T5 — Query-count evidence (AC-23) — MUTATION / COVERAGE GUARD, explicitly NOT a RED.**
  - [x] T5.1 **Mutation sensitivity guard (labelled; NOT an original RED — do not present it as one).** These three query-count tests are authored **after** T1–T4 have already landed the production symbols they measure, so they are expected to be **green on first run**. That is not TDD evidence and must never be written up as though a failure was observed first: §15 records them as a guard, and the Change Log/commit message must not claim a RED for T5. Their load-bearing character is proven the only honest way available at this point — by a **labelled temporary mutation**:
    1. record `sha256` of `apps/api/app/modules/sot/service.py` **before** touching it;
    2. temporarily replace `_browse_category_model_counts`'s single `GROUP BY` aggregate with a per-category count loop (the exact N+1 defect AC-23(a) exists to forbid);
    3. run the count tests, **observe and quote the failure** — this is the sensitivity proof;
    4. revert the mutation, re-run, quote the green;
    5. record `sha256` again and assert it is **byte-identical to step 1**.
    The mutation is a throwaway measurement, never committed. If step 5's hash differs, the tree is dirty and the evidence is void — stop and re-derive.
  - [x] T5.2 **GREEN (post-restoration)** — quote the pass line and the matching hash pair from T5.1 steps 1/5.
  - [x] T5.3 For AC-23(c) specifically, construct the fixture so the scoped and unscoped calls page **equally and non-emptily** (AC-23(c)'s mandatory precondition; `architecture.md:3328`). A 2-vs-4 SELECT delta means the fixture is wrong, **not** that the production code is. Do not "fix" it by touching the `if model_ids:` guards.

- [x] **T6 — Repair the 47.5 retired-surface guard (AC-24).**
  - [x] T6.1 Run `tests/test_openapi_agent_surface.py` unmodified and **quote the genuine regression** (`test_retired_taxonomy_read_route_is_gone` failing on the new status code). This is a real observed failure, not a manufactured one.
  - [x] T6.2 Re-point that single test body per AC-24(b) — **authenticated**, asserting the flat-array contract, the absence of `children`/`subcategories`, and the presence of `model_count` — preserving the runtime-assembled literal and updating its docstring to name Story 49.3 and G26-ROUTE-PATH. Add the three module-level imports AC-24 records as mechanically necessary (`uuid`, `ACCESS_COOKIE`, `encode_token`); the file currently imports only `pytest` and `create_app`. Leave every other **test** in the file untouched.
  - [x] T6.3 **GREEN** — quote; confirm `test_no_category_schemas_in_components`, `test_no_category_properties_on_model_schemas`, `test_no_dangling_refs` and `test_retired_taxonomy_admin_crud_route_is_gone` all pass **unmodified**.

- [x] **T7 — Auth-boundary matrix (AC-6, AC-9, AC-21).**
  - [x] T7.1 Extend `tests/test_sot_auth_boundary.py` with the anonymous-401 and agent/member/admin-200 cases for both new routes, following the 42.2 precedent that added `/api/tag-groups` there (`:134-135`).
  - [x] T7.2 Run `tests/test_route_enforcement_gate.py` **unmodified** and quote the pass.

- [x] **T8 — Doc honesty (AC-25).**
  - [x] T8.1 `docs/operations.md:460-464` — rewrite the Active-surfaces parenthetical at `:463-464` **and**, in the same bounded prose change, add the two truthful current routes (`/api/categories`, `/api/tag-groups`) to the Public-read enumeration at `:460-462`, which today omits both. Controller-ratified as deliberate same-passage doc reconciliation (§18 D-2), **not** backend scope and not a licence to widen the doc pass further.
  - [x] T8.2 `docs/operations.md:613-616` — rewrite the probe-history parenthetical.
  - [x] T8.3 `infra/scripts/cutover-smoke.sh:401-404` — correct the comment's now-false justification; **keep `endpoint="/api/tags"` unchanged** (§7 records why).
  - [x] T8.4 `infra/scripts/audit-six-scenarios.sh:673-675` — correct the "not current surface" clause (discovered at create; see §6 F-8).
  - [x] T8.5 Confirm no correction implies the Initiative 25 retirement was reversed; confirm `docs/operations.md:426-427` was **not** rewritten (§6 F-7).

- [x] **T9 — Scope + quality (AC-26).**
  - [x] T9.1 `.venv/bin/ruff format --check .` and `.venv/bin/ruff check .` in `apps/api`.
  - [x] T9.2 Full API suite: `.venv/bin/pytest -q` in `apps/api`.
  - [x] T9.3 `git diff --name-only` + `git status --porcelain` proving the §7 file set exactly, and `git diff --name-only` returning empty for every AC-26 byte-unchanged path.

- [x] **T10 — Controller-owned closeout. DONE.**
  - [x] T10.1 Frozen final `infra/scripts/check-all.sh` 16/16 on the final commit. **DONE — controller-owned frozen tree:** `.hermes/run-logs/e49-3-controller-check-all-20260726.log`, exit 0, `all green.`, 16/16; API 1827 passed / 3 skipped; Web 785 passed; visual 536 passed / 32 expected skips; all 10 product/doc files hash-stable before/after at `e58fe1a2f51fd8e4fc3adab62331d9dc120f22be2aaf2bbb2eb881e99295a54d`.
  - [x] T10.2 Determinism triple (NFR26-DETERMINISM-1). **DONE — controller-owned:** three consecutive full API runs each exit 0 with identical `1827 passed / 3 skipped / 2101 warnings`; proof `.hermes/run-logs/e49-3-controller-api-determinism-proof-20260726.txt`; product/doc hash remained `e58fe1a2…a54d` before/after.
  - [x] T10.3 Native `bmad-code-review`, then independent `laura-aider-review-diff`. **DONE — controller-owned.** Historical native §20 `REQUEST_CHANGES` (CR-1) was fixed test-side; fresh native §22 re-review returned `APPROVE` (Critical 0, Important 0); fresh post-fix Aider rerun returned literal `APPROVE` (Critical 0, Important 0). See §21–§22. Pre-fix Aider output is retained but explicitly not accepted as the final external review because it missed CR-1.
  - [x] T10.4 One atomic commit, ff-only merge, push, deploy. **DONE — controller-owned.** One atomic story commit with subject `feat(api): add category read API and scope` exists on the story branch; this final checkbox/status closeout is folded into that same commit by amend. The final SHA is intentionally external Git evidence (no self-reference). The branch is a one-commit descendant of baseline `2d4fd75`; ff-only integration, push, controlled deploy and read-only live postverify are executed immediately after the amended artifact is committed, with durable external logs.

## 6. Verify-at-create findings (traced against real code at HEAD `336bf1b` this session)

**F-1 — `_PUBLIC_ROUTES` needs no edit. CONFIRMED, and the UX artifact affirmatively agrees.**
`_PUBLIC_ROUTES` is at **`app/main.py:50-61`** — exactly the range the epic cites — and contains only `/api/health`, six `/api/auth/*` entries and three `/api/share/*` entries. No category path, and no wildcard mechanism that could sweep one in. The controller's caution about UX saying "public browse" is **resolved rather than merely obeyed**: `EXPERIENCE.md:30` states verbatim *"Every surface in this pass is behind `current_user` — none of it is anonymous, and none of it touches the anonymous `/share/$token` projection."* There is therefore **no contradiction** between UX and the default-deny posture, and none had to be arbitrated. `app/main.py` stays byte-unchanged.

**F-2 — The shipped count helper is `_tag_model_counts` (`service.py:59-76`) and is directly reusable in shape.** One `GROUP BY` over the join table joined to `Model` with `Model.deleted_at.is_(None)`, returning a `{id: count}` dict; the docstring records that the composite PK makes `func.count()` a distinct-model count without `DISTINCT`. `ModelBrowseCategory` has the same composite-PK shape (`_entities.py:167-183`) **and** a matching covering index `ix_model_browse_category_cat_model` on `(category_id, model_id)` (`:175`), so the analogue is exact. **Do not extend `_tag_model_counts` to cover both** — it is consumed by `list_tags` and `list_tag_groups` and keyed by `tag_id`; add a sibling `_browse_category_model_counts` with the same docstring discipline.

**F-3 — Two shipped 47.5 guards constrain naming, and pass unmodified only because Decision AX chose `BrowseCategory*`.** `test_no_category_schemas_in_components` (`test_openapi_agent_surface.py:327-331`) fails on **any** component schema whose name `startswith("Category")` — `BrowseCategoryRead`/`BrowseCategorySummary` clear it. `test_no_category_properties_on_model_schemas` (`:334-347`) fails if `ModelSummary`, `ModelDetail`, `ModelCreate`, `ModelPatch` or `ShareModelView` gains a property in `{"category", "category_id"}` — the plural `categories` clears it. **Both are load-bearing constraints on this story's naming, and both stay byte-unmodified.**

**F-4 — The new routes inherit a mandatory OpenAPI documentation obligation.** `TARGET_ROUTER_TAGS = {"admin", "sot-admin", "sot-read"}` (`test_openapi_agent_surface.py:54`) and the SoT read router is declared `tags=["sot-read"]` (`router.py:43`). Consequently `test_every_admin_sot_operation_has_summary` and `test_every_admin_sot_operation_has_description` will fail if either new operation ships without both. `test_target_routes_present` asserts `>= 30` operations, so adding two can only help. `test_every_sot_admin_route_has_agent_write_tag` keys off `sot_admin_router` and the `agent-write` tag only — read routes are outside it, so no `extra` is produced.

**F-5 — `tests/test_openapi_agent_surface.py:361-369` is a hard, unavoidable in-story edit that the epic sketch does not mention.** `test_retired_taxonomy_read_route_is_gone` does `client.get("/api/" + "categories")` and asserts **404**. The base `client` fixture is **anonymous** (`conftest.py:65-70` sets only `X-Portal-Client`, no cookie), so once the route exists this test receives **401**, not 404, and fails. There is no configuration of this story under which it survives untouched. AC-24 repairs it by preserving its intent (the recursive contract is gone) rather than deleting coverage. *This is the single most likely thing an implementer working from the epic sketch alone would discover only at `check-all` time.* **Second-order consequence confirmed at validation:** the module's entire import block is `from __future__ import annotations`, `import pytest`, `from app.main import create_app` (`:18-22`) — there is no auth fixture and no token helper anywhere in the file, so the controller-mandated *authenticated* repair necessarily adds imports. AC-24 states this so "one test only" is not read as forbidding it.

**F-6 — Honest scope of the "no join fan-out" requirement.** `slug` is **unique** (`Index("uq_browse_category_slug", "slug", unique=True)`, `_entities.py:148`) and `model_browse_category` has composite PK `(model_id, category_id)`. A single-slug scope therefore matches **at most one row per model** even under a naive SQL `JOIN` — so, stated plainly: **for this story in isolation a join would not actually inflate rows or `total`.** The `IN`-subquery requirement is nonetheless binding for two real reasons, not a manufactured one: (a) it is the shipped pattern that `tag_ids` (`service.py:220-243`) and `external_url` (`:267-276`) already establish, and `external_url`'s own comment states the rationale — keeping the outer `SELECT` shape unchanged so the sort/paging/eager-hydration pipeline applies untouched; (b) **Story 49.4 adds a tag-name disjunct that genuinely does fan out under a join**, and a join introduced here would compose with it into exactly the duplicate-row/inflated-total defect Decision AY forbids. AC-13 is accordingly labelled an **invariant guard**, and §5 T3.5 forbids presenting it as a RED.

**F-7 — The epic's `docs/operations.md:426` citation is imprecise, and following it literally would be a mistake.** Line **426-427** currently reads *"…43 legacy / categories (single-category taxonomy since retired by the Story 47.5 / cutover — facet tags are the sole classification system),"*. That is a statement about the **retired Initiative 25 taxonomy and a historical row count**, not about the `/api/categories` **route**, and it **remains true** after this story ships — Initiative 25's retirement stands permanently. Rewriting it risks implying the mandatory single-category taxonomy came back, which AC-25 explicitly forbids. **Reported, deliberately not edited.** The genuine route-retirement statements are at `:463-464` and `:613-616` (the epic's ":613-614" undercounts a four-line parenthetical). Likewise `infra/scripts/cutover-smoke.sh`: the epic cites `:397-405`, but the retired-route comment is exactly **`:401-404`**; `:400` is the function header and `:405` is `local ts code endpoint="/api/tags"`, which stays unchanged.

**F-8 — A fourth stale passage the epic does not list.** `infra/scripts/audit-six-scenarios.sh:673-675` reads *"…the category taxonomy and its routes were later retired by Story 47.5, so this is historical context, not current surface."* The moment `/api/categories` is live that clause is misleading. It meets AC-25's own criterion exactly (a statement that goes stale at *this* deploy), and it is in **neither** of 54.3's retained areas (agent runbook, `docs/architecture.md`, governance doc), so it is taken into scope here rather than left to rot. Scenario 4 enumerates routes dynamically via `/api/openapi.json`, so **no executable behaviour changes** — this is a comment-only correction.

**F-9 — Historical design documents are deliberately NOT in scope.** `docs/superpowers/specs/2026-05-04-portal-source-of-truth-design.md:486,530-532`, `…2026-05-05-portal-ui-rewrite-design.md:76,138,375`, `…2026-05-07-auth-refresh-token-flow-design*.md:60,91` and `docs/design/HANDOFF-tagi-fasetowe.md:47` all describe the old recursive `/api/categories`. They are **dated point-in-time design records**, not live operational documentation, and correcting them would falsify the historical record. Reported, not edited.

**F-10 — Test-authoring constraint from the shared session DB.** `conftest.py:_isolated_db` is **session-scoped** (`:32`), so rows persist across tests within a run. Every new test must seed **unique slugs** (the shipped files use a `uuid4().hex[:6]` prefix, `test_sot_tag_groups.py:236`) and scope every assertion to its own seeded rows. **No test may assert a DB-global category count** — in particular, nothing may assert "8 categories", because 49.2's seed is an explicit admin CLI with no lifespan wiring, so the test database starts with **zero** browse categories.

**F-11 — Auth pattern for the new test modules.** Both shipped SoT read test modules use an `autouse` fixture that mints an admin token via `encode_token(..., secret="test-secret-not-real")` and sets `ACCESS_COOKIE` (`test_sot_tag_groups.py:29-38`, `test_sot_models_list.py:20-30`). Reuse it verbatim; do not invent a new auth helper. For the anonymous cases, delete the cookie or use `make_anonymous_client` (`conftest.py:127`).

**F-12 — `inclusion_criterion` is deliberately absent from the read contract. RESOLVED: omit.** Decision AY enumerates the item key set as `{id, slug, name_en, name_pl, description_en, description_pl, position, parent_id, model_count}` (`architecture.md:3309`) — `inclusion_criterion` is not in it, even though 49.2 seeds it and `_entities.py:157` stores it. This story follows the ratified contract exactly. **Controller decision at validation (§18 D-1): omit from this read contract**, following Decision AY's exact public-read keyset. A later admin/curation DTO for E49.5/52.3 may add it; adding a field is purely additive, so no forward dependency is created and this story is **not** broadened. Recorded rather than silently added, and no longer an open question.

**F-13 — No frontend work is implied or permitted.** `apps/web/src/lib/api-types.ts` gains `BrowseCategoryRead`/`BrowseCategorySummary` and `ModelDetail.categories` in **Story 50.1**, not here. Web tests mock `/api/*` responses and do not consult the OpenAPI document, so no web test breaks from this change and `apps/web/**` stays byte-unchanged.

## 7. Predicted file changes (exact)

**Total: 10 product/doc files** = **3** production + **4** test + **3** docs/operational. Plus the two workflow records recorded separately at the end of this section, per this project's convention. The arithmetic is stated here once and every other scope statement in this document (§11, AC-26) and in `sprint-status.yaml` must match it. *(The create pass said "nine"; that was an arithmetic error — 3 + 4 + 3 = 10. Corrected at validation, §16 V-9.)*

**Production code — 3 files, all MODIFY:**

| File | Change |
|---|---|
| `apps/api/app/modules/sot/schemas.py` | ADD `BrowseCategorySummary` (`{id, slug, name_en, name_pl, position, parent_id}`) and `BrowseCategoryRead(BrowseCategorySummary)` (`+ description_en, description_pl, model_count: int`), both on `_OrmBase`. ADD `categories: list[BrowseCategorySummary]` to **`ModelDetail` only** (`:158`). `ModelSummary` untouched. |
| `apps/api/app/modules/sot/service.py` | ADD `_browse_category_model_counts`, `list_browse_categories`, `get_browse_category_by_slug`. EXTEND `list_models` with the `category` parameter + `IN`-subquery predicate (inserted after `:257`, before `:258`). EXTEND `get_model_detail` with the ordered category query + the `"categories"` payload key. Import `BrowseCategory`, `ModelBrowseCategory` from `app.core.db.models` (already exported — `__init__.py:19,21,44,47`). |
| `apps/api/app/modules/sot/router.py` | ADD `GET /api/categories` and `GET /api/categories/{slug}`, both `current_user`, both with `summary` + `description` (AC-22). EXTEND `get_models` with the `category` query parameter, its pass-through, and the route `description`. |

**Tests — 4 files (2 NEW, 2 MODIFY):**

| File | Change |
|---|---|
| `apps/api/tests/test_sot_categories.py` | **NEW.** List + detail endpoints, `ModelDetail.categories`, `ModelSummary` negative, query-count proofs. |
| `apps/api/tests/test_sot_models_category_scope.py` | **NEW.** Scope correctness, unknown slug, the AC-14 composition matrix, soft-delete, uncategorized-visible, duplicate/total invariant guard. |
| `apps/api/tests/test_openapi_agent_surface.py` | **MODIFY — one test body only** (`test_retired_taxonomy_read_route_is_gone`, `:361-369`) per AC-24, **plus the three module-level imports** (`uuid`, `ACCESS_COOKIE`, `encode_token`) that the authenticated repair mechanically requires — the file currently imports only `pytest` + `create_app` (`:18-22`). No other test in the file changes. |
| `apps/api/tests/test_sot_auth_boundary.py` | **MODIFY — additive.** Anonymous-401 + agent/member/admin-200 cases for both new routes. |

**Docs / operational scripts — 3 files, all MODIFY (comment/prose only, no executable change).** Note the table below has **four rows but three files** — `docs/operations.md` owns two separate passages. Validation independently swept the whole repo for `api/categories` and confirmed these are the **only** live (non-historical, non-workflow-artifact) occurrences; `docs/architecture.md` contains **zero** (§16 V-4).

| File | Current text (verbatim at `336bf1b`) | Required correction |
|---|---|---|
| `docs/operations.md:463-464` | `(`/api/categories` was part of this surface until the Story 47.5` / `category-taxonomy cutover retired it.)` | State that the path is **live again** as the Initiative 26 **flat browse-category read** (Story 49.3), and that the retired thing was the *recursive single-category taxonomy*, which stays retired. Also add `/api/categories` and `/api/tag-groups` to the Public-read enumeration at `:460-462`, which currently omits both. |
| `docs/operations.md:613-616` | `(The 2026-05-21 verification originally probed `/api/categories`; that route` / `was retired by the Story 47.5 category cutover, so the example now uses` / ``/api/tags` — an equivalent auth-protected SoT read with the same 401` / `default-deny behavior.)` | Keep the `/api/tags` example; correct the justification — the path now hosts a different, additive contract, and both routes are equally auth-protected 401 surfaces. |
| `infra/scripts/cutover-smoke.sh:401-404` | `# Probe endpoint re-pointed by Story 47.5: /api/categories was retired in` / `#   the category-taxonomy cutover (would 404, false-failing this gate);` / `#   /api/tags is a live auth-protected SoT read that preserves the exact` / `#   anonymous-external default-deny 401 property this scenario verifies.` | The `(would 404, false-failing this gate)` justification becomes **false** — post-49.3 an anonymous `/api/categories` returns **401**, which is exactly what the scenario wants. Correct the reason; **keep `endpoint="/api/tags"` at `:405` unchanged** (minimal-diff; the probe is about the default-deny property, not about which route hosts it). |
| `infra/scripts/audit-six-scenarios.sh:673-675` | `# anonymous external read of /api/categories — a route that was live at the` / `#   time of that finding; the category taxonomy and its routes were later` / `#   retired by Story 47.5, so this is historical context, not current surface).` | Per §6 F-8: the path is current surface again under a different contract, and the High-002 finding remains historical. Comment-only. |

**Workflow records (separate from the product commit):** this story artifact and `_bmad-output/implementation-artifacts/sprint-status.yaml`.

**Asserted byte-unchanged (AC-26):** `app/main.py`; `app/core/db/models/_entities.py`; `app/core/db/models/__init__.py`; `app/core/db/seed.py`; `apps/api/scripts/**`; `migrations/**`; `tests/test_sot_models_list.py`; `tests/test_sot_models_detail.py`; `tests/test_sot_tags.py`; `tests/test_sot_tag_groups.py`; `tests/test_sot_schemas.py`; `tests/test_route_enforcement_gate.py`; `tests/test_orm_migration_parity.py`; `tests/test_migration_0020.py`; `tests/test_browse_category_entity.py`; `tests/test_seed_browse_categories.py`; `tests/conftest.py`; `apps/web/**`; `workers/**`; `pyproject.toml`; `uv.lock`; `infra/scripts/check-all.sh`; all `_bmad-output/planning-artifacts/**`.

## 8. Dev Notes

### 8.1 The shipped `list_models` pipeline you are extending

`service.py:209-335`. Order of operations, which the new predicate must respect: `base = select(Model)` → soft-delete filter (`:210-211`) → `status` (`:212-213`) → tag/untagged composition (`:215-254`) → `source` (`:256-257`) → `q` (`:258-266`) → `external_url` (`:267-276`) → **`total = count(*) over base.subquery()` (`:279-280`)** → sort (`:282`) → offset/limit (`:283`) → eager tags (`:286-296`) → eager gallery (`:298-322`).

Insert the category predicate **between `source` and `q`**. Anywhere before `:279` is functionally equivalent (they all AND), but pinning one position keeps the diff reviewable and keeps the base-filter block contiguous.

```python
if category is not None:
    # Initiative 26 (Story 49.3) — ONE slug-addressed browse-category scope.
    # IN-subquery, never a JOIN: keeps the outer SELECT shape unchanged so the
    # sort / offset-limit / eager-tag / eager-gallery pipeline below applies
    # untouched, exactly as external_url records at :267-276. An unknown slug
    # yields an empty subquery -> unsatisfiable predicate -> empty page with
    # total=0, matching the shipped unknown-tag_id posture (:231-238).
    base = base.where(
        Model.id.in_(
            select(ModelBrowseCategory.model_id)
            .join(BrowseCategory, BrowseCategory.id == ModelBrowseCategory.category_id)
            .where(BrowseCategory.slug == category)
        )
    )
```

**Why this cannot disturb tag semantics:** it is a standalone `base.where(...)`, structurally outside the `tag_predicate` / `untagged_predicate` composition at `:249-254`. `tag_match` never sees it.

### 8.2 The counts helper

Mirror `_tag_model_counts` (`service.py:59-76`) exactly, including the docstring discipline that explains *why* `func.count()` is already a distinct count:

```python
def _browse_category_model_counts(session: Session) -> dict[uuid.UUID, int]:
    rows = session.exec(
        select(ModelBrowseCategory.category_id, func.count())
        .select_from(ModelBrowseCategory)
        .join(Model, Model.id == ModelBrowseCategory.model_id)
        .where(Model.deleted_at.is_(None))
        .group_by(ModelBrowseCategory.category_id)
    ).all()
    return {category_id: n for category_id, n in rows}
```

Hits `ix_model_browse_category_cat_model`. One statement regardless of cardinality — that is AC-23(a).

`list_browse_categories` then does: one `select(BrowseCategory)`, one counts call, sort in Python by `(position, slug)` (the `list_tag_groups` pattern at `:165`) or in SQL via `.order_by(BrowseCategory.position, BrowseCategory.slug)` — **prefer SQL**, since unlike `list_tag_groups` there is no bucketing to do in Python.

### 8.3 `ModelDetail.categories`

Mirror the tags block at `service.py:370-376`:

```python
category_rows = session.exec(
    select(BrowseCategory)
    .join(ModelBrowseCategory, ModelBrowseCategory.category_id == BrowseCategory.id)
    .where(ModelBrowseCategory.model_id == model_id)
    .order_by(BrowseCategory.position, BrowseCategory.slug)
).all()
categories = [BrowseCategorySummary.model_validate(c) for c in category_rows]
```

One extra statement on a function that already issues **seven** (model, tags, files, notes, prints, external_links, gallery-ids — measured at validation on this baseline, §16 V-2), i.e. **7 → 8**: constant, not N+1. That is AC-23(b), and T0.2 re-captures the baseline so "exactly one more" is a measured delta rather than a quoted number.

### 8.4 Why the list tolerates an unknown slug but the detail 404s

Not an inconsistency — two different questions. `GET /api/models?category=X` asks *"which models are in X"*; a stale bookmark should degrade to an empty catalogue page, which is what an unsatisfiable predicate naturally produces and what the shipped `tag_ids` posture already does (`service.py:231-238`). `GET /api/categories/{slug}` asks *"give me the category X"*; if it does not exist there is no resource, and 404 is the only honest answer. Decision AY specifies both explicitly (`architecture.md:3310-3311`).

### 8.5 Testing standards

- **Framework:** pytest, `TestClient`, the session-scoped `_isolated_db` SQLite fixture. No Docker, no network, no live DB.
- **Unique slugs everywhere** and per-test-scoped assertions (§6 F-10). Never assert a DB-global count.
- **Auth:** the `autouse` admin-cookie fixture from `test_sot_tag_groups.py:29-38` (§6 F-11).
- **Query counting:** the `_count_selects` contextmanager from `test_sot_tag_groups.py:89-102`. Measure at the **service layer**, not through `TestClient`, so auth/session overhead does not pollute the count — the reason the shipped test records at `:233-235`.
- **Two-cardinality comparison** for AC-23(a): seed a small fixture, count; seed a doubled fixture, count; assert equality **and** an absolute bound (the shipped pattern asserts both, `:254-255`; the unique-prefix idiom is at `:237`).
- **AC-23(c) fixtures must page equally and non-emptily** — see AC-23(c)'s mandatory precondition and §16 V-1. This is the one query-count assertion in this story that a plausible-looking fixture will get wrong.
- Docstrings name the AC they discharge, as every shipped SoT test module does.

### 8.6 Anti-patterns — do not do these

- ❌ Extending `_tag_model_counts` to serve both entities (§6 F-2).
- ❌ A SQL `JOIN` onto `base` for the category scope (§6 F-6).
- ❌ Adding `categories` to `ModelSummary` (AC-20, and it costs a per-page eager-load for no rendered pixel).
- ❌ Naming anything `Category*` or adding a `category`/`category_id` property (§6 F-3 — two shipped tests fail immediately).
- ❌ Deleting `test_retired_taxonomy_read_route_is_gone` instead of repairing it (AC-24).
- ❌ Touching `_PUBLIC_ROUTES` (§6 F-1).
- ❌ A second, parallel category listing endpoint, or a `with_counts` toggle — `model_count` is unconditional on this contract (AY), unlike `GET /api/tags`.
- ❌ Rewriting `docs/operations.md:426-427` (§6 F-7).
- ❌ Assigning any model to any category "so the tests have data" in a way that touches the live DB — all fixtures are throwaway SQLite.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-1 | Implementer works from the epic sketch and is blindsided by `test_openapi_agent_surface.py:361` at `check-all` time. | §6 F-5 + AC-24 + T6 make it a first-class, planned task with a quoted regression. |
| R-2 | Reusing a retired public path is read as resurrecting the retired taxonomy. | AC-24(b) keeps an executable guard that the flat shape ≠ the recursive shape; AC-25 forbids any doc wording implying reversal; Decision AX's `BrowseCategory*` naming keeps every historical sentence unambiguous. |
| R-3 | The category scope is accidentally folded into the tag `or_()`, silently changing 42.1 semantics. | Constraint 4 + AC-15 + `test_sot_models_list.py` byte-unmodified as the witness. |
| R-4 | A per-category count loop ships (N+1) because the test passes on a small fixture. | AC-23(a) two-cardinality equality **plus** the T5.1 labelled mutation check that proves the test is load-bearing. |
| R-5 | On live data every count is 0 and every scoped page is empty, and this is misread as a broken feature at review. | §2 states the expected live behaviour explicitly and up front. |
| R-6 | Doc corrections over-reach into 54.3's retained scope. | §7 enumerates exactly four passages; §6 F-7/F-9 record what is deliberately left alone and why. |
| R-7 | `total` inflation from a future join composed with 49.4. | §6 F-6 states the forward reason honestly instead of overclaiming a present-tense bug; AC-13 stands as the standing invariant guard 49.4 will inherit. |

## 10. Non-goals (this story ships none of these)

Model↔category **assignments** of any kind; admin category CRUD or reorder (`49.5`); `PUT /api/admin/models/{id}/categories` replace-set (`49.5`); the audit `entity_type browse_category` (`49.5`); depth-2/self-cycle service rules (`49.5`); tag-name free-text search (`49.4`); any new migration or DDL; any edit to `0020`; any seed change or seed re-run (`49.2` is closed); `inclusion_criterion` on the wire (§6 F-12); frontend types, hooks, routes or UI (`50.x`/`51.x`); i18n keys, a11y assertions, visual baselines (no user-visible surface is added); `docs/architecture.md`, the agent add-model runbook and the category governance doc (**explicitly retained by 54.3**); any live-database, production, push, merge or deploy action.

## 11. Branch and commit atomicity

One story branch off `main`, one commit containing the **10** product/doc files in §7 (3 production + 4 test + 3 docs/operational), plus the two workflow records committed per this project's convention. `check-all.sh` 16/16 must pass on the branch alone. The story is independently mergeable: it depends only on 49.1 + 49.2, both already on `main` at `336bf1b`.

## 12. Traceability

| AC | Requirement / Decision | Source |
|---|---|---|
| AC-1…AC-5, AC-7, AC-8 | FR26-CAT-2, FR26-BROWSE-2; Decision AY read surface | `architecture.md:3309-3311`; `epics.md:4479` |
| AC-6, AC-9, AC-21 | Decision AY default-deny; Init 6 Decision M; Decision AW | `architecture.md:3307`; `main.py:50-61`; `EXPERIENCE.md:30` |
| AC-10…AC-17 | FR26-BROWSE-3; Decision AY category scope | `architecture.md:3311`; `epics.md:4479`; `sprint-status.yaml:381` |
| AC-13, AC-23 | NFR26-PERF-1 as query count; 42.2 no-N+1 precedent | `architecture.md:3328`; `test_sot_tag_groups.py:229-262` |
| AC-15 | 42.1 AND/OR semantics preserved | `epics.md:4479`; `service.py:215-254`; `test_sot_models_list.py:276-310` |
| AC-18…AC-20 | Decision AY `ModelDetail` gains categories | `architecture.md:3312` |
| AC-22 | Story 4.3 OpenAPI enrichment gate | `test_openapi_agent_surface.py:54,158-175` |
| AC-24 | Story 47.5 retired-surface guards; G26-ROUTE-PATH | `test_openapi_agent_surface.py:309-382`; `sprint-status.yaml:381` |
| AC-25 | Readiness finding M-1; 54.3 scope narrowing | `epics.md:4481`; `sprint-status.yaml:381,409` |
| AC-26 | Mergeability rule; additive-only invariant | `sprint-status.yaml:356-368`; `architecture.md:3287,3301` |

## 13. Project structure notes

No new module, package or directory. Everything lands in the existing `apps/api/app/modules/sot/` triad (`router` / `service` / `schemas`) that every SoT read already uses, and in `apps/api/tests/` following the shipped `test_sot_*.py` naming. Two new test modules rather than growth of `test_sot_models_list.py` — deliberate, so that file stays byte-unmodified as the AC-15 non-regression witness. No conflict with the unified structure was found.

## 14. Testing standards summary

`.venv/bin/pytest` from `apps/api` (the venv-relative form `check-all.sh:86-87` uses). Final commands:

```bash
# targeted (new coverage)
cd apps/api && .venv/bin/pytest -q tests/test_sot_categories.py tests/test_sot_models_category_scope.py

# non-regression witnesses (must pass byte-unmodified except the two noted MODIFY files)
cd apps/api && .venv/bin/pytest -q \
  tests/test_sot_models_list.py tests/test_sot_models_detail.py \
  tests/test_sot_tags.py tests/test_sot_tag_groups.py tests/test_sot_schemas.py \
  tests/test_sot_auth_boundary.py tests/test_openapi_agent_surface.py \
  tests/test_route_enforcement_gate.py tests/test_orm_migration_parity.py \
  tests/test_seed_browse_categories.py tests/test_browse_category_entity.py

# full suite + lint
cd apps/api && .venv/bin/pytest -q
cd apps/api && .venv/bin/ruff format --check . && .venv/bin/ruff check .

# controller-owned frozen gate (NOT run by the implementer)
infra/scripts/check-all.sh
```

## 15. Dev Agent Record

**Provenance.** Native `bmad-dev-story` (menu **DS**), 2026-07-26, Claude Opus 5 agent session, routed via the repository's native `bmad-help` → `_bmad/_config/bmad-help.csv` row `BMad Method,bmad-dev-story,Dev Story,DS,…,4-implementation,preceded-by bmad-create-story:validate,required=true`. Customization resolved via `python3 _bmad/scripts/resolve_customization.py --skill /home/ezop/repos/3d-portal/.claude/skills/bmad-dev-story --key workflow` → `{"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}`; no team override (`_bmad/custom/bmad-dev-story.toml` absent) and no user override. `persistent_facts` resolved to `_bmad-output/project-context.md` (exists, 321 lines, loaded). Config from `_bmad/bmm/config.yaml` (`user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`).

**Environment.** Worktree `/home/ezop/worktrees/3d-portal-e49-3-dev`, branch `feat/E49.3-category-read-api-and-model-scope`, **actual implementation baseline `2d4fd75832ce54b38cd6a69c986fb323818b778b`** (`docs: create and validate story 49.3`), working tree clean at start. The create/validate source baseline `336bf1b5…` is preserved in `create_validate_baseline_commit`; `2d4fd75` is docs-only on top of it, so `apps/api` product code is byte-identical between the two.

**Authorization.** Implemented under `G26-DEVGO`, granted for this validated story by **Laura/controller** under Ezop's standing Initiative 26 authorization (§18.1). **This is a controller decision, NOT an Ezop signature and NOT an Ezop review.**

**Honesty statement — read before quoting anything below.** **No native `bmad-code-review` was run. No Aider review was run. No commit, push, merge or deploy occurred. No live/production database was opened, read or written.** Every test executed against the session-scoped throwaway SQLite database from `tests/conftest.py::_isolated_db`. T10.1–T10.4 are controller-owned and are left **unchecked**. This record is the implementer's own account; it is not a review verdict.

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), native BMAD `bmad-dev-story`.

### Debug Log References

**T0.1 — clean-tree baseline regression set** (`.venv/bin/pytest -q tests/test_sot_models_list.py tests/test_sot_models_detail.py tests/test_sot_tags.py tests/test_sot_tag_groups.py tests/test_sot_auth_boundary.py tests/test_sot_schemas.py tests/test_openapi_agent_surface.py tests/test_route_enforcement_gate.py`):

```
133 passed, 162 warnings in 16.47s
```

**T0.2 — measured baseline SELECT counts** (throwaway `/tmp` script, worktree source on `PYTHONPATH`, temp SQLite, no live DB; script never committed):

```
get_model_detail SELECTs = 7
list_models NON-EMPTY page SELECTs = 4 items: 1 total: 1
list_models EMPTY page SELECTs   = 2 items: 0 total: 0
```

Exactly reproduces validation E-6 / V-1 / V-2. AC-23(b) target is therefore **8**, and AC-23(c)'s equal-and-non-empty-page precondition is confirmed load-bearing (4 vs 2).

**T1.1 — RED, `GET /api/categories`.** `11 failed, 21 warnings in 1.91s`. Authenticated cases failed on route absence, anonymous case on 404 ≠ 401:

```
        r = client.get("/api/categories")
>       assert r.status_code == 200, r.text
E       AssertionError: {"detail":"Not Found"}
E       assert 404 == 200
```

```
    def test_categories_list_anonymous_returns_401(client):
        client.cookies.delete(ACCESS_COOKIE)
        r = client.get("/api/categories")
>       assert r.status_code == 401
E       assert 404 == 401
```

**T1.5 — GREEN.** `11 passed, 21 warnings in 1.78s`.

**T2.1 — RED, `GET /api/categories/{slug}`.** First authoring left the unknown-slug case passing **by construction** (a route-absent FastAPI 404 satisfies an "expect 404" assertion). Per §5's ordering rule this was **restructured (option a), not relabelled**: the assertion now pins the route's own `detail` message, which a route-absence 404 cannot produce. All six then RED-ed — `6 failed, 11 deselected`:

```
E       AssertionError: {"detail":"Not Found"}
E       assert 'Not Found' == 'Browse category not found'
E         - Browse category not found
E         + Not Found
```

**T2.3 — GREEN.** `17 passed, 32 warnings in 2.76s`.

**T3.1 — RED, `GET /api/models?category=`.** The genuine RED validation predicted: FastAPI silently ignores an unrecognised query parameter, so the unscoped page came back and the subset assertion failed.

```
E       AssertionError: assert {'cs-2e5036-a...2e5036-loose'} == {'cs-2e5036-a...cs-2e5036-a2'}
E         Extra items in the left set:
E         'cs-2e5036-b1'
E         'cs-2e5036-loose'
```

**T3.2/T3.3 — GREEN on the plain scope.** `1 passed, 2 warnings in 0.35s`.

**T3.4/T3.5 — full AC-14(a)–(j) matrix + AC-5/AC-12/AC-13/AC-16/AC-17.** A **test-code defect** surfaced during GREEN and is recorded as such, **not** as a behavioural RED: the new module's `_mk_model` helper hard-coded `status=ModelStatus.not_printed` while also forwarding `**kw`, so the AC-14(e) caller passing `status=ModelStatus.printed` raised `TypeError: Model() got multiple values for keyword argument 'status'` (`1 failed, 32 passed`). Fixed minimally in the helper (`status=kw.pop("status", ModelStatus.not_printed)`); **no production code and no assertion changed**. Re-run: `33 passed, 64 warnings in 5.70s`.

**T4.1 — RED, `ModelDetail.categories`.** Authored in `tests/test_sot_categories.py` so `tests/test_sot_models_detail.py` stays byte-unmodified as the non-regression witness.

```
E       KeyError: 'categories'
E       KeyError: 'categories'
=> 2 failed, 1 passed, 17 deselected
```

The one passing case is AC-20's `ModelSummary` negative, which passes **by construction** (the key never existed there). Labelled a **structural guard**, not a RED.

**T4.4 — GREEN.** `36 passed, 70 warnings in 6.32s`.

**T5 — query-count evidence. COVERAGE GUARD, explicitly NOT an original RED.** The three query-count tests were authored after T1–T4 landed the symbols they measure and were **green on first run** (`39 passed, 73 warnings in 6.98s`). That is *not* TDD evidence and is not presented as any. Their load-bearing character was proven the only honest way available, by the mandated labelled temporary mutation:

1. `sha256sum app/modules/sot/service.py` → `1ce652b1cb7ffdbb68b567bec9aed4d5cd5b34df204611f91959582d5ecc5efa`
2. `_browse_category_model_counts`'s single `GROUP BY` aggregate temporarily replaced with a per-category count loop (the exact N+1 AC-23(a) forbids), commented `TEMPORARY N+1 MUTATION … NEVER COMMITTED`.
3. Sensitivity proof — the guard caught it on the cardinality-independence assertion:

```
>       assert c_small["n"] == c_large["n"], (c_small["n"], c_large["n"])
E       AssertionError: (4, 8)
E       assert 4 == 8
=> 1 failed, 1 warning in 0.57s
```

4. Mutation reverted.
5. `sha256sum` again → `1ce652b1cb7ffdbb68b567bec9aed4d5cd5b34df204611f91959582d5ecc5efa` — **byte-identical to step 1**; independent `diff -q` against a pre-mutation copy printed `BYTE-IDENTICAL`. Post-restoration green: `39 passed, 73 warnings in 6.80s`.

T5.3 honoured: the AC-23(c) fixture seeds enough assignments that the scoped and unscoped calls both return a **non-empty page of 4 rows**, asserted explicitly before the count comparison. Measured `4 == 4`, and equal again at doubled page size. The `if model_ids:` guards were **not** touched.

**T6.1 — genuine regression on the shipped 47.5 guard** (`tests/test_openapi_agent_surface.py` run **unmodified** against the new routes), exactly as §6 F-5 predicted:

```
>       assert r.status_code == 404, f"expected 404 on retired read route, got {r.status_code}"
E       AssertionError: expected 404 on retired read route, got 401
E       assert 401 == 404
=> 1 failed, 34 passed in 1.03s
```

**T6.2/T6.3 — repaired, not deleted.** `test_retired_taxonomy_read_route_is_gone` re-pointed per AC-24(b): it now **authenticates**, asserts `200` + a **flat** JSON array, asserts **no** `children` and **no** `subcategories` on any item, asserts the exact nine-key browse shape **including `model_count`**, and asserts `parent_id` is a scalar-or-null. The runtime-assembled literal `"/api/" + "categories"` is preserved, so the 47.5 §11 residual-symbol grep stays clean. The three mechanically necessary module-level imports were added (`uuid`, `ACCESS_COOKIE`, `encode_token`) — the file previously imported only `pytest` + `create_app`. `git diff -U0` confirms the only touched hunks are the import block and that single test body. GREEN: `35 passed, 2 warnings in 0.97s`; the sibling guards `test_no_category_schemas_in_components`, `test_no_category_properties_on_model_schemas`, `test_no_dangling_refs` and `test_retired_taxonomy_admin_crud_route_is_gone` pass **byte-unmodified** (`8 passed, 27 deselected`).

**T7 — auth-boundary matrix.** `tests/test_sot_auth_boundary.py` extended **purely additively** (`git diff --numstat` = `65 0` — 65 insertions, **zero** deletions) with anonymous-401 and agent/member/admin-200 cases for both new routes, following the 42.2 `/api/tag-groups` precedent. `36 passed, 54 warnings in 5.63s`. T7.2: `tests/test_route_enforcement_gate.py` passes **byte-unmodified** — `3 passed in 0.55s`, `git diff --stat` empty — proving both new routes carry an auth dependency and neither entered `_PUBLIC_ROUTES`.

**T8 — doc honesty.** Four passages corrected across three files, comment/prose only. Mechanically verified afterwards:

```
=== docs/operations.md:424-428 untouched? ===
OK: line 426-427 NOT in the diff
=== cutover-smoke.sh: endpoint= line unchanged? ===
OK: endpoint="/api/tags" NOT in the diff
=== executable lines changed in the two scripts? ===
OK: comment-only, zero executable lines
```

`bash -n` passes on both scripts. Every correction distinguishes the retired Initiative 25 **recursive single-category taxonomy** (permanently gone) from the new Initiative 26 **flat browse-category read**; none implies the retirement was reversed. `docs/operations.md:426-427` was deliberately **not** rewritten (§6 F-7), and the historical design records of §6 F-9 were left alone.

**T9.1 — lint.** `.venv/bin/ruff format --check .` initially reported one new test module needing reformatting; `ruff format` applied, then `ruff check .` → `All checks passed!` and `ruff format --check .` → `277 files already formatted`.

**T9.2 — full API suite, and one regression this story's specification did not anticipate.** The first full run was:

```
FAILED tests/test_sot_schemas.py::test_model_detail_from_orm_with_embeds
1 failed, 1826 passed, 3 skipped, 2101 warnings in 399.43s (0:06:39)
```

```
>           schema = ModelDetail.model_validate(
E           pydantic_core._pydantic_core.ValidationError: 1 validation error for ModelDetail
E           categories
E             Field required [type=missing, input_value={'slug': 'dragon-002', …}, input_type=dict]
```

**Discovered spec gap, stated plainly.** Neither §7 nor the validation pass anticipated that `tests/test_sot_schemas.py` constructs `ModelDetail.model_validate({…})` from an explicit payload dict, so a *required* new field breaks it. That file is on §7's and AC-26's **byte-unchanged** list, so "fix the test" was not available. Resolved in production code by the minimal additive change: `categories: list[BrowseCategorySummary] = Field(default_factory=list)`. `get_model_detail` still always populates the key explicitly, so the wire contract is unchanged — AC-18's ordering and AC-19's `categories: []` both remain executable and green. **`tests/test_sot_schemas.py` is byte-unchanged** (`git diff --quiet` → `BYTE-UNCHANGED`). Focused re-run after the fix: `53 passed, 83 warnings in 8.78s` over `test_sot_schemas.py`, `test_sot_categories.py`, `test_sot_models_category_scope.py`, `test_sot_models_detail.py`.

**Full-suite corroboration (controller-run, not run by the implementer in this pass).** The controller independently re-ran `apps/api/.venv/bin/pytest -q apps/api` after the DTO fix; terminal pytest summary **`1827 passed, 3 skipped, 2101 warnings in 409.21s`**. Pytest itself was GREEN — the outer pipeline's non-zero rc came only from `tee` failing to open an initially missing `.hermes/run-logs` path, not from any test. A truthful **summary artifact** (not a full captured log) exists at `.hermes/run-logs/e49-3-controller-api-full-after-dto-fix-summary-20260726.txt`.

**T9.3 — scope containment.** `git status --porcelain` reconciles to exactly the §7 set — **10 product/doc files (9 modified + 2 new tests, of which 8 modified are product/doc) plus the 2 workflow records**; `git diff --check` is clean (empty output). Every AC-26 immutable path verified `UNCHANGED` by per-path `git diff --quiet`: `app/main.py`, `_entities.py`, `models/__init__.py`, `seed.py`, `apps/api/scripts/**`, `migrations/**`, `conftest.py`, `test_sot_models_list.py`, `test_sot_models_detail.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_sot_schemas.py`, `test_route_enforcement_gate.py`, `test_orm_migration_parity.py`, `test_migration_0020.py`, `test_browse_category_entity.py`, `test_seed_browse_categories.py`, `apps/web/**`, `workers/**`, `pyproject.toml`, `package-lock.json`, `infra/scripts/check-all.sh`, `_bmad-output/planning-artifacts/**`. No lockfile appears in `git status`.

**CR-1 remediation (post-native-review, this session).** The fresh native `bmad-code-review` returned `REQUEST_CHANGES` with one Important finding, and it was **correct**. My AC-24 repair placed every contract assertion inside a bare `for item in body:` sweep with no non-empty precondition. `tests/test_openapi_agent_surface.py` seeds no `BrowseCategory`, and 49.2's starter seed is an admin CLI with no lifespan wiring, so on a fresh database the endpoint legitimately returns `[]` — the loop executed **zero** times and the test passed while asserting only `200` + "is a list". Reproduced standalone before touching anything, with a throwaway probe module (created, run, deleted):

```
PROBE status=200 len(body)=0
1 passed, 2 warnings in 0.32s
```

That is exactly AC-24(b)/D-3's "not merely some array" requirement going unenforced, so the coverage was vacuous rather than wrong. Fixed **test-side only**, inside the same test body: the test now seeds one uniquely-slugged `BrowseCategory` (`f"browse-guard-{uuid4().hex[:8]}"`) through the real session-scoped test engine before probing, then locates that specific slug in the response (`assert seeded is not None`) and applies the exact nine-key shape, the `children`/`subcategories` negatives, the scalar-or-null `parent_id` and the integer `model_count` assertions **to the found item**. It does not seed globally and does not depend on test order or on rows any other module leaves behind. The whole-array nesting negative is retained on top, now backed by a guaranteed non-empty array.

**Non-vacuity proven, not asserted.** Same hash-verified temporary-mutation protocol as T5: `sha256 908c87a93c43f3dfdb8ef7235f63f0bd787a5708b9b502564f64b66af69d88b6` recorded, the expected key set temporarily mutated (`"model_count"` → `"model_count_SENTINEL"`), and the contract block **executed and failed** — which a vacuous loop could not have done:

```
        } == set(seeded), f"unexpected browse item shape: {sorted(seeded)}"
E       AssertionError: unexpected browse item shape: ['description_en', 'description_pl', 'id',
E                       'model_count', 'name_en', 'name_pl', 'parent_id', 'position', 'slug']
E         Extra items in the left set:
E         'model_count_SENTINEL'
```

The observed key set in that failure message *is* Decision AY's nine-key contract, independently confirming AC-2/AC-24(b) on real response data. Mutation reverted; `sha256` re-measured as `908c87a9…` — **byte-identical**, `diff -q` → `BYTE-IDENTICAL`. Post-restoration: module standalone `35 passed`; the CR-1 test alone on a fresh DB `1 passed`; sibling 47.5 guards `8 passed, 27 deselected` **byte-unmodified**; focused non-regression set (`test_sot_categories`, `test_sot_models_category_scope`, `test_sot_auth_boundary`, `test_route_enforcement_gate`, `test_sot_schemas`, `test_sot_models_list`, `test_sot_models_detail`) `124 passed, 207 warnings in 19.86s`. `ruff format` + `ruff check` clean.

**Import-count correction against the validated plan, stated plainly.** §7/AC-24/§16 V-5 predicted the repair would need exactly **three** module-level imports (`uuid`, `ACCESS_COOKIE`, `encode_token`) for authentication. That prediction was right about authentication and incomplete about coverage: making the assertions *non-vacuous* mechanically required **three more** — `Session` (sqlmodel), `BrowseCategory` (`app.core.db.models`) and `get_engine` (`app.core.db.session`) — because the test must seed its own row to have anything to assert against. Six module-level imports total. This is a genuine departure from the validated §7 prediction, not a silent widening: the file is still "one test **body** plus mechanically necessary imports", every other test in it remains byte-unmodified, and `git diff -U0` shows hunks only in the import block and in `test_retired_taxonomy_read_route_is_gone`. Both runtime-assembled route literals (`"/api/" + "categories"` at `:405` and `"/api/admin/" + "categories" + …` at `:449`) are preserved, so the Story 47.5 §11 residual-symbol grep discipline still holds.

### Completion Notes List

- **All 26 ACs implemented and executable.** Two new authenticated read routes (`GET /api/categories`, `GET /api/categories/{slug}`), one new `category` slug-addressed scope on `GET /api/models`, and `ModelDetail.categories`. Nothing was written to `browse_category` or `model_browse_category` — the story is read-only over both, as §1 requires.
- **Constraint 3/4/5 honoured structurally.** The category predicate is a standalone `base.where(Model.id.in_(select(...).join(...)))`, inserted between the `source` filter and the `q` filter — inside the base-filter block, **before** the total-count subquery, and structurally outside the `tag_predicate`/`untagged_predicate` composition. It is never a SQL `JOIN` onto `base` and `tag_match` never sees it. `tests/test_sot_models_list.py` passes byte-unmodified.
- **Naming clears both shipped 47.5 guards.** `BrowseCategorySummary`/`BrowseCategoryRead` (neither `startswith("Category")`) and the plural property `categories` (not in `{"category", "category_id"}`).
- **`inclusion_criterion` omitted** from the read DTO per Decision AY / disposition D-1, with an executable negative asserting its absence.
- **`ModelSummary` gained nothing** (AC-20), asserted by an executable negative; `ModelDetail` alone declares `categories`.
- **Three honestly-labelled non-REDs**, each labelled in both the test docstring and this record: AC-13's duplicate/total invariant (structural guard — holds by construction against the `IN`-subquery; it exists as the standing invariant Story 49.4 inherits), AC-20's `ModelSummary` negative (passes by construction), and the whole of T5 (coverage guard, proven load-bearing by the hash-verified mutation instead).
- **One test-code defect** found during GREEN and fixed in the test helper only (`_mk_model` keyword collision). Recorded as a test defect, not a behavioural RED.
- **One specification gap discovered and resolved in-place** without broadening scope: the required-vs-default shape of `ModelDetail.categories` versus the byte-unchanged `tests/test_sot_schemas.py` (see T9.2 above).
- **Live-data expectation restated, unchanged:** with zero `model_browse_category` rows in production, `GET /api/categories` will return every seeded category with `model_count: 0` and `GET /api/models?category=<any-slug>` will return `total: 0`. That is correct behaviour per §2, not a defect; assignments are curation work owned by 49.5/52.2.
- **Not done, deliberately, and owned by the reviewer/controller:** native `bmad-code-review`; independent `laura-aider-review-diff`; frozen `infra/scripts/check-all.sh` 16/16; the NFR26-DETERMINISM-1 determinism triple; commit, ff-only merge, push and deploy. T10.1–T10.4 remain **unchecked**. The tree is left **uncommitted and review-ready**.

### File List

**Production code — 3 modified**

- `apps/api/app/modules/sot/schemas.py` — added `BrowseCategorySummary` + `BrowseCategoryRead`; added `categories` to `ModelDetail` only (default `[]`).
- `apps/api/app/modules/sot/service.py` — added `_browse_category_model_counts`, `_browse_category_read`, `list_browse_categories`, `get_browse_category_by_slug`; added the `category` parameter + `IN`-subquery predicate to `list_models`; added the ordered category query + `"categories"` payload key to `get_model_detail`; imported `BrowseCategory`/`ModelBrowseCategory`.
- `apps/api/app/modules/sot/router.py` — added `GET /api/categories` and `GET /api/categories/{slug}` (both `current_user`, both with non-empty `summary` + `description`); added the `category` query parameter, its pass-through and its documented contract to `get_models`.

**Tests — 2 new, 2 modified**

- `apps/api/tests/test_sot_categories.py` — **NEW.** List + detail endpoints, `ModelDetail.categories`, `ModelSummary` negative, AC-23(a)/(b) query-count guards.
- `apps/api/tests/test_sot_models_category_scope.py` — **NEW.** Scope correctness, unknown-slug empty page, the full AC-14(a)–(j) matrix, soft-delete posture, uncategorized-visible, AC-5 agreement, AC-13 invariant guard, AC-23(c) query-count guard.
- `apps/api/tests/test_openapi_agent_surface.py` — **MODIFIED.** One test body (`test_retired_taxonomy_read_route_is_gone`) plus **six** mechanically necessary module-level imports: the three auth imports the validation predicted (`uuid`, `ACCESS_COOKIE`, `encode_token`) and three DB-seeding imports the native review (CR-1) showed were equally necessary for **non-vacuous** coverage (`Session`, `BrowseCategory`, `get_engine`). The test now seeds its own uniquely-slugged category and asserts the exact nine-key contract on that specific row. No other test in the file touched; both runtime-assembled route literals preserved.
- `apps/api/tests/test_sot_auth_boundary.py` — **MODIFIED, purely additive** (65 insertions, 0 deletions): one `seeded_browse_category` fixture + six boundary cases for the two new routes.

**Docs / operational scripts — 3 modified (comment/prose only, zero executable change)**

- `docs/operations.md` — Active-surfaces enumeration + parenthetical (`:460-464` region) and the probe-history parenthetical (`:613-616` region). `:426-427` deliberately untouched.
- `infra/scripts/cutover-smoke.sh` — corrected the now-false retirement justification in the Scenario 5 comment; `endpoint="/api/tags"` unchanged.
- `infra/scripts/audit-six-scenarios.sh` — corrected the "not current surface" clause in the Scenario 4 comment.

**Workflow records — 2**

- `_bmad-output/implementation-artifacts/49-3-category-read-api-and-model-scope.md` (this file) — front matter, Tasks T0–T9, §15, Status, Change Log.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story key `ready-for-dev` → `in-progress` → `review`; `epic-49` left at `in-progress`.

## 16. Validation Record

**Verdict: `PASS`**

**Provenance.** Native `bmad-create-story` **action=validate** (menu code **VS**, "Validate Story"), routed from native `bmad-help` → `_bmad/_config/bmad-help.csv` row `BMad Method,bmad-create-story,Validate Story,VS,…,validate,…,4-implementation,preceded-by bmad-create-story:create,followed-by bmad-dev-story,required=false`. Customization resolved with `python3 _bmad/scripts/resolve_customization.py --skill /home/ezop/repos/3d-portal/.claude/skills/bmad-create-story --key workflow` → `{"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}`; no team override (`_bmad/custom/bmad-create-story.toml` absent) and no user override — `_bmad/custom/` holds only `.gitignore` + `config.toml`, and that `config.toml` contains only commented examples. `persistent_facts` resolved to `_bmad-output/project-context.md` (exists, 321 lines, loaded). `checklist.md` (the "Story Context Quality Competition" validation checklist) executed end-to-end in this fresh context. Config from `_bmad/bmm/config.yaml` (`user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`, `implementation_artifacts`, `planning_artifacts`). BMad install v6.10.0.

**Environment.** Worktree `/home/ezop/worktrees/3d-portal-e49-3-create`, branch `docs/init26-e49-3-create-validate`, baseline `336bf1b5ebb9724f99c667ed8f9ded0601950247`.

**Honesty statement — read this before quoting the verdict.** This validation is **Claude / native BMAD only**. **No human reviewed this document.** No Ezop signature, no Ezop review and no Laura review is recorded, implied or claimable from this pass. **`G26-DEVGO` is NOT granted and remains open and controller-owned regardless of this native `PASS`** — a native PASS is a necessary input to that gate, never the gate itself. No code, test or documentation was implemented; no commit, push, merge or deploy; no live database was opened.

### 16.1 Executed evidence

| # | Check | Command / method | Result |
|---|---|---|---|
| E-1 | Routing | `cat _bmad/_config/bmad-help.csv` | `VS` row present, `action=validate`, `preceded-by bmad-create-story:create` ✔ |
| E-2 | Effective customization | `resolve_customization.py --key workflow` and `--key workflow.on_complete` | resolved; all hooks empty; `on_complete` empty ✔ |
| E-3 | Scope containment | `git status --porcelain`; `git diff --name-only 336bf1b` | exactly two workflow paths — ` M …/sprint-status.yaml`, `?? …/49-3-…md`. No product file touched ✔ |
| E-4 | Whitespace / conflict hygiene | `git diff --check` | clean (empty output) ✔ |
| E-5 | Sprint-status parses | `yaml.safe_load` | OK, 336 `development_status` keys; `epic-49: in-progress`, `49-1: done`, `49-2: done`, `49-3: ready-for-validation` → set to `ready-for-dev` by this pass ✔ |
| E-6 | Baseline query counts | live measurement, throwaway `/tmp` SQLite, worktree source on `PYTHONPATH`, no live DB | `get_model_detail` = **7** SELECTs; `list_models` = **4** (non-empty page) / **2** (empty page) ✔ |
| E-7 | Repo-wide doc sweep | `grep -rn "api/categories"` across `*.md *.sh *.py *.ts *.tsx *.yaml` | 4 live passages / 3 files, exactly as §7; `docs/architecture.md` = 0 hits ✔ |

### 16.2 Independently re-derived claims — all CONFIRMED against real code at `336bf1b`

Every citation below was opened and read this pass; none was carried over on trust.

- **`_PUBLIC_ROUTES` / auth posture (F-1).** `app/main.py:50-61` — exactly the cited range, containing only `/api/health`, six `/api/auth/*` and three `/api/share/*` entries. No category path, no wildcard. `app/main.py` needs no edit. UX **affirmatively agrees**: `EXPERIENCE.md:30` reads verbatim *"Every surface in this pass is behind `current_user` — none of it is anonymous, and none of it touches the anonymous `/share/$token` projection."* No contradiction existed to arbitrate. ✔
- **`_tag_model_counts` (F-2).** `service.py:59-76`, one `GROUP BY` over `ModelTag` joined to `Model` filtered `Model.deleted_at.is_(None)`, returning `{tag_id: n}`; the docstring does record the composite-PK ⇒ `func.count()`-is-distinct argument. The sibling-helper instruction (not extending it) is correct — it is keyed by `tag_id` and consumed by both `list_tags` and `list_tag_groups`. ✔
- **`list_models` pipeline and the exact insertion point (§8.1, constraints 3–5).** Verified **line by line**: `base = select(Model)` `:209`; soft-delete `:210-211`; `status` `:212-213`; tag/untagged composition `:215-254`; `source` `:256-257`; `q` `:258-266`; `external_url` `:267-276`; `total` over `base.subquery()` `:279-280`; sort `:282`; offset/limit `:283`; eager tags `:286-296`; eager gallery `:298-322`. The mandated slot — after `source`, before `q`, hence before the count — is real and correct. ✔
- **`get_model_detail` (§8.3).** Tags block `:370-376`; `ModelDetail.model_validate({...})` payload `:410-421`. ✔ (SELECT count corrected — V-2.)
- **Schemas.** `ModelDetail(ModelSummary)` at `schemas.py:158` ✔ — declaring `categories` on the subclass only is structurally sound and leaves `ModelSummary` untouched.
- **Router.** `router = APIRouter(prefix="/api", tags=["sot-read"])` at `router.py:43` ✔; shipped `get_models` signature at `:123-137` ✔; `HTTPException(404)` miss pattern in `get_model` ✔ (line range corrected — V-3).
- **47.5 naming guards (F-3).** `test_no_category_schemas_in_components` `:327-331` rejects any schema `startswith("Category")`; `test_no_category_properties_on_model_schemas` `:334-347` rejects a `category`/`category_id` property on `ModelSummary`/`ModelDetail`/`ModelCreate`/`ModelPatch`/`ShareModelView`. **`BrowseCategoryRead`, `BrowseCategorySummary` and the plural `categories` clear both** — neither name starts with `Category`, and `categories` is not in `{"category", "category_id"}`. Both guards stay byte-unmodified. ✔
- **OpenAPI obligation (F-4).** `TARGET_ROUTER_TAGS = {"admin", "sot-admin", "sot-read"}` at `:54`, and the read router carries `sot-read`, so both new operations genuinely inherit the mandatory non-empty `summary` + `description`. ✔
- **F-5 — the unavoidable in-story test edit.** `test_retired_taxonomy_read_route_is_gone` at `:361-369` does `client.get("/api/" + "categories")` and asserts `404`; the `client` fixture at `conftest.py:65-70` sets only `X-Portal-Client` and no cookie, i.e. it is anonymous. Once the route exists this receives **401** and fails. **The finding is correct and the failure is unavoidable.** ✔
- **Response shapes are implementable.** `BrowseCategorySummary` `{id, slug, name_en, name_pl, position, parent_id}` (6 keys) + `BrowseCategoryRead` adding `description_en, description_pl, model_count` = **exactly** Decision AY's 9-key set at `architecture.md:3309`. Plain Pydantic subclassing on `_OrmBase`; both surface as distinct OpenAPI components (satisfying AC-22) with no dangling `$ref`. `model_count` is not an ORM attribute, so the service assembles it via a dict payload — the shipped `list_tags` idiom. ✔
- **Decision AY conformance.** `architecture.md:3307` (default-deny, `_PUBLIC_ROUTES` needs no edit), `:3309` (flat list, `(position, slug)`, 9-key item, `model_count` distinct non-deleted, **empty categories returned**), `:3310` (detail 404 on unknown slug), `:3311` (`?category=<slug>`, composes with the named filters, unknown slug ⇒ empty page `total=0`, **not** 404), `:3312` (`ModelDetail` gains `categories`, `ModelSummary` deliberately does not), `:3328` (NFR26-PERF-1 as query count, equal-result-count fixtures). **Every AC in §4 conforms; nothing exceeds the ratified contract.** ✔
- **Entity shape.** `BrowseCategory` unique-slug index and `ModelBrowseCategory` composite PK + `ix_model_browse_category_cat_model` all present as described ✔ (line numbers corrected — V-8).
- **Test precedents.** `_count_selects` `test_sot_tag_groups.py:89-102` ✔; autouse admin-cookie fixture `:29-38` ✔; two-cardinality query-count precedent `:232-255` ✔; `make_anonymous_client` `conftest.py:127` ✔; session-scoped `_isolated_db` `conftest.py:32-62` ✔ (so F-10's unique-slug / no-global-count discipline is genuinely necessary); 42.2 auth-boundary precedent for a new read route at `test_sot_auth_boundary.py:134-135` ✔; AC-15's non-regression witness `test_sot_models_list.py:276-310` ✔.
- **Doc passages — all four quoted verbatim and correct to the line.** `docs/operations.md:426-427` ✔ (and F-7's judgment that it stays **true** and must **not** be rewritten is sound — it describes the retired Initiative 25 taxonomy plus a historical 43-row count, not the route); `:460-462` ✔ (Public-read enumeration; independently confirmed to omit **both** `/api/categories` and `/api/tag-groups`, so D-2's premise holds); `:463-464` ✔; `:613-616` ✔ (the epic's ":613-614" does undercount a four-line parenthetical); `infra/scripts/cutover-smoke.sh:401-404` ✔ — F-7's precision claim is **exactly right**: `:400` is the function header and `:405` is `local ts code endpoint="/api/tags"`, which stays unchanged; `infra/scripts/audit-six-scenarios.sh:673-675` ✔ (F-8's fourth passage is real and correctly in scope).
- **Doc set completeness (F-8 / F-9).** Independently swept — the live non-historical occurrences are **exactly** those four passages in three files. `docs/superpowers/specs/**` and `docs/design/HANDOFF-tagi-fasetowe.md:47` are dated point-in-time design records; leaving them alone is correct and editing them **would** falsify the historical record. 54.3's retained areas are preserved, and `docs/architecture.md` has **zero** `/api/categories` occurrences, so no overlap exists. ✔
- **Task ordering does not ask anyone to fabricate a failure.** T3.1's stated RED — FastAPI **ignores** an unrecognised query parameter, so the unscoped page returns and the subset assertion fails — is a genuine, mechanically guaranteed failure ✔. T6.1's regression is real ✔. T1/T2/T4 REDs are route-absence failures ✔. T5 was the one exception and is repaired (V-7). AC-13 is correctly labelled an invariant guard rather than a RED, and F-6's honest admission that a join would **not** actually inflate rows in this story in isolation is accurate — `slug` is unique and the join PK is `(model_id, category_id)`. ✔
- **G26-ROUTE-PATH.** `sprint-status.yaml:381` does carry the ratification text, and §2 characterizes it correctly as a **controller** decision, explicitly not an Ezop signature. ✔

### 16.3 Amendments applied by this validation

Controller-directed:

- **V-7 — T5.1 was mislabelled `RED`.** The query-count tests are authored **after** T1–T4 land the symbols they measure and may start green; the original text even said so while still printing **RED**. Rewritten as an explicit **mutation / coverage guard**, stating in terms that it is **NOT an original RED**, that §15 and the commit message must not claim TDD evidence that did not happen, and specifying the hash-proven temporary-mutation protocol (record `sha256` → mutate → quote failure → revert → quote green → assert identical hash). New T5.3 pins AC-23(c)'s fixture precondition.
- **V-9 — file-count arithmetic.** 3 production + 4 test + 3 docs = **10**, not nine. Corrected in §7 (with the total stated once, authoritatively), §11, AC-26 and `sprint-status.yaml`, each noting the two workflow records separately.
- **D-1 / D-2 / D-3** folded into §6 F-12, §5 T8.1, §7, AC-24 and §5 T6.2; §18 rewritten from an open-question posture to resolved dispositions.

Independently discovered by this validation:

- **V-1 (material — the most consequential finding of this pass). AC-23(c) was not falsifiable-safe and set a trap that could have caused a real regression.** Measured: `list_models` issues **4** SELECTs on a non-empty page but only **2** on an empty one, because the eager-tag (`:289`) and eager-gallery (`:305`) blocks are both guarded by `if model_ids:`. AC-23(c) demanded that a scoped call issue "the same number of SELECTs as the equivalent unscoped call at the same page size" **without stating that both pages must be non-empty and equally sized** — and §2 records that on live data every scoped page **is** empty, making the broken comparison the *default* one to write. An implementer seeing 2 vs 4 could reasonably conclude the production code was wrong and "fix" it by removing the `if model_ids:` guards, i.e. introduce a genuine per-page N+1 while believing they were satisfying an anti-N+1 AC. AC-23(c) now carries the **mandatory equal-and-non-empty page precondition**, the measured numbers, the ratified `architecture.md:3328` equal-result-count rationale, and an explicit prohibition on touching the guards. Mirrored in §8.5 and T5.3.
- **V-6 — AC-14's "every shipped filter family" was incomplete.** The matrix claimed completeness while omitting two shipped `get_models` parameters: **`include_deleted`** and **`external_url`** (`router.py:123-137`). Added as **(i)** and **(j)**, with the parameter-by-parameter completeness check recorded. `(i)` matters on its merits, not as bookkeeping: `category` + `include_deleted=true` is the one composition where the category predicate and soft-delete could interact wrongly, and AC-16 asserts an asymmetry there (rows reappear, `model_count` still excludes) that had no mandated executable test. T3.4 now requires it.
- **V-5 — AC-24's mandated authenticated repair collides with "one test only".** `tests/test_openapi_agent_surface.py` imports **only** `pytest` and `create_app` (`:18-22`) and has no auth fixture, so authenticating requires module-level imports (`uuid`, `ACCESS_COOKIE`, `encode_token`). Recorded in AC-24, §6 F-5, §7 and T6.2 as "one test **body**, plus mechanically necessary imports", so the implementer is not blocked by an apparent contradiction and AC-26 stays truthful.
- **V-2 — `get_model_detail` issues 7 SELECTs, not "six".** Measured (E-6). §8.3 corrected to `7 → 8`; T0.2 now carries the measured baseline while still requiring re-measurement.
- **V-3 — `router.py:176-185` was wrong** for the shipped `get_model` 404 pattern; the real range is **`:166-175`** (`:178` starts the next route). Corrected in T2.2.
- **V-8 — `_entities.py` citations drifted by 1–2 lines.** `uq_browse_category_slug` is `:148` (not `:147`); `inclusion_criterion` is `:157` (not `:155`); `ModelBrowseCategory` is `:167-183` (not `:165-181`). Corrected in F-2, F-6, F-12, with `ix_model_browse_category_cat_model` pinned at `:175`.
- **V-10 — minor test-citation drift.** The two-cardinality assertion pair is `:254-255` (not `:252-253`), the unique-prefix idiom `:237` (not `:236`), the service-layer-measurement rationale `:233-235`. Corrected in §8.5.
- **V-4 — AC-26 / §7 list agreement.** AC-26's "in particular" list omitted `tests/test_sot_models_detail.py` (the witness T4.1's whole design depends on) and `tests/conftest.py`. Both added, with AC-26 explicitly declared a subset that must not contradict §7.

### 16.4 Residual risk carried into dev, stated plainly

- The story's own §15 remains empty and its Tasks remain unchecked — correct, since no implementation has occurred. Nothing in this record asserts otherwise.
- On live data every `model_count` will be `0` and every scoped page empty (§2). This is correct behaviour; combined with V-1 it is also the single most likely source of a misdiagnosed test failure during dev. Both are now stated in the ACs an implementer actually reads.
- Query-count expectations were checked for feasibility and are **not** tautological: AC-23(a) `≤ 2` and cardinality-independent is achievable with the mandated single aggregate; AC-23(b) is a measured `7 → 8` delta; AC-23(c) compares `4` vs `4` under the now-mandatory equal-page precondition, so it genuinely discriminates a subquery from an extra round-trip.

**No open question remains.** No new material blocker was found: the two specification defects discovered independently (V-1, V-6) were repairable in place within the frozen intent-contract and were repaired, without broadening scope or relaxing any binding constraint.

## 17. Disclosed deviations from the base workflow

1. **The create pass ended at `ready-for-validation`, not the base workflow's `ready-for-dev`.** The base `bmad-create-story` sets `ready-for-dev` at the end of the create pass. This project routes create → **independent** validate → controller `G26-DEVGO`, and 49.1/49.2 both used `ready-for-validation` at that stage. The independent validate pass has now run and returned `PASS`, so the status advanced to **`ready-for-dev`** — which is where the base workflow would have put it, one gate later. `G26-DEVGO` still gates actual implementation and is **not** granted by that status. Disclosed, not silently applied.
2. **`epic-49` is left at `in-progress`.** It was flipped at 49.1's dev-story pass; the base workflow's first-story auto-promote does not apply and no change is warranted.
3. **Doc scope is one passage wider than the epic enumerates** (`infra/scripts/audit-six-scenarios.sh`, §6 F-8) and **one passage narrower** (`docs/operations.md:426-427`, §6 F-7). Both departures are argued from the current file contents against AC-25's own stated criterion, and both are reported here rather than folded in silently.
4. **Subagents were not used** despite the base skill recommending them, because this session's operating instructions forbid dispatching agents unless explicitly requested. All artifact and code analysis in §6 was performed directly in-session against files at `336bf1b`.

## 18. Resolved dispositions (no open questions remain)

The create pass raised three questions. All three are **decided** by the controller at validation and folded into the ACs above. **No open question remains**, and validation discovered no new material blocker (the two specification defects it did find — §16 V-1 and V-6 — were repaired in place within the frozen contract, not escalated).

- **D-1 — `inclusion_criterion`: OMIT from this read contract.** Follow ratified Decision AY's exact public-read keyset (`architecture.md:3309`). E49.5/52.3 may add an admin/curation DTO later; this story is **not** broadened. Applied in §6 F-12 and AC-2.
- **D-2 — `docs/operations.md:460-462`: bounded honesty correction ACCEPTED.** Because the current-state read-surface enumeration is already being edited for the new categories route and already omits the shipped `/api/tag-groups`, **both** truthful current routes are added in that one bounded prose change. Recorded as deliberate **same-passage doc reconciliation**, not backend scope and not a licence to widen the doc pass. Applied in §5 T8.1 and §7.
- **D-3 — AC-24's repair shape ACCEPTED, with tightening.** The runtime-assembled route literal and the old retirement intent are preserved, **and** the repaired test must **authenticate** and assert the **exact new flat contract/item shape** — absence of `children`/`subcategories`, presence of the distinguishing browse fields including `model_count` — rather than merely accepting any array. `test_retired_taxonomy_admin_crud_route_is_gone` and both `Category*` / singular-property guards stay **byte-unmodified**. Applied in AC-24 and §5 T6.2, together with the validation-discovered import consequence (§16 V-5).

## 18.1 Controller pre-development gate — G26-DEVGO

**Independent focused specification review:** `laura-aider-review-repo`, Aider v0.86.2 / `openrouter/deepseek/deepseek-v3.2`, read-only compact pack (this validated story plus current SoT service/router/schemas and the retired-surface OpenAPI guard). Durable local output: `.hermes/run-logs/e49-3-predev-aider-review-20260726.log`.

- Final literal verdict: **`APPROVE`**.
- Critical: **0**.
- Important: **0**.
- Missing tests: **0**.
- Three Minor notes merely confirmed the native-validation amendments: AC-24's required auth imports, AC-23(c)'s equal-and-non-empty query-count precondition, and the corrected 10-file arithmetic. No additional amendment or implementation fix was required.
- Controller consistency audit: story/YAML both `ready-for-dev`; literal native `PASS`; `epic-49: in-progress`; exact 10 product/doc paths plus two workflow records; T5 is explicitly a mutation guard rather than an invented RED; `git diff --check` clean; reviewer `.gitignore` byproduct restored exactly from `HEAD` and no `.aider*` cache remained.

**Controller decision — `G26-DEVGO`: GRANTED for Story 49.3 on 2026-07-26 by Laura/controller.** Basis: native validation `PASS`, controller audit, independent Aider `APPROVE`, and Ezop's standing Initiative 26 authorization. This grants only a fresh native `bmad-dev-story` over the exact validated scope. It grants no live DB, model assignment, seed, migration, E49.4/E49.5, commit, push, merge or deploy action to the implementer. This is not an Ezop signature or review.

**Next:** commit/integrate this docs-only create+validate artifact, then run a fresh native `bmad-dev-story` from that planning baseline on a separate `feat/E49.3-category-read-api-and-model-scope` worktree. Native and Aider code review plus final controller gates remain required.

## 19. Change Log

| Date | Pass | Result |
|---|---|---|
| 2026-07-26 | `bmad-create-story` (action=create, menu CS), Claude Opus 5, native BMAD | Story created at baseline `336bf1b`; status `ready-for-validation`. No human review; no Ezop or Laura sign-off recorded or implied. |
| 2026-07-26 | `bmad-create-story` (action=**validate**, menu **VS**), Claude Opus 5, native BMAD, fresh independent session at the same baseline `336bf1b` | **`PASS` with amendments.** All §6 citations independently re-derived from real source/tests/docs; four doc passages verbatim-confirmed and the doc set independently confirmed complete. Controller items applied: file count nine → **10** (V-9), T5.1 rebuilt from a false `RED` into a labelled hash-proven **mutation guard** (V-7), dispositions D-1/D-2/D-3 folded in and §18 closed. Validation additionally found and repaired in place: **V-1** AC-23(c) was not falsifiable-safe (measured 4-vs-2 SELECTs; could have driven an implementer to delete the `if model_ids:` guards and ship a real N+1) and **V-6** AC-14 omitted the shipped `include_deleted` and `external_url` families; plus V-2/V-3/V-4/V-5/V-8/V-10 precision fixes. Status → `ready-for-dev`. **No human review; no Ezop signature, no Ezop review, no Laura review recorded or implied. `G26-DEVGO` remains open and controller-owned at native-validation time.** |
| 2026-07-26 | Laura/controller pre-development gate | Independent Aider specification `APPROVE` (Critical 0, Important 0, Missing tests 0); controller consistency audit PASS; `G26-DEVGO` granted for the exact validated Story 49.3 scope under standing Initiative 26 authorization. This is not an Ezop signature or review. |
| 2026-07-26 | `bmad-dev-story` (DS) — bounded CR-1 remediation pass, Claude Opus 5, same implementer session, same baseline `2d4fd75` | **Native review finding CR-1 (Important) fixed, test-side only.** The AC-24 repair's contract assertions all sat inside a bare `for item in body:` sweep with no non-empty precondition; the module seeds no `BrowseCategory` and 49.2's seed is a CLI with no lifespan wiring, so on a fresh DB the endpoint returned `[]`, the loop ran **zero** times and the test passed while proving only `200` + "is a list". Reproduced standalone (`PROBE status=200 len(body)=0`) before editing. The test now seeds one uniquely-slugged category via the real test engine, locates that exact slug in the response, and applies the nine-key shape / no-`children` / no-`subcategories` / scalar-`parent_id` / integer-`model_count` assertions to that found item. Non-vacuity proven by a hash-verified temporary mutation of the expected key set (`assertion executed and failed`, revealing the true nine keys), reverted with `sha256 908c87a9…` byte-identical. **Correction to the validated plan, recorded not hidden:** §7/§16 V-5 predicted three auth imports; non-vacuous coverage mechanically required three more (`Session`, `BrowseCategory`, `get_engine`) — six total. `git diff -U0` confined to the import block + that one test body; every other test byte-unmodified; both runtime-assembled route literals preserved. Module `35 passed`, CR-1 test alone `1 passed`, sibling 47.5 guards `8 passed`, focused non-regression `124 passed`, ruff clean. **No production, docs or operational-script file touched in this pass.** Story/sprint stay `review`; `epic-49` stays `in-progress`; T10.1–T10.4 stay unchecked. **This pass issues no review verdict** — re-review is the reviewer's/controller's call. No commit/push/merge/deploy, no live DB. |
| 2026-07-26 | `bmad-dev-story` (DS), Claude Opus 5, native BMAD, fresh session at implementation baseline `2d4fd75` | **Implemented.** T0–T9 complete; T10.1–T10.4 left unchecked (controller-owned). Two new authenticated read routes, the `?category=` slug scope, and `ModelDetail.categories`. Behavioural RED→GREEN observed and quoted for T1/T2/T3/T4 and for T6's genuine 401-vs-404 regression; T5 recorded as a **coverage guard, explicitly not a RED**, with the labelled temporary N+1 mutation caught at `assert 4 == 8` and `service.py` restored to a byte-identical `sha256 1ce652b1…`. Three non-REDs labelled honestly (AC-13 invariant guard, AC-20 negative, all of T5). One test-helper defect fixed in test code only. One specification gap resolved in place: `ModelDetail.categories` ships with `default_factory=list` so the byte-unchanged `tests/test_sot_schemas.py` keeps passing while AC-18/AC-19 stay green. Scope reconciled to exactly the 10 product/doc files + 2 workflow records; `git diff --check` clean; every AC-26 immutable path verified unchanged. ruff clean. Controller-run full API suite after the fix: **1827 passed, 3 skipped**. Status → `review`; `epic-49` unchanged at `in-progress`. **No native code review, no Aider review, no commit/push/merge/deploy, no live DB. No Ezop signature and no Ezop review recorded or implied.** |
| 2026-07-26 | `bmad-code-review` (CR), Claude Opus 5, native BMAD, fresh independent adversarial session over the uncommitted working tree at baseline `2d4fd75` | **Literal verdict `REQUEST_CHANGES`** — Critical **0**, Important **1**, Minor **3** (2 routed `defer`, 1 recorded note), Dismissed **0**. All 26 ACs re-derived against the real diff rather than trusted from §15; the AC-26 immutable set verified `UNCHANGED` path-by-path; `service.py` sha256 independently re-derived as `1ce652b1…` (the T5.1 mutation was genuinely restored); ruff clean; 124 targeted tests green; OpenAPI components/summaries/descriptions inspected from a live `create_app().openapi()`. The one Important is **CR-1**: the AC-24(b)/D-3 repaired 47.5 guard keeps its entire contract block inside `for item in body:` with no non-empty precondition, so it self-disables whenever the shared test DB holds no browse categories — empirically confirmed (`len(body) == 0` on a fresh DB; `pytest tests/test_openapi_agent_surface.py` → `35 passed` while asserting only `200` + "is a list", i.e. exactly the "merely some array" posture D-3 tightened against). Full record in §20. Status left at `review`; T10.1–T10.4 left **unchecked**. **This review ran no Aider pass, no frozen `check-all.sh`, no determinism triple, no commit/push/merge/deploy and touched no live DB. It is Claude/native-BMAD only — no Ezop review, no Ezop signature and no Laura review is recorded, implied or claimable from it.** |
| 2026-07-26 | `bmad-code-review` (CR) — **fresh independent re-review after the CR-1 remediation**, Claude Opus 5, native BMAD, new context over the same uncommitted tree at baseline `2d4fd75` | **Literal verdict `APPROVE`** — Critical **0**, Important **0**, Minor **2** (both `note, no action`). **CR-1 is RESOLVED and the resolution was verified independently, not trusted.** The guard now seeds one uniquely-slugged `BrowseCategory` (`browse-guard-<uuid4[:8]>`) through the real session-scoped test engine and pins that exact slug before asserting the flat nine-key browse contract, so the block can no longer self-disable. Proven non-vacuous on a fresh standalone DB (`pytest tests/test_openapi_agent_surface.py::test_retired_taxonomy_read_route_is_gone` → `1 passed`, i.e. `assert seeded is not None` executed) and by a reviewer-built mutation harness **outside the repo** (`/tmp/cr1mut`): the key-set mutant fails revealing the true nine keys, and the seed-removal mutant fails with `seeded category 'browse-guard-8d1771ca' missing from []` — which also re-reproduces the original empty-DB evidence. Containment re-derived byte-wise: of 26 top-level blocks in the file exactly **2** differ from baseline (the import preamble, additions only, and that one test body); the runtime-assembled `"/api/" + "categories"` literal and every sibling 47.5 residual/naming/admin guard are byte-identical; the three added imports (`Session`, `BrowseCategory`, `get_engine`) are each mechanically necessary. `service.py` sha256 still `1ce652b1…` → the fix pass touched no production code; test-file sha256 `908c87a9…` matches the implementer's claimed restoration. `35 passed` module, `5 passed` sibling-guard selection, `124 passed` targeted non-regression, ruff clean. §20's `REQUEST_CHANGES` is preserved unchanged as history; CR-2/CR-3 (`defer`) and CR-4 (note) carry forward untouched. Full record in §22. Story/sprint stay `review`, `epic-49` stays `in-progress`, T10.1–T10.4 stay **unchecked**. **This re-review ran no Aider pass, no frozen `check-all.sh`, no determinism triple, no commit/merge/push/deploy and touched no live DB; it edited no product, test or documentation file. Claude/native-BMAD only — no Ezop review, no Ezop signature and no Laura review is recorded, implied or claimable from it.** |
| 2026-07-26 | Independent Aider code reviews + Laura/controller adjudication | Pre-fix Aider returned `APPROVE` but missed native Important CR-1 and was explicitly rejected as insufficient. Fresh post-fix Aider rerun over the final diff returned literal `APPROVE` (Critical 0, Important 0). Its one source-order Minor was dismissed against current lines (`q` before `external_url`); both missing-test notes were already covered. Full record §21. No product edit, commit or live action. |
| 2026-07-26 | Laura/controller final gate | Native remediation/re-review and post-fix Aider chain green; frozen `check-all` 16/16; API 1827/3; Web 785; visual 536/32; three identical full API determinism runs 1827/3/2101; 10-file product/doc hash `e58fe1a2…a54d` stable. Status → `done`; T10.4 intentionally pending until the atomic commit exists. No live DB action in this record. |

## 20. Code Review Record (native `bmad-code-review`)

**Verdict: `REQUEST_CHANGES`**

**Counts: Critical 0 · Important 1 · Minor 3 (2 `defer`, 1 note) · Dismissed 0.**

**Provenance.** Native `bmad-code-review` (menu **CR**), 2026-07-26, Claude Opus 5 agent session, fresh context, routed via the repository's native `bmad-help` → `_bmad/bmm/module-help.csv` row `BMad Method,bmad-code-review,Code Review,CR,"Story cycle: If issues back to DS if approved then next CS or ER if epic complete.",,,4-implementation,bmad-dev-story,,false,,` (phase `4-implementation`, `preceded-by bmad-dev-story` — the routing the current story/sprint state at `review` selects). Customization resolved via `python3 _bmad/scripts/resolve_customization.py --skill /home/ezop/repos/3d-portal/.claude/skills/bmad-code-review --key workflow` → `{"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}`; no team override (`_bmad/custom/bmad-code-review.toml` absent) and no user override. `persistent_facts` glob resolved to **no file in this worktree** (`_bmad-output/project-context.md` does not exist here — it is present only in the create/validate worktree), so no persistent fact was loaded; this is disclosed rather than silently skipped. Config from `_bmad/bmm/config.yaml` (`user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`). Step files `step-01-gather-context` → `step-02-review` → `step-03-triage` → `step-04-present` executed in order.

**Environment and review target.** Worktree `/home/ezop/worktrees/3d-portal-e49-3-dev`, branch `feat/E49.3-category-read-api-and-model-scope`, baseline `2d4fd75832ce54b38cd6a69c986fb323818b778b`. Diff source: **uncommitted changes** (`git diff HEAD` = 10 files / 522 lines, plus the two untracked test modules at 988 lines) — well under step-01's 3000-line chunking threshold, so the review ran whole. `{review_mode}` = `full`, `{spec_file}` = this story, `{story_key}` = `49-3-category-read-api-and-model-scope`.

**Honesty statement — read before quoting anything below.** This review is **Claude / native BMAD only**. **No human reviewed this code.** No Ezop signature, no Ezop review and no Laura review is recorded, implied or claimable from this pass. **Not done by this review and still outstanding:** the independent `laura-aider-review-diff`, the frozen `infra/scripts/check-all.sh` 16/16, the NFR26-DETERMINISM-1 determinism triple, and the commit / ff-only merge / push / deploy. **T10.1–T10.4 remain unchecked.** No product, test or documentation file was edited by this review; no fix was applied; no commit, push, merge, deploy, seed or migration was performed; no live/production database was opened, read or written. Every command below ran against the throwaway session-scoped SQLite from `tests/conftest.py::_isolated_db` or against `git` metadata. The implementer's §15 assertions were **re-derived, not trusted**.

### 20.1 Executed evidence

| # | Check | Command / method | Result |
|---|---|---|---|
| R-1 | Diff scope | `git status --porcelain`; `git diff HEAD --stat` | Exactly the §7 set: 8 modified product/doc + 2 new tests + 2 workflow records ✔ |
| R-2 | AC-26 immutable witnesses | per-path `git diff --quiet HEAD -- <path>` over all 17 named files + `migrations/`, `apps/web/`, `workers/`, `apps/api/scripts/`, `planning-artifacts/` | every one `UNCHANGED`; no stray untracked file ✔ |
| R-3 | Mutation proof restored | `sha256sum apps/api/app/modules/sot/service.py` | `1ce652b1cb7ffdbb68b567bec9aed4d5cd5b34df204611f91959582d5ecc5efa` — **byte-identical to §15 T5.1 steps 1/5** ✔ |
| R-4 | No residual N+1 | read `_browse_category_model_counts`, `list_browse_categories`, `get_model_detail` | single `GROUP BY` aggregate; the only loops are in-memory list comprehensions (`service.py:233,490`) ✔ |
| R-5 | Targeted + non-regression tests | `.venv/bin/pytest -q tests/test_sot_categories.py tests/test_sot_models_category_scope.py tests/test_sot_auth_boundary.py tests/test_route_enforcement_gate.py tests/test_sot_models_list.py tests/test_sot_models_detail.py tests/test_sot_schemas.py` | `124 passed, 207 warnings in 19.74s` ✔ |
| R-6 | Retired-surface module | `.venv/bin/pytest -q tests/test_openapi_agent_surface.py` | `35 passed` — but see **CR-1**: the AC-24(b) block was **unreachable** in this run ✖ |
| R-7 | Lint | `.venv/bin/ruff check .`; `.venv/bin/ruff format --check .` | `All checks passed!`; `277 files already formatted` ✔ |
| R-8 | OpenAPI surface | live `create_app().openapi()` in a throwaway `/tmp` SQLite | `BrowseCategoryRead` + `BrowseCategorySummary` both in `components.schemas`; **zero** `Category*`-named components; `ModelSummary.properties` has no `categories`; `/api/categories` summary 70 chars / description 1051 chars; `/api/categories/{slug}` 47 / 572; `get_models` params = `[status, tag_ids, tag_match, untagged, source, category, q, external_url, sort, include_deleted, offset, limit]` — exactly **one** new param, no `category_id`/`category_ids`/`category_match` ✔ |
| R-9 | Empty-DB wire probe | throwaway `/tmp` script, fresh SQLite, admin cookie, `GET /api/categories` | `status 200 len(body)= 0` — the evidence CR-1 rests on ✔ |
| R-10 | Script honesty | `bash -n` on both scripts; `git diff` filtered to non-comment `+`/`-` lines | both parse; **zero** executable lines changed; `endpoint="/api/tags"` untouched ✔ |
| R-11 | Doc containment | `git diff -U0 -- docs/operations.md` hunk headers | hunks at `@@ -460 +460,2 @@`, `@@ -463,2 +464,7 @@`, `@@ -613,4 +619,7 @@` only — `:426-427` deliberately untouched per §6 F-7 ✔ |

### 20.2 Acceptance-criteria audit (all 26 re-derived)

- **AC-1 / AC-2 / AC-3** — `list_browse_categories` (`service.py:214-233`) orders in SQL by `(position, slug)`; the response is a flat `list[BrowseCategoryRead]`; `_browse_category_read` emits the exact nine keys with genuine nulls present; zero-assignment categories are returned with `model_count: 0` via `counts.get(c.id, 0)`. Executable in `test_sot_categories.py:107,129,152,196`. ✔
- **AC-4 / AC-5 / AC-16** — `_browse_category_model_counts` (`service.py:175-192`) is one `GROUP BY` over `ModelBrowseCategory` joined to `Model` filtered `Model.deleted_at.is_(None)`; the composite-PK distinctness argument is carried in the docstring as §6 F-2 required. Soft-deleted assignees are excluded on **both** sides and the AC-5 equality is asserted numerically (`test_sot_models_category_scope.py:187`, `:211`). ✔
- **AC-6 / AC-9 / AC-21** — both routes declare `_user_id: uuid.UUID = current_user`; `app/main.py` is byte-unchanged so `_PUBLIC_ROUTES` gained nothing; `test_route_enforcement_gate.py` passes byte-unmodified; the anonymous-401 and agent/member/admin-200 matrix exists twice over (`test_sot_categories.py:238,245,304,314` and the six additive cases in `test_sot_auth_boundary.py`, `git diff --numstat` = `65 0`). ✔
- **AC-7 / AC-8** — `get_browse_category_by_slug` returns `None` on a miss and `router.py` raises `HTTPException(404, "Browse category not found")`. The unknown-slug test pins that **route-specific** message, so it genuinely fails on route absence instead of passing on FastAPI's generic `"Not Found"` — the T2.1 restructuring is real, not relabelled. ✔
- **AC-10 … AC-13, AC-17** — exactly one `category: str | None = None` param (confirmed against the live OpenAPI parameter list, R-8). The predicate is a standalone `base.where(Model.id.in_(select(...).join(...)))` at `service.py:340-359`, sitting **after** the `source` filter and **before** `if q:` — hence before the `total` subquery — and structurally outside the tag/untagged `or_()`/`and_()` composition, so `tag_match` cannot see it. Never a SQL `JOIN` onto `base`; the outer `SELECT Model` shape is unchanged. Unknown slug → unsatisfiable predicate → 200 + `items: []` + `total: 0` with the `offset`/`limit` echo preserved. ✔
- **AC-14(a)–(j)** — all ten families have an executable composition test, including the two V-6 additions: `include_deleted=true` (`:439`) proves the asymmetry AC-16 demands (the soft-deleted assignee **reappears** in the scoped page, `total` 1 → 2, while `/api/categories` `model_count` stays 1) and `external_url` (`:473`) proves the two `IN`-subquery families AND cleanly. The `tag_match=all` case additionally re-asserts the unscoped partitioning as a control, which is the right shape for AC-15. ✔
- **AC-15** — `tests/test_sot_models_list.py` byte-unchanged and green. ✔
- **AC-18 / AC-19 / AC-20** — `get_model_detail` issues one ordered category query and always writes `"categories"` into the `model_validate` payload; ordering `(position, slug)` incl. the tie case is asserted through HTTP, `[]` (never null) is asserted, and `ModelSummary` carries no `categories` on the wire **and** none in the OpenAPI component. See **CR-2** for the one honest caveat about the *published* required-ness. ✔ (with Minor)
- **AC-22** — both operations carry non-empty `summary` + `description`; both new components are present with no dangling `$ref` (`test_no_dangling_refs` green). ✔
- **AC-23** — (a) two-cardinality equality **and** the absolute `≤ 2` bound; (b) absolute `== 8` plus bare-vs-rich equality, so a per-category fan-out would break it; (c) the equal-and-non-empty precondition is **asserted, not assumed** (`assert len(scoped.items) == len(unscoped.items) == page`) before the `4 == 4` comparison, and re-checked at doubled page size. The `if model_ids:` guards are untouched. Both query counters clean up via `event.remove` in a `finally`. ✔
- **AC-24** — (a) and (c) hold: `test_no_category_schemas_in_components`, `test_no_category_properties_on_model_schemas` and `test_retired_taxonomy_admin_crud_route_is_gone` are byte-unmodified and green, and the retired-route literal is still assembled at runtime (`"/api/" + "categories"`), so the 47.5 §11 residual-symbol grep stays clean. **(b) does NOT hold deterministically — see CR-1.** ✖
- **AC-25** — all four passages corrected, comment/prose only, `bash -n` clean, zero executable lines changed, `/api/tags` probe endpoint untouched, `docs/operations.md:426-427` deliberately untouched. Every correction states explicitly that the Initiative 25 recursive single-category taxonomy stays retired; none implies reversal. ✔
- **AC-26** — verified path-by-path (R-2). ✔

### 20.3 Findings

**CR-1 — Important — `patch` — severity `high` — AC-24(b) / D-3 not deterministically discharged: the repaired 47.5 guard self-disables on an empty category table.**
`apps/api/tests/test_openapi_agent_surface.py:394`
The entire contract-proving block — no `children`, no `subcategories`, the exact nine-key browse shape including `model_count`, `parent_id` scalar-or-null — lives inside `for item in body:` with **no precondition that `body` is non-empty**. `test_openapi_agent_surface.py` seeds no browse category and imports no fixture that does, so on a fresh session DB the route legitimately returns `[]` and the loop never executes: the test then asserts only `200` and `isinstance(body, list)` — precisely the "merely some array" posture that AC-24(b) and controller disposition D-3 were written to forbid.
*Evidence:* R-9 measured `status 200 len(body)= 0` against a fresh DB with the admin cookie set; R-6 ran the module standalone → `35 passed` with the block provably unreached. In a full-suite run the loop is non-empty only because `tests/test_browse_category_entity.py` happens to sort earlier and leaves rows in the session-scoped DB — an undeclared cross-file coupling that §6 F-10 explicitly tells this story's tests not to rely on, and that reverses under the story's own §14 targeted command, where `test_openapi_agent_surface.py` precedes `test_browse_category_entity.py` on the pytest command line (explicit paths run in CLI order, not alphabetically).
*Why it is Important and not Minor:* AC-24(b) is a named acceptance criterion, tightened by an explicit controller disposition, and this test is the **sole** surviving 47.5 guard for the read path — 47.5's original 404 assertion was given up in exchange for it. A guard that can silently assert nothing has not replaced that coverage. The product behaviour itself is fine and is separately proven in `test_sot_categories.py:129,152`; what fails is this AC's own executable obligation.
*Unambiguous fix (not applied by this review):* seed one uniquely-slugged `BrowseCategory` inside the test before the probe, then assert the seeded item is present in `body` (or, minimally, `assert body, "no browse category seeded — the contract assertions below would be vacuous"`) before the loop. No production change, no other test touched, AC-26 unaffected.

**CR-2 — Minor — `defer` — severity `low` — `ModelDetail.categories` is advertised as OPTIONAL in the published OpenAPI contract.**
`apps/api/app/modules/sot/schemas.py:204`
`categories: list[BrowseCategorySummary] = Field(default_factory=list)` was the correct minimal resolution of the §15 T9.2 spec gap — `tests/test_sot_schemas.py` is on the AC-26 byte-unchanged list and builds `ModelDetail` from an explicit payload dict, so a required field was not available. Verified adversarially and it does **not** weaken AC-18/AC-19 on the wire: `ModelDetail` has exactly two construction sites in the whole repo (`service.py:524` and that test), the runtime one always writes `"categories"` explicitly, and the ordering / `categories: []` behaviour is asserted end-to-end through HTTP. The honest residue is that the generated document now omits `categories` from `ModelDetail.required` (measured: `ModelDetail required has categories: False`, `properties has categories: True`), so Story 50.1's type generation will emit an optional property for a field the API always sends. Recorded so 50.1 inherits the fact rather than rediscovering it; no change is warranted inside this story's frozen scope.

**CR-3 — Minor — `defer` — severity `low` — `get_browse_category_by_slug` computes the whole-table count aggregate to serve one slug.**
`apps/api/app/modules/sot/service.py:246`
`_browse_category_model_counts(session)` groups over the entire `model_browse_category` table and the result is then reduced to a single `counts.get(c.id, 0)`. It is correct, constant in statement count (2 SELECTs) and no AC constrains it — AC-23 covers only the list, the detail and the scoped model list. At current cardinality it is free. A `.where(ModelBrowseCategory.category_id == row.id)` variant would be strictly cheaper; deferred as a non-blocking optimisation for whoever next touches this helper (49.5 curation work is the natural moment).

**CR-4 — Minor — note, no action — `docs/operations.md:462-463` carries one clarifying sentence beyond T8.1's two mandated elements.**
T8.1 authorised rewriting the `:463-464` parenthetical **and**, in the same bounded change, adding the two truthful current routes to the `:460-462` enumeration. The implementation also added *("Public read" means the read half of the API, not anonymous access — every route listed here is behind `current_user`.)*. Checked and it is **true** — none of the eight enumerated routes appears in `_PUBLIC_ROUTES` — and it is same-passage, prose-only and directly serves AC-25's honesty purpose (the heading "Public read" over auth-protected routes was itself misleading). Recorded as a disclosed micro-widening of T8.1, not as a scope violation and not as a blocker.

**Dismissed: none.** Nothing raised during the pass turned out to be a false positive worth recording as noise.

### 20.4 Explicitly checked and found clean (no finding raised)

- No `_PUBLIC_ROUTES` edit, no `app/main.py` edit, no migration, no seed change, no DDL, no write to `browse_category` / `model_browse_category` anywhere in the diff.
- No component schema named `Category*`; no `category` / `category_id` property on any model-shaped DTO.
- `inclusion_criterion` absent from both wire shapes, with an executable negative (`test_sot_categories.py:183`) rather than an assertion of intent.
- The three non-REDs are labelled honestly in **both** the test docstrings and §15 (AC-13 invariant guard, AC-20 negative, all of T5) — no manufactured RED was found anywhere in the two new modules.
- No test asserts a DB-global browse-category count; every assertion in both new modules is scoped through a `uuid4`-derived unique prefix (`_mine` / `_slugs` + prefixed slugs), so the session-scoped shared DB cannot produce a false pass or a false failure. `_seed_tag_matrix`'s tags and groups are prefix-unique too, so the unscoped control assertion in the `tag_match=all` case is safe.
- Both `_count_selects` context managers detach their listener in a `finally`, so the query counters cannot leak into neighbouring tests.
- The authenticated repair in `test_openapi_agent_surface.py` sets its cookie on the **function-scoped** `client` fixture (`conftest.py:65-70`), so it cannot bleed into `test_retired_taxonomy_admin_crud_route_is_gone` or any other test in the file.
- `git diff --check` clean; no lockfile, no `.aider*` byproduct, no reviewer artifact in `git status`.

### 20.5 Disclosed deviations from the base `bmad-code-review` workflow

1. **No subagents were dispatched** for the Blind Hunter / Edge Case Hunter / Acceptance Auditor layers, despite the skill recommending them: this session's operating instructions forbid dispatching agents unless the operator explicitly requests it. All three review lenses were executed directly in-session against the real diff and the real test runs. This is a disclosed reduction in review independence, not a silent one.
2. **`persistent_facts` resolved to nothing.** The `**/project-context.md` glob has no match in this implementation worktree (the file exists only in the create/validate worktree). Disclosed rather than papered over.
3. **Step-01's CHECKPOINT halt and step-04's HALTs were not offered interactively.** This run was driven by a non-interactive controller input that already fixed the review target, the diff mode, the spec file and the disposition of findings ("leave as action items"), so the cascade had nothing left to ask. Findings are recorded here as action items; **none was applied**.
4. **Step-04 §6's status transition was NOT applied.** The base workflow would set the story and sprint key to `in-progress` because `patch` findings were left as action items. The controller input explicitly overrides this: story and sprint key stay at **`review`**, `epic-49` stays at **`in-progress`**, and `done` is never set. Disclosed, not silently applied.
5. **Nothing was written to `{implementation_artifacts}/deferred-work.md`** for CR-2/CR-3, although step-04 §2 directs it. This review's authorisation covers only the story's review record and, at most, the sprint-status comment. The two `defer` items are recorded in full in §20.3 instead; promoting them into the shared ledger is a controller action.

### 20.6 Verdict

**`REQUEST_CHANGES`** — Critical **0**, Important **1** (CR-1), Minor **3** (CR-2, CR-3 `defer`; CR-4 note), Dismissed **0**.

The implementation is otherwise sound and its §15 account survived re-derivation: the scope is exactly the ratified 10 product/doc files plus 2 workflow records, every AC-26 immutable path is genuinely byte-unchanged, the T5.1 mutation was genuinely reverted to a byte-identical `service.py`, the category scope is genuinely an `IN` subquery applied before the total, and the composition matrix genuinely covers all ten shipped filter families. The single Important finding is a test-side gap in AC-24(b), fixable in one line without touching production code or the frozen scope.

Story status remains **`review`**; T10.1–T10.4 remain **unchecked**. The independent Aider review, the frozen `check-all.sh` 16/16, the determinism triple and the commit / merge / push / deploy are **not** performed by this review and remain outstanding controller-owned work.

## 21. Independent external code review record (Aider)

**Final post-remediation verdict: `APPROVE`** — Critical **0**, Important **0**. Reviewer: `laura-aider-review-diff`, Aider v0.86.2 / `openrouter/deepseek/deepseek-v3.2`, pasted final 10-file product/doc diff, read-only/no-git mode. Durable local output: `.hermes/run-logs/e49-3-aider-code-rereview-20260726.log`.

**Two-pass honesty.** A pre-remediation Aider pass also returned `APPROVE` (log `.hermes/run-logs/e49-3-aider-code-review-20260726.log`) but missed the native review's Important CR-1 vacuous-test defect. That earlier verdict is retained as evidence but is **not accepted as the final external review**. After CR-1 was fixed and fresh native §22 re-review returned `APPROVE`, Aider was run again from a fresh pasted final diff and independently returned literal `APPROVE` with Critical 0 / Important 0.

**Post-fix Aider notes and controller disposition.**

- One Minor claimed the `external_url` filter precedes `q` and therefore makes the comment at `service.py:347` inaccurate. **Dismissed as a false positive:** current source has `if q` at `:362` and `if external_url` at `:371`; the comment's “external_url records at the block just past q” is exact.
- “Missing” direct `default_factory=list` construction coverage is already supplied by byte-unmodified `tests/test_sot_schemas.py::test_model_detail_from_orm_with_embeds`; its initial failure is what forced the compatibility fix, and the post-fix full API suite is green.
- “Missing” OpenAPI coverage is already supplied by the new route/component assertions plus the preserved `test_no_category_schemas_in_components`, `test_no_category_properties_on_model_schemas`, `test_no_dangling_refs`, and native §20/§22 live OpenAPI inspection. No additional test is required.

No product/test/docs file was edited by Aider. This record is Laura/controller's adjudication of the external tool output, not an Ezop review or signature. Frozen `check-all`, determinism, commit/merge/push/deploy remain controller-owned at this point.

## 22. Native code re-review after CR-1 remediation (native `bmad-code-review`, fresh session)

**Verdict: `APPROVE`**

**Counts (this pass): Critical 0 · Important 0 · Minor 2 (both `note, no action`) · Dismissed 0.**

**§20 is history and is preserved verbatim.** Its `REQUEST_CHANGES` (Critical 0 / Important 1 / Minor 3) remains the truthful record of the pre-remediation tree and is **not** amended, softened or overwritten by this section. Section numbering skips `## 21`, which is left free for the controller.

**Provenance.** Native `bmad-code-review` (menu **CR**), 2026-07-26, Claude Opus 5, **fresh reviewer context** with no memory of the prior pass beyond this story file. Routed via native `bmad-help`: catalog `_bmad/_config/bmad-help.csv:29` = `BMad Method,bmad-code-review,Code Review,CR,"Story cycle: If issues back to DS if approved then next CS or ER if epic complete.",,,4-implementation,bmad-dev-story,,false,,` — phase `4-implementation`, `preceded-by bmad-dev-story`, which is what the story/sprint state `review` selects. Config resolved with `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` (`user_name: Ezop`, `communication_language: Polish`, `document_output_language: English`). Customization resolved with `python3 _bmad/scripts/resolve_customization.py --skill /home/ezop/repos/3d-portal/.claude/skills/bmad-code-review --key workflow` → `{"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}`; no team override (`_bmad/custom/bmad-code-review.toml` absent), no user override. Step files `step-01-gather-context` → `step-02-review` → `step-03-triage` → `step-04-present` executed in order.

**Provenance correction to §20.5 item 2 (recorded here, §20 left untouched).** The prior pass reported that the `persistent_facts` glob `**/project-context.md` matched no file in this worktree. That is **not** the case at this pass: `_bmad-output/project-context.md` exists here (tracked, 42 KB) and **was loaded** as persistent facts — its backend/testing/quality rules were carried through this review. Stated as a correction of the earlier environment claim, not as a finding against the implementation.

**Environment and review target.** Worktree `/home/ezop/worktrees/3d-portal-e49-3-dev`, branch `feat/E49.3-category-read-api-and-model-scope`, baseline `2d4fd75832ce54b38cd6a69c986fb323818b778b`. Diff source: **uncommitted changes**, `{review_mode}` = `full`, `{spec_file}` = this story, `{story_key}` = `49-3-category-read-api-and-model-scope`. Scope re-derived at this pass: 8 modified product/doc files + 2 untracked new test modules + 2 workflow records — exactly the §7 ratified set, with no stray untracked file.

**Honesty statement — read before quoting anything below.** This re-review is **Claude / native BMAD only**. **No human reviewed this code.** No Ezop signature, no Ezop review and no Laura review is recorded, implied or claimable from it. **Not done by this pass and still outstanding:** the independent `laura-aider-review-diff` rerun, the frozen `infra/scripts/check-all.sh` 16/16, the NFR26-DETERMINISM-1 determinism triple, and the commit / ff-only merge / push / deploy. **T10.1–T10.4 remain unchecked.** No product, test or documentation file was edited by this pass; no fix was applied; no commit, push, merge, deploy, seed or migration was performed; no live or production database was opened, read or written. Every command ran against the throwaway session-scoped SQLite from `tests/conftest.py::_isolated_db`, against a reviewer-built scratch directory in `/tmp`, or against `git` metadata. **The implementer's claimed sentinel mutation and hash restoration were re-derived independently, not trusted.**

### 22.1 Executed evidence

| # | Check | Command / method | Result |
|---|---|---|---|
| RR-1 | Scope | `git status --porcelain`; `git diff --stat 2d4fd75` | 8 modified product/doc + 2 new tests + 2 workflow records; `760 insertions, 81 deletions` — the ratified §7 set, unchanged by the fix pass ✔ |
| RR-2 | Implementer's restoration hash | `sha256sum apps/api/tests/test_openapi_agent_surface.py` | `908c87a93c43f3dfdb8ef7235f63f0bd787a5708b9b502564f64b66af69d88b6` — **matches** the `908c87a9…` claimed in §19/§15 ✔ |
| RR-3 | Byte-containment of the fix | positional split of `git show 2d4fd75:apps/api/tests/test_openapi_agent_surface.py` vs the working file into 26 top-level blocks, compared byte-wise | **exactly 2 blocks differ**: the module preamble (import block) and `test_retired_taxonomy_read_route_is_gone`. The other **24** blocks — including `test_retired_taxonomy_admin_crud_route_is_gone`, `test_no_category_schemas_in_components`, `test_no_category_properties_on_model_schemas` and every 47.5 residual/naming guard — are **byte-identical** ✔ |
| RR-4 | Import-block containment | `git diff -U0` hunk headers | `@@ -19,0 +20,2 @@`, `@@ -20,0 +23 @@`, `@@ -21,0 +25,4 @@` — **additions only**, no deletion, module docstring untouched; the remaining three hunks all fall inside baseline lines 361-369, i.e. the one test body ✔ |
| RR-5 | Production untouched by the fix pass | `sha256sum app/modules/sot/{service,router,schemas}.py` | `service.py` = `1ce652b1cb7ffdbb68b567bec9aed4d5cd5b34df204611f91959582d5ecc5efa` — **byte-identical to §20 R-3**, so the T5.1 restoration still holds and the CR-1 pass changed no production code. Recorded for future passes: `router.py` `40c16386fda359ef63616e671c4a7a532c9f0cdc05c312a596c204fb68f109ca`, `schemas.py` `5cd0d2217354356c245029c2eb2d0bbd5273eee6c5040c8b15a4594474f12845` ✔ |
| RR-6 | **CR-1 non-vacuity on a fresh standalone DB** | `.venv/bin/pytest -q tests/test_openapi_agent_surface.py::test_retired_taxonomy_read_route_is_gone` | `1 passed, 2 warnings in 0.33s` — a single-test run creates a brand-new session DB, so the `assert seeded is not None` gate **provably executed**. This is the exact invocation under which the pre-fix guard asserted nothing ✔ |
| RR-7 | Module standalone | `.venv/bin/pytest -q tests/test_openapi_agent_surface.py` | `35 passed, 2 warnings in 0.94s` ✔ |
| RR-8 | Sibling 47.5 guards | `.venv/bin/pytest -q tests/test_openapi_agent_surface.py -k "retired or residual or naming or admin"` | `5 passed, 30 deselected` ✔ |
| RR-9 | Targeted non-regression | `.venv/bin/pytest -q tests/test_sot_categories.py tests/test_sot_models_category_scope.py tests/test_sot_auth_boundary.py tests/test_route_enforcement_gate.py tests/test_sot_models_list.py tests/test_sot_models_detail.py tests/test_sot_schemas.py` | `124 passed, 207 warnings in 19.63s` ✔ |
| RR-10 | Lint | `.venv/bin/ruff check .`; `.venv/bin/ruff format --check .` | `All checks passed!`; `277 files already formatted` ✔ |
| RR-11 | **Independent mutation harness** (built in `/tmp/cr1mut`, conftest copied, **no repo file touched**) | control + two mutants of the repaired test, run with `-p no:cacheprovider` | control `1 passed`; **M1** (expected key set widened with `"children"`) → `AssertionError: unexpected browse item shape: ['description_en', 'description_pl', 'id', 'model_count', 'name_en', 'name_pl', 'parent_id', 'position', 'slug']`; **M2** (seeding block deleted) → `AssertionError: seeded category 'browse-guard-8d1771ca' missing from []` / `assert None is not None` ✔ |
| RR-12 | Cross-file contamination of the persisted seeded row | grep for consumers of `/api/categories` and for whole-table `select(BrowseCategory)` assertions | the only HTTP consumers are `test_sot_categories.py`, `test_sot_models_category_scope.py`, `test_sot_auth_boundary.py`, all scoped through the unique-prefix `_mine` helper; **every** global-count assertion lives in `test_seed_browse_categories.py`, which builds a per-test `_fresh_engine(tmp_path)`, and `test_browse_category_entity.py` uses `sqlite:///:memory:` — so the seeded row cannot flip any assertion anywhere ✔ |

### 22.2 CR-1 disposition — **RESOLVED**

`apps/api/tests/test_openapi_agent_surface.py:369-406` (`test_retired_taxonomy_read_route_is_gone`).

Every element the blocker required is present and was verified, not read:

- **Seeds its own row against the real test engine.** `slug = f"browse-guard-{uuid.uuid4().hex[:8]}"`, then `with Session(get_engine()) as session: session.add(BrowseCategory(slug=slug, name_en="Browse guard")); session.commit()`. `get_engine()` is the same session-scoped SQLite the app serves — `conftest.py::_isolated_db` calls `get_engine.cache_clear()` and `init_schema(get_engine())` precisely so direct engine access and the `TestClient` share one database. RR-6 confirms behaviourally that the seeded row is what the route returns.
- **Asserts the specifically seeded item is present** before anything else: `seeded = next((i for i in body if i.get("slug") == slug), None)` followed by `assert seeded is not None`. Not "some element", not "the first element" — that exact slug.
- **Exact nine-key flat browse contract**, asserted as set **equality** (not containment) against `{id, slug, name_en, name_pl, description_en, description_pl, position, parent_id, model_count}`. RR-11/M1 proves the equality executes and is load-bearing: widening the expected set by one key fails the test and prints the true nine keys the wire actually carries.
- **No nesting**: `"children" not in seeded` and `"subcategories" not in seeded` on the seeded item, plus the same negative swept across the whole array — the structural discriminator against the retired recursive `CategoryTree`.
- **`parent_id` scalar-or-null** (`is None or isinstance(..., str)`) and **`model_count` integer** (`isinstance(seeded["model_count"], int)`), both applied to the found item.
- **Runtime-assembled route literal retained**: `client.get("/api/" + "categories")`, so the Story 47.5 §11 residual-symbol grep stays clean. The sibling admin guard keeps its own `"/api/admin/" + "categories" + "/…"` literal, byte-unmodified (RR-3).
- **No test-order or shared-row dependency remains.** The undeclared coupling §20 objected to — the guard only being non-empty because `test_browse_category_entity.py` happened to run earlier — is gone: the row the assertions target is created by the test itself under a `uuid4`-derived slug that no other module can produce or collide with. RR-6 is the direct proof (single test, fresh DB, passes with the gate executed); RR-11/M2 is the counter-proof (delete the seeding and the same test fails against `[]`, reproducing the original CR-1 measurement `len(body) == 0`).
- **The three added DB-seeding imports are each mechanically necessary and each used exactly once**: `from sqlmodel import Session` (the context manager), `from app.core.db.models import BrowseCategory` (the row constructed), `from app.core.db.session import get_engine` (the engine handle). `uuid` and the two auth imports (`ACCESS_COOKIE`, `encode_token`) pre-date this pass and are still used. `ruff` (RR-10) independently rules out an unused import.
- **No other test body changed** — RR-3's block-level byte comparison is the evidence, and it is stronger than a hunk read: 24 of 26 blocks hash-identical to baseline.

**On the implementer's claimed sentinel mutation and hash restoration.** The claim was not accepted on its word. RR-2 confirms the file's current sha256 is exactly the `908c87a9…` claimed, and RR-11 independently reconstructs the mutation the implementer says they ran: the reviewer-built M1 mutant produces precisely the described failure mode (`assertion executed and failed`, revealing the true nine keys) from a copy in `/tmp`, leaving the repo file untouched. The claim is therefore corroborated by re-derivation rather than trusted.

### 22.3 Regression check on the rest of the diff

Re-read at this pass and clean: the two new test modules, the `sot` router/schemas/service diff, `test_sot_auth_boundary.py`'s additive block, the doc and operational-script prose changes. `service.py` is hash-identical to the pre-fix state (RR-5), so nothing in the product surface could have moved; `124 passed` (RR-9) covers the read routes, the `?category=` scope, the auth matrix, the route-enforcement gate, the untouched list/detail suites and the schema tests; `ruff` is clean repo-wide. §20's AC-by-AC audit therefore still stands, with AC-24(b) now **discharged** instead of failing.

### 22.4 Findings (this pass)

**Critical: none. Important: none.**

**RR-N1 — Minor — note, no action — stale reviewer/implementer byproduct in the ignored bytecode cache.**
`apps/api/tests/__pycache__/test_zz_cr1_probe.cpython-312-pytest-9.0.3.pyc` survives from the implementer's temporary CR-1 reproduction module, whose `.py` source is correctly gone. `git check-ignore` confirms it is covered by `.gitignore:3` (`__pycache__/`), pytest collects `.py` files and never a bare `.pyc`, and `git status` is unaffected. Recorded for completeness because the fix pass claimed "no other file touched" and this is the one on-disk residue; it changes no behaviour and needs no action.

**RR-N2 — Minor — note, no action — the `parent_id` `isinstance(str)` branch is not exercised inside this guard.**
`apps/api/tests/test_openapi_agent_surface.py:401`. The seeded row has `parent_id = None`, so `assert seeded["parent_id"] is None or isinstance(seeded["parent_id"], str)` is satisfied by its first disjunct and the scalar-string case never runs *here*. This is not a gap in coverage: the nine-key set equality already rejects an embedded parent node (a dict-valued nesting would have to arrive under a key the equality forbids), and the genuine non-null scalar case is proven end-to-end at `apps/api/tests/test_sot_categories.py:146` (`assert child["parent_id"] == str(parent_id)`) against a real parent/child pair. Recorded so nobody later mistakes this line for stronger evidence than it is.

**Carried forward from §20, unchanged and untouched by the fix pass:** **CR-2** (`schemas.py:204` — `ModelDetail.categories` published as optional; `defer` to Story 50.1), **CR-3** (`service.py:246` — whole-table count aggregate to serve one slug; `defer`), **CR-4** (`docs/operations.md:462-463` — one clarifying sentence beyond T8.1; note, no action). None of them was in the remediation's scope, none regressed, and none blocks.

**Dismissed: none.**

### 22.5 Disclosed deviations from the base `bmad-code-review` workflow

1. **No subagents were dispatched** for the Blind Hunter / Edge Case Hunter / Acceptance Auditor layers. This session's operating instructions forbid dispatching agents unless the operator explicitly requests it, and this controller input did not. All three lenses were executed directly in-session against the real diff and real test runs. A disclosed reduction in review independence, not a silent one.
2. **Step-01's CHECKPOINT halt and step-04's HALTs were not offered interactively.** The controller input already fixed the review target, the diff mode, the spec file and the disposition of findings, so the cascade had nothing left to ask.
3. **Step-04's status transition was NOT applied.** The base workflow would move story and sprint key on the review outcome; the controller input overrides this. Story and sprint key stay at **`review`**, `epic-49` stays **`in-progress`**, T10.1–T10.4 stay **unchecked**, and `done` is never set. Disclosed, not silently applied.
4. **Nothing was written to `{implementation_artifacts}/deferred-work.md`.** CR-2/CR-3 remain recorded in §20.3 only; promoting them into the shared ledger is a controller action.

### 22.6 Verdict

**`APPROVE`** — Critical **0**, Important **0**, Minor **2** (RR-N1, RR-N2; both `note, no action`), Dismissed **0**.

The single Important finding from §20 (CR-1) is genuinely fixed, and the fix is confined, non-vacuous and independently proven so: the guard seeds its own uniquely-slugged row through the real test engine, pins that exact item, and asserts the exact nine-key flat browse contract with the recursive-taxonomy negatives intact; it passes standalone on a fresh database and fails under both reviewer-built mutants; 24 of 26 top-level blocks in the file are byte-identical to baseline, the runtime-assembled route literals and every sibling 47.5 guard among them; `service.py` is unchanged, so no production behaviour moved. §20's historical `REQUEST_CHANGES` stands as written.

Story status remains **`review`**; `epic-49` remains **`in-progress`**; T10.1–T10.4 remain **unchecked**. The independent Aider rerun, the frozen `infra/scripts/check-all.sh` 16/16, the NFR26-DETERMINISM-1 determinism triple and the commit / ff-only merge / push / deploy — plus any live-database action — are **not** performed by this re-review and remain outstanding controller-owned work.

## 23. Controller final disposition

**Disposition: DONE — Laura/controller, 2026-07-26.** This is a controller decision under Ezop's standing Initiative 26 authorization, not an Ezop signature or a claim that Ezop reviewed this code.

**Review chain.** Native §20 correctly returned `REQUEST_CHANGES` (Critical 0 / Important 1) for the vacuous AC-24 repair. The same implementer fixed CR-1 test-side only. Fresh native §22 re-review returned `APPROVE` (Critical 0 / Important 0) with CR-1 independently proven non-vacuous. The pre-fix Aider `APPROVE` is retained but rejected as insufficient because it missed CR-1; the fresh post-fix Aider rerun returned literal `APPROVE` (Critical 0 / Important 0). Full external disposition is in §21.

**Frozen gates.** `.hermes/run-logs/e49-3-controller-check-all-20260726.log` ended exit 0 with `all green.` and 16/16: API **1827 passed / 3 skipped**, Web Vitest **785 passed**, visual **536 passed / 32 expected skips**. The complete 10-file product/doc manifest was hash-stable before and after at `e58fe1a2f51fd8e4fc3adab62331d9dc120f22be2aaf2bbb2eb881e99295a54d`. NFR26-DETERMINISM-1 passed: three consecutive full API suites each returned **1827 passed / 3 skipped / 2101 warnings**, all exit 0, with the same product/doc hash before and after; proof `.hermes/run-logs/e49-3-controller-api-determinism-proof-20260726.txt`.

**Scope and safety.** The final tree contains exactly the validated 10 product/doc files plus this story and `sprint-status.yaml`; no migration, seed, DDL, dependency/lockfile, auth allowlist, `app/main.py`, E49.4 or E49.5 work. No live database was opened, read or written during development or review. CR-2 (`ModelDetail.categories` requiredness for Story 50.1) and CR-3 (single-slug count optimisation for E49.5) remain explicit non-blocking defers in §20; CR-4 is a truthful docs note.

Story and sprint status are `done`; `epic-49` remains `in-progress`. T10.1–T10.4 are complete. One atomic story commit exists; this final checkbox/status closeout is folded into the same commit by amend. The branch is a one-commit descendant of baseline `2d4fd75`. Controller executes the ff-only merge, push, controlled deploy and read-only live verification immediately after this amended artifact is committed; Git and deploy logs are the external evidence rather than self-referential SHA text in this artifact.
