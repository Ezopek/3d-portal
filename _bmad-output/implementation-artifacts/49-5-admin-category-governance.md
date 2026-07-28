---
baseline_commit: 0df663e12d2718dde441dd89418cae0a301386fc
---

# Story 49.5: Admin category governance

Status: ready-for-dev

<!-- Provenance. CREATE: native bmad-create-story (action=create, menu CS), 2026-07-28, Claude Sonnet 5 agent session, routed via the repository's native bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story` (CS / create; preceded-by bmad-sprint-planning, followed-by bmad-create-story:validate, required=true). This session's `.claude/skills/` directory (the actual native skill bodies, gitignored per `.gitignore:143`) was ABSENT from this isolated `git worktree add` checkout — `.claude/skills/` is untracked/regenerated-by-installer content and `git worktree add` only materializes tracked files. Root-caused against `/home/ezop/repos/3d-portal` (same repo, `_bmad/_config/manifest.yaml` byte-identical at version 6.10.0) and repaired by copying that worktree's `.claude/skills/` (90 skill directories, purely local/gitignored, zero git diff) into this worktree before invoking any skill — disclosed as §17.6. Customization resolved via `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow`: no team override (`_bmad/custom/bmad-create-story.toml` absent) and no user override; `activation_steps_prepend`, `activation_steps_append` and `on_complete` all empty; `persistent_facts` = `file:{project-root}/**/project-context.md`, resolved to `_bmad-output/project-context.md` (321 lines, loaded). `discover-inputs.md` executed (epics.md loaded selectively for the Initiative 26 / Epic 49 section; architecture.md loaded selectively for Decisions AX/AY/AZ; no PRD/UX file pattern matched beyond what epics.md already embeds). One `Explore` research subagent was dispatched for exhaustive current-code grounding (tag_group_admin_router.py, audit.py, admin_service.py, admin_schemas.py, test precedents) — disclosed as §17.4, a partial (not full) use of the base workflow's subagent recommendation given this session's serial-tool-call operating mode. `checklist.md` executed against the drafted artifact before finalising (§6 below doubles as the exhaustive-analysis record the checklist requires). Baseline HEAD `0df663e12d2718dde441dd89418cae0a301386fc` on branch `docs/init26-e49-5-create` in worktree `/home/ezop/worktrees/3d-portal-e49-5-create`, working tree clean at start and clean at finish except this artifact and `sprint-status.yaml`. **VALIDATE was NOT run in the Create session** — that session's operating instructions explicitly scoped it to Create only ("Do not invoke validation"), a deliberate, disclosed narrowing of the base `bmad-create-story` cycle (49.1/49.2/49.3/49.4 all bundled Create+Validate in one session; that one did not) — see §17.1. G26-DEVGO is **NOT** granted by that pass. NO human review of any kind. No Ezop signature, no Ezop review, and no Laura review is recorded, implied or claimable from this document. No code, no test, no doc, no live DB touched. No commit, push, merge, deploy, migration, seed, or live action.

VALIDATE: native bmad-create-story (action=validate, menu VS), 2026-07-28, fresh independent Claude Sonnet 5 agent session, same isolated worktree and baseline `0df663e12d2718dde441dd89418cae0a301386fc` on branch `docs/init26-e49-5-create`. Routed via `AGENTS.md` / `CLAUDE.md` / `_bmad-output/project-context.md` / the Laura Agent Rulebook, then `_bmad/_config/manifest.yaml` (BMad 6.10.0) + `bmad-help.csv:27` (VS row: action=validate, phase 4-implementation, preceded-by `bmad-create-story:create`, followed-by `bmad-dev-story`, required=false) + `skill-manifest.csv:40`, confirming `bmad-create-story:validate` as the canonical action after Create. `.claude/skills/bmad-create-story/` was already present (Create pass's §17.6 repair) and used as-is; the Validate action's substance is `checklist.md`, executed under its own "When Running in Fresh Context" protocol — the story file and every source document re-derived independently rather than trusted. **Verdict: PASS** — full evidence, re-derived citations and the two explicit priority arbitrations are recorded in §16. Status advanced `ready-for-validation` → `ready-for-dev`; `epic-49` unchanged at `in-progress`. **G26-DEVGO remains NOT granted** — validation is not implementation authorization. NO human review of any kind in this pass either: no Ezop signature, no Ezop review, no Laura review recorded or implied. No product, test, config, or migration file touched; no live DB, no network, no commit, push, merge, deploy, migration, or seed. Only this artifact and `sprint-status.yaml` were written. -->

## 1. Story

As an **admin**,
I want **to create, rename/reorder/reparent and delete browse categories, and to atomically set (replace) the full set of categories assigned to a model**,
so that **the browse-category taxonomy stood up by Stories 49.1–49.3 can actually be curated — the eight starter categories from 49.2 are just a seed, and this is the only write surface that lets an admin correct, extend, or retire that taxonomy and assign models to it, with every change auditable.**

**Epic:** E49 — Browse-category data + additive API foundation (backend).
**Story key:** `49-5-admin-category-governance` *(renumbered from 49.6 by the 2026-07-26 controller review; there is no Story 49.6).*
**Requirements:** FR26-ADMIN-1 (admin CRUD/reorder/replace-set; 409-unless-detach delete; audit per write), FR26-CAT-3 (1–3 per model is an advisory warning owned by 52.2, not this story — see §10), FR26-CAT-4 (nullable `parent_id`; service-layer depth-2 ceiling; flat MVP UI).
**Architecture:** Decision AY "Admin governance" sub-section (`architecture.md:3334-3341`) is the canonical source for the write contract; Decision AX (`architecture.md:3285-3301`) supplies the entity shape and the depth-2/self-cycle service-layer mandate being enforced here.
**Depends on:** Story 49.1 (`done`, entities + migration, live at this baseline), Story 49.3 (`done`, read API — `GET /api/categories[/{slug}]`, `ModelDetail.categories`, unmodified by this story). **Hard prerequisite for** Story 52.2 (admin category management screen — the UI over this API).

**This story writes to `browse_category` and `model_browse_category`.** It is the first story in Initiative 26 to do so; every prior E49 story (49.1–49.4) was additive-schema or read-only.

## 2. Gate and authorization posture (truthful)

- **G26-DEVGO GRANTED 2026-07-28 by Laura/controller** under the operator's standing Initiative 26 delegation, after controller audit of the fresh native Validate `PASS`, the exact two-path workflow diff, clean `git diff --check`, and parsed sprint state. This is a Laura/controller authorization only: **never an Ezop signature, Ezop review, or claim that a human reviewed the artifact.** It authorizes native `bmad-dev-story` on an isolated Story 49.5 branch; the implementer still may not independently review, commit, push, merge, deploy, or touch live state.
- **No human has reviewed this document.** Not Ezop, not Laura, not any other agent acting as a reviewer — this holds for both the Create pass and the Validate pass. Every claim, citation, and design decision below is Claude/native-BMAD-session-only; the Validate pass re-derived them independently from source, which is agent-independence, not human sign-off.
- **No live-database action of any kind, in either pass.** All research in §6 and all re-derivation in §16 read source files and prior committed artifacts only; no test was executed, no throwaway SQLite database was built, no `pytest` command ran.
- **Live posture (inherited, not re-measured here):** at the 49.4 closeout the live database carried eight seeded `browse_category` rows (Story 49.2) and **zero** `model_browse_category` rows. Consequently, on first deploy of this story, every `POST/PATCH/DELETE /api/admin/categories` call against a real category will succeed with no assignment-conflict path exercised until an admin actually assigns a model — the 409-in-use and `detach=true` paths are real and tested here (§4, §5) but will not be naturally exercised on live data until 52.2 or a manual assignment exists.
- **G26-ROUTE-PATH, G26-CAT-SET, G26-UXGATE, G26-SCP-RATIFY — closed**; none of them gate this story. G26-MIGRATE does not apply (§3.1 — no DDL).

## 3. Binding constraints (a violation is a story defect, not a preference)

1. **No destructive DDL, no schema migration, no seed behaviour.** `browse_category` and `model_browse_category` are exactly the tables Story 49.1 shipped (`_entities.py:130-183`, `migrations/versions/0020_browse_categories.py`) — this story adds **zero** columns, indexes, or tables. `apps/api/scripts/seed_browse_categories.py` (Story 49.2) is not touched or re-run.
2. **No frontend/admin screen.** That is Story 52.2. This story ships API + tests + docs only. `apps/web/**` stays byte-unchanged.
3. **No category-assignment automation and no inference from tags.** Every write in this story is an explicit admin-initiated HTTP call. Nothing here reads `Tag`/`TagGroup`/`ModelTag` to auto-populate `model_browse_category`.
4. **`current_admin` only, on every new route.** No route in this story accepts an `agent` principal — a deliberate tightening relative to the tags precedent this story's replace-set endpoint is modelled on (§6 F-9); there is no `agent-write` tag anywhere in this story's surface.
5. **`Model` and existing `BrowseCategory*`/`ModelDetail`/read-router surfaces stay byte-unchanged.** `GET /api/categories[/{slug}]`, `GET /api/models?category=`, and `ModelDetail.categories` (all Story 49.3) are not touched. `apps/api/tests/test_sot_categories.py` and `test_sot_models_category_scope.py` pass byte-unmodified as non-regression witnesses.
6. **New schema identifiers are `BrowseCategory*`, never bare `Category*`.** `test_no_category_schemas_in_components` (`test_openapi_agent_surface.py:334-341`) hard-fails on any component schema `startswith("Category")`. No property named `category`/`category_id` may be added to `ModelSummary`/`ModelDetail`/`ModelCreate`/`ModelPatch`/`ShareModelView` (`test_no_category_properties_on_model_schemas`, `:344-354`).
7. **Depth-2 ceiling and self-cycle rejection are service-layer rules, not DDL.** `BrowseCategory.parent_id` stays a plain nullable self-FK with `ondelete="RESTRICT"` — no CHECK constraint, no trigger. All enforcement is in `admin_service.py` (§4 AC-12…AC-16, §6 F-4).
8. **Delete = `409 Conflict` while assignments exist, unless explicit `detach=true`** (payload of `?detach=true` query param). Detach + delete is **one transaction**; the audit row carries both the detached model ids and a count (epic:42 unbounded-audit-payload precedent applied by analogy, §6 F-6). A category with **children** is a **second, independent** conflict source (`parent_id` is also `RESTRICT`) that `detach=true` does **not** resolve — §6 F-4 records why this is a story-level decision the planning artifacts left open.
9. **`PUT /api/admin/models/{id}/categories` is whole-set replace, idempotent, explicit last-writer-wins.** No merge, no diff, no optimistic-concurrency precondition (no `revision` column, no `If-Match`) is built in this story — that is a named future trigger (§8.6), not a defect. The endpoint audits the resulting set; it must never claim conflict detection it does not have.
10. **`entity_type="browse_category"`** is added to `KNOWN_ENTITY_TYPES` (`app/core/audit.py:51-69`) with `browse_category.create` / `browse_category.update` / `browse_category.delete` actions; the model-scoped replace-set reuses the existing `entity_type="model"` / `action="model.update"` convention `replace_model_tags` already established (§6 F-9) — no new M:N-specific `entity_type` is introduced.
11. **CSRF and route-enforcement gates apply unmodified.** Every mutating route sits behind the existing prefix-based `csrf_guard` (`app/core/auth/csrf.py`) and resolves to `current_admin` in `test_route_enforcement_gate.py`'s auth-dependency scan — no edit to `_PUBLIC_ROUTES`, no new auth-dependency name introduced (§6 F-7, F-8).
12. **Strict RED → GREEN.** Every behavioural assertion in §4 is proven by a test observed failing before the production code satisfying it exists, with the failure output quoted verbatim by the dev pass in §15. A test that passes by construction must be labelled a structural/composition guard, never dressed up as a RED (§5 ordering rule).

## 4. Acceptance Criteria

### `POST /api/admin/categories` — create

**AC-1 — Success shape.** A valid `{slug, name_en}` (minimum) payload returns **201** + `BrowseCategoryAdminRead` — the 9-key `BrowseCategoryRead` set (`{id, slug, name_en, name_pl, description_en, description_pl, position, parent_id, model_count}`) **plus `inclusion_criterion`** (§6 F-3 — the public read contract deliberately omits it; the admin contract is where it is first exposed over HTTP). `model_count` is always `0` on create (no assignment can exist yet for a brand-new id).

**AC-2 — Defaults.** Omitting `name_pl`, `description_en`, `description_pl`, `inclusion_criterion`, `parent_id` leaves them `null`. Omitting `position` defaults to `0` (mirrors `TagGroupCreate.position: int = 0`).

**AC-3 — Slug uniqueness.** A `slug` colliding with an existing `browse_category.slug` (the `uq_browse_category_slug` unique index, `_entities.py:141`) returns **409**, not 422 and not 500.

**AC-4 — Auth matrix.** Anonymous → **401**. `member`/`agent` role → **403** (`admin_required`). `admin` → **201**. No route in this story ever accepts `agent`.

**AC-5 — CSRF.** A `POST` without `X-Portal-Client: web` returns **403 `csrf_required`** — proven by the existing, unmodified `test_csrf_middleware.py` staying green (prefix-based middleware, no per-route code); not a new test this story authors (§6 F-8).

**AC-6 — `parent_id` on create: unknown parent → 404.** A `parent_id` that does not resolve to any existing `browse_category.id` returns **404** (mirrors the "unknown model/tag id → 404" convention `PUT /models/{id}/tags` already establishes for referenced-resource validation, §6 F-9), not 422 and not a raw `IntegrityError`.

**AC-7 — `parent_id` depth ceiling on create.** A `parent_id` that itself has a non-null `parent_id` (i.e. is already a child) returns **422** `parent_not_root`. A brand-new category can only ever be created as a root (`parent_id: null`) or as a direct child of an existing **root** category — never as a grandchild.

### `PATCH /api/admin/categories/{category_id}` — rename / reorder / reparent

**AC-8 — Partial update, `exclude_unset`.** Only fields present in the request body change. `model_config = ConfigDict(extra="forbid")` — an unknown key returns 422. Returns **200** + `BrowseCategoryAdminRead`.

**AC-9 — Omitted vs. explicit null on NOT NULL fields.** `slug`, `name_en`, `position` are `NOT NULL` on the entity. Omitting any of them from the PATCH body leaves the current value untouched (Pydantic v2 skips `@field_validator` on an unset field). An **explicit** `{"slug": null}` / `{"name_en": null}` / `{"position": null}` in the body returns **422** — the same `_reject_explicit_null` pattern `TagGroupPatch` already uses (`admin_schemas.py:270-280`), applied to a new `BrowseCategoryPatch`. `name_pl`, `description_en`, `description_pl`, `inclusion_criterion`: an explicit `null` **clears** the field (200), matching `TagGroupPatch.name_pl`'s posture.

**AC-10 — Empty PATCH is a no-op that still audits.** `PATCH {}` on an existing category returns **200** unchanged, and still writes **exactly one** `browse_category.update` audit row with `before == after` — the unconditional-audit convention `update_tag_group` already establishes (`admin_service.py:1204-1205,1232-1240`). This is deliberate, not a bug: an admin action that changes nothing is still a recorded event.

**AC-11 — Slug uniqueness on rename.** Patching `slug` to a value already used by a **different** category returns **409**. Patching a category's `slug` to its **own current** `slug` (a no-op rename) succeeds with 200 (not a false-positive 409 against itself).

**AC-12 — Unknown category → 404.** `PATCH /api/admin/categories/{unknown-uuid}` returns **404**, not a silent no-op and not 422.

**AC-13 — `parent_id` self-cycle rejection.** `PATCH {"parent_id": "<own id>"}` returns **422** `self_cycle` and mutates nothing.

**AC-14 — `parent_id` depth ceiling on reparent (target side).** Setting `parent_id` to a category that is itself already a child (has a non-null `parent_id`) returns **422** `parent_not_root` — identical rule to AC-7, applied on update.

**AC-15 — `parent_id` depth ceiling on reparent (source side) — the case AC-7/AC-14 alone do not cover.** Setting `parent_id` (to any non-null root category) on a category that **currently has children** returns **422** `reparent_exceeds_depth` — because it would push those children to depth 3. Verified independently of AC-14: a category with zero children can always be reparented onto any valid root; a category with ≥1 child can never be reparented onto anything (only its `parent_id` can move **toward** `null`, never **away from** `null`, while it has children).

**AC-16 — Clearing `parent_id` (making a child a root again) always succeeds.** `PATCH {"parent_id": null}` on a child category returns 200 regardless of the category's own children (setting a category's parent to `null` can never increase any depth).

### `DELETE /api/admin/categories/{category_id}` — delete, with optional detach

**AC-17 — Clean delete.** A category with **no** model assignments and **no** children: `DELETE` (no query param, or `?detach=false`) returns **204**. One `browse_category.delete` audit row is written, `before` = the full bounded snapshot (§6 F-6), no `after`.

**AC-18 — 409 while model-assignments exist, `detach` omitted or `false`.** A category with ≥1 `model_browse_category` row and **no** children: `DELETE` returns **409** `category_in_use`. **Nothing is deleted, nothing is audited** — the request has no side effect (proven by an unchanged row count and an unchanged audit-row count for that `entity_id`, §5 T5).

**AC-19 — `detach=true` performs detach + delete atomically.** Same precondition as AC-18, with `?detach=true`: returns **204**. In **one transaction**: every `model_browse_category` row for that category is deleted, then the category row itself is deleted, then the category commits. One `browse_category.delete` audit row carries `before` = the full snapshot **plus** `detached_model_ids: [uuid, ...]` (every detached model id, as strings) **and** `detached_model_count: int` — both fields together, per §3.8 and the epic:42 precedent (§6 F-6). A subsequent `GET /api/models?category=<deleted-slug>` (via a fresh, still-existing category with the same slug — the slug itself does not survive) is not asserted here; the assignment rows themselves are proven gone by a direct row-count query in §5 T5.

**AC-20 — `detach=true` on a category with NO assignments is a harmless no-op flag.** `DELETE ...?detach=true` on a clean category (AC-17's precondition) still returns 204, still writes exactly one audit row, and the row carries **no** `detached_model_ids`/`detached_model_count` keys (they are only present when at least one row was actually detached) — `detach=true` never fabricates a non-empty detach record.

**AC-21 — Children are a second, independent 409 source that `detach=true` does NOT resolve.** A category with ≥1 child category (regardless of model assignments, regardless of `detach`): `DELETE` — with or without `?detach=true` — returns **409** `category_has_children`. Deleting a category's children (or reparenting them to `null`/elsewhere) first is a **separate prior request**; this story does not add a cascading-child-delete or auto-reparent-on-delete behaviour. This is a story-created-pass decision, not inherited from any planning artifact — see §6 F-4 for the full reasoning and why it is the correct minimal-diff resolution of the RESTRICT-on-`parent_id` hazard the planning artifacts did not address.

**AC-22 — Both conflict sources present.** A category with both ≥1 child **and** ≥1 model assignment: `DELETE ...?detach=true` still returns **409** `category_has_children` (children are checked first, unconditionally) and performs **zero** detach side effects — the model-assignment rows are untouched, proven by an unchanged row count.

**AC-23 — Unknown category → 404.** `DELETE /api/admin/categories/{unknown-uuid}` returns **404** regardless of the `detach` query param.

**AC-24 — Auth + CSRF matrix.** Same posture as AC-4/AC-5, applied to DELETE: anonymous 401, member/agent 403, admin 204/409/404 per the above; missing CSRF header → 403 `csrf_required` (existing middleware, no new test required).

### `PUT /api/admin/models/{model_id}/categories` — replace-set assignment

**AC-25 — Success, whole-set replace.** A valid `{"category_ids": [...]}` (any length, including empty `[]`) against an existing, non-soft-deleted model returns **200** + `list[BrowseCategorySummary]` (the embeddable 5-key shape `ModelDetail.categories` already uses, §6 F-3) — the resulting set, ordered `(position, slug)` matching the existing `list_browse_categories`/`ModelDetail.categories` ordering convention.

**AC-26 — Idempotent.** Calling the same `{"category_ids": [A, B]}` twice in a row against the same model produces the identical result both times (200, same resulting set) and writes **two independent** `model.update` audit rows (once per call) — idempotent means "same end state," not "audited once." Verified by asserting the row set is unchanged between calls, not by asserting only one audit row exists.

**AC-27 — Empty set clears all assignments.** `{"category_ids": []}` on a model with existing assignments returns 200 + `[]`, and every prior `model_browse_category` row for that model is gone. A model with **zero** categories remains fully valid and public (FR26-CAT-2 — no downstream visibility change; this story does not touch any read/visibility path).

**AC-28 — Duplicate ids in the payload → 400.** `{"category_ids": [A, A]}` (the same id twice) returns **400**, not a 500 from an `IntegrityError` on the composite PK `(model_id, category_id)`, and not a silent de-duplication. This is a **deliberate improvement** over the `PUT /models/{id}/tags` precedent, which the research for this story found has no such guard and would hit an uncaught `IntegrityError` on a literal-duplicate payload (§6 F-9) — Story 49.5 closes that gap for categories rather than copying it forward, and does **not** retroactively fix the tags endpoint (out of scope, not silently touched).

**AC-29 — Unknown category id in the payload → 404.** Any `category_ids` entry that does not resolve to an existing `browse_category.id` returns **404**, and the request has **no** side effect (no partial replace) — validation happens before any `ModelBrowseCategory` row is deleted or inserted.

**AC-30 — Unknown or soft-deleted model → 404.** `PUT /api/admin/models/{unknown-or-deleted-uuid}/categories` returns **404**, mirroring `_get_model_active`'s existing "absent or soft-deleted" LookupError semantics that `replace_model_tags` already relies on (§6 F-9) — no new soft-delete logic is introduced.

**AC-31 — Detach transaction rollback on mid-replace failure.** If validation (duplicate check or existence check) fails, **zero** `ModelBrowseCategory` rows are deleted — the existing set for that model is provably unchanged (row-count + row-identity comparison before/after the failed call). This proves the "validate everything, then mutate" ordering, not a partial replace.

**AC-32 — Audit fidelity.** Exactly one `model.update` audit row per successful `PUT` call, `entity_type="model"`, `entity_id=<model_id>`, `before={"category_ids": [...]}` (the pre-call set, as strings), `after={"category_ids": [...]}` (the post-call set, as strings) — the identical shape `replace_model_tags` already uses for `tag_ids` (§6 F-9), applied to categories. No merge/conflict-detection claim appears anywhere in the response, the audit row, or the route `description` (§3.9).

**AC-33 — Auth + CSRF matrix.** Anonymous 401, member/agent 403 (this is the deliberate tightening vs. the tags precedent — §6 F-9 records this as an open rationale gap the Validate pass should double-check, not a silent given), admin 200; missing CSRF header → 403 (existing middleware).

### Audit contract (cross-cutting)

**AC-34 — `entity_type="browse_category"` registered.** `app/core/audit.py::KNOWN_ENTITY_TYPES` gains `"browse_category"` with a doc-comment entry in the same style as the existing 15 entries (`:16-49`), naming the three actions and noting the delete-with-detach payload shape. `record_event`'s `ValueError` guard is unaffected for existing entity types (proven by every pre-existing audit-touching test staying green, §7 asserted-unchanged list).

**AC-35 — Bounded, truthful snapshot — no PII, no unbounded growth beyond the one documented exception.** `_browse_category_snapshot` carries exactly `{slug, name_en, name_pl, description_en, description_pl, inclusion_criterion, position, parent_id}` (UUIDs/strings/ints/null only — D-AUDIT-2 posture, §6 F-6). The **one** intentionally-unbounded field, `detached_model_ids` on delete, is the epic:42-precedented exception — always paired with `detached_model_count` so a reader never has to count array elements to know the scale, and is re-evaluated (not capped) if model-assignment cardinality per category grows large in practice, exactly mirroring the still-open epic:42 action item (§6 F-6). This story does **not** invent a truncation/cap mechanism — that would be scope creep beyond what the ratified precedent asks for.

### Non-regression

**AC-36 — Neighbouring read paths are untouched.** `GET /api/categories`, `GET /api/categories/{slug}`, `GET /api/models?category=<slug>`, `GET /api/tag-groups`, `GET /api/tags`, and the existing `POST/PATCH/DELETE /api/admin/tag-groups` + `POST /api/admin/tags` governance routes all pass their existing test suites **byte-unmodified**. `test_route_enforcement_gate.py`'s three tests pass unmodified with the four new routes registered (§6 F-7 — `current_admin` resolves to the already-recognized `_current_admin_dep`, no allowlist edit needed).

**AC-37 — OpenAPI honesty for the new, off-target-tag-set routes.** All four new routes carry `tags=["sot-admin-governance"]` (never `agent-write`), and each carries a non-empty `summary` and `description` — proven by two new tests mirroring `test_governance_routes_absent_from_agent_write_set` / `test_governance_routes_have_summary_and_description` (`test_openapi_agent_surface.py:257-297`), since `sot-admin-governance` sits outside `TARGET_ROUTER_TAGS` and is not auto-covered by the generic `test_every_admin_sot_operation_has_summary/description` (§6 F-5).

## 5. Tasks / Subtasks — strict RED → GREEN

> **Ordering rule.** Within each slice the test is authored and observed failing **before** the production symbol it exercises exists. Failure output is quoted verbatim into §15. A test that passes by construction (e.g. AC-20's "no detach keys on a clean delete" once T3 already exists) is either restructured to have a genuine RED, or explicitly labelled a structural/composition guard in both the test docstring and §15 — never dressed up as a RED.

- [ ] **T0 — Baseline capture (no edits).**
  - [ ] T0.1 Confirm clean tree at `0df663e`; run the regression set that must stay green and record pass counts verbatim: `.venv/bin/pytest -q tests/test_sot_categories.py tests/test_sot_models_category_scope.py tests/test_sot_admin_tag_groups.py tests/test_sot_admin_tags.py tests/test_route_enforcement_gate.py tests/test_openapi_agent_surface.py tests/test_csrf_middleware.py`.
  - [ ] T0.2 Confirm (grep, not assumption) that `create_category`/`update_category`/`delete_category` genuinely do not exist in `admin_service.py` — the 42.4 story's own Dev Notes cite a now-stale template at those old line numbers (§6 F-1); do not follow that citation.

- [ ] **T1 — Schemas: `BrowseCategoryCreate` / `BrowseCategoryPatch` / `BrowseCategoryAdminRead` / `ModelCategoriesReplace` (no route yet).**
  - [ ] T1.1 **RED** — a schema-level unit test (or the first router test, whichever lands first — see T2.1) proving `BrowseCategoryPatch(extra="forbid")` rejects an unknown key and `BrowseCategoryPatch(slug=None)` raises at construction; both fail with `ImportError`/`AttributeError` before the class exists. Quote the failure.
  - [ ] T1.2 Add `BrowseCategoryCreate`, `BrowseCategoryPatch` to `admin_schemas.py` (request DTOs, alongside `TagGroupCreate`/`TagGroupPatch`), and `ModelCategoriesReplace` (mirroring `TagsReplace`, `admin_schemas.py:129-143`).
  - [ ] T1.3 Add `BrowseCategoryAdminRead(BrowseCategoryRead)` to `sot/schemas.py` (response DTO, alongside `BrowseCategorySummary`/`BrowseCategoryRead`), adding exactly `inclusion_criterion: str | None`.
  - [ ] T1.4 **GREEN** — quote.

- [ ] **T2 — `POST /api/admin/categories` (AC-1 … AC-7).**
  - [ ] T2.1 **RED** — author `tests/test_sot_admin_categories.py`, new file. Success shape + defaults; slug conflict 409; auth matrix (401/403/403/201); unknown `parent_id` 404; non-root `parent_id` 422 `parent_not_root`. Observe route-absent 404s and quote.
  - [ ] T2.2 Add `_browse_category_snapshot`, `create_browse_category` to `admin_service.py` (new section, mirroring `create_tag_group`'s `try: session.flush() except IntegrityError: rollback; raise ValueError("slug_conflict")` shape, plus the new parent-id existence + root-check validation ahead of the insert).
  - [ ] T2.3 Add `KNOWN_ENTITY_TYPES` entry `"browse_category"` in `app/core/audit.py` (AC-34), with the doc-comment block.
  - [ ] T2.4 Create `apps/api/app/modules/sot/browse_category_admin_router.py` (new file, mirrors `tag_group_admin_router.py`'s docstring/router-declaration shape verbatim: `router = APIRouter(prefix="/api/admin", tags=["sot-admin-governance"])`), with `POST /categories`.
  - [ ] T2.5 Register the new router in `app/router.py`, immediately after `sot_tag_group_admin_router` (same registration block, same relative order as the existing governance router).
  - [ ] T2.6 **GREEN** — quote.

- [ ] **T3 — `PATCH /api/admin/categories/{category_id}` (AC-8 … AC-16).**
  - [ ] T3.1 **RED** — extend `test_sot_admin_categories.py`: partial update; omitted-vs-explicit-null on `slug`/`name_en`/`position`; explicit-null clears `name_pl`; empty-patch no-op + audit; slug conflict (incl. no-op self-rename 200); unknown category 404; self-cycle 422; `parent_not_root` on reparent-target 422; `reparent_exceeds_depth` on reparent-source-with-children 422; clearing `parent_id` on a childful category succeeds. Quote each failure as it's added, or the first composite failure if authored as one RED batch — label accordingly in §15.
  - [ ] T3.2 Add `update_browse_category` to `admin_service.py`: `patch.model_dump(exclude_unset=True)`; before/after snapshots; the reparent validation block (self-cycle check first, then "is the *target* parent itself non-root", then "does *this* category currently have children and is parent_id being set non-null") — all three checks independent and all three must be exercised (§4 AC-13/14/15 are three distinct tests, not one).
  - [ ] T3.3 Add `PATCH /categories/{category_id}` to `browse_category_admin_router.py`, mapping `LookupError` → 404, `ValueError("slug_conflict")` → 409, `ValueError("self_cycle")`/`ValueError("parent_not_root")`/`ValueError("reparent_exceeds_depth")` → 422.
  - [ ] T3.4 **GREEN** — quote.

- [ ] **T4 — `DELETE /api/admin/categories/{category_id}` (AC-17 … AC-24).**
  - [ ] T4.1 **RED** — extend `test_sot_admin_categories.py`: clean delete 204 + one audit row; 409 `category_in_use` with no side effect (assert row survives + assert no new audit row, mirroring the pattern §4 AC-18 requires); `detach=true` 204 + detach-and-delete-in-one-tx + audit row with both `detached_model_ids` and `detached_model_count`; `detach=true` on a clean category → 204 + audit row **without** those two keys (AC-20 — author this as an explicit assertion, not an assumption); `category_has_children` 409 with and without `detach=true` (AC-21); both-conflicts-present still 409 `category_has_children` with zero detach side effects (AC-22); unknown category 404. Quote failures.
  - [ ] T4.2 Add `delete_browse_category(session, *, category_id, detach, actor_user_id)` to `admin_service.py`: look up category (404 if missing) → **query children first** (`select(BrowseCategory.id).where(BrowseCategory.parent_id == category_id)`) → if any, `raise ValueError("category_has_children")` **unconditionally, before even looking at `detach`** → else query `ModelBrowseCategory` rows for the category → if any and not `detach`, `raise ValueError("category_in_use")` → else (clean, or has-assignments-with-detach): if detaching, delete the `ModelBrowseCategory` rows and capture their `model_id`s for the audit payload; delete the category row; **one** `_audit_entity(action="browse_category.delete", entity_type="browse_category", ...)` call carrying the base snapshot plus (only if any were detached) `detached_model_ids`/`detached_model_count`; single `session.commit()`.
  - [ ] T4.3 Add `DELETE /categories/{category_id}` to the router, `detach: bool = False` query param, mapping `LookupError` → 404, `ValueError("category_has_children")`/`ValueError("category_in_use")` → 409.
  - [ ] T4.4 **GREEN** — quote.

- [ ] **T5 — `PUT /api/admin/models/{model_id}/categories` (AC-25 … AC-33).**
  - [ ] T5.1 **RED** — author `tests/test_sot_admin_model_categories.py`, new file, mirroring `test_sot_admin_tags.py`'s replace-tags test shapes: success + defaults ordering; idempotent double-call; empty-set clear; duplicate-id 400 with no side effect; unknown-category-id 404 with no side effect; unknown/soft-deleted model 404; rollback-proof (unchanged row set) on a failed validation call; audit row shape (`before`/`after` keysets); auth matrix incl. agent → 403 (the deliberate tightening, AC-33). Quote failures.
  - [ ] T5.2 Add `replace_model_categories` to `admin_service.py`, mirroring `replace_model_tags` (`admin_service.py:807-859`) exactly in structure but adding the **duplicate-id pre-check** `replace_model_tags` itself lacks (AC-28 — validate `len(payload.category_ids) == len(set(payload.category_ids))` before touching the session, `raise ValueError("duplicate_category_ids")` if not) and validating every id against `BrowseCategory` (not `Tag`) before any delete/insert.
  - [ ] T5.3 Add `PUT /api/admin/models/{model_id}/categories` to `browse_category_admin_router.py` (not `sot/admin_router.py` — this is an admin-only, non-`agent-write` route; keeping it beside the category CRUD keeps the whole category-write surface in one cohesive, easily-audited module). Map `LookupError` → 404, `ValueError("duplicate_category_ids")` → 400, `ValueError(f"category not found: {cid}")` → 404.
  - [ ] T5.4 **GREEN** — quote.

- [ ] **T6 — OpenAPI honesty + route-enforcement non-regression (AC-36, AC-37).**
  - [ ] T6.1 Extend `test_openapi_agent_surface.py`'s `_GOVERNANCE_ROUTES` set with the four new `(METHOD, path)` tuples, extending — not duplicating — `test_governance_routes_absent_from_agent_write_set` and `test_governance_routes_have_summary_and_description` coverage (§6 F-5). **RED** first (the new tuples fail against the pre-T2…T5 OpenAPI doc, since the routes don't exist yet) — fold this into T2.1/T3.1/T4.1/T5.1's RED batches rather than a separate isolated RED, and say so plainly in §15.
  - [ ] T6.2 Run `tests/test_route_enforcement_gate.py` and `tests/test_no_category_schemas_in_components`/`test_no_category_properties_on_model_schemas` (`test_openapi_agent_surface.py`) **unmodified** — quote passes.
  - [ ] T6.3 Run `tests/test_csrf_middleware.py` **unmodified** — quote pass (proves AC-5/AC-24/AC-33's CSRF posture without any story-specific edit).

- [ ] **T7 — Scope + quality (§7).**
  - [ ] T7.1 `.venv/bin/ruff format --check .` and `.venv/bin/ruff check .` in `apps/api`.
  - [ ] T7.2 Full API suite: `.venv/bin/pytest -q` in `apps/api`.
  - [ ] T7.3 `git diff --name-only` + `git status --porcelain` proving the §7 file set exactly, and `git diff --name-only` returning empty for every AC-36 byte-unchanged path.

- [ ] **T8 — Controller-owned closeout (leave UNCHECKED by the implementer).**
  - [ ] T8.1 Frozen final `infra/scripts/check-all.sh` 16/16 on the final commit.
  - [ ] T8.2 Determinism triple (NFR26-DETERMINISM-1).
  - [ ] T8.3 Native `bmad-code-review`, then independent `laura-aider-review-diff` per the Laura Agent Rulebook (Aider routine default; Codex fallback/high-stakes only; Gemini not a default reviewer).
  - [ ] T8.4 One commit, ff-only merge, push, deploy.

## 6. Verify-at-create findings (traced against real code at HEAD `0df663e` this session)

**F-1 — The 42.4 story's own Dev Notes cite a stale template; do not follow it literally.** Story 42.4's artifact (`_bmad-output/implementation-artifacts/42-4-admin-group-governance.md`, `done`) references `admin_service.py:1150-1306 — Category CRUD is the exact template` and named functions `create_category`/`update_category` at specific line numbers. **These functions and the entire `class Category` feature they governed were retired by Epic 47** (`0019_drop_category`) and do **not exist anywhere** in this worktree — confirmed by an exhaustive grep for `def create_category\|def update_category\|def delete_category\|class Category\b` across `apps/api/app/` returning zero matches. The line range `1150-1306` in the current file is occupied by `TagGroup` CRUD (`create_tag_group`/`update_tag_group`/`delete_tag_group`, verified verbatim at `admin_service.py:1150-1284` this session), which **is** the correct template — exactly what `sprint-status.yaml:383`'s own directive already says ("extend `tag_group_admin_router.py` + the 42.4 audit posture"). This story's tasks (§5 T2-T5) cite `create_tag_group`/`update_tag_group`/`delete_tag_group`/`delete_tag`/`replace_model_tags` throughout, never the retired citation.

**F-2 — Current `BrowseCategory`/`ModelBrowseCategory` entities, verified line-for-line at `_entities.py:130-183`.** Both FKs on `ModelBrowseCategory` are `ondelete="RESTRICT"` (`model_id` → `model.id` and `category_id` → `browse_category.id`), and `BrowseCategory.parent_id` is **also** `ondelete="RESTRICT"` (self-FK). `BrowseCategory` has **no** `deleted_at`/soft-delete column (confirmed by the `list_browse_categories` docstring in `sot/service.py`: "No lifecycle filtering — BrowseCategory has no soft-delete column"). `position: int = Field(default=0)` at the ORM layer, `server_default="0"` at the migration layer (`migrations/versions/0020_browse_categories.py:60-113`).

**F-3 — Neither existing read schema exposes `inclusion_criterion`.** `BrowseCategorySummary` (`sot/schemas.py:87-101`, 5 keys: `id, slug, name_en, name_pl, position, parent_id`) and `BrowseCategoryRead` (`:104-120`, +`description_en, description_pl, model_count`) both deliberately omit it — Story 49.3's own §6 F-12 recorded this as following Decision AY's exact public-read keyset and explicitly deferred a wider DTO to "a later admin/curation DTO for E49.5/52.3." **This story is that later DTO.** `BrowseCategoryAdminRead(BrowseCategoryRead)` (T1.3) is additive — it does not touch `BrowseCategorySummary`/`BrowseCategoryRead`, and `GET /api/categories[/{slug}]` (Story 49.3, unmodified) continues to omit `inclusion_criterion` from its response, which is the correct, deliberate asymmetry: the public read contract and the admin write-response contract are allowed to differ, and Decision AY's keyset governs only the former.

**F-4 — The double-RESTRICT hazard on category delete is real and unaddressed by any planning artifact — this story resolves it.** `sprint-status.yaml:383` and `architecture.md:3337` both say "409 Conflict while assignments exist, unless explicit `detach=true`" — language that reads as though `model_browse_category` rows are the *only* RESTRICT source. They are not: `BrowseCategory.parent_id`'s own `ondelete="RESTRICT"` (F-2) means a category with children raises `IntegrityError` on delete for a completely independent reason, and `detach=true`'s documented scope ("detach + delete in one transaction," carrying **model** ids) has no natural extension to "also reparent or delete children" — doing so would silently redefine what `detach=true` means and would require its own depth/self-cycle re-validation on every affected child. **Resolution adopted by this Create pass (AC-21/AC-22, §5 T4.2):** children are checked **first and unconditionally** — a category with any child is a flat 409 `category_has_children` regardless of `detach`. Deleting or reparenting children is a separate, prior admin action using the existing PATCH/DELETE routes this story already ships (`PATCH {"parent_id": null}` on the child, or `DELETE` the child first). This is the minimal-diff resolution: it adds no new query parameter, no new transaction shape, and no cascading-delete semantics that nothing in Decision AX/AY asked for — Decision AX explicitly says depth-2 is "flat MVP" with "MVP writes no child categories at all" in the seed/product sense, so in practice this path is rare, but the API must not crash with a raw 500 `IntegrityError` when it is hit. **Flagged for the Validate pass**, not silently applied: an alternative design (making `detach=true` also orphan children to `parent_id=null`) is plausible and was considered but rejected here as a larger, unrequested behavioural surface.

**F-5 — `sot-admin-governance` sits outside `TARGET_ROUTER_TAGS`.** `test_openapi_agent_surface.py:61` — `TARGET_ROUTER_TAGS = {"admin", "sot-admin", "sot-read"}` — confirmed does **not** include `sot-admin-governance`. The generic `test_every_admin_sot_operation_has_summary`/`test_every_admin_sot_operation_has_description` (`:165-182`) therefore do not automatically cover this story's four new routes; the existing precedent for closing that gap is `test_governance_routes_have_summary_and_description` (`:290-297`), which iterates an explicit `_GOVERNANCE_ROUTES` set literal (`:257-262`) — §5 T6.1 extends that literal rather than writing a parallel, redundant test.

**F-6 — The epic:42 unbounded-audit-payload precedent, quoted exactly.** `_bmad-output/implementation-artifacts/deferred-work.md` / `sprint-status.yaml:439-442` records: *"Re-evaluate the unbounded `detached_tag_ids` delete-audit payload only if tag-group membership can grow large (42.4 native-review Minor #1; bounded in practice by the small admin-rare tag table, `detached_tag_count` carried alongside)."* `sprint-status.yaml:383`, `architecture.md:3337`, and the SCP all invoke this **by analogy** for 49.5. The shipped precedent shape (`delete_tag_group`, `admin_service.py:1267-1279`) is `{"slug":..., "name_en":..., "detached_tag_ids": [str,...], "detached_tag_count": int}`. This story's `browse_category.delete` audit (AC-19) mirrors it exactly with `detached_model_ids`/`detached_model_count`, and inherits the same accepted, open, non-blocking posture — **not** a mandate to build truncation. `_browse_category_snapshot`'s base fields (AC-35) follow `_tag_group_snapshot`'s "full bounded snapshot, UUIDs/strings/ints only, no PII" discipline (D-AUDIT-2, `admin_service.py:1140-1147`).

**F-7 — Route-enforcement gate needs no edit.** `test_route_enforcement_gate.py`'s `_AUTH_DEP_NAMES = {"_current_user_dep", "_current_admin_dep", "_current_member_or_admin_dep", "_current_admin_or_agent_dep"}` already recognizes `current_admin`'s underlying callable (`_current_admin_dep`, `app/core/auth/dependencies.py:76`), and this story introduces no new auth-dependency function — all four new routes reuse `current_admin` verbatim. `_PUBLIC_ROUTES` (`main.py:50-61`) needs no edit; none of these routes is anonymous.

**F-8 — CSRF middleware is prefix-based and needs no per-route test.** `app/core/auth/csrf.py`'s `csrf_guard` gates every `UNSAFE_METHODS` request under `/api/` except `/api/share/*`, keyed only on path prefix and `X-Portal-Client` header presence — it has no per-route allowlist to extend. `tests/test_csrf_middleware.py` (whole-file, path-prefix-driven) already proves this generically; §5 T6.3 runs it unmodified rather than authoring four redundant per-route CSRF tests.

**F-9 — `PUT /models/{model_id}/tags` is the direct structural precedent for the replace-set endpoint, verified line-for-line at `admin_service.py:807-859` / router at `admin_router.py:571-598`.** Its docstring's contract ("Returns 200 + the resulting tag list... 404 if model or any tag id is missing. 400 on validation failure (e.g. duplicate ids in the payload)") is the source for this story's AC-28/AC-29/AC-30 status-code choices. **Two deliberate departures:** (a) the tags endpoint is `_current_principal` (admin OR agent) and tagged `agent-write`; this story's `PUT /categories` is `current_admin`-only with no `agent-write` tag. (b) the tags endpoint has **no duplicate-id guard** in the actual shipped code (only in its own docstring's stated contract) — a literal-duplicate `tag_ids` payload today hits an uncaught `IntegrityError` on the second `session.add(ModelTag(...))` at `session.flush()`. AC-28 closes this gap for categories; this story does **not** retroactively patch `replace_model_tags` (out of scope, would be silent unrequested scope creep into a different, closed story's surface).

**F-9 addendum — RESOLVED by the Validate pass (2026-07-28), correcting departure (a)'s framing.** The Create pass characterized the `current_admin`-only tier as "a real auth-tier tightening with no ratified rationale beyond the task's own explicit instruction" — re-derived against source, that understates the evidence and is corrected here: **Decision AY** (`architecture.md:3334-3341`) places **all four** new routes — including `PUT /api/admin/models/{id}/categories` — under one explicit heading, *"Admin governance (`current_admin`, audit row on every write; structural precedent `tag_group_admin_router.py` + the 42.4 audit posture)"*. This is a ratified planning-artifact requirement, not a session-invented or merely task-instructed choice. It is also not a novel pattern in this codebase: `tag_group_admin_router.py`'s own docstring (verified verbatim at HEAD) states the identical doctrine for facet governance — *"Facet governance is admin curation, not agent ingestion (FR25-ADMIN-1 / Decision AW)... never advertises an agent capability"* — and `D-ADMINONLY-1` already relocated `POST /tags` from the agent-write router to this admin-only one on that exact basis. Categories vs. tags is the same admin-curation/agent-ingestion split applied to a new taxonomy family, not an unprecedented asymmetry. The genuinely open item is narrower than Q-1 as originally framed: `architecture.md` states the `current_admin` requirement but does not itself spell out *why* the split falls the way it does for the replace-set operation specifically (as opposed to the create/rename/delete routes, which are admin-curation by any reading) — that is a documentation-completeness observation for a future architecture-hygiene pass, not an unratified or ungrounded design decision. §8.1's router docstring and §18 Q-1 are amended below to state this truthfully.

**F-10 — Test-authoring precedent, `test_sot_admin_tag_groups.py` (507 lines, whole file read).** `_admin_cookie(client)` (`:52-57`) seeds a real `User(role=admin)` row via a direct `Session(get_engine())` write (required because `AuditLog.actor_user_id` FKs `user.id` with `ondelete=SET NULL`, so a bare JWT-minted UUID with no backing row would still pass auth but produce an audit row whose FK reference is technically valid-but-orphaned rather than exercising the real actor-linkage path). The auth-matrix pattern (`:407-451`) sequentially swaps `client.cookies` between no-cookie / member-token / agent-token / `_admin_cookie(client)` and asserts 401/403/403/2xx — replicated verbatim for this story's four routes. Audit assertions query `audit_log` directly via a small `_tag_group_audits(action, entity_id)` helper (`:80-89`) using `select(AuditLog).where(AuditLog.action == ..., AuditLog.entity_id == ...)`, then `json.loads(log.before_json/after_json)` and exact-keyset assertions (`set(before.keys()) == {...}`) — this story's `_category_audits`/`_model_audits` helpers follow the identical shape. `test_delete_tag_409_in_use` (`test_sot_admin_tags.py:477-491`) is the closest existing 409-in-use test body shape (seed admin + model + tag + a `ModelTag` row, then assert `client.delete(...).status_code == 409`) — this story's AC-18/AC-19/AC-21/AC-22 tests extend that exact shape with a seeded `ModelBrowseCategory` row and/or a seeded child `BrowseCategory` row.

**F-11 — No admin-facing docs section is falsified by this story (unlike Story 49.3's forced doc-honesty correction).** `docs/operations.md:471-474`'s "Admin write" enumeration ("`/api/admin/*` for models, files, tags, notes, prints, external_links") is **incomplete** relative to the already-shipped `tag-groups` governance router and will remain incomplete after this story ships `categories` too — but it states nothing **false**; it is a documentation gap, not a documentation lie, unlike the `/api/categories` retirement text Story 49.3 was forced to correct because deploying would make it false. Per §3/§10 minimal-diff discipline, this story does **not** edit `docs/operations.md` — closing that enumeration gap (for `tag-groups` too, not just `categories`, since it's already stale) is left as a reported, not silently absorbed, observation for a future doc-hygiene pass.

## 7. Predicted file changes (exact)

**Total: 9 product/doc files** = **6** production + **3** test (2 NEW + 1 additive extension of an existing file). Plus the two workflow records (this artifact + `sprint-status.yaml`).

**Production code — 6 files:**

| File | Change |
|---|---|
| `apps/api/app/modules/sot/browse_category_admin_router.py` | **NEW.** `POST /api/admin/categories`, `PATCH /api/admin/categories/{category_id}`, `DELETE /api/admin/categories/{category_id}`, `PUT /api/admin/models/{model_id}/categories`. All `current_admin`, all `tags=["sot-admin-governance"]`, mirroring `tag_group_admin_router.py`'s docstring/structure. |
| `apps/api/app/modules/sot/admin_schemas.py` | MODIFY. ADD `BrowseCategoryCreate`, `BrowseCategoryPatch` (with the NOT-NULL `_reject_explicit_null` validator on `slug`/`name_en`/`position`), `ModelCategoriesReplace`. |
| `apps/api/app/modules/sot/admin_service.py` | MODIFY. ADD `_browse_category_snapshot`, `create_browse_category`, `update_browse_category`, `delete_browse_category`, `replace_model_categories`. No existing function's body changes. |
| `apps/api/app/modules/sot/schemas.py` | MODIFY. ADD `BrowseCategoryAdminRead(BrowseCategoryRead)` (+`inclusion_criterion`). `BrowseCategorySummary`/`BrowseCategoryRead`/`ModelDetail` unchanged. |
| `apps/api/app/core/audit.py` | MODIFY. ADD `"browse_category"` to `KNOWN_ENTITY_TYPES` + its doc-comment entry. No existing entry changes. |
| `apps/api/app/router.py` | MODIFY. ADD one `api_router.include_router(...)` line for the new router, positioned immediately after the existing `sot_tag_group_admin_router` line. |

**Tests — 2 files, both NEW:**

| File | Change |
|---|---|
| `apps/api/tests/test_sot_admin_categories.py` | **NEW.** `POST`/`PATCH`/`DELETE /api/admin/categories[...]` — AC-1…AC-24, AC-34…AC-37 (category-scoped OpenAPI/audit assertions). |
| `apps/api/tests/test_sot_admin_model_categories.py` | **NEW.** `PUT /api/admin/models/{id}/categories` — AC-25…AC-33. |

**Test file extended in place (counted above as part of the "6 production" OpenAPI-guard coverage, not a 9th file — `test_openapi_agent_surface.py` is a test file; recorded here separately for clarity, bringing the true test-file count to 3):**

| File | Change |
|---|---|
| `apps/api/tests/test_openapi_agent_surface.py` | MODIFY — additive only. Extend `_GOVERNANCE_ROUTES` (`:257-262`) with the four new `(METHOD, path)` tuples. No existing test body changes; every existing assertion in the file, including the `Category*`-naming guards (§3.6), stays byte-unmodified and must keep passing against the new routes/schemas. |

**Workflow records (separate from the product commit):** this story artifact and `_bmad-output/implementation-artifacts/sprint-status.yaml`.

**Asserted byte-unchanged (AC-36):** `apps/api/app/core/db/models/_entities.py`; `apps/api/app/core/db/models/__init__.py`; `apps/api/migrations/**`; `apps/api/app/core/db/seed.py`; `apps/api/scripts/seed_browse_categories.py`; `apps/api/app/modules/sot/router.py`; `apps/api/app/modules/sot/service.py`; `apps/api/app/modules/sot/admin_router.py`; `apps/api/app/main.py`; `apps/api/app/core/auth/csrf.py`; `apps/api/app/core/auth/dependencies.py`; `apps/api/tests/test_sot_categories.py`; `apps/api/tests/test_sot_models_category_scope.py`; `apps/api/tests/test_sot_models_tag_search.py`; `apps/api/tests/test_sot_admin_tag_groups.py`; `apps/api/tests/test_sot_admin_tags.py`; `apps/api/tests/test_sot_auth_boundary.py`; `apps/api/tests/test_route_enforcement_gate.py`; `apps/api/tests/test_csrf_middleware.py`; `apps/api/tests/test_browse_category_entity.py`; `apps/api/tests/test_migration_0020.py`; `apps/api/tests/test_seed_browse_categories.py`; `apps/api/tests/test_orm_migration_parity.py`; `apps/api/tests/conftest.py`; `apps/web/**`; `workers/**`; `docs/operations.md` (F-11); `pyproject.toml`; `uv.lock`; `infra/scripts/check-all.sh`; all `_bmad-output/planning-artifacts/**`.

## 8. Dev Notes

### 8.1 Router file shape — mirror `tag_group_admin_router.py` verbatim

```python
"""Admin-only browse-category governance write endpoints (Story 49.5).

Prefix: /api/admin
Auth: `current_admin` (admin role only — 403 `admin_required` otherwise).

Deliberately SEPARATE from `sot/admin_router.py` (the agent-write ingestion
surface): categories are admin curation, never agent-writable — per ratified
Decision AY (architecture.md:3334-3341), which places every route in this
router under `current_admin`, mirroring the identical admin-curation/
agent-ingestion split `tag_group_admin_router.py` already applies (FR25-ADMIN-1
/ Decision AW, D-ADMINONLY-1) — not a task-local invention (see story §6 F-9).
Lives under the `sot-admin-governance` tag alongside tag-group governance.

Owns:
  POST   /api/admin/categories                        — create
  PATCH  /api/admin/categories/{category_id}           — rename/reorder/reparent
  DELETE /api/admin/categories/{category_id}           — delete (409 unless clean or detach=true)
  PUT    /api/admin/models/{model_id}/categories        — replace-set assignment
"""
```

### 8.2 `create_browse_category` — parent validation ahead of insert

```python
def create_browse_category(session, *, payload, actor_user_id) -> BrowseCategory:
    if payload.parent_id is not None:
        parent = session.get(BrowseCategory, payload.parent_id)
        if parent is None:
            raise LookupError("parent not found")
        if parent.parent_id is not None:
            raise ValueError("parent_not_root")
    now = datetime.datetime.now(datetime.UTC)
    cat = BrowseCategory(
        slug=payload.slug, name_en=payload.name_en, name_pl=payload.name_pl,
        description_en=payload.description_en, description_pl=payload.description_pl,
        inclusion_criterion=payload.inclusion_criterion, position=payload.position,
        parent_id=payload.parent_id, created_at=now, updated_at=now,
    )
    session.add(cat)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc
    _audit_entity(session, action="browse_category.create", entity_type="browse_category",
                  entity_id=cat.id, actor_user_id=actor_user_id, after=_browse_category_snapshot(cat))
    session.commit()
    session.refresh(cat)
    return cat
```

### 8.3 `update_browse_category` — the three independent reparent checks

```python
def update_browse_category(session, *, category_id, patch, actor_user_id) -> BrowseCategory:
    cat = session.get(BrowseCategory, category_id)
    if cat is None:
        raise LookupError("category not found")
    before = _browse_category_snapshot(cat)
    data = patch.model_dump(exclude_unset=True)

    if "parent_id" in data and data["parent_id"] is not None:
        new_parent_id = data["parent_id"]
        if new_parent_id == category_id:
            raise ValueError("self_cycle")
        parent = session.get(BrowseCategory, new_parent_id)
        if parent is None:
            raise LookupError("parent not found")
        if parent.parent_id is not None:
            raise ValueError("parent_not_root")
        has_children = session.exec(
            select(BrowseCategory.id).where(BrowseCategory.parent_id == category_id)
        ).first()
        if has_children is not None:
            raise ValueError("reparent_exceeds_depth")

    for field, value in data.items():
        setattr(cat, field, value)
    cat.updated_at = datetime.datetime.now(datetime.UTC)
    after = _browse_category_snapshot(cat)
    session.add(cat)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("slug_conflict") from exc
    _audit_entity(session, action="browse_category.update", entity_type="browse_category",
                  entity_id=cat.id, actor_user_id=actor_user_id, before=before, after=after)
    session.commit()
    session.refresh(cat)
    return cat
```

Note the **no-op self-rename** case (AC-11): patching `slug` to its own current value reaches `session.flush()` with the row's own pre-existing unique index entry unchanged — SQLite's unique index does not conflict with a row against itself, so this returns 200 without any special-case code.

### 8.4 `delete_browse_category` — children checked first, unconditionally

```python
def delete_browse_category(session, *, category_id, detach, actor_user_id) -> None:
    cat = session.get(BrowseCategory, category_id)
    if cat is None:
        raise LookupError("category not found")

    child_ids = session.exec(
        select(BrowseCategory.id).where(BrowseCategory.parent_id == category_id)
    ).all()
    if child_ids:
        raise ValueError("category_has_children")

    assignment_rows = session.exec(
        select(ModelBrowseCategory).where(ModelBrowseCategory.category_id == category_id)
    ).all()
    if assignment_rows and not detach:
        raise ValueError("category_in_use")

    before = _browse_category_snapshot(cat)
    if assignment_rows:
        detached_ids = [row.model_id for row in assignment_rows]
        before["detached_model_ids"] = [str(m) for m in detached_ids]
        before["detached_model_count"] = len(detached_ids)
        for row in assignment_rows:
            session.delete(row)
        session.flush()

    _audit_entity(session, action="browse_category.delete", entity_type="browse_category",
                  entity_id=cat.id, actor_user_id=actor_user_id, before=before)
    session.delete(cat)
    session.commit()
```

### 8.5 `replace_model_categories` — duplicate-id guard the tags precedent lacks

```python
def replace_model_categories(session, *, model_id, payload, actor_user_id) -> list[BrowseCategory]:
    _get_model_active(session, model_id)  # LookupError("model not found") — reused verbatim

    if len(payload.category_ids) != len(set(payload.category_ids)):
        raise ValueError("duplicate_category_ids")

    for cid in payload.category_ids:
        if session.get(BrowseCategory, cid) is None:
            raise ValueError(f"category not found: {cid}")

    before_ids = [row.category_id for row in session.exec(
        select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
    ).all()]

    existing_rows = session.exec(
        select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
    ).all()
    for row in existing_rows:
        session.delete(row)
    session.flush()

    for cid in payload.category_ids:
        session.add(ModelBrowseCategory(model_id=model_id, category_id=cid))
    session.flush()

    after_ids = list(payload.category_ids)
    _audit_entity(session, action="model.update", entity_type="model", entity_id=model_id,
                  actor_user_id=actor_user_id,
                  before={"category_ids": [str(c) for c in before_ids]},
                  after={"category_ids": [str(c) for c in after_ids]})
    session.commit()

    cats = (session.exec(select(BrowseCategory).where(BrowseCategory.id.in_(after_ids))).all()
            if after_ids else [])
    return sorted(cats, key=lambda c: (c.position, c.slug))
```

Router-level `HTTPException` mapping: `LookupError` → 404, `ValueError("duplicate_category_ids")` → 400, any other `ValueError` (the `f"category not found: {cid}"` shape) → 404 — matching `PUT /models/{id}/tags`'s documented ("404 if model or any tag id is missing") contract exactly (§6 F-9).

### 8.6 Anti-patterns — do not do these

- ❌ Trying to catch `IntegrityError` from the DELETE to distinguish "children" vs. "assignments" — SQLite's error message does not reliably name which FK fired; the proactive pre-query approach in §8.4 is required, not stylistic.
- ❌ Letting `detach=true` reparent or delete children — that redefines the flag's documented meaning (model-assignment detach only) with no planning-artifact mandate; AC-21/AC-22 forbid this explicitly.
- ❌ Silently de-duplicating `category_ids` in the replace-set payload instead of rejecting with 400 — a caller sending literal duplicates has a bug worth surfacing, not silently masking (AC-28).
- ❌ Building a `revision`/`ETag`/`If-Match` precondition on the replace-set endpoint "while we're in here" — explicitly out of scope; §3.9/AC-32 name it as a **future** trigger, not this story's work.
- ❌ Adding `category`/`category_id` as a property anywhere on `ModelSummary`/`ModelDetail`/`ModelCreate`/`ModelPatch`/`ShareModelView`, or naming any new schema bare `Category*` — two shipped guard tests fail immediately (§3.6).
- ❌ Fixing `docs/operations.md`'s stale "Admin write" enumeration as a drive-by — reported (F-11), not edited, to keep this story's diff to exactly its own surface.
- ❌ Retroactively adding a duplicate-id guard to `replace_model_tags` "since we're fixing the same bug for categories" — that is a different, closed story's surface; report it (already done, F-9), don't silently patch it here.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-1 | Implementer follows the 42.4 story's stale `create_category`/`admin_service.py:1150-1306` citation and either invents dead code or gets confused about the real template. | §6 F-1 states the fact plainly and points at the real, verified template (`create_tag_group`/`update_tag_group`/`delete_tag_group`). |
| R-2 | A category-with-children delete raises a raw, unhandled `IntegrityError` (500) instead of a clean 409, because the planning artifacts only speak of "assignments." | §6 F-4 + AC-21/AC-22 + §8.4's children-first proactive query make this a first-class, tested case. |
| R-3 | `detach=true` scope creeps into reparenting/deleting children "to be helpful," silently redefining the flag. | AC-21 makes children-present a flat, unconditional 409 regardless of `detach`; §8.6 lists it as an explicit anti-pattern. |
| R-4 | A literal-duplicate `category_ids` payload crashes with an uncaught `IntegrityError` → 500, replaying the `PUT /models/{id}/tags` gap this story was supposed to close. | AC-28 + §8.5's explicit pre-check, tested in T5.1 before any session mutation. |
| R-5 | The admin-only auth tier on `PUT /categories` is later found inconsistent with `agent`-capable model ingestion, and a future agent workflow needs to set categories but can't. | §6 F-9 flags this explicitly as an unresolved-rationale tightening for the Validate pass / future story to revisit; not silently asserted as obviously correct. |
| R-6 | The new governance routes are invisible to `test_every_admin_sot_operation_has_summary/description` because `sot-admin-governance` sits outside `TARGET_ROUTER_TAGS`, and ship with an empty `description` unnoticed. | §6 F-5 + AC-37 + T6.1 extend the existing `_GOVERNANCE_ROUTES`-driven test rather than relying on the generic (non-covering) gate. |
| R-7 | Audit snapshot payload grows unbounded on a category with a very large assigned-model set, mirroring the still-open epic:42 concern. | AC-35 states the accepted posture explicitly (paired count, re-evaluate-if-large, not cap-now) so it is not mistaken for an oversight at review time. |

## 10. Non-goals (this story ships none of these)

Any frontend/admin screen (`52.2`); the 1–3-per-model advisory warning UI/logic (`FR26-CAT-3`, owned by `52.2`); curation QA surfaces (`52.3`); category-assignment automation or inference from tags (explicitly forbidden by Decision AX/AY); any new Alembic migration or DDL change; any seed-script change or re-run; any optimistic-concurrency mechanism (`revision`/ETag/`If-Match`) on the replace-set endpoint — a named future trigger, not this story's work; cascading child-delete or auto-reparent-on-delete; a truncation/cap mechanism on the audit payload; correcting `docs/operations.md`'s stale "Admin write" endpoint enumeration (reported, not edited — F-11); any change to `GET /api/categories[/{slug}]`, `GET /api/models?category=`, or `ModelDetail.categories` (Story 49.3, untouched); any change to `PUT /models/{id}/tags` or any other existing agent-write route; any live-database, production, push, merge or deploy action.

## 11. Branch and commit atomicity

One story branch off `main`, one commit containing the **9** product/doc files in §7 (6 production + 3 test, 2 of the 3 test files NEW), plus the two workflow records. `check-all.sh` 16/16 must pass on the branch alone. The story is independently mergeable: it depends only on Story 49.1 and Story 49.3, both already on `main` at this baseline.

## 12. Traceability

| AC | Requirement / Decision | Source |
|---|---|---|
| AC-1…AC-7 | FR26-ADMIN-1 create; Decision AY admin governance | `architecture.md:3334-3341`; `epics.md:4491-4493` |
| AC-8…AC-16 | FR26-ADMIN-1 rename/reorder; FR26-CAT-4 depth-2 + self-cycle | `architecture.md:3299` (Decision AX depth ceiling); `epics.md:4491-4493` |
| AC-17…AC-24 | FR26-ADMIN-1 delete/409/detach; epic:42 audit precedent | `sprint-status.yaml:383`; `architecture.md:3337`; `sprint-status.yaml:439-442` (epic:42 action item) |
| AC-25…AC-33 | FR26-ADMIN-1 replace-set; honest LWW concurrency posture | `architecture.md:3338-3340`; `sprint-status.yaml:383,398` |
| AC-34, AC-35 | Audit contract; D-AUDIT-2 bounded snapshot; epic:42 precedent | `app/core/audit.py:16-49`; `42-4-admin-group-governance.md` AC #6 (D-AUDIT-2) |
| AC-36 | Additive-only invariant; route-enforcement gate | `test_route_enforcement_gate.py`; §3.5 |
| AC-37 | OpenAPI honesty for off-target-tag-set routes | `test_openapi_agent_surface.py:61,257-297` |

## 13. Project structure notes

One new router file (`browse_category_admin_router.py`), sized and shaped like its direct sibling `tag_group_admin_router.py` — the codebase's established pattern of one focused router module per governance taxonomy family (tags/tag-groups vs. categories), rather than folding new write surface into the already-980-line agent-write `admin_router.py`. Request/response schemas and service functions extend the existing shared `admin_schemas.py`/`admin_service.py`/`sot/schemas.py` files rather than fragmenting further — matching how tag-group governance itself was added to those same three files in Story 42.4. No new top-level module, package, or directory. No conflict with the unified project structure was found.

## 14. Testing standards summary

`.venv/bin/pytest` from `apps/api` (the venv-relative form `check-all.sh:86-87` uses). Final commands:

```bash
# targeted (new coverage)
cd apps/api && .venv/bin/pytest -q tests/test_sot_admin_categories.py tests/test_sot_admin_model_categories.py

# non-regression witnesses (must pass byte-unmodified, or additive-only for the one extended file)
cd apps/api && .venv/bin/pytest -q \
  tests/test_sot_categories.py tests/test_sot_models_category_scope.py \
  tests/test_sot_admin_tag_groups.py tests/test_sot_admin_tags.py \
  tests/test_sot_auth_boundary.py tests/test_openapi_agent_surface.py \
  tests/test_route_enforcement_gate.py tests/test_csrf_middleware.py \
  tests/test_orm_migration_parity.py tests/test_browse_category_entity.py

# full suite + lint
cd apps/api && .venv/bin/pytest -q
cd apps/api && .venv/bin/ruff format --check . && .venv/bin/ruff check .

# controller-owned frozen gate (NOT run by the implementer)
infra/scripts/check-all.sh
```

## 15. Dev Agent Record

*(Empty — no implementation has occurred. `bmad-dev-story` fills this in, quoting every RED and GREEN verbatim, and labelling every structural/composition guard as such per §5's ordering rule.)*

### Agent Model Used

*(To be recorded by the dev pass.)*

### Debug Log References

### Completion Notes List

### File List

## 16. Validation Record

**Verdict: PASS** — native `bmad-create-story` **action=validate** (menu VS), run 2026-07-28 by a fresh, independent Claude Sonnet 5 session in the same isolated worktree, per `checklist.md`'s "When Running in Fresh Context" protocol (loaded independently of, and with no memory of, the Create pass). **NO human review of any kind** — no Ezop signature, no Ezop review, no Laura review is recorded, implied, or claimable from this document.

**Routing.** `AGENTS.md`, `CLAUDE.md`, `_bmad-output/project-context.md`, and the Laura Agent Rulebook were read first. `_bmad/_config/manifest.yaml` (BMad 6.10.0), `bmad-help.csv` row 27 (`bmad-create-story` / Validate Story / VS / preceded-by `bmad-create-story:create`, followed-by `bmad-dev-story`, required=false), and `skill-manifest.csv` row 40 confirmed `bmad-create-story:validate` as the canonical post-Create action. `.claude/skills/bmad-create-story/` was present in this worktree (repaired by the Create pass, §17.6) and was used as-is — no second repair needed. `SKILL.md` contains only the Create-action workflow (steps 1–6); the Validate action's actual content is `checklist.md`, whose own "When Running in Fresh Context" section directs a fresh-context reviewer to load the story file and source documents directly and systematically re-derive rather than trust the Create pass — exactly the protocol this session followed. `resolve_customization.py` was not re-run (no team/user override files exist for this skill per the Create pass's own resolution, unchanged at this baseline).

**Re-derivation performed (independent of the Create pass's prose).** `epics.md:4375-4496` (Initiative 26 overview, FR matrix, Epic 49 + Story 49.5 sketch) and `architecture.md:3285-3386` (Decisions AX, AY, AZ) were read in full, not selectively. Source code was read directly at HEAD `0df663e`: `_entities.py:117-183` (`ModelTag`, `BrowseCategory`, `ModelBrowseCategory` — confirms F-2's RESTRICT/CASCADE claims verbatim, including `parent_id`'s `ondelete="RESTRICT"` at `_entities.py:158-161`); `app/core/audit.py:1-69` (`KNOWN_ENTITY_TYPES` — confirms `"browse_category"` is genuinely absent today, AC-34 is additive); `admin_service.py:807-859` (`replace_model_tags` — confirms F-9(b)'s no-duplicate-guard claim: the only guard is a docstring promise, not code) and `:1150,1192,1247` (`create_tag_group`/`update_tag_group`/`delete_tag_group` — confirms F-1's "real template" claim; the retired `create_category`/`admin_service.py:1150-1306` citation F-1 warns against is indeed absent, `grep` for `def create_category\|class Category\b` returns zero matches); `admin_router.py:98-120,147,571-598` (`_current_admin_or_agent_dep`/`_current_principal`, `agent-write` tags — confirms F-9(a)'s tags-endpoint auth claim); `tag_group_admin_router.py:1-40` (confirms F-7's `current_admin`/`_current_admin_dep` claim, and supplies the admin-curation-vs-agent-ingestion doctrine used to resolve Q-1, below); `test_openapi_agent_surface.py:61,257-269` (`TARGET_ROUTER_TAGS`, `_GOVERNANCE_ROUTES` — confirms F-5's exact set contents); `test_route_enforcement_gate.py:37-42` (`_AUTH_DEP_NAMES` — confirms F-7's exact set contents); `app/core/auth/dependencies.py:55-76` (`current_admin = Depends(_current_admin_dep)`); `app/core/auth/csrf.py:6-17` (`UNSAFE_METHODS`, prefix-based `csrf_guard` — confirms F-8). No test was run, no throwaway database was built, no live system was touched — this is source re-derivation only, consistent with a story that has not yet entered `bmad-dev-story`.

**Priority arbitration (task-mandated, not merely repeated from the Create pass):**

- **A — Child-category delete conflict (§6 F-4, AC-21/AC-22, §18 Q-2): RATIFIED, no amendment to the substantive contract.** The `409 category_has_children` unconditional-and-`detach`-independent design is confirmed the correct minimal, planning-compatible resolution — see Q-2 above for the full re-derivation. No planning artifact contradicts it; the RESTRICT FK it defends against is real; the rejected cascading alternative is correctly recorded, not adopted.
- **B — Admin-only replace-set rationale (§6 F-9, §18 Q-1): AMENDED for truthfulness, not rejected.** The Create pass's framing — "no ratified rationale beyond the task's own explicit instruction" — understated the evidence. `current_admin`-only is explicitly ratified by Decision AY (`architecture.md:3334-3341`, which places this exact route under the heading naming `current_admin`) and is not a novel asymmetry: it is the same admin-curation/agent-ingestion split `tag_group_admin_router.py` already applies to facet governance (FR25-ADMIN-1/Decision AW, D-ADMINONLY-1), verified verbatim in that router's own docstring. §6 F-9's addendum, §8.1's router docstring, and §18 Q-1 are corrected in place to state this truthfully. This was a documentation-accuracy defect in the Create pass's self-characterization, not a defect in the underlying design choice, which was correct all along.

**Other checks.** Traceability (§12) cross-checked against `epics.md`'s FR matrix (`4397-4411`) — no mismatch found. AC set (§4, AC-1…AC-37) re-read for contradictions, missing cases, and impossible test claims — none found; the depth-ceiling reparent logic (§8.3) was independently traced (a category with children cannot itself have a non-null `parent_id` under the depth-2 ceiling already enforced by AC-7/AC-14, so AC-15's check has no false-positive no-op case). §7's predicted file list and §11's branch/commit atomicity were read for internal consistency with §5's task list — consistent. No blocking finding survived re-derivation.

**Scope of this pass.** Story-artifact and `sprint-status.yaml` amendment only, per this pass's write policy. No code, test, config, or migration file touched; no live database, network, commit, push, merge, deploy, or human review of any kind. **`G26-DEVGO` remains NOT granted by this pass** — validation clears the story to `ready-for-dev`, which is a prerequisite for, not equivalent to, implementation authorization; the controller must still separately confirm this specific story under the standing initiative authorization before `bmad-dev-story` runs.

## 17. Disclosed deviations from the base workflow

1. **The Create pass stopped at `ready-for-validation`, and status advanced no further at that time — by explicit task scope, not by the base workflow's own logic.** *(Superseded 2026-07-28 by the separate Validate pass recorded in §16, which returned PASS and advanced the status to `ready-for-dev` per this same repo convention. The text below is preserved as the Create pass's honest record of its own scope, not as a current status claim.)* The base `bmad-create-story` workflow (`SKILL.md` step 5/6, `template.md:3`) literally sets `Status: ready-for-dev` at the end of a create pass. **This repo's established, repeatedly-disclosed convention** (Stories 49.1/49.2/49.3 all record this explicitly — verified this session by reading the committed initial-create text of Story 49.3, `git show 2d4fd75:_bmad-output/implementation-artifacts/49-3-category-read-api-and-model-scope.md:512` — *"The create pass ended at `ready-for-validation`, not the base workflow's `ready-for-dev`... 49.1/49.2 both used `ready-for-validation` at that stage"*) is that a Create pass alone lands at `ready-for-validation`, and only a subsequent, independent Validate pass with a `PASS` verdict advances it to `ready-for-dev`. This session follows that established repo convention rather than the base skill's literal instruction, and additionally — unlike 49.1/49.2/49.3, which bundled Create+Validate into one session/commit — this session runs **Create only**, per this pass's explicit operating scope ("Perform exactly ONE native BMAD lifecycle transition... Do not validate"). Both the status value and the stop-after-create scoping are disclosed, not silently applied.
2. **`epic-49` stays `in-progress`.** It was flipped at Story 49.1's dev-story pass; this story is the fifth in the epic, so the base workflow's first-story auto-promote does not apply and no change is warranted.
3. **The double-RESTRICT-on-delete resolution (§6 F-4, AC-21/AC-22) is a create-pass judgment call, not a transcription of any planning artifact.** No source document (`sprint-status.yaml`, `architecture.md`, `epics.md`) addresses the case of a category with children being deleted; this document adopts "children are an unconditional, `detach`-independent 409" as the minimal-diff resolution and states the reasoning and the rejected alternative explicitly (F-4) rather than picking silently or leaving it unspecified for the dev pass to improvise.
4. **Subagent use was partial, not full, relative to the base workflow's recommendation.** `SKILL.md`'s "On Activation" preamble recommends subagents/subprocesses for "thoroughly analyz[ing] different artifacts simultaneously." This session dispatched **one** `Explore` research subagent for the exhaustive current-code grounding in §6 (tag_group_admin_router.py, audit.py, admin_service.py, admin_schemas.py, test precedents — its full report is the basis for F-1 through F-11), then continued with direct in-session reads for verbatim code citation (§8's code blocks) and for the epics.md/architecture.md/sprint-status.yaml planning-artifact grounding, rather than fanning out multiple parallel subagents for every artifact category as the base workflow's ideal describes. This reflects the session's serial, single-orchestrator operating mode for this task, not a decision that parallel subagents were unnecessary.
5. **`checklist.md`'s "fresh independent context, competitive review" protocol was applied inline during authoring, not as a separate fresh-context pass.** `SKILL.md` step 6 directs the create pass to "Validate the newly created story file against `./checklist.md` and apply any required fixes before finalizing." `checklist.md` itself is written as a from-scratch, independent-context adversarial re-derivation — structurally the same exercise as the separate `bmad-create-story:validate` action this pass is explicitly scoped **not** to run. This session resolved that overlap by applying the checklist's disaster-prevention categories (reinvention, wrong file locations, regression, vague ACs, scope creep) as an authoring discipline throughout §4/§6/§8/§9 — every AC in this document was written against a real, cited code fact rather than an assumption, and every open judgment call is flagged in §6/§18 rather than silently resolved — plus one direct post-write arithmetic self-check (§7's file-count line, corrected in place before finalizing). It did **not** spin up a genuinely fresh, independent context to adversarially re-derive every citation the way the separate Validate action would. That full independent pass remains owed to the next `bmad-create-story:validate` session, per §16/§18.
6. **This worktree's `.claude/skills/` directory was missing at session start and was repaired before any skill invocation, rather than proceeding hand-authored.** `.claude/skills/` is gitignored (`.gitignore:143`) and regenerated by the `bmad-method` installer (per the durable memory note on this repo's install/surface drift); `git worktree add` — which created this isolated worktree — only materializes git-tracked content, so the 90 native skill directories (including `bmad-help` and `bmad-create-story` themselves) were simply absent here at session start, even though `_bmad/_config/manifest.yaml` (the git-tracked config surface) correctly reported BMad 6.10.0 installed. Rather than hand-authoring the story around the missing native skill (explicitly forbidden by this pass's operating instructions) or running the full non-interactive installer (which would have touched the git-tracked `_bmad/_config/` surface, violating the "no code/config change" scope of this pass), this session copied `.claude/skills/` verbatim from the sibling worktree `/home/ezop/repos/3d-portal` — confirmed to be the exact same repo at the exact same BMad version (`manifest.yaml` byte-identical, `diff` confirmed) — into this worktree. This is a purely local, gitignored filesystem repair with **zero** git diff (verified: `git status --short` unaffected by the copy) and is the smallest change that restores genuine native-skill invocability without touching any tracked file. Recorded here in full rather than silently worked around.

## 18. Open questions carried to Validate (no silent resolution claimed)

Three design decisions in this Create pass were explicitly flagged, not silently asserted as obviously correct. The Validate pass (2026-07-28) re-derived each against source: Q-1 and Q-2 are now closed (see below); Q-3 is a minor, non-blocking file-placement question carried forward for the dev pass.

- **Q-1 — CLOSED by Validate (2026-07-28).** Is `current_admin`-only (no `agent-write`) the right auth tier for `PUT /api/admin/models/{id}/categories`? **Yes — ratified, not merely task-instructed.** `architecture.md:3334-3341` (Decision AY) explicitly places this exact route under `current_admin` alongside the other three; the split follows the same admin-curation/agent-ingestion doctrine `tag_group_admin_router.py` already codifies for facet governance (FR25-ADMIN-1/Decision AW, D-ADMINONLY-1). See §6 F-9 addendum for the full re-derivation. Residual, non-blocking observation: `architecture.md` does not itself spell out prose reasoning for *why* the replace-set operation specifically (vs. the CRUD routes) falls on the admin-curation side — a documentation-completeness note for a future architecture-hygiene pass, not a gap in this story's authorization.
- **Q-2 — RATIFIED by Validate (2026-07-28), no override.** Is "children block delete unconditionally, `detach=true` never touches children" (§6 F-4) the right shape, versus an alternative where `detach=true` also orphans children to `parent_id=null`? **Confirmed as the correct minimal, planning-compatible contract.** Re-derived independently: `BrowseCategory.parent_id`'s `ondelete="RESTRICT"` is verified at `_entities.py:158-161`; no planning artifact (`epics.md:4491-4493`, `architecture.md:3337`) addresses the children-present case at all — both speak only of model-assignment conflicts — so this is genuinely an unfilled gap the Create pass had to resolve, not a contradiction of ratified text. The adopted shape is the more conservative of the two live options, does not silently redefine `detach=true`'s documented (model-only) scope, requires no new query parameter or cascading-delete semantics nothing in Decision AX/AY asked for, and is consistent with Decision AX's "MVP writes no child categories at all" framing (the path is rare by construction, but must not 500 when hit). The rejected alternative (auto-orphan children on `detach=true`) remains recorded in §6 F-4 for a future reader; it is not adopted.
- **Q-3 — Should the admin-write response schema (`BrowseCategoryAdminRead`) live in `sot/schemas.py` (response DTOs) as this document places it, or in `admin_schemas.py` alongside the request DTOs it's paired with?** This document follows the existing file-role convention (`schemas.py` = response/read shapes including `TagGroupSummary`; `admin_schemas.py` = request shapes including `TagGroupCreate`/`Patch`) exactly, but `BrowseCategoryAdminRead` is genuinely admin-specific in a way `BrowseCategorySummary`/`BrowseCategoryRead` are not — worth a second look at Validate.

## 19. Change Log

| Date | Pass | Result |
|---|---|---|
| 2026-07-28 | `bmad-create-story` (action=create, menu CS), Claude Sonnet 5, native BMAD | Story created at baseline `0df663e`; status `ready-for-validation`. `.claude/skills/` repair disclosed (§17.6). No human review; no Ezop or Laura sign-off recorded or implied. No Validate pass run this session (explicit task scope) — §16/§17.1/§18 record the resulting open items honestly rather than presenting the document as validated. |
| 2026-07-28 | `bmad-create-story` (action=validate, menu VS), fresh independent Claude Sonnet 5 session, native BMAD | **PASS.** Independent re-derivation of every §6 finding against source at HEAD `0df663e` (see §16). Priority A (child-delete conflict, §18 Q-2) ratified unchanged. Priority B (admin-only replace-set rationale, §18 Q-1) amended for truthfulness — §6 F-9 addendum, §8.1 docstring, §18 Q-1 corrected to cite the ratified Decision AY basis instead of framing the choice as merely task-mandated. Status → `ready-for-dev`; `epic-49` stays `in-progress`. No human review of any kind. `G26-DEVGO` still NOT granted — controller confirmation of this specific story remains owed before `bmad-dev-story`. No code/test/config/migration/live change; no commit, push, merge, or deploy. |
