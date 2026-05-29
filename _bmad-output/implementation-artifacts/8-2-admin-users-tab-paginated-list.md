# Story 8.2: Admin Users tab (`/admin/users` route + `GET /api/admin/users` paginated list)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer (Ezop, banking-IT operator wearing the dev-team ITCM hat),
I want **the first of the two Epic 8 admin tabs — `/admin/users` — shipped end-to-end as a paginated, sortable, searchable users list with the per-user columns Decision I binds (email, role, created_at, last_active_at, totp_enabled, is_active), built on top of the Story 8.1 schema + middleware foundation but performing strictly READ operations (no row mutations in this story; PATCH + per-row actions belong to Story 8.3)**, namely:

1. **NEW backend endpoint `GET /api/admin/users`** in `apps/api/app/modules/admin/router.py` (the same module that already hosts `/api/admin/audit` and `/api/admin/sentry-test` — co-locate per existing convention; do NOT spin up a new `users_router.py`). Signature: `GET /api/admin/users?page=N&page_size=M&search=<email-substring>&sort_by=<col>&sort_order=<asc|desc>` returning `AdminUserListResponse{total, items: list[AdminUserListItem], page, page_size}`. Each item exposes the binding column set from epics §1770 verbatim: `{id, email, display_name, role, created_at, last_active_at, totp_enabled (derived: totp_enabled_at IS NOT NULL), is_active}`. **Critical:** `password_hash` and `totp_secret` (the Fernet ciphertext column) MUST NOT appear in the response shape — they are confidentiality-tier columns that the admin panel has no legitimate read of (the operator does not paste Fernet ciphertext anywhere; exposing it widens the blast radius if the admin endpoint leaks). Dependency: `current_admin` per the FR5-MEMBER-2 contract verbatim (a `member`-authenticated GET returns 403 — verified by extending `apps/api/tests/test_share_member_permission.py` with one new assertion against this endpoint, OR by a new dedicated negative-perm test in the new test file; implementer's call between the two).
2. **NEW Pydantic schemas** at `apps/api/app/modules/admin/users_schemas.py` (the NEW file — `admin/router.py` does not yet have a schemas sibling; create the file as a peer of `admin/router.py` mirroring the `invite/admin_schemas.py:1-101` shape verbatim including the file-level docstring citing Decision I + the hygiene rule that confidentiality-tier columns NEVER appear here): `AdminUserListItem(BaseModel, frozen=True)` with the 8 fields above + `AdminUserListResponse(BaseModel, frozen=True){total, items, page, page_size}` mirroring `InviteListResponse:78-83` verbatim. **The `email` field is wired through `Pydantic str` (not `EmailStr` — the SQLModel `User.email` is a plain `str` with a uniqueness index per `_user.py:24` and re-validating via `EmailStr` on every list-page read introduces overhead with zero defense; the input layer at register time has already validated).**
3. **NEW backend tests** `apps/api/tests/test_admin_users_list.py` with 8 named tests T1-T8 binding the endpoint contract (see AC-3 table). Reuses the new `isolated_client` conftest fixture promoted in Story 8.1 (NOT a per-file copy of the `client` fixture — Story 8.2 is the first Epic 8 test file and is the binding consumer of the conftest promotion per Story 8.1 AC-7 last bullet; per-file copy would constitute a regression on the promotion).
4. **NEW frontend route + page** at `apps/web/src/routes/admin/users.tsx` (TanStack Router file-route) + `apps/web/src/modules/admin/UsersPage.tsx` (the actual page component, mirrored on the `apps/web/src/routes/settings/sessions.tsx:1-110` → `Sessions` component pattern verbatim — the route file imports the page component from the modules folder; tests live next to the page component in the modules folder for parity with `Settings2faPage.tsx` + `Reauth2faModal.tsx` Story 7.5 precedent at `apps/web/src/modules/auth/`). The page renders:
   - A page header `<h1>{t("admin.users.title")}</h1>` (locale-agnostic `<h1>` for visual-regression role matching per `tests/visual/sessions.spec.ts:55-58` precedent — exactly ONE H1 per page).
   - A **tab strip** above the table containing TWO tab buttons "Users" (active) + "Invites" (disabled with `aria-disabled="true"` + tooltip `t("admin.tabs.invites_coming_soon")` citing Story 8.6 — disabled-tab pattern lets Story 8.6 enable the second tab without restructuring the layout; per the epics §1739 "two admin tabs on the existing admin module" binding the tabs are co-equal peers from the user's mental model, just one is not yet shipped). The tab strip is a single shared component `apps/web/src/modules/admin/AdminTabs.tsx` exporting a `<AdminTabs activeTab="users" />` that 8.6 will reuse with `activeTab="invites"`.
   - A **search input** (`<input type="search">`) controlled by `search` query-string param (TanStack Router `useSearch({ from: "/admin/users" })` + `useNavigate` per the `apps/web/src/routes/login.tsx:172-179` precedent for typed search params).
   - A **page-size selector** as a `<select>` with options `[25, 50, 100, 200]` (the existing admin-list defaults from `invite/admin_router.py:119` `page_size=50 ge=1 le=200` — Story 8.2 honors this bound, NOT the epics §1772 mention of "25 rows per page" verbatim which is a planning-text approximation; the actual ratified shipping bound across Epic 6 is `page_size=50` default, `le=200` cap, and Story 8.2 stays consistent rather than introducing a divergent 25-default just for users; flagged for bmad-correct-course at Epic 8 retro if operator wants the 25-default explicitly).
   - A **sortable table** with columns in this order: Email, Display name, Role, 2FA, Active, Created, Last active. Each of {Email, Role, Created at, Last active at} has a clickable column header that cycles `none → asc → desc → none` via `sort_by` + `sort_order` query-string params. 2FA + Display name + Active are display-only columns (not sortable in this story — added in future stories if operator finds a use; sorting on derived booleans is awkward UX). Per-cell renders use the existing `formatDate` / `formatDateTime` helpers from `apps/web/src/lib/` if present; otherwise inline `new Date(iso).toLocaleString("pl-PL", ...)` per Story 7.5 `Settings2faPage.tsx` precedent.
   - A **footer pagination strip** showing `t("admin.users.pagination_label", {first, last, total})` (e.g. "Showing 1-25 of 137 users") + Previous + Next buttons (no jump-to-page input for v1 — minimum-surface; can add if operator complains).
   - **Negative AC enforcement (FR5-ADMIN-4):** the page renders ZERO `<input type="checkbox">` elements in either the table header OR table body, ZERO bulk-action menus, ZERO "Select all" controls. The per-row action column is **also absent** in Story 8.2 (per-row actions ship in Story 8.3 — adding an empty actions column here would muddy the visual baseline that Story 8.3 then has to update). Verifiable: the new Playwright spec (AC-7) asserts `page.locator('table input[type="checkbox"]').count() === 0` AND `page.getByRole('button', { name: /bulk|select all|wszystkie/i }).count() === 0`.
5. **NEW frontend hook** `apps/web/src/modules/admin/hooks/useAdminUsers.ts` exporting `useAdminUsers({page, page_size, search, sort_by, sort_order})` — a single `useQuery` per the `apps/web/src/modules/catalog/hooks/useSessions.ts:7-10` precedent verbatim. `queryKey: ["admin", "users", {page, page_size, search, sort_by, sort_order}]`. Stale-time: 30 seconds (matches the catalog default per `apps/web/src/lib/queryClient.ts` if present, else default 0 → react-query background-refetch on every focus, which is fine for an admin panel).
6. **NEW frontend vitest tests** at `apps/web/src/modules/admin/UsersPage.test.tsx` with 4 named tests V1-V4 binding the rendering contract (see AC-9).
7. **NEW Playwright spec** at `apps/web/tests/visual/admin-users.spec.ts` covering 3 baseline scenarios (empty / one-row / many-row) + the FR5-ADMIN-4 negative AC. Mirrors `tests/visual/sessions.spec.ts:1-78` shape verbatim.
8. **NEW api-types entries** at `apps/web/src/lib/api-types.ts` — `AdminUser` interface (the 8 fields) + `AdminUsersListResponse` interface (`{total, items, page, page_size}`). Inserted in a NEW `// --- Admin users (Story 8.2) ---` section after the existing `// --- Sessions ---` block at line 184.
9. **NEW i18n keys** in both `apps/web/src/locales/en.json` AND `apps/web/src/locales/pl.json` for the strings consumed by UsersPage + AdminTabs (see AC-8). All keys use the `admin.*` namespace introduced by this story.
10. **Modified `apps/web/src/shell/UserMenu.tsx`** — add a single `DropdownMenuItem` rendering `<a href="/admin/users" />` with label `t("admin.menu_link")` gated behind `isAdmin` (mirrors the existing `isAdmin && (...)` pattern at lines 56-58 verbatim for the "Agents info" dialog). This is the operator's entry point into the admin panel from the user menu; ModuleRail is NOT modified in this story (the rail is the cross-module switcher for catalog/queue/spools/printer/requests — admin is operator-tier and lives behind the user menu per existing UX shape, not as a top-level module peer).

so that:

- **The Epic 8 admin-panel surface lights up** — Story 8.1 shipped the schema + middleware but the operator has no UI to see `last_active_at` in action. Story 8.2 makes the column visible and proves the throttle is doing what it claims (the operator can browse `/admin/users` after a fresh login and verify their own row's `last_active_at` updates ≤1×/5min).
- **The /admin/users route is wired before Story 8.3 needs it** — Story 8.3 layers per-row action menu on top of the table Story 8.2 ships. Decoupling the read path (8.2) from the write path (8.3) preserves the 8.1 design principle "read columns first, mutate next" and keeps the visual baseline stable across the 8.2 → 8.3 transition (Story 8.3 only ADDS a row-actions column to the existing baseline; it does not restructure it).
- **FR5-ADMIN-4 (no bulk operations) is enforced architecturally, not just documentationally** — the Playwright snapshot test that asserts the absence of `input[type="checkbox"]` + bulk-action selectors lands in the same commit as the table itself, so a future panel-v2 refactor cannot quietly add the bulk-select scaffolding without tripping the spec. Per epics §1774 verbatim "the deliberate exclusion is recorded so future agents (UI redesigns, panel-v2 considerations) do not infer missing bulk CRUD as a defect" — this story turns that documentation into runnable evidence.
- **The Init 5 `_user.py:24` invariant is preserved at the response layer** — the new endpoint exposes the 8 binding columns and ONLY those 8; `password_hash` + `totp_secret` are filtered at the schema layer, not at the SQL layer (the SQL `SELECT *` still fetches them — there is no value in dropping them at the SQL tier since SQLAlchemy session-attached User objects are cheap). The hygiene boundary is the Pydantic-from-orm projection inside the endpoint, mirroring the `InviteListItem` shape's hygiene boundary which drops the `token_hash` column at the same projection step.

### Story scope is strictly bounded

- **NEW files (~6):**
  - `apps/api/app/modules/admin/users_schemas.py`
  - `apps/api/tests/test_admin_users_list.py`
  - `apps/web/src/modules/admin/UsersPage.tsx`
  - `apps/web/src/modules/admin/UsersPage.test.tsx`
  - `apps/web/src/modules/admin/AdminTabs.tsx`
  - `apps/web/src/modules/admin/hooks/useAdminUsers.ts`
  - `apps/web/src/routes/admin/users.tsx`
  - `apps/web/tests/visual/admin-users.spec.ts`
  - (One of the above is the route file; the others are the page module + tests + spec — the route file is a small <30-LOC file that imports from the module folder per the `routes/settings/sessions.tsx` precedent.)
- **MODIFIED files (~4):**
  - `apps/api/app/modules/admin/router.py` (add the new GET handler beside the existing `/audit` + `/audit-log` + `/sentry-test`; no other change).
  - `apps/web/src/lib/api-types.ts` (add NEW `// --- Admin users (Story 8.2) ---` section after sessions block).
  - `apps/web/src/shell/UserMenu.tsx` (add admin-only "Admin panel" DropdownMenuItem; one new `isAdmin && (...)` block).
  - `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` (add the new `admin.*` i18n keys — see AC-8).
- **STRICTLY OUT OF SCOPE** (these belong to later stories and adding them here splits ownership / inflates the diff):
  - `PATCH /api/admin/users/{id}` for `is_active` / role mutations — Story 8.3.
  - `POST /api/admin/users/{id}/force-logout` — Story 8.3.
  - `POST /api/admin/users/{id}/force-2fa-enrollment` + `POST /api/admin/users/{id}/force-disable-2fa` — Story 8.4.
  - `POST /api/admin/users/{id}/password-reset` — Story 8.5.
  - The per-row action column (kebab menu, "Change role / Deactivate / etc.") on the Users table — Story 8.3 surfaces this. Story 8.2 ships ZERO actions UI.
  - The Invites tab content (`/admin/invites` route + InvitesPage component + filter UI) — Story 8.6. Story 8.2 ships only the tab strip with the Invites tab DISABLED + tooltip pointing at 8.6.
  - Rate-limit middleware on the new endpoint — admin endpoints are NOT under any of the four rate-limit scopes (login / refresh / register / share); admin-tier access is bounded by `current_admin` dependency + operator-tier trust, not by request-frequency throttle. (If 8.3+ ever introduces an admin-tier rate-limit scope, that's a Decision-G amendment, not a Story 8.2 deliverable.)
  - Soft-delete enforcement at `/api/auth/login` + `/api/auth/refresh` — Story 8.3 per epics §1786 + Story 8.1 § Critical scope boundary verbatim.
  - Audit-log emissions — Story 8.2 is a READ endpoint, no `record_event()` call lands here. (Reads are not audited in this project — confirmed by `apps/api/app/modules/admin/router.py:55-81` `list_audit` itself not emitting an audit row.)
  - `/admin/invites` route file — Story 8.6 creates this. Story 8.2's AdminTabs component references "/admin/invites" as the future-target but does NOT define the route (TanStack Router silently no-ops on undefined-target hrefs at runtime; the AdminTabs Invites button is disabled via `aria-disabled` so it does not navigate anyway).
  - `/admin/audit` panel UI surfacing the existing `/api/admin/audit` endpoint — out of scope of Epic 8 (deferred panel UX; the operator queries audit via raw `curl` or via the Story 6.3 invite-admin tests' assertions for now).

No new dependencies. No new audit action emissions. No new entity_type. No new Settings field. No new rate-limit scope. No new env-var. No new Alembic migration (head stays `0014_users_is_active_last_active` post Story 8.1). No new middleware. No change to `apps/api/app/main.py`. No change to `apps/api/app/router.py` (the existing `admin_router` mount line 19 covers the new endpoint).

## Acceptance Criteria

**AC-1 — `GET /api/admin/users` endpoint shape: paginated, sortable, searchable, admin-only.**

- Given an admin-authenticated request (valid `portal_access` cookie, `role == "admin"`),
- When the client calls `GET /api/admin/users?page=N&page_size=M&search=<q>&sort_by=<col>&sort_order=<dir>`,
- Then the endpoint MUST:
  - Validate query params per FastAPI `Query(...)` constraints:
    - `page: int = Query(default=1, ge=1)` — 1-indexed, mirrors `invite/admin_router.py:118`.
    - `page_size: int = Query(default=50, ge=1, le=200)` — mirrors `invite/admin_router.py:119` verbatim. **Critical:** despite epics §1772 saying "25 rows per page", Story 8.2 ships `default=50` to stay consistent with the established Init 5 admin-list contract (Story 6.3, 6.4); changing the default to 25 would force a divergent UX bound on the Users tab vs Invites tab and is rejected as gratuitous churn. The page-size SELECTOR in the frontend defaults to 50 to match the API default; the frontend MAY remember the operator's last-chosen size in `localStorage` later (NOT this story).
    - `search: str | None = Query(default=None, max_length=255)` — substring match against `email` column, case-insensitive (use SQLAlchemy `User.email.ilike(f"%{search}%")` for SQLite + Postgres dialect-portable lowercase comparison). If `None` or empty string, no filter applied.
    - `sort_by: Literal["email", "role", "created_at", "last_active_at"] | None = Query(default=None)` — sort column. If `None`, default ordering is `created_at DESC` (newest user first, matches `InviteToken.generated_at DESC` convention).
    - `sort_order: Literal["asc", "desc"] | None = Query(default=None)` — sort direction. If `None`, default is `desc` for `created_at`/`last_active_at` (recency-first), `asc` for `email`/`role` (alphabetical).
  - Resolve dependency `_user_id: uuid.UUID = current_admin` — non-admin authenticated requests return 403 with FastAPI's default `{"detail": "..."}` envelope; anonymous requests return 401.
  - Execute the query via the `session: Session = Depends(get_session)` injection (mirrors `list_audit` at `admin/router.py:55-61` verbatim — same session pattern; do NOT introduce `AsyncSession` here, the project is sync-SQLAlchemy throughout per Init 0).
  - Apply filters in order: `search` ilike → `sort_by` ordering (with fallback to `created_at DESC` when `sort_by` is None or `User.last_active_at` is NULL — `sort_by=last_active_at` puts NULLs LAST regardless of asc/desc, use `User.last_active_at.is_(None).asc()` as primary sort key + then the requested column).
  - Compute `total` as `SELECT COUNT(*) FROM user [WHERE email ILIKE ...]` (apply search filter to count too; the result is the post-filter count, not the total user count).
  - Apply pagination via `offset = (page - 1) * page_size` + `.offset(offset).limit(page_size)`.
  - Project each `User` row to `AdminUserListItem` shape: `{id, email, display_name, role, created_at, last_active_at, totp_enabled: bool (= user.totp_enabled_at is not None), is_active}`. The projection happens INSIDE the endpoint via an explicit list comprehension over the SQLAlchemy result — do NOT add a `from_row()` classmethod on the schema (the `InviteListItem` shape uses inline construction at `invite/admin_router.py:138-152` and that's the binding convention for Init 5 admin endpoints).
  - Return `AdminUserListResponse(total, items, page, page_size)`.
- And the OpenAPI surface MUST expose the endpoint with a `summary` + `description` matching the `invite/admin_router.py:99-110` docstring shape (3-4 sentences: what it returns, hygiene rule about `password_hash`/`totp_secret` filtered out, ordering, pagination semantics).
- And the endpoint MUST be mounted under the existing `apps/api/app/modules/admin/router.py` router (`prefix="/api/admin"`) — full path `/api/admin/users`. The `tags=["admin"]` tag is inherited from the router definition (verify by checking the existing audit/sentry-test endpoints' OpenAPI tags after the change; they MUST still appear under the `admin` tag).

**AC-2 — `AdminUserListItem` + `AdminUserListResponse` schemas at NEW `apps/api/app/modules/admin/users_schemas.py`.**

- Given the existing schema-module precedent at `apps/api/app/modules/invite/admin_schemas.py:1-101`,
- When Story 8.2 ships,
- Then `apps/api/app/modules/admin/users_schemas.py` MUST exist as a NEW file with:
  - A 4-line file-level docstring citing Decision I (`architecture.md §1601-1630`) for the column-shape rationale + a hygiene-rule paragraph: `Hygiene rule: this schema exposes only the 8 panel-visible columns from epics §1770; password_hash + totp_secret are NEVER projected here. The admin panel has no legitimate read of those columns; surfacing them would widen blast radius on accidental endpoint leaks.` (the hygiene rule statement is verbatim binding per Story 8.2 AC-2 grep check below).
  - `from __future__ import annotations` first.
  - Imports: `datetime`, `uuid`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `app.core.db.models._enums.UserRole`.
  - `class AdminUserListItem(BaseModel)` with `model_config = ConfigDict(frozen=True)` + 8 fields in this order: `id: uuid.UUID`, `email: str`, `display_name: str`, `role: UserRole`, `created_at: datetime.datetime`, `last_active_at: datetime.datetime | None`, `totp_enabled: bool`, `is_active: bool`. Field ordering MUST match this list (the OpenAPI schema preserves declared order; consumer codegen sees this order).
  - `class AdminUserListResponse(BaseModel)` with `model_config = ConfigDict(frozen=True)` + 4 fields: `total: int`, `items: list[AdminUserListItem]`, `page: int`, `page_size: int`. Mirrors `InviteListResponse:78-83` verbatim.
- And the schema file MUST NOT import `User` SQLModel — the projection happens in the router, not in the schema (keeps the schema dialect-free; consumer codegen can read this file standalone).
- And `apps/api/app/modules/admin/__init__.py` is NOT modified (the existing file is empty per `ls apps/api/app/modules/admin/` shows `__init__.py` exists but no re-exports — Story 8.2 keeps it that way; the schemas are imported by full dotted path from the router, not from the package).

**AC-3 — Backend tests `apps/api/tests/test_admin_users_list.py` (NEW; 8 named tests T1-T8 binding the AC-1 + AC-2 behavior).**

- Given the new conftest `isolated_client` fixture promoted in Story 8.1 (AC-7),
- When Story 8.2 ships,
- Then `apps/api/tests/test_admin_users_list.py` MUST exist as a NEW file with 8 tests:

  | # | Name | Asserts |
  |---|------|---------|
  | T1 | `test_admin_user_list_returns_seeded_admin_only_on_empty_db` | After fixture boot (just `seed_admin()` ran), GET `/api/admin/users` returns 200 with `total=1`, `items=[{email: "admin@localhost.localdomain", role: "admin", is_active: true, totp_enabled: false, last_active_at: <recent or null>}]`. Verifies the projection shape end-to-end. |
  | T2 | `test_admin_user_list_paginates_correctly` | Seed 75 `member`-role users (script in fixture, NOT inline — extract to a `_seed_members(session, n)` helper at top of file) + `page=1&page_size=25` → 25 items + `total=76` (75 + seeded admin) + `page=4&page_size=25` → 1 item (the seeded admin if sorted ASC by email, OR no items if pagination clamps; verify the SHAPE first then adjust the assertion). 1-index semantics: `page=0` returns HTTP 422 (FastAPI Query validation). |
  | T3 | `test_admin_user_list_search_filters_by_email_substring` | Seed 5 members with emails `["alice@a", "alice2@a", "bob@b", "alex@a", "charlie@c"]` + GET `/api/admin/users?search=al` → 3 items in `total` (alice, alice2, alex) regardless of order. Case-insensitive: `search=AL` returns same 3. Empty search → all 6 (5 + admin). |
  | T4 | `test_admin_user_list_sort_by_email_asc` | Seed 5 members with emails `["zeta@z", "alpha@a", "mike@m", "beta@b", "delta@d"]` + GET `/api/admin/users?sort_by=email&sort_order=asc` → items[0..5].email == `["admin@localhost.localdomain", "alpha@a", "beta@b", "delta@d", "mike@m", "zeta@z"]`. (The seeded admin's email starts with `a`, sorts before alpha@a — verify the alphabetical order of dot-domain vs `@a`; if collation differs, adjust expected order to match actual SQLite lexicographic byte order.) |
  | T5 | `test_admin_user_list_sort_by_last_active_at_desc_puts_nulls_last` | Seed 3 members: one with `last_active_at = 2026-05-15T10:00:00Z`, one with `2026-05-16T10:00:00Z`, one with `None`. GET `/api/admin/users?sort_by=last_active_at&sort_order=desc` → first item is the 2026-05-16 one, second is the 2026-05-15 one, third is the None one (NULLs LAST regardless of asc/desc). |
  | T6 | `test_admin_user_list_derives_totp_enabled_from_totp_enabled_at` | Seed 3 members: one with `totp_enabled_at = NULL`, one with `totp_enabled_at = 2026-05-10T...`, one with `totp_enabled_at = 2026-05-15T...`. Response `totp_enabled` flags == `[False, True, True]` matching the inputs by user_id. Verifies the projection-time derivation. |
  | T7 | `test_admin_user_list_omits_password_hash_and_totp_secret` | Seed 1 member with `password_hash = "test-hash"` + `totp_secret = "test-ciphertext"`. Parse the response JSON via `response.json()` + assert `"password_hash" not in items[i]` AND `"totp_secret" not in items[i]` for every item. **Binding hygiene check.** |
  | T8 | `test_admin_user_list_returns_403_for_member_role` | Mint a `member`-role cookie (use `encode_token(..., role="member", ...)` per the `test_share_member_permission.py` precedent — that test already proves the cookie-mint path works). GET `/api/admin/users` with that cookie → HTTP 403 + body `{"detail": "Forbidden"}` (or whatever the existing `current_admin` dependency returns; verify by reading `apps/api/app/core/auth/dependencies.py:current_admin` to confirm the exact error envelope). Anonymous (no cookie) → HTTP 401. |

- And T1-T8 MUST consume the conftest `isolated_client` fixture (NOT a per-file copy). If any test needs cookie-minting + admin-token, mint the token inline inside the test body via `encode_token(...)` per the Story 7.x precedent — do NOT add a wrapper fixture in this test file for that (per-file fixture proliferation is the anti-pattern Story 8.1 AC-7 explicitly mitigated).
- And the file MUST include the seed helper `_seed_members(session: Session, n: int, *, email_prefix: str = "member") -> list[uuid.UUID]` at the top (returns the inserted UUIDs in insertion order for assertion). The helper creates rows with deterministic emails (`f"{email_prefix}{i}@test.example"` for i in range(n)) + `display_name=f"Member {i}"` + `role=UserRole.member` + `password_hash="bcrypt-test-hash"` (no real bcrypt — these rows are never authenticated; the test cookie is admin's).
- And the AUTOUSE fixture pattern from `test_invite_admin.py:65-78` MUST be replicated: a per-test `_clear_user_and_audit_tables` autouse that wipes everything EXCEPT the seeded admin between tests (use `WHERE email != 'admin@localhost.localdomain'` predicate to preserve the seed). This guarantees test isolation when run together vs in isolation.
- And `cd apps/api && .venv/bin/pytest tests/test_admin_users_list.py -v` MUST be green for all 8 tests, both in isolation and together with the full suite (current Epic 7 close-out baseline: 690 backend tests + Story 8.1 added ~10 → ~700; Story 8.2 adds 8 more → ~708).

**AC-4 — Frontend route `apps/web/src/routes/admin/users.tsx` + page component `apps/web/src/modules/admin/UsersPage.tsx`.**

- Given the TanStack Router file-route convention + the `routes/settings/sessions.tsx` precedent at `apps/web/src/routes/settings/sessions.tsx:1-110`,
- When Story 8.2 ships,
- Then `apps/web/src/routes/admin/users.tsx` MUST exist as a NEW file (~30 LOC max) with:
  - `import { createFileRoute } from "@tanstack/react-router";`
  - `import { UsersPage } from "@/modules/admin/UsersPage";` (the page component lives in the modules folder per the Settings2faPage precedent at `apps/web/src/routes/settings/2fa.tsx` → `apps/web/src/modules/auth/Settings2faPage.tsx`).
  - `validateSearch` accepting `{ page?: number; page_size?: number; search?: string; sort_by?: "email" | "role" | "created_at" | "last_active_at"; sort_order?: "asc" | "desc" }` — typed search params (lookup `apps/web/src/routes/login.tsx:172-179` for the `validateSearch` shape; this is the binding precedent for typed search params).
  - The route's `component` wraps the page in `<AuthGate>` AND an additional inline `isAdmin` check: if `!isAdmin`, render `<Navigate to="/" replace />` per the `apps/web/src/routes/login.tsx` next-param-redirect precedent. (Backend already returns 403 on non-admin; the frontend guard avoids the flicker of a forbidden screen for non-admin users who land on the URL directly.)
- And `apps/web/src/modules/admin/UsersPage.tsx` MUST exist as a NEW file with:
  - The `UsersPage` named export (matching the `Sessions` function at `routes/settings/sessions.tsx:14` shape).
  - The header `<h1>{t("admin.users.title")}</h1>` + `<p className="text-sm text-muted-foreground">{t("admin.users.description")}</p>` block (mirrors `sessions.tsx:46-49` verbatim).
  - The `<AdminTabs activeTab="users" />` component (NEW shared component at `apps/web/src/modules/admin/AdminTabs.tsx` — see AC-5 below).
  - The search input controlled by `search` query-string param, debounced 250ms via `useDebouncedValue` if such helper exists (search the codebase first; if no debounce helper, fall back to plain `onChange` without debounce — debounce is a nice-to-have, not a v1 blocker).
  - The page-size `<select>` with `[25, 50, 100, 200]` options (default to whatever the URL search param says, else 50 to match API default).
  - The sortable `<table>` mirroring `sessions.tsx:62-94` shape but with the 7 columns + 4 sortable headers per the story foundation. Sortable header click handler updates `sort_by` + `sort_order` URL params via `useNavigate({to: "/admin/users", search: (prev) => ({...prev, sort_by, sort_order}), replace: true})`. The visual indicator for current sort is a tiny `↑` / `↓` UTF-8 arrow appended to the column header text (no SVG icon library import — the existing UserMenu uses inline UTF-8 for the same reason; keep visual baseline minimal).
  - The footer pagination strip with Previous + Next buttons (disabled at boundaries: Previous disabled when `page == 1`; Next disabled when `page * page_size >= total`).
  - **No checkbox, no bulk-action UI, no per-row action menu.** Per AC-10 negative AC enforcement.
- And the page consumes the React Query hook `useAdminUsers({page, page_size, search, sort_by, sort_order})` from `@/modules/admin/hooks/useAdminUsers` (see AC-6).
- And the page handles loading + error states via `<LoadingState variant="spinner" />` (existing component at `apps/web/src/ui/custom/LoadingState.tsx` per `sessions.tsx:25` precedent) + an inline error message `{t("admin.users.error_loading")}` on `error != null`.

**AC-5 — Shared `AdminTabs.tsx` component for the admin-section tab strip.**

- Given the architecture decision to ship two admin tabs (Users + Invites) per FR5-ADMIN-1, and the staging across Stories 8.2 (Users) + 8.6 (Invites),
- When Story 8.2 ships,
- Then `apps/web/src/modules/admin/AdminTabs.tsx` MUST exist as a NEW component file (~50 LOC max) exporting `AdminTabs({activeTab: "users" | "invites"})` with:
  - Two tab buttons rendered as a horizontal `<nav role="tablist">` per the WAI-ARIA tabs pattern (NOT a `<ul>` — tablist is the semantic surface that vitest + Playwright role-queries can target).
  - Tab 1 "Users" — clickable `<Link to="/admin/users">` styled as a tab button (active styles applied when `activeTab === "users"`); always visible.
  - Tab 2 "Invites" — rendered with `aria-disabled="true"` + `tabindex="-1"` + a tooltip `title={t("admin.tabs.invites_coming_soon")}` (the tooltip is a plain HTML `title` attribute for v1 — not a Radix tooltip; minimum-surface). The button does NOT navigate (`onClick={(e) => e.preventDefault()}`); the visual style is grayed-out per `text-muted-foreground opacity-50` Tailwind classes (mirrors the existing disabled-button styling pattern; search the codebase for `aria-disabled` to find the closest precedent; if none, document the chosen pattern inline).
  - Story 8.6 will modify this component to enable the Invites tab + remove the disabled styling — the modification is a 5-line touch when 8.6 ships. The component shape (props, render structure) does NOT change in 8.6.
- And the component MUST be importable via `import { AdminTabs } from "@/modules/admin/AdminTabs"` — no default export.

**AC-6 — React Query hook `useAdminUsers` at NEW `apps/web/src/modules/admin/hooks/useAdminUsers.ts`.**

- Given the existing `useSessions` hook pattern at `apps/web/src/modules/catalog/hooks/useSessions.ts:1-15` (note: the path is `modules/catalog/hooks/` because that's where sessions hooks accidentally landed in Story 6.x; Story 8.2 places the new admin hook under `modules/admin/hooks/` which is the cleaner location going forward — no migration of the old path required),
- When Story 8.2 ships,
- Then `apps/web/src/modules/admin/hooks/useAdminUsers.ts` MUST exist as a NEW file (~25 LOC) with:
  - Default export `useAdminUsers` (named export per project convention — verify by checking the `useSessions` export shape; if it's `export function useSessions(...)` then mirror that).
  - Signature: `useAdminUsers(params: { page: number; page_size: number; search?: string; sort_by?: "email" | "role" | "created_at" | "last_active_at"; sort_order?: "asc" | "desc" })`.
  - Returns `useQuery<AdminUsersListResponse>` per the `useSessions:7-10` shape: `{queryKey: ["admin", "users", params], queryFn: () => api<AdminUsersListResponse>(...)}`.
  - The `queryFn` constructs the URL via `URLSearchParams` to handle undefined/empty params (e.g. `search=""` should NOT be sent — coalesce to omitted query param; same for `sort_by=undefined`). The constructed URL is `/admin/users?${params.toString()}` (the existing `api()` helper prepends `/api/`).
- And the hook MUST tolerate the `search` debouncing concern from AC-4 — the hook itself does NOT debounce; the page does (or doesn't, per the v1-blocker note above). The hook treats every param-change as a new query-key.
- And the hook does NOT prefetch the next page (no prefetch in v1 — operator-tier UX, the latency cost is tolerable). Future story may add `useQueryClient().prefetchQuery(...)` on Next button hover, NOT this story.

**AC-7 — Playwright visual spec `apps/web/tests/visual/admin-users.spec.ts` (NEW; 3 baseline scenarios + FR5-ADMIN-4 negative AC + tab-strip verification).**

- Given the existing Playwright visual-test pattern at `apps/web/tests/visual/sessions.spec.ts:1-78`,
- When Story 8.2 ships,
- Then `apps/web/tests/visual/admin-users.spec.ts` MUST exist as a NEW file with:
  - A `stubAdminUsersPage(page)` helper at the top (mirrors `stubSessionsPage` at sessions.spec.ts:5-50) that:
    - Stubs `/api/auth/me` → 200 with `role: "admin"`.
    - Stubs `/api/admin/users**` → returns a configurable payload (the helper accepts a `payload` arg defaulting to a 5-row fixture; tests override for empty/many states).
  - **Test 1 — `admin-users-empty.spec.ts` baseline** (`/admin/users` with `total=0&items=[]` stub): asserts `<h1>` heading visible + table empty-state message (`t("admin.users.empty")`) visible + `await expect(page).toHaveScreenshot("admin-users-empty.png", { fullPage: true })`.
  - **Test 2 — `admin-users-one-row` baseline**: stub `total=1&items=[seeded-admin-row]` → screenshot `admin-users-one-row.png` (the seeded admin appears as expected; verifies the single-row table layout doesn't collapse weirdly).
  - **Test 3 — `admin-users-many-rows` baseline**: stub `total=137&items=[25 deterministic rows for page 1]` → screenshot `admin-users-many-rows.png`. The fixture covers the full table: rows with all column variations (one row `is_active=false` with grayed-out styling per UsersPage's visual treatment, one row `totp_enabled=true` with a tiny ✓ badge, one row `last_active_at=NULL` rendered as `—`).
  - **Test 4 — `admin-users-no-bulk-controls` (FR5-ADMIN-4 negative AC)** explicitly named to make the constraint visible in test reports: stub `total=10&items=[...]` → assert ALL of the following return count 0:
    - `page.locator('table input[type="checkbox"]')` — no row checkboxes.
    - `page.locator('thead input[type="checkbox"]')` — no select-all checkbox.
    - `page.getByRole('button', { name: /bulk/i })` — no bulk-action button (English-locale).
    - `page.getByRole('button', { name: /wszystkie|zaznacz wszyst/i })` — no Polish bulk-action button (project tests run under `pl-PL` locale per playwright.config.ts).
    - `page.getByRole('menuitem', { name: /bulk|zbiorow/i })` — no bulk menu item.
  - **Test 5 — `admin-users-tab-strip-shows-invites-disabled` (AdminTabs disabled-state regression guard)**: navigate to `/admin/users`, assert `page.getByRole('tab', { name: /Invites|Zaproszenia/i }).getAttribute('aria-disabled')` === `"true"`. This prevents Story 8.6 (or any future change) from silently enabling the tab via a global CSS regression while leaving the disabled `aria-disabled` semantic — the tab MUST be disabled until 8.6's AC explicitly opts in.
- And the spec MUST run under the existing `playwright.config.ts` locale=`pl-PL` (the project's default) — visual baselines are PL-locale screenshots. If running under en-locale during dev is needed, document the override in the spec header.
- And the spec MUST pass `cd apps/web && npm run test:visual -- admin-users` after first-time baseline generation via `npm run test:visual -- --update-snapshots admin-users`. The first run generates the 3 baselines; subsequent CI runs compare against them.

**AC-8 — i18n keys in both `en.json` and `pl.json` for the admin namespace.**

- Given the existing i18n structure at `apps/web/src/locales/en.json:1-320` + `apps/web/src/locales/pl.json:1-320`,
- When Story 8.2 ships,
- Then both locale files MUST gain the following NEW keys (insertion location: after the `auth.2fa.*` block, before any deeper-nested catalog/sot keys; pick a stable alphabetical position):

  | Key | English text | Polish text |
  |---|---|---|
  | `admin.menu_link` | Admin panel | Panel administratora |
  | `admin.tabs.users` | Users | Użytkownicy |
  | `admin.tabs.invites` | Invites | Zaproszenia |
  | `admin.tabs.invites_coming_soon` | Coming in Story 8.6 — admin invite list + revoke UI | Wkrótce w Story 8.6 — lista i odwoływanie zaproszeń |
  | `admin.users.title` | Users | Użytkownicy |
  | `admin.users.description` | All registered users. Sort by any header, filter by email, paginate. Per-user actions ship in the next story. | Wszyscy zarejestrowani użytkownicy. Sortuj po nagłówku, filtruj po e-mailu, paginuj. Akcje per-użytkownik dostarczone w kolejnej historii. |
  | `admin.users.search_placeholder` | Search by email… | Szukaj po e-mailu… |
  | `admin.users.page_size_label` | Rows per page | Wiersze na stronę |
  | `admin.users.column_email` | Email | E-mail |
  | `admin.users.column_display_name` | Display name | Nazwa wyświetlana |
  | `admin.users.column_role` | Role | Rola |
  | `admin.users.column_totp` | 2FA | 2FA |
  | `admin.users.column_active` | Active | Aktywny |
  | `admin.users.column_created_at` | Created | Utworzony |
  | `admin.users.column_last_active_at` | Last active | Ostatnia aktywność |
  | `admin.users.totp_enabled_short` | ✓ | ✓ |
  | `admin.users.totp_disabled_short` | — | — |
  | `admin.users.active_yes` | Yes | Tak |
  | `admin.users.active_no` | No | Nie |
  | `admin.users.empty` | No users match this filter. | Brak użytkowników pasujących do filtru. |
  | `admin.users.error_loading` | Could not load users. Refresh the page or check the API. | Nie udało się załadować użytkowników. Odśwież stronę lub sprawdź API. |
  | `admin.users.pagination_label` | Showing {{first}}–{{last}} of {{total}} | Pokazuję {{first}}–{{last}} z {{total}} |
  | `admin.users.pagination_previous` | Previous | Poprzednia |
  | `admin.users.pagination_next` | Next | Następna |

- And the `i18next` `t(...)` call discipline is preserved (no inline string concatenation — every user-visible string goes through `t()`).
- And the Polish translations MUST use proper diacritics (`ą`, `ę`, `ć`, `ł`, `ó`, `ś`, `ź`, `ż`) per the user-instruction language directive — verify by grepping the new pl.json keys for the substring matches: `Użytkownicy`, `Aktywny`, `Nieaktywny`, `Wkrótce`, `Wiersze`, `Sortuj`.
- And the en.json + pl.json key counts MUST match exactly post-merge (run `jq 'keys | length' en.json pl.json` after the edit — both files MUST report the same integer; mismatched key sets are a pre-merge blocker per existing project discipline).

**AC-9 — Frontend vitest tests at NEW `apps/web/src/modules/admin/UsersPage.test.tsx` (4 named V1-V4 tests).**

- Given the existing vitest pattern at `apps/web/src/modules/auth/Settings2faPage.test.tsx` (Story 7.5 precedent),
- When Story 8.2 ships,
- Then `apps/web/src/modules/admin/UsersPage.test.tsx` MUST exist as a NEW file with 4 tests:

  | # | Name | Asserts |
  |---|------|---------|
  | V1 | `renders table with all 7 columns for a non-empty response` | Mock `useAdminUsers` to return `{total: 1, items: [seed admin row], page: 1, page_size: 50}`. Render `<UsersPage />`. Assert ALL 7 column headers are visible by `t()` key lookup (use `vi.mock` on `react-i18next` to return the key as the text per project precedent in `Settings2faPage.test.tsx`). |
  | V2 | `renders empty-state message when total=0` | Mock with `{total: 0, items: [], ...}`. Assert `screen.getByText("admin.users.empty")` is in the document; assert NO `<tr>` rows in `<tbody>`. |
  | V3 | `renders error message when query.error is non-null` | Mock the hook to return `{isError: true, error: new Error("boom")}`. Assert `screen.getByText("admin.users.error_loading")` is visible. |
  | V4 | `renders zero checkboxes and zero bulk-action buttons (FR5-ADMIN-4 negative AC)` | Mock with `{total: 5, items: [5 deterministic rows], page: 1, page_size: 50}`. Render. Assert `screen.queryAllByRole("checkbox").length === 0` AND `screen.queryAllByRole("button", { name: /bulk|select all/i }).length === 0`. **Binding negative AC verification** at the unit-test tier (Playwright spec AC-7 Test 4 is the integration-tier mirror). |

- And the tests MUST use the `afterEach(cleanup)` pattern from the project's `vitest.setup.ts` (already registered globally per Story 5.10 / commit `a026e97` per memory `feedback_vitest_manual_cleanup` — no per-file `afterEach` needed).
- And `cd apps/web && npm run vitest -- UsersPage` MUST be green for all 4 tests. Current vitest baseline per Story 7.5 close-out: 343 tests; Story 8.2 adds 4 → ~347.

**AC-10 — Negative AC enforcement (FR5-ADMIN-4): zero bulk-select / bulk-action surfaces.**

- Given the FR5-ADMIN-4 deliberate exclusion at PRD §1196 verbatim + the binding architecture phrase at Decision I §1630 verbatim "Bulk deactivation explicitly NOT in panel UI (FR5-ADMIN-4) — DB-direct only",
- When Story 8.2 ships,
- Then the rendered DOM of `/admin/users` (verifiable via both vitest V4 AND Playwright Test 4 above) MUST satisfy ALL of the following:
  - ZERO `<input type="checkbox">` elements anywhere in the page (table header, table body, page chrome).
  - ZERO buttons with an accessible name matching `/bulk|select all|zaznacz wszyst|wszystkie zaznaczone|operacje grupowe/i` (English + Polish bulk-action lexicon).
  - ZERO `<menu>` / `<menuitem>` with bulk-related accessible names.
  - ZERO `<th>` containing a bulk-select checkbox.
- And the absence is enforced at BOTH the unit (vitest V4) AND the integration (Playwright Test 4) tier — single-tier enforcement is insufficient because vitest can miss CSS-rendering issues + Playwright can miss conditional-render branches that vitest catches.
- And a regression guard at the spec-text tier: `grep -rn "Bulk\|bulk-select\|bulk_action\|selectAll" apps/web/src/modules/admin/ apps/web/src/routes/admin/` MUST return ZERO matches (the codebase contains no string or identifier suggesting bulk operations in the admin module — if a future PR introduces one, this grep catches it immediately).
- This AC is a HARD BLOCKER for the dev commit. A single checkbox in the rendered DOM is a pre-merge fail.

**AC-11 — Pre-flight grep checklist (Story 8.2 close-out invariants, per Story 8.1 AC-10 precedent).**

Before the dev commit lands, the developer agent MUST run the following greps and confirm each returns the expected result:

1. `grep -rn "GET /api/admin/users\|@router.get.*users" apps/api/app/modules/admin/router.py` returns ≥1 line matching the new endpoint (AC-1 enforcement).
2. `grep -rn "password_hash\|totp_secret" apps/api/app/modules/admin/users_schemas.py` returns ZERO matches (AC-2 hygiene-rule enforcement; the schema MUST NOT mention those columns at all, even in comments — the only acceptable mention is in the file-level docstring's hygiene-rule paragraph itself which uses the strings as documentation; if the grep finds a hit, verify it's the docstring line and only the docstring line).
3. `grep -rn "Hygiene rule:" apps/api/app/modules/admin/users_schemas.py` returns ≥1 line (the binding docstring statement from AC-2 — confirms the hygiene-rule paragraph landed).
4. `grep -rn "AdminTabs\|activeTab" apps/web/src/modules/admin/AdminTabs.tsx` returns ≥3 matches (component name + `activeTab` prop usage at AC-5 binding).
5. `grep -rn "input\[type=.checkbox.\]\|select all\|bulk" apps/web/src/modules/admin/ apps/web/src/routes/admin/ apps/web/tests/visual/admin-users.spec.ts` ONLY matches inside `admin-users.spec.ts` (the spec file LEGITIMATELY mentions these strings inside the negative-AC assertions; ALL OTHER matches in the source-code paths are pre-merge BLOCKERS).
6. `grep -rn "AdminUserListItem\|AdminUserListResponse" apps/api/app/modules/admin/` returns ≥3 matches (schema definitions in `users_schemas.py` + endpoint import in `router.py` + at least one test reference).
7. `grep -rn "useAdminUsers" apps/web/src/modules/admin/` returns ≥2 matches (hook export + UsersPage import).
8. `grep -rn "admin.menu_link\|admin.users.title" apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns ≥4 matches (the 2 keys × 2 locale files = 4 lines minimum; AC-8 enforcement).
9. `jq 'keys | length' apps/web/src/locales/en.json` and `jq 'keys | length' apps/web/src/locales/pl.json` MUST return the SAME integer (en/pl key-set parity, AC-8 enforcement).
10. `grep -rn "aria-disabled" apps/web/src/modules/admin/AdminTabs.tsx` returns ≥1 line (the disabled Invites tab semantic, AC-5 enforcement).
11. `cd apps/api && .venv/bin/pytest tests/test_admin_users_list.py -v` returns 8/8 green (AC-3 enforcement).
12. `cd apps/web && npm run vitest -- UsersPage` returns 4/4 green (AC-9 enforcement).
13. `cd apps/web && npm run test:visual -- admin-users` returns 5/5 green (AC-7 enforcement — 3 baselines + 1 negative-AC + 1 tab-disabled regression).
14. `infra/scripts/check-all.sh` returns ALL 13 stages green end-to-end (the 13-stage baseline established by Story 8.1's `check-all.sh` extensions stays at 13/13).
15. `git log --oneline --decorate -5` shows the Story 8.2 dev commit as a single squashed atomic commit (`feat(api,web,tests): admin users tab (Story 8.2)` or similar prefix).

All 15 checks are AC-11 binding; a failure on any of them is a pre-merge blocker.

## Tasks / Subtasks

- [ ] **T1 — Author Pydantic schemas at NEW `apps/api/app/modules/admin/users_schemas.py`** (AC-2)
  - [ ] T1.1 Read `apps/api/app/modules/invite/admin_schemas.py:1-101` end-to-end for the docstring + ConfigDict + field-order conventions.
  - [ ] T1.2 Create the new file with `AdminUserListItem` (8 fields) + `AdminUserListResponse` (4 fields) per the AC-2 shape.
  - [ ] T1.3 Verify import path: `cd apps/api && .venv/bin/python -c "from app.modules.admin.users_schemas import AdminUserListItem, AdminUserListResponse; print(AdminUserListItem.model_fields.keys())"` prints the 8 field names in declared order.

- [ ] **T2 — Add `GET /api/admin/users` endpoint to `apps/api/app/modules/admin/router.py`** (AC-1)
  - [ ] T2.1 Read `apps/api/app/modules/admin/router.py:1-137` (the existing file) to understand the surrounding endpoint conventions + imports.
  - [ ] T2.2 Read `apps/api/app/modules/invite/admin_router.py:97-156` for the page/page_size/sort + ilike + ordering pattern (the closest existing precedent).
  - [ ] T2.3 Add the new endpoint with the AC-1 query params, the search ilike filter, the sort_by Literal validation, the NULLs-LAST sort logic, and the projection list comprehension.
  - [ ] T2.4 Verify locally: `cd apps/api && .venv/bin/python -c "from app.modules.admin.router import router; print([r.path for r in router.routes])"` includes `/api/admin/users` in the route list.

- [ ] **T3 — Write backend tests `apps/api/tests/test_admin_users_list.py`** (AC-3)
  - [ ] T3.1 Read `apps/api/tests/test_invite_admin.py:1-100` end-to-end for the conftest `isolated_client` consumption + the cookie-minting + the autouse table-clear discipline.
  - [ ] T3.2 Author the `_seed_members` helper at the top of the file (returns list of UUIDs).
  - [ ] T3.3 Author the `_clear_user_and_audit_tables` autouse fixture preserving the seeded admin row.
  - [ ] T3.4 Implement T1-T8 per the AC-3 table.
  - [ ] T3.5 Verify: `cd apps/api && .venv/bin/pytest tests/test_admin_users_list.py -v` returns 8/8 green.
  - [ ] T3.6 Verify the full backend suite: `cd apps/api && .venv/bin/pytest -v` returns ALL tests green (~708 total).

- [ ] **T4 — Author api-types entries in `apps/web/src/lib/api-types.ts`** (UsersPage prereq)
  - [ ] T4.1 Read `apps/web/src/lib/api-types.ts:180-200` (the Sessions block) to find the insertion point.
  - [ ] T4.2 Insert NEW `// --- Admin users (Story 8.2) ---` section header + `AdminUser` interface + `AdminUsersListResponse` interface after the Sessions block.
  - [ ] T4.3 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T5 — Author `useAdminUsers` hook at NEW `apps/web/src/modules/admin/hooks/useAdminUsers.ts`** (AC-6)
  - [ ] T5.1 Create the new directory `apps/web/src/modules/admin/hooks/`.
  - [ ] T5.2 Read `apps/web/src/modules/catalog/hooks/useSessions.ts:1-15` for the exact `useQuery` shape.
  - [ ] T5.3 Author the hook per AC-6 with URLSearchParams construction + undefined-param skipping.
  - [ ] T5.4 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T6 — Author `AdminTabs.tsx` at NEW `apps/web/src/modules/admin/AdminTabs.tsx`** (AC-5)
  - [ ] T6.1 Read `apps/web/src/shell/ModuleRail.tsx:8-60` for the Link + active-class pattern.
  - [ ] T6.2 Author the component with the tablist semantic + aria-disabled Invites tab.
  - [ ] T6.3 Verify the component renders standalone (no test in this story — V5 visual + V1 vitest cover this indirectly).

- [ ] **T7 — Author `UsersPage.tsx` at NEW `apps/web/src/modules/admin/UsersPage.tsx`** (AC-4)
  - [ ] T7.1 Read `apps/web/src/routes/settings/sessions.tsx:1-110` for the page-component shape.
  - [ ] T7.2 Implement the page per AC-4 with the header, AdminTabs, search input, page-size selector, sortable table, pagination strip.
  - [ ] T7.3 Wire `useAdminUsers` consumption + loading/error states.
  - [ ] T7.4 **Critical:** NO checkbox, NO bulk-action UI, NO per-row action menu (AC-10 enforcement at code-author time).
  - [ ] T7.5 Verify `cd apps/web && npm run typecheck` + `npm run lint` are green.

- [ ] **T8 — Author route file `apps/web/src/routes/admin/users.tsx`** (AC-4)
  - [ ] T8.1 Read `apps/web/src/routes/settings/sessions.tsx:1-15` for the route-file shape.
  - [ ] T8.2 Read `apps/web/src/routes/login.tsx:172-179` for the validateSearch pattern.
  - [ ] T8.3 Author the route file (~30 LOC) wrapping UsersPage in AuthGate + inline isAdmin redirect.

- [ ] **T9 — i18n keys in en.json + pl.json** (AC-8)
  - [ ] T9.1 Insert the 23 NEW keys at a stable alphabetical position after `auth.2fa.*` in BOTH locale files.
  - [ ] T9.2 Verify Polish diacritics: `grep -E "Użytkownicy|Wiersze|Wkrótce|Sortuj|Zaproszenia" apps/web/src/locales/pl.json` returns ≥5 lines.
  - [ ] T9.3 Verify key-set parity: `jq 'keys | length' apps/web/src/locales/en.json` and `apps/web/src/locales/pl.json` return the SAME integer.

- [ ] **T10 — Modify `apps/web/src/shell/UserMenu.tsx` to add the Admin panel link** (story foundation §10)
  - [ ] T10.1 Read `apps/web/src/shell/UserMenu.tsx:1-80` for the existing isAdmin-gated DropdownMenuItem pattern.
  - [ ] T10.2 Add ONE new `isAdmin && <DropdownMenuItem render={<a href="/admin/users" />}>{t("admin.menu_link")}</DropdownMenuItem>` block.
  - [ ] T10.3 Verify the existing `UserMenu.test.tsx` stays green (the test asserts existing menu items; adding a new item under isAdmin guard may require a small test update if the test asserts the EXACT count of menu items — check the test file and adjust if needed).

- [ ] **T11 — Write vitest tests at NEW `apps/web/src/modules/admin/UsersPage.test.tsx`** (AC-9)
  - [ ] T11.1 Read `apps/web/src/modules/auth/Settings2faPage.test.tsx` for the mock-hook + render-with-i18n-passthrough pattern.
  - [ ] T11.2 Implement V1-V4 per the AC-9 table.
  - [ ] T11.3 Verify `cd apps/web && npm run vitest -- UsersPage` returns 4/4 green.

- [ ] **T12 — Write Playwright spec at NEW `apps/web/tests/visual/admin-users.spec.ts`** (AC-7)
  - [ ] T12.1 Read `apps/web/tests/visual/sessions.spec.ts:1-78` for the stub helper + screenshot pattern.
  - [ ] T12.2 Implement `stubAdminUsersPage(page, payload?)` helper + 5 tests per AC-7.
  - [ ] T12.3 First-time baseline generation: `cd apps/web && npm run test:visual -- --update-snapshots admin-users`.
  - [ ] T12.4 Verify regression mode: `cd apps/web && npm run test:visual -- admin-users` returns 5/5 green against the freshly-generated baselines.

- [ ] **T13 — Run AC-11 pre-flight grep checklist** (AC-11)
  - [ ] T13.1 Execute all 15 checks; capture grep outputs.
  - [ ] T13.2 If any check fails, fix the underlying gap before committing.

- [ ] **T14 — Dev commit + sprint-status flip** (close-out)
  - [ ] T14.1 Single squashed `feat(api,web,tests): admin users tab (Story 8.2)` commit covering all ~9 NEW files + ~4 modified files. Commit body cites Decision I + epics §1762-1774 + the FR5-ADMIN-4 negative AC enforcement.
  - [ ] T14.2 Commit message ends with the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
  - [ ] T14.3 Update sprint-status: flip `8-2-admin-users-tab-paginated-list` from `ready-for-dev` → `review` (NOT `done` — Codex review comes next per Epic 7 retro action item §3 fixed-point loop discipline).
  - [ ] T14.4 Run `infra/scripts/deploy.sh` per `feedback_auto_deploy_dev` after merge to main (auto-deploy to `.190` is mandatory for code commits; doc-only skips apply).

## Dev Notes

### Architectural anchors

- **Decision I** (`_bmad-output/planning-artifacts/architecture.md:1601-1630`) — the binding spec for the `is_active` + `last_active_at` columns AND the FR5-ADMIN-4 negative bound at §1630 verbatim. Story 8.2 makes the columns visible; Story 8.3 makes them mutable. Read in full before T2 + T7.
- **Epics anchor** (`_bmad-output/planning-artifacts/epics.md:1762-1774`) — the Story 8.2 acceptance check shape with the verbatim column-set binding + the negative AC for FR5-ADMIN-4. Read in full to confirm scope.
- **FR5-ADMIN-1 + FR5-ADMIN-4** (`_bmad-output/planning-artifacts/prd.md:1193 + 1196`) — the binding PRD-tier requirements; FR5-ADMIN-4 is the deliberate exclusion that Story 8.2 architecturally enforces.
- **Story 8.1 conftest promotion** (`_bmad-output/implementation-artifacts/8-1-alembic-0014-is-active-last-active-middleware.md` AC-7) — Story 8.2 is the binding consumer of the new `isolated_client` fixture; do NOT copy the per-file fixture into the new test file.
- **FR5-MEMBER-2 dependency contract** (`architecture.md:1486-1493`) — the per-route dependency table binds `current_admin` on `/api/admin/users`; member-authenticated requests MUST return 403. T3.4 (T8 test) is the binding verifier.

### Critical files to read before touching

- `apps/api/app/modules/admin/router.py:1-137` — the file Story 8.2 modifies; understand the existing audit + sentry-test endpoint conventions before adding a third.
- `apps/api/app/modules/invite/admin_router.py:97-156` — the closest precedent for paginated admin list (page/page_size + filter + ordering); Story 8.2 mirrors this shape.
- `apps/api/app/modules/invite/admin_schemas.py:1-101` — the schema-file precedent Story 8.2's `users_schemas.py` mirrors.
- `apps/api/app/core/db/models/_user.py:1-40` — the SQLModel Story 8.2 reads from; the 8 column names are bound to this file's field declarations.
- `apps/api/app/core/auth/dependencies.py` (just `current_admin` and `_decode`) — the auth contract Story 8.2 inherits unchanged.
- `apps/api/tests/test_invite_admin.py:1-100` — the test-pattern precedent for admin endpoints with cookie-minting + pagination + ilike search assertions.
- `apps/api/tests/conftest.py:64-124` — the `isolated_client` fixture Story 8.2 consumes.
- `apps/web/src/routes/settings/sessions.tsx:1-110` — the page-component precedent Story 8.2's `UsersPage.tsx` mirrors.
- `apps/web/src/routes/login.tsx:172-179` — the `validateSearch` pattern for typed search params.
- `apps/web/src/modules/catalog/hooks/useSessions.ts:1-15` — the React Query hook precedent.
- `apps/web/src/shell/UserMenu.tsx:1-80` — the file Story 8.2 modifies for the admin-panel menu link.
- `apps/web/tests/visual/sessions.spec.ts:1-78` — the Playwright spec precedent.
- `apps/web/src/modules/auth/Settings2faPage.test.tsx` — the vitest precedent.

### Library/framework versions to respect

- **FastAPI 0.115+** — `Query(default=..., ge=..., le=...)` is the canonical query-param validation API; `Literal[...]` in the Query type is auto-converted to an OpenAPI enum.
- **SQLAlchemy 2.x** — `User.email.ilike(f"%{search}%")` is the dialect-portable case-insensitive substring match (SQLite + Postgres both honor it). `User.last_active_at.is_(None)` is the NULL check (NOT `== None` which generates `IS NULL` but triggers a linter warning); for NULLs-LAST ordering use `User.last_active_at.is_(None).asc()` as primary key + then the requested column.
- **Pydantic 2.9** — `ConfigDict(frozen=True)` is the v2 equivalent of v1's `class Config: allow_mutation = False`; matches the `InviteListItem` precedent.
- **SQLModel 0.0.22** — `session.exec(select(User).where(...).order_by(...).offset(...).limit(...)).all()` is the canonical paginated read; `func.count()` for the total count.
- **TanStack Router 1.x** — `createFileRoute("/admin/users")` is the file-route declaration; `validateSearch: (search) => ({...})` accepts a typed search-param object; `useSearch({ from: "/admin/users" })` reads the typed object back in the component.
- **TanStack Query 5.x** — `useQuery({queryKey, queryFn})` is the v5 API (v5 dropped `queryFn` as a positional arg; the object form is binding).
- **Vitest 2.x** — `vi.mock("@/modules/admin/hooks/useAdminUsers", () => ({ useAdminUsers: vi.fn() }))` is the canonical module-mock; `vi.mocked(useAdminUsers).mockReturnValue(...)` per-test.
- **Playwright 1.x** — `page.route(url, route => route.fulfill({...}))` for stubs; `expect(page).toHaveScreenshot(name, { fullPage: true })` for visual baselines; `page.getByRole("tab", { name: /.../ })` for tablist queries (NOT `page.locator("[role=tab]")` — role-query is more robust).

### File structure requirements

- **NEW schema MUST live at `apps/api/app/modules/admin/users_schemas.py`** per the `invite/admin_schemas.py` peer-of-router precedent. Do NOT inline the schemas into `admin/router.py` (the existing AuditLogEntry inline class at `admin/router.py:84-105` is a legacy shape from the pre-Init-5 era and is NOT the precedent Story 8.2 follows).
- **NEW endpoint MUST live in `apps/api/app/modules/admin/router.py`** (the existing module), not in a NEW `users_router.py`. The existing module is the canonical home for cross-cutting admin endpoints (audit, sentry-test, now users); per-resource sub-routers (`share/admin_router.py`, `invite/admin_router.py`, `sot/admin_router.py`) exist because those resources have CRUD endpoints — users will gain CRUD in Story 8.3+ and MAY then be promoted to a `users/admin_router.py` sub-router with a refactor pass; that promotion is NOT a Story 8.2 deliverable.
- **NEW frontend page MUST live at `apps/web/src/modules/admin/UsersPage.tsx`** per the `modules/auth/Settings2faPage.tsx` precedent — the routes/ folder hosts thin file-route declarations; the modules/ folder hosts the actual page components. This split mirrors the project's existing convention.
- **NEW frontend route MUST live at `apps/web/src/routes/admin/users.tsx`** per TanStack Router's file-route convention (`/admin/users` URL ↔ `routes/admin/users.tsx` file).
- **NEW tests MUST follow project naming:** backend `test_admin_users_list.py` (per `test_admin_audit.py` precedent); frontend `UsersPage.test.tsx` (next to the component, per `Settings2faPage.test.tsx` precedent); Playwright `admin-users.spec.ts` (under `tests/visual/` per `sessions.spec.ts` precedent).

### Testing requirements

- **AC-3 backend tests T1-T8 MUST pass in isolation AND together.** Run `pytest tests/test_admin_users_list.py -v` (isolation) and `pytest tests/ -v -k "admin_users"` (together-with-related) to catch ordering / fixture-bleed issues. The `_clear_user_and_audit_tables` autouse fixture is the binding isolation primitive.
- **AC-9 vitest tests V1-V4 MUST pass in isolation AND together.** The global `afterEach(cleanup)` in `vitest.setup.ts` handles inter-test isolation per the project's existing setup (per memory `feedback_vitest_manual_cleanup`).
- **AC-7 Playwright tests Tests 1-5 MUST pass in isolation AND together against fresh baselines.** First-time baseline generation via `--update-snapshots`; subsequent runs against the committed baselines.
- **`infra/scripts/check-all.sh` 13/13 green** — the canonical pre-commit gate established at Story 8.1's `check-all.sh` extensions stays at 13/13. Story 8.2 does NOT add new stages.
- **AC-10 negative AC verification** is dual-tier (vitest V4 + Playwright Test 4) — both MUST be green; single-tier failure is a pre-merge blocker.
- **NO Codex P2 fix-ups expected on the read endpoint itself** — a single SELECT-with-filter-and-sort-and-pagination endpoint has minimal failure modes (no concurrency, no state mutation, no external dependency). **HOWEVER:** Codex may surface fix-ups on (a) the NULLs-LAST sort logic if the SQLAlchemy expression compiles differently across SQLite + Postgres dialects; (b) the search ilike performance if the email column doesn't have an index (the User table has `email: str = Field(unique=True, index=True)` per `_user.py:24` — verified, the unique index covers ilike but with a leading wildcard `%` it's a full scan; for admin-bounded datasets O(thousands) this is acceptable, flag as P3 if Codex calls it out); (c) the frontend pagination boundary handling (off-by-one risks at `page * page_size > total`); (d) the AdminTabs disabled-tab a11y if the `aria-disabled="true"` semantic is missing a complementary `aria-controls` or `aria-selected="false"` per WAI-ARIA tablist guidance. Expect 0-3 fix-ups per Epic 7's 100% intercept rate baseline.

### Previous story intelligence (Stories 8.1 + 7.5 + 6.3 carryover)

- **Story 8.1 `LastActiveMiddleware` runtime behavior**: when the operator browses `/admin/users` after logging in, their OWN row's `last_active_at` will be populated within the first request (the middleware UPDATE fires post-handler). The Story 8.2 test T2 (75 seeded members + 1 admin) MUST account for the admin's `last_active_at` being populated by the test client's request — assert per-row last_active_at is the seeded value (NULL for the 75 members) regardless of the admin's own column being touched by the request itself.
- **Story 8.1 isolated_client fixture** is the binding consumer pattern. The fixture name is `isolated_client` (NOT plain `client`) per the Story 8.1 AC-7 footnote — `client` is already bound to a session-scoped TestClient in the existing conftest; Story 8.2 MUST use `isolated_client` to get the per-test fakeredis + tmpdir SQLite isolation.
- **Story 6.3 invite-admin pagination shape**: the `(page, page_size)` + `(total, items)` envelope Story 8.2 mirrors. The Story 6.3 endpoint loads ALL rows then filters in Python (per a documented O(thousands) admin-bounded justification); Story 8.2 differs by pushing the filter + sort to SQL (the `is_active`/`role`/`email`/`last_active_at` columns are all indexed-or-cheap to scan, and the ilike filter is dialect-portable). The divergence is intentional: Story 6.3 needs computed-status which is Python-only; Story 8.2 has no derived sortable columns so SQL-side filtering is the natural fit.
- **Story 7.5 reauth-modal scope discipline** — Story 8.2 ships UI for read-only column display; ANY write action (deactivate, role change, force logout) is OUT OF SCOPE per Story 8.3 ownership. The per-row action column is NOT added in Story 8.2 — Story 8.3 adds it, and the visual baseline Story 8.2 generates becomes the BEFORE snapshot Story 8.3 updates AFTER. This pattern (consecutive stories own consecutive baselines) was established in Stories 7.2 → 7.5 (enrollment baseline → enrollment-plus-disable baseline).
- **Vitest global cleanup** (per memory `feedback_vitest_manual_cleanup`): the `vitest.setup.ts` registers `afterEach(cleanup)` globally as of commit `a026e97`, so Story 8.2's UsersPage.test.tsx does NOT need per-file `afterEach(cleanup)`. New test files can rely on the global setup.
- **Polish diacritics requirement** (per global user-instruction language directive): the pl.json keys MUST use proper diacritics. Verify by manually inspecting OR running `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` and asserting the count grew by at least 6 after the AC-8 keys land.
- **Auto-deploy after merge** (per memory `feedback_auto_deploy_dev`): after the Story 8.2 dev commit lands on main, run `infra/scripts/deploy.sh` to deploy to `.190`. The deploy-gate range check (per memory `feedback_deploy_skip_gate_design`) determines whether the deploy is a no-op based on the commit range; Story 8.2 has code changes so a deploy WILL run.

### Git intelligence (recent commits)

```
195fb22 fix(api): Story 8.1 codex P2 fix-up — monotonic UPDATE + asyncio.to_thread
80eebc9 feat(api,infra): alembic 0014 is_active + last_active + LastActiveMiddleware (Story 8.1)
9dedc81 fix(infra): Story 7.6 codex fix-up — drill script hardening
1fbba7b chore(infra): add 2fa-recovery-drill.sh — Epic 7 acceptance-gate drill script (Story 7.6)
f325efa fix(api): Story 7.5 codex P2 follow-up — preserve active-only predicate on UPDATE
```

Pattern: each story lands as `feat(api[,web,infra,tests]): ...` initial commit, then 1-2 `fix(...)` Codex P2 follow-up commits on the same story-scoped commit-message subject. Story 8.2 should follow the same shape — single `feat(api,web,tests): admin users tab (Story 8.2)` initial commit, then Codex review + 0-3 fix-up commits before sprint-status flips `review` → `done`.

### Project Structure Notes

- **Alignment with unified project structure:** all new files land in their natural locations (schemas under `apps/api/app/modules/admin/`, endpoint in the existing `admin/router.py`, tests under `apps/api/tests/`, frontend page in `apps/web/src/modules/admin/`, route in `apps/web/src/routes/admin/`, hook in `modules/admin/hooks/`, visual spec under `apps/web/tests/visual/`, i18n keys in the existing locale files). One NEW top-level frontend directory: `apps/web/src/modules/admin/` (the modules folder for admin-tier UI, peer of `modules/auth` + `modules/catalog`). One NEW frontend route directory: `apps/web/src/routes/admin/` (the route folder mirroring the URL prefix `/admin/`).
- **Detected conflicts or variances:** Epics §1772 says "Pagination defaults match existing admin-list defaults (Init 0 pattern: 25 rows per page)" — but the actual shipped Init 5 admin-list default is `page_size=50 ge=1 le=200` per `invite/admin_router.py:119`. Story 8.2 honors the ACTUAL shipped default (50) over the planning-text approximation (25). Flagged for bmad-correct-course at Epic 8 retro if the operator wants the 25-default explicitly re-stated; alternatively the page-size selector dropdown defaults its UI choice to 50 to match.
- **Naming conventions:** the new endpoint path `/api/admin/users` follows the project's REST-resource convention (`/api/admin/<resource>` for admin-scoped CRUD; existing peers: `/api/admin/audit`, `/api/admin/invites`, `/api/admin/share`). The new frontend route `/admin/users` follows the standard pattern (no trailing slash; lowercase). The new hook `useAdminUsers` follows the project's `use<Resource>` convention (compare `useSessions`, `useAuditLog`). The new component `UsersPage` follows the project's `<Resource>Page` convention (compare `Settings2faPage`, `ResetPasswordPage` (planned)). The new schema `AdminUserListItem` follows the project's `<Resource>ListItem` convention (compare `InviteListItem`, `AuditLogEntry`).
- **Module folder split is intentional:** the existing `apps/web/src/modules/admin/` does NOT exist yet — Story 8.2 creates it. The existing `apps/api/app/modules/admin/` does exist with just a `router.py` + empty `__init__.py`; Story 8.2 adds `users_schemas.py` as a peer of `router.py`.
- **TanStack Router `routes/admin/` directory** does NOT exist yet — Story 8.2 creates it with the single `users.tsx` file. Story 8.6 will add `invites.tsx` as a peer. Neither story creates an `admin/index.tsx` index route in this iteration (deferred — the operator entry is via `/admin/users` directly from the UserMenu link).

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-I-Soft-delete-+-last_active_at-throttling`] (lines 1601-1630)
- [Source: `_bmad-output/planning-artifacts/architecture.md#FR5-MEMBER-2-permission-table`] (lines 1486-1493) — the binding `current_admin` dependency on `/api/admin/users` row
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-8.2`] (lines 1762-1774)
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-1`] (line 1193)
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-4`] (line 1196)
- [Source: `_bmad-output/implementation-artifacts/8-1-alembic-0014-is-active-last-active-middleware.md#AC-7`] — the conftest fixture promotion Story 8.2 consumes
- [Source: `apps/api/app/modules/admin/router.py:1-137`] — the file Story 8.2 modifies
- [Source: `apps/api/app/modules/invite/admin_router.py:97-156`] — paginated-admin-list precedent
- [Source: `apps/api/app/modules/invite/admin_schemas.py:1-101`] — schema-file precedent
- [Source: `apps/api/app/core/db/models/_user.py:20-40`] — the SQLModel column binding
- [Source: `apps/api/tests/test_invite_admin.py:1-100`] — backend test precedent
- [Source: `apps/api/tests/conftest.py:64-124`] — the `isolated_client` fixture
- [Source: `apps/web/src/routes/settings/sessions.tsx:1-110`] — page-component precedent
- [Source: `apps/web/src/routes/login.tsx:172-179`] — `validateSearch` pattern
- [Source: `apps/web/src/modules/catalog/hooks/useSessions.ts:1-15`] — React Query hook precedent
- [Source: `apps/web/src/shell/UserMenu.tsx:1-80`] — the file Story 8.2 modifies for the menu link
- [Source: `apps/web/tests/visual/sessions.spec.ts:1-78`] — Playwright spec precedent
- [Source: `_bmad-output/project-context.md`] — FastAPI / SQLModel / auth / vitest conventions
- [Source: `AGENTS.md`] — repo layout + commit conventions + Polish-i18n requirement

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m]

### Debug Log References

### Completion Notes List

### File List
