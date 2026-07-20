# Epic 45 Context: Card / detail / edit

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic E45 finishes surfacing the new facet-tag taxonomy (Initiative 25) on the three remaining catalog UI touchpoints: the model card, the model detail view, and the tag-editing sheet. It renders per-model facets on the card, groups tags by facet on detail, and makes tag editing group-aware with admin-only tag creation — plus drops the category selector from the admin model-add form (partially deferred, see Cross-Story Dependencies). It depends on E43 (frontend data layer: types, hooks, URL state) being on `main`, and reuses UI patterns established in E44 (catalog browse: FacetSidebar, FilterRibbon, CatalogList).

## Stories

- Story 45.1: `ModelCard` untagged chip
- Story 45.2: `CatalogDetail` grouped tags
- Story 45.3: `EditTagsSheet` grouped picker + create-form cutover

## Requirements & Constraints

- Zero-tag models must remain valid, first-class catalog entries. Every model starts untagged after the cutover (categories are dropped with no data migration), so untagged is the expected common state, not an error.
- The model card must visually distinguish "no tags" from "tags present" with a single ghost-style placeholder chip rather than an empty tag row.
- On detail view, tags render grouped by their facet (group label + chips). A facet group with no tags for a given model is hidden entirely for regular users, but shown as a dash with an inline "Add" affordance for admins.
- Clicking a tag on the detail view navigates to the catalog pre-filtered by that tag.
- Tag creation remains admin-only. Non-admin users can only select from existing tags in the edit sheet; the "create new tag" affordance must not be shown to them.
- The tag-edit picker groups its options by facet, matching the sidebar's grouping.
- All new/changed UI must be theme-token-only (Tailwind classes on `--color-*` tokens, e.g. `bg-card`, `text-muted-foreground`, `border-border`) — no inline hex colors — so light and dark mode both work automatically. This is a hard acceptance criterion.
- i18n: Polish/English parity required for any new UI copy (facet/tag/group strings); category-only i18n keys are being retired elsewhere (E47) — don't add new dependencies on them.

## Technical Decisions

- Data model: tags are grouped via a nullable `Tag.group_id` FK to a new `TagGroup` entity (`SET NULL` on group delete — a tag survives its group's deletion and becomes "groupless"). The `model_tag` many-to-many join is unchanged. `Category` and `Model.category_id` are being retired, but only in the terminal cutover epic (E47) — the live category API/fields remain a zero-code compatibility bridge until then.
- Frontend types are additive for this phase: `TagRead` carries `group_id` + `group_position` only (no embedded group label/slug — the human-readable group name comes from `GET /api/tag-groups`, consumed via `useTagGroups()`). Shipped group types to use: `TagListItem`, `TagReadWithCount`, `TagGroupRead` (`{ id, slug, name_en, name_pl, position, tags }`), `TagGroupsResponse` (`{ groups, groupless }`).
- `GET /api/models` supports `tag_ids`, `tag_match` (`all`|`any`, default `all`), and `untagged` (zero-tag models only) — already wired by E42/E43; E45 components consume this via existing hooks/URL state rather than reimplementing filtering.
- The "groupless" pseudo-facet ("Bez tagów" / "Untagged") is a first-class rendering case, not an error path — applies both to models with zero tags (card/detail) and to tags with no assigned group (edit picker).
- Admin tag creation and group governance (rename, merge, move-to-group) live in a separate admin screen (E46); E45's `EditTagsSheet` only needs to gate/hide the create affordance for non-admins, not implement governance itself.

## UX & Interaction Patterns

- ModelCard: tag chips already render via `topTags`; for zero-tag models, replace the (currently empty) chip row with a single dashed/ghost-style "Bez tagów" chip rather than leaving blank space (mockups 08A/08B).
- CatalogDetail: tags render in facet groups, each with a group label and its chips. An admin viewing a group with no tags for the model sees a dash placeholder plus an inline "Add" action; a regular user simply doesn't see that group. Each tag chip is clickable and navigates to the catalog pre-filtered on that tag (mockups 05, 08C).
- EditTagsSheet: picker options are grouped under facet headings, mirroring the sidebar's grouping. Selected-tag chips continue to display at the top of the sheet, unchanged. The "create new tag" path is removed from the picker for non-admin users — selection-only for them.

## Cross-Story Dependencies

- Story 45.3's admin create-form change (removing the category selector from `routes/admin/models/new.tsx`) cannot ship on its own: the backend still requires `ModelCreate.category_id` until Story 47.5 lands. That selector removal is deferred and must deploy in the same `main` HEAD as 47.5's `ModelCreate.category_id` drop (single-host deploy applies API+web from one commit). Until then, the create form keeps the category selector. This constraint does **not** block the rest of 45.3 — the grouped tag picker itself has no such coupling and proceeds independently within E45.
- E45 depends on E43's frontend data layer (types, hooks, URL state) already being merged to `main`, and benefits from reusing UI patterns established in E44 (facet grouping/collapsing conventions, AND/OR filter semantics) for visual and interaction consistency across the catalog surfaces.
