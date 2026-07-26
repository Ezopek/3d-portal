# Reconciliation — `docs/design/HANDOFF-tagi-fasetowe.md` (Initiative 25)

The facet-tag handoff is **shipped history**, not a competing spec. It is reconciled here because Initiative 26 changes the *role* of one thing it established — the facet sidebar as navigation — and must be shown to change nothing else.

## Preserved verbatim by this pass

| HANDOFF decision | Status |
|---|---|
| Tags are many-to-many with Model; a tag belongs to **one** group | Unchanged. `EXPERIENCE.md` § Foundation restates it and § Non-goals forbids Tag↔TagGroup M:N. |
| `TagGroup` is a real admin-managed table, not a string convention | Unchanged. The admin tag-group surface is untouched by this pass; categories get a **separate** tab. |
| `tag.group_id` is a **nullable** FK; null is the curation-queue state | Unchanged, and promoted to a visible curation check ("ungrouped user-facing tag"). |
| AND between groups, OR within a group, with a user-visible `tag_match` override | Unchanged. `FR26-BROWSE-3`; category scope is never folded into `tag_match`. |
| Client-side substring tag search over the already-loaded `useTagGroups()` — no new endpoint, no fuzzy | Unchanged, and extended: the `+tag` suggestion surface reuses the shipped `GET /api/tags?q=` and resolves group labels from the same already-loaded map. |
| Two leading groups expanded by default, plus any group with an active filter; collapse persisted per user in `localStorage` | Unchanged. The facet list **relocates** into the Filters surface with this behaviour intact. |
| `Bez tagów` pseudo-facet pinned at the bottom | Unchanged, and counted in `Filters (n)`. |
| Creators are a separate facet; no tag prefixes | Unchanged, and reinforced — "Twórca / Premium" is in the **rejected category candidates** table. |
| Empty result from an over-narrow AND offers "Switch to OR" / "Clear filters" | Unchanged, and given explicit precedence over the new scoped-empty branch in § State Patterns. |
| Token-only colours, `.dark` theme-aware, zero inline hex | Unchanged, and this pass adds **no new token at all**. |
| Entity labels come from `name_pl` / `name_en`; UI chrome comes from i18next | Unchanged, including the empty-string-`name_pl` fallback guard. |

## Superseded — one thing only

| HANDOFF statement | Superseded by | Nature of the change |
|---|---|---|
| `CategoryTreeSidebar.tsx` → **replace with `FacetSidebar`** as the catalog's left navigation (§4) | `FR26-BROWSE-1`; `EXPERIENCE.md` § Component Patterns (Browse rail) and § Component Ownership | **Role, not function.** `FacetSidebar` stops being *navigation* and becomes the body of the `Filters (n)` surface. Its behaviour — group search, collapse persistence, per-tag counts, `Bez tagów` — moves with it unchanged. The component is **relocated, not deleted**; whether that is literally the same component or a re-render inside the panel is a Story 51.1 / 52.1 decision against then-current code, per its `VERIFY-AT-CREATE-STORY` marker. |

Nothing else in the HANDOFF is reversed. In particular: the retirement of the **mandatory single category** (`Model.category_id` NOT NULL, the self-referential `category` tree, `CategoryTree`) stays permanent. Initiative 26's category is a **new, independent, many-to-many, zero-valid** entity with distinct identifiers (`BrowseCategory*`, `browse_category`).

## The one place the HANDOFF is *reused as content*, deliberately

HANDOFF §8 lists the starter facet taxonomy, and it shipped as `STARTER_TAXONOMY` in `apps/api/app/core/db/seed.py` (8 groups / 36 tags). This pass reads it as the **vocabulary the category set must not duplicate**:

- the `Typ` group's 12 object-shape tags (`Wazony`, `Klipsy`, `Etui`, …) are explicitly **rejected** as a 1:1 category source — see `EXPERIENCE.md` § Browse Taxonomy, rejected candidates;
- `Pomieszczenie`, `System`, `Materiał`, `Twórca (premium)` and `Poziom` are likewise rejected as category axes;
- every one of the eight categories is required to **cross ≥ 2** of these groups, which is the mechanism that keeps a category from collapsing back into a tag;
- every category label was widened so that **no category label is byte-identical to any shipped tag or tag-group label**, giving Story 52.3's label-overlap check a known-good baseline.

## Dropped qualitative ideas — surfaced

1. **HANDOFF §9's `DEFAULT_EXPANDED_GROUP_COUNT = 2` "tunable constant"** — inherited unchanged into the Filters surface. This pass deliberately does **not** re-tune it, even though the Filters surface has more vertical room than the old sidebar did. Re-tuning would be a change with no evidence behind it, and the constant is already tunable without touching logic.
2. **HANDOFF §5's `untagged=true` triage filter** ("important after the migration — everything starts untagged") — the same posture now applies to categories, and this pass adopts it as the **admin curation queue's "models with zero categories"** row rather than as a second public pseudo-facet. Reason: a public `Bez kategorii` checkbox would contradict `FR26-CAT-2` ("zero categories is valid and the model stays public/visible"), which is exactly the trap the tag-side `Bez tagów` facet does *not* fall into, because an untagged model genuinely matches no filter while an uncategorised model still appears everywhere.
3. **HANDOFF §3's `?with_counts=true` shared-helper approach** — reused for `model_count` on the category read, so the two counts can never disagree. Recorded here because it is an inherited idea, not a new one.
