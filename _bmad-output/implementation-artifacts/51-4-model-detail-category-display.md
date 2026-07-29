---
baseline_commit: ac249bfc2dbcb16a98e055185cc79a2ae2ea63aa
---

# Story 51.4 — Model-detail category display (FR26-CAT-2, FR26-BROWSE-2, NFR26-A11Y-1, NFR26-I18N-1, NFR26-VISUAL-1, NFR26-DARKMODE-1)

Status: review

- **Epic:** E51 — Browse IA: categories as navigation (Initiative 26 — Catalog Discovery). **Last story in the epic.**
- **Author:** Claude Opus 5, native `bmad-create-story` (Create → Validate). **Authorization posture:** delegated by Laura/controller under the standing Initiative 26 authorization. **NOT** an Ezop signature, **NOT** human review of any kind; no Codex, no Gemini, no Aider. No app code written, no gate/test/build run, no branch/commit/merge/deploy. This pass edited exactly two files: this artifact and `sprint-status.yaml`.
- **Created:** 2026-07-29 at `main` @ `ac249bf` (clean tree, aligned with `origin/main`), directly after Story 51.3's full closeout. `epic-51` already `in-progress`; no epic flip owed.
- **Duplicate check:** `_bmad-output/implementation-artifacts/` carries `51-1-*`, `51-2-*`, `51-3-*` only; no pre-existing `51-4-*` artifact.
- **Scope class:** frontend-only. One new component + its test, one mount line in `ModelHero.tsx`, two i18n keys, one visual-stub fixture field, one new visual spec. **No** backend change, **no** new route, **no** new hook, **no** new dependency, **no** new `--color-*` token, **no** mutation UI.
- **Why this story exists:** added 2026-07-26 by `bmad-check-implementation-readiness` (finding C-1) — Story 49.3 ships `ModelDetail.categories` and Story 50.1 types it, but **no story consumed it**. This closes an API field with no reader and the coverage hole against FR26-CAT-2's "zero categories is valid and publicly visible" verifiable.
- **Sources of truth:** `epics.md:4539-4541` (Story 51.4 sketch), `:4400` (FR26-CAT-2 matrix row), `:4406` (FR26-BROWSE-2), `:4417-4420` (per-story NFR ownership), `:4525` (E51 merge-gate obligations); `prd.md` § Initiative 26 FR26-CAT-2 / FR26-BROWSE-2; `architecture.md` § Initiative 26 Decision AY (embeddable summary shape); UX artifact `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/` — `EXPERIENCE.md:57` (surface map row), `:230` (Model-detail category list component pattern), `:251` (zero-category state), `:374` (transition table: detail link **replaces** scope), `:398-404` (component ownership: 51.4, sibling to `TagGroupsSection.tsx`), `:422-423` (non-goals: no categories on `ModelSummary`, none on the anonymous share surface), `:198`/`:231` (entity labels are content, not i18n keys); `DESIGN.md:140-144` (`model-detail-category-link` token block), `:203-205` (location vs constraint colour roles), `:282` (component spec), `:293-294` (do/don't); in-repo predecessors `spec-45-2-catalogdetail-grouped-tags.md` (the empty-group posture this mirrors), `50-1-fe-types-and-hooks.md`, `51-1`/`51-2`/`51-3` (all `done`); shipped code at `main` @ `ac249bf`.

---

## 1. Story statement

**As** a catalog user looking at one model,
**I want** to see which broad browse categories that model belongs to, told apart at a glance from its facet tags, and to jump straight into any of them,
**so that** a model detail page is an entry point back into browsing rather than a dead end — and so a model with no categories still reads as perfectly normal.

**FR mapping.**

- **FR26-CAT-2** — "model detail renders its categories; zero categories valid and publicly visible". Verifiable here: `/catalog/$modelId` renders `detail.categories`; a zero-category model shows **no** empty-state noise to a regular member.
- **FR26-BROWSE-2** — `/categories/{slug}` is reachable from the detail surface; the scope lives in the path.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `ac249bf`

The epic sketch's marker is *"`CatalogDetail`/`TagGroupsSection` structure as shipped"*. Traced fresh; **two findings below (V-8 and V-9) contradict the UX artifact and the story sketch as written**, and are resolved in § 3.

| # | Fact | Evidence |
|---|---|---|
| V-1 | `CatalogDetail` does **not** render tags/categories itself — it delegates to `ModelHero` | `routes/CatalogDetail.tsx:23-44` — `CatalogDetailRender({detail})` renders `<ModelHero detail={detail} />` (`:26`) then gallery/description/links/metadata/`SecondaryTabs`. `CatalogDetailBody` (`:53-73`) fetches via `useModel(id)`; `CatalogDetail` (`:75-78`) is the `/catalog/$id` param wrapper. **This story does not touch `CatalogDetail.tsx`.** |
| V-2 | `ModelHero` renders `TagGroupsSection` immediately after the status/rating/source badge row | `ModelHero.tsx:92-122` is the badge row (`StatusPopover`/`StatusBadge`, rating, `SourceBadge`, admin pencil); `:123` is `<TagGroupsSection detail={detail} isAdmin={isAdmin} onAddTags={() => setTagsOpen(true)} />`. `isAdmin`/`isAuthenticated` come from `useAuth()` (`:27`). |
| V-3 | `TagGroupsSection` is the sibling this story sits beside, and its empty-group posture is the model to mirror | `TagGroupsSection.tsx` — fails closed while `useTagGroups().data === undefined` (`:33`); `labelOf` treats empty-string `name_pl` as absent (`:39-40`); sections sorted by `position` + trailing `__groupless__` (`:44-61`); **visibility rule `s.tags.length > 0 \|\| isAdmin` (`:65`)**; empty group for admin = `—` + `Button` "+ tag" with a group-scoped `a11y.addTagToGroup` name (`:87-99`); real chips are `Link to="/catalog" search={{tag_ids:[tag.id]}}` styled `rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground` (`:77-85`); section wrapper is `mt-2 space-y-1.5`, per-row `flex flex-wrap items-center gap-x-2 gap-y-1`, label `text-xs font-semibold uppercase tracking-wide text-muted-foreground` (`:69-74`). |
| V-4 | `ModelDetail.categories` exists, is **required**, and is `BrowseCategorySummary[]` | `lib/api-types.ts:233-247` — typed required with an explicit comment that the wire always emits the key (`[]`, never null/absent). `BrowseCategorySummary` (`:102-109`) = `{id, slug, name_en, name_pl, position, parent_id}` — **no `model_count`, no `description_*`** (Decision AY). `BrowseCategoryRead` (`:116-120`) adds those and is the *list* shape — not what the detail carries. |
| V-5 | The backend populates it unconditionally, already ordered | `apps/api/app/modules/sot/service.py:527-534` — one extra `SELECT` joined through `ModelBrowseCategory`, `ORDER BY BrowseCategory.position, BrowseCategory.slug`; written into `ModelDetail` at `:572`. `schemas.py:220` — `categories: list[BrowseCategorySummary] = Field(default_factory=list)`. **No client-side re-sort is needed or permitted.** |
| V-6 | `/categories/$slug` is live and its search layer is entirely optional | `routes/categories/$slug.tsx:7-21` — `createFileRoute("/categories/$slug")`, `validateSearch` = `validateCatalogSearch(raw)` with `category` stripped (`Omit<CatalogSearch,"category">`). Every field of `CatalogSearch` (`routes/catalog/index.tsx:42-55`) is optional, so a `Link` with `params` and **no** `search` is valid. Route already exists ⇒ **no `routeTree.gen.ts` regeneration expected** — flag it if one appears. |
| V-7 | The "location" visual vocabulary is already shipped twice and must be reused, not re-derived | `ScopeChip.tsx:25-26` — `rounded-md bg-primary/10 ... text-foreground ring-1 ring-inset ring-primary`; `BrowseCategoryList.tsx:41-42` `ROW_ACTIVE` — `bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary`. Matches `DESIGN.md:140-144` `model-detail-category-link` byte-for-byte. Tag chips next door use `bg-muted`/`accent` — never `primary` (`DESIGN.md:204`, `:294`). |
| **V-8** | **⚠️ CONTRADICTION — there is no admin category-assignment surface to link to.** `EXPERIENCE.md:251` says admins see the advisory **"+ link to assign"**; that link has no destination today. | `apps/web/src/modules/admin/` contains no category page (only tag-groups, users, invites, profiles, queues); `grep -rn "admin/categories\|adminCategories" apps/web/src` → **zero hits**; no `/admin/categories` route exists in `apps/web/src/routes/admin/`. The backend replace-set endpoint **does** exist (`apps/api/app/modules/sot/browse_category_admin_router.py:18,101` — `PUT /api/admin/models/{model_id}/categories`, Story 49.5), but `epics.md:4555-4557` assigns the **UI** to Story 52.2, which is `backlog`. Resolved by **D-5**. |
| **V-9** | **⚠️ GAP — the shared visual fixture does not carry `categories`.** | `tests/visual/api-stubs.ts:319-441` — `stubSotDetail`'s `**/api/models/{id}` body has `tags`, `files`, `prints`, `notes`, `external_links` and **no `categories` key**, so every visual detail render would currently exercise the zero-category branch by accident (and `detail.categories` would be `undefined` at runtime despite the required type — an unguarded `.map` would throw). The `**/api/categories*` stub at `:218` belongs to `stubSotList` only and is **irrelevant here** (the detail surface reads the embedded field, it fetches nothing). Resolved by **D-6**. |
| V-10 | `MemberShareView` reuses this render tree and its probe returns the full canonical detail | `routes/share/MemberShareView.tsx:154` → `<CatalogDetailRender detail={modelData} />`; `routes/share/useShareModelProbe.ts` fetches the **canonical** `/api/models/{id}` under queryKey `["sot","models",id]`. ⇒ the new section **will** render for authenticated members at `/share/$token`. That is correct and consistent with 45.2 (`TagGroupsSection` does the same). The **anonymous** `ShareModelView` is a different component on the `/api/share/*` DTO and is untouched — `EXPERIENCE.md:423`'s non-goal and the `NFR25-LEAKFENCE-1` fence both hold with a zero-line diff. |
| V-11 | i18n is a **flat**-key JSON pair; the `catalog.browse.*` prefix already has a hard guard | `locales/en.json` / `pl.json` — 919 keys each, keys are literal dotted strings. `src/modules/catalog/browse-i18n.test.ts` asserts `storyKeys(enKeys)).toHaveLength(11)`, en/pl key-set equality, non-empty in both, **every pl value ≠ en value**, and the `Przeglądaj` vocabulary. Adding a `catalog.browse.*` key without bumping the literal **fails the suite by design**. |
| V-12 | `ModelHero.test.tsx` mocks its section children | `ModelHero.test.tsx:20-31` mocks `TagGroupsSection` so the file stays router-free, and `:114-120` asserts prop wiring. The same pattern is owed for the new section (see T5). |
| V-13 | Seven visual specs consume `stubSotDetail` | `catalog-detail.spec.ts`, `share-member-enriched.spec.ts`, `share-member-enriched-dismissed.spec.ts`, `admin-dropdowns-tooltip-open.spec.ts`, `destructive-dialogs-edit-sheets-open.spec.ts`, `image-viewer-containment.spec.ts` (it stubs only file **content** inline, so it inherits `stubSotDetail`'s model body), `remaining-sheets-open.spec.ts`. `catalog-detail-admin.spec.ts` is `test.describe.skip`-ped entirely (deferred to Slice 3E) and consumes nothing. Baseline-churn expectation is set in D-7/AC-14. |
| **V-14** | **⚠️ GAP (widened) — `stubSotDetail` is not the only model-detail fixture missing `categories`. A full sweep found two more sites, both of which would throw on an unguarded read.** | Sweep = every file carrying its own `external_links` model body. **(a)** `tests/visual/catalog-filestab-estimate.spec.ts:47-85` — its own `stubModelDetail` fulfils `**/api/models/{MODEL_ID}` with a body that has `tags`, `files`, `prints`, `notes`, `external_links` and **no `categories`**; it does **not** import `stubSotDetail`. **(b)** `src/routes/share/MemberShareView.test.tsx:187-212` — an **untyped** inline `fetch` stub whose own comment says the payload "only needs to satisfy enough of the `ModelDetail` contract … to not throw"; it has no `categories`. **(c)** Every *typed* vitest fixture is already safe — `categories: []` is present in `ModelHero.test.tsx:85`, `TagGroupsSection.test.tsx:81`, and eleven sibling `*.test.tsx` files, because `ModelDetail.categories` is a required field and those fixtures are typed. Resolved by **D-6**. |

---

## 3. Design decisions

- **D-1 (new sibling component, not an edit to `TagGroupsSection`).** Create `apps/web/src/modules/catalog/components/ModelCategoriesSection.tsx`. `TagGroupsSection.tsx` gets a **zero-line diff** — the two vocabularies stay independent in code exactly as they are in the product (`EXPERIENCE.md:32-44`, `:404` "sibling, visually distinct"). Props mirror the sibling's shape minus the sheet callback: `{ detail: ModelDetail; isAdmin: boolean }`. `detail.categories` is read directly — **no hook, no fetch** (`useCategories`/`useCategoryBySlug` must not be mounted here; the embedded summary is the whole contract, and the detail shape deliberately carries no `model_count` to render).
- **D-2 (mount point: above the tags).** In `ModelHero.tsx`, insert `<ModelCategoriesSection detail={detail} isAdmin={isAdmin} />` between the badge row (`:92-122`) and `<TagGroupsSection …>` (`:123`). Categories answer *where does this live* and read first; tags answer *what properties* and refine. One added line plus one import; no other `ModelHero` behaviour changes.
- **D-3 (visual distinction is load-bearing, and the recipe already exists).** Each category renders as a `Link` carrying the **location** vocabulary copied verbatim from `ScopeChip.tsx:26` / `BrowseCategoryList.tsx:41`: `rounded-md bg-primary/10 text-foreground ring-1 ring-inset ring-primary`. Deliberately **`rounded-md`, never `rounded-full`**, and deliberately **never `bg-muted`/`accent`** — shape *and* colour both separate it from the tag chips sitting directly below (`DESIGN.md:258`, `:293-294`). No new token, no inline hex. Sizing: `min-h-6` + `px-2 py-0.5 text-xs` keeps the ≥24×24 CSS-px floor (WCAG 2.2 SC 2.5.8) while staying visually lighter than the full-width `ScopeChip`.
- **D-4 (navigation: fresh, path-scoped, no search merge).** `<Link to="/categories/$slug" params={{ slug: c.slug }}>` with **no** `search` prop — the detail page owns no catalog search state to preserve, so this is a fresh navigation, precisely as `TagGroupsSection`'s chips are (`spec-45-2…md:28` "a fresh navigation, not a merge with any prior search state"). The `EXPERIENCE.md:374` transition row ("Select a category … category **replaced**, everything else preserved") is satisfied vacuously: there is nothing to preserve. V-6 confirms this typechecks; if TanStack's types demand the prop, pass `search={{}}` — never `useSearch({strict:false})` (the silent-widening trap 51.2 D-2 rejected).
- **D-5 (zero-category posture — the honest resolution of V-8).** Mirrors 45.2's rule shape (`TagGroupsSection.tsx:65`), not its markup:
  - **`categories.length > 0`** → label + links, for every viewer (member and admin alike). Categories are public (`FR26-CAT-2`).
  - **`categories.length === 0` and `!isAdmin`** → the component returns `null`. **Nothing rendered** — no heading, no dash, no placeholder (`EXPERIENCE.md:230`, `:251`). A zero-category model is *normal*, and saying otherwise to a member is the exact copy sin `EXPERIENCE.md:208` names.
  - **`categories.length === 0` and `isAdmin`** → one muted advisory line, `t("catalog.browse.noCategoriesAdmin")` = *"Bez kategorii — do uzupełnienia"* (pl copy fixed verbatim by `EXPERIENCE.md:208`/`:251`) rendered as **static text, not a control and not a link**.
    **Why no link (V-8):** the assignment surface does not exist — `/admin/categories` is Story 52.2 and is `backlog`. A link to a 404, or a bespoke assignment sheet built here, would both be worse than an honest advisory: the first lies, the second duplicates 52.2's replace-set editor (with its LWW re-fetch-on-open and 1–3 advisory obligations, `epics.md:4557`) in the wrong story. **The 45.2 analogy holds for the *rule*, not the *affordance*: 45.2 could open a sheet only because `EditTagsSheet` already shipped; no `EditCategoriesSheet` exists.** Recorded as an explicit handoff in § 9.
- **D-6 (every model-detail fixture must carry the field — resolution of V-9 **and** V-14).** Three sites, all three owed, because each one renders `ModelHero` and would otherwise reach the new component with `detail.categories === undefined`:
  - **(a) `tests/visual/api-stubs.ts` `stubSotDetail`** — add a `categories` key on the model body plus an options field so a spec can select the state: `stubSotDetail(page, { categories?: BrowseCategorySummary[] })`, **defaulting to a two-category fixture** (e.g. `storage-organization` / `holders-mounts`, `position` 0 and 2, one with `name_pl` present and one with `name_pl: null` so the `labelOf` fallback is exercised in the pl-PL harness). Default non-empty is deliberate: the shared fixture should exercise the real shipped surface, and it makes the zero-category spec an explicit `categories: []` opt-in rather than an accident. Same enrichment posture 45.2 used for `/api/tag-groups`.
  - **(b) `tests/visual/catalog-filestab-estimate.spec.ts` `stubModelDetail`** (`:47-85`) — its own inline body, not an import of `stubSotDetail`. Add `categories: []`. Zero, not populated: that spec is about the FilesTab estimate chip and its screenshots are scoped to `page.getByRole("tabpanel").first()`, so **no baseline of that spec is expected to move** — the fix is purely to keep the hero from throwing. Flag it if a baseline there does move.
  - **(c) `src/routes/share/MemberShareView.test.tsx`** (`:187-212`) — the untyped inline `fetch` stub. Add `categories: []`. Its own comment already states the payload exists only to satisfy enough of the `ModelDetail` contract not to throw; `categories` is now part of that minimum. No assertion in that file changes.
  These are **test-fixture repairs**, not behaviour changes, and they are the whole reason no runtime `?? []` guard is permitted (§ 10).
- **D-7 (baseline churn is expected, bounded, and triaged — not blanket-regenerated).** Seven specs consume `stubSotDetail` (V-13); the ones whose screenshots include the hero region will move by exactly one new row. Every diff image is inspected and classified `stale-baseline` / `deterministic-fail` / `flake-candidate` **before** any `--update-snapshots` (standing Init-10 Murat rule). Expected classification: `stale-baseline` (INTENTIONAL FEATURE DELTA) confined to the new category row. Any movement in a `browse-rail-*`, `browse-sheet-*`, `facet-sidebar-*` or `catalog-list-*` baseline is **out of family** and is an Ask-First signal (§ 5).
- **D-8 (labels are content, never i18n).** Category labels come from `name_pl`/`name_en` with the shipped `labelOf` guard — `preferPl && item.name_pl ? item.name_pl : item.name_en`, empty string treated as absent (`DESIGN.md:231`, `TagGroupsSection.tsx:39-40`, `BrowseCategoryList.tsx:71-72`). Only the section heading and the admin advisory are i18n keys.
- **D-9 (render order + `parent_id`).** Render `detail.categories` in **wire order** — the backend already sorts by `(position, slug)` (V-5) and owns that contract; a client-side re-sort silently forks it (the same rule `BrowseCategoryList.tsx:107-110` records). `parent_id` is **ignored**: MVP browse is flat (`FR26-CAT-4`, `EXPERIENCE.md:419`) — no nesting, no indentation, no grouping by parent.
- **D-10 (no count, no fetch, no reactivity).** The detail summary carries no `model_count` by design (Decision AY / V-4). Do **not** fetch `useCategories()` to enrich it with counts: it would add a request per detail view for a number this surface never shows, and would silently make a *location* label look like the rail's *size* readout.
- **D-11 (i18n placement inherits the existing guard).** Both new keys go under the **`catalog.browse.`** prefix so `browse-i18n.test.ts` (V-11) automatically enforces en/pl parity, non-emptiness and genuine-Polish for them: `catalog.browse.modelCategoriesLabel` (en `Categories` / pl `Kategorie`) and `catalog.browse.noCategoriesAdmin` (en `No categories — needs curation` / pl `Bez kategorii — do uzupełnienia`). The guard's literal count bumps **11 → 13** with an updated comment naming this story.

---

## 4. Acceptance Criteria

1. A new component `apps/web/src/modules/catalog/components/ModelCategoriesSection.tsx` exists, takes `{ detail: ModelDetail; isAdmin: boolean }`, and reads `detail.categories` with **no** query hook and no network call of its own.
2. `ModelHero.tsx` mounts it exactly once, positioned **between** the status/rating/source badge row and `<TagGroupsSection>`; no other behaviour in `ModelHero` changes.
3. `TagGroupsSection.tsx` has a **zero-line diff**.
4. Given a model with ≥1 category, `/catalog/$modelId` renders a section heading from `t("catalog.browse.modelCategoriesLabel")` followed by one entry per category, in the order the API returned them (no client-side sort), for **both** member and admin viewers.
5. Each category entry is an anchor (`Link`) resolving to `/categories/{slug}` for that category's `slug`, with no catalog search params attached.
6. Each category entry's visible text is the locale-resolved label — `name_pl` when the UI language is Polish **and** `name_pl` is a non-empty string, otherwise `name_en`. No label comes from an i18n key.
7. Category entries carry the location vocabulary (`bg-primary/10` + `ring-1 ring-inset ring-primary` + `rounded-md`) and are visually distinguishable from the adjacent tag chips (`bg-muted`, `rounded`). No inline hex, no new `--color-*` token, correct in light **and** dark (NFR26-DARKMODE-1).
8. Given a model with **zero** categories and a non-admin viewer, the component renders **nothing at all** — no heading, no dash, no placeholder, no empty-state copy.
9. Given a model with **zero** categories and an admin viewer, exactly one muted advisory line renders using `t("catalog.browse.noCategoriesAdmin")`; it is **static text**, not a link and not a button, and it opens nothing.
10. `parent_id` is not read; no category is nested, indented, or grouped by parent. No `model_count` is rendered anywhere in this section.
11. Two new keys — `catalog.browse.modelCategoriesLabel` and `catalog.browse.noCategoriesAdmin` — exist in **both** `en.json` and `pl.json` with genuine (non-identical) Polish; no existing key's value changes; en/pl key-set parity stays 1:1; `browse-i18n.test.ts`'s literal count is deliberately bumped 11 → 13 with a comment naming this story.
12. Component-level a11y assertions ship with the story (NFR26-A11Y-1): each category link's **accessible name equals its visible label**; each link is keyboard-focusable and reachable in reading order (categories before tags); each link's target size is ≥24×24 CSS px; the admin advisory is **not** exposed as an interactive element.
13. Targeted unit coverage exists (`ModelCategoriesSection.test.tsx`, router-mounted since entries are `Link`s) covering every row of the § 6 matrix: populated/member, populated/admin, zero/member, zero/admin, pl-label fallback (`name_pl: null` **and** `name_pl: ""`), wire-order preservation, and the resolved `href`. `ModelHero.test.tsx` mocks the new section (matching its existing `TagGroupsSection` treatment) and asserts prop wiring.
14. Targeted pl-PL Playwright coverage exists for the new surface, light **and** dark, with an explicit `toBeVisible()` on the category row **before** every `toHaveScreenshot` (standing epic:45/epic:46 TEST-AUTHORING rule): at minimum populated-admin, populated-member, and zero-category-admin (advisory). Pre-existing baselines that move are individually diff-inspected and classified per D-7 before any regeneration; the commit's `baseline-reviewed:` lines name the agent that actually inspected them and **never** `Ezop` or any human.
15. Every model-detail fixture carries `categories` (D-6): `stubSotDetail` emits it on the model body (default: two categories, one with `name_pl`, one with `name_pl: null`) with an option to override it — including to `[]`; `catalog-filestab-estimate.spec.ts`'s own `stubModelDetail` and `MemberShareView.test.tsx`'s inline `fetch` stub each emit `categories: []`. No other assertion in those two files changes, and no runtime `?? []` fallback is added to production code to compensate.
16. The anonymous share surface is untouched: `routes/share/$token.tsx`'s anonymous `ShareModelView` path, `lib/share-api.ts`, and every `apps/api/app/modules/share/` file have a zero-line diff. Categories appearing for **authenticated members** at `/share/$token` (via `CatalogDetailRender`, V-10) is expected and correct.
17. No backend file changes. No `routeTree.gen.ts` diff (V-6) — if one appears, stop and report it.
18. `npm run typecheck`, `npm run lint --max-warnings=0`, `npm run test`, `npm run build`, and the targeted `npm run test:visual` all pass; `git diff --check` is clean.

---

## 5. Ask First / Never

**Never** (hard boundaries — not even as a "better" idea):

- Build any category **assignment/edit** UI, sheet, dialog, or mutation call here. The replace-set editor with its re-fetch-on-open, last-audited-writer note, "Zastąp kategorie" copy and advisory 1–3 warning is **Story 52.2** (`epics.md:4555-4557`). This story is read-only.
- Link the admin advisory to `/admin/categories` or any other non-existent route (V-8).
- Modify `TagGroupsSection.tsx`, `EditTagsSheet.tsx`, `FacetSidebar.tsx`, `BrowseRail.tsx`, `BrowseSheet.tsx`, `BrowseCategoryList.tsx`, `ScopeChip.tsx`, or `CatalogList.tsx`.
- Add `categories` to `ModelSummary` or render categories on catalog list cards (`EXPERIENCE.md:422`).
- Add categories to the **anonymous** share view or touch the `/api/share/*` DTO — the `NFR25-LEAKFENCE-1` fence stays exactly as it is (`EXPERIENCE.md:423`).
- Fetch `useCategories()` / `useCategoryBySlug()` from this surface, or render a `model_count` (D-10).
- Re-sort, nest, group-by-parent, or truncate/cap the category list (D-9).
- Use `accent`, `bg-muted`, `rounded-full`, or any new colour token for a category entry (`DESIGN.md:294`).
- Blanket-run `--update-snapshots` without per-baseline diff inspection and classification (D-7).
- Sign a `baseline-reviewed:` line with a human's name. It names the agent that actually looked at the PNGs.

**Ask First** if, during implementation:

- A **desktop** `browse-rail-*`, `browse-sheet-*`, `facet-sidebar-*`, or `catalog-list-*` baseline moves. Those families are outside this story's render tree; movement means something leaked (D-7).
- `detail.categories` turns out to be `undefined` at runtime anywhere despite the required type (i.e. some caller reaches `CatalogDetailRender` with a non-canonical `ModelDetail`) — that is a contract break worth surfacing, not worth papering over with an inline `?? []` and silence. (Report it; a defensive fallback may then be the agreed fix.)
- Satisfying AC-12's accessible-name rule appears to need an `aria-label` that does **not** contain the visible label — that would risk WCAG 2.2 SC 2.5.3 (Label in Name), and the plain visible-text name is the intended default.
- A visual baseline cannot be made deterministic without touching shared harness code in `tests/visual/_test.ts` or `helpers.ts`.

---

## 6. I/O & edge-case matrix

| Scenario | Input / state | Expected render | Notes |
|---|---|---|---|
| Populated, member | `categories.length ≥ 1`, `isAdmin=false` | Heading + one location-styled `Link` per category, wire order | Categories are public (FR26-CAT-2) |
| Populated, admin | `categories.length ≥ 1`, `isAdmin=true` | Identical to the member render | No extra admin affordance when non-empty |
| Zero, member | `categories = []`, `isAdmin=false` | `null` — nothing at all | AC-8; the FR26-CAT-2 "renders normally" verifiable |
| Zero, admin | `categories = []`, `isAdmin=true` | One muted advisory line, static text | AC-9; D-5 |
| pl locale, `name_pl` non-empty | `i18n.language = "pl"` | `name_pl` | `labelOf` |
| pl locale, `name_pl` `null` **or** `""` | `i18n.language = "pl"` | `name_en` | Empty string treated as absent (D-8) |
| en locale | `i18n.language = "en"` | `name_en` | — |
| Entry activated | click / `Enter` | Navigates to `/categories/{slug}`, no search params | D-4 |
| Unknown/stale slug | slug no longer resolves | `/categories/{slug}` renders an empty page with `total = 0`, **not** a 404 | Shipped 51.2 behaviour; nothing owed here |
| Member share view | authenticated member at `/share/$token` | Section renders (same tree via `CatalogDetailRender`) | V-10; expected, not a leak |
| Anonymous share view | `/share/$token`, not signed in | Unchanged, no categories | AC-16 |

---

## 7. Tasks / Subtasks

- [x] **T1 — Build `ModelCategoriesSection` (AC: 1, 4, 5, 6, 7, 8, 9, 10)**
  - [x] New `apps/web/src/modules/catalog/components/ModelCategoriesSection.tsx`; props `{ detail, isAdmin }`; read `detail.categories` only.
  - [x] Early return `null` when `categories.length === 0 && !isAdmin`; admin advisory branch when `categories.length === 0 && isAdmin`.
  - [x] Copy the `labelOf` guard from `TagGroupsSection.tsx:39-40` (module-local, unexported — `react-refresh/only-export-components` runs at `--max-warnings=0`).
  - [x] Location-vocabulary class recipe per D-3, taken verbatim from `ScopeChip.tsx:26` / `BrowseCategoryList.tsx:41`.
- [x] **T2 — Mount in `ModelHero` (AC: 2, 3)**
  - [x] Import + one JSX line between `ModelHero.tsx:122` and `:123`. Confirm `TagGroupsSection.tsx` stays at a zero-line diff (`git diff --stat`).
- [x] **T3 — i18n (AC: 11)**
  - [x] Add both keys to `en.json` and `pl.json`; pl copy exactly `Kategorie` and `Bez kategorii — do uzupełnienia`.
  - [x] Bump `browse-i18n.test.ts`'s `toHaveLength(11)` → `13` and extend the comment to name Story 51.4.
  - [x] Re-verify 1:1 en/pl key-set parity (921/921 expected).
- [x] **T4 — Fixtures (AC: 15)**
  - [x] Extend `stubSotDetail` per D-6(a): `categories` on the model body + an options override, default two categories (one `name_pl` present, one `null`).
  - [x] Add `categories: []` to `tests/visual/catalog-filestab-estimate.spec.ts`'s own `stubModelDetail` body per D-6(b).
  - [x] Add `categories: []` to `src/routes/share/MemberShareView.test.tsx`'s inline `fetch` stub per D-6(c).
  - [x] Re-run the V-14 sweep before closing this task (`grep -rl external_links apps/web/src apps/web/tests` → every hit that is a model-detail body carries `categories`) to confirm no fourth site was introduced meanwhile.
- [x] **T5 — Unit + a11y tests (AC: 12, 13)**
  - [x] New `ModelCategoriesSection.test.tsx`, router-mounted (mirror `TagGroupsSection.test.tsx`'s harness); cover every § 6 row plus resolved `href`, wire-order, accessible name = visible label, focusability, and that the admin advisory is not an interactive element.
  - [x] `import { cleanup } from "@testing-library/react"; afterEach(cleanup);` — mandatory, `vitest globals: false` in this repo.
  - [x] `ModelHero.test.tsx`: mock the new section (same shape as the existing `TagGroupsSection` mock at `:29-31`) and assert prop wiring (`detail`, `isAdmin`).
- [x] **T6 — Visual coverage + baseline triage (AC: 14)**
  - [x] New `tests/visual/catalog-detail-categories.spec.ts`: populated-admin, populated-member (`/api/auth/me` → `role: "member"`, per `catalog-detail.spec.ts:26-38`), zero-category-admin (`categories: []`). Explicit `toBeVisible()` before every screenshot.
  - [x] Run the seven `stubSotDetail` consumers (V-13) **plus `catalog-filestab-estimate.spec.ts`** (its fixture changed under D-6(b), even though no baseline of it should move); inspect and classify every moved baseline before regenerating; record the per-family counts in the Dev Agent Record.
- [x] **T7 — Merge-gate obligations (E51 per-story ownership, `epics.md:4525`) (AC: 16, 17, 18)**
  - [x] Verify the anonymous share path and all backend files have zero-line diffs (`git diff --stat`).
  - [x] Verify no `routeTree.gen.ts` diff.
  - [x] Run the § 8 gates and read their output.

---

## 8. Tests / Gates (dev-story owns running and reading these)

- `npm run typecheck` (`tsc -b`) rc=0.
- `npm run lint` (`--max-warnings=0`) rc=0.
- `npm run test` — full vitest, including the new and updated files.
- `npm run build` rc=0 (no `routeTree.gen.ts` diff expected — flag if one appears).
- Targeted `npm run test:visual` for `catalog-detail-categories.spec.ts`, the seven `stubSotDetail` consumers (V-13), and `catalog-filestab-estimate.spec.ts` (fixture touched by D-6(b)), all four projects.
- `git diff --check` rc=0.
- **NFR26-DETERMINISM-1:** 3× consecutive identical vitest pass counts. Backend is untouched, so pytest determinism is not this story's obligation — say so plainly rather than claiming a run that did not happen.
- Full `infra/scripts/check-all.sh`, native `bmad-code-review`, independent Aider review, commit/ff-merge/push/deploy/smoke: **controller-owned at closeout**, same as 51.1–51.3.

---

## 9. Handoffs recorded by this story

- **→ Story 52.2 (admin category management screen).** When `/admin/categories` and the replace-set editor ship, wire the admin advisory line from D-5 to it. The advisory is deliberately static text today because the destination does not exist (V-8); making it a link is a 52.2 change, not a 51.4 omission. `EXPERIENCE.md:251`'s "+ link to assign" is satisfied **at 52.2**, and this note is the record that the deferral was deliberate and traced, not missed.
- **→ Story 54.1 (cross-surface i18n parity).** Two `catalog.browse.*` keys added here (13 total under that prefix after this story). The Polish for the advisory is fixed verbatim by `EXPERIENCE.md:208` — a terminology audit should not "improve" it.
- **→ Story 54.2 (cross-surface a11y/visual audit).** The `stubSotDetail` `categories` field added here is the fixture every future detail-surface spec inherits; fold it into the `/api/*` route-mock consolidation pass rather than re-authoring a parallel fixture.

---

## 10. Dev Notes

- **Read `_bmad-output/project-context.md` before writing code.** Load-bearing here: `import type` under `verbatimModuleSyntax`; `noUncheckedIndexedAccess` (no `!` shortcuts); no inline hex; `@/…` path alias; `--max-warnings=0`; keep the file's only export a component (module-local constants stay unexported, as `BrowseCategoryList.tsx:9-16` documents).
- The three shipped `labelOf` implementations (`FacetSidebar`, `TagGroupsSection:39-40`, `BrowseCategoryList:71-72`) are intentionally duplicated module-locals, not a shared util. Follow that convention — do not "DRY" them into `lib/` as a drive-by.
- `detail.categories` is typed **required**; the fixture gaps (V-9 and V-14) are *test-fixture* bugs across three files, not a licence to add a runtime `?? []`. Fix all three fixtures (T4, D-6 a/b/c). If a genuine runtime `undefined` shows up, that is an Ask-First item (§ 5), not a silent guard.
- Reuse `t("catalog.browse.railLabel")`-style vocabulary consistency: this surface's heading is a **noun** ("Kategorie"), not the verb the browse surfaces use ("Przeglądaj") — they answer different questions and 54.1 audits for exactly this kind of consistency.
- Playwright's harness forces `pl-PL`; text matchers in visual specs must be Polish or locale-independent.
- Story branch per AGENTS.md: `feat/E51.4-model-detail-category-display`, cut from clean `main` @ `ac249bf`.

### Project Structure Notes

- New component lands in `apps/web/src/modules/catalog/components/` beside its siblings; its test is colocated (`*.test.tsx`), per the repo's no-mirror-tree rule.
- New visual spec lands in `apps/web/tests/visual/`; new baselines under `apps/web/tests/visual/__snapshots__/catalog-detail-categories.spec.ts/`.
- No `apps/web/src/ui/*.tsx` file is added, so the Visual Coverage Contract pre-commit hook does not apply; the Baseline Acceptance Gate (`baseline-reviewed:` per changed PNG) **does**.
- No variance from the unified structure is introduced by this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 51.4 — Model-detail category display] (`:4539-4541`), [#Requirements Inventory] (`:4400`, `:4406`), [#Epic E51] (`:4519-4525`)
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/EXPERIENCE.md#Information Architecture] (`:57`), [#Component Patterns] (`:230`), [#State Patterns] (`:251`), [#URL and state transitions] (`:374`), [#Component ownership] (`:398-411`), [#Non-goals] (`:422-423`), [#Voice and Tone] (`:198`, `:208`)
- [Source: _bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/DESIGN.md#Components] (`:140-144`, `:282`), [#Colors] (`:203-205`), [#Do/Don't] (`:293-295`), [#Content] (`:231`)
- [Source: _bmad-output/planning-artifacts/architecture.md#Initiative 26 Decision AY]
- [Source: _bmad-output/implementation-artifacts/spec-45-2-catalogdetail-grouped-tags.md#Boundaries & Constraints] — the empty-group posture mirrored by D-5
- [Source: apps/web/src/modules/catalog/routes/CatalogDetail.tsx:23-44], [apps/web/src/modules/catalog/components/ModelHero.tsx:92-123], [apps/web/src/modules/catalog/components/TagGroupsSection.tsx:33-99], [apps/web/src/modules/catalog/components/ScopeChip.tsx:25-26], [apps/web/src/modules/catalog/components/BrowseCategoryList.tsx:41-42,71-72,107-110]
- [Source: apps/web/src/lib/api-types.ts:102-120,233-247], [apps/web/src/routes/categories/$slug.tsx:7-21], [apps/web/src/routes/catalog/index.tsx:42-55]
- [Source: apps/api/app/modules/sot/service.py:527-534,572], [apps/api/app/modules/sot/schemas.py:220], [apps/api/app/modules/sot/browse_category_admin_router.py:18,101]
- [Source: apps/web/tests/visual/api-stubs.ts:319-441], [apps/web/tests/visual/catalog-detail.spec.ts], [apps/web/src/modules/catalog/browse-i18n.test.ts]
- [Source: AGENTS.md#Branching and workflow], [_bmad-output/project-context.md#Frontend gotchas]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5[1m]`), repo-local Claude Code, native `bmad-dev-story`. **Authorization posture:** controller authorization `G26-DEVGO` under the standing Initiative 26 delegation from Laura/Hermes (ITCM). **NOT** an Ezop signature, **NOT** human review of any kind; no Codex, no Gemini, no Aider in this pass. Branch `feat/E51.4-model-detail-category-display` cut from `main` @ `ac249bf`, carrying the create+validate artifact changes. No commit, no merge, no push, no deploy — controller-owned.

### Debug Log References

**Gates run and read (all from `apps/web/`):**

| Gate | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` (`tsc -b`) | **rc=0** |
| Lint | `npm run lint` (`eslint . --max-warnings=0` + stylelint) | **rc=0** |
| Vitest (full) | `npm run test` | **rc=0 — 147 files / 946 tests passed** |
| NFR26-DETERMINISM-1 | `npm run test` ×3 consecutive | **identical on all three runs: 147/147 files, 946/946 tests, rc=0** |
| Build | `npm run build` | **rc=0** (pre-existing >500 kB chunk advisory only) |
| Visual (full suite) | `npm run test:visual` | **rc=0 — 586 passed, 42 skipped, 0 failed** across all 4 projects |
| Whitespace | `git diff --check` | **rc=0** |

Backend is untouched (`apps/api` → 0 changed files), so **pytest was not run and this story claims no pytest determinism** — stated plainly per § 8 rather than implied.

**TDD (RED → GREEN) evidence:**

- `ModelCategoriesSection.test.tsx` authored first → RED: `Failed to resolve import "./ModelCategoriesSection"`, `Test Files 1 failed`, `Tests no tests`. After `ModelCategoriesSection.tsx` → GREEN: 15 passed.
- `ModelHero.test.tsx` mount/position assertion authored first → RED: `expected "spy" to be called 1 times, but got 0 times`. After the `ModelHero.tsx` mount line → GREEN: 9 passed.

**V-14 sweep re-run (T4) — and the fourth site it exposed.** The sweep as specified (`grep -rl external_links …`, file-scoped) returned a **false negative** once D-6(a) landed: `tests/visual/api-stubs.ts` holds *two* model-detail bodies, and adding `categories` to `stubSotDetail` made the whole file match "categories" while `stubViewerModelDetail` (`api-stubs.ts:39-110`) still lacked it. Re-run at **occurrence level** (one check per `external_links:` site, 15 sites) instead of file level. Result: 12 typed vitest fixtures OK, the three D-6 sites fixed, and **`stubViewerModelDetail` found MISSING** — a fourth instance of exactly the V-9/V-14 class.

Symptom that caught it independently: `admin-dropdowns-tooltip-open.spec.ts` → "ViewToolbar Tooltip hover" failed in **all four** projects, because that test is the one `stubViewerModelDetail` consumer that renders `ModelHero`, and `ModelCategoriesSection` reads `categories.length` unguarded. Fixed per D-6's own rule (`categories: []`, matching D-6(b)'s "zero, not populated" posture for a spec that is not about categories); **no runtime `?? []` was added** (§ 10). All four failures cleared and **no viewer3d baseline moved** (`viewer3d-inline-loaded`, `-measure-plane`, `-measure-pp`, `-mobile`, `-modal-closed`, `-modal-open` → 41 passed).

This was **not** escalated as an Ask-First item: § 5's trigger is `detail.categories` being `undefined` *at runtime from a non-canonical caller* — a production contract break. Here the only source was a **test stub**, which V-9/V-14 already classified as a fixture bug and D-6 already prescribed the fix for. Recorded here rather than blocked on; flagged to the controller as a spec-sweep-methodology defect worth carrying to 54.2.

### Completion Notes List

**Baseline triage (D-7 / AC-14).** 37 baselines total: **12 new** + **25 pre-existing moved**. Every moved baseline was diff-inspected and classified **before** any `--update-snapshots`; no blanket regeneration.

| Family | Baselines | Classification | Evidence |
|---|---|---|---|
| `catalog-detail.spec.ts` (3 tests × 4 projects) | 12 | **stale-baseline — INTENTIONAL FEATURE DELTA** | Diff PNGs show the new `KATEGORIE` row inserted in the hero and everything below shifted down by exactly one row (~32 px). No content changed anywhere else. |
| `share-member-enriched.spec.ts` | 4 | **stale-baseline — INTENTIONAL FEATURE DELTA** | Same one-row shift. Expected per **V-10**: the authenticated-member share view reuses `CatalogDetailRender`. Info-bar itself byte-unchanged. |
| `share-member-enriched-dismissed.spec.ts` | 4 | **stale-baseline — INTENTIONAL FEATURE DELTA** | Same one-row shift. |
| `admin-dropdowns-tooltip-open.spec.ts` — `status-popover-open` (desktop-dark, mobile-dark), `rating-popover-open` (desktop-dark, mobile-light, mobile-dark) | 5 | **stale-baseline — INTENTIONAL FEATURE DELTA (second-order)** | 3–13 px, ratio 0.01, **confined to the menu's outer border antialiasing**; the menu's own content is identical. Sub-pixel re-anchoring of a menu whose trigger sits in the hero that grew by one row. **Verified not flake and not environmental drift:** `git stash`-ed the whole `apps/web` change set and re-ran → **8/8 passed on clean `main`**; restored and re-ran → the same 5 failed deterministically. In-family per V-13/D-7 (this spec is one of the seven `stubSotDetail` consumers), so **no Ask-First trigger**. |
| `catalog-detail-categories.spec.ts` (3 tests × 4 projects) | 12 **new** | **new baseline — visually inspected** | Light + dark, desktop + mobile confirmed by eye: `KATEGORIE` heading + two ringed `bg-primary/10` entries, clearly distinct from the `bg-muted` tag chips directly below; categories render **above** tags; `rounded-md` not `rounded-full`; legible in dark mode (NFR26-DARKMODE-1). Zero-category admin shows exactly one muted `Bez kategorii — do uzupełnienia` line — no heading, no dash, no control. |

**`baseline-reviewed:` sign-off for the commit (controller-owned).** Every one of the 37 PNGs was inspected by **Claude Opus 5 (`bmad-dev-story`, repo-local)** on **2026-07-29**. The commit's `baseline-reviewed:` lines must name that agent — **never `Ezop` or any human**, who reviewed none of them.

**Specs that consume a touched fixture and did NOT move (verified, not assumed):** `catalog-filestab-estimate.spec.ts` (D-6(b)'s prediction held — its screenshots are tabpanel-scoped), `destructive-dialogs-edit-sheets-open.spec.ts`, `image-viewer-containment.spec.ts`, `remaining-sheets-open.spec.ts`, and all six `viewer3d-*.spec.ts`.

**Out-of-family proof (§ 5 Ask-First).** The **full** `npm run test:visual` suite was run after regeneration: 586 passed / 42 skipped / 0 failed. **No `browse-rail-*`, `browse-sheet-*`, `facet-sidebar-*`, `category-browse-*` or `catalog-list-*` baseline moved** — `git status` over `__snapshots__/` lists exactly the 25 modified PNGs above plus the one new directory. Nothing leaked.

**Zero-line-diff obligations, all verified by `git status --porcelain` (AC-3, AC-16, AC-17):**

- `TagGroupsSection.tsx` → **0 changed files** (AC-3).
- Anonymous share path — `routes/share/$token.tsx`, `lib/share-api.ts`, `apps/api/app/modules/share/` → **0 changed files** each. `NFR25-LEAKFENCE-1` fence intact (AC-16).
- `apps/api/` in its entirety → **0 changed files**; no backend change (AC-17).
- `routeTree.gen.ts` → **0 changed files**; V-6 held, no regeneration appeared (AC-17).
- `lib/api-types.ts` → **0 changed files**; the wire type already carried `categories`.

**Design decisions honoured as written.** No hook/fetch in the new component (D-1, D-10); mounted above the tags (D-2); location vocabulary copied verbatim from `ScopeChip.tsx:26` / `BrowseCategoryList.tsx:41`, no new token, no inline hex (D-3); `Link` with `params` and **no** `search` prop — typechecked without needing `search={{}}` (D-4); zero-category member → `null`, zero-category admin → one **static** advisory, never a link to the non-existent `/admin/categories` (D-5, V-8); wire order preserved, `parent_id` ignored, no `model_count` (D-9, D-10); labels from `name_pl`/`name_en` via a module-local `labelOf`, not i18n (D-8); both keys under `catalog.browse.` with the guard literal bumped 11 → 13 (D-11) and en/pl at **921 keys each, 1:1 parity**.

**No Ask-First condition was triggered and no Never was crossed.** No assignment/edit UI, no mutation, no link to a non-existent route, no `useCategories()`/`useCategoryBySlug()`, no `model_count`, no re-sort/nest/cap, no `accent`/`bg-muted`/`rounded-full` on a category, no blanket `--update-snapshots`, no human name on a baseline sign-off. `ModelSummary` and the anonymous share view untouched.

**Handoff carried forward (§ 9).** The D-5 advisory stays static text until **Story 52.2** ships `/admin/categories`; wiring it is a 52.2 change, not a 51.4 omission.

### File List

**New (4 + 12 baselines):**

- `apps/web/src/modules/catalog/components/ModelCategoriesSection.tsx`
- `apps/web/src/modules/catalog/components/ModelCategoriesSection.test.tsx` (15 tests)
- `apps/web/tests/visual/catalog-detail-categories.spec.ts` (3 tests × 4 projects)
- `apps/web/tests/visual/__snapshots__/catalog-detail-categories.spec.ts/` — 12 new PNGs

**Modified (8 source/test + 25 baselines + 2 BMAD artifacts):**

- `apps/web/src/modules/catalog/components/ModelHero.tsx` — import + mount line (+ a 2-line WHY comment)
- `apps/web/src/modules/catalog/components/ModelHero.test.tsx` — mock the new section + prop/position wiring test
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — 2 keys each (919 → 921)
- `apps/web/src/modules/catalog/browse-i18n.test.ts` — guard literal 11 → 13 + comment naming Story 51.4
- `apps/web/src/routes/share/MemberShareView.test.tsx` — D-6(c) `categories: []`
- `apps/web/tests/visual/api-stubs.ts` — D-6(a) `stubSotDetail` `categories` + override option and `DEFAULT_MODEL_CATEGORIES`; **plus the fourth site**, `stubViewerModelDetail` `categories: []`
- `apps/web/tests/visual/catalog-filestab-estimate.spec.ts` — D-6(b) `categories: []`
- 25 baseline PNGs across `catalog-detail.spec.ts` (12), `share-member-enriched.spec.ts` (4), `share-member-enriched-dismissed.spec.ts` (4), `admin-dropdowns-tooltip-open.spec.ts` (5)
- `_bmad-output/implementation-artifacts/51-4-model-detail-category-display.md` (this file), `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Remaining, controller-owned:** `infra/scripts/check-all.sh`, native `bmad-code-review`, independent Aider review, commit (with the 37 `baseline-reviewed:` lines), ff-merge, push, deploy, smoke, and the flip to `done`.

---

## Code Review Record (native `bmad-code-review`)

**Verdict: APPROVE.** No blocking defect, no actionable defect requiring a code patch. Status stays `review`.

- **Reviewer:** repo-local Claude Code, Claude Opus 5 (`claude-opus-5[1m]`), native BMAD `bmad-code-review` skill, run against the **working-tree diff** (`git diff HEAD`) vs baseline `main` @ `ac249bf`. **NOT** an Ezop signature, **NOT** human review of any kind; **no Codex, no Gemini, no Aider** in this pass (the independent Aider review remains a separate, controller-owned gate). No subagents were used — the operator profile for this session forbids `Agent` dispatch, so the Blind-Hunter / Edge-Case-Hunter / Acceptance-Auditor layers were executed inline by the reviewing session.
- **Date:** 2026-07-29. **Scope reviewed:** 12 source/test files + `api-stubs.ts` + 37 baseline PNGs + both BMAD artifacts. No file was modified by this pass except this artifact and `sprint-status.yaml`.
- **Checkpoint note:** the skill's step-01 checkpoint (confirm review target) was satisfied by the controller's explicit invocation (spec file + branch + baseline + "review this working tree"), not by a fresh human prompt. Recorded rather than skipped silently.

### Gates re-run independently by this review (not inherited from the dev record)

| Gate | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` (`tsc -b`) | **rc=0** |
| Lint | `npm run lint` (`eslint . --max-warnings=0` + stylelint) | **rc=0** (only the pre-existing "React version not specified" advisory) |
| Vitest | `npm run test` | **rc=0 — 147 files / 946 tests passed** |
| NFR26-DETERMINISM-1 | `npm run test` ×4 consecutive (this pass) | **identical every run: 147/147 files, 946/946 tests, rc=0** |
| Build | `npm run build` | **rc=0** (pre-existing >500 kB chunk advisory only); **no `routeTree.gen.ts` regeneration** after the build (V-6 held) |
| Visual — new + detail family | `test:visual -- catalog-detail-categories catalog-detail catalog-filestab-estimate` | **rc=0 — 40 passed / 0 failed** |
| Visual — share + admin + sheets + viewer chrome | `test:visual -- share-member-enriched share-member-enriched-dismissed admin-dropdowns-tooltip-open destructive-dialogs-edit-sheets-open image-viewer-containment remaining-sheets-open` | **rc=0 — 70 passed / 6 skipped / 0 failed** |
| Visual — `viewer3d-*` (the `stubViewerModelDetail` consumers) | `test:visual -- viewer3d` | **rc=0 — 30 passed / 2 skipped / 0 failed** |
| Whitespace | `git diff --check` | **rc=0** |

**140 visual assertions passed against the committed baselines and `git status` over `__snapshots__/` still lists exactly 37 PNGs afterwards** — nothing was regenerated by the review runs, so the committed baselines are reproducible, not run-specific. Backend untouched → **pytest was not run and this review claims no pytest result**.

### Independently verified claims

- **Zero-line diffs (AC-3, AC-16, AC-17):** `git status --porcelain` over `apps/api/`, `apps/web/src/routeTree.gen.ts`, `routes/share/$token.tsx`, `lib/share-api.ts`, `lib/api-types.ts` and `TagGroupsSection.tsx` → **empty**. Confirmed.
- **Anonymous share leak fence:** `routes/share/$token.tsx:618` mounts `MemberShareView` **only** on the authenticated-member branch; the anonymous path renders its own tree off the `/api/share/*` DTO and never reaches `ModelHero`. `ShareModelView` is a *type* from `lib/share-api.ts`, both untouched. `NFR25-LEAKFENCE-1` intact.
- **Every `CatalogDetailRender` caller is canonical:** `CatalogDetail.tsx:72` (`useModel`) and `MemberShareView.tsx:154` (`useShareModelProbe`, canonical `/api/models/{id}` under the same query key). No non-canonical `ModelDetail` reaches the unguarded `categories.length` read — the § 5 Ask-First trigger is genuinely not met, and the absence of a runtime `?? []` is correct.
- **i18n (AC-11):** `en.json`/`pl.json` at **921 keys each, key-set parity `True`**, **13** `catalog.browse.*` keys, **zero** browse keys whose pl value equals its en value. Guard literal bumped 11 → 13 with a comment naming Story 51.4.
- **Baseline accounting (D-7/AC-14):** exactly **37** changed PNGs — 12 new + 25 moved, matching the dev record file-for-file. **No out-of-family movement**: no `browse-rail-*`, `browse-sheet-*`, `facet-sidebar-*`, `category-browse-*` or `catalog-list-*` baseline differs from `main`. This is proven by the `git status` set itself, independently of any test run.
- **Baseline visual honesty (re-inspected by this reviewer, not taken on trust):** admin/member populated baselines show the `KATEGORIE` heading followed by two `bg-primary/10` + inset-primary-ring `rounded-md` entries, rendered **above** the `MOTYW` / `MATERIAŁ` / `BEZ GRUPY` tag rows and clearly distinct from the `bg-muted` tag chips; wire order preserved with the pl label first (`Przechowywanie i organizacja`) and the `name_pl: null` fallback second (`Holders & mounts`). Dark mode legible (NFR26-DARKMODE-1). The zero-category admin baselines show exactly one muted `Bez kategorii — do uzupełnienia` line — no heading, no dash, no control.
- **Keyboard focus (AC-12):** the entries carry no hover/focus classes of their own, but `styles/theme.css:103` applies a global `*:focus-visible { outline-2 outline-offset-2 outline-ring }`, so every category link has a visible focus indicator (WCAG 2.4.7). The unit suite additionally proves no `tabindex` shadows the tab order and no `aria-label` shadows the visible name (SC 2.5.3).
- **`data-testid` on a production component** is an established repo convention (17 non-test source files, including the sibling `TagGroupsSection.tsx:81` `tag-chip`), not a new practice introduced here.
- **`EXPERIENCE.md:251`'s "+ link to assign" is deliberately unmet**, and the review agrees with D-5/V-8: `/admin/categories` does not exist, the § 5 Never list forbids linking to it, and the assignment editor is Story 52.2. The static advisory is the honest render; the § 9 handoff is the correct record.

### Findings — all non-blocking, none patched

| # | Severity | Finding |
|---|---|---|
| **CR-1** | Minor (record-honesty; no code change) | **8 of the 12 new baselines duplicate existing ones.** `catalog-detail-categories-admin-{desktop,mobile}-{light,dark}.png` are **byte-identical** (md5 match) to `catalog-detail.spec.ts`'s `catalog-detail-{desktop,mobile}-{light,dark}.png`, and the four `…-member-*` baselines are the same surface within antialiasing noise (10–17 differing px, ratio ≈ 2×10⁻⁵) of `catalog-detail-member-*`. Both specs stub identically, both screenshot `fullPage`. Consequence: the hero's pixel surface is now baselined twice, so every future hero change costs 8 extra PNGs of triage and the two sets can drift apart silently. **Not patched:** AC-14 explicitly mandates populated-admin, populated-member and zero-category-admin screenshots, and element-scoping them would be a reviewer rewrite of a frozen, satisfied AC plus a deliberate 12-baseline regeneration. The genuinely new pixel coverage in this spec is the **zero-category-admin** family (4 PNGs); the populated pair's real added value is its DOM assertions (href, wire order, pl/en label split, advisory absence), which are worth keeping. **Recorded so the Dev Agent Record's "12 new baselines" is not read as 12 new surfaces.** Carried to Story 54.2 alongside the existing `/api/*` route-mock consolidation handoff. |
| **CR-2** | Nit (no change) | `tests/visual/catalog-detail-categories.spec.ts:41` types the helper option as `categories?: []` — the **empty-tuple** type, so `gotoDetail` can never be called with a populated override even though `stubSotDetail` accepts `BrowseCategorySummary[]`. Correct for this spec's three tests and typechecks cleanly; misleading if a later story reuses the helper. Left as authored under minimal-diff. |
| **CR-3** | Nit (no change; 54.2 handoff) | Category entries have **no hover affordance**, while the tag chips on the row below do (`hover:bg-accent`) and both shipped location surfaces style their interactive parts on hover (`ScopeChip` `ACTION` → `hover:underline focus-visible:underline`; `BrowseCategoryList` `ROW_IDLE` → `hover:text-foreground hover:bg-accent`). Not a WCAG failure — focus is covered globally (above) and hover is not a success criterion — and `DESIGN.md:140-144`'s `model-detail-category-link` block specifies no hover state, while § 5 forbids `accent` and any new colour token on a category. Adding one would therefore be an out-of-spec colour decision, not a defect repair. Flagged for the Story 54.2 cross-surface visual audit to settle deliberately. |

**Checked and found clean (no finding):** wire-order preservation and the absence of a client-side re-sort; `parent_id` ignored with no nesting/indentation; no `model_count` rendered; no `useCategories()`/`useCategoryBySlug()` mount and no network call from the section; mount position between the badge row and `TagGroupsSection`, asserted by both invocation order and DOM sibling; `Link` carries `params` and no `search`, resolving to `/categories/{slug}` with an empty search object after navigation; `labelOf` handles `name_pl` `null` **and** `""` under `pl`, and `i18n.language.startsWith("pl")` matches the shipped siblings; `cleanup` registered in `afterEach` (repo runs `vitest globals: false`); the zero-category member branch returns before any DOM node, so a member's tag-row spacing is byte-identical to `main`; every one of the three visual tests has an explicit `toBeVisible()` before its `toHaveScreenshot`; the fourth fixture site (`stubViewerModelDetail`) is genuinely fixed and the `viewer3d-*` baselines did not move; no inline hex, no new `--color-*` token, no `rounded-full`/`bg-muted`/`accent` on a category; no `import` ordering rule exists in `eslint.config.js`, so the new `ModelHero` import placement is not a lint deviation.

**Ask-First / Never audit:** no Never was crossed and no Ask-First condition was met. No assignment/edit UI, no mutation, no link to a non-existent route, no `ModelSummary` change, no anonymous-share change, no re-sort/nest/cap, no forbidden token, no blanket `--update-snapshots` (this review regenerated nothing), and no human name on any `baseline-reviewed:` provenance.

**`baseline-reviewed:` provenance, re-affirmed by this review:** the 37 PNGs were inspected by **Claude Opus 5 (`bmad-dev-story`, repo-local)** and re-inspected (spot-checked light + dark, desktop + mobile, populated + empty) by **Claude Opus 5 (`bmad-code-review`, repo-local)** on 2026-07-29. The commit's `baseline-reviewed:` lines must name those agents and **never `Ezop` or any human**.

**Remaining controller-owned steps after native review:** independent Aider review, `infra/scripts/check-all.sh`, commit, ff-merge, push, deploy, smoke, flip to `done`.

---

## Independent External Review Record

**Verdict: APPROVE.** `laura-aider-review-diff` (Aider v0.86.2, OpenRouter DeepSeek) reviewed the text-only working-tree diff with the 37 PNG baseline paths listed as context; binary PNG bytes were deliberately excluded from stdin to keep the review focused and bounded. Log: `.hermes/run-logs/aider-review-51-4-20260729_043851.log`, `RUN_EXIT rc=0`.

- **Critical:** none.
- **Important:** none.
- **Minor:** 3, all non-blocking and aligned with the native review record: duplicate pixel coverage for 8/12 new populated baselines, the visual helper's narrow `categories?: []` type, and lack of hover affordance on category entries pending a deliberate cross-surface visual audit.
- **Missing tests:** none.

Aider made **no edits**. This discharges the independent external-review gate. **No human review of any kind** is claimed; no Codex, no Gemini.

---

## Full Closeout Gate Record

`infra/scripts/check-all.sh` was run standalone by the controller after native BMAD review and independent Aider review. Log: `.hermes/run-logs/check-all-e51-4-20260729_043941.log`; exit marker `CHECK_ALL_RC=0 2026-07-29T04:50:52+02:00`; literal trailer `all green.`

All **16/16** stages passed:

- apps/api ruff format / ruff check
- workers/render ruff format / ruff check
- apps/web typecheck
- apps/web production build
- apps/web lint (eslint + stylelint)
- apps/web vitest — **147 files / 946 tests passed**
- apps/api pytest — passed
- workers/render pytest — passed
- infra/scripts pytest — passed
- apps/web visual regression — **586 passed / 42 skipped**
- settings-env-compose-diff
- uv-lock-check (apps/api)
- uv-lock-check (workers/render)
- local-env-secrets

This discharges the full pre-merge gate. **Remaining controller-owned steps:** commit, ff-merge, push, deploy, post-deploy smoke, and flip to `done`.
