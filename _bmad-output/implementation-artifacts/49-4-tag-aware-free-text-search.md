---
baseline_commit: 166ef10a6fcc71a823bd655155b94a24cab1f20e
---

# Story 49.4: Tag-aware free-text search

Status: ready-for-dev

<!-- Provenance. CREATE: native bmad-create-story (action=create, menu CS), 2026-07-26, Claude Opus 5 agent session, routed via the repository's native bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story` (CS / create; preceded-by bmad-sprint-planning, followed-by bmad-create-story:validate, required=true); canonical skill id/path confirmed in _bmad/_config/skill-manifest.csv (`bmad-create-story`, module bmm, `_bmad/bmm/4-implementation/bmad-create-story/SKILL.md`). Customization resolved via `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow` -> {"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}; no team override (`_bmad/custom/bmad-create-story.toml` absent) and no user override. persistent_facts resolved to `_bmad-output/project-context.md` (exists, 321 lines, loaded). Effective config resolved via `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` (user_name Ezop, communication_language Polish, document_output_language English, implementation_artifacts `_bmad-output/implementation-artifacts`). `discover-inputs.md` executed (epics.md, architecture.md, prd.md loaded whole; no sharded dirs; ux artifacts under planning-artifacts/ux-designs/ consulted). `checklist.md` executed against the drafted artifact before finalising. Baseline HEAD 166ef10a6fcc71a823bd655155b94a24cab1f20e on branch docs/init26-e49-4-create in worktree /home/ezop/worktrees/3d-portal-e49-4-create, working tree clean at start. THIS PASS IS CREATE ONLY. The story has NOT been validated — §16 is empty and bmad-create-story:validate (VS) has not run. NO human review of any kind. No Ezop signature, no Ezop review, no Laura review and no Laura signature is recorded, implied or claimable from this pass; every finding in this document is Claude/native-BMAD only. G26-DEVGO is NOT granted by this create pass. No production code, no test, no planning artifact, no config and no live DB was touched; no commit, push, merge or deploy. Read-only baseline probes were executed against THROWAWAY tmpdir SQLite databases only — see §6 F-1 and §15 for the verbatim outputs and the exact disclosure of where they ran. -->

<!-- Provenance. VALIDATE: native bmad-create-story (action=validate, menu VS), 2026-07-26, fresh independent Claude Opus 5 agent session, routed via the repository's native bmad-help -> _bmad/_config/bmad-help.csv row `bmad-create-story` / `Validate Story` / VS / action `validate` (phase 4-implementation; preceded-by bmad-create-story:create, followed-by bmad-dev-story); canonical skill id/path re-confirmed in _bmad/_config/skill-manifest.csv line 40 (`bmad-create-story`, module bmm, `_bmad/bmm/4-implementation/bmad-create-story/SKILL.md`). DISCLOSED SKILL-DISCOVERY MECHANISM: this gitignored worktree has no `.claude/skills/` directory, so SKILL.md, checklist.md and customize.toml were read from the canonical installed copies under /home/ezop/repos/3d-portal/.claude/skills/bmad-create-story/; the native workflow was executed, not skipped. Customization re-resolved via `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow` -> {"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}; no team override (`_bmad/custom/bmad-create-story.toml` absent) and no user override; persistent_facts loaded from `_bmad-output/project-context.md` (321 lines). Config from `_bmad/bmm/config.yaml`. `checklist.md` executed in full. THIS PASS SUPERSEDES the create-pass sentences above that state "§16 is empty" and "bmad-create-story:validate (VS) has not run" — both were true at create and are now historical. VERDICT: PASS; status ready-for-validation -> ready-for-dev; 3 defects amended (§16 V-1/V-2/V-3). Create claims were treated as UNTRUSTED and independently re-derived at baseline HEAD 166ef10a6fcc71a823bd655155b94a24cab1f20e on branch docs/init26-e49-4-create. NO human review of any kind. No Ezop signature, no Ezop review, no Laura review, no Laura signature is recorded, implied or claimable from this pass. G26-DEVGO is NOT granted by this validation pass; epic-49 stays in-progress. No production code, no test, no planning artifact, no config and no live DB was touched; no commit, push, merge or deploy. Only two files were edited: this artifact and sprint-status.yaml. Read-only probes ran against THROWAWAY tmpdir SQLite databases only, executed in the sibling checkout /home/ezop/repos/3d-portal (re-verified this session to be at the identical commit 166ef10 with a clean tree) because this worktree ships no apps/api/.venv — see §16 for the full evidence list. -->

## 1. Story

As an **authenticated portal member searching the catalogue**,
I want **the free-text `q` filter to also find models by the names of the tags assigned to them**,
so that **typing "kabel" surfaces both models named for cables and models merely *tagged* `Kabel`/`Cable`, without the result set growing duplicate rows or an inflated `total`.**

**Epic:** E49 — Browse-category data + additive API foundation (backend).
**Story key:** `49-4-tag-aware-free-text-search` *(renumbered from 49.5 by the 2026-07-26 controller review).*
**Requirements:** FR26-SEARCH-1, NFR26-PERF-1.
**Architecture:** the tag-aware `q` paragraph at `architecture.md:3316-3326` is the canonical source; NFR26-PERF-1's query-count framing at `architecture.md:3328` is binding. `prd.md:2248` (FR) and `prd.md:2270` (NFR) restate the same contract.
**Depends on:** Story 49.3 (`done`, `category` scope + category read API, on `main` at this baseline). Nothing in 49.1/49.2/49.3 is re-opened. **Not a prerequisite for** any E49 story; E50.3's suggestion surface consumes the *already shipped* `GET /api/tags?q=` and does **not** consume this change.

**This story adds no route, no query parameter, no schema and no table.** It changes the meaning of exactly one existing filter, `q`, on exactly one endpoint, `GET /api/models`.

## 2. Gate and authorization posture (truthful)

- **G26-DEVGO — GRANTED 2026-07-26 by Laura/controller for Story 49.4** under Ezop's standing Initiative 26 authorization, after controller audit of the fresh native validation PASS and its evidence. This is a controller workflow decision only: **not** an Ezop signature, **not** an Ezop review, **not** a Laura code/spec review, and no claim that a human reviewed the implementation diff (which does not yet exist). The grant authorizes only the bounded native `bmad-dev-story` implementation described by this artifact; commit, merge, push, deploy, and live actions remain controller-owned closeout steps.
- **G26-MIGRATE — does not apply.** No DDL, no new Alembic revision, no edit to `0020`, no `alembic` invocation in any test this story adds.
- **G26-CAT-SET, G26-UXGATE, G26-SCP-RATIFY, G26-ROUTE-PATH — closed**; none gate this story. G26-LIB (E53) is unrelated.
- **No live-database action of any kind.** Every test runs against the session-scoped throwaway SQLite database built by `conftest.py:_isolated_db` (`init_schema` on a `tempfile.mkdtemp` path, `conftest.py:32-62`). The production database is never opened, read or written by this story at dev time or review time.
- **Live posture, stated so nobody misreads a correct deploy as a broken feature:** the live catalogue carries real tags (Initiative 25's facet taxonomy is seeded and models are tagged), so unlike 49.3 this feature **will** produce visible behaviour change on `.190` the moment it deploys — `q` will start returning strictly **more** models than before for any query that matches a tag name. That is the point of the story, not a defect. It can never return **fewer**: the change is a new disjunct inside an existing `OR`, so the shipped match set is a subset of the new one (AC-2).

## 3. Binding constraints (a violation is a story defect, not a preference)

1. **Exactly one new disjunct, inside the existing `q` `or_()`** (`service.py:365-369`). Not a new `base.where(...)`, not a second `or_()`, not a separate parameter, not a new endpoint.
2. **Membership `IN` (or `EXISTS`) subquery — never a SQL `JOIN` onto the outer base query.** The `SELECT Model` shape must stay unchanged so the shipped `total` → sort → offset/limit → eager-tag → eager-gallery pipeline (`service.py:383-426`) applies untouched. The subquery may internally join `model_tag` to `tag`; that join is *inside* the subquery and is not the forbidden one. See §6 F-4 for why this constraint is load-bearing **here** in a way it was not in 49.3.
3. **Match `lower(Tag.name_pl)` and `lower(Tag.name_en)` only. Do NOT match `Tag.slug`.** Ratified recommendation at `architecture.md:3326` and `epics.md:4485`; §6 F-5 records the second, code-grounded reason.
4. **The disjunct goes inside the `q` block and nowhere else.** It must not touch the soft-delete filter (`service.py:295-296`), the `status` filter, the tag/untagged composition (`:300-339`), the `source` filter, the `category` predicate (`:343-361`) or the `external_url` predicate (`:371-380`). The 42.1 AND-between-groups / OR-within-group semantics and the 49.3 category scope are untouched.
5. **`total` stays `count(*)` over `base.subquery()` computed before pagination** (`service.py:383-384`) and must equal the **distinct** model count. No `DISTINCT` is added; the membership predicate is what makes `DISTINCT` unnecessary.
6. **No new query parameter, no new response field, no new route, no schema change.** `sot/schemas.py` is byte-unchanged. `get_models`'s signature (`router.py:188-202`) is byte-unchanged.
7. **The `q` contract sentence in the OpenAPI description must be corrected in this same commit.** `router.py:177-178` currently asserts `q` **"does NOT search tag names"**. This story makes that statement false. §6 F-2.
8. **No frontend work.** `apps/web/**` is byte-unchanged. `useModels` already sends `q` verbatim (`apps/web/src/modules/catalog/hooks/useModels.ts:15,57`); a server-side semantic widening needs no client change, and none is authorized here.
9. **Strict RED→GREEN** for every behavioural assertion in §4. A test that passes by construction is either restructured until it has a genuine RED, or **explicitly labelled a structural/coverage guard** in both its docstring and §15 — never dressed up as a RED.
10. **No shipped test module may be modified.** New coverage lands in one new module. §6 F-8 records the enumeration behind this prediction and the one honest caveat on it.

## 4. Acceptance Criteria

### The new match branch

**AC-1 — Tag names are matched.** `GET /api/models?q=<s>` returns a model that carries at least one assigned tag whose `name_pl` **or** `name_en` contains `<s>` case-insensitively as a substring, even when the model's own `name_en`, `name_pl` and `slug` contain nothing resembling `<s>`.
*This is a genuine RED.* Measured on this baseline (§6 F-1): a model tagged `{name_en: "Cable", name_pl: "Kabel"}` and named `<prefix> M0` is returned by `q=kabel` **0** times today.

**AC-2 — Union, never subtraction.** The result set is exactly (name/slug-match) ∪ (tag-match). Every model the shipped `q` returns today is still returned. The new branch can only add rows, never remove them — it is a disjunct inside an existing `OR`.

**AC-3 — Each matching model appears exactly once.**
  (a) a model matching on **both** its own name and a tag name appears once;
  (b) a model carrying **N ≥ 2** tags that each match `<s>` appears once;
  (c) both cases hold on the page **and** are counted once in `total`.

**AC-4 — `total` is the distinct model count.** For a query whose whole result set fits on one page, `total == len(items)`. For a multi-page query, `total` is the number of distinct models and is independent of the page window; paging through the whole result set yields each model exactly once, with no repeats across pages.

**AC-5 — Membership predicate, structurally.** The implementation adds no `.join(` to `base` in `list_models`. The `q` block remains a single `base.where(or_(...))` whose new member is `Model.id.in_(select(ModelTag.model_id).join(Tag, ...).where(or_(...)))`. Reviewable by reading the diff; asserted behaviourally by AC-3 + AC-4 and proven load-bearing by the T5 mutation.

**AC-6 — `Tag.slug` is NOT matched.** A query equal to a tag's `slug` that matches neither that tag's `name_pl`/`name_en` nor any model field returns **no** rows for that tag's models. This is a deliberate asymmetry against `GET /api/tags?q=`, which *does* match `Tag.slug` (`service.py:105`); §6 F-5 records why it is correct and why it must not be "fixed".

**AC-7 — Bilingual and null-safe.** A tag with `name_pl IS NULL` still matches on `name_en` (SQL three-valued logic: `NULL OR TRUE` is `TRUE`), and a tag matching only on `name_pl` matches. `Tag.name_pl` is nullable (`_entities.py:53`) while `Tag.name_en` is not (`:52`) — the implementation must not add a `COALESCE`, an `is_not(None)` guard, or a Python-side null filter to "fix" a non-problem.

**AC-8 — Case-insensitive both sides.** Matching is `lower(column) LIKE lower(q)`, mirroring the shipped model-name branch (`service.py:363-369`) and `list_tags` (`:101-109`). `q=KABEL`, `q=kabel` and `q=KaBeL` return identical result sets.

### Composition and non-regression

**AC-9 — `q=None` changes nothing.** With `q` omitted or empty, `list_models` behaves byte-identically to baseline: the `if q:` guard is untouched, so no subquery is built and no SELECT is added.

**AC-10 — Composition with `category` (Story 49.3).** `?category=S&q=<s>` is a pure AND: the tag-aware `q` narrows within the category scope, and the category scope is not widened by a tag match. A model tagged `<s>` but assigned to a different category is absent.

**AC-11 — Composition with `tag_ids` + `tag_match`.** `?tag_ids=…&tag_match=all&q=<s>` and `…&tag_match=any&q=<s>` are pure ANDs between the tag-id predicate and the `q` `or_()`. The tag-name match inside `q` **does not** enter any `tag_match` bucket, does not partition by `Tag.group_id`, and does not alter the groupless-bucket rule. A model that matches `q` only by tag name but fails the `tag_ids` predicate is absent.

**AC-12 — Composition with `untagged=true`.** A zero-tag model can never satisfy the new disjunct, so `?untagged=true&q=<s>` returns exactly the zero-tag models whose own `name_en`/`name_pl`/`slug` match `<s>` — never a tag-only match. The `tag_ids`+`untagged` OR-union case (`service.py:334-335`) composes with `q` as a pure AND and is unchanged.

**AC-13 — Composition with soft-delete.** A soft-deleted model carrying a matching tag is absent from the default page and contributes nothing to `total`. With `include_deleted=true` it reappears, because the shipped row semantics at `service.py:295-296` continue to govern and the new disjunct adds no lifecycle filtering of its own. The subquery deliberately does **not** filter `Model.deleted_at` — the outer query already does, and duplicating it there would be dead code.

**AC-14 — Composition with the remaining shipped filters.** `status`, `source`, `sort` (at least `recent` and `name_asc`), `offset`/`limit`, and `external_url` each compose with the tag-aware `q` as a pure AND with no change to their own semantics. This enumeration together with AC-10…AC-13 is **complete** against the shipped `get_models` signature (`router.py:188-202`: `status`, `tag_ids`, `tag_match`, `untagged`, `source`, `category`, `q`, `external_url`, `sort`, `include_deleted`, `offset`, `limit`) — twelve parameters, all covered.

### NFR26-PERF-1 — query count, not latency

**AC-15 — Constant across page size.** A `q` call that matches tags issues the **same** number of SQL statements at `limit=k` and at `limit=2k`, given both pages are non-empty.

**AC-16 — Constant across matching tag/model fan-out.** Two fixtures — one with few matching tags/models, one with many — chosen so both return the **same non-empty number of rows on the same page**, issue the **same** number of SQL statements. This is the equal-result-count comparison `architecture.md:3328` prescribes; it isolates fan-out from result volume.

**AC-17 — Absolute baseline, measured not guessed.** On a **non-empty** page `list_models` issues **4** SELECTs and on an **empty** page **2**; a tag-aware `q` call must still issue **4** on a non-empty page. Measured on this baseline at create — see §6 F-3 for the verbatim probe output and §5 T0.2 for the re-measure obligation.
  **Mandatory precondition on AC-15/AC-16/AC-17, inherited verbatim from 49.3's AC-23(c):** every compared call MUST return a **non-empty** page of the **same** row count. The eager-tag block (`service.py:393`) and eager-gallery block (`service.py:409`) are each guarded by `if model_ids:`, so an empty page legitimately costs 2 and a populated one 4. A 2-vs-4 delta means the fixture is wrong, **not** the production code. **Removing or weakening the `if model_ids:` guards to make a badly-constructed count test pass is a forbidden regression, not a fix.**

**AC-18 — No N+1 anywhere on the path.** The membership branch adds **zero** round-trips (it is a subquery inside the existing statement, not a pre-query resolving tag ids in Python — contrast the `tag_match=all` branch at `service.py:312-314`, which legitimately does issue one extra SELECT and measures **5**, §6 F-3). The count branch and the eager hydration blocks are untouched.

### Honesty and containment

**AC-19 — The OpenAPI `q` contract is corrected.** `router.py:177-178` no longer claims `q` "does NOT search tag names"; it states the tag-name match, names `name_pl`/`name_en`, states that `tag.slug` is **not** matched, and states that a model matching by both name and tag is returned exactly once. Both `test_every_admin_sot_operation_has_summary` and `..._has_description` (`test_openapi_agent_surface.py:165,175`) continue to pass **byte-unmodified** — they assert non-emptiness, not exact text (§6 F-2).

**AC-20 — Non-regression witnesses pass byte-unmodified.** `tests/test_sot_models_list.py`, `tests/test_sot_models_category_scope.py`, `tests/test_sot_categories.py`, `tests/test_sot_models_detail.py`, `tests/test_sot_tags.py`, `tests/test_sot_tag_groups.py`, `tests/test_sot_auth_boundary.py`, `tests/test_openapi_agent_surface.py`, `tests/test_route_enforcement_gate.py` and `tests/test_orm_migration_parity.py` all pass with **zero** edits. Baseline for the first nine measured at create: **171 passed** (§6 F-8).

**AC-21 — Scope containment.** `git diff --name-only` over the story branch shows exactly the **3** product files in §7 plus the two workflow records. In particular `apps/api/app/modules/sot/schemas.py`, `app/main.py`, `app/core/db/models/**`, `app/core/db/seed.py`, `migrations/**`, `tests/conftest.py`, every shipped `tests/test_*.py`, `apps/web/**`, `workers/**`, `infra/**`, `docs/**`, `pyproject.toml` and `uv.lock` are **byte-unchanged**.

## 5. Tasks / Subtasks — strict RED → GREEN

> **Ordering rule, stated precisely.** Only **T1** precedes the production change, so **T1 is the only genuine RED slice**; its failure output is quoted verbatim into §15. Everything authored after T2's GREEN — that is **T3, T4 and T5 in full** — is green on first run and is a **guard**, never a RED. Each such test says "GUARD, not a RED" in its own docstring and is recorded as a guard in §15. Their load-bearing character is established by the T5.2 mutation battery, which is the only honest proof available once the code exists.
>
> **Where a genuine RED was available but deliberately not taken:** the tag-side assertions of AC-7 (bilingual / null-safe) and AC-8 (case-insensitivity) **would** be red at baseline — validation measured `q='<p> cable'` (tag `name_en` only), `q='<p> kabel'` (tag `name_pl` only) and a `name_pl IS NULL` tag matched via `name_en` all returning **0 items** on `166ef10`. The implementer may therefore either move those assertions into **T1** and claim a real RED, or leave them in T3.4 and label them guards. **What is forbidden is leaving them in T3.4 and writing them up as REDs.**

- [ ] **T0 — Baseline capture (no edits).**
  - [ ] T0.1 Confirm a clean tree at the dev baseline and run the AC-20 witness set, recording the pass count verbatim: `.venv/bin/pytest -q tests/test_sot_models_list.py tests/test_sot_models_category_scope.py tests/test_sot_categories.py tests/test_sot_models_detail.py tests/test_sot_tags.py tests/test_sot_tag_groups.py tests/test_openapi_agent_surface.py tests/test_route_enforcement_gate.py tests/test_sot_auth_boundary.py`. Create measured **171 passed** at `166ef10` (§6 F-8) — a materially different number means something else changed and must be investigated before proceeding.
  - [ ] T0.2 Re-measure, do not trust, the SELECT baselines AC-17/AC-18 depend on: `list_models` = **4** SELECTs on a non-empty page, **2** on an empty page, **5** with `tag_ids`+`tag_match=all`, **4** with `tag_match=any`, **4** with `untagged=true`. Create's verbatim probe output is in §6 F-3.
  - [ ] T0.3 **Bootstrap note, not optional:** this worktree ships **no** `apps/api/.venv`. Create the venv exactly as the repo's own tooling does before any pytest run; do not fall back to a sibling checkout's venv for the *implementation* run (create's read-only probes did, and disclosed it — §6 F-1 — but a dev run must exercise this tree's own code).

- [ ] **T1 — RED: the tag-only match (AC-1).**
  - [ ] T1.1 Author `apps/api/tests/test_sot_models_tag_search.py` with the module-level scaffolding copied from the shipped SoT read modules: the `autouse` admin-cookie fixture (`test_sot_models_category_scope.py:38-49`), the unique `_prefix()` idiom (`:55-56`), the `_count_selects` contextmanager (`:85-98`) and a `_slugs(body)` helper (`:101-102`). Do **not** invent a new auth helper and do **not** add anything to `tests/conftest.py`.
  - [ ] T1.2 Write the AC-1 test: seed a tag `{slug: f"{p}-cable", name_en: "Cable", name_pl: "Kabel"}` and a model whose `slug`/`name_en` contain **no** occurrence of `kabel`/`cable`, assign the tag, then `GET /api/models?q=kabel`. **Observe and quote the failure** — the model is absent and `total` is 0.
  - [ ] T1.3 Write the AC-2 companion in the same run: a second model named `…kabel…` with **no** tags must be present both before and after. Quote the pre-change state (name-match present, tag-match absent).

- [ ] **T2 — GREEN: the disjunct (AC-1, AC-2, AC-5, AC-9).**
  - [ ] T2.1 Add the membership disjunct inside the existing `or_()` at `service.py:365-369`, exactly as §8.1 shows. `ModelTag` and `Tag` are already imported (`service.py:26-27`) — add no import.
  - [ ] T2.2 Extend the `list_models` docstring (`:265-293`) with a `- q:` bullet: substring over `name_en`/`name_pl`/`slug` **plus** assigned-tag `name_pl`/`name_en`, membership subquery, `tag.slug` deliberately excluded. The docstring currently documents every other filter family and omits `q`; leaving it silent after changing `q`'s meaning is the same honesty defect AC-19 fixes on the wire.
  - [ ] T2.3 **GREEN** — quote the pass line.

- [ ] **T3 — Correctness of the union (AC-3, AC-4, AC-6, AC-7, AC-8).**
  - [ ] T3.1 AC-3(a)/(b)/(c): a both-match model, and a model carrying **three** tags that all match, each appear exactly once with `total` counting them once. Authored after T2 → label as **structural guards**, not REDs; their load-bearing character is proven by the T5.2 mutation, which is the only honest proof available at this point.
  - [ ] T3.2 AC-4 — **structural guard, not a RED.** Seed enough matching models to need two pages; assert `total` is stable across `offset` windows and that the union of pages contains each model exactly once. Green by construction once T2 lands; proven load-bearing by T5.2 mutation (a).
  - [ ] T3.3 **RED** for AC-6: assert that `q=<tag-slug>` (a slug whose text appears in **neither** name column nor in any model field) returns nothing. Written *before* T2 would pass trivially, so write it *after* T2 and label it a **negative guard**; then prove it load-bearing in T5.2 mutation (c) by adding `func.lower(Tag.slug).like(like)` to the disjunct and observing this test fail.
  - [ ] T3.4 AC-7: a tag with `name_pl=None` matched via `name_en`; a tag matched only via `name_pl`. AC-8: the same query in three cases returns identical sets. **These are red-capable at baseline (see the ordering rule above): either author them in T1 and quote a real RED, or keep them here and label them guards. Do not write them up as REDs while authoring them after T2.**

- [ ] **T4 — Composition matrix (AC-10 … AC-14) — ALL STRUCTURAL GUARDS, explicitly NOT REDs.** Authored after T2; every one of them is green on first run. §15 and the commit message must not claim a RED for any T4 subtask.
  - [ ] T4.1 AC-10 `category` + tag-aware `q`, both directions (in-scope tag match present; out-of-scope tag match absent).
  - [ ] T4.2 AC-11 `tag_ids`+`tag_match=all` and `…=any`, each ANDed with a tag-name `q`. Reuse the two-group/three-tag fixture shape from `test_sot_models_category_scope.py:255-289` rather than inventing one.
  - [ ] T4.3 AC-12 `untagged=true` + a tag-name-only `q` → empty; `untagged=true` + a model-name `q` → the zero-tag model; the `tag_ids`+`untagged` union case unchanged.
  - [ ] T4.4 AC-13 soft-delete: matching-tag model soft-deleted → absent and uncounted; `include_deleted=true` → present.
  - [ ] T4.5 AC-14 `status`, `source`, `sort` (`recent`, `name_asc`), pagination, `external_url`.
  - [ ] T4.6 AC-9: an explicit `q=None` call returns the same envelope as baseline for the module's own seeded rows.

- [ ] **T5 — Query-count evidence (AC-15 … AC-18) — COVERAGE + MUTATION GUARD, explicitly NOT a RED.**
  - [ ] T5.1 **Coverage guards, expected green on first run.** Authored after T2 landed the code they measure. §15 and the commit message must **not** claim a RED for T5. Three assertions: (a) equal SELECT count at `limit=k` vs `limit=2k`, both pages non-empty and equal-sized (AC-15); (b) equal SELECT count between a low-fan-out fixture (1 matching tag, 1 tag per model) and a high-fan-out fixture (5 matching tags, 3 matching tags per model), sized so **both return the same non-empty row count on the same page** (AC-16); (c) the absolute count is **4** (AC-17).
  - [ ] T5.2 **Mutation sensitivity, labelled.** Prove the guards and the correctness tests are load-bearing:
    1. record `sha256` of `apps/api/app/modules/sot/service.py` **before** touching it;
    2. mutation **(a)** — replace the membership subquery with a SQL `JOIN` onto `base` (the exact forbidden defect of Constraint 2). Run T3 + T5.1 and **observe and quote** the duplicate-row / inflated-`total` failures;
    3. mutation **(b)** — replace the subquery with a Python pre-query that resolves matching model ids and feeds them into `Model.id.in_([...])` (the N+1 shape). Run T5.1 and quote the SELECT-count failure;
    4. mutation **(c)** — add `func.lower(Tag.slug).like(like)` to the disjunct. Run T3.3 and quote the failure — this is what makes AC-6 a real constraint rather than a comment;
    5. revert every mutation, re-run, quote the green;
    6. record `sha256` again and assert it is **byte-identical** to step 1. A differing hash voids the evidence — stop and re-derive.
    Mutations are throwaway measurements and are **never** committed.
  - [ ] T5.3 Fixtures for AC-16 must be constructed so the two cardinalities return **equal, non-empty** row counts on the same page. If they do not, the fixture is wrong; do not touch the `if model_ids:` guards.

- [ ] **T6 — Contract honesty (AC-19).**
  - [ ] T6.1 Rewrite the `q` clause in the `GET /api/models` description (`router.py:177-178`), removing `**does NOT search tag names**` and replacing it with the true contract per AC-19. Change **nothing else** in that description string — the `category` paragraph (`:169-176`), the `external_url` clause (`:178-180`) and the tail are byte-unchanged.
  - [ ] T6.2 Confirm no other in-repo statement about `q` semantics went stale: create's repo-wide sweep found `router.py:178` to be the **only** occurrence (§6 F-2). Re-run the sweep rather than trusting it; historical design docs under `docs/superpowers/specs/` are **out of scope** by the 49.3 F-9 precedent and must not be edited.

- [ ] **T7 — Scope + quality (AC-20, AC-21).**
  - [ ] T7.1 Re-run the T0.1 witness set **unmodified** and quote the pass count.
  - [ ] T7.2 Full API suite: `.venv/bin/pytest -q` in `apps/api`.
  - [ ] T7.3 `.venv/bin/ruff format --check .` and `.venv/bin/ruff check .` in `apps/api`.
  - [ ] T7.4 `git diff --name-only` + `git status --porcelain` proving the §7 file set exactly, and `git diff --name-only` returning empty for every AC-21 byte-unchanged path. `git diff --check` clean.

- [ ] **T8 — Controller-owned closeout. NOT the implementer's to check.**
  - [ ] T8.1 Frozen final `infra/scripts/check-all.sh` 16/16 on the final commit, teed to `.hermes/run-logs/`.
  - [ ] T8.2 Determinism triple (NFR26-DETERMINISM-1) — three consecutive full runs with identical pass counts.
  - [ ] T8.3 Native `bmad-code-review`, then independent `laura-aider-review-diff`; findings loop back to dev-story.
  - [ ] T8.4 One atomic commit, ff-only merge, push, deploy.

## 6. Verify-at-create findings (traced against real code at HEAD `166ef10` this session)

**F-1 — The epic's and architecture's line numbers are STALE; here are the current ones.** `epics.md:4485` and `architecture.md:3316` both cite the `q` clause as `service.py:258-266`, `total` as `:279-280`, `tag_ids` as `:216-254` and `external_url` as `:267-276`. Those were true before Story 49.3 landed. **At `166ef10` the real locations are:** the `q` block `service.py:362-370` with its `or_()` at **`:365-369`**; `total` at **`:383-384`**; the soft-delete filter at **`:295-296`**; the tag/untagged composition at **`:300-339`**; `source` at **`:341-342`**; the 49.3 `category` predicate at **`:343-361`**; `external_url` at **`:371-380`**; the eager-tag block at **`:390-400`** and eager-gallery at **`:402-426`**. An implementer following the sketch's numbers literally would edit the wrong region.
*Disclosure on how create measured things:* this worktree has **no** `apps/api/.venv`, so the read-only probes ran in the sibling checkout `/home/ezop/repos/3d-portal`, which was verified first to be at the **identical** commit `166ef10`, with a clean tree, and `diff -rq --exclude=__pycache__` over `apps/api` reporting **no** content differences (only `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `portal_api.egg-info/`). Nothing tracked was written there; the probes created only a `tempfile.mkdtemp` SQLite database, which was deleted.

**F-2 — There is exactly one in-repo statement that this story falsifies, and it is on the wire.** `router.py:177-178` reads verbatim: `"q" (case-insensitive substring across name_en / name_pl / slug; **does NOT search tag names**)`. A repo-wide sweep for `does NOT search tag names` / `search tag names` / `substring across` across `apps/api/tests`, `apps/web/src`, `apps/web/tests`, `docs/` and `infra/` returned **that single line and nothing else** — no test asserts the description's text, no generated frontend type carries it, no runbook repeats it. The OpenAPI gates (`test_openapi_agent_surface.py:165,175`) assert only that `summary` and `description` are non-empty, so rewriting the sentence is safe. **`docs/operations.md` and `docs/architecture.md` contain no description of `q` semantics at all** — unlike 49.3, this story owes **no** doc-honesty edit outside `router.py`. The historical `docs/superpowers/specs/2026-05-05-portal-ui-rewrite-design.md:377` lists `q` in an old route signature; it is a dated design record and stays untouched (49.3 F-9 precedent).

**F-3 — SELECT baselines, measured, not assumed.** A throwaway-DB probe of the shipped `list_models` at `166ef10` (8 models, 4 tagged, one tag `{name_en: "Cable", name_pl: "Kabel"}`) produced verbatim:
```
q non-empty page limit=4         -> SELECTs=4 items=4 total=8
q non-empty page limit=8         -> SELECTs=4 items=8 total=8
q no match (empty page)          -> SELECTs=2 items=0 total=0
no filters limit=4               -> SELECTs=4 items=4 total=8
tag_ids match=all limit=4        -> SELECTs=5 items=4 total=4
tag_ids match=any limit=4        -> SELECTs=4 items=4 total=4
untagged limit=4                 -> SELECTs=4 items=4 total=4
shipped q='kabel' matches: 0 total: 0
shipped q=<tag slug> matches: 0 total: 0
```
Three things follow. (a) AC-17's target of **4** is a measurement, not a guess, and matches 49.3's independently-measured figure. (b) The `tag_match=all` path costs **5**, because it resolves `Tag.group_id` in Python first (`service.py:312-314`) — an AC-15/AC-16 fixture that varies `tag_match` while comparing counts will fail for a reason that has nothing to do with this story. (c) **The last two lines are the RED for AC-1 and the green-by-construction baseline for AC-6:** today `q='kabel'` finds nothing despite a model carrying a tag named `Kabel`, and `q=<tag slug>` finds nothing either.

**F-4 — Why `IN`-not-`JOIN` is genuinely load-bearing HERE, unlike in 49.3.** Story 49.3's own §6 F-6 conceded honestly that for a single unique category slug a `JOIN` would *not* actually have inflated anything, and left the standing invariant for this story to inherit — `test_sot_models_category_scope.py:158-181` is that inherited guard, and its docstring says so verbatim: *"the guard exists because Story 49.4 adds a tag-name disjunct that DOES fan out under a SQL JOIN"*. That prediction is correct and now becomes concrete: `model_tag` has composite PK `(model_id, tag_id)` (`_entities.py:117-127`), so a model may carry arbitrarily many tags, and a substring query can match many of them at once. Under a `JOIN` a model with three matching tags yields **three** rows in `base`; since `total` is `count(*)` over `base.subquery()` computed **before** pagination (`service.py:383-384`), both the page and the count inflate. AC-3(b) and T5.2 mutation (a) exist precisely to make that failure observable rather than argued.

**F-5 — Why `Tag.slug` must NOT be matched — two reasons, one of them code-grounded.** The ratified reason is that slugs are internal and the requirement names `name_pl`/`name_en` only (`architecture.md:3326`, `prd.md:2248`). The second reason is discovered here and is stronger: the shipped test suite seeds tags whose **slug carries a per-test unique prefix** while the **name does not** — `test_sot_models_category_scope.py:265-267` creates `Tag(slug=f"{p}-g1a", name_en="G1A")`, and `test_sot_models_list.py:51-56` creates tags with `name_en = slug`. Because `conftest.py:_isolated_db` is **session-scoped** (`:32`), rows from every module coexist in one database. Matching `tag.slug` would make a `q=<prefix>` query in one module start returning models tagged by another module's fixtures, turning several exact-set assertions into cross-module coupling. Note the direct consequence for `test_sot_models_list.py:51-56`: those tags have `name_en == slug` (e.g. `tag-4-dragon`), so they *are* reachable by a name match — which is exactly why the enumeration in F-8 had to be done by hand rather than assumed.

**F-6 — `Tag.name_pl` is nullable; do not defend against it.** `_entities.py:52-53`: `name_en: str` (required), `name_pl: str | None = None`. In SQL, `lower(NULL) LIKE '%x%'` evaluates to `NULL`, and inside an `OR` that is absorbed by any `TRUE` and behaves as non-matching otherwise. The shipped `list_tags` already relies on exactly this (`service.py:103-109` ORs over `slug`, `name_en`, `name_pl` with no null guard) and has shipped correctly for two initiatives. Adding `COALESCE`, `is_not(None)` or a Python-side filter would be cargo-cult defensive code and is forbidden by AC-7.

**F-7 — The subquery must not re-filter soft-deletes, and the reason is not stylistic.** The disjunct answers "does this model have a matching tag", not "is this model live". Liveness is already enforced on the outer query (`service.py:295-296`) and, critically, must **remain** overridable by `include_deleted=true`. Adding `Model.deleted_at.is_(None)` inside the subquery would silently make `include_deleted=true` stop returning soft-deleted tag-matched models while still returning soft-deleted name-matched ones — an asymmetry no AC asks for and no reviewer would expect. AC-13 is the executable guard.

**F-8 — Predicted zero shipped-test breakage; the enumeration, the ONE name collision it contains, and the caveat.** Every model-list call site using `q` in `apps/api/tests` was enumerated by hand — there are **five**: `test_sot_models_list.py:135` (`q=articulated`), `test_sot_models_category_scope.py:150` (`q={p}-orphan`), `:179` (`q={p}-shared`), `:250` (`q={p}-keep`), and `test_sot_categories.py:377` (`q={model_slug}`, where the slug is `m-<uuid4 hex[:10]>`). The complete set of literal tag `name_en` values constructed anywhere in the suite is `A`, `Articulated`, `B`, `Del`, `Dragon`, `Dragonfly`, `Egg`, `G1A`, `G1B`, `G2A`, `NoCount`, `PLA`, `Solo`, `T`, `Unused`, `WIP`, `WithCount`, `X`, plus the f-string families (`RACER TAG`, `CUSTOM TAG EN`/`CUSTOM PL`, `Tag <suffix>`, `slug.upper()`) and the `name_en = slug` family from `test_sot_models_list.py:52` (`tag-4-dragon`, `tag-4-only`, …); the only literal `name_pl` values are `Smok` and `Jajko`.

**There IS exactly one collision, and the implementer must not be surprised by it: `q=articulated` (`test_sot_models_list.py:135`) is a case-insensitive substring of the tag `name_en="Articulated"` seeded at `test_sot_tags.py:32` and `:47`.** Because `conftest.py:_isolated_db` is session-scoped, those tag rows coexist in the same database as the models that test queries. The prediction of zero breakage therefore does **not** rest on "no query string matches any tag name" — that statement is false. It rests on two narrower, checked facts:

1. **Neither `Articulated` tag is ever assigned to a model.** The only `ModelTag` rows created in `test_sot_tags.py` attach the `WithCount` tag (`:157`) and the `Del` tag (`:190-191`). The new disjunct matches only models carrying an **assigned** tag, so an unassigned tag name can never widen the model result set.
2. **`test_sot_models_list.py:135` asserts membership and non-membership of two specific model ids, not an exact result set**, so it would survive even a stray extra row.

**Standing hazard, not a resolved one:** fact (1) is a property of fixture data that a future test could change with one `ModelTag(...)` line. If anyone ever assigns an `Articulated`-named tag to a model in `test_sot_tags.py`, `test_sot_models_list.py:135` becomes coupled to it. Do not "fix" that by editing either module — see AC-20. **The witness set measured 171 passed at `166ef10`** (`test_sot_models_list.py`, `test_sot_models_category_scope.py`, `test_sot_categories.py`, `test_sot_models_detail.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_openapi_agent_surface.py`, `test_route_enforcement_gate.py`, `test_sot_auth_boundary.py`). **Honest caveat: this is a prediction derived from static enumeration, not an observed post-change result** — no production code exists yet to run it against. T0.1/T7.1 turn it into evidence. If a witness does break, the correct response is to re-examine whether the disjunct is right, **not** to edit the witness.

**F-9 — The new test module must seed unique prefixes in tag NAMES, not just slugs.** Every shipped SoT read module prefixes **slugs** with `uuid4().hex[:6]` to survive the session-scoped shared DB. This story's module is the first whose assertions depend on tag **names**, so its tag `name_en`/`name_pl` values must carry the same unique prefix — otherwise a name like `"Cable"` could be matched by, or could pollute, another module's fixtures. Use e.g. `name_en=f"{p} Cable"`, `name_pl=f"{p} Kabel"` and query `q=f"{p} kabel"`. **No test may assert a DB-global count.**

**F-10 — `GET /api/tags?q=` is deliberately NOT touched, and the resulting asymmetry is intentional.** `list_tags` matches `slug`, `name_en` and `name_pl` (`service.py:99-110`); after this story `GET /api/models?q=` matches model `name_en`/`name_pl`/`slug` plus tag `name_en`/`name_pl` but **not** tag `slug`. Two endpoints, two questions, two correct answers — and `GET /api/tags?q=` is the ratified suggestion surface for FR26-SEARCH-2 (`architecture.md:3330`, "REUSE, not build"), which E50.3 consumes unchanged. Do not "harmonize" them.

**F-11 — No frontend consequence.** `apps/web/src/modules/catalog/hooks/useModels.ts:15,57` declares `q?: string` and forwards it verbatim as a query param. A server-side widening of `q`'s meaning needs no client change, no new i18n key, no a11y assertion and no visual baseline — no user-visible *surface* is added, only more rows in an existing list. `apps/web/**` stays byte-unchanged and `npm run test:visual` is not required by this story. (It still runs as part of the controller's frozen `check-all` gate.)

**F-12 — This worktree cannot run pytest as delivered.** There is no `apps/api/.venv` here. The 49.2 record already flags worktree-bootstrap/venv defects as a known tooling hazard that previously produced false gate readings. T0.3 makes bootstrapping an explicit first task so the implementer does not silently validate a sibling checkout's code.

## 7. Predicted file changes (exact)

**Total: 3 product files** = **2** production + **1** test. Plus the two workflow records, per this project's convention. The arithmetic is stated once here and every other scope statement in this document (§11, AC-21) and in `sprint-status.yaml` must match it.

**Production code — 2 files, both MODIFY:**

| File | Change |
|---|---|
| `apps/api/app/modules/sot/service.py` | ADD one membership disjunct inside the existing `q` `or_()` at `:365-369`. EXTEND the `list_models` docstring (`:265-293`) with a `- q:` bullet. **No new import** (`ModelTag`, `Tag`, `or_`, `func`, `select` are all already imported at `:12-29`). No other function touched. |
| `apps/api/app/modules/sot/router.py` | MODIFY the `q` clause of the `GET /api/models` `description` string (`:177-178`) per AC-19. **Signature, parameters, pass-through and every other route are byte-unchanged.** |

**Tests — 1 file, NEW:**

| File | Change |
|---|---|
| `apps/api/tests/test_sot_models_tag_search.py` | **NEW.** AC-1…AC-18: the tag-name RED, union semantics, exactly-once + distinct `total`, `tag.slug` negative guard, bilingual/null-safe/case-insensitive matching, the AC-10…AC-14 composition matrix, and the AC-15…AC-18 query-count guards. |

**Workflow records (separate from the product commit):** this story artifact and `_bmad-output/implementation-artifacts/sprint-status.yaml`.

**Asserted byte-unchanged (AC-21):** `apps/api/app/modules/sot/schemas.py`; `app/main.py`; `app/core/db/models/**`; `app/core/db/seed.py`; `apps/api/scripts/**`; `migrations/**`; `tests/conftest.py`; `tests/test_sot_models_list.py`; `tests/test_sot_models_category_scope.py`; `tests/test_sot_categories.py`; `tests/test_sot_models_detail.py`; `tests/test_sot_tags.py`; `tests/test_sot_tag_groups.py`; `tests/test_sot_auth_boundary.py`; `tests/test_sot_schemas.py`; `tests/test_openapi_agent_surface.py`; `tests/test_route_enforcement_gate.py`; `tests/test_orm_migration_parity.py`; `tests/test_browse_category_entity.py`; `tests/test_seed_browse_categories.py`; `apps/web/**`; `workers/**`; `infra/**`; `docs/**`; `AGENTS.md`; `CLAUDE.md`; `pyproject.toml`; `uv.lock`; all `_bmad-output/planning-artifacts/**`.

## 8. Dev Notes

### 8.1 The exact change

`service.py:362-370` today:

```python
if q:
    like = f"%{q.lower()}%"
    base = base.where(
        or_(
            func.lower(Model.name_en).like(like),
            func.lower(Model.name_pl).like(like),
            func.lower(Model.slug).like(like),
        )
    )
```

after:

```python
if q:
    like = f"%{q.lower()}%"
    base = base.where(
        or_(
            func.lower(Model.name_en).like(like),
            func.lower(Model.name_pl).like(like),
            func.lower(Model.slug).like(like),
            # Initiative 26 (Story 49.4, FR26-SEARCH-1) — tag-name membership.
            # IN-subquery, never a JOIN onto `base`: a model carrying three
            # matching tags would appear three times under a join, and `total`
            # is count(*) over base.subquery() computed BEFORE pagination
            # (:383-384), so a join inflates both the page and the count. The
            # join below is INSIDE the subquery (model_tag -> tag) and does not
            # multiply outer rows. `tag.slug` is deliberately NOT matched —
            # slugs are internal (architecture.md:3326) and matching them would
            # couple the session-scoped test DB's per-module slug prefixes.
            # No soft-delete filter here on purpose: liveness is owned by the
            # outer query (:295-296) so `include_deleted=true` keeps working.
            Model.id.in_(
                select(ModelTag.model_id)
                .join(Tag, Tag.id == ModelTag.tag_id)
                .where(
                    or_(
                        func.lower(Tag.name_pl).like(like),
                        func.lower(Tag.name_en).like(like),
                    )
                )
            ),
        )
    )
```

That is the whole production delta besides two docstring/description edits. **Nothing outside the `if q:` block changes.**

### 8.2 Why this costs zero extra round-trips

The disjunct is a correlated-free subquery compiled into the **same** `SELECT` statement, so the statement *count* is unchanged — `4` on a non-empty page (§6 F-3). Contrast the `tag_match=all` branch (`service.py:312-314`), which genuinely issues a separate `SELECT Tag.id, Tag.group_id` before building its predicate and therefore measures `5`. That contrast is the concrete meaning of AC-18: this story must look like the `4` case, not the `5` case.

### 8.3 Testing standards

- **Framework:** pytest, `TestClient`, the session-scoped `_isolated_db` SQLite fixture. No Docker, no network, no live DB.
- **Auth:** the `autouse` admin-cookie fixture from `test_sot_models_category_scope.py:38-49` (`encode_token(..., secret="test-secret-not-real")` + `ACCESS_COOKIE`). Do not invent a new helper; do not edit `conftest.py`.
- **Unique prefixes in slugs *and* tag names** (§6 F-9); per-test-scoped assertions; never a DB-global count.
- **Query counting:** the `_count_selects` contextmanager from `test_sot_models_category_scope.py:85-98`, measured at the **service layer** (call `list_models` directly), not through `TestClient` — auth and session overhead would pollute the count.
- **Equal-result-count comparison** for AC-16, per `architecture.md:3328`. If the two cardinalities do not return the same non-empty row count on the same page, the fixture is wrong.
- Docstrings name the AC they discharge, as every shipped SoT test module does, and guards say "GUARD, not a RED" in the docstring itself.

### 8.4 Anti-patterns — do not do these

- ❌ A SQL `JOIN` onto `base` (Constraint 2; §6 F-4; T5.2 mutation (a) makes it fail loudly).
- ❌ `DISTINCT` on the outer query to "fix" duplicates — it would mask a wrong predicate and change the `total` pipeline.
- ❌ Matching `func.lower(Tag.slug)` (AC-6; §6 F-5).
- ❌ Resolving matching tag ids in Python first and passing a list into `Model.id.in_([...])` — that is the N+1 shape, and T5.2 mutation (b) is built to catch it.
- ❌ Adding `Model.deleted_at.is_(None)` inside the subquery (§6 F-7).
- ❌ `COALESCE` / `is_not(None)` guards around `Tag.name_pl` (§6 F-6).
- ❌ A new query parameter (`q_tags`, `search_tags`, `include_tag_names`) or a match mode. FR26-SEARCH-1 widens `q`; it does not make the widening opt-in.
- ❌ Editing any shipped test module, or `tests/conftest.py`, to accommodate the new match set (§6 F-8).
- ❌ Touching `list_tags` / `GET /api/tags?q=` (§6 F-10).
- ❌ Any `apps/web/**` change, i18n key, or visual baseline regeneration (§6 F-11).

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-1 | Implementer follows the epic/architecture line numbers (`service.py:258-266`) and edits the wrong region — those numbers predate 49.3. | §6 F-1 restates every current line number; §8.1 quotes the exact before/after block. |
| R-2 | A `JOIN` ships because it reads more naturally, silently inflating `total` and duplicating rows. | Constraint 2 + AC-3 + AC-4 + T5.2 mutation (a), which makes the defect an observed, quoted failure rather than an argument. |
| R-3 | Query-count guards pass on a fixture where one side returns an empty page (2 vs 4), and someone "fixes" the `if model_ids:` guards. | AC-17's mandatory precondition, inherited verbatim from 49.3's AC-23(c), plus T5.3 and the explicit "forbidden regression" wording. |
| R-4 | The T5 guards are written up as REDs, overstating the TDD evidence. | T5.1 forbids it in the task text; T5.2's mutation battery is the honest substitute; §15 must record them as guards. |
| R-5 | A shipped test breaks because a `q=` query now matches through a tag name, and the reflex is to edit the shipped test. | §6 F-8 enumerates all five `q=` call sites and every tag name in the suite, names the **one real collision** (`q=articulated` vs the tag `name_en="Articulated"`), and shows the prediction of no breakage rests on those tags never being **assigned** to a model — not on the absence of a name match. T0.1/T7.1 turn the prediction into evidence, and AC-20 forbids the edit. |
| R-6 | `tag.slug` gets added "for symmetry" with `GET /api/tags?q=`. | AC-6 + §6 F-5 + §6 F-10 + T5.2 mutation (c), which proves the negative guard is load-bearing. |
| R-7 | Live behaviour changes visibly on deploy and is read as a regression. | §2 states plainly that `q` will return strictly more rows and can never return fewer, with the subset argument. |
| R-8 | Tests are run against the sibling checkout's venv because this worktree has none, validating code that is not in the branch. | §6 F-12 + T0.3 make bootstrapping an explicit task; create discloses that its own read-only probes did exactly this and why it was safe there (identical commit, verified byte-identical `apps/api`, nothing written). |

## 10. Non-goals (this story ships none of these)

Tag `slug` matching; any change to `GET /api/tags` or `list_tags`; a new suggestion endpoint (`architecture.md:3330` — REUSE, not build); the E50.3 inline suggestion UI; frontend types, hooks, routes, i18n keys, a11y assertions or visual baselines (`50.x`/`51.x`); any new query parameter or match mode on `GET /api/models`; `DISTINCT` on the list query; ranking, relevance scoring, fuzzy matching, stemming or diacritic folding; full-text search infrastructure (`docs/architecture.md:51` — OpenSearch remains a non-adopted option; note the qualified path, the planning-artifact `architecture.md` contains no OpenSearch reference at all); model↔category assignments or admin category governance (`49.5`); any migration, DDL or schema change; any seed change; any live-database, production, push, merge or deploy action.

## 11. Branch and commit atomicity

One story branch off `main`, one commit containing the **3** product files in §7 (2 production + 1 test), plus the two workflow records committed per this project's convention. Suggested branch name per AGENTS.md § Branching: `feat/E49.4-tag-aware-free-text-search`. `check-all.sh` 16/16 must pass on the branch alone. The story is independently mergeable: it depends only on 49.3, already on `main` at `166ef10`, and it adds nothing any other story must wait for.

## 12. Traceability

| AC | Requirement / Decision | Source |
|---|---|---|
| AC-1, AC-2, AC-8 | FR26-SEARCH-1 — tag-aware free-text `q` | `prd.md:2248`; `epics.md:4403,4485`; `architecture.md:3316-3326` |
| AC-3, AC-4, AC-5 | FR26-SEARCH-1 no duplicate rows / no count inflation; membership-not-join | `prd.md:2248`; `architecture.md:3279,3326`; `service.py:383-384` |
| AC-6 | Ratified "do not match `tag.slug`" recommendation | `architecture.md:3326`; `epics.md:4485` |
| AC-7 | `Tag.name_pl` nullable; shipped `list_tags` precedent | `_entities.py:52-53`; `service.py:103-109` |
| AC-9…AC-14 | FR26-SEARCH-1 composition clause; 42.1 tag semantics; 49.3 category scope | `prd.md:2248`; `epics.md:4487`; `service.py:300-361`; `test_sot_models_category_scope.py:232-495` |
| AC-15…AC-18 | NFR26-PERF-1 as query count; 42.2 constant-query no-N+1 precedent | `prd.md:2270`; `epics.md:4423,4489`; `architecture.md:3328`; `test_sot_models_category_scope.py:503-541`; `test_sot_tag_groups.py:90-102,247-263` |
| AC-19 | Doc-honesty-at-deploy discipline (49.3 AC-25 precedent) | `router.py:177-178`; `epics.md:4481` |
| AC-20 | Additive-only invariant; 42.1 semantics preserved | `epics.md:4430`; `architecture.md:3279` |
| AC-21 | Independent-mergeability rule; scope containment | `epics.md:4461`; `sprint-status.yaml:378-384` |
| — (inherited) | 49.3's standing duplicate/total invariant guard, authored *for* this story | `test_sot_models_category_scope.py:158-166` |

## 13. Project structure notes

No new module, package or directory. The production delta lands in the existing `apps/api/app/modules/sot/` pair (`service` / `router`) that every SoT read already uses. One new test module in `apps/api/tests/` following the shipped `test_sot_*.py` naming — deliberately a new module rather than growth of `test_sot_models_list.py`, so that file stays byte-unmodified as the AC-20 non-regression witness (the same reasoning 49.3 applied at its §13). No conflict with the unified structure was found.

## 14. Testing standards summary

`.venv/bin/pytest` from `apps/api` (the venv-relative form `check-all.sh:86-87` uses). Bootstrap the venv first (§6 F-12). Final commands:

```bash
# targeted (new coverage)
cd apps/api && .venv/bin/pytest -q tests/test_sot_models_tag_search.py

# non-regression witnesses (must all pass byte-unmodified)
cd apps/api && .venv/bin/pytest -q \
  tests/test_sot_models_list.py tests/test_sot_models_category_scope.py \
  tests/test_sot_categories.py tests/test_sot_models_detail.py \
  tests/test_sot_tags.py tests/test_sot_tag_groups.py \
  tests/test_sot_auth_boundary.py tests/test_openapi_agent_surface.py \
  tests/test_route_enforcement_gate.py tests/test_orm_migration_parity.py

# full suite + lint
cd apps/api && .venv/bin/pytest -q
cd apps/api && .venv/bin/ruff format --check . && .venv/bin/ruff check .

# controller-owned frozen gate (NOT run by the implementer)
infra/scripts/check-all.sh
```

## 15. Dev Agent Record

*Empty. `bmad-dev-story` has not run. No implementation, no RED, no GREEN, no mutation evidence exists for this story.*

**Read-only baseline probes executed during the create pass** (recorded here so they are not later mistaken for implementation evidence):

1. `pytest -q` over the nine AC-20 witness modules at `166ef10` → **`171 passed, 249 warnings in 24.08s`**.
2. A throwaway-DB `list_models` SELECT-count and match probe → output quoted verbatim in §6 F-3.

Both ran in the sibling checkout `/home/ezop/repos/3d-portal` (verified identical commit and byte-identical `apps/api` content) because this worktree has no venv; see §6 F-1 for the full disclosure. Nothing tracked was modified in either checkout; the probe's SQLite database was a `tempfile.mkdtemp` path and was deleted.

## 16. Validation Record

**Verdict: PASS.** Native `bmad-create-story` action `validate` (menu **VS**), 2026-07-26, fresh independent Claude Opus 5 / native-BMAD session. **No human review of any kind.** No Ezop signature, no Ezop review, no Laura review, no Laura signature. Status moved `ready-for-validation` → `ready-for-dev`. **G26-DEVGO is NOT granted by this pass** — §18.1 stays empty; that remains a separate controller decision. `epic-49` stays `in-progress`.

**Routing and configuration actually resolved.** `bmad-help` executed first from `_bmad/_config/bmad-help.csv`; the `BMad Method,bmad-create-story,Validate Story,VS,…,validate,…,4-implementation,bmad-create-story:create,bmad-dev-story` row is the routing used. Canonical skill confirmed in `_bmad/_config/skill-manifest.csv` line 40: `bmad-create-story`, module `bmm`, path `_bmad/bmm/4-implementation/bmad-create-story/SKILL.md`. **Disclosed mechanism:** this gitignored worktree ships no `.claude/skills/`, so `SKILL.md`, `checklist.md` and `customize.toml` were read from the canonical installed copies under `/home/ezop/repos/3d-portal/.claude/skills/bmad-create-story/`. Customization resolved with `python3 _bmad/scripts/resolve_customization.py --skill <skill-root> --key workflow` → `{"activation_steps_prepend": [], "activation_steps_append": [], "persistent_facts": ["file:{project-root}/**/project-context.md"], "on_complete": ""}`; no team or user override exists. `persistent_facts` loaded (`_bmad-output/project-context.md`, 321 lines). Config from `_bmad/bmm/config.yaml` (`user_name` Ezop, `communication_language` Polish, `document_output_language` English). `checklist.md` executed in full against the artifact.

**Independently executed evidence (create claims were treated as untrusted and re-derived).** All probes were read-only against **throwaway `tempfile.mkdtemp` SQLite databases**, deleted afterwards; no live database, no migration, no tracked file in either checkout was written. Like the create pass, execution used the sibling checkout `/home/ezop/repos/3d-portal` — re-verified this session to be at the **identical** commit `166ef10` with a clean tree — because this worktree has no `apps/api/.venv`.

1. **Every load-bearing source line re-read at baseline and confirmed:** `service.py` `q` block `362-370` with `or_()` at `365-369`; `total` `383-384`; soft-delete `295-296`; tag/untagged composition `300-339`; `source` `341-342`; `category` `343-361`; `external_url` `371-380`; eager-tag `390-400` (`if model_ids:` at `393`); eager-gallery `402-426` (`if model_ids:` at `409`); docstring `265-293`; `tag_match=all` Python pre-query `312-314`; imports `12-13` and `26-27` (`or_`, `func`, `select`, `ModelTag`, `Tag` all present — **the "no new import" prediction is correct**). `router.py:177-178` carries the `does NOT search tag names` sentence verbatim; `get_models` signature `188-202`, twelve filter parameters, and AC-14's composition enumeration is **complete** against it. `_entities.py:52-53` (`name_en: str`, `name_pl: str | None`) and `117-127` (`ModelTag` composite PK) confirmed. `conftest.py:32-62` `_isolated_db` is session-scoped. Test-helper anchors `38-49`, `55-56`, `85-98`, `101-102`, `158-181`, `255-289`, `265-267`, `503-541` confirmed, including the inherited 49.3 guard whose docstring names Story 49.4 verbatim. `useModels.ts:15,57` confirmed. Planning anchors `prd.md:2248,2270`, `architecture.md:3279,3316,3326,3328,3330` and `epics.md:4403,4423,4461,4481,4483,4485,4487,4489,4491` confirmed, including that 49.5 is admin governance renumbered from 49.6 (**no Story 49.6 exists**) and E48 is closed.
2. **Repo-wide sweep re-run:** `does NOT search tag names` occurs in exactly **one** place, `router.py:178`. F-2's containment claim holds.
3. **SELECT baselines re-measured independently, matching §6 F-3 exactly:** non-empty page `limit=4` → **4**; `limit=8` → **4**; empty page → **2**; no filters → **4**; `tag_ids`+`tag_match=all` → **5**; `tag_match=any` → **4**; `untagged` → **4**. AC-17/AC-18 rest on measurement, not assertion.
4. **The AC-1 RED is genuine.** On `166ef10`, a model carrying a tag `{name_en: "<p> Cable", name_pl: "<p> Kabel"}` returns **0 items / total 0** for `q='<p> kabel'` and for `q='<p> cable'`. AC-6's baseline is likewise 0 for `q=<tag slug>`, confirming it is correctly labelled a negative guard rather than a RED.
5. **The §8.1 statement was rebuilt verbatim and executed** — it compiles and runs against SQLModel/SQLAlchemy as written. With a model carrying **three** matching tags, a both-match model, a slug-only-matching tag and a `name_pl IS NULL` tag: `total=4`, 4 rows, **no duplicates**; AC-3(a), AC-3(b), AC-4, AC-6, AC-7 and AC-8 all hold. **T5.2 mutation (a) is executable and produces exactly the predicted failure:** the JOIN form returns **6** rows with `total=6`, the three-tag model appearing three times. Mutations (b) and (c) are likewise expressible against this ORM.
6. **AC-20 witness set re-run unmodified: `171 passed, 249 warnings in 23.50s`** — the create pass's figure is reproduced exactly.

**Defects found and amended in this pass (3).**

- **V-1 (material) — §6 F-8 contained a false supporting claim.** It asserted that "**No** enumerated query string is a substring of **any** enumerated tag name". That is false: `q=articulated` (`test_sot_models_list.py:135`) is a case-insensitive substring of the tag `name_en="Articulated"` seeded at `test_sot_tags.py:32` and `:47`, and the session-scoped fixture puts those rows in the same database. The enumeration had also omitted `Articulated`, `Dragonfly`, `Egg`, `PLA`, `Solo`, `Del`, `WIP`, `NoCount`, `WithCount`, `Unused` and `name_pl="Jajko"`. **The conclusion survives, for a narrower reason that is now stated:** neither `Articulated` tag is ever assigned to a model (`test_sot_tags.py` creates `ModelTag` rows only for the `WithCount` tag at `:157` and the `Del` tag at `:190-191`), and the disjunct matches only assigned tags; additionally that test asserts two specific ids rather than an exact set. F-8 was rewritten with the complete enumeration, the named collision, the true reason, and the standing hazard that one added `ModelTag(...)` line would couple the two modules. R-5's mitigation was corrected to match.
- **V-2 (minor) — §10 mis-cited `architecture.md:51` for OpenSearch.** The planning-artifact `architecture.md` contains **zero** occurrences of "OpenSearch"; its line 51 is `status: 'shipped'`. The real source is `docs/architecture.md:51`, and everywhere else in this story an unqualified `architecture.md` means the planning artifact. Citation qualified.
- **V-3 (minor) — §5's ordering rule contradicted the story's own task order.** The header claimed that within each slice the test is observed failing before the production change exists, yet T3, T4 and T5 are all authored after T2's GREEN. T3.1, T3.3 and T5 were correctly labelled guards; **T3.2, T3.4 and all of T4 were not**, which is exactly the "dressed up as a RED" failure Constraint 9 forbids. The ordering rule was restated precisely (T1 is the only RED slice), T3.2 and T4 are now labelled structural guards, and T3.4 records that AC-7/AC-8's tag-side assertions are genuinely red-capable at baseline — measured 0 items — so the implementer must either move them into T1 and claim a real RED or label them guards.

**Checked and found sound, no amendment required:** the single-disjunct / `IN`-not-`JOIN` / no-`Tag.slug` scope; category scope independent of tags and outside `tag_match`; 42.1 OR-within / AND-across semantics untouched; zero-category models unaffected (guarded by the byte-unmodified `test_sot_models_category_scope.py` witness); `total` as distinct count with no `DISTINCT` added; the AC-15/AC-16/AC-17 equal-non-empty-row-count precondition and the explicit ban on weakening the `if model_ids:` guards; the AC-14 twelve-parameter composition matrix; OpenAPI honesty (both gates assert non-emptiness only, so AC-19's rewrite is safe); the 3-file scope arithmetic, consistent across §7, §11 and AC-21; the branch name against `AGENTS.md:81` § Branching (`feat/E{epic}.{story}-<kebab-slug>`); dependency posture (49.3 done on `main`; not a prerequisite for any other story); and the no-migration / no-frontend / no-live-DB boundaries.

**Next gate:** controller decision on **G26-DEVGO** for this story, then `bmad-dev-story` (DS). This validation authorizes neither.

## 17. Disclosed deviations from the base workflow

1. **The create pass set `ready-for-validation`, not the base template's `ready-for-dev`.** Project precedent (43.1/43.2/43.3/47.5/49.1/49.2/49.3 in `sprint-status.yaml`) plus the `bmad-help.csv` `create → validate` sequencing: `ready-for-dev` is earned at VS, not at CS. Disclosed rather than applied silently. **Discharged 2026-07-26** — the VS pass (§16, verdict PASS) moved the status to `ready-for-dev`, which is where the base template's step 5 would have put it, one workflow step later.
2. **`epic-49` is deliberately left at `in-progress`.** It was flipped at 49.1's dev-story pass; 49.4 is not the epic's first story, so step 1's first-story epic-flip branch does not apply.
3. **Read-only baseline probes ran in a sibling checkout** at the identical commit, because this worktree ships no `apps/api/.venv` and provisioning one would require a network install, which this pass is not authorized to perform. Verified equivalence and the exact non-mutation guarantees are recorded in §6 F-1 and §15.

## 18. Open questions

**None.** Every disposition the epic sketch left to story creation is resolved in this document and stated as a binding constraint rather than a suggestion:

- *"Whether `tag.slug` should also match is left to story-creation with a recommendation of no"* (`architecture.md:3326`) → **RESOLVED: no.** AC-6 + Constraint 3 + §6 F-5, with a second code-grounded reason and a mutation test that makes the negative load-bearing.
- *"Re-derive exact current source paths/lines at baseline rather than trusting old line numbers"* → **DONE.** §6 F-1.
- *NFR26-PERF-1's absolute baseline* → **MEASURED**, not guessed. §6 F-3.

## 18.1 Controller pre-development gate — G26-DEVGO

**GRANTED 2026-07-26 by Laura/controller for Story 49.4.** Preconditions: (1) fresh independent native `bmad-create-story:validate` — **PASS**, §16; (2) controller audit of the literal validator result, clean scoped docs worktree, parsed sprint YAML, and binding Initiative 26 constraints — **complete**. Authority is Ezop's standing Initiative 26 delegation. This is a controller workflow authorization only: **not** an Ezop signature, **not** an Ezop review, **not** a Laura review/sign-off of the story or future diff, and no claim any human reviewed implementation. Scope is limited to native `bmad-dev-story` on `feat/E49.4-tag-aware-free-text-search`; the implementer may not independently review, commit, push, merge, deploy, or touch live data.

## 19. Change Log

| Date | Pass | Author | Outcome |
|---|---|---|---|
| 2026-07-26 | Create (native `bmad-create-story`, action `create`, menu **CS**) | Claude Opus 5 / native BMAD — **no human review** | Story authored at baseline `166ef10`. Status `backlog` → `ready-for-validation`. 21 ACs, 9 task groups, 12 verify-at-create findings, 3 predicted product files. No code, test, planning artifact, config or live DB touched; no commit/push/merge/deploy. G26-DEVGO **not** granted. |
| 2026-07-26 | Validate (native `bmad-create-story`, action `validate`, menu **VS**) | Fresh independent Claude Opus 5 / native BMAD — **no human review** | **PASS.** Status `ready-for-validation` → `ready-for-dev`. Every load-bearing source/path/line claim re-derived at `166ef10`; SELECT baselines (4/2/5) re-measured; AC-1 RED confirmed genuine; the §8.1 statement and T5.2 mutation (a) executed and confirmed executable with the predicted 4-vs-6 duplicate/total inflation; witness set reproduced at **171 passed**. **3 defects amended** — V-1 false enumeration claim in §6 F-8 (real `articulated`/`Articulated` collision; conclusion survives on the unassigned-tag reason, now stated), V-2 mis-cited `architecture.md:51` → `docs/architecture.md:51`, V-3 unlabelled green-first tests in §5 T3.2/T3.4/T4. Details in §16. No code, test, planning artifact, config or live DB touched; no commit/push/merge/deploy. G26-DEVGO **not** granted. |
| 2026-07-26 | Controller gate | Laura/controller — **workflow authorization, not review** | G26-DEVGO **GRANTED** for Story 49.4 under Ezop's standing Initiative 26 delegation after auditing the native validation PASS and scoped tree. Authorizes bounded `bmad-dev-story` only; independent review and all SCM/deploy/live actions remain controller-owned. |

## 20. Code Review Record (native `bmad-code-review`)

*Empty. Not run — this is a create pass.*

## 21. Independent external code review record (Aider)

*Empty. Not run — this is a create pass, and no diff exists to review.*

## 22. Controller final disposition

*Empty.*
