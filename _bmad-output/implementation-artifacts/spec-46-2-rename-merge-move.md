---
title: 'Admin tag-groups screen — rename / merge / move + group create/reorder (Story 46.2)'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '9e526f85826d40ba20b7d6a43e8c81aec046eb0a'
final_revision: '760c526dc5be80555077eead6223467408e6d9ca'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** The `/admin/tag-groups` screen (Story 46.1) is read-only. Admins can see the tag taxonomy but cannot curate it — there is still no UI to rename a tag or group, merge duplicate tags, move a tag between groups, or create/reorder groups. Every governance write endpoint already exists and is live (E42/42.4); only the admin UI wiring is missing.

**Approach:** Extend `TagGroupsPage` with write affordances that call the existing admin governance API — per-tag actions (rename, move-to-group, merge-into), per-group actions (rename, move up/down to reorder), and a top-level "Create group". Add thin TanStack mutation hooks per endpoint; drive each action from a small dialog. No backend changes.

## Boundaries & Constraints

**Always:**
- Reuse the existing endpoints via `api()` (paths are `/api`-relative through `api()`): tag rename+move → `PATCH /admin/tags/{id}`; merge → `POST /admin/tags/merge` (body `{ from_id, to_id }`); group create → `POST /admin/tag-groups`; group rename+reorder → `PATCH /admin/tag-groups/{id}`. Do NOT add a new backend endpoint or a new merge endpoint.
- **Move-to-group must set `group_position` explicitly** — discharge the inherited 42.4 item (silent position-0 collision). When moving a tag into a group, send `group_position = <count of tags already in the target container>` (append at end); this applies whether the target is a group (use `target.tags.length`) or Ungrouped (`group_id: null`, `group_position = groupless.length`). Never rely on the tag's stale `group_position`.
- PATCH bodies send only changed fields (omit untouched). Send `name_pl: null` only to deliberately clear it (user emptied the field); never send explicit null for `slug`/`name_en`/`position`/`group_position` (all 422 per validators). `group_id: null` is the meaningful "make groupless" signal.
- After every successful write, invalidate the `["sot", "tag-groups"]` query (and `["sot", "tags"]` for tag rename/move/merge) so the list refreshes; show a `sonner` success toast; close the dialog. On `ApiError`, keep the dialog open and show an inline error (map 409 → slug-conflict copy, 400 → group-not-found copy, else generic).
- Group reorder is adjacent-swap of the `position` field: "move up" swaps this group's `position` with the previous group's, "move down" with the next; disable the boundary direction (first group can't move up, last can't move down). Groups render in the read's `(position, slug)` order.
- All new UI uses Tailwind semantic tokens only (`bg-*`/`text-*`/`border-*`) — no raw hex, no `dark:` variants. Reuse the existing `useLocalizedName()` (`preferPl` fallback) for all group/tag labels.
- All new copy goes under `modules.admin.tagGroups.*` in both `en.json` and `pl.json` with real (non-identical) Polish; the existing `tag-groups-i18n.test.ts` parity test auto-covers the prefix. If a new key is legitimately identical across locales (loanword), add it to that test's `COINCIDENTAL_MATCHES` allowlist rather than faking a translation.
- Every rendered write state (populated page with actions, and each open dialog) gets a Playwright visual assertion (`toBeVisible()` immediately before `toHaveScreenshot`) across all 4 projects, per the Epic 45 retro rule.

**Block If:**
- The live backend contract for any write endpoint no longer matches the documented shape (e.g. `PATCH /admin/tags/{id}` no longer accepts `group_id`/`group_position`, or merge is not at `POST /admin/tags/merge` with `{from_id,to_id}`) — HALT rather than guess a new contract.

**Never:**
- Do not add tag creation, tag deletion, or group deletion here — the 46.2 enumerated operations are rename/merge/move + group create/reorder only (tag-create/delete + group-delete are out of scope for this story).
- Do not add duplicate-tag detection (Story 46.3).
- Do not edit tag/group `slug` from this screen — rename edits display names (`name_en`/`name_pl`) only; slugs stay immutable identifiers (except when creating a new group, which requires a slug).
- Do not gate the reused read (`GET /tag-groups`) behind new backend permissions; do not bypass `api()` with raw `fetch`; do not hand-edit `routeTree.gen.ts`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Rename tag | Admin edits `name_en`/`name_pl` in rename dialog, submits | `PATCH /admin/tags/{id}` with only changed name fields; list refreshes; success toast | 409 → inline slug/name conflict copy; dialog stays open |
| Clear Polish name | Admin empties `name_pl`, submits | PATCH sends `name_pl: null`; label falls back to `name_en` | 422 unexpected → generic inline error |
| Rename group | Admin edits group `name_en`/`name_pl`, submits | `PATCH /admin/tag-groups/{id}` with changed fields; refresh; toast | 409 → inline conflict copy |
| Move tag into group | Admin picks a different target group | `PATCH /admin/tags/{id}` `{ group_id: <target>, group_position: <target.tags.length> }`; tag moves to end of target | 400 group-not-found → inline error |
| Move tag to Ungrouped | Admin picks "Ungrouped" for a grouped tag | PATCH `{ group_id: null, group_position: <groupless.length> }` | generic inline error |
| Merge tag | Admin picks a survivor target ≠ source, confirms | `POST /admin/tags/merge` `{ from_id: source, to_id: target }`; source tag disappears; refresh; toast | 404 → inline error; dialog open |
| Create group | Admin enters `slug`+`name_en` (+optional `name_pl`), submits | `POST /admin/tag-groups` `{ slug, name_en, name_pl?, position: groups.length }`; new empty group appears | 409 slug conflict → inline copy; empty slug/name → submit disabled |
| Reorder group up | Admin clicks "move up" on a non-first group | Two PATCHes swap `position` with previous group; order updates on refresh | either PATCH fails → error toast, list re-syncs from server |
| Boundary reorder | First group "move up" / last group "move down" | Control disabled (no request) | n/a |
| Non-admin | Authenticated non-admin at `/admin/tag-groups` | Redirected to `/` (unchanged from 46.1); no write UI reachable | n/a |

</intent-contract>

## Code Map

- `apps/web/src/modules/admin/TagGroupsPage.tsx` -- extend: add per-tag + per-group action menus, "Create group" button, dialog open-state, and mutation wiring. Keep 46.1 read/loading/error/empty branches intact.
- `apps/web/src/modules/admin/dialogs/RenameEntityDialog.tsx` -- NEW: generic `name_en`/`name_pl` editor (reused for tag rename and group rename); caller supplies title + initial values + submit handler + pending/error state.
- `apps/web/src/modules/admin/dialogs/MoveTagDialog.tsx` -- NEW: target-container `Select` (each group + "Ungrouped", current container excluded); confirms move.
- `apps/web/src/modules/admin/dialogs/MergeTagDialog.tsx` -- NEW: survivor-tag `Select` (all other tags from loaded data, source excluded), destructive-warning copy ("source tag deleted"), confirm.
- `apps/web/src/modules/admin/dialogs/CreateGroupDialog.tsx` -- NEW: `slug`+`name_en`+`name_pl` form; submit disabled until slug+name_en non-empty.
- `apps/web/src/modules/catalog/hooks/mutations/useUpdateTag.ts` -- NEW: `PATCH /admin/tags/{id}` with partial `{ slug?, name_en?, name_pl?, group_id?, group_position? }`; invalidate `["sot","tag-groups"]` + `["sot","tags"]`.
- `apps/web/src/modules/catalog/hooks/mutations/useMergeTags.ts` -- NEW: `POST /admin/tags/merge` `{from_id,to_id}`; same invalidations.
- `apps/web/src/modules/catalog/hooks/mutations/useCreateTagGroup.ts` -- NEW: `POST /admin/tag-groups`; invalidate `["sot","tag-groups"]`.
- `apps/web/src/modules/catalog/hooks/mutations/useUpdateTagGroup.ts` -- NEW: `PATCH /admin/tag-groups/{id}` (rename + reorder); invalidate `["sot","tag-groups"]`.
- `apps/web/src/modules/catalog/hooks/mutations/useCreateTag.ts` -- reference template for the new hooks (api() call + invalidate shape).
- `apps/web/src/lib/api-types.ts:90-117` -- `TagReadWithCount`/`TagGroupRead`/`TagGroupsResponse`/`TagGroupSummary`/`TagRead` consumed unchanged.
- `apps/web/src/ui/dialog.tsx`, `select.tsx`, `dropdown-menu.tsx`, `input.tsx`, `button.tsx` -- primitives to compose the dialogs and per-row action menus.
- `apps/web/src/modules/admin/TagGroupsPage.test.tsx` -- extend: cover each write flow (open → submit → assert outgoing request method/path/body → refresh), following the file's existing data-provision pattern.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` -- add `modules.admin.tagGroups.*` action/dialog/error/toast keys (en/pl parity).
- `apps/web/src/modules/admin/tag-groups-i18n.test.ts` -- unchanged mechanism; may need a `COINCIDENTAL_MATCHES` addition for any loanword key.
- `apps/web/tests/visual/admin-tag-groups.spec.ts` -- extend: regen populated/empty baselines (now carry action affordances) + add open-dialog screenshots (create-group, rename, move, merge) across the 4 projects.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/src/modules/catalog/hooks/mutations/useUpdateTag.ts` -- PATCH tag hook (rename + move) invalidating tag-groups+tags -- backs rename and move actions.
- [x] `apps/web/src/modules/catalog/hooks/mutations/useMergeTags.ts` -- merge hook -- backs merge action.
- [x] `apps/web/src/modules/catalog/hooks/mutations/useCreateTagGroup.ts` -- group create hook -- backs Create group.
- [x] `apps/web/src/modules/catalog/hooks/mutations/useUpdateTagGroup.ts` -- group PATCH hook (rename + reorder) -- backs group rename and up/down reorder.
- [x] `apps/web/src/modules/admin/dialogs/RenameEntityDialog.tsx` -- generic name editor dialog -- reused for tag + group rename.
- [x] `apps/web/src/modules/admin/dialogs/MoveTagDialog.tsx` -- target-group selector, computes explicit `group_position` -- move action.
- [x] `apps/web/src/modules/admin/dialogs/MergeTagDialog.tsx` -- survivor picker + destructive warning -- merge action.
- [x] `apps/web/src/modules/admin/dialogs/CreateGroupDialog.tsx` -- slug/name form -- create action.
- [x] `apps/web/src/modules/admin/TagGroupsPage.tsx` -- add per-tag action menu (rename/move/merge), per-group action menu (rename/up/down with boundary-disable), "Create group" button, dialog state + reorder swap logic -- wires everything to the screen.
- [x] `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` -- add action/dialog/error/toast keys under `modules.admin.tagGroups.*`, real pl translations -- i18n parity.
- [x] `apps/web/src/modules/admin/TagGroupsPage.test.tsx` -- add coverage for every I/O Matrix write row (assert method/path/body + refresh; boundary-disable) -- correctness gate.
- [x] `apps/web/tests/visual/admin-tag-groups.spec.ts` -- regen populated/empty baselines + add the four open-dialog states with `toBeVisible()` before each screenshot, 4 projects -- visual gate.

_Note (impl): move/merge dialogs use a native `<select>` (matching the `ChangeRoleModal` admin precedent) rather than the base-ui `Select` primitive, for deterministic jsdom testability; base-ui `Dialog` + `DropdownMenu` used as specified. Dialogs are presentational; the page owns mutations/toasts/error-mapping and builds move/merge candidate lists from the already-loaded `useTagGroups()` data (no extra fetch). Shared `dialogs/apiErrorMessage.ts` maps 409→conflict / 400→group-not-found / else generic._

**Acceptance Criteria:**
- Given an admin on `/admin/tag-groups`, when they rename a tag/group, merge a tag into another, move a tag between groups (or to/from Ungrouped), create a group, or reorder groups up/down, then the corresponding governance endpoint is called with the correct method/path/body and the list reflects the change after refresh.
- Given an admin moves a tag into a group, when the request is built, then `group_position` is sent explicitly as the target container's current tag count (never omitted / never a stale value), so no silent position-0 collision occurs.
- Given a write fails with a conflict/validation error, when the response returns, then the dialog stays open with an inline, localized error and no partial UI corruption; the tag-groups list still reflects only server-confirmed state.
- Given a non-admin navigates to the route, then they are redirected to `/` and no write UI or data is reachable (46.1 behavior preserved).
- Given the visual suite runs, then populated + empty page baselines and the four open-dialog states pass in all 4 projects (light/dark × desktop/mobile).

## Spec Change Log

_No bad_spec loopback occurred; empty._

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1, low 0)
- defer: 1
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` `MergeTagDialog` reset effect (`useEffect([open, options])`) re-seeded the survivor selection to `options[0]` on every parent re-render, because the page rebuilds `options` as a fresh array each render (inline `mergeOptions`). A background refetch (`refetchOnWindowFocus` after `staleTime`) while the dialog was open would silently snap the selection back to the first tag → a confirmed merge would delete the source and reassign its models to the WRONG survivor (destructive). Fixed: the effect now preserves the current selection when it is still a valid option and only re-seeds when it has disappeared; added `MergeTagDialog.test.tsx` locking preservation-across-rerender + re-seed-when-removed.
  - `[medium]` `[patch]` `MoveTagDialog` had the identical unstable-`options` reset bug → a background re-render could move a tag into the wrong group. Same fix + `MoveTagDialog.test.tsx` regression test.
  - Deferred (F3): the two-PATCH adjacent-swap reorder (`TagGroupsPage.reorder`) has no rollback on partial failure — if the first `PATCH position` lands and the second fails, two groups share a `position` (read tie-breaks by slug); an equal-position swap is also a no-op that still toasts success. Low consequence (group display order only, self-heals on next successful reorder/refetch, requires a mid-swap server error) and the spec pre-accepted the tradeoff; the robust fix is a backend atomic-reorder endpoint, out of this frontend story's scope. Recorded in `deferred-work.md`.
  - Rejected (F4): the two concurrent `mutateAsync` calls share one mutation instance so `isPending` tracks only the latest — noise; self-heals via invalidation and the reorder control lives in a menu that closes on click.
  - Rejected (F5): `CreateGroupDialog`/`RenameEntityDialog` omit `DialogDescription` (Move/Merge include it) — cosmetic a11y-consistency only; the repo convention is already mixed (`Viewer3DModal`, `ImageFullscreenViewer` omit it too).

### 2026-07-22 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 9
- addressed_findings:
  - none
- notes (fresh Blind Hunter + Edge Case Hunter pass on the shipped diff; no new actionable defects — every finding is already-tracked, spec-conformant, or a pre-accepted low-consequence tradeoff, so no code changed):
  - Reject/already-tracked: the reorder cluster resurfaced by both reviewers — two-PATCH swap non-atomic partial-failure (duplicate `position`), equal-position swap no-op that still toasts success, and the untested reorder-failure branch — is the same F3 already recorded in `deferred-work.md` (spec Design Notes pre-accepted it; robust fix = backend atomic-reorder endpoint, out of scope). Not re-deferred to avoid a duplicate ledger entry.
  - Reject/spec-conformant: `mapApiError` (409→conflict, 400→group-not-found, else generic) implements the spec Boundaries error-mapping verbatim; the "400 reads oddly for rename/merge" and "422 slug-format → generic" concerns require responses the documented contract doesn't emit for those flows (400 is a move-only signal), so they are unreachable/spec-accepted.
  - Reject/spec-conformant: merge dialog pre-selecting the first survivor with an immediately-enabled button mirrors the Move dialog pattern and ships the mandated destructive-warning banner; requiring an empty placeholder is a design change, not a defect.
  - Reject/low-consequence: Move/Merge dialogs opening with an empty `<select>` only in degenerate states (a catalog with exactly one tag; a groupless tag with zero groups) that don't occur in the real taxonomy, and are recoverable via Cancel; a guard would add non-trivial prop threading against the minimal-diff policy.
  - Reject/pre-accepted: stale/concurrent `group_position`/`position` collisions (two admins, or a stale tab) fall under the spec Design Notes' explicit "acceptable at admin scale" tradeoff; multi-admin concurrency is out of this story's scope.
  - Reject/low-consequence: a no-op rename closing silently without a toast, and the `name_pl === ""` (empty-string) vs `null` normalization firing one redundant harmless PATCH, are cosmetic with no spec requirement.

### 2026-07-22 — Dev-repair pass (verify gate REQUEST_CHANGES)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` The independent verify-gate review (`aider-review-gate.py`, rc=4 → REQUEST_CHANGES) flagged the non-atomic group reorder as a critical data-consistency risk: the two-PATCH adjacent-swap fired both writes concurrently (`Promise.all`), so a first-lands/second-fails partial failure left two groups sharing a `position`. Fixed within the frozen intent contract (still "adjacent-swap of `position`" + "either PATCH fails → error toast, list re-syncs from server"): the PATCHes now run sequentially and, on second-PATCH failure, a best-effort compensating PATCH restores the first group's original `position` so the server never persists a duplicate-position order. Added `TagGroupsPage.test.tsx` "reorder partial failure rolls back the first PATCH…" covering the previously-untested partial-failure branch. Updated the F3 `deferred-work.md` entry (partial-failure inconsistency now resolved; only out-of-scope single-request atomicity + corrupt-seed equal-position no-op remain).
  - `[low]` `[patch]` Same review's Minor "inconsistent dialog accessibility": `CreateGroupDialog` and `RenameEntityDialog` omitted `DialogDescription` while Move/Merge include it. Added a `DialogDescription` to both (screen-reader-only via `sr-only`, so no visual-baseline change) with new `create.description` / `rename.description` i18n keys (en+pl parity auto-covered by `tag-groups-i18n.test.ts`). This reverses the earlier F5 reject now that the same finding blocks the deterministic gate.

### 2026-07-22 — Review pass (dev-repair re-review)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 12
- addressed_findings:
  - none
- notes (fresh Blind Hunter + Edge Case Hunter pass over the repaired diff; no new actionable defects — the reorder rollback is a strict improvement over the prior concurrent `Promise.all`, and every surfaced item is already-tracked, spec-conformant, or a pre-accepted low-consequence tradeoff, so no code changed):
  - Reject/pre-accepted: the reorder rollback cannot cover a network partition where the second PATCH applies server-side but its response is lost (both groups then briefly share a `position`). This residual is the same non-atomic tradeoff already recorded as F3 — true single-request atomicity needs an out-of-scope backend endpoint — and it self-heals on the next refetch. The change still strictly improves the common clean-failure case, which now rolls back to a consistent order. Same bucket: the transient duplicate-position window between the two success-path PATCHes, and the equal-position swap no-op (only reachable from corrupt seed data).
  - Reject/spec-conformant: `mapApiError` 400→group-not-found and the count-based append `group_position`/`position` are the spec Boundaries verbatim; the "400 reads oddly for create/rename" and "counts collide across position gaps" concerns fall under the documented duplicate-position tolerance and the move-only 400 signal.
  - Reject/already-tracked: Move/Merge dialogs reachable with an empty candidate `<select>` in degenerate catalogs, and `reorderPending`/`isPending` conflating rename with reorder, are the prior passes' rejected F4/F5-class findings; the Move/Merge selection-preserving effect firing on each render is the intended pass-1 fix (it bails via the state-setter).
  - Reject/cosmetic: the sr-only (Create/Rename) vs visible (Move/Merge) `DialogDescription` is a deliberate choice adding a11y parity without a visual-baseline regen; the Edge Case Hunter confirmed no reachable missing-`aria-describedby` path. The partial-failure reorder test asserting PATCH call counts (not the toast) matches every other write test's convention in this file (none mount the sonner Toaster).

## Design Notes

Merge target and move target lists are built from the already-loaded `useTagGroups()` data (all tags across `groups[].tags` + `groupless`) — do not add a separate `useTags` fetch. Exclude the source/current container from options.

Reorder swap (in `TagGroupsPage`): for "move up" at rendered index `i`, fire `useUpdateTagGroup` sequentially — first `{id: groups[i].id, position: groups[i-1].position}`, then `{id: groups[i-1].id, position: groups[i].position}` (the hook invalidates after each success). Running them in sequence (not `Promise.all`) means a mid-swap failure leaves at most one applied write; if the second PATCH fails after the first landed, a best-effort compensating PATCH restores `groups[i]` to its original `position` so the server never persists two groups sharing a `position`. If two groups share an equal stored `position` (only possible from corrupt seed data), the swap is a visual no-op (read tie-breaks by slug); acceptable at admin scale, not worth a full reindex. True single-request atomicity would need a backend reorder endpoint (out of scope).

Mutation hook shape (mirror `useCreateTag.ts`):
```ts
export function useUpdateTag() {
  const qc = useQueryClient();
  return useMutation<TagRead, ApiError, { id: string; body: Partial<TagPatchBody> }>({
    mutationFn: ({ id, body }) => api<TagRead>(`/admin/tags/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tag-groups"] });
      void qc.invalidateQueries({ queryKey: ["sot", "tags"] });
    },
  });
}
```

## Verification

**Commands:**
- `pnpm --filter web test -- TagGroupsPage` -- expected: write-flow unit tests pass.
- `pnpm --filter web test -- tag-groups-i18n` -- expected: i18n parity passes.
- `pnpm --filter web typecheck` -- expected: no new type errors.
- `pnpm --filter web lint` -- expected: no new lint warnings (`--max-warnings=0`).
- `npx playwright test --config=tests/visual/playwright.config.ts admin-tag-groups` (from `apps/web/`) -- expected: all 4 projects pass; regenerate baselines intentionally with `--update-snapshots` and review the diff (only the added action affordances + new dialog states).

**Manual checks (if no CLI):**
- Confirm each dialog renders correctly in light and dark themes with token-only styling, and that move/merge selectors exclude the source/current container.

## Auto Run Result

Status: done

### Summary

Dev-repair iteration: the deterministic verify gate (`aider-review-gate.py`) returned rc=4 (independent review verdict `REQUEST_CHANGES`), driven by a critical data-consistency risk in the group reorder and a minor dialog-accessibility inconsistency. Repaired both **without touching the frozen `<intent-contract>`**, then re-reviewed adversarially (Blind Hunter + Edge Case Hunter) with no new actionable defects.

- **Reorder consistency (critical):** the two-PATCH adjacent-swap previously fired both writes concurrently (`Promise.all`), so a first-lands/second-fails partial failure left two groups sharing a `position`. Now the PATCHes run sequentially and, if the second fails after the first landed, a best-effort compensating PATCH restores the first group's original `position`, so the server never persists a duplicate-position order in the common clean-failure case. Still honors the intent contract's "adjacent-swap of `position`" + "either PATCH fails → error toast, list re-syncs from server". The only residual (network partition where the second write applies but its response is lost) is the same non-atomic tradeoff already recorded as F3 and self-heals on refetch.
- **Dialog a11y (minor):** added a screen-reader-only `DialogDescription` to `CreateGroupDialog` and `RenameEntityDialog` for a11y parity with Move/Merge (sr-only → no visual-baseline change), with en+pl i18n keys auto-covered by the parity test.

### Files changed

- `apps/web/src/modules/admin/TagGroupsPage.tsx` — `reorder()` now sequential with a compensating rollback on partial failure; pass `description` to both rename dialogs.
- `apps/web/src/modules/admin/dialogs/RenameEntityDialog.tsx` — optional `description` prop rendered as an sr-only `DialogDescription`.
- `apps/web/src/modules/admin/dialogs/CreateGroupDialog.tsx` — sr-only `DialogDescription`.
- `apps/web/src/locales/en.json`, `apps/web/src/locales/pl.json` — new `create.description` + `rename.description` keys (real pl translations).
- `apps/web/src/modules/admin/TagGroupsPage.test.tsx` — new "reorder partial failure rolls back the first PATCH…" test covering the previously-untested partial-failure branch.
- `_bmad-output/implementation-artifacts/deferred-work.md` — F3 entry updated (partial-failure inconsistency resolved; only out-of-scope single-request atomicity + corrupt-seed equal-position no-op remain).

### Review findings breakdown

- Dev-repair pass: patch 2 (high 1 reorder consistency, low 1 dialog a11y); intent_gap 0, bad_spec 0, defer 0, reject 0.
- Adversarial re-review pass: patch 0, defer 0, reject 12 (all already-tracked, spec-conformant, pre-accepted, or cosmetic); intent_gap 0, bad_spec 0.

### Verification performed

- `pnpm --filter web test -- TagGroupsPage tag-groups-i18n RenameEntityDialog CreateGroupDialog MoveTagDialog MergeTagDialog` — pass (25 tests; `window.scrollTo` lines are pre-existing jsdom noise, not failures).
- `pnpm --filter web typecheck` — pass.
- `pnpm --filter web lint` (`--max-warnings=0`) — pass.
- Visual suite not re-run: the sr-only descriptions add no visible pixels and the reorder change is behavior-only, so the committed baselines remain valid (no `--update-snapshots` needed).

### Residual risks

- Group reorder remains non-atomic at the transport layer: a network partition that applies the second PATCH but drops its response can still briefly leave two groups sharing a `position` (self-heals on refetch). Full single-request atomicity is deferred (F3) pending a backend reorder endpoint, out of this frontend story's scope.

