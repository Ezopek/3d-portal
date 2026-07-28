---
baseline_commit: f55bb9f491613b27c0f35b2770afc71d954b1dd9
---

# Story 51.2 — `/categories/$slug` route + scope chip (FR26-BROWSE-2, FR26-BROWSE-3, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1, NFR26-DARKMODE-1)

- **Epic:** E51 — Browse IA: categories as navigation (Initiative 26 — Catalog Discovery).
- **Status:** `done` — implemented 2026-07-29 by native `bmad-dev-story` (**DS**) under a controller-issued `G26-DEVGO`, repaired and fully closed out by the **controller** after the DS run terminated on `error_max_turns` mid-hygiene (§15). Created and validated 2026-07-29 by native `bmad-create-story` (Create **CS** → Validate **VS**), verdict **PASS** (§13). Shipped by Laura/controller: commit `50446371e94fde774b08d6b22fa6a2ae07676809`, ff-only merge to `main`, push to `origin/main`, deploy `DEPLOY_RC=0`, post-deploy smoke OK (§15.7).
- **Author:** Claude (native `bmad-create-story`, Create + Validate; native `bmad-dev-story`, implementation). **Closeout repair + gates:** Laura/controller. **Controller:** Laura.
- **Authorization posture, stated plainly:** this create + validate pass was delegated by **Laura/controller under the standing Initiative 26 authorization**. It is **NOT** an Ezop signature, **NOT** Ezop review, and **NOT** human review of any kind. No human reviewed this artifact. No Codex, no Gemini, no Aider participated. **No `G26-DEVGO` is recorded by this pass** — dev start on this story remains a separate controller act. No app code was written, no gate/test/build/script was run, no branch was created, and no commit / stage / push / merge / deploy / migration / seed / live-DB / network action was taken. This pass edited exactly two files: this artifact and `sprint-status.yaml`.
- **Created:** 2026-07-29 via native `bmad-create-story` after a mandatory `bmad-help` run. Canonical route from `_bmad/_config/bmad-help.csv:26-29`: `bmad-code-review` (**CR**, `:29` — *"if approved then next CS"*) → `bmad-create-story:create` (**CS**, phase `4-implementation`, `preceded-by bmad-sprint-planning` — done, `required=true`) → `bmad-create-story:validate` (**VS**, `:27`) → `bmad-dev-story` (**DS**, `:28`).
- **Duplicate check:** `ls _bmad-output/implementation-artifacts/ | grep -E '^51'` returned only `51-1-desktop-browse-navigation.md`; no `spec-*` artifact matched `51-2`, `categories-route` or `scope-chip`. No pre-existing story or spec duplicate existed before this pass.
- **Sprint-status readback:** `sprint-status.yaml` read start-to-end. `epic-51: in-progress` (flipped at 51.1 create-story); `51-1-desktop-browse-navigation: done`; `51-2-categories-route-and-scope-chip: backlog` is the **first** `backlog` story key under `epic-51` and the canonical next story. (`42-3`, `42-5`, `47-4` remain `backlog` under epics already closed `done` by recorded operator/controller scope decisions — deferred, not next.) `epic-51` is already `in-progress`, so no epic flip is owed by this story.
- **Scope class:** **frontend-only, user-visible navigation cutover.** One **new file route** (`routeTree` regeneration required), one new presentational component, a props-cutover on the shipped `CatalogList`, one `Link` conversion inside the shipped `BrowseRail`, one additive optional prop on the shared `EmptyState`, one predicate widening in the shell `ModuleRail`. **No** backend change, **no** new endpoint, **no** migration, **no** new dependency, **no** infra change.
- **Sources of truth:** `epics.md` §E51 Story 51.2 (`:4531-4533`); `prd.md` FR26-BROWSE-2 (`:2251`), FR26-BROWSE-3 (`:2252`), NFR26 block (`:2262-2270`); `architecture.md` § Initiative 26 Decision AY (`:3303-3345`); UX artifact `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` — `DESIGN.md` (`:84-95` scope-chip tokens, `:203-204` colour roles, `:216-217` contrast, `:244` geometry, `:256-258` radius, `:273-274` + `:282` component specs, `:293-296` do/don't), `EXPERIENCE.md` (`:37-44` scope-vs-facet table, `:50-54` surface map, `:219-222` interaction table, `:245-247` + `:258` states, `:268` targets, `:278` tab order, `:314-316` announcements, `:324` focus, `:328-335` responsive, `:342-362` URL state, `:364-387` transition table, `:399` component ownership, `:450-454` journey); shipped code at `main` @ `f55bb9f`; in-repo predecessors `50-1-fe-types-and-hooks.md`, `50-2-url-state-category-scope.md`, `50-3-inline-structured-suggestions.md`, `51-1-desktop-browse-navigation.md` (all `done`); `deferred-work.md:190-197`; `sprint-status.yaml` `action_items` epic-51 handoffs.

---

## 1. Story statement

**As** a catalog user who has picked a browse category,
**I want** that category to be a real place with its own URL (`/categories/{slug}`), shown as a **scope chip above the results** with a one-click escape back to the whole catalogue —
**so that** "where am I browsing" is visible, linkable and shareable, and widening my search never silently throws away the query and filters I already chose.

**FR mapping — FR26-BROWSE-2** (`prd.md:2251`), quoted: *"The active category renders as a **scope** above the results (chip), never as another checkbox, and is **excluded** from the `Filters (n)` count. Public MVP allows exactly **one** active category scope at a time… Canonical URL `/categories/{stable-slug}`; `q`, `tag_ids`, `tag_match`, `sort` remain query params and independent visible URL state layers. A search started inside a category stays scoped by default, with a visible category chip and a one-click **"Search entire catalog"** escape."*
Verifiable, quoted: **(a)** *"the `Filters (n)` badge does not change when a category is active"*; **(b)** *"the escape control clears only the scope."*

**FR26-BROWSE-3** (`prd.md:2252`) rides along as a non-regression obligation: OR-within-group / AND-between-groups and `tag_match` are untouched, and **category scope is never mixed into `tag_match`**. Verifiable: *"the shipped Story 42.1 semantics tests pass unmodified with a category scope applied."*

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `f55bb9f`

> `prd.md:2302` makes every `VERIFY-AT-CREATE-STORY` marker a mandatory fresh repo-wide trace at story-creation time (standing `epic:47` stale-precondition action item, `status: open`). `EXPERIENCE.md:397` repeats it for the component-ownership table. Everything below was re-read at source in this run at `main` @ `f55bb9f` (clean tree, `HEAD == origin/main`). Nothing is carried from the epic sketch or from the UX artifact's file anchors.

### 2.1 The route surface as it exists today

| Fact | Evidence |
|---|---|
| Router | `@tanstack/react-router` **1.169.2** installed (`package.json` declares `^1.84.0`); file-based routing via `TanStackRouterVite({ routesDirectory: "src/routes", routeFileIgnorePattern: "\\.js$" })` (`vite.config.ts:27`) |
| `routeTree.gen.ts` | **tracked in git** (`git ls-files src/routeTree.gen.ts` → hit), header says *"automatically generated … You should NOT make any changes"*; carries `/* eslint-disable */` + `// @ts-nocheck` |
| Regeneration mechanism | The **vite plugin** regenerates it on `npm run dev` and on `npm run build`. There is **no** standalone `generate-routes` npm script (`package.json` scripts: `dev`, `build`, `typecheck`, `preview`, `test`, `test:watch`, `test:visual`, `design-sync*`, `lint`, `format`, `prepare`). So the regeneration step for this story is **run `npm run build` (or `npm run dev`) and commit the resulting `routeTree.gen.ts` diff** — never hand-edit it |
| Existing catalog routes | `src/routes/catalog/index.tsx` (`/catalog/`) and `src/routes/catalog/$id.tsx` (`/catalog/$id`). There is **no** `src/routes/categories/` directory — this story creates it |
| Param naming precedent | `$id` (`routes/catalog/$id.tsx`), `$token` (`routes/share/$token.tsx`). The epic and the UX artifact both name the new param **`$slug`** — adopted |
| SPA fallback | `apps/web/nginx.conf:40-41` — `location / { try_files $uri /index.html; }`. A new top-level `/categories/...` path is served by the SPA fallback with **no infra change**. `location /api/` (`:63`) is a longer-prefix match and is unaffected; the browser path `/categories/x` and the API path `/api/categories/x` never collide |
| Non-route files inside `src/routes/` | `routes/share/MemberShareView.tsx`, `routes/catalog/index.test.ts` etc. exist and do **not** appear in `routeTree.gen.ts` — the plugin only picks up files exporting `createFileRoute`. A colocated test file next to the new route is therefore safe |

### 2.2 `routes/catalog/index.tsx` — the shipped 50.2 URL layer

- `CatalogSearch` (`:36-50`) already carries `category?: string` (`:46`) with the comment *"The scope chip and the 'Search entire catalog' escape are Story 51.2."*
- `validateSearch` (`:54-122`) — the `category` branch is `:105-108`: `typeof raw.category === "string"` → trim → drop-if-empty → **single slug**, array dropped wholesale. Its comment block (`:95-104`) records why there is no format check (wire type is bare `str | None`; unknown slug returns 200 + empty page) and why trim/drop-if-empty is load-bearing (`category=""` would blank the catalog).
- The 43.3 canonical-UUID hardening for `tag_ids` (`:34`, `:57-72`) and the `tag_match` ≥2-tag normalisation (`:78-85`) are **untouched by this story**.
- Route options today are exactly `{ component: CatalogList, validateSearch }` — **no** `beforeLoad`, **no** loader.

### 2.3 `CatalogList.tsx` — the component both routes must share (379 lines)

| Fact | Evidence |
|---|---|
| Router binding is **hard-coded** | `useSearch({ from: "/catalog/" })` (`:30`), `useNavigate({ from: "/catalog/" })` (`:31`). This is the single blocker to reusing the component under a second route, and §4 D-2 resolves it |
| Navigators | `setFilters` (`:69-90`), `toggleTag` (`:92-109`), `toggleUntagged` (`:111-120`), `setCategory` (`:127-136`), `setPage` (`:138-146`) — **all** `replace: true` |
| `setCategory` | Writes `?category=<slug>` on `/catalog` (`:127-136`). This is precisely the seam 51.1 D-3 recorded as *"exactly the seam 51.2 will re-point"* |
| Fatal guards | error `:159-174` (`tagGroups.isError || models.isError`), loading `:175-177` (`tagGroups.data === undefined || models.data === undefined`). `categories` is deliberately in **neither** (`:36-40`, 51.1 D-8/D-9) |
| `filtersActive` | `:186-191` — `tag_ids.length > 0 || status !== undefined || source !== undefined || q.length > 0 || untagged === true`. **Exactly** the predicate the chip's action-label rule needs (§4 D-6) |
| `andTooNarrow` | `:199-202` — `total === 0 && tag_ids.length >= 2 && (tag_match ?? "all") === "all"` |
| Empty-state branch order | `andTooNarrow` (`:280-308`) → page-overshoot `total > 0` (`:309-321`) → generic (`:322-344`). New scoped branches must slot **after** page-overshoot, which is what `EXPERIENCE.md:247` means by *"this branch is checked before the generic scoped-empty branch"* |
| `Clear filters` handlers | Two of them (`:296-307`, `:325-343`), both `search: (prev) => ({ category: prev.category })` with a comment naming 51.2 as the story that owns scope clearing |
| Layout | Outer `<div className="flex">` (`:205`) → `<BrowseRail/>` (`:212-219`) + `<div className="min-w-0 flex-1">` (`:220`) containing the Tags-sheet row (`:229-257`), the FilterRibbon/AddModel toolbar row (`:271-278`), then the grid/empty branch. **There is no results heading and no live region** — confirming 51.1 D-7's premise is still true |
| No `<h1>`/`<h2>` anywhere in the file | `grep` for heading tags returns nothing — the focus target `EXPERIENCE.md:324` requires does not exist yet |

### 2.4 `BrowseRail.tsx` — shipped by 51.1, 135 lines

- Props (`:15-24`): `categories`, `activeSlug`, `onSelect(slug|undefined)`, `isLoading`, `isError`, `onRetry`.
- Rows are `<button type="button">` with `aria-current="page"` on exactly one row (`:61-68`, `:79-103`) and `aria-label` from `catalog.browse.categoryWithCount` (`:85-88`).
- Class strings, module-local: `ROW_BASE` (`:32`), `ROW_ACTIVE` (`:33`, copied verbatim from `ModuleRail.tsx:34`), `ROW_IDLE` (`:34`). `SKELETON_ROW_COUNT = 6` (`:13`), unexported so the file's only export stays the component.
- Label fallback `preferPl && item.name_pl ? item.name_pl : item.name_en` (`:49-50`).
- **The `<button>`-vs-`Link` divergence is a live, recorded open item**: `sprint-status.yaml` `action_items` epic-51 *"REVIEW-VISIBLE DIVERGENCE from 51.1 … Recommended adjudication: revisit in 51.2, which introduces /categories/$slug"* (`status: open`), and 51.1 §17 `DF-1`/`DF-2`. §4 D-4/D-5 discharge both.

### 2.5 `ModuleRail.tsx` — the shell integration this route breaks

`ModuleRail.tsx:26` and `:49` both compute `const active = pathname.startsWith(to)` against `MODULES` (`:8-14`), where the catalog entry is `{ key: "catalog", to: "/catalog", … }`.

**Therefore, at `/categories/uchwyty` no module row is active** — the desktop rail and the mobile bottom bar both go dark on the canonical browse URL this story introduces. That is a visible "where am I" regression **caused by this story**, on both viewports. §4 D-8 resolves it with the minimum possible change.

### 2.6 The data layer this story consumes

| Artifact | Path | State |
|---|---|---|
| `useCategories()` | `hooks/useCategories.ts:13-19` — `useQuery<BrowseCategoryRead[]>`, key `["sot","categories"]`, `staleTime: 5*60*1000` | Shipped 50.1; **already mounted unconditionally** by `CatalogList.tsx:40` at every viewport (the rail is desktop-only, the query is not) |
| `useCategoryBySlug()` | `hooks/useCategoryBySlug.ts:13-19` — key `["sot","categories",slug]`, `queryFn: api(`/categories/${slug}`)` | Shipped 50.1, **still zero callers**. §4 D-7 decides *not* to mount it and re-routes the two ledger entries rather than silently closing them |
| `useModels({category})` | `useModels.ts:18` + `buildParams` `:61` — `p.set("category", f.category)` on a `URLSearchParams` (`:42-43`) | Shipped 50.2. Encoding is handled by `URLSearchParams`, so a slug containing `#`, `?` or `/` reaches the backend intact on **this** path |
| `BrowseCategoryRead` | `lib/api-types.ts:116-120` → `{id, slug, name_en, name_pl, position, parent_id, description_en, description_pl, model_count}` | `model_count` required and unconditional |
| Backend contract | `architecture.md:3308-3311` — `GET /api/categories` flat, ordered `(position, slug)`, **empty categories returned**; `GET /api/models?category=<slug>` with an **unknown slug yielding an empty page with `total = 0`, not a 404** | Shipped 49.3 |

### 2.7 Shared UI + i18n inventory

- `EmptyState` (`ui/custom/EmptyState.tsx:7-13`) — props `messageKey`, `icon`, `action`, `secondaryAction`, `tone`. **It renders `t(messageKey)` with no interpolation params** (`:24`), and `secondaryAction` only renders when `action` is also present (`:25-36`). `"No matches in {Category}"` therefore needs one additive optional prop (§4 D-9).
- `en.json` / `pl.json` carry **913 keys each** today (906 before 51.1's seven). Reusable, already shipped: `catalog.empty`, `catalog.emptyPage`, `catalog.actions.clear_filters`, `catalog.actions.switch_to_or`, `catalog.actions.back_to_page_1`, `catalog.totalSuffix` (`total` / `łącznie`), `catalog.browse.allCatalog` (`All catalog` / `Cały katalog`), `catalog.browse.railLabel`, `errors.network`, `common.retry`.
- Terminology is **fixed by `EXPERIENCE.md:203`**: `"Szukaj w całym katalogu"` / `"Search entire catalog"`. The artifact explicitly rejects `"Wyczyść"` / `"Clear"` for that control *"— it does not clear the query, and saying so would be a lie."*

### 2.8 Test surfaces that this story's change makes false

| Surface | Coupling | Consequence |
|---|---|---|
| `CatalogList.test.tsx:163-183` (`mountAt`) | Builds a memory router with a single route whose `path: "/catalog/"` exists *"under a route whose id matches its hard-coded `useSearch/useNavigate({ from: "/catalog/" })`"* | The comment and the harness both become false under D-2. The harness must mount **both** routes so the cross-route assertions in §7.2 are reachable |
| `CatalogList.test.tsx` category tests (added by 51.1 T6) | Assert `?category=<slug>` is written on `/catalog` | **Break by design** — must be re-pointed at path navigation (§7.2) |
| `browse-rail.spec.ts:36-40` and throughout | Queries rail rows with `getByRole("button", …)` | **Breaks under D-4** — a `Link` renders an `<a>` with role `link`. Must be repaired, not re-baselined (§7.5) |
| `BrowseRail.test.tsx` (16 tests) | Renders the component bare, asserts `onSelect` payloads | Needs a router wrapper and `href` assertions instead of callback payloads (§7.1) |
| `routes/catalog/index.test.ts` | Validator unit tests incl. the 50.2 `category` branch | **Must stay green unmodified** — this story does not touch `validateSearch` (§4 D-3) |
| `tests/visual/api-stubs.ts:162-227` | `stubSotList` already stubs `**/api/categories*` with `DEFAULT_BROWSE_CATEGORIES` (slugs `organizery` 12, `uchwyty` 7, `dekoracje` 0) and `**/api/models*` | **Reusable as-is** for the new route's visual coverage — no new stub is needed |

---

## 3. Additive scope — the implementable-green target

### 3.1 NEW — `apps/web/src/routes/categories/$slug.tsx`

```tsx
export const Route = createFileRoute("/categories/$slug")({
  component: CategoryBrowseRoute,
  validateSearch: (raw: Record<string, unknown>): CatalogSearch => {
    // Scope lives in the PATH on this route. Re-use the shipped catalog
    // validator verbatim, then drop `category` so a hand-crafted
    // /categories/a?category=b can never express two scopes at once.
    const { category: _scopeIsInThePath, ...rest } = validateCatalogSearch(raw);
    return rest;
  },
});
```

`validateCatalogSearch` is the **existing** `validateSearch` function from `routes/catalog/index.tsx`, extracted to a named `export` in that same file (definition site unchanged, no new module, no import ripple — `CatalogSearch` and `TagMatch` keep their current export site, so `CatalogList.tsx:13` and every other consumer is untouched).

`CategoryBrowseRoute` is a module-local, unexported component:

```tsx
function CategoryBrowseRoute() {
  const { slug } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <CatalogList
      scopeSlug={slug}
      search={search}
      onSearchChange={(updater) => void navigate({ search: updater, replace: true })}
    />
  );
}
```

### 3.2 UPDATE — `apps/web/src/routes/catalog/index.tsx`

1. `export` the validator as a named function `validateCatalogSearch` and pass it as `validateSearch` (same function, now reusable). **No change to any validation rule.**
2. Add `beforeLoad` canonicalisation:
   ```ts
   beforeLoad: ({ search }) => {
     if (search.category !== undefined) {
       throw redirect({
         to: "/categories/$slug",
         params: { slug: search.category },
         search: { ...search, category: undefined },
         replace: true,
       });
     }
   },
   ```
3. Replace `component: CatalogList` with a module-local `CatalogListRoute` that supplies the three props (`scopeSlug: undefined`, `search`, `onSearchChange`), mirroring §3.1.

### 3.3 UPDATE — `apps/web/src/modules/catalog/routes/CatalogList.tsx`

1. **Props cutover** — the component stops binding itself to one route:
   ```ts
   interface Props {
     /** Path-borne browse scope. `undefined` on /catalog — the unscoped catalogue. */
     scopeSlug: string | undefined;
     search: CatalogSearch;
     /** Route-bound search updater. Always replace:true — the shipped behaviour. */
     onSearchChange: (updater: (prev: CatalogSearch) => CatalogSearch) => void;
   }
   ```
   Delete `useSearch({from})` / `useNavigate({from})` (`:30-31`) and `setCategory` (`:122-136`). Re-point `setFilters`, `toggleTag`, `toggleUntagged`, `setPage`, `Switch to OR` and both `Clear filters` handlers at `onSearchChange(...)` — **each keeps its exact existing updater body**, minus the now-dead `category: prev.category` preservation, which becomes `() => ({})` (scope survives in the path, or does not exist).
2. `useModels({ …, category: scopeSlug })` — the scope now comes from the path, not from `search.category`.
3. `<BrowseRail categories={…} activeSlug={scopeSlug} isLoading isError onRetry />` — the `onSelect` prop is gone (D-4).
4. Insert `<ScopeChip/>` as a full-width row **between the toolbar row (`:271-278`) and the grid/empty branch**, rendered only when `scopeSlug !== undefined`.
5. Insert the results heading and the live region at the top of the results region (D-10, D-11).

### 3.4 NEW — `apps/web/src/modules/catalog/components/ScopeChip.tsx`

Single export (`react-refresh/only-export-components` under `--max-warnings=0`).

```ts
interface Props {
  /** Resolved category label, or the raw slug when the slug is unknown. */
  label: string;
  /** True when q / tag_ids / untagged / status / source is active. */
  otherConstraintsActive: boolean;
}
```

Geometry and tokens, verbatim from `DESIGN.md:84-95`, `:244`, `:256-258`, `:273-274`:
- Full-width row above the grid (`DESIGN.md:244`: *"The scope chip inserts one full-width row between the toolbar and the grid; nothing else moves"*), **flat** — `border`-separated, never a shadow (`:250`).
- `bg-primary/10`, `ring-1 ring-inset ring-primary`, `rounded-md`, `min-h-6`, `text-foreground`.
- **`rounded-md`, deliberately not `rounded-full`** — the tag pill is `rounded-full`; the shape contrast is a free reinforcement of place-vs-constraint (`DESIGN.md:258`).
- Trailing action is a **text label, never a bare `×`** (`DESIGN.md:274`, `:296`), `min-h-6 min-w-6`, underline on hover/focus, rendered as a TanStack `Link` (D-5).
- Colour role: `primary` @10% = *location* (`DESIGN.md:203`). **Never** `accent`, which is the chosen-constraint vocabulary (`:204`, `:294`).

### 3.5 UPDATE — `apps/web/src/modules/catalog/components/BrowseRail.tsx`

Rows become `Link`s (D-4). `onSelect` is removed from `Props`; every other prop, both class strings, `aria-current`, the `aria-label`/count contract, the dimmed zero-count treatment, the skeleton and the error block are **unchanged**.

- "All catalog": `<Link to="/catalog" search={(prev) => ({ ...prev, page: undefined })}>`
- Category row: `<Link to="/categories/$slug" params={{ slug: c.slug }} search={(prev) => ({ ...prev, page: undefined })}>`

`ROW_BASE`/`ROW_ACTIVE`/`ROW_IDLE` are applied to the anchor unchanged, so the rendered box is pixel-identical (D-4 states the one residual risk and how to treat it).

### 3.6 UPDATE — `apps/web/src/ui/custom/EmptyState.tsx`

One additive optional prop: `messageParams?: Record<string, string | number>`, used as `t(messageKey, messageParams)`. Every existing caller is unaffected (D-9).

### 3.7 UPDATE — `apps/web/src/shell/ModuleRail.tsx`

The catalog module's active predicate widens to cover the browse route it now owns (D-8). One entry gains an explicit extra prefix; the `MODULES` array shape, the tab set, the icons, the labels, the desktop geometry and the mobile bottom bar are otherwise **unchanged**.

### 3.8 UPDATE — `apps/web/src/locales/en.json` + `pl.json`

Five new keys, both files, identical key set (flat-key convention; 913 → 918 keys each):

| Key | `en` | `pl` |
|---|---|---|
| `catalog.browse.searchEntireCatalog` | `Search entire catalog` | `Szukaj w całym katalogu` |
| `catalog.browse.clearCategory` | `Clear category` | `Wyczyść kategorię` |
| `catalog.browse.activeScope` | `Active category: {{name}}` | `Aktywna kategoria: {{name}}` |
| `catalog.emptyCategory` | `Nothing in this category yet.` | `W tej kategorii nie ma jeszcze nic.` |
| `catalog.emptyInCategory` | `No matches in {{name}}.` | `Brak wyników w kategorii {{name}}.` |

`catalog.browse.searchEntireCatalog` is **quoted from `EXPERIENCE.md:203`** and must not be softened to `Wyczyść`/`Clear`. `catalog.browse.activeScope` supplies the chip row's accessible name. **Reuse, do not re-add:** `catalog.browse.allCatalog`, `catalog.totalSuffix`, `catalog.actions.clear_filters`, `catalog.actions.switch_to_or`, `catalog.empty`, `catalog.emptyPage`.

### 3.9 UPDATE — `apps/web/src/routeTree.gen.ts`

Regenerated by the vite plugin (§2.1), **never hand-edited**. Expected diff: one new `CategoriesSlugRoute` import + registration + the union-type entries for `/categories/$slug`. `*.gen.ts` is lint-ignored and `@ts-nocheck`'d, so it is a mechanical, reviewable artifact — it must be **committed** with the story.

---

## 4. Resolved decisions — each with its cost stated

**D-1 — Scope lives in the path, and only in the path.**
`EXPERIENCE.md:362` and `prd.md:2251` both put `category` in the path; `q`/`tag_ids`/`tag_match`/`untagged`/`status`/`source`/`sort`/`page` stay query params. After this story **nothing in the app writes `?category=`**. Two URLs expressing one state is the failure mode this decision exists to prevent — the chip, the rail's active row and the `useModels` call all read **one** source: the route param.

**D-2 — `CatalogList` becomes props-driven; each route owns its own router binding.**
The component is hard-bound to `/catalog/` (`:30-31`). Three ways out were considered:
- *`useSearch({ strict: false })` inside the shared component* — the installed 1.169.2 typings do support `StrictOrFrom`, but the non-strict result is the **union across every registered route**, so `search.q` would typecheck only by accident and would silently widen if an unrelated route changed. Rejected: it makes a shared component's types depend on the whole route tree.
- *Duplicate `CatalogList` for the new route* — rejected outright; that is the "reinvent the wheel" failure, and the two surfaces must stay pixel- and behaviour-identical apart from the chip.
- **Chosen:** each route file resolves `search`/`params`/`navigate` through its own `Route.useSearch()` / `Route.useParams()` / `Route.useNavigate()` and passes three props down. Typing is exact at both call sites, and `CatalogList` becomes route-agnostic.
*Cost:* ~10 mechanical call-site edits inside a file that shipped yesterday, plus a harness change in `CatalogList.test.tsx` (§7.2). *Benefit:* zero `any`, zero cast, zero route-tree coupling in a module component.

**D-3 — `validateSearch` is re-used, not re-authored; `routes/catalog/index.tsx`'s validation rules are byte-unchanged.**
The new route imports the shipped validator and strips `category` from its result (§3.1). The 43.3 canonical-UUID `tag_ids` hardening, the `tag_match` ≥2-tag normalisation and the 50.2 `category` trim/drop rules are **not touched**, so `routes/catalog/index.test.ts` must pass **unmodified** — that is the falsifiable form of this decision.
*Why strip rather than share as-is:* `/categories/a?category=b` would otherwise express two scopes. Stripping makes the impossible state unrepresentable instead of merely unlikely.

**D-4 — Rail rows become `Link`s. This discharges the open 51.1 divergence.**
`EXPERIENCE.md:219` (*"Each row is a `Link`"*), 51.1 `DF-1`, and the `sprint-status.yaml` epic-51 action item (*"Recommended adjudication: revisit in 51.2, which introduces `/categories/$slug`"*) all point here, and the reason 51.1 deferred it — the target route did not exist — is now gone. Anchors give middle-click, copy-link-address and the browser's own hover URL for free, which is exactly what a *navigation* surface owes.
*Cost:* `BrowseRail.test.tsx` needs a router wrapper (§7.1) and `browse-rail.spec.ts`'s `getByRole("button")` queries become `getByRole("link")` (§7.5). *Residual risk, named:* an `<a>` may pick up UA defaults the `<button>` did not. `ROW_BASE`/`ROW_ACTIVE`/`ROW_IDLE` set colour explicitly and there is no global `a` rule in `src/styles/*.css`, so the box is expected pixel-identical — **but any rail baseline movement is a `deterministic-fail` to root-cause, not a stale baseline to regenerate** (§7.6).

**D-5 — Scope changes **push**; every other navigation stays `replace: true`.**
`EXPERIENCE.md:387` says all navigations replace *"Selecting a category is the one exception: it is a genuine navigation and pushes, so browser Back returns to the previous category."* Read literally, that leaves the chip's escape ambiguous — it is not "selecting a category", yet it *is* a scope change and a route change. The rule adopted here, stated once so it is checkable: **a change of the route (scope) pushes; a change of search params only, replaces.** Both rail rows (including "All catalog") and the chip escape are route changes, so all three push; filters, sort, tags, pagination and the empty-state recoveries all keep the shipped `replace: true`.
*Cost:* one line of divergence from the spine's literal sentence, recorded rather than hidden. *Benefit:* Back is symmetric — it returns from an escape to the category you escaped, and there is no surface where the same logical transition pushes from one control and replaces from another. This also closes 51.1 `DF-2` (*"`setCategory` uses `replace: true` … browse-route history should be revisited when 51.2 adds canonical category routes"*).

**D-6 — The chip carries one action with two labels, selected by the shipped `filtersActive` predicate.**
`EXPERIENCE.md:222`: *"one trailing action whose label depends on state: **"Search entire catalog"** when `q` or any tag/status/source is active, **"Clear category"** when the scope is the only constraint."* The transition table (`:376`) gives both rows the **same** effect — scope cleared, everything else preserved, `page` reset — so this is **one navigation with two labels**, not two behaviours. The predicate is `CatalogList.tsx:186-191`'s existing `filtersActive`, reused verbatim; `untagged` is included because it is a tag-family constraint and the shipped predicate already counts it. `sort` is **not** a constraint for this purpose (it is not listed at `EXPERIENCE.md:222`) and is preserved by both labels regardless.

**D-7 — `useCategoryBySlug` is NOT mounted; the chip label comes from the already-loaded `useCategories()` list.**
`EXPERIENCE.md:258`: an unknown slug must render *"Empty page with `total = 0`, **not** a 404 … The chip renders the raw slug and the escape action stays available."* `useCategoryBySlug` is specified to **404 on an unknown slug** (`architecture.md:3310`), so mounting it on this route would introduce an error surface the UX contract forbids. The category list is already fetched unconditionally by `CatalogList.tsx:40` at every viewport, is flat and complete (empty categories included, `architecture.md:3309`), and resolves the label with **zero** extra requests: `categories.data?.find(c => c.slug === scopeSlug)`, falling back to the raw `scopeSlug`. That fallback simultaneously covers unknown slugs, a pending list and a failed list — one code path, three states.
*Cost, stated:* the two `deferred-work.md:190-197` entries (missing `encodeURIComponent`; `useCategoryBySlug("")` following the `307` to the list endpoint) were ledgered *"until Story 51.2 mounts the first caller"*, and this story does not mount one. They are **re-routed, not closed** — see §12.

**D-8 — `ModuleRail`'s catalog predicate widens to `/categories`.**
§2.5 proves that without this, **no module row is active** on `/categories/{slug}` on desktop *and* mobile — a "where am I" regression introduced by this story's own route. The minimum fix is to make the catalog module's active predicate also match the `/categories` prefix.
*Boundary check, explicit:* Story 51.3's `Ask First` (and 48.1's before it) is about **changing the mobile `ModuleRail` navigation structure** — adding a sixth tab (`EXPERIENCE.md:335`). This adds **no tab**, removes none, renames none and moves nothing; it only teaches the existing catalog tab that the browse route belongs to it. That is inside this story's blast radius, not across the `Ask First` line. Recorded as reversible in §13.2 if the controller reads it otherwise.

**D-9 — `EmptyState` gains one optional `messageParams` prop rather than a bespoke empty state.**
`"No matches in {Category}."` needs interpolation; `EmptyState` renders `t(messageKey)` with none (`:24`). Adding an optional param bag is ~2 lines and leaves all existing callers byte-identical in behaviour. The rejected alternative — a second, near-duplicate empty-state component inside the catalog module — is the wheel-reinvention this checklist exists to prevent.

**D-10 — The results heading is `sr-only`, focusable, and is the focus target on scope change.**
`EXPERIENCE.md:324`: *"Navigating to a category moves focus to the results heading, not to the top of the document."* 51.1 D-7 deferred this here explicitly because no heading existed. It renders as `<h2 className="sr-only" tabIndex={-1}>` whose text is the active category label, or `catalog.browse.allCatalog` when unscoped — **no new i18n key**, and **no pixel change**, so it cannot move a baseline. Focus moves to it on a scope change only (not on filter/sort/page changes, which do not relocate the user).

**D-11 — One polite live region, owned by the results area, keyed on `total`.**
`EXPERIENCE.md:314-316`: *"Result count changes announce via a polite live region on scope change, filter change and query commit — **one region, not one per control**. … The scope chip is not a live region; the result count is."* A single `role="status" aria-live="polite"` `sr-only` node rendering `{total} {t("catalog.totalSuffix")}` satisfies all three triggers at once, because every one of them changes `total`. Building it per-trigger would violate the "one region" rule and would spill into 50.3's and 52.1's surfaces. Reuses the shipped `catalog.totalSuffix` key.

**D-12 — `/catalog?category=<slug>` is canonicalised by a redirect, not tolerated as a second source of truth.**
Legacy `?category=` URLs exist in the wild: 51.1 shipped that writer and the 51.1 deploy smoke itself hit `https://3d.ezop.ddns.net/catalog/?category=uchwyty` (51.1 §19). A `beforeLoad` redirect (§3.2) preserves every other search param, uses `replace: true` so the legacy URL does not linger in history, and cannot loop (the target route's schema has no `category`, so the redirect condition is false at the destination). This is what makes "canonical URL" (`prd.md:2251`) true rather than aspirational, and it keeps the 50.2 `category` validator branch load-bearing — it is now the parser for inbound legacy URLs.
*Cost:* one `beforeLoad` on a shipped route. *Rejected alternative — accept both URLs:* leaves `CatalogList` reading scope from two places forever, and every future story must remember which.

**D-13 — Category scope stays out of `Filters (n)` and out of `tag_match`, and this story adds no counting logic.**
`FilterRibbon.activeFilterCount()` (`FilterRibbon.tsx:53-59`) counts status + source + non-default sort and has no notion of `category`. It is **not touched**. FR26-BROWSE-2's verifiable (a) — *"the `Filters (n)` badge does not change when a category is active"* — is therefore proven by a test that asserts the badge across a scope change, not by new code (AC-19). Likewise `tag_match` (FR26-BROWSE-3): the scope never enters it.

---

## 5. Cache-coherence enumeration (mandatory — `project-context.md:286`)

| Dimension | `useCategories()` (`["sot","categories"]`) | `useModels(...)` (`["sot","models",…filters]`) |
|---|---|---|
| **Staleness budget** | `staleTime: 5 * 60 * 1000`, shipped and justified at `useCategories.ts:6-12` against the contract it serves (admin-governed reference data). **Unchanged by this story**, and must stay pointed at that contract rather than at a neighbouring number (`project-context.md:287`). This story adds a *second* reader of the same key (the chip label, D-7) at the same staleness — it does not add a second budget. | `category` moves from `search.category` to the path-borne `scopeSlug`; the **key content is identical** (same slug value in the same filter slot), so no cache entry is orphaned and a `/catalog?category=x` → `/categories/x` redirect (D-12) lands on the **same** cached models entry. |
| **Retry policy** | TanStack Query default; the rail's inline retry (`categories.refetch()`, 51.1 D-8) is unchanged and is still the only recovery. The chip does **not** add a retry — a missing label degrades to the raw slug (D-7), which is a rendered value, not an error. | Unchanged; the shipped `EmptyState` retry (`CatalogList.tsx:159-174`) keeps its three refetches. |
| **Cache propagation (mutations)** | None. This story is read-only; no member surface mutates a category. Admin writes (52.2) will invalidate the `["sot","categories"]` prefix, refreshing rail **and** chip label together — a property the prefix key already guarantees. | n/a |
| **Cache eviction on route exit** | None, and none wanted — reference data cached across `/catalog` ↔ `/categories/{slug}` navigations is the point, and it is what makes a scope change feel instant. No token-scoped variant exists (authenticated default-deny), so there is no Story 30.2-class contamination risk (`project-context.md:286`). | Unchanged. |
| **Cache seeding on this route** | The new route mounts the **same** `useCategories()` call through the shared `CatalogList`, so `/categories/{slug}` is served from the entry `/catalog` already seeded — a rail→category navigation issues **no** new category request. `useCategoryBySlug`'s sibling key stays unseeded and unused (D-7). | Seeded per filter combination as shipped. |

**Conflict check:** none. The chip and the rail read the **same** key with the same staleness and the same failure treatment, which is why the label and the active row can never disagree. No column disagrees, so no additional design choice needs naming.

---

## 6. Acceptance criteria

**Route**

- **AC-1** — `/categories/{slug}` is a real file route (`src/routes/categories/$slug.tsx`) rendering the catalog surface scoped to `{slug}`; `routeTree.gen.ts` is **regenerated by the vite plugin** and committed, with no hand edits.
- **AC-2** — The new route's `validateSearch` re-uses the shipped catalog validator and **drops** `category`, so `/categories/a?category=b` renders scope `a` and carries no `category` param.
- **AC-3** — `routes/catalog/index.tsx`'s validation **rules** are unchanged: `routes/catalog/index.test.ts` passes **unmodified**.
- **AC-4** — `/catalog?category=<slug>` redirects (`replace`) to `/categories/<slug>` preserving `q`, `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `sort`; `/catalog` with no `category` does not redirect.
- **AC-5** — An unknown slug renders an empty grid with `total = 0` — **never** a 404, never an error surface — with the chip and its escape action present (D-7).

**Scope chip**

- **AC-6** — When a scope is active, a **full-width chip row** renders between the toolbar and the grid, carrying the category label; it renders on **every** viewport, including when the grid is empty.
- **AC-7** — No chip renders on `/catalog` (no scope active) — the row is absent from the DOM, not merely hidden.
- **AC-8** — The chip is **not** a checkbox and exposes no toggle, no multi-select and no bare `×`; its single action is a **text-labelled** control (`DESIGN.md:274`, `:296`).
- **AC-9** — The action label is `catalog.browse.searchEntireCatalog` when `filtersActive` is true and `catalog.browse.clearCategory` when it is false (D-6).
- **AC-10** — Activating the action navigates to `/catalog` clearing **only** the scope: `q`, `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `sort` are all preserved and `page` resets (FR26-BROWSE-2 verifiable (b)).
- **AC-11** — For an unknown slug the chip renders the **raw slug** as its label and the action still works (D-7).
- **AC-12** — Chip styling is `bg-primary/10` + `ring-1 ring-inset ring-primary` + `rounded-md` + `min-h-6`, flat (no shadow), with **no** `accent` colour anywhere in it (`DESIGN.md:84-95`, `:203-204`, `:250`, `:258`).

**Scoped search and navigation**

- **AC-13** — A search committed while scoped (`q`, tag toggle, status/source/sort change, pagination) **stays inside the category**: the path is unchanged and only search params move.
- **AC-14** — Selecting a category from the rail navigates to `/categories/{slug}` preserving `q`/`tag_ids`/`tag_match`/`untagged`/`status`/`source`/`sort` and resetting `page`; selecting "All catalog" navigates to `/catalog` with the same preservation (`EXPERIENCE.md:364-376`).
- **AC-15** — Rail rows are `Link`s (`role="link"`, real `href`), exactly one carries `aria-current="page"`, and the active row's class string remains byte-identical to `ModuleRail.tsx:34` (D-4).
- **AC-16** — Scope changes (rail row, "All catalog", chip escape) **push** onto history so Back returns to the previous scope; all filter/sort/tag/page navigations remain `replace: true` (D-5).
- **AC-17** — At `/categories/{slug}` the shell `ModuleRail` shows **Catalog** as the active module on desktop **and** mobile (D-8); no module tab is added, removed or renamed.
- **AC-18** — `useModels` receives the scope from the **path**; nothing in the app writes `?category=` any more (D-1).

**Non-interference (FR26-BROWSE-2 (a) / FR26-BROWSE-3)**

- **AC-19** — The `Filters (n)` badge is **identical** with and without an active scope; `FilterRibbon.tsx` is not modified and `activeFilterCount()` gains no notion of `category` (D-13).
- **AC-20** — Category scope never enters `tag_match`; the shipped Story 42.1 tag-semantics tests pass **unmodified** with a scope applied (FR26-BROWSE-3).
- **AC-21** — `FacetSidebar.tsx` and `routes/catalog/$id.tsx` have a **zero-line** diff.

**Empty states (branch order is load-bearing)**

- **AC-22** — Scoped + ≥2 tags + effective AND + `total === 0` → the shipped **`andTooNarrow`** branch still wins (primary "Switch to OR", secondary "Clear filters"), and the **scope survives both** (`EXPERIENCE.md:247`).
- **AC-23** — Scoped + no other constraint + `total === 0` → `catalog.emptyCategory` with the primary action **"Search entire catalog"**.
- **AC-24** — Scoped + `filtersActive` + `total === 0` → `catalog.emptyInCategory` interpolated with the category label, primary **"Search entire catalog"** (keeps `q` and tags, drops the scope), secondary **"Clear filters"** (keeps the scope, drops the rest) (`EXPERIENCE.md:246`, `:385`).
- **AC-25** — The shipped page-overshoot branch (`total > 0`, page past the end) is unchanged and still precedes the scoped-empty branches.
- **AC-26** — "Clear filters" **preserves the scope** on every branch — now structurally, because the scope is in the path (`EXPERIENCE.md:385`).

**i18n / a11y / visual / theming**

- **AC-27** — The five new keys exist in **both** `en.json` and `pl.json` with genuine, non-identical Polish; a key-set diff is recorded at close (NFR26-I18N-1). The escape label is exactly `Szukaj w całym katalogu` / `Search entire catalog` (`EXPERIENCE.md:203`) — never `Wyczyść`/`Clear`. No user-visible string is hard-coded. Category labels come from `name_pl`/`name_en` with the empty-string fallback, **never** from i18next (`DESIGN.md:231`).
- **AC-28** — The chip row carries an accessible name from `catalog.browse.activeScope`; the chip action's accessible name states what it does, and is distinct from every other control on the surface (NFR26-A11Y-1).
- **AC-29** — Every control introduced here is keyboard-reachable with a ≥24×24 CSS px target, with no hover-only affordance and no path-based or drag-only interaction (WCAG 2.2 SC 2.5.1 / 2.5.7 / 2.5.8).
- **AC-30** — Tab order is rail → toolbar → scope chip → grid → pagination (`EXPERIENCE.md:278`).
- **AC-31** — A scope change moves focus to the `sr-only` results heading (D-10); it does **not** move focus on filter, sort or page changes.
- **AC-32** — Exactly **one** polite live region exists on the surface, announcing the result count, and the chip is **not** a live region (D-11).
- **AC-33** — Zero colour literals; every colour is a Tailwind class over a `theme.css` token; correct in light **and** dark (NFR26-DARKMODE-1).
- **AC-34** — Targeted **pl-PL** Playwright coverage exists for: scoped default, scoped + filters (both chip labels), unknown slug, scoped-empty and scoped-no-hits empty states — each with an explicit `toBeVisible()` **before** every `toHaveScreenshot` (NFR26-VISUAL-1).
- **AC-35** — `browse-rail.spec.ts` is **repaired** for the `button`→`link` role change (§7.5), not blanket re-baselined.

**Non-regression**

- **AC-36** — `check-all.sh` is green: `npm run lint --max-warnings=0`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run test:visual` (all 4 projects), plus the untouched pytest suites.
- **AC-37** — NFR26-DETERMINISM-1: 3× consecutive identical vitest + pytest pass counts before merge.
- **AC-38** — No `apps/api/`, `workers/`, `infra/` or migration file is modified.

---

## 7. Test strategy

### 7.1 UPDATE — `src/modules/catalog/components/BrowseRail.test.tsx`

Rows are anchors now, so the suite needs a router. Wrap renders in a memory `RouterProvider` registering `/catalog` and `/categories/$slug` (the same shape `CatalogList.test.tsx` already builds — reuse that pattern, do not invent a second one). Keep `import { cleanup } from "@testing-library/react"; afterEach(cleanup);` — `vitest.config.ts` sets `globals: false`, so auto-cleanup does not register (`project-context.md:115`).

Re-point the shipped assertions from `onSelect` payloads to `href`s: `/categories/organizery` for a category row, `/catalog` for "All catalog", both carrying the preserved search string. Every other shipped assertion (API order, count rendering, `aria-current` on exactly one row, dimmed-but-focusable zero-count row, skeleton, empty list, error + retry, `name_pl: ""` fallback, no `parent_id` nesting) is **preserved unchanged** — no test may be weakened, narrowed, renamed or deleted to accommodate the anchor.

### 7.2 UPDATE — `src/modules/catalog/routes/CatalogList.test.tsx`

Extend `mountAt` to register **both** routes with the real `validateSearch` (and the real `beforeLoad`), and correct its now-false comment about the hard-coded `from`. Continue stubbing `fetch` over `json()` — **never** mock `api()` (`project-context.md:114,252`).

New/updated cases: `/catalog?category=x` redirects to `/categories/x` preserving `q` + `tag_ids` (AC-4); a rail row click lands on `/categories/{slug}` with filters preserved and `page` reset (AC-14); the chip renders only when scoped (AC-6/AC-7); the escape lands on `/catalog` with every other param intact (AC-10); an unknown slug renders the raw-slug chip and an empty grid, not an error (AC-5/AC-11); a query committed while scoped keeps the path (AC-13); the three scoped empty branches fire in the right order (AC-22/AC-23/AC-24/AC-25); "Clear filters" keeps the scope (AC-26); the `Filters (n)` badge is identical across a scope change (AC-19); focus lands on the results heading after a scope change but not after a filter change (AC-31).

### 7.3 NEW — `src/modules/catalog/components/ScopeChip.test.tsx`

Presentational unit coverage: both action labels under `otherConstraintsActive` true/false (AC-9); the action is a link with a text label and no `×` (AC-8); the accessible name from `catalog.browse.activeScope` (AC-28); raw-slug label passthrough (AC-11); token classes present and no `accent` class (AC-12/AC-33).

### 7.4 UPDATE — `src/modules/catalog/browse-i18n.test.ts`

Extend the shipped key-set-diff guard (51.1 §7.3) with the five new keys: present in both files, Polish not identical to English. The repo-wide `tests/i18n.test.ts` parity check must stay green.

### 7.5 UPDATE — `tests/visual/browse-rail.spec.ts` (mandatory repair, not a re-baseline)

Every `getByRole("button", …)` targeting a rail row becomes `getByRole("link", …)` (§2.8). The `skipOnMobile` helper and its reason stay accurate (the rail is still `hidden … lg:flex`). **Classify each resulting baseline change as `stale-baseline` before any `--update-snapshots`** — per the Init 10 triage rule (`AGENTS.md` § "Visual baseline triage before regen"). The expectation is that **no rail baseline moves at all** (D-4); one that does is a `deterministic-fail` to root-cause.

### 7.6 NEW — `tests/visual/category-browse.spec.ts`

pl-PL, using the shipped `stubSotList` (its `**/api/categories*` and `**/api/models*` stubs already cover this route — no new stub is needed). Navigate to `/categories/uchwyty`. Baselines: scoped default (chip + `Wyczyść kategorię`), scoped with a filter applied (chip action flips to `Szukaj w całym katalogu`), unknown slug (raw-slug chip + empty grid), scoped-empty (`dekoracje`, `model_count: 0`), scoped-no-hits. Each preceded by an explicit `toBeVisible()` on the specific element under test (AC-34).

### 7.7 Expected baseline movement (triage list, authored up front)

**The headline expectation is ZERO movement on every existing `/catalog` baseline**, on all four projects. This story adds no pixels to `/catalog`: the chip renders only when scoped, the results heading and the live region are `sr-only`, and the rail's anchor conversion keeps every class string. Any `/catalog` baseline that moves — desktop **or** mobile — is a `deterministic-fail` to root-cause, **not** a stale baseline to regenerate. The only *new* baselines are `category-browse.spec.ts`'s. Every regenerated or new PNG needs a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line naming **the agent that actually inspected it** — never a human who did not (`epic:45`/`epic:46` GOVERNANCE action items, both still `open`; 51.1 §15.2).

### 7.8 RED→GREEN evidence

Tee dev-time runs to gitignored `.hermes/run-logs/e51.2-*.log`. Record the failing run before the fix and the passing run after for §7.1–7.4. Visual regression is the gate, not typecheck (`project-context.md:254`).

---

## 8. Gates + ownership

| Gate | Owner | Notes |
|---|---|---|
| `ruff` (api + worker) | untouched | no Python in this story |
| `npm run lint --max-warnings=0` | this story | watch `react-refresh/only-export-components` on `ScopeChip.tsx`; `routeTree.gen.ts` is lint-ignored |
| `npm run typecheck` | this story | `verbatimModuleSyntax` → `import type`; `noUncheckedIndexedAccess` → no `!` shortcuts; the D-2 props cutover is where type errors will surface first |
| `npm run test` (vitest) | this story | §7.1–7.4 |
| `npm run build` | this story | **also the `routeTree.gen.ts` regeneration step** (§2.1) — run it before committing |
| `npm run test:visual` (4 projects) | this story | §7.5–7.7; mandatory for any UI change |
| `bmad-code-review` (CR) | after DS | Blind Hunter + Edge Case Hunter + Acceptance Auditor |
| Independent external review | after CR | **`laura-aider-review-diff` / Aider** — the routine default per `LAURA_AGENT_RULEBOOK.md` § 2 and `AGENTS.md:108`. Gemini is **not** a default reviewer. Codex is fallback / high-stakes / explicit-operator-request only |
| `infra/scripts/check-all.sh` 16/16 | before ff-merge | tee to `.hermes/run-logs/` |
| NFR26-DETERMINISM-1 | before merge | 3× consecutive identical vitest + pytest pass counts |

Branch: `feat/E51.2-categories-route-and-scope-chip` (`AGENTS.md` § Branch naming). ff-only merge, no squash. Deploy after merge (`feat:` prefix forces the range-based deploy gate).

---

## 9. Anti-pattern fences — do NOT do these

- **Do not** hand-edit `routeTree.gen.ts` — regenerate it via `npm run build`/`npm run dev` (`project-context.md:131`).
- **Do not** change any validation **rule** in `routes/catalog/index.tsx`; the extraction is a rename-to-export only (D-3, AC-3).
- **Do not** solve the shared-component problem with `useSearch({ strict: false })`, a cast or `any` (D-2).
- **Do not** duplicate `CatalogList` for the new route.
- **Do not** keep `?category=` alive as a second scope source (D-1/D-12).
- **Do not** mount `useCategoryBySlug` on this route — it 404s on an unknown slug, which the UX contract forbids here (D-7).
- **Do not** add `category` to `activeFilterCount()` or touch `FilterRibbon.tsx` (D-13, AC-19).
- **Do not** mix category scope into `tag_match` (FR26-BROWSE-3).
- **Do not** modify `FacetSidebar.tsx` (AC-21) or re-open 51.1's D-2 relocation — the `Filters (n)` surface is Story 52.1.
- **Do not** build the mobile Browse surface or add/remove/rename a `ModuleRail` tab — Story 51.3's `Ask First` (D-8 states exactly what this story does touch).
- **Do not** render categories on `/catalog/$modelId` — Story 51.4.
- **Do not** ship a bare `×` as the chip's escape (`DESIGN.md:296`).
- **Do not** use `accent` colour on the chip, or `primary` on a tag chip (`DESIGN.md:293-294`).
- **Do not** add a second live region or make the chip one (D-11).
- **Do not** weaken, narrow, rename or delete a shipped test to accommodate the anchor conversion (§7.1).
- **Do not** blanket-run `--update-snapshots`; a moved `/catalog` baseline is a `deterministic-fail` (§7.7).
- **Do not** bypass `api()` with raw `fetch` (`project-context.md:48,250`), and **do not** add an inline hex colour (`:47`).
- **Do not** touch `apps/api/`, `workers/`, `infra/`, or any migration (AC-38).

---

## 10. Verification performed for this spec

Every fact above was produced by a command run in this session at `main` @ `f55bb9f` (clean tree, `HEAD == origin/main`).

| # | Command / read | Result used |
|---|---|---|
| 1 | `git status --short --branch`; `git rev-parse HEAD`; `git rev-parse origin/main` | clean `main`, `f55bb9f == origin/main` → `baseline_commit` |
| 2 | Read `AGENTS.md`, `CLAUDE.md`, `_bmad-output/project-context.md` (§ index + rules) | gates, branch policy, reviewer routing (§8), execution discipline |
| 3 | Full read of `sprint-status.yaml` `development_status` (comments stripped) + epic-51 `action_items` | `epic-51: in-progress`, `51-1: done`, `51-2` first `backlog` key, four open epic-51 handoffs |
| 4 | `ls _bmad-output/implementation-artifacts/ \| grep -E '^51'` + spec-name scan | no duplicate story or spec for 51.2 |
| 5 | `grep -n 'create-story\|dev-story\|code-review' _bmad/_config/bmad-help.csv` | routing rows 26/27/28/29 (§ header) |
| 6 | `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` | `implementation_artifacts`, `document_output_language: English`, `communication_language: Polish` |
| 7 | `python3 _bmad/scripts/resolve_customization.py --skill … --key workflow` | `persistent_facts: file:**/project-context.md`; no prepend/append/on_complete steps |
| 8 | Full read `_bmad-output/implementation-artifacts/51-1-desktop-browse-navigation.md` (605 lines) | previous-story intelligence: D-1…D-11, §12 handoffs, §17 `DF-1`…`DF-4`, §19 merge/deploy facts |
| 9 | Full read `routes/catalog/index.tsx` (123 lines) | `CatalogSearch`, `validateSearch` structure, the 50.2 `category` branch, absence of `beforeLoad` (§2.2) |
| 10 | Full read `modules/catalog/routes/CatalogList.tsx` (379 lines) | hard-coded `from`, every navigator, both fatal guards, `filtersActive`, `andTooNarrow`, empty-branch order, layout seams (§2.3) |
| 11 | Full read `components/BrowseRail.tsx` (135 lines) | props, class strings, a11y contract, label fallback (§2.4) |
| 12 | Full read `shell/ModuleRail.tsx` | `pathname.startsWith(to)` predicate → the D-8 finding (§2.5) |
| 13 | Read `hooks/useCategories.ts`, `hooks/useCategoryBySlug.ts`, `grep` `useModels.ts` `buildParams` | keys, staleTime, the 404 contract, `URLSearchParams` encoding (§2.6) |
| 14 | Read `ui/custom/EmptyState.tsx` | no interpolation, `secondaryAction` gated on `action` → D-9 (§2.7) |
| 15 | `find apps/web/src/routes -type f`; `git ls-files src/routeTree.gen.ts`; `grep` `routeTree.gen.ts` | no `categories/` dir; the gen file is tracked; existing catalog route ids (§2.1) |
| 16 | Read `vite.config.ts` plugins + `package.json` scripts | `TanStackRouterVite` is the only regeneration mechanism; no standalone codegen script (§2.1) |
| 17 | `python3 -c` version dump of `node_modules/@tanstack/react-router` + read `useSearch.d.ts` / `useParams.d.ts` | installed **1.169.2**; `StrictOrFrom` confirms `strict:false` exists and why it is rejected (D-2) |
| 18 | `grep` `try_files` in `apps/web/nginx.conf` | SPA fallback already serves `/categories/*`; no infra change (§2.1) |
| 19 | `python3` key dump of `en.json`/`pl.json` | 913 keys each; reusable key inventory; no pre-existing scope-chip key (§2.7, §3.8) |
| 20 | Read `CatalogList.test.tsx:1-200` | harness shape, `mountAt`, the now-false `from` comment, the 51.1 category fixtures (§2.8, §7.2) |
| 21 | Read `tests/visual/api-stubs.ts:160-232`; `browse-rail.spec.ts:1-40` | `stubSotList` already stubs categories; `getByRole("button")` breakage (§2.8, §7.5–7.6) |
| 22 | Read `epics.md:4519-4541`; `prd.md:2244-2302`; `architecture.md:3303-3345` | epic sketch, FR26-BROWSE-1/2/3, NFR26 block, Decision AY read surface + unknown-slug posture |
| 23 | `grep`-guided reads of `ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md` + `DESIGN.md` | scope-chip anatomy, action-label rule, transition table, empty states, a11y/focus/announcements, responsive, tokens |
| 24 | `grep 'useCategoryBySlug\|51.2' deferred-work.md` | the two ledgered 50.1 entries routed to this story → D-7 / §12 |
| 25 | `git log --oneline -5` | `f55bb9f` is the 51.1 docs closeout on top of `e15b8fe` (`feat(web): add desktop browse navigation`) |

**Not run, and not claimed:** no test, no build, no lint, no typecheck, no visual run, no `npm` invocation of any kind. This is a story-authoring pass; every gate in §8 is owed by `bmad-dev-story`.

---

## 11. Tasks / Subtasks — dev execution (native `bmad-dev-story`, under a controller-issued `G26-DEVGO`)

Completion state below is recorded at the **2026-07-29 controller closeout**, which is the union of the native `bmad-dev-story` run and the controller repair pass. §16 states, per task, which of the two actually finished it — no controller-authored patch is attributed to the DS run.

- [x] **T1 — Branch** — `feat/E51.2-categories-route-scope-chip` off `main` @ `f55bb9f`. *(Note: the branch name shipped is `…-categories-route-scope-chip`, one word shorter than the `…-categories-route-and-scope-chip` §8 predicted. Cosmetic, recorded rather than silently corrected.)* — DS.
- [x] **T2 — RED** (AC-6…AC-12, AC-28) — `ScopeChip.test.tsx` authored against the not-yet-existing component; failing run captured by DS.
- [x] **T3 — i18n** (AC-27) — five keys in `en.json` + `pl.json`; `browse-i18n.test.ts` extended with the `catalog.browse.` prefix bump 7 → 10 **and** an explicit `SCOPE_KEYS` block for the two keys that sit outside the prefix (`catalog.emptyCategory`, `catalog.emptyInCategory`), plus a literal assertion pinning `Search entire catalog` / `Szukaj w całym katalogu` and rejecting `Wyczyść`/`Clear` on the escape. — DS.
- [x] **T4 — GREEN** — `ScopeChip.tsx` shipped with the `DESIGN.md` token set verbatim (`bg-primary/10`, `ring-1 ring-inset ring-primary`, `rounded-md`, `min-h-6`, flat, no `accent`, text-labelled escape). — DS.
- [x] **T5 — Route** (AC-1…AC-5) — `validateCatalogSearch` exported from `routes/catalog/index.tsx`, `beforeLoad` redirect added, `routes/categories/$slug.tsx` created; `routeTree.gen.ts` regenerated **by the vite/TanStack plugin during `npm run build`**, never hand-edited. Regeneration re-confirmed by the controller's own `npm run build` (§15.3). Commit of the generated diff is **owed at closeout**, which is controller-owned and not yet run.
- [x] **T6 — Props cutover** (D-2, AC-13, AC-18, AC-26) — `CatalogList` takes `{scopeSlug, search, onSearchChange}`; both route files own their own `Route.use*` bindings; no `strict:false`, no cast, no `any`. `FacetSidebar.tsx` and `routes/catalog/$id.tsx` are absent from the change set (AC-21). — DS.
- [x] **T7 — Chip + empty states** (AC-22…AC-25) — chip row mounted between the toolbar and the grid; both scoped branches slotted **after** `andTooNarrow` and page-overshoot (`CatalogList.tsx:387-470`); `EmptyState` gained the optional `messageParams` prop. — DS.
- [x] **T8 — Rail anchors** (AC-14…AC-16) — `BrowseRail` rows are `Link`s; `onSelect` removed and replaced by a `search` prop carrying the forwarded (category-free) search layer; `BrowseRail.test.tsx` re-pointed from `onSelect` payloads to `href`s with a router wrapper. — DS.
- [x] **T9 — Shell** (AC-17) — `ModuleRail` gained an `alsoOwns?: readonly string[]` field and one `isModuleActive()` helper shared by the desktop rail and the mobile bottom bar; the catalog entry declares `alsoOwns: ["/categories"]`. No tab added, removed or renamed — 51.3's `Ask First` boundary untouched. `ModuleRail.test.tsx` is **new** and pins both viewports. — DS.
- [x] **T10 — a11y** (AC-29…AC-32) — `sr-only` `tabIndex={-1}` `<h2>` results heading with a **ref callback** keyed on `useRouterState(s => s.location.state.__TSR_index > 0)`, because a scope change remounts the component across two routes and a "previous scope" ref cannot survive it; one polite `role="status"` region on the result count; the chip is `role="group"` and explicitly **not** a live region. — DS.
- [x] **T11 — Integration tests** (§7.2) — `CatalogList.test.tsx` harness registers both routes with the real `validateSearch` and the real `beforeLoad`; redirect, branch-order, scope-preservation, `Filters (n)`-invariance and focus cases added. — DS.
- [x] **T12 — Visual** (§7.5–7.6, AC-34/AC-35) — `browse-rail.spec.ts` **repaired** (every rail-row `getByRole("button")` → `getByRole("link")`; the "active" case now navigates to `/categories/uchwyty`, the real canonical URL, instead of `/catalog?category=`). `category-browse.spec.ts` **authored by the controller** (§15.2): two pl-PL cases, each with a concrete `toBeVisible()` immediately before capture. — DS (repair) + **controller** (new spec).
- [x] **T13 — Baseline triage** (§7.7) — 8 new `category-browse` baselines (2 cases × 4 projects) and exactly **2** regenerated `browse-rail-active-desktop-{light,dark}` baselines. The two movements are classified **intentional feature delta**, not `stale-baseline` drift and not `deterministic-fail`: the spec itself was re-pointed from `/catalog?category=uchwyty` to `/categories/uchwyty`, so the captured page legitimately now contains the scope-chip row. **Zero `/catalog` baseline movement and zero mobile baseline movement**, which is the positive evidence D-4's pixel-neutrality claim asked for. — controller.
- [x] **T14 — Gates** (AC-36) — lint / tsc / vitest / build / targeted visual / `git diff --check` all rc=0 (§15.3). **Deviation, stated:** `infra/scripts/check-all.sh` 16/16 and the AC-37 3× determinism triple were **not** re-run at the closeout; the DS run's full vitest pass (145 files / 913 tests) was reproduced once by the controller, not three times. Both remain **owed and controller-owned** (§15.6).
- [ ] **T15 — Handoffs** — §12's forward handoffs (52.1 badge invariant, 51.3 mobile Browse, 51.4 detail links) and the two **re-routed** `deferred-work.md` entries are recorded in §12 and in this closeout's `sprint-status.yaml` entry, but the `action_items` block itself was **not** edited by this pass: closing the three epic-51 items (51.1 D-7 handoff, the `Link` divergence, `DF-2`) is part of the controller's merge-time bookkeeping, and claiming them before the merge would assert a discharge the tree has not yet shipped. **Open.**

---

## 12. Handoffs and ledger movements

**Discharged by this story** (close at its gate, with evidence):
1. epic-51 action item *"HANDOFF from 51.1 (D-7): results-heading focus target … 51.2 must add it AND re-point 51.1's setCategory navigator at the new /categories/$slug canonical URL"* → D-10 + D-1/D-12.
2. epic-51 action item *"REVIEW-VISIBLE DIVERGENCE from 51.1: EXPERIENCE.md:219 specifies each browse-rail row 'is a Link'"* → D-4.
3. 51.1 `DF-2` (*`setCategory` uses `replace: true`; browse-route history should be revisited when 51.2 adds canonical category routes*) → D-5.

**Re-routed, not closed** (D-7 — this story deliberately mounts no `useCategoryBySlug` caller, so the ledger's stated trigger did not fire):
4. `deferred-work.md` — *`useCategoryBySlug` interpolates the slug without `encodeURIComponent`*. **New trigger:** the first surface that actually calls the hook, or the backend slug-charset validation ledgered under the 49.5 review — whichever lands first. Both halves are still best closed together, server-side. Reachability remains **zero**.
5. `deferred-work.md` — *`useCategoryBySlug("")` follows the `307` to the list endpoint and types an array as one object*. **New trigger:** same. Additionally worth raising at that time: a hook with no caller across two stories is itself a finding — either give it a caller or delete it. This story does not act on it, because 50.1 froze the hook's shape.

**Carried forward unchanged:**
6. → Story 52.1 — the interim Tags sheet label/side/badge consolidation (51.1 D-2). Untouched here; **the badge it introduces must still exclude category scope** (AC-19 is the invariant 52.1 inherits).
7. → Story 51.3 — the mobile Browse surface. This story renders the chip on all viewports but adds **no** mobile browse control; the `Ask First` boundary is undisturbed (D-8).
8. → Story 51.4 — model-detail category links target `/categories/{slug}`, which this story makes real.

---

## 13. Validation record — native `bmad-create-story:validate` (VS), 2026-07-29

Run immediately after Create, in the same session, against `./checklist.md`. Route: `_bmad/_config/bmad-help.csv:27` (**VS**, `preceded-by bmad-create-story:create`, `followed-by bmad-dev-story`, `required=false` — run as the recommended quality gate per `AGENTS.md:218`).

**Verdict: PASS.** Status set to `ready-for-dev`. No BMAD protest, no missing prerequisite, no duplicate story, no unmet dependency, and no operator decision that could not be resolved from the artifacts.

### 13.1 Disaster-prevention checks and what they found

| Checklist axis | Finding |
|---|---|
| **Reinvention prevention** | Four catches, all folded in during Create: (1) `validateSearch` is **re-used**, not re-authored (D-3), so the 43.3/50.2 hardening cannot fork; (2) `CatalogList` is **shared**, not duplicated (D-2); (3) `EmptyState` gains one optional prop instead of a near-duplicate catalog empty state (D-9); (4) the chip label reads the **already-loaded** `useCategories()` result instead of adding a second request (D-7). `stubSotList`'s existing category stub is reused rather than re-added (§7.6). |
| **Wrong libraries / versions** | No new dependency. The installed router was checked **at source** — `@tanstack/react-router` **1.169.2**, not the `^1.84.0` the manifest declares — and its `useSearch`/`useParams` typings were read to justify rejecting `strict: false` (D-2) rather than assuming it. Regeneration mechanism verified from `vite.config.ts` + `package.json`: there is **no** codegen script, so `npm run build` *is* the regeneration step (§2.1, T5) — a story that said "regenerate routeTree" without naming a command would have stranded the dev agent. Stack facts re-checked against `project-context.md`: React 19, TanStack Query 5, Tailwind v4, TS with `verbatimModuleSyntax` + `noUncheckedIndexedAccess`, i18next. |
| **Wrong file locations** | `routes/categories/$slug.tsx` follows the `$id`/`$token` file-route convention; `ScopeChip.tsx` lands beside its siblings in `modules/catalog/components/` with a colocated unit test; the visual spec goes to `tests/visual/`. Verified that non-route files inside `src/routes/` are ignored by the plugin, so a colocated test is safe (§2.1). |
| **Regression prevention** | **The three highest-value finds.** (1) `ModuleRail.tsx:26,49` uses `pathname.startsWith("/catalog")`, so the new route would leave **no active module** on desktop *and* mobile — a regression this story causes and must fix (D-8, AC-17). (2) `browse-rail.spec.ts` queries rail rows by `role="button"`; the `Link` conversion silently breaks it, and the repair is mandated as a repair, not a re-baseline (AC-35, §7.5). (3) `CatalogList.test.tsx`'s `mountAt` comment and single-route harness become false under D-2, and the 51.1 `?category=` assertions break **by design** — both are pre-declared rather than discovered mid-run. Fourth: §7.7 pre-declares that **any** moved `/catalog` baseline is a `deterministic-fail`, which is what converts "should be pixel-neutral" from a hope into a gate. |
| **UX compliance** | Cross-checked against the closed **G26-UXGATE** artifact, not the epic prose: chip anatomy and tokens (`DESIGN.md:84-95`, `:273-274`), colour-role rules (`:203-204`, `:293-296`), radius contrast (`:256-258`), flat-not-floating (`:250`), geometry (`:244`); action-label state rule (`EXPERIENCE.md:222`), transition table (`:364-387`), empty-state branch order (`:245-247`), unknown-slug posture (`:258`), tab order (`:278`), focus (`:324`), announcements (`:314-316`), terminology (`:203`). The one place the spine is **ambiguous** — whether the chip escape pushes or replaces — is resolved explicitly with a stated rule and a stated cost (D-5) rather than silently. |
| **Vagueness / completion-lying** | 38 ACs, each mechanically checkable. AC-3 ("`index.test.ts` passes unmodified"), AC-15 ("byte-identical to `ModuleRail.tsx:34`"), AC-19 ("badge identical across a scope change"), AC-21 ("zero-line diff") and §7.7 ("zero `/catalog` baseline movement") are deliberately falsifiable. §10 separates what was verified from what was explicitly **not** run. |
| **Scope creep** | §9 fences 18 named non-goals. Three edits outside the catalog module are each justified against a defect this story would otherwise introduce (`ModuleRail` predicate, `EmptyState` param, `routeTree.gen.ts`) and each is bounded to a single line-class of change. Ponytail minimal-diff honoured: one new route, one new component, one shared-component prop cutover, one anchor conversion, one predicate widening, five i18n keys. The `Filters (n)` surface, the mobile Browse surface and model-detail categories are all explicitly fenced to 52.1 / 51.3 / 51.4. |
| **Learning from past work** | Applies the `epic:47` stale-precondition item (§2 exists because of it, and it found the `ModuleRail` and `browse-rail.spec.ts` breakages), the `epic:45`/`epic:46` TEST-AUTHORING `toBeVisible()` rule (AC-34), the baseline-provenance GOVERNANCE items (§7.7), Init 10's visual-triage rule (§7.7/T13), Init 18's cache-coherence enumeration (§5) and magic-constant contract-pointing (§5 — `staleTime` left unchanged and pointed at its own contract). 51.1's own in-run defect classes are pre-empted: the pl copy for every new key is authored from the UX terminology table rather than guessed, and the `en`/`pl` divergence trap that produced 51.1's latent false-green is covered by AC-27 + §7.4. |
| **Sequencing / prerequisites** | E49 + E50 are `done`; 51.1 is `done`, merged (`e15b8fe`), deployed and smoke-verified (51.1 §19), which is the stated dependency for the rest of E51. `epic-51` is already `in-progress`, so no epic flip is owed. G26-UXGATE closed 2026-07-26. **G26-DEVGO is not issued by this pass** — dev start remains a separate controller act. No prerequisite is unmet. |
| **LLM/dev-agent optimization** | Decisions are numbered (D-1…D-13) and referenced from the ACs, the fences and the tasks, so the dev agent can resolve any "why" without re-reading prose. Exact file paths, exact line anchors, exact class strings, the exact regeneration command and the exact i18n values are inlined so nothing needs re-derivation. |

### 13.2 Open questions for the controller — none blocking

- **Q1 (informational, D-12).** The `/catalog?category=` → `/categories/{slug}` redirect is what makes "canonical URL" true and preserves the bookmarks 51.1 shipped (including the deploy-smoke URL). If the controller would rather tolerate both URL forms, deleting the `beforeLoad` is a ~6-line reversal — but `CatalogList` would then read scope from two sources forever, and every later story would have to remember which. Recorded recommendation: **keep the redirect**.
- **Q2 (informational, D-8).** The `ModuleRail` predicate widening touches a shell file that Story 51.3 carries an `Ask First` boundary over. The boundary is about the mobile **tab set**, which this does not change; without the widening, the shell shows no active module on the new route. Recorded recommendation: **keep it in this story**. If the controller reads the boundary more broadly, drop T9 and file the dark-module-row as a known defect owned by 51.3.
- **Q3 (informational, D-5).** The chip escape **pushes** rather than replaces, diverging from the literal wording of `EXPERIENCE.md:387` in order to keep "scope changes push, filter changes replace" internally consistent. One flag flips it.

---

## 14. Dev Agent Record

### 14.1 Agent Model Used

- **Implementation:** Claude Opus 5 (1M context), native `bmad-dev-story` (**DS**), 2026-07-29, under a controller-issued `G26-DEVGO`. The run terminated on `subtype=error_max_turns` during final lint hygiene, **after** its own `TSC_RC=0` and a full `npm run test` pass of **145 files / 913 tests**. No `RUN_EXIT rc=0` may be cited for that session; its writes landed and were re-confirmed from the tree.
- **Closeout repair + gates:** Claude Opus 5 (1M context) acting as **controller**, same day, in a separate session. Authored `tests/visual/category-browse.spec.ts` and its 8 baselines, repaired the two `no-unused-vars` errors and the `react-refresh/only-export-components` warning, restored the files an accidental repo-wide Prettier invocation had touched outside this story's blast radius, and re-ran the gates in §15.3.
- **Independent external review:** `laura-aider-review-diff` / Aider — the Rulebook's routine route. **Gemini was not used. Codex was not used.**
- **Authorization posture:** Laura/controller standing Initiative 26 authorization plus the story-specific `G26-DEVGO`. **NOT** an Ezop signature, **NOT** Ezop review, **NOT** human review of any kind. No human has reviewed this diff.

### 14.2 Debug Log References

| What | Where / marker |
|---|---|
| DS implementation run | native `bmad-dev-story` session, 2026-07-29; terminal condition `error_max_turns` during lint hygiene. In-run evidence read from the session: `TSC_RC=0`; full vitest **145 files / 913 tests passed**. Applies the standing `epic:45` RECOVERY action item — a turn-limit **after** the work landed is a truncated epilogue, not a failed unit, so the tree was inspected and repaired rather than restarted. |
| Controller closeout gates | §15.3, all rc=0: `npm run lint`, `npx tsc -b`, `npm run test` (145 files / 913 tests), `npm run build`, targeted Playwright visual (22 passed / 10 skipped), `git diff --check`, added-line static secret / dangerous-code scan → `STATIC_SCAN_OK`. |
| Independent external review | `laura-aider-review-diff`. **Pass 1: REQUEST_CHANGES** — missing Story 51.2 visual coverage, role-query breakage, and no evidence that `routeTree.gen.ts` had actually been regenerated by a build. **Follow-up pass: APPROVE** after the controller added `category-browse.spec.ts` + baselines, repaired the role queries and produced the build/regeneration evidence. Both verdicts recorded literally; the initial REQUEST_CHANGES is **not** presented as a formality. |
| Not teed to `.hermes/run-logs/` | §7.8 asked for `.hermes/run-logs/e51.2-*.log`. The DS run's RED→GREEN transcripts were **not** teed to that path, and this closeout does not invent log filenames for them. The gate results above are controller-reported from the runs themselves. Recorded as a §7.8 shortfall, not as a satisfied obligation. |

### 14.3 Completion Notes List

1. **Scope lives in the path, and the seam is defended twice (D-1).** The scoped route's `validateSearch` strips `category` (`routes/categories/$slug.tsx:14-20`), but TanStack merges the **root** match's raw parsed search into every child match, so a hand-crafted `/categories/uchwyty?category=organizery` puts the stray token back. `CatalogList.tsx:135-136` drops it once more at the single seam that feeds every onward URL (rail hrefs, chip escape). Without that second drop the second scope source D-1 exists to abolish would have been resurrected by any hand-crafted URL. This is a real defect found during implementation, not a belt-and-braces flourish.
2. **`CatalogListSearch = Omit<CatalogSearch, "category">`** was introduced (`routes/catalog/index.tsx:152`) so anything forwarding search across the two routes is typed exactly and cannot smuggle a scope back in. `ScopeChip` takes an explicit `search` **object**, not a TanStack updater, for the same reason D-2 rejected `useSearch({strict:false})`: an updater's `prev` is the union across every registered route.
3. **The focus-target problem was harder than D-10 assumed.** `/catalog` and `/categories/$slug` are different routes, so a scope change **remounts** `CatalogList` — a "previous scope" ref cannot survive it, and a mount effect fires while the component is still on the loading branch (fresh query key, no data). Solved with `useRouterState(s => s.location.state.__TSR_index > 0)` plus a **ref callback** that fires when the heading node actually attaches. Net: focus moves on a real navigation, and does **not** move on a cold load (which would strand Tab past the browse rail) or on a `replace`-class filter/sort/page change.
4. **`BrowseRail`'s prop cutover is `onSelect` → `search`, not just `onSelect` removed.** The rows need the current search layer to build their `href`s, so the rail now receives `search={forwardSearch}` from `CatalogList`. Every other prop, both class strings, `aria-current`, the `aria-label`/count contract, the dimmed zero-count treatment, the skeleton and the error block are unchanged.
5. **`ModuleRail` (D-8) was widened with data, not a hard-coded string.** `MODULES` gained an optional `alsoOwns?: readonly string[]`, and one `isModuleActive()` helper is shared by the desktop rail and the mobile bottom bar (they previously duplicated `pathname.startsWith(to)` at `:26` and `:49`). The catalog entry declares `alsoOwns: ["/categories"]`. No tab added, removed or renamed.
6. **AC-3 is recorded as PARTIALLY verified, deliberately.** No validation **rule** in `routes/catalog/index.tsx` changed — the extraction is a rename-to-`export` plus one `eslint-disable-next-line react-refresh/only-export-components` comment, and the `beforeLoad` sits on the route object, outside the validator. Every shipped assertion block in `routes/catalog/index.test.ts` (43.3 `tag_ids` hardening, 44.2 `tag_match` normalisation, the 50.2 `category` suite, the login-`next` case) is present, unweakened, unrenamed and undeleted — verified by a full read at closeout. **But** the file shows as `M` in the working tree, and this bookkeeping pass had **no shell access**, so it could not run `git diff` to prove the change is byte-empty of behavioural edits. AC-3's literal "passes **unmodified**" clause is therefore **not** claimed as measured. This must be re-checked with `git diff apps/web/src/routes/catalog/index.test.ts` before the merge.
7. **The two `browse-rail-active` baselines moved, and the movement is intentional feature delta.** §7.7 pre-declared that any moved **`/catalog`** baseline is a `deterministic-fail`. Zero `/catalog` baselines moved. The two that did are `browse-rail-active-desktop-{light,dark}`, and they moved because the spec itself was re-pointed from `/catalog?category=uchwyty` to the now-real `/categories/uchwyty`, so the captured page legitimately contains the scope-chip row. That is a changed **input**, not a drifted render — classified before regeneration, per the Init 10 triage rule.
8. **Zero mobile baseline movement**, and zero movement anywhere outside the two rail-active files. The chip renders only when scoped; the results heading and the live region are `sr-only`; the rail's anchor conversion kept every class string.
9. **`useCategoryBySlug` is still not mounted (D-7).** The chip label resolves from the already-loaded `useCategories()` list with a raw-slug fallback that covers unknown slug, pending list and failed list in one path. The two `deferred-work.md` entries are therefore **re-routed with a new named trigger, not closed** (§12 items 4–5). `deferred-work.md` was deliberately **not** edited by this pass.
10. **Honest attribution.** Items 1–5 and 9 are the DS run's work. The visual spec, its 8 baselines, the two lint-error repairs (`void scopeLivesInThePath` in both files), the `react-refresh` disable comment on `validateCatalogSearch`, the Prettier blast-radius restoration and every gate figure in §15.3 are the **controller's**. The DS run did not finish its own lint hygiene.

### 14.4 File List

Derived from the working tree at closeout. **Provenance caveat:** this bookkeeping session had no shell access, so the list below is reconstructed from the session's `git status` snapshot plus direct reads of each file — not from a fresh `git status -uall`. Re-verify with `git status --porcelain -uall` before staging.

**Production code (7)**

| Path | State |
|---|---|
| `apps/web/src/routes/categories/$slug.tsx` | **new** — the canonical scoped browse route (AC-1/AC-2) |
| `apps/web/src/routes/catalog/index.tsx` | modified — `validateCatalogSearch` exported, `CatalogListSearch` added, `beforeLoad` redirect, `CatalogListRoute` wrapper |
| `apps/web/src/modules/catalog/components/ScopeChip.tsx` | **new** — the scope chip (AC-6…AC-12) |
| `apps/web/src/modules/catalog/routes/CatalogList.tsx` | modified — three-prop cutover, chip mount, scoped empty branches, results heading, live region, `escapeScope` |
| `apps/web/src/modules/catalog/components/BrowseRail.tsx` | modified — rows are `Link`s; `onSelect` → `search` |
| `apps/web/src/shell/ModuleRail.tsx` | modified — `alsoOwns` + `isModuleActive()` (D-8) |
| `apps/web/src/ui/custom/EmptyState.tsx` | modified — additive optional `messageParams` (D-9) |

**Generated (1)**

| Path | State |
|---|---|
| `apps/web/src/routeTree.gen.ts` | modified — regenerated by the vite/TanStack plugin during `npm run build`; never hand-edited |

**i18n (2)**

`apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — the five new keys from §3.8.

**Tests (7)**

| Path | State |
|---|---|
| `apps/web/src/modules/catalog/components/ScopeChip.test.tsx` | **new** |
| `apps/web/src/shell/ModuleRail.test.tsx` | **new** |
| `apps/web/src/modules/catalog/components/BrowseRail.test.tsx` | modified — router wrapper + `href` assertions |
| `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` | modified — both routes registered in `mountAt` |
| `apps/web/src/modules/catalog/browse-i18n.test.ts` | modified — prefix count 7 → 10 + `SCOPE_KEYS` block |
| `apps/web/src/ui/custom/EmptyState.test.tsx` | modified — `messageParams` coverage |
| `apps/web/src/routes/catalog/index.test.ts` | modified — **see completion note 6; the diff was not measured by this pass** |

**Visual specs (2)**

| Path | State |
|---|---|
| `apps/web/tests/visual/category-browse.spec.ts` | **new** — controller-authored (§15.2) |
| `apps/web/tests/visual/browse-rail.spec.ts` | modified — `role=button` → `role=link`; active case re-pointed to `/categories/uchwyty` |

**Baselines (10)**

- **New (8)** — `__snapshots__/category-browse.spec.ts/`: `category-browse-scoped-populated-{desktop,mobile}-{light,dark}.png`, `category-browse-empty-unknown-{desktop,mobile}-{light,dark}.png`.
- **Regenerated (2)** — `__snapshots__/browse-rail.spec.ts/browse-rail-active-desktop-{light,dark}.png`.
- Every one of the 10 needs a `baseline-reviewed: <basename>, Claude Opus 5, 2026-07-29` line at commit time, naming **the agent that actually inspected it** — never Ezop, never Laura (`epic:45`/`epic:46` GOVERNANCE action items, both still `open`).

**BMAD artifacts (2)**

`_bmad-output/implementation-artifacts/51-2-categories-route-and-scope-chip.md` (this file), `_bmad-output/implementation-artifacts/sprint-status.yaml`.

**Fences verified empty** — `FacetSidebar.tsx`, `FilterRibbon.tsx`, `routes/catalog/$id.tsx`, `apps/api/**`, `workers/**`, `infra/**`, any migration, `package.json` / lockfiles, `deferred-work.md`. None appears in the change set (AC-21, AC-38, D-13).

---

## 15. Controller closeout + visual repair record — 2026-07-29

This section exists so the DS run is not credited with work it did not do.

### 15.1 What the `bmad-dev-story` run actually finished

It implemented the story: the route, the chip, the props cutover, the anchor conversion, the shell predicate, the `EmptyState` prop, the five i18n keys, and every unit/integration test except the visual spec. Its own evidence, before it stopped: **`TSC_RC=0`** and a full `npm run test` pass of **145 files / 913 tests**. It then hit `subtype=error_max_turns` **during final lint hygiene** — so it never cleared its own lint, and never authored the Story 51.2 visual coverage §7.6 owes. Applying the standing `epic:45` RECOVERY action item, the controller inspected the tree and repaired forward rather than restarting.

### 15.2 What the controller repaired

1. **Prettier blast radius.** A repo-wide Prettier invocation during the DS run's hygiene phase reformatted tracked files well outside this story. Every unrelated file was **restored**; the change set is back to the story's own blast radius. (This is the same repo-wide drift the 50.2 review characterised: there is no `.prettierrc`, so Prettier defaults to `printWidth: 80` against a codebase written at ~100, and `prettier` is not part of `npm run lint`.)
2. **Two `no-unused-vars` errors** — the deliberate destructure-to-discard of `category` in `routes/categories/$slug.tsx` and in `CatalogList.tsx`. Fixed with an explicit `void scopeLivesInThePath;` at each site, which keeps the "this is discarded on purpose" intent visible instead of hiding it behind a rename.
3. **One `react-refresh/only-export-components` warning** — `routes/catalog/index.tsx` now exports both a component and `validateCatalogSearch`. Fixed with a targeted `// eslint-disable-next-line` carrying the reason (`:63`), not by relaxing the rule and not by splitting the validator into a new module, which would have contradicted D-3's "no new module, no import ripple".
4. **The missing Story 51.2 visual coverage** — authored `tests/visual/category-browse.spec.ts` (2 pl-PL cases, each with a concrete `toBeVisible()` immediately before capture, per the `epic:45`/`epic:46` TEST-AUTHORING rule) and generated its 8 baselines; re-pointed `browse-rail.spec.ts`'s active case at `/categories/uchwyty` and repaired its role queries.

### 15.3 Controller gates — all rc=0

| Gate | Result |
|---|---|
| `npm run lint` | **rc=0** |
| `npx tsc -b` | **rc=0** |
| `npm run test` | **rc=0** — 145 files / **913 tests passed** |
| `npm run build` | **rc=0** — `routeTree.gen.ts` regenerated by the vite/TanStack plugin. Only the expected pre-existing route-file warnings and the Sentry auth-token warnings; nothing new. |
| targeted Playwright visual | **rc=0** — `npx playwright test --config=tests/visual/playwright.config.ts tests/visual/browse-rail.spec.ts tests/visual/category-browse.spec.ts --update-snapshots` → **22 passed, 10 skipped** (the 10 are `browse-rail.spec.ts`'s `skipOnMobile` cases, which are correct: the rail is `hidden … lg:flex` and the mobile Browse surface is Story 51.3). Added the 8 `category-browse` baselines, updated the 2 `browse-rail-active` desktop baselines. |
| `git diff --check` | **rc=0** |
| added-line static secret / dangerous-code scan | **rc=0** — `STATIC_SCAN_OK` |
| `laura-aider-review-diff` (Aider) | pass 1 **REQUEST_CHANGES** → follow-up **APPROVE** (§14.2) |

### 15.4 What was NOT run in the pre-commit controller repair pass

This subsection records the honest state **before** the later full closeout in §15.7. At the first controller repair checkpoint, repo-wide `npm run test:visual`, `infra/scripts/check-all.sh` 16/16, backend pytest, and the AC-37 determinism triple had not yet been run. That changed for AC-36 in §15.7: `check-all.sh` later ran all 16 stages, including repo-wide visual regression and backend pytest, and printed `CHECK_ALL_RC=0`. AC-37 remains unclaimed: no 3× consecutive identical vitest + pytest determinism triple was produced. `.hermes/run-logs/e51.2-*.log` tees from the DS story run were also not produced.

### 15.5 AC ledger at closeout

Satisfied and evidenced after §15.7: AC-1, AC-2, AC-4…AC-18, AC-19…AC-36 and AC-38. **AC-3 is accepted by reviewer/controller adjudication:** validation semantics and every shipped assertion remain intact; `routes/catalog/index.test.ts` changed only by Prettier-style line wrapping, while `routes/catalog/index.tsx` extracted/exports the same validator and adds the redirect path. **AC-37 not satisfied** (no determinism triple).

### 15.6 Still owed after the first controller repair checkpoint

This subsection is superseded by §15.7 for merge/deploy state. At first repair closeout, `check-all.sh`, repo-wide visual, commit, ff-merge, push, deploy and smoke were still owed. The later controller closeout completed those items. **Still not claimed:** AC-37 determinism triple.


### 15.7 Controller full closeout, merge, deploy and smoke — 2026-07-29

- Full aggregate gate: `.hermes/run-logs/check-all-e51-2-20260729_011714.log` printed `all green.` and `CHECK_ALL_RC=0 2026-07-29T01:28:04+02:00`: **16/16** stages passed, including apps/web visual regression **568 passed / 36 skipped**, apps/web vitest **145 files / 913 tests**, apps/api pytest, workers/render pytest, infra/scripts pytest, ruff/lock/env checks, typecheck, lint and production build. The Hermes process wrapper reported exit 1 because the remote shell printed `logout` after the rc marker; the script's own recorded rc is 0.
- Independent external review: `laura-aider-review-diff` follow-up verdict **APPROVE**. A later native BMAD code-review attempt was started but timed out without a verdict, so no native CR approval is claimed for this story.
- Commit / merge / push: `50446371e94fde774b08d6b22fa6a2ae07676809` (`feat(web): add category browse route`) was committed on `feat/E51.2-categories-route-scope-chip`, fast-forward merged to `main`, and pushed to `origin/main`; local `main` and `origin/main` both resolved to `5044637`.
- Deploy: `.hermes/run-logs/deploy-e51-2-20260729_013941.log` recorded `DEPLOY_RC=0 2026-07-29T01:43:52+02:00` and `last_deploy_sha=50446371e94fde774b08d6b22fa6a2ae07676809`. Images built/shipped, stack restarted, alembic ran. Slicer-worker overlay was correctly skipped (`no portal-api/slicer-adjacent change`). GlitchTip symbolication smoke matched issue id=320, top frame `apps/web/src/main.tsx`, release `0.1.0+5044637`; smoke issue deleted; runbook fingerprint OK. The Hermes process wrapper again reported exit 1 because of trailing `logout`, after the deploy script's own `DEPLOY_RC=0` marker.
- Post-deploy smoke by controller: `.190` compose showed api, arq-worker, redis, slicer-worker, web and worker **Up**; `http://192.168.2.190:8090/api/health` returned `{"status":"ok","version":"0.1.0"}`; LAN web `http://192.168.2.190:8090/` returned HTTP 200; production HTTPS `https://3d.ezop.ddns.net/` returned HTTP 200.
- Action-item closeout: the epic-51 handoff requiring the results heading + canonical `/categories/$slug` navigation and the 51.1 button-vs-Link divergence are discharged by this story. The E52 Filters-surface handoff remains open for Story 52.1; the 51.1 baseline-provenance governance item remains separate.

**Final status:** `done` by Laura/controller after green gates, Aider approval, ff-only merge, push, deploy and smoke. No human review or Ezop signature is claimed. AC-37 determinism triple remains unclaimed, but the controller accepted merge/deploy on the stronger `check-all.sh` 16/16 gate plus independent Aider approval.

---

## 16. Change log

| Date | Change | By |
|---|---|---|
| 2026-07-29 | Created via native `bmad-create-story` (CS) at `main` @ `f55bb9f`, after mandatory `bmad-help` routing. `VERIFY-AT-CREATE-STORY` traces performed at source for the route surface, `CatalogList`, `BrowseRail`, `ModuleRail`, `EmptyState`, the data layer, the i18n inventory and the coupled test surfaces (§2). | Claude (native BMAD), delegated by Laura/controller under standing Initiative 26 authorization |
| 2026-07-29 | Validated via native `bmad-create-story:validate` (VS). Verdict **PASS**; status `ready-for-dev` (§13). No code, no branch, no gate run, no commit/merge/deploy. **No `G26-DEVGO` issued by this pass.** | Claude (native BMAD) |
| 2026-07-29 | Implemented via native `bmad-dev-story` (DS) under a controller-issued `G26-DEVGO` on branch `feat/E51.2-categories-route-scope-chip` off `main` @ `f55bb9f`. Route, chip, props cutover, anchor conversion, shell predicate, `EmptyState` prop, five i18n keys and all unit/integration tests landed. Own evidence: `TSC_RC=0`; full vitest **145 files / 913 tests passed**. Run terminated `error_max_turns` **during final lint hygiene** — lint was left unclear and the §7.6 visual coverage was never authored. No `rc=0` may be cited for that session. | Claude Opus 5 (native `bmad-dev-story`) |
| 2026-07-29 | Controller closeout + repair (§15): restored the files an accidental repo-wide Prettier run touched outside this story; fixed the two `no-unused-vars` errors and the `react-refresh` warning; authored `tests/visual/category-browse.spec.ts` + 8 baselines; repaired `browse-rail.spec.ts`'s role queries and re-pointed its active case at `/categories/uchwyty` (2 baselines regenerated, triaged as intentional feature delta). Gates re-run, all rc=0: lint, `tsc -b`, `npm run test` 145/913, `npm run build` (routeTree regenerated by the vite plugin), targeted visual 22 passed / 10 skipped, `git diff --check`, static secret scan `STATIC_SCAN_OK`. Independent `laura-aider-review-diff` pass 1 **REQUEST_CHANGES** → follow-up **APPROVE**. Status `ready-for-dev` → `review`. **NOT `done`:** `check-all.sh`, repo-wide `test:visual`, the AC-37 determinism triple, commit, ff-merge, push, deploy and post-deploy smoke are all unrun (§15.4, §15.6). No human review of any kind — no Ezop signature; no Codex, no Gemini. | Laura/controller (Claude Opus 5) |
| 2026-07-29 | Bookkeeping-only pass: filled §11 task state, §14 Dev Agent Record, §16 closeout record and this change log; updated `sprint-status.yaml`. **This pass had no shell access** — it ran no gate, test, build or script, wrote no app code, and took no commit/stage/push/merge/deploy/migration/seed/live-DB/network action. Every gate figure above is controller-reported; every source claim was read directly from the working tree. It edited exactly two files: this artifact and `sprint-status.yaml`. | Claude Opus 5 (bookkeeping) |
| 2026-07-29 | Controller full closeout after the first commit: `check-all.sh` 16/16 all green (`CHECK_ALL_RC=0`), ff-only merge to `main`, push to `origin/main`, deploy `DEPLOY_RC=0`, `.last-deploy-sha=50446371e94fde774b08d6b22fa6a2ae07676809`, GlitchTip symbolication/runbook OK, .190 compose/web/API and production HTTPS smokes OK. Status `review` → `done`. Native BMAD code-review attempt timed out with no verdict; independent Aider follow-up remained **APPROVE**. No human review or Ezop signature claimed. | Laura/controller |
