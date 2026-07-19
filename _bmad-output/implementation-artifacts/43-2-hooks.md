---
baseline_commit: 52868c054c999088178cec75baef567869d602f8
---

# Story 43.2 — Hooks: `useTagGroups()` + `useTags` re-type (FR25-BROWSE-1, FR25-DETAIL-1)

- **Epic:** E43 — Frontend data layer (Initiative 25 — Facet Tag Taxonomy + Category Retirement)
- **Status:** `ready-for-dev` — authored via native `bmad-create-story` (Create) after mandatory `bmad-help`; independent native `bmad-create-story:validate` (VS) ran and returned **PASS** on 2026-07-19 (RED strategy empirically verified against expect-type 1.3.0; RED hardened with the framework-independent `model_count` member-access; 0 critical). Next native route: `bmad-dev-story` (controller Laura owns dev-go). Specification only — no production/test code changed by this run.
- **Author:** Claude (BMAD create-story). **Controller:** Laura.
- **Created:** 2026-07-19 via native `bmad-create-story` (Create), phase 4-implementation; preceded-by `bmad-sprint-planning` (done), followed-by `bmad-create-story:validate`.
- **Scope class:** frontend data-layer **hooks only** (`apps/web/src/modules/catalog/hooks/`). One new hook + one existing-hook re-type + their colocated vitest tests. **No** URL state (43.3), UI/components (E44/E45), backend, migration, locale, route tree, visual baseline, package/lock, or codegen change.
- **Sources of truth:** `epics.md` §Initiative 25 E43 / Story 43.2 (`:4250-4264`, additive re-scope); `architecture.md` Decision AW § Frontend types + § Default-deny auth posture + both 2026-07-19 correct-course Updates (`:3188-3250`); SCP `sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md` (APPROVED/APPLIED); shipped 42.2 backend read surface (`apps/api/app/modules/sot/router.py:67-121`, `schemas.py:35-101`, `tests/test_sot_auth_boundary.py:139-196`); shipped 43.1 FE types (`apps/web/src/lib/api-types.ts:67-115`, story `43-1-api-types.md` — `done`).

---

## 1. Story statement

**As** the catalog frontend (browse/detail surfaces and, later, the facet sidebar),
**I want** a typed `useTagGroups()` query hook backed by the shipped `GET /api/tag-groups` endpoint, and the existing `useTags` hook re-typed to the exact shipped `GET /api/tags` item shape (`TagListItem`),
**so that** E44 (`FacetSidebar`, `FilterRibbon`) and E45 (card/detail/edit) can consume the facet taxonomy and per-tag data through the repo's standard TanStack-Query data layer without any component reaching for `fetch` or an inaccurate type.

**Business value / FR mapping:** FR25-BROWSE-1 (facet browse needs the group→tags tree in one round-trip) and FR25-DETAIL-1 (tags carry facet membership). This is the **additive** hook layer of E43 — it adds `useTagGroups()` and corrects the `useTags` return type **alongside** the still-live category hook. **No category hook, type, or field is removed** (E43 is the zero-code compatibility bridge; `useCategoriesTree` deletion is owned by 47.4 after its last consumer migrates in 44.3/45.2/45.3).

---

## 2. Additive scope — the implementable-green target

Three deliverables, all additive, all mirroring the **shipped** 42.2 wire and the shipped 43.1 types exactly. Nothing is removed.

### 2.1 NEW — `useTagGroups()` (`apps/web/src/modules/catalog/hooks/useTagGroups.ts`)

Mirrors the `useCategoriesTree` hook shape (the nearest single-shot, param-less, `sot`-context read) exactly — same import surface, same `useQuery` shape, same `staleTime`:

```ts
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagGroupsResponse } from "@/lib/api-types";

export function useTagGroups() {
  return useQuery<TagGroupsResponse>({
    queryKey: ["sot", "tag-groups"],
    queryFn: () => api<TagGroupsResponse>("/tag-groups"),
    staleTime: 5 * 60 * 1000,
  });
}
```

- **No parameters** — the endpoint (`sot/router.py:117-121`) takes none (`session` + `current_user` only); the whole taxonomy is one round-trip.
- **Return type** is inferred by TanStack Query from the `useQuery<TagGroupsResponse>` type argument: `result.data` is `TagGroupsResponse | undefined`, `result.isLoading`/`isError`/`error` per the standard `UseQueryResult`. No wrapper type, no `select` transform (the wire already matches `TagGroupsResponse` field-for-field from 43.1).

### 2.2 UPDATE — `useTags` return/query type `TagRead[]` → `TagListItem[]` (`apps/web/src/modules/catalog/hooks/useTags.ts`)

The only change is the generic type argument on `useQuery` and `api`, plus the `import type`. **The request behaviour is preserved verbatim** — same `q`/`limit` params, same query key, same `staleTime`:

```ts
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagListItem } from "@/lib/api-types"; // was: TagRead

const DEFAULT_LIMIT = 50;

export function useTags(q?: string) {
  const params = new URLSearchParams();
  if (q !== undefined && q.length > 0) params.set("q", q);
  params.set("limit", String(DEFAULT_LIMIT));
  const path = `/tags?${params.toString()}`;
  return useQuery<TagListItem[]>({                 // was: useQuery<TagRead[]>
    queryKey: ["sot", "tags", q ?? ""],            // UNCHANGED
    queryFn: () => api<TagListItem[]>(path),        // was: api<TagRead[]>
    staleTime: 5 * 60 * 1000,                       // UNCHANGED
  });
}
```

- **Why `TagListItem[]` is the exact shape:** the endpoint's `response_model` is `list[TagListItem]` (`sot/router.py:85`). `TagListItem extends TagRead` (43.1, `api-types.ts:84-87`), so every returned entry carries `group_id`/`group_position` (from `TagRead`) plus the **optional** `model_count?: number`. `useTags` does **not** pass `with_counts=true`, so the backend serializer drops the `model_count` key (42.2 D-RESPONSEMODEL-1) — which the `?:` optional models correctly (never `| null`). No runtime transform is added; the type is simply made honest.
- **No `with_counts` param** is introduced here — it is out of scope (no consumer needs counts through `useTags` yet; the facet sidebar's counts come from `useTagGroups`/`GET /api/tag-groups`). Adding it would be speculative (Ponytail rung 1).

### 2.3 PRESERVE — `useCategoriesTree` unchanged (`apps/web/src/modules/catalog/hooks/useCategoriesTree.ts`)

**Do NOT touch** the file, its export, its `["sot", "categories"]` key, or its colocated `useCategoriesTree.test.tsx`. Its production consumers (`AddModelForm.tsx`, `CatalogList.tsx`, `ModelHero.tsx` — audited in `43-1-api-types.md` §2) survive all of E43; the hook deletion is owned by **47.4** after the last consumer migrates (44.3 `CatalogList` / 45.2 `ModelHero`/detail / 45.3 `AddModelForm`). Removing or editing it now is a live-consumer compile break and contradicts the operator-approved additive correct-course.

---

## 3. Resolved contract questions (code-first)

The eight controller questions, each resolved against the actual repo, not convention memory.

### Q1 — Exact query key + `staleTime` for `useTagGroups`

- **Query key: `["sot", "tag-groups"]`.** Repo convention (project-context §69; verified across `useModels`/`useModel`/`useFiles`/`usePhotos`/`useCategoriesTree`) is an **inline** `["<bounded-context>", "<entity>", ...filters]` array — there is **no** query-key factory in the repo (confirmed: `grep -rn queryKeys/keyFactory` → none). The bounded context is `sot`; the entity segment mirrors the URL path segment exactly as `useCategoriesTree` mirrors `/categories` → `["sot", "categories"]`, so `/tag-groups` → `["sot", "tag-groups"]`. **No factory is introduced** (Ponytail rung 3 — no abstraction for one call site).
- **`staleTime: 5 * 60 * 1000` (5 min).** Contract-pointing justification (project-context §287): the facet taxonomy is **admin-governed, slowly-changing reference data** — tag-groups mutate only through the 42.4 admin governance endpoints (`POST/PATCH/DELETE /api/admin/tag-groups`), never on the member browse path. A 5-minute staleness budget between an admin edit and a member's automatic refetch is acceptable for a facet sidebar; it matches the sibling taxonomy read (`useCategoriesTree`, `useTags`) so the whole `sot`-taxonomy family stays coherent. **Future invalidation:** when the admin tag-group UI lands (E46), its mutations `invalidateQueries({ queryKey: ["sot", "tag-groups"] })` (and `["sot", "tags"]`) to force-fresh — the stable, path-mirroring key above is exactly what makes that one-line invalidation possible. No proactive invalidation wiring is built now (no admin FE mutation exists yet — Ponytail rung 1/4).

### Q2 — Exact request path through `api()`

`api<TagGroupsResponse>("/tag-groups")`. `lib/api.ts` prepends `const BASE = "/api"` to every call, so the emitted request is **`/api/tag-groups`** (verified: `fetch(\`${BASE}${path}\`, …)`, `api.ts:32`). The hook passes the path **without** the `/api` prefix, exactly like every sibling hook (`useCategoriesTree` passes `/categories`, `useTags` passes `/tags?…`).

### Q3 — Parameters + return-type inference

- **No parameters.** Recommended and adopted: the endpoint has none, so `useTagGroups()` takes no args. (Contrast `useTags(q?)` which forwards `q`/`limit`.)
- **Return type** is TanStack Query's `UseQueryResult<TagGroupsResponse, Error>` inferred from the `useQuery<TagGroupsResponse>` generic: `data: TagGroupsResponse | undefined`, `isLoading`, `isError`, `error`, `refetch`, etc. `data.groups` is `TagGroupRead[]`, `data.groupless` is `TagReadWithCount[]` (43.1 types). No custom return interface, no `select`.

### Q4 — Error behaviour

Rely entirely on the shared `api()` client — **no local swallow, no local retry override**. `api()` throws `ApiError` on non-2xx (`api.ts:47-52`) and transparently handles the default-deny 401→refresh→retry once for `access_expired`/`missing_access` (`api.ts:34-43`); TanStack Query surfaces the throw as `isError`/`error`. The hook does **not** set `retry`, `throwOnError`, or a local `onError` — matching `useCategoriesTree`/`useTags` precedent exactly (neither sets any error policy). The endpoint is authenticated default-deny (`current_user`, outside `_PUBLIC_ROUTES`; Decision AW § auth posture, TB-055) — the FE needs **no** special auth handling because `credentials: "include"` + the 401-refresh path already live in `api()`.

### Q5 — Test strategy — see §6.

### Q6 — `useTags` test fallout — see §6.3.

### Q7 — RED→GREEN executable evidence — see §7.

### Q8 — Gates + controller ownership — see §8.

---

## 4. Cache-coherence enumeration (mandatory — project-context §286)

`useTagGroups` fetches taxonomy data that **overlaps** with `useTags` (both surface tag rows off the same `Tag` table), so the 5-row coherence table is required before the AC block. Filled once for `useTagGroups` (this story's hook) and once for the coupled `useTags`.

| Invariant | `useTagGroups` (`["sot","tag-groups"]`) | `useTags` (`["sot","tags",q]`) |
|---|---|---|
| **Staleness budget** | 5 min — admin-governed reference data; member browse never mutates it (Q1). | 5 min — same taxonomy family; unchanged by this story. |
| **Retry policy** | Inherit `api()` (401→refresh→retry once); TanStack default retry otherwise (test wrapper pins `retry:false`). No local override. | Unchanged — same inherited policy. |
| **Cache propagation (mutations)** | None in E43 (no FE tag-group mutation exists yet). E46 admin mutations will invalidate this key + `["sot","tags"]`. Not wired now (YAGNI). | None in E43. Existing `useCreateTag`/`useDeleteTag` mutation invalidation (if any) is out of scope and unchanged. |
| **Cache eviction on route exit** | Default gc — no forced `removeQueries`; taxonomy is not per-token/sensitive (unlike the share-probe terminus). | Unchanged. |
| **Cache seeding on this route** | None — `useTagGroups` is the canonical fetcher for its key; no other surface seeds `["sot","tag-groups"]`. | Unchanged — `["sot","tags",q]` seeded only by `useTags`. |

**Design choice recorded:** the two hooks keep **separate canonical query keys** (`["sot","tag-groups"]` vs `["sot","tags",q]`) — no shared cache, no cross-seeding. They read the same underlying table but return different shapes (`TagGroupsResponse` with required counts vs `TagListItem[]` with optional counts), so a shared cache would be a category error. No coupled-invariant divergence exists in E43 because no mutation surface ships here; the only forward coupling (admin edits must refresh both) is a future E46 concern discharged by the two independent, stable, path-mirroring keys.

---

## 5. Acceptance criteria (additive)

1. **`useTagGroups()` exists** at `apps/web/src/modules/catalog/hooks/useTagGroups.ts`, exported, taking **no** parameters, returning `useQuery<TagGroupsResponse>({ queryKey: ["sot","tag-groups"], queryFn: () => api<TagGroupsResponse>("/tag-groups"), staleTime: 5*60*1000 })` — no `select`, no local `retry`/`onError`, no key factory.
2. **Request path is `/api/tag-groups`** (path `/tag-groups` through `api()`'s `/api` base). Verified by test: `fetch` called with `"/api/tag-groups"`.
3. **`useTagGroups` return type** is `TagGroupsResponse | undefined` on `.data`; `.data.groups: TagGroupRead[]`, `.data.groupless: TagReadWithCount[]` typecheck without cast.
4. **`useTags` return/query type is `TagListItem[]`** (was `TagRead[]`) on both `useQuery<…>` and `api<…>`; **`import type { TagListItem }`** replaces `TagRead`. The `q`/`limit` request behaviour, the `["sot","tags", q ?? ""]` key, and the `staleTime` are **unchanged**. No runtime transform is added.
5. **`useCategoriesTree`** (file, export, `["sot","categories"]` key, `staleTime`) and its colocated test are **unchanged** — verified by `git diff` showing no edit to `useCategoriesTree.ts`/`.test.tsx` and no category consumer touched.
6. **Tests** (§6) pass and prove: `/api/tag-groups` endpoint hit; a typed body with populated `groups` (incl. an empty-`tags[]` group), `groupless`, required per-tag `model_count`, and `group_id: null` on a groupless tag round-trips through the hook; loading→success and error states resolve as neighbouring hooks assert; the query key/cache behaviour where meaningful. `useTags` tests prove the `q`/`limit` URLs are byte-identical to today and the returned items are typed `TagListItem[]` carrying `group_id`/`group_position` + optional `model_count`.
7. **Green gates:** `npm run typecheck` (`tsc -b`), `npm run lint` (`--max-warnings=0`), `npm run test` (vitest) all pass; `test:visual` untouched (no UI). Backend untouched. `git diff --check` clean.
8. **RED→GREEN evidence** captured (§7): the new `useTagGroups.test.tsx` is RED before the hook exists (unresolved import), GREEN after; the `useTags` re-type is proven by a type-level assertion that is RED against `TagRead[]` and GREEN against `TagListItem[]`.

---

## 6. Test strategy

**Convention (verified, non-negotiable):** the repo uses **mocked `fetch`**, NOT MSW, for hook tests — `vi.stubGlobal("fetch", fetchMock)` + `afterEach(() => fetchMock.mockReset())`, a `QueryClientProvider` wrapper with `retry: false`, and `renderHook` + `waitFor`. This is the exact shape of both neighbours (`useTags.test.tsx`, `useCategoriesTree.test.tsx`). **Do NOT introduce MSW** and **do NOT mock `api()`** — intercept at `fetch` so the CSRF header + 401-retry path stay exercised (project-context §114/§252). New test files mirror the neighbours' imports verbatim.

### 6.1 NEW — `useTagGroups.test.tsx` (colocated)

Model on `useCategoriesTree.test.tsx`. Assert, at minimum:

1. **Endpoint + shape (success):** `fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(body), { status: 200 }))` where `body` is a real 42.2 `TagGroupsResponse` fixture — at least one populated group, **one empty-`tags[]` group** (backend returns empty groups; endpoint description confirms), a non-empty `groupless`, each tag carrying a **required** `model_count`, and at least one tag with **`group_id: null`** in `groupless`. Then `expect(fetchMock).toHaveBeenCalledWith("/api/tag-groups", expect.any(Object))` and assert `result.current.data?.groups` / `.groupless` lengths + a nested `model_count` and the `group_id: null` round-trip.
2. **Loading→success:** `result.current.isLoading` is true before `waitFor(() => expect(result.current.data).toBeDefined())` resolves (mirrors neighbour timing).
3. **Error:** `fetchMock.mockResolvedValueOnce(new Response("{}", { status: 500 }))` → `await waitFor(() => expect(result.current.isError).toBe(true))` (wrapper's `retry:false` makes this deterministic). Include only if it adds signal beyond the neighbours — `useCategoriesTree.test.tsx` does not assert error, but a single-shot taxonomy hook backing a sidebar warrants the error branch; keep it to one case.
4. **Query-key/cache (only where meaningful):** a second `renderHook(() => useTagGroups())` under the **same** wrapper does **not** re-fetch within `staleTime` (one `fetch` call for two mounts) — proves the stable key + cache. Keep to one assertion; do not over-test framework behaviour.

### 6.2 Type-level proof (no cast)

In `useTagGroups.test.tsx` (or a sibling `*.test-d`-style block using vitest `expectTypeOf`, matching the 43.1 `api-types-tags.test.ts` precedent), assert `useTagGroups`'s `data` is `TagGroupsResponse | undefined` — e.g. `expectTypeOf(result.current.data).toEqualTypeOf<TagGroupsResponse | undefined>()`. No `as`, no `any`.

### 6.3 UPDATE — `useTags.test.tsx` fallout (regression-lock)

The existing three `it` blocks (`fetches /api/tags without query`, `passes q parameter`, `uses different cache keys`) must stay **green byte-for-byte** — they already assert `"/api/tags?limit=50"` and `"/api/tags?q=dragon&limit=50"`, which this story does **not** change. Add coverage proving the returned entries are typed `TagListItem[]`:

- A fixture response carrying `group_id`/`group_position` **and `model_count`** on each item. **Primary (framework-independent) RED:** a type-level access of the count key in the test body — reference `result.current.data?.[0]?.model_count`. `model_count` is the *only* structural difference between `TagRead` and `TagListItem`, so that line is a `tsc -b` **compile error while `useTags` still returns `TagRead[]`** (property absent on `TagRead`) and GREEN after the re-type (empirically verified). **Confirmation:** `expectTypeOf(result.current.data).toEqualTypeOf<TagListItem[] | undefined>()`, which *also* fails against `TagRead[]` — but note **why**: expect-type 1.3.0's `toEqualTypeOf` is a DeepBrand strict-equality (`StrictEqualUsingBranding`) that treats the extra optional `model_count` key as a difference, **not** mere mutual assignability. `TagRead[]` and `TagListItem[]` **are** mutually assignable (the optional key permits it), so an assignability-only matcher (`toMatchTypeOf`) would NOT discriminate them; the strict-equal matcher does. Do **not** use `result.current.data?.[0]?.group_id` as the re-type proof — `group_id` exists on `TagRead` too and does not discriminate the shapes. This is the only net-new `useTags` test; the three URL/cache tests are untouched.

---

## 7. RED→GREEN executable evidence (dev-time)

Expected during `bmad-dev-story`; capture logs to gitignored `.hermes/run-logs/e43.2-*.log`.

1. **RED — `useTagGroups`:** author `useTagGroups.test.tsx` first. Before the hook file exists, `npm run typecheck` (`tsc -b`, which compiles `src/**/*.test.tsx`) fails with an unresolved-import error for `./useTagGroups`, and `npm run test` fails the suite (module not found). Capture `.hermes/run-logs/e43.2-red-typecheck.log`.
2. **RED — `useTags` re-type:** while `useTags` still returns `TagRead[]`, both (a) the direct `result.current.data?.[0]?.model_count` type-access and (b) `expectTypeOf(...).toEqualTypeOf<TagListItem[] | undefined>()` are RED under `tsc -b`. The two array types **are** mutually assignable, so the RED does *not* come from assignability: (a) fails because `model_count` is absent on `TagRead`; (b) fails because expect-type 1.3.0's `toEqualTypeOf` is a DeepBrand strict-equality that treats the extra optional key as a difference (both empirically verified). Same log.
3. **GREEN:** create `useTagGroups.ts`; re-type `useTags`. Focused `npx vitest run src/modules/catalog/hooks/useTagGroups.test.tsx src/modules/catalog/hooks/useTags.test.tsx` PASS; `npm run typecheck` PASS. Capture `.hermes/run-logs/e43.2-green-*.log`.
4. Note (as in 43.1): `npm run test` (vitest run, no `--typecheck`) is NOT the type-RED gate — esbuild erases `import type`/`expectTypeOf` at runtime. The **runtime** RED for the new hook is the unresolved runtime import (module not found); the **type** RED is `tsc -b`. Both must be shown.

---

## 8. Gates + controller ownership

- **Dev-time green gates (dev owns):** `npm run typecheck`, `npm run lint` (`--max-warnings=0`), focused + full `npm run test` (vitest), `npm run build` (`tsc -b && vite build`). No `test:visual` change (no UI touched) — but the full `check-all.sh` still runs it. `git diff --check` clean.
- **Full closeout gate (controller owns):** `infra/scripts/check-all.sh` all-green standalone, teed to `.hermes/run-logs/check-all-*.log`, before the story-branch ff-merge to `main` (per AGENTS.md § gate evidence). Native `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor) + independent external review (Aider via `laura-aider-review-diff`; Codex only fallback/high-stakes) per the rulebook. epic-43 stays `in-progress`; the 43.2 status flip to `done` is controller-owned at closeout.
- **Branch:** `feat/E43.2-hooks` off `main` (single-story-in-progress; ff-only merge). Not created by this spec run.

---

## 9. Convention & fence notes

- **Hook location:** `apps/web/src/modules/catalog/hooks/` — colocated with siblings; `useTagGroups.test.tsx` colocated next to `useTagGroups.ts` (project-context §113 — no `__tests__/` mirror).
- **Import order** matches the repo lint (`@tanstack/react-query`, blank line, `@/lib/*`) — copy the neighbour files' exact import block to satisfy `--max-warnings=0`.
- **No key factory, no `select`, no `with_counts` on `useTags`, no MSW, no `api()` mock, no error swallow/retry override** — each is a Ponytail rung-1/3 avoidance; the smallest correct diff is two ~15-line hook files + colocated tests.
- **Scope fences honored:** hooks only. No URL state (43.3), no UI/components (E44/E45), no backend, no migration, no locale, no route-tree regen (no route param change), no visual-baseline regen, no `package.json`/lockfile, no codegen (`api-types.ts` is hand-maintained; 43.1 already shipped the types this hook imports — 43.2 adds **no** type).
- **Category preservation:** `useCategoriesTree` + all category consumers untouched; deletion owned by 47.4 (Decision AW § Frontend types; `43-1-api-types.md` §2).

---

## 10. Verification performed for this spec

- `bmad-help` run (mandatory session start) → canonical route confirmed from `_bmad/_config/bmad-help.csv:26-28`: `bmad-create-story:create` (CS), phase 4-implementation, preceded-by `bmad-sprint-planning` (done), followed-by `bmad-create-story:validate` (VS) → `bmad-dev-story`.
- Shipped read surface read from source: `sot/router.py:67-121` (`GET /tags` `response_model=list[TagListItem]`, params `q`/`limit`/`with_counts`; `GET /tag-groups` param-less, `response_model=TagGroupsResponse`; both gated on `current_user`), `schemas.py:35-101` (exact shapes/nullability), `test_sot_auth_boundary.py:139-196` (anonymous→401 / agent→200 for `/tag-groups`).
- Shipped 43.1 FE types confirmed present: `api-types.ts:67-115` (`TagRead` + `TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary`) — 43.2 imports, adds none.
- FE conventions confirmed by source: `lib/api.ts` (`BASE="/api"`, 401→refresh, `ApiError`); `useTags.ts`/`useCategoriesTree.ts` (inline `["sot",…]` keys, 5-min `staleTime`, no error policy); `useModels.ts` (key precedent); no query-key factory anywhere (`grep`); test convention mocked-`fetch` (`useTags.test.tsx`, `useCategoriesTree.test.tsx`), project-context §69/§113/§114/§252/§286/§287.
- No pre-existing `useTagGroups.ts` / `useTagGroups.test.tsx` (fresh create; `grep` clean). `useTags` currently typed `TagRead[]` (RED baseline correct).

---

## 11. Tasks / Subtasks — dev execution (native `bmad-dev-story`)

- [ ] **T1 — RED first (TDD).** Author `apps/web/src/modules/catalog/hooks/useTagGroups.test.tsx` (mocked-`fetch`, `QueryClientProvider` `retry:false`, `renderHook`/`waitFor`; mirror `useCategoriesTree.test.tsx`) covering §6.1 + the §6.2 `expectTypeOf` proof. Add the §6.3 net-new `useTags` type/field assertion to `useTags.test.tsx`. Capture RED (`npm run typecheck` unresolved import + type-inequality; `npm run test` module-not-found). Evidence → `.hermes/run-logs/e43.2-red-typecheck.log`.
- [ ] **T2 — GREEN new hook.** Create `useTagGroups.ts` per §2.1 (no params, `["sot","tag-groups"]`, `api<TagGroupsResponse>("/tag-groups")`, `staleTime: 5*60*1000`, no `select`/`retry`/`onError`).
- [ ] **T3 — GREEN re-type `useTags`.** Change the three type references (`import type`, `useQuery<TagListItem[]>`, `api<TagListItem[]>`) per §2.2; leave params/key/`staleTime` byte-identical.
- [ ] **T4 — Preserve category surface.** `useCategoriesTree.ts`/`.test.tsx` and all category consumers untouched (`git diff` proves no edit).
- [ ] **T5 — Green gates.** Focused vitest (both hook tests) PASS; `npm run typecheck` PASS; `npm run lint` PASS (`--max-warnings=0`); full `npm run test` PASS; `npm run build` PASS. No visual regen. `git diff --check` clean. Evidence → `.hermes/run-logs/e43.2-green-*.log`.

## 12. Dev Agent Record

### 12.1 Debug Log

_(populated by `bmad-dev-story`)_

### 12.2 Completion Notes

_(populated by `bmad-dev-story`)_

## 13. File List (expected)

New (intended):

- `apps/web/src/modules/catalog/hooks/useTagGroups.ts` — the new query hook (core deliverable).
- `apps/web/src/modules/catalog/hooks/useTagGroups.test.tsx` — RED-first mocked-`fetch` + type-level test.

Changed:

- `apps/web/src/modules/catalog/hooks/useTags.ts` — `TagRead[]` → `TagListItem[]` on `useQuery`/`api` + `import type` (type-only re-type; request behaviour unchanged).
- `apps/web/src/modules/catalog/hooks/useTags.test.tsx` — one net-new `TagListItem[]`/field assertion; three existing URL/cache tests untouched.

Docs (tracked): this story artifact; `sprint-status.yaml` (43-2-hooks → ready-for-validation).

Explicitly NOT changed: `useCategoriesTree.ts`/`.test.tsx`, any category consumer, `api-types.ts` (types already shipped in 43.1), any backend/migration/locale/route-tree/visual/package file.

## 14. Change Log

| Date | Change |
|---|---|
| 2026-07-19 | Native `bmad-create-story` (Create) authored the additive 43.2 hooks spec (baseline `main` @ 52868c0): `useTagGroups()` off `GET /api/tag-groups` typed `TagGroupsResponse`; `useTags` re-typed `TagRead[]`→`TagListItem[]` (request behaviour preserved); `useCategoriesTree` preserved (deletion owned by 47.4). Contract Qs resolved code-first (key `["sot","tag-groups"]`, path `/api/tag-groups`, no params, `staleTime` 5 min, shared-`api()` error policy). Cache-coherence table filled. Status → `ready-for-validation`; independent `bmad-create-story:validate` (VS) to follow. |
| 2026-07-19 | Independent native `bmad-create-story:validate` (VS) → **PASS** (0 critical). Empirically verified (isolated `tsc` against the repo's expect-type 1.3.0) that the `useTags` re-type RED is real: `expectTypeOf(...).toEqualTypeOf<TagListItem[] | undefined>()` fails to compile against `TagRead[] | undefined` because `toEqualTypeOf` is a DeepBrand strict-equality, **not** mutual assignability (the two arrays are mutually assignable). Hardened §6.3/§7.2 with the framework-independent primary RED — a direct `result.current.data?.[0]?.model_count` type-access (compile error on `TagRead`, GREEN after re-type) — and removed the non-discriminating `group_id` re-type proof (1 important + 1 minor wording, both fixed). Status `ready-for-validation` → `ready-for-dev`; next native route `bmad-dev-story`. Evidence: `.hermes/run-logs/e43.2-validation.md`. |
