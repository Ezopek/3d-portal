# Epic 46 Context: Admin tag/group management screen

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic E46 gives admins the one net-new screen in the facet-tags initiative (Initiative 25): a governance surface to manage tag groups and the tags inside them. It lists tags per group with counts, and supports rename, merge, move-to-group, duplicate detection, and group create/reorder. Merge is reuse of an existing endpoint, not new build — the genuinely new work is group governance (create/rename/reorder/delete) and the admin UI itself. E46 depends on E42's additive backend governance API (already shipped and live) and E43's frontend data layer.

## Stories

- Story 46.1: Group list + counts
- Story 46.2: Rename / merge / move
- Story 46.3: Duplicate detection

## Requirements & Constraints

- Tag creation is admin-only; this screen is where admins manage the curated tag set that non-admin surfaces (EditTagsSheet, model-detail inline add) can only select from.
- The screen must list tags per group with per-tag counts (model_count), matching mockup 06 (right panel).
- Supported operations: rename a tag or group, merge tags (reusing the existing merge endpoint — do not rebuild it), move a tag to a different group (including to/from groupless), duplicate-tag detection for operator cleanup, and group create/reorder.
- Deleting a group must not delete or block on its tags — tags become groupless, not orphaned or cascade-deleted. This is a hard existing invariant from the data model, not something E46 needs to (re)implement, only respect in the UI/UX (e.g. confirming a group delete doesn't say "delete tags").
- Deleting a tag still requires merge-or-empty first (a tag cannot be deleted while models reference it) — this RESTRICT posture on `model_tag.tag_id` is unchanged and the UI must not imply otherwise.
- Every write action must produce an audit row (already true of the underlying API — the UI doesn't need to build audit logging, just not bypass the API layer that does).
- All new UI must be theme-token-only (Tailwind `--color-*` tokens) and pass both light and dark themes — no inline hex colors.
- i18n: Polish/English parity required for all new UI copy (merge/rename/newGroup/duplicates admin strings).
- Admin-only route: gated the same way as the existing admin screens (403 for non-admins), consistent with the category-CRUD posture it succeeds.

## Technical Decisions

- Backend governance API is already shipped (E42/Story 42.4, live on main): `POST/PATCH/DELETE /api/admin/tag-groups` (group create/rename+reorder/delete), `POST /api/admin/tags` (admin-only tag create, moved to a dedicated `sot-admin-governance` router so it isn't mistaken for an agent-writable route), and an extended `PATCH /api/admin/tags/{id}` that also accepts `group_id`/`group_position` for move-to-group. `POST /api/tags/merge` already existed pre-Initiative-25 and is reused unchanged for merge/rename/patch/delete-sibling behavior.
- Group delete uses `ON DELETE SET NULL` on `tag.group_id` — tags survive their group's deletion and become groupless; there is no tag deletion side effect to guard against in the UI.
- Known gaps explicitly left for E46 by the 42.4 review (not yet fixed, and now this epic's responsibility): (1) when Story 46.2 moves a groupless tag into a group, it must set `group_position` explicitly — omitting it silently reuses the tag's stale value (often `0`), which can collide with other tags already in that group; the 42.2 read tie-breaks ties by slug, so this is silent, not crashing, but should be handled deliberately by the move UI/API call. (2) `detached_tag_ids` in the group-delete audit payload is unbounded by group size — acceptable at current scale but worth revisiting if group membership grows large.
- Explicit-null vs omitted-field semantics on PATCH endpoints: explicit `null` on a NOT NULL patch field (e.g. `slug`, `name_en`, `position`) is rejected at 422 by field validators; omitting a field leaves it untouched (Pydantic v2 skips validators for omitted defaults). Only genuinely nullable fields (`name_pl`, `group_id`) accept explicit null. The admin UI's write calls should rely on this contract (omit fields it isn't changing) rather than sending nulls defensively.
- Admin FE screens follow an established pattern: `apps/web/src/modules/admin/AdminTabs.tsx` holds an `ActiveTab` union type and tab chrome; each admin screen is a `routes/admin/<name>.tsx` route mirroring existing tabs (e.g. `users.tsx`, `invites.tsx`, `profiles.tsx`, `queues.tsx`). E46 adds a new tab following this same mirroring convention. Adding a new TanStack route requires regenerating `routeTree.gen.ts` and updating AdminTabs visual baselines.
- Frontend types/hooks this screen consumes are additive per E43: `TagReadWithCount`, `TagGroupRead` (`{ id, slug, name_en, name_pl, position, tags }`), `TagGroupsResponse` (`{ groups, groupless }`), `TagGroupSummary` (flat admin write-response, no `tags[]`), and `useTagGroups()`. No embedded group label lives on `TagRead` itself — the human-readable group name always comes from the tag-groups response.
- All Init-25 SoT/admin reads and writes are authenticated default-deny (`current_admin` for governance writes), never added to `_PUBLIC_ROUTES`.

## Cross-Story Dependencies

- E46 depends on E42 (group governance API — already `done` and live on main) and E43 (frontend data layer — types/hooks/URL state) being on `main`.
- Story 46.2 explicitly inherits an open item from the 42.4 review: set `group_position` explicitly whenever moving a groupless tag into a group, to avoid a silent position-0 collision.
- Merge (46.2) is reuse of the existing `POST /tags/merge` endpoint, not new backend work — treat it as a UI wiring task, not an API design task.
- This is the only net-new admin screen in Initiative 25; it does not depend on or block the catalog browse/detail/edit UI epics (E44/E45), though it shares the same underlying tag/tag-group data model and FE type/hook layer.
