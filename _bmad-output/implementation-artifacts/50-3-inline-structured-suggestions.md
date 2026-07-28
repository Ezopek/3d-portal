---
baseline_commit: 8f2852a1e50f66bf71e207d256ab2400cc6b19fa
---

# Story 50.3 — Inline structured suggestions (FR26-SEARCH-2, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1)

- **Epic:** E50 — Frontend data layer, URL state, and search suggestions (Initiative 26 — Catalog Discovery)
- **Status:** `review` — dev pass (native `bmad-dev-story`, implementation turn + bookkeeping-only resume turn after `error_max_turns`) then native code review (native `bmad-code-review`, 2026-07-28) then independent external review (`laura-aider-review-diff` / Aider, 2026-07-28) all completed. Native CR verdict: **APPROVE** (post-patch) — see Code Review Record below. Independent Aider verdict: **APPROVE** — see Aider Review Record below. See Dev Agent Record below for RED/GREEN evidence. Still not `done` — no full repo-wide `npm run test:visual`/`npm run build` (or `check-all.sh`), no commit/merge/deploy; all controller-owned from here.
- **Author:** Claude (native `bmad-create-story`). **Controller:** Laura.
- **Authorization posture:** Laura/controller granted this pass under the standing Initiative 26 authorization (**G26-DEVGO** recorded for downstream dev, not consumed by this create pass). **This is NOT an Ezop signature, NOT Ezop review, NOT human review of any kind.** No Codex, no Gemini, no Aider. No app code written, no gate/test/build/script run, no commit/stage/push/merge/deploy/migration/seed/live-DB/network action; this pass edited only this artifact and the sprint-status status line.
- **Created:** 2026-07-28 via native `bmad-create-story` after a mandatory `bmad-help` run. Canonical route `_bmad/_config/bmad-help.csv:26-28`: `bmad-create-story:create` (CS) → `bmad-create-story:validate` (VS) → `bmad-dev-story` (DS) → `bmad-code-review` (CR). Sprint status re-read start-to-end: `epic-50` already `in-progress` (flipped at 50.1 closeout); `50-1`/`50-2` `done`; `50-3` was the first `backlog` story key encountered. `find _bmad-output -iname '*50-3*' -o -iname '*inline-structured*'` returned nothing — no duplicate/in-progress artifact existed.
- **Validation verdict:** **PASS** — story is `ready-for-dev` for the next `bmad-dev-story` pass. Validation did not identify a BMAD protest, missing prerequisite, duplicate story, or required scope amendment beyond the decisions already captured in this artifact.
- **Scope class:** frontend-only, additive UI surface on the already-shipped `/catalog/` route. **No new backend endpoint** — reuses the shipped `GET /api/tags?q=&limit=` verbatim. Owns its own i18n keys, a11y assertions, unit tests, and pl-PL visual coverage per the NFR ownership matrix (`epics.md:4417-4420`).
- **Sources of truth:** `epics.md` §E50 Story 50.3 (`:4511-4517`); `prd.md` FR26-SEARCH-2; NFR matrix (`epics.md:4413-4423`); UX artifact `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` — `DESIGN.md` (component specs `:264-298`), `EXPERIENCE.md` (interaction table `:223-226`, cold/empty/error states `:244-255`, three-channel rule `:304-317`, journey walkthrough `:464-500`); shipped code at `main` @ `8f2852a`; in-repo precedent `50-2-url-state-category-scope.md` (`done`) for structure/verification style and `tag-groups-i18n.test.ts` for the i18n key-set-diff pattern.

---

## 1. Story statement

**As** a catalog user typing into the search box,
**I want** the box to offer both "search for this text" and "add this as a structured tag filter" as two visually and semantically distinct options,
**so that** I can narrow by a canonical tag without guessing its exact spelling or accidentally turning free text into a filter.

**FR mapping.** **FR26-SEARCH-2** — inline suggestions on the **existing** `GET /api/tags?q=` read; distinct query-vs-`+tag` semantics; ≤6–8 items; dedupe by canonical `tag_id`; group labels resolved from the already-loaded tag-group map. **NFR26-A11Y-1 / NFR26-I18N-1 / NFR26-VISUAL-1** — this story is a named owner: it ships its own `en.json`/`pl.json` keys with a key-set diff, its own component-level a11y assertions, and its own targeted unit + pl-PL visual coverage.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `8f2852a`

| Claim | Verified at | Result |
|---|---|---|
| `GET /api/tags?q=&limit=` exists, matches `slug`/`name_en`/`name_pl` case-insensitively, orders by `slug`, `limit` defaults 50/max 200, and returns `group_id`+`group_position` on every item | `apps/api/app/modules/sot/router.py:71-75`; `apps/api/app/modules/sot/service.py:84-113` (`list_tags`) | ✅ confirmed. **No new/duplicate endpoint is needed or permitted.** |
| A FE hook for this endpoint already exists | `apps/web/src/modules/catalog/hooks/useTags.ts` | ✅ `useTags(q)` — `queryKey ["sot","tags",q]`, `staleTime` 5 min, no `with_counts`. **Reuse this hook verbatim**; do not add a second one. |
| `TagListItem`/`TagRead` carry `group_id: string \| null` and `group_position: number`, but **no** embedded group label | `apps/web/src/lib/api-types.ts:43-63` | ✅ confirmed (Decision AW / D-SHAPE-1, unchanged since 42.2). Group label must come from `useTagGroups()`. |
| `useTagGroups()` exists and `CatalogList` already loads it | `apps/web/src/modules/catalog/hooks/useTagGroups.ts`; `apps/web/src/modules/catalog/routes/CatalogList.tsx:32` | ✅ `TagGroupsResponse { groups: TagGroupRead[]; groupless: TagReadWithCount[] }`, `staleTime` 5 min. `CatalogList` calls `const tagGroups = useTagGroups()` at line 32 — **already mounted on the suggestion surface's parent**, so step-2 of the epic's resolution order applies: resolve `group_id → group label` from this already-loaded map, **no new request on the suggestion path**. |
| The existing search input and the existing `+tag` picker live in `FilterRibbon.tsx` | `apps/web/src/modules/catalog/components/FilterRibbon.tsx:67-73` (plain `<Input value={state.q} onChange=.../>`), `:99-113` (`+tag` `Button` toggling `TagPicker`), `TagPicker` function `:273-350` | ✅ confirmed. The plain `q` input is the mount point for the new combobox. **The `+tag` button/`TagPicker` dialog is left untouched and coexisting** — retiring it as the *primary* tag path is explicitly Story 52.1's job (`epics.md:4553`), not this story's. |
| Active-locale-label-with-fallback is an established FE pattern | `FacetSidebar.tsx:80-81`, `TagGroupsSection.tsx:39-40` | ✅ `preferPl && item.name_pl ? item.name_pl : item.name_en` (empty-string `name_pl` treated as absent). Reuse this exact pattern for both tag labels and group labels — do not invent a new one. |
| `FilterRibbonState.q` and `onChange` are the only wiring the new component needs for the plain-query channel; `tag_ids` append is the only wiring needed for the tag channel | `FilterRibbon.tsx:37-44` (`FilterRibbonState`), the `TagPicker onAdd` call site `:274-279` (`onChange({ ...state, tag_ids: [...state.tag_ids, tid] })`) | ✅ mirror this exact append semantics (no dedupe-guard needed beyond "don't re-suggest an already-selected tag", see D-3). |
| `activeFilterCount` (the `Filters (n)` badge) counts only `status`/`source`/non-default `sort` | `FilterRibbon.tsx:52-58` | ✅ confirmed unaffected — selecting a suggested tag changes `tag_ids`, which was never counted, so this story needs **no change here**. |
| No debounce utility exists in the codebase; the shipped `+tag` `TagPicker` already fires `useTags(q)` on every keystroke with no debounce | `grep -rl debounce apps/web/src` (zero hits, excluding tests); `TagPicker` `:284` | ✅ confirmed — see D-5. |
| No existing ARIA-combobox pattern exists anywhere in this codebase to copy | `grep -rln 'role="combobox"' apps/web/src --include=*.test.*` (zero hits) — note: shadcn `Select` triggers also render `role="combobox"` for their own unrelated purpose, so this story's combobox is a **genuinely new pattern**, not an extension of `Select`. | ✅ this story must implement the WAI-ARIA APG combobox listbox pattern from scratch: `role="combobox"` + `aria-expanded` + `aria-controls` + `aria-activedescendant` on the input, `role="listbox"` on the panel, `role="option"` on each row. |
| i18n key-set-diff test pattern already exists to copy | `apps/web/src/modules/admin/tag-groups-i18n.test.ts` | ✅ filter both locale files by story-owned key prefixes, assert equal sorted key sets and non-empty values. Follow this exact shape for the new `catalog.suggestions.*` keys. |
| `en.json`/`pl.json` are flat files (dotted strings as literal keys, `keySeparator` effectively unused for these paths) | both files, existing `catalog.filters.*`/`catalog.tags.*` keys | ✅ add new flat keys under a `catalog.suggestions.*` prefix, consistent with existing `catalog.tags.*`/`catalog.filters.*` naming. |
| A `toBeVisible()`-before-screenshot precedent exists for this suite | `apps/web/tests/visual/admin-tag-groups.spec.ts` (Epic 45 retro action item, `:12-14`) | ✅ every new visual test must assert the populated suggestion panel is rendered (specific rows, not just "panel exists") before `toHaveScreenshot`. |

---

## 3. Key decisions

**D-1 — Where the combobox lives.** Replace the plain `<Input value={state.q} onChange={...}/>` at `FilterRibbon.tsx:67-73` with a new component, e.g. `apps/web/src/modules/catalog/components/SearchSuggest.tsx`, that owns the input, the ARIA-combobox wiring, and the suggestion panel. It receives `state.q`, `onQueryChange(q)`, `state.tag_ids`, `tagGroups` (thread `useTagGroups()` down the same way `CatalogList` already loads it — **do not** call `useTagGroups()` a second time inside the new component if it can be passed down; if wiring it as a prop is impractical without touching `CatalogList`'s call signature more than needed, calling `useTagGroups()` again inside the new component is acceptable — TanStack Query dedupes identical `queryKey`s, so it is not a second network request), and `onSelectTag(tagId)` mirroring the existing `TagPicker onAdd` semantics. The existing `+tag` `Button`/`TagPicker` dialog at `:99-350` stays **exactly as shipped** — this story does not remove, hide, or alter it. **Code-review correction (2026-07-28):** shipped `SearchSuggestProps` does not include `tagsById` — nothing in D-3/D-4 needs a `tag_id → TagRead` lookup since `useTags(q)` rows already carry `name_en`/`name_pl` directly, so it was correctly never wired as a prop. This line originally listed `tagsById` in error; struck here rather than left as a stale claim.

**D-2 — Enter never creates a tag.** The input's `onKeyDown` only intercepts `Enter` when `aria-activedescendant` currently points at a `+tag` option (i.e., the user explicitly arrowed onto it) — in that case `Enter` selects that tag (same as click) and swallows the event. In every other case (no explicit arrow-selection, or `activedescendant` points at the row-1 plain-query option), `Enter` is a no-op beyond closing the panel: `state.q` is already the committed value (it updates on every keystroke via the existing controlled-input `onChange`), so there is nothing further to "commit". This is the mechanism that makes "Enter never converts text into a tag" true by construction, not by a special-cased check.

**D-3 — Suggestion list composition and cap.** Row 1 is always the plain-query row (rendered whenever the panel is open, i.e., `state.q.trim().length >= 1`) — magnifier glyph + typed text, `role="option"`, distinct accessible name (see D-6). Rows 2..N are tag rows sourced from `useTags(state.q)`, **filtered to exclude any `tag_id` already in `state.tag_ids`** (mirrors `TagPicker`'s existing `!selected.includes(tag.id)` filter — an already-selected tag is not a useful suggestion and re-adding it would be a silent no-op duplicate in `tag_ids`). Cap the **combined** list (plain-query row + tag rows) at 8: slice tag rows to the first 7. If the filtered tag list has more than 7 entries, render a trailing non-interactive overflow note (not a `role="option"`, not a focus stop, `aria-hidden` from the listbox per `EXPERIENCE.md:317`). **Overflow note text — resolved, not carried over verbatim from the UX doc:** the UX doc's copy ("points at Filters as the exhaustive surface") assumes the `Filters (n)` drawer from Story 52.1, which has **not shipped yet** — that surface does not exist on `main`. Point the overflow note at the surface that *does* exist today: the shipped `+tag` picker (`catalog.actions.addTag`, `FilterRibbon.tsx:99-113`). Phrase it generically enough that it does not need editing when 52.1 lands (e.g. en: `"More matches — use Add tag to browse all"`, pl: `"Więcej wyników — użyj „Dodaj tag”, aby przejrzeć wszystkie"`). No dedupe-by-`tag_id` logic is needed beyond this filter: `list_tags` (`service.py:100`) selects `Tag` rows directly, so each tag already appears **at most once** in the API response regardless of whether the match came from `name_en`, `name_pl`, or `slug` — "dedupe by ID" is satisfied by the shipped endpoint shape, not by new FE code. Do not write a `Map`/`Set`-based dedupe pass; it would be dead code.

**D-4 — Label + group suffix + matched-alias resolution.** For each tag row: `activeLabel = preferPl && tag.name_pl ? tag.name_pl : tag.name_en` (the established pattern, D-2 of §2). Matched-alias: if `state.q` (lowercased) is a substring of the *other*-locale name and is **not** a substring of `activeLabel` (lowercased), render that other-locale name as a small muted alias beneath/after the pill; otherwise render no alias. Group suffix: look up `tag.group_id` in the `tagGroups` map (build `groupsById = new Map(tagGroups.data?.groups.map(g => [g.id, g]))` once per render of the list, not per-row); if found, suffix = ` · ${activeLabel-style resolution of the group's own name_en/name_pl}`; if `tag.group_id` is `null`, or `tagGroups.data` is not yet loaded (`isLoading`/`isError`/`undefined`), **omit the suffix entirely** — never render a placeholder, never block the row on the tag-groups fetch (per `epics.md:4515` step 3 and `EXPERIENCE.md:225`).

**D-5 — No debounce added.** The shipped `+tag` `TagPicker` already calls `useTags(q)` on every keystroke with no debounce (§2), and this is an accepted, shipped pattern against the same endpoint. Adding a debounce utility that does not exist anywhere else in the codebase is out of scope for this story; the UX doc's "debounced" language is satisfied well enough by TanStack Query's request de-duplication/cache and the endpoint's cheap indexed-adjacent `LIKE` query. If perceived latency becomes a real problem, that is a follow-up, not this story's blocker.

**D-6 — Three-channel distinction (load-bearing, NFR26-A11Y-1).** Plain-query row vs `+tag` row must differ by: (1) **glyph** — magnifier icon vs plus icon; (2) **shape** — plain text vs a `bg-accent` pill, `rounded-full` per `DESIGN.md:256`. **Code-review correction (2026-07-28):** this decision originally also said "reuse the exact pill classes from the shipped tag-chip at `FilterRibbon.tsx:84-89`", which contradicted the `rounded-full` instruction in the same sentence — the shipped tag-chip actually uses `rounded` (not `rounded-full`; confirmed at `FilterRibbon.tsx:84`). The implementation correctly followed `DESIGN.md:256`'s `rounded-full`, not the tag-chip's `rounded`; the "exact classes" clause is struck as the wrong half of the original instruction. (3) **accessible name** — plain-query row: `t("catalog.suggestions.queryOption", { query })` → en `"Search: {{query}}"` / pl `"Szukaj: {{query}}"`; tag row: `t("catalog.suggestions.tagOption", { name, group })` when a group suffix exists, else `t("catalog.suggestions.tagOptionNoGroup", { name })` → en `"Add filter: {{name}}, group {{group}}"` / pl `"Dodaj filtr: {{name}}, grupa {{group}}"` (this exact Polish string is the one named verbatim in `EXPERIENCE.md:207`, so it is not invented — it is a contract). Never rely on colour or position alone (`DESIGN.md:298`).

**D-7 — Panel open/empty/error states.** Panel is closed when `state.q.trim().length === 0`. Opens once length ≥ 1. **Never** shows a "no matches" panel — if `useTags(q)` returns zero tag rows, the panel still opens with the plain-query row alone. On `useTags` error, same: plain-query row only, no error text (`EXPERIENCE.md:255`). No loading spinner inside the panel (`EXPERIENCE.md:244`) — the plain-query row is shown immediately and tag rows simply appear once the query resolves (or don't, if it fails).

**D-8 — Panel sizing.** `overflow: visible`, no `max-h`, no internal scrollbar (`DESIGN.md:275`, `EXPERIENCE.md:287`) — this is enforced structurally by the 8-row cap in D-3, not by CSS clipping. Do not add `overflow-y-auto`/`max-h-*` to the panel container (unlike the *existing* `TagPicker` dialog, which does use `max-h-48 overflow-y-auto` at `FilterRibbon.tsx:331` — that is a **different, untouched** surface with its own, already-shipped scroll behavior; do not "fix" it as part of this story).

---

## 4. Acceptance Criteria

1. Typing ≥1 character into the catalog search input opens a suggestion panel anchored to the input; typing an empty/whitespace-only value keeps it closed.
2. The panel's first row is always a plain-query option offering to search the typed text as-is; selecting it (click or `Enter` with no tag row explicitly arrow-highlighted) sets/keeps `state.q` at the typed text and closes the panel — it never mutates `tag_ids`.
3. Pressing `Enter` at any point, with no `+tag` row explicitly arrow-highlighted, **never** adds a tag to `tag_ids` and never clears `state.q`.
4. When `useTags(state.q)` returns matching tags (excluding any tag already in `state.tag_ids`), each renders as a visually distinct pill row (magnifier-vs-plus glyph, plain-text-vs-pill shape, distinct accessible name per D-6) below the plain-query row.
5. Selecting a `+tag` row (click, or arrowing onto it then `Enter`) appends its `tag_id` to `state.tag_ids`, clears `state.q`, and closes the panel; it never mutates any other `FilterRibbonState` field.
6. The combined panel (plain-query row + tag rows) never exceeds 8 rows; when more tags matched than fit, a trailing non-interactive overflow note appears (not a focus stop, not a `role="option"`) instead of a 9th tag row.
7. The panel never grows an internal scrollbar — its height is fully content-driven up to the 8-row cap.
8. Each tag row's group suffix, when present, is resolved from the already-loaded `useTagGroups()` map by `group_id` with **no additional network request** on the suggestion path; a groupless tag or an unloaded tag-groups map renders the row **without** a suffix, never a placeholder.
9. A tag matched via the non-active-locale name renders the active-locale label as primary with the matched other-locale name as a subtle muted alias; a tag matched via the active-locale name (or via `slug`) renders no alias.
10. `useTags` returning zero matches, or erroring, still opens the panel with the plain-query row alone — never a "no results" panel, never error text inside the panel.
11. `Escape` closes the panel and preserves the typed text in the input; no tag is added.
12. Losing focus (e.g. `Tab`) closes the panel, preserves the typed text, and adds no tag.
13. The existing `+tag` button/`TagPicker` dialog (`FilterRibbon.tsx:99-350`) is unchanged in behavior and continues to coexist with the new combobox.
14. The `Filters (n)` badge (`activeFilterCount`) is unaffected by any suggestion-panel interaction (already true by construction — `tag_ids` was never counted — proven by an integration test that selects a tag via the new panel and asserts the badge count is unchanged).
15. New `catalog.suggestions.*` en/pl keys exist with a passing key-set-diff test (same shape as `tag-groups-i18n.test.ts`) and are all non-empty in both locales.
16. Component-level a11y assertions pass: input is `role="combobox"` with `aria-expanded`/`aria-controls`/`aria-activedescendant`; panel is `role="listbox"`; each row is `role="option"`; plain-query and `+tag` rows have distinguishable accessible names (not just distinguishable appearance); focus order keeps the input focused throughout (no focus is stolen by the panel — arrow-key highlighting moves `aria-activedescendant`, not DOM focus); interactive rows meet ≥24×24px targets.
17. Targeted pl-PL visual baseline(s) added for the populated suggestion panel (plain-query row + ≥2 tag rows, at least one with a group suffix and at least one with a matched alias), each preceded by an explicit `toBeVisible()` assertion on the specific rendered rows before `toHaveScreenshot` (per the Epic 45 retro action item).

---

## 5. Tasks / Subtasks

- [x] **Task 1 — i18n keys (AC 15)**
  - [x] Add `catalog.suggestions.queryOption`, `catalog.suggestions.tagOption`, `catalog.suggestions.tagOptionNoGroup`, `catalog.suggestions.overflowNote` (and any row-label sub-keys needed for the alias hint) to `apps/web/src/locales/en.json` and `pl.json`, with genuine Polish text (not machine-transliterated English) — the `tagOption` pl string must match `EXPERIENCE.md:207` verbatim (`"Dodaj filtr: {{name}}, grupa {{group}}"`).
  - [x] Add `apps/web/src/modules/catalog/suggestions-i18n.test.ts` mirroring `tag-groups-i18n.test.ts`: filter both locale files by prefix `catalog.suggestions.`, assert equal sorted key sets, assert every value non-empty.
- [x] **Task 2 — `SearchSuggest` component (AC 1-13, 16)**
  - [x] Create `apps/web/src/modules/catalog/components/SearchSuggest.tsx` implementing the ARIA-combobox pattern per D-1/D-2/D-6/D-7/D-8: input (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`), panel (`role="listbox"`), plain-query row + tag rows (`role="option"`) with the pill/glyph/accessible-name distinctions.
  - [x] Implement row composition/cap/overflow-note per D-3, label/suffix/alias resolution per D-4, keyboard handling (`ArrowUp`/`ArrowDown` moves `aria-activedescendant` only; `Enter` per D-2; `Escape`/blur per AC 11-12).
  - [x] Wire `apps/web/src/modules/catalog/components/FilterRibbon.tsx:67-73` to mount `SearchSuggest` in place of the plain `Input`, passing `state.q`, `state.tag_ids`, `tagsById`, `tagGroups` (or an internal `useTagGroups()` call — see D-1), and `onSelectTag` calling the same `onChange({ ...state, tag_ids: [...] })` shape the existing `TagPicker onAdd` uses, plus a `q`-clearing path on tag selection.
  - [x] Do not touch the `+tag` `Button`/`TagPicker` block (`:99-350`) or `activeFilterCount` (`:52-58`).
- [x] **Task 3 — Unit tests**
  - [x] `SearchSuggest.test.tsx`: panel open/closed on empty/non-empty query; plain-query-row-always-first; cap-at-8 + overflow note when >7 tag matches; group-suffix present/absent (loaded map, groupless tag, unloaded map); matched-alias present/absent; `Enter` without arrow-selection never mutates `tag_ids`; `Enter` after `ArrowDown` onto a tag row selects it and clears `q`; `Escape` preserves text and closes; zero-match and error states render plain-query-row-only.
  - [x] `FilterRibbon.test.tsx` (extend existing, or new integration case): selecting a suggested tag updates `state.tag_ids` and leaves `activeFilterCount`'s inputs (`status`/`source`/`sort`) untouched (AC 14); the existing `+tag` picker still functions unchanged (AC 13). **Dev repair note:** the first version of this integration test used a non-stateful `onChange` stub and a plain (non-round-tripping) render, so the suggestion panel never actually populated and the assertion on `tag_ids` failed on the first run; repaired by rendering through a small stateful test harness that feeds `onChange` back into `state` (matching how `CatalogList` actually drives `FilterRibbon`) before the tag-click assertion. No production code was at fault — see Completion Notes.
- [x] **Task 4 — a11y assertions (AC 16)**
  - [x] Assert combobox/listbox/option roles and the three-channel accessible-name distinction directly in `SearchSuggest.test.tsx` (Testing Library `getByRole`/`aria-*` queries) — do not defer this to the visual suite, which cannot assert ARIA attributes.
- [x] **Task 5 — pl-PL visual baseline (AC 17)**
  - [x] Add `apps/web/tests/visual/catalog-search-suggestions.spec.ts` (mirroring the `stubSotList`/`waitForReady`/`toBeVisible()`-before-screenshot shape of `filter-ribbon-selects-open.spec.ts` and `admin-tag-groups.spec.ts`): stub `GET /api/tags?q=...` with a fixture returning ≥2 tags (one with a `group_id` present in a stubbed `GET /api/tag-groups` response, one matched via the non-active locale to exercise the alias hint), type into the search input, assert the specific rows are `toBeVisible()`, then `toHaveScreenshot`.
  - [x] Run across all four projects (desktop-light/dark, mobile-light/dark) per repo convention; skip only if a specific breakpoint genuinely can't render the surface (state the reason inline, mirroring `skipOnMobile` precedent) — the UX doc's breakpoint table (`EXPERIENCE.md:328-331`) says the panel is pinned under the input on all breakpoints, so no skip is needed and none was applied; all 4 projects render and pass with newly baselined screenshots (visually reviewed — see Completion Notes).
- [ ] **Task 6 — Gates**
  - [ ] `npm run typecheck`, `npm run lint`, full `npm run test`, `npm run test:visual`, `npm run build` all green; `git status --porcelain apps/web/src/routeTree.gen.ts` empty (no route touched, so this should be a trivial no-op check, not a real risk). **PARTIAL, honestly recorded:** `typecheck` (rc=0), `lint` (rc=0), full `npm run test` (850/850 passed, 141 files) all ran green in this dev pass; the *targeted* `catalog-search-suggestions.spec.ts` visual spec ran green across all 4 projects (4 passed) with new baselines accepted. The **full** `npm run test:visual` suite (all specs, not just this story's) and `npm run build` were **not run** in this dev pass — the session hit `max_turns` immediately after the targeted visual run, and this resume pass is bookkeeping-only per controller instruction (no new broad gates). `git status --porcelain apps/web/src/routeTree.gen.ts` is confirmed empty (verified both mid-session and in this resume pass). **Owed before merge:** full `npm run test:visual` and `npm run build`, both controller/reviewer-owned from here.

---

## 6. Dev Notes

### Architecture compliance
- Frontend-only; no backend, migration, or contract change. Reuses `GET /api/tags?q=&limit=` verbatim (§2). No new TanStack Query hook beyond possibly a second `useTagGroups()` call site (query-key-deduped, not a new request).
- Stack: React + TypeScript + TanStack Query + TanStack Router + react-i18next + Tailwind + shadcn-derived primitives, matching every other `modules/catalog/components/*` file.

### File structure
- New: `apps/web/src/modules/catalog/components/SearchSuggest.tsx`, `SearchSuggest.test.tsx`, `apps/web/src/modules/catalog/suggestions-i18n.test.ts`, `apps/web/tests/visual/catalog-search-suggestions.spec.ts` (+ its `__snapshots__/` baselines).
- Modified: `apps/web/src/modules/catalog/components/FilterRibbon.tsx` (mount point only, per Task 2), `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json`.
- **Untouched, verified by fence:** `apps/web/src/routes/catalog/index.tsx` (43.3/50.2 validator), `apps/web/src/modules/catalog/hooks/useModels.ts`, `useTags.ts`, `useTagGroups.ts` (all reused as-is, no signature change), `FilterRibbon.tsx:99-350` (`+tag` picker), `activeFilterCount` (`:52-58`), `apps/web/src/routeTree.gen.ts` (no route change).

### Testing standards
- Vitest + Testing Library for unit/a11y assertions (repo convention, see `FilterRibbon` and admin `*-i18n.test.ts` precedents).
- Playwright for pl-PL visual coverage; global config forces `pl-PL` locale (see memory: web-visual-tests-render-pl-pl) — any text assertion in the new visual spec must use the Polish strings, mirroring `filter-ribbon-selects-open.spec.ts`'s comment convention that documents *which* locale string is expected and why.
- Every screenshot assertion must be preceded by a `toBeVisible()` on the specific populated state (Epic 45 retro action item) — do not screenshot on a bare `waitForReady()`.

### Project Structure Notes
- No conflicts with `apps/web/src` conventions. `SearchSuggest.tsx` sits alongside `FilterRibbon.tsx`/`TagGroupsSection.tsx` in `modules/catalog/components/`, consistent with existing component granularity (one file per self-contained UI concern).

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story 50.3 (`:4511-4517`)]
- [Source: _bmad-output/planning-artifacts/epics.md#NFR ownership matrix (`:4417-4420`)]
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/DESIGN.md#suggestion panel (`:264-298`)]
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md#interaction table (`:223-226`), states (`:244-255`), three-channel rule (`:304-317`), journey (`:464-500`)]
- [Source: apps/api/app/modules/sot/router.py:71-75, service.py:84-113]
- [Source: apps/web/src/modules/catalog/hooks/useTags.ts, useTagGroups.ts]
- [Source: apps/web/src/lib/api-types.ts:43-63]
- [Source: apps/web/src/modules/catalog/components/FilterRibbon.tsx:37-113, 273-350]
- [Source: apps/web/src/modules/catalog/components/FacetSidebar.tsx:80-81, TagGroupsSection.tsx:39-40]
- [Source: apps/web/src/modules/admin/tag-groups-i18n.test.ts]
- [Source: apps/web/tests/visual/filter-ribbon-selects-open.spec.ts, admin-tag-groups.spec.ts]

---

## 7. Previous Story Intelligence (from 50-2, `done`)

- Pattern to keep: exhaustive `VERIFY-AT-CREATE-STORY` table tracing every claim to a live file+line, not a carried-over sketch assumption (this artifact's §2 follows that shape).
- Pattern to keep: a "Key decisions" section (`D-1`... ) that names the decision, the reasoning, and the rejected alternative where relevant — 50.2 caught 3 real defects in its own draft this way during validation; this story front-loads that same rigor into create rather than deferring it to a separate validate pass.
- Fence discipline: 50.2 proved that "list the exact files this story does NOT touch, with the verifying grep/read" prevents scope creep from a plausible-sounding sketch. Applied here against `FilterRibbon.tsx`'s `+tag` block and `activeFilterCount`.
- The UX doc sometimes describes end-state composition (e.g. the `Filters (n)` drawer) that depends on a *later* story (52.1) that hasn't shipped — 50.2 didn't hit this, but 50.3 does (D-3's overflow-note text). Resolved explicitly rather than silently copying forward-looking UX copy that would reference a non-existent surface.

## 8. Git Intelligence

- Last 5 commits (`8f2852a`, `0093187`, `c436f61`, `9697d8c`, `910e976`) are all 50.x/49.5 docs-closeout or single-scope feature commits — no drive-by refactors, no bundling of unrelated changes. This story should land as one commit touching only the files listed in §6 File structure.
- `0093187` (`feat(web): add catalog category URL state`) is the most recent FE feature commit and shows the established shape: new/extended `.tsx` + matching `.test.ts`/`.test.tsx`, no unrelated file touched, no `routeTree.gen.ts` diff when no route changes (this story changes no route either).

---

## 9. Project Context Reference

No `project-context.md` file matched the persistent-facts glob at activation; none was available to load.

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5, via native `bmad-dev-story`, under Laura/controller standing Initiative 26 authorization (G26-DEVGO for this exact validated scope). Two process turns: the primary implementation turn ended on `error_max_turns` (RUN_EXIT rc=1) immediately after the targeted visual run reported `4 passed (5.9s)` and before Dev Agent Record/status bookkeeping was written; this resume turn completed only the BMAD bookkeeping described below — no application code was touched in the resume turn.

### Debug Log References

- `.hermes/run-logs/e50-3-dev-story-20260728_203450.log` — primary implementation run (RED/GREEN TDD cycles, component build, wiring, targeted visual baseline acceptance; ends at `error_max_turns`).
- `.hermes/run-logs/e50-3-dev-story-bookkeeping-20260728_204907.log` — this resume turn (story/sprint-status bookkeeping only).
- Prior create/validate logs (not part of this dev pass): `e50-3-create-validate-20260728_195906.log`, `e50-3-create-validate-20260728_195917.log`, `e50-3-create-validate-retry-20260728_201103.log`, `e50-3-create-validate-bashwrite-20260728_201810.log`, `e50-3-create-validate-sonnet-20260728_202515.log`.

### Completion Notes List

**RED → GREEN evidence (strict TDD, per task):**

- Task 1 (i18n): `suggestions-i18n.test.ts` written first — confirmed RED (2 of 4 tests failing: empty key set, missing `tagOption` string) against the locale files with no `catalog.suggestions.*` keys present. Added the 4 keys (en/pl) → GREEN, 4/4 passed.
- Task 2/3 (component): `SearchSuggest.test.tsx` (25 cases) written first against a non-existent `./SearchSuggest` module — confirmed RED (suite failed to resolve the import, 0 tests collected). Implemented `SearchSuggest.tsx` → first pass left 12 tests failing (async-timing races where `findAllByRole("option")` resolved before the tag rows — which load asynchronously via `useTags` — had rendered; one incorrect test assumption that `aria-expanded` starts `false` for a non-empty query; a focus assertion with no explicit `.focus()` call). Fixed by waiting for the exact expected option count (`findOptions(count)` helper) and correcting the two test-only assumptions → GREEN, 25/25 passed. No production logic changed to reach green on those 12 — the fixes were test-side only, confirmed by rereading the failures.
- Task 3 (FilterRibbon integration): extended `FilterRibbon.test.tsx` with a new tag-selection case. First run surfaced a real *production* race: `SearchSuggest.selectTagRow` originally called both `onSelectTag(tag.id)` and `onQueryChange("")` as two separate callback invocations; `FilterRibbon`'s wiring already folds the `q`-clear into the same `onChange` call `onSelectTag` makes, so the second, separate `onQueryChange("")` call clobbered the first update with a stale `state.tag_ids: []` closure, and the assertion `expect(last.tag_ids).toEqual(["t1"])` failed (`received: []`). Root-caused to the double-dispatch and fixed by making `onSelectTag` the sole owner of clearing `q` (D-1's "existing `TagPicker onAdd` semantics" contract is a single atomic update, not two independent ones) — removed the redundant `onQueryChange("")` call from `selectTagRow` in `SearchSuggest.tsx`, and updated the two `SearchSuggest.test.tsx` assertions that had (incorrectly) expected `onQueryChange` to fire on tag selection. Re-ran both suites → GREEN (`SearchSuggest.test.tsx` 25/25, `FilterRibbon.test.tsx` 14/14).
- Task 4 (a11y): folded into `SearchSuggest.test.tsx` (combobox/listbox/option roles, `aria-expanded`/`aria-controls`/`aria-activedescendant` wiring, `tabIndex=-1` on every option, activedescendant-moves-without-DOM-focus-theft) — all green as part of the 25/25 above.
- Task 5 (visual): `catalog-search-suggestions.spec.ts` written and run per project. First attempt used RTL-only APIs (`getByPlaceholderText`) that don't exist on Playwright's `Page`, and an ambiguous `getByPlaceholder` substring match against both the `+tag` `TagPicker`'s own placeholder and the new combobox's — both fixed to `page.getByRole("combobox", { name: "Szukaj" })`. Also caught and corrected an inverted fixture: under the pl-PL harness locale, the active label for a tag with both `name_en`/`name_pl` is the **Polish** name, so the query needed to match the *English* name to exercise D-4's matched-alias (not the reverse, which was the first draft). All 4 `toBeVisible()` content assertions (plain-query row, group-suffixed pill, alias text, groupless pill) passed before every screenshot. No baseline existed yet (new spec) — ran once to inspect the 4 "actual" renders (desktop-light/dark, mobile-light/dark) directly, visually confirmed correct three-channel anatomy (magnifier vs plus glyph, plain text vs pill, group suffix, alias, no internal scrollbar) in all four, then accepted them via `--update-snapshots`. Final targeted run: **4 passed (5.9s)**, all 4 projects, no skips.
- Task 6 (gates): see the Task 6 checklist item above for the exact partial/owed breakdown — `typecheck` rc=0, `lint` rc=0 (1 pre-existing benign eslint-react-version warning, not a new finding), full `npm run test` 850/850 passed across 141 files (this story added 2 new test files — `suggestions-i18n.test.ts`, `SearchSuggest.test.tsx` — plus new/extended cases in `FilterRibbon.test.tsx`; the 804-passed/139-file figure recorded against this repo at the 50.1 check-all gate is a stale baseline from an earlier story, not a same-tree comparison point, so no delta arithmetic against it is claimed here), targeted visual spec 4/4 passed with newly accepted baselines. **Not run in this dev pass:** the full `npm run test:visual` suite (all specs, not just this story's) and `npm run build` — the implementation turn hit `max_turns` right after the targeted visual acceptance, and per controller instruction this resume turn is bookkeeping-only and does not run new broad gates. `git status --porcelain apps/web/src/routeTree.gen.ts` is empty (verified both mid-session and in this resume pass) — no route was touched, matching the story's fence.

**Scope fences held:** the `+tag` `Button`/`TagPicker` block (`FilterRibbon.tsx:99-350` in the pre-story file) and `activeFilterCount` (`:52-58`) were not touched beyond the single mount-point swap at the old `:67-73` plain `<Input>`. No backend file, no route file, no `routeTree.gen.ts` change.

### File List

- `apps/web/src/locales/en.json` (modified) — added 4 `catalog.suggestions.*` keys.
- `apps/web/src/locales/pl.json` (modified) — added 4 `catalog.suggestions.*` keys (genuine Polish, `tagOption` verbatim per `EXPERIENCE.md:207`).
- `apps/web/src/modules/catalog/suggestions-i18n.test.ts` (new) — key-set-diff parity test.
- `apps/web/src/modules/catalog/components/SearchSuggest.tsx` (new) — the ARIA-combobox suggestion component.
- `apps/web/src/modules/catalog/components/SearchSuggest.test.tsx` (new) — 25 unit/a11y tests.
- `apps/web/src/modules/catalog/components/FilterRibbon.tsx` (modified) — mounts `SearchSuggest` in place of the plain search `<Input>`; `+tag`/`TagPicker`/`activeFilterCount` unchanged.
- `apps/web/src/modules/catalog/components/FilterRibbon.test.tsx` (modified) — added the tag-selection integration case (AC 13/14).
- `apps/web/tests/visual/catalog-search-suggestions.spec.ts` (new) — pl-PL visual baseline spec, 4 projects.
- `apps/web/tests/visual/__snapshots__/catalog-search-suggestions.spec.ts/` (new) — 4 accepted baseline PNGs (desktop-light/dark, mobile-light/dark).
- `_bmad-output/implementation-artifacts/50-3-inline-structured-suggestions.md` (this file) — Tasks/Subtasks, Dev Agent Record, Status.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `50-3-inline-structured-suggestions` status line (`in-progress` → `review`).

---

## Code Review Record

**Verdict: APPROVE** (post-patch). Native `bmad-code-review`, 2026-07-28. Diff reviewed: dirty working tree vs `baseline_commit` `8f2852a1e50f66bf71e207d256ab2400cc6b19fa` (HEAD, unmoved). Three adversarial layers ran in parallel with no prior conversation context: Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`), Acceptance Auditor (all 17 ACs + D-1..D-8, this artifact as spec). **Provenance:** native BMAD agent review only — NOT an Ezop signature, NOT human review of any kind. No Codex, no Gemini. Independent Aider review (`laura-aider-review-diff`) recorded separately below (Aider Review Record) — this native CR pass did not run it.

### Acceptance Auditor result

All 17 ACs and D-1 through D-8 independently verified compliant by reading the shipped code (not the spec's own claims). Two documentation-only nits found and corrected directly in this artifact (§3, no code impact): D-1 listed a `tagsById` prop `SearchSuggest` never received or needed; D-6 gave two contradictory pill-class instructions where the code correctly followed `DESIGN.md:256`'s `rounded-full`.

### Triage

0 decision-needed · 3 patch (all applied) · 0 pre-existing-defer · ~4 low-severity informational findings recorded and dismissed · remainder dismissed as noise.

**Patches applied (all in `SearchSuggest.tsx` unless noted):**

1. **[Medium — correctness]** `useTags(q)` was called with the raw, untrimmed query while `isOpen` was gated on the trimmed query. The backend's `list_tags` filter (`apps/api/app/modules/sot/service.py:100-110`) does `f"%{q.lower()}%"` with no server-side trim, so a leading/trailing space (paste, autocorrect, IME) opened the panel (trimmed length > 0) but silently returned zero tag matches for text that plainly matches once trimmed. Fixed: `useTags(trimmed)` instead of `useTags(q)`.
2. **[Medium — content bug]** `catalog.suggestions.overflowNote` (en + pl) directed users to a button labeled "Add tag" / "Dodaj tag", but the real `+tag` button renders the literal string `"+ tag"` in both locales (`en.json`/`pl.json:314`, confirmed by grep — the button never had an "Add tag" label). Fixed: corrected both locale strings to reference the real `"+ tag"` label.
3. **[Medium — accessibility]** The D-4 matched-alias hint (cross-locale tag disambiguation — the entire reason it exists) was invisible to screen readers: the tag row's explicit `aria-label` excludes all descendant text, including the alias `<span>`, from the accessible-name computation, so sighted users saw the alias but AT users got no equivalent. Fixed: added `aria-describedby` on the option row pointing at the alias span's own `id`, added only when an alias exists — this does **not** touch the `tagOption`/`tagOptionNoGroup` locale strings, which `suggestions-i18n.test.ts` asserts verbatim against the `EXPERIENCE.md:207` contract.

**Recorded, dismissed as noise or by-design (no code change):** panel opening immediately whenever `state.q` arrives non-empty at mount (e.g. a bookmarked `/catalog?q=...` URL) — confirmed intentional per D-7 ("Opens once length ≥ 1", no focus gating) and already covered by `SearchSuggest.test.tsx:116-120`; `activeIndex` not reconciled if the row set shifts under an already-arrow-highlighted index — narrow, no crash (optional chaining), low severity; a theoretical double-click race on `onSelectTag` — mirrors the pre-existing, equally-unguarded `TagPicker.onAdd` pattern, not a new regression; overflow note being `aria-hidden` with no AT-equivalent truncation signal — explicit per D-3/`EXPERIENCE.md:317`; group-suffix contrast pairing nuance (`bg-accent` vs `popover` per `DESIGN.md`) — unverifiable without a full contrast audit, speculative; debounce-free per-keystroke fetch duplicated in a second call site — explicitly accepted scope per D-5; 36px row height vs a "commonly cited" 44px target — AC 16's actual bar (≥24×24) is met.

### Gates re-run after patches (targeted, not full `check-all.sh`)

- `npx vitest run SearchSuggest.test.tsx suggestions-i18n.test.ts FilterRibbon.test.tsx` → **43/43 passed** (25 + 4 + 14), no test file edited.
- `npx tsc --noEmit -p .` → **rc=0**.
- `npx eslint src/modules/catalog/components/SearchSuggest.tsx --max-warnings=0` → **rc=0**, 0 warnings.
- `npx playwright test --config=tests/visual/playwright.config.ts tests/visual/catalog-search-suggestions.spec.ts` → **4/4 passed**, all 4 projects, against the **existing** (unregenerated) baselines — `aria-describedby` is non-visual, confirmed by the unchanged pass.

### Files changed by this review pass

`apps/web/src/modules/catalog/components/SearchSuggest.tsx`, `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json`, this artifact (D-1/D-6 corrections + this section), `_bmad-output/implementation-artifacts/sprint-status.yaml`.

**No commit, stage, push, merge, or deploy action was taken.** Status held at `review` (not `done`): full `npm run test:visual` (repo-wide), `npm run build`, `infra/scripts/check-all.sh`, and the commit/ff-merge/push/deploy chain remain controller-owned and unrun, per explicit task scope for this review pass. The independent Aider pass is recorded below (Aider Review Record) as a separate, later pass.

---

## Aider Review Record

**Verdict: APPROVE.** Routine external reviewer per the Laura Agent Rulebook: `laura-aider-review-diff` / Aider v0.86.2 via OpenRouter DeepSeek, 2026-07-28. Diff reviewed: dirty working tree vs `baseline_commit` `8f2852a1e50f66bf71e207d256ab2400cc6b19fa` (HEAD, unmoved).

**Attempts:**

1. `.hermes/run-logs/e50-3-aider-review-20260728_210708.log` — failed, `rc=64`: the diff piped to stdin was empty, so Aider had nothing to review.
2. `.hermes/run-logs/e50-3-aider-review-20260728_210716.log` — failed, `rc=124`: a binary-inclusive diff (including the 4 new PNG baselines under `apps/web/tests/visual/__snapshots__/catalog-search-suggestions.spec.ts/`) exceeded the model's context window.
3. `.hermes/run-logs/e50-3-aider-review-textdiff-20260728_211027.log` — succeeded. Used a **text-only** diff that excludes PNG bytes, while naming the 4 PNG baseline paths in the review context (so Aider knew new baselines existed without needing their binary content).

**Result (successful run):** Critical: none. Important: only controller-owned remaining gates (full `npm run test:visual`, `npm run build` / `check-all.sh` before merge) — no code-level Important finding. Missing tests: none. **Literal verdict: APPROVE.**

**Caveat, stated honestly:** Aider's own prose redundantly restates "Aider review owed" inside its Important section — an artifact of the review prompt/context listing controller-owned gates as still-outstanding items, not a claim that the Aider pass itself didn't run. The controller treats the literal, successful `APPROVE` verdict from attempt 3 as the independent-review obligation discharged; that stale wording should not be read as implying Aider is still unrun.

**Provenance:** independent external reviewer only — NOT an Ezop signature, NOT human review of any kind. No Codex, no Gemini. No file was edited by Aider (review-only invocation); no commit/stage/push/merge/deploy action taken by this pass.

**Still owed, all controller-owned:** full `npm run test:visual` (repo-wide), `npm run build` (or `infra/scripts/check-all.sh`), commit, ff-merge, push, deploy, post-deploy smoke.

---

## Full Closeout Gate Record

**First full `infra/scripts/check-all.sh` run:** `.hermes/run-logs/check-all-e50-3-20260728_211240.log`, `CHECK_ALL_RC=1` — 15/16 stages passed; the sole failure was the `apps/web` visual regression stage. That stage itself reported 536 passed / 32 skipped and only 4 failures, all in `tests/visual/empty-states.spec.ts`, test `catalog empty state offers a clear-filters action when filters active`, across all four projects (desktop-light, desktop-dark, mobile-light, mobile-dark).

**Baseline triage (before regenerating anything):** classified as `stale-baseline` / intentional feature delta, **not** a real regression. Reasoning: for `/catalog?q=no-match`, the `q` search param is non-empty on mount, and per this story's D-7 the suggestion panel opens whenever `state.q.trim().length >= 1` — so the panel is now expected to be open on this route by construction. The actual screenshots showed the correct empty-state content plus the correct clear-filters action, with the new suggestion panel also rendered — no unexpected layout defect. This matches the native code-review pass's own by-design classification of "panel opens on mount for a pre-populated `q`" (recorded above, Code Review Record, "Recorded, dismissed as noise or by-design").

**Targeted baseline update:** `npx playwright test --config=tests/visual/playwright.config.ts tests/visual/empty-states.spec.ts --grep "offers a clear-filters" --update-snapshots`, run from `apps/web`, log `.hermes/run-logs/e50-3-empty-states-update-20260728_212421.log` (the controller's logging redirect was issued from `apps/web`, so the log's effective on-disk path is `../../.hermes/run-logs/...` relative to that cwd — same file, path noted for traceability). Result: 4 passed. Only the 4 pre-existing `catalog-empty-with-action-*.png` baselines were regenerated — no other spec's baselines were touched.

**Full `infra/scripts/check-all.sh` rerun:** `.hermes/run-logs/check-all-e50-3-rerun-20260728_212516.log`, `CHECK_ALL_RC=0 2026-07-28T21:36:05+02:00` — **16/16 stages, all green**, literal trailer `all green.`. Key in-log figures: `apps/web` vitest 141 files / 850 tests passed; `apps/web` visual regression 540 passed / 32 skipped (the 4 regenerated baselines now pass alongside the story's own 4 new `catalog-search-suggestions` baselines); check-all's own summary line confirms `all green.`.

**Remaining before `done`:** commit, ff-only merge to `main`, push, deploy, post-deploy smoke, then the final status flip. All controller-owned; none taken by this bookkeeping pass. This pass edited only this artifact and `sprint-status.yaml`; it ran no gate/test/build/script itself (it recorded gates the controller already ran) and took no commit/stage/push/merge/deploy/migration/seed/live-DB/network action. Status remains `review`.
