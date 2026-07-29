---
baseline_commit: cc5e6e86cd1dcf7567f991a484dd341b9395ac4b
---

# Story 52.1 — `Filters (n)` drawer/panel consolidation (FR26-BROWSE-1, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1, NFR26-DARKMODE-1)

- **Epic:** E52 — Filters surface + admin curation and governance (Initiative 26 — Catalog Discovery).
- **Status:** `review`.
- **Author:** Claude Opus 5, native `bmad-create-story` (Create + Validate), repo-local. **Authorization posture:** `G26-DEVGO` granted by Laura/controller for this create+validate pass and downstream dev, under Ezop's standing Initiative 26 delegation. **NOT** an Ezop signature, **NOT** human review of any kind; no Codex, no Gemini, no Aider, no subagents. No app code written, no gate/test/build run, no branch/commit/merge/deploy in this pass.
- **Created:** 2026-07-29 at `main` @ `cc5e6e8` (clean tree), directly after Story 51.4's full closeout.
- **Duplicate check:** no pre-existing `_bmad-output/implementation-artifacts/*52-1*` artifact. Only `50-*` and `51-*` story files exist in the Initiative 26 range.
- **Dependency check (from `sprint-status.yaml` @ `cc5e6e8`):** E52 depends on E49 (admin API) + E51 (browse IA patterns). `epic-49: done` with 49.1–49.5 all `done`. All four E51 stories (51.1–51.4) `done` and deployed. Both dependencies are satisfied. **G26-UXGATE is closed** by `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` (commit `48db6bb`).
- **Scope class:** frontend-only. One new component (`FiltersPanel`), a subtractive refactor of `FilterRibbon.tsx`, toolbar rewiring in `CatalogList.tsx`, one i18n value change, one new key, two removed keys. **No** backend change, **no** new endpoint, **no** new route, **no** `routeTree` regeneration, **no** new dependency, **no** new `--color-*` token, **no** `ModuleRail` change.
- **Sources of truth:** `epics.md:4551-4553` (Story 52.1 sketch), `epics.md:4543-4549` (E52 header + per-story merge-gate obligations); `prd.md` FR26-BROWSE-1; UX artifact — `EXPERIENCE.md:39-40` (browse-vs-refine split and the "counts toward `Filters (n)`" column), `:56` (IA row: the `Filters (n)` surface is 52.1), `:62` (nesting rule / sibling sheets), `:204` (never render "Filtry (0)"), `:222` (scope chip never counted), `:226` (overflow note points at Filters), `:227` (**the exact `n` formula**), `:228` (surface contents and ordering), `:229` (promoted group ceiling), `:249` (in-panel tag-search empty state unchanged), `:278` (Tab order), `:328-333` (responsive presentation table + "never merged into one sheet with tabs"), `:346-347` (Baymard/Algolia liftings), `:367` (panel open/closed is deliberately NOT in the URL), `:403` (component ownership: `FilterRibbon.tsx` + relocated `FacetSidebar.tsx`), `:411` (per-story gate obligations), `:426` (**MVP non-goal: no promoted filter groups**); `DESIGN.md:123-136` (`filters-trigger`, `filters-trigger-badge`, `filters-surface` token specs), `:203` (the `primary`-at-10% "location" vocabulary is for browse only; solid `primary` is the badge fill), `:237-239` (regime table), `:250` (elevation: the panel floats, the chip does not), `:256` (`{rounded.full}` for the badge), `:279-281` (component visual specs); shipped code at `main` @ `cc5e6e8`; carried handoffs from 51.1 (D-2), 51.2 (§12 item 6), 51.3 (D-4.4) and `sprint-status.yaml` `action_items` epic-51 entry (`owner: E52 (52.1)`, `status: open`).

---

## 1. Story statement

**As** a catalog user,
**I want** one clearly-labelled `Filters (n)` control that opens a single surface holding every refinement — tag groups with in-panel search, `Bez tagów`, status, source and sort — with the badge telling me how many constraints are active,
**so that** refining the catalogue is one discoverable place instead of three scattered controls, and the number I see never lies about what is actually narrowing my results.

**FR mapping — FR26-BROWSE-1** ("categories in navigation; facets into `Filters (n)`; ≤2–4 promoted groups"). Verifiable for this story: the shipped app exposes exactly **one** refinement control per viewport; opening it reaches every tag group, the groupless section, `Bez tagów`, status, source and sort within one interaction; the badge count follows `EXPERIENCE.md:227` exactly; and the active browse category contributes **zero** to that count.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `cc5e6e8`

The epic sketch (`epics.md:4553`) names `FilterRibbon.tsx:99-113` as the `+tag` control. **That line range is stale** — 50.3 and 51.3 both edited the file since. Everything below is re-traced against the tree as it actually stands.

| Fact | Evidence at `cc5e6e8` | Consequence for this story |
|---|---|---|
| There are **three** refinement controls today, not one | (a) `CatalogList.tsx:360-394` — `Sheet side="left" w-80 max-w-[85vw]`, trigger label `catalog.filters.openTags` ("Tagi"), content `FacetSidebar mobile`, rendered at **every** viewport since 51.1's D-2 relocation. (b) `FilterRibbon.tsx:162-189` — `Sheet side="bottom" max-h-[80vh]`, trigger `md:hidden`, icon `SlidersHorizontal`, label `catalog.filters.openFilters` ("Filtry"), badge from `activeFilterCount`, content `FilterSelects` (status/source/sort) only, **no tags at all**. (c) `FilterRibbon.tsx:192-194` — `hidden ... md:flex` inline `FilterSelects` on desktop. | D-1 collapses (a)+(b)+(c) into one `FiltersPanel`. |
| The `+tag` control is at `FilterRibbon.tsx:109-125`, not `:99-113` | `:109-125` is the `Button` toggling `tagPickerOpen`; `:99` is the `aria-label` on a **chip remove** button. `TagPicker` is `:285-362`. | D-3 targets the correct range; the chip-remove button at `:97-105` is explicitly **kept**. |
| `activeFilterCount` today counts the **wrong** things | `FilterRibbon.tsx:58-64` — `status` + `source` + `sort !== "recent"`. It counts `sort` (which `EXPERIENCE.md:227` forbids) and ignores `tag_ids` and `untagged` (which it requires). | D-2 rewrites it. This is a **behaviour change to a shipped badge**, not a new feature. |
| `untagged` is not visible to `FilterRibbon` | `FilterRibbonState` (`FilterRibbon.tsx:38-45`) has no `untagged`. The flag lives in `CatalogList`'s `search.untagged` and reaches `FacetSidebar` via `untaggedActive`/`onToggleUntagged` (`CatalogList.tsx:389-390`). | The count cannot be computed inside today's `FilterRibbon`. D-1's `FiltersPanel` receives both prop sets, so it can. |
| Category scope is structurally unreachable from the filter surface | `CatalogList.tsx:108` passes `category: scopeSlug` (from the **path**) straight to `useModels`; `:164-165` strips a stray `category` search token out of `forwardSearch` at one seam. `FilterRibbonState` has no category field. | D-7: "category is never counted" is satisfied **structurally**, not by a subtraction. Do not add a category prop to the panel to "exclude" it. |
| `FacetSidebar` already ships in-panel tag search | `FacetSidebar.tsx:107-113` (`Input` + `matchesQuery` over `name_en`+`name_pl`), `:126-128` collapsible groups with `a11y.collapse`/`a11y.expand` names, `:164` per-tag `model_count`, `:174-192` trailing `Bez tagów` row, `:9-17` + `:56-64` `localStorage` collapse persistence under `catalog:facet-collapse`. | D-8: reuse **verbatim**. Do not re-author tag search inside `FiltersPanel`. |
| `FacetSidebar`'s non-`mobile` branch is already dead on `main` | `FacetSidebar.tsx:101-103` — the `hidden ... lg:flex` `<aside>` variant. Its only mount (`CatalogList.tsx:384-392`) passes `mobile`. 51.1's D-2 removed the desktop `<aside>` mount. | Out of scope (§5 Never). Recorded as a deferred-work candidate in §11, not cleaned here. |
| The 50.3 suggestion surface's overflow note points at a control this story retires | `SearchSuggest.tsx:216-220` renders `catalog.suggestions.overflowNote`; shipped values are en `"More matches — use + tag to browse all"` / pl `"Więcej wyników — użyj „Dodaj tag”, aby przejrzeć wszystkie"`. 50.3's own D-3 recorded this as deliberate interim wording because the Filters drawer did not exist yet, and `EXPERIENCE.md:226` requires the note to point at **Filters**. | D-3 changes the **value** of this key in both locales. The key name, its `aria-hidden`, its non-interactive/non-focus-stop status and every other 50.3 semantic stay byte-unchanged. |
| The rest of the 50.3 contract must survive untouched | `SearchSuggest.tsx:113-129` — Enter with no arrowed selection only closes the panel (`D-2`); tag selection is explicit; `:96-103` `onSelectTag` clears `q` atomically; `:11-13` 8-row cap; `:150-157` no internal scrollbar; `:180-197` `aria-label` accname + `aria-describedby` alias. `suggestions-i18n.test.ts:39-43` asserts the pl `tagOption` string verbatim. | §5 Never. This story adds **no** behaviour to `SearchSuggest.tsx`; its only edit anywhere near 50.3 is the overflow-note *copy*. |
| Sheet exclusivity is currently a three-boolean invariant | `CatalogList.tsx:59-83` — `mobileBrowseOpen` / `mobileTagsOpen` / `mobileFiltersOpen`, each setter closing the other two (51.3 D-4.3). 51.3's D-4.4 recorded verbatim that 52.1 collapses this to two. | D-5 discharges that handoff. |
| Data for a promoted-group qualification test exists, but the UX forbids shipping one | `useTagGroups()` → `TagGroupsResponse { groups: TagGroupRead[]; groupless: TagReadWithCount[] }`; `TagGroupRead.tags` is `TagReadWithCount[]` with **required** `model_count` (`api-types.ts:64-83`). So "≥2 tags with non-zero counts" (`EXPERIENCE.md:229`) is computable client-side with zero extra requests. But `EXPERIENCE.md:426` records **"No promoted filter groups in MVP"** as an explicit non-goal. | D-4: ship **zero** promoted groups. See D-4 for the full justification. |
| No `matchMedia`/`resize` handling exists anywhere in the catalog module | Confirmed absent in `CatalogList.tsx`, `FilterRibbon.tsx`, `BrowseRail.tsx`, `BrowseSheet.tsx`, `FacetSidebar.tsx` (also recorded as a pre-existing non-blocking observation in 51.3 §9). | D-6 introduces the first one, **file-local** to `FiltersPanel.tsx`, with a jsdom-safe fallback. |
| Locale files are **flat** dotted-key JSON | `browse-i18n.test.ts:8-15` and `suggestions-i18n.test.ts:8-15` both treat them as `Record<string, string>` and filter by `k.startsWith(prefix)`; `browse-i18n.test.ts:25` asserts a literal count of 13. | The new `catalog.filters.*` parity guard (Task 5) follows the same shape. `catalog.browse.*` is untouched, so the 13-literal does **not** move. |
| `catalog.actions.addTag` is **not** orphaned by removing `TagPicker` | Also used by `TagGroupsSection.tsx:96` (the admin add-tag affordance on model detail). | Keep the key. Only `catalog.tags.pickerTitle` and `catalog.filters.openTags` become orphans. |
| `catalog.tags.searchPlaceholder` / `catalog.tags.noMatches` survive `TagPicker`'s removal | Both are also used by `FacetSidebar.tsx:110-111` and `:116`. | Keep both keys. |
| `catalog.filters.tags` is already unused on `main` | No `t("catalog.filters.tags")` call site anywhere in `apps/web/src`. | **Pre-existing** orphan, not created by this story. Out of scope; E54.1's cross-surface i18n audit owns it. §11 records it. |
| Two visual specs are pinned to controls this story removes | `remaining-sheets-open.spec.ts:90-112` — one test clicks `/^Filtry$/i` (the `md:hidden` bottom sheet), one clicks `/^Tagi$/i` (the left facet sheet). `filter-ribbon-selects-open.spec.ts` exercises the desktop inline selects. `facet-filtering.spec.ts:210-225` opens the `TagPicker`. | Task 6 re-points all three. Their baselines are expected to move or retire; §7 lists the full expected baseline surface. |

---

## 3. Design decisions

### D-1 — One canonical `FiltersPanel`, one state model, two presentations

Create `apps/web/src/modules/catalog/components/FiltersPanel.tsx`. It owns:

- the **trigger** (`SlidersHorizontal` icon + `catalog.filters.openFilters` label + the count badge),
- the **surface** (a single shipped `Sheet` from `@/ui/sheet`), and
- the **content**, in exactly the order `EXPERIENCE.md:228` prescribes: the relocated `FacetSidebar` verbatim (group search → collapsible groups with per-tag counts → trailing `Bez tagów` row), **then** status, source, sort.

Props: the union of what the two dying surfaces need — `state: FilterRibbonState`, `onChange`, plus `groups`, `groupless`, `onToggleTag`, `untaggedActive`, `onToggleUntagged`, plus `open` / `onOpenChange` (controlled, mirroring `BrowseSheet`).

**One source for the selected tags.** Do **not** add a `selectedTagIds` prop alongside `state`. `FilterRibbonState.tag_ids` is already that array (`CatalogList.tsx:170` builds it from `search.tag_ids`), so `FiltersPanel` passes `selectedTagIds={state.tag_ids}` down to `FacetSidebar` internally, and D-2's count reads the same array. Two props carrying the same value is a divergence waiting to happen.

**No loading or error branch inside the panel.** `CatalogList.tsx:258-276` already returns an error surface or a skeleton grid before any of this renders, guarding on `tagGroups.isError` / `tagGroups.data === undefined`. By the time `FiltersPanel` mounts, `groups` and `groupless` are always defined. Do not build a second skeleton, spinner or retry inside the panel.

`FilterSelects` moves **verbatim** from `FilterRibbon.tsx:199-283` into `FiltersPanel.tsx` — same three `Select`s, same `ANY_STATUS`/`ANY_SOURCE` sentinels, same `aria-label`s, same `SelectValue` render props. It is a file move, not a rewrite. `FilterRibbon.tsx` consequently drops its `Sheet`, `Select`, `SlidersHorizontal` and `Input` imports.

After this, `FilterRibbon.tsx` retains exactly three things: the `SearchSuggest` mount (`:79-85`), the selected-tag chips with their remove buttons (`:87-108`), and the match-mode toggle (`:126-148`). All three are **active-constraint display**, which `EXPERIENCE.md:347` (the Algolia lifting) requires to stay visible outside the panel: *"active constraints must be visible regardless of where they were selected"*.

*Rejected — keep the desktop inline selects and also put them in the panel:* two live controls writing the same `status`/`source`/`sort` state is exactly the duplication this story exists to remove, and it would make the badge describe controls the user is already looking at.

*Rejected — two `Sheet` mounts gated by `lg:hidden` / `hidden lg:block`:* duplicates the whole subtree in the DOM, and 51.3's code review already flagged the duplicate-`data-testid` hazard that pattern produces (`BrowseCategoryList`'s skeleton). D-6 solves the same problem with one mount.

### D-2 — `activeFilterCount` rewrite (the `(n)` contract)

Replace `FilterRibbon.tsx:58-64` with, verbatim per `EXPERIENCE.md:227`:

```
n = selectedTagIds.length
  + (untaggedActive ? 1 : 0)
  + (status !== undefined ? 1 : 0)
  + (source !== undefined ? 1 : 0)
```

- **`sort` is NOT counted** — it is an ordering, not a constraint. This *removes* a count contribution the shipped badge has today.
- **`tag_match` is NOT counted** — it modifies an already-counted set. Note this is also why the match-mode toggle staying in the ribbon (D-1) does not affect `n`.
- **Each selected tag counts as 1**, individually — not "1 if any tags are selected".
- **`q` is NOT counted.** `EXPERIENCE.md:227` enumerates the four contributors exhaustively and `q` is not among them; `q` has its own visible surface (the search input and its 50.3 suggestion panel), and counting it would double-report text the user is looking at.
- **Category is NOT counted** — see D-7.

At `n === 0` the badge element is **not rendered at all** (`EXPERIENCE.md:204`, `DESIGN.md:279`). Never a `0`, never a hidden-but-present node.

### D-3 — Retire `TagPicker` as the tag path

Delete the `+tag` `Button` (`FilterRibbon.tsx:109-125`), the `tagPickerOpen` state (`:74`), the conditional mount (`:150-159`) and the `TagPicker` function (`:285-362`). `useTags` and `Input` imports go with it.

**Why deletion rather than demotion.** The epic sketch says the control "stops being the primary tag path". After D-1, every capability `TagPicker` had is strictly dominated: it offered a flat, ungrouped, count-less tag list behind a search box capped at `useTags`' `DEFAULT_LIMIT = 50`; the panel offers the same tags **grouped**, **with counts**, with the same search, with collapse persistence, and with the groupless section and `Bez tagów` row `TagPicker` never had. Leaving it would be a second, weaker write path into `tag_ids` — a duplicate the `EXPERIENCE.md:228` "the Filters surface stays exhaustive" posture argues against, and one more surface for E54's cross-surface audit to reconcile. Nothing in the 50.3 contract depends on it: `SearchSuggest` reads `useTags` itself (`SearchSuggest.tsx:64`) and never touches `TagPicker`.

**Consequent copy repair (required, not optional).** `catalog.suggestions.overflowNote` currently names the control being deleted. Change its **value** in both locales to point at the Filters surface, per `EXPERIENCE.md:226`. Suggested: en `"More matches — open Filters to browse all"`, pl `"Więcej wyników — otwórz Filtry, aby przejrzeć wszystkie"`. The key name, the `aria-hidden` attribute, the non-`option` / non-focus-stop status and the 7-row slice are unchanged.

**Orphaned keys removed from both locales:** `catalog.tags.pickerTitle` (only `TagPicker` used it) and `catalog.filters.openTags` (only the dying Tagi trigger and its `SheetTitle` used it). `catalog.actions.addTag`, `catalog.tags.searchPlaceholder` and `catalog.tags.noMatches` all have surviving call sites (§2) and **stay**.

### D-4 — Zero promoted groups, and why

`epics.md:4553` allows "at most **2–4** promoted groups outside it, **and only when justified**". The UX artifact narrows the ceiling to **≤ 2, desktop only** (`EXPERIENCE.md:229`, `DESIGN.md:281`) and then records the disposition explicitly at `EXPERIENCE.md:426`:

> **No promoted filter groups in MVP** — the ceiling (≤ 2, desktop only) is specified so 52.1 can enable them without a second UX pass, but `FR26-BROWSE-1`'s "only when justified" clause is not satisfied by any evidence available today.

**This story therefore ships zero promoted groups.** The controller's create-time instruction ("if the shipped data/UX does not justify promotion, choose the smallest defensible surface and document why") resolves the same way, for three independently sufficient reasons:

1. **The UX spine, which is the closed G26-UXGATE artifact, states the non-goal directly.** Overriding it would need a second UX pass, which nothing here authorises.
2. **The justification evidence does not exist.** `EXPERIENCE.md:229`'s qualification rule is "≥ 2 tags with non-zero counts", but qualification is a *floor*, not a *justification* — the justification FR26-BROWSE-1 asks for is usage evidence that a specific group is reached often enough to earn permanent chrome. The catalogue currently has zero model→category assignments (`EXPERIENCE.md:421`), the browse IA cutover shipped four days of history ago, and no usage telemetry exists in this product at all.
3. **Promotion is additive and reversible.** `EXPERIENCE.md:229`: "Promoting a group does **not** remove it from the Filters surface — it is a shortcut, never a relocation." So shipping zero costs nothing later: a follow-up story adds a promoted row without touching the panel's contents or the `(n)` formula.

Consequences the dev agent must honour: no promoted-group row component, no promoted-group i18n key, no qualification helper, no `localStorage` slot for it, no `data-testid` reserved for it. Adding any of these is scope creep against an explicit non-goal.

### D-5 — Sheet exclusivity collapses from three booleans to two

51.3's D-4.4 recorded this handoff verbatim. `CatalogList.tsx:59-83` currently carries `mobileBrowseOpen` / `mobileTagsOpen` / `mobileFiltersOpen`. After D-1 there is one filter surface, so `mobileTagsOpen` and `mobileFiltersOpen` collapse into a single `filtersOpen`, and the three-way cross-closing becomes a two-way Browse ↔ Filters invariant — which is exactly what `EXPERIENCE.md:62` and `:333` specify ("The Browse sheet and the Filters sheet are siblings — opening one closes the other").

Keep the shipped naming pattern: `mobileBrowseOpen` stays as-is; the new boolean is `filtersOpen` (**not** `mobileFiltersOpen` — after D-6 the panel exists on desktop too, so a `mobile` prefix would be a lie). The Browse setter closes Filters; the Filters setter closes Browse. `BrowseSheet` and its trigger are otherwise untouched.

Per `EXPERIENCE.md:367`, the panel's open/closed state is **deliberately not in the URL**. Do not add a search param, and do not persist it.

### D-6 — One `Sheet`, responsive side

`EXPERIENCE.md:328-331` and `DESIGN.md:237-239`: at `≥ lg` the Filters surface is a **right** panel/drawer; below `lg` it is a **bottom** sheet. Today's two surfaces are `side="left"` (the relocated facet sheet — 51.1's D-2 explicitly deferred re-siding to this story) and `side="bottom"` (the `md:hidden` selects sheet).

Render **one** `Sheet` whose `side` is `"right"` at `lg`+ and `"bottom"` below. Resolve the regime with a **file-local** hook in `FiltersPanel.tsx`:

- Subscribe to `window.matchMedia("(min-width: 1024px)")` via `useSyncExternalStore` (React 19; no polling, no `resize` listener).
- **jsdom-safe fallback:** if `typeof window === "undefined" || typeof window.matchMedia !== "function"`, return `false` (compact/bottom). Vitest runs in jsdom where `matchMedia` is not implemented by default; the fallback must be a plain branch, not a `?.` that yields `undefined`.
- `1024` is the Tailwind `lg` breakpoint the rest of this epic already keys on (`BrowseRail.tsx`'s `lg:flex`, `BrowseSheet`'s `lg:hidden`, `FacetSidebar.tsx:103`). It is a **contract-pointing** constant: it is the `lg` regime boundary `EXPERIENCE.md:330` names, not a number copied from a neighbouring file.

Do not add this hook to `@/lib` or `@/ui` — a shared primitive is a wider blast radius than this story needs, and no second consumer exists. If a second one appears, promoting it is that story's call.

Geometry: at `lg`+ keep the shipped facet-sheet width vocabulary (`w-80 max-w-[85vw]`) so the panel matches the rail's `w-60`-class column language without a new size token; below `lg` keep the shipped bottom-sheet vocabulary (`max-h-[80vh] overflow-y-auto`) from `FilterRibbon.tsx:181`. No new `--color-*`, radius, shadow or font token (`EXPERIENCE.md:425`); the panel uses `{components.filters-surface}` = `bg-card` + `border-border` and carries the shipped shadcn sheet elevation (`DESIGN.md:250` — the panel floats and goes away, unlike the scope chip).

### D-7 — Category exclusion is structural, not subtractive

`FiltersPanel` receives **no** category, scope or slug prop. `FilterRibbonState` has no category field. `CatalogList.tsx:164-165` already strips a stray `category` search token at one seam and `:108` sources the scope from the path. So `n` **cannot** include the scope even by mistake — which is the invariant 51.2's §12 item 6 handed forward ("the badge it introduces must still exclude category scope").

Do **not** implement this as "compute a count then subtract the category". Prove it with a test that mounts the panel under an active `/categories/$slug` scope with no other constraints and asserts the badge is absent (`n === 0`), per `EXPERIENCE.md:222` and `:451`.

### D-8 — `FacetSidebar` is relocated, not rewritten

`FacetSidebar.tsx` gets a **zero-line diff**. `FiltersPanel` mounts it with `mobile` (the full-width, no-`border-r` form — the only form any live mount uses today) and passes the same six props `CatalogList.tsx:384-392` passes now. Specifically **do not**:

- re-implement tag search inside `FiltersPanel` (`FacetSidebar.tsx:107-113` already has it, and `EXPERIENCE.md:249` says its no-match copy is "unchanged");
- change the `localStorage` key `catalog:facet-collapse` or the `DEFAULT_EXPANDED_GROUP_COUNT = 2` default (`EXPERIENCE.md:228`: "Group collapse state stays in `localStorage` under the shipped key");
- pass `untaggedCount` — it is optional, nothing computes it today, and no endpoint supplies it (see D-9).

### D-9 — No new backend surface

Everything this story renders comes from hooks already mounted in `CatalogList.tsx`: `useTagGroups()` (`:85`) for groups/groupless/counts, `useTags()` (`:86`) for the chip label map, `useModels()` (`:99`) for results. The panel adds **zero** requests. Creating an endpoint, or extending `GET /api/tag-groups` / `GET /api/tags`, is explicitly out of scope — verification above shows the shipped contracts already carry every field the surface needs (`TagReadWithCount.model_count` is required, groups carry `position` and `tags[]`).

The one thing the shipped contracts do **not** supply is an "untagged models" count. That is why `untaggedCount` stays unpassed and the `Bez tagów` row renders label-only, exactly as it does today.

### D-10 — Trigger accessible name carries the count

`DESIGN.md:279`: sliders glyph + "Filters" + count badge; badge `bg-primary`, `{rounded.full}`, omitted entirely at `n === 0`. The count must be in the **accessible name**, not only in a visual badge — a screen-reader user must hear "Filtry (3)", not "Filtry".

- `n === 0` → accessible name is `t("catalog.filters.openFilters")` ("Filters"/"Filtry"), no badge node.
- `n > 0` → accessible name is a **new key** `catalog.filters.openFiltersWithCount` = en `"Filters ({{count}})"`, pl `"Filtry ({{count}})"`. No `_one/_few/_many` plural forms: a parenthesised numeral is grammatically invariant in both locales, and `EXPERIENCE.md:204`'s own examples ("Filtry (3)" / "Filters (3)") are the literal contract.

The badge span itself is decorative once the count is in the accessible name — mark it `aria-hidden` so the number is not announced twice (the same technique `SearchSuggest.tsx:217` uses for the overflow note).

Target size: the trigger must be ≥ 24×24 CSS px (`{spacing.target-min}`, `EXPERIENCE.md:302` / SC 2.5.8) at every viewport, badge included.

### D-11 — Two update paths into the panel stay separate

`CatalogList` writes the search layer through **three** distinct handlers today, and they are not interchangeable:

- `setFilters` (`:176-196`) — used by `FilterRibbon`. It normalises `tag_match` inline: a non-default value is only persisted while `tag_ids.length >= 2` (review 2026-07-20), because the toggle that sets it hides below that threshold.
- `toggleTag` (`:198-212`) — used by `FacetSidebar`. It deliberately does **not** normalise `tag_match` itself; it lets the route's `validateSearch` do it (the E44.2 enforcement layer).
- `toggleUntagged` (`:214-222`) — used by `FacetSidebar`.

After D-1 both consumers live inside one panel, which makes "unify them into a single `onChange`" look tempting. **Do not.** Routing facet toggles through `setFilters` would move `tag_match` normalisation from `validateSearch` to the component and silently change the stranded-`tag_match` behaviour E44.2 and the 2026-07-20 review both pinned down. `FiltersPanel` takes `onChange` (for the three `Select`s) and `onToggleTag` / `onToggleUntagged` (for the facet list) as separate props and passes each straight through.

### D-12 — Tab order

`EXPERIENCE.md:278`: rail → toolbar (search, Browse, Filters) → scope chip → grid → pagination. Today's toolbar has Browse and Tagi in one row (`CatalogList.tsx:344-395`) and the search input in the row below (`:409-422`). After D-1 the toolbar carries: search (`FilterRibbon`), Browse trigger, Filters trigger. Place the Filters trigger **after** the Browse trigger in DOM order so keyboard traversal matches the specified reading order without any `tabIndex` juggling. Do not add positive `tabIndex` anywhere.

---

## 4. Acceptance Criteria

**The consolidated surface**

1. Exactly **one** refinement trigger is rendered per viewport: a button with the `SlidersHorizontal` icon and the `catalog.filters.openFilters` label. The former `catalog.filters.openTags` ("Tagi") trigger and the former `md:hidden` "Filtry" trigger are both gone from the DOM at every viewport.
1a. The Filters trigger is **not** breakpoint-gated — it renders at every viewport, unlike the Browse trigger, which keeps its `lg:hidden` gate because the desktop rail already covers `lg`+. Below `lg` the two sit side by side in one toolbar row (`EXPERIENCE.md:333`); at `lg`+ the toolbar carries search + Filters only.
2. Activating the trigger opens one `Sheet` containing, in this order: the `FacetSidebar` surface (tag-search input, collapsible groups with per-tag counts, groupless section when non-empty, trailing `Bez tagów` row), then the status `Select`, then the source `Select`, then the sort `Select`.
3. At `≥ lg` the sheet renders on the **right**; below `lg` it renders on the **bottom**. Only one `Sheet` is mounted — no duplicated content subtree, no duplicated `data-testid`.
4. The desktop inline status/source/sort row (`FilterRibbon.tsx:192-194`) is removed; those three controls exist only inside the panel, and each still writes the same `FilterRibbonState` fields with the same `ANY_STATUS`/`ANY_SOURCE` sentinel semantics as before.
5. `FacetSidebar.tsx` has a **zero-line diff**. Group collapse state still persists under `catalog:facet-collapse`, still defaults to the first 2 groups expanded, and still force-expands during an active in-panel search.
5a. Facet toggles still route through `CatalogList`'s existing `toggleTag` / `toggleUntagged`, and the three `Select`s still route through `setFilters`. The three handlers are not merged (D-11), so `tag_match` normalisation stays where E44.2 put it and the stranded-`tag_match` behaviour is unchanged.
5b. `FiltersPanel` renders no loading, skeleton, spinner, retry or error branch of its own; `CatalogList.tsx:258-276` still guards upstream.

**The `(n)` badge**

6. The badge count equals `tag_ids.length + (untagged ? 1 : 0) + (status !== undefined ? 1 : 0) + (source !== undefined ? 1 : 0)`.
7. Changing `sort` away from `recent` does **not** change the count. Toggling `tag_match` between `all` and `any` does **not** change the count. A non-empty `q` does **not** change the count.
8. Selecting three tags yields a count of exactly 3 (each tag counts individually).
9. At `n === 0` no badge element is rendered at all — not a `0`, not a visually-hidden node.
10. On `/categories/$slug` with an active scope and no other constraint, `n === 0` and no badge is rendered. The panel receives no category/scope prop, so the exclusion is structural.
11. The trigger's accessible name is `catalog.filters.openFilters` at `n === 0` and `catalog.filters.openFiltersWithCount` (rendering the number) at `n > 0`. The badge span is `aria-hidden` so the count is announced exactly once.

**Retiring the `+tag` path**

12. The `+tag` button, the `tagPickerOpen` state and the `TagPicker` component are removed from `FilterRibbon.tsx`. No other component gains a `TagPicker`-equivalent.
13. Selected-tag chips with their remove buttons (`catalog.tags.removeTag`) and the ≥2-tag match-mode toggle (`catalog.filters.matchMode` / `matchAll` / `matchAny`) remain rendered **outside** the panel, in `FilterRibbon`, with unchanged behaviour.
14. Every tag reachable through the old `TagPicker` is reachable inside the panel: all grouped tags, all groupless tags, via the in-panel search or by expanding a group.
15. `SearchSuggest.tsx` has no behavioural change. Enter with nothing arrow-selected still only closes the panel and never converts typed text into a tag; selecting a tag row is still an explicit act that appends the canonical `tag_id` and clears `q` atomically; the 8-row cap and the no-internal-scrollbar rule still hold.

**Exclusivity and state**

16. Exactly two sheet-open booleans remain in `CatalogList.tsx`: `mobileBrowseOpen` and `filtersOpen`. Opening Browse closes Filters; opening Filters closes Browse. The two are never simultaneously open.
17. The panel's open/closed state is not written to the URL and not persisted.
18. Tab order through the toolbar is search → Browse → Filters, matching `EXPERIENCE.md:278`. No positive `tabIndex` is introduced.

**Promoted groups**

19. **Zero** promoted group controls ship. No promoted-group component, i18n key, qualification helper or reserved test id exists in the diff.

**i18n**

20. Exactly one key is added: `catalog.filters.openFiltersWithCount`, in both `en.json` and `pl.json`, with a genuine Polish value (not English-identical).
21. `catalog.suggestions.overflowNote` changes **value** in both locales to point at the Filters surface; the key name and its call site's attributes are unchanged.
22. Exactly two keys are removed from both locales: `catalog.tags.pickerTitle` and `catalog.filters.openTags`. `catalog.actions.addTag`, `catalog.tags.searchPlaceholder` and `catalog.tags.noMatches` are **not** removed (each has a surviving call site).
23. A key-set diff between `en.json` and `pl.json` is 1:1 after the change, and no key is left with a call site that no longer exists (other than the pre-existing `catalog.filters.tags` orphan, which this story does not touch).

**Accessibility**

24. Component-level a11y assertions cover: the trigger's accessible name at `n === 0` and `n > 0` (AC-11); the sheet's accessible name via `SheetTitle` (`catalog.filters.title`); focus trap while open, `Escape` closing, and focus returning to the trigger; and a ≥24×24 CSS-px trigger target.
25. Every interactive control introduced or relocated by this story is reachable by keyboard alone, and the three `Select`s keep their existing `aria-label`s (`catalog.filters.status` / `.source` / `.sort`).

**Tests / visual**

26. Targeted unit coverage exists for: the `n` formula including each negative case in AC-7; the zero-badge case; the structural category exclusion (AC-10); the responsive-side resolution including the jsdom fallback; and the two-way Browse ↔ Filters exclusivity.
27. Targeted Playwright visual coverage exists at pl-PL for the panel: desktop right-panel open, mobile bottom-sheet open, trigger with a badge, trigger without a badge — each in light **and** dark, each with an explicit `toBeVisible()` before the screenshot.
28. `remaining-sheets-open.spec.ts`, `filter-ribbon-selects-open.spec.ts` and `facet-filtering.spec.ts` are re-pointed at the surviving surfaces; no spec is left clicking a control this story deleted.

---

## 5. Ask First / Never

**Never** (hard boundaries — do not attempt even as a "better" idea):

- Ship any promoted group control, or any scaffolding for one (D-4, `EXPERIENCE.md:426`).
- Count `sort`, `tag_match`, `q` or the category scope toward `n` (`EXPERIENCE.md:227`, `:222`).
- Render the badge as `0` (`EXPERIENCE.md:204`).
- Merge the Browse surface and the Filters surface into one sheet with tabs (`EXPERIENCE.md:333`: "never merged").
- Add, extend or invent a backend endpoint, or add any request to the panel's path (D-9). Everything needed is already loaded.
- Change any 50.3 behaviour in `SearchSuggest.tsx` — the Enter semantics, the explicit-tag-selection rule, the 8-row cap, the no-internal-scrollbar rule, the `aria-label`/`aria-describedby` accname split, or the verbatim pl `tagOption` string asserted by `suggestions-i18n.test.ts:39-43`. The overflow-note **value** (AC-21) is the single permitted edit in that neighbourhood.
- Modify `FacetSidebar.tsx` (AC-5), including "cleaning up" its now-dead non-`mobile` `<aside>` branch.
- Change `shell/ModuleRail.tsx` (`EXPERIENCE.md:292`, standing boundary since 48.1).
- Put the panel's open state in the URL or in `localStorage` (`EXPERIENCE.md:367`).
- Add a new `--color-*` token, font, radius or shadow (`EXPERIENCE.md:425`).
- Touch category assignment, admin CRUD or curation QA — those are Stories 52.2 and 52.3.
- Remove `catalog.actions.addTag` (still used by `TagGroupsSection.tsx:96`), `catalog.tags.searchPlaceholder` or `catalog.tags.noMatches` (both still used by `FacetSidebar`).
- Promote D-6's media-query hook into `@/lib` or `@/ui`.
- Write Polish or English copy inline; every user-visible string goes through `t()` with keys in both locale files.

**Ask First** if, during implementation:

- The one-`Sheet`-with-responsive-`side` approach (D-6) turns out to require editing `@/ui/sheet` itself (a shared shadcn primitive) rather than staying local to `FiltersPanel.tsx` — e.g. if the primitive latches `side` at mount and cannot re-render across the breakpoint. Stop and confirm before either patching the primitive or falling back to two mounts.
- Removing the desktop inline selects (D-1 / AC-4) turns out to move a baseline outside the catalog surface — i.e. anything other than the catalog/browse/filter/empty-state/focus-ring/axe spec families listed in §7.
- The `n`-formula change (D-2) breaks an existing assertion that encodes the **old** count semantics in a way that is not a straightforward re-point — that would mean a shipped surface depends on `sort` being counted, which contradicts the UX contract and deserves a decision rather than a silent test edit.
- Deleting `TagPicker` (D-3) turns out to strand a tag that is reachable *only* through it and not through the panel (AC-14 fails) — that would falsify D-3's dominance argument and the control should be kept pending a decision.
- A `browse-rail-*` or `browse-sheet-*` baseline moves at **desktop** — the Browse surfaces are not in this story's scope and a desktop rail movement signals leakage.

---

## 6. Tasks / Subtasks

- [x] **Task 1 — Build `FiltersPanel` (AC: 1, 2, 3, 5, 24, 25)**
  - [x] New `apps/web/src/modules/catalog/components/FiltersPanel.tsx`: controlled `Sheet` (`open`/`onOpenChange`), `SheetHeader`/`SheetTitle` = `catalog.filters.title`, body = `<FacetSidebar mobile ...>` then `<FilterSelects fullWidth>`.
  - [x] Move `FilterSelects` verbatim from `FilterRibbon.tsx:199-283` (plus the `ANY_STATUS`/`ANY_SOURCE`/`STATUS_VALUES`/`SOURCE_VALUES`/`SORT_VALUES` constants it needs) into `FiltersPanel.tsx`. No behaviour edit.
  - [x] Implement the file-local `lg` media-query hook per D-6, with the jsdom-safe fallback; `side = isDesktop ? "right" : "bottom"`.
- [x] **Task 2 — Trigger, badge and the `n` formula (AC: 6, 7, 8, 9, 10, 11)**
  - [x] Implement `activeFilterCount` per D-2 inside `FiltersPanel.tsx`; delete the old one from `FilterRibbon.tsx:58-64`.
  - [x] Trigger: `SlidersHorizontal` + label; accessible name switches on `n > 0` per D-10; badge span `aria-hidden`, `bg-primary`, `rounded-full`, omitted entirely at `n === 0`; target ≥24×24.
- [x] **Task 3 — Subtract from `FilterRibbon` (AC: 4, 12, 13)**
  - [x] Delete the `+tag` `Button`, `tagPickerOpen`, the conditional `TagPicker` mount and the `TagPicker` function; drop the now-unused `useTags`, `Input`, `Sheet*`, `Select*`, `SlidersHorizontal` imports.
  - [x] Delete `FilterRibbon`'s own `Sheet` (`:162-189`) and the desktop inline `FilterSelects` row (`:192-194`), plus the `filtersSheetOpen`/`onFiltersSheetOpenChange` props 51.3 added.
  - [x] Keep `SearchSuggest`, the tag chips + remove buttons, and the match-mode toggle exactly as they are.
- [x] **Task 4 — `CatalogList` rewiring (AC: 1, 16, 17, 18)**
  - [x] Delete the Tagi `Sheet` block (`:360-394`) and its `FacetSidebar` mount; render `<FiltersPanel>` in the same toolbar row, **after** the Browse trigger.
  - [x] Collapse `mobileTagsOpen` + `mobileFiltersOpen` into one `filtersOpen`; reduce the cross-closing logic to the two-way Browse ↔ Filters invariant (D-5).
  - [x] Pass `groups`/`groupless`/`selectedTagIds`/`onToggleTag`/`untaggedActive`/`onToggleUntagged` through to `FiltersPanel` (the same six values the Tagi mount passed to `FacetSidebar`).
- [x] **Task 5 — i18n (AC: 20, 21, 22, 23)**
  - [x] Add `catalog.filters.openFiltersWithCount` to `en.json` + `pl.json`.
  - [x] Change the `catalog.suggestions.overflowNote` value in both locales per D-3.
  - [x] Remove `catalog.tags.pickerTitle` and `catalog.filters.openTags` from both locales.
  - [x] Add `apps/web/src/modules/catalog/filters-i18n.test.ts` mirroring `browse-i18n.test.ts`'s shape: `catalog.filters.*` en/pl key-set equality, a **literal** key count, non-empty in both locales, and no pl value identical to its en value. Run a full-file en/pl key-set diff and record the before/after totals.
- [x] **Task 6 — Tests (AC: 26, 27, 28)**
  - [x] Unit `FiltersPanel.test.tsx`: the `n` formula (each contributor and each AC-7 negative), zero-badge, accessible-name switch, `aria-hidden` badge, panel contents and their order, `SheetTitle` accname, focus trap / `Escape` / focus return, ≥24×24 target, desktop-vs-compact side resolution and the jsdom fallback, and the AC-10 scoped no-badge case.
  - [x] Update `FilterRibbon.test.tsx` (14 cases today): drop the `TagPicker` cases; remove the `filtersSheetOpen` / `onFiltersSheetOpenChange` props from **all** call sites (51.3 added them to 14 of them); keep chips/remove/match-mode coverage.
  - [x] Update `CatalogList.test.tsx` (44 cases today): rewrite the 51.3 three-way exclusivity block as a two-way Browse ↔ Filters block; re-point anything querying the "Tagi" trigger.
  - [x] Re-point visual specs: `remaining-sheets-open.spec.ts:90-112` (both tests), `filter-ribbon-selects-open.spec.ts` (selects now open inside the panel), `facet-filtering.spec.ts:210-266` (the `TagPicker` test becomes an in-panel tag-selection test; the match-mode test keeps its subject but reaches it through the panel).
  - [x] New `apps/web/tests/visual/filters-panel.spec.ts` per AC-27, each screenshot preceded by an explicit `toBeVisible()` (epic:45 TEST-AUTHORING rule).
- [x] **Task 7 — Merge-gate obligations (every E52 story owns these, `epics.md:4549`)**
  - [x] Component-level a11y assertions (Task 6) — this story's own gate, not E54's.
  - [x] pl-PL targeted visual coverage (Task 6; the Playwright harness forces `pl-PL` across all four projects).
  - [x] Baseline triage: inspect every diff image before regenerating; classify each moved baseline as INTENTIONAL FEATURE DELTA or investigate. Record the full per-family count in the Dev Agent Record.
  - [x] Baseline commit-message `baseline-reviewed:` lines must name the agent that actually inspected them, never `Ezop` or any human (standing provenance requirement; open action item at epic:45 / epic:46 / epic:51).
- [x] **Task 8 — Handoff bookkeeping**
  - [x] Close the `epic-51` `action_items` entry owned by `E52 (52.1)` (51.1's D-2 interim-label/side handoff) at merge time; record 51.2 §12 item 6 (badge excludes category scope) as discharged by AC-10.

---

## 7. Expected baseline surface (read before regenerating anything)

This story changes the catalog toolbar on **every** viewport, so the moving-baseline surface is larger than 51.3's. Expected families:

- **New:** `filters-panel.spec.ts` baselines (AC-27).
- **Retired or renamed:** `remaining-sheets-open.spec.ts/{filter-ribbon-mobile-filters-sheet-open, catalog-list-mobile-tags-sheet-open}-*`, `facet-filtering.spec.ts/filter-ribbon-tag-picker-open-*`, and the `filter-ribbon-selects-open.spec.ts` family (the desktop inline selects no longer exist).
- **Regenerated (desktop **and** mobile, unlike 51.3's mobile-only set):** `catalog-list.spec.ts`, `facet-filtering.spec.ts`, `category-browse.spec.ts`, `catalog-search-suggestions.spec.ts`, `empty-states.spec.ts`, `focus-ring.spec.ts`, `browse-sheet.spec.ts` (mobile toolbar row changes), `accessibility-axe.spec.ts` if it screenshots.
- **Must NOT move at desktop:** `browse-rail.spec.ts`. A desktop rail movement is the §5 Ask-First signal that the toolbar change leaked into the browse column.

Do not blanket-`--update-snapshots`. Inspect diffs per family and record the classification.

---

## 8. Tests / Gates (dev-story owns running and reading these)

- `npm run typecheck` (`tsc -b`) rc=0.
- `npm run lint` (`--max-warnings=0`) rc=0 — note `react-refresh/only-export-components` is a gating warning; keep `FiltersPanel.tsx`'s exports to components only.
- `npm run test` — full vitest, including the new/updated files above.
- `npm run build` rc=0. No route change, so **no** `routeTree.gen.ts` diff is expected — flag one if it appears.
- Targeted `npm run test:visual` across the families in §7, then the full four-project run before the gate.
- `git diff --check` rc=0.
- Full `infra/scripts/check-all.sh` remains controller-owned at closeout, same as 51.1–51.4.

---

## 9. Dev Notes

- `noUncheckedIndexedAccess` is on: any indexed access in the count logic yields `T | undefined`. Do not paper over with `!`.
- `verbatimModuleSyntax` is on: type-only imports need `import type`.
- Vitest runs with `globals: false` — every new test file with multiple `it` blocks needs `import { cleanup } from "@testing-library/react"; afterEach(cleanup);`.
- Do not mock `api()`; the panel makes no requests of its own anyway (D-9).
- Reuse `t("catalog.filters.title")`, `t("catalog.tags.searchPlaceholder")`, `t("catalog.tags.noMatches")`, `t("a11y.expand")`, `t("a11y.collapse")` verbatim — no parallel copy.
- `SlidersHorizontal` and the `Sheet`/`Select` primitives are already imported in the catalog module today; no new package.
- The shipped `@/ui/sheet` primitive **already** returns focus to its trigger on close and already traps focus while open — 51.3 verified this against real DOM focus rather than assuming it (`BrowseSheet.test.tsx`'s last case) and added **no** manual restoration code. Assert the behaviour (AC-24); do not re-implement it, and do not touch `@/ui/sheet`.
- The badge's solid `bg-primary` fill is the one sanctioned solid-primary use here; `primary`-at-10% + inset ring is reserved for the *location* vocabulary (rail row, scope chip, model-detail category link) and must not appear on a filter control (`DESIGN.md:203`).

### Project Structure Notes

- New component lands in `apps/web/src/modules/catalog/components/` alongside `BrowseSheet.tsx` / `FacetSidebar.tsx`, matching the module layout rule (`modules/<name>/{routes,components,hooks}`).
- Colocated test `FiltersPanel.test.tsx`; visual spec in `apps/web/tests/visual/`.
- No variance from the unified structure. The only cross-file movement is `FilterSelects` (component → component within the same directory).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 52.1` — lines 4543-4553]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md#Component Patterns` — lines 227-229]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md#Non-goals` — line 426]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md#Responsive Behaviour` — lines 328-333]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/DESIGN.md#Components` — lines 123-136, 279-281]
- [Source: `_bmad-output/implementation-artifacts/51-3-mobile-browse-surface.md#Design decisions` — D-4.4 handoff]
- [Source: `_bmad-output/implementation-artifacts/51-1-desktop-browse-navigation.md#Forward handoffs` — items 2 and 3]
- [Source: `_bmad-output/implementation-artifacts/50-3-inline-structured-suggestions.md#Design decisions` — D-3 overflow-note interim wording]
- [Source: `_bmad-output/project-context.md#Frontend`]

---

## 10. Open questions (recorded, non-blocking)

- **Q1 (informational).** D-1 removes the desktop inline status/source/sort row, so on desktop those three controls go from always-visible to one-click-away. That is what `EXPERIENCE.md:228` and `DESIGN.md:239` specify, and it is the whole point of "consolidate", but it is the most user-visible regression risk in this story. If the controller would rather keep sort inline on desktop, that is a scoped amendment — the recorded recommendation is **no**, because `EXPERIENCE.md:56` and `:228` both list sort inside the surface and a duplicated control would contradict the single-state-model rule.
- **Q2 (informational).** D-6 introduces the first `matchMedia` usage in the codebase. It is file-local by design. If a second consumer appears in 52.2/52.3, promoting it to `@/lib` is that story's call, not this one's.

---

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), repo-local Claude Code, native `bmad-dev-story`. Single dev pass on branch `feat/E52.1-filters-drawer-consolidation`, baseline `cc5e6e8`. **Authorization posture:** `G26-DEVGO` granted by Laura/controller under Ezop's standing Initiative 26 delegation. **NOT** an Ezop signature, **NOT** human review, **NOT** human sign-off. No Codex, no Gemini, no Aider, no subagents. No commit, push, merge, deploy or external review in this pass — all controller-owned.

### Debug Log References

- Final full visual run: `/tmp/vfull-final.txt` — **600 passed, 36 skipped, 0 failed** (4 projects, pl-PL).
- Pre-regeneration triage run: `/tmp/vfull.txt` — 536 passed, 36 skipped, **64 failed**; all 64 classified below before any baseline was written.
- Gate logs: `/tmp/g-tc.txt` (typecheck), `/tmp/g-lint.txt` (lint), `/tmp/g-test.txt` (vitest), `/tmp/g-build.txt` (build).
- **Discarded run (do not cite):** an intermediate full-suite run reported "536 passed / 0 failed" while a stale dev server was being reused. It was invalidated by re-running `catalog-list.spec.ts` from a cold server (4/4 failed as expected). Every visual number quoted here comes from a run whose dev server was started fresh by Playwright.

### Gate Results (run by this dev pass)

| Gate | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` (`tsc -b`) | **rc=0** — `/tmp/g-tc.txt` |
| Lint | `npm run lint` (`eslint --max-warnings=0` + stylelint) | **rc=0** — `/tmp/g-lint.txt` (no `react-refresh/only-export-components` warning; `FiltersPanel.tsx` exports only the component) |
| Unit | `npm run test` (vitest) | **rc=0 — 149 files, 985/985 passed** — `/tmp/g-test.txt` |
| Build | `npm run build` | **rc=0** — `/tmp/g-build.txt`; **no `routeTree.gen.ts` diff**, as §8 predicted (verified via `git status`) |
| Visual | `npm run test:visual` (4 projects, pl-PL, light+dark, desktop+mobile) | **600 passed, 36 skipped, 0 failed** — `/tmp/vfull-final.txt` |
| Whitespace | `git diff --check` | **rc=0** |
| Full `check-all.sh` | `infra/scripts/check-all.sh` | **NOT RUN — controller-owned at closeout**, same as 51.1–51.4 |

New/changed test counts this story owns: `FiltersPanel.test.tsx` **30 cases** (new), `filters-i18n.test.ts` **7 cases** (new), `FilterRibbon.test.tsx` rewritten (TagPicker/Select cases retired, absence assertions added), `CatalogList.test.tsx` exclusivity block rewritten three-way → two-way plus AC-10 / AC-17 / AC-18 / AC-2 / AC-5a coverage added.

### Completion Notes List

**Implementation (Tasks 1–5).**

- `FiltersPanel.tsx` is the one canonical surface: one `Sheet`, `side="right"` at `lg`+ and `"bottom"` below, resolved by a file-local `useSyncExternalStore` + `matchMedia("(min-width: 1024px)")` hook with a plain-branch jsdom fallback to the compact regime (D-6). Verified as a single mount — the test asserts exactly one `[data-slot='sheet-content']`, one tag-search input and one Untagged row, so no duplicated subtree or `data-testid`.
- `FilterSelects` moved verbatim from `FilterRibbon.tsx` into `FiltersPanel.tsx`; the only edit was dropping the now-redundant `fullWidth` prop (inside the panel every trigger is `w-full`, which is exactly what the shipped mobile Filters sheet already did). Same `ANY_STATUS`/`ANY_SOURCE` sentinels, same `aria-label`s, same `SelectValue` render props.
- `activeFilterCount` rewritten per `EXPERIENCE.md:227`: `tag_ids.length + untagged + status + source`. `sort` is **no longer counted** — a deliberate behaviour change to a shipped badge. `tag_match`, `q` and the browse scope contribute nothing.
- D-7 honoured structurally: `FiltersPanel`'s `Props` carry no category/scope field at all, so the scope is unreachable rather than subtracted.
- D-11 honoured: `onChange` (Selects) and `onToggleTag`/`onToggleUntagged` (facets) stay three separate props passed straight through, so `tag_match` normalisation stays in the route's `validateSearch` (E44.2 layer).
- `FacetSidebar.tsx`: **zero-line diff**, as required by AC-5. Confirmed by `git diff --stat` (file absent from the diff).
- `SearchSuggest.tsx`: **zero-line diff**. Only the `catalog.suggestions.overflowNote` locale *value* changed, in both locales.
- `FilterRibbon.tsx` shrank 362 → 90 lines: `TagPicker`, the `+tag` button, `tagPickerOpen`, its own `Sheet`, the desktop inline select row, `activeFilterCount`, the `filtersSheetOpen`/`onFiltersSheetOpenChange` props and the `useTags`/`Input`/`Sheet*`/`Select*`/`SlidersHorizontal`/`Button` imports are all gone. It retains exactly the three active-constraint-display concerns `EXPERIENCE.md:347` requires outside the panel.
- **Zero promoted groups shipped** (D-4). No promoted-group component, i18n key, qualification helper, `localStorage` slot or reserved test id exists anywhere in the diff.
- i18n: full-file en/pl key sets verified 1:1 **before and after** — 921 → 920 keys in each locale. Added `catalog.filters.openFiltersWithCount`; removed `catalog.filters.openTags` and `catalog.tags.pickerTitle`. `catalog.actions.addTag`, `catalog.tags.searchPlaceholder` and `catalog.tags.noMatches` kept (surviving call sites). `catalog.filters.*` holds at 14 keys. `catalog.filters.status` is the single legitimately-identical en/pl pair (a true cognate) and is allow-listed by name in the new parity test rather than by weakening the guard.

**Deviation from the story text, recorded (AC-18 vs Task 4 ordering).**

Task 4 says to render `FiltersPanel` in the Browse trigger's toolbar row, after the Browse trigger — done. But that row shipped **above** the `FilterRibbon` (search) row, which would have produced a DOM/tab order of Browse → Filters → search, contradicting AC-18 and `EXPERIENCE.md:278` (search → Browse → Filters). The two sibling toolbar blocks were therefore **swapped** so the search row comes first. No positive `tabIndex` was introduced; DOM order alone produces the specified order, and a test asserts both the relative order and that no `tabindex > 0` exists anywhere on the page. The admin-only `AddModelButton` sits between search and Browse in tab order; it is not one of the three controls `EXPERIENCE.md:278` sequences, and the specified relative order of those three holds exactly. This is the single most user-visible layout consequence of the story and is flagged for controller review.

**Two real defects found and fixed during verification (not cosmetic).**

1. `facet-filtering.spec.ts`'s panel-opening helper matched the trigger by the exact string `"Filtry"`. Because D-10 puts the count **in the accessible name**, any test arriving with a constraint already in the URL (e.g. `?untagged=true`) sees `"Filtry (1)"` and the click times out. Fixed with `/^Filtry(\s\(\d+\))?$/`. This was a genuine consequence of the D-10 contract, caught by a failing run rather than by inspection.
2. Two visual specs outside the three AC-28 names still drove the **deleted** "Tagi" trigger: `browse-rail.spec.ts:133` (re-pointed to "Filtry") and `browse-sheet.spec.ts:32` (now asserts the Tagi trigger is absent and the Filtry trigger is present, per AC-1). Without this, "no spec is left clicking a control this story deleted" would have been false.

**Baseline triage (Task 7) — every one of the 64 pre-regeneration failures classified before writing anything.**

All 64 failing instances came from exactly 20 unique tests in 8 spec files, every one inside the §7 allowlist (catalog / browse / filter / empty-state / focus-ring). No baseline outside the catalog surface moved, so the second §5 Ask-First condition did not trigger.

Classification method: for each of the 64 `test-results/**` artifact pairs, the expected and actual PNGs were diffed with PIL and the **bounding box of differing pixels** computed — not eyeballed, and not blanket-accepted.

| Family | Baselines | Classification |
|---|---|---|
| `browse-rail.spec.ts` | 14 M | INTENTIONAL FEATURE DELTA — see the rail finding below |
| `browse-sheet.spec.ts` | 6 M | INTENTIONAL — mobile toolbar row changes (§7 predicted) |
| `catalog-list.spec.ts` | 4 M | INTENTIONAL — toolbar consolidation + row swap |
| `catalog-search-suggestions.spec.ts` | 4 M | INTENTIONAL — toolbar row swap + new overflow-note copy |
| `category-browse.spec.ts` | 8 M | INTENTIONAL — mobile page height 765 → 729 px (one toolbar row's worth, three triggers becoming two) |
| `empty-states.spec.ts` | 4 M | INTENTIONAL — toolbar consolidation |
| `facet-filtering.spec.ts` | 20 M, 4 D, 4 new | INTENTIONAL — surface re-pointed to the panel |
| `focus-ring.spec.ts` | 4 M | INTENTIONAL — toolbar consolidation; the ring itself is unchanged |

**The `browse-rail` desktop finding (§5 Ask-First condition, resolved on evidence, not assumption).** §7 says `browse-rail.spec.ts` must NOT move at desktop, because a desktop rail movement signals the toolbar change leaking into the browse column. The `browse-rail` baselines **did** move at desktop — but these are `fullPage: true` screenshots that include the catalog content column, not just the rail. Of the **12** modified desktop `browse-rail` baselines, **10** have a bounding box whose **left edge is x ≥ 240** (desktop-dark: exactly 240; desktop-light: 248–479). The rail is `w-60` = 15 rem = **240 px**, so for those ten, columns 0–239 — the entire rail including its `border-r` — are pixel-identical, and the movement is confined to the content column the story owns.

The remaining **2** — `browse-rail-relocated-facets-open-desktop-{light,dark}` — differ over the **entire frame**, bbox `(0, 0, 1280, 720)`, rail columns included. That is expected and in-scope, for a reason the bbox rule cannot express: this is the one `browse-rail` test that captures the facet surface **open**, and D-6 re-sides that surface from the shipped `side="left"` (which physically covered the rail) to `side="right"` at `lg`+, while the modal backdrop dims the whole page — rail included. The rail's own geometry, contents and active-row treatment are unchanged underneath the dim; only the overlay moved. So the Ask-First condition is **not** met for these two either, but on a different argument than the x ≥ 240 one.

*(Corrected by the `bmad-code-review` pass: the original wording claimed x ≥ 240 held "in every case" across 10 diffs, which under-counted the desktop set by two and would have read as a clean bbox result for baselines the rule never covered. The classification outcome is unchanged; only the evidence statement is now accurate. Both bbox sets were independently recomputed with PIL by the review — see the Code Review Record.)*

Orphaned baselines deleted (14), all confirmed unreferenced by any spec first: `remaining-sheets-open.spec.ts/{filter-ribbon-mobile-filters-sheet-open,catalog-list-mobile-tags-sheet-open}-mobile-{light,dark}` (tests retired — their consolidated successor has its own spec), `facet-filtering.spec.ts/filter-ribbon-tag-picker-open-*` (TagPicker deleted), `filter-ribbon-selects-open.spec.ts/filter-ribbon-{status,source,sort}-open-desktop-*` (renamed to `filters-panel-*`, and the family now runs on all four projects instead of desktop-only).

**Provenance.** The baseline commit message's `baseline-reviewed:` line must name **Claude Opus 5 (repo-local `bmad-dev-story`)** — the agent that actually performed the PIL bounding-box inspection above. It must **not** name Ezop or any human.

**Task 8 handoffs discharged.** 51.2 §12 item 6 (the badge must exclude category scope) is discharged by AC-10, proven at `CatalogList` level on the real `/categories/$slug` route. The `epic-51` `action_items` entry owned by `E52 (52.1)` (51.1's D-2 interim label/side handoff) is discharged in code — the interim "Tagi" label and `side="left"` are both gone — and is marked closed in `sprint-status.yaml`; the controller owns the merge-time bookkeeping.

**Not done / controller-owned.** Full `infra/scripts/check-all.sh` (backend + repo-wide) was not run — it stays controller-owned at closeout, same as 51.1–51.4. No commit, branch, merge, push, deploy or external review was performed.

### File List

Confirmed against `git status` (123 entries: 8 source/spec/doc + 28 new baselines + 64 regenerated baselines + 14 deleted baselines + sprint-status + story file):

**Source**

- `apps/web/src/modules/catalog/components/FiltersPanel.tsx` (new)
- `apps/web/src/modules/catalog/components/FiltersPanel.test.tsx` (new)
- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` (modified — subtractive, 362 → 90 lines)
- `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` (modified)
- `apps/web/src/modules/catalog/routes/CatalogList.tsx` (modified)
- `apps/web/src/modules/catalog/routes/CatalogList.test.tsx` (modified)
- `apps/web/src/modules/catalog/filters-i18n.test.ts` (new)
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` (modified)

**Visual specs**

- `apps/web/tests/visual/filters-panel.spec.ts` (new)
- `apps/web/tests/visual/facet-filtering.spec.ts` (modified — re-pointed to the panel)
- `apps/web/tests/visual/filter-ribbon-selects-open.spec.ts` (modified — Selects now opened inside the panel, all four projects)
- `apps/web/tests/visual/remaining-sheets-open.spec.ts` (modified — two retired tests removed)
- `apps/web/tests/visual/browse-rail.spec.ts` (modified — "Tagi" → "Filtry"; **not** anticipated by the story, see Completion Notes)
- `apps/web/tests/visual/browse-sheet.spec.ts` (modified — asserts the Tagi trigger is gone; **not** anticipated by the story)

**Baselines** — 28 new, 64 regenerated, 14 deleted under `apps/web/tests/visual/__snapshots__/**` (per-family table above).

**Bookkeeping**

- `_bmad-output/implementation-artifacts/52-1-filters-drawer-consolidation.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Unchanged, and verified so:** `apps/web/src/modules/catalog/components/FacetSidebar.tsx` (AC-5 zero-line diff), `apps/web/src/modules/catalog/components/SearchSuggest.tsx` (AC-15 zero behaviour diff), `apps/web/src/shell/ModuleRail.tsx`, `apps/web/src/ui/sheet.tsx`, `apps/web/src/routeTree.gen.ts`.

### Change Log

| Date | Change |
|---|---|
| 2026-07-29 | Story 52.1 implemented by native `bmad-dev-story` (Claude Opus 5, repo-local). Three refinement controls consolidated into one `FiltersPanel`; `(n)` formula rewritten per `EXPERIENCE.md:227`; `TagPicker` retired; sheet exclusivity collapsed to two booleans; toolbar rows swapped for AC-18 tab order; i18n 921 → 920 keys; 106 baselines touched (28 new / 64 regenerated / 14 deleted) after per-image bounding-box triage. Status `ready-for-dev` → `review`. |
| 2026-07-29 | Native `bmad-code-review` pass (Claude Opus 5, repo-local). **Verdict `APPROVE`.** One `patch` applied — to the Dev Agent Record's `browse-rail` desktop bbox claim, not to any code file. Two `defer` observations added to §11 and to `deferred-work.md`. Zero code, test, locale, spec or baseline files changed by the review. Status deliberately left at `review`. |
| 2026-07-29 | Independent Aider review (`laura-aider-review-diff`, DeepSeek v3.2) recorded **Verdict `APPROVE`** from a text-only diff with PNG paths listed, no binary bytes. Full `infra/scripts/check-all.sh` closeout gate passed **16/16 all green**. Story remains `review` until commit/merge/deploy/smoke closeout. |
| 2026-07-29 | Controller full closeout complete. Implementation commit `3202b7c66aa2eff8ba5c75c7374e0084904d5a14` was fast-forward merged to `main`, pushed, deployed to `.190`, and smoke-tested green. Status `review` → `done`. |

---

## Code Review Record (native `bmad-code-review`)

**Verdict: APPROVE.** No blocking defect and no code defect requiring a patch. Status stays `review` — closure is controller-owned, same as 51.1–51.4.

- **Reviewer:** repo-local Claude Code, Claude Opus 5 (`claude-opus-5[1m]`), native BMAD `bmad-code-review`, run against the **dirty working-tree diff vs `cc5e6e8`** on `feat/E52.1-filters-drawer-consolidation`. **NOT** an Ezop signature, **NOT** human review of any kind; **no Codex, no Gemini, no Aider** (the independent Aider review stays a separate controller-owned gate).
- **Subagents:** none. The session's operator profile forbids `Agent` dispatch unless the user requests it, and the controller did not. The skill's Blind-Hunter / Edge-Case-Hunter / Acceptance-Auditor layers were therefore executed **inline** by the reviewing session rather than fanned out; the skill's alternative (emit prompt files and HALT) would have stalled a non-interactive run. Recorded rather than skipped silently. Likewise, step-01's checkpoint and step-04's patch HALT were satisfied by the controller's explicit standing instruction ("review the dirty diff vs `cc5e6e8`", "patch actionable issues if safe"), not by a fresh human prompt.
- **Date:** 2026-07-29. **Files modified by this pass:** exactly two — this artifact and `sprint-status.yaml` — plus one appended block in `deferred-work.md`. No source, test, locale, visual-spec or PNG was touched.

### Gates re-run independently by this review (not inherited from the dev record)

| Gate | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` (`tsc -b`) | **rc=0** |
| Lint | `npm run lint` (`eslint . --max-warnings=0` + stylelint) | **rc=0** (only the pre-existing "React version not specified" advisory) |
| Vitest — the four files this story owns | `npx vitest run FiltersPanel.test.tsx FilterRibbon.test.tsx CatalogList.test.tsx filters-i18n.test.ts` | **rc=0 — 97/97 passed** (`FiltersPanel` 30, `CatalogList` 47, `FilterRibbon` 13, `filters-i18n` 7) |
| Visual — the six affected families | `test:visual -- filters-panel browse-rail catalog-list remaining-sheets-open filter-ribbon-selects-open facet-filtering` | **rc=0 — 86 passed / 14 skipped / 0 failed** |
| Whitespace | `git diff --check` | **rc=0** |

The visual run started its own dev server (no reuse of a stale one — the trap the dev record's "discarded run" documents) and **regenerated nothing**: `git status` over `__snapshots__/` still lists exactly 64 M + 28 new + 14 D afterwards. The committed baselines are reproducible, not run-specific. Backend untouched → **pytest was not run and this review claims no pytest result**. Full `npm run test`, `npm run build` and `check-all.sh` were not re-run by this pass; the dev record's `/tmp/g-*.txt` and `/tmp/vfull-final.txt` (600 passed / 36 skipped / 0 failed) stand as that pass's evidence, and `check-all.sh` remains controller-owned.

### Independently verified claims

- **Zero-diff boundaries (AC-5, AC-15, §5 Never, §8):** `git diff cc5e6e8` over `FacetSidebar.tsx`, `SearchSuggest.tsx`, `shell/ModuleRail.tsx`, `ui/sheet.tsx` and `routeTree.gen.ts` → **0 lines each**. All five confirmed byte-unchanged.
- **i18n (AC-20/21/22/23), recomputed from the files rather than read from the record:** `en.json` and `pl.json` both **920 keys**, key sets **1:1** (`en-only = []`, `pl-only = []`), `catalog.filters.*` = **14**. `openFiltersWithCount` present in both with a genuine Polish value; `catalog.filters.openTags` and `catalog.tags.pickerTitle` gone from both. `catalog.actions.addTag` (live at `TagGroupsSection.tsx:96`), `catalog.tags.searchPlaceholder` and `catalog.tags.noMatches` (both live in `FacetSidebar`) all retained. A repo-wide grep for the two removed keys and for `TagPicker`/`tagPickerOpen` finds **no** surviving call site — only comments and the guard assertions in `filters-i18n.test.ts`. `catalog.filters.tags` remains the documented pre-existing orphan.
- **Baseline accounting, recounted:** **28** new PNGs, **64** modified, **14** deleted — matching the record exactly. All 14 deletions are **staged in the index** (`git rm`) while everything else is unstaged; that is the only staged content in the tree. No spec references any deleted snapshot name.
- **No blanket regeneration:** every one of the 64 modified PNGs genuinely differs from its `cc5e6e8` predecessor — **zero** byte-identical rewrites. Six changed height (`765→729`, `775→735`, all mobile), consistent with the toolbar losing one row; this reviewer's independent measurement matches the record's "765 → 729 px" claim.
- **Out-of-family leakage (§5 Ask-First condition 2):** the touched families are `browse-rail`, `browse-sheet`, `catalog-list`, `catalog-search-suggestions`, `category-browse`, `empty-states`, `facet-filtering`, `focus-ring`, `filter-ribbon-selects-open`, `filters-panel`, `remaining-sheets-open` — **all** inside §7's catalog/browse/filter/empty-state/focus-ring allowlist. Nothing outside the catalog surface moved. Every modified `browse-sheet` baseline is `mobile-*`; **no desktop `browse-sheet` baseline moved**.
- **`browse-rail` desktop bboxes, recomputed with PIL (this is finding CR-1):** 10 of 12 confirmed at x ≥ 240 exactly as recorded (dark: 240; light: 248–479). The other 2 — `relocated-facets-open-desktop-{light,dark}` — are full-frame `(0,0,1280,720)`. The reviewer rendered that baseline: it shows the panel correctly on the **right** at `w-80`, contents in the `EXPERIENCE.md:228` order, with the rail intact beneath the modal backdrop's dim. Intentional (D-6 left→right re-siding), not leakage. Record corrected above; classification unchanged.
- **AC-18 / the layout deviation, verified in the DOM not just the prose:** `CatalogList.tsx:338-383` puts the search row (`FilterRibbon`) before the `BrowseSheet` → `FiltersPanel` row, so DOM order is search → Add-Model → Browse → Filters. The specified relative order of the three sequenced controls holds; `AddModelButton` is admin-only and is not one of them. The `CatalogList.test.tsx` assertion is non-vacuous — it uses `compareDocumentPosition` on the three real nodes and separately sweeps every `[tabindex]` in the document for a positive value. The reviewer independently confirms **no** positive `tabIndex` in the diff. The deviation is correct: honouring Task 4's literal wording would have violated AC-18, and AC-18 is the one traceable to `EXPERIENCE.md:278`.
- **Structural category exclusion (AC-10, D-7):** `FiltersPanel`'s `Props` carries no category/scope field, and `activeFilterCount(state, untaggedActive)` can only reach `tag_ids`/`status`/`source`/`untagged`. The exclusion is unreachable-by-construction, not a subtraction, and the `CatalogList` test proves it on the real `/categories/$slug` route by asserting the accessible name is bare `"Filters"` **and** that `filters-trigger-badge` is absent.
- **The `(n)` contract (AC-6/7/8/9/11):** matches `EXPERIENCE.md:227` verbatim, `sort`/`tag_match`/`q` all excluded, badge node omitted entirely at `n === 0`, count in the accessible name via `openFiltersWithCount` with the badge `aria-hidden`. The i18next `{{count}}` option triggers plural-suffix resolution in `pl` (`_few`/`_many`), which is absent by design and falls back to the base key — proven empirically, not assumed: the pl-PL visual spec matches the literal accessible name `"Filtry (2)"` with `exact: true` and passes.
- **D-11 preserved:** `onChange`, `onToggleTag` and `onToggleUntagged` remain three separate props passed straight through. `tag_match` normalisation stays in the route's `validateSearch`, and `CatalogList.test.tsx` proves an in-panel facet toggle reaches `/api/models?tag_ids=…` through `toggleTag` rather than `setFilters`.
- **`FilterSelects` move:** verbatim apart from the documented `fullWidth` removal (every trigger is `w-full` inside the panel, which is what the shipped mobile sheet already did). Same `ANY_STATUS`/`ANY_SOURCE` sentinels, same `aria-label`s, same `SelectValue` render props.
- **Lint gate §8's specific risk:** `FiltersPanel.tsx` exports only the component (`FilterSelects` is module-private), so `react-refresh/only-export-components` does not fire — confirmed by the rc=0 lint re-run, not by reading the record.

### Findings

| # | Severity | Bucket | Finding |
|---|---|---|---|
| **CR-1** | Low (record honesty; no code change) | **patch — applied** | The Dev Agent Record's `browse-rail` Ask-First resolution claimed the x ≥ 240 bbox result held "in every case" over "the 10 desktop `browse-rail` diffs". There are **12** modified desktop `browse-rail` baselines, and the two omitted (`relocated-facets-open-desktop-{light,dark}`) differ across the **whole frame including the rail columns**. The classification outcome is right — that test captures the surface *open*, and D-6 deliberately moves it from `side="left"` (which covered the rail) to `side="right"`, with the backdrop dimming the page — but §5's Ask-First condition on desktop rail movement was being resolved on evidence that silently did not cover 2 of the 12 baselines it appeared to. Patched: the paragraph now states 12, splits 10 + 2, and gives the separate argument for the pair. **No baseline and no code was changed.** |
| **CR-2** | Low | **defer** | `filter-ribbon-selects-open.spec.ts` keeps its old filename while all its tests and 18 baselines are now `filters-panel-*`. Recorded in §11; E54 visual-spec hygiene. |
| **CR-3** | Low | **defer** | `status`/`source` now have no out-of-panel representation on any viewport; only the `(n)` badge reports them. Spec-sanctioned (`EXPERIENCE.md:228`, `DESIGN.md:239`) and already flagged by §10 Q1; recorded in §11 so a future "chips for status/source" request lands in the right place. |
| — | — | **dismissed ×2** | (a) `filtersActive` (`CatalogList.tsx:268-273`, ScopeChip's `otherConstraintsActive`) counts `q` while the new badge deliberately does not — two different contracts (51.2 D-6 vs `EXPERIENCE.md:227`), each correct, diverging only on `q`, which both specify explicitly. (b) The toolbar's partial-width divider under the search row and the zero-bottom-padding trigger row are the shipped pre-`cc5e6e8` styling vocabulary, verified against the `cc5e6e8` baselines — relocated by the row swap, not introduced by it. |

**Checked and found clean (no finding):** one `Sheet` mount, asserted by test and confirmed in the diff (no breakpoint-gated duplicate subtree, no duplicated `data-testid`); the file-local `matchMedia` hook stays out of `@/lib`/`@/ui` and its jsdom fallback is a plain branch returning `false`, not an `undefined` snapshot — with `subscribe`/`getSnapshot` as stable module-level functions; **zero** promoted-group component, i18n key, qualification helper, `localStorage` slot or reserved test id anywhere in the diff (D-4 / AC-19); exactly two sheet-open booleans in `CatalogList`, cross-closing both ways, with the invariant proven across a four-step transition sweep; panel open state absent from the URL and from `localStorage`, asserted against the real router's `searchStr`; no new `--color-*`, font, radius or shadow token; `FacetSidebar` mounted with the same six props the retired Tagi sheet passed, `untaggedCount` still unpassed, `catalog:facet-collapse` and `DEFAULT_EXPANDED_GROUP_COUNT` untouched; no loading/skeleton/error branch inside the panel (AC-5b); no new request, endpoint or dependency; the `≥24×24` target met via `size="sm"` → `h-7` (28 px); focus trap, `Escape` and focus-return asserted against the shipped `@/ui/sheet` rather than re-implemented; every `toHaveScreenshot` in the new and re-pointed specs preceded by an explicit visibility assertion; the two defects the dev pass self-reported (the `"Filtry"`-exact matcher broken by D-10's counted accname, and the two specs outside AC-28 still driving the deleted "Tagi" trigger) are both genuinely fixed and were re-verified by this review's visual run.

**Ask-First / Never audit:** no Never was crossed. Of the five Ask-First conditions, one was **met and correctly resolved without escalation** — the `browse-rail` desktop movement (see CR-1) — and the other four were genuinely not met: `@/ui/sheet` is byte-unchanged so the one-`Sheet`-responsive-`side` approach needed no primitive edit; no baseline moved outside the §7 families; the old `sort`-counting badge semantics were re-pointed by straightforward test edits with no shipped surface depending on them; and AC-14 holds, so `TagPicker`'s dominance argument was not falsified.

**`baseline-reviewed:` provenance, re-affirmed:** the 106 touched PNGs were triaged by **Claude Opus 5 (`bmad-dev-story`, repo-local)** via PIL bounding-box measurement, and independently re-measured and spot-rendered (light + dark, desktop + mobile, open + closed) by **Claude Opus 5 (`bmad-code-review`, repo-local)** on 2026-07-29. The commit's `baseline-reviewed:` lines must name those agents and **never `Ezop` or any human**.

**Remaining controller-owned steps after native review:** commit (note the 14 staged deletions), ff-merge, push, deploy, post-deploy smoke, and the flip to `done`. Independent Aider review and full `check-all.sh` are now recorded below as complete.

---

## Independent External Review (Aider)

**Verdict: APPROVE.** Routine independent review was run with `laura-aider-review-diff` (Aider v0.86.2, OpenRouter `deepseek/deepseek-v3.2`) against a text-only diff that excluded PNG bytes while listing every changed/new/deleted baseline path.

- Log: `.hermes/run-logs/e52-1-aider-review-20260729_062014.log`, `RUN_EXIT rc=0`.
- Diff prompt: `.hermes/run-logs/e52-1-aider-textdiff-20260729_062014.txt`, 229444 bytes.
- Critical: none.
- Important: 2, both already recorded/deferred — the stale `filter-ribbon-selects-open.spec.ts` filename and the spec-sanctioned lack of out-of-panel status/source representation beyond the `(n)` badge.
- Minor: 2, both already recorded — the browse-rail desktop baseline-count correction patched by native CR, and visual-spec hygiene around `remaining-sheets-open.spec.ts`'s retired-control naming.
- Missing tests: none.
- Aider made **no edits** and did not review/inspect PNG pixels directly; native `bmad-dev-story` + native `bmad-code-review` remain the baseline-review provenance.

This is not an Ezop signature and not human review.

---

## Full Closeout Gate

`infra/scripts/check-all.sh` passed **16/16 all green**.

- Log: `.hermes/run-logs/check-all-e52-1-20260729_062135.log`.
- Exit marker: `CHECK_ALL_RC=0`, `2026-07-29T06:32:52+02:00`.
- Passed stages: apps/api ruff format/check; workers/render ruff format/check; apps/web typecheck, production build, lint, vitest; apps/api pytest; workers/render pytest; infra/scripts pytest; apps/web visual regression; settings/env/compose drift; uv lock checks for api/render; local-env-secrets.
- In-log headline counts: apps/web vitest **149 files / 985 tests passed**; apps/web visual regression **600 passed / 36 skipped**; check-all summary literal trailer `all green.`.

This discharges the pre-merge full-gate obligation. Remaining controller-owned steps: commit, ff-only merge to `main`, push, deploy, post-deploy smoke, then story/status flip to `done`.

---

## Controller Full Closeout

Story 52.1 is **done**.

- Implementation commit: `3202b7c66aa2eff8ba5c75c7374e0084904d5a14` (`feat(web): consolidate catalog filters panel`).
- Branch: `feat/E52.1-filters-drawer-consolidation` fast-forward merged into `main`.
- Push: `.hermes/run-logs/push-e52-1-20260729_063441.log`, `PUSH_RC=0`; lean pre-push gate **11/11 passed**.
- Deploy: `.hermes/run-logs/deploy-e52-1-20260729_063513.log`, `DEPLOY_RC=0`, `2026-07-29T06:38:36+02:00`.
- Deploy evidence: images built and shipped; docker compose restarted `api`, `arq-worker`, and `web`; alembic migrations ran; slicer-worker overlay correctly skipped because no portal-api/slicer-adjacent change in `ed4d58df3d5d28afa73d27902ee855174a97ae17..HEAD`; GlitchTip symbolication matched issue id `324` with release `0.1.0+3202b7c` and the smoke issue was deleted; runbook fingerprint OK.
- Post-deploy smoke: `.190` compose services `api`, `arq-worker`, `redis`, `slicer-worker`, `web`, and `worker` all running; LAN API health `http://192.168.2.190:8090/api/health` returned `{"status":"ok","version":"0.1.0"}`; LAN `/` returned 200; production HTTPS `/`, `/catalog/`, and `/categories/uchwyty` all returned 200.
- `main` and `origin/main` verified at `3202b7c66aa2eff8ba5c75c7374e0084904d5a14` before this docs closeout edit.

No human review or human sign-off is claimed. Closeout authority is native BMAD review + Aider review + full gate + controller-run merge/push/deploy/smoke.

---

## 11. Deferred / out-of-scope, recorded not actioned

- `FacetSidebar.tsx:101-103`'s non-`mobile` `<aside>` branch has been dead since 51.1's D-2 relocation and stays dead after this story. Cleanup candidate for E54 or a hygiene pass; **not** touched here (AC-5 requires a zero-line diff).
- `catalog.filters.tags` is an orphan key on `main` with no call site — pre-existing, not created by this story. E54.1's cross-surface i18n audit owns it.
- Sheets still do not auto-close when the viewport crosses `lg` while open (pre-existing, recorded in 51.3 §9). D-6 makes the Filters panel's **side** reactive but does not change its open state; the Browse sheet is unchanged.
- No usage telemetry exists, so the promoted-group justification bar (D-4) cannot be met by any story in this epic. Revisit only if usage data appears.
- **(Added by code review, `defer`.)** `apps/web/tests/visual/filter-ribbon-selects-open.spec.ts` keeps its Story-5.12a filename while every test inside it, and all 18 of its baselines, are now `filters-panel-*`. Its snapshot directory is therefore `__snapshots__/filter-ribbon-selects-open.spec.ts/filters-panel-{status,source,sort}-open-*.png` — a spec whose name contradicts its contents. Not renamed here: a rename relocates 18 PNGs for zero behavioural gain and would enlarge an already 106-baseline diff. Candidate for E54's visual-spec hygiene pass, together with `remaining-sheets-open.spec.ts`'s now-stale `(E5.12d)` describe title.
- **(Added by code review, `defer`.)** After D-1, an active `status` or `source` constraint has **no** representation outside the panel on any viewport — on desktop it previously showed in the inline `Select` triggers. `EXPERIENCE.md:347`'s "active constraints must be visible regardless of where they were selected" is met for those two only by the `(n)` badge, whereas tags get chips and `tag_match` gets the toggle. This is what `EXPERIENCE.md:228` / `DESIGN.md:239` specify and §10 Q1 already flags the desktop consequence, so it is not a defect against this story; recorded because a future "active filter chips for status/source" request would land here, not in the panel.
