# Sprint Change Proposal — E42 Deferred Coupled Cutover (Category Retirement Re-sequencing)

- **Date:** 2026-07-19
- **Author:** Ezop (via native `bmad-correct-course`, APPLY mode)
- **Status:** APPROVED by operator (Ezop) 2026-07-19 — relocation + additive-42.4-now approved; **final destructive-go for 47.5 DEFERRED to its dev-go** (not granted here).
- **Change class:** MODERATE — in-sprint re-sequencing + gap closure inside the already-approved Initiative 25 (no new initiative, no PRD FR change). Backlog reorganization (PO/DEV) with an architecture-doc Update.
- **Trigger doc:** `_bmad-output/implementation-artifacts/42-3-category-endpoint-removal.md` (Story 42.3 create-story `BLOCKED_PROCEDURAL` at the pre-ready dependency-audit gate).
- **Advisory (proposal-only source):** `.hermes/run-logs/e42.3-correct-course-party.md` (native roundtable + options A–E; recommendation §4 "Deferred coupled cutover"; operator decision text §5).
- **Baseline:** `main` @ `a05a3a5`.
- **Supersedes/relocates:** stories **42.3** → **47.4**, **42.5** → **47.5**; assigns TB-053 owner to **47.5**; resolves TB-055.

> This proposal modifies planning/SoT artifacts on approval (`epics.md`, `sprint-status.yaml`, `architecture.md`, `triage-backlog.md`) and marks the blocked 42.3 artifact superseded. It touches **no production or test code**. Destructive implementation of `0019_drop_category` is **not** authorized by this document — see §7.

---

## 1. Issue Summary

Story 42.3 (`category-endpoint removal`) STOPPED at the native `bmad-create-story` pre-ready dependency-audit gate: as decomposed, E42 **conflates two opposite operations into one epic and mis-orders them**.

- **Additive** — stand up the new backend contract: 42.1 model facet filtering (`done`), 42.2 tags/tag-groups read (`done`), 42.4 admin group governance. These land first; nothing depends on them being removed.
- **Destructive** — retire the old category contract: 42.3 (route + schema removal), 42.5 (DTO drop), **plus an orphaned ORM/DB removal** (`class Category` + `Model.category_id` + `0019_drop_category`) that no story owned (TB-053; E41 retro action item #1).

The destructive work was sketched **upstream** of the things it structurally **depends on**. Confirmed, code-grounded couplings (verified 2026-07-19 @ `a05a3a5`, see the advisory §1 and the blocked artifact's Dependency Audit):

1. `CategorySummary` (`schemas.py:18`) is embedded in the **retained** `ModelDetail.category` (`:167`) and mirrored by `ShareModelView.category` → "remove all `Category*` schemas" in 42.3 is impossible without 42.5.
2. `ModelSummary.category_id` **required** (`:148`); `create_model`/`update_model` hard-validate `select(Category)` and import `Category`/`CategoryCreate`/`CategoryPatch` (`admin_service.py:29,42-43,161-167,220-230`) → removing category schemas/ORM breaks the retained write path until 42.5 **and** the ORM drop.
3. `.190` = `main` HEAD, auto-deploy, no skew (AGENTS.md). Frontend (`useCategoriesTree`, `CategoryTreeSidebar`, admin `AddModelForm`) and `hydrate_local_tree.py` still call `GET /api/categories` and consume `category_id` → removing the surface on `main` ahead of the FE/hydrate cutover is a **live 404 / broken catalog browse + broken admin-add + broken hydrate on `.190`** (production regression, not a test failure).
4. `Model.category_id` is **NOT NULL** (`_entities.py:110`). Dropping `ModelCreate.category_id` (42.5) or the column (`0019`) each require the other in the same change, else inserts fail. E41 retro action item #1 mandates `0019_drop_category` land in the **same migration/commit** as the ORM removal.

This is exactly the failure mode E41 retro action item #4 was written to prevent. It recurred because sprint-planning created no ORM-removal owner and numbered the destructive stories ahead of their prerequisites.

## 2. Evidence

- Blocked artifact verdict `BLOCKED_PROCEDURAL`; DoR gate **NOT READY** (5 of 7 open, 3 requiring operator/correct-course decisions).
- Advisory roundtable (PM/SM, Architect, Backend Dev, QA/TEA, FE/deploy) consensus: re-sequence all destructive category work behind the FE + hydrate/runbook cutover; keep the live category API as a zero-code bridge; split into a routes-retirement story + an irreducibly-atomic ORM/DTO/`0019` story; 42.4 proceeds now.
- Live-code spot-checks (advisory §0, all CONFIRMED): `_entities.py:29,109-111`; `sot/schemas.py:18,26,31,148,164,167`; `sot/admin_service.py:29,42-43,138,161-167,220-230`; `scripts/hydrate_local_tree.py:120,176-177,346`; `migrations/versions/0018_facet_tags.py` (**additive-only, shipped** — the destructive drop is NOT in it).
- E41 retro (`epic-41-retro-2026-07-18.md`) §"Decisions formalized at closeout" + Action items → E42: destructive `0019_drop_category` must be coupled to the ORM removal in one commit; `down_revision = "0018_facet_tags"`; forward-only, raising `downgrade`.

## 3. Approved Decision — "Deferred coupled cutover"

Operator approved (2026-07-19) the advisory §4 recommendation:

1. **Relocate** every category-destructive operation from E42 to the terminal cutover epic **E47**, behind the FE + hydrate/runbook consumers, split into:
   - **47.4** — Category **API-surface** retirement (routes + route-only schemas/services), after all `GET /api/categories` consumers are gone. Reversible by code revert.
   - **47.5** — Category **ORM + DTO + `0019`** irreducibly-atomic cutover (ONE commit), after 47.4 + the `45.3` create-form consumer is gone. Forward-only, destructive.
2. **Proceed with additive-only 42.4 now** (admin group governance; no category coupling; needs no SoT edit first).
3. **Close E42 after 42.4** — E42 is re-scoped to the **additive backend contract** (42.1 / 42.2 / 42.4). Old 42.3 / 42.5 IDs are **superseded/relocated** (history preserved, not deleted).
4. **Assign TB-053** (atomic ORM + DTO + `0019` owner) to **47.5**; discharge E41 retro parity + classify action items there.
5. **Fold TB-055** and the `0018`(additive) / `0019`(destructive) **architecture drift** corrections into this pass (Decision AV/AW Update).
6. **Confirm the 45.3 ↔ 47.5 handshake:** the admin create-form category-selector removal lands in the **same `main` HEAD deploy** as the backend `ModelCreate.category_id` drop (single-host deploy makes this consistent).
7. **Defer** the final forward-only destructive approval for 47.5 to its dev-go, gated on a verified pre-`0019` `.190` DB backup. **Destructive-go is NOT recorded as granted here.**

**Zero-code compatibility bridge:** the already-live category API, left untouched, IS the bridge. No deprecation shim is built (minimal-diff / Ponytail-consistent).

## 4. Revised sequence + dependency arrows

```
E42 (corrected: ADDITIVE-only)
  42.1 done ──▶ 42.2 done ──▶ 42.4 admin group governance  ─┐  (E42 CLOSES here)
                                                            │
E43 FE data layer   : 43.1 types ▶ 43.2 hooks ▶ 43.3 url  ◀─┤ (depends on E42 ADDITIVE = 42.1/42.2/42.4 on main)
E44 Catalog browse  : 44.1 ▶ 44.2 ▶ 44.3 CatalogList       ◀─┘ (depends on E43)
E45 Card/detail/edit: 45.1 ▶ 45.2 ▶ 45.3 grouped picker     (depends on E43/E44)
                          └─ 45.3 category-SELECTOR removal is DEFERRED into the cutover (same HEAD as 47.5)
E46 Admin tag/group : depends on 42.4 (governance API) + E43
E47 Cutover (terminal)
  47.1 i18n ▶ 47.2 visual ▶ 47.3 runbook/docs + HYDRATE cutover
  47.4 Category API-surface retirement   ◀── depends on 44.3 + 45.x(no category read) + 47.3(hydrate)
  47.5 Category ORM+DTO+0019 ATOMIC cutover ◀── depends on 47.4 + 45.3(create-form) ; ONE commit ; same main HEAD deploy as 45.3 selector removal
                                              └─ closes TB-053; discharges E41 parity + classify actions
```

Sequence for execution: **42.4 → E43 → E44 → E45 → E46 → 47.1/47.2/47.3 → 47.4 → 47.5.**

## 5. Scope per relocated story (planning-level; NOT yet an implementation-ready story)

**47.4 — Category API-surface retirement** (after all `GET /api/categories` consumers gone; reversible by code revert):
- Routes: `GET /api/categories` (`sot/router.py:48-64`); admin `POST/PATCH/DELETE /api/admin/categories` (`admin_router.py:774-861`).
- Service: `create/update/delete_category` + `_would_cycle` (`admin_service.py:1134-1306`); `list_categories_tree` (`service.py:63-124`).
- Schemas: `CategoryNode`, `CategoryTree`, `CategoryCreate`, `CategoryPatch` **only** — NOT `CategorySummary` (still embedded in retained `ModelDetail`).
- Tests: delete `test_sot_categories.py`, `test_sot_admin_categories.py`; update `test_sot_auth_boundary.py` category assertions; migrate `test_bootstrap_agent.py:79-95` off the admin-CRUD POST to ORM-seed.
- Route-enforcement gate: **no `_PUBLIC_ROUTES` edit** (category routes are authenticated, never in the allowlist — TB-055); the enumeration test self-heals off the live route table.
- **Keeps alive:** `CategorySummary`, `ModelCreate/Patch/Summary/Detail.category(_id)`, `create_model`/`update_model` Category validation, `class Category`, `Model.category_id`. `main` stays green.

**47.5 — Category ORM + DTO + `0019` atomic cutover** (ONE commit; after 47.4 + create-form consumer gone; DESTRUCTIVE, forward-only):
- Schemas/DTOs: drop `ModelCreate.category_id` + `ModelPatch.category_id`; drop `ModelSummary.category_id`; drop `ModelDetail.category` + `CategorySummary`; drop `ShareModelView.category` (live projection).
- Service: remove `Category` validation + `Category*` imports from `create_model`/`update_model`.
- ORM: remove `class Category` + `Model.category_id` + FK + `ix_model_category_id`.
- Migration: **`0019_drop_category`** — `down_revision = "0018_facet_tags"`, forward-only, `downgrade()` raises `NotImplementedError`; `batch_alter_table("model")` drop index + column (no `drop_constraint` — the `category.id` FK is an unnamed inline, per Decision AV), then `op.drop_table("category")`.
- Tests: ORM↔migration **parity test** (`compare_metadata`) — discharges E41 action item #2; NFR25-LEAKFENCE-1 negative share-DTO test; fix ~25 fixtures that ORM-seed `Model(category_id=...)`.
- FE coordination (same `main` HEAD deploy): `45.3` admin create-form category-selector removal.
- Docs/scripts: `hydrate_local_tree.py` category path-map removal (coordinated w/ 47.3); runbook/ops/overview owned by 47.3.
- **Closes TB-053.**

## 6. Detailed change proposals (this pass)

- **`epics.md` §Initiative 25:** E42 goal → additive backend contract, closes after 42.4; 42.3/42.5 marked SUPERSEDED/RELOCATED (history preserved) → 47.4/47.5; E43 "depends on E42 on `main`" → "depends on E42 **additive** (42.1/42.2/42.4)"; E47 gains 47.4 + 47.5 with dependency arrows incl. the 45.3↔47.5 same-HEAD handshake.
- **`sprint-status.yaml`:** 42.3/42.5 keys kept as `backlog` with `superseded by 47.4/47.5` comments; new `47-4-category-api-surface-retirement` + `47-5-category-orm-dto-0019-atomic-cutover` = `backlog`; 42.4 stays `backlog` (next E42 story); E41 `action_items` owners flipped to concrete `47.5` (items #1, #2) and `47.4` note where routes-scoped; epic-42 comment records close-after-42.4. No enum invented; no code story marked done/ready.
- **`architecture.md` Decision AV/AW Update:** record shipped `0018_facet_tags` as **additive-only** and `0019_drop_category` as the **terminal, forward-only** destructive migration owned by 47.5; correct TB-055 §3211 auth prose (SoT reads are authenticated `current_user`, outside `_PUBLIC_ROUTES`; categories never in the allowlist; removal needs no allowlist edit); record the live category API as a **zero-code compatibility bridge** + terminal cutover constraints (backup-first, isolated deploy, single head, 45.3 handshake).
- **`triage-backlog.md`:** TB-053 → `promoted` (owner `47.5`; not `done` until delivery); TB-055 → `resolved` by the architecture correction in this pass (exact artifact reference).
- **`42-3-category-endpoint-removal.md`:** header marked SUPERSEDED/RELOCATED by this SCP; dependency audit preserved; pointer to 47.4 (routes) + 47.5 (ORM/DTO/`0019`).

## 7. Destructive gate — DEFERRED (explicit approval record)

- Operator **approved** (2026-07-19): relocation of category-destructive work to 47.4/47.5, additive **42.4 to proceed now**, close E42 after 42.4, TB-053 owner = 47.5, TB-055 + `0018/0019` architecture drift folded into this pass, 45.3↔47.5 same-HEAD handshake.
- Operator **DEFERRED** the final forward-only destructive go for **47.5** to its dev-go. **This SCP does NOT record destructive-go as granted.**
- Before any 47.5 dev-go / deploy, the operator must record an explicit destructive-go acknowledging: (1) `0019` is forward-only, `downgrade()` raises — irreversible by Alembic; (2) category rows + per-model assignment are permanently lost by design (already accepted in the 2026-07-17 SCP — models start untagged); (3) rollback = **verified pre-`0019` `.190` DB backup restore + `git revert` of the 47.5 commit + redeploy**; (4) a verified pre-`0019` DB backup exists on `.190`, taken under the deploy lock immediately before the merge/deploy; (5) 47.5 is the only substantive change in its deploy (isolated for clean rollback); (6) single Alembic head after `0019`.
- 47.4 (API-surface retirement) is reversible by code revert — standard review/gate path + explicit note, not the full destructive gate.
- Spec validation of 47.4/47.5 may proceed; dev-story/deploy of 47.5 may not, until the deferred destructive-go is recorded.

## 8. Implementation handoff

- **Scope classification:** MODERATE — backlog reorganization (PO/DEV). Additive 42.4 can enter `bmad-create-story` → dev → merge → deploy now, in parallel, with no dependency on this SoT edit landing first.
- **Do NOT** create implementation-ready 47.4/47.5 stories yet — this pass makes the planning/SoT changes only; `bmad-create-story` re-runs on 47.4 then 47.5 at their turn in the sequence.
- **Success criteria:** YAML parses with allowed statuses; no duplicate story IDs; dependency statements consistent (E43↔E42-additive; 45.3↔47.5 same HEAD); category live API preserved as bridge until consumers gone; destructive-go for 47.5 recorded before its dev-go.

---

**Tracked changes made by this SCP's APPLY pass:** `epics.md`, `sprint-status.yaml`, `architecture.md`, `triage-backlog.md`, `42-3-category-endpoint-removal.md`, and this artifact. No production/test code. No commit/push/merge/deploy/branch switch.
