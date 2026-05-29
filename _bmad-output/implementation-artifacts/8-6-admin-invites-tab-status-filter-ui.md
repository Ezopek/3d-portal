# Story 8.6: Admin Invites tab — `/admin/invites` route + status-filter UI

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer (Ezop, banking-IT operator wearing the dev-team ITCM hat),
I want **the Epic 8 Admin Invites tab — paginated list + status filter + generate-invite modal + per-row revoke button — wired end-to-end on top of the Story 6.3 admin invite endpoints (`POST/GET /api/admin/invites` + `POST /api/admin/invites/{id}/revoke`, already shipped + tested), so that all four brief-defined routine operator actions per epics §1741 acceptance gate ("generate invite (via E6 Story 6.3 endpoint surfaced via Invites tab in 8.6), revoke invite (via 8.6 panel button), change user role (via 8.3), reset user password (via 8.5)") become FULLY panel-driven without DB-direct surgery, Decisions A + B (architecture.md §1417-1456) DB-row metadata surfaced verbatim in the UI (eight per-row columns: `role`, `generated_by`, `generated_at`, `ttl_seconds`/`expires_at`, `used_by`, `used_at`, `used_from_ip`, `revoked_at` plus computed `status`), cleartext-token-surfaces-ONCE UX mirroring Story 8.5's `ResetLinkDisplayModal` precedent (Decision B verbatim "cleartext token never returned in any list-invites response"), the Story 8.5 `useIssuePasswordResetAdminUser` hook precedent extended to a NEW `apps/web/src/modules/admin/hooks/useAdminInvites.ts` (peer of `useAdminUsers.ts` — separate file because invite-row is a distinct entity, NOT a User mutation), the AdminTabs `<span aria-disabled="true">` placeholder REPLACED with a live `<Link to="/admin/invites">` mirroring the Users tab shape verbatim (the only frontend AdminTabs.tsx mutation in this story), and ZERO backend changes (NO new endpoints, NO Pydantic schema additions, NO Alembic migration, NO new audit action names, NO new rate-limit scope, NO new entity_type — the Story 6.3 server-side contract is the binding API surface), in one atomic story per epics §1820-1831 acceptance gate verbatim**, namely:

1. **NEW route file `apps/web/src/routes/admin/invites.tsx`** mirroring `apps/web/src/routes/admin/users.tsx` exactly: TanStack Router `createFileRoute("/admin/invites")` + `<AuthGate>` wrapper + `<Navigate to="/" replace />` when `!isAdmin` + `validateSearch` accepting `{page?: number, page_size?: number, status?: "active"|"used"|"expired"|"revoked"}`. The route renders the NEW `<InvitesPage />` component. **Critical:** `routeTree.gen.ts` MUST be regenerated via `npm run generate:routes` after adding the file — the regeneration is a side-effect, commit the regenerated file alongside the source (per Story 8.5 §T17 verbatim convention).

2. **NEW component `apps/web/src/modules/admin/InvitesPage.tsx` (~280-320 LOC)** mirroring the `apps/web/src/modules/admin/UsersPage.tsx` shape and conventions: header (title + description), `<AdminTabs activeTab="invites" />`, status-filter dropdown (5 options: all/active/used/expired/revoked — `all` is the absence of the `status` query param), per-page-size dropdown (25/50/100/200), a "Generate invite" primary button (top-right), error-banner pattern via `errorCode` useState slot + `KNOWN_ERROR_CODES` Set (`generic`, `invite_not_found`, `invite_already_resolved`), table with 9 columns rendering each `InviteListItem` from the Story 6.3 list response (`role` / `generated_by` / `generated_at` / `expires_at` (computed from `generated_at + ttl_seconds`) / `used_by` (or `—`) / `used_at` (or `—`) / `used_from_ip` (or `—`) / `revoked_at` (or `—`) / `status` (badge with role+status-coded styling) + Actions column with per-row "Revoke" button (visible ONLY for `status === "active"` rows; disabled with greyed-out styling for the other 3 statuses — mirrors Story 8.3 actions-disabled convention but at the BUTTON level not the menu level since invites only have one action), pagination footer `Previous` / `Next` + `Showing X-Y of Z` label, calling `useAdminInvites({page, page_size, status})` from the new hooks file. **Critical:** the table renders `generated_by_user_id` AS the UUID-string (NOT resolved to email — backend doesn't join; future story could surface email but Story 8.6 keeps the panel UUID-string per epics §1828 verbatim "per-row metadata columns (`generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`)" — `generated_by` literal-string IS the FK UUID).

3. **NEW component `apps/web/src/modules/admin/GenerateInviteModal.tsx` (~120-150 LOC)** peer of `ChangeRoleModal.tsx` (modal-as-peer-of-page convention from Story 8.3): `<Dialog>` with `<DialogTitle>` "Generate new invite" + `<DialogDescription>` explaining one-shot link + `<form>` containing TWO controlled fields: (1) `<select>` for `role` with TWO options `member` and `admin` (NO `agent` option — backend rejects agent at the schema layer per `admin_schemas.py:36-44` `InviteRoleRequestLiteral = Literal["member", "admin"]` verbatim; mirrors `ChangeRoleModal` agent-disabled convention), (2) `<select>` for `ttl_preset` with FOUR options matching `InviteTTLPresetNameLiteral` from `admin_schemas.py:31` verbatim: `ONE_DAY` / `THREE_DAYS` / `SEVEN_DAYS` / `THIRTY_DAYS` (default `SEVEN_DAYS`). The modal does NOT expose the `ttl_seconds` custom-int field (operational radio-button choice per Decision B verbatim "TTL preset enum keeps the admin panel form a finite radio-button choice"; the `ttl_seconds` custom field is reserved for backend-direct invocation in operational edge cases, NOT panel-UX). Form submit dispatches `useGenerateInvite()` mutation; on success closes the modal AND opens the NEW `<InviteTokenDisplayModal>` with `{registration_url, token, role, ttl_seconds, expires_at}` from the 201 response. Mirrors Story 8.5's `ConfirmDialog` → `ResetLinkDisplayModal` 2-step flow but compressed to `GenerateInviteModal` (form) → `InviteTokenDisplayModal` (display) since the generate flow has form input (the password-reset has none).

4. **NEW component `apps/web/src/modules/admin/InviteTokenDisplayModal.tsx` (~80 LOC)** peer of `ResetLinkDisplayModal.tsx` (Story 8.5 convention continues for cleartext-token-once UX). `<Dialog>` with title "Invite generated for {role} role" + body text "This invite link will be valid until {expires_at}. The cleartext token is shown ONLY ONCE — copy it now and deliver it out-of-band to the recipient (SMS, Messenger, personal mail). If you close this modal without copying, you must generate a fresh invite.", a read-only `<Input>` with the `registration_url` value + clipboard-copy `<Button>` via `navigator.clipboard.writeText(absoluteUrl)` + `<Button>` "Done" closing the modal. **Critical:** `absoluteUrl` is computed via `new URL(registration_url, window.location.origin).toString()` mirroring the Story 8.5 P2 fix-up at `ResetLinkDisplayModal.tsx:45-51` verbatim — backend returns relative path (`/register?token=...`), out-of-band delivery needs an absolute URL with origin so the recipient can paste-and-open without manual prefix.

5. **NEW hooks file `apps/web/src/modules/admin/hooks/useAdminInvites.ts` (~140-160 LOC)** peer of `hooks/useAdminUsers.ts`. Exports THREE hooks:
   - `useAdminInvites({page, page_size, status?})` — `useQuery<AdminInvitesListResponse>` with `queryKey: ["admin", "invites", {page, page_size, status}]` calling `api<AdminInvitesListResponse>("/admin/invites?" + qs)`, `staleTime: 30 * 1000` (mirrors `useAdminUsers` line 35 verbatim).
   - `useGenerateInvite()` — `useMutation<GenerateInviteResponse, ApiError, GenerateInviteRequest>` calling `api<GenerateInviteResponse>("/admin/invites", {method: "POST", body: JSON.stringify(body)})`. `onSuccess` invalidates `["admin", "invites"]` query subtree so the list reflects the new row immediately.
   - `useRevokeInvite()` — `useMutation<void, ApiError, string>` (variable = invite_id UUID string) calling `api<void>("/admin/invites/${invite_id}/revoke", {method: "POST"})`. `onSuccess` invalidates `["admin", "invites"]` query subtree so the row visibly transitions to `revoked` status without manual refresh.

6. **MODIFIED `apps/web/src/modules/admin/AdminTabs.tsx`** — REPLACE the `<span aria-disabled="true" ...>` placeholder (lines 31-44) with a `<Link to="/admin/invites" ...>` mirroring the Users-tab block (lines 18-30) verbatim. The new shape is a structural copy-paste with `to="/admin/invites"` / `activeTab === "invites"` predicate / `t("admin.tabs.invites")` label. **Critical:** the `title={t("admin.tabs.invites_coming_soon")}` attribute is REMOVED entirely (the key is also removed from both locale files per T13). The `cursor-not-allowed` / `opacity-50` Tailwind classes are REMOVED. The tab becomes structurally identical to the Users tab.

7. **MODIFIED `apps/web/src/lib/api-types.ts`** — APPEND new types in a NEW `// --- Admin invites (Story 8.6) ---` section AFTER the Story 8.5 `PasswordResetMintResponse` block (around line 241):
   ```ts
   // --- Admin invites (Story 8.6) ---

   export type InviteStatus = "active" | "used" | "expired" | "revoked";
   export type InviteTTLPreset = "ONE_DAY" | "THREE_DAYS" | "SEVEN_DAYS" | "THIRTY_DAYS";
   export type InviteRoleRequest = "member" | "admin";

   export interface AdminInviteRow {
     invite_id: string;
     role: Role;
     ttl_seconds: number;
     generated_by_user_id: string | null;
     generated_at: string;
     expires_at: string;
     used_by_user_id: string | null;
     used_at: string | null;
     used_from_ip: string | null;
     revoked_at: string | null;
     status: InviteStatus;
   }

   export interface AdminInvitesListResponse {
     total: number;
     items: AdminInviteRow[];
     page: number;
     page_size: number;
   }

   export interface GenerateInviteRequest {
     role: InviteRoleRequest;
     ttl_preset?: InviteTTLPreset;
     ttl_seconds?: number;
   }

   export interface GenerateInviteResponse {
     invite_id: string;
     token: string;
     registration_url: string;
     role: Role;
     ttl_seconds: number;
     expires_at: string;
   }
   ```
   **Critical:** field names match the backend `InviteListItem` + `GenerateInviteResponse` Pydantic models from `apps/api/app/modules/invite/admin_schemas.py:53-83` 1:1; `generated_by_user_id` is `string | null` (FK can be null if the original admin row is soft-deleted in the future — DB schema allows it per `invite_tokens.generated_by_user_id NOT NULL FK` but Decision I §1622 binds deactivation not deletion, so null is currently impossible but the TS type stays defensive). The `GenerateInviteRequest.ttl_preset` AND `ttl_seconds` are both optional at the TS level (matches Pydantic optional defaults), but the BACKEND enforces exactly-one via `@model_validator(mode="after")` at `admin_schemas.py:40-44` — the frontend modal in T3 always supplies `ttl_preset` (NEVER `ttl_seconds`), so a malformed `{role: "member"}` payload cannot escape the modal in practice; the TS optionality is preserved for completeness.

8. **NEW vitest test file `apps/web/src/modules/admin/InvitesPage.test.tsx` (~250-300 LOC)** with 9 named tests I1-I9 binding AC-3:
   - **I1** — `renders empty state` (stubs `useAdminInvites` returning empty items, asserts `t("admin.invites.empty")` text visible)
   - **I2** — `renders 4 rows with mixed statuses + status badges` (stubs 4 rows one per status; asserts table rendering + Revoke button visibility predicate — visible for `active` only)
   - **I3** — `clicking status filter dispatches navigate with status search param` (asserts URL changes to `?status=used`)
   - **I4** — `clicking Generate button opens GenerateInviteModal` (asserts modal renders)
   - **I5** — `submitting GenerateInviteModal calls useGenerateInvite mutation and opens InviteTokenDisplayModal on success` (asserts mutation called with `{role: "member", ttl_preset: "SEVEN_DAYS"}`, then token modal renders with registration_url)
   - **I6** — `clicking Revoke on an active row opens ConfirmDialog` (asserts confirm dialog renders)
   - **I7** — `confirming revoke dispatches useRevokeInvite mutation` (asserts mutation called with the row's invite_id)
   - **I8** — `revoke 409 error renders "invite_already_resolved" inline error` (mocks 409 ApiError; asserts error banner)
   - **I9** — `revoke 404 error renders "invite_not_found" inline error` (mocks 404 ApiError; asserts error banner)

   ALL test cases use `afterEach(cleanup)` registration (apps/web vitest globals=false convention per project-context.md line 115; the global setupFiles fix from 2026-05-10 commit a026e97 covers this — registering manually is now redundant but harmless; new test files should add the registration anyway for defensive coding until the project-context.md note is retired).

9. **NEW vitest test file `apps/web/src/modules/admin/GenerateInviteModal.test.tsx` (~80 LOC)** with 3 named tests G1-G3:
   - **G1** — `renders role select with only member + admin options (NO agent option)` (asserts `<option value="agent">` absent — backend mirror)
   - **G2** — `renders ttl_preset select with 4 options defaulting to SEVEN_DAYS`
   - **G3** — `onConfirm dispatches role + ttl_preset to callback` (asserts the callback receives `{role: "admin", ttl_preset: "ONE_DAY"}` after user changes both selects)

10. **NEW vitest test file `apps/web/src/modules/admin/InviteTokenDisplayModal.test.tsx` (~80 LOC)** with 3 named tests IT1-IT3 mirroring `ResetLinkDisplayModal.test.tsx` 1:1:
    - **IT1** — `renders registration_url as readonly input + copy button + done button`
    - **IT2** — `clicking copy button calls navigator.clipboard.writeText with absolute URL` (mocks `window.location.origin = "https://3d.example"` → asserts the writeText arg is `https://3d.example/register?token=<token>`)
    - **IT3** — `clicking done button calls onOpenChange(false)`

11. **NEW Playwright spec `apps/web/tests/visual/admin-invites.spec.ts` (~200 LOC)** mirroring `admin-users.spec.ts` shape with 4 baseline screenshots × 4 projects (desktop-light/desktop-dark/mobile-light/mobile-dark) = 16 NEW PNGs first commit:
    - **Test 1** — `empty state matches baseline` → `admin-invites-empty.png` (stubs `GET /api/admin/invites` returning `{total:0, items:[], page:1, page_size:50}`)
    - **Test 2** — `mixed-status state matches baseline` → `admin-invites-mixed-status.png` (stubs 4 rows one per status: active/used/expired/revoked, with realistic timestamps)
    - **Test 3** — `generate-modal-open state matches baseline` → `admin-invites-generate-modal-open.png` (loads page → clicks "Generate invite" button → asserts modal visible → takes screenshot)
    - **Test 4** — `revoke-confirm state matches baseline` → `admin-invites-revoke-confirm.png` (loads page with one active row → clicks Revoke → asserts ConfirmDialog visible → takes screenshot)

    Use the `stubAdminUsersPage` pattern from `admin-users.spec.ts:40-80` verbatim, adapted as `stubAdminInvitesPage(page, payload?)`. Stub the `**/api/auth/me` admin response identically (lines 41-52 verbatim).

12. **MODIFIED `apps/web/tests/visual/admin-users.spec.ts`** — UPDATE the "AdminTabs disabled-state regression guard" test block (lines 156-166): the existing assertion `await expect(invitesTab).toHaveAttribute("aria-disabled", "true")` IS THE NEGATIVE-OF-THE-STORY contract — Story 8.6's job is to flip the tab from disabled to active. Update the test to: (a) RENAME the describe block to `"AdminTabs active-state regression guard"`, (b) replace the assertion with `await expect(invitesTab).toBeEnabled()` AND `await expect(invitesTab).toHaveAttribute("href", "/admin/invites")` to verify the tab is now a routable link. **Critical:** the original test was a forward-guard for Story 8.6 specifically (the per-story note says "until Story 8.6"); replacing it with the active-state check is the binding contract update, NOT test deletion.

13. **MODIFIED `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`** — APPLY THREE distinct edits per locale (6 edits total):
    - (a) DELETE the `admin.tabs.invites_coming_soon` key (line 110 in both files) — the placeholder is gone after T6.
    - (b) UPDATE the `admin.users.description` line (line 112 in both files) — the existing "Per-user actions ship in the next story." trailing sentence is stale (8.3 shipped them). Update to a forward-looking sentence: en `"All registered users. Sort by any header, filter by email, paginate. Per-user actions live in the row kebab menu."`; pl `"Wszyscy zarejestrowani użytkownicy. Sortuj po nagłówku, filtruj po e-mailu, paginuj. Akcje per-użytkownik są dostępne w menu kontekstowym wiersza."` — defensible micro-hygiene because the Invites tab now exists and a stale Users-tab description undermines the cross-tab UX. (If Codex flags this as scope creep, revert in fix-up; the story still ships.)
    - (c) APPEND NEW `admin.invites.*` namespace section AFTER the Story 8.5 `admin.users.reset_link.*` block (around line 171). Approximately 50 new keys × 2 locales = ~100 new key additions. Required keys:
      ```
      admin.invites.title                          "Invites" / "Zaproszenia"
      admin.invites.description                    short page subtitle
      admin.invites.empty                          "No invites match this filter."
      admin.invites.error_loading                  "Could not load invites. Refresh the page or check the API."
      admin.invites.filter_label                   "Status"
      admin.invites.filter_all                     "All"
      admin.invites.filter_active                  "Active"
      admin.invites.filter_used                    "Used"
      admin.invites.filter_expired                 "Expired"
      admin.invites.filter_revoked                 "Revoked"
      admin.invites.page_size_label                "Rows per page"
      admin.invites.pagination_label               "Showing {{first}}–{{last}} of {{total}}"
      admin.invites.pagination_previous            "Previous"
      admin.invites.pagination_next                "Next"
      admin.invites.column_role                    "Role"
      admin.invites.column_generated_by            "Generated by"
      admin.invites.column_generated_at            "Generated at"
      admin.invites.column_expires_at              "Expires at"
      admin.invites.column_used_by                 "Used by"
      admin.invites.column_used_at                 "Used at"
      admin.invites.column_used_from_ip            "Used from IP"
      admin.invites.column_revoked_at              "Revoked at"
      admin.invites.column_status                  "Status"
      admin.invites.column_actions                 "Actions"
      admin.invites.status.active                  "Active"
      admin.invites.status.used                    "Used"
      admin.invites.status.expired                 "Expired"
      admin.invites.status.revoked                 "Revoked"
      admin.invites.actions.generate               "Generate invite"
      admin.invites.actions.revoke                 "Revoke"
      admin.invites.confirm.revoke_title           "Revoke invite for {{role}} role?"
      admin.invites.confirm.revoke_description     "This invite link will become immediately unusable. Already-consumed registrations are not affected."
      admin.invites.errors.invite_not_found        "Invite not found. The list may be out of date — refresh and try again."
      admin.invites.errors.invite_already_resolved "This invite is already used or revoked."
      admin.invites.errors.generic                 "Action failed. Try again or check the API logs."
      admin.invites.generate.title                 "Generate new invite"
      admin.invites.generate.description           "Mint a single-use invite link for a new member or admin account. The cleartext token is shown ONLY ONCE."
      admin.invites.generate.role_label            "Role"
      admin.invites.generate.role_member           "Member"
      admin.invites.generate.role_admin            "Admin"
      admin.invites.generate.ttl_label             "Validity"
      admin.invites.generate.ttl_one_day           "1 day"
      admin.invites.generate.ttl_three_days        "3 days"
      admin.invites.generate.ttl_seven_days        "7 days"
      admin.invites.generate.ttl_thirty_days       "30 days"
      admin.invites.token_modal.title              "Invite generated for {{role}} role"
      admin.invites.token_modal.body               "This invite link will be valid until {{expires_at}}. Copy it now and deliver it out-of-band. If you close this modal without copying, you must generate a fresh invite."
      admin.invites.token_modal.copy_button        "Copy link"
      admin.invites.token_modal.copied_label       "Copied"
      admin.invites.token_modal.done_button        "Done"
      ```
    - Polish translations carry diacritics per global directive (Zaproszenia/Wystaw zaproszenie/Odwołaj/Aktywne/Wykorzystane/Wygasłe/Odwołane/Wygenerowany przez/Wygenerowano/Wygasa/etc.).

14. **`apps/web/tests/visual/admin-users.spec.ts` baseline regeneration impact** — the AdminTabs change in T6 transitions the Invites tab from disabled-greyed (`opacity-50 cursor-not-allowed text-muted-foreground`) to active-link styling (matches Users tab). This is a structural style change in the AdminTabs strip rendered on EVERY admin page, so the 3 admin-users baseline PNGs (`admin-users-empty.png` / `admin-users-one-row.png` / `admin-users-many-rows.png`) × 4 projects = 12 PNGs MUST be regenerated. Run `npm run test:visual -- --update-snapshots admin-users` ONCE at dev time and commit the regenerated PNGs alongside the source code per Story 8.2 §419 consecutive-stories-own-consecutive-baselines convention. Commit message MUST include the `baseline-reviewed:` sign-off line per project-context.md §245 verbatim ("Baseline Acceptance Gate") for each regenerated PNG: 12 sign-off lines for admin-users + 16 sign-off lines for admin-invites = 28 total.

so that:

- **FR5-ADMIN-1 is fully realized.** PRD §1487 binds "Two admin tabs `/admin/users` + `/admin/invites` with paginated lists and documented column sets". Stories 8.2 + 8.6 ship the two tabs respectively; after Story 8.6 merges, the Invites tab is no longer a `<span aria-disabled>` placeholder but a functional `<Link to="/admin/invites">` route. The Decisions A + B column set (`role`, `generated_by`, `generated_at`, `ttl_seconds`/`expires_at`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`, computed `status`) is surfaced verbatim in the table.

- **FR5-INVITE-2 (UI surface) is fully realized.** The Story 6.3 `GET /api/admin/invites?status=...&page=...&page_size=...` endpoint is wired into the UI with the 5-option status filter dropdown (all/active/used/expired/revoked) + per-row metadata display. The UI never surfaces the cleartext `token` field from the list response (Decision B hygiene — backend already omits it, the UI doesn't accidentally re-render it).

- **FR5-INVITE-3 (UI surface) is fully realized.** The per-row "Revoke" button (visible only for `status === "active"`) calls Story 6.3's `POST /api/admin/invites/{id}/revoke` endpoint with optimistic-style refetch (the `onSuccess` invalidation makes the row visibly transition to `revoked` status post-confirm without manual refresh). A revoked invite token immediately returns HTTP 410 from `/register?token=<token>` (verified end-to-end through Story 6.4's public consume endpoint — Story 8.6 does NOT re-verify this, the Story 6.3 + 6.4 test suite already binds it).

- **Epic 8 acceptance gate is unblocked.** Epics §1741 verbatim binds: "All four brief-defined routine operator actions exercised via the panel UI on `.190`: generate invite (via E6 Story 6.3 endpoint surfaced via Invites tab in 8.6), revoke invite (via 8.6 panel button), change user role (via 8.3), reset user password (via 8.5)." After Story 8.6 ships, all four panel paths exist; the operator can verify Epic 8 closure by executing the four actions on `.190` and confirming audit-log rows appear with correct `actor_user_id` / `target_user_id` shape. Story 8.6 closes Epic 8 — `epic-8-retrospective: optional` per `sprint-status.yaml:171`.

- **The cleartext-token-once UX from Story 8.5 extends naturally to the new modal.** The `InviteTokenDisplayModal` mirrors `ResetLinkDisplayModal` structurally (`<Dialog>` + readonly `<Input>` + clipboard copy + Done button + absolute-URL resolution via `new URL(path, window.location.origin).toString()`). The two modals are sibling implementations of the same "cleartext-token surfaces ONCE" pattern — Story 8.5 introduced the pattern (Story 6.3 specifically deferred the UI to 8.6 per epics §1828 verbatim "matches Decision B 'cleartext token surfaces ONCE' property"), Story 8.6 reuses it. The two modals could in principle be merged into one generic `<TokenDisplayModal>` — explicitly DEFERRED to a future refactor story (see § "Strictly out of scope" below).

- **Story 8.3 + 8.4 + 8.5 enforcement gates stay intact.** Story 8.6 does NOT touch `UsersPage.tsx`, does NOT touch `ChangeRoleModal.tsx`, does NOT touch `ResetLinkDisplayModal.tsx`, does NOT touch `hooks/useAdminUsers.ts`, does NOT touch any backend file in `apps/api/`. The only `apps/web/src/modules/admin/` files modified or added are: AdminTabs.tsx (T6 edit), InvitesPage.tsx (NEW), GenerateInviteModal.tsx (NEW), InviteTokenDisplayModal.tsx (NEW), hooks/useAdminInvites.ts (NEW), InvitesPage.test.tsx (NEW), GenerateInviteModal.test.tsx (NEW), InviteTokenDisplayModal.test.tsx (NEW). The `admin-users.spec.ts` change in T12 is a test-file update, NOT a source-code change to Users page. The 12 admin-users baseline PNG regenerations in T14 are visual-side-effect of the AdminTabs change, NOT a Users-page logic change.

### Story scope is strictly bounded

- **NEW files (~9):**
  - `apps/web/src/routes/admin/invites.tsx`
  - `apps/web/src/modules/admin/InvitesPage.tsx`
  - `apps/web/src/modules/admin/InvitesPage.test.tsx`
  - `apps/web/src/modules/admin/GenerateInviteModal.tsx`
  - `apps/web/src/modules/admin/GenerateInviteModal.test.tsx`
  - `apps/web/src/modules/admin/InviteTokenDisplayModal.tsx`
  - `apps/web/src/modules/admin/InviteTokenDisplayModal.test.tsx`
  - `apps/web/src/modules/admin/hooks/useAdminInvites.ts`
  - `apps/web/tests/visual/admin-invites.spec.ts`
- **MODIFIED files (~6):**
  - `apps/web/src/modules/admin/AdminTabs.tsx` (replace `<span>` placeholder with `<Link>` per T6).
  - `apps/web/src/lib/api-types.ts` (append `// --- Admin invites (Story 8.6) ---` section).
  - `apps/web/src/locales/en.json` (delete 1 key + update 1 desc + append 27 new keys).
  - `apps/web/src/locales/pl.json` (same as en.json with Polish strings).
  - `apps/web/tests/visual/admin-users.spec.ts` (update AdminTabs disabled-state test from "disabled regression guard" to "active-state regression guard" per T12).
  - `apps/web/src/routeTree.gen.ts` — auto-regenerated by `npm run generate:routes` after adding `routes/admin/invites.tsx` (the regeneration is a side-effect, NOT a hand-edit; commit the regenerated file alongside source).
- **REGENERATED baselines (12 admin-users PNGs):**
  - `apps/web/tests/visual/__snapshots__/admin-users-empty-*.png` × 4 projects
  - `apps/web/tests/visual/__snapshots__/admin-users-one-row-*.png` × 4 projects
  - `apps/web/tests/visual/__snapshots__/admin-users-many-rows-*.png` × 4 projects
- **NEW baselines (16 admin-invites PNGs):**
  - `apps/web/tests/visual/__snapshots__/admin-invites-empty-*.png` × 4 projects
  - `apps/web/tests/visual/__snapshots__/admin-invites-mixed-status-*.png` × 4 projects
  - `apps/web/tests/visual/__snapshots__/admin-invites-generate-modal-open-*.png` × 4 projects
  - `apps/web/tests/visual/__snapshots__/admin-invites-revoke-confirm-*.png` × 4 projects
- **STRICTLY OUT OF SCOPE** (these belong to later stories and pollute the diff if added here):
  - **Backend changes of any kind** — Story 8.6 is a UI-only story on top of the already-shipped Story 6.3 endpoints. ZERO file changes under `apps/api/`. ZERO changes to `infra/`. The audit-action names `auth.invite.generated` + `auth.invite.revoked` are already registered + emitted by Story 6.3; no audit-registry edits.
  - **`generated_by` / `used_by` email-resolution in the panel** — backend returns FK UUID strings; the panel displays UUIDs verbatim. Joining `users` table to surface emails is a NICE-TO-HAVE deferred to a future Epic 8.x or Epic 10.x retrofit (would need either a backend JOIN response shape change OR a frontend N+1 query against `/api/admin/users` per row). Out of scope for the closing Epic 8 story; the operator's intra-panel context (admin emails from /admin/users) is enough to recognize own-issued vs other-admin-issued invites by UUID.
  - **Custom `ttl_seconds` input on the GenerateInviteModal** — only the 4 preset radio choices are exposed. The Story 6.3 backend accepts `ttl_seconds` as an optional alternative to `ttl_preset`, but Decision B verbatim states "TTL preset enum keeps the admin panel form a finite radio-button choice + one custom-input fallback (matches brief working assumption)". The custom-input fallback is reserved for backend-direct curl invocations in operational edge cases, NOT panel UX. If a future operator workflow needs e.g. "10 minute" or "90 day" invites from the panel, a follow-up Epic 10.x story can add the custom-input toggle.
  - **Optimistic UI updates** — both `useGenerateInvite` and `useRevokeInvite` use the simple `invalidateQueries` pattern (refetch on success), NOT React Query optimistic-update with rollback. The admin panel is single-operator banking-IT, refetch latency is acceptable, and rollback complexity has no payoff.
  - **Generic `<TokenDisplayModal>` refactor** — `ResetLinkDisplayModal` + `InviteTokenDisplayModal` are sibling implementations of the same pattern. Merging them into one generic `<TokenDisplayModal>` is a 30-LOC refactor savings that would invalidate Story 8.5's baseline + tests. DEFER until a third token-once modal arrives (audit-log export download token? OAuth client-secret display?). Per project-context.md feedback `feedback_preexisting_issue_threshold.md` the threshold for refactor candidacy is 3 instances.
  - **Pagination beyond page 1 visual baseline** — the 4 baselines cover empty / mixed-status (page 1 with 4 rows) / generate-modal-open / revoke-confirm. A "page 2 + sort" baseline is operational drift from "every UI state needs a baseline"; the underlying pagination logic is the same Vitest-tested + Story 8.2-precedent code path.
  - **Search-by-email on invites** — the Story 6.3 backend list endpoint does NOT support search (only status filter + pagination). Adding search would require a backend extension (filter by `generated_by_user_id` or by `used_by_user_id` email-join), which is a Story 6.x or Epic 10.x backend change. DEFER unless operator explicitly requests in retro.
  - **Sortable columns** — the Story 6.3 backend returns `generated_at DESC` ordering only; no client-side sort. Adding column sort would require backend `sort_by` query param. DEFER (mirrors the rationale of "search-by-email" — backend-side feature, not Story 8.6).
  - **"Resend invite" action** — backend has no `/resend` endpoint; the operator's resend flow is "revoke old + generate new + deliver new URL out-of-band". DEFER as a UX improvement until operator post-mortem flags it.
  - **Bulk operations** (FR5-ADMIN-4 deliberate-exclusion enforced via Stories 8.2 + 8.3 negative ACs; Story 8.6 inherits the absence — no bulk-select checkboxes, no bulk-revoke button).
  - **AdminTabs third tab for audit log** — `/admin/audit` exists at the backend (`GET /api/admin/audit`) and has a Story 6.3-era CLI shape, but no admin tab. DEFER to a future story when audit-log panel UX is in scope.
  - **i18n string `admin.users.description` adjustment in T13(b)** — if Codex review flags the description tweak as scope creep, the fix-up is to revert that one-line change without affecting the rest of Story 8.6.

No new Alembic migration. No backend endpoint changes. No new audit action name (the 2 emissions from Story 6.3 — `auth.invite.generated` + `auth.invite.revoked` — are already registered in `app/core/audit.py:17` and emitted by Story 6.3). No new entity_type. No new rate-limit scope. No new env-var. No new middleware. No change to `apps/api/app/main.py`. No change to `apps/api/app/router.py`. No change to Story 8.1 `LastActiveMiddleware`. No change to Story 8.2 Users list endpoint. No change to Story 8.3 PATCH/force-logout endpoints. No change to Story 8.4 force-enroll/force-disable endpoints. No change to Story 8.5 password-reset endpoints. No change to Story 6.3 admin invite endpoints (Story 8.6 CONSUMES them). No change to Story 6.4 public `/register?token=` flow.

## Acceptance Criteria

**AC-1 — NEW `apps/web/src/routes/admin/invites.tsx` route ships + routeTree regenerated + `/admin/invites` reachable for admin role.**

- Given the current Init 5 frontend layout (TanStack Router file-based routes; `apps/web/src/routes/admin/users.tsx` exists; `routeTree.gen.ts` covers `/admin/users` but NOT `/admin/invites`),
- When Story 8.6 ships,
- Then `apps/web/src/routes/admin/invites.tsx` MUST exist with the same shape as `apps/web/src/routes/admin/users.tsx:1-57`: `createFileRoute("/admin/invites")` + `<AuthGate>` wrapper + `<Navigate to="/" replace />` redirect when `!isAdmin && !isLoading` + `validateSearch` accepting `{page?: number, page_size?: number, status?: "active"|"used"|"expired"|"revoked"}`.
- And `apps/web/src/routeTree.gen.ts` MUST contain an `AdminInvitesRouteImport` entry parallel to the existing `AdminUsersRouteImport` (line 25); a `'/admin/invites'` path entry parallel to lines 93-94 + 103 + 119 + 136 + 154 + 170 + 186 + 308-311.
- And `cd apps/web && npm run generate:routes` MUST succeed (regeneration of `routeTree.gen.ts` is the binding step; manual hand-editing of the .gen.ts file is FORBIDDEN per ESLint ignore rule `**/*.gen.ts`).
- And `cd apps/web && npm run typecheck` MUST exit 0.
- And navigating to `/admin/invites` while authenticated as admin MUST render `<InvitesPage />`; navigating while authenticated as member MUST redirect to `/` (mirrors the AC for `/admin/users` from Story 8.2); navigating while anonymous MUST trigger the `<AuthGate>` redirect to `/login` per the standard AuthGate contract.

**AC-2 — `InvitesPage.tsx` renders `<AdminTabs activeTab="invites">` + status filter + pagination + 10-column table + Generate button + Revoke buttons gated by `status === "active"`.**

- Given the `useAdminInvites` hook returns a successful response with N items,
- When `<InvitesPage />` renders,
- Then the page MUST render `<AdminTabs activeTab="invites" />` (with the Invites tab visually selected; the AdminTabs source change from T6 makes the tab routable).
- And the page MUST render a header with `t("admin.invites.title")` + `t("admin.invites.description")`.
- And the page MUST render a `<select>` for status filter with 5 options (all/active/used/expired/revoked) and a `<select>` for page size with 4 options (25/50/100/200) — when value changes, dispatches `navigate({to: "/admin/invites", search: ({...prev, status, page_size, page: 1})})` (mirrors `UsersPage.tsx:217-238` verbatim shape).
- And the page MUST render a "Generate invite" button (top-right of the controls row); clicking it opens `<GenerateInviteModal>`.
- And the page MUST render a `<table>` with 9 columns: Role / Generated by / Generated at / Expires at / Used by / Used at / Used from IP / Revoked at / Status / Actions (column 10 = Actions — total 10 columns). Each column header reads from the `admin.invites.column_*` i18n keys.
- And each row's Status cell MUST render the i18n string `admin.invites.status.{status}` with a visual badge style differentiated per status (active = subtle green/`bg-success/10`, used = neutral/`bg-muted`, expired = warning/`bg-warning/10`, revoked = destructive/`bg-destructive/10` — Tailwind utility classes from `theme.css` token set; no inline hex colors per project-context.md §47 verbatim).
- And each row's Actions cell MUST render a "Revoke" button visible AND enabled ONLY when `row.status === "active"`; for the 3 non-active statuses the cell renders `—` (em-dash) OR the button is rendered as `aria-disabled="true"` + greyed-out (developer discretion per UX micro-decision; both are AC-acceptable).
- And the page MUST render the pagination footer with `Previous` / `Next` buttons disabled appropriately + `t("admin.invites.pagination_label", {first, last, total})` text (mirrors `UsersPage.tsx:532-554`).
- And the page MUST render an `errorCode` banner ABOVE the table when an error code is set (uses the `admin.invites.errors.{code}` translation; mirrors `UsersPage.tsx:281-285` shape).
- And the `useAdminInvites` query MUST be keyed `["admin", "invites", {page, page_size, status}]` (verifiable via React Query Devtools or by mocking the hook in vitest).

**AC-3 — Vitest tests I1-I9 + G1-G3 + IT1-IT3 PASS in isolation AND together.**

- Given the test files from T8-T10 are authored with the 15 named tests,
- When `cd apps/web && npm run test -- --run InvitesPage GenerateInviteModal InviteTokenDisplayModal` is executed,
- Then ALL 15 tests MUST PASS (9 InvitesPage + 3 GenerateInviteModal + 3 InviteTokenDisplayModal).
- And `cd apps/web && npm run test -- --run` (full vitest suite) MUST PASS with target count ~383 (368 baseline from Story 8.5 close-out + 9 InvitesPage + 3 GenerateInviteModal + 3 InviteTokenDisplayModal = 383).
- And ZERO tests in the existing `apps/web/src/modules/admin/UsersPage.test.tsx`, `ChangeRoleModal.test.tsx`, `ResetLinkDisplayModal.test.tsx` are touched or regressed (Stories 8.3 + 8.4 + 8.5 regression guards stay green).

**AC-4 — `GenerateInviteModal` rejects `agent` role at the UI layer (mirrors backend `InviteRoleRequestLiteral` Literal["member", "admin"]).**

- Given the `<GenerateInviteModal>` is rendered with `open={true}`,
- When the user inspects the role `<select>`,
- Then EXACTLY TWO options MUST be present: `value="member"` + `value="admin"`. NO `value="agent"` option (vitest test G1 verifies via `assert screen.queryByRole("option", {name: /agent/i}) === null`).
- And the default selected option MUST be `member` (UX-rational: members are the dominant invite use case per brief Initiative 5 personas; admin invites are rare).
- And selecting role + ttl_preset + clicking confirm MUST dispatch `onConfirm({role, ttl_preset})` with the selected values (G3 verifies).
- And the `<select>` for `ttl_preset` MUST have EXACTLY 4 options matching `InviteTTLPresetNameLiteral`: `ONE_DAY` / `THREE_DAYS` / `SEVEN_DAYS` / `THIRTY_DAYS`. NO `ttl_seconds` custom-int input (G2 verifies count is 4).
- And the default selected `ttl_preset` MUST be `SEVEN_DAYS` (operational rationale: 7-day default matches most-common invite delivery latency expectations).

**AC-5 — `InviteTokenDisplayModal` renders absolute URL + clipboard copy works + done-button closes.**

- Given `<InviteTokenDisplayModal>` is rendered with `open={true}`, `registrationUrl="/register?token=abc"`, `expiresAt="2026-05-27T12:00:00Z"`, `role="member"`,
- When the modal renders,
- Then the readonly `<Input>` value MUST be `new URL("/register?token=abc", window.location.origin).toString()` (absolute URL; IT2 verifies via `assert input.value === "https://3d.example/register?token=abc"` with mocked origin).
- And clicking the "Copy link" `<Button>` MUST call `navigator.clipboard.writeText(absoluteUrl)` exactly once (IT2 verifies via `vi.spyOn(navigator.clipboard, "writeText")`).
- And clicking the "Done" `<Button>` MUST call `onOpenChange(false)` exactly once (IT3 verifies).
- And the modal MUST NOT call `onOpenChange` automatically on mount or on copy (the operator explicitly clicks Done to dismiss — protects against accidental dismissal that would lose the cleartext token).

**AC-6 — `useAdminInvites` / `useGenerateInvite` / `useRevokeInvite` hooks wire the Story 6.3 HTTP contract correctly.**

- Given the new hooks file `apps/web/src/modules/admin/hooks/useAdminInvites.ts`,
- When the hooks are imported and used in the page,
- Then `useAdminInvites({page: 1, page_size: 50, status: "active"})` MUST call `api<AdminInvitesListResponse>("/admin/invites?page=1&page_size=50&status=active")` (HTTP GET via the `api()` wrapper from `@/lib/api` — never raw fetch per project-context.md §48 verbatim).
- And `useGenerateInvite()` mutationFn MUST call `api<GenerateInviteResponse>("/admin/invites", {method: "POST", body: JSON.stringify(body)})` where `body: GenerateInviteRequest`.
- And `useRevokeInvite()` mutationFn MUST call `api<void>("/admin/invites/${invite_id}/revoke", {method: "POST"})` (no body).
- And ALL THREE hooks MUST invalidate the `["admin", "invites"]` query subtree on success (`useGenerateInvite` + `useRevokeInvite` mutate state; `useAdminInvites` is a query so it self-refetches on key change).
- And the `useAdminInvites` query MUST have `staleTime: 30 * 1000` (mirrors `useAdminUsers` line 35 verbatim — 30-second cache window for typical admin browse rhythm).

**AC-7 — AdminTabs flips Invites tab from disabled-placeholder to active-link, mirroring Users-tab styling.**

- Given the current `apps/web/src/modules/admin/AdminTabs.tsx` lines 31-44 render a `<span aria-disabled="true" ... onClick={preventDefault}>` for the Invites tab,
- When Story 8.6 ships,
- Then those lines MUST be REPLACED with a `<Link to="/admin/invites" role="tab" aria-selected={activeTab === "invites"} className={cn(baseTab, activeTab === "invites" ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>` block (structural copy of the Users-tab block at lines 18-30).
- And the `title={t("admin.tabs.invites_coming_soon")}` attribute MUST be GONE.
- And the `aria-disabled="true"` attribute MUST be GONE.
- And the `cursor-not-allowed` + `opacity-50` Tailwind classes MUST be GONE.
- And the `onClick={(e) => e.preventDefault()}` handler MUST be GONE.
- And rendering `<AdminTabs activeTab="users" />` on the Users page MUST show the Invites tab as an enabled `<a href="/admin/invites">` link (not a disabled `<span>`); rendering `<AdminTabs activeTab="invites" />` on the new Invites page MUST show the Invites tab visually selected (`border-primary text-foreground`).

**AC-8 — Playwright spec `admin-invites.spec.ts` ships with 4 baselines × 4 projects = 16 PNGs all green.**

- Given the new Playwright spec file from T11,
- When `cd apps/web && npm run test:visual -- admin-invites` is executed for the first time (with `--update-snapshots`),
- Then 16 PNG baselines MUST be generated under `apps/web/tests/visual/__snapshots__/` (4 tests × 4 projects).
- And after baseline generation, re-running `cd apps/web && npm run test:visual -- admin-invites` (WITHOUT `--update-snapshots`) MUST exit 0 (the binding visual-regression contract).
- And the commit landing the 16 PNGs MUST include 16 `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` lines in the message per project-context.md §245 verbatim "Baseline Acceptance Gate" — the pre-commit hook at `apps/web/.husky/pre-commit` REJECTS the commit otherwise via `_check-baseline-review.mjs` (exit 1).

**AC-9 — Story 8.3 + 8.4 + 8.5 admin-users baselines regenerate cleanly with the AdminTabs styling change + Test 5 updates.**

- Given the AdminTabs source change in T6 alters the visual styling of the Invites tab from greyed/disabled to active link,
- When Story 8.6 ships,
- Then 12 PNG baselines MUST be regenerated via `cd apps/web && npm run test:visual -- --update-snapshots admin-users` (3 baseline names × 4 projects).
- And after regeneration, `cd apps/web && npm run test:visual -- admin-users` (WITHOUT `--update-snapshots`) MUST exit 0.
- And the existing 7 Playwright tests in `admin-users.spec.ts` (4 baselines + bulk-negative AC + AdminTabs guard + Story 8.3 4 kebab tests + Story 8.4 2 kebab tests + Story 8.5 Test 10 kebab assertion — total Playwright assertion count from `admin-users.spec.ts` is bigger than 7; the binding count is "every existing test passes post-Story-8.6"; see Story 8.5 `admin-users.spec.ts` for the final inventory).
- And the updated test from T12 (renamed `"AdminTabs active-state regression guard"` block) MUST PASS:
  - `expect(invitesTab).toBeEnabled()` — the Invites tab is now a routable `<a>` link, not a disabled `<span>`.
  - `expect(invitesTab).toHaveAttribute("href", "/admin/invites")` — TanStack Router `<Link to="...">` renders as `<a href="...">`.
- And the commit landing the 12 regenerated PNGs MUST include 12 `baseline-reviewed:` sign-off lines (combined with the 16 new admin-invites lines = 28 sign-off lines in the Story 8.6 commit message).

**AC-10 — i18n keys appended + obsolete key removed + parity between en.json + pl.json.**

- Given the locales files `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` (391 lines each pre-Story-8.6 per `wc -l` baseline),
- When Story 8.6 ships,
- Then `admin.tabs.invites_coming_soon` MUST be REMOVED from both files.
- And the `admin.invites.*` namespace MUST be APPENDED to both files (≥40 new keys per T13(c) inventory).
- And the `admin.users.description` key MUST be UPDATED per T13(b) (en + pl values match the listed Polish/English strings).
- And `cd apps/web && jq -r 'keys[]' src/locales/en.json | sort > /tmp/en.keys && jq -r 'keys[]' src/locales/pl.json | sort > /tmp/pl.keys && diff /tmp/en.keys /tmp/pl.keys` MUST exit 0 (key-set parity invariant from Story 8.3 + 8.4 + 8.5 convention).
- And the Polish translations MUST carry diacritics (Zaproszenia / Wystaw zaproszenie / Odwołaj / Aktywne / Wykorzystane / Wygasłe / Odwołane / Wygenerowany przez / Wygenerowano / Wygasa / etc.) per global directive verbatim.

**AC-11 — Pre-merge grep checklist (17 invariants verified before flipping `review` → `done`).**

The Dev Agent MUST run the following 17 grep-based verifications and confirm ALL pass before flipping `sprint-status.yaml` from `review` → `done`. The grep commands are deterministic + binding; failures must be fixed before merge.

1. **Route file exists:** `test -f apps/web/src/routes/admin/invites.tsx` exit 0.
2. **InvitesPage exists:** `test -f apps/web/src/modules/admin/InvitesPage.tsx` exit 0.
3. **GenerateInviteModal exists:** `test -f apps/web/src/modules/admin/GenerateInviteModal.tsx` exit 0.
4. **InviteTokenDisplayModal exists:** `test -f apps/web/src/modules/admin/InviteTokenDisplayModal.tsx` exit 0.
5. **useAdminInvites hook exists:** `test -f apps/web/src/modules/admin/hooks/useAdminInvites.ts` exit 0.
6. **Visual spec exists:** `test -f apps/web/tests/visual/admin-invites.spec.ts` exit 0.
7. **AdminTabs uses `<Link to="/admin/invites">`:** `grep -q 'to="/admin/invites"' apps/web/src/modules/admin/AdminTabs.tsx` exit 0.
8. **AdminTabs no longer has the `<span aria-disabled` placeholder:** `grep -q 'admin.tabs.invites_coming_soon' apps/web/src/modules/admin/AdminTabs.tsx` exit 1 (negative — key reference gone).
9. **api-types section marker present:** `grep -q '// --- Admin invites (Story 8.6) ---' apps/web/src/lib/api-types.ts` exit 0.
10. **api-types includes `AdminInviteRow`:** `grep -q 'export interface AdminInviteRow' apps/web/src/lib/api-types.ts` exit 0.
11. **i18n keys removed:** `grep -q 'invites_coming_soon' apps/web/src/locales/en.json apps/web/src/locales/pl.json` exit 1 (negative — key gone from both).
12. **i18n keys appended (≥40 per locale):** `grep -c '"admin.invites.' apps/web/src/locales/en.json` returns ≥40; same for pl.json.
13. **Polish diacritics in pl.json (Story 8.6 keys):** `grep 'admin.invites' apps/web/src/locales/pl.json | grep -cE 'ł|ą|ę|ó|ś|ż|ź'` returns ≥5 (multiple keys carry Polish diacritics).
14. **Vitest InvitesPage + GenerateInviteModal + InviteTokenDisplayModal tests pass:** `cd apps/web && npm run test -- --run InvitesPage GenerateInviteModal InviteTokenDisplayModal` exit 0.
15. **TypeScript clean:** `cd apps/web && npm run typecheck` exit 0.
16. **Lint clean (max-warnings=0):** `cd apps/web && npm run lint` exit 0.
17. **routeTree.gen.ts contains AdminInvitesRouteImport:** `grep -q 'AdminInvitesRouteImport' apps/web/src/routeTree.gen.ts` exit 0.

## Tasks / Subtasks

- [ ] **T1 — Author `apps/web/src/lib/api-types.ts` Story 8.6 section (AC-6, AC-10)**
  - [ ] T1.1 Open `apps/web/src/lib/api-types.ts`, locate the Story 8.5 `// --- Password reset (Story 8.5) ---` block ending at line 241.
  - [ ] T1.2 APPEND the new `// --- Admin invites (Story 8.6) ---` section per T7 spec verbatim (10 type/interface declarations).
  - [ ] T1.3 Verify `cd apps/web && npm run typecheck` exits 0.

- [ ] **T2 — Author `apps/web/src/modules/admin/hooks/useAdminInvites.ts` (AC-6)**
  - [ ] T2.1 NEW file mirroring `useAdminUsers.ts:1-37` (the `useAdminUsers` query hook shape) + `useAdminUsers.ts:46-58` (the `useUpdateAdminUser` mutation hook shape) verbatim.
  - [ ] T2.2 Export `UseAdminInvitesParams { page, page_size, status? }` interface, `buildQueryString(params)` helper, `useAdminInvites(params)` query hook, `useGenerateInvite()` mutation hook, `useRevokeInvite()` mutation hook.
  - [ ] T2.3 Run `cd apps/web && npm run typecheck` exit 0.

- [ ] **T3 — Author `apps/web/src/modules/admin/InviteTokenDisplayModal.tsx` (AC-5)**
  - [ ] T3.1 NEW file mirroring `ResetLinkDisplayModal.tsx:1-97` verbatim shape with field renames: `email` → `role`, `resetUrl` → `registrationUrl`, `expiresAt` → `expiresAt` (same), titles + bodies wired via `admin.invites.token_modal.*` i18n keys.
  - [ ] T3.2 Reuse the absolute-URL resolution block (lines 45-51 of ResetLinkDisplayModal verbatim — `new URL(registrationUrl, window.location.origin).toString()` wrapped in try/catch fallback).
  - [ ] T3.3 Reuse the `useState<boolean>(false)` `copied` slot + `handleCopy()` async function (lines 37 + 53-62 of ResetLinkDisplayModal verbatim).

- [ ] **T4 — Author `apps/web/src/modules/admin/InviteTokenDisplayModal.test.tsx` (AC-3)**
  - [ ] T4.1 NEW test file mirroring `ResetLinkDisplayModal.test.tsx:1-69` verbatim shape. Tests IT1-IT3 per T10 spec.
  - [ ] T4.2 Register `afterEach(cleanup)` from `@testing-library/react` per project-context.md §115 verbatim (defensive — global setup file covers it post-2026-05-10).
  - [ ] T4.3 Mock `navigator.clipboard.writeText` via `vi.spyOn(navigator.clipboard, "writeText")` (mirrors Story 8.5 modal test pattern).
  - [ ] T4.4 Run `cd apps/web && npm run test -- --run InviteTokenDisplayModal.test.tsx` exit 0.

- [ ] **T5 — Author `apps/web/src/modules/admin/GenerateInviteModal.tsx` (AC-4)**
  - [ ] T5.1 NEW file mirroring `ChangeRoleModal.tsx:1-102` shape: `<Dialog>` + `<DialogHeader>` + `<DialogContent>` + form body + `<DialogFooter>` Cancel + Confirm buttons.
  - [ ] T5.2 Two `<select>` fields: role (member/admin only — NO agent option, mirrors ChangeRoleModal `<option value="agent" disabled>` precedent but Story 8.6 OMITS the agent option entirely since `InviteRoleRequestLiteral` rejects it at schema level), ttl_preset (4 values defaulting to SEVEN_DAYS).
  - [ ] T5.3 `useState<InviteRoleRequest>("member")` + `useState<InviteTTLPreset>("SEVEN_DAYS")` for controlled state.
  - [ ] T5.4 `onConfirm({role: selectedRole, ttl_preset: selectedTtlPreset})` on Confirm click. Pending state disables both selects + Confirm button.
  - [ ] T5.5 i18n keys per AC-10 inventory.

- [ ] **T6 — Author `apps/web/src/modules/admin/GenerateInviteModal.test.tsx` (AC-3, AC-4)**
  - [ ] T6.1 NEW test file with 3 tests G1-G3 per T9 spec.
  - [ ] T6.2 Register `afterEach(cleanup)`.
  - [ ] T6.3 Run `cd apps/web && npm run test -- --run GenerateInviteModal.test.tsx` exit 0.

- [ ] **T7 — Author `apps/web/src/modules/admin/InvitesPage.tsx` (AC-2)**
  - [ ] T7.1 NEW file mirroring `UsersPage.tsx:79-661` structural shape with adaptations: header → invites title, AdminTabs activeTab → "invites", filter dropdown replaces search input, table columns → 10-column invite shape, single Revoke action per row replaces the multi-item kebab menu.
  - [ ] T7.2 Use `useAdminInvites({page, page_size, status})` query hook.
  - [ ] T7.3 Use `useGenerateInvite()` + `useRevokeInvite()` mutation hooks.
  - [ ] T7.4 `useState<AdminInviteRow | null>` slots for: `confirmRevokeTarget` + `displayedToken` (the post-generate cleartext token + role + expires_at + registration_url tuple).
  - [ ] T7.5 `handleGenerateConfirm({role, ttl_preset})` dispatches `useGenerateInvite.mutate({role, ttl_preset})`; on success closes the generate modal AND sets `displayedToken` (which opens `<InviteTokenDisplayModal>`).
  - [ ] T7.6 `handleRevokeConfirm()` dispatches `useRevokeInvite.mutate(confirmRevokeTarget.id)`; on success closes the confirm dialog.
  - [ ] T7.7 Status-badge rendering per AC-2 (4 color variants via Tailwind utility classes from theme.css; NO inline hex colors).
  - [ ] T7.8 i18n keys per AC-10 inventory.

- [ ] **T8 — Author `apps/web/src/modules/admin/InvitesPage.test.tsx` (AC-3)**
  - [ ] T8.1 NEW test file with 9 tests I1-I9 per T8 spec.
  - [ ] T8.2 Register `afterEach(cleanup)`.
  - [ ] T8.3 Mock `useAdminInvites` / `useGenerateInvite` / `useRevokeInvite` hooks via `vi.mock("@/modules/admin/hooks/useAdminInvites", ...)` (mirrors `UsersPage.test.tsx` hook-mocking pattern; the project's convention is hook-mocking at the module boundary, NOT `fetch`-mocking at the network boundary, because both surfaces are tested separately).
  - [ ] T8.4 Mock `useAuth` (for `useAuth().user?.id` in InvitesPage if needed — InvitesPage does NOT use `useAuth` in the core flow because there's no self/agent guard at the invite-row level, but `<AuthGate>` wrapper in the route still requires it via the route component).
  - [ ] T8.5 Mock `useNavigate` + `useSearch` from `@tanstack/react-router` per `UsersPage.test.tsx` precedent.
  - [ ] T8.6 Run `cd apps/web && npm run test -- --run InvitesPage.test.tsx` exit 0.

- [ ] **T9 — Author `apps/web/src/routes/admin/invites.tsx` (AC-1)**
  - [ ] T9.1 NEW file copying `apps/web/src/routes/admin/users.tsx:1-57` verbatim with the following changes: import `<InvitesPage>` from `@/modules/admin/InvitesPage`, change `validateSearch` interface to `{page?, page_size?, status?: "active"|"used"|"expired"|"revoked"}`, change `createFileRoute("/admin/users")` → `createFileRoute("/admin/invites")`.
  - [ ] T9.2 Run `cd apps/web && npm run generate:routes` to regenerate `routeTree.gen.ts`. Verify the regenerated file contains `AdminInvitesRouteImport` + `'/admin/invites'` path entries parallel to the existing `AdminUsersRouteImport` lines.
  - [ ] T9.3 Commit the regenerated `routeTree.gen.ts` alongside the new `routes/admin/invites.tsx` source.
  - [ ] T9.4 Verify `cd apps/web && npm run typecheck` exits 0.

- [ ] **T10 — Modify `apps/web/src/modules/admin/AdminTabs.tsx` (AC-7)**
  - [ ] T10.1 REPLACE lines 31-44 (`<span aria-disabled="true" ...>` block) with the `<Link>` structural copy from lines 18-30 with `to="/admin/invites"` / `activeTab === "invites"` substitutions.
  - [ ] T10.2 Verify `grep -q 'to="/admin/invites"' apps/web/src/modules/admin/AdminTabs.tsx` exit 0.
  - [ ] T10.3 Verify `grep -q 'admin.tabs.invites_coming_soon' apps/web/src/modules/admin/AdminTabs.tsx` exit 1 (key reference gone).
  - [ ] T10.4 Run `cd apps/web && npm run typecheck` + `npm run lint` exit 0.

- [ ] **T11 — Modify `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` (AC-10)**
  - [ ] T11.1 DELETE the `admin.tabs.invites_coming_soon` key from BOTH files (line 110 in each).
  - [ ] T11.2 UPDATE the `admin.users.description` value in both files per T13(b) (trailing sentence rephrase).
  - [ ] T11.3 APPEND the 27-key `admin.invites.*` namespace block AFTER the existing Story 8.5 `admin.users.reset_link.*` block (around line 171 in both files).
  - [ ] T11.4 Verify `jq -e .` exit 0 on both files (valid JSON syntax).
  - [ ] T11.5 Verify key-set parity: `jq -r 'keys[]' apps/web/src/locales/en.json | sort > /tmp/en && jq -r 'keys[]' apps/web/src/locales/pl.json | sort > /tmp/pl && diff /tmp/en /tmp/pl` exit 0.
  - [ ] T11.6 Verify Polish diacritics present: `grep 'admin.invites' apps/web/src/locales/pl.json | grep -cE 'ł|ą|ę|ó|ś|ż|ź'` returns ≥5.

- [ ] **T12 — Modify `apps/web/tests/visual/admin-users.spec.ts` AdminTabs test (AC-9)**
  - [ ] T12.1 Locate the `test.describe("/admin/users — AdminTabs disabled-state regression guard", ...)` block at lines 156-166.
  - [ ] T12.2 RENAME the describe block string to `"/admin/users — AdminTabs active-state regression guard"`.
  - [ ] T12.3 REPLACE the test body assertion `await expect(invitesTab).toHaveAttribute("aria-disabled", "true")` with TWO assertions: `await expect(invitesTab).toBeEnabled()` AND `await expect(invitesTab).toHaveAttribute("href", "/admin/invites")`.
  - [ ] T12.4 RENAME the test name string from `"Invites tab stays aria-disabled until Story 8.6"` to `"Invites tab is now an active link (Story 8.6 shipped)"`.
  - [ ] T12.5 Run `cd apps/web && npm run test:visual -- admin-users.spec.ts -g "active-state"` exit 0.

- [ ] **T13 — Author `apps/web/tests/visual/admin-invites.spec.ts` (AC-8)**
  - [ ] T13.1 NEW file mirroring `admin-users.spec.ts:1-80` shape (imports + `stubAdminInvitesPage` helper).
  - [ ] T13.2 Implement Test 1 `empty state matches baseline` per T11 spec — stubs empty response, navigates to `/admin/invites`, waits for heading, takes `admin-invites-empty.png` baseline.
  - [ ] T13.3 Implement Test 2 `mixed-status state matches baseline` per T11 spec — stubs 4-item response with distinct statuses, takes `admin-invites-mixed-status.png` baseline.
  - [ ] T13.4 Implement Test 3 `generate-modal-open state matches baseline` per T11 spec — clicks Generate button, waits for modal, takes `admin-invites-generate-modal-open.png` baseline.
  - [ ] T13.5 Implement Test 4 `revoke-confirm state matches baseline` per T11 spec — clicks Revoke on active row, waits for confirm dialog, takes `admin-invites-revoke-confirm.png` baseline.
  - [ ] T13.6 Run `cd apps/web && npm run test:visual -- admin-invites --update-snapshots` ONCE at dev time. Verify 16 PNGs generated under `apps/web/tests/visual/__snapshots__/`.
  - [ ] T13.7 Re-run `cd apps/web && npm run test:visual -- admin-invites` (without `--update-snapshots`) exit 0.

- [ ] **T14 — Regenerate admin-users baselines + capture sign-off lines (AC-9)**
  - [ ] T14.1 Run `cd apps/web && npm run test:visual -- admin-users --update-snapshots` to regenerate 12 PNGs.
  - [ ] T14.2 Inspect the diff for each regenerated PNG to confirm the visual delta is ONLY the AdminTabs styling change (Invites tab transitions from greyed to active). If any other unexpected delta is present (e.g. theme drift), STOP and surface to the operator — do NOT blanket-update.
  - [ ] T14.3 Re-run `cd apps/web && npm run test:visual -- admin-users` (without `--update-snapshots`) exit 0.
  - [ ] T14.4 Prepare the `baseline-reviewed:` sign-off lines for the commit message: 12 lines for admin-users + 16 lines for admin-invites = 28 lines total. Format per project-context.md §245: `baseline-reviewed: admin-invites-empty-desktop-light.png, Ezop, 2026-05-21` etc.

- [ ] **T15 — Pre-merge grep checklist (AC-11)**
  - [ ] T15.1 Run all 17 grep-based verifications from AC-11. Document each command + expected exit code in the Dev Agent Record.
  - [ ] T15.2 Fix any failure before flipping `sprint-status.yaml` from `ready-for-dev` → `review`.

- [ ] **T16 — Quality gate + status flip + deploy (all ACs)**
  - [ ] T16.1 Run `cd apps/web && npm run typecheck` exit 0.
  - [ ] T16.2 Run `cd apps/web && npm run lint` exit 0 (max-warnings=0 per project-context.md §128).
  - [ ] T16.3 Run `cd apps/web && npm run test -- --run` exit 0 (full vitest suite; target count ~383).
  - [ ] T16.4 Run `cd apps/web && npm run test:visual` exit 0 (full Playwright suite; the 4-project matrix is automatic).
  - [ ] T16.5 Run `infra/scripts/check-all.sh` from repo root — all 13 stages green.
  - [ ] T16.6 Stage all changed files; commit with subject `feat(web): admin Invites tab — list + status filter + generate + revoke UI (Story 8.6)` + body listing the new files + the 28 `baseline-reviewed:` sign-off lines + the `Co-Authored-By:` trailer per global git convention.
  - [ ] T16.7 Push the dev commit; flip `sprint-status.yaml` `8-6-admin-invites-tab-status-filter-ui: backlog` → `review` with a session note documenting the commit SHA + test counts + AC-11 checklist results.
  - [ ] T16.8 Trigger Codex review via `codex review --commit <SHA>` per `feedback_invoke_codex_directly.md`. Wait for verdict; address P1/P2 fix-ups in follow-up commits before flipping `review` → `done`.
  - [ ] T16.9 After `done` flip, run `infra/scripts/deploy.sh` per `feedback_auto_deploy_dev` to deploy to `.190`.
  - [ ] T16.10 Post-deploy real-world verification on `.190`: navigate to `https://3d.ezop.ddns.net/admin/invites` → confirm tab loads, list renders, generate flow produces a registration URL, revoke flow transitions a row to revoked status (acceptance gate from epics §1741 verified end-to-end).

## Dev Notes

### Relevant architecture patterns and constraints

- **Story 6.3 admin invite endpoints are the binding API contract.** This story consumes:
  - `POST /api/admin/invites` body `{role, ttl_preset?}` returning `{invite_id, token, registration_url, role, ttl_seconds, expires_at}` with 201.
  - `GET /api/admin/invites?status=&page=&page_size=` returning `{total, items: InviteListItem[], page, page_size}` with 200.
  - `POST /api/admin/invites/{id}/revoke` returning 204; errors 404 (not found) + 409 (already used/revoked).
  - All three require `current_admin` dependency (member → 403; anonymous → 401); the global CSRF middleware (`X-Portal-Client: web` header) is auto-attached by the `api()` wrapper per project-context.md §48.
- **Decision A — dual-backed storage** (architecture.md §1417-1423): the list endpoint queries the DB (NOT Redis) because used + expired invites remain visible to the panel. The UI doesn't need to know — `useAdminInvites` just consumes the list response.
- **Decision B — token shape + admin-panel hygiene** (architecture.md §1425-1456): the cleartext token surfaces ONCE at generation, NEVER in the list. The `GenerateInviteResponse.token` field is the only place the cleartext appears in the API surface; the `InviteListItem` MUST NOT expose `token` or `token_hash`. Story 8.6's UI mirrors this rule: the `InviteTokenDisplayModal` is the only place the cleartext is rendered, and it's dismissed by user click (NOT auto-dismiss).
- **AdminTabs role: 2-tab tablist contract.** Both tabs use `role="tab"` + `aria-selected={...}` per ARIA tablist pattern. Story 8.6 keeps the 2-tab contract; the 3rd tab "Audit log" is NOT in scope (see "Strictly out of scope" above).
- **TanStack Router `validateSearch` is the type-safe filter contract.** Per `UsersPage.tsx:81` precedent, the page reads `useSearch({from: "/admin/users"})` to get a typed `AdminUsersSearch` shape. Story 8.6 mirrors this with `AdminInvitesSearch { page?, page_size?, status? }`.
- **`useQueryClient().invalidateQueries({queryKey: ["admin", "invites"]})` invalidates ALL subtree keys.** Per TanStack Query v5 docs, partial key matches trigger refetch — calling `invalidateQueries({queryKey: ["admin", "invites"]})` from `useGenerateInvite.onSuccess` refetches `useAdminInvites({page: 1, page_size: 50, status: "active"})` (the cache key starts with `["admin", "invites", ...]`). Same applies to `useRevokeInvite.onSuccess`.
- **No `api()` wrapper bypass.** Per project-context.md §48 verbatim "Network calls go through `api()` from `@/lib/api`. It auto-attaches the `X-Portal-Client: web` CSRF header, sets `credentials: 'include'`, and retries once on `401 access_expired` via the silent refresh path. Bypassing it (raw `fetch`) silently breaks auth + CSRF." All three hooks use `api()`.
- **Tailwind v4 + theme tokens.** Status badge colors come from theme tokens (`bg-success/10`, `bg-warning/10`, `bg-destructive/10`, `bg-muted`) — NO inline hex colors anywhere. Per project-context.md §47 verbatim. The 4 status-color tokens already exist in `theme.css` (Init 3 baseline; the `bg-success/10` shape applies Tailwind v4 `/<alpha>` opacity modifier to the token, no new token needed).
- **`noUncheckedIndexedAccess: true`** — `items[0]` is `AdminInviteRow | undefined`. Handle the undefined branch with `if (!row) return null` or guard via `.map()` over the array (which preserves type via `Array.prototype.map<T, U>`). Per project-context.md §45 verbatim.
- **i18n required for ALL user-visible strings.** Per project-context.md §72 verbatim. The 27 new keys per locale × 2 locales = 54 new entries. Polish translations carry diacritics per global directive.

### Library / framework requirements

- **React 19** — uses `useState` / `useId` / `useEffect` hooks per existing patterns. No `use()` / Actions API needed in this story.
- **TanStack Router 1.x** — `createFileRoute("/admin/invites")` + `validateSearch` + `useSearch` + `useNavigate`. Mirrors `UsersPage` route shape.
- **TanStack Query 5.x** — `useQuery<TData>({queryKey, queryFn, staleTime})` + `useMutation<TData, TError, TVariables>({mutationFn, onSuccess})` + `useQueryClient().invalidateQueries({queryKey})`. Mirrors `useAdminUsers` hooks shape.
- **i18next v24 / react-i18next v15** — `useTranslation()` + `t("namespace.key", {variable})` for variable interpolation. Polish diacritics MUST be present.
- **shadcn/ui 4.x** — `<Dialog>` + `<DialogContent>` + `<DialogTitle>` + `<DialogDescription>` + `<DialogHeader>` + `<DialogFooter>` from `@/ui/dialog`. `<Input>` from `@/ui/input`. `<Button>` from `@/ui/button`. `<ConfirmDialog>` from `@/ui/custom/ConfirmDialog`. `<LoadingState>` from `@/ui/custom/LoadingState`. NO new shadcn primitives sourced for this story.
- **Vitest 1.6+** — `vi.fn()` / `vi.mock()` / `vi.spyOn()` standard mocking; `afterEach(cleanup)` from `@testing-library/react`. Mirrors Story 8.5 test patterns.
- **Playwright 1.45+** — `page.route("**/api/admin/invites**", ...)` for stubbing; `page.getByRole("tab", {name: ...})` / `page.getByRole("button", {name: ...})` for ARIA-based queries; `expect(page).toHaveScreenshot("name.png", {fullPage: true})` for baselines. Mirrors `admin-users.spec.ts` shape.

### File structure requirements

- **NEW frontend page lives at `apps/web/src/modules/admin/InvitesPage.tsx`** — peer of `UsersPage.tsx`. Naming follows the module-page convention.
- **NEW frontend route lives at `apps/web/src/routes/admin/invites.tsx`** — peer of `routes/admin/users.tsx`. TanStack Router file-based-route convention.
- **NEW frontend hooks file lives at `apps/web/src/modules/admin/hooks/useAdminInvites.ts`** — peer of `hooks/useAdminUsers.ts`. The hooks file is the dedicated abstraction for the admin-invites HTTP surface; separate file because invite-row is a distinct entity from User.
- **NEW frontend modals live at `apps/web/src/modules/admin/{GenerateInviteModal,InviteTokenDisplayModal}.tsx`** — peers of `ChangeRoleModal.tsx` + `ResetLinkDisplayModal.tsx`. Modal-as-peer-of-page convention from Stories 8.3 + 8.5.
- **NEW test files** at `apps/web/src/modules/admin/{InvitesPage,GenerateInviteModal,InviteTokenDisplayModal}.test.tsx` — colocated with source per project-context.md §113 verbatim "Vitest tests are colocated".
- **NEW Playwright spec** at `apps/web/tests/visual/admin-invites.spec.ts` — peer of `admin-users.spec.ts`. Visual-regression-spec naming convention.

### Testing requirements

- **AC-3 vitest tests I1-I9 + G1-G3 + IT1-IT3 (15 tests total) MUST pass in isolation AND together.** Run `cd apps/web && npm run test -- --run InvitesPage GenerateInviteModal InviteTokenDisplayModal` (isolation by name match) AND `cd apps/web && npm run test -- --run` (together with the full suite).
- **AC-8 Playwright 4 baselines × 4 projects = 16 PNGs MUST be committed in the dev commit.** First-time regeneration via `--update-snapshots` ONCE at dev time; subsequent CI runs compare against the baselines.
- **AC-9 admin-users 3 baselines × 4 projects = 12 PNGs MUST be regenerated AND committed in the same dev commit.** The AdminTabs styling change is the visual-diff cause; the diff is intentional + reviewable.
- **Stories 8.2 + 8.3 + 8.4 + 8.5 regression guards MUST stay green:**
  - `cd apps/web && npm run test -- --run UsersPage.test.tsx` (Stories 8.2 + 8.3 + 8.4 + 8.5 — UsersPage tests stay untouched).
  - `cd apps/web && npm run test -- --run ChangeRoleModal.test.tsx` (Story 8.3).
  - `cd apps/web && npm run test -- --run ResetLinkDisplayModal.test.tsx` (Story 8.5).
  - `cd apps/web && npm run test:visual -- admin-users` (post-baseline-regeneration).
- **Backend regression guards MUST stay green** (Story 8.6 ships NO backend changes, but the deploy gate runs check-all.sh which exercises the full backend suite anyway):
  - `cd apps/api && pytest tests/test_invite_admin.py -v` (Story 6.3 — the backend endpoints Story 8.6 consumes).
  - `cd apps/api && pytest tests/test_admin_users_list.py tests/test_admin_users_mutations.py tests/test_admin_users_2fa_overrides.py tests/test_admin_password_reset_mint.py tests/test_auth_password_reset_consume.py -v` (Stories 8.2 + 8.3 + 8.4 + 8.5).
- **`infra/scripts/check-all.sh` 13/13 green** — Story 8.6 does NOT add new stages.
- **Codex review fix-up budget: expect 0-3 fix-ups.** The most likely surface areas:
  - (a) **Status-badge color tokens.** Codex may flag the Tailwind utility classes `bg-success/10` / `bg-warning/10` etc. if any of those tokens don't exist in `theme.css`. Mitigation: verify token presence via `grep -E '\-\-color\-(success|warning|destructive|muted)' apps/web/src/styles/theme.css` before commit. If a token is missing, either add it to `@theme {}` (Init 3 pattern) OR substitute a present token (e.g. `bg-green-500/10` is FORBIDDEN per project-context.md §47 — must be a theme token). DEFER full color-system audit; ship with whatever 4 distinct tokens exist + render.
  - (b) **`generated_by_user_id` rendering as UUID-string vs email-resolution.** Codex may flag that rendering raw UUIDs is poor UX. Defensible: epics §1828 verbatim lists the column as `generated_by` literal-string IS the FK UUID; email-resolution is explicit out-of-scope per § "Strictly out of scope" above. If Codex insists strongly, the fix-up is a 10-LOC N+1 query against `/api/admin/users` per row OR a backend list endpoint extension — both significantly scope-creep beyond Story 8.6; flag for follow-up story.
  - (c) **AdminTabs `<Link>` styling parity.** The existing Users tab uses inline `cn(baseTab, ...)` conditional class building; Story 8.6's Invites tab MUST mirror this exactly. Codex may flag any divergence (e.g. different padding, different active-state border). Mitigation: copy-paste the Users tab block verbatim, only renaming `to="/admin/users"` → `to="/admin/invites"` and `activeTab === "users"` → `activeTab === "invites"`.

### Previous story intelligence (Stories 8.5 + 8.4 + 8.3 + 8.2 + 6.3 carryover)

- **Story 8.5 set the precedent for the cleartext-token-once modal UX.** `ResetLinkDisplayModal.tsx` is the structural template for `InviteTokenDisplayModal.tsx`. Two modals share the absolute-URL resolution logic, the readonly `<Input>` + clipboard copy + Done pattern, the `useState<boolean>(false)` copied slot. A future refactor to a generic `<TokenDisplayModal>` is explicitly deferred per "Strictly out of scope" above.
- **Story 8.5 set the precedent for `useIssuePasswordResetAdminUser`** (a mutation hook returning a non-void response shape that the page consumes). Story 8.6's `useGenerateInvite` follows this pattern: returns `GenerateInviteResponse` (not void), the page handles the response by opening the display modal.
- **Story 8.4 set the precedent for force-* mutation hooks WITHOUT useQuerydClient invalidation when the mutation has no list-state side-effect.** Story 8.6's `useGenerateInvite` + `useRevokeInvite` DO invalidate `["admin", "invites"]` because the list IS the surface that changes (new row appears, existing row transitions to revoked). The Story 8.5 `useIssuePasswordResetAdminUser` deliberately does NOT invalidate `["admin", "users"]` because the user-list state is unchanged — the analogy holds: Story 8.6 invalidates because the invite-list state IS changed.
- **Story 8.3 set the precedent for the `errorCode` useState slot + `KNOWN_ERROR_CODES` Set + inline error banner above the table.** Story 8.6 mirrors this pattern: `errorCode: "generic" | "invite_not_found" | "invite_already_resolved" | null`, mapped via `t("admin.invites.errors.{code}")`.
- **Story 8.3 + 8.4 + 8.5 set the precedent for `<ConfirmDialog>` reuse from `@/ui/custom/ConfirmDialog`.** Story 8.6 reuses for the revoke-confirm flow (single instance — only one destructive action per row, vs Story 8.3's 4 destructive actions via menu items).
- **Story 8.2 set the precedent for the `<AdminTabs activeTab="users">` shell render + `tab` ARIA role + Generate-button positioning at the top-right of the controls row.** Story 8.6's InvitesPage uses `activeTab="invites"` + identical controls-row pattern.
- **Story 6.3 audit-action names `auth.invite.generated` + `auth.invite.revoked` are already registered in `app/core/audit.py:17` + emitted by the backend.** Story 8.6 ships ZERO audit registry changes; the audit-trail is naturally extended via the backend already-shipped emissions when the panel triggers the endpoints. The acceptance gate per epics §1741 ("Audit row visible for every panel action with correct `actor_user_id` / `target_user_id` pair") is verified post-deploy on `.190` by inspecting `/api/admin/audit?action=auth.invite.generated&actor_user_id=<admin_uuid>` and confirming a row exists with the matching `target_user_id` (the row will have `entity_id = invite_uuid`, NOT `target_user_id` — the `auth.invite.*` audit shape uses `entity_type="invite_token"` not `entity_type="user"`).
- **Auto-deploy after merge** — per `feedback_auto_deploy_dev`, run `infra/scripts/deploy.sh` to `.190` after Story 8.6 merges to main. Code changes present so deploy WILL run (not no-op).
- **`feedback_subagent_format_residue` reminder** — after dev-agent flips status to `review`, run `git status` to verify no `ruff format` residue from frontend tooling drift. The frontend is prettier-formatted not ruff-formatted, but a `chore: prettier format` catch-up commit per phase is plausible if the dev agent leaves formatting drift.
- **`feedback_preexisting_issue_threshold` reminder** — Story 6.3 + 8.5 had similar "should we refactor to a generic component" candidates that were left as 1-flag-each. Story 8.6's `InviteTokenDisplayModal` adds a 2nd flag for the "cleartext-token-once modal" pattern; threshold is 3 for refactor-candidate promotion. Document the 2nd flag in the deferred-work log without promoting yet.

### Git intelligence (recent commits)

```
cd6354a fix(api,web): Story 8.5 codex P2 — password validate pre-claim + absolute URL
aaac593 feat(api,web): admin-issued password reset link (Story 8.5)
af07752 fix(api,web): Story 8.4 codex P3 — colspan + race-safe force flag clear
ed84257 feat(api,web): admin 2FA overrides — force-enrollment + force-disable (Story 8.4)
ddb9f14 fix(api,web): Story 8.3 codex P1+P2 — typecheck guard + 2FA is_active gate
```

Pattern (Epic 8 baseline): each story lands as `feat(<scopes>): <subject> (Story 8.X)` initial commit, then 1-2 `fix(...)` Codex P1/P2 follow-up commits on the same story-scoped subject before sprint-status flips `review` → `done`. Story 8.6's commit shape: `feat(web): admin Invites tab — list + status filter + generate + revoke UI (Story 8.6)`. Scope is `web` only (NOT `api,web`) because Story 8.6 is UI-only — the absence of `api` scope signals the zero-backend-changes invariant at a glance for reviewers and future readers of git history.

### Latest technical specifics

- **TanStack Router 1.85+** — `<Link to="/admin/invites">` renders as `<a href="/admin/invites">` at runtime; the `aria-selected` attribute is passed-through but NOT mapped to a CSS pseudo-class — the Tailwind class string handles the active-state styling manually (per existing AdminTabs Users-tab block precedent).
- **React Query v5 cache invalidation** — `invalidateQueries({queryKey: ["admin", "invites"]})` triggers refetch for ALL keys starting with `["admin", "invites"]` (prefix match). The pagination/filter state is preserved in the query key, so the refetch reads the same page+filter automatically.
- **Tailwind v4 `/<alpha>` modifier** — `bg-success/10` applies the `--color-success` token at 10% opacity (Tailwind v4 native; NO PostCSS plugin needed). The 4 status colors (`success`, `muted`, `warning`, `destructive`) are project-standard tokens (Init 3 baseline; same set used in `<Button variant="destructive">` from shadcn/ui).
- **Playwright `--update-snapshots` flag** — regenerates baselines for the matched test pattern only; running with `admin-invites` matches only the new spec file, leaving other baselines untouched. Running with `admin-users` matches the existing spec file for the 12 PNG regenerations in T14.

### Project Structure Notes

- **Alignment with unified project structure:** all new content lands in natural locations per project-context.md §132-138 verbatim "Folder layout under `apps/web/src/`": shell stays untouched (no top-level chrome change), modules/admin gains 4 new files + 4 new test files, routes/admin gains 1 new route file, lib/api-types.ts is appended, locales/{en,pl}.json are appended/edited, tests/visual gains 1 new spec. NO new top-level directories. NO new infra/scripts files. NO new Docker/Compose changes.
- **Detected conflicts or variances:** AdminTabs.tsx still references `admin.tabs.invites_coming_soon` i18n key as of pre-Story-8.6 state — Story 8.6 removes both the key reference (T10) AND the key itself (T11.1). This is the binding cleanup. If a future story re-introduces a disabled-tab placeholder pattern (e.g. for Audit log tab), it should re-create the key under a new namespace like `admin.tabs.audit_coming_soon` to avoid shadowing.
- **Naming conventions:** the new TypeScript types in `api-types.ts` follow the existing convention: PascalCase (`AdminInviteRow`, `GenerateInviteRequest`) for interfaces, PascalCase (`InviteStatus`, `InviteTTLPreset`) for string literal unions. The hook names mirror Story 8.5 verbatim shape (`useAdminInvites` matches `useAdminUsers`; `useGenerateInvite` matches `useUpdateAdminUser`; `useRevokeInvite` matches `useForceLogoutAdminUser`).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-8.6`] (lines 1820-1831) — Story 8.6 acceptance check shape verbatim
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-8-acceptance-gate`] (line 1741) — the four routine operator actions includes "generate invite (via Invites tab in 8.6), revoke invite (via 8.6 panel button)"
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-A`] (lines 1417-1423) — invite-token storage rationale; Story 8.6 surfaces the DB-row metadata
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-B`] (lines 1425-1456) — token shape + admin-panel hygiene; Story 8.6 enforces the "cleartext token never in list" rule via UI never rendering `token` field from list response
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-1`] (line 1487) — the two-tab panel binding; Story 8.6 + 8.2 jointly realize it
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-INVITE-2`] (line 1474) — admin invite list with status filter UI; Story 8.6 surfaces it
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-INVITE-3`] (line 1475) — admin invite revoke UI; Story 8.6 surfaces the panel button calling the Story 6.3 revoke endpoint
- [Source: `_bmad-output/implementation-artifacts/6-3-admin-invite-endpoints-generate-list-revoke.md`] — the backend contract Story 8.6 consumes (POST/GET/POST endpoints; request/response shapes)
- [Source: `_bmad-output/implementation-artifacts/8-2-admin-users-tab-paginated-list.md`] — the Users-tab UI pattern Story 8.6's Invites-tab mirrors (page layout, AdminTabs render, pagination footer)
- [Source: `_bmad-output/implementation-artifacts/8-3-per-user-actions-role-deactivate-force-logout.md`] — the kebab/menu-action UX pattern (Story 8.6 simplifies to single-action-per-row); `ConfirmDialog` reuse precedent
- [Source: `_bmad-output/implementation-artifacts/8-5-admin-issued-password-reset-link.md`] — the cleartext-token-once modal UX pattern (ResetLinkDisplayModal); the absolute-URL resolution Codex P2 fix-up; the post-success modal-opens-modal pattern
- [Source: `apps/api/app/modules/invite/admin_router.py:40-191`] — the backend route declarations Story 8.6 consumes (URL paths, response models, error envelope)
- [Source: `apps/api/app/modules/invite/admin_schemas.py:24-101`] — the backend Pydantic schemas Story 8.6 mirrors in `api-types.ts`
- [Source: `apps/web/src/modules/admin/UsersPage.tsx:1-661`] — Story 8.6's InvitesPage mirrors the page-shape, controls-row, pagination, error-banner conventions
- [Source: `apps/web/src/modules/admin/AdminTabs.tsx:1-47`] — Story 8.6 modifies the Invites tab block (lines 31-44)
- [Source: `apps/web/src/modules/admin/ResetLinkDisplayModal.tsx:1-97`] — Story 8.6's InviteTokenDisplayModal mirrors the modal-shape, clipboard copy, absolute-URL resolution
- [Source: `apps/web/src/modules/admin/ChangeRoleModal.tsx:1-102`] — Story 8.6's GenerateInviteModal mirrors the form-modal shape (controlled select + Confirm/Cancel)
- [Source: `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-113`] — Story 8.6's useAdminInvites hooks file mirrors the query + mutation hook conventions
- [Source: `apps/web/src/routes/admin/users.tsx:1-57`] — Story 8.6's route file mirrors the structure (AuthGate, isAdmin guard, validateSearch)
- [Source: `apps/web/src/lib/api-types.ts:200-241`] — Story 8.6 appends a new section after Story 8.5's `PasswordResetMintResponse`
- [Source: `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`] — Story 8.6 modifies + appends i18n entries; key-set parity invariant per AC-10
- [Source: `apps/web/tests/visual/admin-users.spec.ts:1-353`] — Story 8.6 modifies one test block (T12); mirrors the spec shape for the new admin-invites.spec.ts
- [Source: `apps/web/tests/visual/register.spec.ts:1-104`] — Story 8.6's admin-invites.spec.ts mirrors the stub-helper pattern + baseline naming convention
- [Source: `_bmad-output/project-context.md` §38-269] — TypeScript / React / TanStack / shadcn / Tailwind / Vitest / Playwright / git / deploy / observability conventions
- [Source: `AGENTS.md`] — repo layout + commit conventions + Polish-i18n requirement + auto-deploy rule

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m]

### Debug Log References

### Completion Notes List

### File List

### Change Log

| Date       | Author | Change                                                                                                                                                                              |
| ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-20 | Ezop   | Story 8.6 spec authored via bmad-create-story (autonomous YOLO mode). Admin Invites tab (FR5-ADMIN-1, FR5-INVITE-2 UI, FR5-INVITE-3 UI): UI-only consumer of Story 6.3 endpoints; AdminTabs `<span>` placeholder replaced with `<Link>`; cleartext-token-once modal pattern reused from Story 8.5; 15 vitest tests + 4 Playwright baselines × 4 projects + 12 admin-users baselines regenerated; Epic 8 acceptance gate unblocked. |
