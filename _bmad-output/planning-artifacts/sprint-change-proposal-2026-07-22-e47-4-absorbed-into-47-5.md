# Sprint Change Proposal — E47.4 Absorbed Into E47.5 (Terminal Category-Cutover Re-sequencing)

- **Date:** 2026-07-22
- **Author:** Claude (native `bmad-correct-course`, **PROPOSAL-ONLY** mode)
- **Status:** **APPROVED & APPLIED 2026-07-22.** Operator GO received — exact phrase `GO E47 ATOMIC CUTOVER` (Michał/Ezop, controller session, 2026-07-22), against the §8 interpretation as explicitly presented (including the destructive-go for `0019_drop_category` — see the APPLY record at the end of this document). The §6 planning edits were applied by a follow-up APPLY-mode `bmad-correct-course` pass the same day. *(Original status when authored: PROPOSED — awaiting operator GO/NO-GO; §8 was the decision block relayed.)*
- **Change class:** MODERATE — in-sprint re-sequencing + scope absorption inside the already-approved Initiative 25 (no new initiative, no PRD FR change, no new epic). Backlog reorganization (PO/DEV), matching the classification precedent set by the 2026-07-19 E42 re-sequencing SCP.
- **Trigger doc:** `.bmad-loop/runs/20260722-190446-a27a/worktrees/47-4-category-api-surface-retirement/_bmad-output/implementation-artifacts/spec-47-4-category-api-surface-retirement.md` (native `bmad-create-story`/spec-authoring run on Story 47.4, status **`blocked`**, `Auto Run Result` status `blocked`).
- **Baseline:** `main` @ `dff3d4427979af87ca7b17c4da41db48f4113f63`.
- **Supersedes/absorbs:** Story **47.4** is proposed to be absorbed into **47.5** (both stay inside Epic 47 — this is not a cross-epic relocation like the 2026-07-19 42.3→47.4/42.5→47.5 move, it is a merge of two sibling stories already inside the terminal cutover epic).

> This proposal, in this session, modifies **no** planning/SoT artifact. §6 lists exactly what a subsequent APPLY pass would change, worded as it would be written, so an operator or a future APPLY-mode correct-course run can act on it without re-deriving the analysis. It touches **no production or test code**. No reviewer identity or operator approval is recorded or implied anywhere below beyond what is explicitly cited from existing, dated artifacts.

---

## 1. Issue Summary

Story 47.4 ("Category API-surface retirement + FE category-tree type/hook cleanup") was run through native spec-authoring in an isolated worktree and **correctly self-blocked** before authoring any tasks. Its own intent-contract states the reason precisely: the story's stated hard precondition — *"every consumer of `GET /api/categories` / `category_id` is gone"* — is **false** against the current codebase, and the planning artifacts that assert it is true (`epics.md`, `epic-47-context.md`) are stale relative to what Stories 45.2 and 45.3 actually shipped.

This is the same failure class the 2026-07-19 E42 correct-course (`sprint-change-proposal-2026-07-19-e42-deferred-coupled-cutover.md`) and the E43 additive-correction SCP already closed once each: an epic-level sketch asserting a dependency precondition is met, when the shipped code says otherwise. It has now recurred a further time, at the very story the earlier two corrections routed the destructive work *to* — the terminal cutover itself is not immune to the same drift class it was created to fix.

**Concretely:** two live frontend call sites still depend on the category-tree API surface 47.4 was scoped to remove:

1. `apps/web/src/modules/admin/AddModelForm.tsx:13,81` — admin create-form category `<select>`, feeding `category_id` into `POST /admin/models`.
2. `apps/web/src/modules/catalog/components/ModelHero.tsx:14,65` — category-ancestry breadcrumb on `/catalog/$id`, independent of the tag-grouping work Story 45.2 shipped.

Removing the backend routes/hook 47.4 targeted, while either consumer is still wired to them, is not a test failure — `main` auto-deploys to `.190` (AGENTS.md), so it is a **live production outage**: a broken admin add-model form and/or a broken model-detail page the moment the merge deploys.

## 2. Evidence

**Precondition-mismatch, consumer #1 — `AddModelForm` (documented, operator-approved deferral, not a gap in itself):**
- `apps/web/src/modules/admin/AddModelForm.tsx:13` imports `useCategoriesTree`; `:81` calls it to populate the category `<select>` feeding `POST /admin/models`.
- `_bmad-output/implementation-artifacts/spec-45-3-edittagssheet-grouped-picker-create-form-cutover.md` (`status: done`) explicitly scoped itself to the grouped tag *picker* only and left `AddModelForm.tsx`/`routes/admin/models/new.tsx` "byte-for-byte untouched," deferring the selector removal "to ship in the same `main` HEAD as story 47.5" — the **45.3↔47.5 handshake**.
- `epics.md:4306` and `sprint-status.yaml` (epic-45 retro comment + the `epic:45 "HANDSHAKE"` action item, lines 407-410) record this same deferral. This is a *known, approved* fact — the contradiction is that 47.4's own scope (as sketched in `epics.md:4346-4352`) still assumed this consumer would be gone by 47.4's turn, which the 45.3↔47.5 handshake directly contradicts: the handshake ties the selector removal to **47.5**, not 47.4.

**Precondition-mismatch, consumer #2 — `ModelHero` breadcrumb (undocumented as a migration target — the genuinely new finding):**
- `apps/web/src/modules/catalog/components/ModelHero.tsx:14,65` (plus the ancestry-walk at ~lines 26-35, 73-77, 93-99) calls `useCategoriesTree()` independently of `AddModelForm`, to render a category-ancestry breadcrumb by walking `parent_id` from `detail.category` up to the root.
- `_bmad-output/implementation-artifacts/spec-45-2-catalogdetail-grouped-tags.md` (`status: done`) — the most recent story to touch `ModelHero.tsx` — scoped itself explicitly and only to replacing the flat tag-chip row with `TagGroupsSection` (its own Code Map, line 63-64; its `Never` boundary explicitly forbids touching `FacetSidebar`/`CatalogList`/`ModelCard`, but says nothing about the breadcrumb because the breadcrumb was out of scope, not reviewed and kept). Its own test-file note explicitly preserves "the existing `useAuth`/`useCategoriesTree` mocks."
- **No retrospective, epic sketch, or triage-backlog entry anywhere in this repo flags the `ModelHero` breadcrumb as scheduled for migration or removal.** `epics.md:4346-4352`'s 47.4 sketch and `epic-47-context.md:23,38` both assert the FE-consumer precondition is met "after 44.3 + 45.x" — that assertion is stale against what 45.2 actually shipped.

**Verified live on `main` @ `dff3d44` (this session, `grep`):**
```
apps/web/src/modules/admin/AddModelForm.tsx:13:import { useCategoriesTree } from "@/modules/catalog/hooks/useCategoriesTree";
apps/web/src/modules/admin/AddModelForm.tsx:81:  const tree = useCategoriesTree();
apps/web/src/modules/catalog/components/ModelHero.tsx:14:import { useCategoriesTree } from "@/modules/catalog/hooks/useCategoriesTree";
apps/web/src/modules/catalog/components/ModelHero.tsx:65:  const tree = useCategoriesTree();
```
Both call sites match the blocked spec's Code Map exactly — the blocked spec's own investigation is confirmed independently, not merely trusted.

**Blocked-artifact verdict:** `spec-47-4-category-api-surface-retirement.md` frontmatter `status: blocked`; `Auto Run Result` → `Status: blocked`, `Tasks & Acceptance` explicitly "Not authored — blocked pending the operator decision," consistent with this story correctly refusing to guess per this repo's "Stop at unknown unknowns" / "No silent scope creep" AI-agent execution-discipline rules (`project-context.md` § "AI agent execution discipline").

## 3. Path-forward evaluation

**Option 1 — Direct adjustment (rescope 47.4 standalone to also migrate both consumers first, then proceed as its own story).** *Not recommended.* This would reopen the already-settled, operator-approved 45.3↔47.5 handshake (pulling `AddModelForm`'s selector removal earlier than the atomic DTO cutover it's coupled to for good reason — `Model.category_id` is `NOT NULL`, so the selector can't safely go fully-optional until the backend field is actually optional/gone) and would force a fresh, un-reviewed product decision on `ModelHero`'s breadcrumb (drop it? replace it?) inside a story whose own title says "API-surface retirement," not "UX redesign." It also does not remove the underlying two-atomic-commits risk: 47.4 (FE+BE surface) and 47.5 (ORM+DTO+migration) would still be two separate deploys touching the same live category dependency chain, doubling the live-outage-window surface instead of collapsing it.

**Option 2 — Rollback.** *Not viable / not applicable.* Nothing shippable has landed for 47.4 — it never got past spec-authoring (`blocked`, no tasks authored, no code written). There is nothing to roll back.

**Option 3 — PRD/MVP scope reduction.** *Not applicable.* No FR/NFR is affected; Initiative 25's target contract (facet tags replace category everywhere, category fully retired) is unchanged. This is a sequencing/atomicity correction, not a scope-of-value change.

**Recommended: Hybrid of Direct Adjustment + the existing 47.5 atomicity precedent — absorb 47.4 into 47.5, one atomic cutover.** This is the controller's (Laura's) formalized recommendation, evaluated against the above and found sound on its own logic, not merely rubber-stamped:

- It extends — rather than contradicts — the *already-approved* 2026-07-19 principle that irreducibly-coupled category-removal work belongs in one atomic commit (the same reasoning the E42 SCP used to justify making 47.5 "ONE commit" for ORM+DTO+migration in the first place; TB-053). The two now-known live consumers are exactly the kind of coupling that reasoning was meant to catch.
- It resolves the `ModelHero` breadcrumb gap the only way consistent with existing product decisions already made in this initiative: Story 45.2 already shipped `TagGroupsSection`, which is Initiative 25's answer to "how do users see a model's classification" — grouped tags, not single-parent ancestry. Inventing a new tag-hierarchy/breadcrumb to preserve the old UX would contradict the initiative's own premise (FR25-TAX-1: many admin-managed tags across facets that legitimately coexist, replacing a single hard category precisely because "pick one" was lossy). Plain removal, no replacement, is the only option consistent with what's already shipped.
- It does not reopen the 45.3↔47.5 handshake — it reinforces it by keeping the `AddModelForm` selector removal exactly where the operator already agreed it belongs (same `main` HEAD as the DTO/ORM drop), while adding `ModelHero`'s removal to the same HEAD for the identical reason (both are FE reads of a category field/tree the backend is about to make impossible to read).
- Net effect: one atomic cutover commit instead of two staggered ones, one destructive-go decision instead of two, and zero live-outage window between "FE surface retired" and "ORM+DTO retired" (today's two-story split has exactly that window if 47.4 ships alone).

**Effort/risk:** Low-medium effort (47.5's own migration/DTO/ORM work is unchanged in kind; the added scope is two FE removals whose code maps are already fully enumerated by the blocked 47.4 spec and this proposal's §5). Risk is lower than the status-quo two-story sequencing, not higher — it removes an intermediate deploy state.

## 4. Revised sequence + dependency arrows

```
E44/E45 (already done, on main)
  44.3 CatalogList migrated off useCategoriesTree/category_id  ── DONE
  45.2 ModelHero tag-chip row → TagGroupsSection               ── DONE (breadcrumb/useCategoriesTree call NOT migrated — this proposal's finding)
  45.3 EditTagsSheet grouped picker shipped;
       AddModelForm category-selector left untouched            ── DONE (45.3↔47.5 handshake recorded)

E47 (terminal cutover)
  47.1 i18n            ── DONE
  47.2 visual specs    ── DONE
  47.3 runbook/docs    ── DONE
  47.4 API-surface retirement  ── BLOCKED (this proposal's trigger) ─┐
                                                                      │  PROPOSED: absorb 47.4 INTO 47.5
  47.5 ORM+DTO+0019 atomic cutover  ◀───────────────────────────────┘
       NEW internal ordering inside the single 47.5 cutover (one commit / one branch / one deploy HEAD):
         (a) FE consumer migration first, same branch:
             - AddModelForm.tsx: remove category <select>, stop calling useCategoriesTree()
             - ModelHero.tsx: remove category-ancestry breadcrumb + useCategoriesTree() call (no replacement UI)
         (b) FE hook/types retirement:
             - delete useCategoriesTree hook + its test
             - delete CategoryNode/CategoryTree FE types (api-types.ts)
         (c) BE API-surface retirement (originally 47.4's backend half):
             - delete GET /api/categories, admin category CRUD routes, service fns, route-only schemas, their dedicated tests
         (d) BE DTO + ORM + migration (47.5's original scope):
             - drop ModelCreate/Patch/Summary.category_id, ModelDetail.category, CategorySummary, ShareModelView.category
             - drop class Category, Model.category_id, FK, index
             - ship 0019_drop_category (down_revision=0018_facet_tags, forward-only, downgrade() raises)
       (a)→(b)→(c)→(d) is the required internal order within the one commit/PR: FE stops reading before the BE stops serving, before the ORM stops existing — never the reverse, else an in-flight request mid-deploy could read a field the model no longer has.
```

Sequence for execution: **47.1 → 47.2 → 47.3 (all done) → [absorbed 47.4+47.5, one story, one atomic cutover] → epic-47 closes.**

## 5. Precise absorbed-47.5 scope (planning-level; NOT yet an implementation-ready story)

**(a) Frontend consumer migration — NEW scope, folded in from this proposal's finding:**
- `apps/web/src/modules/admin/AddModelForm.tsx` — remove the category `<select>` (`flattenCategories` helper, lines ~53-67, ~143-144, ~194-206 per the blocked spec's citations) and the `useCategoriesTree()` call (`:81`); `POST /admin/models` payload stops sending `category_id` (already optional-at-create per the target DTO in (d) below).
- `apps/web/src/modules/catalog/components/ModelHero.tsx` — remove the category-ancestry breadcrumb (ancestry-walk + render, ~lines 26-35, 73-77, 93-99) and its `useCategoriesTree()` call (`:65`). **No replacement breadcrumb or tag-hierarchy** — `TagGroupsSection` (already mounted below the badge row per Story 45.2) is the classification surface going forward.
- Test updates: both components' existing `.test.tsx` files drop their `useCategoriesTree` mocks and any assertions tied to the removed UI; add/adjust assertions confirming the removed elements are absent and no regression to the surrounding markup (badge row, `TagGroupsSection` mount, `EditTagsSheet` pencil).
- Visual regression: any Playwright baseline covering `AddModelForm`/model-add and `ModelHero`/catalog-detail must be regenerated across all four projects with `baseline-reviewed:` sign-off lines, per the Baseline Acceptance Gate.

**(b) FE hook/types retirement — carried over from 47.4's original scope, now gated on (a) landing first in the same commit series:**
- `apps/web/src/modules/catalog/hooks/useCategoriesTree.ts` + `useCategoriesTree.test.tsx` — delete (last two consumers now gone).
- `apps/web/src/lib/api-types.ts:55-59` (`CategoryNode`), `:61-63` (`CategoryTree`) — delete. `CategorySummary` (`:47-53`) is dropped in (d), not here — it's still embedded in `ModelDetail`/`ShareModelView` until the DTO drop.

**(c) Backend API-surface retirement — carried over verbatim from 47.4's Code Map (`spec-47-4-category-api-surface-retirement.md`), unchanged in content, only in sequencing (now inside 47.5's commit instead of its own):**
- `apps/api/app/modules/sot/router.py:48-64` — `GET /api/categories`.
- `apps/api/app/modules/sot/admin_router.py:765-792,795-828,831-853` — admin category create/patch/delete routes.
- `apps/api/app/modules/sot/service.py:63-124` — `list_categories_tree()`.
- `apps/api/app/modules/sot/admin_service.py:~1303-1479` — `create_category()`, `update_category()`, `_would_cycle()`, `delete_category()`.
- `apps/api/app/modules/sot/schemas.py:26-32` — `CategoryNode`, `CategoryTree` (route-only; **not** `CategorySummary`).
- `apps/api/app/modules/sot/admin_schemas.py:291-329` — `CategoryCreate`, `CategoryPatch`.
- Delete `apps/api/tests/test_sot_categories.py`, `test_sot_admin_categories.py`; remove `test_category_node_recursive_shape` from `test_sot_schemas.py:159-177`; drop `CategoryCreate`/`CategoryPatch` entries from `test_openapi_agent_surface.py:43-44`; update the category-route params in `test_sot_auth_boundary.py:129,180,230,286,313`; migrate `test_bootstrap_agent.py:79-95` off the admin-CRUD POST to ORM-seed.
- No `_PUBLIC_ROUTES` edit needed (category routes were never in the allowlist — confirmed by 47.4's own audit and TB-055); `test_route_enforcement_gate.py` self-heals off the live route table.

**(d) Backend DTO + ORM + migration — 47.5's original scope, unchanged:**
- Drop `ModelCreate.category_id` + `ModelPatch.category_id`; drop `ModelSummary.category_id`; drop `ModelDetail.category` + `CategorySummary`; drop `ShareModelView.category` (live projection, `share/router.py:16,144,228`, `share/models.py:40`).
- Remove `Category` validation + `Category*` imports from `create_model`/`update_model` (`admin_service.py:29,42-43,161-167,220-230`).
- Remove `class Category` (`_entities.py:29-58`) + `Model.category_id` + FK + `ix_model_category_id` (`_entities.py:109-111`).
- Migration `0019_drop_category` — `down_revision = "0018_facet_tags"`, forward-only, `downgrade()` raises `NotImplementedError`; `batch_alter_table("model")` drop index + column (no `drop_constraint` — unnamed inline FK, per architecture.md Decision AV), then `op.drop_table("category")`.
- Tests: ORM↔migration parity test (`compare_metadata`, discharges E41 retro action item #2); NFR25-LEAKFENCE-1 negative share-DTO test; fix the ~25 fixtures that ORM-seed `Model(category_id=...)`.
- OpenAPI: `/api/openapi.json` surface loses every `Category*` schema and the `category_id`/`category` fields on `Model*`/`ShareModelView` — verify via `test_openapi_agent_surface.py` (already updated in (c)) and a fresh spot-check that no orphaned `$ref` remains.
- `hydrate_local_tree.py` category path-map removal — coordinated with the already-shipped 47.3 runbook/docs cutover (no new doc work, just confirming no residual reference survived 47.3).

**No partial/hidden/internal category API bridge** at any point in (a)-(d) — matches 47.4's own `Never` boundary and the E42 SCP's "zero-code compatibility bridge" framing: the bridge is the *unmodified live API until this cutover*, not a scoped-down shim during it.

## 6. Detailed change proposals — NOT applied this session; exact text an APPLY pass would write

- **`epics.md` § Initiative 25, Epic E47:**
  - Story 47.4 heading (`:4346`) gains a superseded/absorbed banner in the same style as the existing 42.3/42.5 banners (`:4234`, `:4244`): *"> **Absorbed 2026-07-22** by `bmad-correct-course` (SCP `sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md`). 47.4's full scope (backend API-surface retirement + FE `useCategoriesTree`/`CategoryNode`/`CategoryTree` cleanup) is folded into Story 47.5 as one atomic cutover, together with the newly-identified `AddModelForm` selector removal and `ModelHero` breadcrumb removal. Do NOT build 47.4 as a standalone story. The original sketch is retained below for history."*
  - Story 47.5 heading (`:4354`) gains an expanded scope line naming the four sub-phases (a)-(d) from §5 above, and its title changes from "Category ORM + DTO + `0019` atomic cutover" to something reflecting the merged scope, e.g. "Category API-surface + ORM + DTO + `0019` atomic cutover (absorbs 47.4)."
  - The Epic List table row for E47 (`:4198`) updates its Stories column from "47.4 ... 47.5 ..." to reflect 47.4's absorbed status.

- **`epic-47-context.md`:**
  - `## Stories` list — Story 47.4 line gains "(absorbed into 47.5, 2026-07-22)"; Story 47.5's description expands to name the FE consumer migrations.
  - `## Requirements & Constraints` bullet on the 47.4/47.5 precondition (currently: *"47.4 (API-surface retirement) and 47.5 (ORM+DTO+migration 0019) may only proceed once every consumer... is gone"*) is corrected to state the actual current gap (`ModelHero` breadcrumb undocumented dependency) and the absorbed-cutover resolution, replacing the stale "after 44.3 + 45.x" precondition framing.
  - `## Technical Decisions` — the bullet distinguishing what 47.4 vs 47.5 "own" is rewritten: both now describe sub-phases of one story.
  - `## Cross-Story Dependencies` — the "47.5 depends on 47.4" line is removed (no longer a cross-story dependency, both are the same story's internal phases).

- **`sprint-status.yaml`:**
  - `47-4-category-api-surface-retirement` — comment updated from "RELOCATED from 42.3... Not implementation-ready" to: *"SUPERSEDED / ABSORBED → 47-5 by bmad-correct-course 2026-07-22 (SCP sprint-change-proposal-2026-07-22-e47-4-absorbed-into-47-5.md). Blocked at spec-authoring on a live-consumer precondition mismatch (AddModelForm + ModelHero both still call useCategoriesTree). Kept as historical backlog key (not deleted). Do NOT dev this key."* Status stays `backlog` (matching the existing 42-3/42-5 precedent of not deleting superseded keys).
  - `47-5-category-orm-dto-0019-atomic-cutover` — comment expands to list the absorbed 47.4 scope + the new `AddModelForm`/`ModelHero` FE removals, keeping the existing "Not implementation-ready" + destructive-go-deferred language verbatim.
  - `epic-47` rollup comment gains a note that 47.4 is absorbed, not separately delivered, so the epic's story count for closeout purposes is one fewer than originally sketched.
  - A new `action_items` entry under `epic: 47` (optional, recommended not required): flag the recurrence pattern — this is now the third time an epic/story sketch's stated dependency-precondition was stale against shipped code (after the E42 42.3 sketch and the E43/E44 sketch-wording items already tracked) — for the eventual epic-47 retrospective to fold into its "process aid" review, per the standing `epic: 43` action item on the same class of drift.

- **`architecture.md` § Initiative 25, Decision AW / AV area:**
  - A new dated update block, in the same style as the two existing 2026-07-19 update blocks (`:3230`, `:3241`): *"#### Update 2026-07-22 (bmad-correct-course) — 47.4 absorbed into 47.5; ModelHero breadcrumb removal added to the terminal cutover scope."* Body: names the two live-consumer findings, states the absorption decision, and amends the Decision AV "Terminal cutover constraints (47.5)" paragraph (`:3238`) to add the backup-restore-readiness strengthening from §7 below (not just "a backup exists" but a demonstrated restore).

- **`spec-47-4-category-api-surface-retirement.md`** (the blocked artifact itself, currently untracked in the worktree): header status line updated from `blocked` to a terminal marker such as `superseded-absorbed-into-47-5`, with a one-line pointer to this SCP — mirroring how `42-3-category-endpoint-removal.md` was marked after its own supersession.

**No file listed above is edited by this session.** All are candidate edits for a follow-up APPLY-mode `bmad-correct-course` pass, contingent on the §8 operator decision.

## 7. Pre-migration backup / verification / rollback-or-forward-fix policy

This absorbs and **strengthens** the destructive gate already recorded at `epics.md:4360` (47.5's original gate) — it does not replace it; every item below is additive to that existing text, carried forward verbatim in spirit:

1. `0019_drop_category` is forward-only; `downgrade()` raises `NotImplementedError` — irreversible by Alembic. Unchanged from the existing gate.
2. Category rows + per-model assignment are permanently lost by design (accepted in the 2026-07-17 SCP — models start untagged). Unchanged.
3. **Rollback = verified pre-`0019` `.190` DB backup restore + `git revert` of the (now-merged) cutover commit + redeploy.** Unchanged in shape, but now covers a larger single commit (a)-(d) instead of just (d) — the revert target is the whole absorbed-47.5 commit, including the FE removals, since a partial revert (e.g. restoring the DB but leaving the FE code that no longer reads `category`) would leave the app in an inconsistent state.
4. **Strengthened:** a pre-`0019` backup on `.190` must not merely *exist* — its restore path must be **demonstrated** before the cutover deploy: a dry-run restore of the backup file into a scratch SQLite database (or equivalent verification query proving the backup file opens cleanly and contains the expected `category`/`model.category_id` rows) immediately before the deploy, under the deploy lock (`flock /tmp/3d-portal-deploy.lock`), with the verification command and its output logged to `.hermes/run-logs/` as the closeout evidence. A file that exists but has never been opened/verified is not "restore-readiness."
5. The absorbed cutover (a)-(d) must be the **only** substantive change in its deploy — no unrelated feature/fix commits riding along — for a clean, unambiguous revert target.
6. Confirm a **single Alembic head** after `0019` before the deploy proceeds.
7. **Destructive-go remains DEFERRED — not granted by this proposal, and not implied by any prior approval.** The existing 2026-07-19 E42 SCP's explicit statement that "the final forward-only destructive go for 47.5 to its dev-go... is NOT recorded as granted" stays in force; this proposal does not and cannot substitute for that operator act.
8. Spec validation of the absorbed 47.5 (i.e., running `bmad-create-story`/spec-authoring on the merged scope) may proceed once this SCP itself is approved; **dev-story execution and deploy may not proceed** until the destructive-go in item 7 is separately recorded at the merged story's dev-go.

## 8. Operator decision block — for Laura to relay to Michał as a single GO/NO-GO question

> **Epic 47 — Story 47.4 blocked on a planning contradiction (two live consumers of `useCategoriesTree` still exist: `AddModelForm`'s admin category-selector, and `ModelHero`'s category-ancestry breadcrumb — the second was never previously flagged for migration). Recommended resolution: cancel Story 47.4 as a standalone story and absorb its entire scope (backend API-surface retirement + FE hook/types cleanup) into Story 47.5, together with removing `AddModelForm`'s category selector (already deferred here per the existing 45.3↔47.5 handshake) and removing `ModelHero`'s breadcrumb with no replacement (its classification role is already served by the shipped `TagGroupsSection`). This makes 47.5 one atomic cutover: FE consumer removal → FE hook/type retirement → backend route/service/schema retirement → ORM/DTO/migration `0019_drop_category`, all in one commit/deploy.**
>
> **This is a planning re-sequencing only — it does NOT authorize the destructive migration itself.** The existing requirement that you separately record an explicit destructive-go before 47.5's dev-go stays in force, now additionally requiring demonstrated (not merely existing) SQLite backup restore-readiness on `.190` immediately before that deploy.
>
> **GO** = approve absorbing 47.4 into 47.5 as described (planning-artifact edits in §6 proceed in a follow-up APPLY pass; `bmad-create-story` then runs on the merged 47.5 scope; destructive-go for the migration itself is still a separate, later decision).
> **NO-GO** = reject this resolution — state which part (the absorption itself, the `ModelHero` breadcrumb removal with no replacement, or something else) and an alternative will be drafted.
>
> No code, migration, deploy, commit, or push has occurred. Nothing is destructive yet.

## 9. Implementation handoff

- **Scope classification:** MODERATE — backlog reorganization (PO/DEV), consistent with the 2026-07-19 E42 SCP's classification of the same kind of change.
- **Do NOT** create an implementation-ready merged-47.5 story yet — that is `bmad-create-story`'s job, to run only after this SCP is approved and §6's planning edits are actually applied by a follow-up APPLY-mode `bmad-correct-course` pass (this session did not apply them).
- **Success criteria for the APPLY pass, if approved:** `epics.md`/`epic-47-context.md`/`sprint-status.yaml`/`architecture.md` edits land exactly as previewed in §6 (or as amended by operator feedback); no duplicate/invented story IDs; 47.4 key preserved as historical/superseded, not deleted; the 45.3↔47.5 handshake language is preserved, not weakened; the destructive gate is preserved and strengthened per §7, never loosened.
- **Success criteria for the eventual merged-47.5 implementation:** all four sub-phases (a)-(d) in §5 land in one commit; full `check-all.sh` green; visual baselines regenerated with sign-off for both touched components; ORM↔migration parity test passes; NFR25-LEAKFENCE-1 negative share-DTO test passes; no `Category*` symbol remains anywhere in `apps/api`/`apps/web` except this proposal's and the retrospective's historical references.

---

**Tracked changes made by this SCP in its authoring session:** none to `epics.md`, `sprint-status.yaml`, `architecture.md`, `epic-47-context.md`, or the blocked spec artifact. Only this proposal document was written, under `_bmad-output/planning-artifacts/`. No commit, no push, no merge, no deploy, no branch switch, no destructive-go recorded in that session.

---

## APPLY record — 2026-07-22 (native `bmad-correct-course`, APPLY mode)

- **Operator approval:** exact phrase **`GO E47 ATOMIC CUTOVER`**, received from Michał/Ezop in the controller session on **2026-07-22**, relayed by Laura. The interpretation explicitly presented before approval — and therefore authorized — covers: (1) absorbing Story 47.4 into Story 47.5 per §8; (2) removal of the `AddModelForm` category selector; (3) removal of the `ModelHero` category-ancestry breadcrumb with no replacement; (4) **destructive implementation and deployment of forward-only `0019_drop_category`, accepting deletion of 43 category rows and 130 model-category assignments from the live DB** (i.e., the §7-item-7 destructive-go is now RECORDED, superseding "deferred" language elsewhere in this document, which is retained above as authored); (5) rollback = verified DB restore + `git revert` of the whole cutover + redeploy, not Alembic downgrade; (6) pre-deploy still requires a second **fresh** verified backup under `/tmp/3d-portal-deploy.lock`.
- **Restore-readiness checkpoint (pre-GO, controller-verified):** backup `/mnt/raid/3d-portal-state/backups/portal-pre-e47-5-20260722T172024Z.db`, sha256 `0dfd305e59fd211b7f0578bbb480239a75d69941406e71582be1c4329bd21652`, integrity `ok`, FK check 0, alembic `0018_facet_tags`, 43 category rows / 130 model-category assignments; independent scratch restore integrity `ok` with matching counts; evidence `.hermes/run-logs/e47-precutover-backup-20260722T172024Z.log`. Demonstrates restore-readiness per §7 item 4 but does **not** replace the fresh pre-deploy backup.
- **Applied edits (this APPLY pass; docs/planning artifacts only):** `epics.md` (E47 table row; E47 goal/depends; 47.4 absorbed banner; 47.5 title + phases (a)-(d) scope; destructive gate strengthened + GO recorded), `_bmad-output/implementation-artifacts/epic-47-context.md` (Stories, Requirements & Constraints, Technical Decisions, Cross-Story Dependencies), `_bmad-output/implementation-artifacts/sprint-status.yaml` (`47-4` superseded/absorbed comment — status stays `backlog`, key preserved; `47-5` expanded comment; `epic-47` rollup; new `epic: 47` action item; `last_updated` log), `architecture.md` (new dated Update block, Decision AV/AW area), and the blocked 47.4 spec copied from the bmad-loop worktree into `_bmad-output/implementation-artifacts/spec-47-4-category-api-surface-retirement.md` with terminal status `superseded-absorbed-into-47-5` (investigation preserved verbatim).
- **Not done in this pass (out of scope by §9 + task mandate):** no implementation story created or validated; no code/test/migration touched; no live DB action; no commit, push, merge, or deploy.
- **Next canonical route:** `bmad-create-story` (Create) on the merged `47-5-category-orm-dto-0019-atomic-cutover` scope → `bmad-create-story:validate` → dev-go per the strengthened gate.
- **Provenance:** applied by Claude (Opus 4.8) in the APPLY-mode `bmad-correct-course` session; no human reviewed the applied diffs before this record was written — controller review is the next gate. No reviewer identity beyond this is claimed.
