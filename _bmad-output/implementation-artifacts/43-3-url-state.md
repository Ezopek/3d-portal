---
baseline_commit: 99e61f8a53e42cfb53863542114ae563382b1735
---

# Story 43.3 — URL state: `tag_match` + `untagged` (+ `tag_ids` normalization), additive (FR25-FILT-1)

- **Epic:** E43 — Frontend data layer (Initiative 25 — Facet Tag Taxonomy + Category Retirement)
- **Status:** `review` — implemented via native `bmad-dev-story` (2026-07-19, branch `feat/E43.3-url-state` from main `99e61f8`, uncommitted for controller). Previously `ready-for-dev` — created via native `bmad-create-story` (Create), then **PASS** under independent native `bmad-create-story:validate` (VS, 2026-07-19), mirroring the 43.1/43.2 additive-E43 flow. VS corrected the `tag_ids` UUID accuracy wording (canonical subset, not exact backend mirror), the TanStack version label (resolved `1.169.2`), and made the normalized-state/serialization/address-bar distinction explicit; no scope/AC change. epic-43 stays `in-progress`; 43.1/43.2 stay `done`.
- **Author:** Claude (BMAD create-story). **Controller:** Laura.
- **Created:** 2026-07-19, phase 4-implementation; preceded-by `bmad-sprint-planning` (done) + 43.2 (done); followed-by `bmad-create-story:validate`.
- **Scope class:** frontend **route search-state schema only** (`apps/web/src/routes/catalog/index.tsx` `validateSearch` + `CatalogSearch`) plus one **new** colocated vitest test. Adds the `tag_match` + `untagged` URL params and hardens `tag_ids` normalization to the shipped 42.1 wire. **No** product consumption wiring (`useModels`/`CatalogList`/`FilterRibbon` UI = E44), **no** category type/hook/field/param change, **no** backend, migration, locale, route-tree regen, visual baseline, package/lock, or codegen change.
- **Sources of truth:**
  - `epics.md` §Initiative 25 E43 / Story 43.3 (`:4266-4268`, additive re-scope) + E44.2/44.3 consumption owners (`:4280-4286`).
  - `architecture.md` Decision AW § API contract (`:3188-3206`) + § Frontend types (`:3208-3211`) + both 2026-07-19 correct-course Updates (`:3230-3247`).
  - SCP `sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md` (APPROVED/APPLIED; §2.1 43.3 row).
  - Shipped 42.1 backend filter contract: `42-1-models-facet-filtering.md` (AC #2–#6, `done`); `apps/api/app/modules/sot/service.py` `list_models` + `TagMatch`; `apps/api/app/modules/sot/router.py` `get_models`.
  - Shipped FE code: `apps/web/src/routes/catalog/index.tsx` (current `CatalogSearch`/`validateSearch`); `apps/web/src/modules/catalog/hooks/useModels.ts` (`ModelsFilters`/`buildParams`); `apps/web/src/modules/catalog/routes/CatalogList.tsx`; `apps/web/src/routes/login.tsx` + `login.test.tsx` (validateSearch-test + `next` precedent); `apps/web/src/App.tsx` (router config).
  - Executable serialization spike (this story, read-only) — see §7.

---

## 1. Story statement

**As** the catalog frontend URL/search-state layer,
**I want** the catalog route to validate and normalize the facet-filter search params `tag_match` (`all`\|`any`, default `all`) and `untagged` (boolean, default `false`) — and to harden the already-present `tag_ids` param to the shipped `list[uuid.UUID]` wire — as durable, shareable, back/forward-safe URL state,
**so that** E44 (`FilterRibbon` AND/OR toggle, `CatalogList` empty-state + untagged surfacing) can *consume* a well-formed, backend-compatible canonical search object without re-deriving parsing/normalization, and a bookmarked or hand-edited catalog URL degrades gracefully instead of white-screening.

**Business value / FR mapping:** FR25-FILT-1 (`GET /models` … `tag_ids` + `tag_match` (`all`\|`any`, default `all`) + `untagged`; **URL state**). This is the **URL/search-state foundation** half of FR25-FILT-1; the *product consumption* half (sending the params to the backend + the AND/OR toggle + empty-result CTA) is E44.2/44.3. E43 is purely **additive** — the live `category_id` param and its plumbing are preserved as a zero-code compatibility bridge until `CatalogList` migrates in 44.3 and the terminal cutover (47.4/47.5) retires category.

---

## 2. Additive scope — the implementable-green target

### 2.0 Critical pre-read — `tag_ids` already exists (this narrows the story)

The catalog route **already declares** `tag_ids?: string[]` and already normalizes it (array-or-single-string coercion), and `useModels`/`CatalogList` already thread it through to a repeated-param API query. Verified:

- `apps/web/src/routes/catalog/index.tsx:31` — `CatalogSearch.tag_ids?: string[]`.
- `apps/web/src/routes/catalog/index.tsx:45-51` — `validateSearch` accepts an array (filters to strings) **or** coerces a single string to `[value]`.
- `apps/web/src/modules/catalog/hooks/useModels.ts:11` (`ModelsFilters.tag_ids?: string[]`) + `:55` (`for (const tid of f.tag_ids) p.append("tag_ids", tid)`).
- `apps/web/src/modules/catalog/routes/CatalogList.tsx:48` — `tag_ids: search.tag_ids` passed to `useModels`.

**Therefore 43.3 is NOT "add `tag_ids`."** It is: **add `tag_match` + `untagged`** to the route schema, and **harden `tag_ids` normalization** to the `list[uuid.UUID]` contract. The already-shipped `tag_ids` consumption (`buildParams` repeated-param emit) is left **exactly** as-is — extending it (and `tag_match`/`untagged` consumption) is E44.

### 2.1 The exact shipped backend 42.1 contract these params must mirror

From `42-1-models-facet-filtering.md` (AC #2–#6, `done`) and `sot/service.py`/`router.py`:

| Wire param | Type (backend) | Default | Backend on invalid | Semantics |
|---|---|---|---|---|
| `tag_ids` | `list[uuid.UUID] \| None` (repeated `Query()`; **each element a UUID**) | `None` (unfiltered) | non-UUID element → **422**; unknown-but-valid UUID → not rejected (all-mode: own singleton bucket → empty; any-mode: silently ignored) | partitioned by `Tag.group_id`; AND-between-groups / OR-within-group |
| `tag_match` | `TagMatch(StrEnum)` = `{all, any}` | `all` | unknown value (e.g. `both`) → **422** | `all` = group-aware AND/OR; `any` = pure OR across all `tag_ids` |
| `untagged` | `bool` | `false` | — | `true` → zero-tag models; combined with `tag_ids` = **union** (D2) |

**Param names, value domains, and defaults are copied verbatim.** 43.3 stores/serializes them as FE URL state; it does **not** re-implement the filter algebra (that lives in the backend and is already shipped + tested in `test_sot_models_list.py`).

### 2.2 CatalogSearch — the additive shape (`apps/web/src/routes/catalog/index.tsx`)

Add two optional fields to the existing interface (keep every current field, incl. `category_id`, unchanged):

```ts
export interface CatalogSearch {
  category_id?: string;          // PRESERVED — do not touch (47.4/47.5-owned removal)
  tag_ids?: string[];            // existing; normalization hardened (§2.3)
  tag_match?: TagMatch;          // NEW — "all" | "any"
  untagged?: boolean;            // NEW — true only (false ≡ absent)
  status?: ModelStatus;
  source?: ModelSource;
  sort?: ModelListSort;
  q?: string;
  page?: number;
}
```

with a local allow-list constant beside the existing `STATUSES`/`SOURCES`/`SORTS`:

```ts
const TAG_MATCHES = ["all", "any"] as const;
type TagMatch = (typeof TAG_MATCHES)[number];
```

`TagMatch` is a local literal union (no new import; mirrors the existing `STATUSES`/`SORTS` in-file pattern). It intentionally lives **only** in the route for now; the `FilterRibbon` AND/OR toggle that mirrors it is E44.2 (no second allow-list is introduced by 43.3 — see the two-parallel-allow-lists note in §9).

### 2.3 Normalization policy (the heart of this story)

FE convention across this repo: **`validateSearch` never throws / never 422s — it silently drops invalid values (omits the key from the returned object)** so a bookmarked/hand-edited URL degrades gracefully. Precedent: `login.tsx:224-230` drops an unsafe `next`; `catalog/index.tsx:52-64` drops invalid `status`/`source`/`sort`. This is a **justified** divergence from the backend's 422-on-invalid (URL resilience is a different concern than API strictness) and is applied uniformly below.

**Canonical-URL default policy: omit defaults.** Matches the shipped `sort`-omit-when-`"recent"` (`CatalogList.tsx:72`) and `page`-omit-when-`1` conventions. A "clean" catalog URL carries none of the three facet params.

| Param | Accept / normalize | Omit (→ default at consumption) |
|---|---|---|
| **`tag_match`** (NEW) | `raw.tag_match` is a string in `TAG_MATCHES` **and** ≠ `"all"` → set (`"any"`) | anything else, incl. `"all"` (its default), unknown (`"both"`), non-string, absent |
| **`untagged`** (NEW) | boolean `true` **or** string `"true"` → `untagged = true` | `false`, `"false"`, `"0"`, `""`, other strings/types, absent (default `false` ≡ absent) |
| **`tag_ids`** (harden) | array (filter to strings) **or** single string → `[value]`; then **trim, drop empties, drop non-UUID entries, dedupe preserving first-seen order** | resulting array empty → omit the key |

**`tag_ids` UUID hardening rationale (canonical-form subset — safe, one-directional).** The backend type is `list[uuid.UUID]`; a non-UUID element yields a **422 the user cannot recover from** in the browser. Dropping non-UUID entries in `validateSearch` (a) narrows the FE param to the **canonical 8-4-4-4-12 subset** of what the wire type accepts, (b) is consistent with the repo's drop-invalid resilience convention, and (c) cannot desynchronise from the backend semantics because unknown-but-well-formed canonical UUIDs are still forwarded (the backend, not the FE, decides they match nothing). Dedupe/order are cosmetic-for-the-URL only (the backend AND/OR is set-based, `in_(bucket_ids)`), so no semantic divergence is introduced.

> **Accuracy note (verified 2026-07-19, VS empirical).** `UUID_RE` is **stricter** than the backend, not an exact mirror: Python/pydantic `uuid.UUID` also accepts hyphenless (`1111…1111`, 32 hex), braced (`{…}`), and `urn:uuid:…` forms — all of which `UUID_RE` rejects (canonical hyphenated form only; case-insensitive). This divergence is **one-directional and safe**: the FE only ever *drops* an exotic-but-valid form, never forwards a malformed one, so it cannot induce a 422 the backend wouldn't. Every real tag id in this system is minted canonical (`Tag.id` → `tag.id` → `FilterRibbon` selection → URL), and a repo sweep (catalog URLs, fixtures, `useModels`/`FilterRibbon` tests, e2e, navigation) found **no** non-canonical `tag_ids` value reaching `validateSearch`, so no current path regresses. Do **not** describe the FE matcher as "matching the backend contract exactly" — it is a deliberately narrower canonical-only subset.

> **Controller decision (tag_ids hardening): INCLUDE.** The shipped array-or-single-string coercion already round-trips, but canonical UUID filtering prevents malformed browser state from provoking a backend 422, while dedupe stabilizes the normalized state. This is deliberately a stricter canonical subset — **not** an exact mirror of every textual form accepted by `uuid.UUID`. RED→GREEN cases are marked `[H]` in §8 for audit traceability.

Reference UUID matcher (case-insensitive, canonical 8-4-4-4-12; version-agnostic to tolerate any UUID the backend mints):

```ts
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
```

### 2.4 Explicit non-goals (scope fences — see §9 for the full list)

- **No product consumption.** 43.3 does **not** add `tag_match`/`untagged` to `ModelsFilters`/`buildParams` (that sends them to `/api/models` — **E44.3**), and does **not** add the AND/OR toggle (**E44.2**) or empty-result/untagged UI (**E44.3**). The two new params are validated + normalized as parked URL state; consumption lands next epic. The already-shipped `tag_ids` consumption is untouched.
- **No `category_id` change.** Preserved byte-for-byte (URL param, `CategoryTreeSidebar`, `expandCategoryIds`, `useModels.category_ids`). Its removal is 44.3 (consumer) → 47.4/47.5 (types/field).
- **No route-tree regen** (§5), **no backend/migration/locale/visual/codegen**.

---

## 3. Acceptance Criteria

1. **`tag_match` URL param added.** `CatalogSearch` gains `tag_match?: "all" | "any"`. `validateSearch` sets it **only** when `raw.tag_match` is the string `"any"` (a valid non-default value); `"all"` (default), any unknown value (`"both"`, `"AND"`, …), non-string, or absent → key omitted. Validated against the `TAG_MATCHES` allow-list via `.includes()` (mirrors `STATUSES`/`SOURCES`/`SORTS`). No 422/throw.
2. **`untagged` URL param added.** `CatalogSearch` gains `untagged?: boolean`. `validateSearch` sets `untagged = true` when `raw.untagged` is boolean `true` or string `"true"`; every other value (`false`, `"false"`, `"0"`, `""`, other) and absence → key omitted (default `false` ≡ absence). No 422/throw.
3. **`tag_ids` normalization hardened `[H]`.** Existing array-or-single-string coercion preserved; additionally each candidate is trimmed, empty strings dropped, non-canonical (per `UUID_RE` — hyphenated 8-4-4-4-12, case-insensitive) dropped, and the result deduped preserving first-seen order; an empty result omits the key. Unknown-but-valid **canonical** UUIDs are **retained** (backend owns match semantics). `UUID_RE` is intentionally a **narrower canonical subset** of pydantic `uuid.UUID` (which also accepts hyphenless/braced/urn forms); the drop is one-directional and safe (see §2.3 accuracy note) — this AC does **not** assert an exact backend mirror.
4. **Defaults omitted from the canonical URL.** `tag_match="all"`, `untagged=false`, and empty `tag_ids` never appear in the **serialization of the normalized search object** (`defaultStringifySearch(validateSearch(raw))`) — matching the shipped `sort`/`page` omit-default convention. No default value is ever written to `history`/`replace` by this story (this story adds no navigation).
   - **Three distinct layers (do not conflate):** (i) `validateSearch` normalizes the router's in-memory **search state** (drops defaults/invalid → `useSearch` never sees them); (ii) `defaultStringifySearch` of that normalized object omits the defaults from the produced query string (the AC assertion, T3); (iii) an **already-loaded browser address bar** is a separate concern — TanStack does **not** auto-rewrite it to strip `?tag_match=all` on direct load *without a navigation/`replace`*, and 43.3 **adds no navigation**, so the visible URL is not rewritten by this story. The AC is satisfied at layers (i)+(ii) — normalized state and its serialization — **not** by any claim that a stale address bar is physically scrubbed.
5. **Canonical browser serialization is TanStack Router default (proven, §7).** With the un-customized `createRouter` (`App.tsx:15`): `tag_ids` → a single URL-encoded JSON array `?tag_ids=%5B%22<uuid>%22%2C%22<uuid>%22%5D`; `tag_match` → `?tag_match=any`; `untagged` → `?untagged=true`. Round-trip (`stringify → parse → validateSearch`) is stable. **This is distinct from the `/api/models` request wire** (repeated `?tag_ids=a&tag_ids=b`, owned by `useModels.buildParams`, unchanged, E44-consumed) — the two serializations must not be conflated.
6. **`category_id` + all unrelated keys preserved.** A direct URL carrying `category_id` (and/or `q`, `status`, `source`, `sort`, `page`) alongside the new params round-trips unchanged; no existing search key is dropped, reordered destructively, or altered. `category_id` semantics (`expandCategoryIds` → `useModels.category_ids`) are untouched.
7. **Auth-redirect `next` preservation intact.** A catalog URL bearing the new params remains a valid, preserved `next` through the login redirect: `_isSafeReturnPath("/catalog?tag_ids=…&tag_match=any&untagged=true")` is `true` and the value survives login (asserted test-only; **no** change to `login.tsx`/`AuthGate.tsx`/`AppShell.tsx`).
8. **New dedicated test, RED→GREEN, real convention.** `apps/web/src/routes/catalog/index.test.ts` (NEW; today there is **no** catalog `validateSearch` test — a gap) imports `Route.options.validateSearch` (precedent: `login.test.tsx:342-344` pulls `LoginRoute.options.validateSearch`) and covers §8's cases, including a `defaultStringifySearch`/`defaultParseSearch` round-trip. RED is meaningful (see §8.1); GREEN after the schema change.
9. **Green gates, no unrelated change.** `npm run typecheck` (`tsc -b`), `npm run lint` (`eslint --max-warnings=0` + stylelint), `npm run test` (vitest `run`) all pass. **No** `test:visual` run (no UI). **No** `routeTree.gen.ts` regen (§5). Backend/migration/locale/`api-types.ts`/`useModels.ts`/`CatalogList.tsx` untouched. `git diff --check` clean.

---

## 4. Tasks / Subtasks

- [x] **T1 — RED first (TDD).** (AC #8) Author `apps/web/src/routes/catalog/index.test.ts` (vitest; jsdom; `globals: false` → `import { describe, it, expect } from "vitest"`). Import `{ Route }` from `./index` and exercise `Route.options.validateSearch`. Write all §8 cases before touching production. Capture RED under `npm run typecheck` (type-level: `CatalogSearch["tag_match"]`/`["untagged"]` unresolved → TS error) **and** `npm run test` (behavioral: new-param cases fail because `validateSearch` drops them). Evidence → `.hermes/run-logs/e43.3-red.log`. **DONE:** typecheck RED = 2× TS2339 (`tag_match`@32, `untagged`@52), no spurious errors; vitest RED = 8 failed | 11 passed (19).
- [x] **T2 — GREEN schema (additive).** (AC #1–#4) In `apps/web/src/routes/catalog/index.tsx`:
  - [x] Add `TAG_MATCHES` const + `TagMatch` type + `UUID_RE` beside the existing `STATUSES`/`SOURCES`/`SORTS`.
  - [x] Extend `CatalogSearch` with `tag_match?: TagMatch` and `untagged?: boolean` (keep `category_id` + all fields).
  - [x] Extend `validateSearch`: `tag_match` allow-list + omit-`"all"`; `untagged` truthy coercion (`true`/`"true"` only); `tag_ids` hardening `[H]` (trim, drop empty, drop non-UUID, dedupe first-seen). Leave the `category_id`/`status`/`source`/`sort`/`q`/`page` branches byte-for-byte.
- [x] **T3 — Serialization + coexistence proof.** (AC #5, #6) In the test, use `defaultStringifySearch`/`defaultParseSearch` from `@tanstack/react-router` for the round-trip; assert the exact URL substrings (`tag_ids=%5B…%5D`, `tag_match=any`, `untagged=true`) and a full coexistence object incl. `category_id`. **DONE:** round-trip green on resolved `1.169.2`; coexistence uses a valid `status: "printed"` (the §8 illustration's `"published"` is not in `STATUSES`).
- [x] **T4 — `next` preservation guard (test-only).** (AC #7) Assert `_isSafeReturnPath` (or the login route `validateSearch`, per `login.test.tsx:340-380`) accepts a catalog URL carrying the new params. **No** production login change. If `_isSafeReturnPath` is not exported, assert via `LoginRoute.options.validateSearch({ next })` returning the value (same access pattern as `login.test.tsx`). **DONE:** `_isSafeReturnPath` confirmed not exported → used `LoginRoute.options.validateSearch({ next })`; login prod untouched.
- [x] **T5 — Green gates.** (AC #9) `npm run typecheck`, `npm run lint`, `npm run test` (focused then full) all PASS. Confirm `routeTree.gen.ts` unchanged (`git diff --quiet apps/web/src/routeTree.gen.ts`), no `api-types.ts`/`useModels.ts`/`CatalogList.tsx`/backend diff, `git diff --check` clean. Optional sanity: `npm run build`. **DONE:** typecheck/lint PASS; focused 19/19; full 681/681 (662 baseline + 19); build ✓; `routeTree.gen.ts` byte-unchanged; all fenced files unchanged; `git diff --check` clean; no `vitest*.d.ts` byproduct.

---

## 5. routeTree.gen.ts — do NOT regenerate (route_tree_regen = NO)

**Proven from the actual generated file, not assumed.** `apps/web/src/routeTree.gen.ts` is emitted by the `TanStackRouterVite` plugin (`vite.config.ts`, `routesDirectory: "src/routes"`) during `vite`/`vite build`; there is **no** standalone `tsr generate` / `generate:routes` npm script. Its content encodes **only** route id/path/hierarchy/imports — `grep -nE "Search|validateSearch|parseSearch"` over it returns **zero** matches. The catalog block (`routeTree.gen.ts:417-422`) is:

```ts
'/catalog/': {
  id: '/catalog/'
  path: '/catalog'
  fullPath: '/catalog/'
  preLoaderRoute: typeof CatalogIndexRouteImport
  parentRoute: typeof rootRouteImport
}
```

It re-exports `typeof CatalogIndexRouteImport` **by reference**, so any change to `CatalogSearch`/`validateSearch` flows through the import with **zero** delta to the generated file. Adding search params to an **existing** route does **not** trigger regeneration; regen is required only when route **files/paths** are added/removed/renamed (memory `reference_web_routetree_regen`, applied identically in `35-4`/`35-5` artifacts — "regen NOT needed; no new route files"). **Task T5 asserts `routeTree.gen.ts` is byte-unchanged.**

---

## 6. Dev Notes

### 6.1 Files to touch (and the ones to NOT touch)

**Touch (2 files):**
- `apps/web/src/routes/catalog/index.tsx` — `CatalogSearch` +2 fields; `validateSearch` extension; `TAG_MATCHES`/`TagMatch`/`UUID_RE` consts.
- `apps/web/src/routes/catalog/index.test.ts` — **NEW** RED-first test.

**Do NOT touch (explicit):** `apps/web/src/modules/catalog/hooks/useModels.ts` (`buildParams`/`ModelsFilters` — E44.3 consumption), `apps/web/src/modules/catalog/routes/CatalogList.tsx` (E44.3), `apps/web/src/modules/catalog/components/FilterRibbon.tsx` (AND/OR toggle = E44.2), `apps/web/src/lib/api-types.ts` (43.1-owned; category symbols 47.4/47.5), `apps/web/src/routes/login.tsx` / `shell/AuthGate.tsx` / `shell/AppShell.tsx` (only *read* in a test), `apps/web/src/routeTree.gen.ts`, `apps/web/src/App.tsx` (router config), any backend / migration / locale / visual baseline / `package.json` / lockfile.

### 6.2 Current `validateSearch` (the exact code being extended — read before editing)

`apps/web/src/routes/catalog/index.tsx:39-71` (verbatim). Note lines 45-51 already handle `tag_ids` as array-or-single-string, and 41-43 already handle `category_id`:

```ts
if (typeof raw.category_id === "string" && raw.category_id.length > 0) {
  out.category_id = raw.category_id;          // PRESERVE — do not change
}
if (Array.isArray(raw.tag_ids)) {
  const arr = raw.tag_ids.filter((x): x is string => typeof x === "string");
  if (arr.length > 0) out.tag_ids = arr;      // harden here (§2.3 [H])
} else if (typeof raw.tag_ids === "string" && raw.tag_ids.length > 0) {
  out.tag_ids = [raw.tag_ids];                // harden here (§2.3 [H])
}
// status / source / sort validated via .includes(); q string; page number|string→floor
```

The two new branches (`tag_match`, `untagged`) slot in alongside these; the `tag_ids` branch gains the trim/UUID/dedupe pass. The enum-drop precedent for `tag_match` is the existing `status`/`source`/`sort` `.includes()` blocks (`:52-64`).

### 6.3 Why "parked" URL state is coherent, not half-done

43.3 lands the *foundation*: the catalog URL can now **hold** a normalized `tag_match`/`untagged` (and a wire-exact `tag_ids`). E44.2 reads `tag_match` to render the AND/OR toggle; E44.3 reads `untagged` (+ `tag_match`) into `buildParams` → `/api/models` and renders the empty-result CTA. Splitting foundation (43.3) from consumption (E44) is the same shape as 43.1 (types) → 43.2 (hooks) → E44 (UI). The backend already accepts all three params (42.1 `done`), so nothing is stranded server-side.

### 6.4 Terminology guard (carry from 42.1)

`untagged` (a **model** with zero `model_tag` rows) ≠ a **groupless tag** (a real `Tag` with `group_id IS NULL`, selected via its id in `tag_ids`). The FE URL layer never needs to distinguish them — `untagged` is a boolean, `tag_ids` carries real tag UUIDs — but name test cases accordingly to avoid the conflation 42.1 called out.

### 6.5 Known, out-of-scope transition state (do not "fix")

Backend 42.1 removed `category_ids` from `GET /api/models`; `useModels.buildParams` still emits `?category_ids=` (from the FE `category_id`), which FastAPI now **silently ignores** (42.1 AC #1 / transition note). This means category filtering is already a server-side no-op — **expected** under E42-before-E43/E44 sequencing. 43.3 must **not** touch `category_id` or `buildParams` to "repair" this; the category param + UI are the zero-code bridge retired by 44.3 → 47.4/47.5.

### 6.6 Type/test config facts (carry from 43.1)

`tsconfig.json`: `strict` on, `include: ["src","tests"]` (test files typechecked → tsc is the type-level RED gate), `noUncheckedIndexedAccess` on (unaffected here — known-literal-key access), `exactOptionalPropertyTypes` **not** set (so `untagged?: boolean` = `boolean | undefined`, `tag_match?: TagMatch` = `TagMatch | undefined` — assertions hold). Vitest `^2.1.6`, jsdom, `globals: false`, `setupFiles: ["./vitest.setup.ts"]`.

---

## 7. Serialization spike (executed, read-only — proves AC #5)

The browser-URL wire format was **not** pinned by any existing test (the Explore map flagged it as inferred). Proven here against the app's **actually-installed** `@tanstack/react-router` (declared range `^1.84.0` in `package.json`; **resolved on disk = `1.169.2`** — re-verified by VS, serialization identical across the range) via a throwaway script (run inside `apps/web`, deleted immediately; `git status` clean after — no repo mutation):

```
IN    {"tag_ids":["1111…-1111-4111-8111-…","2222…-2222-4222-8222-…"]}
URL   ?tag_ids=%5B%2211111111-1111-4111-8111-111111111111%22%2C%2222222222-…%22%5D
PARSE {"tag_ids":[…same…]}                                                RT-OK true
IN    {"tag_match":"any"}   URL ?tag_match=any     PARSE {"tag_match":"any"}    RT-OK true
IN    {"tag_match":"all"}   URL ?tag_match=all     PARSE {"tag_match":"all"}    RT-OK true
IN    {"untagged":true}     URL ?untagged=true     PARSE {"untagged":true}      RT-OK true
IN    {"untagged":false}    URL ?untagged=false    PARSE {"untagged":false}     RT-OK true
IN    {category_id, tag_ids:[uuid], tag_match:"any", untagged:true, q, status, sort, page}
URL   ?category_id=cat-abc&tag_ids=%5B%22…%22%5D&tag_match=any&untagged=true&q=vase&status=published&sort=name_asc&page=2
PARSE {…identical…}                                                       RT-OK true
```

**Conclusions:** (a) arrays → URL-encoded JSON array (`defaultStringifySearch` = `stringifySearchWith(JSON.stringify)`), **not** repeated params, **not** CSV; (b) `tag_match` → bare string; (c) `untagged` → JSON boolean; (d) all round-trip stable and coexist with `category_id` + unrelated keys. Because the router is un-customized (`App.tsx:15` — no `parseSearch`/`stringifySearch`), this is the definitive canonical format. The story's round-trip test reproduces this spike as a committed assertion (T3).

---

## 8. Test plan — `apps/web/src/routes/catalog/index.test.ts` (NEW)

Access pattern (proven precedent — `login.test.tsx:342-344`):

```ts
import { describe, it, expect } from "vitest";
import { defaultStringifySearch, defaultParseSearch } from "@tanstack/react-router";
import { Route } from "./index";
const v = Route.options.validateSearch; // (raw: Record<string, unknown>) => CatalogSearch
```

### 8.1 RED gates (must be meaningful)

- **Type-level (`npm run typecheck`, `tsc -b`):** any case asserting `v({...}).tag_match` / `.untagged` against the `CatalogSearch` type fails to compile until the interface gains the fields (TS2339/property-missing) — mirrors 43.1's `tsc`-is-RED strategy.
- **Behavioral (`npm run test`, vitest `run`):** before T2, `v({ tag_match: "any" })` and `v({ untagged: "true" })` return `{}` (current `validateSearch` ignores unknown keys), so the "parses new param" assertions FAIL. This is the runtime RED (unlike 43.1's type-only test, this one has real behavioral RED because `validateSearch` is runtime logic).

### 8.2 GREEN cases

**`tag_match`:**
- `v({ tag_match: "any" })` → `{ tag_match: "any" }`.
- `v({ tag_match: "all" })` → `{}` (default omitted).
- `v({ tag_match: "both" })` / `v({ tag_match: "AND" })` / `v({ tag_match: 5 })` → `{}` (invalid dropped).
- absent → `{}`.

**`untagged`:**
- `v({ untagged: true })` → `{ untagged: true }`; `v({ untagged: "true" })` → `{ untagged: true }`.
- `v({ untagged: false })` / `"false"` / `"0"` / `""` / `1` → `{}` (default/invalid omitted).

**`tag_ids` `[H]` (excise with the hardening if vetoed, §2.3):**
- `v({ tag_ids: [UUID_A, UUID_B] })` → both preserved, order kept.
- `v({ tag_ids: UUID_A })` (single string) → `{ tag_ids: [UUID_A] }` (existing coercion).
- `v({ tag_ids: [UUID_A, UUID_A, UUID_B] })` → `[UUID_A, UUID_B]` (deduped, first-seen order).
- `v({ tag_ids: [UUID_A, "not-a-uuid", "", UUID_B] })` → `[UUID_A, UUID_B]` (non-UUID + empty dropped).
- `v({ tag_ids: ["not-a-uuid"] })` → `{}` (empties out → omitted).
- `v({ tag_ids: [UNKNOWN_BUT_VALID_UUID] })` → retained (backend owns match semantics).

**Round-trip / serialization (AC #5, reproduces §7):**
- For `s = { tag_ids: [UUID_A, UUID_B], tag_match: "any", untagged: true }`: `v(defaultParseSearch(defaultStringifySearch(s)))` deep-equals `s`; and `defaultStringifySearch(s)` contains `tag_ids=%5B` (JSON array), `tag_match=any`, `untagged=true`.
- `tag_match: "all"` and `untagged: false` and `tag_ids: []` do **not** appear in `defaultStringifySearch` of a normalized object (canonical omit-default).

**Coexistence with `category_id` + unrelated keys (AC #6):**
- `v({ category_id: "cat-1", tag_ids: [UUID_A], tag_match: "any", untagged: true, q: "vase", status: "published", source: "printables", sort: "name_asc", page: 2 })` → every key preserved with `category_id` unchanged.
- `v({ category_id: "cat-1" })` → `{ category_id: "cat-1" }` (category-only URL still valid).

**`next` preservation (AC #7, test-only):**
- `_isSafeReturnPath("/catalog?tag_ids=%5B%22" + UUID_A + "%22%5D&tag_match=any&untagged=true")` → `true` (or, if not exported, `LoginRoute.options.validateSearch({ next })` returns that `next`). Imports from `@/routes/login` — **no** login production edit.

### 8.3 Runner / gates

Vitest (`npm run test`) — focused (`npx vitest run src/routes/catalog/index.test.ts`) then full. `npm run typecheck` + `npm run lint`. No `test:visual`. Determinism: pure-function assertions, no DB/network.

---

## 9. Scope fences & gate ownership

**In scope (43.3):** `tag_match` + `untagged` route search-schema fields; `tag_ids` normalization hardening; the new `validateSearch` test. Two files (§6.1).

**Out of scope — with owner:**

| Deferred item | Owner |
|---|---|
| Send `tag_match`/`untagged` to `/api/models` (`buildParams`/`ModelsFilters`) | **E44.3** (`CatalogList` states) |
| AND/OR (`tag_match`) toggle UI | **E44.2** (`FilterRibbon`) |
| Empty-result CTA ("Switch to OR / Clear") + untagged surfacing UI | **E44.3** |
| Drop `category_id` param + `useCategoriesTree`/`CategoryTreeSidebar` wiring | **E44.3** (consumer) → **47.4** (types/hook) |
| Remove `CategorySummary`/`ModelSummary.category_id`/`ModelDetail.category` | **47.5** (atomic ORM+DTO+`0019`) |
| Backend filter algebra, migration, locale, visual baselines, `api-types.ts`, `useModels.ts`, codegen, `routeTree.gen.ts` | not this story (respective owners / already shipped in 42.1) |

**Full gate ownership (this story's dev must clear all):** `npm run typecheck` (`tsc -b`) · `npm run lint` (`eslint --max-warnings=0` + stylelint) · `npm run test` (vitest `run`) · `git diff --check` clean · `routeTree.gen.ts` byte-unchanged · no diff outside the 2 in-scope files. **No** `test:visual`, **no** backend suite, **no** Alembic, **no** destructive-go. **No commit/push/deploy/branch by the spec author** — controller Laura owns the branch + review→done path (as in 43.1/43.2).

**Notes for the dev:**
- Two parallel enum allow-lists exist in the codebase (`STATUSES`/`SOURCES`/`SORTS` in `routes/catalog/index.tsx` vs `STATUS_VALUES`/`SOURCE_VALUES`/`SORT_VALUES` in `FilterRibbon.tsx`). 43.3 adds `TAG_MATCHES` **only** to the route (no UI). The mirrored `FilterRibbon` toggle allow-list is E44.2 — do **not** pre-create it here.
- `validateSearch` must stay a pure, total function (never throw) — TanStack calls it on every navigation + on direct URL load; a throw white-screens the catalog.

---

## 10. References

- [Source: `_bmad-output/planning-artifacts/epics.md:4266-4268`] — Story 43.3 additive sketch: "add URL state for `tag_ids`/`tag_match`/`untagged`; **Preserve the `category_id` URL param** until `CatalogList` migrates in 44.3".
- [Source: `_bmad-output/planning-artifacts/epics.md:4280-4286`] — E44.2 `FilterRibbon` (AND/OR toggle) + E44.3 `CatalogList` (wire `tag_ids`/`tag_match`/`untagged`, empty-state) = consumption owners.
- [Source: `_bmad-output/planning-artifacts/epics.md:4169`] — FR25-FILT-1 trace (E42+E43 / 42.1+43.3): `tag_ids` + `tag_match` (default `all`) + `untagged`; URL state.
- [Source: `_bmad-output/planning-artifacts/architecture.md:3193`] — Decision AW `GET /api/models`: drop `category_ids`; add `tag_ids: list[str]`, `tag_match: "all"|"any"` (default `"all"`), `untagged: bool`.
- [Source: `_bmad-output/planning-artifacts/architecture.md:3241-3247`] — 2026-07-19 correct-course Update: E43 additive; FE category removals relocated (47.4 tree types+hook / 47.5 model DTO+field); E43 removes none.
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-19-e43-fe-data-additive-correction.md` §2.1] — 43.3 row: additive `tag_ids`/`tag_match`/`untagged`; keep `category_id` until 44.3.
- [Source: `_bmad-output/implementation-artifacts/42-1-models-facet-filtering.md` AC #2–#6] — shipped backend contract: `tag_ids: list[uuid.UUID]`, `tag_match` StrEnum `{all,any}` default `all` (422 on unknown), `untagged: bool` default `false`; unknown-UUID + union semantics.
- [Source: `apps/web/src/routes/catalog/index.tsx:29-71`] — current `CatalogSearch` + `validateSearch` (existing `category_id` + `tag_ids` handling; enum-drop precedent).
- [Source: `apps/web/src/modules/catalog/hooks/useModels.ts:8-63`] — `ModelsFilters` + `buildParams` (repeated-param API wire; **E44-owned**, untouched).
- [Source: `apps/web/src/routes/login.tsx:222-231` + `login.test.tsx:340-380`] — `validateSearch`-as-testable-option precedent + `_isSafeReturnPath` open-redirect suite (RU-1 accepts `/catalog?…`).
- [Source: `apps/web/src/App.tsx:15`] — `createRouter({ routeTree, scrollRestoration: true })`, no custom search (de)serializer → TanStack defaults (§7).
- [Source: `apps/web/src/routeTree.gen.ts:417-422` + header `:1-9`] — generated file encodes path/hierarchy only; no search schema → no regen on schema edit (§5).
- [Source: memory `reference_web_routetree_regen`, applied in `35-4-admin-policy-management.md` + `35-5-estimate-ui-source-labels.md`] — routeTree regen needed only for new/renamed route **files**, not search-schema edits.
- [Source: `43-1-api-types.md` §T4/§tsconfig + `43-2-hooks.md`] — FE gate/test conventions (`tsc -b` RED, vitest, `--max-warnings=0`; `done` predecessors).

---

## 11. File List (to be filled by dev-story)

**Modified:**
- `apps/web/src/routes/catalog/index.tsx` — `CatalogSearch` +`tag_match`/`untagged`; `validateSearch` extension; `TAG_MATCHES`/`TagMatch`/`UUID_RE` consts.

**New:**
- `apps/web/src/routes/catalog/index.test.ts` — RED-first `validateSearch` + serialization/coexistence/next test.

---

## 12. Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context) — native `bmad-dev-story`. Controller: Laura.

### Debug Log References

- RED: `.hermes/run-logs/e43.3-red.log` (typecheck 2× TS2339 + focused vitest 8 failed | 11 passed).
- GREEN: `.hermes/run-logs/e43.3-green.log` (focused 19/19, typecheck, lint, full 681/681, build, scope assertions).
- Progress: `.hermes/run-logs/e43.3-dev-progress.md`.

### Completion Notes List

- **Scope:** exactly the 2 in-scope files touched — `apps/web/src/routes/catalog/index.tsx` (schema) + new `apps/web/src/routes/catalog/index.test.ts` (RED-first). No product wiring; `useModels`/`CatalogList`/`FilterRibbon`/`api-types.ts`/`login.tsx`/`App.tsx`/`routeTree.gen.ts` all byte-unchanged.
- **Implementation:** added `TAG_MATCHES`/`TagMatch`/`UUID_RE` beside `STATUSES`/`SOURCES`/`SORTS`; `CatalogSearch` gains `tag_match?: TagMatch` + `untagged?: boolean`. `validateSearch`: `tag_match` set only for allow-listed non-default `"any"` (`.includes()` + `!== "all"`, mirroring the status/source/sort enum blocks); `untagged = true` only for boolean `true` / string `"true"`; `tag_ids` hardened to unified pass — array-or-single-string → trim → drop empty → drop non-canonical (`UUID_RE`) → dedupe first-seen (`Set`) → omit when empty. `category_id`/`status`/`source`/`sort`/`q`/`page` branches left byte-for-byte.
- **Controller decision applied:** `tag_ids` canonical-UUID hardening INCLUDED (`[H]`). `UUID_RE` is a deliberately narrower canonical-only subset of pydantic `uuid.UUID` (one-directional, safe — documented inline).
- **Serialization:** proven against resolved `@tanstack/react-router` 1.169.2 — `tag_ids` → URL-encoded JSON array (`%5B…`), `tag_match=any` bare, `untagged=true` boolean; `stringify→parse→validateSearch` round-trip stable; defaults omitted from the serialized normalized object (AC #4 layers i+ii; no address-bar rewrite — this story adds no navigation).
- **Test-typing note:** `Route.options.validateSearch` is a TanStack `Constrain<…>` validator union (not directly callable), so the test unwraps it with the established repo cast (login.test.tsx:341) to `(raw: Record<string, unknown>) => CatalogSearch`. The cast preserves the return type, so the type-level RED for the new fields was genuine (not masked). No `any`, no result-masking casts. `_isSafeReturnPath` confirmed not exported → `next` guard via `LoginRoute.options.validateSearch`.
- **Spec-illustration correction:** §8's coexistence example used `status: "published"`, which is not a member of the actual `STATUSES` allow-list — the test uses `status: "printed"` (a real member) so the coexistence round-trip holds. No AC change.
- **Gates:** typecheck ✓, lint ✓ (`--max-warnings=0`), focused 19/19, full 681/681 (662 baseline + 19, zero regressions), build ✓, `git diff --check` clean. No `test:visual`, no backend/migration/locale/codegen. No `vitest*.d.ts` byproduct created.
- **Controller reviews/gates:** native BMAD adversarial review **APPROVE** (`0 critical`, `0 important`, `1 minor` safe cosmetic case-variant dedupe); Aider **APPROVE** with no missing tests. Controller rerun typecheck + focused **19/19** + lint PASS; explicit fenced-file and existing-branch byte-equality guards PASS. Full `infra/scripts/check-all.sh` **16/16 green**, including web Vitest **681 passed** and visual **464 passed / 24 skipped**.

### Change Log

| Date | Note |
|---|---|
| 2026-07-19 | Story created via native `bmad-create-story` (Create). Additive `tag_match` + `untagged` URL params + `tag_ids` wire-hardening; `category_id` preserved; serialization proven via read-only spike (§7); route-tree regen = NO (§5). Status → `ready-for-validation` (independent VS to follow). No prod/test code edited by author; no destructive-go. |
| 2026-07-19 | Native `bmad-dev-story` implementation (Claude; Laura controller). Branch `feat/E43.3-url-state` from main `99e61f8` (frontmatter `baseline_commit` aligned to the controller-designated `99e61f8` so the review diff isolates implementation only). RED-first: new `apps/web/src/routes/catalog/index.test.ts` → typecheck 2× TS2339 + vitest 8 failed \| 11 passed. GREEN: `apps/web/src/routes/catalog/index.tsx` gains `tag_match`/`untagged` + `tag_ids` canonical-UUID hardening `[H]`; `category_id` and all unrelated branches byte-identical. Gates: typecheck/lint/focused 19-19/full 681-681/build all PASS; `routeTree.gen.ts` + all fenced files byte-unchanged; `git diff --check` clean; no `vitest*.d.ts` byproduct. Status → `review`. Branch left uncommitted for controller (no commit/push/merge/deploy by author). |
| 2026-07-19 | Independent native `bmad-create-story:validate` (VS) → **PASS**. Empirical checks: (1) `tag_ids` confirmed already declared + consumed (`useModels.buildParams:49-51` → repeated `?tag_ids=`; `CatalogList.tsx:49`) — story correctly narrows to "add `tag_match`/`untagged` + harden `tag_ids`", no false no-consumption claim, runtime wire untouched. (2) UUID: `UUID_RE` is a **canonical subset**, stricter than pydantic `uuid.UUID` (hyphenless/braced/urn accepted by backend, rejected by FE) — verified via `python3 uuid.UUID` + regex; "exact backend match" wording corrected; drop is one-directional/safe; repo sweep found no non-canonical `tag_ids` reaching `validateSearch` (real ids minted canonical) → hardening kept, no regression. (3) Serialization re-proven on **resolved `1.169.2`** (not just declared `^1.84.0`): `tag_ids`→JSON-array `%5B…`, `tag_match=any` bare, `untagged=true` boolean, round-trip stable, `defaultStringifySearch({tag_match:"all"})`→`?tag_match=all` (⇒ omit-default must occur in `validateSearch`, as specified). (4) Normalized-state vs serialization vs address-bar-rewrite distinction made explicit in AC #4 (no over-claim of physical URL scrub without navigation). (5) `defaultParseSearch("untagged=true")`→boolean `true`, `tag_match=any`→string — both coercion forms handled, no throw. (6) `category_id` + `q/status/source/sort/page` preserved byte-for-byte (backend `tag_ids: Annotated[list[uuid.UUID]|None, Query()]` confirmed). (7) Co-located `.test` under `src/routes` proven route-tree-inert (4 existing `*.test.tsx`, `routeTree.gen.ts` has 0 `test` refs); `.test.ts` naming safe. (8) `_isSafeReturnPath` confirmed **not exported** — T4 fallback to `LoginRoute.options.validateSearch` is the correct access path. Findings: 0 critical, 1 important (fixed: UUID accuracy wording), 2 minor (fixed: version label + rewrite distinction). Status → `ready-for-dev`. Log: `.hermes/run-logs/e43.3-validation.md`. No prod/test code touched by VS; no destructive-go. |
| 2026-07-19 | Controller pre-integration gates: native BMAD APPROVE (0 critical / 0 important / 1 non-blocking cosmetic minor), Aider APPROVE, focused 19/19 + typecheck/lint + fenced-file guards PASS, full `check-all` 16/16 (web 681, visual 464/24). |
