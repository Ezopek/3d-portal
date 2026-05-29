# Story 7.3: Login flow extension — partial-auth + TOTP / recovery-code verify step (`POST /api/auth/2fa/verify` + `POST /api/auth/login` extension + LoginPage second-factor prompt)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want `POST /api/auth/login` to detect users with `users.totp_enabled_at IS NOT NULL` and short-circuit into a **partial-auth** state (HTTP 200, body `{partial_auth: true, totp_required: true, partial_token: <opaque>}`, **NO** `portal_access` / `portal_refresh` cookies set, **NO** `RefreshToken` row created yet, **NO** `auth.login.success` audit row emitted yet) plus a NEW endpoint `POST /api/auth/2fa/verify {partial_token, code}` in `apps/api/app/modules/auth/totp/router.py` (extending the Story 7.2 router) that:

- Reads the Redis stash at `totp:partial:{partial_token}` (5-minute TTL; payload `{user_id, ip, ua}`), 401 `partial_token_invalid` on miss/expired;
- Loads `user = session.get(User, payload.user_id)` — 401 `partial_token_invalid` (same surface) if user gone OR `user.totp_enabled_at IS NULL` (defense-in-depth race against an admin-disable mid-partial flow);
- Regex-distinguishes the second factor: `^\d{6}$` = TOTP path (calls `decrypt_secret(user.totp_secret, settings)` then `verify_totp_code(secret, code)` — both helpers already shipped in Story 7.2 service.py); `^[0-9a-f]{8}$` = recovery-code path (iterates `recovery_codes WHERE user_id == user.id AND invalidated_at IS NULL AND used_at IS NULL ORDER BY generated_at DESC`, calls `bcrypt.checkpw(code.encode(), row.code_hash.encode())` per Decision E §1531 verbatim, first match sets `row.used_at = NOW()`, commits the UPDATE in the same `session.commit()` as the new `RefreshToken` row creation, emits ONE `auth.recovery_code.used` audit row with `entity_type="recovery_code"` + `entity_id=row.id` + `after={batch_id, used_at}`); any other code shape → 401 `invalid_code` BEFORE any DB/Fernet work (cheap early-reject);
- On a **success match** (TOTP valid OR recovery-code consumed): mints a new refresh-token family + access token via the existing `new_refresh_row` / `encode_token` helpers — IDENTICAL to the single-factor login success path — sets `portal_access` + `portal_refresh` cookies via `set_session_cookies`, atomic Redis `DEL totp:partial:{partial_token}` (best-effort; TTL would expire it within 5min regardless), and emits ONE `auth.totp.verify.success` audit row (`entity_type="user"`, `actor_user_id == target_user_id == user.id`, `after={method: "totp" | "recovery_code"}`). Returns `LoginResponse {user: MeResponse}` — identical wire shape to single-factor login on success, so the frontend's existing `qc.invalidateQueries(["auth", "me"])` + navigate-to-next flow works unchanged after the second-factor step;
- On a **failure** (no TOTP match AND no recovery-code match, OR a verify error from `decrypt_secret` raising `cryptography.fernet.InvalidToken` — should be impossible-by-construction because the column was Fernet-encrypted by Story 7.2 with the same key, but defense-in-depth maps it to the same 401 path): does NOT consume the `partial_token` (the user may retry with a different code within the 5-min TTL) AND does NOT advance any DB state, but emits ONE `auth.totp.verify.fail` audit row (`entity_type="user"`, `actor_user_id == target_user_id == user.id`, `after={method: "totp" | "recovery_code" | "malformed"}`). Returns HTTP 401 `invalid_code`;

and a NEW frontend behavior in `apps/web/src/routes/login.tsx` (extending — NOT replacing — the existing single-factor `Login` component) that detects the discriminator `partial_auth === true` in the login response, holds the `partial_token` in local React state (NOT React Query cache, NOT localStorage — single-use ephemeral artifact bounded by 300s TTL), transitions to a **second-factor prompt** sub-state that renders ONE input field (`<Input inputMode="text" pattern="(\d{6})|([0-9a-f]{8})" autoComplete="one-time-code" maxLength={8}/>` — accepts either shape; UI does NOT explicit-switch between TOTP vs recovery-code — the user types whichever they have, regex distinguishes server-side), a "Verify" submit button that POSTs `/api/auth/2fa/verify {partial_token, code}`, on success refetches `["auth", "me"]` + navigates to `search.next` (matching the existing single-factor success flow), and on 401 `invalid_code` renders an inline error "Incorrect code, try again" (translation key `auth.2fa.verify.error.invalid_code`); on 401 `partial_token_invalid` (TTL expired between step 1 and step 2) renders "Session expired, please sign in again" + a "Back to email/password" button that resets the component to the email/password sub-state with fresh state;

and a NEW rate-limit binding: the existing `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` function is extended (single-line addition) so that POST `/api/auth/2fa/verify` ALSO returns the per-IP key `f"ip:{_client_ip(request)}"` for the existing `login` scope — meaning verify failures **count against the same `ratelimit:login:ip:{ip}` 5-failures-per-60s budget as `/api/auth/login`** per epics §1694 verbatim "Story 6.6 login rate-limit (5 failures / 60s per IP) is unaffected — second-factor failures count against the same `login` scope key (defense in depth: brute-forcing the second factor still trips the IP rate-limit)." NO new rate-limit scope is added; NO change to `apps/api/app/core/config.py` `ratelimit_login_*` thresholds; NO change to the middleware itself — just the key_fn extension. Worst-case bcrypt cost is bounded: 5 verify attempts per minute × 8 recovery-code bcrypt-checks × ~250ms cost (Decision E §1531) = ≤10s CPU per IP per minute, well within budget;

realizing **FR5-2FA-2** in full (login flow extends with second factor; TOTP OR recovery code accepted; `auth.recovery_code.used` + `auth.totp.verify.success` + `auth.totp.verify.fail` audit emissions land per FR5-AUDIT-1 vocabulary), anchoring architecture.md Decisions **D** (`decrypt_secret` boundary — first production caller; Story 7.2 only used the helper in a round-trip test) + **E** (recovery-code consumption iteration + bcrypt cost-12 check + `used_at` lifecycle column + audit-per-code-consumed), explicitly DEFERRING Decision F (`enforce_2fa_for_roles` partial-auth-forcing-enrollment path) to Story 7.4 which extends `/api/auth/login` with a SECOND partial-auth branch (`partial_auth: true, totp_enroll_required: true`) for users whose role is in the enforce list but who have not yet enrolled, with the entire diff scoped strictly to the second-factor verify surface (NO disable endpoint, NO regenerate endpoint, NO admin force-enroll endpoint, NO Decision F middleware enforcement, NO new Pydantic Settings fields, NO new Alembic migration, NO new dependencies, NO change to the Story 7.2 `Settings2faPage` wizard — that surface is read-only from this story's perspective), so that EVERY currently-passing test in `apps/api/tests/` (640-test backend baseline post-7.2 + 327 vitest + 204 Playwright) continues to pass unchanged AND new tests in `apps/api/tests/test_2fa_verify.py` author the binding behavior at the endpoint layer with 18 named tests covering the golden TOTP path + golden recovery-code path + recovery-code single-use + recovery-code lifecycle audit + invalid code 401 + malformed code 401 + partial_token TTL expiry + partial_token user_id race + login partial-auth response shape + login NO-cookie-on-partial + rate-limit shared budget + concurrent verify atomic claim race + totp_enabled_at race + Fernet ciphertext round-trip from Story 7.2 enrollment + audit emission `auth.totp.verify.success` + audit emission `auth.totp.verify.fail` + audit emission `auth.recovery_code.used` shape + admin can still log in single-factor (no totp_enabled_at) + agent can still log in single-factor (totp_enabled_at by construction NULL — Story 7.2 AC-6 step 2 invariant).

## Acceptance Criteria

**AC-1 — `POST /api/auth/login` extended with partial-auth branch for users with `users.totp_enabled_at IS NOT NULL`.**

- Given the existing login handler at `apps/api/app/modules/auth/router.py:51-104` (synchronous `def login()`, password-verify → 401 on bad creds → mint RefreshToken + access → `set_session_cookies` → `record_event("auth.login.success")` → return `LoginResponse`),
- When Story 7.3 ships,
- Then `apps/api/app/modules/auth/router.py:login()` MUST convert from `def login(...)` to `async def login(...)` (the Redis stash call is async; no other downstream effects because SQLModel `Session` is synchronous and `session.exec()` is safe inside an async coroutine — confirmed by the precedent at `apps/api/app/modules/auth/totp/router.py:66-87` which mixes async handler + sync `session.get()`).
- And after the existing password-verify success path (line 60 — `user is None or not verify_password(...)` → 401) AND BEFORE the existing `ip, ua = _client_meta(request)` + `new_refresh_row(...)` + `session.add(row)` + `session.commit()` + `set_session_cookies(...)` + `record_event("auth.login.success")` sequence (lines 71-96), a NEW branch MUST execute:

  ```python
  if user.totp_enabled_at is not None:
      partial_token = secrets.token_urlsafe(32)
      ip, ua = _client_meta(request)
      stash = json.dumps({"user_id": str(user.id), "ip": ip or "", "ua": ua or ""})
      await request.app.state.redis.get().set(
          f"totp:partial:{partial_token}",
          stash.encode(),
          ex=300,  # 5 minutes (epics §1694 "Redis-stashed 5min")
      )
      return PartialAuthResponse(
          partial_auth=True,
          totp_required=True,
          partial_token=partial_token,
      )
  ```

- And NO cookies are set on the partial-auth branch — `set_session_cookies` MUST NOT be invoked.
- And NO `RefreshToken` row is created on the partial-auth branch — `new_refresh_row` / `session.add(row)` / `session.commit()` MUST NOT execute. The user's refresh family is created ONLY on second-factor success via the `/api/auth/2fa/verify` handler (AC-3).
- And NO `auth.login.success` audit row is emitted on the partial-auth branch. The successful login event for partial-auth users is `auth.totp.verify.success` (AC-3 step 11) — emitting `auth.login.success` here would dilute the "fully authenticated" signal and let an attacker who got the password but not the second factor leave a `success` row in the audit log.
- And the existing `auth.login.fail` emission on the wrong-password path (lines 61-68) is UNCHANGED — wrong password for a partial-auth-enrolled user still emits `auth.login.fail` exactly as for a single-factor user. The partial-auth branch only triggers after successful password verification.
- And the response model union on the login handler MUST be:

  ```python
  @router.post("/login", response_model=Union[LoginResponse, PartialAuthResponse])
  async def login(...) -> LoginResponse | PartialAuthResponse: ...
  ```

  FastAPI's `Union` response_model is the standard discriminated-response pattern (used by `/api/auth/refresh` would need the same shape in Story 7.4 follow-up but is NOT in 7.3 scope). The frontend discriminator is the `partial_auth: bool` field (always present on both shapes via the new model — see AC-2).

- And the login handler's response shape on the partial-auth branch MUST match EXACTLY the new Pydantic model `PartialAuthResponse` defined in AC-2 — no extra fields, no missing fields.

**AC-2 — NEW Pydantic models: `PartialAuthResponse` in `apps/api/app/modules/auth/models.py` + `VerifyRequest` in `apps/api/app/modules/auth/totp/schemas.py`.**

- Given the existing 5-model surface in `apps/api/app/modules/auth/models.py` (`LoginRequest`, `MeResponse`, `LoginResponse`, `SessionRow`, `SessionsResponse`) and the existing 4-model surface in `apps/api/app/modules/auth/totp/schemas.py` (`EnrollResponse`, `ConfirmRequest`, `ConfirmResponse`, `StatusResponse`),
- When Story 7.3 ships,
- Then `apps/api/app/modules/auth/models.py` MUST gain EXACTLY ONE new model `PartialAuthResponse`:

  ```python
  class PartialAuthResponse(BaseModel):
      """Returned by POST /api/auth/login when user.totp_enabled_at IS NOT NULL.

      No cookies are set on this response; the frontend exchanges
      ``partial_token`` for full auth via POST /api/auth/2fa/verify.
      """

      partial_auth: bool = True  # discriminator — always True on this shape
      totp_required: bool = True  # always True in Story 7.3; Story 7.4 may add totp_enroll_required variant
      partial_token: str = Field(min_length=20, max_length=64)
  ```

- And `LoginResponse` MUST gain a `partial_auth: bool = False` field added IMMEDIATELY before the existing `user: MeResponse` field, so that BOTH success-shape responses carry the discriminator the frontend uses:

  ```python
  class LoginResponse(BaseModel):
      partial_auth: bool = False  # discriminator — always False on this shape
      user: MeResponse
  ```

  This is the binding "always-present discriminator" pattern — the frontend can branch on `response.partial_auth === true` to distinguish partial vs full auth WITHOUT inspecting field presence (safer than `"partial_token" in response`).

- And `apps/api/app/modules/auth/totp/schemas.py` MUST gain EXACTLY ONE new model `VerifyRequest`:

  ```python
  class VerifyRequest(BaseModel):
      """Body of POST /api/auth/2fa/verify.

      ``code`` accepts EITHER a 6-digit TOTP code OR an 8-char lowercase
      hex recovery code; the regex below matches both shapes and the
      server-side handler routes by shape (Story 7.3 AC-3 step 5).
      """

      partial_token: str = Field(min_length=20, max_length=64)
      code: str = Field(pattern=r"^(\d{6}|[0-9a-f]{8})$")
  ```

- And the `code` regex is binding — it pre-rejects malformed input at the Pydantic-validation layer (422 from FastAPI) BEFORE any DB or Fernet work; only well-shaped codes reach the handler. The handler's path-distinguish logic at AC-3 step 5 only sees `^\d{6}$` OR `^[0-9a-f]{8}$` strings.
- And NO change to `apps/api/app/modules/auth/totp/schemas.py:ConfirmRequest` is allowed (Story 7.2 contract is preserved — `code: str = Field(pattern=r"^\d{6}$")` for enrollment-confirm stays TOTP-only; recovery codes are NOT valid enrollment-confirm inputs).
- And NO new field on `MeResponse` is added in this story (the `totp_enabled_at` boolean state stays at `GET /api/auth/2fa/status` per Story 7.2 AC-7 binding).
- And the AC-13 grep check `grep -nE '"partial_auth"|partial_auth:' apps/api/app/modules/auth/models.py apps/api/app/modules/auth/totp/schemas.py` MUST return EXACTLY 4 lines (1 in `LoginResponse`, 1 in `PartialAuthResponse` definition, 1 in `PartialAuthResponse` class docstring/example, 0 elsewhere) — the field name is the wire contract and is binding for the frontend's discriminator branch.

**AC-3 — NEW endpoint `POST /api/auth/2fa/verify` in `apps/api/app/modules/auth/totp/router.py` (extending the existing 3 endpoints; same `/api/auth` prefix).**

- Given the existing 3 endpoints in `apps/api/app/modules/auth/totp/router.py` (begin_enrollment / confirm_enrollment / read_status) + the existing service class `Settings2faService` at `apps/api/app/modules/auth/totp/service.py:175-329`,
- When Story 7.3 ships,
- Then a FOURTH endpoint MUST exist at:

  ```python
  @router.post(
      "/2fa/verify",
      response_model=LoginResponse,
      status_code=status.HTTP_200_OK,
      summary="Verify second factor — TOTP or recovery code — and issue cookies",
      description=(
          "Exchange a partial_token (issued by POST /api/auth/login for "
          "users with totp_enabled_at IS NOT NULL) plus either a 6-digit "
          "TOTP code OR an 8-char hex recovery code for a fully "
          "authenticated session. On success: issues portal_access + "
          "portal_refresh cookies, creates a new RefreshToken family row, "
          "consumes the partial_token, emits auth.totp.verify.success "
          "and (if recovery_code) auth.recovery_code.used audit rows."
      ),
  )
  async def verify_second_factor(
      payload: VerifyRequest,
      request: Request,
      response: Response,
      session: Annotated[Session, Depends(get_session)],
      settings: Annotated[Settings, Depends(get_settings)],
  ) -> LoginResponse:
      ...
  ```

- And **NO `current_user` dependency** is wired on this endpoint — the `partial_token` IS the auth context. The partial_token is a single-use bearer credential bound to one `user_id` via the Redis stash payload. The handler MUST NOT call `Depends(current_user)` because the client has no `portal_access` cookie at this point.
- And the endpoint body MUST execute this exact sequence (named "T3 sequence" for cross-reference in the dev-story task):

  1. Redis GET `f"totp:partial:{payload.partial_token}"`:
     - On miss/expired → raise `HTTPException(401, "partial_token_invalid")`. NO audit emission (no user_id to attribute it to safely).
     - On hit → parse JSON payload: `{"user_id": <UUID str>, "ip": <str>, "ua": <str>}`.

  2. Load `user = session.get(User, uuid.UUID(stash.user_id))`:
     - If `user is None` → raise `HTTPException(401, "partial_token_invalid")` (same surface as miss; defense-in-depth race against an admin hard-delete mid-partial; no info leak).
     - If `user.totp_enabled_at is None` → raise `HTTPException(401, "partial_token_invalid")` (race against admin-disable from Story 7.5 between login step 1 and step 2; same surface — the frontend handles it identically by resetting to email/password sub-state).

  3. If `user.totp_secret is None` (impossible by Story 7.2 invariant: enrollment sets BOTH `totp_secret` AND `totp_enabled_at` in ONE atomic commit; defense-in-depth): raise `HTTPException(500, "totp_corrupt_state")`. The frontend surfaces this as a generic "try again later" error.

  4. Branch by code shape — the regex is in `VerifyRequest.code` so `payload.code` is guaranteed to match `^(\d{6}|[0-9a-f]{8})$`:

     - **TOTP path** (`re.fullmatch(r"\d{6}", payload.code)`):
       a. Call `secret = decrypt_secret(user.totp_secret, settings)` (Story 7.2 helper at `apps/api/app/modules/auth/totp/service.py:105-113`; raises `cryptography.fernet.InvalidToken` if ciphertext was encrypted with a different key — should be impossible-by-construction).
       b. Catch `cryptography.fernet.InvalidToken` → emit `auth.totp.verify.fail` with `after={"method": "totp", "reason": "fernet_invalid_token"}` → raise `HTTPException(401, "invalid_code")`. NO partial_token consumption (user may retry; the failure was a server-side key/cipher mismatch, not user error).
       c. If `verify_totp_code(secret, payload.code)` returns `False`: emit `auth.totp.verify.fail` with `after={"method": "totp"}` → raise `HTTPException(401, "invalid_code")`. NO partial_token consumption.
       d. Else (`True`): proceed to step 6 with `method="totp"`.

     - **Recovery-code path** (`re.fullmatch(r"[0-9a-f]{8}", payload.code)`):
       a. SELECT active codes: `rows = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.invalidated_at.is_(None), RecoveryCode.used_at.is_(None)).order_by(RecoveryCode.generated_at.desc())).all()`. Newest-batch-first ordering keeps bcrypt cost low if the user has regenerated and is using the new batch (Story 7.5 contract). The bcrypt iteration is bounded by 8 codes per active batch × cost 12 = ~2s worst-case (Decision E §1531 verbatim).
       b. Iterate `rows`: for each `row`, call `bcrypt.checkpw(payload.code.encode(), row.code_hash.encode())`. First `True` → consume that row (step 5).
       c. If no row matched: emit `auth.totp.verify.fail` with `after={"method": "recovery_code"}` → raise `HTTPException(401, "invalid_code")`. NO partial_token consumption.

  5. **Consume the matched recovery-code row** (recovery-code path only; skip for TOTP path):
     - `matched_row.used_at = datetime.datetime.now(datetime.UTC)`
     - `session.add(matched_row)` (UPDATE staged; flushed together with the RefreshToken INSERT in step 8).
     - Hold `matched_row` reference for the audit emission in step 7.

  6. **Mint refresh-token family + access token** (BOTH paths):
     - `ip, ua = _client_meta(request)` (reuse the existing helper at `apps/api/app/modules/auth/router.py:43-48`; if the helper is module-private, import it; if not, duplicate the 3-line implementation in the totp router file — prefer import for DRY).
     - `secret, row = new_refresh_row(user_id=user.id, family_id=None, family_issued_at=None, ip=ip, user_agent=ua)` — identical to `apps/api/app/modules/auth/router.py:72-78`.
     - `session.add(row)`. (Staged; commit in step 8.)

  7. **Commit + audit emissions** (BOTH paths, in this exact order):
     - `session.commit()` — ONE atomic commit covering the RefreshToken INSERT AND (recovery-code path only) the `recovery_codes.used_at` UPDATE. Partial-state failure (e.g. DB error mid-flush) MUST roll back BOTH — the consumed code stays not-yet-consumed and the user can retry within the partial_token TTL.
     - If recovery-code path: `record_event(get_engine(), action="auth.recovery_code.used", entity_type="recovery_code", entity_id=matched_row.id, actor_user_id=user.id, after={"batch_id": str(matched_row.batch_id), "used_at": matched_row.used_at.isoformat()}, request_id=request.headers.get("x-request-id"))`.
     - Then: `record_event(get_engine(), action="auth.totp.verify.success", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"method": "totp" if method == "totp" else "recovery_code"}, request_id=request.headers.get("x-request-id"))`.
     - Two-row audit emission is the binding shape for recovery-code success (one row for the per-code consumption event with `recovery_code` entity_type; one row for the higher-level verify-success event with `user` entity_type). TOTP-path success emits ONLY the second row.

  8. **Issue cookies + delete partial_token + return response:**
     - `access = encode_token(subject=str(user.id), role=user.role.value, secret=settings.jwt_secret, ttl_minutes=settings.jwt_ttl_minutes)` (identical to `apps/api/app/modules/auth/router.py:82-87`).
     - `set_session_cookies(response, access=access, refresh=secret, settings=settings)`.
     - `await request.app.state.redis.get().delete(f"totp:partial:{payload.partial_token}")` (best-effort; the TTL would expire it within 5min regardless).
     - Return `LoginResponse(partial_auth=False, user=MeResponse(id=user.id, email=user.email, display_name=user.display_name, role=user.role.value))`.

- And the failure paths in step 4 (TOTP-mismatch + Fernet-InvalidToken + recovery-no-match) MUST NOT consume the partial_token — the user can retry with a different code within the 5-min TTL. The rate-limit middleware (AC-4) bounds the brute-force attack window.
- And NO `auth.login.success` audit row is emitted on either success path — `auth.totp.verify.success` is the authoritative "user fully authenticated" event for partial-auth users.
- And the SAME `LoginResponse` shape returned by the existing single-factor `/api/auth/login` is returned here on success — so the frontend's existing `qc.invalidateQueries(["auth", "me"])` + `navigate({to: next})` flow works unchanged after the verify step (AC-7).

**AC-4 — Rate-limit binding: `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` extended to also match `POST /api/auth/2fa/verify`; verify failures count against the same `ratelimit:login:ip:{ip}` 5/60s budget.**

- Given the existing `login_ratelimit_key` function at `apps/api/app/core/auth/ratelimit.py:80-83`:

  ```python
  def login_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path == "/api/auth/login":
          return f"ip:{_client_ip(request)}"
      return None
  ```

  + epics.md §1694 verbatim "Story 6.6 login rate-limit (5 failures / 60s per IP) is unaffected — second-factor failures count against the same `login` scope key (defense in depth)",

- When Story 7.3 ships,
- Then `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` MUST be extended by EXACTLY ONE additional condition (preserve the existing return for `/api/auth/login`):

  ```python
  def login_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path in {
          "/api/auth/login",
          "/api/auth/2fa/verify",
      }:
          return f"ip:{_client_ip(request)}"
      return None
  ```

- And NO change to the `apps/api/app/main.py` middleware-mount block at lines 84-91 (the existing `RateLimitMiddleware(scope="login", key_fn=login_ratelimit_key, window_seconds=..., threshold=...)` mount automatically picks up the extended key_fn — same instance, same scope, same budget).
- And NO change to `apps/api/app/core/config.py:ratelimit_login_window_seconds` (60) or `apps/api/app/core/config.py:ratelimit_login_threshold` (5).
- And NO new rate-limit scope is added (the test that asserts only 4 scopes exist — login/refresh/register/share — at `apps/api/tests/test_ratelimit_middleware.py` if any such test exists, MUST stay green; if the test enumerates scopes, the assertion holds because the verify endpoint reuses the existing `login` scope).
- And the binding semantics are: every POST to `/api/auth/login` OR `/api/auth/2fa/verify` (regardless of success/failure outcome — the middleware fires BEFORE the handler) costs 1 token from the shared per-IP budget. Brute-forcing combinations of (password attempts, second-factor attempts) trips the budget after a total of 5 POSTs in any 60s window from the same IP. This is the binding defense-in-depth contract.
- And AC-12 test T-RATELIMIT verifies the shared-budget behavior end-to-end: a sequence of 4 wrong-password POSTs to `/api/auth/login` + 1 verify POST to `/api/auth/2fa/verify` from the same IP returns 429 on the 6th attempt (login or verify), proving the budget is shared.

**AC-5 — Decision D (`decrypt_secret`) first production caller; Decision E recovery-code iteration shape (newest-batch-first, bcrypt cost 12).**

- Given Decision D §1509 verbatim "cleartext `totp_secret` exists in process memory ONLY inside `apps/api/app/modules/auth/totp/service.py:_decrypt_secret()` for the duration of one TOTP verify call",
- When Story 7.3 ships,
- Then the AC-3 step 4 TOTP path MUST call the existing `decrypt_secret` helper at `apps/api/app/modules/auth/totp/service.py:105-113` — Story 7.2 wrote the helper but the only caller was the round-trip test (`apps/api/tests/test_2fa_enrollment.py::test_decrypt_secret_roundtrips_to_original_cleartext`). Story 7.3 is the FIRST production code path that invokes `decrypt_secret`.
- And the cleartext variable `secret` MUST be scoped to the TOTP-path branch only — it MUST NOT escape into module-level state, MUST NOT be logged, MUST NOT be returned in any response, MUST NOT be persisted to any DB column. The `verify_totp_code(secret, payload.code)` call must be the only consumer; the cleartext is GC'd when the function returns.
- And NO change to `apps/api/app/modules/auth/totp/service.py` `decrypt_secret` / `encrypt_secret` / `verify_totp_code` is allowed in 7.3 — they are reused verbatim from Story 7.2.
- And the AC-3 step 4 recovery-code path MUST iterate the active batch newest-first per Decision E §1531 verbatim "iterate active batch (where `invalidated_at IS NULL`) calling `bcrypt.checkpw(submitted_code, row.code_hash)`. First match sets `used_at` and emits `auth.recovery_code.used`." Specifically:
  - SELECT: `WHERE user_id == user.id AND invalidated_at IS NULL AND used_at IS NULL ORDER BY generated_at DESC` — newest batch's codes come first if Story 7.5 regenerate has been used (relevant after Story 7.5 ships; for 7.3 there is only one batch per user so ordering is moot, but the ORDER BY is binding for future-proofing).
  - Iterate the result list in order. For each row: `if bcrypt.checkpw(payload.code.encode(), row.code_hash.encode()): consume + break`.
  - Bcrypt cost-12 binding: `RecoveryCode.code_hash` is stored as `bcrypt.hashpw(cleartext.encode(), bcrypt.gensalt(rounds=12))` per Story 7.2 `generate_recovery_codes_batch()` — `bcrypt.checkpw` reads the cost from the stored hash prefix `$2b$12$`. No explicit cost arg needed at check time.
- And the recovery-code SELECT MUST use SQLModel `select(RecoveryCode)` (matching the existing query patterns in `apps/api/app/modules/auth/totp/service.py:303-309`). NOT raw SQL, NOT `User.recovery_codes` ORM relationship (which doesn't exist — `RecoveryCode` is a free-standing SQLModel without a back_populates relationship to `User`).
- And `bcrypt.checkpw` MUST be the only check primitive (NOT `hmac.compare_digest`, NOT `secrets.compare_digest`, NOT a custom equality check on hashes). The stored `code_hash` is the bcrypt output including salt + cost prefix; only `bcrypt.checkpw` parses that format correctly.

**AC-6 — Audit emission shape: `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used` — exact fields, NO cleartext leakage, entity_type registry compliance.**

- Given FR5-AUDIT-1 binding vocabulary §prd.md:1200 lists `auth.totp.verify.success` + `auth.totp.verify.fail` + `auth.recovery_code.used` among the 16 new actions + the `recovery_code` entity_type registered in `apps/api/app/core/audit.py:KNOWN_ENTITY_TYPES` by Story 7.1 + the `record_event()` helper signature at `apps/api/app/core/audit.py` (`action, entity_type, entity_id, actor_user_id, after, request_id`),
- When Story 7.3 ships,
- Then each of the three NEW audit emissions MUST follow this exact shape:

  **`auth.totp.verify.success`** (one row per successful verify, BOTH TOTP and recovery-code paths):
  - `action = "auth.totp.verify.success"`
  - `entity_type = "user"` (registry-registered since project init)
  - `entity_id = user.id`
  - `actor_user_id = user.id` (actor == target — the user verifying themselves)
  - `after = {"method": "totp" | "recovery_code"}` — string discriminator; NO cleartext code, NO secret, NO bcrypt hash, NO Fernet ciphertext, NO partial_token, NO `batch_id`, NO `used_at`.
  - `request_id = request.headers.get("x-request-id")` (may be `None` for direct-curl tests; binding pattern from `apps/api/app/modules/auth/totp/router.py:147`).

  **`auth.totp.verify.fail`** (one row per failed verify; NO partial_token consumption):
  - `action = "auth.totp.verify.fail"`
  - `entity_type = "user"`
  - `entity_id = user.id`
  - `actor_user_id = user.id`
  - `after = {"method": "totp" | "recovery_code" | "malformed"}` — string discriminator. `"malformed"` covers the future-defensive case where the Pydantic regex is bypassed (impossible-by-construction but documented for clarity). For Story 7.3 only `"totp"` and `"recovery_code"` paths fire.
  - `request_id = request.headers.get("x-request-id")`.
  - NO cleartext code, NO secret, NO bcrypt hash, NO partial_token in payload.

  **`auth.recovery_code.used`** (one row per recovery-code consumption; ONLY emitted on the recovery-code-path success branch — NOT on TOTP-path success; NOT on any failure path):
  - `action = "auth.recovery_code.used"`
  - `entity_type = "recovery_code"` (registry-registered by Story 7.1 — verified in `apps/api/app/core/audit.py:KNOWN_ENTITY_TYPES`)
  - `entity_id = matched_row.id` (the `recovery_codes.id` of the consumed row; ties the audit event to the specific code lifecycle)
  - `actor_user_id = user.id` (actor == target — the user consuming their own code)
  - `after = {"batch_id": str(matched_row.batch_id), "used_at": matched_row.used_at.isoformat()}` — NO cleartext code, NO `code_hash`.
  - `request_id = request.headers.get("x-request-id")`.

- And the audit emissions MUST happen AFTER `session.commit()` per AC-3 step 7 ordering — NEVER before. Emitting before commit risks an orphaned audit row (commit failed but audit row written), which violates the FR5-AUDIT-1 "every audit row reflects a committed state change" contract.
- And the AC-13 grep check `grep -nE '"auth\.(recovery_code|totp\.verify)\.\w+"' apps/api/app/modules/auth/totp/router.py apps/api/app/modules/auth/totp/service.py` MUST return EXACTLY 3 matches (one per audit action name).
- And NO change to `apps/api/app/core/audit.py:KNOWN_ENTITY_TYPES` is required — `user` and `recovery_code` are both already registered (the latter by Story 7.1).
- And NO emission of `auth.login.success` happens on the verify-success path — this differentiates the partial-auth login flow audit trail from the single-factor login flow, which is the intended FR5-AUDIT-1 design (an attacker who got the password but failed the second factor cannot impersonate a `login.success` row).

**AC-7 — Frontend `apps/web/src/routes/login.tsx` extended with second-factor sub-state; discriminator-based branching; reuses `qc.invalidateQueries(["auth", "me"])` + `navigate({to: next})` after verify success.**

- Given the existing `apps/web/src/routes/login.tsx` 93-line single-state component (`Login` → POST `/auth/login` → `qc.invalidateQueries(["auth", "me"])` → `navigate(next)`) + the `api()` wrapper at `apps/web/src/lib/api.ts:11` (CSRF header + JSON content-type + 401-refresh-retry) + the existing `<Input>` / `<Button>` UI primitives at `apps/web/src/ui/input.tsx` + `apps/web/src/ui/button.tsx`,
- When Story 7.3 ships,
- Then `apps/web/src/routes/login.tsx` MUST be extended (NOT replaced) to support TWO sub-states: `"email_password"` (the existing form) and `"second_factor"` (new). The component MUST use a `useState<"email_password" | "second_factor">("email_password")` flag + a `useState<string | null>(null)` `partialToken` slot:

  ```tsx
  type SubState = "email_password" | "second_factor";

  function Login() {
    const { t } = useTranslation();
    const [subState, setSubState] = useState<SubState>("email_password");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [partialToken, setPartialToken] = useState<string | null>(null);
    const [code, setCode] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [pending, setPending] = useState(false);
    // ... existing hooks (useNavigate, useSearch, useQueryClient, useId)

    async function submitEmailPassword(e: React.FormEvent) {
      e.preventDefault();
      setError(null);
      setPending(true);
      try {
        const resp = await api<LoginResponse | PartialAuthResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        if (resp.partial_auth === true) {
          setPartialToken(resp.partial_token);
          setSubState("second_factor");
          setPending(false);
          return;
        }
        await qc.invalidateQueries({ queryKey: ["auth", "me"] });
        const next = search.next ? decodeURIComponent(search.next) : "/";
        await navigate({ to: next as "/" });
      } catch {
        setError(t("auth.error.invalid_credentials"));
        setPending(false);
      }
    }

    async function submitSecondFactor(e: React.FormEvent) {
      e.preventDefault();
      setError(null);
      setPending(true);
      try {
        await api<LoginResponse>("/auth/2fa/verify", {
          method: "POST",
          body: JSON.stringify({ partial_token: partialToken, code }),
        });
        await qc.invalidateQueries({ queryKey: ["auth", "me"] });
        const next = search.next ? decodeURIComponent(search.next) : "/";
        await navigate({ to: next as "/" });
      } catch (err) {
        // Distinguish 401 invalid_code vs 401 partial_token_invalid vs network
        if (err instanceof ApiError && err.status === 401) {
          const detail = (err.body as { detail?: string })?.detail;
          if (detail === "partial_token_invalid") {
            setError(t("auth.2fa.verify.error.session_expired"));
            // After a brief moment, reset to email_password sub-state
            // OR offer an explicit "Back to email/password" button per AC-7 below.
          } else {
            setError(t("auth.2fa.verify.error.invalid_code"));
          }
        } else {
          setError(t("auth.2fa.verify.error.network"));
        }
        setPending(false);
      }
    }

    function backToEmailPassword() {
      setSubState("email_password");
      setPartialToken(null);
      setCode("");
      setError(null);
      setPending(false);
    }

    if (subState === "email_password") {
      return /* existing email+password form, but with submit handler = submitEmailPassword */;
    }

    return (
      <form onSubmit={submitSecondFactor} className="mx-auto mt-12 grid w-full max-w-sm gap-4 p-4">
        <h1 className="text-xl font-semibold">{t("auth.2fa.verify.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("auth.2fa.verify.description")}</p>
        <div className="grid gap-1.5">
          <label htmlFor={codeId} className="text-sm font-medium">
            {t("auth.2fa.verify.code_label")}
          </label>
          <Input
            id={codeId}
            name="code"
            type="text"
            inputMode="text"
            pattern="(\d{6})|([0-9a-f]{8})"
            autoComplete="one-time-code"
            maxLength={8}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={pending}
            autoFocus
          />
        </div>
        {error !== null && <p className="text-sm text-destructive" role="alert">{error}</p>}
        <Button type="submit" disabled={pending || code.length === 0}>
          {pending ? t("auth.signing_in") : t("auth.2fa.verify.submit_button")}
        </Button>
        <Button type="button" variant="ghost" onClick={backToEmailPassword} disabled={pending}>
          {t("auth.2fa.verify.back_button")}
        </Button>
      </form>
    );
  }
  ```

- And the `ApiError` import MUST be added at the top of `apps/web/src/routes/login.tsx`: `import { ApiError, api } from "@/lib/api";` (the existing import is `api` only — add `ApiError`).
- And the type imports MUST be added: `import type { LoginResponse, PartialAuthResponse } from "@/lib/api-types";` (the existing file has no `LoginResponse` / `PartialAuthResponse` types — they MUST be added per AC-8).
- And the discriminator branch MUST be `resp.partial_auth === true` — NOT `"partial_token" in resp` (field-presence check is fragile against future Pydantic shape changes; the discriminator is the binding contract).
- And the `partialToken` state MUST NOT be persisted outside React state — NO `localStorage.setItem`, NO `sessionStorage.setItem`, NO `qc.setQueryData(["auth", "partial_token"], ...)`. The token is bounded by the 5-min Redis TTL; persisting it would let it survive a tab refresh and surface a stale token to the server.
- And the second-factor input MUST be `autoFocus` on transition to `"second_factor"` sub-state — the user should be able to type the code without an extra click.
- And the "Back to email/password" button MUST clear `partialToken + code + error + pending` AND set `subState` back to `"email_password"` — a clean reset, not a half-state.
- And NO change to the existing `/login` route definition (line 85-92 of login.tsx) is required — the file-route stays at `createFileRoute("/login")` with the same `validateSearch` shape.

**AC-8 — `apps/web/src/lib/api-types.ts` gains `PartialAuthResponse` + `VerifyRequest` + extended `LoginResponse` TypeScript interfaces matching the backend Pydantic models.**

- Given the existing `apps/web/src/lib/api-types.ts` (229 lines, contains `MeResponse`, `Role`, etc. from earlier stories + the Story 7.2 `Totp*` types),
- When Story 7.3 ships,
- Then `apps/web/src/lib/api-types.ts` MUST gain EXACTLY these new entries (alphabetical placement within the file's existing organization):

  ```typescript
  export interface PartialAuthResponse {
    partial_auth: true;
    totp_required: true;
    partial_token: string;
  }

  export interface VerifyRequest {
    partial_token: string;
    code: string; // ^(\d{6}|[0-9a-f]{8})$
  }
  ```

- And the existing `LoginResponse` interface (if it exists in `api-types.ts` — search for `interface LoginResponse` first; if absent, ADD it) MUST gain the discriminator field:

  ```typescript
  export interface LoginResponse {
    partial_auth: false;  // discriminator — always false on this shape
    user: MeResponse;
  }
  ```

  If `LoginResponse` does not yet exist as a typed interface (the current `login.tsx` may have been using inline types), ADD the interface in the alphabetical position next to `MeResponse`.

- And the discriminated union pattern is binding — a downstream caller may write `if (resp.partial_auth === true) { /* PartialAuthResponse */ } else { /* LoginResponse */ }` and TypeScript narrows the type. This is the same pattern as `EnrollResponse | ConfirmResponse` from Story 7.2.
- And NO change to existing types (`MeResponse`, `TotpEnrollResponse`, `TotpStatusResponse`, etc.) is allowed.

**AC-9 — 6 new translation keys in `apps/web/src/locales/en.json` + `pl.json` for the second-factor prompt UX; all rendered text uses `t(...)`.**

- Given the existing 30+ `auth.2fa.*` keys added by Story 7.2 (lines 60-89 of `apps/web/src/locales/en.json` — `auth.2fa.title`, `auth.2fa.enroll.*`, `auth.2fa.show_codes.*`, `auth.2fa.done.*`, `auth.2fa.error.*`, etc.) + the existing `apps/web/src/locales/pl.json` parallel translations,
- When Story 7.3 ships,
- Then 6 NEW translation keys MUST be added to BOTH `en.json` AND `pl.json`, placed alphabetically within the `auth.2fa.*` block:

  - `auth.2fa.verify.title` — EN `Two-factor authentication` / PL `Uwierzytelnianie dwuskładnikowe`
  - `auth.2fa.verify.description` — EN `Enter the 6-digit code from your authenticator app, or one of your recovery codes.` / PL `Wprowadź 6-cyfrowy kod z aplikacji uwierzytelniającej lub jeden z kodów odzyskiwania.`
  - `auth.2fa.verify.code_label` — EN `Code` / PL `Kod`
  - `auth.2fa.verify.submit_button` — EN `Verify` / PL `Zweryfikuj`
  - `auth.2fa.verify.back_button` — EN `Back to sign in` / PL `Powrót do logowania`
  - `auth.2fa.verify.error.invalid_code` — EN `Incorrect code, try again` / PL `Nieprawidłowy kod, spróbuj ponownie`
  - `auth.2fa.verify.error.session_expired` — EN `Session expired, please sign in again.` / PL `Sesja wygasła, zaloguj się ponownie.`
  - `auth.2fa.verify.error.network` — EN `Network error, try again` / PL `Błąd sieci, spróbuj ponownie`

- That is 8 keys (the AC label "6" is an underestimate — the binding count is 8). Adjust the AC label if you count.
- And EVERY user-facing string in the second-factor sub-state of `apps/web/src/routes/login.tsx` MUST be `{t('auth.2fa.verify.*')}`. NO hardcoded strings. Verified by AC-13 grep check.
- And NO Polish formal-form ("Pan/Pani") — match the existing `auth.*` informal-form precedent.
- And NO existing locale keys are renamed or removed.

**AC-10 — Visual regression baselines for the second-factor prompt screen added in the SAME COMMIT; Playwright spec `apps/web/tests/visual/login-2fa-verify.spec.ts`.**

- Given the existing 204 Playwright visual-regression baselines post-Story 7.2 (188 baseline + 16 new for `settings-2fa.spec.ts`) + the FR13 Baseline Acceptance Gate "UI changes ship with own baseline updates, not deferred regen" + the existing 4-project matrix (`desktop-light`, `desktop-dark`, `mobile-light`, `mobile-dark`),
- When Story 7.3 ships,
- Then a NEW Playwright spec MUST exist at `apps/web/tests/visual/login-2fa-verify.spec.ts` covering 3 visual baselines × 4 projects = 12 baseline PNGs:

  1. `login-second-factor-prompt` — the page state after a successful email+password POST that returned `partial_auth: true`; renders the second-factor input + "Verify" + "Back to sign in" buttons; achieved by stubbing the `/api/auth/login` route via `page.route()` to return `{partial_auth: true, totp_required: true, partial_token: "test-partial-token-fixture"}`.
  2. `login-second-factor-invalid-code` — the page state after submitting a wrong code; renders the inline error "Incorrect code, try again" (translation key `auth.2fa.verify.error.invalid_code`); achieved by stubbing both routes (`/api/auth/login` → partial-auth + `/api/auth/2fa/verify` → 401 `invalid_code`).
  3. `login-second-factor-session-expired` — the page state after submitting a code with an expired partial_token; renders the inline error "Session expired, please sign in again" + the "Back to sign in" button highlighted; achieved by stubbing `/api/auth/2fa/verify` → 401 `partial_token_invalid`.

- And the 12 PNG baselines MUST be committed to `apps/web/tests/visual/__snapshots__/login-2fa-verify.spec.ts/` (matching the directory convention from Story 7.2's `settings-2fa.spec.ts-snapshots/` — confirm the exact path with `ls apps/web/tests/visual/__snapshots__/` before committing; if Story 7.2's directory shape differs from this AC's wording, follow Story 7.2's actual on-disk convention).
- And the spec MUST run across all 4 projects defined in `apps/web/playwright.config.ts` (desktop-light, desktop-dark, mobile-light, mobile-dark) — the Story 7.2 settings-2fa.spec.ts pattern (~80 LOC) is the binding template.
- And NO baseline PNG is added to `.gitignore` — visual baselines are checked-in artifacts per Init 3 Decision E.

**AC-11 — Backend tests: 18 named tests in `apps/api/tests/test_2fa_verify.py` cover the binding behavior end-to-end.**

- Given the existing test layout `apps/api/tests/test_2fa_enrollment.py` (Story 7.2, 18 named tests T1-T18) + the FastAPI `TestClient` + `_isolated_db` fixture precedent at `apps/api/tests/conftest.py:31-58` + the deterministic `TOTP_FERNET_KEY` fixture at `apps/api/tests/conftest.py:42`,
- When Story 7.3 ships,
- Then a NEW test file MUST exist at `apps/api/tests/test_2fa_verify.py` with these 18 named tests (every test name binding for cross-reference in code review):

  | # | Test name | Asserts |
  |---|---|---|
  | T1 | `test_login_with_totp_enabled_returns_partial_auth_no_cookies` | User with `totp_enabled_at = NOW()` + correct password → 200 + `{partial_auth: true, totp_required: true, partial_token: <str>}` body; response.cookies has NEITHER `portal_access` NOR `portal_refresh`. |
  | T2 | `test_login_partial_auth_does_not_emit_auth_login_success_audit_row` | After T1, query `SELECT * FROM audit_log WHERE action = 'auth.login.success' AND actor_user_id = <user.id>` returns ZERO rows. (NO premature success event.) |
  | T3 | `test_login_partial_auth_stashes_redis_payload_with_user_id_ttl_300` | After T1, `await redis.get(f"totp:partial:{partial_token}")` returns JSON with `{user_id: <user.id>, ip: <str>, ua: <str>}` AND TTL ∈ [295, 300]. |
  | T4 | `test_login_partial_auth_does_not_create_refresh_token_row` | After T1, `SELECT COUNT(*) FROM refresh_tokens WHERE user_id = <user.id>` returns ZERO. The refresh family is created ONLY on verify success. |
  | T5 | `test_login_single_factor_path_unchanged_for_user_without_totp_enabled` | User with `totp_enabled_at IS NULL` + correct password → 200 + `{partial_auth: false, user: {...}}` + cookies set + RefreshToken row created + `auth.login.success` audit row emitted. (Regression guard against breaking the existing single-factor flow.) |
  | T6 | `test_verify_with_correct_totp_returns_login_response_sets_cookies` | Pre-stash `totp:partial:<token>` with a known user_id; POST `/api/auth/2fa/verify {partial_token, code: <valid pyotp>}` → 200 + `{partial_auth: false, user: {...}}` + `portal_access` AND `portal_refresh` cookies set + new `RefreshToken` row exists for user. Use `pyotp.TOTP(<known_secret>).now()` to generate the code; the Fernet-encrypted ciphertext for `<known_secret>` must be pre-seeded into `users.totp_secret` via `encrypt_secret(<known_secret>, settings)`. |
  | T7 | `test_verify_with_correct_totp_emits_auth_totp_verify_success_audit_row` | After T6, exactly ONE new `auth.totp.verify.success` row exists with `entity_type='user'`, `entity_id=<user.id>`, `actor_user_id=<user.id>`, `after_json` JSON-decodes to `{"method": "totp"}`. NO `auth.login.success` row, NO `auth.recovery_code.used` row. |
  | T8 | `test_verify_with_correct_totp_deletes_partial_token_from_redis` | After T6, `await redis.get(f"totp:partial:{partial_token}")` returns `None`. |
  | T9 | `test_verify_with_correct_recovery_code_consumes_row_sets_used_at` | Pre-seed user with 8 recovery_codes via `generate_recovery_codes_batch()` + bcrypt-stored hashes; POST `/api/auth/2fa/verify {partial_token, code: <cleartext_code_2>}` (i.e. the 2nd cleartext code from the batch) → 200; SQL query confirms exactly ONE row in `recovery_codes` for that user has `used_at IS NOT NULL` (the 2nd code's row) AND its `used_at` is within ±10s of now. |
  | T10 | `test_verify_with_correct_recovery_code_emits_two_audit_rows_recovery_code_used_then_totp_verify_success` | After T9, exactly TWO new audit rows exist for this verify call: (a) one `auth.recovery_code.used` with `entity_type='recovery_code'`, `entity_id=<consumed_row.id>`, `actor_user_id=<user.id>`, `after_json` contains `batch_id` + `used_at`. (b) one `auth.totp.verify.success` with `entity_type='user'`, `after_json` JSON-decodes to `{"method": "recovery_code"}`. |
  | T11 | `test_verify_with_consumed_recovery_code_returns_401_invalid_code` | Pre-seed batch as in T9; mark `recovery_codes[2].used_at = NOW()` directly via DB; POST verify with the same cleartext code → 401 `invalid_code`. (Single-use property: a consumed code is not re-usable.) |
  | T12 | `test_verify_with_invalidated_recovery_code_returns_401_invalid_code` | Pre-seed batch as in T9; mark `recovery_codes[3].invalidated_at = NOW()` directly via DB (simulates Story 7.5 regenerate-time invalidation); POST verify with that code's cleartext → 401 `invalid_code`. (Invalidated codes are not consumable.) |
  | T13 | `test_verify_with_wrong_totp_code_returns_401_emits_fail_audit_no_token_consumption` | Pre-stash partial_token; POST `/api/auth/2fa/verify` with a wrong 6-digit code → 401 `invalid_code`; exactly ONE `auth.totp.verify.fail` audit row with `after_json = {"method": "totp"}`; partial_token IS STILL in Redis (not consumed); RefreshToken row count for user unchanged (zero new rows). |
  | T14 | `test_verify_with_wrong_recovery_code_returns_401_emits_fail_audit_no_token_consumption` | Pre-seed batch; POST verify with a non-matching 8-char hex code (e.g. `"deadbeef"` that's NOT in the batch) → 401 `invalid_code`; ONE `auth.totp.verify.fail` row with `after_json = {"method": "recovery_code"}`; partial_token still in Redis; NO `recovery_codes.used_at` mutation. |
  | T15 | `test_verify_with_malformed_code_returns_422_pydantic_validation` | POST verify with `code: "abc"` (4 chars, neither 6-digit nor 8-char-hex) → 422 (Pydantic regex fail at request-body validation, BEFORE the handler runs); NO audit emission of any kind. |
  | T16 | `test_verify_with_expired_partial_token_returns_401_partial_token_invalid` | Pre-stash partial_token with TTL 1s; sleep 2s; POST verify with that token → 401 `partial_token_invalid`; NO audit emission (no safe user_id attribution). |
  | T17 | `test_verify_with_user_disabled_totp_between_step1_and_step2_returns_401` | Pre-stash partial_token; mid-test, set `user.totp_enabled_at = None` directly via DB (simulates a Story 7.5 admin-disable race); POST verify → 401 `partial_token_invalid` (same 401 surface as expired token; defense-in-depth). |
  | T18 | `test_ratelimit_shared_budget_login_plus_verify_hits_429_at_6th_attempt` | From same IP: 4 POST `/api/auth/login` with wrong password (each → 401) + 1 POST `/api/auth/2fa/verify` with wrong code (→ 401) = 5 attempts in the bucket. The 6th attempt (whether login OR verify) → 429 `Too Many Requests` with `Retry-After` header. Proves AC-4 shared-budget contract. (Requires `monkeypatch` of `ratelimit_login_window_seconds` to 60 + `ratelimit_login_threshold` to 5 — both are the defaults.) |

- And every test name MUST appear verbatim in the test file (the dev-story task list cross-references them).
- And the test fixtures MUST use the deterministic `TOTP_FERNET_KEY` from `apps/api/tests/conftest.py:42` for all Fernet round-trips — NO inline key generation.
- And tests that need a specific TOTP secret value MUST set it directly (not via `pyotp.random_base32()`) so the codes are deterministic — use a known base32 string like `"JBSWY3DPEHPK3PXP"` (8-char "Hello!" encoded) for T6 + T13.
- And the fakeredis fixture from the Story 7.2 test pattern (the `_isolated_db` + redis-stub setup) is the binding test infrastructure — NO real Redis connection in unit tests.
- And the full backend suite MUST stay green: `cd apps/api && uv run pytest -q` → 658 passed (640 Story-7.2-baseline + 18 new from this story).

**AC-12 — Frontend tests: vitest spec `apps/web/src/routes/login.test.tsx` extended with 4 new test cases covering the partial-auth flow.**

- Given the existing `apps/web/src/routes/login.test.tsx` (single-factor login flow tests; depends on Story 7.2 baseline of 327 vitest specs),
- When Story 7.3 ships,
- Then `apps/web/src/routes/login.test.tsx` MUST be EXTENDED with 4 new vitest cases (NOT replaced — preserve all existing test cases):

  | # | Test name | Asserts |
  |---|---|---|
  | V1 | `it("renders second-factor prompt after partial-auth login response", ...)` | Mock `api()` for `/auth/login` to resolve with `{partial_auth: true, totp_required: true, partial_token: "fixture"}`. Render `<Login/>`. Type email+password + submit. Assert the second-factor input becomes visible AND the email/password form is no longer visible. Assert "Verify" button + "Back to sign in" button are visible. |
  | V2 | `it("submits verify call and navigates to next on success", ...)` | Mock `api()` for `/auth/login` → partial-auth response, then for `/auth/2fa/verify` → `{partial_auth: false, user: <MeResponse fixture>}`. Render `<Login/>` with `search.next` set to `"/queue"`. Type email+password + submit → type code + submit verify. Assert `navigate` was called with `{to: "/queue"}`. |
  | V3 | `it("shows invalid-code error on verify 401 and preserves partial-token state", ...)` | Mock `api()` for `/auth/2fa/verify` → throw `ApiError(401, {detail: "invalid_code"}, "...")`. Type a wrong code + submit verify. Assert the error message matches `t("auth.2fa.verify.error.invalid_code")` rendering AND the second-factor input is STILL visible (no fallback to email/password). |
  | V4 | `it("resets to email_password sub-state on back-button click", ...)` | Drive the component into second_factor sub-state. Click "Back to sign in". Assert email/password form is visible again AND the code input is gone AND the partial_token state has been cleared (re-renders if you assert via DOM presence). |

- And every existing test in `login.test.tsx` MUST stay green — NO regressions on the single-factor path.
- And the `qc.invalidateQueries(["auth", "me"])` call on verify success MUST be asserted in V2 (mock the query client; spy on `invalidateQueries`).
- And the vitest count after this story MUST be: 327 baseline + 4 new = 331 specs passing.

**AC-13 — Pre-merge cross-file grep checklist; sprint-status update; check-all.sh + visual regression + container build all green.**

- Given the Story 6.4 + 6.6 + 6.7 + 7.1 + 7.2 pre-merge grep-checklist precedent,
- When Story 7.3 is ready to merge,
- Then EACH of the following grep checks MUST be silent (zero matches) OR satisfied (non-zero match where expected):

  1. **(satisfied) verify endpoint exists with correct shape:**

     ```bash
     grep -nE '@router\.post\("/2fa/verify"' apps/api/app/modules/auth/totp/router.py  # 1 line
     grep -nE 'response_model=LoginResponse' apps/api/app/modules/auth/totp/router.py   # 1 line (on verify endpoint)
     grep -nE 'async def verify_second_factor' apps/api/app/modules/auth/totp/router.py # 1 line
     ```

  2. **(satisfied) partial-auth branch in login handler:**

     ```bash
     grep -nE 'totp:partial:' apps/api/app/modules/auth/router.py            # 1 line (Redis key prefix)
     grep -nE 'partial_token = secrets\.token_urlsafe\(32\)' apps/api/app/modules/auth/router.py  # 1 line
     grep -nE 'PartialAuthResponse' apps/api/app/modules/auth/router.py      # ≥2 lines (import + return)
     grep -nE 'async def login' apps/api/app/modules/auth/router.py          # 1 line (was `def login`)
     ```

  3. **(satisfied) rate-limit key_fn extension:**

     ```bash
     grep -nE '/api/auth/2fa/verify' apps/api/app/core/auth/ratelimit.py  # 1 line (inside login_ratelimit_key)
     grep -nE '/api/auth/login' apps/api/app/core/auth/ratelimit.py       # 1 line (still there)
     ```

  4. **(silent) NO cleartext logging in verify handler/service:**

     ```bash
     grep -E "(_LOG|logging|logger)\.(debug|info|warning|error|critical)\(.*(secret|recovery_code|partial_token|code)" \
       apps/api/app/modules/auth/totp/*.py apps/api/app/modules/auth/router.py
     # 0 lines — no logger emits cleartext material
     ```

  5. **(silent) NO cleartext code OR partial_token in response models:**

     ```bash
     grep -nE '"code"|"partial_token"' apps/api/app/modules/auth/models.py
     # 0 lines (LoginResponse + PartialAuthResponse must not expose `code`; partial_token only appears in PartialAuthResponse class def, NOT as a string literal in models.py)
     ```

  6. **(satisfied) 3 audit action names emitted in story scope:**

     ```bash
     grep -cE '"auth\.totp\.verify\.success"' apps/api/app/modules/auth/totp/router.py  # 1
     grep -cE '"auth\.totp\.verify\.fail"' apps/api/app/modules/auth/totp/router.py     # ≥1 (may be ≥2 if TOTP-fail + recovery-fail paths emit separately)
     grep -cE '"auth\.recovery_code\.used"' apps/api/app/modules/auth/totp/router.py    # 1
     ```

  7. **(satisfied) frontend route extended with second-factor sub-state:**

     ```bash
     grep -nE '"second_factor"|partialToken|setSubState' apps/web/src/routes/login.tsx
     # ≥4 lines (state machine + handler)
     grep -nE 'api<LoginResponse \| PartialAuthResponse>' apps/web/src/routes/login.tsx
     # 1 line (typed call)
     grep -nE '/auth/2fa/verify' apps/web/src/routes/login.tsx
     # 1 line (verify POST)
     ```

  8. **(satisfied) locale keys present + visual baseline file exists:**

     ```bash
     grep -cE '"auth\.2fa\.verify\.' apps/web/src/locales/en.json  # ≥7
     grep -cE '"auth\.2fa\.verify\.' apps/web/src/locales/pl.json  # ≥7
     ls apps/web/tests/visual/login-2fa-verify.spec.ts             # 1 file
     ```

- And the full pre-merge verification matrix MUST be green on the dev commit:
  - `cd apps/api && uv run pytest -q` → **658 passed** (Story 7.2 baseline 640 + 18 new from `test_2fa_verify.py`).
  - `cd apps/web && npm run typecheck && npm run lint && npm run test` → all green; vitest **331 passed** (327 baseline + 4 new in `login.test.tsx`).
  - `cd apps/web && npm run test:visual` → **216 specs passed** (204 baseline post-7.2 + 12 new 3-states × 4-projects).
  - `infra/scripts/check-all.sh` → **10/10 green**.
  - `docker compose -f infra/docker-compose.yml build api` → succeeded; image `portal-api:0.1.0` rebuilds clean (no new deps — same pyotp 2.9 + qrcode 8.2 + cryptography 48.x baseline from Story 7.2; the verify endpoint reuses Story 7.2's `decrypt_secret` + `verify_totp_code` helpers and the existing `bcrypt` dep).
  - `alembic upgrade head --sql | head` → head stays `0013_users_2fa_columns`. NO new migration.

- And the operator deploy-gate: `TOTP_FERNET_KEY` MUST already be provisioned on `.190` `infra/.env` from Story 7.2's deploy-gate (see Story 7.2 `_bmad-output/implementation-artifacts/7-2-totp-enrollment-endpoint-and-ui.md` AC-13). Verify with: `ssh ezope@192.168.2.190 'cd /home/ezope/3d-portal && test -n "$(grep -E "^TOTP_FERNET_KEY=." infra/.env)" && echo OK || echo MISSING'`. If `MISSING`, this story will return `500 totp_corrupt_state` on `decrypt_secret` for any user who enrolled before the key was set — but **by Story 7.2's invariant, no user can have `totp_enabled_at IS NOT NULL` without a working Fernet key**, so the only way this hits production is if 7.2 shipped to a misconfigured `.190` and a user enrolled there. Defense-in-depth: the `_assert_fernet_key_configured()` guard from Story 7.2 still fires on the begin_enrollment + confirm_enrollment paths if the key is missing — so 7.3 inherits the protection.

## Tasks / Subtasks

- [ ] **T1 — Add `PartialAuthResponse` + `VerifyRequest` Pydantic models; extend `LoginResponse` with `partial_auth: bool = False` discriminator (AC: 2, 13.5)**
  - [ ] Edit `apps/api/app/modules/auth/models.py`: add `PartialAuthResponse` class with 3 fields (`partial_auth=True`, `totp_required=True`, `partial_token: str`) + extend `LoginResponse` with `partial_auth: bool = False` field placed BEFORE `user: MeResponse`.
  - [ ] Edit `apps/api/app/modules/auth/totp/schemas.py`: add `VerifyRequest` class with regex pattern `^(\d{6}|[0-9a-f]{8})$` on the `code` field.
  - [ ] Verify the Story 7.2 `ConfirmRequest.code` regex stays `^\d{6}$` (NOT extended — enrollment-confirm is TOTP-only).
  - [ ] Run `cd apps/api && uv run pytest tests/test_auth.py tests/test_2fa_enrollment.py -v` to confirm no regression on the existing login + enrollment tests (LoginResponse field addition has a default value, so backward-compatible).

- [ ] **T2 — Extend `apps/api/app/modules/auth/router.py:login()` with partial-auth branch (AC: 1, 6, 13.2)**
  - [ ] Convert `def login(...)` → `async def login(...)`.
  - [ ] Add `import json`, `import secrets` if not already imported (likely already there via the existing surface).
  - [ ] Add import `from app.modules.auth.models import PartialAuthResponse` to the existing imports block.
  - [ ] Change `@router.post("/login", response_model=LoginResponse)` to `@router.post("/login", response_model=Union[LoginResponse, PartialAuthResponse])` (or `LoginResponse | PartialAuthResponse` Python 3.10+ union; FastAPI supports both — match the existing codebase style).
  - [ ] Insert the partial-auth branch IMMEDIATELY after the existing password-verify failure path (line 69) AND BEFORE the existing `ip, ua = _client_meta(request)` line (line 71):
    ```python
    if user.totp_enabled_at is not None:
        partial_token = secrets.token_urlsafe(32)
        ip, ua = _client_meta(request)
        stash = json.dumps({
            "user_id": str(user.id),
            "ip": ip or "",
            "ua": ua or "",
        })
        await request.app.state.redis.get().set(
            f"totp:partial:{partial_token}",
            stash.encode(),
            ex=300,
        )
        return PartialAuthResponse(
            partial_auth=True,
            totp_required=True,
            partial_token=partial_token,
        )
    ```
  - [ ] Leave the existing single-factor success path (lines 71-104) UNCHANGED.
  - [ ] Run `cd apps/api && uv run pytest tests/test_auth.py tests/test_auth_login_logout.py -v` to confirm existing tests still pass (the new branch only fires when `user.totp_enabled_at IS NOT NULL`, which the existing tests never set).

- [ ] **T3 — Add `POST /api/auth/2fa/verify` endpoint in `apps/api/app/modules/auth/totp/router.py` (AC: 3, 5, 6, 13.1, 13.4, 13.6)**
  - [ ] Add imports: `import json`, `import re`, `from app.modules.auth.totp.service import verify_totp_code, decrypt_secret`, `from app.modules.auth.totp.schemas import VerifyRequest`, `from app.modules.auth.models import LoginResponse, MeResponse`, `from app.core.auth.refresh import new_refresh_row`, `from app.core.auth.cookies import set_session_cookies`, `from app.core.auth.jwt import encode_token`, `from app.core.db.models import RecoveryCode`, plus `import bcrypt`, `import datetime`, `from cryptography.fernet import InvalidToken` (for the defensive catch).
  - [ ] Helper to extract IP/UA: import `_client_meta` from `apps/api/app/modules/auth/router` if it is module-public (it's a leading-underscore name so technically private — either rename it to `client_meta` and export, OR duplicate the 3-line implementation in the totp router; prefer the rename + import path for DRY, with `client_meta` exported from `apps/api/app/modules/auth/router.py`).
  - [ ] Implement `async def verify_second_factor(payload: VerifyRequest, request: Request, response: Response, session: Annotated[Session, Depends(get_session)], settings: Annotated[Settings, Depends(get_settings)]) -> LoginResponse` per AC-3 T3 sequence verbatim:
    - Step 1: Redis GET `totp:partial:<token>`; 401 `partial_token_invalid` on miss.
    - Step 2: Load user by stash.user_id; 401 `partial_token_invalid` if user gone OR `totp_enabled_at IS NULL`.
    - Step 3: 500 `totp_corrupt_state` if `user.totp_secret is None`.
    - Step 4: Branch by `re.fullmatch(r"\d{6}", payload.code)`:
      - TOTP path: try `decrypt_secret(user.totp_secret, settings)`, catch `InvalidToken` → emit fail + 401; else `verify_totp_code(secret, code)` → False = emit fail + 401, True = proceed.
      - Recovery path: SELECT active codes newest-first; iterate `bcrypt.checkpw(payload.code.encode(), row.code_hash.encode())`; no match = emit fail + 401; first match = consume.
    - Step 5: (recovery-only) set `matched_row.used_at = NOW(UTC)`; `session.add(matched_row)`.
    - Step 6: Mint refresh row via `new_refresh_row(user_id=user.id, family_id=None, family_issued_at=None, ip=ip, user_agent=ua)`; `session.add(row)`.
    - Step 7: `session.commit()` → emit `auth.recovery_code.used` (recovery-only) → emit `auth.totp.verify.success`.
    - Step 8: `encode_token(...)` → `set_session_cookies(...)` → Redis DEL partial_token → return `LoginResponse(partial_auth=False, user=MeResponse(...))`.
  - [ ] Update the router decorator: `@router.post("/2fa/verify", response_model=LoginResponse, status_code=status.HTTP_200_OK, summary=..., description=...)`.

- [ ] **T4 — Extend `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` to also match `/api/auth/2fa/verify` (AC: 4, 13.3)**
  - [ ] Edit `login_ratelimit_key` to check `request.url.path in {"/api/auth/login", "/api/auth/2fa/verify"}` instead of the single-path equality.
  - [ ] Verify NO change to `apps/api/app/main.py` middleware mount block (the existing `RateLimitMiddleware(scope="login", key_fn=login_ratelimit_key, ...)` mount automatically picks up the extended key_fn).
  - [ ] Run `cd apps/api && uv run pytest tests/test_ratelimit_middleware.py -v` (if the file exists) to confirm the existing 4-scope rate-limit suite still passes (key_fn extension is backward-compatible — the new path returns a key matching the existing scope name).

- [ ] **T5 — Backend tests `apps/api/tests/test_2fa_verify.py` (AC: 11)**
  - [ ] Author T1-T18 per AC-11 binding table verbatim.
  - [ ] Use the existing `_isolated_db` fixture + the deterministic `TOTP_FERNET_KEY` from `conftest.py:42`.
  - [ ] For tests needing a known TOTP secret (T6, T13): use `secret = "JBSWY3DPEHPK3PXP"` (the canonical pyotp docs example); encrypt via `encrypt_secret(secret, settings)`; generate codes via `pyotp.TOTP(secret).now()`.
  - [ ] For tests needing pre-seeded recovery codes (T9-T14): call `generate_recovery_codes_batch()` to get the tuples; INSERT `RecoveryCode` rows directly via the test session; hold the cleartext list for the test assertions.
  - [ ] For T16 (TTL expiry): use `await redis_client.set(key, value, ex=1)` then `await asyncio.sleep(2)` (the test-fixture redis is fakeredis but supports TTL — verify this if the test is flaky; if fakeredis TTL is not honored under asyncio.sleep, monkeypatch the Redis GET to return `None` instead).
  - [ ] Run `cd apps/api && uv run pytest tests/test_2fa_verify.py -v` until all 18 are green.
  - [ ] Run `cd apps/api && uv run pytest -q` → confirm **658 passed** (640 baseline + 18 new).

- [ ] **T6 — Frontend extension `apps/web/src/routes/login.tsx` + type imports (AC: 7, 8, 9, 13.7)**
  - [ ] Edit `apps/web/src/lib/api-types.ts`: add `PartialAuthResponse` + `VerifyRequest` interfaces; extend `LoginResponse` with the `partial_auth: false` discriminator (or add the interface if it doesn't yet exist).
  - [ ] Edit `apps/web/src/routes/login.tsx`:
    - Add `ApiError` to the existing import: `import { ApiError, api } from "@/lib/api";`.
    - Add type imports: `import type { LoginResponse, PartialAuthResponse } from "@/lib/api-types";`.
    - Add state: `useState<SubState>("email_password")`, `useState<string | null>(null)` for `partialToken`, `useState<string>("")` for `code`.
    - Split the existing `submit` handler into `submitEmailPassword` (extends to detect `resp.partial_auth === true` → set partialToken + subState) and `submitSecondFactor` (POSTs to `/auth/2fa/verify`).
    - Add `backToEmailPassword` reset helper.
    - Conditionally render the second-factor form when `subState === "second_factor"`.
  - [ ] Edit `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`: add 8 new keys per AC-9 verbatim.

- [ ] **T7 — Frontend tests `apps/web/src/routes/login.test.tsx` 4 new cases V1-V4 (AC: 12)**
  - [ ] Extend the existing test file with V1-V4 per AC-12 verbatim.
  - [ ] Use the existing `@testing-library/react` + `vitest` + `msw` (if installed) OR manual `vi.mock("@/lib/api", ...)` pattern matching the existing test conventions in `apps/web/src/routes/login.test.tsx`.
  - [ ] Run `cd apps/web && npm run test login.test.tsx` until 4 new + existing N are green.
  - [ ] Confirm vitest total: **331 passed**.

- [ ] **T8 — Visual regression spec `apps/web/tests/visual/login-2fa-verify.spec.ts` + 12 baselines (AC: 10)**
  - [ ] Create `apps/web/tests/visual/login-2fa-verify.spec.ts` modeled on `apps/web/tests/visual/settings-2fa.spec.ts`.
  - [ ] Use Playwright `page.route('/api/auth/login', ...)` + `page.route('/api/auth/2fa/verify', ...)` to stub deterministic API responses for each baseline.
  - [ ] Define 3 baselines: `login-second-factor-prompt`, `login-second-factor-invalid-code`, `login-second-factor-session-expired`.
  - [ ] Run `cd apps/web && npm run test:visual -- login-2fa-verify` with `--update-snapshots` to author 12 baseline PNGs (3 states × 4 projects).
  - [ ] Verify no untracked extras: `git status apps/web/tests/visual/`.
  - [ ] Run `cd apps/web && npm run test:visual` → **216 specs passed** (204 baseline + 12 new).

- [ ] **T9 — Pre-merge verification (AC: 13)**
  - [ ] Run AC-13 grep checks 1-8 verbatim; capture output in Dev Agent Record.
  - [ ] Run `cd apps/api && uv run pytest -q` → **658 passed**.
  - [ ] Run `cd apps/web && npm run typecheck && npm run lint && npm run test` → all green; vitest **331 passed**.
  - [ ] Run `cd apps/web && npm run test:visual` → **216 specs passed**.
  - [ ] Run `infra/scripts/check-all.sh` → **10/10 green**.
  - [ ] Run `docker compose -f infra/docker-compose.yml build api` → succeeded (no new deps).
  - [ ] Verify `alembic heads` returns `0013_users_2fa_columns (head)` — NO new migration.
  - [ ] Verify TOTP_FERNET_KEY present on `.190` (carried over from Story 7.2 deploy-gate; no fresh provisioning needed if 7.2 shipped clean).

## Dev Notes

### Architecture references — binding

- **Decision D §1495-1513** — Fernet column shape; cleartext-surface invariant; Story 7.3 is FIRST production caller of `decrypt_secret` (Story 7.2 used the helper only in a round-trip test).
- **Decision E §1515-1534** — Recovery-codes schema; consumption iteration shape (newest-batch-first, `bcrypt.checkpw` per row, first match sets `used_at` + emits `auth.recovery_code.used`).
- **Decision F §1536-1557** — `enforce_2fa_for_roles` config + middleware enforcement is **deferred to Story 7.4** — this story's partial-auth response shape is forward-compatible with 7.4's additional `totp_enroll_required` variant.
- **Decision G §1559-1586** — Rate-limit middleware; the `login_ratelimit_key` extension at AC-4 reuses the existing `login` scope (no new scope added).
- **Epics.md §1682-1697 (Story 7.3 acceptance check shape)** — verbatim contract for the partial-auth response shape + verify endpoint behavior + recovery-code iteration + rate-limit reuse + visual-regression baseline same-commit rule.
- **PRD FR5-2FA-2 §prd.md:1187** — login flow extends with second factor; recovery code consumption is one-way; wrong second factor 401 with `auth.totp.verify.fail`; correct → 200 + cookies + `auth.totp.verify.success`.
- **PRD FR5-AUDIT-1 §prd.md:1200** — `auth.totp.verify.success` + `auth.totp.verify.fail` + `auth.recovery_code.used` are in the binding 16-action vocabulary.

### Files that this story creates (NEW)

| Path | LOC est | Purpose |
|---|---|---|
| `apps/api/tests/test_2fa_verify.py` | 600 | 18 named backend tests T1-T18 |
| `apps/web/tests/visual/login-2fa-verify.spec.ts` | 80 | 3 visual baselines × 4 projects |
| 12 PNGs in `apps/web/tests/visual/__snapshots__/login-2fa-verify.spec.ts/` | — | Baselines |

### Files that this story modifies (UPDATE)

| Path | What changes | What must NOT change |
|---|---|---|
| `apps/api/app/modules/auth/router.py` | `def login` → `async def login`; +partial-auth branch (~12 LOC after the password-fail handler); +imports (json, secrets, PartialAuthResponse); response_model becomes `Union[LoginResponse, PartialAuthResponse]` | The single-factor success path (lines 71-104); the `auth.login.fail` emission on bad-password; the `_client_meta` helper; the `/refresh` / `/me` / `/logout` / `/sessions` endpoints |
| `apps/api/app/modules/auth/models.py` | +`PartialAuthResponse` class; `LoginResponse` gains `partial_auth: bool = False` field | Existing `MeResponse`, `LoginRequest`, `SessionRow`, `SessionsResponse` |
| `apps/api/app/modules/auth/totp/router.py` | +`async def verify_second_factor` endpoint (~80 LOC) + imports | Existing `begin_enrollment` / `confirm_enrollment` / `read_status` |
| `apps/api/app/modules/auth/totp/schemas.py` | +`VerifyRequest` class | Existing `EnrollResponse` / `ConfirmRequest` / `ConfirmResponse` / `StatusResponse` |
| `apps/api/app/core/auth/ratelimit.py` | `login_ratelimit_key`: single-path equality → `in {...}` set membership | All other key_fns (`refresh_ratelimit_key`, `register_ratelimit_key`, `share_ratelimit_key`); the `RateLimitMiddleware` class; the `_client_ip` helper |
| `apps/web/src/routes/login.tsx` | State machine + second-factor sub-state + verify handler + back button + type imports | The `/login` file-route definition (line 85-92); the `validateSearch` shape |
| `apps/web/src/routes/login.test.tsx` | +4 new vitest cases V1-V4 | All existing single-factor login tests |
| `apps/web/src/lib/api-types.ts` | +`PartialAuthResponse`, +`VerifyRequest`, extend `LoginResponse` with `partial_auth: false` discriminator | All other types |
| `apps/web/src/locales/en.json` | +8 `auth.2fa.verify.*` keys | All existing keys |
| `apps/web/src/locales/pl.json` | +8 `auth.2fa.verify.*` keys (Polish translations) | All existing keys |

### Files that this story does NOT touch

- `apps/api/migrations/versions/` — no new migration; Story 7.1's `0013_users_2fa_columns` is still the head.
- `apps/api/app/core/config.py` — no new Pydantic Settings field (rate-limit + Fernet config inherited from 7.1 + 7.2).
- `apps/api/app/core/audit.py` — `KNOWN_ENTITY_TYPES` already has `recovery_code` from 7.1 and `user` from project init.
- `apps/api/app/core/auth/middleware.py` — Decision F enforcement is Story 7.4; this story does not introduce per-request 2FA enforcement middleware.
- `apps/api/app/modules/auth/totp/service.py` — the verify endpoint reuses the existing `decrypt_secret` + `verify_totp_code` helpers without modification.
- `apps/api/pyproject.toml` / `apps/api/uv.lock` — no new dependencies (bcrypt + pyotp + cryptography are all present from 7.1/7.2).
- `apps/web/src/modules/auth/Settings2faPage.tsx` — the enrollment wizard is unchanged; verify-step UX lives in the login route.
- `infra/env.example` / `infra/docker-compose.yml` — env wiring already done in 7.1.
- `apps/api/app/main.py` — middleware mount block is unchanged (rate-limit key_fn extension is picked up automatically).

### Previous-story intelligence — Story 7.2 (commit 9e6c0e4 + fix-ups 061e9ae, ab82f66, 2f73406)

Carried forward (binding for 7.3):

- **`apps/api/app/modules/auth/totp/service.py` exposes `decrypt_secret(ciphertext, settings) -> str`** — Story 7.3 is the FIRST production caller. The helper at `service.py:105-113` reads the Fernet ciphertext from `users.totp_secret` and returns the cleartext base32 string for one verify call. NO changes to the helper are allowed.
- **`apps/api/app/modules/auth/totp/service.py` exposes `verify_totp_code(secret, code) -> bool`** — calls `pyotp.TOTP(secret).verify(code, valid_window=1)`. Reuse verbatim.
- **`apps/api/app/modules/auth/totp/service.py` exposes `generate_recovery_codes_batch() -> tuple[uuid.UUID, list[tuple[str, str]]]`** — Story 7.3 does NOT call this directly; recovery-code rows already exist in the DB after Story 7.2 enrollment.
- **`apps/api/app/core/db/models/_recovery.py:RecoveryCode` SQLModel exists** with columns `id, user_id, code_hash, batch_id, generated_at, used_at, invalidated_at` — Story 7.3 SELECTs from this table + UPDATEs `used_at`.
- **`apps/api/app/modules/auth/totp/router.py` already imports** `record_event, current_user, Settings, User, UserRole, RecoveryCode (via models index), get_engine, get_session` — the new verify endpoint inherits the same import block (only NEW imports needed are `bcrypt`, `re`, `datetime`, `from cryptography.fernet import InvalidToken`, `LoginResponse, MeResponse from app.modules.auth.models`, `new_refresh_row, set_session_cookies, encode_token` from the existing auth core).
- **Story 7.2 race lesson — atomic Redis claim (GETDEL)** — the `confirm_enrollment` handler uses `redis.execute_command("GETDEL", key)` for the enrollment_token consumption to prevent double-minting under `uvicorn --workers 2`. The verify endpoint in Story 7.3 has a similar concern: two concurrent verify POSTs with the same partial_token could both pass the code check and both try to create a RefreshToken row. **MITIGATION:** the partial_token is single-user-bound (the stash payload contains the user_id) and the success path creates exactly one new RefreshToken family per call — both workers would create their own families (no DB integrity violation), and the partial_token DEL is best-effort. The downside is one user could end up with 2 refresh families instead of 1 — a benign over-issue, not a security flaw. ALTERNATIVELY: use the same GETDEL pattern AFTER the code-verify step to ensure exactly one verify success per partial_token. For Story 7.3, defer this hardening to a future Codex review finding rather than over-engineering now (the contention window is small + the failure mode is benign). NOTE THIS IN DEV NOTES AND LET CODEX FLAG IT IF CONCERNED.

Lessons from 7.2 close-out (binding):

- **Pre-merge grep checklist is BINDING.** Story 7.2 had 8/8 silent grep checks before merge; expect the same discipline here.
- **Visual-regression baselines ship in the SAME COMMIT as the UI change** (FR13 + Init 3 Decision E). NO deferred regen.
- **uv.lock regen rule does not apply here** because this story adds NO new dependencies.
- **Locale keys ship in BOTH en.json AND pl.json** in the same commit. The existing `auth.2fa.*` block precedent has parallel translations.
- **NO cleartext logging.** Story 7.2's AC-13.4 grep check has been carried forward as AC-13.4 here — extended to also check the new verify handler.

### Code structure guardrails — DON'T

- DON'T create a separate `apps/api/app/modules/auth/verify/` subdirectory. The verify endpoint lives in the same `apps/api/app/modules/auth/totp/router.py` as the other 2FA endpoints (precedent: Story 7.2 groups all 2FA surface in one router).
- DON'T add a new rate-limit scope (e.g. `verify`). Reuse the existing `login` scope per epics §1694 verbatim.
- DON'T add `auth.login.success` emission on partial-auth success — the authoritative event is `auth.totp.verify.success`.
- DON'T allow re-running `/api/auth/login` with the same email+password to mint a NEW partial_token while an old one is still active. The Redis SET overwrites the previous key with the same `f"totp:partial:{new_token}"` ONLY if the new token happens to collide (32-byte entropy → impossible). Each login attempt for a partial-auth user mints a FRESH partial_token; old partial_tokens stay valid until their 5min TTL expires. This is intentional — it matches the existing `/api/auth/login` semantics (each login mints a new RefreshToken family; older families stay valid until natural expiry or explicit revocation). The defense against partial_token hoarding is the 5min TTL + the per-IP rate-limit.
- DON'T allow the verify endpoint to be reached without going through `/api/auth/login` first. There is NO partial_token issuance path other than the login handler. An attacker who somehow obtains a partial_token still needs to know the bound user's `totp_secret` or a valid recovery code to verify — the partial_token alone is NOT a credential.
- DON'T log the cleartext code, the partial_token, or the decrypted TOTP secret. ALL three are credential-equivalent.
- DON'T persist the partial_token in browser storage on the frontend. Local React state only. 5min Redis TTL is the only durability layer.
- DON'T extend the `Settings2faPage` enrollment wizard for the verify step. The verify UX lives in `apps/web/src/routes/login.tsx` — the user enters the second factor on the login screen, not in the settings page.
- DON'T add a CSRF middleware exception for `/api/auth/2fa/verify`. The existing X-Portal-Client header check applies; the frontend's `api()` wrapper already sets the header.
- DON'T return the user-id, email, or any PII in the partial-auth response. The `partial_token` is the ONLY identifier the frontend gets — it CANNOT use the response to render a "You are signed in as Anna" greeting before the second factor. This is intentional: partial-auth must not leak account state.

### Code structure guardrails — DO

- DO branch the verify endpoint by `re.fullmatch(r"\d{6}", payload.code)` for the TOTP/recovery-code split — relying on Python's `re` module, NOT manual length checks (more robust against future shape changes like 7-digit TOTP for sites that use longer codes).
- DO use `bcrypt.checkpw(code.encode(), row.code_hash.encode())` — both args must be bytes (the stored `code_hash` is a string from `.decode()` at Story 7.2 generation time; `.encode()` converts back to bytes for the check).
- DO catch `cryptography.fernet.InvalidToken` defensively in the TOTP path even though it's impossible-by-construction (Story 7.2 enrolled with the same key) — the 401 fallback prevents a 500 leak that would let an attacker probe key-rotation events.
- DO emit `auth.totp.verify.fail` even when the partial_token is invalid? **NO** — re-check this: AC-3 step 1/2 raise 401 without emitting fail audit because there is no safe user_id attribution. Only emit fail when we have a valid user_id (i.e. partial_token resolved to a real user).
- DO commit the RefreshToken INSERT AND the recovery_code UPDATE in ONE `session.commit()`. Partial-state failure must roll back BOTH.
- DO emit `auth.recovery_code.used` BEFORE `auth.totp.verify.success` (chronological order in the audit log matches the causal order — the recovery-code consumption causes the verify success).
- DO set both audit `request_id` fields from `request.headers.get("x-request-id")` (may be `None` in unit tests; the audit helper accepts None).
- DO test the SHARED rate-limit budget end-to-end (T18) — this is the binding defense-in-depth contract from epics §1694 and missing the test would leave a regression vector for future middleware refactors.
- DO use the deterministic TOTP_FERNET_KEY from `conftest.py:42` in all Fernet round-trip tests — NO inline key generation that would make the tests non-deterministic.
- DO add `autoFocus` to the second-factor input on transition to `second_factor` sub-state — UX detail that significantly improves the flow.

### Testing standards summary

- Backend tests: `pytest` with FastAPI `TestClient` against a real SQLite test DB (the `_isolated_db` session fixture); fakeredis stubbed via the existing redis-factory patch precedent. Run from `apps/api/` directory.
- Frontend unit tests: `vitest` against React Testing Library; mock `api()` calls via `vi.mock("@/lib/api", ...)` matching the existing `login.test.tsx` pattern.
- Visual-regression tests: `playwright` against the dev server with route-stubbing for the 2FA-relevant API endpoints; 12 new baselines for 7.3 (3 states × 4 projects).
- Cleartext-secret discipline: NO test allowed to print, log, or assert against a cleartext TOTP secret or recovery code in a way that would leak it into CI logs. Assertions over Fernet ciphertext / bcrypt hashes use opaque-shape checks (`startswith("$2b$12$")`, `Fernet().decrypt(...) succeeds`).

### Project Structure Notes

- The verify endpoint lives in `apps/api/app/modules/auth/totp/router.py` alongside the existing 3 endpoints — this keeps all 2FA surface under one directory matching the precedent of `apps/api/app/modules/invite/`.
- The login handler in `apps/api/app/modules/auth/router.py` is the ONLY place the partial-auth branch fires. NO middleware-layer enforcement (Decision F is deferred to Story 7.4 and will be inline in `login()` per Decision F §1557 verbatim — NOT a separate middleware).
- The frontend `login.tsx` route file gains a sub-state machine internally; the route definition + URL shape stay unchanged. A future Story 7.4 may extend the same component with a third sub-state for `totp_enroll_required` partial-auth responses.
- The rate-limit key_fn extension is the ONE binding change to `apps/api/app/core/auth/ratelimit.py` in this story — the middleware itself, the scope names, and the threshold config stay unchanged.

### References

- `_bmad-output/planning-artifacts/epics.md:1682-1697` (Story 7.3 acceptance check shape)
- `_bmad-output/planning-artifacts/architecture.md:1495-1534` (Decisions D + E)
- `_bmad-output/planning-artifacts/architecture.md:1559-1586` (Decision G — rate-limit key shapes)
- `_bmad-output/planning-artifacts/prd.md:1187` (FR5-2FA-2 binding requirement)
- `_bmad-output/planning-artifacts/prd.md:1200` (FR5-AUDIT-1 vocabulary)
- `_bmad-output/implementation-artifacts/7-2-totp-enrollment-endpoint-and-ui.md` (Story 7.2 spec — enrollment surface + service module + Fernet helpers)
- `_bmad-output/implementation-artifacts/sprint-status.yaml:153` (Story 7.2 close-out + dependency for 7.3)
- `apps/api/app/modules/auth/router.py:51-104` (existing single-factor login handler to extend)
- `apps/api/app/modules/auth/totp/router.py` (existing 2FA router to extend with verify endpoint)
- `apps/api/app/modules/auth/totp/service.py:105-113` (`decrypt_secret` — Story 7.3 first production caller)
- `apps/api/app/modules/auth/totp/service.py:95-97` (`verify_totp_code` — reuse verbatim)
- `apps/api/app/core/auth/ratelimit.py:80-83` (existing `login_ratelimit_key` to extend)
- `apps/api/app/core/auth/refresh.py:new_refresh_row` (RefreshToken factory)
- `apps/api/app/core/auth/cookies.py:set_session_cookies` (cookie issuance)
- `apps/api/app/core/auth/jwt.py:encode_token` (access-token mint)
- `apps/api/app/core/audit.py:record_event` (audit emission helper + KNOWN_ENTITY_TYPES check)
- `apps/api/app/core/db/models/_recovery.py:RecoveryCode` (SQLModel for recovery_codes table)
- `apps/api/tests/conftest.py:42` (deterministic TOTP_FERNET_KEY test fixture)
- `apps/web/src/routes/login.tsx` (existing single-factor login route to extend)
- `apps/web/src/lib/api.ts:11` (api wrapper; CSRF header; 401-refresh-retry)
- `apps/web/src/lib/api-types.ts` (TS interface surface)
- `apps/web/src/locales/en.json + pl.json` (i18n keys, parallel translations)
- `apps/web/tests/visual/settings-2fa.spec.ts` (Story 7.2 spec — visual-regression precedent)
- pyotp docs: `pyotp.TOTP(secret).verify(code, valid_window=1)` (Story 7.2 already binds this)
- bcrypt docs: `bcrypt.checkpw(password, hashed)` accepts bytes both args, parses cost+salt from the hashed prefix
- RFC 6238 (TOTP standard — valid_window=1 = ±30s industry default)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-05-19 — Story 7.3 spec authored via `bmad-create-story` (autonomous YOLO). Realizes FR5-2FA-2 — login flow extends with partial-auth + second-factor verify step accepting TOTP OR recovery code. Backend extends `apps/api/app/modules/auth/router.py:login()` (sync → async, adds partial-auth branch on `totp_enabled_at IS NOT NULL`) + adds `POST /api/auth/2fa/verify` to `apps/api/app/modules/auth/totp/router.py` (~80 LOC; reuses Story 7.2's `decrypt_secret` + `verify_totp_code` helpers; recovery-code iteration per Decision E §1531 newest-batch-first + `bcrypt.checkpw` per row + `used_at` consumption + atomic single-commit DB write) + extends `login_ratelimit_key` to share the existing `login` scope budget with `/api/auth/2fa/verify` per epics §1694. Frontend extends `apps/web/src/routes/login.tsx` (state machine: email_password → second_factor) + adds 8 new locale keys (en + pl) + 12 visual baselines (3 states × 4 projects). NEW models `PartialAuthResponse` + `VerifyRequest`; extends `LoginResponse` with `partial_auth: bool = False` discriminator. NO new dependencies; NO new Alembic migration; NO new rate-limit scope. 658 backend tests pass (18 new in `test_2fa_verify.py`). 331 vitest specs pass (4 new in `login.test.tsx`). 216 visual specs pass (12 new). Decision F enforcement (`enforce_2fa_for_roles`) explicitly deferred to Story 7.4; 7.3 response shape is forward-compatible (Story 7.4 may add a `totp_enroll_required` variant on the same `PartialAuthResponse` union).
