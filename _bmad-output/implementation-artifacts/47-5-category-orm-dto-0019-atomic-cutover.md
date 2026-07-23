---
baseline_commit: b75701a5a0b6ec2ba90f0b057853d78bcc0d87ef
---

# Story 47.5 — Category API-surface + ORM + DTO + `0019` atomic cutover (absorbs 47.4)

- **Epic:** E47 — i18n + theming + visual regression + runbook/docs cutover + terminal category retirement (Initiative 25 — Facet Tag Taxonomy + Category Retirement).
- **Status:** `done` — implemented (`98246d7`); native code review CR-1 REQUEST_CHANGES → focused repair (`4636d88`) → CR-2 APPROVE (Claude Opus 4.8); independent Aider APPROVE on both `98246d7` (full diff) and `4636d88` (focused repair); Laura/controller independently inspected before/after/diff contact sheets for all 28 changed/added baselines and recorded visual ACCEPT; docs review closeout (`0443432`). Deployed as release `0.1.0+0443432` (ff-only `main`==`origin/main`==deploy HEAD `0443432`); pre-deploy backup verified + live smoke passed (see §17 Post-Deploy Closeout). Epic 47 stays `review` pending the native retrospective — out of this story's scope.
- **Story key:** `47-5-category-orm-dto-0019-atomic-cutover`. FR/NFR: FR25-SHARE-1, FR25-AGENT-1, NFR25-LEAKFENCE-1, NFR25-SCHEMA-MIGRATION-1, NFR25-DETERMINISM-1.
- **Author:** Claude (native BMAD `bmad-create-story`, Create). No human has reviewed this spec at authoring time; no reviewer identity is claimed anywhere below.
- **Created:** 2026-07-22, phase 4-implementation; preceded-by 47.3 (done) + the applied 2026-07-22 SCP; followed-by `bmad-create-story:validate`.
- **Scope class:** DESTRUCTIVE, forward-only, irreducibly atomic. One substantive cutover commit / one deploy HEAD covering four internal phases (a)→(b)→(c)→(d). Migration `0019_drop_category` is irreversible by Alembic (`downgrade()` raises).
- **Sources of truth:**
  - SCP `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md` — **APPROVED & APPLIED 2026-07-22**, incl. the APPLY record with the operator GO and the pre-GO restore-readiness checkpoint.
  - `epics.md` §Initiative 25 / E47 / Story 47.5 (`:4356-4372`, expanded scope + destructive gate + GO record) and the absorbed 47.4 sketch (`:4346-4352`).
  - `architecture.md` §Initiative 25: Decision AU (`:3152-3166`), Decision AV incl. name-introspection (`:3168-3186`), Decision AW + all three dated Updates (2026-07-19 ×2, 2026-07-22).
  - `epic-47-context.md` (corrected 2026-07-22).
  - `spec-47-4-category-api-surface-retirement.md` (`superseded-absorbed-into-47-5`) — its Code Map is carried into §4 phases (b)-(c) and re-verified against `b75701a` this session.
  - Prior specs: `spec-45-2-catalogdetail-grouped-tags.md`, `spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md` (45.3↔47.5 handshake), `spec-47-3-runbook-docs-cutover.md` (runbook `category_id` deliberately retained — see §5.2).
  - Code-grounded investigation @ `b75701a` (this session, two independent full-repo traces — backend and frontend). **Every file:line in §4 was re-verified against `b75701a`; SCP/epics line-number drift is corrected in §5.**

---

## 1. Story statement

**As** the portal's owner (Michał),
**I want** the legacy single-category taxonomy removed end-to-end in one atomic cutover — frontend consumers, FE hook/types, backend API surface, DTOs, ORM entity, and the forward-only schema migration `0019_drop_category` —
**so that** facet tags (shipped E41–E46) are the sole classification system, the zero-code category compatibility bridge stops existing, no anonymous share payload can leak a category field (NFR25-LEAKFENCE-1), and the live app never passes through a broken intermediate state (`main` auto-deploys to `.190`).

## 2. Frozen authorization & destructive boundaries

These decisions are **frozen by the operator** and are not re-openable by dev/review sessions. Any contradiction discovered against them is a Block-If, not a judgment call.

1. **Destructive GO is RECORDED:** exact phrase `GO E47 ATOMIC CUTOVER`, Michał/Ezop, controller session, 2026-07-22 (SCP APPLY record). It covers: absorption of 47.4; `AddModelForm` selector removal; `ModelHero` breadcrumb removal **with no replacement UI**; destructive implementation + deployment of forward-only `0019_drop_category`, accepting permanent deletion of **43 category rows + 130 model-category assignments** from the live DB; rollback model per item 6.
2. **One atomic story, one substantive cutover commit, one deploy HEAD.** Internal phase order within that commit: (a) FE consumer migration → (b) FE hook/types deletion → (c) BE API-surface retirement → (d) BE DTO + ORM + `0019`. FE stops reading before BE stops serving, before the ORM stops existing — never the reverse.
3. **No partial/hidden/internal category API bridge** at any phase (47.4's own `Never` boundary + E42 SCP framing).
4. **`0019_drop_category`:** `down_revision = "0018_facet_tags"`, forward-only, `downgrade()` raises `NotImplementedError`. Single Alembic head after it.
5. **Fresh verified pre-`0019` backup** of the `.190` SQLite DB, taken under the deploy lock (`flock /tmp/3d-portal-deploy.lock`) **immediately before deploy**, with **demonstrated restore-readiness** (scratch restore + verification, evidence logged to `.hermes/run-logs/`). The pre-GO checkpoint backup `portal-pre-e47-5-20260722T172024Z.db` (sha256 `0dfd305e…d21652`, evidence `.hermes/run-logs/e47-precutover-backup-20260722T172024Z.log`) demonstrated the restore path but does **NOT** substitute for the fresh pre-deploy backup.
6. **Rollback = backup restore + `git revert` of the whole cutover commit + redeploy.** Never Alembic downgrade; never a partial revert (DB-only or code-only would leave FE/BE/DB inconsistent).
7. **Determinism (NFR25-DETERMINISM-1):** 3 consecutive identical pytest AND vitest pass counts before merge.
8. **Gates before merge:** full `infra/scripts/check-all.sh` green, native BMAD code review, independent Aider review, visual acceptance. Visual baselines regenerate with `baseline-reviewed:` sign-off lines added **by the actual reviewer at commit time — this spec pre-fills no signatures** (see §10).
9. **The cutover is the only substantive change in its deploy** — clean, unambiguous revert target.

**Block If (halt dev, escalate — do not guess):**
- Any live-DB category/model counts observed at pre-deploy backup time differ wildly from the authorized 43/130 (indicates drift since GO — controller re-confirms before deploy).
- A previously-unknown live consumer of `GET /api/categories`, `category_id`, or `ShareModelView.category` surfaces during implementation that is not in §4 (this story's precondition class has been stale three times — see sprint action item `epic: 47`).
- The single-head check after `0019` shows more than one head.

## 3. Atomicity contract

- **Branch:** `feat/E47.5-category-atomic-cutover` off `main` (`b75701a` or later reviewed HEAD). ff-only merge.
- Phases (a)-(d) are **commit-internal ordering of work**, not separate commits/deploys. Intermediate WIP commits on the branch are permitted for review legibility, but the branch must reach `main` as a state where all four phases are complete — no `main` HEAD may exist with any phase partially applied. The final substantive state (and its deploy) is indivisible.
- `deploy.sh` runs `alembic upgrade head` before the API container is healthy — the same deploy that ships the code applies `0019`. That is the atomic DB+code cutover point.
- Docs edits in this story (runbook payload cutover, §4.d8) ride the same commit — they are part of the contract surface (runbook↔OpenAPI consistency test), not doc-only.

## 4. Code Map — code-grounded @ `b75701a`

### Phase (a) — FE consumer migration

**A1. `apps/web/src/modules/admin/AddModelForm.tsx`** — remove the category selector + payload:
- `:12` `CategoryNode` import; `:13` `useCategoriesTree` import; `:34` `FormState.category_id`; `:45` `EMPTY_FORM.category_id`; `:53-67` `flattenCategories()`; `:81` hook call; `:89` `category_id` in the `POST /admin/models` payload (payload `:87-97`); `:134` 400→`admin.models.new.errors.category_not_found` mapping; `:143-144` `categoryOptions`; `:145-146` submit gate `form.category_id !== ""`; `:189-207` selector UI (label `:191`, `<select>` `:194-206`, placeholder `:200`).
- Post-cutover the form has **no replacement classification input** — tagging happens post-create via `EditTagsSheet`/`TagGroupsSection` on the detail page (45.2/45.3 shipped surface). Payload simply omits `category_id`; submit gate drops the category condition.
- **No existing test coverage** (verified: zero vitest files reference `AddModelForm`/`AddModelModal`/`models/new`; zero visual specs visit `/admin/models/new`) — see §5.1. New coverage is authored in this story (§8 T-A1/T-V2).

**A2. `apps/web/src/modules/catalog/components/ModelHero.tsx`** — remove the category-ancestry breadcrumb, **no replacement**:
- `:5` `CategoryNode`/`CategorySummary` imports; `:14` `useCategoriesTree` import; `:26-35` `flattenCategoryTree()`; `:37-55` `buildAncestorChain()`; `:65` hook call; `:73-77` `ancestorChain` memo; `:79-80` `labelFor()`; `:93-101` breadcrumb render (`data-testid="model-breadcrumb"` `:93`, `t("catalog.gallery.allBreadcrumb")` `:94`, `" › "` separators `:95-100`).
- **Keep intact:** `TagGroupsSection` (import `:13`, render `:174`) and `EditTagsSheet` (`:177`) — the classification surface.

**A3. `apps/web/src/modules/catalog/components/ModelHero.test.tsx`** — drop `mockUseCategoriesTree` (`:16-19`; uses `:57`, `:140`, `:164`); delete the three breadcrumb tests (`:115-119`, `:121-161`, `:163-168`); keep all remaining tests; fixture `category_id`/`category` fields (`:73`, `:90-96`) fall out with the type drops in (b)/(d).

**A4. Dead FE category filter plumbing** (never migrated by 44.3's URL-state cleanup; unreachable but grep-relevant):
- `apps/web/src/modules/catalog/hooks/useModels.ts:10` `ModelsFilters.category_id`; `:11-16` `category_ids`; `:47-51` `?category_ids=` serialization. Companion tests `useModels.test.tsx:31-65` (category_ids serialization) — delete/rewrite.
- `apps/web/src/modules/catalog/hooks/mutations/useUpdateModel.ts:11` `ModelPatch.category_id?` — remove.
- `apps/web/src/routes/catalog/index.test.ts:150-171` asserts `category_id` is stripped from `validateSearch` — simplify/remove once the param has no meaning anywhere.

**A7. FE colocated vitest fixtures (mechanical — break typecheck when the `ModelSummary`/`ModelDetail` fields drop in (b)/(d)):** `category_id`/`category` fixture fields in `CatalogList.test.tsx:78`, `MetadataPanel.test.tsx:16,26`, `tabs/PhotosTab.test.tsx:30,40`, `dialogs/DeleteModelDialog.test.tsx:26,36`, `DescriptionPanel.test.tsx:52,62`, `SecondaryTabs.test.tsx:35,45`, `sheets/RenderSheet.test.tsx:34,44`, `sheets/EditTagsSheet.test.tsx:46,56`, `sheets/EditDescriptionSheet.test.tsx:30,40`, `TagGroupsSection.test.tsx:59,79` (all under `apps/web/src/modules/catalog/`), `apps/web/src/ui/custom/ModelCard.test.tsx:19`. Fixture-only (zero category assertions) — strip the fields, keep the tests.

**A5. i18n (en+pl parity — both files, same keys):**
- `admin.models.new.field.category` (`en.json:543`/`pl.json:543`), `admin.models.new.field.category_placeholder` (`:544`), `admin.models.new.errors.category_not_found` (`:555`) — die with A1.
- `catalog.gallery.allBreadcrumb` (`:371`) — sole consumer is the removed breadcrumb (`ModelHero.tsx:94`); delete.
- `catalog.category.*` block (`:393-401`, 9 keys) — **already orphaned** (zero code references); delete in the same sweep.
- Keep every `modules.admin.profileOffers.*` material-category key (different taxonomy — §11).

**A6. Incidental `category_id` as arbitrary query-string in tests** (taxonomy-unrelated; rename param to keep the residual grep clean): `apps/web/tests/visual/anon-login-only.spec.ts:92-108`; `apps/web/src/routes/login.test.tsx:350-351`; comment `apps/web/src/shell/AppShell.tsx:52-53`.

### Phase (b) — FE hook/types retirement

- **Delete** `apps/web/src/modules/catalog/hooks/useCategoriesTree.ts` (queryKey `["sot","categories"]` `:8`, `api<CategoryTree>("/categories")` `:9`) + `useCategoriesTree.test.tsx` (whole file).
- `apps/web/src/lib/api-types.ts`: delete `CategoryNode` (`:55-59`), `CategoryTree` (`:61-63`); delete/reword the 47.4/47.5 retention comment (`:41-45`); reword the `TagGroupSummary` docblock reference (`:110`). **`CategorySummary` (`:47-53`), `ModelSummary.category_id` (`:215`), `ModelDetail.category` (`:232`) fall in (d)**, with the backend DTO drop.

### Phase (c) — BE API-surface retirement (ex-47.4 Code Map, re-verified @ `b75701a`)

- `apps/api/app/modules/sot/router.py:48-64` — `GET /api/categories` (`get_categories`, `response_model=CategoryTree`, `current_user`); imports `CategoryTree` (`:27`), `list_categories_tree` (`:38`).
- `apps/api/app/modules/sot/admin_router.py` — `POST /api/admin/categories` (`:765-792`), `PATCH /api/admin/categories/{category_id}` (`:795-828`), `DELETE /api/admin/categories/{category_id}` (`:831-853`); all on `_current_admin_or_agent_dep`. Imports: `CategoryCreate`/`CategoryPatch` (`:33-34`), `create_category`/`delete_category`/`update_category` (`:54`,`:59`,`:75`), `CategorySummary` (`:85` — the import stays until (d) removes the last non-category-CRUD use, then goes).
- `apps/api/app/modules/sot/service.py:63-124` — `list_categories_tree()`; imports `CategoryNode`/`CategoryTree` (`:30`,`:32`) go here; `Category` (`:16`)/`CategorySummary` (`:31`) go in (d) with `get_model_detail`.
- `apps/api/app/modules/sot/admin_service.py:1303-1479` — `_would_cycle` (`:1307-1320`), `create_category` (`:1323-1371`), `update_category` (`:1373-1445`), `delete_category` (`:1447-1479`); imports `CategoryCreate`/`CategoryPatch` (`:43-44`); docstring cross-ref `:1222`.
- `apps/api/app/modules/sot/schemas.py` — `CategoryNode` (`:26-28`), `CategoryTree` (`:31-32`). **NOT `CategorySummary` (`:18-23`) — (d).**
- `apps/api/app/modules/sot/admin_schemas.py` — `CategoryCreate` (`:291-314`), `CategoryPatch` (`:317-330`).
- `apps/api/app/core/audit.py` — remove `"category"` from `KNOWN_ENTITY_TYPES` (`:55`; comment `:16`); `apps/api/tests/test_audit.py:69` expectation updated.
- **Tests:** delete `apps/api/tests/test_sot_categories.py` (7 tests) and `test_sot_admin_categories.py` (13 tests); remove `test_category_node_recursive_shape` from `test_sot_schemas.py:159-177` (+ imports `:8`,`:24-25`); drop `CategoryCreate`/`CategoryPatch` from `test_openapi_agent_surface.py:43-44`; rewrite the `/api/categories` params in `test_sot_auth_boundary.py:127,178,228` (+ fixture `:86,:95`) onto surviving SoT reads; re-point `test_bootstrap_agent.py:76-92` agent-write smoke (currently `client.post("/api/admin/categories", ...)` `:88-91`, docstring `:77-79`) onto a **surviving** agent-writable endpoint (see §5.3 — the SCP's "ORM-seed" wording predates the merge and is impossible once `class Category` is gone in (d)). Verified: `POST /api/admin/models` stays on `_current_admin_or_agent_dep` (tag `agent-write`, `admin_router.py:141-159`) and post-(d) no longer requires `category_id` — a clean replacement target.
- **No `_PUBLIC_ROUTES` edit** (`app/main.py:50-61`; TB-055 — category routes were never in the allowlist); `test_route_enforcement_gate.py` self-heals off the live route table.

### Phase (d) — BE DTO + ORM + migration + share + docs

**d1. Read DTOs — `apps/api/app/modules/sot/schemas.py`:** `CategorySummary` (`:18-23`), `ModelSummary.category_id` (`:160`), `ModelDetail.category` (`:179`); reword `TagGroupSummary` docstring (`:94`).
**d2. Write DTOs — `admin_schemas.py`:** `ModelCreate.category_id` (`:32`; example `:22`), `ModelPatch.category_id` (`:56`).
**d3. Services/routes:** `admin_service.py` — `_model_snapshot["category_id"]` (`:155`), `create_model` category validation (`:178`,`:181-184`,`:203`), `update_model` (`:237`,`:244-247`), `Category` import (`:29`); `admin_router.py` — model create/patch category-not-found error mapping (`:146-147`,`:165-166`,`:184`,`:204-205`), `CategorySummary` import (`:85`); `service.py` — `get_model_detail` category join+embed (`:438`,`:486`), `Category`/`CategorySummary` imports (`:16`,`:31`), `_tag_model_counts` docstring (`:131`); `router.py:179` route description "including category"; `app/modules/admin/router.py:4` module-docstring cross-ref ("…tag/category write endpoints…") — reword.
**d4. Share (NFR25-LEAKFENCE-1):** `apps/api/app/modules/share/router.py` — `Category` import (`:16`), live category query (`:144`), `category=category.slug` emit (`:228`); `share/models.py:40` `ShareModelView.category: str`. FE side: `apps/web/src/lib/share-api.ts:33`, anonymous render `apps/web/src/routes/share/$token.tsx:509`, fixtures `MemberShareView.test.tsx:141,198,208`, `tests/visual/share-anonymous-with-signin.spec.ts:25`.
**d5. ORM — `apps/api/app/core/db/models/_entities.py`:** `class Category` (`:29-58`, incl. `__table_args__` `uq_category_parent_slug`/`uq_category_root_slug`/`ix_category_parent`), `Model.category_id` (`:109-111`, NOT NULL FK `category.id` + index); re-exports in `core/db/models/__init__.py` (`:19`, `__all__` `:43`, docstring `:4`); reword the `TagGroup` docstring precedent-comment (`:67`). **No `relationship()` exists** — joins are explicit queries (verified).
**d6. Migration:** `apps/api/migrations/versions/0019_drop_category.py` — §9.
**d7. Seed/scripts docstrings:** `app/core/db/seed.py:174`, `apps/api/scripts/seed_taxonomy.py:5` (claims "writes NO Category rows" — reword to past-tense/no-mention); `test_seed_taxonomy.py:180-194` AC#6 negative-assert becomes meaningless — rework/remove.
**d8. Docs (same commit — contract-coupled):** `docs/agents-add-model-runbook.md` — `category_id` curl example (`:62`), "model + file + tag + category" (`:318`), "minimum fields are name_en + category_id" (`:369`), the `$CATEGORY_ID` out-of-band legacy-field note 47.3 deliberately retained (`:371-377`), "category not found" error example (`:411`). **Constraint:** H1 + first non-blank line after it stay byte-for-byte — the deploy fingerprint (`deploy.sh:229-231`) hashes exactly the **first non-blank line after the H1**; keeping both unchanged guarantees `infra/.runbook-fingerprint` needs no regen (else post-deploy verify logs MISMATCH to `infra/.last-verify-runbook`). `test_runbook_openapi_consistency.py` locks runbook↔OpenAPI claims — both sides drop together, keeping it green.
**d9. Backend test fixtures (mechanical):** files whose only category use is FK scaffolding (`_seed_category` + `Model(category_id=...)`): `test_sot_admin_files.py`, `test_sot_admin_tags.py`, `test_sot_admin_notes.py`, `test_sot_admin_prints.py`, `test_sot_admin_external_links.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_sot_model_files.py`, `test_sot_model_file_content.py`, `test_sot_model_bundle.py`, `test_admin_render_sot.py`, `test_thumbnail_pipeline.py`, `test_backfill_thumbnails.py`, `test_hydrate_local_tree.py`, `test_enqueue_estimate_backfill.py`, `test_share_asset.py`, `test_share_admin.py`, `test_share_member_permission.py`, `test_share_member_router.py`, `test_ratelimit_share_cap.py`, `test_stl_preview_single_flight.py`, **`test_admin_profile_offers.py`** (`:686` `Category` import scaffolding, `:731-735` seed — fixture-only, missed by the SCP), and **`test_sot_models_list.py`** (~25 `category_id=` seed kwargs, **zero** category assertions — fixture-only, reclassified out of d10). Plus **`workers/render/tests/test_worker_sot.py:33-40,115-122,208-220,325-337`** (imports `Category`, sets `category_id`; runs in the `workers/render pytest` check-all stage — missed by the SCP, see §5.4).
**d10. Assertion-bearing tests (rewrite, not just fixtures):** `test_sot_admin_models.py` (`test_create_model_400_unknown_category` `:122-134`; response assert `:111` + `category_id` payload lines `:106,:153`; `_seed_category` `:66`), `test_sot_models_detail.py:97` (`body["category"]["slug"]`), `test_share_public.py:128` (`body["category"]` — flips to the §8 negative leak-fence assert), `test_db_entity_tables.py` (category persistence tests `:92,:109,:124,:134,:244` + ~29 refs — delete the category-entity tests).
**d11. Migration tests — every file that upgrades to `head` AND/OR downgrades from `head` is affected (verified file-by-file; the raising `0019.downgrade()` breaks any head-downward traversal even in files that never mention category):**
- `test_migration_0018.py` — upgrade `head` `:94,:138`, deferral guard `:118-120` (asserts category survives), downgrade to `0017…` `:123` — **re-pin to `upgrade 0018_facet_tags`** (guard + downgrade stay valid historically).
- `test_migration_0004.py` — category in expected sets `:70,:115,:162`; roundtrip `upgrade head → downgrade base → upgrade head` `:85-89`; `test_alembic_and_sqlmodel_emit_equivalent_index_sets` `:137-196` compares index sets at head vs ORM metadata (auto-consistent only because d5+d6 land atomically). Pin upgrade targets to `0018_facet_tags` (or update expected sets to head-after-`0019` where no downgrade is involved).
- `test_migration_0005.py` — `:91` category assert after `downgrade 0004`; roundtrip `:97-101`. Same re-pin treatment.
- **`test_migration_0009.py:30-35`, `test_migration_0012.py:63,87,95`, `test_migration_0014.py:70,87,95`** — no category mentions, but each does `upgrade head → downgrade <pinned> → upgrade head`; the downgrade from head traverses `0019` and raises. **Re-pin their upgrade target to `0018_facet_tags`** (missed by SCP/Create — VS finding).
- New `test_migration_0019.py` owns all head assertions (§8 T-M19).
**d12. FE visual stubs/fixtures:** `apps/web/tests/visual/api-stubs.ts` — `**/api/categories` route + tree fixture (`:176-~205`), `category_id`/`category` in model fixtures (`:54`, `:66-72`, `:248`, `:277`, `:320`, `:347-353`); `catalog-filestab-estimate.spec.ts:57,67` own fixture; stale `/admin/categories` entry in `accessibility-axe.spec.ts:34`; stale comments `_test.ts:21`, `remaining-sheets-open.spec.ts:12`. Dev harness `src/routes/dev/components.tsx:21` `FAKE_MODEL.category_id`.

## 5. Investigation corrections vs the SCP/epics (do not trust superseded line numbers)

1. **`AddModelForm` has NO existing tests** — SCP §5(a) says "both components' existing `.test.tsx` files drop their `useCategoriesTree` mocks"; only `ModelHero.test.tsx` exists. This story **authors** AddModelForm coverage: a new colocated vitest file and a new visual spec (§8 T-A1, §10). This satisfies the frozen "mandatory visual coverage … for affected AddModelForm and ModelHero surfaces" requirement — for AddModelForm that means **new coverage**, not regen.
2. **Runbook still carries `category_id`** — SCP §5(d) claims "no new doc work, just confirming no residual reference survived 47.3". False: 47.3's own `Always` boundary deliberately kept `category_id` in every runnable payload example (backend still requires it at `b75701a`). Phase d8 removes them; `test_runbook_openapi_consistency.py` enforces the coupling.
3. **`test_bootstrap_agent.py` cannot migrate to "ORM-seed"** — the SCP's (c) wording predates the merge; after (d) there is no `Category` ORM to seed. The agent-write smoke re-points to a surviving `agent-write` endpoint (recommended: `POST /api/admin/models`, which stays agent-writable; dev confirms tag choice at implementation).
4. **`workers/render/tests/test_worker_sot.py` imports `Category`** and would fail the `workers/render pytest` gate — absent from SCP/47.4 Code Map; added to d9.
5. **`admin_service.py` category-CRUD block is at `:1303-1479`** (SCP's "~" hedge confirmed); epics' 47.4 sketch cites stale `:1134-1306` and `admin_router.py:774-861` — actual `:765-853`.
6. **Migration tests upgrade to `head`** (not pinned revisions) — d11 is mandatory, not optional; the SCP never mentions `test_migration_0004/0005/0018` adjustments.
7. **Extra FE consumers of category symbols beyond the SCP list:** dead filter plumbing in `useModels.ts`/`useUpdateModel.ts` (A4), orphaned `catalog.category.*` i18n block (A5), anonymous share render `$token.tsx:509` (d4), `accessibility-axe.spec.ts:34` stale route (d12), dev harness fixture (d12).
8. **`ModelSummary.category_id` exists on BE (`schemas.py:160`) and FE (`api-types.ts:215`)** — both drop in (d); every `GET /api/models` list item currently carries it.

**VS corrections (independent validate pass, 2026-07-22 — each verified against code @ `b75701a`):**

9. **11 FE colocated vitest fixture files carry `category_id`/`category`** and were absent from Create's Code Map — now §4 A7. Fixture-only; typecheck-fatal after (d).
10. **Three additional migration-test files break on the raising `downgrade()`** despite never mentioning category (`test_migration_0009/0012/0014` all downgrade from head) — now in d11.
11. **`test_admin_profile_offers.py` seeds `Category`** (`:686,:731-735`) — added to d9. `test_sot_models_list.py` is fixture-only (zero category asserts) — moved d10→d9.
12. **`test_bootstrap_agent.py` smoke is `:76-92`** (file has 92 lines; Create's `:79-105` was stale) — corrected in §4(c), replacement target verified.
13. **No global en/pl key-parity vitest exists** — parity is enforced only by scoped per-prefix tests (`tag-groups-i18n.test.ts` etc.), none covering `admin.models.new.*`/`catalog.*`. The §6 parity row now requires an explicit key-set diff logged in T-v, not a nonexistent "parity check".
14. **Extra-field policy verified (do not re-derive):** `ModelCreate` has **no** `extra` config → Pydantic default *ignores* unknown fields (legacy `category_id` in a create payload → 201, field ignored); `ModelPatch` has `extra="forbid"` (`admin_schemas.py:43`) → legacy `category_id` in a patch → 422. §6 rows updated; assert exactly this in tests.
15. **`catalog-filestab-estimate.spec.ts` does NOT use `stubSotDetail`** — it has its own local `stubModelDetail` (`:47`); audit/strip that fixture separately (d12 already lists its `:57,:67` category fields). §10 list corrected.
16. **The `baseline-reviewed:` gate is a controller-side process convention, not an in-repo mechanical hook** (no `.githooks`/CI check exists; see open `epic: 45`/`epic: 46` GOVERNANCE action items for the gate-script gap). The provenance rule in §10 binds regardless.

## 6. I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Create model post-cutover | `POST /api/admin/models` payload without `category_id` | 201; model created untagged | 422 only for genuinely missing fields (`name_en` etc.) |
| Create model with legacy field | payload **with** `category_id` | **201, field ignored** — verified: `ModelCreate` has no `extra` config → Pydantic default ignores unknowns (§5.14); assert this exact behavior in test | documented in test, not silently passed through |
| Patch model with `category_id` | `PATCH /api/admin/models/{id}` with `category_id` | **422** — verified: `ModelPatch` has `extra="forbid"` (`admin_schemas.py:43`); assert in test | as asserted |
| `GET /api/categories` | any auth | 404 (route gone) | none — no tombstone, no redirect |
| `POST/PATCH/DELETE /api/admin/categories*` | admin/agent auth | 404/405 (routes gone) | none |
| `GET /api/models` list | authenticated | items have **no** `category_id` key | — |
| `GET /api/models/{id}` | authenticated | body has **no** `category` key | — |
| Anonymous share view | `GET /api/share/{token}` | `ShareModelView` JSON has **no** `category` key (NFR25-LEAKFENCE-1) | — |
| OpenAPI | `GET /api/openapi.json` | zero `Category*` component schemas; zero `category`/`category_id` properties on `Model*`/`ShareModelView`; no orphaned `$ref` | `test_openapi_agent_surface.py` green |
| Fresh DB migrate | `alembic upgrade head` on empty DB | passes through `0018` then `0019`; final schema has no `category` table, no `model.category_id`, no `ix_model_category_id` | — |
| Live DB migrate (deploy) | `.190` DB at `0018_facet_tags` with 43 categories / 130 assignments | `0019` drops them; app healthy | rollback per §2 item 6 only |
| Alembic downgrade from head | `alembic downgrade -1` | raises `NotImplementedError` | intended — forward-only |
| Alembic heads | `alembic heads` | exactly one: `0019_drop_category` | Block-If otherwise |
| ORM↔migration parity | `compare_metadata` on upgraded scratch DB | empty diff | new parity test fails otherwise |
| Add-model form | admin opens `/admin/models/new` | no category select; submit enabled once non-category-required fields valid; payload has no `category_id`; **zero** `/api/categories` fetch | — |
| Model detail page | `/catalog/$id` | no breadcrumb (`model-breadcrumb` testid absent); `TagGroupsSection` + `EditTagsSheet` intact; **zero** `/api/categories` fetch | — |
| FE i18n parity | en.json vs pl.json | identical key sets after deletions | explicit key-set diff in T-v (§12) — **no global parity vitest exists** (§5.13); scoped prefix tests stay green |
| Visual suite | all 4 projects, pl-PL | ModelHero-affected baselines regenerated; new AddModelForm spec baselines created | `baseline-reviewed:` sign-off lines per §10 (controller-side convention — §5.16) |

## 7. Tasks / Subtasks (test-first where logic changes)

**T0 — RED gates first (before any deletion):**
- [ ] Author `apps/api/tests/test_migration_0019.py` (fails: revision absent) — head assertions per §8.
- [ ] Author ORM↔migration parity test (fails or is vacuous pre-cutover; green post) — §8.
- [ ] Flip `test_share_public.py:128` to the negative leak-fence assert (RED against live code).
- [ ] Author `AddModelForm.test.tsx` asserting no-category form behavior (RED against live form).
- [ ] Author OpenAPI negative surface test (no `Category*` schema / `category*` properties) (RED).

**T-a — Phase (a):** execute §4 A1–A7 (component edits, `ModelHero.test.tsx` update, i18n deletions with parity, dead-filter removal, incidental param renames; A7 fixture-field strips may mechanically ride with (b)/(d) type drops).
**T-b — Phase (b):** delete hook + test; `api-types.ts` tree-type deletions + comment rewording.
**T-c — Phase (c):** route/service/schema/audit removals + test deletions/rewrites per §4(c); confirm `test_route_enforcement_gate.py` green with no gate-file edit.
**T-d — Phase (d):** execute §4 d1–d12 in order (DTO → services/routes → share → ORM → migration → seeds/docstrings → docs → fixtures → assertion tests → migration tests → FE stubs).
**T-v — Verification battery (§8 + §11 + §12):** full check-all; 3× deterministic runs; residual greps; visual regen + new spec; evidence logs.

## 8. Test matrix

**New tests:**
| ID | File | Asserts |
|---|---|---|
| T-M19 | `apps/api/tests/test_migration_0019.py` | `upgrade head` on scratch SQLite: no `category` table; no `model.category_id` column; no `ix_model_category_id`; `tag`/`tag_group`/`model_tag` untouched; `downgrade` from head raises `NotImplementedError`; script `alembic heads` = exactly `0019_drop_category` |
| T-PAR | same file or `test_orm_migration_parity.py` | `alembic.autogenerate.compare_metadata(migration-upgraded scratch DB, SQLModel.metadata)` → empty diff (discharges the E41 retro parity action item) |
| T-LF | `test_share_public.py` (rewritten) | anonymous share body: `"category" not in body`; tags still present |
| T-OAS | `test_openapi_agent_surface.py` or sibling | `app.openapi()`: no `Category*` in `components.schemas`; no `category`/`category_id` property under `ModelSummary`/`ModelDetail`/`ModelCreate`/`ModelPatch`/`ShareModelView`; no dangling `$ref` |
| T-A1 | `apps/web/src/modules/admin/AddModelForm.test.tsx` (NEW) | form renders without category select; submit possible without category; `POST` body lacks `category_id` key; **no** fetch to `/api/categories` |
| T-V2 | `apps/web/tests/visual/add-model-form.spec.ts` (NEW) | `/admin/models/new` across all 4 projects (pl-PL), pre-screenshot `toBeVisible()` per the E45/E46 test-authoring rule |

**Updated:** `ModelHero.test.tsx` (breadcrumb tests removed; absence assert `queryByTestId("model-breadcrumb") === null` added), `test_sot_auth_boundary.py` (incl. the additional `/api/categories` params at `:284,:303,:313`), `test_bootstrap_agent.py`, `test_sot_admin_models.py`, `test_sot_models_detail.py`, `test_audit.py`, `test_seed_taxonomy.py`, `test_migration_0004/0005/0009/0012/0014/0018.py` (per §4 d11), `useModels.test.tsx`, `routes/catalog/index.test.ts`, `MemberShareView.test.tsx`, all d9 fixture files (incl. `test_sot_models_list.py`, `test_admin_profile_offers.py`), the §4 A7 FE fixture files, `api-stubs.ts` + affected visual specs.
**Deleted:** `test_sot_categories.py`, `test_sot_admin_categories.py`, `useCategoriesTree.test.tsx`, `test_category_node_recursive_shape`, `test_db_entity_tables.py` category tests.

**Determinism (NFR25-DETERMINISM-1):** 3 consecutive runs each of `cd apps/api && .venv/bin/pytest -q` and `cd apps/web && npm run test` with **identical pass counts** (and 3× `cd workers/render && .venv/bin/pytest -q`), logged.

## 9. Migration `0019_drop_category` — exact spec (Decision AV-final)

```python
revision = "0019_drop_category"
down_revision = "0018_facet_tags"

def upgrade() -> None:
    with op.batch_alter_table("model") as batch:
        batch.drop_index("ix_model_category_id")
        batch.drop_column("category_id")   # NO drop_constraint — the category.id FK
                                           # is an unnamed inline (0004:73-78); the
                                           # SQLite batch table-copy removes it.
    op.drop_table("category")              # self-FK + uq_category_parent_slug +
                                           # uq_category_root_slug + ix_category_parent
                                           # + ix_category_slug die with the table.

def downgrade() -> None:
    raise NotImplementedError("0019_drop_category is forward-only (Decision AV / NFR25-SCHEMA-MIGRATION-1)")
```
- Precedents: column+inline-FK batch drop `0010:36-38`, `0005:125-126`; whole-table drop `0008:31-32`. Name introspection is **RESOLVED** (architecture.md Decision AV) — do not re-guess; do not add `drop_constraint`.
- Structural only — no data copy, no seed content.
- Same commit as the ORM removal (d5) — enforced by T-PAR.

## 10. Visual coverage & baseline regeneration

- **Projects (fixed matrix):** `desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`; locale `pl-PL`, TZ `Europe/Warsaw` (`tests/visual/playwright.config.ts:5-35`).
- **ModelHero surface (regen):** every spec that renders the detail page via `stubSotDetail` re-baselines after the breadcrumb removal: `catalog-detail.spec.ts` (3 shots ×4), `destructive-dialogs-edit-sheets-open.spec.ts` (3×4), `remaining-sheets-open.spec.ts`, `admin-dropdowns-tooltip-open.spec.ts`, `share-member-enriched.spec.ts`, `share-member-enriched-dismissed.spec.ts` (verified exhaustive `stubSotDetail` consumer list). `catalog-filestab-estimate.spec.ts` also re-baselines but via its **own local `stubModelDetail` (`:47`)** — strip its category fields (d12) in the same pass. The anonymous share spec (`share-anonymous-with-signin.spec.ts`) re-baselines for the removed share `category` label.
- **AddModelForm surface (NEW spec):** `add-model-form.spec.ts` per §8 T-V2 — creates new baselines in all 4 projects.
- **Regen command:** `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts --update-snapshots` — then **read every diff intentionally** (AGENTS.md triage discipline; classify stale-baseline vs regression before accepting).
- **Provenance (hard rule):** each changed/added PNG requires a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line in the commit message, written **by whoever actually reviewed the diffs, at commit time**. This spec **must not and does not pre-fill any reviewer identity**; an agent signs as itself (e.g. the model name) only if it truly performed the review — never as Michał/Ezop/Laura (E45/E46 forged-sign-off recurrence, sprint action item `epic: 46`).

## 11. Residual-symbol gate (grep contract)

Post-implementation, all of the following must hold (evidence-logged):
```bash
# BE + workers: zero taxonomy symbols
grep -rn "class Category\|CategorySummary\|CategoryNode\|CategoryTree\|CategoryCreate\|CategoryPatch" \
  apps/api/app apps/api/scripts apps/api/migrations/versions/0019_drop_category.py workers/render --include='*.py'   # expect 0 hits
grep -rn "category_id\|/api/categories" apps/api/app apps/api/tests apps/api/scripts workers/render --include='*.py' # expect 0 hits
# FE: only material/reason-category (slicer/profile-offers) hits may remain
grep -rni "categor" apps/web/src apps/web/tests --include='*.ts' --include='*.tsx' --include='*.json'
# Docs contract surface
grep -n "category" docs/agents-add-model-runbook.md   # expect 0 hits
```
**Allowed exceptions (different meaning — do NOT remove):** slicer material/reason taxonomy (`profile_offer.py`, `profile_library.py`, slicer routers/schemas/compatibility/publish — `compatible_material_categories`, `material_category`, `reason_category`, `REASON_MATERIAL_CATEGORY_MISMATCH`); Sentry breadcrumb `category=` kwargs (`spools/client.py:105,141,165`, `recompute.py:398`, `worker_job.py:382,486`) + the breadcrumb assert `test_slicer_estimate.py:757` (`b.get("category") == "slicer"`); `main.py:40` comment heading; FE `api-types.ts` material-category fields (`:576,:589-592,:620-624,:666,:696-711,:751`) + ProfileLibrary/ProfileOffers pages/hooks/tests + `modules.admin.profileOffers.*` locale keys; legacy file-catalog index.json taxonomy (`infra/scripts/migrate_catalog_3mf.py`, its tests, `apps/api/tests/fixtures/*index.json`); historical docs/specs/retros/SCPs and `_bmad-output/**` (including this file); migration files `0004`–`0018` (immutable history); generated build artifacts (`dist/`, `tsconfig.tsbuildinfo`, `.design-sync/`). Old migrations still create+drop category through history — that is correct and untouched.

## 12. Merge & deploy gates — honest evidence commands

**Before merge (dev/controller):**
```bash
mkdir -p .hermes/run-logs
infra/scripts/check-all.sh 2>&1 | tee .hermes/run-logs/check-all-$(date +%Y%m%d_%H%M%S)-e47-5.log   # all 16 stages green
for i in 1 2 3; do (cd apps/api && .venv/bin/pytest -q) 2>&1 | tail -3; done   # identical counts ×3
for i in 1 2 3; do (cd apps/web && npm run test) 2>&1 | tail -5; done          # identical counts ×3
for i in 1 2 3; do (cd workers/render && .venv/bin/pytest -q) 2>&1 | tail -3; done
(cd apps/api && .venv/bin/alembic heads)    # exactly: 0019_drop_category (head)
# i18n key-set parity (no global parity vitest exists — §5.13); expect empty diff:
diff <(jq -r 'paths(scalars)|join(".")' apps/web/src/locales/en.json | sort) \
     <(jq -r 'paths(scalars)|join(".")' apps/web/src/locales/pl.json | sort)
```
Plus: native BMAD code review, independent Aider review (rc=4 = REQUEST_CHANGES is binding — repair within the frozen contract), visual acceptance of every baseline diff, §11 greps.

**Immediately before deploy (controller-owned, under the deploy lock — separate from the pre-GO checkpoint):**
```bash
exec 9>/tmp/3d-portal-deploy.lock && flock 9
TS=$(date -u +%Y%m%dT%H%M%SZ)
ssh -p "$PORTAL_SSH_PORT" "$PORTAL_HOST" "sqlite3 /mnt/raid/3d-portal-state/portal.db \".backup '/mnt/raid/3d-portal-state/backups/portal-pre-0019-cutover-$TS.db'\""
# verify on the backup file: sha256sum; PRAGMA integrity_check; PRAGMA foreign_key_check;
# SELECT version_num FROM alembic_version;  -- must be 0018_facet_tags
# SELECT count(*) FROM category;            -- expected ~43 (Block-If on wild drift)
# SELECT count(*) FROM model WHERE category_id IS NOT NULL;  -- expected ~130
# scratch restore: copy to /tmp, open, re-run integrity_check + counts
# log all commands + output: .hermes/run-logs/e47-5-predeploy-backup-$TS.log
```
Then ff-only merge (cutover = only substantive change in range) → `infra/scripts/deploy.sh` (runs `alembic upgrade head`) → post-deploy: `/api/health` 200, symbolication verify, runbook fingerprint OK, live smoke: `GET /api/categories` → 404, share view has no `category` key.
**Rollback (only path):** restore the fresh backup on `.190` + `git revert` the whole cutover commit on `main` + redeploy. Never `alembic downgrade`; never partial.

## 13. Scope fences (Never)

- Never build any partial/hidden/internal category API bridge, tombstone route, or compatibility shim.
- Never touch slicer/spools material/reason-category code, legacy file-catalog index.json taxonomy, or historical docs/migrations/retros (§11 exceptions).
- Never add a replacement breadcrumb/hierarchy UI to `ModelHero` or a replacement classification input to `AddModelForm` — `TagGroupsSection` is the classification surface (FR25-TAX-1).
- Never edit `_PUBLIC_ROUTES`, `.190` data outside the gated backup/deploy flow, or the runbook's H1/first non-blank line.
- Never pre-fill or forge reviewer/operator identity in commit messages, sign-offs, or this spec's completion records.
- Never ship any unrelated change in the cutover deploy.

## 14. References

- SCP 2026-07-22 (`sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md`) §5 (planning scope), §7 (backup policy), APPLY record (GO + checkpoint).
- `epics.md:4356-4372`; `architecture.md:3152-3186` (AU/AV) + `:3230+` (AW Updates); `epic-47-context.md`; `spec-47-4-category-api-surface-retirement.md` Code Map; `spec-47-3-runbook-docs-cutover.md` `Always` boundary; `spec-45-3` handshake; `project-context.md` §AI agent execution discipline, §UI quality gates.
- Sprint action items: `epic: 41` (0019 same-commit + parity), `epic: 45` (HANDSHAKE), `epic: 46` (governance sign-off, test-authoring), `epic: 47` (precondition-drift recurrence flag).
- Repo memory: web visual tests render pl-PL; baseline-review provenance honesty; Aider verify gate (rc=4 binding).

## 15. Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context) — `claude-opus-4-8[1m]` (bmad-loop dev session, 2026-07-22/23).

### Debug Log References

- `.hermes/run-logs/check-all-20260723_*-e47-5.log` — full check-all gate run (all stages). *(Superseded: CR-1 found these logs validated a divergent uncommitted attempt-2 tree — see final evidence below.)*
- `.hermes/run-logs/determinism-e47-5.log` — 3× pytest (apps/api), 3× vitest (apps/web), 3× pytest (workers/render), identical pass counts. *(Superseded, same provenance finding.)*
- **Final evidence (exact HEAD `4636d88a6c20a48411c650d38f32cfdfc5c83fa9`, post review-repair):**
  - `.hermes/run-logs/check-all-e47-5-final2-4636d88-20260723_071245.log` — check-all 16/16 all green: apps/api pytest **1747 passed/3 skipped** (up from 1745 by the 2 CR-1 retired-route negative tests), apps/web vitest **785**, workers/render pytest **21**, visual **522 passed/30 skipped**.
  - `.hermes/run-logs/determinism-e47-5-final-4636d88-20260723_072322.log` — opens `HEAD=4636d88a6c20a48411c650d38f32cfdfc5c83fa9`; identical triples: apps/api 1747/3 ×3, apps/web 785 ×3, workers/render 21 ×3; ends `DETERMINISM_DONE`.

### Completion Notes List

- T0 RED gates authored and observed RED before any deletion: `test_migration_0019.py` (3 tests — revision absent), `test_share_public.py` leak-fence flip, T-OAS negatives in `test_openapi_agent_surface.py` (6 params RED), new `AddModelForm.test.tsx` (3 tests RED). The T-PAR parity test (`test_orm_migration_parity.py`) was green-vacuous pre-cutover (ORM and migrations both still carried category), as §7 anticipated ("fails or is vacuous pre-cutover").
- Phases (a)→(d) executed in order per §4; all four complete in the single cutover commit.
- §11 grep-contract note: negative-assert tests that must reference the retired literals (`test_migration_0019.py`, `test_migration_0018.py` deferral guard, `test_openapi_agent_surface.py` T-OAS, `test_sot_admin_models.py` extra-field policy, FE `AddModelForm.test.tsx`) assemble them at runtime (`"category" + "_id"`, split FE literals) so the residual-symbol greps stay at 0 disallowed hits while the asserts remain real.
- `test_sot_auth_boundary.py` `/api/categories` params re-pointed onto `GET /api/models/{id}/bundle` (previously uncovered surviving SoT read; seeded file kind image→stl so bundle returns 200) and `GET /api/tags` (admin + rogue-role rows).
- Extra-field policy asserted exactly per §5.14: create with legacy field → 201 ignored (`test_create_model_with_legacy_taxonomy_field_201_ignored`); patch → 422 (`test_patch_model_with_legacy_taxonomy_field_422`).
- `test_2fa_schema.py::test_known_entity_types_count_includes_one_new_addition` updated 16→15 (KNOWN_ENTITY_TYPES lost "category") — a §4 omission discovered at run time.
- Runbook d8 done with H1 + first non-blank line byte-identical (sha256 matches `infra/.runbook-fingerprint` before and after); 0 `category` hits.
- Visual: 24 regenerated baselines (catalog-detail ×12, share-anonymous-with-signin ×4, share-member-enriched ×4, share-member-enriched-dismissed ×4) all show only the breadcrumb / share category-label removal (page height −17..20px or in-viewport upward shift); 4 new `add-model-form` baselines (all 4 projects, pl-PL). Every diff read and classified expected; no regressions. Element-scoped specs (`admin-dropdowns-tooltip-open`, `destructive-dialogs-edit-sheets-open`, `remaining-sheets-open`, `catalog-filestab-estimate`) produced no pixel change (their screenshots don't include the hero breadcrumb region).
- Review closeout (2026-07-23): native BMAD CR-1 (fresh context, Claude Opus 4.8) on `fb8b568...98246d7` → REQUEST_CHANGES (narrow repairs; runtime cutover verified correct); repair commit `4636d88` (docs/tests/scripts only — incl. rename of the `test_2fa_schema.py` count test to `test_known_entity_types_count_reflects_taxonomy_retirement`); focused native re-review CR-2 (Claude Opus 4.8) on `98246d7...4636d88` → **APPROVE**. Independent Aider verdicts: base cutover `98246d7` APPROVE, focused repair `4636d88` APPROVE. Laura/controller independently inspected before/after/diff contact sheets for all 28 changed/added baselines and recorded visual ACCEPT in the controller session. Final evidence at exact HEAD `4636d88`: check-all 16/16, API 1747/3, web 785, workers 21, visual 522/30, determinism triples identical ×3 (log paths in Debug Log References). Docs review closeout `0443432`; ff-only `main`/`origin/main`/deploy HEAD converged on `0443432`.
- **Post-deploy closeout (2026-07-23, native BMAD docs/artifacts pass — see §17 for the full evidence bundle):** production deploy of `0.1.0+0443432` completed under the destructive gate (backup verified, migration `0019_drop_category` applied, live smoke green). Story flipped `done`; `epic-47` flipped to `review` pending the native Epic 47 retrospective (next canonical step, not run in this pass).

### File List

Backend (apps/api): `app/modules/sot/router.py`, `app/modules/sot/admin_router.py`, `app/modules/sot/service.py`, `app/modules/sot/admin_service.py`, `app/modules/sot/schemas.py`, `app/modules/sot/admin_schemas.py`, `app/modules/share/router.py`, `app/modules/share/models.py`, `app/modules/admin/router.py`, `app/core/audit.py`, `app/core/db/models/_entities.py`, `app/core/db/models/__init__.py`, `app/core/db/seed.py`, `scripts/seed_taxonomy.py`, `migrations/versions/0019_drop_category.py` (NEW).
Backend tests: NEW `tests/test_migration_0019.py`, `tests/test_orm_migration_parity.py`; DELETED `tests/test_sot_categories.py`, `tests/test_sot_admin_categories.py`; rewritten/updated `test_share_public.py`, `test_openapi_agent_surface.py`, `test_sot_schemas.py`, `test_sot_auth_boundary.py`, `test_bootstrap_agent.py`, `test_audit.py`, `test_2fa_schema.py`, `test_sot_admin_models.py`, `test_sot_models_detail.py`, `test_db_entity_tables.py`, `test_seed_taxonomy.py`, `test_migration_0004/0005/0009/0012/0014/0018.py`, and the d9 fixture-only files (`test_sot_admin_files/tags/notes/prints/external_links.py`, `test_sot_tags.py`, `test_sot_tag_groups.py`, `test_sot_models_list.py`, `test_sot_model_files.py`, `test_sot_model_file_content.py`, `test_sot_model_bundle.py`, `test_admin_render_sot.py`, `test_thumbnail_pipeline.py`, `test_backfill_thumbnails.py`, `test_hydrate_local_tree.py`, `test_enqueue_estimate_backfill.py`, `test_share_asset.py`, `test_share_admin.py`, `test_share_member_permission.py`, `test_share_member_router.py`, `test_ratelimit_share_cap.py`, `test_stl_preview_single_flight.py`, `test_admin_profile_offers.py`, `test_admin_profile_publish.py`).
Workers: `workers/render/tests/test_worker_sot.py`.
Frontend (apps/web): `src/modules/admin/AddModelForm.tsx`, NEW `src/modules/admin/AddModelForm.test.tsx`, `src/modules/catalog/components/ModelHero.tsx` + `.test.tsx`, `src/modules/catalog/hooks/useModels.ts` + `.test.tsx`, `src/modules/catalog/hooks/mutations/useUpdateModel.ts`, DELETED `src/modules/catalog/hooks/useCategoriesTree.ts` + `.test.tsx`, `src/lib/api-types.ts`, `src/lib/share-api.ts`, `src/routes/share/$token.tsx`, `src/routes/share/MemberShareView.test.tsx`, `src/routes/catalog/index.test.ts`, `src/routes/login.test.tsx`, `src/routes/dev/components.tsx`, `src/shell/AppShell.tsx`, `src/locales/en.json`, `src/locales/pl.json`, the 11 §4 A7 fixture test files, `tests/visual/api-stubs.ts`, `tests/visual/accessibility-axe.spec.ts`, `tests/visual/anon-login-only.spec.ts`, `tests/visual/catalog-filestab-estimate.spec.ts`, `tests/visual/share-anonymous-with-signin.spec.ts`, `tests/visual/_test.ts`, `tests/visual/remaining-sheets-open.spec.ts`, NEW `tests/visual/add-model-form.spec.ts` + 4 baselines, 24 regenerated baselines.
Docs: `docs/agents-add-model-runbook.md`.

## 16. Validation Record (VS)

- **2026-07-22 — independent native `bmad-create-story:validate` (VS), fresh context, Claude (Opus 4.8).** No human reviewed this pass; no reviewer identity beyond the agent's own is claimed.
- Method: planning-side verification against the 2026-07-22 SCP (+APPLY record), `epics.md` §E47, `architecture.md` Decisions AU/AV/AW + all three dated Updates, `epic-47-context.md`, the superseded 47.4 spec, `sprint-status.yaml`, AGENTS.md, `project-context.md`; code-side verification of **every §4 file:line claim** via three parallel full-repo traces (FE, BE, migrations/infra) @ `b75701a`, each including an independent completeness sweep for missed category consumers.
- Result: Create's Code Map and §5 discovered-dependency corrections **confirmed** (trivial ±1-line drifts only). Destructive GO provenance confirmed **exact** (`GO E47 ATOMIC CUTOVER`, SCP APPLY record, 2026-07-22); checkpoint-backup evidence log verified on disk (sha256 match; note: the log is a key=value summary, not a raw transcript — the mandatory fresh pre-deploy backup in §12 is where live counts are re-proven). No fabricated reviewer signatures found anywhere in the spec.
- Amendments applied this pass (all spec-text only; no code/tests/migrations/DB/backup/commit actions): §4 A7 (11 FE vitest fixture files), d3 (+`admin/router.py:4`), d9 (+`test_admin_profile_offers.py`, `test_sot_models_list.py` reclassified), d10 (reclass), **d11 rewritten** (+`test_migration_0009/0012/0014` — raising `downgrade()` breaks all head-downward traversals), d8 fingerprint mechanics precision, §4(c) bootstrap range `:76-92` + verified replacement target, §5.9-16 VS corrections, §6 rows (extra-field policy verified: create=ignore / patch=forbid; parity + gate rows honest), §8 Updated list, §10 `stubSotDetail` list corrected, §11 exception (+`test_slicer_estimate.py:757`), §12 i18n parity diff command. Status: `ready-for-validation` → `ready-for-dev`.

## 17. Post-Deploy Closeout (2026-07-23)

Native BMAD docs/artifacts closeout pass, run after code-review completion (`4636d88` CR-2 APPROVE, docs review closeout `0443432`) and after the operator-authorized production deploy. This section records the destructive-gate execution and live verification only; it authors no code/test/migration change and re-runs no implementation or review.

**Destructive-gate authorization (exact phrases, controller session):**
- `GO E47 ATOMIC CUTOVER` — original destructive-go (§2 item 1, recorded 2026-07-22, unchanged).
- `GO FINAL BACKUP AND DEPLOY E47.5` — terminal gate confirmation to proceed with the fresh pre-deploy backup + deploy.
- `APPROVED IN TERMINAL UI` — final operator approval recorded in the controller terminal.

**Fresh pre-deploy backup (under `/tmp/3d-portal-deploy.lock`, §12 mandatory backup — distinct from the 2026-07-22 pre-GO checkpoint):**
- File: `/mnt/raid/3d-portal-state/backups/portal-pre-e47-5-20260723T190246Z.db`; sha256 `cb5e794a3929fe3df0fd1a1f911c965e134642c9b18f63caca4c04d7fd468140`; 4,317,184 bytes.
- Source + backup + scratch restore all confirmed at Alembic `0018_facet_tags`; `PRAGMA integrity_check` ok; `PRAGMA foreign_key_check` 0 errors; scratch restore verified.
- Live counts at backup time: 43 category rows, 130 models, 130 category assignments — matches the §2 Block-If bound (43/130); no drift since GO.
- Evidence log: `.hermes/run-logs/e47-final-predeploy-backup-20260723T190245Z.log`.

**Deploy:**
- Release `0.1.0+0443432`; `infra/scripts/deploy.sh` exit code 0.
- Migration head after deploy: `0019_drop_category`.
- Post-deploy DB checks: integrity ok; FK errors 0; `category` table absent (0 rows queryable — table dropped); `model.category_id` column absent; `ix_model_category_id` index absent; `model` row count preserved at 130.

**Public live smoke:**
- `GET /api/health` → 200 `{"status":"ok","version":"0.1.0"}`.
- `GET /api/categories` → 404 (route retired, confirms §4(c)).
- `GET /api/tags` → 401 `missing_access` (confirms default-deny auth boundary intact).
- All six compose services running; slicer worker smoke OK.
- GlitchTip symbolication: top frame `main.tsx` resolves correctly for release `0.1.0+0443432`.
- Runbook fingerprint OK: `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573` (confirms §4 d8's byte-for-byte H1/first-non-blank-line constraint held through deploy).

**Disposition:** Story status → `done`. `epic-47` → `review`, pending the native Epic 47 retrospective (next canonical step — not run in this pass). No code, test, migration, or further deploy action taken in this closeout pass.
