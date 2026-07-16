# Sprint Change Proposal — Facet Tag Taxonomy + Category Retirement (Catalog Rebuild)

- **Date:** 2026-07-17
- **Author:** Ezop (via Correct Course workflow)
- **Status:** APPROVED by operator (Ezop) 2026-07-17 — routed Path A (PM/Architect → Sprint Planning)
- **Trigger doc:** `docs/design/HANDOFF-tagi-fasetowe.md` (7 mockups + edge states, PL/EN + light/dark)
- **Design source of truth (visual):** `Katalog — Tagi fasetowe.dc.html`
- **Change class:** **MAJOR** — retires a shipped core entity (`Category`), requires a schema migration, amends PRD + Architecture, and opens a new Initiative (25) with multiple epics.
- **Slots into:** Initiative 25, Epics 41+ (highest shipped: Initiative 24 / epic-40, production baseline frozen 2026-07-16).

> This proposal is produced in **Batch** mode with **amendment drafts** (PRD FR block, Alembic migration sketch, epic/story list) embedded inline. It is an analysis + plan artifact; it does **not** modify `prd.md` / `architecture.md` / `epics.md` — those edits happen at handoff after approval.

---

## Change Navigation Checklist (completed)

| # | Item | Status | Note |
|---|---|---|---|
| 1.1 | Triggering story | [x] | No single story — a deliberate product pivot captured in the HANDOFF; the two cancelled residuals (`38-4`, `4-6`) already name this rebuild as their supersessor in `sprint-status.yaml`. |
| 1.2 | Core problem defined | [x] | Strategic pivot: single hard category → many facet-grouped tags. |
| 1.3 | Evidence gathered | [x] | Code-verified (see Appendix A). |
| 2.1 | Current epic completable? | [x] N/A | All epics through 40 are `done` and frozen; nothing in-flight to complete. |
| 2.2 | Epic-level changes | [x] | **Add** new Initiative 25 (epics 41+). No existing epic reopened. |
| 2.3 | Remaining epics impacted | [x] N/A | No open epics remain. |
| 2.4 | Invalidates / needs new epics | [x] | Net-new epics needed; no planned epic invalidated (baseline frozen). |
| 2.5 | Resequencing | [x] N/A | Greenfield forward work; internal sequencing defined in §4.3. |
| 3.1 | PRD conflicts | [x] Action-needed | FR0-CAT-1..3, FR0-ADM-1, FR0-SOT-1 reference categories (see §3-PRD). |
| 3.2 | Architecture conflicts | [x] Action-needed | Data model (Category tree, `model.category_id`), API contract, share projection. |
| 3.3 | UI/UX conflicts | [x] Action-needed | Full catalog browse + detail + edit + admin surfaces (HANDOFF §4, verified). |
| 3.4 | Other artifacts | [x] Action-needed | Agent add-model runbook (`GET /api/categories` pre-flight), i18n, visual-regression baselines, docs. |
| 4.1–4.4 | Path forward | [x] | **Direct Adjustment via a new Initiative** (§3). |
| 5.1–5.5 | Proposal components | [x] | §1–§5 below. |
| 6.x | Final review / handoff | [ ] | Pending operator approval (§5). |

---

## Section 1 — Issue Summary

The catalog was built on a **single, hard, mandatory category per model** (`Model.category_id`, NOT NULL, FK → `category.id`), organised as a **hierarchical tree** (`Category.parent_id` self-ref). Operating the catalog exposed the classic taxonomy failure: one model legitimately belongs to several axes at once (a *type*, a *room*, a *system*, a *material*, a *creator*), and a single tree forces a lossy "pick one" choice plus deep drill-downs.

**Decision (owner, 2026-07-16):** replace the hard single category with **many tags grouped into facets**:

- Many-to-many model↔tag already exists (`model_tag`); we lean on it.
- A tag belongs to one **group/facet** (Type, Room, System, Material, Creator, …); groups are a real, admin-managed entity — not a string convention.
- **Tag creation is admin-only.** Users pick from a curated set.
- Filter combination is a **user-visible AND/OR toggle** (default AND).
- **No data migration.** Old categories are dropped; every model starts **untagged** and is re-tagged from scratch (deliberate owner reset). The `untagged=true` filter exists precisely to triage this post-cutover state.

This supersedes and finalises the two residuals cancelled in the frozen baseline (`38-4-member-offer-request-estimate-cta`, `4-6-add-model-from-url-cli`).

---

## Section 2 — Impact Analysis

### 2.1 Epic impact
- No open epic is affected — the baseline is frozen at epic-40, all `done`. This is **additive**: a new **Initiative 25** with epics **41+**.

### 2.2 Artifact conflicts

**PRD (`_bmad-output/planning-artifacts/prd.md`)**
- `FR0-CAT-2` (search across name/tags/**categories**), `FR0-CAT-3` (filter by **categories**), `FR0-ADM-1` (edit **categories**), `FR0-SOT-1` (public list **categories**), and the `admin/` CRUD-over-Category surface (line 244) all reference the retiring entity. Needs an Initiative-25 FR block that redefines catalog browse/filter/admin around facet tags and marks the category FRs superseded.

**Architecture (`architecture.md`)**
- Data model: `Category`, `CategoryNode`, `CategoryTree`, `Model.category_id`.
- API contract: `GET /api/categories`, `GET /api/models?category_ids=…`, admin category CRUD.
- New: `TagGroup` table, `tag.group_id` nullable FK, facet filter semantics.

**UI/UX (`apps/web/src/modules/catalog/**`, `apps/web/src/ui/custom/ModelCard.tsx`)** — all files in HANDOFF §4 exist and are correctly named (Appendix A). Full browse/detail/edit/admin rework.

**Other artifacts**
- Agent add-model runbook / PRD FR6 pre-flight uses `GET /api/categories` (slug-exists check) — must drop.
- i18n (`locales/pl.json`, `en.json`), visual-regression baselines (new facet surfaces; **pl-PL locale** per project memory), docs.

### 2.3 Technical impact — schema (code-verified, Appendix A)
- `Model.category_id` is **NOT NULL + FK `category.id` ondelete=RESTRICT + indexed** (`_entities.py:85`). Removal is **not** a plain `drop column`: on SQLite the FK + index live inside the table definition and require `batch_alter_table`.
- `Category` is a **self-referential tree** (`parent_id` FK RESTRICT, plus `uq_category_parent_slug`, `uq_category_root_slug`, `ix_category_parent`) — drop the table wholesale after `model.category_id` is gone; no leaf-by-leaf delete needed because we are dropping, not clearing.
- `Tag` / `model_tag` stay. `model_tag.tag_id` is `ondelete=RESTRICT` — tag delete still requires merge-or-empty first (unchanged; `POST /tags/merge` already handles this).
- Migration head is **`0017_model_note_bilingual`** → new revision **`0018`**.

### 2.4 Diligence findings **beyond** the HANDOFF (important)

1. **Share module couples to Category — HANDOFF §4 omits it.** `ShareModelView` (Pydantic DTO, `share/models.py:40`) carries `category: str`, resolved **live** from `model.category_id` at `share/router.py:144` and emitted at `:228` (`category=category.slug`). **No data migration needed** (it is a projection, not a stored column), but the anonymous share contract + share detail UI must drop or replace `category`. Good news: `ShareModelView.tags: list[str]` already flows to anonymous visitors, so the facet story extends cleanly.
2. **`slicer/*` "category" is a false positive — explicitly OUT OF SCOPE.** The many `category` hits under `apps/api/app/modules/slicer/**` are `reason_category` / warning-`code` / structured-incompatibility strings — unrelated to the `Category` entity (no import of it). Excluding this prevents a large, wrong scope expansion.
3. **`POST /tags/merge` already exists** (`admin_router.py:693`) with rename/patch/delete siblings — the HANDOFF asks for merge as new work; it is **reuse**, not build. New admin work is **group governance** (group CRUD, move-to-group, `tag.group_id`), not merge.
4. **Admin manual-add form + `ModelCreate` require `category_id`** (NOT NULL; `admin_router.py:148/167` 400-on-category-not-found; FR10 `routes/admin/models/new.tsx` has a category selector). Both must drop the category field and make tagging optional-at-create.

---

## Section 3 — Recommended Approach

**Selected: Option 1 — Direct Adjustment, realised as a new Initiative 25 (epics 41+).**
Rollback (Option 2) is N/A — nothing recent to revert; the baseline is intentionally frozen. MVP-reduction (Option 3) is unnecessary — the owner has already scoped the target in the HANDOFF.

- **Effort:** High (schema migration + full backend contract change + full catalog UI rebuild + new admin screen + i18n + visual baselines).
- **Risk:** Medium. The migration is destructive-by-design (categories dropped, models reset to untagged) but that is the **explicit owner decision**, de-risked by the `untagged` triage filter. Forward-only migration (per project precedent `NFR10-SCHEMA-MIGRATION-1`), old revision kept for emergency revert.
- **Classification:** **MAJOR** → PM/Architect confirm the Initiative-25 PRD + Architecture amendments, then Sprint Planning decomposes epics 41+ into stories, then Dev executes.

---

## Section 4 — Detailed Change Proposals

### 4.1 PRD amendment — Initiative 25 FR block (draft, to paste into `prd.md`)

> **Supersede note (prepend to FR0-CAT/ADM/SOT):** *"Categories retired by Initiative 25 (facet tags). `category_*` requirements below are historical; see Initiative 25 for the facet-tag replacement."*

**Initiative 25 — Facet Tag Taxonomy + Category Retirement**

- **FR25-TAX-1 — Facet groups are a first-class admin entity.** A `TagGroup` (table `tag_group`: `slug`, `name_en`, `name_pl?`, `position`) organises tags. A tag has a nullable `group_id` FK → `tag_group.id` (nullable required for the "Untagged" pseudo-facet / tags without a group). *Verifiable:* admin creates a group, assigns tags, reorders; a tag with `group_id=NULL` renders under the groupless pseudo-facet.
- **FR25-TAX-2 — Tag creation is admin-only.** Non-admin surfaces (EditTagsSheet, model-detail inline add) offer selection only; the "create tag" path is admin-gated. *Verifiable:* member EditTagsSheet exposes no create affordance; admin does.
- **FR25-FILT-1 — Facet filtering replaces category filtering.** `GET /api/models` drops `category_ids`; adds `tag_ids: string[]`, `tag_match: "all" | "any"` (default `all`), `untagged: bool`. Default semantics: **AND between groups, OR within a group**; `tag_match` is the user override (mockup 04). *Verifiable:* AND/OR toggle changes result set; `untagged=true` returns only models with zero tags.
- **FR25-FILT-2 — Untagged triage.** Every model with zero tags is a valid catalog member (matches no facet filter). `untagged=true` surfaces them; card shows a ghost "Bez tagów" chip (mockup 08A/08B).
- **FR25-BROWSE-1 — Facet sidebar.** Collapsible groups with multi-select checkboxes + per-tag counts, client-side substring search over `name_pl`/`name_en` on already-fetched groups (no new endpoint, no fuzzy), 2 groups expanded by default (by `position`) + any group with an active filter, collapse state persisted per user in `localStorage` (mockups 02/03).
- **FR25-DETAIL-1 — Grouped tag rendering on model detail.** Tags render grouped by facet (group label + chips). Empty group: hidden for users, dash + inline "Add" for admin. Tag click → catalog pre-filtered by that tag (mockups 05/08C).
- **FR25-ADMIN-1 — Tag/group governance screen.** Admin screen lists tags per group with counts; supports rename, **merge** (reuse existing `POST /tags/merge`), move-to-group, duplicate detection, group create/reorder (mockup 06 right).
- **FR25-SHARE-1 — Share projection drops category.** `ShareModelView` no longer carries `category`; tags continue to flow (mockup-agnostic; diligence finding §2.4.1).
- **FR25-AGENT-1 — Agent add-model no longer pre-flights categories.** The runbook pre-flight drops the "category slug exists / `GET /api/categories`" step; model create no longer requires `category_id`.

*(NFRs: reuse existing observability/i18n-parity/visual-verification/determinism NFR families — no new NFR class required; dark-mode is a hard AC per HANDOFF §7 token rule.)*

### 4.2 Architecture amendment — data model + migration + API contract

**Entities (`apps/api/app/core/db/models/_entities.py`)**
- **Add** `TagGroup(table="tag_group")`: `id` PK, `slug` unique+index, `name_en`, `name_pl: str|None`, `position: int`, `created_at`, `updated_at`.
- **Amend** `Tag`: add `group_id: uuid.UUID | None` FK → `tag_group.id` (nullable, `ondelete="SET NULL"`), add `group_position: int = 0`.
- **Remove** `class Category` entirely.
- **Amend** `Model`: remove `category_id` field (+ its FK + index).

**Alembic `0018_facet_tags_drop_category` (sketch)** — `down_revision = "0017"`, **forward-only**:

```python
def upgrade() -> None:
    # 1. New group table
    op.create_table(
        "tag_group",
        sa.Column("id", <uuid_type>, primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name_en", sa.String(), nullable=False),
        sa.Column("name_pl", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("uq_tag_group_slug", "tag_group", ["slug"], unique=True)

    # 2. Tag gains group membership (nullable FK — groupless allowed)
    with op.batch_alter_table("tag") as b:
        b.add_column(sa.Column("group_id", <uuid_type>, nullable=True))
        b.add_column(sa.Column("group_position", sa.Integer(),
                               nullable=False, server_default="0"))
        b.create_foreign_key("fk_tag_group_id", "tag_group",
                             ["group_id"], ["id"], ondelete="SET NULL")

    # 3. Drop Model.category_id (NOT NULL + inline FK + index) — batch on SQLite
    with op.batch_alter_table("model") as b:
        b.drop_index("ix_model_category_id")          # named @ 0004:91
        b.drop_column("category_id")
        # NOTE (corrected by Architecture Decision AV): NO drop_constraint here.
        # The category.id FK is an UNNAMED inline sa.ForeignKey (0004:73-78), so
        # there is no named constraint to drop; the SQLite batch copy-and-move
        # removes it with the column (precedents 0010:36-38, 0005:125-126).

    # 4. Drop the category tree wholesale (indexes/constraints go with the table)
    op.drop_table("category")

def downgrade() -> None:
    # Forward-only: categories + per-model assignment are unrecoverable.
    raise NotImplementedError("0018 is forward-only (NFR10-SCHEMA-MIGRATION-1).")
```

> **RESOLVED by Architecture Decision AV** (introspected against `0004_entity_tables.py`): index is named `ix_model_category_id` (`0004:91`); the `category.id` FK is **unnamed inline** (`0004:73-78`) → no `drop_constraint` needed. `down_revision = "0017_model_note_bilingual"` (full slug, not `0017`).

**API contract (`apps/api/app/modules/sot`, `.../admin`, `.../share`)**
- `GET /api/models`: drop `category_ids`; add `tag_ids`, `tag_match` (`all`|`any`, default `all`), `untagged`. Implement AND-between-groups / OR-within-group with `tag_match` override.
- `GET /api/tags`: return `group`/`group_id`; add `?with_counts=true`.
- **New** `GET /api/tag-groups` (groups + tags + per-tag counts) backing `useTagGroups()`.
- **Remove** `GET /api/categories` (`router.py`) + admin `POST/PATCH/DELETE /categories` (`admin_router.py:770+`) + `create/update/delete_category` service fns + `Category*` schemas.
- `ModelCreate`/`ModelPatch`: drop `category_id` (no longer required).
- Admin group governance: `POST/PATCH/DELETE /api/admin/tag-groups`, tag `move-to-group` (PATCH tag `group_id`). **Reuse** existing `POST /tags/merge`.
- `ShareModelView`: drop `category`; adjust `share/router.py:144/228`.

**Frontend types (`apps/web/src/lib/api-types.ts`)**
- `TagRead`: add `group`/`group_id` (+ `group_position`).
- `ModelSummary`/`ModelDetail`: remove `category_id` and `category: CategorySummary`.
- Remove `CategorySummary`, `CategoryNode`, `CategoryTree`.

### 4.3 Epic list (Initiative 25, epics 41+) — dependency-ordered

> Sequencing is a proposal; Sprint Planning finalises IDs/splits. Backend contract (E41–E42) precedes FE (E43–E46); cutover (E47) last.

- **Epic 41 — Data model + migration foundation (backend).**
  `TagGroup` entity; `Tag.group_id`+`group_position`; remove `Category`; remove `Model.category_id`; Alembic `0018` (forward-only); optional seed of the §8 starter taxonomy as `tag_group` + `tag` rows. *Stories:* 41.1 entities, 41.2 migration 0018, 41.3 optional taxonomy seed.
- **Epic 42 — API: facet filtering + group governance + category retirement.**
  `GET /models` (tag_ids/tag_match/untagged; AND-between/OR-within); `GET /tags` (group + counts); new `GET /tag-groups`; remove category endpoints + schemas + services; `ModelCreate/Patch` drop `category_id`; admin group CRUD + move-to-group (reuse merge); `ShareModelView` drop category. *Stories:* 42.1 models filter, 42.2 tags/tag-groups read, 42.3 category-endpoint removal, 42.4 admin group governance, 42.5 model create/patch + share DTO.
- **Epic 43 — Frontend data layer.**
  `api-types` (TagRead.group, drop Category*); `useTagGroups()`; retire `useCategoriesTree`; `useTags` with group; URL state `tag_ids`/`tag_match`/`untagged`. *Stories:* 43.1 types, 43.2 hooks, 43.3 URL state.
- **Epic 44 — Catalog browse UI.**
  `FacetSidebar` (replaces `CategoryTreeSidebar`) — collapsible groups, multi-select, counts, client-side search, localStorage collapse state, untagged pseudo-facet; `FilterRibbon` active chips + AND/OR toggle; `CatalogList` empty-result CTA ("Switch to OR / Clear"). *Stories:* 44.1 FacetSidebar, 44.2 FilterRibbon, 44.3 CatalogList states.
- **Epic 45 — Card / detail / edit.**
  `ModelCard` "Bez tagów" ghost-chip; `CatalogDetail` grouped-by-facet tags (admin inline-add on empty group); `EditTagsSheet` grouped picker + remove non-admin create; admin `models/new` drop category field. *Stories:* 45.1 card, 45.2 detail, 45.3 EditTagsSheet + create form.
- **Epic 46 — Admin tag/group management screen.**
  `modules/admin` new screen: per-group list, counts, rename, merge (reuse), move-to-group, duplicate detection, group create/reorder (mockup 06 right). *Stories:* 46.1 group list + counts, 46.2 rename/merge/move, 46.3 duplicate detection.
- **Epic 47 — i18n + theming + visual regression + runbook/docs cutover.**
  Remove `catalog.filters.category`/`openCategories`/`a11y.allCategories`; add `facets`/`matchAll`/`matchAny`/`untagged`/`noTags`/`tags.groupless`/admin merge-rename-newGroup-duplicates; token-only styling (dark-mode AC); new Playwright visual specs for facet surfaces (**pl-PL locale**; consolidate any overlapping `/api/*` mocks per project memory); update agent add-model runbook (drop category pre-flight); docs. *Stories:* 47.1 i18n, 47.2 visual specs, 47.3 runbook/docs.

### 4.4 UI/UX file map (from HANDOFF §4 — all paths verified to exist)

| File | Change |
|---|---|
| `components/CategoryTreeSidebar.tsx` | Replace with `FacetSidebar` (groups, checkboxes, counts, search, untagged pinned). |
| `components/FilterRibbon.tsx` | Active removable chips + AND/OR (`tag_match`) toggle. |
| `routes/CatalogList.tsx` | Drop `useCategoriesTree`/`category_id`; URL `tag_ids`/`tag_match`/`untagged`; empty-result CTA. |
| `hooks/useCategoriesTree.ts` | Remove; add `useTagGroups()`; `useTags` keeps `group`. |
| `ui/custom/ModelCard.tsx` | "Bez tagów" ghost-chip. |
| `components/sheets/EditTagsSheet.tsx` | Grouped-by-facet picker; drop non-admin create. |
| `routes/CatalogDetail.tsx` | Tags grouped by facet; admin inline-add on empty group. |
| `modules/admin/…` | New tag/group management screen. |

---

## Section 5 — Implementation Handoff

- **Scope class:** **MAJOR** → PM/Architect first.
- **Step 1 (PM/Architect):** ratify the Initiative-25 FR block (§4.1) into `prd.md` and the data-model/API/migration amendments (§4.2) into `architecture.md`; append Initiative 25 to `epics.md`.
- **Step 2 (Sprint Planning):** run `bmad-sprint-planning` to add epics 41–47 (status `backlog`) + stories into `sprint-status.yaml`; finalise story splits.
- **Step 3 (Dev):** execute back-to-front (E41 → E47); backend contract (E41–E42) is the hard prerequisite for FE.
- **Success criteria:** categories fully removed (schema, API, types, UI); facet browse/filter (AND/OR + untagged) works; admin group governance live; dark-mode + pl-PL visual specs green; agent runbook no longer references categories; migration 0018 applies forward-only on the frozen baseline.

### Open items to confirm at handoff (not blockers)
- Exact autogenerated FK/index names for `model.category_id` (introspect, don't guess).
- Whether to **seed** the §8 starter taxonomy in migration 0018 vs. a separate admin-run seed (recommend: separate seed story 41.3, keeps the destructive migration minimal).
- Share detail UI copy once `category` leaves `ShareModelView`.

---

## Appendix A — Code evidence (verified 2026-07-17)

- `apps/api/app/core/db/models/_entities.py:85-87` — `Model.category_id` NOT NULL + FK `category.id` ondelete=RESTRICT + index.
- `_entities.py:29-58` — `Category` self-ref tree (`parent_id` RESTRICT; `uq_category_parent_slug`, `uq_category_root_slug`, `ix_category_parent`).
- `_entities.py:61-69,129-139` — `Tag` + `model_tag` (M2M; `tag_id` RESTRICT) present and retained.
- `apps/api/migrations/versions/0017_model_note_bilingual.py` — current head → new `0018`.
- `apps/api/app/modules/sot/router.py:46-134` — `GET /categories` (`CategoryTree`), `GET /tags`, `GET /models?category_ids(OR)&tag_ids(AND)`.
- `apps/api/app/modules/sot/admin_router.py:668-797` — tag CRUD + `POST /tags/merge` (**exists**) + category CRUD (`/categories` create/patch/delete).
- `apps/api/app/modules/share/models.py:40` + `share/router.py:144,228` — `ShareModelView.category` resolved live from `model.category_id` (DTO, not a stored column).
- `apps/api/app/modules/slicer/**` "category" = `reason_category`/warning `code` strings — **unrelated** to the `Category` entity (no import).
- `apps/web/src/lib/api-types.ts:43-63,166,183` — `CategorySummary`/`CategoryNode`/`CategoryTree`/`TagRead`/`ModelSummary.category_id`/`ModelDetail.category`.
- HANDOFF §4 UI files all present (see §4.4).
