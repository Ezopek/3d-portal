---
baseline_commit: 0f722d270ae30d97423e6b1d2ceb71d59975b785
---

# Story 51.1 — Desktop browse navigation (FR26-BROWSE-1, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1, NFR26-DARKMODE-1)

- **Epic:** E51 — Browse IA: categories as navigation (Initiative 26 — Catalog Discovery). **This is the one user-visible cutover in Initiative 26.**
- **Status:** `review` — implemented 2026-07-28 by native `bmad-dev-story` (DS) on branch `feat/E51.1-desktop-browse-navigation`, under Laura/controller **G26-DEVGO** (standing Initiative 26 authorization). All 12 tasks complete, all 27 ACs satisfied. Native BMAD CR and independent Aider review both approved; the aggregate `check-all.sh` closeout gate is green (§16–§18). Not yet committed, pushed, merged, or deployed at this artifact update point.
- **Author:** Claude (native `bmad-create-story`, Create + Validate). **Controller:** Laura.
- **Authorization posture, stated plainly:** this create + validate pass was delegated by **Laura/controller under the standing Initiative 26 authorization**. **G26-DEVGO is recorded here as Laura/controller authorization under that standing Initiative 26 authorization** — it is **NOT** an Ezop signature, **NOT** Ezop review, and **NOT** human review of any kind. No human reviewed this artifact. No Codex, no Gemini, no Aider participated. No app code was written, no gate/test/build/script was run, no branch was created, and no commit / stage / push / merge / deploy / migration / seed / live-DB / network action was taken. This pass edited exactly two files: this artifact and `sprint-status.yaml` status fields.
- **Created:** 2026-07-28 via native `bmad-create-story` after a mandatory `bmad-help` run. Canonical route from `_bmad/_config/bmad-help.csv:26-28`: `bmad-create-story:create` (**CS**, phase `4-implementation`, `preceded-by bmad-sprint-planning` — done, `required=true`) → `bmad-create-story:validate` (**VS**) → `bmad-dev-story` (**DS**) → `bmad-code-review` (**CR**).
- **Duplicate check:** `ls _bmad-output/implementation-artifacts/ | grep -E '^51'` returned nothing; no `spec-*` artifact matched `51`/`browse`. No pre-existing story or spec duplicate for 51.1 existed before this pass.
- **Sprint-status readback:** `sprint-status.yaml` read start-to-end. `epic-51: backlog`; `51-1-desktop-browse-navigation: backlog` is the **first** `backlog` story key under `epic-51` and the canonical next story. (`42-3`, `42-5`, `47-4` remain `backlog` under epics already closed `done` by recorded operator/controller scope decisions — they are deferred, not next.) Per the CS workflow's first-story rule, `epic-51` flips `backlog` → `in-progress` with this story.
- **Scope class:** **frontend-only, user-visible IA cutover** on the already-shipped `/catalog/` route. One new component, one relocated mount, first consumer of the shipped `useCategories()` hook. **No** backend change, **no** new endpoint, **no** migration, **no** new dependency, **no** route file, **no** `routeTree` regeneration, **no** codegen.
- **Sources of truth:** `epics.md` §E51 Story 51.1 (`:4519-4529`); `prd.md` FR26-BROWSE-1 (`:2250`) + NFR26 block (`:2264-2270`); `architecture.md` § Initiative 26 Decision AY (`:3303-3345`); UX artifact `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` — `DESIGN.md` (`:68-89` component tokens, `:239-242` breakpoints/geometry, `:264-273` component specs, `:293-302` do/don't), `EXPERIENCE.md` (`:50-53` surface map, `:62` nesting rule, `:202` terminology, `:219-228` interaction table, `:242-253` cold/empty/error states, `:268-283` + `:315-324` a11y, `:328-335` responsive); shipped code at `main` @ `0f722d2`; in-repo precedents `50-1-fe-types-and-hooks.md`, `50-2-url-state-category-scope.md`, `50-3-inline-structured-suggestions.md` (all `done`).

---

## 1. Story statement

**As** a catalog user standing at `/catalog` on a desktop viewport,
**I want** the persistent left column to be a short list of **broad browse categories** with their sizes — instead of the deep facet-tag tree it renders today —
**so that** navigation answers *"what kind of thing do I want?"* and the tag taxonomy is demoted to refinement, which is the entire point of Initiative 26's browse-vs-filter split.

**FR mapping — FR26-BROWSE-1** (`prd.md:2250`): *"Desktop left navigation lists only broad categories with optional counts… Facets and tags move into a `Filters (n)` drawer/panel… full tag search remains inside Filters."*
Verifiable, quoted: **(a)** the default `/catalog` left rail renders **categories only**; **(b)** **every tag group stays reachable within one interaction from `Filters`**.

This story delivers (a) in full and (b) as a **verbatim relocation** of the shipped facet surface (§4 D-2). The *consolidated* `Filters (n)` drawer — badge count, promoted groups, tag search inside the panel — is **Story 52.1** and is fenced out here (§10).

---

## 2. `VERIFY-AT-CREATE-STORY` — `FacetSidebar.tsx` traced against shipped code at `0f722d2`

> The epic sketch (`epics.md:4529`) mandates: *"trace `FacetSidebar.tsx`'s actual mount points, props and consumers **at that time**; whether the component is relocated into the Filters surface or re-rendered there is a story-level decision against then-current code, **not** an assumption carried from this sketch."* This is the standing `epic:47` stale-precondition action item (`sprint-status.yaml` action_items, epic 47, `status: open`) — a story sketch's stated precondition has been stale against shipped code **three times** in this repo. Everything below was re-read at source in this run; nothing is carried from the sketch.

**Command run:** `grep -rn "FacetSidebar" apps/web/src apps/web/tests` (node_modules excluded). Full result set, classified:

### 2.1 The component itself

| Fact | Evidence |
|---|---|
| Path | `apps/web/src/modules/catalog/components/FacetSidebar.tsx` (228 lines, 8381 bytes, mtime 2026-07-19) |
| Single export | `export function FacetSidebar(...)` at `FacetSidebar.tsx:40` — the file's **only** export, deliberately, so `react-refresh/only-export-components` stays quiet (`:10-14` comment) |
| Renders | An `<aside>` containing: a tag-search `Input`, collapsible **tag-group** sections, per-tag **checkboxes** with `model_count`, and a trailing `Untagged models` checkbox (`:106-192`) |
| It renders **no** category | Confirmed by reading the whole file — it consumes `TagGroupRead[]` + `TagReadWithCount[]` only |

### 2.2 Props — the exact current interface (`FacetSidebar.tsx:19-32`)

```ts
interface Props {
  groups: TagGroupRead[];
  groupless: TagReadWithCount[];
  selectedTagIds: string[];
  onToggleTag: (id: string) => void;
  untaggedActive: boolean;
  onToggleUntagged: () => void;
  untaggedCount?: number;
  mobile?: boolean;   // omits the desktop-only wrapper; adapts for Sheet slotting
}
```

Responsive behavior is **prop-driven, inside the component** (`FacetSidebar.tsx:101-103`):

```ts
const asideClassName = mobile
  ? "flex w-full flex-col bg-card p-4"
  : "hidden w-60 shrink-0 flex-col border-r border-border bg-card p-4 lg:flex";
```

Module-local, unexported, and load-bearing for tests: `STORAGE_KEY = "catalog:facet-collapse"` (`:9`), `DEFAULT_EXPANDED_GROUP_COUNT = 2` (`:14`), `GROUPLESS_ID = "__groupless__"` (`:17`).

### 2.3 Mount points — exactly TWO, both in ONE file

**`apps/web/src/modules/catalog/routes/CatalogList.tsx` is the only file that imports it** (`CatalogList.tsx:6`). There is no other consumer anywhere in `src/`.

| # | Location | Shape | Viewport |
|---|---|---|---|
| **M1** | `CatalogList.tsx:183-190` | Standalone, **no** `mobile` prop → renders the `hidden … lg:flex` `<aside>`; first child of the route's outer `<div className="flex">` (`:182`) | **Desktop only** (`lg`+) |
| **M2** | `CatalogList.tsx:205-213` | Inside `<SheetContent side="left" className="w-80 max-w-[85vw] …">` (`:201`), with `mobile` set (`:212`); the whole `Sheet` block sits in a wrapper carrying **`lg:hidden`** (`:192`) | **Below `lg` only** |

Both mounts are fed **identical** props: `tagGroups.data.groups`, `tagGroups.data.groupless`, `search.tag_ids ?? []`, `toggleTag`, `search.untagged ?? false`, `toggleUntagged`. **Neither** mount passes `untaggedCount` — that optional prop has **no** production caller today (only `FacetSidebar.test.tsx` exercises it).

M2's trigger is a `Button` labelled `t("catalog.filters.openTags")` (`CatalogList.tsx:197`) → `"Tags"` / `"Tagi"`.

### 2.4 Coupled consumers that must not be broken

| Consumer | Coupling | Consequence for this story |
|---|---|---|
| `CatalogList.tsx:127` | Comment: the `tagGroups.data === undefined` fatal guard (`:152`) exists *specifically* so `FacetSidebar` never paints with empty group data | Guard must keep its current shape; the **category** query must **not** join it (§4 D-8/D-9) |
| `FacetSidebar.test.tsx` | 1 unit suite, renders the component directly with `ComponentProps<typeof FacetSidebar>` overrides (`:48-58`) | Untouched — no prop or behavior change (§4 D-1) |
| `tests/visual/facet-filtering.spec.ts:126-136` | `skipOnMobile()` exists **because** *"FacetSidebar's standalone `<aside>` renders desktop-only (`hidden lg:flex`); mobile uses the Sheet-triggered instance"* | **BREAKS.** After D-2 there is no desktop standalone `<aside>`. **This story must repair the spec** (§7.5) |
| `tests/visual/facet-filtering.spec.ts:207-211` | Comment contrasts the desktop-only `<aside>` with FilterRibbon's unconditional render | Comment becomes false; repaired with the same edit |
| `tests/visual/remaining-sheets-open.spec.ts:106` | Comment names `catalog.filters.openTags` = `"Tagi"` as *"the FacetSidebar SheetTrigger label"* | Trigger survives verbatim (D-2), only its breakpoint gate widens — verify the spec still passes; do not pre-emptively edit |
| `TagGroupsSection.tsx:9,37`, `sheets/EditTagsSheet.tsx:15,84` | **Comment-only** references to FacetSidebar's independently-defined `GROUPLESS_ID` and pl-label fallback | No code coupling. Do not touch. |

### 2.5 The `Filters` surface as it actually exists today — the decisive finding

The epic and `EXPERIENCE.md:228` both talk about relocating facets *"into the `Filters (n)` surface"*. **That surface does not exist yet.** Traced at source:

- `FilterRibbon.tsx:152-179` has a `Sheet` whose trigger is `catalog.filters.openFilters` (`"Filters"`/`"Filtry"`) — but its trigger `Button` carries **`md:hidden`** (`:158`), and its content is **`FilterSelects` only**: status, source, sort (`:176`). It contains **no tags at all**.
- `activeFilterCount()` (`FilterRibbon.tsx:53-59`) counts status + source + non-default sort. It already **excludes** `tag_ids` and — correctly — has no notion of `category`.
- The only always-visible tag path in the ribbon is the `+ tag` `TagPicker` popover (`FilterRibbon.tsx:99-115`, `:275-352`), which is **search-by-name**, with **no group structure**.
- `catalog.filters.title` (`"Filters"`/`"Filtry"`) is that mobile sheet's `SheetTitle` (`FilterRibbon.tsx:173`).

**Therefore:** the grouped-facet surface that FR26-BROWSE-1's verifiable (b) requires to stay reachable is **the `FacetSidebar` itself** — nothing else in the shipped app renders tag *groups*. Deleting M1 without relocating it would strand desktop users with no grouped-facet path at all until Story 52.1 lands. That constraint drives Decision **D-2**.

### 2.6 The shipped data layer this story consumes (first reader)

| Artifact | Path | State |
|---|---|---|
| `useCategories()` | `hooks/useCategories.ts:13-19` — `useQuery<BrowseCategoryRead[]>`, key `["sot","categories"]`, `queryFn: api("/categories")`, `staleTime: 5 * 60 * 1000` | Shipped by 50.1. **Zero production consumers today** — this story is its first reader |
| `BrowseCategoryRead` | `lib/api-types.ts:116-120` extends `BrowseCategorySummary` (`:102-109`) → `{ id, slug, name_en, name_pl, position, parent_id, description_en, description_pl, model_count }` | `model_count` is **required and unconditional** (`:112-113`) |
| `CatalogSearch.category?: string` | `routes/catalog/index.tsx:46` + validator branch `:105-108` (trim, drop-if-empty, single slug, array dropped wholesale) | Shipped by 50.2 |
| `useModels({ category })` | wired at `CatalogList.tsx:47` | Shipped by 50.2 — the scope already reaches the backend |
| `Clear filters` preserves `category` | `CatalogList.tsx:259-264`, `:290-298` | Shipped by 50.2, with the comment naming 51.2 as the clearing story |
| `useCategoryBySlug()` | `hooks/useCategoryBySlug.ts` | Shipped by 50.1; **not used by this story** — it serves 51.2's route |

`GET /api/categories` returns a **flat list ordered `(position, slug)`**, **includes empty categories**, and is authenticated default-deny (`architecture.md:3309`, `:3307`).

### 2.7 Trace conclusion — the story-level decision this evidence forces

`FacetSidebar` is **not** relocated *into a Filters panel* in this story, because no such panel exists at `0f722d2`. It is **relocated into the shipped Sheet mount it already has (M2)**, by widening that mount's breakpoint gate. M1 (the desktop `<aside>`) is removed and its column is taken by the new `BrowseRail`. See **D-2** for the decision, its cost, and its 52.1 handoff.

---

## 3. Additive scope — the implementable-green target

### 3.1 NEW — `apps/web/src/modules/catalog/components/BrowseRail.tsx`

A new presentational component. **Single export** (`BrowseRail`) so `react-refresh/only-export-components` stays satisfied under `--max-warnings=0` — the same constraint `FacetSidebar.tsx:10-14` records.

```ts
interface Props {
  categories: BrowseCategoryRead[];
  activeSlug: string | undefined;   // undefined => "All catalog" is current
  onSelect: (slug: string | undefined) => void;   // undefined => clear scope
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}
```

Geometry, verbatim from `DESIGN.md:239-242` + `:268`: `<nav>` column, `hidden w-60 shrink-0 flex-col border-r border-border bg-card lg:flex`. This is the **exact** geometry `FacetSidebar`'s `<aside>` occupies today (`FacetSidebar.tsx:103`) and the exact geometry the shipped `ModuleRail` uses (`ModuleRail.tsx:22`), so the cutover is a swap in one column, not a grid reflow.

Row vocabulary (`DESIGN.md:268-271`, `EXPERIENCE.md:219-220`):
- First row is **always** "All catalog", then categories in the order the API returns them (`(position, slug)` — do **not** re-sort client-side; the backend owns the order per `architecture.md:3309`).
- Each row is a full-width button, `min-h-9`, `rounded-md` — the whole row is the hit target. **Never a checkbox.**
- Active row: `bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary` — **copy this class string from `ModuleRail.tsx:34`**, do not re-derive it. `DESIGN.md:269` explicitly requires identity with the shipped `ModuleRail` active treatment.
- Inactive row: `text-muted-foreground hover:text-foreground` (`ModuleRail.tsx:35`).
- Count: `text-xs tabular-nums text-muted-foreground`, no badge, no pill, no background (`DESIGN.md:270`, `:230`).
- `model_count === 0` → label at 60% muted (`text-muted-foreground/60`), **still focusable, still navigable, never hidden** (`DESIGN.md:271`, `EXPERIENCE.md:219`).
- Bilingual label fallback — mirror `FacetSidebar.tsx:74,80-81` exactly: `preferPl && item.name_pl ? item.name_pl : item.name_en`. Empty string is a valid `name_pl` on the wire and must fall back, or a pl-locale row renders blank.
- `parent_id` is **ignored**. MVP browse is flat (`FR26-CAT-4`; `EXPERIENCE.md:186`). No tree, no nesting, no indentation.

### 3.2 UPDATE — `apps/web/src/modules/catalog/routes/CatalogList.tsx`

1. Import `BrowseRail` + `useCategories`; call `const categories = useCategories();`.
2. **Replace** the M1 `FacetSidebar` block (`:183-190`) with `<BrowseRail …/>` as the first child of the outer `flex` div.
3. **Promote** the M2 wrapper (`:192`) from `className="… lg:hidden"` to all breakpoints (drop `lg:hidden`; keep the rest). The `Sheet`, its trigger label, `SheetContent side="left" className="w-80 max-w-[85vw]"`, and the `mobile`-prop `FacetSidebar` inside it are **unchanged**.
4. Add `setCategory(slug: string | undefined)` alongside the existing `toggleTag` / `toggleUntagged` / `setPage` navigators — same shape: `navigate({ search: (prev) => ({ …prev, category: slug, page: undefined }), replace: true })`.
5. **Do not** add `categories` to either fatal guard (`:136` error, `:152` loading). See D-8/D-9.

### 3.3 UPDATE — `apps/web/src/locales/en.json` + `pl.json`

Three new keys, both files, same key set (flat-key convention, 906 keys each today):

| Key | `en` | `pl` |
|---|---|---|
| `catalog.browse.railLabel` | `Browse categories` | `Przeglądaj kategorie` |
| `catalog.browse.allCatalog` | `All catalog` | `Cały katalog` |
| `catalog.browse.categoryWithCount` | `{{name}}, {{count}} models` | `{{name}}, modeli: {{count}}` |
| `catalog.browse.categoryWithCount_one` | `{{name}}, {{count}} model` | `{{name}}, model: {{count}}` |
| `catalog.browse.categoryWithCount_few` | `{{name}}, {{count}} models` | `{{name}}, {{count}} modele` |
| `catalog.browse.categoryWithCount_many` | `{{name}}, {{count}} models` | `{{name}}, {{count}} modeli` |
| `catalog.browse.categoryWithCount_other` | `{{name}}, {{count}} models` | `{{name}}, {{count}} modelu` |

Terminology is **fixed by `EXPERIENCE.md:202`**: "Przeglądaj" / "Browse". `"Odkrywaj"` and `"Eksploruj"` are explicitly rejected — this is a private tool, not a storefront. `catalog.browse.categoryWithCount` supplies the row's accessible name so a screen reader hears label + count as **one** item (`EXPERIENCE.md:220`).

**Reuse, do not re-add:** `errors.network` and `common.retry` already exist and are already used by this very route (`CatalogList.tsx:139,141`). The rail's error state uses them.

### 3.4 UPDATE — `apps/web/tests/visual/api-stubs.ts`

`stubSotList()` gains a `**/api/categories*` route stub with a default fixture and an `opts.categories` override, following the established `opts.tags` / `opts.tagGroups` pattern (`api-stubs.ts:162-186`). Without it, every existing `/catalog` visual test would hit an unstubbed route the moment `useCategories()` mounts — violating *"No real network in any test"* (`project-context.md:120`).

---

## 4. Resolved decisions — each with its cost stated

**D-1 — `BrowseRail` is a NEW component; `FacetSidebar.tsx` is NOT modified.**
The two render different entities with different semantics (navigation vs refinement), different interaction models (navigate-and-replace vs multi-select toggle), and different colour vocabularies (`DESIGN.md:203-204`: primary = *location*, accent = *constraint you chose* — and the rail uses primary **precisely because** accent would collide with the tag chips). Generalizing one component over both would be the "reinvent/overload" failure. *Cost:* one more file (~110 lines). *Benefit:* `FacetSidebar.tsx`, `FacetSidebar.test.tsx`, and its `localStorage` collapse contract keep a zero-diff surface.

**D-2 — M1 is removed; M2 is promoted to all breakpoints. Relocation, not deletion.**
FR26-BROWSE-1's second verifiable requires every tag group to stay reachable within one interaction. §2.5 proves `FacetSidebar` is the **only** grouped-facet surface shipped, and that the existing `Filters` sheet (`FilterRibbon.tsx:152-179`, `md:hidden`, status/source/sort only) cannot satisfy it. Widening M2's gate makes the shipped grouped-facet surface reachable in **one** click on every viewport, from a control that already exists and is already translated, with **zero** change to `FacetSidebar`'s props or behavior.
*Cost, stated honestly:* on desktop the facets go from always-visible to one-click-away, and the interim trigger is labelled `Tags` / `Tagi` (`catalog.filters.openTags`) rather than `Filters (n)`. `EXPERIENCE.md:331` also puts the eventual desktop Filters surface on the **right**, whereas the reused sheet is `side="left"`. Both divergences are **intentionally left for Story 52.1**, which owns the consolidated `Filters (n)` surface (badge, promoted groups, in-panel tag search, final side/presentation). Re-siding or re-labelling the sheet here would be scope creep into 52.1 and would be redone within one epic.
*Rejected alternative — delete M1 outright:* leaves desktop with no grouped-facet path until 52.1; fails verifiable (b). *Rejected alternative — build the real `Filters (n)` panel now:* that is Story 52.1 in full, including the `(n)` semantics that must exclude category scope.

**D-3 — Rail rows write `?category=<slug>` on `/catalog`. They do NOT link to `/categories/$slug`.**
That route does not exist at `0f722d2` and is **Story 51.2**'s deliverable (`epics.md:4531`), including its `routeTree` regeneration. The `category` search-param layer shipped in **50.2** (`routes/catalog/index.tsx:46,105-108`) and is already wired to `useModels` (`CatalogList.tsx:47`), so the rail is fully functional today with no dead links and no route work. *Cost:* the canonical URL changes shape when 51.2 lands. *Mitigation:* 51.2 owns that transition and the scope chip; this story's `setCategory` navigator is exactly the seam it will re-point.

**D-4 — "All catalog" clears **only** `category`.**
`setCategory(undefined)` spreads `prev` and overwrites `category` alone, resetting `page`. `q`, `tag_ids`, `tag_match`, `untagged`, `status`, `source`, `sort` all survive. This is the mirror image of the shipped 50.2 rule that `Clear filters` must not drop the scope (`CatalogList.tsx:259-264`) — scope and filters are independent layers (FR26-BROWSE-2/3), and each clearing control clears exactly its own layer.

**D-5 — Counts are `model_count` from `GET /api/categories` and are NOT filter-aware.**
`EXPERIENCE.md:220`, quoted: *"It answers 'how big is this category', never 'how many match my current filters'. A story must not silently make it reactive to `q`/`tag_ids`."* Do **not** pass `q`/`tag_ids` into the category query; do **not** derive counts from the model page.

**D-6 — The rail is desktop-only (`hidden … lg:flex`). Mobile keeps exactly what it has today.**
The mobile Browse surface is **Story 51.3** (`epics.md:4535`, `EXPERIENCE.md:53`), and it carries an explicit `Ask First` boundary about the mobile `ModuleRail`. Below `lg` this story changes nothing except that the shipped Tags sheet trigger — already visible on mobile — is now also visible on desktop. The mobile bottom `ModuleRail` is **untouched** (`EXPERIENCE.md:292,335`).

**D-7 — No focus relocation on category selection.**
`EXPERIENCE.md:324` asks that navigating to a category move focus to the *results heading*. There is **no results heading** in `CatalogList.tsx` at `0f722d2` — it is introduced with the scope chip and the `/categories/$slug` route in **Story 51.2** (`EXPERIENCE.md:222`). Selecting a rail row here is a same-route search-param change; focus correctly stays on the activated row, so a keyboard user does not re-traverse anything. Inventing a heading now would collide with 51.2's chip. **Handoff recorded in §12** so 51.2 owns it rather than it being silently dropped.

**D-8 — A failed category read must NOT blank the catalog.**
`EXPERIENCE.md:253`: *"Rail degrades to 'All catalog' + inline retry; the grid stays fully usable. The catalogue must never become unreachable because a navigation aid failed."* Therefore `categories.isError` must **not** be added to `CatalogList.tsx:136`. The rail's own `onRetry` calls `categories.refetch()`. This mirrors the shipped, deliberate treatment of `tags` (`CatalogList.tsx:130-135`) — a non-fatal query that degrades gracefully rather than blanking the grid.

**D-9 — A pending category read must NOT blank the catalog.**
`EXPERIENCE.md:242`: *"The rail resolving is **independent** of the grid — a pending category list must never blank an already-painted grid."* Therefore `categories.data === undefined` must **not** be added to `CatalogList.tsx:152`. The rail renders skeleton rows sized to the row height while `isLoading`. The existing `tagGroups`/`models` guard keeps its current shape verbatim — including its `:125-135` comment, which explains why it guards on data presence rather than `isLoading`.

**D-10 — Empty category list renders "All catalog" alone.** No error, no empty-state copy (`EXPERIENCE.md:250`). This is the true state between Stories 49.1 and 49.2 and must not read as a failure.

**D-11 — Sheet nesting invariant.** `EXPERIENCE.md:62`: a `Sheet` never opens another `Sheet`. The promoted Tags sheet and `FilterRibbon`'s status/source/sort sheet are siblings in the DOM, never nested. The "opening one closes the other" coordination is part of the **52.1** consolidation (they cannot be simultaneously open on the same viewport today: the Filters sheet trigger is `md:hidden`, and both are one-at-a-time modal sheets); do not build cross-sheet coordination state here.

---

## 5. Cache-coherence enumeration (mandatory — `project-context.md:286`)

| Dimension | `useCategories()` (`["sot","categories"]`) | `useModels(...)` (`["sot","models",…filters]`) |
|---|---|---|
| **Staleness budget** | `staleTime: 5 * 60 * 1000`, **already shipped and justified** at `useCategories.ts:6-12`: browse categories are admin-governed reference data (FR26-CAT-1), mutated only via the 49.5 admin endpoints, never on the member browse path. The rail is navigation chrome, not a correctness surface — a ≤5-min window between an admin edit and a member's refetch is the accepted budget. **This story does not change it**, and must not: the constant points at the contract it serves, not at a neighbouring number (`project-context.md:287`). | Unchanged by this story. |
| **Retry policy** | TanStack Query default. On error the rail renders an **inline** retry that calls `categories.refetch()` (D-8). | Unchanged — the shipped `EmptyState` retry at `CatalogList.tsx:141-147` keeps its current three refetches. Do **not** add `categories.refetch()` to it; the rail owns its own recovery, and the fatal-guard branch is for a blanked grid. |
| **Cache propagation (mutations)** | **None.** This story is read-only — no category mutation exists on any member surface. Admin writes (52.2) will invalidate `["sot","categories"]`; the key is deliberately a **prefix** of `useCategoryBySlug`'s so one `invalidateQueries` refreshes both (`useCategories.ts:10-12`). | n/a |
| **Cache eviction on route exit** | None, and none wanted. Reference data cached across `/catalog` visits is the point; there is no per-user or per-token contamination risk of the kind Story 30.2 hit with share-seeded caches (`project-context.md:286`) — the read is authenticated default-deny with no token-scoped variant. | Unchanged. |
| **Cache seeding on this route** | The rail is the **first** consumer of `["sot","categories"]` in the app. It seeds; nothing else reads it yet. 51.2's `useCategoryBySlug` will populate the sibling key independently. | Unchanged. |

**Conflict check:** none. The two queries have disjoint keys, disjoint staleness contracts, and — by D-8/D-9 — deliberately disjoint failure blast radii. No column disagrees, so no design choice needs naming.

---

## 6. Acceptance criteria

**Rail composition and ordering**

- **AC-1** — At `lg`+ on `/catalog`, the first column is a `<nav>` rendering **only** browse categories. No tag group, no tag, no tag checkbox, and no `Untagged models` row appears anywhere in that column.
- **AC-2** — The `<nav>` carries an accessible name from `catalog.browse.railLabel`, distinct from the app's `ModuleRail` (`EXPERIENCE.md:219`).
- **AC-3** — The first row is always `catalog.browse.allCatalog`; category rows follow **in API order**, with no client-side re-sort.
- **AC-4** — Each category row shows its label (pl fallback per §3.1) and its `model_count`, styled `text-xs tabular-nums text-muted-foreground` with no badge/pill/background.
- **AC-5** — `parent_id` is not rendered, not indented, and not used to build a tree.

**Selection semantics**

- **AC-6** — Activating a category row navigates on `/catalog` with `?category=<slug>`, `page` reset, and `q`/`tag_ids`/`tag_match`/`untagged`/`status`/`source`/`sort` **preserved**.
- **AC-7** — Selecting a row **replaces** the scope; two categories can never be active at once (`EXPERIENCE.md:219`).
- **AC-8** — Activating "All catalog" removes **only** `category` and resets `page`; every other search param survives (D-4).
- **AC-9** — The row whose slug equals `search.category` renders active — `bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary`, byte-identical to `ModuleRail.tsx:34` — and carries `aria-current="page"` (`EXPERIENCE.md:315`). When `search.category` is `undefined`, "All catalog" is the active row. **Exactly one** row is active at any time.
- **AC-10** — Rows are not checkboxes and expose no multi-select affordance.

**States**

- **AC-11 (cold load)** — While the category read is pending the rail shows skeleton rows sized to the row height, and the model grid renders normally (D-9).
- **AC-12 (empty)** — An empty category list renders "All catalog" alone: no error, no empty-state copy (D-10).
- **AC-13 (error)** — A failed category read renders "All catalog" plus an inline retry using the existing `errors.network` + `common.retry` keys; the grid stays fully usable and the retry calls `categories.refetch()` (D-8).
- **AC-14 (empty category)** — A `model_count === 0` row renders dimmed (60% muted) but remains focusable, navigable, and present.

**Facet relocation**

- **AC-15** — The desktop standalone `FacetSidebar` `<aside>` (M1) no longer renders at any viewport.
- **AC-16** — The Sheet-mounted `FacetSidebar` (M2) is reachable in **one** interaction at **every** viewport, from the shipped `catalog.filters.openTags` trigger, and renders the same tag groups, per-tag counts, group search, collapse state and `Untagged models` row it renders today.
- **AC-17** — `FacetSidebar.tsx` has a **zero-line** diff. Its props, `STORAGE_KEY`, `DEFAULT_EXPANDED_GROUP_COUNT` and `GROUPLESS_ID` are unchanged.
- **AC-18** — The mobile experience below `lg` is unchanged apart from the rail's absence there; the mobile bottom `ModuleRail` is untouched.

**i18n / a11y / visual / theming**

- **AC-19** — The seven new keys (three base rail keys plus four `categoryWithCount_*` plural forms) exist in **both** `en.json` and `pl.json` with genuine, non-identical Polish; a key-set diff is recorded at close (NFR26-I18N-1). No user-visible string is hard-coded.
- **AC-20** — Every rail row is a keyboard-reachable control with a ≥24×24 CSS px target (`min-h-9` = 36px) (NFR26-A11Y-1 / WCAG 2.2 SC 2.5.8). No hover-only affordance; no path-based or drag-only interaction (SC 2.5.1 / 2.5.7).
- **AC-21** — Each row's accessible name carries label **and** count as one item via `catalog.browse.categoryWithCount` (`EXPERIENCE.md:220`).
- **AC-22** — The rail is reachable by `Tab`, is not a focus trap, and does not steal focus on navigation (`EXPERIENCE.md:283`). Tab order is rail → toolbar → grid → pagination (`:278`).
- **AC-23** — Zero colour literals; every colour is a Tailwind class over a `theme.css` token; correct in light **and** dark (NFR26-DARKMODE-1).
- **AC-24** — Targeted **pl-PL** Playwright coverage exists for default, active, empty-category, cold-load and error states, each with an explicit `toBeVisible()` **before** every `toHaveScreenshot` (NFR26-VISUAL-1; `epic:45`/`epic:46` TEST-AUTHORING action items).
- **AC-25** — `tests/visual/facet-filtering.spec.ts`'s desktop-`<aside>` premise (`:126-136`, `:207-211`) is repaired, not merely re-baselined (§7.5).

**Non-regression**

- **AC-26** — `check-all.sh` is green: `npm run lint --max-warnings=0`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run test:visual` (all 4 projects), plus the untouched pytest suites.
- **AC-27** — NFR26-DETERMINISM-1: 3× consecutive identical vitest + pytest pass counts before merge.

---

## 7. Test strategy

### 7.1 NEW — `src/modules/catalog/components/BrowseRail.test.tsx`

Unit, presentational. Must include `import { cleanup } from "@testing-library/react"; afterEach(cleanup);` — `vitest.config.ts` sets `globals: false`, so auto-cleanup does **not** register and multi-`it` files otherwise fail with `Found multiple elements` (`project-context.md:115`).

Covers: API-order rendering without re-sort (AC-3); "All catalog" first (AC-3); count rendering + `tabular-nums` (AC-4); `aria-current="page"` on exactly one row, both when a slug is active and when it is not (AC-9); `onSelect(slug)` / `onSelect(undefined)` payloads (AC-6/AC-8); dimmed-but-focusable zero-count row (AC-14); `isLoading` skeleton (AC-11); empty list → All-catalog-only (AC-12); `isError` → retry control invoking `onRetry` (AC-13); `name_pl: ""` falls back to `name_en` under a pl locale (§3.1); accessible name includes the count (AC-21); `parent_id` produces no nesting (AC-5).

### 7.2 UPDATE — `src/modules/catalog/routes/CatalogList.test.tsx`

Extend the shipped harness (memory router + `fetch` stub over `json()`; **never** mock `api()` — `project-context.md:114,252`). Add a `/api/categories` branch to the fetch stub.

Covers: rail mounts and M1 `FacetSidebar` `<aside>` is gone (AC-1/AC-15); clicking a row writes `?category=<slug>` while preserving a pre-set `q` + `tag_ids` (AC-6); "All catalog" clears only `category` (AC-8); a failed `/api/categories` leaves the grid rendered (AC-13/D-8); a pending `/api/categories` leaves the grid rendered (AC-11/D-9); the Tags sheet trigger is present and opens the grouped facet surface (AC-16).

### 7.3 NEW — `src/modules/catalog/browse-i18n.test.ts`

Key-set-diff guard for the three new keys, following the shipped pattern in `src/modules/catalog/suggestions-i18n.test.ts` and `src/modules/admin/tag-groups-i18n.test.ts`. Asserts presence in both files, and that the Polish value is not identical to the English one (NFR26-I18N-1). The repo-wide `tests/i18n.test.ts` parity check must stay green.

### 7.4 NEW — `tests/visual/browse-rail.spec.ts`

pl-PL, all four projects, using `stubSotList` + the new categories stub. Desktop-only assertions gate with a `skipOnMobile`-style helper mirroring `facet-filtering.spec.ts:129-135` (the rail is `hidden … lg:flex`), with an **accurate** skip reason. Baselines: default rail, active category row, dimmed zero-count row, cold-load skeleton, error + retry — each preceded by an explicit `toBeVisible()` on the specific element under test (AC-24).

### 7.5 UPDATE — `tests/visual/facet-filtering.spec.ts` (mandatory repair, not a re-baseline)

`skipOnMobile()` (`:126-136`) and the contrast comment (`:207-211`) both assert a desktop-only standalone `<aside>` that D-2 removes. Re-point the suite at the Sheet-mounted instance: open the `catalog.filters.openTags` sheet, then run the existing default / collapsed / untagged assertions against it. If the suite now runs on all four projects, the skip helper is deleted rather than left with a false reason. **Classify each resulting baseline change as `stale-baseline` before any `--update-snapshots`** — per the Init 10 Murat triage rule (`AGENTS.md` § Conventions, "Visual baseline triage before regen"), a blanket regen here would mask a real IA regression. Every regenerated PNG needs a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line naming **the agent that actually inspected it** — never a human who did not (`epic:45`/`epic:46` GOVERNANCE action items, both still `open`).

### 7.6 Expected baseline movement (triage list, authored up front)

`catalog-list.spec.ts`, `catalog-search-suggestions.spec.ts`, `empty-states.spec.ts`, `filter-ribbon-selects-open.spec.ts`, `accessibility-axe.spec.ts`, `focus-ring.spec.ts` and any other `/catalog`-mounting desktop spec will shift, because the desktop left column changes content. All are expected `stale-baseline` (intentional IA cutover). Any **mobile** `/catalog` baseline that moves is **not** expected — D-6 says mobile is unchanged below `lg` — and must be treated as `deterministic-fail` and root-caused, not regenerated.

### 7.7 RED→GREEN evidence

Tee dev-time runs to gitignored `.hermes/run-logs/e51.1-*.log`. Record the failing run before the fix and the passing run after for §7.1–7.3. Visual regression is the gate, not typecheck (`project-context.md:254`).

---

## 8. Gates + ownership

| Gate | Owner | Notes |
|---|---|---|
| `ruff` (api + worker) | untouched | no Python in this story |
| `npm run lint --max-warnings=0` | this story | watch `react-refresh/only-export-components` on the new file |
| `npm run typecheck` | this story | `verbatimModuleSyntax` → `import type` for `BrowseCategoryRead`; `noUncheckedIndexedAccess` → no `!` shortcuts |
| `npm run test` (vitest) | this story | §7.1–7.3 |
| `npm run test:visual` (4 projects) | this story | §7.4–7.6; mandatory for any UI change |
| `npm run build` | this story | part of `check-all.sh` |
| `bmad-code-review` (CR) | after DS | Blind Hunter + Edge Case Hunter + Acceptance Auditor |
| Independent external review | after CR | **`laura-aider-review-diff` / Aider** — the routine default per `LAURA_AGENT_RULEBOOK.md` § 2 and `AGENTS.md:108`. Gemini is **not** a default reviewer. Codex is fallback / high-stakes / explicit-operator-request only. |
| `infra/scripts/check-all.sh` 16/16 | before ff-merge | tee to `.hermes/run-logs/` |
| NFR26-DETERMINISM-1 | before merge | 3× consecutive identical vitest + pytest pass counts |

Branch: `feat/E51.1-desktop-browse-navigation` (`AGENTS.md` § Branch naming). ff-only merge, no squash. Deploy after merge (`feat:` prefix forces the range-based deploy gate).

---

## 9. Anti-pattern fences — do NOT do these

- **Do not** modify `FacetSidebar.tsx` (AC-17). It is relocated, not refactored.
- **Do not** generalize `FacetSidebar` into a "generic sidebar" that renders both categories and tags (D-1).
- **Do not** create `/categories/$slug` or regenerate `routeTree.gen.ts` — Story 51.2 (D-3). `*.gen.ts` is lint-ignored and never hand-edited (`project-context.md:131`).
- **Do not** build the scope chip or a "Search entire catalog" control — Story 51.2.
- **Do not** build the `Filters (n)` drawer, its badge count, promoted groups, or in-panel tag search — Story 52.1.
- **Do not** add `category` to `activeFilterCount()` (`FilterRibbon.tsx:53-59`). Scope is never counted in `(n)` (FR26-BROWSE-2).
- **Do not** build the mobile Browse surface or touch the mobile `ModuleRail` — Story 51.3, which carries an explicit `Ask First` (D-6).
- **Do not** render categories on `/catalog/$modelId` — Story 51.4.
- **Do not** make counts filter-aware (D-5).
- **Do not** add the category query to either fatal guard in `CatalogList.tsx` (D-8/D-9).
- **Do not** touch `apps/api/`, `workers/`, `infra/`, or any migration. `GET /api/categories` shipped in Story 49.3 and is consumed as-is.
- **Do not** bypass `api()` with raw `fetch` (`project-context.md:48,250`).
- **Do not** add an inline hex colour (`project-context.md:47`).
- **Do not** blanket-run `--update-snapshots` (§7.5).
- **Do not** add a `parent_id` tree (D-11 / `EXPERIENCE.md:186`).

---

## 10. Verification performed for this spec

Every fact above was produced by a command run in this session at `main` @ `0f722d2` (clean tree, synced with `origin/main`).

| # | Command / read | Result used |
|---|---|---|
| 1 | `git status --short --branch`; `git rev-parse HEAD`; `git rev-parse origin/main` | clean `main`, `0f722d2` == `origin/main` → `baseline_commit` |
| 2 | Read `AGENTS.md`, `CLAUDE.md`, `_bmad-output/project-context.md`, `LAURA_AGENT_RULEBOOK.md` | gates, branch policy, reviewer routing (§8), execution discipline |
| 3 | Full read of `sprint-status.yaml` (comments stripped + raw lines 389-411) | `epic-51: backlog`, `51-1` first backlog key, epic-51 story briefs |
| 4 | `ls _bmad-output/implementation-artifacts/ \| grep -E '^51'` + `grep -iE 'spec-.*(51\|browse)'` | no duplicate story or spec |
| 5 | `grep -n 'create-story' _bmad/_config/bmad-help.csv` | routing rows 26/27/28 (§ header) |
| 6 | `uv run --python 3.11 _bmad/scripts/resolve_config.py --project-root .` | `implementation_artifacts`, `document_output_language: English`, `communication_language: Polish` |
| 7 | `grep -rn "FacetSidebar" apps/web/src apps/web/tests` | complete consumer set (§2.3–2.4) |
| 8 | Full read `FacetSidebar.tsx` (228 lines) | props, responsive branch, module-local constants (§2.1–2.2) |
| 9 | Full read `CatalogList.tsx` (338 lines) | M1 `:183-190`, M2 `:192-215`, fatal guards `:136`/`:152`, 50.2 wiring `:47`, Clear-filters scope preservation `:259-264` |
| 10 | Full read `FilterRibbon.tsx` (353 lines) | the decisive §2.5 finding: the Filters sheet is `md:hidden` and tag-free |
| 11 | Full read `ModuleRail.tsx` | active-row class string reused verbatim at `:34` |
| 12 | Read `hooks/useCategories.ts`; `ls hooks/` | shipped hook, key, staleTime, zero consumers (§2.6, §5) |
| 13 | Read `lib/api-types.ts:95-126` | `BrowseCategorySummary` / `BrowseCategoryRead` field list |
| 14 | Full read `routes/catalog/index.tsx` | `CatalogSearch.category` `:46`, validator `:105-108` |
| 15 | `python3` key dump of `en.json`/`pl.json` | 906 keys each; `catalog.filters.*`, `a11y.*`, `errors.network`, `common.retry` inventory (§3.3) |
| 16 | `sed -n '110,145p;200,235p' tests/visual/facet-filtering.spec.ts` | the desktop-`<aside>` premise that breaks (§7.5) |
| 17 | Read `tests/visual/catalog-list.spec.ts`; `grep` structure of `api-stubs.ts` | stub pattern for §3.4; expected baseline movement §7.6 |
| 18 | `head -75 CatalogList.test.tsx`; `ls components/`; `find … -name '*i18n*'` | test harness pattern (§7.2), i18n-diff precedents (§7.3) |
| 19 | Read `epics.md:4515-4554`; `grep FR26-BROWSE-1 / NFR26- prd.md` | epic + FR/NFR text |
| 20 | Read `architecture.md:3303-3350` | Decision AY read surface, slug-vs-UUID rationale, empty-categories-returned |
| 21 | Read `DESIGN.md:40-89,239-242,264-273,293-302`; `grep` `EXPERIENCE.md` | tokens, geometry, row vocabulary, states, a11y, terminology |
| 22 | `git log --oneline -5` | 50.1/50.2/50.3 landed in sequence; `0f722d2` is the 50.3 closeout |

**Not run, and not claimed:** no test, no build, no lint, no typecheck, no visual run. This is a story-authoring pass; every gate in §8 is owed by `bmad-dev-story`.

---

## 11. Tasks / Subtasks — dev execution (native `bmad-dev-story`, under G26-DEVGO)

- [x] **T1 — Branch** `feat/E51.1-desktop-browse-navigation` from clean `main`.
- [x] **T2 — RED** (AC-1…AC-14, AC-21): author `BrowseRail.test.tsx` (§7.1) against the not-yet-existing component; capture the failing run.
- [x] **T3 — i18n** (AC-19): add the three keys to `en.json` + `pl.json`; author `browse-i18n.test.ts` (§7.3).
- [x] **T4 — GREEN**: implement `BrowseRail.tsx` (§3.1). Copy the active-row class string from `ModuleRail.tsx:34`; copy the pl-fallback from `FacetSidebar.tsx:80-81`.
- [x] **T5 — Wire** (AC-6…AC-9, AC-15, AC-16): edit `CatalogList.tsx` per §3.2 — five changes, no more. Verify `FacetSidebar.tsx` diff is zero (AC-17).
- [x] **T6 — Integration** (§7.2): extend `CatalogList.test.tsx`, including the D-8 and D-9 non-blanking cases.
- [x] **T7 — Visual infra** (§3.4): add the `/api/categories` stub to `stubSotList`.
- [x] **T8 — Visual coverage** (§7.4, AC-24): author `browse-rail.spec.ts` with `toBeVisible()` before every screenshot.
- [x] **T9 — Repair** (§7.5, AC-25): re-point `facet-filtering.spec.ts` at the Sheet-mounted instance; fix both stale comments.
- [x] **T10 — Baseline triage** (§7.6): classify every failing baseline as `stale-baseline` / `deterministic-fail` / `flake-candidate` **before** any `--update-snapshots`. Any moved **mobile** `/catalog` baseline is a `deterministic-fail` — root-cause it, do not regenerate.
- [x] **T11 — Gates** (AC-26/AC-27): story-owned gates run and teed to `.hermes/run-logs/`; 3× determinism runs.
- [x] **T12 — Handoffs**: §12 items carried into `sprint-status.yaml` `action_items` so 51.2/52.1 inherit them explicitly.

---

## 12. Handoffs this story deliberately does not absorb

1. **→ Story 51.2** — the results-heading focus target required by `EXPERIENCE.md:324` (D-7). It cannot exist before the scope chip and `/categories/$slug`. 51.2 must add it **and** re-point this story's `setCategory` navigator at the new canonical URL (D-3).
2. **→ Story 52.1** — the interim Tags sheet promoted by D-2 keeps the `Tags`/`Tagi` label and `side="left"`, whereas `EXPERIENCE.md:331` puts the desktop Filters surface on the right with a `Filters (n)` badge. 52.1 owns re-labelling, re-siding, the badge (which must exclude category scope), promoted groups, in-panel tag search, and the "opening one closes the other" coordination (D-11).
3. **→ Story 52.1** — `FilterRibbon`'s `+ tag` picker (`:99-115`) is untouched here; the epic sketch says it stops being the primary tag path *in 52.1* (`epics.md:4553`).

---

## 13. Validation record — native `bmad-create-story:validate` (VS), 2026-07-28

Run immediately after Create, in the same session, against `./checklist.md`. Route: `_bmad/_config/bmad-help.csv:27` (**VS**, `preceded-by bmad-create-story:create`, `followed-by bmad-dev-story`, `required=false` — run as the recommended quality gate per `AGENTS.md:218`).

**Verdict: PASS.** Status set to `ready-for-dev`. No BMAD protest, no missing prerequisite, no duplicate story, no required scope amendment beyond the decisions already captured above.

### 13.1 Disaster-prevention checks and what they found

| Checklist axis | Finding |
|---|---|
| **Reinvention prevention** | Caught and fixed during Create: the story initially risked treating "relocate into Filters" as if a Filters surface existed. §2.5 traced `FilterRibbon.tsx:152-179` and proved it is `md:hidden` and tag-free, forcing D-2 to reuse the **shipped** Sheet mount instead of building a new one. Also reuses `useCategories()` (shipped, unused), `errors.network`/`common.retry` (shipped), and `ModuleRail.tsx:34`'s class string rather than re-deriving it. |
| **Wrong libraries / versions** | No new dependency. Stack facts re-checked against `project-context.md:22-36`: React 19, TanStack Router/Query 5, Tailwind **v4** (no `tailwind.config.js`), TS 5.6 with `verbatimModuleSyntax` + `noUncheckedIndexedAccess`, i18next 24. Recorded as typecheck notes in §8. No web research was needed — every API this story touches is in-repo and shipped. |
| **Wrong file locations** | `BrowseRail.tsx` lands in `modules/catalog/components/` beside its siblings; unit tests colocated (`project-context.md:113`); visual spec in `tests/visual/`. Matches the enforced layout at `project-context.md:132-139`. |
| **Regression prevention** | **The highest-value find.** `tests/visual/facet-filtering.spec.ts:126-136` gates on a desktop-only standalone `<aside>` that D-2 removes. Without §7.5 that suite would either silently skip everywhere or be blanket-re-baselined, masking the IA change. Promoted to **AC-25** and task **T9**. Second find: D-8/D-9 keep a failing/pending category read out of the fatal guards, so a navigation aid can never blank the catalog. Third: §7.6 pre-declares that a moved **mobile** baseline is a `deterministic-fail`, not a stale baseline. |
| **UX compliance** | Cross-checked against the closed **G26-UXGATE** artifact rather than the epic prose: geometry `DESIGN.md:239-242`, row/active/count/empty specs `:268-271`, colour-role rules `:203-204`, count-not-filter-aware `EXPERIENCE.md:220`, cold/empty/error `:242-253`, terminology `:202`, a11y `:268-283`/`:315-324`. |
| **Vagueness / completion-lying** | 27 ACs, each mechanically checkable. AC-17 ("zero-line diff") and AC-9 ("byte-identical to `ModuleRail.tsx:34`") are deliberately falsifiable. §10 separates what was verified from what was explicitly **not** run. |
| **Scope creep** | §9 fences 14 named non-goals; §12 records three handoffs with their owning stories, so deferral is explicit rather than silent. Ponytail minimal-diff honored: one new file, five edits in one existing file, one shipped component relocated with a zero-line diff. |
| **Learning from past work** | Applies the `epic:47` stale-precondition item (§2 exists because of it), the `epic:45`/`epic:46` TEST-AUTHORING `toBeVisible()` rule (AC-24), the `epic:45`/`epic:46` baseline-provenance GOVERNANCE items (§7.5), Init 10's visual-triage rule (§7.6/T10), Init 18's cache-coherence enumeration (§5) and magic-constant contract-pointing (§5, `staleTime` justified by its own contract and left unchanged). |
| **Sequencing / prerequisites** | E49 + E50 are `done` on `main` (`sprint-status.yaml`; `git log` `c436f61`/`0093187`/`00725af`). G26-UXGATE closed 2026-07-26. G26-DEVGO recorded as Laura/controller authorization under the standing Initiative 26 authorization — **not** an Ezop signature and **not** human review. No prerequisite is unmet. |
| **LLM/dev-agent optimization** | Decisions are numbered (D-1…D-11) and referenced from the ACs and tasks, so the dev agent can resolve any "why" without re-reading prose. Exact class strings, exact line anchors, and exact file paths are inlined so no re-derivation is needed. |

### 13.2 Open questions for the controller — none blocking

- **Q1 (informational).** D-2 leaves the desktop grouped-facet surface behind a `Tags`/`Tagi` label until 52.1 re-labels it `Filters (n)`. If the controller would rather 51.1 also ship the label change, that is a one-key amendment — but it would put a `Filters` label on a surface that lacks the `(n)` badge semantics 52.1 defines, so the recorded recommendation is **no**.

---

## 14. Dev Agent Record

### 14.1 Agent Model Used

Claude Opus 5 (1M context), native `bmad-dev-story` (DS), 2026-07-28. No other agent participated — no Aider, no Codex, no Gemini, no human reviewer.

### 14.2 Debug Log References

All teed to gitignored `.hermes/run-logs/`:

| Log | Contents |
|---|---|
| `e51.1-red-t2.log` | RED proof for T2 — `Failed to resolve import "./BrowseRail"`, 0 tests collected |
| `e51.1-green-t4.log` | GREEN for T2+T3+T4 — 21/21 (`BrowseRail.test.tsx` 16, `browse-i18n.test.ts` 5) |
| `e51.1-t6-integration.log` | `CatalogList.test.tsx` 19/19 (11 pre-existing + 8 new) |
| `e51.1-vitest-full-1.log` | first full vitest — 143 files / 879 tests |
| `e51.1-visual-1.log` | first full visual — 46 failed, the input to the T10 triage |
| `e51.1-visual-2.log` | post-triage visual — 26 failed, all desktop, zero mobile |
| `e51.1-visual-3.log` | full visual after regeneration — 560 passed / 0 failed |
| `e51.1-vitest-3x.log` | NFR26-DETERMINISM-1 — 3× identical 143/879 |
| `e51.1-pytest-3x.log`, `e51.1-pytest-runs-2-3.log` | NFR26-DETERMINISM-1 — pytest ×3 |

### 14.3 Completion Notes List

**Implemented exactly as specified, then amended by native CR's M-1 minor fix.** One new component, five edits in `CatalogList.tsx`, seven i18n keys per locale (three base browse keys + four pluralized `categoryWithCount_*` forms), one relocated mount. `FacetSidebar.tsx` has a **verified zero-line diff** (`git diff --stat` on that path returns empty), so AC-17 is proven mechanically rather than asserted.

**Three defects were found and fixed during the run — recorded because silence would misrepresent the run as frictionless:**

1. **`common.retry` is `"Spróbuj ponownie"` in pl, not `"Ponów"`.** The first `browse-rail.spec.ts` error-state test asserted a Polish string that does not exist, and failed. This was a **spec-authoring defect, not a product defect** — the product rendered the correct shipped copy all along. Fixed in `browse-rail.spec.ts`, and the same wrong alternative was corrected in the `CatalogList.test.tsx` regex (where it had been passing only because that suite runs under the `en` locale, so the bad alternative was never exercised — a latent false-green).
2. **Invalid JSX from a misplaced comment.** The `w-full lg:w-auto` fix was first written as `render={ {/* comment */} <Button/> }`, which is not a valid expression container. The dev server failed to compile the route, and the whole `browse-rail` suite went red with "Tagi trigger not found". Caught because the suite went red — fixed by moving the comment above `<SheetTrigger>`. Typecheck and lint had both passed *before* this edit and were re-run *after* it (both 0), which is why the story's gate list runs static checks after every edit, not once.
3. **A stale/ambiguous baseline state produced a misleading intermediate reading.** After the `lg:w-auto` fix, `--update-snapshots` reported "14 passed" without rewriting any PNG, while a DOM probe showed the button had genuinely changed width (47.2px computed). Rather than trust either signal, the `browse-rail` snapshot directory was **deleted and regenerated from scratch**, then re-run twice to confirm stability, and the resulting baseline was **read as an image and visually verified**. This is the `epic:47` "environment, not product" discipline applied: the ambiguity was resolved by forcing a clean regeneration, not by explaining it away.

**One deliberate, minimal deviation from §3.2, surfaced for review.** §3.2 step 3 says to promote the M2 wrapper by dropping `lg:hidden` and otherwise keep it unchanged. Doing exactly that left the relocated trigger `Button` carrying `w-full` — correct while it was mobile-only, but at `lg`+ it stretched into a full-width bar across the results column. One responsive class was added (`w-full justify-start` → `w-full justify-start lg:w-auto`) so the control sizes to its label on desktop while **mobile keeps the shipped geometry byte-for-byte** (confirmed: zero mobile baselines moved). This is a layout adaptation required by the promotion itself, not a label/side/behavior change, and it does not encroach on Story 52.1's ownership of the consolidated `Filters (n)` surface.

**A spec-vs-UX-artifact divergence is recorded rather than silently resolved.** `EXPERIENCE.md:219` says each rail row "is a `Link`"; the frozen story spec §3.1 defines a presentational component with an `onSelect` callback, so rows are `<button>` elements and the route owns navigation (matching the shipped `toggleTag`/`toggleUntagged` pattern). Every AC is satisfied either way — `aria-current="page"` is valid on a button — but a real `Link` would additionally give middle-click/copy-URL affordances. Native CR adjudicated this as Minor/deferred to Story 51.2: keep the frozen `onSelect` contract here, avoid converting `BrowseRail.test.tsx` into a `RouterProvider` integration harness, and re-point the navigator once 51.2 introduces `/categories/$slug`.

**Two stale in-repo comments were corrected as part of the change** (both now false because of this story): the `facet-filtering.spec.ts` contrast comment about a desktop-only `<aside>`, and the `CatalogList.test.tsx` note claiming "no UI emits `category` until 51.2".

**Review follow-up:** native `bmad-code-review` approved the story with no Critical/Important findings and surfaced M-1 (`1 models` in English accessible names). M-1 was repaired after CR by adding pluralized `catalog.browse.categoryWithCount_{one,few,many,other}` keys in both locales and updating the i18n parity + visual assertions; focused vitest re-run passed 21/21, full vitest/typecheck/lint remained green, and targeted browse-rail visual update passed 14/10 skipped. Independent Aider review approved the full text/code diff (PNG payload excluded, manifest included). Aggregate `check-all.sh` rerun passed 16/16 (`.hermes/run-logs/check-all-e51-1-rerun-20260728_235414.log`). Remaining CR minors are deferred/polish only (§17). No commit, push, merge, or deploy yet.

### 14.4 File List

**New (5 source/test files + 20 new baselines):**

- `apps/web/src/modules/catalog/components/BrowseRail.tsx`
- `apps/web/src/modules/catalog/components/BrowseRail.test.tsx`
- `apps/web/src/modules/catalog/browse-i18n.test.ts`
- `apps/web/tests/visual/browse-rail.spec.ts`
- `_bmad-output/implementation-artifacts/51-1-desktop-browse-navigation.md` (this artifact, from the CS/VS pass)
- `apps/web/tests/visual/__snapshots__/browse-rail.spec.ts/` — **14** new PNGs
- `apps/web/tests/visual/__snapshots__/facet-filtering.spec.ts/facet-sidebar-{default,group-expanded,untagged}-mobile-{light,dark}.png` — **6** new PNGs (these tests were previously skipped on mobile and had no committed baseline; they now run on all four projects)

**Modified (6 source/test files + 26 regenerated baselines):**

- `apps/web/src/modules/catalog/routes/CatalogList.tsx` (+59/−…) — import + `useCategories()` + `setCategory()` + M1→`BrowseRail` swap + M2 breakpoint promotion + trigger width
- `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` — `/api/categories` stub modes, `browseCategories()` fixture, 8 new tests
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — 3 keys each
- `apps/web/tests/visual/api-stubs.ts` — `DEFAULT_BROWSE_CATEGORIES` + `categories` option (`"never"` / `"error"` modes)
- `apps/web/tests/visual/facet-filtering.spec.ts` — `skipOnMobile()` → `openFacetSheet()`, three tests re-pointed, two stale comments corrected
- **26** regenerated PNGs, **all desktop-light/desktop-dark**, across `catalog-list`, `catalog-search-suggestions`, `empty-states`, `facet-filtering`, `filter-ribbon-selects-open`, `focus-ring`
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status transitions + handoff action items

**Deliberately NOT modified:** `apps/web/src/modules/catalog/components/FacetSidebar.tsx` (AC-17, zero-line diff verified), `FacetSidebar.test.tsx`, `FilterRibbon.tsx`, `routes/catalog/index.tsx`, `routeTree.gen.ts`, and everything under `apps/api/`, `workers/`, `infra/`.

---

## 16. Gate record — native `bmad-dev-story`, 2026-07-28

Every gate below was **run in this session and its output read**. Nothing is inferred.

| Gate | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` | **rc=0** (re-run after the JSX fix) |
| Lint | `npm run lint` (`eslint --max-warnings=0` + stylelint) | **rc=0** |
| Unit/integration | `npm run test` | **rc=0** — 143 files / **879 tests** passed |
| Production build | `npm run build` | **rc=0** (pre-existing >500 kB chunk warning, unchanged) |
| Visual regression | `npm run test:visual` (4 projects) | **rc=0** — **560 passed**, 0 failed, 36 skipped; re-run a second time, identical |
| Determinism — vitest | `npm run test` ×3 | 143/879, 143/879, 143/879 — **identical** |
| Determinism — pytest | `uv run --frozen pytest -q` ×3 (`apps/api`) | **1922 passed, 3 skipped** ×3 — run 1 433.66s, run 2 431.32s, run 3 429.34s. **Identical pass counts across all three runs.** No Python file is touched by this story, so pytest is a pure non-regression check. |

### 16.1 Baseline triage record (T10) — classification BEFORE regeneration

First full visual run: **46 failed**. After repairing the two spec-authoring defects, the residual set was **26 failed**, and every one was classified before any `--update-snapshots`:

| Class | Count | Disposition |
|---|---|---|
| `stale-baseline` — intentional IA cutover | **26** (all `desktop-light`/`desktop-dark`) | Regenerated. Two representative diffs were **opened and read as images** first: `focus-ring` (confirmed the left column changing from the tag tree to the category rail, plus the new desktop Tags trigger row) and `catalog-search-suggestions` (confirmed Story 50.3's suggestion panel — plain-query row, `Smok · Motyw` pill, alias `Dragon`, `Drake` pill — is **pixel-intact**; only the left column and vertical offset moved). |
| `deterministic-fail` | **0** | — |
| `flake-candidate` | **0** | Two consecutive full visual runs were identical. |

**The D-6 / §7.6 invariant held and is the headline triage result: ZERO mobile baselines moved.** `catalog-list`, `empty-states`, `focus-ring`, `filter-ribbon-selects-open` and `catalog-search-suggestions` failed on `desktop-*` **only**. The story predicted that a moved mobile `/catalog` baseline would be a `deterministic-fail`; none occurred, which is positive evidence that promoting the Tags trigger to desktop left the sub-`lg` surface untouched.

The 6 new `facet-sidebar-*-mobile-*` PNGs are **untracked/new**, not rewrites — `git status` shows `??`, confirming no committed mobile baseline was overwritten. They exist because `facet-filtering.spec.ts`'s three tests were previously `skipOnMobile`-gated and now run on all four projects (T9).

### 16.2 Baseline provenance — sign-off owed at commit time

**46 baseline PNGs** are staged for this story (26 regenerated + 20 new). The repo's Baseline Acceptance Gate requires a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line per changed PNG in the commit message.

**The reviewer name MUST be the agent that actually inspected them — `Claude Opus 5` — and MUST NOT name Ezop or any human.** This is the twice-recurring forged-sign-off defect class flagged as `open` in the `epic:45` and `epic:46` GOVERNANCE action items. In this run, the browse-rail baselines were genuinely inspected as images (§14.3 item 3, §16.1); the remaining regenerated baselines were reviewed via their diff artifacts. No human has reviewed any of them.

### 16.3 Controller closeout gates after DS

- Native `bmad-code-review` (CR) — run and approved; see §17.
- Independent external review — **Aider via `laura-aider-review-diff`** approved full text/code diff; see §18.
- `infra/scripts/check-all.sh` — standalone rerun passed **16/16 all green** at `.hermes/run-logs/check-all-e51-1-rerun-20260728_235414.log`; see §18.
- Commit, ff-merge, push, deploy, post-deploy smoke — still owed at this artifact update point.

---

## 15. Change log

| Date | Change | By |
|---|---|---|
| 2026-07-28 | Created via native `bmad-create-story` (CS) at `main` @ `0f722d2`, after mandatory `bmad-help` routing. `VERIFY-AT-CREATE-STORY` trace of `FacetSidebar.tsx` performed at source (§2). | Claude (native BMAD), delegated by Laura/controller under standing Initiative 26 authorization |
| 2026-07-28 | Validated via native `bmad-create-story:validate` (VS). Verdict **PASS**; status `ready-for-dev` (§13). | Claude (native BMAD) |
| 2026-07-28 | Implemented via native `bmad-dev-story` (DS) on `feat/E51.1-desktop-browse-navigation` under G26-DEVGO. All 12 tasks and 27 ACs closed. Gates: typecheck 0, lint 0, vitest 143/879 (×3 identical), build 0, visual 560/0 (×2 identical), pytest 1922 passed/3 skipped. 46 baselines staged (26 regenerated desktop-only + 20 new); triage recorded zero `deterministic-fail` and **zero mobile baseline movement**. Three in-run defects found and fixed (pl `common.retry` string, invalid JSX comment, ambiguous baseline state resolved by clean regeneration) — see §14.3. Status → `review`. **No CR, no Aider/Codex/Gemini, no human review, no commit/push/merge/deploy.** | Claude Opus 5 (native `bmad-dev-story`) |
| 2026-07-28 | Native `bmad-code-review` verdict **APPROVE** (native BMAD agent approval only). Critical/Important: none. M-1 (`catalog.browse.categoryWithCount` lacked plural forms, producing English `1 models` in accessible names) repaired immediately with pluralized en/pl keys and focused vitest 21/21. Remaining minors/deferred items recorded in §17. **No human review, no Aider/Codex/Gemini, no commit/push/merge/deploy.** | Claude Opus 5 (native `bmad-code-review`) + Laura/controller fix loop |

---

## 17. Native BMAD code-review record — 2026-07-28

Verdict: **APPROVE**. This is native BMAD agent approval only; no human review, no Aider, no Codex, no Gemini.

Critical: none. Important: none.

Minor findings:

- **M-1 fixed after CR:** `catalog.browse.categoryWithCount` did not model plurals, so an English category with exactly one model would announce `1 models`. Fixed by adding `catalog.browse.categoryWithCount_{one,few,many,other}` in both locales and updating `browse-i18n.test.ts`; focused re-run `npm run test -- src/modules/catalog/browse-i18n.test.ts src/modules/catalog/components/BrowseRail.test.tsx` passed **2 files / 21 tests**.
- **M-2 deferred/polish:** retry after category-load error gives no pending feedback while refetch is in flight. AC-13 is satisfied; this is UX polish only.
- **M-3 deferred/out-of-scope:** desktop `/catalog` has two `<nav>` landmarks, but only `BrowseRail` is named. `ModuleRail` is outside this story.
- **M-4 deferred/test-hardening:** `accessibility-axe.spec.ts` reaches `/catalog` without `stubSotList`, so it scans the fatal-error surface rather than the newly added rail. Pre-existing harness shape, newly consequential.

Deferred:

- **DF-1 → 51.2:** keep `<button>` rows for 51.1. The frozen story contract is `onSelect`, all ACs pass with a button, and 51.2 introduces `/categories/$slug` where a real `Link` conversion naturally belongs.
- **DF-2 → 51.2:** `setCategory` uses `replace: true`; appropriate for this shipped `/catalog?category=` seam, but browse-route history should be revisited when 51.2 adds canonical category routes.
- **DF-3 → 51.2:** `CatalogList.test.tsx` category-clear comment overstates the desktop case slightly; below `lg` the gap remains real until 51.2/51.3.
- **DF-4 → commit time:** the commit message must include `baseline-reviewed:` lines for all 46 PNGs, naming `Claude Opus 5` and no human.

---

## 18. Independent review and aggregate closeout gate — 2026-07-28/29

- **Aider review:** `laura-aider-review-diff` approved the full text/code diff with PNG payload excluded by size and a PNG manifest included. Log: `.hermes/run-logs/e51.1-aider-review-fulldiff-nopng-20260728_234056.log`. Verdict: **APPROVE**; Critical/Important none; minor notes matched already documented 51.2/52.1 handoffs.
- **Post-CR fix verification:** focused `npm run test -- src/modules/catalog/browse-i18n.test.ts src/modules/catalog/components/BrowseRail.test.tsx` passed 2 files / 21 tests, full `npm run test` passed 143 files / 879 tests, `npm run typecheck` rc=0, and `npm run lint` rc=0.
- **Visual follow-up:** CR's pluralization fix changed legitimate rendered accessible strings; browse-rail visual assertions were updated from `modeli: N` to plural-aware `N modeli`, targeted `npm run test:visual -- tests/visual/browse-rail.spec.ts --update-snapshots` passed 14 / 10 skipped, then the aggregate visual gate passed 560 / 36 skipped.
- **Aggregate closeout:** `infra/scripts/check-all.sh` rerun passed **16/16 all green**. Log: `.hermes/run-logs/check-all-e51-1-rerun-20260728_235414.log`; marker: `CHECK_ALL_RC=0 2026-07-29T00:04:54+02:00`.
