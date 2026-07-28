---
baseline_commit: c436f619d26ed9f1262c2566af797afeee002ba5
---

# Story 50.2 — URL state: `category` as an independent layer (FR26-BROWSE-2, FR26-BROWSE-3)

- **Epic:** E50 — Frontend data layer, URL state, and search suggestions (Initiative 26 — Catalog Discovery)
- **Status:** `done` — CLOSED 2026-07-28 by Laura/controller after native `bmad-dev-story`, native `bmad-code-review` APPROVE, independent Aider APPROVE, full `infra/scripts/check-all.sh` 16/16 all-green, fast-forward merge to `main`, push, deploy and post-deploy smoke (§19). Implemented 2026-07-28 by native `bmad-dev-story` (DS) under Laura/controller **G26-DEVGO** (see §16). Previously: created **and** validated 2026-07-28 by native `bmad-create-story` (Create + Validate), validation verdict **PASS** (§12); that create/validate run recorded **no** G26-DEVGO, which the controller granted separately for this DS run.
- **Author:** Claude (native `bmad-create-story`, Create + Validate). **Controller:** Laura.
- **Authorization posture, stated plainly:** Laura/controller granted this create + validate pass under the standing Initiative 26 authorization. **This is NOT Ezop human review and NOT an Ezop signature.** No human of any kind reviewed this artifact. No Codex, no Gemini, no Aider in this pass. No code was written, no gate was run, no commit / stage / push / merge / deploy / migration / seed / live-DB / network action was taken.
- **Created:** 2026-07-28 via native `bmad-create-story` after a mandatory `bmad-help` run. Canonical route from `_bmad/_config/bmad-help.csv:26-28`: `bmad-create-story:create` (CS, phase `4-implementation`, preceded-by `bmad-sprint-planning` — done) → `bmad-create-story:validate` (VS) → `bmad-dev-story` (DS) → `bmad-code-review` (CR). Canonical skill ID/path confirmed at `_bmad/_config/skill-manifest.csv:40` (`_bmad/bmm/4-implementation/bmad-create-story/SKILL.md`).
- **Provenance note — the first create attempt was blocked by a tool permission, not by BMAD.** An earlier `bmad-create-story` pass completed its analysis and was then denied `Write` to this path by the agent harness's default permission layer. That was a **tool-permission failure, not a BMAD protest**: no skill rejected the state, no checklist failed, and no route-around was attempted. The controller relaunched this run with the permission granted. Every code fact below was **re-traced at source in this run** rather than carried over from that aborted pass — three of its recorded observations are re-verified in §2 and one of its path claims is corrected in §2.1.
- **Scope class:** frontend **URL state only** — one search-param layer on the already-shipped `/catalog/` route plus the minimal wiring that makes it reach the already-shipped query hook. **No** new route file, **no** new component, **no** new i18n key, **no** new a11y surface, **no** visual baseline, **no** backend, **no** dependency, **no** codegen, **no** route-tree regeneration.
- **Sources of truth:** `epics.md` § Initiative 26 → E50 → Story 50.2 (`:4507-4509`); `prd.md` FR26-BROWSE-2 (`:2251`), FR26-BROWSE-3 (`:2252`); NFR ownership matrix (`epics.md:4413-4423`); the **shipped** E49 wire and the **shipped** 50.1 data layer at `main` @ `c436f61`; in-repo precedent `43-3-url-state.md` (`done`, the validator this story extends) and `50-1-fe-types-and-hooks.md` (`done`, the hook this story feeds).

---

## 1. Story statement

**As** a catalog user (and as every downstream Initiative 26 surface),
**I want** the active browse-category scope to live in the catalog URL as its own visible, shareable, back-button-addressable layer — independent of the tag facets, the tag match mode, and the `Filters (n)` count —
**so that** a category-scoped catalog view is a real, linkable application state that the shipped `useModels({ category })` filter actually reaches, and so Story 51.2 can mount the `/categories/$slug` route and the scope chip on top of a settled state contract instead of inventing one.

**FR mapping.**
**FR26-BROWSE-2** — *category is a browse **scope**, not another filter*: exactly **one** active category at a time, addressed by **slug**; `q`/`tag_ids`/`tag_match`/`sort` remain independent visible URL layers; the `Filters (n)` badge **does not change** when a category is active. This story delivers the URL-layer half; the chip and the "Search entire catalog" escape are **51.2**.
**FR26-BROWSE-3** — *facet semantics unchanged*: OR-within-group / AND-between-groups with `tag_match` as the user override; **category scope is never mixed into `tag_match`**. This story's fences are what make that mechanically checkable on the frontend.

**This story renders no new element and adds no user-visible string.** Per the NFR ownership matrix (`epics.md:4417-4420`), which names **50.3, 51.1–51.4, 52.1–52.3, 53.2** — and not 50.2 — as the i18n/a11y owners, this story owns **no new i18n key and no new a11y assertion**. Its own gate is the **validator unit coverage** the epic sketch assigns it (`epics.md:4509`), plus the integration assertions in §7.2 that keep the FR26-BROWSE-2 verifiables from being vacuous. Existing visual baselines must be green **UNCHANGED** — none may be added, changed or regenerated.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `c436f61`

The standing epic:47 PROCESS action item forbids carrying a sketch's "X already exists / Y is already gone" as settled fact. Every row below was re-read at source **in this run**.

| Claim | Verified at | Result |
|---|---|---|
| The catalog route + validator live at `apps/web/src/routes/catalog/index.tsx` | file read in full, 105 lines | ✅ `CatalogSearch` interface `:36-45`; `createFileRoute("/catalog/")` `:47`; `validateSearch` body `:49-103`. The epic sketch's `routes/catalog/index.tsx:49-103` is **accurate**. |
| `validateSearch` has **no** `category` layer | `grep -n category apps/web/src/routes/catalog/index.tsx` | ✅ zero hits. Correct RED baseline. |
| The 43.3 canonical-UUID hardening is present and is what must stay untouched | `index.tsx:30-34` (`UUID_RE`) + `:52-67` | ✅ trim → `UUID_RE` → dedupe → omit-if-empty, with the comment explaining it only ever DROPS an exotic form. Untouched by this story. |
| The ≥2-tag `tag_match` normalization is present | `index.tsx:68-80` | ✅ `tag_match` survives only when non-`all` **and** `out.tag_ids.length >= 2`. Untouched by this story. |
| Validator unit coverage already exists and is the file to extend | `apps/web/src/routes/catalog/index.test.ts`, 179 lines, 7 `describe` blocks | ✅ Story 43.3 / 44.2 coverage. Uses the `Route.options.validateSearch as (raw) => CatalogSearch` cast (`:15`) and exact-object `toEqual` assertions — so adding a `category` key does **not** break any existing assertion (none of them passes `category`). |
| `useModels` already accepts `category` (shipped by 50.1) and is **unwired** | `modules/catalog/hooks/useModels.ts:15-18, 61` | ✅ `ModelsFilters.category?: string` with the comment *"Unset everywhere until Story 50.2 wires URL state"*; `buildParams` emits `category=<slug>` only when `!== undefined && length > 0`. |
| `CatalogList` does **not** pass `category` to `useModels` | `modules/catalog/routes/CatalogList.tsx:41-50` | ✅ the `useModels({...})` literal lists `tag_ids, tag_match, untagged, status, source, q, sort, page` — no `category`. This is the dead-state gap this story closes (D-5). |
| `Filters (n)` is `activeFilterCount` in `FilterRibbon.tsx` — and it is a **different thing** from `CatalogList.filtersActive` | `FilterRibbon.tsx:52-58` and `:161-165`; `CatalogList.tsx:162-167` | ✅ `activeFilterCount(state)` counts **only** `status`, `source`, and a non-`recent` `sort` (**not even `tag_ids`**), and is rendered as the badge on the mobile Filters trigger. `filtersActive` in `CatalogList` is a separate boolean gating the empty-state **Clear filters** action. **They are not the same predicate** — a dev agent that conflates them will encode the wrong fence. See D-4 / D-6. |
| `FilterRibbonState` carries no category and the ribbon never sees one | `FilterRibbon.tsx:37-44`, `CatalogList.tsx:52-59` | ✅ six keys: `q, tag_ids, tag_match?, status, source, sort`. Adding nothing here **is** the FR26-BROWSE-2 mechanism. |
| Backend `category` is a **bare string** with no format constraint | `sot/router.py:196` (`category: str \| None = None`) | ✅ no `Query(pattern=…)`, no enum, no UUID type. A malformed value can therefore **never** produce a 422. |
| Unknown slug → **200 + empty page + `total: 0`**, never 404 | `sot/service.py:357-375` (IN-subquery on `BrowseCategory.slug == category`) + the endpoint description `router.py:169-176` | ✅ empty subquery → unsatisfiable predicate → empty page. Explicitly *"never a 404"*. |
| The slug match is **exact and case-sensitive**, and structurally **outside** the tag composition | `service.py:357-375` | ✅ `BrowseCategory.slug == category` (no `lower()`, no `LIKE`), inside its own `base.where(...)` block placed after `source` and before `q`, with the in-code comment *"Structurally OUTSIDE the tag/untagged composition above, so `tag_match` never sees it"*. **Do not lowercase on the frontend.** |
| The backend treats `category=""` as a **real** filter, not as absent | `service.py:357` (`if category is not None:`) | ✅ an empty string would produce an unsatisfiable predicate and a silently empty catalog. This is why the validator must **drop** an empty/whitespace-only value (D-1) — the `buildParams` `length > 0` guard is the second fence, not the only one. |
| Admin-created slugs have **no** format validation | `sot/admin_schemas.py:302` (`slug: str = Field(min_length=1)`) and `:327` | ✅ `min_length=1` only — no `pattern`, no regex. A frontend regex would be **stricter than the contract** (D-2). |
| Real seeded slugs are plain kebab-case ASCII | `apps/api/app/core/db/seed.py:282+` (`STARTER_BROWSE_CATEGORIES`) | ✅ e.g. `storage-organization`, `home-decor`. Representative, **not** a constraint — the seed comment states it is *"a plain ordered data structure and NOT a frozen contract"* and admin governance owns renames. |
| `routeTree.gen.ts` does **not** encode `validateSearch` or search types | `grep -c search apps/web/src/routeTree.gen.ts` → **0**; `grep -n catalog` → only route `id`/`path`/import lines | ✅ the generated tree carries route ids, paths and imports only. Regeneration is driven by route **files**, not by a route's search schema (D-7). |
| The route-tree generator is the Vite plugin, not a standalone script | `apps/web/vite.config.ts:7,28` (`TanStackRouterVite({ routesDirectory: "src/routes", … })`); `package.json` has no `routes:generate` script | ✅ regeneration happens inside `npm run dev` / `npm run build`. Recorded so the dev agent can *prove* the no-op rather than assert it (§9). |
| No FE symbol collision for a catalog `category` | `grep -rn category apps/web/src --include=*.ts --include=*.tsx` | ✅ the only production hits outside 50.1's `useModels` are `material_category` / `reason_category` in `modules/admin/ProfileOffers*` — a **different domain** (filament material classes). Do not touch them; do not reuse their patterns. |
| `CatalogList` has a real integration harness this story can extend | `modules/catalog/routes/CatalogList.test.tsx`, 200 lines | ✅ `mountAt(url)` builds a memory router that **reuses the real `CatalogRoute.options.validateSearch`** (`:123-142`), and `installFetch()` returns a `calls` array of every requested URL. The existing test *"sends `untagged=true` to the models query when the URL carries untagged"* (`:192-199`) is the **exact precedent** for §7.2. |

### 2.1 Correction to the aborted pass's carried-over path claim

The task brief that seeded the aborted pass referred to the route module as `apps/web/src/modules/catalog/routes/catalog/index.tsx`. **That path does not exist.** The real split, verified in this run:

- `apps/web/src/routes/catalog/index.tsx` — the TanStack **file route**: `createFileRoute`, `CatalogSearch`, `validateSearch`. **This story edits this file.**
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` — the **component** the route mounts. **This story edits this file too**, for D-5/D-6 only.

Both are in scope; they are two different files with two different jobs. The epic sketch's own citation (`routes/catalog/index.tsx:49-103`) was correct all along.

---

## 3. Additive scope — the implementable-green target

Four production edits across two files. Nothing is removed, renamed, narrowed or weakened.

### 3.1 `routes/catalog/index.tsx` — `CatalogSearch` gains one optional key

```ts
export interface CatalogSearch {
  tag_ids?: string[];
  tag_match?: TagMatch;
  untagged?: boolean;
  status?: ModelStatus;
  source?: ModelSource;
  // Initiative 26 (Story 50.2) — ONE browse-category slug. An INDEPENDENT
  // visible URL layer: never folded into tag_match, never counted in the
  // FilterRibbon's Filters (n) badge. The scope chip and the
  // "Search entire catalog" escape are Story 51.2.
  category?: string;
  sort?: ModelListSort;
  q?: string;
  page?: number;
}
```

Placed after `source` and before `sort`, mirroring the backend parameter order (`sot/router.py:196-208`) and 50.1's `buildParams` placement (`useModels.ts:61`, after `source`, before `q`) as closely as the existing local order allows.

### 3.2 `routes/catalog/index.tsx` — one validator branch

Inserted in `validateSearch` after the `source` branch (`:87-89`) and before the `sort` branch (`:90-92`):

```ts
    // Initiative 26 (Story 50.2). A SINGLE slug — an array (`?category=a&category=b`)
    // is dropped wholesale rather than silently reduced to one element, because
    // FR26-BROWSE-2 allows exactly one active scope and a silent pick would make
    // the URL lie about which one. No format check: the wire type is a bare
    // `str | None` (`sot/router.py:196`) and an unknown slug returns 200 + an
    // empty page (`service.py:357-375`), so there is no 422 to protect against —
    // unlike `tag_ids`, whose wire type IS `uuid.UUID`. Trim + drop-if-empty is
    // required, not cosmetic: the backend treats `category=""` as a real,
    // unsatisfiable filter (`if category is not None`), which would blank the
    // catalog with no visible cause.
    if (typeof raw.category === "string") {
      const trimmed = raw.category.trim();
      if (trimmed.length > 0) out.category = trimmed;
    }
```

### 3.3 `modules/catalog/routes/CatalogList.tsx` — wire the layer to the shipped hook

One line inside the existing `useModels({...})` call (`:41-50`), positioned after `source` and before `q`:

```ts
  const models = useModels({
    tag_ids: search.tag_ids,
    tag_match: search.tag_match,
    untagged: search.untagged,
    status: search.status,
    source: search.source,
    category: search.category,
    q: search.q,
    sort: search.sort,
    page: search.page,
  });
```

### 3.4 `modules/catalog/routes/CatalogList.tsx` — `Clear filters` clears filters, not the scope

Both `clear_filters` handlers currently call `navigate({ search: {}, replace: true })` (`:256-258` inside the `andTooNarrow` branch, `:281-284` inside the plain-empty branch). Both become:

```ts
                  void navigate({
                    // Category is a SCOPE, not a filter (FR26-BROWSE-2), so
                    // "Clear filters" must not silently drop it. Clearing the
                    // scope is Story 51.2's "Search entire catalog" control.
                    search: (prev: CatalogSearch): CatalogSearch => ({ category: prev.category }),
                    replace: true,
                  });
```

**Behaviour is byte-identical for every URL reachable today**: with no `category` present, `{ category: undefined }` normalizes back to `{}` through the same `validateSearch` the router already runs. Nothing else in either handler changes.

---

## 4. Resolved decisions (code-first, each with its cost stated)

**D-1 — `category` is a single trimmed non-empty string; arrays, numbers, booleans, `null` and objects are dropped.** `typeof raw.category === "string"` is the only accepted shape. *Why an array is dropped wholesale rather than reduced to `[0]`*: FR26-BROWSE-2 permits exactly one active scope, and silently picking one element would leave the URL claiming two scopes while the app honours one — the class of lie `validateSearch` exists to prevent. *Why trim*: identifiers are trimmed everywhere else in this validator (`tag_ids`, `index.tsx:61`), and a stray space is a copy-paste artefact, not user intent. *Why drop-if-empty is load-bearing, not cosmetic*: the backend guard is `if category is not None` (`service.py:357`), so `category=""` is a **real** filter producing an unsatisfiable predicate — an empty catalog with no visible cause. 50.1's `buildParams` `length > 0` guard is a second fence; this is the first, and neither is redundant (the validator's output is also what the URL and the query key carry). **Cost:** `?category=%20` normalizes to no scope rather than erroring — consistent with how this validator treats every other malformed input.

**D-2 — NO format/regex validation on `category`. This is the single most likely dev-agent mistake in this story.** A dev agent mirroring the adjacent `tag_ids` hardening would add a slug regex. That would be **wrong**, and the asymmetry is contractual, not stylistic:

| | `tag_ids` | `category` |
|---|---|---|
| Wire type | `list[uuid.UUID]` (`router.py:195`) | `str \| None` (`router.py:196`) |
| Malformed value → | FastAPI **422** | impossible — any string parses |
| Unknown-but-well-formed value → | 200, empty page | 200, empty page (`service.py:357-375`) |
| Authoring constraint | — | admin `slug` is `Field(min_length=1)` with **no** `pattern` (`admin_schemas.py:302`) |

So `UUID_RE` exists to stop a client-induced 422 the wire type would otherwise produce; `category` has no such failure mode. A frontend regex would be **stricter than the contract** and would silently delete a legitimately admin-created slug (the seed's kebab-case shape is *representative*, and the seed file itself says it is *"NOT a frozen contract"*). **Cost, stated:** a nonsense slug reaches the backend and returns an empty page. That is the shipped, deliberate posture, not a gap. **Corollary:** do **not** lowercase either — the match is `BrowseCategory.slug == category`, exact and case-sensitive.

**D-3 — the 43.3 canonical-UUID hardening and the 44.2 `tag_match` normalization are byte-unchanged.** The new branch is inserted between the `source` and `sort` branches and touches neither. Proven by `git diff` (the `tag_ids`/`tag_match` hunks must not appear) **and** by the pre-existing tests in `index.test.ts` staying green **without a single edit**.

**D-4 — `category` never enters `FilterRibbonState` and never enters `activeFilterCount`.** This is how FR26-BROWSE-2's *"the `Filters (n)` badge does not change when a category is active"* is satisfied: **by adding nothing**. `FilterRibbon.tsx` must show a **zero-line diff**. The verifiable is not vacuous because §7.2 asserts badge-text invariance across a with-category / without-category pair through the real component.

**D-5 — `CatalogList` wires `category: search.category` into `useModels`. In scope, deliberately.** Without it the layer is dead state: `?category=home-decor` would validate, survive navigation and sit in the URL while changing nothing — a URL that lies. No other story owns this wiring (51.2 mounts the **new** `/categories/$slug` route; the `/catalog/` surface is nobody else's). The skill's standing rule — *a story must leave the system working end-to-end* — makes the one-line wiring part of the deliverable, not scope creep.
**Cache-key safety, verified rather than assumed:** the query key is `["sot","models", filters]` (`useModels.ts:30`) and TanStack Query's `hashKey` is a key-sorted `JSON.stringify`, which **omits properties whose value is `undefined`**. With no category in the URL, `{ …, category: undefined }` hashes identically to today's object — **no cache-key churn, no refetch, no extra request for any existing user**. `buildParams` already guards `length > 0`, so the emitted URL is byte-identical too. §7.2 case 2 locks this mechanically.

**D-6 — `CatalogList.filtersActive` is NOT extended with `category`, and the resulting edge is disclosed, not hidden.** `filtersActive` (`CatalogList.tsx:162-167`) is a *different predicate* from `Filters (n)` — it gates the empty-state **Clear filters** affordance. Leaving it alone means: **a URL carrying only `?category=<unknown-slug>` and no other filter renders the empty state with no recovery button.** That is a real dead-end edge and it is accepted here for three traced reasons: (a) it is reachable in this story **only by a hand-crafted or deep-linked URL**, because no UI emits `category` until 51.2; (b) the designed affordance for exactly this state is FR26-BROWSE-2's **"Search entire catalog"**, which 51.2 owns — building a stand-in now would have to be removed or reconciled two stories later; (c) adding `category` to `filtersActive` would make **Clear filters** wipe the scope, which §3.4 exists to prevent. *Rejected alternative:* extend `filtersActive`. *Named handoff:* **Story 51.2** must supply the escape control for the category-only empty state. §7.2 case 6 pins the current behaviour as **intentional** so a later reader cannot mistake it for an oversight.

**D-7 — no `routeTree` regeneration; recorded as a proof obligation, not an assertion.** `[[reference_web_routetree_regen]]` applies to stories that add or rename **route files**. This story adds none: `apps/web/src/routes/` is untouched except for the existing `catalog/index.tsx`, and the generated tree encodes route ids/paths/imports only — `grep -c search src/routeTree.gen.ts` returns **0**, so no `validateSearch` shape reaches it. The generator is the `TanStackRouterVite` Vite plugin (`vite.config.ts:28`), which runs inside `npm run build`; the dev agent therefore gets the proof for free and **must record it** (§9): after `npm run build`, `git status --porcelain src/routeTree.gen.ts` is empty. If it is *not* empty, **stop and report** — the premise was wrong and the controller decides.

**D-8 — no i18n key, no a11y assertion, no visual baseline.** The story adds no rendered string and no new interactive control; the NFR ownership matrix (`epics.md:4417-4420`) names 50.3 / 51.x / 52.x / 53.2 as the i18n and a11y owners and does **not** name 50.2. `en.json` / `pl.json` and `apps/web/tests/visual/**` must show zero-line diffs, and `npm run test:visual` must be green **UNCHANGED** — no `--update-snapshots`, ever, in this story.

**D-9 — no `useCategories()` call, no slug→label resolution, no chip.** A raw slug is never displayed in this story; nothing renders it, so nothing needs to translate it. Calling 50.1's `useCategories()` here would add a request to the catalog route for data nothing shows. The chip, the label and the counts are **51.2 / 51.1**.

**D-10 — `q` is left exactly as-is.** FR26-BROWSE-2's *"a search started inside a category stays scoped by default"* is satisfied here **structurally, for free**: every navigation helper in `CatalogList` (`setFilters` `:63`, `toggleTag` `:86`, `toggleUntagged` `:105`, `setPage` `:116`, the Switch-to-OR handler `:245`) spreads `...prev`, so a present `category` survives every filter and search change with no new code. §7.2 case 4 proves it rather than assuming it. Do **not** add a bespoke preservation mechanism.

---

## 5. Cache-coherence enumeration (mandatory — project-context §286)

Required because this story changes what feeds an existing shared query key.

| Invariant | `useModels` `["sot","models",filters]` — **no** `category` in the URL (every user today) | `useModels` `["sot","models",filters]` — `category` present | `useCategories` `["sot","categories"]` (50.1) |
|---|---|---|---|
| **Staleness budget** | **Unchanged, 30 s** + `keepPreviousData` (`useModels.ts:32,38`). This story adds a filter key, it does not re-budget the read. | Same 30 s — the same query, one more AND-composed predicate. | **Not mounted by this story** (D-9). |
| **Retry policy** | Unchanged — `api()`'s 401→refresh→retry-once; TanStack default otherwise. | Unchanged. An unknown slug is **200 + empty page**, not an error, so there is nothing to retry and nothing to surface as `isError`. | n/a |
| **Cache propagation (mutations)** | Unchanged — no FE model mutation is touched. | Same. E52's admin replace-set writes will invalidate `["sot","models"]`; not wired here (YAGNI). | n/a |
| **Cache eviction on route exit** | Default gc. Catalog listings are neither per-token nor sensitive. | Default gc. | n/a |
| **Cache seeding on this route** | None. | None — the scope is a query predicate, not a fetched entity. | n/a |
| **Key identity vs today** | **Identical hash** — `hashKey`'s `JSON.stringify` drops `undefined`-valued properties, so `{…, category: undefined}` ≡ today's object (D-5). No refetch, no cache split. | New distinct key per slug, which is correct: a different scope is a different result set. | n/a |

**Divergence check:** none. No column disagrees with another. The only cross-surface coupling — an admin category rename or a replace-set write changing which models a scope returns — is owned by **E52** and reachable through the already-stable `["sot","models"]` prefix.

---

## 6. Acceptance criteria

1. **`CatalogSearch` gains `category?: string`** — optional, a single `string`, never an array, never a UUID type, positioned after `source` and before `sort`.
2. **`validateSearch` accepts a plain slug**: `{ category: "home-decor" }` → `{ category: "home-decor" }`.
3. **Trim + drop-if-empty**: `" home-decor "` → `"home-decor"`; `""`, `"   "` → the key is **absent** from the output (not `""`, not `undefined`-valued).
4. **Non-string shapes are dropped**: array (including a two-element one), number, boolean, `null`, object → the key is absent. Exactly-one-scope is enforced by dropping, never by silently picking (D-1).
5. **No format validation**: `"UPPER_case"`, `"kategoria-łazienka"`, `"a"`, a 200-character string and any other well-formed non-empty string **survive unchanged**. No regex, no lowercasing, no length cap, no allow-list (D-2).
6. **Independence from the facet layer, proven in both directions**: `category` present alongside `tag_ids` + `tag_match` leaves both **exactly** as the 43.3/44.2 rules already produce them; and `category` present alongside a stranded `tag_match` (<2 tags) does **not** rescue it. The `tag_ids` UUID hardening and the ≥2-tag `tag_match` normalization are **byte-unchanged** in source (D-3).
7. **Round-trip**: `category` survives `defaultStringifySearch` → `defaultParseSearch` → `validateSearch`, including a value needing percent-encoding. A normalized-away `category` produces a query string containing **no** `category` key.
8. **Unknown-key stripping still holds** with `category` present; the existing combined-object assertion extended with `category` still yields exact equality.
9. **`CatalogList` sends the scope to the API**: mounting `/catalog/?category=home-decor` produces a `/api/models` request whose query string contains `category=home-decor`.
10. **Zero behaviour change when no category is present**: mounting `/catalog/` (and any pre-existing filter URL) produces `/api/models` requests containing **no** `category` key, byte-identical to today. Every pre-existing `CatalogList.test.tsx` and `index.test.ts` assertion stays green **with no edit**.
11. **`Filters (n)` is invariant under the scope** (FR26-BROWSE-2's verifiable): the Filters trigger's badge text is **identical** for `?status=printed` and `?status=printed&category=home-decor`. `FilterRibbon.tsx` shows a **zero-line diff**; `FilterRibbonState` and `activeFilterCount` are untouched (D-4).
12. **The scope survives filter and search changes** without bespoke code — after a search/filter change made through the real UI on a `?category=…` URL, the next `/api/models` request still carries `category=` (D-10).
13. **`Clear filters` clears filters and preserves the scope** (§3.4): from `?category=home-decor&status=printed` with an empty result, clicking Clear filters produces a request that still carries `category=home-decor` and no longer carries `status=`.
14. **A category-only empty result offers no recovery action** — the documented, intentional D-6 edge, pinned by a test so 51.2 inherits a known state rather than a surprise.
15. **No new user-visible surface**: zero-line diffs in `src/locales/en.json`, `src/locales/pl.json`, `apps/web/tests/visual/**`, `src/routeTree.gen.ts`, `package.json` and the lockfiles; zero changes under `apps/api/**`, `workers/**`, `infra/**`; `modules/catalog/hooks/useModels.ts` **byte-unchanged** (50.1 already shipped the filter key — do **not** re-edit it).
16. **Green gates**: `npm run typecheck`, `npm run lint --max-warnings=0`, `npm run test`, `npm run build` all pass; `npm run test:visual` green **UNCHANGED** (no baseline added, changed or regenerated); `git diff --check` clean.
17. **TDD**: every deliverable lands RED-first with captured evidence (§8). The validator tests are authored **before** the validator branch.
18. **NFR26-DETERMINISM-1**: 3× consecutive identical vitest pass counts before merge.

---

## 7. Test strategy

**Non-negotiable conventions** (verified in-repo, not recalled):
- `vitest.config.ts` has **`globals: false`**, so every multi-`it` test file needs `import { cleanup } from "@testing-library/react"; afterEach(cleanup);`. `CatalogList.test.tsx` already has it (`:26-29`); `index.test.ts` renders nothing and needs none.
- **Do not mock `api()`** — `CatalogList.test.tsx` intercepts at `fetch` via `vi.stubGlobal` (`:116`). Keep it.
- `CatalogList.test.tsx` calls `await i18n.changeLanguage("en")` in `beforeAll` (`:32`), so **assertions in this file are English** (its existing matchers use `/English|Polski/` alternation for safety). This is the opposite of the Playwright visual suite, which is pinned to **pl-PL** — do not carry a matcher between the two.
- `mountAt(url)` (`:123-142`) reuses the **real** `CatalogRoute.options.validateSearch`, so these integration tests exercise the production normalization path, not a stub.

### 7.1 UPDATE — `apps/web/src/routes/catalog/index.test.ts` (the story's own validator gate)

Add one `describe("catalog validateSearch — category (Story 50.2)")` block. **Do not edit any existing block.** Minimum cases:

1. **Accepts a plain slug** — `v({ category: "home-decor" })` → `{ category: "home-decor" }`. (AC-2)
2. **Trims** — `v({ category: "  home-decor  " })` → `{ category: "home-decor" }`. (AC-3)
3. **Drops empty and whitespace-only** — `v({ category: "" })` → `{}`; `v({ category: "   " })` → `{}`. (AC-3)
4. **Drops non-string shapes** — `v({ category: ["a", "b"] })` → `{}` (the exactly-one-scope proof: assert `{}`, **not** `{category:"a"}`); also `5`, `true`, `null`, `{}`. (AC-4)
5. **No format validation** — each of `"UPPER_case"`, `"kategoria-łazienka"`, `"a"`, `"x".repeat(200)`, `"has.dots"` survives verbatim. (AC-5)
6. **Independence from the facets** —
   - `v({ category: "home-decor", tag_ids: [UUID_A, UUID_B], tag_match: "any" })` → all three keys, `tag_match` still `"any"`;
   - `v({ category: "home-decor", tag_match: "any" })` → `{ category: "home-decor" }` only — the ≥2-tag rule is **not** relaxed by the scope's presence;
   - `v({ category: "home-decor", tag_ids: ["not-a-uuid"] })` → `{ category: "home-decor" }` only — the UUID hardening is untouched. (AC-6)
7. **Round-trip** — `defaultStringifySearch({ category: "home-decor", q: "vase" })` contains `category=home-decor`, and `v(defaultParseSearch(qs))` returns the same object; separately, a value needing encoding (e.g. `"a b"`) round-trips to `"a b"`. `defaultStringifySearch(v({ category: "" }))` contains **no** `category`. (AC-7)
8. **Coexistence with every other key** — extend the existing AC-6-style combined assertion with `category: "home-decor"` in a **new** `it` (leave the original untouched, so it keeps proving the pre-50.2 shape), and confirm `v({ legacy_param: "x", category: "home-decor" })` → `{ category: "home-decor" }`. (AC-8)

### 7.2 UPDATE — `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` (integration; keeps FR26-BROWSE-2 non-vacuous)

Model every case on the existing *"sends `untagged=true`…"* test (`:192-199`). Six cases:

1. **Scope reaches the API** — `installFetch()`; `mountAt("/catalog/?category=home-decor")`; `await waitFor(() => expect(calls.some((u) => u.includes("/api/models") && u.includes("category=home-decor"))).toBe(true))`. (AC-9)
2. **No category ⇒ no `category` key** — `mountAt("/catalog/?status=printed")`; assert **every** `/api/models` call satisfies `!u.includes("category=")`. The D-5 regression lock. (AC-10)
3. **`Filters (n)` invariance** — mount `?status=printed`, read the Filters trigger button's `textContent` (found by its `aria-label`, `catalog.filters.openFilters`); `cleanup()`; mount `?status=printed&category=home-decor`; assert the badge text is **identical** (and that it is `"1"`, so the assertion cannot pass on two empty strings). (AC-11)
4. **The scope survives a search change** — `mountAt("/catalog/?category=home-decor")`, then `fireEvent.change` on the FilterRibbon search input with a value; assert a subsequent `/api/models` call carries **both** `q=` and `category=home-decor`. This exercises `setFilters` → `navigate({ search: (prev) => ({ ...prev, … }) })`. (AC-12)
5. **`Clear filters` preserves the scope** — `mountAt("/catalog/?category=home-decor&status=printed")` with the stub's default `total: 0`; the Clear-filters button is present (status makes `filtersActive` true); click it; assert the next `/api/models` call carries `category=home-decor` and **not** `status=`. (AC-13)
6. **Category-only empty result offers no recovery action** — `mountAt("/catalog/?category=home-decor")` with `total: 0`; the empty message renders and **neither** the Clear-filters nor the Switch-to-OR button exists. Add the D-6 rationale as a comment in the test so the behaviour reads as intentional. (AC-14)

The stub in `installFetch` (`:99-115`) needs **no** change — its `/api/models` branch already returns `{ items: [], total: 0, … }` for any URL that is not `tag_match=any` or `offset=48`. Do not widen it.

### 7.3 No new file, no new fixture, no new stub

Both test files already exist and both already have the harness this story needs. Creating a third test file, a `CatalogSearch` factory, or a new visual spec is **out of scope**.

---

## 8. RED→GREEN evidence (dev-time; tee to gitignored `.hermes/run-logs/e50.2-*.log`)

1. **RED — validator (type).** Author the §7.1 block first. Before `CatalogSearch` gains the key, `npm run typecheck` fails on the property access with `TS2339` (`Property 'category' does not exist on type 'CatalogSearch'`). → `e50.2-red-typecheck.log`.
2. **RED — validator (behaviour).** `npx vitest run src/routes/catalog/index.test.ts` fails on the accept/trim cases: `expected {} to deeply equal { category: 'home-decor' }`. **Both RED forms are required** — the type RED alone does not prove the branch is missing, and vitest alone is not the type gate (esbuild erases `import type`). → `e50.2-red-vitest-validator.log`.
3. **RED — wiring.** Author the §7.2 cases before touching `CatalogList.tsx`. Case 1 fails (no `/api/models` call contains `category=`); case 5 fails (Clear filters drops the scope). → `e50.2-red-vitest-cataloglist.log`.
4. **GREEN.** Apply §3.1 → §3.4 in that order. Focused vitest on both files PASS; `npm run typecheck` PASS; `npm run lint` PASS; full `npm run test` PASS ×3 with identical counts; `npm run build` PASS. → `e50.2-green-*.log`.
5. **Route-tree no-op proof.** After `npm run build`, `git status --porcelain apps/web/src/routeTree.gen.ts` must be **empty**. Record the literal output. If it is non-empty, **stop and report** (D-7).
6. **Visual.** `npm run test:visual` runs at the closeout gate and must be green with **zero** baseline changes. Never `--update-snapshots` in this story.

---

## 9. Gates + ownership

- **Dev-time (dev owns):** `npm run typecheck`, `npm run lint` (`--max-warnings=0`), focused + full `npm run test` ×3 (NFR26-DETERMINISM-1), `npm run build`, the §8.5 `routeTree.gen.ts` no-op proof, `git diff --check` clean.
- **Closeout (controller owns):** `infra/scripts/check-all.sh` all-green standalone, teed to `.hermes/run-logs/check-all-*.log`, before the ff-only merge to `main` (AGENTS.md § gate evidence). Native `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor), then the independent external review per the Laura Agent Rulebook — **Aider** (`laura-aider-review-diff`) is the routine route; **Codex** is fallback / high-stakes / repo-mandated only; **Gemini is not a route**.
- **Branch:** `feat/E50.2-url-state-category-scope` off `main` — created by `bmad-dev-story`, **not** by this spec run.
- **Status ownership:** the `50-2` flip past `ready-for-dev` and any `epic-50` change are **controller-owned**. `epic-50` is already `in-progress` (flipped at 50.1 closeout) and this run does **not** touch it.
- **Deploy:** the story touches `apps/web/**` only, so a merge to `main` is a non-skip-prefixed commit and deploys normally. **Mandatory for a UI-touching commit:** `npm run test:visual` before commit (AGENTS.md § Execution discipline) — here it must be green *unchanged*.

---

## 10. Scope fences (explicit "do not")

- **Do not add a slug regex, an allow-list, a length cap, or lowercasing** to `category` (D-2). This is the most likely wrong instinct in this story.
- **Do not edit `modules/catalog/hooks/useModels.ts`** — 50.1 shipped `ModelsFilters.category` and the `buildParams` branch. Byte-unchanged.
- **Do not edit `FilterRibbon.tsx`** — not `FilterRibbonState`, not `activeFilterCount`, not the badge (D-4). Zero-line diff.
- **Do not add `category` to `CatalogList.filtersActive`** (D-6).
- **Do not call `useCategories()` / `useCategoryBySlug()`**, and do not render a chip, a label, a count, or a "Search entire catalog" control — **Story 51.2** (D-9).
- **Do not add a route file, and do not hand-edit `routeTree.gen.ts`** (D-7; it is also lint-ignored as `**/*.gen.ts`).
- **Do not add an i18n key or touch `en.json` / `pl.json`; do not add, change or regenerate any visual baseline** (D-8).
- **Do not touch the suggestion surface or `GET /api/tags?q=`** — Story 50.3.
- **Do not touch `apps/api/**`, `workers/**`, `infra/**`, `package.json` or the lockfiles.** No backend change is needed: `category` shipped in 49.3.
- **Do not touch `modules/admin/ProfileOffers*`** — its `material_category` / `reason_category` are an unrelated domain that merely shares a word.
- **Do not fold `category` into `tag_match`, and do not touch the `tag_ids` UUID hardening or the ≥2-tag `tag_match` rule** (FR26-BROWSE-3, D-3).

---

## 11. Verification performed for this spec

- `bmad-help` run (mandatory, session start) → canonical route recorded in the header from `_bmad/_config/bmad-help.csv:26-28`; canonical skill ID/path confirmed at `_bmad/_config/skill-manifest.csv:40`. Effective config resolved via `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` (`communication_language: Polish`; `document_output_language: English`; `implementation_artifacts = _bmad-output/implementation-artifacts`). Skill customization resolved via `_bmad/scripts/resolve_customization.py --key workflow` → no prepend/append steps; `persistent_facts` = `project-context.md`, loaded.
- **Sprint-status state confirmed at `main` @ `c436f61`, clean tree:** `epic-50: in-progress`, `50-1-fe-types-and-hooks: done`, `50-2-url-state-category-scope: backlog` (the first `backlog` story key top-to-bottom in `development_status`), `50-3-inline-structured-suggestions: backlog`, `epic-49: done` with 49.1–49.5 all `done`. **No duplicate or in-progress 50.2 artifact:** `find _bmad-output -iname '*50-2*' -o -iname '*url-state*' -o -iname '*category-scope*'` returns only the unrelated historical `43-3-url-state.md`. Exactly one story is in flight.
- Shipped code read at source in this run, not from the sketch: `apps/web/src/routes/catalog/index.tsx` (full), `modules/catalog/routes/CatalogList.tsx` (full), `modules/catalog/components/FilterRibbon.tsx` (full), `modules/catalog/hooks/useModels.ts` (full), `src/routes/catalog/index.test.ts` (full), `modules/catalog/routes/CatalogList.test.tsx` (full), `src/routeTree.gen.ts` (targeted greps), `apps/web/vite.config.ts:6-36`, `apps/web/package.json` scripts; backend `sot/router.py:155-232`, `sot/service.py:176-247,355-380`, `sot/schemas.py:85-133`, `sot/admin_schemas.py:296-340`, `core/db/seed.py:275-300`.
- Planning artifacts read at source: `epics.md:4375-4604` (whole Initiative 26 block, including the FR/NFR matrices and every E50–E54 sketch, for cross-story boundary checks), `prd.md:2251-2252` (FR26-BROWSE-2/3).
- Precedent stories read: `50-1-fe-types-and-hooks.md` (full — the shipped data layer, its D-1…D-7 decisions and its two open defers) and the `43-3-url-state.md` validator lineage as it survives in `index.tsx:30-34,68-80` and `index.test.ts`.
- Negative greps across `apps/web/src`: `category` in `routes/catalog/index.tsx` → **0**; `search` in `routeTree.gen.ts` → **0**; catalog-domain `category` outside 50.1's `useModels` → **0** (only the unrelated admin `material_category` / `reason_category`).
- **Subagents were available but deliberately not used** for this analysis: this session's harness instruction is not to invoke the Agent tool unless the user requests it, and the controller did not. All artifact and code analysis above was performed inline in a single 1M-context session. Stated rather than implied, because the skill's default is to fan out.
- **Not verified (out of remit, stated rather than implied):** no code was written, no test was executed, no build / typecheck / lint / visual run was performed for this story. The RED evidence in §8 and the gate results in §9 are **dev-time obligations, not claims already discharged**. No human review of any kind is recorded.

---

## 12. Validation record — native `bmad-create-story:validate` (VS), 2026-07-28

**Verdict: PASS.** Fresh validation pass over the created artifact against `.claude/skills/bmad-create-story/checklist.md`, re-tracing the shipped code rather than trusting §2. The story's ACs are each mechanically checkable against a named file and line, its RED→GREEN path is executable under the real `tsc -b` / vitest configuration, its scope fences match the epic sketch and the FR text, and its one genuinely load-bearing asymmetry (D-2) is stated with the contract evidence rather than as a style preference.

**Provenance honesty.** This was a **separated second pass within the same session**, not an independent fresh-context agent — the strongest form available under this run's constraints, and it is labelled as such rather than dressed up. It re-read the primary sources itself; it did not accept §2 as given. Items 1–5 are disaster classes the Create pass anticipated and resolved while authoring, each **re-verified at source** by this pass. Items 6–8 are defects this pass actually caught in the created draft and corrected in place. All edits are spec-only; no production or test file was touched.

**Findings:**

1. **[critical — regression disaster, re-verified] Mirroring the `tag_ids` UUID hardening onto `category`.** The two params sit four lines apart in the same validator, and the adjacent one is aggressively hardened with a documented regex. A dev agent copying the pattern would add a slug regex that is stricter than the wire contract and would silently delete legitimately admin-created slugs. **Verified at source by this pass:** `router.py:196` types `category` as a bare `str | None` (no `Query(pattern=…)`), and `admin_schemas.py:302` types the authoring field as `Field(min_length=1)` with no `pattern` — so there is no 422 failure mode to protect against and no format to enforce. D-2 states the asymmetry as a table with both wire types, and AC-5 makes "exotic-but-legal slugs survive" an explicit positive assertion rather than a silence.
2. **[critical — dead-state disaster, re-verified] The URL layer with no consumer.** `useModels` accepts `category` (50.1) but `CatalogList.tsx:41-50` never passes it — re-read and confirmed in this pass. Without §3.3 the story would ship a URL param that validates, persists across navigation and changes nothing: a URL that lies. D-5 puts the wiring in scope with the cache-key safety argument, and AC-9 makes it a request-level assertion rather than a code-shape one.
3. **[critical — false-fence disaster, re-verified] `Filters (n)` and `filtersActive` are two different predicates.** Confirmed at source: `activeFilterCount` (`FilterRibbon.tsx:52-58`) counts only `status`/`source`/non-default `sort` — **not even `tag_ids`** — and is the badge; `filtersActive` (`CatalogList.tsx:162-167`) is a separate boolean gating the empty-state Clear-filters action. A story that wrote "keep category out of the filter count" without naming both would leave a dev agent free to satisfy the letter in the wrong place. D-4 and D-6 separate them explicitly, and §2's table row calls the conflation out by name.
4. **[important — cache disaster, re-verified] The query key could have churned.** `useModels` keys on the whole `filters` object (`useModels.ts:30`). Adding a key with an `undefined` value is only free because TanStack's `hashKey` runs `JSON.stringify`, which omits `undefined`-valued properties. Left unstated, a reviewer could not distinguish "safe" from "every existing user silently refetches". D-5 states the mechanism, §5's last row tabulates it, and AC-10 / §7.2 case 2 lock it behaviourally.
5. **[important — regression lock, re-verified] The existing validator tests use exact-object `toEqual`.** Re-read `index.test.ts` in full: none of the 20-odd assertions passes `category`, so adding an output key breaks nothing — but that had to be *checked*, not assumed, before AC-10 could promise "green with no edit". Confirmed; §7.1 accordingly forbids editing any existing block and requires the extended combined-object case to be a **new** `it`.
6. **[important — missing invariant; caught by this pass] `Clear filters` silently wiped the scope.** The draft's D-6 correctly refused to add `category` to `filtersActive`, but was silent on the *other* half: both `clear_filters` handlers call `navigate({ search: {} })` (`CatalogList.tsx:257,282`), which drops `category` along with everything else. That directly contradicts "category is an independent layer, not a filter" and would have shipped as an invisible scope-loss bug the moment 51.2 made scopes reachable. **Fixed:** §3.4 adds the two-line change with its rationale, AC-13 asserts it, and §7.2 case 5 tests it. The change is behaviour-identical for every URL reachable today, which is stated rather than left for a reviewer to derive.
7. **[important — undisclosed dead end; caught by this pass] The category-only empty state has no recovery action.** A consequence of D-6 that the draft left implicit. Unstated, it would surface at 51.2 as an unexplained regression, or would tempt the dev agent into building a stand-in escape control that 51.2 must then reconcile. **Fixed:** D-6 now discloses the edge with its three reasons, names the rejected alternative, hands the escape control to 51.2 explicitly, and AC-14 / §7.2 case 6 pin the behaviour as **intentional**.
8. **[minor — proof vs assertion; caught by this pass] The route-tree no-op was asserted, not provable.** The draft said regeneration is not required. True, but a dev agent could not *demonstrate* it. **Fixed:** D-7 records that the `TanStackRouterVite` plugin (`vite.config.ts:28`) regenerates during `npm run build`, so §8.5 turns the claim into a free, recorded check (`git status --porcelain src/routeTree.gen.ts` empty) with a stop-and-report escape hatch.

**Independently verified against source by this pass (no defect found):**

- **Validator shape** (`index.tsx:36-45,49-103`): `CatalogSearch` has eight optional keys and no `category`; the `UUID_RE` hardening and the ≥2-tag `tag_match` normalization are exactly as §2 describes; the insertion point §3.2 names (between the `source` and `sort` branches) is real and does not disturb either.
- **Backend contract** (`router.py:196`, `service.py:357-375`): one bare-string slug, exact case-sensitive `==` match, structurally outside the tag composition (so `tag_match` genuinely never sees it — FR26-BROWSE-3 holds by construction, not by frontend discipline), unknown slug → 200 + empty page, and `if category is not None` confirming that an empty string is a real filter. AC-3's drop-if-empty is therefore load-bearing, exactly as D-1 claims.
- **50.1 data layer** (`useModels.ts:15-18,61`): `ModelsFilters.category?: string` and the `length > 0` guard are shipped; the story correctly requires this file to stay byte-unchanged rather than re-editing it.
- **Test harnesses** (`CatalogList.test.tsx:26-29,32,99-142,192-199`): `afterEach(cleanup)` present; `i18n.changeLanguage("en")` in `beforeAll` (so §7's English-vs-pl-PL note is correct and load-bearing); `mountAt` reuses the real `validateSearch`; `installFetch`'s `/api/models` branch already returns `total: 0` by default, so §7.2 needs no stub widening — checked, not assumed.
- **Route tree** (`routeTree.gen.ts`): `grep -c search` → **0**; the only `catalog` hits are route `id`/`path`/import lines. D-7's premise holds.
- **NFR ownership** (`epics.md:4413-4423`): NFR26-I18N-1 and NFR26-A11Y-1 name 50.3 / 51.1–51.4 / 52.1–52.3 / 53.2 — **50.2 is absent from both**, which is what licenses D-8. NFR26-VISUAL-1 says "all UI stories"; since this story renders nothing new, "green UNCHANGED" (AC-16) is the correct discharge, and the story says so rather than claiming an exemption.
- **Cross-story boundaries** (`epics.md:4507-4509,4531-4533,4551-4553`): the chip, the `/categories/$slug` route and the "Search entire catalog" escape are 51.2; the `Filters (n)` drawer is 52.1; the suggestion surface is 50.3. No fence in §10 claims scope another story owns, and no §10 fence blocks something 50.2 must do.
- **State/uniqueness gates:** `git status --porcelain` clean at creation; `main` @ `c436f61` matches the controller-supplied SoT SHA; `sprint-status.yaml` re-parsed with `yaml.safe_load` after the edit — well-formed, `50-2-url-state-category-scope: ready-for-dev`, `epic-50: in-progress` (untouched by this run), `50-1: done`, `50-3: backlog`.

**Not verified (out of remit, stated rather than implied):** no code was written, no test, build, typecheck, lint or visual run was executed, and no gate was reproduced. No human review is recorded — the validation authority here is a native BMAD agent pass under Laura/controller's standing Initiative 26 authorization, **not** an Ezop signature.

---

## 13. Tasks / Subtasks — dev execution (native `bmad-dev-story`, after G26-DEVGO)

- [x] **T1 — RED first (validator).** Add the §7.1 `describe` block to `src/routes/catalog/index.test.ts`. Edit **no** existing block. Capture **both** REDs: `npm run typecheck` (`TS2339` on `.category`) and `npx vitest run src/routes/catalog/index.test.ts` (behavioural). → `.hermes/run-logs/e50.2-red-*.log`.
- [x] **T2 — RED first (wiring).** Add the six §7.2 cases to `modules/catalog/routes/CatalogList.test.tsx`. Capture the RED (no `/api/models` call carries `category=`; Clear filters drops the scope).
- [x] **T3 — GREEN interface.** Add `category?: string` to `CatalogSearch` (§3.1), after `source`, before `sort`, with the comment.
- [x] **T4 — GREEN validator.** Add the single branch (§3.2) between the `source` and `sort` branches. **No regex, no lowercasing, no length cap** (D-2). Do not touch the `tag_ids` or `tag_match` hunks.
- [x] **T5 — GREEN wiring.** Add `category: search.category` to the `useModels({...})` call (§3.3), after `source`, before `q`.
- [x] **T6 — GREEN scope preservation.** Change both `clear_filters` handlers to preserve `category` (§3.4). Nothing else in either handler changes.
- [x] **T7 — Preserve.** `git diff` shows **zero lines** in `modules/catalog/hooks/useModels.ts`, `modules/catalog/components/FilterRibbon.tsx`, `modules/catalog/components/FacetSidebar.tsx`, `src/locales/*.json`, `apps/web/tests/**`, `src/routeTree.gen.ts`, `package.json` / lockfiles, `apps/api/**`, `workers/**`, `infra/**`. `CatalogList.filtersActive` unchanged (D-6).
- [x] **T8 — Green gates.** Focused vitest on both touched test files, `npm run typecheck`, `npm run lint`, full `npm run test` ×3 (identical counts — NFR26-DETERMINISM-1), `npm run build`. Then the §8.5 route-tree no-op proof: `git status --porcelain apps/web/src/routeTree.gen.ts` **empty** (stop and report if not). `git diff --check` clean. **No `--update-snapshots` at any point.** Evidence → `.hermes/run-logs/e50.2-green-*.log`.

---

## 14. Dev Agent Record

### 14.1 Agent Model Used

Claude Opus 5 (1M context), `claude-opus-5[1m]`, running native `bmad-dev-story` (DS) inline in a single session. Routing re-confirmed by a mandatory `bmad-help` run at the validate → development pivot: `_bmad/_config/bmad-help.csv` gives `bmad-dev-story` (menu **DS**, phase `4-implementation`, `preceded-by: bmad-create-story:validate`, `followed-by: bmad-code-review`, `required=true`); canonical skill ID/path confirmed at `_bmad/_config/skill-manifest.csv:42` (`_bmad/bmm/4-implementation/bmad-dev-story/SKILL.md`). Activation resolved via `resolve_customization.py --key workflow` → **no** prepend/append steps, `persistent_facts` = `project-context.md` (loaded). Config resolved via `resolve_config.py` (`communication_language: Polish`, `document_output_language: English`, `user_skill_level: intermediate`). **No subagents were used** — this session's harness instruction forbids invoking the Agent tool unless the user requests it, and the controller did not. No BMAD skill protested at any point.

### 14.2 Debug Log References

All logs teed to the gitignored `.hermes/run-logs/`. RED was captured **before any production line was written**, in both forms §8 requires.

| Phase | Log | Literal result |
|---|---|---|
| **RED — validator (type)** | `e50.2-red-typecheck.log` | `npm run typecheck` **rc=1**, exactly one error: `src/routes/catalog/index.test.ts(181,42): error TS2339: Property 'category' does not exist on type 'CatalogSearch'.` |
| **RED — validator (behaviour)** | `e50.2-red-vitest-validator.log` | `npx vitest run src/routes/catalog/index.test.ts` **rc=1** — **7 failed / 24 passed (31)**. The 3 new cases that pass at RED are the drop-behaviour ones (empty/whitespace, non-string shapes, normalized-away serialization), which are correctly vacuous-green before the branch exists. |
| **RED — wiring** | `e50.2-red-vitest-cataloglist.log` | `npx vitest run …/CatalogList.test.tsx` **rc=1** — **3 failed / 8 passed (11)**. Failures are exactly §7.2 cases **1** (`category=` never reaches `/api/models`), **4** (scope lost on a search change) and **5** (Clear filters drops the scope). Cases 2, 3 and 6 pass at RED by construction — they assert *absence*/*invariance*. |
| **GREEN — focused** | `e50.2-green-vitest-focused.log` | **rc=0** — 2 files, **42/42 passed** (31 validator + 11 CatalogList). |
| **GREEN — typecheck** | `e50.2-green-typecheck.log` | `npm run typecheck` (`tsc -b`) **rc=0**. |
| **GREEN — lint** | `e50.2-green-lint.log` | `npm run lint` (`eslint . --max-warnings=0 && stylelint`) **rc=0**. |
| **GREEN — full suite ×3** | `e50.2-green-vitest-full-x3.log` | `npm run test` **rc=0** three consecutive times, **identical counts each run: 139 files / 820 tests passed**. NFR26-DETERMINISM-1 satisfied. 820 = the 804 recorded at the 50.1 closeout **+ exactly the 16 new tests** (10 validator + 6 integration). |
| **GREEN — build** | `e50.2-green-build.log` | `npm run build` (`tsc -b && vite build`) **rc=0**, `✓ built in 10.13s`. |
| **GREEN — visual** | `e50.2-green-visual.log` | `npm run test:visual` **rc=0** — **536 passed, 32 skipped** across all four projects (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`). Same 536/32 figures as the 50.1 closeout. **No `--update-snapshots` was used at any point.** |

### 14.3 Completion Notes List

**Route-tree no-op proof (§8.5 / D-7) — recorded, not asserted.** After `npm run build` (which is what runs the `TanStackRouterVite` plugin), `git status --porcelain apps/web/src/routeTree.gen.ts` printed **nothing**. Corroborated byte-wise: `sha256(HEAD:routeTree.gen.ts) == sha256(worktree)` = `2a87ed4cc1467ecc…`. The stop-and-report hatch was therefore **not** triggered.

**Fence proof (T7) — measured, not claimed.** `git diff --numstat` over the whole fenced set printed **nothing**: `useModels.ts`, `FilterRibbon.tsx`, `FacetSidebar.tsx`, `src/locales/**`, `apps/web/tests/**` (incl. every visual baseline), `routeTree.gen.ts`, `api-types.ts`, `package.json`/lockfiles, `apps/api/**`, `workers/**`, `infra/**`. sha256 identity vs `HEAD` additionally confirmed for `useModels.ts` (`2fdd2415ce8fad3c…` — the same digest the 50.1 code review recorded), `FilterRibbon.tsx` (`331bbb8c70da1e73…`), `api-types.ts` (`9a28875fdecebadc…`) and `routeTree.gen.ts`. **`FilterRibbon.tsx` has the required zero-line diff (D-4); `CatalogList.filtersActive` is unchanged (D-6).**

**D-3 proof — the 43.3/44.2 hardening is byte-unchanged.** The diff of `routes/catalog/index.tsx` is exactly **two hunks** (`@@ -40,4 +40,9 @@` in the interface and `@@ -88,4 +93,18 @@` in the validator), both strictly between the `source` and `sort` branches. `UUID_RE`, the `tag_ids` normalization block and the ≥2-tag `tag_match` block fall **outside every hunk**, so they are untouched at the byte level, not merely "not intentionally edited". Independently corroborated behaviourally: all 24 pre-existing assertions in `index.test.ts` and all 5 pre-existing tests in `CatalogList.test.tsx` are green **with no edit to any existing block** (AC-10).

**Strictly additive except for the two deliberate `Clear filters` lines.** `git diff --numstat`: `index.tsx` **+19/-0**, `index.test.ts` **+94/-0**, `CatalogList.test.tsx` **+101/-0**, `CatalogList.tsx` **+18/-2**. The only two deleted lines in the entire change are the two `void navigate({ search: {}, replace: true });` calls replaced by §3.4's scope-preserving updater — verified by listing every `-` line in the diff.

**D-2 honoured.** No regex, no allow-list, no lowercasing, no length cap on `category`. AC-5 is a positive assertion, not a silence: `"UPPER_case"`, `"kategoria-łazienka"`, `"a"`, a 200-character string and `"has.dots"` each survive verbatim.

**D-1 honoured.** An array is dropped **wholesale** — the test asserts `v({ category: ["a","b"] })` equals `{}`, explicitly *not* `{ category: "a" }`, so a future silent-pick regression fails the suite.

**AC-11 is non-vacuous.** The badge-invariance test reads the real Filters trigger's `textContent` through the mounted component (found by its accessible name, `aria-label="Filters"`), pins it to contain `"1"` on the no-category mount, then asserts strict equality against the with-category mount — so it cannot pass on two empty strings.

**Prettier drift observed, deliberately not "fixed" (minor, out of scope).** `npx prettier --check` flags all four touched files — but it flags the **`HEAD` versions of the same four files too** (verified by piping `git show HEAD:<path>` through `prettier --check`). The drift is pre-existing, `npm run lint` is `eslint --max-warnings=0 && stylelint` (prettier is not a gate), and running `prettier --write` would rewrite lines this story does not own. Recorded here rather than silently widening the diff.

**No new dependency, no configuration change, no HALT condition was triggered.** Nothing in §10's "do not" list was touched. No story premise turned out to be wrong, so the §8.5 / §14.4 stop-and-report hatches went unused.

### 14.4 File List

**Confirmed — the planned 4 files were exactly the 4 files changed. No fifth path was named by `tsc`, the test runs or the build, so the "stop and report" hatch was not triggered.**

- `apps/web/src/routes/catalog/index.tsx` — UPDATE (§3.1 interface key, §3.2 validator branch) — +19/-0
- `apps/web/src/routes/catalog/index.test.ts` — UPDATE (§7.1, one new `describe` with 10 `it`s; no existing block edited) — +94/-0
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` — UPDATE (§3.3 `useModels` wiring, §3.4 both `clear_filters` handlers) — +18/-2
- `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` — UPDATE (§7.2, one new `describe` with the 6 cases; no existing block edited) — +101/-0

Plus this artifact and `_bmad-output/implementation-artifacts/sprint-status.yaml`. `git status --porcelain` at the end of this run lists exactly these six paths and nothing else (the artifact itself still shows as `??` because it has never been committed).

---

## 15. Change log

| Date | Pass | Change |
|---|---|---|
| 2026-07-28 | `bmad-create-story:create` | Artifact created at `main` @ `c436f61` after mandatory `bmad-help`. `sprint-status.yaml`: `50-2-url-state-category-scope` `backlog` → `ready-for-validation`. `epic-50` left at `in-progress` (already flipped at 50.1 closeout) — **not** touched by this run. |
| 2026-07-28 | `bmad-dev-story` (DS) | Implemented under G26-DEVGO. RED captured before any production line in both required forms (`TS2339`; 7/31 validator + 3/11 integration behavioural failures), then GREEN: focused 42/42, `tsc -b` rc=0, `eslint --max-warnings=0` rc=0, full vitest **139 files / 820 tests ×3 identical**, `npm run build` rc=0, `npm run test:visual` **536 passed / 32 skipped, zero baseline changes**, `git diff --check` rc=0, route-tree no-op **proven** (`git status --porcelain routeTree.gen.ts` empty after the build). 4 files changed, exactly as planned. Status `ready-for-dev` → `review`; `sprint-status.yaml` likewise. `epic-50` **not** touched (already `in-progress`). |
| 2026-07-28 | `bmad-create-story:validate` | Verdict **PASS** (§12). Three defects corrected in place (findings 6–8): `Clear filters` scope preservation (§3.4 / AC-13), the disclosed category-only dead-end edge (D-6 / AC-14), and the route-tree no-op turned into a recorded proof (D-7 / §8.5). `sprint-status.yaml`: `ready-for-validation` → `ready-for-dev`. |

**Disclosed deviation from the vanilla workflow (create/validate run).** `bmad-create-story` step 6 sets the story status directly to `ready-for-dev` at Create. This run used the controller-requested two-step (`backlog` → `ready-for-validation` at Create, → `ready-for-dev` after the Validate pass passed), which makes the intermediate state honest when Create and Validate run in one session. The **terminal** value is identical to the vanilla flow and to the Initiative 26 precedent (49.5, 50.1 both landed at `ready-for-dev` from a single create+validate run). No other workflow step was altered, and no skill protest occurred at any point in this run.

---

## 16. Dev run record — native `bmad-dev-story` (DS), 2026-07-28

**Authorization posture, stated plainly.** This DS run executed under **G26-DEVGO**, granted by **Laura/controller** for this Story 50.2 under the user's standing Initiative 26 authorization. That is **controller authorization only — NOT Ezop human review, NOT an Ezop signature, and not human review of any kind.** No Aider, no Codex, no Gemini participated in this run. The story's scope was taken exactly as validated; nothing was widened, narrowed or reinterpreted.

**Actions NOT taken (controller-owned, per §9).** No commit, no stage, no push, no merge, no deploy, no migration, no seed, no live-DB and no network action. `infra/scripts/check-all.sh` was **not** run; native `bmad-code-review` (CR) was **not** run; the independent external review (`laura-aider-review-diff` — Aider is the Rulebook's routine route, Codex fallback/high-stakes only, Gemini not a route) was **not** run. `epic-50` was **not** touched and stays `in-progress`. Branch `feat/E50.2-url-state-category-scope` already existed off `main` @ `c436f61`; this run did not create, rebase or retarget it.

**Gates this run owns — all run, all green, each with its literal result in §14.2.** Focused RED×3 → GREEN 42/42; `npm run typecheck` rc=0; `npm run lint` rc=0; `npm run test` 139 files / 820 tests ×3 identical; `npm run build` rc=0; `npm run test:visual` 536 passed / 32 skipped with **zero** baseline changes; `git diff --check` rc=0; the §8.5 route-tree no-op proof empty.

**Acceptance criteria.** AC-1 … AC-18 are all satisfied and each is backed by a named test or a recorded command result rather than by prose — the mapping is: AC-1/2/3/4/5 → the §7.1 validator block; AC-6 → its two facet-independence cases plus the D-3 hunk proof; AC-7/8 → the round-trip and coexistence cases; AC-9/10/11/12/13/14 → the six §7.2 integration cases; AC-15 → the T7 fence + sha256 proof; AC-16 → the gate table; AC-17 → the RED-before-GREEN log ordering; AC-18 → the ×3 identical full-suite counts.

**Defers, minors and blockers.** **No blockers.** **No defers** — nothing was deferred by this run, and the story's own disclosed carry-forward (D-6: the category-only empty state has no recovery action, escape control owned by **Story 51.2**) is a pre-accepted spec decision that is now *pinned by a passing test* (§7.2 case 6), not a new defer. **One minor, recorded not fixed:** `prettier --check` flags all four touched files, but it flags their `HEAD` versions identically — pre-existing drift, prettier is not part of `npm run lint`, and reformatting would rewrite lines outside this story's scope.

**What remains owed at closeout (controller).** Native `bmad-code-review` (CR) → independent Aider review (`laura-aider-review-diff`) → `infra/scripts/check-all.sh` all-green standalone teed to `.hermes/run-logs/` → commit → ff-only merge to `main` → push → `infra/scripts/deploy.sh` → post-deploy smoke → flip `50-2-url-state-category-scope` to `done`. **Controller closeout is still owed in full.**

---

## 17. Code review record — native `bmad-code-review` (CR), 2026-07-28

**LITERAL VERDICT: APPROVE.** Clean review — all three layers passed. **0** `decision-needed`, **0** `patch`, **0** `defer`, **3** dismissed as handled-elsewhere. No file was edited by this pass except this record and the `sprint-status.yaml` comment. **Status deliberately left at `review`** — see "Deviation" below.

**Routing.** Mandatory `bmad-help` run first. `_bmad/_config/bmad-help.csv` gives `bmad-code-review` (menu **CR**, phase `4-implementation`, `preceded-by: bmad-dev-story`) — exactly this state; canonical skill id/path confirmed at `_bmad/_config/skill-manifest.csv` (`_bmad/bmm/4-implementation/bmad-code-review/SKILL.md`). Customization resolved via `resolve_customization.py --key workflow` → no prepend/append steps, `persistent_facts` = `project-context.md` (loaded). Target resolved at Tier 1: spec file + "uncommitted working tree". `HEAD` = `c436f619d26ed9f1262c2566af797afeee002ba5` — **byte-identical to the artifact's `baseline_commit`**. `review_mode` = `full`. **No BMAD skill protested at any point.**

**Provenance, stated plainly.** Native BMAD CR pass under Laura/controller. **NOT Ezop human review, NOT an Ezop signature, not human review of any kind.** No Aider, no Codex, no Gemini participated. **Subagent deviation, disclosed:** the skill's step 2 launches Blind Hunter / Edge Case Hunter / Acceptance Auditor as parallel subagents; this session's harness forbids the Agent tool unless the user requests it, and the controller did not. The skill's documented fallback (write prompt files and HALT) would have returned no verdict this run, so **all three layers were executed inline, sequentially**, matching how the create/validate and DS passes on this story ran. Recorded rather than implied.

### 17.1 Gates independently re-run by this pass (not taken on trust)

Every DS-claimed figure was reproduced from scratch. **All matched exactly.**

| Gate | DS claim | CR re-run | Match |
|---|---|---|---|
| Focused vitest (both touched files) | 42/42 | **42/42** (31 validator + 11 CatalogList) | ✅ |
| `npm run typecheck` (`tsc -b`) | rc=0 | **rc=0** | ✅ |
| `npm run lint` (`eslint --max-warnings=0 && stylelint`) | rc=0 | **rc=0** | ✅ |
| Full `npm run test` | 139 files / 820 tests | **139 files / 820 tests passed** | ✅ |
| `npm run build` | rc=0, `✓ built in 10.13s` | **rc=0, `✓ built in 10.13s`** | ✅ |
| D-7 route-tree no-op | `git status --porcelain` empty, sha256 `2a87ed4cc1467ecc…` | **empty**; sha256 `2a87ed4cc1467ecc782a947c8977ba25e728924349799fe8ee0ae2c629c77eab` identical to `HEAD` | ✅ |
| `git diff --check` | rc=0 | **rc=0** | ✅ |
| `--numstat` per file | `index.tsx` +19/-0, `index.test.ts` +94/-0, `CatalogList.test.tsx` +101/-0, `CatalogList.tsx` +18/-2 | **identical** | ✅ |
| Fence set | empty | **`git diff --numstat` over the full fenced set printed nothing** | ✅ |

**Not re-run by this pass, stated rather than implied:** `npm run test:visual` (DS: 536 passed / 32 skipped) and the ×3 determinism repetition (DS: three identical full-suite runs). The full suite was run **once** here and matched DS's count exactly. The load-bearing half of the visual claim **was** independently proven: `git diff --numstat -- apps/web/tests/` is empty, so **no visual baseline was added, changed or regenerated** — mechanically, not on assertion. `infra/scripts/check-all.sh` and the Aider review were **not** run (controller-owned).

### 17.2 Findings — Critical / Important / Minor

**Critical: none.** **Important: none.**

**Minor (all dismissed as handled-elsewhere; none blocks merge, none requires a DS repair round):**

1. **Category-only empty state offers no recovery action.** `CatalogList.tsx:162-167` (`filtersActive`) deliberately excludes `category`, so `?category=<unknown-slug>` with no other filter renders the empty state with no button. **Dismissed, not deferred:** this is D-6 — a disclosed, reasoned, pre-accepted spec decision, now *pinned by a passing test* (§7.2 case 6), with the escape control (`"Search entire catalog"`) explicitly owned by **Story 51.2**. Reachable today only by a hand-crafted URL, since nothing in the UI emits `category` until 51.2. Re-raised here **only** so the 51.2 handoff cannot be lost; it is not a new defer and was correctly kept out of the deferred-work ledger.
2. **`prettier --check` flags all four touched files.** **Verified pre-existing, not introduced:** the `HEAD` version of each of the four files fails `prettier --check` identically (checked by piping `git show HEAD:<path>` through `prettier --stdin-filepath`), and a trial `prettier --write` rewrites many lines this story does not own (hunks at `CatalogList.tsx:7,195,231` and `index.tsx:34,84`, all outside the diff). Root cause is repo-wide: there is **no `.prettierrc`**, so prettier defaults to `printWidth: 80` while the codebase is written at ~100. `npm run lint` is `eslint && stylelint` — prettier is not a gate. DS recorded this honestly and correctly declined to widen the diff. Trial `--write` was reverted; `--numstat` re-verified at +18/-2 and +19/-0.
3. **Scope-preservation is proven for the search path only.** §7.2 case 4 exercises `setFilters`; the `toggleTag`, `toggleUntagged` and `setPage` paths rely on the same `...prev` spread (`CatalogList.tsx:64,87,106,117`) and are untested for `category` survival. Structurally sound and covered by D-10's reasoning, so no patch is warranted — noted as optional future hardening only.

### 17.3 Adversarial checks that found nothing (recorded so the silence is not mistaken for absence)

- **D-1 verified at the URL level, not just the raw-object level.** The story claims `?category=a&category=b` is dropped wholesale. Unit tests only exercise `v({category:["a","b"]})`, so this pass probed the real parser: `defaultParseSearch("?category=a&category=b")` → `{"category":["a","b"]}` → `validateSearch` → **`{}`**. The duplicate-key URL form genuinely drops rather than silently picking. **The claim holds where it actually matters.**
- **The `Clear filters` change is byte-identical for every URL reachable today.** Probed rather than reasoned: `defaultStringifySearch({category: undefined, status: undefined})` returns **`""`**, so the new `(prev) => ({ category: prev.category })` updater serializes to an empty query string exactly as the old `search: {}` did.
- **No other wholesale search reset survives.** `grep -rn "search: {}" apps/web/src` → **zero hits** repo-wide. All five navigation helpers spread `...prev`. The `to="/catalog"` links in `LandingPage.tsx:42` / `TagGroupsSection.tsx:79` carry no search and are entry points, not scope-loss paths.
- **D-3 confirmed by reading, not only by hunk arithmetic.** `UUID_RE`, the `tag_ids` normalization loop and the ≥2-tag `tag_match` block were read in full at `index.tsx:56-84` and are untouched; the new branch sits cleanly between the `source` and `sort` branches.
- **House style honoured.** The braceless `if (trimmed.length > 0) out.category = trimmed;` matches the file's existing idiom at `index.tsx:67,71,119` — not a lone stylistic outlier.
- **D-2 confirmed as implemented, including its stated cost.** No regex, no allow-list, no lowercasing, no length cap; a 5000-character slug survives validation verbatim (probed). Accepted posture per the wire contract, and harmless: `useModels.buildParams` emits via `URLSearchParams.set` (`useModels.ts:61`), so there is no injection surface, and the backend match is a parameterized exact `==`.
- **Cache-key safety re-confirmed.** `useModels.ts` is byte-unchanged; `category: undefined` is dropped by `hashKey`'s `JSON.stringify`, so no existing user's query key churns. Locked behaviourally by §7.2 case 2.
- **AC-11 is non-vacuous.** The badge test resolves the real trigger by accessible name (`aria-label` → `"Filters"`, `en.json:285`) and pins the text to contain `"1"` before asserting equality, so it cannot pass on two empty strings.
- **D-4 / D-8 / D-9 hold mechanically.** `FilterRibbon.tsx`, `FacetSidebar.tsx`, `en.json`/`pl.json`, `apps/web/tests/**`, `routeTree.gen.ts`, `api-types.ts`, lockfiles, `apps/api/**`, `workers/**`, `infra/**` all show a zero-line diff. Nothing renders `category`; no `useCategories()` call was added.

### 17.4 Acceptance audit — AC-1 … AC-18

All eighteen satisfied, each backed by a named test or a reproduced command result. AC-1/2/3/4/5 → the §7.1 validator block (10 `it`s, all green); AC-6 → the two facet-independence cases plus the D-3 read; AC-7/8 → round-trip and coexistence cases; AC-9…AC-14 → the six §7.2 integration cases; AC-15 → the fence proof re-measured empty by this pass; AC-16 → the gate table in §17.1 (visual green-unchanged accepted on DS evidence, baseline zero-diff independently proven); AC-17 → RED-before-GREEN log ordering as recorded in §14.2; AC-18 → DS's ×3 identical counts, one of which this pass reproduced exactly. **No AC is vacuous, and no AC is satisfied by prose alone.**

### 17.5 Deviation from the skill's default terminal action, and what remains owed

The CR skill's step 4 §6 would set a clean-review story to `done` and sync that to `sprint-status.yaml`. **This pass deliberately did not**, on explicit controller instruction and consistent with §9's gate ownership: `infra/scripts/check-all.sh`, the independent Aider review (`laura-aider-review-diff`), commit, ff-only merge, push, deploy and post-deploy smoke are **all still owed and all controller-owned**. Flipping to `done` now would assert closeout gates that have not run. **Story status stays `review`.**

**Actions NOT taken by this pass:** no production or test file edited, no commit, stage, push, merge, deploy, migration, seed, live-DB or network action; `check-all.sh` not run; Aider/Codex/Gemini not run; `epic-50` not touched (stays `in-progress`).

---

## 18. Controller closeout pre-merge record — 2026-07-28

- **Independent external review:** `laura-aider-review-diff` run on the Story 50.2 diff; verdict **APPROVE**. Critical: none. Important: none. Minor only: the already-documented category-only empty-state handoff to 51.2, pre-existing prettier drift, and optional future hardening for additional `...prev` navigation paths.
- **Full gate:** `infra/scripts/check-all.sh` passed **16/16**, `all green.`, log `.hermes/run-logs/check-all-e50-2-20260728_193636.log`, exit marker `CHECK_ALL_RC=0 2026-07-28T19:47:29+02:00`.
- **Status:** still `review` at this pre-merge checkpoint. Remaining controller closeout: commit, ff-only merge to `main`, push, deploy, post-deploy smoke, then flip Story 50.2 to `done` in a docs closeout commit.


---

## 19. Controller final closeout — 2026-07-28

- **Implementation commit:** `0093187` (`feat(web): add catalog category URL state`), directly on baseline `c436f61`.
- **Merge/push:** branch `feat/E50.2-url-state-category-scope` fast-forward merged to `main`; `git push origin main` succeeded, log `.hermes/run-logs/push-e50-2-20260728_195021.log`, lean pre-push gate **11/11 passed**.
- **Deploy:** `infra/scripts/deploy.sh` succeeded for release `0.1.0+0093187`, log `.hermes/run-logs/deploy-e50-2-20260728_195051.log`, exit marker `DEPLOY_RC=0 2026-07-28T19:54:08+02:00`. Images built and shipped to `.190`; API, arq-worker and web were recreated; alembic ran; slicer-worker overlay correctly skipped because the deploy range was frontend-only; GlitchTip symbolication smoke matched issue id `317` with top frame `apps/web/src/main.tsx` and release `0.1.0+0093187`; smoke issue deleted; runbook fingerprint OK.
- **Post-deploy smoke:** `.190` compose ps showed api, arq-worker, redis, slicer-worker, web and worker all running. LAN API `http://192.168.2.190:8090/api/health` returned `{"status":"ok","version":"0.1.0"}`. LAN web `/`, production HTTPS `/`, and production HTTPS `/catalog/?category=home-decor` all returned HTTP 200 with the freshly deployed `Last-Modified: Tue, 28 Jul 2026 17:52:07 GMT`. Smoke log `.hermes/run-logs/smoke-e50-2-20260728_195424.log`.
- **Final status:** `done`. `epic-50` remains `in-progress`; `50-3-inline-structured-suggestions` remains `backlog`.
