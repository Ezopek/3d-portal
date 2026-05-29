# Story 7.5: Regenerate recovery codes + disable TOTP — re-auth-gated endpoints + `/settings/2fa` panel actions (Decision E batch invalidation + audit lifecycle)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an Initiative 5 maintainer,
I want **two NEW backend endpoints** mounted on the existing `apps/api/app/modules/auth/totp/router.py` (NOT a new `regenerate_router.py` file — the `_recovery.py:18-19` docstring hint pre-dates Story 7.3's same-file precedent and the spec EXPLICITLY OVERRIDES that hint to keep all `/api/auth/2fa/*` endpoints in one router file for OpenAPI grouping consistency):

- `POST /api/auth/2fa/recovery-codes/regenerate {password, totp_code}` (`current_user` dep, agent-forbidden, 200 OK on success) — re-auth-gates on `verify_password(payload.password, user.password_hash)` AND `verify_totp_code(decrypt_secret(user.totp_secret, settings), payload.totp_code)` (both must pass; either single failure → 401 `invalid_credentials` with NO state mutation + emit `auth.totp.verify.fail` audit row with `after={"method": "regenerate_reauth", "reason": "password" | "totp"}`); on success, ATOMIC single-session-commit covering: (1) UPDATE recovery_codes SET invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL (Decision E §1533 "one-statement UPDATE" verbatim) — `result.rowcount` captured + emitted in audit payload as `invalidated_count`; (2) INSERT 8 new `recovery_codes` rows via the existing `generate_recovery_codes_batch()` helper from `apps/api/app/modules/auth/totp/service.py:116-133` (NO duplication — reuse the helper as-is); (3) `record_event(action="auth.recovery_codes.regenerated", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"batch_id": <new_batch_uuid>, "codes_count": 8, "invalidated_count": <int from step 1>})` ONE audit row; returns `RegenerateResponse {recovery_codes: list[str](8), batch_id: UUID, generated_at: ISO-8601}` — IDENTICAL shape to Story 7.2 `ConfirmResponse` (architectural reuse — same `_ConfirmPayload` dataclass; do NOT introduce a separate response model);

- `POST /api/auth/2fa/disable {password, totp_code}` (`current_user` dep, agent-forbidden, 204 No Content on success) — SAME re-auth gate as regenerate (`verify_password` + `verify_totp_code` + same `auth.totp.verify.fail` audit emission on failure); on success, ATOMIC single-session-commit covering: (1) UPDATE recovery_codes SET invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL (invalidate all active rows; deliberate `invalidated_at` set NOT `used_at` to preserve "which codes did the user actually consume" audit history per Decision E §1531 lifecycle-column rationale); (2) UPDATE user SET totp_enabled_at = NULL (the `users.totp_secret` Fernet ciphertext column is INTENTIONALLY RETAINED — epics §1719 verbatim "users.totp_secret is intentionally retained as Fernet ciphertext — disable does not delete the secret column, only clears the timestamp; rationale: enables future 'I re-enrolled with the same authenticator app' path without secret rotation"); (3) `record_event(action="auth.totp.disabled", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"invalidated_count": <int>})` ONE audit row; returns HTTP 204 (NO response body — match the existing logout/logout-all pattern at `apps/api/app/modules/auth/router.py:186,419,449`);

a NEW Pydantic model `ReauthRequest` in `apps/api/app/modules/auth/totp/schemas.py` shared by BOTH endpoints (`password: str = Field(min_length=1, max_length=128)` + `totp_code: str = Field(pattern=r"^\d{6}$")`) and a NEW response model `RegenerateResponse` (alias-typed to the existing `ConfirmResponse` shape — `class RegenerateResponse(ConfirmResponse): pass` because OpenAPI surface readers benefit from a distinct endpoint-response symbol even when the wire shape is identical);

a NEW rate-limit binding extending `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` to ALSO match `POST /api/auth/2fa/recovery-codes/regenerate` and `POST /api/auth/2fa/disable` — both share the existing `ratelimit:login:ip:{ip}` 5-failures-per-60s budget per the same epics §1694 verbatim rationale Story 7.3 invoked ("second-factor failures count against the same `login` scope key"); the re-auth gate has the SAME brute-force surface area as login + verify (password + TOTP guessing), so it MUST share the same rate-limit budget — a separate scope would let an attacker spend their login budget then spend a fresh regenerate/disable budget, defeating the consolidated defense;

a NEW frontend re-auth modal component `apps/web/src/modules/auth/Reauth2faModal.tsx` (~120 LOC; new file) — a controlled modal that takes `{onSubmit: (password, totpCode) => Promise<void>, onCancel: () => void, title: string, submitLabel: string}` and renders two `<Input>` fields (password type="password" autoComplete="current-password" + totp_code inputMode="numeric" pattern="\d{6}" maxLength={6} autoComplete="one-time-code") + Submit/Cancel buttons + an inline error region — used by BOTH the Regenerate and Disable paths in `Settings2faPage.tsx`; modal state is local (NOT React Query cache, NOT localStorage — single-use ephemeral artifact, cleared on close);

EXTENDED `apps/web/src/modules/auth/Settings2faPage.tsx:EnabledPanel` (lines 351-388 today — currently has two `disabled` placeholder buttons with title `t("auth.2fa.status.enabled.coming_in_75")`) — REMOVE the `disabled` attribute + REMOVE the `coming_in_75` title from BOTH buttons + wire `onClick` to open the new `Reauth2faModal` (one modal instance per button, mode-discriminated via component-local state `regenerateModalOpen: bool` / `disableModalOpen: bool`) + on modal `onSubmit` calls (a) for Regenerate: `api("/auth/2fa/recovery-codes/regenerate", { method: "POST", body: JSON.stringify({password, totp_code}) })` then on success TRANSITIONS the parent `Settings2faPage` to the existing Step 3 "show-codes" sub-state (REUSE — set `codesState` + `step="show-codes"` + `confirmedSaved=false` exactly like the post-enroll-confirm path at `Settings2faPage.tsx:77-85`), (b) for Disable: `api("/auth/2fa/disable", { method: "POST", body: JSON.stringify({password, totp_code}) })` (returns 204 — fetch handles empty body), then invalidates `["auth", "2fa", "status"]` query and resets `step="status"` so the disabled panel re-renders; on modal failure: surface 401 → "Incorrect password or code" (new i18n key `auth.2fa.reauth.error.invalid_credentials`), 429 → "Too many attempts, try again later" (REUSE existing `auth.2fa.verify.error.rate_limited` if it exists else add NEW `auth.2fa.reauth.error.rate_limited`), 500 → reuse `auth.2fa.error.totp_not_configured`, other → reuse `auth.2fa.error.network`; the "Continue" button on the post-regenerate show-codes step (existing line 325) navigates back to `/settings/2fa` (NOT to `next` — Story 7.4's forced-enrollment `next` URL flow does NOT apply here because regenerate is a voluntary action initiated from an already-enrolled state);

a NEW Pydantic-validator `password` length cap of 128 chars (matches the existing `User.password_hash` bcrypt-72-byte truncation invariant — bcrypt silently truncates at 72 bytes per `apps/api/app/core/auth/password.py:hash_password`, so longer payloads are wasted bytes; 128 is the documented `LoginRequest.password` cap precedent in the codebase — check current `apps/api/app/modules/auth/models.py:LoginRequest` if unset, add the same cap there too in a follow-up if missing) — defense-in-depth against attacker-injected huge passwords that waste bcrypt CPU before the rate limiter catches up;

a NEW audit action name `auth.recovery_codes.regenerated` added to ZERO new entries in `app/core/audit.py:KNOWN_ENTITY_TYPES` (the entity-type column is `user` — same as `auth.totp.enrolled` / `auth.totp.disabled`; the action name is a free-form string per the `KNOWN_ENTITY_TYPES` docstring at `app/core/audit.py:14` "actions are free-form `action=` strings, NOT entries in `KNOWN_ENTITY_TYPES`") — NO migration needed; the `audit_log.action` text column accepts any string;

a NEW frontend type addition in `apps/web/src/lib/api-types.ts` — `ReauthRequest {password: string; totp_code: string;}` interface mirroring the backend `ReauthRequest` Pydantic model + `RegenerateResponse` re-exported as a type alias of `TotpConfirmResponse` (same shape — `recovery_codes: string[]; batch_id: string; generated_at: string`);

a NEW visual-regression baseline addition in `apps/web/tests/visual/settings-2fa.spec.ts` — TWO new test blocks added per FR13 Baseline Acceptance Gate: (a) `2fa-reauth-modal` (the modal open over the EnabledPanel — captures the password + TOTP code inputs + Submit/Cancel buttons + the enabled-panel context behind it) + (b) `2fa-after-regenerate` (the show-codes step rendered with a fresh batch after the regenerate flow — visually identical to the existing `2fa-show-codes` baseline but with `data-testid="2fa-after-regenerate"` to disambiguate the entry path; if visually identical to the existing show-codes baseline, the new one MAY share the same baseline image file via Playwright's `screenshot.threshold` defaults — flag NON-binding, dev's discretion at implementation time);

realizing **FR5-2FA-4** in full (regenerate + disable both gated on re-auth body `{password, totp_code}`; disable clears `totp_enabled_at` AND invalidates all active recovery_codes rows; post-disable the Story 7.3 partial-auth path no longer triggers because `totp_enabled_at IS NULL`), anchoring architecture.md **Decision E §1515-1534** (batch invalidation via one-statement UPDATE + lifecycle column `invalidated_at` set on regen + per-batch `auth.recovery_codes.regenerated` audit row; the secret-retention rationale from epics §1719 is the binding "do NOT clear `users.totp_secret`" guard), explicitly DEFERRING the admin-mirror force-disable endpoint (`POST /api/admin/users/{id}/force-disable-2fa`) to **Story 8.4** per epics §1799 (that endpoint has different auth contract — `current_admin` actor, NO re-auth re-quirement, `admin_override: true` audit field, retains the SAME secret-retention policy as this story per epics §1799 verbatim "Retained matches Story 7.5 retention policy"), explicitly DEFERRING the force-logout-all-sessions-on-disable behavior (an attacker who steals a session and disables 2FA mid-session leaves no defensive escalation — operator review for E10 audit; flagged as a known limitation in the spec's Dev Notes, NOT a blocker for E7 closure because the actor==target audit row is sufficient evidence for the operator-recovery flow), explicitly DEFERRING the `force_2fa_enrollment` per-user override BOOLEAN column to Story 8.4 (the regen + disable endpoints do NOT consult this column; the column does not exist yet), explicitly DEFERRING any change to the existing Story 7.2/7.3/7.4 surfaces (enrollment endpoints, verify endpoint, login partial-auth + forced-enrollment branches stay BYTE-IDENTICAL — this story is strictly additive), so that EVERY currently-passing test in `apps/api/tests/` (673-test backend baseline post-7.4 + 335 vitest + 216 Playwright per Story 7.4 spec close-out line) continues to pass UNCHANGED AND new tests in:

- `apps/api/tests/test_2fa_regenerate.py` (NEW file ~330 LOC; 9 named tests T-REGEN-1..9 covering golden path + invalidation rowcount + cleartext-once + audit emission shape + 401 wrong password + 401 wrong TOTP + agent 403 + rate-limit shared budget + concurrent-call atomic semantics)
- `apps/api/tests/test_2fa_disable.py` (NEW file ~280 LOC; 8 named tests T-DISABLE-1..8 covering golden path + `totp_secret` retention + post-disable login is single-factor + audit emission shape + 401 wrong password + 401 wrong TOTP + agent 403 + rate-limit shared budget)
- `apps/web/src/modules/auth/Settings2faPage.test.tsx` EXTENDED with 5 new vitest cases V7-V11 (regenerate happy path → show-codes; regenerate 401 → error stays in modal; disable happy path → status panel; disable 401 → error stays in modal; modal cancel → no API call)
- `apps/web/src/modules/auth/Reauth2faModal.test.tsx` (NEW file ~110 LOC; 3 vitest cases R1-R3 covering form submission shape + submit-disabled-while-pending + cancel button calls onCancel)
- `apps/web/tests/visual/settings-2fa.spec.ts` EXTENDED with 2 new baselines (2fa-reauth-modal + 2fa-after-regenerate)

land in this story's diff. Test target counts: **backend 690 (673 baseline + 9 in test_2fa_regenerate.py + 8 in test_2fa_disable.py); vitest 343 (335 baseline + 5 in Settings2faPage.test.tsx + 3 in Reauth2faModal.test.tsx); visual 218 (216 baseline + 2 new baselines)**. The diff is scoped strictly to the regenerate + disable surface; NO new Alembic migration (head stays `0013_users_2fa_columns` from Story 7.1); NO new dependencies (reuses `pyotp` + `bcrypt` + `cryptography` from 7.1+7.2); NO new rate-limit scope (extends existing `login` scope key_fn); NO new audit entity_type (reuses `user`); NO new middleware module; NO new env-var provisioning required on `.190` (this story ships no-op operator footprint).

## Acceptance Criteria

**AC-1 — NEW endpoint `POST /api/auth/2fa/recovery-codes/regenerate` mounted on existing `apps/api/app/modules/auth/totp/router.py` (NOT a new `regenerate_router.py` file).**

- Given the existing 4-endpoint router at `apps/api/app/modules/auth/totp/router.py:65-451` (`/2fa/enroll`, `/2fa/enroll/confirm`, `/2fa/status`, `/2fa/verify`),
- When Story 7.5 ships,
- Then `apps/api/app/modules/auth/totp/router.py` MUST gain ONE new endpoint definition `regenerate_recovery_codes` placed IMMEDIATELY AFTER the existing `verify_second_factor` handler (after line 451):

  ```python
  @router.post(
      "/2fa/recovery-codes/regenerate",
      response_model=RegenerateResponse,
      status_code=status.HTTP_200_OK,
      summary="Regenerate recovery codes — invalidates prior batch, returns 8 new cleartext codes ONCE",
      description=(
          "Re-auth gated body {password, totp_code}. On success: "
          "invalidates the prior batch via UPDATE ... WHERE invalidated_at "
          "IS NULL, mints a fresh 8-code batch, emits "
          "auth.recovery_codes.regenerated audit row, returns the 8 "
          "cleartext codes ONCE. Subsequent /status reads return only "
          "the new batch's metadata. The Fernet-encrypted users.totp_secret "
          "column is unchanged."
      ),
  )
  async def regenerate_recovery_codes(
      payload: ReauthRequest,
      request: Request,
      session: Annotated[Session, Depends(get_session)],
      settings: Annotated[Settings, Depends(get_settings)],
      user_id: uuid.UUID = current_user,
  ) -> RegenerateResponse: ...
  ```

- And the handler MUST execute the following steps in this exact order:

  1. `_assert_fernet_key_configured(settings)` (existing helper from `service.py:57-70`; raises HTTP 500 `totp_not_configured` on empty key — same precedent as enroll/confirm/verify).
  2. `user = session.get(User, user_id)` — 404 `user_not_found` on miss (defense-in-depth; current_user JWT was valid but row gone).
  3. `if user.role == UserRole.agent: raise HTTPException(403, "agent_role_forbidden")` (agent has no 2FA per epics §1666 + Story 7.2 AC-6).
  4. `if user.totp_enabled_at is None: raise HTTPException(409, "totp_not_enrolled")` (regenerate has no prior batch to invalidate; user must enroll first via Story 7.2 enroll/confirm).
  5. `if user.totp_secret is None: raise HTTPException(500, "totp_corrupt_state")` (Story 7.3 §verify Step 3 precedent — should be impossible-by-construction because `totp_enabled_at IS NOT NULL` implies `totp_secret IS NOT NULL`, but defense-in-depth maps the inconsistent state to a clean 500).
  6. **Re-auth gate (password):** `if not await asyncio.to_thread(verify_password, payload.password, user.password_hash): emit auth.totp.verify.fail with after={"method": "regenerate_reauth", "reason": "password"}; raise HTTPException(401, "invalid_credentials")`. Off-loaded to threadpool per Story 7.3 Codex P2-1 pattern (bcrypt cost 12 blocks ~250ms on event loop).
  7. **Re-auth gate (TOTP):** `secret = decrypt_secret(user.totp_secret, settings)` (Fernet-decrypt via the existing Decision D §1509 single-cleartext-surface helper; the `cryptography.fernet.InvalidToken` exception path MUST emit `auth.totp.verify.fail` with `after={"method": "regenerate_reauth", "reason": "fernet_invalid_token"}` and raise 401 — same `# noqa: B904` pattern as Story 7.3 verify); then `if not verify_totp_code(secret, payload.totp_code): emit auth.totp.verify.fail with after={"method": "regenerate_reauth", "reason": "totp"}; raise HTTPException(401, "invalid_credentials")`. Note: BOTH password-failure and TOTP-failure paths surface the SAME `"invalid_credentials"` detail to prevent oracle distinction (Init 0 login precedent — never reveal which factor was wrong).
  8. **Invalidate prior batch + mint new batch (atomic single-session-commit):**

     ```python
     now = datetime.datetime.now(datetime.UTC)
     batch_id, code_pairs = generate_recovery_codes_batch()
     def _commit_batch() -> int:
         result = session.execute(
             update(RecoveryCode)
             .where(RecoveryCode.user_id == user.id)
             .where(RecoveryCode.invalidated_at.is_(None))
             .values(invalidated_at=now)
         )
         invalidated_count = result.rowcount
         for _cleartext, code_hash in code_pairs:
             session.add(
                 RecoveryCode(
                     user_id=user.id,
                     code_hash=code_hash,
                     batch_id=batch_id,
                     generated_at=now,
                 )
             )
         session.commit()
         return invalidated_count
     invalidated_count = await asyncio.to_thread(_commit_batch)
     ```

     The `result.rowcount` value is BINDING in the audit payload — operators querying `audit_log.after_json->>'invalidated_count'` get the prior batch size (typically 8 on first regen, less if some codes were already consumed).
  9. **Audit emission:** `record_event(get_engine(), action="auth.recovery_codes.regenerated", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"batch_id": str(batch_id), "codes_count": 8, "invalidated_count": invalidated_count}, request_id=request.headers.get("x-request-id"))`.
  10. **Return response:** `return RegenerateResponse(recovery_codes=[cleartext for cleartext, _h in code_pairs], batch_id=batch_id, generated_at=now)`.

- And the new endpoint MUST be importable via `from app.modules.auth.totp.router import router` (the existing single `router` symbol — NO new router instance is created).
- And the OpenAPI path MUST be `/api/auth/2fa/recovery-codes/regenerate` (path prefix `/api/auth` from the router + literal `/2fa/recovery-codes/regenerate` in the `@router.post` decorator).
- And NO change to the existing 4 endpoints in this file (enroll, enroll/confirm, status, verify) is allowed — they stay BYTE-IDENTICAL.

**AC-2 — NEW endpoint `POST /api/auth/2fa/disable` mounted on same router; 204 No Content on success; clears `totp_enabled_at` + invalidates all active recovery codes; RETAINS `users.totp_secret` Fernet ciphertext.**

- Given the same router file extension from AC-1,
- When Story 7.5 ships,
- Then `apps/api/app/modules/auth/totp/router.py` MUST gain ONE additional endpoint definition `disable_2fa` placed IMMEDIATELY AFTER the AC-1 `regenerate_recovery_codes` handler:

  ```python
  @router.post(
      "/2fa/disable",
      status_code=status.HTTP_204_NO_CONTENT,
      summary="Disable 2FA — clears users.totp_enabled_at, invalidates recovery codes",
      description=(
          "Re-auth gated body {password, totp_code}. On success: clears "
          "users.totp_enabled_at, invalidates all active recovery_codes "
          "rows for the user, emits auth.totp.disabled audit row. The "
          "Fernet-encrypted users.totp_secret column is intentionally "
          "RETAINED (epics §1719) — disable does not delete the secret, "
          "only the timestamp; this enables future 'I re-enrolled with "
          "the same authenticator app' UX without secret rotation."
      ),
  )
  async def disable_2fa(
      payload: ReauthRequest,
      request: Request,
      response: Response,
      session: Annotated[Session, Depends(get_session)],
      settings: Annotated[Settings, Depends(get_settings)],
      user_id: uuid.UUID = current_user,
  ) -> Response: ...
  ```

- And the handler MUST execute the following steps in this exact order:

  1. Steps 1-7 IDENTICAL to AC-1 (Fernet key gate, user load, agent 403, totp_enabled 409, secret-null 500, password verify gate, TOTP verify gate — all with the same `auth.totp.verify.fail` emissions on failure; the `after.method` value MUST be `"disable_reauth"` instead of `"regenerate_reauth"` so audit-log queries can distinguish the two re-auth surfaces).
  2. **Invalidate active codes + clear timestamp (atomic single-session-commit):**

     ```python
     now = datetime.datetime.now(datetime.UTC)
     def _commit_disable() -> int:
         result = session.execute(
             update(RecoveryCode)
             .where(RecoveryCode.user_id == user.id)
             .where(RecoveryCode.invalidated_at.is_(None))
             .values(invalidated_at=now)
         )
         invalidated_count = result.rowcount
         user.totp_enabled_at = None
         session.add(user)
         session.commit()
         return invalidated_count
     invalidated_count = await asyncio.to_thread(_commit_disable)
     ```

     **CRITICAL:** `user.totp_secret` is NOT mutated. The Fernet ciphertext column stays populated. Verified by AC-9 grep check 4.
  3. **Audit emission:** `record_event(get_engine(), action="auth.totp.disabled", entity_type="user", entity_id=user.id, actor_user_id=user.id, after={"invalidated_count": invalidated_count}, request_id=request.headers.get("x-request-id"))`.
  4. **Return response:** `response.status_code = status.HTTP_204_NO_CONTENT; return response` (NO body — match logout/logout-all precedent at `apps/api/app/modules/auth/router.py:186,419,449`).

- And NO change to `users.totp_secret` is allowed on this path — the Fernet ciphertext column stays UNTOUCHED. Verified by AC-9 grep check 4 (`grep -nE 'totp_secret\s*=' apps/api/app/modules/auth/totp/router.py` → ONE match in `regenerate_recovery_codes` AC-1 step 5 defensive read + ZERO matches in `disable_2fa` AC-2 — disable never assigns to `totp_secret`).

- And the action name `"auth.totp.disabled"` is BINDING (declared as part of the FR5-AUDIT-1 vocabulary in Story 7.1 §sprint-status line 152 + epics §1648 verbatim). The 5 E7 action names landing through E7 are: `auth.totp.enrolled` (7.2), `auth.totp.verify.success` (7.3), `auth.totp.verify.fail` (7.3 + 7.5 re-auth fail), `auth.recovery_code.used` (7.3), `auth.totp.disabled` (7.5). Story 7.5 adds ONE NEW action name `auth.recovery_codes.regenerated` (note the plural `recovery_codes` matching the table name) — this action name is NEW vs the 5-action E7 vocabulary declared at FR5-AUDIT-1 §1666 and the spec EXPLICITLY EXTENDS the E7 vocabulary by 1 action; the audit_log.action column is a free-form text per `app/core/audit.py:14` so no migration / no entity_type addition is needed. Update `apps/api/app/core/audit.py` docstring comment block (lines 18-25 the inline `#` comment list documenting action names per entity_type) to add the new action name to the `user` entity_type row.

**AC-3 — NEW Pydantic schemas in `apps/api/app/modules/auth/totp/schemas.py`: `ReauthRequest` (shared body) + `RegenerateResponse` (alias of `ConfirmResponse` shape).**

- Given the existing 5-model surface in `apps/api/app/modules/auth/totp/schemas.py` (`EnrollResponse`, `ConfirmRequest`, `ConfirmResponse`, `StatusResponse`, `VerifyRequest`),
- When Story 7.5 ships,
- Then `apps/api/app/modules/auth/totp/schemas.py` MUST gain TWO new models added at the end of the file (after `VerifyRequest`):

  ```python
  class ReauthRequest(BaseModel):
      """Body of POST /api/auth/2fa/recovery-codes/regenerate AND
      POST /api/auth/2fa/disable.

      Both endpoints re-auth on (password + totp_code) before mutating
      recovery_codes / users.totp_enabled_at. Sharing one request model
      across both endpoints is binding (Story 7.5 AC-3) — operators
      reading the OpenAPI doc see the same shape twice, reinforcing the
      symmetric re-auth contract.
      """

      password: str = Field(min_length=1, max_length=128)
      totp_code: str = Field(pattern=r"^\d{6}$")


  class RegenerateResponse(ConfirmResponse):
      """Returned by POST /api/auth/2fa/recovery-codes/regenerate.

      Wire shape IDENTICAL to ConfirmResponse (Story 7.2 enroll/confirm)
      — same fields, same types. The subclass exists as a distinct
      OpenAPI symbol so endpoint readers can navigate from the path to
      a dedicated response model name. Adding fields to RegenerateResponse
      in the future must NOT change ConfirmResponse semantics.
      """
  ```

- And `ReauthRequest.password.max_length = 128` is BINDING (defense-in-depth — bcrypt silently truncates at 72 bytes; capping at 128 chars covers all UTF-8 worst-cases without burning CPU on attacker-injected huge payloads). The `LoginRequest.password` field at `apps/api/app/modules/auth/models.py:10` is currently UNCAPPED — Story 7.5 does NOT extend this story's diff to cap `LoginRequest.password`, but the inconsistency is flagged in Dev Notes for a follow-up triage item.
- And `ReauthRequest.totp_code` regex `^\d{6}$` MATCHES the existing `ConfirmRequest.code` pattern at `schemas.py:40` BUT INTENTIONALLY DOES NOT MATCH the existing `VerifyRequest.code` pattern at `schemas.py:79` which is `^(\d{6}|[0-9a-f]{8})$` — the re-auth gate does NOT accept recovery codes (the user MUST prove they have the authenticator app device, not just a recovery code they might have screenshot from someone). This is BINDING — a recovery code MUST NOT pass the re-auth gate for regenerate or disable; recovery codes are second-factor consumers, not re-auth proofs. Verified by AC-7 T-REGEN-7 + T-DISABLE-7.
- And both new models MUST be re-exported from `apps/api/app/modules/auth/totp/__init__.py:18-26` `__all__` tuple in alphabetical order between the existing entries (`ReauthRequest` between `Enrollment2faPayload` and `Settings2faService`; `RegenerateResponse` between `Settings2faService` and `StatusResponse`). And the corresponding `from app.modules.auth.totp.schemas import (...)` block at `__init__.py:8-13` MUST be extended.

**AC-4 — Rate-limit binding extended in `apps/api/app/core/auth/ratelimit.py:login_ratelimit_key` — both new endpoints SHARE the existing `login` scope per-IP budget (5 failures / 60s).**

- Given the existing `login_ratelimit_key` function at `apps/api/app/core/auth/ratelimit.py:80-86`:

  ```python
  def login_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path in {
          "/api/auth/login",
          "/api/auth/2fa/verify",
      }:
          return f"ip:{_client_ip(request)}"
      return None
  ```

- When Story 7.5 ships,
- Then the path-set MUST be extended with EXACTLY TWO new entries:

  ```python
  def login_ratelimit_key(request: Request) -> str | None:
      if request.method == "POST" and request.url.path in {
          "/api/auth/login",
          "/api/auth/2fa/verify",
          "/api/auth/2fa/recovery-codes/regenerate",
          "/api/auth/2fa/disable",
      }:
          return f"ip:{_client_ip(request)}"
      return None
  ```

- And NO change to the threshold (`ratelimit_login_threshold = 5`) or window (`ratelimit_login_window_seconds = 60`) in `apps/api/app/core/config.py` is allowed — the new endpoints inherit the existing values.
- And NO change to the middleware mount block in `apps/api/app/main.py:create_app()` is needed — the existing `RateLimitMiddleware(scope="login", key_fn=login_ratelimit_key, ...)` instance picks up the new paths automatically once `login_ratelimit_key` returns a key for them.
- And the documentation block above the function MUST be updated to reflect the new path-set (replace any "verify" mention with "verify + regenerate + disable").
- And the AC-9 grep check 5 verifies the path-set:

  ```bash
  grep -nE '/api/auth/2fa/(verify|recovery-codes/regenerate|disable)' apps/api/app/core/auth/ratelimit.py
  # ≥3 matches (one per path string)
  ```

**AC-5 — Frontend `EnabledPanel` in `Settings2faPage.tsx` wires the existing Regenerate + Disable buttons (currently disabled placeholders) to open a new `Reauth2faModal` component; success path for Regenerate transitions the parent to Step 3 "show-codes"; success path for Disable invalidates status query + resets to Step 1.**

- Given the existing `EnabledPanel` component at `apps/web/src/modules/auth/Settings2faPage.tsx:346-388`:

  ```tsx
  function EnabledPanel({ data, t }: EnabledPanelProps) {
    /* ... */
    return (
      <div className="space-y-3">
        {/* ... */}
        <Button variant="secondary" disabled title={t("auth.2fa.status.enabled.coming_in_75")}>
          {t("auth.2fa.status.enabled.regenerate_button")}
        </Button>
        <Button variant="secondary" disabled title={t("auth.2fa.status.enabled.coming_in_75")}>
          {t("auth.2fa.status.enabled.disable_button")}
        </Button>
      </div>
    );
  }
  ```

- When Story 7.5 ships,
- Then `EnabledPanel` MUST be refactored to accept callbacks from its parent (Settings2faPage owns the modal state + mutation hooks because the Regenerate success path needs to set parent-level state `step="show-codes"` + `codesState`):

  ```tsx
  interface EnabledPanelProps {
    data: TotpStatusResponse;
    t: ReturnType<typeof useTranslation>["t"];
    onRegenerateClick: () => void;
    onDisableClick: () => void;
  }

  function EnabledPanel({ data, t, onRegenerateClick, onDisableClick }: EnabledPanelProps) {
    /* ... */
    return (
      <div className="space-y-3">
        {/* ... */}
        <Button variant="secondary" onClick={onRegenerateClick}>
          {t("auth.2fa.status.enabled.regenerate_button")}
        </Button>
        <Button variant="secondary" onClick={onDisableClick}>
          {t("auth.2fa.status.enabled.disable_button")}
        </Button>
      </div>
    );
  }
  ```

  The `disabled` attribute MUST be REMOVED. The `title` attribute referencing `coming_in_75` MUST be REMOVED. The `t("auth.2fa.status.enabled.coming_in_75")` i18n key in `en.json` + `pl.json` MUST be REMOVED in this story (AC-8).
- And `Settings2faPage` MUST add TWO new useMutation hooks parallel to the existing `enroll` and `confirm` mutations:

  ```tsx
  const regenerate = useMutation<TotpConfirmResponse, ApiError, ReauthRequest>({
    mutationFn: (body) =>
      api<TotpConfirmResponse>("/auth/2fa/recovery-codes/regenerate", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      setCodesState({
        recovery_codes: data.recovery_codes,
        batch_id: data.batch_id,
        generated_at: data.generated_at,
      });
      setConfirmedSaved(false);
      setReauthModal(null);
      setStep("show-codes");
    },
    onError: () => { /* handled inside Reauth2faModal via mutation state */ },
  });

  const disable = useMutation<void, ApiError, ReauthRequest>({
    mutationFn: (body) =>
      api<void>("/auth/2fa/disable", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setReauthModal(null);
      void qc.invalidateQueries({ queryKey: ["auth", "2fa", "status"] });
      setStep("status");
    },
    onError: () => { /* handled inside Reauth2faModal via mutation state */ },
  });

  type ReauthModalMode = "regenerate" | "disable" | null;
  const [reauthModal, setReauthModal] = useState<ReauthModalMode>(null);
  ```

- And the modal MUST be rendered conditionally in the `step === "status"` JSX branch (outside the `EnabledPanel` so the modal can layer over both the enabled and disabled panels — though it only OPENS in the enabled-panel CTA paths):

  ```tsx
  {reauthModal && (
    <Reauth2faModal
      title={
        reauthModal === "regenerate"
          ? t("auth.2fa.reauth.regenerate_title")
          : t("auth.2fa.reauth.disable_title")
      }
      submitLabel={
        reauthModal === "regenerate"
          ? t("auth.2fa.reauth.regenerate_submit")
          : t("auth.2fa.reauth.disable_submit")
      }
      pending={
        reauthModal === "regenerate"
          ? regenerate.isPending
          : disable.isPending
      }
      error={
        reauthModal === "regenerate"
          ? mapReauthError(regenerate.error, t)
          : mapReauthError(disable.error, t)
      }
      onSubmit={(password, totp_code) => {
        if (reauthModal === "regenerate") {
          regenerate.mutate({ password, totp_code });
        } else {
          disable.mutate({ password, totp_code });
        }
      }}
      onCancel={() => setReauthModal(null)}
    />
  )}
  ```

- And `EnabledPanel` MUST be invoked with the new props in the `step === "status"` branch:

  ```tsx
  <EnabledPanel
    data={status.data}
    t={t}
    onRegenerateClick={() => setReauthModal("regenerate")}
    onDisableClick={() => setReauthModal("disable")}
  />
  ```

- And the post-regenerate `continueToDone` path (existing function at `Settings2faPage.tsx:152-161`) MUST NOT change semantics for the post-regenerate case — it still navigates to `next` if `forcedEnrollmentMode` is true (Story 7.4 carry-over) OR resets to `step="done"` otherwise. For Story 7.5, the regenerate path enters show-codes with `forcedEnrollmentMode` typically FALSE (regenerate is a voluntary action from already-enrolled state), so the continueToDone "done" branch is the normal path. If forcedEnrollmentMode is somehow true on a regenerate (impossible-by-construction because the user is already enrolled to reach the EnabledPanel that exposes the regenerate button), the existing navigate-to-next still wins — no harm done.
- And a NEW helper function `mapReauthError(err: ApiError | null, t): string | null` MUST be added at the bottom of `Settings2faPage.tsx` parallel to the existing `mapEnrollError`:

  ```tsx
  function mapReauthError(
    err: ApiError | null,
    t: ReturnType<typeof useTranslation>["t"],
  ): string | null {
    if (!err) return null;
    if (err.status === 401) return t("auth.2fa.reauth.error.invalid_credentials");
    if (err.status === 429) return t("auth.2fa.reauth.error.rate_limited");
    if (err.status === 500) return t("auth.2fa.error.totp_not_configured");
    return t("auth.2fa.error.network");
  }
  ```

  The `null` return on `!err` is BINDING — the modal must render NO error region when there is no error (avoids an empty "error message" slot showing the previous error after a successful submit).

**AC-6 — NEW component `apps/web/src/modules/auth/Reauth2faModal.tsx` — single-purpose re-auth modal with password + TOTP code inputs, controlled by parent state.**

- Given that no such component exists today,
- When Story 7.5 ships,
- Then `apps/web/src/modules/auth/Reauth2faModal.tsx` MUST be created with the following exact shape:

  ```tsx
  import { useId, useState } from "react";
  import { Button } from "@/ui/button";
  import { Input } from "@/ui/input";

  interface Reauth2faModalProps {
    title: string;
    submitLabel: string;
    pending: boolean;
    error: string | null;
    onSubmit: (password: string, totp_code: string) => void;
    onCancel: () => void;
  }

  export function Reauth2faModal({
    title,
    submitLabel,
    pending,
    error,
    onSubmit,
    onCancel,
  }: Reauth2faModalProps) {
    const passwordId = useId();
    const codeId = useId();
    const [password, setPassword] = useState("");
    const [code, setCode] = useState("");

    function handleSubmit(e: React.FormEvent) {
      e.preventDefault();
      if (pending || password.length === 0 || code.length !== 6) return;
      onSubmit(password, code);
    }

    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-testid="reauth-2fa-modal"
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      >
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-md space-y-4 rounded-md border border-border bg-background p-6 shadow-lg"
        >
          <h2 className="text-lg font-semibold">{title}</h2>
          <div className="space-y-2">
            <label htmlFor={passwordId} className="block text-sm font-medium">
              {/* i18n: auth.2fa.reauth.password_label */}
              Password
            </label>
            <Input
              id={passwordId}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={pending}
            />
          </div>
          <div className="space-y-2">
            <label htmlFor={codeId} className="block text-sm font-medium">
              {/* i18n: auth.2fa.reauth.code_label */}
              6-digit code
            </label>
            <Input
              id={codeId}
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              disabled={pending}
              className="w-32 font-mono tracking-widest"
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onCancel} disabled={pending}>
              {/* i18n: auth.2fa.reauth.cancel */}
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={pending || password.length === 0 || code.length !== 6}
            >
              {submitLabel}
            </Button>
          </div>
        </form>
      </div>
    );
  }
  ```

  **CRITICAL:** the inline English strings in the JSX comments (`Password`, `6-digit code`, `Cancel`) are PLACEHOLDERS — the dev agent MUST replace each with the corresponding `t("auth.2fa.reauth.password_label")` / `t("auth.2fa.reauth.code_label")` / `t("auth.2fa.reauth.cancel")` i18n call AND add the matching component-level `const { t } = useTranslation();` import at the top of the file. The placeholder English values are a hint for what the i18n key SHOULD render in `en.json` — not the final shipped text.

- And the modal MUST NOT manage its own pending / error state — those come exclusively from parent props (parent owns the React Query mutation). This is BINDING because mutating from inside the modal would leak the API surface into a presentational component.
- And the modal MUST clear its local `password` + `code` state when it UNMOUNTS (when parent sets `reauthModal = null`). React's natural unmount-on-conditional-render gives this for free — verified by R3 vitest case.
- And the modal MUST be re-exported from `apps/web/src/modules/auth/` somehow accessible to `Settings2faPage.tsx` via `import { Reauth2faModal } from "./Reauth2faModal"` (sibling-module relative import, matching the existing Settings2faPage import pattern).
- And the dialog MUST trap focus inside its form on open (per WCAG 2.1 dialog-modal pattern) — for Story 7.5, the minimal acceptable implementation is `<input autoFocus>` on the first input (password). A full focus-trap library is OUT OF SCOPE for this story; the bare-minimum a11y signal (`role="dialog" aria-modal="true" aria-label={title}`) is binding.

**AC-7 — 9+8+5+3 = 25 named tests across 4 test files cover the binding behavior at endpoint + component layers.**

The following test names are BINDING — using different test names will cause the AC-9 grep checks to fail. Each test must exist with the EXACT name shown:

**`apps/api/tests/test_2fa_regenerate.py` (NEW file, 9 tests T-REGEN-1..9):**

- `T-REGEN-1`: `def test_regenerate_with_valid_password_and_totp_invalidates_prior_batch_returns_8_new_codes(client)` — fully enroll, snapshot batch_id, call regenerate, verify response.recovery_codes has 8 cleartext entries AND the new batch_id differs from the original AND all 8 old rows now have `invalidated_at IS NOT NULL`.
- `T-REGEN-2`: `def test_regenerate_emits_auth_recovery_codes_regenerated_audit_row_with_invalidated_count(client)` — verify the audit row exists with `action="auth.recovery_codes.regenerated"`, `entity_type="user"`, `actor_user_id == user.id == entity_id`, and `after_json` contains `batch_id` (new UUID), `codes_count: 8`, `invalidated_count: 8`.
- `T-REGEN-3`: `def test_regenerate_after_partial_consumption_invalidated_count_reflects_active_only(client)` — enroll, consume 3 codes via verify, regenerate, assert `invalidated_count == 5` (only the 5 still-active rows were invalidated; the 3 consumed rows already had `used_at IS NOT NULL` and stay UNTOUCHED — `invalidated_at` stays NULL for those because the UPDATE WHERE clause is `invalidated_at IS NULL` not "all rows").
- `T-REGEN-4`: `def test_regenerate_wrong_password_returns_401_emits_verify_fail_audit_no_state_mutation(client)` — golden enroll, call regenerate with wrong password, assert 401 + verify NO new audit row of action="auth.recovery_codes.regenerated" + verify ONE audit row of action="auth.totp.verify.fail" with `after.method == "regenerate_reauth"` `after.reason == "password"` + verify recovery_codes table state UNCHANGED (no new rows, no invalidated_at flips).
- `T-REGEN-5`: `def test_regenerate_wrong_totp_returns_401_emits_verify_fail_audit_no_state_mutation(client)` — same as T-REGEN-4 but wrong TOTP code + assert `after.reason == "totp"`.
- `T-REGEN-6`: `def test_regenerate_agent_role_returns_403(client)` — provision an agent-role user, force `totp_enabled_at` (impossible-by-construction in normal flow but valid for the negative test), call regenerate, assert 403 `agent_role_forbidden`.
- `T-REGEN-7`: `def test_regenerate_with_recovery_code_in_totp_code_field_returns_422_pydantic(client)` — submit a recovery-code-shape value (`[0-9a-f]{8}`) in `totp_code` field, assert 422 (Pydantic validation; the regex `^\d{6}$` rejects). Verifies the re-auth gate does NOT accept recovery codes.
- `T-REGEN-8`: `def test_regenerate_not_enrolled_returns_409_totp_not_enrolled(client)` — user without `totp_enabled_at`, call regenerate, assert 409 `totp_not_enrolled`.
- `T-REGEN-9`: `def test_regenerate_shares_login_ratelimit_budget_429_at_6th_attempt_across_login_verify_regenerate(client)` — 3 failed login attempts + 2 failed verify attempts + 1 failed regenerate attempt → assert 6th attempt returns 429 (verifies the shared per-IP `ratelimit:login:ip:{ip}` budget extends to regenerate).

**`apps/api/tests/test_2fa_disable.py` (NEW file, 8 tests T-DISABLE-1..8):**

- `T-DISABLE-1`: `def test_disable_with_valid_password_and_totp_clears_totp_enabled_at_returns_204(client)` — enroll, call disable, assert 204 + `user.totp_enabled_at IS NULL` after.
- `T-DISABLE-2`: `def test_disable_retains_users_totp_secret_fernet_ciphertext(client)` — enroll, snapshot `user.totp_secret` ciphertext value, call disable, re-read user row, assert `user.totp_secret == snapshotted_ciphertext` (column UNTOUCHED per epics §1719 retention rule).
- `T-DISABLE-3`: `def test_disable_invalidates_all_active_recovery_codes(client)` — enroll, call disable, assert all 8 `recovery_codes` rows for the user now have `invalidated_at IS NOT NULL`.
- `T-DISABLE-4`: `def test_disable_post_state_login_returns_normal_login_response_not_partial_auth(client)` — enroll, disable, attempt fresh `/api/auth/login` with original password, assert response shape is `LoginResponse` (`partial_auth=False`, `totp_enroll_required=False`) NOT `PartialAuthResponse` — verifies the Story 7.3 partial-auth gate no longer fires because `totp_enabled_at IS NULL`.
- `T-DISABLE-5`: `def test_disable_emits_auth_totp_disabled_audit_row_with_invalidated_count(client)` — assert audit row exists with `action="auth.totp.disabled"`, `entity_type="user"`, `actor_user_id == user.id == entity_id`, `after_json.invalidated_count == 8`.
- `T-DISABLE-6`: `def test_disable_wrong_password_returns_401_emits_verify_fail_audit_no_state_mutation(client)` — analogue of T-REGEN-4 with `after.method == "disable_reauth"` and `after.reason == "password"`.
- `T-DISABLE-7`: `def test_disable_with_recovery_code_in_totp_code_field_returns_422_pydantic(client)` — same shape as T-REGEN-7 for disable.
- `T-DISABLE-8`: `def test_disable_shares_login_ratelimit_budget_429_at_6th_attempt_across_login_verify_disable(client)` — same shape as T-REGEN-9 for disable.

**`apps/web/src/modules/auth/Settings2faPage.test.tsx` EXTENDED with 5 vitest cases V7-V11:**

- `V7`: "Regenerate flow: clicking regenerate button opens reauth modal; submit transitions to show-codes step displaying new cleartext codes"
- `V8`: "Regenerate 401 keeps modal open with error message; does NOT advance to show-codes"
- `V9`: "Disable flow: clicking disable button opens reauth modal; submit closes modal, invalidates status query, resets to status step"
- `V10`: "Disable 401 keeps modal open with error message; status query is NOT invalidated"
- `V11`: "Cancel button in reauth modal closes modal without firing API call"

**`apps/web/src/modules/auth/Reauth2faModal.test.tsx` (NEW file, 3 vitest cases R1-R3):**

- `R1`: "Submit button is disabled when password is empty OR code length != 6; enabled when both fields valid"
- `R2`: "onSubmit is called with (password, totp_code) on form submit; not called when fields invalid"
- `R3`: "Submit button + inputs are disabled while pending=true; cancel button still enabled"

**Visual baselines `apps/web/tests/visual/settings-2fa.spec.ts` EXTENDED with 2 new test blocks:**

- `test("2fa-reauth-modal matches baseline", ...)` — stubs status as enabled, clicks Regenerate button, waits for modal to render, screenshots the full viewport (modal + dimmed background).
- `test("2fa-after-regenerate matches baseline", ...)` — stubs status as enabled + stubs `/auth/2fa/recovery-codes/regenerate` POST to return a fresh 8-code batch, clicks Regenerate, fills modal, submits, waits for show-codes view, screenshots.

All baselines are added in the SAME commit as the code change per FR13 Baseline Acceptance Gate.

**AC-8 — i18n keys for the new modal + reauth surfaces — 9 new keys added in `apps/web/src/locales/en.json` + `apps/web/src/locales/pl.json`; obsolete `coming_in_75` key REMOVED.**

- The 9 new keys are:
  - `auth.2fa.reauth.regenerate_title` → en: `Regenerate recovery codes` / pl: `Wygeneruj nowe kody odzyskiwania`
  - `auth.2fa.reauth.regenerate_submit` → en: `Generate new codes` / pl: `Wygeneruj nowe kody`
  - `auth.2fa.reauth.disable_title` → en: `Disable two-factor authentication` / pl: `Wyłącz uwierzytelnianie dwuskładnikowe`
  - `auth.2fa.reauth.disable_submit` → en: `Disable 2FA` / pl: `Wyłącz 2FA`
  - `auth.2fa.reauth.password_label` → en: `Password` / pl: `Hasło`
  - `auth.2fa.reauth.code_label` → en: `6-digit code from your authenticator app` / pl: `6-cyfrowy kod z aplikacji uwierzytelniającej`
  - `auth.2fa.reauth.cancel` → en: `Cancel` / pl: `Anuluj`
  - `auth.2fa.reauth.error.invalid_credentials` → en: `Incorrect password or code, try again` / pl: `Nieprawidłowe hasło lub kod, spróbuj ponownie`
  - `auth.2fa.reauth.error.rate_limited` → en: `Too many attempts, try again later` / pl: `Zbyt wiele prób, spróbuj ponownie później`

- The obsolete key `auth.2fa.status.enabled.coming_in_75` (currently in en.json line 67 + pl.json line 67) MUST be REMOVED — the buttons it documented are now functional. Verified by AC-9 grep check 6.
- Translation polish is binding. Use the existing diacritic conventions in `pl.json` (e.g. line 65 `Wygeneruj nowe kody` matches the existing button label — keep the verb form consistent).

**AC-9 — Pre-merge grep checklist enforces 8 cross-file invariants verbatim.**

The dev agent MUST run all 8 grep commands before flipping the story to `review`. Each command MUST produce the documented output. ALL 8 must pass; ANY non-zero output failure blocks the commit.

1. **Both new endpoints exist on the router:**
   ```bash
   grep -nE 'recovery-codes/regenerate|/2fa/disable' apps/api/app/modules/auth/totp/router.py
   # ≥4 matches (≥2 per endpoint: one in @router.post path arg, one in summary or description)
   ```

2. **New schemas + reauth model exist:**
   ```bash
   grep -nE 'class (ReauthRequest|RegenerateResponse)' apps/api/app/modules/auth/totp/schemas.py
   # exactly 2 matches
   ```

3. **Audit action `auth.recovery_codes.regenerated` emitted from router:**
   ```bash
   grep -n 'auth.recovery_codes.regenerated' apps/api/app/modules/auth/totp/router.py apps/api/app/core/audit.py
   # ≥2 matches (1 in record_event call in router, 1 in audit.py docstring comment update)
   ```

4. **`totp_secret` NOT assigned in `disable_2fa` handler (retention invariant):**
   ```bash
   grep -nE 'user\.totp_secret\s*=' apps/api/app/modules/auth/totp/router.py
   # 0 matches — totp_secret is NEVER assigned in router.py (encrypt_secret return only flows through service.py:confirm_enrollment)
   ```

5. **Rate-limit key_fn extended:**
   ```bash
   grep -nE '/api/auth/2fa/(verify|recovery-codes/regenerate|disable)' apps/api/app/core/auth/ratelimit.py
   # ≥3 matches (one per path string)
   ```

6. **Obsolete `coming_in_75` removed:**
   ```bash
   grep -rn 'coming_in_75' apps/web/src/
   # 0 matches
   ```

7. **All 9 new i18n keys present in both locales:**
   ```bash
   grep -E '"auth\.2fa\.reauth\.' apps/web/src/locales/en.json apps/web/src/locales/pl.json | wc -l
   # ≥18 matches (9 keys × 2 locales)
   ```

8. **Test files exist + binding test names present:**
   ```bash
   grep -nE 'def test_regenerate_with_valid_password_and_totp_invalidates_prior_batch_returns_8_new_codes|def test_disable_with_valid_password_and_totp_clears_totp_enabled_at_returns_204' apps/api/tests/test_2fa_regenerate.py apps/api/tests/test_2fa_disable.py
   # exactly 2 matches (one per file — the T-REGEN-1 and T-DISABLE-1 anchor names)
   ```

**AC-10 — `infra/.190` deployment is no-op-on-config — Story 7.5 ships ZERO operator action requirements.**

- NO new env-var on `.190` (TOTP_FERNET_KEY already provisioned by Story 7.1+7.2 close-out; no new key needed).
- NO Alembic migration (head stays `0013_users_2fa_columns`).
- NO new dependency (reuses `bcrypt`, `pyotp`, `cryptography`, `redis`).
- NO new docker-compose env wiring.
- The deploy-gate skip range from `infra/.last-deploy-sha..HEAD` MUST be empty of infra/env files for this story; `infra/scripts/deploy.sh` will skip the full deploy and only fast-forward the SHA if the dev agent commits only `apps/api/` + `apps/web/` + `_bmad-output/` paths. (Operator-side action: typical `infra/scripts/deploy.sh` invocation per the existing post-merge auto-deploy rule from MEMORY `feedback_auto_deploy_dev.md` — Claude runs this without asking.)

## Tasks / Subtasks

- [ ] **Task 1 — Add `ReauthRequest` + `RegenerateResponse` schemas in `apps/api/app/modules/auth/totp/schemas.py`** (AC: #3)
  - [ ] 1.1 Append `class ReauthRequest(BaseModel): password: str = Field(min_length=1, max_length=128); totp_code: str = Field(pattern=r"^\d{6}$")` at end of file
  - [ ] 1.2 Append `class RegenerateResponse(ConfirmResponse): pass` immediately after
  - [ ] 1.3 Extend `apps/api/app/modules/auth/totp/__init__.py` imports + `__all__` to re-export both new names in alphabetical order

- [ ] **Task 2 — Implement `regenerate_recovery_codes` endpoint in `apps/api/app/modules/auth/totp/router.py`** (AC: #1)
  - [ ] 2.1 Add `from app.core.auth.password import verify_password` import
  - [ ] 2.2 Add `from app.modules.auth.totp.schemas import ReauthRequest, RegenerateResponse` to existing import block
  - [ ] 2.3 Add `from app.modules.auth.totp.service import generate_recovery_codes_batch` import
  - [ ] 2.4 Add `from sqlalchemy import update` import (or extend existing `update` import from line 30)
  - [ ] 2.5 Append `@router.post("/2fa/recovery-codes/regenerate", ...)` decorator + `regenerate_recovery_codes` async handler after `verify_second_factor`, executing AC-1 steps 1-10 in exact order
  - [ ] 2.6 Verify `_assert_fernet_key_configured` is called before any DB / Fernet work

- [ ] **Task 3 — Implement `disable_2fa` endpoint in same router** (AC: #2)
  - [ ] 3.1 Append `@router.post("/2fa/disable", status_code=204)` decorator + `disable_2fa` async handler after `regenerate_recovery_codes`
  - [ ] 3.2 Execute AC-2 steps 1-4 in exact order; CRITICAL: do NOT assign `user.totp_secret = None` or `user.totp_secret = ""` anywhere in this handler — only `user.totp_enabled_at = None` mutation is allowed
  - [ ] 3.3 Verify the 204 No Content return shape mirrors logout-all precedent (`response.status_code = HTTP_204_NO_CONTENT; return response`)

- [ ] **Task 4 — Extend rate-limit key function in `apps/api/app/core/auth/ratelimit.py`** (AC: #4)
  - [ ] 4.1 Add `"/api/auth/2fa/recovery-codes/regenerate"` and `"/api/auth/2fa/disable"` to the path-set inside `login_ratelimit_key`
  - [ ] 4.2 Update the function docstring to reflect the 4-path shared budget

- [ ] **Task 5 — Update audit-action documentation comment in `apps/api/app/core/audit.py`** (AC: #2)
  - [ ] 5.1 Add `auth.recovery_codes.regenerated` to the `# user` entity_type docstring block at lines 18-25
  - [ ] 5.2 Do NOT modify the `KNOWN_ENTITY_TYPES` frozenset (entity_type=`user` already registered)

- [ ] **Task 6 — Create `apps/web/src/modules/auth/Reauth2faModal.tsx`** (AC: #6)
  - [ ] 6.1 Implement the component per the AC-6 reference shape
  - [ ] 6.2 Replace the placeholder English inline strings with `t("auth.2fa.reauth.*")` i18n calls; add `useTranslation` import
  - [ ] 6.3 Verify the modal is fully controlled (no internal mutation state); pending + error come from props only

- [ ] **Task 7 — Extend `apps/web/src/modules/auth/Settings2faPage.tsx`** (AC: #5)
  - [ ] 7.1 Refactor `EnabledPanel` to accept `onRegenerateClick` + `onDisableClick` callbacks; remove `disabled` + `coming_in_75` `title`
  - [ ] 7.2 Add `regenerate` + `disable` useMutation hooks to `Settings2faPage`
  - [ ] 7.3 Add `reauthModal: ReauthModalMode` state + the conditional `<Reauth2faModal />` JSX render
  - [ ] 7.4 Add `mapReauthError` helper at file bottom
  - [ ] 7.5 Wire `onRegenerateClick={() => setReauthModal("regenerate")}` + `onDisableClick={() => setReauthModal("disable")}` in `EnabledPanel` invocation
  - [ ] 7.6 Verify the regenerate-success path sets `step="show-codes"` + the existing show-codes UI re-renders with the new codes (no new UI work needed)

- [ ] **Task 8 — Add i18n keys to en.json + pl.json + remove obsolete `coming_in_75` key** (AC: #8)
  - [ ] 8.1 Add 9 new `auth.2fa.reauth.*` keys to `apps/web/src/locales/en.json` (alphabetically grouped with existing 2fa keys)
  - [ ] 8.2 Add the same 9 keys with Polish translations to `apps/web/src/locales/pl.json`
  - [ ] 8.3 Remove `auth.2fa.status.enabled.coming_in_75` from BOTH locale files (line 67 in each today)

- [ ] **Task 9 — Add API types to `apps/web/src/lib/api-types.ts`** (AC: #5)
  - [ ] 9.1 Add `export interface ReauthRequest { password: string; totp_code: string; }` after the existing TOTP types block (~line 224)
  - [ ] 9.2 Add `export type RegenerateResponse = TotpConfirmResponse;` (type alias — wire shape identical)

- [ ] **Task 10 — Author backend tests `apps/api/tests/test_2fa_regenerate.py`** (AC: #7)
  - [ ] 10.1 Author 9 named tests T-REGEN-1..9 per AC-7 binding names; fixture style mirrors `test_2fa_verify.py` (fresh client + isolated DB)
  - [ ] 10.2 Each test asserts the exact AC-1 behavior (audit shape, state mutation, return shape) — use the test names from AC-7 verbatim

- [ ] **Task 11 — Author backend tests `apps/api/tests/test_2fa_disable.py`** (AC: #7)
  - [ ] 11.1 Author 8 named tests T-DISABLE-1..8 per AC-7 binding names
  - [ ] 11.2 T-DISABLE-2 MUST snapshot `users.totp_secret` BEFORE the disable call and assert byte-identical AFTER — this is the binding retention guard
  - [ ] 11.3 T-DISABLE-4 MUST do a fresh `/api/auth/login` round-trip after disable + assert `partial_auth=False` AND `totp_enroll_required=False` (defense against Story 7.4 forced-enrollment regression where the user's role IS in `enforce_2fa_for_roles` — the test fixture role must NOT be in that list so the assertion is clean; if the test fixture uses `member` role, ensure `enforce_2fa_for_roles=[]` in test settings)

- [ ] **Task 12 — Author frontend vitest tests V7-V11 in existing `Settings2faPage.test.tsx`** (AC: #7)
  - [ ] 12.1 Add 5 new `it("...")` cases inside a new `describe("Settings2faPage — Regenerate + Disable flows (Story 7.5)")` block at end of file
  - [ ] 12.2 Mock `api()` to return appropriate fixture responses per V7-V11 binding behavior

- [ ] **Task 13 — Author `apps/web/src/modules/auth/Reauth2faModal.test.tsx`** (AC: #7)
  - [ ] 13.1 Author 3 named vitest cases R1-R3 per AC-7 binding names
  - [ ] 13.2 Use `render(<Reauth2faModal {...props} />)` with controlled props per the AC-6 interface

- [ ] **Task 14 — Add visual baselines in `apps/web/tests/visual/settings-2fa.spec.ts`** (AC: #7)
  - [ ] 14.1 Add `test("2fa-reauth-modal matches baseline", ...)` — stubs status=enabled, clicks Regenerate button, screenshots
  - [ ] 14.2 Add `test("2fa-after-regenerate matches baseline", ...)` — stubs status=enabled + regenerate POST response, screenshots show-codes view
  - [ ] 14.3 Generate baseline images via `npm run test:visual -- --update-snapshots` in same commit
  - [ ] 14.4 Verify the 218 total baseline count post-commit (216 baseline + 2 new)

- [ ] **Task 15 — Run pre-merge grep checklist + full test suite + ruff** (AC: #9, #10)
  - [ ] 15.1 Execute all 8 AC-9 grep commands; verify expected output for each
  - [ ] 15.2 Run `cd apps/api && uv run ruff format . && uv run ruff check .` — expect 0 violations
  - [ ] 15.3 Run `cd apps/api && uv run pytest -q` — expect 690 pass (673 baseline + 17 new)
  - [ ] 15.4 Run `cd apps/web && npm run typecheck && npm run lint && npm run test` — expect 343 vitest pass (335 baseline + 8 new)
  - [ ] 15.5 Run `cd apps/web && npm run test:visual` — expect 218 visual pass (216 baseline + 2 new)
  - [ ] 15.6 Run `infra/scripts/check-all.sh` end-to-end — expect 10/10 green
  - [ ] 15.7 Flip sprint-status `7-5-regenerate-recovery-codes-disable-totp: ready-for-dev` → `review` AFTER all above pass

## Dev Notes

### Architectural Anchors (verbatim from architecture.md)

- **Decision E §1515-1534 — Recovery codes schema with batch grouping + lifecycle columns + per-code audit.** Story 7.5 realizes the "regeneration (FR5-2FA-4) is a one-statement `UPDATE recovery_codes SET invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL` followed by an INSERT of the new 8-code batch" (§1533 verbatim) — this is the ONLY architecturally-correct way to implement regen. Do NOT introduce a separate `disabled_codes` table; do NOT cascade-delete the old rows; the `invalidated_at` lifecycle column is the binding regen marker per Decision E §1528.
- **Decision E §1530 — "8 codes per batch. Displayed cleartext ONCE at enrollment / regeneration; subsequent panel loads return only batch metadata."** Story 7.5's regenerate response body shows the 8 new cleartext codes ONCE (mirroring Story 7.2's enroll-confirm response) — the `GET /api/auth/2fa/status` endpoint must keep returning ONLY metadata after the show-codes step closes. The frontend must NOT cache the cleartext codes in any persistence layer.
- **Decision D §1509 — Single cleartext-surface invariant.** The regenerate endpoint's re-auth TOTP gate calls `decrypt_secret(user.totp_secret, settings)` — the same Fernet-decrypt boundary used by Story 7.3 verify. Cleartext exists in process memory ONLY for the duration of the `verify_totp_code(secret, payload.totp_code)` call inside the handler. NO logging of the cleartext is permitted; NO persisting it anywhere outside the verify call's stack frame.
- **epics.md §1719 verbatim — Secret retention on disable.** "`users.totp_secret` is intentionally retained as Fernet ciphertext — disable does not delete the secret column, only clears the timestamp; rationale: enables future 'I re-enrolled with the same authenticator app' path without secret rotation (low-priority optimization)." This is the BINDING anti-temptation guard against the obvious-feeling "clear both columns on disable" implementation. AC-2 step 2 + T-DISABLE-2 enforce this verbatim.

### Cross-Story Dependencies

- **Story 7.2** (enrollment endpoints + Settings2faPage wizard) shipped the `Settings2faService` + `generate_recovery_codes_batch` helper + the show-codes wizard step + the `EnabledPanel` placeholder buttons. Story 7.5 reuses all of these. Do NOT duplicate `generate_recovery_codes_batch`; do NOT introduce a parallel batch-generator helper.
- **Story 7.3** (verify endpoint) shipped the `decrypt_secret` + `verify_totp_code` helpers, the partial-auth login branch, and the rate-limit key_fn extension. Story 7.5 reuses `decrypt_secret` + `verify_totp_code` for the re-auth gate; the partial-auth branch is NOT touched (this story has no login flow changes).
- **Story 7.4** (Decision F enforce_2fa + login forced-enrollment branch) shipped the `enforce_2fa_for_roles` Settings field + the `totp_enroll_required` LoginResponse discriminator + the Settings2faPage forced-banner. Story 7.5 has NO interaction with Decision F enforcement — disabling 2FA for a user whose role is in `enforce_2fa_for_roles` will, on the NEXT login, return `totp_enroll_required=True` and force them into the enrollment wizard again. This is the CORRECT behavior (per Story 7.4 binding); T-DISABLE-4 verifies the post-disable login is single-factor by setting the test user's role to one NOT in `enforce_2fa_for_roles`. If the test fixture defaults to a role in the enforce list, T-DISABLE-4 must override `settings.enforce_2fa_for_roles = []` for that test scope.
- **Story 7.6** (recovery-code drill + artifact) consumes Story 7.5 — drill steps 6 + 7 explicitly invoke the regenerate + disable flows on a real test user against `.190`. The drill artifact format mirrors Init 1 verify-symbolication artifact shape. Story 7.5's spec is the binding contract that Story 7.6 will exercise.

### Previous-Story Lessons (mandatory pre-merge AC promotions)

From Stories 6.4 + 6.6 + 6.7 + 7.1 + 7.2 + 7.3 + 7.4 close-outs, the following are now mandatory pre-merge for EVERY new story in this codebase (already absorbed into AC-9 + Task 15):

- **uv.lock regen on dependency changes** — N/A this story (no new deps).
- **docker-compose env wiring on new env vars** — N/A this story (no new env vars).
- **Visual baselines added in the same commit as code change** — AC-7 + Task 14.
- **asyncio.to_thread offload for any bcrypt or sync DB I/O inside an async handler** — AC-1 step 6 (password verify) + step 8 (DB commit) + AC-2 step 2 (DB commit) all use `await asyncio.to_thread(...)` per the Story 7.3 Codex P2-1 pattern.
- **Audit emission on EVERY auth-relevant state mutation OR failure** — AC-1 + AC-2 emit on both success AND each failure branch (password fail, TOTP fail, Fernet invalid).

### Known Limitations Flagged for Operator Review (NOT blockers for this story)

1. **No force-logout-all-sessions on disable.** An attacker with a stolen session who calls `/api/auth/2fa/disable` succeeds (assuming they have the password + TOTP) and leaves the victim's other sessions ACTIVE. The mitigations: (a) re-auth gate requires `password + totp_code` so a session-stealer without the password cannot trivially disable; (b) the `auth.totp.disabled` audit row with `actor==target` provides the operator review signal; (c) Story 8.3 admin force-logout-all-sessions is the operator-recovery path. Flagged for E10 audit review.
2. **`LoginRequest.password` field is uncapped.** Story 7.5's `ReauthRequest.password` caps at 128 chars but the existing `LoginRequest.password` does not. Both surfaces have the same brute-force defense (rate-limit), and bcrypt truncates at 72 bytes anyway. Flagged as a triage item in `_bmad-output/triage-backlog.md` per `feedback_preexisting_issue_threshold` (this is the 1st mention; promotion to triage-stub requires 3rd flag).
3. **Visual baseline `2fa-after-regenerate` may be visually identical to `2fa-show-codes`.** If so, the dev agent MAY skip the second baseline OR add a distinguishing data-testid attribute to disambiguate. Final call is at implementation time.

### Project Structure Notes

- **All `/api/auth/2fa/*` endpoints live in ONE router file** (`apps/api/app/modules/auth/totp/router.py`) per the Story 7.3 precedent. The `_recovery.py:18-19` docstring hint at a separate `regenerate_router.py` file PRE-DATES Story 7.3 and is now stale — the spec EXPLICITLY OVERRIDES that hint. Do NOT create `regenerate_router.py`. Update `_recovery.py:18-19` docstring to remove the stale file reference (replace with mention of `router.py:disable_2fa` + `router.py:regenerate_recovery_codes`).
- **No new Pydantic model file is created** — schemas extend the existing `apps/api/app/modules/auth/totp/schemas.py`.
- **No new frontend module directory is created** — `Reauth2faModal.tsx` is a sibling of `Settings2faPage.tsx` inside `apps/web/src/modules/auth/`.

### References

- [Source: docs/_bmad-output/planning-artifacts/epics.md#Story 7.5 — Regenerate recovery codes + disable TOTP] (epics.md §1710-1721)
- [Source: docs/_bmad-output/planning-artifacts/architecture.md#Decision E — Recovery codes schema] (architecture.md §1515-1534)
- [Source: docs/_bmad-output/planning-artifacts/architecture.md#Decision D — 2FA column shape] (architecture.md §1495-1513)
- [Source: docs/_bmad-output/implementation-artifacts/7-2-totp-enrollment-endpoint-and-ui.md] (Story 7.2 — enrollment endpoints + Settings2faPage wizard)
- [Source: docs/_bmad-output/implementation-artifacts/7-3-login-partial-auth-totp-verify.md] (Story 7.3 — verify endpoint + decrypt_secret + verify_totp_code + rate-limit key_fn extension)
- [Source: docs/_bmad-output/implementation-artifacts/7-4-enforce-2fa-config-startup-fail-fast.md] (Story 7.4 — Decision F enforcement + forced-banner i18n key precedent)
- [Source: apps/api/app/modules/auth/totp/router.py] (4 existing endpoints; this story extends with 2 more)
- [Source: apps/api/app/modules/auth/totp/service.py:116-133] (existing `generate_recovery_codes_batch` helper — REUSE)
- [Source: apps/api/app/modules/auth/totp/service.py:105-113] (existing `decrypt_secret` helper — REUSE)
- [Source: apps/api/app/modules/auth/totp/service.py:95-97] (existing `verify_totp_code` helper — REUSE)
- [Source: apps/api/app/core/auth/password.py:8-12] (existing `verify_password` helper — REUSE)
- [Source: apps/api/app/core/audit.py:14-25] (audit action vocabulary docstring — UPDATE to add new action)
- [Source: apps/web/src/modules/auth/Settings2faPage.tsx:346-388] (existing `EnabledPanel` — REFACTOR; remove disabled + coming_in_75)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
