---
title: 'Story 47.4 — Category API-surface retirement + FE category-tree type/hook cleanup'
type: 'chore'
created: '2026-07-22'
status: 'superseded-absorbed-into-47-5'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

> **SUPERSEDED / ABSORBED → 47.5 (2026-07-22).** The `blocked` verdict below was resolved by the operator-approved `bmad-correct-course` APPLY pass — SCP `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md` (exact operator GO phrase `GO E47 ATOMIC CUTOVER`, Michał/Ezop via controller session, 2026-07-22). Story 47.4's full scope is absorbed into Story **47.5** as internal phases (b) FE hook/types + (c) BE API surface of one atomic cutover, whose phase (a) additionally removes both live consumers documented below (`AddModelForm` selector per the 45.3↔47.5 handshake; `ModelHero` breadcrumb with no replacement) and whose phase (d) is the original 47.5 ORM+DTO+`0019` scope. This file was authored in the bmad-loop worktree `.bmad-loop/runs/20260722-190446-a27a/.../47-4-category-api-surface-retirement/` and is recorded here (canonical tracked surface) with a terminal status; the investigation below is preserved **verbatim** — its Code Map is the authoritative inventory for the merged 47.5 story's phases (b)-(c). Do **not** dev the `47-4` sprint key; `bmad-create-story` runs next on the merged 47.5 scope. Historical: this scope was earlier RELOCATED from 42.3 (2026-07-19 SCP).

<intent-contract>

## Intent

**Problem:** `epic-47-context.md` and `epics.md:4352` scope 47.4 as retiring the category-tree API surface (`GET /api/categories`, the three admin category CRUD routes, their service functions, and the route-only `CategoryNode`/`CategoryTree` schemas) plus the symmetric FE `useCategoriesTree` hook and `CategoryNode`/`CategoryTree` types, gated on a stated hard precondition: "every consumer of `GET /api/categories` / `category_id` is gone." Investigation of the current worktree shows that precondition is **not met** — two live production consumers of `useCategoriesTree` (and transitively `GET /api/categories`) still exist, and the planning artifacts disagree on why/whether that's expected.

**Approach:** BLOCKED — see Boundaries § Block If. This story cannot be scoped further without an operator decision on how to resolve the two live-consumer findings below.

## Boundaries & Constraints

**Always:** N/A — no execution scope has been confirmed yet.

**Block If:**
1. `apps/web/src/modules/admin/AddModelForm.tsx:81` calls `useCategoriesTree()` (`apps/web/src/modules/catalog/hooks/useCategoriesTree.ts:6-12`, backed by `GET /api/categories`) to populate its category `<select>` (lines 53-67 `flattenCategories`, 143-144, 194-206), which feeds `category_id` into the live `POST /admin/models` payload. Per `epics.md:4352` and sprint-status (`45-3-...`: "admin category-selector removal deferred to the 47.5 atomic handshake (selector byte-for-byte untouched)"), this migration was **explicitly, operator-approved deferred to story 47.5**, not resolved in 45.3 as the original epic sketch assumed. If `GET /api/categories`/`useCategoriesTree` are retired now, this selector breaks in production the moment `main` deploys (epic-47-context.md's own stated risk: "the app auto-deploys `main` HEAD, so removing a still-consumed surface produces a live outage, not just a failing test").
2. `apps/web/src/modules/catalog/components/ModelHero.tsx` (lines 5, 14, 26-35, 65, 73-77, 93-99) also calls `useCategoriesTree()` — independently of `AddModelForm` — to fetch the full category tree and walk `parent_id` from `detail.category` (the in-scope, retained `CategorySummary`) up to the root, rendering a category-ancestry breadcrumb on the model detail page. Unlike (1), **no planning artifact documents this dependency as deferred or scheduled for migration.** `spec-45-2-catalogdetail-grouped-tags.md` (the story that touched `ModelHero.tsx` most recently) explicitly scoped itself to replacing the flat tag-chip row with `TagGroupsSection` and left the `useCategoriesTree`-based breadcrumb untouched (its own Code Map, line 63-64, only mentions the tag-row change; its test-file note explicitly preserves "the existing `useAuth`/`useCategoriesTree` mocks"). `epics.md:4264/4352`'s premise that "`ModelHero`/`CatalogDetail` migrate in 45.2" is stale/incorrect against what 45.2 actually shipped.
3. Because of (1) and (2), retiring `GET /api/categories`, the admin category CRUD routes, `list_categories_tree`/`create_category`/`update_category`/`delete_category`, or the FE `useCategoriesTree`/`CategoryNode`/`CategoryTree` surface **as currently scoped would break two live production features**, not just violate a convention. This needs an explicit operator decision among (non-exhaustive): (a) hold 47.4 until 47.5 lands and merge the two stories' consumer-migration work, (b) expand 47.4's own scope to migrate `AddModelForm` and/or `ModelHero` off the category tree first (which would reopen the already-settled 45.3 deferral decision for `AddModelForm`, and is a genuine product/UX call for `ModelHero`'s breadcrumb — keep it on a different data source, or remove it), or (c) some other resolution. This spec does not guess.

**Never:** Do not silently keep both live consumers wired to a route being "removed" (e.g. deleting the public route table entry while leaving an internal-only path) as a workaround — no planning artifact authorizes a partial/hidden retirement, and it would contradict "API surface retirement" as the story's own name states it.

</intent-contract>

## Code Map

<!-- Confirmed-safe inventory, preserved for whichever resolution path is chosen. Not an execution plan. -->

**Backend — route-only, safe to delete once Block-If is resolved:**
- `apps/api/app/modules/sot/router.py:48-64` -- `GET /api/categories` (public sot_router, `current_user` auth)
- `apps/api/app/modules/sot/admin_router.py:765-792,795-828,831-853` -- admin category create/patch/delete routes (`_current_admin_or_agent_dep`)
- `apps/api/app/modules/sot/service.py:63-124` -- `list_categories_tree()`
- `apps/api/app/modules/sot/admin_service.py:~1303-1479` -- `create_category()`, `update_category()`, `_would_cycle()`, `delete_category()`
- `apps/api/app/modules/sot/schemas.py:26-32` -- `CategoryNode`, `CategoryTree` (route-only response shapes)
- `apps/api/app/modules/sot/admin_schemas.py:291-329` -- `CategoryCreate`, `CategoryPatch`
- `apps/api/tests/test_sot_categories.py`, `apps/api/tests/test_sot_admin_categories.py` -- dedicated test files for the above
- `apps/api/tests/test_sot_schemas.py:159-177` (`test_category_node_recursive_shape`) -- single function to remove, rest of file stays
- `apps/api/tests/test_openapi_agent_surface.py:43-44` -- `CategoryCreate`/`CategoryPatch` entries to drop from `ENRICHED_REQUEST_MODELS`
- `apps/api/tests/test_sot_auth_boundary.py:129,180,230,286,313` -- category-route assertions embedded in a broader parametrized suite; only these params, not the file

**Backend — explicitly out of scope for 47.4 (confirmed, do not touch):**
- `Category` ORM entity, `Model.category_id` column (`apps/api/app/core/db/models/_entities.py:29`) -- 47.5
- `CategorySummary` schema (`sot/schemas.py:18-23`), embedded in `ModelDetail.category` (`schemas.py:179`) -- survives until 47.5
- `apps/api/app/modules/share/router.py:16,144,228`, `share/models.py:40` (`ShareModelView.category`) -- uses the `Category` ORM directly, unrelated to the routes/service above -- 47.5

**Frontend — the two unresolved live consumers (see Block If):**
- `apps/web/src/modules/admin/AddModelForm.tsx`
- `apps/web/src/modules/catalog/components/ModelHero.tsx`

**Frontend — hook/types targeted for deletion, blocked on the above:**
- `apps/web/src/modules/catalog/hooks/useCategoriesTree.ts:6-12` + `useCategoriesTree.test.tsx`
- `apps/web/src/lib/api-types.ts:55-59` (`CategoryNode`), `:61-63` (`CategoryTree`) -- `CategorySummary` (`:47-53`) stays, embedded in the retained `ModelDetail`/`ShareModelView` FE types

**No edits needed:** `apps/api/tests/test_route_enforcement_gate.py` -- no category route is in `_PUBLIC_ROUTES` (`app/main.py:50-61`) and both auth deps used (`current_user`, `_current_admin_or_agent_dep`) are already-recognized `_AUTH_DEP_NAMES`; deleting the routes requires no gate-file change.

## Tasks & Acceptance

Not authored — blocked pending the operator decision in Boundaries § Block If. Authoring tasks now would require guessing which resolution path is chosen, which this spec must not do.

## Spec Change Log

(none — first pass)

## Review Triage Log

(none — blocked before reaching review)

## Design Notes

`epics.md:4264` records the original correction history: `useCategoriesTree` was preserved past E43 specifically because `CatalogList` (44.3), `ModelHero`/`CatalogDetail` (45.2), and `AddModelForm` (45.3) were all still-live consumers, with hook deletion assigned to 47.4 "after the last consumer migrates." `44-3-cataloglist-states` is confirmed `done` and `CatalogList` no longer appears among the live-usage grep hits in this investigation — that migration held. The other two did not fully happen as the sketch assumed: `AddModelForm`'s non-migration is a *documented, operator-approved* deferral (45.3 → 47.5 handshake, per `epic-47-context.md:24` and sprint-status `45-3-...` notes); `ModelHero`'s is *not* documented anywhere — 45.2 scoped itself narrowly to the tag-grouping display change and left the category-ancestry breadcrumb feature (and its `useCategoriesTree` call) completely untouched, and no retro, deferred-work entry, or epic sketch flags this as a known gap. This is a genuine planning gap, not a stale-wording issue a create-story session can self-correct the way `epic-43-retro-2026-07-19.md` Challenge #1/#2 or the E42→E43 SCP precedent did — those corrected *descriptions* of settled facts; here the resolution itself (what happens to `ModelHero`'s breadcrumb, and whether 47.4 waits for or reopens the 45.3 `AddModelForm` deferral) is an open product/sequencing decision with real production-outage risk if guessed wrong, per this repo's own "Stop at unknown unknowns" / "No silent scope creep" AI-agent execution-discipline rules (`project-context.md` § "AI agent execution discipline").

## Verification

Not authored — blocked, see above.

## Auto Run Result

Status: blocked

**Blocking condition:** intent gaps — 47.4's stated hard precondition ("every consumer of `GET /api/categories`/`category_id` is gone") is not met. Two live production consumers of `useCategoriesTree`/`GET /api/categories` remain:

1. `apps/web/src/modules/admin/AddModelForm.tsx` (admin create-form category `<select>`) — non-migration is a *known, operator-approved* deferral to story 47.5 (see `epic-47-context.md:24`, sprint-status `45-3-...` notes), but this directly contradicts 47.4 retiring the same route/hook/types now.
2. `apps/web/src/modules/catalog/components/ModelHero.tsx` (category-ancestry breadcrumb on `/catalog/$id`) — an *undocumented* live dependency; `spec-45-2-catalogdetail-grouped-tags.md` (the most recent story touching this file) explicitly left it untouched and no planning artifact schedules its migration.

**Unanswered questions requiring an operator decision:**
- Should 47.4 be held/merged with 47.5 so both live consumers migrate together with the ORM/DTO cutover, rather than attempting a standalone API-surface retirement now?
- If 47.4 proceeds standalone, should it be rescoped to also migrate `ModelHero`'s breadcrumb (and if so, onto what replacement — drop the breadcrumb entirely, or source ancestry from a different, tag-taxonomy-native mechanism)? This is a UX/product call, not a mechanical code-map fact.
- Does the operator want to reopen the 45.3→47.5 `AddModelForm` selector-removal deferral (move it earlier, into 47.4), or must 47.4 continue to honor that settled handshake and therefore cannot retire the backend route/FE hook it depends on until 47.5?

**Evidence gathered:** full investigation detail is in this file's Boundaries § Block If and Code Map sections above (exact file:line citations for both consumers, the backend route/schema/service inventory, and the planning-artifact citations showing the precondition mismatch: `epics.md:4264,4352`, `epic-47-context.md:23-24,29-30`, sprint-status `epic-45`/`45-3-...`/`47-4-...` entries, `spec-45-2-catalogdetail-grouped-tags.md` Code Map + Design Notes).
