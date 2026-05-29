# Story 8.5: Admin-issued password-reset link

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer (Ezop, banking-IT operator wearing the dev-team ITCM hat),
I want **the Epic 8 admin-issued password-reset link surface — admin mint + public consume — wired end-to-end on top of the Story 8.4 lockout-recovery flow, with a NEW Redis-fronted single-use opaque token primitive that mirrors the Story 6.2 invite-token shape (Decision A + B per epics §1809 verbatim "Decisions A + B (token shape reuse — Redis-fronted single-use opaque token)") at a NEW `apps/api/app/modules/auth/password_reset/` sub-module (per Story 8.4 §file-structure-requirements verbatim "Story 8.5's password-reset endpoints will push the file over 500 LOC + introduce a distinct Redis-token concern — THAT is the natural sub-router promotion point per the obvious-when-you-see-it architectural-deferral pattern"), plus the two audit emissions `auth.password.reset.initiated` (admin mint, `actor_user_id != entity_id`) + `auth.password.reset.completed` (public consume, `actor_user_id == entity_id`) per FR5-AUDIT-1 §1200 (both action names ALREADY documented in `app/core/audit.py:33-38` from the audit-registry pre-registration in Story 7.5 closing commit — zero-touch on the registry per AC-13), plus the foot-gun guardrails inherited from Stories 8.3 + 8.4 (cannot_target_self, cannot_target_agent) on the admin-mint endpoint, plus the public consume endpoint's zxcvbn ≥3 + ≥12-char password gate that REUSES the Story 6.4 register-endpoint helpers verbatim, plus the Redis GETDEL atomic single-use semantics (mirrors Story 7.3 partial-auth token claim pattern per `auth/totp/router.py:361-371` verbatim — no consume-race window), plus the new `/reset-password?token=<token>` React route at `apps/web/src/routes/reset-password.tsx` that mirrors `apps/web/src/routes/register.tsx` exactly (same TanStack Router shape, same password-strength UX, same i18n key family layout), plus a new "Issue password reset link" kebab menu item on the existing Story 8.3 per-row Actions column whose confirm flow opens a one-time `ResetLinkDisplayModal.tsx` rendering the returned `reset_url` (mirrors invite-token cleartext-surfaces-once UX from Story 6.3 §generate-invite verbatim), plus the rate-limit middleware reuse via Story 6.6 `register` scope (epics §1818 verbatim "Endpoint rate-limited via Story 6.6 middleware (`register` scope shared — 3 attempts / 60s per IP; reset and register share the public-write rate-limit budget by design)"), with all backend + frontend + audit + visual test layers wired in one atomic story per epics §1806-1818 acceptance gate verbatim**, namely:

1. **NEW backend sub-module `apps/api/app/modules/auth/password_reset/`** following the `apps/api/app/modules/auth/totp/` precedent (NOT the `apps/api/app/modules/invite/` precedent because there is NO `password_resets` DB table — Redis is the SOLE state surface per epics §1814 verbatim "NO DB-row audit history is needed at the password-reset-link tier — `auth.password.reset.initiated` audit row captures issuance; `auth.password.reset.completed` captures consumption"). Five new files: `__init__.py`, `service.py`, `router.py`, `admin_router.py`, `schemas.py`.

2. **NEW `service.py::PasswordResetService`** — Redis-only single-use opaque-token service constructed with `__init__(self, *, redis: Redis)` (NO `engine` arg unlike invite/service.py — no DB I/O). Two public async methods:
   - `async generate(*, user_id: uuid.UUID, generated_by_user_id: uuid.UUID, ttl_seconds: int) -> str` — mints `secrets.token_urlsafe(32)` (43-char URL-safe, 256-bit entropy, mirrors invite/service.py:117 verbatim), stores JSON `{user_id, generated_by_user_id, generated_at}` at Redis key `invite:reset:{token}` with `EX=ttl_seconds`, returns the cleartext token (the ONLY place cleartext leaves the service). The Redis prefix `invite:reset:` (NOT `password_reset:`) is the epics §1814 verbatim binding ("stores at Redis key `invite:reset:{token}`") — keeps the auth-token-namespace conceptually unified.
   - `async claim(token: str) -> uuid.UUID | None` — atomic `GETDEL invite:reset:{token}` (mirrors `auth/totp/router.py:369` verbatim — Redis 6.2+ `GETDEL` is a single indivisible op under Redis's single-threaded model). On hit: parses JSON, returns `user_id`. On miss (token never existed, expired, or already claimed by a racing request): returns `None`. The atomicity guarantees single-use: two concurrent `POST /api/auth/password-reset` calls with the same token can never both succeed because at most one observes a non-None value from GETDEL.
   - **Critical:** the service does NOT emit audit events — that is the router's responsibility (mirrors `apps/api/app/modules/invite/service.py:13-16` verbatim convention "Caller contract: audit emission (`auth.invite.generated` / `.used` / `.revoked`) is the caller's responsibility, mirroring the share-router precedent").

3. **NEW `admin_router.py::issue_password_reset_admin_user()`** at `POST /api/admin/users/{user_id}/password-reset`. Body: NONE (POST with empty body, mirrors Story 8.4 force-2fa-enrollment + force-disable-2fa). Returns `PasswordResetMintResponse(reset_url=...)` (NEW Pydantic v2 schema, see T5) — the cleartext token is embedded in `reset_url` ONCE; subsequent admin-panel reads cannot retrieve it (Redis is the sole holder, and listing endpoints DO NOT exist for password-reset tokens unlike invite-tokens). Three foot-gun guardrails baked at endpoint contract (mirror Stories 8.3 + 8.4 conventions verbatim):
   - **cannot_target_self** (400) — `target.id == admin_id`: the operator cannot issue a reset link to themselves. The operator's own password is rotated via DB-direct surgery on `.190` per Decision L §1741 "until self-hosted mail server arrives". Bypass attempts via this endpoint would create a paper-trail anomaly (`actor_user_id == entity_id` on `auth.password.reset.initiated`) that contradicts the binding FR5-ADMIN-3 audit shape per epics §1808.
   - **cannot_target_agent** (400) — `target.role == UserRole.agent`: NFR5-INT-1 — the agent service account's password is bootstrap-script-managed (`scripts.bootstrap_agent --rotate` per architecture.md:1049 verbatim); issuing a reset link via the panel would create a parallel rotation path that the bootstrap script does not coordinate with.
   - **user_not_found** (404) — `session.get(User, user_id)` returns `None`. Standard 404 shape.
4. **NEW `admin_router.py` audit emission** AFTER the successful Redis SET and BEFORE the response return: `record_event(action="auth.password.reset.initiated", entity_type="user", entity_id=target.id, actor_user_id=admin_id, after={"ttl_seconds": settings.password_reset_ttl_seconds}, request_id=...)`. **Critical:** `actor_user_id = admin_id` (the admin who triggered the mint) ≠ `entity_id = target.id` (the target user being reset) — the actor-pivot discriminator. The `after.ttl_seconds` payload captures the configured TTL for ops visibility (operator can answer "how long was the link valid?" from the audit row). NO `before` payload — the password is not in the before-state being mutated; that comes on consume.

5. **NEW `router.py::consume_password_reset()`** at `POST /api/auth/password-reset` (PUBLIC — no `current_user` dependency). Body: `PasswordResetConsumeRequest(token: str, new_password: str)` (NEW Pydantic v2 schema with `model_config = ConfigDict(extra="forbid")`, `token: str = Field(min_length=43, max_length=43)` matching `secrets.token_urlsafe(32)` output exactly per Story 6.4 §invite/schemas.py:27 verbatim, `new_password: str = Field(min_length=1)` with the meaningful zxcvbn + ≥12 policy enforced at the handler tier — NOT at the schema tier — so the failure surface emits the user-facing 422 + audit row per Story 6.4 §invite/router.py:48-52 verbatim convention). Returns 204 on success. The handler executes a deterministic 4-step sequence:
   - **Step 1 — atomic token claim:** `user_id = await service.claim(payload.token)`. If `None`: emit `auth.password.reset.completed` audit row with `after={"reason": "token_invalid"}` (NO `actor_user_id` because we cannot resolve user identity without the token), `entity_id=None`, raise `HTTPException(404, detail="token_invalid")`. **Critical:** unlike Story 6.4 register which distinguishes `token_invalid` (404) from `token_consumed` (410) via a DB-row lookup, password-reset has NO DB row to consult — Redis is the SOLE state surface, and `GETDEL` cannot distinguish "never existed" from "expired" from "already claimed". All three return 404 `token_invalid` (uniform-error surface protects against token-status enumeration attacks per Story 6.4 §invite/service.py:54-57 verbatim convention).
   - **Step 2 — password validation:** length-first (`len(new_password) < 12` → 422 + audit row reason `weak_password`), then zxcvbn score (`< 3` → 422 + audit row). Reuses the EXACT same `_MIN_PASSWORD_LEN = 12` + `_MIN_ZXCVBN_SCORE = 3` constants + the `_LEN_MSG` + `_SCORE_MSG` user-facing strings from `apps/api/app/modules/invite/router.py:48-52` (DO NOT redefine — `from app.modules.invite.router import _MIN_PASSWORD_LEN, _MIN_ZXCVBN_SCORE, _LEN_MSG, _SCORE_MSG` is acceptable Python-private-import for the inter-module-share since the constants are stable contract; if importing private names raises a lint-style objection from Codex, the alternative is to promote them to `apps/api/app/core/auth/password_policy.py` as a 4-line public module — DEFER that refactor to a follow-up if it surfaces, NOT a Story 8.5 in-scope task).
   - **Step 3 — password update:** `target = session.get(User, user_id)`. If `target is None` (the row was deleted between mint and consume): emit `auth.password.reset.completed` with `after={"reason": "user_not_found"}`, raise 404. Else: `target.password_hash = hash_password(new_password)` (reuses `apps/api/app/core/auth/password.py:hash_password` — bcrypt cost 12 per project convention), `session.add(target); session.commit()`. **Critical:** the user's existing refresh-token families are NOT proactively invalidated by this story — Decision I §1622 binds force-logout to the Story 8.3 PATCH/force-logout admin actions, NOT to password rotation. Rationale: operator typically invokes Story 8.3 force-logout BEFORE issuing a reset link (defense in depth), and the Story 8.4 force-disable-2fa step already invalidates `recovery_codes` for the lost-2FA recovery flow. If the operator wants session-burn coupled with password-reset, they invoke both admin actions in sequence — the panel makes this a 2-click flow.
   - **Step 4 — success audit:** `record_event(action="auth.password.reset.completed", entity_type="user", entity_id=target.id, actor_user_id=target.id, after={"email": target.email}, request_id=...)`. **Critical:** `actor_user_id == entity_id == target.id` (the user resetting their own password is both actor AND entity — the discriminator vs the admin-mint emission). NO cookies are issued on consume (the user must `POST /api/auth/login` with the new password afterwards; the consume endpoint is NOT a login endpoint).

6. **NEW `schemas.py`** with TWO Pydantic v2 models:
   ```python
   class PasswordResetConsumeRequest(BaseModel):
       model_config = ConfigDict(extra="forbid")
       token: str = Field(min_length=43, max_length=43)
       new_password: str = Field(min_length=1)

   class PasswordResetMintResponse(BaseModel):
       model_config = ConfigDict(frozen=True)
       reset_url: str
       expires_at: datetime.datetime
   ```
   The `expires_at` field is computed at mint time as `generated_at + timedelta(seconds=ttl_seconds)` and surfaced to the admin panel so the operator can see "how long does this link last?" without re-reading the TTL from settings.

7. **MODIFIED `apps/api/app/router.py`** — append two new lines AFTER the existing Story 6.3/6.4 invite imports:
   ```python
   from app.modules.auth.password_reset.admin_router import router as password_reset_admin_router
   from app.modules.auth.password_reset.router import router as password_reset_public_router
   ```
   And register them in `api_router.include_router(...)` block — the public router goes alongside `invite_public_router` (between lines 16-17), the admin router alongside `invite_admin_router` (between lines 17-18). Order does not matter functionally (FastAPI mounts independently); placement mirrors the invite-router precedent for grep-ability.

8. **MODIFIED `apps/api/app/core/config.py`** — APPEND ONE new Pydantic Settings field IMMEDIATELY AFTER the existing `ratelimit_share_soft_alert_threshold` block (around line 58):
   ```python
   # Story 8.5: admin-issued password-reset link TTL bounds.
   password_reset_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
   ```
   Default 3600 (1 hour) matches epics §1814 verbatim "TTL default 1h configurable via `PASSWORD_RESET_TTL_SECONDS` Pydantic Settings field". Lower bound 60 (1 min) and upper bound 86400 (24h) are the operational range — anything less than 60s is unusable in practice (operator cannot send the link out-of-band that fast), anything more than 24h is a security smell (stale-token surface widens). The Pydantic Field constraint enforces both bounds at startup-config-load — a misconfigured `.env` value raises `ValidationError` at app boot, NOT at first endpoint call.

9. **MODIFIED `apps/api/app/core/auth/ratelimit.py::register_ratelimit_key()`** at lines 106-109 — EXTEND the path match to include `/api/auth/password-reset` so both endpoints share the `register` scope's 3-attempts-per-60s budget per epics §1818 verbatim. The change is a TWO-LINE diff: rewrite the `if` predicate as:
   ```python
   def register_ratelimit_key(request: Request) -> str | None:
       if request.method == "POST" and request.url.path in {
           "/api/auth/register",
           "/api/auth/password-reset",
       }:
           return f"ip:{_client_ip(request)}"
       return None
   ```
   No new scope, no new key shape, no new threshold — the existing `ratelimit_register_window_seconds = 60` + `ratelimit_register_threshold = 3` settings cover both endpoints. The shared budget is the deliberate design per epics §1818 verbatim "reset and register share the public-write rate-limit budget by design".

10. **NEW backend test files (TWO):**
    - `apps/api/tests/test_admin_password_reset_mint.py` — 8 tests M1-M8 covering the admin mint endpoint (see AC-7 table).
    - `apps/api/tests/test_auth_password_reset_consume.py` — 10 tests C1-C10 covering the public consume endpoint (see AC-7 table).
    Both files reuse the conftest `isolated_client` fixture + duplicate the `_admin_token` + `_set_admin_cookie` + `_seed_members` helpers from `tests/test_admin_users_mutations.py:32-80` verbatim (Story 8.3 deliberate-duplication convention continues; the shared `_helpers/admin_users.py` extraction remains a Story 9.x+ refactor candidate per the pre-existing-issue threshold tracker — 3 files now duplicate these helpers, threshold "5× within a single session" stays uncrossed).

11. **MODIFIED frontend `apps/web/src/modules/admin/UsersPage.tsx`** — append ONE new `<DropdownMenuItem>` entry to the existing Story 8.4 kebab menu (placed AFTER the Story 8.4 "Force-disable 2FA (lockout recovery)" item — the 4 Story 8.3 items + 2 Story 8.4 items + 1 Story 8.5 item = 7 total per active row):
    - **"Issue password reset link"** — visible ALWAYS for non-self non-agent rows (no `totp_enabled` or `force_2fa_enrollment` gating — the operator may issue a reset link independently of 2FA state; the lost-2FA recovery flow specifically pairs Story 8.4 force-disable + Story 8.5 reset, but Story 8.5 also covers the "user just forgot their password" non-2FA case per epics §1817 + brief "What Makes This Special" §"Admin-issued password reset link"). Opens a confirmation `ConfirmDialog` (NOT destructive — issuing a reset link is reversible by simply waiting for the TTL to expire without the user consuming it). On confirm calls `useIssuePasswordResetAdminUser()` mutation — on success, the returned `{reset_url, expires_at}` opens the NEW `ResetLinkDisplayModal.tsx` (see T12) rendering the URL ONCE with a clipboard-copy button.
12. **DISABLED menu item mirrors Stories 8.3 + 8.4 foot-guns:** the new item is `aria-disabled="true"` + non-interactive via the SAME kebab-button-level `actionsDisabled = isSelf || isAgent` guard at `UsersPage.tsx:333` (Story 8.3's binding contract continues for the 7th menu item — NO new useState slot for self/agent detection needed).

13. **NEW frontend `apps/web/src/modules/admin/ResetLinkDisplayModal.tsx` (~80 LOC)** — peer of `apps/web/src/modules/admin/ChangeRoleModal.tsx` (Story 8.3 modal-as-peer-of-page convention continues). Renders `<Dialog>` with: title `"Password reset link issued for {email}"`, body text `"This link will be valid until {expires_at}. The cleartext token is shown ONLY ONCE — copy it now and deliver it out-of-band to the user (SMS, Messenger, personal mail). If you close this modal without copying the link, you must issue a fresh one."` (i18n key — see T15), a read-only `<Input>` with the `reset_url` value + a `<Button>` with copy-to-clipboard via `navigator.clipboard.writeText(reset_url)`, and a `<Button>` "Done" that closes the modal. The cleartext-token surfaces-once UX mirrors the Story 6.3 invite-token modal (which currently does NOT exist as a separate component but lives inline in the admin invites flow that is itself Story 8.6+; for Story 8.5 we ship the modal pattern that Story 8.6 can later reuse).

14. **NEW `useIssuePasswordResetAdminUser()` hook** appended to the existing `apps/web/src/modules/admin/hooks/useAdminUsers.ts` (Story 8.4's file). Follows the `useForce2faEnrollmentAdminUser()` precedent (lines 74-85 of the post-Story-8.4 file) with ONE difference: the response shape is `PasswordResetMintResponse` (NOT void) — so the mutation type is `useMutation<PasswordResetMintResponse, ApiError, string>`. The `onSuccess` callback does NOT invalidate the `["admin", "users"]` query subtree (no user-list state change on mint — the user row is identical pre/post; only the Redis-side token state changes which the panel does not surface). One new export; the queryClient.invalidateQueries call is OMITTED on purpose to avoid an unnecessary refetch of the user list.

15. **NEW frontend `apps/web/src/routes/reset-password.tsx`** — public TanStack Router route mirroring `apps/web/src/routes/register.tsx` exactly. The component reads `token` from the URL search params via `useSearch({ from: "/reset-password" })`, renders a form with ONE password input (NO email field — the reset link binds the user identity via the Redis-stored `user_id`), runs the SAME password-strength UX as `/register` (length floor 12, zxcvbn-score-by-server gate), POSTs `{token, new_password}` to `/api/auth/password-reset`. On 204: navigates to `/login` with a query param `?reset=success` (NEW i18n string on login page renders a one-time success banner — see T15). On 404 with `detail=token_invalid`: renders a full-page error mirroring `/register` token_invalid panel verbatim. On 422 weak-password: renders inline field error mirroring `/register` weak-password panel verbatim. **Critical:** the route does NOT call `useQueryClient().invalidateQueries(["auth", "me"])` on success because the consume endpoint does NOT issue cookies — the user is NOT logged in post-reset; they must subsequently `POST /api/auth/login` with the new password.

16. **NEW frontend test files:**
    - `apps/web/src/routes/reset-password.test.tsx` — 3 tests R1-R3 (golden-path submit + token_invalid full-page error + weak-password inline error).
    - `apps/web/src/modules/admin/ResetLinkDisplayModal.test.tsx` — 2 tests RM1-RM2 (renders reset_url + clipboard copy callback fires on button click).
    - Vitest tests V15-V17 (3 new tests) APPENDED to existing `apps/web/src/modules/admin/UsersPage.test.tsx` (Story 8.4's file): V15 menu item visible for non-self non-agent rows; V16 confirm-dialog dispatches `useIssuePasswordResetAdminUser` mutation; V17 mutation success opens the `ResetLinkDisplayModal` with the returned reset_url.

17. **NEW frontend Playwright spec `apps/web/tests/visual/reset-password.spec.ts`** — mirrors `apps/web/tests/visual/register.spec.ts` exactly with 3 visual snapshots (empty form / token_invalid panel / weak-password inline error) per the Init 3 baseline 4-project convention (desktop-light/dark, mobile-light/dark = 12 PNGs total at first commit). The existing `apps/web/tests/visual/admin-users.spec.ts` (Story 8.4's file) gains ONE new Test 10 (kebab shows 7 items including "Issue password reset link" for an active non-2FA-enrolled non-flagged member; verifies the menu count goes from 5/6 (Story 8.4 Tests 8-9 covered) to 7. Visual baselines for admin-users-empty/one-row/many-rows DO NOT need regeneration because Story 8.5 adds NO new column — the 9 columns from Story 8.4 stay. Only the kebab-menu-open state (which Story 8.4 Tests 8-9 covered via interaction, not via screenshot) gains the new item — Test 10 verifies via DOM assertion, NOT a new snapshot.

so that:

- **FR5-ADMIN-3 is fully realized.** PRD §1195 binds Admin-issued password-reset link as a per-user admin action with: single-use, short TTL (default 1h, configurable), Redis-fronted at `invite:reset:{token}`, out-of-band delivery by the operator, `auth.password.reset.initiated` audit on mint, `auth.password.reset.completed` audit on consume, mirrored `/reset-password?token=<token>` public route with registration-equivalent password-strength gates. Story 8.5 ships all six bullets in one commit.

- **The lost-2FA-AND-lost-recovery-codes recovery flow gains its concrete Step 2.** Per epics §1817 verbatim: Step 1 = Story 8.4's `POST /api/admin/users/{id}/force-disable-2fa` (already shipped at `acd7a85` + `af07752`); Step 2 = Story 8.5's `POST /api/admin/users/{id}/password-reset`. After Story 8.5 ships, operators can fully resolve the lost-2FA-AND-recovery-codes lockout via the panel UI (2-click flow: kebab → force-disable-2fa → kebab → issue-reset) WITHOUT DB-direct surgery on `.190`. The docs/operations.md operator-runbook section that documents the full 2-step flow is authored in Story 10.4 closing commit per epics §1817 verbatim "documented in `docs/operations.md` (operator runbook section authored in Story 10.4 closing commit)" — Story 8.5 ships the endpoints; Story 10.4 ships the operator runbook prose.

- **FR5-AUDIT-1 `actor != target` discriminator is enforced for the initiated emission; `actor == target` discriminator for the completed emission.** Both action names (`auth.password.reset.initiated`, `auth.password.reset.completed`) are ALREADY documented in `app/core/audit.py:37-38` (pre-registered in the Story 7.5 closing commit per the audit-registry forward-declaration convention used throughout Init 5). Story 8.5's audit emissions activate the names — the registry stays untouched per AC-13.

- **Token shape reuse from invite-token primitive (Decision A + B) is enforced verbatim.** `secrets.token_urlsafe(32)` (256-bit URL-safe), Redis key shape `invite:reset:{token}` per epics §1814 verbatim (the "invite:reset:" prefix sharing with invite-tokens is the architecture's deliberate namespace-unification choice), JSON payload `{user_id, generated_by, generated_at}`. The Redis SET happens with `EX=ttl_seconds` (built-in TTL, no manual sweep). The GETDEL atomic claim mirrors Story 7.3 partial-auth pattern verbatim — no consume-race window.

- **The Story 8.4 frontend disabled-state guards extend transparently to the new menu item.** Story 8.3's `actionsDisabled = isSelf || isAgent` kebab-button-level guard at `UsersPage.tsx:333` already short-circuits the kebab render for self + agent rows; Story 8.5's new menu item inherits this short-circuit via the same conditional. NO new useState slot, NO new aria-disabled wiring at the menu-item level — the 7 menu items all gate uniformly through one button-level disable. 

- **Story 8.3 + 8.4 enforcement gates stay intact.** Story 8.5 does NOT touch `is_active`, does NOT touch `totp_enabled_at`, does NOT touch `totp_secret`, does NOT touch `recovery_codes`, does NOT touch `force_2fa_enrollment`, does NOT add a new column to `users`, does NOT add an Alembic migration. The Story 8.3 `is_active` gate on `/api/auth/login` + `/api/auth/refresh` continues to fire for deactivated users — and a deactivated user CAN have a reset link issued (the admin guards do not check `is_active`; rationale: the operator may want to "reactivate + reset" as a 2-click flow, OR may want to lock-then-reset on a compromised account before reactivation). Verify regression via `pytest tests/test_auth_deactivated_user.py tests/test_admin_users_2fa_overrides.py -q` (Stories 8.3 + 8.4 must stay green).

### Story scope is strictly bounded

- **NEW files (~11):**
  - `apps/api/app/modules/auth/password_reset/__init__.py`
  - `apps/api/app/modules/auth/password_reset/service.py`
  - `apps/api/app/modules/auth/password_reset/router.py`
  - `apps/api/app/modules/auth/password_reset/admin_router.py`
  - `apps/api/app/modules/auth/password_reset/schemas.py`
  - `apps/api/tests/test_admin_password_reset_mint.py`
  - `apps/api/tests/test_auth_password_reset_consume.py`
  - `apps/web/src/modules/admin/ResetLinkDisplayModal.tsx`
  - `apps/web/src/modules/admin/ResetLinkDisplayModal.test.tsx`
  - `apps/web/src/routes/reset-password.tsx`
  - `apps/web/src/routes/reset-password.test.tsx`
  - `apps/web/tests/visual/reset-password.spec.ts`
- **MODIFIED files (~9):**
  - `apps/api/app/router.py` (append 2 router imports + 2 include_router lines).
  - `apps/api/app/core/config.py` (append `password_reset_ttl_seconds` Settings field).
  - `apps/api/app/core/auth/ratelimit.py` (extend `register_ratelimit_key` path-match set).
  - `apps/web/src/modules/admin/UsersPage.tsx` (1 new useState slot + 1 new mutation hook + 1 new handler + 1 new menu item + 1 new ConfirmDialog instance + 1 new modal instance + 1 new error code in KNOWN_ERROR_CODES if needed).
  - `apps/web/src/modules/admin/UsersPage.test.tsx` (append V15-V17).
  - `apps/web/src/modules/admin/hooks/useAdminUsers.ts` (append `useIssuePasswordResetAdminUser` mutation hook).
  - `apps/web/src/lib/api-types.ts` (append `PasswordResetMintResponse` interface + Story 8.5 section comment).
  - `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json` (~14 new keys).
  - `apps/web/tests/visual/admin-users.spec.ts` (append Test 10 — DOM-assert kebab shows 7 items; NO new screenshot, NO baseline regeneration).
  - `apps/web/src/routeTree.gen.ts` — auto-regenerated by `npm run generate:routes` after adding `reset-password.tsx` (the regeneration is a side-effect, NOT a hand-edit; commit the regenerated file alongside source).
- **STRICTLY OUT OF SCOPE** (these belong to later stories and pollute the diff if added here):
  - **Self-service mail-based password reset** — Decision L §1741-1745 verbatim defers this to a future "self-hosted mail server initiative" (vision-tier per brief §"Vision" +12 months). Story 8.5 ships ONLY the admin-issued path; the future self-service `POST /api/auth/password-reset` (with email-lookup → mail-delivery) is a separate non-Init-5 feature.
  - **DB-row audit history for password-reset tokens** — epics §1814 verbatim "NO DB-row audit history is needed at the password-reset-link tier". The audit-log emissions (`auth.password.reset.initiated` + `auth.password.reset.completed`) ARE the audit history; no parallel `password_reset_tokens` table is created. Future operator visibility into "which admin issued which reset link" comes from the audit-log query (`/api/admin/audit?action=auth.password.reset.initiated`), NOT a separate panel surface.
  - **Admin "list issued reset links" panel surface** — there is no `GET /api/admin/password-reset-tokens` endpoint and no Invites-style admin tab for reset links. Rationale: the audit-log surface answers "what links were issued?" and the Redis-only state (TTL-bounded auto-expiry) makes a list-active-tokens view operationally low-value. If a future story needs this view, it would mirror Story 6.3's `list_invites()` shape but with a Redis SCAN — DEFER until justified.
  - **Force-logout on password change** — Decision I §1622 binds force-logout to Story 8.3's PATCH/force-logout admin actions, NOT to password rotation. Story 8.5 does NOT proactively burn refresh-token families on consume. If the operator wants session-burn coupled with password-reset, they invoke Story 8.3 force-logout BEFORE issuing the reset link (the 2-click panel flow). Re-evaluating "should consume implicitly burn families?" is a Story 9.x security-audit follow-up if NFR5-SEC-3 surfaces the gap.
  - **Multi-use reset tokens** — single-use semantics is the architecture's binding contract (Decision A + B). A multi-use token would defeat the single-shot-and-rotate property and create a stale-token surface.
  - **Email-validation on consume** — the consume endpoint accepts ONLY `{token, new_password}`; the user's email is resolved from the Redis-stored `user_id` (the link IS the identity proof). Adding email-validation would be a UX-confusion vector (the user has the link from out-of-band delivery — they don't necessarily remember their email exactly as registered).
  - **Token-status enumeration distinction** — Story 8.5 returns 404 `token_invalid` uniformly for never-existed / expired / consumed states (the Redis-only state surface cannot distinguish them after GETDEL). This is the deliberate token-status-enumeration protection per Story 6.4 §invite/service.py:54-57 verbatim convention.
  - **Migration to a new admin sub-router** for the existing `apps/api/app/modules/admin/router.py` Story 8.3 + 8.4 endpoints — those stay in admin/router.py. Story 8.5's NEW endpoints go in the NEW `password_reset/` sub-module (the Story 8.4 §file-structure-requirements promotion-point decision applied here means NEW endpoints get the new module, NOT pre-existing endpoints).
  - **Cookies issued on consume** — the consume endpoint does NOT mint cookies. Post-reset, the user must `POST /api/auth/login` with the new password. Rationale: this matches the security-conservative path (no implicit auth on a public endpoint with weak identity proof — the token IS the proof for password-rotation but NOT for session-establishment).
  - **Admin Invites tab UI content** (Story 8.6 — AdminTabs stays in Story 8.2's shipped disabled-Invites state).
  - **Bulk operations** (FR5-ADMIN-4 deliberate-exclusion enforced via Stories 8.2 + 8.3 negative ACs; Story 8.5 inherits the absence).

No new Alembic migration. No new entity_type in `KNOWN_ENTITY_TYPES`. No new audit action name (the 2 emissions reuse pre-registered names from `app/core/audit.py:37-38`). No new rate-limit scope. No new middleware. No change to `apps/api/app/main.py` (middleware mounting unchanged). No change to Story 8.1 `LastActiveMiddleware`. No change to Story 8.3 PATCH or POST force-logout endpoints. No change to Story 8.4 force-enroll or force-disable endpoints. No change to Story 8.2 GET endpoint's sorting/searching/pagination logic. No change to the existing `apps/api/app/modules/invite/` module (the password-reset sub-module is a peer, NOT a fork). No change to existing rate-limit `share` / `login` / `refresh` scopes.

## Acceptance Criteria

**AC-1 — NEW `apps/api/app/modules/auth/password_reset/` sub-module ships with the five expected files + canonical structure.**

- Given the current Init 5 module layout (`apps/api/app/modules/auth/{router.py, totp/, models.py}`),
- When Story 8.5 ships,
- Then `apps/api/app/modules/auth/password_reset/` MUST exist as a Python package containing exactly five files: `__init__.py`, `service.py`, `router.py`, `admin_router.py`, `schemas.py`.
- And `__init__.py` MUST export the public surface: `PasswordResetService`, `PasswordResetConsumeRequest`, `PasswordResetMintResponse` (mirrors `apps/api/app/modules/invite/__init__.py` precedent shape).
- And the module MUST NOT contain a `models.py` — there is NO SQLModel for password-reset tokens (Redis-only state per epics §1814).
- And `cd apps/api && .venv/bin/python -c "from app.modules.auth.password_reset import PasswordResetService; print('ok')"` MUST print `ok`.
- And running `cd apps/api && .venv/bin/ruff check app/modules/auth/password_reset/` MUST return 0 lint errors.

**AC-2 — `PasswordResetService.generate()` mints a single-use Redis-backed token with correct shape.**

- Given a `PasswordResetService` instance constructed with a live Redis client,
- When `generate(user_id=<UUID>, generated_by_user_id=<UUID>, ttl_seconds=3600)` is awaited,
- Then the method MUST:
  - Mint a token via `secrets.token_urlsafe(32)` (43 characters, URL-safe base64-without-padding).
  - SET Redis key `invite:reset:<token>` to JSON `{"user_id": "<uuid-str>", "generated_by_user_id": "<uuid-str>", "generated_at": "<iso8601-utc>"}` with `ex=3600`.
  - Return the cleartext token string.
- And calling `generate()` with `ttl_seconds < 60` MUST raise `ValueError` (mirrors the `_TTL_MIN_SECONDS = 60` floor from `invite/service.py:35`).
- And calling `generate()` with `ttl_seconds > 86400` MUST raise `ValueError` (the password-reset MAX is 86400, NOT the 7776000 invite MAX — Story 8.5's TTL ceiling matches Settings `password_reset_ttl_seconds.le=86400`).
- And the token is verifiably stored in Redis with `await redis.get(f"invite:reset:{token}")` returning the JSON payload exactly as written.

**AC-3 — `PasswordResetService.claim()` is atomic single-use via Redis GETDEL.**

- Given a token previously minted via `generate()`,
- When `claim(token)` is awaited,
- Then the method MUST execute `await redis.execute_command("GETDEL", f"invite:reset:{token}")` (single Redis round-trip; mirrors `auth/totp/router.py:369` verbatim pattern).
- And on a Redis HIT (token exists): parse the JSON payload, return `uuid.UUID(payload["user_id"])`.
- And on a Redis MISS (token never existed, expired, or already claimed): return `None`.
- And two concurrent `claim(token)` calls with the same token MUST result in EXACTLY ONE returning a UUID and EXACTLY ONE returning `None` (verified by AC-7 test C9 with `asyncio.gather`).
- And after `claim(token)` returns a UUID, a subsequent `claim(token)` with the same token MUST return `None` (the GETDEL has deleted the key; second call is the consume-race-loser path).

**AC-4 — `POST /api/admin/users/{user_id}/password-reset` mints + emits audit + returns reset_url.**

- Given an admin-authenticated request with a valid `portal_access` cookie + `role == "admin"`,
- When the client calls `POST /api/admin/users/<target-id>/password-reset` (no body),
- Then the endpoint MUST:
  - Resolve `admin_id: uuid.UUID = current_admin` — non-admin authenticated returns 403; anonymous returns 401.
  - Validate the path UUID via FastAPI's native `uuid.UUID` parsing (invalid UUID → 422).
  - Look up `target = session.get(User, user_id)`. If `None`, return 404 `detail="user_not_found"`.
  - **Self-mutation guard:** `target.id == admin_id` → 400 `detail="cannot_target_self"`. Self-reset goes through DB-direct surgery per Decision L §1741.
  - **Agent-role guard:** `target.role == UserRole.agent` → 400 `detail="cannot_target_agent"`. NFR5-INT-1.
  - Call `token = await service.generate(user_id=target.id, generated_by_user_id=admin_id, ttl_seconds=settings.password_reset_ttl_seconds)`.
  - Emit `record_event(action="auth.password.reset.initiated", entity_type="user", entity_id=target.id, actor_user_id=admin_id, after={"ttl_seconds": settings.password_reset_ttl_seconds}, request_id=...)`. `actor_user_id != entity_id` is the binding invariant.
  - Compute `expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=settings.password_reset_ttl_seconds)`.
  - Return `PasswordResetMintResponse(reset_url=f"/reset-password?token={token}", expires_at=expires_at)` with HTTP 201 status code.
- And ZERO row changes occur to: `users.password_hash`, `users.totp_secret`, `users.totp_enabled_at`, `users.is_active`, `users.force_2fa_enrollment`, `recovery_codes`, RefreshToken table. The admin mint side-effects are: ONE Redis SET + ONE audit-log row + ONE HTTP response.
- And the OpenAPI surface MUST expose the endpoint with `summary="Issue a single-use password-reset link for a user (admin only)"` + a 6-8 sentence description citing the 2 guards (self / agent), the cleartext-token-surfaces-once UX, the out-of-band delivery requirement, the lost-2FA-recovery Step-2 binding (epics §1817), and the Redis-only state (no DB row audit history per epics §1814).

**AC-5 — `POST /api/auth/password-reset` consumes the token + updates password + emits audit.**

- Given a token previously minted via the admin endpoint,
- When the client calls `POST /api/auth/password-reset` with body `{"token": "<token>", "new_password": "<plain>"}` (NO auth cookies required — public endpoint),
- Then the endpoint MUST:
  - Parse the body as `PasswordResetConsumeRequest`. Unknown fields → 422 via `extra="forbid"`. Token length ≠ 43 → 422 via `Field(min_length=43, max_length=43)`.
  - **Step 1 — atomic claim:** `user_id = await service.claim(payload.token)`. If `None`:
    - Emit `record_event(action="auth.password.reset.completed", entity_type="user", entity_id=None, actor_user_id=None, after={"reason": "token_invalid"}, request_id=...)`.
    - Raise `HTTPException(404, detail="token_invalid")`.
  - **Step 2 — password validation:** `len(payload.new_password) < 12` → emit `auth.password.reset.completed` with `after={"reason": "weak_password"}` + raise 422 `detail="password must be at least 12 characters"`. `zxcvbn.zxcvbn(payload.new_password)["score"] < 3` → same audit emission + raise 422 `detail="password is too predictable; choose a stronger one"`. **Critical:** the weak-password audit emission DOES include `entity_id=user_id` (the user identity is known post-claim) — distinct from token_invalid which has `entity_id=None`.
  - **Step 3 — user lookup:** `target = session.get(User, user_id)`. If `None`: emit `auth.password.reset.completed` with `after={"reason": "user_not_found"}` + raise 404 `detail="user_not_found"`.
  - **Step 4 — password update:** `target.password_hash = hash_password(payload.new_password)`. `session.add(target); session.commit()`.
  - **Step 5 — success audit:** `record_event(action="auth.password.reset.completed", entity_type="user", entity_id=target.id, actor_user_id=target.id, after={"email": target.email}, request_id=...)`. `actor_user_id == entity_id == target.id` (the success-path invariant; the user is both actor and entity for self-reset).
  - Return HTTP 204 (no body, no cookies).
- And the response MUST NOT set `portal_access` or `portal_refresh` cookies — the consume endpoint is NOT a login endpoint; the user must subsequently POST `/api/auth/login` with the new password.
- And ZERO row changes occur to: `users.totp_secret`, `users.totp_enabled_at`, `users.is_active`, `users.force_2fa_enrollment`, `recovery_codes`, RefreshToken table. The single side-effects on success are: ONE Redis DEL (via GETDEL) + ONE `users.password_hash` UPDATE + ONE audit-log row.
- And golden-path regression: a deactivated user (`is_active = False`) CAN still consume a reset token successfully (the consume endpoint does NOT enforce `is_active` gating — the operator may "issue reset then reactivate" as a 2-step flow). The user is still BLOCKED from logging in after the reset because the Story 8.3 `is_active` gate at `/api/auth/login` continues to fire — verified by AC-7 test C8.

**AC-6 — `password_reset_ttl_seconds` Settings field with default 3600 + bounds [60, 86400] enforced at startup.**

- Given the existing Pydantic Settings class at `apps/api/app/core/config.py`,
- When Story 8.5 ships,
- Then the Settings class MUST gain `password_reset_ttl_seconds: int = Field(default=3600, ge=60, le=86400)` (inserted after the `ratelimit_share_*` block per the chronological-by-story field-order convention).
- And starting the app with `PASSWORD_RESET_TTL_SECONDS=30` in `infra/.env` MUST raise `pydantic.ValidationError` at startup-config-load (ge=60 floor).
- And starting the app with `PASSWORD_RESET_TTL_SECONDS=100000` MUST raise `pydantic.ValidationError` at startup-config-load (le=86400 ceiling).
- And starting the app with NO `PASSWORD_RESET_TTL_SECONDS` env var MUST default to 3600 (no `RuntimeError`).
- And `cd apps/api && .venv/bin/python -c "from app.core.config import get_settings; print(get_settings().password_reset_ttl_seconds)"` MUST print `3600` in dev (where no env var is set).

**AC-7 — Backend tests: 8 mint tests (M1-M8) + 10 consume tests (C1-C10) all pass in isolation and together.**

| ID | File | Test | Asserts |
|----|------|------|---------|
| M1 | test_admin_password_reset_mint.py | golden-path mint returns 201 + reset_url shape | response.status_code == 201; `/reset-password?token=` prefix; expires_at within (now+ttl-5s, now+ttl+5s) window |
| M2 | " | mint emits auth.password.reset.initiated audit | one row with actor=admin, entity_id=target, action=auth.password.reset.initiated, after.ttl_seconds=3600 |
| M3 | " | mint requires admin cookie (member 403) | response.status_code == 403; ZERO Redis key written |
| M4 | " | mint anonymous returns 401 | response.status_code == 401; ZERO Redis key |
| M5 | " | mint self-target returns 400 cannot_target_self | response.status_code == 400; detail == "cannot_target_self"; ZERO Redis key; ZERO audit row |
| M6 | " | mint agent-target returns 400 cannot_target_agent | response.status_code == 400; detail == "cannot_target_agent"; ZERO Redis key; ZERO audit row |
| M7 | " | mint unknown user_id returns 404 user_not_found | response.status_code == 404; detail == "user_not_found"; ZERO Redis key; ZERO audit row |
| M8 | " | mint two links for same user yields two independent tokens | two separate POSTs return two distinct reset_urls; both tokens valid; consuming token 1 does NOT affect token 2 |
| C1 | test_auth_password_reset_consume.py | golden-path consume returns 204 + password updated | response.status_code == 204; subsequent login with new password succeeds; one auth.password.reset.completed audit row with actor==entity==target |
| C2 | " | consume with invalid token returns 404 token_invalid | response.status_code == 404; detail == "token_invalid"; one audit row with entity_id=None, after.reason="token_invalid" |
| C3 | " | consume with consumed token returns 404 token_invalid (uniform) | first consume returns 204; second consume with same token returns 404 (NOT 410 — uniform-error per Story 6.4 convention); ONE successful audit row + ONE token_invalid audit row |
| C4 | " | consume with expired token returns 404 token_invalid | manually expire the Redis key (DEL it from the test), consume returns 404 |
| C5 | " | consume with weak password (length < 12) returns 422 + audit | response.status_code == 422; detail starts with "password must be at least 12 characters"; audit row with entity_id=user_id (resolved post-claim), after.reason="weak_password"; Redis key DELETED (token is consumed by the claim even on weak-password failure — single-use semantics) |
| C6 | " | consume with weak password (zxcvbn < 3) returns 422 + audit | response.status_code == 422; detail starts with "password is too predictable"; audit row with after.reason="weak_password"; Redis key DELETED |
| C7 | " | consume with unknown user_id (row deleted between mint and consume) returns 404 user_not_found | mint a token, DELETE the user row from DB, consume returns 404 + audit row with after.reason="user_not_found" |
| C8 | " | consume succeeds for a deactivated user (is_active=False) but login still blocked | mint + consume returns 204; user.password_hash is updated; subsequent /api/auth/login with new password returns 401 account_deactivated (Story 8.3 gate still fires) |
| C9 | " | concurrent consume on same token: exactly one 204 + one 404 | asyncio.gather two POSTs to the same token; assert exactly one 204 + one 404; password_hash was set exactly once |
| C10 | " | consume does NOT issue cookies | response.status_code == 204; assert "set-cookie" header is absent OR does not contain portal_access/portal_refresh names |

- And `cd apps/api && .venv/bin/pytest tests/test_admin_password_reset_mint.py tests/test_auth_password_reset_consume.py -v` MUST return 18/18 green.
- And `cd apps/api && .venv/bin/pytest tests/ -q` MUST return ≥740 green (current baseline ~724 + 18 new Story 8.5 tests; allow for slight count drift from regression-test additions).
- And the AUTOUSE `_clear_user_audit_and_refresh_tables` fixture pattern from Story 8.3 + 8.4 is REUSED (preserves seeded admin, wipes User + AuditLog + RefreshToken). Story 8.5 ALSO needs to clear Redis state between tests — add a fixture `_clear_password_reset_redis_keys` that `await redis.delete(*await redis.keys("invite:reset:*"))` in `setup` and `teardown` to prevent inter-test token leakage.

**AC-8 — Frontend admin menu item + ResetLinkDisplayModal wired through UsersPage.tsx.**

- Given the existing Story 8.4 kebab menu at `apps/web/src/modules/admin/UsersPage.tsx:418-487` (6 items: Change role / Deactivate / Reactivate / Force logout / Force 2FA enrollment / Force-disable 2FA),
- When Story 8.5 ships,
- Then UsersPage.tsx MUST gain ONE new `<DropdownMenuItem>` entry placed AFTER the existing Story 8.4 force-disable item — making the menu 7 items total.
- And the new item's i18n key MUST be `admin.users.actions.issue_password_reset` (label EN: "Issue password reset link" / PL: "Wystaw link do resetu hasła").
- And clicking the item MUST open a confirmation `<ConfirmDialog>` (NOT destructive — the issue-link action is reversible by waiting for TTL expiry without consume).
- And confirming the dialog MUST call `useIssuePasswordResetAdminUser().mutate(target.id)`.
- And on `onSuccess` of the mutation, the returned `{reset_url, expires_at}` payload MUST open the `<ResetLinkDisplayModal>` rendering: title with target email, body explaining the one-time UX, read-only input with the URL, copy-to-clipboard button, Done button.
- And the menu item MUST inherit Story 8.3's `actionsDisabled = isSelf || isAgent` kebab-button-level guard — verified by V15.
- And `cd apps/web && npm run typecheck` MUST be green after the changes.
- And `cd apps/web && npm run lint` MUST be green after the changes.

**AC-9 — Public `/reset-password` React route mirrors `/register` shape.**

- Given the existing `apps/web/src/routes/register.tsx` route shape (TanStack Router file-based route with `useSearch({from: "/register"})` to read `?token=...` query param + form with email + password + submit handler + full-page error panel for token_missing / token_invalid / token_consumed + inline error for weak-password / email-taken),
- When Story 8.5 ships,
- Then `apps/web/src/routes/reset-password.tsx` MUST exist with:
  - `createFileRoute("/reset-password")` declaration with `validateSearch` accepting `?token=<string>` (mirrors register.tsx:149-153).
  - Component reads `token` via `useSearch({from: "/reset-password"})`.
  - Form with ONE `<Input>` (password — autoComplete="new-password") + ONE `<Button>` submit. **NO email field** — the user identity is bound by the token.
  - Submit handler POSTs `{token, new_password}` to `/api/auth/password-reset`.
  - Full-page error panel renders for `fullPageError ∈ {"token_missing", "token_invalid"}` (NO `token_consumed` variant — per Story 8.5 uniform-error semantics, the consume endpoint returns 404 token_invalid for both never-existed AND already-consumed states).
  - Inline error renders for weak-password 422 (mirrors register.tsx:76-80 verbatim).
  - On 204 success: navigate to `/login?reset=success` (NEW search param triggers a one-time success banner on login page — see T15 i18n key).
  - `routeTree.gen.ts` regenerated (via `npm run generate:routes`) to include the new `/reset-password` route.
- And `cd apps/web && npm run typecheck` MUST be green.

**AC-10 — Frontend i18n keys added to BOTH en.json + pl.json with proper Polish diacritics.**

- Given the existing locale files at `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`,
- When Story 8.5 ships,
- Then BOTH locale files MUST gain the following keys (14 new keys per locale = 28 total):
  - `admin.users.actions.issue_password_reset` — "Issue password reset link" / "Wystaw link do resetu hasła"
  - `admin.users.confirm.issue_password_reset_title` — "Issue password reset link for {{email}}?" / "Wystawić link do resetu hasła dla {{email}}?"
  - `admin.users.confirm.issue_password_reset_description` — "A single-use reset link will be generated. The link must be delivered out-of-band to the user (SMS, Messenger, personal mail). The cleartext token is shown ONLY ONCE." / "Zostanie wygenerowany jednorazowy link do resetu. Link należy dostarczyć użytkownikowi poza systemem (SMS, Messenger, mail prywatny). Token w postaci jawnej zostanie pokazany TYLKO RAZ."
  - `admin.users.reset_link.modal_title` — "Password reset link issued for {{email}}" / "Wystawiono link do resetu hasła dla {{email}}"
  - `admin.users.reset_link.modal_body` — "This link will be valid until {{expires_at}}. Copy it now and deliver it out-of-band. If you close this modal without copying, you must issue a fresh one." / "Link będzie ważny do {{expires_at}}. Skopiuj go teraz i dostarcz poza systemem. Jeśli zamkniesz to okno bez kopiowania, musisz wystawić nowy link."
  - `admin.users.reset_link.copy_button` — "Copy link" / "Kopiuj link"
  - `admin.users.reset_link.copied_label` — "Copied" / "Skopiowano"
  - `admin.users.reset_link.done_button` — "Done" / "Gotowe"
  - `auth.reset_password.title` — "Set a new password" / "Ustaw nowe hasło"
  - `auth.reset_password.setting_password` — "Setting password…" / "Ustawianie hasła…"
  - `auth.reset_password.error.token_invalid` — "This reset link is invalid, has expired, or has already been used. Ask the administrator for a fresh link." / "Ten link do resetu jest nieprawidłowy, wygasł lub został już wykorzystany. Poproś administratora o nowy link."
  - `auth.reset_password.error.token_missing` — "This page requires a reset link. Ask the administrator for one." / "Ta strona wymaga linku do resetu. Poproś administratora o link."
  - `auth.reset_password.error.unexpected` — "Could not reset your password. Try again in a moment." / "Nie udało się zresetować hasła. Spróbuj ponownie za chwilę."
  - `auth.login.reset_success_banner` — "Your password has been reset. Sign in with your new password." / "Twoje hasło zostało zresetowane. Zaloguj się nowym hasłem."
- And `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` MUST grow by ≥10 from baseline (Story 8.4 baseline of ~198 lines containing diacritics — Story 8.5 adds ~10 new diacritic-bearing values).
- And `jq 'keys | length' apps/web/src/locales/en.json apps/web/src/locales/pl.json` MUST return the same integer (key-set parity holds).
- And NO existing i18n key may be removed or renamed.

**AC-11 — Vitest tests V15-V17 (UsersPage) + R1-R3 (reset-password route) + RM1-RM2 (ResetLinkDisplayModal) all pass.**

| ID | File | Test | Asserts |
|----|------|------|---------|
| V15 | UsersPage.test.tsx | "Issue password reset link" menu item visible for non-self non-agent rows | renders kebab → opens menu → assert getByText("Issue password reset link") visible |
| V16 | " | ConfirmDialog dispatches useIssuePasswordResetAdminUser on confirm | mock the hook returns {mutate: vi.fn(), isPending: false}; open menu → click item → click Confirm → assert mutate called with target.id |
| V17 | " | mutation onSuccess opens ResetLinkDisplayModal with returned reset_url | mock useMutation to invoke onSuccess({reset_url: "/reset-password?token=ABC", expires_at: "2026-05-21T..."}); assert ResetLinkDisplayModal renders with the URL |
| R1 | reset-password.test.tsx | golden-path submit POSTs to /api/auth/password-reset and navigates to /login?reset=success | render with ?token=ABC, fill password, click submit, assert fetch called with correct body, assert navigate called with {to:"/login", search:{reset:"success"}} |
| R2 | " | token_invalid 404 renders full-page error panel | render with ?token=ABC, mock fetch returns 404 token_invalid, assert getByText matching i18n auth.reset_password.error.token_invalid |
| R3 | " | weak-password 422 renders inline field error | render, mock fetch returns 422 with detail "password must be at least 12 characters", assert that detail string appears under the password input |
| RM1 | ResetLinkDisplayModal.test.tsx | renders reset_url in readonly input | render with reset_url prop, assert getByDisplayValue(reset_url) is present + has readOnly attribute |
| RM2 | " | copy button invokes navigator.clipboard.writeText | mock navigator.clipboard.writeText, click copy button, assert writeText called with reset_url, assert "Copied" label appears |

- And `cd apps/web && npm run vitest -- UsersPage ResetLinkDisplayModal reset-password` MUST return 8/8 green (3 V + 3 R + 2 RM).
- And the existing Story 8.3 + 8.4 V1-V14 tests MUST stay green (no regression).
- And `cd apps/web && npm run test` (full vitest suite) MUST return ≥368 green (post-Story-8.4 baseline ~360 + 8 new Story 8.5 tests).

**AC-12 — Playwright `reset-password.spec.ts` + admin-users.spec.ts Test 10 ship.**

- Given the existing Story 8.4 Playwright matrix at `apps/web/tests/visual/`,
- When Story 8.5 ships,
- Then `apps/web/tests/visual/reset-password.spec.ts` MUST exist with 3 named tests + 3 visual baseline snapshots × 4 projects (desktop-light/desktop-dark/mobile-light/mobile-dark = 12 PNGs total):
  - Test 1 — empty-form snapshot (route loaded with ?token=ABC, password field empty).
  - Test 2 — token_invalid-error-panel snapshot (route loaded with ?token=ABC, mock API returns 404).
  - Test 3 — weak-password-inline-error snapshot (form submitted with weak password, 422 returned, inline error visible).
- And `apps/web/tests/visual/admin-users.spec.ts` MUST gain ONE new Test 10 (kebab-menu shows 7 items including "Issue password reset link" for an active non-2FA-enrolled non-flagged member — DOM-assert only, NO new screenshot).
- And `cd apps/web && npm run test:visual -- --update-snapshots reset-password` runs ONCE at dev time to generate the 12 NEW baseline PNGs. Commit them alongside source.
- And `cd apps/web && npm run test:visual -- reset-password admin-users` MUST return all green on regression mode (12 new + 9 existing admin-users tests; total 21 tests for the union, ~33 with the 4-project matrix).
- And the existing Story 8.4 admin-users baselines (3 states × 4 projects = 12 PNGs) MUST NOT be regenerated — Story 8.5 adds NO new column, so the empty/one-row/many-rows screenshots remain pixel-identical to the post-Story-8.4 commit.

**AC-13 — Audit-registry zero-touch.**

- Given the existing audit registry at `apps/api/app/core/audit.py:37-38`,
- When Story 8.5 ships,
- Then `KNOWN_ENTITY_TYPES` MUST remain UNCHANGED (the existing `user` entity_type is reused for both new emissions).
- And the audit-action-name registry docblock at lines 28-38 MUST remain UNCHANGED — the `auth.password.reset.initiated` + `auth.password.reset.completed` action names are ALREADY documented (pre-registered in the Story 7.5 closing commit per the audit-registry forward-declaration convention).
- And `git diff apps/api/app/core/audit.py` after Story 8.5 ships MUST be empty.
- And NO new `record_event` call site introduces a previously-undocumented action name (verified by grepping all `action="..."` strings in the new files against the registry docblock).

**AC-14 — Pre-merge grep invariants (22 checks).**

The following grep + test checks MUST pass before the dev commit lands:

1. `grep -l "PasswordResetService" apps/api/app/modules/auth/password_reset/*.py` returns service.py + admin_router.py + router.py + __init__.py.
2. `grep -c "GETDEL" apps/api/app/modules/auth/password_reset/service.py` returns ≥1.
3. `grep -c "auth.password.reset.initiated" apps/api/app/modules/auth/password_reset/admin_router.py` returns exactly 1.
4. `grep -c "auth.password.reset.completed" apps/api/app/modules/auth/password_reset/router.py` returns ≥4 (one success-path + at least three failure-path emissions: token_invalid, weak_password, user_not_found).
5. `grep -c "cannot_target_self\|cannot_target_agent\|user_not_found" apps/api/app/modules/auth/password_reset/admin_router.py` returns ≥3.
6. `grep -c "invite:reset:" apps/api/app/modules/auth/password_reset/service.py` returns ≥2 (SET + GETDEL key shape).
7. `grep -c "password_reset_ttl_seconds" apps/api/app/core/config.py` returns exactly 1 (the field declaration).
8. `grep -c "password-reset" apps/api/app/core/auth/ratelimit.py` returns ≥1 (the register_ratelimit_key extension).
9. `grep -c "include_router.*password_reset" apps/api/app/router.py` returns exactly 2 (admin + public).
10. `cd apps/api && .venv/bin/python -c "from app.core.config import get_settings; s = get_settings(); assert 60 <= s.password_reset_ttl_seconds <= 86400"` MUST exit 0.
11. `cd apps/api && .venv/bin/pytest tests/test_admin_password_reset_mint.py tests/test_auth_password_reset_consume.py -v` returns 18/18 green.
12. `cd apps/api && .venv/bin/pytest tests/test_auth_deactivated_user.py tests/test_admin_users_mutations.py tests/test_admin_users_2fa_overrides.py tests/test_admin_users_list.py -q` returns all green (Stories 8.1/8.2/8.3/8.4 regression guard).
13. `cd apps/api && .venv/bin/pytest tests/test_2fa_enrollment.py tests/test_2fa_disable.py tests/test_2fa_verify.py -q` returns all green (Stories 7.2/7.3/7.5 regression guard — Story 8.5 does not touch TOTP flow).
14. `cd apps/api && .venv/bin/pytest tests/test_register.py -q` returns all green (Story 6.4 regression guard — the shared zxcvbn/password-policy constants must still work via the cross-module import).
15. `cd apps/api && .venv/bin/ruff check app/modules/auth/password_reset/` returns 0 errors.
16. `cd apps/api && .venv/bin/mypy app/modules/auth/password_reset/` returns 0 errors.
17. `grep -c "useIssuePasswordResetAdminUser" apps/web/src/modules/admin/hooks/useAdminUsers.ts` returns exactly 1.
18. `grep -c "PasswordResetMintResponse" apps/web/src/lib/api-types.ts` returns ≥1.
19. `grep -c "ResetLinkDisplayModal" apps/web/src/modules/admin/UsersPage.tsx` returns ≥1.
20. `cd apps/web && npm run typecheck && npm run lint` returns green.
21. `cd apps/web && npm run vitest -- UsersPage ResetLinkDisplayModal reset-password` returns 8/8 green.
22. `jq 'keys | length' apps/web/src/locales/en.json apps/web/src/locales/pl.json` returns two equal integers; `jq -r 'keys[]' apps/web/src/locales/en.json | sort > /tmp/en_keys.txt && jq -r 'keys[]' apps/web/src/locales/pl.json | sort > /tmp/pl_keys.txt && diff /tmp/en_keys.txt /tmp/pl_keys.txt` returns empty (key-set parity).

## Tasks / Subtasks

- [ ] **T1 — Author `apps/api/app/modules/auth/password_reset/service.py`** (AC-1, AC-2, AC-3)
  - [ ] T1.1 Read `apps/api/app/modules/invite/service.py:1-260` for the service-class convention (constructor, async methods, internal `_KEY_PREFIX`, TTL bounds, JSON payload shape).
  - [ ] T1.2 Implement `PasswordResetService` class with `__init__(self, *, redis: Redis)`, `_KEY_PREFIX = "invite:reset:"`, `_TTL_MIN_SECONDS = 60`, `_TTL_MAX_SECONDS = 86400`.
  - [ ] T1.3 Implement `async generate(*, user_id, generated_by_user_id, ttl_seconds) -> str` — token via `secrets.token_urlsafe(32)`, JSON payload `{user_id, generated_by_user_id, generated_at}`, Redis SET with EX, return token.
  - [ ] T1.4 Implement `async claim(token) -> uuid.UUID | None` — atomic `redis.execute_command("GETDEL", key)` (mirrors auth/totp/router.py:369 verbatim), parse JSON on hit, return None on miss.
  - [ ] T1.5 Verify isolated: `cd apps/api && .venv/bin/python -c "from app.modules.auth.password_reset.service import PasswordResetService; print('ok')"` returns ok.

- [ ] **T2 — Author `apps/api/app/modules/auth/password_reset/schemas.py`** (AC-5)
  - [ ] T2.1 Implement `PasswordResetConsumeRequest` (extra=forbid, token min/max=43, new_password min_length=1).
  - [ ] T2.2 Implement `PasswordResetMintResponse` (frozen=True, reset_url: str, expires_at: datetime).

- [ ] **T3 — Author `apps/api/app/modules/auth/password_reset/admin_router.py`** (AC-4)
  - [ ] T3.1 Read `apps/api/app/modules/admin/router.py:444-507` (Story 8.4's force-disable-2fa endpoint) for the admin-side endpoint convention (current_admin dependency, self/agent guards, record_event emission).
  - [ ] T3.2 Implement `POST /api/admin/users/{user_id}/password-reset` with the 3 guards (self / agent / user_not_found) + service.generate() + audit emission + PasswordResetMintResponse return.
  - [ ] T3.3 OpenAPI docstring with summary + 6-8 sentence description citing guards + cleartext-once UX + epics §1817 binding.
  - [ ] T3.4 Verify route registration: `cd apps/api && .venv/bin/python -c "from app.modules.auth.password_reset.admin_router import router; print([(r.path, r.methods) for r in router.routes])"` lists the path.

- [ ] **T4 — Author `apps/api/app/modules/auth/password_reset/router.py`** (AC-5)
  - [ ] T4.1 Read `apps/api/app/modules/invite/router.py:1-100` for the public-side endpoint convention (audit emission helper, zxcvbn import, password-policy constants).
  - [ ] T4.2 Implement `POST /api/auth/password-reset` (no auth dependency) with 4-step sequence: claim → password validation → user lookup → password update + audit emissions per failure mode.
  - [ ] T4.3 Reuse `_MIN_PASSWORD_LEN`, `_MIN_ZXCVBN_SCORE`, `_LEN_MSG`, `_SCORE_MSG` via cross-module import from `app.modules.invite.router`. If Codex objects to private-name import, promote them to a 4-line `apps/api/app/core/auth/password_policy.py` public module — DEFER unless raised.
  - [ ] T4.4 Implement audit emissions for ALL paths: token_invalid (404), weak_password (422), user_not_found (404), success (204).
  - [ ] T4.5 Verify route registration similar to T3.4.

- [ ] **T5 — Author `apps/api/app/modules/auth/password_reset/__init__.py`** (AC-1)
  - [ ] T5.1 Export `PasswordResetService`, `PasswordResetConsumeRequest`, `PasswordResetMintResponse` via `__all__`.

- [ ] **T6 — Wire routers into `apps/api/app/router.py`** (AC-1)
  - [ ] T6.1 Append two imports after invite imports (lines 6-7).
  - [ ] T6.2 Append two `api_router.include_router(...)` calls alongside invite-router includes.
  - [ ] T6.3 Verify both endpoints in OpenAPI: `cd apps/api && .venv/bin/python -c "from app.main import create_app; app = create_app(); paths = [r.path for r in app.routes]; assert '/api/admin/users/{user_id}/password-reset' in paths; assert '/api/auth/password-reset' in paths"` exits 0.

- [ ] **T7 — Add `password_reset_ttl_seconds` Settings field** (AC-6)
  - [ ] T7.1 Read `apps/api/app/core/config.py:40-60` for the existing Pydantic Field convention.
  - [ ] T7.2 Append `password_reset_ttl_seconds: int = Field(default=3600, ge=60, le=86400)` after the `ratelimit_share_soft_alert_threshold` block.
  - [ ] T7.3 Verify default + bounds: see AC-6 verification commands.

- [ ] **T8 — Extend `register_ratelimit_key()` to also match `/api/auth/password-reset`** (AC-11)
  - [ ] T8.1 Read `apps/api/app/core/auth/ratelimit.py:106-109` for the current single-path predicate.
  - [ ] T8.2 Rewrite the `if` predicate to use a set-membership check including both paths.
  - [ ] T8.3 Verify: hand-craft a `POST /api/auth/password-reset` request, assert it returns the same `ip:{ip}` key as `/api/auth/register`.

- [ ] **T9 — Write backend tests at `tests/test_admin_password_reset_mint.py`** (AC-7 M1-M8)
  - [ ] T9.1 Duplicate `_admin_token` + `_set_admin_cookie` + `_seed_members` helpers from `tests/test_admin_users_mutations.py:32-80`.
  - [ ] T9.2 Implement the `_clear_user_audit_and_redis_keys` autouse fixture (preserves seeded admin, wipes User + AuditLog + Redis keys matching `invite:reset:*`).
  - [ ] T9.3 Implement M1-M8 per the AC-7 table.
  - [ ] T9.4 Verify `cd apps/api && .venv/bin/pytest tests/test_admin_password_reset_mint.py -v` returns 8/8 green.

- [ ] **T10 — Write backend tests at `tests/test_auth_password_reset_consume.py`** (AC-7 C1-C10)
  - [ ] T10.1 Mirror T9.1-T9.2 helpers + fixture.
  - [ ] T10.2 Helper `_mint_reset_token(client, target_id) -> str` — POSTs to admin endpoint, returns the token from reset_url parsing.
  - [ ] T10.3 Implement C1-C10 per the AC-7 table; pay special attention to C9 (asyncio.gather concurrency test — mirrors `tests/test_2fa_verify.py` concurrent claim pattern if it exists).
  - [ ] T10.4 Verify `cd apps/api && .venv/bin/pytest tests/test_auth_password_reset_consume.py -v` returns 10/10 green.

- [ ] **T11 — Append `useIssuePasswordResetAdminUser()` to `apps/web/src/modules/admin/hooks/useAdminUsers.ts`** (AC-8)
  - [ ] T11.1 Read the existing Story 8.4 hooks at lines 74-98 for the pattern.
  - [ ] T11.2 Append `useIssuePasswordResetAdminUser()` with `useMutation<PasswordResetMintResponse, ApiError, string>`. OMIT the queryClient.invalidateQueries call (no list refetch needed).
  - [ ] T11.3 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T12 — Author `apps/web/src/modules/admin/ResetLinkDisplayModal.tsx`** (AC-8)
  - [ ] T12.1 Read `apps/web/src/modules/admin/ChangeRoleModal.tsx:1-80` for the modal-as-peer-of-page pattern.
  - [ ] T12.2 Implement the modal with Dialog + read-only Input + copy-to-clipboard Button + Done Button + i18n keys per AC-10.
  - [ ] T12.3 Verify `cd apps/web && npm run typecheck && npm run lint` is green.

- [ ] **T13 — Modify `apps/web/src/modules/admin/UsersPage.tsx`** (AC-8)
  - [ ] T13.1 Read the existing Story 8.4 patterns at lines 94 (hook calls) + 101 (useState slots) + 463-486 (kebab menu items) + 573-602 (ConfirmDialog instances).
  - [ ] T13.2 Add ONE `useState<{reset_url: string; expires_at: string; email: string} | null>` slot for the displayed reset link.
  - [ ] T13.3 Add ONE `useIssuePasswordResetAdminUser()` hook call.
  - [ ] T13.4 Add ONE `handleIssuePasswordResetConfirm()` handler that calls `mutation.mutate(target.id, {onSuccess: ({reset_url, expires_at}) => setDisplayedResetLink({reset_url, expires_at, email: target.email})})`.
  - [ ] T13.5 Add ONE new `<DropdownMenuItem>` "Issue password reset link" placed AFTER the existing Story 8.4 force-disable item.
  - [ ] T13.6 Add ONE new `<ConfirmDialog>` instance for the issue-confirm flow.
  - [ ] T13.7 Add `{displayedResetLink && <ResetLinkDisplayModal ... onClose={() => setDisplayedResetLink(null)} />}` render below the existing modals.
  - [ ] T13.8 Verify `cd apps/web && npm run typecheck && npm run lint` is green.

- [ ] **T14 — Append `PasswordResetMintResponse` to `apps/web/src/lib/api-types.ts`** (AC-8)
  - [ ] T14.1 Read lines 220-227 for the Story 8.4 section comment marker.
  - [ ] T14.2 Append a NEW `// --- Password reset (Story 8.5) ---` section after the Story 8.4 block.
  - [ ] T14.3 Add `export interface PasswordResetMintResponse { reset_url: string; expires_at: string; }`.

- [ ] **T15 — Append 14 i18n keys to en.json + pl.json** (AC-10)
  - [ ] T15.1 Insert the 14 new keys (8 admin.users.* + 5 auth.reset_password.* + 1 auth.login.reset_success_banner) in BOTH locale files. Place them AFTER the Story 8.4 keys.
  - [ ] T15.2 Verify Polish diacritics: `grep -P "[ąęćłóśźżĄĘĆŁÓŚŹŻ]" apps/web/src/locales/pl.json | wc -l` grew by ≥10.
  - [ ] T15.3 Verify key-set parity per AC-14 #22.

- [ ] **T16 — Author `apps/web/src/routes/reset-password.tsx`** (AC-9)
  - [ ] T16.1 Read `apps/web/src/routes/register.tsx:1-153` for the TanStack Router file-based-route + form + error-handling pattern.
  - [ ] T16.2 Implement the route mirroring register.tsx exactly EXCEPT: NO email field, NO `?reset=success` retry logic, ONE password input only.
  - [ ] T16.3 On 204 success: `navigate({to: "/login", search: {reset: "success"}})`.
  - [ ] T16.4 On 404 token_invalid: render full-page error panel.
  - [ ] T16.5 On 422 weak-password: render inline error.
  - [ ] T16.6 Run `cd apps/web && npm run generate:routes` to regenerate `routeTree.gen.ts`. Commit the regenerated file alongside source.
  - [ ] T16.7 Verify `cd apps/web && npm run typecheck` is green.

- [ ] **T17 — Optional one-time success banner on `/login` when `?reset=success`** (AC-9, AC-10)
  - [ ] T17.1 Read the existing login route + login.tsx component for the search-param-handling convention.
  - [ ] T17.2 Add a `validateSearch` accepting `{reset?: "success"}` to the login route OR extend the existing search schema.
  - [ ] T17.3 In the login component, if `search.reset === "success"`, render a `<p className="text-sm text-success">{t("auth.login.reset_success_banner")}</p>` above the form.
  - [ ] T17.4 If the existing login route does NOT have a `validateSearch` accepting arbitrary search params, this task is a MINIMAL 5-line addition (read-only conditional render). If it would balloon, DEFER this banner to a follow-up — the password-reset flow still works without it (the user simply lands on /login and signs in).

- [ ] **T18 — Append vitest tests V15-V17 to `UsersPage.test.tsx`** (AC-11)
  - [ ] T18.1 Add `vi.mock` for the new hook.
  - [ ] T18.2 Implement V15-V17 per AC-11 table.
  - [ ] T18.3 Verify `cd apps/web && npm run vitest -- UsersPage` returns 17/17 green (Story 8.4 baseline 14 + 3 new).

- [ ] **T19 — Author `apps/web/src/routes/reset-password.test.tsx`** (AC-11)
  - [ ] T19.1 Mirror `apps/web/src/routes/register.test.tsx` shape if it exists; otherwise mirror UsersPage.test.tsx render pattern.
  - [ ] T19.2 Implement R1-R3 per AC-11 table.

- [ ] **T20 — Author `apps/web/src/modules/admin/ResetLinkDisplayModal.test.tsx`** (AC-11)
  - [ ] T20.1 Mirror `apps/web/src/modules/admin/ChangeRoleModal.test.tsx` shape.
  - [ ] T20.2 Implement RM1-RM2 per AC-11 table (mock `navigator.clipboard.writeText`).

- [ ] **T21 — Author Playwright spec `apps/web/tests/visual/reset-password.spec.ts`** (AC-12)
  - [ ] T21.1 Mirror `apps/web/tests/visual/register.spec.ts` shape (3 tests, 4 projects, 12 PNGs).
  - [ ] T21.2 Run `cd apps/web && npm run test:visual -- --update-snapshots reset-password` ONCE to generate the 12 baselines. Commit the PNGs alongside source.

- [ ] **T22 — Append Test 10 to `admin-users.spec.ts`** (AC-12)
  - [ ] T22.1 Add Test 10: kebab-menu opens, asserts 7 menu items including "Issue password reset link" — DOM assertion only.
  - [ ] T22.2 Verify `cd apps/web && npm run test:visual -- admin-users` returns all green (no new baselines for admin-users).

- [ ] **T23 — Run AC-14 pre-flight grep checklist** (AC-14)
  - [ ] T23.1 Execute all 22 checks; capture grep + test outputs.
  - [ ] T23.2 If any check fails, fix the underlying gap before committing.

- [ ] **T24 — Dev commit + sprint-status flip** (close-out)
  - [ ] T24.1 Single squashed `feat(api,web,tests): admin-issued password-reset link (Story 8.5)` commit covering ALL new + modified files. Commit body cites Decision A + B + epics §1806-1818 + the lost-2FA-recovery Step 2 binding as top-line bullets.
  - [ ] T24.2 Commit message ends with the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
  - [ ] T24.3 Update sprint-status: flip `8-5-admin-issued-password-reset-link` from `ready-for-dev` → `review` (NOT `done` — Codex review is the canonical post-dev gate per Epic 7 retro §3).
  - [ ] T24.4 Run `infra/scripts/deploy.sh` per `feedback_auto_deploy_dev` after merge to main.

## Dev Notes

### Architectural anchors

- **Decision A §1417-1423** — invite-token dual-backed storage rationale. Story 8.5 deliberately DOES NOT mirror the dual-backed pattern (no DB-row audit history per epics §1814); only the Redis-side primitive is reused.
- **Decision B §1425-1456** — invite-token shape (32-byte entropy, Redis key, JSON payload). Story 8.5 reuses the token primitive verbatim: `secrets.token_urlsafe(32)`, Redis key `invite:reset:{token}` (shared `invite:` namespace), JSON payload `{user_id, generated_by_user_id, generated_at}`.
- **Decision G §1559-1586** — rate-limit middleware. Story 8.5 extends the existing `register` scope path-match (NO new scope, NO new threshold).
- **Decision L §1741-1745** — self-service mail-based password reset is deferred. Story 8.5 ships the admin-issued path; self-service via mail is a future non-Init-5 initiative.
- **Epics §1806-1818** — Story 8.5 acceptance check shape verbatim. Includes the two endpoints + the lost-2FA recovery Step-2 binding + the Story 6.6 rate-limit reuse.
- **Epics §1817** — lost-2FA-AND-lost-recovery-codes recovery flow Step 2; Step 1 is Story 8.4's force-disable-2FA endpoint.
- **PRD §1195 FR5-ADMIN-3** — admin-issued password-reset link contract: single-use, short TTL, Redis-fronted, out-of-band delivery, two audit events.
- **PRD §1200 FR5-AUDIT-1** — the 2 Story 8.5 audit-action emissions (already pre-registered in `app/core/audit.py:37-38`).
- **Story 6.4 spec** at `_bmad-output/implementation-artifacts/6-4-public-register-endpoint-and-ui.md` — the public invite-token register endpoint Story 8.5's consume endpoint mirrors (password-strength gates, audit-emission helper).
- **Story 7.3 spec** at `_bmad-output/implementation-artifacts/7-3-login-partial-auth-totp-verify.md` — the atomic Redis GETDEL claim pattern Story 8.5's consume endpoint reuses.
- **Story 8.4 spec** at `_bmad-output/implementation-artifacts/8-4-admin-2fa-overrides-force-enrollment-disable.md` — the immediate predecessor; §file-structure-requirements explicitly named Story 8.5 as the sub-router promotion point.

### Critical files to read before touching

- `apps/api/app/modules/invite/service.py:1-260` — the dual-backed invite-token service convention; Story 8.5's PasswordResetService is the Redis-only sibling (simpler — no DB I/O, no audit history).
- `apps/api/app/modules/invite/router.py:1-100` — the public-side consumption endpoint convention (audit emission helper, zxcvbn import, password-policy constants).
- `apps/api/app/modules/admin/router.py:444-507` — Story 8.4's force-disable-2fa admin endpoint as the structural template for Story 8.5's admin mint.
- `apps/api/app/modules/auth/totp/router.py:355-372` — the atomic Redis GETDEL claim pattern Story 8.5's `claim()` method mirrors verbatim.
- `apps/api/app/modules/auth/router.py:111-129` — the partial-auth + Redis SET pattern for token-stash (Story 7.3); Story 8.5 reset-token generation follows the same SET-with-EX pattern.
- `apps/api/app/core/audit.py:28-56` — the audit registry; Story 8.5 action names are ALREADY pre-registered (lines 37-38).
- `apps/api/app/core/auth/password.py` — `hash_password()` helper Story 8.5 reuses verbatim for the consume-side password update.
- `apps/api/app/core/auth/ratelimit.py:106-109` — the `register_ratelimit_key()` path-match Story 8.5 extends.
- `apps/api/app/core/config.py:48-58` — the existing Pydantic Settings field convention.
- `apps/api/tests/test_admin_users_mutations.py:32-80` — Story 8.3's test-helpers Story 8.5 duplicates inline.
- `apps/api/tests/test_admin_users_2fa_overrides.py:1-50` — Story 8.4's autouse fixture pattern Story 8.5 extends with Redis-keys-cleanup.
- `apps/web/src/modules/admin/UsersPage.tsx:1-602` — Story 8.4's page Story 8.5 modifies (1 menu item + 1 useState + 1 hook + 1 handler + 1 ConfirmDialog + 1 modal render).
- `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-98` — Story 8.4's hooks file Story 8.5 extends.
- `apps/web/src/modules/admin/ChangeRoleModal.tsx` — the modal-as-peer-of-page precedent Story 8.5's ResetLinkDisplayModal mirrors.
- `apps/web/src/routes/register.tsx:1-153` — the public TanStack Router file-based-route Story 8.5's `/reset-password` mirrors.
- `apps/web/src/lib/api-types.ts:220-227` — the Story 8.4 section-comment marker Story 8.5 appends after.
- `apps/web/tests/visual/register.spec.ts` — the Playwright spec shape Story 8.5's reset-password.spec.ts mirrors.

### Library/framework versions to respect

- **FastAPI 0.115+** — `@router.post("/users/{user_id}/password-reset", status_code=201, response_model=PasswordResetMintResponse)` is the canonical admin-mint POST declaration. `@router.post("/password-reset", status_code=204)` for the public consume.
- **Pydantic 2.9** — `model_config = ConfigDict(extra="forbid")` on PasswordResetConsumeRequest. `Field(min_length=43, max_length=43)` for token shape. `Field(default=3600, ge=60, le=86400)` for the Settings field.
- **SQLAlchemy 2.x / SQLModel 0.0.22** — `session.get(User, user_id)` returns `User | None`. `session.add(target); session.commit()` for the password update.
- **redis.asyncio (redis-py 5.x)** — `await redis.set(key, value, ex=ttl)` for SET-with-EX. `await redis.execute_command("GETDEL", key)` for atomic claim (GETDEL is Redis 6.2+; the project's Redis container is pinned at ≥6.2 per Init 0 infra — verify via `docker compose config | grep -A2 redis` if uncertain). Returns `bytes | None`.
- **zxcvbn 4.4+** — `zxcvbn.zxcvbn(password)["score"]` returns 0-4. Same import + same threshold (`< 3` → weak) as Story 6.4 register endpoint.
- **bcrypt via app.core.auth.password.hash_password** — cost 12 per project convention (matches user-row password storage).
- **TanStack Query 5.x** — `useMutation<TData, TError, TVariables>` v5 API; the Story 8.4 `useForce2faEnrollmentAdminUser` is the precedent. Story 8.5's hook has `TData = PasswordResetMintResponse` instead of `void`.
- **TanStack Router 1.x** — `createFileRoute("/reset-password")` + `validateSearch` mirror the register.tsx pattern. `useSearch({from: "/reset-password"})` for typed search-param reading. `useNavigate()` for post-success redirect.
- **Radix Dialog (via @/ui/dialog)** — the existing wrapper for `ResetLinkDisplayModal`; `<Dialog>` + `<DialogContent>` + `<DialogTitle>` + `<DialogDescription>` shape per ChangeRoleModal precedent.
- **react-i18next v23+** — `t("admin.users.reset_link.modal_title", {email})` interpolates `{{email}}`. Polish strings carry diacritics per global directive.

### File structure requirements

- **NEW endpoints live in NEW sub-module `apps/api/app/modules/auth/password_reset/`** — NOT appended to `apps/api/app/modules/admin/router.py` (which is at ~508 LOC after Story 8.4 and would tip over 550 LOC if Story 8.5 endpoints were co-located). Story 8.4's §file-structure-requirements explicitly named Story 8.5 as the sub-router promotion point per the "obvious-when-you-see-it" architectural-deferral pattern. The promotion sets a precedent: NEW concerns get NEW modules; pre-existing concerns stay in admin/router.py.
- **Module follows the `auth/totp/` precedent** (NOT the `invite/` precedent) because there is no SQLModel for password-reset tokens — Redis-only state per epics §1814. Files: `__init__.py`, `service.py`, `router.py`, `admin_router.py`, `schemas.py`. NO `models.py`. NO Alembic migration.
- **NEW frontend page lives at `apps/web/src/routes/reset-password.tsx`** following the TanStack Router file-based-route convention (peer of `register.tsx`).
- **NEW frontend modal at `apps/web/src/modules/admin/ResetLinkDisplayModal.tsx`** — peer of `ChangeRoleModal.tsx` (modal-as-peer-of-page convention).
- **NEW backend test files** at `tests/test_admin_password_reset_mint.py` + `tests/test_auth_password_reset_consume.py` — naming follows the `test_<router-namespace>.py` convention (mirrors `test_admin_users_*.py` family).

### Testing requirements

- **AC-7 tests M1-M8 + C1-C10 MUST pass in isolation AND together.** Run `pytest tests/test_admin_password_reset_mint.py tests/test_auth_password_reset_consume.py -v` (isolation) and `pytest tests/ -k "password_reset" -v` (together).
- **AC-7 C9 concurrency test is critical** — it's the binding verification of the atomic-single-use GETDEL semantics. If C9 fails, the GETDEL primitive is being used incorrectly (most likely a non-atomic SET+GET+DEL sequence snuck in).
- **AC-11 vitest V15-V17 + R1-R3 + RM1-RM2 MUST pass in isolation AND together with V1-V14.** Total UsersPage vitest count is 17.
- **AC-12 Playwright reset-password 3 tests × 4 projects = 12 PNGs MUST all be committed in the dev commit.** First-time regeneration via `--update-snapshots` ONCE at dev time; subsequent CI runs compare against the baselines.
- **Stories 6.4 + 7.2 + 7.3 + 7.5 + 8.1 + 8.2 + 8.3 + 8.4 regression guards MUST stay green:**
  - `pytest tests/test_register.py -v` (Story 6.4 — the shared password-policy constants must still work).
  - `pytest tests/test_2fa_enrollment.py tests/test_2fa_verify.py tests/test_2fa_disable.py -v` (Stories 7.2/7.3/7.5 — Story 8.5 does not touch TOTP).
  - `pytest tests/test_admin_users_list.py tests/test_admin_users_mutations.py tests/test_admin_users_2fa_overrides.py tests/test_auth_deactivated_user.py -v` (Stories 8.2/8.3/8.4).
- **`infra/scripts/check-all.sh` 13/13 green** — Story 8.5 does NOT add new stages.
- **Codex review fix-up budget: expect 0-4 fix-ups.** The most likely surface areas:
  - (a) **Cross-module private-name import** — the `from app.modules.invite.router import _MIN_PASSWORD_LEN, _MIN_ZXCVBN_SCORE, _LEN_MSG, _SCORE_MSG` may be flagged by Codex as a private-name leak. Defensible: the constants are stable contract (≥12 chars + zxcvbn ≥3 is in the PRD and unlikely to change). If Codex insists, promote to `apps/api/app/core/auth/password_policy.py` as a 4-line public module — adds ~10 LOC across two files for minimal value, hence deferred unless raised.
  - (b) **Audit-emission on weak-password (entity_id resolution)** — Codex may flag the audit-emission paths where `entity_id` is sometimes None (token_invalid) and sometimes the resolved user_id (weak_password, user_not_found). Defensible: the entity_id is set as soon as the user identity is known (post-claim); pre-claim it's None because the token was invalid. The asymmetry IS the audit-shape — operator can query by `entity_id IS NULL` to find "anonymous reset attempts" vs `entity_id IS NOT NULL` for "identified user reset attempts/successes".
  - (c) **Redis GETDEL vs Redis version constraint** — Codex may flag that GETDEL requires Redis 6.2+, and ask for a version assertion. Defensible: Init 0 baseline pins Redis ≥6.2 (verify with `docker compose config | grep redis:` in infra/); if uncertain, add a startup-config assertion in `main.py` lifespan-startup checking `redis_version >= "6.2"` via `INFO server` — but defer unless infra version is < 6.2 (extremely unlikely given Init 0 was 2024+).
  - (d) **Rate-limit middleware test gap** — Codex may flag that the test suite does not verify the new `/api/auth/password-reset` shares the `register` scope rate-limit (currently no test asserts the 4th attempt within 60s returns 429). DEFER to Story 9.2 NFR5-SEC-3 audit (verifies all rate-limit scopes); if Codex insists, add ONE smoke test in `tests/test_ratelimit_register.py` (if file exists) or `tests/test_password_reset_ratelimit.py` (new file) — keep to 5 lines max.

### Previous story intelligence (Stories 8.4 + 8.3 + 8.1 + 7.5 + 6.2 carryover)

- **Story 8.4 set the precedent for sub-router promotion** — §file-structure-requirements explicitly named Story 8.5 as the natural promotion point. Story 8.5 follows through by creating the NEW `password_reset/` sub-module instead of appending to admin/router.py.
- **Story 8.4 `auth.totp.disabled` actor-pivot audit pattern** — Story 8.5's `auth.password.reset.initiated` (admin mint, actor != entity) mirrors the actor-pivot semantics; the `auth.password.reset.completed` (consume, actor == entity) is the self-action shape.
- **Story 8.3 PATCH endpoint's `extra="forbid"` UserMutationRequest stays UNTOUCHED.** Story 8.5 does NOT extend it. Adding `password_reset: bool | None = None` to that schema would CONFLATE the password-reset audit shape with the role-change/deactivate audit shape — keep them distinct per Story 8.3 AC-4 verbatim convention.
- **Story 8.3 frontend `actionsDisabled = isSelf || isAgent` guard** — Story 8.5's new menu item inherits via the kebab-button-level disable (no new useState slot needed).
- **Story 7.5 user-side disable contract** — Story 8.5 does NOT mirror the re-auth gate (the consume endpoint is PUBLIC; the token IS the identity proof, NOT cookies+TOTP). The Fernet `totp_secret` is NOT touched by Story 8.5 (it's not a 2FA story).
- **Story 7.3 GETDEL atomic claim pattern** — Story 8.5's `PasswordResetService.claim()` mirrors `auth/totp/router.py:369` verbatim. Same atomicity property; same loser-gets-None semantics; same single-line `await redis.execute_command("GETDEL", key)` shape.
- **Story 6.2 invite-token JSON payload shape** — Story 8.5's Redis value mirrors invite payload structure: `{user_id, generated_by_user_id, generated_at}`. NO `role` field (password-reset doesn't carry role-grant semantics — the user already has a role from their existing User row), NO `invite_id` field (no DB row), NO `ttl_seconds` field (Redis EXPIRE handles TTL; the value just records the mint moment).
- **Story 6.4 register-endpoint password-strength gates** — Story 8.5 reuses the `_MIN_PASSWORD_LEN = 12` + `_MIN_ZXCVBN_SCORE = 3` constants via cross-module import. If the import path is objectionable, promote constants to a public `core/auth/password_policy.py` module (~10 LOC two-file change). Deferred unless Codex insists.
- **Story 6.6 register rate-limit scope** — Story 8.5 extends the path-match set, NOT the threshold. The shared budget (3 attempts / 60s per IP) is the deliberate design per epics §1818 verbatim.
- **Auto-deploy after merge** — per `feedback_auto_deploy_dev`, run `infra/scripts/deploy.sh` to `.190` after Story 8.5 merges to main.

### Git intelligence (recent commits)

```
af07752 fix(api,web): Story 8.4 codex P3 — colspan + race-safe force flag clear
ed84257 feat(api,web): admin 2FA overrides — force-enrollment + force-disable (Story 8.4)
ddb9f14 fix(api,web): Story 8.3 codex P1+P2 — typecheck guard + 2FA is_active gate
acd7a85 feat(api,web): per-user admin actions — role change + deactivate + force logout (Story 8.3)
ec5ac5d fix(api): Story 8.2 codex P2 — stable tie-breaker on user list pagination
```

Pattern (Epic 8 baseline): each story lands as `feat(<scopes>): <subject> (Story 8.X)` initial commit, then 1-2 `fix(...)` Codex P1/P2 follow-up commits on the same story-scoped subject before sprint-status flips `review` → `done`. Story 8.5's commit shape: `feat(api,web,tests): admin-issued password-reset link (Story 8.5)`.

### Project Structure Notes

- **Alignment with unified project structure:** all new content lands in natural locations (new sub-module under `apps/api/app/modules/auth/`; mirrors the `auth/totp/` precedent; new test files under `apps/api/tests/`; new frontend route at `apps/web/src/routes/`; new modal at `apps/web/src/modules/admin/`; new Playwright spec at `apps/web/tests/visual/`; i18n keys in existing locale files). NO new top-level directories. NO new infra/scripts files. NO new Docker/Compose changes.
- **Detected conflicts or variances:** Story 8.4 deferred the sub-router promotion to Story 8.5 (per Story 8.4 §file-structure-requirements). Story 8.5 fulfills that deferral by creating the NEW `password_reset/` sub-module. The promotion is the binding architectural change Story 8.5 ships.
- **Naming conventions:** the new endpoint paths `/api/admin/users/{user_id}/password-reset` + `/api/auth/password-reset` follow the project's REST-action-as-sub-resource convention (compare `/api/admin/users/{id}/force-logout` from Story 8.3, `/api/admin/users/{id}/force-2fa-enrollment` from Story 8.4, `/api/auth/register` from Story 6.4). The new module `apps/api/app/modules/auth/password_reset/` follows the `apps/api/app/modules/auth/totp/` precedent (snake_case folder + 5 standard files). The new Settings field `password_reset_ttl_seconds` follows the `ratelimit_<scope>_<dimension>` snake_case convention. The audit action names `auth.password.reset.initiated` + `auth.password.reset.completed` follow the dot-separated action convention from FR5-AUDIT-1 §1200.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-A`] (lines 1417-1423) — invite-token storage rationale; Story 8.5 reuses the Redis primitive only
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-B`] (lines 1425-1456) — token shape verbatim; Story 8.5 reuses `secrets.token_urlsafe(32)` + JSON payload
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-G`] (lines 1559-1586) — rate-limit middleware; Story 8.5 extends register scope path-match
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision-L`] (lines 1741-1745) — self-service password reset deferred; Story 8.5 ships admin-issued only
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-8.5`] (lines 1806-1818) — Story 8.5 acceptance check shape verbatim
- [Source: `_bmad-output/planning-artifacts/epics.md#Epic-8-acceptance-gate`] (lines 1741-1745) — the four routine operator actions includes "reset user password (via 8.5)"
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-ADMIN-3`] (line 1195) — the binding PRD requirement (single-use, short TTL, Redis-fronted, out-of-band, two audit events, mirrored React route)
- [Source: `_bmad-output/planning-artifacts/prd.md#FR5-AUDIT-1`] (line 1200) — the audit-action surface; Story 8.5 reuses 2 of the 16 pre-registered names
- [Source: `_bmad-output/implementation-artifacts/6-2-invite-service-dual-backed-crud.md`] — the InviteService dual-backed pattern; Story 8.5's PasswordResetService is the Redis-only sibling
- [Source: `_bmad-output/implementation-artifacts/6-4-public-register-endpoint-and-ui.md`] — the public-side register-endpoint convention Story 8.5 mirrors (password-strength gates, audit emission)
- [Source: `_bmad-output/implementation-artifacts/6-6-ratelimit-middleware-login-refresh-register.md`] — the rate-limit middleware Story 8.5 extends
- [Source: `_bmad-output/implementation-artifacts/7-3-login-partial-auth-totp-verify.md`] — the GETDEL atomic claim pattern Story 8.5 reuses
- [Source: `_bmad-output/implementation-artifacts/8-3-per-user-actions-role-deactivate-force-logout.md`] — the admin-side per-user action precedent Story 8.5 extends
- [Source: `_bmad-output/implementation-artifacts/8-4-admin-2fa-overrides-force-enrollment-disable.md`] — the immediate predecessor; §file-structure-requirements named Story 8.5 as the sub-router promotion point
- [Source: `apps/api/app/modules/invite/service.py:1-260`] — the service class convention Story 8.5's PasswordResetService mirrors (Redis-only)
- [Source: `apps/api/app/modules/invite/router.py:1-100`] — the public-endpoint convention Story 8.5's consume endpoint mirrors
- [Source: `apps/api/app/modules/admin/router.py:444-507`] — Story 8.4's force-disable endpoint as the admin-mint structural template
- [Source: `apps/api/app/modules/auth/totp/router.py:361-371`] — the GETDEL atomic claim pattern Story 8.5 mirrors
- [Source: `apps/api/app/core/auth/ratelimit.py:106-109`] — the register_ratelimit_key path-match Story 8.5 extends
- [Source: `apps/api/app/core/audit.py:37-38`] — the audit-action names ALREADY pre-registered for Story 8.5 (zero-touch on the registry)
- [Source: `apps/api/app/core/config.py:48-58`] — the existing Pydantic Settings field convention
- [Source: `apps/web/src/modules/admin/UsersPage.tsx:1-602`] — Story 8.4's page Story 8.5 modifies
- [Source: `apps/web/src/modules/admin/hooks/useAdminUsers.ts:1-98`] — Story 8.4's hooks file Story 8.5 extends
- [Source: `apps/web/src/modules/admin/ChangeRoleModal.tsx`] — the modal-as-peer-of-page precedent Story 8.5's ResetLinkDisplayModal mirrors
- [Source: `apps/web/src/routes/register.tsx:1-153`] — the TanStack Router file-based-route Story 8.5's /reset-password mirrors
- [Source: `apps/web/src/lib/api-types.ts:220-227`] — Story 8.4's section-comment marker Story 8.5 appends after
- [Source: `apps/web/tests/visual/register.spec.ts`] — the Playwright spec shape Story 8.5's reset-password.spec.ts mirrors
- [Source: `_bmad-output/project-context.md`] — FastAPI / SQLModel / Alembic / vitest / Playwright conventions
- [Source: `AGENTS.md`] — repo layout + commit conventions + Polish-i18n requirement

## Dev Agent Record

### Agent Model Used

claude-opus-4-7[1m]

### Debug Log References

### Completion Notes List

### File List

### Change Log

| Date       | Author | Change                                                                                                                                                                              |
| ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-20 | Ezop   | Story 8.5 spec authored via bmad-create-story (autonomous YOLO mode). Admin-issued password-reset link (FR5-ADMIN-3): Decision A + B token reuse, NEW `auth/password_reset/` sub-module per Story 8.4's deferred promotion point, lost-2FA recovery Step 2 anchored, 18 backend tests + 8 frontend tests, audit-registry zero-touch. |
