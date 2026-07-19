---
baseline_commit: a05a3a5
---
# Story 42.3: Category-endpoint removal

Status: SUPERSEDED / RELOCATED — 2026-07-19 by operator-approved `bmad-correct-course` (was: BLOCKED — procedural)

> **SUPERSEDED / RELOCATED (2026-07-19).** The `BLOCKED_PROCEDURAL` verdict below was resolved by the E42 `bmad-correct-course` APPLY pass — SCP `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-19-e42-deferred-coupled-cutover.md` (operator-approved "Deferred coupled cutover"). The 42.3 scope is **relocated to the terminal cutover epic E47** and split:
> - **Story 47.4 — Category API-surface retirement** takes the route/service/route-only-schema removals (`GET /api/categories`, admin category CRUD, `create/update/delete_category`, `list_categories_tree`, `CategoryNode`/`CategoryTree`/`CategoryCreate`/`CategoryPatch`). Runs **after** all `GET /api/categories` consumers (E43–E45 FE + 47.3 hydrate/runbook) are gone. Reversible by code revert.
> - **Story 47.5 — Category ORM + DTO + `0019` atomic cutover** takes the load-bearing removals this artifact fenced out (`CategorySummary`, `ModelDetail.category`, `ModelSummary.category_id`, `create_model`/`update_model` validation, `class Category`, `Model.category_id`, `0019_drop_category`) — **one atomic commit**, after 47.4 + the 45.3 create-form. Closes TB-053. **Destructive-go DEFERRED to 47.5 dev-go** (verified pre-`0019` `.190` DB backup required).
>
> The **Dependency Audit and contradiction resolution below are preserved verbatim** — they are the code-grounded evidence that drove the relocation and remain the reference for authoring 47.4/47.5 (do NOT create the implementation-ready 47.4/47.5 stories yet — `bmad-create-story` runs at their turn in the sequence). Do **not** dev the `42-3` / `42-5` sprint keys; see `epics.md` §E42 (superseded stories) and §E47 (47.4/47.5).

<!--
Authored 2026-07-19 via native bmad-help → bmad-sprint-status (consulted) → bmad-create-story
dependency-audit gate (Claude author; Laura controller). The create-story flow STOPPED at the
mandatory pre-ready dependency audit: the approved E42 story sketch for 42.3 cannot be
implemented narrow / green / non-breaking as sequenced. Per BMAD vanilla-first ("if a skill
rejects the current state, STOP and consult the operator") this artifact is a truthful
procedural/triage draft, NOT a ready-for-dev story. The required native next route is
bmad-correct-course (E42 re-sequencing/split + assign the orphaned ORM-removal story).
Sprint status stays `backlog`. See "## Verdict", "## Dependency Audit", "## Decision Needed".
-->

## Story (as sketched — target, not yet buildable)

As the **backend catalog contract**,
I want **the category read endpoint (`GET /api/categories`), the admin category CRUD endpoints (`POST/PATCH/DELETE /api/admin/categories`), the `create/update/delete_category` service functions, and the `Category*` request/response schemas removed**,
so that **the category API surface is retired in favour of the facet-tag taxonomy (Initiative 25)**.

Traces: **FR25-FILT-1**, FR25-SOT retirement (Epic E42; SCP `sprint-change-proposal-2026-07-17-tag-taxonomy-catalog-rebuild.md`; architecture.md § Initiative 25 Decision AW).

## Verdict

**BLOCKED_PROCEDURAL.** The 42.3 sketch as written removes category endpoints **and** "all `Category*` schemas" while story 42.5 is what later drops `category_id`/`category` from `ModelCreate`/`ModelPatch`/`ModelDetail`/`ShareModelView`, and while the destructive ORM/DB removal (`class Category`, `Model.category_id`, migration `0019_drop_category`) is an **orphaned action item with no owner story**. Code-grounded audit confirms all five flagged contradictions are real, not hand-waveable. The intra-E42 dependency is **inverted**: 42.3 (schema + endpoint removal) is sketched upstream of 42.5 + the ORM removal, but it structurally **depends on them**. This requires a re-sequencing/split decision that only `bmad-correct-course` + the operator may make; inventing a workaround would either break a retained live contract or leak 42.5/E43–E47 scope.

## Current on-`main` state (why the sketch is out of order)

- E41 shipped **additive-only** migration `0018_facet_tags` (`tag_group` + `Tag.group_id`/`group_position`). The destructive drop was **deferred to E42** (sprint-status.yaml:300-302; epic-41 retro).
- ORM `class Category` (`_entities.py:29`) and `Model.category_id` (`_entities.py:109-111`, **NOT NULL + FK `category.id` RESTRICT + indexed**) are **still live on `main`**. The category table + `model.category_id` column are still in the DB.
- `sprint-status.yaml` `action_items` (E41) explicitly owe `0019_drop_category` (forward-only destructive DDL) to "the E42 ORM-removal story … same migration/commit as removal of `class Category` + `Model.category_id`." **No such story exists** among 42.1–42.5. E42 sprint-planning did not create it (audit finding — this is itself a planning gap correct-course must close).

## Dependency Audit (code-grounded; all references verified 2026-07-19 @ `a05a3a5`)

### Removable in 42.3 *in isolation* (category-route-only, no retained-contract embed)
- `GET /api/categories` route — `sot/router.py:48-64` (`get_categories`, `response_model=CategoryTree`).
- Admin CRUD — `sot/admin_router.py`: `POST` (774-801), `PATCH /{category_id}` (804-837), `DELETE /{category_id}` (840-861).
- Write service fns — `sot/admin_service.py`: `create_category` (1150), `update_category` (1200), `delete_category` (1274), helper `_would_cycle` (1134).
- Read tree service — `sot/service.py`: `list_categories_tree` (63-124) — used **only** by `GET /api/categories`.
- Schemas usable-only-by-category-routes — `CategoryNode` (schemas.py:26), `CategoryTree` (schemas.py:31), `CategoryCreate` (admin_schemas.py:220), `CategoryPatch` (admin_schemas.py:246).
- Route-enforcement gate: **no allowlist edit needed** — category routes are authenticated (`current_user` / admin-or-agent) and are **not** in `main.py:_PUBLIC_ROUTES`. `test_route_enforcement_gate.py` keys off the live route table, so it stays green after removal automatically (audit §6).

### NOT removable in 42.3 — load-bearing for RETAINED contracts (= 42.5 + ORM-removal scope)
- **`CategorySummary` (schemas.py:18) is embedded in the RETAINED `ModelDetail.category` (schemas.py:167)**, resolved live by `get_model_detail` (`service.py:438,486`) and mirrored by `ShareModelView.category: str` (`share/models.py:40`, resolved `share/router.py:144,228`). ⇒ "remove **all** `Category*` schemas" is **impossible** in 42.3 without also editing `ModelDetail`/`ShareModelView` — which is explicitly **42.5** work.
- **`ModelSummary.category_id: uuid.UUID` (schemas.py:148) is REQUIRED** on the retained list response; `ModelCreate.category_id` REQUIRED (admin_schemas.py:32); `ModelPatch.category_id` (admin_schemas.py:56). Dropping these is **42.5**.
- **`create_model`/`update_model` (admin_service.py:152-230) hard-validate `select(Category).where(id==payload.category_id)` → "category not found" (164-167, 227-230)** and import `Category`, `CategoryCreate`, `CategoryPatch` (29,42-43). ⇒ the retained model create/patch path still requires the `Category` ORM + category schemas until 42.5 + ORM removal.
- **ORM `class Category` + `Model.category_id` (NOT NULL)** — removal needs migration `0019_drop_category` + the orphaned ORM-removal story (per E41 action_items).

### Cross-cutting breakage if `GET /api/categories` is removed on `main` ahead of the FE cutover
- **Frontend (shipped, auto-deploys to `.190` on every `main` push):** `useCategoriesTree` (`web/src/modules/catalog/hooks/useCategoriesTree.ts:9` GET `/categories`), `CatalogList.tsx`, `CategoryTreeSidebar.tsx`, admin `AddModelForm.tsx` (`useCategoriesTree` + category picker) all call it. Removal ⇒ **live 404 / broken catalog browse + broken admin model-add on `.190`** until E43 (43.2 retire `useCategoriesTree`) / E44 / E45 land. This is a production regression on the deployed FE, not merely a test failure.
- **Hydrate agent workflow:** `apps/api/scripts/hydrate_local_tree.py:177` GETs `/api/categories` in `_build_category_path_map`, consumes `model["category_id"]` (:346) → path (:348). Removal breaks the supported reverse-sync/hydrate path; `category_id` stays on `ModelSummary` until 42.5, so hydrate is only fully repaired after 42.5 + E47 runbook cutover.
- **Agent add-model runbook + docs:** `docs/agents-add-model-runbook.md:55,62,284-292,388-389,395` (category pre-flight + `ModelCreate.category_id`); `docs/operations.md:112,458,461,594`; `docs/project-overview.md`. E47 (47.3) owns this cutover.
- **Bootstrap smoke test:** `test_bootstrap_agent.py:79-95` **POSTs `/api/admin/categories`** and asserts 201 — breaks on admin-CRUD removal.
- **Category route tests to delete/update:** `test_sot_categories.py`, `test_sot_admin_categories.py`, `test_sot_auth_boundary.py:120,171,221,277,304` (default-deny assertions on `/api/categories`).
- **ORM-seed model fixtures (break on `category_id` DROP, i.e. 42.5/ORM, NOT on route removal):** ~25 files seed `Model(category_id=...)` directly (audit §8) — flagged so the correct-course sequencing accounts for the 42.5/ORM blast radius.

## Contradiction resolution (the five flagged items — all CONFIRMED, none hand-waved)
1. **`ModelDetail` embeds `CategorySummary` until 42.5** — CONFIRMED (schemas.py:167). ⇒ 42.3 cannot remove all `Category*` schemas; `CategorySummary` must survive 42.3.
2. **`hydrate_local_tree.py` needs `GET /api/categories` while create still needs `category_id`** — CONFIRMED (:177/:346). ⇒ route removal breaks a supported agent workflow before 42.5/E47.
3. **Tests/bootstrap create categories via admin endpoint / seed `category_id`** — CONFIRMED (`test_bootstrap_agent.py:79-95` uses admin CRUD; ~25 files ORM-seed `category_id`).
4. **Frontend + visual tests still reference categories; E43/E44 retire later** — CONFIRMED. Backend route removal ahead of FE cutover is **not** silently tolerable (auto-deploy to `.190` ⇒ live 404). Needs an explicit operator decision: re-sequence, or accept a temporary broken-catalog window, or stage compatibility.
5. **Removing an API/SoT surface is destructive** — CONFIRMED. Implementation requires an explicit **Laura/operator destructive gate** (below).

## Decision Needed (operator + `bmad-correct-course`)

Route: **`bmad-correct-course`** (E42 epics/stories re-sequencing + gap closure). Exact decisions:

- **D-1 (orphaned ORM-removal story).** Create the missing E42 story that lands `0019_drop_category` + removal of `class Category` + `Model.category_id` from `_entities.py` in **one** migration/commit (per E41 action_items). Decide its ID/position (e.g. new `42.6` or fold into `42.5`).
- **D-2 (re-sequence 42.3 vs 42.5/ORM/FE).** Choose one:
  - **(a) Re-order:** move category-**read-route** + `CategorySummary`/`ModelDetail.category`/`ModelSummary.category_id` removal to **after** 42.5 + the D-1 ORM removal + the E43–E45 FE cutover. 42.3 becomes admin-**write**-CRUD-only removal (see D-3).
  - **(b) Documented split:** `42.3a` = remove admin `POST/PATCH/DELETE /categories` + `create/update/delete_category` + `CategoryCreate/CategoryPatch` (keep `GET /api/categories` + `CategorySummary`/`CategoryNode`/`CategoryTree` alive for FE/hydrate/runbook). `42.3b` (post-FE-cutover) = remove `GET /api/categories` + tree service + tree schemas. `CategorySummary` deletion deferred to 42.5/ORM.
  - **(c) Tolerate a broken window:** keep the sketch order but operator explicitly accepts a temporary broken catalog/admin-add on `.190` between 42.3 merge and the E43–E45 FE cutover (deploy-gate implication — must be recorded).
- **D-3 (bootstrap + create-model reachability).** If admin category CRUD is removed while `ModelCreate.category_id` is still required and `Category` still exists (pre-D-1), there is **no API path to mint a category**. Decide: migrate `test_bootstrap_agent.py` to ORM-seed, and confirm operator-facing model creation only references pre-existing categories in that window (or block admin-CRUD removal until D-1).
- **D-4 (Decision AV/AW doc drift).** Architecture Decision AV states `0018` drops category; the shipped `0018` is additive-only with the drop deferred. File a documentation-correction (candidate **TB**) so the architecture reflects the `0018` additive / `0019` destructive split. Non-blocking; note for correct-course.

## Destructive implementation gate (MANDATORY before any dev-go)

Removing a live API/SoT surface is **destructive and forward-only** (per `NFR10-SCHEMA-MIGRATION-1` precedent for the coupled ORM removal). Implementation of **any** variant above requires an **explicit Laura/operator destructive-go**, recorded here, that acknowledges: (1) `GET /api/categories` + admin category CRUD leave the public surface; (2) coupled ORM removal (D-1) is unrecoverable by design (`downgrade()` raises); (3) the `.190` auto-deploy window implication chosen in D-2. Spec validation may proceed without this gate; **dev-story may not**.

## Definition of Ready — status per item (all-or-nothing for ready-for-dev)
- [x] Exact route/service/schema removals inventoried (above) with retained-compatibility surface identified.
- [ ] **No-404-drift on retained routes** — NOT satisfiable under sketch order (FE/hydrate/runbook 404). Requires D-2.
- [x] Route-enforcement/OpenAPI/auth impact assessed (allowlist needs no edit; category route tests need deletion).
- [ ] **Script/runbook/frontend transition handling** — requires D-2/D-4 sequencing decision.
- [ ] **Schema removal scope** — blocked by retained `CategorySummary`/`ModelDetail` (needs 42.5 first).
- [ ] Orphaned ORM-removal story owner (D-1).
- [ ] Destructive implementation approval gate (unsigned).
- Gate result: **NOT READY** — 5 of 7 open, 3 requiring operator/correct-course decisions.

## Native workflow record
- `bmad-help` — run (session-start handshake). Phase 4-implementation; canonical story-cycle entry is `bmad-create-story`, but its pre-ready dependency audit gate failed.
- `bmad-sprint-status` — data source (`sprint-status.yaml`) consulted directly; E42 `in-progress`, 42.1/42.2 `done`, 42.3 `backlog`.
- `bmad-create-story` (create) — **entered, STOPPED at dependency-audit gate**; not carried to ready-for-dev per vanilla-first STOP rule.
- **Required next:** `bmad-correct-course` (operator-gated) for D-1…D-4, then re-run `bmad-create-story` on the re-sequenced/split story.
