# Story 8.3: Per-user actions: change role, deactivate / reactivate, force logout-all-sessions

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer (Ezop, banking-IT operator wearing the dev-team ITCM hat),
I want **the Epic 8 per-user action surface — change role, deactivate, reactivate, force logout-all-sessions — wired end-to-end on top of the Story 8.2 Users tab, with Decision I §1622-1630 enforcement gates landed at the auth-router tier so a deactivated user cannot refresh OR re-login (closing the gap left by Story 8.1 which added the column but no enforcement), plus a per-row kebab action menu + confirm modals on the existing `/admin/users` page, plus matching audit emissions (`user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`) per FR5-AUDIT-1, plus the four foot-gun guardrails (self-deactivate, self-demote, agent-role mutation, agent-force-logout) baked into the endpoint contract so the operator cannot lock themselves out of their own panel or break the `/agent-runbook` nginx-bypass invariant (NFR5-INT-1)**, namely:

1. **NEW backend endpoint `PATCH /api/admin/users/{id}`** in the existing `apps/api/app/modules/admin/router.py` (NOT a new sub-router — see Story 8.2 file-structure note §400 verbatim: the per-resource sub-router promotion is deferred until Story 8.4+ either accumulates enough endpoints to justify it OR an operator pass explicitly approves the refactor). Accepts JSON body `{role?: "admin"|"agent"|"member", is_active?: bool}` (BOTH fields optional, at least one MUST be present — empty body returns 400; presence semantics differ from value semantics, so `{is_active: false}` AND `{role: null}` are distinguishable by Pydantic v2 `model_fields_set` exposure). Returns `204 No Content` (the projection shape of the mutated row is not surfaced — the operator re-reads the list endpoint to see the updated state; mirrors `DELETE /api/auth/sessions/{family_id}` 204-contract from `apps/api/app/modules/auth/router.py:379-417` verbatim).
2. **NEW backend endpoint `POST /api/admin/users/{id}/force-logout`** in the same router. No body. Returns `204 No Content`. Invalidates every refresh-token family for the target user (mirrors the user-side `logout_all` endpoint at `apps/api/app/modules/auth/router.py:420-447` but with `actor_user_id == admin.id` AND `target_user_id == path-id` distinct in the audit row — the difference vs the existing `auth.logout_all` audit event is critical: this is `user.force_logout` per epics §1759 + §1778 binding).
3. **NEW Pydantic schemas** appended to the existing `apps/api/app/modules/admin/users_schemas.py` (Story 8.2's file — co-locate the mutation schemas as peers of the list-projection schemas; do NOT spin up a `users_mutations.py` peer file). Add `UserMutationRequest(BaseModel)` with `model_config = ConfigDict(extra="forbid")` (unknown fields are 422 — invariant: a future agent cannot quietly piggyback a `force_2fa_enrollment` field onto this schema; that belongs to Story 8.4's distinct endpoint with its own audit shape).
4. **REGRESSION-FIX `apps/api/app/modules/auth/router.py:login()` + `refresh()`:** add `if not user.is_active:` gate after password-verify (login) and after rotation succeeds (refresh). On hit, both return `HTTP 401` with `detail="account_deactivated"` AND emit `auth.login.fail` with reason `account_deactivated`, AND the refresh path burns the entire family via `burn_family()` (matches Decision I §1622 verbatim — "invalidates the entire refresh-token family (matches existing reuse-detection invalidation pattern)"). **This is the missing piece from Story 8.1.** Story 8.1 shipped the column + middleware; Story 8.3 ships the enforcement at the auth-router tier per epics §1786 binding ("Deactivation behavior verified end-to-end") — without this regression fix Story 8.3 is incomplete and Decision I is documentation-only.
5. **MODIFIED `apps/api/app/modules/admin/router.py`** — adds the two new endpoints (PATCH + POST force-logout) alongside the existing GET handlers. ZERO change to the GET endpoint shipped in Story 8.2 (the read endpoint is feature-complete; do not refactor it during 8.3). The two new endpoints sit immediately after the existing `list_admin_users` handler at line 155+.
6. **NEW backend tests** at `apps/api/tests/test_admin_users_mutations.py` (NEW file — peer of `test_admin_users_list.py` from Story 8.2). 12 tests M1-M12 binding the AC-1 through AC-6 contracts (see AC-7 table). Reuses the conftest `isolated_client` fixture + the `_seed_members` helper pattern from Story 8.2's test file but does NOT import from it (test files do not import from each other per project convention — duplicate the 15-line helper inline rather than constructing a `tests/_helpers/admin_users.py` shared module which is a Story 8.4+ refactor candidate, NOT a Story 8.3 deliverable).
7. **NEW backend tests** at `apps/api/tests/test_auth_deactivated_user.py` (NEW file binding the AC-3 regression fix). 4 tests D1-D4 covering: (a) login of deactivated user returns 401 + `account_deactivated`, (b) refresh of deactivated user returns 401 + burns the family, (c) refresh of active user still works (golden-path regression guard — the new gate does not accidentally break active flows), (d) login of active user still works (same golden-path on the login side).
8. **NEW frontend per-row action menu** integrated into `apps/web/src/modules/admin/UsersPage.tsx` (MODIFIED). Adds an 8th "Actions" column to the existing 7-column table with a kebab `<button>` per row triggering a `DropdownMenu` (from `apps/web/src/ui/dropdown-menu.tsx` — the existing Radix-wrapper used by `ModelHero.tsx:104-129` precedent). Menu items (in this order):
   - "Change role" — opens role-select modal.
   - "Deactivate" — visible only when `user.is_active === true`; opens confirm modal; on confirm calls `PATCH /admin/users/{id}` with `{is_active: false}`.
   - "Reactivate" — visible only when `user.is_active === false`; opens confirm modal; on confirm calls `PATCH /admin/users/{id}` with `{is_active: true}`.
   - "Force logout all sessions" — opens confirm modal; on confirm calls `POST /admin/users/{id}/force-logout`.
   - **Disabled menu items (foot-gun mirroring of backend guards):** all four items are `aria-disabled="true"` + grayed-out + non-interactive when the target row is (a) the current admin's own row, OR (b) any row with `role === "agent"`. The frontend mirror prevents the operator from triggering an action only to receive a 400/403 from the backend; backend guards remain the binding enforcement (defense-in-depth), frontend mirrors them only for UX.
9. **NEW frontend role-change modal** at `apps/web/src/modules/admin/ChangeRoleModal.tsx` (NEW file). Renders a `<Dialog>` with a `<select>` populated from `["admin", "agent", "member"]`, defaulting to the current target's role. On confirm calls `PATCH /admin/users/{id}` with `{role: <new>}`. The `agent` option is disabled in the select (`<option disabled>`) when target role is not already `agent` AND when target role IS `agent` (agent is a system role; the panel does not promote-to-agent or demote-from-agent — those are bootstrap-script operations per `architecture.md:1049` verbatim).
10. **MODIFIED `apps/web/src/lib/api-types.ts`** — adds NEW `// --- Admin users mutations (Story 8.3) ---` section immediately after the existing Story 8.2 block at line 199. Adds `UserMutationRequest` interface (`{role?: Role; is_active?: boolean}`).
11. **MODIFIED `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`** — adds 16 new `admin.users.actions.*` + `admin.users.confirm.*` + `admin.users.errors.*` keys (see AC-9 table). All Polish strings use proper diacritics per the global directive.
12. **MODIFIED frontend hook** `apps/web/src/modules/admin/hooks/useAdminUsers.ts` (Story 8.2's file) gains TWO new sibling hooks at the same file (do NOT split into per-hook files):
    - `useUpdateAdminUser()` → `useMutation` calling `PATCH /admin/users/{id}` with `{role?, is_active?}` body; on success calls `queryClient.invalidateQueries({queryKey: ["admin", "users"]})` to refresh the table.
    - `useForceLogoutAdminUser()` → `useMutation` calling `POST /admin/users/{id}/force-logout`; on success invalidates `["admin", "users"]` (since `last_active_at` may shift) AND emits a toast via `apps/web/src/lib/toast.ts` if such helper exists (search the codebase; fall back to a simple `alert()` or no-op if there's no project-wide toast contract yet — toast UX is NOT a Story 8.3 deliverable, just a nice-to-have).
13. **NEW frontend vitest tests** appended to `apps/web/src/modules/admin/UsersPage.test.tsx` (Story 8.2's file). Tests V5-V10 (6 new tests) cover the per-row action menu rendering, the confirm-modal flow, the disabled-state for self + agent rows, and the FR5-ADMIN-4 negative AC regression guard (the column-of-actions does NOT introduce bulk-select scaffolding).
14. **NEW frontend vitest tests** at `apps/web/src/modules/admin/ChangeRoleModal.test.tsx` (NEW file). 3 tests R1-R3 binding the modal's role-select shape + the disabled `agent` option + the confirm dispatch.
15. **MODIFIED frontend Playwright spec** `apps/web/tests/visual/admin-users.spec.ts` (Story 8.2's file). The 3 baseline screenshots (`admin-users-empty.png`, `admin-users-one-row.png`, `admin-users-many-rows.png`) MUST be regenerated to include the new Actions column; the AC-10 FR5-ADMIN-4 negative AC remains unchanged (zero checkboxes; bulk-action lexicon still returns count 0); a NEW Test 6 explicitly verifies the per-row kebab menu opens + lists the 4 action labels.

so that:

- **Decision I §1622-1630 is fully realized, not just partially.** Story 8.1 shipped the schema + middleware (the data plane). Story 8.2 shipped the read endpoint (the visibility plane). Story 8.3 ships the WRITE plane AND the ENFORCEMENT plane in one atomic story per epics §1739 "Acceptance gate" verbatim. The deactivation flow is verifiable end-to-end on `.190` after merge: deactivate a member → that member's `/api/auth/refresh` returns 401 + `account_deactivated` within seconds; their JWT expires naturally within ≤10 minutes; their cookie is then invalid.
- **The four foot-gun guardrails prevent operator self-lockout.** Banking-IT instinct (from the user profile memory): a single operator + single admin account = single point of failure. If the operator could deactivate their own row OR demote themselves to `member`, the panel becomes unreachable until DB-direct surgery on `.190`. Story 8.3 makes the lockout impossible at the endpoint tier (400 `cannot_target_self`) AND mirrors the guard in the UI (disabled menu items on own row). The same protection extends to the `agent` row — NFR5-INT-1 binds `agent` as a service account that must never enter the panel UI (PRD §1180 "no 2FA forced ever; nginx bypass preserved"); allowing the panel to deactivate it would break `/agent-runbook` polling silently.
- **FR5-AUDIT-1 emits the four E8 action names the registry already documents.** `apps/api/app/core/audit.py:33-35` already lists `user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout` as Story 8.3-owned actions; Story 8.3 makes the references real. All four use the existing `user` entity_type from `KNOWN_ENTITY_TYPES` — no registry expansion needed.
- **The Story 8.2 visual baseline updates cleanly to the Story 8.3 baseline.** Per Story 8.2 dev notes §419 "consecutive stories own consecutive baselines": Story 8.2's baselines were BEFORE-state (no actions column); Story 8.3 updates them AFTER (with actions column + kebab). The FR5-ADMIN-4 negative AC remains the regression guard: the Actions column adds a per-row menu, NOT a per-row checkbox; the spec's `input[type="checkbox"].count() === 0` assertion still passes.
- **The existing Story 8.1 `LastActiveMiddleware` test (`test_last_active_throttle.py`) stays green.** The Story 8.3 enforcement gate sits AFTER auth dependency resolution (in `login()` post-password-verify AND in `refresh()` post-rotation); the middleware runs only on authenticated requests, and a deactivated user's request that 401s at the auth-router tier never reaches the middleware (the dependency-resolution exception short-circuits the middleware chain). No regression risk on Story 8.1's NFR5-PERF-1 throttle.

### Story scope is strictly bounded

- **NEW files (~3):**
  - `apps/api/tests/test_admin_users_mutations.py`
  - `apps/api/tests/test_auth_deactivated_user.py`
  - `apps/web/src/modules/admin/ChangeRoleModal.tsx`
  - `apps/web/src/modules/admin/ChangeRoleModal.test.tsx`
- **MODIFIED files (~7):**
  - `apps/api/app/modules/admin/router.py` (add PATCH + POST force-logout endpoints).
  - `apps/api/app/modules/admin/users_schemas.py` (append `UserMutationRequest`).
  - `apps/api/app/modules/auth/router.py` (add `is_active` gate to `login()` + `refresh()` — the regression fix).
  - `apps/web/src/modules/admin/UsersPage.tsx` (add Actions column + DropdownMenu integration).
  - `apps/web/src/modules/admin/UsersPage.test.tsx` (append V5-V10).
  - `apps/web/src/modules/admin/hooks/useAdminUsers.ts` (append `useUpdateAdminUser` + `useForceLogoutAdminUser`).
  - `apps/web/src/lib/api-types.ts` (append `UserMutationRequest` interface).
  - `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` (16 new keys).
  - `apps/web/tests/visual/admin-users.spec.ts` (update fixtures + regenerate baselines + add Test 6 kebab-menu interaction).
- **STRICTLY OUT OF SCOPE** (these belong to later stories and pollute the diff if added here):
  - `POST /api/admin/users/{id}/force-2fa-enrollment` + `POST /api/admin/users/{id}/force-disable-2fa` — Story 8.4 (per epics §1789-1804).
  - `POST /api/admin/users/{id}/password-reset` — Story 8.5 (per epics §1806-1818).
  - The Invites tab — Story 8.6 (AdminTabs remains in Story 8.2's shipped state: Invites tab disabled).
  - Bulk operations (FR5-ADMIN-4 deliberate exclusion — explicitly NOT in scope, enforced by AC-10 negative AC mirroring Story 8.2 AC-10).
  - Admin re-auth gate before destructive actions (e.g. "enter TOTP again before deactivating") — NOT in scope. The architecture binds the panel actions to `current_admin` cookie + ConfirmDialog UX only. A re-auth-on-destructive-action gate is a Story 9.x security audit follow-up if NFR5-SEC-3 scenarios surface the need; out-of-scope for Epic 8.
  - GDPR right-to-be-forgotten hard-delete — Decision I §1628 explicitly bounds this as "DB-direct only — not exposed in the panel". Out-of-scope.
  - Rate-limit middleware on the new admin write endpoints — admin-tier requests are bounded by `current_admin` + operator-tier trust, not by request-frequency throttle (per Story 8.2 §61 out-of-scope rationale). If 9.x audit surfaces a need, it lands as a Decision-G amendment.
  - Toast/snackbar component contract — Story 8.3 falls back to no-op or `alert()` if no project-wide toast exists; introducing one is a separate UX-polish chore.
  - Migration to a new admin sub-router (`apps/api/app/modules/admin/users_router.py`) — Story 8.4+ may justify it, NOT 8.3 (per Story 8.2 §400 file-structure rationale).
  - `PATCH /api/admin/users/{id}` accepting `display_name` or `email` mutations — NOT in scope of FR5-ADMIN-2. The PATCH body is bounded to `{role, is_active}` ONLY; unknown fields are 422 via `ConfigDict(extra="forbid")`. Display-name + email mutations are deferred indefinitely; the operator uses DB-direct surgery if they ever become necessary.

No new Alembic migration (head stays `0014_users_is_active_last_active` from Story 8.1). No new dependency. No new env-var. No new rate-limit scope. No new entity_type. No change to `apps/api/app/main.py` or `apps/api/app/router.py`. No change to `Story 8.1 LastActiveMiddleware`. No change to the GET endpoint shipped in Story 8.2.

## Acceptance Criteria

**AC-1 — `PATCH /api/admin/users/{id}` endpoint: role + is_active mutation with audit emissions and foot-gun guardrails.**

- Given an admin-authenticated request with a valid `portal_access` cookie + `role == "admin"`,
- When the client calls `PATCH /api/admin/users/{id}` with JSON body `{role?, is_active?}`,
- Then the endpoint MUST:
  - Validate the path UUID via FastAPI's native `uuid.UUID` path-param parsing (invalid UUID → 422 per FastAPI default).
  - Validate body via `UserMutationRequest(BaseModel)` with `model_config = ConfigDict(extra="forbid")` — unknown fields return 422. Both fields are `Optional`; if NEITHER field is set in the body (the parsed pydantic model's `model_fields_set` is empty), return 400 with `detail="no_mutation_provided"`.
  - Resolve `_admin_id: uuid.UUID = current_admin` — non-admin authenticated requests return 403; anonymous requests return 401.
  - Look up the target row: `target = session.get(User, user_id)`. If `None`, return 404 with `detail="user_not_found"`.
  - **Self-mutation guard:** if `target.id == admin_id`, return 400 with `detail="cannot_target_self"`. This blocks BOTH `{role: X}` AND `{is_active: false}` on own row; the deliberately-broad guard prevents the operator from accidentally demoting themselves to member (a partial guard that only blocked `is_active=false` would still allow demote → permanent lockout via role downgrade). The check fires regardless of the body fields' values.
  - **Agent-role guard:** if `target.role == UserRole.agent`, return 400 with `detail="cannot_target_agent"`. NFR5-INT-1 binds the agent service account as a panel-untouchable identity; the `/agent-runbook` nginx-bypass invariant fails silently if the agent row is deactivated or demoted. The guard fires regardless of the body fields' values.
  - **Role-promote-to-agent guard:** if the body sets `role == UserRole.agent` AND `target.role != UserRole.agent` (i.e. attempting to promote a non-agent to agent), return 400 with `detail="cannot_promote_to_agent"`. The `agent` role is created by `python -m scripts.bootstrap_agent --email agent@portal.local --rotate` per `architecture.md:1049` verbatim — NOT by the admin panel. The check fires only on attempted promotion; if the target is already `agent` the earlier agent-role guard short-circuits first.
  - Read the BEFORE state (capture `before_role`, `before_is_active`) before mutating. The audit payload's `before` JSON consumes these.
  - Apply mutations atomically in a single SQLAlchemy session:
    - If `role` field set AND `body.role != target.role` (i.e. actual change, not no-op): `target.role = body.role`. Emit `record_event(action="user.role_changed", entity_type="user", entity_id=target.id, actor_user_id=admin_id, before={"role": before_role.value}, after={"role": body.role.value}, request_id=...)`.
    - If `is_active` field set AND `body.is_active != target.is_active`:
      - `target.is_active = body.is_active`.
      - Emit `record_event(action="user.deactivated" if body.is_active == False else "user.reactivated", entity_type="user", entity_id=target.id, actor_user_id=admin_id, before={"is_active": before_is_active}, after={"is_active": body.is_active})`.
      - **Critical:** if `body.is_active == False`, ALSO immediately burn all refresh-token families for the target (mirrors `burn_family()` from `app.core.auth.refresh:93-105` over every family_id present in `RefreshToken WHERE user_id = target.id AND revoked_at IS NULL`). The rationale: the AC-3 enforcement at `/refresh` catches the next refresh attempt, but the in-flight refresh family for the deactivated user is invalidated AT DEACTIVATION TIME so the access-token-only window is bounded to ≤10 minutes (JWT TTL). Without this immediate burn, a deactivated user with a long-lived refresh cookie could in theory replay it once before the 401 fires — the burn closes that window deterministically.
    - `session.commit()` once at the end of the handler (not per-mutation — atomic two-field change is a single commit).
  - If neither field changed actual state (e.g. body says `{is_active: true}` and target.is_active is already True), the endpoint returns 204 anyway BUT emits ZERO audit rows (no-op mutations are not audited; mirrors the SoT-write convention at `apps/api/app/modules/sot/admin_router.py` per existing project precedent — verify by reading at least one SoT write handler if unsure).
  - Return `Response(status_code=204)`.
- And the OpenAPI surface MUST expose the endpoint with `summary="Update admin-visible user fields (role + is_active)"` + a 5-7 sentence description citing the four guards explicitly (self / agent / promote-to-agent / no-mutation-provided) so the operator runbook documentation (a future Story 10.4 deliverable) can quote it verbatim.

**AC-2 — `POST /api/admin/users/{id}/force-logout` endpoint: revoke-all-families + audit.**

- Given an admin-authenticated request,
- When the client calls `POST /api/admin/users/{id}/force-logout` (no body),
- Then the endpoint MUST:
  - Validate path UUID + resolve `_admin_id: uuid.UUID = current_admin` per AC-1.
  - Look up `target = session.get(User, user_id)`. If `None`, return 404 with `detail="user_not_found"`.
  - **Self-force-logout guard:** if `target.id == admin_id`, return 400 with `detail="cannot_target_self"`. The operator can already self-logout via `POST /api/auth/logout-all` (the user-side endpoint at `auth/router.py:420`); forcing the operator to use the user-side endpoint preserves the audit-shape invariant `actor_user_id != target_user_id` for `user.force_logout` (audit-querying for cross-cutting force-logout events stays clean — no self-targets pollute the result).
  - **Agent-force-logout guard:** if `target.role == UserRole.agent`, return 400 with `detail="cannot_target_agent"`. Same NFR5-INT-1 rationale as AC-1: forcing logout on the agent service account would break `/agent-runbook` polling until the agent script re-authenticates (the agent flow does not auto-retry on auth failure; it logs + exits per Init 2 design).
  - Burn every active refresh-token family for the target via the burn helper in `app/core/auth/refresh.py:93-105` (one `burn_family()` call per distinct `family_id`; OR an inline single-pass UPDATE if the implementer prefers — the existing `auth.router.py::logout_all` at line 420-447 uses the inline pattern). Capture `revoked_count` for the audit payload.
  - Emit `record_event(action="user.force_logout", entity_type="user", entity_id=target.id, actor_user_id=admin_id, after={"revoked_count": revoked_count}, request_id=...)`.
  - **Critical:** the access-token (JWT) is NOT proactively invalidated — per Decision I §1621 verbatim "JWT-based requests stay valid until natural 10-minute expiry; no proactive token revocation". The force-logout is bounded by the JWT TTL window; refresh attempts within that window 401 with `force_relogin`.
  - `session.commit()`. Return `Response(status_code=204)`.
- And if the target has ZERO active families (e.g. they have not logged in OR have already been force-logged-out), the endpoint STILL returns 204 + emits the audit event with `after={"revoked_count": 0}`. The idempotent shape matches `DELETE /api/auth/sessions/{family_id}` at line 387-390 verbatim ("idempotent — returns 204 even if no rows to revoke").

**AC-3 — `is_active` enforcement gate on `POST /api/auth/login` + `POST /api/auth/refresh` (the missing piece from Story 8.1).**

- Given a user with `is_active = FALSE`,
- When that user calls `POST /api/auth/login` with valid credentials,
- Then the endpoint MUST:
  - Verify the password as today.
  - AFTER password-verify succeeds, AND BEFORE any other branch (TOTP partial-auth, force-enroll, refresh-row mint), check `if not user.is_active:`.
  - On hit: `record_event(action="auth.login.fail", entity_type="user", entity_id=user.id, actor_user_id=None, after={"email": user.email, "reason": "account_deactivated"})` AND raise `HTTPException(status.HTTP_401_UNAUTHORIZED, "account_deactivated")`.
  - **Critical placement:** the check fires AFTER password-verify so the `is_active` gate cannot be probed as a user-enumeration oracle (the 401 returns whether the password is wrong OR the account is deactivated — same status code, distinguishable only via the `detail` string AND only AFTER successful password verification, so an attacker without the password cannot distinguish "user does not exist" vs "user exists but is deactivated"). The information-disclosure risk is acceptable for the operator-tier admin (the deactivated user themselves does need to be told their account is off — bombarding them with `invalid_credentials` would be a UX disaster).
- Given a user with `is_active = FALSE`,
- When that user calls `POST /api/auth/refresh` with a valid refresh-token cookie,
- Then the endpoint MUST:
  - Execute the rotation as today (resolve presented row, run `rotate_refresh()`).
  - AFTER rotation succeeds AND BEFORE issuing cookies (so a deactivated user does NOT receive a fresh JWT), look up `user = session.get(User, target.user_id)` AND check `if not user.is_active:`.
  - On hit: `burn_family(session, target.family_id)` (closes the entire family — mirrors the reuse-detection invalidation path verbatim per Decision I §1622) + `session.commit()` + `record_event(action="auth.login.fail", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"reason": "account_deactivated", "family_id": str(target.family_id)})` + raise `HTTPException(status.HTTP_401_UNAUTHORIZED, "account_deactivated")`.
  - **Critical placement:** the check fires AFTER `rotate_refresh()` succeeds because the existing rotation logic (grace period, reuse detection) needs to run consistently for active AND deactivated users; placing the check BEFORE rotation would create a separate code path for deactivated users that diverges on the grace handling. Placing it AFTER rotation but BEFORE cookie issuance means the rotated refresh-row exists in the DB briefly but is burned in the same transaction (single `session.commit()` covers both the rotation and the burn).
- And both gates emit `auth.login.fail` (NOT a new audit action name — Decision I §1622 verbatim and FR5-AUDIT-1 §1200 verbatim bind this to the existing `auth.login.fail` action with `reason: account_deactivated` in the after-payload, NOT a new `auth.refresh.deactivated` action). The reason field discriminates the cause.
- And the gates do NOT regress the active-user path: D3 + D4 below (golden-path tests) MUST stay green.

**AC-4 — `UserMutationRequest` schema appended to `apps/api/app/modules/admin/users_schemas.py`.**

- Given the existing schema-file from Story 8.2 (lines 1-42, exporting `AdminUserListItem` + `AdminUserListResponse`),
- When Story 8.3 ships,
- Then the schema file MUST gain a NEW `UserMutationRequest(BaseModel)` class with:
  - `model_config = ConfigDict(extra="forbid")` — unknown fields are 422. **This is critical:** without `extra="forbid"`, a future agent could quietly piggyback a `force_2fa_enrollment` field onto the schema and the PATCH endpoint would silently accept it without dispatching the Story 8.4 audit shape. The forbid contract makes scope creep impossible at the schema layer.
  - Two optional fields:
    - `role: UserRole | None = None` — the optional role mutation; `None` means "do not change role".
    - `is_active: bool | None = None` — the optional active-flag mutation; `None` means "do not change active".
  - A 3-line class docstring citing FR5-ADMIN-2 + the four guards (self, agent, promote-to-agent, no-mutation) so the schema's purpose is self-documenting at the call site.
- And the schema MUST be importable via `from app.modules.admin.users_schemas import UserMutationRequest` — no namespace change to the file's existing exports.
- And the file's existing `AdminUserListItem` + `AdminUserListResponse` definitions MUST NOT be modified (Story 8.2's hygiene boundary stays intact).

**AC-5 — Backend tests `apps/api/tests/test_admin_users_mutations.py` (NEW; 12 named tests M1-M12).**

- Given the conftest `isolated_client` fixture + the seeded-admin row,
- When Story 8.3 ships,
- Then `apps/api/tests/test_admin_users_mutations.py` MUST exist as a NEW file with 12 tests:

  | # | Name | Asserts |
  |---|------|---------|
  | M1 | `test_patch_user_role_emits_user_role_changed` | Seed 1 member. PATCH `/api/admin/users/{member_id}` with `{role: "admin"}` returns 204. DB read: member.role == admin. Audit-log query: 1 row with `action="user.role_changed"`, `actor_user_id == admin.id`, `entity_id == member.id`, `before == {"role": "member"}`, `after == {"role": "admin"}`. |
  | M2 | `test_patch_user_is_active_false_emits_user_deactivated_and_burns_families` | Seed 1 member + mint 2 refresh-token rows for them in 2 distinct families (helper `_seed_active_refresh_token(session, user_id, family_id=None)` at top of file). PATCH `{is_active: false}` returns 204. DB read: member.is_active == False; both RefreshToken rows have `revoked_at IS NOT NULL` AND `revoke_reason == "reuse_detected"` OR an alternate "force_deactivation" reason (the implementer picks the literal string but it MUST be deterministic; the test asserts whichever was chosen). Audit-log query: 1 row with `action="user.deactivated"`, `actor_user_id == admin.id`, `entity_id == member.id`, `before == {"is_active": True}`, `after == {"is_active": False}`. |
  | M3 | `test_patch_user_is_active_true_after_false_emits_user_reactivated` | Seed 1 member with `is_active=False`. PATCH `{is_active: true}` returns 204. DB read: member.is_active == True. Audit-log query: 1 row with `action="user.reactivated"`, before == `{"is_active": False}`, after == `{"is_active": True}`. |
  | M4 | `test_patch_self_returns_400_cannot_target_self` | PATCH `/api/admin/users/{admin.id}` with `{role: "member"}` returns 400 + `{"detail": "cannot_target_self"}`. Audit-log row count == 0 (no event emitted for the rejected request). DB read: admin.role still == "admin". Same check with `{is_active: false}` body also returns 400. |
  | M5 | `test_patch_agent_row_returns_400_cannot_target_agent` | Seed 1 agent-role user. PATCH `/api/admin/users/{agent_id}` with `{is_active: false}` returns 400 + `{"detail": "cannot_target_agent"}`. Audit count == 0. DB read: agent.is_active still == True. Same check with `{role: "member"}` body also returns 400. |
  | M6 | `test_patch_promote_to_agent_returns_400_cannot_promote_to_agent` | Seed 1 member. PATCH `/api/admin/users/{member_id}` with `{role: "agent"}` returns 400 + `{"detail": "cannot_promote_to_agent"}`. Audit count == 0. DB read: member.role still == "member". |
  | M7 | `test_patch_unknown_field_returns_422_extra_forbid` | PATCH `/api/admin/users/{member_id}` with `{role: "admin", force_2fa_enrollment: true}` returns 422 (Pydantic v2 extra-forbid). The body MUST NOT mutate anything. Audit count == 0. DB read: member unchanged. |
  | M8 | `test_patch_empty_body_returns_400_no_mutation_provided` | PATCH `/api/admin/users/{member_id}` with `{}` returns 400 + `{"detail": "no_mutation_provided"}`. Audit count == 0. |
  | M9 | `test_patch_noop_mutation_emits_no_audit` | Seed 1 member with role=member, is_active=True. PATCH `{role: "member", is_active: true}` returns 204. Audit count == 0 (no-op mutations are not audited). DB read: member unchanged. |
  | M10 | `test_patch_returns_403_for_member_role` | Mint a `member`-role cookie (per Story 8.2 T8 precedent). PATCH `/api/admin/users/{some_id}` returns 403. Audit count == 0. |
  | M11 | `test_force_logout_revokes_all_families_and_emits_user_force_logout` | Seed 1 member with 3 active refresh-token rows across 2 distinct families. POST `/api/admin/users/{member_id}/force-logout` (no body) returns 204. DB read: all 3 rows have `revoked_at IS NOT NULL`. Audit-log query: 1 row with `action="user.force_logout"`, `actor_user_id == admin.id`, `entity_id == member.id`, `after.revoked_count == 3`. |
  | M12 | `test_force_logout_self_and_agent_return_400` | POST `/api/admin/users/{admin.id}/force-logout` returns 400 + `cannot_target_self`. Seed 1 agent; POST `/api/admin/users/{agent_id}/force-logout` returns 400 + `cannot_target_agent`. Audit count == 0 for both rejected requests. |

- And M1-M12 MUST consume the conftest `isolated_client` fixture (per Story 8.2 AC-3 binding). Cookie minting is inline via `encode_token(...)` per the Story 8.2 `_admin_token` helper precedent — duplicate the 15-line helper at the top of this new file rather than constructing a shared `_helpers` module (per the Story 8.3 §6 structure note: helper extraction is a Story 8.4+ deliberate refactor, NOT a 8.3 accidental side-effect).
- And the file MUST include an autouse `_clear_user_and_audit_and_refresh_tables` fixture preserving the seeded admin row (mirrors Story 8.2's `_clear_user_and_audit_tables` at test_admin_users_list.py:54-64 verbatim, extended to also wipe the `RefreshToken` table between tests since M2 + M11 + M12 seed refresh-token rows).
- And `cd apps/api && .venv/bin/pytest tests/test_admin_users_mutations.py -v` MUST be green for all 12 tests, both in isolation and together with the full suite.

**AC-6 — Backend tests `apps/api/tests/test_auth_deactivated_user.py` (NEW; 4 named tests D1-D4) for the AC-3 regression fix.**

- Given the conftest `isolated_client` fixture,
- When Story 8.3 ships,
- Then `apps/api/tests/test_auth_deactivated_user.py` MUST exist as a NEW file with 4 tests:

  | # | Name | Asserts |
  |---|------|---------|
  | D1 | `test_login_deactivated_user_returns_401_account_deactivated` | Seed 1 member with known password ("test-password-d1") + is_active=False. POST `/api/auth/login` with `{email, password}` returns 401 + `{"detail": "account_deactivated"}`. Audit-log query: 1 row `action="auth.login.fail"`, `after.reason == "account_deactivated"`. Response MUST NOT include a `set-cookie` header for `portal_access` or `portal_refresh` (no cookies issued to deactivated users). |
  | D2 | `test_refresh_deactivated_user_returns_401_and_burns_family` | Seed 1 member with active refresh-token cookie (mint via test helper `_seed_login(c, email, password)` that performs a real login + captures cookies). Mid-test, flip `member.is_active = False` directly in the DB. POST `/api/auth/refresh` with the captured refresh cookie returns 401 + `{"detail": "account_deactivated"}`. DB read: all RefreshToken rows for that user have `revoked_at IS NOT NULL`. Audit-log query: 1 row `action="auth.login.fail"`, after.reason == "account_deactivated", after.family_id set. |
  | D3 | `test_refresh_active_user_still_works_golden_path` | Seed 1 active member + login. POST `/api/auth/refresh` returns 200 + sets a fresh refresh cookie. Audit-log query: no `auth.login.fail` event for the user; no `revoked_at IS NOT NULL` on the active row (the old row IS revoked with reason=rotated as before, but the new row is active). Regression guard: ensures the new gate does not accidentally burn active flows. |
  | D4 | `test_login_active_user_still_works_golden_path` | Seed 1 active member. POST `/api/auth/login` returns 200 + sets cookies. Audit-log query: 1 row `action="auth.login.success"`. Regression guard: ensures the new gate does not accidentally 401 active flows. |

- And D1-D4 MUST consume the `isolated_client` fixture + the per-file `_clear_user_and_audit_and_refresh_tables` autouse fixture (same shape as test_admin_users_mutations.py).
- And `cd apps/api && .venv/bin/pytest tests/test_auth_deactivated_user.py -v` MUST be green for all 4 tests.

**AC-7 — Frontend per-row action menu integrated into `apps/web/src/modules/admin/UsersPage.tsx`.**

- Given the Story 8.2 Users page at `apps/web/src/modules/admin/UsersPage.tsx:36-266` with 7 columns and NO row-actions,
- When Story 8.3 ships,
- Then `apps/web/src/modules/admin/UsersPage.tsx` MUST be modified to:
  - Add an 8th column header `<th>{t("admin.users.column_actions")}</th>` at the END of the existing `<tr>` in `<thead>` (between Last active and the closing `</tr>` — NOT in the middle of the existing column order; appending preserves visual baseline minimization on the BEFORE columns).
  - Add an 8th `<td>` per row containing:
    - A kebab `<button>` with `aria-label={t("admin.users.actions.menu_label", {email})}` + a Lucide `<MoreVertical className="size-4" aria-hidden />` icon (matches `apps/web/src/modules/catalog/components/ModelHero.tsx:116` precedent verbatim).
    - The button opens a `<DropdownMenu>` (from `@/ui/dropdown-menu` — the existing Radix wrapper used by ModelHero) with 4 items in order:
      1. "Change role" — `<DropdownMenuItem onSelect={() => setChangeRoleTarget(user)}>` opens the ChangeRoleModal (AC-8).
      2. "Deactivate" — visible only when `user.is_active === true`. `<DropdownMenuItem onSelect={() => setConfirmDeactivate(user)}>` opens a ConfirmDialog with `destructive` variant.
      3. "Reactivate" — visible only when `user.is_active === false`. `<DropdownMenuItem onSelect={() => setConfirmReactivate(user)}>` opens a ConfirmDialog (non-destructive variant).
      4. "Force logout all sessions" — `<DropdownMenuItem onSelect={() => setConfirmForceLogout(user)}>` opens a ConfirmDialog with `destructive` variant.
  - **Disabled state on own + agent rows:** if `user.id === currentAdmin.id` OR `user.role === "agent"`, the kebab `<button>` is `disabled` + `aria-disabled="true"` + grayed-out (Tailwind: `opacity-50 cursor-not-allowed`); the DropdownMenu does not open. The check uses `useAuth().user?.id` for the current-admin ID (the `useAuth` hook exists at `apps/web/src/shell/AuthContext.tsx` per the AdminUsersRoute precedent at `apps/web/src/routes/admin/users.tsx:17`).
  - Wire the four action handlers via three `useState` slots (`changeRoleTarget`, `confirmDeactivateTarget`, `confirmReactivateTarget`, `confirmForceLogoutTarget`) + the two new mutation hooks `useUpdateAdminUser()` + `useForceLogoutAdminUser()` from `useAdminUsers.ts`.
  - On mutation success: close the relevant modal + invalidate the admin-users query (done inside the hook's `onSuccess`).
  - On mutation error (ApiError with `status === 400` and `detail === "cannot_target_self"` etc.): display an inline error message above the table (`<p role="alert" className="text-sm text-destructive">{t("admin.users.errors." + detail)}</p>`) — the message MUST honor the 5 known error codes (`cannot_target_self`, `cannot_target_agent`, `cannot_promote_to_agent`, `no_mutation_provided`, `user_not_found`); unknown error codes fall back to `t("admin.users.errors.generic")`.
- And the existing 7 columns + their sortable behavior + the search input + page-size selector + pagination strip MUST NOT change (regression guard: Story 8.2 V1-V4 vitest tests stay green).
- And the file MUST NOT introduce any `<input type="checkbox">` element (AC-10 negative AC enforcement persists from Story 8.2).

**AC-8 — `ChangeRoleModal.tsx` at NEW `apps/web/src/modules/admin/ChangeRoleModal.tsx`.**

- Given the `ConfirmDialog` precedent at `apps/web/src/ui/custom/ConfirmDialog.tsx:1-71` + the Dialog Radix wrapper at `apps/web/src/ui/dialog.tsx`,
- When Story 8.3 ships,
- Then `apps/web/src/modules/admin/ChangeRoleModal.tsx` MUST exist as a NEW file (~80 LOC) with:
  - A `ChangeRoleModal({open, onOpenChange, target, onConfirm, pending})` named export where `target: AdminUser | null` (`null` allowed for the closed state — the modal renders nothing if target is null) AND `onConfirm: (newRole: Role) => void`.
  - The modal renders a `<Dialog>` with header `<DialogTitle>{t("admin.users.change_role.title", {email: target.email})}</DialogTitle>` + description `<DialogDescription>{t("admin.users.change_role.description")}</DialogDescription>`.
  - A `<select>` with options `[{value: "admin", label: t("admin.users.change_role.option_admin")}, {value: "member", label: t("admin.users.change_role.option_member")}, {value: "agent", label: t("admin.users.change_role.option_agent"), disabled: true}]`. The `agent` option is ALWAYS disabled (the panel does not promote-to-agent; matches AC-1 backend guard). The select defaults its initial value to `target.role`.
  - A `useState<Role>` slot for the in-modal selection, initialized to `target?.role`. Reset to `target.role` when target changes (`useEffect`).
  - `<DialogFooter>` with `<Button variant="outline" onClick={() => onOpenChange(false)}>{t("common.cancel")}</Button>` + `<Button onClick={() => onConfirm(selectedRole)} disabled={pending || selectedRole === target.role}>{t("common.confirm")}</Button>`. The confirm button is disabled if the in-modal selection equals the target's existing role (no-op mutation — the AC-1 backend returns 204 in this case but the UI prevents the round-trip).
- And the modal MUST be importable via `import { ChangeRoleModal } from "@/modules/admin/ChangeRoleModal"` — no default export.

**AC-9 — i18n keys appended to `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`.**

- Given Story 8.2's `admin.*` namespace block at `en.json:107-130`,
- When Story 8.3 ships,
- Then both locale files MUST gain the following 16 NEW keys (insertion location: immediately after Story 8.2's `admin.users.pagination_next` key, before any deeper-nested keys):

  | Key | English text | Polish text |
  |---|---|---|
  | `admin.users.column_actions` | Actions | Akcje |
  | `admin.users.actions.menu_label` | Actions for {{email}} | Akcje dla {{email}} |
  | `admin.users.actions.change_role` | Change role | Zmień rolę |
  | `admin.users.actions.deactivate` | Deactivate | Dezaktywuj |
  | `admin.users.actions.reactivate` | Reactivate | Reaktywuj |
  | `admin.users.actions.force_logout` | Force logout all sessions | Wymuś wylogowanie ze wszystkich sesji |
  | `admin.users.change_role.title` | Change role for {{email}} | Zmień rolę dla {{email}} |
  | `admin.users.change_role.description` | Pick a new role for this user. Promoting to admin grants full panel access. The agent role is system-managed and cannot be assigned from this panel. | Wybierz nową rolę dla tego użytkownika. Promocja do admina przyznaje pełny dostęp do panelu. Rola agent jest zarządzana przez system i nie może być przypisana z tego panelu. |
  | `admin.users.change_role.option_admin` | Admin | Administrator |
  | `admin.users.change_role.option_member` | Member | Członek |
  | `admin.users.change_role.option_agent` | Agent (system-managed) | Agent (zarządzane przez system) |
  | `admin.users.confirm.deactivate_title` | Deactivate {{email}}? | Dezaktywować {{email}}? |
  | `admin.users.confirm.deactivate_description` | The user will lose access on their next refresh (within 10 minutes) and cannot log in until reactivated. All their active sessions will be terminated. | Użytkownik straci dostęp przy następnym odświeżeniu (do 10 minut) i nie będzie mógł się zalogować do czasu reaktywacji. Wszystkie jego aktywne sesje zostaną zakończone. |
  | `admin.users.confirm.reactivate_title` | Reactivate {{email}}? | Reaktywować {{email}}? |
  | `admin.users.confirm.reactivate_description` | The user will regain login access. Existing sessions remain invalidated; the user will need to log in again. | Użytkownik odzyska dostęp do logowania. Istniejące sesje pozostają unieważnione; użytkownik będzie musiał zalogować się ponownie. |
  | `admin.users.confirm.force_logout_title` | Force logout {{email}}? | Wymusić wylogowanie {{email}}? |
  | `admin.users.confirm.force_logout_description` | All active sessions for this user will be invalidated. They will need to log in again. Their access token remains valid until natural expiry (≤10 minutes). | Wszystkie aktywne sesje tego użytkownika zostaną unieważnione. Będą musieli zalogować się ponownie. Token dostępu pozostaje ważny do naturalnego wygaśnięcia (≤10 minut). |
  | `admin.users.errors.cannot_target_self` | You cannot apply this action to your own account. | Nie możesz zastosować tej akcji do własnego konta. |
  | `admin.users.errors.cannot_target_agent` | The agent service account is system-managed; this action is not allowed. | Konto serwisowe agent jest zarządzane przez system; ta akcja nie jest dozwolona. |
  | `admin.users.errors.cannot_promote_to_agent` | The agent role is created by the bootstrap script, not from this panel. | Rola agent jest tworzona przez skrypt bootstrap, a nie z tego panelu. |
  | `admin.users.errors.no_mutation_provided` | No changes provided. | Nie podano żadnych zmian. |
  | `admin.users.errors.user_not_found` | User not found. The list may be out of date — refresh and try again. | Nie znaleziono użytkownika. Lista może być nieaktualna — odśwież i spróbuj ponownie. |
  | `admin.users.errors.generic` | Action failed. Try again or check the API logs. | Akcja nie powiodła się. Spróbuj ponownie lub sprawdź logi API. |

- And the Polish translations MUST use proper diacritics. Verify with `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` — the count MUST grow by ≥10 lines vs the pre-Story-8.3 baseline.
- And the en.json + pl.json key counts MUST remain equal post-merge (`jq 'keys | length' en.json pl.json` returns the same integer).

**AC-10 — Frontend hooks `useUpdateAdminUser` + `useForceLogoutAdminUser` appended to `useAdminUsers.ts`.**

- Given the Story 8.2 file at `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-35` exporting the `useAdminUsers` React Query hook,
- When Story 8.3 ships,
- Then the same file MUST gain TWO new exports:
  - `useUpdateAdminUser()`: returns `useMutation<void, ApiError, {user_id: string; body: UserMutationRequest}>` calling `api<void>('/admin/users/' + user_id, { method: "PATCH", body: JSON.stringify(body) })`. On `onSuccess`: `queryClient.invalidateQueries({queryKey: ["admin", "users"]})`. No optimistic updates (admin-tier mutations are low-frequency; the refetch cost is fine).
  - `useForceLogoutAdminUser()`: returns `useMutation<void, ApiError, string>` (the variable is the target `user_id`) calling `api<void>('/admin/users/' + user_id + '/force-logout', { method: "POST" })`. Same onSuccess invalidation.
- And both hooks MUST import `queryClient` via `useQueryClient()` (the hook from `@tanstack/react-query`, NOT a global singleton — matches the `Settings2faPage.tsx:38` precedent).
- And both hooks MUST be importable via `import { useUpdateAdminUser, useForceLogoutAdminUser } from "@/modules/admin/hooks/useAdminUsers"` — co-located with the existing read hook.

**AC-11 — Frontend vitest tests V5-V10 appended to `UsersPage.test.tsx`.**

- Given the Story 8.2 vitest test file at `apps/web/src/modules/admin/UsersPage.test.tsx` (4 tests V1-V4 passing),
- When Story 8.3 ships,
- Then the file MUST gain 6 NEW tests:

  | # | Name | Asserts |
  |---|------|---------|
  | V5 | `renders an actions kebab button for every non-self non-agent row` | Mock useAdminUsers to return 3 rows: 1 admin (the current-user mock), 1 member, 1 agent. Render. Assert: the member's row has an enabled kebab button (`screen.getByRole("button", { name: /Actions for member/ })`); the agent's row has a disabled kebab button (`aria-disabled="true"`); the admin's own row has a disabled kebab button. |
  | V6 | `opens action menu on kebab click and lists 4 items for active user` | Mock + render with a single active member row. Click the kebab. Assert: 4 menu items visible — "Change role", "Deactivate", "Force logout all sessions" (Reactivate is NOT visible because is_active===true). |
  | V7 | `opens action menu and shows Reactivate instead of Deactivate for inactive user` | Mock with a single is_active=false member row. Open menu. Assert: "Reactivate" visible, "Deactivate" NOT visible. |
  | V8 | `clicking Deactivate opens confirm modal then PATCH on confirm` | Mock + render single active member. Open menu → click "Deactivate". Assert ConfirmDialog opens with the deactivate-title text. Click Confirm. Assert `useUpdateAdminUser`'s mutate was called with `{user_id: member.id, body: {is_active: false}}`. |
  | V9 | `clicking Force logout opens confirm modal then POST on confirm` | Same shape as V8 but for force-logout. Assert `useForceLogoutAdminUser`'s mutate was called with the member.id. |
  | V10 | `renders NO checkbox column header even with the new Actions column (FR5-ADMIN-4 negative AC regression guard)` | Mock + render 5 rows. Assert `screen.queryAllByRole("checkbox").length === 0` AND `screen.queryAllByRole("button", { name: /bulk|select all/i }).length === 0`. The Actions column adds a per-row menu, NOT a per-row checkbox. **Binding negative-AC regression guard at the V4 level — V10 is the Story-8.3 continuation of V4.** |

- And V5-V10 MUST coexist with V1-V4 (NO deletion or modification of V1-V4). The total UsersPage vitest count grows from 4 → 10.
- And `cd apps/web && npm run vitest -- UsersPage` MUST return 10/10 green.

**AC-12 — `ChangeRoleModal.test.tsx` at NEW `apps/web/src/modules/admin/ChangeRoleModal.test.tsx` (3 tests R1-R3).**

- Given the AC-8 component shape,
- When Story 8.3 ships,
- Then the test file MUST exist with 3 tests:
  - **R1** — `renders role select with current target role pre-selected` — render `<ChangeRoleModal open={true} target={{role: "member", ...}} ... />`. Assert the `<select>` has `value="member"`.
  - **R2** — `agent option is disabled in the select` — render. Find the agent option. Assert `option.disabled === true`.
  - **R3** — `confirm button calls onConfirm with selected role` — render with target.role="member". Change select to "admin". Click Confirm. Assert `onConfirm` was called once with `"admin"`.
- And `cd apps/web && npm run vitest -- ChangeRoleModal` returns 3/3 green.

**AC-13 — Frontend Playwright spec updated at `apps/web/tests/visual/admin-users.spec.ts` (modified existing 5 tests + 1 NEW Test 6).**

- Given the Story 8.2 spec at `apps/web/tests/visual/admin-users.spec.ts:1-160` shipping 5 tests + the empty/one-row/many-rows baselines,
- When Story 8.3 ships,
- Then the spec MUST:
  - **Regenerate the 3 baseline screenshots** (`admin-users-empty.png`, `admin-users-one-row.png`, `admin-users-many-rows.png`) to include the new Actions column. The regeneration is committed in the same dev commit as the source code change. `npm run test:visual -- --update-snapshots admin-users` runs once at dev time; the diff lists the 3 baseline-PNG changes alongside the source code.
  - **Test 4 (FR5-ADMIN-4 negative AC) MUST continue to pass UNCHANGED** — the Actions column adds a kebab button, NOT a checkbox; `page.locator('table input[type="checkbox"]').count() === 0` remains true.
  - **Test 5 (AdminTabs disabled regression guard) MUST continue to pass UNCHANGED** — Story 8.3 does not touch AdminTabs.
  - **NEW Test 6 — `kebab-menu-opens-and-shows-four-actions`:** stub `/api/admin/users` with a single active member row. Stub `/api/auth/me` returning the admin identity. Navigate to `/admin/users`. Click the kebab button (`page.getByRole("button", { name: /Actions for member/ })`). Assert 4 menu items appear: "Change role", "Deactivate", "Force logout all sessions" (+ optionally "Reactivate" — the spec asserts the 3 expected for the active row are present AND "Reactivate" is NOT). Optional screenshot: `admin-users-kebab-open.png` to baseline the menu shape (recommended but not strictly required — if the menu's CSS shifts in the future, a screenshot catches it; if it doesn't ship in 8.3, that's a Story 8.4+ deliverable).
  - **NEW Test 7 — `kebab-disabled-on-self-and-agent-rows`:** stub with 3 rows (admin = own row, agent, member). Navigate. Assert the admin's kebab button has `aria-disabled="true"` AND the agent's kebab button has `aria-disabled="true"` AND the member's kebab button does NOT (it is enabled).
- And the spec MUST pass `cd apps/web && npm run test:visual -- admin-users` after first-time baseline regeneration. Test count grows from 5 → 7.

**AC-14 — Audit registry compatibility check (zero-touch on `app/core/audit.py`).**

- Given the audit registry at `apps/api/app/core/audit.py:33-35` already documents Story 8.3 actions in the `# user — ...` docblock,
- When Story 8.3 ships,
- Then `app/core/audit.py` MUST NOT be modified. The 4 action names (`user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`) reuse the existing `user` entity_type from `KNOWN_ENTITY_TYPES` (per FR5-AUDIT-1 §1200 verbatim "actions are convention; entity_types are the registry"). No new `KNOWN_ENTITY_TYPES` entry is needed; no docstring rewording is needed (the docstring already names Story 8.3).
- And `grep -n "user.role_changed\|user.deactivated\|user.reactivated\|user.force_logout" apps/api/app/core/audit.py` returns ≥4 lines confirming the registry references stay intact.

**AC-15 — Pre-flight grep checklist (Story 8.3 close-out invariants, mirroring Story 8.2 AC-11 precedent).**

Before the dev commit lands, the developer agent MUST run the following greps and confirm each returns the expected result:

1. `grep -nE "PATCH|patch.*users|@router.patch" apps/api/app/modules/admin/router.py` returns ≥1 line matching the new PATCH handler.
2. `grep -nE "force-logout|force_logout" apps/api/app/modules/admin/router.py` returns ≥1 line matching the new POST handler.
3. `grep -n "UserMutationRequest" apps/api/app/modules/admin/users_schemas.py apps/api/app/modules/admin/router.py` returns ≥2 lines (schema definition + endpoint consumer).
4. `grep -n "extra=\"forbid\"" apps/api/app/modules/admin/users_schemas.py` returns ≥1 line (the AC-4 binding).
5. `grep -n "is_active" apps/api/app/modules/auth/router.py` returns ≥2 lines (the new gates in login() AND refresh()).
6. `grep -n "account_deactivated" apps/api/app/modules/auth/router.py` returns ≥2 lines (the AC-3 binding string in both login + refresh paths).
7. `grep -n "cannot_target_self\|cannot_target_agent\|cannot_promote_to_agent\|no_mutation_provided" apps/api/app/modules/admin/router.py` returns ≥4 lines (one per guard literal).
8. `grep -n "user.role_changed\|user.deactivated\|user.reactivated\|user.force_logout" apps/api/app/modules/admin/router.py` returns ≥4 lines (the four `record_event(action=...)` call sites).
9. `grep -rn "input\[type=.checkbox.\]\|select all\|bulk" apps/web/src/modules/admin/ apps/web/src/routes/admin/ apps/web/tests/visual/admin-users.spec.ts` ONLY matches inside `admin-users.spec.ts` (the spec's negative-AC assertions remain the ONLY legitimate matches — Story 8.2 AC-11 §5 invariant continues to hold).
10. `grep -n "useUpdateAdminUser\|useForceLogoutAdminUser" apps/web/src/modules/admin/` returns ≥4 matches (hook exports + UsersPage consumer references).
11. `grep -n "ChangeRoleModal" apps/web/src/modules/admin/UsersPage.tsx apps/web/src/modules/admin/ChangeRoleModal.tsx` returns ≥2 matches.
12. `grep -n "admin.users.actions.\|admin.users.confirm.\|admin.users.errors." apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns ≥32 matches (16 keys × 2 files = 32).
13. `jq 'keys | length' apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns the SAME integer.
14. `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` ≥ pre-Story-8.3 baseline + 10 (the new Polish strings carry diacritics).
15. `cd apps/api && .venv/bin/pytest tests/test_admin_users_mutations.py tests/test_auth_deactivated_user.py -v` returns 16/16 green (12 + 4).
16. `cd apps/api && .venv/bin/pytest tests/test_admin_users_list.py -v` returns 8/8 green (Story 8.2 regression guard — no breakage).
17. `cd apps/web && npm run vitest -- UsersPage` returns 10/10 green (V1-V10).
18. `cd apps/web && npm run vitest -- ChangeRoleModal` returns 3/3 green (R1-R3).
19. `cd apps/web && npm run test:visual -- admin-users` returns 7/7 green (5 existing + 2 new) against the regenerated baselines.
20. `infra/scripts/check-all.sh` returns ALL 13 stages green end-to-end.
21. `git log --oneline -1` shows the Story 8.3 dev commit as a single atomic commit (`feat(api,web,tests): per-user actions (Story 8.3)` or similar).

All 21 checks are AC-15 binding; a failure on any of them is a pre-merge blocker.

## Tasks / Subtasks

- [ ] **T1 — Author `UserMutationRequest` schema appended to `apps/api/app/modules/admin/users_schemas.py`** (AC-4)
  - [ ] T1.1 Read the existing file 1-42 to confirm import shape + ConfigDict convention.
  - [ ] T1.2 Append the new class with `extra="forbid"` + the docstring binding the four guards.
  - [ ] T1.3 Verify import: `cd apps/api && .venv/bin/python -c "from app.modules.admin.users_schemas import UserMutationRequest; print(UserMutationRequest.model_fields.keys())"` prints `dict_keys(['role', 'is_active'])`.

- [ ] **T2 — Add PATCH + POST endpoints to `apps/api/app/modules/admin/router.py`** (AC-1, AC-2)
  - [ ] T2.1 Read `admin/router.py:1-217` (the existing file) to understand the surrounding endpoint conventions.
  - [ ] T2.2 Add `@router.patch("/users/{user_id}", status_code=204, summary="...")` handler implementing AC-1: validate body, resolve target, fire the 4 guards, compute before-state, apply mutations, emit audit per mutated field, return 204.
  - [ ] T2.3 Add `@router.post("/users/{user_id}/force-logout", status_code=204, summary="...")` handler implementing AC-2: 2 guards, burn-all-families, emit audit, return 204.
  - [ ] T2.4 Verify route registration: `cd apps/api && .venv/bin/python -c "from app.modules.admin.router import router; print([(r.path, r.methods) for r in router.routes])"` lists both new paths.

- [ ] **T3 — Add `is_active` enforcement gate to `apps/api/app/modules/auth/router.py::login()` and `refresh()`** (AC-3, regression fix)
  - [ ] T3.1 Read `auth/router.py:63-168` (login handler) and `auth/router.py:223-338` (refresh handler).
  - [ ] T3.2 In `login()`: insert the `if not user.is_active:` gate AFTER `verify_password()` returns truthy AND BEFORE the TOTP partial-auth branch. Emit `auth.login.fail` with reason `account_deactivated`. Raise 401 with detail `account_deactivated`.
  - [ ] T3.3 In `refresh()`: insert the `if not user.is_active:` gate AFTER `rotate_refresh()` succeeds AND `user = session.get(User, target.user_id)` resolved AND BEFORE `set_session_cookies()`. Call `burn_family(session, target.family_id)` + commit + emit `auth.login.fail` with reason `account_deactivated`. Raise 401 with detail `account_deactivated`.
  - [ ] T3.4 Verify locally: deactivate a user via DB manipulation OR via the new PATCH endpoint; their next `/refresh` returns 401 + `account_deactivated`; their next `/login` returns 401 + `account_deactivated`.

- [ ] **T4 — Write backend mutation tests at NEW `apps/api/tests/test_admin_users_mutations.py`** (AC-5)
  - [ ] T4.1 Copy the `_seed_members` + `_admin_token` + `_set_admin_cookie` helpers from `tests/test_admin_users_list.py:32-80` verbatim (acknowledged duplication per §6 file-structure note).
  - [ ] T4.2 Author a `_seed_active_refresh_token(session, user_id, family_id=None)` helper at top of the file (mints a RefreshToken row with hashed secret + active state).
  - [ ] T4.3 Implement the autouse `_clear_user_and_audit_and_refresh_tables` fixture (preserves seeded admin, wipes User + AuditLog + RefreshToken).
  - [ ] T4.4 Implement M1-M12 per the AC-5 table.
  - [ ] T4.5 Verify: `cd apps/api && .venv/bin/pytest tests/test_admin_users_mutations.py -v` returns 12/12 green.

- [ ] **T5 — Write backend deactivation-flow tests at NEW `apps/api/tests/test_auth_deactivated_user.py`** (AC-6)
  - [ ] T5.1 Adopt the conftest `isolated_client` fixture + the per-file autouse cleanup.
  - [ ] T5.2 Author a `_seed_login(client, email, password)` helper that posts `/api/auth/login` and captures the cookies into the TestClient.
  - [ ] T5.3 Implement D1-D4 per the AC-6 table.
  - [ ] T5.4 Verify: `cd apps/api && .venv/bin/pytest tests/test_auth_deactivated_user.py -v` returns 4/4 green.

- [ ] **T6 — Append `useUpdateAdminUser` + `useForceLogoutAdminUser` to `useAdminUsers.ts`** (AC-10)
  - [ ] T6.1 Read the existing file 1-35 for the import + return-shape conventions.
  - [ ] T6.2 Append the two new mutation hooks per AC-10 with `useMutation` + `useQueryClient` + onSuccess-invalidate.
  - [ ] T6.3 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T7 — Author `ChangeRoleModal.tsx` at NEW `apps/web/src/modules/admin/ChangeRoleModal.tsx`** (AC-8)
  - [ ] T7.1 Read `apps/web/src/ui/custom/ConfirmDialog.tsx` for the modal structure precedent.
  - [ ] T7.2 Implement the modal per AC-8 with the role select (agent option disabled) + the confirm button gated by the no-op check.
  - [ ] T7.3 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T8 — Modify `UsersPage.tsx` to add the Actions column + DropdownMenu integration** (AC-7)
  - [ ] T8.1 Read `apps/web/src/modules/catalog/components/ModelHero.tsx:104-129` for the DropdownMenu + MoreVertical kebab precedent.
  - [ ] T8.2 Add the 8th column header + 8th `<td>` per row with the kebab button + DropdownMenu shipping the 4 action items per AC-7.
  - [ ] T8.3 Add the disabled state for own + agent rows (using `useAuth().user?.id` and `user.role === "agent"` checks).
  - [ ] T8.4 Wire the 3 modal-state useState slots + the 2 mutation hooks + the inline error message bar.
  - [ ] T8.5 Add ConfirmDialog usage for deactivate/reactivate/force-logout (3 separate slots; the modal is reused, the props differ per action).
  - [ ] T8.6 Verify `cd apps/web && npm run typecheck` + `npm run lint` are green.

- [ ] **T9 — Append api-types entries to `apps/web/src/lib/api-types.ts`** (story foundation §10)
  - [ ] T9.1 Read lines 199-220 (the Story 8.2 admin block) to find the insertion point.
  - [ ] T9.2 Append a NEW `// --- Admin users mutations (Story 8.3) ---` section with the `UserMutationRequest` interface.
  - [ ] T9.3 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T10 — Append i18n keys to en.json + pl.json** (AC-9)
  - [ ] T10.1 Insert the 16 new keys + `admin.users.column_actions` after the Story 8.2 admin block in BOTH locale files.
  - [ ] T10.2 Verify diacritics: `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` grew by ≥10.
  - [ ] T10.3 Verify key-set parity: `jq 'keys | length' apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns the same integer.

- [ ] **T11 — Append vitest V5-V10 to `UsersPage.test.tsx`** (AC-11)
  - [ ] T11.1 Read the existing V1-V4 tests to understand the mock-hook + render-with-i18n-passthrough pattern.
  - [ ] T11.2 Add a vi.mock for the two new mutation hooks (return `{mutate: vi.fn(), isPending: false, isError: false, error: null}` shape).
  - [ ] T11.3 Add a vi.mock for `useAuth()` returning the admin identity (used by the disabled-state checks).
  - [ ] T11.4 Implement V5-V10 per the AC-11 table.
  - [ ] T11.5 Verify `cd apps/web && npm run vitest -- UsersPage` returns 10/10 green.

- [ ] **T12 — Write `ChangeRoleModal.test.tsx`** (AC-12)
  - [ ] T12.1 Implement R1-R3 per the AC-12 table.
  - [ ] T12.2 Verify `cd apps/web && npm run vitest -- ChangeRoleModal` returns 3/3 green.

- [ ] **T13 — Regenerate Playwright baselines + add Test 6 + Test 7** (AC-13)
  - [ ] T13.1 Update the fixture data in `admin-users.spec.ts` to include `display_name` consistent with the new Actions column rendering.
  - [ ] T13.2 First-time regeneration: `cd apps/web && npm run test:visual -- --update-snapshots admin-users`. Commit the 3 regenerated PNGs.
  - [ ] T13.3 Add Test 6 (kebab-menu interaction) + Test 7 (disabled state on self + agent rows) per AC-13.
  - [ ] T13.4 Verify regression mode: `cd apps/web && npm run test:visual -- admin-users` returns 7/7 green.

- [ ] **T14 — Run AC-15 pre-flight grep checklist** (AC-15)
  - [ ] T14.1 Execute all 21 checks; capture grep + test outputs.
  - [ ] T14.2 If any check fails, fix the underlying gap before committing.

- [ ] **T15 — Dev commit + sprint-status flip** (close-out)
  - [ ] T15.1 Single squashed `feat(api,web,tests): per-user actions — role, deactivate, force-logout (Story 8.3)` commit covering ALL new + modified files. Commit body cites Decision I §1622-1630 + epics §1776-1787 + AC-3 regression fix as a top-line bullet (the regression fix is the most consequential change for users in production today).
  - [ ] T15.2 Commit message ends with the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
  - [ ] T15.3 Update sprint-status: flip `8-3-per-user-actions-role-deactivate-force-logout` from `ready-for-dev` → `review` (NOT `done` — Codex review is the canonical post-dev gate per Epic 7 retro §3).
  - [ ] T15.4 Run `infra/scripts/deploy.sh` per `feedback_auto_deploy_dev` after merge to main.

## Dev Notes

### Architectural anchors

- **Decision I §1601-1630** — the binding spec for is_active soft-delete + the AC-3 enforcement gate on login + refresh + the FR5-ADMIN-4 negative bound. Story 8.3 ships the WRITE side of Decision I in full. Read in full before T2 + T3.
- **Epics §1776-1787** — the Story 8.3 acceptance check shape verbatim including the four-action surface + the deactivation-end-to-end binding "target user with `is_active = FALSE` attempting `POST /api/auth/refresh` returns HTTP 401 + emits `auth.login.fail` reason `account_deactivated` + invalidates the refresh-token family". Read in full before T3 + T5.
- **PRD §1194 FR5-ADMIN-2** — the binding PRD-tier requirement for the per-user actions: change role, force 2FA enrollment (Story 8.4 — out of scope here), issue password reset link (Story 8.5 — out of scope), deactivate, force logout-all-sessions, reactivate.
- **PRD §1196 FR5-ADMIN-4** — the deliberate-exclusion guardrail: no bulk operations. Story 8.3 mirrors Story 8.2's negative AC at the new Actions column (the column adds a per-row menu, NOT a per-row checkbox).
- **PRD §1200 FR5-AUDIT-1** — the 4 Story 8.3 action names already documented; reuse the existing `user` entity_type; no registry expansion.
- **NFR5-INT-1 / Architecture §1411 §1488** — the agent service account is panel-untouchable. Story 8.3's AC-1 + AC-2 + AC-7 + AC-13 all mirror this guard.
- **Architecture §1049** — the agent role is created by `python -m scripts.bootstrap_agent --email agent@portal.local --rotate`, NOT via the admin panel. Story 8.3's AC-1 promote-to-agent guard enforces this.
- **Story 8.1 spec** at `_bmad-output/implementation-artifacts/8-1-alembic-0014-is-active-last-active-middleware.md` — the migration that added `user.is_active`. Story 8.3 is the consumer that makes the column gate-active.
- **Story 8.2 spec** at `_bmad-output/implementation-artifacts/8-2-admin-users-tab-paginated-list.md` — the predecessor that ships the read endpoint + Users tab. Story 8.3 modifies UsersPage.tsx + appends to UsersPage.test.tsx + appends to admin-users.spec.ts.

### Critical files to read before touching

- `apps/api/app/modules/admin/router.py:1-217` — Story 8.2's file; understand the existing GET handler convention before adding PATCH + POST peers.
- `apps/api/app/modules/admin/users_schemas.py:1-42` — Story 8.2's file; the new `UserMutationRequest` class is appended here.
- `apps/api/app/modules/auth/router.py:63-168` (login handler) + `:223-338` (refresh handler) — the regression-fix touch points.
- `apps/api/app/core/auth/refresh.py:93-105` (`burn_family` helper) — Story 8.3 reuses this from `refresh()` for the deactivate-burn path AND the force-logout path.
- `apps/api/app/modules/auth/router.py:420-447` (`logout_all` handler) — the closest precedent for the per-user-revoke-all-families pattern; Story 8.3's AC-2 handler is the admin-side mirror.
- `apps/api/app/core/audit.py:33-35` — the registry's docblock already names Story 8.3 actions; do not modify.
- `apps/api/app/core/auth/dependencies.py:55-76` — the `current_admin` dependency Story 8.3 inherits unchanged.
- `apps/api/app/core/db/models/_user.py:20-40` — the SQLModel; the new endpoint reads + writes `is_active` + `role` fields.
- `apps/api/tests/test_admin_users_list.py:32-80` — Story 8.2's test helpers; Story 8.3's new test file duplicates these inline.
- `apps/api/tests/conftest.py:64-124` — the `isolated_client` fixture (Story 8.1 promotion).
- `apps/web/src/modules/admin/UsersPage.tsx:1-266` — Story 8.2's file; the major frontend touch point.
- `apps/web/src/modules/catalog/components/ModelHero.tsx:104-129` — the kebab + DropdownMenu + MoreVertical precedent.
- `apps/web/src/ui/custom/ConfirmDialog.tsx:1-71` — the modal precedent + the destructive variant.
- `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-35` — Story 8.2's file; the new mutation hooks are appended here.
- `apps/web/src/shell/AuthContext.tsx` — the `useAuth()` hook (used by AC-7 for the own-row check).
- `apps/web/tests/visual/admin-users.spec.ts:1-160` — Story 8.2's spec; baselines regenerate + Test 6 + Test 7 add here.

### Library/framework versions to respect

- **FastAPI 0.115+** — `@router.patch("/users/{user_id}", status_code=204)` is the canonical PATCH declaration; the path param is auto-converted to `uuid.UUID` from the type hint. `HTTPException(status.HTTP_400_BAD_REQUEST, detail="cannot_target_self")` is the canonical 400-with-detail shape.
- **Pydantic 2.9** — `model_config = ConfigDict(extra="forbid")` rejects unknown fields. `model_fields_set` exposes which fields were explicitly set in the request body (distinct from defaults). `Optional[X]` is equivalent to `X | None = None`.
- **SQLAlchemy 2.x / SQLModel 0.0.22** — `session.get(User, user_id)` returns `User | None` for the lookup. `session.exec(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))).all()` is the dialect-portable family-listing query.
- **TanStack Query 5.x** — `useMutation({mutationFn, onSuccess})` is the v5 API. `queryClient.invalidateQueries({queryKey: ["admin", "users"]})` invalidates the entire `["admin", "users", ...]` subtree (all paginations + filters). The variable type in `useMutation<TData, TError, TVariables>` is the third parameter.
- **Radix DropdownMenu (via `@/ui/dropdown-menu`)** — the existing wrapper at `apps/web/src/ui/dropdown-menu.tsx`. `<DropdownMenuItem>` uses `onSelect` (NOT `onClick`) for the action callback; `onSelect` fires AFTER the menu closes which is the correct ordering for opening a follow-up modal.
- **lucide-react MoreVertical** — already imported in `apps/web/src/modules/catalog/components/ModelHero.tsx:1`; reuse the same import path verbatim.
- **react-i18next v23+** — `t("admin.users.confirm.deactivate_title", {email})` interpolates `{{email}}` per the {{var}} convention. The Polish strings use proper diacritics per the global directive.

### File structure requirements

- **NEW endpoints (PATCH + POST force-logout) MUST live in the existing `apps/api/app/modules/admin/router.py`** — NOT in a new `users_router.py`. Per Story 8.2 file-structure rationale §400: the per-resource sub-router promotion is a Story 8.4+ deliberate refactor candidate, NOT a Story 8.3 accidental side-effect. The cumulative endpoint count in admin/router.py after Story 8.3 is 5 (sentry-test, audit, audit-log, users-list from 8.2, users-patch + users-force-logout from 8.3); the file remains under 300 LOC and the sub-router promotion threshold is not yet justified.
- **NEW schema (UserMutationRequest) MUST live in the existing `apps/api/app/modules/admin/users_schemas.py`** — NOT in a new `users_mutations.py`. Co-locate request + response schemas in one file (matches the `invite/admin_schemas.py` convention where InviteListItem + InviteListResponse + InviteRevokeRequest all live in one file).
- **NEW test files live as peers of Story 8.2's:** `apps/api/tests/test_admin_users_mutations.py` + `apps/api/tests/test_auth_deactivated_user.py`. Naming follows the `test_<feature>_<action>.py` convention from `test_admin_users_list.py` + `test_invite_admin.py`.
- **NEW frontend modal `ChangeRoleModal.tsx`** lives at `apps/web/src/modules/admin/ChangeRoleModal.tsx` — peer of UsersPage.tsx; mirrors the `Reauth2faModal.tsx` precedent at `apps/web/src/modules/auth/` (modal-as-peer-of-page, NOT modal-in-ui-folder).
- **The ConfirmDialog reuse (NO new file):** the deactivate/reactivate/force-logout confirms reuse `apps/web/src/ui/custom/ConfirmDialog.tsx` verbatim — do NOT create a `DeactivateConfirmModal.tsx` or similar; the existing component takes title/description/destructive props that cover all three cases.
- **NEW hook exports** are APPENDED to the existing `useAdminUsers.ts` — NOT in separate files (`useUpdateAdminUser.ts`, `useForceLogoutAdminUser.ts`). The per-resource hook file convention (`useSessions.ts`, `useAdminUsers.ts`) is preserved.

### Testing requirements

- **AC-5 mutation tests M1-M12 MUST pass in isolation AND together.** Run `pytest tests/test_admin_users_mutations.py -v` (isolation) and `pytest tests/ -k "admin_users" -v` (together-with-Story-8.2). The `_clear_user_and_audit_and_refresh_tables` autouse fixture handles inter-test isolation.
- **AC-6 deactivation tests D1-D4 MUST pass in isolation AND together.** Especially D3 + D4 (golden-path regression guards) must stay green to prove the new gate does not regress active-user flows.
- **AC-11 vitest V5-V10 MUST pass in isolation AND together with V1-V4.** The total UsersPage vitest count is 10. Run `npm run vitest -- UsersPage`.
- **AC-13 Playwright Tests 6-7 MUST pass in isolation AND together with Tests 1-5.** Tests 1-3 (baseline screenshots) need regeneration via `--update-snapshots` ONCE at dev time; subsequent CI runs compare against the new baselines.
- **`infra/scripts/check-all.sh` 13/13 green** — Story 8.3 does NOT add new stages.
- **Codex review fix-up budget: expect 0-4 fix-ups.** The most likely surface areas:
  - (a) The deactivate-burn-families path: should it run BEFORE or AFTER the `record_event` call? Codex may flag the ordering if the audit fires but the burn fails (transactional consistency); current spec puts both in one `session.commit()` which is correct, but the audit log uses a separate session per `app/core/audit.py:85` — the burn-commit + audit-commit are independent so audit emission may succeed even if burn rolls back. Acceptable per existing project convention (the audit IS the source of truth for "what was attempted"; the DB row is the source of truth for "what landed"); flag as P3 if Codex insists.
  - (b) The login-fail audit on AC-3 deactivated-user-login emits with `actor_user_id=None` (anonymous login attempt) — Codex may flag that the `user.id` is known by then. Defensible: the existing `invalid_credentials` path also uses `actor_user_id=None` (auth/router.py:84-91 verbatim); maintaining consistency on the `actor_user_id` semantic is correct. The user is identified by `entity_id`, not `actor_user_id`.
  - (c) The refresh-deactivated audit emits with `actor_user_id=user.id` (not None) — divergence from (b) above is intentional: in refresh(), the user IS authenticated by the refresh-cookie possession; the `actor` is the user themselves (their own session is being burned). In login(), the cookie hasn't been issued yet so the user is not yet an authenticated actor.
  - (d) Frontend: the disabled kebab on own row uses `useAuth().user?.id` — Codex may flag that the field could be undefined during loading; the `?.` chain handles it, but a Codex pass may suggest a more defensive `isLoading` check. Add if requested.
- **0 fix-ups expected on the schemas + i18n + hooks** — those are mechanical from the existing precedents.

### Previous story intelligence (Stories 8.1 + 8.2 carryover)

- **Story 8.1 `LastActiveMiddleware` is untouched.** The Story 8.3 AC-3 gates fire AT THE AUTH-ROUTER LAYER (in login + refresh handlers); the middleware sits AT THE MIDDLEWARE LAYER and only triggers on authenticated requests that pass through. A deactivated user's `/refresh` 401s in the handler BEFORE the middleware runs — the middleware chain short-circuits on the HTTPException. Story 8.1's `test_last_active_throttle.py` MUST stay green; verify by running it explicitly post-merge.
- **Story 8.2 conftest + helpers** — Story 8.3 inherits `isolated_client` (the Story 8.1 promotion) + the `_admin_token` / `_set_admin_cookie` / `_seed_members` shape from `tests/test_admin_users_list.py`. Duplicate inline; do NOT construct a `_helpers` module (Story 8.4+ refactor candidate).
- **Story 8.2 UsersPage scope:** Story 8.2 explicitly deferred per-row actions to Story 8.3 (Story 8.2 §59 verbatim). The Actions column is the Story 8.3 deliverable; the 7 existing columns + their sort behavior MUST stay untouched.
- **Story 8.2 visual baseline pattern:** Story 8.2's baselines (empty/one-row/many-rows) were the BEFORE snapshot; Story 8.3 updates them AFTER per the consecutive-stories-own-consecutive-baselines convention (Story 8.2 §419 verbatim). Regeneration via `--update-snapshots` is expected, NOT a Codex-flag-worthy event.
- **Story 8.2 i18n key budget** — 23 keys added; Story 8.3 appends 16 more (16+1 column key = 17 if we count `admin.users.column_actions` separately; the AC-9 table lists 16 + 1). The Polish-diacritic requirement persists; new strings carry `ą/ę/ć/ł/ó/ś/ź/ż` per the AC-15 §14 grep check.
- **Story 8.2 FR5-ADMIN-4 negative-AC enforcement** — the Story 8.2 invariant (zero checkboxes, zero bulk-action lexicon) persists into Story 8.3. The Actions column adds a per-row kebab MENU; it does NOT add a per-row checkbox. V10 + Test 4 are the regression guards.
- **Story 8.1 BUG (now closed by Story 8.3 AC-3):** between Story 8.1 ship and Story 8.3 ship, the `is_active=False` state was VISIBLE in the panel (Story 8.2) but NOT ENFORCED at the auth router (no login/refresh check existed). Story 8.3 closes the gap. Operator post-Story-8.3 verification: deactivate a real `.190` user → their `/refresh` returns 401 within ≤10 minutes → cookie expires → their `/login` returns 401.
- **Auto-deploy after merge** — per `feedback_auto_deploy_dev`, run `infra/scripts/deploy.sh` to `.190` after Story 8.3 merges to main. The deploy-gate range check determines no-op vs run; Story 8.3 has code changes so deploy WILL run.

### Git intelligence (recent commits)

```
ec5ac5d fix(api): Story 8.2 codex P2 — stable tie-breaker on user list pagination
6bd7475 feat(api,web): Admin Users tab + paginated list (Story 8.2)
195fb22 fix(api): Story 8.1 codex P2 fix-up — monotonic UPDATE + asyncio.to_thread
80eebc9 feat(api,infra): alembic 0014 is_active + last_active + LastActiveMiddleware (Story 8.1)
9dedc81 fix(infra): Story 7.6 codex fix-up — drill script hardening
```

Pattern (Epic 7 + 8 baseline): each story lands as `feat(<scopes>): <subject> (Story X.Y)` initial commit, then 1-2 `fix(...)` Codex P2 follow-up commits on the same story-scoped subject before sprint-status flips `review` → `done`. Story 8.3's commit shape: `feat(api,web,tests): per-user actions — role, deactivate, force-logout (Story 8.3)`.

### Project Structure Notes

- **Alignment with unified project structure:** all new files land in their natural locations (mutation schema appended to `apps/api/app/modules/admin/users_schemas.py`; new endpoints in the existing `admin/router.py`; new test files under `apps/api/tests/`; new frontend modal in `apps/web/src/modules/admin/`; hook appended to the existing `useAdminUsers.ts`; i18n keys in the existing locale files). NO new top-level directories.
- **Detected conflicts or variances:** Story 8.1 shipped the schema + middleware for is_active soft-delete BUT NEVER implemented the auth-router enforcement gate per Decision I §1622-1623 verbatim. This is the gap Story 8.3 closes. The variance is a known acceptance-criteria-incomplete-on-Story-8.1 that surfaced at Story 8.2 retro (Story 8.2 explicitly out-of-scoped the enforcement per its §62 boundary, deferring to Story 8.3). Story 8.3 owns the close-out per epics §1786 verbatim.
- **Naming conventions:** the new endpoint path `/api/admin/users/{user_id}` (PATCH) follows the project's REST-resource convention. The force-logout sub-resource `/api/admin/users/{user_id}/force-logout` (POST) follows the project's REST-action-as-sub-resource convention (compare `/api/admin/invites/{id}/revoke` from Story 6.3, `/api/auth/2fa/recovery-codes/regenerate` from Story 7.5). The new schema `UserMutationRequest` follows the project's `<Resource><Action>Request` convention (compare `InviteRevokeRequest`, `TotpConfirmRequest`).

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-I-Soft-delete-+-last_active_at-throttling`] (lines 1601-1630) — the binding spec for is_active enforcement + the panel actions
- [Source: `_bmad-output/planning-artifacts/architecture.md#NFR5-INT-1`] (lines 1411, 1488) — agent service account preservation
- [Source: `_bmad-output/planning-artifacts/architecture.md#Agent-bootstrap`] (line 1049) — agent role created by bootstrap script
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-8.3`] (lines 1776-1787)
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-2`] (line 1194) — the binding PRD requirement
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-4`] (line 1196) — the FR5-ADMIN-4 deliberate exclusion (no bulk operations)
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-AUDIT-1`] (line 1200) — the 16 audit-action surface; Story 8.3 uses 4 of them
- [Source: `_bmad-output/implementation-artifacts/8-1-alembic-0014-is-active-last-active-middleware.md`] — the migration + middleware Story 8.3 builds upon
- [Source: `_bmad-output/implementation-artifacts/8-2-admin-users-tab-paginated-list.md`] — the predecessor Story 8.3 modifies (UsersPage + tests + Playwright + i18n)
- [Source: `apps/api/app/modules/admin/router.py:1-217`] — the file Story 8.3 modifies (add PATCH + POST endpoints)
- [Source: `apps/api/app/modules/admin/users_schemas.py:1-42`] — Story 8.2's schema file Story 8.3 extends
- [Source: `apps/api/app/modules/auth/router.py:63-168` (login)] — the regression-fix touch point
- [Source: `apps/api/app/modules/auth/router.py:223-338` (refresh)] — the regression-fix touch point
- [Source: `apps/api/app/modules/auth/router.py:420-447` (logout_all)] — the closest precedent for revoke-all-families
- [Source: `apps/api/app/core/auth/refresh.py:93-105` (`burn_family`)] — the helper Story 8.3 reuses
- [Source: `apps/api/app/core/audit.py:33-35`] — the audit registry (already documents Story 8.3 actions)
- [Source: `apps/api/app/core/db/models/_user.py:20-40`] — the SQLModel `is_active` field
- [Source: `apps/api/tests/test_admin_users_list.py:32-80`] — Story 8.2's test helpers Story 8.3 duplicates inline
- [Source: `apps/api/tests/conftest.py:64-124`] — the `isolated_client` fixture (Story 8.1 promotion)
- [Source: `apps/web/src/modules/admin/UsersPage.tsx:1-266`] — Story 8.2's page; Story 8.3 modifies
- [Source: `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-35`] — Story 8.2's hook file Story 8.3 extends
- [Source: `apps/web/src/modules/catalog/components/ModelHero.tsx:104-129`] — kebab + DropdownMenu precedent
- [Source: `apps/web/src/ui/custom/ConfirmDialog.tsx:1-71`] — confirm-modal precedent
- [Source: `apps/web/src/shell/AuthContext.tsx`] — `useAuth()` hook for own-row detection
- [Source: `apps/web/tests/visual/admin-users.spec.ts:1-160`] — Story 8.2's spec; Story 8.3 extends + regenerates baselines
- [Source: `_bmad-output/project-context.md`] — FastAPI / SQLModel / vitest / Playwright conventions
- [Source: `AGENTS.md`] — repo layout + commit conventions + Polish-i18n requirement

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m]

### Debug Log References

### Completion Notes List

### File List
