---
baseline_commit: 910e976c7f2017104ed37c05e79f1ae36f72ec1c
---

# Story 50.1 — FE types + hooks for browse categories (FR26-CAT-1, FR26-CAT-2)

- **Epic:** E50 — Frontend data layer, URL state, and search suggestions (Initiative 26 — Catalog Discovery)
- **Status:** `done` — **CLOSED 2026-07-28 by Laura/controller.** Implementation commit **`9697d8c0095863e83c895b8de8e1ee7ba296a860`** (`feat(web): add browse category data hooks`); branch `feat/E50.1-fe-types-and-hooks` **fast-forward merged** into `main`; `git push origin main` succeeded and `origin/main` verified at the same SHA (lean pre-push transport gate **11/11** passed). Deploy: `infra/scripts/deploy.sh` succeeded — log `.hermes/run-logs/deploy-e50-1-20260728_183653.log`, exit marker **`DEPLOY_RC=0 2026-07-28T18:40:05+02:00`**, script ended `Done.` Post-deploy smoke (controller): all six `.190` services `running`, LAN `/api/health` → `{"status":"ok","version":"0.1.0"}`, LAN web **200**, production HTTPS `https://3d.ezop.ddns.net/` **200**. **Closeout provenance, stated plainly: native BMAD `bmad-code-review` APPROVE + independent Aider APPROVE + `check-all.sh` 16/16 + controller-run merge/push/deploy/smoke — NO human review of any kind, NO Ezop signature, no Codex, no Gemini.** See **§20**. PRIOR: full closeout gate **`infra/scripts/check-all.sh` all green, 2026-07-28: 16/16 stages passed** (`.hermes/run-logs/check-all-e50-1-20260728_182040.log`, exit marker `CHECK_ALL_RC=0 2026-07-28T18:31:26+02:00`), which discharges the `npm run test:visual` and backend-suite obligations as in-check-all stages (§19). Status was **deliberately held at `review`** at that point because commit / ff-only merge to `main` / push / deploy / post-deploy smoke were then still owed and unclaimed — all five are now discharged (§20). PRIOR: independent external review **`laura-aider-review-diff` / Aider, 2026-07-28: literal verdict `APPROVE`**, 0 critical, no patch required (§18). PRIOR: native `bmad-code-review` (CR) pass 1, 2026-07-28: **literal verdict `APPROVE`** (native BMAD agent approval ONLY — **NOT an Ezop signature, NOT human review of any kind**). Status was deliberately held at `review` then, not flipped to `done`, because the controller-owned closeout (`infra/scripts/check-all.sh`, `npm run test:visual`, commit / ff-merge / push / deploy) was still owed. See §17–§18. PRIOR: implemented 2026-07-28 by native `bmad-dev-story` (DS) under Laura/controller **G26-DEVGO** for this exact scope. PRIOR: `ready-for-dev` — created + validated 2026-07-28.
- **Author:** Claude (native `bmad-create-story`, Create + Validate). **Controller:** Laura.
- **Created:** 2026-07-28 via native `bmad-create-story` after mandatory `bmad-help`. Canonical route from `_bmad/_config/bmad-help.csv:26-28`: `bmad-create-story:create` (CS, phase `4-implementation`, preceded-by `bmad-sprint-planning` — done) → `bmad-create-story:validate` (VS) → `bmad-dev-story` (DS) → `bmad-code-review` (CR).
- **Scope class:** frontend **data layer only** — `apps/web/src/lib/api-types.ts` (additive types + one additive `ModelDetail` field), two new query hooks, one additive `useModels` filter key, and their colocated tests. **No** UI/component, no route/URL state (50.2), no suggestion surface (50.3), no i18n key, no a11y assertion, no visual baseline, no backend, no migration, no dependency/lockfile, no codegen, no route-tree regeneration.
- **Sources of truth:** `epics.md` § Initiative 26 → E50 → Story 50.1 (`:4497-4505`); `architecture.md` Decision AY (`:3303-3345`); `prd.md` FR26-CAT-1 (`:2244`), FR26-CAT-2 (`:2245`); the **shipped** E49 wire (`apps/api/app/modules/sot/schemas.py:87-133,207-225`, `router.py:106-232`, `service.py:176-247,505-575`) at `main` @ `910e976`; in-repo precedents `43-1-api-types.md` (`done`) and `43-2-hooks.md` (`done`).

---

## 1. Story statement

**As** the catalog frontend,
**I want** the shipped Initiative 26 browse-category read contract mirrored honestly in `api-types.ts`, plus `useCategories()` / `useCategoryBySlug()` query hooks and a `category` filter key on `useModels`,
**so that** Stories 50.2 (URL state), 51.1/51.2/51.4 (browse IA, `/categories/$slug`, model-detail category display) and 52.x (admin/curation surfaces) can consume categories through the repo's standard `api()` + TanStack-Query data layer without any component reaching for `fetch`, an inaccurate type, or an `as` cast.

**FR mapping.** **FR26-CAT-1** (categories are a first-class admin-curated browse entity with stable slug, bilingual labels, optional bilingual descriptions and explicit `position`) — the FE type must carry that shape without inventing or dropping a key. **FR26-CAT-2** (M:N membership; **zero categories is valid** and stays publicly visible) — the FE type for `ModelDetail.categories` must make the empty case ordinary, not exceptional.

**This story renders nothing.** It is the typed substrate for the epic. Per `epics.md:4505` and the NFR matrix (`:4417-4420`), it therefore owns **no i18n key, no a11y assertion and no visual baseline of its own**; hook + type unit coverage is still fully owed at its own merge gate.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `910e976`

The standing epic:47 PROCESS action item forbids carrying a sketch's "X already exists / Y is already gone" as settled fact. Every claim below was re-traced at story-creation time.

| Claim | Verified at | Result |
|---|---|---|
| `BrowseCategorySummary` shipped, 6 keys | `sot/schemas.py:87-104` | ✅ `id, slug, name_en, name_pl: str \| None, position: int, parent_id: UUID \| None`. No `model_count` (deliberate — Decision AY). |
| `BrowseCategoryRead` shipped, 9 keys | `sot/schemas.py:107-120` | ✅ extends `BrowseCategorySummary` with `description_en: str \| None`, `description_pl: str \| None`, `model_count: int` (**required + unconditional**, unlike `TagListItem.model_count`). |
| `GET /api/categories` → `list[BrowseCategoryRead]`, flat, `(position, slug)`, empty categories included, `current_user` | `router.py:106-132`, `service.py:213-234` | ✅ Flat array — **no** `children`/`subcategories` key; `parent_id` is a scalar FK. |
| `GET /api/categories/{slug}` → `BrowseCategoryRead`, **404** on unknown slug | `router.py:135-159` | ✅ `HTTPException(404, "Browse category not found")`. |
| `ModelDetail.categories: list[BrowseCategorySummary]`, always emitted, `[]` never null/absent | `schemas.py:207-225`, `service.py:558-570` | ✅ Declared on the **subclass only**; `get_model_detail` always writes the `"categories"` key explicitly. `ModelSummary` deliberately does **not** carry it. |
| `GET /api/models?category=<slug>` — one slug, no 404 on unknown | `router.py:161-226` (`category: str \| None = None`) | ✅ Exactly one value, AND-composed, **not** folded into `tag_match`; unknown slug → 200 + empty page + `total: 0`. |
| `BrowseCategoryAdminRead` exists but is **admin-only** | `schemas.py:123-133` (Story 49.5) | ✅ `BrowseCategoryRead` + `inclusion_criterion`. **Not** in any 50.1 SoT line — see D-2. |
| FE has no browse-category symbol yet | `grep -rn "BrowseCategory\|useCategories\|useCategoryBySlug" apps/web/src` | ✅ Zero hits. Correct RED baseline. |
| Retired Initiative 25 category surface is gone from the FE | `grep -rn "CategorySummary\|CategoryNode\|CategoryTree\|useCategoriesTree" apps/web/src` | ✅ Zero hits (deleted by 47.4/47.5). Nothing to preserve, nothing to resurrect. |
| `routes/catalog/index.tsx` `validateSearch` has no `category` layer | `routes/catalog/index.tsx:47-103` | ✅ Zero `category` occurrences — that layer is **Story 50.2**, not this one. |
| Every `ModelDetail`-returning endpoint routes through the one constructor | `router.py:237`, `admin_router.py:146,177,212,244,290` → `service.get_model_detail` | ✅ Single construction site, so `categories` is on **every** `ModelDetail` the FE can receive (`useModel`, `useShareModelProbe`, `useUpdateModel`, `useSetThumbnail`, `AddModelForm`). |
| The anonymous share projection has **no** categories | `lib/share-api.ts:29-49`; Decision AY § Invariants (`architecture.md:3343`) | ✅ `ShareModelView` is a separate hand-typed interface and stays byte-unchanged (NFR25-LEAKFENCE-1 fence). |
| Route tree is unaffected | no route file added/changed; `/categories/$slug` is **51.2** | ✅ `reference_web_routetree_regen` does **not** apply to this story. |

**Inherited fact from Story 49.3 (CR-2, deferred to this story — `49-3-…md:811`).** Because `ModelDetail.categories` is declared as `Field(default_factory=list)`, the generated OpenAPI document lists `categories` under `properties` but **not** under `required` (measured in 49.3). That is a document artefact of the default, **not** the wire behaviour: the single runtime constructor always writes the key, and 49.3 asserts `categories: []` end-to-end over HTTP. This story inherits the fact rather than rediscovering it, and resolves it explicitly in **D-1**.

---

## 3. Additive scope — the implementable-green target

Nothing is removed, renamed, narrowed or made optional. Four deliverables.

### 3.1 `api-types.ts` — two new interfaces (mirror `sot/schemas.py:87-120` field-for-field)

```ts
// --- Browse categories (Initiative 26, Story 49.3) ---

// Embeddable browse-category shape — what ModelDetail.categories carries.
// Deliberately WITHOUT model_count: embedding a count here would cost an
// aggregate per detail read for a number the detail view never renders
// (Decision AY). `parent_id` is a scalar FK — the contract is FLAT and
// carries no children/subcategories key.
export interface BrowseCategorySummary {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
  position: number;
  parent_id: string | null; // null = top-level
}

// GET /api/categories item and GET /api/categories/{slug} body.
// model_count is REQUIRED and unconditional here (unlike TagListItem's
// opt-in ?with_counts count) — browse IA and curation QA always need it.
// inclusion_criterion is deliberately absent from the public read contract.
export interface BrowseCategoryRead extends BrowseCategorySummary {
  description_en: string | null;
  description_pl: string | null;
  model_count: number;
}
```

### 3.2 `api-types.ts` — `ModelDetail` gains `categories` (required)

```ts
export interface ModelDetail extends ModelSummary {
  // Initiative 26 (Story 49.3) — declared on ModelDetail only; ModelSummary
  // deliberately does NOT carry it (list cards render no categories in the
  // MVP IA). The backend always emits the key: `[]` for a zero-category
  // model, never null and never absent (FR26-CAT-2).
  categories: BrowseCategorySummary[];
  files: ModelFileRead[];
  prints: PrintRead[];
  notes: NoteRead[];
  external_links: ExternalLinkRead[];
}
```

### 3.3 Two new hooks (`apps/web/src/modules/catalog/hooks/`)

```ts
// useCategories.ts
export function useCategories() {
  return useQuery<BrowseCategoryRead[]>({
    queryKey: ["sot", "categories"],
    queryFn: () => api<BrowseCategoryRead[]>("/categories"),
    staleTime: 5 * 60 * 1000,
  });
}

// useCategoryBySlug.ts
export function useCategoryBySlug(slug: string) {
  return useQuery<BrowseCategoryRead>({
    queryKey: ["sot", "categories", slug],
    queryFn: () => api<BrowseCategoryRead>(`/categories/${slug}`),
    staleTime: 5 * 60 * 1000,
  });
}
```

Both mirror `useTagGroups` (43.2) exactly in shape: no `select`, no local `retry`/`onError`/`throwOnError`, no key factory, no wrapper return type. `api()` prepends `/api`, so the emitted requests are `/api/categories` and `/api/categories/<slug>`.

### 3.4 `useModels` — one additive filter key

```ts
export interface ModelsFilters {
  tag_ids?: string[];
  tag_match?: TagMatch;
  untagged?: boolean;
  status?: ModelStatus;
  source?: ModelSource;
  category?: string; // NEW (Initiative 26) — one browse-category SLUG
  q?: string;
  sort?: ModelListSort;
  page?: number;
}
```

and, in `buildParams`, immediately after the `source` branch and before `q` (matching the backend parameter order at `router.py:196-208`):

```ts
if (f.category !== undefined && f.category.length > 0) p.set("category", f.category);
```

**Behaviour for every existing caller is byte-identical** — `category` is unset everywhere until Story 50.2 wires the URL layer, so the emitted query string and the `["sot", "models", filters]` key are unchanged.

---

## 4. Resolved decisions (code-first, each with its cost stated)

**D-1 — `ModelDetail.categories` is REQUIRED on the FE type, not optional.** The OpenAPI document marks it non-required (49.3 CR-2, §2 above), but the *wire* always sends it: `get_model_detail` is the only constructor and writes the key unconditionally, and 49.3 asserts `categories: []` over HTTP. `api-types.ts` mirrors the **wire**, not the document — this repo has **no** codegen (43.1 §6: the file header says "keep this file in sync by hand"; there is no `api-types.gen.ts` and no OpenAPI pipeline), so nothing forces the document's optionality on us. An optional `categories?:` would push a `?? []` fallback into every future consumer (51.4 renders the empty state as *ordinary*, per FR26-CAT-2) and would model a field the API always sends as one it might not. **Stated cost:** every hand-built `ModelDetail` literal must supply the key — enumerated exhaustively in §7, ten test fixtures, zero production sites. This is the identical, sanctioned tail 43.1 took when `TagRead.group_id`/`group_position` were made required.

**D-2 — `BrowseCategoryAdminRead` is OUT of scope.** It ships on the backend (49.5, `schemas.py:123-133`) but appears in **no** 50.1 source of truth: not in the epic sketch (`epics.md:4505`), not in Decision AY's frontend line, not in the sprint-status text. Its consumer is the admin category screen, **Story 52.2**. Adding it here would be speculative typing for a surface no story in E50 mounts. *(Contrast 43.1, where `TagGroupSummary` — the analogous admin write-response type — WAS explicitly named in both governing artifacts and was therefore in scope. The asymmetry is deliberate and traced, not an oversight.)*

**D-3 — Query keys `["sot", "categories"]` and `["sot", "categories", slug]`; `staleTime` 5 min.** The repo has **no** query-key factory (`grep` — none); every hook writes an inline `["<bounded-context>", "<entity>", ...filters]` array whose entity segment mirrors the URL path (`/tag-groups` → `["sot","tag-groups"]`). `/categories` → `["sot","categories"]` follows. The list key is a **prefix** of the by-slug key, which is desirable: when the E52 admin mutations land, a single `invalidateQueries({ queryKey: ["sot","categories"] })` refreshes both. No invalidation is wired now — no FE category mutation exists yet.
**`staleTime: 5 * 60 * 1000` — contract-pointing justification** (project-context §287, which bans "matches the neighbour" as a justification): browse categories are **admin-governed reference data** mutated only through the Story 49.5 admin endpoints (`POST/PATCH/DELETE /api/admin/categories`, `PUT /api/admin/models/{id}/categories`) and never on the member browse path. FR26-CAT-1 makes curation a deliberate admin act, so a ≤5-minute window between an admin edit and a member's automatic refetch is the accepted staleness budget for a navigation rail. *(It coincides with `useTagGroups`/`useTags`; that coincidence is a consequence of the same contract class, not the reason.)*

**D-4 — No `enabled` guard on `useCategoryBySlug`.** It mirrors `useModel(id)`, which also takes a required non-empty identifier and sets no `enabled`. Its future caller is the `/categories/$slug` route param (51.2), which is non-empty by construction. Adding a speculative guard for a caller that does not exist is a Ponytail rung-1 addition. **Contract recorded for the dev agent and for 51.2:** the caller passes a non-empty slug; 51.2 may revisit if it ever mounts the hook before the param resolves.

**D-5 — Hand-written types, no codegen.** 43.1 §6 established this and it still holds: `api-types.ts` is hand-maintained. Do **not** introduce OpenAPI generation in this story.

**D-6 — `ShareModelView` is untouched.** Categories are deliberately absent from the anonymous share projection (Decision AY § Invariants); `lib/share-api.ts` must show a zero-line diff. The NFR25-LEAKFENCE-1 negative share-DTO test stays the fence.

**D-7 — Naming.** FE types are `BrowseCategory*`, never `Category*` — matching the backend and keeping the Story 47.5 retirement statements unambiguous. The hooks are `useCategories`/`useCategoryBySlug` per the epic sketch; hook names are not schema component names, and the `test_no_category_schemas_in_components` guard (`apps/api/tests/test_openapi_agent_surface.py:340`) checks backend OpenAPI components only. No FE symbol named `CategorySummary`/`CategoryNode`/`CategoryTree` may be reintroduced.

---

## 5. Cache-coherence enumeration (mandatory — project-context §286)

Required because these hooks fetch data that overlaps other surfaces: `["sot","categories"]` and `["sot","categories",slug]` describe the same rows, and `ModelDetail.categories` carries a projection of them inside `["sot","models",id]`.

| Invariant | `useCategories` `["sot","categories"]` | `useCategoryBySlug` `["sot","categories",slug]` | `useModel` `["sot","models",id]` (`.categories`) | `useModels` `["sot","models",filters]` (`category` filter) |
|---|---|---|---|---|
| **Staleness budget** | 5 min — admin-governed reference data (D-3). | 5 min — same contract class, same data. | **Unchanged, 30 s** — this story adds a field to an existing payload, it does not re-budget the detail read. | **Unchanged, 30 s** + `keepPreviousData` — untouched. |
| **Retry policy** | Inherit `api()` (401→refresh→retry once); TanStack default otherwise; test wrapper pins `retry:false`. No local override. | Same. A **404 on an unknown slug is a real error**, surfaced as `isError` — it is *not* retried into success and *not* swallowed. | Unchanged. | Unchanged. |
| **Cache propagation (mutations)** | None in E50 — no FE category mutation exists. E52 admin mutations invalidate the `["sot","categories"]` prefix (hits both keys) **and** `["sot","models"]`, because a replace-set write changes `ModelDetail.categories` and every `model_count`. Not wired now (YAGNI). | Same, via the prefix. | Same — flagged for E52, not built here. | Same. |
| **Cache eviction on route exit** | Default gc. Taxonomy is neither per-token nor sensitive — no forced `removeQueries` (contrast the share-probe terminus). | Default gc. | Unchanged. | Unchanged. |
| **Cache seeding on this route** | None — `useCategories` is the sole canonical fetcher for its key. | None. **Deliberately not seeded** from the list result: the two keys are populated independently. | None — `useModel` remains the sole fetcher; this story adds no `setQueryData`. | None. |

**Design choice recorded — the by-slug key is NOT seeded from the list.** `GET /api/categories` returns the same `BrowseCategoryRead` shape as `GET /api/categories/{slug}`, so seeding is *technically* possible, and it is deliberately not done: it would make a 404-on-unknown-slug (a real contract distinction — Decision AY draws it on purpose) silently resolve from a stale list, and it couples two independent staleness clocks for a single avoided round-trip on a route no story mounts yet. Two independent canonical keys, no cross-seeding — the same posture 43.2 recorded for `["sot","tag-groups"]` vs `["sot","tags",q]`.

**Divergence check:** none. No column in the table disagrees with another; the only forward coupling (admin writes must refresh categories *and* models) is discharged by stable, prefix-invalidatable keys and is explicitly owned by E52.

---

## 6. Acceptance criteria

1. **`BrowseCategorySummary`** exists and exported in `api-types.ts`, exactly `{ id: string; slug: string; name_en: string; name_pl: string | null; position: number; parent_id: string | null }` — six keys, **no** `model_count`, **no** `children`/`subcategories`.
2. **`BrowseCategoryRead extends BrowseCategorySummary`** adding exactly `description_en: string | null`, `description_pl: string | null`, `model_count: number` (**required**, not optional, not `| null`). **No** `inclusion_criterion` (that key is the admin contract, D-2).
3. **`ModelDetail.categories: BrowseCategorySummary[]`** — **required**, non-optional, non-nullable (D-1). **`ModelSummary` does NOT gain it** — verified by an explicit negative assertion.
4. **`useCategories()`** exists at `modules/catalog/hooks/useCategories.ts`, exported, takes **no** parameters, returns `useQuery<BrowseCategoryRead[]>({ queryKey: ["sot","categories"], queryFn: () => api<BrowseCategoryRead[]>("/categories"), staleTime: 5*60*1000 })` — no `select`, no local `retry`/`onError`, no key factory. Emitted request is **`/api/categories`**.
5. **`useCategoryBySlug(slug: string)`** exists at `modules/catalog/hooks/useCategoryBySlug.ts`, exported, returns `useQuery<BrowseCategoryRead>({ queryKey: ["sot","categories", slug], queryFn: () => api<BrowseCategoryRead>(\`/categories/${slug}\`), staleTime: 5*60*1000 })`. Emitted request is **`/api/categories/<slug>`**. A **404 surfaces as `isError`** — not swallowed, not defaulted, not retried into success.
6. **`ModelsFilters` gains `category?: string`** and `buildParams` emits `category=<slug>` **only** when the value is a non-empty string, positioned after `source` and before `q`. `category` is a **slug**, never a UUID and never an array. The 43.3 canonical-UUID hardening for `tag_ids` is untouched.
7. **No existing type, field, hook, query key, `staleTime`, or request URL is removed, renamed, narrowed or weakened.** Specifically byte-unchanged: `useTags`, `useTagGroups`, `useModel`, `useModels`' existing branches, `ModelSummary`, `TagRead`/`TagListItem`/`TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary`, and `lib/share-api.ts` (`ShareModelView` — D-6). Proven by `git diff` review plus the untouched pre-existing tests staying green **without edits**.
8. **Type-level test** `apps/web/src/lib/api-types-categories.test.ts` proves the exact shapes with `expectTypeOf` — **no `as`, no `any`, no unsafe cast** (43.1 convention). Minimum assertions in §7.1.
9. **Hook unit tests** (colocated, mocked `fetch`, never a mocked `api()`) prove endpoint, typed round-trip, loading→success, error branch, and the stable-key cache behaviour — §7.2.
10. **Green gates:** `npm run typecheck` (`tsc -b`), `npm run lint` (`--max-warnings=0`), `npm run test` (vitest) all pass; `npm run build` passes. Backend byte-unchanged. `git diff --check` clean. **No visual baseline is added, changed or regenerated** — no component renders in this story; `npm run test:visual` must be green **unchanged** (it still runs inside `check-all.sh`).
11. **TDD:** every deliverable lands RED-first with captured evidence (§8). The RED for the type work is `tsc -b`, **not** `vitest run` — esbuild erases `import type`/`expectTypeOf` at runtime (43.1 AC #6, 35.5 precedent).
12. **NFR26-DETERMINISM-1:** 3× consecutive identical vitest pass counts before merge.

---

## 7. Test strategy

**Non-negotiable conventions** (verified in-repo, not recalled): hook tests use `vi.stubGlobal("fetch", fetchMock)` + `afterEach(() => fetchMock.mockReset())`, a `QueryClientProvider` wrapper pinned to `retry: false`, and `renderHook`/`waitFor` — the exact shape of `useTagGroups.test.tsx` and `useTags.test.tsx`. **Do not introduce MSW. Do not mock `api()`** — intercepting at `fetch` keeps the CSRF header and 401-retry path exercised (project-context §114/§252). With `globals: false` in `vitest.config.ts`, every new multi-`it` test file **must** include `import { cleanup } from "@testing-library/react"; afterEach(cleanup);` (project-context §115 — this has bitten three times).

### 7.1 NEW — `apps/web/src/lib/api-types-categories.test.ts` (type-level, no runtime)

Mirrors `api-types-tags.test.ts`. Assert at minimum:

- `BrowseCategorySummary` `toEqualTypeOf<{ id: string; slug: string; name_en: string; name_pl: string | null; position: number; parent_id: string | null }>()` — structural equality, which also **fails if an extra key is added**.
- `BrowseCategorySummary` `.not.toHaveProperty("model_count")` and `.not.toHaveProperty("children")`.
- `BrowseCategoryRead["model_count"]` `toEqualTypeOf<number>()` (**required** — this is what discriminates it from a `TagListItem`-style optional count); `BrowseCategoryRead["description_en"]` / `["description_pl"]` `toEqualTypeOf<string | null>()`; `BrowseCategoryRead["parent_id"]` `toEqualTypeOf<string | null>()`.
- `BrowseCategoryRead` `.not.toHaveProperty("inclusion_criterion")` (D-2 fence, in the type system).
- `ModelDetail["categories"]` `toEqualTypeOf<BrowseCategorySummary[]>()` — note **not** `| undefined`, which is exactly the D-1 requiredness proof (`noUncheckedIndexedAccess` does not affect a known-literal-key access; `exactOptionalPropertyTypes` is not set, so an optional key would widen to `| undefined` and fail this assertion).
- `ModelSummary` `.not.toHaveProperty("categories")` (AC-3 negative).
- A literal fixture built from a **real** `GET /api/categories` body assigned via `satisfies BrowseCategoryRead[]` (compile-time wire proof, no cast) — including one top-level category (`parent_id: null`), one child (`parent_id: <uuid>`), one with `name_pl: null`, one with both descriptions `null`, and one with `model_count: 0` (the empty category the curation surface must see).

### 7.2 NEW — `useCategories.test.tsx` / `useCategoryBySlug.test.tsx` (colocated)

`useCategories`:
1. **Endpoint + typed round-trip:** `expect(fetchMock).toHaveBeenCalledWith("/api/categories", expect.any(Object))`; the fixture from §7.1 round-trips, including a `model_count: 0` category and a `parent_id: null` vs non-null pair.
2. **Loading→success:** `isLoading` true before `waitFor(() => expect(result.current.data).toBeDefined())`.
3. **Error:** `new Response("{}", { status: 500 })` → `isError` true (deterministic under `retry:false`).
4. **Stable key / cache:** two mounts under the **same** wrapper produce **one** `fetch` call within `staleTime`. Unmount both observers in the test.
5. **Type proof:** `expectTypeOf(result.current.data).toEqualTypeOf<BrowseCategoryRead[] | undefined>()`.

`useCategoryBySlug`:
1. **Endpoint:** called with `"/api/categories/kitchen"` for `useCategoryBySlug("kitchen")` — proves the path is interpolated, not a query param.
2. **Typed round-trip** of a single `BrowseCategoryRead`.
3. **404 → `isError`** (the Decision AY distinction; assert `isError`, and that `data` stays `undefined` — no silent default).
4. **Key isolation:** two different slugs under the same wrapper produce **two** fetches and do not share a cache entry.
5. **Type proof:** `expectTypeOf(result.current.data).toEqualTypeOf<BrowseCategoryRead | undefined>()`.

### 7.3 UPDATE — `useModels.test.tsx` (regression-lock + one net-new case)

The existing URL assertions must stay green **byte-for-byte with no edit** — that is the proof `category` changed nothing for existing callers. Add exactly two cases:
- `useModels({ category: "kitchen" })` → `fetch` called with a URL containing `category=kitchen`.
- `useModels({ category: "" })` (and, separately, `category` absent) → the emitted URL contains **no** `category` key at all.

### 7.4 Mechanical fallout — required, data-only, exhaustively enumerated

Making `ModelDetail.categories` required (D-1) makes every hand-built `ModelDetail` literal a `tsc -b` error until it supplies the key. **`tsc` is the enumerator; this list is the pre-enumeration the dev agent verifies against, not a guess.** Exactly **ten** sites, **all test fixtures, zero production code**:

1. `modules/catalog/components/ModelHero.test.tsx` (`makeDetail`)
2. `modules/catalog/components/TagGroupsSection.test.tsx` (`makeDetail`)
3. `modules/catalog/components/MetadataPanel.test.tsx` (`makeDetail`)
4. `modules/catalog/components/SecondaryTabs.test.tsx` (`makeDetail`)
5. `modules/catalog/components/DescriptionPanel.test.tsx` (`makeDetail`)
6. `modules/catalog/components/dialogs/DeleteModelDialog.test.tsx` (`makeDetail`)
7. `modules/catalog/components/sheets/EditTagsSheet.test.tsx` (`makeDetail`)
8. `modules/catalog/components/sheets/EditDescriptionSheet.test.tsx` (`makeDetail`)
9. `modules/catalog/components/sheets/RenderSheet.test.tsx` (`makeDetail`)
10. `modules/catalog/components/tabs/PhotosTab.test.tsx` (`makeDetail`)

Each gets **one line — `categories: [],`** in its base literal. Nothing else in those files may change. **Not affected (verified, do not touch):** `routes/dev/components.tsx` (`FAKE_MODEL` is a `ModelSummary`), `routes/share/MemberShareView.test.tsx` (untyped `JSON.stringify` body), `apps/web/tests/visual/api-stubs.ts` (untyped `route.fulfill` bodies; it imports `TagGroupsResponse`/`TagListItem` only). If `tsc` names a site outside this list, **stop and report it** — the pre-enumeration was wrong and the controller decides, rather than the dev agent widening scope silently.

---

## 8. RED→GREEN evidence (dev-time; tee to gitignored `.hermes/run-logs/e50.1-*.log`)

1. **RED — types.** Author `api-types-categories.test.ts` first. Before the types exist, `npm run typecheck` fails with unresolved-export errors (`TS2305`) for `BrowseCategorySummary`/`BrowseCategoryRead` and a missing-property error for `ModelDetail["categories"]`. → `e50.1-red-typecheck.log`.
2. **RED — hooks.** Author both hook tests first. `npx vitest run` fails with *"Failed to resolve import ./useCategories"* (runtime RED) and `tsc -b` fails `TS2307` (type RED). **Both must be shown** — 43.2 established that the type RED alone is not enough evidence for a new file.
3. **RED — `useModels.category`.** While `ModelsFilters` lacks the key, `useModels({ category: "kitchen" })` is a `tsc -b` excess-property error (`TS2353`). Framework-independent, does not rest on `expectTypeOf`.
4. **GREEN.** Add the two interfaces + the `ModelDetail` field, the two hook files, the `ModelsFilters` key + `buildParams` branch, then the ten fixture lines from §7.4. Focused vitest PASS; `npm run typecheck` PASS; `npm run lint` PASS; full `npm run test` PASS; `npm run build` PASS. → `e50.1-green-*.log`.
5. **Note:** `npm run test` (vitest run, no `--typecheck`) is **not** the type-RED gate — esbuild erases `import type`/`expectTypeOf` at runtime.

---

## 9. Gates + ownership

- **Dev-time (dev owns):** `npm run typecheck`, `npm run lint` (`--max-warnings=0`), focused + full `npm run test` ×3 (NFR26-DETERMINISM-1), `npm run build`. `git diff --check` clean. No `--update-snapshots`, ever, in this story.
- **Closeout (controller owns):** `infra/scripts/check-all.sh` all-green standalone, teed to `.hermes/run-logs/check-all-*.log`, before the ff-only merge to `main` (AGENTS.md § gate evidence). Native `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor), then the independent external review per the Laura Agent Rulebook — **Aider** (`laura-aider-review-diff`) is the routine route; Codex is fallback/high-stakes/repo-mandated only; Gemini is not a route.
- **Branch:** `feat/E50.1-fe-types-and-hooks` off `main` — created by `bmad-dev-story`, **not** by this spec run. `epic-50` and the `50-1` status flip past `ready-for-dev` are controller-owned.
- **Deploy:** the story touches `apps/web/**` only, so a merge to `main` is a non-skip-prefixed commit and deploys normally. Nothing in this story requires a deploy decision at create time.

---

## 10. Scope fences (explicit "do not")

- No `validateSearch` / URL-state change (`routes/catalog/index.tsx`) — **Story 50.2**.
- No suggestion surface, no `GET /api/tags?q=` consumer change — **Story 50.3**.
- No component, route, rail, chip, or admin screen — **E51/E52**.
- No i18n key, no `en.json`/`pl.json` edit, no a11y assertion, no visual spec or baseline — this story renders nothing (`epics.md:4505`).
- No `BrowseCategoryAdminRead`, no admin mutation hook, no `PUT /api/admin/models/{id}/categories` client — **Story 52.2** (D-2).
- No backend, migration, seed, `_PUBLIC_ROUTES`, or OpenAPI change.
- No `package.json`/lockfile change, no MSW, no codegen, no query-key factory, no `select` transform.
- No `routeTree` regeneration — no route param changes ([[reference_web_routetree_regen]] does not apply).
- No touch to `lib/share-api.ts` (D-6), `useTags`, `useTagGroups`, `useModel`, or `ModelSummary`.

---

## 11. Verification performed for this spec

- `bmad-help` run (mandatory session start) → canonical route recorded in the header from `_bmad/_config/bmad-help.csv:26-28`; `_bmad/_config/skill-manifest.csv:40` confirms `bmad-create-story` at `_bmad/bmm/4-implementation/bmad-create-story/SKILL.md`. Effective config resolved via `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` (`communication_language: Polish`, `document_output_language`/committed content English, `implementation_artifacts` = `_bmad-output/implementation-artifacts`).
- Shipped E49 wire read from source at `910e976`, not from the epic sketch: `sot/schemas.py:87-133,207-225`; `sot/router.py:106-232`; `sot/service.py:176-247,505-575`; `sot/admin_router.py:146,177,212,244,290`.
- FE baseline read from source: `lib/api-types.ts:43-218`; `modules/catalog/hooks/{useTags,useTagGroups,useModel,useModels}.ts`; `lib/share-api.ts:29-49`; `routes/catalog/index.tsx:40-103`; `tests/visual/api-stubs.ts:1-50`.
- Negative greps across `apps/web/src`: `BrowseCategory` (0), `useCategories|useCategoryBySlug|useCategoriesTree` (0), `CategorySummary|CategoryNode|CategoryTree` (0), `category` in `routes/catalog/index.tsx` (0). Correct RED baseline; no retired symbol to resurrect.
- `ModelDetail` literal-construction sites enumerated exhaustively (§7.4): ten `*.test.tsx` fixtures, zero production sites.
- Inherited 49.3 CR-2 (OpenAPI optionality of `categories`) read from `49-3-…md:811,928` and resolved in D-1 rather than rediscovered.
- Precedent stories read in full: `43-1-api-types.md` (type story shape, RED gate, mechanical-fallout pattern), `43-2-hooks.md` (hook shape, cache-coherence table, key/`staleTime` justification convention).
- No pre-existing `50-1-*` artifact; `sprint-status.yaml` had `50-1-fe-types-and-hooks: backlog` under `epic-50: backlog` with no other Initiative 26 story in progress (`49-1`…`49-5` all `done`, `epic-49: done`).

---

## 12. Validation record — native `bmad-create-story:validate` (VS), 2026-07-28

**Verdict: PASS.** Independent fresh-context validation pass over the created artifact against `checklist.md`, re-tracing the shipped wire rather than trusting §2. The story mirrors the shipped E49 contract field-for-field, its RED→GREEN path is executable under the real `tsc -b`/vitest config, its scope fences match the epic sketch and Decision AY, and the mechanical fallout is enumerated exhaustively rather than promised.

**Provenance honesty.** This was a second pass over the artifact by the same session, not a separate fresh-context agent — the strongest available form here, and it is labelled as such rather than dressed up as an independent reviewer. Items 1–6 below are the disaster classes the Create pass anticipated and resolved while authoring; the Validate pass **re-verified each one at source** (results in the block after the list) rather than trusting the story's own §2. Item 7 is the one defect this pass actually caught in the created artifact and corrected. All edits are spec-only; no production or test code was touched.

**Findings (each resolved in-place):**

1. **[critical — regression disaster] The `ModelDetail.categories` requiredness fallout was under-specified.** The first draft asserted requiredness (D-1) without enumerating the construction sites it breaks, which is precisely the failure 43.1 hit and recorded ("required mechanical fallout"). A dev agent would have discovered ten `tsc` errors mid-implementation and had to choose between widening scope silently and weakening the type. **Fixed:** §7.4 now enumerates all ten sites by path, states the one-line change, names the three verified *non*-affected sites, and instructs the dev agent to **stop and report** if `tsc` names an eleventh.
2. **[important — reinvention/scope] `BrowseCategoryAdminRead` had no recorded disposition.** It ships on the backend (49.5) and a dev agent mirroring "the browse-category schemas" would plausibly have added it. **Fixed:** D-2 excludes it with the SoT trace (absent from `epics.md:4505`, Decision AY's frontend line, and the sprint-status text), assigns it to 52.2, and contrasts the 43.1 `TagGroupSummary` case so the asymmetry reads as deliberate.
3. **[important — magic constant] `staleTime: 5 * 60 * 1000` was justified by neighbour-matching.** project-context §287 classifies "matches the sibling hook" as a category error; the justification must point at the contract. **Fixed:** D-3 now points at FR26-CAT-1 + the 49.5 admin-only mutation surface, and demotes the coincidence with `useTagGroups` to a consequence.
4. **[important — cache coherence] The by-slug key could be seeded from the list result, and the draft was silent.** Silence would have left a dev agent free to add `setQueryData` "for free", which would resolve a 404-on-unknown-slug from a stale list and destroy the Decision AY distinction. **Fixed:** §5 records the explicit no-seeding choice with its reason, and the 404-is-a-real-error row is now in the retry-policy line and in AC-5/§7.2.
5. **[minor — test disaster] Missing `afterEach(cleanup)` reminder.** Two new multi-`it` test files under `globals: false` would accumulate DOM nodes and fail with *"Found multiple elements"* (project-context §115, hit 3×). **Fixed:** §7 states it as a non-negotiable convention.
6. **[minor — honesty] 49.3's CR-2 note says "Story 50.1's type generation will emit an optional property".** There is **no** codegen in this repo (43.1 §6). **Fixed:** §2 and D-1/D-5 restate the fact accurately — the document artefact is inherited as a *fact*, and the FE choice is an explicit hand-typing decision, not a generator output.
7. **[important — false state signal; caught by this pass] The draft change log recorded `epic-50` `backlog` → `in-progress`.** The vanilla workflow flips the epic when its first story is created, but this repo's recorded precedent is the opposite and was applied three times: `sprint-status.yaml`'s `epic-49` comment states the epic was *"FLIPPED 2026-07-26 from backlog by native `bmad-dev-story` (DS) … the project's 43.1/47.5 precedent (flip the epic at dev-story)"*, and the `49-5` create+validate commit (`b1a46a2`) changed **only** the story key and `last_updated`. Flipping `epic-50` now would announce that Initiative 26 frontend work is underway when no dev-go exists and no code has been written. **Fixed:** `epic-50` is left at `backlog`; the deviation from the workflow's default and its reason are recorded in `sprint-status.yaml` and in §16 for the controller to overturn cheaply if it prefers the vanilla flip.

**Independently verified against source (no defect found):**

- **Shipped schemas** (`sot/schemas.py:87-133`): `BrowseCategorySummary` six keys ✓; `BrowseCategoryRead` +3 with **required** `model_count` ✓; `inclusion_criterion` only on `BrowseCategoryAdminRead` ✓; `ModelDetail.categories: list[BrowseCategorySummary]` on the subclass, `ModelSummary` clean ✓. §3 mirrors all of them field-for-field, nullability included.
- **Shipped routes** (`router.py:106-232`): `list[BrowseCategoryRead]` / `BrowseCategoryRead` + 404 / `category: str | None` single-slug param, unknown slug → 200 empty page ✓. AC-4/5/6 match.
- **Single `ModelDetail` constructor** (`service.py:558-570` writes `"categories"` unconditionally; all six `response_model=ModelDetail` routes funnel through `get_model_detail`) → D-1's "the wire always sends it" is verified, not assumed.
- **FE baseline:** `api-types.ts` has no browse-category symbol and `ModelDetail` has no `categories` (correct RED); no name collision for `BrowseCategorySummary`/`BrowseCategoryRead`/`useCategories`/`useCategoryBySlug`; `["sot","categories"]` is free (the 47.4-deleted `useCategoriesTree` that once held it is gone, and an in-memory cache cannot carry a stale entry across a page load).
- **Type config:** `strict` + `noUncheckedIndexedAccess` on (does not affect known-literal-key access, so `ModelDetail["categories"]` is exactly `BrowseCategorySummary[]`); `exactOptionalPropertyTypes` **not** set — which is what makes the D-1 requiredness assertion in §7.1 meaningful (an optional key would widen to `| undefined` and fail).
- **Scope fences** hold against the SoT: no URL state (50.2), no suggestions (50.3), no UI (E51/E52), no i18n/a11y/visual (explicitly disclaimed by `epics.md:4505` and the NFR matrix `:4417-4420`), no share-DTO touch (Decision AY invariants), no route-tree regen.
- **Toolchain facts the ACs depend on, re-read at source by this pass:** `apps/web/vitest.config.ts:34-35` — `environment: "jsdom"`, **`globals: false`** (so §7's `afterEach(cleanup)` rule is load-bearing, not decorative); `apps/web/tsconfig.json:8,12,23` — `strict: true`, `noUncheckedIndexedAccess: true`, **`exactOptionalPropertyTypes` absent**, `include: ["src","tests"]` (test files are typechecked, which is what makes `tsc -b` the RED gate); `apps/web/src/lib/api.ts:3,30` — `const BASE = "/api"` prepended to every call, confirming AC-4/AC-5's emitted paths; `useModels.test.tsx` has nine `it` blocks asserting exact URLs, so §7.3's "existing assertions stay green with no edit" is a real regression lock rather than an assumption.
- **Gates:** `git status` clean at creation; `sprint-status.yaml` re-parsed with `yaml.safe_load` after the edit — well-formed, 336 `development_status` keys, `50-1-fe-types-and-hooks: ready-for-dev`, `epic-50: backlog`, `epic-49: done`. Validation edits are tracked-doc only (this artifact + `sprint-status.yaml`), per the VS remit.

**Not verified (out of remit, stated rather than implied):** no code was written, no test was executed, and no build/typecheck was run for this story — the RED evidence in §8 is a dev-time obligation, not a claim already discharged. No human review is recorded.

---

## 13. Tasks / Subtasks — dev execution (native `bmad-dev-story`, after G26-DEVGO)

- [x] **T1 — RED first (types).** Author `apps/web/src/lib/api-types-categories.test.ts` per §7.1 (`expectTypeOf`; no `as`/`any`/cast; `satisfies` wire fixture). Capture RED under `npm run typecheck` → `.hermes/run-logs/e50.1-red-typecheck.log`.
- [x] **T2 — RED first (hooks + filter).** Author `useCategories.test.tsx`, `useCategoryBySlug.test.tsx` (§7.2) and the two net-new `useModels.test.tsx` cases (§7.3), each with `afterEach(cleanup)`. Capture **both** the runtime RED (unresolved import, vitest) and the type RED (`TS2307` + `TS2353` on `category`).
- [x] **T3 — GREEN types.** Add `BrowseCategorySummary` + `BrowseCategoryRead` and the required `ModelDetail.categories` to `api-types.ts` (§3.1–3.2), mirroring `sot/schemas.py:87-120,207-220` field-for-field.
- [x] **T4 — GREEN hooks.** Create `useCategories.ts` and `useCategoryBySlug.ts` (§3.3) — inline keys, 5-min `staleTime`, no `select`/`retry`/`onError`/factory/`enabled`.
- [x] **T5 — GREEN `useModels`.** Add `category?: string` to `ModelsFilters` and the single guarded `buildParams` branch (§3.4). Existing branches, key, `staleTime`, `keepPreviousData` and `PAGE_SIZE` byte-unchanged.
- [x] **T6 — Mechanical fallout.** Add `categories: []` to the ten `makeDetail` fixtures in §7.4 — one line each, nothing else. If `tsc` names a site outside the list, **stop and report** instead of editing it.
- [x] **T7 — Preserve.** `git diff` shows zero lines in `lib/share-api.ts`, `useTags.ts`, `useTagGroups.ts`, `useModel.ts`, `routes/catalog/index.tsx`, `locales/*.json`, `tests/visual/**`, `apps/api/**`, `routeTree.gen.ts`, `package.json`/lockfile.
- [x] **T8 — Green gates.** Focused vitest, `npm run typecheck`, `npm run lint`, full `npm run test` ×3 (identical counts), `npm run build`. `git diff --check` clean. No snapshot update. Evidence → `.hermes/run-logs/e50.1-green-*.log`.

### Review Findings (native `bmad-code-review`, CR pass 1, 2026-07-28)

**Verdict `APPROVE`. Critical: none. Important: none. Patch: none. Decision-needed: none.** Triage: **0 decision-needed, 0 patch, 2 defer, 1 minor-recorded, 3 dismissed.** Severities are this pass's own (step-03 rule 4). Full evidence, method and disclosed deviations in §17; durable report `.hermes/run-logs/e50-1-native-code-review-20260728.md`.

**Defer (2)**

- [x] [Review][Defer] `useCategoryBySlug` interpolates the slug into the path without `encodeURIComponent` [apps/web/src/modules/catalog/hooks/useCategoryBySlug.ts:16] — deferred to **Story 51.2** (the first caller). Measured, not reasoned: against the real app router, `/api/categories/kitchen%23x`, `%3Fx` and `%20x` all reach the endpoint (401 auth gate = route matched), so encoding *would* work; unencoded, `fetch("/api/categories/kitchen#x")` drops the fragment and `…/kitchen?x` splits the query, so a slug containing `#` or `?` silently addresses a **different** category instead of 404-ing. Raw `/` matches no route either way (`/api/categories/a/b` → 404), so encoding cannot rescue that case. Reachability today is **zero** — the hook has no caller until 51.2 — and the root cause is an already-ledgered 49.5 defer (admin `slug` has no format validation, `BrowseCategoryCreate.slug = Field(min_length=1)`, stored verbatim by `create_browse_category`). Not charged as `patch` because AC-5 pins the literal expression `` api<BrowseCategoryRead>(`/categories/${slug}`) `` and this story's scope is frozen; a one-line `encodeURIComponent(slug)` is a cheap controller-electable hardening if preferred over deferral.
- [x] [Review][Defer] `useCategoryBySlug("")` resolves against the LIST endpoint and returns an array typed as a single object [apps/web/src/modules/catalog/hooks/useCategoryBySlug.ts:16] — deferred to **Story 51.2**. Measured: `GET /api/categories/` → **307** → `/api/categories` (`app.router.redirect_slashes` is `True`), which `fetch` follows, so an authenticated caller receives `BrowseCategoryRead[]` while `.data` is typed `BrowseCategoryRead` — a silent type lie rather than an error. D-4 already records the caller contract (non-empty slug, no `enabled` guard, mirroring `useModel`) and 51.2 supplies the slug from a route param that is non-empty by construction, so this is a latent contract edge, not a live defect.

**Minor (1, recorded not charged)** — `useCategoryBySlug.test.tsx` has no explicit loading→success (`isLoading`) assertion, which AC-9's summary sentence lists for "hook unit tests" generically. The tests match **§7.2's** per-hook enumeration verbatim (§7.2 gives `useCategories` five cases including loading, and `useCategoryBySlug` five cases that swap loading/cache for 404 + key isolation), and §7.2 is the operative specification. Recorded for transparency; no coverage the story asked for is missing.

**Dismissed as noise (3)** — (a) "`ModelDetail.categories` typed required contradicts the OpenAPI document's non-required marking": re-derived at source, all **six** `response_model=ModelDetail` routes (`router.py:237`, `admin_router.py:146,177,212,244,290`) funnel through the single `get_model_detail`, which writes `"categories"` unconditionally (`service.py:568-572`), and all **seven** FE `ModelDetail` call sites hit exactly those routes — D-1 holds on the wire. (b) "`as string` casts in the two new `useModels.test.tsx` cases violate AC-8": AC-8 scopes the no-cast rule to the type-level test (which has **zero** casts), and the two new lines reproduce nine byte-identical pre-existing lines in the same file. (c) "the type-level test asserts nothing at runtime, so it is vacuous": disproved by this pass's own mutation probes — it is enforced by `tsc -b`, which is a real `check-all.sh` stage.

## 14. Dev Agent Record

### 14.1 Agent Model Used

Claude Opus 5 (1M context) — `claude-opus-5[1m]`, native `bmad-dev-story` (DS), repo-local BMAD skill, single session, 2026-07-28. Routing re-confirmed by a mandatory `bmad-help` run at the scope pivot from create/validate to development: `_bmad/_config/bmad-help.csv` places `bmad-dev-story` (DS) in phase `4-implementation` as the `required` step preceded by `bmad-create-story`, followed by the optional `bmad-code-review` (CR). No route-around, no skill protest.

### 14.2 Debug Log References

All logs teed to the gitignored `.hermes/run-logs/` (see `.gitignore:127-130`). Working directory for every `npm` command is `apps/web/`.

**RED (captured before any production line was written):**

| Log | Command | Result |
|---|---|---|
| `e50.1-red-typecheck.log` | `npm run typecheck` (after T1, then appended after T2) | rc=1. T1: `TS2305` ×2 — `'@/lib/api-types'` has no exported member `BrowseCategoryRead` / `BrowseCategorySummary`; `TS2339` — property `categories` does not exist on type `ModelDetail`. T2 append: `TS2307` ×2 — cannot find module `./useCategories` / `./useCategoryBySlug`; `TS2353` ×2 — `'category'` does not exist in type `ModelsFilters` (`useModels.test.tsx:180,189`). |
| `e50.1-red-vitest.log` | `npx vitest run` on the three hook/filter test files | `Test Files 3 failed (3)`, `Tests 1 failed \| 10 passed (11)`. Two files failed to transform (`Failed to resolve import "./useCategories"` / `"./useCategoryBySlug"`) — the **runtime** RED; `useModels.test.tsx` failed behaviourally: `expected '/api/models?sort=recent&offset=0&limit=48' to contain 'category=kitchen'`. |

Both RED forms were required and both are recorded: the type RED alone is insufficient evidence for a new file (43.2 precedent), and `vitest run` alone cannot be the type gate because esbuild erases `import type`/`expectTypeOf` at runtime (§8.5, 43.1 AC-6, 35.5).

**GREEN:**

| Log | Command | Result |
|---|---|---|
| `e50.1-green-typecheck.log` | `npm run typecheck` (`tsc -b`) | rc=0, zero diagnostics. |
| `e50.1-green-vitest-focused.log` | `npx vitest run` on the four story-owned files | `Test Files 4 passed (4)`, `Tests 28 passed (28)` — `api-types-categories.test.ts` 7, `useModels.test.tsx` 11 (9 pre-existing + 2 net-new), `useCategories.test.tsx` 5, `useCategoryBySlug.test.tsx` 5. |
| `e50.1-green-lint.log` | `npm run lint` (`eslint . --max-warnings=0 && stylelint`) | rc=0. Only the pre-existing, unrelated "React version not specified in eslint-plugin-react settings" notice. |
| `e50.1-green-vitest-full-{1,2,3}.log` | `npm run test` ×3 consecutive | `139 passed (139)` files / **`804 passed (804)`** tests, identical all three runs → **NFR26-DETERMINISM-1 satisfied**. Zero regressions. |
| `e50.1-green-build.log` | `npm run build` | rc=0, `✓ built in 10.13s`. Only the pre-existing chunk-size advisory. |

`git diff --check` → rc=0 (clean). No `--update-snapshots` was run at any point.

### 14.3 Completion Notes List

**What was actually implemented and tested** — all four deliverables of §3, nothing else.

1. **`api-types.ts` (+36 lines, −0).** `BrowseCategorySummary` (exact six keys, no `model_count`, no `children`) and `BrowseCategoryRead extends BrowseCategorySummary` (+`description_en`/`description_pl` `string | null`, +**required** `model_count: number`, no `inclusion_criterion`), plus `ModelDetail.categories: BrowseCategorySummary[]` as a **required** field. Mirrored field-for-field against the shipped Pydantic source re-read at `910e976` in this pass (`sot/schemas.py:87-133,207-225`) rather than trusting §2 — the standing epic:47 `VERIFY-AT-CREATE-STORY` obligation. `ModelSummary` untouched.
2. **Two hooks.** `useCategories.ts` and `useCategoryBySlug.ts`, each mirroring `useTagGroups`/`useModel` in shape: inline query key, 5-min `staleTime`, no `select`, no local `retry`/`onError`/`throwOnError`, no key factory, no `enabled` guard (D-4). Both call `api()`; neither touches `fetch` directly. The by-slug key is **not** seeded from the list result (D-3/§5) — the reason is recorded as a code comment so a later reader cannot "optimize" the 404 distinction away.
3. **`useModels` (+5 lines, −0).** `ModelsFilters.category?: string` plus one guarded `buildParams` branch placed after `source` and before `q`, matching the backend parameter order at `router.py:196-208`. Emits only for a non-empty string, so every pre-50.1 caller's URL and `["sot","models",filters]` key are byte-identical.
4. **Tests.** 22 net-new assertions across three files. Type-level (`api-types-categories.test.ts`): structural six-key equality, the two negative `model_count`/`children`/`subcategories` fences, the `inclusion_criterion` fence, required-`model_count`, the D-1 requiredness proof `ModelDetail["categories"] toEqualTypeOf<BrowseCategorySummary[]>` (no `| undefined`), the AC-3 negative `ModelSummary` assertion, and a four-item `satisfies BrowseCategoryRead[]` wire fixture covering top-level, child, `name_pl: null` and `model_count: 0`. Hook tests intercept at `fetch` via `vi.stubGlobal` (never a mocked `api()`), pin `retry: false`, and both carry `afterEach(cleanup)` per project-context §115. `useCategoryBySlug` asserts the 404 surfaces as `isError` **with `data` left `undefined`** and exactly one fetch — the Decision AY distinction, proven not swallowed.
5. **Mechanical fallout (D-1) — pre-enumeration held exactly.** `tsc` was used as the enumerator and named **precisely the ten** `makeDetail` fixture sites §7.4 predicted, no eleventh. Each received exactly one line (`categories: [],`); `git diff --numstat` shows `1 0` for all ten — one insertion, zero deletions. No production site required a change. The §7.4 "stop and report" escape hatch was therefore not triggered.
6. **Additive-only, proven mechanically.** `git diff --numstat` over `apps/web/` shows **zero deletions in every touched file** (`36 0`, `26 0`, `5 0`, and `1 0` ×10). The nine pre-existing `useModels` URL assertions are byte-unchanged and green without edits — the §7.3 regression lock. `git status --porcelain` over `apps/api`, `apps/worker`, `infra`, `lib/share-api.ts`, `useTags.ts`, `useTagGroups.ts`, `useModel.ts`, `src/routes/**`, `src/locales/**`, `apps/web/tests/**`, `package.json` and the lockfiles returns **empty**. No `routeTree.gen.ts` change, no visual baseline added/changed/regenerated, no i18n key, no dependency change, no codegen.

**Caveats, stated rather than implied:**

- **`npm run test:visual` was NOT run** in this pass. This story renders nothing and touches no `apps/web/tests/**` file or snapshot, so AC-10's "green **unchanged**" is expected to hold by construction — but it is a controller-owned gate inside `infra/scripts/check-all.sh` and is **not claimed as verified here**.
- **`infra/scripts/check-all.sh` was NOT run** — controller-owned closeout gate (§9). The backend suite was not executed either; the backend is byte-unchanged, which is asserted from `git status`, not from a test run.
- **No commit, stage, push, merge, deploy, migration, seed, live-DB or network action** was taken. No Aider, no Codex, no Gemini. **No human review of any kind** — G26-DEVGO is Laura/controller authorization only, not an Ezop signature.
- **`epic-50` deliberately left at `backlog`.** The repo's 43.1/47.5/49.1 precedent flips the epic at `bmad-dev-story`, but this story's own §9 assigns `epic-50` to the controller, so this pass did not take the flip. The resulting `epic-50: backlog` / `50-1: review` combination is a knowing, recorded state, cheap for the controller to overturn with a one-line edit.
- The `TS2554` diagnostics visible in the T1 RED log on the `.not.toHaveProperty(...)` lines were artifacts of the receiver being an unresolved error type; they disappeared on their own at GREEN with no test edit.

## 15. File List (actual)

Verified against `git status --short` + `git diff --numstat` at the end of the dev pass. **Sixteen** code paths (5 new, 11 modified) + 2 tracked docs. Deletions: **zero, in every file**.

New (5):

- `apps/web/src/lib/api-types-categories.test.ts` — RED-first type-level test (7 `it` blocks).
- `apps/web/src/modules/catalog/hooks/useCategories.ts`
- `apps/web/src/modules/catalog/hooks/useCategories.test.tsx` — 5 `it` blocks.
- `apps/web/src/modules/catalog/hooks/useCategoryBySlug.ts`
- `apps/web/src/modules/catalog/hooks/useCategoryBySlug.test.tsx` — 5 `it` blocks.

Modified (11):

- `apps/web/src/lib/api-types.ts` (+36 −0) — `BrowseCategorySummary`, `BrowseCategoryRead`, required `ModelDetail.categories`.
- `apps/web/src/modules/catalog/hooks/useModels.ts` (+5 −0) — `ModelsFilters.category?` + one guarded `buildParams` branch.
- `apps/web/src/modules/catalog/hooks/useModels.test.tsx` (+26 −0) — two net-new cases; the nine pre-existing URL assertions byte-unchanged.
- `apps/web/src/modules/catalog/components/DescriptionPanel.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/MetadataPanel.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/SecondaryTabs.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/TagGroupsSection.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/dialogs/DeleteModelDialog.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/sheets/EditDescriptionSheet.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/sheets/EditTagsSheet.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/sheets/RenderSheet.test.tsx` (+1 −0)
- `apps/web/src/modules/catalog/components/tabs/PhotosTab.test.tsx` (+1 −0)

*(The last ten are the §7.4 mechanical fallout — `categories: [],` and nothing else, exactly as pre-enumerated.)*

Docs (tracked, modified): this artifact; `_bmad-output/implementation-artifacts/sprint-status.yaml`.

Untracked evidence (gitignored, NOT part of the diff): `.hermes/run-logs/e50.1-red-*.log`, `.hermes/run-logs/e50.1-green-*.log`.

## 16. Change Log

| Date | Change |
|---|---|
| 2026-07-28 | Created via native `bmad-create-story` (Create) at `main` @ `910e976` after mandatory `bmad-help`; shipped E49 wire and FE baseline re-traced at source per the epic:47 `VERIFY-AT-CREATE-STORY` action item. |
| 2026-07-28 | Native `bmad-dev-story` (DS) — **IMPLEMENTED**, story `ready-for-dev` → `in-progress` → `review`, under Laura/controller **G26-DEVGO** for the exact validated scope (controller authorization only; **no Ezop signature, no human review**). Routing re-confirmed by a mandatory `bmad-help` run at the create/validate → development pivot. All eight tasks T1–T8 complete. RED captured before any production line in **both** required forms (type: `TS2305`/`TS2339`/`TS2307`/`TS2353`; runtime: unresolved-import transform failure + a behavioural `category=kitchen` assertion failure), then GREEN: `tsc -b` rc=0, `eslint --max-warnings=0` rc=0, focused vitest 28/28, full vitest **804 passed ×3 identical** (NFR26-DETERMINISM-1 satisfied), `npm run build` rc=0, `git diff --check` rc=0. Strictly additive — **zero deletions in every touched file**; the nine pre-existing `useModels` URL assertions green with no edit. D-1's mechanical fallout hit **exactly the ten** pre-enumerated `makeDetail` fixtures, no eleventh site, one line each. Fences verified empty by `git status --porcelain`: `apps/api`, `apps/worker`, `infra`, `share-api.ts`, `useTags`/`useTagGroups`/`useModel`, `src/routes/**`, `src/locales/**`, `apps/web/tests/**`, `package.json`/lockfiles, `routeTree.gen.ts`. **NOT run and NOT claimed:** `npm run test:visual`, `infra/scripts/check-all.sh`, backend suite — all controller-owned closeout gates. No commit, stage, push, merge, deploy or live action; no Aider, Codex or Gemini. `epic-50` deliberately left at `backlog` per this story's §9 (controller-owned), a knowing deviation from the 43.1/47.5/49.1 flip-at-dev-story precedent. Next: native `bmad-code-review` (CR). |
| 2026-07-28 | Native `bmad-code-review` (CR) pass 1 — **literal verdict `APPROVE`**, native BMAD agent approval ONLY (no Ezop signature, no human review, no Aider/Codex/Gemini). Status **held at `review`**, deliberately not `done` (§17 disclosed deviation 2). Every AC re-derived from source rather than from §14's prose; all four DS-claimed gates independently reproduced (`tsc -b --force` rc=0, `eslint --max-warnings=0` rc=0, focused vitest 28/28, full vitest 139 files / **804 passed** — run **twice** by this pass, both identical); three mutation probes (two on `api-types.ts`, one on `useModels.ts`) proved the new type fences and the `buildParams` branch non-vacuous, each restore sha-asserted. Triage: 0 decision-needed, 0 patch, 2 defer (both → Story 51.2, appended to `deferred-work.md`), 1 minor-recorded, 3 dismissed. **NOT run and NOT claimed:** `npm run test:visual`, `infra/scripts/check-all.sh`, the backend suite. No commit, stage, push, merge, deploy or live action; no code file edited. |
| 2026-07-28 | **Independent external review — `laura-aider-review-diff` / Aider v0.86.2 (OpenRouter DeepSeek): literal verdict `APPROVE`.** Log `.hermes/run-logs/e50-1-aider-review-20260728_181736.log`, `RUN_EXIT rc=0`. Critical: **none**. Important: **2** — both already recorded by native CR as deferred to **Story 51.2** (`useCategoryBySlug` slug not `encodeURIComponent`-encoded; `useCategoryBySlug("")` follows the 307 to the list endpoint and types an array as a single object). Minor: **1** — the missing explicit `isLoading` assertion in `useCategoryBySlug.test.tsx`, already recorded by native CR as minor with no missing story coverage. Missing tests: **none**. **No patch required for Story 50.1**; Aider made **no edits** to any file. The Laura Agent Rulebook's routine independent-review obligation is thereby **discharged**; status stays `review` because `infra/scripts/check-all.sh`, `npm run test:visual` and the commit / ff-merge / push / deploy chain remain unrun and controller-owned. `deferred-work.md` **not** touched — the two defers were already appended by the CR pass and no duplicate entry was added. No human review of any kind; no Codex, no Gemini. See §18. |
| 2026-07-28 | **Full closeout gate recorded — `infra/scripts/check-all.sh` all green, 16/16 stages, `all green.`** Log `.hermes/run-logs/check-all-e50-1-20260728_182040.log`; controller-reported exit marker `CHECK_ALL_RC=0 2026-07-28T18:31:26+02:00`. In-check-all figures read from the log: `apps/web vitest` **139 files / 804 tests passed**; `apps/web visual regression` **536 passed / 32 skipped**; `apps/api pytest` **1922 passed, 3 skipped**; `workers/render pytest` **21 passed**; `infra/scripts pytest` **13 passed**; ruff format/check ×4, typecheck, production build, lint, settings-env-compose-diff, both `uv-lock-check`s and `local-env-secrets` all ✓. This **discharges** the previously unclaimed `npm run test:visual` (AC-10's "green **unchanged**" — no baseline added, changed or regenerated) and backend-suite obligations. Gate run by the **controller**; this bookkeeping pass executed **nothing** and edited only this artifact and `sprint-status.yaml`. Status **held at `review`**, `epic-50` held at `backlog` — commit / ff-only merge / push / deploy / post-deploy smoke remain **owed and unclaimed**. No human review of any kind; no Codex, no Gemini. See §19. |
| 2026-07-28 | **FINAL CLOSEOUT — story `review` → `done`; `epic-50` `backlog` → `in-progress`.** Controller committed the implementation as **`9697d8c0095863e83c895b8de8e1ee7ba296a860`** (`feat(web): add browse category data hooks`), **fast-forward merged** `feat/E50.1-fe-types-and-hooks` into `main`, and pushed: `git push origin main` succeeded with the lean pre-push transport gate **11/11** passed; local `HEAD` and `origin/main` both verified at `9697d8c`, `git status --short --branch` → `## main...origin/main`. Deploy: `infra/scripts/deploy.sh` succeeded — log `.hermes/run-logs/deploy-e50-1-20260728_183653.log`, exit marker **`DEPLOY_RC=0 2026-07-28T18:40:05+02:00`**, script ended `Done.`; images built and shipped to `.190`, `docker compose` recreated **web + worker**, alembic migrations ran, the **slicer-worker overlay was correctly skipped** (no portal-api/slicer-adjacent change in `52519d851444828371b987eb2ab7cb6f2c778078..HEAD`), GlitchTip symbolication smoke matched **issue id=316** and verified release **`0.1.0+9697d8c`**, runbook fingerprint OK. Post-deploy smoke: all six `.190` services (`api`, `arq-worker`, `redis`, `slicer-worker`, `web`, `worker`) `running`; LAN `http://192.168.2.190:8090/api/health` → `{"status":"ok","version":"0.1.0"}`; LAN web **200**; production HTTPS `https://3d.ezop.ddns.net/` → **200**. Closeout authority: native BMAD `bmad-code-review` **APPROVE** + independent Aider **APPROVE** + `check-all.sh` **16/16** + the controller's own merge/push/deploy/smoke — **no human review of any kind, no Ezop signature, no Codex, no Gemini**. `epic-50` flipped to `in-progress` per the repo's `43.1`/`47.5`/`49.1` flip-at-first-real-work precedent (`epic-49`'s own comment records the same flip), now unambiguous with a shipped, deployed first story; `50-2` and `50-3` stay `backlog`, so `in-progress` — not `done` — is the truthful epic state. This bookkeeping pass ran **no** gate, test, build, script, commit, stage, push, merge or deploy and edited only this artifact and `sprint-status.yaml`; every figure above was read from the controller's report and cross-checked against the repo (`git rev-parse HEAD` / `origin/main`) and the teed deploy log. See §20. |
| 2026-07-28 | Native `bmad-create-story:validate` (Validate) — **PASS**; seven findings (1 critical, 4 important, 2 minor) resolved in-place, all spec-only. Status `ready-for-dev`; `sprint-status.yaml` `50-1-fe-types-and-hooks` `backlog` → `ready-for-dev`. **`epic-50` deliberately left at `backlog`** — a recorded deviation from the create-story workflow's default epic flip, following this repo's `43.1`/`47.5`/`49.1` precedent of flipping the epic at `bmad-dev-story`, and truthful about the fact that no implementation has started (finding 7). Controller may overturn it with a one-line edit. No implementation authorization recorded — **G26-DEVGO is the controller's to grant in a later run**. No commit, no push, no deploy; no human review; no Codex, Gemini or Aider in this pass. |

---

## 17. Code Review Record (native `bmad-code-review`, CR pass 1, 2026-07-28)

**Verdict: `APPROVE` — native BMAD agent approval ONLY.** Claude Opus 5 (1M context), model id `claude-opus-5[1m]`, repo-local native BMAD `bmad-code-review`, in `/home/ezop/repos/3d-portal` on branch `feat/E50.1-fe-types-and-hooks`, baseline `main` @ `910e976` (matches this artifact's `baseline_commit` frontmatter). **NO human review of any kind** — no Ezop signature, no Ezop review, no Laura review is recorded, implied or claimable. **Still owed and all controller-owned:** `infra/scripts/check-all.sh` all-green standalone with teed evidence, `npm run test:visual`, the backend suite, the independent external review `laura-aider-review-diff` / **Aider** (routine default per the Laura Agent Rulebook; Codex is fallback/high-stakes/explicit-operator-request only; **Gemini is not a default reviewer**), and the commit / ff-only merge / push / deploy chain. No commit, stage, push, merge, deploy, migration, seed, live-DB or network action; **no code or test file was edited** (the three mutation probes were restored byte-identically, sha-asserted). Durable report: `.hermes/run-logs/e50-1-native-code-review-20260728.md`.

**Routing (re-confirmed, not recalled).** `_bmad/_config/bmad-help.csv:29` — `bmad-code-review`, menu **CR**, phase `4-implementation`, `preceded-by=bmad-dev-story`, "Story cycle: If issues back to DS if approved then next CS or ER if epic complete." The story sits at `review` after a completed DS pass, so CR is the canonical next skill. `_bmad/_config/skill-manifest.csv:38` — canonical id `bmad-code-review`, module `bmm`; the manifest path `_bmad/bmm/4-implementation/…` does not exist in this worktree, so the installed body `.claude/skills/bmad-code-review/` (SKILL.md + `steps/step-01…04`) was used and followed 01→04. Customization resolved via `resolve_customization.py --key workflow`: no team or user override, `activation_steps_prepend`/`append` empty, `on_complete` empty, `persistent_facts=["file:{project-root}/**/project-context.md"]`. Step-01 Tier-1: `{spec_file}` = this artifact, branch diff vs `main` **plus** the complete dirty tree including untracked files, `{review_mode}="full"`, `{story_key}=50-1-fe-types-and-hooks`. `AGENTS.md`, `CLAUDE.md` and the Laura Agent Rulebook guard read before any review work.

**Scope re-derived, no file missed.** `git status --porcelain --untracked-files=all` → **exactly 20 paths** (18 code + 2 tracked docs), identical at session start, after every mutation probe and at close. `git diff main --numstat -- apps/web` → **503 insertions, 0 deletions** across 18 files — the additive-only claim is mechanical, not rhetorical. `git diff --check` exit 0. No untracked file outside that set (two `vitest.*.d.ts` artifacts emitted by this pass's own `tsc -b --force` were removed; the tree closed at the same 20 paths).

**AC-by-AC, verified at source.**

- **AC-1/AC-2/AC-3 (type shapes).** `api-types.ts:95-121` mirrors `sot/schemas.py:87-120` field-for-field: `BrowseCategorySummary` exactly six keys, no `model_count`, no `children`/`subcategories`; `BrowseCategoryRead extends` it with `description_en`/`description_pl: string | null` + required `model_count: number`, no `inclusion_criterion` (which lives only on the admin-only `BrowseCategoryAdminRead`, `schemas.py:123-133` — correctly out of scope per D-2). `ModelDetail.categories: BrowseCategorySummary[]` required; `ModelSummary` untouched.
- **AC-3 / D-1 requiredness holds on the wire.** Re-derived independently: **six** `response_model=ModelDetail` routes (`router.py:237`, `admin_router.py:146,177,212,244,290`), **all** funnelling through the one `get_model_detail`, which writes `"categories": categories` unconditionally (`service.py:568-572`); and **all seven** FE `ModelDetail` call sites (`useModel`, `useShareModelProbe`, `useUpdateModel`, `useSetThumbnail`, `AddModelForm`) hit exactly those routes. The only `setQueryData` in the FE is `["auth","me"]`, so no production code hand-builds a `ModelDetail` that the required key could break.
- **AC-4/AC-5 (hooks).** `useCategories.ts` / `useCategoryBySlug.ts` match the specified shape exactly — inline keys `["sot","categories"]` and `["sot","categories",slug]` (prefix relationship intact for a future single `invalidateQueries`), `staleTime: 5 * 60 * 1000`, no `select`, no local `retry`/`onError`/`throwOnError`, no key factory, no `enabled`. Emitted paths verified by test against `api()`'s `BASE = "/api"` (`lib/api.ts:3,30`): `/api/categories` and `/api/categories/kitchen`. The 404 branch is real: `api()` throws `ApiError` on any non-OK (`api.ts:46-53`) and the hook adds no swallow/default/retry — the test asserts `isError` **and** `data === undefined` **and** exactly one fetch. No cross-seeding from the list result (D-3/§5), with the reason recorded in-code so it cannot be "optimized" away.
- **AC-6 (`useModels`).** `ModelsFilters.category?: string` added; one guarded `buildParams` branch at `useModels.ts:61`, positioned after `source` and before `q`, matching the backend parameter order (`router.py:196-208`, `category: str | None = None`). Emits only for a non-empty string. `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `q`, `sort`, `offset`, `limit`, the `["sot","models",filters]` key, `staleTime` and `keepPreviousData` are byte-unchanged.
- **AC-7 (no drift).** Confirmed by the 20-path inventory: zero lines in `lib/share-api.ts` (`ShareModelView` / NFR25-LEAKFENCE-1 fence intact, D-6), `useTags.ts`, `useTagGroups.ts`, `useModel.ts`, `src/routes/**` (no `validateSearch` change — 50.2's job), `src/locales/**`, `apps/web/tests/visual/**`, `routeTree.gen.ts`, `package.json`/lockfiles, `apps/api/**`, `workers/**`, `infra/**`. No dependency, codegen, MSW, key-factory or `select` transform introduced.
- **AC-8 (no casts).** `api-types-categories.test.ts`, `useCategories.test.tsx`, `useCategoryBySlug.test.tsx`, `useCategories.ts` and `useCategoryBySlug.ts` contain **zero** `as` / `any` / `<any>` (the grep hits are prose inside `it(...)` titles and comments). The wire fixture is admitted by `satisfies BrowseCategoryRead[]`, not by a cast. The two `as string` lines in `useModels.test.tsx` reproduce nine byte-identical pre-existing lines — see the dismissed finding (b).
- **AC-9 (hook coverage).** Both hook tests intercept at `fetch` via `vi.stubGlobal` (never a mocked `api()`, so the CSRF header and 401-retry path stay live), pin `retry: false`, and carry `afterEach(cleanup)` per project-context §115. One coverage asymmetry recorded as Minor.
- **§7.4 (mechanical fallout) is exactly bounded.** `npx tsc -b --force` (full, not incremental) rc=0 → the ten `makeDetail` fixtures are the complete set; there is no eleventh site, and `git diff --numstat` shows `1 0` for each — one line, nothing else.
- **AC-11 (TDD) corroborated, not assumed.** `.hermes/run-logs/e50.1-red-typecheck.log` and `e50.1-red-vitest.log` exist with timestamps preceding every `-green-` log, and this pass reproduced the behavioural RED directly by mutation probe C.

**Independent gate reproduction (this pass's own runs, in `apps/web/`).**

| Command | Result |
|---|---|
| `npx tsc -b --force` | rc=0, zero diagnostics (full rebuild, not incremental) |
| `npm run lint -- --max-warnings=0` | rc=0 (only the pre-existing eslint-plugin-react version notice) |
| `npx vitest run` (four story-owned files) | `Test Files 4 passed (4)`, `Tests 28 passed (28)` |
| `npm run test` (full) ×2 | `139 passed (139)` / **`804 passed (804)`**, identical both runs |

Both figures match §14.2's claims exactly. Determinism was sampled **twice**, not three times — NFR26-DETERMINISM-1's triple remains the DS pass's claim plus this pass's two-run corroboration, and is stated as such rather than re-claimed.

**Mutation probes — the type fences are load-bearing, not decorative.** Each probe was applied to a `cp`-backed copy and restored byte-identically with the restore sha printed in the same command (`api-types.ts` → `sha256 9a28875fdecebadc…`, both times; `useModels.ts` → `sha256 2fdd2415ce8fad3c…`, `+5 −0` re-confirmed). No suite run overlapped any probe.

- **(A)** add `model_count: number` to `BrowseCategorySummary` → `tsc -b --force` rc=2, killed by **both** the structural-equality assertion (`TS2344`, `api-types-categories.test.ts:20`) and the `.not.toHaveProperty("model_count")` fence (`TS2554`, `:34`).
- **(B)** make `ModelDetail.categories` optional → rc=2, killed by the D-1 requiredness assertion (`TS2344 … does not satisfy the constraint '"Expected: …, Actual: undefined"'`, `:126`). This is the proof that the requiredness claim is enforced rather than asserted.
- **(C)** delete the `buildParams` category branch → focused vitest `1 failed | 10 passed (11)`, killed by exactly `emits category=<slug> when a category filter is set`, with the nine pre-existing URL assertions still green — the §7.3 regression lock verified in both directions.

**Backend probes (read-only, `TestClient`, no DB writes).** `GET /api/categories/` → **307** → `/api/categories` (`redirect_slashes=True`); `/api/categories/kitchen`, `…/kitchen%23x`, `…/kitchen%3Fx`, `…/kitchen%20x` → **401** (route matched, auth gate reached); `/api/categories/a/b` and `/api/categories/kitchen%2Fsub` → **404** (no route). These four lines are the measurement behind both defers.

**Why `APPROVE`.** The diff is strictly additive (503/0), every AC re-derives from source rather than from the implementer's prose, all four claimed gates reproduce on this pass's own runs, the new type fences and the new production branch are proven non-vacuous by mutation, the D-1 requiredness bet is verified against all six backend routes and all seven FE call sites, and every scope fence in §10 is empty in the actual inventory. Nothing found is a security, authorization, data-corruption, data-loss or merge-blocking defect. The two open items are edges of a hook that **has no caller until Story 51.2**, one of which is the frontend face of an already-ledgered 49.5 backend defer — neither is `patch`-class inside this story's frozen scope, and no unresolved `high`/`medium` finding remains.

**Disclosed deviations from the base workflow.**

1. **Step-02's three layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor) were executed inline by this session rather than as three blind subagents**, under a standing harness constraint against dispatching subagents the operator did not request. All three methods were applied to the full 20-path diff, but they were **not independently blind** — stated so it can be weighed. Partial compensation: every finding and every dismissal is backed by an executed probe (three mutations, four routing probes, four gate reruns) rather than by reading alone.
2. **Step-04 §6's status rule was deliberately NOT followed to `done`.** Its literal text sets `done` on a zero-patch triage, but `check-all.sh`, `test:visual`, the backend suite, the Aider review and the whole commit/merge/deploy chain are unrun and controller-owned, so `done` would be a false claim. `Status: review` preserved — the same disclosed deviation the 49.5 CR passes took, and what the controller's own instruction for this run directs.
3. **Step-01's CHECKPOINT and step-04's §4/§5/§7 HALTs were not honoured interactively** — non-interactive automation session; the Tier-1 argument fully determined the target, and with zero `decision-needed` and zero `patch` findings §4 and §5 did not apply.
4. **`epic-50` left untouched at `backlog`.** The DS pass's knowing deviation is preserved, not silently corrected; it stays a one-line controller edit.
5. `deferred-work.md` **was** written by this pass (both defers appended under a `## Deferred from: code review of 50-1-fe-types-and-hooks (2026-07-28)` heading) — the ledger gap the 49.5 passes had to disclose five times does not recur here.
6. `npm run test:visual`, `infra/scripts/check-all.sh` and the backend suite were **not run and are not claimed**. This story renders nothing and touches no snapshot, so visual is *expected* green by construction — an expectation, not a measurement.
7. This record is English per `CLAUDE.md` and `document_output_language`; the conversational surface is Polish per `communication_language`.

---

## 18. Independent external review record (`laura-aider-review-diff` / Aider, 2026-07-28)

**Verdict: `APPROVE`.** Recorded by the controller from the run log; this bookkeeping pass did **not** re-run the review and did not re-derive its findings.

| Field | Value |
|---|---|
| Tool | `laura-aider-review-diff` — **Aider v0.86.2**, model routed via **OpenRouter DeepSeek** |
| Log | `.hermes/run-logs/e50-1-aider-review-20260728_181736.log` (gitignored) |
| Exit | `RUN_EXIT rc=0` |
| Verdict | **`APPROVE`** |
| Critical | **none** |
| Important | **2** (both pre-recorded defers — below) |
| Minor | **1** (pre-recorded — below) |
| Missing tests | **none** |
| Edits made by Aider | **none** — the review was read-only; no file was changed |

**Routing provenance.** Per the Laura Agent Rulebook guard (`~/.local/share/laura-agent-ops/LAURA_AGENT_RULEBOOK.md`, digest in the global `CLAUDE.md`), `laura-aider-review-diff` / Aider is the **routine diff-review default**. Codex is fallback / high-stakes / explicit-operator-request only; **Gemini is not a default reviewer**. This story took the routine route, so the §9 / §17 "independent external review" obligation is **discharged**.

**Important ×2 — no new work, both already ledgered.** Aider independently surfaced exactly the two edges the native CR pass had already triaged as `defer` → **Story 51.2**, and reached the same disposition:

1. `useCategoryBySlug` does not `encodeURIComponent` the slug, so a slug containing `#` or `?` can address a **different** category (or a different route behaviour) instead of 404-ing. Aider likewise attributes the root cause to the backend's missing slug-format validation (the already-ledgered Story 49.5 defer).
2. `useCategoryBySlug("")` follows the backend's 307 slash-redirect to the **list** endpoint, so an array can arrive typed as a single `BrowseCategoryRead`.

Both are recorded in §13 "Defer (2)" and were appended to `deferred-work.md` by the CR pass under `## Deferred from: code review of 50-1-fe-types-and-hooks (2026-07-28)`. **No duplicate ledger entry was created by this pass** — independent corroboration of an existing entry is not a second entry.

**Minor ×1 — already recorded.** The missing explicit `isLoading` assertion in `useCategoryBySlug.test.tsx`, matching §13's minor-recorded item verbatim: the tests follow **§7.2**'s per-hook enumeration (which swaps loading/cache for 404 + key isolation on this hook), so **no coverage the story asked for is missing**.

**Consequence for Story 50.1.** **No patch is required.** Zero critical findings, zero new findings of any severity, and no test gap — the review adds independent corroboration, not work. The story's production and test diff is unchanged by this pass.

**Still owed after this pass (all controller-owned, none claimed here):** `infra/scripts/check-all.sh` all-green standalone with teed evidence, `npm run test:visual`, and the commit / ff-only merge to `main` / push / deploy chain. Status therefore **stays `review`**; `epic-50` stays at `backlog`.

**NOT claimed by this bookkeeping pass:** no human review of any kind (no Ezop signature, no Ezop review, no Laura review); no Codex; no Gemini; no test, build, typecheck, lint, `check-all.sh` or visual run; no code or test file edited; no commit, stage, push, merge, deploy, migration, seed, live-DB or network action. The only writes are this artifact and `sprint-status.yaml`.

---

## 19. Full closeout gate evidence — `infra/scripts/check-all.sh` (controller, 2026-07-28)

**Result: all green — 16/16 stages passed, literal trailer `all green.`** Run by the **controller**; this bookkeeping pass did **not** execute the gate and re-ran nothing. The counts below were read out of the teed log by this pass rather than copied from prose.

| Field | Value |
|---|---|
| Command | `infra/scripts/check-all.sh` (standalone, full 16-stage sweep) |
| Log | `.hermes/run-logs/check-all-e50-1-20260728_182040.log` (gitignored) |
| Exit marker | **`CHECK_ALL_RC=0 2026-07-28T18:31:26+02:00`** — controller-reported from the wrapper; the teed log itself terminates at the `all green.` trailer |
| Summary | **passed: 16**, failed: 0 — `all green.` |

**Per-stage counts, as recorded in the log:**

| Stage | Result |
|---|---|
| `apps/api ruff format` / `ruff check` | ✓ |
| `workers/render ruff format` / `ruff check` | ✓ |
| `apps/web typecheck` | ✓ |
| `apps/web production build` | ✓ |
| `apps/web lint (eslint + stylelint)` | ✓ |
| **`apps/web vitest`** | **`Test Files 139 passed (139)` / `Tests 804 passed (804)`** — identical to the DS and CR passes' figures |
| **`apps/api pytest`** | ✓ — `1922 passed, 3 skipped in 421.19s` |
| **`workers/render pytest`** | ✓ — `21 passed in 4.52s` |
| **`infra/scripts pytest`** | ✓ — `13 passed in 0.45s` |
| **`apps/web visual regression`** | ✓ — **`536 passed` / `32 skipped`** |
| `settings-env-compose-diff` | ✓ — 54 Settings fields / 52 env.example vars / 42 compose env refs aligned |
| `uv-lock-check (apps/api)` / `(workers/render)` | ✓ |
| `local-env-secrets` | ✓ |

**What this discharges.** Three obligations §9/§14.3/§17/§18 carried as explicitly *unrun and unclaimed* are now measured rather than expected:

1. **AC-10's `npm run test:visual` "green **unchanged**"** — the `apps/web visual regression` stage passed **536 / 32 skipped** inside check-all. The story adds, changes and regenerates **no** baseline (`apps/web/tests/**` is empty in the diff), so this is the *unchanged*-green the AC asked for, now verified instead of merely expected by construction.
2. **The backend suite** — `apps/api pytest` passed as a check-all stage, confirming the byte-unchanged-backend claim behaviourally and not only from `git status`.
3. **AC-10's full-gate green** — `tsc -b`, `eslint`/`stylelint`, `npm run build` and the full vitest suite all re-passed inside the same sweep.

**Still owed after this pass — all controller-owned, none claimed here:** the **commit**, the **ff-only merge to `main`**, the **push** to `origin/main`, the **deploy**, and the **post-deploy smoke**. Status therefore **stays `review`**, not `done`; `epic-50` stays at `backlog`.

**NOT claimed by this pass:** no human review of any kind (no Ezop signature, no Ezop review, no Laura review); no Codex; no Gemini; no gate, test, build or script executed by this pass; no code or test file edited; no commit, stage, push, merge, deploy, migration, seed, live-DB or network action. The only writes are this artifact and `sprint-status.yaml`.

---

## 20. Final closeout — commit, merge, push, deploy, post-deploy smoke (controller, 2026-07-28)

**Story `review` → `done`.** Everything §19 listed as still owed is now discharged. The chain below was executed **by the controller**; this bookkeeping pass executed **nothing** — it recorded the controller's report and cross-checked the parts that are checkable from the repo (`git rev-parse`, the teed deploy log).

### 20.1 Commit / merge / push

| Field | Value |
|---|---|
| Implementation commit | **`9697d8c0095863e83c895b8de8e1ee7ba296a860`** — `feat(web): add browse category data hooks` |
| Branch | `feat/E50.1-fe-types-and-hooks` |
| Merge | **fast-forward only** into `main` — no merge commit, linear history preserved |
| Push | `git push origin main` **succeeded**; lean **pre-push transport gate 11/11 passed** |
| Verified | local `HEAD` **and** `origin/main` both at `9697d8c0095863e83c895b8de8e1ee7ba296a860`; `git status --short --branch` → `## main...origin/main` (no ahead/behind, clean tree) |
| Pre-merge gate | already recorded in §19 — `infra/scripts/check-all.sh` **16/16 all green**, log `.hermes/run-logs/check-all-e50-1-20260728_182040.log` |

The commit sits directly on `910e976` (`docs: close Story 49.5 after deploy`), which is this artifact's `baseline_commit` frontmatter — so the reviewed baseline and the merged baseline are the same commit, with no rebase drift between review and merge.

### 20.2 Deploy — `infra/scripts/deploy.sh`

| Field | Value |
|---|---|
| Result | **succeeded** |
| Log | `.hermes/run-logs/deploy-e50-1-20260728_183653.log` (gitignored) |
| Exit marker | **`DEPLOY_RC=0 2026-07-28T18:40:05+02:00`** |
| Trailer | script ended **`Done.`** |

Evidence read out of the deploy log rather than paraphrased from prose:

- **Images built and shipped** to `ezop@192.168.2.190` — `portal-api:0.1.0`, `portal-render:0.1.0`, `portal-web:0.1.0` loaded on the host; release identity **`0.1.0+9697d8c`**, built at `2026-07-28T16:36:53Z`.
- **Stack restarted** — compose synced, then `3d-portal-web-1` and `3d-portal-worker-1` **Recreated → Started**; `redis`, `arq-worker` and `api` stayed `Running`.
- **Migrations ran** — `→ Run alembic migrations`, alembic context established and applied with no error. (This story is frontend-only and adds no revision; the stage still ran as part of the standard deploy.)
- **Slicer-worker overlay correctly skipped** — `[slicer-worker] no portal-api/slicer-adjacent change in '52519d851444828371b987eb2ab7cb6f2c778078..HEAD' — overlay rebuild not needed`, then `overlay rebuild not needed for this deploy — skipping`. Correct: the diff is `apps/web/**` only, so SW-DEPLOY-1's rebuild trigger genuinely does not fire.
- **GlitchTip symbolication smoke verified** — smoke event triggered, `→ Matched issue id=316`, `✓ verify OK — top frame: apps/web/src/main.tsx, release: 0.1.0+9697d8c`, and the smoke issue **id=316 deleted** from GlitchTip afterwards. The verified release string matches the merged SHA exactly.
- **Agent runbook fingerprint OK** — `49280ada79ed49151c682e8e61e5e446c7af13909553f89b24c2a2622e454573`.

### 20.3 Post-deploy smoke (controller)

| Probe | Result |
|---|---|
| `git status --short --branch` | `## main...origin/main`; local `HEAD` and `origin/main` both `9697d8c0095863e83c895b8de8e1ee7ba296a860` |
| `.190` `docker compose ps` (from `/mnt/raid/docker-compose/3d-portal`) | `api`, `arq-worker`, `redis`, `slicer-worker`, `web`, `worker` — **all `running`** |
| LAN API health `http://192.168.2.190:8090/api/health` | **`{"status":"ok","version":"0.1.0"}`** |
| LAN web `http://192.168.2.190:8090/` | **HTTP 200** |
| Production HTTPS `https://3d.ezop.ddns.net/` | **HTTP 200** |

### 20.4 Why `done`

Every acceptance criterion was verified at source by the CR pass (§17) and independently corroborated by Aider (§18); the full 16-stage gate is green (§19); the change is merged fast-forward, pushed, deployed and smoked green on both the LAN and the production hostname. The two open items are `defer`-class edges of a hook with **no caller until Story 51.2**, already in `deferred-work.md` — they are ledgered, not outstanding work for this story. Nothing in the closeout chain remains owed.

### 20.5 Provenance — stated, not implied

**No human review of any kind.** No Ezop signature, no Ezop review, no Laura review. This closeout rests on: native BMAD `bmad-code-review` **APPROVE** (agent approval only) + independent **Aider** `APPROVE` (`laura-aider-review-diff`, the Laura Agent Rulebook's routine route) + `check-all.sh` **16/16** + the controller's own merge / push / deploy / smoke. **No Codex, no Gemini** at any point in this story.

**What this bookkeeping pass did and did not do.** It edited exactly two tracked files — this artifact and `sprint-status.yaml` — and set `50-1-fe-types-and-hooks: done` plus `epic-50: in-progress`. It ran **no** gate, test, build, script, commit, stage, push, merge, deploy, migration, seed, live-DB or network action, and touched **no** app code. Every figure recorded above is either the controller's reported evidence or a value this pass read directly from the repo (`git rev-parse HEAD` / `git rev-parse origin/main`, both `9697d8c…`) and from the teed deploy log — no number here was invented or inferred.

**`epic-50` flip, with its precedent named.** `epic-50` moves `backlog` → **`in-progress`**. The repo's recorded precedent is to flip the epic when its first story starts real work: `sprint-status.yaml`'s `epic-49` comment states it was *"FLIPPED 2026-07-26 from backlog by native `bmad-dev-story` (DS) … the project's 43.1/47.5 precedent (flip the epic at dev-story)"*. The DS, CR and check-all passes each deliberately left `epic-50` at `backlog` because §9 assigns the flip to the controller — that deferral is now spent: the first E50 story is committed, merged, pushed and live. `in-progress`, not `done`, is the truthful state — `50-2-url-state-category-scope` and `50-3-inline-structured-suggestions` are still `backlog`, and `epic-50-retrospective` remains `optional`.
