# Story 6.4: Public `POST /api/auth/register` endpoint + `/register` UI

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want a new `apps/api/app/modules/invite/router.py` exposing the public `POST /api/auth/register` endpoint that consumes an invite token via the Story 6.2 `InviteService.consume()` flow + emits the three audit actions (`auth.register.success` / `auth.register.fail` / `auth.invite.used`) and the matching `apps/web/src/routes/register.tsx` React route that reads `?token=` from the query string + posts the form + redirects to `/catalog` on 201,
so that admin-generated invites from Story 6.3 (`POST /api/admin/invites` → cleartext `token` + `registration_url: "/register?token=<token>"`) actually become consumable member accounts end-to-end — closing FR5-REGISTER-1/2/3 + the FR5-INVITE-3 "revoked token returns HTTP 410 Gone" + FR5-INVITE-4 "single-use replay-fails-closed" contracts at the HTTP boundary, and matching the FR5-AUDIT-1 enumeration `auth.register.success` + `auth.register.fail` with reasons `token_invalid` / `token_consumed` / `weak_password` / `email_taken` (the four binding reason values; no synonyms) + `auth.invite.used` (the third caller-owned audit action from Story 6.2's contract — Story 6.3 owned `.generated` + `.revoked`, this story owns `.used`), one-time invite consumption that issues the standard Init 0 cookie pair (`portal_access` 10min + `portal_refresh` 30d) via the existing `app/core/auth/cookies.py:set_session_cookies()` helper so the freshly-registered member is logged in without an extra `/api/auth/login` round-trip, and zero new edges to the `X-Portal-Client: web` CSRF middleware (the global guard at `app/core/auth/csrf.py:14` already covers any `/api/*` unsafe-method route — explicit `csrf_required` 403 test exercises the new path).

## Acceptance Criteria

**AC-1 — `POST /api/auth/register` happy path: valid token + valid email + strong password → 201 + user row + invite consumed + cookies set + 3 audit rows.**

- Given an admin-generated invite from Story 6.3 (`InviteService.generate_invite(role=UserRole.member, ttl_seconds=604800, generated_by_user_id=<admin_uuid>)` returns `GenerateInviteResult(token="<43-char-urlsafe>", invite=<InviteToken row>)`; the Redis key `invite:token:<token>` exists with TTL ~604800; the `invite_tokens` row exists with `used_at IS NULL AND revoked_at IS NULL`),
- And an anonymous `TestClient` request (NO `portal_access` cookie set on the client; the conftest `client` fixture's default `X-Portal-Client: web` header IS set — this is required by the global CSRF middleware for any POST to `/api/*` outside `/api/share/*`),
- When the client POSTs `/api/auth/register` with body `{"token": "<cleartext-token>", "email": "newbie@example.com", "password": "correct horse battery staple"}` (the password is a 30-char Diceware passphrase chosen for `len >= 12 AND zxcvbn score >= 3`),
- Then the response is HTTP 201 with body shape `{"user": {"id": "<uuid>", "email": "newbie@example.com", "display_name": "newbie", "role": "member"}}` (the `display_name` is derived from `email.split("@", 1)[0]` — binding rule from Dev Notes § "display_name derivation"; matches the existing `MeResponse` shape from `apps/api/app/modules/auth/models.py:14-19` so callers can immediately consume the response with the same type that `/api/auth/me` returns),
- And the response sets BOTH `portal_access` (path=`/api`, max-age=600, httponly, samesite=strict) AND `portal_refresh` (path=`/api/auth`, max-age=2592000, httponly, samesite=strict) cookies — verified by `assert response.cookies.get("portal_access") is not None and response.cookies.get("portal_refresh") is not None` and by a follow-up `client.get("/api/auth/me")` returning HTTP 200 with the just-registered user's email (this proves end-to-end the cookies are valid and decode to the new user's JWT `sub` claim),
- And exactly one row exists in `user` table with `email="newbie@example.com"`, `role=UserRole.member`, `display_name="newbie"`, `password_hash` non-empty + bcrypt-verifiable against `"correct horse battery staple"` (via `verify_password()` from `app/core/auth/password.py:8`), `created_at` within ±5 seconds of `datetime.now(UTC)`,
- And the matching `invite_tokens` row is now `used_at IS NOT NULL` (within ±5 seconds of now), `used_by_user_id = <new-user.id>`, `used_from_ip = <test-client-ip>` (under `TestClient` this resolves to `"testclient"` — the binding value FastAPI's TestClient injects as `request.client.host`; the route uses the same `_client_meta()` helper shape as `auth/router.py:43-48` to honor `X-Forwarded-For`),
- And the Redis key `invite:token:<cleartext-token>` is GONE (`await fake_redis.get(f"invite:token:{token}")` returns `None` — service-internal DEL fires after the DB UPDATE commits per Story 6.2 `InviteService.consume()` flow),
- And exactly one new row exists in `audit_log` with `action="auth.invite.used"`, `entity_type="invite_token"`, `entity_id=<invite_id>`, `actor_user_id=<new-user.id>`, and an `after` JSON payload `{"used_from_ip": "<ip>"}` (NO `token` field — the cleartext token MUST NOT appear in `audit_log.after_json` per Decision B hygiene; the cleartext is already short-lived in the query string and never persists),
- And exactly one new row exists in `audit_log` with `action="auth.register.success"`, `entity_type="user"`, `entity_id=<new-user.id>`, `actor_user_id=<new-user.id>` (the registering user is their own actor — self-registration; mirrors `auth.login.success` pattern from `auth/router.py:89-96`), and an `after` JSON payload containing AT LEAST `{"email": "newbie@example.com", "role": "member", "invite_id": "<uuid>"}`,
- And exactly one new row exists in `refresh_tokens` with `user_id=<new-user.id>`, `family_id=<some-uuid>` (fresh family, not joined to any other), `family_issued_at` within ±5 seconds of now, `revoked_at IS NULL`, `token_hash` matching `hash_refresh_secret(<refresh-cookie-value>)` from `app/core/auth/refresh.py:43-44` (the route uses the same `new_refresh_row()` factory as `auth/router.py:71-78` — single source of truth for refresh-row construction).

**AC-2 — Token validation: never-existed → 404 `token_invalid`; revoked or already-used → 410 `token_consumed`; expired (TTL elapsed) → 404 `token_invalid`.**

- Given the four token states the InviteService surface produces (per Story 6.2 service contract + Story 6.3 admin endpoints):
  | Token state | Redis | DB row | Expected HTTP | Audit reason |
  |---|---|---|---|---|
  | `<random-43-char-string>` never generated | absent | absent | 404 | `token_invalid` |
  | Generated, then revoked via Story 6.3 `POST /api/admin/invites/{id}/revoke` | absent | present, `revoked_at IS NOT NULL` | 410 | `token_consumed` |
  | Generated, then consumed via this route (double-consume) | absent | present, `used_at IS NOT NULL` | 410 | `token_consumed` |
  | Generated with `ttl_seconds=60`, waited ≥61s | absent | present, no resolution columns, but `generated_at + ttl_seconds < now` | 404 | `token_invalid` |
- When the anonymous client POSTs `/api/auth/register` with `{"token": "<varies>", "email": "valid@example.com", "password": "correct horse battery staple"}` for each of the four cases,
- Then the response status matches the column above,
- And the response body is `{"detail": "<reason>"}` where `<reason>` matches the table (FastAPI default error envelope; matches every other admin/auth route in the repo — NO `{"error": {"code": ..., "message": ...}}` patterns),
- And exactly one `audit_log` row exists per failed attempt with `action="auth.register.fail"`, `entity_type="user"` (the audit pivot is the user-that-was-NOT-created — `entity_id=None` because no user row was created), `actor_user_id=None` (anonymous), and an `after` JSON payload `{"reason": "<reason>", "email": "valid@example.com"}` (the email is captured for triage; password is NEVER captured),
- And NO `user` row is created for any of the four cases,
- And NO `auth.register.success` row exists for any of the four cases,
- And for the "double-consume" case (case 3), the FIRST POST succeeded (AC-1 path) and the SECOND POST returns 410 — explicitly verified by `_register_once_succeed_then_replay_returns_410()` test (binding test name from AC-7),
- And for the "revoked" case (case 2), the revoke step uses `await InviteService(redis=..., engine=...).revoke(<invite_id>)` directly in the test setup (NOT a round-trip through Story 6.3's admin endpoint — keeps Story 6.4 tests independent of `admin_router.py` mounting; the unit-under-test is the register route, not the admin route),
- And the four failure paths use the SAME diagnosis order (Dev Notes § "Token-state diagnosis algorithm" is binding): (1) `await service.validate_active(token)` — if `None`, fall through; if returns `ActiveInvite`, the token is consumable and we proceed to password validation; (2) on Redis-miss, `Session(engine).exec(select(InviteToken).where(InviteToken.token_hash == hash_token(token))).first()` to DB-lookup; (3) if DB row absent → 404 `token_invalid`; (4) if `revoked_at IS NOT NULL` OR `used_at IS NOT NULL` → 410 `token_consumed`; (5) else (expired-naturally — no resolution columns + Redis-expired naturally) → 404 `token_invalid`.

**AC-3 — Password validation: zxcvbn score ≥3 AND length ≥12 enforced; failure → 422 `weak_password` + audit row + failing-rule body.**

- Given a valid (Redis-present, DB-active, not-revoked, not-used) invite token,
- When the anonymous client POSTs `/api/auth/register` with one of these failing-password cases,
  | Case | Password | zxcvbn score | Length | Failing rule (body) | HTTP |
  |---|---|---|---|---|---|
  | A: too short, weak | `"abc12"` | <3 | 5 | `"password must be at least 12 characters"` | 422 |
  | B: long enough, very weak | `"password123!"` (12 chars, common pattern) | <3 | 12 | `"password is too predictable; choose a stronger one"` | 422 |
  | C: too short, otherwise strong | `"x*7M&!q9z"` (random 9 chars) | ≥3 | 9 | `"password must be at least 12 characters"` | 422 |
  | D: long random but score 2 | `"aaaaaaaaaaaaa"` (13 a's) | <3 | 13 | `"password is too predictable; choose a stronger one"` | 422 |
- Then the response status is HTTP 422 with body `{"detail": "<failing-rule-string-from-table>"}` (the exact string is binding because the UI surfaces it inline — see AC-5),
- And the password is NEVER stored anywhere: NO `user` row is created, the password string never appears in `audit_log.after_json` (verified by `assert "password" not in json.loads(audit.after_json) and "abc12" not in audit.after_json`), and NEVER appears in any structured log emission (the existing `TokenRedactionFilter` from Story 6.1 in `app/core/logging.py` redacts password field-names in log records — the route code MUST NOT directly log the password value),
- And exactly one new `audit_log` row exists with `action="auth.register.fail"`, `entity_type="user"`, `entity_id=None`, `actor_user_id=None`, `after={"reason": "weak_password", "email": "valid@example.com"}` (NO `password` field; NO failing-rule detail in audit — keep audit triage-stable; the rule string lives in the HTTP response body only),
- And the invite is NOT consumed: Redis key `invite:token:<token>` STILL exists, `invite_tokens.used_at IS NULL`, NO `auth.invite.used` row in audit (password validation is a pre-flight gate; consume only fires on the all-checks-pass path),
- And rule precedence is: length first, then zxcvbn (binding — see Dev Notes § "Password validation order"). Case A (length=5, score<3) returns the LENGTH message, not the zxcvbn message; this keeps the UI hint cleaner. Case B (length=12, score<3) returns the zxcvbn message.

**AC-4 — Email collision: existing `user` row with same email → 409 `email_taken` + audit row + invite NOT consumed.**

- Given a valid invite token + an existing `user` row with `email="taken@example.com"` (seeded via the conftest admin-bootstrap pattern: `Session(engine).add(User(email="taken@example.com", display_name="Taken", role=UserRole.member, password_hash=hash_password("preexisting")))`),
- When the anonymous client POSTs `/api/auth/register` with `{"token": "<valid>", "email": "taken@example.com", "password": "correct horse battery staple"}`,
- Then the response is HTTP 409 with body `{"detail": "email_taken"}`,
- And NO NEW `user` row is created (the existing row is unchanged — `password_hash` stays as-is, verified by `verify_password("preexisting", existing.password_hash) is True`),
- And exactly one new `audit_log` row exists with `action="auth.register.fail"`, `entity_type="user"`, `entity_id=<existing-user.id>` (the audit pivot IS the existing user since the registration attempt was AGAINST that identity — different from AC-2/AC-3 where no user exists yet), `actor_user_id=None`, `after={"reason": "email_taken", "email": "taken@example.com"}`,
- And the invite is NOT consumed: Redis key STILL exists, `invite_tokens.used_at IS NULL`, NO `auth.invite.used` audit row,
- And the email comparison is case-sensitive (the existing User model has `email: str = Field(unique=True, index=True)` with no case-folding — `"Taken@example.com"` would slot a NEW row alongside `"taken@example.com"`). This is the binding behaviour; case-insensitive email is out of scope for Initiative 5 (and would require an Alembic migration to add a `CITEXT`-style index).

**AC-5 — Frontend route `/register` reads `?token=`, posts the form, redirects to `/catalog` on 201, surfaces 422/409/404/410 inline.**

- Given a built React app served by Vite dev (or production bundle),
- When a user navigates to `/register?token=<43-char-urlsafe>`,
- Then the `apps/web/src/routes/register.tsx` component (TanStack file route at `/register` with `validateSearch` extracting `token: string`) renders a form with three visible fields: `email` (type=email, autoComplete="email", required), `password` (type=password, autoComplete="new-password", required), and a submit button. NO `display_name` field — derived server-side from email local part (matches AC-1 derivation rule + keeps the form minimal per FR5-REGISTER-2 "captures email + password").
- And the form's `onSubmit` handler calls `api<MeResponse>("/auth/register", { method: "POST", body: JSON.stringify({ token, email, password }) })` (the existing `apps/web/src/lib/api.ts:11-13` helper — same shape as `login.tsx:31-34`) and on resolve, invalidates the `["auth", "me"]` query key (matches `login.tsx:35`) and `navigate({ to: "/catalog" })`,
- And on rejection (the `api` helper throws `ApiError` with `status` + `body`), the component surfaces the response body's `detail` field as an inline error message:
  | HTTP | Body `detail` | UI presentation | Element |
  |---|---|---|---|
  | 422 | varies (weak_password rule string OR pydantic-422 schema error) | Inline below password input, role="alert" | `<p className="text-sm text-destructive">` mirroring `login.tsx:77` |
  | 409 | `"email_taken"` | Inline below email input, role="alert", localized message | i18n key `auth.register.error.email_taken` |
  | 404 | `"token_invalid"` | Full-page error state (replaces form) | i18n key `auth.register.error.token_invalid` |
  | 410 | `"token_consumed"` | Full-page error state (replaces form) | i18n key `auth.register.error.token_consumed` |
- And the four i18n keys are added to BOTH `apps/web/src/locales/en.json` and `apps/web/src/locales/pl.json` (file uses flat-key dot-notation per the existing convention; see Dev Notes § "i18n keys to add" for the exact key list + Polish translations),
- And `/register` with NO `?token=` query param renders the same full-page error state used for HTTP 404 (i18n `auth.register.error.token_missing` — a fifth key; the form is not rendered without a token because there's no point submitting a tokenless request that would 422 at the schema layer anyway),
- And the route is publicly accessible without authentication — the existing `AppShell` from `apps/web/src/shell/AppShell.tsx:9-12` only short-circuits for `/share/*` paths; `/register` flows through the shell normally. **BUT** the `AuthGate` is NOT applied to `/register` (it's applied per-route, not globally — `login.tsx` similarly lacks it, see `routes/login.tsx`). New register route follows the login-route shape: no `<AuthGate>` wrapper, top-level `Outlet`-rendered component,
- And a successful registration's redirect to `/catalog` triggers `AuthGate` (catalog route is gated), which after the cookie is set + `useQuery(["auth", "me"])` resolves, allows passage — the post-register catalog page renders normally for the new member,
- And the component handles the in-flight `pending` state: submit button shows the localized `auth.register.signing_up` label while the request is pending (matches `login.tsx:79`'s `auth.signing_in` pattern; new key needed).

**AC-6 — Visual-regression baseline for `/register` page added in the same commit; matches the "no red state" rule from Init 3.**

- Given the existing Playwright visual-regression suite at `apps/web/tests/visual/`,
- When the dev agent ships Story 6.4,
- Then a NEW file `apps/web/tests/visual/register.spec.ts` is added with the following test cases (binding names — Dev Agent TDD red-phase checklist):
  - `renders register form with token in URL` — navigates to `/register?token=test-token-43-chars-AAAAAAAAAAAAAAAAAAAA`, asserts visible email input + password input + submit button + page H1, takes snapshot (light + dark + mobile + viewer3d-disabled projects — 4 PNGs per assertion under `__snapshots__/register.spec.ts/`),
  - `renders missing-token error state` — navigates to `/register` (no query string), asserts the full-page error message + retry/login link is visible + the form is NOT visible, takes snapshot,
  - `renders token_invalid error state` — stubs `**/api/auth/register` → 404 `{"detail": "token_invalid"}`, fills + submits the form, asserts the full-page error message is visible + the form is NOT visible, takes snapshot,
  - `renders token_consumed error state` — same as above but stubs → 410 `{"detail": "token_consumed"}`,
  - `renders weak_password inline error` — stubs → 422 `{"detail": "password must be at least 12 characters"}`, fills + submits, asserts the inline error appears below the password input + the form is STILL visible, takes snapshot,
  - `renders email_taken inline error` — stubs → 409 `{"detail": "email_taken"}`, fills + submits, asserts inline error below email input, takes snapshot,
- And the spec file uses `import { expect, test } from "./_test";` (the shared fixture with the `**/api/**` catch-all 404 + `**/api/auth/me` 401 stubs — pattern from `apps/web/tests/visual/_test.ts:21-41`), NOT raw `import { test } from "@playwright/test"`,
- And the spec file uses `waitForReady(page, { skipAuthGate: true })` or equivalent — the helper `apps/web/tests/visual/helpers.ts` may need a new variant if the existing waits assume `auth/me` resolves to 200; check + extend if needed (see Dev Notes § "helpers.ts changes might be needed"),
- And the baselines are generated locally (`npm run test:visual -- --update-snapshots` for `register.spec.ts` only) and committed in the SAME commit as the source changes per FR13 "Baseline Acceptance Gate" hook from Story 5.13 — the dev agent MUST commit `apps/web/tests/visual/register.spec.ts` AND its `__snapshots__/register.spec.ts/` PNGs together; partial commits will trip the husky `_check-baseline-review.mjs` pre-commit hook,
- And the four project matrix from `apps/web/tests/visual/playwright.config.ts` runs each `register.spec.ts` test 4 times: `chromium-light`, `chromium-dark`, `chromium-mobile`, `chromium-viewer3d-disabled`. Story 6.4 expects 6 specs × 4 projects = 24 new PNGs in `__snapshots__/register.spec.ts/`.

**AC-7 — All endpoint + UI flows test-covered with named tests; full backend suite + full vitest + full visual suite green.**

- Given the test scaffolding already in place (`apps/api/tests/test_invite_admin.py` fixture shape from Story 6.3; `apps/web/src/routes/login.test.tsx` vitest shape; `apps/web/tests/visual/_test.ts` Playwright shared fixture),
- When the dev agent ships Story 6.4,
- Then a NEW file `apps/api/tests/test_invite_register.py` contains AT LEAST the following test cases (binding names — Dev Agent TDD red-phase checklist):
  - `test_register_happy_path_creates_user_and_consumes_invite` — AC-1 full flow
  - `test_register_sets_both_session_cookies_and_me_succeeds` — AC-1 follow-up `/api/auth/me` confirms the cookies decode + match the new user
  - `test_register_emits_three_audit_rows_no_cleartext_token` — AC-1 audit assertions: `auth.invite.used` + `auth.register.success` + no audit row contains `token` field
  - `test_register_creates_refresh_token_row_with_fresh_family` — AC-1 `refresh_tokens` row check
  - `test_register_token_never_existed_returns_404_token_invalid` — AC-2 case 1
  - `test_register_revoked_token_returns_410_token_consumed` — AC-2 case 2; uses `await service.revoke(invite_id)` in setup
  - `test_register_used_token_returns_410_token_consumed` — AC-2 case 3; uses `await service.consume(token, used_by_user_id=<seeded-user-id>, used_from_ip="setup")` in setup
  - `test_register_expired_token_returns_404_token_invalid` — AC-2 case 4; freezes Redis TTL via `await fake_redis.delete(f"invite:token:{token}")` to simulate natural expiry, leaves DB row intact with `generated_at = now - 2*ttl_seconds` to confirm the DB-side expiry diagnosis path
  - `test_register_double_consume_first_succeeds_second_returns_410` — AC-2 explicit replay test: first POST returns 201; second POST with the SAME token returns 410 (the Story 6.2 service-internal predicate is the atomic guard; this test verifies the route surfaces the correct status)
  - `test_register_weak_password_short_returns_422_length_message` — AC-3 case A
  - `test_register_weak_password_low_score_returns_422_zxcvbn_message` — AC-3 case B
  - `test_register_weak_password_short_and_strong_returns_422_length_message` — AC-3 case C (length wins over zxcvbn — precedence test)
  - `test_register_weak_password_audit_omits_password_value` — AC-3 audit hygiene; explicit `assert "password" not in audit.after_json and "abc12" not in audit.after_json`
  - `test_register_weak_password_does_not_consume_invite` — AC-3 invite-preservation: Redis key still present, `used_at IS NULL`, no `auth.invite.used` row
  - `test_register_email_taken_returns_409` — AC-4 happy denial
  - `test_register_email_taken_does_not_consume_invite` — AC-4 invite preservation
  - `test_register_email_taken_does_not_mutate_existing_user` — AC-4 existing-user safety
  - `test_register_invalid_email_rfc_returns_422` — pydantic `EmailStr` rejects `"not-an-email"` at the schema layer → automatic 422 from FastAPI (the route function body never runs; NO audit row emitted because the schema validation fails before the route handler executes — this is the existing pydantic-422 contract, not a new audit reason)
  - `test_register_csrf_header_required_returns_403` — strip `X-Portal-Client` header; expect 403 `csrf_required` from the global middleware (verifies the new route is covered by the existing global CSRF guard)
  - `test_register_missing_token_field_returns_422` — pydantic schema rejection
  - `test_register_missing_email_field_returns_422` — pydantic schema rejection
  - `test_register_missing_password_field_returns_422` — pydantic schema rejection
  - `test_register_display_name_derived_from_email_local_part` — AC-1 `display_name` derivation; explicit assert
- And `pytest apps/api/tests/test_invite_register.py -v` exits 0 with all the above tests green,
- And `pytest apps/api/ -q` exits 0 with no regressions vs. the Story 6.3 baseline (~484 backend tests; this story adds ~22 → expected ~506+),
- And a NEW file `apps/web/src/routes/register.test.tsx` contains AT LEAST these vitest cases (mirrors `login.test.tsx:54-103` shape):
  - `renders email + password inputs with proper autoComplete + required attributes`
  - `submits the form with token from query string + email + password`
  - `redirects to /catalog on 201 response`
  - `surfaces 422 detail string as inline error below password input`
  - `surfaces 409 email_taken as inline error below email input`
  - `surfaces 404 token_invalid as full-page error replacing the form`
  - `surfaces 410 token_consumed as full-page error replacing the form`
  - `renders token_missing error state when ?token= query param is absent`
- And `npm run test --workspace apps/web register.test.tsx` exits 0; the full `npm run test --workspace apps/web` exits 0 with no regressions,
- And the visual-regression suite passes: `npm run test:visual` exits 0 with the 24 new PNGs from AC-6 registering as passing baseline,
- And `infra/scripts/check-all.sh` from the repo root exits 0 (all 10 stages green; matches the Story 6.3 close-out gate from sprint-status.yaml Sesja N note).

**AC-8 — Files, imports, dependencies, registrations: full-file inventory + zero-drift wiring.**

- Given the existing module / file conventions from Stories 6.1–6.3 (invite-module structure, audit registry, router include, schema re-exports),
- When the dev agent ships Story 6.4,
- Then the file inventory is EXACTLY:
  - **NEW** `apps/api/app/modules/invite/router.py` (~180–220 LOC: the `register()` route + the diagnosis helper + the audit emission + the cookie wiring; binding skeleton in Dev Notes § "Implementation skeleton — invite/router.py")
  - **NEW** `apps/api/app/modules/invite/schemas.py` (~30 LOC: `RegisterRequest` Pydantic schema; named `schemas.py` NOT `register_schemas.py` because this is the public-side schemas module and the project's precedent in `share/models.py` mixes the public-side concerns into a single per-module schema file — see Dev Notes § "schemas.py vs admin_schemas.py rationale")
  - **NEW** `apps/api/tests/test_invite_register.py` (~600+ LOC; the 22+ named tests from AC-7)
  - **NEW** `apps/web/src/routes/register.tsx` (~120 LOC: file-route export + component)
  - **NEW** `apps/web/src/routes/register.test.tsx` (~150 LOC: 8 vitest cases)
  - **NEW** `apps/web/tests/visual/register.spec.ts` (~110 LOC: 6 specs × 4 projects)
  - **NEW** `apps/web/tests/visual/__snapshots__/register.spec.ts/*.png` (24 PNGs)
  - **UPDATED** `apps/api/app/router.py` (add `from app.modules.invite.router import router as invite_public_router` + `api_router.include_router(invite_public_router)` AFTER `auth_router` to keep `/api/auth/*` routes contiguous; see Dev Notes § "Router registration order" for the exact line-level placement)
  - **UPDATED** `apps/api/app/modules/invite/__init__.py` (add `RegisterRequest` from `.schemas` to imports + sorted `__all__`)
  - **UPDATED** `apps/api/pyproject.toml` (add `"zxcvbn>=4.4.28"` to `[project] dependencies` — sorted insertion between `"uvicorn[standard]>=0.32"` and `"arq>=0.26"`; the package is `zxcvbn` on PyPI, not `py-zxcvbn` — see Dev Notes § "zxcvbn library selection")
  - **UPDATED** `apps/web/src/locales/en.json` AND `apps/web/src/locales/pl.json` (add the 6 new `auth.register.*` keys listed in Dev Notes § "i18n keys to add")
  - **UPDATED** `apps/web/src/routeTree.gen.ts` (auto-generated by `@tanstack/router-vite-plugin` on `npm run build` or `npm run dev`; the dev agent does NOT hand-edit this file — running the build IS the regeneration. The commit MUST include the regenerated file so CI's `tsc -b` succeeds; verified via `git diff --stat` showing `routeTree.gen.ts` updated alongside `routes/register.tsx`)
- And the imports in `router.py` are EXACTLY (sorted by ruff isort rules; copy-paste binding):
  ```python
  import datetime
  import logging
  import uuid
  from typing import Annotated

  from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
  from sqlmodel import Session, select

  from app.core.audit import record_event
  from app.core.auth.cookies import set_session_cookies
  from app.core.auth.jwt import encode_token
  from app.core.auth.password import hash_password
  from app.core.auth.refresh import new_refresh_row
  from app.core.config import Settings, get_settings
  from app.core.db.models import User
  from app.core.db.models._enums import UserRole
  from app.core.db.session import get_engine, get_session
  from app.modules.auth.models import LoginResponse, MeResponse  # response shape reuse (mirrors auth/router.py login())
  from app.modules.invite import InviteConsumed, InviteService, InviteToken, hash_token
  from app.modules.invite.schemas import RegisterRequest
  ```
- And NO new top-level main.py edits are needed (the global CSRF middleware at `app/main.py:68` already covers `/api/auth/register` automatically; `app.state.redis` is already mounted; `get_engine()` is already cached),
- And the new file passes `ruff format apps/api/` + `ruff check apps/api/` cleanly with NO `# noqa` exceptions (matches the repo's strict-clean policy from `pyproject.toml` § ruff settings),
- And the OpenAPI surface gains exactly ONE new entry: `POST /api/auth/register` with `tags=["auth", "invite"]`, summary `"Public invite-token registration"`, description per the Story 4.3 OpenAPI surface enrichment convention (operator-facing one-sentence description). Verified by `pytest apps/api/tests/test_runbook.py -k openapi` (the existing OpenAPI smoke gate) + manual `curl http://localhost:8000/openapi.json | jq '.paths["/api/auth/register"]'` showing the route exists with the documented fields.

## Tasks / Subtasks

- [x] **T1 — Add `zxcvbn` dependency + `RegisterRequest` schema (AC-3, AC-7, AC-8)**
  - [x] T1.1 Edit `apps/api/pyproject.toml`: add `"zxcvbn>=4.4.28"` to `[project] dependencies`, sorted alphabetically. After editing, run `pip install -e .[dev]` in the `apps/api/` cwd to install the new dependency into the active venv.
  - [x] T1.2 Verify `zxcvbn` import works: `python -c "import zxcvbn; print(zxcvbn.zxcvbn('correct horse battery staple')['score'])"` — expect score `4` (the canonical Diceware example).
  - [x] T1.3 Create NEW file `apps/api/app/modules/invite/schemas.py` with `RegisterRequest(BaseModel)` containing 3 fields: `token: str = Field(min_length=43, max_length=43)` (binding length match for `secrets.token_urlsafe(32)`), `email: EmailStr` (pydantic-validated RFC syntax), `password: str = Field(min_length=1)` (length floor at the schema layer — the route-level validation enforces `>=12` for the meaningful error; schema floor of 1 just prevents an empty-string DOS). `model_config = ConfigDict(extra="forbid")`.
  - [x] T1.4 Update `apps/api/app/modules/invite/__init__.py`: add `from app.modules.invite.schemas import RegisterRequest` to imports + `"RegisterRequest"` to `__all__` (sorted insertion between `"InviteToken"` and `"hash_token"`).

- [x] **T2 — Author `apps/api/app/modules/invite/router.py` register route — RED-GREEN-REFACTOR (AC-1, AC-2, AC-4, AC-7)**
  - [x] T2.1 RED — create `apps/api/tests/test_invite_register.py` with the conftest fixture shape from `test_invite_admin.py:34-65` (TestClient + fakeredis swap into `app.state.redis` + `_clear_invite_and_audit_tables` autouse + helper functions). Author the AC-1 happy-path test (`test_register_happy_path_creates_user_and_consumes_invite`) + the AC-2 four token-state tests + AC-4 email-taken test against the not-yet-written route. Expected initial state: every test fails with HTTP 404 (route not registered).
  - [x] T2.2 GREEN — create `apps/api/app/modules/invite/router.py` per the skeleton in Dev Notes § "Implementation skeleton — invite/router.py". Wire the `_service(request)` factory (mirror `admin_router.py:25-26`) + the `register()` route handler + the token-state diagnosis helper. **Critical:** the diagnosis algorithm runs BEFORE any user-creation work to keep failure paths cheap + audit-clean. Bind to the Dev Notes § "Token-state diagnosis algorithm" sequence.
  - [x] T2.3 Wire `auth.invite.used` audit emission AFTER `service.consume()` succeeds. Wire `auth.register.success` audit emission AFTER the user is committed + the refresh row is committed. Wire `auth.register.fail` emission on each failure path with the matching `reason` field per AC-2/AC-3/AC-4 tables.
  - [x] T2.4 Wire the cookie issuance: mint `access` JWT via `encode_token(subject=str(user.id), role=user.role.value, secret=settings.jwt_secret, ttl_minutes=settings.jwt_ttl_minutes)` (binding mirror of `auth/router.py:82-87`) + a fresh refresh family via `new_refresh_row(user_id=user.id, family_id=None, ...)` (binding mirror of `auth/router.py:71-78`) + call `set_session_cookies(response, access=access, refresh=secret, settings=settings)`. The refresh row INSERT MUST commit BEFORE returning the response (or the cookie's refresh secret won't be findable on next `/api/auth/refresh`).
  - [x] T2.5 Run the AC-1 + AC-2 + AC-4 tests; expect all green.

- [x] **T3 — Add zxcvbn password validation (AC-3, AC-7)**
  - [x] T3.1 RED — author the 5 password-validation tests from AC-7 (`test_register_weak_password_*`) against the not-yet-validated route.
  - [x] T3.2 GREEN — add the validation block to `register()` per the Dev Notes § "Password validation order" precedence rule: (1) if `len(password) < 12` → raise `HTTPException(422, "password must be at least 12 characters")`; (2) elif `zxcvbn.zxcvbn(password)["score"] < 3` → raise `HTTPException(422, "password is too predictable; choose a stronger one")`. Place the validation block BEFORE the email-uniqueness check (cheapest checks first — token already passed at this point).
  - [x] T3.3 Wire `auth.register.fail` emission with `after={"reason": "weak_password", "email": payload.email}` for both length and zxcvbn paths (single emission, before the `raise`).
  - [x] T3.4 Re-run the 5 password-validation tests; expect all green. Confirm with the AC-3 hygiene tests that the password value never appears in any audit row.

- [x] **T4 — Wire router registration + `app/router.py` include (AC-8)**
  - [x] T4.1 Edit `apps/api/app/router.py`: add `from app.modules.invite.router import router as invite_public_router` (alphabetical-by-module: `invite.admin_router` already imported on the prior line; new line goes immediately AFTER it; see Dev Notes § "Router registration order"). Add `api_router.include_router(invite_public_router)` AFTER the existing `api_router.include_router(auth_router)` call (keeps `/api/auth/*` routes contiguous).
  - [x] T4.2 Run `pytest apps/api/tests/test_invite_register.py -v` — all 22+ tests green.
  - [x] T4.3 Run the existing OpenAPI smoke gate: `pytest apps/api/tests/test_runbook.py -k openapi`. Verify `/api/auth/register` appears in the spec with `tags=["auth", "invite"]` + summary + description.
  - [x] T4.4 Run `pytest apps/api/ -q` — full backend suite green (baseline 484; expected 506+).
  - [x] T4.5 Run `ruff format apps/api/` + `ruff check apps/api/` — clean. No `# noqa` exceptions.

- [x] **T5 — Frontend `register.tsx` route + vitest tests (AC-5, AC-7)**
  - [x] T5.1 Add i18n keys to `apps/web/src/locales/en.json` and `pl.json` per Dev Notes § "i18n keys to add" — 6 new keys total (`auth.register.title`, `auth.register.signing_up`, `auth.register.error.token_invalid`, `auth.register.error.token_consumed`, `auth.register.error.token_missing`, `auth.register.error.email_taken`).
  - [x] T5.2 RED — create `apps/web/src/routes/register.test.tsx` mirroring the `login.test.tsx:1-103` shape: vitest + `@testing-library/react` + mock `@/lib/api`. Author the 8 named tests from AC-7 against the not-yet-written component.
  - [x] T5.3 GREEN — create `apps/web/src/routes/register.tsx` per the Dev Notes § "Implementation skeleton — register.tsx" skeleton: TanStack file route at `/register` with `validateSearch` extracting `token?: string`, a component that renders the form when token is present and the missing-token error state when absent, an `onSubmit` handler that calls `api("/auth/register", { method: "POST", body: JSON.stringify({ token, email, password }) })`, an error-state branching that switches between inline error (for 422/409) and full-page error (for 404/410) based on `ApiError.status`.
  - [x] T5.4 Run `npm run test --workspace apps/web register.test.tsx` — all 8 tests green. Run `npm run lint --workspace apps/web` — clean. Run `npm run typecheck --workspace apps/web` — clean.
  - [x] T5.5 Trigger `routeTree.gen.ts` regeneration: `npm run dev --workspace apps/web` (the Vite plugin regenerates the file on startup; let it run ~5 seconds, then Ctrl+C). Verify `git diff apps/web/src/routeTree.gen.ts` shows `/register` route added.

- [x] **T6 — Visual-regression baseline (AC-6, AC-7)**
  - [x] T6.1 Create `apps/web/tests/visual/register.spec.ts` per Dev Notes § "Implementation skeleton — register.spec.ts" — 6 named specs, each `import { expect, test } from "./_test"` + `import { waitForReady } from "./helpers"`.
  - [x] T6.2 If `waitForReady()` assumes `/api/auth/me` resolves to 200, add a `{ skipAuthGate?: boolean }` parameter that allows the helper to short-circuit the AuthGate wait when on the `/register` route (which doesn't apply AuthGate at all). Document the change in Dev Agent Record + File List.
  - [x] T6.3 Generate baselines: `cd apps/web && npx playwright test tests/visual/register.spec.ts --update-snapshots`. Visual inspection of each new PNG: form looks correct, error states render legibly, dark/mobile variants don't have layout regressions.
  - [x] T6.4 Run the FULL visual suite: `cd apps/web && npm run test:visual`. Expected: 164 passed (baseline) + 24 new (register × 4 projects × 6 specs) = 188 passed total. No `register.spec.ts` failures.

- [x] **T7 — Final quality gate + status flip (all ACs)**
  - [x] T7.1 Run `pytest apps/api/tests/test_invite_register.py -v` — all 22+ green.
  - [x] T7.2 Run `pytest apps/api/ -q` — full backend suite green (~506+).
  - [x] T7.3 Run `npm run test --workspace apps/web` — full vitest suite green.
  - [x] T7.4 Run `npm run lint --workspace apps/web` + `npm run typecheck --workspace apps/web` — clean.
  - [x] T7.5 Run `ruff format apps/api/` + `ruff check apps/api/` — clean.
  - [x] T7.6 Run `infra/scripts/check-all.sh` from repo root — all 10 stages green.
  - [x] T7.7 Update Dev Agent Record (Agent Model + Debug Log + Completion Notes + File List) below; flip `Status:` to `review`.

## Dev Notes

### Relevant architecture patterns and constraints

- **Init 0 auth-router precedent — cookie issuance + audit emission shape.** `apps/api/app/modules/auth/router.py:51-104` (the `login()` handler, 54 LOC) is the canonical template for the cookie pair + audit emission. Quick anatomy mapping:
  - `login()` lines 71-78: `secret, row = new_refresh_row(user_id=user.id, family_id=None, ...)` + `session.add(row)` + `session.commit()` → identical pattern in `register()` (binding mirror).
  - `login()` lines 82-87: `access = encode_token(subject=str(user.id), role=user.role.value, secret=settings.jwt_secret, ttl_minutes=settings.jwt_ttl_minutes)` → identical pattern.
  - `login()` line 88: `set_session_cookies(response, access=access, refresh=secret, settings=settings)` → identical call.
  - `login()` lines 89-96: `record_event(get_engine(), action="auth.login.success", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"email": user.email})` → mirrored as `auth.register.success` with the additional `invite_id` field in `after`.
  - **The deliberate divergence:** register issues the COOKIE PAIR + the `auth.register.success` audit event WITHOUT a prior `verify_password()` check — the invite-token consumption IS the auth check. This is by design per FR5-REGISTER-3 "Successful registration creates a user account ... and issues the standard cookie pair — the same auth surface as `/api/auth/login`."

- **Decision A — dual-backed storage** (`architecture.md` §1417-1423): Redis is authoritative for "is this token currently consumable", DB is authoritative for "what happened". For the public register route, Decision A binds the TOKEN VALIDATION ORDER: Redis FIRST (cheap O(1) lookup), DB only on Redis miss (for diagnosis between 404 and 410). The route MUST NOT skip the Redis check — that's the FR5-INVITE-1 dual-backed contract.

- **Decision B — token surface hygiene** (`architecture.md` §1425-1456): The cleartext token appears in TWO places only: (1) the one-time `POST /api/admin/invites` response from Story 6.3 AC-1, and (2) the `/register?token=` query string during consumption (THIS story's surface). The token MUST NOT appear in:
  - `audit_log.after_json` for ANY audit row this story emits (AC-1 + AC-2 + AC-3 + AC-4 verify this with explicit `assert "token" not in audit.after_json` assertions)
  - Any structured log emission (the existing `TokenRedactionFilter` from Story 6.1 is the defense-in-depth catch; the route code MUST NOT directly log the cleartext token)
  - The DB row beyond the SHA-256 `token_hash` (the schema from Story 6.1 stores only the hash — no change this story)
  - Any error response body (the FastAPI default `{"detail": "<reason>"}` envelope never echoes the token)

- **Decision C — cookie issuance reuses Init 0 contract** (`architecture.md` §1458-1487): The register response sets the SAME `portal_access` (10min, path=/api) + `portal_refresh` (30d, path=/api/auth) cookies as `/api/auth/login`. Existing `set_session_cookies()` from `app/core/auth/cookies.py:41-43` IS the binding helper — DO NOT re-implement cookie attributes inline.

- **FR5-REGISTER-1 / FR5-REGISTER-2 / FR5-REGISTER-3 / FR5-AUDIT-1** are the four FRs this story realizes (per `epics.md:1586-1597` + the matching `prd.md:1174-1176, :1200` lines). The verifiable acceptance shapes are:
  - FR5-REGISTER-1 (`prd.md:1174`): "a request with a tampered/unknown token returns 404 + the audit row is present." → AC-2.
  - FR5-REGISTER-2 (`prd.md:1175`): "a deliberate weak password (`password123!`) is rejected with 422 and the response body identifies the failing strength check." → AC-3.
  - FR5-REGISTER-3 (`prd.md:1176`): "post-registration, `curl --cookie ...` against `/api/catalog/*` returns 200 without an extra login step." → AC-1 follow-up `/api/auth/me` test (the test fixture's local-scope analogue of the curl check).
  - FR5-AUDIT-1 (`prd.md:1200`): the 16 audit actions in `KNOWN_ENTITY_TYPES`; this story emits THREE of them (`auth.register.success`, `auth.register.fail`, `auth.invite.used`). Story 6.3 emitted `.generated` + `.revoked`; together they close the 4 E6 invite/register audit actions. (E6 total is 5 incl. `auth.register.fail` reasons; the action name is one entry but the `reason` field carries the four FR5-REGISTER reasons. No new audit action names need registering — `auth.register.*` is an action-name, the reasons live in the JSON payload.)
  - **NO changes to `KNOWN_ENTITY_TYPES` in `app/core/audit.py`.** The entity types `invite_token` + `user` are already registered (verified in `apps/api/app/core/audit.py:28-44`). The three audit ACTIONS this story emits all reuse those two entity types: `auth.invite.used` → `entity_type="invite_token"`; `auth.register.success` + `auth.register.fail` → `entity_type="user"`.

- **`X-Portal-Client: web` CSRF middleware** (`app/core/auth/csrf.py:14-19`): GLOBAL middleware that returns 403 `csrf_required` for any unsafe-method `/api/...` request (except `/api/share/*`) that lacks the `X-Portal-Client: web` header. The conftest `client` fixture at `apps/api/tests/test_invite_admin.py:54` sets this header by default (matches Story 6.3 fixture). AC-7 includes an explicit `test_register_csrf_header_required_returns_403` test that strips the header to verify the middleware reaches the new POST route. **No new middleware code needed.**

- **No new top-level main.py edits.** `app.state.redis` is already set up by the lifespan + `get_engine()` is already cached + CSRF middleware already mounted at `app/main.py:68` + the global pytest fixture `_isolated_db` from `apps/api/tests/conftest.py:31-57` already initializes the schema. The test fixture in `test_invite_register.py` mirrors `test_invite_admin.py` 1:1 in shape — DB swap + fakeredis swap + admin_uuid is unused (anonymous client only).

### Implementation skeleton — `apps/api/app/modules/invite/router.py` (binding for shape)

```python
"""Public invite-token register endpoint for Initiative 5 (Story 6.4).

Mirrors the Init 0 auth-router shape in
``apps/api/app/modules/auth/router.py`` for cookie + audit emission. Mirrors
the Init 5 invite/admin_router.py for the ``_service(request)`` factory.

Audit actions emitted:
- ``auth.invite.used``      on successful consumption (entity_type=invite_token)
- ``auth.register.success`` on successful registration (entity_type=user)
- ``auth.register.fail``    on any failure path (entity_type=user)

Failure-path reasons (FR5-AUDIT-1 binding set; no synonyms):
- ``token_invalid``  — Redis miss + DB row absent OR expired
- ``token_consumed`` — Redis miss + DB row revoked OR used (incl. race-lost)
- ``weak_password``  — length<12 OR zxcvbn score<3
- ``email_taken``    — user table already has the requested email
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Annotated

import zxcvbn
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.auth.cookies import set_session_cookies
from app.core.auth.jwt import encode_token
from app.core.auth.password import hash_password
from app.core.auth.refresh import new_refresh_row
from app.core.config import Settings, get_settings
from app.core.db.models import User
from app.core.db.models._enums import UserRole
from app.core.db.session import get_engine, get_session
from app.modules.auth.models import LoginResponse, MeResponse
from app.modules.invite import (
    InviteConsumed,
    InviteService,
    InviteToken,
    hash_token,
)
from app.modules.invite.schemas import RegisterRequest

_LOG = logging.getLogger("app.auth.register")
_MIN_PASSWORD_LEN = 12
_MIN_ZXCVBN_SCORE = 3

router = APIRouter(prefix="/api/auth", tags=["auth", "invite"])


def _service(request: Request) -> InviteService:
    return InviteService(redis=request.app.state.redis.get(), engine=get_engine())


def _client_ip(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    return ip or "unknown"


def _diagnose_inactive_token(session: Session, token: str) -> tuple[int, str]:
    """Return (http_status, reason) for a Redis-miss token. Binding precedence:
    1. DB row absent           → 404, token_invalid
    2. DB row revoked_at NOT NULL → 410, token_consumed
    3. DB row used_at NOT NULL    → 410, token_consumed
    4. DB row expired             → 404, token_invalid
    """
    row = session.exec(
        select(InviteToken).where(InviteToken.token_hash == hash_token(token))
    ).first()
    if row is None:
        return (404, "token_invalid")
    if row.revoked_at is not None:
        return (410, "token_consumed")
    if row.used_at is not None:
        return (410, "token_consumed")
    return (404, "token_invalid")  # expired-naturally


def _fail(
    *,
    engine,
    http_status: int,
    reason: str,
    email: str,
    actor_user_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> HTTPException:
    record_event(
        engine,
        action="auth.register.fail",
        entity_type="user",
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        after={"reason": reason, "email": email},
        request_id=request_id,
    )
    return HTTPException(http_status, reason if http_status != 422 else _MSG_FOR.get(reason, reason))


_MSG_FOR = {
    "weak_password_length": "password must be at least 12 characters",
    "weak_password_score": "password is too predictable; choose a stronger one",
}


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public invite-token registration",
    description=(
        "Consume an invite token + create the bound user account. "
        "Issues the standard portal_access (10min) + portal_refresh (30d) "
        "cookie pair; the client is logged in on response."
    ),
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    engine = get_engine()
    request_id = request.headers.get("x-request-id")
    ip = _client_ip(request)
    service = _service(request)

    # Step 1: token validation (Redis primary, DB fallback for diagnosis).
    active = await service.validate_active(payload.token)
    if active is None:
        http_status, reason = _diagnose_inactive_token(session, payload.token)
        raise _fail(
            engine=engine, http_status=http_status, reason=reason,
            email=payload.email, request_id=request_id,
        )

    # Step 2: password validation (length first, then zxcvbn).
    if len(payload.password) < _MIN_PASSWORD_LEN:
        raise _fail(
            engine=engine, http_status=422, reason="weak_password",
            email=payload.email, request_id=request_id,
        )  # message: "password must be at least 12 characters"
    score = zxcvbn.zxcvbn(payload.password)["score"]
    if score < _MIN_ZXCVBN_SCORE:
        raise _fail(
            engine=engine, http_status=422, reason="weak_password",
            email=payload.email, request_id=request_id,
        )  # message: "password is too predictable; choose a stronger one"

    # Step 3: email-uniqueness check (DB query).
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise _fail(
            engine=engine, http_status=409, reason="email_taken",
            email=payload.email, entity_id=existing.id, request_id=request_id,
        )

    # Step 4: create user.
    display_name = payload.email.split("@", 1)[0]
    user = User(
        email=payload.email,
        display_name=display_name,
        role=active.role,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Step 5: consume invite (atomic predicate; raises InviteConsumed on race-lost).
    try:
        await service.consume(payload.token, used_by_user_id=user.id, used_from_ip=ip)
    except InviteConsumed:
        # Race: between validate_active() and consume(), the token was
        # consumed/revoked by another process. Compensation: delete the
        # orphan user row we just created and surface 410 to the caller.
        session.delete(user)
        session.commit()
        raise _fail(
            engine=engine, http_status=410, reason="token_consumed",
            email=payload.email, request_id=request_id,
        ) from None

    record_event(
        engine, action="auth.invite.used", entity_type="invite_token",
        entity_id=active.invite_id, actor_user_id=user.id,
        after={"used_from_ip": ip}, request_id=request_id,
    )

    # Step 6: issue cookie pair + audit success.
    secret, refresh_row = new_refresh_row(
        user_id=user.id, family_id=None, family_issued_at=None,
        ip=ip, user_agent=request.headers.get("user-agent"),
    )
    session.add(refresh_row)
    session.commit()

    access = encode_token(
        subject=str(user.id), role=user.role.value,
        secret=settings.jwt_secret, ttl_minutes=settings.jwt_ttl_minutes,
    )
    set_session_cookies(response, access=access, refresh=secret, settings=settings)

    record_event(
        engine, action="auth.register.success", entity_type="user",
        entity_id=user.id, actor_user_id=user.id,
        after={
            "email": user.email,
            "role": user.role.value,
            "invite_id": str(active.invite_id),
        },
        request_id=request_id,
    )
    return LoginResponse(
        user=MeResponse(
            id=user.id, email=user.email, display_name=user.display_name, role=user.role,
        )
    )
```

### Implementation skeleton — `apps/web/src/routes/register.tsx` (binding for shape)

```tsx
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api } from "@/lib/api";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import type { LoginResponse } from "@/lib/api-types";

interface RegisterSearch { token?: string }

type FullPageError = "token_missing" | "token_invalid" | "token_consumed";

function Register() {
  const { t } = useTranslation();
  const search = useSearch({ from: "/register" });
  const navigate = useNavigate();
  const qc = useQueryClient();
  const emailId = useId();
  const passwordId = useId();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [fullPageError, setFullPageError] = useState<FullPageError | null>(
    search.token ? null : "token_missing"
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!search.token) return;
    setEmailError(null);
    setPasswordError(null);
    setPending(true);
    try {
      await api<LoginResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ token: search.token, email, password }),
      });
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      await navigate({ to: "/catalog" });
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : null;
      const detail = ((apiErr?.body as { detail?: string }) ?? {}).detail ?? "";
      if (apiErr?.status === 404) setFullPageError("token_invalid");
      else if (apiErr?.status === 410) setFullPageError("token_consumed");
      else if (apiErr?.status === 409) setEmailError(t("auth.register.error.email_taken"));
      else if (apiErr?.status === 422) setPasswordError(detail);
      else setPasswordError(t("auth.register.error.unexpected"));
      setPending(false);
    }
  }

  if (fullPageError) {
    return (
      <div className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4 text-center">
        <h1 className="text-xl font-semibold">{t("auth.register.title")}</h1>
        <p className="text-destructive" role="alert">
          {t(`auth.register.error.${fullPageError}`)}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
      <h1 className="text-xl font-semibold">{t("auth.register.title")}</h1>
      <div className="grid gap-1.5">
        <label htmlFor={emailId} className="text-sm font-medium">{t("auth.email")}</label>
        <Input id={emailId} name="email" type="email" autoComplete="email"
          required value={email} onChange={(e) => setEmail(e.target.value)}
          disabled={pending} />
        {emailError && <p className="text-sm text-destructive" role="alert">{emailError}</p>}
      </div>
      <div className="grid gap-1.5">
        <label htmlFor={passwordId} className="text-sm font-medium">{t("auth.password")}</label>
        <Input id={passwordId} name="password" type="password" autoComplete="new-password"
          required value={password} onChange={(e) => setPassword(e.target.value)}
          disabled={pending} />
        {passwordError && <p className="text-sm text-destructive" role="alert">{passwordError}</p>}
      </div>
      <Button type="submit" disabled={pending}>
        {pending ? t("auth.register.signing_up") : t("auth.register.title")}
      </Button>
    </form>
  );
}

export const Route = createFileRoute("/register")({
  component: Register,
  validateSearch: (raw: Record<string, unknown>): RegisterSearch =>
    typeof raw.token === "string" && raw.token.length > 0 ? { token: raw.token } : {},
});
```

### Implementation skeleton — `apps/web/tests/visual/register.spec.ts` (binding for shape)

```ts
import type { Page, Route } from "@playwright/test";
import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

const VALID_TOKEN = "test-token-43-chars-AAAAAAAAAAAAAAAAAAAA";

async function stubRegister(page: Page, status: number, detail: string) {
  await page.route("**/api/auth/register", (route: Route) =>
    route.fulfill({
      status, contentType: "application/json", body: JSON.stringify({ detail }),
    }),
  );
}

test("renders register form with token in URL", async ({ page }) => {
  await page.goto(`/register?token=${VALID_TOKEN}`);
  await waitForReady(page);
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await expect(page.getByLabel(/password|hasło/i)).toBeVisible();
  await expect(page).toHaveScreenshot("register-form-with-token.png");
});

// ... five more specs per AC-6 list
```

### Token-state diagnosis algorithm (binding precedence)

The four cases enumerated in AC-2 are resolved by this exact sequence in `_diagnose_inactive_token()`:

| Step | Check | Result |
|------|-------|--------|
| 1 | `await service.validate_active(token)` returns `ActiveInvite` | proceed to password validation; route continues |
| 2 | `await service.validate_active(token)` returns `None` AND DB row absent (`hash_token(token)` not in `invite_tokens`) | **404 `token_invalid`** |
| 3 | DB row exists AND `revoked_at IS NOT NULL` | **410 `token_consumed`** |
| 4 | DB row exists AND `used_at IS NOT NULL` | **410 `token_consumed`** |
| 5 | DB row exists AND no resolution columns set AND `generated_at + ttl_seconds <= now` (expired-naturally) | **404 `token_invalid`** |

Step 5 = step 2's behaviour for the Redis-expired case. Both map to 404 because from the consumer's perspective an expired token is indistinguishable from a never-existed one — the operator-side admin panel (Story 8.6) is where expired-vs-never-existed gets disambiguated, not the consumer-side register flow.

### Password validation order (binding precedence)

```
1. if len(password) < 12 → 422 "password must be at least 12 characters"   (cheaper check, more actionable UX)
2. elif zxcvbn.zxcvbn(password)["score"] < 3 → 422 "password is too predictable; choose a stronger one"
```

Length first because:
- Cheaper (no zxcvbn allocation)
- More actionable UX hint (user immediately knows to add chars)
- Bounds zxcvbn allocations to ≥12-char strings (zxcvbn cost is roughly linear in length; this caps the worst case)

The two failure messages in the HTTP body are deliberately differentiated so the UI can surface them inline below the password input without needing extra branching logic — just `setPasswordError(response.body.detail)` (see register.tsx skeleton line `setPasswordError(detail)`).

### display_name derivation

`display_name = payload.email.split("@", 1)[0]` is the binding rule. Rationale:
- The User model requires `display_name` (no default) and the register form per FR5-REGISTER-2 captures only email + password.
- Email local-parts are typically the user's name or handle anyway (`john.doe@example.com` → `"john.doe"`).
- Storing the local-part avoids the alternative — requiring a third form field — which violates the FR5-REGISTER-2 contract.
- The user can update their display_name in the settings UI later (out of scope for this story; covered by a future Init 5 settings expansion).

### Router registration order (binding contract for `apps/api/app/router.py`)

Final state after this story's edit:

```python
from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.invite.admin_router import router as invite_admin_router
from app.modules.invite.router import router as invite_public_router  # NEW Story 6.4
from app.modules.share.admin_router import router as share_admin_router
from app.modules.share.router import router as share_router
from app.modules.sot.admin_router import router as sot_admin_router
from app.modules.sot.router import router as sot_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(invite_public_router)  # NEW Story 6.4 — keeps /api/auth/* contiguous
api_router.include_router(invite_admin_router)
api_router.include_router(sot_admin_router)
api_router.include_router(admin_router)
api_router.include_router(share_admin_router)
api_router.include_router(share_router)
api_router.include_router(sot_router)
```

Both insertions are alphabetical-by-module-path AND keep `/api/auth/*` routes contiguous in the registration list (FastAPI's route matching is first-match; the new route's path `/api/auth/register` doesn't overlap any existing route — `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me`, etc. — so ordering is cosmetic, but the binding convention of "contiguous prefixes" stays clean).

### schemas.py vs admin_schemas.py rationale

Story 6.3 created `apps/api/app/modules/invite/admin_schemas.py` for admin-router schemas. This story creates `apps/api/app/modules/invite/schemas.py` (no `register_` prefix) for the PUBLIC-router schemas because:
- The public surface is small (one schema — `RegisterRequest`) and unlikely to grow beyond a handful of public-side schemas in Initiative 5 (future Story 6.6 rate-limit-middleware doesn't add Pydantic schemas; it operates on the request layer).
- The Init 0 precedent `apps/api/app/modules/share/models.py` mixes SQLModel + Pydantic in a single file for the share module. The invite module split is cleaner: `models.py` (SQLModel only), `schemas.py` (public Pydantic), `admin_schemas.py` (admin Pydantic).
- The `__init__.py` re-exports both `RegisterRequest` (from `.schemas`) AND the admin schemas (from `.admin_schemas`) so callers do `from app.modules.invite import RegisterRequest` cleanly.

Alternative considered: name the file `register_schemas.py` for symmetry with `admin_schemas.py`. Rejected because the symmetry isn't useful — `admin_schemas.py` is admin-router-specific, while `schemas.py` would be the public-router file. If a future story adds a second public schema, it lands in `schemas.py` alongside `RegisterRequest`; if it's a different concern entirely, a third file is justified.

### zxcvbn library selection

The Python package name is `zxcvbn` (PyPI), not `py-zxcvbn`. The package provides `zxcvbn.zxcvbn(password) -> dict` with the canonical fields `score` (0-4), `feedback`, `crack_times_*`, etc. The score is what FR5-REGISTER-2 references.

API call shape (binding):
```python
import zxcvbn
result = zxcvbn.zxcvbn("correct horse battery staple")
score = result["score"]  # 4 for this input
```

Version pin: `zxcvbn>=4.4.28`. The library has been stable for years (no breaking changes since 4.0); the `>=4.4.28` lower bound matches the current PyPI release as of 2026-05-19.

Alternative considered: `zxcvbn-python` (a different package name on PyPI). Rejected because `zxcvbn` is the canonical port maintained by the original author; `zxcvbn-python` is a less-maintained fork.

Frontend zxcvbn (`@zxcvbn-ts/core` on npm) is NOT added by this story. The strength check is server-side only per the epic. The UI just surfaces the 422 response body's `detail` string inline — no client-side scoring needed. Future UX iteration (strength meter while typing) is out of scope.

### i18n keys to add

```json
// apps/web/src/locales/en.json — 6 new keys
"auth.register.title": "Create account",
"auth.register.signing_up": "Creating account…",
"auth.register.error.token_invalid": "This invite link is invalid or has expired. Ask the administrator for a fresh invite.",
"auth.register.error.token_consumed": "This invite has already been used or was revoked. Ask the administrator for a fresh invite.",
"auth.register.error.token_missing": "This page requires an invite link. Ask the administrator for one.",
"auth.register.error.email_taken": "An account with this email already exists. Sign in instead.",
"auth.register.error.unexpected": "Could not create your account. Try again in a moment.",
```

```json
// apps/web/src/locales/pl.json — 6 new keys (7 with .unexpected fallback)
"auth.register.title": "Utwórz konto",
"auth.register.signing_up": "Tworzenie konta…",
"auth.register.error.token_invalid": "To zaproszenie jest nieprawidłowe lub wygasło. Poproś administratora o nowe.",
"auth.register.error.token_consumed": "To zaproszenie zostało już użyte lub unieważnione. Poproś administratora o nowe.",
"auth.register.error.token_missing": "Ta strona wymaga linku z zaproszeniem. Poproś administratora.",
"auth.register.error.email_taken": "Konto z tym adresem e-mail już istnieje. Zaloguj się zamiast tego.",
"auth.register.error.unexpected": "Nie udało się utworzyć konta. Spróbuj ponownie za chwilę.",
```

Total: 6 named keys + 1 fallback = 7 keys per locale. Insert sorted in the existing flat-key dot-notation file structure.

### helpers.ts changes might be needed

The visual-regression suite's `apps/web/tests/visual/helpers.ts` has a `waitForReady(page)` helper used by every spec. If the existing helper assumes `/api/auth/me` resolves to 200 (because every other spec stubs an authenticated user), the register spec — which is PUBLIC and renders without auth — may time out on the wait.

The fix path:
- Inspect `waitForReady()` in helpers.ts (Dev Agent: read it during T6.1).
- If it waits for an AuthGate to clear (e.g. `page.waitForFunction(() => !document.querySelector('[data-loading]'))`), it'll work for `/register` too since AuthGate is not applied there — the page renders synchronously.
- If it waits for a specific authenticated element (e.g. the catalog rail) to be visible, it'll time out on `/register`. In that case, add an optional `{ skipAuthGate?: boolean }` parameter that short-circuits the wait when truthy. Use it in the register spec.
- Document the change in Dev Agent Record + File List if the helper is modified.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.4]
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-REGISTER-1] — never-existed token → 404 + audit
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-REGISTER-2] — zxcvbn ≥3 + length ≥12 + 422 with failing rule
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-REGISTER-3] — cookie pair + audit
- [Source: _bmad-output/planning-artifacts/prd.md#FR5-AUDIT-1] — 16 audit actions; this story emits 3
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-A] — dual-backed storage
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-B] — token shape + hygiene
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision-C] — cookie issuance reuses Init 0
- [Source: apps/api/app/modules/auth/router.py:51-104] — login() reference shape (cookie + audit pattern)
- [Source: apps/api/app/modules/invite/service.py:162-206] — consume() contract used by this story
- [Source: apps/api/app/modules/invite/admin_router.py] — Story 6.3 _service() factory + audit pattern
- [Source: apps/api/app/core/audit.py:28-44] — KNOWN_ENTITY_TYPES (no changes needed)
- [Source: apps/api/app/core/auth/cookies.py:41-43] — set_session_cookies() helper
- [Source: apps/api/app/core/auth/refresh.py:47-76] — new_refresh_row() helper
- [Source: apps/web/src/routes/login.tsx] — sibling auth route shape for parity
- [Source: apps/web/tests/visual/_test.ts] — shared Playwright fixture pattern
- [Source: _bmad-output/implementation-artifacts/6-3-admin-invite-endpoints-generate-list-revoke.md] — Story 6.3 conventions

### Previous story intelligence (Story 6.3 — Sesja N close-out 2026-05-19)

**What landed:** Three admin endpoints (`POST /api/admin/invites` generate, `GET /api/admin/invites` list, `POST /api/admin/invites/{id}/revoke` revoke), all gated by `current_admin`, emit `auth.invite.generated` + `auth.invite.revoked` audit. Shipped in commit `278a3c5` + fix-up `2cc0b7c`. 484 backend tests pass. Files: `apps/api/app/modules/invite/admin_router.py` (~190 LOC), `admin_schemas.py` (~100 LOC), `test_invite_admin.py` (32 tests). One Codex review finding addressed: OpenAPI request contract narrowed from `UserRole` (which advertised the `agent` value the route would reject) to a `Literal["member", "admin"]` string-literal — same fix pattern applies HERE for `RegisterRequest` if any field surfaces an enum that admits values the route would reject (it doesn't — `RegisterRequest` fields are `token: str`, `email: EmailStr`, `password: str`; no enums leak through).

**Patterns to reuse:**
- The `_service(request)` factory pattern (admin_router.py:25-26) — copy verbatim.
- The fakeredis fixture shape (test_invite_admin.py:34-65) — copy verbatim, drop the admin_token + admin_uuid yield since the register tests are anonymous.
- The `_clear_invite_and_audit_tables` autouse fixture (test_invite_admin.py:69-79) — copy verbatim, plus add `User` to the table-clear set so test isolation extends to the user table this story creates rows in.
- The audit assertion helpers (`_audit_rows(action)` at test_invite_admin.py end) — copy verbatim.
- The `summary=...` + `description=...` per @router.post decorator (Story 6.3 fix added these to satisfy the OpenAPI surface gate from Story 4.3) — apply HERE on the new register endpoint.

**Anti-patterns to avoid:**
- DO NOT call `record_event()` inside `InviteService.consume()` — the service is caller-owned for audit per the Story 6.2 contract. The router (THIS story's `register()`) emits all three audit actions.
- DO NOT introduce a new audit action name for `weak_password` or `email_taken` — these are REASONS within the existing `auth.register.fail` action. Don't drift the FR5-AUDIT-1 enumeration.
- DO NOT use a custom error envelope like `{"error": {"code": "weak_password", "message": "..."}}` — keep the FastAPI default `{"detail": "<reason>"}` shape used by every route in the repo.
- DO NOT log the password value in any form, even at DEBUG level. The `TokenRedactionFilter` from Story 6.1 is defense-in-depth, not absolution.
- DO NOT add a "password_strength" field to the response (e.g. echoing the zxcvbn score back to the user). The response body for failures stays as `{"detail": "<message>"}`; the UI surfaces that string inline. Score-echoing leaks signal about the password.

### Git intelligence

Recent commits (`git log --oneline -10`):
```
2cc0b7c fix(api): Story 6.3 codex fix-up — narrow OpenAPI request contract
278a3c5 feat(api): admin invite endpoints generate/list/revoke (Story 6.3)
82ef441 fix(api): Story 6.2 codex review fix-up — atomic revoke (CAS predicate)
8944669 feat(api): invite service dual-backed write/read/revoke/consume (Story 6.2)
4ed620d fix(api): Story 6.1 codex review fix-up (logging redaction + init_schema)
```

The commit-message pattern is `feat(api): <description> (Story 6.X)` for the dev-story commit + `fix(api): Story 6.X codex fix-up — <description>` for any Codex review fix-up. Story 6.4's dev-story commit should follow `feat(api): public invite-token register endpoint + /register UI (Story 6.4)`. The visual-baseline commit MAY be folded into the same commit (per Story 5.13 hook) OR live in a follow-up `chore: add /register visual baseline (Story 6.4)` — Dev Agent's call based on staging hygiene.

### Latest technical specifics

- **FastAPI 0.115+**: `status_code=status.HTTP_201_CREATED` on `@router.post()` decorator is the binding form (matches Story 6.3 `POST /api/admin/invites` shape). Pydantic 2.9's `EmailStr` is the email-validation type; requires `email-validator>=2.2` (already in pyproject.toml).
- **zxcvbn 4.4.28+**: Stateless function call `zxcvbn.zxcvbn(password)` returns a dict; `["score"]` is 0-4. No global state, no thread-safety concerns.
- **Pydantic 2.9 schemas**: `Field(min_length=43, max_length=43)` for the token field is a tight bound matching `secrets.token_urlsafe(32)` output exactly. Tighter than the prior implementation freedom in Story 6.3 (`token: str` with no length bound on the cleartext field — but Story 6.3 returns the token, doesn't receive it; this story's RECEIVING a token, so bounded validation is the right call).
- **TanStack Router 1.84+ file-route conventions**: `createFileRoute("/register")` auto-registers via the `@tanstack/router-vite-plugin` regeneration of `routeTree.gen.ts`. The route MUST be a default-exported function via the `Route` named export per the existing convention (`routes/login.tsx:85-92`).

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) via bmad-dev-story skill — Sesja P, 2026-05-19.

### Debug Log References

- **Event-loop binding for fakeredis** — async test bodies hit `RuntimeError: bound to a different event loop` because pytest-asyncio's loop and TestClient's anyio loop are different. Resolved by converting tests to sync `def` and routing every service / Redis call through `c.portal.call(_do)` where `_do` is a local async closure (Base UI's `BlockingPortal.call` does not accept kwargs, so closures are required). Mirrors Story 6.3 fixture note that uses the same workaround for `validate_active()` in the revoke test.
- **`created_at` tz comparison** — SQLite re-read of a `default_factory=_now_utc` timestamp can come back as a naive datetime under SQLModel ORM. The happy-path assertion now coerces `tzinfo=UTC` when missing so `before <= created_at <= after` stays sound under both naive- and aware-return modes.
- **AC-3 hygiene assertion** — `"password" not in audit.after_json` matched on the substring inside the `weak_password` REASON string. Tightened to `"password" not in payload` (dict key check) to test the intent: no `password` field in the audit payload.
- **Visual-suite click target** — Playwright's `getByRole("button").first()` resolved to the theme-toggle button in the banner (rendered first in the `AppShell` chrome), not the form's submit button. Fixed by selecting via `getByRole("button", { name: /utwórz konto|create account/i })`. `BTN_CLICK fired` and `FORM_SUBMIT fired` confirmed via `page.evaluate` instrumentation before tightening the locator.
- **routeTree.gen.ts regeneration** — Vite plugin only regenerates on startup. Ran `timeout 12 npm run dev` to let the plugin observe `routes/register.tsx`; verified the generated file gained the `/register` entry (`grep "RegisterRouteImport" routeTree.gen.ts`).

### Completion Notes List

- All 8 ACs satisfied; all 7 tasks (T1–T7) + 41 subtasks marked complete.
- Backend: 507 pytest passed (baseline 484 + 23 new in `test_invite_register.py`). The 23 tests cover AC-1 happy path × 5, AC-2 token diagnosis × 5, AC-3 password × 5, AC-4 email collision × 3, plus 4 schema-/CSRF-layer rejection cases and 1 display-name-derivation assertion (the spec's "22+ named tests" floor; some AC-7 entries collapsed into single tests when the assertion set fully overlapped — e.g., `test_register_emits_three_audit_rows_no_cleartext_token` covers both AC-1 audit-shape AND AC-3 hygiene).
- OpenAPI smoke gate: `POST /api/auth/register` advertised with `tags=["auth", "invite"]`, summary + description per Story 6.3 convention.
- Frontend: 326 vitest passed (incl. 8 new `register.test.tsx` cases); 188 Playwright visual passed (164 baseline + 24 new `register.spec.ts` × 4 projects). Lint + typecheck clean.
- `infra/scripts/check-all.sh` from repo root: 10/10 stages green.
- Race-lost compensation path (TOCTOU between `validate_active()` and `service.consume()`) is implemented per Dev Notes skeleton but not unit-tested directly — exercising it would require injecting a between-step state mutation, which is out of scope here. The atomic predicate inside `InviteService.consume()` is already covered by Story 6.2's tests; the route just wraps the InviteConsumed catch with `session.delete(user)` + 410.
- No drift from spec skeleton: response shape, audit-action names, fail-reason vocabulary, cookie helpers, and router prefix all bind to the spec. `_diagnose_inactive_token` precedence matches the Dev Notes table exactly.
- `helpers.ts` (`waitForReady`) needed no changes — it only waits on `networkidle` + animation-disable; works for `/register` without an authenticated `me` stub.

### File List

NEW:
- `apps/api/app/modules/invite/router.py`
- `apps/api/app/modules/invite/schemas.py`
- `apps/api/tests/test_invite_register.py`
- `apps/web/src/routes/register.tsx`
- `apps/web/src/routes/register.test.tsx`
- `apps/web/tests/visual/register.spec.ts`
- `apps/web/tests/visual/__snapshots__/register.spec.ts/` (24 PNG baselines — 6 specs × 4 projects)

UPDATED:
- `apps/api/pyproject.toml` (add `zxcvbn>=4.4.28`)
- `apps/api/app/modules/invite/__init__.py` (re-export `RegisterRequest`)
- `apps/api/app/router.py` (mount `invite_public_router`)
- `apps/web/src/locales/en.json` (7 new `auth.register.*` keys)
- `apps/web/src/locales/pl.json` (7 new `auth.register.*` keys)
- `apps/web/src/routeTree.gen.ts` (auto-regenerated — `/register` route added)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (status flip + Sesja P note)
- `_bmad-output/implementation-artifacts/6-4-public-register-endpoint-and-ui.md` (this story file: Status → review, Tasks/Subtasks [x], Dev Agent Record, Change Log)

### Change Log

- 2026-05-19 (Sesja P) — Story 6.4 implemented end-to-end. `POST /api/auth/register` ships with full token-state diagnosis, zxcvbn + length password gate, email-uniqueness guard, race-lost compensation, three audit emissions (`auth.invite.used` + `auth.register.success` + `auth.register.fail`), and cookie-pair issuance via existing Init 0 helpers. `/register` UI mirrors the login-route shape with token-state-aware error surfaces (inline 422/409, full-page 404/410, missing-token). 24 visual baselines + 23 backend tests + 8 vitest cases. All 10 stages of `infra/scripts/check-all.sh` green.
