# Sprint Change Proposal — E43 frontend-data-layer additive correction

- **Status:** **APPROVED / APPLIED** (operator-approved 2026-07-19; applied same day via native `bmad-correct-course`). Authored by Claude/BMAD create-story dependency audit for Story 43.1; controller Laura.
- **Operator decision (2026-07-19):** Approved the recommended **additive** E43 correction (§2.1/§2.2). Confirmed the FE `CategoryNode`/`CategoryTree` type + `useCategoriesTree` hook deletion owner = **Story 47.4**, after all E44/E45 consumers migrate (§2.3, the recommended owner). No destructive-go granted; no new story IDs; no FR/NFR change.
- **Applied paths (2026-07-19 via `bmad-correct-course`):**
  - `_bmad-output/planning-artifacts/epics.md` — E43 goal + `Depends on` + additive correct-course note; 43.1/43.2/43.3 sketches re-scoped additive; 47.4 sketch extended to own the FE `CategoryNode`/`CategoryTree` type + `useCategoriesTree` hook cleanup (47.5 model-DTO/field drops unchanged).
  - `_bmad-output/planning-artifacts/architecture.md` — Decision AW § Frontend types rewritten (strike `group`; `group_id`+`group_position` only; shipped group-read types documented; category removals relocated to 47.4 tree-types/hook + 47.5 model DTO/field); new "Update 2026-07-19 (E43)" note appended to Decision AW.
  - `_bmad-output/implementation-artifacts/43-1-api-types.md` — story status flipped `BLOCKED_PROCEDURAL` → `ready-for-validation` (additive spec; audit history + approval record preserved).
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — 43.1 comment updated to the applied additive re-scope; epic-43 / 43.2 / 43.3 / 47.4 / 47.5 stay `backlog`; destructive-go stays DEFERRED.
- **Date:** 2026-07-19
- **Trigger:** `bmad-create-story` (Create) for Story 43.1 found the approved E43 story sketches non-implementable-green — they mandate destructive category-type removals that this same initiative's approved 2026-07-19 correct-course (`sprint-change-proposal-2026-07-19-e42-deferred-coupled-cutover.md`) relocated to E47/47.5. This is a planning-artifact contradiction, not a code decision.
- **Change class:** MINOR (planning re-scope + doc correction; no new story IDs, no FR/NFR change, no architecture decision reversal — it *aligns* E43 with the already-approved E42→E47 relocation).
- **Companion evidence:** `_bmad-output/implementation-artifacts/43-1-api-types.md` (full dependency audit).

## 1. Problem

The 2026-07-19 correct-course re-scoped E42 to the **additive** backend contract and relocated all category-**destructive** work to E47 (47.4 API-surface, 47.5 ORM+DTO+`0019` atomic, destructive-go deferred). It updated the E42/E47 epic bodies and Decision AV/AW headers — but left stale:

1. **`epics.md` E43 story sketches** (43.1/43.2/43.3) still prescribe destructive removals:
   - 43.1 (`epics.md:4258`): *"`ModelSummary`/`ModelDetail` drop `category_id` and `category`; remove `CategorySummary`/`CategoryNode`/`CategoryTree`."*
   - 43.2 (`epics.md:4262`): *"retire `useCategoriesTree`."*
2. **`architecture.md` Decision AW § Frontend types** (`:3208-3211`): *"`TagRead`: add `group`/`group_id`(+`group_position`); `ModelSummary`/`ModelDetail`: remove `category_id` and `category`; remove `CategorySummary`, `CategoryNode`, `CategoryTree`."*

Both contradict the approved relocation (47.5 owns those FE type/field drops; *"Keeps alive: `CategorySummary`, `…Detail.category(_id)`"*, SCP line 83) and the still-live category API bridge (`epics.md:4254`). They are **impossible to implement green** — the backend still ships `category` on the wire and six production FE consumers depend on the types (audit §2 of the story artifact). Additionally, the `TagRead.group` field named in both artifacts **was never shipped** — 42.2's `TagRead` (`sot/schemas.py:35-47`, D-SHAPE-1) carries only `group_id` + `group_position`.

## 2. Recommended minimal correction

### 2.1 Re-scope E43 story sketches to additive-only (`epics.md` §Initiative 25 E43)

| Story | Corrected additive sketch |
|---|---|
| **43.1 types** | `TagRead` gains `group_id` + `group_position` (**not** `group`). Add `TagListItem`, `TagReadWithCount`, `TagGroupRead`, `TagGroupsResponse` (and optionally `TagGroupSummary`) mirroring shipped 42.2. **Keep** `CategorySummary`/`CategoryNode`/`CategoryTree`/`ModelSummary.category_id`/`ModelDetail.category` (still live). |
| **43.2 hooks** | Add `useTagGroups()`; type `useTags` as `TagListItem[]`. **Do not** retire `useCategoriesTree` — its consumers (`CatalogList` 44.3, `ModelHero` 45.2, `AddModelForm` 45.3) survive E43; hook deletion moves to §2.3. |
| **43.3 url state** | Additive URL params `tag_ids`/`tag_match`/`untagged`. **Keep** `category_id` param until `CatalogList` migrates in 44.3. |

### 2.2 Correct `architecture.md` Decision AW § Frontend types (`:3208-3211`)

- `TagRead`: add `group_id` + `group_position` **only** — strike `group` (shipped 42.2 D-SHAPE-1 does not embed the group label).
- Move "remove `CategorySummary` / `ModelSummary.category_id` / `ModelDetail.category`" to **47.5** (already the owner; the atomic BE+FE cutover).
- Add the shipped read types (`TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`) to the FE-types list.

### 2.3 Assign the deferred FE category-type + hook deletions to explicit owners

| FE symbol | Recommended owner |
|---|---|
| `CategorySummary` (type), `ModelDetail.category`, `ModelSummary.category_id`, `data.category` | **47.5** (already owns — atomic w/ backend drop, deferred destructive-go) |
| `CategoryNode`, `CategoryTree` (types) | after last consumer (44.3 / 45.2 / 45.3); final FE-type delete folded into **47.4** (which already removes the BE route-only `CategoryNode`/`CategoryTree`) — **operator confirm** |
| `useCategoriesTree` (hook) | after `CatalogList` (44.3) + `ModelHero` (45.2) + `AddModelForm` (45.3) migrate; delete with **47.4** cleanup — **operator confirm** |

## 3. Exact operator decisions required

1. Approve the E43 sketch re-scope (§2.1) — additive-only 43.1/43.2/43.3.
2. Approve the Decision AW § Frontend-types correction (§2.2) — drop `group`, relocate category removals to 47.5, add shipped read types.
3. Confirm the owner for the FE `CategoryNode`/`CategoryTree` type + `useCategoriesTree` hook deletion (§2.3 — recommend 47.4).

## 4. What this proposal does NOT do

- No new story IDs; no FR/NFR change; no architecture decision reversal; no destructive-go; no code change. It aligns stale sketches with the already-approved relocation and the shipped 42.2 wire.
- Applying §2.1/§2.2 to `epics.md`/`architecture.md` is deferred until operator approval (vanilla-first: no direct artifact edits that bypass an approved correct-course route).

## 5. Route on approval — APPLIED 2026-07-19

`bmad-correct-course` applied §2.1 (E43 sketches, `epics.md`) + §2.2 (Decision AW § Frontend types, `architecture.md`) + §2.3 (FE `CategoryNode`/`CategoryTree` type + `useCategoriesTree` hook deletion → **47.4**). Story 43.1 flipped `BLOCKED_PROCEDURAL` → `ready-for-validation`. **Next native route:** `bmad-create-story:validate` on the corrected additive 43.1 (VS), then dev-go. The category surface stays the zero-code compatibility bridge; no destructive-go granted.
</content>
