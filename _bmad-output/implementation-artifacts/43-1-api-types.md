---
baseline_commit: 5b5da8c4f0aa3f03a05f2c25eb0ca45d43f7177a
---

# Story 43.1 — `api-types` facet-tag data types (FR25-FILT-1, FR25-TAX-1)

- **Epic:** E43 — Frontend data layer (Initiative 25 — Facet Tag Taxonomy + Category Retirement)
- **Status:** `review` — **DEV COMPLETE 2026-07-19 via native `bmad-dev-story` (author Claude/BMAD; controller Laura owns review/commit/merge/push/deploy). Branch `feat/E43.1-api-types` from `main` @ 5b5da8c, left uncommitted for controller review. All ACs green (typecheck/lint/vitest/build); see § 9 Dev Agent Record. Was:** `ready-for-dev` — **validated 2026-07-19 via native `bmad-create-story:validate` (VS) → PASS** (see § 8 Validation record; 1 important + 2 minor findings fixed in-place). The planning correction that blocked this story is **APPLIED** (operator-approved `bmad-correct-course` 2026-07-19; SCP `sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md`, status APPROVED/APPLIED). The `epics.md` E43 sketches + `architecture.md` Decision AW § Frontend types now match the shipped 42.2 wire and the additive scope; every category symbol is preserved (owners: 47.4 tree types + `useCategoriesTree`, 47.5 model DTO/field). The additive spec in §3–§4 is the source of truth. Next native step: `bmad-dev-story` (dev-go — validation PASS recorded in § 8). **History note:** this story was authored `BLOCKED_PROCEDURAL` (see § Procedural block, retained below as audit history); that block is now **RESOLVED** by the applied correction — the SoT contradiction it flagged no longer exists.
- **Author:** Claude (BMAD create-story). **Controller:** Laura.
- **Created:** 2026-07-19 via native `bmad-create-story` (Create) after mandatory `bmad-help`.
- **Scope class:** frontend data types only (`apps/web/src/lib/api-types.ts` + a type-level test). No hooks / URL / UI / backend / migration.
- **Sources of truth:** `epics.md` §Initiative 25 (E43, 43.1); `architecture.md` Decision AW; SCP `sprint-change-proposal-2026-07-19-e42-deferred-coupled-cutover.md` (APPROVED); shipped E42 wire (`apps/api/app/modules/sot/schemas.py`, 42.2 done + deployed `0.1.0+d291283`).

---

## 1. Procedural block — why this WAS not ready-for-dev as sketched  *(RESOLVED 2026-07-19 — retained as audit history)*

> **RESOLVED 2026-07-19.** The operator-approved `bmad-correct-course` (SCP `sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md`, APPROVED/APPLIED) amended `epics.md` E43 sketches + `architecture.md` Decision AW § Frontend types to the additive scope, discharging every blocker below. The section is preserved **unchanged** as the audit record of why the story was authored `BLOCKED_PROCEDURAL`; it is no longer an active block.

The epic sketch for 43.1 (`epics.md:4258`, pre-correction) read:

> `TagRead` gains `group`/`group_id`/`group_position`; `ModelSummary`/`ModelDetail` drop `category_id` and `category`; remove `CategorySummary`/`CategoryNode`/`CategoryTree`.

Two parts of that sketch are **not implementable green today** and one is **inaccurate vs. the shipped wire**:

### 1.1 Destructive category-type removals contradict the approved 2026-07-19 relocation

The 2026-07-19 `bmad-correct-course` (SCP `…-e42-deferred-coupled-cutover.md`, operator-approved) **relocated** the category-destructive work to the terminal cutover epic E47 and recorded that the live category surface is a **zero-code compatibility bridge** until then:

- **47.5** (relocated from 42.5 + orphaned ORM/`0019`) owns dropping `ModelSummary.category_id`, `ModelDetail.category`, `CategorySummary`, `ShareModelView.category` — as **one irreducibly atomic commit** with the backend ORM/`0019_drop_category` removal, behind a **DEFERRED destructive-go gate** (`epics.md:4350-4356`).
- The SCP explicitly lists **"Keeps alive: `CategorySummary`, `ModelCreate/Patch/Summary/Detail.category(_id)`"** (SCP line 83) until 47.4/47.5.
- E43's own dependency note (`epics.md:4254`): *"E43 coexists with the still-live category API (the zero-code compatibility bridge)."*

Removing these **FE types now** while the backend still ships the fields would (a) desynchronise `api-types.ts` from the live wire (a dishonest contract — the type would deny a field the server sends), and (b) break compilation of live consumers (§2). Both violate the green-repo invariant and the approved relocation.

### 1.2 The removals break live production consumers (compile-time)

Full consumer audit in §2. Every category type/field/hook in the sketch still has **production** (non-test) consumers that are only migrated by later E44/E45/47.x stories. Deleting the types in 43.1 is a hard TypeScript compile break in at least `ModelHero.tsx`, `AddModelForm.tsx`, `CatalogList.tsx`, `CategoryTreeSidebar.tsx`, `useCategoriesTree.ts`, and `routes/share/$token.tsx`.

### 1.3 `TagRead.group` does not exist on the shipped wire

Both the 43.1 sketch and Decision AW (`architecture.md:3209`) say *"`TagRead`: add `group`/`group_id`(+`group_position`)"*. The **shipped** 42.2 backend `TagRead` (`sot/schemas.py:35-47`) carries **only** `group_id` + `group_position`; decision **D-SHAPE-1** in that file states the human group label/slug is **NOT embedded** — it is delivered authoritatively by `GET /api/tag-groups`. Adding a `group` field to the FE type would mirror a field the server never sends. The additive type must add `group_id` + `group_position` **only**.

**Conclusion:** the literal sketch is a stale pre-relocation artifact. The correct-course that re-scoped E42→E47 updated the E42/E47 epic bodies and Decision AV/AW headers but left the **E43 story sketches** and **Decision AW § Frontend types bullet** unamended. This is a load-bearing planning contradiction between two approved artifacts → `BLOCKED_PROCEDURAL`, not a dev-go.

---

## 2. Dependency audit — production consumers of category types/fields/hooks

Enumerated across `apps/web/src` (production only; `*.test.tsx` fixtures listed separately as non-blocking). Retiring-story column keyed to `epics.md`/SCP ownership.

| FE symbol (in `api-types.ts` unless noted) | Production consumers (file:line) | Still shipped by backend? | Retires in |
|---|---|---|---|
| `CategorySummary` (type) | `ModelHero.tsx:5,39,41,44,74,80` (breadcrumb chain from `detail.category`); embedded in `ModelDetail.category` | **yes** (`sot/schemas.py:18`; `ModelDetail`) | **47.5** (atomic w/ backend drop) |
| `ModelDetail.category` (field) | `ModelHero.tsx:75,77,78` (`detail.category`) | **yes** | **47.5** |
| `ModelSummary.category_id` (field) | `useModels.ts` filter param path; `routes/dev/components.tsx:21` fixture object; wire mirror | **yes** | **47.5** |
| `CategoryNode` (type) | `AddModelForm.tsx:12,53-54`; `CatalogList.tsx:5,259,267,269,276`; `CategoryTreeSidebar.tsx:5,84`; `ModelHero.tsx:5,27-31,40,76` | **yes** (`sot/schemas.py:26`) | consumers: 44.1 / 44.3 / 45.2 / 45.3; **FE type delete owner = 47.4** (resolved §5 decision 3 / applied `epics.md:4352` + Decision AW `:3212`) |
| `CategoryTree` (type) | `useCategoriesTree.ts:4,7,9`; `CatalogList.tsx:5,259`; `CategoryTreeSidebar.tsx:5,11,21` | **yes** (`sot/schemas.py:31`) | same as `CategoryNode` |
| `useCategoriesTree` (hook, `hooks/useCategoriesTree.ts`) | `AddModelForm.tsx:13,81`; `CatalogList.tsx:9,33`; `ModelHero.tsx:13,66` | live `GET /api/categories` bridge | **43.2 sketch says "retire" — BLOCKED by same coupling**; consumers migrate in 44.3 (CatalogList) / 45.2 (ModelHero) / 45.3+47.5 (AddModelForm) |
| `ShareModelView.category` → `data.category` | `routes/share/$token.tsx:509` | **yes** (`share/router.py:144,228` emits `category=category.slug`) | **47.5** |
| `CategoryTreeSidebar` (component) | catalog browse (`CatalogList.tsx:143,164`) | n/a | **44.1** (replaced by `FacetSidebar`) |
| `AddModelForm` category selector | admin new-model (`AddModelForm.tsx:34,45,89,146,191-196`) | n/a | **45.3**, deploy-coupled to **47.5** same-`main`-HEAD (`epics.md:4304`) |

**Test-fixture-only references** (non-blocking, retired with their stories, not by 43.1): `CategoryTreeSidebar.test.tsx`, `useCategoriesTree.test.tsx`, `ModelHero.test.tsx`.

**Verdict:** the controller finding is **CONFIRMED**. No category type/field/hook is free to delete in E43; every one is load-bearing until an E44/E45/47.x consumer-removal story lands, and the FE-type drops of `CategorySummary`/`category`/`category_id` are already owned atomically by **47.5**.

---

## 3. Safe additive scope (the implementable-green re-scope) — recommended GREEN target

This is what 43.1 **should** deliver once the planning correction (§5) is approved. It is purely additive, mirrors the **shipped** 42.2 wire exactly, and breaks nothing.

### 3.1 Extend `TagRead` (additive — no `group`)

```ts
export interface TagRead {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
  group_id: string | null;   // NEW (42.2) — facet membership FK; null = groupless
  group_position: number;    // NEW (42.2) — order within group
}
```

Existing `TagRead[]` consumers (`useTags`, `ModelSummary.tags`, `ModelDetail.tags`) stay green — the two new keys are additive and already arrive on every model response (`sot/schemas.py:40-45`).

### 3.2 Add the tag-group read/response types (currently missing)

Mirror `sot/schemas.py:50-101` exactly:

```ts
// GET /api/tags item — TagRead + OPT-IN model_count (present only with ?with_counts=true;
// the backend serializer DROPS the key when absent, so it is optional, never null).
export interface TagListItem extends TagRead {
  model_count?: number;
}

// Per-tag entry inside GET /api/tag-groups — model_count always computed (required).
export interface TagReadWithCount extends TagRead {
  model_count: number;
}

export interface TagGroupRead {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
  position: number;
  tags: TagReadWithCount[];
}

// GET /api/tag-groups response.
export interface TagGroupsResponse {
  groups: TagGroupRead[];
  groupless: TagReadWithCount[];
}
```

### 3.3 (Required, additive) admin write-response type for 42.4

`TagGroupSummary` (flat, no `tags[]`) mirrors `sot/schemas.py:92-101`, returned by the 42.4 `POST/PATCH /api/admin/tag-groups` write path. **In scope for 43.1** — the applied SoT lists it as a type to add in the 43.1 additive set (`epics.md:4260` "Add the shipped read/response types … and `TagGroupSummary`"; Decision AW `architecture.md:3210` names it in the shipped group-read/response set). Additive, zero risk, keeps the shipped 42.x wire contract complete; its downstream consumer is the E46 admin screen.

```ts
export interface TagGroupSummary {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
  position: number;
}
```

### 3.4 Explicitly PRESERVED (do NOT touch in 43.1)

`CategorySummary`, `CategoryNode`, `CategoryTree`, `ModelSummary.category_id`, `ModelDetail.category` — all still match the live wire and have live consumers (§2). Their removal is owned by **47.5** (types/fields) and the E44/E45 consumer-migration stories (`CategoryNode`/`CategoryTree` follow their last consumer). A `// Initiative 25: retained until 47.5 / consumer migration` marker comment is the only category-line change permitted here.

---

## 4. Acceptance criteria (additive re-scope)

1. `TagRead` carries `group_id: string | null` and `group_position: number`; **no** `group` field is added.
2. `TagListItem`, `TagReadWithCount`, `TagGroupRead`, `TagGroupsResponse`, and `TagGroupSummary` exist and match `sot/schemas.py:50-101` field-for-field (nullability included). `TagListItem.model_count` is `?: number` (optional, never `| null`); `TagGroupSummary` is the flat `{ id, slug, name_en, name_pl: string | null, position }` (no `tags[]`).
3. All five preserved category symbols (§3.4) remain unchanged and exported.
4. A new type-level test (`apps/web/src/lib/api-types-tags.test.ts`) proves the exact shapes with `expectTypeOf` — **no `as`, no `any`, no unsafe casts** (mirrors the existing `api-types-profile-source.test.ts` convention). It must assert, at minimum:
   - `TagRead["group_id"]` `toEqualTypeOf<string | null>()`; `TagRead["group_position"]` `toEqualTypeOf<number>()`.
   - `TagListItem["model_count"]` `toEqualTypeOf<number | undefined>()`; `TagReadWithCount["model_count"]` `toEqualTypeOf<number>()`.
   - `TagGroupsResponse` `toEqualTypeOf<{ groups: TagGroupRead[]; groupless: TagReadWithCount[] }>()` (structural).
   - `TagGroupSummary` `toEqualTypeOf<{ id: string; slug: string; name_en: string; name_pl: string | null; position: number }>()` (flat, no `tags[]`).
   - A literal fixture built from a real 42.2 `GET /api/tag-groups` JSON body assigned via `satisfies TagGroupsResponse` (compile-time wire-shape proof, no cast).
5. Green gates: `npm run typecheck` (`tsc -b`), `npm run lint` (already pins `--max-warnings=0`), `npm run test` (vitest) all pass; no change to `test:visual` (no UI touched). Backend untouched. `git diff --check` clean.
6. TDD: the type-level test is written RED first (types absent) → GREEN after the additions (mirrors the `// RED:` convention in the existing type test). **The RED manifests under `npm run typecheck` (`tsc -b`, which compiles `src/**/*.test.ts` per `tsconfig.json:include`): a `type`-only import of a not-yet-exported type is an unresolved-import error, and any `expectTypeOf`/`satisfies` mismatch is a type error — both fail `tsc`. `npm run test` (vitest run, no `--typecheck`) is NOT the RED gate: esbuild erases `import type` + `expectTypeOf` at runtime, so it would pass green even with the types absent. Precedent: `api-types-profile-source.test.ts` (Story 35.5) uses this exact pattern.**

---

## 5. Required planning correction — APPROVED + APPLIED 2026-07-19

Native BMAD required a `bmad-correct-course` before 43.1 could be flipped to ready, because the fix amends approved artifacts (`epics.md` E43 sketches + `architecture.md` Decision AW). Proposed in `sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md` — now **APPROVED / APPLIED** (operator decision 2026-07-19). The three decisions below were all approved as recommended (decision 3 owner = **47.4**); the amendments are live in `epics.md`/`architecture.md`. Exact operator decisions (for the record):

1. **Re-scope E43 story sketches to additive-only.**
   - **43.1** = §3 above (add `group_id`/`group_position` + tag-group types; **keep** all category types).
   - **43.2** = add `useTagGroups()` + type `useTags` as `TagListItem[]`; **do NOT retire `useCategoriesTree`** until its consumers migrate (44.3/45.2/45.3) — the 43.2 sketch is blocked by the same coupling.
   - **43.3** = additive URL state for `tag_ids`/`tag_match`/`untagged`; **keep** the `category_id` URL param until `CatalogList` migrates in 44.3.
2. **Correct Decision AW § Frontend types (`architecture.md:3208-3211)`:** (a) `TagRead` adds `group_id` + `group_position` **only** — strike `group` (shipped 42.2 D-SHAPE-1 does not embed it); (b) relocate the "remove `CategorySummary` / `category_id` / `category`" bullet to **47.5** (already the owner); (c) note the shipped read types (`TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`).
3. **Assign the FE `CategoryNode`/`CategoryTree` type-deletion + `useCategoriesTree` hook-deletion owner.** They follow their last consumer (`CatalogList` 44.3, `ModelHero` 45.2, `AddModelForm` 45.3). Recommendation: fold the FE-type + hook deletion into **47.4** (which already removes the backend route-only `CategoryNode`/`CategoryTree` schemas) or the 44.3/45.x cleanup, so FE↔BE symmetry is explicit. Operator picks the owner; this is a **planning-ownership** reassignment, not implementation. **→ APPROVED 2026-07-19: owner = 47.4** (the recommended option; FE `CategoryNode`/`CategoryTree` types + `useCategoriesTree` hook delete after all E44/E45 consumers migrate — now reflected in `epics.md` 47.4 + Decision AW).

No destructive-go, no data decision, and no code change is requested by this story — only the additive type surface and the sketch/Decision-AW correction.

---

## 6. Convention & fence notes

- **Manual typing, no codegen.** `api-types.ts` is hand-maintained ("Keep this file in sync by hand", header). There is **no** `api-types.gen.ts` and **no** OpenAPI generation pipeline in the repo (the `architecture.md:2753` `api-types.gen.ts` reference is inaccurate/aspirational, scoped to a different Initiative's prose). 43.1 must **not** introduce speculative OpenAPI codegen — additive hand-typed interfaces only.
- **Type-test convention:** vitest `expectTypeOf` in `src/lib/*.test.ts` (precedent: `api-types-profile-source.test.ts`). This is the "compile-time proof without unsafe casts" the audit requires.
- **Scope fences honored:** frontend data types only. No hooks (`useTagGroups` is 43.2), no URL state (43.3), no UI, no backend, no category-endpoint/ORM/migration change.

---

## 7. Verification performed for this spec

- `bmad-help` run (mandatory session start) → canonical route confirmed: `bmad-create-story` (CS/create), phase 4-implementation, preceded-by `bmad-sprint-planning` (done), followed-by `bmad-create-story:validate`.
- Shipped wire read from `apps/api/app/modules/sot/schemas.py:35-101` (42.2, `done`) — `group` absence, `TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse` shapes, nullability.
- Live category emission confirmed: `share/router.py:144,228`; `ModelDetail.category` / `ModelSummary.category_id` still in backend schemas.
- Consumer enumeration by `grep` across `apps/web/src` (§2).
- No pre-existing `43-1-*` artifact (fresh create).

---

## 8. Validation record — native `bmad-create-story:validate` (VS), 2026-07-19

**Verdict: PASS** (independent fresh-context validator; controller Laura). Story now mirrors the shipped 42.2 wire and the applied additive SoT; RED→GREEN strategy is executable under the real `tsc -b`/vitest config; scope fences and category-owner assignments match the operator-approved correct-course.

**Findings (all fixed in-place — spec-only edits, no production/test code touched):**

1. **[important — SoT-consistency] `TagGroupSummary` was marked "Optional" (§3.3) and omitted from the ACs**, but the applied SoT lists it in-scope for 43.1 in **both** governing artifacts (`epics.md:4260` "Add the shipped read/response types … and `TagGroupSummary`"; Decision AW `architecture.md:3210`). Per the applied plan it is a required 43.1 deliverable. **Fixed:** §3.3 re-titled *(Required, additive)*; AC #2 extended to `TagGroupSummary` (`sot/schemas.py:50-101`); AC #4 adds its flat-shape `expectTypeOf` assertion.
2. **[minor — stale audit] §2 table** listed the `CategoryNode`/`CategoryTree` FE-type-delete owner as "UNASSIGNED", contradicting §5 decision 3 and the applied `epics.md:4352` + Decision AW `:3212` (owner = **47.4**). **Fixed:** owner set to 47.4.
3. **[minor — dev-clarity] AC #5/#6 RED gate** was ambiguous: `expectTypeOf`/`satisfies` are compile-time only, so `npm run test` (vitest run, no `--typecheck`) passes green even with types absent — the RED is delivered by `npm run typecheck` (`tsc -b`, which compiles `src/**/*.test.ts`). **Fixed:** AC #6 states the RED gate explicitly and cites the 35.5 precedent; AC #5 corrects the lint command to `npm run lint` (the script already pins `--max-warnings=0`).

**Independently verified against source (no defects):**

- **Shipped backend schemas** (`sot/schemas.py:35-101`): `TagRead` = `group_id: UUID|None` + `group_position: int`, **no** embedded `group` (D-SHAPE-1) ✓; `TagListItem.model_count: int|None` with serializer dropping the key when absent → FE `?: number`, never `| null` ✓; `TagReadWithCount.model_count: int` required ✓; `TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary` exact ✓. Story §3 mirrors all.
- **Current FE `api-types.ts`**: `TagRead` still 4-field (RED baseline correct); the 5 preserved category symbols (`CategorySummary`/`CategoryNode`/`CategoryTree`/`ModelSummary.category_id`/`ModelDetail.category`) are present and match the live wire; owners 47.4 (tree types + `useCategoriesTree` hook) / 47.5 (model DTO + field + ORM/`0019`, destructive-go deferred) match the applied SoT.
- **Type config**: `tsconfig.json` — `strict` on, `include: ["src","tests"]` (test files typechecked), `noUncheckedIndexedAccess` on but does NOT affect known-literal-key indexed access (`TagRead["group_id"]` = `string | null` exactly); **`exactOptionalPropertyTypes` is NOT set**, so `TagListItem["model_count"]` = `number | undefined` and the AC #4 assertion holds. `satisfies` fixture compiles only once the type exists → meaningful RED.
- **Name collisions**: `grep` across `apps/web/src` — none of `TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary`/`useTagGroups` exist yet; names match the backend exactly.
- **Scope fences**: deliverables limited to `api-types.ts` + one new type-test (`api-types-tags.test.ts`) + story/status — no hooks (`useTagGroups` = 43.2), no URL state (43.3), no UI, no backend, no migration.
- **Gates**: `git diff --check` clean; `sprint-status.yaml` well-formed. Validation edits are tracked-doc only (story artifact + sprint-status), per the VS remit.

---

## 9. Tasks / Subtasks — dev execution (native `bmad-dev-story`, 2026-07-19)

- [x] **T1 — RED first (TDD).** Author `apps/web/src/lib/api-types-tags.test.ts` (type-level, `expectTypeOf`; no `as`/`any`/unsafe cast) before any production change. Assert `TagRead["group_id"]`=`string|null`, `TagRead["group_position"]`=`number`, `TagListItem["model_count"]`=`number|undefined`, `TagReadWithCount["model_count"]`=`number`, `TagGroupRead` shape, `TagGroupsResponse` structural equality, flat `TagGroupSummary` (no `tags[]`), plus a literal `satisfies TagGroupsResponse` 42.2 wire fixture.
  - [x] Capture RED under `npm run typecheck` (`tsc -b`): 5 unresolved-export errors (`TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary`, TS2305) + 2 missing-field errors on `TagRead` (`group_id`/`group_position`, TS2339). Evidence `.hermes/run-logs/e43.1-red-typecheck.log`.
- [x] **T2 — GREEN production types (additive).** In `apps/web/src/lib/api-types.ts`: extend `TagRead` with `group_id: string | null` and `group_position: number` (NO embedded `group`, per 42.2 D-SHAPE-1); add exported `TagListItem` (`model_count?: number`), `TagReadWithCount` (`model_count: number`), `TagGroupRead`, `TagGroupsResponse`, `TagGroupSummary` (flat) — each field-for-field against `sot/schemas.py:35-101`.
- [x] **T3 — Preserve category surface.** `CategorySummary`, `CategoryNode`, `CategoryTree`, `ModelSummary.category_id`, `ModelDetail.category` unchanged (only a non-behavioural Initiative-25 retention marker comment added on the Categories header, permitted by §3.4).
- [x] **T4 — Green gates.** Focused vitest PASS (8); `npm run typecheck` PASS; `npm run lint` PASS (`--max-warnings=0`); full `npm run test` PASS (123 files / 656 tests); full web production build (`npm run build`, `tsc -b && vite build`) PASS. No visual-baseline regen (no UI change).

## 10. Dev Agent Record

### 10.1 Debug Log

| Phase | Command | Result |
|---|---|---|
| RED | `npm run typecheck` | FAIL — TS2305 ×5 (missing exports) + TS2339 ×2 (missing `TagRead.group_id`/`group_position`). Meaningful RED. |
| GREEN focused | `npx vitest run src/lib/api-types-tags.test.ts` | PASS (8) |
| GREEN typecheck | `npm run typecheck` (`tsc -b`) | PASS |
| Lint | `npm run lint` | PASS — "ESLint: No issues found" |
| Full unit | `npm run test` (`vitest run`) | PASS — 123 files / 656 tests |
| Build | `npm run build` (`tsc -b && vite build`) | PASS (exit 0; only pre-existing route-file/sentry/chunk-size warnings) |

Logs under `.hermes/run-logs/e43.1-*.log` (gitignored).

### 10.2 Completion Notes

- Additive-only per §3–§4. `TagRead` gains `group_id`/`group_position` **only**; five tag/tag-group interfaces added; all five category symbols preserved. Manual typing, no codegen.
- **Required mechanical fallout (scope note for controller):** making `TagRead.group_id`/`group_position` REQUIRED (matching the non-optional backend wire) forces every hand-constructed `TagRead` literal to supply the two new keys, else `tsc -b` is RED (AC #5 mandates green). `tsc` enumerated exactly **five** such construction sites — four test fixtures (`ModelHero.test.tsx`, `ModelCard.test.tsx`, `FilterRibbon.test.tsx`, `EditTagsSheet.test.tsx`) and one dev-only showcase route (`routes/dev/components.tsx`, `/dev/components` mock `FAKE_MODEL`). **No** production hook/component/route builds a `TagRead` literal, so no feature surface was touched. Each site received data-only `group_id: null, group_position: 0` (faithful "groupless" defaults). This is the unavoidable tail of the sanctioned additive type change, not scope expansion (no hooks / URL state / feature UI / locales / backend / migration / generated route tree). Flagged for controller veto if a different resolution is preferred.
- RED gate is `tsc` (compile-time), not `vitest run` — esbuild erases `import type`/`expectTypeOf` at runtime (per AC #6 + Story 35.5 precedent).
- Controller rerun: `npm run typecheck`, focused type test **8/8**, and `npm run lint` all PASS; explicit source guard confirmed all category compatibility exports/fields remain and no embedded `group` exists.
- Fresh native BMAD adversarial review: **APPROVE** (`critical=0`, `important=0`, `minor=2` non-blocking type-test hardening notes). Report: `.hermes/run-logs/e43.1-native-review.md`; independent focused review rerun **36/36**.
- Aider full-diff review found no concrete defect but ended `REQUEST_CHANGES` asking for a manual audit of direct `TagRead` constructions. Controller triage closed it with full `tsc -b` plus explicit source search: only the updated fixture/dev sites construct `TagRead`; no code change owed.
- Full repo `infra/scripts/check-all.sh`: **16/16 green**, including web Vitest **656 passed** and visual regression **464 passed / 24 skipped**. Evidence: `.hermes/run-logs/e43.1-check-all.log`.

## 11. File List

Changed (tracked, uncommitted on `feat/E43.1-api-types`):

- `apps/web/src/lib/api-types.ts` — additive `TagRead` fields + 5 new tag-group interfaces + Categories retention comment (core deliverable).
- `apps/web/src/routes/dev/components.tsx` — dev-showcase mock `TagRead` literals: +`group_id`/`group_position` (required fallout).
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` — test fixture tags: +2 fields (required fallout).
- `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` — test fixture tags: +2 fields (required fallout).
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` — `makeTag` fixture: +2 default fields (required fallout).
- `apps/web/src/ui/custom/ModelCard.test.tsx` — test fixture tags: +2 fields (required fallout).

New (untracked, intended):

- `apps/web/src/lib/api-types-tags.test.ts` — RED-first type-level test (the story's mandated deliverable).

Docs (tracked): this story artifact; `sprint-status.yaml` (epic-43 → in-progress, 43-1-api-types → review).

## 12. Change Log

| Date | Change |
|---|---|
| 2026-07-19 | Native `bmad-dev-story` executed on branch `feat/E43.1-api-types` (baseline `main` @ 5b5da8c). Additive facet-tag FE types implemented RED→GREEN; five required-fallout `TagRead` construction sites updated; all gates green (typecheck/lint/vitest 656/build). Status → `review`; left uncommitted for controller review. |
