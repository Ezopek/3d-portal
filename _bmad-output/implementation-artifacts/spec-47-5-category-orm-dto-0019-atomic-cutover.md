---
title: 'Story 47.5 — Category API-surface + ORM + DTO + `0019` atomic cutover (absorbs 47.4)'
type: 'refactor'
created: '2026-07-22'
status: 'in-review'
baseline_revision: 'fb8b568db85327ac9b23e8f5512c632afe7cfe2e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/47-5-category-orm-dto-0019-atomic-cutover.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-47-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The legacy single-category taxonomy survives as a zero-code compatibility bridge (FE consumers `AddModelForm` selector + `ModelHero` breadcrumb, `useCategoriesTree` hook/types, `GET /api/categories` + admin category CRUD, `category`/`category_id` DTO fields incl. the anonymous `ShareModelView.category` leak surface, the `Category` ORM entity, and DB schema) even though facet tags (E41–E46) are the sole classification system.

**Approach:** Remove it end-to-end in ONE atomic cutover per the validated story file `47-5-category-orm-dto-0019-atomic-cutover.md` (the canonical, line-verified Code Map — §4 phases (a)→(d), corrections §5): (a) FE consumer migration → (b) FE hook/types deletion → (c) BE API-surface retirement → (d) BE DTO + ORM + forward-only migration `0019_drop_category`. Test-first: the §7 T0 RED gates are authored before any deletion. FE stops reading before BE stops serving, before the ORM stops existing — never the reverse.

## Boundaries & Constraints

**Always:**
- Follow the story file's §4 Code Map (re-verified @ `b75701a`; code unchanged since — `git diff --stat b75701a..HEAD` touches only `_bmad-output/`). Its §5 corrections override the SCP/epics where they conflict.
- Phase order (a)→(b)→(c)→(d) as commit-internal ordering; WIP commits on this branch are allowed for legibility, but the branch's final state must have all four phases complete — the substantive cutover reaches `main` as one indivisible state (atomicity contract, story §3).
- Migration `0019_drop_category`: exactly the story §9 shape — `down_revision = "0018_facet_tags"`, `batch_alter_table` drop of `ix_model_category_id` + `category_id` (NO `drop_constraint` — inline unnamed FK), then `op.drop_table("category")`; `downgrade()` raises `NotImplementedError`. Single Alembic head after.
- T0 RED tests first (story §7): `test_migration_0019.py`, ORM↔migration parity test, share leak-fence negative assert, `AddModelForm.test.tsx`, OpenAPI negative surface test — each RED (or import-failing) against live code before deletions start.
- Extra-field policy is verified fact (story §5.14): create with legacy `category_id` → 201 ignored (`ModelCreate` has no `extra` config); patch → 422 (`ModelPatch` `extra="forbid"`). Assert exactly this.
- en/pl i18n key parity after deletions — enforced by the existing global parity vitest `apps/web/tests/i18n.test.ts` (story §5.13 is wrong that none exists; it runs under `npm run test`) plus the §12 jq key-set diff as evidence.
- Runbook edit (d8): H1 + first non-blank line after it stay byte-for-byte (deploy fingerprint); `test_runbook_openapi_consistency.py` stays green.
- Determinism (NFR25-DETERMINISM-1): 3 consecutive identical pass counts for apps/api pytest, apps/web vitest, workers/render pytest — logged to `.hermes/run-logs/`.
- Residual-symbol greps (story §11) must pass with only the §11 allowed exceptions (slicer material/reason taxonomy, Sentry breadcrumb kwargs, historical migrations/docs, `_bmad-output/**`).
- Visual baselines: regenerate affected specs + create the new `add-model-form.spec.ts` baselines (all 4 projects, pl-PL); read every diff intentionally; `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` lines in the commit message written by the actual reviewing agent signing as itself — never as Michał/Ezop/Laura.
- Bootstrap the fresh worktree first: `uv sync` in `apps/api` + `workers/render`, `npm ci` in `apps/web` (no `.venv`/`node_modules` exist yet).

**Block If:**
- A previously-unknown live consumer of `GET /api/categories`, `category_id`, or `ShareModelView.category` surfaces that is not in story §4 (precondition class has been stale 3×; do not improvise coverage).
- `alembic heads` after `0019` shows more than one head.
- Any contradiction against the story §2 frozen operator decisions (GO scope, rollback model, no-bridge rule) — frozen decisions are not re-openable here.

**Never:**
- Never build any partial/hidden/internal category API bridge, tombstone route, or compatibility shim.
- Never touch slicer/spools material/reason-category code, legacy file-catalog index.json taxonomy, historical migrations `0004`–`0018`, or dated/historical docs (§11 exceptions list).
- Never add replacement classification UI (`ModelHero` breadcrumb, `AddModelForm` selector) — `TagGroupsSection`/`EditTagsSheet` is the classification surface.
- Never edit `_PUBLIC_ROUTES`, the runbook's H1/first non-blank line, or `.190` live data. The pre-deploy backup, ff-merge to `main`, and deploy are controller/operator-owned gates (story §12) — NOT performed by this dev session.
- Never pre-fill or forge reviewer/operator identity anywhere.
- Never ship unrelated changes on this branch.

## I/O & Edge-Case Matrix

Story §6 is the authoritative matrix (16 rows). Binding highlights:

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create model post-cutover | `POST /api/admin/models` w/o `category_id` | 201, untagged model | 422 only for genuinely missing fields |
| Create with legacy field | payload **with** `category_id` | 201, field ignored (no `extra` config) | asserted in test |
| Patch with legacy field | `PATCH .../models/{id}` with `category_id` | 422 (`extra="forbid"`) | asserted in test |
| Category routes | any auth, `GET /api/categories`, admin CRUD | 404/405 — routes gone, no tombstone | none |
| List/detail/share DTOs | `GET /api/models`, `/api/models/{id}`, `/api/share/{token}` | no `category_id`/`category` keys (share = NFR25-LEAKFENCE-1) | negative asserts |
| OpenAPI | `GET /api/openapi.json` | zero `Category*` schemas, zero `category*` props, no dangling `$ref` | T-OAS |
| Fresh DB migrate | `alembic upgrade head` on empty DB | passes `0018`→`0019`; no `category` table, no `model.category_id`, no `ix_model_category_id` | — |
| Downgrade from head | `alembic downgrade -1` | raises `NotImplementedError` | intended |
| ORM↔migration parity | `compare_metadata` on upgraded scratch DB | empty diff | T-PAR |
| Add-model form | `/admin/models/new` | no category select; submit without category; zero `/api/categories` fetch | — |
| Model detail | `/catalog/$id` | no breadcrumb testid; `TagGroupsSection` + `EditTagsSheet` intact; zero `/api/categories` fetch | — |

</intent-contract>

## Code Map

The story file §4 (with §5 corrections) is the canonical, line-verified Code Map — code unchanged since verification. Summary by phase:

- **Phase (a) FE consumers:** `apps/web/src/modules/admin/AddModelForm.tsx` (selector+payload+gate, A1), `apps/web/src/modules/catalog/components/ModelHero.tsx` + `.test.tsx` (breadcrumb, A2/A3), dead filter plumbing `useModels.ts`/`useUpdateModel.ts`/`routes/catalog/index.test.ts` (A4), i18n key deletions en+pl (A5), incidental query-param renames (A6), 11 FE vitest fixture files (A7).
- **Phase (b) FE hook/types:** delete `useCategoriesTree.ts` + test; `lib/api-types.ts` `CategoryNode`/`CategoryTree` + comments (`CategorySummary`/`ModelSummary.category_id`/`ModelDetail.category` fall in (d)).
- **Phase (c) BE API surface:** `sot/router.py` GET /categories, `sot/admin_router.py` category CRUD, `sot/service.py` `list_categories_tree`, `sot/admin_service.py:1303-1479` CRUD+`_would_cycle`, `schemas.py` `CategoryNode`/`CategoryTree`, `admin_schemas.py` `CategoryCreate`/`CategoryPatch`, `core/audit.py` entity type, test deletions/rewrites incl. `test_bootstrap_agent.py` re-point to `POST /api/admin/models` (§5.3), `test_sot_auth_boundary.py` param rewrites.
- **Phase (d) DTO+ORM+migration+share+docs:** d1-d3 DTO/service/route category drops, d4 share leak fence (BE `share/router.py`+`share/models.py`, FE `share-api.ts`/`$token.tsx`/fixtures), d5 ORM `_entities.py` `Category` + `Model.category_id` + re-exports, d6 `migrations/versions/0019_drop_category.py`, d7 seed/docstrings, d8 runbook `docs/agents-add-model-runbook.md` (fingerprint-safe), d9 ~23 fixture-only backend test files + `workers/render/tests/test_worker_sot.py`, d10 assertion-bearing test rewrites, d11 migration-test re-pins (`0004/0005/0009/0012/0014/0018` → `upgrade 0018_facet_tags` where downgrade traverses head), d12 FE visual stubs/fixtures + dev harness.

## Tasks & Acceptance

**Execution:**
- [x] `apps/api`, `workers/render`, `apps/web` -- bootstrap: `uv sync` ×2, `npm ci` -- fresh worktree has no envs; all verification depends on it
- [x] T0 RED gates (story §7): `apps/api/tests/test_migration_0019.py` + ORM↔migration parity test + `test_share_public.py` leak-fence flip + `apps/web/src/modules/admin/AddModelForm.test.tsx` + OpenAPI negative surface test -- authored and observed RED before any deletion -- destructive change lands against pre-proven gates
- [x] Phase (a) -- story §4 A1–A7 -- FE stops reading category data
- [x] Phase (b) -- delete hook+test, `api-types.ts` tree types -- FE types retire
- [x] Phase (c) -- BE routes/services/schemas/audit + test surgery per §4(c) -- BE stops serving; `test_route_enforcement_gate.py` green with zero gate-file edits
- [x] Phase (d) -- §4 d1–d12 in order -- DTO/ORM/migration/share/docs/fixtures/migration-test re-pins
- [x] `apps/web` visual -- regen affected baselines + new `tests/visual/add-model-form.spec.ts` (T-V2, pre-screenshot `toBeVisible()`), read every diff -- story §10
- [x] T-v -- full `infra/scripts/check-all.sh` + 3× determinism runs + §11 residual greps + §12 i18n jq diff + `alembic heads`, all tee'd to `.hermes/run-logs/` -- honest evidence

**Acceptance Criteria:**
- Given the finished branch, when `infra/scripts/check-all.sh` runs, then all stages pass (evidence log in `.hermes/run-logs/`).
- Given 3 consecutive runs each of apps/api pytest, apps/web vitest, workers/render pytest, when pass counts are compared, then all three triples are identical (logged).
- Given `cd apps/api && .venv/bin/alembic heads`, when run, then output is exactly `0019_drop_category (head)`.
- Given the §11 grep battery, when run, then zero disallowed hits (only §11 exceptions remain).
- Given `docs/agents-add-model-runbook.md`, when grepped for `category`, then 0 hits, and the deploy-fingerprint line (H1 + first non-blank line after) is byte-identical to before.
- Given the new visual spec + regenerated baselines, when committed, then every changed/added PNG has a truthful `baseline-reviewed:` line signed by the actual reviewing agent.
- Given story §8's test matrix (new T-M19/T-PAR/T-LF/T-OAS/T-A1/T-V2; updated/deleted lists), when the suites run, then each named assert exists and passes.

### Review Findings

<!-- Native BMAD code review (CR), 2026-07-23, fresh context, reviewer: Claude Opus 4.8 (claude-opus-4-8[1m]) — the reviewing agent signs as itself; no human reviewed this pass. Layers: Blind Hunter + Edge Case Hunter + Acceptance Auditor (parallel subagents) + direct verification. Diff: fb8b568...98246d7. Verdict: REQUEST_CHANGES (narrow repairs; runtime cutover itself verified correct and green). Review was mandated read-only: findings recorded here only — no code/test/migration edits, no status flip, no sprint-status sync, no deferred-work.md write (controller applies those on triage). -->

- [x] [Review][Decision] **Block-If-class residual consumers of `GET /api/categories` outside story §4 (medium)** — `infra/scripts/cutover-smoke.sh:401` scenario 5 probes `/api/categories` expecting 401; post-cutover the route 404s, so the external-probe gate false-FAILs (and its SKIP text tells the operator to curl a dead route). Live ops docs still advertise the route as active surface: `docs/operations.md:112,458,461,605`, `docs/architecture.md:34` (comment-level: `infra/scripts/audit-six-scenarios.sh:673`). The intent contract's Block-If ("previously-unknown live consumer … not in story §4 — do not improvise") makes this an operator escalation, not a reviewer judgment call: either authorize extending the branch with the smoke-script re-point + ops-docs cutover, or explicitly accept them as a pre-deploy follow-up. Precondition-drift class recurs a 4th time (sprint action item `epic: 47`). **RESOLVED (2026-07-23, review repair): controller ruled EXTEND-the-branch — code-grounded cutover drift inside the already operator-authorized full category retirement, not a new product decision (leaving a smoke probe on a deleted route would be a defect). Applied: `cutover-smoke.sh` scenario 5 re-pointed to `/api/tags` (live auth-protected SoT read preserving the exact anonymous-external default-deny 401 purpose; comment documents the re-point; `bash -n` clean, no live probe run); `docs/operations.md` current surfaces cut over (112, 458-461) with the retired route annotated historically, dated 43-categories row count kept and annotated as legacy retired by E47.5 (425), example curl re-pointed to `/api/tags` with a dated-verification note (605-611); `docs/architecture.md` data-flow entity list cut over (34; container table list 26 same class); `audit-six-scenarios.sh:673` High-002 comment clarified then-live/retired-by-E47.5. Sprint action item on the precondition-drift class recurrence stands.**
- [ ] [Review][Patch] **Evidence-provenance gap for the committed tree (medium; NFR25-DETERMINISM-1 / §12 honest-evidence)** — §15 Debug Log References point at `.hermes/run-logs/check-all-20260723_*-e47-5.log` + `determinism-e47-5.log`, but the on-disk logs (bmad-loop run be53 worktree, 06:08–06:21) validate a *divergent uncommitted second-attempt tree* (73 files differ from `98246d7`; its check-all shows 1742/3, not the claimed 1745/3). Committed-tree evidence survives only as collapsed TUI capture (`logs/…dev-1.log:417135` — determinism run 1 = 1745/3; check-all tee started but its artifact was destroyed by the loop reset). Repair: re-run `check-all.sh` + the 3× determinism battery against `98246d7` (rescue branch) and tee fresh logs before merge. Mitigation already in hand: this review independently re-ran all three suites once on `98246d7` — apps/api **1745 passed/3 skipped**, apps/web **785 (136 files)**, workers/render **21** — all matching the commit claims; visual 522/30 confirmed only for the attempt-2 tree.
- [x] [Review][Patch] No test asserts the retired routes now 404 — spec §6 rows "`GET /api/categories` → 404" / "admin CRUD → 404/405" are verified only indirectly (grep + OpenAPI + route-gate). Add a 2-assert negative test [apps/api/tests/test_openapi_agent_surface.py or sibling] (low). **RESOLVED (2026-07-23, review repair): added `test_retired_taxonomy_read_route_is_gone` (GET → 404) + `test_retired_taxonomy_admin_crud_route_is_gone` (PATCH admin CRUD → 404/405) in `test_openapi_agent_surface.py`; literals runtime-assembled per the §11 grep contract; focused run green (file suite passes).**
- [x] [Review][Patch] `AddModelForm.test.tsx:62-63` — both "no selector" asserts are text-based against strings whose i18n keys this same commit deleted; a resurrected selector would render raw keys and still pass. Add a `queryAllByRole("combobox")` length-2 assert (the visual spec already guards this; unit test should too) [apps/web/src/modules/admin/AddModelForm.test.tsx:58-64] (low). **RESOLVED (2026-07-23, review repair): `getAllByRole("combobox")` `toHaveLength(2)` structural assert added alongside the kept text negatives; focused vitest green (3 passed).**
- [x] [Review][Patch] `test_known_entity_types_count_includes_one_new_addition` now guards a count *decrease* (16→15) — name contradicts behavior; rename [apps/api/tests/test_2fa_schema.py:440] (low). **RESOLVED (2026-07-23, review repair): renamed to `test_known_entity_types_count_reflects_taxonomy_retirement`; body/comment unchanged; focused run green.**
- [x] [Review][Patch] Bootstrap-agent smoke: comment "unique slug so this test stays independent" above a hard-coded `agent-bootstrap-smoke` slug; row persists in the session-scoped DB for all later tests. Use a per-run unique suffix [apps/api/tests/test_bootstrap_agent.py:87-91] (low). **RESOLVED (2026-07-23, review repair): slug now `agent-bootstrap-smoke-{uuid4().hex[:8]}` per run; comment rewritten to state the real collision risk (409 in the session-scoped DB); endpoint + assertions preserved; focused run green.**
- [x] [Review][Defer] T-OAS hardening beyond spec letter: also scan `paths` keys for retired routes and all `parameters` for `category_ids`-style survivors [apps/api/tests/test_openapi_agent_surface.py:327-358] — deferred, matches §8 as written
- [x] [Review][Defer] T-PAR blind spots: `compare_metadata` on SQLite won't diff CHECK constraints, server defaults (no `compare_server_default`), or FK `ondelete`; docstring "cannot drift apart" overclaims [apps/api/tests/test_orm_migration_parity.py:1-9] — deferred, known Alembic limitation; still discharges the E41 parity action item
- [x] [Review][Defer] Historical `audit_log.entity_type='category'` rows survive; note in `KNOWN_ENTITY_TYPES` docstring so a future strict-enum/CHECK conversion grandfathers them [apps/api/app/core/audit.py:51-60] — deferred, future-migration caveat
- [x] [Review][Defer] `_round_trip_db` fixture now triplicated (0018/0019/parity) and its `set_main_option("sqlalchemy.url", …)` is decorative (env.py reads settings) — consolidate into a conftest helper [apps/api/tests/test_orm_migration_parity.py:37-55] — deferred, pre-existing pattern
- [x] [Review][Defer] `accessibility-axe.spec.ts:33` `/admin/tags` audits a nonexistent route (real file is `tag-groups.tsx`) — same dead-entry class as the removed `/admin/categories` line — deferred, pre-existing
- [x] [Review][Defer] Review-environment note (not a commit defect): this rescue worktree's `apps/api/.venv`, `workers/render/.venv`, `apps/web/node_modules` are symlinks into `~/repos/3d-portal` @ `fb8b568`; the editable `portal-api` maps `app` → the *pre-cutover* tree, so a naive `workers/render` pytest false-fails 13/21 (`NOT NULL … model.category_id`). Re-reviews must set `PYTHONPATH=<worktree>/apps/api` or `uv sync` fresh — deferred, controller/env hygiene

## Spec Change Log

## Review Triage Log

## Design Notes

- The story file (validated by an independent fresh-context VS pass, §16) IS the detailed plan; this spec deliberately does not duplicate its §4 line inventory — treat story §4/§5 as normative, this spec as the execution contract.
- Correction to story §5.13 found this session: a global en/pl key-parity vitest DOES exist (`apps/web/tests/i18n.test.ts`, runs under `npm run test` — vitest default include covers `tests/`, only `tests/visual/` is excluded). Effect: deleting keys from only one locale fails vitest mechanically; the §12 jq diff stays as belt-and-braces evidence. No other §5 claim is affected.
- Migration precedents: column+inline-FK batch drop `0010:36-38`, `0005:125-126`; whole-table drop `0008:31-32`. Name introspection RESOLVED (architecture.md Decision AV) — do not re-guess, no `drop_constraint`.
- This session ends at the reviewed, gate-green branch. Pre-deploy backup (under `/tmp/3d-portal-deploy.lock`), ff-merge, deploy, and post-deploy smoke are controller/operator-owned (story §12) — out of this spec's execution scope by design, not an omission.

## Verification

**Commands:**
- `mkdir -p .hermes/run-logs && infra/scripts/check-all.sh 2>&1 | tee .hermes/run-logs/check-all-$(date +%Y%m%d_%H%M%S)-e47-5.log` -- expected: all stages green
- `for i in 1 2 3; do (cd apps/api && .venv/bin/pytest -q) 2>&1 | tail -3; done` -- expected: identical counts ×3 (same for `apps/web npm run test` and `workers/render .venv/bin/pytest -q`)
- `(cd apps/api && .venv/bin/alembic heads)` -- expected: exactly `0019_drop_category (head)`
- Story §11 grep battery -- expected: 0 disallowed hits
- `diff <(jq -r 'paths(scalars)|join(".")' apps/web/src/locales/en.json | sort) <(jq -r 'paths(scalars)|join(".")' apps/web/src/locales/pl.json | sort)` -- expected: empty
- `awk '/^# / {after_h1=1; next} after_h1 && NF>0 {print; exit}' docs/agents-add-model-runbook.md | sha256sum` -- expected: matches `infra/.runbook-fingerprint`

**Manual checks (if no CLI):**
- Read every regenerated visual baseline diff; classify stale-baseline vs regression before accepting.
